"""
aggregator.py
==================================================================

Dieses Modul fasst die Ergebnisse aller Einzelanalysen zu einem
konsistenten Datenobjekt zusammen. Es bildet damit die zentrale
Schnittstelle zwischen der technischen Analysepipeline und der
Darstellung im Frontend.

Aufgaben des Moduls
-------------------
- Vereinheitlichung der Seitenergebnisse (Links, APIs, XML, Repos)
- Berechnung grundlegender Kennzahlen (Statistiken für das Frontend)
- Zusammenführung strukturierter Metadaten und Normdaten
- Nicht-bewertende Weitergabe externer Systemanalysen (Shodan, Wappalyzer)
- Bereitstellung aggregierter Nutzlast für LLM-basierte Auswertungen

Das Modul verändert keine Einzelergebnisse, sondern aggregiert,
ordnet und bereitet sie auf. Es enthält keine Interpretations- oder
Bewertungslogik; diese liegt ausschließlich in den Analysemodulen
bzw. im späteren LLM-Schritt.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


# =====================================================================
# Hauptfunktion – Einstiegspunkt für die Gesamtaggregation
# =====================================================================

def aggregate_for_scoring(
    pages: List[Dict[str, Any]],
    shodan_info: Optional[Dict[str, Any]] = None,
    shodan_overview: Optional[Dict[str, Any]] = None,
    wappalyzer: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Sammelt und strukturiert alle Analyseergebnisse.

    Parameter
    ---------
    pages :
        Liste aller analysierten Seiten. Jede Seite enthält Rohdaten
        aus dem Crawler sowie Ergebnisse der Einzelmodule.
    shodan_info, shodan_overview :
        Ergebnisse der Infrastruktur-Analyse (Hostscan).
    wappalyzer :
        Technologie-Signaturen der Startseite.

    Rückgabe
    --------
    dict :
        Vollständiges Aggregat mit Seiteninformationen, Statistiken
        und externen Systemdaten. Grundlage für das Frontend und
        die LLM-basierte Bewertung.
    """

    print("[Aggregator] Starte zentrale Aggregation …")

    # Leeres Ergebnis, falls keine Seiten analysiert wurden
    if not pages:
        print("[Aggregator] Keine Seiten vorhanden – leeres Ergebnis.")
        return _empty_result(shodan_info, shodan_overview, wappalyzer)

    # ------------------------------------------------------------------
    # Interne Links: Statusauswertung (bewertet)
    # ------------------------------------------------------------------
    print("[Aggregator] Aggregiere interne Links …")
    link_data = _aggregate_links_internal_only(pages)
    internal_links = link_data["all"]
    broken_internal = link_data["broken"]
    ok_internal = link_data["ok"]
    bad_internal = link_data["bad"]

    total_internal = len(internal_links)
    ok_rate = (ok_internal / total_internal * 100) if total_internal else None

    # ------------------------------------------------------------------
    # Externe Links: rein informativ (keine Bewertung)
    # ------------------------------------------------------------------
    print("[Aggregator] Sammle externe Links (unbewertet) …")
    external_links = _collect_external_links(pages)

    # ------------------------------------------------------------------
    # Downloads des Projekts (z. B. XML, ZIP, CSV)
    # ------------------------------------------------------------------
    print("[Aggregator] Sammle Downloads …")
    download_items = _collect_downloads(pages)

    # ------------------------------------------------------------------
    # XML- und TEI-Ergebnisse
    # ------------------------------------------------------------------
    print("[Aggregator] Aggregiere XML/TEI-Ergebnisse …")
    xml_entries, tei_hits = _aggregate_xml(pages)

    # ------------------------------------------------------------------
    # API-Schnittstellen (OAI-PMH, IIIF, REST…)
    # ------------------------------------------------------------------
    print("[Aggregator] Aggregiere API-Schnittstellen …")
    api_interfaces, api_types = _aggregate_api(pages)

    # ------------------------------------------------------------------
    # Repositories (GitHub / GitLab getrennt)
    # ------------------------------------------------------------------
    print("[Aggregator] Aggregiere Repositories …")
    github_repos, gitlab_repos = _aggregate_repos_distinct(pages)

    # ------------------------------------------------------------------
    # Strukturierte Metadaten (FAIR F2A/F2B)
    # ------------------------------------------------------------------
    print("[Aggregator] Aggregiere strukturierte Metadaten …")
    sm_avg = _aggregate_structured_metadata_scores(pages)

    # ------------------------------------------------------------------
    # Normdaten (GND, VIAF, Wikidata…)
    # ------------------------------------------------------------------
    print("[Aggregator] Sammle Normdaten …")
    norm_items, norm_sources = _collect_normdata(pages)

    # ------------------------------------------------------------------
    # LLM-Analyse (frei strukturierte Auswertung)
    # ------------------------------------------------------------------
    print("[Aggregator] Aggregiere LLM-Auswertungen …")
    llm_payloads = [
        p["llm_analysis"] for p in pages
        if isinstance(p.get("llm_analysis"), dict)
    ]
    llm_aggregated = _merge_llm(llm_payloads)

    # ------------------------------------------------------------------
    # FAIR-Checker-Ergebnisse (JSON-LD pro Seite)
    # ------------------------------------------------------------------
    print("[Aggregator] Sammle FAIR-Checker-Daten …")
    fair_checker_all = [
        {"url": p.get("url"), "result": p.get("fair_checker")}
        for p in pages
        if p.get("fair_checker") not in (None, {}, [])
    ]


    # ------------------------------------------------------------------
    # Statistiken für das Frontend
    # ------------------------------------------------------------------
    print("[Aggregator] Berechne Statistiken …")
    stats = {
        "total_pages": len(pages),
        "internal_links_total": total_internal,
        "internal_links_ok": ok_internal,
        "internal_links_bad": bad_internal,
        "internal_ok_rate_percent": ok_rate,
        "external_links_total": len(external_links),
        "xml_entries_count": len(xml_entries),
        "tei_files_count": tei_hits,
        "api_interfaces_count": len(api_interfaces),
        "api_types": sorted(api_types),
        "github_repos_count": len(github_repos),
        "gitlab_repos_count": len(gitlab_repos),
        "structured_metadata_score_average": sm_avg,
        "normdata_items_count": len(norm_items),
        "normdata_sources": norm_sources,
        "download_items_count": len(download_items),
        "fair_checker_count": len(fair_checker_all),

    }

    print("[Aggregator] Aggregation abgeschlossen.")

    # ------------------------------------------------------------------
    # Zusammenstellung des finalen Aggregats
    # ------------------------------------------------------------------
    return {
        "page_data": pages,

        # Linkdaten
        "internal_link_checks": internal_links,
        "broken_internal_links": broken_internal,
        "external_links": external_links,

        # Repositories
        "github_repos": github_repos,
        "gitlab_repos": gitlab_repos,

        # XML/TEI
        "xml_scan_results": xml_entries,

        # Strukturierte Metadaten
        "strukturierte_metadaten": {
            "score": sm_avg,
            "pages": [p.get("structured_metadata", {}) for p in pages],
        },

        # Normdaten
        "normdaten": {
            "items": norm_items,
            "sources": norm_sources,
            "count": len(norm_items),
        },

        # FAIR
        "fair_checker_results": fair_checker_all,


        # Infrastruktur
        "shodan_info": shodan_info or {},
        "shodan_overview": shodan_overview or {},
        "wappalyzer": wappalyzer or [],

        # Statistiken und LLM-Ergebnis
        "stats": stats,
        "llm_aggregated": llm_aggregated,
    }


# =====================================================================
# Hilfsfunktionen für Aggregation
# =====================================================================

def _empty_result(shodan_info, shodan_overview, wappalyzer):
    """Gibt eine vollständig leere Aggregationsstruktur zurück."""
    return {
        "page_data": [],
        "internal_link_checks": [],
        "broken_internal_links": [],
        "external_links": [],
        "github_repos": [],
        "gitlab_repos": [],
        "xml_scan_results": [],
        "strukturierte_metadaten": {"score": None, "pages": []},
        "normdaten": {"items": [], "sources": [], "count": 0},
        "fair_checker_results": [],
        "shodan_info": shodan_info or {},
        "shodan_overview": shodan_overview or {},
        "wappalyzer": wappalyzer or [],
        "stats": {},
        "llm_aggregated": {},
    }


# =====================================================================
# Link-Aggregation (interne Links mit Statusbewertung)
# =====================================================================

def _aggregate_links_internal_only(pages):
    """Extrahiert interne Links aller Seiten und klassifiziert Statuscodes."""
    all_links = []
    broken = []
    ok = bad = 0

    for p in pages:
        for l in p.get("internal_links_all") or []:
            if not isinstance(l, dict):
                continue

            url = l.get("url")
            status = l.get("status")

            all_links.append({"url": url, "status": status})

            # Fehlerhafte oder unklare Statuscodes gelten grundsätzlich als "bad".
            if status is None or (isinstance(status, str) and status.startswith("ERROR")):
                bad += 1
                broken.append({"url": url, "status": status})
                continue

            # Bewertung regulärer HTTP-Codes
            try:
                code = int(status)
                if 200 <= code < 400:
                    ok += 1
                else:
                    bad += 1
                    broken.append({"url": url, "status": code})
            except:
                bad += 1
                broken.append({"url": url, "status": status})

    return {"all": all_links, "broken": broken, "ok": ok, "bad": bad}


def _collect_external_links(pages):
    """Sammelt alle externen Links; hierbei erfolgt keine Bewertung."""
    out = []
    for p in pages:
        for l in p.get("external_links_all") or []:
            if isinstance(l, dict):
                out.append({"url": l.get("url"), "status": l.get("status")})
    return out


# =====================================================================
# Downloads
# =====================================================================

def _collect_downloads(pages):
    """Sammelt alle erkennbaren Download-Elemente der Seiten."""
    out = []
    for p in pages:
        dl = p.get("downloads")
        if isinstance(dl, dict) and "items" in dl:
            out.extend(dl["items"])
        elif isinstance(dl, list):
            out.extend(dl)
    return out


# =====================================================================
# XML / TEI
# =====================================================================

def _aggregate_xml(pages):
    """
    Zusammenführung aller XML-Ergebnisse.
    Falls keine Analyse vorliegt, wird anhand der URL ein einfacher
    TEI-Hinweis (Heuristik) erzeugt.
    """
    xml_entries = []
    tei_hits = 0

    for p in pages:
        scan = p.get("xml_scan") or []
        if scan:
            for entry in scan:
                xml_entries.append(entry)
                if entry.get("is_tei"):
                    tei_hits += 1
        else:
            # Fallback: heuristische XML/TEI-Erkennung
            for url in p.get("xml_candidates") or []:
                entry = {"url": url, "is_tei": ("tei" in url.lower())}
                xml_entries.append(entry)
                if entry["is_tei"]:
                    tei_hits += 1
    return xml_entries, tei_hits


# =====================================================================
# API-Schnittstellen
# =====================================================================

def _aggregate_api(pages):
    """Fasst alle erkannten API-Schnittstellen zusammen."""
    items = []
    types = set()
    for p in pages:
        for api in p.get("api_interfaces") or []:
            if isinstance(api, dict):
                items.append(api)
                if api.get("type"):
                    types.add(api["type"])
    return items, types


# =====================================================================
# Repository-Analyse
# =====================================================================

def _aggregate_repos_distinct(pages):
    """Sammelt GitHub- und GitLab-Links ohne Duplikate."""
    github = []
    gitlab = []

    seen_github = set()
    seen_gitlab = set()

    for p in pages:
        # GitHub
        for r in p.get("github_repos") or []:
            if isinstance(r, dict):
                url = r.get("html_url") or r.get("url")
                if url and url not in seen_github:
                    seen_github.add(url)
                    github.append(r)

        # GitLab
        for r in p.get("gitlab_repos") or []:
            if isinstance(r, dict):
                url = r.get("web_url") or r.get("url")
                if url and url not in seen_gitlab:
                    seen_gitlab.add(url)
                    gitlab.append(r)

    return github, gitlab


# =====================================================================
# Strukturierte Metadaten (F2A/F2B scores)
# =====================================================================

def _aggregate_structured_metadata_scores(pages):
    """Berechnet den Durchschnittswert strukturierter Metadaten."""
    vals = []
    for p in pages:
        sm = p.get("structured_metadata") or {}
        score = sm.get("score") or sm.get("score_overall")
        if isinstance(score, (int, float, str)):
            try:
                vals.append(float(score))
            except:
                pass
    return sum(vals) / len(vals) if vals else None


# =====================================================================
# Normdaten
# =====================================================================

def _collect_normdata(pages):
    """Aggregiert Normdaten (GND, VIAF etc.) und kontrollierte Vokabulare."""
    norm_items = []
    sources = set()

    for p in pages:
        nd = p.get("normdata") or {}
        items = nd.get("items") or []

        # Normdaten-Einträge
        for it in items:
            if isinstance(it, dict):
                src = it.get("source")
                if isinstance(src, str) and src.strip():
                    norm_items.append(it)
                    sources.add(src.strip())

        # Vokabulare aus strukturierten Metadaten
        sm = p.get("structured_metadata") or {}
        cv = sm.get("controlled_vocabularies") or []

        for x in cv:
            if isinstance(x, str):
                if x.strip():
                    sources.add(x.strip())
            elif isinstance(x, dict):
                s = x.get("source") or x.get("type")
                if isinstance(s, str) and s.strip():
                    sources.add(s.strip())

    return norm_items, sorted(sources)


# =====================================================================
# LLM-Auswertung
# =====================================================================

def _merge_llm(payloads: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Führt LLM-Auswertungen ohne Duplikate zusammen."""
    out: Dict[str, List[str]] = {}

    for p in payloads:
        for key, value in p.items():

            # Werte in Listenform überführen
            if isinstance(value, str):
                vals = [value]
            elif isinstance(value, list):
                vals = value
            else:
                continue

            if key not in out:
                out[key] = []

            existing = {x.lower() for x in out[key]}

            # Duplikatfreie Zusammenführung
            for v in vals:
                s = str(v).strip()
                if s and s.lower() not in existing:
                    out[key].append(s)

    return out
