"""MCProbe pytest plugin.

Provides pytest integration for running MCProbe test scenarios as pytest tests.

Usage:
    pytest scenarios/  # Run all scenario files
    pytest scenarios/ --mcprobe-model=llama3.2  # With specific model
    pytest -m mcprobe  # Run only MCProbe tests
"""

from mcprobe.pytest_plugin.plugin import (
    MCProbeAssertionError,
    MCProbeFile,
    MCProbeItem,
    get_mcprobe_results,
    pytest_addoption,
    pytest_collect_file,
    pytest_collection_modifyitems,
    pytest_configure,
)

__all__ = [
    "MCProbeAssertionError",
    "MCProbeFile",
    "MCProbeItem",
    "get_mcprobe_results",
    "pytest_addoption",
    "pytest_collect_file",
    "pytest_collection_modifyitems",
    "pytest_configure",
]
