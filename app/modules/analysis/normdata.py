"""
normdata.py
==============================

Dieses Modul erkennt **Normdatenverweise** in digitalen Editionsseiten.
Es durchsucht:

  • eingebettete JSON-LD-Daten
  • sichtbare interne und externe Links

und klassifiziert gefundene URLs gegen bekannte Normdaten-Quellen wie:
GND, VIAF, LCCN, SUDOC, BNCF, Getty ULAN, GeoNames, EU Vocabularies,
Wikidata, BARTOC, DANTE und ORCID.
"""

import json
import re
import html as ihtml
from typing import Any, Dict, List, Optional, Iterable, Tuple
from urllib.parse import urldefrag, urljoin, urlparse


# ============================================================================ #
# 1. Mustererkennung für bekannte Normdatenquellen
# ============================================================================ #

AUTHORITY_PATTERNS = {
    "GND": re.compile(r"https?://(?:www\.)?(?:d-nb\.info|lobid\.org)/gnd/[0-9Xx\-]+", re.I),
    "VIAF": re.compile(r"https?://(?:www\.)?viaf\.org/viaf/[0-9Xx\-]+", re.I),
    "LCCN": re.compile(r"https?://(?:www\.)?lccn\.loc\.gov/[a-z0-9\-]+", re.I),
    "SUDOC": re.compile(r"https?://(?:www\.)?(?:idref\.fr|sudoc\.fr)/[0-9A-Za-z\-]+", re.I),
    "BNCF": re.compile(r"https?://(?:thes|opac)\.bncf\.firenze\.sbn\.it/[^\s\"'>]+", re.I),

    "Getty ULAN": re.compile(r"https?://(?:vocab\.getty\.edu/(?:page/)?ulan/[0-9]+)", re.I),
    "GeoNames": re.compile(r"https?://(?:www\.)?geonames\.org/[0-9]+", re.I),
    "EU Vocabularies": re.compile(
        r"https?://(?:data\.europa\.eu|publications\.europa\.eu)/(?:resource|xsp)/[A-Za-z0-9\-_\/]+",
        re.I
    ),

    "Wikidata": re.compile(r"https?://(?:www\.)?wikidata\.org/(?:entity|wiki)/[A-Za-z0-9]+", re.I),
    "BARTOC": re.compile(r"https?://(?:www\.)?bartoc\.org/[A-Za-z0-9\-/]+", re.I),
    "DANTE": re.compile(r"https?://dante\.gbv\.de/[^\s\"'>]+", re.I),
    "ORCID": re.compile(r"https?://(?:www\.)?orcid\.org/\d{4}-\d{4}-\d{4}-\d{3}[0-9Xx]", re.I),
}



# ============================================================================ #
# 2. Hilfsfunktionen
# ============================================================================ #

def _normalize_url_basic(u: str) -> str:
    """Normalisiert eine URL (Kleinbuchstaben, kein Fragment, kein Slash am Ende)."""
    try:
        p = urlparse(u.strip())
        netloc = p.netloc.lower()
        path = (p.path or "/").rstrip("/")
        return p._replace(netloc=netloc, path=path, fragment="").geturl()
    except Exception:
        return u.strip()


def _classify_authority_url(u: str) -> Optional[str]:
    """Prüft, ob eine URL zu einer bekannten Normdatenquelle gehört."""
    for name, rx in AUTHORITY_PATTERNS.items():
        if rx.search(u):
            print(f"🔎 Normdaten-Treffer ({name}): {u}")
            return name
    return None



# ============================================================================ #
# 3. JSON-LD-Extraktion
# ============================================================================ #

def _urls_from_jsonld(html: Optional[str], base_url: str) -> List[str]:
    print("🔍 Starte JSON-LD-Prüfung …")
    if not html:
        print("⚠️ Kein HTML übergeben — JSON-LD-Suche übersprungen.")
        return []

    print(f"[DEBUG] HTML-Länge: {len(html)}")

    urls: List[str] = []

    json_blocks = re.findall(
        r'<script[^>]*application/ld\+json[^>]*>(.*?)</script\s*>',
        html,
        flags=re.I | re.S
    )
    print(f"📦 Gefundene JSON-LD-Blöcke: {len(json_blocks)}")

    for raw_block in json_blocks:
        try:
            block = ihtml.unescape(raw_block).replace("\\/", "/")
            data = json.loads(block)
            block_text = json.dumps(data, ensure_ascii=False)
        except Exception:
            block_text = raw_block

        found_urls = re.findall(
            r'https?:\\/\\/[^\s"\'<>]+|https?://[^\s"\'<>]+',
            block_text
        )

        print(f"🔗 URLs in JSON-LD-Block: {len(found_urls)}")

        for u in found_urls:
            u = u.replace("\\/", "/")
            final = urljoin(base_url, urldefrag(u)[0])
            urls.append(final)

    # deduplizieren
    out = []
    seen = set()
    for u in urls:
        nu = _normalize_url_basic(u)
        if nu not in seen:
            seen.add(nu)
            out.append(nu)

    print(f"📊 JSON-LD extrahierte URLs (unique): {len(out)}")
    return out



# ============================================================================ #
# 4. Sichtbare Links flatten
# ============================================================================ #

def _flatten_links(links: Optional[Iterable]) -> List[str]:
    flat = []
    for l in links or []:
        if isinstance(l, str):
            flat.append(_normalize_url_basic(urldefrag(l)[0]))
        elif isinstance(l, dict) and isinstance(l.get("url"), str):
            flat.append(_normalize_url_basic(urldefrag(l["url"])[0]))
    print(f"📚 Flattened Links: {len(flat)}")
    return flat



# ============================================================================ #
# 5. Hauptfunktion
# ============================================================================ #

async def collect_normdata(
    base_url: str,
    html: Optional[str] = None,
    links_internal: Optional[Iterable] = None,
    links_external: Optional[Iterable] = None,
    prefer_jsonld: bool = True,
    session: Optional[Any] = None,
) -> Dict[str, Any]:

    print("\n======================")
    print("🔎 Starte Normdaten-Analyse")
    print("======================")

    candidates: List[Tuple[str, str]] = []
    used_sources: set = set()

    # --- JSON-LD ---
    if prefer_jsonld and html:
        jl = _urls_from_jsonld(html, base_url)
        print(f"📦 JSON-LD URLs: {len(jl)}")
        if jl:
            used_sources.add("json-ld")
            candidates.extend((u, "json-ld") for u in jl)

    # --- Links ---
    lk = _flatten_links(links_internal) + _flatten_links(links_external)
    print(f"🔗 Gesamte sichtbare Links: {len(lk)}")
    if lk:
        used_sources.add("links")
        candidates.extend((u, "links") for u in lk)

    print(f"📌 Gesamte Kandidaten vor Filterung: {len(candidates)}")

    # --- Duplikate anhand URL ---
    seen_origin: Dict[str, str] = {}
    for u, origin in candidates:
        if u not in seen_origin:
            seen_origin[u] = origin

    print(f"📌 Kandidaten (unique): {len(seen_origin)}")

    # --- Klassifikation ---
    items: List[Dict[str, Any]] = []
    for u, origin in seen_origin.items():
        src = _classify_authority_url(u)
        if src:
            items.append({"url": u, "source": src, "origin": origin})

    print(f"🏛️ Gefundene Normdaten-Verweise: {len(items)}")

    # --- Zählen ---
    counts: Dict[str, int] = {}
    for it in items:
        counts[it["source"]] = counts.get(it["source"], 0) + 1

    print("📊 Normdaten-Zusammenfassung:", counts)

    return {
        "items": items,
        "counts": counts,
        "total": len(items),
        "_sources": sorted(used_sources) if used_sources else [],
    }
