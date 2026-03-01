"""Liest Terminal-State-Dateien und extrahiert Alert-Informationen."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from provider_mcp.config import MONITOR_STATE_FILE, PIPELINE_STATE_FILE


# Alert-Level-Mapping auf lesbare Ampelfarben
_ALERT_LEVEL_LABELS = {
    "RED": "Kritisch",
    "ORANGE": "Hoch",
    "YELLOW": "Erhöht",
    "GREEN": "Normal",
    "GRAY": "Unbekannt",
}

_RISK_THRESHOLDS = {
    "RED": 0.75,
    "ORANGE": 0.55,
    "YELLOW": 0.35,
}


def _load_json_file(path: Path) -> dict[str, Any] | None:
    """Liest eine JSON-Datei sicher ein."""
    try:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _probability_to_alert_level(probability: float) -> str:
    if probability >= _RISK_THRESHOLDS["RED"]:
        return "RED"
    if probability >= _RISK_THRESHOLDS["ORANGE"]:
        return "ORANGE"
    if probability >= _RISK_THRESHOLDS["YELLOW"]:
        return "YELLOW"
    return "GREEN"


def get_current_alerts(
    monitor_state_file: Path | None = None,
    pipeline_state_file: Path | None = None,
) -> dict[str, Any]:
    """
    Liest monitor_state.json und pipeline_state.json und gibt eine strukturierte
    Alert-Zusammenfassung zurück.
    """
    mon_file = monitor_state_file or MONITOR_STATE_FILE
    pip_file = pipeline_state_file or PIPELINE_STATE_FILE

    monitor_data = _load_json_file(mon_file)
    pipeline_data = _load_json_file(pip_file)

    alerts = []
    markets_summary = []

    if monitor_data:
        markets = monitor_data.get("markets", [])
        last_updated = monitor_data.get("last_updated", "")
        poll_count = monitor_data.get("poll_count", 0)

        for market in markets:
            prob = market.get("current_probability", 0.0)
            level = _probability_to_alert_level(prob)
            market_alerts = market.get("alerts", [])

            market_summary = {
                "market_id": market.get("market_id", ""),
                "question": market.get("question", ""),
                "disruption_type": market.get("disruption_type", ""),
                "current_probability": round(prob, 3),
                "alert_level": level,
                "alert_label": _ALERT_LEVEL_LABELS.get(level, "Unbekannt"),
                "eu_relevance": market.get("eu_relevance", 0.0),
                "active_alerts": market_alerts,
            }
            markets_summary.append(market_summary)

            # Füge kritische Alerts zur Alert-Liste hinzu
            for alert in market_alerts:
                alerts.append({
                    "market_id": market.get("market_id", ""),
                    "question": market.get("question", ""),
                    "disruption_type": market.get("disruption_type", ""),
                    "alert_type": alert.get("type", ""),
                    "message": alert.get("message", ""),
                    "severity": alert.get("severity", level),
                    "probability": round(prob, 3),
                    "timestamp": alert.get("timestamp", last_updated),
                })

        # Sortiere nach Wahrscheinlichkeit (höchste zuerst)
        markets_summary.sort(key=lambda x: x["current_probability"], reverse=True)

    # Pipeline-State: Szenario-Zusammenfassung
    pipeline_summary = None
    if pipeline_data:
        pipeline_summary = {
            "last_updated": pipeline_data.get("last_updated", ""),
            "scenario_count": len(pipeline_data.get("scenarios", [])),
            "status": pipeline_data.get("status", "unknown"),
        }

    # Gesamtstatus ermitteln
    overall_status = "GREEN"
    if any(m["alert_level"] == "RED" for m in markets_summary):
        overall_status = "RED"
    elif any(m["alert_level"] == "ORANGE" for m in markets_summary):
        overall_status = "ORANGE"
    elif any(m["alert_level"] == "YELLOW" for m in markets_summary):
        overall_status = "YELLOW"

    return {
        "overall_status": overall_status,
        "overall_label": _ALERT_LEVEL_LABELS.get(overall_status, "Unbekannt"),
        "market_count": len(markets_summary),
        "alert_count": len(alerts),
        "last_updated": monitor_data.get("last_updated", "") if monitor_data else "",
        "poll_count": monitor_data.get("poll_count", 0) if monitor_data else 0,
        "top_risks": markets_summary[:5],  # Top 5 nach Wahrscheinlichkeit
        "active_alerts": alerts,
        "pipeline": pipeline_summary,
        "data_available": monitor_data is not None,
    }
