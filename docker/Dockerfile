# Упрощенный Dockerfile для локальной разработки
FROM python:3.11-slim-bookworm

# Установка системных зависимостей
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    python3-pip \
    python3-setuptools \
    && rm -rf /var/lib/apt/lists/* && \
    pip3 install --no-cache-dir certbot==2.1.0

# Установка рабочей директории
WORKDIR /app

# Копирование файла зависимостей
COPY requirements.txt /app/

# Установка Python зависимостей
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /app/requirements.txt

# Копирование исходного кода
COPY . /app/

# Команда по умолчанию
CMD ["python", "apps/web/main.py"]