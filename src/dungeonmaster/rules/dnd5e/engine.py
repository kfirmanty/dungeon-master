"""
D&D 5th Edition rules engine — concrete implementation of RulesEngine Protocol.

This is the default rules system. It delegates to the specialized modules
(abilities, combat, characters) and provides the system info methods that
the AI DM uses to adapt its prompts.
"""

from dungeonmaster.models import AttackResult, CheckResult, DamageResult, DiceResult
from dungeonmaster.rules.base import register_engine
from dungeonmaster.rules.dnd5e.abilities import (
    ability_check,
    concentration_save,
    saving_throw,
    skill_check,
)
from dungeonmaster.rules.dnd5e.characters import (
    create_character as _create_character,
    get_character_summary as _get_character_summary,
    level_up as _level_up,
    take_long_rest,
    take_short_rest,
)
from dungeonmaster.rules.dnd5e.combat import (
    apply_damage as _apply_damage,
    attack_roll,
    death_saving_throw,
    roll_initiative as _roll_initiative,
)


class DnD5eEngine:
    """D&D 5th Edition rules engine."""

    @property
    def system_name(self) -> str:
        return "D&D 5th Edition"

    # --- Checks ---

    def roll_check(
        self,
        character: dict,
        check_type: str,
        detail: str,
        target: int,
        **kwargs,
    ) -> CheckResult:
        """Route to the appropriate check function based on check_type."""
        advantage = kwargs.get("advantage", False)
        disadvantage = kwargs.get("disadvantage", False)

        if check_type == "ability_check":
            return ability_check(
                character, detail, target,
                advantage=advantage, disadvantage=disadvantage,
            )
        elif check_type == "skill_check":
            return skill_check(
                character, detail, target,
                advantage=advantage, disadvantage=disadvantage,
            )
        elif check_type == "saving_throw":
            return saving_throw(
                character, detail, target,
                advantage=advantage, disadvantage=disadvantage,
            )
        elif check_type == "concentration":
            return concentration_save(character, target)
        else:
            raise ValueError(
                f"Unknown check type '{check_type}'. "
                f"Valid types: {', '.join(self.get_check_types())}"
            )

    # --- Combat ---

    def roll_initiative(self, character: dict) -> DiceResult:
        return _roll_initiative(character)

    def resolve_attack(
        self,
        attacker: dict,
        defender: dict,
        weapon: dict | None = None,
        **kwargs,
    ) -> AttackResult:
        target_ac = defender.get("ac", 10)
        return attack_roll(
            attacker, target_ac, weapon=weapon,
            advantage=kwargs.get("advantage", False),
            disadvantage=kwargs.get("disadvantage", False),
            sneak_attack_eligible=kwargs.get("sneak_attack_eligible", False),
        )

    def apply_damage(
        self,
        target: dict,
        damage: int,
        damage_type: str = "",
    ) -> DamageResult:
        return _apply_damage(target, damage, damage_type)

    # --- Characters ---

    def create_character(self, choices: dict) -> dict:
        return _create_character(choices)

    def get_character_summary(self, character: dict) -> str:
        return _get_character_summary(character)

    def get_available_actions(self, character: dict, scene_type: str) -> list[str]:
        """Return valid actions for the current scene type."""
        base_actions = ["look around", "talk", "use item", "rest"]

        if scene_type == "combat":
            return [
                "attack",
                "cast spell",
                "dash",
                "dodge",
                "disengage",
                "help",
                "hide",
                "ready",
                "use item",
            ]
        elif scene_type == "exploration":
            return base_actions + [
                "investigate",
                "search",
                "move",
                "sneak",
                "pick lock",
            ]
        elif scene_type == "social":
            return base_actions + [
                "persuade",
                "intimidate",
                "deceive",
                "insight",
            ]
        elif scene_type == "rest":
            return ["short rest", "long rest", "keep watch", "talk"]
        else:
            return base_actions

    # --- Lifecycle ---

    def take_rest(self, character: dict, rest_type: str) -> dict:
        """Process a short or long rest."""
        if rest_type == "short":
            return take_short_rest(character)
        elif rest_type == "long":
            return take_long_rest(character)
        else:
            raise ValueError(f"Unknown rest type '{rest_type}'. Valid: 'short', 'long'")

    def resolve_spell(self, caster: dict, spell: dict, targets: list[dict], **kwargs) -> CheckResult | AttackResult:
        """Basic spell resolution: attack roll or save DC.

        spell dict should have:
        - type: "attack" or "save"
        - ability: governing ability for save DC (e.g., "wisdom")
        - damage: damage expression (e.g., "3d6")
        - damage_type: e.g., "fire"
        - level: spell level (for slot consumption)
        """
        from dungeonmaster.rules.dnd5e.abilities import ability_modifier, proficiency_bonus
        from dungeonmaster.rules.dnd5e.data import CLASS_SPELLCASTING_ABILITY

        char_class = caster.get("character_class", "").lower()
        casting_ability = CLASS_SPELLCASTING_ABILITY.get(char_class, "intelligence")
        casting_mod = ability_modifier(caster.get("abilities", {}).get(casting_ability, 10))
        prof = proficiency_bonus(caster.get("level", 1))

        spell_type = spell.get("type", "attack")

        if spell_type == "attack":
            # Spell attack roll: d20 + casting mod + proficiency vs target AC
            from dungeonmaster.rules.dice import roll_d20, roll as dice_roll
            target = targets[0] if targets else {"ac": 10}
            target_ac = target.get("ac", 10)
            total_mod = casting_mod + prof
            attack_dice = roll_d20(modifier=total_mod)

            hit = attack_dice.natural_max or (not attack_dice.natural_min and attack_dice.total >= target_ac)
            critical = attack_dice.natural_max

            damage_roll = None
            total_damage = 0
            if hit and spell.get("damage"):
                damage_roll = dice_roll(spell["damage"])
                total_damage = damage_roll.total
                if critical:
                    crit_roll = dice_roll(spell["damage"])
                    total_damage += crit_roll.total

            return AttackResult(
                attack_roll=attack_dice,
                hit=hit,
                critical=critical,
                damage_roll=damage_roll,
                total_damage=total_damage,
                attacker=caster.get("name", "Unknown"),
                defender=target.get("name", "target"),
                description=f"Spell attack: {attack_dice.total} vs AC {target_ac} — {'Hit' if hit else 'Miss'}",
            )
        else:
            # Spell save: DC = 8 + casting mod + proficiency
            dc = 8 + casting_mod + prof
            save_ability = spell.get("ability", "dexterity")
            target = targets[0] if targets else {}
            return saving_throw(target, save_ability, dc)

    def level_up(self, character: dict, choices: dict) -> dict:
        return _level_up(character, choices)

    # --- System info for AI DM ---

    def get_rules_summary(self) -> str:
        return """D&D 5th Edition core mechanics:
- All checks use d20 + modifier vs a Difficulty Class (DC).
  - Easy = DC 10, Medium = DC 15, Hard = DC 20.
- Ability checks: d20 + ability modifier.
- Skill checks: d20 + ability modifier + proficiency bonus (if proficient). Expertise doubles proficiency.
- Saving throws: d20 + ability modifier + proficiency bonus (if proficient).
- Attack rolls: d20 + ability modifier + proficiency vs target's Armor Class (AC).
  - Natural 20 = critical hit (double damage dice). Natural 1 = automatic miss.
- Damage reduces HP. At 0 HP a character falls unconscious and makes death saving throws.
- Advantage: roll 2d20 take the higher. Disadvantage: roll 2d20 take the lower.
- Conditions affect rolls: poisoned/frightened = disadvantage on checks/attacks. Paralyzed/stunned = auto-fail STR/DEX saves.
- Short rest: spend hit dice to recover HP. Long rest: restore all HP and spell slots.
- Spellcasters use spell slots. Spell save DC = 8 + casting modifier + proficiency.
- Six abilities: Strength, Dexterity, Constitution, Intelligence, Wisdom, Charisma.
- Skills are tied to abilities (e.g., Stealth→DEX, Perception→WIS, Persuasion→CHA).
- Key class features: Rogue has Sneak Attack (extra damage with advantage/ally nearby), Barbarian has Rage (bonus damage, resistance)."""

    def get_check_types(self) -> list[str]:
        return ["ability_check", "skill_check", "saving_throw", "attack", "concentration"]


# Register this engine so it can be instantiated by system ID
register_engine("dnd5e", DnD5eEngine)
