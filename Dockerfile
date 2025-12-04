FROM python:3.12-slim

WORKDIR /app

# System libs für Playwright/Chromium etc.
RUN apt-get update && apt-get install -y \
    git curl wget unzip \
    libasound2t64 libatk1.0-0t64 libatk-bridge2.0-0t64 \
    libcups2t64 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libpango-1.0-0 libpangocairo-1.0-0 \
    libgtk-3-0t64 libnss3 libnspr4 libx11-xcb1 libxshmfence1 \
    fonts-liberation libu2f-udev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Playwright installieren (für Crawl4AI notwendig)
RUN pip install playwright && playwright install --with-deps chromium

# App-Code kopieren
COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
