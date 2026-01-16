"""Template loading utilities for scenario generation."""

from importlib.resources import files
from typing import Any

import yaml

import mcprobe.generator.templates as templates_package


class TemplateNotFoundError(Exception):
    """Raised when a requested template does not exist."""


def load_template(category: str) -> dict[str, Any]:
    """Load a scenario template by category name.

    Args:
        category: The category name (e.g., "happy_path", "clarification")

    Returns:
        The template as a dictionary

    Raises:
        TemplateNotFoundError: If the template file does not exist
    """
    template_file = files(templates_package).joinpath(f"{category}.yaml")

    try:
        content = template_file.read_text()
    except FileNotFoundError as e:
        msg = f"Template not found: {category}"
        raise TemplateNotFoundError(msg) from e

    result = yaml.safe_load(content)
    if not isinstance(result, dict):
        msg = f"Invalid template format for {category}: expected dict"
        raise TemplateNotFoundError(msg)
    return result


def list_available_templates() -> list[str]:
    """List all available template categories.

    Returns:
        List of category names (without .yaml extension)
    """
    templates_dir = files(templates_package)
    categories: list[str] = []

    for item in templates_dir.iterdir():
        name = str(item.name)
        if name.endswith(".yaml"):
            categories.append(name.removesuffix(".yaml"))

    return sorted(categories)
