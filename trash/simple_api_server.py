#!/usr/bin/env python3
"""
Простой API сервер StaffProBot без зависимостей от FastAPI
"""
import json
import time
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Добавляем корневую папку в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from core.config.settings import settings
    from core.logging.logger import logger
    print("✅ Настройки и логгер загружены")
except ImportError as e:
    print(f"⚠️ Ошибка импорта: {e}")
    print("Используем значения по умолчанию")
    
    # Значения по умолчанию
    class DefaultSettings:
        app_name = "StaffProBot"
        version = "1.0.0"
        api_host = "0.0.0.0"
        api_port = 8000
    
    settings = DefaultSettings()
    
    # Простой логгер
    class SimpleLogger:
        def info(self, msg, **kwargs):
            print(f"INFO: {msg}")
        def error(self, msg, **kwargs):
            print(f"ERROR: {msg}")
    
    logger = SimpleLogger()


class SimpleAPIHandler(BaseHTTPRequestHandler):
    """Простой HTTP обработчик для API."""
    
    def log_message(self, format, *args):
        """Переопределяем логирование."""
        logger.info(f"HTTP {format}", *args)
    
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
            
            if path == "/":
                # Корневой эндпоинт
                self._send_json_response({
                    "app": settings.app_name,
                    "version": settings.version,
                    "status": "running",
                    "docs": "disabled"
                })
                
            elif path == "/health":
                # Health check
                self._send_json_response({
                    "status": "healthy",
                    "timestamp": time.time(),
                    "version": settings.version
                })
                
            elif path == "/api/v1/objects":
                # Список объектов (заглушка)
                self._send_json_response({
                    "objects": [],
                    "total": 0,
                    "page": 1,
                    "size": 10
                })
                
            elif path.startswith("/api/v1/objects/"):
                # Получение объекта по ID (заглушка)
                object_id = path.split("/")[-1]
                try:
                    object_id = int(object_id)
                    self._send_json_response({
                        "id": object_id,
                        "name": f"Объект {object_id}",
                        "status": "not_implemented"
                    })
                except ValueError:
                    self._send_error_response("Invalid ID", "ID должен быть числом", 400)
                    
            else:
                self._send_error_response("Not Found", "Эндпоинт не найден", 404)
                
        except Exception as e:
            logger.error(f"Error in GET request: {e}, path: {self.path}")
            self._send_error_response("Internal Error", str(e), 500)
    
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
                    try:
                        data = json.loads(post_data.decode('utf-8'))
                        logger.info(f"Creating object: {data}")
                        
                        # Здесь будет логика создания объекта
                        self._send_json_response({
                            "id": 1,
                            "name": data.get("name", "Новый объект"),
                            "status": "created",
                            "message": "Объект создан (заглушка)"
                        }, 201)
                    except json.JSONDecodeError:
                        self._send_error_response("Invalid JSON", "Неверный формат JSON", 400)
                else:
                    self._send_error_response("No Data", "Отсутствуют данные", 400)
            else:
                self._send_error_response("Not Found", "Эндпоинт не найден", 404)
                
        except Exception as e:
            logger.error(f"Error in POST request: {e}, path: {self.path}")
            self._send_error_response("Internal Error", str(e), 500)
    
    def do_PUT(self):
        """Обработка PUT запросов."""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            
            if path.startswith("/api/v1/objects/") and path.count("/") == 4:
                # Обновление объекта (заглушка)
                object_id = path.split("/")[-1]
                try:
                    object_id = int(object_id)
                    content_length = int(self.headers.get('Content-Length', 0))
                    if content_length > 0:
                        put_data = self.rfile.read(content_length)
                        try:
                            data = json.loads(put_data.decode('utf-8'))
                            logger.info(f"Updating object {object_id}: {data}")
                            
                            self._send_json_response({
                                "id": object_id,
                                "name": data.get("name", f"Объект {object_id}"),
                                "status": "updated",
                                "message": "Объект обновлен (заглушка)"
                            })
                        except json.JSONDecodeError:
                            self._send_error_response("Invalid JSON", "Неверный формат JSON", 400)
                    else:
                        self._send_error_response("No Data", "Отсутствуют данные", 400)
                except ValueError:
                    self._send_error_response("Invalid ID", "ID должен быть числом", 400)
            else:
                self._send_error_response("Not Found", "Эндпоинт не найден", 404)
                
        except Exception as e:
            logger.error(f"Error in PUT request: {e}, path: {self.path}")
            self._send_error_response("Internal Error", str(e), 500)
    
    def do_DELETE(self):
        """Обработка DELETE запросов."""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            
            if path.startswith("/api/v1/objects/") and path.count("/") == 4:
                # Удаление объекта (заглушка)
                object_id = path.split("/")[-1]
                try:
                    object_id = int(object_id)
                    logger.info(f"Deleting object {object_id}")
                    
                    self._set_headers(204)
                    # 204 No Content - успешное удаление без тела ответа
                except ValueError:
                    self._send_error_response("Invalid ID", "ID должен быть числом", 400)
            else:
                self._send_error_response("Not Found", "Эндпоинт не найден", 404)
                
        except Exception as e:
            logger.error(f"Error in DELETE request: {e}, path: {self.path}")
            self._send_error_response("Internal Error", str(e), 500)
    
    def do_PATCH(self):
        """Обработка PATCH запросов."""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            
            if path.startswith("/api/v1/objects/") and path.count("/") == 5:
                # Активация/деактивация объекта (заглушка)
                parts = path.split("/")
                object_id = parts[-2]
                action = parts[-1]
                
                try:
                    object_id = int(object_id)
                    logger.info(f"Patching object {object_id} with action: {action}")
                    
                    if action in ["activate", "deactivate"]:
                        self._send_json_response({
                            "id": object_id,
                            "status": "active" if action == "activate" else "inactive",
                            "message": f"Объект {action}d (заглушка)"
                        })
                    else:
                        self._send_error_response("Invalid Action", "Неверное действие", 400)
                except ValueError:
                    self._send_error_response("Invalid ID", "ID должен быть числом", 400)
            else:
                self._send_error_response("Not Found", "Эндпоинт не найден", 404)
                
        except Exception as e:
            logger.error(f"Error in PATCH request: {e}, path: {self.path}")
            self._send_error_response("Internal Error", str(e), 500)


def main():
    """Основная функция запуска простого API сервера."""
    print("🚀 Запуск StaffProBot Simple API")
    print(f"✅ Настройки загружены: {settings.app_name}")
    print(f"🌐 API будет доступен по адресу: http://{settings.api_host}:{settings.api_port}")
    print(f"🔍 Health check: http://{settings.api_host}:{settings.api_port}/health")
    print(f"📝 API endpoints: http://{settings.api_host}:{settings.api_port}/api/v1/objects")
    
    try:
        server_address = (settings.api_host, settings.api_port)
        httpd = HTTPServer(server_address, SimpleAPIHandler)
        
        logger.info(f"Simple API server started on {settings.api_host}:{settings.api_port}")
        
        print(f"✅ Сервер запущен на {settings.api_host}:{settings.api_port}")
        print("🛑 Для остановки нажмите Ctrl+C")
        
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        logger.info("Simple API server stopped by user")
        print("\n🛑 Сервер остановлен пользователем")
    except Exception as e:
        logger.error(f"Error starting simple API server: {e}")
        print(f"💥 Ошибка запуска сервера: {e}")
        raise


if __name__ == "__main__":
    main()

