# Multi-stage build для оптимизации размера образа
FROM python:3.11-slim as base

# Установка системных зависимостей для PostGIS и геоданных
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libgeos-dev \
    libproj-dev \
    proj-bin \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Создание пользователя для безопасности
RUN useradd --create-home --shell /bin/bash app

# Установка Python зависимостей
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Копирование кода приложения
COPY . /app
WORKDIR /app

# Установка прав доступа
RUN chown -R app:app /app
USER app

# Проверка здоровья приложения
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Команда по умолчанию
CMD ["python", "main.py"]


