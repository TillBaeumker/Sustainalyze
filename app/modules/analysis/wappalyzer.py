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
import os
from typing import Optional, Dict, List

# =============================
# KONFIGURATION
# =============================

USE_WAPPALYZER_DOCKER = False   # Docker ist aus
WAPPALYZER_CLI_PATH = "/app/app/wappalyzer/src/drivers/npm/cli.js"

print(f"🔧 [Wappalyzer] Local mode")
print(f"🔧 CLI path: {WAPPALYZER_CLI_PATH}")


# =============================
# LOCAL CLI
# =============================

def _run_wappalyzer_local(url: str, max_retries: int = 3) -> Optional[Dict]:

    cli_path = WAPPALYZER_CLI_PATH

    print(f"🔧 Wappalyzer CLI: {cli_path}")

    if not os.path.isfile(cli_path):
        print(f"❌ CLI fehlt: {cli_path}")
        return {"technologies": [], "error": "CLI fehlt"}

    for attempt in range(1, max_retries + 1):
        print(f"\n🖥️ [Local] Versuch {attempt}/{max_retries}")
        print(f"➡️  URL: {url}")

        try:
            result = subprocess.run(
                ["node", cli_path, url],
                capture_output=True,
                text=True,
                timeout=120,
            )

            print(f"📥 exit code: {result.returncode}")

            if result.stdout:
                print(f"📥 stdout:\n{result.stdout[:500]}")
            else:
                print("⚠️ stdout: leer")

            if result.stderr:
                print(f"📥 stderr:\n{result.stderr[:500]}")
            else:
                print("⚠️ stderr: leer")

            output = result.stdout.strip()

            if not output:
                print("⚠️ stdout leer → wahrscheinlich Puppeteer/Browser Problem")
                continue

            try:
                return json.loads(output)

            except json.JSONDecodeError:
                print("❌ JSON Fehler!")
                print(f"---- RAW OUTPUT BEGIN ----\n{output}\n---- RAW OUTPUT END ----")

        except subprocess.TimeoutExpired:
            print("❌ Timeout")
        except Exception as e:
            print(f"❌ Python Exception: {e}")

    print("❌ kein Erfolg nach allen Versuchen!")
    return {"technologies": [], "error": "lokale Analyse fehlgeschlagen"}


# ============================================================
# ÖFFENTLICHE FUNKTION
# ============================================================

def analyze_technologies_with_wappalyzer(
    url: str,
    max_retries: int = 3,
) -> Optional[Dict]:
    """
    Führt die Technologieanalyse NUR lokal aus.
    """
    return _run_wappalyzer_local(url, max_retries)


# ============================================================
# PARSING
# ============================================================

def parse_wappalyzer_result(result: Dict) -> List[Dict]:
    """
    Formatiert rohe Wappalyzer-Daten in ein einheitliches Format.
    """

    parsed: List[Dict] = []

    for tech in result.get("technologies", []):
        categories = tech.get("categories", [{}])
        category_name = (categories[0] or {}).get("name")

        parsed.append({
            "name": tech.get("name"),
            "version": tech.get("version"),
            "category": category_name,
            "description": tech.get("description"),
            "website": tech.get("website"),
            "oss": tech.get("oss"),
        })

    return parsed
