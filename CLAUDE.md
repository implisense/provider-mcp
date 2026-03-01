# CLAUDE.md — provider-mcp

MCP-Server für das PROVIDER-Verbundprojekt. Exponiert Lieferketten-Simulationsintelligenz als standardisiertes Tool-Set für Claude Desktop und andere MCP-kompatible Assistenten.

## Sprache

Kommunikation auf Deutsch, Code und Variablen auf Englisch.

## Zweck & AP7-Bezug

Dieser MCP-Server erfüllt die **AP7-Anforderungen** (LLM-basierte Auswertung, M16–32) aus dem Förderantrag. Er exponiert PROVIDER-Kapazitäten als MCP-Tools, sodass DATEV-Steuerberater, IAK-Agrarberater und Kommunalplaner ihre vorhandenen Claude-Assistenten damit erweitern können — ohne neue UI oder Login.

## Commands

```bash
# Installation
git clone https://github.com/implisense/provider-mcp
cd provider-mcp
uv sync

# Server starten (stdio, Standard für Claude Desktop)
uv run provider-mcp

# Entwicklungsmodus mit MCP Inspector
uv run mcp dev provider_mcp/server.py

# Tests ausführen
uv run pytest tests/ -v
```

**Wichtig:** Befehle aus dem `provider-mcp/`-Verzeichnis ausführen.

## Architektur

```
Claude Desktop / Enterprise-Chatbot
           |
    [PROVIDER MCP-Server]  ← stdio Transport
          /        \
   PDL-Dateien   Terminal State-Dateien
   (direkt)      (monitor_state.json)
```

```
provider-mcp/
├── CLAUDE.md
├── pyproject.toml               # Python 3.10+, mcp[cli], pyyaml
├── provider_mcp/
│   ├── server.py                # Haupt-MCP-Server, alle @mcp.tool() Definitionen
│   ├── config.py                # Pfade und Umgebungsvariablen
│   ├── tools/
│   │   ├── scenarios.py         # list_scenarios, get_scenario
│   │   ├── alerts.py            # get_current_alerts
│   │   ├── simulation.py        # run_stress_test, get_simulation_results
│   │   └── exposure.py          # assess_company_exposure
│   └── backends/
│       ├── pdl_reader.py        # Liest PDL-YAML-Dateien
│       ├── terminal_reader.py   # Liest terminal state files
│       └── stresstest_client.py # Regelbasierte Heuristik
└── tests/
    ├── test_scenarios.py
    ├── test_alerts.py
    └── test_simulation.py
```

## MCP-Tools (6)

| Tool | Beschreibung | Backend |
|---|---|---|
| `list_scenarios()` | Alle 9 Szenarien mit Metadaten | PDL-Dateien |
| `get_scenario(id)` | Vollständiges PDL-Szenario | PDL-Dateien |
| `get_current_alerts()` | Aktuelle Risikoampeln aus Monitoring | State-Dateien |
| `run_stress_test(description, ...)` | Freitext → Heuristik → Risk Score | Heuristik |
| `get_simulation_results(run_id)` | Gecachtes Ergebnis abrufen | In-Memory-Cache |
| `assess_company_exposure(sector, commodities)` | Betroffenheitsanalyse | PDL + Heuristik |

## MCP-Resources

- `provider://scenarios/` — Alle Szenarien als lesbare Textliste
- `provider://scenarios/{id}` — Einzelszenario als YAML (für Claude-Kontext)

## MCP-Prompt

- `analyze_supply_chain_risk` — Vordefinierter Analyse-Workflow

## Konfiguration (Umgebungsvariablen)

| Variable | Beschreibung |
|---|---|
| `PDL_SCENARIOS_DIR` | Pfad zu PDL-YAML-Dateien (Standard: automatisch ermittelt relativ zu diesem Repo) |
| `TERMINAL_STATE_DIR` | Pfad zu `monitor_state.json` / `pipeline_state.json` (Standard: automatisch) |
| `DEFAULT_N_SIMULATIONS` | Anzahl Heuristik-Läufe (Standard: 200) |

Die Standardpfade werden **automatisch relativ zum Repo-Root** berechnet und müssen nur gesetzt werden, wenn die Verzeichnisstruktur abweicht.

## Claude Desktop Integration

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "provider": {
      "command": "/pfad/zu/uv",
      "args": [
        "run",
        "--directory",
        "/pfad/zu/provider-mcp",
        "provider-mcp"
      ],
      "env": {
        "PDL_SCENARIOS_DIR": "/pfad/zu/pdl-szenarien",
        "TERMINAL_STATE_DIR": "/pfad/zu/terminal-state"
      }
    }
  }
}
```

**Tipp:** `uv`-Pfad ermitteln mit `which uv` — Claude Desktop hat einen eingeschränkten PATH und benötigt den absoluten Pfad.

## Abhängigkeiten

```
mcp[cli]>=1.0.0        # MCP-Framework (FastMCP)
pyyaml>=6.0            # PDL-YAML parsen
python-dotenv>=1.0.0   # .env-Datei Unterstützung
```

## Tests

```bash
uv run pytest tests/ -v              # Alle Tests
uv run pytest tests/test_scenarios.py -v   # Nur Szenario-Tests
uv run pytest tests/ -k "heuristic"  # Nur Heuristik-Tests
```

Alle Tests sind ohne laufende externe Services ausführbar.

## Fehlerbehandlung

- **PDL-Dateien fehlen:** `list_scenarios()` gibt leere Liste + Warnung zurück
- **monitor_state.json fehlt:** `get_current_alerts()` gibt `data_available: False` zurück

## Verifikations-Checkliste

1. `uv run provider-mcp` startet ohne Fehler
2. `uv run mcp dev provider_mcp/server.py` → MCP Inspector zeigt 6 Tools
3. `list_scenarios()` → 9 Szenarien (Soja, Halbleiter, Pharma, ...)
4. `get_scenario("s1-soja")` → vollständiges PDL-Objekt
5. `get_current_alerts()` → State aus `monitor_state.json` (oder `data_available: False`)
6. `run_stress_test("Soja-Import aus Brasilien")` → Risk Score via Heuristik
7. `assess_company_exposure("Landwirtschaft", ["Soja"])` → Betroffenheitsanalyse
