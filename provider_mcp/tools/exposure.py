"""MCP-Tool: assess_company_exposure."""

from __future__ import annotations

from typing import Any

from provider_mcp.backends.pdl_reader import load_all_scenarios
from provider_mcp.backends.stresstest_client import (
    get_cached_result,
    run_stress_test as _run_stress_test,
)
from provider_mcp.config import USE_HEURISTIC_FALLBACK


# Sektoren-Mapping: welche PDL-Szenarien sind relevant für welche Sektoren/Commodities
_SECTOR_SCENARIO_MAP = {
    "landwirtschaft": ["s1-soja", "s4-duengemittel-adblue"],
    "agriculture": ["s1-soja", "s4-duengemittel-adblue"],
    "pharma": ["s3-pharma"],
    "halbleiter": ["s2-halbleiter"],
    "semiconductor": ["s2-halbleiter"],
    "elektronik": ["s2-halbleiter", "s7-seltene-erden"],
    "automotive": ["s2-halbleiter", "s7-seltene-erden"],
    "energie": ["s6-rechenzentren"],
    "wasser": ["s5-wasseraufbereitung"],
    "logistik": ["s8-seefracht", "s9-unterwasserkabel"],
    "shipping": ["s8-seefracht"],
    "telekommunikation": ["s9-unterwasserkabel"],
    "rohstoffe": ["s7-seltene-erden", "s4-duengemittel-adblue"],
    "it": ["s6-rechenzentren", "s2-halbleiter"],
    "rechenzentren": ["s6-rechenzentren"],
}

_COMMODITY_SCENARIO_MAP = {
    "soja": "s1-soja",
    "soy": "s1-soja",
    "soybeans": "s1-soja",
    "halbleiter": "s2-halbleiter",
    "chips": "s2-halbleiter",
    "semiconductor": "s2-halbleiter",
    "pharmawirkstoffe": "s3-pharma",
    "api": "s3-pharma",
    "medikamente": "s3-pharma",
    "düngemittel": "s4-duengemittel-adblue",
    "duengemittel": "s4-duengemittel-adblue",
    "adblue": "s4-duengemittel-adblue",
    "harnstoff": "s4-duengemittel-adblue",
    "wasser": "s5-wasseraufbereitung",
    "strom": "s6-rechenzentren",
    "seltene erden": "s7-seltene-erden",
    "lithium": "s7-seltene-erden",
    "kobalt": "s7-seltene-erden",
    "seefracht": "s8-seefracht",
    "container": "s8-seefracht",
    "unterwasserkabel": "s9-unterwasserkabel",
    "datenkabel": "s9-unterwasserkabel",
}


def _find_relevant_scenarios(
    sector: str,
    commodities: list[str],
) -> tuple[list[str], list[str]]:
    """Findet relevante PDL-Szenarien für Sektor und Commodities."""
    relevant_ids: set[str] = set()
    matched_commodities: list[str] = []

    # Sektor-Matching
    sector_lower = sector.lower()
    for key, scenario_ids in _SECTOR_SCENARIO_MAP.items():
        if key in sector_lower or sector_lower in key:
            relevant_ids.update(scenario_ids)

    # Commodity-Matching
    all_scenarios = load_all_scenarios()
    scenario_names = {s["file_id"]: s["name"] for s in all_scenarios}

    for commodity in commodities:
        commodity_lower = commodity.lower()
        for key, scenario_id in _COMMODITY_SCENARIO_MAP.items():
            if key in commodity_lower or commodity_lower in key:
                relevant_ids.add(scenario_id)
                matched_commodities.append(commodity)
                break
        else:
            # Fuzzy-Match auf Szenario-Beschreibungen
            for s in all_scenarios:
                if commodity_lower in s["description"].lower() or \
                   commodity_lower in s["name"].lower():
                    relevant_ids.add(s["file_id"])
                    matched_commodities.append(commodity)
                    break

    return list(relevant_ids), matched_commodities


def _build_exposure_prompt(
    sector: str,
    commodities: list[str],
    relevant_scenario_ids: list[str],
) -> str:
    """Erstellt einen strukturierten Prompt für die Expositionsanalyse."""
    commodity_str = ", ".join(commodities) if commodities else "keine spezifischen Commodities"
    scenario_str = ", ".join(relevant_scenario_ids) if relevant_scenario_ids else "allgemein"

    return (
        f"Unternehmensbetroffenheitsanalyse für den Sektor '{sector}'. "
        f"Kritische Commodities/Materialien: {commodity_str}. "
        f"Analysiere Lieferkettenrisiken und mögliche Engpässe, "
        f"insbesondere für: {scenario_str}. "
        f"Bewerte die Vulnerabilität und empfehle Maßnahmen zur Risikoreduktion."
    )


async def assess_company_exposure_impl(
    sector: str,
    commodities: list[str],
) -> dict[str, Any]:
    """
    Analysiert die Betroffenheit eines Unternehmens durch Lieferkettenrisiken.

    Args:
        sector: Unternehmenssektor (z.B. 'Landwirtschaft', 'Pharma', 'Halbleiter',
                'Automotive', 'Logistik', 'Rechenzentren')
        commodities: Liste kritischer Commodities/Materialien
                     (z.B. ['Soja', 'Düngemittel'] oder ['Lithium', 'Kobalt'])

    Returns eine strukturierte Betroffenheitsanalyse mit:
    - relevant_scenarios: Welche PROVIDER-Szenarien relevant sind
    - risk_score: Geschätzter Risiko-Score (0-100)
    - exposure_level: HIGH/MEDIUM/LOW
    - key_vulnerabilities: Kritische Schwachstellen
    - recommendations: Konkrete Maßnahmen
    """
    relevant_ids, matched_commodities = _find_relevant_scenarios(sector, commodities)

    # Relevante Szenario-Details laden
    all_scenarios = load_all_scenarios()
    relevant_scenarios = [
        {
            "file_id": s["file_id"],
            "name": s["name"],
            "sector": s["sector"],
            "criticality": s["criticality"],
            "description": s["description"],
        }
        for s in all_scenarios
        if s["file_id"] in relevant_ids
    ]

    # Simulation starten (oder Heuristik wenn nicht erreichbar)
    prompt = _build_exposure_prompt(sector, commodities, relevant_ids)
    sim_result = await _run_stress_test(description=prompt)

    risk_score = sim_result.get("risk_score", 45.0)
    if risk_score is None:
        risk_score = 45.0

    # Exposure-Level bestimmen
    if risk_score >= 65:
        exposure_level = "HIGH"
        exposure_label = "Hohe Betroffenheit"
    elif risk_score >= 40:
        exposure_level = "MEDIUM"
        exposure_label = "Mittlere Betroffenheit"
    else:
        exposure_level = "LOW"
        exposure_label = "Geringe Betroffenheit"

    # Schlüssel-Vulnerabilitäten aus Szenarien extrahieren
    key_vulnerabilities = []
    for scenario in relevant_scenarios:
        key_vulnerabilities.append({
            "scenario": scenario["name"],
            "criticality": scenario["criticality"],
            "description": scenario["description"],
        })

    result = {
        "sector": sector,
        "commodities": commodities,
        "matched_commodities": matched_commodities,
        "exposure_level": exposure_level,
        "exposure_label": exposure_label,
        "risk_score": round(float(risk_score), 1),
        "risk_grade": sim_result.get("risk_grade", "B"),
        "relevant_scenarios": relevant_scenarios,
        "scenario_count": len(relevant_scenarios),
        "key_vulnerabilities": key_vulnerabilities,
        "recommendations": sim_result.get("recommendations", []),
        "run_id": sim_result.get("run_id", ""),
        "simulation_status": sim_result.get("status", "unknown"),
    }

    if not relevant_scenarios:
        result["warning"] = (
            f"Keine spezifischen PROVIDER-Szenarien für Sektor '{sector}' "
            f"und Commodities {commodities} gefunden. "
            "Verfügbare Sektoren: Landwirtschaft, Pharma, Halbleiter, "
            "Automotive, Logistik, Rechenzentren, Wasseraufbereitung."
        )

    if sim_result.get("source") == "heuristic_fallback":
        result["note"] = sim_result.get("note", "")

    return result
