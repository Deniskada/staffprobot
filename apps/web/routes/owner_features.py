"""
Роуты для управления функциями в профиле владельца.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from apps.web.middleware.role_middleware import get_user_id_from_current_user
from core.database.session import get_db_session
from shared.services.system_features_service import SystemFeaturesService
from core.logging.logger import logger

router = APIRouter()


@router.get("/api/status")
async def get_features_status(
    current_user: dict = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Получить статус всех функций для пользователя."""
    try:
        user_id = await get_user_id_from_current_user(current_user, session)
        
        service = SystemFeaturesService()
        features_status = await service.get_user_features_status(session, user_id)
        
        # Формируем удобный формат для frontend
        features_list = []
        for key, status in features_status.items():
            feature_info = status['info'].to_dict()
            feature_info['available'] = status['available']
            feature_info['enabled'] = status['enabled']
            features_list.append(feature_info)
        
        # Сортируем по sort_order
        features_list.sort(key=lambda x: x['sort_order'])
        
        return JSONResponse({
            "success": True,
            "features": features_list
        })
    except Exception as e:
        logger.error(f"Error getting features status: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/api/toggle")
async def toggle_feature(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Включить/выключить функцию."""
    try:
        # Получаем JSON данные
        data = await request.json()
        feature_key = data.get('feature_key')
        enabled = data.get('enabled')
        
        if not feature_key or enabled is None:
            return JSONResponse({
                "success": False,
                "error": "Не указаны обязательные параметры"
            }, status_code=400)
        
        user_id = await get_user_id_from_current_user(current_user, session)
        
        service = SystemFeaturesService()
        success = await service.toggle_user_feature(session, user_id, feature_key, enabled)
        
        if not success:
            return JSONResponse({
                "success": False,
                "error": "Функция недоступна в вашем тарифном плане"
            }, status_code=403)
        
        # Хуки при включении/отключении функций
        if feature_key == 'rules_engine':
            await _handle_rules_engine_toggle(session, user_id, enabled)
        
        # Автоотключение зависимых фич при отключении родительской
        disabled_features = []
        if not enabled:
            disabled_features = await _disable_dependent_features(session, user_id, feature_key, service)
        
        return JSONResponse({
            "success": True,
            "disabled_dependent_features": disabled_features  # Список автоотключённых фич
        })
    except Exception as e:
        logger.error(f"Error toggling feature: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)



async def _handle_rules_engine_toggle(session: AsyncSession, user_id: int, enabled: bool) -> None:
    """Обработка включения/отключения Rules Engine."""
    from domain.entities.rule import Rule
    from sqlalchemy import select, update
    import json
    
    try:
        if enabled:
            # При ВКЛЮЧЕНИИ: проверяем, есть ли правила, если нет — создаём
            existing_query = select(Rule).where(Rule.owner_id == user_id)
            existing_result = await session.execute(existing_query)
            
            if not existing_result.scalars().first():
                # Создаём стартовые правила
                logger.info(f"Auto-creating rules for owner {user_id} on enable")
                
                rules = [
                    Rule(
                        owner_id=user_id,
                        code="late_default",
                        name="Штраф за опоздание на смену (по умолчанию)",
                        scope="late",
                        priority=100,
                        is_active=True,
                        condition_json=json.dumps({
                            "description": "Применяется при опоздании на смену. Порог опоздания настраивается в подразделениях/объектах (каскадное наследование настроек)."
                        }),
                        action_json=json.dumps({
                            "type": "fine",
                            "amount": 50,
                            "label": "Штраф за опоздание (по умолчанию)",
                            "code": "late_default"
                        })
                    ),
                    Rule(
                        owner_id=user_id,
                        code="cancel_short_notice",
                        name="Штраф за отмену смены в короткий срок",
                        scope="cancellation",
                        priority=100,
                        is_active=True,
                        condition_json=json.dumps({
                            "description": "Применяется при отмене смены в короткий срок. Минимальный срок уведомления настраивается в подразделениях/объектах (каскадное наследование)."
                        }),
                        action_json=json.dumps({
                            "type": "fine",
                            "amount": 500,
                            "fine_code": "short_notice",
                            "label": "Штраф за отмену в короткий срок",
                            "code": "cancel_short_notice"
                        })
                    ),
                    Rule(
                        owner_id=user_id,
                        code="cancel_invalid_reason",
                        name="Штраф за неуважительную причину отмены смены",
                        scope="cancellation",
                        priority=200,
                        is_active=True,
                        condition_json=json.dumps({
                            "description": "Применяется, когда причина отмены не входит в список уважительных. Список уважительных причин настраивается в разделе 'Причины отмен' → позволяет отличать форс-мажор от простого 'не хочу'."
                        }),
                        action_json=json.dumps({
                            "type": "fine",
                            "amount": 1000,
                            "fine_code": "invalid_reason",
                            "label": "Штраф за неуважительную причину",
                            "code": "cancel_invalid_reason"
                        })
                    )
                ]
                
                for rule in rules:
                    session.add(rule)
                
                await session.commit()
                logger.info(f"Created {len(rules)} default rules for owner {user_id}")
            else:
                # Правила уже есть — делаем их активными
                await session.execute(
                    update(Rule).where(Rule.owner_id == user_id).values(is_active=True)
                )
                await session.commit()
                logger.info(f"Activated existing rules for owner {user_id}")
        else:
            # При ОТКЛЮЧЕНИИ: деактивируем все правила владельца
            await session.execute(
                update(Rule).where(Rule.owner_id == user_id).values(is_active=False)
            )
            await session.commit()
            logger.info(f"Deactivated all rules for owner {user_id}")
    
    except Exception as e:
        logger.error(f"Error handling rules_engine toggle: {e}", exc_info=True)
        await session.rollback()
        raise


async def _disable_dependent_features(session: AsyncSession, user_id: int, parent_key: str, service) -> list:
    """Отключение зависимых фич при отключении родительской.
    
    Returns:
        Список автоматически отключённых ключей фич
    """
    from core.config.features import SYSTEM_FEATURES_REGISTRY
    
    disabled = []
    try:
        # Находим все фичи, зависящие от parent_key
        for key, feature_def in SYSTEM_FEATURES_REGISTRY.items():
            depends_on = feature_def.get('depends_on', [])
            if parent_key in depends_on:
                logger.info(f"Auto-disabling dependent feature {key} (parent {parent_key} disabled)")
                await service.toggle_user_feature(session, user_id, key, False)
                disabled.append(key)
    
    except Exception as e:
        logger.error(f"Error disabling dependent features: {e}", exc_info=True)
    
    return disabled
