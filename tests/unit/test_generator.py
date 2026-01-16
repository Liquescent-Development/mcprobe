"""Tests for scenario generator module."""

from unittest.mock import AsyncMock

import pytest

from mcprobe.generator.generator import (
    COMPLEXITY_CATEGORIES,
    ComplexityLevel,
    ScenarioCategory,
    ScenarioGenerator,
)
from mcprobe.generator.mcp_client import ServerTools, ToolSchema
from mcprobe.generator.prompts import GeneratedScenarioContent
from mcprobe.providers.base import LLMProvider


@pytest.fixture
def sample_tool() -> ToolSchema:
    """Create a sample tool schema."""
    return ToolSchema(
        name="get_weather",
        description="Get the current weather for a location",
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name or coordinates"},
                "units": {"type": "string", "description": "Temperature units"},
            },
            "required": ["location"],
        },
    )


@pytest.fixture
def sample_server_tools(sample_tool: ToolSchema) -> ServerTools:
    """Create sample server tools."""
    return ServerTools(tools=[sample_tool])


@pytest.fixture
def mock_provider() -> LLMProvider:
    """Create a mock LLM provider."""
    return AsyncMock(spec=LLMProvider)


class TestComplexityCategories:
    """Tests for complexity level to category mapping."""

    def test_simple_complexity(self) -> None:
        """Test simple complexity only includes happy path."""
        categories = COMPLEXITY_CATEGORIES[ComplexityLevel.SIMPLE]
        assert categories == [ScenarioCategory.HAPPY_PATH]

    def test_medium_complexity(self) -> None:
        """Test medium complexity includes happy path and clarification."""
        categories = COMPLEXITY_CATEGORIES[ComplexityLevel.MEDIUM]
        assert ScenarioCategory.HAPPY_PATH in categories
        assert ScenarioCategory.CLARIFICATION in categories
        assert len(categories) == 2

    def test_complex_complexity(self) -> None:
        """Test complex complexity includes all categories."""
        categories = COMPLEXITY_CATEGORIES[ComplexityLevel.COMPLEX]
        assert len(categories) == len(ScenarioCategory)
        for category in ScenarioCategory:
            assert category in categories


class TestScenarioCategory:
    """Tests for ScenarioCategory enum."""

    def test_all_categories_exist(self) -> None:
        """Test all expected categories exist."""
        assert ScenarioCategory.HAPPY_PATH.value == "happy_path"
        assert ScenarioCategory.CLARIFICATION.value == "clarification"
        assert ScenarioCategory.EDGE_CASE.value == "edge_case"
        assert ScenarioCategory.ADVERSARIAL.value == "adversarial"
        assert ScenarioCategory.EFFICIENCY.value == "efficiency"


class TestScenarioGenerator:
    """Tests for ScenarioGenerator class."""

    @pytest.mark.asyncio
    async def test_generate_single_scenario(
        self,
        mock_provider: LLMProvider,
        sample_server_tools: ServerTools,
    ) -> None:
        """Test generating a single scenario."""
        # Mock the LLM response
        mock_generated = GeneratedScenarioContent(
            name="get_weather Happy Path",
            description="Test basic weather retrieval",
            persona="A user checking weather for travel",
            initial_query="What's the weather in Seattle?",
            known_facts=["I want to know about Seattle"],
            unknown_facts=[],
            correctness_criteria=["Returns weather for Seattle"],
            required_tools=["get_weather"],
        )
        mock_provider.generate_structured = AsyncMock(return_value=mock_generated)

        generator = ScenarioGenerator(mock_provider)
        scenarios = await generator.generate(
            tools=sample_server_tools,
            complexity=ComplexityLevel.SIMPLE,
            count=1,
        )

        assert len(scenarios) == 1
        assert scenarios[0].name == "get_weather Happy Path"
        assert "get_weather" in scenarios[0].evaluation.tool_usage.required_tools

    @pytest.mark.asyncio
    async def test_generate_respects_count_limit(
        self,
        mock_provider: LLMProvider,
        sample_server_tools: ServerTools,
    ) -> None:
        """Test that generation respects count limit."""
        mock_generated = GeneratedScenarioContent(
            name="Test Scenario",
            description="Test description",
            persona="Test user",
            initial_query="Test query",
            known_facts=[],
            unknown_facts=[],
            correctness_criteria=["Test criterion"],
            required_tools=["get_weather"],
        )
        mock_provider.generate_structured = AsyncMock(return_value=mock_generated)

        generator = ScenarioGenerator(mock_provider)
        scenarios = await generator.generate(
            tools=sample_server_tools,
            complexity=ComplexityLevel.COMPLEX,
            count=2,
        )

        # Should stop at 2 even though complex would generate 5 per tool
        assert len(scenarios) == 2

    @pytest.mark.asyncio
    async def test_generated_scenario_has_correct_structure(
        self,
        mock_provider: LLMProvider,
        sample_server_tools: ServerTools,
    ) -> None:
        """Test that generated scenario has correct structure."""
        mock_generated = GeneratedScenarioContent(
            name="Weather Test",
            description="Test weather query",
            persona="A traveler planning a trip",
            initial_query="What's the weather forecast?",
            known_facts=["I'm going to Seattle", "Next week"],
            unknown_facts=["Specific dates"],
            correctness_criteria=["Provides forecast", "Mentions temperature"],
            required_tools=["get_weather"],
        )
        mock_provider.generate_structured = AsyncMock(return_value=mock_generated)

        generator = ScenarioGenerator(mock_provider)
        scenarios = await generator.generate(
            tools=sample_server_tools,
            complexity=ComplexityLevel.SIMPLE,
            count=1,
        )

        scenario = scenarios[0]

        # Check synthetic user config
        assert scenario.synthetic_user.persona == "A traveler planning a trip"
        assert scenario.synthetic_user.initial_query == "What's the weather forecast?"
        assert "I'm going to Seattle" in scenario.synthetic_user.clarification_behavior.known_facts
        assert "Specific dates" in scenario.synthetic_user.clarification_behavior.unknown_facts

        # Check evaluation config
        assert "Provides forecast" in scenario.evaluation.correctness_criteria
        assert "get_weather" in scenario.evaluation.tool_usage.required_tools

    @pytest.mark.asyncio
    async def test_scenario_includes_tags(
        self,
        mock_provider: LLMProvider,
        sample_server_tools: ServerTools,
    ) -> None:
        """Test that scenarios include category and tool tags."""
        mock_generated = GeneratedScenarioContent(
            name="Test",
            description="Test",
            persona="Test",
            initial_query="Test",
            correctness_criteria=["Test"],
            required_tools=["get_weather"],
        )
        mock_provider.generate_structured = AsyncMock(return_value=mock_generated)

        generator = ScenarioGenerator(mock_provider)
        scenarios = await generator.generate(
            tools=sample_server_tools,
            complexity=ComplexityLevel.SIMPLE,
            count=1,
        )

        assert "happy_path" in scenarios[0].tags
        assert "get_weather" in scenarios[0].tags
