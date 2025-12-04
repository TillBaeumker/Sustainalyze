#!/bin/bash

set -e

############################################################
#   Umgebungsvariablen für Docker-Wappalyzer
############################################################
export USE_WAPPALYZER_DOCKER=true
export WAPPALYZER_CONTAINER=wappalyzer

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
FUJI_PORT=1071
FASTAPI_PORT=8000

echo -e "${BLUE}======================================================="
echo -e "🚀 STARTE ALLE DIENSTE (LIVE-AUSGABE)"
echo -e "=======================================================${RESET}"


############################################################
#   Alte Prozesse stoppen (aber nicht Docker-FUJI!)
############################################################
echo -e "${BLUE}🛑 Stoppe alte Prozesse…${RESET}"

for proc in "uvicorn" "gunicorn" "playwright" "chromium" "chrome"; do
    if pkill -f "$proc" 2>/dev/null; then
        echo -e "   ${YELLOW}→ Prozess '$proc' beendet${RESET}"
    fi
done

sleep 1


############################################################
#   Ports prüfen (nur FastAPI-Port)
############################################################
echo ""
echo -e "${BLUE}🧹 Prüfe Ports…${RESET}"

if lsof -ti:$FASTAPI_PORT >/dev/null; then
    echo -e "   ${YELLOW}→ Port $FASTAPI_PORT belegt. Prozess wird beendet.${RESET}"
    kill -9 "$(lsof -ti:$FASTAPI_PORT)" 2>/dev/null || true
else
    echo -e "   ${GREEN}→ Port $FASTAPI_PORT frei${RESET}"
fi

echo -e "   ${GREEN}→ FUJI-Port $FUJI_PORT wird von Docker verwaltet${RESET}"


############################################################
#   FUJI im Docker prüfen/starten
############################################################
echo ""
echo -e "${BLUE}🐟 Prüfe FUJI im Docker…${RESET}"

if docker ps --format '{{.Names}}' | grep -q "^fuji$"; then
    echo -e "   ${GREEN}✔ FUJI läuft bereits im Container${RESET}"
else
    echo -e "   ${YELLOW}→ Starte FUJI-Container…${RESET}"
    docker start fuji
    sleep 2
fi


############################################################
#   Wappalyzer im Docker prüfen/starten
############################################################
echo ""
echo -e "${BLUE}🧪 Prüfe Wappalyzer im Docker…${RESET}"

if docker ps --format '{{.Names}}' | grep -q "^wappalyzer$"; then
    echo -e "   ${GREEN}✔ Wappalyzer läuft bereits im Container${RESET}"
else
    echo -e "   ${YELLOW}→ Starte Wappalyzer-Container…${RESET}"
    docker start wappalyzer
    sleep 2
fi


############################################################
#   FastAPI starten
############################################################
echo ""
echo -e "${BLUE}⚙️ Starte FastAPI…${RESET}"

# venv aktivieren
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    echo -e "${GREEN}→ Aktiviere virtuelle Umgebung${RESET}"
    source "$PROJECT_ROOT/venv/bin/activate"
else
    echo -e "${YELLOW}⚠️ Keine venv gefunden! Starte ohne virtuelle Umgebung.${RESET}"
fi

echo -e "${GREEN}--- FASTAPI START (LIVE) ---${RESET}"
uvicorn app.main:app --reload --host 127.0.0.1 --port $FASTAPI_PORT

# Nach dem Stoppen:
deactivate 2>/dev/null || true
