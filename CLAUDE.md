# CLAUDE.md — provider-mcp

MCP-Server für das PROVIDER-Verbundprojekt. Exponiert Lieferketten-Simulationsintelligenz als standardisiertes Tool-Set für Claude Desktop und andere MCP-kompatible Assistenten.

## Sprache

Kommunikation auf Deutsch, Code und Variablen auf Englisch.

## Zweck & AP7-Bezug

Dieser MCP-Server erfüllt die **AP7-Anforderungen** (LLM-basierte Auswertung, M16–32) aus dem Förderantrag. Er exponiert PROVIDER-Kapazitäten als MCP-Tools, sodass DATEV-Steuerberater, IAK-Agrarberater und Kommunalplaner ihre vorhandenen Claude-Assistenten damit erweitern können — ohne neue UI oder Login.

## Commands

```bash
# Installation
cd 04_Apps/provider-mcp
uv sync           # Abhängigkeiten installieren

# Server starten (stdio, Standard für Claude Desktop)
uv run provider-mcp

# Entwicklungsmodus mit MCP Inspector
uv run mcp dev provider_mcp/server.py

# Tests ausführen
uv run pytest tests/ -v

# Mit API-Key-Konfiguration
ANTHROPIC_API_KEY=sk-ant-... uv run provider-mcp
```

**Wichtig:** Befehle von `04_Apps/provider-mcp/` aus ausführen.

## Architektur

```
Claude Desktop / Enterprise-Chatbot
           |
    [PROVIDER MCP-Server]  ← stdio Transport
     /          |          \
PDL-Dateien   terminal     stress-test-saas
(direkt)      state files  (REST API, Port 8080)
```

```
provider-mcp/
├── CLAUDE.md
├── pyproject.toml               # Python 3.10+, mcp[cli], httpx, pyyaml
├── provider_mcp/
│   ├── server.py                # Haupt-MCP-Server, alle @mcp.tool() Definitionen
│   ├── config.py                # Pfade, Ports, Umgebungsvariablen
│   ├── tools/
│   │   ├── scenarios.py         # list_scenarios, get_scenario
│   │   ├── alerts.py            # get_current_alerts
│   │   ├── simulation.py        # run_stress_test, get_simulation_results
│   │   └── exposure.py          # assess_company_exposure
│   └── backends/
│       ├── pdl_reader.py        # Liest PDL-YAML-Dateien
│       ├── terminal_reader.py   # Liest terminal state files
│       └── stresstest_client.py # httpx-Client für stress-test-saas
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
| `run_stress_test(description, ...)` | Freitext → Monte-Carlo → Risk Score | stress-test-saas |
| `get_simulation_results(run_id)` | Gecachtes Ergebnis abrufen | In-Memory-Cache |
| `assess_company_exposure(sector, commodities)` | Betroffenheitsanalyse | PDL + stress-test-saas |

## MCP-Resources

- `provider://scenarios/` — Alle Szenarien als lesbare Textliste
- `provider://scenarios/{id}` — Einzelszenario als YAML (für Claude-Kontext)

## MCP-Prompt

- `analyze_supply_chain_risk` — Vordefinierter Analyse-Workflow

## Datenzugriff

- **PDL-Szenarien:** `../../06_Szenarien/scenarios/*.pdl.yaml` (relativ zum Repo-Root)
- **Alert-Status:** `../terminal/monitor_state.json` + `../terminal/pipeline_state.json`
- **Simulation:** HTTP POST `http://localhost:8080/api/analyze` (SSE-Stream)
- **Fallback:** Wenn stress-test-saas nicht läuft → regelbasierte Heuristik

## Konfiguration (Umgebungsvariablen)

| Variable | Standard | Beschreibung |
|---|---|---|
| `PDL_SCENARIOS_DIR` | `../../06_Szenarien/scenarios` | Pfad zu PDL-YAML-Dateien |
| `TERMINAL_STATE_DIR` | `../terminal` | Pfad zu State-Dateien |
| `STRESS_TEST_API_URL` | `http://localhost:8080` | stress-test-saas URL |
| `HTTP_TIMEOUT` | `120` | Timeout für SSE-Streaming (Sekunden) |
| `USE_HEURISTIC_FALLBACK` | `true` | Heuristik wenn API nicht erreichbar |
| `DEFAULT_N_SIMULATIONS` | `200` | Monte-Carlo-Läufe Standard |

## Claude Desktop Integration

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "provider": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/DEIN_USER/Projekte/Forschung/PROVIDER/04_Apps/provider-mcp",
        "provider-mcp"
      ],
      "env": {
        "STRESS_TEST_API_URL": "http://localhost:8080",
        "PDL_SCENARIOS_DIR": "/Users/DEIN_USER/Projekte/Forschung/PROVIDER/06_Szenarien/scenarios",
        "TERMINAL_STATE_DIR": "/Users/DEIN_USER/Projekte/Forschung/PROVIDER/04_Apps/terminal"
      }
    }
  }
}
```

## Abhängigkeiten

```
mcp[cli]>=1.0.0        # MCP-Framework (FastMCP)
httpx>=0.27.0          # Async HTTP-Client für stress-test-saas
pyyaml>=6.0            # PDL-YAML parsen
python-dotenv>=1.0.0   # .env-Datei Unterstützung
```

## Tests

```bash
uv run pytest tests/ -v              # Alle Tests
uv run pytest tests/test_scenarios.py -v   # Nur Szenario-Tests
uv run pytest tests/ -k "heuristic"  # Nur Heuristik-Tests
```

Alle Tests sind mit Mock-Backends und ohne laufende Services ausführbar.

## Fehlerbehandlung & Fallbacks

- **stress-test-saas nicht erreichbar:** Automatischer Fallback auf regelbasierte Heuristik
- **PDL-Dateien fehlen:** `list_scenarios()` gibt leere Liste + Warnung zurück
- **monitor_state.json fehlt:** `get_current_alerts()` gibt `data_available: False` zurück
- **Timeout SSE-Stream:** Nach `HTTP_TIMEOUT` Sekunden → Fehler-Response

## Verifikations-Checkliste

1. `uv run provider-mcp` startet ohne Fehler
2. `uv run mcp dev provider_mcp/server.py` → MCP Inspector zeigt 6 Tools
3. `list_scenarios()` → 9 Szenarien (Soja, Halbleiter, Pharma, ...)
4. `get_scenario("s1-soja")` → vollständiges PDL-Objekt
5. `get_current_alerts()` → gibt State aus `monitor_state.json` (oder `data_available: False`)
6. `run_stress_test("Soja-Import aus Brasilien")` → Risk Score (Heuristik oder echte Simulation)
7. `assess_company_exposure("Landwirtschaft", ["Soja"])` → Betroffenheitsanalyse
