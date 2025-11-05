import os
import re
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from apps.web.services.system_settings_service import SystemSettingsService
from core.logging.logger import logger
from pathlib import Path
from apps.web.services.exec_service import LocalExecutor, SSHExecutor

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
            # Fallback для dev: сохраняем в локальную папку проекта
            try:
                fallback_dir = Path(__file__).parent.parent.parent.parent / "deployment" / "nginx" / "dev_out"
                fallback_dir.mkdir(parents=True, exist_ok=True)
                fallback_file = fallback_dir / f"staffprobot-{domain}.conf"
                fallback_file.write_text(await self.generate_nginx_config(domain, use_https), encoding='utf-8')
                logger.info(f"Nginx configuration saved to fallback path: {fallback_file}")
                return True
            except Exception as e2:
                logger.error(f"Fallback save failed: {e2}")
                return False
    
    async def validate_nginx_config(self, domain: str, use_https: bool = True) -> Dict[str, Any]:
        """
        Валидирует конфигурацию Nginx
        """
        try:
            # Генерируем конфигурацию
            config_content = await self.generate_nginx_config(domain, use_https)
            
            # Проверяем синтаксис через nginx -t
            # Пишем во временный файл на целевой стороне и валидируем
            executor = await self._get_executor()
            tmp_path = f"/tmp/staffprobot_nginx_{domain}.conf"
            # sudo нужен только на удалённом хосте
            from apps.web.services.exec_service import SSHExecutor, LocalExecutor
            use_sudo = isinstance(executor, SSHExecutor)
            code, out, err = executor.write_file(tmp_path, config_content, sudo=use_sudo)
            if code != 0:
                return {"valid": False, "message": "Failed to write temp config", "error": err or out}
            # В dev (LocalExecutor) nginx может отсутствовать — пропускаем проверку
            if isinstance(executor, LocalExecutor):
                rm_cmd = f"rm -f {tmp_path}"
                executor.run(rm_cmd)
                return {"valid": True, "message": "Dev mode: skipped nginx -t (nginx not available)", "output": "skipped"}
            nginx_cmd = f"{'sudo ' if use_sudo else ''}nginx -t -c {tmp_path}"
            code, out, err = executor.run(nginx_cmd, timeout=15)
            # Удалить временный файл (best-effort)
            rm_cmd = f"{'sudo ' if use_sudo else ''}rm -f {tmp_path}"
            executor.run(rm_cmd)
            if code == 0:
                return {"valid": True, "message": "Nginx configuration is valid", "output": out}
            return {"valid": False, "message": "Nginx configuration is invalid", "error": err or out}
                
        except Exception as e:
            logger.error(f"Failed to validate Nginx configuration: {e}")
            return {
                "valid": False,
                "message": "Failed to validate configuration",
                "error": str(e)
            }
    
    async def create_config_backup(self, domain: str) -> bool:
        """
        Создает backup текущей конфигурации Nginx
        """
        try:
            executor = await self._get_executor()
            nginx_config_path = await self.settings_service.get_nginx_config_path()
            config_file_path = Path(nginx_config_path) / f"staffprobot-{domain}.conf"
            from apps.web.services.exec_service import LocalExecutor
            if isinstance(executor, LocalExecutor):
                # dev fallback: берем файл из проекта deployment/nginx/dev_out
                project_dev_out = Path(__file__).parent.parent.parent.parent / "deployment" / "nginx" / "dev_out"
                src = project_dev_out / f"staffprobot-{domain}.conf"
                if not src.exists():
                    logger.warning(f"(dev) No config to backup: {src}")
                    return True
                backup_dir = project_dev_out / "backups"
                backup_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dst = backup_dir / f"staffprobot-{domain}_{timestamp}.conf"
                import shutil
                shutil.copy2(src, dst)
                logger.info(f"(dev) Nginx configuration backup created: {dst}")
                return True
            # prod/system path
            if not config_file_path.exists():
                logger.warning(f"No existing configuration to backup for domain: {domain}")
                return True
            backup_dir = Path(nginx_config_path) / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file_path = backup_dir / f"staffprobot-{domain}_{timestamp}.conf"
            import shutil
            shutil.copy2(config_file_path, backup_file_path)
            logger.info(f"Nginx configuration backup created: {backup_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create Nginx configuration backup: {e}")
            return False

    async def apply_nginx_config(self, domain: str) -> bool:
        """
        Применяет конфигурацию Nginx (перезагружает)
        """
        try:
            # Создаем backup перед применением
            await self.create_config_backup(domain)
            executor = await self._get_executor()
            nginx_config_path = await self.settings_service.get_nginx_config_path()
            config_file = f"{nginx_config_path}/staffprobot-{domain}.conf"
            enabled_link = f"/etc/nginx/sites-enabled/staffprobot-{domain}.conf"
            # Проверка наличия файла
            code, out, err = executor.run(f"test -f {shlex.quote(config_file)}")
            if code != 0:
                logger.error(f"Nginx configuration file not found: {config_file}")
                return False
            # Создать symlink при отсутствии
            executor.run(f"sudo ln -sf {shlex.quote(config_file)} {shlex.quote(enabled_link)}")
            # Тест и перезагрузка
            code, out, err = executor.run("sudo nginx -t", timeout=15)
            if code != 0:
                logger.error(f"Nginx configuration test failed: {err or out}")
                return False
            code, out, err = executor.run("sudo systemctl reload nginx", timeout=15)
            if code != 0:
                logger.error(f"Failed to reload Nginx: {err or out}")
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
            executor = await self._get_executor()
            nginx_config_path = await self.settings_service.get_nginx_config_path()
            config_file = f"{nginx_config_path}/staffprobot-{domain}.conf"
            enabled_link = f"/etc/nginx/sites-enabled/staffprobot-{domain}.conf"
            executor.run(f"sudo rm -f {shlex.quote(enabled_link)}")
            executor.run(f"sudo rm -f {shlex.quote(config_file)}")
            code, out, err = executor.run("sudo systemctl reload nginx", timeout=15)
            if code != 0:
                logger.error(f"Failed to reload Nginx after removal: {err or out}")
                return False
            
            logger.info(f"Nginx configuration removed successfully for domain: {domain}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove Nginx configuration: {e}")
            return False
    
    async def list_config_backups(self, domain: str) -> List[Dict[str, Any]]:
        """
        Получает список backup'ов конфигурации для домена
        """
        try:
            executor = await self._get_executor()
            from apps.web.services.exec_service import LocalExecutor
            backups: List[Dict[str, Any]] = []
            if isinstance(executor, LocalExecutor):
                project_dev_out = Path(__file__).parent.parent.parent.parent / "deployment" / "nginx" / "dev_out" / "backups"
                if not project_dev_out.exists():
                    return []
                for backup_file in project_dev_out.glob(f"staffprobot-{domain}_*.conf"):
                    stat = backup_file.stat()
                    backups.append({
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "size": stat.st_size
                    })
                backups.sort(key=lambda x: x["created_at"], reverse=True)
                return backups
            # remote/system path via ls
            nginx_config_path = await self.settings_service.get_nginx_config_path()
            backup_dir = f"{nginx_config_path}/backups"
            code, out, err = executor.run(f"bash -lc 'ls -l --time-style=+%s {shlex.quote(backup_dir)}/staffprobot-{domain}_*.conf 2>/dev/null'", timeout=10)
            if code != 0 or not out.strip():
                return []
            for line in out.strip().splitlines():
                parts = line.split()
                if len(parts) < 6:
                    continue
                size = int(parts[4])
                epoch = int(parts[5])
                path = parts[-1]
                filename = path.split('/')[-1]
                backups.append({
                    "filename": filename,
                    "path": path,
                    "created_at": datetime.fromtimestamp(epoch).isoformat(),
                    "size": size
                })
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list Nginx configuration backups: {e}")
            return []
    
    async def restore_config_from_backup(self, domain: str, backup_filename: str) -> bool:
        """
        Восстанавливает конфигурацию из backup'а
        """
        try:
            executor = await self._get_executor()
            from apps.web.services.exec_service import LocalExecutor
            if isinstance(executor, LocalExecutor):
                project_dev_out = Path(__file__).parent.parent.parent.parent / "deployment" / "nginx" / "dev_out"
                backup_file_path = project_dev_out / "backups" / backup_filename
                config_file_path = project_dev_out / f"staffprobot-{domain}.conf"
                if not backup_file_path.exists():
                    logger.error(f"(dev) Backup file not found: {backup_file_path}")
                    return False
                await self.create_config_backup(domain)
                import shutil
                shutil.copy2(backup_file_path, config_file_path)
                logger.info(f"(dev) Nginx configuration restored from backup: {backup_file_path}")
                return True
            # Remote/system
            nginx_config_path = await self.settings_service.get_nginx_config_path()
            backup_dir = f"{nginx_config_path}/backups"
            backup_file_path = f"{backup_dir}/{backup_filename}"
            config_file_path = f"{nginx_config_path}/staffprobot-{domain}.conf"
            code, _, _ = executor.run(f"test -f {shlex.quote(backup_file_path)}")
            if code != 0:
                logger.error(f"Backup file not found: {backup_file_path}")
                return False
            await self.create_config_backup(domain)
            executor.run(f"sudo cp -f {shlex.quote(backup_file_path)} {shlex.quote(config_file_path)}")
            code, out, err = executor.run("sudo nginx -t", timeout=15)
            if code != 0:
                logger.error(f"Restored Nginx configuration test failed: {err or out}")
                return False
            code, out, err = executor.run("sudo systemctl reload nginx", timeout=15)
            if code != 0:
                logger.error(f"Failed to reload Nginx after restore: {err or out}")
                return False
            logger.info(f"Nginx configuration restored from backup: {backup_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore Nginx configuration from backup: {e}")
            return False
    
    async def delete_config_backup(self, domain: str, backup_filename: str) -> bool:
        """
        Удаляет backup конфигурации
        """
        try:
            executor = await self._get_executor()
            from apps.web.services.exec_service import LocalExecutor
            if isinstance(executor, LocalExecutor):
                project_dev_out = Path(__file__).parent.parent.parent.parent / "deployment" / "nginx" / "dev_out" / "backups"
                p = project_dev_out / backup_filename
                if p.exists():
                    p.unlink()
                    logger.info(f"(dev) Nginx configuration backup deleted: {backup_filename}")
                    return True
                logger.error(f"(dev) Backup file not found: {p}")
                return False
            nginx_config_path = await self.settings_service.get_nginx_config_path()
            backup_file_path = f"{nginx_config_path}/backups/{backup_filename}"
            code, out, err = executor.run(f"sudo rm -f {shlex.quote(backup_file_path)}", timeout=10)
            if code != 0:
                logger.error(f"Failed to delete backup: {err or out}")
                return False
            logger.info(f"Nginx configuration backup deleted: {backup_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete Nginx configuration backup: {e}")
            return False
    
    async def get_nginx_status(self) -> Dict[str, Any]:
        """
        Получает статус Nginx
        """
        try:
            executor = await self._get_executor()
            code, out, err = executor.run("systemctl is-active nginx", timeout=5)
            is_active = code == 0
            code2, out2, err2 = executor.run("sudo nginx -t", timeout=10)
            config_valid = code2 == 0
            return {
                "is_active": is_active,
                "config_valid": config_valid,
                "status_output": (out if is_active else err).strip(),
                "config_output": out2 if config_valid else err2,
            }
        except Exception as e:
            logger.error(f"Failed to get Nginx status: {e}")
            return {
                "is_active": False,
                "config_valid": False,
                "error": str(e)
            }

    async def _get_executor(self):
        """Определить исполнителя команд по настройкам (prod/dev)."""
        try:
            is_prod = await self.settings_service.get_is_production_mode()
            if is_prod:
                host = await self.settings_service.get_nginx_ssh_host()
                user = await self.settings_service.get_nginx_ssh_user()
                key = await self.settings_service.get_nginx_ssh_key_path()
                if host:
                    return SSHExecutor(host=host, user=user or None, key_path=key or None)
        except Exception:
            pass
        return LocalExecutor()
