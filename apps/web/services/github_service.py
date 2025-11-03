"""
Сервис для работы с GitHub Issues API.

Предоставляет:
- Создание issues из багов
- Получение списка issues по фильтрам
- Обновление статусов issues
"""
import httpx
from typing import List, Dict, Optional, Any
from core.config.settings import settings
from core.logging.logger import logger


class GitHubService:
    """Сервис для взаимодействия с GitHub API."""
    
    def __init__(self):
        self.token = getattr(settings, 'github_token', None)
        self.repo = getattr(settings, 'github_repo', 'OWNER/REPO')  # format: "owner/repo"
        self.base_url = "https://api.github.com"
        
        if not self.token:
            logger.warning("GitHub token not configured")
    
    async def create_issue(
        self,
        title: str,
        body: str,
        labels: List[str],
        assignees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Создание issue в GitHub.
        
        Args:
            title: Заголовок issue
            body: Описание issue
            labels: Список меток
            assignees: Список назначенных пользователей
        
        Returns:
            Dict с данными созданного issue
        
        Raises:
            httpx.HTTPError: При ошибке API
        """
        if not self.token:
            raise ValueError("GitHub token not configured")
        
        url = f"{self.base_url}/repos/{self.repo}/issues"
        
        payload = {
            "title": title,
            "body": body,
            "labels": labels
        }
        
        if assignees:
            payload["assignees"] = assignees
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"token {self.token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                
                issue_data = response.json()
                
                logger.info(
                    "GitHub issue created",
                    issue_number=issue_data['number'],
                    title=title,
                    labels=labels
                )
                
                return issue_data
        except httpx.HTTPError as e:
            logger.error(
                "Failed to create GitHub issue",
                error=str(e),
                title=title
            )
            raise
    
    async def get_issues(
        self,
        labels: Optional[List[str]] = None,
        state: str = "open",
        assignee: Optional[str] = None,
        since: Optional[str] = None,
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Получение списка issues по фильтрам.
        
        Args:
            labels: Фильтр по меткам (OR)
            state: Статус issues (open, closed, all)
            assignee: Фильтр по назначенному пользователю
            since: Фильтр по дате (ISO 8601 timestamp)
            per_page: Количество результатов на страницу
        
        Returns:
            List с данными issues
        """
        if not self.token:
            raise ValueError("GitHub token not configured")
        
        url = f"{self.base_url}/repos/{self.repo}/issues"
        
        params = {
            "state": state,
            "per_page": per_page
        }
        
        if labels:
            params["labels"] = ",".join(labels)
        
        if assignee:
            params["assignee"] = assignee
        
        if since:
            params["since"] = since
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    headers={
                        "Authorization": f"token {self.token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                
                issues = response.json()
                
                logger.info(
                    "GitHub issues fetched",
                    count=len(issues),
                    labels=labels,
                    state=state
                )
                
                return issues
        except httpx.HTTPError as e:
            logger.error(
                "Failed to fetch GitHub issues",
                error=str(e),
                labels=labels
            )
            raise
    
    async def update_issue(
        self,
        issue_number: int,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Обновление issue в GitHub.
        
        Args:
            issue_number: Номер issue
            state: Новый статус (open, closed)
            labels: Новый список меток
            assignees: Новый список назначенных
        
        Returns:
            Dict с обновлёнными данными issue
        """
        if not self.token:
            raise ValueError("GitHub token not configured")
        
        url = f"{self.base_url}/repos/{self.repo}/issues/{issue_number}"
        
        payload = {}
        
        if state:
            payload["state"] = state
        
        if labels:
            payload["labels"] = labels
        
        if assignees:
            payload["assignees"] = assignees
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"token {self.token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                
                issue_data = response.json()
                
                logger.info(
                    "GitHub issue updated",
                    issue_number=issue_number,
                    state=state
                )
                
                return issue_data
        except httpx.HTTPError as e:
            logger.error(
                "Failed to update GitHub issue",
                error=str(e),
                issue_number=issue_number
            )
            raise
    
    async def add_comment(
        self,
        issue_number: int,
        comment_body: str
    ) -> Dict[str, Any]:
        """
        Добавление комментария к issue.
        
        Args:
            issue_number: Номер issue
            comment_body: Текст комментария
        
        Returns:
            Dict с данными созданного комментария
        """
        if not self.token:
            raise ValueError("GitHub token not configured")
        
        url = f"{self.base_url}/repos/{self.repo}/issues/{issue_number}/comments"
        
        payload = {"body": comment_body}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"token {self.token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                
                comment_data = response.json()
                
                logger.info(
                    "GitHub comment added",
                    issue_number=issue_number
                )
                
                return comment_data
        except httpx.HTTPError as e:
            logger.error(
                "Failed to add GitHub comment",
                error=str(e),
                issue_number=issue_number
            )
            raise


# Глобальный экземпляр сервиса
github_service = GitHubService()

