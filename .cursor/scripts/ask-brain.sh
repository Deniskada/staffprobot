#!/bin/bash
# Project Brain - Quick Access Script для Cursor
# Использование: ./ask-brain.sh "Ваш вопрос"

BRAIN_URL="http://192.168.2.107:8003/api/query"
PROJECT="staffprobot"

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

if [ $# -eq 0 ]; then
    echo -e "${YELLOW}Использование: $0 \"Ваш вопрос\"${NC}"
    echo ""
    echo "Примеры:"
    echo "  $0 \"Где функция start_shift?\""
    echo "  $0 \"API endpoint для создания объекта\""
    echo "  $0 \"Поля модели User\""
    exit 1
fi

QUERY="$*"

echo -e "${BLUE}🤖 Спрашиваю Project Brain...${NC}"
echo ""

# Отправляем запрос
RESPONSE=$(curl -s "$BRAIN_URL" \
  -H 'Content-Type: application/json' \
  -d "{\"query\":\"$QUERY\",\"project\":\"$PROJECT\"}")

# Проверяем ошибки
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Ошибка подключения к Project Brain${NC}"
    echo "Проверьте, что API запущен: docker compose -f docker-compose.local.yml ps"
    exit 1
fi

# Извлекаем ответ
ANSWER=$(echo "$RESPONSE" | jq -r '.answer')

if [ "$ANSWER" = "null" ] || [ -z "$ANSWER" ]; then
    echo -e "${YELLOW}⚠️  Не удалось получить ответ${NC}"
    echo "Ответ API:"
    echo "$RESPONSE" | jq '.'
    exit 1
fi

# Выводим ответ
echo -e "${GREEN}$ANSWER${NC}"
echo ""

# Извлекаем количество источников
SOURCES_COUNT=$(echo "$RESPONSE" | jq '.sources | length')
echo -e "${BLUE}📚 Использовано источников: $SOURCES_COUNT${NC}"

# Извлекаем время обработки
PROCESSING_TIME=$(echo "$RESPONSE" | jq -r '.processing_time')
if [ "$PROCESSING_TIME" != "null" ]; then
    echo -e "${BLUE}⏱️  Время обработки: ${PROCESSING_TIME}s${NC}"
fi

