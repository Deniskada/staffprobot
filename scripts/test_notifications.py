"""
Скрипт для тестирования системы уведомлений StaffProBot.

Использование:
    docker compose -f docker-compose.dev.yml exec web python scripts/test_notifications.py

Или внутри контейнера:
    python scripts/test_notifications.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from core.database.session import get_async_session
from core.logging.logger import logger
from domain.entities.user import User
from domain.entities.notification import (
    NotificationType,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus
)
from shared.services.notification_service import NotificationService
from shared.services.notification_dispatcher import NotificationDispatcher


async def get_test_user() -> User | None:
    """Получение первого доступного пользователя для тестирования."""
    try:
        async with get_async_session() as session:
            # Получаем первого пользователя с telegram_id
            query = select(User).where(User.telegram_id.isnot(None)).limit(1)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if user:
                print(f"✅ Найден пользователь для тестирования:")
                print(f"   ID: {user.id}")
                print(f"   Имя: {user.full_name}")
                print(f"   Telegram ID: {user.telegram_id}")
                print(f"   Email: {user.email or 'не указан'}")
                return user
            else:
                print("❌ Пользователи с Telegram ID не найдены!")
                print("💡 Подсказка: зарегистрируйте пользователя через Telegram бота")
                return None
                
    except Exception as e:
        logger.error(f"Ошибка получения пользователя: {e}")
        print(f"❌ Ошибка: {e}")
        return None


async def test_create_notification(user_id: int) -> None:
    """Тест создания уведомления через NotificationService."""
    print("\n" + "="*70)
    print("ТЕСТ 1: Создание уведомления через NotificationService")
    print("="*70)
    
    try:
        service = NotificationService()
        
        # Создаём тестовое уведомление
        notification = await service.create_notification(
            user_id=user_id,
            type=NotificationType.WELCOME,
            channel=NotificationChannel.TELEGRAM,
            title="🎉 Добро пожаловать в StaffProBot!",
            message="Это тестовое уведомление для проверки работы системы.",
            data={
                "test": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            priority=NotificationPriority.NORMAL
        )
        
        if notification:
            print(f"✅ Уведомление создано успешно!")
            print(f"   ID: {notification.id}")
            print(f"   Тип: {notification.type.value}")
            print(f"   Канал: {notification.channel.value}")
            print(f"   Статус: {notification.status.value}")
            print(f"   Заголовок: {notification.title}")
            print(f"   Сообщение: {notification.message}")
            return notification.id
        else:
            print("❌ Не удалось создать уведомление")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка создания уведомления: {e}")
        print(f"❌ Ошибка: {e}")
        return None


async def test_dispatch_notification(notification_id: int) -> None:
    """Тест отправки уведомления через NotificationDispatcher."""
    print("\n" + "="*70)
    print("ТЕСТ 2: Отправка уведомления через NotificationDispatcher")
    print("="*70)
    
    try:
        dispatcher = NotificationDispatcher()
        
        print(f"📤 Отправка уведомления ID={notification_id}...")
        success = await dispatcher.dispatch_notification(notification_id)
        
        if success:
            print("✅ Уведомление отправлено успешно!")
            print("💡 Проверьте Telegram, должно прийти сообщение")
        else:
            print("❌ Не удалось отправить уведомление")
            print("💡 Проверьте логи для деталей")
            
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {e}")
        print(f"❌ Ошибка: {e}")


async def test_scheduled_notification(user_id: int) -> None:
    """Тест запланированного уведомления."""
    print("\n" + "="*70)
    print("ТЕСТ 3: Создание запланированного уведомления")
    print("="*70)
    
    try:
        service = NotificationService()
        
        # Создаём уведомление, запланированное через 30 секунд
        scheduled_time = datetime.now(timezone.utc) + timedelta(seconds=30)
        
        notification = await service.create_notification(
            user_id=user_id,
            type=NotificationType.SHIFT_REMINDER,
            channel=NotificationChannel.TELEGRAM,
            title="⏰ Напоминание о смене",
            message="Это запланированное тестовое уведомление (должно прийти через 30 сек).",
            data={
                "test": True,
                "scheduled": True
            },
            priority=NotificationPriority.HIGH,
            scheduled_at=scheduled_time
        )
        
        if notification:
            print(f"✅ Запланированное уведомление создано!")
            print(f"   ID: {notification.id}")
            print(f"   Запланировано на: {scheduled_time.strftime('%H:%M:%S')}")
            print(f"   Статус: {notification.status.value}")
            print("\n💡 Чтобы отправить запланированные уведомления, используйте:")
            print("   await dispatcher.dispatch_scheduled_notifications()")
            return notification.id
        else:
            print("❌ Не удалось создать запланированное уведомление")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка создания запланированного уведомления: {e}")
        print(f"❌ Ошибка: {e}")
        return None


async def test_get_user_notifications(user_id: int) -> None:
    """Тест получения уведомлений пользователя."""
    print("\n" + "="*70)
    print("ТЕСТ 4: Получение уведомлений пользователя")
    print("="*70)
    
    try:
        service = NotificationService()
        
        # Получаем все уведомления
        all_notifications = await service.get_user_notifications(
            user_id=user_id,
            limit=10
        )
        
        print(f"📊 Всего уведомлений: {len(all_notifications)}")
        
        # Получаем количество непрочитанных
        unread_count = await service.get_unread_count(user_id)
        print(f"📬 Непрочитанных: {unread_count}")
        
        # Показываем последние 5 уведомлений
        if all_notifications:
            print("\n📝 Последние уведомления:")
            for i, notif in enumerate(all_notifications[:5], 1):
                status_emoji = "✅" if notif.status == NotificationStatus.SENT else "📤"
                print(f"   {i}. {status_emoji} [{notif.type.value}] {notif.title}")
                print(f"      Статус: {notif.status.value} | Создано: {notif.created_at.strftime('%Y-%m-%d %H:%M')}")
        else:
            print("   (нет уведомлений)")
            
    except Exception as e:
        logger.error(f"Ошибка получения уведомлений: {e}")
        print(f"❌ Ошибка: {e}")


async def test_mark_as_read(user_id: int) -> None:
    """Тест отметки уведомления как прочитанного."""
    print("\n" + "="*70)
    print("ТЕСТ 5: Отметка уведомления как прочитанного")
    print("="*70)
    
    try:
        service = NotificationService()
        
        # Получаем первое непрочитанное
        notifications = await service.get_user_notifications(
            user_id=user_id,
            include_read=False,
            limit=1
        )
        
        if notifications:
            notif = notifications[0]
            print(f"📬 Отмечаем как прочитанное: {notif.title}")
            
            success = await service.mark_as_read(
                notification_id=notif.id,
                user_id=user_id
            )
            
            if success:
                print("✅ Уведомление отмечено как прочитанное")
            else:
                print("❌ Не удалось отметить как прочитанное")
        else:
            print("💡 Нет непрочитанных уведомлений")
            
    except Exception as e:
        logger.error(f"Ошибка отметки как прочитанного: {e}")
        print(f"❌ Ошибка: {e}")


async def test_different_notification_types(user_id: int) -> None:
    """Тест создания уведомлений разных типов."""
    print("\n" + "="*70)
    print("ТЕСТ 6: Создание уведомлений разных типов")
    print("="*70)
    
    service = NotificationService()
    dispatcher = NotificationDispatcher()
    
    # Список тестовых уведомлений
    test_notifications = [
        {
            "type": NotificationType.SHIFT_REMINDER,
            "title": "⏰ Напоминание о смене",
            "message": "Ваша смена начинается через 2 часа!",
            "priority": NotificationPriority.HIGH
        },
        {
            "type": NotificationType.CONTRACT_SIGNED,
            "title": "📝 Договор подписан",
            "message": "Ваш договор успешно подписан и активирован.",
            "priority": NotificationPriority.NORMAL
        },
        {
            "type": NotificationType.REVIEW_RECEIVED,
            "title": "⭐ Получен новый отзыв",
            "message": "Вы получили новый отзыв с оценкой 5 звёзд!",
            "priority": NotificationPriority.LOW
        },
    ]
    
    created_ids = []
    
    for test_data in test_notifications:
        try:
            notification = await service.create_notification(
                user_id=user_id,
                type=test_data["type"],
                channel=NotificationChannel.TELEGRAM,
                title=test_data["title"],
                message=test_data["message"],
                priority=test_data["priority"],
                data={"test": True, "batch": "different_types"}
            )
            
            if notification:
                created_ids.append(notification.id)
                print(f"✅ Создано: [{test_data['type'].value}] {test_data['title']}")
            else:
                print(f"❌ Ошибка создания: {test_data['title']}")
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    # Отправляем все созданные уведомления
    if created_ids:
        print(f"\n📤 Отправка {len(created_ids)} уведомлений...")
        for notif_id in created_ids:
            await dispatcher.dispatch_notification(notif_id)
        print("✅ Отправка завершена!")


async def test_urgent_notification(user_id: int) -> None:
    """Тест срочного уведомления."""
    print("\n" + "="*70)
    print("ТЕСТ 7: Создание срочного уведомления")
    print("="*70)
    
    try:
        service = NotificationService()
        dispatcher = NotificationDispatcher()
        
        notification = await service.create_notification(
            user_id=user_id,
            type=NotificationType.ACCOUNT_SUSPENDED,
            channel=NotificationChannel.TELEGRAM,
            title="🚨 СРОЧНО: Требуется действие",
            message="Это срочное уведомление с высоким приоритетом!",
            priority=NotificationPriority.URGENT,
            data={"test": True, "urgent": True}
        )
        
        if notification:
            print(f"✅ Срочное уведомление создано (ID={notification.id})")
            print(f"   Приоритет: {notification.priority.value}")
            
            # Немедленная отправка
            print("📤 Отправка срочного уведомления...")
            success = await dispatcher.dispatch_notification(notification.id)
            
            if success:
                print("✅ Срочное уведомление отправлено!")
            else:
                print("❌ Ошибка отправки срочного уведомления")
        else:
            print("❌ Не удалось создать срочное уведомление")
            
    except Exception as e:
        logger.error(f"Ошибка создания срочного уведомления: {e}")
        print(f"❌ Ошибка: {e}")


async def run_all_tests() -> None:
    """Запуск всех тестов."""
    print("\n" + "="*70)
    print("🧪 ТЕСТИРОВАНИЕ СИСТЕМЫ УВЕДОМЛЕНИЙ STAFFPROBOT")
    print("="*70)
    
    # Получаем тестового пользователя
    user = await get_test_user()
    
    if not user:
        print("\n❌ Невозможно продолжить тесты без пользователя!")
        print("💡 Создайте пользователя через Telegram бота или веб-интерфейс")
        return
    
    user_id = user.id
    
    # Запускаем тесты
    print("\n🚀 Начинаем тестирование...\n")
    
    # Тест 1: Создание уведомления
    notification_id = await test_create_notification(user_id)
    
    # Тест 2: Отправка уведомления
    if notification_id:
        await test_dispatch_notification(notification_id)
    
    # Тест 3: Запланированное уведомление
    await test_scheduled_notification(user_id)
    
    # Тест 4: Получение уведомлений
    await test_get_user_notifications(user_id)
    
    # Тест 5: Отметка как прочитанного
    await test_mark_as_read(user_id)
    
    # Тест 6: Разные типы уведомлений
    await test_different_notification_types(user_id)
    
    # Тест 7: Срочное уведомление
    await test_urgent_notification(user_id)
    
    # Финальная статистика
    await test_get_user_notifications(user_id)
    
    print("\n" + "="*70)
    print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ!")
    print("="*70)
    print("\n💡 Проверьте Telegram для просмотра полученных уведомлений")
    print("💡 Проверьте логи для деталей: docker compose -f docker-compose.dev.yml logs web")


async def interactive_menu() -> None:
    """Интерактивное меню для выбора тестов."""
    user = await get_test_user()
    
    if not user:
        return
    
    user_id = user.id
    
    while True:
        print("\n" + "="*70)
        print("📋 МЕНЮ ТЕСТИРОВАНИЯ УВЕДОМЛЕНИЙ")
        print("="*70)
        print("1. Запустить все тесты")
        print("2. Создать и отправить одно тестовое уведомление")
        print("3. Создать запланированное уведомление")
        print("4. Посмотреть мои уведомления")
        print("5. Отметить все как прочитанные")
        print("6. Создать уведомления разных типов")
        print("7. Создать срочное уведомление")
        print("0. Выход")
        print("="*70)
        
        choice = input("\nВыберите действие (0-7): ").strip()
        
        if choice == "0":
            print("👋 До свидания!")
            break
        elif choice == "1":
            await run_all_tests()
        elif choice == "2":
            notif_id = await test_create_notification(user_id)
            if notif_id:
                await test_dispatch_notification(notif_id)
        elif choice == "3":
            await test_scheduled_notification(user_id)
        elif choice == "4":
            await test_get_user_notifications(user_id)
        elif choice == "5":
            service = NotificationService()
            count = await service.mark_all_as_read(user_id)
            print(f"✅ Отмечено как прочитанных: {count}")
        elif choice == "6":
            await test_different_notification_types(user_id)
        elif choice == "7":
            await test_urgent_notification(user_id)
        else:
            print("❌ Неверный выбор, попробуйте снова")


def main():
    """Главная функция."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        # Запуск всех тестов
        asyncio.run(run_all_tests())
    else:
        # Интерактивное меню
        asyncio.run(interactive_menu())


if __name__ == "__main__":
    main()

