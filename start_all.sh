#!/bin/bash

set -e

############################################################
#   Farben
############################################################
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
RED="\033[1;31m"
RESET="\033[0m"

############################################################
#   Variablen
############################################################
PROJECT_ROOT="$(dirname "$(realpath "$0")")"
FUJI_MAIN="$PROJECT_ROOT/fuji/fuji_server/__main__.py"
FUJI_CONFIG="$PROJECT_ROOT/fuji/fuji_server/config/server.ini"

FUJI_PORT=1071
FASTAPI_PORT=8000

############################################################
echo -e "${BLUE}======================================================="
echo -e "🚀 STARTE ALLE DIENSTE (LIVE-AUSGABE)"
echo -e "=======================================================${RESET}"


############################################################
#   Alte Prozesse stoppen
############################################################
echo -e "${BLUE}🛑 Stoppe alte Prozesse…${RESET}"

for proc in "uvicorn" "gunicorn" "playwright" "chromium" "chrome" "fuji_server" "python.*fuji_server"; do
    pkill -f "$proc" 2>/dev/null && \
        echo -e "   ${YELLOW}→ Prozess '$proc' beendet${RESET}" || true
done

sleep 1


############################################################
#   Ports prüfen
############################################################
echo ""
echo -e "${BLUE}🧹 Prüfe Ports…${RESET}"

for port in $FUJI_PORT $FASTAPI_PORT; do
    if lsof -ti:$port >/dev/null; then
        echo -e "   ${YELLOW}→ Port $port belegt. Prozess wird beendet.${RESET}"
        kill -9 "$(lsof -ti:$port)" 2>/dev/null || true
    else
        echo -e "   ${GREEN}→ Port $port frei${RESET}"
    fi
done


############################################################
#   FUJI prüfen
############################################################
echo ""
echo -e "${BLUE}🐟 Starte FUJI…${RESET}"

if [ ! -f "$FUJI_MAIN" ]; then
    echo -e "${RED}❌ FUJI wurde nicht gefunden!${RESET}"
    echo -e "   Erwartet an:"
    echo -e "   $FUJI_MAIN"
    exit 1
fi

if [ ! -f "$FUJI_CONFIG" ]; then
    echo -e "${RED}❌ FUJI Config nicht gefunden!${RESET}"
    echo -e "   Erwartet an:"
    echo -e "   $FUJI_CONFIG"
    exit 1
fi

echo -e "   → FUJI-Skript gefunden"
echo -e "   → FUJI-Konfiguration: $FUJI_CONFIG"
echo -e "${GREEN}--- FUJI START (LIVE) ---${RESET}"

python3 "$FUJI_MAIN" -c "$FUJI_CONFIG" &
FUJI_PID=$!

sleep 2


############################################################
#   FastAPI starten
############################################################
echo ""
echo -e "${BLUE}⚙️ Starte FastAPI…${RESET}"

# Deine virtuelle Umgebung aktivieren
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
else
    echo -e "${YELLOW}⚠️ Keine venv gefunden! Starte ohne virtuelle Umgebung.${RESET}"
fi

echo -e "${GREEN}--- FASTAPI START (LIVE) ---${RESET}"
uvicorn app.main:app --reload --host 127.0.0.1 --port $FASTAPI_PORT

# Nach dem Stoppen:
deactivate 2>/dev/null || true
