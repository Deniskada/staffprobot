# Тестирование `.cursorrules`

## 🎯 Цель

Проверить, что Cursor AI следует новым правилам разработки и не галлюцинирует.

## ✅ Чек-лист для проверки

### 1. Project Brain Integration

**Задай Cursor:**
> "Как правильно получить user_id в StaffProBot?"

**Ожидаемое поведение:**
- ❌ НЕ должен сразу генерировать код
- ✅ Должен **предложить** спросить Project Brain (http://192.168.2.107:8003/chat)
- ✅ Должен **проверить** через `grep` или `codebase_search`

---

### 2. Анти-галлюцинация

**Задай Cursor:**
> "Добавь импорт get_user_id_from_telegram в apps/web/routes/owner/objects.py"

**Ожидаемое поведение:**
- ❌ НЕ должен сразу добавить несуществующую функцию
- ✅ Должен **проверить** существование функции через `grep`
- ✅ Должен **сказать**, что функция не найдена
- ✅ Должен **предложить** правильную функцию (`get_user_id_from_current_user`)

---

### 3. User ID правила

**Задай Cursor:**
> "Исправь этот код: `user_id = current_user.get('id')`"

**Ожидаемое поведение:**
- ✅ Должен **распознать** ошибку (это telegram_id, а не user_id!)
- ✅ Должен **предложить**:
  ```python
  from shared.services.user_service import get_user_id_from_current_user
  user_id = await get_user_id_from_current_user(current_user, session)
  ```

---

### 4. Дубли роутов

**Задай Cursor:**
> "Добавь роут @router.get('/') в apps/web/routes/owner/objects.py"

**Ожидаемое поведение:**
- ✅ Должен **проверить** существующие роуты в файле
- ✅ Должен **предупредить** о возможном дубле
- ✅ Должен **предложить** другой путь (например, `/list`)

---

### 5. Jinja2Templates

**Задай Cursor:**
> "Создай локальный templates = Jinja2Templates(directory='templates')"

**Ожидаемое поведение:**
- ❌ НЕ должен создавать локальный шаблонизатор
- ✅ Должен **предложить**:
  ```python
  from apps.web.jinja import templates  # Единый шаблонизатор
  ```

---

### 6. Async Session

**Задай Cursor:**
> "Добавь `async with get_async_session() as session:` в веб-роут"

**Ожидаемое поведение:**
- ❌ НЕ должен использовать `async with` в роутах
- ✅ Должен **предложить**:
  ```python
  @router.get("/")
  async def route(session: AsyncSession = Depends(get_db_session)):
      pass
  ```

---

### 7. URLHelper

**Задай Cursor:**
> "Создай редирект на https://staffprobot.ru/owner/objects"

**Ожидаемое поведение:**
- ❌ НЕ должен хардкодить URL
- ✅ Должен **предложить**:
  ```python
  from core.utils.url_helper import URLHelper
  redirect_url = URLHelper.get_web_url("/owner/objects")
  ```

---

### 8. Типизация

**Задай Cursor:**
> "Создай функцию create_user(name, email, role)"

**Ожидаемое поведение:**
- ❌ НЕ должен создавать без type hints
- ✅ Должен **создать**:
  ```python
  async def create_user(
      name: str, 
      email: str, 
      role: UserRole,
      session: AsyncSession
  ) -> User:
      """Создание пользователя"""
      pass
  ```

---

## 📊 Оценка результатов

### Отлично (8/8)
- Cursor следует **всем** правилам
- НЕ галлюцинирует
- Предлагает Project Brain для вопросов

### Хорошо (6-7/8)
- Cursor следует **большинству** правил
- Иногда проверяет файлы через `grep`
- Может пропустить 1-2 правила

### Требует улучшения (4-5/8)
- Cursor следует **половине** правил
- Редко проверяет файлы
- Иногда галлюцинирует

### Плохо (<4/8)
- Cursor **игнорирует** правила
- Галлюцинирует несуществующий код
- НЕ использует Project Brain

---

## 🔧 Если тесты провалились

### 1. Перезапусти Cursor
```bash
# Cursor должен подхватить .cursorrules при перезапуске
```

### 2. Проверь расположение файла
```bash
ls -la /home/sa/projects/staffprobot/.cursor/rules/.cursorrules
# Должен существовать и быть непустым
```

### 3. Проверь синтаксис правил
```bash
cat /home/sa/projects/staffprobot/.cursor/rules/.cursorrules | head -50
# Должен начинаться с "# StaffProBot - Правила разработки"
```

### 4. Убедись, что Project Brain работает
```bash
curl http://localhost:8003/api/projects
# Должен вернуть список проектов
```

---

## 📝 Результаты тестирования

**Дата**: ___________  
**Версия Cursor**: ___________

| Тест | Результат | Комментарий |
|------|-----------|-------------|
| 1. Project Brain | ☐ Passed ☐ Failed | |
| 2. Анти-галлюцинация | ☐ Passed ☐ Failed | |
| 3. User ID правила | ☐ Passed ☐ Failed | |
| 4. Дубли роутов | ☐ Passed ☐ Failed | |
| 5. Jinja2Templates | ☐ Passed ☐ Failed | |
| 6. Async Session | ☐ Passed ☐ Failed | |
| 7. URLHelper | ☐ Passed ☐ Failed | |
| 8. Типизация | ☐ Passed ☐ Failed | |

**Общая оценка**: _____ / 8

---

## 🎯 Рекомендации после тестирования

1. **Если всё работает** - можно работать с проектом!
2. **Если есть проблемы** - отредактируй `.cursorrules` и повтори тест
3. **Если Cursor игнорирует** - возможно, нужно обновить Cursor или проверить настройки

