# Sustainalyze

Automated sustainability analysis for digital scholarly editions.

Sustainalyze crawls and evaluates edition websites. Sustainalyze ist ein Web-Tool zur automatisierten Analyse von Webauftritten mit Fokus auf digitale Editionen Die Anwendung crawlt eine Website, sammelt technische und inhaltliche Hinweise auf digitale Nachhaltigkeit und erzeugt eine strukturierte Auswertung inklusive Bericht und LLM-gestützter Zusammenfassung.


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

Alle Services starten automatisch.

## 🧪 Weiterentwickeln

1. Code in `app/` ändern
2. `docker compose up --build` ausführen, wenn nötig
3. Testen im Browser

## 📄 Lizenz
MIT – siehe `LICENSE` Datei.
