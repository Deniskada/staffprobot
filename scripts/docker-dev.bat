@echo off
REM Скрипт для запуска StaffProBot в режиме разработки на Windows
echo 🚀 Запуск StaffProBot в режиме разработки...

REM Проверка наличия Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker не установлен. Установите Docker Desktop и попробуйте снова.
    pause
    exit /b 1
)

REM Проверка Docker Compose (поддержка обеих версий)
set DOCKER_COMPOSE_CMD=docker-compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    docker compose version >nul 2>&1
    if errorlevel 1 (
        echo ❌ Docker Compose не установлен. Установите Docker Compose и попробуйте снова.
        pause
        exit /b 1
    ) else (
        set DOCKER_COMPOSE_CMD=docker compose
    )
)

echo ✅ Используется: %DOCKER_COMPOSE_CMD%

REM Переход в корневую директорию проекта
cd /d "%~dp0.."

REM Создание .env файла если его нет
if not exist .env (
    echo 📝 Создание .env файла из примера...
    copy env.example .env
    echo ⚠️  Отредактируйте .env файл, указав ваши токены и настройки
)

REM Остановка существующих контейнеров
echo 🛑 Остановка существующих контейнеров...
%DOCKER_COMPOSE_CMD% -f docker-compose.dev.yml down

REM Сборка и запуск
echo 🔨 Сборка и запуск контейнеров...
%DOCKER_COMPOSE_CMD% -f docker-compose.dev.yml up --build -d

REM Ожидание готовности сервисов
echo ⏳ Ожидание готовности сервисов...
timeout /t 10 /nobreak >nul

REM Проверка статуса
echo 📊 Статус сервисов:
%DOCKER_COMPOSE_CMD% -f docker-compose.dev.yml ps

echo ✅ StaffProBot запущен в режиме разработки!
echo 🌐 Бот доступен на порту 8000
echo 🗄️  База данных PostgreSQL на порту 5432
echo 🔴 Redis на порту 6379
echo 🐰 RabbitMQ на порту 5672 (управление: http://localhost:15672)
echo 📈 Prometheus на порту 9090
echo 📊 Grafana на порту 3000

echo.
echo 📝 Полезные команды:
echo   Просмотр логов: %DOCKER_COMPOSE_CMD% -f docker-compose.dev.yml logs -f bot
echo   Остановка: %DOCKER_COMPOSE_CMD% -f docker-compose.dev.yml down
echo   Перезапуск: %DOCKER_COMPOSE_CMD% -f docker-compose.dev.yml restart bot

pause
