#!/usr/bin/env python3
"""
Упрощённая диагностика проблем с лендингом (без внешних зависимостей)
"""

import urllib.request
import urllib.error
import json
import sys
import subprocess
import os
from datetime import datetime

class SimpleLandingDiagnostic:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'base_url': base_url,
            'issues': [],
            'checks': {}
        }
    
    def check_static_files(self):
        """Проверка загрузки статических файлов"""
        print("🔍 Проверяю статические файлы...")
        
        static_files = [
            '/static/css/main.css',
            '/static/js/main.js'
        ]
        
        for file_path in static_files:
            url = f"{self.base_url}{file_path}"
            try:
                with urllib.request.urlopen(url, timeout=10) as response:
                    if response.status == 200:
                        content = response.read()
                        self.results['checks'][f'static_{file_path}'] = {
                            'status': 'OK',
                            'size': len(content),
                            'content_type': response.headers.get('content-type', 'unknown')
                        }
                    else:
                        self.results['issues'].append(f"Статический файл {file_path} недоступен: {response.status}")
            except urllib.error.HTTPError as e:
                self.results['issues'].append(f"Статический файл {file_path} недоступен: HTTP {e.code}")
            except Exception as e:
                self.results['issues'].append(f"Ошибка загрузки {file_path}: {str(e)}")
    
    def check_landing_page(self):
        """Проверка главной страницы"""
        print("🏠 Проверяю главную страницу...")
        
        try:
            with urllib.request.urlopen(self.base_url, timeout=10) as response:
                if response.status == 200:
                    html_content = response.read().decode('utf-8')
                    
                    # Проверяем наличие ключевых элементов
                    checks = {
                        'has_landing_title': 'StaffProBot - Умное управление персоналом' in html_content,
                        'has_bootstrap_css': 'bootstrap.min.css' in html_content,
                        'has_bootstrap_icons': 'bootstrap-icons' in html_content,
                        'has_google_fonts': 'fonts.googleapis.com' in html_content,
                        'has_custom_css': 'main.css' in html_content,
                        'has_hero_section': 'hero-section' in html_content,
                        'has_entry_cards': 'entry-card' in html_content,
                        'has_gradients': 'gradient' in html_content.lower()
                    }
                    
                    self.results['checks']['landing_page'] = {
                        'status': 'OK',
                        'size': len(html_content),
                        'content_checks': checks
                    }
                    
                    # Проверяем проблемы
                    if not checks['has_bootstrap_css']:
                        self.results['issues'].append("Bootstrap CSS не найден в HTML")
                    if not checks['has_custom_css']:
                        self.results['issues'].append("Custom CSS (main.css) не найден в HTML")
                    if not checks['has_hero_section']:
                        self.results['issues'].append("Hero секция не найдена")
                    if not checks['has_entry_cards']:
                        self.results['issues'].append("Карточки входа не найдены")
                        
                else:
                    self.results['issues'].append(f"Главная страница недоступна: {response.status}")
        except Exception as e:
            self.results['issues'].append(f"Ошибка загрузки главной страницы: {str(e)}")
    
    def check_docker_containers(self):
        """Проверка Docker контейнеров"""
        print("🐳 Проверяю Docker контейнеры...")
        
        try:
            result = subprocess.run(['docker', 'ps', '--format', 'json'], 
                                 capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                containers = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        containers.append(json.loads(line))
                
                web_containers = [c for c in containers if 'staffprobot' in c.get('Names', '') and 'web' in c.get('Names', '')]
                
                if web_containers:
                    container = web_containers[0]
                    self.results['checks']['docker_web'] = {
                        'status': 'OK',
                        'container_id': container['ID'],
                        'state': container['State'],
                        'status': container['Status']
                    }
                else:
                    self.results['issues'].append("Web контейнер не найден")
            else:
                self.results['issues'].append("Не удалось получить список контейнеров")
                
        except Exception as e:
            self.results['issues'].append(f"Ошибка проверки Docker: {str(e)}")
    
    def check_nginx_config(self):
        """Проверка конфигурации Nginx"""
        print("⚙️ Проверяю конфигурацию Nginx...")
        
        nginx_configs = [
            '/etc/nginx/sites-available/staffprobot',
            '/etc/nginx/conf.d/staffprobot.conf',
            '/etc/nginx/nginx.conf'
        ]
        
        for config_path in nginx_configs:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        content = f.read()
                        
                    # Проверяем наличие location для статических файлов
                    has_static_location = 'location /static/' in content
                    has_css_mime = 'text/css' in content
                    
                    self.results['checks']['nginx_config'] = {
                        'status': 'OK',
                        'config_path': config_path,
                        'has_static_location': has_static_location,
                        'has_css_mime': has_css_mime
                    }
                    
                    if not has_static_location:
                        self.results['issues'].append("Nginx: не найден location /static/")
                    if not has_css_mime:
                        self.results['issues'].append("Nginx: не настроен MIME тип для CSS")
                        
                    break
                except Exception as e:
                    self.results['issues'].append(f"Ошибка чтения конфигурации Nginx: {str(e)}")
        else:
            self.results['issues'].append("Конфигурация Nginx не найдена")
    
    def generate_report(self):
        """Генерация отчёта"""
        print("\n" + "="*60)
        print("📊 ДИАГНОСТИЧЕСКИЙ ОТЧЁТ")
        print("="*60)
        
        print(f"🌐 URL: {self.base_url}")
        print(f"⏰ Время: {self.results['timestamp']}")
        print(f"❌ Проблем найдено: {len(self.results['issues'])}")
        
        if self.results['issues']:
            print("\n🚨 ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ:")
            for i, issue in enumerate(self.results['issues'], 1):
                print(f"  {i}. {issue}")
        else:
            print("\n✅ Критических проблем не найдено")
        
        print("\n📋 ДЕТАЛЬНЫЕ ПРОВЕРКИ:")
        for check_name, check_data in self.results['checks'].items():
            status_icon = "✅" if check_data.get('status') == 'OK' else "❌"
            print(f"  {status_icon} {check_name}: {check_data.get('status', 'UNKNOWN')}")
        
        # Сохраняем отчёт в файл
        report_file = f"landing_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Полный отчёт сохранён в: {report_file}")
        
        return self.results

def main():
    if len(sys.argv) != 2:
        print("Использование: python3 simple_diagnose.py <URL>")
        print("Пример: python3 simple_diagnose.py https://staffprobot.ru")
        sys.exit(1)
    
    base_url = sys.argv[1]
    diagnostic = SimpleLandingDiagnostic(base_url)
    
    print(f"🔍 Запускаю диагностику для {base_url}")
    print("⏳ Это может занять несколько минут...\n")
    
    # Выполняем все проверки
    diagnostic.check_landing_page()
    diagnostic.check_static_files()
    diagnostic.check_docker_containers()
    diagnostic.check_nginx_config()
    
    # Генерируем отчёт
    results = diagnostic.generate_report()
    
    # Возвращаем код выхода
    if results['issues']:
        print(f"\n⚠️  Найдено {len(results['issues'])} проблем")
        sys.exit(1)
    else:
        print("\n🎉 Все проверки пройдены успешно!")
        sys.exit(0)

if __name__ == "__main__":
    main()
