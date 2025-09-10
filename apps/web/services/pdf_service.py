"""
Сервис для генерации PDF документов
"""

import os
import tempfile
from typing import Dict, Any, Optional
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import html2text
import re

from core.logging.logger import logger
from domain.entities.contract import Contract


class PDFService:
    """Сервис для генерации PDF документов."""
    
    def __init__(self):
        self.setup_fonts()
        
    def setup_fonts(self):
        """Настройка шрифтов для поддержки русского языка."""
        try:
            # Попытка использовать системные шрифты
            font_paths = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                '/System/Library/Fonts/Helvetica.ttc',
                'C:\\Windows\\Fonts\\arial.ttf',
            ]
            
            font_registered = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
                        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', font_path))
                        logger.info(f"Registered font from: {font_path}")
                        font_registered = True
                        break
                    except Exception as e:
                        logger.warning(f"Failed to register font {font_path}: {e}")
                        continue
            
            if not font_registered:
                logger.warning("No suitable font found, using default")
                # Регистрируем встроенный шрифт как fallback
                try:
                    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
                    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
                    logger.info("Registered fallback Unicode font")
                except Exception as e:
                    logger.warning(f"Failed to register fallback font: {e}")
                
        except Exception as e:
            logger.error(f"Error setting up fonts: {e}")
    
    async def generate_contract_pdf(
        self, 
        contract: Contract,
        content: Optional[str] = None
    ) -> bytes:
        """Генерация PDF договора."""
        try:
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                temp_filename = tmp_file.name
            
            # Создаем PDF документ
            doc = SimpleDocTemplate(
                temp_filename,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # Стили
            styles = getSampleStyleSheet()
            
            # Определяем доступный шрифт
            available_fonts = pdfmetrics.getRegisteredFontNames()
            font_name = 'DejaVuSans' if 'DejaVuSans' in available_fonts else 'STSong-Light' if 'STSong-Light' in available_fonts else 'Helvetica'
            
            # Создаем кастомные стили с поддержкой русского языка
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=20,
                alignment=TA_CENTER,
                fontName=font_name
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=12,
                alignment=TA_LEFT,
                fontName=font_name
            )
            
            # Контент документа
            story = []
            
            # Заголовок
            title = f"ДОГОВОР № {contract.contract_number}"
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 20))
            
            # Информация о договоре
            contract_info = f"""
            <b>Название:</b> {contract.title}<br/>
            <b>Дата заключения:</b> {contract.start_date.strftime('%d.%m.%Y')}<br/>
            """
            
            if contract.end_date:
                contract_info += f"<b>Дата окончания:</b> {contract.end_date.strftime('%d.%m.%Y')}<br/>"
            
            if contract.hourly_rate:
                contract_info += f"<b>Почасовая ставка:</b> {contract.hourly_rate} ₽<br/>"
            
            story.append(Paragraph(contract_info, normal_style))
            story.append(Spacer(1, 20))
            
            # Основное содержание
            contract_content = content or contract.content or "Содержание договора не указано"
            
            # Конвертируем HTML в обычный текст, если необходимо
            if '<' in contract_content and '>' in contract_content:
                # Простая обработка HTML тегов
                contract_content = self._process_html_content(contract_content)
            
            # Разбиваем на абзацы
            paragraphs = contract_content.split('\n')
            for paragraph in paragraphs:
                if paragraph.strip():
                    story.append(Paragraph(paragraph.strip(), normal_style))
                else:
                    story.append(Spacer(1, 6))
            
            story.append(Spacer(1, 30))
            
            # Подписи
            signature_info = """
            <b>Стороны договора:</b><br/><br/>
            Заказчик: ___________________________<br/>
            <br/>
            Исполнитель: ________________________<br/>
            <br/>
            Дата: _______________
            """
            
            story.append(Paragraph(signature_info, normal_style))
            
            # Генерируем PDF
            doc.build(story)
            
            # Читаем файл в память
            with open(temp_filename, 'rb') as f:
                pdf_data = f.read()
            
            # Удаляем временный файл
            os.unlink(temp_filename)
            
            logger.info(f"Generated PDF for contract: {contract.id}")
            return pdf_data
            
        except Exception as e:
            logger.error(f"Error generating PDF for contract {contract.id}: {e}")
            raise
    
    def _process_html_content(self, content: str) -> str:
        """Обработка HTML контента для PDF."""
        try:
            # Заменяем основные HTML теги на ReportLab разметку
            content = content.replace('<br>', '<br/>')
            content = content.replace('<br/>', '\n')
            content = re.sub(r'<p[^>]*>', '', content)
            content = content.replace('</p>', '\n\n')
            content = re.sub(r'<div[^>]*>', '', content)
            content = content.replace('</div>', '\n')
            
            # Обрабатываем жирный текст
            content = re.sub(r'<b[^>]*>(.*?)</b>', r'<b>\1</b>', content)
            content = re.sub(r'<strong[^>]*>(.*?)</strong>', r'<b>\1</b>', content)
            
            # Обрабатываем курсив
            content = re.sub(r'<i[^>]*>(.*?)</i>', r'<i>\1</i>', content)
            content = re.sub(r'<em[^>]*>(.*?)</em>', r'<i>\1</i>', content)
            
            # Удаляем остальные HTML теги
            content = re.sub(r'<[^>]+>', '', content)
            
            # Очищаем лишние переносы
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
            content = content.strip()
            
            return content
            
        except Exception as e:
            logger.error(f"Error processing HTML content: {e}")
            return content
