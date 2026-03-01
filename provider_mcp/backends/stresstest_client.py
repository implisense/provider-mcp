"""Regelbasierte Heuristik für Lieferketten-Risikoanalyse."""

from __future__ import annotations

import uuid
from typing import Any

from provider_mcp.config import DEFAULT_N_SIMULATIONS

# In-Memory-Cache für Analyseergebnisse {run_id: result_dict}
_results_cache: dict[str, dict[str, Any]] = {}

_RISK_KEYWORDS = {
    # Hochrisiko
    "krieg": 0.3, "konflikt": 0.25, "sanktion": 0.25, "embargo": 0.25,
    "katastrophe": 0.3, "ausfall": 0.2, "störung": 0.2, "engpass": 0.2,
    "monopol": 0.2, "einziger lieferant": 0.3, "single source": 0.3,
    # Mittleres Risiko
    "soja": 0.15, "halbleiter": 0.15, "lithium": 0.15, "seltene erden": 0.15,
    "pharmawirkstoffe": 0.15, "api": 0.1, "chip": 0.1,
    "china": 0.1, "russland": 0.15, "iran": 0.1,
    "hafen": 0.1, "transport": 0.08, "logistik": 0.08,
    # Risikoreduzierend
    "europa": -0.05, "diversifiziert": -0.1, "lager": -0.05,
    "alternative": -0.08, "backup": -0.08,
}


async def run_stress_test(
    description: str,
    template: str | None = None,
    n_simulations: int = DEFAULT_N_SIMULATIONS,
    api_url: str | None = None,
) -> dict[str, Any]:
    """Analysiert eine Lieferkettenbeschreibung mit regelbasierter Heuristik."""
    run_id = str(uuid.uuid4())[:8]
    return _heuristic_analysis(run_id, description)


def get_cached_result(run_id: str) -> dict[str, Any] | None:
    """Gibt gecachtes Ergebnis für eine run_id zurück."""
    return _results_cache.get(run_id)


def _heuristic_analysis(run_id: str, description: str) -> dict[str, Any]:
    """Regelbasierte Risikoanalyse anhand von Schlüsselwörtern."""
    desc_lower = description.lower()

    base_score = 30.0
    for keyword, weight in _RISK_KEYWORDS.items():
        if keyword in desc_lower:
            base_score += weight * 100

    risk_score = max(10, min(90, base_score))

    if risk_score >= 70:
        grade = "D"
    elif risk_score >= 55:
        grade = "C"
    elif risk_score >= 40:
        grade = "B"
    else:
        grade = "A"

    result = {
        "run_id": run_id,
        "status": "complete",
        "description": description,
        "risk_score": round(risk_score, 1),
        "risk_grade": grade,
        "source": "heuristic",
        "recommendations": [
            "Lieferantenkonzentration analysieren und reduzieren",
            "Strategische Lagerbestände aufbauen",
            "Alternative Beschaffungsquellen identifizieren",
            "Frühwarnsystem für Marktentwicklungen einrichten",
        ],
    }
    _results_cache[run_id] = result
    return result


# Alias für Rückwärtskompatibilität der Tests
_heuristic_fallback = _heuristic_analysis
