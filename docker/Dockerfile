FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=60 \
    PIP_RETRIES=5 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://pypi.org/simple \
    PIP_EXTRA_INDEX_URL=https://mirror.yandex.ru/mirrors/pypi/simple

# Источники deb822 (без дублей)
RUN rm -f /etc/apt/sources.list && mkdir -p /etc/apt/sources.list.d

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

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc g++ libpq-dev libgeos-dev libproj-dev proj-bin curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

# Python зависимости
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /app/requirements.txt

# Код
COPY . /app

# Права и пользователь
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "main.py"]