#!/usr/bin/env python3
"""
Полностью независимый API сервер StaffProBot
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

# Отмечаем, что база данных недоступна
DB_AVAILABLE = False
db_manager = None
get_db_session = None

print("⚠️ База данных недоступна, работаем в режиме заглушек")


class StandaloneAPIHandler(BaseHTTPRequestHandler):
    """HTTP обработчик для API без зависимостей."""
    
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
                    "database": "disconnected (standalone mode)",
                    "docs": "disabled"
                })
                
            elif path == "/health":
                # Health check
                self._send_json_response({
                    "status": "healthy",
                    "timestamp": time.time(),
                    "version": settings.version,
                    "database": "disconnected (standalone mode)"
                })
                
            elif path == "/api/v1/objects":
                # Список объектов (заглушка)
                self._send_json_response({
                    "objects": [
                        {
                            "id": 1,
                            "name": "Тестовый объект",
                            "owner_id": 1,
                            "address": "ул. Тестовая, 1",
                            "coordinates": "55.7558,37.6176",
                            "opening_time": "09:00:00",
                            "closing_time": "18:00:00",
                            "hourly_rate": 500.00,
                            "required_employees": "Охранник, уборщик",
                            "is_active": True,
                            "created_at": "2025-01-20T10:00:00",
                            "updated_at": "2025-01-20T10:00:00"
                        }
                    ],
                    "count": 1,
                    "message": "Database not available - using mock data"
                })
                
            elif path.startswith("/api/v1/objects/") and path.count("/") == 4:
                # Получение объекта по ID (заглушка)
                object_id = int(path.split("/")[-1])
                if object_id == 1:
                    self._send_json_response({
                        "id": 1,
                        "name": "Тестовый объект",
                        "owner_id": 1,
                        "address": "ул. Тестовая, 1",
                        "coordinates": "55.7558,37.6176",
                        "opening_time": "09:00:00",
                        "closing_time": "18:00:00",
                        "hourly_rate": 500.00,
                        "required_employees": "Охранник, уборщик",
                        "is_active": True,
                        "created_at": "2025-01-20T10:00:00",
                        "updated_at": "2025-01-20T10:00:00"
                    })
                else:
                    self._send_error_response("not_found", f"Object {object_id} not found", 404)
                
            elif path == "/api/v1/users":
                # Список пользователей (заглушка)
                self._send_json_response({
                    "users": [
                        {
                            "id": 1,
                            "telegram_id": 123456789,
                            "username": "test_user",
                            "first_name": "Тест",
                            "last_name": "Пользователь",
                            "phone": "+79001234567",
                            "role": "employee",
                            "is_active": True,
                            "created_at": "2025-01-20T10:00:00",
                            "updated_at": "2025-01-20T10:00:00"
                        }
                    ],
                    "count": 1,
                    "message": "Database not available - using mock data"
                })
                
            elif path.startswith("/api/v1/users/") and path.count("/") == 4:
                # Получение пользователя по ID (заглушка)
                user_id = int(path.split("/")[-1])
                if user_id == 1:
                    self._send_json_response({
                        "id": 1,
                        "telegram_id": 123456789,
                        "username": "test_user",
                        "first_name": "Тест",
                        "last_name": "Пользователь",
                        "phone": "+79001234567",
                        "role": "employee",
                        "is_active": True,
                        "created_at": "2025-01-20T10:00:00",
                        "updated_at": "2025-01-20T10:00:00"
                    })
                else:
                    self._send_error_response("not_found", f"User {user_id} not found", 404)
                
            elif path == "/api/v1/shifts":
                # Список смен (заглушка)
                self._send_json_response({
                    "shifts": [
                        {
                            "id": 1,
                            "user_id": 1,
                            "object_id": 1,
                            "start_time": "2025-01-20T10:00:00",
                            "end_time": None,
                            "status": "active",
                            "start_coordinates": "55.7558,37.6176",
                            "end_coordinates": None,
                            "total_hours": None,
                            "hourly_rate": 500.00,
                            "total_payment": None,
                            "notes": "Тестовая смена",
                            "created_at": "2025-01-20T10:00:00",
                            "updated_at": "2025-01-20T10:00:00"
                        }
                    ],
                    "count": 1,
                    "message": "Database not available - using mock data"
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
                # Создание объекта (заглушка)
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    post_data = self.rfile.read(content_length)
                    object_data = json.loads(post_data.decode('utf-8'))
                    logger.info(f"Creating object: {object_data}")
                
                self._send_json_response({
                    "message": "Object created successfully (mock mode)",
                    "object_id": 999,
                    "note": "This is mock data - database not available"
                }, 201)
                
            elif path == "/api/v1/users":
                # Создание пользователя (заглушка)
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    post_data = self.rfile.read(content_length)
                    user_data = json.loads(post_data.decode('utf-8'))
                    logger.info(f"Creating user: {user_data}")
                
                self._send_json_response({
                    "message": "User created successfully (mock mode)",
                    "user_id": 999,
                    "note": "This is mock data - database not available"
                }, 201)
                
            elif path == "/api/v1/shifts":
                # Создание смены (заглушка)
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    post_data = self.rfile.read(content_length)
                    shift_data = json.loads(post_data.decode('utf-8'))
                    logger.info(f"Creating shift: {shift_data}")
                
                self._send_json_response({
                    "message": "Shift created successfully (mock mode)",
                    "shift_id": 999,
                    "note": "This is mock data - database not available"
                }, 201)
                
            else:
                self._send_error_response("not_found", "Endpoint not found", 404)
                
        except Exception as e:
            logger.error(f"Error in POST request: {e}")
            self._send_error_response("internal_error", str(e), 500)


def main():
    """Главная функция."""
    try:
        print("⚠️ База данных недоступна, работаем в режиме заглушек")
        
        # Создаем сервер
        server = HTTPServer((settings.api_host, settings.api_port), StandaloneAPIHandler)
        print(f"🚀 API сервер запущен на {settings.api_host}:{settings.api_port}")
        print("📊 База данных: недоступна (режим заглушек)")
        print("🔧 Для остановки нажмите Ctrl+C")
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Останавливаем сервер...")
            server.shutdown()
            print("✅ Сервер остановлен")
            
    except Exception as e:
        print(f"❌ Ошибка запуска сервера: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
