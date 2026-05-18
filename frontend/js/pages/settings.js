/* ============================================================
   GeoAnalytica — Settings Page
   Handles: API keys, Account, Preferences, Usage + Plan/Tier
   ============================================================ */

const SettingsPage = {
  // Known API key services shown in the API Keys tab
  SERVICES: [
    { id: 'world_bank',   name: 'World Bank',     desc: 'GDP, population, trade — free, no key required', free: true,  getKeyUrl: null },
    { id: 'imf',          name: 'IMF',             desc: 'Economic indicators — free, no key required',    free: true,  getKeyUrl: null },
    { id: 'open_meteo',   name: 'Open-Meteo',      desc: 'Weather & climate data — free, no key required', free: true,  getKeyUrl: null },
    { id: 'restcountries',name: 'REST Countries',  desc: 'Country metadata — free, no key required',       free: true,  getKeyUrl: null },
    { id: 'brave',        name: 'Brave Search',    desc: 'Real-time web search intelligence',              free: false, getKeyUrl: 'https://api.search.brave.com/' },
    { id: 'serp',         name: 'SerpAPI',         desc: 'Google search results & trends',                 free: false, getKeyUrl: 'https://serpapi.com/' },
    { id: 'openai',       name: 'OpenAI',          desc: 'AI-enhanced data enrichment',                    free: false, getKeyUrl: 'https://platform.openai.com/api-keys' },
    { id: 'alpha_vantage',name: 'Alpha Vantage',   desc: 'Financial market data',                          free: false, getKeyUrl: 'https://www.alphavantage.co/support/' },
  ],

  _userTier: 'free',
  _existingKeys: [],
  _pendingKeyId: null,

  async init() {
    const ok = await Auth.guardPage();
    if (!ok) return;

    Sidebar.init();
    Topbar.init();

    try {
      const projects = await API.projects.list();
      Sidebar.renderProjects(projects);
    } catch (_) {}

    // Tab switching
    document.querySelectorAll('.tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        const panel = document.getElementById(tab.dataset.tab);
        if (panel) panel.classList.add('active');
      });
    });

    // Load everything in parallel
    await Promise.allSettled([
      SettingsPage._loadProfile(),
      SettingsPage._loadApiKeys(),
      SettingsPage._loadUsageAndTier(),
    ]);
  },

  // ── Profile ──────────────────────────────────────────────────────────────────
  async _loadProfile() {
    try {
      const user = await API.users.me();
      const nameEl  = document.getElementById('account-name');
      const emailEl = document.getElementById('account-email');
      if (nameEl)  nameEl.value  = user.full_name || '';
      if (emailEl) emailEl.value = user.email || '';
    } catch (_) {}
  },

  async saveAccount() {
    const name = document.getElementById('account-name')?.value?.trim();
    if (!name) { Toast.error('Full name cannot be empty'); return; }
    try {
      await API.users.update({ full_name: name });
      Toast.success('Profile updated!');
    } catch (e) {
      Toast.error('Failed to update profile: ' + e.message);
    }
  },

  async changePassword() {
    const current = document.getElementById('current-password')?.value;
    const next    = document.getElementById('new-password')?.value;
    const confirm = document.getElementById('confirm-new-password')?.value;
    if (!current || !next) { Toast.error('Please fill in all password fields'); return; }
    if (next !== confirm)  { Toast.error('New passwords do not match'); return; }
    if (next.length < 8)   { Toast.error('Password must be at least 8 characters'); return; }
    try {
      await API.users.changePassword({ current_password: current, new_password: next });
      Toast.success('Password changed successfully!');
      ['current-password','new-password','confirm-new-password'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });
    } catch (e) {
      Toast.error('Failed: ' + e.message);
    }
  },

  // ── API Keys ──────────────────────────────────────────────────────────────────
  async _loadApiKeys() {
    try {
      this._existingKeys = await API.apiKeys.list();
    } catch (_) {
      this._existingKeys = [];
    }
    this._renderKeysList();
  },

  _renderKeysList() {
    const container = document.getElementById('api-keys-list');
    if (!container) return;

    container.innerHTML = '';
    for (const svc of SettingsPage.SERVICES) {
      const existing = SettingsPage._existingKeys.find(k => k.service_name === svc.id);
      const card = document.createElement('div');
      card.className = 'card';
      card.style.cssText = 'padding:var(--space-4)';
      card.innerHTML = `
        <div style="display:flex;align-items:center;gap:var(--space-4)">
          <div style="flex:1;min-width:0">
            <div style="font-size:var(--text-sm);font-weight:600;color:var(--text-primary)">${svc.name}</div>
            <div style="font-size:var(--text-xs);color:var(--text-muted);margin-top:2px">${svc.desc}</div>
          </div>
          ${svc.free
            ? `<span style="font-size:11px;padding:2px 8px;border-radius:999px;background:rgba(63,185,80,.12);color:#3fb950;border:1px solid rgba(63,185,80,.25)">Free</span>`
            : existing
              ? `<span style="font-size:11px;padding:2px 8px;border-radius:999px;background:rgba(63,185,80,.12);color:#3fb950;border:1px solid rgba(63,185,80,.25)">● Connected</span>
                 <button class="btn btn-ghost btn-sm" onclick="SettingsPage._deleteKey('${existing.id}','${svc.name}')">Remove</button>`
              : `<button class="btn btn-secondary btn-sm" onclick="SettingsPage._openAddKey('${svc.id}','${svc.name}','${svc.getKeyUrl||''}')">Add Key</button>`
          }
        </div>
      `;
      container.appendChild(card);
    }
  },

  _openAddKey(serviceId, serviceName, getKeyUrl) {
    SettingsPage._pendingKeyId = null;
    const nameEl = document.getElementById('add-key-service-name');
    const idEl   = document.getElementById('add-key-service-id');
    const inputEl = document.getElementById('add-key-input');
    if (nameEl)  nameEl.textContent = serviceName;
    if (idEl)    idEl.value         = serviceId;
    if (inputEl) inputEl.value      = '';

    const errEl = document.getElementById('add-key-error');
    const okEl  = document.getElementById('add-key-success');
    const saveBtn = document.getElementById('save-key-btn');
    if (errEl)   errEl.hidden   = true;
    if (okEl)    okEl.hidden    = true;
    if (saveBtn) saveBtn.disabled = true;

    const getLink = document.getElementById('add-key-get-link');
    if (getLink) {
      getLink.href   = getKeyUrl || '#';
      getLink.hidden = !getKeyUrl;
    }
    Modal.open('add-key-modal');
  },

  async testAndSaveKey() {
    const key = document.getElementById('add-key-input')?.value?.trim();
    const svc = document.getElementById('add-key-service-id')?.value;
    if (!key) { Toast.error('Please enter an API key'); return; }

    const btn = document.getElementById('test-key-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Testing…'; }

    try {
      const created = await API.apiKeys.add({ service_name: svc, api_key: key });
      const testRes = await API.apiKeys.test(created.id);
      SettingsPage._pendingKeyId = created.id;

      const saveBtn = document.getElementById('save-key-btn');
      if (saveBtn) saveBtn.disabled = false;

      const okEl = document.getElementById('add-key-success');
      if (okEl) {
        okEl.hidden = false;
        okEl.querySelector('.notice-text').textContent = testRes?.message || 'Connection successful!';
      }
      const errEl = document.getElementById('add-key-error');
      if (errEl) errEl.hidden = true;
    } catch (e) {
      const errEl = document.getElementById('add-key-error');
      if (errEl) {
        errEl.hidden = false;
        errEl.querySelector('.notice-text').textContent = e.message;
      }
      const okEl = document.getElementById('add-key-success');
      if (okEl) okEl.hidden = true;
    } finally {
      if (btn) { btn.textContent = 'Test Connection'; btn.disabled = false; }
    }
  },

  async saveKey() {
    Modal.close('add-key-modal');
    Toast.success('API key saved!');
    await SettingsPage._loadApiKeys();
  },

  async _deleteKey(keyId, serviceName) {
    const ok = await Confirm.show({
      title:       `Remove ${serviceName} Key`,
      message:     `Remove the ${serviceName} API key? This cannot be undone.`,
      confirmText: 'Remove',
      cancelText:  'Cancel',
      danger:      true,
    });
    if (!ok) return;
    try {
      await API.apiKeys.delete(keyId);
      Toast.success(`${serviceName} key removed`);
      await SettingsPage._loadApiKeys();
    } catch (e) {
      Toast.error('Failed to remove key: ' + e.message);
    }
  },

  // ── Usage + Tier ───────────────────────────────────────────────────────────────
  async _loadUsageAndTier() {
    try {
      const stats = await API.users.stats();
      const el = id => document.getElementById(id);
      if (el('usage-queries-today'))  el('usage-queries-today').textContent  = stats.queries_today;
      if (el('usage-queries-month'))  el('usage-queries-month').textContent  = stats.total_queries_month;
      if (el('usage-api-keys'))       el('usage-api-keys').textContent       = stats.api_keys_connected;
      if (el('usage-alerts'))         el('usage-alerts').textContent         = stats.alerts_active;
      if (el('usage-queries-label'))  el('usage-queries-label').textContent  =
        `${stats.queries_today} / ${stats.queries_today_limit} today`;
      const pct = Math.min(100, (stats.queries_today / Math.max(stats.queries_today_limit, 1)) * 100);
      if (el('usage-queries-fill'))   el('usage-queries-fill').style.width   = pct + '%';
    } catch (_) {}

    try {
      const tierInfo = await API.users.tier();
      SettingsPage._userTier = tierInfo.tier;
      SettingsPage._renderTierCard(tierInfo);
    } catch (_) {}
  },

  _renderTierCard(tierInfo) {
    const badge   = document.getElementById('plan-badge');
    const freeDiv = document.getElementById('plan-free');
    const proDiv  = document.getElementById('plan-pro');
    if (!badge) return;

    if (tierInfo.tier === 'pro') {
      badge.textContent      = '★ Pro';
      badge.style.background = 'rgba(210,153,34,.15)';
      badge.style.color      = '#d29922';
      badge.style.border     = '1px solid rgba(210,153,34,.3)';

      const L = tierInfo.limits || {};
      const setTxt = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
      setTxt('pro-limit-qpd',  L.queries_per_day  || 500);
      setTxt('pro-limit-fpq',  L.fields_per_query || 20);
      setTxt('pro-limit-rows', L.export_rows ? (L.export_rows >= 100000 ? '500K' : L.export_rows) : '500K');

      if (freeDiv) freeDiv.hidden = true;
      if (proDiv)  proDiv.hidden  = false;
    } else {
      badge.textContent      = 'Free';
      badge.style.background = 'rgba(47,129,247,.15)';
      badge.style.color      = '#2f81f7';
      badge.style.border     = '1px solid rgba(47,129,247,.3)';

      if (freeDiv) freeDiv.hidden = false;
      if (proDiv)  proDiv.hidden  = true;
    }
  },

  async upgradeToPro() {
    const btn = document.getElementById('upgrade-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Upgrading…'; }
    try {
      await API.users.upgrade();
      Toast.success('🎉 Welcome to Pro! Your plan is being refreshed…');
      setTimeout(() => window.location.reload(), 1300);
    } catch (e) {
      Toast.error('Upgrade failed: ' + e.message);
      if (btn) { btn.disabled = false; btn.textContent = '★ Upgrade to Pro'; }
    }
  },

  async downgradeToFree() {
    const ok = await Confirm.show({
      title: 'Downgrade to Free',
      message: 'Downgrade to the Free plan? Limits (20 queries/day, 5 fields/query) apply immediately.',
      confirmText: 'Downgrade',
      cancelText: 'Cancel',
      danger: true
    });
    if (!ok) return;
    const btn = document.getElementById('downgrade-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Downgrading…'; }
    try {
      await API.users.downgrade();
      Toast.success('Downgraded to Free plan.');
      setTimeout(() => window.location.reload(), 1300);
    } catch (e) {
      Toast.error('Downgrade failed: ' + e.message);
      if (btn) { btn.disabled = false; btn.textContent = 'Downgrade to Free'; }
    }
  },
};

window.SettingsPage = SettingsPage;
document.addEventListener('DOMContentLoaded', () => SettingsPage.init());
