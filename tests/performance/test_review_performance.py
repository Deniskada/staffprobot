"""
Тесты производительности для системы отзывов.
"""

import time
import pytest
from concurrent.futures import ThreadPoolExecutor


class TestReviewPerformance:
    """Тесты производительности системы отзывов."""
    
    @pytest.fixture
    def base_url(self):
        """Базовый URL API."""
        return "http://localhost:8001"
    
    def test_api_response_times(self, base_url):
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
            
            import requests
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
                response_time = time.time() - start_time
                
                print(f"Endpoint {endpoint}: {response_time:.3f}s (status: {response.status_code})")
                
                # Проверяем, что время отклика приемлемое
                assert response_time < max_response_time, f"Endpoint {endpoint} too slow: {response_time:.3f}s"
                
            except requests.exceptions.RequestException as e:
                print(f"Error testing {endpoint}: {e}")
                # Для некоторых endpoints ожидаем ошибки авторизации
                if "401" in str(e) or "403" in str(e):
                    continue
                raise
    
    def test_concurrent_requests(self, base_url):
        """Тест одновременных запросов."""
        def make_request(endpoint):
            import requests
            try:
                start_time = time.time()
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
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
    
    def test_database_connection_pool(self, base_url):
        """Тест пула соединений с базой данных."""
        # Делаем несколько быстрых запросов подряд
        start_time = time.time()
        
        import requests
        for i in range(20):
            try:
                response = requests.get(f"{base_url}/api/ratings/top/employee", timeout=5)
                # Небольшая задержка между запросами
                time.sleep(0.1)
            except Exception as e:
                print(f"Request {i} failed: {e}")
        
        total_time = time.time() - start_time
        print(f"20 requests completed in {total_time:.3f}s")
        
        # Проверяем, что все запросы выполнились за разумное время
        assert total_time < 10.0, f"Database connection pool too slow: {total_time:.3f}s"
    
    def test_memory_usage(self):
        """Тест использования памяти."""
        import psutil
        import os
        
        # Получаем текущий процесс
        process = psutil.Process(os.getpid())
        
        # Измеряем память до теста
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Выполняем операции, которые могут использовать память
        import requests
        for i in range(10):
            try:
                response = requests.get("http://localhost:8001/api/ratings/top/employee", timeout=5)
                # Имитируем обработку данных
                data = response.json() if response.status_code == 200 else {}
            except Exception:
                pass
        
        # Измеряем память после теста
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = memory_after - memory_before
        
        print(f"Memory used: {memory_used:.2f} MB")
        
        # Проверяем, что использование памяти разумное
        assert memory_used < 50, f"Memory usage too high: {memory_used:.2f} MB"


if __name__ == "__main__":
    pytest.main([__file__])
