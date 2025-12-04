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


import subprocess
import json
import os
from typing import Optional, Dict, List

# ============================================================
# KONFIGURATION
# ============================================================

USE_WAPPALYZER_DOCKER = os.getenv("USE_WAPPALYZER_DOCKER", "false").lower() == "true"
WAPPALYZER_CONTAINER = os.getenv("WAPPALYZER_CONTAINER", "wappalyzer")

print(f"🐳 [Wappalyzer] Docker-Modus: {USE_WAPPALYZER_DOCKER}")
print(f"🐳 [Wappalyzer] Container-Name: {WAPPALYZER_CONTAINER}")


# ============================================================
# DOCKER-MODUS
# ============================================================

def _run_wappalyzer_docker(url: str, max_retries: int = 3) -> Optional[Dict]:
    """
    Führt Wappalyzer innerhalb des Docker-Containers aus.
    """
    print(f"🐳 [Wappalyzer] Starte Docker-Analyse für: {url}")

    for attempt in range(1, max_retries + 1):
        print(f"🐳 [Docker] Versuch {attempt}/{max_retries}")

        try:
            result = subprocess.run(
                [
                    "docker", "exec", WAPPALYZER_CONTAINER,
                    "node", "/app/src/drivers/npm/cli.js", url
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            output = result.stdout.strip()

            if not output:
                print("⚠️ [Docker] Leere Ausgabe – erneuter Versuch")
                continue

            try:
                data = json.loads(output)
                print("✅ [Docker] Analyse erfolgreich!")
                return data
            except json.JSONDecodeError:
                print("❌ [Docker] JSON-Parsing fehlgeschlagen!")
                print("RAW OUTPUT:")
                print(output)
                continue

        except subprocess.TimeoutExpired:
            print("❌ [Docker] Timeout")
        except Exception as e:
            print(f"❌ [Docker] Fehler: {e}")

    print("❌ [Docker] Alle Versuche fehlgeschlagen.")
    return {"technologies": [], "error": "Docker-Analyse fehlgeschlagen"}


# ============================================================
# LOKALER FALLBACK (CLI)
# ============================================================

def _run_wappalyzer_local(url: str, max_retries: int = 3) -> Optional[Dict]:
    """
    Fallback: Lokale Wappalyzer-CLI nutzen.
    """

    cli_path = os.getenv("WAPPALYZER_CLI_PATH")

    # Falls kein Pfad gesetzt → automatisch den Projektpfad verwenden
    if not cli_path:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(base_dir, "..", "..", ".."))

        cli_path = os.path.join(
            project_root,
            "wappalyzer",
            "src",
            "drivers",
            "npm",
            "cli.js"
        )

        print(f"⚠️ [Wappalyzer] Nutze relativen CLI-Pfad: {cli_path}")

    if not os.path.isfile(cli_path):
        print(f"❌ Wappalyzer CLI nicht gefunden: {cli_path}")
        return {"technologies": [], "error": "CLI fehlt"}

    for attempt in range(1, max_retries + 1):
        print(f"🖥️ [Local CLI] Versuch {attempt}/{max_retries}")

        try:
            result = subprocess.run(
                ["xvfb-run", "node", cli_path, url],
                capture_output=True,
                text=True,
                check=True,
                timeout=120,
            )

            output = result.stdout.strip()

            if not output:
                print("⚠️ [Local CLI] Leere Ausgabe")
                continue

            try:
                data = json.loads(output)
                print("✅ [Local CLI] Analyse erfolgreich!")
                return data
            except json.JSONDecodeError:
                print("❌ [Local CLI] Ungültiges JSON")
                print(output)

        except subprocess.TimeoutExpired:
            print("❌ [Local CLI] Timeout")
        except subprocess.CalledProcessError as e:
            err = e.stderr.strip() if e.stderr else str(e)
            print(f"❌ [Local CLI] Fehler: {err}")

    print("❌ [Local CLI] Alle Versuche fehlgeschlagen.")
    return {"technologies": [], "error": "Lokale Analyse fehlgeschlagen"}


# ============================================================
# ÖFFENTLICHE FUNKTION
# ============================================================

def analyze_technologies_with_wappalyzer(
    url: str,
    max_retries: int = 3,
) -> Optional[Dict]:
    """
    Führt die Technologieanalyse entweder über Docker oder lokal aus.
    """

    if USE_WAPPALYZER_DOCKER:
        return _run_wappalyzer_docker(url, max_retries)

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
