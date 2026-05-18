/* ============================================================
   GeoAnalytica — Topbar Component
   ============================================================ */

const Topbar = {
  init() {
    const user = Auth.getUser();
    if (!user) return;

    // User avatar / menu
    const avatar = document.getElementById('topbar-avatar');
    const userName = document.getElementById('topbar-user-name');
    if (avatar)   avatar.textContent   = Auth.getUserInitials(user.full_name);
    if (userName) userName.textContent = user.full_name;

    // Dropdown toggle
    const userBtn = document.getElementById('topbar-user-btn');
    const dropdown = document.getElementById('topbar-dropdown');
    if (userBtn && dropdown) {
      userBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('open');
      });
      document.addEventListener('click', () => dropdown.classList.remove('open'));
    }

    // Logout
    const logoutBtn = document.getElementById('topbar-logout');
    if (logoutBtn) logoutBtn.addEventListener('click', () => Auth.logout());

    // Theme toggle
    const themeBtn = document.getElementById('topbar-theme');
    if (themeBtn) {
      themeBtn.addEventListener('click', () => GeoAnalytica.toggleTheme());
    }
  },

  setBreadcrumb(parts) {
    const el = document.getElementById('topbar-breadcrumb');
    if (!el) return;
    el.innerHTML = parts.map((p, i) =>
      i < parts.length - 1
        ? `<a href="${p.href || '#'}" class="breadcrumb-link">${p.label}</a><span class="breadcrumb-sep">/</span>`
        : `<span class="breadcrumb-current">${p.label}</span>`
    ).join('');
  },
};

window.Topbar = Topbar;
