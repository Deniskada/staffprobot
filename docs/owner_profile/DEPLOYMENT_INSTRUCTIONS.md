# 🚀 Инструкции по деплою: Расширение профиля владельца

## ⚠️ КРИТИЧНЫЕ ПРЕДУПРЕЖДЕНИЯ

### 1. Таблица `shift_cancellations`

**ВАЖНО**: Миграция `a266c36de460` была исправлена, чтобы **НЕ УДАЛЯТЬ** таблицу `shift_cancellations` на проде!

#### Что было изменено:

- ✅ **Строки 65-74**: Закомментированы `op.drop_table('shift_cancellations')` и удаление индексов
- ✅ **Строки 714-755**: Закомментированы `op.create_table('shift_cancellations')` и создание индексов

#### Почему это важно:

Alembic автоматически сгенерировал миграцию, которая:
1. Удаляла бы старую таблицу `shift_cancellations` **СО ВСЕМИ ДАННЫМИ**
2. Создавала бы новую пустую таблицу

**На проде это привело бы к ПОТЕРЕ ВСЕХ данных об отменах смен!**

---

## 📋 Порядок деплоя

### Шаг 1: Подготовка

```bash
# На локальной машине
cd /home/sa/projects/staffprobot
git checkout feature/owner-profile-extension
git pull origin feature/owner-profile-extension

# Проверяем, что миграция исправлена
grep -A 3 "КРИТИЧНО" migrations/versions/a266c36de460_add_organization_profiles_and_system_.py
```

Должны увидеть комментарии о сохранении `shift_cancellations`.

### Шаг 2: Бэкап на проде (ОБЯЗАТЕЛЬНО!)

```bash
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres -d staffprobot_prod > /tmp/backup_before_owner_profile_$(date +%Y%m%d_%H%M%S).sql'
```

### Шаг 3: Merge и push

```bash
# Локально
git checkout main
git merge feature/owner-profile-extension
git push origin main
```

### Шаг 4: Деплой на прод

```bash
# 1. Подключение и обновление кода
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && git fetch origin && git checkout main && git pull origin main'

# 2. Применение миграций (ВНИМАТЕЛЬНО!)
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec web alembic upgrade head'

# 3. Seed данных (SystemFeatures)
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec web python scripts/seed_system_features.py'

# 4. Seed данных (Organization Tags)
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec web python scripts/seed_organization_tags.py'

# 5. Перезапуск контейнеров
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml down && docker compose -f docker-compose.prod.yml up -d'
```

### Шаг 5: Проверка

```bash
# 1. Проверяем таблицы
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -c "\dt system_features"'
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -c "\dt organization_profiles"'
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -c "SELECT COUNT(*) FROM shift_cancellations"'

# 2. Проверяем SystemFeatures
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -c "SELECT key, name FROM system_features ORDER BY sort_order"'

# 3. Проверяем логи
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml logs web --tail 100'
```

### Шаг 6: Тестирование

1. ✅ Откройте https://staffprobot.ru/owner/profile
2. ✅ Проверьте отображение новых разделов
3. ✅ Включите/выключите функции
4. ✅ Проверьте видимость меню
5. ✅ Откройте https://staffprobot.ru/owner/cancellations (данные должны сохраниться)

---

## 🔧 Что делать если что-то пошло не так

### Если миграция упала:

```bash
# 1. Проверяем текущую версию
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec web alembic current'

# 2. Смотрим ошибку в логах
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml logs web --tail 200'

# 3. При необходимости откатываем миграцию
# ВНИМАНИЕ: откат тоже может потребовать исправления!
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec web alembic downgrade -1'
```

### Если данные потеряны (НЕ ДОЛЖНО ПРОИЗОЙТИ):

```bash
# Восстанавливаем из бэкапа
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec -T postgres psql -U postgres -d staffprobot_prod < /tmp/backup_before_owner_profile_*.sql'
```

---

## 📊 Что добавлено в проект

### Новые таблицы:

1. **`system_features`** - справочник дополнительных функций
2. **`organization_profiles`** - профили организаций (ИП/ЮЛ)

### Новые колонки в `owner_profiles`:

- `about_company` (TEXT) - описание компании
- `values` (TEXT) - ценности компании
- `photos` (JSON) - фотографии (до 5 шт)
- `contact_phone` (VARCHAR) - телефон для связи
- `contact_messengers` (JSON) - мессенджеры для связи
- `enabled_features` (JSON) - включенные функции

### Новые колонки в `org_structure_units`:

- `organization_profile_id` (INTEGER) - связь с профилем организации

### Новые скрипты:

- `scripts/seed_system_features.py` - заполнение справочника функций
- `scripts/seed_organization_tags.py` - заполнение тегов для реквизитов

### Новые роуты:

- `/owner/profile/organization/api/*` - API для управления профилями организаций
- `/owner/profile/features/api/*` - API для управления функциями
- `/owner/notifications` - страница управления уведомлениями (заглушка)

### Новый middleware:

- `FeaturesMiddleware` - автоматическое добавление `enabled_features` в контекст

---

## ✅ Чеклист перед деплоем

- [ ] Проверили, что в миграции закомментированы DROP/CREATE для `shift_cancellations`
- [ ] Сделали бэкап БД на проде
- [ ] Протестировали на dev-окружении
- [ ] Убедились, что seed скрипты работают
- [ ] Проверили, что все коммиты в ветке
- [ ] Готовы к быстрому откату если что-то пойдет не так

---

## 📞 Контакты для экстренных ситуаций

Если во время деплоя возникли проблемы:
1. **НЕ ПАНИКОВАТЬ**
2. Сохранить логи ошибок
3. Связаться с командой разработки
4. При необходимости откатить изменения

---

**Коммитов в ветке:** 27  
**Дата создания:** 2025-10-19  
**Статус:** ✅ Готово к деплою (после исправления миграции)

