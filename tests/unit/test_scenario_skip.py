"""Tests for scenario skip functionality."""

from mcprobe.models.scenario import (
    ClarificationBehavior,
    EvaluationConfig,
    SyntheticUserConfig,
    TestScenario,
)


def _make_scenario(**kwargs: object) -> TestScenario:
    """Create a minimal TestScenario with overrides."""
    defaults: dict[str, object] = {
        "name": "Test Scenario",
        "description": "A test",
        "synthetic_user": SyntheticUserConfig(
            persona="User",
            initial_query="Hello",
            clarification_behavior=ClarificationBehavior(),
            max_turns=5,
        ),
        "evaluation": EvaluationConfig(
            correctness_criteria=["Responds"],
        ),
    }
    defaults.update(kwargs)
    return TestScenario(**defaults)  # type: ignore[arg-type]


class TestScenarioSkip:
    """Tests for the skip field on TestScenario."""

    def test_skip_defaults_to_none(self) -> None:
        """Skip field is None when not specified."""
        scenario = _make_scenario()
        assert scenario.skip is None

    def test_skip_true(self) -> None:
        """Skip field accepts True."""
        scenario = _make_scenario(skip=True)
        assert scenario.skip is True

    def test_skip_false(self) -> None:
        """Skip field accepts False (treated as not skipped)."""
        scenario = _make_scenario(skip=False)
        assert scenario.skip is False
        # False is falsy, so skip check won't trigger
        assert not scenario.skip

    def test_skip_with_reason_string(self) -> None:
        """Skip field accepts a reason string."""
        scenario = _make_scenario(skip="Feature not ready yet")
        assert scenario.skip == "Feature not ready yet"

    def test_skip_truthy_for_bool_and_string(self) -> None:
        """Both True and non-empty string are truthy for skip checks."""
        assert _make_scenario(skip=True).skip
        assert _make_scenario(skip="reason").skip

    def test_skip_falsy_for_none_and_false(self) -> None:
        """None and False are falsy for skip checks."""
        assert not _make_scenario(skip=None).skip
        assert not _make_scenario(skip=False).skip
