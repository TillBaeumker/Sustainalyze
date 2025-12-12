# Sustainalyze

Automated sustainability analysis for digital scholarly editions.

Sustainalyze ist ein Web-Tool zur automatisierten Analyse von digitalen Editionen. Die Anwendung crawlt eine Website, sammelt technische und inhaltliche Hinweise auf digitale Nachhaltigkeit und erzeugt eine strukturierte Auswertung inklusive Bericht und LLM-gestützter Zusammenfassung. [web:2]

## Projektstruktur (Überblick)

Dieses Repository enthält den vollständigen Code des Prototyps *Sustainalyze*. Die wichtigsten Bereiche sind:

### 1. Anwendungscode (`app/`)
Hier befindet sich der gesamte **eigene Code** von Sustainalyze.

- **`modules/`**  
  Enthält die zentralen Funktionsbereiche der Anwendung:  
  - **analysis/** – alle selbst entwickelten Analyse-Module zur Datenextraktion  
    (Crawling, Link-Analyse, API-Erkennung, Shodan, Wappalyzer-Wrapper, FAIR-Checks, Repo-Analyse, LLM-Auswertung, Metadaten usw.)  
  - **manager/** – Orchestrierung der Analyseprozesse, Steuerung des Crawls und Aggregation der Ergebnisse  
  - **results/** – Module zur Berichtserstellung, Scoring-Logik und Heuristiken  

- **`utils/`**  
  Kleine Hilfsfunktionen, die modulübergreifend genutzt werden.

### 2. Frontend (`templates/` & `static/`)
- **`templates/`**  
  HTML-Templates für das Webfrontend (basierend auf einem HTML5-UP-Theme).  
- **`static/`**  
  CSS-, JavaScript- und Bilddateien für die Oberfläche.

### 3. Fremdmodule
- **`app/wappalyzer/`**  
  Enthält das vollständige Wappalyzer-Modul zur Technologieerkennung (Third-Party).
- **`fuji/`**  
  Vollständige Installation des FAIR-Checker-Tools FUJI (Third-Party), angebunden über die interne API.

### 4. Evaluation (`evaluation/`)
Enthält alle Skripte, Datensätze und Ergebnisse, die zur wissenschaftlichen Evaluation genutzt wurden  
(z. B. LLM-Reproduzierbarkeit, ISO-Tests, Linkstabilität, Structured-Metadata-Auswertung).

---

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
