"""Tests für Simulation-Backend und Tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from provider_mcp.backends.stresstest_client import (
    _heuristic_fallback,
    _results_cache,
    get_cached_result,
)
from provider_mcp.tools.simulation import (
    get_simulation_results_impl,
    run_stress_test_impl,
)


# ── Heuristik-Tests ──────────────────────────────────────────────────────────

class TestHeuristicFallback:
    def test_returns_complete_status(self):
        result = _heuristic_fallback("test_id", "Soja-Import aus Brasilien")
        assert result["status"] == "complete"
        assert result["run_id"] == "test_id"
        assert result["source"] == "heuristic_fallback"

    def test_high_risk_keywords(self):
        result = _heuristic_fallback("id1", "Krieg und Sanktionen und Katastrophe")
        assert result["risk_score"] > 50

    def test_low_risk_keywords(self):
        result = _heuristic_fallback("id2", "Diversifizierte Lieferkette mit Backup")
        assert result["risk_score"] < 50

    def test_soja_increases_risk(self):
        base = _heuristic_fallback("id3", "Normales Unternehmen")
        soja = _heuristic_fallback("id4", "Soja-Importeur aus Brasilien")
        assert soja["risk_score"] >= base["risk_score"]

    def test_risk_score_bounds(self):
        result = _heuristic_fallback("id5", "Krieg Sanktion Katastrophe Embargo Monopol")
        assert 0 <= result["risk_score"] <= 100

    def test_includes_recommendations(self):
        result = _heuristic_fallback("id6", "Test")
        assert len(result["recommendations"]) > 0

    def test_caches_result(self):
        result = _heuristic_fallback("cache_test", "Test")
        assert get_cached_result("cache_test") == result

    def test_grade_assignment(self):
        high = _heuristic_fallback("grade_high", "Krieg Krieg Krieg Sanktion Katastrophe Monopol")
        assert high["risk_grade"] in ("D", "F", "C")

        low = _heuristic_fallback("grade_low", "Diversifiziert Backup Alternative Europa")
        assert low["risk_grade"] in ("A", "B")


# ── Cache-Tests ───────────────────────────────────────────────────────────────

class TestResultsCache:
    def setup_method(self):
        """Cache vor jedem Test leeren."""
        _results_cache.clear()

    def test_cache_miss(self):
        assert get_cached_result("nonexistent_id") is None

    def test_cache_hit_after_heuristic(self):
        _heuristic_fallback("my_run", "Test")
        result = get_cached_result("my_run")
        assert result is not None
        assert result["run_id"] == "my_run"


# ── Simulation-Tool-Tests ─────────────────────────────────────────────────────

class TestRunStressTestImpl:
    @pytest.mark.asyncio
    async def test_with_heuristic_fallback(self):
        """run_stress_test verwendet Heuristik wenn stress-test-saas nicht erreichbar."""
        heuristic_result = {
            "run_id": "abc12345",
            "status": "complete",
            "risk_score": 55.0,
            "risk_grade": "C",
            "recommendations": ["Empfehlung 1"],
            "source": "heuristic_fallback",
            "note": "Heuristik-Ergebnis",
        }

        with patch(
            "provider_mcp.tools.simulation._run_stress_test",
            new=AsyncMock(return_value=heuristic_result),
        ):
            result = await run_stress_test_impl("Soja-Import aus Brasilien")

        assert result["run_id"] == "abc12345"
        assert result["risk_score"] == 55.0
        assert result["risk_grade"] == "C"
        assert result["status"] == "complete"
        assert "note" in result

    @pytest.mark.asyncio
    async def test_scenario_ids_added_to_description(self):
        """scenario_ids werden als Kontext in die Beschreibung eingebaut."""
        captured = {}

        async def mock_run(description, **kwargs):
            captured["description"] = description
            return {"run_id": "x", "status": "complete", "risk_score": 30.0}

        with patch("provider_mcp.tools.simulation._run_stress_test", new=mock_run):
            await run_stress_test_impl(
                "Meine Lieferkette", scenario_ids=["s1-soja", "s4-duengemittel-adblue"]
            )

        assert "s1-soja" in captured["description"]
        assert "s4-duengemittel-adblue" in captured["description"]
        assert "Meine Lieferkette" in captured["description"]

    @pytest.mark.asyncio
    async def test_error_response(self):
        """Fehler werden korrekt weitergegeben."""
        error_result = {
            "run_id": "err123",
            "status": "error",
            "error": "Verbindung verweigert",
        }

        with patch(
            "provider_mcp.tools.simulation._run_stress_test",
            new=AsyncMock(return_value=error_result),
        ):
            result = await run_stress_test_impl("Test")

        assert result["status"] == "error"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_no_scenario_ids(self):
        """Ohne scenario_ids wird die Beschreibung unverändert übergeben."""
        captured = {}

        async def mock_run(description, **kwargs):
            captured["description"] = description
            return {"run_id": "x", "status": "complete", "risk_score": 30.0}

        with patch("provider_mcp.tools.simulation._run_stress_test", new=mock_run):
            await run_stress_test_impl("Originalbeschreibung")

        assert captured["description"] == "Originalbeschreibung"


class TestGetSimulationResultsImpl:
    def setup_method(self):
        _results_cache.clear()

    def test_found_in_cache(self):
        _results_cache["known_id"] = {"run_id": "known_id", "risk_score": 42.0}
        result = get_simulation_results_impl("known_id")
        assert result["risk_score"] == 42.0

    def test_not_in_cache(self):
        result = get_simulation_results_impl("unknown_id")
        assert "error" in result
        assert "unknown_id" in result["error"]
        assert "info" in result
