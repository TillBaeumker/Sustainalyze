#!/bin/bash

echo "🔍 Status der laufenden Prozesse"

# Prüfe FUJI (Port 1071)
FUJI_PID=$(lsof -ti :1071)
if [ -n "$FUJI_PID" ]; then
    echo "✔️ FUJI läuft (Port 1071, PID $FUJI_PID)"
else
    echo "❌ FUJI läuft nicht (Port 1071 frei)"
fi

# Prüfe FastAPI (Uvicorn)
FASTAPI_PID=$(pgrep -f "uvicorn app.main:app")
if [ -n "$FASTAPI_PID" ]; then
    FASTAPI_PORT=$(lsof -Pan -p "$FASTAPI_PID" -i | grep LISTEN | awk '{print $9}' | cut -d':' -f2)
    echo "✔️ FastAPI läuft (PID $FASTAPI_PID, Port $FASTAPI_PORT)"
else
    echo "❌ FastAPI läuft nicht"
fi
