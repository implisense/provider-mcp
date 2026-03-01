"""Tests für Alert-Backend und Tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from provider_mcp.backends.terminal_reader import (
    _probability_to_alert_level,
    get_current_alerts,
)
from provider_mcp.tools.alerts import get_current_alerts_impl


# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def _write_monitor_state(tmp_path: Path, markets: list[dict]) -> Path:
    """Schreibt eine temporäre monitor_state.json."""
    state = {
        "last_updated": "2026-02-28T10:00:00+00:00",
        "poll_count": 42,
        "markets": markets,
    }
    path = tmp_path / "monitor_state.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    return path


SAMPLE_MARKET_HIGH = {
    "market_id": "ew_ukraine",
    "question": "Waffenstillstand in der Ukraine bis 2026?",
    "disruption_type": "geopolitical_conflict",
    "eu_relevance": 1.0,
    "current_probability": 0.80,
    "previous_probability": 0.75,
    "probability_history": [0.80],
    "timestamp_history": ["2026-02-28T10:00:00+00:00"],
    "alerts": [
        {
            "type": "THRESHOLD_CROSSED",
            "message": "Kritische Schwelle überschritten",
            "severity": "RED",
            "timestamp": "2026-02-28T10:00:00+00:00",
        }
    ],
}

SAMPLE_MARKET_LOW = {
    "market_id": "energy_stable",
    "question": "Energiepreise stabil?",
    "disruption_type": "energy_supply",
    "eu_relevance": 0.8,
    "current_probability": 0.20,
    "previous_probability": 0.22,
    "probability_history": [0.20],
    "timestamp_history": ["2026-02-28T10:00:00+00:00"],
    "alerts": [],
}


# ── Unit-Tests ────────────────────────────────────────────────────────────────

class TestProbabilityToAlertLevel:
    def test_red_threshold(self):
        assert _probability_to_alert_level(0.75) == "RED"
        assert _probability_to_alert_level(0.90) == "RED"
        assert _probability_to_alert_level(1.0) == "RED"

    def test_orange_threshold(self):
        assert _probability_to_alert_level(0.55) == "ORANGE"
        assert _probability_to_alert_level(0.65) == "ORANGE"
        assert _probability_to_alert_level(0.74) == "ORANGE"

    def test_yellow_threshold(self):
        assert _probability_to_alert_level(0.35) == "YELLOW"
        assert _probability_to_alert_level(0.45) == "YELLOW"
        assert _probability_to_alert_level(0.54) == "YELLOW"

    def test_green_threshold(self):
        assert _probability_to_alert_level(0.0) == "GREEN"
        assert _probability_to_alert_level(0.20) == "GREEN"
        assert _probability_to_alert_level(0.34) == "GREEN"


class TestGetCurrentAlerts:
    def test_no_state_files(self, tmp_path):
        """Gibt data_available=False zurück wenn keine State-Dateien vorhanden."""
        result = get_current_alerts(
            monitor_state_file=tmp_path / "nonexistent_monitor.json",
            pipeline_state_file=tmp_path / "nonexistent_pipeline.json",
        )
        assert result["data_available"] is False
        assert result["market_count"] == 0
        assert result["alert_count"] == 0
        assert result["overall_status"] == "GREEN"

    def test_with_high_risk_market(self, tmp_path):
        """Erkennt kritisches Risiko und setzt overall_status auf RED."""
        _write_monitor_state(tmp_path, [SAMPLE_MARKET_HIGH])
        result = get_current_alerts(
            monitor_state_file=tmp_path / "monitor_state.json",
            pipeline_state_file=tmp_path / "nonexistent.json",
        )

        assert result["data_available"] is True
        assert result["overall_status"] == "RED"
        assert result["market_count"] == 1
        assert result["alert_count"] >= 1
        assert len(result["top_risks"]) == 1
        assert result["top_risks"][0]["alert_level"] == "RED"

    def test_with_low_risk_market(self, tmp_path):
        """Niedrigrisikomarkt → GREEN."""
        _write_monitor_state(tmp_path, [SAMPLE_MARKET_LOW])
        result = get_current_alerts(
            monitor_state_file=tmp_path / "monitor_state.json",
            pipeline_state_file=tmp_path / "nonexistent.json",
        )

        assert result["overall_status"] == "GREEN"
        assert result["alert_count"] == 0

    def test_top_risks_sorted_by_probability(self, tmp_path):
        """Top-Risks sind nach Wahrscheinlichkeit absteigend sortiert."""
        markets = [SAMPLE_MARKET_LOW, SAMPLE_MARKET_HIGH]
        _write_monitor_state(tmp_path, markets)
        result = get_current_alerts(
            monitor_state_file=tmp_path / "monitor_state.json",
            pipeline_state_file=tmp_path / "nonexistent.json",
        )

        probs = [m["current_probability"] for m in result["top_risks"]]
        assert probs == sorted(probs, reverse=True)

    def test_top_risks_limit_5(self, tmp_path):
        """Nur die 5 höchsten Risiken werden zurückgegeben."""
        # 7 Märkte mit absteigenden Wahrscheinlichkeiten
        markets = [
            {**SAMPLE_MARKET_LOW, "market_id": f"m_{i}",
             "current_probability": 0.9 - i * 0.1, "alerts": []}
            for i in range(7)
        ]
        _write_monitor_state(tmp_path, markets)
        result = get_current_alerts(
            monitor_state_file=tmp_path / "monitor_state.json",
            pipeline_state_file=tmp_path / "nonexistent.json",
        )

        assert len(result["top_risks"]) == 5

    def test_mixed_risk_overall_status(self, tmp_path):
        """Bei gemischten Risiken dominiert der höchste Level."""
        _write_monitor_state(tmp_path, [SAMPLE_MARKET_HIGH, SAMPLE_MARKET_LOW])
        result = get_current_alerts(
            monitor_state_file=tmp_path / "monitor_state.json",
            pipeline_state_file=tmp_path / "nonexistent.json",
        )
        assert result["overall_status"] == "RED"

    def test_corrupt_json_returns_empty(self, tmp_path):
        """Korrupte JSON-Datei → data_available=False."""
        path = tmp_path / "monitor_state.json"
        path.write_text("{ invalid json }", encoding="utf-8")

        result = get_current_alerts(
            monitor_state_file=path,
            pipeline_state_file=tmp_path / "nonexistent.json",
        )
        assert result["data_available"] is False


class TestGetCurrentAlertsTool:
    def test_adds_info_when_no_data(self, tmp_path):
        """Tool fügt Info-Hinweis hinzu wenn kein Monitoring aktiv."""
        from unittest.mock import patch

        no_data_result = {
            "data_available": False,
            "overall_status": "GREEN",
            "overall_label": "Normal",
            "market_count": 0,
            "alert_count": 0,
            "last_updated": "",
            "poll_count": 0,
            "top_risks": [],
            "active_alerts": [],
            "pipeline": None,
        }

        with patch("provider_mcp.tools.alerts._get_alerts", return_value=no_data_result):
            result = get_current_alerts_impl()

        assert "info" in result
        assert "monitor" in result["info"].lower()
