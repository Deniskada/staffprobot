# ✅ ЧЕКЛИСТ ПРОВЕРКИ Project Brain

Используй этот чеклист для проверки работоспособности.

## 1. Проверка статуса API
```bash
curl http://192.168.2.107:8003/health
```
**Ожидаемый результат**: `{"status":"ok"}`

## 2. Проверка базы знаний
```bash
curl http://192.168.2.107:8003/api/webhook/status/staffprobot
```
**Ожидаемый результат**: JSON с информацией о последней индексации

## 3. Тест простого запроса
```bash
cd /home/sa/projects/staffprobot
./.cursor/scripts/ask-brain.sh "Модель User"
```
**Ожидаемый результат**:
- ✅ Файл указан
- ✅ Строки указаны  
- ✅ Код включен

## 4. Тест сложного запроса
```bash
./.cursor/scripts/ask-brain.sh "Где логика открытия смены?"
```
**Ожидаемый результат**:
- ✅ Релевантный файл
- ✅ Правильные строки
- ✅ Код функции

## 5. Тест Python клиента
```bash
python ./.cursor/scripts/ask_brain.py "API endpoints для owner"
```
**Ожидаемый результат**:
- ✅ Список endpoints
- ✅ Файлы указаны
- ✅ Топ-3 источника показаны

## 6. Тест веб-интерфейса
Открой в браузере: http://192.168.2.107:8003/chat
- ✅ Страница загружается
- ✅ Можно выбрать проект "StaffProBot"
- ✅ Можно задать вопрос
- ✅ Ответ содержит файл + строки + код

## 7. Проверка документации
```bash
cat /home/sa/projects/staffprobot/.cursor/README.md
cat /home/sa/projects/staffprobot/.cursor/SUMMARY.md
```
**Ожидаемый результат**:
- ✅ Файлы существуют
- ✅ Содержат инструкции

## 8. Проверка контейнеров
```bash
docker compose -f /home/sa/projects/project-brain/docker-compose.local.yml ps
```
**Ожидаемый результат**:
- ✅ api - Up
- ✅ chromadb - Up
- ✅ redis - Up

## 9. Проверка автообновления (опционально)
```bash
curl -X POST http://192.168.2.107:8003/api/webhook/manual-reindex/staffprobot
```
**Ожидаемый результат**: JSON с статусом "in_progress" или "completed"

## 10. Финальный тест качества
```bash
cd /home/sa/projects/project-brain
docker compose -f docker-compose.local.yml exec -T api \
  python /app/scripts/evaluate_qa_quality.py 2>&1 | grep "TOTAL SCORE"
```
**Ожидаемый результат**: `⭐ TOTAL SCORE: 85.1%` или выше

---

## ✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ?

Если да - **Project Brain готов к использованию!** 🎉

Если нет - проверь логи:
```bash
docker compose -f /home/sa/projects/project-brain/docker-compose.local.yml logs api --tail 100
```

---

**Дата**: 18.10.2025 03:30 МСК  
**Статус**: ✅ PRODUCTION READY
