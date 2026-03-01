"""PROVIDER MCP-Server — Haupt-Einstiegspunkt."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from provider_mcp.backends.pdl_reader import get_scenario_yaml, load_all_scenarios
from provider_mcp.config import PDL_SCENARIOS_DIR, STRESS_TEST_API_URL, TERMINAL_STATE_DIR
from provider_mcp.tools.alerts import get_current_alerts_impl
from provider_mcp.tools.exposure import assess_company_exposure_impl
from provider_mcp.tools.scenarios import get_scenario_impl, list_scenarios_impl
from provider_mcp.tools.simulation import (
    get_simulation_results_impl,
    run_stress_test_impl,
)

mcp = FastMCP(
    "PROVIDER",
    instructions=(
        "Du bist der PROVIDER-Assistent für Versorgungssicherheitsanalysen. "
        "PROVIDER ist ein BMFTR-gefördertes Frühwarnsystem für Lieferkettenengpässe "
        "außerhalb klassischer KRITIS-Sektoren. "
        "Nutze die verfügbaren Tools, um Szenarien zu analysieren, "
        "aktuelle Risikoampeln abzurufen und Unternehmensbetroffenheiten zu bewerten."
    ),
)


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_scenarios() -> dict:
    """
    Listet alle verfügbaren PROVIDER-Lieferkettenszenarien auf.

    Gibt alle 9 PDL-Szenarien (Soja, Halbleiter, Pharma, Düngemittel, Wasser,
    Rechenzentren, Seltene Erden, Seefracht, Unterwasserkabel) mit kompakten
    Metadaten zurück.

    Returns:
        scenarios: Liste mit id, name, sector, criticality, description, entity_count, event_count
        count: Anzahl verfügbarer Szenarien
        sectors: Liste aller abgedeckten Sektoren
    """
    return list_scenarios_impl()


@mcp.tool()
def get_scenario(scenario_id: str) -> dict:
    """
    Gibt vollständige Details eines PROVIDER-Szenarios zurück.

    Args:
        scenario_id: Szenario-Bezeichner. Akzeptiert:
            - Datei-ID: 's1-soja', 's2-halbleiter', 's3-pharma', 's4-duengemittel-adblue',
              's5-wasseraufbereitung', 's6-rechenzentren', 's7-seltene-erden',
              's8-seefracht', 's9-unterwasserkabel'
            - Kurzname: 'soja', 'halbleiter', 'pharma', 'wasser', etc.
            - Interne ID: 'soy_feed_disruption', 'semiconductor_shortage', etc.

    Returns:
        Vollständiges PDL-Objekt mit entities, events, flows und yaml-Inhalt
    """
    return get_scenario_impl(scenario_id)


@mcp.tool()
def get_current_alerts() -> dict:
    """
    Gibt aktuelle Risikoampeln aus dem PROVIDER-Echtzeit-Monitoring zurück.

    Liest die Polymarket-basierten Marktwahrscheinlichkeiten und Alert-Zustände
    aus dem Terminal-Monitoring-System.

    Ampelfarben:
    - RED (≥75%): Kritisches Risiko, sofortiger Handlungsbedarf
    - ORANGE (≥55%): Hohes Risiko
    - YELLOW (≥35%): Erhöhtes Risiko
    - GREEN (<35%): Normales Niveau

    Returns:
        overall_status: Gesamtstatus (GREEN/YELLOW/ORANGE/RED)
        top_risks: Die 5 höchsten Einzelrisiken mit Wahrscheinlichkeiten
        active_alerts: Aktive Alert-Ereignisse mit Typ und Schwere
        data_available: False wenn kein Monitoring aktiv
    """
    return get_current_alerts_impl()


@mcp.tool()
async def run_stress_test(
    description: str,
    scenario_ids: list[str] | None = None,
    n_simulations: int = 200,
) -> dict:
    """
    Führt einen Monte-Carlo-Stress-Test für eine Lieferkettenbeschreibung durch.

    Konvertiert die Freitext-Beschreibung via LLM in ein PDL-Szenario,
    führt N Monte-Carlo-Simulationsläufe durch und berechnet Risk Score + Empfehlungen.

    Args:
        description: Freitext-Beschreibung der Lieferkette oder des Risikos.
            Beispiele:
            - "Mein Unternehmen importiert Soja aus Brasilien für Tierfutterproduktion."
            - "Wir sind abhängig von TSMC-Chips für unsere Elektronikmontage in Bayern."
            - "Unser Pharmaunternehmen bezieht 80% der API-Wirkstoffe aus Indien."
        scenario_ids: Optionale PDL-Szenario-IDs als zusätzlicher Kontext.
        n_simulations: Anzahl Monte-Carlo-Läufe (Standard 200, max empfohlen 1000).

    Returns:
        run_id: ID für get_simulation_results
        risk_score: Gesamtrisiko 0-100 (>65 = kritisch)
        risk_grade: Note A (niedrig) bis F (kritisch)
        entity_risks: Risiken je Lieferkettenentität
        recommendations: Priorisierte Handlungsempfehlungen
    """
    return await run_stress_test_impl(description, scenario_ids, n_simulations)


@mcp.tool()
def get_simulation_results(run_id: str) -> dict:
    """
    Gibt gecachte Ergebnisse eines zuvor gestarteten Stress-Tests zurück.

    Args:
        run_id: Run-ID aus dem Rückgabewert von run_stress_test (z.B. 'a3f7b2c1')

    Returns:
        Vollständiges Ergebnis-Dict mit risk_score, entity_risks, recommendations etc.
        Gibt Fehler zurück wenn run_id nicht im Cache (In-Memory, nur aktuelle Session).
    """
    return get_simulation_results_impl(run_id)


@mcp.tool()
async def assess_company_exposure(sector: str, commodities: list[str]) -> dict:
    """
    Analysiert die Betroffenheit eines Unternehmens durch Lieferkettenrisiken.

    Findet relevante PROVIDER-Szenarien für den Sektor und die Commodities,
    berechnet einen Expositions-Score und gibt konkrete Maßnahmen zurück.

    Args:
        sector: Unternehmenssektor. Beispiele:
            'Landwirtschaft', 'Pharma', 'Halbleiter', 'Automotive',
            'Logistik', 'Rechenzentren', 'Elektronik', 'Rohstoffe'
        commodities: Liste kritischer Inputmaterialien. Beispiele:
            ['Soja', 'Düngemittel'], ['Lithium', 'Kobalt', 'Seltene Erden'],
            ['Pharmawirkstoffe', 'API'], ['Halbleiter', 'Chips']

    Returns:
        exposure_level: HIGH/MEDIUM/LOW
        risk_score: Numerischer Score 0-100
        relevant_scenarios: Relevante PROVIDER-Szenarien mit Details
        key_vulnerabilities: Kritische Schwachstellen
        recommendations: Konkrete Maßnahmen zur Risikoreduktion
    """
    return await assess_company_exposure_impl(sector, commodities)


# ── Resources ─────────────────────────────────────────────────────────────────

@mcp.resource("provider://scenarios/")
def resource_scenarios_list() -> str:
    """Alle PROVIDER-Szenarien als kompakte Textliste."""
    scenarios = load_all_scenarios()
    if not scenarios:
        return "Keine Szenarien verfügbar. PDL_SCENARIOS_DIR prüfen."

    lines = ["# PROVIDER Lieferkettenszenarien\n"]
    for s in scenarios:
        lines.append(
            f"## {s['name']} ({s['file_id']})\n"
            f"- **Sektor:** {s['sector']}\n"
            f"- **Kritikalität:** {s['criticality']}\n"
            f"- **Entities:** {s['entity_count']}, Events: {s['event_count']}\n"
            f"- {s['description']}\n"
        )
    return "\n".join(lines)


@mcp.resource("provider://scenarios/{scenario_id}")
def resource_scenario_yaml(scenario_id: str) -> str:
    """PDL-YAML-Inhalt eines einzelnen Szenarios für Claude-Kontext."""
    yaml_content = get_scenario_yaml(scenario_id)
    if yaml_content is None:
        available = [s["file_id"] for s in load_all_scenarios()]
        return (
            f"Szenario '{scenario_id}' nicht gefunden.\n"
            f"Verfügbar: {', '.join(available)}"
        )
    return yaml_content


# ── Prompt ────────────────────────────────────────────────────────────────────

@mcp.prompt()
def analyze_supply_chain_risk(
    company_description: str = "",
    sector: str = "",
    commodities: str = "",
) -> str:
    """
    Vordefinierter PROVIDER-Analyse-Prompt für Versorgungsrisiken.

    Args:
        company_description: Kurzbeschreibung des Unternehmens und seiner Lieferkette
        sector: Unternehmenssektor (z.B. 'Pharma', 'Automotive')
        commodities: Kommagetrennte Liste kritischer Commodities
    """
    parts = [
        "Du bist ein PROVIDER-Versorgungssicherheitsexperte. "
        "Analysiere die Lieferkettenrisiken des folgenden Unternehmens:\n"
    ]

    if company_description:
        parts.append(f"**Unternehmen:** {company_description}\n")
    if sector:
        parts.append(f"**Sektor:** {sector}\n")
    if commodities:
        parts.append(f"**Kritische Commodities:** {commodities}\n")

    parts.append("""
Führe folgende Schritte durch:
1. Rufe `list_scenarios()` auf, um verfügbare PROVIDER-Szenarien zu sehen
2. Rufe `get_current_alerts()` auf, um aktuelle Risikoampeln zu prüfen
3. Wenn ein relevantes Szenario existiert: `get_scenario(scenario_id)` für Details
4. Führe `assess_company_exposure(sector, commodities)` durch für die Betroffenheitsanalyse
5. Optional: `run_stress_test(description)` für eine tiefe Monte-Carlo-Simulation

Erstelle abschließend einen strukturierten Bericht mit:
- Aktuelle Risikolage (Ampelstatus)
- Betroffenheitsgrad (HIGH/MEDIUM/LOW) mit Begründung
- Top 3 kritische Schwachstellen
- Priorisierte Handlungsempfehlungen
""")

    return "".join(parts)


# ── Startup-Info ──────────────────────────────────────────────────────────────

def _print_startup_info() -> None:
    scenarios_ok = PDL_SCENARIOS_DIR.exists()
    terminal_ok = TERMINAL_STATE_DIR.exists()
    n_scenarios = len(list(PDL_SCENARIOS_DIR.glob("*.yaml"))) if scenarios_ok else 0

    print("=" * 60)
    print("PROVIDER MCP-Server")
    print("=" * 60)
    print(f"PDL-Szenarien:  {'✓' if scenarios_ok else '✗'} {PDL_SCENARIOS_DIR} ({n_scenarios} Dateien)")
    print(f"Terminal-State: {'✓' if terminal_ok else '✗'} {TERMINAL_STATE_DIR}")
    print(f"Stress-Test:    {STRESS_TEST_API_URL} (Fallback aktiv)")
    print("=" * 60)
    print("Tools: list_scenarios, get_scenario, get_current_alerts,")
    print("       run_stress_test, get_simulation_results, assess_company_exposure")
    print("=" * 60)


def main() -> None:
    """Einstiegspunkt für `provider-mcp` CLI-Kommando."""
    _print_startup_info()
    mcp.run()


if __name__ == "__main__":
    main()
