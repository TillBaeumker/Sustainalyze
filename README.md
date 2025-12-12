# Sustainalyze

Automated sustainability analysis for digital scholarly editions.

Sustainalyze ist ein Web-Tool zur automatisierten Analyse digitaler Editionen. Die Anwendung crawlt eine Website, sammelt technische und inhaltliche Evidenzen für digitale Nachhaltigkeit und erzeugt eine strukturierte Auswertung inklusive Bericht und LLM-gestützter Zusammenfassung.

## Projektstruktur (Überblick)

Dieses Repository enthält den vollständigen Code des Prototyps *Sustainalyze*. Die wichtigsten Bereiche sind:

### 1. Anwendungscode (`app/`)
Dieses Repository enthält den vollständigen Code des Prototyps Sustainalyze. Die wichtigsten Bereiche sind:

- **`modules/`**  
  Enthält die zentralen Funktionsbereiche der Anwendung:  
  - **analysis/** – alle selbst entwickelten Analyse-Module zur Datenextraktion   
  - **manager/** – Orchestrierung der Analyseprozesse, Steuerung des Crawls und Aggregation der Ergebnisse  
  - **results/** – Module zur Berichtserstellung, Scoring-Logik und Heuristiken  

### 2. Frontend (`templates/` & `static/`)
- **`templates/`**  
  HTML-Templates für das Webfrontend (basierend auf einem HTML5-UP-Theme).  
- **`static/`**  
  CSS-, JavaScript- und Bilddateien für die Oberfläche (basierend auf einem HTML5-UP-Theme).

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

## Systemvoraussetzungen

Sustainalyze läuft vollständig in Docker-Containern.  
Es müssen daher **keine zusätzlichen Python-, Node- oder Playwright-Installationen** lokal vorgenommen werden.

### Windows
- **Docker Desktop**
- **WSL 2 (Windows Subsystem for Linux)**  
  (Docker Desktop richtet WSL 2 automatisch ein.)

### macOS
- **Docker Desktop**  
  Keine weiteren Anforderungen.

### Linux
- **Docker Engine**
- **Docker Compose**

### weitere Voraussetzungen
- `.env` mit optionalen API-Keys

<<<<<<< HEAD
#### 🔑 Hinweise zu benötigten API-Keys
=======
### 🔑 Hinweise zu benötigten API-Keys
>>>>>>> 05a25e5 (Update project)

Für den Betrieb von Sustainalyze werden einige optionale API-Keys unterstützt. Die Anwendung funktioniert grundsätzlich auch ohne diese, allerdings stehen dann bestimmte Analysefunktionen nicht zur Verfügung.

- **OpenAI (`OPENAI_API_KEY`) – erforderlich für LLM-gestützte Zusammenfassungen**  
  Ohne diesen Key wird keine automatische Bewertung oder LLM-Zusammenfassung erzeugt.

- **Shodan (`SHODAN_API_KEY`) – optional**  
  Aktiviert sicherheitsrelevante Abfragen zur Serverkonfiguration und offenen Ports.  
  Ohne Key wird dieser Teil der Analyse übersprungen.

- **GitHub / GitLab (`GITHUB_API_TOKEN`, `GITLAB_API_TOKEN`) – optional**  
  Erlaubt erweiterte Repository-Analysen wie Lizenzprüfung, letzte Commits, Contributor-Zahlen etc.  
  Ohne Tokens erfolgt nur eine rudimentäre Link-Erkennung.

- **FUJI (`FUJI_USERNAME`, `FUJI_PASSWORD`) – optional, Standard = leer**  
  Diese Variablen dienen ausschließlich dazu, FUJI in Umgebungen mit Authentifizierung anzusprechen.  
<<<<<<< HEAD
  
=======
  Die mitgelieferte lokale FUJI-Installation benötigt **keine Zugangsdaten**.  
  Die Platzhalter sind nur aus Gründen der Dokumentation vorhanden.

>>>>>>> 05a25e5 (Update project)
Sustainalyze lädt keine API-Keys mit Git aus; du musst Werte ausschließlich lokal in der `.env` eintragen.

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


