# Project Brain - Как использовать СЕЙЧАС

## ✅ ЧТО ГОТОВО

- 2,000 QA пар в базе
- API работает: http://192.168.2.107:8003
- Score: 52.5% (reference quality)
- Скрипты готовы

## 🚀 КАК ИСПОЛЬЗОВАТЬ

### Способ 1: Веб-интерфейс (РЕКОМЕНДУЮ!)
```
1. Открой: http://192.168.2.107:8003/chat
2. Выбери проект: StaffProBot
3. Задай вопрос
4. СМОТРИ НА SOURCES ← ГЛАВНОЕ!
5. Открывай нужные файлы в Cursor
```

### Способ 2: Bash скрипт
```bash
cd /home/sa/projects/staffprobot
./.cursor/scripts/ask-brain.sh "Ваш вопрос"
```

### Способ 3: Python скрипт
```bash
python /home/sa/projects/staffprobot/.cursor/scripts/ask_brain.py "Ваш вопрос"
```

## ⚠️ ВАЖНО

**НЕ полагайся на answer полностью!**
- Answer может быть нерелевантным (52.5% точность)
- ВСЕГДА смотри на sources
- Проверяй файлы сам

**Используй Project Brain как:**
- 🔍 Быстрый поиск файлов
- 📖 Reference tool
- 🎯 Подсказки где искать

**НЕ используй как:**
- ❌ Единственный источник истины
- ❌ Для критичных решений без проверки

## 📖 ПОЛНАЯ ДОКУМЕНТАЦИЯ

См. `/home/sa/projects/staffprobot/.cursor/FINAL_REPORT_22_00.md`

---

**Готов к использованию как reference tool**: ✅ ДА  
**Production ready**: ⚠️ С оговорками (смотри sources!)  
**Качество**: 52.5% (приемлемо для reference)
