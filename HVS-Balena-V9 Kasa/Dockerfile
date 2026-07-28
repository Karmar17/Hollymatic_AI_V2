# Usa una imagen base de balena con Python y herramientas de construcción.
FROM balenalib/raspberrypi4-64-debian-python:3.11-bookworm-build

# Establece variables de entorno. PYTHONUNBUFFERED es crucial para ver los logs en balena.
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Los_Angeles

# Instala dependencias del sistema en una sola capa para optimizar.
# Limpia la caché de apt en el mismo comando para reducir el tamaño de la imagen.
RUN apt-get update && apt-get install -y --no-install-recommends \
       # Dependencias para OpenCV y cámaras
       libopencv-dev \
       v4l-utils \
       default-mysql-client \
       default-libmysqlclient-dev \
       tzdata \
       rclone \
    && rm -rf /var/lib/apt/lists/*
    
# Configura la zona horaria del sistema.
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && dpkg-reconfigure -f noninteractive tzdata

# Establece el directorio de trabajo.
WORKDIR /app

# Actualiza pip a su última versión.
RUN pip install --upgrade pip

# Crea directorios necesarios globales
RUN mkdir -p /root/.config/rclone /app/captures /secrets

# Copia solo el archivo de requisitos primero para aprovechar la caché de Docker.
COPY requirements.txt .

# Instala las dependencias de Python.
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copia el resto del código de la aplicación.
COPY app/ /app/

# Copy credentials and configs inside the container
COPY rclone.conf /root/.config/rclone/rclone.conf
COPY secrets/ /secrets/

# Asegura permisos correctos
RUN chmod 600 /root/.config/rclone/rclone.conf \
    && find /secrets -type f -exec chmod 600 {} + \
    && find /secrets -type d -exec chmod 700 {} + \
    && chmod 700 /root/.config /root/.config/rclone \
    && chmod -R 755 /app \
    && chmod +x /app/start.sh

# Comando para ejecutar la aplicación como root.
# Se invoca con bash para no depender del bit de ejecucion del fichero.
CMD ["python", "./main.py"]
