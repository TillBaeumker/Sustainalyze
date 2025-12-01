
"""
detect_persistent_identifiers.py
================================

Erkennung persistenter Identifier (PIDs)
----------------------------------------

Dieses Modul erkennt persistente Identifier (PIDs) in URLs anhand
valider regulärer Ausdrücke nach gängigen Standards (z. B. DOI Foundation,
Handle System, ARK Alliance, ORCID, arXiv). Die Heuristik richtet sich an
praktische Forschungsdaten-Workflows (CLARIN, OpenAIRE, DH-Projekte).

Unterstützte Typen:
-------------------
• DOI
• Handle
• ARK
• URN (inkl. strukturierten Varianten wie CTS-URNs)
• ORCID
• arXiv

"""

import re
from typing import Optional, Dict

# Satzzeichen, die oft am Ende von DOI/URN/Handle stehen
_TRAIL_PUNCT = '.,);:]»«"“”\'\u00A0 '

# Reguläre Ausdrücke für verschiedene PID-Systeme
_PATTERNS = [

    # DOI – weit verbreitet in Wissenschaft
    ("doi", re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)\s*(10\.\d{4,9}/\S+)$", re.I)),

    # Handle – Basis für DOI
    ("handle", re.compile(r"^https?://hdl\.handle\.net/(\S+)$", re.I)),

    # ARK – häufig in Archiven/Bibliotheken
    ("ark", re.compile(r"^https?://(?:n2t\.net|ark\.cdlib\.org)/ark:/\d+/\S+$", re.I)),

    # URN – z. B. CTS-URNs in Editionen
    ("urn", re.compile(r"^urn:[a-z0-9][a-z0-9-]*:[\w\-.:/]+$", re.I)),

    # ORCID – Personenidentifikator
    ("orcid", re.compile(r"^https?://orcid\.org/\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", re.I)),

    # arXiv – Preprint-Identifier
    ("arxiv", re.compile(r"^https?://arxiv\.org/(?:abs|pdf)/\d{4}\.\d{4,5}(?:v\d+)?(?:\.pdf)?$", re.I)),
]

# -------------------------------------------------------
# Hilfsfunktionen
# -------------------------------------------------------

def _log(msg: str, verbose: bool):
    """Optionales Debug-Logging."""
    if verbose:
        print(msg)


def _strip_trailing(s: str) -> str:
    """Entfernt störende Satzzeichen am Ende eines möglichen Identifiers."""
    return s.rstrip(_TRAIL_PUNCT)


# -------------------------------------------------------
# Hauptfunktion zur PID-Erkennung
# -------------------------------------------------------

def detect_persistent_id(url: str, *, verbose: bool = False) -> Optional[Dict[str, str]]:
    """
    Erkennt persistente Identifier (DOI, Handle, ARK, URN, ORCID, arXiv).

    Rückgabe:
        {
            "type": PID-Typ (str),
            "normalized": normalisierte URL,
            "persistent": True/False
        }

    Beispiel:
        detect_persistent_id("https://doi.org/10.1000/xyz123")
    """

    # Eingabe muss String sein
    if not isinstance(url, str):
        _log("[PID] Ungültiger Typ (kein String).", verbose)
        return None

    original = url
    u = _strip_trailing(url.strip())

    if u != original:
        _log(f"[PID] Bereinigt: '{original}' → '{u}'", verbose)
    else:
        _log(f"[PID] Prüfe: {u}", verbose)

    # Prüfen auf Matches in den PID-Mustern
    for name, pat in _PATTERNS:
        m = pat.match(u)
        if not m:
            _log(f"[PID] Kein Treffer für {name.upper()}", verbose)
            continue

        # Normalisierung für konsistente Weiterverarbeitung
        if name == "doi":
            norm = f"https://doi.org/{m.group(1)}"
        elif name in {"handle", "ark", "arxiv"}:
            norm = u
        elif name in {"urn", "orcid"}:
            norm = u.lower()
        else:
            norm = u

        # URI wäre nicht persistent, alle anderen schon
        persistent = name != "uri"

        _log(f"[PID] Erkannt: {name.upper()} → {norm}", verbose)
        return {"type": name, "normalized": norm, "persistent": persistent}

    _log("[PID] Keine persistente ID erkannt.", verbose)
    return None
