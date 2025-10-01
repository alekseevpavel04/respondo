from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime
from google import genai
from google.genai import types
import os
from pathlib import Path

# Импортируем настройки из config.py
try:
    from config import API_KEY, USE_CUSTOM_ENDPOINT, CUSTOM_API_URL, MODEL_NAME
except ImportError:
    raise Exception(
        "Файл config.py не найден или неполный!\n"
        "Создайте файл backend/config.py со следующими переменными:\n"
        "  API_KEY = 'your-api-key'\n"
        "  USE_CUSTOM_ENDPOINT = False  # True для custom endpoint\n"
        "  CUSTOM_API_URL = 'https://hubai.loe.gg'  # URL custom endpoint\n"
        "  MODEL_NAME = 'gemini-2.0-flash-lite'  # Название модели"
    )

# Инициализируем Google Genai клиент
if USE_CUSTOM_ENDPOINT:
    print(f"🔧 Используется custom endpoint: {CUSTOM_API_URL}")
    genai_client = genai.Client(
        api_key=API_KEY,
        http_options=types.HttpOptions(base_url=CUSTOM_API_URL)
    )
else:
    print("🔧 Используется стандартный Google API endpoint")
    genai_client = genai.Client(api_key=API_KEY)

app = FastAPI(title="Respondo Backend")

# Настройка CORS для работы с расширением браузера
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальная переменная для системного промпта
SYSTEM_PROMPT = None


def load_system_prompt(prompt_file: str = "prompts/system_prompt.txt") -> str:
    """
    Загружает системный промпт из файла.
    Извлекает только содержимое внутри фигурных скобок {}.
    Всё остальное считается комментариями и игнорируется.
    
    Args:
        prompt_file: путь к файлу с промптом
    
    Returns:
        str: содержимое промпта из фигурных скобок
    """
    try:
        prompt_path = Path(__file__).parent / prompt_file
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Ищем содержимое между { и }
        import re
        match = re.search(r'\{(.*?)\}', content, re.DOTALL)
        
        if match:
            prompt = match.group(1).strip()
            print(f"✅ Промпт извлечён из фигурных скобок")
            return prompt
        else:
            print(f"⚠️  Фигурные скобки не найдены в файле. Используется весь файл как промпт.")
            return content.strip()
            
    except FileNotFoundError:
        print(f"⚠️  Файл {prompt_file} не найден. Используется дефолтный промпт.")
        # Дефолтный промпт
        return """Ты - умный ассистент для анализа диалогов и формирования ответов.

ТВОЯ ЗАДАЧА:
Проанализировать историю диалога с учётом временных меток и предложить уместный, естественный ответ.

ВРЕМЕННОЙ КОНТЕКСТ:
- Обращай внимание на время между сообщениями
- Долгие паузы (несколько часов/дней) могут требовать более вежливого возобновления диалога
- Быстрые ответы указывают на активную беседу
- Если последнее сообщение было давно, учти это в тоне ответа

ПРАВИЛА:
- Отвечай на том же языке, что и диалог
- Сохраняй тон и стиль беседы (формальный/неформальный)
- Будь кратким и по существу
- Отвечай на заданные вопросы
- Не повторяй уже сказанное
- Будь вежливым и естественным

ФОРМАТ ОТВЕТА:
Предложи только текст ответа, без дополнительных пояснений или комментариев."""


# Загружаем промпт при старте приложения
@app.on_event("startup")
async def startup_event():
    global SYSTEM_PROMPT
    SYSTEM_PROMPT = load_system_prompt()
    print("✅ Системный промпт загружен")
    print(f"📝 Длина промпта: {len(SYSTEM_PROMPT)} символов")
    print(f"🤖 Модель: {MODEL_NAME}")
    if USE_CUSTOM_ENDPOINT:
        print(f"🔗 Custom API endpoint: {CUSTOM_API_URL}")
    else:
        print(f"🔗 Standard Google API endpoint")


class Message(BaseModel):
    """Модель одного сообщения в диалоге"""
    author: str  # Кто написал
    timestamp: str  # Когда написал (ISO формат или строка)
    content: str  # Что написал


class DialogRequest(BaseModel):
    """Модель запроса с диалогом"""
    messages: List[Message]
    context: str = ""  # Дополнительный контекст (опционально)


class DialogResponse(BaseModel):
    """Модель ответа с предложенным текстом"""
    suggested_reply: str
    processing_time: float


@app.get("/")
async def root():
    """Проверка работоспособности API"""
    return {
        "status": "ok",
        "service": "Respondo Backend",
        "version": "2.1.0",
        "prompt_loaded": SYSTEM_PROMPT is not None,
        "model": MODEL_NAME,
        "endpoint_type": "custom" if USE_CUSTOM_ENDPOINT else "standard",
        "api_endpoint": CUSTOM_API_URL if USE_CUSTOM_ENDPOINT else "api.google.com"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/reload-prompt")
async def reload_prompt():
    """
    Перезагружает системный промпт из файла без перезапуска сервера
    """
    global SYSTEM_PROMPT
    SYSTEM_PROMPT = load_system_prompt()
    return {
        "status": "success",
        "message": "Промпт перезагружен",
        "prompt_length": len(SYSTEM_PROMPT)
    }


@app.post("/api/suggest-reply", response_model=DialogResponse)
async def suggest_reply(request: DialogRequest):
    """
    Основной endpoint для получения предложенного ответа на диалог
    
    Принимает диалог, отправляет в LLM и возвращает предложенный ответ
    """
    start_time = datetime.now()
    
    try:
        # Формируем промпт для LLM из истории диалога с временными метками
        dialog_text = format_dialog_with_time_analysis(request.messages)
        
        # Отправляем запрос к LLM API
        llm_response = await call_llm_api(dialog_text, request.context)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return DialogResponse(
            suggested_reply=llm_response,
            processing_time=processing_time
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обработке запроса: {str(e)}"
        )


def parse_timestamp(timestamp_str: str) -> datetime:
    """
    Парсит timestamp из разных форматов
    """
    # Попытка распарсить ISO формат
    try:
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except:
        pass
    
    # Попытка распарсить другие форматы
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%H:%M",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except:
            continue
    
    # Если не получилось распарсить, возвращаем текущее время
    return datetime.now()


def analyze_time_gaps(messages: List[Message]) -> str:
    """
    Анализирует временные промежутки между сообщениями
    """
    if len(messages) < 2:
        return "Диалог только начался."
    
    try:
        timestamps = [parse_timestamp(msg.timestamp) for msg in messages]
        
        # Анализируем последний промежуток
        last_gap = timestamps[-1] - timestamps[-2]
        total_duration = timestamps[-1] - timestamps[0]
        
        analysis = []
        
        # Анализ последнего промежутка
        if last_gap.total_seconds() < 60:
            analysis.append("Активная переписка (ответ в течение минуты)")
        elif last_gap.total_seconds() < 3600:
            minutes = int(last_gap.total_seconds() / 60)
            analysis.append(f"Небольшая пауза ({minutes} мин)")
        elif last_gap.total_seconds() < 86400:
            hours = int(last_gap.total_seconds() / 3600)
            analysis.append(f"Значительная пауза ({hours} ч)")
        else:
            days = int(last_gap.total_seconds() / 86400)
            analysis.append(f"Долгая пауза ({days} дн)")
        
        # Общая длительность диалога
        if total_duration.total_seconds() < 3600:
            analysis.append("Быстрая беседа")
        elif total_duration.total_seconds() < 86400:
            analysis.append("Диалог в течение дня")
        else:
            analysis.append("Долгий диалог")
        
        return " | ".join(analysis)
    
    except:
        return "Не удалось проанализировать временные промежутки"


def format_dialog_with_time_analysis(messages: List[Message]) -> str:
    """
    Форматирует список сообщений в текстовый диалог с анализом времени
    """
    dialog_lines = []
    
    # Добавляем анализ временных промежутков
    time_analysis = analyze_time_gaps(messages)
    dialog_lines.append(f"=== ВРЕМЕННОЙ АНАЛИЗ ===")
    dialog_lines.append(time_analysis)
    dialog_lines.append(f"Всего сообщений: {len(messages)}")
    dialog_lines.append("")
    dialog_lines.append("=== ИСТОРИЯ ДИАЛОГА ===")
    
    # Форматируем сообщения
    for i, msg in enumerate(messages):
        prefix = "└─" if i == len(messages) - 1 else "├─"
        dialog_lines.append(f"{prefix} [{msg.timestamp}] {msg.author}: {msg.content}")
    
    return "\n".join(dialog_lines)


async def call_llm_api(dialog: str, context: str = "") -> str:
    """
    Отправляет запрос к Gemini API и возвращает предложенный ответ
    """
    
    # Используем загруженный системный промпт
    system_instruction = SYSTEM_PROMPT
    
    # Добавляем дополнительный контекст, если есть
    if context:
        system_instruction += f"\n\nДополнительный контекст: {context}"
    
    # Формируем финальный промпт
    full_prompt = f"""{system_instruction}

{dialog}

Проанализируй диалог выше (обрати особое внимание на временной анализ) и предложи подходящий ответ на последнее сообщение."""
    
    try:
        # Используем Google Genai SDK
        response = genai_client.models.generate_content(
            model=MODEL_NAME,
            contents=full_prompt
        )
        
        return response.text.strip()
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при вызове Gemini API: {str(e)}"
        )


@app.post("/api/test")
async def test_endpoint(request: DialogRequest):
    """
    Тестовый endpoint для проверки форматирования без реального вызова LLM
    """
    dialog_text = format_dialog_with_time_analysis(request.messages)
    time_analysis = analyze_time_gaps(request.messages)
    
    return {
        "formatted_dialog": dialog_text,
        "time_analysis": time_analysis,
        "message_count": len(request.messages),
        "system_prompt_length": len(SYSTEM_PROMPT) if SYSTEM_PROMPT else 0,
        "test_reply": "Это тестовый ответ. LLM не вызывался."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)