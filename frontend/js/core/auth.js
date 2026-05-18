/* ============================================================
   GeoAnalytica — Auth
   Login, logout, token management, page guards
   ============================================================ */

const Auth = {
  TOKEN_KEY:   'ga_access_token',
  REFRESH_KEY: 'ga_refresh_token',
  USER_KEY:    'ga_user',

  // ── Token Helpers ─────────────────────────────────────────
  getToken()   { return localStorage.getItem(Auth.TOKEN_KEY); },
  getRefresh() { return localStorage.getItem(Auth.REFRESH_KEY); },

  setTokens(access, refresh) {
    localStorage.setItem(Auth.TOKEN_KEY, access);
    if (refresh) localStorage.setItem(Auth.REFRESH_KEY, refresh);
  },

  clearTokens() {
    localStorage.removeItem(Auth.TOKEN_KEY);
    localStorage.removeItem(Auth.REFRESH_KEY);
    localStorage.removeItem(Auth.USER_KEY);
    GeoAnalytica.state.user = null;
  },

  isLoggedIn() { return !!Auth.getToken(); },

  // ── Login ────────────────────────────────────────────────
  async login(email, password) {
    const data = await API.auth.login(email, password);
    Auth.setTokens(data.access_token, data.refresh_token);

    // Fetch user profile
    const user = await API.auth.me();
    GeoAnalytica.state.user = user;
    localStorage.setItem(Auth.USER_KEY, JSON.stringify(user));

    window.location.href = '/dashboard.html';
  },

  // ── Logout ───────────────────────────────────────────────
  async logout() {
    const refresh = Auth.getRefresh();
    try {
      if (refresh) await API.auth.logout(refresh);
    } catch (_) { /* ignore */ }
    Auth.clearTokens();
    window.location.href = '/login.html';
  },

  // ── Check Auth (for guarded pages) ───────────────────────
  async checkAuth() {
    if (!Auth.getToken()) return false;

    // Try cached user first
    const cached = localStorage.getItem(Auth.USER_KEY);
    if (cached) {
      try {
        GeoAnalytica.state.user = JSON.parse(cached);
      } catch (_) { /* ignore */ }
    }

    // Verify token is still valid
    try {
      const user = await API.auth.me();
      GeoAnalytica.state.user = user;
      localStorage.setItem(Auth.USER_KEY, JSON.stringify(user));
      return true;
    } catch (err) {
      if (err.message && err.message.includes('401')) {
        // Try refresh
        const refreshed = await API.refreshToken();
        if (refreshed) {
          try {
            const user = await API.auth.me();
            GeoAnalytica.state.user = user;
            localStorage.setItem(Auth.USER_KEY, JSON.stringify(user));
            return true;
          } catch (_) { /* fall through */ }
        }
      }
      Auth.clearTokens();
      return false;
    }
  },

  // ── Guards ───────────────────────────────────────────────
  async guardPage() {
    const ok = await Auth.checkAuth();
    if (!ok) {
      const current = encodeURIComponent(window.location.href);
      window.location.href = `/login.html?redirect=${current}`;
    }
    return ok;
  },

  async requireGuest() {
    if (Auth.isLoggedIn()) {
      window.location.href = '/dashboard.html';
    }
  },

  // ── User helpers ─────────────────────────────────────────
  getUser() {
    if (GeoAnalytica.state.user) return GeoAnalytica.state.user;
    const cached = localStorage.getItem(Auth.USER_KEY);
    if (cached) {
      try { return JSON.parse(cached); }
      catch (_) { return null; }
    }
    return null;
  },

  getUserInitials(name) {
    if (!name) return '?';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0][0].toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  },

  getUserTierBadge(tier) {
    if (tier === 'pro') return '<span class="badge badge-blue">Pro</span>';
    return '<span class="badge badge-muted">Free</span>';
  },
};

window.Auth = Auth;
