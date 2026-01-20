"""Tests for prompt and schema tracking functionality (GH Issue #24)."""

from pathlib import Path
from unittest.mock import MagicMock

from mcprobe.agents.simple import SimpleLLMAgent
from mcprobe.config import FileConfig, MCPServerConfig


class TestComputeHash:
    """Tests for hash computation helper."""

    def test_compute_hash_string(self) -> None:
        """Computes consistent hash for same string."""
        from mcprobe.pytest_plugin.plugin import compute_hash

        result1 = compute_hash("test string")
        result2 = compute_hash("test string")

        assert result1 == result2
        assert result1 is not None
        assert len(result1) == 16  # First 16 chars of SHA256

    def test_compute_hash_different_strings(self) -> None:
        """Different strings produce different hashes."""
        from mcprobe.pytest_plugin.plugin import compute_hash

        result1 = compute_hash("string one")
        result2 = compute_hash("string two")

        assert result1 != result2

    def test_compute_hash_dict(self) -> None:
        """Computes consistent hash for dict."""
        from mcprobe.pytest_plugin.plugin import compute_hash

        data = {"name": "test_tool", "description": "A test tool"}
        result1 = compute_hash(data)
        result2 = compute_hash(data)

        assert result1 == result2
        assert result1 is not None
        assert len(result1) == 16

    def test_compute_hash_dict_order_independent(self) -> None:
        """Dict hashes are order-independent (sorted keys)."""
        from mcprobe.pytest_plugin.plugin import compute_hash

        data1 = {"b": 2, "a": 1}
        data2 = {"a": 1, "b": 2}

        assert compute_hash(data1) == compute_hash(data2)

    def test_compute_hash_list(self) -> None:
        """Computes consistent hash for list."""
        from mcprobe.pytest_plugin.plugin import compute_hash

        data = [{"name": "tool1"}, {"name": "tool2"}]
        result1 = compute_hash(data)
        result2 = compute_hash(data)

        assert result1 == result2

    def test_compute_hash_none(self) -> None:
        """Returns None for None input."""
        from mcprobe.pytest_plugin.plugin import compute_hash

        result = compute_hash(None)
        assert result is None

    def test_compute_hash_empty_string(self) -> None:
        """Computes hash for empty string."""
        from mcprobe.pytest_plugin.plugin import compute_hash

        result = compute_hash("")
        assert result is not None
        assert len(result) == 16


class TestSimpleAgentGetSystemPrompt:
    """Tests for SimpleLLMAgent.get_system_prompt()."""

    def test_get_system_prompt_returns_prompt(self) -> None:
        """Returns the system prompt when set."""
        provider = MagicMock()
        agent = SimpleLLMAgent(
            provider=provider,
            system_prompt="You are a helpful assistant.",
        )

        result = agent.get_system_prompt()
        assert result == "You are a helpful assistant."

    def test_get_system_prompt_returns_none_when_not_set(self) -> None:
        """Returns None when no system prompt set."""
        provider = MagicMock()
        agent = SimpleLLMAgent(provider=provider)

        result = agent.get_system_prompt()
        assert result is None

    def test_get_system_prompt_empty_string(self) -> None:
        """Returns empty string when set to empty."""
        provider = MagicMock()
        agent = SimpleLLMAgent(provider=provider, system_prompt="")

        # Empty string is falsy but still a value
        result = agent.get_system_prompt()
        assert result == ""


class TestTestRunResultModel:
    """Tests for TestRunResult model with new fields."""

    def test_result_with_prompt_serializes(self) -> None:
        """Result with system prompt serializes correctly."""
        import time
        from datetime import datetime

        from mcprobe.models.conversation import (
            ConversationResult,
            ConversationTurn,
            TerminationReason,
        )
        from mcprobe.models.judgment import JudgmentResult
        from mcprobe.persistence import TestRunResult

        result = TestRunResult(
            run_id="test-123",
            timestamp=datetime.now(),
            scenario_name="Test Scenario",
            scenario_file="/path/to/scenario.yaml",
            conversation_result=ConversationResult(
                turns=[ConversationTurn(role="user", content="Hello", timestamp=time.time())],
                final_answer="Hi there!",
                total_tool_calls=[],
                total_tokens=10,
                duration_seconds=1.0,
                termination_reason=TerminationReason.USER_SATISFIED,
            ),
            judgment_result=JudgmentResult(
                passed=True,
                score=1.0,
                correctness_results={"test": True},
                failure_results={},
                tool_usage_results={
                    "required_tools": [],
                    "required_tools_used": [],
                    "prohibited_tools": [],
                    "prohibited_tools_used": [],
                    "all_required_used": True,
                    "no_prohibited_used": True,
                    "criteria_results": {},
                },
                efficiency_results={
                    "total_tool_calls": 0,
                    "max_tool_calls": 10,
                    "total_turns": 1,
                    "max_turns": 5,
                    "within_limits": True,
                    "total_tokens": 10,
                },
                reasoning="Test passed",
            ),
            agent_type="simple",
            judge_model="test-model",
            synthetic_user_model="test-model",
            agent_model="test-model",
            duration_seconds=1.0,
            mcprobe_version="0.1.0",
            python_version="3.12.0",
            agent_system_prompt="You are a test assistant.",
            agent_system_prompt_hash="abc123def456",
            mcp_tool_schemas=[{"name": "tool1", "description": "A tool"}],
            mcp_tool_schemas_hash="xyz789uvw012",
        )

        # Serialize and deserialize
        json_str = result.model_dump_json()
        loaded = TestRunResult.model_validate_json(json_str)

        assert loaded.agent_system_prompt == "You are a test assistant."
        assert loaded.agent_system_prompt_hash == "abc123def456"
        assert loaded.mcp_tool_schemas == [{"name": "tool1", "description": "A tool"}]
        assert loaded.mcp_tool_schemas_hash == "xyz789uvw012"

    def test_result_without_prompt_backward_compatible(self) -> None:
        """Result without new fields is backward compatible."""
        import time
        from datetime import datetime

        from mcprobe.models.conversation import (
            ConversationResult,
            ConversationTurn,
            TerminationReason,
        )
        from mcprobe.models.judgment import JudgmentResult
        from mcprobe.persistence import TestRunResult

        # Create result without new fields (simulating old data)
        result = TestRunResult(
            run_id="test-456",
            timestamp=datetime.now(),
            scenario_name="Old Scenario",
            scenario_file="/path/to/old.yaml",
            conversation_result=ConversationResult(
                turns=[ConversationTurn(role="user", content="Hi", timestamp=time.time())],
                final_answer="Hello!",
                total_tool_calls=[],
                total_tokens=5,
                duration_seconds=0.5,
                termination_reason=TerminationReason.USER_SATISFIED,
            ),
            judgment_result=JudgmentResult(
                passed=True,
                score=1.0,
                correctness_results={},
                failure_results={},
                tool_usage_results={
                    "required_tools": [],
                    "required_tools_used": [],
                    "prohibited_tools": [],
                    "prohibited_tools_used": [],
                    "all_required_used": True,
                    "no_prohibited_used": True,
                    "criteria_results": {},
                },
                efficiency_results={
                    "total_tool_calls": 0,
                    "max_tool_calls": 10,
                    "total_turns": 1,
                    "max_turns": 5,
                    "within_limits": True,
                    "total_tokens": 5,
                },
                reasoning="Passed",
            ),
            agent_type="simple",
            judge_model="old-model",
            synthetic_user_model="old-model",
            agent_model="old-model",
            duration_seconds=0.5,
            mcprobe_version="0.0.1",
            python_version="3.11.0",
            # New fields not provided - should use defaults
        )

        assert result.agent_system_prompt is None
        assert result.agent_system_prompt_hash is None
        assert result.mcp_tool_schemas == []
        assert result.mcp_tool_schemas_hash is None


class TestMCPServerConfig:
    """Tests for MCPServerConfig model."""

    def test_command_only(self) -> None:
        """Config with only command set."""
        config = MCPServerConfig(command="npx @example/mcp-server")

        assert config.command == "npx @example/mcp-server"
        assert config.url is None
        assert config.headers is None

    def test_url_only(self) -> None:
        """Config with only URL set."""
        config = MCPServerConfig(url="http://localhost:8080/mcp")

        assert config.command is None
        assert config.url == "http://localhost:8080/mcp"
        assert config.headers is None

    def test_url_with_headers(self) -> None:
        """Config with URL and authentication headers."""
        config = MCPServerConfig(
            url="http://localhost:8080/mcp",
            headers={"Authorization": "Bearer test-token"},
        )

        assert config.url == "http://localhost:8080/mcp"
        assert config.headers == {"Authorization": "Bearer test-token"}

    def test_both_command_and_url(self) -> None:
        """Config with both command and URL (command takes precedence in code)."""
        config = MCPServerConfig(
            command="npx @example/mcp-server",
            url="http://localhost:8080/mcp",
        )

        assert config.command == "npx @example/mcp-server"
        assert config.url == "http://localhost:8080/mcp"

    def test_neither_set(self) -> None:
        """Config with neither set."""
        config = MCPServerConfig()

        assert config.command is None
        assert config.url is None
        assert config.headers is None


class TestFileConfigWithMCPServer:
    """Tests for FileConfig with mcp_server field."""

    def test_file_config_with_mcp_server(self) -> None:
        """FileConfig correctly includes mcp_server."""
        config = FileConfig(
            mcp_server=MCPServerConfig(command="npx @example/mcp")
        )

        assert config.mcp_server is not None
        assert config.mcp_server.command == "npx @example/mcp"

    def test_file_config_without_mcp_server(self) -> None:
        """FileConfig works without mcp_server (default None)."""
        config = FileConfig()

        assert config.mcp_server is None

    def test_load_config_with_mcp_server_command(self, tmp_path: Path) -> None:
        """Config file with mcp_server command is parsed."""
        from mcprobe.config import ConfigLoader

        config_file = tmp_path / "mcprobe.yaml"
        config_file.write_text(
            "mcp_server:\n"
            "  command: npx @example/weather-mcp\n"
        )

        result = ConfigLoader.load_config(config_file)

        assert result is not None
        assert result.mcp_server is not None
        assert result.mcp_server.command == "npx @example/weather-mcp"
        assert result.mcp_server.url is None

    def test_load_config_with_mcp_server_url(self, tmp_path: Path) -> None:
        """Config file with mcp_server url is parsed."""
        from mcprobe.config import ConfigLoader

        config_file = tmp_path / "mcprobe.yaml"
        config_file.write_text(
            "mcp_server:\n"
            "  url: http://localhost:8080/mcp\n"
        )

        result = ConfigLoader.load_config(config_file)

        assert result is not None
        assert result.mcp_server is not None
        assert result.mcp_server.command is None
        assert result.mcp_server.url == "http://localhost:8080/mcp"

    def test_load_config_with_mcp_server_headers(self, tmp_path: Path) -> None:
        """Config file with mcp_server headers is parsed."""
        from mcprobe.config import ConfigLoader

        config_file = tmp_path / "mcprobe.yaml"
        config_file.write_text(
            "mcp_server:\n"
            "  url: http://localhost:8080/mcp\n"
            "  headers:\n"
            "    Authorization: Bearer test-token\n"
            "    X-Custom-Header: custom-value\n"
        )

        result = ConfigLoader.load_config(config_file)

        assert result is not None
        assert result.mcp_server is not None
        assert result.mcp_server.url == "http://localhost:8080/mcp"
        assert result.mcp_server.headers == {
            "Authorization": "Bearer test-token",
            "X-Custom-Header": "custom-value",
        }


class TestHtmlGeneratorChangeBadges:
    """Tests for change detection badges in HTML generator."""

    def test_build_change_badges_prompt_changed(self) -> None:
        """Badge shown when prompt changed."""
        from mcprobe.reporting.html_generator import HtmlReportGenerator

        generator = HtmlReportGenerator()
        result = generator._build_change_badges(prompt_changed=True, schema_changed=False)

        assert "Prompt Changed" in result
        assert "prompt-changed" in result
        assert "Schema Changed" not in result

    def test_build_change_badges_schema_changed(self) -> None:
        """Badge shown when schema changed."""
        from mcprobe.reporting.html_generator import HtmlReportGenerator

        generator = HtmlReportGenerator()
        result = generator._build_change_badges(prompt_changed=False, schema_changed=True)

        assert "Schema Changed" in result
        assert "schema-changed" in result
        assert "Prompt Changed" not in result

    def test_build_change_badges_both_changed(self) -> None:
        """Both badges shown when both changed."""
        from mcprobe.reporting.html_generator import HtmlReportGenerator

        generator = HtmlReportGenerator()
        result = generator._build_change_badges(prompt_changed=True, schema_changed=True)

        assert "Prompt Changed" in result
        assert "Schema Changed" in result

    def test_build_change_badges_no_changes(self) -> None:
        """Empty string when no changes."""
        from mcprobe.reporting.html_generator import HtmlReportGenerator

        generator = HtmlReportGenerator()
        result = generator._build_change_badges(prompt_changed=False, schema_changed=False)

        assert result == ""


class TestHtmlGeneratorHashBadges:
    """Tests for hash badges in HTML generator."""

    def test_build_hash_badges_with_prompt_hash(self) -> None:
        """Badge shown when prompt hash provided."""
        from mcprobe.reporting.html_generator import HtmlReportGenerator

        generator = HtmlReportGenerator()
        result = generator._build_hash_badges(
            prompt_hash="abc123def456", schema_hash=None
        )

        assert "Prompt:" in result
        assert "abc123de" in result  # First 8 chars of hash
        assert "hash-badge" in result
        assert "Schema:" not in result

    def test_build_hash_badges_with_schema_hash(self) -> None:
        """Badge shown when schema hash provided."""
        from mcprobe.reporting.html_generator import HtmlReportGenerator

        generator = HtmlReportGenerator()
        result = generator._build_hash_badges(
            prompt_hash=None, schema_hash="xyz789uvw012"
        )

        assert "Schema:" in result
        assert "xyz789uv" in result  # First 8 chars of hash
        assert "hash-badge" in result
        assert "Prompt:" not in result

    def test_build_hash_badges_with_both_hashes(self) -> None:
        """Both badges shown when both hashes provided."""
        from mcprobe.reporting.html_generator import HtmlReportGenerator

        generator = HtmlReportGenerator()
        result = generator._build_hash_badges(
            prompt_hash="abc123def456", schema_hash="xyz789uvw012"
        )

        assert "Prompt:" in result
        assert "Schema:" in result
        assert "abc123de" in result
        assert "xyz789uv" in result

    def test_build_hash_badges_no_hashes(self) -> None:
        """Empty string when no hashes provided."""
        from mcprobe.reporting.html_generator import HtmlReportGenerator

        generator = HtmlReportGenerator()
        result = generator._build_hash_badges(prompt_hash=None, schema_hash=None)

        assert result == ""


class TestHtmlGeneratorConfigDetails:
    """Tests for config details section in HTML generator."""

    def test_build_config_details_with_prompt(self) -> None:
        """Config details shows system prompt when present."""
        import time
        from datetime import datetime

        from mcprobe.models.conversation import (
            ConversationResult,
            ConversationTurn,
            TerminationReason,
        )
        from mcprobe.models.judgment import JudgmentResult
        from mcprobe.persistence import TestRunResult
        from mcprobe.reporting.html_generator import HtmlReportGenerator

        result = TestRunResult(
            run_id="test-123",
            timestamp=datetime.now(),
            scenario_name="Test Scenario",
            scenario_file="/path/to/scenario.yaml",
            conversation_result=ConversationResult(
                turns=[ConversationTurn(role="user", content="Hello", timestamp=time.time())],
                final_answer="Hi!",
                total_tool_calls=[],
                total_tokens=10,
                duration_seconds=1.0,
                termination_reason=TerminationReason.USER_SATISFIED,
            ),
            judgment_result=JudgmentResult(
                passed=True,
                score=1.0,
                correctness_results={},
                failure_results={},
                tool_usage_results={
                    "required_tools": [],
                    "required_tools_used": [],
                    "prohibited_tools": [],
                    "prohibited_tools_used": [],
                    "all_required_used": True,
                    "no_prohibited_used": True,
                    "criteria_results": {},
                },
                efficiency_results={
                    "total_tool_calls": 0,
                    "max_tool_calls": 10,
                    "total_turns": 1,
                    "max_turns": 5,
                    "within_limits": True,
                    "total_tokens": 10,
                },
                reasoning="Test passed",
            ),
            agent_type="simple",
            judge_model="test-model",
            synthetic_user_model="test-model",
            agent_model="test-model",
            duration_seconds=1.0,
            mcprobe_version="0.1.0",
            python_version="3.12.0",
            agent_system_prompt="You are a helpful assistant.",
            agent_system_prompt_hash="abc123",
            mcp_tool_schemas=[],
            mcp_tool_schemas_hash=None,
        )

        generator = HtmlReportGenerator()
        html = generator._build_config_details_html(result)

        assert "System Prompt" in html
        assert "You are a helpful assistant." in html
        assert "config-details" in html

    def test_build_config_details_with_schemas(self) -> None:
        """Config details shows tool schemas when present."""
        import time
        from datetime import datetime

        from mcprobe.models.conversation import (
            ConversationResult,
            ConversationTurn,
            TerminationReason,
        )
        from mcprobe.models.judgment import JudgmentResult
        from mcprobe.persistence import TestRunResult
        from mcprobe.reporting.html_generator import HtmlReportGenerator

        result = TestRunResult(
            run_id="test-456",
            timestamp=datetime.now(),
            scenario_name="Test Scenario",
            scenario_file="/path/to/scenario.yaml",
            conversation_result=ConversationResult(
                turns=[ConversationTurn(role="user", content="Hello", timestamp=time.time())],
                final_answer="Hi!",
                total_tool_calls=[],
                total_tokens=10,
                duration_seconds=1.0,
                termination_reason=TerminationReason.USER_SATISFIED,
            ),
            judgment_result=JudgmentResult(
                passed=True,
                score=1.0,
                correctness_results={},
                failure_results={},
                tool_usage_results={
                    "required_tools": [],
                    "required_tools_used": [],
                    "prohibited_tools": [],
                    "prohibited_tools_used": [],
                    "all_required_used": True,
                    "no_prohibited_used": True,
                    "criteria_results": {},
                },
                efficiency_results={
                    "total_tool_calls": 0,
                    "max_tool_calls": 10,
                    "total_turns": 1,
                    "max_turns": 5,
                    "within_limits": True,
                    "total_tokens": 10,
                },
                reasoning="Test passed",
            ),
            agent_type="simple",
            judge_model="test-model",
            synthetic_user_model="test-model",
            agent_model="test-model",
            duration_seconds=1.0,
            mcprobe_version="0.1.0",
            python_version="3.12.0",
            agent_system_prompt=None,
            agent_system_prompt_hash=None,
            mcp_tool_schemas=[
                {
                    "name": "get_weather",
                    "description": "Get weather for a location",
                    "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}},
                }
            ],
            mcp_tool_schemas_hash="xyz789",
        )

        generator = HtmlReportGenerator()
        html = generator._build_config_details_html(result)

        assert "MCP Tool Schemas (1)" in html
        assert "get_weather" in html
        assert "Get weather for a location" in html
        assert "tool-schema-item" in html

    def test_build_config_details_no_data(self) -> None:
        """Config details shows 'no data' messages when empty."""
        import time
        from datetime import datetime

        from mcprobe.models.conversation import (
            ConversationResult,
            ConversationTurn,
            TerminationReason,
        )
        from mcprobe.models.judgment import JudgmentResult
        from mcprobe.persistence import TestRunResult
        from mcprobe.reporting.html_generator import HtmlReportGenerator

        result = TestRunResult(
            run_id="test-789",
            timestamp=datetime.now(),
            scenario_name="Test Scenario",
            scenario_file="/path/to/scenario.yaml",
            conversation_result=ConversationResult(
                turns=[ConversationTurn(role="user", content="Hello", timestamp=time.time())],
                final_answer="Hi!",
                total_tool_calls=[],
                total_tokens=10,
                duration_seconds=1.0,
                termination_reason=TerminationReason.USER_SATISFIED,
            ),
            judgment_result=JudgmentResult(
                passed=True,
                score=1.0,
                correctness_results={},
                failure_results={},
                tool_usage_results={
                    "required_tools": [],
                    "required_tools_used": [],
                    "prohibited_tools": [],
                    "prohibited_tools_used": [],
                    "all_required_used": True,
                    "no_prohibited_used": True,
                    "criteria_results": {},
                },
                efficiency_results={
                    "total_tool_calls": 0,
                    "max_tool_calls": 10,
                    "total_turns": 1,
                    "max_turns": 5,
                    "within_limits": True,
                    "total_tokens": 10,
                },
                reasoning="Test passed",
            ),
            agent_type="simple",
            judge_model="test-model",
            synthetic_user_model="test-model",
            agent_model="test-model",
            duration_seconds=1.0,
            mcprobe_version="0.1.0",
            python_version="3.12.0",
        )

        generator = HtmlReportGenerator()
        html = generator._build_config_details_html(result)

        assert "No system prompt captured" in html
        assert "No MCP tool schemas captured" in html


class TestHumanizeCriterion:
    """Tests for _humanize_criterion helper function."""

    def test_snake_case_to_human_readable(self) -> None:
        """Converts snake_case to human readable format."""
        from mcprobe.reporting.html_generator import _humanize_criterion

        result = _humanize_criterion("correct_temperature_returned")
        assert result == "Correct temperature returned"

    def test_single_word(self) -> None:
        """Single word is capitalized."""
        from mcprobe.reporting.html_generator import _humanize_criterion

        result = _humanize_criterion("passed")
        assert result == "Passed"

    def test_already_capitalized(self) -> None:
        """Already capitalized word stays capitalized."""
        from mcprobe.reporting.html_generator import _humanize_criterion

        result = _humanize_criterion("Valid_response")
        assert result == "Valid response"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        from mcprobe.reporting.html_generator import _humanize_criterion

        result = _humanize_criterion("")
        assert result == ""

    def test_multiple_underscores(self) -> None:
        """Multiple underscores are all converted to spaces."""
        from mcprobe.reporting.html_generator import _humanize_criterion

        result = _humanize_criterion("has_valid_api_response")
        assert result == "Has valid api response"
