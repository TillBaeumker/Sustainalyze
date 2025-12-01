#!/usr/bin/env bash
set -euo pipefail

echo
echo "=============================================================="
echo "🚀 Starte Sustainalyze Setup"
echo "=============================================================="
echo

cd "$(dirname "$0")"
PROJECT_ROOT="$(pwd)"
echo "📁 Projektverzeichnis: $PROJECT_ROOT"
echo

# ------------------------------------------------------------
# 1) Sicherstellen, dass Python 3.12 installiert ist
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
# 3) Node.js + Yarn installieren
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
# 4) Python venv neu erstellen
# ------------------------------------------------------------

echo "==> Baue Python venv..."

rm -rf venv
$PY -m venv venv
source venv/bin/activate

pip install --upgrade pip setuptools wheel

echo "📦 Installiere requirements.txt…"
pip install -r "$PROJECT_ROOT/requirements.txt"

deactivate

echo "✔ Python venv OK"
echo

# ------------------------------------------------------------
# 5) FUJI vorbereiten
# ------------------------------------------------------------

echo "==> FUJI vorbereiten..."

if [ -d fuji ]; then
    cd fuji
    rm -rf fuji-venv
    $PY -m venv fuji-venv
    source fuji-venv/bin/activate
    pip install --upgrade pip setuptools wheel
    deactivate
    cd "$PROJECT_ROOT"
else
    echo "⚠️ Warnung: Ordner 'fuji' fehlt!"
fi

echo "✔ FUJI OK"
echo

# ------------------------------------------------------------
# 6) Wappalyzer installieren
# ------------------------------------------------------------

echo "==> Wappalyzer installieren..."

if [ ! -d wappalyzer ]; then
    git clone https://github.com/tomnomnom/wappalyzer.git wappalyzer
fi

cd wappalyzer
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
    echo "⚠️ Chromium NICHT gefunden!"
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
