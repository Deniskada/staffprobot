# Multi-stage build для оптимизации размера образа
FROM python:3.11-slim-bookworm as base

ENV DEBIAN_FRONTEND=noninteractive PIP_DISABLE_PIP_VERSION_CHECK=1

# Установка системных зависимостей для PostGIS и геоданных
# Переключаем источники apt на HTTPS и добавляем fallback-зеркало при недоступности deb.debian.org
# 1) Задаём deb822-источники (без дублей)
RUN rm -f /etc/apt/sources.list && \
    mkdir -p /etc/apt/sources.list.d

RUN cat <<'EOF' > /etc/apt/sources.list.d/debian.sources
Types: deb
URIs: https://mirror.yandex.ru/debian
Suites: bookworm bookworm-updates
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
EOF

RUN cat <<'EOF' > /etc/apt/sources.list.d/debian-security.sources
Types: deb
URIs: https://mirror.yandex.ru/debian-security
Suites: bookworm-security
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
EOF

# 2) Обновляем индексы и ставим зависимости
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      gcc g++ libpq-dev libgeos-dev libproj-dev proj-bin curl ca-certificates && \
    rm -rf /var/lib/apt/lists/* && apt-get clean

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


