"""
xml_handler.py
===============================

Dieses Modul dient der Extraktion und Validierung von XML-Dateien
– einzeln oder in ZIP-Archiven – sowie der Erkennung von TEI-Dokumenten.

Funktionen
----------

1) detect_xml_candidates(links)
   Schnelle Heuristik, um aus Linklisten XML-/TEI-/METS-/MODS-/ODD-Kandidaten
   zu extrahieren.

2) analyze_xml_bytes(content)
   Validiert einzelne XML-Dateien (strict parser) und erkennt:
      – Wurzelelement
      – XML-Namespace
      – TEI (verschiedene Varianten)
      – Fehler (HTML, ungültiges XML …)

3) download_and_analyze_xml(session, url)
   Lädt Dateien (XML oder ZIP), analysiert sie und liefert eine einheitliche,
   maschinenlesbare Struktur zurück.
"""

import asyncio
import aiohttp
import zipfile
import io
from urllib.parse import urldefrag
from lxml import etree
from typing import Dict, List, Optional, Any


# ===========================================
# Konfiguration
# ===========================================
MAX_ZIP_MEMBERS = 30           # maximale Anzahl analysierter Dateien pro ZIP
MAX_FILE_SIZE = 10_000_000     # 10 MB Hardlimit pro Datei


# ===========================================
# XML-Kandidatenerkennung
# ===========================================

def detect_xml_candidates(links: List[str], limit: int = 10) -> List[str]:
    """
    Ermittelt URLs, die mit hoher Wahrscheinlichkeit XML/TEI-ähnliche Dateien sind.

    Kriterien:
    - harte Endungen (xml, tei, mods, mets, alto …)
    - weiche Heuristik über Namensfragmente
    """
    print("[XML] Starte Kandidatenerkennung …")
    candidates = []

    for url in links or []:
        if not url:
            continue

        u = url.lower()

        # harte Endungen
        if u.endswith((
            ".xml", ".tei", ".tei.xml", ".odd", ".rng",
            ".xsd", ".dtd", ".mets", ".mods", ".alto", ".foxml"
        )):
            candidates.append(url)
        else:
            # weiche Erkennung (semantische Dateinamen)
            if any(x in u for x in ("tei", "xml", "metadata", "manifest", "record")):
                candidates.append(url)

        if len(candidates) >= limit:
            break

    print(f"[XML] Kandidaten gefunden: {len(candidates)}")
    return candidates


# ===========================================
# XML-Byteanalyse
# ===========================================

def analyze_xml_bytes(
    content: bytes,
    url: str,
    filename: Optional[str] = None,
    zip_member: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analysiert ein XML-Dokument direkt aus Bytes.

    Erkennt:
    - gültiges XML (strict parsing, recover=False)
    - Root-Element
    - Namespace
    - TEI-Dokumente
    - frühe HTML-Erkennung (häufiger Fehlerfall)
    """

    identifier = filename or zip_member or url
    print(f"[XML] Analysiere Datei: {identifier}")

    result = {
        "file": filename,
        "zip_member": zip_member,
        "url": url,
        "is_valid_xml": False,
        "root_element": None,
        "namespace": None,
        "is_tei": False,
        "error": None,
    }

    try:
        # -------------------------
        # 1) HTML früh erkennen
        # -------------------------
        stripped = content.lstrip().lower()

        if (
            stripped.startswith(b"<!doctype html")
            or stripped.startswith(b"<html")
            or b"<html" in stripped[:300]
        ):
            print(f"[XML] HTML erkannt statt XML → {identifier}")
            return {
                **result,
                "root_element": "html",
                "error": "HTML-Dokument – kein XML/TEI",
            }

        # -------------------------
        # 2) Strict XML Parser
        # -------------------------
        parser = etree.XMLParser(
            recover=False,
            resolve_entities=False,
            no_network=True,
        )

        root = etree.fromstring(content, parser=parser)

        # -------------------------
        # 3) Basisinformationen
        # -------------------------
        result["is_valid_xml"] = True
        result["root_element"] = etree.QName(root).localname
        result["namespace"] = etree.QName(root).namespace or None

        # -------------------------
        # 4) TEI-Erkennung (robust)
        # -------------------------
        ns = result["namespace"] or ""
        root_name = (result["root_element"] or "").lower()

        result["is_tei"] = (
            root_name == "tei"
            or "tei" in ns.lower()
            or ns.strip() == "http://www.tei-c.org/ns/1.0"
        )

        print(
            f"[XML] OK: Root=<{result['root_element']}>, "
            f"NS={result['namespace']} | TEI={result['is_tei']}"
        )

    except Exception as e:
        result["error"] = str(e)
        print(f"[XML] Fehler bei {identifier}: {e}")

    return result


# ===========================================
# Download + Analyse
# ===========================================

async def download_and_analyze_xml(
    session: aiohttp.ClientSession,
    url: str,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> Dict[str, Any]:
    """
    Lädt XML- oder ZIP-Dateien herunter und analysiert sie einheitlich.

    Rückgabe:
        {
            "type": "file" | "zip" | "error",
            "url": <str>,
            "count_xml": <int>,
            "entries": [ ... ],
            "error": <str|None>
        }
    """
    url_clean = urldefrag(url)[0]
    print(f"[XML] ↓ Download & Analyse: {url_clean}")

    try:
        async with (semaphore or asyncio.Semaphore(1)):
            async with session.get(url_clean, timeout=12) as resp:
                if resp.status != 200:
                    msg = f"HTTP {resp.status}"
                    print(f"[XML] ❌ {msg} bei {url_clean}")
                    return {
                        "type": "error",
                        "url": url_clean,
                        "entries": [],
                        "count_xml": 0,
                        "error": msg,
                    }

                content = await resp.read()
                ctype = (resp.headers.get("Content-Type") or "").lower()
                fname = url_clean.split("/")[-1] or "download.xml"

                # -------------------------
                # Dateigrößenlimit
                # -------------------------
                if len(content) > MAX_FILE_SIZE:
                    msg = f"Datei zu groß ({len(content)/1_000_000:.1f} MB)"
                    print(f"[XML] ⚠️ {msg}")
                    return {
                        "type": "error",
                        "url": url_clean,
                        "entries": [],
                        "count_xml": 0,
                        "error": msg,
                    }

                # -------------------------
                # ZIP-Datei?
                # -------------------------
                if "zip" in ctype or fname.endswith(".zip"):
                    print("[XML] 🗜 ZIP erkannt → entpacke XML-Dateien …")
                    entries = []

                    try:
                        with zipfile.ZipFile(io.BytesIO(content)) as zf:
                            members = zf.infolist()

                            if len(members) > MAX_ZIP_MEMBERS:
                                print(
                                    f"[XML] ⚠️ ZIP enthält {len(members)} Dateien → "
                                    f"beschränke auf {MAX_ZIP_MEMBERS}"
                                )

                            for m in members[:MAX_ZIP_MEMBERS]:
                                if m.is_dir() or not m.filename.lower().endswith(".xml"):
                                    continue

                                data = zf.read(m)
                                info = analyze_xml_bytes(
                                    data,
                                    url_clean,
                                    filename=m.filename,
                                    zip_member=m.filename,
                                )
                                entries.append(info)

                    except zipfile.BadZipFile:
                        msg = "Ungültiges oder beschädigtes ZIP"
                        print(f"[XML] ❌ {msg}")
                        return {
                            "type": "error",
                            "url": url_clean,
                            "entries": [],
                            "count_xml": 0,
                            "error": msg,
                        }

                    return {
                        "type": "zip",
                        "url": url_clean,
                        "entries": entries,
                        "count_xml": len(entries),
                        "error": None,
                    }

                # -------------------------
                # Einzelne XML-Datei
                # -------------------------
                info = analyze_xml_bytes(content, url_clean, filename=fname)

                return {
                    "type": "file",
                    "url": url_clean,
                    "entries": [info],
                    "count_xml": 1 if info["is_valid_xml"] else 0,
                    "error": info.get("error"),
                }

    except Exception as e:
        msg = str(e)
        print(f"[XML] ❌ Fehler beim Download/Analyse {url_clean}: {msg}")

        return {
            "type": "error",
            "url": url_clean,
            "entries": [],
            "count_xml": 0,
            "error": msg,
        }
