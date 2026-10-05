# Imagen ligera para el agendador (apagado del KP200, limpieza y reporte de KPIs).
# Base multiarch: construye nativo en x86 (dev) y en arm64 (balena/RPi4 prod).
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV TZ=America/Los_Angeles

# tzdata para que el cron de APScheduler dispare en hora local correcta (igual que el Dockerfile principal).
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY src/ ./src/
COPY main.py .
COPY tests/ ./tests/
COPY secrets/ ./secrets/



CMD ["python", "./main.py"]
