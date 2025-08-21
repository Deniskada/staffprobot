"""
Главный API роутер StaffProBot
"""
from fastapi import APIRouter

from apps.api.routers.objects import router as objects_router

# Создаем главный роутер
api_router = APIRouter(prefix="/api/v1")

# Подключаем роутеры
api_router.include_router(objects_router)

# В будущем здесь будут подключены другие роутеры:
# api_router.include_router(users_router)
# api_router.include_router(shifts_router)
# api_router.include_router(schedules_router)

