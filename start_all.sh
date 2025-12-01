#!/bin/bash

set -e

PROJECT_ROOT="$(dirname "$(realpath "$0")")"
FUJI_PORT=1071
FASTAPI_PORT=8000

GREEN="\033[1;32m"
RED="\033[1;31m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
RESET="\033[0m"

echo -e "${BLUE}======================================================="
echo -e "🚀 STARTE ALLE DIENSTE (LIVE-AUSGABE)"
echo -e "=======================================================${RESET}"

echo -e "${BLUE}🛑 Stoppe alte Prozesse…${RESET}"

for proc in "uvicorn" "gunicorn" "playwright" "chromium" "chrome" "fuji_server"; do
    pkill -f "$proc" 2>/dev/null && \
        echo -e "   ${YELLOW}→ Prozess '$proc' beendet${RESET}" || true
done

sleep 1

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

echo ""
echo -e "${BLUE}🐟 Starte FUJI (falls vorhanden)…${RESET}"

FUJI_VENV="$PROJECT_ROOT/fuji/fuji-venv"

if [ -d "$FUJI_VENV" ]; then
    echo -e "   → FUJI erkannt"

    source "$FUJI_VENV/bin/activate"

    echo -e "${GREEN}--- FUJI START (LIVE) ---${RESET}"
    uvicorn fuji_server.main:app --host 127.0.0.1 --port $FUJI_PORT &
    FUJI_PID=$!

    deactivate
else
    echo -e "   ${YELLOW}FUJI nicht installiert${RESET}"
    FUJI_PID=""
fi


echo ""
echo -e "${BLUE}⚙️ Starte FastAPI…${RESET}"

source "$PROJECT_ROOT/venv/bin/activate"

echo -e "${GREEN}--- FASTAPI START (LIVE) ---${RESET}"
uvicorn app.main:app --reload --host 127.0.0.1 --port $FASTAPI_PORT

deactivate
