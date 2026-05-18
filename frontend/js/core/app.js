/* ============================================================
   GeoAnalytica — Core App
   Global state, initialization, utility functions
   ============================================================ */

window.GeoAnalytica = {
  state: {
    user: null,
    currentProject: null,
    currentQuery: null,
    currentResult: null,
    activeModal: null,
    theme: localStorage.getItem('ga_theme') || 'dark',
    mapInstance: null,
    wsConnection: null,
  },
  config: {
    apiBase: '/api',
    wsBase: (window.location.protocol === 'https:' ? 'wss://' : 'ws://') +
            window.location.host + '/api/ws',
  },

  // ── Initialization ──────────────────────────────────────
  init() {
    GeoAnalytica.applyTheme(GeoAnalytica.state.theme);
    document.addEventListener('DOMContentLoaded', () => {
      GeoAnalytica.applyTheme(GeoAnalytica.state.theme);
    });
  },

  // ── Theme ────────────────────────────────────────────────
  applyTheme(theme) {
    GeoAnalytica.state.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('ga_theme', theme);
  },

  toggleTheme() {
    const current = GeoAnalytica.state.theme;
    const next = current === 'dark' ? 'light' : 'dark';
    GeoAnalytica.applyTheme(next);
  },

  // ── Navigation ───────────────────────────────────────────
  navigate(url) {
    window.location.href = url;
  },

  getParam(key) {
    return new URLSearchParams(window.location.search).get(key);
  },

  // ── Formatters ───────────────────────────────────────────
  formatDate(isoString) {
    if (!isoString) return '—';
    const d = new Date(isoString);
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  },

  formatDateTime(isoString) {
    if (!isoString) return '—';
    const d = new Date(isoString);
    return d.toLocaleString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  },

  formatNumber(n, decimals = 2) {
    if (n === null || n === undefined || isNaN(n)) return '—';
    const num = parseFloat(n);
    if (Math.abs(num) >= 1e12) return (num / 1e12).toFixed(decimals) + 'T';
    if (Math.abs(num) >= 1e9)  return (num / 1e9).toFixed(decimals) + 'B';
    if (Math.abs(num) >= 1e6)  return (num / 1e6).toFixed(decimals) + 'M';
    if (Math.abs(num) >= 1e3)  return num.toLocaleString('en-US', { maximumFractionDigits: decimals });
    return num.toFixed(decimals);
  },

  formatPercent(n, decimals = 1) {
    if (n === null || n === undefined || isNaN(n)) return '—';
    return parseFloat(n).toFixed(decimals) + '%';
  },

  formatRelativeTime(isoString) {
    if (!isoString) return '—';
    const diff = Date.now() - new Date(isoString).getTime();
    const mins = Math.floor(diff / 60000);
    const hrs  = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    if (mins < 1)   return 'just now';
    if (mins < 60)  return `${mins}m ago`;
    if (hrs < 24)   return `${hrs}h ago`;
    if (days < 30)  return `${days}d ago`;
    return GeoAnalytica.formatDate(isoString);
  },

  // ── Confidence ───────────────────────────────────────────
  getConfidenceClass(score) {
    if (score === null || score === undefined) return 'conf-null';
    if (score >= 0.8) return 'conf-high';
    if (score >= 0.5) return 'conf-medium';
    if (score > 0.0)  return 'conf-low';
    return 'conf-null';
  },

  getConfidenceLabel(score) {
    if (score === null || score === undefined) return 'No data';
    if (score >= 0.8) return 'High';
    if (score >= 0.5) return 'Medium';
    if (score > 0.0)  return 'Low';
    return 'No data';
  },

  // ── Utilities ────────────────────────────────────────────
  debounce(fn, ms) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), ms);
    };
  },

  throttle(fn, ms) {
    let last = 0;
    return function (...args) {
      const now = Date.now();
      if (now - last >= ms) {
        last = now;
        fn.apply(this, args);
      }
    };
  },

  truncate(str, len = 80) {
    if (!str) return '';
    return str.length > len ? str.slice(0, len) + '…' : str;
  },

  slugify(str) {
    return str.toLowerCase().replace(/\s+/g, '-').replace(/[^\w-]/g, '');
  },

  generateId() {
    return Math.random().toString(36).slice(2, 10);
  },

  // ── DOM helpers ──────────────────────────────────────────
  el(id) {
    return document.getElementById(id);
  },

  qs(selector, parent = document) {
    return parent.querySelector(selector);
  },

  qsAll(selector, parent = document) {
    return [...parent.querySelectorAll(selector)];
  },

  show(el) {
    if (typeof el === 'string') el = document.getElementById(el);
    if (el) el.hidden = false;
  },

  hide(el) {
    if (typeof el === 'string') el = document.getElementById(el);
    if (el) el.hidden = true;
  },

  setHTML(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  },

  setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  },

  // ── Copy to clipboard ─────────────────────────────────────
  async copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      return true;
    }
  },

  // ── SVG Icons ─────────────────────────────────────────────
  icon: {
    dashboard: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="1" width="6" height="6" rx="1"/><rect x="9" y="1" width="6" height="6" rx="1"/><rect x="1" y="9" width="6" height="6" rx="1"/><rect x="9" y="9" width="6" height="6" rx="1"/></svg>`,
    analysis:  `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M8 4v4l3 2"/></svg>`,
    alert:     `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2L14 13H2L8 2z"/><path d="M8 7v3M8 11.5v.5"/></svg>`,
    settings:  `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="2"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41"/></svg>`,
    project:   `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 4h12v9a1 1 0 01-1 1H3a1 1 0 01-1-1V4zM5 4V3a1 1 0 011-1h4a1 1 0 011 1v1"/></svg>`,
    plus:      `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3v10M3 8h10"/></svg>`,
    export:    `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 10V2M4 6l4 4 4-4M2 12v1a1 1 0 001 1h10a1 1 0 001-1v-1"/></svg>`,
    chart:     `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 12l3-4 3 2 3-5 3 3"/><path d="M2 14h12"/></svg>`,
    map:       `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M1 3l5-2 4 2 5-2v10l-5 2-4-2-5 2V3z"/><path d="M6 1v10M10 3v10"/></svg>`,
    ai:        `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="3"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41"/></svg>`,
    key:       `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="5" cy="9" r="3"/><path d="M7.5 9H14l1-1-1-1h-2v2M12 9v2"/></svg>`,
    bell:      `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 1a5 5 0 015 5v3l1.5 2.5H1.5L3 9V6a5 5 0 015-5z"/><path d="M6 13a2 2 0 004 0"/></svg>`,
    user:      `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="5" r="3"/><path d="M2 14a6 6 0 0112 0"/></svg>`,
    logout:    `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 3H3a1 1 0 00-1 1v8a1 1 0 001 1h3M10 11l3-3-3-3M13 8H6"/></svg>`,
    trash:     `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 4h12M5 4V2h6v2M6 7v5M10 7v5M3 4l1 9a1 1 0 001 1h6a1 1 0 001-1l1-9"/></svg>`,
    edit:      `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M11 2l3 3-8 8H3v-3l8-8z"/><path d="M9 4l3 3"/></svg>`,
    check:     `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 8l4 4 8-8"/></svg>`,
    copy:      `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="5" y="5" width="9" height="9" rx="1"/><path d="M3 11H2a1 1 0 01-1-1V2a1 1 0 011-1h8a1 1 0 011 1v1"/></svg>`,
    globe:     `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M8 2a9 9 0 010 12M2 8h12"/><path d="M5 4.5C5.5 6 7 7 8 8s2.5 2 3 3.5"/></svg>`,
    search:    `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="6.5" cy="6.5" r="4.5"/><path d="M10 10l3 3"/></svg>`,
    expand:    `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M1 5V1h4M11 1h4v4M15 11v4h-4M5 15H1v-4"/></svg>`,
  },
};

// Auto-init
GeoAnalytica.init();
