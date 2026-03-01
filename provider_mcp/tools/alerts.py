"""MCP-Tool: get_current_alerts."""

from __future__ import annotations

from typing import Any

from provider_mcp.backends.terminal_reader import get_current_alerts as _get_alerts


def get_current_alerts_impl() -> dict[str, Any]:
    """
    Gibt aktuelle Risikoampeln und Alerts aus dem PROVIDER-Monitoring zurück.

    Liest die Terminal-State-Dateien (monitor_state.json, pipeline_state.json)
    und gibt strukturierte Alert-Informationen zurück.

    Ampelfarben:
    - RED (≥75%): Kritisches Risiko, sofortiger Handlungsbedarf
    - ORANGE (≥55%): Hohes Risiko, Beobachtung empfohlen
    - YELLOW (≥35%): Erhöhtes Risiko, Vorsicht geboten
    - GREEN (<35%): Normales Niveau

    Returns dict mit overall_status, top_risks und active_alerts.
    Wenn kein Monitoring läuft, gibt data_available=False zurück.
    """
    result = _get_alerts()

    if not result["data_available"]:
        result["info"] = (
            "Kein Monitoring aktiv. Starten mit: "
            "cd 04_Apps && python -m terminal.monitor --demo"
        )

    return result
