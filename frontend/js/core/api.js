/* ============================================================
   GeoAnalytica — API Client
   All fetch() wrappers for every backend endpoint
   ============================================================ */

const API = {
  base: '/api',

  // ── Core Request ─────────────────────────────────────────
  async request(method, path, body = null, options = {}) {
    const token = localStorage.getItem('ga_access_token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    let res;
    try {
      res = await fetch(API.base + path, {
        method,
        headers,
        body: body ? JSON.stringify(body) : null,
        ...options,
      });
    } catch (err) {
      throw new Error('Network error — please check your connection.');
    }

    // Handle 401 — try refresh
    if (res.status === 401) {
      const refreshed = await API.refreshToken();
      if (!refreshed) {
        localStorage.removeItem('ga_access_token');
        localStorage.removeItem('ga_refresh_token');
        if (!window.location.pathname.includes('login')) {
          window.location.href = '/login.html';
        }
        return null;
      }
      return API.request(method, path, body, options);
    }

    if (res.status === 204) return null;

    if (!res.ok) {
      let errMsg = `HTTP ${res.status}`;
      try {
        const err = await res.json();
        errMsg = err.detail || err.message || errMsg;
      } catch (_) { /* ignore */ }
      throw new Error(errMsg);
    }

    return res.json();
  },

  get:    (path)        => API.request('GET',    path),
  post:   (path, body)  => API.request('POST',   path, body),
  put:    (path, body)  => API.request('PUT',    path, body),
  patch:  (path, body)  => API.request('PATCH',  path, body),
  delete: (path)        => API.request('DELETE', path),

  // ── Token Refresh ────────────────────────────────────────
  async refreshToken() {
    const refresh = localStorage.getItem('ga_refresh_token');
    if (!refresh) return false;
    try {
      const res = await fetch(API.base + '/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      localStorage.setItem('ga_access_token', data.access_token);
      if (data.refresh_token) {
        localStorage.setItem('ga_refresh_token', data.refresh_token);
      }
      return true;
    } catch {
      return false;
    }
  },

  // ── File Download ────────────────────────────────────────
  async downloadFile(path, filename) {
    const token = localStorage.getItem('ga_access_token');
    const res = await fetch(API.base + path, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Download failed');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  // ── Auth ─────────────────────────────────────────────────
  auth: {
    login:    (email, password) => API.post('/auth/login', { email, password }),
    register: (data)            => API.post('/auth/register', data),
    logout:   (refresh_token)   => API.post('/auth/logout', { refresh_token }),
    me:       ()                => API.get('/auth/me'),
    refresh:  (refresh_token)   => API.post('/auth/refresh', { refresh_token }),
  },

  // ── Users ────────────────────────────────────────────────
  users: {
    me:             ()     => API.get('/users/me'),
    update:         (data) => API.put('/users/me', data),
    changePassword: (data) => API.post('/users/me/change-password', data),
    stats:          ()     => API.get('/users/me/stats'),
    tier:           ()     => API.get('/users/me/tier'),
    upgrade:        ()     => API.post('/users/me/upgrade', {}),
    downgrade:      ()     => API.post('/users/me/downgrade', {}),
  },

  // ── Admin (requires is_admin=true) ─────────────────────────────
  admin: {
    listUsers:    (tier)         => API.get('/admin/users' + (tier ? `?tier=${tier}` : '')),
    getUser:      (id)           => API.get(`/admin/users/${id}`),
    setTier:      (id, tier)     => API.patch(`/admin/users/${id}/tier`, { tier }),
    toggleActive: (id)           => API.patch(`/admin/users/${id}/active`, {}),
  },

  // ── Projects ─────────────────────────────────────────────
  projects: {
    list:   ()              => API.get('/projects'),
    create: (data)          => API.post('/projects', data),
    get:    (id)            => API.get(`/projects/${id}`),
    update: (id, data)      => API.put(`/projects/${id}`, data),
    delete: (id)            => API.delete(`/projects/${id}`),
  },

  // ── Queries ──────────────────────────────────────────────
  queries: {
    create:  (data)         => API.post('/queries', data),
    get:     (id)           => API.get(`/queries/${id}`),
    history: (projectId)    => API.get(`/queries/history${projectId ? '?project_id=' + projectId : ''}`),
    rerun:   (id)           => API.post(`/queries/${id}/rerun`, {}),
    delete:  (id)           => API.delete(`/queries/${id}`),
  },

  // ── Results ──────────────────────────────────────────────
  results: {
    get:         (queryId)          => API.get(`/results/${queryId}`),
    geojson:     (queryId)          => API.get(`/results/${queryId}/geojson`),
    timeline:    (queryId)          => API.get(`/results/${queryId}/timeline`),
    country:     (queryId, code)    => API.get(`/results/${queryId}/country/${code}`),
  },

  // ── Datasources ──────────────────────────────────────────
  datasources: {
    list:   (projectId) => API.get(`/datasources?project_id=${projectId}`),
    delete: (id)        => API.delete(`/datasources/${id}`),
    upload: async (projectId, file) => {
      const token = localStorage.getItem('ga_access_token');
      const fd = new FormData();
      fd.append('file', file);
      fd.append('project_id', projectId);
      const res = await fetch(API.base + '/datasources/upload', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: fd,
      });
      if (!res.ok) throw new Error('Upload failed');
      return res.json();
    },
  },

  // ── API Keys ─────────────────────────────────────────────
  apiKeys: {
    list:   ()          => API.get('/api-keys'),
    add:    (data)      => API.post('/api-keys', data),
    test:   (id)        => API.post(`/api-keys/${id}/test`, {}),
    delete: (id)        => API.delete(`/api-keys/${id}`),
  },

  // ── Alerts ───────────────────────────────────────────────
  alerts: {
    list:    ()          => API.get('/alerts'),
    create:  (data)      => API.post('/alerts', data),
    get:     (id)        => API.get(`/alerts/${id}`),
    update:  (id, data)  => API.put(`/alerts/${id}`, data),
    toggle:  (id)        => API.post(`/alerts/${id}/toggle`, {}),
    delete:  (id)        => API.delete(`/alerts/${id}`),
    history: (id)        => API.get(`/alerts/${id}/history`),
  },

  // ── Exports ──────────────────────────────────────────────
  exports: {
    download: async (queryId, format) => {
      const ext = format;
      const filename = `geoanalytica_${queryId.slice(0,8)}.${ext}`;
      await API.downloadFile(`/exports/${queryId}/${format}`, filename);
    },
    schedule: (data) => API.post('/exports/schedule', data),
  },

  // ── Health ───────────────────────────────────────────────
  health: () => API.get('/health'),
};

window.API = API;
