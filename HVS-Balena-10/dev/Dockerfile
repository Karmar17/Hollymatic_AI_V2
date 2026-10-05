# Use the python:3.11.10-slim-bookworm base image
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV TZ=America/Los_Angeles

# Install dependencies and create the app user
# Instalar dependencias
RUN apt-get update && apt-get install -y --no-install-recommends\
       libopencv-dev python3-opencv v4l-utils \
       default-mysql-client default-libmysqlclient-dev gcc pkg-config \
       build-essential python3-dev \
       gcc \
       curl \
       unzip \
    && rm -rf /var/lib/apt/lists/* 

    

 RUN apt-get update && \
     apt-get install -y --no-install-recommends tzdata && \
     ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
     echo $TZ > /etc/timezone && \
     dpkg-reconfigure -f noninteractive tzdata && \
     apt-get clean && \
     rm -rf /var/lib/apt/lists/* \
     && useradd -m -u 1000 -s /bin/bash appuser

RUN pip install --upgrade pip

COPY requirements.txt /requirements.txt

RUN mkdir -p /home/appuser/.config/rclone  \
    && chown -R appuser:appuser /home/appuser

# Install Python dependencies using the requirements.txt file
RUN pip install --no-cache-dir -r /requirements.txt

RUN dpkg-reconfigure -f noninteractive tzdata

# Instala rclone (considera fijar una versión específica más adelante)
RUN curl -fsSL https://rclone.org/install.sh | bash

# Set the working directory inside the container
WORKDIR /app

# Copy the entire app/ folder into the container's /app directory
COPY --chown=appuser:appuser app/ /app/

# Copy credentials and confis inside the container
COPY --chown=appuser:appuser rclone.conf /home/appuser/.config/rclone/rclone.conf
COPY --chown=appuser:appuser secrets/ /secrets/

#asegurating have read permissions to app user to rclone configurations and secrets
RUN chown -R appuser:appuser /app /home/appuser/.config /secrets

# Credentials and configurations only have needed access (files 600, directories 700)
RUN chmod 600 /home/appuser/.config/rclone/rclone.conf \
&& find /secrets -type f -exec chmod 600 {} + \
&& find /secrets -type d -exec chmod 700 {} + \
&& chmod 700 /home/appuser/.config /home/appuser/.config/rclone

# Ensure the non-root user 'appuser' owns all the files in the /app directory and rclone config
RUN chown -R appuser:appuser /app 

# Ensure owner and group can modify the files
RUN chmod -R 775 /app 

RUN mkdir -p /app/images \
&& chmod -R 775 /app


# Add the app user to the video group
RUN usermod -aG video appuser

# Switch to the non-root user
USER appuser

# Run the main Python application as the non-root user from the new src/ directory
CMD ["python", "/app/main.py"]