# Sustainalyze

Automated sustainability analysis for digital scholarly editions.

Sustainalyze crawls and evaluates edition websites. Es nutzt Repository-Daten, semantische Metadaten, FAIR-Dataset-Analysen über FUJI und LLM-basierte Zusammenfassungen.

## 🚀 Schnellstart (Docker)

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

Alle Services starten automatisch (FUJI, Wappalyzer, App).

## 🔧 Lokale Entwicklung (ohne Docker)
Optional für Entwicklung oder Experimente.
*Nicht für Produktion gedacht.*

## 📁 Struktur

- **`app/`** – FastAPI-Code, Frontend, Module
- **`fuji/`** – FUJI-Dienst
- **`wappalyzer/`** – Wappalyzer-Dienst
- **`docker-compose.yml`** – Services Definition
- **`.env.example`** – Template für Umgebungsvariablen
- **`requirements.txt`** – Python-Abhängigkeiten

## ⚠ Hinweise

- **Nicht committen:** `.env`, `venv/`, `node_modules`, Download-Ordner
- `.env.example` als Vorlage verwenden
- Dummy-Keys erlauben den Start, deaktivieren aber externe Services (z.B. LLM-API)

## 🧪 Weiterentwickeln

1. Code in `app/` ändern
2. `docker compose up --build` ausführen, wenn nötig
3. Testen im Browser

## 📄 Lizenz
MIT – siehe `LICENSE` Datei.
