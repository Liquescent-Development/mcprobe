"""Tests for configuration file loader."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from mcprobe.config import (
    AgentConfig,
    CLIOverrides,
    ConfigLoader,
    FileConfig,
    FileLLMConfigOverride,
    ResultsConfig,
)
from mcprobe.exceptions import ConfigurationError
from mcprobe.models.config import LLMConfig, OrchestratorConfig


class TestConfigFileDiscovery:
    """Tests for config file discovery."""

    def test_discover_explicit_path(self, tmp_path: Path) -> None:
        """Uses provided explicit path."""
        config_file = tmp_path / "custom-config.yaml"
        config_file.write_text("llm:\n  provider: openai\n  model: gpt-4\n")

        result = ConfigLoader.discover_config_file(config_file)
        assert result == config_file

    def test_discover_explicit_path_not_found_raises(self, tmp_path: Path) -> None:
        """Raises ConfigurationError for missing explicit path."""
        missing_file = tmp_path / "missing.yaml"

        with pytest.raises(ConfigurationError) as exc_info:
            ConfigLoader.discover_config_file(missing_file)
        assert "not found" in str(exc_info.value)

    def test_discover_mcprobe_yaml(self, tmp_path: Path) -> None:
        """Finds mcprobe.yaml in current directory."""
        config_file = tmp_path / "mcprobe.yaml"
        config_file.write_text("llm:\n  provider: ollama\n  model: llama3.2\n")

        with patch.object(Path, "cwd", return_value=tmp_path):
            result = ConfigLoader.discover_config_file()
        assert result == config_file

    def test_discover_dot_mcprobe_yaml(self, tmp_path: Path) -> None:
        """Finds .mcprobe.yaml in current directory."""
        config_file = tmp_path / ".mcprobe.yaml"
        config_file.write_text("llm:\n  provider: ollama\n  model: llama3.2\n")

        with patch.object(Path, "cwd", return_value=tmp_path):
            result = ConfigLoader.discover_config_file()
        assert result == config_file

    def test_discover_priority_mcprobe_over_dot(self, tmp_path: Path) -> None:
        """mcprobe.yaml takes priority over .mcprobe.yaml."""
        (tmp_path / "mcprobe.yaml").write_text("llm:\n  model: gpt-4\n")
        (tmp_path / ".mcprobe.yaml").write_text("llm:\n  model: llama3.2\n")

        with patch.object(Path, "cwd", return_value=tmp_path):
            result = ConfigLoader.discover_config_file()
        assert result == tmp_path / "mcprobe.yaml"

    def test_discover_none_when_no_file(self, tmp_path: Path) -> None:
        """Returns None when no config file found (silent)."""
        with patch.object(Path, "cwd", return_value=tmp_path):
            result = ConfigLoader.discover_config_file()
        assert result is None


class TestYamlLoading:
    """Tests for YAML file loading."""

    def test_load_valid_yaml(self, tmp_path: Path) -> None:
        """Parses valid YAML config file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "llm:\n"
            "  provider: openai\n"
            "  model: gpt-4\n"
            "orchestrator:\n"
            "  max_turns: 5\n"
        )

        result = ConfigLoader.load_yaml(config_file)
        assert result["llm"]["provider"] == "openai"
        assert result["llm"]["model"] == "gpt-4"
        assert result["orchestrator"]["max_turns"] == 5

    def test_load_empty_yaml_returns_empty_dict(self, tmp_path: Path) -> None:
        """Empty YAML file returns empty dict."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        result = ConfigLoader.load_yaml(config_file)
        assert result == {}

    def test_load_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Invalid YAML raises ConfigurationError."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content:")

        with pytest.raises(ConfigurationError) as exc_info:
            ConfigLoader.load_yaml(config_file)
        assert "Failed to parse" in str(exc_info.value)

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        """Missing file raises ConfigurationError."""
        missing_file = tmp_path / "missing.yaml"

        with pytest.raises(ConfigurationError) as exc_info:
            ConfigLoader.load_yaml(missing_file)
        assert "Failed to read" in str(exc_info.value)


class TestEnvironmentInterpolation:
    """Tests for environment variable interpolation."""

    def test_interpolate_simple_var(self) -> None:
        """${VAR} is replaced with environment value."""
        with patch.dict(os.environ, {"MY_API_KEY": "secret123"}):
            result = ConfigLoader.interpolate_env_vars("${MY_API_KEY}")
        assert result == "secret123"

    def test_interpolate_with_default_uses_default(self) -> None:
        """${VAR:-default} uses default when var is not set."""
        # Make sure the variable is not set
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MISSING_VAR", None)
            result = ConfigLoader.interpolate_env_vars("${MISSING_VAR:-fallback}")
        assert result == "fallback"

    def test_interpolate_with_default_uses_env_when_set(self) -> None:
        """${VAR:-default} uses env var value when set."""
        with patch.dict(os.environ, {"MY_VAR": "actual_value"}):
            result = ConfigLoader.interpolate_env_vars("${MY_VAR:-default}")
        assert result == "actual_value"

    def test_interpolate_empty_default(self) -> None:
        """${VAR:-} allows empty string as default."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MISSING_VAR", None)
            result = ConfigLoader.interpolate_env_vars("${MISSING_VAR:-}")
        assert result == ""

    def test_interpolate_nested_dict(self) -> None:
        """Interpolates variables in nested structures."""
        with patch.dict(os.environ, {"API_KEY": "key123", "BASE_URL": "http://api.example.com"}):
            config = {
                "llm": {
                    "api_key": "${API_KEY}",
                    "base_url": "${BASE_URL}",
                }
            }
            result = ConfigLoader.interpolate_env_vars(config)
        assert result["llm"]["api_key"] == "key123"
        assert result["llm"]["base_url"] == "http://api.example.com"

    def test_interpolate_list(self) -> None:
        """Interpolates variables in lists."""
        with patch.dict(os.environ, {"VAR1": "value1", "VAR2": "value2"}):
            config = ["${VAR1}", "${VAR2}"]
            result = ConfigLoader.interpolate_env_vars(config)
        assert result == ["value1", "value2"]

    def test_interpolate_missing_var_raises(self) -> None:
        """Raises ConfigurationError for undefined variable without default."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("UNDEFINED_VAR", None)
            with pytest.raises(ConfigurationError) as exc_info:
                ConfigLoader.interpolate_env_vars("${UNDEFINED_VAR}")
        assert "UNDEFINED_VAR" in str(exc_info.value)
        assert "not set" in str(exc_info.value)

    def test_interpolate_no_vars_unchanged(self) -> None:
        """Strings without variables pass through unchanged."""
        result = ConfigLoader.interpolate_env_vars("plain string without vars")
        assert result == "plain string without vars"

    def test_interpolate_non_string_types_unchanged(self) -> None:
        """Non-string types pass through unchanged."""
        assert ConfigLoader.interpolate_env_vars(42) == 42
        assert ConfigLoader.interpolate_env_vars(3.14) == 3.14
        assert ConfigLoader.interpolate_env_vars(True) is True
        assert ConfigLoader.interpolate_env_vars(None) is None

    def test_interpolate_mixed_content(self) -> None:
        """Interpolates variables embedded in larger strings."""
        with patch.dict(os.environ, {"HOST": "localhost", "PORT": "8080"}):
            result = ConfigLoader.interpolate_env_vars("http://${HOST}:${PORT}/api")
        assert result == "http://localhost:8080/api"


class TestLoadConfig:
    """Tests for full config loading."""

    def test_load_config_returns_file_config(self, tmp_path: Path) -> None:
        """Returns validated FileConfig object."""
        config_file = tmp_path / "mcprobe.yaml"
        config_file.write_text(
            "llm:\n"
            "  provider: openai\n"
            "  model: gpt-4\n"
            "  temperature: 0.5\n"
        )

        result = ConfigLoader.load_config(config_file)
        assert isinstance(result, FileConfig)
        assert result.llm is not None
        assert result.llm.provider == "openai"
        assert result.llm.model == "gpt-4"
        assert result.llm.temperature == 0.5

    def test_load_config_with_env_vars(self, tmp_path: Path) -> None:
        """Environment variables are interpolated."""
        config_file = tmp_path / "mcprobe.yaml"
        config_file.write_text(
            "llm:\n"
            "  provider: openai\n"
            "  model: gpt-4\n"
            "  api_key: ${TEST_API_KEY}\n"
        )

        with patch.dict(os.environ, {"TEST_API_KEY": "secret_key"}):
            result = ConfigLoader.load_config(config_file)

        assert result is not None
        assert result.llm is not None
        assert result.llm.api_key is not None
        assert result.llm.api_key.get_secret_value() == "secret_key"

    def test_load_config_returns_none_when_not_found(self, tmp_path: Path) -> None:
        """Returns None when no config file found."""
        with patch.object(Path, "cwd", return_value=tmp_path):
            result = ConfigLoader.load_config()
        assert result is None

    def test_load_config_invalid_schema_raises(self, tmp_path: Path) -> None:
        """Raises ConfigurationError for invalid config schema."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text(
            "llm:\n"
            "  provider: invalid_provider\n"
            "  model: 123\n"  # Invalid: model should be string
            "  temperature: 'not_a_number'\n"
        )

        with pytest.raises(ConfigurationError) as exc_info:
            ConfigLoader.load_config(config_file)
        assert "Invalid configuration" in str(exc_info.value)


class TestResolveLLMConfig:
    """Tests for LLM config resolution with priority."""

    def test_defaults_when_no_config(self) -> None:
        """Returns defaults when no config file."""
        result = ConfigLoader.resolve_llm_config(None, "judge")

        assert result.provider == "ollama"
        assert result.model == "llama3.2"
        assert result.temperature == 0.0
        assert result.max_tokens == 4096

    def test_shared_llm_config_used(self) -> None:
        """Shared llm config is used when component-specific not provided."""
        file_config = FileConfig(
            llm=LLMConfig(provider="openai", model="gpt-4", temperature=0.7)
        )

        result = ConfigLoader.resolve_llm_config(file_config, "judge")

        assert result.provider == "openai"
        assert result.model == "gpt-4"
        assert result.temperature == 0.7

    def test_component_overrides_shared(self) -> None:
        """Component-specific config overrides shared llm config."""
        file_config = FileConfig(
            llm=LLMConfig(provider="openai", model="gpt-4"),
            judge=FileLLMConfigOverride(model="gpt-4o"),
        )

        result = ConfigLoader.resolve_llm_config(file_config, "judge")

        assert result.model == "gpt-4o"
        assert result.provider == "openai"  # Inherited from shared llm

    def test_cli_overrides_file_config(self) -> None:
        """CLI arguments override file config."""
        file_config = FileConfig(
            llm=LLMConfig(provider="openai", model="gpt-4")
        )
        cli_overrides = CLIOverrides(model="gpt-3.5-turbo")

        result = ConfigLoader.resolve_llm_config(file_config, "judge", cli_overrides)

        assert result.model == "gpt-3.5-turbo"
        assert result.provider == "openai"  # From file config

    def test_cli_overrides_all_fields(self) -> None:
        """CLI can override all fields."""
        file_config = FileConfig(
            llm=LLMConfig(provider="openai", model="gpt-4")
        )
        cli_overrides = CLIOverrides(
            provider="ollama",
            model="llama3.2",
            base_url="http://localhost:11434",
            temperature=0.5,
            max_tokens=2048,
            api_key="cli-key",
        )

        result = ConfigLoader.resolve_llm_config(file_config, "judge", cli_overrides)

        assert result.provider == "ollama"
        assert result.model == "llama3.2"
        assert result.base_url == "http://localhost:11434"
        assert result.temperature == 0.5
        assert result.max_tokens == 2048
        assert result.api_key is not None
        assert result.api_key.get_secret_value() == "cli-key"

    def test_different_components_can_have_different_configs(self) -> None:
        """Judge and synthetic_user can have different configurations."""
        file_config = FileConfig(
            llm=LLMConfig(provider="openai", model="gpt-4"),
            judge=FileLLMConfigOverride(model="gpt-4o"),
            synthetic_user=FileLLMConfigOverride(provider="ollama", model="llama3.2"),
        )

        judge_config = ConfigLoader.resolve_llm_config(file_config, "judge")
        user_config = ConfigLoader.resolve_llm_config(file_config, "synthetic_user")

        assert judge_config.provider == "openai"  # Inherited from shared llm
        assert judge_config.model == "gpt-4o"
        assert user_config.provider == "ollama"
        assert user_config.model == "llama3.2"

    def test_api_key_from_file_config(self) -> None:
        """API key from file config is used."""
        file_config = FileConfig(
            llm=LLMConfig(
                provider="openai",
                model="gpt-4",
                api_key=SecretStr("file-api-key"),
            )
        )

        result = ConfigLoader.resolve_llm_config(file_config, "judge")

        assert result.api_key is not None
        assert result.api_key.get_secret_value() == "file-api-key"


class TestResolveOrchestratorConfig:
    """Tests for orchestrator config resolution."""

    def test_defaults_when_no_config(self) -> None:
        """Returns defaults when no config file."""
        result = ConfigLoader.resolve_orchestrator_config(None)

        assert result.max_turns == 10
        assert result.turn_timeout_seconds == 30.0
        assert result.loop_detection_threshold == 3

    def test_file_config_used(self) -> None:
        """File config values are used."""
        file_config = FileConfig(
            orchestrator=OrchestratorConfig(
                max_turns=20,
                turn_timeout_seconds=60.0,
                loop_detection_threshold=5,
            )
        )

        result = ConfigLoader.resolve_orchestrator_config(file_config)

        assert result.max_turns == 20
        assert result.turn_timeout_seconds == 60.0
        assert result.loop_detection_threshold == 5

    def test_cli_overrides_file_config(self) -> None:
        """CLI arguments override file config."""
        file_config = FileConfig(
            orchestrator=OrchestratorConfig(max_turns=20, turn_timeout_seconds=60.0)
        )

        result = ConfigLoader.resolve_orchestrator_config(
            file_config, cli_max_turns=5, cli_timeout=15.0
        )

        assert result.max_turns == 5
        assert result.turn_timeout_seconds == 15.0


class TestResolveResultsConfig:
    """Tests for results config resolution."""

    def test_defaults_when_no_config(self) -> None:
        """Returns defaults when no config file."""
        result = ConfigLoader.resolve_results_config(None)

        assert result.save is True
        assert result.dir == "test-results"

    def test_file_config_used(self) -> None:
        """File config values are used."""
        file_config = FileConfig(
            results=ResultsConfig(save=False, dir="custom-results")
        )

        result = ConfigLoader.resolve_results_config(file_config)

        assert result.save is False
        assert result.dir == "custom-results"

    def test_cli_overrides_file_config(self) -> None:
        """CLI arguments override file config."""
        file_config = FileConfig(
            results=ResultsConfig(save=True, dir="file-results")
        )

        result = ConfigLoader.resolve_results_config(
            file_config, cli_save=False, cli_dir="cli-results"
        )

        assert result.save is False
        assert result.dir == "cli-results"


class TestResolveAgentConfig:
    """Tests for agent config resolution."""

    def test_defaults_when_no_config(self) -> None:
        """Returns defaults when no config file."""
        result = ConfigLoader.resolve_agent_config(None)

        assert result.type == "simple"
        assert result.factory is None

    def test_file_config_used(self) -> None:
        """File config values are used."""
        file_config = FileConfig(
            agent=AgentConfig(type="adk", factory="path/to/agent.py")
        )

        result = ConfigLoader.resolve_agent_config(file_config)

        assert result.type == "adk"
        assert result.factory == "path/to/agent.py"

    def test_cli_overrides_file_config(self) -> None:
        """CLI arguments override file config."""
        file_config = FileConfig(
            agent=AgentConfig(type="simple", factory=None)
        )

        result = ConfigLoader.resolve_agent_config(
            file_config,
            cli_agent_type="adk",
            cli_agent_factory="cli/agent.py",
        )

        assert result.type == "adk"
        assert result.factory == "cli/agent.py"

    def test_partial_cli_override(self) -> None:
        """CLI can override individual fields."""
        file_config = FileConfig(
            agent=AgentConfig(type="adk", factory="config/agent.py")
        )

        # Only override factory, keep type from config
        result = ConfigLoader.resolve_agent_config(
            file_config,
            cli_agent_factory="cli/agent.py",
        )

        assert result.type == "adk"  # From config
        assert result.factory == "cli/agent.py"  # From CLI

    def test_simple_agent_no_factory_required(self) -> None:
        """Simple agent type doesn't require factory."""
        result = ConfigLoader.resolve_agent_config(
            None,
            cli_agent_type="simple",
        )

        assert result.type == "simple"
        assert result.factory is None


class TestFullIntegration:
    """Integration tests for end-to-end config loading."""

    def test_full_config_file_loading(self, tmp_path: Path) -> None:
        """Full config file is loaded and resolved correctly."""
        config_file = tmp_path / "mcprobe.yaml"
        config_file.write_text(
            "agent:\n"
            "  type: adk\n"
            "  factory: my_agent.py\n"
            "\n"
            "llm:\n"
            "  provider: openai\n"
            "  model: gpt-4\n"
            "  base_url: ${API_URL:-https://api.openai.com/v1}\n"
            "  api_key: ${OPENAI_API_KEY}\n"
            "  temperature: 0.0\n"
            "  max_tokens: 4096\n"
            "\n"
            "judge:\n"
            "  provider: openai\n"
            "  model: gpt-4o\n"
            "\n"
            "synthetic_user:\n"
            "  provider: ollama\n"
            "  model: llama3.2\n"
            "  base_url: http://localhost:11434\n"
            "\n"
            "orchestrator:\n"
            "  max_turns: 15\n"
            "  turn_timeout_seconds: 45.0\n"
            "\n"
            "results:\n"
            "  save: true\n"
            "  dir: my-test-results\n"
        )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}):
            file_config = ConfigLoader.load_config(config_file)

        assert file_config is not None

        # Resolve agent config - should use agent settings
        agent_config = ConfigLoader.resolve_agent_config(file_config)
        assert agent_config.type == "adk"
        assert agent_config.factory == "my_agent.py"

        # Resolve judge config - should use judge-specific settings
        judge_config = ConfigLoader.resolve_llm_config(file_config, "judge")
        assert judge_config.provider == "openai"
        assert judge_config.model == "gpt-4o"
        assert judge_config.api_key is not None
        assert judge_config.api_key.get_secret_value() == "test-key-123"

        # Resolve synthetic_user config - should use synthetic_user-specific settings
        user_config = ConfigLoader.resolve_llm_config(file_config, "synthetic_user")
        assert user_config.provider == "ollama"
        assert user_config.model == "llama3.2"
        assert user_config.base_url == "http://localhost:11434"

        # Resolve orchestrator config
        orch_config = ConfigLoader.resolve_orchestrator_config(file_config)
        assert orch_config.max_turns == 15
        assert orch_config.turn_timeout_seconds == 45.0

        # Resolve results config
        results_config = ConfigLoader.resolve_results_config(file_config)
        assert results_config.save is True
        assert results_config.dir == "my-test-results"
