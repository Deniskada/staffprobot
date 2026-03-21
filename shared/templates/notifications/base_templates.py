"""Шаблоны уведомлений для StaffProBot."""

from typing import Dict, Any, Optional
from string import Template
from domain.entities.notification import NotificationType, NotificationChannel
from core.logging.logger import logger


class NotificationTemplateManager:
    """Менеджер шаблонов уведомлений."""
    
    # Шаблоны для смен
    SHIFT_TEMPLATES = {
        NotificationType.SHIFT_REMINDER: {
            "title": "Напоминание о смене",
            "plain": "Привет, $user_name!\n\nНапоминаем, что ваша смена начинается через $time_until на объекте '$object_name'.\n\nВремя смены: $shift_time\nАдрес: $object_address\n\nНе забудьте отметиться по геолокации!",
            "html": """<h2>Напоминание о смене</h2>
<p>Привет, <strong>$user_name</strong>!</p>
<p>Напоминаем, что ваша смена начинается через <strong>$time_until</strong> на объекте <strong>'$object_name'</strong>.</p>
<p><strong>Время смены:</strong> $shift_time<br>
<strong>Адрес:</strong> $object_address</p>
<p>Не забудьте отметиться по геолокации!</p>""",
            "telegram": "🔔 *Напоминание о смене*\n\nПривет, $user_name!\n\nТвоя смена начинается через *$time_until* на объекте *$object_name*.\n\n⏰ Время: $shift_time\n📍 Адрес: $object_address\n\n⚠️ Не забудь отметиться по геолокации!\n\n🔗 $link_url"
        },
        NotificationType.SHIFT_CONFIRMED: {
            "title": "Смена запланирована сотрудником",
            "plain": "Сотрудник $employee_name запланировал смену на объекте '$object_name'.\nВремя: $shift_time.",
            "html": """<h2>Смена запланирована</h2>
<p>Сотрудник <strong>$employee_name</strong> запланировал смену на объекте <strong>'$object_name'</strong>.</p>
<p><strong>Время:</strong> $shift_time</p>"""
        },
        NotificationType.SHIFT_CANCELLED: {
            "title": "Смена отменена",
            "plain": "Здравствуйте, $user_name.\n\nСмена на объекте '$object_name' ($shift_time) была отменена.\n\nПричина: $cancellation_reason\n\nПриносим извинения за неудобства.",
            "html": """<h2>Смена отменена ❌</h2>
<p>Здравствуйте, <strong>$user_name</strong>.</p>
<p>Смена на объекте <strong>'$object_name'</strong> ($shift_time) была отменена.</p>
<p><strong>Причина:</strong> $cancellation_reason</p>
<p>Приносим извинения за неудобства.</p>"""
        },
        NotificationType.SHIFT_STARTED: {
            "title": "Смена началась",
            "plain": "Смена на объекте '$object_name' началась.\n\nВремя начала: $start_time\nХорошей работы, $user_name!",
            "html": """<h2>Смена началась 🚀</h2>
<p>Смена на объекте <strong>'$object_name'</strong> началась.</p>
<p><strong>Время начала:</strong> $start_time</p>
<p>Хорошей работы, <strong>$user_name</strong>!</p>"""
        },
        NotificationType.SHIFT_COMPLETED: {
            "title": "Смена завершена",
            "plain": "Смена на объекте '$object_name' завершена.\n\nВремя работы: $duration\nСпасибо за работу, $user_name!",
            "html": """<h2>Смена завершена ✅</h2>
<p>Смена на объекте <strong>'$object_name'</strong> завершена.</p>
<p><strong>Время работы:</strong> $duration</p>
<p>Спасибо за работу, <strong>$user_name</strong>!</p>"""
        },
        NotificationType.SHIFT_DID_NOT_START: {
            "title": "Смена не состоялась",
            "plain": "Смена на объекте '$object_name' не состоялась.\n\nПлановое время: $shift_time\nСотрудник: $employee_name\n\nСмена была запланирована, но сотрудник не приступил к работе.",
            "html": """<h2>Смена не состоялась ⚠️</h2>
<p>Смена на объекте <strong>'$object_name'</strong> не состоялась.</p>
<p><strong>Плановое время:</strong> $shift_time<br>
<strong>Сотрудник:</strong> $employee_name</p>
<p>Смена была запланирована, но сотрудник не приступил к работе.</p>""",
            "telegram": "⚠️ *Смена не состоялась*\n\nСмена на объекте *$object_name* не состоялась.\n\n⏰ Плановое время: $shift_time\n👤 Сотрудник: $employee_name\n\n🔗 $link_url"
        }
    }
    
    # Шаблоны для договоров
    CONTRACT_TEMPLATES = {
        NotificationType.CONTRACT_SIGNED: {
            "title": "Договор подписан",
            "plain": "Поздравляем, $user_name!\n\nДоговор №$contract_number успешно подписан.\n\nНачало действия: $start_date\nОкончание: $end_date\nПочасовая ставка: $hourly_rate руб.\n\nДобро пожаловать в команду!",
            "html": """<h2>Договор подписан ✅</h2>
<p>Поздравляем, <strong>$user_name</strong>!</p>
<p>Договор <strong>№$contract_number</strong> успешно подписан.</p>
<p><strong>Начало действия:</strong> $start_date<br>
<strong>Окончание:</strong> $end_date<br>
<strong>Почасовая ставка:</strong> $hourly_rate руб.</p>
<p>Добро пожаловать в команду!</p>""",
            "telegram": "✅ *Договор подписан*\n\nПоздравляем, $user_name!\n\nДоговор *№$contract_number* успешно подписан.\n\n📅 Начало: $start_date\n💰 Ставка: $hourly_rate руб/ч\n\n🔗 $link_url"
        },
        NotificationType.CONTRACT_TERMINATED: {
            "title": "Договор расторгнут",
            "plain": "Уважаемый $user_name,\n\nДоговор №$contract_number был расторгнут.\n\nДата расторжения: $termination_date\nПричина: $termination_reason\n\nСпасибо за сотрудничество!",
            "html": """<h2>Договор расторгнут</h2>
<p>Уважаемый <strong>$user_name</strong>,</p>
<p>Договор <strong>№$contract_number</strong> был расторгнут.</p>
<p><strong>Дата расторжения:</strong> $termination_date<br>
<strong>Причина:</strong> $termination_reason</p>
<p>Спасибо за сотрудничество!</p>""",
            "telegram": "📋 *Договор расторгнут*\n\nДоговор *№$contract_number* расторгнут.\n\n📅 Дата: $termination_date\n📝 Причина: $termination_reason\n\n🔗 $link_url"
        },
        NotificationType.CONTRACT_EXPIRING: {
            "title": "Договор истекает",
            "plain": "Внимание, $user_name!\n\nВаш договор №$contract_number истекает через $days_left дней.\n\nДата окончания: $end_date\n\nПожалуйста, свяжитесь с вашим работодателем для продления.",
            "html": """<h2>Договор истекает ⚠️</h2>
<p>Внимание, <strong>$user_name</strong>!</p>
<p>Ваш договор <strong>№$contract_number</strong> истекает через <strong>$days_left дней</strong>.</p>
<p><strong>Дата окончания:</strong> $end_date</p>
<p>Пожалуйста, свяжитесь с вашим работодателем для продления.</p>""",
            "telegram": "⚠️ *Договор истекает*\n\nДоговор *№$contract_number* истекает через *$days_left дн*.\n\n📅 Окончание: $end_date\n\n🔗 $link_url"
        },
        NotificationType.CONTRACT_UPDATED: {
            "title": "Договор обновлен",
            "plain": "Здравствуйте, $user_name!\n\nДоговор №$contract_number был обновлен.\n\nИзменения:\n$changes\n\nПожалуйста, ознакомьтесь с новыми условиями.",
            "html": """<h2>Договор обновлен 📝</h2>
<p>Здравствуйте, <strong>$user_name</strong>!</p>
<p>Договор <strong>№$contract_number</strong> был обновлен.</p>
<p><strong>Изменения:</strong></p>
<p>$changes</p>
<p>Пожалуйста, ознакомьтесь с новыми условиями.</p>""",
            "telegram": "📝 *Договор обновлён*\n\nДоговор *№$contract_number* обновлён.\n\n$changes\n\n🔗 $link_url"
        }
    }
    
    # Шаблоны для оферт
    OFFER_TEMPLATES = {
        NotificationType.OFFER_SENT: {
            "title": "Оферта направлена на подписание",
            "plain": "Здравствуйте, $user_name!\n\nВам направлена оферта «$offer_title» от $company_name.\n\nДля подписания перейдите в личный кабинет: $accept_url",
            "html": """<h2>Оферта направлена на подписание 📋</h2>
<p>Здравствуйте, <strong>$user_name</strong>!</p>
<p>Вам направлена оферта <strong>«$offer_title»</strong> от <strong>$company_name</strong>.</p>
<p>Для подписания перейдите в <a href="$accept_url">личный кабинет</a>.</p>""",
            "telegram": "📋 *Оферта на подписание*\n\nЗдравствуйте, $user_name!\n\nВам направлена оферта *«$offer_title»* от *$company_name*.\n\n🔗 Подпишите в личном кабинете: $accept_url"
        },
        NotificationType.OFFER_ACCEPTED: {
            "title": "Оферта принята",
            "plain": "Сотрудник $employee_name принял оферту «$offer_title».\n\nДоговор №$contract_number вступил в силу.\nПодписанный документ доступен в разделе «Договоры».",
            "html": """<h2>Оферта принята ✅</h2>
<p>Сотрудник <strong>$employee_name</strong> принял оферту <strong>«$offer_title»</strong>.</p>
<p>Договор <strong>№$contract_number</strong> вступил в силу.</p>
<p>Подписанный документ доступен в разделе «Договоры».</p>""",
            "telegram": "✅ *Оферта принята*\n\nСотрудник *$employee_name* принял оферту *«$offer_title»*.\n\n📄 Договор №$contract_number вступил в силу.\n\n🔗 $link_url"
        },
        NotificationType.OFFER_REJECTED: {
            "title": "Оферта отклонена",
            "plain": "Сотрудник $employee_name отклонил оферту «$offer_title».",
            "html": """<h2>Оферта отклонена ❌</h2>
<p>Сотрудник <strong>$employee_name</strong> отклонил оферту <strong>«$offer_title»</strong>.</p>""",
            "telegram": "❌ *Оферта отклонена*\n\nСотрудник *$employee_name* отклонил оферту *«$offer_title»*.\n\n🔗 $link_url"
        },
        NotificationType.OFFER_TERMS_CHANGED: {
            "title": "Условия оферты изменены",
            "plain": "Здравствуйте, $user_name!\n\nУсловия оферты «$offer_title» обновлены.\nИзменения вступают в силу автоматически (п. 10.3 оферты).",
            "html": """<h2>Условия оферты изменены 📝</h2>
<p>Здравствуйте, <strong>$user_name</strong>!</p>
<p>Условия оферты <strong>«$offer_title»</strong> обновлены.</p>
<p>Изменения вступают в силу автоматически (п. 10.3 оферты).</p>""",
            "telegram": "📝 *Условия оферты изменены*\n\nУсловия оферты *«$offer_title»* обновлены.\nИзменения вступают в силу автоматически (п. 10.3).\n\n🔗 $link_url"
        }
    }
    
    # Шаблоны для KYC / верификации
    KYC_TEMPLATES = {
        NotificationType.KYC_REQUIRED: {
            "title": "Требуется верификация",
            "plain": "Здравствуйте, $user_name!\n\nДля верификации профиля пройдите проверку через Госуслуги: $kyc_url",
            "html": """<h2>Требуется верификация 🔐</h2>
<p>Здравствуйте, <strong>$user_name</strong>!</p>
<p>Для верификации профиля пройдите проверку через <a href="$kyc_url">Госуслуги</a>.</p>""",
            "telegram": "🔐 *Требуется верификация*\n\nДля верификации профиля пройдите проверку через Госуслуги:\n$kyc_url"
        },
        NotificationType.KYC_VERIFIED: {
            "title": "Профиль верифицирован",
            "plain": "Поздравляем, $user_name!\n\nВаш профиль успешно верифицирован через Госуслуги.",
            "html": """<h2>Профиль верифицирован ✅</h2>
<p>Поздравляем, <strong>$user_name</strong>!</p>
<p>Ваш профиль успешно верифицирован через Госуслуги.</p>""",
            "telegram": "✅ *Профиль верифицирован*\n\nПоздравляем, $user_name! Ваш профиль успешно верифицирован через Госуслуги."
        },
        NotificationType.KYC_FAILED: {
            "title": "Верификация не пройдена",
            "plain": "Здравствуйте, $user_name.\n\nВерификация профиля через Госуслуги не пройдена.\nПричина: $failure_reason\n\nВы можете повторить попытку.",
            "html": """<h2>Верификация не пройдена ❌</h2>
<p>Здравствуйте, <strong>$user_name</strong>.</p>
<p>Верификация профиля через Госуслуги не пройдена.</p>
<p><strong>Причина:</strong> $failure_reason</p>
<p>Вы можете повторить попытку.</p>""",
            "telegram": "❌ *Верификация не пройдена*\n\nПричина: $failure_reason\n\nВы можете повторить попытку."
        }
    }
    
    # Шаблоны для отзывов
    REVIEW_TEMPLATES = {
        NotificationType.REVIEW_RECEIVED: {
            "title": "Получен новый отзыв",
            "plain": "Новый отзыв о $target_type '$target_name'.\n\nОценка: $rating из 5\nАвтор: $reviewer_name\n\nПерейдите в систему для просмотра.",
            "html": """<h2>Получен новый отзыв ⭐</h2>
<p>Новый отзыв о <strong>$target_type</strong> <strong>'$target_name'</strong>.</p>
<p><strong>Оценка:</strong> $rating из 5<br>
<strong>Автор:</strong> $reviewer_name</p>
<p>Перейдите в систему для просмотра.</p>"""
        },
        NotificationType.REVIEW_MODERATED: {
            "title": "Отзыв прошел модерацию",
            "plain": "Ваш отзыв прошел модерацию.\n\nСтатус: $moderation_status\nКомментарий модератора: $moderator_comment",
            "html": """<h2>Отзыв прошел модерацию</h2>
<p>Ваш отзыв прошел модерацию.</p>
<p><strong>Статус:</strong> $moderation_status<br>
<strong>Комментарий модератора:</strong> $moderator_comment</p>"""
        },
        NotificationType.APPEAL_SUBMITTED: {
            "title": "Подано обжалование",
            "plain": "Получено обжалование отзыва.\n\nОтзыв ID: $review_id\nАвтор обжалования: $appellant_name\nПричина: $appeal_reason",
            "html": """<h2>Подано обжалование ⚖️</h2>
<p>Получено обжалование отзыва.</p>
<p><strong>Отзыв ID:</strong> $review_id<br>
<strong>Автор обжалования:</strong> $appellant_name<br>
<strong>Причина:</strong> $appeal_reason</p>"""
        },
        NotificationType.APPEAL_DECISION: {
            "title": "Решение по обжалованию",
            "plain": "Принято решение по вашему обжалованию.\n\nРешение: $decision\nОбоснование: $decision_reason",
            "html": """<h2>Решение по обжалованию</h2>
<p>Принято решение по вашему обжалованию.</p>
<p><strong>Решение:</strong> $decision<br>
<strong>Обоснование:</strong> $decision_reason</p>"""
        }
    }
    
    # Шаблоны для платежей
    PAYMENT_TEMPLATES = {
        NotificationType.PAYMENT_DUE: {
            "title": "Предстоящий платеж",
            "plain": "Напоминание о платеже.\n\nСумма: $amount руб.\nДата: $due_date\nТариф: $tariff_name\n\nПожалуйста, пополните баланс вовремя.",
            "html": """<h2>Предстоящий платеж 💳</h2>
<p>Напоминание о платеже.</p>
<p><strong>Сумма:</strong> $amount руб.<br>
<strong>Дата:</strong> $due_date<br>
<strong>Тариф:</strong> $tariff_name</p>
<p>Пожалуйста, пополните баланс вовремя.</p>"""
        },
        NotificationType.PAYMENT_SUCCESS: {
            "title": "Платеж успешно проведен",
            "plain": "Платеж успешно проведен!\n\nСумма: $amount руб.\nДата: $payment_date\nНомер транзакции: $transaction_id\n\nСпасибо!",
            "html": """<h2>Платеж успешно проведен ✅</h2>
<p>Платеж успешно проведен!</p>
<p><strong>Сумма:</strong> $amount руб.<br>
<strong>Дата:</strong> $payment_date<br>
<strong>Номер транзакции:</strong> $transaction_id</p>
<p>Спасибо!</p>"""
        },
        NotificationType.PAYMENT_FAILED: {
            "title": "Ошибка платежа",
            "plain": "Не удалось провести платеж.\n\nСумма: $amount руб.\nПричина: $error_reason\n\nПожалуйста, проверьте платежные данные и попробуйте снова.",
            "html": """<h2>Ошибка платежа ❌</h2>
<p>Не удалось провести платеж.</p>
<p><strong>Сумма:</strong> $amount руб.<br>
<strong>Причина:</strong> $error_reason</p>
<p>Пожалуйста, проверьте платежные данные и попробуйте снова.</p>"""
        },
        NotificationType.SUBSCRIPTION_EXPIRING: {
            "title": "Подписка истекает",
            "plain": "Ваша подписка '$tariff_name' истекает через $days_left дней.\n\nДата окончания: $expiry_date\n\nПродлите подписку, чтобы не потерять доступ к функциям.",
            "html": """<h2>Подписка истекает ⚠️</h2>
<p>Ваша подписка <strong>'$tariff_name'</strong> истекает через <strong>$days_left дней</strong>.</p>
<p><strong>Дата окончания:</strong> $expiry_date</p>
<p>Продлите подписку, чтобы не потерять доступ к функциям.</p>"""
        },
        NotificationType.SUBSCRIPTION_EXPIRED: {
            "title": "Подписка истекла",
            "plain": "Ваша подписка '$tariff_name' истекла.\n\nНекоторые функции теперь недоступны.\nПродлите подписку для полного доступа.",
            "html": """<h2>Подписка истекла ⏰</h2>
<p>Ваша подписка <strong>'$tariff_name'</strong> истекла.</p>
<p>Некоторые функции теперь недоступны.</p>
<p>Продлите подписку для полного доступа.</p>"""
        },
        NotificationType.USAGE_LIMIT_WARNING: {
            "title": "Предупреждение о лимите",
            "plain": "Вы используете $usage_percent% от лимита '$limit_type'.\n\nИспользовано: $used/$total\n\nРассмотрите возможность upgrade тарифа.",
            "html": """<h2>Предупреждение о лимите ⚠️</h2>
<p>Вы используете <strong>$usage_percent%</strong> от лимита <strong>'$limit_type'</strong>.</p>
<p><strong>Использовано:</strong> $used/$total</p>
<p>Рассмотрите возможность upgrade тарифа.</p>"""
        },
        NotificationType.USAGE_LIMIT_EXCEEDED: {
            "title": "Лимит превышен",
            "plain": "Лимит '$limit_type' превышен!\n\nИспользовано: $used/$total\n\nНекоторые функции могут быть ограничены. Обновите тариф.",
            "html": """<h2>Лимит превышен 🚫</h2>
<p>Лимит <strong>'$limit_type'</strong> превышен!</p>
<p><strong>Использовано:</strong> $used/$total</p>
<p>Некоторые функции могут быть ограничены. Обновите тариф.</p>"""
        }
    }
    
    # Системные шаблоны
    SYSTEM_TEMPLATES = {
        NotificationType.WELCOME: {
            "title": "Добро пожаловать в StaffProBot!",
            "plain": "Здравствуйте, $user_name!\n\nДобро пожаловать в StaffProBot - систему управления сменами и сотрудниками.\n\nВы зарегистрированы как: $user_role\n\nНачните работу с системой прямо сейчас!",
            "html": """<h2>Добро пожаловать в StaffProBot! 🎉</h2>
<p>Здравствуйте, <strong>$user_name</strong>!</p>
<p>Добро пожаловать в <strong>StaffProBot</strong> - систему управления сменами и сотрудниками.</p>
<p><strong>Вы зарегистрированы как:</strong> $user_role</p>
<p>Начните работу с системой прямо сейчас!</p>"""
        },
        NotificationType.PASSWORD_RESET: {
            "title": "Сброс пароля",
            "plain": "Получен запрос на сброс пароля для вашего аккаунта.\n\nКод подтверждения: $reset_code\n\nЕсли это были не вы, проигнорируйте это сообщение.",
            "html": """<h2>Сброс пароля 🔐</h2>
<p>Получен запрос на сброс пароля для вашего аккаунта.</p>
<p><strong>Код подтверждения:</strong> <code>$reset_code</code></p>
<p>Если это были не вы, проигнорируйте это сообщение.</p>"""
        },
        NotificationType.ACCOUNT_SUSPENDED: {
            "title": "Аккаунт заблокирован",
            "plain": "Ваш аккаунт был временно заблокирован.\n\nПричина: $suspension_reason\nСвяжитесь с поддержкой для разблокировки.",
            "html": """<h2>Аккаунт заблокирован ⛔</h2>
<p>Ваш аккаунт был временно заблокирован.</p>
<p><strong>Причина:</strong> $suspension_reason</p>
<p>Свяжитесь с поддержкой для разблокировки.</p>"""
        },
        NotificationType.ACCOUNT_ACTIVATED: {
            "title": "Аккаунт активирован",
            "plain": "Ваш аккаунт успешно активирован!\n\nТеперь вы можете пользоваться всеми функциями системы.",
            "html": """<h2>Аккаунт активирован ✅</h2>
<p>Ваш аккаунт успешно активирован!</p>
<p>Теперь вы можете пользоваться всеми функциями системы.</p>"""
        },
        NotificationType.SYSTEM_MAINTENANCE: {
            "title": "Техническое обслуживание",
            "plain": "Запланировано техническое обслуживание системы.\n\nДата: $maintenance_date\nПродолжительность: $maintenance_duration\n\nВ это время доступ к системе будет ограничен.",
            "html": """<h2>Техническое обслуживание 🔧</h2>
<p>Запланировано техническое обслуживание системы.</p>
<p><strong>Дата:</strong> $maintenance_date<br>
<strong>Продолжительность:</strong> $maintenance_duration</p>
<p>В это время доступ к системе будет ограничен.</p>"""
        },
        NotificationType.FEATURE_ANNOUNCEMENT: {
            "title": "Новая функция!",
            "plain": "В StaffProBot появилась новая функция!\n\n$feature_name:\n$feature_description\n\nОпробуйте прямо сейчас!",
            "html": """<h2>Новая функция! 🎉</h2>
<p>В StaffProBot появилась новая функция!</p>
<p><strong>$feature_name:</strong></p>
<p>$feature_description</p>
<p>Опробуйте прямо сейчас!</p>"""
        }
    }
    
    # Шаблоны для объектов
    OBJECT_TEMPLATES = {
        NotificationType.OBJECT_OPENED: {
            "title": "Объект открылся",
            "plain": "Объект '$object_name' открылся вовремя.\n\nВремя открытия: $open_time\nСотрудник: $employee_name",
            "html": """<h2>Объект открылся ✅</h2>
<p>Объект <strong>'$object_name'</strong> открылся вовремя.</p>
<p><strong>Время открытия:</strong> $open_time<br>
<strong>Сотрудник:</strong> $employee_name</p>""",
            "telegram": "✅ *Объект открылся*\n\n📍 $object_name\n⏰ Время: $open_time\n👤 Сотрудник: $employee_name\n\n🔗 $link_url"
        },
        NotificationType.OBJECT_CLOSED: {
            "title": "Объект закрылся",
            "plain": "Объект '$object_name' закрылся.\n\nВремя закрытия: $close_time\nСотрудник: $employee_name",
            "html": """<h2>Объект закрылся 🔒</h2>
<p>Объект <strong>'$object_name'</strong> закрылся.</p>
<p><strong>Время закрытия:</strong> $close_time<br>
<strong>Сотрудник:</strong> $employee_name</p>""",
            "telegram": "🔒 *Объект закрылся*\n\n📍 $object_name\n⏰ Время: $close_time\n👤 Сотрудник: $employee_name\n\n🔗 $link_url"
        },
        NotificationType.OBJECT_LATE_OPENING: {
            "title": "Объект открылся с опозданием",
            "plain": "⚠️ ВНИМАНИЕ!\n\nОбъект '$object_name' открылся с опозданием $delay_minutes мин.\n\nПлановое время: $planned_time\nФактическое время: $actual_time\nСотрудник: $employee_name",
            "html": """<h2>Объект открылся с опозданием ⚠️</h2>
<p><strong>ВНИМАНИЕ!</strong></p>
<p>Объект <strong>'$object_name'</strong> открылся с опозданием <strong>$delay_minutes мин</strong>.</p>
<p><strong>Плановое время:</strong> $planned_time<br>
<strong>Фактическое время:</strong> $actual_time<br>
<strong>Сотрудник:</strong> $employee_name</p>""",
            "telegram": "⚠️ *ОПОЗДАНИЕ!*\n\n📍 $object_name\n⏱ Опоздание: *$delay_minutes мин*\n\n📅 Плановое время: $planned_time\n⏰ Фактическое: $actual_time\n👤 Сотрудник: $employee_name\n\n🔗 $link_url"
        },
        NotificationType.OBJECT_NO_SHIFTS_TODAY: {
            "title": "Нет смен на объекте",
            "plain": "⚠️ ВНИМАНИЕ!\n\nНа объекте '$object_name' нет запланированных смен на сегодня.\n\nДата: $date\nАдрес: $object_address",
            "html": """<h2>Нет смен на объекте ⚠️</h2>
<p><strong>ВНИМАНИЕ!</strong></p>
<p>На объекте <strong>'$object_name'</strong> нет запланированных смен на сегодня.</p>
<p><strong>Дата:</strong> $date<br>
<strong>Адрес:</strong> $object_address</p>""",
            "telegram": "⚠️ *НЕТ СМЕН!*\n\n📍 $object_name\n📅 Дата: $date\n📌 $object_address\n\nНет запланированных смен на сегодня!\n\n🔗 $link_url"
        },
        NotificationType.OBJECT_EARLY_CLOSING: {
            "title": "Объект закрылся раньше",
            "plain": "⚠️ ВНИМАНИЕ!\n\nОбъект '$object_name' закрылся раньше на $early_minutes мин.\n\nПлановое время: $planned_time\nФактическое время: $actual_time\nСотрудник: $employee_name",
            "html": """<h2>Объект закрылся раньше ⚠️</h2>
<p><strong>ВНИМАНИЕ!</strong></p>
<p>Объект <strong>'$object_name'</strong> закрылся раньше на <strong>$early_minutes мин</strong>.</p>
<p><strong>Плановое время:</strong> $planned_time<br>
<strong>Фактическое время:</strong> $actual_time<br>
<strong>Сотрудник:</strong> $employee_name</p>""",
            "telegram": "⚠️ *РАННЕЕ ЗАКРЫТИЕ!*\n\n📍 $object_name\n⏱ Раньше на: *$early_minutes мин*\n\n📅 Плановое время: $planned_time\n⏰ Фактическое: $actual_time\n👤 Сотрудник: $employee_name\n\n🔗 $link_url"
        }
    }
    
    # Шаблоны для инцидентов
    INCIDENT_TEMPLATES = {
        NotificationType.INCIDENT_CREATED: {
            "title": "Инцидент создан",
            "plain": "Создан новый инцидент #$incident_number.\n\nКатегория: $category\nКритичность: $severity\nОбъект: $object_name\nСотрудник: $employee_name\nДата: $incident_date",
            "html": """<h2>Инцидент создан ⚠️</h2>
<p>Создан новый инцидент <strong>#$incident_number</strong>.</p>
<p><strong>Категория:</strong> $category<br>
<strong>Критичность:</strong> $severity<br>
<strong>Объект:</strong> $object_name<br>
<strong>Сотрудник:</strong> $employee_name<br>
<strong>Дата:</strong> $incident_date</p>""",
            "telegram": "⚠️ *Инцидент создан*\n\n📋 Инцидент #$incident_number\n\n📂 Категория: $category\n🔴 Критичность: $severity\n📍 Объект: $object_name\n👤 Сотрудник: $employee_name\n📅 Дата: $incident_date\n\n🔗 $link_url"
        },
        NotificationType.INCIDENT_RESOLVED: {
            "title": "Инцидент решён",
            "plain": "Инцидент #$incident_number решён.\n\nКатегория: $category\nОбъект: $object_name\nСотрудник: $employee_name\nДата решения: $resolved_date",
            "html": """<h2>Инцидент решён ✅</h2>
<p>Инцидент <strong>#$incident_number</strong> решён.</p>
<p><strong>Категория:</strong> $category<br>
<strong>Объект:</strong> $object_name<br>
<strong>Сотрудник:</strong> $employee_name<br>
<strong>Дата решения:</strong> $resolved_date</p>""",
            "telegram": "✅ *Инцидент решён*\n\n📋 Инцидент #$incident_number\n\n📂 Категория: $category\n📍 Объект: $object_name\n👤 Сотрудник: $employee_name\n📅 Дата решения: $resolved_date\n\n🔗 $link_url"
        },
        NotificationType.INCIDENT_REJECTED: {
            "title": "Инцидент отклонён",
            "plain": "Инцидент #$incident_number отклонён.\n\nКатегория: $category\nОбъект: $object_name\nСотрудник: $employee_name\nДата отклонения: $rejected_date",
            "html": """<h2>Инцидент отклонён ❌</h2>
<p>Инцидент <strong>#$incident_number</strong> отклонён.</p>
<p><strong>Категория:</strong> $category<br>
<strong>Объект:</strong> $object_name<br>
<strong>Сотрудник:</strong> $employee_name<br>
<strong>Дата отклонения:</strong> $rejected_date</p>""",
            "telegram": "❌ *Инцидент отклонён*\n\n📋 Инцидент #$incident_number\n\n📂 Категория: $category\n📍 Объект: $object_name\n👤 Сотрудник: $employee_name\n📅 Дата отклонения: $rejected_date\n\n🔗 $link_url"
        },
        NotificationType.INCIDENT_CANCELLED: {
            "title": "Инцидент отменён",
            "plain": "Инцидент #$incident_number отменён.\n\nПричина отмены: $cancellation_reason\nКатегория: $category\nОбъект: $object_name\nСотрудник: $employee_name\nДата отмены: $cancelled_date",
            "html": """<h2>Инцидент отменён 🚫</h2>
<p>Инцидент <strong>#$incident_number</strong> отменён.</p>
<p><strong>Причина отмены:</strong> $cancellation_reason<br>
<strong>Категория:</strong> $category<br>
<strong>Объект:</strong> $object_name<br>
<strong>Сотрудник:</strong> $employee_name<br>
<strong>Дата отмены:</strong> $cancelled_date</p>""",
            "telegram": "🚫 *Инцидент отменён*\n\n📋 Инцидент #$incident_number\n\n📝 Причина: $cancellation_reason\n📂 Категория: $category\n📍 Объект: $object_name\n👤 Сотрудник: $employee_name\n📅 Дата отмены: $cancelled_date\n\n🔗 $link_url"
        }
    }
    
    # Объединяем все шаблоны
    ALL_TEMPLATES = {
        **SHIFT_TEMPLATES,
        **CONTRACT_TEMPLATES,
        **OFFER_TEMPLATES,
        **KYC_TEMPLATES,
        **REVIEW_TEMPLATES,
        **PAYMENT_TEMPLATES,
        **SYSTEM_TEMPLATES,
        **OBJECT_TEMPLATES,
        **INCIDENT_TEMPLATES
    }
    
    @classmethod
    def render(
        cls,
        notification_type: NotificationType,
        channel: NotificationChannel,
        variables: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Рендеринг шаблона уведомления.
        
        Args:
            notification_type: Тип уведомления
            channel: Канал доставки
            variables: Переменные для подстановки
            
        Returns:
            Словарь с title, message (plain или html в зависимости от канала)
        """
        try:
            # Получаем шаблон
            template_data = cls.ALL_TEMPLATES.get(notification_type)
            
            if not template_data:
                logger.warning(f"Template not found for {notification_type.value}")
                return {
                    "title": "Уведомление",
                    "message": "Содержимое уведомления недоступно."
                }
            
            # Определяем формат в зависимости от канала
            if channel in (NotificationChannel.TELEGRAM, NotificationChannel.MAX):
                message_template = template_data.get("telegram", template_data.get("plain", ""))
            elif channel in [NotificationChannel.EMAIL, NotificationChannel.IN_APP]:
                message_template = template_data.get("html", template_data.get("plain", ""))
            else:
                message_template = template_data.get("plain", "")
            
            # Рендерим с подстановкой переменных
            title = Template(template_data["title"]).safe_substitute(variables)
            message = Template(message_template).safe_substitute(variables)
            
            return {
                "title": title,
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Error rendering template: {e}", notification_type=notification_type.value, error=str(e))
            return {
                "title": "Уведомление",
                "message": "Ошибка при формировании сообщения."
            }
    
    @classmethod
    def get_template_variables(cls, notification_type: NotificationType) -> list[str]:
        """
        Получение списка переменных для шаблона.
        
        Args:
            notification_type: Тип уведомления
            
        Returns:
            Список имен переменных
        """
        import re
        
        template_data = cls.ALL_TEMPLATES.get(notification_type)
        if not template_data:
            return []
        
        # Извлекаем все переменные из шаблона
        plain_text = template_data.get("plain", "")
        variables = set(re.findall(r'\$(\w+)', plain_text))
        
        return sorted(list(variables))
    
    @classmethod
    def validate_variables(
        cls,
        notification_type: NotificationType,
        variables: Dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """
        Валидация предоставленных переменных.
        
        Args:
            notification_type: Тип уведомления
            variables: Предоставленные переменные
            
        Returns:
            Кортеж (valid, missing_variables)
        """
        required = cls.get_template_variables(notification_type)
        provided = set(variables.keys())
        missing = [var for var in required if var not in provided]
        
        return (len(missing) == 0, missing)

