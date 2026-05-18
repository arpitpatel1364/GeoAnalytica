/* ============================================================
   GeoAnalytica — Dashboard Page
   ============================================================ */

const DashboardPage = {
  async init() {
    const ok = await Auth.guardPage();
    if (!ok) return;

    Sidebar.init();
    Topbar.init();

    await DashboardPage.loadStats();
    await DashboardPage.loadProjects();
    await DashboardPage.loadRecentQueries();

    // New project modal
    document.getElementById('new-project-btn')?.addEventListener('click', () => {
      Modal.open('new-project-modal');
    });
    document.getElementById('new-project-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      await DashboardPage.createProject();
    });

    // Set breadcrumb
    Topbar.setBreadcrumb([{ label: 'GeoAnalytica', href: '/dashboard.html' }, { label: 'Dashboard' }]);
  },

  async loadStats() {
    try {
      const stats = await API.users.stats();
      GeoAnalytica.setText('stat-projects',   stats.projects_count);
      GeoAnalytica.setText('stat-queries',    stats.queries_today);
      GeoAnalytica.setText('stat-api-keys',   stats.api_keys_connected);
      GeoAnalytica.setText('stat-alerts',     stats.alerts_active);

      // Queries today progress bar
      const pct = Math.min(100, (stats.queries_today / stats.queries_today_limit) * 100);
      const fill = document.getElementById('queries-today-fill');
      if (fill) fill.style.width = pct + '%';
      GeoAnalytica.setText('queries-today-label',
        `${stats.queries_today} / ${stats.queries_today_limit} today`);
    } catch (e) {
      console.warn('Stats load failed:', e.message);
    }
  },

  async loadProjects() {
    const grid = document.getElementById('projects-grid');
    if (!grid) return;

    try {
      const projects = await API.projects.list();
      GeoAnalytica.state.projects = projects;

      // Render sidebar projects
      Sidebar.renderProjects(projects);

      if (!projects.length) {
        grid.innerHTML = `
          <div class="empty-state" style="grid-column:1/-1">
            <svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M3 7h18M3 12h18M3 17h18"/>
            </svg>
            <h3>No projects yet</h3>
            <p>Create your first project to start analyzing global data.</p>
            <button class="btn btn-primary" onclick="Modal.open('new-project-modal')">
              + New Project
            </button>
          </div>
        `;
        return;
      }

      grid.innerHTML = projects.map(p => `
        <div class="project-card" onclick="window.location.href='/analysis.html?project=${p.id}'">
          <div class="project-card-name">${p.name}</div>
          <div class="project-card-desc">${p.description || 'No description'}</div>
          <div class="project-card-meta">
            <span>${GeoAnalytica.formatRelativeTime(p.last_query_at || p.created_at)}</span>
            <span class="badge badge-muted">${p.query_count} queries</span>
          </div>
          <div class="project-card-actions" onclick="event.stopPropagation()">
            <a href="/analysis.html?project=${p.id}" class="btn btn-primary btn-sm">Open</a>
            <button class="btn btn-ghost btn-sm btn-icon" onclick="DashboardPage.deleteProject('${p.id}', '${p.name.replace(/'/g,'')}')" title="Delete">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M2 4h12M5 4V2h6v2M6 7v5M10 7v5M3 4l1 9a1 1 0 001 1h6a1 1 0 001-1l1-9"/>
              </svg>
            </button>
          </div>
        </div>
      `).join('');
    } catch (e) {
      grid.innerHTML = `<div class="notice notice-error" style="grid-column:1/-1">Failed to load projects: ${e.message}</div>`;
    }
  },

  async loadRecentQueries() {
    const tbody = document.getElementById('recent-queries-body');
    if (!tbody) return;

    try {
      const queries = await API.queries.history();
      if (!queries.length) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:24px">No queries yet</td></tr>`;
        return;
      }

      tbody.innerHTML = queries.slice(0, 10).map(q => `
        <tr>
          <td>
            <span class="truncate" style="max-width:300px;display:block;font-size:var(--text-sm);">
              ${GeoAnalytica.truncate(q.instruction_text, 60)}
            </span>
          </td>
          <td><span class="status-badge status-${q.status}">${q.status}</span></td>
          <td style="color:var(--text-muted);font-size:var(--text-xs);">
            ${q.duration_seconds ? Format.duration(q.duration_seconds) : '—'}
          </td>
          <td style="color:var(--text-muted);font-size:var(--text-xs);">
            ${q.data_point_count ? GeoAnalytica.formatNumber(q.data_point_count, 0) + ' pts' : '—'}
          </td>
          <td style="color:var(--text-muted);font-size:var(--text-xs);">
            ${GeoAnalytica.formatRelativeTime(q.created_at)}
          </td>
          <td>
            <div style="display:flex;gap:4px">
              ${q.status === 'completed' ? `<a href="/results.html?query=${q.id}" class="btn btn-ghost btn-xs">View</a>` : ''}
              <button class="btn btn-ghost btn-xs" onclick="DashboardPage.rerunQuery('${q.id}')">Re-run</button>
            </div>
          </td>
        </tr>
      `).join('');
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="6">Failed to load queries</td></tr>`;
    }
  },

  async createProject() {
    const name = document.getElementById('project-name')?.value?.trim();
    const desc = document.getElementById('project-desc')?.value?.trim();
    const btn  = document.getElementById('create-project-btn');
    const errEl= document.getElementById('project-error');

    if (!name) {
      if (errEl) { errEl.textContent = 'Project name is required'; errEl.hidden = false; }
      return;
    }

    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner spinner-sm"></span>'; }

    try {
      await API.projects.create({ name, description: desc || null });
      Modal.close('new-project-modal');
      Toast.success('Project created!');
      await DashboardPage.loadProjects();
      await DashboardPage.loadStats();
      // Reset form
      document.getElementById('project-name').value = '';
      document.getElementById('project-desc').value  = '';
    } catch (e) {
      if (errEl) { errEl.textContent = e.message; errEl.hidden = false; }
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Create'; }
    }
  },

  async deleteProject(id, name) {
    const ok = await Confirm.show({
      title:       'Delete Project',
      message:     `Delete "${name}" and all its queries? This cannot be undone.`,
      confirmText: 'Delete',
      cancelText:  'Cancel',
      danger:      true,
    });
    if (!ok) return;

    try {
      await API.projects.delete(id);
      Toast.success('Project deleted');
      await DashboardPage.loadProjects();
      await DashboardPage.loadStats();
    } catch (e) {
      Toast.error('Failed to delete: ' + e.message);
    }
  },

  async rerunQuery(queryId) {
    try {
      const q = await API.queries.rerun(queryId);
      Toast.success('Query re-queued!');
      window.location.href = `/analysis.html?project=${q.project_id}&query=${q.id}`;
    } catch (e) {
      Toast.error('Failed to re-run: ' + e.message);
    }
  },
};

window.DashboardPage = DashboardPage;
document.addEventListener('DOMContentLoaded', () => DashboardPage.init());
