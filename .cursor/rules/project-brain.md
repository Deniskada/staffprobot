# Project Brain - Правила использования в Cursor

## 🎯 Цель
Project Brain - локальная RAG система с 26,290 QA парами для помощи в разработке StaffProBot.

## 📊 Текущие метрики качества
- ✅ **Line Numbers**: 100% (файл + строки ВСЕГДА указываются)
- ✅ **File Path**: 100% (путь к файлу ВСЕГДА указывается)
- ✅ **Code Snippet**: 100% (код ВСЕГДА включается)
- ⚠️ **Keywords**: 25.5% (релевантность ключевых слов)
- ⭐ **TOTAL SCORE**: 85.1%

**Распределение ответов**: 50% Отлично (>85%) + 50% Хорошо (70-85%) = 100% приемлемо!

## 🚀 Как использовать

### 1. HTTP API запросы (рекомендуется)
```bash
curl -s http://192.168.2.107:8003/api/query \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "Где находится функция start_shift?",
    "project": "staffprobot"
  }'
```

**Ответ всегда содержит**:
```
📁 Файл: `apps/web/routes/employee.py`
📍 Строки: 145-167

💻 КОД:
```python
@router.post('/shift/start')
async def start_shift(...):
    ...
```

📝 Объяснение: [краткое описание]
```

### 2. Веб-интерфейс
Откройте: http://192.168.2.107:8003/chat
- Выберите проект: **StaffProBot**
- Задайте вопрос
- Получите ответ с кодом и строками

### 3. Интеграция в Cursor

#### Вариант A: Через terminal command
В Cursor можно добавить команду:
```bash
# .cursor/commands/ask-brain.sh
#!/bin/bash
QUERY="$1"
curl -s http://192.168.2.107:8003/api/query \
  -H 'Content-Type: application/json' \
  -d "{\"query\":\"$QUERY\",\"project\":\"staffprobot\"}" \
  | jq -r '.answer'
```

Использование:
```bash
bash .cursor/commands/ask-brain.sh "Как открыть смену?"
```

#### Вариант B: Через Python скрипт
```python
# .cursor/scripts/ask_brain.py
import requests
import sys

def ask_brain(query: str) -> str:
    response = requests.post(
        "http://192.168.2.107:8003/api/query",
        json={"query": query, "project": "staffprobot"}
    )
    return response.json()["answer"]

if __name__ == "__main__":
    query = " ".join(sys.argv[1:])
    print(ask_brain(query))
```

## 💡 Лучшие практики запросов

### ✅ Хорошие вопросы (дают точные ответы)
1. **Конкретные функции/классы**:
   - "Где находится функция start_shift?"
   - "Что делает класс User?"
   - "Код функции close_shift"

2. **API endpoints**:
   - "Какой endpoint для открытия смены?"
   - "API для создания объекта"
   - "Роуты для owner"

3. **Модели БД**:
   - "Поля модели Shift"
   - "Модель User"
   - "Структура таблицы objects"

4. **Реализация логики**:
   - "Как работает геолокация?"
   - "Логика расчета зарплаты"
   - "Проверка активного договора"

### ❌ Менее эффективные вопросы
1. Слишком общие: "Как работает система?"
2. Без контекста: "Что делает эта функция?" (не указана какая)
3. Множественные вопросы: "Где User и как работает аутентификация?"

### 🎯 Оптимальный формат вопроса
```
[Действие] [Конкретная сущность] [Дополнительный контекст]?

Примеры:
- Где [находится] [функция create_contract] ?
- Как [работает] [открытие смены] [для сотрудника]?
- Какие [поля] [в модели Shift] ?
- Код [endpoint] [/owner/objects] ?
```

## 📚 База знаний

### Содержимое (26,290 QA пар)
1. **Функции** (19,700 пар):
   - Где находится?
   - Что делает?
   - Как использовать?
   - Параметры
   - Код

2. **Классы** (1,536 пар):
   - Определение
   - Методы
   - Поля
   - Использование

3. **API Endpoints** (3,024 пар):
   - Метод (GET/POST/etc)
   - Путь
   - Обработчик
   - Код

4. **Остальное** (2,030 пар):
   - Импорты
   - Зависимости
   - Файлы
   - Конфигурация

### Обновление базы знаний

#### Автоматическое (через webhook)
При `git push` в репозиторий StaffProBot:
1. GitHub webhook → Project Brain API
2. Автоматический `git pull`
3. Переиндексация измененных файлов
4. База обновляется без участия

#### Ручное
```bash
# Переиндексация конкретного проекта
curl -X POST http://192.168.2.107:8003/api/webhook/manual-reindex/staffprobot

# Проверка статуса
curl http://192.168.2.107:8003/api/webhook/status/staffprobot
```

## 🔧 Настройка и обслуживание

### Мониторинг
```bash
# Статус контейнеров
docker compose -f docker-compose.local.yml ps

# Логи API
docker compose -f docker-compose.local.yml logs api -f

# Статус ChromaDB
curl http://192.168.2.107:8000/api/v1/heartbeat
```

### Перезапуск при проблемах
```bash
cd /home/sa/projects/project-brain
docker compose -f docker-compose.local.yml restart api
```

### Очистка и переиндексация
```bash
# Удалить старую коллекцию и создать новую
docker compose -f docker-compose.local.yml exec api python -c "
from backend.storage.chroma_client import get_chroma_client
client = get_chroma_client()
client.delete_collection('staffprobot_main')
"

# Запустить полную переиндексацию
docker compose -f docker-compose.local.yml exec api \
  python /app/scripts/load_all_qa_pairs.py
```

## 📖 Примеры использования в Cursor

### Сценарий 1: Найти код функции
**Задача**: Нужно изменить логику открытия смены

```bash
$ ask-brain "Где код функции start_shift?"

📁 Файл: `apps/bot/handlers/shift_handlers.py`
📍 Строки: 234-289

💻 КОД:
```python
async def start_shift(message: Message, state: FSMContext):
    # Код функции...
```
```

**Результат**: Вы сразу знаете файл и строки, можете открыть нужный файл в Cursor.

### Сценарий 2: Понять структуру модели
**Задача**: Нужно добавить поле в модель Contract

```bash
$ ask-brain "Поля модели Contract"

📁 Файл: `domain/entities/contract.py`
📍 Строки: 15-67

💻 КОД:
```python
class Contract(Base):
    __tablename__ = 'contracts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    # ... остальные поля
```
```

**Результат**: Видите все поля, понимаете структуру, добавляете новое поле корректно.

### Сценарий 3: Найти API endpoint
**Задача**: Нужно отправить запрос на создание объекта

```bash
$ ask-brain "API endpoint для создания объекта"

📁 Файл: `apps/web/routes/owner/objects.py`
📍 Строка: 145

💻 ENDPOINT: POST `/owner/objects`

💻 КОД:
```python
@router.post('/')
async def create_object(
    data: ObjectCreate,
    session: AsyncSession = Depends(get_db_session)
):
    ...
```
```

**Результат**: Знаете endpoint, метод, параметры.

## 🎓 Расширенное использование

### Цепочка вопросов
Для сложных задач задавайте вопросы последовательно:

1. "Где логика расчета зарплаты?"
2. "Функция calculate_salary код"
3. "Где вызывается calculate_salary?"
4. "Модель Payroll поля"

### Поиск похожих реализаций
```bash
# Найти все endpoints для owner
ask-brain "Какие API endpoints для owner?"

# Найти все функции работы со сменами
ask-brain "Функции для работы со сменами"

# Найти использование конкретного модуля
ask-brain "Где используется shift_service?"
```

## 🔍 Отладка

### Проблема: Нет результатов
**Причины**:
1. Вопрос слишком общий
2. Сущность не проиндексирована
3. API недоступен

**Решение**:
1. Уточните вопрос (добавьте имя функции/класса)
2. Проверьте статус API: `curl http://192.168.2.107:8003/health`
3. Проверьте логи: `docker logs project-brain-api`

### Проблема: Неточный ответ
**Причины**:
1. Модель нашла похожий, но не тот код
2. Вопрос неоднозначный

**Решение**:
1. Добавьте больше контекста в вопрос
2. Укажите файл/модуль: "функция X в routes/owner"
3. Используйте точные имена функций/классов

## 📊 Статистика и метрики

### Текущее состояние
- **База знаний**: 26,290 QA пар
- **Проиндексировано**: 
  - 1,970 функций
  - 192 класса
  - 252 API endpoints
  - 269 файлов
- **Качество ответов**: 85.1% (50% отлично, 50% хорошо)
- **Скорость ответа**: ~5-30 секунд (зависит от сложности)

### История улучшений
- **Начало**: 474 QA пар, качество ~57%
- **После фазы 3**: 8,707 QA пар, качество ~48%
- **После фазы 4**: 26,290 QA пар, качество **85.1%**

## 🚀 Roadmap (будущие улучшения)

### Запланировано
1. ⏳ Улучшение keyword matching (цель: >90%)
2. ⏳ Специализированные коллекции (architecture, api, models, debug)
3. ⏳ Интеграция с VSCode/Cursor plugin
4. ⏳ Кэширование частых запросов
5. ⏳ Multilingual support (English queries)

### В разработке
- Автоматическое обновление при изменениях в коде
- Улучшенный reranking результатов
- Контекстные подсказки в редакторе

---

**Версия**: 1.0.0  
**Дата**: 18.10.2025  
**Автор**: Project Brain Team  
**Статус**: ✅ Production Ready
