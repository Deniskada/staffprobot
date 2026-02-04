# Отчёт об установке фреймворков

**Дата**: 2026-02-04  
**Статус**: Частично завершено

## Анализ ошибки установки

### Проблема
Команда `npx cursor-bankinit` выдала ошибку:
```
npm ERR! 404 Not Found - GET https://registry.npmjs.org/cursor-bankinit - Not found
```

### Причина
**cursor-memory-bank** не является npm пакетом. Это GitHub репозиторий, который использует:
- **Cursor 2.0 команды** (не npm пакет)
- **Файлы в `.cursor/commands/`** для интеграции с Cursor
- **Структуру `memory-bank/`** для хранения контекста

Версия v0.8 перешла от custom modes к командам Cursor 2.0, поэтому установка через npm невозможна.

### Решение
Установка выполнена через клонирование репозитория и копирование файлов:
```bash
git clone https://github.com/vanzan01/cursor-memory-bank.git /tmp/cursor-memory-bank
cp -r /tmp/cursor-memory-bank/.cursor/commands .cursor/
cp -r /tmp/cursor-memory-bank/.cursor/rules .cursor/memory-bank-rules
```

## Статус установки по инструментам

### ✅ 1. cursor-memory-bank
**Статус**: Установлено и готово к использованию

**Установлено**:
- ✅ Команды в `.cursor/commands/`: `/van`, `/plan`, `/creative`, `/build`, `/reflect`, `/archive`
- ✅ Правила в `.cursor/memory-bank-rules/`
- ✅ Структура `memory-bank/` для хранения контекста
- ✅ Файлы Memory Bank (PROJECT_BRIEF.md, ACTIVE_FOCUS.md, и т.д.)

**Использование**:
- В Cursor набрать `/` для просмотра команд
- Начать с `/van` для инициализации проекта
- Команды работают без дополнительной настройки

### ✅ 2. OpenSpec структура
**Статус**: Структура создана

**Создано**:
- ✅ `specs/capabilities/` - для авторитетных спецификаций
- ✅ `changes/active/` - для активных предложений изменений
- ✅ `changes/archive/` - для архивированных изменений

**Следующие шаги**:
- Мигрировать спецификации из `doc/vision_v1/` в `specs/capabilities/`
- Использовать для spec-driven разработки

### ✅ 3. spec-kit
**Статус**: Установлено

**Установлено через pipx**:
```bash
# Установить pipx
sudo apt install pipx
pipx ensurepath

# Установить spec-kit из GitHub
pipx install git+https://github.com/github/spec-kit.git
```

**Команда**: `specify` (версия 0.0.22)

**Использование**:
- `specify --version` - проверить версию
- `specify init` - инициализировать проект

**После установки**:
- Создать `.spec-kit/config.yaml`
- Настроить команды `/specify`, `/plan`, `/tasks`, `/implement`

### ⚠️ 4. Claude Task Master
**Статус**: Требует установки через MCP

**Инструмент**: mcpbar доступен (версия 1.1.0)

**Установка**:
```bash
npx mcpbar@latest install eyaltoledano/claude-task-master -c claude
```

**Требования**:
- API ключ Anthropic (Claude)
- Настройка MCP серверов в Cursor Settings

**После установки**:
- Настроить API ключи
- Добавить MCP сервер в конфигурацию Cursor
- Настроить синхронизацию с roadmap.md

## Итоговый статус

### Готово к использованию (2/4)
1. ✅ **cursor-memory-bank** - команды доступны в Cursor
2. ✅ **OpenSpec структура** - готова к использованию

### Требует действий (2/4)
1. ⚠️ **spec-kit** - установить pip3, затем spec-kit
2. ⚠️ **TaskMaster** - установить через MCP, настроить API ключи

## Рекомендации

### Немедленно
1. **Использовать Memory Bank**: Команды `/van`, `/plan`, `/build` уже доступны
2. **Начать работу с OpenSpec**: Структура готова, можно мигрировать спецификации

### Сегодня
1. **Установить pip3 и spec-kit**:
   ```bash
   sudo apt install python3-pip
   pip3 install spec-kit
   ```

2. **Установить TaskMaster** (если есть API ключ Claude):
   ```bash
   npx mcpbar@latest install eyaltoledano/claude-task-master -c claude
   ```

### На этой неделе
1. Мигрировать ключевые спецификации в OpenSpec
2. Настроить интеграцию между всеми инструментами
3. Создать примеры использования

## Полезные ссылки

- **Memory Bank**: https://github.com/vanzan01/cursor-memory-bank
- **spec-kit**: https://github.com/github/spec-kit
- **TaskMaster**: https://github.com/eyaltoledano/claude-task-master
- **OpenSpec**: https://www.openspec.cn/

---

**Вывод**: Memory Bank и OpenSpec структура готовы к использованию. spec-kit и TaskMaster требуют дополнительной установки.
