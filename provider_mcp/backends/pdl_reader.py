"""Liest PDL-YAML-Szenarien aus dem Dateisystem."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from provider_mcp.config import PDL_SCENARIOS_DIR


def _scenario_id_from_path(path: Path) -> str:
    """Extrahiert die Szenario-ID aus dem Dateinamen (z.B. 's1-soja' aus 's1-soja.pdl.yaml')."""
    name = path.name
    # Entferne .pdl.yaml oder .yaml am Ende
    name = re.sub(r"\.pdl\.yaml$|\.yaml$", "", name)
    return name


def load_all_scenarios(scenarios_dir: Path | None = None) -> list[dict[str, Any]]:
    """Lädt alle PDL-Szenarien und gibt eine Liste strukturierter Dicts zurück."""
    base_dir = scenarios_dir or PDL_SCENARIOS_DIR
    scenarios = []

    if not base_dir.exists():
        return scenarios

    for path in sorted(base_dir.glob("*.yaml")):
        scenario = _load_scenario_file(path)
        if scenario:
            scenarios.append(scenario)

    return scenarios


def load_scenario(scenario_id: str, scenarios_dir: Path | None = None) -> dict[str, Any] | None:
    """Lädt ein einzelnes Szenario nach ID (z.B. 's1-soja')."""
    base_dir = scenarios_dir or PDL_SCENARIOS_DIR

    if not base_dir.exists():
        return None

    # Suche nach exakter ID
    for path in base_dir.glob("*.yaml"):
        if _scenario_id_from_path(path) == scenario_id:
            return _load_scenario_file(path)

    # Fallback: Suche nach Teilstring
    for path in base_dir.glob("*.yaml"):
        if scenario_id in path.name:
            return _load_scenario_file(path)

    return None


def _load_scenario_file(path: Path) -> dict[str, Any] | None:
    """Liest eine PDL-YAML-Datei und gibt ein strukturiertes Dict zurück."""
    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not raw or "scenario" not in raw:
            return None

        file_id = _scenario_id_from_path(path)
        scenario_meta = raw.get("scenario", {})

        return {
            "file_id": file_id,
            "id": scenario_meta.get("id", file_id),
            "name": scenario_meta.get("name", file_id),
            "sector": scenario_meta.get("sector", "unknown"),
            "criticality": scenario_meta.get("criticality", "unknown"),
            "description": scenario_meta.get("description", ""),
            "entity_count": len(raw.get("entities", [])),
            "event_count": len(raw.get("events", [])),
            "entities": raw.get("entities", []),
            "events": raw.get("events", []),
            "flows": raw.get("flows", []),
            "pdl_version": raw.get("pdl_version", "1.0"),
            "raw": raw,
            "_path": str(path),
        }
    except Exception:
        return None


def get_scenario_summary(scenario: dict[str, Any]) -> dict[str, Any]:
    """Gibt eine kompakte Zusammenfassung eines Szenarios zurück (ohne raw-Daten)."""
    return {
        "file_id": scenario["file_id"],
        "id": scenario["id"],
        "name": scenario["name"],
        "sector": scenario["sector"],
        "criticality": scenario["criticality"],
        "description": scenario["description"],
        "entity_count": scenario["entity_count"],
        "event_count": scenario["event_count"],
    }


def get_scenario_yaml(scenario_id: str, scenarios_dir: Path | None = None) -> str | None:
    """Gibt den rohen YAML-Inhalt eines Szenarios zurück."""
    base_dir = scenarios_dir or PDL_SCENARIOS_DIR

    if not base_dir.exists():
        return None

    for path in base_dir.glob("*.yaml"):
        if _scenario_id_from_path(path) == scenario_id or scenario_id in path.name:
            try:
                return path.read_text(encoding="utf-8")
            except Exception:
                return None

    return None
