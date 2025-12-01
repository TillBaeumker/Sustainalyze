# file: app/modules/manager/handle_analysis.py
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
handle_analysis.py
==================

Zentrales Management-Modul der Analysepipeline
----------------------------------------------

Dieses Modul koordiniert den vollständigen Analyseablauf für eine eingegebene URL.
Es verbindet Crawling, Einzelanalysen und Ergebnisaggregation zu einem strukturierten
Gesamtbericht, der im Frontend angezeigt werden kann.

Ablaufübersicht
---------------

1. Deep Crawl
   - Aufruf von `deep_crawl_summary`
   - Ermittelt analysierbare HTML-Seiten innerhalb der Domain
   - Übergibt pro Seite HTML, interne und externe Links

2. Linkanreicherung und Statusprüfung
   - Kennzeichnung persistenter Identifier in Links
   - HTTP-Status-Prüfung aller Links (intern/extern)
   - Ableitung einfacher Download-Hinweise (z. B. .xml, .zip, .csv)

3. FUJI-Datensatzerkennung (optional, fair_mode="fuji")
   - Erkennung externer Datensatz-Links (z. B. DOI-/Repo-Links)
   - Vorbereitung für FUJI-Auswertung

4. XML-/TEI-Kandidaten
   - Ermittlung von XML-/TEI-/METS-/MODS-Kandidaten-URLs
   - Übergabe an das XML-Analysemodul

5. Metadaten- und Schnittstellenanalyse
   - FAIR F2A/F2B (strukturierte Metadaten, Vokabulare) via FAIR-Checker-API
   - Normdaten (GND, VIAF, Wikidata etc.) über `collect_normdata`
   - API-Erkennung (OAI-PMH, IIIF, REST) über Linkklassifikation und Host-Probing

6. FAIR-Checker & FUJI (optional)
   - Detaillierte FAIR-Auswertung via FAIR-Checker (JSON-LD-Gesamteindruck)
   - FUJI-Evaluierung von Datensatz-Links (fair_mode="fuji")

7. XML-/TEI-Analyse
   - Download von XML- oder ZIP-Dateien
   - Struktur- und TEI-Erkennung
   - Pro Seite: Liste relevanter TEI-Dateien

8. Repository-Analyse (GitHub/GitLab)
   - Analyse externer Links auf GitHub/GitLab-Repositories
   - Erhebung von Lizenz, README, CONTRIBUTING, Mitwirkenden, Aktivität

9. Infrastruktur (Shodan + Wappalyzer)
   - Shodan: Host- und Dienstinformationen zum Ziel
   - Wappalyzer: Technologien, Frameworks, ggf. Open-Source-Hinweise

10. Aggregation und Berichtserzeugung
    - Übergabe aller Teilresultate an `aggregate_for_scoring`
    - Erstellung eines HTML-Reports über `build_report`
    - Rückgabe eines Gesamt-Dictionaries für das Frontend

Öffentliche Hauptfunktion
-------------------------
- handle_analysis(request, url, log_func=print, max_pages=3, fair_mode="start_only")

Diese Funktion wird vom FastAPI-Endpunkt aufgerufen und liefert die komplette
Analyse inkl. Scoring, Seitenabschnitten und generiertem Report.
"""

from typing import Dict, Any, List
from urllib.parse import urlparse
import asyncio
import aiohttp
import os
from fastapi import Request

# Crawling
from app.modules.manager.crawler import deep_crawl_summary

# Aggregation / Report
from app.modules.manager.aggregator import aggregate_for_scoring
from app.modules.results.report_builder import build_report

# Einzelanalysen
from app.modules.analysis.link_checker import check_links_bounded
from app.modules.analysis.download_detector import detect_downloadables
from app.modules.analysis.detect_persistent_links import detect_persistent_id
from app.modules.analysis.structured_metadata import check_f2a_f2b_for_url
from app.modules.analysis.normdata import collect_normdata
from app.modules.analysis.api_detector import classify_links_min, probe_host_min
from app.modules.analysis.xml_handler import detect_xml_candidates, download_and_analyze_xml
from app.modules.analysis.repo_analyzer import analyze_repos
from app.modules.analysis.shodan_client import get_shodan_info, get_shodan_overview
from app.modules.analysis.wappalyzer import analyze_technologies_with_wappalyzer, parse_wappalyzer_result

# FAIR + FUJI
from app.modules.analysis.fair_checker_client import run_fair_checker_once
from app.modules.analysis.fuji_client import run_fuji_for_dataset, find_fuji_dataset_links


# -------------------------------------------------------------------
# Hilfsfunktionen
# -------------------------------------------------------------------

def _dedupe_keep_order(seq):
    """
    Entfernt Duplikate aus einer Sequenz, behält aber die ursprüngliche Reihenfolge bei.

    Beispiel:
        [a, b, a, c] → [a, b, c]
    """
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# -------------------------------------------------------------------
# Hauptfunktion: handle_analysis
# -------------------------------------------------------------------

async def handle_analysis(
    request: Request,
    url: str,
    log_func=print,
    max_pages: int = 3,
    fair_mode: str = "start_only",
) -> Dict[str, Any]:
    """
    Zentrale Steuerungsfunktion der Analysepipeline.

    Parameter
    ---------
    request : fastapi.Request
        Aktueller FastAPI-Request (wird aktuell nur für spätere Erweiterungen benötigt).
    url : str
        Start-URL der zu analysierenden digitalen Edition / Website.
    log_func : callable
        Logging-Funktion, standardmäßig `print`. Kann im Web-Frontend durch
        eine eigene Logger-Funktion ersetzt werden.
    max_pages : int
        Maximale Anzahl intern gecrawlter Seiten (1–5 sinnvoll).
    fair_mode : str
        Steuerung der FAIR-/FUJI-Integration:
        - "start_only": FAIR-Checker wird auf den analysierten Seiten ausgeführt,
          FUJI bleibt deaktiviert.
        - "fuji": zusätzlich FUJI-Datensatzanalyse auf erkannten Datensatz-Links.

    Rückgabe
    --------
    dict
        Struktur mit:
        - aggregierten Scoring-Ergebnissen
        - seitenbezogenen Analyseergebnissen (`page_sections`)
        - generiertem HTML-Report (`report`)
        - Kontextinformationen (url, max_pages, fair_mode, warnings)
    """

    # Kontext-Metadaten, die am Ende mit zurückgegeben werden
    context = {
        "url": url,
        "max_pages": max_pages,
        "fair_mode": fair_mode,
        "warnings": [],
    }

    try:
        # ==============================================================
        # 1) CRAWLING – Einstieg in die Pipeline
        # ==============================================================
        log_func("🌐 Starte Deep Crawl…")
        crawl_sem = asyncio.Semaphore(2)  # nur 2 gleichzeitige Crawls erlaubt
        async with crawl_sem:
            crawl_result = await deep_crawl_summary(url, max_pages=max_pages)
        page_data: List[Dict[str, Any]] = crawl_result.get("page_data", [])
        log_func(f"🔍 {len(page_data)} Seiten gecrawlt.")

        # Falls keine Seiten analysiert werden konnten, früh zurückkehren
        if not page_data:
            context["warnings"].append("Keine Seiten konnten gecrawlt werden.")
            aggregated = aggregate_for_scoring([], {}, {}, [])
            return {
                **aggregated,
                "page_sections": [],
                "report": build_report(aggregated),
                **context,
            }

        # Sicherstellen, dass für jede Seite HTML-Felder gesetzt sind
        for p in page_data:
            html = p.get("html") or p.get("raw_html") or ""
            p["html"] = html
            p["raw_html"] = html

        # ==============================================================
        # 2) LINKANREICHERUNG + STATUSCODES
        # ==============================================================
        log_func("🔗 Prüfe Links & Statuscodes…")

        # Pro Seite: interne/externe Links in Dict-Struktur überführen
        # inkl. Markierung von Persistent-IDs (DOI, Handle, URN etc.).
        for p in page_data:
            p["internal_links"] = [
                {
                    "url": u,
                    "persistent_type": (detect_persistent_id(u) or {}).get("type"),
                }
                for u in (p.get("internal_links") or [])
            ]

            p["external_links"] = [
                {
                    "url": u,
                    "persistent_type": (detect_persistent_id(u) or {}).get("type"),
                }
                for u in (p.get("external_links") or [])
            ]

        # Alle Links (intern + extern) über alle Seiten hinweg einsammeln
        all_links = _dedupe_keep_order(
            [l["url"] for p in page_data for l in (p["internal_links"] + p["external_links"])]
        )

        # HTTP-Status aller Links prüfen (bounded concurrency)
        try:
            results = await check_links_bounded(all_links, max_concurrent=12)
            status_map = {r["url"]: r.get("status") for r in results}
        except Exception as e:
            context["warnings"].append(f"Linkstatus konnte nicht geprüft werden: {e}")
            status_map = {}

        # Statuscodes wieder pro Seite einsortieren
        for p in page_data:
            p["internal_links_all"] = [
                {**l, "status": status_map.get(l["url"])}
                for l in p["internal_links"]
            ]
            p["external_links_all"] = [
                {**l, "status": status_map.get(l["url"])}
                for l in p["external_links"]
            ]

            # Download-Hinweise (z. B. XML/ZIP/CSV) pro Seite ableiten
            p["downloads"] = detect_downloadables(
                p["internal_links_all"] + p["external_links_all"]
            )

        # ==============================================================
        # 3) FUJI-DATASET-LINKERKENNUNG & XML-KANDIDATEN
        # ==============================================================
        log_func("🧬 Analysiere FUJI-Datasets (falls aktiviert) und XML-Kandidaten…")

        base_domain = urlparse(url).netloc

        for p in page_data:
            all_links_page = [l["url"] for l in (p["internal_links_all"] + p["external_links_all"])]

            # FUJI-Dataset-Erkennung nur, wenn fair_mode = "fuji"
            if fair_mode == "fuji":
                ds = find_fuji_dataset_links(all_links_page, base_domain)
                p["dataset_links"] = [{"url": u} for u in ds.get("dataset_links", [])]
            else:
                p["dataset_links"] = []

            # XML-Kandidaten für weitere Analyse
            p["xml_candidates"] = list({u for u in p["xml_candidates"]})


        # ==============================================================
        # 4) METADATEN (F2A/F2B), NORMDATEN, APIs
        # ==============================================================
        log_func("🧠 Meta, Normdaten, APIs analysieren…")

        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:

            async def analyze_meta_norm_api(p: Dict[str, Any]) -> None:
                """
                Führt für eine Seite:
                - FAIR F2A/F2B via FAIR-Checker
                - Normdaten-Erkennung
                - API-Erkennung (OAI/IIIF/REST)
                durch und speichert die Ergebnisse in `p`.
                """

                # -------------------------
                # FAIR F2A/F2B (Structured Metadata)
                # -------------------------
                try:
                    fair_raw = await check_f2a_f2b_for_url(session, p["url"])
                    p["fair"] = fair_raw
                    summary = fair_raw.get("summary") or {}
                    scores = summary.get("scores") or {}

                    sm = {
                        "has_structured_metadata": summary.get("has_structured_metadata"),
                        "controlled_vocabularies": summary.get("rdf_vocabularies") or [],
                        "rdf_triples": summary.get("rdf_count"),
                        "score": scores.get("F2A"),
                        "score_overall": None,
                    }

                    f2a = scores.get("F2A")
                    f2b = scores.get("F2B")
                    numeric_scores = [
                        float(x) for x in (f2a, f2b) if isinstance(x, (int, float))
                    ]
                    if numeric_scores:
                        sm["score_overall"] = sum(numeric_scores) / len(numeric_scores)

                    p["structured_metadata"] = sm
                except Exception:
                    # Bei Fehlern: leere Strukturen, um spätere Verarbeitung zu erleichtern
                    p["fair"] = {}
                    p["structured_metadata"] = {}

                # -------------------------
                # Normdaten (GND, VIAF, Wikidata, ORCID, …)
                # -------------------------
                try:
                    p["normdata"] = await collect_normdata(
                        base_url=p["url"],
                        html=p.get("raw_html") or p.get("html"),
                        links_internal=[l["url"] for l in p["internal_links_all"]],
                        links_external=[l["url"] for l in p["external_links_all"]],
                        prefer_jsonld=True,
                        session=session,
                    )
                except Exception:
                    p["normdata"] = {}

                # -------------------------
                # API-Schnittstellen (OAI-PMH, IIIF, REST)
                # -------------------------
                try:
                    links_flat = p["internal_links_all"] + p["external_links_all"]
                    link_list = [{"url": l["url"], "status": l.get("status")} for l in links_flat]

                    # Klassifikation konkreter Links
                    _, classified = await classify_links_min(link_list)
                    # Hostweites Probing auf Standardpfade
                    probed = await probe_host_min(p["url"])

                    # Deduplizieren über (type, url)
                    dedup = {(x.get("type"), x.get("url")): x for x in (*classified, *probed)}
                    p["api_interfaces"] = list(dedup.values())
                except Exception:
                    p["api_interfaces"] = []

            # Parallelisierte Ausführung pro Seite
            await asyncio.gather(*(analyze_meta_norm_api(p) for p in page_data))

        # ==============================================================
        # 5) FAIR-CHECKER (JSON-LD) & FUJI (optional, dedupliziert)
        # ==============================================================
        log_func("🟦 FAIR-Checker & FUJI…")

        fuji_semaphore = asyncio.Semaphore(2)

        # --------------------------------------------------------------
        # FAIR-Checker JSON-LD für alle Seiten
        # --------------------------------------------------------------
        for p in page_data:
            try:
                p["fair_checker"] = await run_fair_checker_once(p["url"])
            except Exception as e:
                p["fair_checker"] = {"ok": False, "error": str(e)}

            p["fuji"] = False
            p["fuji_datasets"] = []

        # --------------------------------------------------------------
        # FUJI: globale Deduplizierung aller gefundenen Datensätze
        # --------------------------------------------------------------
        if fair_mode == "fuji":

            # 1) Alle Dataset-Links sammeln
            all_ds_links = []
            page_origin = {}

            for p in page_data:
                for ds in p.get("dataset_links", []):
                    url_ds = ds["url"]
                    all_ds_links.append(url_ds)

                    if url_ds not in page_origin:
                        page_origin[url_ds] = p["url"]

            # 2) Deduplizieren
            unique_ds_links = _dedupe_keep_order(all_ds_links)

            log_func(f"🔎 FUJI: {len(all_ds_links)} Links gefunden, {len(unique_ds_links)} eindeutig.")

            # 3) FUJI einmal ausführen
            fuji_results = {}
            for url_ds in unique_ds_links:
                try:
                    fuji_results[url_ds] = await run_fuji_for_dataset(url_ds, fuji_semaphore)
                except Exception as e:
                    fuji_results[url_ds] = {"ok": False, "error": str(e)}

            # 4) Ergebnisse auf Seiten verteilen
            for p in page_data:
                fuji_list = []
                for ds in p.get("dataset_links", []):
                    url_ds = ds["url"]
                    ds["fuji"] = fuji_results.get(url_ds)
                    fuji_list.append(ds["fuji"])
                p["fuji"] = bool(fuji_list)
                p["fuji_datasets"] = fuji_list

            # 5) Globale Liste fürs Frontend
            aggregated_fuji_list = []
            for url_ds in unique_ds_links:
                fr = fuji_results[url_ds] or {}
                summary = fr.get("summary") or {}

                aggregated_fuji_list.append({
                    "url": url_ds,
                    "page_url": page_origin.get(url_ds),
                    "summary": summary,
                    "raw": fr
                })

            # Diese globale Liste ins context packen
            context["fuji_all"] = aggregated_fuji_list
        else:
            context["fuji_all"] = []

        # ==============================================================
        # 6) XML-/TEI-ANALYSE
        # ==============================================================
        log_func("📄 Untersuche XML/TEI-Dateien…")

        # Optionaler Zielordner für Downloads (kann später erweitert werden)
        os.makedirs("tei_downloads", exist_ok=True)

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:

            async def analyze_xml(p: Dict[str, Any]) -> None:
                """
                Lädt für jede XML-Kandidaten-URL die Ressource herunter,
                analysiert sie und speichert TEI-relevante Ergebnisse in `p["xml_scan"]`.
                """
                collected = []
                for cand in p["xml_candidates"]:
                    try:
                        info = await download_and_analyze_xml(
                            session=session,
                            url=cand,
                        )
                        collected.extend(info.get("entries", []))
                    except Exception:
                        # Einzelne Fehler blockieren die restliche Analyse nicht
                        pass

                # Nur Einträge behalten, die explizit als TEI erkannt wurden
                p["xml_scan"] = [
                    entry for entry in collected
                    if entry.get("is_tei") is True
                ]

            await asyncio.gather(*(analyze_xml(p) for p in page_data))

        # ==============================================================
        # 7) GITHUB / GITLAB-REPOSITORIES
        # ==============================================================
        log_func("📁 Analysiere Repositories…")

        repo_sem = asyncio.Semaphore(4)

        async def analyze_repo_page(p: Dict[str, Any]) -> None:
            """
            Sammelt externe Links einer Seite, filtert GitHub/GitLab-Links
            und führt pro Seite die Repositoryanalyse aus.
            """
            extern = {l["url"] for l in p["external_links_all"]}

            async with repo_sem:
                info = await analyze_repos(extern)
                p["github_repos"] = info.get("github_repos", [])
                p["gitlab_repos"] = info.get("gitlab_repos", [])

        await asyncio.gather(*(analyze_repo_page(p) for p in page_data))

        # ==============================================================
        # 8) INFRASTRUKTUR (Shodan + Wappalyzer)
        # ==============================================================
        log_func("🏗️ Infrastruktur-Analyse…")

        # Für Shodan/Wappalyzer wird die exakte Eingabe-URL verwendet
        exact_url = url
        loop = asyncio.get_running_loop()

        try:
            shodan_info = await loop.run_in_executor(
                None, lambda: get_shodan_info(exact_url)
            )
            shodan_overview = await loop.run_in_executor(
                None, lambda: get_shodan_overview(shodan_info)
            )
        except Exception:
            shodan_info, shodan_overview = {}, {}

        try:
            w_raw = await loop.run_in_executor(
                None, lambda: analyze_technologies_with_wappalyzer(exact_url)
            )
            wappalyzer = parse_wappalyzer_result(w_raw)
        except Exception:
            wappalyzer = []

        # ==============================================================
        # 9) AGGREGATION & REPORT
        # ==============================================================
        log_func("📊 Aggregiere Gesamtergebnis…")

        # FAIR-Checker-Ergebnis der Startseite explizit hervorheben
        home_fair_checker = page_data[0].get("fair_checker")

        aggregated = aggregate_for_scoring(
            pages=page_data,
            shodan_info=shodan_info,
            shodan_overview=shodan_overview,
            wappalyzer=wappalyzer,
        )

        aggregated["fair_checker"] = home_fair_checker


        log_func("📝 Generiere Report…")
        report = build_report(aggregated)

        # ==============================================================
        # 10) FINAL – Rückgabe an das Frontend
        # ==============================================================
        return {
            **aggregated,
            "page_sections": aggregated.get("page_data", []),
            "report": report,
            **context,
        }

    except Exception as ex:
        # Zentrale Fehlerbehandlung – sorgt dafür, dass Exceptions sichtbar bleiben
        log_func("❌ Analyse ist abgestürzt!")
        import traceback
        traceback.print_exc()
        raise ex
