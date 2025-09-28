import os
import re
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from apps.web.services.system_settings_service import SystemSettingsService
from core.logging.logger import logger
from pathlib import Path

class NginxService:
    """Сервис для управления конфигурацией Nginx"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings_service = SystemSettingsService(session)
    
    async def generate_nginx_config(self, domain: str, use_https: bool = True) -> str:
        """
        Генерирует конфигурацию Nginx на основе шаблона
        """
        logger.info(f"Generating Nginx configuration for domain: {domain}, HTTPS: {use_https}")
        
        # Путь к шаблону
        template_path = Path(__file__).parent.parent.parent.parent / "deployment" / "nginx" / "staffprobot.template.conf"
        
        if not template_path.exists():
            raise FileNotFoundError(f"Nginx template not found at {template_path}")
        
        # Читаем шаблон
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Заменяем переменные
        config_content = template_content.replace("{{DOMAIN}}", domain)
        config_content = config_content.replace("{{GENERATED_AT}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # Если HTTPS отключен, генерируем упрощенную конфигурацию
        if not use_https:
            config_content = self._generate_http_only_config(domain)
        
        return config_content
    
    def _generate_http_only_config(self, domain: str) -> str:
        """Генерирует конфигурацию только для HTTP (для разработки)"""
        return f"""
# Nginx конфигурация для StaffProBot (HTTP only)
# Сгенерировано: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

server {{
    listen 80;
    server_name {domain} www.{domain} api.{domain} admin.{domain} manager.{domain} employee.{domain} moderator.{domain} bot.{domain};

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    
    # Основной сайт
    location / {{
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # Таймауты
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Буферизация
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }}
    
    # Статические файлы
    location /static/ {{
        proxy_pass http://localhost:8001/static/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Кэширование статических файлов
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}
    
    # Медиа файлы
    location /media/ {{
        proxy_pass http://localhost:8001/media/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Кэширование медиа файлов
        expires 30d;
        add_header Cache-Control "public";
    }}
    
    # Health check
    location /health {{
        proxy_pass http://localhost:8001/health;
        access_log off;
        
        # Кэширование health check
        expires 1m;
        add_header Cache-Control "public, no-cache";
    }}
}}
"""
    
    async def save_nginx_config(self, domain: str, use_https: bool = True) -> bool:
        """
        Сохраняет конфигурацию Nginx в файл
        """
        try:
            # Получаем путь к конфигурации
            nginx_config_path = await self.settings_service.get_nginx_config_path()
            config_file_path = Path(nginx_config_path) / f"staffprobot-{domain}.conf"
            
            # Генерируем конфигурацию
            config_content = await self.generate_nginx_config(domain, use_https)
            
            # Создаем директорию если не существует
            config_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Сохраняем конфигурацию
            with open(config_file_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            logger.info(f"Nginx configuration saved to {config_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save Nginx configuration: {e}")
            return False
    
    async def validate_nginx_config(self, domain: str, use_https: bool = True) -> Dict[str, Any]:
        """
        Валидирует конфигурацию Nginx
        """
        try:
            # Генерируем конфигурацию
            config_content = await self.generate_nginx_config(domain, use_https)
            
            # Проверяем синтаксис через nginx -t
            import tempfile
            import subprocess
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as temp_file:
                temp_file.write(config_content)
                temp_file_path = temp_file.name
            
            try:
                # Тестируем конфигурацию
                result = subprocess.run(
                    ['nginx', '-t', '-c', temp_file_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Удаляем временный файл
                os.unlink(temp_file_path)
                
                if result.returncode == 0:
                    return {
                        "valid": True,
                        "message": "Nginx configuration is valid",
                        "output": result.stdout
                    }
                else:
                    return {
                        "valid": False,
                        "message": "Nginx configuration is invalid",
                        "error": result.stderr
                    }
                    
            except subprocess.TimeoutExpired:
                os.unlink(temp_file_path)
                return {
                    "valid": False,
                    "message": "Nginx configuration validation timed out",
                    "error": "Timeout"
                }
            except FileNotFoundError:
                os.unlink(temp_file_path)
                return {
                    "valid": False,
                    "message": "Nginx not found in PATH",
                    "error": "Nginx command not found"
                }
                
        except Exception as e:
            logger.error(f"Failed to validate Nginx configuration: {e}")
            return {
                "valid": False,
                "message": "Failed to validate configuration",
                "error": str(e)
            }
    
    async def apply_nginx_config(self, domain: str) -> bool:
        """
        Применяет конфигурацию Nginx (перезагружает)
        """
        try:
            # Получаем путь к конфигурации
            nginx_config_path = await self.settings_service.get_nginx_config_path()
            config_file_path = Path(nginx_config_path) / f"staffprobot-{domain}.conf"
            
            if not config_file_path.exists():
                logger.error(f"Nginx configuration file not found: {config_file_path}")
                return False
            
            # Создаем симлинк в sites-enabled если его нет
            sites_enabled_path = Path("/etc/nginx/sites-enabled") / f"staffprobot-{domain}.conf"
            if not sites_enabled_path.exists():
                sites_enabled_path.symlink_to(config_file_path)
                logger.info(f"Created symlink: {sites_enabled_path} -> {config_file_path}")
            
            # Тестируем конфигурацию
            test_result = subprocess.run(
                ['nginx', '-t'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if test_result.returncode != 0:
                logger.error(f"Nginx configuration test failed: {test_result.stderr}")
                return False
            
            # Перезагружаем Nginx
            reload_result = subprocess.run(
                ['systemctl', 'reload', 'nginx'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if reload_result.returncode != 0:
                logger.error(f"Failed to reload Nginx: {reload_result.stderr}")
                return False
            
            logger.info(f"Nginx configuration applied successfully for domain: {domain}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply Nginx configuration: {e}")
            return False
    
    async def remove_nginx_config(self, domain: str) -> bool:
        """
        Удаляет конфигурацию Nginx
        """
        try:
            # Удаляем симлинк из sites-enabled
            sites_enabled_path = Path("/etc/nginx/sites-enabled") / f"staffprobot-{domain}.conf"
            if sites_enabled_path.exists():
                sites_enabled_path.unlink()
                logger.info(f"Removed symlink: {sites_enabled_path}")
            
            # Удаляем файл конфигурации
            nginx_config_path = await self.settings_service.get_nginx_config_path()
            config_file_path = Path(nginx_config_path) / f"staffprobot-{domain}.conf"
            
            if config_file_path.exists():
                config_file_path.unlink()
                logger.info(f"Removed configuration file: {config_file_path}")
            
            # Перезагружаем Nginx
            reload_result = subprocess.run(
                ['systemctl', 'reload', 'nginx'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if reload_result.returncode != 0:
                logger.error(f"Failed to reload Nginx after removal: {reload_result.stderr}")
                return False
            
            logger.info(f"Nginx configuration removed successfully for domain: {domain}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove Nginx configuration: {e}")
            return False
    
    async def get_nginx_status(self) -> Dict[str, Any]:
        """
        Получает статус Nginx
        """
        try:
            # Проверяем статус сервиса
            status_result = subprocess.run(
                ['systemctl', 'is-active', 'nginx'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            is_active = status_result.returncode == 0
            
            # Проверяем конфигурацию
            test_result = subprocess.run(
                ['nginx', '-t'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            config_valid = test_result.returncode == 0
            
            return {
                "is_active": is_active,
                "config_valid": config_valid,
                "status_output": status_result.stdout.strip() if is_active else status_result.stderr.strip(),
                "config_output": test_result.stdout if config_valid else test_result.stderr
            }
            
        except Exception as e:
            logger.error(f"Failed to get Nginx status: {e}")
            return {
                "is_active": False,
                "config_valid": False,
                "error": str(e)
            }
