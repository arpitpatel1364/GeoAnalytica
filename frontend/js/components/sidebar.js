/* ============================================================
   GeoAnalytica — Sidebar Component
   ============================================================ */

const Sidebar = {
  init() {
    const user = Auth.getUser();
    if (!user) return;

    // Set user info
    const avatar = document.getElementById('sidebar-avatar');
    const userName = document.getElementById('sidebar-user-name');
    const userTier = document.getElementById('sidebar-user-tier');

    if (avatar)   avatar.textContent   = Auth.getUserInitials(user.full_name);
    if (userName) userName.textContent = user.full_name;
    if (userTier) userTier.textContent = user.tier.charAt(0).toUpperCase() + user.tier.slice(1) + ' plan';

    // Highlight active nav item
    const currentPage = window.location.pathname.split('/').pop();
    document.querySelectorAll('.nav-item[data-page]').forEach(item => {
      item.classList.toggle('active', item.dataset.page === currentPage);
    });

    // Logout handler
    const logoutBtn = document.getElementById('sidebar-logout');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => Auth.logout());
    }

    // Theme toggle
    const themeToggle = document.getElementById('sidebar-theme-toggle');
    if (themeToggle) {
      themeToggle.addEventListener('click', () => {
        GeoAnalytica.toggleTheme();
        const isDark = GeoAnalytica.state.theme === 'dark';
        themeToggle.title = isDark ? 'Switch to light mode' : 'Switch to dark mode';
      });
    }
  },

  // Render project list in sidebar
  renderProjects(projects) {
    const container = document.getElementById('sidebar-projects');
    if (!container) return;

    if (!projects || projects.length === 0) {
      container.innerHTML = `<div style="padding:4px 12px;font-size:11px;color:var(--text-muted);">No projects yet</div>`;
      return;
    }

    container.innerHTML = projects.slice(0, 8).map(p => `
      <a href="/analysis.html?project=${p.id}"
         class="nav-item"
         data-page="analysis.html"
         title="${GeoAnalytica.truncate(p.name, 40)}">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="4" cy="8" r="1.5" fill="currentColor" stroke="none"/>
        </svg>
        <span class="truncate" style="flex:1">${GeoAnalytica.truncate(p.name, 24)}</span>
        <span class="nav-item-count">${p.query_count}</span>
      </a>
    `).join('');
  },
};

window.Sidebar = Sidebar;
