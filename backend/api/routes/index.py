"""
API роуты для индексации проектов
"""
import asyncio
import logging
import time
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ...indexers.simple_project_indexer import SimpleProjectIndexer
from ...indexers.python_indexer import PythonIndexer
from ...indexers.markdown_indexer import MarkdownIndexer
from ...rag.engine import RAGEngine

router = APIRouter()
logger = logging.getLogger(__name__)


class IndexResponse(BaseModel):
    status: str
    project: str
    message: str


# Глобальные экземпляры
project_indexer = SimpleProjectIndexer()
python_indexer = PythonIndexer()
markdown_indexer = MarkdownIndexer()
rag_engine = None


async def get_rag_engine():
    """Получение RAG engine"""
    global rag_engine
    if rag_engine is None:
        rag_engine = RAGEngine()
        await rag_engine.initialize()
    return rag_engine


async def index_project_background(project_name: str):
    """Фоновая индексация проекта (потоковая обработка)"""
    try:
        logger.info(f"=== Начало индексации: {project_name} ===")
        start_time = time.time()

        # Получение RAG engine
        rag = await get_rag_engine()

        # Получаем список уже проиндексированных файлов
        # ВАЖНО: НЕ используем collection.get() - это медленно и виснет
        # Вместо этого просто пытаемся добавить, ChromaDB сам отбросит дубли по ID
        indexed_files = set()  # Оставляем пустым - не проверяем заранее
        logger.info(
            "📊 Начинаем индексацию без предварительной проверки (дубли отбросит ChromaDB)"
        )

        stats = {
            "total_files": 0,
            "python_files": 0,
            "markdown_files": 0,
            "total_chunks": 0,
            "errors": 0,
        }

        # Потоковая обработка файлов
        logger.info(f"🚀 Индексация проекта {project_name}")
        async for file_info in project_indexer.iter_project_files(project_name):
            try:
                file_path = file_info["file_path"]
                file_type = file_info["file_type"]
                relative_path = file_info["relative_path"]

                stats["total_files"] += 1

                # Индексация файла
                chunks = []
                if file_type == "python":
                    chunks = await python_indexer.index_file(file_path)
                    stats["python_files"] += 1
                elif file_type == "markdown":
                    chunks = await markdown_indexer.index_file(file_path)
                    stats["markdown_files"] += 1

                # Загрузка чанков в ChromaDB
                for chunk in chunks:
                    try:
                        # Классификация типа документа
                        doc_type = (
                            python_indexer._classify_doc_type(relative_path)
                            if file_type == "python"
                            else "documentation"
                        )

                        await rag.store_document(
                            project=project_name,
                            content=chunk["content"],
                            metadata={
                                "file": relative_path,
                                "type": chunk["type"],
                                "doc_type": doc_type,
                                "start_line": chunk.get("start_line", 0),
                                "end_line": chunk.get("end_line", 0),
                                "lines": chunk.get(
                                    "lines",
                                    f"{chunk.get('start_line', 0)}-{chunk.get('end_line', 0)}",
                                ),
                                "project": project_name,
                                "chunk_id": chunk.get(
                                    "chunk_id", hash(chunk["content"][:100])
                                ),
                            },
                        )
                        stats["total_chunks"] += 1
                    except Exception as error:
                        stats["errors"] += 1
                        logger.error("Ошибка загрузки чанка: %s", error)

                # Логируем прогресс
                if stats["total_files"] % 50 == 0:
                    logger.info(
                        "📊 Обработано: %s файлов, %s чанков, %s ошибок",
                        stats["total_files"],
                        stats["total_chunks"],
                        stats["errors"],
                    )

            except Exception as error:
                stats["errors"] += 1
                logger.error(
                    "Ошибка обработки файла %s: %s",
                    file_info.get("relative_path", "unknown"),
                    error,
                )

        processing_time = time.time() - start_time

        logger.info(f"=== Индексация завершена за {processing_time:.2f}с ===")
        logger.info(
            "📊 Статистика: файлов=%s, чанков=%s, ошибок=%s",
            stats["total_files"],
            stats["total_chunks"],
            stats["errors"],
        )

    except Exception as error:
        logger.error("❌ Критическая ошибка индексации: %s", error, exc_info=True)


@router.post("/index/{project_name}", response_model=IndexResponse)
async def index_project(project_name: str, background_tasks: BackgroundTasks):
    """
    Индексация проекта в фоновом режиме
    """
    try:
        # Проверка, что проект существует
        project_indexer.load_config()
        project_names = [p["name"] for p in project_indexer.projects]

        if project_name not in project_names:
            raise HTTPException(
                status_code=404,
                detail=f"Проект {project_name} не найден. Доступные: {project_names}",
            )

        # Запуск фоновой задачи
        background_tasks.add_task(index_project_background, project_name)

        return IndexResponse(
            status="started",
            project=project_name,
            message=(
                f"Индексация проекта {project_name} запущена в фоновом режиме. "
                "Проверяйте логи Docker."
            ),
        )

    except HTTPException:
        raise
    except Exception as error:
        logger.error("Ошибка запуска индексации: %s", error)
        raise HTTPException(status_code=500, detail=str(error))


@router.get("/index/status/{project_name}")
async def get_index_status(project_name: str):
    """
    Получение статуса индексации проекта
    """
    try:
        rag = await get_rag_engine()

        collection = rag.get_collection(project_name)
        count = await asyncio.to_thread(collection.count)

        return {
            "project": project_name,
            "total_documents": count,
            "status": "indexed" if count > 0 else "empty",
            "message": f"В базе {count} документов",
        }

    except Exception as error:
        logger.error("Ошибка получения статуса: %s", error)
        raise HTTPException(status_code=500, detail=str(error))
