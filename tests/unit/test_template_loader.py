"""Tests for template loader module."""

import pytest

from mcprobe.generator.template_loader import (
    TemplateNotFoundError,
    list_available_templates,
    load_template,
)


class TestLoadTemplate:
    """Tests for load_template function."""

    def test_load_happy_path_template(self) -> None:
        """Test loading happy_path template."""
        template = load_template("happy_path")

        assert template["category"] == "happy_path"
        assert "structure" in template
        assert "synthetic_user" in template["structure"]
        assert "evaluation" in template["structure"]

    def test_load_clarification_template(self) -> None:
        """Test loading clarification template."""
        template = load_template("clarification")

        assert template["category"] == "clarification"
        assert template["structure"]["synthetic_user"]["max_turns"] == 8

    def test_load_edge_case_template(self) -> None:
        """Test loading edge_case template."""
        template = load_template("edge_case")

        assert template["category"] == "edge_case"
        assert "failure_criteria" in template["structure"]["evaluation"]

    def test_load_adversarial_template(self) -> None:
        """Test loading adversarial template."""
        template = load_template("adversarial")

        assert template["category"] == "adversarial"
        assert template["structure"]["synthetic_user"]["traits"]["patience"] == "low"

    def test_load_efficiency_template(self) -> None:
        """Test loading efficiency template."""
        template = load_template("efficiency")

        assert template["category"] == "efficiency"
        assert template["structure"]["evaluation"]["efficiency"]["max_tool_calls"] == 2

    def test_load_nonexistent_template_raises_error(self) -> None:
        """Test that loading nonexistent template raises error."""
        with pytest.raises(TemplateNotFoundError, match="Template not found"):
            load_template("nonexistent_category")


class TestListAvailableTemplates:
    """Tests for list_available_templates function."""

    def test_lists_all_templates(self) -> None:
        """Test that all templates are listed."""
        templates = list_available_templates()

        assert "happy_path" in templates
        assert "clarification" in templates
        assert "edge_case" in templates
        assert "adversarial" in templates
        assert "efficiency" in templates

    def test_returns_sorted_list(self) -> None:
        """Test that template list is sorted."""
        templates = list_available_templates()

        assert templates == sorted(templates)

    def test_at_least_five_templates(self) -> None:
        """Test that at least 5 templates exist."""
        templates = list_available_templates()

        assert len(templates) >= 5
