"""
AI Dungeon Master — the central orchestrator.

Ties together RAG retrieval, the rules engine, and LLM generation to
process player input and produce narrative responses with mechanical
resolution.

Two-phase flow per turn:
1. Player input → RAG retrieval → LLM generates narrative + [ROLL:...] tags
2. Rules engine resolves rolls → results fed back to LLM → outcome narration
"""

import logging
import time
from typing import Iterator

from bookworm.embeddings.base import EmbeddingProvider
from bookworm.llm.base import LLMProvider

logger = logging.getLogger(__name__)

from dungeonmaster.ai.actions import (
    ActionResult,
    execute_action,
    format_result_for_llm,
    parse_actions,
)
from dungeonmaster.ai.context import build_messages, build_narration_messages
from dungeonmaster.ai.prompts import build_dm_system_prompt
from dungeonmaster.models import GameSession, NarrativeEntry
from dungeonmaster.rules.base import RulesEngine


class DungeonMasterAI:
    """The AI Dungeon Master — processes player input and generates narrative."""

    def __init__(
        self,
        llm: LLMProvider,
        engine: RulesEngine,
        embedding_provider: EmbeddingProvider | None = None,
        conn=None,
    ):
        self.llm = llm
        self.engine = engine
        self.embedding_provider = embedding_provider
        self.conn = conn

    def process_player_input(
        self,
        session: GameSession,
        player_input: str,
    ) -> list[NarrativeEntry]:
        """Main entry point: process player input and return narrative entries.

        Returns a list of NarrativeEntry objects representing:
        - Player's input
        - DM narrative (pre-roll)
        - Dice roll results (if any)
        - DM narrative (post-roll, if rolls occurred)
        """
        turn_start = time.time()
        entries: list[NarrativeEntry] = []
        logger.info("Processing player input: %s", player_input[:80])

        # Record player input
        entries.append(NarrativeEntry(
            actor="player",
            content=player_input,
            action_type="dialogue",
        ))

        # Build character lookup for action execution
        characters = self._build_character_lookup(session)

        # Retrieve context via RAG (if embedding provider + DB available)
        t0 = time.time()
        rule_context, adventure_context = self._retrieve_context(session, player_input)
        logger.info("RAG retrieval: %d rule chunks, %d adventure chunks (%.1fs)",
                     len(rule_context), len(adventure_context), time.time() - t0)

        # Build system prompt from rules engine info
        system_prompt = self._build_system_prompt(session)

        # Build full message list
        messages = build_messages(
            system_prompt=system_prompt,
            history=session.narrative_history,
            rule_context=rule_context,
            adventure_context=adventure_context,
            player_input=player_input,
        )

        # Phase 1: LLM generates narrative + roll tags
        t0 = time.time()
        raw_response = self.llm.generate_chat(messages)
        logger.info("LLM phase 1 response: %d chars (%.1fs)", len(raw_response), time.time() - t0)
        narrative_text, actions = parse_actions(raw_response)
        if actions:
            logger.info("Parsed %d roll tags: %s", len(actions),
                        ", ".join(a.raw_tag for a in actions))

        entries.append(NarrativeEntry(
            actor="dm",
            content=narrative_text,
            action_type="narration",
        ))

        # Phase 2: Execute any roll tags through the rules engine
        if actions:
            action_results = []
            for action in actions:
                result = execute_action(action, self.engine, characters)
                action_results.append(result)

                # Record dice result
                entries.append(self._result_to_entry(result))

            # Phase 2b: Ask LLM to narrate the outcomes
            result_descriptions = [format_result_for_llm(r) for r in action_results]
            narration_messages = build_narration_messages(
                system_prompt=system_prompt,
                narrative_so_far=narrative_text,
                roll_results=result_descriptions,
            )
            outcome_narration = self.llm.generate_chat(narration_messages)

            entries.append(NarrativeEntry(
                actor="dm",
                content=outcome_narration,
                action_type="narration",
            ))

            # Apply state changes from combat results
            self._apply_combat_results(session, action_results)

        return entries

    def process_player_input_stream(
        self,
        session: GameSession,
        player_input: str,
    ) -> Iterator[NarrativeEntry | str]:
        """Streaming version — yields tokens and entries as they're generated.

        Yields:
        - str: individual tokens from the LLM (for real-time display)
        - NarrativeEntry: completed entries (player input, dice results, etc.)
        """
        # Record player input
        yield NarrativeEntry(
            actor="player",
            content=player_input,
            action_type="dialogue",
        )

        characters = self._build_character_lookup(session)
        rule_context, adventure_context = self._retrieve_context(session, player_input)
        system_prompt = self._build_system_prompt(session)

        messages = build_messages(
            system_prompt=system_prompt,
            history=session.narrative_history,
            rule_context=rule_context,
            adventure_context=adventure_context,
            player_input=player_input,
        )

        # Phase 1: Stream narrative from LLM
        full_response = ""
        for token in self.llm.generate_stream(messages):
            full_response += token
            yield token  # stream to frontend

        # Parse roll tags from complete response
        narrative_text, actions = parse_actions(full_response)

        yield NarrativeEntry(
            actor="dm",
            content=narrative_text,
            action_type="narration",
        )

        # Phase 2: Execute rolls and narrate outcomes
        if actions:
            action_results = []
            for action in actions:
                result = execute_action(action, self.engine, characters)
                action_results.append(result)
                yield self._result_to_entry(result)

            result_descriptions = [format_result_for_llm(r) for r in action_results]
            narration_messages = build_narration_messages(
                system_prompt=system_prompt,
                narrative_so_far=narrative_text,
                roll_results=result_descriptions,
            )

            # Stream outcome narration
            outcome_text = ""
            for token in self.llm.generate_stream(narration_messages):
                outcome_text += token
                yield token

            yield NarrativeEntry(
                actor="dm",
                content=outcome_text,
                action_type="narration",
            )

            self._apply_combat_results(session, action_results)

    def run_companion_turn(
        self,
        session: GameSession,
        companion: dict,
    ) -> list[NarrativeEntry]:
        """Generate and resolve an AI companion's turn in combat."""
        from dungeonmaster.ai.prompts import COMPANION_TURN_PROMPT

        system_prompt = self._build_system_prompt(session)
        companion_summary = self.engine.get_character_summary(companion)

        # Build companion prompt
        enemies_str = ", ".join(
            e.get("name", "enemy") for e in session.current_scene.enemies
        )
        allies_str = ", ".join(
            self.engine.get_character_summary(c)
            for c in [session.player_character] + session.companions
            if c.get("name") != companion.get("name")
        )

        prompt = COMPANION_TURN_PROMPT.format(
            companion_name=companion.get("name", "Companion"),
            companion_summary=companion_summary,
            scene_description=session.current_scene.description,
            enemies=enemies_str or "none visible",
            allies=allies_str or "none",
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        raw_response = self.llm.generate_chat(messages)
        narrative_text, actions = parse_actions(raw_response)

        entries = [NarrativeEntry(
            actor=companion.get("name", "Companion"),
            content=narrative_text,
            action_type="combat_action",
        )]

        characters = self._build_character_lookup(session)
        for action in actions:
            result = execute_action(action, self.engine, characters)
            entries.append(self._result_to_entry(result))

        return entries

    # --- Private helpers ---

    def _build_system_prompt(self, session: GameSession) -> str:
        """Build the DM system prompt from current game state."""
        # Party summary
        party_parts = [self.engine.get_character_summary(session.player_character)]
        for comp in session.companions:
            party_parts.append(self.engine.get_character_summary(comp))
        party_summary = "\n".join(party_parts)

        # Scene description
        scene = session.current_scene
        scene_desc = f"Location: {scene.location}\n{scene.description}"
        if scene.npcs_present:
            scene_desc += f"\nNPCs present: {', '.join(scene.npcs_present)}"

        return build_dm_system_prompt(
            rules_summary=self.engine.get_rules_summary(),
            check_types=self.engine.get_check_types(),
            party_summary=party_summary,
            scene_description=scene_desc,
        )

    def _build_character_lookup(self, session: GameSession) -> dict[str, dict]:
        """Build a name → character dict for action execution."""
        lookup = {}
        pc = session.player_character
        if pc:
            lookup[pc.get("name", "Player")] = pc
        for comp in session.companions:
            lookup[comp.get("name", "Companion")] = comp
        for enemy in session.current_scene.enemies:
            lookup[enemy.get("name", "Enemy")] = enemy
        return lookup

    def _retrieve_context(
        self, session: GameSession, query: str,
    ) -> tuple[list[dict], list[dict]]:
        """Retrieve relevant rules and adventure content via RAG."""
        if not self.embedding_provider or not self.conn:
            return [], []

        from dungeonmaster.db.repository import search_by_content_type

        query_embedding = self.embedding_provider.embed_query(query)

        rule_context = search_by_content_type(
            self.conn, query_embedding,
            content_types=["rule"],
            top_k=3,
            book_id=session.rulebook_book_id,
        )

        adventure_context = search_by_content_type(
            self.conn, query_embedding,
            content_types=["encounter", "npc", "monster", "lore"],
            top_k=2,
            book_id=session.adventure_book_id,
        )

        return rule_context, adventure_context

    def _result_to_entry(self, result: ActionResult) -> NarrativeEntry:
        """Convert an ActionResult to a NarrativeEntry for the game log."""
        dice_data = []
        if result.check_result:
            cr = result.check_result
            dice_data.append({
                "expression": cr.dice_result.expression,
                "rolls": cr.dice_result.rolls,
                "modifier": cr.dice_result.modifier,
                "total": cr.dice_result.total,
                "description": cr.description,
            })
        if result.attack_result:
            ar = result.attack_result
            dice_data.append({
                "expression": ar.attack_roll.expression,
                "rolls": ar.attack_roll.rolls,
                "modifier": ar.attack_roll.modifier,
                "total": ar.attack_roll.total,
                "description": ar.description,
            })

        return NarrativeEntry(
            actor="system",
            content=result.description,
            action_type="dice_roll",
            dice_results=dice_data,
        )

    def _apply_combat_results(
        self, session: GameSession, results: list[ActionResult],
    ) -> None:
        """Apply damage and state changes from combat action results."""
        for result in results:
            if result.attack_result and result.attack_result.hit:
                # Find the target and apply damage
                # For now, damage is tracked in the result description
                # Full implementation would update enemy/character HP
                pass
