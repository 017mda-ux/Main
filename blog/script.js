// =============================================
// Alakazam Alpha — Site Scripts
// =============================================

// --- Dark Mode Toggle ---
(function () {
  const savedTheme = localStorage.getItem('aa-theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('aa-theme', next);
        updateThemeIcon(next);
      });
    }

    // Mobile nav toggle
    const hamburger = document.getElementById('nav-hamburger');
    const mobileMenu = document.getElementById('nav-mobile-menu');
    if (hamburger && mobileMenu) {
      hamburger.addEventListener('click', () => {
        mobileMenu.classList.toggle('open');
      });
      // Close on outside click
      document.addEventListener('click', (e) => {
        if (!hamburger.contains(e.target) && !mobileMenu.contains(e.target)) {
          mobileMenu.classList.remove('open');
        }
      });
    }

    // Email signup forms
    document.querySelectorAll('.signup-form').forEach(form => {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const input = form.querySelector('.signup-input');
        if (input && input.value.includes('@')) {
          showToast('✓ You\'re on the list! Welcome to Alakazam Alpha.');
          input.value = '';
        } else {
          showToast('Please enter a valid email address.');
        }
      });
    });

    // Category filter on blog page
    document.querySelectorAll('.category-pill[data-filter]').forEach(pill => {
      pill.addEventListener('click', () => {
        const filter = pill.dataset.filter;
        document.querySelectorAll('.category-pill[data-filter]').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');

        document.querySelectorAll('[data-category]').forEach(item => {
          if (filter === 'all' || item.dataset.category === filter) {
            item.style.display = '';
          } else {
            item.style.display = 'none';
          }
        });
      });
    });

    // Search filter on blog page
    const searchInput = document.getElementById('post-search');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        document.querySelectorAll('[data-title]').forEach(item => {
          const title = item.dataset.title.toLowerCase();
          const excerpt = (item.dataset.excerpt || '').toLowerCase();
          item.style.display = (title.includes(query) || excerpt.includes(query)) ? '' : 'none';
        });
      });
    }

    // Set active nav link
    const path = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-links a, .nav-mobile-menu a').forEach(link => {
      const href = link.getAttribute('href');
      if (href === path || (path === '' && href === 'index.html')) {
        link.classList.add('active');
      }
    });
  });

  function updateThemeIcon(theme) {
    document.querySelectorAll('#theme-toggle').forEach(btn => {
      btn.textContent = theme === 'dark' ? '☀️' : '🌙';
      btn.title = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
    });
  }
})();

// --- Toast Notification ---
function showToast(msg) {
  let toast = document.querySelector('.toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3500);
}

// --- Reading progress bar (for post pages) ---
document.addEventListener('DOMContentLoaded', () => {
  const bar = document.getElementById('reading-progress');
  if (!bar) return;
  window.addEventListener('scroll', () => {
    const docH = document.documentElement.scrollHeight - window.innerHeight;
    const progress = docH > 0 ? (window.scrollY / docH) * 100 : 0;
    bar.style.width = progress + '%';
  });
});
