# -*- coding: utf-8 -*-
"""
main.py
=======

Zentrale Applikationssteuerung der FastAPI-Anwendung zur automatisierten
Analyse digitaler Editionen.

Dieses Modul initialisiert die Webanwendung, bindet statische Ressourcen
und Templates ein, verarbeitet eingehende Analyseanfragen und leitet die
Analysepipeline über `handle_analysis` ein. Ergebnisse und Laufzeitdaten
werden im Frontend ausgegeben und über einen internen Log-Puffer für
Monitoring-Zwecke vorgehalten.

Die Funktionalität der Anwendung bleibt vollständig unverändert;
es wurden ausschließlich Struktur, Kommentierung und Übersichtlichkeit
für die wissenschaftliche Abgabe optimiert.
"""

import sys
import os
import time
import traceback
from typing import Dict, Any

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Analysepipeline
from app.modules.manager.handle_analysis import handle_analysis


# -------------------------------------------------------------------
# Globaler Exception Hook: sorgt für nachvollziehbare Fehlerausgabe
# -------------------------------------------------------------------
def handle_exception(exc_type, exc_value, exc_traceback):
    """Zentrale Fehlerbehandlung außerhalb des FastAPI-Kontextes."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    print("❌ Unbehandelte Ausnahme:")
    traceback.print_exception(exc_type, exc_value, exc_traceback)


sys.excepthook = handle_exception


# -------------------------------------------------------------------
# FastAPI-Anwendung initialisieren
# -------------------------------------------------------------------
app = FastAPI()

# Verzeichnis für statische Dateien sicherstellen
STATIC_DIR = "app/static"
os.makedirs(STATIC_DIR, exist_ok=True)

# Statische Dateien und Templates einbinden
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory="app/templates")


# -------------------------------------------------------------------
# Interner Log-Puffer für Live-Ausgaben im Frontend
# -------------------------------------------------------------------
log_buffer: list[str] = []


def log(msg: str):
    """Einfaches Puffern und Ausgeben von Log-Nachrichten."""
    print(msg)
    log_buffer.append(msg)
    if len(log_buffer) > 300:
        log_buffer.pop(0)


@app.get("/status", response_class=PlainTextResponse)
def get_status():
    """Aktuellen Log-Puffer zur Anzeige im Frontend ausgeben."""
    return "\n".join(log_buffer)


# -------------------------------------------------------------------
# Globale Speicherung des letzten Analyseergebnisses (optional)
# -------------------------------------------------------------------
last_result: Dict[str, Any] | None = None


# -------------------------------------------------------------------
# ROUTES
# -------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Root-Endpunkt: liefert die Startseite der Anwendung.
    Beim initialen Aufruf sind keine Analyseergebnisse gesetzt.
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": {},
            "report": None,
            "error": None,
        }
    )


@app.post("/analyse", response_class=HTMLResponse)
async def analyse(
    request: Request,
    url: str = Form(...),
    max_pages: int = Form(3),
    fair_mode: str = Form("start_only"),
):
    """
    Führt die vollständige Analyse durch:

    - Validierung der Eingabe-URL
    - Begrenzung der Crawl-Seitentiefe
    - Delegation an `handle_analysis`
    - Fehlerbehandlung und Ausgabe im Template

    Ergebnisse werden im Template angezeigt und im globalen
    `last_result` gespeichert.
    """
    global last_result
    started = time.perf_counter()

    try:
        # Log zurücksetzen und URL prüfen
        log_buffer.clear()
        url = url.strip()

        if not url.startswith(("http://", "https://")):
            raise ValueError("Nur URLs mit http(s):// werden akzeptiert.")

        # Crawl-Tiefe begrenzen
        max_pages = max(1, min(max_pages, 5))

        log(f"🚀 Starte Analyse: {url}")

        # Analyse starten
        result = await handle_analysis(
            request=request,
            url=url,
            log_func=log,
            max_pages=max_pages,
            fair_mode=fair_mode,
        )

        log("🎉 Analyse fertig.")
        last_result = result

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": result,
                "report": result.get("report"),
                "error": None,
            }
        )

    except Exception as e:
        log("❌ Fehler: " + str(e))
        traceback.print_exc()

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": {},
                "report": None,
                "error": f"Analysefehler: {e}",
            }
        )

    finally:
        # Laufzeitmessung
        duration = time.perf_counter() - started
        log(f"⏱️ Dauer: {duration:.2f}s")
