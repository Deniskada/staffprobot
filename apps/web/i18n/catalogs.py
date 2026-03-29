from typing import Dict


CATALOGS: Dict[str, Dict[str, str]] = {
    "ru": {
        "menu.home": "Главная",
        "menu.objects": "Объекты",
        "menu.employees": "Сотрудники",
        "profile.theme": "Тема интерфейса",
        "profile.language": "Язык интерфейса",
        "profile.industry": "Отрасль",
    }
}


def t(key: str, language: str = "ru", fallback: str = "") -> str:
    lang = language if language in CATALOGS else "ru"
    return CATALOGS.get(lang, {}).get(key, fallback or key)
