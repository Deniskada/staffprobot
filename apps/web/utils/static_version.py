"""
Утилиты для версионирования статических файлов
"""
import os
import hashlib
from pathlib import Path
from typing import Optional


def get_static_file_version(file_path: str) -> str:
    """
    Получает версию статического файла на основе времени модификации и содержимого
    
    Args:
        file_path: Путь к статическому файлу относительно static/
        
    Returns:
        Версия файла в формате timestamp_hash
    """
    static_dir = Path(__file__).parent.parent / "static"
    full_path = static_dir / file_path
    
    if not full_path.exists():
        return "1"
    
    # Получаем время модификации
    mtime = full_path.stat().st_mtime
    timestamp = int(mtime)
    
    # Получаем хэш содержимого файла
    with open(full_path, 'rb') as f:
        content_hash = hashlib.md5(f.read()).hexdigest()[:8]
    
    return f"{timestamp}_{content_hash}"


def get_static_url_with_version(file_path: str, base_url: str = "/static/") -> str:
    """
    Генерирует URL статического файла с версией
    
    Args:
        file_path: Путь к статическому файлу относительно static/
        base_url: Базовый URL для статических файлов
        
    Returns:
        URL с версией
    """
    version = get_static_file_version(file_path)
    return f"{base_url}{file_path}?v={version}"
