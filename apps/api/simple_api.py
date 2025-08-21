#!/usr/bin/env python3
"""
Простое API приложение StaffProBot без FastAPI
"""
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional

from core.config.settings import settings
from core.logging.logger import logger


class SimpleAPIHandler(BaseHTTPRequestHandler):
    """Простой HTTP обработчик для API."""
    
    def log_message(self, format, *args):
        """Переопределяем логирование для использования нашего логгера."""
        logger.info(f"HTTP {format}", *args)
    
    def _set_headers(self, status_code: int = 200, content_type: str = "application/json"):
        """Устанавливаем заголовки ответа."""
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, PATCH, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def _send_json_response(self, data: Dict[str, Any], status_code: int = 200):
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
            logger.error("Error in GET request", error=str(e), path=self.path)
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
                        logger.info("Creating object", data=data)
                        
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
            logger.error("Error in POST request", error=str(e), path=self.path)
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
                            logger.info("Updating object", object_id=object_id, data=data)
                            
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
            logger.error("Error in PUT request", error=str(e), path=self.path)
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
                    logger.info("Deleting object", object_id=object_id)
                    
                    self._set_headers(204)
                    # 204 No Content - успешное удаление без тела ответа
                except ValueError:
                    self._send_error_response("Invalid ID", "ID должен быть числом", 400)
            else:
                self._send_error_response("Not Found", "Эндпоинт не найден", 404)
                
        except Exception as e:
            logger.error("Error in DELETE request", error=str(e), path=self.path)
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
                    logger.info("Patching object", object_id=object_id, action=action)
                    
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
            logger.error("Error in PATCH request", error=str(e), path=self.path)
            self._send_error_response("Internal Error", str(e), 500)


def run_simple_api():
    """Запуск простого API сервера."""
    try:
        server_address = (settings.api_host, settings.api_port)
        httpd = HTTPServer(server_address, SimpleAPIHandler)
        
        logger.info(
            "Simple API server started",
            host=settings.api_host,
            port=settings.api_port
        )
        
        print(f"🚀 Запуск StaffProBot Simple API")
        print(f"✅ Настройки загружены: {settings.app_name}")
        print(f"🌐 API будет доступен по адресу: http://{settings.api_host}:{settings.api_port}")
        print(f"🔍 Health check: http://{settings.api_host}:{settings.api_port}/health")
        print(f"📝 API endpoints: http://{settings.api_host}:{settings.api_port}/api/v1/objects")
        
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        logger.info("Simple API server stopped by user")
        print("\n🛑 Сервер остановлен пользователем")
    except Exception as e:
        logger.error("Error starting simple API server", error=str(e))
        print(f"💥 Ошибка запуска сервера: {e}")
        raise


if __name__ == "__main__":
    run_simple_api()

