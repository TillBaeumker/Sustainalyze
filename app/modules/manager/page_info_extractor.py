"""
page_info_extractor.py
=======================

Funktion
--------
Dieses Modul übernimmt die inhaltliche Analyse einzelner HTML-Seiten,
nachdem der zentrale Crawler die Seite bereits geladen, validiert und
interne/externe Links extrahiert hat.

Ablauf (Kurzüberblick)
----------------------
1. URL-Bereinigung
2. Titelbestimmung aus <title>, OG-Tags oder strukturellen Elementen
3. Übergabe der vom Crawler gelieferten Links
4. LLM-basierte Extraktion strukturierter Informationen (Debug-orientiert)
   - HTML-Cleaning
   - Chunking
   - Strategy.extract(...) pro Chunk
   - JSON-Extraktion aus Strings / Listen / content[]
   - Zusammenführen aller Ergebnisse

Hinweis
-------
Dies ist explizit die Debug-Version:
- vollständige Konsolenausgaben
- keine XML-Analyse
- keine Heuristiken
"""

import logging
import asyncio
import re
from urllib.parse import urlparse, urlunparse, urldefrag
from lxml import html as lhtml

from app.modules.analysis.llm_analysis import (
    get_llm_extraction_strategy,
    extract_json_from_text,
    merge_results,
)

logger = logging.getLogger(__name__)


# ============================================================
# URL-Hilfsfunktionen
# ============================================================

def normalize_url(u: str) -> str:
    """
    Entfernt Fragmentteile (#...) und gibt eine bereinigte HTTP/HTTPS-URL zurück.
    """
    if not u:
        return ""
    u = urldefrag(u)[0]
    try:
        p = urlparse(u)
        return urlunparse((
            (p.scheme or "http").lower(),
            (p.netloc or "").lower(),
            p.path or "/",
            "",
            p.query,
            "",
        ))
    except Exception:
        return u.strip()


def is_http_url(u: str) -> bool:
    """
    Prüft, ob eine URL auf http oder https basiert.
    """
    try:
        return urlparse(u).scheme in ("http", "https")
    except Exception:
        return False


def is_ignorable_link(u: str) -> bool:
    """
    Minimale Filterlogik für nicht-webfähige URLs.
    """
    if not u:
        return True

    low = u.lower()
    return low.startswith(("javascript:", "mailto:", "tel:", "data:"))


# ============================================================
# HTML-Hilfsfunktionen
# ============================================================

def extract_title(html: str, fallback: str) -> str:
    """
    Bestimmt den Seitentitel über <title>, OG:title oder <h1>.
    Falls nicht vorhanden, wird die URL-Komponente verwendet.
    """
    try:
        doc = lhtml.fromstring(html)

        t = (doc.xpath("string(//title)") or "").strip()
        if t:
            return t

        og = doc.xpath("string(//meta[@property='og:title']/@content)") or ""
        if og.strip():
            return og.strip()

        h1 = doc.xpath("string(//h1[1])") or ""
        if h1.strip():
            return h1.strip()

    except Exception:
        pass

    p = urlparse(fallback)
    return (p.path.strip("/") or p.netloc).strip()


# ============================================================
# LLM-Analyse (Debug-Version)
# ============================================================

async def run_llm_analysis(html: str, url: str, api_token: str) -> dict:
    """
    Führt eine LLM-basierte Extraktion durch, bestehend aus:
    - HTML-Bereinigung
    - Chunk-Segmentierung
    - Verarbeitung durch strategy.extract(...)
    - JSON-Extraktion aus Direkt- und verschachtelten Strukturen
    - Zusammenführung mehrerer Ergebnisse

    Alle Schritte liefern detaillierte Konsolenausgaben.
    """
    print("🧠 [DEBUG] Starte LLM-Analyse…")

    if not html:
        print("🧠 [DEBUG] Kein HTML → Analyse übersprungen")
        return {}

    try:
        strategy = get_llm_extraction_strategy(api_token)
        print("🧠 [DEBUG] Strategy erstellt")

        # HTML-Bereinigung ähnlich zur alten Implementierung
        clean_html = re.sub(r"<script.*?</script>", "", html,
                            flags=re.DOTALL | re.IGNORECASE)
        clean_html = re.sub(r"<style.*?</style>", "", clean_html,
                            flags=re.DOTALL | re.IGNORECASE)

        # Chunking
        CHUNK_SIZE = 200_000
        chunks = [
            clean_html[i: i + CHUNK_SIZE]
            for i in range(0, len(clean_html), CHUNK_SIZE)
        ]
        chunks = [c for c in chunks if c.strip() != ""]

        if not chunks:
            print("🧠 [DEBUG] Alle Chunks leer → Abbruch")
            return {}

        # Begrenzung auf ersten und letzten Chunk
        if len(chunks) > 2:
            chunks = [chunks[0], chunks[-1]]

        collected_results = []

        for idx, chunk in enumerate(chunks):
            print(f"🔎 LLM-Block {idx + 1}/{len(chunks)}")

            # strategy.extract ist synchron
            result = strategy.extract(str(idx), url, chunk)

            parsed_obj = None

            # Direkter dict
            if isinstance(result, dict):
                parsed_obj = result

            # Listen durchsuchen
            elif isinstance(result, list):
                for elem in result:

                    # Direktes Dict mit bekannten Keys
                    if isinstance(elem, dict):
                        if any(k in elem for k in [
                            "institution", "roles_responsibilities",
                            "funding_information", "continuation_strategy",
                            "contact_info", "documentation", "license",
                            "tei_hint", "api_hint", "downloads_hint",
                            "repositories_hint", "normdata_hint",
                            "structured_metadata_hint",
                            "persistent_identifier_hint",
                            "staticization_hint",
                            "isolation_hint",
                            "open_source_hint",
                        ]):
                            parsed_obj = elem
                            break

                        # JSON in content[]
                        if "content" in elem and isinstance(elem["content"], list):
                            for candidate in elem["content"]:
                                if isinstance(candidate, str):
                                    extracted = extract_json_from_text(candidate)
                                    if extracted:
                                        parsed_obj = extracted
                                        break
                            if parsed_obj:
                                break

                    # JSON aus String
                    if isinstance(elem, str):
                        extracted = extract_json_from_text(elem)
                        if extracted:
                            parsed_obj = extracted
                            break

            if parsed_obj:
                collected_results.append(parsed_obj)

        merged = merge_results(collected_results)
        return merged

    except Exception as e:
        print(f"⚠️ [LLM] Fehler: {e}")
        return {}


# ============================================================
# Hauptfunktion: extract_page_info
# ============================================================

async def extract_page_info(r, api_token: str, session=None) -> dict:
    """
    Analysiert eine einzelne Seite. Erwartet ein Objekt mit:
    - url
    - html
    - internal_links (durch Crawler geliefert)
    - external_links (durch Crawler geliefert)

    Rückgabeformat ist kompatibel mit dem Aggregator und den Scoring-Modulen.
    """

    print("\n======================================================")
    print("➡️ DEBUG: extract_page_info START")
    print("======================================================")

    # URL
    url = normalize_url(r.url)
    print(f"URL: {url}")

    # HTML
    raw_html = getattr(r, "html", None) or ""
    if asyncio.iscoroutine(raw_html):
        raw_html = await raw_html

    print(f"HTML-Länge: {len(raw_html)}")

    # Titel
    title = extract_title(raw_html, url)
    print(f"Titel: {title}")

    internal = getattr(r, "internal_links", [])
    external = getattr(r, "external_links", [])

    print(f"Interne Links: {len(internal)}")
    print(f"Externe Links: {len(external)}")

    # LLM-Analyse
    llm_data = await run_llm_analysis(raw_html, url, api_token)

    print("======================================================")
    print("➡️ DEBUG: extract_page_info ENDE")
    print("======================================================\n")

    return {
        "url": url,
        "title": title,
        "html": raw_html,
        "internal_links": internal,
        "external_links": external,
        "xml_candidates": [],
        "downloads": [],
        "fair": {},
        "normdata": {},
        "api_interfaces": [],
        "github_repos": [],
        "gitlab_repos": [],
        "llm_analysis": llm_data,
    }
