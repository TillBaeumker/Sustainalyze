# file: app/evaluation/test_linkextraction.py
# -*- coding: utf-8 -*-
"""
Testet die Stabilität der neuen Playwright-basierten Link-Extraktion.

Ablauf:
- Führt extract_links_http() 15x auf derselben URL aus
- Misst die Anzahl gefundener Links pro Durchlauf
- Berechnet Mittelwert, Standardabweichung, Variationskoeffizient (CV)
- Speichert Ergebnisse sauber als JSON in results/links/
"""

import os
import sys
import json
import time
import asyncio
import statistics
from urllib.parse import urlparse

# Projektpfad einbinden
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.modules.analysis.link_extractor import extract_links_http


# ---------------------------------------------------------
# Einzel-Lauf der Extraktion
# ---------------------------------------------------------

async def run_single_extraction(url: str) -> int:
    """
    Ruft die zentrale Extraktionsfunktion auf und gibt
    die Gesamtzahl gefundener Links zurück.
    """
    internal, external = await extract_links_http(url, mode="deep")
    total = len(internal) + len(external)
    print(f"🔗 Extraktion: {total} Links")
    return total


# ---------------------------------------------------------
# Vergleich / Stabilitätsanalyse
# ---------------------------------------------------------

async def compare_link_extraction(url: str, runs: int = 15):
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")

    print(f"\n🌐 Starte Stabilitätsanalyse für: {url}")
    print(f"🧪 Durchläufe: {runs}\n")

    results = []
    times = []

    for i in range(runs):
        print(f"▶️ Run {i+1}/{runs}")

        t0 = time.time()
        total_links = await run_single_extraction(url)
        t1 = time.time()

        results.append(total_links)
        times.append(round(t1 - t0, 3))

        # Kleine Pause, um den Browser zu entlasten
        await asyncio.sleep(0.3)

    # Statistische Auswertung
    mean = round(statistics.mean(results), 2)
    stddev = round(statistics.stdev(results), 2) if len(results) > 1 else 0.0
    cv = round(stddev / mean, 3) if mean > 0 else None

    print("\n📊 Ergebnisse:")
    print("   Werte:", results)
    print(f"   Mittelwert: {mean}")
    print(f"   Std-Abweichung: {stddev}")
    print(f"   CV: {cv}")
    print()

    # Speicherpfad
    OUT_DIR = os.getenv("TEST_LINK_OUTPUT_DIR", "app/evaluation/results/links")
    os.makedirs(OUT_DIR, exist_ok=True)

    save_path = os.path.join(OUT_DIR, f"stability_{domain}.json")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    data = {
        "target": url,
        "runs": runs,
        "samples": results,
        "mean": mean,
        "stddev": stddev,
        "cv": cv,
        "times": times,
        "timestamp": time.time(),
    }

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"📂 Ergebnisse gespeichert unter:\n   {save_path}\n")


# ---------------------------------------------------------
# CLI-Einstiegspunkt
# ---------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Nutzung:")
        print("   python app/evaluation/test_linkextraction.py <URL>")
        sys.exit(1)

    url = sys.argv[1]
    asyncio.run(compare_link_extraction(url))
