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

# Simulationsparameter
DEFAULT_N_SIMULATIONS = int(os.getenv("DEFAULT_N_SIMULATIONS", "200"))
