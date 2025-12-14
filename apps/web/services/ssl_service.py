"""
Сервис для управления SSL сертификатами
"""

import subprocess
import os
import ssl
import socket
import configparser
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncio
from core.logging.logger import logger
from apps.web.services.system_settings_service import SystemSettingsService
from apps.web.services.ssl_logging_service import SSLLoggingService


class SSLService:
    """Сервис для управления SSL сертификатами"""
    
    def __init__(self, settings_service: SystemSettingsService, logging_service: SSLLoggingService = None):
        self.settings_service = settings_service
        self.logging_service = logging_service
        self.certbot_path = "/usr/bin/certbot"
        self.letsencrypt_dir = "/etc/letsencrypt"
        self.nginx_dir = "/etc/nginx/sites-available"
    
    async def setup_ssl(self, domain: str, email: str) -> Dict[str, Any]:
        """Настройка SSL сертификатов для домена"""
        try:
            logger.info(f"Starting SSL setup for domain: {domain}")
            
            # Логируем начало операции
            if self.logging_service:
                await self.logging_service.log_ssl_operation(
                    operation="setup_ssl",
                    domain=domain,
                    status="started",
                    details={"email": email}
                )
            
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
            
            # Получаем домен для передачи в renew (для fallback)
            domain = await self.settings_service.get_domain()
            if not domain or domain == "localhost:8001":
                return {
                    "success": False,
                    "error": "Домен не настроен"
                }
            
            # Проверяем, нужно ли обновление
            renewal_check = await self._check_renewal_needed()
            if not renewal_check["needed"]:
                return {
                    "success": True,
                    "message": "Обновление сертификатов не требуется",
                    "next_renewal": renewal_check.get("next_renewal")
                }
            
            # Выполняем обновление с передачей домена для fallback
            result = await self._run_certbot_renew(domain=domain)
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
            # Проверяем основной путь
            cert_path = f"{self.letsencrypt_dir}/live/{domain}/fullchain.pem"
            
            # Если сертификат не найден, проверяем варианты с суффиксами (-0001, -0002 и т.д.)
            if not os.path.exists(cert_path):
                # Ищем сертификаты с суффиксами
                live_dir = f"{self.letsencrypt_dir}/live"
                if os.path.exists(live_dir):
                    for item in os.listdir(live_dir):
                        if item.startswith(f"{domain}-"):
                            alt_cert_path = f"{live_dir}/{item}/fullchain.pem"
                            if os.path.exists(alt_cert_path):
                                logger.info(f"Найден сертификат в альтернативной директории: {item}")
                                cert_path = alt_cert_path
                                break
                
                if not os.path.exists(cert_path):
                    return {
                        "valid": False,
                        "exists": False,
                        "error": "Сертификат не найден"
                    }
            
            # Получаем информацию о сертификате
            cert_info = await self._parse_certificate_info(cert_path)
            
            # Проверяем, что парсинг прошел успешно
            if "not_after" not in cert_info:
                logger.error(f"Не удалось распарсить дату истечения сертификата для {domain}")
                return {
                    "valid": False,
                    "exists": True,
                    "error": "Ошибка парсинга сертификата: не найдена дата истечения"
                }
            
            # Проверяем срок действия
            now = datetime.now()
            days_until_expiry = (cert_info["not_after"] - now).days
            
            # Сертификат существует, но может быть истекшим
            # valid = True означает, что файл существует и может быть прочитан
            # needs_renewal = True означает, что нужно обновление (истек или скоро истечет)
            return {
                "valid": True,  # Файл существует и может быть прочитан
                "exists": True,
                "domain": domain,
                "issuer": cert_info.get("issuer", "Unknown"),
                "subject": cert_info.get("subject", "Unknown"),
                "not_before": cert_info["not_before"].isoformat(),
                "not_after": cert_info["not_after"].isoformat(),
                "days_until_expiry": days_until_expiry,
                "needs_renewal": days_until_expiry <= 30,
                "expired": days_until_expiry <= 0,
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
            # Пытаемся использовать systemctl напрямую
            result = await self._run_command(["systemctl", "stop", "nginx"])
            if result["success"]:
                return True
            
            # Если systemctl недоступен (в контейнере), пытаемся через docker exec на хосте
            # Проверяем, находимся ли мы в контейнере
            if os.path.exists("/.dockerenv"):
                # Используем docker exec для выполнения команды на хосте
                # Нужно определить имя контейнера или использовать host.docker.internal
                logger.warning("systemctl недоступен в контейнере, пропускаем остановку nginx")
                logger.info("Для standalone режима certbot nginx должен быть остановлен вручную на хосте")
                # В standalone режиме certbot сам займет порт 80, поэтому nginx должен быть остановлен
                # Но мы не можем это сделать из контейнера, поэтому просто пропускаем
                return True  # Возвращаем True, чтобы продолжить выполнение
            
            return False
        except Exception as e:
            logger.error(f"Error stopping nginx: {e}")
            # Если мы в контейнере, продолжаем выполнение
            if os.path.exists("/.dockerenv"):
                logger.warning("Продолжаем выполнение без остановки nginx (в контейнере)")
                return True
            return False
    
    async def _start_nginx(self) -> bool:
        """Запуск nginx"""
        try:
            # Пытаемся использовать systemctl напрямую
            result = await self._run_command(["systemctl", "start", "nginx"])
            if result["success"]:
                return True
            
            # Если systemctl недоступен (в контейнере), пропускаем
            if os.path.exists("/.dockerenv"):
                logger.warning("systemctl недоступен в контейнере, пропускаем запуск nginx")
                logger.info("Nginx должен быть запущен вручную на хосте после получения сертификата")
                return True  # Возвращаем True, чтобы продолжить выполнение
            
            return False
        except Exception as e:
            logger.error(f"Error starting nginx: {e}")
            # Если мы в контейнере, продолжаем выполнение
            if os.path.exists("/.dockerenv"):
                logger.warning("Продолжаем выполнение без запуска nginx (в контейнере)")
                return True
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
            
            # Если systemctl недоступен (в контейнере), возвращаем успех с предупреждением
            if not reload_result["success"] and os.path.exists("/.dockerenv"):
                logger.warning("systemctl недоступен в контейнере, nginx должен быть перезагружен вручную на хосте")
                return {
                    "success": True,
                    "warning": "Nginx должен быть перезагружен вручную на хосте"
                }
            
            return reload_result
            
        except Exception as e:
            logger.error(f"Error reloading nginx: {e}")
            # Если мы в контейнере, возвращаем успех с предупреждением
            if os.path.exists("/.dockerenv"):
                logger.warning("Продолжаем выполнение без перезагрузки nginx (в контейнере)")
                return {
                    "success": True,
                    "warning": "Nginx должен быть перезагружен вручную на хосте"
                }
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
            # Получаем домен из настроек
            domain = await self.settings_service.get_domain()
            if not domain or domain == "localhost:8001":
                return {
                    "needed": False,
                    "message": "Домен не настроен"
                }
            
            # Проверяем статус сертификата напрямую
            status = await self.check_certificate_status(domain)
            
            # Если сертификат не найден, проверяем наличие конфигурации renewal
            if not status.get("valid") or not status.get("exists"):
                config_exists = await self._check_renewal_config_exists(domain)
                
                if config_exists:
                    logger.info(f"Сертификат не найден, но есть конфигурация renewal для {domain}")
                    return {
                        "needed": True,
                        "message": "Сертификат не найден, но есть конфигурация renewal - попытка восстановления",
                        "next_renewal": datetime.now(),
                        "has_config": True
                    }
                else:
                    logger.warning(f"Сертификат не найден и нет конфигурации renewal для {domain}")
                    return {
                        "needed": True,
                        "message": "Сертификат не найден и нет конфигурации - требуется получение нового",
                        "next_renewal": datetime.now(),
                        "has_config": False
                    }
            
            # Проверяем срок действия
            days_until_expiry = status.get("days_until_expiry", 0)
            
            # Обновляем, если до истечения осталось 30 дней или меньше
            # Также обновляем, если сертификат уже истек (отрицательное значение)
            if days_until_expiry <= 30:
                return {
                    "needed": True,
                    "message": f"Сертификат истекает через {days_until_expiry} дней" if days_until_expiry > 0 else "Сертификат истек",
                    "days_until_expiry": days_until_expiry,
                    "next_renewal": datetime.now(),
                    "expired": days_until_expiry <= 0
                }
            else:
                return {
                    "needed": False,
                    "message": f"Сертификат действителен еще {days_until_expiry} дней",
                    "days_until_expiry": days_until_expiry,
                    "next_renewal": datetime.now() + timedelta(days=days_until_expiry - 30)
                }
                
        except Exception as e:
            logger.error(f"Error checking renewal needed: {e}")
            return {
                "needed": False,
                "error": f"Ошибка проверки обновления: {str(e)}"
            }
    
    async def _check_renewal_config_exists(self, domain: str) -> bool:
        """Проверка наличия конфигурации renewal для домена"""
        try:
            config_path = f"{self.letsencrypt_dir}/renewal/{domain}.conf"
            return os.path.exists(config_path)
        except Exception as e:
            logger.error(f"Error checking renewal config for {domain}: {e}")
            return False
    
    async def _get_certbot_config_params(self, domain: str) -> Dict[str, Any]:
        """Чтение параметров из конфигурации renewal"""
        try:
            config_path = f"{self.letsencrypt_dir}/renewal/{domain}.conf"
            
            if not os.path.exists(config_path):
                return {
                    "success": False,
                    "error": "Конфигурация renewal не найдена"
                }
            
            config = configparser.ConfigParser()
            config.read(config_path)
            
            params = {
                "success": True,
                "domains": [],
                "email": None,
                "authenticator": "standalone",
                "installer": None
            }
            
            # Читаем домены из секции [renewalparams]
            if "renewalparams" in config:
                if "domains" in config["renewalparams"]:
                    domains_str = config["renewalparams"]["domains"]
                    # Парсим формат: domain1, domain2, domain3
                    params["domains"] = [d.strip() for d in domains_str.split(",")]
                
                if "email" in config["renewalparams"]:
                    params["email"] = config["renewalparams"]["email"]
                
                if "authenticator" in config["renewalparams"]:
                    params["authenticator"] = config["renewalparams"]["authenticator"]
                
                # Читаем webroot_path, если указан
                if "webroot_path" in config["renewalparams"]:
                    params["webroot_path"] = config["renewalparams"]["webroot_path"].rstrip(",")
            
            # Также проверяем секцию [[webroot_map]] для получения webroot_path
            for section_name in config.sections():
                if section_name.startswith("webroot_map"):
                    for key, value in config[section_name].items():
                        if key == domain or key == f"www.{domain}":
                            params["webroot_path"] = value
                            break
            
            return params
            
        except Exception as e:
            logger.error(f"Error reading certbot config for {domain}: {e}")
            return {
                "success": False,
                "error": f"Ошибка чтения конфигурации: {str(e)}"
            }
    
    async def _run_certbot_renew(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """Запуск обновления сертификатов с fallback на certonly"""
        try:
            # Сначала пытаемся стандартное обновление
            cmd = [self.certbot_path, "renew", "--quiet"]
            result = await self._run_command(cmd)
            
            if result["success"]:
                # Проверяем, действительно ли что-то обновилось
                output = result["stdout"].lower()
                if "no renewals were attempted" in output or "no certs found" in output:
                    logger.warning("certbot renew не нашел сертификаты для обновления")
                    
                    # Если указан домен, пытаемся получить новый сертификат
                    if domain:
                        return await self._fallback_to_certonly(domain)
                    else:
                        return {
                            "success": False,
                            "error": "Сертификаты не найдены для обновления",
                            "details": result["stdout"]
                        }
                
                return {
                    "success": True,
                    "renewed": True,
                    "output": result["stdout"],
                    "method": "renew"
                }
            else:
                # Анализируем ошибку
                error_output = result["stderr"].lower()
                stdout_output = result["stdout"].lower()
                
                # Если сертификат не найден и есть домен, пытаемся получить новый
                if ("no certs found" in error_output or 
                    "certificate not found" in error_output or
                    "no such file" in error_output) and domain:
                    logger.info(f"Сертификат не найден для {domain}, пытаемся получить новый")
                    return await self._fallback_to_certonly(domain)
                
                # Если certbot renew не смог обновить из-за challenge failed, пробуем certonly
                if ("challenges have failed" in error_output or 
                    "some challenges have failed" in error_output or
                    "renewal failure" in error_output or
                    "failed to renew" in error_output) and domain:
                    logger.warning(f"certbot renew не смог обновить сертификат для {domain} из-за ошибки challenge, пробуем certonly")
                    return await self._fallback_to_certonly(domain)
                
                return {
                    "success": False,
                    "error": "Ошибка обновления сертификатов",
                    "details": result["stderr"],
                    "stdout": result["stdout"]
                }
                
        except Exception as e:
            logger.error(f"Error running certbot renew: {e}")
            
            # Если указан домен, пытаемся fallback
            if domain:
                return await self._fallback_to_certonly(domain)
            
            return {
                "success": False,
                "error": f"Ошибка обновления сертификатов: {str(e)}"
            }
    
    async def _fallback_to_certonly(self, domain: str) -> Dict[str, Any]:
        """Fallback: получение нового сертификата через certonly"""
        try:
            logger.info(f"Попытка получить новый сертификат для {domain} через certonly")
            
            # Проверяем наличие конфигурации renewal
            config_exists = await self._check_renewal_config_exists(domain)
            
            if config_exists:
                # Читаем параметры из конфигурации
                config_params = await self._get_certbot_config_params(domain)
                
                if config_params.get("success") and config_params.get("domains"):
                    domains = config_params["domains"]
                    email = config_params.get("email")
                    authenticator = config_params.get("authenticator", "standalone")
                else:
                    # Если не удалось прочитать конфигурацию, используем дефолтные значения
                    domains = [domain]
                    if not domain.startswith("www."):
                        domains.append(f"www.{domain}")
                    email = await self.settings_service.get_ssl_email()
                    authenticator = "standalone"
            else:
                # Конфигурации нет, используем дефолтные значения
                domains = [domain]
                if not domain.startswith("www."):
                    domains.append(f"www.{domain}")
                email = await self.settings_service.get_ssl_email()
                authenticator = "standalone"
            
            if not email:
                return {
                    "success": False,
                    "error": "Email для SSL не настроен, невозможно получить сертификат"
                }
            
            # Определяем приоритетный метод аутентификации
            # 1. Если в конфигурации renewal указан webroot - используем его
            # 2. Если webroot_path доступен - используем webroot
            # 3. Иначе используем nginx плагин или standalone
            use_webroot = False
            webroot_path = "/var/www/html"
            
            # Проверяем, указан ли webroot в конфигурации renewal
            if config_exists and config_params.get("success"):
                if config_params.get("authenticator") == "webroot":
                    use_webroot = True
                    # Пытаемся получить webroot_path из конфигурации
                    if "webroot_path" in config_params:
                        webroot_path = config_params["webroot_path"]
                    logger.info(f"Используем webroot из конфигурации renewal: {webroot_path}")
            
            # Если webroot не указан в конфигурации, проверяем доступность директории
            if not use_webroot:
                webroot_challenge_path = f"{webroot_path}/.well-known/acme-challenge"
                # Пытаемся создать директорию, если её нет
                try:
                    os.makedirs(webroot_challenge_path, exist_ok=True)
                    # Проверяем доступность через os.path.exists
                    if os.path.exists(webroot_challenge_path) and os.path.isdir(webroot_challenge_path):
                        use_webroot = True
                        logger.info(f"Webroot директория доступна: {webroot_challenge_path}")
                    else:
                        logger.warning(f"Webroot директория недоступна: {webroot_challenge_path}")
                except Exception as e:
                    logger.warning(f"Не удалось проверить/создать webroot директорию: {e}")
            
            use_nginx_plugin = False
            # Если webroot не используется и authenticator из конфигурации - standalone, пробуем nginx плагин
            if not use_webroot and authenticator == "standalone":
                # Проверяем, можем ли мы использовать nginx плагин
                # Если nginx запущен, лучше использовать nginx плагин
                nginx_check = await self._run_command(["nginx", "-t"])
                if nginx_check["success"]:
                    # Nginx доступен, пробуем использовать nginx плагин
                    logger.info("Nginx доступен, используем nginx плагин вместо standalone")
                    authenticator = "nginx"
                    use_nginx_plugin = True
                else:
                    # Nginx недоступен, используем standalone
                    # Но нужно остановить nginx на хосте вручную
                    logger.warning("Nginx недоступен или не настроен, используем standalone режим")
                    logger.warning("ВНИМАНИЕ: Для standalone режима nginx должен быть остановлен на хосте!")
                    await self._stop_nginx()  # Попытка остановить (может не сработать в контейнере)
            
            try:
                # Формируем команду certonly
                if use_webroot:
                    # Используем webroot плагин (не требует остановки nginx)
                    cmd = [
                        self.certbot_path,
                        "certonly",
                        "--webroot",
                        "--webroot-path", webroot_path,
                        "--email", email,
                        "--agree-tos",
                        "--no-eff-email",
                        "--domains", ",".join(domains),
                        "--non-interactive"
                    ]
                    logger.info(f"Выполняем certbot certonly с webroot плагином для доменов: {', '.join(domains)}")
                else:
                    cmd = [
                        self.certbot_path,
                        "certonly",
                        f"--{authenticator}",
                        "--email", email,
                        "--agree-tos",
                        "--no-eff-email",
                        "--domains", ",".join(domains),
                        "--non-interactive"
                    ]
                    
                    # Для nginx плагина не нужно останавливать nginx
                    if use_nginx_plugin:
                        logger.info(f"Выполняем certbot certonly с nginx плагином для доменов: {', '.join(domains)}")
                    else:
                        logger.info(f"Выполняем certbot certonly в standalone режиме для доменов: {', '.join(domains)}")
                        logger.warning("Убедитесь, что nginx остановлен на хосте для standalone режима!")
                
                result = await self._run_command(cmd)
                
                if result["success"]:
                    logger.info(f"Сертификат успешно получен для {domain}")
                    
                    # Проверяем, создан ли сертификат в новой директории (с суффиксом)
                    cert_path = await self._find_certificate_path(domain)
                    
                    # Обновляем конфигурацию nginx, если путь изменился
                    if cert_path:
                        await self._update_nginx_certificate_path(domain, cert_path)
                    
                    return {
                        "success": True,
                        "renewed": True,
                        "output": result["stdout"],
                        "method": "certonly",
                        "authenticator": "webroot" if use_webroot else authenticator,
                        "domains": domains,
                        "cert_path": cert_path
                    }
                else:
                    # Если webroot не сработал, пробуем nginx плагин, затем standalone
                    if use_webroot:
                        logger.info("Webroot режим не сработал, пробуем nginx плагин")
                        nginx_check = await self._run_command(["nginx", "-t"])
                        if nginx_check["success"]:
                            cmd_nginx = [
                                self.certbot_path,
                                "certonly",
                                "--nginx",
                                "--email", email,
                                "--agree-tos",
                                "--no-eff-email",
                                "--domains", ",".join(domains),
                                "--non-interactive"
                            ]
                            logger.info(f"Выполняем certbot certonly с nginx плагином для доменов: {', '.join(domains)}")
                            result_nginx = await self._run_command(cmd_nginx)
                            
                            if result_nginx["success"]:
                                logger.info(f"Сертификат успешно получен через nginx плагин для {domain}")
                                
                                # Проверяем путь сертификата и обновляем nginx
                                cert_path = await self._find_certificate_path(domain)
                                if cert_path:
                                    await self._update_nginx_certificate_path(domain, cert_path)
                                
                                return {
                                    "success": True,
                                    "renewed": True,
                                    "output": result_nginx["stdout"],
                                    "method": "certonly",
                                    "authenticator": "nginx",
                                    "domains": domains,
                                    "cert_path": cert_path
                                }
                    
                    # Если nginx плагин не сработал или недоступен, пробуем standalone
                    if authenticator == "standalone" and not use_nginx_plugin:
                        logger.info("Nginx плагин не сработал, пробуем standalone режим")
                        logger.warning("ВНИМАНИЕ: Для standalone режима nginx должен быть остановлен на хосте!")
                        await self._stop_nginx()
                        
                        cmd_standalone = [
                            self.certbot_path,
                            "certonly",
                            "--standalone",
                            "--email", email,
                            "--agree-tos",
                            "--no-eff-email",
                            "--domains", ",".join(domains),
                            "--non-interactive"
                        ]
                        logger.info(f"Выполняем certbot certonly в standalone режиме для доменов: {', '.join(domains)}")
                        result_standalone = await self._run_command(cmd_standalone)
                        
                        if result_standalone["success"]:
                            logger.info(f"Сертификат успешно получен через standalone режим для {domain}")
                            await self._start_nginx()
                            
                            # Проверяем путь сертификата и обновляем nginx
                            cert_path = await self._find_certificate_path(domain)
                            if cert_path:
                                await self._update_nginx_certificate_path(domain, cert_path)
                            
                            return {
                                "success": True,
                                "renewed": True,
                                "output": result_standalone["stdout"],
                                "method": "certonly",
                                "authenticator": "standalone",
                                "domains": domains,
                                "cert_path": cert_path
                            }
                        else:
                            await self._start_nginx()
                    
                    return {
                        "success": False,
                        "error": "Ошибка получения нового сертификата",
                        "details": result["stderr"],
                        "stdout": result["stdout"]
                    }
            finally:
                # Запускаем nginx обратно только если мы его останавливали для standalone
                if authenticator == "standalone" and not use_nginx_plugin and not use_webroot:
                    await self._start_nginx()
                    
        except Exception as e:
            logger.error(f"Error in fallback certonly for {domain}: {e}")
            return {
                "success": False,
                "error": f"Ошибка получения сертификата через certonly: {str(e)}"
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
                elif "Not Before" in line:
                    # Может быть "Not Before :" или "Not Before:"
                    if ":" in line:
                        date_str = line.split(":", 1)[1].strip()
                    else:
                        date_str = line.replace("Not Before", "").strip()
                    
                    try:
                        try:
                            cert_info["not_before"] = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
                        except ValueError:
                            cert_info["not_before"] = datetime.strptime(date_str, "%b %d %H:%M:%S %Y")
                    except Exception as e:
                        logger.warning(f"Ошибка парсинга даты Not Before: {date_str}, ошибка: {e}")
                elif "Not After" in line:
                    # Может быть "Not After :" или "Not After:"
                    if ":" in line:
                        date_str = line.split(":", 1)[1].strip()
                    else:
                        date_str = line.replace("Not After", "").strip()
                    
                    try:
                        try:
                            cert_info["not_after"] = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
                        except ValueError:
                            cert_info["not_after"] = datetime.strptime(date_str, "%b %d %H:%M:%S %Y")
                    except Exception as e:
                        logger.warning(f"Ошибка парсинга даты Not After: {date_str}, ошибка: {e}")
                elif line.startswith("Serial Number:"):
                    cert_info["serial_number"] = line.replace("Serial Number:", "").strip()
                elif line.startswith("Version:"):
                    cert_info["version"] = line.replace("Version:", "").strip()
            
            return cert_info
            
        except Exception as e:
            logger.error(f"Error parsing certificate info: {e}")
            raise
    
    async def _find_certificate_path(self, domain: str) -> Optional[str]:
        """Поиск пути к сертификату (включая варианты с суффиксами)"""
        try:
            # Проверяем основной путь
            cert_path = f"{self.letsencrypt_dir}/live/{domain}/fullchain.pem"
            if os.path.exists(cert_path):
                return cert_path
            
            # Ищем сертификаты с суффиксами (-0001, -0002 и т.д.)
            live_dir = f"{self.letsencrypt_dir}/live"
            if os.path.exists(live_dir):
                # Сортируем по имени в обратном порядке, чтобы получить самый новый
                items = sorted([item for item in os.listdir(live_dir) if item.startswith(f"{domain}-")], reverse=True)
                for item in items:
                    alt_cert_path = f"{live_dir}/{item}/fullchain.pem"
                    if os.path.exists(alt_cert_path):
                        logger.info(f"Найден сертификат в директории: {item}")
                        return alt_cert_path
            
            return None
        except Exception as e:
            logger.error(f"Error finding certificate path for {domain}: {e}")
            return None
    
    async def _update_nginx_certificate_path(self, domain: str, cert_path: str) -> bool:
        """Обновление пути к сертификату в конфигурации nginx"""
        try:
            # Извлекаем директорию из пути сертификата
            # Например: /etc/letsencrypt/live/staffprobot.ru-0001/fullchain.pem -> /etc/letsencrypt/live/staffprobot.ru-0001
            cert_dir = os.path.dirname(cert_path)
            
            # Находим конфигурационные файлы nginx
            nginx_config_paths = [
                "/etc/nginx/sites-enabled/staffprobot.conf",
                f"/etc/nginx/sites-enabled/{domain}.conf",
                "/etc/nginx/nginx.conf"
            ]
            
            updated = False
            for config_path in nginx_config_paths:
                if not os.path.exists(config_path):
                    continue
                
                # Читаем конфигурацию
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Заменяем старый путь на новый
                old_patterns = [
                    f"/etc/letsencrypt/live/{domain}/",
                    f"/etc/letsencrypt/live/{domain}-0001/",
                    f"/etc/letsencrypt/live/{domain}-0002/",
                ]
                
                new_content = content
                for old_pattern in old_patterns:
                    if old_pattern in content and old_pattern != cert_dir + "/":
                        new_content = new_content.replace(old_pattern, cert_dir + "/")
                        updated = True
                        logger.info(f"Обновлен путь к сертификату в {config_path}: {old_pattern} -> {cert_dir}/")
                
                # Сохраняем обновленную конфигурацию
                if updated:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    logger.info(f"Конфигурация nginx обновлена: {config_path}")
            
            # Перезагружаем nginx, если конфигурация была обновлена
            if updated:
                reload_result = await self._reload_nginx()
                if reload_result.get("success"):
                    logger.info("Nginx успешно перезагружен с новым путем к сертификату")
                else:
                    logger.warning(f"Nginx не был перезагружен автоматически: {reload_result.get('error', 'unknown error')}")
            
            return updated
            
        except Exception as e:
            logger.error(f"Error updating nginx certificate path for {domain}: {e}")
            return False
    
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
