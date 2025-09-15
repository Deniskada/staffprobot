#!/bin/bash
# Быстрая диагностика лендинга в продакшене

if [ $# -eq 0 ]; then
    echo "Использование: $0 <URL>"
    echo "Пример: $0 https://yourdomain.com"
    exit 1
fi

URL=$1
echo "🔍 Быстрая диагностика лендинга для $URL"
echo "=========================================="

# Проверяем доступность главной страницы
echo "1. Проверяю главную страницу..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL")
if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ Главная страница доступна (HTTP $HTTP_CODE)"
else
    echo "   ❌ Главная страница недоступна (HTTP $HTTP_CODE)"
fi

# Проверяем статические файлы
echo "2. Проверяю статические файлы..."
CSS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL/static/css/main.css")
if [ "$CSS_CODE" = "200" ]; then
    echo "   ✅ CSS файл доступен (HTTP $CSS_CODE)"
else
    echo "   ❌ CSS файл недоступен (HTTP $CSS_CODE)"
fi

# Проверяем CDN ресурсы
echo "3. Проверяю CDN ресурсы..."
BOOTSTRAP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css")
if [ "$BOOTSTRAP_CODE" = "200" ]; then
    echo "   ✅ Bootstrap CDN доступен"
else
    echo "   ❌ Bootstrap CDN недоступен (HTTP $BOOTSTRAP_CODE)"
fi

# Проверяем содержимое страницы
echo "4. Проверяю содержимое страницы..."
HTML_CONTENT=$(curl -s "$URL")
if echo "$HTML_CONTENT" | grep -q "hero-section"; then
    echo "   ✅ Hero секция найдена"
else
    echo "   ❌ Hero секция не найдена"
fi

if echo "$HTML_CONTENT" | grep -q "entry-card"; then
    echo "   ✅ Карточки входа найдены"
else
    echo "   ❌ Карточки входа не найдены"
fi

if echo "$HTML_CONTENT" | grep -q "bootstrap.min.css"; then
    echo "   ✅ Bootstrap CSS подключен"
else
    echo "   ❌ Bootstrap CSS не подключен"
fi

if echo "$HTML_CONTENT" | grep -q "main.css"; then
    echo "   ✅ Custom CSS подключен"
else
    echo "   ❌ Custom CSS не подключен"
fi

# Проверяем Docker контейнеры
echo "5. Проверяю Docker контейнеры..."
if command -v docker &> /dev/null; then
    WEB_CONTAINER=$(docker ps --format "table {{.Names}}\t{{.Status}}" | grep -i staffprobot | grep -i web | head -1)
    if [ -n "$WEB_CONTAINER" ]; then
        echo "   ✅ Web контейнер найден: $WEB_CONTAINER"
    else
        echo "   ❌ Web контейнер не найден"
    fi
else
    echo "   ⚠️  Docker не установлен или недоступен"
fi

echo ""
echo "🎯 Для детальной диагностики запустите:"
echo "   python3 scripts/diagnose_landing.py $URL"
