# Sustainalyze

Automated sustainability analysis for digital scholarly editions.

Sustainalyze ist ein Web-Tool zur automatisierten Analyse digitaler Editionen. Die Anwendung crawlt eine Website, sammelt technische und inhaltliche Evidenzen für digitale Nachhaltigkeit und erzeugt eine strukturierte Auswertung inklusive Bericht und LLM-gestützter Zusammenfassung.

## Projektstruktur (Überblick)

Dieses Repository enthält den vollständigen Code des Prototyps *Sustainalyze*.  
Die wichtigsten Bereiche sind:

### 1. Anwendungscode (`app/`)

- **`modules/`**  
  Zentrale Funktionsbereiche der Anwendung:  
  - **`analysis/`** – selbst entwickelte Analyse-Module zur Datenextraktion  
  - **`manager/`** – Orchestrierung der Analyseprozesse, Steuerung des Crawls und Aggregation der Ergebnisse  
  - **`results/`** – Module zur Berichtserstellung, Scoring-Logik und Heuristiken  

- **`templates/`**  
  HTML-Templates für das Webfrontend (basierend auf einem HTML5-UP-Theme).

- **`static/`**  
  CSS-, JavaScript- und Bilddateien für die Oberfläche (basierend auf einem HTML5-UP-Theme).

### 2. Fremdmodule

- **`app/wappalyzer/`**  
  Enthält das vollständige Wappalyzer-Modul zur Technologieerkennung (Third-Party).

- **`fuji/`**  
  Vollständige Installation des FAIR-Checker-Tools FUJI (Third-Party).

### 3. Evaluation (`evaluation/`)

Enthält Skripte und Rohdaten der wissenschaftlichen Evaluation  
(z. B. Untersuchungen zur Konsistenz von LLM-Ausgaben, Tests zur korrekten Technologieerkennung, Analysen der Linkstabilität sowie Auswertungen strukturierter Metadaten).

---

## Installation und Ausführung (Docker)

### Systemvoraussetzungen

Sustainalyze läuft vollständig in Docker-Containern.  

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

### 🔑 Hinweise zu benötigten API-Keys

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
  Diese Variablen dienen ausschließlich dazu, FUJI bei technisch abgesicherten Endpunkten (z. B. Basic Auth) anzusprechen.  

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


