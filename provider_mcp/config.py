"""Konfiguration für den PROVIDER MCP-Server."""

import os
from pathlib import Path

# Basis-Verzeichnis des Repos (04_Apps/provider-mcp/ -> vier Ebenen hoch -> PROVIDER/)
_THIS_DIR = Path(__file__).parent.parent
_APPS_DIR = _THIS_DIR.parent          # 04_Apps/
_REPO_DIR = _APPS_DIR.parent          # PROVIDER/

# PDL-Szenarien
PDL_SCENARIOS_DIR = Path(
    os.getenv("PDL_SCENARIOS_DIR", str(_REPO_DIR / "06_Szenarien" / "scenarios"))
)

# Terminal State-Dateien
TERMINAL_STATE_DIR = Path(
    os.getenv("TERMINAL_STATE_DIR", str(_APPS_DIR / "terminal"))
)
MONITOR_STATE_FILE = TERMINAL_STATE_DIR / "monitor_state.json"
PIPELINE_STATE_FILE = TERMINAL_STATE_DIR / "pipeline_state.json"

# stress-test-saas API
STRESS_TEST_API_URL = os.getenv("STRESS_TEST_API_URL", "http://localhost:8080")

# Timeouts
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "120"))  # Sekunden (SSE kann lang dauern)
HTTP_CONNECT_TIMEOUT = float(os.getenv("HTTP_CONNECT_TIMEOUT", "5"))

# Fallback: wenn stress-test-saas nicht erreichbar, Heuristik verwenden
USE_HEURISTIC_FALLBACK = os.getenv("USE_HEURISTIC_FALLBACK", "true").lower() == "true"

# Simulationsparameter
DEFAULT_N_SIMULATIONS = int(os.getenv("DEFAULT_N_SIMULATIONS", "200"))
