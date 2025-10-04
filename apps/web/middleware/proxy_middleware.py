"""Middleware для обработки заголовков прокси."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class ProxyMiddleware(BaseHTTPMiddleware):
    """Middleware для обработки заголовков прокси и установки правильного URL."""
    
    async def dispatch(self, request: Request, call_next):
        """Обработка запроса с заголовками прокси."""
        
        # Получаем заголовки от прокси
        forwarded_proto = request.headers.get("x-forwarded-proto")
        forwarded_host = request.headers.get("x-forwarded-host")
        forwarded_port = request.headers.get("x-forwarded-port")
        
        # Если есть заголовки прокси, обновляем URL
        if forwarded_proto:
            # Определяем схему (http/https)
            scheme = forwarded_proto
            
            # Определяем хост
            if forwarded_host:
                host = forwarded_host
            else:
                host = request.headers.get("host", "localhost")
            
            # Определяем порт
            if forwarded_port:
                port = forwarded_port
            elif scheme == "https":
                port = "443"
            else:
                port = "80"
            
            # Обновляем URL в запросе
            if port in ["80", "443"] and (scheme == "http" and port == "80" or scheme == "https" and port == "443"):
                # Стандартные порты не указываем в URL
                request._url = request._url.replace(
                    scheme=request.url.scheme,
                    hostname=request.url.hostname,
                    port=request.url.port,
                    netloc=f"{scheme}://{host}"
                )
            else:
                request._url = request._url.replace(
                    scheme=request.url.scheme,
                    hostname=request.url.hostname,
                    port=request.url.port,
                    netloc=f"{scheme}://{host}:{port}"
                )
        
        response = await call_next(request)
        return response
