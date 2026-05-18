/* ============================================================
   GeoAnalytica — Query Builder
   Controls all 3 input modes (NL, Structured, Fields)
   ============================================================ */

const QueryBuilder = {
  mode:            'nl',
  selectedFields:  new Set(),
  selectedScope:   'world',
  customEntities:  [],
  timeRange:       { start: '2015', end: '2023' },
  granularity:     'annual',
  filters:         [],

  init() {
    // Mode toggle
    document.querySelectorAll('.mode-btn[data-mode]').forEach(btn => {
      btn.addEventListener('click', () => QueryBuilder.setMode(btn.dataset.mode));
    });

    // Example chips
    document.querySelectorAll('.example-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const ta = document.getElementById('nl-instruction');
        if (ta) {
          ta.value = chip.textContent.trim();
          QueryBuilder.updateCharCount();
          QueryBuilder.setMode('nl');
          ta.focus();
        }
      });
    });

    // Examples toggle
    const examplesToggle = document.getElementById('examples-toggle');
    const examplesChips  = document.getElementById('examples-chips');
    if (examplesToggle && examplesChips) {
      examplesToggle.addEventListener('click', () => {
        const isOpen = examplesChips.style.display !== 'none';
        examplesChips.style.display = isOpen ? 'none' : 'flex';
        examplesToggle.classList.toggle('open', !isOpen);
      });
    }

    // Field checkboxes
    document.querySelectorAll('.field-checkbox').forEach(cb => {
      cb.addEventListener('change', () => {
        if (cb.checked) QueryBuilder.selectedFields.add(cb.value);
        else            QueryBuilder.selectedFields.delete(cb.value);
        QueryBuilder.updatePreview();
      });
    });

    // Scope buttons
    document.querySelectorAll('.scope-btn[data-scope]').forEach(btn => {
      btn.addEventListener('click', () => QueryBuilder.setScope(btn.dataset.scope));
    });

    // Time range
    document.getElementById('time-start')?.addEventListener('change', e => {
      QueryBuilder.timeRange.start = e.target.value;
      QueryBuilder.updatePreview();
    });
    document.getElementById('time-end')?.addEventListener('change', e => {
      QueryBuilder.timeRange.end = e.target.value;
      QueryBuilder.updatePreview();
    });

    // Granularity
    document.querySelectorAll('.granularity-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        QueryBuilder.granularity = btn.dataset.granularity;
        document.querySelectorAll('.granularity-btn').forEach(b =>
          b.classList.toggle('active', b === btn));
      });
    });

    // Add filter
    document.getElementById('add-filter-btn')?.addEventListener('click', () => {
      QueryBuilder.addFilter();
    });

    // Run button
    const runBtn = document.getElementById('run-query-btn');
    if (runBtn) {
      runBtn.addEventListener('click', () => QueryBuilder.runQuery());
    }

    // Preview button
    document.getElementById('preview-btn')?.addEventListener('click', () => {
      QueryBuilder.showPreview();
    });

    // Char counter
    const ta = document.getElementById('nl-instruction');
    if (ta) {
      ta.addEventListener('input', QueryBuilder.updateCharCount);
      ta.addEventListener('input', QueryBuilder.updatePreview);
    }

    // Field search
    document.getElementById('field-search')?.addEventListener('input', e => {
      QueryBuilder.filterFields(e.target.value);
    });

    // Custom scope input
    document.getElementById('custom-entities')?.addEventListener('input', e => {
      QueryBuilder.customEntities = e.target.value
        .split(',')
        .map(s => s.trim())
        .filter(Boolean);
      QueryBuilder.updatePreview();
    });

    // Set default scope active
    QueryBuilder.setScope('world');
  },

  setMode(mode) {
    QueryBuilder.mode = mode;
    document.querySelectorAll('.mode-btn[data-mode]').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.mode === mode);
    });
    document.querySelectorAll('.mode-panel[data-mode]').forEach(panel => {
      panel.hidden = panel.dataset.mode !== mode;
    });
  },

  setScope(scope) {
    QueryBuilder.selectedScope = scope;
    document.querySelectorAll('.scope-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.scope === scope);
    });

    const customInput = document.getElementById('custom-entities-input');
    if (customInput) {
      customInput.classList.toggle('visible', scope === 'custom');
    }

    QueryBuilder.updatePreview();
  },

  addFilter() {
    const container = document.getElementById('filters-container');
    if (!container) return;

    const fields = Array.from(QueryBuilder.selectedFields);
    const fieldOptions = fields.length
      ? fields.map(f => `<option value="${f}">${f.replace(/_/g, ' ')}</option>`).join('')
      : '<option value="">Select field first</option>';

    const row = document.createElement('div');
    row.className = 'filter-row';
    row.innerHTML = `
      <select class="form-input form-select filter-field">
        <option value="">Field...</option>
        ${fieldOptions}
      </select>
      <select class="form-input form-select filter-op">
        <option value="gt">&gt;</option>
        <option value="lt">&lt;</option>
        <option value="gte">&ge;</option>
        <option value="lte">&le;</option>
        <option value="eq">=</option>
        <option value="neq">&ne;</option>
      </select>
      <input type="number" class="form-input filter-val" placeholder="Value" step="any">
      <button class="filter-remove" title="Remove filter">×</button>
    `;

    row.querySelector('.filter-remove').addEventListener('click', () => {
      row.remove();
      QueryBuilder.updatePreview();
    });

    row.querySelectorAll('select, input').forEach(el => {
      el.addEventListener('change', QueryBuilder.updatePreview);
    });

    container.appendChild(row);
    QueryBuilder.updatePreview();
  },

  _collectFilters() {
    const filters = [];
    document.querySelectorAll('.filter-row').forEach(row => {
      const field = row.querySelector('.filter-field')?.value;
      const op    = row.querySelector('.filter-op')?.value;
      const val   = parseFloat(row.querySelector('.filter-val')?.value);
      if (field && op && !isNaN(val)) {
        filters.push({ field, operator: op, value: val });
      }
    });
    return filters;
  },

  buildPayload() {
    const projectId = GeoAnalytica.getParam('project');

    if (QueryBuilder.mode === 'nl') {
      const ta = document.getElementById('nl-instruction');
      return {
        project_id:       projectId,
        instruction_text: ta?.value?.trim() || '',
        mode:             'natural',
      };
    }

    // Build instruction from structured form
    const fields = Array.from(QueryBuilder.selectedFields);
    const scope  = QueryBuilder.selectedScope;
    const entities = scope === 'custom'
      ? QueryBuilder.customEntities
      : [scope];

    const { start, end } = QueryBuilder.timeRange;
    const filters = QueryBuilder._collectFilters();

    let instruction = `Analyze ${fields.length ? fields.join(', ') : 'GDP per capita'} `;
    instruction += `for ${entities.join(', ')} `;
    instruction += `from ${start} to ${end} (${QueryBuilder.granularity}). `;
    if (filters.length) {
      instruction += filters.map(f =>
        `Filter: ${f.field} ${f.operator} ${f.value}`
      ).join(' AND ') + '.';
    }

    return {
      project_id:       projectId,
      instruction_text: instruction.trim(),
      mode:             'structured',
    };
  },

  async runQuery() {
    const payload = QueryBuilder.buildPayload();

    if (!payload.instruction_text) {
      Toast.error('Please enter a query or select fields');
      return;
    }
    if (!payload.project_id) {
      Toast.error('No project selected');
      return;
    }

    const btn = document.getElementById('run-query-btn');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner spinner-sm"></span> Running…';
    }

    Progress.show();

    try {
      const query = await API.queries.create(payload);
      GeoAnalytica.state.currentQuery = query;

      // Connect WebSocket
      WS.disconnect();
      WS.clearHandlers();
      WS.connect(query.id);

      WS.on('progress',      msg => Progress.update(msg));
      WS.on('country_data',  msg => {
        Choropleth.updateCountry(msg.country_code, msg.value);
      });
      WS.on('error',         msg => {
        Progress.hide();
        if (btn) { btn.disabled = false; btn.textContent = 'Run Analysis'; }
        Toast.error(msg.message || 'Analysis failed');
        WS.disconnect();
      });
      WS.on('complete',      async (msg) => {
        WS.disconnect();
        if (btn) { btn.disabled = false; btn.textContent = 'Run Analysis'; }
        Progress.hide();
        Toast.success('Analysis complete!');

        // Fetch full result
        try {
          const result = await API.results.get(query.id);
          GeoAnalytica.state.currentResult = result;
          ResultsPanel.render(result);

          const fields  = [...new Set(result.data_points.map(p => p.field_name))];
          const primary = fields[0];
          const primaryPts = result.data_points.filter(p => p.field_name === primary);
          Choropleth.render(primaryPts, primary);

          const years = [...new Set(result.data_points.map(p => p.timestamp.slice(0, 4)))].sort();
          Timeline.init('timeline-container', years, result.data_points);
        } catch (err) {
          Toast.error('Could not load results: ' + err.message);
        }
      });

    } catch (err) {
      Progress.hide();
      if (btn) { btn.disabled = false; btn.textContent = 'Run Analysis'; }
      Toast.error(err.message || 'Failed to start query');
    }
  },

  showPreview() {
    const payload = QueryBuilder.buildPayload();
    const previewEl = document.getElementById('query-preview-card');
    if (!previewEl) return;

    const fields   = Array.from(QueryBuilder.selectedFields);
    const scope    = QueryBuilder.selectedScope;
    const filters  = QueryBuilder._collectFilters();
    const { start, end } = QueryBuilder.timeRange;
    const years    = parseInt(end) - parseInt(start) + 1;
    const estPts   = (fields.length || 1) * years * (scope === 'world' ? 195 : 30);
    const estTime  = '8–20 seconds';

    const user = Auth.getUser();
    const queriesLeft = user
      ? Math.max(0, 20 - (user.queries_today || 0))
      : '?';

    previewEl.innerHTML = `
      <div class="query-preview-title">Query Preview</div>
      <div class="query-preview-row">
        <span class="query-preview-key">Fields</span>
        <span class="query-preview-val">${fields.length ? fields.map(f => f.replace(/_/g,' ')).join(', ') : 'Auto-detect'}</span>
      </div>
      <div class="query-preview-row">
        <span class="query-preview-key">Scope</span>
        <span class="query-preview-val">${scope.toUpperCase()}</span>
      </div>
      <div class="query-preview-row">
        <span class="query-preview-key">Range</span>
        <span class="query-preview-val">${start}–${end} (${QueryBuilder.granularity})</span>
      </div>
      <div class="query-preview-row">
        <span class="query-preview-key">Filters</span>
        <span class="query-preview-val">${filters.length || 'None'}</span>
      </div>
      <div class="query-preview-row">
        <span class="query-preview-key">Est. points</span>
        <span class="query-preview-val">~${GeoAnalytica.formatNumber(estPts, 0)}</span>
      </div>
      <div class="query-preview-row">
        <span class="query-preview-key">Est. time</span>
        <span class="query-preview-val">${estTime} (Free tier)</span>
      </div>
      <div class="query-usage-bar">
        <div class="query-usage-label">
          <span>Queries today</span>
          <span>${queriesLeft} of 20 remaining</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" style="width:${Math.min(100, ((20 - queriesLeft) / 20) * 100)}%"></div>
        </div>
      </div>
    `;

    previewEl.hidden = false;
  },

  updateCharCount() {
    const ta = document.getElementById('nl-instruction');
    const counter = document.getElementById('char-count');
    if (ta && counter) counter.textContent = `${ta.value.length} chars`;
  },

  updatePreview() {
    const previewEl = document.getElementById('query-preview-card');
    if (previewEl && !previewEl.hidden) QueryBuilder.showPreview();
  },

  filterFields(query) {
    const q = query.toLowerCase();
    document.querySelectorAll('.field-item').forEach(item => {
      const text = item.textContent.toLowerCase();
      item.style.display = text.includes(q) ? '' : 'none';
    });
  },
};

window.QueryBuilder = QueryBuilder;
