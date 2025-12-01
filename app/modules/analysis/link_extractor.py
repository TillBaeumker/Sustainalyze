# -*- coding: utf-8 -*-
"""
link_extractor.py (Playwright-only)
===================================

Dieses Modul extrahiert Links mithilfe eines echten Browsers
(Chromium über Playwright). Es ist speziell optimiert für
digitale Editionen, die häufig veraltete SSL-Zertifikate,
exotische Linkstrukturen oder Non-HTML-Assets nutzen.

Eigenschaften:
--------------
- ignoriert ungültige HTTPS-Zertifikate (relevant bei alten Editionen)
- automatischer Fallback von HTTPS → HTTP bei Ladefehlern
- extrahiert Links aus:
    • <a href="...">
    • allen Netzwerk-Requests und -Responses (requests_seen)
- robuste Normalisierung und Bereinigung (mailto:, javascript:, data:, etc.)
- klare Trennung zwischen internen und externen Links
- API-kompatibel zu extract_links_http() deiner Gesamtanwendung

Dieses Modul wird im Crawler für Deep Crawling verwendet und
liefert die primären Linksets für alle weiteren Analyseschritte
(z. B. FUJI, FAIR, Repositories, APIs, Downloads).
"""

import asyncio
from urllib.parse import urljoin, urlparse, urldefrag
from playwright.sync_api import sync_playwright


# -------------------------------------------------------------
# Hilfsfunktionen
# -------------------------------------------------------------

def _same_site(netloc: str, domain: str) -> bool:
    """Prüft, ob eine URL auf derselben Domain oder Subdomain liegt."""
    return (
        netloc.lower() == domain.lower() or
        netloc.lower().endswith("." + domain.lower())
    )


def _is_http(url: str) -> bool:
    """Erlaubt nur http/https-URLs."""
    return urlparse(url).scheme in ("http", "https")


def _clean_abs(base: str, href: str) -> str | None:
    """
    Normalisiert relative und absolute Links.
    Filtert technisch irrelevante Links (mailto:, javascript:, etc.).
    """
    if not href:
        return None

    href = href.strip()

    # Nicht-webfähige Links ausschließen
    if href.startswith(("mailto:", "javascript:", "data:", "tel:", "#")):
        return None

    # Fragmente (#...) entfernen
    href, _ = urldefrag(href)

    # Relative URL → absolute URL
    absu = urljoin(base, href)

    if not _is_http(absu):
        return None

    return absu.rstrip("/")  # Vereinheitlichung


def _split_internal_external(found: set[str], domain: str):
    """Teilt Links in intern/external auf und gibt Statistiken aus."""
    internal, external = set(), set()

    for u in found:
        nl = urlparse(u).netloc.lower()
        if _same_site(nl, domain):
            internal.add(u)
        else:
            external.add(u)

    print(f"✅ Interne Links: {len(internal)}")
    print(f"🌍 Externe Links: {len(external)}")
    print(f"📊 Gesamt: {len(found)}")

    return internal, external


# -------------------------------------------------------------
# Playwright Deep Extractor
# -------------------------------------------------------------

def _playwright_extract(url: str):
    """
    Führt die Extraktion durch:
    - öffnet Chromium headless
    - ignoriert ungültige HTTPS-Zertifikate
    - sammelt Links aus HTML + Netzwerkverkehr
    """
    links = set()
    domain = urlparse(url).netloc.lower()

    with sync_playwright() as p:
        print(f"🌐 [DEEP] Lade Seite: {url}")

        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)  # 💡 wichtig für alte Editionen
        page = context.new_page()

        requests_seen = set()

        # Netzwerk-Anfragen erfassen
        page.on("request", lambda req: requests_seen.add(req.url) if _is_http(req.url) else None)
        page.on("response", lambda res: requests_seen.add(res.url) if _is_http(res.url) else None)

        # -------------------
        # Seite laden
        # -------------------
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"⚠️ Fehler beim Laden mit HTTPS: {e}")
            context.close()
            browser.close()
            return None  # → löst später HTTP-Fallback aus

        # -------------------
        # HTML-Links extrahieren
        # -------------------
        anchors = page.query_selector_all("a[href]")
        for a in anchors:
            href = a.get_attribute("href")
            cleaned = _clean_abs(url, href)
            if cleaned:
                links.add(cleaned)

        # -------------------
        # Netzwerk-Links hinzunehmen
        # -------------------
        links |= requests_seen

        context.close()
        browser.close()

    print(f"🔗 {len(links)} Links (DEEP, Playwright) gefunden")
    return _split_internal_external(links, domain)


def deep_extract_links(url: str):
    """
    Robuster Deep Extractor:
    - versucht zuerst die Original-URL
    - bei HTTPS-Fehler → fallback auf HTTP://
    """
    result = _playwright_extract(url)

    if result is None and url.startswith("https://"):
        fallback = "http://" + url[len("https://"):]
        print(f"🔄 Fallback auf HTTP: {fallback}")
        result = _playwright_extract(fallback)

    if result is None:
        print("❌ Playwright Extraction vollständig gescheitert.")
        return set(), set()

    return result


# -------------------------------------------------------------
# Öffentliche API – kompatibel mit deiner App
# -------------------------------------------------------------

async def extract_links_http(start_url: str, mode: str = "deep", raw_html: str | None = None):
    """
    Asynchrone API für deine App.
    Mode/HTML werden ignoriert (für API-Kompatibilität).
    """
    print(f"🔎 extract_links_http() → DEEP für: {start_url}")

    loop = asyncio.get_event_loop()
    # Playwright läuft synchron → deshalb run_in_executor()
    return await loop.run_in_executor(None, lambda: deep_extract_links(start_url))
