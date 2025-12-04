FROM python:3.12-slim

WORKDIR /fuji

COPY . .

RUN pip install --upgrade pip && pip install -e .

EXPOSE 1071

CMD ["python", "-m", "fuji_server", "-c", "fuji_server/config/server.ini"]
