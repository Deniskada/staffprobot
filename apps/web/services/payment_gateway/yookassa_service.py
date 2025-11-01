"""Сервис для работы с YooKassa."""

from typing import Dict, Any, Optional
import hashlib
import hmac
from yookassa import Configuration, Payment
from yookassa.domain.notification import WebhookNotificationFactory

from core.config.settings import settings
from core.logging.logger import logger


class YooKassaService:
    """Сервис для работы с YooKassa API."""
    
    def __init__(self):
        """Инициализация сервиса YooKassa."""
        # Настройка YooKassa SDK
        if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
            logger.warning("YooKassa credentials not configured - payments will fail")
            self.is_configured = False
        else:
            Configuration.account_id = settings.yookassa_shop_id
            Configuration.secret_key = settings.yookassa_secret_key
            self.is_configured = True
    
    async def create_payment(
        self,
        amount: float,
        currency: str,
        description: str,
        return_url: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Создание платежа через YooKassa API.
        
        Args:
            amount: Сумма платежа
            currency: Валюта (RUB)
            description: Описание платежа
            return_url: URL для возврата после оплаты
            metadata: Дополнительные данные (transaction_id, user_id, etc.)
            
        Returns:
            dict с данными платежа: id, status, confirmation_url
        """
        if not self.is_configured:
            raise ValueError("YooKassa credentials not configured. Set YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY")
        
        try:
            # Конвертируем сумму в копейки для YooKassa
            amount_value = {
                "value": f"{amount:.2f}",
                "currency": currency
            }
            
            # Создаем объект платежа
            payment_data = {
                "amount": amount_value,
                "description": description,
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url
                },
                "capture": True,
                "metadata": metadata or {}
            }
            
            # Создаем платеж
            payment = Payment.create(payment_data)
            
            # Логируем для отладки
            logger.info(
                f"Created YooKassa payment",
                payment_id=payment.id,
                amount=amount,
                currency=currency,
                metadata=metadata,
                payment_created_at_type=str(type(payment.created_at)) if hasattr(payment, 'created_at') else 'no created_at',
                payment_confirmation_type=str(type(payment.confirmation)) if hasattr(payment, 'confirmation') else 'no confirmation'
            )
            
            # Обрабатываем created_at безопасно
            created_at_str = None
            if payment.created_at:
                if hasattr(payment.created_at, 'isoformat'):
                    created_at_str = payment.created_at.isoformat()
                elif isinstance(payment.created_at, str):
                    created_at_str = payment.created_at
                else:
                    created_at_str = str(payment.created_at)
            
            # Обрабатываем confirmation_url безопасно
            confirmation_url = None
            if hasattr(payment, 'confirmation') and payment.confirmation:
                if hasattr(payment.confirmation, 'confirmation_url'):
                    confirmation_url = payment.confirmation.confirmation_url
                elif isinstance(payment.confirmation, dict):
                    confirmation_url = payment.confirmation.get('confirmation_url')
            
            # Обрабатываем amount безопасно (может быть Decimal, dict, или объект)
            amount_value = None
            if hasattr(payment, 'amount'):
                if hasattr(payment.amount, 'value'):
                    # Объект Amount с полем value
                    amount_value = float(payment.amount.value) if hasattr(payment.amount.value, '__float__') else str(payment.amount.value)
                elif isinstance(payment.amount, dict):
                    # Словарь с ключом 'value'
                    amount_value = payment.amount.get('value')
                    if isinstance(amount_value, (int, float)):
                        amount_value = float(amount_value)
                    else:
                        amount_value = str(amount_value)
                elif isinstance(payment.amount, (int, float)):
                    amount_value = float(payment.amount)
                else:
                    # Decimal или другой тип - конвертируем в float или str
                    try:
                        amount_value = float(payment.amount)
                    except (ValueError, TypeError):
                        amount_value = str(payment.amount)
            
            return {
                "id": payment.id,
                "status": payment.status,
                "confirmation_url": confirmation_url,
                "amount": amount_value,
                "created_at": created_at_str
            }
            
        except Exception as e:
            logger.error(
                f"Error creating YooKassa payment: {e}",
                error=str(e),
                amount=amount,
                currency=currency
            )
            raise
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Получение статуса платежа.
        
        Args:
            payment_id: ID платежа в YooKassa
            
        Returns:
            dict с данными платежа
        """
        try:
            payment = Payment.find_one(payment_id)
            
            logger.info(
                f"Retrieved YooKassa payment status",
                payment_id=payment_id,
                status=payment.status
            )
            
            # Обрабатываем даты безопасно
            created_at_str = None
            if payment.created_at:
                if hasattr(payment.created_at, 'isoformat'):
                    created_at_str = payment.created_at.isoformat()
                elif isinstance(payment.created_at, str):
                    created_at_str = payment.created_at
                else:
                    created_at_str = str(payment.created_at)
            
            captured_at_str = None
            if payment.captured_at:
                if hasattr(payment.captured_at, 'isoformat'):
                    captured_at_str = payment.captured_at.isoformat()
                elif isinstance(payment.captured_at, str):
                    captured_at_str = payment.captured_at
                else:
                    captured_at_str = str(payment.captured_at)
            
            # Обрабатываем amount безопасно (может быть Decimal, dict, или объект)
            amount_value = None
            if hasattr(payment, 'amount'):
                if hasattr(payment.amount, 'value'):
                    # Объект Amount с полем value
                    amount_value = float(payment.amount.value) if hasattr(payment.amount.value, '__float__') else str(payment.amount.value)
                elif isinstance(payment.amount, dict):
                    # Словарь с ключом 'value'
                    amount_value = payment.amount.get('value')
                    if isinstance(amount_value, (int, float)):
                        amount_value = float(amount_value)
                    else:
                        amount_value = str(amount_value)
                elif isinstance(payment.amount, (int, float)):
                    amount_value = float(payment.amount)
                else:
                    # Decimal или другой тип - конвертируем в float или str
                    try:
                        amount_value = float(payment.amount)
                    except (ValueError, TypeError):
                        amount_value = str(payment.amount)
            
            # Проверяем статус отмены безопасно
            is_cancelled = False
            if hasattr(payment, 'cancelled'):
                is_cancelled = payment.cancelled
            elif hasattr(payment, 'status'):
                is_cancelled = payment.status == "canceled"
            
            return {
                "id": payment.id,
                "status": payment.status,
                "amount": amount_value,
                "paid": payment.paid if hasattr(payment, 'paid') else False,
                "cancelled": is_cancelled,
                "created_at": created_at_str,
                "captured_at": captured_at_str
            }
            
        except Exception as e:
            logger.error(
                f"Error getting YooKassa payment status: {e}",
                error=str(e),
                payment_id=payment_id
            )
            raise
    
    def verify_webhook(self, request_body: bytes, signature: str) -> bool:
        """
        Проверка подлинности вебхука от YooKassa.
        
        Args:
            request_body: Тело запроса (bytes)
            signature: Подпись из заголовка HTTP
            
        Returns:
            True если вебхук подлинный
        """
        if not settings.yookassa_webhook_secret:
            # Если секрет не настроен, используем секретный ключ
            secret = settings.yookassa_secret_key.encode('utf-8')
        else:
            secret = settings.yookassa_webhook_secret.encode('utf-8')
        
        try:
            # Вычисляем ожидаемую подпись
            expected_signature = hmac.new(
                secret,
                request_body,
                hashlib.sha256
            ).hexdigest()
            
            # Сравниваем подписи (защита от timing attack)
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(
                f"Error verifying YooKassa webhook: {e}",
                error=str(e)
            )
            return False
    
    def parse_webhook(self, request_body: bytes) -> Optional[Dict[str, Any]]:
        """
        Парсинг вебхука от YooKassa.
        
        Args:
            request_body: Тело запроса (bytes)
            
        Returns:
            dict с данными события или None
        """
        try:
            # Декодируем JSON
            import json
            data = json.loads(request_body.decode('utf-8'))
            
            # Создаем объект уведомления через SDK
            notification = WebhookNotificationFactory().create(data)
            
            return {
                "type": notification.type,
                "event": notification.event,
                "payment_id": notification.object.id if hasattr(notification.object, 'id') else None,
                "payment_status": notification.object.status if hasattr(notification.object, 'status') else None,
                "payment_amount": notification.object.amount if hasattr(notification.object, 'amount') else None,
                "metadata": notification.object.metadata if hasattr(notification.object, 'metadata') else {}
            }
            
        except Exception as e:
            logger.error(
                f"Error parsing YooKassa webhook: {e}",
                error=str(e)
            )
            return None

