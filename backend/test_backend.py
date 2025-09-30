"""
Тестовый скрипт для проверки backend API
"""
import requests
import json
from datetime import datetime

# URL вашего backend
BASE_URL = "http://localhost:8000"


def test_health_check():
    """Проверка работоспособности сервера"""
    print("=== Проверка health check ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {response.json()}\n")
    return response.status_code == 200


def test_root():
    """Проверка корневого endpoint"""
    print("=== Проверка root endpoint ===")
    response = requests.get(f"{BASE_URL}/")
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}\n")
    return response.status_code == 200


def test_dialog_processing():
    """Тестирование обработки диалога"""
    print("=== Тест обработки диалога ===")
    
    # Тестовые данные диалога
    test_data = {
        "messages": [
            {
                "author": "Алексей",
                "timestamp": "2025-09-30T10:30:00",
                "content": "Привет! Как дела с проектом?"
            },
            {
                "author": "Мария",
                "timestamp": "2025-09-30T10:31:15",
                "content": "Привет! Все хорошо, почти закончили первую версию backend."
            },
            {
                "author": "Алексей",
                "timestamp": "2025-09-30T10:32:00",
                "content": "Отлично! Когда планируешь деплоить?"
            }
        ],
        "context": "Обсуждение рабочего проекта"
    }
    
    print("Отправляемые данные:")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))
    print()
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/suggest-reply",
            json=test_data,
            timeout=30
        )
        
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Предложенный ответ: {result['suggested_reply']}")
            print(f"Время обработки: {result['processing_time']:.2f} сек")
            return True
        else:
            print(f"Ошибка: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при отправке запроса: {e}")
        return False
    
    print()


def test_without_llm():
    """Тест без реального вызова LLM (тестовый endpoint)"""
    print("=== Тест без LLM (test endpoint) ===")
    
    test_data = {
        "messages": [
            {
                "author": "User1",
                "timestamp": datetime.now().isoformat(),
                "content": "Тестовое сообщение"
            },
            {
                "author": "User2",
                "timestamp": datetime.now().isoformat(),
                "content": "Ответ на тестовое сообщение"
            }
        ]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/test",
            json=test_data,
            timeout=10
        )
        
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return True
        else:
            print(f"Ошибка: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при отправке запроса: {e}")
        return False
    
    print()


def main():
    """Запуск всех тестов"""
    print("=" * 50)
    print("ТЕСТИРОВАНИЕ RESPONDO BACKEND")
    print("=" * 50)
    print()
    
    # Проверяем доступность сервера
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except requests.exceptions.RequestException:
        print("❌ Сервер недоступен!")
        print(f"Убедитесь, что backend запущен на {BASE_URL}")
        print("Запустите: cd backend && python main.py")
        return
    
    # Запускаем тесты
    results = []
    
    results.append(("Health Check", test_health_check()))
    results.append(("Root Endpoint", test_root()))
    results.append(("Test Endpoint (без LLM)", test_without_llm()))
    results.append(("Dialog Processing (с LLM)", test_dialog_processing()))
    
    # Итоги
    print("=" * 50)
    print("РЕЗУЛЬТАТЫ ТЕСТОВ")
    print("=" * 50)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    print(f"\nПройдено: {passed_count}/{len(results)}")


if __name__ == "__main__":
    main()