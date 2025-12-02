#!/usr/bin/env bash
set -euo pipefail

echo
echo "=============================================================="
echo "🚀 Starte Sustainalyze Setup (lokale FUJI + Wappalyzer)"
echo "=============================================================="
echo

# Stelle sicher, dass wir im Projekt root sind
cd "$(dirname "$0")"
PROJECT_ROOT="$(pwd)"
echo "📁 Projektverzeichnis: $PROJECT_ROOT"
echo

# ------------------------------------------------------------
# 1) Python 3.12 sicherstellen
# ------------------------------------------------------------
if command -v python3.12 &>/dev/null; then
    PY=python3.12
else
    echo "⚠️ Python 3.12 NICHT gefunden – installiere..."
    sudo apt-get update -y
    sudo apt-get install -y python3.12 python3.12-venv
    PY=python3.12
fi

echo "✔ Python gefunden: $($PY --version)"
echo

# ------------------------------------------------------------
# 2) Systempakete installieren
# ------------------------------------------------------------
echo "==> Installiere Systempakete..."
sudo apt-get install -y \
    git curl wget unzip \
    libasound2t64 libatk1.0-0t64 libatk-bridge2.0-0t64 \
    libcups2t64 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libpango-1.0-0 libpangocairo-1.0-0 \
    libgtk-3-0t64 libnss3 libnspr4 libx11-xcb1 libxshmfence1 \
    fonts-liberation libu2f-udev ca-certificates
echo "✔ Systempakete OK"
echo

# ------------------------------------------------------------
# 3) Node.js + Yarn sicherstellen
# ------------------------------------------------------------
echo "==> Prüfe Node.js"
if ! command -v node &>/dev/null; then
    echo "📦 Installiere Node.js 20.x"
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

echo "Node: $(node -v)"
echo "npm:  $(npm -v)"

if ! command -v yarn &>/dev/null; then
    sudo npm install -g yarn
fi
echo "Yarn: $(yarn -v)"
echo

# ------------------------------------------------------------
# 4) Python venv + Dependencies
# ------------------------------------------------------------
echo "==> Baue Python venv..."

rm -rf venv
$PY -m venv venv
source venv/bin/activate

pip install --upgrade pip setuptools wheel

echo "📦 Installiere requirements.txt…"
pip install -r "$PROJECT_ROOT/requirements.txt"

echo "📦 Installiere FUJI lokal..."
pip install -e "$PROJECT_ROOT/fuji"

echo "📦 Installiere Crawl4AI (erneut sicherheitshalber)..."
pip install crawl4ai

deactivate

echo "✔ Python venv OK"
echo

# ------------------------------------------------------------
# 5) FUJI prüfen
# ------------------------------------------------------------
echo "==> Prüfe FUJI..."

if [ -d "$PROJECT_ROOT/fuji" ]; then
    echo "✔ Lokaler FUJI-Ordner gefunden"
else
    echo "❌ FEHLER: Ordner 'fuji/' fehlt!"
    exit 1
fi

# Prüfe Konfiguration
if [ ! -f "$PROJECT_ROOT/fuji/fuji_server/config/server.ini" ]; then
    echo "⚠️ WARNUNG: FUJI-Konfiguration fehlt (server.ini)"
    echo "    Bitte server.ini hinzufügen, sonst startet FUJI nicht."
fi

echo "✔ FUJI OK"
echo

# ------------------------------------------------------------
# 6) Wappalyzer lokal installieren
# ------------------------------------------------------------
echo "==> Wappalyzer installieren…"

if [ ! -d "$PROJECT_ROOT/wappalyzer" ]; then
    echo "❌ FEHLER: Ordner 'wappalyzer/' fehlt!"
    echo "Bitte Repository vollständig klonen."
    exit 1
fi

cd "$PROJECT_ROOT/wappalyzer"

# Entferne kaputte yarn.lock
rm -f yarn.lock

# Installiere Node-Abhängigkeiten
yarn install --ignore-engines

cd "$PROJECT_ROOT"

echo "✔ Wappalyzer OK"
echo

# ------------------------------------------------------------
# 7) Chromium prüfen
# ------------------------------------------------------------
CHROME_PATH="$(command -v chromium-browser || command -v chromium || true)"
if [[ -n "$CHROME_PATH" ]]; then
    echo "✔ Chromium gefunden: $CHROME_PATH"
else
    echo "⚠️ Chromium NICHT gefunden! (Playwright nutzt dann eigenen Build)"
fi

echo
echo "=============================================================="
echo "🎉 Setup abgeschlossen – Sustainalyze ist bereit!"
echo "=============================================================="
echo
echo "Nächste Schritte:"
echo "  1) cp .env.example .env"
echo "  2) nano .env → API Keys eintragen"
echo "  3) ./start_all.sh"
echo
echo "Fertig! 🚀"
