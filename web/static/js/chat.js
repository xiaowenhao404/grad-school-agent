const chatBox = document.getElementById('chat-messages');
const input = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

function appendMsg(html, isUser) {
  const row = document.createElement('div');
  row.className = 'msg-row' + (isUser ? ' user' : '');
  if (isUser) {
    row.innerHTML = `<div class="avatar">👤</div><div class="user-msg">${escHtml(html)}</div>`;
  } else {
    row.innerHTML = `<div class="avatar">🤖</div><div class="bot-msg">${html}</div>`;
  }
  chatBox.appendChild(row);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
}

function formatBotMsg(text, agentName) {
  const tag = agentName ? `<span class="agent-tag">🤖 ${agentName}</span>` : '';
  return tag + escHtml(text);
}

async function sendMessage() {
  const msg = input.value.trim();
  if (!msg) return;
  appendMsg(msg, true);
  input.value = '';
  sendBtn.classList.add('loading');

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: msg})
    });
    const data = await res.json();
    appendMsg(formatBotMsg(data.agent_response || '（无回复）', data.agent_name), false);
  } catch (e) {
    appendMsg('<span style="color:#e05252">网络错误，请重试</span>', false);
  } finally {
    sendBtn.classList.remove('loading');
    input.focus();
  }
}

sendBtn.addEventListener('click', sendMessage);
input.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
input.focus();
