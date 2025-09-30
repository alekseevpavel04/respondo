// popup.js - скрипт для popup окна расширения

let currentMessages = [];
const API_URL = 'http://localhost:8000';

document.getElementById('generateBtn').addEventListener('click', generateResponse);
document.getElementById('debugBtn').addEventListener('click', debugDialog);
document.getElementById('copyBtn').addEventListener('click', copyResponse);

async function loadMessages() {
  const statusDiv = document.getElementById('status');
  
  try {
    // Получаем активную вкладку
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    // Проверяем, что мы на VK
    if (!tab.url.includes('vk.com')) {
      statusDiv.textContent = 'Ошибка: откройте диалог в VK';
      return null;
    }
    
    // Отправляем запрос в content script
    return new Promise((resolve, reject) => {
      chrome.tabs.sendMessage(tab.id, { action: 'getMessages' }, (response) => {
        if (chrome.runtime.lastError) {
          statusDiv.textContent = 'Ошибка: перезагрузите страницу VK';
          console.error(chrome.runtime.lastError);
          reject(chrome.runtime.lastError);
          return;
        }
        
        if (response && response.messages) {
          currentMessages = response.messages;
          resolve(response.messages);
        } else {
          statusDiv.textContent = 'Сообщения не найдены';
          resolve([]);
        }
      });
    });
    
  } catch (error) {
    statusDiv.textContent = 'Произошла ошибка';
    console.error(error);
    return null;
  }
}

async function debugDialog() {
  const statusDiv = document.getElementById('status');
  const messagesDiv = document.getElementById('messages');
  
  statusDiv.textContent = 'Загрузка сообщений...';
  messagesDiv.innerHTML = '';
  messagesDiv.classList.remove('show');
  
  const messages = await loadMessages();
  
  if (messages && messages.length > 0) {
    displayMessages(messages);
    messagesDiv.classList.add('show');
    statusDiv.textContent = `Загружено сообщений: ${messages.length}`;
  }
}

function displayMessages(messages) {
  const messagesDiv = document.getElementById('messages');
  
  if (messages.length === 0) {
    messagesDiv.innerHTML = '<div class="empty">Сообщения не найдены в текущем диалоге</div>';
    return;
  }
  
  // Сортируем по времени
  messages.sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
  
  messages.forEach(msg => {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${msg.role}`;
    
    const headerDiv = document.createElement('div');
    headerDiv.className = 'message-header';
    headerDiv.textContent = `${msg.role === 'user' ? 'Клиент' : 'Вы'} | ${msg.date || 'время неизвестно'}`;
    
    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';
    textDiv.textContent = msg.text;
    
    messageDiv.appendChild(headerDiv);
    messageDiv.appendChild(textDiv);
    messagesDiv.appendChild(messageDiv);
  });
  
  // Прокручиваем вниз к последним сообщениям
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function generateResponse() {
  const statusDiv = document.getElementById('status');
  const generateBtn = document.getElementById('generateBtn');
  const aiResponse = document.getElementById('aiResponse');
  const aiResponseText = document.getElementById('aiResponseText');
  const messagesDiv = document.getElementById('messages');
  
  generateBtn.disabled = true;
  statusDiv.textContent = 'Загрузка диалога...';
  aiResponse.classList.remove('show');
  messagesDiv.classList.remove('show');
  
  // Сначала загружаем сообщения
  const messages = await loadMessages();
  
  if (!messages || messages.length === 0) {
    statusDiv.textContent = 'Не удалось загрузить сообщения';
    generateBtn.disabled = false;
    return;
  }
  
  statusDiv.textContent = 'Генерация ответа...';
  aiResponseText.value = '⏳ Ожидание ответа от LLM...';
  aiResponse.classList.add('show');
  
  try {
    // Формируем данные в формате вашего API
    const requestData = {
      messages: messages.map(msg => ({
        author: msg.role === 'user' ? 'Клиент' : 'Вы',
        timestamp: msg.date || new Date(msg.timestamp * 1000).toISOString(),
        content: msg.text
      })),
      context: ""
    };
    
    console.log('Отправка запроса:', requestData);
    
    // Отправляем запрос на ваш FastAPI endpoint
    const response = await fetch(`${API_URL}/api/suggest-reply`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Получен ответ:', data);
    
    // Отображаем ответ
    aiResponseText.value = data.suggested_reply || 'Ответ получен, но текст пуст';
    statusDiv.textContent = `Ответ сгенерирован за ${data.processing_time?.toFixed(2) || '?'} сек`;
    
  } catch (error) {
    console.error('Ошибка при генерации ответа:', error);
    aiResponseText.value = `Ошибка: ${error.message}\n\nПроверьте:\n1. Сервер запущен на ${API_URL}\n2. Файл config.py существует с API_KEY\n3. API ключ Google Gemini валиден`;
    statusDiv.textContent = 'Ошибка при генерации ответа';
  } finally {
    generateBtn.disabled = false;
  }
}

function copyResponse() {
  const aiResponseText = document.getElementById('aiResponseText');
  const copyBtn = document.getElementById('copyBtn');
  
  // Копируем текст
  aiResponseText.select();
  document.execCommand('copy');
  
  // Визуальная обратная связь
  const originalText = copyBtn.textContent;
  copyBtn.textContent = '✓ Скопировано!';
  copyBtn.classList.add('copied');
  
  setTimeout(() => {
    copyBtn.textContent = originalText;
    copyBtn.classList.remove('copied');
  }, 2000);
}

// Автоматическая загрузка при открытии popup
window.addEventListener('load', () => {
  console.log('Popup loaded');
});