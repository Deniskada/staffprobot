# 🧪 Тесты StaffProBot

> **Статус:** Активно разрабатываются  
> **Покрытие:** Планируется 90%+  
> **Фреймворк:** pytest + asyncio

---

## 📋 Содержание

1. [Структура тестов](#структура-тестов)
2. [Запуск тестов](#запуск-тестов)
3. [Типы тестов](#типы-тестов)
4. [Конфигурация](#конфигурация)
5. [Утилиты и хелперы](#утилиты-и-хелперы)
6. [Моки и фикстуры](#моки-и-фикстуры)
7. [CI/CD интеграция](#cicd-интеграция)

---

## 🏗 Структура тестов

```
tests/
├── conftest.py                    # Конфигурация pytest и общие фикстуры
├── README.md                      # Документация тестов
├── utils/
│   └── test_helpers.py           # Утилиты и хелперы для тестов
├── unit/                          # Unit тесты (быстрые, изолированные)
│   ├── test_admin_notification_service.py
│   └── test_notification_template_service.py
├── integration/                   # Integration тесты (медленные, с зависимостями)
│   ├── test_admin_notifications_routes.py
│   └── test_template_crud_operations.py
└── fixtures/                      # Тестовые данные и фикстуры
    ├── notifications.json
    └── templates.json
```

---

## 🚀 Запуск тестов

### Установка зависимостей

```bash
# Установка pytest и плагинов
pip install pytest pytest-asyncio pytest-mock pytest-cov

# Или через requirements
pip install -r requirements.txt
```

### Базовые команды

```bash
# Запуск всех тестов
pytest

# Запуск с подробным выводом
pytest -v

# Запуск только unit тестов
pytest -m unit

# Запуск только integration тестов
pytest -m integration

# Запуск конкретного файла
pytest tests/unit/test_admin_notification_service.py

# Запуск конкретного теста
pytest tests/unit/test_admin_notification_service.py::TestAdminNotificationService::test_get_notifications_paginated_success
```

### Запуск с покрытием кода

```bash
# Запуск с измерением покрытия
pytest --cov=apps --cov=core --cov=domain --cov=shared --cov-report=html

# Просмотр отчета покрытия
open htmlcov/index.html
```

### Запуск в Docker

```bash
# Запуск тестов в контейнере
docker compose -f docker-compose.dev.yml exec web pytest

# Запуск с покрытием в контейнере
docker compose -f docker-compose.dev.yml exec web pytest --cov=apps --cov-report=term-missing
```

---

## 🎯 Типы тестов

### Unit тесты (`tests/unit/`)

**Характеристики:**
- ⚡ Быстрые (< 1 сек на тест)
- 🔒 Изолированные (без внешних зависимостей)
- 🎭 Полностью замокированные
- 📊 Высокое покрытие кода

**Что тестируется:**
- Бизнес-логика сервисов
- Валидация данных
- Обработка ошибок
- Алгоритмы и вычисления

**Примеры:**
```python
async def test_get_notifications_paginated_success(self, service, mock_session):
    """Тест успешного получения уведомлений с пагинацией"""
    # Arrange
    mock_session.scalar.return_value = 1
    
    # Act
    notifications, total_count = await service.get_notifications_paginated(page=1, per_page=20)
    
    # Assert
    assert len(notifications) == 1
    assert total_count == 1
```

### Integration тесты (`tests/integration/`)

**Характеристики:**
- 🐌 Медленные (1-10 сек на тест)
- 🔗 С внешними зависимостями
- 🌐 Тестирование API endpoints
- 🗄️ Работа с базой данных

**Что тестируется:**
- HTTP API endpoints
- Интеграция между сервисами
- Работа с базой данных
- Аутентификация и авторизация

**Примеры:**
```python
async def test_create_template_success(self, client, mock_superadmin_user, sample_template_data):
    """Тест успешного создания шаблона через API"""
    # Act
    response = client.post("/admin/notifications/api/templates/create", json=sample_template_data)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
```

---

## ⚙️ Конфигурация

### pytest.ini

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests (быстрые, изолированные)
    integration: Integration tests (медленные, с внешними зависимостями)
    slow: Медленные тесты

asyncio_mode = auto
addopts = -v --tb=short --strict-markers
```

### Фикстуры (conftest.py)

```python
@pytest.fixture
def mock_superadmin_user():
    """Мок пользователя-суперадмина"""
    return {
        "id": 1,
        "telegram_id": 123456789,
        "role": "superadmin",
        "is_active": True
    }

@pytest.fixture
def sample_notification():
    """Образец уведомления для тестов"""
    return Notification(
        id=1,
        user_id=123,
        type=NotificationType.SHIFT_REMINDER,
        # ... остальные поля
    )
```

---

## 🛠 Утилиты и хелперы

### TestDataFactory

```python
from tests.utils.test_helpers import TestDataFactory

# Создание тестового уведомления
notification = TestDataFactory.create_notification(
    id=1,
    user_id=123,
    type=NotificationType.SHIFT_REMINDER
)

# Создание тестового шаблона
template = TestDataFactory.create_template(
    template_key="test_template",
    name="Test Template"
)

# Создание данных для API
template_data = TestDataFactory.create_template_data(
    template_key="new_template",
    name="New Template"
)
```

### MockServiceFactory

```python
from tests.utils.test_helpers import MockServiceFactory

# Создание мок AdminNotificationService
mock_service = MockServiceFactory.create_admin_notification_service_mock(
    notifications=[notification1, notification2],
    statistics={"total_notifications": 100}
)

# Создание мок NotificationTemplateService
mock_template_service = MockServiceFactory.create_notification_template_service_mock(
    templates=[template1, template2]
)
```

### AssertionHelpers

```python
from tests.utils.test_helpers import AssertionHelpers

# Проверка равенства уведомлений
AssertionHelpers.assert_notification_equal(actual, expected)

# Проверка успешного API ответа
AssertionHelpers.assert_api_response_success(response_data, "Template created successfully")

# Проверка ошибочного API ответа
AssertionHelpers.assert_api_response_error(response_data, "Template not found")
```

---

## 🎭 Моки и фикстуры

### Основные фикстуры

```python
@pytest.fixture
def mock_db_session():
    """Мок сессии базы данных"""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.commit = AsyncMock()
    return session

@pytest.fixture
def sample_notification():
    """Образец уведомления"""
    return TestDataFactory.create_notification()

@pytest.fixture
def mock_superadmin_user():
    """Мок суперадмина"""
    return TestDataFactory.create_user_data(role="superadmin")
```

### Мокирование зависимостей

```python
@patch('apps.web.routes.admin_notifications.require_superadmin')
@patch('apps.web.routes.admin_notifications.get_db_session')
async def test_api_endpoint(mock_get_db_session, mock_require_superadmin, client):
    # Настройка моков
    mock_require_superadmin.return_value = mock_superadmin_user
    mock_get_db_session.return_value = mock_db_session
    
    # Выполнение теста
    response = client.get("/admin/notifications/")
    assert response.status_code == 200
```

---

## 🔄 CI/CD интеграция

### GitHub Actions

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run unit tests
        run: pytest -m unit --cov=apps --cov-report=xml
      
      - name: Run integration tests
        run: pytest -m integration
      
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

### Pre-commit hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: [-m unit, --tb=short]
```

---

## 📊 Метрики и покрытие

### Цели покрытия

- **Unit тесты:** 95%+ покрытие
- **Integration тесты:** 80%+ покрытие
- **Общее покрытие:** 90%+

### Отчеты покрытия

```bash
# HTML отчет
pytest --cov=apps --cov-report=html
open htmlcov/index.html

# XML отчет для CI
pytest --cov=apps --cov-report=xml

# Терминальный отчет
pytest --cov=apps --cov-report=term-missing
```

---

## 🐛 Отладка тестов

### Запуск с отладкой

```bash
# Запуск с pdb
pytest --pdb

# Запуск конкретного теста с отладкой
pytest tests/unit/test_admin_notification_service.py::TestAdminNotificationService::test_get_notifications_paginated_success --pdb

# Запуск с подробным выводом
pytest -v -s
```

### Логирование

```python
import logging

# Включение логирования в тестах
logging.basicConfig(level=logging.DEBUG)

# Логирование в конкретном тесте
def test_something(caplog):
    with caplog.at_level(logging.DEBUG):
        # выполнение теста
        pass
    
    assert "Expected log message" in caplog.text
```

---

## 📚 Дополнительные ресурсы

### Документация

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-mock](https://pytest-mock.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)

### Полезные команды

```bash
# Запуск только быстрых тестов
pytest -m "not slow"

# Запуск тестов с определенным маркером
pytest -m "admin"

# Запуск тестов в параллель
pytest -n auto

# Запуск тестов с профилированием
pytest --profile
```

---

**Тестирование — это не просто проверка кода, это гарантия качества! 🚀**
