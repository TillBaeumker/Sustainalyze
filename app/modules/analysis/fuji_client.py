
"""
fuji_client.py
==============================

FUJI-Integration für automatische FAIR-Bewertungen
--------------------------------------------------

Dieses Modul erkennt potenziell relevante Forschungsdatensätze auf Webseiten
(z. B. DOI-/Handle-/ARK-Links, Repository-Domains wie *Zenodo* oder *Figshare*)
und führt anschließend eine vollständige FAIR-Bewertung über einen externen
FUJI-Server aus.

Zentrale Komponenten:
---------------------
1) **Heuristik zur Datensatz-Erkennung**
   - Erkennung persistenter Identifikatoren (DOI, Handle, ARK)
   - Erkennung typischer Datenrepositorien
   - API-basierte Hinweise (OAI-PMH, SPARQL, Metadaten-Endpunkte)

2) **FUJI API-Anbindung**
   - POST-Request an den FUJI-Server
   - Auffällig viele Debug-Ausgaben (bewusst ausführlich)
   - Robuste Fehlerbehandlung für Netzwerk-, Auth- oder JSON-Probleme

3) **Ergebnisverarbeitung**
   - Prüfung, ob FUJI den Link als echten Datensatz bewertet
   - Extraktion und Labeling der FAIR-Metriken (z. B. F1, R1.1, I2)
   - Aufbereitung für die spätere Anzeige im Gesamtreport
"""

import aiohttp
import traceback
import re
from urllib.parse import urlparse
from app.core.config import settings

# ============================================================
# FUJI-KONFIGURATION
# ============================================================

# Die FUJI-Serverdaten stammen aus .env (über config.py)
FUJI_HOST = settings.FUJI_HOST
FUJI_USERNAME = settings.FUJI_USERNAME
FUJI_PASSWORD = settings.FUJI_PASSWORD

# Timeout für HTTP-Anfragen
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=60)

print("🟦 [FUJI] Modul geladen")

# Warnungen, falls die FUJI-Konfiguration unvollständig ist
if not FUJI_HOST:
    print("❌ [FUJI] WARNUNG: FUJI_HOST ist leer oder None!")
elif not FUJI_HOST.startswith("http"):
    print("❌ [FUJI] WARNUNG: FUJI_HOST beginnt nicht mit http/https!")


# ============================================================
# Metrik-Namen für schönere Labels
# ============================================================

METRIC_LABELS = {
    "A": "Accessibility",
    "A1": "Access Level Information",
    "F": "Findability (gesamt)",
    "F1": "Global Identifier",
    "F2": "Descriptive Metadata",
    "F3": "Data Identifier in Metadata",
    "F4": "Metadata Machine-readable",
    "FAIR": "FAIR Overall Score",
    "I": "Interoperability (gesamt)",
    "I1": "Formal Representation",
    "I2": "Semantic Resources",
    "I3": "Related Resources",
    "R": "Reusability (gesamt)",
    "R1": "Data Content Description",
    "R1.1": "License Information",
    "R1.2": "Provenance Metadata",
    "R1.3": "Community Standards",
}

print("🟦 [FUJI] Metric Labels geladen.")


# ============================================================
# HEURISTIKEN ZUR DATENSATZ-ERKENNUNG
# ============================================================

MAX_LINKS = 1000
MAX_DATASETS_PER_RUN = 5

# Domains, die häufig Forschungsdaten enthalten
FUJI_DATA_REPOS = [
    "zenodo.org",
    "figshare.com",
    "dataverse.org",
    "openaire.eu",
    "pangaea.de",
    "b2share.eudat.eu",
    "dryad.org",
    "data.bnf.fr",
    "hdl.handle.net",
    "doi.org",
    "api.datacite.org",
    "clarin.eu",
    "dariah.eu",
]

# Regex-Muster für DOI, Handle, ARK
PID_PATTERNS = [
    r"doi\.org/10\.\d{4,9}/[A-Za-z0-9._;()/:+-]+",
    r"hdl\.handle\.net/\d+/.+",
    r"ark:/\d+/.+",
]

# Hinweise auf Daten-APIs
DATA_API_HINTS = [
    "/oai?verb=Identify",
    "/oai?verb=ListRecords",
    "/sparql",
    "/api/",
    "/metadata",
]


def is_external(url: str, base_domain: str) -> bool:
    """Prüft, ob der Link außerhalb der aktuellen Domain liegt."""
    parsed = urlparse(url)
    ext = bool(parsed.netloc and base_domain not in parsed.netloc)
    print(f"🔍 [FUJI] Prüfe extern: {url} → {ext}")
    return ext


def looks_like_fuji_dataset(url: str) -> bool:
    """Heuristik: Erkenne mögliche Datensatz-Links anhand PID-Muster und bekannten Repos."""
    url_lower = url.lower()

    # 1) PID-Erkennung
    if any(re.search(pat, url_lower) for pat in PID_PATTERNS):
        print(f"🧬 [FUJI] PID erkannt in: {url}")
        return True

    # 2) Repository-Domain
    if any(repo in url_lower for repo in FUJI_DATA_REPOS):
        print(f"🧬 [FUJI] Repository-Domain erkannt in: {url}")
        return True

    # 3) API-Hinweise
    if any(hint in url_lower for hint in DATA_API_HINTS):
        print(f"🧬 [FUJI] API-Hint erkannt in: {url}")
        return True

    return False


def find_fuji_dataset_links(links: list[str], base_domain: str) -> dict:
    """Filtert Links der Seite nach potenziellen Forschungsdatensätzen."""
    print("🔎 [FUJI] --- STARTE Dataset-Link-Erkennung ---")
    print(f"🔎 Anzahl aller Links: {len(links)}")
    print(f"🔎 Basisdomain: {base_domain}")

    if not links:
        print("⚠️ [FUJI] Keine Links vorhanden.")
        return {"dataset_links": [], "count": 0}

    # Schritt 1: externe Links herausfiltern
    external_links = [l for l in links if is_external(l, base_domain)]
    print(f"🌍 Externe Links: {len(external_links)}")

    # Sicherheitsschnitt
    if len(external_links) > MAX_LINKS:
        print("⚠️ [FUJI] Externe Links wurden gekürzt.")
        external_links = external_links[:MAX_LINKS]

    # Schritt 2: Heuristiken anwenden
    dataset_links = [l for l in external_links if looks_like_fuji_dataset(l)]
    print(f"🧬 Gefundene FUJI-relevante Datensatz-Links: {dataset_links}")

    dataset_links = dataset_links[:MAX_DATASETS_PER_RUN]
    print(f"✔️ Final berücksichtigt: {dataset_links}")

    return {
        "dataset_links": dataset_links,
        "count": len(dataset_links),
    }


# ============================================================
# FUJI API-ANBINDUNG (mit maximalem Debug)
# ============================================================

async def test_with_fuji(url: str) -> dict:
    """Führt eine FUJI-Bewertung für die übergebene URL aus."""
    api_url = f"{FUJI_HOST}/v1/evaluate"
    payload = {"object_identifier": url}

    print("=======================================================")
    print(f"➡️ [FUJI] Starte Anfrage für: {url}")
    print(f"🌐 [FUJI] API-URL: {api_url}")
    print(f"🔑 [FUJI] Benutzername: {FUJI_USERNAME!r}")
    print(f"📦 [FUJI] Payload: {payload}")
    print("=======================================================")

    if not FUJI_HOST or not FUJI_HOST.startswith("http"):
        print("❌ [FUJI] Ungültiger FUJI_HOST – Abbruch.")
        return {"url": url, "error": "Ungültiger FUJI_HOST"}

    try:
        async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
            print("🔄 [FUJI] Sende HTTP POST...")

            async with session.post(
                api_url,
                json=payload,
                auth=aiohttp.BasicAuth(FUJI_USERNAME, FUJI_PASSWORD),
            ) as response:

                print(f"🔁 [FUJI] HTTP Status: {response.status}")
                print(f"📄 [FUJI] Response-Header: {dict(response.headers)}")

                text_preview = (await response.text())[:500]
                print(f"📜 [FUJI] Response-Vorschau:\n{text_preview}")

                # Erfolgreicher Fall
                if response.status == 200:
                    print(f"✅ [FUJI] Analyse erfolgreich für {url}")
                    try:
                        return await response.json()
                    except Exception:
                        print("❌ [FUJI] JSON Parsing fehlgeschlagen.")
                        traceback.print_exc()
                        return {"url": url, "error": "JSON Parsing Error"}

                # Fehlerfall
                print(f"❌ [FUJI] Fehlerstatus {response.status} für {url}")
                return {"url": url, "error": f"FUJI Fehler {response.status}: {text_preview}"}

    except Exception as e:
        print("❌ [FUJI] Ausnahme in test_with_fuji():")
        traceback.print_exc()
        return {"url": url, "error": str(e)}


# ============================================================
# RESULTATSVERARBEITUNG
# ============================================================

def check_is_dataset(fuji_result: dict) -> bool:
    """Prüft, ob FUJI den Link als Datensatz bewertet."""
    print("🔍 [FUJI] Prüfe Dataset-Validität…")

    if not fuji_result:
        print("⚠️ [FUJI] Leeres Resultat.")
        return False

    msg = str(fuji_result).lower()
    if "not identify itself" in msg:
        print("🚫 [FUJI] Kein Datensatz laut FUJI.")
        return False

    score = fuji_result.get("fairness_score", 0)
    print(f"🎯 [FUJI] FAIRness Score laut FUJI: {score}")

    return score > 0


def extract_fuji_summary(fuji_result: dict) -> dict:
    """Extrahiert FAIR-Summary und sortiert die Metriken."""
    print("📝 [FUJI] Extrahiere Summary…")

    if not fuji_result:
        print("⚠️ [FUJI] Keine Summary extrahierbar.")
        return None

    summary = fuji_result.get("summary", {}) or {}
    score_percent = summary.get("score_percent", {}) or {}

    labeled_metrics = [
        {
            "code": code,
            "label": METRIC_LABELS.get(code, code),
            "score": value,
            "low_score": (value is not None and value < 50),
        }
        for code, value in score_percent.items()
    ]

    fair_score = score_percent.get("FAIR") or fuji_result.get("fairness_score")

    print(f"🧮 [FUJI] FAIR Score extrahiert: {fair_score}")

    return {
        "fair_score": fair_score,
        "maturity": summary.get("maturity", {}).get("FAIR"),
        "score_percent": score_percent,
        "metrics_labeled": labeled_metrics,
        "missing_elements": summary.get("missing_elements", {}),
        "fuji_version": fuji_result.get("version"),
        "metrics_count": len(fuji_result.get("results", [])),
        "raw_fuji_json": fuji_result,
    }


async def run_fuji_for_dataset(url: str, semaphore) -> dict:
    """Führt FUJI-Bewertung aus und sammelt die Ergebnisdaten."""
    print(f"🚦 [FUJI] Warte auf Semaphore für {url}…")

    async with semaphore:
        print(f"🔓 [FUJI] Semaphore erhalten → Starte FUJI für {url}")

        fuji_res = await test_with_fuji(url)
        dataset_flag = check_is_dataset(fuji_res)
        fuji_summary = extract_fuji_summary(fuji_res)

        print(
            f"✅ [FUJI] Abschluss für {url} | "
            f"Dataset={dataset_flag} | "
            f"Score={fuji_summary.get('fair_score') if fuji_summary else None}"
        )

        return {
            "url": url,
            "is_dataset": dataset_flag,
            "fuji_summary": fuji_summary,
        }


def process_fuji_summaries(page_data: list):
    """Bereitet die FUJI-Informationen für alle analysierten Seiten auf."""
    print("🗂️ [FUJI] Verarbeite FUJI-Summaries für alle Seiten …")

    dataset_links_all = []

    for page in page_data:
        print(f"📄 [FUJI] Seite: {page.get('url')}")

        for ds in page.get("dataset_links", []):
            print(f"   🔗 Dataset-Link: {ds.get('url')}")

            fuji_raw = ds.get("fuji_raw")
            fuji_summary = extract_fuji_summary(fuji_raw) if fuji_raw else None

            dataset_links_all.append({
                "url": ds.get("url"),
                "is_dataset": ds.get("is_dataset", False),
                "fuji_summary": fuji_summary,
            })

    print(f"📦 [FUJI] Gesamtzahl Datensätze: {len(dataset_links_all)}")

    return page_data, dataset_links_all
