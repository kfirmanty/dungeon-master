# ADR-011: SRD Compliance Scope

## Status
Accepted

## Context
After auditing the D&D 5e rules engine against the official SRD content, we identified three tiers of missing features. We needed to decide how much of the SRD to implement given the project's goals (playable single-player RPG, not a full VTT).

## Decision
Implement **high-impact features** that make classes feel mechanically distinct, while deferring features that add complexity without significantly improving gameplay for an AI-run single-player experience.

### Implemented (this iteration)
- **Expertise** — Rogue/Bard double proficiency on chosen skills
- **Conditions in mechanics** — All 15 SRD conditions impose correct advantage/disadvantage/auto-fail
- **Sneak Attack** — Rogue extra damage with finesse/ranged weapons when eligible
- **Rage** — Barbarian bonus damage when raging condition active
- **Unarmored Defense** — Barbarian (10+DEX+CON), Monk (10+DEX+WIS)
- **Damage resistance/immunity** — Type-checked in `apply_damage()`
- **Basic spellcasting** — Spell attack rolls, spell save DCs, spell slot tracking
- **Rest mechanics** — Short rest (hit dice spending, Warlock slot recovery), long rest (full HP, slot reset)
- **Level-up with ASI** — HP gain, feature updates, ability score improvements at 4/8/12/16/19
- **Subraces** — Hill Dwarf, Mountain Dwarf, High Elf, Wood Elf, Lightfoot/Stout Halfling
- **Racial traits and resistances** — Darkvision, poison resistance, etc.
- **Class features levels 1-5** — Key defining features for all 12 classes
- **Spell slot tables** — Full caster, half caster, and Warlock pact magic
- **Concentration saves** — CON save vs max(10, damage/2)

### Deferred
- **Full class features** (levels 6-20) — Very large scope; AI can improvise higher-level features
- **Subclasses** — Depends on full class feature system
- **Feats** — Optional rule, significant complexity for marginal gameplay improvement
- **Multiclassing** — Rare in solo play, very complex interaction rules
- **Full spell definitions** — Individual spell effects are best handled by the AI DM with RAG-retrieved spell text
- **Lair/Legendary actions** — Monster-specific, AI improvises effectively
- **Backgrounds** — Mostly RP flavor (2 skill profs), can be added as proficiency choices

## Consequences

**Positive:**
- Classes now feel mechanically distinct (Rogue deals sneak attack damage, Barbarian rages, etc.)
- Conditions correctly affect gameplay (poisoned creature has disadvantage on attacks)
- Rest cycle creates meaningful resource management (spell slots, hit dice)
- Subraces add character creation depth
- The AI DM's rules summary now mentions conditions, resting, and class features

**Negative:**
- Levels 6-20 class features are not mechanically enforced (AI must improvise)
- Individual spells are not coded — the AI resolves spell effects narratively based on RAG-retrieved spell descriptions
- Some edge cases in multiclass spell slot calculations are not handled
