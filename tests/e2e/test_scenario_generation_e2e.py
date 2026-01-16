"""End-to-end tests for scenario generation with real LLM.

These tests use a real Ollama instance to verify the generation pipeline works.
They are marked with pytest.mark.e2e and can be skipped in CI if Ollama is not available.
"""

import httpx
import pytest
import yaml

from mcprobe.generator import (
    ComplexityLevel,
    ScenarioGenerator,
    ServerTools,
    ToolSchema,
)
from mcprobe.models.config import LLMConfig
from mcprobe.models.scenario import TestScenario
from mcprobe.providers.factory import create_provider


def is_ollama_available() -> bool:
    """Check if Ollama is available locally."""
    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


# Skip all tests in this module if Ollama is not available
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not is_ollama_available(), reason="Ollama not available"),
]


@pytest.fixture
def weather_tool() -> ToolSchema:
    """Create a realistic weather tool schema."""
    return ToolSchema(
        name="get_weather_forecast",
        description=(
            "Get the weather forecast for a specific location. "
            "Returns temperature, conditions, and precipitation probability."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or coordinates (e.g., 'Seattle, WA')",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to forecast (1-14)",
                    "minimum": 1,
                    "maximum": 14,
                },
                "units": {
                    "type": "string",
                    "description": "Temperature units",
                    "enum": ["celsius", "fahrenheit"],
                },
            },
            "required": ["location"],
        },
    )


@pytest.fixture
def search_tool() -> ToolSchema:
    """Create a realistic search tool schema."""
    return ToolSchema(
        name="search_documents",
        description="Search for documents in the knowledge base using semantic search.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query in natural language",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 10)",
                },
                "filter_date_after": {
                    "type": "string",
                    "description": "Only return documents after this date (ISO 8601)",
                },
            },
            "required": ["query"],
        },
    )


@pytest.fixture
def ollama_provider():
    """Create an Ollama provider for testing."""
    config = LLMConfig(
        provider="ollama",
        model="llama3.2",
        base_url="http://localhost:11434",
    )
    return create_provider(config)


class TestScenarioGenerationE2E:
    """End-to-end tests for scenario generation."""

    @pytest.mark.asyncio
    async def test_generate_happy_path_scenario(
        self,
        ollama_provider,
        weather_tool: ToolSchema,
    ) -> None:
        """Test generating a happy path scenario with real LLM."""
        server_tools = ServerTools(tools=[weather_tool])
        generator = ScenarioGenerator(ollama_provider)

        scenarios = await generator.generate(
            tools=server_tools,
            complexity=ComplexityLevel.SIMPLE,
            count=1,
        )

        assert len(scenarios) == 1
        scenario = scenarios[0]

        # Verify it's a valid TestScenario
        assert isinstance(scenario, TestScenario)

        # Verify required fields are populated with meaningful content
        assert len(scenario.name) > 0
        assert len(scenario.description) > 10  # Should be a real description
        assert len(scenario.synthetic_user.persona) > 10  # Should be descriptive
        assert len(scenario.synthetic_user.initial_query) > 5  # Should be a real query
        assert len(scenario.evaluation.correctness_criteria) > 0

        # Verify tool is referenced
        assert "get_weather_forecast" in scenario.evaluation.tool_usage.required_tools

        print(f"\nGenerated scenario: {scenario.name}")
        print(f"  Persona: {scenario.synthetic_user.persona}")
        print(f"  Query: {scenario.synthetic_user.initial_query}")
        print(f"  Criteria: {scenario.evaluation.correctness_criteria}")

    @pytest.mark.asyncio
    async def test_generate_clarification_scenario(
        self,
        ollama_provider,
        weather_tool: ToolSchema,
    ) -> None:
        """Test generating a clarification scenario with real LLM."""
        server_tools = ServerTools(tools=[weather_tool])
        generator = ScenarioGenerator(ollama_provider)

        scenarios = await generator.generate(
            tools=server_tools,
            complexity=ComplexityLevel.MEDIUM,
            count=2,
        )

        # Medium complexity should include happy_path and clarification
        assert len(scenarios) == 2

        # Find the clarification scenario
        clarification_scenarios = [s for s in scenarios if "clarification" in s.tags]
        assert len(clarification_scenarios) == 1

        scenario = clarification_scenarios[0]

        # Clarification scenarios should have more turns allowed
        assert scenario.synthetic_user.max_turns >= 5

        print(f"\nClarification scenario: {scenario.name}")
        print(f"  Query: {scenario.synthetic_user.initial_query}")
        print(f"  Known facts: {scenario.synthetic_user.clarification_behavior.known_facts}")

    @pytest.mark.asyncio
    async def test_generate_multiple_tools(
        self,
        ollama_provider,
        weather_tool: ToolSchema,
        search_tool: ToolSchema,
    ) -> None:
        """Test generating scenarios for multiple tools."""
        server_tools = ServerTools(tools=[weather_tool, search_tool])
        generator = ScenarioGenerator(ollama_provider)

        scenarios = await generator.generate(
            tools=server_tools,
            complexity=ComplexityLevel.SIMPLE,
            count=5,
        )

        # Should generate 1 happy_path per tool = 2 scenarios
        assert len(scenarios) == 2

        # Verify both tools are covered
        tool_names = set()
        for s in scenarios:
            tool_names.update(s.evaluation.tool_usage.required_tools)

        assert "get_weather_forecast" in tool_names
        assert "search_documents" in tool_names

        for scenario in scenarios:
            print(f"\n{scenario.name}")
            print(f"  Tools: {scenario.evaluation.tool_usage.required_tools}")

    @pytest.mark.asyncio
    async def test_generated_scenario_serializes_to_yaml(
        self,
        ollama_provider,
        weather_tool: ToolSchema,
    ) -> None:
        """Test that generated scenarios can be serialized and deserialized."""
        server_tools = ServerTools(tools=[weather_tool])
        generator = ScenarioGenerator(ollama_provider)

        scenarios = await generator.generate(
            tools=server_tools,
            complexity=ComplexityLevel.SIMPLE,
            count=1,
        )

        scenario = scenarios[0]

        # Serialize to YAML
        scenario_dict = scenario.model_dump(mode="json")
        yaml_output = yaml.dump(scenario_dict, default_flow_style=False)

        # Verify it can be parsed back
        parsed = yaml.safe_load(yaml_output)
        restored = TestScenario.model_validate(parsed)

        # Verify key fields match
        assert restored.name == scenario.name
        assert restored.synthetic_user.initial_query == scenario.synthetic_user.initial_query
        assert restored.evaluation.correctness_criteria == scenario.evaluation.correctness_criteria

        print(f"\nGenerated YAML:\n{yaml_output[:500]}...")

    @pytest.mark.asyncio
    async def test_complex_generates_all_categories(
        self,
        ollama_provider,
        weather_tool: ToolSchema,
    ) -> None:
        """Test that complex complexity generates all scenario categories."""
        server_tools = ServerTools(tools=[weather_tool])
        generator = ScenarioGenerator(ollama_provider)

        scenarios = await generator.generate(
            tools=server_tools,
            complexity=ComplexityLevel.COMPLEX,
            count=10,
        )

        # Complex with 1 tool should generate 5 scenarios (one per category)
        assert len(scenarios) == 5

        # Verify all categories are represented
        categories_found = set()
        for s in scenarios:
            for tag in s.tags:
                if tag in ["happy_path", "clarification", "edge_case", "adversarial", "efficiency"]:
                    categories_found.add(tag)

        expected = {"happy_path", "clarification", "edge_case", "adversarial", "efficiency"}
        assert categories_found == expected, f"Missing categories: {expected - categories_found}"

        print("\nGenerated categories:")
        for s in scenarios:
            category = next(t for t in s.tags if t != "get_weather_forecast")
            print(f"  {category}: {s.name}")
