"""
llm_analysis.py
================

LLM-basierte Extraktion strukturierter Nachhaltigkeitsindikatoren
-----------------------------------------------------------------
Dieses Modul steuert die KI-gesteuerte Extraktion von Projekt- und
Nachhaltigkeitsinformationen aus HTML-Seiten. Es erzeugt ein strikt
valides JSON-Ergebnis nach dem Schema `LLMAnalysis`.

Zentrale Bestandteile:
----------------------
1. Datenmodell (LLMAnalysis)
   - Definiert alle Felder, die der LLM aus HTML extrahieren darf
   - Ausschließlich belegbare Hinweise → nie Halluzinationen

2. get_llm_extraction_strategy()
   - Baut eine LLMExtractionStrategy für Crawl4AI
   - Nutzt GPT-4o-mini
   - Enthält den vollständigen Evaluations-Prompt (unverändert)
   - Wendet Chunking & robuste JSON-Ausgabe an
   - Verbose-Modus für Debugging aktiviert

3. Encoding- & Typkorrektur
   - `_fix_encoding()` behebt UTF-8/Latin-1-Fehler
   - `_normalize_types()` vereinheitlicht Listen und Strings

4. JSON-Extraktionslogik
   - `_extract_json_objects()` findet verschachtelte JSON-Fragmente
   - `extract_json_from_text()` wählt das beste gültige Objekt aus
     (höchste Überschneidung mit erwarteten Feldern)

5. Merge-Funktion
   - `merge_results()` kombiniert Chunk-Ergebnisse duplikatfrei
   - Liefert ein einziges konsolidiertes Analyseobjekt
   - Debug-Logs zeigen Merge-Fortschritt & finalen Zustand

"""

import re
import json
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.async_configs import LLMConfig


# --------------------------------------------------------------------
# 🧱 Datenmodell für die LLM-Ausgabe
# --------------------------------------------------------------------
class LLMAnalysis(BaseModel):
    institution: Optional[str] = None
    roles_responsibilities: Optional[str] = None
    funding_information: Optional[str] = None
    continuation_strategy: Optional[str] = None
    contact_info: Optional[str] = None
    community: Optional[str] = None
    documentation: Optional[str] = None
    license: Optional[Union[str, List[str]]] = None
    tei_hint: Optional[str] = None
    api_hint: Optional[str] = None
    downloads_hint: Optional[str] = None
    repositories_hint: Optional[str] = None
    normdata_hint: Optional[str] = None
    structured_metadata_hint: Optional[str] = None
    persistent_identifier_hint: Optional[str] = None
    staticization_hint: Optional[str] = None
    isolation_hint: Optional[str] = None
    open_source_hint: Optional[str] = None



# --------------------------------------------------------------------
# 🤖 LLM-Extraktionsstrategie (für Crawl4AI)
# --------------------------------------------------------------------
def get_llm_extraction_strategy(
    api_token: str,
    temperature: float = 0.0,
    max_tokens: int = 1800,
) -> LLMExtractionStrategy:
    """
    Erstellt eine deterministische LLMExtractionStrategy für Crawl4AI.
    GPT-4o-mini extrahiert strukturierte JSON-Daten nach dem Schema `LLMAnalysis`.
    """
    print("⚙️ Initialisiere LLMExtractionStrategy mit GPT-4o-mini (erweitert)")

    llm_config = LLMConfig(
        provider="openai/gpt-4o-mini",
        api_token=api_token,
    )

    instruction = r"""
    Du bist ein präzises Analysemodell zur Extraktion von Web-Metadaten und Nachhaltigkeitsindikatoren aus HTML-Quelltexten. 
    Analysiere den gesamten HTML-Inhalt (sichtbare Texte, Metadaten, Skripte, Impressum, Footer, technische Hinweise, Quellcode-Kommentare). 
    Ziehe ausschließlich aus expliziten Text- oder Strukturhinweisen belegbare Schlüsse. 
    Erfinde nichts, interpretiere nicht frei und gib nur Informationen wieder, die im HTML tatsächlich vorkommen.\n\n

    Erstelle **genau ein valides JSON-Objekt** mit den unten definierten Feldern. 
    Für jedes Feld gilt: Wenn keine ausreichenden oder eindeutigen Hinweise im HTML zu finden sind, setze den Wert **null**.\n\n

    ### Felder:\n
    - institution: Bestimme die Institution(en), die bei der Erstellung der digitalen Edition mitgewirkt haben (inhaltlich und/oder technisch). Nenne diese. 
       Berücksichtige auch alle Informationen aus alt-Texten von Logos, Bannern oder Icons. \n
    - roles_responsibilities: Erfasse alle Personen mit organisatorischer, technischer oder inhaltlicher Verantwortung für die digitale Edition.
       Gib jede Angabe im Format 'Rolle: Name' aus (z. B. Editor: Dániel Kiss oder Technische Umsetzung: Woodpecker Software).\n
    - funding_information: Prüfe, ob Informationen zur finanziellen Förderung vorliegen. Gib alle gefundenen förderbezogenen Angaben vollständig wieder.
       Dazu gehören:
       Förderinstitutionen (z. B. DFG, FWF)
       Förderprogramme
       Jahreszahlen im Kontext von Projektphasen, Förderung oder Finanzierung (z. B. "2018–2021", "gefördert 2020–2024")
       Nutze auch Angaben in alt-Texten von Logos oder Icons von Förderorganisationen.\n
    - continuation_strategy: Prüfe ausschließlich Hinweise auf Fortführung, Weiterarbeit oder langfristige Sicherung der Edition, unabhängig von Förderung.
       Dazu zählen:
       Aussagen zur Weiterführung nach Förderende
       Hinweise auf dauerhafte Pflege, Wartung oder Aktualisierung
       Strategien zur technischen Nachhaltigkeit
       Hinweise auf langfristige Zugänglichkeit (Archivserver, statische Bereitstellung etc.)
       Wichtig: Jahreszahlen zählen **nur dann**, wenn sie explizit als „Fortführung nach Förderende“ oder „langfristige Sicherung“ erwähnt werden.
       Förderzeiträume dürfen **nicht** als Fortführung interpretiert werden.
       Gib die entsprechenden Textstellen zusammengefasst wieder.
       Wenn keine Hinweise erkennbar sind, setze null. \n
    - contact_info: Prüfe, ob auf der Website klare institutionelle Kontakt- oder Impressumsangaben vorhanden sind. 
       Achte dabei auf: 
       E-Mail-Adressen (z. B. mit 'mailto:' oder '@'), 
       Physische Adressen (Straße, Hausnummer, Postleitzahl, Stadt, Land), 
       Links oder Hinweise zu Impressum oder Kontakt. 
       Gib alle gefundenen Informationen vollständig aus (z. B. Name, E-Mail, Adresse). 
       Wenn zusätzlich ein Link zu einer Kontakt- oder Impressumsseite vorhanden ist, gib beides aus – also die Kontaktangabe und den Hinweis 'Link mit Impressumsangaben oder Kontaktinformationen gefunden'. 
       Wenn keine direkte Kontaktangabe sichtbar ist, aber ein solcher Link existiert, gib nur diesen Hinweis aus. 
       Wenn weder Kontaktangaben noch ein solcher Link vorhanden sind, setze null.\n
    - community: Prüfe auf Hinweise auf Austauschmöglichkeiten (Forum, Mailingliste, soziale Medien).\n
    - documentation: Prüfe auf Links oder Textstellen, die auf eine methodische oder technische Dokumentation hinweisen, welche den Entstehungs- und Arbeitsprozess der Edition erläutert, einschließlich detaillierter Beschreibungen zu Editionsmethoden, editorischen Richtlinien, Abläufe zur Datenmodellierung und Arbeitsabläufen (z. B. Editorial Guidelines, Methodology, Technical Workflow, Encoding Policy, Developer or Project Documentation).\n
    - license: Prüfe auf Hinweise auf Lizenzangaben. Durchsuche die Seite nach offenen Lizenzhinweisen (z. B. CC-BY, CC0, MIT, Apache, GPL, BSD, EUPL) sowie nach proprietären oder geschlossenen Lizenzhinweisen (z. B. ©-Angaben, „Alle Rechte vorbehalten“, „proprietary“). Wenn keine Lizenz gefunden wurde, gib nichts dazu aus. Lass es komplett weg.\n
    - tei_hint:
       Gib eine kurze Zusammenfassung, ob und warum TEI-XML auf der Seite erkennbar ist.
       Berücksichtige dabei u. a.:
       Vorkommen von "TEI" oder "Text Encoding Initiative" im Text
       TEI-Hinweise in URL-Pfaden
       TEI/XML-Hinweise in Metadaten
       Links, die auf XML-Dateien oder TEI-Ansichten zeigen
       Der Wert soll immer eine kurze Erklärung sein wie:
       "TEI-Hinweis durch sdef:TEI-Links",
       "TEI über XML-Ansichten erkennbar".
       Wenn keinerlei TEI-Hinweise vorhanden sind, setze den Wert auf null (nicht als Text ausgeben).\n
    - api_hint: Ermittle, ob auf der Seite Hinweise auf APIs vorhanden sind.
       Durchsuche dafür die Linknamen, die Link-Texte, die Button-Beschriftungen, Menüeinträge,
       Hover-Texte, Titles und den gesamten restlichen Seiteninhalt (HTML, sichtbarer Text, Skripte, JSON-LD, Kommentare).
       Als Hinweis gelten sowohl direkte API-Links als auch indirekte UI- oder Text-Hinweise,
       z. B. die Begriffe "API", "REST", "OAI-PMH", "IIIF", "SPARQL", "GraphQL",
       "OpenAPI", "Swagger", "Endpoint", "Service", "Datenschnittstelle"
       sowie URL-Fragmente wie "/api", "/rest", "/oai", "/iiif", "/sparql", "/endpoint", "/service".
       Wichtig: Auch reine Link-Namen, Button-Texte oder UI-Bezeichnungen zählen als Hinweis,
       selbst wenn die dahinterliegende URL keine API-Struktur aufweist.
       Gib eine kurze Zusammenfassung der gefundenen Hinweise zurück.
       Wenn absolut keine Hinweise vorhanden sind, setze den Wert auf null
       (wirklich null, kein Text).\n
    - downloads_hint: Prüfe auf Hinweise darauf, dass Dateien, Software oder Datensätze heruntergeladen werden können. 
       Erkenne sowohl direkte Downloadlinks als auch jede sprachliche Formulierung, die den Download oder die Bereitstellung von Dateien beschreibt. 
       Wenn keinerlei Download-Hinweise vorhanden sind, setze den Wert auf null. \n
    - repositories_hint: Hinweise auf Quellcode- oder Daten-Repositories (z. B. GitHub, GitLab, Zenodo, institutionelle Repositorien).\n
    - normdata_hint: Prüfe auf Hinweise auf Normdaten oder Identifikatoren (z. B. GND, VIAF, Wikidata, ORCID, ISNI, CTS-URNs, Geonames).
       Erkenne sowohl sprachliche Erwähnungen (z. B. 'Normdatei') als auch strukturierte Normdaten in Links oder JSON-LD.
       Gib nur das wieder, was im HTML vorkommt:
       Wenn nur ein Begriff wie 'GND' erwähnt wird, gib dies als Hinweis aus (z. B. 'GND erwähnt').
       Achte auch auf Normdaten in strukturierten Formaten wie JSON-LD, insbesondere @id-Links zu Normdaten (z. B. d-nb.info/GND).\n
       Wenn eine echte Normdaten-ID oder ein Normdaten-Link vorkommt, darfst du diese ID oder URL ausgeben.
       Erfinde niemals IDs oder Normdaten — verwende nur exakt das, was sichtbar ist.
    - persistent_identifier_hint: Prüfe auf Hinweise auf persistente Identifier (z. B. DOI, Handle, ARK, URN, ORCID, ARXIV, CTS-URNs).\n
    - staticization_hint: Prüfe auf Hinweise darauf, dass die Website statisch erzeugt oder serverlos ausgeliefert wird.\n
    - isolation_hint: Prüfe auf Hinweise auf Containerisierung oder virtuelle Maschinen (z. B. Docker, Kubernetes, Virtualisierung, Sandbox, Cloud-Instanz).\n
    - open_source_hint: Prüfe auf Hinweise darauf, dass offene oder frei verfügbare Software genutzt wird oder die Seite auf quelloffener Technologie basiert.\n\n

    ### ⚖️ Richtlinien:\n
    1. Nutze nur Informationen, die im HTML oder in Metadaten tatsächlich vorhanden sind.\n
    2. Ziehe nur explizit belegte Schlussfolgerungen – keine Annahmen oder externes Wissen.\n
    3. Wenn ein Hinweis schwach, vage oder widersprüchlich ist, setze das Feld auf null.\n
    4. Wenn du ein Feld ausfüllst, gib immer **eine kurze Evidenz** an (max. 5–10 Wörter oder Textausschnitt), die aus dem HTML stammt.\n
    5. Alle nicht belegbaren Felder müssen explizit null sein.\n
    6. Gib **exakt ein valides JSON-Objekt** ohne Kommentare, Markdown oder Fließtext aus.\n\n

    ### Beispielausgabe:\n
    {
      "institution": "Universität zu Köln",
      "roles_responsibilities": null,
      "funding_information": "DFG 2018–2020",
      "continuation_strategy": null,
      "contact_info": "info@uni-koeln.de",
      "community": null,
      "documentation": null,
      "license": "CC BY 4.0",
      "tei_hint": "<TEI xmlns=...>",
      "api_hint": "OAI-PMH endpoint",
      "downloads_hint": "Download XML",
      "repositories_hint": "github.com/edition-project",
      "normdata_hint": "GND: 1234567-8",
      "structured_metadata_hint": "JSON-LD schema.org",
      "persistent_identifier_hint": "DOI:10.1234/example",
      "staticization_hint": null,
      "isolation_hint": null,
      "open_source_hint": "powered by open-Source Software"
    }
    """

    return LLMExtractionStrategy(
        llm_config=llm_config,
        extraction_type="json",
        schema=LLMAnalysis.model_json_schema(),
        input_format="html",
        instruction=instruction,
        apply_chunking=True,
        extra_args={
            "seed": 42,
            "temperature": float(temperature),
            "top_p": 0.1,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "max_tokens": int(max_tokens),
        },
        verbose=True,
    )


# --------------------------------------------------------------------
# 🔤 Encoding-Korrektur
# --------------------------------------------------------------------
def _fix_encoding(s: str) -> str:
    if s is None:
        return s
    s = s.strip()
    try:
        fixed = s.encode("latin1").decode("utf-8")
    except Exception:
        fixed = s
    replacements = {
        "Ã¼": "ü", "Ã¶": "ö", "Ã¤": "ä", "Ãß": "ß",
        "Ã": "Ö", "Ã": "Ä", "Ã": "Ü",
    }
    for bad, good in replacements.items():
        fixed = fixed.replace(bad, good)
    return fixed.strip()


def _normalize_types(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Säubert Encoding und konvertiert Listen zu Semikolon-getrennten Strings."""
    if not isinstance(obj, dict):
        return obj
    for k, v in list(obj.items()):
        if isinstance(v, list):
            obj[k] = "; ".join(str(x).strip() for x in v if str(x).strip()) or None
        elif isinstance(v, str):
            obj[k] = _fix_encoding(v)
    return obj


# --------------------------------------------------------------------
# 🧩 JSON-Extraktion & Merging
# --------------------------------------------------------------------
def _extract_json_objects(text: str) -> List[str]:
    """Finde alle JSON-Objekte im Text."""
    candidates, stack = [], []
    start_idx, in_str, str_char, escape = None, False, "", False
    for i, ch in enumerate(text):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == str_char:
                in_str = False
        else:
            if ch in ("'", '"'):
                in_str = True
                str_char = ch
            elif ch == "{":
                if not stack:
                    start_idx = i
                stack.append("{")
            elif ch == "}":
                if stack:
                    stack.pop()
                    if not stack and start_idx is not None:
                        candidates.append(text[start_idx:i + 1])
                        start_idx = None
    return candidates


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    expected_keys = set(LLMAnalysis.model_fields.keys())
    if "\\n" in text or '\\"' in text or "\\{" in text:
        try:
            text = bytes(text, "utf-8").decode("unicode_escape")
        except Exception:
            pass
    raw_candidates = _extract_json_objects(text)
    best_obj, best_score = None, (-1, -1)
    for cand in raw_candidates:
        try:
            obj = json.loads(cand)
            if not isinstance(obj, dict):
                continue
            key_hits = len(set(obj.keys()) & expected_keys)
            length = len(cand)
            if (key_hits, length) > best_score:
                best_obj, best_score = obj, (key_hits, length)
        except Exception:
            continue
    if best_obj:
        return _normalize_types(best_obj)
    return None


# --------------------------------------------------------------------
# 🧠 Merge-Funktion für mehrere Chunks
# --------------------------------------------------------------------
_ALL_FIELDS = list(LLMAnalysis.model_fields.keys())


def merge_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Führt mehrere Chunk-Ergebnisse zu einem duplikatfreien String-Feld zusammen."""
    print(f"[DEBUG] Starte Merging mit {len(results)} Ergebnissen")
    merged: Dict[str, Any] = {}
    seen_values: Dict[str, set] = {f: set() for f in _ALL_FIELDS}

    for r in results:
        if not isinstance(r, dict):
            continue
        r = _normalize_types(r)
        for f in _ALL_FIELDS:
            v = r.get(f)
            if isinstance(v, str) and v.strip():
                seen_values[f].add(v.strip())

    for f, vals in seen_values.items():
        if vals:
            merged[f] = "; ".join(sorted(vals, key=lambda x: x.lower()))

    print(f"[DEBUG] Ergebnis nach Merge: {json.dumps(merged, indent=2, ensure_ascii=False)}")
    return merged