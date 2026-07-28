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
     && useradd -ms /bin/bash app

RUN pip install --upgrade pip

COPY requirements.txt /requirements.txt

# Install Python dependencies using the requirements.txt file
RUN pip install --no-cache-dir -r /requirements.txt

RUN dpkg-reconfigure -f noninteractive tzdata

# Set the working directory inside the container
WORKDIR /app

# Copy the entire app/ folder into the container's /app directory
COPY app/ /app

# Copy the entire secrets/ folder into the container's /app directory
COPY secrets/ /secrets

# Ensure the non-root user 'app' owns all the files in the /app directory and rclone config
RUN chown -R app:app /app 

# Ensure owner and group can modify the files
RUN chmod -R 775 /app 


# Add the app user to the video group
RUN usermod -aG video app

# Switch to the non-root user
USER app

# Run the main Python application as the non-root user from the new src/ directory
CMD ["python", "/app/main.py"]
