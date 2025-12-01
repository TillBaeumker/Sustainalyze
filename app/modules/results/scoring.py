"""
scoring.py – Bewertung digitaler Editionen
==========================================

Dieses Modul fasst sämtliche Bewertungsfunktionen zusammen, mit die festgelegten Nachhaltigkeitindikatoren beurteilt werden.
Die Scoring-Methodik folgt den in der Arbeit definierten Indikatorengruppen und kombiniert technische
Evidenzen (Crawling, Wappalyzer, Shodan, FAIR-Checker, Repository-Daten) mit textuellen und semantischen Hinweisen aus der LLM-basierten Analyse.

Aufgaben des Moduls
-------------------
1. Berechnung einzelner Indikatoren:
   - Nutzung offener oder proprietärer Technologien
   - Hinweise auf isolierte Ausführungsumgebungen (Container/VM)
   - statische vs. dynamische Webarchitektur
   - strukturierte Metadaten und kontrollierte Vokabulare
   - Normdaten und persistente Identifier
   - API-Schnittstellen
   - Repository-Praxis (GitHub/GitLab)
   - TEI/XML-Präsenz
   - Downloads und technische Artefakte
   - institutionelle und organisatorische Angaben (LLM-basiert)
   - Link-Funktionalität

2. Zusammenführen der Ergebnisse in einem normalisierten Format
   zur späteren Anzeige im Frontend und zur Erstellung eines
   Gesamt-Scores (ohne FAIR, die separat ausgewertet werden).

3. Bereitstellung generischer Hilfsfunktionen:
   - Textnormalisierung und Keyword-Matching
   - Gewichtete Score-Berechnung
   - Formatierung einheitlicher Hinweisblöcke
   - Zusammenführung semantischer LLM-Hinweise

Struktur des Moduls
-------------------
- Utility-Funktionen (Normalisierung, Gewichtung, String-Matching)
- Scoring-Funktionen für technische und semantische Indikatoren
- Spezifische Bewertungen für FAIR
- Zusammenführung in einem Gesamtscore via `compute_scoring()`

Einsatzkontext
--------------
Das Modul wird von der zentralen Analyselogik des Systems
(`handle_analysis()` und der Aggregator-Komponente) aufgerufen und
liefert strukturierte Bewertungsdaten, die direkt im HTML-Frontend
ausgegeben oder für spätere Analysen gespeichert werden können.

Die Implementierung ist modular gehalten, sodass einzelne
Bewertungsfunktionen getrennt getestet, erweitert oder ersetzt werden
können, ohne dass der Gesamtprozess verändert werden muss.
"""

from __future__ import annotations

from app.modules.results.heuristics import (
    STATIC_SITE_GENERATORS,
    STATIC_HOST_PLATFORMS,
    DYNAMIC_FRAMEWORKS,
    CMS_RUNTIME,
    ISO_STRONG
)

# ============================================================
# Hilfsfunktionen (Utilities)
# ============================================================
"""
Die folgenden Funktionen stellen modulübergreifende Hilfsroutinen bereit,
die in mehreren Scoring-Komponenten verwendet werden. Sie bündeln häufig
benötigte Aufgaben wie:

- Prüfung und Normalisierung von Eingabewerten
- vereinheitlichte Textaufbereitung für robuste Keyword-Matches
- gewichtete Score-Berechnung
- Zusammenführung verschachtelter JSON-Strukturen (z. B. Shodan-Ausgaben)
- Standardformatierung der Hinweisblöcke für die HTML-Ausgabe
- Technologie-Normalisierung zum Abgleich mit Heuristiklisten

Die Utilities sind bewusst generisch gehalten, damit sie sowohl für
technische Daten (Wappalyzer, Shodan, Link-Status) als auch für
semantische LLM-Auswertungen einheitlich eingesetzt werden können.
"""

from typing import Any, Dict, List, Optional
import re

# ------------------------------------------------------------
# Grundlegende Prüf- und Bewertungsfunktionen
# ------------------------------------------------------------
# Unterstützen einfache Plausibilitätsprüfungen (z. B. numerische Werte)
# und dienen als Bausteine für mehrere Scoring-Komponenten.

def is_num(x: Any) -> bool:
    """Prüft, ob ein Wert numerisch ist (int oder float)."""
    return isinstance(x, (int, float))


def band_for(score: Optional[int]) -> str:
    """
    Leitet aus einem numerischen Score eine qualitative Bewertung ab.
    Wird insbesondere für die Gesamtbewertung genutzt
    („nachhaltig“, „teilweise nachhaltig“, „nicht nachhaltig“).
    """
    if score is None:
        return "unbekannt"
    if score >= 70:
        return "nachhaltig"
    if score >= 40:
        return "teilweise nachhaltig"
    return "nicht nachhaltig"


def is_present(v: Any) -> bool:
    """
    Prüft, ob ein Wert inhaltlich belegt ist.
    Diese Funktion wird u. a. für LLM-basierte Auswertungen genutzt,
    bei denen Werte Listen, Strings oder komplexere Strukturen sein können.
    """
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, list):
        return any(is_present(x) for x in v)
    return bool(str(v).strip())


# ------------------------------------------------------------
# Gewichtete Score-Berechnung
# ------------------------------------------------------------
# Bildet aus mehreren Teilkomponenten einen gewichteten Score.
# Fehlende Werte werden herausgerechnet (Renormalisierung).

def weighted_total(components: Dict[str, Dict[str, Any]], weights: Dict[str, float]) -> Optional[int]:
    """
    Berechnet einen gewichteten Gesamtscore.
    components: {key: {"score": int|None, ...}}
    weights:    {key: float}
    """
    usable: List[tuple[int, float]] = []
    total_w = 0.0

    for k, payload in components.items():
        sc = payload.get("score")
        w = float(weights.get(k, 0.0))
        if sc is None or w <= 0:
            continue
        usable.append((int(sc), w))
        total_w += w

    if not usable or total_w <= 0:
        return None

    acc = sum(sc * (w / total_w) for sc, w in usable)
    return int(round(acc))

# ------------------------------------------------------------
# Standardisiertes Hinweisformat für HTML-Berichte
# ------------------------------------------------------------
# Wandelt Listen von Textbausteinen in ein einheitliches HTML-Format um.

def format_hints(hint_parts):
    """
    Formatiert eine Liste von Hinweisblöcken in ein konsistentes HTML-Format.
    Ohne Bulletpoints, mit definierten Abständen.
    """
    blocks = []

    for raw in hint_parts:
        if not raw:
            continue
        raw = str(raw).strip()
        if not raw:
            continue

        title = None
        content = raw

        if ":" in raw:
            title, content = raw.split(":", 1)
            title = title.strip()
            content = content.strip()

        entries = []
        if content:
            entries = [e.strip() for e in content.split("<br>") if e.strip()]

        if title:
            if entries:
                block_html = (
                    f"<u>{title}:</u><br>" +
                    "<br><br>".join(entries)
                )
            else:
                block_html = f"<u>{title}:</u>"
        else:
            if entries:
                block_html = "<br><br>".join(entries)
            else:
                block_html = content

        blocks.append(block_html)

    return "<br><br>".join(blocks)


# ------------------------------------------------------------
# JSON- und Technologie-Normalisierung (Shodan/Wappalyzer)
# ------------------------------------------------------------
# Helfen beim Durchsuchen und Vereinheitlichen komplexer Strukturen.

def _norm(value: Any) -> str:
    """Normalisiert beliebige Eingaben zu Kleinbuchstaben-Strings."""
    return str(value or "").strip().lower()


def _flatten_json(obj: Any) -> List[str]:
    """Reduziert verschachtelte JSON-Strukturen auf eine flache Textliste."""
    parts: List[str] = []
    if isinstance(obj, dict):
        for v in obj.values():
            parts.extend(_flatten_json(v))
    elif isinstance(obj, list):
        for v in obj:
            parts.extend(_flatten_json(v))
    elif obj is not None:
        text = _norm(obj)
        if text:
            parts.append(text)
    return parts


def _wapp_concat(techs: Optional[List[Dict[str, Any]]]) -> str:
    """
    Kombiniert Namen und Beschreibungen aus Wappalyzer-Ergebnissen
    zu einem durchsuchbaren Textstring.
    """
    entries: List[str] = []
    for tech in techs or []:
        if not isinstance(tech, dict):
            continue
        name = _norm(tech.get("name"))
        desc = _norm(tech.get("description"))
        if name or desc:
            entries.append(f"{name} {desc}".strip())
    return " | ".join(e for e in entries if e)


def _remove_references_recursive(obj):
    """Entfernt rekursiv 'references' und 'html' aus verschachtelten Datensätzen."""
    if isinstance(obj, dict):
        return {
            k: _remove_references_recursive(v)
            for k, v in obj.items()
            if k not in ("references", "html")
        }
    elif isinstance(obj, list):
        return [_remove_references_recursive(i) for i in obj]
    return obj


def _shodan_concat(shodan_data: Optional[Dict[str, Any]]) -> str:
    """
    Extrahiert relevante Textbestandteile aus Shodan-Daten,
    bereinigt um HTML- und Referenzfelder.
    """
    if not isinstance(shodan_data, dict):
        return ""
    cleaned = _remove_references_recursive(shodan_data)
    parts = _flatten_json(cleaned)
    return " | ".join(
        s.strip().lower() for s in parts
        if isinstance(s, str) and s.strip()
    )


# ------------------------------------------------------------
# Technologie-Matching für Wappalyzer
# ------------------------------------------------------------
# Vergleicht normalisierte Technologienamen mit Heuristiklisten
# (z. B. für statische Generatoren).

def _normalize_name(name: str) -> str:
    """Normalisiert Technologie-Bezeichnungen für Token-Vergleiche."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return name.strip()


def _match_tech_name(tech_name: str, reference_list: list[str]) -> Optional[str]:
    """
    Prüft, ob ein Wappalyzer-Technologiename einer Referenz entspricht.
    Vergleicht Token, um Teilworttreffer zu vermeiden.
    """
    norm_tech = _normalize_name(tech_name)
    tech_tokens = set(norm_tech.split())

    for ref in reference_list:
        norm_ref = _normalize_name(ref)
        ref_tokens = set(norm_ref.split())
        if tech_tokens == ref_tokens or tech_tokens.issuperset(ref_tokens):
            return ref
    return None


# ============================================================
# ⚖️  Scoring-Konfiguration & Gewichtung
# ============================================================
#
# Aktuelle Gewichtung:
# --------------------
# Alle Indikatoren werden mit dem Gewicht 1.0 in die
# Gesamtbewertung einbezogen. Dadurch fließen sämtliche
# Techniken, Metadatenmerkmale und organisatorischen Hinweise
# gleichberechtigt in den Gesamtscore ein.
#
# Hintergrund:
# Die Gewichtung wurde bewusst neutral gewählt, um innerhalb
# dieser Arbeit keine Priorisierung einzelner Indikatorgruppen
# vorzunehmen.
#
# Weiterführende Forschung:
# -------------------------
# Für zukünftige Arbeiten besteht die Möglichkeit, differenziertere
# Gewichtungen einzuführen (z. B. stärkere Bewertung technischer
# Nachhaltigkeitsparameter, institutioneller Governance oder
# struktureller Metadaten). Das Framework ist so aufgebaut, dass
# diese Anpassungen ohne Änderungen an den Scoring-Funktionen
# vorgenommen werden können.
#
# Beispiel:
# Anpassungen können direkt in der WEIGHTS-Struktur erfolgen,
# etwa durch Erhöhen einzelner Faktoren (z. B. 1.5 oder 2.0),
# wenn bestimmte Indikatoren stärker zur Gesamtbewertung
# beitragen sollen.
#
# Im Rahmen der vorliegenden Arbeit wurde von einer
# Modifikation der Gewichtung abgesehen.
# ============================================================

WEIGHTS = {
    "isolation": 1.0,
    "staticization": 1.0,
    "wappalyzer_open_closed": 1.0,
    "link_functionality": 1.0,

    "institution_present": 1.0,
    "roles_responsibilities_present": 1.0,
    "funding_present": 1.0,
    "continuation_archiving_preservation_present": 1.0,
    "contact_info_present": 1.0,
    "community_present": 1.0,
    "pi_documentation": 1.0,
    "repos_oss_practice": 1.0,
    "open_license": 1.0,

    "tei_xml_presence": 1.0,
    "f2ab_combined": 1.0,
    "normdata_presence": 1.0,
    "api_presence": 1.0,
    "downloads_presence": 1.0,
    "persistent_ids": 1.0,
}


# ---------------------------------------------------------------
# 🧩 Bewertung: Open Source vs. Closed Source (Wappalyzer + LLM)
# ---------------------------------------------------------------
# Dieser Abschnitt klassifiziert Technologien, die durch Wappalyzer
# oder die LLM-Auswertung erkannt wurden, als „Open Source“ oder
# „Closed Source“. Die Bewertung erfolgt primär anhand technischer
# Evidenzen (OSS-Flag, eindeutige Schlüsselbegriffe), ergänzt
# durch semantische LLM-Hinweise, falls technische Daten fehlen.

from typing import Dict, Any, List


def _text_from_tech(t: Dict[str, Any]) -> str:
    """
    Kombiniert Name und Beschreibung einer Technologie zu einem
    normalisierten Suchtext. Dient zur robusten Keyword-Suche,
    wenn Wappalyzer kein explizites OSS-Flag liefert.
    """
    name = t.get("name")
    desc = t.get("description")

    if isinstance(name, list):
        name = " ".join(map(str, name))
    if isinstance(desc, list):
        desc = " ".join(map(str, desc))

    if not isinstance(name, str):
        name = str(name or "")
    if not isinstance(desc, str):
        desc = str(desc or "")

    text = f"{name} {desc}".lower()
    return (
        text.replace("–", "-")
            .replace("—", "-")
            .replace("  ", " ")
            .strip()
    )


# Starke Keywords für eindeutige Klassifikation.
# Schwache Begriffe wie "free", "gratis" werden bewusst nicht genutzt.
_WAPP_POS = [
    "open source", "open-source", "foss", "free and open",
    "libre software"
]

_WAPP_NEG = [
    "closed source", "closed-source", "proprietary", "commercial only",
    "paid only", "proprietär", "nur kommerziell", "lizenzpflichtig"
]


def score_wappalyzer_open_closed(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bewertet Technologien nach Open-Source- oder Closed-Source-Charakter.
    Grundlage:
        - Wappalyzer-OSS-Flag (technisch belastbar)
        - robuste Keyword-Heuristik
        - LLM-Hinweise (open_source_hint)
    """

    def ensure_list(x):
        # Vereinheitlichung, da Wappalyzer je nach Fall Einzelobjekt liefert
        if isinstance(x, list):
            return x
        if x is None:
            return []
        return [x]

    techs = (result or {}).get("wappalyzer") or []
    techs = ensure_list(techs)

    pos_names: List[str] = []
    neg_names: List[str] = []
    seen_names = set()

    # -------------------------------------------------
    # 1️⃣ Technische Evidenz per OSS-Flag und Keywords
    # -------------------------------------------------
    for t in techs:
        if not isinstance(t, dict):
            continue

        # Name dient als eindeutiger Schlüssel zur Doppelvermeidung
        name = (t.get("name") or "(unbenannt)").strip()
        if name in seen_names:
            continue
        seen_names.add(name)

        oss_flag = t.get("oss")
        text = _text_from_tech(t)

        # Explizite Kennzeichnung durch Wappalyzer
        if oss_flag is True:
            pos_names.append(name)
            continue

        if oss_flag is False:
            neg_names.append(name)
            continue

        # Starke Keyword-Heuristik als Fallback
        hit_pos = any(k in text for k in _WAPP_POS)
        hit_neg = any(k in text for k in _WAPP_NEG)

        if hit_pos:
            pos_names.append(name)
        if hit_neg:
            neg_names.append(name)

    pos = len(pos_names)
    neg = len(neg_names)
    denom = pos + neg

    # -------------------------------------------------
    # 2️⃣ Semantische Evidenz vom LLM
    # -------------------------------------------------
    llm_hints: List[str] = []
    for p in (result.get("page_data") or []):
        if isinstance(p, dict):
            hint = (p.get("llm_analysis") or {}).get("open_source_hint")
            if hint and str(hint).strip():
                llm_hints.append(str(hint).strip())

    llm_hints = sorted(set(llm_hints))

    # -------------------------------------------------
    # 3️⃣ Bewertung basierend auf technischer Evidenz
    # -------------------------------------------------
    if denom == 0 and not llm_hints:
        # Keine Daten → konservativ als proprietär gewertet
        score = 0
        bewertung = "Keine Hinweise auf Open Source erkannt (Standardannahme: Closed Source)"

    elif denom == 0 and llm_hints:
        score = 50
        bewertung = "Semantische Hinweise auf Open Source (nur LLM)"

    else:
        # Verhältniswertung: Anteil Open Source
        score = int(round(100 * (pos / denom)))

        if score == 100:
            bewertung = "Hinweise auf Open Source"
        elif score == 0:
            bewertung = "Hinweise auf proprietäre / Closed-Source-Technologien"
        elif score > 50:
            bewertung = "Open Source überwiegt"
        elif score < 50:
            bewertung = "Closed Source überwiegt"
        else:
            bewertung = "Gemischte Hinweise"

    # -------------------------------------------------
    # 4️⃣ Hinweise formatiert zurückgeben
    # -------------------------------------------------
    hint_parts = []

    if pos_names:
        hint_parts.append(
            "Open-Source-Technologien:<br>" +
            "<br>".join(sorted(set(pos_names)))
        )

    if neg_names:
        hint_parts.append(
            "Proprietäre Technologien:<br>" +
            "<br>".join(sorted(set(neg_names)))
        )

    if llm_hints:
        hint_parts.append(
            "LLM-Analyse:<br>" +
            "<br>".join(llm_hints)
        )

    hinweise = format_hints(hint_parts)

    # -------------------------------------------------
    # 5️⃣ Rückgabe der vollständigen Bewertung
    # -------------------------------------------------
    return {
        "score": score,
        "bewertung": bewertung,
        "hinweise": hinweise,
        "technische_hinweise": {
            "open_source": sorted(set(pos_names)),
            "closed_source": sorted(set(neg_names)),
        },
        "llm_analyse": llm_hints,
        "counts": {
            "open_source_count": pos,
            "closed_source_count": neg,
            "gesamt_bewertet": denom,
            "gesamt_technologien": len(techs),
        },
    }


# ---------------------------------------------------------------
# 🔒 Isolierungserkennung (Container / VM)
# ---------------------------------------------------------------
def score_global_isolation(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bewertet, ob das Projekt Hinweise auf eine isolierte
    Ausführungsumgebung zeigt (Container, VM, Kubernetes etc.).
    Die Bewertung kombiniert technische Hinweise (Shodan/Wappalyzer)
    mit semantischen LLM-Analysen.
    """

    import re

    # -------------------------------------------------
    # 1️⃣ Technische Evidenz aus Shodan/Wappalyzer extrahieren
    # -------------------------------------------------
    shodan_info = result.get("shodan_info") or {}
    wappalyzer = result.get("wappalyzer") or []

    # Vollständige Rohdaten extrahieren, falls verschachtelt
    if isinstance(shodan_info, dict) and "raw_json" in shodan_info:
        shodan_info = shodan_info["raw_json"]

    shodan_text = _shodan_concat(shodan_info)
    wapp_text = _wapp_concat(wappalyzer)

    combined_text = f"{wapp_text} | {shodan_text}"
    lower_text = combined_text.lower()

    # Wortbasierte Erkennung bekannter Isolationstechnologien
    matches: List[str] = []
    for term in ISO_STRONG:
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        if re.search(pattern, lower_text):
            matches.append(term)

    has_technical = bool(matches)

    # -------------------------------------------------
    # 2️⃣ Semantische Hinweise (LLM)
    # -------------------------------------------------
    llm_hints: List[str] = []
    for p in (result.get("page_data") or []):
        if isinstance(p, dict):
            hint = (p.get("llm_analysis") or {}).get("isolation_hint")
            if hint:
                llm_hints.append(str(hint).strip())

    clean_llm_hints = [h for h in llm_hints if h.strip()]

    # -------------------------------------------------
    # 3️⃣ Bewertung
    # -------------------------------------------------
    if has_technical and clean_llm_hints:
        score = 100
        bewertung = "Technische und semantische Evidenz für Isolation vorhanden"

    elif has_technical:
        score = 100
        bewertung = "Technische Hinweise auf isolierte Umgebung vorhanden"

    elif clean_llm_hints:
        score = 50
        bewertung = "Semantische Hinweise auf eine isolierte Umgebung (LLM)"

    else:
        score = None
        bewertung = "Keine Hinweise auf isolierte Ausführungsumgebung gefunden"

    # -------------------------------------------------
    # 4️⃣ Hinweise ausgeben
    # -------------------------------------------------
    hint_parts = []

    if matches:
        hint_parts.append("Technische Hinweise: " + ", ".join(sorted(set(matches))))

    if clean_llm_hints:
        hint_parts.append("LLM-Analyse: " + ", ".join(sorted(set(clean_llm_hints))))

    hinweise = format_hints(hint_parts)

    # -------------------------------------------------
    # 5️⃣ Rückgabe
    # -------------------------------------------------
    return {
        "score": score,
        "bewertung": bewertung,
        "hinweise": hinweise,
        "technische_hinweise": sorted(set(matches)),
        "llm_hinweise": sorted(set(clean_llm_hints)),
    }


# ---------------------------------------------------------------
# 🏗️ Nutzung statischer Webtechnologien (Staticization)
# ---------------------------------------------------------------
def score_static_technologies(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bewertet den Einsatz statischer Webtechnologien, z. B.
    Generatoren (Jekyll, Hugo) oder statische Hosts (GitHub Pages).
    Es werden technische Treffer (Wappalyzer) und LLM-Hinweise
    kombiniert, falls technische Daten unvollständig sind.
    """

    techs = result.get("wappalyzer") or []

    # -------------------------------------------------
    # 1️⃣ Technologie-Namen extrahieren
    # -------------------------------------------------
    tech_names = [
        str(t.get("name")).strip()
        for t in techs
        if isinstance(t, dict) and t.get("name")
    ]

    static_hits = []
    dynamic_hits = []

    # -------------------------------------------------
    # 2️⃣ Technische Evidenz über Matching-Listen
    # -------------------------------------------------
    for tech in tech_names:

        match_static = _match_tech_name(
            tech, STATIC_SITE_GENERATORS + STATIC_HOST_PLATFORMS
        )
        if match_static:
            static_hits.append(match_static)
            continue

        match_dynamic = _match_tech_name(
            tech, DYNAMIC_FRAMEWORKS + CMS_RUNTIME
        )
        if match_dynamic:
            dynamic_hits.append(match_dynamic)

    pos = len(static_hits)
    neg = len(dynamic_hits)
    denom = pos + neg

    # -------------------------------------------------
    # 3️⃣ Semantische LLM-Hinweise
    # -------------------------------------------------
    llm_hints: List[str] = []
    for p in (result.get("page_data") or []):
        hint = (p.get("llm_analysis") or {}).get("staticization_hint")
        if hint:
            llm_hints.append(str(hint).strip())

    clean_llm_hints = [h for h in llm_hints if h.strip()]

    # -------------------------------------------------
    # 4️⃣ Bewertung kombinieren
    # -------------------------------------------------
    if denom == 0 and not clean_llm_hints:
        score = None
        bewertung = "Keine Hinweise auf statische oder dynamische Architektur gefunden"

    elif denom == 0 and clean_llm_hints:
        score = 50
        bewertung = "Semantische Hinweise auf statische Architektur (nur LLM)"

    else:
        ratio = pos / denom
        score = int(round(100 * ratio))

        if score >= 80:
            bewertung = "Hinweise auf statische Architektur"
        elif score >= 60:
            bewertung = "Statische Technologien überwiegen"
        elif score >= 40:
            bewertung = "Gemischte oder hybride Architektur"
        elif score >= 20:
            bewertung = "Dynamische Technologien überwiegen leicht"
        else:
            bewertung = "Hinweise auf dynamische Architektur"

    # -------------------------------------------------
    # 5️⃣ Hinweise formatiert zurückgeben
    # -------------------------------------------------
    hinweise_parts = []

    if static_hits:
        hinweise_parts.append(
            f"Statische Technologien: {', '.join(sorted(set(static_hits)))}"
        )

    if dynamic_hits:
        hinweise_parts.append(
            f"Dynamische Technologien: {', '.join(sorted(set(dynamic_hits)))}"
        )

    if clean_llm_hints:
        hinweise_parts.append(
            f"LLM-Analyse:: {', '.join(sorted(set(clean_llm_hints)))}"
        )

    hinweise = format_hints(hinweise_parts)

    # -------------------------------------------------
    # 6️⃣ Rückgabe
    # -------------------------------------------------
    return {
        "score": score,
        "bewertung": bewertung,
        "hinweise": hinweise,
        "statische_technologien": sorted(set(static_hits)),
        "dynamische_technologien": sorted(set(dynamic_hits)),
        "llm_hinweise": sorted(set(clean_llm_hints)),
        "counts": {
            "static_count": pos,
            "dynamic_count": neg,
            "gesamt_bewertet": denom
        }
    }

# ---------------------------------------------------------------
# 🧩 FAIR Overall (nur FAIR-Checker, keine Mischquellen)
# ---------------------------------------------------------------
#
# Bewertet ausschließlich die von einem FAIR-Checker gelieferten
# Gesamt-Scores. Es werden KEINE anderen Quellen gemischt.
# Die Funktion erwartet eine standardisierte Struktur:
#   result["fair_checker"]["score_overall"] → 0–100 %

def score_fairchecker_overall(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bewertet das FAIR-Checker-Gesamtergebnis (Homepage-Metrik).
    Erwartet:
        result["fair_checker"]["score_overall"]  → Prozentwert (0–100)

    Skala:
        ≥ 70  = FAIR-Score hoch
        40–69 = FAIR-Score mittel
        < 40  = FAIR-Score niedrig
    """
    fc = result.get("fair_checker") or {}

    raw = fc.get("score_overall")
    if not is_num(raw):
        # Kein valider Wert vorhanden
        return {
            "score": None,
            "bewertung": "Kein FAIR-Checker-Ergebnis verfügbar",
            "hinweise": "Es konnte kein FAIR Overall Score ermittelt werden."
        }

    score = int(round(float(raw)))

    # qualitative Einordnung
    if score >= 70:
        hinweis = "FAIR-Score hoch"
    elif score >= 40:
        hinweis = "FAIR-Score mittel"
    else:
        hinweis = "FAIR-Score niedrig"

    return {
        "score": score,
        "bewertung": f"FAIR Overall: {score} %",
        "hinweise": hinweis
    }

# ---------------------------------------------------------------
# 🏛️ Institution & Governance (seitenübergreifend konsolidiert)
# ---------------------------------------------------------------
#
# Diese Funktion erzeugt für jede Governance-Kategorie
# (Institution, Rollen, Förderung, Community etc.)
# eine zusammengefasste LLM-Ausgabe. Die Auswertung ist rein
# qualitativ: sobald ein sinnvoller Hinweis existiert → Score 100.
#
# Kein Seitenvergleich und keine Gewichtung: die Funktion dient
# ausschließlich dazu, anzuzeigen *ob* entsprechende Informationen
# vorhanden sind und sie gesammelt auszugeben.

def score_pages_institutional_governance_split(result: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Einheitliche Ausgabe:

    <u>LLM-Analyse:</u>
    Hinweis A

    Hinweis B
    """

    pages = result.get("page_data") or []

    # Mapping: interne Ergebnis-Schlüssel → LLM-Feldname
    fields = {
        "institution_present": "institution",
        "roles_responsibilities_present": "roles_responsibilities",
        "funding_present": "funding_information",
        "continuation_archiving_preservation_present": "continuation_strategy",
        "contact_info_present": "contact_info",
        "community_present": "community",
    }

    results = {}

    for out_key, llm_field in fields.items():
        blocks = []

        # 1️⃣ Alle LLM-Hinweise der Seiten einsammeln
        for p in pages:
            llm = p.get("llm_analysis") or {}
            raw = llm.get(llm_field)

            if raw and str(raw).strip():
                blocks.append(str(raw).strip())

        # 2️⃣ Deduplizieren (seitenübergreifend)
        unique = []
        seen = set()
        for b in blocks:
            k = b.lower().strip()
            if k not in seen:
                seen.add(k)
                unique.append(b)

        # 3️⃣ Ausgabeformat vereinheitlichen
        if unique:
            parts = ["LLM-Analyse: " + "<br>".join(unique)]
            hinweise = format_hints(parts)
            score = 100
            bewertung = "Hinweise vorhanden"
        else:
            hinweise = ""
            score = None
            bewertung = "Keine Hinweise"

        results[out_key] = {
            "score": score,
            "bewertung": bewertung,
            "hinweise": hinweise,
        }

    return results

# ---------------------------------------------------------------
# 📄 Dokumentation (seitenbasiert)
# ---------------------------------------------------------------
#
# Diese Funktion durchsucht die LLM-Ausgabe jeder Seite nach
# Hinweisen zur Projektdokumentation (z. B. technische Beschreibung,
# Editionsrichtlinien, Datensatzinformationen).
#
# Logik:
#   - Alle Hinweise werden seitenübergreifend gesammelt.
#   - Sobald in irgendeiner Seite ein valider Hinweis vorkommt, gilt:
#         score = 100 (Dokumentation vorhanden)
#   - Keine Hinweise → score = None
#
# Der Rückgabewert enthält sowohl:
#   - eine Gesamtbewertung (score, bewertung, hinweise)
#   - als auch seitenbezogene Detailangaben ("pages")

def score_pages_documentation(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bewertet Dokumentationshinweise im einheitlichen Format:

    <u>LLM-Analyse:</u>
    Hinweis 1

    Hinweis 2
    """
    pages = result.get("page_data") or []
    collected = set()   # alle gefundenen Hinweise (dedupliziert)
    rows = []           # seitenbasierte Einträge für Frontend/Report

    # -----------------------------------------------------
    # Hinweise pro Seite auslesen
    # -----------------------------------------------------
    for p in pages:
        if not isinstance(p, dict):
            continue

        llm = p.get("llm_analysis") or {}
        raw = llm.get("documentation")
        present = False

        # Strings
        if isinstance(raw, str) and raw.strip():
            collected.add(raw.strip())
            present = True

        # Listen
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, str) and item.strip():
                    collected.add(item.strip())
                    present = True

        # Dict-Struktur
        elif isinstance(raw, dict):
            for v in raw.values():
                if isinstance(v, str) and v.strip():
                    collected.add(v.strip())
                    present = True

        rows.append({
            "url": p.get("url") or p.get("final_url") or "?",
            "pi_documentation": 100 if present else None,
            "present": present,
        })

    # -----------------------------------------------------
    # Gesamtbewertung
    # -----------------------------------------------------
    if collected:
        score = 100
        bewertung = "Hinweise auf Dokumentation vorhanden"

        parts = ["LLM-Analyse: " + "<br>".join(sorted(collected))]
        hinweise = format_hints(parts)
    else:
        score = None
        bewertung = "Keine Hinweise auf Dokumentation"
        hinweise = ""

    return {
        "pages": rows,
        "score": score,
        "bewertung": bewertung,
        "hinweise": hinweise,
    }


# ---------------------------------------------------------------
# 🧬 FAIR F2A/B: strukturierte Metadaten & kontrollierte Vokabulare
# ---------------------------------------------------------------
#
# Bewertet die Qualität strukturierter Metadaten (JSON-LD, RDF)
# sowie den Einsatz kontrollierter Vokabulare. Die Bewertung
# kombiniert technische Evidenz und optionale LLM-Hinweise.
#
# Bewertungsskala:
#   100 = strukturierte Metadaten + kontrollierte Vokabulare
#    75 = strukturierte Metadaten vorhanden
#    50 = nur LLM-Hinweise
#  None = keine Hinweise
#
# Alle Seiten tragen zur Bewertung bei.

def score_pages_structured_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bewertet strukturierte Metadaten & kontrollierte Vokabulare.
    Nutzt ausschließlich:
        - p["structured_metadata"]
        - p["llm_analysis"]["structured_metadata_hint"]
    """
    pages = result.get("page_data") or []

    vals = []                  # Scores pro Seite
    rdf_counts = []            # RDF-Tripel gesamt
    llm_hints = set()          # LLM-Hinweise gesamthaft

    for p in pages:
        sm = p.get("structured_metadata") or {}

        has_structured = bool(sm.get("has_structured_metadata"))
        vocabularies = sm.get("controlled_vocabularies") or []
        rdf_count = sm.get("rdf_triples")

        # RDF Triples sammeln
        if isinstance(rdf_count, int) and rdf_count > 0:
            rdf_counts.append(rdf_count)

        # LLM fallback
        raw_llm = (p.get("llm_analysis") or {}).get("structured_metadata_hint")
        if isinstance(raw_llm, str):
            llm_hints.add(raw_llm.strip())
        elif isinstance(raw_llm, list):
            for h in raw_llm:
                if isinstance(h, str) and h.strip():
                    llm_hints.add(h.strip())

        # seitenspezifische Bewertung
        if has_structured and vocabularies:
            vals.append(100)
        elif has_structured:
            vals.append(75)
        elif raw_llm:
            vals.append(50)

    # -----------------------------------------------------
    # Gesamtbewertung
    # -----------------------------------------------------
    avg_score = int(round(sum(vals) / len(vals))) if vals else None

    if avg_score == 100:
        bewertung = "Strukturierte Metadaten und kontrollierte Vokabulare erkannt"
    elif avg_score == 75:
        bewertung = "Strukturierte Metadaten gefunden"
    elif avg_score == 50:
        bewertung = "LLM-Hinweise auf strukturierte Metadaten"
    else:
        bewertung = "Keine Hinweise auf strukturierte Metadaten"

    # Hinweise zusammenstellen
    hint_parts = []

    if rdf_counts:
        hint_parts.append(f"RDF-Tripel gesamt: {sum(rdf_counts)}")

    if llm_hints:
        hint_parts.append("LLM-Analyse: " + ", ".join(sorted(llm_hints)))

    hinweise = format_hints(hint_parts)

    return {
        "score": avg_score,
        "bewertung": bewertung,
        "hinweise": hinweise,
    }


# ---------------------------------------------------------------
# 🗃️ Normdaten-Erkennung (GND, VIAF, Wikidata …)
# ---------------------------------------------------------------
#
# Bewertet das Vorhandensein von Normdaten anhand:
#   - aggregator-basierter Normdatenobjekte
#   - LLM-Hinweisen aus llm_aggregated["normdata_hint"]
#
# Bewertung:
#   100 = echte Normdaten vorhanden
#    50 = nur LLM-Hinweise
#  None = keine Hinweise

def score_pages_normdata_presence(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bewertet Normdaten (GND, VIAF, Wikidata, etc.)
    Basierend auf Aggregator-Ausgabe:
        - result["normdata_items"]
        - result["llm_aggregated"]["normdata_hint"]
    """

    # -----------------------------------------------
    # 1️⃣ Technische Normdateinträge aus Aggregator
    # -----------------------------------------------
    norm_items = result.get("normdata_items") or []
    norm_sources = set()

    for it in norm_items:
        src = it.get("source")
        if isinstance(src, str) and src.strip():
            norm_sources.add(src.strip())

    # -----------------------------------------------
    # 2️⃣ Semantische LLM-Hinweise (aggregiert)
    # -----------------------------------------------
    llm_aggr = result.get("llm_aggregated") or {}
    raw_llm = llm_aggr.get("normdata_hint") or []

    llm_hints = {v.strip() for v in raw_llm if isinstance(v, str) and v.strip()}

    # Hinweisformat wie bei strukturierten Metadaten
    hint_parts = []

    if norm_sources:
        hint_parts.append(
            "Normdaten-Quellen: " + ", ".join(sorted(norm_sources))
        )

    if llm_hints:
        hint_parts.append(
            "LLM-Analyse: " + ", ".join(sorted(llm_hints))
        )

    hinweise = format_hints(hint_parts)

    # -----------------------------------------------
    # Bewertung (technische Evidenz > LLM > keine Evidenz)
    # -----------------------------------------------
    if norm_sources:
        return {
            "score": 100,
            "bewertung": "Hinweise auf Normdaten gefunden",
            "hinweise": hinweise,
        }

    if llm_hints:
        return {
            "score": 50,
            "bewertung": "Nur LLM-Hinweise auf Normdaten gefunden",
            "hinweise": hinweise,
        }

    return {
        "score": None,
        "bewertung": "Keine Hinweise auf Normdaten gefunden",
        "hinweise": "",
    }

# ---------------------------------------------------------------
# 📦 Downloads-Präsenz (technische & semantische Evidenz)
# ---------------------------------------------------------------
#
# Bewertet das Vorhandensein von herunterladbaren Dateien
# (XML, TEI, ZIP, PDF …), die während des Crawlings erkannt wurden.
#
# Bewertungslogik:
#   100 = echte Downloads gefunden (technische Evidenz)
#    50 = ausschließlich LLM-Hinweise
#  None = keine Hinweise
#
# Die Hinweise werden im standardisierten format_hints()-Format ausgegeben.

def score_downloads_presence(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bewertet das Vorhandensein von Downloads (XML, TEI, ZIP, PDF …)
    und formatiert Hinweise im Standardformat.
    """
    pages = result.get("page_data") or []

    # -----------------------------------------------------------
    # 1️⃣ Technische Evidenz: Downloads aus allen Seiten sammeln
    # -----------------------------------------------------------
    all_download_urls: List[str] = []
    total_count = 0

    for p in pages:
        if not isinstance(p, dict):
            continue

        dl = p.get("downloads")
        if not isinstance(dl, dict):
            continue

        # Gesamtanzahl der Downloads pro Seite (aus dem Aggregator)
        total_count += dl.get("count", 0) or 0

        # Download-URLs extrahieren
        for it in dl.get("items", []):
            if isinstance(it, dict):
                url = it.get("url")
                if isinstance(url, str):
                    clean = url.split("?")[0].split("#")[0]
                    all_download_urls.append(clean)

    # -----------------------------------------------------------
    # 2️⃣ Semantische Hinweise aus LLM
    # -----------------------------------------------------------
    llm_hints: List[str] = []

    for p in pages:
        pi = p.get("llm_analysis") or {}
        raw = pi.get("downloads_hint")

        if isinstance(raw, str) and raw.strip():
            llm_hints.append(raw.strip())

        elif isinstance(raw, list):
            for v in raw:
                if isinstance(v, str) and v.strip():
                    llm_hints.append(v.strip())

    # -----------------------------------------------------------
    # 3️⃣ Hinweise formatieren (globales format_hints)
    # -----------------------------------------------------------
    hint_parts: List[str] = []

    # technische Evidenz
    if total_count > 0:
        if all_download_urls:
            joined = "<br>".join(sorted(set(all_download_urls)))
            hint_parts.append(f"Gefundene Downloads:<br>{joined}")
        else:
            hint_parts.append("Gefundene Downloads: Download-Links vorhanden")

    # LLM-Hinweise
    if llm_hints:
        joined = "<br>".join(sorted(set(llm_hints)))
        hint_parts.append(f"LLM-Analyse:<br>{joined}")

    hinweise = format_hints(hint_parts)

    # -----------------------------------------------------------
    # 4️⃣ Bewertung
    # -----------------------------------------------------------
    if total_count > 0:
        return {
            "score": 100,
            "bewertung": "Downloads gefunden",
            "hinweise": hinweise,
            "urls": sorted(set(all_download_urls)),
            "count": total_count,
        }

    if llm_hints:
        return {
            "score": 50,
            "bewertung": "Nur LLM-Hinweise auf Downloads gefunden",
            "hinweise": hinweise,
            "urls": [],
            "count": 0,
        }

    return {
        "score": None,
        "bewertung": "Keine Hinweise auf Downloads",
        "hinweise": "",
        "urls": [],
        "count": 0,
    }


# ---------------------------------------------------------------
# 🔌 API-Präsenz (technisch + LLM)
# ---------------------------------------------------------------
#
# Erkennt vorhandene API-Schnittstellen (OAI-PMH, IIIF, SPARQL,
# REST-Endpunkte usw.) und kombiniert diese mit optionalen
# LLM-Hinweisen.
#
# Bewertung:
#   100 = technische API gefunden
#    50 = nur LLM-Hinweise
#  None = keine Hinweise

def score_api_presence(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bewertet das Vorhandensein von API-Schnittstellen.
    """
    pages = result.get("page_data") or []

    tech_entries: Set[str] = set()
    llm_hints: Set[str] = set()

    # -----------------------------------------------------------
    # 1️⃣ Technische APIs einsammeln
    # -----------------------------------------------------------
    for p in pages:
        if not isinstance(p, dict):
            continue

        for api in (p.get("api_interfaces") or []):
            if not isinstance(api, dict):
                continue

            api_type = str(api.get("type") or "API").strip()
            api_url = api.get("url")

            # Einheitliche Darstellungsweise „Typ (URL)“
            if api_url:
                entry = f"{api_type} ({api_url})"
            else:
                entry = api_type

            tech_entries.add(entry)

        # -----------------------------------------------------------
        # 2️⃣ LLM-Hinweise
        # -----------------------------------------------------------
        raw_hint = (p.get("llm_analysis") or {}).get("api_hint")

        if isinstance(raw_hint, str) and raw_hint.strip():
            llm_hints.add(raw_hint.strip())

        elif isinstance(raw_hint, list):
            for h in raw_hint:
                if isinstance(h, str) and h.strip():
                    llm_hints.add(h.strip())

    # -----------------------------------------------------------
    # 3️⃣ Hinweise formatieren
    # -----------------------------------------------------------
    hint_parts: List[str] = []

    if tech_entries:
        hint_parts.append("Technische APIs:<br>" + "<br>".join(sorted(tech_entries)))

    if llm_hints:
        hint_parts.append("LLM-Analyse:<br>" + "<br>".join(sorted(llm_hints)))

    hinweise = format_hints(hint_parts)

    # -----------------------------------------------------------
    # 4️⃣ Bewertung
    # -----------------------------------------------------------
    if tech_entries:
        return {
            "score": 100,
            "bewertung": "Technische APIs gefunden",
            "hinweise": hinweise,
            "apis": sorted(tech_entries),
            "llm_hinweise": sorted(llm_hints),
        }

    if llm_hints:
        return {
            "score": 50,
            "bewertung": "Nur Hinweise auf APIs (LLM) gefunden",
            "hinweise": hinweise,
            "apis": [],
            "llm_hinweise": sorted(llm_hints),
        }

    return {
        "score": None,
        "bewertung": "Keine Hinweise auf APIs gefunden",
        "hinweise": "",
        "apis": [],
        "llm_hinweise": [],
    }


# ---------------------------------------------------------------
# 📝 XML / TEI-Präsenz
# ---------------------------------------------------------------
#
# Erkennt echte XML/TEI-Dateien aus xml_scan sowie LLM-Hinweise.
#
# Bewertung:
#   100 = technische XML/TEI-Evidenz
#    50 = nur LLM-Hinweise
#  None = keine Hinweise

def score_xml_tei(result: Dict[str, Any]) -> Dict[str, Any]:

    pages = result.get("page_data") or []

    xml_urls: Set[str] = set()
    llm_hints: Set[str] = set()

    for p in pages:
        if not isinstance(p, dict):
            continue

        # -------------------------------------------------------
        # 1️⃣ Technische Evidenz: erkannte XML/TEI-Dateien
        # -------------------------------------------------------
        for entry in (p.get("xml_scan") or []):
            url = entry.get("url")
            if isinstance(url, str) and url.strip():
                xml_urls.add(url.split("?")[0].split("#")[0])

        # -------------------------------------------------------
        # 2️⃣ LLM-Hinweise
        # -------------------------------------------------------
        raw = (p.get("llm_analysis") or {}).get("tei_hint")

        if isinstance(raw, str) and raw.strip():
            llm_hints.add(raw.strip())
        elif isinstance(raw, list):
            for h in raw:
                if isinstance(h, str) and h.strip():
                    llm_hints.add(h.strip())

    # -------------------------------------------------------
    # 3️⃣ Hinweise formatieren
    # -------------------------------------------------------
    hint_parts = []

    if xml_urls:
        hint_parts.append("XML/TEI-Dateien:<br>" + "<br>".join(sorted(xml_urls)))

    if llm_hints:
        hint_parts.append("LLM-Analyse:<br>" + "<br>".join(sorted(llm_hints)))

    hinweise = format_hints(hint_parts)

    # -------------------------------------------------------
    # 4️⃣ Bewertung
    # -------------------------------------------------------
    if xml_urls:
        return {
            "score": 100,
            "bewertung": "XML/TEI-Dateien gefunden",
            "hinweise": hinweise,
            "urls": sorted(xml_urls),
            "llm_hinweise": sorted(llm_hints),
        }

    if llm_hints:
        return {
            "score": 50,
            "bewertung": "Nur LLM-Hinweise auf XML/TEI gefunden",
            "hinweise": hinweise,
            "urls": [],
            "llm_hinweise": sorted(llm_hints),
        }

    return {
        "score": None,
        "bewertung": "Keine Hinweise auf XML/TEI gefunden",
        "hinweise": "",
        "urls": [],
        "llm_hinweise": [],
    }


# ---------------------------------------------------------------
# 🗂️ Repositories (GitHub / GitLab)
# ---------------------------------------------------------------
#
# Bewertet Repository-Präsenz anhand:
#   - technischer Evidenz (GitHub/GitLab-Extraktion)
#   - optionaler LLM-Hinweise
#
# Bewertung:
#   100 = echte Repositories gefunden
#    50 = nur LLM-Hinweise
#  None = keine Hinweise

def score_repositories(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bewertet GitHub/GitLab-Repositories im einheitlichen format_hints()-Format.
    """

    github_repos = result.get("github_repos") or []
    gitlab_repos = result.get("gitlab_repos") or []

    # -----------------------------------------------------------
    # 1️⃣ LLM-Hinweise
    # -----------------------------------------------------------
    llm_hints: Set[str] = set()
    for p in (result.get("page_data") or []):
        if isinstance(p, dict):
            raw = (p.get("llm_analysis") or {}).get("repositories_hint")
            if isinstance(raw, str) and raw.strip():
                llm_hints.add(raw.strip())

    # -----------------------------------------------------------
    # 2️⃣ Technische Repo-Links extrahieren
    # -----------------------------------------------------------
    tech_links: List[str] = []

    for repo in github_repos:
        url = repo.get("html_url") or repo.get("web_url")
        if isinstance(url, str) and url.startswith("http"):
            tech_links.append(url)

    for repo in gitlab_repos:
        url = repo.get("web_url") or repo.get("html_url")
        if isinstance(url, str) and url.startswith("http"):
            tech_links.append(url)

    tech_links = sorted(set(tech_links))

    # -----------------------------------------------------------
    # 3️⃣ Deduplizierte LLM-Hinweise generieren
    # -----------------------------------------------------------
    cleaned_llm_hints = [
        h for h in sorted(llm_hints) if h not in tech_links
    ]

    # -----------------------------------------------------------
    # 4️⃣ Hinweise formatieren
    # -----------------------------------------------------------
    hint_parts = []

    if tech_links:
        hint_parts.append("Gefundene Repositories:<br>" + "<br>".join(tech_links))

    if cleaned_llm_hints:
        hint_parts.append("LLM-Hinweise:<br>" + "<br>".join(cleaned_llm_hints))

    hinweise = format_hints(hint_parts)

    # -----------------------------------------------------------
    # 5️⃣ Bewertung
    # -----------------------------------------------------------
    if tech_links:
        return {
            "score": 100,
            "bewertung": "Echte GitHub/GitLab-Repositories gefunden",
            "hinweise": hinweise,
            "repos": {
                "github": github_repos,
                "gitlab": gitlab_repos,
            },
        }

    if cleaned_llm_hints:
        return {
            "score": 50,
            "bewertung": "Nur Hinweise auf Repositories (LLM-Fallback) gefunden",
            "hinweise": hinweise,
            "repos": {"github": [], "gitlab": []},
        }

    return {
        "score": None,
        "bewertung": "Keine Hinweise auf Repositories gefunden",
        "hinweise": "",
        "repos": {"github": [], "gitlab": []},
    }


# ---------------------------------------------------------------
# 🔗 Link-Funktionalität (Stabilität interner Seiten)
# ---------------------------------------------------------------
#
# Bewertet die technische Qualität interner Links anhand der HTTP-
# Statuscodes, die der Crawler ermittelt hat.
#
# Bewertung:
#   - 100% = alle Links funktionieren
#   - 0%   = alle fehlerhaft
#
# Die Beschreibung ist textuell differenziert, damit das Frontend
# eine gut lesbare Einordnung anzeigen kann.

def _status_ok(code: Any) -> bool:
    """
    True, wenn der Statuscode einen funktionsfähigen Link anzeigt.
    200–399 = OK
    """
    try:
        c = int(code)
        return 200 <= c < 400
    except Exception:
        return False


def _status_err(code: Any) -> bool:
    """
    True, wenn der Statuscode einen fehlerhaften Link anzeigt.
    400–599 = Fehler.
    Alles außerhalb des HTTP-Spektrums wird als Fehler gewertet.
    """
    try:
        c = int(code)
        # echte HTTP-Fehlercodes
        if 400 <= c < 600:
            return True
        # nicht interpretierbare Codes → Fehler
        if c < 100 or c > 599:
            return True
        return False
    except Exception:
        return True


def score_link_functionality(link_checks: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Bewertet die technische Stabilität der Webseite anhand der Link-Funktionalität.
    """
    if not link_checks:
        return {
            "score": None,
            "bewertung": "Keine Link-Prüfungen vorhanden",
            "hinweise": "",
        }

    # 1️⃣ Duplikate entfernen (nach URL)
    by_url: Dict[str, Any] = {}
    for r in link_checks:
        if isinstance(r, dict):
            url = (r.get("url") or "").strip()
            if url:
                by_url[url] = r.get("status")

    if not by_url:
        return {
            "score": None,
            "bewertung": "Keine auswertbaren Links erkannt",
            "hinweise": "",
        }

    # 2️⃣ Statuscodes auswerten
    ok = sum(_status_ok(st) for st in by_url.values())
    fail = sum(_status_err(st) for st in by_url.values())
    total = ok + fail

    if total == 0:
        return {
            "score": 0,
            "bewertung": "Keine gültigen HTTP-Antworten erhalten",
            "hinweise": "Links vorhanden, aber keine verwertbaren Statuscodes",
        }

    # 3️⃣ numerischer Score
    score = int(round(100 * ok / total))

    # 4️⃣ textliche Bewertung
    bewertung = f"{ok} von {total} Links funktionieren"

    # 5️⃣ Detailhinweis
    if score == 100:
        hinweis = "Alle internen Links funktionieren stabil."
    elif score >= 90:
        hinweis = "Die meisten internen Links funktionieren stabil."
    elif score >= 70:
        hinweis = "Die Link-Stabilität ist insgesamt solide, aber einige interne Links sind fehlerhaft."
    elif score >= 40:
        hinweis = "Etwa die Hälfte der internen Links funktioniert; es bestehen deutliche technische Probleme."
    elif score >= 10:
        hinweis = "Die meisten internen Links sind fehlerhaft. Die technische Stabilität ist eingeschränkt."
    else:
        hinweis = "Fast alle internen Links sind fehlerhaft. Die Seite weist gravierende technische Probleme auf."

    return {
        "score": score,
        "bewertung": bewertung,
        "hinweise": hinweis,
        "counts": {
            "ok": ok,
            "fail": fail,
            "total": total
        }
    }


# ---------------------------------------------------------------
# 🔗 Persistente Identifier (PID)
# ---------------------------------------------------------------
#
# Erkennt echte persistente Identifier wie:
#   - DOI
#   - Handle
#   - ARK
#   - URN
#   - ORCID
#   - arXiv
#
# Bewertungslogik:
#   100 = technische Evidenz für echte PIDs
#    50 = ausschließlich textuelle/semantische LLM-Hinweise
#  None = keine Hinweise
#
# Die Hinweise werden im standardisierten format_hints()-Format ausgegeben.

def score_persistent_ids(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bewertet persistente Identifier (PIDs) wie DOI, Handle, ARK, URN, ORCID, arXiv
    im einheitlichen format_hints()-Format.
    """
    pages = result.get("page_data") or []

    found_pids: List[str] = []
    llm_hints: List[str] = []

    # -----------------------------------------------------------
    # 1️⃣ Technische Evidenz (harte PIDs aus internal/external_links)
    # -----------------------------------------------------------
    for p in pages:
        if not isinstance(p, dict):
            continue

        # beide Buckets durchsuchen
        for bucket in ("internal_links_all", "external_links_all"):
            for link in (p.get(bucket) or []):
                if not isinstance(link, dict):
                    continue

                pid_type = link.get("persistent_type")

                # "uri" = kein PID → ignorieren
                if pid_type and pid_type not in ("uri", None):
                    url = link.get("url") or ""
                    found_pids.append(f"{pid_type}: {url}")

    # -----------------------------------------------------------
    # 2️⃣ Semantische Evidenz (LLM)
    # -----------------------------------------------------------
    for p in pages:
        if not isinstance(p, dict):
            continue

        raw = (p.get("llm_analysis") or {}).get("persistent_identifier_hint")

        if isinstance(raw, str) and raw.strip():
            llm_hints.append(raw.strip())
        elif isinstance(raw, list):
            for h in raw:
                if isinstance(h, str) and h.strip():
                    llm_hints.append(h.strip())

    # Eindeutigkeit herstellen
    found_pids = sorted(set(found_pids))
    llm_hints = sorted(set(llm_hints))

    # -----------------------------------------------------------
    # 3️⃣ Hinweise im standardisierten format_hints()-Format
    # -----------------------------------------------------------
    hint_parts: List[str] = []

    if found_pids:
        hint_parts.append("Persistente Identifier:<br>" + "<br>".join(found_pids))

    if llm_hints:
        hint_parts.append("LLM-Analyse:<br>" + "<br>".join(llm_hints))

    hinweise = format_hints(hint_parts)

    # -----------------------------------------------------------
    # 4️⃣ Bewertung
    # -----------------------------------------------------------
    if found_pids:
        return {
            "score": 100,
            "bewertung": "Persistente Identifier erkannt",
            "hinweise": hinweise,
            "technische_hinweise": found_pids,
            "llm_hinweise": llm_hints,
        }

    if llm_hints:
        return {
            "score": 50,
            "bewertung": "Semantische Hinweise auf persistente Identifier (LLM)",
            "hinweise": hinweise,
            "technische_hinweise": [],
            "llm_hinweise": llm_hints,
        }

    return {
        "score": None,
        "bewertung": "Keine Hinweise auf persistente Identifier gefunden",
        "hinweise": "",
        "technische_hinweise": [],
        "llm_hinweise": [],
    }


# ---------------------------------------------------------------
# 🧾 Lizenz-Heuristik (offene vs. proprietäre Lizenz)
# ---------------------------------------------------------------
#
# Die Funktion is_open_license() gleicht Lizenzangaben gegen zwei
# Keyword-Listen ab — einmal für offene, einmal für proprietäre Lizenzen.
#
# score_open_license() kombiniert:
#   - LLM-Lizenzangaben (institutionelle Lizenz)
#   - Repository-Lizenzen (GitHub/GitLab)
#
# Bewertungslogik:
#   100 = offene Lizenz in Repositories
#    50 = offene Lizenz nur laut LLM / institutionell
#     0 = proprietäre Lizenz gefunden
#  None = keinerlei Lizenzangaben

OPEN_LICENSE_KEYWORDS = [
    "mit", "gpl", "lgpl", "agpl", "apache", "bsd", "mpl",
    "cc-by", "cc by", "cc0", "creative commons", "public domain",
    "eupl", "osl", "artistic",
]

PROPRIETARY_KEYWORDS = [
    "all rights reserved",
    "alle rechte vorbehalten",
    "proprietary",
    "commercial",
    "nicht öffentlich",
    "closed",
    "no-license",
    "no license",
    "copyright",
    "©",
]


def is_open_license(name: Any) -> bool:
    """
    Robuste Heuristik zur Erkennung offener Lizenzen.
    Akzeptiert Strings, Listen und Dictionaries.
    """
    if not name:
        return False

    # Listen oder Tupel
    if isinstance(name, (list, tuple)):
        return any(is_open_license(n) for n in name)

    # Dictionaries
    if isinstance(name, dict):
        return any(is_open_license(v) for v in name.values())

    # String normalisieren
    if not isinstance(name, str):
        try:
            name = str(name)
        except Exception:
            return False

    n = name.lower().strip()

    # proprietäre Muster zuerst
    if any(p in n for p in PROPRIETARY_KEYWORDS):
        return False

    # offene Lizenzen
    if any(o in n for o in OPEN_LICENSE_KEYWORDS):
        return True

    return False


def score_open_license(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bewertet offene/proprietäre Lizenzen im einheitlichen format_hints()-Format.
    Verwendet:
        - institutionelle Lizenz aus LLM
        - technische Repositories (GitHub/GitLab)
    """
    pages = result.get("page_data") or []

    # ------------------------------------------------
    # 1️⃣ Institutionelle Lizenz aus LLM
    # ------------------------------------------------
    institutional_license = None
    for p in pages:
        if not isinstance(p, dict):
            continue

        lic = (p.get("llm_analysis") or {}).get("license")
        if lic:
            institutional_license = lic
            break

    has_inst_license = institutional_license is not None
    inst_is_open = is_open_license(institutional_license) if has_inst_license else False

    # ------------------------------------------------
    # 2️⃣ Technische Lizenzen aus Repositories
    # ------------------------------------------------
    repos = (result.get("github_repos") or []) + (result.get("gitlab_repos") or [])
    repo_licenses: List[str] = []

    repo_has_open = False
    repo_has_proprietary = False

    for r in repos:
        if not isinstance(r, dict):
            continue

        lic_obj = r.get("license")
        lic_name = None

        # GitHub liefert dict
        if isinstance(lic_obj, dict):
            lic_name = lic_obj.get("name") or lic_obj.get("spdx_id") or lic_obj.get("key")

        # GitLab liefert string
        elif isinstance(lic_obj, str):
            lic_name = lic_obj

        if lic_name:
            repo_licenses.append(lic_name)
            if is_open_license(lic_name):
                repo_has_open = True
            else:
                repo_has_proprietary = True

    has_repos = len(repos) > 0

    # ------------------------------------------------
    # 3️⃣ Score bestimmen
    # ------------------------------------------------
    if has_repos:
        if repo_has_open:
            score = 100
        elif repo_has_proprietary:
            score = 0
        else:
            # keine Info → fallback auf LLM
            score = 50 if inst_is_open else None
    else:
        # keine Repos → ausschließlich institutionelle Info
        if inst_is_open:
            score = 50
        elif institutional_license:
            score = 0
        else:
            score = None

    # ------------------------------------------------
    # 4️⃣ Hinweise formatieren
    # ------------------------------------------------
    hint_parts: List[str] = []

    if repo_licenses:
        joined = "<br>".join(sorted(set(repo_licenses)))
        hint_parts.append(f"Repository-Lizenzen:<br>{joined}")

    if institutional_license:
        hint_parts.append(f"Institutionelle Lizenz (LLM): {institutional_license}")

    hinweise = format_hints(hint_parts)

    # ------------------------------------------------
    # 5️⃣ Bewertungstext
    # ------------------------------------------------
    if score == 100:
        bewertung = "Offene Lizenz gefunden (technische Evidenz)"
    elif score == 50:
        bewertung = "Offene Lizenz laut institutioneller/LLM-Angabe"
    elif score == 0:
        bewertung = "Proprietäre Lizenz gefunden"
    else:
        bewertung = "Keine Lizenzangaben gefunden"

    # ------------------------------------------------
    # 6️⃣ Rückgabe
    # ------------------------------------------------
    return {
        "score": score,
        "bewertung": bewertung,
        "hinweise": hinweise,
        "repo_lizenzen": sorted(set(repo_licenses)),
        "institutionelle_lizenz": institutional_license or "",
    }


# ======================================================================
# 🧮 compute_scoring(): Hauptfunktion zur Gesamtauswertung aller Indikatoren
# ======================================================================
#
# compute_scoring() ruft ALLE Einzel-Scores auf, sammelt sie,
# ergänzt fehlende Keys und berechnet abschließend den gewichteten
# Gesamtscore (ohne FAIR-Score).
#
# Die Debug-Ausgaben helfen für die Live-Ausgabe im Terminal.
# Keine Funktionsänderung → rein erklärende Kommentare.

def compute_scoring(
    result: Dict[str, Any],
    component_results: Optional[Dict[str, Dict[str, Any]]] = None
) -> Dict[str, Any]:

    print("\n[DEBUG] compute_scoring() gestartet")

    # Hilfsfunktion für sichere Aufrufe
    def safe_call(label: str, func, *args, **kwargs):
        print(f"[DEBUG] → Starte {label} ...")
        try:
            out = func(*args, **kwargs)
            print(f"[DEBUG] ← {label} OK ✅")
            return out
        except Exception as e:
            print(f"[ERROR] {label} fehlgeschlagen → {e}")
            import traceback
            traceback.print_exc()
            return {"score": None, "bewertung": f"Fehler in {label}", "hinweise": str(e)}

    # ------------------------------------------------------------
    # 1️⃣ Alle Scoring-Komponenten berechnen (falls nicht vorhanden)
    # ------------------------------------------------------------
    if component_results is None:
        print("[DEBUG] Berechne Einzelindikatoren...")

        component_results = {
            "wappalyzer_open_closed": safe_call("score_wappalyzer_open_closed", score_wappalyzer_open_closed, result),
            "isolation": safe_call("score_global_isolation", score_global_isolation, result),
            "staticization": safe_call("score_static_technologies", score_static_technologies, result),
            "pi_documentation": safe_call("score_pages_documentation", score_pages_documentation, result),
            "link_functionality": safe_call("score_link_functionality", score_link_functionality, result.get("internal_link_checks") or []),
            "downloads_presence": safe_call("score_downloads_presence", score_downloads_presence, result),
            "tei_xml_presence": safe_call("score_xml_tei", score_xml_tei, result),
            "f2ab_combined": safe_call("score_pages_structured_metadata", score_pages_structured_metadata, result),
            "normdata_presence": safe_call("score_pages_normdata_presence", score_pages_normdata_presence, result),
            "repos_oss_practice": safe_call("score_repositories", score_repositories, result),
            "api_presence": safe_call("score_api_presence", score_api_presence, result),
            "open_license": safe_call("score_open_license", score_open_license, result),
            "persistent_ids": safe_call("score_persistent_ids", score_persistent_ids, result),

            # FAIR separat (fließt nicht in Gesamtscore ein)
            "fair_overall": safe_call("score_fairchecker_overall", score_fairchecker_overall, result),
        }

        # Governance separat → mehrere Unterkategorien
        governance_split = safe_call(
            "score_pages_institutional_governance_split",
            score_pages_institutional_governance_split,
            result
        )
        if governance_split:
            component_results.update(governance_split)

    # ------------------------------------------------------------
    # 2️⃣ FAIR aus Gesamtbewertung herausnehmen
    # ------------------------------------------------------------
    FAIR_KEYS = {"fair_overall"}

    scoring_components = {
        k: v
        for k, v in component_results.items()
        if k not in FAIR_KEYS and isinstance(v, dict) and v.get("score") is not None
    }

    # Mindestanzahl an Kriterien für Gesamtbewertung
    MIN_CRITERIA_COUNT = 5
    valid_count = len(scoring_components)
    total_count = len([k for k in component_results if k not in FAIR_KEYS])

    if valid_count < MIN_CRITERIA_COUNT:
        total_score = None
        total_band = "keine Bewertung (zu wenige Daten)"
        note = f"Keine Gesamtbewertung – nur {valid_count} von {total_count} Kriterien bewertet."
    else:
        total_score = weighted_total(scoring_components, WEIGHTS)
        total_band = band_for(total_score)
        note = f"Bewertung basiert auf {valid_count} von {total_count} Kriterien (ohne FAIR)."

    # ------------------------------------------------------------
    # 3️⃣ Fehlende Keys ergänzen (Frontend erwartet vollständiges Set)
    # ------------------------------------------------------------
    EXPECTED_KEYS = [
        "institution_present",
        "roles_responsibilities_present",
        "funding_present",
        "continuation_archiving_preservation_present",
        "contact_info_present",
        "community_present",

        "tei_xml_presence",
        "f2ab_combined",
        "normdata_presence",
        "api_presence",
        "pi_documentation",
        "repos_oss_practice",
        "wappalyzer_open_closed",
        "downloads_presence",
        "open_license",
        "isolation",
        "staticization",
        "link_functionality",
        "persistent_ids",

        "fair_overall",
    ]

    for key in EXPECTED_KEYS:
        if key not in component_results:
            component_results[key] = {"score": None, "bewertung": "–", "hinweise": "–"}

    # ------------------------------------------------------------
    # 4️⃣ Rückgabe
    # ------------------------------------------------------------
    return {
        "global": component_results,
        "total": {
            "score": total_score,
            "band": total_band,
            "criteria_count": {"valid": valid_count, "total": total_count},
            "note": note,
        },
    }


