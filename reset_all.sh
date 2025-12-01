#!/bin/bash

echo "🔧 Beende alle relevanten Prozesse …"

# FastAPI / Uvicorn / Gunicorn
pkill -f uvicorn 2>/dev/null
pkill -f gunicorn 2>/dev/null

# Python-Skripte (Crawler, FUJI, Shodan, Wappalyzer-Aufrufe)
pkill -f python 2>/dev/null

# Node-basierte Tools (Wappalyzer, Playwright Driver)
pkill -f node 2>/dev/null

# Playwright / Browser / Chromium
pkill -f playwright 2>/dev/null
pkill -f chromium 2>/dev/null
pkill -f chrome 2>/dev/null

# FUJI (falls als Server gestartet)
pkill -f fuji 2>/dev/null

# Andere mögliche Hintergrundprozesse
pkill -f uvicorn 2>/dev/null
pkill -f gunicorn 2>/dev/null
pkill -f "selenium" 2>/dev/null

# Netzwerk-Tools / Tunnels
pkill -f ssh 2>/dev/null

echo "🧹 Alles beendet. Umgebung ist komplett sauber."
