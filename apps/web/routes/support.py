"""
Роуты веб-интерфейса поддержки сотрудников.

Предоставляет:
- Главную страницу Support Hub
- Форму отчета о баге
- FAQ базу знаний
- API для создания багов
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
import httpx

from core.database.session import get_db_session
from apps.web.middleware.auth_middleware import get_current_user
from apps.web.jinja import templates
from domain.entities.user import User
from domain.entities.bug_log import BugLog
from apps.web.services.github_service import github_service
from core.logging.logger import logger

router = APIRouter()


def get_base_template_for_role(user_role: str) -> str:
    """Определяет базовый шаблон в зависимости от роли пользователя."""
    if user_role == "superadmin":
        return "admin/base_admin.html"
    elif user_role == "owner":
        return "owner/base_owner.html"
    elif user_role == "manager":
        return "manager/base_manager.html"
    elif user_role == "moderator":
        return "base.html"
    else:
        return "employee/base_employee.html"


async def get_user_id_from_current_user(current_user, session):
    """Получает внутренний ID пользователя из current_user."""
    if isinstance(current_user, dict):
        telegram_id = current_user.get("telegram_id") or current_user.get("id")
        user_query = select(User).where(User.telegram_id == telegram_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        return user.id if user else None
    return current_user.id if hasattr(current_user, 'id') else None

# Временное хранилище для багов (до создания таблицы)
GITHUB_TOKEN = None  # TODO: Получить из settings
GITHUB_REPO = "OWNER/REPO"  # TODO: Получить из settings


@router.get("/", response_class=HTMLResponse)
async def support_hub(
    request: Request,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Главная страница Support Hub.
    
    Показывает:
    - Меню поддержки
    - Быстрый доступ к FAQ
    - Форму отчета о баге
    - Статус обращений пользователя
    """
    # Проверка авторизации
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=307)
    
    user_id = current_user.get("telegram_id")
    
    # Определяем базовый шаблон в зависимости от роли
    user_role = current_user.get("role", "employee")
    base_template = get_base_template_for_role(user_role)
    
    # Получаем статистику обращений пользователя
    # TODO: После создания таблицы bug_logs
    user_bugs_count = 0
    recent_bugs = []
    
    context = {
        "request": request,
        "current_user": current_user,
        "user_bugs_count": user_bugs_count,
        "recent_bugs": recent_bugs,
        "base_template": base_template,
        "user_role": user_role,
    }
    
    return templates.TemplateResponse("support/hub.html", context)


@router.get("/bug", response_class=HTMLResponse)
async def bug_form(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Форма отчета о баге.
    
    Поля:
    - Что делали
    - Что ожидали
    - Что получилось
    - Скриншот (опционально)
    - Приоритет
    """
    # Проверка авторизации
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=307)
    
    # Определяем базовый шаблон в зависимости от роли
    user_role = current_user.get("role", "employee")
    base_template = get_base_template_for_role(user_role)
    
    context = {
        "request": request,
        "current_user": current_user,
        "base_template": base_template,
        "user_role": user_role,
    }
    
    return templates.TemplateResponse("support/bug.html", context)


@router.post("/api/bug")
async def create_bug_report(
    request: Request,
    what_doing: str = Form(...),
    expected: str = Form(...),
    actual: str = Form(...),
    priority: str = Form(default="medium"),
    screenshot: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    API создания отчета о баге.
    
    После создания:
    1. Сохраняет в БД (bug_logs)
    2. Создает GitHub Issue
    3. Отправляет уведомление админу
    """
    # Проверка авторизации
    if not current_user:
        raise HTTPException(status_code=401, detail="Необходима авторизация")
    
    user_telegram_id = current_user.get("telegram_id")
    username = current_user.get("username", "Unknown")
    
    # Обработка скриншота
    screenshot_url = None
    if screenshot and screenshot.filename:
        # TODO: Сохранение в uploads/bugs/
        pass
    
    # Формирование тела Issue
    issue_body = f"""
## 🐛 Bug Report (from Web Interface)

**Reporter:** @{username} (Telegram ID: {user_telegram_id})
**Priority:** {priority}

### What was doing
{what_doing}

### Expected
{expected}

### Actual
{actual}

### Screenshot
{screenshot_url or 'No screenshot'}
"""
    
    # Получаем внутренний user_id из БД
    user_id = await get_user_id_from_current_user(current_user, session)
    
    # Сохранение в bug_logs
    bug_log = BugLog(
        user_id=user_id,
        title=f"Bug: {what_doing[:50]}",
        what_doing=what_doing,
        expected=expected,
        actual=actual,
        screenshot_url=screenshot_url,
        priority=priority,
        status='open'
    )
    session.add(bug_log)
    await session.commit()
    
    # Создание GitHub Issue через GitHubService
    try:
        issue = await github_service.create_issue(
            title=f"Bug: {what_doing[:50]}",
            body=issue_body,
            labels=["bug", "from-web", f"priority-{priority}", "needs-triage"]
        )
        # Обновляем bug_log с номером issue
        bug_log.github_issue_number = issue['number']
        await session.commit()
    except Exception as e:
        logger.error("Failed to create GitHub issue", error=str(e))
        # Продолжаем, даже если GitHub недоступен
    
    logger.info(
        "Bug report created via web",
        user_id=user_id,
        priority=priority,
        github_issue=bug_log.github_issue_number
    )
    
    # Редирект на страницу успеха
    return RedirectResponse(
        url="/support?success=bug_created",
        status_code=303
    )


@router.get("/faq", response_class=HTMLResponse)
async def faq_page(
    request: Request,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    База знаний FAQ.
    
    Показывает:
    - Категории вопросов
    - Список часто задаваемых вопросов
    - Поиск по вопросам
    """
    # Проверка авторизации
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=307)
    
    # TODO: Получение из faq_entries
    faq_categories = {
        "shifts": {
            "title": "Смены",
            "questions": [
                {
                    "q": "Как открыть смену?",
                    "a": "Нажмите кнопку 'Открыть смену' в боте или на сайте, затем отправьте вашу геолокацию. Система проверит, что вы находитесь на объекте."
                },
                {
                    "q": "Как закрыть смену?",
                    "a": "Нажмите 'Закрыть смену'. Система автоматически рассчитает отработанное время и добавит его в табель."
                },
                {
                    "q": "Что делать, если забыл закрыть смену?",
                    "a": "Обратитесь к менеджеру или владельцу для ручного закрытия смены. В будущем система будет автоматически закрывать смены через 24 часа."
                }
            ]
        },
        "salary": {
            "title": "Зарплата и расчеты",
            "questions": [
                {
                    "q": "Когда начисляется зарплата?",
                    "a": "Расчеты производятся автоматически после закрытия смены. Итоговая зарплата доступна в личном кабинете."
                },
                {
                    "q": "Как рассчитываются штрафы?",
                    "a": "Штрафы применяются согласно вашему договору. Вы можете увидеть список активных штрафов в разделе 'Мой договор'."
                }
            ]
        },
        "technical": {
            "title": "Технические вопросы",
            "questions": [
                {
                    "q": "Не работает геолокация",
                    "a": "Убедитесь, что вы разрешили приложению доступ к геолокации в настройках телефона. Проверьте также, что GPS включен."
                },
                {
                    "q": "Бот не отвечает",
                    "a": "Попробуйте отправить команду /start. Если проблема сохраняется, обратитесь в поддержку через эту форму."
                }
            ]
        }
    }
    
    # Фильтрация по категории
    if category:
        faq_data = {category: faq_categories.get(category, {})}
    else:
        faq_data = faq_categories
    
    # Определяем базовый шаблон в зависимости от роли
    user_role = current_user.get("role", "employee")
    base_template = get_base_template_for_role(user_role)
    
    context = {
        "request": request,
        "current_user": current_user,
        "faq_data": faq_data,
        "selected_category": category,
        "base_template": base_template,
        "user_role": user_role,
    }
    
    return templates.TemplateResponse("support/faq.html", context)


@router.get("/my-bugs", response_class=HTMLResponse)
async def my_bugs(
    request: Request,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Страница с обращениями пользователя.
    
    Показывает список всех багов, созданных текущим пользователем.
    """
    # Проверка авторизации
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=307)
    
    # Получаем внутренний user_id
    user_id = await get_user_id_from_current_user(current_user, session)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=307)
    
    # Получаем все баги пользователя
    result = await session.execute(
        select(BugLog)
        .where(BugLog.user_id == user_id)
        .order_by(BugLog.created_at.desc())
    )
    bugs = result.scalars().all()
    
    # Преобразуем в словари для JSON сериализации
    bugs_dict = []
    for bug in bugs:
        bugs_dict.append({
            "id": bug.id,
            "title": bug.title,
            "what_doing": bug.what_doing,
            "expected": bug.expected,
            "actual": bug.actual,
            "priority": bug.priority,
            "status": bug.status,
            "screenshot_url": bug.screenshot_url,
            "github_issue_number": bug.github_issue_number,
            "created_at": bug.created_at.isoformat() if bug.created_at else None,
            "resolved_at": bug.resolved_at.isoformat() if bug.resolved_at else None
        })
    
    # Определяем базовый шаблон в зависимости от роли
    user_role = current_user.get("role", "employee")
    base_template = get_base_template_for_role(user_role)
    
    context = {
        "request": request,
        "current_user": current_user,
        "bugs": bugs,
        "bugs_json": bugs_dict,
        "base_template": base_template,
        "user_role": user_role,
    }
    
    return templates.TemplateResponse("support/my_bugs.html", context)


@router.get("/api/search", response_class=HTMLResponse)
async def search_faq(
    q: str,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Поиск по FAQ.
    
    Возвращает JSON с релевантными вопросами.
    """
    # TODO: Полнотекстовый поиск по faq_entries
    results = []
    
    return {"results": results, "query": q}

