"""
ChromaDB клиент для хранения векторных данных (адаптирован под chromadb 0.5.x)
"""
import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.api import ClientAPI
import yaml

logger = logging.getLogger(__name__)


class ChromaClient:
    """Асинхронная обёртка над синхронным chromadb.HttpClient."""

    def __init__(self, host: str = "chromadb", port: int = 8000) -> None:
        self.host = host
        self.port = port
        self.client: Optional[ClientAPI] = None
        self.collection = None
        self._default_collection_name = "project_brain"

    async def initialize(self) -> None:
        """Инициализация ChromaDB клиента."""
        try:
            self.client = chromadb.HttpClient(host=self.host, port=self.port)
            self.collection = await asyncio.to_thread(
                self.client.get_or_create_collection,
                name=self._default_collection_name,
                metadata={"description": "Knowledge base"},
            )
            logger.info("ChromaDB клиент инициализирован успешно")
        except Exception as error:
            logger.error("Ошибка инициализации ChromaDB: %s", error, exc_info=True)
            raise

    async def store_chunks(self, project: str, chunks: List[Dict[str, Any]]) -> None:
        """Сохранение чанков в ChromaDB."""
        if not chunks:
            return

        if self.collection is None:
            raise RuntimeError("ChromaDB коллекция не инициализирована")

        try:
            embeddings: List[List[float]] = []
            documents: List[str] = []
            metadatas: List[Dict[str, Any]] = []
            ids: List[str] = []

            for chunk in chunks:
                embedding = [0.0] * 384  # TODO: заменить на реальные эмбеддинги
                embeddings.append(embedding)
                documents.append(chunk["content"])

                metadata: Dict[str, Any] = {
                    "project": project,
                    "file": chunk.get("file", ""),
                    "lines": chunk.get("lines", ""),
                    "type": chunk.get("type", ""),
                    "chunk_id": chunk.get("chunk_id", 0),
                }
                if "class_name" in chunk:
                    metadata["class_name"] = chunk["class_name"]
                if "function_name" in chunk:
                    metadata["function_name"] = chunk["function_name"]
                if "section" in chunk:
                    metadata["section"] = chunk["section"]

                metadatas.append(metadata)
                ids.append(f"{project}_{chunk.get('file', '')}_{chunk.get('chunk_id', 0)}")

            await asyncio.to_thread(
                self.collection.add,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )

            logger.info("Сохранено %s чанков для проекта %s", len(chunks), project)
        except Exception as error:
            logger.error("Ошибка при сохранении чанков: %s", error, exc_info=True)
            raise

    async def get_project_config(self, project: str) -> Optional[Dict[str, Any]]:
        """Получение конфигурации проекта."""
        try:
            config_path = "config/projects.yaml"
            if not os.path.exists(config_path):
                return None

            with open(config_path, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file)

            projects = config.get("projects", [])
            return next((item for item in projects if item["name"] == project), None)
        except Exception as error:
            logger.error(
                "Ошибка получения конфигурации проекта %s: %s", project, error, exc_info=True
            )
            return None

    async def get_project_stats(self, project: str) -> Dict[str, Any]:
        """Получение статистики проекта."""
        try:
            collection = await self._get_project_collection(project)
            total_chunks = await asyncio.to_thread(collection.count)

            metadatas_result = await asyncio.to_thread(
                collection.get,
                ids=None,
                include=["metadatas"],
            )
            metadatas = metadatas_result.get("metadatas", []) or []

            files = {metadata.get("file") for metadata in metadatas if metadata and metadata.get("file")}
            file_types: Dict[str, int] = {}
            for metadata in metadatas:
                if not metadata:
                    continue
                file_type = metadata.get("type")
                if file_type:
                    file_types[file_type] = file_types.get(file_type, 0) + 1

            return {
                "total_chunks": total_chunks,
                "total_files": len(files),
                "file_types": file_types,
                "last_indexed": None,
            }
        except Exception as error:
            logger.error(
                "Ошибка получения статистики проекта %s: %s", project, error, exc_info=True
            )
            return {"total_chunks": 0, "total_files": 0, "file_types": {}}

    async def get_global_stats(self) -> Dict[str, Any]:
        """Получение глобальной статистики по всем коллекциям."""
        if self.client is None:
            raise RuntimeError("ChromaDB клиент не инициализирован")

        try:
            collections = await asyncio.to_thread(self.client.list_collections)
            total_chunks = 0
            total_projects = 0

            for collection in collections:
                count = await asyncio.to_thread(collection.count)
                total_chunks += count
                if collection.name.startswith("kb_"):
                    total_projects += 1

            return {
                "total_chunks": total_chunks,
                "total_projects": total_projects,
                "total_files": 0,
                "storage_size": 0,
                "last_updated": None,
            }
        except Exception as error:
            logger.error("Ошибка получения глобальной статистики: %s", error, exc_info=True)
            return {"total_chunks": 0, "total_projects": 0, "total_files": 0}

    async def _get_project_collection(self, project: str):
        if self.client is None:
            raise RuntimeError("ChromaDB клиент не инициализирован")

        collection_name = self._make_collection_name(project)
        return await asyncio.to_thread(
            self.client.get_or_create_collection,
            name=collection_name,
            metadata={"description": f"Knowledge base for {project}"},
        )

    @staticmethod
    def _make_collection_name(project: str) -> str:
        return f"kb_{project.replace('-', '_')}"
