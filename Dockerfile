# ==================================================================
#   BASE IMAGE
# ==================================================================
FROM python:3.12-slim

WORKDIR /app

RUN echo 'APT::Sandbox::User "root";' >/etc/apt/apt.conf

# ==================================================================
#   SYSTEM DEPENDENCIES + CHROMIUM (WICHTIG!!!)
# ==================================================================
RUN apt-get update && apt-get install -y \
    git curl wget unzip \
    nodejs npm \
    chromium \
    libasound2 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libpango-1.0-0 libpangocairo-1.0-0 \
    libgtk-3-0 libnss3 libnspr4 libx11-xcb1 libxshmfence1 \
    libxss1 libglib2.0-0 libxext6 libxfixes3 \
    libxcursor1 libxi6 libxrender1 libxtst6 \
    fonts-liberation ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV PUPPETEER_ARGS="--no-sandbox --disable-setuid-sandbox"

# ==================================================================
#   PYTHON DEPENDENCIES
# ==================================================================
COPY requirements.txt ./ 
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# ==================================================================
#   PLAYWRIGHT (für dein Crawling)
# ==================================================================
RUN playwright install chromium

# ==================================================================
#   COPY CODE
# ==================================================================
COPY . /app

# ==================================================================
#   WAPPALYZER INSTALLATION (yarn + puppeteer)
# ==================================================================
RUN npm install --global yarn \
    && cd /app/app/wappalyzer \
    && yarn install --ignore-engines --no-lockfile \
    && npm install puppeteer --legacy-peer-deps \
    && yarn build || true

# ==================================================================
#   STARTUP COMMAND
# ==================================================================
CMD sh -c "cd /app/app/wappalyzer && \
           PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium \
           yarn start --no-sandbox --disable-setuid-sandbox & \
           uvicorn app.main:app --host 0.0.0.0 --port 8000"
