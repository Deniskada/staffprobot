-- Инициализация прод БД для StaffProBot
-- Выполняется контейнером postgres при первом старте (docker-entrypoint-initdb.d)

-- Параметры окружения ожидаются в docker-compose: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

-- Создание расширения PostGIS (без topology/tiger)
CREATE EXTENSION IF NOT EXISTS postgis;

-- Настройка search_path
ALTER DATABASE CURRENT_DATABASE() SET search_path = 'public';

-- Владелец уже будет POSTGRES_USER. Дальше владельца таблиц управляем на уровне миграций/приложения.

