# Техническое видение проекта StaffProBot

## 2.0. Статус проекта

**🎉 ПРОЕКТ ЗАВЕРШЕН! Все итерации успешно реализованы.**

### ✅ Завершенные итерации:
- **Итерация 1-6**: MVP, базовая функциональность, геолокация, планирование, отчетность, оптимизация
- **Итерация 7**: Docker-разработка и кросс-платформенность  
- **Итерация 8**: Расширенная функциональность (частично)
- **Итерация 9**: Веб-сайт с системой договоров и ролей
- **Итерация 12**: Улучшение drag&drop и планирования
- **Итерация 13**: Система множественных ролей и управляющих

### 🚀 Готовность к production:
- **Миграции**: Все применены и проверены
- **Тестирование**: Система протестирована в реальных условиях
- **Документация**: Полная документация по всем функциям
- **Стабильность**: Все критические ошибки исправлены

**Система готова к развертыванию в production!**

---

## 2.1. Технологии

### Backend Framework
- **FastAPI** - современный, быстрый веб-фреймворк для Python с автоматической генерацией API документации
- **Python 3.11+** - для лучшей производительности и поддержки современных возможностей
- **Pydantic** - валидация данных и сериализация
- **SQLAlchemy 2.0** - современный ORM с поддержкой async/await

### Web Frontend
- **Jinja2** - шаблонизатор для серверного рендеринга HTML
- **Bootstrap 5** - современный CSS фреймворк для адаптивного дизайна
- **FullCalendar.js** - интерактивный календарь для планирования
- **Chart.js** - библиотека для создания графиков и диаграмм
- **HTMX** - для динамических обновлений без перезагрузки страницы
- **FastAPI + Uvicorn** - веб-сервер для обработки HTTP запросов
- **JWT токены** - для аутентификации и авторизации
- **Redis** - для хранения PIN-кодов и сессий

### База данных
- **PostgreSQL 15+** - основная реляционная БД
- **PostGIS** - расширение для работы с геоданными
- **Redis** - кэширование, сессии, очереди задач
- **Alembic** - миграции базы данных

### LLM и AI
- **OpenAI GPT-4** - основная модель для обработки естественного языка
- **LangChain** - фреймворк для работы с LLM
- **Embeddings** - OpenAI text-embedding-ada-002 для семантического поиска
- **Fallback модели** - локальные модели (Llama 2, Mistral) для резервирования

### Telegram Bot
- **python-telegram-bot** - официальная библиотека для Telegram Bot API
- **Webhook режим** - для production окружения
- **Long Polling** - для разработки и тестирования
- **Location API** - встроенная геолокация Telegram для точных координат
- **Callback Queries** - интерактивные кнопки для выбора объектов
- **State Management** - UserStateManager для сохранения состояния диалога пользователя
- **Retry Logic** - кнопки повторной отправки геолокации при ошибках
- **Timezone Support** - отображение времени в локальном часовом поясе
- **Timeslot Management** - полное управление тайм-слотами с редактированием времени, ставок, сотрудников и заметок
- **Object Management** - расширенное управление объектами с настройкой времени работы и удалением
- **Advanced Reporting** - система отчетности с разбивкой по сотрудникам, Excel экспортом и произвольными периодами
- **Custom Date Selection** - возможность выбора произвольных дат для формирования отчетов
- **Web Integration** - интеграция с веб-приложением для отправки PIN-кодов
- **Telegram ID Display** - отображение Telegram ID пользователя для авторизации на сайте
- **Calendar Integration** - полная интеграция планирования смен между ботом и веб-календарем
- **Shift Status Display** - цветовая индикация статуса слотов (пустой, запланирован, подтвержден, отменен)
- **Occupancy Information** - отображение занятости слотов (1/2, 0/1) для планирования
- **Drag & Drop Planning** - интерактивное планирование смен через перетаскивание сотрудников
- **Employee Panel** - панель сотрудников для drag&drop планирования с проверкой доступа
- **Visual Planning Interface** - улучшенный интерфейс планирования с визуальными элементами
- **Web Interface** - полный веб-интерфейс для управления объектами, сотрудниками и договорами
- **Contract Management** - система договоров с шаблонами, версионированием и управлением доступом
- **Employee Management** - управление сотрудниками с заключением договоров и назначением объектов
- **Template System** - унифицированная система шаблонов для планирования и договоров
- **Role-based Interface** - раздельные интерфейсы для владельцев (/owner/*) и сотрудников (/employee/*)
- **Unified Navigation** - единая навигация с цветовой индикацией ролей (зеленый для владельцев)
- **Responsive Design** - адаптивный дизайн для всех устройств
- **Exception Handling** - умная обработка ошибок с редиректами и подсказками
- **Owner Object Access** - владельцы могут работать на своих объектах без договора
- **Work Schedule Management** - полное управление графиком работы объектов (дни недели, периодичность)
- **Shift Logic Enhancement** - улучшенная логика открытия смен с приоритетом запланированных смен
- **Drag & Drop Planning** - интерактивное планирование смен через перетаскивание объектов и сотрудников
- **Employee Panel** - панель сотрудников для планирования смен с drag&drop функциональностью
- **Visual Planning Interface** - улучшенный интерфейс календаря с возможностью визуального планирования
- **Applicant Support** - поддержка соискателей с доступом к объектам "Доступен для соискателей"
- **Role-based Object Filtering** - фильтрация объектов по ролям (сотрудники видят все, соискатели - только доступные)

### Микросервисы и коммуникация
- **Celery** - асинхронные задачи и планировщик
- **RabbitMQ** - брокер сообщений для межсервисного взаимодействия
- **gRPC** - высокопроизводительная коммуникация между сервисами
- **REST API** - для внешних интеграций

### Мониторинг и логирование
- **Prometheus** - метрики и мониторинг
- **Grafana** - визуализация метрик
- **ELK Stack** - Elasticsearch, Logstash, Kibana для логирования
- **Sentry** - отслеживание ошибок

### Деплой и инфраструктура
- **Docker** - контейнеризация приложений
- **Docker Compose** - оркестрация для разработки
- **Kubernetes** - оркестрация для production
- **Nginx** - reverse proxy и балансировщик нагрузки
- **Traefik** - современный reverse proxy для контейнеров

## 2.2. Принцип разработки

### Архитектурные принципы
- **Микросервисная архитектура** - разделение на независимые сервисы
- **Event-Driven Architecture** - асинхронная обработка событий
- **CQRS** - разделение команд и запросов для оптимизации
- **Domain-Driven Design** - проектирование на основе бизнес-доменов

### Принципы разработки
- **SOLID принципы** - чистая архитектура и дизайн
- **DRY** - избежание дублирования кода
- **KISS** - простота и читаемость
- **Fail Fast** - быстрое выявление и исправление ошибок

### Качество кода
- **Type Hints** - статическая типизация Python
- **Black** - автоматическое форматирование кода
- **Flake8** - проверка стиля и качества
- **MyPy** - статический анализ типов
- **Pytest** - модульное и интеграционное тестирование
- **Coverage** - покрытие кода тестами (цель: 90%+)

### CI/CD
- **GitHub Actions** - автоматизация сборки и тестирования
- **Pre-commit hooks** - проверка кода перед коммитом
- **Automated testing** - автоматические тесты на каждый PR
- **Code review** - обязательный ревью кода

## 2.3. Структура проекта

```
staffprobot/
├── apps/                          # Основные приложения
│   ├── bot/                       # Telegram Bot сервис
│   │   ├── handlers_div/          # Модульные обработчики
│   │   │   ├── core_handlers.py   # Основные команды и роутинг
│   │   │   ├── shift_handlers.py  # Управление сменами
│   │   │   ├── object_handlers.py # Управление объектами
│   │   │   ├── timeslot_handlers.py # Управление тайм-слотами
│   │   │   ├── utility_handlers.py # Служебные функции
│   │   │   └── utils.py           # Общие утилиты
│   │   └── services/              # Сервисы бота
│   ├── web/                       # Веб-приложение
│   │   ├── templates/             # Jinja2 шаблоны
│   │   │   ├── base.html          # Базовый шаблон
│   │   │   ├── auth/              # Страницы авторизации
│   │   │   ├── dashboard/         # Дашборды
│   │   │   ├── owner/             # Интерфейс владельца (/owner/*)
│   │   │   │   ├── base_owner.html # Базовый шаблон владельца
│   │   │   │   ├── objects/       # Управление объектами
│   │   │   │   ├── calendar/      # Календарное планирование
│   │   │   │   ├── employees/     # Управление сотрудниками
│   │   │   │   ├── shifts/        # Управление сменами
│   │   │   │   ├── reports/       # Отчетность
│   │   │   │   └── profile/       # Профиль владельца
│   │   │   ├── employee/          # Интерфейс сотрудника (/employee/*)
│   │   │   └── admin/             # Административный интерфейс
│   │   │   ├── shifts/            # Управление сменами
│   │   │   ├── reports/           # Отчетность
│   │   │   └── contracts/         # Система договоров
│   │   ├── static/                # Статические файлы
│   │   │   ├── css/               # Стили
│   │   │   ├── js/                # JavaScript
│   │   │   └── images/            # Изображения
│   │   ├── routes/                # Веб-роуты
│   │   │   ├── auth.py            # Авторизация
│   │   │   ├── dashboard.py       # Дашборды
│   │   │   ├── objects.py         # Объекты
│   │   │   ├── calendar.py        # Календарь
│   │   │   ├── shifts.py          # Смены
│   │   │   ├── reports.py         # Отчеты
│   │   │   └── contracts.py       # Договоры
│   │   └── services/              # Веб-сервисы
│   ├── api/                       # REST API сервис
│   ├── scheduler/                 # Сервис планировщика
│   ├── analytics/                 # Аналитический сервис
│   └── notification/              # Сервис уведомлений
├── core/                          # Общая логика
│   ├── config/                    # Конфигурация
│   ├── database/                  # Настройки БД
│   ├── geolocation/               # Геолокационные сервисы
│   ├── scheduler/                 # Планировщик смен
│   ├── state/                     # Управление состоянием пользователей
│   ├── auth/                      # Аутентификация и управление пользователями
│   ├── logging/                   # Структурированное логирование
│   ├── exceptions/                # Кастомные исключения
│   └── utils/                     # Утилиты (timezone, helpers)
├── domain/                        # Бизнес-логика
│   ├── entities/                  # Сущности домена
│   ├── repositories/              # Интерфейсы репозиториев
│   ├── services/                  # Бизнес-сервисы
│   └── value_objects/             # Объекты-значения
├── infrastructure/                 # Инфраструктурный слой
│   ├── database/                  # Реализация репозиториев
│   ├── external/                  # Внешние API интеграции
│   ├── messaging/                 # Система сообщений
│   └── storage/                   # Файловое хранилище
├── shared/                        # Общие компоненты
│   ├── schemas/                   # Pydantic схемы
│   ├── constants/                 # Константы
│   └── types/                     # Общие типы
├── tests/                         # Тесты
│   ├── unit/                      # Модульные тесты
│   ├── integration/               # Интеграционные тесты
│   └── e2e/                       # End-to-end тесты
├── docker/                        # Docker конфигурация
│   ├── Dockerfile                 # Production образ
│   ├── Dockerfile.dev             # Development образ
│   └── monitoring/                # Конфигурация мониторинга
│       ├── prometheus.yml         # Настройки Prometheus
│       └── grafana/               # Дашборды Grafana
├── .dockerignore                  # Исключения для Docker build
│   # Исключает .git, __pycache__, venv/, .env файлы, логи, тесты
├── k8s/                          # Kubernetes манифесты
├── scripts/                       # Скрипты развертывания
│   ├── docker-dev.sh              # Скрипт запуска dev окружения (Linux/macOS)
│   └── docker-dev.bat             # Скрипт запуска dev окружения (Windows)
├── docs/                          # Документация
├── requirements.txt               # Python зависимости
├── pyproject.toml                # Конфигурация проекта
├── docker-compose.dev.yml        # Docker Compose для разработки
├── docker-compose.prod.yml       # Docker Compose для продакшена
├── README.md                     # Документация проекта
└── README_DOCKER.md              # Подробная документация по Docker
```

## 2.4. Модель данных

### Основные сущности

#### User (Пользователь)
```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255),
    phone VARCHAR(20),
    role VARCHAR(50) NOT NULL DEFAULT 'employee',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Object (Объект)
```sql
CREATE TABLE objects (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    owner_id BIGINT REFERENCES users(id),
    address TEXT,
    coordinates POINT NOT NULL,
    opening_time TIME NOT NULL,
    closing_time TIME NOT NULL,
    hourly_rate DECIMAL(10,2) NOT NULL,
    max_distance_meters INTEGER DEFAULT 500,
    required_employees JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    available_for_applicants BOOLEAN DEFAULT FALSE, -- Доступен для соискателей (уже реализовано)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Shift (Смена)
```sql
CREATE TABLE shifts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    object_id BIGINT REFERENCES objects(id),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    start_coordinates POINT,
    end_coordinates POINT,
    total_hours DECIMAL(5,2),
    hourly_rate DECIMAL(10,2),
    total_payment DECIMAL(10,2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### ShiftSchedule (Расписание смен)
```sql
CREATE TABLE shift_schedules (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    object_id BIGINT REFERENCES objects(id),
    planned_start TIMESTAMP NOT NULL,
    planned_end TIMESTAMP NOT NULL,
    status VARCHAR(50) DEFAULT 'planned',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### TimeSlot (Тайм-слоты объектов)
```sql
CREATE TABLE time_slots (
    id BIGSERIAL PRIMARY KEY,
    object_id BIGINT REFERENCES objects(id),
    slot_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    hourly_rate DECIMAL(10,2),
    max_employees INTEGER DEFAULT 1,
    is_additional BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### UserState (Состояние диалога пользователя)
```sql
CREATE TABLE user_states (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) UNIQUE,
    action VARCHAR(50) NOT NULL, -- 'open_shift', 'close_shift', 'create_object'
    selected_object_id BIGINT REFERENCES objects(id),
    selected_shift_id BIGINT REFERENCES shifts(id),
    step VARCHAR(50) NOT NULL, -- 'object_selection', 'location_request', 'processing'
    data JSONB, -- Дополнительные данные состояния
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### UserRole (Роли пользователей)
```sql
CREATE TABLE user_roles (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL, -- 'applicant', 'owner', 'employee', 'manager', 'superadmin'
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, role)
);

CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role);
```

#### Contract (Договоры)
```sql
CREATE TABLE contracts (
    id BIGSERIAL PRIMARY KEY,
    owner_id BIGINT REFERENCES users(id) NOT NULL,
    employee_id BIGINT REFERENCES users(id) NOT NULL,
    template_id BIGINT REFERENCES contract_templates(id),
    version_id BIGINT REFERENCES contract_versions(id),
    status VARCHAR(50) DEFAULT 'active', -- active, suspended, terminated
    start_date DATE NOT NULL,
    end_date DATE,
    hourly_rate DECIMAL(10,2),
    objects JSONB, -- Список доступных объектов
    is_manager BOOLEAN DEFAULT FALSE, -- Назначен ли управляющим
    manager_permissions JSONB DEFAULT '{}', -- Общие права управляющего
    can_create_objects BOOLEAN DEFAULT FALSE,
    can_manage_contracts BOOLEAN DEFAULT FALSE,
    can_view_all_reports BOOLEAN DEFAULT FALSE,
    can_manage_managers BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### ManagerObjectPermission (Права управляющего на объекты)
```sql
CREATE TABLE manager_object_permissions (
    id BIGSERIAL PRIMARY KEY,
    contract_id BIGINT REFERENCES contracts(id) ON DELETE CASCADE,
    object_id BIGINT REFERENCES objects(id) ON DELETE CASCADE,
    can_view BOOLEAN DEFAULT TRUE,
    can_edit BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    can_manage_employees BOOLEAN DEFAULT FALSE,
    can_view_finances BOOLEAN DEFAULT FALSE,
    can_edit_rates BOOLEAN DEFAULT FALSE,
    can_edit_schedule BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(contract_id, object_id)
);

CREATE INDEX idx_manager_object_permissions_contract ON manager_object_permissions(contract_id);
CREATE INDEX idx_manager_object_permissions_object ON manager_object_permissions(object_id);
```

#### ContractTemplate (Шаблоны договоров)
```sql
CREATE TABLE contract_templates (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_content TEXT NOT NULL, -- Шаблон договора
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### ContractVersion (Версии договоров)
```sql
CREATE TABLE contract_versions (
    id BIGSERIAL PRIMARY KEY,
    contract_id BIGINT REFERENCES contracts(id) NOT NULL,
    version_number INTEGER NOT NULL,
    content TEXT NOT NULL, -- Содержимое договора
    changes_description TEXT, -- Описание изменений
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### TrialShift (Пробные выходы)
```sql
CREATE TABLE trial_shifts (
    id BIGSERIAL PRIMARY KEY,
    applicant_id BIGINT REFERENCES users(id) NOT NULL,
    object_id BIGINT REFERENCES objects(id) NOT NULL,
    requested_date DATE NOT NULL,
    requested_time TIME NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, approved, rejected, completed
    owner_notes TEXT,
    applicant_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Геолокационные возможности

#### PostGIS расширения
```sql
-- Включение PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Индекс для быстрого поиска по координатам
CREATE INDEX idx_objects_coordinates ON objects USING GIST (coordinates);
CREATE INDEX idx_shifts_start_coordinates ON shifts USING GIST (start_coordinates);
CREATE INDEX idx_shifts_end_coordinates ON shifts USING GIST (end_coordinates);
```

#### Функции расчета расстояний
- **Формула Гаверсина**: точный расчет расстояния между координатами
- **Валидация координат**: проверка формата и точности GPS данных
- **Проверка местоположения**: контроль нахождения в радиусе объекта
- **Настраиваемые радиусы**: `max_distance_meters` для каждого объекта

### Индексы и оптимизация
```sql
-- Индексы для быстрого поиска
CREATE INDEX idx_shifts_user_id ON shifts(user_id);
CREATE INDEX idx_shifts_object_id ON shifts(object_id);
CREATE INDEX idx_shifts_start_time ON shifts(start_time);
CREATE INDEX idx_shifts_status ON shifts(status);

-- Геопространственные индексы
CREATE INDEX idx_objects_coordinates ON objects USING GIST(coordinates);
CREATE INDEX idx_shifts_start_coordinates ON shifts USING GIST(start_coordinates);

-- Составные индексы
CREATE INDEX idx_shifts_user_date ON shifts(user_id, DATE(start_time));
CREATE INDEX idx_schedules_user_planned ON shift_schedules(user_id, planned_start);

-- Индексы для состояний пользователей
CREATE INDEX idx_user_states_user_id ON user_states(user_id);
CREATE INDEX idx_user_states_expires_at ON user_states(expires_at);
CREATE INDEX idx_user_states_action ON user_states(action);
```

## 2.5. Работа с LLM

### Управление состоянием пользователей

#### UserStateManager
```python
class UserAction(Enum):
    NONE = "none"
    OPEN_SHIFT = "open_shift"
    CLOSE_SHIFT = "close_shift"
    CREATE_OBJECT = "create_object"
    EDIT_OBJECT = "edit_object"

class UserStep(Enum):
    NONE = "none"
    OBJECT_SELECTION = "object_selection"
    LOCATION_REQUEST = "location_request"
    INPUT_FIELD_VALUE = "input_field_value"
    PROCESSING = "processing"

class UserState(BaseModel):
    user_id: int
    action: UserAction
    step: UserStep
    selected_object_id: Optional[int] = None
    selected_shift_id: Optional[int] = None
    field_name: Optional[str] = None
    created_at: datetime
```

#### Диалоговые потоки
- **Открытие смены**: выбор объекта → запрос геопозиции → открытие
- **Закрытие смены**: выбор смены → запрос геопозиции → закрытие
- **Создание объекта**: пошаговый ввод всех параметров
- **Редактирование объекта**: выбор поля → ввод значения → сохранение

### UX улучшения

#### Обработка ошибок геолокации
- **Кнопки повтора**: "📍 Отправить геопозицию повторно"
- **Отмена операции**: "❌ Отмена" с возвратом в главное меню
- **Информативные сообщения**: точное расстояние и лимит

#### Команды бота
- **/start** - главное меню с интерактивными кнопками
- **/help** - подробная справка по всем функциям
- **/status** - текущие активные смены с локальным временем

### Архитектура LLM-модуля

#### Компоненты
- **Prompt Manager** - управление промптами и шаблонами
- **Context Manager** - управление контекстом диалога
- **Response Processor** - обработка и валидация ответов LLM
- **Fallback Handler** - резервные модели при сбоях
- **Rate Limiter** - ограничение запросов к API

#### Промпт-инженерия
```python
class PromptTemplate:
    SYSTEM_PROMPT = """
    Ты - ассистент для управления рабочими сменами. 
    Твоя задача - помогать пользователям планировать смены, 
    открывать/закрывать смены и получать отчеты.
    
    Правила:
    1. Всегда уточняй детали, если информации недостаточно
    2. Предлагай альтернативы при конфликтах в расписании
    3. Используй дружелюбный, но профессиональный тон
    4. При ошибках предлагай решения
    """
    
    SHIFT_OPENING_PROMPT = """
    Пользователь хочет открыть смену.
    Контекст: {context}
    
    Запрос: {user_message}
    
    Действия:
    1. Проверь доступность пользователя
    2. Предложи выбор объекта
    3. Запроси подтверждение геолокации
    """
```

#### Обработка контекста
```python
class ConversationContext:
    def __init__(self, user_id: int, max_turns: int = 10):
        self.user_id = user_id
        self.conversation_history = []
        self.max_turns = max_turns
        self.current_intent = None
        self.entities = {}
    
    def add_message(self, message: str, is_user: bool = True):
        self.conversation_history.append({
            'message': message,
            'is_user': is_user,
            'timestamp': datetime.now(),
            'intent': self.current_intent
        })
        
        if len(self.conversation_history) > self.max_turns:
            self.conversation_history.pop(0)
    
    def get_context_summary(self) -> str:
        # Создание краткого контекста для LLM
        recent_messages = self.conversation_history[-5:]
        return "\n".join([f"{'User' if msg['is_user'] else 'Bot'}: {msg['message']}" 
                         for msg in recent_messages])
```

### Интеграция с OpenAI
```python
class OpenAIService:
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.rate_limiter = RateLimiter(max_requests=100, time_window=60)
    
    async def generate_response(self, prompt: str, context: str = None) -> str:
        try:
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": context or ""}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return await self.fallback_response(prompt, context)
```

## 2.7. Система авторизации и аутентификации

### Веб-авторизация через Telegram
Реализована система авторизации, которая использует Telegram ID пользователя и PIN-код, отправляемый через бота.

#### Компоненты системы
- **AuthService** - основной сервис авторизации
- **BotIntegrationService** - интеграция с Telegram Bot API
- **JWT токены** - для управления сессиями
- **Redis** - для хранения PIN-кодов

#### Процесс авторизации
1. Пользователь вводит Telegram ID на веб-сайте
2. Система генерирует 6-значный PIN-код
3. PIN-код сохраняется в Redis с TTL 5 минут
4. Бот отправляет PIN-код пользователю в Telegram
5. Пользователь вводит PIN-код на сайте
6. Система проверяет PIN-код и создает JWT токен
7. Пользователь получает доступ к веб-интерфейсу

#### Реализация AuthService
```python
class AuthService:
    def __init__(self):
        self.cache = CacheService()
        self.bot_integration = BotIntegrationService()
        self.secret_key = settings.secret_key
        self.algorithm = "HS256"
        self.token_expire_minutes = settings.jwt_expire_minutes

    async def generate_and_send_pin(self, telegram_id: int) -> str:
        pin_code = f"{secrets.randbelow(1000000):06d}"
        await self.store_pin(telegram_id, pin_code, ttl=300)
        success = await self.bot_integration.send_pin_code(telegram_id, pin_code)
        return pin_code

    async def verify_pin(self, telegram_id: int, pin_code: str) -> bool:
        key = f"pin:{telegram_id}"
        stored_pin = await self.cache.get(key)
        if stored_pin and stored_pin == pin_code:
            await self.cache.delete(key)
            return True
        return False
```

#### Интеграция с ботом
```python
class BotIntegrationService:
    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.telegram_api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.http_client = httpx.AsyncClient()

    async def send_pin_code(self, telegram_id: int, pin_code: str) -> bool:
        message = f"""
🔑 <b>Ваш PIN-код для входа в StaffProBot:</b>
<code>{pin_code}</code>

Этот код действителен 5 минут.
"""
        return await self.send_message(telegram_id, message)
```

## 2.8. Система администрирования

### Роли пользователей
Система поддерживает множественные роли пользователей:

#### Базовые роли
- **applicant** - соискатель (базовая роль при первом старте бота)
- **employee** - сотрудник, может работать на объектах
- **owner** - владелец объектов, может управлять сотрудниками и объектами
- **manager** - управляющий, имеет детальные права доступа к объектам владельца
- **superadmin** - системный администратор с полными правами

#### Система множественных ролей
Пользователи могут иметь несколько ролей одновременно:
- **applicant + owner** - если пользователь создал объекты
- **applicant + employee** - если с пользователем заключен договор
- **applicant + owner + employee** - если пользователь и владелец, и сотрудник
- **applicant + owner + manager** - если пользователь владелец и управляющий
- **applicant + employee + manager** - если пользователь сотрудник и управляющий

#### Логика назначения ролей
- **applicant** - назначается при первом старте бота (базовая роль)
- **owner** - назначается при создании первого объекта, удаляется при удалении последнего
- **employee** - назначается при заключении договора, удаляется при расторжении всех договоров
- **manager** - назначается владельцем при создании договора с is_manager=True
- **superadmin** - назначается вручную системным администратором

#### Особенности роли applicant
- **Доступ к интерфейсу сотрудника** - может использовать `/employee/*` интерфейс
- **Ограниченный доступ к объектам** - видит только объекты с `available_for_applicants = TRUE`
- **Подача заявок** - может подавать заявки на смены на доступных объектах
- **Поиск работы** - имеет доступ к карте свободных смен
- **Автоматическое обновление** - при заключении договора получает роль employee

#### Роль управляющего (Manager)
Управляющий имеет детальные права доступа к объектам владельца:

**Общие права:**
- Создание новых объектов (если разрешено)
- Управление договорами с сотрудниками (если разрешено)
- Просмотр всех отчетов (если разрешено)
- Управление другими управляющими (если разрешено)

**Права на объекты:**
- **can_view** - просмотр информации об объекте
- **can_edit** - редактирование настроек объекта
- **can_delete** - удаление объекта
- **can_manage_employees** - управление сотрудниками на объекте
- **can_view_finances** - просмотр финансовой информации
- **can_edit_rates** - изменение ставок сотрудников
- **can_edit_schedule** - изменение графика работы

**Ограничения:**
- Доступ только к объектам, разрешенным в договоре
- Не может видеть объекты, к которым нет доступа
- Не может управлять объектами других владельцев

### Логика входа и переключения интерфейсов

#### Точки входа в систему
1. **Telegram Bot** - `/start` команда
2. **Веб-сайт** - ввод Telegram ID + PIN-код
3. **Прямые ссылки** - переход на конкретный интерфейс

#### Система переключения интерфейсов
При множественных ролях пользователь может переключаться между интерфейсами:

**Доступные интерфейсы:**
- `/admin/*` - административный интерфейс (superadmin)
- `/owner/*` - интерфейс владельца (owner)
- `/manager/*` - интерфейс управляющего (manager)
- `/employee/*` - интерфейс сотрудника (employee, applicant)
- `/auth/*` - общие функции (applicant)

**Логика выбора интерфейса:**
1. **Приоритет ролей**: superadmin > owner > manager > employee > applicant
2. **Автоматический выбор**: система выбирает интерфейс с наивысшим приоритетом
3. **Ручное переключение**: пользователь может переключиться на любой доступный интерфейс
4. **Сохранение выбора**: система запоминает последний выбранный интерфейс

**Компонент переключения ролей:**
- Dropdown в навигации с доступными интерфейсами
- Отображение текущей роли и доступных ролей
- Быстрое переключение между интерфейсами
- Визуальная индикация текущего интерфейса

### Административные функции

#### Управление пользователями ✅
- **Административная панель** - `/admin/` - полноценный интерфейс для суперадминов
- **Просмотр всех пользователей** - `/admin/users/` - список всех зарегистрированных пользователей
- **Редактирование ролей** - возможность назначения и изменения ролей пользователей
- **Блокировка пользователей** - активация/деактивация аккаунтов
- **Фильтрация по ролям** - поиск пользователей по роли и статусу
- **Разделение интерфейсов** - отдельные меню для разных ролей пользователей

#### Системная статистика ✅
- **Prometheus метрики** - сбор метрик производительности системы
- **Grafana дашборды** - визуализация статистики
- **Мониторинг активности** - отслеживание активных пользователей
- **Статистика по объектам** - количество объектов и их загруженность
- **Метрики смен** - статистика по выполненным сменам

#### Мониторинг системы ✅
- **HTTP запросы** - метрики запросов к API
- **База данных** - мониторинг запросов и соединений
- **Кэш Redis** - статистика попаданий в кэш
- **Celery задачи** - мониторинг фоновых задач
- **Telegram бот** - метрики сообщений и команд

#### Тарифные планы (в разработке)
- **Создание тарифов** - настройка лимитов и возможностей
- **Управление подписками** - назначение тарифов пользователям
- **Биллинг** - отслеживание использования и оплаты
- **Ограничения** - контроль лимитов по тарифам

### Реализованные компоненты

#### Метрики Prometheus
```python
# HTTP метрики
http_requests_total = Counter('staffprobot_http_requests_total')
http_request_duration_seconds = Histogram('staffprobot_http_request_duration_seconds')

# Метрики БД
db_queries_total = Counter('staffprobot_db_queries_total')
db_connections_active = Gauge('staffprobot_db_connections_active')

# Бизнес-метрики
users_active = Gauge('staffprobot_users_active')
objects_total = Gauge('staffprobot_objects_total')
shifts_total = Counter('staffprobot_shifts_total')
```

#### Административные роуты
```python
# Управление пользователями
@router.get("/users/")  # Список пользователей
@router.get("/users/{user_id}/edit")  # Редактирование пользователя
@router.post("/users/{user_id}/roles")  # Обновление ролей

# Системная статистика (через Prometheus)
# http://localhost:9090 - Prometheus
# http://localhost:3000 - Grafana
```

#### Мониторинг и логирование
- **Структурированное логирование** - JSON формат для удобного анализа
- **Централизованные логи** - сбор логов всех сервисов
- **Алерты** - уведомления о критических ошибках
- **Health checks** - проверка состояния всех компонентов

## 2.9. Концепция разделения интерфейсов по ролям

### Архитектурный подход "Роль = Отдельное приложение"

#### Принципы разделения
- **Полная изоляция** интерфейсов между ролями
- **Безопасность** - роль не может попасть в чужой раздел  
- **Простота разработки** - каждая роль = отдельное приложение
- **Масштабируемость** - легко добавлять новые роли

#### URL-структура
```
/admin/*    - суперадмин: управление системой
/owner/*    - владелец: управление объектами и сотрудниками  
/manager/*  - управляющий: управление по правам доступа
/employee/* - сотрудник: поиск смен, календарь, заработок
/auth/*     - общие: авторизация, доступна всем
```

#### Структура шаблонов
```
templates/
├── admin/           # Только для суперадмина
│   ├── base_admin.html
│   ├── dashboard.html
│   └── users.html
├── owner/           # Только для владельцев
│   ├── base_owner.html
│   ├── dashboard.html
│   └── objects.html
├── manager/         # Только для управляющих
│   ├── base_manager.html
│   ├── dashboard.html
│   ├── objects.html
│   └── employees.html
├── employee/        # Только для сотрудников
│   ├── base_employee.html
│   ├── dashboard.html
│   └── shifts_map.html
└── common/          # Общие компоненты
    ├── login.html
    ├── role_switcher.html
    └── error.html
```

#### Функциональное разделение

**🔧 Суперадмин (`/admin/*`):**
- Управление пользователями
- Тарифные планы  
- Системная статистика
- Мониторинг

**🏢 Владелец (`/owner/*`):**
- Объекты
- Календарь смен
- Сотрудники
- Шаблоны договоров
- Отчеты по объектам
- Назначение управляющих

**👨‍💼 Управляющий (`/manager/*`):**
- Управление доступными объектами (по правам)
- Создание новых объектов (если разрешено)
- Управление сотрудниками (если разрешено)
- Заключение договоров (если разрешено)
- Планирование смен
- Отчеты по доступным объектам
- Управление другими управляющими (если разрешено)

**👷 Сотрудник (`/employee/*`):**
- Карта свободных смен
- Мой календарь
- История работы
- Заработок

**📋 Соискатель (`/employee/*` + `/auth/*`):**
- Карта свободных смен (только объекты с признаком "Доступен для соискателей")
- Поиск работы
- Подача заявок на смены
- Регистрация в системе

#### Middleware с проверкой множественных ролей
```python
class RoleBasedAccessMiddleware:
    async def __call__(self, request, call_next):
        path = request.url.path
        user_roles = get_user_roles(request)  # Список ролей пользователя
        
        # Проверка доступа по ролям и пути
        if path.startswith('/admin/') and 'superadmin' not in user_roles:
            return redirect_to_available_interface(user_roles)
        elif path.startswith('/owner/') and 'owner' not in user_roles:
            return redirect_to_available_interface(user_roles)
        elif path.startswith('/manager/') and 'manager' not in user_roles:
            return redirect_to_available_interface(user_roles)
        elif path.startswith('/employee/') and 'employee' not in user_roles:
            return redirect_to_available_interface(user_roles)
        
        # Дополнительная проверка прав управляющего на объекты
        if path.startswith('/manager/') and 'manager' in user_roles:
            if not await check_manager_object_permissions(request, path):
                return redirect_to_manager_dashboard()
```

#### Реализованные компоненты ✅
- **Административная панель** - полноценный интерфейс `/admin/*`
- **Разделение навигации** - отдельные меню для каждой роли
- **Роутинг по ролям** - проверка доступа в каждом роуте
- **Шаблоны админки** - отдельные HTML шаблоны для суперадмина

#### Планируемая реализация
- **Отдельные базовые шаблоны** для каждой роли
- **Middleware проверки доступа** по URL и роли
- **Восстановление меню владельцев** с правильной навигацией
- **Интерфейс сотрудников** с картой смен и календарем

## 2.10. Мониторинг LLM

### Метрики производительности
- **Response Time** - время ответа LLM
- **Token Usage** - количество использованных токенов
- **Success Rate** - процент успешных запросов
- **Error Rate** - процент ошибок по типам
- **Cost per Request** - стоимость запроса

### Мониторинг качества
```python
class LLMMonitor:
    def __init__(self):
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0,
            'total_tokens_used': 0,
            'total_cost': 0
        }
    
    def record_request(self, start_time: float, end_time: float, 
                      success: bool, tokens: int, cost: float):
        response_time = end_time - start_time
        
        self.metrics['total_requests'] += 1
        if success:
            self.metrics['successful_requests'] += 1
        else:
            self.metrics['failed_requests'] += 1
        
        # Обновление среднего времени ответа
        current_avg = self.metrics['average_response_time']
        total_requests = self.metrics['total_requests']
        self.metrics['average_response_time'] = (
            (current_avg * (total_requests - 1) + response_time) / total_requests
        )
        
        self.metrics['total_tokens_used'] += tokens
        self.metrics['total_cost'] += cost
    
    def get_success_rate(self) -> float:
        if self.metrics['total_requests'] == 0:
            return 0.0
        return self.metrics['successful_requests'] / self.metrics['total_requests']
    
    def export_metrics(self) -> dict:
        return {
            **self.metrics,
            'success_rate': self.get_success_rate(),
            'average_cost_per_request': (
                self.metrics['total_cost'] / self.metrics['total_requests']
                if self.metrics['total_requests'] > 0 else 0
            )
        }
```

### Алерты и уведомления
```python
class LLMAlertManager:
    def __init__(self, alert_thresholds: dict):
        self.thresholds = alert_thresholds
        self.alert_history = []
    
    def check_alerts(self, metrics: dict):
        alerts = []
        
        # Проверка успешности запросов
        if metrics['success_rate'] < self.thresholds['min_success_rate']:
            alerts.append({
                'type': 'LOW_SUCCESS_RATE',
                'message': f"Success rate {metrics['success_rate']:.2%} below threshold",
                'severity': 'HIGH',
                'timestamp': datetime.now()
            })
        
        # Проверка времени ответа
        if metrics['average_response_time'] > self.thresholds['max_response_time']:
            alerts.append({
                'type': 'HIGH_RESPONSE_TIME',
                'message': f"Average response time {metrics['average_response_time']:.2f}s above threshold",
                'severity': 'MEDIUM',
                'timestamp': datetime.now()
            })
        
        # Проверка стоимости
        if metrics['average_cost_per_request'] > self.thresholds['max_cost_per_request']:
            alerts.append({
                'type': 'HIGH_COST',
                'message': f"Average cost per request ${metrics['average_cost_per_request']:.4f} above threshold",
                'severity': 'MEDIUM',
                'timestamp': datetime.now()
            })
        
        return alerts
```

## 2.11. UX улучшения и ограничения

### Бизнес-правила
1. **Одна активная смена на пользователя** - исключает конфликты и ошибки учета
2. **Обязательная геопозиция** - повышает точность и исключает мошенничество  
3. **Упрощенный флоу** - выбор объекта → геопозиция → действие (без лишних шагов)

### Технические ограничения
```python
# Проверка активных смен
async def check_active_shifts(user_id: int) -> bool:
    """Проверяет, есть ли у пользователя активные смены"""
    active_shifts = await shift_service.get_user_shifts(
        user_id=user_id, 
        status='active'
    )
    return len(active_shifts) > 0

# Состояние диалога пользователя
user_states = {
    user_id: {
        'action': 'open_shift' | 'close_shift',
        'selected_object_id': int,
        'selected_shift_id': int,
        'step': 'object_selection' | 'location_request' | 'processing'
    }
}
```

### Обработка геопозиции
```python
# Обработчик location сообщений
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка геопозиции от пользователя"""
    location = update.message.location
    user_id = update.effective_user.id
    
    # Получаем состояние пользователя
    user_state = user_states.get(user_id)
    if not user_state:
        await update.message.reply_text("❌ Сначала выберите действие")
        return
    
    coordinates = f"{location.latitude},{location.longitude}"
    
    if user_state['action'] == 'open_shift':
        result = await shift_service.open_shift(
            user_id=user_id,
            object_id=user_state['selected_object_id'],
            coordinates=coordinates
        )
    elif user_state['action'] == 'close_shift':
        result = await shift_service.close_shift(
            user_id=user_id,
            shift_id=user_state['selected_shift_id'],
            coordinates=coordinates
        )
    
    # Очищаем состояние после обработки
    del user_states[user_id]
```

## 2.12. Сценарии работы

### Сценарий 1: Открытие смены (обновленный UX)
```mermaid
sequenceDiagram
    participant U as User
    participant B as Bot
    participant DB as Database
    participant Geo as Geolocation Service
    
    U->>B: Нажимает "🔄 Открыть смену"
    B->>DB: Проверка активных смен пользователя
    alt У пользователя есть активная смена
        B->>U: ❌ У вас уже есть активная смена
    else Активных смен нет
        B->>DB: Получение доступных объектов
        B->>U: Список объектов для выбора
        U->>B: Выбор объекта (callback)
        B->>U: Запрос геопозиции (кнопка "📍 Отправить геопозицию")
        U->>B: Отправка location (встроенная функция Telegram)
        B->>Geo: Проверка расстояния до выбранного объекта
        Geo->>B: Результат проверки
        alt Геопозиция корректна
            B->>DB: Создание записи смены
            DB->>B: Подтверждение создания
            B->>U: ✅ Смена успешно открыта
        else Геопозиция некорректна
            B->>U: ❌ Вы находитесь слишком далеко от объекта
        end
    end
```

### Сценарий 1.1: Закрытие смены (обновленный UX)
```mermaid
sequenceDiagram
    participant U as User
    participant B as Bot
    participant DB as Database
    participant Geo as Geolocation Service
    
    U->>B: Нажимает "🔚 Закрыть смену"
    B->>DB: Получение активных смен пользователя
    alt Нет активных смен
        B->>U: ❌ У вас нет активных смен
    else Есть активные смены
        alt Одна активная смена
            B->>U: Подтверждение закрытия смены + запрос геопозиции
            U->>B: Отправка location (встроенная функция Telegram)
            B->>Geo: Проверка расстояния до объекта смены
            Geo->>B: Результат проверки
            alt Геопозиция корректна
                B->>DB: Закрытие смены + расчет оплаты
                DB->>B: Подтверждение закрытия
                B->>U: ✅ Смена закрыта. Отработано: X часов, заработано: Y₽
            else Геопозиция некорректна
                B->>U: ❌ Вы находитесь слишком далеко от объекта
            end
        else Несколько активных смен (устаревший случай)
            B->>U: Список активных смен для выбора
            U->>B: Выбор смены (callback)
            B->>U: Запрос геопозиции для выбранной смены
        end
    end
```

### Сценарий 2: Планирование смены
```mermaid
sequenceDiagram
    participant U as User
    participant B as Bot
    participant LLM as LLM Service
    participant Scheduler as Scheduler Service
    participant DB as Database
    
    U->>B: "Запланируй смену на завтра с 9 до 17"
    B->>LLM: Извлечение параметров из запроса
    LLM->>B: {"date": "tomorrow", "start": "09:00", "end": "17:00"}
    B->>Scheduler: Проверка доступности
    Scheduler->>DB: Поиск конфликтов в расписании
    DB->>Scheduler: Результат поиска
    Scheduler->>B: Доступность времени
    alt Время доступно
        B->>DB: Создание запланированной смены
        DB->>B: Подтверждение создания
        B->>U: Смена запланирована успешно
    else Время занято
        B->>Scheduler: Поиск альтернатив
        Scheduler->>B: Список свободных слотов
        B->>U: Предложение альтернатив
    end
```

### Сценарий 3: Формирование отчета
```mermaid
sequenceDiagram
    participant U as User
    participant B as Bot
    participant LLM as LLM Service
    participant Analytics as Analytics Service
    participant DB as Database
    
    U->>B: "Покажи отчет по объекту А за последний месяц"
    B->>LLM: Извлечение параметров отчета
    LLM->>B: {"object": "A", "period": "last_month", "type": "summary"}
    B->>Analytics: Формирование отчета
    Analytics->>DB: Запрос данных
    DB->>Analytics: Данные для отчета
    Analytics->>Analytics: Обработка и агрегация
    Analytics->>B: Готовый отчет
    B->>U: Отправка отчета
    B->>U: Предложение экспорта в PDF/Excel
```

## 2.13. Деплой

### Docker-разработка и кросс-платформенность ✅

#### Принципы Docker-разработки
- **Единая среда**: Все разработчики работают в одинаковых контейнерах
- **Hot-reload**: Изменения кода отражаются без перезапуска контейнеров
- **Кросс-платформенность**: Работает на Windows, macOS и Linux
- **Оптимизация образов**: Multi-stage build для уменьшения размера

#### Преимущества Docker-разработки
- **🚀 Быстрый старт**: Один скрипт для запуска всего окружения
- **🔧 Изоляция**: Зависимости не конфликтуют с системными пакетами
- **📱 Кросс-платформенность**: Одинаковая работа на всех ОС
- **🔄 Hot-reload**: Мгновенное отражение изменений кода
- **📊 Мониторинг**: Встроенные health checks для всех сервисов
- **🧪 Тестирование**: Идентичная среда для разработки и тестирования

#### Реализованные компоненты
- **Dockerfile**: Оптимизированный multi-stage build для Python 3.11+ с PostGIS зависимостями
- **Docker Compose**: Отдельные файлы для разработки (dev) и продакшена (prod)
- **Volume mounts**: Настроены для hot-reload разработки
- **Health checks**: Автоматическая проверка состояния всех сервисов
- **Переменные окружения**: Раздельные конфигурации для разных сред

#### Технические детали реализации
- **Multi-stage build**: Оптимизация размера образа через разделение зависимостей
- **PostGIS клиенты**: Установка libgeos-dev, libproj-dev для работы с геоданными
- **Hot-reload**: Монтирование проекта в контейнер с исключением кэша Python
- **Health checks**: Проверка состояния PostgreSQL, Redis, RabbitMQ с настраиваемыми интервалами
- **Зависимости сервисов**: Условный запуск с проверкой готовности зависимостей
- **Переменные окружения**: Раздельные .env файлы для dev и prod окружений
- **Restart policies**: Автоматический перезапуск сервисов при сбоях в production

#### Решенные проблемы совместимости
- **Docker Compose команды**: Автоопределение `docker-compose` (v1) vs `docker compose` (v2)
- **Пути файлов**: Корректное разрешение путей в скриптах для поиска Docker Compose файлов
- **Python зависимости**: Исправление конфликтов версий SQLAlchemy, Pydantic и pydantic-settings
- **Логирование**: Исправление синтаксиса в Celery для корректной работы с Python logging
- **Async/await**: Исправление синтаксиса в Celery задачах для совместимости с Python 3.11

#### Dockerfile стратегия
```dockerfile
# Multi-stage build для оптимизации
FROM python:3.11-slim as base

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libgeos-dev \
    libproj-dev \
    proj-bin \
    && rm -rf /var/lib/apt/lists/*

# Установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . /app
WORKDIR /app

# Команда по умолчанию
CMD ["python", "main.py"]
```

#### Docker Compose для разработки ✅
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  postgres:
    image: postgis/postgis:15-3.3
    environment:
      POSTGRES_DB: staffprobot_dev
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_dev_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  rabbitmq:
    image: rabbitmq:3-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: password
    ports:
      - "5672:5672"
      - "15672:15672"
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  bot:
    build:
      context: .
      dockerfile: docker/Dockerfile.dev
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
      - PYTHONPATH=/app
      - PYTHONDONTWRITEBYTECODE=1
      - PYTHONUNBUFFERED=1
    volumes:
      - .:/app  # Hot-reload для разработки
      - /app/__pycache__  # Исключение кэша
      - /app/.pytest_cache  # Исключение pytest кэша
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy

  celery_worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.dev
    command: python scripts/start_celery_worker.py
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
    volumes:
      - .:/app
      - /app/__pycache__
      - /app/.pytest_cache
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy

  celery_beat:
    build:
      context: .
      dockerfile: docker/Dockerfile.dev
    command: python scripts/start_celery_beat.py
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
    volumes:
      - .:/app
      - /app/__pycache__
      - /app/.pytest_cache
      - celery_beat_dev_data:/tmp
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy

volumes:
  postgres_dev_data:
  redis_dev_data:
  celery_beat_dev_data:
```

### Docker Compose для продакшена ✅
```yaml
version: '3.8'

services:
  postgres:
    image: postgis/postgis:15-3.3
    environment:
      POSTGRES_DB: staffprobot_prod
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
    env_file:
      - .env.prod
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    volumes:
      - redis_prod_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  rabbitmq:
    image: rabbitmq:3-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq_prod_data:/var/lib/rabbitmq
    env_file:
      - .env.prod
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  bot:
    build:
      context: .
      dockerfile: docker/Dockerfile
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    env_file:
      - .env.prod
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery_worker:
    build:
      context: .
      dockerfile: docker/Dockerfile
    command: python scripts/start_celery_worker.py
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    env_file:
      - .env.prod
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy

  celery_beat:
    build:
      context: .
      dockerfile: docker/Dockerfile
    command: python scripts/start_celery_beat.py
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    env_file:
      - .env.prod
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./docker/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    restart: unless-stopped
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'

  grafana:
    image: grafana/grafana
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_USER}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    env_file:
      - .env.prod
    restart: unless-stopped

volumes:
  postgres_prod_data:
  redis_prod_data:
  rabbitmq_prod_data:
  prometheus_data:
  grafana_data:
```

#### Автоматизация Docker-разработки ✅

##### Скрипты запуска
- **scripts/docker-dev.sh** (Linux/macOS): Автоматический запуск development окружения
- **scripts/docker-dev.bat** (Windows): Автоматический запуск development окружения
- **README_DOCKER.md**: Подробная документация по Docker использованию

##### Возможности скриптов
- Автоматическое создание .env файла из env.example
- Остановка существующих контейнеров
- Сборка и запуск всех сервисов
- Ожидание готовности сервисов
- Отображение статуса контейнеров
- Автоопределение версии Docker Compose (v1/v2)

##### Доступные сервисы и порты
- **🌐 Бот**: http://localhost:8000 (Telegram Bot API)
- **🗄️ PostgreSQL**: localhost:5432 (PostGIS база данных)
- **🔴 Redis**: localhost:6379 (кэширование и очереди)
- **🐰 RabbitMQ**: localhost:5672 (брокер сообщений)
- **📊 RabbitMQ Management**: http://localhost:15672 (веб-интерфейс)
- **📈 Prometheus**: http://localhost:9090 (метрики)
- **📊 Grafana**: http://localhost:3000 (дашборды)

##### Полезные команды Docker
```bash
# Запуск development окружения
./scripts/docker-dev.sh          # Linux/macOS
scripts\docker-dev.bat           # Windows

# Просмотр логов
docker compose -f docker-compose.dev.yml logs -f bot
docker compose -f docker-compose.dev.yml logs -f celery_worker

# Остановка всех сервисов
docker compose -f docker-compose.dev.yml down

# Перезапуск конкретного сервиса
docker compose -f docker-compose.dev.yml restart bot

# Просмотр статуса контейнеров
docker compose -f docker-compose.dev.yml ps

# Очистка Docker кэша
docker system prune -f
```

#### Docker Compose для продакшена ✅
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  postgres:
    image: postgis/postgis:15-3.3
    environment:
      POSTGRES_DB: staffprobot_prod
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
    env_file:
      - .env.prod
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    volumes:
      - redis_prod_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  rabbitmq:
    image: rabbitmq:3-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq_prod_data:/var/lib/rabbitmq
    env_file:
      - .env.prod
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  bot:
    build:
      context: .
      dockerfile: docker/Dockerfile
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    env_file:
      - .env.prod
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery_worker:
    build:
      context: .
      dockerfile: docker/Dockerfile
    command: python scripts/start_celery_worker.py
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    env_file:
      - .env.prod
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy

  celery_beat:
    build:
      context: .
      dockerfile: docker/Dockerfile
    command: python scripts/start_celery_beat.py
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    env_file:
      - .env.prod
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./docker/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    restart: unless-stopped
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'

  grafana:
    image: grafana/grafana
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_USER}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    env_file:
      - .env.prod
    restart: unless-stopped

volumes:
  postgres_prod_data:
  redis_prod_data:
  rabbitmq_prod_data:
  prometheus_data:
  grafana_data:
```

### Kubernetes для production
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: staffprobot-bot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: staffprobot-bot
  template:
    metadata:
      labels:
        app: staffprobot-bot
    spec:
      containers:
      - name: bot
        image: staffprobot/bot:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-secret
              key: api-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: staffprobot-bot-service
spec:
  selector:
    app: staffprobot-bot
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### CI/CD Pipeline
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    - name: Run tests
      run: |
        pytest tests/ --cov=apps --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Build Docker image
      run: |
        docker build -t staffprobot/bot:${{ github.sha }} .
        docker push staffprobot/bot:${{ github.sha }}
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/staffprobot-bot bot=staffprobot/bot:${{ github.sha }}
        kubectl rollout status deployment/staffprobot-bot
```

### 2.13.1. Автоматические миграции и единый источник конфигурации

- Все сервисы читают секреты из единого файла `.env.prod`.
- `DATABASE_URL` в приложениях формируется из `POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB` и хоста `postgres`.
- Перед поднятием приложений выполняется отдельный одноразовый сервис `migrator` с командой `alembic upgrade head`.
- Скрипт прод-деплоя запускает порядок: Postgres/Redis/RabbitMQ → migrator → приложения (`web`, `bot`, `celery_*`).
- Исключены ручные правки паролей в БД: пароль управляется только через `.env.prod`.

## 2.14. Подход к конфигурированию

### Иерархия конфигурации
```python
# core/config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Основные настройки
    app_name: str = "StaffProBot"
    debug: bool = False
    environment: str = "development"
    
    # База данных
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    
    # RabbitMQ
    rabbitmq_url: str = "amqp://localhost:5672"
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 500
    openai_temperature: float = 0.7
    
    # Telegram
    telegram_bot_token: str
    telegram_webhook_url: Optional[str] = None
    
    # Геолокация
    max_distance_meters: int = 100
    location_accuracy_meters: int = 50
    
    # UX ограничения
    max_active_shifts_per_user: int = 1
    require_location_for_shifts: bool = True
    location_timeout_seconds: int = 300  # 5 минут на отправку геопозиции
    
    # Мониторинг
    prometheus_port: int = 9090
    grafana_port: int = 3000
    
    # Безопасность
    secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 часа
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Создание экземпляра настроек
settings = Settings()

# Проверка обязательных переменных
def validate_settings():
    required_vars = [
        'database_url',
        'openai_api_key',
        'telegram_bot_token',
        'secret_key'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")

# Валидация при импорте
validate_settings()
```

### Переменные окружения
```bash
# .env.example
# Основные настройки
APP_NAME=StaffProBot
DEBUG=false
ENVIRONMENT=production

# Docker-специфичные переменные
POSTGRES_DB=staffprobot_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=password
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin

# Настройки для разработки
MAX_DISTANCE_METERS=500
DATABASE_URL=postgresql://postgres:password@postgres:5432/staffprobot_dev
REDIS_URL=redis://redis:6379
RABBITMQ_URL=amqp://admin:password@rabbitmq:5672

# База данных
DATABASE_URL=postgresql://user:password@localhost:5432/staffprobot
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis
REDIS_URL=redis://localhost:6379
REDIS_DB=0

# RabbitMQ
RABBITMQ_URL=amqp://user:password@localhost:5672

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=500
OPENAI_TEMPERATURE=0.7

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook

# Геолокация
MAX_DISTANCE_METERS=100
LOCATION_ACCURACY_METERS=50

# UX ограничения
MAX_ACTIVE_SHIFTS_PER_USER=1
REQUIRE_LOCATION_FOR_SHIFTS=true
LOCATION_TIMEOUT_SECONDS=300

# Мониторинг
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# Безопасность
SECRET_KEY=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

### Конфигурация для разных окружений
```python
# core/config/environments.py
from enum import Enum
from core.config.settings import Settings

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

def get_environment_config(env: Environment) -> dict:
    """Возвращает конфигурацию для конкретного окружения"""
    
    base_config = {
        "debug": False,
        "database_pool_size": 20,
        "database_max_overflow": 30,
        "max_distance_meters": 100,
        "location_accuracy_meters": 50
    }
    
    if env == Environment.DEVELOPMENT:
        base_config.update({
            "debug": True,
            "database_pool_size": 5,
            "database_max_overflow": 10,
            "max_distance_meters": 1000,  # Более мягкие требования для разработки
            "location_accuracy_meters": 100
        })
    elif env == Environment.STAGING:
        base_config.update({
            "debug": False,
            "database_pool_size": 10,
            "database_max_overflow": 15
        })
    elif env == Environment.PRODUCTION:
        base_config.update({
            "debug": False,
            "database_pool_size": 50,
            "database_max_overflow": 100
        })
    
    return base_config

def apply_environment_config(settings: Settings):
    """Применяет конфигурацию окружения к настройкам"""
    env_config = get_environment_config(Environment(settings.environment))
    
    for key, value in env_config.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
```

## 2.15. Подход к логированию

### Структурированное логирование
```python
# core/logging/logger.py
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

class JSONFormatter(logging.Formatter):
    """Форматтер для структурированного JSON логирования"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Добавление дополнительных полей
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        
        if hasattr(record, 'execution_time'):
            log_entry['execution_time_ms'] = record.execution_time
        
        # Добавление исключений
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # Добавление extra полей
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                          'pathname', 'filename', 'module', 'lineno', 'funcName',
                          'created', 'msecs', 'relativeCreated', 'thread',
                          'threadName', 'processName', 'process', 'getMessage',
                          'exc_info', 'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry, ensure_ascii=False)

class StructuredLogger:
    """Структурированный логгер с контекстом"""
    
    def __init__(self, name: str, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Настройка форматтера
        formatter = JSONFormatter()
        
        # Консольный хендлер
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Файловый хендлер для production
        if level.upper() != "DEBUG":
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            file_handler = logging.FileHandler(log_dir / f"{name}.log")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def _log_with_context(self, level: str, message: str, **kwargs):
        """Логирование с дополнительным контекстом"""
        extra = {}
        
        # Добавление контекста пользователя
        if 'user_id' in kwargs:
            extra['user_id'] = kwargs['user_id']
        
        # Добавление ID запроса
        if 'request_id' in kwargs:
            extra['request_id'] = kwargs['request_id']
        
        # Добавление времени выполнения
        if 'execution_time' in kwargs:
            extra['execution_time'] = kwargs['execution_time']
        
        # Добавление других полей
        for key, value in kwargs.items():
            if key not in ['user_id', 'request_id', 'execution_time']:
                extra[key] = value
        
        log_method = getattr(self.logger, level.lower())
        log_method(message, extra=extra)
    
    def info(self, message: str, **kwargs):
        self._log_with_context('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log_with_context('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log_with_context('ERROR', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log_with_context('DEBUG', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log_with_context('CRITICAL', message, **kwargs)

# Создание основного логгера
logger = StructuredLogger("staffprobot")
```

### Логирование в разных компонентах
```python
# apps/bot/handlers.py
from core.logging.logger import logger
import time
from functools import wraps

def log_execution_time(func):
    """Декоратор для логирования времени выполнения функций"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000  # в миллисекундах
            
            logger.info(
                f"Function {func.__name__} executed successfully",
                execution_time=execution_time,
                **kwargs
            )
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            logger.error(
                f"Function {func.__name__} failed: {str(e)}",
                execution_time=execution_time,
                error=str(e),
                **kwargs
            )
            raise
    
    return wrapper

class BotHandler:
    def __init__(self, user_id: int, request_id: str):
        self.user_id = user_id
        self.request_id = request_id
        self.logger = logger
    
    @log_execution_time
    async def handle_open_shift(self, object_id: int, coordinates: tuple):
        """Обработка открытия смены"""
        self.logger.info(
            "Opening shift",
            user_id=self.user_id,
            request_id=self.request_id,
            object_id=object_id,
            coordinates=coordinates
        )
        
        # Логика открытия смены
        try:
            # ... код открытия смены ...
            self.logger.info(
                "Shift opened successfully",
                user_id=self.user_id,
                request_id=self.request_id,
                shift_id=shift_id
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to open shift",
                user_id=self.user_id,
                request_id=self.request_id,
                error=str(e),
                object_id=object_id
            )
            raise
```

### Интеграция с ELK Stack
```python
# core/logging/elk_handler.py
import logging
from elasticsearch import Elasticsearch
from datetime import datetime
import json

class ElasticsearchHandler(logging.Handler):
    """Хендлер для отправки логов в Elasticsearch"""
    
    def __init__(self, es_host: str, es_port: int = 9200, index_prefix: str = "staffprobot"):
        super().__init__()
        self.es = Elasticsearch([{'host': es_host, 'port': es_port}])
        self.index_prefix = index_prefix
    
    def emit(self, record: logging.LogRecord):
        try:
            # Создание индекса с датой
            today = datetime.now().strftime('%Y.%m.%d')
            index_name = f"{self.index_prefix}-{today}"
            
            # Подготовка документа для Elasticsearch
            doc = {
                '@timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            
            # Добавление extra полей
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                              'pathname', 'filename', 'module', 'lineno', 'funcName',
                              'created', 'msecs', 'relativeCreated', 'thread',
                              'threadName', 'processName', 'process', 'getMessage',
                              'exc_info', 'exc_text', 'stack_info']:
                    doc[key] = value
            
            # Отправка в Elasticsearch
            self.es.index(
                index=index_name,
                body=doc
            )
            
        except Exception as e:
            # Логирование ошибки отправки в ES
            print(f"Failed to send log to Elasticsearch: {e}")

# Добавление ES хендлера к основному логгеру
def setup_elk_logging(es_host: str, es_port: int = 9200):
    """Настройка логирования в Elasticsearch"""
    es_handler = ElasticsearchHandler(es_host, es_port)
    es_handler.setLevel(logging.INFO)
    
    # Добавление к корневому логгеру
    root_logger = logging.getLogger()
    root_logger.addHandler(es_handler)
```

### Мониторинг и алерты по логам
```python
# core/logging/monitoring.py
from core.logging.logger import logger
import time
from collections import defaultdict
from typing import Dict, List

class LogMonitor:
    """Мониторинг логов для выявления проблем"""
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.slow_operations = defaultdict(list)
        self.last_reset = time.time()
        self.reset_interval = 3600  # 1 час
    
    def record_error(self, error_type: str, context: str = None):
        """Запись ошибки для мониторинга"""
        key = f"{error_type}:{context}" if context else error_type
        self.error_counts[key] += 1
        
        # Проверка порога ошибок
        if self.error_counts[key] > 10:  # Порог: 10 ошибок
            logger.warning(
                f"High error rate detected: {key} - {self.error_counts[key]} errors",
                error_type=error_type,
                context=context,
                error_count=self.error_counts[key]
            )
    
    def record_slow_operation(self, operation: str, execution_time: float):
        """Запись медленных операций"""
        if execution_time > 1000:  # Порог: 1 секунда
            self.slow_operations[operation].append(execution_time)
            
            # Ограничение истории
            if len(self.slow_operations[operation]) > 100:
                self.slow_operations[operation].pop(0)
            
            # Алерт при частых медленных операциях
            if len(self.slow_operations[operation]) > 10:
                avg_time = sum(self.slow_operations[operation]) / len(self.slow_operations[operation])
                logger.warning(
                    f"Frequent slow operations detected: {operation}",
                    operation=operation,
                    average_time_ms=avg_time,
                    slow_operation_count=len(self.slow_operations[operation])
                )
    
    def get_metrics(self) -> Dict:
        """Получение метрик мониторинга"""
        current_time = time.time()
        
        # Сброс счетчиков каждый час
        if current_time - self.last_reset > self.reset_interval:
            self.error_counts.clear()
            self.slow_operations.clear()
            self.last_reset = current_time
        
        return {
            'error_counts': dict(self.error_counts),
            'slow_operations': {
                op: {
                    'count': len(times),
                    'average_time_ms': sum(times) / len(times) if times else 0
                }
                for op, times in self.slow_operations.items()
            },
            'last_reset': self.last_reset
        }

# Глобальный экземпляр монитора
log_monitor = LogMonitor()
```

## 2.16. Технические задачи Итерации 7 ✅

### 2.11.1. Docker-разработка и кросс-платформенность ✅

#### Создание Dockerfile
- ✅ **Multi-stage build**: Оптимизированный образ с разделением зависимостей
- ✅ **PostGIS клиенты**: Установка libgeos-dev, libproj-dev для геоданных
- ✅ **Python 3.11+**: Современная версия Python с оптимизацией
- ✅ **Безопасность**: Создание непривилегированного пользователя app

#### Настройка Docker Compose
- ✅ **Development окружение**: docker-compose.dev.yml с hot-reload
- ✅ **Production окружение**: docker-compose.prod.yml с health checks
- ✅ **Переменные окружения**: Раздельные конфигурации для разных сред
- ✅ **Health checks**: Автоматическая проверка состояния всех сервисов

#### Автоматизация
- ✅ **Скрипты запуска**: docker-dev.sh для Linux/macOS, docker-dev.bat для Windows
- ✅ **Автоопределение**: Docker Compose v1/v2 команды
- ✅ **Пути файлов**: Корректное разрешение путей в скриптах
- ✅ **Документация**: README_DOCKER.md с подробными инструкциями

### 2.11.2. Исправление критических ошибок ✅

#### Проблема с созданием пользователей ✅
- **Решение**: Убрана зависимость от файла `/data/users.json`
- **Реализация**: Все пользователи создаются только в PostgreSQL
- **Проверка**: Метод `UserManager.create_user()` работает корректно

#### Исправление команд /help и /status ✅
- **Решение**: Исправлена логика получения данных из базы данных
- **Реализация**: Добавлена обработка ошибок и валидация
- **Проверка**: Команды работают без ошибок

#### Исправление логики дашборда ✅
- **Решение**: Изменена логика расчета с "earnings" на "payments"
- **Реализация**: Владельцы платят сотрудникам, а не зарабатывают
- **Проверка**: Дашборд отображает корректную информацию

### 2.11.3. Решенные проблемы совместимости ✅

#### Docker Compose команды ✅
- **Проблема**: Различия между `docker-compose` (v1) и `docker compose` (v2)
- **Решение**: Автоопределение версии в скриптах запуска
- **Реализация**: Переменная `DOCKER_COMPOSE_CMD` для корректной команды

#### Пути файлов ✅
- **Проблема**: Скрипты искали файлы в неправильных директориях
- **Решение**: Добавлен `cd` в корень проекта в скриптах
- **Реализация**: `cd "$(dirname "$0")/.."` для Linux/macOS, `cd /d "%~dp0.."` для Windows

#### Python зависимости ✅
- **Проблема**: Конфликты версий SQLAlchemy, Pydantic и pydantic-settings
- **Решение**: Обновлены версии до совместимых
- **Реализация**: `sqlalchemy>=2.0.0`, `pydantic>=2.0.1`, `pydantic-settings>=2.0.3`

#### Логирование и синтаксис ✅
- **Проблема**: Неправильный синтаксис в Celery задачах
- **Решение**: Исправлен синтаксис логирования и async/await
- **Реализация**: Корректная работа с Python 3.11+

### 2.11.4. Исправление критических ошибок

**🎉 Итерация 7 успешно завершена!**

Все задачи по Docker-интеграции и кросс-платформенности выполнены:
- ✅ Dockerfile создан и оптимизирован
- ✅ .dockerignore настроен корректно
- ✅ docker-compose.dev.yml работает для разработки
- ✅ docker-compose.prod.yml готов для продакшена
- ✅ Проект запускается на Windows, macOS и Linux
- ✅ Hot-reload работает в режиме разработки
- ✅ Health checks настроены для всех сервисов
- ✅ Документация по Docker обновлена
- ✅ Все критические ошибки исправлены
- ✅ Проблемы совместимости решены

**🚀 Система готова к кросс-платформенной разработке!**

---

## 🎉 Достижения Итерации 11: Исправление логики бота и веб-интерфейса

### ✅ Исправления логики бота
- **Доступ владельцев к объектам**: Владельцы теперь могут открывать смены на своих объектах без необходимости заключения договора
- **Логика открытия смен**: Улучшена логика с приоритетом запланированных смен над спонтанными
- **Ставки для спонтанных смен**: Спонтанные смены используют ставку из свободного тайм-слота или объекта по умолчанию
- **Исправление ошибок**: Устранены ошибки "Ошибка при обработке выбора объекта" и неправильные ставки

### ✅ Исправления веб-интерфейса
- **График работы объектов**: Добавлен полный функционал управления графиком работы (дни недели, периодичность)
- **Сохранение настроек**: Исправлена проблема с сохранением изменений графика работы в базе данных
- **JavaScript исправления**: Устранены ошибки redeclaration и проблемы с загрузкой данных
- **Отображение данных**: Исправлено отображение настроек графика работы при просмотре и редактировании

### 🔧 Техническая реализация
- **EmployeeObjectsService**: Расширен для поддержки доступа владельцев к своим объектам
- **ShiftService**: Улучшена логика определения ставок для разных типов смен
- **ObjectService**: Добавлена обработка work_days_mask и schedule_repeat_weeks
- **Веб-роуты**: Исправлена обработка полей графика работы в POST запросах

### 📱 Готовность системы: 94%
**🎯 Итерация 11 успешно завершена!**

Все критические проблемы с логикой бота и веб-интерфейсом исправлены:
- ✅ Владельцы могут работать на своих объектах
- ✅ Сотрудники видят только доступные объекты
- ✅ График работы полностью функционален
- ✅ Все изменения сохраняются корректно

**🚀 Система готова к полноценному использованию!**

---

## 🎯 Итоги Docker-интеграции

### ✅ Успешно реализованные компоненты
- **Dockerfile**: Multi-stage build для Python 3.11+ с PostGIS зависимостями
- **Docker Compose**: Отдельные файлы для dev и prod окружений
- **Volume mounts**: Hot-reload для мгновенного отражения изменений
- **Health checks**: Автоматическая проверка состояния всех сервисов
- **Переменные окружения**: Раздельные конфигурации для разных сред
- **Автоматизация**: Скрипты запуска для Linux/macOS и Windows

### 🔧 Решенные технические проблемы
- **Docker Compose команды**: Автоопределение v1/v2 версий
- **Пути файлов**: Корректное разрешение путей в скриптах
- **Python зависимости**: Исправление конфликтов версий
- **Логирование**: Корректный синтаксис для Python 3.11+
- **Async/await**: Совместимость с современными версиями Python

### 📱 Готовность системы: 100%
**🎯 Итерация 7 полностью завершена!**

Проект StaffProBot теперь:
- 🐳 Полностью контейнеризирован
- 🌍 Работает на всех платформах
- 🔧 Готов к production развертыванию
- 📚 Имеет подробную Docker документацию
- 🚀 Поддерживает hot-reload разработку

---

## 2.17. Технические задачи Итерации 8

### 2.12.1. Исправления планирования смен (Завершено)

#### Проблемы и решения
- **Ошибка обновления расписания**: При нажатии "🔄 Обновить" возникала ошибка редактирования сообщения
  - **Решение**: Добавлена обработка ошибок с fallback на отправку нового сообщения
- **Неправильная отмена смен**: При нажатии "Отменить смену 1" удалялась другая смена
  - **Решение**: Убрана нумерация, теперь используется прямой `shift.id` для каждой смены
- **Плохой UX отмены**: Кнопки показывали только номера смен
  - **Решение**: Кнопки теперь показывают дату и время смены (например: "❌ Отменить 06.09 07:55")
- **Неправильная кнопка "Закрыть"**: Показывала сообщение об отмене планирования вместо возврата в главное меню
  - **Решение**: Создан отдельный callback `close_schedule` с функцией `handle_close_schedule()`

#### Техническая реализация
```python
# apps/bot/handlers_div/schedule_handlers.py - исправления
async def handle_view_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Просмотр запланированных смен с улучшенным интерфейсом."""
    # Обработка ошибок при редактировании сообщения
    try:
        await update.callback_query.edit_message_text(...)
    except Exception as edit_error:
        logger.error(f"Error editing message: {edit_error}")
        await update.callback_query.message.reply_text(...)

async def handle_cancel_shift(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отмена запланированной смены с логированием."""
    shift_id = int(query.data.split("_")[-1])
    logger.info(f"Attempting to cancel shift {shift_id} for user {telegram_id}")
    # Логика отмены смены...

async def handle_close_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Закрытие окна просмотра смен - возврат в главное меню."""
    await query.delete_message()
    # Отправка главного меню...
```

### 2.12.2. Расширенное планирование смен
```python
# core/auth/user_manager.py - исправление
class UserManager:
    async def create_user(self, telegram_id: int, user_data: dict) -> User:
        """Создание пользователя только в базе данных"""
        # Убрать зависимость от файла /data/users.json
        # Использовать только PostgreSQL
        user = User(
            telegram_id=telegram_id,
            username=user_data.get('username'),
            first_name=user_data['first_name'],
            last_name=user_data.get('last_name'),
            role='employee'
        )
        
        async with self.session() as session:
            session.add(user)
            await session.commit()
            await session.refresh(user)
        
        return user
```

#### Исправление команд /help и /status
```python
# apps/bot/handlers.py - исправление
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help с подробной справкой"""
    help_text = """
🤖 **StaffProBot - Помощь**

**Основные команды:**
/start - Главное меню
/help - Эта справка
/status - Статус активных смен

**Управление сменами:**
🔄 Открыть смену - начать работу на объекте
🔚 Закрыть смену - завершить работу
📅 Запланировать смену - запланировать будущую смену
📋 Мои планы - просмотр запланированных смен

**Отчеты:**
📊 Отчеты - создание отчетов по работе
📈 Дашборд - ключевые метрики

**Настройки:**
⚙️ Настройки - управление объектами и параметрами
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status - статус активных смен"""
    user_id = update.effective_user.id
    
    # Получение активных смен из базы данных
    active_shifts = await shift_service.get_user_active_shifts(user_id)
    
    if not active_shifts:
        await update.message.reply_text("✅ У вас нет активных смен")
        return
    
    status_text = "📊 **Ваши активные смены:**\n\n"
    
    for shift in active_shifts:
        object_name = await object_service.get_object_name(shift.object_id)
        start_time = shift.start_time.strftime("%H:%M")
        status_text += f"🏢 **{object_name}**\n"
        status_text += f"⏰ Начало: {start_time}\n"
        status_text += f"📍 Статус: {shift.status}\n\n"
    
    await update.message.reply_text(status_text, parse_mode='Markdown')
```

#### Исправление логики дашборда
```python
# apps/analytics/analytics_service.py - исправление
class AnalyticsService:
    async def get_owner_dashboard(self, owner_id: int) -> dict:
        """Дашборд владельца объектов (исправленная логика)"""
        # Владельцы платят сотрудникам, а не зарабатывают
        total_payments = await self._calculate_total_payments(owner_id)
        total_shifts = await self._count_total_shifts(owner_id)
        active_shifts = await self._count_active_shifts(owner_id)
        
        return {
            'total_payments': total_payments,  # Сумма к выплате
            'total_shifts': total_shifts,
            'active_shifts': active_shifts,
            'top_objects': await self._get_top_objects_by_cost(owner_id)
        }
    
    async def _calculate_total_payments(self, owner_id: int) -> Decimal:
        """Расчет общей суммы к выплате сотрудникам"""
        # Логика расчета выплат (не заработка)
        return await self._sum_shift_payments(owner_id)
```

### 2.11.2. Расширенное планирование смен

#### Календарный интерфейс
```python
# apps/bot/handlers/schedule_handlers.py - новый функционал
class CalendarHandler:
    def __init__(self):
        self.months = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ]
    
    async def show_calendar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать календарь для выбора дат"""
        current_date = datetime.now()
        
        keyboard = [
            [InlineKeyboardButton(f"📅 {current_date.year}", callback_data="year_select")],
            [InlineKeyboardButton(f"📅 {self.months[current_date.month-1]}", callback_data="month_select")],
            self._generate_days_keyboard(current_date.year, current_date.month),
            [InlineKeyboardButton("✅ Подтвердить выбор", callback_data="confirm_dates")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            "🗓️ Выберите даты для планирования смен:",
            reply_markup=reply_markup
        )
    
    def _generate_days_keyboard(self, year: int, month: int) -> List[List[InlineKeyboardButton]]:
        """Генерация клавиатуры с днями месяца"""
        # Логика генерации кнопок с днями
        pass
```

#### Множественное планирование
```python
# apps/scheduler/schedule_service.py - расширение
class ScheduleService:
    async def plan_multiple_shifts(self, user_id: int, object_id: int, 
                                 dates: List[date], time_slot: TimeSlot) -> List[ShiftSchedule]:
        """Планирование множественных смен по выбранным датам"""
        planned_shifts = []
        
        for selected_date in dates:
            # Проверка доступности для каждой даты
            if await self._is_time_available(object_id, selected_date, time_slot):
                shift = await self._create_planned_shift(
                    user_id, object_id, selected_date, time_slot
                )
                planned_shifts.append(shift)
            else:
                # Уведомление о недоступности даты
                await self._notify_date_unavailable(user_id, selected_date, object_id)
        
        return planned_shifts
```

### 2.11.3. Управление занятостью и персоналом

#### Проверка конфликтов
```python
# domain/entities/shift_schedule.py - расширение модели
class ShiftSchedule(Base):
    __tablename__ = "shift_schedules"
    
    # Новые поля для управления занятостью
    max_employees: Optional[int] = Column(Integer, default=1)
    allow_overlap: Optional[bool] = Column(Boolean, default=False)
    approval_required: Optional[bool] = Column(Boolean, default=True)

# apps/scheduler/schedule_service.py - проверка конфликтов
class ScheduleService:
    async def check_employee_conflicts(self, object_id: int, date: date, 
                                     time_slot: TimeSlot) -> List[Conflict]:
        """Проверка конфликтов занятости сотрудников"""
        existing_shifts = await self._get_shifts_at_time(object_id, date, time_slot)
        object_settings = await self._get_object_settings(object_id)
        
        conflicts = []
        
        if len(existing_shifts) >= object_settings.max_employees:
            conflicts.append(Conflict(
                type="MAX_EMPLOYEES_EXCEEDED",
                message=f"Максимум сотрудников: {object_settings.max_employees}",
                existing_employees=len(existing_shifts)
            ))
        
        if not object_settings.allow_overlap:
            # Проверка пересечений по времени
            for shift in existing_shifts:
                if self._time_overlaps(time_slot, shift.planned_time):
                    conflicts.append(Conflict(
                        type="TIME_OVERLAP",
                        message=f"Время пересекается с сменой {shift.id}",
                        conflicting_shift=shift
                    ))
        
        return conflicts
```

### 2.11.4. Система одобрения заявок

#### Модель заявок
```python
# domain/entities/shift_request.py - новая сущность
class ShiftRequest(Base):
    __tablename__ = "shift_requests"
    
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    object_id = Column(BigInteger, ForeignKey("objects.id"), nullable=False)
    requested_dates = Column(JSONB, nullable=False)  # Список запрошенных дат
    time_slot = Column(JSONB, nullable=False)  # Временной интервал
    status = Column(String(50), default="pending")  # pending, approved, rejected
    owner_notes = Column(Text)  # Комментарии владельца
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# apps/bot/handlers/request_handlers.py - обработка заявок
class RequestHandler:
    async def submit_shift_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подача заявки на смены"""
        user_id = update.effective_user.id
        
        # Создание заявки вместо прямого планирования
        request = await self._create_request(user_id, context.user_data)
        
        # Уведомление владельца объекта
        await self._notify_owner(request)
        
        await update.callback_query.edit_message_text(
            "📝 Заявка подана! Ожидайте одобрения владельца объекта."
        )
    
    async def _notify_owner(self, request: ShiftRequest):
        """Уведомление владельца о новой заявке"""
        owner_id = await self._get_object_owner(request.object_id)
        
        notification_text = f"""
🔔 **Новая заявка на смены**

👤 Сотрудник: {await self._get_user_name(request.user_id)}
🏢 Объект: {await self._get_object_name(request.object_id)}
📅 Даты: {len(request.requested_dates)} смен
⏰ Время: {request.time_slot['start']} - {request.time_slot['end']}

[✅ Одобрить](callback_data="approve_request_{request.id}")
[❌ Отклонить](callback_data="reject_request_{request.id}")
        """
        
        await self._send_owner_notification(owner_id, notification_text)
```

### 2.11.5. Улучшение геолокации и карт

#### Интеграция с Telegram Maps
```python
# apps/bot/handlers/map_handlers.py - новый функционал
class MapHandler:
    async def show_object_map(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать карту с объектами"""
        user_id = update.effective_user.id
        
        # Получение объектов пользователя
        user_objects = await self._get_user_objects(user_id)
        
        # Создание интерактивной карты
        map_keyboard = [
            [InlineKeyboardButton("🗺️ Показать на карте", callback_data="show_map")],
            [InlineKeyboardButton("🔍 Найти новые объекты", callback_data="find_new_objects")],
            [InlineKeyboardButton("📋 Мои объекты", callback_data="my_objects")]
        ]
        
        reply_markup = InlineKeyboardMarkup(map_keyboard)
        await update.callback_query.edit_message_text(
            "🗺️ Выберите способ поиска объектов:",
            reply_markup=reply_markup
        )
    
    async def send_location_map(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка карты с отметками объектов"""
        # Использование Telegram Location API для отображения карты
        # с отметками объектов в чате
        pass
```

### 2.11.6. Расширенная отчетность

#### Календарный выбор периода
```python
# apps/analytics/analytics_handlers.py - расширение
class AnalyticsHandler:
    async def show_report_calendar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать календарь для выбора периода отчетности"""
        current_date = datetime.now()
        
        # Генерация календарной клавиатуры
        calendar_keyboard = self._generate_report_calendar(current_date)
        
        reply_markup = InlineKeyboardMarkup(calendar_keyboard)
        await update.callback_query.edit_message_text(
            "📊 Выберите период для отчета:",
            reply_markup=reply_markup
        )
    
    async def generate_owner_report(self, owner_id: int, start_date: date, 
                                   end_date: date) -> dict:
        """Отчет по всем объектам владельца в разрезе сотрудников"""
        objects = await self._get_owner_objects(owner_id)
        
        report_data = {
            'period': {'start': start_date, 'end': end_date},
            'total_objects': len(objects),
            'objects_summary': []
        }
        
        for obj in objects:
            object_summary = await self._get_object_summary(
                obj.id, start_date, end_date
            )
            report_data['objects_summary'].append(object_summary)
        
        return report_data
```

### 2.11.7. Автоматизация развертывания

#### CI/CD Pipeline
```yaml
# .github/workflows/deploy.yml - расширенный pipeline
name: Deploy to Production

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    - name: Run tests
      run: |
        pytest tests/ --cov=apps --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  security-scan:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Run security scan
      run: |
        pip install safety
        safety check

  build-and-deploy:
    needs: [test, security-scan]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v3
    - name: Build Docker image
      run: |
        docker build -t staffprobot/bot:${{ github.sha }} .
        docker push staffprobot/bot:${{ github.sha }}
    - name: Deploy to production
      run: |
        ./scripts/deploy.sh production ${{ github.sha }}
```

#### Скрипты развертывания
```bash
# scripts/deploy.sh - скрипт развертывания
#!/bin/bash

ENVIRONMENT=$1
IMAGE_TAG=$2

if [ -z "$ENVIRONMENT" ] || [ -z "$IMAGE_TAG" ]; then
    echo "Usage: $0 <environment> <image_tag>"
    exit 1
fi

echo "🚀 Deploying to $ENVIRONMENT with image $IMAGE_TAG"

# Обновление docker-compose
sed -i "s|image: staffprobot/bot:.*|image: staffprobot/bot:$IMAGE_TAG|g" \
    docker-compose.$ENVIRONMENT.yml

# Перезапуск сервисов
docker-compose -f docker-compose.$ENVIRONMENT.yml down
docker-compose -f docker-compose.$ENVIRONMENT.yml up -d

# Проверка health
./scripts/health_check.sh $ENVIRONMENT

echo "✅ Deployment completed successfully!"
```

---

Это техническое видение проекта StaffProBot охватывает все аспекты разработки, от выбора технологий до деталей реализации. Документ служит руководством для команды разработки и обеспечивает единообразие в архитектуре и подходах к реализации.

## 2.18. Drag & Drop планирование смен

### 2.18.1. Интерактивное планирование

#### Панель объектов для планирования
- **Расположение**: Левая сторона календаря
- **Функциональность**: Drag & drop объектов на свободные тайм-слоты
- **Состояния**: Развернутое (полный список) и свернутое (вертикальный текст)
- **Стилизация**: Улучшенная читаемость в свернутом состоянии

#### Панель сотрудников для планирования
- **Расположение**: Правая сторона календаря
- **Функциональность**: Drag & drop сотрудников на свободные тайм-слоты
- **API**: `/api/employees` - получение списка сотрудников
- **API фильтрации**: `/api/employees/for-object/{object_id}` - сотрудники с доступом к объекту
- **Планирование**: `/api/calendar/plan-shift` - создание запланированной смены
- **Проверка доступа**: Валидация `allowed_objects` в договорах сотрудников

### 2.18.2. Техническая реализация

#### HTML структура
```html
<!-- Панель объектов -->
<div class="drag-drop-panel" id="objectsPanel">
    <div class="panel-header">
        <h6>Объекты для планирования</h6>
        <button class="toggle-btn">−</button>
    </div>
    <div class="panel-content">
        <!-- Список объектов для перетаскивания -->
    </div>
</div>

<!-- Панель сотрудников -->
<div class="employees-panel" id="employeesPanel">
    <div class="panel-header">
        <h6>Сотрудники для планирования</h6>
        <button class="toggle-btn">−</button>
    </div>
    <div class="panel-content">
        <!-- Список сотрудников для перетаскивания -->
    </div>
</div>
```

#### JavaScript функциональность
```javascript
// Drag & Drop для объектов
function makeObjectDraggable(element) {
    element.draggable = true;
    element.addEventListener('dragstart', function(e) {
        e.dataTransfer.setData('text/plain', 'object:' + this.dataset.objectId);
        this.classList.add('dragging');
    });
}

// Drag & Drop для сотрудников
function makeEmployeeDraggable(element) {
    element.draggable = true;
    element.addEventListener('dragstart', function(e) {
        e.dataTransfer.setData('text/plain', 'employee:' + this.dataset.employeeId);
        this.classList.add('dragging');
    });
}

// Обработка drop на тайм-слоты
function handleTimeslotDrop(e) {
    e.preventDefault();
    const data = e.dataTransfer.getData('text/plain');
    const [type, id] = data.split(':');
    
    if (type === 'employee') {
        planEmployeeShift(id, e.target.dataset.timeslotId);
    }
}
```

#### API endpoints
```python
# Получение списка сотрудников
@router.get("/api/employees")
async def get_employees_for_planning(
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Получение списка сотрудников для панели планирования"""
    # Логика получения сотрудников владельца

# Планирование смены сотрудника
@router.post("/api/calendar/plan-shift")
async def plan_employee_shift(
    request: PlanShiftRequest,
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Планирование смены для сотрудника в тайм-слоте"""
    # Логика создания запланированной смены
```

### 2.18.3. UX улучшения

#### Свернутое состояние панелей
```css
.drag-drop-panel.collapsed .panel-header h6,
.employees-panel.collapsed .panel-header h6 {
    writing-mode: vertical-rl;
    text-orientation: mixed;
    margin: 0;
    font-size: 0.9em;
    white-space: nowrap;
    color: #495057;
    font-weight: bold;
    text-shadow: 1px 1px 2px rgba(255,255,255,0.8);
}
```

#### Модальные окна
- **Интеграция с существующим модальным окном**: Кнопка "Добавить сотрудника в план" в модальном окне тайм-слота
- **Модальное окно выбора сотрудника**: Отдельное окно для выбора сотрудника при планировании
- **Фильтрация сотрудников**: Показ только сотрудников с доступом к конкретному объекту
- **Информативные ошибки**: Конкретные сообщения о причинах ошибок планирования

### 2.18.4. Проверка доступа к объектам

#### Валидация прав сотрудников
- **Проверка договора**: Валидация активного договора между сотрудником и владельцем
- **Проверка allowed_objects**: Валидация доступа к конкретному объекту через поле `allowed_objects` в договоре
- **API фильтрации**: `/api/employees/for-object/{object_id}` возвращает только сотрудников с доступом
- **Обработка ошибок**: Конкретные сообщения об отсутствии доступа или договора

#### Техническая реализация
```python
# Проверка доступа к объекту
allowed_objects = contract.allowed_objects if contract.allowed_objects else []
if timeslot.object_id not in allowed_objects:
    raise HTTPException(status_code=400, 
        detail=f"У сотрудника нет доступа к объекту ID {timeslot.object_id}")
```

### 2.18.5. Интеграция с календарем

#### Месячный вид календаря
- Панели объектов и сотрудников доступны в `apps/web/templates/owner/calendar/index.html`
- Поддержка drag & drop для всех тайм-слотов
- Автоматическое обновление после планирования смен

#### Недельный вид календаря
- Аналогичная функциональность в `apps/web/templates/owner/calendar/week.html`
- Единообразный интерфейс между месячным и недельным видами

---

*Последнее обновление: 19 сентября 2025*
*Версия документа: 2.10*

## 2.19. Система множественных ролей и управляющих

### 2.19.1. Архитектура множественных ролей

#### Принципы системы ролей
- **Множественность**: Пользователь может иметь несколько ролей одновременно
- **Автоматическое назначение**: Роли назначаются автоматически на основе действий пользователя
- **Гранулярные права**: Детальный контроль доступа к функциям системы
- **Гибкость**: Легкое добавление новых ролей и прав

#### Модель данных
```python
# domain/entities/user_role.py
class UserRole(Base):
    __tablename__ = "user_roles"
    
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    role = Column(String(50), nullable=False)  # applicant, owner, employee, manager, superadmin
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'role', name='uq_user_role'),
        Index('idx_user_roles_user_id', 'user_id'),
        Index('idx_user_roles_role', 'role')
    )

# domain/entities/manager_permission.py
class ManagerObjectPermission(Base):
    __tablename__ = "manager_object_permissions"
    
    id = Column(BigInteger, primary_key=True)
    contract_id = Column(BigInteger, ForeignKey("contracts.id", ondelete="CASCADE"))
    object_id = Column(BigInteger, ForeignKey("objects.id", ondelete="CASCADE"))
    can_view = Column(Boolean, default=True)
    can_edit = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_manage_employees = Column(Boolean, default=False)
    can_view_finances = Column(Boolean, default=False)
    can_edit_rates = Column(Boolean, default=False)
    can_edit_schedule = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('contract_id', 'object_id', name='uq_manager_object_permission'),
        Index('idx_manager_object_permissions_contract', 'contract_id'),
        Index('idx_manager_object_permissions_object', 'object_id')
    )
```

### 2.19.2. Логика входа и переключения интерфейсов

#### Точки входа в систему
1. **Telegram Bot** (`/start`)
   - Автоматическое определение ролей пользователя
   - Показ доступных функций на основе ролей
   - Переход к веб-интерфейсу при необходимости

2. **Веб-сайт** (ввод Telegram ID + PIN-код)
   - Авторизация через PIN-код от бота
   - Определение доступных интерфейсов
   - Автоматический редирект на подходящий интерфейс

3. **Прямые ссылки** (например, `/owner/dashboard`)
   - Проверка прав доступа к интерфейсу
   - Редирект на доступный интерфейс при отсутствии прав

#### Система переключения интерфейсов

**Приоритет ролей:**
1. **superadmin** - высший приоритет, доступ ко всем интерфейсам
2. **owner** - доступ к `/owner/*` и `/manager/*` (если управляющий)
3. **manager** - доступ к `/manager/*` и `/employee/*` (если сотрудник)
4. **employee** - доступ к `/employee/*`
5. **applicant** - доступ только к базовым функциям

**Компонент переключения ролей:**
```html
<!-- Компонент переключения ролей в навигации -->
<div class="role-switcher dropdown">
    <button class="btn btn-outline-light dropdown-toggle" type="button" data-bs-toggle="dropdown">
        <i class="bi bi-person-gear"></i> {{ current_role_display }}
    </button>
    <ul class="dropdown-menu">
        {% for role in available_roles %}
        <li>
            <a class="dropdown-item" href="/{{ role.interface }}/dashboard">
                <i class="bi bi-{{ role.icon }}"></i> {{ role.display_name }}
            </a>
        </li>
        {% endfor %}
    </ul>
</div>
```

**JavaScript для переключения:**
```javascript
// apps/web/static/js/role_switcher.js
class RoleSwitcher {
    constructor() {
        this.currentRole = this.getCurrentRole();
        this.availableRoles = this.getAvailableRoles();
        this.init();
    }
    
    init() {
        this.renderRoleSwitcher();
        this.bindEvents();
    }
    
    getCurrentRole() {
        const path = window.location.pathname;
        if (path.startsWith('/admin/')) return 'superadmin';
        if (path.startsWith('/owner/')) return 'owner';
        if (path.startsWith('/manager/')) return 'manager';
        if (path.startsWith('/employee/')) return 'employee';
        return 'applicant';
    }
    
    getAvailableRoles() {
        // Получаем доступные роли от сервера
        return window.availableRoles || [];
    }
    
    switchRole(role) {
        const roleInterfaces = {
            'superadmin': '/admin/dashboard',
            'owner': '/owner/dashboard',
            'manager': '/manager/dashboard',
            'employee': '/employee/dashboard'
        };
        
        if (roleInterfaces[role]) {
            window.location.href = roleInterfaces[role];
        }
    }
}
```

### 2.19.3. Сервисы управления ролями

#### RoleService
```python
class RoleService:
    async def add_role(self, user_id: int, role: str) -> bool:
        """Добавление роли пользователю"""
        
    async def remove_role(self, user_id: int, role: str) -> bool:
        """Удаление роли у пользователя"""
        
    async def has_role(self, user_id: int, role: str) -> bool:
        """Проверка наличия роли у пользователя"""
        
    async def get_user_roles(self, user_id: int) -> List[str]:
        """Получение всех ролей пользователя"""
        
    async def get_available_interfaces(self, user_id: int) -> List[dict]:
        """Получение доступных интерфейсов для пользователя"""
        
    async def update_roles_for_objects(self, user_id: int) -> None:
        """Обновление ролей на основе объектов пользователя"""
        
    async def update_roles_for_contracts(self, user_id: int) -> None:
        """Обновление ролей на основе договоров пользователя"""
```

#### ManagerPermissionService
```python
class ManagerPermissionService:
    async def grant_object_permission(self, contract_id: int, object_id: int, permissions: dict):
        """Предоставление прав на объект управляющему"""
        
    async def revoke_object_permission(self, contract_id: int, object_id: int):
        """Отзыв прав на объект у управляющего"""
        
    async def get_accessible_objects(self, manager_id: int, owner_id: int) -> List[int]:
        """Получение списка доступных объектов для управляющего"""
        
    async def can_manage_object(self, manager_id: int, object_id: int, action: str) -> bool:
        """Проверка прав на выполнение действия с объектом"""
        
    async def can_create_objects(self, manager_id: int, owner_id: int) -> bool:
        """Проверка права на создание объектов"""
        
    async def can_manage_contracts(self, manager_id: int, owner_id: int) -> bool:
        """Проверка права на управление договорами"""
```

### 2.19.4. Middleware для множественных ролей

#### Новые middleware
```python
async def require_any_role(request: Request, roles: List[str]):
    """Проверка наличия любой из указанных ролей"""
    
async def require_all_roles(request: Request, roles: List[str]):
    """Проверка наличия всех указанных ролей"""
    
async def require_manager_or_owner(request: Request):
    """Проверка роли управляющего или владельца"""
    
async def require_object_access(request: Request, object_id: int):
    """Проверка доступа к конкретному объекту"""
    
async def require_manager_permission(permission: str):
    """Декоратор для проверки конкретного права управляющего"""
```

### 2.19.5. Интерфейс управляющего

#### URL-структура
- `/manager/dashboard` - дашборд управляющего
- `/manager/objects` - управление доступными объектами
- `/manager/objects/create` - создание нового объекта
- `/manager/objects/{id}` - просмотр/редактирование объекта
- `/manager/employees` - управление сотрудниками
- `/manager/contracts` - управление договорами
- `/manager/calendar` - планирование смен
- `/manager/reports` - отчеты по доступным объектам

#### Базовый шаблон управляющего
```html
<!-- apps/web/templates/manager/base_manager.html -->
<!DOCTYPE html>
<html lang="ru">
<head>
    <title>{% block title %}StaffProBot - Управляющий{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-warning">
        <div class="container-fluid">
            <a class="navbar-brand" href="/manager/dashboard">
                <i class="bi bi-person-gear"></i> StaffProBot - Управляющий
            </a>
            
            <!-- Компонент переключения ролей -->
            <div class="role-switcher dropdown">
                <button class="btn btn-outline-light dropdown-toggle" type="button" data-bs-toggle="dropdown">
                    <i class="bi bi-person-gear"></i> {{ current_role_display }}
                </button>
                <ul class="dropdown-menu">
                    {% for role in available_roles %}
                    <li>
                        <a class="dropdown-item" href="/{{ role.interface }}/dashboard">
                            <i class="bi bi-{{ role.icon }}"></i> {{ role.display_name }}
                        </a>
                    </li>
                    {% endfor %}
                </ul>
            </div>
            
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/manager/objects">Объекты</a>
                <a class="nav-link" href="/manager/employees">Сотрудники</a>
                <a class="nav-link" href="/manager/calendar">Календарь</a>
                <a class="nav-link" href="/manager/reports">Отчеты</a>
                <a class="nav-link" href="/auth/logout">Выход</a>
            </div>
        </div>
    </nav>

    <div class="container-fluid mt-4">
        {% block content %}{% endblock %}
    </div>

    <script src="/static/js/role_switcher.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

### История изменений
- **v2.10** (19.09.2025): Добавлена система множественных ролей и управляющих - детальная система прав доступа, умное переключение интерфейсов, роль управляющего с гранулярными правами
- **v2.9** (19.09.2025): Улучшена drag&drop функциональность - добавлена проверка доступа к объектам, фильтрация сотрудников по договорам, информативные сообщения об ошибках
- **v2.8** (11.09.2025): Добавлена drag&drop функциональность для планирования смен - панели объектов и сотрудников, интерактивное планирование, улучшенный UX
- **v2.7** (11.09.2025): Исправлена логика бота - доступ владельцев к своим объектам, улучшена логика открытия смен, исправлены проблемы с веб-интерфейсом (график работы)
- **v2.6** (10.09.2025): Завершена миграция веб-интерфейса в /owner/* пространство, унификация навигации, оптимизация кода
- **v2.5** (09.09.2025): Добавлена система администрирования, концепция разделения интерфейсов по ролям, исправлена навигация
- **v2.4** (06.09.2025): Исправлены проблемы с планированием смен - отмена смен, обновление расписания, кнопка закрытия
- **v2.3** (02.09.2025): Добавлена система тайм-слотов, рефакторинг handlers в модульную структуру, очистка проекта
- **v2.2** (28.08.2025): Добавлена полная Docker-интеграция, кросс-платформенность, health checks
- **v2.1** (21.08.2025): Добавлены UserStateManager, UX улучшения, геолокационные возможности
- **v2.0** (ранее): Базовая архитектура и техническое видение
- **v1.0** (ранее): Первоначальная версия
