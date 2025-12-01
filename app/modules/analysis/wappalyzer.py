"""
wappalyzer_client.py
==============================

Wappalyzer-Integration (CLI-Variante)
-------------------------------------

Dieses Modul führt eine robuste Technologieanalyse mittels der
*Wappalyzer*-CLI durch. Dies geschieht nicht über die Cloud-API,
sondern über eine lokale Node.js-Installation:

    node wappalyzer/src/drivers/npm/cli.js <url>

Funktionen:
-----------
1. analyze_technologies_with_wappalyzer(url, path, retries)
   Führt die CLI-Analyse aus, bereinigt result.stdout,
   behandelt JSON-Fehler und liefert das rohe Ergebnis.

2. parse_wappalyzer_result(result)
   Formatiert das CLI-Ergebnis für das Frontend/Scoring.
"""

import subprocess
import json
from typing import Optional, Dict, List


def analyze_technologies_with_wappalyzer(
    url: str,
    wappalyzer_path: str = "/home/till/sustainability_checker/wappalyzer",
    max_retries: int = 3,
) -> Optional[Dict]:
    """
    Führt eine stabile Technologieanalyse mit der Wappalyzer-CLI durch.

    Ablauf:
    -------
    1. Build des CLI-Pfads (cli.js)
    2. Mehrfache Ausführung von:
            xvfb-run node <cli_path> <url>
    3. JSON-Parsing der Wappalyzer-Ausgabe
    4. Erfolgsabbruch, sobald Technologien erkannt werden
    5. Rückgabe des originalen Datenobjekts

    Fehlerfälle:
    ------------
    - leere Ausgabe → erneute Versuche
    - ungültiges JSON → erneute Versuche
    - Timeout / subprocess.CalledProcessError → Logging + Retry
    """
    cli_path = f"{wappalyzer_path}/src/drivers/npm/cli.js"

    print(f"🧪 [Wappalyzer] Starte Technologieanalyse für URL: {url}")
    print(f"🔄 [Wappalyzer] Verwende CLI-Pfad: {cli_path}")

    for attempt in range(1, max_retries + 1):
        try:
            result = subprocess.run(
                ["xvfb-run", "node", cli_path, url],
                capture_output=True,
                text=True,
                check=True,
                cwd=wappalyzer_path,
                timeout=100,
            )

            output = result.stdout.strip()
            if not output:
                print(f"⚠️ [Wappalyzer] Leere Ausgabe (Versuch {attempt}/{max_retries})")
                continue

            try:
                data = json.loads(output)
            except json.JSONDecodeError:
                print(f"❌ [Wappalyzer] Ungültiges JSON (Versuch {attempt}/{max_retries})")
                continue

            technologies = data.get("technologies", [])
            if technologies:
                print("✅ [Wappalyzer] Analyse erfolgreich.")
                print(f"🔍 [Wappalyzer] Gefundene Technologien: {len(technologies)}")
                return data

            print(f"⚠️ [Wappalyzer] 0 Technologien erkannt (Versuch {attempt}/{max_retries})")

        except subprocess.TimeoutExpired:
            print(f"❌ [Wappalyzer] Timeout bei Versuch {attempt}/{max_retries}")
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.strip() if e.stderr else str(e)
            print(f"❌ [Wappalyzer] CLI-Fehler (Versuch {attempt}/{max_retries}): {err_msg}")

        if attempt < max_retries:
            print("🔁 [Wappalyzer] Erneuter Versuch...\n")

    print("❌ [Wappalyzer] Alle Versuche fehlgeschlagen.")
    return {"technologies": [], "error": "Keine Technologien erkannt oder Fehler"}


def parse_wappalyzer_result(result: Dict) -> List[Dict]:
    """
    Formatiert die rohe Wappalyzer-Ausgabe für das Scoring/Frontend.

    Liefert:
        [
            {name, version, category, description, website, oss},
            ...
        ]
    """
    parsed: List[Dict] = []
    for tech in result.get("technologies", []):
        categories = tech.get("categories", [{}])
        cat = (categories[0] or {}).get("name")
        parsed.append({
            "name": tech.get("name"),
            "version": tech.get("version"),
            "category": cat,
            "description": tech.get("description"),
            "website": tech.get("website"),
            "oss": tech.get("oss"),
        })
    return parsed
