"""
Conversation history and context window management for the AI DM.

The LLM has a limited context window. This module handles:
- Building the message list from game history
- Trimming old entries to stay within budget
- Including RAG-retrieved context (rules + adventure)
"""

from dungeonmaster.models import NarrativeEntry


# Approximate character budgets (conservative for 8K context models)
MAX_HISTORY_CHARS = 4000
MAX_CONTEXT_CHARS = 2000
KEEP_RECENT_ENTRIES = 8


def build_messages(
    system_prompt: str,
    history: list[NarrativeEntry],
    rule_context: list[dict],
    adventure_context: list[dict],
    player_input: str,
) -> list[dict]:
    """Assemble the full message list for the LLM.

    Structure:
    1. System message (DM instructions, party state, scene)
    2. Conversation history (trimmed to budget)
    3. User message with RAG context + player input

    The player input goes LAST in the user message (lost-in-the-middle effect).
    """
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history as alternating user/assistant messages
    history_messages = _build_history_messages(history)
    messages.extend(history_messages)

    # Build the user message: context + player input
    user_content = _build_user_message(rule_context, adventure_context, player_input)
    messages.append({"role": "user", "content": user_content})

    return messages


def build_narration_messages(
    system_prompt: str,
    narrative_so_far: str,
    roll_results: list[str],
) -> list[dict]:
    """Build messages for the second LLM call (narrating roll outcomes).

    After the rules engine resolves rolls, we ask the LLM to narrate
    the results in character.
    """
    results_text = "\n".join(f"- {r}" for r in roll_results)

    user_content = f"""The following actions were attempted and resolved:

{results_text}

Continue the narrative based on these results. Stay in character as the DM.
Keep it to 1-2 paragraphs. Do not request any new rolls in this response."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": narrative_so_far},
        {"role": "user", "content": user_content},
    ]


def _build_history_messages(history: list[NarrativeEntry]) -> list[dict]:
    """Convert narrative history to LLM message format.

    Keeps the most recent KEEP_RECENT_ENTRIES verbatim.
    Summarizes older entries into a single assistant message.
    """
    if not history:
        return []

    messages = []

    # If we have more entries than we keep verbatim, summarize the rest
    if len(history) > KEEP_RECENT_ENTRIES:
        old_entries = history[:-KEEP_RECENT_ENTRIES]
        summary = _summarize_entries(old_entries)
        if summary:
            messages.append({
                "role": "assistant",
                "content": f"[Previous events summary: {summary}]",
            })

    # Add recent entries verbatim
    recent = history[-KEEP_RECENT_ENTRIES:]
    for entry in recent:
        if entry.actor == "player":
            messages.append({"role": "user", "content": entry.content})
        else:
            # DM narration, companion actions, system messages → assistant role
            prefix = f"[{entry.actor}] " if entry.actor not in ("dm", "system") else ""
            content = f"{prefix}{entry.content}"
            # Include dice results if present
            if entry.dice_results:
                dice_str = " | ".join(
                    f"{d.get('description', d.get('expression', ''))}: {d.get('total', '?')}"
                    for d in entry.dice_results
                )
                content += f"\n[Rolls: {dice_str}]"
            messages.append({"role": "assistant", "content": content})

    # Ensure messages stay within character budget
    return _trim_messages(messages, MAX_HISTORY_CHARS)


def _summarize_entries(entries: list[NarrativeEntry]) -> str:
    """Create a brief summary of older narrative entries.

    Extracts key events and actions, discarding detailed descriptions.
    """
    key_events = []
    for entry in entries:
        if entry.action_type in ("combat_action", "skill_check", "dice_roll"):
            # Mechanical events: keep a brief note
            key_events.append(f"{entry.actor}: {entry.content[:80]}")
        elif entry.actor == "player":
            key_events.append(f"Player: {entry.content[:60]}")
        elif entry.action_type == "narration" and len(entry.content) > 50:
            # Long narration: just note the first sentence
            first_sentence = entry.content.split(".")[0] + "."
            key_events.append(first_sentence[:80])

    if not key_events:
        return ""

    # Cap the summary
    summary = "; ".join(key_events[-10:])
    if len(summary) > 500:
        summary = summary[:497] + "..."
    return summary


def _build_user_message(
    rule_context: list[dict],
    adventure_context: list[dict],
    player_input: str,
) -> str:
    """Build the user message with RAG context and player input.

    Context comes first, player input last (lost-in-the-middle).
    """
    parts = []

    if rule_context:
        rules_text = "\n---\n".join(
            f"[{c.get('chapter_title', 'Rules')}]\n{c['content']}"
            for c in rule_context
        )
        # Trim if too long
        if len(rules_text) > MAX_CONTEXT_CHARS:
            rules_text = rules_text[:MAX_CONTEXT_CHARS] + "..."
        parts.append(f"Relevant rules:\n{rules_text}")

    if adventure_context:
        adventure_text = "\n---\n".join(
            f"[{c.get('chapter_title', 'Adventure')}]\n{c['content']}"
            for c in adventure_context
        )
        if len(adventure_text) > MAX_CONTEXT_CHARS:
            adventure_text = adventure_text[:MAX_CONTEXT_CHARS] + "..."
        parts.append(f"Adventure context (DM eyes only):\n{adventure_text}")

    parts.append(f"Player says: {player_input}")

    return "\n\n".join(parts)


def _trim_messages(messages: list[dict], max_chars: int) -> list[dict]:
    """Trim messages from the front (oldest) to stay within char budget."""
    total = sum(len(m["content"]) for m in messages)
    while total > max_chars and len(messages) > 1:
        removed = messages.pop(0)
        total -= len(removed["content"])
    return messages
