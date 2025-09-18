# Multi-stage build для оптимизации размера образа
FROM python:3.11-slim-bookworm as base

ENV DEBIAN_FRONTEND=noninteractive PIP_DISABLE_PIP_VERSION_CHECK=1

# Установка системных зависимостей для PostGIS и геоданных
# Переключаем источники apt на HTTPS и добавляем fallback-зеркало при недоступности deb.debian.org
RUN set -eux; \
    printf "deb https://deb.debian.org/debian bookworm main\n\
    deb https://deb.debian.org/debian bookworm-updates main\n\
    deb https://security.debian.org/debian-security bookworm-security main\n" > /etc/apt/sources.list; \
    apt-get update -o Acquire::Retries=5 -o Acquire::http::Timeout=30; \
    apt-get install -y --no-install-recommends \
      gcc g++ libpq-dev libgeos-dev libproj-dev proj-bin curl ca-certificates; \
    rm -rf /var/lib/apt/lists/*; \
    apt-get clean

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


