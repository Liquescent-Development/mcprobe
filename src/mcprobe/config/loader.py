"""Configuration file loader.

Handles discovery, parsing, and merging of YAML configuration files.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, SecretStr

from mcprobe.exceptions import ConfigurationError
from mcprobe.models.config import LLMConfig, OrchestratorConfig


@dataclass
class _ResolvedValues:
    """Internal dataclass to hold resolved configuration values during merging."""

    provider: str
    model: str
    temperature: float
    max_tokens: int
    base_url: str | None
    api_key: str | None
    context_size: int | None
    reasoning: Literal["low", "medium", "high"] | None

# Pattern matches ${VAR} or ${VAR:-default}
ENV_VAR_PATTERN = re.compile(r"\$\{([^}:-]+)(?::-([^}]*))?\}")

# Default config file names in priority order
CONFIG_FILE_NAMES = ["mcprobe.yaml", ".mcprobe.yaml", "mcprobe.yml", ".mcprobe.yml"]


class AgentConfig(BaseModel):
    """Configuration for the agent under test."""

    type: str = "simple"
    factory: str | None = None


class ResultsConfig(BaseModel):
    """Configuration for test result storage."""

    save: bool = True
    dir: str = "test-results"


class MCPServerConfig(BaseModel):
    """Configuration for MCP server connection.

    Used to extract tool schemas directly from the MCP server for tracking
    changes that may affect agent performance.

    Supports two connection methods:
    - stdio: Command-based connection (e.g., "npx @example/weather-mcp")
    - HTTP: URL-based connection (e.g., "http://localhost:8080/mcp")
    """

    # Stdio connection (command-based)
    command: str | None = None

    # HTTP connection (URL-based)
    url: str | None = None

    # Optional headers for HTTP connections (e.g., for authentication)
    headers: dict[str, str] | None = None


class CLIOverrides(BaseModel):
    """CLI argument overrides for configuration.

    All fields are optional - only set values will override config file settings.
    """

    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class FileConfig(BaseModel):
    """Schema for mcprobe.yaml configuration file."""

    agent: AgentConfig = Field(default_factory=AgentConfig)
    llm: LLMConfig | None = None
    judge: LLMConfig | None = None
    synthetic_user: LLMConfig | None = None
    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
    results: ResultsConfig = Field(default_factory=ResultsConfig)
    mcp_server: MCPServerConfig | None = None


class ConfigLoader:
    """Load and merge configuration from files and CLI arguments."""

    @staticmethod
    def discover_config_file(explicit_path: Path | None = None) -> Path | None:
        """Find configuration file in priority order.

        Args:
            explicit_path: Explicitly provided config file path.

        Returns:
            Path to config file, or None if not found.

        Raises:
            ConfigurationError: If explicit path doesn't exist.
        """
        # 1. Use explicit path if provided
        if explicit_path is not None:
            if not explicit_path.exists():
                msg = f"Configuration file not found: {explicit_path}"
                raise ConfigurationError(msg)
            return explicit_path

        # 2. Search in current directory
        cwd = Path.cwd()
        for filename in CONFIG_FILE_NAMES:
            config_path = cwd / filename
            if config_path.exists():
                return config_path

        # 3. No config file found (silent, no warning)
        return None

    @staticmethod
    def load_yaml(path: Path) -> dict[str, Any]:
        """Load and parse YAML configuration file.

        Args:
            path: Path to YAML file.

        Returns:
            Parsed configuration dictionary.

        Raises:
            ConfigurationError: If file cannot be read or parsed.
        """
        try:
            with path.open() as f:
                content = yaml.safe_load(f)
                return content if content is not None else {}
        except yaml.YAMLError as e:
            msg = f"Failed to parse configuration file {path}: {e}"
            raise ConfigurationError(msg) from e
        except OSError as e:
            msg = f"Failed to read configuration file {path}: {e}"
            raise ConfigurationError(msg) from e

    @staticmethod
    def interpolate_env_vars(value: Any) -> Any:
        """Recursively interpolate environment variables in configuration.

        Supports two syntaxes:
        - ${VAR} - Required variable, raises error if not set
        - ${VAR:-default} - Optional variable with default value

        Args:
            value: Configuration value (string, dict, list, or other).

        Returns:
            Value with environment variables interpolated.

        Raises:
            ConfigurationError: If required environment variable is not set.
        """
        if isinstance(value, str):

            def replace(match: re.Match[str]) -> str:
                var_name = match.group(1)
                default_value = match.group(2)  # None if no default specified
                env_value = os.environ.get(var_name)
                if env_value is not None:
                    return env_value
                if default_value is not None:
                    return default_value
                msg = f"Environment variable {var_name} is not set"
                raise ConfigurationError(msg)

            return ENV_VAR_PATTERN.sub(replace, value)
        elif isinstance(value, dict):
            return {k: ConfigLoader.interpolate_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [ConfigLoader.interpolate_env_vars(item) for item in value]
        return value

    @staticmethod
    def load_config(explicit_path: Path | None = None) -> FileConfig | None:
        """Discover, load, and parse configuration file.

        Args:
            explicit_path: Explicitly provided config file path.

        Returns:
            Parsed FileConfig, or None if no config file found.

        Raises:
            ConfigurationError: If config file exists but is invalid.
        """
        config_path = ConfigLoader.discover_config_file(explicit_path)
        if config_path is None:
            return None

        raw_config = ConfigLoader.load_yaml(config_path)
        interpolated = ConfigLoader.interpolate_env_vars(raw_config)

        try:
            return FileConfig.model_validate(interpolated)
        except Exception as e:
            msg = f"Invalid configuration in {config_path}: {e}"
            raise ConfigurationError(msg) from e

    @staticmethod
    def _apply_llm_config(source: LLMConfig, values: _ResolvedValues) -> None:
        """Apply values from an LLMConfig source (mutates values in place)."""
        values.provider = source.provider
        values.model = source.model
        values.temperature = source.temperature
        values.max_tokens = source.max_tokens
        values.base_url = source.base_url or values.base_url
        if source.api_key:
            values.api_key = source.api_key.get_secret_value()
        if source.context_size is not None:
            values.context_size = source.context_size
        if source.reasoning is not None:
            values.reasoning = source.reasoning

    @staticmethod
    def _apply_cli_overrides(cli: CLIOverrides, values: _ResolvedValues) -> None:
        """Apply CLI overrides to configuration values (mutates values in place)."""
        if cli.provider is not None:
            values.provider = cli.provider
        if cli.model is not None:
            values.model = cli.model
        if cli.temperature is not None:
            values.temperature = cli.temperature
        if cli.max_tokens is not None:
            values.max_tokens = cli.max_tokens
        if cli.base_url is not None:
            values.base_url = cli.base_url
        if cli.api_key is not None:
            values.api_key = cli.api_key

    @staticmethod
    def resolve_llm_config(
        file_config: FileConfig | None,
        component: str,
        cli_overrides: CLIOverrides | None = None,
        default_provider: str = "ollama",
        default_model: str = "llama3.2",
    ) -> LLMConfig:
        """Resolve LLM configuration for a specific component.

        Priority order (highest to lowest):
        1. CLI arguments (via cli_overrides)
        2. Component-specific config (judge:, synthetic_user:)
        3. Shared LLM config (llm:)
        4. Defaults

        Args:
            file_config: Parsed configuration file, or None.
            component: Component name ("judge", "synthetic_user", or "llm").
            cli_overrides: CLI argument overrides, or None.
            default_provider: Default provider if not specified.
            default_model: Default model if not specified.

        Returns:
            Resolved LLMConfig for the component.
        """
        # Start with defaults
        values = _ResolvedValues(
            provider=default_provider,
            model=default_model,
            temperature=0.0,
            max_tokens=4096,
            base_url=None,
            api_key=None,
            context_size=None,
            reasoning=None,
        )

        # Apply shared llm config
        if file_config and file_config.llm:
            ConfigLoader._apply_llm_config(file_config.llm, values)

        # Apply component-specific config
        component_config: LLMConfig | None = None
        if file_config:
            component_config = getattr(file_config, component, None)
        if component_config:
            ConfigLoader._apply_llm_config(component_config, values)

        # Apply CLI overrides (highest priority)
        if cli_overrides:
            ConfigLoader._apply_cli_overrides(cli_overrides, values)

        return LLMConfig(
            provider=values.provider,
            model=values.model,
            temperature=values.temperature,
            max_tokens=values.max_tokens,
            base_url=values.base_url,
            api_key=SecretStr(values.api_key) if values.api_key else None,
            context_size=values.context_size,
            reasoning=values.reasoning,
        )

    @staticmethod
    def resolve_orchestrator_config(
        file_config: FileConfig | None,
        *,
        cli_max_turns: int | None = None,
        cli_timeout: float | None = None,
    ) -> OrchestratorConfig:
        """Resolve orchestrator configuration.

        Args:
            file_config: Parsed configuration file, or None.
            cli_max_turns: CLI max turns override.
            cli_timeout: CLI timeout override.

        Returns:
            Resolved OrchestratorConfig.
        """
        # Start with defaults
        max_turns = 10
        timeout = 30.0
        loop_detection = 3

        # Apply file config
        if file_config:
            max_turns = file_config.orchestrator.max_turns
            timeout = file_config.orchestrator.turn_timeout_seconds
            loop_detection = file_config.orchestrator.loop_detection_threshold

        # Apply CLI overrides
        if cli_max_turns is not None:
            max_turns = cli_max_turns
        if cli_timeout is not None:
            timeout = cli_timeout

        return OrchestratorConfig(
            max_turns=max_turns,
            turn_timeout_seconds=timeout,
            loop_detection_threshold=loop_detection,
        )

    @staticmethod
    def resolve_results_config(
        file_config: FileConfig | None,
        *,
        cli_save: bool | None = None,
        cli_dir: str | None = None,
    ) -> ResultsConfig:
        """Resolve results storage configuration.

        Args:
            file_config: Parsed configuration file, or None.
            cli_save: CLI save results override.
            cli_dir: CLI results directory override.

        Returns:
            Resolved ResultsConfig.
        """
        # Start with defaults
        save = True
        results_dir = "test-results"

        # Apply file config
        if file_config:
            save = file_config.results.save
            results_dir = file_config.results.dir

        # Apply CLI overrides
        if cli_save is not None:
            save = cli_save
        if cli_dir is not None:
            results_dir = cli_dir

        return ResultsConfig(save=save, dir=results_dir)

    @staticmethod
    def resolve_agent_config(
        file_config: FileConfig | None,
        *,
        cli_agent_type: str | None = None,
        cli_agent_factory: str | None = None,
    ) -> AgentConfig:
        """Resolve agent under test configuration.

        Args:
            file_config: Parsed configuration file, or None.
            cli_agent_type: CLI agent type override.
            cli_agent_factory: CLI agent factory override.

        Returns:
            Resolved AgentConfig.
        """
        # Start with defaults
        agent_type = "simple"
        factory = None

        # Apply file config
        if file_config:
            agent_type = file_config.agent.type
            factory = file_config.agent.factory

        # Apply CLI overrides
        if cli_agent_type is not None:
            agent_type = cli_agent_type
        if cli_agent_factory is not None:
            factory = cli_agent_factory

        return AgentConfig(type=agent_type, factory=factory)


def load_config(explicit_path: Path | None = None) -> FileConfig | None:
    """Convenience function to load configuration.

    Args:
        explicit_path: Explicitly provided config file path.

    Returns:
        Parsed FileConfig, or None if no config file found.
    """
    return ConfigLoader.load_config(explicit_path)
