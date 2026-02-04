# Пошаговая установка фреймворков для StaffProBot

## Этап 1: cursor-memory-bank

### Шаг 1.1: Установка
```bash
# Memory Bank v0.8 использует Cursor 2.0 команды, не npm пакет
# Установка через клонирование репозитория:

cd /home/sa/projects/staffprobot
git clone https://github.com/vanzan01/cursor-memory-bank.git /tmp/cursor-memory-bank
cp -r /tmp/cursor-memory-bank/.cursor/commands .cursor/
cp -r /tmp/cursor-memory-bank/.cursor/rules .cursor/memory-bank-rules
mkdir -p memory-bank

# Команды готовы к использованию! Наберите "/" в Cursor для просмотра команд
```

### Шаг 1.2: Настройка структуры
Структура уже создана в `.cursor/memory-bank/`:
- `PROJECT_BRIEF.md` - краткое описание проекта
- `ACTIVE_FOCUS.md` - текущий фокус работы
- `ARCHITECTURE.md` - системная архитектура (создать)
- `PATTERNS.md` - паттерны и практики (создать)
- `TECHNICAL_CONTEXT.md` - технический контекст (создать)
- `PROGRESS.md` - отслеживание прогресса (создать)

### Шаг 1.3: Настройка режимов
Создать режимы в Cursor через Memory Bank:
- **VAN** (Verify, Analyze, Navigate) - анализ и навигация
- **PLAN** - планирование задач из roadmap.md
- **CREATIVE** - генерация идей
- **IMPLEMENT** - реализация через Supercode

### Шаг 1.4: Команды
Настроить команды:
- `PLAN` - создать план задачи из roadmap.md
- `ACT` - реализовать задачу через Supercode workflow
- `UPDATE` - обновить память после изменений

## Этап 2: OpenSpec

### Шаг 2.1: Создание структуры
```bash
cd /home/sa/projects/staffprobot
mkdir -p specs/capabilities changes/active changes/archive
```

### Шаг 2.2: Миграция существующих спецификаций
```bash
# Копировать ключевые спецификации из doc/vision_v1/ в specs/capabilities/
cp doc/vision_v1/contract_constructor.md specs/capabilities/contract-constructor.md
# И т.д. для других ключевых возможностей
```

### Шаг 2.3: Настройка workflow
1. Описать изменение → генерируется proposal в `changes/active/`
2. Review → уточнение спецификации
3. Implement → реализация через Supercode
4. Complete → перенос в `specs/` и архив `changes/`

### Шаг 2.4: Интеграция с roadmap.md
- Каждая задача из roadmap.md может иметь связанную спецификацию
- Изменения спецификаций отслеживаются через deltas

## Этап 3: spec-kit

### Шаг 3.1: Установка
```bash
# Установить Specify CLI
npm install -g @github/spec-kit

# Или через pip (если доступно)
pip install spec-kit
```

### Шаг 3.2: Настройка
Создать конфигурационный файл `.spec-kit/config.yaml`:
```yaml
specs_dir: specs/capabilities
changes_dir: changes
ai_provider: claude  # или другой провайдер
```

### Шаг 3.3: Команды
Настроить команды в Cursor или через CLI:
- `/specify` - создать/обновить спецификацию
- `/clarify` - разрешить неопределённости
- `/plan` - создать технический план
- `/tasks` - разбить на задачи
- `/analyze` - проверить согласованность
- `/implement` - реализовать через Supercode

### Шаг 3.4: Интеграция с OpenSpec
- spec-kit использует структуру `specs/` от OpenSpec
- Команды работают с файлами OpenSpec
- `/analyze` проверяет соответствие кода спецификациям

## Этап 4: Claude Task Master

### Шаг 4.1: Установка через MCP
```bash
# Установка через MCP Bar
npx mcpbar@latest install eyaltoledano/claude-task-master -c claude

# Или через cursor:// deep link
# Открыть ссылку из документации TaskMaster
```

### Шаг 4.2: Настройка API ключей
Настроить переменные окружения для API ключей:
- Anthropic (Claude)
- OpenAI (опционально)
- Другие провайдеры (опционально)

### Шаг 4.3: Конфигурация MCP
Добавить в конфигурацию Cursor MCP серверов:
```json
{
  "mcpServers": {
    "claude-task-master": {
      "command": "npx",
      "args": ["-y", "@eyaltoledano/claude-task-master"],
      "env": {
        "ANTHROPIC_API_KEY": "your-key-here"
      }
    }
  }
}
```

### Шаг 4.4: Интеграция с roadmap.md
- Задачи из roadmap.md синхронизируются с TaskMaster
- TaskMaster отслеживает прогресс выполнения
- Обновления в TaskMaster отражаются в roadmap.md

### Шаг 4.5: Интеграция с Supercode
- Workflow "Новая задача из roadmap" создаёт задачи в TaskMaster
- TaskMaster предоставляет контекст для Supercode workflows

## Проверка установки

### Проверка Memory Bank
```bash
# Проверить структуру
ls -la .cursor/memory-bank/
# Должны быть файлы: PROJECT_BRIEF.md, ACTIVE_FOCUS.md, и т.д.
```

### Проверка OpenSpec
```bash
# Проверить структуру
ls -la specs/ changes/
# Должны быть директории: capabilities/, active/, archive/
```

### Проверка spec-kit
```bash
# Проверить установку
spec-kit --version
# Или
which spec-kit
```

### Проверка TaskMaster
```bash
# Проверить MCP серверы в Cursor
# Открыть Cursor Settings → MCP Servers
# Должен быть claude-task-master
```

## Следующие шаги после установки

1. Заполнить Memory Bank файлы:
   - `ARCHITECTURE.md` - системная архитектура
   - `PATTERNS.md` - паттерны из `.cursor/rules/`
   - `TECHNICAL_CONTEXT.md` - технический контекст
   - `PROGRESS.md` - текущий прогресс

2. Мигрировать спецификации в OpenSpec:
   - Ключевые возможности из `doc/vision_v1/`
   - Текущие задачи из roadmap.md

3. Настроить автоматическую синхронизацию:
   - Memory Bank ↔ roadmap.md
   - TaskMaster ↔ roadmap.md
   - OpenSpec ↔ Supercode workflows

4. Создать примеры использования:
   - Пример workflow с Memory Bank
   - Пример spec-driven разработки
   - Пример использования TaskMaster

---

**Дата создания**: 2026-02-04  
**Статус**: Готов к выполнению
