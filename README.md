# Sustainalyze

Automated sustainability analysis for digital scholarly editions.

Sustainalyze crawls and evaluates edition websites. Sustainalyze ist ein Web-Tool zur automatisierten Analyse von Webauftritten mit Fokus auf digitale Editionen. Die Anwendung crawlt eine Website, sammelt technische und inhaltliche Hinweise auf digitale Nachhaltigkeit und erzeugt eine strukturierte Auswertung inklusive Bericht und LLM-gestützter Zusammenfassung. [web:2]

## Projektstruktur (Überblick)

Dieses Repository enthält den vollständigen Code des Prototyps *Sustainalyze*. Die wichtigsten Bereiche sind:

### `app/` – Hauptanwendung
Hier befindet sich der gesamte **eigene Code** des Projekts.

- **`modules/`**  
  Kern der Anwendung: alle Analysekomponenten wie  
  Crawling, Link-Analyse, API-Erkennung, Download-Detector, Shodan-Check, FAIR-Checker-Anbindung, Wappalyzer-Wrapper, Repository-Analyse, LLM-Auswertung, Metadatenextraktion etc.

- **`manager/`**  
  Steuert den Crawl-Ablauf, aggregiert Ergebnisse und erzeugt strukturierte Output-Daten.

- **`templates/`**  
  HTML-Templates des Frontends (HTML5 UP Theme).

- **`static/`**  
  CSS-, JS-Dateien und Assets für das Webfrontend.

- **`utils/`**  
  Hilfsfunktionen, die modulübergreifend genutzt werden.

### `evaluation/` – Evaluationscode
Enthält alle Skripte, Datensätze und Ergebnisse (z. B. LLM-Reproduzierbarkeit, ISO-Statistiken, Linkstabilität, Structured-Data-Extraktion), die zur **wissenschaftlichen Evaluation** genutzt wurden.

### `fuji/` – FUJI FAIR-Checker (Third-Party)
Eine vollständige Kopie der FAIR-Checker-Software, lokal einsetzbar und über eine API in den Prototyp integriert.

### `app/wappalyzer/` – Wappalyzer (Third-Party)
Enthält die Technologie-Datenbank und die notwendige Logik zur Technologieerkennung auf Webseiten.

## Schnellstart (Docker)

### Voraussetzungen
- Docker
- Docker Compose
- `.env` mit optionalen API-Keys

### Installation & Start

```bash
git clone https://github.com/TillBaeumker/Sustainalyze.git
cd Sustainalyze
cp .env.example .env      # Werte anpassen
docker compose up --build
```

### Browser öffnen

Gehe zu: [http://localhost:8000](http://localhost:8000)

Alle Services starten automatisch.

## Weiterentwickeln

1. Code in `app/` ändern
2. `docker compose up --build` ausführen, wenn nötig
3. Testen im Browser

## Lizenz

Dieses Projekt steht unter der **MIT-License** (siehe `LICENSE`).

Bitte beachte: Das Repository enthält zusätzlich Komponenten von Drittanbietern. Diese Teile stehen **nicht** unter der MIT-Lizenz, sondern unter den jeweiligen Original-Lizenzen der Projekte. Die MIT-Lizenz gilt ausschließlich für den eigenen Code von Till in diesem Repository.

---

### Enthaltene Dritt-Lizenzen

#### Wappalyzer
- Der Ordner `app/wappalyzer` enthält Code und Daten aus dem Projekt *Wappalyzer*
- Der enthaltene Code unterliegt den Lizenzbedingungen des ursprünglichen Projekts
- Siehe die Lizenzen im Verzeichnis `app/wappalyzer/`

#### HTML5 UP Template
- Das Frontend basiert auf einem Template von *HTML5 UP*
- Das Template unterliegt der ursprünglichen Lizenz von HTML5 UP
- Attribution gemäß Lizenz erfolgt im Footer

---

Weitere verwendete Assets oder Bibliotheken behalten jeweils ihre eigene Lizenz. Falls du fremden Code weiterverwendest, modifizierst, veröffentlichst oder weitergibst, musst du die Bedingungen der ursprünglichen Lizenz einhalten.
