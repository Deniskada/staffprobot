#!/usr/bin/env python3
"""
API сервер StaffProBot с поддержкой реальной базы данных
"""
import json
import time
import sys
import os
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Добавляем корневую папку в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Простые настройки по умолчанию
class DefaultSettings:
    app_name = "StaffProBot"
    version = "1.0.0"
    api_host = "0.0.0.0"
    api_port = 8000
    database_url = "postgresql://postgres:password@localhost:5432/staffprobot"
    debug = True

settings = DefaultSettings()

# Простой логгер
class SimpleLogger:
    def info(self, msg, **kwargs):
        print(f"INFO: {msg}")
    def error(self, msg, **kwargs):
        print(f"ERROR: {msg}")

logger = SimpleLogger()

# Проверяем доступность базы данных
try:
    from core.database.session import db_manager, get_db_session
    from apps.api.services.object_service_db import ObjectServiceDB
    from apps.api.services.user_service_db import UserServiceDB
    from apps.api.services.shift_service_db import ShiftServiceDB
    print("✅ Все модули загружены успешно")
    DB_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Ошибка импорта: {e}")
    print("Используем независимые сервисы")
    
    # Импортируем независимые сервисы
    from api_services_standalone import user_service, object_service, shift_service
    DB_AVAILABLE = False
    db_manager = None
    get_db_session = None


class RealDatabaseAPIHandler(BaseHTTPRequestHandler):
    """HTTP обработчик для API с реальной базой данных."""
    
    def log_message(self, format, *args):
        """Переопределяем логирование."""
        logger.info(f"HTTP {format}")
    
    def _set_headers(self, status_code: int = 200, content_type: str = "application/json"):
        """Устанавливаем заголовки ответа."""
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, PATCH, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def _send_json_response(self, data: dict, status_code: int = 200):
        """Отправляем JSON ответ."""
        self._set_headers(status_code)
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode('utf-8'))
    
    def _send_error_response(self, error: str, message: str, status_code: int = 400):
        """Отправляем ответ с ошибкой."""
        self._send_json_response({
            "error": error,
            "message": message,
            "status_code": status_code
        }, status_code)
    
    def do_OPTIONS(self):
        """Обработка preflight запросов CORS."""
        self._set_headers()
    
    def do_GET(self):
        """Обработка GET запросов."""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            if path == "/":
                # Корневой эндпоинт
                self._send_json_response({
                    "app": settings.app_name,
                    "version": settings.version,
                    "status": "running",
                    "database": "connected" if DB_AVAILABLE else "disconnected",
                    "docs": "disabled"
                })
                
            elif path == "/health":
                # Health check
                self._send_json_response({
                    "status": "healthy",
                    "timestamp": time.time(),
                    "version": settings.version,
                    "database": "connected" if DB_AVAILABLE else "disconnected"
                })
                
            elif path == "/api/v1/objects":
                # Список объектов
                if DB_AVAILABLE:
                    asyncio.run(self._handle_get_objects(query_params))
                else:
                    self._send_json_response({
                        "objects": [],
                        "count": 0,
                        "message": "Database not available"
                    })
                
            elif path.startswith("/api/v1/objects/") and path.count("/") == 4:
                # Получение объекта по ID
                if DB_AVAILABLE:
                    object_id = int(path.split("/")[-1])
                    asyncio.run(self._handle_get_object(object_id))
                else:
                    self._send_error_response("service_unavailable", "Database not available", 503)
                
            elif path == "/api/v1/users":
                # Список пользователей
                if DB_AVAILABLE:
                    asyncio.run(self._handle_get_users(query_params))
                else:
                    self._send_json_response({
                        "users": [],
                        "count": 0,
                        "message": "Database not available"
                    })
                
            elif path.startswith("/api/v1/users/") and path.count("/") == 4:
                # Получение пользователя по ID
                if DB_AVAILABLE:
                    user_id = int(path.split("/")[-1])
                    asyncio.run(self._handle_get_user(user_id))
                else:
                    self._send_error_response("service_unavailable", "Database not available", 503)
                
            elif path == "/api/v1/shifts":
                # Список смен
                if DB_AVAILABLE:
                    asyncio.run(self._handle_get_shifts(query_params))
                else:
                    self._send_json_response({
                        "shifts": [],
                        "count": 0,
                        "message": "Database not available"
                    })
                
            else:
                self._send_error_response("not_found", "Endpoint not found", 404)
                
        except Exception as e:
            logger.error(f"Error in GET request: {e}")
            self._send_error_response("internal_error", str(e), 500)
    
    def do_POST(self):
        """Обработка POST запросов."""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            
            if path == "/api/v1/objects":
                # Создание объекта
                if DB_AVAILABLE:
                    asyncio.run(self._handle_create_object())
                else:
                    self._send_error_response("service_unavailable", "Database not available", 503)
                
            elif path == "/api/v1/users":
                # Создание пользователя
                if DB_AVAILABLE:
                    asyncio.run(self._handle_create_user())
                else:
                    self._send_error_response("service_unavailable", "Database not available", 503)
                
            elif path == "/api/v1/shifts":
                # Создание смены
                if DB_AVAILABLE:
                    asyncio.run(self._handle_create_shift())
                else:
                    self._send_error_response("service_unavailable", "Database not available", 503)
                
            else:
                self._send_error_response("not_found", "Endpoint not found", 404)
                
        except Exception as e:
            logger.error(f"Error in POST request: {e}")
            self._send_error_response("internal_error", str(e), 500)
    
    async def _handle_get_objects(self, query_params):
        """Обработка GET /api/v1/objects"""
        try:
            async for session in get_db_session():
                service = ObjectServiceDB(session)
                
                if 'owner_id' in query_params:
                    owner_id = int(query_params['owner_id'][0])
                    objects = await service.get_objects_by_owner(owner_id)
                else:
                    objects = await service.get_all_objects()
                
                # Конвертируем в словари
                objects_data = []
                for obj in objects:
                    obj_dict = {
                        'id': obj.id,
                        'name': obj.name,
                        'owner_id': obj.owner_id,
                        'address': obj.address,
                        'coordinates': obj.coordinates,
                        'opening_time': str(obj.opening_time),
                        'closing_time': str(obj.closing_time),
                        'hourly_rate': float(obj.hourly_rate),
                        'required_employees': obj.required_employees,
                        'is_active': obj.is_active,
                        'created_at': str(obj.created_at),
                        'updated_at': str(obj.updated_at)
                    }
                    objects_data.append(obj_dict)
                
                self._send_json_response({
                    "objects": objects_data,
                    "count": len(objects_data)
                })
                
        except Exception as e:
            logger.error(f"Error getting objects: {e}")
            self._send_error_response("database_error", str(e), 500)
    
    async def _handle_get_object(self, object_id):
        """Обработка GET /api/v1/objects/{id}"""
        try:
            async for session in get_db_session():
                service = ObjectServiceDB(session)
                obj = await service.get_object(object_id)
                
                if not obj:
                    self._send_error_response("not_found", f"Object {object_id} not found", 404)
                    return
                
                obj_dict = {
                    'id': obj.id,
                    'name': obj.name,
                    'owner_id': obj.owner_id,
                    'address': obj.address,
                    'coordinates': obj.coordinates,
                    'opening_time': str(obj.opening_time),
                    'closing_time': str(obj.closing_time),
                    'hourly_rate': float(obj.hourly_rate),
                    'required_employees': obj.required_employees,
                    'is_active': obj.is_active,
                    'created_at': str(obj.created_at),
                    'updated_at': str(obj.updated_at)
                }
                
                self._send_json_response(obj_dict)
                
        except Exception as e:
            logger.error(f"Error getting object {object_id}: {e}")
            self._send_error_response("database_error", str(e), 500)
    
    async def _handle_create_object(self):
        """Обработка POST /api/v1/objects"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error_response("bad_request", "No data provided", 400)
                return
            
            post_data = self.rfile.read(content_length)
            object_data = json.loads(post_data.decode('utf-8'))
            
            async for session in get_db_session():
                service = ObjectServiceDB(session)
                new_object = await service.create_object(object_data)
                
                if not new_object:
                    self._send_error_response("creation_failed", "Failed to create object", 500)
                    return
                
                self._send_json_response({
                    "message": "Object created successfully",
                    "object_id": new_object.id
                }, 201)
                
        except json.JSONDecodeError:
            self._send_error_response("bad_request", "Invalid JSON", 400)
        except Exception as e:
            logger.error(f"Error creating object: {e}")
            self._send_error_response("internal_error", str(e), 500)
    
    async def _handle_get_users(self, query_params):
        """Обработка GET /api/v1/users"""
        try:
            async for session in get_db_session():
                service = UserServiceDB(session)
                
                if 'role' in query_params:
                    role = query_params['role'][0]
                    users = await service.get_users_by_role(role)
                else:
                    users = await service.get_all_users()
                
                # Конвертируем в словари
                users_data = []
                for user in users:
                    user_dict = {
                        'id': user.id,
                        'telegram_id': user.telegram_id,
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'phone': user.phone,
                        'role': user.role,
                        'is_active': user.is_active,
                        'created_at': str(user.created_at),
                        'updated_at': str(user.updated_at)
                    }
                    users_data.append(user_dict)
                
                self._send_json_response({
                    "users": users_data,
                    "count": len(users_data)
                })
                
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            self._send_error_response("database_error", str(e), 500)
    
    async def _handle_get_user(self, user_id):
        """Обработка GET /api/v1/users/{id}"""
        try:
            async for session in get_db_session():
                service = UserServiceDB(session)
                user = await service.get_user(user_id)
                
                if not user:
                    self._send_error_response("not_found", f"User {user_id} not found", 404)
                    return
                
                user_dict = {
                    'id': user.id,
                    'telegram_id': user.telegram_id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'phone': user.phone,
                    'role': user.role,
                    'is_active': user.is_active,
                    'created_at': str(user.created_at),
                    'updated_at': str(user.updated_at)
                }
                
                self._send_json_response(user_dict)
                
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            self._send_error_response("database_error", str(e), 500)
    
    async def _handle_create_user(self):
        """Обработка POST /api/v1/users"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error_response("bad_request", "No data provided", 400)
                return
            
            post_data = self.rfile.read(content_length)
            user_data = json.loads(post_data.decode('utf-8'))
            
            async for session in get_db_session():
                service = UserServiceDB(session)
                new_user = await service.create_user(user_data)
                
                if not new_user:
                    self._send_error_response("creation_failed", "Failed to create user", 500)
                    return
                
                self._send_json_response({
                    "message": "User created successfully",
                    "user_id": new_user.id
                }, 201)
                
        except json.JSONDecodeError:
            self._send_error_response("bad_request", "Invalid JSON", 400)
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            self._send_error_response("internal_error", str(e), 500)
    
    async def _handle_get_shifts(self, query_params):
        """Обработка GET /api/v1/shifts"""
        try:
            async for session in get_db_session():
                service = ShiftServiceDB(session)
                
                if 'user_id' in query_params:
                    user_id = int(query_params['user_id'][0])
                    shifts = await service.get_shifts_by_user(user_id)
                elif 'object_id' in query_params:
                    object_id = int(query_params['object_id'][0])
                    shifts = await service.get_shifts_by_object(object_id)
                else:
                    # Получаем смены за последние 30 дней
                    from datetime import datetime, timedelta
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=30)
                    shifts = await service.get_shifts_by_date_range(start_date, end_date)
                
                # Конвертируем в словари
                shifts_data = []
                for shift in shifts:
                    shift_dict = {
                        'id': shift.id,
                        'user_id': shift.user_id,
                        'object_id': shift.object_id,
                        'start_time': str(shift.start_time),
                        'end_time': str(shift.end_time) if shift.end_time else None,
                        'status': shift.status,
                        'start_coordinates': shift.start_coordinates,
                        'end_coordinates': shift.end_coordinates,
                        'total_hours': float(shift.total_hours) if shift.total_hours else None,
                        'hourly_rate': float(shift.hourly_rate) if shift.hourly_rate else None,
                        'total_payment': float(shift.total_payment) if shift.total_payment else None,
                        'notes': shift.notes,
                        'created_at': str(shift.created_at),
                        'updated_at': str(shift.updated_at)
                    }
                    shifts_data.append(shift_dict)
                
                self._send_json_response({
                    "shifts": shifts_data,
                    "count": len(shifts_data)
                })
                
        except Exception as e:
            logger.error(f"Error getting shifts: {e}")
            self._send_error_response("database_error", str(e), 500)
    
    async def _handle_create_shift(self):
        """Обработка POST /api/v1/shifts"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error_response("bad_request", "No data provided", 400)
                return
            
            post_data = self.rfile.read(content_length)
            shift_data = json.loads(post_data.decode('utf-8'))
            
            async for session in get_db_session():
                service = ShiftServiceDB(session)
                new_shift = await service.create_shift(shift_data)
                
                if not new_shift:
                    self._send_error_response("creation_failed", "Failed to create shift", 500)
                    return
                
                self._send_json_response({
                    "message": "Shift created successfully",
                    "shift_id": new_shift.id
                }, 201)
                
        except json.JSONDecodeError:
            self._send_error_response("bad_request", "Invalid JSON", 400)
        except Exception as e:
            logger.error(f"Error creating shift: {e}")
            self._send_error_response("internal_error", str(e), 500)


def main():
    """Главная функция."""
    try:
        if DB_AVAILABLE:
            # Инициализируем базу данных
            asyncio.run(db_manager.initialize())
            print("✅ База данных инициализирована")
        else:
            print("⚠️ База данных недоступна, работаем в режиме заглушек")
        
        # Создаем сервер
        server = HTTPServer((settings.api_host, settings.api_port), RealDatabaseAPIHandler)
        print(f"🚀 API сервер запущен на {settings.api_host}:{settings.api_port}")
        if DB_AVAILABLE:
            print(f"📊 База данных: {settings.database_url}")
        else:
            print("📊 База данных: недоступна (режим заглушек)")
        print("🔧 Для остановки нажмите Ctrl+C")
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Останавливаем сервер...")
            server.shutdown()
            if DB_AVAILABLE:
                asyncio.run(db_manager.close())
                print("✅ База данных закрыта")
            print("✅ Сервер остановлен")
            
    except Exception as e:
        print(f"❌ Ошибка запуска сервера: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
