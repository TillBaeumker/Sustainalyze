"""
download_detector.py
==============================

Erkennung typischer Download-Links (rein heuristisch)
-----------------------------------------------------

Dieses Modul erkennt Links, die mit hoher Wahrscheinlichkeit direkt auf
herunterladbare Dateien verweisen. Die Erkennung erfolgt vollständig
lokal und heuristisch — es werden **keine Netzwerk-Requests** ausgeführt.

Erkennungsmechanismen:
----------------------
1. **Pfad-Endungen**
   Typische Dateiendungen wie .pdf, .zip, .xml, .csv, .tei.xml usw.

2. **Query-Parameter**
   - `file`, `filename` → enthält oft einen Dateinamen
   - `format=json|xml|rdf|ttl|…` → Mapping auf Endungen
   - Flags wie `download=1`, `dl=true`, `attachment=yes`

3. **Heuristische Download-Pfade**
   z. B. `/download/`, `/files/`, `/uc`, `/ndownloader/`
"""
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qsl, unquote

# Bekannte Dateiendungen, die typischerweise Downloads sind
EXT_HINTS = (
    # Dokumente
    ".pdf", ".epub", ".mobi",
    # Archive
    ".zip", ".tar", ".tar.gz", ".tgz", ".7z", ".rar",
    # Tabellen/Daten
    ".csv", ".tsv", ".xlsx", ".xls", ".ods",
    # Structured Data
    ".xml", "xsl", ".tei", ".tei.xml", ".ttl", ".n3", ".yaml", ".yml",
)

# Parameter, die auf Dateinamen oder Formate hinweisen
PARAM_KEYS_WITH_FILENAME = ("file", "filename")
PARAM_KEYS_WITH_FORMAT   = ("format", "ext")
PARAM_KEYS_DOWNLOAD_FLAG = ("download", "dl", "attachment", "export")

# Zuordnung von Formatparametern zu Dateiendungen
_FORMAT_ALIAS = {
    "xml": ".xml",
    "rdf": ".rdf",
    "ttl": ".ttl",
    "json": ".json",
    "jsonl": ".jsonl",
    "ndjson": ".ndjson",
    "geojson": ".geojson",
    "csv": ".csv",
    "tsv": ".tsv",
    "yaml": ".yaml",
    "yml": ".yml",
    "tei": ".tei",  # auch .tei.xml möglich
}


def _path_ext_hit(path_l: str) -> Optional[str]:
    """Prüft, ob der Pfad mit einer bekannten Endung endet."""
    for ext in EXT_HINTS:
        if path_l.endswith(ext):
            return ext
    return None


def _query_ext_hit(qdict: Dict[str, str], path_l: str) -> Optional[str]:
    """
    Prüft Query-Parameter auf Hinweise für Dateiendungen.
    Reihenfolge:
    1) filename/file=...
    2) format=json/xml/...
    3) download-Flags wie dl=1
    """
    # 1) filename=file.ext
    for key in PARAM_KEYS_WITH_FILENAME:
        val = qdict.get(key)
        if not val:
            continue
        vl = val.lower()
        for ext in EXT_HINTS:
            if vl.endswith(ext):
                return ext

    # 2) format=xml|json|rdf ...
    for key in PARAM_KEYS_WITH_FORMAT:
        val = qdict.get(key)
        if not val:
            continue
        fmt = val.lower().lstrip(".")
        if fmt in _FORMAT_ALIAS:
            return _FORMAT_ALIAS[fmt]

    # 3) download-Flags
    for key in PARAM_KEYS_DOWNLOAD_FLAG:
        val = qdict.get(key)
        if not val:
            continue
        if val.lower() in ("1", "true", "yes"):
            # kleine Heuristik für typische Download-URLs
            if any(tok in path_l for tok in ("/download", "/files/", "/ndownloader/", "/uc")):
                return ""  # Download, aber Endung unbekannt

    return None


def detect_downloadables(links: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detektiert Download-Links anhand von Pfad und Query-Parametern.
    Es wird NICHT im Netz nachgefragt, alles ist rein lokal.
    Rückgabeformat:
    {
        "count": <int>,
        "items": [ <Original-Linkdict + {detector, file_ext, filename}> ]
    }
    """
    hits_by_url: Dict[str, Dict[str, Any]] = {}

    for link in links or []:
        raw_url = link.get("url")
        if not raw_url or not isinstance(raw_url, str):
            continue

        url = raw_url.strip()
        p = urlparse(url)
        path = p.path or ""
        path_l = path.lower()

        # Query-Parameter in Kleinbuchstaben für robuste Erkennung
        qdict = {k.lower(): v for k, v in parse_qsl(p.query or "", keep_blank_values=True)}

        # Dateiname aus dem Pfad extrahieren
        filename = unquote(path.split("/")[-1]) if path else None

        # 1) Pfad → mögliche Endung
        ext = _path_ext_hit(path_l)

        # 2) Query-Parameter → mögliche Endung
        if ext is None:
            qext = _query_ext_hit(qdict, path_l)
            if qext is not None:
                ext = qext  # kann "" sein

        if ext is None:
            # Kein Hinweis, weiter
            continue

        # Deduplizierung pro URL
        if url in hits_by_url:
            continue

        enriched = dict(link)
        enriched.setdefault("detector", "ext" if _path_ext_hit(path_l) else "query")
        enriched["file_ext"] = ext or None
        enriched["filename"] = filename or qdict.get("filename") or qdict.get("file")

        hits_by_url[url] = enriched

    items = list(hits_by_url.values())
    return {"count": len(items), "items": items}
