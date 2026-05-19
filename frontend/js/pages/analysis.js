/* ============================================================
   GeoAnalytica — Analysis Page
   ============================================================ */

const AnalysisPage = {
  async init() {
    const ok = await Auth.guardPage();
    if (!ok) return;

    Sidebar.init();
    Topbar.init();

    const projectId = GeoAnalytica.getParam('project');
    if (!projectId) {
      Toast.error('No project selected');
      setTimeout(() => window.location.href = '/dashboard.html', 1500);
      return;
    }

    // Load project info
    try {
      const project = await API.projects.get(projectId);
      GeoAnalytica.state.currentProject = project;
      Topbar.setBreadcrumb([
        { label: 'Dashboard', href: '/dashboard.html' },
        { label: project.name, href: `/analysis.html?project=${projectId}` },
        { label: 'Analysis' },
      ]);
      document.title = `${project.name} — GeoAnalytica`;
    } catch (e) {
      Toast.error('Project not found');
    }

    // Load sidebar projects
    try {
      const projects = await API.projects.list();
      Sidebar.renderProjects(projects);
    } catch (_) {}

    // Init map
    await WorldMap.init('world-map');

    // Init query builder
    QueryBuilder.init();
    NLPInput.init('nl-instruction');
    Progress.renderStages('progress-stages');

    // Map controls
    document.getElementById('metric-select')?.addEventListener('change', (e) => {
      if (GeoAnalytica.state.currentResult) {
        const pts = GeoAnalytica.state.currentResult.data_points.filter(
          p => p.field_name === e.target.value
        );
        Choropleth.render(pts, e.target.value);
      }
    });

    document.getElementById('opacity-slider')?.addEventListener('input', (e) => {
      Choropleth.setOpacity(e.target.value);
    });

    document.querySelectorAll('.layer-toggle-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.layer-toggle-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });

    // Export quick actions
    document.querySelectorAll('.export-btn[data-format]').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!GeoAnalytica.state.currentQuery) {
          Toast.warning('Run a query first');
          return;
        }
        try {
          await API.exports.download(GeoAnalytica.state.currentQuery.id, btn.dataset.format);
          Toast.success('Download started');
        } catch (e) {
          Toast.error('Export failed: ' + e.message);
        }
      });
    });

    // Restore previous query if URL has query param
    const queryId = GeoAnalytica.getParam('query');
    if (queryId) {
      try {
        const [query, result] = await Promise.all([
          API.queries.get(queryId),
          API.results.get(queryId),
        ]);
        GeoAnalytica.state.currentQuery = query;
        GeoAnalytica.state.currentResult = result;
        ResultsPanel.render(result);

        const primary = [...new Set(result.data_points.map(p => p.field_name))][0];
        const pts = result.data_points.filter(p => p.field_name === primary);
        Choropleth.render(pts, primary);

        const years = [...new Set(result.data_points.map(p => p.timestamp.slice(0, 4)))].sort();
        Timeline.init('timeline-container', years, result.data_points);

        // Pre-fill NL textarea
        const ta = document.getElementById('nl-instruction');
        if (ta) ta.value = query.instruction_text;
      } catch (_) {}
    }

    // Load tier info and decorate UI accordingly
    try {
      const tierInfo = await API.users.tier();
      GeoAnalytica.state.userTier = tierInfo.tier;
      AnalysisPage._applyTierUI(tierInfo);
    } catch (_) {}
  },

  _applyTierUI(tierInfo) {
    // Add badge next to user name in topbar
    const nameEl = document.getElementById('topbar-user-name');
    if (nameEl && tierInfo.tier === 'pro') {
      if (!nameEl.querySelector('.tier-badge')) {
        const badge = document.createElement('span');
        badge.className = 'tier-badge';
        badge.textContent = '★ Pro';
        badge.style.cssText = [
          'font-size:10px', 'font-weight:700', 'padding:1px 6px',
          'border-radius:999px', 'background:rgba(210,153,34,.2)',
          'color:#d29922', 'border:1px solid rgba(210,153,34,.4)',
          'margin-left:6px', 'vertical-align:middle', 'letter-spacing:.04em',
        ].join(';');
        nameEl.appendChild(badge);
      }
    }

    // Show upgrade banner for Free users
    if (tierInfo.tier !== 'pro') {
      const L = tierInfo.limits || {};
      const banner = document.createElement('div');
      banner.id = 'free-tier-banner';
      banner.style.cssText = [
        'background:linear-gradient(135deg,rgba(47,129,247,.12),rgba(210,153,34,.08))',
        'border:1px solid rgba(47,129,247,.25)', 'border-radius:8px',
        'padding:10px 16px', 'margin-bottom:12px',
        'display:flex', 'align-items:center', 'gap:12px',
        'font-size:12px', 'color:var(--text-muted)',
      ].join(';');
      banner.innerHTML = `
        <span style="color:#2f81f7;font-size:16px">ℹ</span>
        <span>
          <strong style="color:var(--text-primary)">Free plan:</strong>
          ${L.queries_per_day || 20} queries/day &nbsp;·&nbsp;
          ${L.fields_per_query || 5} fields/query &nbsp;·&nbsp;
          ${(L.export_rows || 5000).toLocaleString()} export rows.
        </span>
        <a href="/settings.html" style="margin-left:auto;white-space:nowrap;color:#d29922;font-weight:600;text-decoration:none">
          Upgrade to Pro →
        </a>
        <button onclick="this.parentElement.remove()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:16px;line-height:1;padding:0 4px">×</button>
      `;

      // Insert before query builder
      const builder = document.querySelector('.query-builder-panel, .query-panel, #nl-instruction');
      if (builder) {
        builder.parentElement.insertBefore(banner, builder);
      }
    }
  },
};

window.AnalysisPage = AnalysisPage;
// Only init on analysis.html — detected by the world-map canvas element
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('world-map')) AnalysisPage.init();
});


/* ============================================================
   GeoAnalytica — Results Page
   ============================================================ */

const ResultsPage = {
  async init() {
    const ok = await Auth.guardPage();
    if (!ok) return;

    Sidebar.init();
    Topbar.init();

    const queryId = GeoAnalytica.getParam('query');
    if (!queryId) {
      window.location.href = '/dashboard.html';
      return;
    }

    try {
      const [query, result] = await Promise.all([
        API.queries.get(queryId),
        API.results.get(queryId),
      ]);

      GeoAnalytica.state.currentQuery  = query;
      GeoAnalytica.state.currentResult = result;

      // Page header
      GeoAnalytica.setText('result-query-text',
        GeoAnalytica.truncate(query.instruction_text, 120));
      GeoAnalytica.setText('result-meta-points',
        GeoAnalytica.formatNumber(result.total_points, 0) + ' data points');
      GeoAnalytica.setText('result-meta-date',
        GeoAnalytica.formatDateTime(result.created_at));

      document.title = `Results — ${GeoAnalytica.truncate(query.instruction_text, 40)} — GeoAnalytica`;

      Topbar.setBreadcrumb([
        { label: 'Dashboard', href: '/dashboard.html' },
        { label: 'Results' },
      ]);

      // Render dashboard panels
      ResultsDashboard.init(result);

      // Export buttons
      document.querySelectorAll('[data-export-format]').forEach(btn => {
        btn.addEventListener('click', async () => {
          try {
            await API.exports.download(queryId, btn.dataset.exportFormat);
            Toast.success('Download started');
          } catch (e) { Toast.error('Export failed: ' + e.message); }
        });
      });

      // Re-run
      document.getElementById('rerun-btn')?.addEventListener('click', async () => {
        try {
          const newQ = await API.queries.rerun(queryId);
          window.location.href = `/analysis.html?project=${newQ.project_id}&query=${newQ.id}`;
        } catch (e) { Toast.error('Failed: ' + e.message); }
      });

      // Share button
      document.getElementById('share-btn')?.addEventListener('click', async () => {
        const url = window.location.href;
        await GeoAnalytica.copyToClipboard(url);
        Toast.success('Link copied to clipboard');
      });

      // Export modal
      document.getElementById('export-btn')?.addEventListener('click', () => {
        Modal.open('export-modal');
      });

      // Schedule export form
      document.getElementById('schedule-export-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const freq  = document.getElementById('schedule-freq')?.value;
        const email = document.getElementById('schedule-email')?.value;
        const fmt   = document.getElementById('schedule-format')?.value;
        try {
          await API.exports.schedule({
            query_id:           queryId,
            format:             fmt || 'csv',
            is_scheduled:       true,
            schedule_frequency: freq,
            schedule_email:     email,
          });
          Toast.success('Scheduled export set up!');
          Modal.close('export-modal');
        } catch (e) { Toast.error(e.message); }
      });

    } catch (e) {
      Toast.error('Failed to load results: ' + e.message);
      setTimeout(() => window.location.href = '/dashboard.html', 2000);
    }
  },
};

window.ResultsPage = ResultsPage;
// Only init on results.html — detected by result-query-text element
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('result-query-text')) ResultsPage.init();
});


/* ============================================================
   GeoAnalytica — Settings Page
   ============================================================ */

const SettingsPage = {
  async init() {
    const ok = await Auth.guardPage();
    if (!ok) return;

    Sidebar.init();
    Topbar.init();
    Topbar.setBreadcrumb([{ label: 'Dashboard', href: '/dashboard.html' }, { label: 'Settings' }]);

    // Tabs
    document.querySelectorAll('.tab[data-tab]').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(tab.dataset.tab)?.classList.add('active');
      });
    });

    await SettingsPage.loadApiKeys();
    await SettingsPage.loadUserInfo();
    SettingsPage.initPreferences();

    document.title = 'Settings — GeoAnalytica';
  },

  async loadApiKeys() {
    const container = document.getElementById('api-keys-list');
    if (!container) return;

    const services = [
      { id: 'world_bank',    name: 'World Bank',      icon: window.GeoAnalytica?.icon?.globe || 'WB', desc: 'GDP, inflation, demographics — full history to 1960', free: true,  keyUrl: null },
      { id: 'imf',           name: 'IMF',             icon: window.GeoAnalytica?.icon?.chart || 'IMF', desc: 'Macroeconomic datasets — WEO, IFS, DOTS', free: true,  keyUrl: null },
      { id: 'open_meteo',    name: 'Open-Meteo',      icon: window.GeoAnalytica?.icon?.ai || 'OM', desc: 'Historical weather and climate data', free: true,  keyUrl: null },
      { id: 'rest_countries',name: 'REST Countries',  icon: window.GeoAnalytica?.icon?.map || 'RC', desc: 'Country metadata, flags, coordinates', free: true,  keyUrl: null },
      { id: 'alpha_vantage', name: 'Alpha Vantage',   icon: window.GeoAnalytica?.icon?.chart || 'AV', desc: 'Stock prices, forex, economic indicators', free: false, keyUrl: 'https://www.alphavantage.co/support/#api-key' },
      { id: 'newsapi',       name: 'NewsAPI',         icon: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 2h12v12H2V2zm2 3h8M4 8h8M4 11h5"/></svg>`, desc: '70,000+ news sources, full-text search', free: false, keyUrl: 'https://newsapi.org/register' },
      { id: 'brave_search',  name: 'Brave Search',    icon: window.GeoAnalytica?.icon?.search || 'BS', desc: 'Improves web scraping quality', free: false, keyUrl: 'https://brave.com/search/api/' },
      { id: 'openweathermap',name: 'OpenWeatherMap',  icon: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="6" cy="10" r="3"/><path d="M12 9a3 3 0 00-5.83-1.03A3 3 0 006 10"/></svg>`, desc: 'Current weather, forecasts, historical', free: false, keyUrl: 'https://openweathermap.org/api' },
      { id: 'mapbox',        name: 'Mapbox',          icon: window.GeoAnalytica?.icon?.expand || 'MB', desc: 'Premium map tiles, geocoding', free: false, keyUrl: 'https://account.mapbox.com/' },
    ];

    let connectedKeys = [];
    try { connectedKeys = await API.apiKeys.list(); } catch (_) {}

    container.innerHTML = services.map(svc => {
      const connected = connectedKeys.find(k => k.service_name === svc.id);
      return `
        <div class="service-card" id="service-${svc.id}">
          <div class="service-icon">${svc.icon}</div>
          <div class="service-info">
            <div class="service-name">${svc.name}</div>
            <div class="service-desc">${svc.desc}</div>
          </div>
          <div class="service-actions">
            ${svc.free
              ? `<span class="badge badge-green">Always available</span>`
              : connected
                ? `<span class="badge badge-green" style="font-size:10px;">Connected</span>
                   <span style="font-size:10px;color:var(--text-muted);">${connected.key_preview}</span>
                   <button class="btn btn-ghost btn-xs" onclick="SettingsPage.removeKey('${connected.id}', '${svc.id}')">Remove</button>`
                : `${svc.keyUrl ? `<a href="${svc.keyUrl}" target="_blank" class="btn btn-ghost btn-xs">Get free key →</a>` : ''}
                   <button class="btn btn-secondary btn-sm" onclick="SettingsPage.openAddKey('${svc.id}', '${svc.name}', '${svc.keyUrl || ''}')">Add Key</button>`
            }
          </div>
        </div>
      `;
    }).join('');
  },

  openAddKey(serviceId, serviceName, keyUrl) {
    GeoAnalytica.setText('add-key-service-name', serviceName);
    document.getElementById('add-key-service-id').value = serviceId;
    const linkEl = document.getElementById('add-key-get-link');
    if (linkEl) { linkEl.href = keyUrl || '#'; linkEl.hidden = !keyUrl; }
    document.getElementById('add-key-input').value = '';
    document.getElementById('add-key-error').hidden = true;
    document.getElementById('add-key-success').hidden = true;
    Modal.open('add-key-modal');
  },

  async testAndSaveKey() {
    const serviceId = document.getElementById('add-key-service-id').value;
    const apiKey    = document.getElementById('add-key-input').value.trim();
    const testBtn   = document.getElementById('test-key-btn');
    const saveBtn   = document.getElementById('save-key-btn');
    const errEl     = document.getElementById('add-key-error');
    const successEl = document.getElementById('add-key-success');

    if (!apiKey) { if (errEl) { errEl.textContent = 'Please enter an API key.'; errEl.hidden = false; } return; }

    if (testBtn) { testBtn.disabled = true; testBtn.innerHTML = '<span class="spinner spinner-sm"></span> Testing…'; }
    if (errEl) errEl.hidden = true;
    if (successEl) successEl.hidden = true;

    try {
      // Add key first
      const added = await API.apiKeys.add({ service_name: serviceId, api_key: apiKey });
      // Then test it
      const result = await API.apiKeys.test(added.id);

      if (result.success) {
        if (successEl) { successEl.textContent = '✓ ' + result.message; successEl.hidden = false; }
        if (saveBtn) saveBtn.disabled = false;
      } else {
        if (errEl) { errEl.textContent = '✕ ' + result.message; errEl.hidden = false; }
        // Remove the key we just added
        await API.apiKeys.delete(added.id).catch(() => {});
      }
    } catch (e) {
      if (errEl) { errEl.textContent = e.message; errEl.hidden = false; }
    } finally {
      if (testBtn) { testBtn.disabled = false; testBtn.textContent = 'Test Connection'; }
    }
  },

  saveKey() {
    Modal.close('add-key-modal');
    Toast.success('API key saved!');
    SettingsPage.loadApiKeys();
  },

  async removeKey(keyId, serviceId) {
    const ok = await Confirm.show({ title: 'Remove API Key', message: 'Remove this API key?', confirmText: 'Remove', danger: true });
    if (!ok) return;
    try {
      await API.apiKeys.delete(keyId);
      Toast.success('Key removed');
      SettingsPage.loadApiKeys();
    } catch (e) { Toast.error(e.message); }
  },

  async loadUserInfo() {
    const user = Auth.getUser();
    if (!user) return;
    document.getElementById('account-name').value  = user.full_name || '';
    document.getElementById('account-email').value = user.email || '';
  },

  initPreferences() {
    // Theme
    const themeSelect = document.getElementById('pref-theme');
    if (themeSelect) {
      themeSelect.value = GeoAnalytica.state.theme;
      themeSelect.addEventListener('change', () => GeoAnalytica.applyTheme(themeSelect.value));
    }
  },

  async saveAccount() {
    const name = document.getElementById('account-name')?.value?.trim();
    const btn  = document.getElementById('save-account-btn');
    if (!name) { Toast.error('Name cannot be empty'); return; }
    if (btn) btn.disabled = true;
    try {
      await API.users.update({ full_name: name });
      Toast.success('Account updated');
    } catch (e) { Toast.error(e.message); }
    finally { if (btn) btn.disabled = false; }
  },

  async changePassword() {
    const curr = document.getElementById('current-password')?.value;
    const newP = document.getElementById('new-password')?.value;
    const conf = document.getElementById('confirm-new-password')?.value;
    if (!curr || !newP) { Toast.error('Please fill in all fields'); return; }
    if (newP !== conf)  { Toast.error('Passwords do not match'); return; }
    try {
      await API.users.changePassword({ current_password: curr, new_password: newP });
      Toast.success('Password changed');
      document.getElementById('current-password').value     = '';
      document.getElementById('new-password').value         = '';
      document.getElementById('confirm-new-password').value = '';
    } catch (e) { Toast.error(e.message); }
  },
};

window.SettingsPage = SettingsPage;
// Only init on settings.html (legacy) — detected by tab-api-keys panel
// NOTE: settings.html now loads settings.js which supersedes this.
// This block is kept for backwards compatibility only.
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('tab-api-keys') && typeof SettingsPage.SERVICES === 'undefined') {
    SettingsPage.init();
  }
});


/* ============================================================
   GeoAnalytica — Alerts Page
   ============================================================ */

const AlertsPage = {
  async init() {
    const ok = await Auth.guardPage();
    if (!ok) return;

    Sidebar.init();
    Topbar.init();
    Topbar.setBreadcrumb([{ label: 'Dashboard', href: '/dashboard.html' }, { label: 'Alerts' }]);
    document.title = 'Alerts — GeoAnalytica';

    await AlertsPage.loadAlerts();

    document.getElementById('new-alert-btn')?.addEventListener('click', async () => {
      await AlertsPage.populateAlertForm();
      Modal.open('new-alert-modal');
    });

    document.getElementById('new-alert-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      await AlertsPage.createAlert();
    });
  },

  async loadAlerts() {
    const container = document.getElementById('alerts-list');
    const histBody  = document.getElementById('alert-history-body');
    if (!container) return;

    try {
      const alerts = await API.alerts.list();

      if (!alerts.length) {
        container.innerHTML = `
          <div class="empty-state">
            <svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M12 2a7 7 0 017 7v3l1.5 3.5H3.5L5 12V9a7 7 0 017-7z"/><path d="M10 19a2 2 0 004 0"/>
            </svg>
            <h3>No alerts set up</h3>
            <p>Create alerts to get notified when data crosses a threshold.</p>
          </div>
        `;
        return;
      }

      container.innerHTML = alerts.map(a => `
        <div class="alert-card ${a.last_triggered_at ? 'triggered' : ''} ${!a.is_active ? 'paused' : ''}">
          <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;padding-top:2px;">
            <label class="toggle" title="${a.is_active ? 'Pause alert' : 'Activate alert'}">
              <input type="checkbox" ${a.is_active ? 'checked' : ''} onchange="AlertsPage.toggleAlert('${a.id}')">
              <span class="toggle-slider"></span>
            </label>
          </div>
          <div class="alert-card-body">
            <div class="alert-name">${a.name}</div>
            <div class="alert-meta">
              ${a.entity_name} · ${a.metric_field.replace(/_/g,' ')}
            </div>
            <span class="alert-condition">
              ${a.condition_operator} ${GeoAnalytica.formatNumber(a.threshold_value)} · ${a.check_frequency}
            </span>
            <div style="font-size:10px;color:var(--text-muted);margin-top:6px;display:flex;gap:12px;">
              <span>Last checked: ${GeoAnalytica.formatRelativeTime(a.last_checked_at) || 'Never'}</span>
              <span>Triggered: ${a.trigger_count} times</span>
              ${a.notify_email ? '<span>Email</span>' : ''}
              ${a.notify_slack ? '<span>Slack</span>' : ''}
            </div>
          </div>
          <div class="alert-actions">
            <button class="btn btn-ghost btn-sm btn-icon" onclick="AlertsPage.deleteAlert('${a.id}', '${a.name.replace(/'/g,'')}')" title="Delete">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M2 4h12M5 4V2h6v2M6 7v5M10 7v5M3 4l1 9a1 1 0 001 1h6a1 1 0 001-1l1-9"/>
              </svg>
            </button>
          </div>
        </div>
      `).join('');

      // Fetch and display global alert history
      if (histBody) {
        try {
          const histories = await Promise.all(
            alerts.map(async (a) => {
              try {
                const hist = await API.alerts.history(a.id);
                return hist.map(h => ({ ...h, alertName: a.name }));
              } catch (_) {
                return [];
              }
            })
          );
          const allHist = histories.flat().sort((x, y) => new Date(y.triggered_at) - new Date(x.triggered_at)).slice(0, 50);
          if (allHist.length) {
            histBody.innerHTML = allHist.map(h => `
              <tr style="border-bottom:1px solid var(--border-color)">
                <td style="padding:12px 16px;font-size:var(--text-sm);font-weight:600">${h.alertName}</td>
                <td style="padding:12px 16px;font-size:var(--text-sm);color:var(--text-muted)">${GeoAnalytica.formatDateTime(h.triggered_at)}</td>
                <td style="padding:12px 16px;font-size:var(--text-sm)">${GeoAnalytica.formatNumber(h.value_at_trigger)}</td>
                <td style="padding:12px 16px;font-size:var(--text-sm)">
                  ${(h.channels_notified || []).map(c => `<span class="badge badge-muted" style="margin-right:4px">${c}</span>`).join('') || 'None'}
                </td>
                <td style="padding:12px 16px;font-size:var(--text-sm)">
                  <span class="badge ${h.notification_status === 'sent' ? 'badge-green' : 'badge-red'}">${h.notification_status}</span>
                </td>
              </tr>
            `).join('');
          } else {
            histBody.innerHTML = `
              <tr>
                <td colspan="5" style="padding:24px;text-align:center;color:var(--text-muted);font-size:var(--text-sm)">
                  No alert history yet
                </td>
              </tr>
            `;
          }
        } catch (e) {
          console.error(e);
        }
      }
    } catch (e) {
      container.innerHTML = `<div class="notice notice-error">Failed to load alerts: ${e.message}</div>`;
    }
  },

  async populateAlertForm() {
    const querySelect = document.getElementById('alert-query-select');
    if (!querySelect) return;
    try {
      const queries = await API.queries.history();
      const completed = queries.filter(q => q.status === 'completed');
      querySelect.innerHTML = `<option value="">Select query…</option>` +
        completed.map(q => `<option value="${q.id}">${GeoAnalytica.truncate(q.instruction_text, 60)}</option>`).join('');
    } catch (_) {}
  },

  async createAlert() {
    const btn = document.getElementById('create-alert-btn');
    const data = {
      query_id:           document.getElementById('alert-query-select')?.value,
      name:               document.getElementById('alert-name')?.value?.trim(),
      metric_field:       document.getElementById('alert-metric')?.value?.trim(),
      entity_name:        document.getElementById('alert-entity')?.value?.trim(),
      condition_operator: document.getElementById('alert-operator')?.value,
      threshold_value:    parseFloat(document.getElementById('alert-threshold')?.value),
      check_frequency:    document.getElementById('alert-frequency')?.value,
      notify_email:       document.getElementById('alert-email')?.checked,
      notify_slack:       document.getElementById('alert-slack')?.checked,
      slack_webhook_url:  document.getElementById('alert-webhook')?.value?.trim() || null,
    };

    if (!data.query_id || !data.name || !data.metric_field || !data.entity_name || isNaN(data.threshold_value)) {
      Toast.error('Please fill in all required fields');
      return;
    }

    if (btn) btn.disabled = true;
    try {
      await API.alerts.create(data);
      Modal.close('new-alert-modal');
      Toast.success('Alert created!');
      await AlertsPage.loadAlerts();
    } catch (e) {
      Toast.error(e.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  },

  async toggleAlert(id) {
    try {
      await API.alerts.toggle(id);
      await AlertsPage.loadAlerts();
    } catch (e) { Toast.error(e.message); }
  },

  async deleteAlert(id, name) {
    const ok = await Confirm.show({ title: 'Delete Alert', message: `Delete alert "${name}"?`, confirmText: 'Delete', danger: true });
    if (!ok) return;
    try {
      await API.alerts.delete(id);
      Toast.success('Alert deleted');
      await AlertsPage.loadAlerts();
    } catch (e) { Toast.error(e.message); }
  },
};

window.AlertsPage = AlertsPage;
// Only init on alerts.html — detected by alerts-list element
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('alerts-list')) AlertsPage.init();
});
