"""MCP-Tools: list_scenarios und get_scenario."""

from __future__ import annotations

from typing import Any

from provider_mcp.backends.pdl_reader import (
    get_scenario_summary,
    get_scenario_yaml,
    load_all_scenarios,
    load_scenario,
)


def list_scenarios_impl() -> dict[str, Any]:
    """
    Listet alle verfügbaren PROVIDER-Lieferkettenszenarien auf.

    Gibt kompakte Zusammenfassungen aller 9 PDL-Szenarien zurück,
    inklusive Sektor, Kritikalität und Entity/Event-Anzahl.
    """
    scenarios = load_all_scenarios()

    if not scenarios:
        return {
            "scenarios": [],
            "count": 0,
            "warning": "Keine PDL-Szenarien gefunden. PDL_SCENARIOS_DIR überprüfen.",
        }

    summaries = [get_scenario_summary(s) for s in scenarios]

    # Kritikalitäts-Mapping für Sortierung
    criticality_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
    summaries.sort(key=lambda x: criticality_order.get(x["criticality"], 4))

    return {
        "scenarios": summaries,
        "count": len(summaries),
        "sectors": list({s["sector"] for s in summaries}),
    }


def get_scenario_impl(scenario_id: str) -> dict[str, Any]:
    """
    Gibt vollständige Details eines PROVIDER-Szenarios zurück.

    Args:
        scenario_id: Szenario-ID (z.B. 's1-soja', 's2-halbleiter', 'soja') oder
                     interner Name (z.B. 'soy_feed_disruption')

    Returns vollständiges PDL-Objekt mit allen Entities, Events und Flows.
    """
    scenario = load_scenario(scenario_id)

    if not scenario:
        # Versuche fuzzy matching auf Namen
        all_scenarios = load_all_scenarios()
        lower_id = scenario_id.lower()
        for s in all_scenarios:
            if (lower_id in s["file_id"].lower()
                    or lower_id in s["name"].lower()
                    or lower_id in s["id"].lower()):
                scenario = s
                break

    if not scenario:
        return {
            "error": f"Szenario '{scenario_id}' nicht gefunden.",
            "available_ids": [
                get_scenario_summary(s)["file_id"]
                for s in load_all_scenarios()
            ],
        }

    # YAML-Inhalt ergänzen
    yaml_content = get_scenario_yaml(scenario["file_id"])

    return {
        "file_id": scenario["file_id"],
        "id": scenario["id"],
        "name": scenario["name"],
        "sector": scenario["sector"],
        "criticality": scenario["criticality"],
        "description": scenario["description"],
        "entity_count": scenario["entity_count"],
        "event_count": scenario["event_count"],
        "entities": scenario["entities"],
        "events": scenario["events"],
        "flows": scenario["flows"],
        "pdl_version": scenario["pdl_version"],
        "yaml": yaml_content,
    }
