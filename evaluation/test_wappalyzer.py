# -*- coding: utf-8 -*-
"""
Testskript für Wappalyzer-Analysen mit CLI-URLs
"""

import os
import sys
import json
from datetime import datetime

# --- Pfad hinzufügen, damit wappalyzer.py importiert werden kann ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

# Jetzt ist der Import möglich
from app.modules.analysis.wappalyzer import (
    analyze_technologies_with_wappalyzer,
    parse_wappalyzer_result
)
# Ergebnisordner
RESULTS_DIR = "/home/till/sustainability_checker/app/evaluation/results/wappalyzer"
os.makedirs(RESULTS_DIR, exist_ok=True)

def save_as_json(data: dict, filename: str):
    filepath = os.path.join(RESULTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"💾 Ergebnis gespeichert unter: {filepath}")

def run_wappalyzer_for_urls(urls):
    if not urls:
        print("⚠️ Keine URLs übergeben. Beispiel:")
        print("   python3 test_wappalyzer.py https://example.com")
        sys.exit(1)

    print("🚀 Starte Wappalyzer-Analysen...\n")

    for url in urls:
        print("=" * 80)
        print(f"🌐 Analysiere: {url}")

        raw_result = analyze_technologies_with_wappalyzer(url)

        parsed = {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "raw": raw_result,
            "parsed": parse_wappalyzer_result(raw_result)
        }

        safe_name = url.replace("https://", "").replace("http://", "").replace("/", "_")
        filename = f"wappalyzer_{safe_name}.json"

        save_as_json(parsed, filename)

    print("\n🏁 Alle Analysen abgeschlossen.")

if __name__ == "__main__":
    urls = sys.argv[1:]
    run_wappalyzer_for_urls(urls)
