// content.js - скрипт для извлечения сообщений из VK

function extractMessages() {
  const messages = [];
  
  console.log('Начинаем извлечение сообщений...');
  
  // Пробуем разные селекторы для сообщений
  let messageElements = document.querySelectorAll('.im-mess._im_mess');
  console.log('Найдено элементов с .im-mess._im_mess:', messageElements.length);
  
  // Если не нашли, пробуем другие варианты
  if (messageElements.length === 0) {
    messageElements = document.querySelectorAll('[class*="im-mess"]');
    console.log('Найдено элементов с [class*="im-mess"]:', messageElements.length);
  }
  
  if (messageElements.length === 0) {
    messageElements = document.querySelectorAll('li[data-msgid]');
    console.log('Найдено элементов с li[data-msgid]:', messageElements.length);
  }
  
  messageElements.forEach((msg, index) => {
    console.log(`Обработка сообщения ${index}:`, msg.className);
    
    const isOutgoing = msg.classList.contains('im-mess_out');
    const timestamp = msg.getAttribute('data-ts');
    const msgId = msg.getAttribute('data-msgid');
    const peerId = msg.getAttribute('data-peer');
    
    // Пробуем разные селекторы для текста
    let textElement = msg.querySelector('.im-mess--text');
    if (!textElement) {
      textElement = msg.querySelector('[class*="mess--text"]');
    }
    if (!textElement) {
      textElement = msg.querySelector('.message_text');
    }
    
    let text = textElement ? textElement.innerText.trim() : '';
    
    // Если не нашли текст, берем весь текст из элемента
    if (!text) {
      text = msg.innerText.trim();
    }
    
    console.log(`Сообщение ${index}: текст = "${text.substring(0, 50)}...", isOutgoing = ${isOutgoing}`);
    
    if (text) {
      messages.push({
        id: msgId,
        timestamp: timestamp ? parseInt(timestamp) : null,
        date: timestamp ? new Date(parseInt(timestamp) * 1000).toLocaleString() : null,
        isOutgoing: isOutgoing,
        peerId: peerId,
        text: text,
        role: isOutgoing ? 'assistant' : 'user'
      });
    }
  });
  
  console.log('Всего извлечено сообщений:', messages.length);
  return messages;
}

// Слушаем запросы от popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Получен запрос:', request);
  
  if (request.action === 'getMessages') {
    const messages = extractMessages();
    console.log('Отправляем сообщения:', messages.length);
    sendResponse({ messages: messages });
  }
  return true;
});

console.log('Respondo content script loaded');