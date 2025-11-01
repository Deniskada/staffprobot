"""Роуты для обработки вебхуков от внешних сервисов."""

from fastapi import APIRouter, Request, HTTPException, Header, status
from fastapi.responses import Response
from typing import Optional
import json
from decimal import Decimal
from datetime import datetime, date


def json_serializer(obj):
    """Кастомный сериализатор для JSON, обрабатывает Decimal, datetime и другие типы."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        # Объект с атрибутами - конвертируем в словарь
        return obj.__dict__
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

from core.database.session import get_async_session
from apps.web.services.billing_service import BillingService
from apps.web.services.payment_gateway.yookassa_service import YooKassaService
from domain.entities.billing_transaction import TransactionStatus
from core.logging.logger import logger

router = APIRouter()


@router.post("/yookassa", name="yookassa_webhook")
async def yookassa_webhook(
    request: Request,
    x_shop_id: Optional[str] = Header(None),
    x_shop_secret: Optional[str] = Header(None)
):
    """
    Обработка вебхуков от YooKassa.
    
    YooKassa отправляет вебхуки для следующих событий:
    - payment.succeeded - успешная оплата
    - payment.canceled - отменённая оплата
    - payment.waiting_for_capture - ожидание подтверждения
    - refund.succeeded - успешный возврат
    """
    try:
        # Получаем тело запроса
        body = await request.body()
        
        # Проверяем подлинность вебхука (если настроен секрет)
        yookassa_service = YooKassaService()
        
        # YooKassa может отправлять подпись в заголовках или использовать свой механизм
        # Пока что полагаемся на проверку подлинности через SDK
        signature = x_shop_secret or request.headers.get("x-shop-secret")
        
        # Парсим событие
        event_data = yookassa_service.parse_webhook(body)
        
        if not event_data:
            logger.error("Failed to parse YooKassa webhook")
            # Возвращаем 200 OK, чтобы YooKassa не отправляла повторно
            return Response(status_code=200)
        
        event_type = event_data.get("type")
        payment_id = event_data.get("payment_id")
        payment_status = event_data.get("payment_status")
        metadata = event_data.get("metadata", {})
        
        logger.info(
            f"Received YooKassa webhook",
            event_type=event_type,
            payment_id=payment_id,
            payment_status=payment_status,
            metadata=metadata
        )
        
        # Получаем transaction_id из metadata
        transaction_id = metadata.get("transaction_id")
        
        if not transaction_id:
            logger.error(f"No transaction_id in YooKassa webhook metadata: {metadata}")
            return Response(status_code=200)
        
        transaction_id = int(transaction_id)
        
        # Обрабатываем событие
        async with get_async_session() as session:
            billing_service = BillingService(session)
            
            if event_type == "notification" and payment_status == "succeeded":
                # Успешная оплата
                logger.info(
                    f"Processing successful payment",
                    transaction_id=transaction_id,
                    payment_id=payment_id
                )
                
                # Проверяем, что транзакция еще не обработана (защита от дубликатов)
                from sqlalchemy import select
                from domain.entities.billing_transaction import BillingTransaction
                
                transaction_result = await session.execute(
                    select(BillingTransaction).where(BillingTransaction.id == transaction_id)
                )
                transaction = transaction_result.scalar_one_or_none()
                
                if not transaction:
                    logger.error(f"Transaction {transaction_id} not found")
                    return Response(status_code=200)
                
                # Если транзакция уже обработана, игнорируем вебхук
                if transaction.status == TransactionStatus.COMPLETED:
                    logger.info(
                        f"Transaction {transaction_id} already processed, ignoring webhook",
                        transaction_id=transaction_id
                    )
                    return Response(status_code=200)
                
                # Обрабатываем успешную оплату
                await billing_service.process_payment_success(transaction_id, payment_id)
                
            elif event_type == "notification" and payment_status == "canceled":
                # Отменённая оплата
                logger.info(
                    f"Processing canceled payment",
                    transaction_id=transaction_id,
                    payment_id=payment_id
                )
                
                await billing_service.update_transaction_status(
                    transaction_id,
                    TransactionStatus.CANCELLED,
                    gateway_response=json.dumps(event_data, default=json_serializer)
                )
                
            elif event_type == "notification" and payment_status == "waiting_for_capture":
                # Ожидание подтверждения (для двухстадийных платежей)
                logger.info(
                    f"Payment waiting for capture",
                    transaction_id=transaction_id,
                    payment_id=payment_id
                )
                
                # Для одностадийных платежей это не должно происходить
                # Но на всякий случай логируем
                
            elif event_type == "notification" and payment_status == "refund.succeeded":
                # Успешный возврат
                logger.info(
                    f"Processing refund",
                    transaction_id=transaction_id,
                    payment_id=payment_id
                )
                
                # TODO: Создать транзакцию типа REFUND
                # Пока что просто логируем
                
            else:
                logger.warning(
                    f"Unknown YooKassa event type or status",
                    event_type=event_type,
                    payment_status=payment_status
                )
        
        # Возвращаем 200 OK (YooKassa требует успешный ответ)
        return Response(status_code=200)
        
    except Exception as e:
        logger.error(
            f"Error processing YooKassa webhook: {e}",
            error=str(e),
            exc_info=True
        )
        # Возвращаем 200 OK даже при ошибках, чтобы YooKassa не отправляла повторно
        # Но логируем ошибку для отладки
        return Response(status_code=200)

