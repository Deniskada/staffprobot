"""Сервис экспорта отчетов в различные форматы."""

import io
import os
from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from core.logging.logger import logger


class ExportService:
    """Сервис для экспорта отчетов в PDF и Excel."""
    
    def __init__(self):
        """Инициализация сервиса."""
        self._setup_fonts()
        logger.info("ExportService initialized")
    
    def _setup_fonts(self):
        """Настройка шрифтов для PDF."""
        try:
            # Попытка загрузить шрифт с поддержкой кириллицы
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
                pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
            else:
                logger.warning("DejaVu fonts not found, using default fonts")
        except Exception as e:
            logger.warning(f"Failed to setup custom fonts: {e}")
    
    def export_object_report_to_pdf(self, report_data: Dict[str, Any]) -> bytes:
        """
        Экспортирует отчет по объекту в PDF.
        
        Args:
            report_data: Данные отчета
            
        Returns:
            PDF файл в виде байтов
        """
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            
            # Создаем кастомные стили
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=1  # Центрирование
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=12,
                spaceAfter=12
            )
            
            story = []
            
            # Заголовок
            title = f"Отчет по объекту: {report_data['object']['name']}"
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 12))
            
            # Информация об объекте
            story.append(Paragraph("Информация об объекте", heading_style))
            object_info = [
                ["Название", report_data['object']['name']],
                ["Адрес", report_data['object']['address'] or "Не указан"],
                ["Время работы", report_data['object']['working_hours']],
                ["Ставка за час", f"{report_data['object']['hourly_rate']} ₽"]
            ]
            
            object_table = Table(object_info, colWidths=[2*inch, 3*inch])
            object_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(object_table)
            story.append(Spacer(1, 20))
            
            # Период отчета
            story.append(Paragraph("Период отчета", heading_style))
            period_info = [
                ["Начальная дата", report_data['period']['start_date']],
                ["Конечная дата", report_data['period']['end_date']],
                ["Количество дней", str(report_data['period']['days'])]
            ]
            
            period_table = Table(period_info, colWidths=[2*inch, 3*inch])
            period_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(period_table)
            story.append(Spacer(1, 20))
            
            # Общая статистика
            story.append(Paragraph("Общая статистика", heading_style))
            summary = report_data['summary']
            summary_data = [
                ["Показатель", "Значение"],
                ["Всего смен", str(summary['total_shifts'])],
                ["Завершенных смен", str(summary['completed_shifts'])],
                ["Активных смен", str(summary['active_shifts'])],
                ["Общее время (часов)", f"{summary['total_hours']} ч"],
                ["Общая оплата", f"{summary['total_payment']} ₽"],
                ["Средняя длительность смены", f"{summary['avg_shift_duration']} ч"],
                ["Среднее время в день", f"{summary['avg_daily_hours']} ч"]
            ]
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 20))
            
            # Статистика по сотрудникам
            if report_data.get('employees'):
                story.append(Paragraph("Статистика по сотрудникам", heading_style))
                employee_data = [["Сотрудник", "Смены", "Часы", "Оплата"]]
                for emp in report_data['employees']:
                    employee_data.append([
                        emp['name'],
                        str(emp['shifts']),
                        f"{emp['hours']} ч",
                        f"{emp['payment']} ₽"
                    ])
                
                employee_table = Table(employee_data, colWidths=[2*inch, 1*inch, 1*inch, 1.5*inch])
                employee_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(employee_table)
            
            # Генерируем PDF
            doc.build(story)
            buffer.seek(0)
            
            logger.info("Object report PDF generated successfully")
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}")
            raise
    
    def export_personal_report_to_pdf(self, report_data: Dict[str, Any]) -> bytes:
        """
        Экспортирует персональный отчет в PDF.
        
        Args:
            report_data: Данные отчета
            
        Returns:
            PDF файл в виде байтов
        """
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=1
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=12,
                spaceAfter=12
            )
            
            story = []
            
            # Заголовок
            title = f"Персональный отчет: {report_data['user']['name']}"
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 12))
            
            # Информация о сотруднике
            story.append(Paragraph("Информация о сотруднике", heading_style))
            user_info = [
                ["Имя", report_data['user']['name']],
                ["Username", report_data['user']['username'] or "Не указан"],
                ["Telegram ID", str(report_data['user']['telegram_id'])]
            ]
            
            user_table = Table(user_info, colWidths=[2*inch, 3*inch])
            user_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(user_table)
            story.append(Spacer(1, 20))
            
            # Общая статистика
            story.append(Paragraph("Общая статистика", heading_style))
            summary = report_data['summary']
            summary_data = [
                ["Показатель", "Значение"],
                ["Всего смен", str(summary['total_shifts'])],
                ["Завершенных смен", str(summary['completed_shifts'])],
                ["Активных смен", str(summary['active_shifts'])],
                ["Общее время (часов)", f"{summary['total_hours']} ч"],
                ["Общий заработок", f"{summary['total_earnings']} ₽"],
                ["Средняя длительность смены", f"{summary['avg_shift_duration']} ч"],
                ["Средний заработок в день", f"{summary['avg_daily_earnings']} ₽"]
            ]
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 20))
            
            # Последние смены
            if report_data.get('recent_shifts'):
                story.append(Paragraph("Последние смены", heading_style))
                shift_data = [["Дата", "Объект", "Время", "Часы", "Оплата", "Статус"]]
                for shift in report_data['recent_shifts'][:15]:  # Ограничиваем для PDF
                    shift_data.append([
                        shift['date'],
                        shift['object_name'][:20] + "..." if len(shift['object_name']) > 20 else shift['object_name'],
                        f"{shift['start_time']}-{shift['end_time']}",
                        f"{shift['duration_hours']} ч",
                        f"{shift['payment']} ₽",
                        shift['status']
                    ])
                
                shift_table = Table(shift_data, colWidths=[0.8*inch, 1.5*inch, 1*inch, 0.8*inch, 1*inch, 0.9*inch])
                shift_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(shift_table)
            
            # Генерируем PDF
            doc.build(story)
            buffer.seek(0)
            
            logger.info("Personal report PDF generated successfully")
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating personal PDF report: {e}")
            raise
    
    def export_object_report_to_excel(self, report_data: Dict[str, Any]) -> bytes:
        """
        Экспортирует отчет по объекту в Excel.
        
        Args:
            report_data: Данные отчета
            
        Returns:
            Excel файл в виде байтов
        """
        try:
            buffer = io.BytesIO()
            
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                # Лист с общей информацией
                summary_data = {
                    'Показатель': [
                        'Название объекта',
                        'Адрес',
                        'Время работы',
                        'Ставка за час',
                        'Период (начало)',
                        'Период (конец)',
                        'Всего смен',
                        'Завершенных смен',
                        'Активных смен',
                        'Общее время (часов)',
                        'Общая оплата (₽)',
                        'Средняя длительность смены (ч)',
                        'Среднее время в день (ч)'
                    ],
                    'Значение': [
                        report_data['object']['name'],
                        report_data['object']['address'] or 'Не указан',
                        report_data['object']['working_hours'],
                        f"{report_data['object']['hourly_rate']} ₽",
                        report_data['period']['start_date'],
                        report_data['period']['end_date'],
                        report_data['summary']['total_shifts'],
                        report_data['summary']['completed_shifts'],
                        report_data['summary']['active_shifts'],
                        report_data['summary']['total_hours'],
                        report_data['summary']['total_payment'],
                        report_data['summary']['avg_shift_duration'],
                        report_data['summary']['avg_daily_hours']
                    ]
                }
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Общая информация', index=False)
                
                # Лист с данными по сотрудникам
                if report_data.get('employees'):
                    employees_df = pd.DataFrame(report_data['employees'])
                    employees_df.to_excel(writer, sheet_name='Сотрудники', index=False)
                
                # Лист с ежедневной статистикой
                if report_data.get('daily_breakdown'):
                    daily_df = pd.DataFrame(report_data['daily_breakdown'])
                    daily_df.to_excel(writer, sheet_name='По дням', index=False)
            
            buffer.seek(0)
            logger.info("Object report Excel generated successfully")
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating Excel report: {e}")
            raise
    
    def export_personal_report_to_excel(self, report_data: Dict[str, Any]) -> bytes:
        """
        Экспортирует персональный отчет в Excel.
        
        Args:
            report_data: Данные отчета
            
        Returns:
            Excel файл в виде байтов
        """
        try:
            buffer = io.BytesIO()
            
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                # Лист с общей информацией
                summary_data = {
                    'Показатель': [
                        'Имя сотрудника',
                        'Username',
                        'Telegram ID',
                        'Период (начало)',
                        'Период (конец)',
                        'Всего смен',
                        'Завершенных смен',
                        'Активных смен',
                        'Общее время (часов)',
                        'Общий заработок (₽)',
                        'Средняя длительность смены (ч)',
                        'Средний заработок в день (₽)'
                    ],
                    'Значение': [
                        report_data['user']['name'],
                        report_data['user']['username'] or 'Не указан',
                        report_data['user']['telegram_id'],
                        report_data['period']['start_date'],
                        report_data['period']['end_date'],
                        report_data['summary']['total_shifts'],
                        report_data['summary']['completed_shifts'],
                        report_data['summary']['active_shifts'],
                        report_data['summary']['total_hours'],
                        report_data['summary']['total_earnings'],
                        report_data['summary']['avg_shift_duration'],
                        report_data['summary']['avg_daily_earnings']
                    ]
                }
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Общая информация', index=False)
                
                # Лист с данными по объектам
                if report_data.get('objects'):
                    objects_df = pd.DataFrame(report_data['objects'])
                    objects_df.to_excel(writer, sheet_name='По объектам', index=False)
                
                # Лист с последними сменами
                if report_data.get('recent_shifts'):
                    shifts_df = pd.DataFrame(report_data['recent_shifts'])
                    shifts_df.to_excel(writer, sheet_name='Последние смены', index=False)
            
            buffer.seek(0)
            logger.info("Personal report Excel generated successfully")
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating personal Excel report: {e}")
            raise
