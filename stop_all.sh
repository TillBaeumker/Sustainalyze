#!/bin/bash

echo "======================================================="
echo "🛑 Stoppe FUJI und FastAPI"
echo "======================================================="

FUJI_PORT=1071

# --------------------------------------------------------
# FUJI beenden
# --------------------------------------------------------
echo ""
echo "🔍 Beende FUJI (Port $FUJI_PORT)…"

FUJI_PIDS=$(lsof -ti :$FUJI_PORT 2>/dev/null)

if [ -n "$FUJI_PIDS" ]; then
    for pid in $FUJI_PIDS; do
        echo "→ Versuche FUJI (PID $pid) sanft zu beenden…"
        kill "$pid" 2>/dev/null
        sleep 0.5

        if ps -p "$pid" >/dev/null 2>&1; then
            echo "⚠️ Prozess $pid läuft noch – erzwinge Beendigung."
            kill -9 "$pid" 2>/dev/null
        fi

        if ! ps -p "$pid" >/dev/null 2>&1; then
            echo "✔️ FUJI-Prozess $pid gestoppt."
        else
            echo "❌ FUJI-Prozess $pid konnte NICHT beendet werden!"
        fi
    done
else
    echo "ℹ️ Kein laufender FUJI-Prozess gefunden."
fi


# --------------------------------------------------------
# FastAPI beenden
# --------------------------------------------------------
echo ""
echo "🔍 Beende FastAPI (uvicorn app.main:app)…"

FASTAPI_PIDS=$(pgrep -f "uvicorn app.main:app")

if [ -n "$FASTAPI_PIDS" ]; then
    for pid in $FASTAPI_PIDS; do
        echo "→ Versuche FastAPI (PID $pid) sanft zu beenden…"
        kill "$pid" 2>/dev/null
        sleep 0.5

        if ps -p "$pid" >/dev/null 2>&1; then
            echo "⚠️ Prozess $pid läuft noch – erzwinge Beendigung."
            kill -9 "$pid" 2>/dev/null
        fi

        if ! ps -p "$pid" >/dev/null 2>&1; then
            echo "✔️ FastAPI-Prozess $pid gestoppt."
        else
            echo "❌ FastAPI-Prozess $pid konnte NICHT beendet werden!"
        fi
    done
else
    echo "ℹ️ Kein laufender FastAPI-Prozess gefunden."
fi


# --------------------------------------------------------
# Port-Check
# --------------------------------------------------------
echo ""
echo "🔍 Prüfe Ports nach Stop …"

if lsof -ti :$FUJI_PORT >/dev/null; then
    echo "❌ FUJI-Port $FUJI_PORT ist NOCH belegt!"
else
    echo "✔️ FUJI-Port $FUJI_PORT ist jetzt frei."
fi

FASTAPI_LEFT=$(lsof -ti :8000 2>/dev/null)
if [ -n "$FASTAPI_LEFT" ]; then
    echo "❌ Port 8000 ist noch belegt (PID $FASTAPI_LEFT)."
else
    echo "✔️ Port 8000 ist jetzt frei."
fi


echo ""
echo "======================================================="
echo "🧹 Alle Dienste wurden beendet."
echo "======================================================="
echo ""
