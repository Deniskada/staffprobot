#!/usr/bin/env python3
"""
Project Brain - Python Client для Cursor
Использование: python ask_brain.py "Ваш вопрос"
"""
import sys
import requests
import json
from typing import Dict, Any

BRAIN_URL = "http://192.168.2.107:8003/api/query"
PROJECT = "staffprobot"

# Цвета для терминала
class Colors:
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

def ask_brain(query: str) -> Dict[str, Any]:
    """Отправка запроса в Project Brain"""
    try:
        response = requests.post(
            BRAIN_URL,
            json={"query": query, "project": PROJECT},
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"{Colors.RED}❌ Ошибка подключения: {e}{Colors.NC}")
        print(f"\n{Colors.YELLOW}Проверьте, что API запущен:{Colors.NC}")
        print("  docker compose -f docker-compose.local.yml ps")
        sys.exit(1)

def print_answer(data: Dict[str, Any]):
    """Красивый вывод ответа"""
    answer = data.get('answer', '')
    sources = data.get('sources', [])
    processing_time = data.get('processing_time', 0)
    
    if not answer:
        print(f"{Colors.YELLOW}⚠️  Не удалось получить ответ{Colors.NC}")
        print(f"\nОтвет API:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    
    # Выводим ответ
    print(f"\n{Colors.GREEN}{answer}{Colors.NC}")
    print()
    
    # Выводим статистику
    print(f"{Colors.BLUE}📚 Использовано источников: {len(sources)}{Colors.NC}")
    print(f"{Colors.BLUE}⏱️  Время обработки: {processing_time:.2f}s{Colors.NC}")
    
    # Выводим топ-3 источника
    if sources and len(sources) > 0:
        print(f"\n{Colors.BOLD}🔝 Топ-3 источника:{Colors.NC}")
        for i, source in enumerate(sources[:3], 1):
            file = source.get('file', 'unknown')
            lines = source.get('lines', '?')
            score = source.get('score', 0)
            print(f"  {i}. {file} (строки {lines}) - score: {score:.2f}")

def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print(f"{Colors.YELLOW}Использование: {sys.argv[0]} \"Ваш вопрос\"{Colors.NC}")
        print()
        print("Примеры:")
        print(f"  python {sys.argv[0]} \"Где функция start_shift?\"")
        print(f"  python {sys.argv[0]} \"API endpoint для создания объекта\"")
        print(f"  python {sys.argv[0]} \"Поля модели User\"")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    
    print(f"{Colors.BLUE}🤖 Спрашиваю Project Brain...{Colors.NC}")
    
    # Отправляем запрос
    result = ask_brain(query)
    
    # Выводим ответ
    print_answer(result)

if __name__ == "__main__":
    main()

