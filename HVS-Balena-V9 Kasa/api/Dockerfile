# Imagen ligera para la API de calibracion remota (FastAPI + uvicorn).
# Base multiarch: construye nativo en x86 (dev) y en arm64 (balena/RPi4 prod).
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV TZ=America/Los_Angeles

# tzdata para que los timestamps de los logs salgan en hora local (igual patron que scheduler/Dockerfile).
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY run.py .
COPY src/ ./src/

# run.py levanta uvicorn con la configuracion pedida (proxy_headers, forwarded_allow_ips="*").
CMD ["python", "run.py"]
