"""
structured_metadata.py
=======================

Analyse strukturierter Metadaten (FAIR F2A und F2B)
---------------------------------------------------

Dieses Modul automatisiert die Bewertung der beiden zentralen FAIR-Metriken
im Bereich der semantischen Metadatenqualität:

    • F2A – "Data are described with structured metadata"
    • F2B – "Metadata are described using shared vocabularies"

Technische Grundlage
--------------------
Für die Bewertung wird die öffentliche REST-API des *FAIR-Checker*-Tools
verwendet:
    https://fair-checker.france-bioinformatique.fr/api/check

FAIR-Checker (Gaignard et al., 2023) führt intern SPARQL-Abfragen und
SHACL-Validierungen durch, um RDF-Strukturen und Ontologieverwendungen
automatisiert zu erkennen. Dieses Modul kapselt die API-Kommunikation, führt
Retry-Logik, Fehlerbehandlung und Interpretation der API-Antworten durch und
liefert eine klar strukturierte Zusammenfassung.

- check_f2a_f2b_for_url(session, page_url, timeout=20.0)

Diese Funktion:
    1. bereinigt die URL,
    2. ruft F2A und F2B parallel über die FAIR-Checker-API ab,
    3. interpretiert die Ergebnisse (Score, RDF-Tripel, verwendete Vokabulare),
    4. erzeugt eine zusammenfassende Bewertung.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urldefrag
import aiohttp

# =============================
# Basis-URL der FAIR-Checker-API
# =============================
FAIR_BASE = "https://fair-checker.france-bioinformatique.fr/api/check"


# =============================
# Hilfsfunktionen
# =============================

class FairApiError(Exception):
    """Fehlerhülle für API-Aufrufe, um Netzwerk- und Antwortfehler gezielt zu behandeln."""


def _clean_url(u: str) -> str:
    """Bereinigt URLs, entfernt Fragmentteile ('#...') und Leerzeichen."""
    u = (u or "").strip()
    return urldefrag(u)[0]


def _metric_url(metric: str, target_url: str) -> str:
    """
    Erzeugt die vollständige API-Endpunkt-URL für eine gegebene FAIR-Metrik.

    Beispiel:
        _metric_url("F2A", "https://example.org")
        → "https://fair-checker.france-bioinformatique.fr/api/check/metric_F2A?url=https%3A%2F%2Fexample.org"
    """
    return f"{FAIR_BASE}/metric_{metric}?url={quote(target_url, safe='')}"


async def _fetch_json(
    session: aiohttp.ClientSession,
    url: str,
    timeout: float = 20.0,
    retries: int = 2,
    backoff: float = 0.8,
) -> Dict[str, Any]:
    """
    Asynchrone Hilfsfunktion für API-Requests mit Fehlerbehandlung und Retry-Logik.

    - Holt JSON-Antworten über HTTP GET ab.
    - Wiederholt bei temporären Fehlern (HTTP 429, 502, 503 etc.).
    - Wird zentral von den F2A/F2B-Funktionen genutzt.
    """
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            async with session.get(url, timeout=timeout, headers={"accept": "application/json"}) as resp:
                if resp.status == 200:
                    return await resp.json(content_type=None)
                if resp.status in (429, 500, 502, 503, 504) and attempt < retries:
                    await asyncio.sleep(backoff * (2 ** attempt))
                    continue
                text = await resp.text()
                raise FairApiError(f"HTTP {resp.status} for {url}: {text[:500]}")
        except Exception as e:
            last_err = e
            if attempt < retries:
                await asyncio.sleep(backoff * (2 ** attempt))
            else:
                raise
    assert last_err is not None
    raise last_err


def _safe_int(x: Any) -> int:
    """Versucht, eine Zahl in int umzuwandeln, ansonsten 0 (z. B. bei None oder Text)."""
    try:
        return int(x)
    except Exception:
        return 0


# =============================
# Interpretation der FAIR-Metriken
# =============================


def _interpret_f2a(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Interpretiert die FAIR-Metrik F2A:
    ---------------------------------
    Prüft, ob strukturierte, maschinenlesbare Metadaten (z. B. RDF-Tripel)
    in der Webseite vorhanden sind.

    Das Ergebnis der FAIR-API enthält meist:
    - score: numerische Bewertung (0–100)
    - comment: erklärender Text (z. B. „12 RDF triples found“)
    - recommendation: Verbesserungshinweise

    Erkenntnisse:
    - Ein positiver Score oder erkannte RDF-Tripel deuten auf vorhandene strukturierte Metadaten hin.
    """
    score = _safe_int(payload.get("score"))
    comment = (payload.get("comment") or "")

    rdf_count: Optional[int] = None
    m = re.search(r"(\d+)\s+rdf triples", comment, flags=re.I)
    if m:
        rdf_count = int(m.group(1))
    elif "no rdf triples found" in comment.lower():
        rdf_count = 0

    has_structured_metadata = bool(rdf_count and rdf_count > 0) or score > 0

    return {
        "metric": "F2A",
        "score": score,
        "target_uri": payload.get("target_uri"),
        "has_structured_metadata": has_structured_metadata,
        "rdf_count": rdf_count,
        "evidence": payload.get("comment"),
        "recommendation": payload.get("recommendation"),
        "raw": payload,
    }


def _interpret_f2b(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Interpretiert die FAIR-Metrik F2B:
    ---------------------------------
    Bewertet, ob die vorhandenen Metadaten auf *gemeinsam genutzten Vokabularen*
    basieren. FAIR-Checker selbst gibt keine konkreten Namen aus,
    sondern prüft nur, ob die Klassen/Properties aus registrierten Ontologien stammen.
    """
    score = _safe_int(payload.get("score"))
    comment = (payload.get("comment") or "")
    no_rdf = "no rdf found" in comment.lower() or "no rdf triples found" in comment.lower()

    # FAIR-Checker liefert keine konkreten Namen, nur Nachweise über LOV/OLS/BioPortal
    uses_shared_vocabularies = False
    if not no_rdf and (
        "known in linked open vocabularies" in comment.lower()
        or "ontology registries" in comment.lower()
        or score > 0
    ):
        uses_shared_vocabularies = True

    # Vereinheitlichte semantische Ausgabe
    rdf_vocabularies = ["nicht spezifiziert"] if uses_shared_vocabularies else None

    return {
        "metric": "F2B",
        "score": score,
        "target_uri": payload.get("target_uri"),
        "uses_shared_vocabularies": uses_shared_vocabularies,
        "rdf_vocabularies": rdf_vocabularies,
        "evidence": payload.get("comment"),
        "recommendation": payload.get("recommendation"),
        "raw": payload,
    }



# =============================
# Hauptfunktion: check_f2a_f2b_for_url()
# =============================

async def check_f2a_f2b_for_url(
    session: aiohttp.ClientSession,
    page_url: str,
    timeout: float = 20.0
) -> Dict[str, Any]:
    """
    Prüft eine Webseite auf die FAIR-Metriken F2A (Structured Metadata)
    und F2B (Shared Vocabularies) über die FAIR-Checker-API.

    Ablauf:
    --------
    1. Bereinigung der Ziel-URL
    2. Parallele Abfrage der FAIR-Metriken F2A und F2B (asynchron)
    3. Interpretation der API-Ergebnisse
    4. Zusammenführung zu einer leicht interpretierbaren JSON-Struktur

    Technischer Hintergrund:
    ------------------------
    FAIR-Checker verwendet intern SPARQL-Abfragen und SHACL-Regeln, um RDF-Tripel
    und Ontologieverwendungen zu prüfen. Durch die REST-API ist es möglich,
    diese Prüfungen automatisiert für jede gecrawlte Seite durchzuführen.

    Beispielnutzung:
        async with aiohttp.ClientSession() as session:
            result = await check_f2a_f2b_for_url(session, "https://example.org")

    Rückgabe:
        Dictionary mit F2A-, F2B-Ergebnissen und einer zusammenfassenden Bewertung.
    """
    clean = _clean_url(page_url)

    # Asynchron beide FAIR-Metriken abrufen
    async def one(metric: str):
        data = await _fetch_json(session, _metric_url(metric, clean), timeout=timeout)
        return _interpret_f2a(data) if metric == "F2A" else _interpret_f2b(data)

    res = await asyncio.gather(one("F2A"), one("F2B"), return_exceptions=True)

    out: Dict[str, Any] = {
        "url": clean,
        "F2A": None,
        "F2B": None,
        "summary": None,
        "logs": {"F2A": None, "F2B": None},
        "_source": "fair-checker-api",
    }

    # Ergebnisse zusammenführen
    for r in res:
        if isinstance(r, Exception):
            out.setdefault("error", str(r))
            continue
        out[r["metric"]] = r
        out["logs"][r["metric"]] = r.get("evidence")

    f2a, f2b = out.get("F2A") or {}, out.get("F2B") or {}
    has_structured = bool(f2a.get("has_structured_metadata"))
    uses_shared = f2b.get("uses_shared_vocabularies")

    # Einfache textuelle Zusammenfassung
    if has_structured and uses_shared is True:
        verdict = "Strukturierte Metadaten vorhanden und standardisierte Vokabulare genutzt (nicht spezifiziert)."
    elif has_structured and uses_shared is False:
        verdict = "Strukturierte Metadaten vorhanden, aber keine/nicht erkennbare standardisierte Vokabulare."
    else:
        verdict = "Keine strukturierten, maschinenlesbaren Metadaten erkannt."

    out["summary"] = {
        "has_structured_metadata": has_structured,
        "uses_shared_vocabularies": uses_shared,
        "rdf_count": f2a.get("rdf_count"),
        "rdf_vocabularies": f2b.get("rdf_vocabularies"),
        "scores": {
            "F2A": f2a.get("score", 0),
            "F2B": f2b.get("score", 0),
        },
        "verdict": verdict,
    }

    return out
