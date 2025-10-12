"""Email отправщик уведомлений для StaffProBot."""

import smtplib
import ssl
from typing import Optional, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

from core.logging.logger import logger
from core.config.settings import settings
from domain.entities.notification import (
    Notification,
    NotificationType,
    NotificationPriority
)
from shared.templates.notifications import NotificationTemplateManager


class EmailNotificationSender:
    """Отправщик уведомлений через Email (SMTP)."""
    
    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_from_email: Optional[str] = None,
        smtp_from_name: Optional[str] = None
    ):
        """
        Инициализация отправщика.
        
        Args:
            smtp_host: SMTP хост (опционально, из settings)
            smtp_port: SMTP порт (опционально, из settings)
            smtp_user: SMTP пользователь (опционально, из settings)
            smtp_password: SMTP пароль (опционально, из settings)
            smtp_from_email: Email отправителя (опционально, из settings)
            smtp_from_name: Имя отправителя (опционально, из settings)
        """
        self.smtp_host = smtp_host or settings.smtp_host
        self.smtp_port = smtp_port or settings.smtp_port
        self.smtp_user = smtp_user or settings.smtp_user
        self.smtp_password = smtp_password or settings.smtp_password
        self.smtp_from_email = smtp_from_email or settings.smtp_from_email or self.smtp_user
        self.smtp_from_name = smtp_from_name or settings.smtp_from_name
        self.smtp_use_tls = settings.smtp_use_tls
        self.smtp_use_ssl = settings.smtp_use_ssl
        self.smtp_timeout = settings.smtp_timeout
        
        self.max_retries = 3
        self.retry_delay = 2  # секунды
        
        # Проверка конфигурации
        if not all([self.smtp_host, self.smtp_user, self.smtp_password, self.smtp_from_email]):
            logger.warning("Email sender not fully configured (missing SMTP credentials)")
    
    async def send_notification(
        self,
        notification: Notification,
        to_email: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Отправка уведомления по Email.
        
        Args:
            notification: Объект уведомления
            to_email: Email получателя
            variables: Переменные для шаблона (опционально)
            
        Returns:
            True если отправлено успешно
        """
        try:
            # Проверка конфигурации
            if not self._is_configured():
                logger.error("Email sender is not configured")
                return False
            
            # Подготавливаем переменные для шаблона
            template_vars = variables or notification.data or {}
            
            # Рендерим шаблон
            rendered = NotificationTemplateManager.render(
                notification_type=notification.type,
                channel=notification.channel,
                variables=template_vars
            )
            
            # Создаем email сообщение
            message = self._create_email_message(
                notification=notification,
                to_email=to_email,
                subject=rendered["title"],
                html_content=rendered["message"]
            )
            
            # Отправляем с повторными попытками
            success = await self._send_with_retry(
                to_email=to_email,
                message=message,
                notification=notification
            )
            
            if success:
                logger.info(
                    f"Email notification sent successfully",
                    notification_id=notification.id,
                    to_email=to_email,
                    type=notification.type.value
                )
            else:
                logger.error(
                    f"Failed to send email notification",
                    notification_id=notification.id,
                    to_email=to_email,
                    type=notification.type.value
                )
            
            return success
            
        except Exception as e:
            logger.error(
                f"Error sending email notification: {e}",
                notification_id=notification.id,
                to_email=to_email,
                error=str(e)
            )
            return False
    
    def _create_email_message(
        self,
        notification: Notification,
        to_email: str,
        subject: str,
        html_content: str
    ) -> MIMEMultipart:
        """
        Создание email сообщения.
        
        Args:
            notification: Объект уведомления
            to_email: Email получателя
            subject: Тема письма
            html_content: HTML контент
            
        Returns:
            MIME сообщение
        """
        # Создаем multipart сообщение
        message = MIMEMultipart("alternative")
        message["Subject"] = self._format_subject(notification, subject)
        message["From"] = f"{self.smtp_from_name} <{self.smtp_from_email}>"
        message["To"] = to_email
        
        # Добавляем приоритет для срочных уведомлений
        if notification.priority == NotificationPriority.URGENT:
            message["X-Priority"] = "1"
            message["Importance"] = "high"
        elif notification.priority == NotificationPriority.HIGH:
            message["X-Priority"] = "2"
            message["Importance"] = "high"
        
        # Создаем plain text версию из HTML
        plain_text = self._html_to_plain(html_content)
        
        # Прикрепляем обе версии
        part_plain = MIMEText(plain_text, "plain", "utf-8")
        part_html = MIMEText(self._wrap_html(html_content, subject), "html", "utf-8")
        
        message.attach(part_plain)
        message.attach(part_html)
        
        return message
    
    def _format_subject(self, notification: Notification, subject: str) -> str:
        """
        Форматирование темы письма.
        
        Args:
            notification: Объект уведомления
            subject: Базовая тема
            
        Returns:
            Отформатированная тема
        """
        # Добавляем префикс для срочных
        if notification.priority == NotificationPriority.URGENT:
            return f"🚨 СРОЧНО: {subject}"
        elif notification.priority == NotificationPriority.HIGH:
            return f"⚡ Важно: {subject}"
        
        return subject
    
    def _html_to_plain(self, html: str) -> str:
        """
        Конвертация HTML в plain text (упрощенно).
        
        Args:
            html: HTML контент
            
        Returns:
            Plain text
        """
        import re
        
        # Удаляем HTML теги
        text = re.sub(r'<br\s*/?>', '\n', html)
        text = re.sub(r'<p.*?>', '\n', text)
        text = re.sub(r'</p>', '\n', text)
        text = re.sub(r'<h\d.*?>', '\n=== ', text)
        text = re.sub(r'</h\d>', ' ===\n', text)
        text = re.sub(r'<strong>(.*?)</strong>', r'\1', text)
        text = re.sub(r'<b>(.*?)</b>', r'\1', text)
        text = re.sub(r'<i>(.*?)</i>', r'\1', text)
        text = re.sub(r'<.*?>', '', text)
        
        # Убираем лишние переносы
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()
        
        return text
    
    def _wrap_html(self, content: str, title: str) -> str:
        """
        Обертка HTML контента в email шаблон.
        
        Args:
            content: HTML контент
            title: Заголовок
            
        Returns:
            Полный HTML документ
        """
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: #ffffff;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1, h2 {{
            color: #2c3e50;
            margin-top: 0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #666;
            text-align: center;
        }}
        strong {{
            color: #2c3e50;
        }}
        code {{
            background-color: #f0f0f0;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        {content}
        <div class="footer">
            <p>Это автоматическое уведомление от <strong>StaffProBot</strong></p>
            <p>Пожалуйста, не отвечайте на это письмо</p>
        </div>
    </div>
</body>
</html>
"""
    
    async def _send_with_retry(
        self,
        to_email: str,
        message: MIMEMultipart,
        notification: Notification
    ) -> bool:
        """
        Отправка email с повторными попытками.
        
        Args:
            to_email: Email получателя
            message: MIME сообщение
            notification: Объект уведомления
            
        Returns:
            True если отправлено успешно
        """
        import asyncio
        
        for attempt in range(self.max_retries):
            try:
                # Подключаемся к SMTP серверу
                if self.smtp_use_ssl:
                    context = ssl.create_default_context()
                    server = smtplib.SMTP_SSL(
                        self.smtp_host,
                        self.smtp_port,
                        timeout=self.smtp_timeout,
                        context=context
                    )
                else:
                    server = smtplib.SMTP(
                        self.smtp_host,
                        self.smtp_port,
                        timeout=self.smtp_timeout
                    )
                    
                    if self.smtp_use_tls:
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                
                # Логинимся
                server.login(self.smtp_user, self.smtp_password)
                
                # Отправляем
                server.send_message(message)
                
                # Закрываем соединение
                server.quit()
                
                return True
                
            except smtplib.SMTPAuthenticationError as e:
                # Ошибка аутентификации - не повторяем
                logger.error(
                    f"SMTP authentication failed",
                    smtp_user=self.smtp_user,
                    notification_id=notification.id,
                    error=str(e)
                )
                return False
                
            except smtplib.SMTPRecipientsRefused as e:
                # Получатель отклонен - не повторяем
                logger.error(
                    f"SMTP recipient refused",
                    to_email=to_email,
                    notification_id=notification.id,
                    error=str(e)
                )
                return False
                
            except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError) as e:
                # Проблемы с соединением - повторяем
                logger.warning(
                    f"SMTP connection error, attempt {attempt + 1}/{self.max_retries}",
                    notification_id=notification.id,
                    error=str(e)
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    return False
                    
            except Exception as e:
                # Другая ошибка
                logger.error(
                    f"Unexpected error sending email",
                    to_email=to_email,
                    notification_id=notification.id,
                    error=str(e)
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    return False
        
        return False
    
    def _is_configured(self) -> bool:
        """
        Проверка наличия конфигурации.
        
        Returns:
            True если сконфигурирован
        """
        return all([
            self.smtp_host,
            self.smtp_user,
            self.smtp_password,
            self.smtp_from_email
        ])
    
    async def test_connection(self) -> bool:
        """
        Проверка подключения к SMTP серверу.
        
        Returns:
            True если подключение работает
        """
        try:
            if not self._is_configured():
                logger.error("Email sender is not configured")
                return False
            
            # Подключаемся к серверу
            if self.smtp_use_ssl:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(
                    self.smtp_host,
                    self.smtp_port,
                    timeout=self.smtp_timeout,
                    context=context
                )
            else:
                server = smtplib.SMTP(
                    self.smtp_host,
                    self.smtp_port,
                    timeout=self.smtp_timeout
                )
                
                if self.smtp_use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
            
            # Логинимся
            server.login(self.smtp_user, self.smtp_password)
            
            # Закрываем
            server.quit()
            
            logger.info(f"Email SMTP connection successful: {self.smtp_host}:{self.smtp_port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {e}", error=str(e))
            return False


# Глобальный экземпляр отправщика
_email_sender: Optional[EmailNotificationSender] = None


def get_email_sender() -> EmailNotificationSender:
    """
    Получение глобального экземпляра Email отправщика.
    
    Returns:
        Экземпляр EmailNotificationSender
    """
    global _email_sender
    
    if _email_sender is None:
        _email_sender = EmailNotificationSender()
    
    return _email_sender

