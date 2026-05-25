// =============================================
// 151 — Site Scripts + AI Features
// =============================================

const API_BASE = window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1')
  ? 'http://localhost:5000'
  : '';  // same origin in production

// ─── Theme (default: dark Ancient Mew) ─────────────────────────────────────────────
(function () {
  // Always start dark — Ancient Mew IS the brand
  document.documentElement.setAttribute('data-theme', 'dark');

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('theme-toggle');
    let isDark = true;
    if (btn) {
      btn.textContent = '☀️';
      btn.title = 'Switch to parchment mode';
      btn.addEventListener('click', () => {
        isDark = !isDark;
        document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
        btn.textContent = isDark ? '☀️' : '🌙';
        btn.title = isDark ? 'Switch to parchment mode' : 'Switch to dark mode';
      });
    }
  });
})();

// ─── DOM Ready ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initNav();
  initEmailForms();
  initCategoryFilter();
  initSearch();
  initReadingProgress();
  initAIChat();
  initArticleTools();
  initActiveNavLink();
});

// ─── Nav ──────────────────────────────────────────────────────────────────────
function initNav() {
  const hamburger = document.getElementById('nav-hamburger');
  const mobileMenu = document.getElementById('nav-mobile-menu');
  if (!hamburger || !mobileMenu) return;

  hamburger.addEventListener('click', () => mobileMenu.classList.toggle('open'));
  document.addEventListener('click', (e) => {
    if (!hamburger.contains(e.target) && !mobileMenu.contains(e.target)) {
      mobileMenu.classList.remove('open');
    }
  });
}

function initActiveNavLink() {
  const path = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a, .nav-mobile-menu a').forEach(link => {
    if (link.getAttribute('href') === path || (path === '' && link.getAttribute('href') === 'index.html')) {
      link.classList.add('active');
    }
  });
}

// ─── Email forms ─────────────────────────────────────────────────────────────
function initEmailForms() {
  document.querySelectorAll('.signup-form').forEach(form => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const input = form.querySelector('.signup-input');
      if (input && input.value.includes('@')) {
        showToast('✦ You\'re on the list. Welcome to 151.');
        input.value = '';
      } else {
        showToast('Enter a valid email address.');
      }
    });
  });
}

// ─── Category filter ────────────────────────────────────────────────────────────
function initCategoryFilter() {
  document.querySelectorAll('.category-pill[data-filter]').forEach(pill => {
    pill.addEventListener('click', () => {
      const filter = pill.dataset.filter;
      document.querySelectorAll('.category-pill[data-filter]').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      document.querySelectorAll('[data-category]').forEach(item => {
        item.style.display = (filter === 'all' || item.dataset.category === filter) ? '' : 'none';
      });
    });
  });
}

// ─── Search ─────────────────────────────────────────────────────────────────────
function initSearch() {
  const input = document.getElementById('post-search');
  if (!input) return;
  input.addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll('[data-title]').forEach(item => {
      const match = item.dataset.title.toLowerCase().includes(q) ||
                    (item.dataset.excerpt || '').toLowerCase().includes(q);
      item.style.display = match ? '' : 'none';
    });
  });
}

// ─── Reading progress ─────────────────────────────────────────────────────────────
function initReadingProgress() {
  const bar = document.getElementById('reading-progress');
  if (!bar) return;
  window.addEventListener('scroll', () => {
    const h = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.width = h > 0 ? (window.scrollY / h * 100) + '%' : '0%';
  });
}

// ─── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg) {
  let t = document.querySelector('.toast');
  if (!t) { t = document.createElement('div'); t.className = 'toast'; document.body.appendChild(t); }
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 3500);
}

// ───────────────────────────────────────────────────────────────────────────────
//  AI CHAT WIDGET
// ───────────────────────────────────────────────────────────────────────────────

let chatHistory = [];
let articleContext = '';

function initAIChat() {
  const trigger = document.getElementById('ai-chat-trigger');
  const panel = document.getElementById('ai-chat-panel');
  const closeBtn = document.getElementById('ai-chat-close');
  const input = document.getElementById('ai-chat-input');
  const sendBtn = document.getElementById('ai-chat-send');

  if (!trigger || !panel) return;

  // Grab article text if on a post page
  const articleBody = document.querySelector('.post-body .prose');
  if (articleBody) {
    articleContext = articleBody.innerText.slice(0, 6000);
  }

  trigger.addEventListener('click', () => {
    const isOpen = panel.classList.contains('open');
    if (isOpen) {
      panel.classList.remove('open');
    } else {
      panel.classList.add('open');
      input?.focus();
    }
  });

  closeBtn?.addEventListener('click', () => panel.classList.remove('open'));

  // Suggestion buttons
  document.querySelectorAll('.ai-suggestion-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const q = btn.dataset.q;
      if (q) sendMessage(q);
    });
  });

  // Send on Enter or button
  input?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input.value); }
  });
  sendBtn?.addEventListener('click', () => sendMessage(input?.value || ''));
}

async function sendMessage(text) {
  text = text.trim();
  if (!text) return;

  const input = document.getElementById('ai-chat-input');
  const messages = document.getElementById('ai-chat-messages');
  if (!messages) return;

  // Hide welcome msg on first message
  const welcome = messages.querySelector('.ai-welcome-msg');
  if (welcome) welcome.style.display = 'none';

  // Add user message
  chatHistory.push({ role: 'user', content: text });
  appendMessage('user', text);
  if (input) input.value = '';

  // Typing indicator
  const typingId = appendTyping();

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: chatHistory, articleContext }),
    });

    removeTyping(typingId);

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      if (res.status === 503) {
        appendMessage('assistant', '⚙️ AI not connected yet. Add your ANTHROPIC_API_KEY to .env and run `python blog/api.py` to enable this feature.');
      } else {
        appendMessage('assistant', `Something went wrong: ${err.error || res.statusText}`);
      }
      return;
    }

    const data = await res.json();
    const reply = data.response || 'No response.';
    chatHistory.push({ role: 'assistant', content: reply });
    appendMessage('assistant', reply);
  } catch {
    removeTyping(typingId);
    appendMessage('assistant', '⚙️ Run `python blog/api.py` to connect the AI. Make sure your .env file has ANTHROPIC_API_KEY set.');
  }
}

function appendMessage(role, text) {
  const container = document.getElementById('ai-chat-messages');
  if (!container) return;

  const div = document.createElement('div');
  div.className = `ai-message ${role}`;

  if (role === 'assistant') {
    div.innerHTML = `<div class="ai-msg-avatar">M</div><div class="ai-msg-text">${escapeHtml(text).replace(/\n/g, '<br>')}</div>`;
  } else {
    div.innerHTML = `<div class="ai-msg-text">${escapeHtml(text)}</div>`;
  }

  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function appendTyping() {
  const container = document.getElementById('ai-chat-messages');
  if (!container) return null;
  const id = 'typing-' + Date.now();
  const div = document.createElement('div');
  div.className = 'ai-message assistant';
  div.id = id;
  div.innerHTML = `<div class="ai-msg-avatar">M</div><div class="ai-typing"><span></span><span></span><span></span></div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeTyping(id) {
  if (!id) return;
  document.getElementById(id)?.remove();
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ───────────────────────────────────────────────────────────────────────────────
//  ARTICLE AI TOOLS (Summary / Counter / Simplify)
// ───────────────────────────────────────────────────────────────────────────────

function initArticleTools() {
  const toolsEl = document.getElementById('article-ai-tools');
  if (!toolsEl) return;

  const articleBody = document.querySelector('.post-body .prose');
  const content = articleBody ? articleBody.innerText : '';

  document.querySelectorAll('.tool-tab').forEach(tab => {
    tab.addEventListener('click', async () => {
      document.querySelectorAll('.tool-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      await runTool(tab.dataset.tool, content);
    });
  });
}

async function runTool(tool, content) {
  const el = document.getElementById('tool-content');
  if (!el) return;

  const endpointMap = { summary: '/api/summary', debate: '/api/debate', explain: '/api/explain' };
  const responseKey = { summary: 'summary', debate: 'debate', explain: 'explain' };
  const labelMap = {
    summary: '📋 AI Summary',
    debate:  '⚔️ Counter-Argument',
    explain: '🔍 Plain English',
  };

  el.innerHTML = `<div class="tool-loading"><div class="tool-spinner"></div><span>Generating ${labelMap[tool]}…</span></div>`;

  try {
    const res = await fetch(`${API_BASE}${endpointMap[tool]}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });

    if (!res.ok) {
      if (res.status === 503) {
        el.innerHTML = `<p class="tool-error">⚙️ Run <code>python blog/api.py</code> with your API key to enable AI tools.</p>`;
      } else {
        el.innerHTML = `<p class="tool-error">Something went wrong. Try again.</p>`;
      }
      return;
    }

    const data = await res.json();
    const text = data[responseKey[tool]] || '';
    el.innerHTML = `<div class="tool-label">${labelMap[tool]}</div><div class="tool-output">${escapeHtml(text).replace(/\n/g, '<br>').replace(/•/g, '<span class="tool-bullet">✦</span>')}</div>`;
  } catch {
    el.innerHTML = `<p class="tool-error">⚙️ Start the server: <code>python blog/api.py</code></p>`;
  }
}
