const chatBox = document.getElementById('chat-messages');
const input = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

const AGENT_EMOJI = {
  task_classifier: '🧭',
  consultant: '📋',
  school: '🏫',
  school_selection: '🏫',
  appointment: '👨‍🏫',
  user_behavior: '📊',
  reject: '🚫',
  system: '⚠️',
};

let sseFailCount = 0;

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
}

// 渲染 Markdown，含 GFM + 换行；DOMPurify 防 XSS
// 外部链接（http/https/非 # 开头）自动加 target="_blank" rel="noopener"
function renderMd(text) {
  if (typeof marked === 'undefined' || typeof DOMPurify === 'undefined') {
    return escHtml(text);  // 兜底
  }
  // DOMPurify hook：对所有 <a> 节点处理 target
  // 注册一次即可，重复注册无副作用（DOMPurify 内部按顺序执行所有 hooks）
  if (!window.__mdHookRegistered) {
    DOMPurify.addHook('afterSanitizeAttributes', function (node) {
      if (node.tagName === 'A') {
        const href = node.getAttribute('href') || '';
        if (href.startsWith('#')) {
          // 内部锚点（如 #program-1 / #teacher-2），保持当前页
          node.removeAttribute('target');
          node.removeAttribute('rel');
        } else if (href.startsWith('http://') || href.startsWith('https://') || href.startsWith('//')) {
          node.setAttribute('target', '_blank');
          node.setAttribute('rel', 'noopener noreferrer');
        }
      }
    });
    window.__mdHookRegistered = true;
  }
  const html = marked.parse(text || '', {breaks: true, gfm: true});
  return DOMPurify.sanitize(html, {ADD_ATTR: ['target', 'rel']});
}

// 拦截 #program-XX / #teacher-XX 锚点，弹窗显示详情
function attachDetailLinkHandlers(container) {
  container.querySelectorAll('a[href^="#program-"], a[href^="#teacher-"]').forEach(a => {
    a.addEventListener('click', async (e) => {
      e.preventDefault();
      const href = a.getAttribute('href');
      const m = /^#(program|teacher)-(\d+)$/.exec(href);
      if (!m) return;
      await showDetailModal(m[1], parseInt(m[2], 10));
    });
  });
}

// 通用详情弹窗
async function showDetailModal(kind, id) {
  const url = kind === 'program' ? `/api/program/${id}` : `/api/teacher/${id}`;
  let data;
  try {
    const r = await fetch(url);
    data = await r.json();
    if (!r.ok || data.error) throw new Error(data.error || ('HTTP ' + r.status));
  } catch (e) {
    alert('❌ 获取详情失败：' + (e.message || e));
    return;
  }
  // 构造 modal
  let mask = document.getElementById('detail-modal-mask');
  if (!mask) {
    mask = document.createElement('div');
    mask.id = 'detail-modal-mask';
    mask.style.cssText = 'position:fixed;inset:0;background:rgba(40,50,70,.4);z-index:200;display:flex;align-items:center;justify-content:center;';
    mask.innerHTML = `<div id="detail-modal-card" style="background:var(--bg);box-shadow:var(--shadow-out);border-radius:16px;padding:24px;width:540px;max-width:92vw;max-height:80vh;overflow-y:auto;"></div>`;
    document.body.appendChild(mask);
    mask.addEventListener('click', (e) => { if (e.target.id === 'detail-modal-mask') mask.style.display = 'none'; });
  }
  const card = mask.querySelector('#detail-modal-card');
  card.innerHTML = kind === 'program' ? renderProgramDetail(data) : renderTeacherDetail(data);
  mask.style.display = 'flex';
}

function renderProgramDetail(p) {
  const pnames = parseArr(p.program_names);
  const snames = parseArr(p.names);
  const tags = parseArr(p.tags);
  return `
    <h3 style="color:#3d6080;margin-bottom:6px;">🏫 ${esc(snames[0]||'?')}</h3>
    <h4 style="color:#5b7fa6;margin-bottom:14px;font-weight:600;">${esc(pnames[0]||'?')}</h4>
    <p style="font-size:13px;color:#718096;line-height:1.7;margin-bottom:14px;">${esc(p.description_short||'—')}</p>
    <div style="display:grid;grid-template-columns:auto 1fr;gap:6px 14px;font-size:13px;">
      <strong style="color:#5b7fa6;">国家</strong><span>${esc(p.country||'—')} ${p.country_en ? '('+esc(p.country_en)+')' : ''}</span>
      <strong style="color:#5b7fa6;">QS 排名</strong><span>${p.qs_rank ?? '—'}</span>
      <strong style="color:#5b7fa6;">学费</strong><span>${p.tuition_per_year} ${esc(p.currency||'')}/年</span>
      <strong style="color:#5b7fa6;">学制</strong><span>${p.duration_months} 个月</span>
      <strong style="color:#5b7fa6;">语言要求</strong><span>IELTS≥${p.ielts_min??'—'}　TOEFL≥${p.toefl_min??'—'}</span>
      <strong style="color:#5b7fa6;">专业大类</strong><span>${esc(p.major_category||'—')}</span>
      <strong style="color:#5b7fa6;">标签</strong><span>${tags.map(t=>`<span class="slot-pill" style="font-size:11px;margin-right:4px;">${esc(t)}</span>`).join('')}</span>
    </div>
    <div style="margin-top:16px;display:flex;gap:10px;justify-content:flex-end;">
      ${p.program_url ? `<a class="nav-btn" href="${esc(p.program_url)}" target="_blank">🔗 项目主页</a>` : ''}
      ${p.official_site ? `<a class="nav-btn" href="${esc(p.official_site)}" target="_blank">🏫 学校官网</a>` : ''}
      <button class="nav-btn" onclick="document.getElementById('detail-modal-mask').style.display='none'">关闭</button>
    </div>`;
}

function renderTeacherDetail(t) {
  const gender = t.gender === 'male' ? '👨 男' : (t.gender === 'female' ? '👩 女' : '其他');
  return `
    <h3 style="color:#3d6080;margin-bottom:6px;">${t.gender==='male'?'👨':'👩'} ${esc(t.name)}</h3>
    <p style="color:#718096;font-size:13px;margin-bottom:14px;">${gender} ⭐ ${t.rating ?? '—'}</p>
    <p style="font-size:13px;color:#4a5568;line-height:1.7;margin-bottom:14px;">${esc(t.bio||'—')}</p>
    <div style="display:grid;grid-template-columns:auto 1fr;gap:6px 14px;font-size:13px;">
      <strong style="color:#5b7fa6;">擅长地区</strong><span>${esc(t.expertise_regions||'—')}</span>
      <strong style="color:#5b7fa6;">擅长专业</strong><span>${esc(t.expertise_majors||'—')}</span>
      ${t.study_abroad?`<strong style="color:#5b7fa6;">留学经历</strong><span>${esc(t.study_abroad)}</span>`:''}
      ${t.work_experience?`<strong style="color:#5b7fa6;">工作经历</strong><span>${esc(t.work_experience)}</span>`:''}
    </div>
    <div style="margin-top:16px;display:flex;gap:10px;justify-content:flex-end;">
      <button class="nav-btn" onclick="document.getElementById('detail-modal-mask').style.display='none'">关闭</button>
    </div>`;
}

function esc(s) { return escHtml(s).replace(/<br>/g, ''); }
function parseArr(v) {
  if (Array.isArray(v)) return v;
  if (typeof v !== 'string') return [];
  try { const x = JSON.parse(v); return Array.isArray(x) ? x : [v]; } catch(_){ return [v]; }
}

function appendUserMsg(text) {
  const row = document.createElement('div');
  row.className = 'msg-row user';
  row.innerHTML = `<div class="avatar">👤</div><div class="user-msg">${escHtml(text)}</div>`;
  chatBox.appendChild(row);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function createTraceBox() {
  const row = document.createElement('div');
  row.className = 'msg-row';
  row.innerHTML = `<div class="avatar">🛠️</div>
    <div class="trace-box">
      <div class="trace-title">🔗 工作流执行链路</div>
      <ul class="trace-list"></ul>
    </div>`;
  chatBox.appendChild(row);
  chatBox.scrollTop = chatBox.scrollHeight;
  return row.querySelector('.trace-list');
}

function pushTrace(listEl, agent, label, text) {
  const li = document.createElement('li');
  const emoji = AGENT_EMOJI[agent] || '🤖';
  li.innerHTML = `<span class="trace-agent">${emoji} [${escHtml(label || agent)}]</span> ${escHtml(text)}`;
  listEl.appendChild(li);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function appendBotFinal(text, agentName) {
  const row = document.createElement('div');
  row.className = 'msg-row';
  const labelMap = {
    consultant: '咨询机器人',
    school_selection: '选校机器人',
    appointment: '预约机器人',
    user_behavior: '行为分析机器人',
    reject: '归类机器人',
    system: '系统',
  };
  const label = labelMap[agentName] || (agentName || '助手');
  const emoji = AGENT_EMOJI[agentName] || '🤖';
  row.innerHTML = `<div class="avatar">${emoji}</div>
    <div class="bot-msg"><span class="agent-tag">${emoji} ${escHtml(label)}</span><div class="bot-md">${renderMd(text)}</div></div>`;
  chatBox.appendChild(row);
  attachDetailLinkHandlers(row);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendViaSSE(msg, traceList) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120000);
  try {
    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: msg}),
      signal: controller.signal,
    });
    if (!res.ok || !res.body) throw new Error('HTTP ' + res.status);
    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buf = '';
    let gotFinal = false;
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      buf += decoder.decode(value, {stream: true});
      let idx;
      while ((idx = buf.indexOf('\n\n')) >= 0) {
        const chunk = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        if (!chunk.startsWith('data: ')) continue;
        let ev;
        try { ev = JSON.parse(chunk.slice(6)); } catch (_) { continue; }
        if (ev.type === 'trace') {
          pushTrace(traceList, ev.agent, ev.label, ev.text);
        } else if (ev.type === 'final') {
          appendBotFinal(ev.agent_response || '（无回复）', ev.agent_name);
          gotFinal = true;
        }
      }
    }
    clearTimeout(timer);
    if (!gotFinal) throw new Error('stream ended without final event');
    sseFailCount = 0;
    return true;
  } catch (e) {
    clearTimeout(timer);
    sseFailCount++;
    pushTrace(traceList, 'system', '系统',
      '⚠️ SSE 流中断：' + (e.message || e) + (sseFailCount >= 2 ? '（已自动切换同步模式）' : '（正在重试…）'));
    return false;
  }
}

async function sendViaSync(msg, traceList) {
  pushTrace(traceList, 'system', '系统', '正在使用同步模式调用后端…');
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: msg}),
    });
    const data = await res.json();
    if (data.trace && data.trace.length) {
      for (const t of data.trace) {
        pushTrace(traceList, t.agent, t.label, t.text);
      }
    }
    appendBotFinal(data.agent_response || data.error || '（无回复）', data.agent_name || 'system');
    return true;
  } catch (e) {
    pushTrace(traceList, 'system', '系统', '⚠️ 同步模式也失败：' + (e.message || e));
    return false;
  }
}

async function sendMessage() {
  const msg = input.value.trim();
  if (!msg) return;
  appendUserMsg(msg);
  input.value = '';
  sendBtn.classList.add('loading');

  const traceList = createTraceBox();

  if (sseFailCount >= 2) {
    await sendViaSync(msg, traceList);
  } else {
    const ok = await sendViaSSE(msg, traceList);
    if (!ok && sseFailCount < 2) {
      await sendViaSSE(msg, traceList);
    }
    if (!ok && sseFailCount >= 2) {
      await sendViaSync(msg, traceList);
    }
  }

  sendBtn.classList.remove('loading');
  input.focus();
}

sendBtn.addEventListener('click', sendMessage);
input.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
input.focus();
