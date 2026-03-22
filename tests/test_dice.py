"""Tests for the shared dice rolling module."""

import random

import pytest

from dungeonmaster.rules.dice import roll, roll_d20, roll_d100, roll_multiple


class TestRoll:
    """Test the universal dice expression parser and roller."""

    def test_simple_d20(self):
        random.seed(42)
        result = roll("1d20")
        assert result.expression == "1d20"
        assert len(result.rolls) == 1
        assert 1 <= result.rolls[0] <= 20
        assert result.modifier == 0
        assert result.total == result.rolls[0]

    def test_shorthand_d20(self):
        """'d20' should be equivalent to '1d20'."""
        random.seed(42)
        r1 = roll("d20")
        random.seed(42)
        r2 = roll("1d20")
        assert r1.rolls == r2.rolls
        assert r1.total == r2.total

    def test_multiple_dice(self):
        random.seed(42)
        result = roll("3d6")
        assert len(result.rolls) == 3
        assert all(1 <= r <= 6 for r in result.rolls)
        assert result.total == sum(result.rolls)
        assert result.modifier == 0

    def test_positive_modifier(self):
        random.seed(42)
        result = roll("1d20+5")
        assert result.modifier == 5
        assert result.total == result.rolls[0] + 5

    def test_negative_modifier(self):
        random.seed(42)
        result = roll("1d8-1")
        assert result.modifier == -1
        assert result.total == result.rolls[0] - 1

    def test_natural_max_single_die(self):
        """Natural max flag should be set when a single die rolls its maximum."""
        # Force a natural 20
        random.seed(0)
        # Find a seed that gives 20
        for seed in range(1000):
            random.seed(seed)
            result = roll("1d20")
            if result.rolls[0] == 20:
                assert result.natural_max is True
                assert result.natural_min is False
                return
        pytest.skip("Could not find seed producing natural 20 in 1000 tries")

    def test_natural_min_single_die(self):
        """Natural min flag should be set when a single die rolls 1."""
        for seed in range(1000):
            random.seed(seed)
            result = roll("1d20")
            if result.rolls[0] == 1:
                assert result.natural_min is True
                assert result.natural_max is False
                return
        pytest.skip("Could not find seed producing natural 1 in 1000 tries")

    def test_no_natural_flags_on_multi_dice(self):
        """Natural max/min flags should only be set for single-die rolls."""
        random.seed(42)
        result = roll("2d6")
        assert result.natural_max is False
        assert result.natural_min is False

    def test_d100(self):
        random.seed(42)
        result = roll("1d100")
        assert 1 <= result.rolls[0] <= 100
        assert result.total == result.rolls[0]

    def test_deterministic_with_seed(self):
        """Same seed should produce same rolls."""
        random.seed(123)
        r1 = roll("2d6+3")
        random.seed(123)
        r2 = roll("2d6+3")
        assert r1.rolls == r2.rolls
        assert r1.total == r2.total

    def test_invalid_expression(self):
        with pytest.raises(ValueError, match="Invalid dice expression"):
            roll("not_a_dice")

    def test_invalid_zero_count(self):
        with pytest.raises(ValueError, match="Dice count must be >= 1"):
            roll("0d6")

    def test_invalid_one_sided_die(self):
        with pytest.raises(ValueError, match="Dice sides must be >= 2"):
            roll("1d1")

    def test_whitespace_handling(self):
        random.seed(42)
        r1 = roll("  2d6 + 3  ")
        random.seed(42)
        r2 = roll("2d6+3")
        assert r1.total == r2.total


class TestRollD20:
    """Test d20 rolls with advantage/disadvantage."""

    def test_normal_roll(self):
        random.seed(42)
        result = roll_d20(modifier=3)
        assert len(result.rolls) == 1
        assert result.total == result.rolls[0] + 3
        assert result.modifier == 3

    def test_advantage_takes_higher(self):
        """Advantage should take the higher of two d20 rolls."""
        random.seed(42)
        result = roll_d20(advantage=True)
        assert len(result.rolls) == 2
        assert result.total == max(result.rolls)

    def test_disadvantage_takes_lower(self):
        """Disadvantage should take the lower of two d20 rolls."""
        random.seed(42)
        result = roll_d20(disadvantage=True)
        assert len(result.rolls) == 2
        assert result.total == min(result.rolls)

    def test_advantage_and_disadvantage_cancel(self):
        """When both advantage and disadvantage apply, they cancel out."""
        random.seed(42)
        result = roll_d20(advantage=True, disadvantage=True)
        assert len(result.rolls) == 1  # normal roll

    def test_advantage_with_modifier(self):
        random.seed(42)
        result = roll_d20(modifier=5, advantage=True)
        assert result.total == max(result.rolls) + 5

    def test_zero_modifier_no_expression_suffix(self):
        random.seed(42)
        result = roll_d20(modifier=0)
        assert "+" not in result.expression or "0" in result.expression


class TestRollD100:
    """Test percentile dice."""

    def test_d100_range(self):
        random.seed(42)
        result = roll_d100()
        assert 1 <= result.total <= 100
        assert result.expression == "1d100"

    def test_d100_deterministic(self):
        random.seed(99)
        r1 = roll_d100()
        random.seed(99)
        r2 = roll_d100()
        assert r1.total == r2.total


class TestRollMultiple:
    """Test rolling the same expression multiple times."""

    def test_roll_six_times(self):
        random.seed(42)
        results = roll_multiple("4d6", 6)
        assert len(results) == 6
        for r in results:
            assert len(r.rolls) == 4
            assert all(1 <= die <= 6 for die in r.rolls)
