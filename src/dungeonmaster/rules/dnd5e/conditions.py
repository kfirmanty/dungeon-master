"""
D&D 5e conditions and their mechanical effects.

All 15 SRD conditions with the specific mechanical modifiers they impose
on checks, saves, and attacks. Used by abilities.py and combat.py to
automatically apply condition penalties/bonuses to rolls.
"""

from dataclasses import dataclass, field


@dataclass
class ConditionEffect:
    """Mechanical effects a condition imposes."""

    # Advantage/disadvantage on the affected creature's own rolls
    disadvantage_on_attacks: bool = False
    disadvantage_on_ability_checks: bool = False
    disadvantage_on_dex_saves: bool = False
    disadvantage_on_str_saves: bool = False

    # Effects on rolls AGAINST the affected creature
    attacks_against_have_advantage: bool = False
    attacks_against_have_disadvantage: bool = False

    # Auto-fail conditions
    auto_fail_str_saves: bool = False
    auto_fail_dex_saves: bool = False

    # Other mechanical effects
    speed_zero: bool = False
    incapacitated: bool = False  # can't take actions or reactions
    auto_crit_melee: bool = False  # attacks within 5ft are automatic crits if they hit
    can_act: bool = True  # false means completely unable to act


# All 15 SRD conditions
CONDITIONS: dict[str, ConditionEffect] = {
    "blinded": ConditionEffect(
        disadvantage_on_attacks=True,
        attacks_against_have_advantage=True,
    ),
    "charmed": ConditionEffect(
        # Can't attack the charmer; charmer has advantage on social checks
        # (mostly narrative, hard to encode generically)
    ),
    "deafened": ConditionEffect(
        # Fails hearing-based checks (narrative, handled by DM)
    ),
    "frightened": ConditionEffect(
        disadvantage_on_attacks=True,
        disadvantage_on_ability_checks=True,
    ),
    "grappled": ConditionEffect(
        speed_zero=True,
    ),
    "incapacitated": ConditionEffect(
        incapacitated=True,
        can_act=False,
    ),
    "invisible": ConditionEffect(
        attacks_against_have_disadvantage=True,
        # Invisible creature's attacks have advantage (handled in attack_roll)
    ),
    "paralyzed": ConditionEffect(
        incapacitated=True,
        can_act=False,
        auto_fail_str_saves=True,
        auto_fail_dex_saves=True,
        attacks_against_have_advantage=True,
        auto_crit_melee=True,
    ),
    "petrified": ConditionEffect(
        incapacitated=True,
        can_act=False,
        auto_fail_str_saves=True,
        auto_fail_dex_saves=True,
        attacks_against_have_advantage=True,
        # Also: resistance to all damage, weight x10 (narrative)
    ),
    "poisoned": ConditionEffect(
        disadvantage_on_attacks=True,
        disadvantage_on_ability_checks=True,
    ),
    "prone": ConditionEffect(
        disadvantage_on_attacks=True,
        # Attacks within 5ft have advantage, beyond have disadvantage
        # (distance-dependent — handled specially in combat.py)
    ),
    "restrained": ConditionEffect(
        speed_zero=True,
        disadvantage_on_attacks=True,
        disadvantage_on_dex_saves=True,
        attacks_against_have_advantage=True,
    ),
    "stunned": ConditionEffect(
        incapacitated=True,
        can_act=False,
        auto_fail_str_saves=True,
        auto_fail_dex_saves=True,
        attacks_against_have_advantage=True,
    ),
    "unconscious": ConditionEffect(
        incapacitated=True,
        can_act=False,
        auto_fail_str_saves=True,
        auto_fail_dex_saves=True,
        attacks_against_have_advantage=True,
        auto_crit_melee=True,
    ),
    # Exhaustion is special — 6 levels with cumulative effects
    # Level 1: disadvantage on ability checks
    # Level 2: speed halved
    # Level 3: disadvantage on attacks and saves
    # Level 4: HP max halved
    # Level 5: speed 0
    # Level 6: death
    "exhaustion_1": ConditionEffect(
        disadvantage_on_ability_checks=True,
    ),
    "exhaustion_2": ConditionEffect(
        disadvantage_on_ability_checks=True,
        # speed halved (handled narratively)
    ),
    "exhaustion_3": ConditionEffect(
        disadvantage_on_ability_checks=True,
        disadvantage_on_attacks=True,
        disadvantage_on_dex_saves=True,
        disadvantage_on_str_saves=True,
    ),
}


def get_condition_effects(conditions: list[str]) -> ConditionEffect:
    """Merge effects from all active conditions into a single ConditionEffect.

    If any condition grants advantage/disadvantage, the combined result reflects it.
    """
    combined = ConditionEffect()
    for cond_name in conditions:
        cond_lower = cond_name.lower()
        effect = CONDITIONS.get(cond_lower)
        if effect is None:
            continue

        if effect.disadvantage_on_attacks:
            combined.disadvantage_on_attacks = True
        if effect.disadvantage_on_ability_checks:
            combined.disadvantage_on_ability_checks = True
        if effect.disadvantage_on_dex_saves:
            combined.disadvantage_on_dex_saves = True
        if effect.disadvantage_on_str_saves:
            combined.disadvantage_on_str_saves = True
        if effect.attacks_against_have_advantage:
            combined.attacks_against_have_advantage = True
        if effect.attacks_against_have_disadvantage:
            combined.attacks_against_have_disadvantage = True
        if effect.auto_fail_str_saves:
            combined.auto_fail_str_saves = True
        if effect.auto_fail_dex_saves:
            combined.auto_fail_dex_saves = True
        if effect.speed_zero:
            combined.speed_zero = True
        if effect.incapacitated:
            combined.incapacitated = True
        if effect.auto_crit_melee:
            combined.auto_crit_melee = True
        if not effect.can_act:
            combined.can_act = False

    return combined
