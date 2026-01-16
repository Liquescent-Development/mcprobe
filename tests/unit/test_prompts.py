"""Tests for generation prompts module."""

from mcprobe.generator.mcp_client import ToolSchema
from mcprobe.generator.prompts import (
    CATEGORY_DESCRIPTIONS,
    GeneratedScenarioContent,
    build_generation_prompt,
)


class TestGeneratedScenarioContent:
    """Tests for GeneratedScenarioContent model."""

    def test_minimal_content(self) -> None:
        """Test creating content with only required fields."""
        content = GeneratedScenarioContent(
            name="Test Scenario",
            description="A test scenario",
            persona="Test user",
            initial_query="What is this?",
        )

        assert content.name == "Test Scenario"
        assert content.description == "A test scenario"
        assert content.persona == "Test user"
        assert content.initial_query == "What is this?"
        assert content.known_facts == []
        assert content.unknown_facts == []
        assert content.correctness_criteria == []
        assert content.required_tools == []

    def test_full_content(self) -> None:
        """Test creating content with all fields."""
        content = GeneratedScenarioContent(
            name="Full Scenario",
            description="A complete scenario",
            persona="Detailed user persona",
            initial_query="Complex query",
            known_facts=["fact1", "fact2"],
            unknown_facts=["unknown1"],
            correctness_criteria=["criterion1", "criterion2"],
            required_tools=["tool1", "tool2"],
        )

        assert len(content.known_facts) == 2
        assert len(content.unknown_facts) == 1
        assert len(content.correctness_criteria) == 2
        assert len(content.required_tools) == 2


class TestCategoryDescriptions:
    """Tests for CATEGORY_DESCRIPTIONS."""

    def test_all_categories_have_descriptions(self) -> None:
        """Test that all expected categories have descriptions."""
        expected_categories = [
            "happy_path",
            "clarification",
            "edge_case",
            "adversarial",
            "efficiency",
        ]

        for category in expected_categories:
            assert category in CATEGORY_DESCRIPTIONS
            assert len(CATEGORY_DESCRIPTIONS[category]) > 50

    def test_happy_path_description(self) -> None:
        """Test happy_path description content."""
        desc = CATEGORY_DESCRIPTIONS["happy_path"]

        assert "HAPPY PATH" in desc
        assert "Clearly states" in desc or "all required information" in desc.lower()

    def test_clarification_description(self) -> None:
        """Test clarification description content."""
        desc = CATEGORY_DESCRIPTIONS["clarification"]

        assert "CLARIFICATION" in desc
        assert "ambiguous" in desc.lower() or "follow-up" in desc.lower()

    def test_edge_case_description(self) -> None:
        """Test edge_case description content."""
        desc = CATEGORY_DESCRIPTIONS["edge_case"]

        assert "EDGE CASE" in desc
        assert "missing" in desc.lower() or "boundary" in desc.lower()

    def test_adversarial_description(self) -> None:
        """Test adversarial description content."""
        desc = CATEGORY_DESCRIPTIONS["adversarial"]

        assert "ADVERSARIAL" in desc
        assert "contradict" in desc.lower() or "changing" in desc.lower()

    def test_efficiency_description(self) -> None:
        """Test efficiency description content."""
        desc = CATEGORY_DESCRIPTIONS["efficiency"]

        assert "EFFICIENCY" in desc
        assert "minimal" in desc.lower() or "optimal" in desc.lower()


class TestBuildGenerationPrompt:
    """Tests for build_generation_prompt function."""

    def test_prompt_includes_tool_name(self) -> None:
        """Test that prompt includes tool name."""
        tool = ToolSchema(
            name="get_weather",
            description="Get weather info",
            input_schema={},
        )

        prompt = build_generation_prompt(tool, "happy_path")

        assert "get_weather" in prompt

    def test_prompt_includes_tool_description(self) -> None:
        """Test that prompt includes tool description."""
        tool = ToolSchema(
            name="search",
            description="Search for documents in the database",
            input_schema={},
        )

        prompt = build_generation_prompt(tool, "happy_path")

        assert "Search for documents in the database" in prompt

    def test_prompt_handles_none_description(self) -> None:
        """Test that prompt handles tool with no description."""
        tool = ToolSchema(
            name="mystery_tool",
            description=None,
            input_schema={},
        )

        prompt = build_generation_prompt(tool, "happy_path")

        assert "mystery_tool" in prompt
        assert "No description provided" in prompt

    def test_prompt_includes_parameters(self) -> None:
        """Test that prompt includes parameter information."""
        tool = ToolSchema(
            name="test_tool",
            description="Test",
            input_schema={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                    "days": {"type": "integer", "description": "Number of days"},
                },
                "required": ["location"],
            },
        )

        prompt = build_generation_prompt(tool, "happy_path")

        assert "location" in prompt
        assert "City name" in prompt
        assert "required" in prompt.lower()

    def test_prompt_includes_category_description(self) -> None:
        """Test that prompt includes category-specific instructions."""
        tool = ToolSchema(name="tool", description="desc", input_schema={})

        prompt = build_generation_prompt(tool, "clarification")

        assert "CLARIFICATION" in prompt
        assert "ambiguous" in prompt.lower() or "follow-up" in prompt.lower()

    def test_prompt_includes_output_format(self) -> None:
        """Test that prompt specifies expected output fields."""
        tool = ToolSchema(name="tool", description="desc", input_schema={})

        prompt = build_generation_prompt(tool, "happy_path")

        assert "name" in prompt
        assert "description" in prompt
        assert "persona" in prompt
        assert "initial_query" in prompt
        assert "known_facts" in prompt
        assert "correctness_criteria" in prompt
        assert "required_tools" in prompt
