"""Core scenario generator for MCProbe."""

from enum import Enum
from typing import Any

from mcprobe.generator.mcp_client import ServerTools, ToolSchema
from mcprobe.generator.prompts import GeneratedScenarioContent, build_generation_prompt
from mcprobe.generator.template_loader import load_template
from mcprobe.models.scenario import (
    ClarificationBehavior,
    EfficiencyConfig,
    EvaluationConfig,
    ExpertiseLevel,
    PatienceLevel,
    SyntheticUserConfig,
    TestScenario,
    ToolUsageConfig,
    UserTraits,
    VerbosityLevel,
)
from mcprobe.providers.base import LLMProvider, Message


class ComplexityLevel(str, Enum):
    """Complexity level for scenario generation."""

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class ScenarioCategory(str, Enum):
    """Category of test scenario."""

    HAPPY_PATH = "happy_path"
    CLARIFICATION = "clarification"
    EDGE_CASE = "edge_case"
    ADVERSARIAL = "adversarial"
    EFFICIENCY = "efficiency"


COMPLEXITY_CATEGORIES: dict[ComplexityLevel, list[ScenarioCategory]] = {
    ComplexityLevel.SIMPLE: [ScenarioCategory.HAPPY_PATH],
    ComplexityLevel.MEDIUM: [ScenarioCategory.HAPPY_PATH, ScenarioCategory.CLARIFICATION],
    ComplexityLevel.COMPLEX: list(ScenarioCategory),
}


def _parse_patience(value: str) -> PatienceLevel:
    """Parse patience level from string."""
    mapping = {"low": PatienceLevel.LOW, "medium": PatienceLevel.MEDIUM, "high": PatienceLevel.HIGH}
    return mapping.get(value.lower(), PatienceLevel.MEDIUM)


def _parse_verbosity(value: str) -> VerbosityLevel:
    """Parse verbosity level from string."""
    mapping = {
        "concise": VerbosityLevel.CONCISE,
        "brief": VerbosityLevel.CONCISE,
        "medium": VerbosityLevel.MEDIUM,
        "verbose": VerbosityLevel.VERBOSE,
    }
    return mapping.get(value.lower(), VerbosityLevel.CONCISE)


def _parse_expertise(value: str) -> ExpertiseLevel:
    """Parse expertise level from string."""
    mapping = {
        "novice": ExpertiseLevel.NOVICE,
        "intermediate": ExpertiseLevel.INTERMEDIATE,
        "expert": ExpertiseLevel.EXPERT,
    }
    return mapping.get(value.lower(), ExpertiseLevel.NOVICE)


class ScenarioGenerator:
    """LLM-powered scenario generator."""

    def __init__(self, provider: LLMProvider) -> None:
        """Initialize the generator with an LLM provider.

        Args:
            provider: The LLM provider to use for generation
        """
        self._provider = provider

    async def generate(
        self,
        tools: ServerTools,
        complexity: ComplexityLevel,
        count: int,
    ) -> list[TestScenario]:
        """Generate test scenarios for the given tools.

        Args:
            tools: The tools extracted from the MCP server
            complexity: The complexity level determining which categories to generate
            count: Maximum number of scenarios to generate

        Returns:
            List of generated TestScenario objects
        """
        categories = COMPLEXITY_CATEGORIES[complexity]
        scenarios: list[TestScenario] = []

        for tool in tools.tools:
            for category in categories:
                if len(scenarios) >= count:
                    return scenarios
                scenario = await self._generate_scenario(tool, category)
                scenarios.append(scenario)

        return scenarios

    async def _generate_scenario(
        self,
        tool: ToolSchema,
        category: ScenarioCategory,
    ) -> TestScenario:
        """Generate a single scenario using LLM and template.

        Args:
            tool: The tool schema to generate a scenario for
            category: The scenario category

        Returns:
            A generated TestScenario
        """
        template = load_template(category.value)
        prompt = build_generation_prompt(tool, category.value)

        # Use LLM to generate dynamic content
        messages = [Message(role="user", content=prompt)]
        result = await self._provider.generate_structured(
            messages=messages,
            response_schema=GeneratedScenarioContent,
        )

        # Cast the result to the expected type (provider returns BaseModel)
        generated = GeneratedScenarioContent.model_validate(result.model_dump())

        return self._build_scenario(tool, category, template, generated)

    def _build_scenario(
        self,
        tool: ToolSchema,
        category: ScenarioCategory,
        template: dict[str, Any],
        generated: GeneratedScenarioContent,
    ) -> TestScenario:
        """Build a TestScenario from template and generated content.

        Args:
            tool: The tool schema
            category: The scenario category
            template: The loaded template dict
            generated: The LLM-generated content

        Returns:
            A complete TestScenario
        """
        structure = template.get("structure", {})
        user_structure = structure.get("synthetic_user", {})
        eval_structure = structure.get("evaluation", {})
        traits_config = user_structure.get("traits", {})

        # Build user traits from template
        traits = UserTraits(
            patience=_parse_patience(traits_config.get("patience", "medium")),
            verbosity=_parse_verbosity(traits_config.get("verbosity", "concise")),
            expertise=_parse_expertise(traits_config.get("expertise", "novice")),
        )

        # Build clarification behavior with generated facts
        clarification = ClarificationBehavior(
            known_facts=generated.known_facts,
            unknown_facts=generated.unknown_facts,
            traits=traits,
        )

        # Build synthetic user config
        synthetic_user = SyntheticUserConfig(
            persona=generated.persona,
            initial_query=generated.initial_query,
            clarification_behavior=clarification,
            max_turns=user_structure.get("max_turns", 5),
        )

        # Build tool usage config
        tool_usage = ToolUsageConfig(
            required_tools=generated.required_tools or [tool.name],
            prohibited_tools=eval_structure.get("tool_usage", {}).get("prohibited_tools", []),
        )

        # Build efficiency config from template
        efficiency_config = eval_structure.get("efficiency", {})
        efficiency = EfficiencyConfig(
            max_conversation_turns=efficiency_config.get("max_conversation_turns"),
            max_tool_calls=efficiency_config.get("max_tool_calls"),
        )

        # Build evaluation config
        evaluation = EvaluationConfig(
            correctness_criteria=generated.correctness_criteria or [f"Uses {tool.name} correctly"],
            failure_criteria=eval_structure.get("failure_criteria", []),
            tool_usage=tool_usage,
            efficiency=efficiency,
        )

        return TestScenario(
            name=generated.name,
            description=generated.description,
            synthetic_user=synthetic_user,
            evaluation=evaluation,
            tags=[category.value, tool.name],
        )
