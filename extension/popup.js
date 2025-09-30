// popup.js - скрипт для popup окна расширения

document.getElementById('loadMessages').addEventListener('click', loadMessages);

async function loadMessages() {
  const statusDiv = document.getElementById('status');
  const messagesDiv = document.getElementById('messages');
  
  statusDiv.textContent = 'Загрузка сообщений...';
  messagesDiv.innerHTML = '';
  
  try {
    // Получаем активную вкладку
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    // Проверяем, что мы на VK
    if (!tab.url.includes('vk.com')) {
      statusDiv.textContent = 'Ошибка: откройте диалог в VK';
      return;
    }
    
    // Отправляем запрос в content script
    chrome.tabs.sendMessage(tab.id, { action: 'getMessages' }, (response) => {
      if (chrome.runtime.lastError) {
        statusDiv.textContent = 'Ошибка: перезагрузите страницу VK';
        console.error(chrome.runtime.lastError);
        return;
      }
      
      if (response && response.messages) {
        displayMessages(response.messages);
        statusDiv.textContent = `Загружено сообщений: ${response.messages.length}`;
      } else {
        statusDiv.textContent = 'Сообщения не найдены';
      }
    });
    
  } catch (error) {
    statusDiv.textContent = 'Произошла ошибка';
    console.error(error);
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
    headerDiv.textContent = `${msg.role === 'user' ? 'Клиент' : 'Вы'} | ${msg.date || 'время неизвестно'} | ID: ${msg.id || 'N/A'}`;
    
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

// Автоматическая загрузка при открытии popup
window.addEventListener('load', () => {
  console.log('Popup loaded');
});