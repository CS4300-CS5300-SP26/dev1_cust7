//Generated with the help of basic Claude.ai
const mainEl = document.getElementById('chefbot-main');
const SESSION_ID = mainEl.dataset.sessionId;
const CHAT_URL   = mainEl.dataset.chatUrl;
const CSRF_TOKEN = mainEl.dataset.csrfToken;
 
const messagesEl      = document.getElementById('chatMessages');
const inputEl         = document.getElementById('userInput');
const sendBtn         = document.getElementById('sendBtn');
const typingIndicator = document.getElementById('typingIndicator');
const errorToast      = document.getElementById('errorToast');
 
// Auto-grow textarea as user types
inputEl.addEventListener('input', () => {
  inputEl.style.height = 'auto';
  inputEl.style.height = inputEl.scrollHeight + 'px';
});
 
// Enter to send, Shift+Enter for newline
inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
 
sendBtn.addEventListener('click', sendMessage);
 
function appendMessage(role, content) {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}`;
 
  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? '👤' : '🍴';
 
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = content;
 
  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  messagesEl.appendChild(wrapper);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}
 
function showError(msg) {
  errorToast.textContent = msg;
  errorToast.classList.add('visible');
  setTimeout(() => errorToast.classList.remove('visible'), 5000);
}
 
async function sendMessage() {
  const message = inputEl.value.trim();
  if (!message) return;
 
  inputEl.value = '';
  inputEl.style.height = 'auto';
  sendBtn.disabled = true;
  errorToast.classList.remove('visible');
 
  appendMessage('user', message);
 
  typingIndicator.classList.add('visible');
  messagesEl.scrollTop = messagesEl.scrollHeight;
 
  try {
    const response = await fetch(CHAT_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': CSRF_TOKEN,
      },
      body: JSON.stringify({ session_id: SESSION_ID, message }),
    });
 
    const data = await response.json();
 
    if (!response.ok || data.error) {
      showError(data.error || 'Something went wrong. Please try again.');
    } else {
      appendMessage('assistant', data.reply);
    }
 
  } catch (err) {
    showError('Could not reach ChefBot. Check your connection and try again.');
  } finally {
    typingIndicator.classList.remove('visible');
    sendBtn.disabled = false;
    inputEl.focus();
  }
}