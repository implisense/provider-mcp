"""Tests für Szenario-Tools und PDL-Backend."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from provider_mcp.backends.pdl_reader import (
    _load_scenario_file,
    _scenario_id_from_path,
    get_scenario_summary,
    get_scenario_yaml,
    load_all_scenarios,
    load_scenario,
)
from provider_mcp.tools.scenarios import get_scenario_impl, list_scenarios_impl


# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def _make_pdl_yaml(tmp_path: Path, filename: str, content: dict) -> Path:
    """Erstellt eine temporäre PDL-YAML-Datei."""
    import yaml
    path = tmp_path / filename
    path.write_text(yaml.dump(content, allow_unicode=True), encoding="utf-8")
    return path


SAMPLE_PDL = {
    "pdl_version": "1.0",
    "scenario": {
        "id": "test_scenario",
        "name": "Test-Szenario",
        "sector": "agriculture",
        "criticality": "high",
        "description": "Ein Test-Szenario für Unit-Tests",
    },
    "entities": [
        {"id": "entity_a", "type": "region", "name": "Region A"},
        {"id": "entity_b", "type": "manufacturer", "name": "Hersteller B"},
    ],
    "events": [
        {"id": "event_1", "type": "disruption", "name": "Störung 1"},
    ],
    "flows": [],
}


# ── PDL-Reader Tests ──────────────────────────────────────────────────────────

class TestScenarioIdFromPath:
    def test_pdl_yaml_extension(self):
        path = Path("s1-soja.pdl.yaml")
        assert _scenario_id_from_path(path) == "s1-soja"

    def test_plain_yaml_extension(self):
        path = Path("s2-halbleiter.yaml")
        assert _scenario_id_from_path(path) == "s2-halbleiter"

    def test_no_extension_change(self):
        path = Path("my-scenario.pdl.yaml")
        assert _scenario_id_from_path(path) == "my-scenario"


class TestLoadScenarioFile:
    def test_valid_pdl(self, tmp_path):
        path = _make_pdl_yaml(tmp_path, "test.pdl.yaml", SAMPLE_PDL)
        result = _load_scenario_file(path)

        assert result is not None
        assert result["id"] == "test_scenario"
        assert result["name"] == "Test-Szenario"
        assert result["sector"] == "agriculture"
        assert result["criticality"] == "high"
        assert result["entity_count"] == 2
        assert result["event_count"] == 1
        assert result["file_id"] == "test"

    def test_missing_scenario_key(self, tmp_path):
        path = _make_pdl_yaml(tmp_path, "bad.yaml", {"pdl_version": "1.0"})
        result = _load_scenario_file(path)
        assert result is None

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.yaml"
        path.write_text("", encoding="utf-8")
        result = _load_scenario_file(path)
        assert result is None

    def test_nonexistent_file(self):
        result = _load_scenario_file(Path("/nonexistent/path.yaml"))
        assert result is None


class TestLoadAllScenarios:
    def test_empty_directory(self, tmp_path):
        result = load_all_scenarios(tmp_path)
        assert result == []

    def test_nonexistent_directory(self):
        result = load_all_scenarios(Path("/nonexistent/dir"))
        assert result == []

    def test_multiple_scenarios(self, tmp_path):
        for i, name in enumerate(["s1-test", "s2-test", "s3-test"]):
            pdl = dict(SAMPLE_PDL)
            pdl["scenario"] = dict(SAMPLE_PDL["scenario"])
            pdl["scenario"]["id"] = f"scenario_{i}"
            _make_pdl_yaml(tmp_path, f"{name}.pdl.yaml", pdl)

        results = load_all_scenarios(tmp_path)
        assert len(results) == 3

    def test_skips_invalid_files(self, tmp_path):
        _make_pdl_yaml(tmp_path, "valid.pdl.yaml", SAMPLE_PDL)
        _make_pdl_yaml(tmp_path, "invalid.pdl.yaml", {"no_scenario": True})

        results = load_all_scenarios(tmp_path)
        assert len(results) == 1


class TestLoadScenario:
    def test_find_by_file_id(self, tmp_path):
        _make_pdl_yaml(tmp_path, "s1-soja.pdl.yaml", SAMPLE_PDL)
        result = load_scenario("s1-soja", tmp_path)
        assert result is not None
        assert result["file_id"] == "s1-soja"

    def test_find_by_partial_name(self, tmp_path):
        _make_pdl_yaml(tmp_path, "s1-soja.pdl.yaml", SAMPLE_PDL)
        result = load_scenario("soja", tmp_path)
        assert result is not None

    def test_not_found(self, tmp_path):
        result = load_scenario("nonexistent", tmp_path)
        assert result is None


class TestGetScenarioSummary:
    def test_summary_excludes_raw(self, tmp_path):
        path = _make_pdl_yaml(tmp_path, "test.pdl.yaml", SAMPLE_PDL)
        scenario = _load_scenario_file(path)
        summary = get_scenario_summary(scenario)

        assert "raw" not in summary
        assert "entities" not in summary
        assert "events" not in summary
        assert summary["name"] == "Test-Szenario"
        assert summary["entity_count"] == 2


class TestGetScenarioYaml:
    def test_returns_yaml_content(self, tmp_path):
        path = _make_pdl_yaml(tmp_path, "s1-soja.pdl.yaml", SAMPLE_PDL)
        yaml_content = get_scenario_yaml("s1-soja", tmp_path)
        assert yaml_content is not None
        assert "Test-Szenario" in yaml_content

    def test_not_found_returns_none(self, tmp_path):
        result = get_scenario_yaml("nonexistent", tmp_path)
        assert result is None


# ── Tool-Wrapper Tests ────────────────────────────────────────────────────────

class TestListScenariosTool:
    def test_with_real_scenarios_dir(self, tmp_path):
        for i in range(3):
            pdl = dict(SAMPLE_PDL)
            pdl["scenario"] = {**SAMPLE_PDL["scenario"], "id": f"s{i}"}
            _make_pdl_yaml(tmp_path, f"s{i}-test.pdl.yaml", pdl)

        with patch("provider_mcp.tools.scenarios.load_all_scenarios",
                   return_value=[_load_scenario_file(tmp_path / f"s{i}-test.pdl.yaml") for i in range(3)]):
            result = list_scenarios_impl()

        assert result["count"] == 3
        assert "scenarios" in result
        assert "sectors" in result

    def test_empty_result(self):
        with patch("provider_mcp.tools.scenarios.load_all_scenarios", return_value=[]):
            result = list_scenarios_impl()

        assert result["count"] == 0
        assert "warning" in result


class TestGetScenarioTool:
    def test_found(self, tmp_path):
        path = _make_pdl_yaml(tmp_path, "s1-soja.pdl.yaml", SAMPLE_PDL)
        scenario = _load_scenario_file(path)

        with patch("provider_mcp.tools.scenarios.load_scenario", return_value=scenario), \
             patch("provider_mcp.tools.scenarios.get_scenario_yaml", return_value="yaml_content"):
            result = get_scenario_impl("s1-soja")

        assert result["id"] == "test_scenario"
        assert result["yaml"] == "yaml_content"
        assert "entities" in result
        assert "events" in result

    def test_not_found(self):
        with patch("provider_mcp.tools.scenarios.load_scenario", return_value=None), \
             patch("provider_mcp.tools.scenarios.load_all_scenarios", return_value=[]):
            result = get_scenario_impl("nonexistent")

        assert "error" in result
        assert "available_ids" in result
