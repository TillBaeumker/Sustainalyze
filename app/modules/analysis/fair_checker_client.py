"""
fair_checker_client.py
==============================

FAIR-Checker API-Integration (JSON-LD)
--------------------------------------

Dieses Modul stellt eine robuste, vereinfachte Schnittstelle zur öffentlichen
FAIR-Checker-API bereit. Untersucht wird ausschließlich der stabile
JSON-LD-Endpunkt `/api/check/metrics_all`, der sämtliche FAIR-Metriken in einer
maschinenlesbaren Form liefert.

Ablauf:
-------
1. URL bereinigen (Fragmente entfernen)
2. Anfrage an den FAIR-Checker-Server senden
3. JSON-LD-Knoten auswerten
4. FAIR-Metriken extrahieren (z. B. F1A, F2A, R1.2)
5. Gesamtscore berechnen (0–100 %)

"""

import aiohttp
import json
from urllib.parse import urldefrag
from app.core.config import settings

# --------------------------------------------------------------------
# Konfiguration
# --------------------------------------------------------------------

# Basis-URL des FAIR-Checker-Servers aus der .env
BASE = (getattr(settings, "FAIR_CHECKER_BASE", "") or "").rstrip("/")

# Timeout für HTTP-Anfragen
TIMEOUT = aiohttp.ClientTimeout(
    total=getattr(settings, "FAIR_CHECKER_TIMEOUT", 30) or 30
)

# JSON-LD-Endpunkt der FAIR-Checker-API
JSONLD = "/api/check/metrics_all"

# Prädikate nach W3C DQV (Data Quality Vocabulary)
DQV_MEAS  = "http://www.w3.org/ns/dqv#QualityMeasurement"
DQV_IS_OF = "http://www.w3.org/ns/dqv#isMeasurementOf"
DQV_VALUE = "http://www.w3.org/ns/dqv#value"


# --------------------------------------------------------------------
# Hauptfunktion
# --------------------------------------------------------------------
async def run_fair_checker_once(start_url: str) -> dict:
    """
    Führt eine FAIR-Prüfung für eine einzelne URL aus.

    Rückgabeformat:
    {
        "ok": True,
        "url": "...",
        "version": "json-ld",
        "metrics": [{"metric": "F1A", "score": 2}, ...],
        "score_overall": 87.5,
        "debug": {...}
    }

    Bei Fehlern:
    {
        "ok": False,
        "reason": "...",
        "debug": {...}
    }
    """
    if not BASE:
        return {"ok": False, "reason": "FAIR_CHECKER_BASE not set"}

    # Entfernt z. B. #section
    url, _ = urldefrag(start_url)
    endpoint = f"{BASE}{JSONLD}"

    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as s:
            async with s.get(
                endpoint,
                params={"url": url},
                headers={"Accept": "application/json"},
            ) as r:
                if r.status != 200:
                    return _fail(url, endpoint, r.status, await r.text())

                raw = json.loads(await r.text())

                # Der Endpunkt liefert eine Liste von JSON-LD-Knoten
                if not isinstance(raw, list):
                    return _fail(url, endpoint, r.status, str(raw), reason="Unexpected JSON")

                details = _extract_jsonld_metrics(raw)

                return {
                    "ok": True,
                    "url": url,
                    "version": "json-ld",
                    "metrics": details,
                    "score_overall": _calc_overall_score(details),
                    "debug": {
                        "base": BASE,
                        "endpoint": endpoint,
                        "url": url,
                        "status": 200,
                    },
                }

    except Exception as e:
        # Fängt z. B. Netzwerkfehler oder JSON-Fehler ab
        return {"ok": False, "reason": f"Exception: {e.__class__.__name__}: {e}"}


# --------------------------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------------------------
def _extract_jsonld_metrics(nodes: list[dict]) -> list[dict]:
    """
    Extrahiert Metrikcode (z. B. F2A) und Score (0–2) aus JSON-LD-Knoten.
    """
    results = []

    for n in nodes:
        # Nur DQV QualityMeasurement-Knoten
        if DQV_MEAS not in set(n.get("@type", [])):
            continue

        metric_id = None

        # Extrahiert z. B. https://w3id.org/fair/principles/F2A → F2A
        for v in n.get(DQV_IS_OF) or []:
            if "@id" in v:
                metric_id = v["@id"].rsplit("/", 1)[-1]
                break

        # Score extrahieren
        try:
            score = int((n.get(DQV_VALUE) or [{}])[0].get("@value", 0))
        except Exception:
            score = 0

        if metric_id:
            results.append({"metric": metric_id, "score": score})

    return sorted(results, key=lambda x: x["metric"])


def _calc_overall_score(details: list[dict]) -> float:
    """
    Berechnet den Gesamtscore (0–100 %), basierend auf:
      Score pro Metrik ∈ {0,1,2}
    """
    if not details:
        return 0.0

    total = sum(d["score"] for d in details)
    max_total = 2 * len(details)

    return round((total / max_total) * 100, 1)


def _fail(url, endpoint, status, text, reason=None):
    """Zentrale Fehlerausgabe für API-Fehler und unerwartete Daten."""
    return {
        "ok": False,
        "reason": reason or f"HTTP {status}",
        "debug": {
            "base": BASE,
            "endpoint": endpoint,
            "url": url,
            "status": status,
            "raw_text": (text[:800] if text else None),
        },
    }
