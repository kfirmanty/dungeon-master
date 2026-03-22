"""Tests for the [ROLL:...] tag parser."""

import pytest

from dungeonmaster.ai.actions import parse_actions, GameAction


class TestParseActions:
    def test_no_tags(self):
        text = "You walk into the tavern. The bartender nods at you."
        narrative, actions = parse_actions(text)
        assert narrative == text
        assert actions == []

    def test_single_skill_check(self):
        text = (
            "You attempt to sneak past the guards.\n"
            "[ROLL:skill_check:stealth:DC15:Aelindra]\n"
            "The shadows seem to welcome you."
        )
        narrative, actions = parse_actions(text)
        assert len(actions) == 1
        assert actions[0].action_type == "skill_check"
        assert actions[0].detail == "stealth"
        assert actions[0].target_value == 15
        assert actions[0].actor == "Aelindra"
        # Tag should be stripped from narrative
        assert "[ROLL:" not in narrative
        assert "sneak past the guards" in narrative
        assert "shadows seem to welcome" in narrative

    def test_saving_throw(self):
        text = "A fireball erupts! [ROLL:saving_throw:dexterity:DC13:Thorin]"
        _, actions = parse_actions(text)
        assert actions[0].action_type == "saving_throw"
        assert actions[0].detail == "dexterity"
        assert actions[0].target_value == 13
        assert actions[0].actor == "Thorin"

    def test_attack_with_ac_prefix(self):
        text = "The fighter swings! [ROLL:attack:longsword:AC16:Aelindra]"
        _, actions = parse_actions(text)
        assert actions[0].action_type == "attack"
        assert actions[0].detail == "longsword"
        assert actions[0].target_value == 16

    def test_attack_with_dc_prefix(self):
        text = "Strike! [ROLL:attack:shortsword:DC14:Lyra]"
        _, actions = parse_actions(text)
        assert actions[0].target_value == 14

    def test_no_prefix(self):
        """Tags without DC/AC prefix should still parse."""
        text = "Check! [ROLL:ability_check:strength:20:Conan]"
        _, actions = parse_actions(text)
        assert actions[0].action_type == "ability_check"
        assert actions[0].target_value == 20

    def test_multiple_tags(self):
        text = (
            "The party attempts the obstacle.\n"
            "[ROLL:skill_check:athletics:DC15:Thorin]\n"
            "[ROLL:skill_check:acrobatics:DC12:Lyra]\n"
            "Everyone holds their breath."
        )
        narrative, actions = parse_actions(text)
        assert len(actions) == 2
        assert actions[0].detail == "athletics"
        assert actions[1].detail == "acrobatics"
        assert "[ROLL:" not in narrative

    def test_case_insensitive(self):
        text = "[Roll:Skill_Check:Perception:dc12:Aelindra]"
        _, actions = parse_actions(text)
        assert len(actions) == 1
        assert actions[0].action_type == "skill_check"
        assert actions[0].detail == "perception"

    def test_actor_with_spaces(self):
        text = "[ROLL:attack:longsword:AC15:Sir Aldric the Bold]"
        _, actions = parse_actions(text)
        assert actions[0].actor == "Sir Aldric the Bold"

    def test_narrative_cleanup(self):
        """Verify that stripping tags doesn't leave excessive blank lines."""
        text = "First line.\n\n[ROLL:skill_check:stealth:DC15:Test]\n\nSecond line."
        narrative, _ = parse_actions(text)
        # Should not have triple+ newlines
        assert "\n\n\n" not in narrative

    # --- Loose format (3-field, spaces) ---

    def test_loose_3_field_format(self):
        """LLMs often produce [ROLL: Perception: DC 10: Karol] with spaces and no check_type."""
        text = "You look around. [ROLL: Perception: DC 10: Karol]"
        _, actions = parse_actions(text)
        assert len(actions) == 1
        assert actions[0].detail == "perception"
        assert actions[0].target_value == 10
        assert actions[0].actor == "Karol"
        assert actions[0].action_type == "skill_check"  # inferred from skill name

    def test_loose_with_spaces_around_colons(self):
        text = "[ROLL : skill_check : stealth : DC 15 : Aelindra]"
        _, actions = parse_actions(text)
        assert len(actions) == 1
        assert actions[0].detail == "stealth"
        assert actions[0].target_value == 15

    def test_loose_saving_throw_inferred(self):
        """[ROLL: Dexterity: DC 13: Thorin] should infer saving_throw."""
        text = "[ROLL: Dexterity: DC 13: Thorin]"
        _, actions = parse_actions(text)
        assert len(actions) == 1
        assert actions[0].action_type == "saving_throw"
        assert actions[0].detail == "dexterity"
        assert actions[0].target_value == 13

    def test_all_roll_tags_stripped_from_narrative(self):
        """Any [ROLL...] tag should be stripped, even malformed ones."""
        text = "Text before. [ROLL: weird format here] Text after."
        narrative, _ = parse_actions(text)
        assert "[ROLL" not in narrative
        assert "Text before" in narrative
        assert "Text after" in narrative
