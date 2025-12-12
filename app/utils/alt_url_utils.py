# file: app/utils/löschen_url_utils.py
# -*- coding: utf-8 -*-
from urllib.parse import urlparse, urlunparse, urldefrag
import re


def is_http_url(u: str) -> bool:
    """Prüft, ob eine URL ein valider HTTP/HTTPS-Link ist."""
    try:
        p = urlparse(u)
        return p.scheme in ("http", "https")
    except Exception:
        return False


def normalize_url(u: str) -> str:
    """
    Normalisiert eine URL:
      - Entfernt Fragmente (#...)
      - Beibehaltung von Query-Parametern
      - Hostname in lowercase
      - Wenn kein Pfad vorhanden → "/"
    """
    if not u:
        return ""
    try:
        p = urlparse(u)
        scheme = (p.scheme or "http").lower()
        netloc = (p.netloc or "").lower()
        path = p.path or "/"
        new = (scheme, netloc, path, "", p.query, "")
        return urlunparse(new)
    except Exception:
        return (u or "").strip()


def is_nested_html_path(u: str) -> bool:
    """Erkennt verschachtelte HTML-Pfade, die fast immer unnötig sind (z. B. index.html/...)."""
    if not u:
        return False
    low = u.lower()
    return "index.html/" in low or re.search(r"\.html/.+\.html", low) is not None


def is_quatsch_link(u: str) -> bool:
    """
    Filtert Links, die komplett unsinnig oder für die Analyse irrelevant sind.
    Diese Links tauchen NICHT in den Link-Listen auf und werden auch nicht geprüft.
    """
    if not u:
        return True

    low = u.lower().strip()

    # Schemata, die wir grundsätzlich ignorieren
    if low.startswith(("javascript:", "mailto:", "tel:", "data:")):
        return True

    # Offensichtlich irrelevante Dateitypen (keine inhaltliche Relevanz für Editionen)
    BAD_EXTENSIONS = (
        ".css", ".js", ".ico", ".png", ".jpg", ".jpeg", ".gif", ".svg",
        ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".webm", ".avi", ".mov",
        ".mp3", ".wav", ".ogg"
    )
    if any(low.endswith(ext) for ext in BAD_EXTENSIONS):
        return True

    return False


def is_ignored_for_analysis(u: str) -> bool:
    """
    Ermittelt Links, die zwar in den Link-Listen angezeigt werden sollen,
    aber NICHT in Link-Checker oder XML-Check einfließen.
    Beispiele: TEI-Viewer-/Paging-Links oder Thumbnail/Zoom-Ressourcen.
    """
    if not u:
        return False
    low = u.lower()
    return any(x in low for x in ["mode=p_", "mod=", "viewer", "zoom", "thumb"])


def normalize_links(links) -> list[dict]:
    """
    Nimmt Liste von Strings oder Dicts und liefert Liste von Dicts:
      [{"url": "<normalisierte URL>", ...}, ...] (Duplikate entfernt).
    Unsinnige Links (is_quatsch_link) werden komplett ignoriert.
    """
    out: list[dict] = []
    seen: set[str] = set()
    for item in (links or []):
        if isinstance(item, dict):
            raw = item.get("url") or item.get("href") or item.get("link") or ""
        else:
            raw = str(item or "").strip()

        u = normalize_url(raw)
        if not u or not is_http_url(u):
            continue
        if u in seen:
            continue
        if is_quatsch_link(u):
            continue

        seen.add(u)
        if isinstance(item, dict):
            rec = dict(item)
            rec["url"] = u
        else:
            rec = {"url": u}
        out.append(rec)
    return out


def normalize_strlist(values) -> list[str]:
    """Normalisiert eine Liste von Strings: Whitespace trimmen, Duplikate entfernen, Leere rauswerfen."""
    out, seen = [], set()
    for v in (values or []):
        if v is None:
            continue
        s = str(v).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


