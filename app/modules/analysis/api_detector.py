"""
api_detector.py
==============================

Automatische Erkennung von Web-APIs
-----------------------------------

Dieses Modul identifiziert typische API-Endpunkte auf Webseiten und prüft sie
über Live-Requests. Unterstützte API-Typen:

• OAI-PMH
• IIIF (Info API + Image API Heuristik)
• REST (JSON-basierte Endpunkte)

Ziele:
------
- Klassifizierung einzelner Links (classify_links_min)
- Hostweites Probing typischer API-Pfade (probe_host_min)
- Strukturierte Evidenz pro API-Typ
- Ausführliche Debug-Ausgabe zur Nachvollziehbarkeit

Merkmale:
---------
- Robuste Erkennung anhand typischer URL-Fragmente
- Validierung durch content-type, HTTP-Status, JSON/XML-Prüfung
- Trennung zwischen Link-Klassifikation und Host-Scanning
- Vollständig asynchron und mit konfigurierbaren Timeouts

"""

import asyncio
from typing import List, Dict, Any, Tuple, Optional, Union
from urllib.parse import urlsplit, urlunsplit
import httpx


# ============================================================================
# SETTINGS
# ============================================================================

MAX_PROBES = 10
TIMEOUT = 6.0
CONCURRENCY = 10
MAX_BODY = 50000

HEADERS = {
    "Accept": (
        "application/json, application/ld+json;q=0.9, application/xml;q=0.9, "
        "text/html;q=0.5, */*;q=0.1"
    ),
    "User-Agent": "api-detector/4.1"
}

API_SIGNATURES = {
    "OAI-PMH": {"path_fragments": ["oai", "oai-pmh"]},
    "IIIF": {"path_fragments": ["iiif"]},
    "REST": {"path_fragments": ["api", "rest", "v1", "v2"]},
}


# ============================================================================
# LOGGING
# ============================================================================

def _log(tag: str, msg: str):
    print(f"[API-DET:{tag}] {msg}")


# ============================================================================
# HELPERS
# ============================================================================

def _ct(ctype: Optional[str]) -> str:
    return (ctype or "").split(";")[0].strip().lower()


def _base(url: str) -> str:
    s = urlsplit(url)
    return urlunsplit((s.scheme, s.netloc, "", "", ""))


def _as_item(x: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {"url": str(x)}


def _looks_api_candidate(url: str) -> bool:
    ul = (url or "").lower()
    return any(
        frag in ul
        for sig in API_SIGNATURES.values()
        for frag in sig["path_fragments"]
    )


# ============================================================================
# VALIDIERUNGEN
# ============================================================================

async def _validate_oai(client: httpx.AsyncClient, url: str) -> Tuple[bool, List[str]]:
    evidence = []
    test_url = f"{url}?verb=Identify"
    _log("OAI", f"Validate OAI-PMH via Identify: {test_url}")

    try:
        r = await client.get(test_url, headers=HEADERS, timeout=TIMEOUT)
    except Exception as e:
        _log("OAI", f"Request failed: {e}")
        return False, evidence

    ct = _ct(r.headers.get("content-type", ""))
    evidence.append(f"HTTP {r.status_code}")
    evidence.append(f"CT {ct}")

    if ct not in ("application/xml", "text/xml"):
        _log("OAI", f"Wrong content-type: {ct}")
        return False, evidence

    t = (r.text or "").lower()
    if "<oai-pmh" in t or "<identify" in t:
        evidence.append("Body has OAI markers")
        _log("OAI", "Identify OK. OAI-PMH confirmed.")
        return True, evidence

    _log("OAI", "No OAI markers in body.")
    return False, evidence


async def _validate_iiif(client: httpx.AsyncClient, url: str) -> Tuple[bool, List[str]]:
    evidence = []
    ul = (url or "").lower()
    _log("IIIF", f"Validate IIIF candidate: {url}")

    # 1) Info API check
    info_url = url.rstrip("/") + "/info.json"
    _log("IIIF", f"Try info.json: {info_url}")

    try:
        r_info = await client.get(info_url, headers=HEADERS, timeout=TIMEOUT)
        evidence.append(f"info.json HTTP {r_info.status_code}")
        if r_info.status_code == 200:
            t = (r_info.text or "").lower()
            if "@context" in t and "iiif" in t:
                evidence.append("info.json has IIIF context")
                _log("IIIF", "Info API OK. IIIF confirmed.")
                return True, evidence
            else:
                _log("IIIF", "info.json lacks IIIF markers.")
        else:
            _log("IIIF", f"info.json not 200: {r_info.status_code}")
    except Exception as e:
        _log("IIIF", f"info.json request failed: {e}")

    # 2) Image API heuristic
    _log("IIIF", f"Try image URL itself: {url}")
    try:
        r_img = await client.get(url, headers=HEADERS, timeout=TIMEOUT)
        ct = _ct(r_img.headers.get("content-type", ""))
        evidence.append(f"img HTTP {r_img.status_code}")
        evidence.append(f"img CT {ct}")

        if ct in ("image/jpeg", "image/jpg", "image/png", "image/webp"):
            # IIIF Image API typical segments
            if any(k in ul for k in ["full", "pct:", "default", "/0/"]):
                evidence.append("Image URL looks like IIIF Image API")
                _log("IIIF", "Image API pattern OK. IIIF confirmed.")
                return True, evidence
            else:
                _log("IIIF", "Image CT ok but URL pattern weak.")
        else:
            _log("IIIF", f"Not an image content-type: {ct}")
    except Exception as e:
        _log("IIIF", f"Image request failed: {e}")

    return False, evidence


async def _validate_rest(client: httpx.AsyncClient, url: str) -> Tuple[bool, List[str]]:
    evidence = []
    _log("REST", f"Validate REST candidate: {url}")

    try:
        r = await client.get(url, headers=HEADERS, timeout=TIMEOUT)
    except Exception as e:
        _log("REST", f"Request failed: {e}")
        return False, evidence

    ct = _ct(r.headers.get("content-type", ""))
    evidence.append(f"HTTP {r.status_code}")
    evidence.append(f"CT {ct}")

    if not (200 <= r.status_code < 300):
        _log("REST", f"Status not OK: {r.status_code}")
        return False, evidence

    try:
        r.json()
        evidence.append("JSON parse ok")
        _log("REST", "JSON OK. REST confirmed.")
        return True, evidence
    except Exception:
        _log("REST", "No JSON parse possible.")
        return False, evidence


# ============================================================================
# REQUEST WRAPPER
# ============================================================================

async def _fetch(client: httpx.AsyncClient, url: str):
    _log("HTTP", f"GET {url}")
    try:
        r = await client.get(url, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
    except Exception as e:
        _log("HTTP", f"GET failed for {url}. Error: {e}")
        return None

    ct = r.headers.get("content-type", "")
    text = None
    jobj = None

    try:
        jobj = r.json()
    except Exception:
        try:
            text = (r.text or "")[:MAX_BODY]
        except Exception:
            text = ""

    _log("HTTP", f"Response {r.status_code} CT={_ct(ct)} Final={str(r.url)}")
    return (r.status_code, ct, text, jobj, str(r.url))


# ============================================================================
# KLASSIFIKATION EINZELNER LINKS
# ============================================================================

async def classify_links_min(links: Optional[List[Union[str, Dict[str, Any]]]] = None):
    if links is None:
        links = []

    _log("LINKS", f"Start link classification. Links total: {len(links)}")

    annotated: List[Dict[str, Any]] = []
    hits: List[Dict[str, Any]] = []
    tasks = []
    idx = {}

    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=CONCURRENCY)
    ) as client:

        for i, raw in enumerate(links):
            ln = _as_item(raw)
            url = ln.get("url") or ""
            if _looks_api_candidate(url):
                _log("LINKS", f"Candidate {i}: {url}")
                tasks.append(_fetch(client, url))
                idx[len(tasks) - 1] = i
            else:
                ln.update({"is_api": False, "api_type": None})
                annotated.append(ln)

        _log("LINKS", f"Candidates to validate: {len(tasks)}")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for k, res in enumerate(results):
            ln = _as_item(links[idx[k]])

            if isinstance(res, Exception) or not res:
                _log("LINKS", f"Candidate failed: {ln.get('url')}")
                ln.update({"is_api": False, "api_type": None})
                annotated.append(ln)
                continue

            status, ctype, text, jobj, final_url = res
            ul = final_url.lower()

            # OAI-PMH
            if "oai" in ul or "oai-pmh" in ul:
                ok, evidence = await _validate_oai(client, final_url)
                if ok:
                    _log("LINKS", f"OAI-PMH hit: {final_url}")
                    ln.update({
                        "is_api": True,
                        "api_type": "OAI-PMH",
                        "api_url": final_url,
                        "api_evidence": evidence
                    })
                    hits.append({"type": "OAI-PMH", "url": final_url, "evidence": evidence})
                    annotated.append(ln)
                    continue

            # IIIF
            if "iiif" in ul:
                ok, evidence = await _validate_iiif(client, final_url)
                if ok:
                    _log("LINKS", f"IIIF hit: {final_url}")
                    ln.update({
                        "is_api": True,
                        "api_type": "IIIF",
                        "api_url": final_url,
                        "api_evidence": evidence
                    })
                    hits.append({"type": "IIIF", "url": final_url, "evidence": evidence})
                    annotated.append(ln)
                    continue

            # REST
            if any(x in ul for x in ["/api", "/rest", "/v1", "/v2"]):
                ok, evidence = await _validate_rest(client, final_url)
                if ok:
                    _log("LINKS", f"REST hit: {final_url}")
                    ln.update({
                        "is_api": True,
                        "api_type": "REST",
                        "api_url": final_url,
                        "api_evidence": evidence
                    })
                    hits.append({"type": "REST", "url": final_url, "evidence": evidence})
                    annotated.append(ln)
                    continue

            _log("LINKS", f"Not confirmed: {final_url}")
            ln.update({"is_api": False, "api_type": None})
            annotated.append(ln)

    _log("LINKS", f"Done. Hits total: {len(hits)}")
    return annotated, hits


# ============================================================================
# HOSTWEITES PROBING
# ============================================================================

async def probe_host_min(start_url: str):
    base = _base(start_url.rstrip("/"))
    _log("PROBE", f"Start host probing. Base: {base}")

    candidates = []
    for api, conf in API_SIGNATURES.items():
        for frag in conf["path_fragments"][:MAX_PROBES]:
            url = f"{base}/{frag}"
            candidates.append((api, url))

    _log("PROBE", f"Probe candidates: {len(candidates)}")
    hits: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=CONCURRENCY)
    ) as client:

        # nacheinander für klare Logs
        for api, url in candidates:
            _log("PROBE", f"Test {api} candidate: {url}")

            if api == "OAI-PMH":
                ok, evidence = await _validate_oai(client, url)
                if ok:
                    hits.append({"type": "OAI-PMH", "url": url, "evidence": evidence})
                    _log("PROBE", f"OAI-PMH confirmed: {url}")
                continue

            if api == "IIIF":
                ok, evidence = await _validate_iiif(client, url)
                if ok:
                    hits.append({"type": "IIIF", "url": url, "evidence": evidence})
                    _log("PROBE", f"IIIF confirmed: {url}")
                continue

            if api == "REST":
                ok, evidence = await _validate_rest(client, url)
                if ok:
                    hits.append({"type": "REST", "url": url, "evidence": evidence})
                    _log("PROBE", f"REST confirmed: {url}")
                continue

    _log("PROBE", f"Done. Host hits total: {len(hits)}")
    return hits
