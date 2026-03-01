# PROVIDER MCP-Server

MCP-Server für das PROVIDER-Verbundprojekt (BMBF-gefördert). Exponiert Lieferketten-Simulationsintelligenz als standardisiertes Tool-Set für Claude Desktop und andere MCP-kompatible Assistenten.

## Schnellstart

```bash
cd 04_Apps/provider-mcp
uv sync
uv run provider-mcp
```

## Tools

- **list_scenarios** — Alle 9 PROVIDER-Lieferkettenszenarien
- **get_scenario** — Vollständiges PDL-Szenario
- **get_current_alerts** — Aktuelle Risikoampeln aus Polymarket-Monitoring
- **run_stress_test** — Freitext → Monte-Carlo-Simulation → Risk Score
- **get_simulation_results** — Gecachte Ergebnisse abrufen
- **assess_company_exposure** — Unternehmens-Betroffenheitsanalyse

Siehe [CLAUDE.md](CLAUDE.md) für vollständige Dokumentation.
