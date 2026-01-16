"""YAML scenario parser.

Parses test scenario files and validates them against the schema.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from mcprobe.exceptions import ScenarioParseError, ScenarioValidationError
from mcprobe.models.scenario import TestScenario


class ScenarioParser:
    """Parser for test scenario YAML files."""

    @classmethod
    def parse_file(cls, path: Path | str) -> TestScenario:
        """Parse a scenario from a YAML file.

        Args:
            path: Path to the scenario YAML file.

        Returns:
            Validated TestScenario instance.

        Raises:
            ScenarioParseError: If the file cannot be read or parsed as YAML.
            ScenarioValidationError: If the YAML doesn't match the scenario schema.
        """
        path = Path(path)

        if not path.exists():
            msg = f"Scenario file not found: {path}"
            raise ScenarioParseError(msg)

        if not path.is_file():
            msg = f"Scenario path is not a file: {path}"
            raise ScenarioParseError(msg)

        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            msg = f"Failed to read scenario file {path}: {e}"
            raise ScenarioParseError(msg) from e

        return cls.parse_string(content, source=str(path))

    @classmethod
    def parse_string(cls, content: str, source: str = "<string>") -> TestScenario:
        """Parse a scenario from a YAML string.

        Args:
            content: YAML content as a string.
            source: Source identifier for error messages.

        Returns:
            Validated TestScenario instance.

        Raises:
            ScenarioParseError: If the content cannot be parsed as YAML.
            ScenarioValidationError: If the YAML doesn't match the scenario schema.
        """
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            msg = f"Invalid YAML in {source}: {e}"
            raise ScenarioParseError(msg) from e

        if data is None:
            msg = f"Empty scenario file: {source}"
            raise ScenarioParseError(msg)

        if not isinstance(data, dict):
            msg = f"Scenario must be a YAML mapping, got {type(data).__name__}: {source}"
            raise ScenarioParseError(msg)

        return cls.parse_dict(data, source=source)

    @classmethod
    def parse_dict(cls, data: dict[str, Any], source: str = "<dict>") -> TestScenario:
        """Parse a scenario from a dictionary.

        Args:
            data: Scenario data as a dictionary.
            source: Source identifier for error messages.

        Returns:
            Validated TestScenario instance.

        Raises:
            ScenarioValidationError: If the data doesn't match the scenario schema.
        """
        try:
            return TestScenario.model_validate(data)
        except ValidationError as e:
            msg = f"Invalid scenario in {source}: {e}"
            raise ScenarioValidationError(msg) from e

    @classmethod
    def parse_directory(cls, path: Path | str) -> list[TestScenario]:
        """Parse all scenario files in a directory.

        Args:
            path: Path to directory containing scenario YAML files.

        Returns:
            List of validated TestScenario instances.

        Raises:
            ScenarioParseError: If the path is not a directory.
            ScenarioParseError: If any file cannot be parsed.
            ScenarioValidationError: If any scenario fails validation.
        """
        path = Path(path)

        if not path.exists():
            msg = f"Scenario directory not found: {path}"
            raise ScenarioParseError(msg)

        if not path.is_dir():
            msg = f"Scenario path is not a directory: {path}"
            raise ScenarioParseError(msg)

        scenarios: list[TestScenario] = []
        for file_path in sorted(path.glob("**/*.yaml")):
            scenarios.append(cls.parse_file(file_path))

        for file_path in sorted(path.glob("**/*.yml")):
            # Avoid duplicates if both .yaml and .yml exist
            yaml_path = file_path.with_suffix(".yaml")
            if not yaml_path.exists():
                scenarios.append(cls.parse_file(file_path))

        return scenarios
