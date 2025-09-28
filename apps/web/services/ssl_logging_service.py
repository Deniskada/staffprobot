import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from core.logging.logger import logger
from core.cache.redis_cache import cache
from pathlib import Path
import os

class SSLLoggingService:
    """Сервис логирования операций с SSL"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.log_dir = Path("logs/ssl")
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    async def log_ssl_operation(
        self, 
        operation: str, 
        domain: str, 
        status: str, 
        details: Dict[str, Any] = None,
        error: str = None
    ) -> None:
        """
        Логирует операцию с SSL
        """
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "domain": domain,
                "status": status,
                "details": details or {},
                "error": error
            }
            
            # Записываем в файл
            await self._write_to_file(log_entry)
            
            # Сохраняем в Redis для быстрого доступа
            await self._cache_log_entry(log_entry)
            
            # Логируем в основной логгер
            if status == "success":
                logger.info(f"SSL operation {operation} completed successfully for domain {domain}")
            elif status == "error":
                logger.error(f"SSL operation {operation} failed for domain {domain}: {error}")
            else:
                logger.warning(f"SSL operation {operation} completed with status {status} for domain {domain}")
                
        except Exception as e:
            logger.error(f"Failed to log SSL operation: {e}")
    
    async def _write_to_file(self, log_entry: Dict[str, Any]) -> None:
        """Записывает лог в файл"""
        try:
            # Создаем файл с датой
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = self.log_dir / f"ssl_operations_{date_str}.log"
            
            # Добавляем запись в файл
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                
        except Exception as e:
            logger.error(f"Failed to write SSL log to file: {e}")
    
    async def _cache_log_entry(self, log_entry: Dict[str, Any]) -> None:
        """Кэширует лог в Redis"""
        try:
            # Добавляем в список последних операций
            cache_key = f"ssl_logs:{log_entry['domain']}"
            await cache.lpush(cache_key, json.dumps(log_entry))
            
            # Ограничиваем количество записей в кэше (последние 100)
            await cache.ltrim(cache_key, 0, 99)
            
            # Устанавливаем время жизни кэша (7 дней)
            await cache.expire(cache_key, 604800)
            
        except Exception as e:
            logger.error(f"Failed to cache SSL log entry: {e}")
    
    async def get_ssl_logs(
        self, 
        domain: str = None, 
        operation: str = None, 
        status: str = None,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Получает логи SSL операций с фильтрацией
        """
        try:
            logs = []
            
            # Получаем логи из файлов за указанный период
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                log_file = self.log_dir / f"ssl_operations_{date_str}.log"
                
                if log_file.exists():
                    with open(log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            try:
                                log_entry = json.loads(line.strip())
                                
                                # Применяем фильтры
                                if domain and log_entry.get("domain") != domain:
                                    continue
                                if operation and log_entry.get("operation") != operation:
                                    continue
                                if status and log_entry.get("status") != status:
                                    continue
                                
                                logs.append(log_entry)
                            except json.JSONDecodeError:
                                continue
                
                current_date += timedelta(days=1)
            
            # Сортируем по времени (новые сверху)
            logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get SSL logs: {e}")
            return []
    
    async def get_ssl_statistics(self, domain: str = None, days: int = 30) -> Dict[str, Any]:
        """
        Получает статистику по SSL операциям
        """
        try:
            logs = await self.get_ssl_logs(domain=domain, days=days)
            
            # Подсчитываем статистику
            total_operations = len(logs)
            successful_operations = len([log for log in logs if log.get("status") == "success"])
            failed_operations = len([log for log in logs if log.get("status") == "error"])
            warning_operations = len([log for log in logs if log.get("status") == "warning"])
            
            # Группируем по операциям
            operations_count = {}
            for log in logs:
                op = log.get("operation", "unknown")
                operations_count[op] = operations_count.get(op, 0) + 1
            
            # Группируем по доменам
            domains_count = {}
            for log in logs:
                dom = log.get("domain", "unknown")
                domains_count[dom] = domains_count.get(dom, 0) + 1
            
            # Статистика по дням
            daily_stats = {}
            for log in logs:
                timestamp = log.get("timestamp", "")
                if timestamp:
                    date = timestamp.split("T")[0]
                    if date not in daily_stats:
                        daily_stats[date] = {"total": 0, "success": 0, "error": 0, "warning": 0}
                    
                    daily_stats[date]["total"] += 1
                    status = log.get("status", "unknown")
                    if status in daily_stats[date]:
                        daily_stats[date][status] += 1
            
            return {
                "period_days": days,
                "total_operations": total_operations,
                "successful_operations": successful_operations,
                "failed_operations": failed_operations,
                "warning_operations": warning_operations,
                "success_rate": (successful_operations / total_operations * 100) if total_operations > 0 else 0,
                "operations_breakdown": operations_count,
                "domains_breakdown": domains_count,
                "daily_statistics": daily_stats,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get SSL statistics: {e}")
            return {
                "period_days": days,
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "warning_operations": 0,
                "success_rate": 0,
                "operations_breakdown": {},
                "domains_breakdown": {},
                "daily_statistics": {},
                "last_updated": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def get_recent_ssl_errors(self, domain: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает последние ошибки SSL
        """
        try:
            logs = await self.get_ssl_logs(domain=domain, status="error", days=7)
            return logs[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get recent SSL errors: {e}")
            return []
    
    async def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """
        Очищает старые логи SSL
        """
        try:
            deleted_count = 0
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            for log_file in self.log_dir.glob("ssl_operations_*.log"):
                # Извлекаем дату из имени файла
                try:
                    date_str = log_file.stem.replace("ssl_operations_", "")
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    if file_date < cutoff_date:
                        log_file.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old SSL log file: {log_file}")
                        
                except ValueError:
                    # Если не можем распарсить дату, пропускаем файл
                    continue
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old SSL logs: {e}")
            return 0
    
    async def export_ssl_logs(
        self, 
        domain: str = None, 
        days: int = 7, 
        format: str = "json"
    ) -> str:
        """
        Экспортирует логи SSL в указанном формате
        """
        try:
            logs = await self.get_ssl_logs(domain=domain, days=days)
            
            if format == "json":
                return json.dumps(logs, ensure_ascii=False, indent=2)
            elif format == "csv":
                import csv
                import io
                
                output = io.StringIO()
                if logs:
                    writer = csv.DictWriter(output, fieldnames=logs[0].keys())
                    writer.writeheader()
                    writer.writerows(logs)
                return output.getvalue()
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Failed to export SSL logs: {e}")
            return ""
