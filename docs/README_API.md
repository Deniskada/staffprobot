# 🚀 API Сервер StaffProBot

## Обзор

StaffProBot использует **независимый HTTP API сервер**, написанный на чистом Python без внешних фреймворков. Это обеспечивает максимальную совместимость и простоту развертывания.

## 🏗️ Архитектура

### Компоненты
- **`api_standalone.py`** - API сервер с заглушками (для разработки)
- **`api_real_db.py`** - API сервер с поддержкой базы данных
- **`api_services_standalone.py`** - Независимые сервисы без FastAPI

### Режимы работы
1. **Режим заглушек** - Работает без базы данных, использует mock данные
2. **Режим БД** - Работает с PostgreSQL через SQLAlchemy
3. **Автоматическое переключение** между режимами

## 📡 API Endpoints

### Health Check
```
GET /health
```
**Ответ:**
```json
{
  "status": "healthy",
  "timestamp": 1755676312.302665,
  "version": "1.0.0",
  "database": "connected" | "disconnected"
}
```

### Корневой endpoint
```
GET /
```
**Ответ:**
```json
{
  "app": "StaffProBot",
  "version": "1.0.0",
  "status": "running",
  "database": "connected" | "disconnected",
  "docs": "disabled"
}
```

### Пользователи
```
GET /api/v1/users          # Список пользователей
GET /api/v1/users/{id}     # Пользователь по ID
POST /api/v1/users         # Создание пользователя
```

### Объекты
```
GET /api/v1/objects        # Список объектов
GET /api/v1/objects/{id}   # Объект по ID
POST /api/v1/objects       # Создание объекта
```

### Смены
```
GET /api/v1/shifts         # Список смен
GET /api/v1/shifts/{id}    # Смена по ID
POST /api/v1/shifts        # Создание смены
```

## 🚀 Запуск

### 1. API с заглушками (для разработки)
```bash
python api_standalone.py
# или
run_api_standalone.bat
```

### 2. API с базой данных
```bash
python api_real_db.py
# или
run_api_real_db.bat
```

### 3. Тестирование
```bash
# Тест заглушек
python test_api_standalone.py
# или
test_api_standalone.bat

# Тест с БД
python test_api_db.py
# или
test_api_db.bat
```

## 🔧 Конфигурация

### Настройки по умолчанию
```python
class DefaultSettings:
    app_name = "StaffProBot"
    version = "1.0.0"
    api_host = "0.0.0.0"
    api_port = 8000
    database_url = "postgresql://postgres:password@localhost:5432/staffprobot"
    debug = True
```

### Переменные окружения
- `API_HOST` - Хост для API сервера
- `API_PORT` - Порт для API сервера
- `DATABASE_URL` - URL подключения к PostgreSQL

## 📊 База данных

### Поддерживаемые СУБД
- **PostgreSQL** (основная)
- **PostGIS** (для геоданных)

### Миграции
```bash
# Создание миграции
python create_migration.py

# Применение миграции
python apply_migration.py
# или
apply_migration.bat
```

## 🧪 Тестирование

### Автоматические тесты
- **Unit тесты** - Тестирование отдельных компонентов
- **Integration тесты** - Тестирование API endpoints
- **Docker тесты** - Тестирование в контейнерах

### Покрытие кода
- **Цель**: 90%+ покрытие тестами
- **Текущее**: 70%+ (основная логика)

## 🔒 Безопасность

### CORS
- Поддержка CORS для веб-интерфейса
- Настройка заголовков безопасности

### Валидация
- Валидация JSON данных
- Проверка типов и форматов
- Обработка ошибок с HTTP кодами

## 📈 Мониторинг

### Логирование
- Структурированные логи в JSON формате
- Уровни: INFO, ERROR
- Контекст: user_id, request_id, execution_time

### Метрики
- Время ответа API
- Количество запросов
- Статус базы данных

## 🚀 Развертывание

### Docker
```bash
# Запуск PostgreSQL
docker-compose up -d postgres

# Запуск API
python api_real_db.py
```

### Production
- Использование `api_real_db.py`
- Настройка reverse proxy (nginx)
- SSL/TLS сертификаты
- Мониторинг и алерты

## 🔄 Миграция с FastAPI

### Что изменилось
- ❌ Убрали FastAPI зависимости
- ✅ Добавили независимый HTTP сервер
- ✅ Сохранили все API endpoints
- ✅ Улучшили совместимость

### Преимущества
- **Простота** - Меньше зависимостей
- **Совместимость** - Работает с Python 3.11+
- **Производительность** - Легковесный сервер
- **Гибкость** - Легко кастомизировать

## 📚 Дополнительные ресурсы

- [Техническое видение](vision.md)
- [Структура проекта](vision.md#23-структура-проекта)
- [Модель данных](vision.md#24-модель-данных)
- [Работа с LLM](vision.md#25-работа-с-llm)
