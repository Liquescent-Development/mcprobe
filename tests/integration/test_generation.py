"""Integration tests for scenario generation."""

from unittest.mock import AsyncMock

import pytest
import yaml

from mcprobe.generator import (
    ComplexityLevel,
    ScenarioGenerator,
    ServerTools,
    ToolSchema,
)
from mcprobe.generator.prompts import GeneratedScenarioContent
from mcprobe.models.scenario import TestScenario
from mcprobe.providers.base import LLMProvider


@pytest.fixture
def weather_tool() -> ToolSchema:
    """Create a weather tool schema."""
    return ToolSchema(
        name="get_weather_forecast",
        description="Get the weather forecast for a location",
        input_schema={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or coordinates",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of forecast days (1-14)",
                },
            },
            "required": ["location"],
        },
    )


@pytest.fixture
def search_tool() -> ToolSchema:
    """Create a search tool schema."""
    return ToolSchema(
        name="search_documents",
        description="Search for documents in the knowledge base",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results"},
            },
            "required": ["query"],
        },
    )


@pytest.fixture
def multi_tool_server(weather_tool: ToolSchema, search_tool: ToolSchema) -> ServerTools:
    """Create a server with multiple tools."""
    return ServerTools(
        tools=[weather_tool, search_tool],
        server_name="test_server",
    )


@pytest.fixture
def mock_llm_provider() -> LLMProvider:
    """Create a mock LLM provider that returns valid content."""
    provider = AsyncMock(spec=LLMProvider)
    return provider


def _create_mock_generated(
    tool_name: str,
    category: str,
) -> GeneratedScenarioContent:
    """Helper to create mock generated content."""
    return GeneratedScenarioContent(
        name=f"{tool_name} {category.replace('_', ' ').title()}",
        description=f"Test {category} scenario for {tool_name}",
        persona=f"A user testing {tool_name}",
        initial_query=f"I want to use {tool_name}",
        known_facts=[f"I know about {tool_name}"],
        unknown_facts=[],
        correctness_criteria=[f"Uses {tool_name} correctly"],
        required_tools=[tool_name],
    )


class TestScenarioGenerationFlow:
    """Integration tests for full generation flow."""

    @pytest.mark.asyncio
    async def test_generate_simple_scenarios(
        self,
        mock_llm_provider: LLMProvider,
        weather_tool: ToolSchema,
    ) -> None:
        """Test generating simple (happy path only) scenarios."""
        server_tools = ServerTools(tools=[weather_tool])

        mock_llm_provider.generate_structured = AsyncMock(
            return_value=_create_mock_generated("get_weather_forecast", "happy_path")
        )

        generator = ScenarioGenerator(mock_llm_provider)
        scenarios = await generator.generate(
            tools=server_tools,
            complexity=ComplexityLevel.SIMPLE,
            count=5,
        )

        # Simple complexity with 1 tool should produce 1 scenario (1 tool * 1 category)
        assert len(scenarios) == 1
        assert scenarios[0].name == "get_weather_forecast Happy Path"
        assert "happy_path" in scenarios[0].tags

    @pytest.mark.asyncio
    async def test_generate_medium_scenarios(
        self,
        mock_llm_provider: LLMProvider,
        weather_tool: ToolSchema,
    ) -> None:
        """Test generating medium complexity scenarios."""
        server_tools = ServerTools(tools=[weather_tool])

        # Return different content based on call count
        call_count = 0

        async def mock_generate(*args, **kwargs):  # noqa: ARG001
            nonlocal call_count
            categories = ["happy_path", "clarification"]
            category = categories[call_count % len(categories)]
            call_count += 1
            return _create_mock_generated("get_weather_forecast", category)

        mock_llm_provider.generate_structured = mock_generate

        generator = ScenarioGenerator(mock_llm_provider)
        scenarios = await generator.generate(
            tools=server_tools,
            complexity=ComplexityLevel.MEDIUM,
            count=5,
        )

        # Medium complexity with 1 tool should produce 2 scenarios
        assert len(scenarios) == 2

    @pytest.mark.asyncio
    async def test_generate_complex_scenarios(
        self,
        mock_llm_provider: LLMProvider,
        weather_tool: ToolSchema,
    ) -> None:
        """Test generating complex scenarios covers all categories."""
        server_tools = ServerTools(tools=[weather_tool])

        categories = ["happy_path", "clarification", "edge_case", "adversarial", "efficiency"]
        call_count = 0

        async def mock_generate(*args, **kwargs):  # noqa: ARG001
            nonlocal call_count
            category = categories[call_count % len(categories)]
            call_count += 1
            return _create_mock_generated("get_weather_forecast", category)

        mock_llm_provider.generate_structured = mock_generate

        generator = ScenarioGenerator(mock_llm_provider)
        scenarios = await generator.generate(
            tools=server_tools,
            complexity=ComplexityLevel.COMPLEX,
            count=10,
        )

        # Complex complexity with 1 tool should produce 5 scenarios
        assert len(scenarios) == 5

        # Verify all categories are represented
        tags = [tag for s in scenarios for tag in s.tags]
        for category in categories:
            assert category in tags

    @pytest.mark.asyncio
    async def test_generate_multiple_tools(
        self,
        mock_llm_provider: LLMProvider,
        multi_tool_server: ServerTools,
    ) -> None:
        """Test generating scenarios for multiple tools."""
        call_count = 0

        async def mock_generate(*args, **kwargs):  # noqa: ARG001
            nonlocal call_count
            tool_names = ["get_weather_forecast", "search_documents"]
            tool_name = tool_names[call_count % 2]
            call_count += 1
            return _create_mock_generated(tool_name, "happy_path")

        mock_llm_provider.generate_structured = mock_generate

        generator = ScenarioGenerator(mock_llm_provider)
        scenarios = await generator.generate(
            tools=multi_tool_server,
            complexity=ComplexityLevel.SIMPLE,
            count=5,
        )

        # Simple with 2 tools should produce 2 scenarios
        assert len(scenarios) == 2

        # Verify both tools are covered
        tool_tags = [tag for s in scenarios for tag in s.tags if tag not in ["happy_path"]]
        assert "get_weather_forecast" in tool_tags
        assert "search_documents" in tool_tags


class TestGeneratedScenarioValidation:
    """Tests that generated scenarios are valid."""

    @pytest.mark.asyncio
    async def test_scenario_validates_as_test_scenario(
        self,
        mock_llm_provider: LLMProvider,
        weather_tool: ToolSchema,
    ) -> None:
        """Test that generated scenarios pass TestScenario validation."""
        server_tools = ServerTools(tools=[weather_tool])

        mock_llm_provider.generate_structured = AsyncMock(
            return_value=_create_mock_generated("get_weather_forecast", "happy_path")
        )

        generator = ScenarioGenerator(mock_llm_provider)
        scenarios = await generator.generate(
            tools=server_tools,
            complexity=ComplexityLevel.SIMPLE,
            count=1,
        )

        # Verify the scenario is a valid TestScenario
        scenario = scenarios[0]
        assert isinstance(scenario, TestScenario)

        # Verify all required fields are present and valid
        assert len(scenario.name) > 0
        assert len(scenario.description) > 0
        assert len(scenario.synthetic_user.persona) > 0
        assert len(scenario.synthetic_user.initial_query) > 0
        assert len(scenario.evaluation.correctness_criteria) > 0

    @pytest.mark.asyncio
    async def test_scenario_can_serialize_to_yaml(
        self,
        mock_llm_provider: LLMProvider,
        weather_tool: ToolSchema,
    ) -> None:
        """Test that generated scenarios can be serialized to YAML."""
        server_tools = ServerTools(tools=[weather_tool])

        mock_llm_provider.generate_structured = AsyncMock(
            return_value=_create_mock_generated("get_weather_forecast", "happy_path")
        )

        generator = ScenarioGenerator(mock_llm_provider)
        scenarios = await generator.generate(
            tools=server_tools,
            complexity=ComplexityLevel.SIMPLE,
            count=1,
        )

        # Serialize to YAML
        scenario_dict = scenarios[0].model_dump(mode="json")
        yaml_output = yaml.dump(scenario_dict, default_flow_style=False)

        # Verify it's valid YAML
        parsed = yaml.safe_load(yaml_output)
        assert parsed["name"] == scenarios[0].name
        assert parsed["synthetic_user"]["persona"] == scenarios[0].synthetic_user.persona

    @pytest.mark.asyncio
    async def test_scenario_includes_efficiency_limits(
        self,
        mock_llm_provider: LLMProvider,
        weather_tool: ToolSchema,
    ) -> None:
        """Test that generated scenarios include efficiency limits from templates."""
        server_tools = ServerTools(tools=[weather_tool])

        mock_llm_provider.generate_structured = AsyncMock(
            return_value=_create_mock_generated("get_weather_forecast", "happy_path")
        )

        generator = ScenarioGenerator(mock_llm_provider)
        scenarios = await generator.generate(
            tools=server_tools,
            complexity=ComplexityLevel.SIMPLE,
            count=1,
        )

        # Happy path template has efficiency limits
        scenario = scenarios[0]
        assert scenario.evaluation.efficiency.max_conversation_turns == 5
        assert scenario.evaluation.efficiency.max_tool_calls == 3
