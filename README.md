# PROVIDER MCP-Server

MCP-Server für das PROVIDER-Verbundprojekt (BMFTR-gefördert). Exponiert Lieferketten-Simulationsintelligenz als standardisiertes Tool-Set für Claude Desktop und andere MCP-kompatible Assistenten.

## Schnellstart

```bash
git clone https://github.com/implisense/provider-mcp
cd provider-mcp
uv sync
uv run provider-mcp
```

## Tools

- **list_scenarios** — Alle 9 PROVIDER-Lieferkettenszenarien
- **get_scenario** — Vollständiges PDL-Szenario
- **get_current_alerts** — Aktuelle Risikoampeln aus Polymarket-Monitoring
- **run_stress_test** — Freitext → Heuristik-Risikoanalyse → Risk Score
- **get_simulation_results** — Gecachte Ergebnisse abrufen
- **assess_company_exposure** — Unternehmens-Betroffenheitsanalyse

Siehe [CLAUDE.md](CLAUDE.md) für vollständige Dokumentation.
