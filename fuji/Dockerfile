FROM python:3.12-slim

WORKDIR /fuji

RUN apt-get update && apt-get install -y \
    libmagic1 \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --upgrade pip setuptools wheel \
    && pip install -e .

EXPOSE 1071

CMD ["python", "-m", "fuji_server", "-c", "fuji_server/config/server.ini"]
