# -*- coding: utf-8 -*-
"""
Evaluation-Modul
----------------
Extrahiert Isolation- & Staticization-Matches exakt wie das Scoring,
inkl. aller Normalisierungs- und Matching-Schritte aus scoring.py.

ABER: Im Unterschied zum Scoring wird zusätzlich der volle Kontext
(± 5 Wörter) aus dem ORIGINALTEXT (Wappalyzer-Rohdaten + Shodan-Rohdaten)
ausgegeben, um Debugging und wissenschaftliche Validität zu ermöglichen.

JSON-Ausgabe:
{
  "staticization": { "static_hits": [...], "dynamic_hits": [...] },
  "isolation": { "iso_hits": [...] }
}
"""

import json
import os
import re
import sys
from urllib.parse import urlparse

# --- App-Module ----------------------------------------------------------
from app.modules.analysis.wappalyzer import (
    analyze_technologies_with_wappalyzer,
    parse_wappalyzer_result,
)
from app.modules.analysis.shodan_client import get_shodan_info

# Original-Heuristiklisten
from app.modules.results.heuristics import (
    STATIC_SITE_GENERATORS,
    STATIC_HOST_PLATFORMS,
    DYNAMIC_FRAMEWORKS,
    CMS_RUNTIME,
    ISO_STRONG,
)

# Original-Scoring-Funktionen
from app.modules.results.scoring import (
    _wapp_concat,
    _shodan_concat,
    _match_tech_name,
)


# =========================================================================
# 🔍 Kontext-Extraktion aus *Originaltext* (±5 Wörter)
# =========================================================================
def extract_context(raw_text: str, match: str, window: int = 5):
    """
    Kontextsuche im ORIGINALTEXT, nicht im normalisierten Text.
    Tokenisierung erfolgt sehr breit, damit alles gefunden wird.
    """
    # Tokenisierung: trenne ALLES, was kein alphanumerisches Zeichen ist
    tokens = re.split(r"[^a-zA-Z0-9]+", raw_text.lower())
    tokens = [t for t in tokens if t]

    ltokens = tokens
    m = match.lower()

    for i, tok in enumerate(ltokens):
        if tok == m:
            start = max(0, i - window)
            end = i + window + 1
            return " ".join(ltokens[start:end])

    return None


# =========================================================================
# 🔧 Scoring-identische Normalisierung für Matching
# =========================================================================
def prepare_scoring_text_wappalyzer(wapp_raw):
    """1:1 Wappalyzer-Text wie im Scoring."""
    parsed = parse_wappalyzer_result(wapp_raw)
    norm_text = _wapp_concat(parsed)
    return parsed, norm_text


def prepare_scoring_text_shodan(shodan_raw):
    """1:1 Shodan-Text wie im Scoring."""
    raw = shodan_raw.get("raw_json", shodan_raw)
    return _shodan_concat(raw)


# =========================================================================
# 🧠 Hauptfunktion — identisch zu Scoring, aber mit Kontext
# =========================================================================
def analyze_iso_static(url: str):
    print(f"🔍 Starte Evaluation für: {url}")

    # ------------------------------------------------------------
    # 1) Originaldaten holen
    # ------------------------------------------------------------
    wapp_raw = analyze_technologies_with_wappalyzer(url)
    shodan_raw = get_shodan_info(url)

    # ------------------------------------------------------------
    # 2) Normalisierten MATCH-Text erzeugen (wie Scoring)
    # ------------------------------------------------------------
    wap_parsed, wap_norm = prepare_scoring_text_wappalyzer(wapp_raw)
    shodan_norm = prepare_scoring_text_shodan(shodan_raw)

    combined_norm = (wap_norm + " | " + shodan_norm).lower()

    # ------------------------------------------------------------
    # 3) Originaltext für Kontext erzeugen
    # ------------------------------------------------------------
    raw_text = (
        json.dumps(wapp_raw, ensure_ascii=False) +
        " | " +
        json.dumps(shodan_raw, ensure_ascii=False)
    ).lower()

    # ------------------------------------------------------------
    # 4) STATICIZATION
    # ------------------------------------------------------------
    static_hits = []
    dynamic_hits = []

    for t in wap_parsed:
        name = t.get("name", "")
        if not name:
            continue

        # --- statische Matches
        m_static = _match_tech_name(
            name,
            STATIC_SITE_GENERATORS + STATIC_HOST_PLATFORMS
        )
        if m_static:
            ctx = extract_context(raw_text, m_static)
            static_hits.append({"term": m_static, "context": ctx})
            continue

        # --- dynamische Matches
        m_dynamic = _match_tech_name(
            name,
            DYNAMIC_FRAMEWORKS + CMS_RUNTIME
        )
        if m_dynamic:
            ctx = extract_context(raw_text, m_dynamic)
            dynamic_hits.append({"term": m_dynamic, "context": ctx})

    # ------------------------------------------------------------
    # 5) ISOLATION
    # ------------------------------------------------------------
    iso_hits = []

    for term in ISO_STRONG:
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        if re.search(pattern, combined_norm):
            ctx = extract_context(raw_text, term)
            iso_hits.append({"term": term, "context": ctx})

    # ------------------------------------------------------------
    # 6) Ausgabe speichern
    # ------------------------------------------------------------
    hostname = urlparse(url).hostname or "unknown"
    out_dir = os.getenv("EVAL_OUTPUT_DIR", "app/evaluation/results/iso_stat")
    os.makedirs(out_dir, exist_ok=True)

    out_file = os.path.join(out_dir, f"{hostname}.json")

    result = {
        "url": url,
        "staticization": {
            "static_hits": static_hits,
            "dynamic_hits": dynamic_hits,
        },
        "isolation": {
            "iso_hits": iso_hits,
        },
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"✅ Ergebnis gespeichert unter: {out_file}")
    return result


# =========================================================================
# CLI
# =========================================================================
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Verwendung:")
        print("  python3 -m app.evaluation.iso_static_eval https://example.org/")
        sys.exit(1)

    analyze_iso_static(sys.argv[1])
