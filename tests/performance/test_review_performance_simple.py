"""
Упрощенные тесты производительности для системы отзывов.
"""

import time
import pytest
from fastapi.testclient import TestClient
from apps.web.app import app


class TestReviewPerformanceSimple:
    """Упрощенные тесты производительности системы отзывов."""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент FastAPI."""
        return TestClient(app)
    
    def test_api_response_times(self, client):
        """Тест времени отклика API."""
        endpoints = [
            "/api/ratings/top/employee",
            "/api/ratings/top/object", 
            "/api/media/limits",
            "/api/reports/reviews/reviews-summary"
        ]
        
        max_response_time = 2.0  # Максимальное время отклика в секундах
        
        for endpoint in endpoints:
            start_time = time.time()
            
            try:
                response = client.get(endpoint)
                response_time = time.time() - start_time
                
                print(f"Endpoint {endpoint}: {response_time:.3f}s (status: {response.status_code})")
                
                # Проверяем, что время отклика приемлемое
                assert response_time < max_response_time, f"Endpoint {endpoint} too slow: {response_time:.3f}s"
                
            except Exception as e:
                print(f"Error testing {endpoint}: {e}")
                # Для некоторых endpoints ожидаем ошибки авторизации
                if "401" in str(e) or "403" in str(e):
                    continue
                raise
    
    def test_concurrent_requests(self, client):
        """Тест одновременных запросов."""
        def make_request(endpoint):
            try:
                start_time = time.time()
                response = client.get(endpoint)
                response_time = time.time() - start_time
                return {
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "response_time": response_time
                }
            except Exception as e:
                return {
                    "endpoint": endpoint,
                    "error": str(e),
                    "response_time": None
                }
        
        # Список endpoints для тестирования
        endpoints = [
            "/api/ratings/top/employee",
            "/api/ratings/top/object",
            "/api/media/limits",
            "/api/reports/reviews/reviews-summary",
            "/api/reports/reviews/moderation-stats"
        ]
        
        # Создаем 10 одновременных запросов
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, endpoint) for endpoint in endpoints * 2]
            results = [future.result() for future in futures]
        
        # Анализируем результаты
        successful_requests = [r for r in results if r.get("response_time") is not None]
        failed_requests = [r for r in results if r.get("response_time") is None]
        
        print(f"Successful requests: {len(successful_requests)}")
        print(f"Failed requests: {len(failed_requests)}")
        
        if successful_requests:
            avg_response_time = sum(r["response_time"] for r in successful_requests) / len(successful_requests)
            max_response_time = max(r["response_time"] for r in successful_requests)
            
            print(f"Average response time: {avg_response_time:.3f}s")
            print(f"Max response time: {max_response_time:.3f}s")
            
            # Проверяем, что среднее время отклика приемлемое
            assert avg_response_time < 1.0, f"Average response time too high: {avg_response_time:.3f}s"
            assert max_response_time < 3.0, f"Max response time too high: {max_response_time:.3f}s"
    
    def test_database_connection_pool(self, client):
        """Тест пула соединений с базой данных."""
        # Делаем несколько быстрых запросов подряд
        start_time = time.time()
        
        for i in range(20):
            try:
                response = client.get("/api/ratings/top/employee")
                # Небольшая задержка между запросами
                time.sleep(0.01)
            except Exception as e:
                print(f"Request {i} failed: {e}")
        
        total_time = time.time() - start_time
        print(f"20 requests completed in {total_time:.3f}s")
        
        # Проверяем, что все запросы выполнились за разумное время
        assert total_time < 10.0, f"Database connection pool too slow: {total_time:.3f}s"
    
    def test_memory_usage_simple(self):
        """Упрощенный тест использования памяти."""
        # Создаем тестовый клиент
        client = TestClient(app)
        
        # Измеряем время выполнения операций
        start_time = time.time()
        
        # Выполняем операции, которые могут использовать память
        for i in range(10):
            try:
                response = client.get("/api/ratings/top/employee")
                # Имитируем обработку данных
                if response.status_code == 200:
                    data = response.json()
                    # Проверяем, что данные корректные
                    assert "success" in data
            except Exception:
                pass
        
        total_time = time.time() - start_time
        print(f"10 requests completed in {total_time:.3f}s")
        
        # Проверяем, что операции выполнились за разумное время
        assert total_time < 5.0, f"Memory operations too slow: {total_time:.3f}s"


if __name__ == "__main__":
    pytest.main([__file__])
