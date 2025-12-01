from __future__ import annotations

"""
crawler.py
======================================
Webseiten-Crawler (Deep Crawl Light)
--------------------------------------

Dieses Modul bildet den Einstiegspunkt der Analysepipeline. 
Es führt einen Playwright-basierten Deep Crawl (Tiefe = 1) durch
und validiert alle gefundenen Seiten per HTTP-Anfrage.

Hauptaufgaben:
-------------
1. Normalisierung der Start-URL und Ermittlung der Domain
2. Extraktion interner und externer Links über ein Browsermodell (Playwright)
3. Filterung der Links auf wahrscheinliche HTML-Seiten
4. HTTP-Validierung und vollständiges Herunterladen der HTML-Dokumente
5. Übergabe der Seiteninhalte an `extract_page_info`
6. Aggregation der Ergebnisse für die weitere Auswertung

Besonderheiten:
---------------
- Startseite wird immer zuerst verarbeitet
- Nur ein Playwright-Lauf pro Crawl-Vorgang
- Rückgabe erfolgt als strukturierter Datensatz für die spätere Pipeline
- Alle Linksets werden domänenspezifisch eingeschränkt
- Vollständig kompatibel mit `handle_analysis`, Scoring-Modulen und dem Frontend

Hinweis zur Konfiguration:
--------------------------
Die MAX-Pages-Grenzen sowie alle API-Keys stammen aus `app/core/config.py`.
Externe Programme (Playwright, Browser) müssen systemweit verfügbar sein.
"""

from typing import Dict, List, Any
from urllib.parse import urlparse, urldefrag, urlunparse

import aiohttp
from app.modules.analysis.link_extractor import extract_links_http
from app.core.config import settings
from app.modules.manager.page_info_extractor import extract_page_info


# ======================================================================
# Helper-Funktionen
# ======================================================================

def normalize_url(u: str) -> str:
    """
    Entfernt Fragmente, vereinheitlicht Schema und Hostnamen
    und erzeugt eine bereinigte absolute URL.
    """
    if not u:
        return ""
    try:
        p = urlparse(urldefrag(u)[0])
        scheme = (p.scheme or "http").lower()
        netloc = (p.netloc or "").lower()
        path = p.path or "/"
        return urlunparse((scheme, netloc, path, "", p.query, ""))
    except Exception:
        return (u or "").strip()


def is_http_url(url: str) -> bool:
    """Prüft, ob die URL ein http/https-Schema verwendet."""
    try:
        return urlparse(url).scheme in ("http", "https")
    except Exception:
        return False


def domain_of(url: str) -> str:
    """Extrahiert die Domain aus der URL."""
    return urlparse(url).netloc.lower()


def is_probably_html(url: str) -> bool:
    """
    Schließt Ressourcen aus, die nicht auf HTML hinweisen.
    Wird eingesetzt, um Nicht-HTML-Links frühzeitig zu filtern.
    """
    if not is_http_url(url):
        return False

    ext = ""
    path = urlparse(url).path
    if "." in path:
        ext = path.rsplit(".", 1)[-1].lower()

    non_html_ext = {
        "jpg", "jpeg", "png", "gif", "svg", "webp",
        "ico", "css", "js", "pdf", "zip", "json",
        "mp3", "mp4", "wav", "xml", "tei", "woff", "woff2",
    }
    return ext not in non_html_ext


# ======================================================================
# SimplePage – Wrapper für extract_page_info
# ======================================================================

class SimplePage:
    """
    Minimales, typisiertes Objekt zur Kompatibilität mit extract_page_info().
    Enthält HTML-Inhalt, HTTP-Status und Linksets.
    """
    __slots__ = ("url", "html", "status_code", "internal_links", "external_links")

    def __init__(self, url: str, html: str, status_code: int,
                 internal_links: List[str], external_links: List[str]):
        self.url = url
        self.html = html or ""
        self.status_code = status_code
        self.internal_links = internal_links
        self.external_links = external_links


# ======================================================================
# Hauptfunktion: deep_crawl_summary()
# ======================================================================

async def deep_crawl_summary(start_url: str, max_pages: int = 3) -> Dict[str, Any]:
    """
    Führt einen Deep Crawl (Tiefe = 1) durch und sammelt Seiten für die Analyse.
    Die Startseite wird immer zuerst verarbeitet.

    Ablauf:
    -------
    1. Normalisierung der Start-URL
    2. Playwright-basiertes Sammeln aller internen Links
    3. Einschränkung auf HTML-Kandidaten
    4. HTTP-Validierung der Zielseiten
    5. Inhaltliche Analyse über `extract_page_info`
    6. Rückgabe der Seiteninformationen

    Rückgabeformat:
    ---------------
    {
        "start_url_raw": "...",
        "total_pages": <int>,
        "valid_count": <int>,
        "filtered_out_count": <int>,
        "broken_count": <int>,
        "page_data": [...],
        "filtered_out": [...],
        "broken_links": [...],
    }
    """

    max_pages = max(1, min(max_pages, 5))
    seed = normalize_url(start_url)
    domain = domain_of(seed)

    print(f"[Crawler] Start: {seed}")
    print(f"[Crawler] Domain: {domain}")
    print(f"[Crawler] max_pages={max_pages}")

    # =========================================================
    # 1) Playwright-Linkextraktion
    # =========================================================
    print(f"[Crawler] Extrahiere Links: {seed}")

    try:
        internal_raw, external_raw = await extract_links_http(seed)
    except Exception as e:
        print(f"[Crawler][ERROR] LinkExtractor-Fehler: {e}")
        return {
            "start_url_raw": seed,
            "total_pages": 0,
            "valid_count": 0,
            "filtered_out_count": 0,
            "broken_count": 0,
            "page_data": [],
            "filtered_out": [],
            "broken_links": [],
        }

    # Filter auf HTML-Kandidaten
    internal_candidates = [normalize_url(u) for u in internal_raw if is_probably_html(u)]

    # =========================================================
    # 2) Startseite immer zuerst
    # =========================================================
    if seed not in internal_candidates:
        internal_candidates.insert(0, seed)
    else:
        internal_candidates.remove(seed)
        internal_candidates.insert(0, seed)

    # Seitenlimit vorbereiten
    internal_candidates = internal_candidates[: max_pages * 4]

    # =========================================================
    # 3) HTTP-Validierung
    # =========================================================
    print("[Crawler] Prüfe Kandidaten per HTTP…")

    valid_pages = []
    filtered_out = []
    broken_links = []

    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for url in internal_candidates:
            try:
                async with session.get(url, timeout=10) as resp:
                    status = resp.status
                    ctype = resp.headers.get("Content-Type", "")

                    if status < 400 and "text/html" in ctype.lower():
                        html = await resp.text()

                        # Erneute Linkextraktion pro Seite
                        try:
                            internal_l, external_l = await extract_links_http(url)
                        except Exception:
                            internal_l, external_l = set(), set()

                        valid_pages.append({
                            "url": url,
                            "html": html,
                            "status": status,
                            "internal_links": list(internal_l),
                            "external_links": list(external_l),
                        })

                        if len(valid_pages) >= max_pages:
                            break
                    else:
                        filtered_out.append({"url": url, "reason": f"{status}, {ctype}"})
            except Exception as e:
                filtered_out.append({"url": url, "reason": str(e)})

    if not valid_pages:
        return {
            "start_url_raw": seed,
            "total_pages": 0,
            "valid_count": 0,
            "filtered_out_count": len(filtered_out),
            "broken_count": 0,
            "page_data": [],
            "filtered_out": filtered_out,
            "broken_links": broken_links,
        }

    # =========================================================
    # 4) Analysephase (extract_page_info)
    # =========================================================
    print(f"[Crawler] Starte Analysephase ({len(valid_pages)} Seiten)…")

    page_data = []
    async with aiohttp.ClientSession() as session:
        for page in valid_pages:
            sp = SimplePage(
                url=page["url"],
                html=page["html"],
                status_code=page["status"],
                internal_links=page["internal_links"],
                external_links=page["external_links"],
            )

            try:
                info = await extract_page_info(
                    r=sp,
                    api_token=settings.OPENAI_API_KEY,
                    session=session,
                )
            except Exception as e:
                broken_links.append({"url": sp.url, "error": str(e)})
                continue

            if info:
                info["url"] = normalize_url(info.get("url", sp.url))
                page_data.append(info)

    # =========================================================
    # 5) Ergebnisdatensatz aufbauen
    # =========================================================
    return {
        "start_url_raw": seed,
        "total_pages": len(valid_pages),
        "valid_count": len(page_data),
        "filtered_out_count": len(filtered_out),
        "broken_count": len(broken_links),
        "page_data": page_data,
        "filtered_out": filtered_out,
        "broken_links": broken_links,
    }
