"""
link_checker.py
==============================
Dieses Modul prüft URLs effizient und parallel auf Erreichbarkeit.
Einsetzbar, um tote Links (404, SSL-Fehler, DNS-Fehler usw.) im Crawling
automatisch zu erkennen.

Zwei Kernfunktionen:
1) check_link_single()  – prüft eine einzelne URL
2) check_links_bounded() – prüft mehrere URLs mit begrenzter Parallelität
"""

import aiohttp
import asyncio


# --------------------------------------------------------------------
# 🔍 EINZELNE LINKPRÜFUNG
# --------------------------------------------------------------------
async def check_link_single(url: str, session: aiohttp.ClientSession) -> dict:
    """
    Prüft eine einzelne URL asynchron und gibt HTTP-Status oder Fehler zurück.

    Rückgabeformat:
        {"url": <str>, "status": <int oder Fehlertext>}

    Ablauf:
    - GET-Request mit 10s Timeout
    - HTTP-Status wird zurückgegeben (z. B. 200, 404)
    - Bei Fehlern (Timeout, DNS-Error, SSL-Error …) wird ein Text wie
      "ERROR [TimeoutError] ..." erzeugt
    """
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            print(f"🔗 Link geprüft: {url} → Status {resp.status}")
            return {"url": url, "status": resp.status}

    except Exception as e:
        # Fehlertext konsistent erzeugen
        error_type = type(e).__name__
        error_text = str(e) if str(e) else repr(e)
        error_msg = f"ERROR [{error_type}] {error_text}"
        print(f"⚠️ Fehler beim Prüfen von {url}: {error_msg}")
        return {"url": url, "status": error_msg}


# --------------------------------------------------------------------
# ⚙️ PARALLELE LINKPRÜFUNG (Gesteuert über Semaphore)
# --------------------------------------------------------------------
async def check_links_bounded(urls: list, max_concurrent: int = 10) -> list:
    """
    Prüft mehrere URLs parallel, aber mit kontrollierter Obergrenze
    gleichzeitiger Requests (via Semaphore).

    Vorteile:
    - Keine Überlastung von Zielservern
    - Hohe Geschwindigkeit durch parallele Ausführung
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async with aiohttp.ClientSession() as session:

        # Jede einzelne Prüfung wartet auf freie Kapazität der Semaphore
        async def bounded(link):
            async with semaphore:
                return await check_link_single(link, session)

        # Starte alle Prüfungen gleichzeitig
        results = await asyncio.gather(*(bounded(url) for url in urls))
        return results
