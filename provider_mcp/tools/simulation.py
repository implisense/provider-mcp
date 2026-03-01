"""MCP-Tools: run_stress_test und get_simulation_results."""

from __future__ import annotations

from typing import Any

from provider_mcp.backends.stresstest_client import (
    get_cached_result,
    run_stress_test as _run_stress_test,
)
from provider_mcp.config import DEFAULT_N_SIMULATIONS


async def run_stress_test_impl(
    description: str,
    scenario_ids: list[str] | None = None,
    n_simulations: int = DEFAULT_N_SIMULATIONS,
) -> dict[str, Any]:
    """
    Führt einen Monte-Carlo-Stress-Test für eine Lieferkettenbeschreibung durch.

    Args:
        description: Freitext-Beschreibung der Lieferkette oder des Risikos.
                     Beispiel: "Mein Unternehmen importiert Soja aus Brasilien für Tierfutter."
        scenario_ids: Optionale Liste von PDL-Szenario-IDs als Kontext (z.B. ['s1-soja']).
                      Wird dem Beschreibungstext als Kontext hinzugefügt.
        n_simulations: Anzahl Monte-Carlo-Simulationsläufe (Standard: 200).

    Returns dict mit:
    - run_id: ID für späteres Abrufen via get_simulation_results
    - risk_score: Gesamtrisiko-Score (0-100)
    - risk_grade: Risiko-Note (A=niedrig bis F=kritisch)
    - entity_risks: Risiken je Lieferkettenentität
    - recommendations: Priorisierte Handlungsempfehlungen
    - status: 'complete', 'error'
    """
    # Szenario-Kontext in Beschreibung einbauen, falls angegeben
    full_description = description
    if scenario_ids:
        context = f"Relevante PROVIDER-Szenarien: {', '.join(scenario_ids)}. "
        full_description = context + description

    result = await _run_stress_test(
        description=full_description,
        n_simulations=n_simulations,
    )

    # Antwort bereinigen (keine internen Felder)
    response = {
        "run_id": result.get("run_id", ""),
        "status": result.get("status", "unknown"),
        "risk_score": result.get("risk_score"),
        "risk_grade": result.get("risk_grade"),
        "scenario_name": result.get("scenario_name", ""),
        "entity_count": result.get("entity_count", 0),
        "event_count": result.get("event_count", 0),
        "entity_risks": result.get("entity_risks", []),
        "supply_chain_risks": result.get("supply_chain_risks", {}),
        "recommendations": result.get("recommendations", []),
        "n_simulations": result.get("n_simulations", n_simulations),
        "description": description,
    }

    if result.get("error"):
        response["error"] = result["error"]
    if result.get("source") == "heuristic_fallback":
        response["note"] = result.get("note", "")

    return response


def get_simulation_results_impl(run_id: str) -> dict[str, Any]:
    """
    Gibt gecachte Ergebnisse eines zuvor gestarteten Stress-Tests zurück.

    Args:
        run_id: Run-ID aus dem Ergebnis von run_stress_test (z.B. 'a3f7b2c1')

    Returns das vollständige Ergebnis-Dict, oder einen Fehler wenn die ID nicht bekannt ist.
    Note: Ergebnisse werden nur für die Dauer der Server-Session gecacht (In-Memory).
    """
    result = get_cached_result(run_id)

    if result is None:
        return {
            "error": f"Kein Ergebnis für run_id '{run_id}' gefunden.",
            "info": "Ergebnisse werden nur in-memory gecacht. "
                    "Bitte run_stress_test erneut ausführen.",
        }

    return result
