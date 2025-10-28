"""Юнит-тесты для Media Orchestrator."""

import pytest
from shared.services.media_orchestrator import MediaOrchestrator, MediaFlowConfig


@pytest.mark.asyncio
async def test_begin_and_get_flow():
    """Тест создания и получения медиа-потока."""
    orchestrator = MediaOrchestrator()
    
    cfg = MediaFlowConfig(
        user_id=123,
        context_type="task_v2_proof",
        context_id=456,
        require_photo=True,
        max_photos=3
    )
    
    await orchestrator.begin_flow(cfg)
    
    # Получаем поток
    retrieved = await orchestrator.get_flow(123)
    
    assert retrieved is not None
    assert retrieved.user_id == 123
    assert retrieved.context_type == "task_v2_proof"
    assert retrieved.context_id == 456
    assert retrieved.max_photos == 3
    
    await orchestrator.close()


@pytest.mark.asyncio
async def test_add_photo():
    """Тест добавления фото в поток."""
    orchestrator = MediaOrchestrator()
    
    cfg = MediaFlowConfig(
        user_id=123,
        context_type="test",
        context_id=1,
        max_photos=2
    )
    
    await orchestrator.begin_flow(cfg)
    
    # Добавляем фото
    success1 = await orchestrator.add_photo(123, "file_id_1")
    success2 = await orchestrator.add_photo(123, "file_id_2")
    success3 = await orchestrator.add_photo(123, "file_id_3")  # Превышение лимита
    
    assert success1 is True
    assert success2 is True
    assert success3 is False  # Лимит 2 фото
    
    # Проверяем содержимое
    retrieved = await orchestrator.get_flow(123)
    assert len(retrieved.collected_photos) == 2
    
    await orchestrator.close()


@pytest.mark.asyncio
async def test_is_flow_complete():
    """Тест проверки завершённости потока."""
    orchestrator = MediaOrchestrator()
    
    # Поток требует текст И фото
    cfg = MediaFlowConfig(
        user_id=123,
        context_type="test",
        context_id=1,
        require_text=True,
        require_photo=True
    )
    
    await orchestrator.begin_flow(cfg)
    
    # Поток не завершён
    assert await orchestrator.is_flow_complete(123) is False
    
    # Добавляем текст
    await orchestrator.add_text(123, "Описание")
    assert await orchestrator.is_flow_complete(123) is False  # Всё ещё нет фото
    
    # Добавляем фото
    await orchestrator.add_photo(123, "file_id_1")
    assert await orchestrator.is_flow_complete(123) is True  # Теперь всё есть
    
    await orchestrator.close()


@pytest.mark.asyncio
async def test_finish_flow():
    """Тест завершения потока."""
    orchestrator = MediaOrchestrator()
    
    cfg = MediaFlowConfig(
        user_id=123,
        context_type="test",
        context_id=1
    )
    
    await orchestrator.begin_flow(cfg)
    await orchestrator.add_text(123, "Test text")
    
    # Завершаем поток
    final = await orchestrator.finish(123)
    
    assert final is not None
    assert final.collected_text == "Test text"
    
    # Поток удалён
    retrieved = await orchestrator.get_flow(123)
    assert retrieved is None
    
    await orchestrator.close()


@pytest.mark.asyncio
async def test_cancel_flow():
    """Тест отмены потока."""
    orchestrator = MediaOrchestrator()
    
    cfg = MediaFlowConfig(
        user_id=123,
        context_type="test",
        context_id=1
    )
    
    await orchestrator.begin_flow(cfg)
    
    # Отменяем
    await orchestrator.cancel(123)
    
    # Поток удалён
    retrieved = await orchestrator.get_flow(123)
    assert retrieved is None
    
    await orchestrator.close()

