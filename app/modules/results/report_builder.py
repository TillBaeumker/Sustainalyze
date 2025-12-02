"""
report_builder.py
=================

Modul zur Erzeugung des strukturierten Analyseberichts für die
Nachhaltigkeitsbewertung digitaler Editionen.

Dieses Modul formt die zuvor aggregierten Analysedaten in ein
oberflächenorientiertes ViewModel um.
"""

from __future__ import annotations
import os
import json
from typing import Any, Dict, List
from urllib.parse import urlparse

from openai import OpenAI
from app.modules.analysis.llm_analysis import merge_results


# -------------------------------------------------------------------
# UI-Gruppierung der Bewertungsindikatoren
# -------------------------------------------------------------------
FIELDS_UI: Dict[str, List[str]] = {
    "Institution und Governance": [
        "institution_present",
        "roles_responsibilities_present",
        "funding_present",
        "continuation_archiving_preservation_present",
        "contact_info_present",
        "community_present",
    ],
    "Standardisierung und Interoperabilität": [
        "tei_xml_presence",
        "f2ab_combined",
        "normdata_presence",
        "api_presence",
        "pi_documentation",
    ],
    "Offenheit von Code, Daten und Software": [
        "repos_oss_practice",
        "wappalyzer_open_closed",
        "downloads_presence",
        "open_license",
    ],
    "Technische Robustheit und Langzeitverfügbarkeit": [
        "isolation",
        "staticization",
        "link_functionality",
        "persistent_ids",
    ],
    "FAIR (separat)": [
        "fair_overall",
    ],
}


# -------------------------------------------------------------------
# Lesbare Bezeichnungen für Indikatoren
# -------------------------------------------------------------------
INDICATOR_LABELS: Dict[str, str] = {
    "wappalyzer_open_closed": "Open-Source-Technologien",
    "fair_overall": "FAIR-Checker",
    "isolation": "Isolation",
    "staticization": "Statisierung",
    "link_functionality": "Link-Funktionalität",
    "tei_xml_presence": "TEI-Präsenz",
    "downloads_presence": "Downloads verfügbar",
    "f2ab_combined": "strukturierte Metadaten & Vokabulare",
    "normdata_presence": "Normdaten-Verknüpfungen",
    "repos_oss_practice": "Repository verfügbar",
    "institution_present": "Institution vorhanden",
    "roles_responsibilities_present": "Rollen & Verantwortlichkeiten",
    "funding_present": "Förderung angegeben",
    "continuation_archiving_preservation_present": "Strategie zur Fortführung/Sicherung",
    "contact_info_present": "Kontaktinformationen",
    "community_present": "Community / Beteiligung",
    "pi_documentation": "Dokumentation",
    "api_presence": "Technische API",
    "open_license": "Offene Lizenz",
    "persistent_ids": "Persistente Identifier",
}


# -------------------------------------------------------------------
# Scoring-Modul importieren
# -------------------------------------------------------------------
try:
    from app.modules.results.scoring import compute_scoring
    print("[DEBUG] compute_scoring erfolgreich importiert")
except Exception as e:
    print("[IMPORT-ERROR] compute_scoring konnte nicht geladen werden:", e)

    def compute_scoring(_result):
        print("[DEBUG] Fallback compute_scoring aktiv")
        return {"global": {}, "total": {"score": None}, "fair": {"score": None}}


# -------------------------------------------------------------------
# OpenAI-Client
# -------------------------------------------------------------------
GPT_MODEL = "gpt-4o-mini"
_api_key = os.getenv("OPENAI_API_KEY")
_client = OpenAI(api_key=_api_key) if _api_key else None


# -------------------------------------------------------------------
# Hauptfunktion zur Berichterzeugung
# -------------------------------------------------------------------
def build_report(result: Dict[str, Any]) -> Dict[str, Any]:
    print("\n[DEBUG] build_report() gestartet")

    scoring = compute_scoring(result)
    print("[DEBUG] compute_scoring -> OK")

    sw = build_strengths_and_weaknesses(scoring)
    print("[DEBUG] Stärke/Schwächen -> OK")

    report = build_view_model(result, scoring, sw)
    print("[DEBUG] build_view_model -> OK")

    report["conclusion"] = generate_conclusion(scoring, report)
    print("[DEBUG] Fazit erzeugt")

    return report


# -------------------------------------------------------------------
# Stärken/Schwächen aus dem Scoring ableiten
# -------------------------------------------------------------------
def build_strengths_and_weaknesses(scoring: Dict[str, Any]) -> Dict[str, List[str]]:
    g = scoring.get("global", {}) or {}
    strengths: List[str] = []
    weaknesses: List[str] = []

    def s(key: str) -> int:
        val = g.get(key, {}).get("score")
        return int(val) if isinstance(val, (int, float)) else -1

    # --- Technische Robustheit -------------------------------------------------
    if s("isolation") > 0:
        strengths.append("Hinweise auf isolierende Ausführungsumgebungen gefunden")
    else:
        weaknesses.append("Keine Hinweise auf isolierende Ausführungsumgebungen gefunden")

    if s("staticization") > 0:
        strengths.append("Hinweise auf Statisierung gefunden")
    else:
        weaknesses.append("Keine Hinweise auf Statisierung gefunden")

    lf = s("link_functionality")
    if lf >= 80:
        strengths.append("Die meisten internen Links funktionieren zuverlässig")
    elif 50 <= lf < 80:
        weaknesses.append("Teilweise fehlerhafte interne Links")
    elif 0 <= lf < 50:
        weaknesses.append("Viele defekte interne Links")
    else:
        weaknesses.append("interne Link-Funktionalität nicht bewertbar")

    if s("persistent_ids") > 0:
        strengths.append("Persistente Identifier vorhanden")
    else:
        weaknesses.append("Keine persistenten Identifier gefunden")

    # --- Standardisierung ------------------------------------------------------
    if s("tei_xml_presence") > 0:
        strengths.append("TEI-XML oder strukturierte Editionsdaten vorhanden")
    else:
        weaknesses.append("Keine TEI-XML-Dateien gefunden")

    f2 = s("f2ab_combined")
    if f2 == 100:
        strengths.append("Strukturierte Metadaten und kontrollierte Vokabulare gefunden")
    elif f2 == 75:
        strengths.append("Strukturierte Metadaten vorhanden")
        weaknesses.append("Vokabulare unklar oder nicht nachweisbar")
    elif f2 == 50:
        strengths.append("LLM-Hinweise auf strukturierte Metadaten vorhanden")
        weaknesses.append("Keine klaren Nachweise strukturierter Vokabulare")
    else:
        weaknesses.append("Keine Hinweise auf strukturierte Metadaten gefunden")

    if s("normdata_presence") > 0:
        strengths.append("Normdaten-Verknüpfungen vorhanden")
    else:
        weaknesses.append("Keine Normdaten-Verknüpfungen gefunden")

    if s("api_presence") > 0:
        strengths.append("Technische API-Schnittstellen nachweisbar")
    else:
        weaknesses.append("Keine technischen APIs gefunden")

    if s("pi_documentation") > 0:
        strengths.append("Dokumentation vorhanden")
    else:
        weaknesses.append("Keine Dokumentation gefunden")

    # --- Institution/Governance ------------------------------------------------
    if s("institution_present") == 100:
        strengths.append("Klare institutionelle Trägerschaft erkennbar")
    else:
        weaknesses.append("Institutionelle Trägerschaft nicht erkennbar")

    if s("roles_responsibilities_present") == 100:
        strengths.append("Rollen und Verantwortlichkeiten dokumentiert")
    else:
        weaknesses.append("Keine Rollen oder Verantwortlichkeiten erkennbar")

    if s("funding_present") == 100:
        strengths.append("Angaben zu Förderung / Laufzeit vorhanden")
    else:
        weaknesses.append("Keine Förderangaben vorhanden")

    if s("continuation_archiving_preservation_present") == 100:
        strengths.append("Hinweise auf Fortführung/Sicherung vorhanden")
    else:
        weaknesses.append("Keine Hinweise auf langfristige Sicherung")

    if s("contact_info_present") == 100:
        strengths.append("Kontaktinformationen vorhanden")
    else:
        weaknesses.append("Keine Kontaktinformationen gefunden")

    if s("community_present") == 100:
        strengths.append("Community-Beteiligung nachweisbar")
    else:
        weaknesses.append("Keine Community-Hinweise gefunden")

    # --- Offenheit --------------------------------------------------------------
    if s("repos_oss_practice") > 0:
        strengths.append("Code-Repository vorhanden")
    else:
        weaknesses.append("Kein Repository gefunden")

    if s("wappalyzer_open_closed") > 0:
        strengths.append("Open-Source-Technologien nachweisbar")
    else:
        weaknesses.append("Keine Open-Source-Technologien gefunden")

    ol = s("open_license")
    if ol == 100:
        strengths.append("Offene Lizenz vorhanden")
    elif ol == 50:
        strengths.append("Gemischte Lizenzsituation")
    else:
        weaknesses.append("Keine offene Lizenz")

    if s("downloads_presence") > 0:
        strengths.append("Downloadbare Daten verfügbar")
    else:
        weaknesses.append("Keine Downloadmöglichkeiten vorhanden")

    # --- FAIR-Checker -----------------------------------------------------------
    fair_info = g.get("fair_overall", {}) or {}
    fair_score = fair_info.get("score")

    if isinstance(fair_score, (int, float)):
        if fair_score >= 70:
            strengths.append("FAIR-Checker: hoher FAIR-Score")
        elif fair_score >= 40:
            strengths.append("FAIR-Checker: mittlerer FAIR-Score")
        else:
            weaknesses.append("FAIR-Checker: niedriger FAIR-Score")
    else:
        weaknesses.append("FAIR-Checker-Ergebnis nicht verfügbar")

    strengths = sorted(set(strengths))
    weaknesses = sorted(set(weaknesses))

    return {"strengths": strengths, "weaknesses": weaknesses}


# -------------------------------------------------------------------
# LLM-Fazit generieren
# -------------------------------------------------------------------
def generate_conclusion(scoring: Dict[str, Any], report: Dict[str, Any]) -> str:
    project = report.get("project_name", "Unbekannt")
    pages = report.get("valid_pages", 0)
    host_country = report.get("hosting_country", "–")
    host_org = report.get("hosting_org", "–")
    total = scoring.get("total", {})
    score = total.get("score")
    band = total.get("band", "unbekannt")

    llm_data = json.dumps(
        report.get("llm_analysis_aggregated") or {},
        ensure_ascii=False,
        indent=2,
    )

    if not _client:
        return f"{project}: Zusammenfassung nicht verfügbar (kein LLM)."

    try:
        res = _client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Erstelle eine kurze, klar verständliche Zusammenfassung des Projekts. "
                        "Keine Listen, kein Markdown, keine Symbole, keine Fettschrift. "
                        "Schreibe in 3 bis maximal 5 Sätzen. "
                        "Nenne Titel, Herausgeber, Institution, Förderhinweise und zentrale technische Merkmale, "
                        "wenn sie eindeutig aus den Daten hervorgehen. "
                        "Nicht spekulieren. "
                        "Der letzte Satz MUSS lauten: "
                        "'Die Einschätzung bezieht sich ausschließlich auf den im Rahmen der geprüften Seiten sichtbaren Ausschnitt.'"
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Projektname: {project}\n"
                        f"Score: {score} (Band: {band})\n"
                        f"Hosting: {host_country} ({host_org})\n"
                        f"Analysierte Seiten: {pages}\n\n"
                        f"LLM-Daten (Projektinfos, Herausgeber, institutionelle Daten, Jahresangaben, Repositories, Dokumentation, APIs usw.):\n"
                        f"{llm_data}\n\n"
                        "Formuliere eine saubere, kurze Zusammenfassung."
                    )
                },
            ],
            temperature=0.1,
        )
        return res.choices[0].message.content.strip()

    except Exception as e:
        return f"{project}: Zusammenfassung konnte nicht erstellt werden ({e})."


# -------------------------------------------------------------------
# Hilfsfunktionen: Datensäuberung
# -------------------------------------------------------------------
def _clean_title(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\n", " ").replace("\t", " ").strip()
    while "  " in s:
        s = s.replace("  ", " ")
    return s


def _extract_project_name(result: Dict[str, Any]) -> str:
    pages = result.get("page_data") or []
    if not pages:
        return "Unbenanntes Projekt"

    first = pages[0]
    la = first.get("llm_analysis") or {}

    if la.get("project_title"):
        return _clean_title(la["project_title"])

    if first.get("title"):
        return _clean_title(first["title"])

    return urlparse(first.get("url") or "").netloc or "Unbenanntes Projekt"


# -------------------------------------------------------------------
# LLM-Aggregierung
# -------------------------------------------------------------------
def _aggregate_llm_analysis(result: Dict[str, Any]) -> Dict[str, Any]:
    infos = [
        p["llm_analysis"]
        for p in (result.get("page_data") or [])
        if p.get("llm_analysis")
    ]
    if not infos:
        return {}
    return merge_results(infos)


# -------------------------------------------------------------------
# Hilfsfunktion für konsistente Darstellung
# -------------------------------------------------------------------
def _pretty_join(value: Any) -> str:
    if not value:
        return "–"

    def clean(x: Any) -> str:
        return _clean_title(x) if isinstance(x, str) else str(x)

    if isinstance(value, list):
        joined = " // ".join(clean(v) for v in value if v)
        return f"{joined} (LLM)" if joined else "–"

    return f"{clean(value)} (LLM)"


# -------------------------------------------------------------------
# ViewModel für das UI
# -------------------------------------------------------------------
def build_view_model(result: Dict[str, Any], scoring: Dict[str, Any], sw: Dict[str, List[str]]) -> Dict[str, Any]:
    g = scoring.get("global", {}) or {}
    labels = INDICATOR_LABELS

    rows = []
    for section, keys in FIELDS_UI.items():

        # FAIR-Bereich ohne FUJI
        if section == "FAIR (separat)":
            keys = ["fair_overall"]

        items = []
        for key in keys:
            info = g.get(key) or {}
            items.append(
                {
                    "key": key,
                    "label": labels.get(key, key),
                    "bewertung": info.get("bewertung") or "–",
                    "hinweise": info.get("hinweise"),
                    "score": info.get("score"),
                }
            )

        rows.append({"section": section, "items": items})

    fair = scoring.get("global", {}).get("fair_overall", {}) or {}
    llm_analysis = _aggregate_llm_analysis(result)
    hosting = _extract_hosting_data(result)

    return {
        "project_name": _extract_project_name(result),
        "valid_pages": result.get("valid_count") or len(result.get("page_data") or []),
        "hosting_country": hosting["country"],
        "hosting_org": hosting["org"],
        "rows": rows,
        "fair": fair,
        "strengths": sw["strengths"],
        "weaknesses": sw["weaknesses"],
        "conclusion": "",
        "total": scoring.get("total", {}),
        "labels": labels,
        "llm_analysis_aggregated": llm_analysis,
    }


# -------------------------------------------------------------------
# Hosting-Informationen extrahieren
# -------------------------------------------------------------------
def _extract_hosting_data(result: Dict[str, Any]) -> Dict[str, str]:
    sh = result.get("shodan_overview") or result.get("shodan_info") or {}
    return {
        "country": sh.get("country_name") or sh.get("country") or "–",
        "org": sh.get("org") or "–",
    }
