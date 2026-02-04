# Исправление установки spec-kit

## Проблема

При попытке установить spec-kit через `pip3 install spec-kit` возникла ошибка:

```
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try apt install
    python3-xyz, where xyz is the package you are trying to
    install.
```

## Причина

Ubuntu 23.04+ (и другие современные дистрибутивы) используют **PEP 668** для защиты системного Python от конфликтов пакетов. Это означает, что нельзя устанавливать пакеты напрямую через `pip3 install` в системный Python.

## Решения

### Вариант 1: Использовать pipx (Рекомендуется)

**pipx** - инструмент для установки Python CLI приложений в изолированных окружениях.

```bash
# 1. Установить pipx
sudo apt install pipx

# 2. Убедиться, что pipx в PATH
pipx ensurepath

# 3. Установить spec-kit через pipx
pipx install spec-kit

# 4. Проверить установку
spec-kit --version
```

**Преимущества**:
- Изолированное окружение для каждого CLI инструмента
- Не конфликтует с системным Python
- Автоматическое управление зависимостями

### Вариант 2: Использовать uv (Альтернатива)

**uv** - быстрый инструмент на Rust, заменяющий pipx, pip, poetry и другие.

```bash
# 1. Установить uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Добавить в PATH (если нужно)
export PATH="$HOME/.cargo/bin:$PATH"

# 3. Установить spec-kit через uv
uv tool install spec-kit

# 4. Проверить установку
spec-kit --version
```

**Преимущества**:
- Очень быстрый (10-100x быстрее pip)
- Единый инструмент для многих задач
- Современный подход

### Вариант 3: Виртуальное окружение проекта

Если spec-kit нужен только для этого проекта:

```bash
# 1. Создать виртуальное окружение
cd /home/sa/projects/staffprobot
python3 -m venv .venv

# 2. Активировать окружение
source .venv/bin/activate

# 3. Установить spec-kit
pip install spec-kit

# 4. Использовать через активированное окружение
spec-kit --version
```

**Недостатки**:
- Нужно активировать окружение перед использованием
- Не доступен глобально

### Вариант 4: Использовать без установки (для тестирования)

Если нужно просто попробовать spec-kit:

```bash
# Использовать uvx для запуска без установки
uvx --from git+https://github.com/github/spec-kit.git specify init my-project
```

## Рекомендация

**Использовать pipx** - это стандартный способ установки Python CLI инструментов в современных системах.

## Команды для быстрой установки

```bash
# Установить pipx
sudo apt install pipx

# Добавить в PATH (если нужно)
pipx ensurepath

# Перезагрузить shell или выполнить
source ~/.bashrc

# Установить spec-kit
pipx install spec-kit

# Проверить
spec-kit --version
```

## После установки

1. Создать конфигурационный файл `.spec-kit/config.yaml`:
```yaml
specs_dir: specs/capabilities
changes_dir: changes
ai_provider: claude
```

2. Инициализировать проект:
```bash
spec-kit init
```

3. Использовать команды:
- `/specify` - создать/обновить спецификацию
- `/plan` - создать технический план
- `/tasks` - разбить на задачи
- `/implement` - реализовать через Supercode

---

**Дата**: 2026-02-04  
**Статус**: Решение готово к применению
