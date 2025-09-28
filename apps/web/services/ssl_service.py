"""
Сервис для управления SSL сертификатами
"""

import subprocess
import os
import ssl
import socket
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncio
from core.logging.logger import logger
from apps.web.services.system_settings_service import SystemSettingsService


class SSLService:
    """Сервис для управления SSL сертификатами"""
    
    def __init__(self, settings_service: SystemSettingsService):
        self.settings_service = settings_service
        self.certbot_path = "/usr/bin/certbot"
        self.letsencrypt_dir = "/etc/letsencrypt"
        self.nginx_dir = "/etc/nginx/sites-available"
    
    async def setup_ssl(self, domain: str, email: str) -> Dict[str, Any]:
        """Настройка SSL сертификатов для домена"""
        try:
            logger.info(f"Starting SSL setup for domain: {domain}")
            
            # Проверяем DNS
            dns_check = await self._check_dns_resolution(domain)
            if not dns_check["resolves"]:
                return {
                    "success": False,
                    "error": f"DNS не резолвится для домена {domain}",
                    "details": dns_check
                }
            
            # Останавливаем nginx для получения сертификатов
            await self._stop_nginx()
            
            # Получаем сертификаты
            cert_result = await self._obtain_certificates(domain, email)
            if not cert_result["success"]:
                await self._start_nginx()
                return cert_result
            
            # Проверяем полученные сертификаты
            cert_check = await self._verify_certificates(domain)
            if not cert_check["valid"]:
                await self._start_nginx()
                return {
                    "success": False,
                    "error": "Полученные сертификаты невалидны",
                    "details": cert_check
                }
            
            # Запускаем nginx обратно
            await self._start_nginx()
            
            # Обновляем настройки в БД
            await self.settings_service.set_domain(domain)
            await self.settings_service.set_ssl_email(email)
            await self.settings_service.set_use_https(True)
            
            logger.info(f"SSL setup completed successfully for domain: {domain}")
            
            return {
                "success": True,
                "message": f"SSL сертификаты успешно настроены для {domain}",
                "domain": domain,
                "certificates": cert_check["certificates"]
            }
            
        except Exception as e:
            logger.error(f"Error setting up SSL for {domain}: {e}")
            await self._start_nginx()  # Пытаемся запустить nginx обратно
            return {
                "success": False,
                "error": f"Ошибка настройки SSL: {str(e)}"
            }
    
    async def renew_certificates(self) -> Dict[str, Any]:
        """Обновление SSL сертификатов"""
        try:
            logger.info("Starting SSL certificate renewal")
            
            # Проверяем, нужно ли обновление
            renewal_check = await self._check_renewal_needed()
            if not renewal_check["needed"]:
                return {
                    "success": True,
                    "message": "Обновление сертификатов не требуется",
                    "next_renewal": renewal_check["next_renewal"]
                }
            
            # Выполняем обновление
            result = await self._run_certbot_renew()
            if not result["success"]:
                return result
            
            # Перезагружаем nginx
            reload_result = await self._reload_nginx()
            if not reload_result["success"]:
                return {
                    "success": False,
                    "error": "Сертификаты обновлены, но не удалось перезагрузить nginx",
                    "details": reload_result
                }
            
            logger.info("SSL certificate renewal completed successfully")
            
            return {
                "success": True,
                "message": "Сертификаты успешно обновлены",
                "renewed_certificates": result["renewed"]
            }
            
        except Exception as e:
            logger.error(f"Error renewing certificates: {e}")
            return {
                "success": False,
                "error": f"Ошибка обновления сертификатов: {str(e)}"
            }
    
    async def check_certificate_status(self, domain: str) -> Dict[str, Any]:
        """Проверка статуса SSL сертификатов"""
        try:
            cert_path = f"{self.letsencrypt_dir}/live/{domain}/fullchain.pem"
            
            if not os.path.exists(cert_path):
                return {
                    "valid": False,
                    "exists": False,
                    "error": "Сертификат не найден"
                }
            
            # Читаем сертификат
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
            
            # Парсим сертификат
            cert = ssl.DER_cert_to_PEM_cert(cert_data)
            cert_obj = ssl.PEM_cert_to_DER_cert(cert)
            x509 = ssl.DER_cert_to_PEM_cert(cert_obj)
            
            # Получаем информацию о сертификате
            cert_info = await self._parse_certificate_info(cert_path)
            
            # Проверяем срок действия
            now = datetime.now()
            days_until_expiry = (cert_info["not_after"] - now).days
            
            return {
                "valid": True,
                "exists": True,
                "domain": domain,
                "issuer": cert_info["issuer"],
                "subject": cert_info["subject"],
                "not_before": cert_info["not_before"].isoformat(),
                "not_after": cert_info["not_after"].isoformat(),
                "days_until_expiry": days_until_expiry,
                "needs_renewal": days_until_expiry <= 30,
                "certificate_path": cert_path
            }
            
        except Exception as e:
            logger.error(f"Error checking certificate status for {domain}: {e}")
            return {
                "valid": False,
                "exists": False,
                "error": f"Ошибка проверки сертификата: {str(e)}"
            }
    
    async def get_certificate_info(self, domain: str) -> Dict[str, Any]:
        """Получение подробной информации о сертификате"""
        try:
            cert_path = f"{self.letsencrypt_dir}/live/{domain}/fullchain.pem"
            
            if not os.path.exists(cert_path):
                return {
                    "success": False,
                    "error": "Сертификат не найден"
                }
            
            # Получаем информацию о сертификате
            cert_info = await self._parse_certificate_info(cert_path)
            
            # Получаем размер файлов
            cert_size = os.path.getsize(cert_path)
            key_path = f"{self.letsencrypt_dir}/live/{domain}/privkey.pem"
            key_size = os.path.getsize(key_path) if os.path.exists(key_path) else 0
            
            return {
                "success": True,
                "domain": domain,
                "certificate": {
                    "issuer": cert_info["issuer"],
                    "subject": cert_info["subject"],
                    "not_before": cert_info["not_before"].isoformat(),
                    "not_after": cert_info["not_after"].isoformat(),
                    "serial_number": cert_info.get("serial_number", "N/A"),
                    "version": cert_info.get("version", "N/A")
                },
                "files": {
                    "certificate_path": cert_path,
                    "key_path": key_path,
                    "certificate_size": cert_size,
                    "key_size": key_size
                },
                "status": {
                    "valid": True,
                    "days_until_expiry": (cert_info["not_after"] - datetime.now()).days,
                    "needs_renewal": (cert_info["not_after"] - datetime.now()).days <= 30
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting certificate info for {domain}: {e}")
            return {
                "success": False,
                "error": f"Ошибка получения информации о сертификате: {str(e)}"
            }
    
    async def _check_dns_resolution(self, domain: str) -> Dict[str, Any]:
        """Проверка DNS резолвинга домена"""
        try:
            # Убираем протокол если есть
            clean_domain = domain.replace("https://", "").replace("http://", "")
            
            # Проверяем A запись
            try:
                ip = socket.gethostbyname(clean_domain)
                return {
                    "resolves": True,
                    "ip": ip,
                    "domain": clean_domain
                }
            except socket.gaierror as e:
                return {
                    "resolves": False,
                    "error": f"DNS не резолвится: {str(e)}",
                    "domain": clean_domain
                }
                
        except Exception as e:
            return {
                "resolves": False,
                "error": f"Ошибка проверки DNS: {str(e)}",
                "domain": domain
            }
    
    async def _stop_nginx(self) -> bool:
        """Остановка nginx"""
        try:
            result = await self._run_command(["systemctl", "stop", "nginx"])
            return result["success"]
        except Exception as e:
            logger.error(f"Error stopping nginx: {e}")
            return False
    
    async def _start_nginx(self) -> bool:
        """Запуск nginx"""
        try:
            result = await self._run_command(["systemctl", "start", "nginx"])
            return result["success"]
        except Exception as e:
            logger.error(f"Error starting nginx: {e}")
            return False
    
    async def _reload_nginx(self) -> Dict[str, Any]:
        """Перезагрузка nginx"""
        try:
            # Сначала проверяем конфигурацию
            check_result = await self._run_command(["nginx", "-t"])
            if not check_result["success"]:
                return {
                    "success": False,
                    "error": "Ошибка конфигурации nginx",
                    "details": check_result["stderr"]
                }
            
            # Перезагружаем nginx
            reload_result = await self._run_command(["systemctl", "reload", "nginx"])
            return reload_result
            
        except Exception as e:
            logger.error(f"Error reloading nginx: {e}")
            return {
                "success": False,
                "error": f"Ошибка перезагрузки nginx: {str(e)}"
            }
    
    async def _obtain_certificates(self, domain: str, email: str) -> Dict[str, Any]:
        """Получение сертификатов через certbot"""
        try:
            # Подготавливаем домены
            domains = [domain]
            if not domain.startswith("www."):
                domains.append(f"www.{domain}")
            
            # Добавляем поддомены
            subdomains = ["api", "admin", "bot"]
            for subdomain in subdomains:
                domains.append(f"{subdomain}.{domain}")
            
            # Формируем команду certbot
            cmd = [
                self.certbot_path,
                "certonly",
                "--standalone",
                "--email", email,
                "--agree-tos",
                "--no-eff-email",
                "--domains", ",".join(domains),
                "--non-interactive"
            ]
            
            logger.info(f"Running certbot command: {' '.join(cmd)}")
            result = await self._run_command(cmd)
            
            if result["success"]:
                return {
                    "success": True,
                    "domains": domains,
                    "output": result["stdout"]
                }
            else:
                return {
                    "success": False,
                    "error": "Ошибка получения сертификатов",
                    "details": result["stderr"]
                }
                
        except Exception as e:
            logger.error(f"Error obtaining certificates: {e}")
            return {
                "success": False,
                "error": f"Ошибка получения сертификатов: {str(e)}"
            }
    
    async def _verify_certificates(self, domain: str) -> Dict[str, Any]:
        """Проверка валидности сертификатов"""
        try:
            cert_path = f"{self.letsencrypt_dir}/live/{domain}/fullchain.pem"
            key_path = f"{self.letsencrypt_dir}/live/{domain}/privkey.pem"
            
            if not os.path.exists(cert_path) or not os.path.exists(key_path):
                return {
                    "valid": False,
                    "error": "Файлы сертификатов не найдены"
                }
            
            # Проверяем сертификат
            cert_info = await self._parse_certificate_info(cert_path)
            
            # Проверяем, что сертификат действителен
            now = datetime.now()
            if cert_info["not_before"] > now or cert_info["not_after"] < now:
                return {
                    "valid": False,
                    "error": "Сертификат недействителен по времени"
                }
            
            return {
                "valid": True,
                "certificates": {
                    "domain": domain,
                    "issuer": cert_info["issuer"],
                    "not_before": cert_info["not_before"].isoformat(),
                    "not_after": cert_info["not_after"].isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error verifying certificates: {e}")
            return {
                "valid": False,
                "error": f"Ошибка проверки сертификатов: {str(e)}"
            }
    
    async def _check_renewal_needed(self) -> Dict[str, Any]:
        """Проверка необходимости обновления сертификатов"""
        try:
            # Запускаем dry-run обновления
            cmd = [self.certbot_path, "renew", "--dry-run"]
            result = await self._run_command(cmd)
            
            if result["success"]:
                # Проверяем, есть ли сертификаты для обновления
                if "No renewals were attempted" in result["stdout"]:
                    return {
                        "needed": False,
                        "message": "Обновление не требуется"
                    }
                else:
                    return {
                        "needed": True,
                        "message": "Требуется обновление сертификатов"
                    }
            else:
                return {
                    "needed": False,
                    "error": "Ошибка проверки обновления",
                    "details": result["stderr"]
                }
                
        except Exception as e:
            logger.error(f"Error checking renewal needed: {e}")
            return {
                "needed": False,
                "error": f"Ошибка проверки обновления: {str(e)}"
            }
    
    async def _run_certbot_renew(self) -> Dict[str, Any]:
        """Запуск обновления сертификатов"""
        try:
            cmd = [self.certbot_path, "renew", "--quiet"]
            result = await self._run_command(cmd)
            
            if result["success"]:
                return {
                    "success": True,
                    "renewed": True,
                    "output": result["stdout"]
                }
            else:
                return {
                    "success": False,
                    "error": "Ошибка обновления сертификатов",
                    "details": result["stderr"]
                }
                
        except Exception as e:
            logger.error(f"Error running certbot renew: {e}")
            return {
                "success": False,
                "error": f"Ошибка обновления сертификатов: {str(e)}"
            }
    
    async def _parse_certificate_info(self, cert_path: str) -> Dict[str, Any]:
        """Парсинг информации о сертификате"""
        try:
            # Используем openssl для парсинга сертификата
            cmd = ["openssl", "x509", "-in", cert_path, "-noout", "-text"]
            result = await self._run_command(cmd)
            
            if not result["success"]:
                raise Exception(f"Ошибка парсинга сертификата: {result['stderr']}")
            
            # Парсим вывод openssl
            output = result["stdout"]
            lines = output.split('\n')
            
            cert_info = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith("Issuer:"):
                    cert_info["issuer"] = line.replace("Issuer:", "").strip()
                elif line.startswith("Subject:"):
                    cert_info["subject"] = line.replace("Subject:", "").strip()
                elif line.startswith("Not Before:"):
                    date_str = line.replace("Not Before:", "").strip()
                    cert_info["not_before"] = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
                elif line.startswith("Not After:"):
                    date_str = line.replace("Not After:", "").strip()
                    cert_info["not_after"] = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
                elif line.startswith("Serial Number:"):
                    cert_info["serial_number"] = line.replace("Serial Number:", "").strip()
                elif line.startswith("Version:"):
                    cert_info["version"] = line.replace("Version:", "").strip()
            
            return cert_info
            
        except Exception as e:
            logger.error(f"Error parsing certificate info: {e}")
            raise
    
    async def _run_command(self, cmd: List[str]) -> Dict[str, Any]:
        """Выполнение системной команды"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode('utf-8'),
                "stderr": stderr.decode('utf-8'),
                "returncode": process.returncode
            }
            
        except Exception as e:
            logger.error(f"Error running command {' '.join(cmd)}: {e}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
