let currentMessages = [];
const API_URL = 'http://localhost:8000';

// Элементы интерфейса
const loadingContainer = document.getElementById('loadingContainer');
const resultContainer = document.getElementById('resultContainer');
const errorContainer = document.getElementById('errorContainer');
const timerElement = document.getElementById('timer');
const timeInfoElement = document.getElementById('timeInfo');
const aiResponseText = document.getElementById('aiResponseText');
const errorMessage = document.getElementById('errorMessage');

// Секундомер
let startTime;
let timerInterval;

// Форматирование времени: секунды:миллисекунды
function formatTime(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  const milliseconds = Math.floor((ms % 1000) / 10); // Двузначные миллисекунды
  return `${totalSeconds}:${milliseconds.toString().padStart(2, '0')}`;
}

// Форматирование финального времени
function formatFinalTime(ms) {
  const seconds = (ms / 1000).toFixed(2);
  return `${seconds} сек`;
}

// Запуск секундомера
function startTimer() {
  startTime = Date.now();
  timerInterval = setInterval(() => {
    const elapsed = Date.now() - startTime;
    timerElement.textContent = formatTime(elapsed);
  }, 10); // Обновляем каждые 10мс для миллисекунд
}

// Остановка секундомера
function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
  }
  return Date.now() - startTime;
}

// Копирование в буфер обмена
function copyToClipboard(text) {
  // Используем современный Clipboard API
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).catch(err => {
      console.error('Ошибка копирования:', err);
      // Fallback на старый метод
      fallbackCopy(text);
    });
  } else {
    fallbackCopy(text);
  }
}

// Fallback метод копирования
function fallbackCopy(text) {
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand('copy');
  document.body.removeChild(textarea);
}

// Показать результат
function showResult(text, elapsedMs) {
  const finalTime = stopTimer();
  
  // Расширяем окно для показа результата
  document.body.style.width = '450px';
  document.body.style.padding = '15px';
  
  loadingContainer.classList.add('hidden');
  resultContainer.classList.add('show');
  errorContainer.classList.remove('show');
  
  timeInfoElement.textContent = `⏱ Время генерации: ${formatFinalTime(finalTime)}`;
  aiResponseText.value = text;
  
  // Автоматически копируем в буфер обмена
  copyToClipboard(text);
  console.log('Ответ скопирован в буфер обмена');
}

// Показать ошибку
function showError(errorText) {
  stopTimer();
  
  // Расширяем окно для показа ошибки
  document.body.style.width = '350px';
  document.body.style.padding = '15px';
  
  loadingContainer.classList.add('hidden');
  resultContainer.classList.remove('show');
  errorContainer.classList.add('show');
  
  errorMessage.textContent = errorText;
}

// Загрузка сообщений из VK
async function loadMessages() {
  try {
    // Получаем активную вкладку
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    // Проверяем, что мы на VK
    if (!tab.url.includes('vk.com')) {
      throw new Error('Откройте диалог в VK');
    }
    
    // Отправляем запрос в content script
    return new Promise((resolve, reject) => {
      chrome.tabs.sendMessage(tab.id, { action: 'getMessages' }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error('Перезагрузите страницу VK'));
          return;
        }
        
        if (response && response.messages) {
          currentMessages = response.messages;
          resolve(response.messages);
        } else {
          reject(new Error('Сообщения не найдены в диалоге'));
        }
      });
    });
    
  } catch (error) {
    throw error;
  }
}

// Генерация ответа
async function generateResponse() {
  try {
    // Запускаем секундомер
    startTimer();
    
    // Загружаем сообщения
    const messages = await loadMessages();
    
    if (!messages || messages.length === 0) {
      throw new Error('Не удалось загрузить сообщения из диалога');
    }
    
    // Формируем данные для API
    const requestData = {
      messages: messages.map(msg => ({
        author: msg.role === 'user' ? 'Клиент' : 'Вы',
        timestamp: msg.date || new Date(msg.timestamp * 1000).toISOString(),
        content: msg.text
      })),
      context: ""
    };
    
    console.log('Отправка запроса:', requestData);
    
    // Отправляем запрос на FastAPI
    const response = await fetch(`${API_URL}/api/suggest-reply`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Ошибка сервера: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Получен ответ:', data);
    
    // Показываем результат
    const responseText = data.suggested_reply || 'Ответ получен, но текст пуст';
    const elapsedMs = Date.now() - startTime;
    showResult(responseText, elapsedMs);
    
  } catch (error) {
    console.error('Ошибка при генерации:', error);
    
    let errorText = `Ошибка: ${error.message}\n\n`;
    
    if (error.message.includes('VK')) {
      errorText += 'Откройте диалог на сайте vk.com';
    } else if (error.message.includes('Перезагрузите')) {
      errorText += 'Перезагрузите страницу VK и попробуйте снова';
    } else if (error.message.includes('сервера') || error.message.includes('Failed to fetch')) {
      errorText += `Проверьте:\n• Сервер запущен на ${API_URL}\n• Файл config.py содержит API_KEY\n• API ключ Google Gemini валиден`;
    } else {
      errorText += 'Попробуйте перезагрузить страницу';
    }
    
    showError(errorText);
  }
}

// Обработчик кнопки повтора
document.getElementById('retryBtn').addEventListener('click', () => {
  // Возвращаем компактное окно
  document.body.style.width = '';
  document.body.style.padding = '8px';
  
  // Скрываем ошибку и показываем загрузку
  errorContainer.classList.remove('show');
  loadingContainer.classList.remove('hidden');
  
  // Запускаем генерацию заново
  generateResponse();
});

// АВТОЗАПУСК при открытии popup
console.log('Popup opened, starting generation...');
generateResponse();