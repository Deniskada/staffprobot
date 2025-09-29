"""
Простой тестовый роут для отладки страницы управляющего
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory=".")

@router.get("/simple-manager-test", response_class=HTMLResponse)
async def simple_manager_test(request: Request):
    """Простая тестовая страница для отладки"""
    with open("simple_manager_test.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)
