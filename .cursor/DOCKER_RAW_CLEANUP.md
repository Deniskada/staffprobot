# Как сжать Docker.raw (468GB → реальный размер)

## 🔍 ПРОБЛЕМА

`/home/sa/.docker/desktop/vms/0/data/Docker.raw` = 468GB
Но реально используется только ~16-20GB!

Docker.raw **растёт, но не сжимается** автоматически.

---

## ✅ БЕЗОПАСНОЕ РЕШЕНИЕ

### Способ 1: Через Docker Desktop GUI (ЛУЧШИЙ)
```
1. Открой Docker Desktop
2. Settings (⚙️) → Resources → Advanced
3. Нажми кнопку "Disk image location"
4. Нажми "Compact" или "Optimize"
5. Подожди 5-10 минут
```

**Результат**: Docker.raw сожмётся до реального размера (~20-30GB)

---

### Способ 2: Через командную строку (БЕЗ GUI)

**ВНИМАНИЕ**: Это остановит все контейнеры!

```bash
# 1. Останови Docker Desktop
systemctl --user stop docker-desktop

# 2. Сожми диск (займёт 30-60 минут!)
cd /home/sa/.docker/desktop/vms/0/data/
qemu-img convert -O raw Docker.raw Docker-compact.raw  # -O (буква O, не ноль!)
mv Docker.raw Docker-backup.raw  # Сохраняем бэкап
mv Docker-compact.raw Docker.raw

# 3. Запусти Docker Desktop
systemctl --user start docker-desktop
```

**Результат**: 468GB → ~20-30GB

---

### Способ 3: Ограничить максимальный размер (ПРОФИЛАКТИКА)

Docker Desktop → Settings → Resources → Advanced:
- **Disk image size limit**: 100GB (вместо 468GB)

Перезапусти Docker Desktop.

---

## 🎯 МОЯ РЕКОМЕНДАЦИЯ

### Сейчас:
1. ✅ Я уже освободил **~27GB**:
   - Build cache: 12.5GB
   - Старые образы: 2.1GB
   - project-brain-api: 12.4GB

2. Docker.raw **НЕ сжался автоматически** (нужна ручная компактация)

### Для сжатия Docker.raw:
Выполни **Способ 1** (через GUI) - самый безопасный!

**Ожидаемый результат**: 468GB → 20-30GB ✅

---

## ⚠️ НЕ ТРОГАЙ VOLUMES (11.36GB)!

Volumes содержат:
- staffprobot_postgres_prod_data - БАЗА ДАННЫХ ПРОДА!
- staffprobot_postgres_dev_data - база dev
- project-brain_chroma_data - векторная БД
- Redis, RabbitMQ данные

**Удаление = потеря данных!**

---

**Уже освобождено**: 27GB ✅  
**Можно освободить через Compact**: 440GB  
**НЕ трогать**: Volumes (данные проектов)

См. `/home/sa/projects/project-brain/CLEANUP_REPORT.md` для деталей.
