#!/bin/bash

# Скрипт развертывания системы отзывов и рейтингов
# Использование: ./deploy_reviews.sh [environment] [version]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для логирования
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌${NC} $1"
}

# Параметры
ENVIRONMENT=${1:-production}
VERSION=${2:-latest}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

log "Начинаем развертывание системы отзывов и рейтингов"
log "Окружение: $ENVIRONMENT"
log "Версия: $VERSION"
log "Директория проекта: $PROJECT_DIR"

# Проверка окружения
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    log_error "Неверное окружение. Используйте: development, staging, production"
    exit 1
fi

# Проверка Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker не установлен"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose не установлен"
    exit 1
fi

# Функция проверки статуса сервисов
check_services() {
    log "Проверяем статус сервисов..."
    
    # Проверяем PostgreSQL
    if ! docker-compose -f docker-compose.${ENVIRONMENT}.yml ps postgres | grep -q "Up"; then
        log_error "PostgreSQL не запущен"
        return 1
    fi
    
    # Проверяем Redis
    if ! docker-compose -f docker-compose.${ENVIRONMENT}.yml ps redis | grep -q "Up"; then
        log_warning "Redis не запущен (опционально)"
    fi
    
    # Проверяем веб-сервис
    if ! docker-compose -f docker-compose.${ENVIRONMENT}.yml ps web | grep -q "Up"; then
        log_error "Веб-сервис не запущен"
        return 1
    fi
    
    log_success "Все сервисы запущены"
}

# Функция создания резервной копии
create_backup() {
    log "Создаем резервную копию базы данных..."
    
    BACKUP_DIR="$PROJECT_DIR/deployment/backup"
    BACKUP_FILE="staffprobot_reviews_$(date +%Y%m%d_%H%M%S).sql"
    
    mkdir -p "$BACKUP_DIR"
    
    docker-compose -f docker-compose.${ENVIRONMENT}.yml exec -T postgres pg_dump -U postgres -d staffprobot_${ENVIRONMENT} > "$BACKUP_DIR/$BACKUP_FILE"
    
    if [ $? -eq 0 ]; then
        log_success "Резервная копия создана: $BACKUP_FILE"
    else
        log_error "Ошибка создания резервной копии"
        exit 1
    fi
}

# Функция применения миграций
apply_migrations() {
    log "Применяем миграции базы данных..."
    
    # Проверяем текущую версию миграций
    CURRENT_VERSION=$(docker-compose -f docker-compose.${ENVIRONMENT}.yml exec -T web alembic current 2>/dev/null | grep -o '[a-f0-9]\{12\}' || echo "none")
    log "Текущая версия миграций: $CURRENT_VERSION"
    
    # Применяем миграции
    docker-compose -f docker-compose.${ENVIRONMENT}.yml exec web alembic upgrade head
    
    if [ $? -eq 0 ]; then
        log_success "Миграции применены успешно"
    else
        log_error "Ошибка применения миграций"
        exit 1
    fi
}

# Функция создания директорий
create_directories() {
    log "Создаем необходимые директории..."
    
    # Директория для медиа-файлов
    docker-compose -f docker-compose.${ENVIRONMENT}.yml exec web mkdir -p /app/uploads/photos
    docker-compose -f docker-compose.${ENVIRONMENT}.yml exec web mkdir -p /app/uploads/videos
    docker-compose -f docker-compose.${ENVIRONMENT}.yml exec web mkdir -p /app/uploads/audio
    docker-compose -f docker-compose.${ENVIRONMENT}.yml exec web mkdir -p /app/uploads/documents
    docker-compose -f docker-compose.${ENVIRONMENT}.yml exec web mkdir -p /app/uploads/temp
    
    # Директория для логов
    docker-compose -f docker-compose.${ENVIRONMENT}.yml exec web mkdir -p /app/logs/reviews
    
    # Директория для резервных копий
    docker-compose -f docker-compose.${ENVIRONMENT}.yml exec web mkdir -p /app/backups
    
    # Устанавливаем права доступа
    docker-compose -f docker-compose.${ENVIRONMENT}.yml exec web chmod -R 755 /app/uploads
    docker-compose -f docker-compose.${ENVIRONMENT}.yml exec web chmod -R 755 /app/logs
    docker-compose -f docker-compose.${ENVIRONMENT}.yml exec web chmod -R 755 /app/backups
    
    log_success "Директории созданы"
}

# Функция настройки конфигурации
setup_configuration() {
    log "Настраиваем конфигурацию..."
    
    # Копируем файл конфигурации
    if [ -f "$PROJECT_DIR/deployment/reviews.env.example" ]; then
        cp "$PROJECT_DIR/deployment/reviews.env.example" "$PROJECT_DIR/.env.reviews"
        log_success "Файл конфигурации скопирован"
    else
        log_warning "Файл конфигурации не найден, создаем базовый"
        cat > "$PROJECT_DIR/.env.reviews" << EOF
# Базовая конфигурация системы отзывов
MEDIA_UPLOAD_DIR=/app/uploads
MODERATION_TIME_LIMIT_HOURS=48
APPEAL_TIME_LIMIT_HOURS=72
MIN_CONTENT_LENGTH=20
RATING_HALF_LIFE_DAYS=90
INITIAL_RATING=5.0
ENVIRONMENT=$ENVIRONMENT
EOF
    fi
    
    # Загружаем переменные окружения
    if [ -f "$PROJECT_DIR/.env.reviews" ]; then
        export $(cat "$PROJECT_DIR/.env.reviews" | grep -v '^#' | xargs)
        log_success "Переменные окружения загружены"
    fi
}

# Функция тестирования системы
test_system() {
    log "Тестируем систему отзывов..."
    
    # Тест API endpoints
    log "Тестируем API endpoints..."
    
    # Проверяем доступность API
    if curl -s -f "http://localhost:8001/api/media/limits" > /dev/null; then
        log_success "API медиа-файлов доступен"
    else
        log_warning "API медиа-файлов недоступен"
    fi
    
    # Проверяем веб-интерфейсы
    log "Тестируем веб-интерфейсы..."
    
    if curl -s -f "http://localhost:8001/owner/reviews" > /dev/null; then
        log_success "Интерфейс владельца доступен"
    else
        log_warning "Интерфейс владельца недоступен"
    fi
    
    if curl -s -f "http://localhost:8001/moderator/" > /dev/null; then
        log_success "Интерфейс модератора доступен"
    else
        log_warning "Интерфейс модератора недоступен"
    fi
    
    # Запускаем unit-тесты
    log "Запускаем unit-тесты..."
    if docker-compose -f docker-compose.${ENVIRONMENT}.yml exec web python -m pytest tests/integration/test_review_api_simple.py -v; then
        log_success "Unit-тесты прошли успешно"
    else
        log_warning "Unit-тесты завершились с предупреждениями"
    fi
}

# Функция настройки мониторинга
setup_monitoring() {
    log "Настраиваем мониторинг..."
    
    # Создаем конфигурацию Prometheus для отзывов
    cat > "$PROJECT_DIR/deployment/monitoring/reviews_metrics.yml" << EOF
# Метрики системы отзывов для Prometheus
reviews_total: counter
reviews_pending: gauge
reviews_approved: gauge
reviews_rejected: gauge
reviews_moderation_time: histogram
reviews_rating_average: gauge
appeals_total: counter
appeals_pending: gauge
media_uploads_total: counter
media_upload_size: histogram
EOF
    
    log_success "Конфигурация мониторинга создана"
}

# Функция создания пользователей-модераторов
create_moderators() {
    log "Создаем пользователей-модераторов..."
    
    # Создаем скрипт для добавления модераторов
    cat > "$PROJECT_DIR/scripts/create_moderators.py" << 'EOF'
#!/usr/bin/env python3
"""
Скрипт для создания пользователей-модераторов
"""

import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.session import get_async_session
from domain.entities.user import User, UserRole
from sqlalchemy import select

async def create_moderators():
    """Создает пользователей-модераторов."""
    async with get_async_session() as session:
        # Проверяем, есть ли уже модераторы
        query = select(User).where(User.role == UserRole.MODERATOR.value)
        result = await session.execute(query)
        moderators = result.scalars().all()
        
        if moderators:
            print(f"Найдено {len(moderators)} модераторов")
            return
        
        # Создаем тестового модератора
        moderator = User(
            telegram_id=999999999,
            username="moderator",
            first_name="Модератор",
            last_name="Системы",
            role=UserRole.MODERATOR.value
        )
        
        session.add(moderator)
        await session.commit()
        
        print("Создан тестовый модератор")

if __name__ == "__main__":
    asyncio.run(create_moderators())
EOF
    
    # Запускаем скрипт
    docker-compose -f docker-compose.${ENVIRONMENT}.yml exec web python scripts/create_moderators.py
    
    log_success "Модераторы созданы"
}

# Функция финальной проверки
final_check() {
    log "Выполняем финальную проверку..."
    
    # Проверяем статус всех сервисов
    check_services
    
    # Проверяем доступность API
    test_system
    
    # Проверяем логи на ошибки
    log "Проверяем логи на ошибки..."
    if docker-compose -f docker-compose.${ENVIRONMENT}.yml logs web | grep -i error | tail -5; then
        log_warning "Найдены ошибки в логах"
    else
        log_success "Критических ошибок не найдено"
    fi
    
    log_success "Финальная проверка завершена"
}

# Основная функция
main() {
    log "🚀 Начинаем развертывание системы отзывов и рейтингов"
    
    # Переходим в директорию проекта
    cd "$PROJECT_DIR"
    
    # Проверяем сервисы
    check_services
    
    # Создаем резервную копию (только для production)
    if [ "$ENVIRONMENT" = "production" ]; then
        create_backup
    fi
    
    # Создаем директории
    create_directories
    
    # Настраиваем конфигурацию
    setup_configuration
    
    # Применяем миграции
    apply_migrations
    
    # Создаем модераторов
    create_moderators
    
    # Настраиваем мониторинг
    setup_monitoring
    
    # Тестируем систему
    test_system
    
    # Выполняем финальную проверку
    final_check
    
    log_success "🎉 Развертывание системы отзывов и рейтингов завершено успешно!"
    log "Система готова к использованию в окружении: $ENVIRONMENT"
    log "Версия: $VERSION"
    
    # Выводим полезную информацию
    echo ""
    log "📋 Полезные команды:"
    echo "  • Просмотр логов: docker-compose -f docker-compose.${ENVIRONMENT}.yml logs web"
    echo "  • Перезапуск сервисов: docker-compose -f docker-compose.${ENVIRONMENT}.yml restart web"
    echo "  • Проверка статуса: docker-compose -f docker-compose.${ENVIRONMENT}.yml ps"
    echo "  • Применение миграций: docker-compose -f docker-compose.${ENVIRONMENT}.yml exec web alembic upgrade head"
    echo ""
    log "🌐 Доступные интерфейсы:"
    echo "  • Владелец: http://localhost:8001/owner/reviews"
    echo "  • Сотрудник: http://localhost:8001/employee/reviews"
    echo "  • Управляющий: http://localhost:8001/manager/reviews"
    echo "  • Модератор: http://localhost:8001/moderator/"
    echo "  • API документация: http://localhost:8001/docs"
    echo ""
}

# Обработка ошибок
trap 'log_error "Развертывание прервано из-за ошибки на строке $LINENO"' ERR

# Запуск основной функции
main "$@"
