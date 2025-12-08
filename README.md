# Sustainalyze

Automated sustainability analysis for digital scholarly editions.  
Sustainalyze crawls, evaluates and summarizes edition-websites using repository data, semantic metadata, external dataset analysis via FUJI, LLM-based summaries, and more.

## 🚀 Schnellstart (mit Docker)

Voraussetzungen:  
- Docker & Docker Compose (lokal installiert)  
- Ein .env mit API-Keys (optional, aber empfohlen)

```bash
git clone https://github.com/TillBaeumker/Sustainalyze.git  
cd Sustainalyze  
cp .env.example .env            # Environment-Variablen konfigurieren  
docker compose up               # startet alle Services: FUJI, Wappalyzer, App  
```

Dann im Browser öffnen: `http://localhost:8000`

---

## 🔧 Optional: Entwicklung lokal (ohne Docker)

Wenn du lokal entwickeln willst, kannst du — je nach Bedarf — deine alten Setup-Skripte nutzen. Diese sind **nicht** für Produktions-Deploy gedacht.

---

## 📁 Repository Struktur

- `app/` — Hauptcode der Anwendung (FastAPI, Web-Front, Modules…)  
- `fuji/` — FUJI-Service als Docker-Subprojekt  
- `wappalyzer/` — Wappalyzer als Docker-Subprojekt  
- `docker-compose.yml` — definiert Zusammenspiel aller Dienste  
- `.env.example` — Template für Umgebungsvariablen (API-Keys etc.)  
- `requirements.txt` — Python-Abhängigkeiten  

---

## 🛑 Wichtige Hinweise

- **Nicht** committen: `.env`, `venv/`, Node-Modules, Download-Ordner, temporäre Files  
- Verwende `.env.example` als Vorlage für Konfiguration  
- Wenn du Dummy-API-Keys nutzt: Die App startet, aber externe Dienste funktionieren ggf. nicht  

---

## 📝 Weiterentwickeln

Wenn du neue Funktionen entwickelst:  
- Code in `app/` ändern  
- (Optional) `docker compose up --build` ausführen  
- Änderungen testen  

---

## 📄 Lizenz

MIT License — siehe `LICENSE`
