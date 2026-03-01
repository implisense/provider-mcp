"""httpx-Client für stress-test-saas (Port 8080, SSE-Streaming)."""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx

from provider_mcp.config import (
    DEFAULT_N_SIMULATIONS,
    HTTP_CONNECT_TIMEOUT,
    HTTP_TIMEOUT,
    STRESS_TEST_API_URL,
    USE_HEURISTIC_FALLBACK,
)

# In-Memory-Cache für Simulationsergebnisse {run_id: result_dict}
_results_cache: dict[str, dict[str, Any]] = {}


async def run_stress_test(
    description: str,
    template: str | None = None,
    n_simulations: int = DEFAULT_N_SIMULATIONS,
    api_url: str | None = None,
) -> dict[str, Any]:
    """
    Führt einen Stress-Test via stress-test-saas durch.

    Streamt SSE-Events bis zum 'complete'-Event und gibt das finale Ergebnis zurück.
    Speichert das Ergebnis in _results_cache unter einer run_id.

    Returns dict mit: run_id, risk_score, risk_grade, entity_risks, recommendations, pdl_yaml, ...
    """
    base_url = api_url or STRESS_TEST_API_URL
    run_id = str(uuid.uuid4())[:8]

    payload: dict[str, Any] = {
        "description": description,
        "n_simulations": n_simulations,
    }
    if template:
        payload["template"] = template

    result: dict[str, Any] = {
        "run_id": run_id,
        "status": "running",
        "description": description,
    }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(HTTP_TIMEOUT, connect=HTTP_CONNECT_TIMEOUT)
        ) as client:
            async with client.stream(
                "POST",
                f"{base_url}/api/analyze",
                json=payload,
                headers={"Accept": "text/event-stream"},
            ) as response:
                response.raise_for_status()

                event_type = None
                async for line in response.aiter_lines():
                    line = line.strip()
                    if line.startswith("event:"):
                        event_type = line[len("event:"):].strip()
                    elif line.startswith("data:") and event_type:
                        data_str = line[len("data:"):].strip()
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        if event_type == "simulation":
                            result.update({
                                "risk_score": data.get("risk_score"),
                                "risk_grade": data.get("risk_grade"),
                                "entity_risks": data.get("entity_risks", []),
                                "event_risks": data.get("event_risks", []),
                                "supply_chain_risks": data.get("supply_chain_risks", {}),
                                "worst_scenarios": data.get("worst_scenarios", []),
                                "health_distribution": data.get("health_distribution", {}),
                            })
                        elif event_type == "pdl":
                            result.update({
                                "pdl_yaml": data.get("yaml", ""),
                                "scenario_name": data.get("scenario_name", ""),
                                "entity_count": data.get("entity_count", 0),
                                "event_count": data.get("event_count", 0),
                            })
                        elif event_type == "recommendations":
                            result["recommendations"] = data.get("items", [])
                        elif event_type == "complete":
                            result["status"] = "complete"
                            result["n_simulations"] = data.get("n_simulations", n_simulations)
                            break
                        elif event_type == "error":
                            result["status"] = "error"
                            result["error"] = data.get("message", "Unbekannter Fehler")
                            break

        # Ergebnis cachen
        _results_cache[run_id] = result
        return result

    except httpx.ConnectError:
        if USE_HEURISTIC_FALLBACK:
            return _heuristic_fallback(run_id, description)
        return {
            "run_id": run_id,
            "status": "error",
            "error": f"stress-test-saas nicht erreichbar unter {base_url}. "
                     "Bitte starten mit: cd stress-test-saas/backend && python server.py",
            "description": description,
        }
    except httpx.TimeoutException:
        return {
            "run_id": run_id,
            "status": "error",
            "error": "Timeout beim Warten auf Simulationsergebnis.",
            "description": description,
        }


def get_cached_result(run_id: str) -> dict[str, Any] | None:
    """Gibt gecachtes Ergebnis für eine run_id zurück."""
    return _results_cache.get(run_id)


async def check_health(api_url: str | None = None) -> bool:
    """Prüft ob stress-test-saas erreichbar ist."""
    base_url = api_url or STRESS_TEST_API_URL
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=2.0)) as client:
            resp = await client.get(f"{base_url}/api/health")
            return resp.status_code == 200
    except Exception:
        return False


def _heuristic_fallback(run_id: str, description: str) -> dict[str, Any]:
    """
    Einfache regelbasierte Heuristik wenn stress-test-saas nicht läuft.
    Gibt einen ungefähren Risiko-Score basierend auf Schlüsselwörtern zurück.
    """
    desc_lower = description.lower()

    # Schlüsselwörter und ihre Risikogewichte
    risk_keywords = {
        # Hochrisiko
        "krieg": 0.3, "konflikt": 0.25, "sanktion": 0.25, "embargo": 0.25,
        "katastrophe": 0.3, "ausfall": 0.2, "störung": 0.2, "engpass": 0.2,
        "monopol": 0.2, "einziger lieferant": 0.3, "single source": 0.3,
        # Mittleres Risiko
        "soja": 0.15, "halbleiter": 0.15, "lithium": 0.15, "seltene erden": 0.15,
        "pharmawirkstoffe": 0.15, "api": 0.1, "chip": 0.1,
        "china": 0.1, "russland": 0.15, "iran": 0.1,
        "hafen": 0.1, "transport": 0.08, "logistik": 0.08,
        # Niedrigeres Risiko
        "europa": -0.05, "diversifiziert": -0.1, "lager": -0.05,
        "alternative": -0.08, "backup": -0.08,
    }

    base_score = 30.0
    for keyword, weight in risk_keywords.items():
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
        "source": "heuristic_fallback",
        "note": "Heuristik-Ergebnis (stress-test-saas nicht erreichbar). "
                "Für präzise Simulation: cd stress-test-saas/backend && python server.py",
        "recommendations": [
            "Lieferantenkonzentration analysieren und reduzieren",
            "Strategische Lagerbestände aufbauen",
            "Alternative Beschaffungsquellen identifizieren",
            "Frühwarnsystem für Marktentwicklungen einrichten",
        ],
    }
    _results_cache[run_id] = result
    return result
