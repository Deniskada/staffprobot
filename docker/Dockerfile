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
    certbot \
    python3-certbot \
    && rm -rf /var/lib/apt/lists/*

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