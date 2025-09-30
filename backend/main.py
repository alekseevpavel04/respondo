from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime
from google import genai

# Импортируем API ключ из config.py
try:
    from config import API_KEY
except ImportError:
    raise Exception("Файл config.py не найден! Создайте файл backend/config.py с переменной API_KEY")

# Инициализируем Google Genai клиент
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
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/api/suggest-reply", response_model=DialogResponse)
async def suggest_reply(request: DialogRequest):
    """
    Основной endpoint для получения предложенного ответа на диалог
    
    Принимает диалог, отправляет в LLM и возвращает предложенный ответ
    """
    start_time = datetime.now()
    
    try:
        # Формируем промпт для LLM из истории диалога
        dialog_text = format_dialog(request.messages)
        
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


def format_dialog(messages: List[Message]) -> str:
    """
    Форматирует список сообщений в текстовый диалог для LLM
    """
    dialog_lines = []
    
    for msg in messages:
        dialog_lines.append(f"[{msg.timestamp}] {msg.author}: {msg.content}")
    
    return "\n".join(dialog_lines)


async def call_llm_api(dialog: str, context: str = "") -> str:
    """
    Отправляет запрос к Google Gemini API и возвращает предложенный ответ
    """
    
    # Формируем промпт
    system_instruction = """Ты - ассистент, который помогает писать ответы на сообщения в диалогах.
Твоя задача - проанализировать историю диалога и предложить уместный, вежливый и содержательный ответ.

Требования к ответу:
- Будь кратким и по делу
- Учитывай контекст и тон беседы
- Отвечай на том же языке, что и диалог
- Не повторяй уже сказанное
- Будь вежливым и профессиональным"""
    
    if context:
        system_instruction += f"\n\nДополнительный контекст: {context}"
    
    prompt = f"""{system_instruction}

Вот история диалога:

{dialog}

Предложи подходящий ответ на последнее сообщение."""
    
    try:
        # Используем Google Genai SDK
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash-exp",  # или gemini-1.5-flash, gemini-1.5-pro
            contents=prompt
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
    Тестовый endpoint для проверки без реального вызова LLM
    """
    dialog_text = format_dialog(request.messages)
    
    return {
        "formatted_dialog": dialog_text,
        "message_count": len(request.messages),
        "test_reply": "Это тестовый ответ. LLM не вызывался."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)