# -*- coding: utf-8 -*-
"""
Heuristische Erkennung FUJI-relevanter Datensatz-Links
------------------------------------------------------
Identifiziert externe Links, die mit hoher Wahrscheinlichkeit auf
FAIR-bewertbare Forschungsdatensätze verweisen (DOI, Handle, ARK, Repositorien).
Maximal 5 Datensätze pro Durchlauf.
"""

import re
from urllib.parse import urlparse

MAX_LINKS = 1000
MAX_DATASETS_PER_RUN = 5

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

PID_PATTERNS = [
    r"doi\.org/10\.\d{4,9}/[A-Za-z0-9._;()/:+-]+",
    r"hdl\.handle\.net/\d+/.+",
    r"ark:/\d+/.+",
]

DATA_API_HINTS = [
    "/oai?verb=Identify",
    "/oai?verb=ListRecords",
    "/sparql",
    "/api/",
    "/metadata",
]


def is_external(url: str, base_domain: str) -> bool:
    parsed = urlparse(url)
    return bool(parsed.netloc and base_domain not in parsed.netloc)


def looks_like_fuji_dataset(url: str) -> bool:
    url_lower = url.lower()

    if any(re.search(pat, url_lower) for pat in PID_PATTERNS):
        return True
    if any(repo in url_lower for repo in FUJI_DATA_REPOS):
        return True
    if any(hint in url_lower for hint in DATA_API_HINTS):
        return True
    return False


def find_fuji_dataset_links(links: list[str], base_domain: str) -> dict:
    """
    Gibt bis zu 5 FUJI-relevante Datensatz-Links zurück.
    Keine Abbrüche, sondern immer ein konsistentes Ergebnis.
    """
    if not links:
        return {"dataset_links": [], "count": 0}

    external_links = [l for l in links if is_external(l, base_domain)]
    if not external_links:
        return {"dataset_links": [], "count": 0}

    if len(external_links) > MAX_LINKS:
        # Nur erste 1000 prüfen, um Performance zu sichern
        external_links = external_links[:MAX_LINKS]

    dataset_links = [l for l in external_links if looks_like_fuji_dataset(l)]

    # Maximal 5 Datensätze pro Durchlauf
    dataset_links = dataset_links[:MAX_DATASETS_PER_RUN]

    return {
        "dataset_links": dataset_links,
        "count": len(dataset_links),
    }
