/* ============================================================
   GeoAnalytica — NLP Input helpers
   Natural language textarea enhancements
   ============================================================ */

const NLPInput = {
  init(textareaId) {
    const ta = document.getElementById(textareaId);
    if (!ta) return;

    // Auto-resize
    ta.addEventListener('input', () => {
      ta.style.height = 'auto';
      ta.style.height = Math.min(ta.scrollHeight, 240) + 'px';
    });

    // Submit on Ctrl+Enter / Cmd+Enter
    ta.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        document.getElementById('run-query-btn')?.click();
      }
    });
  },
};

window.NLPInput = NLPInput;


/* ============================================================
   GeoAnalytica — Field Picker
   Card-grid view for selecting fields
   ============================================================ */

const FieldPicker = {
  selected: new Set(),

  init(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Sync with QueryBuilder.selectedFields
    container.querySelectorAll('.field-card-toggle').forEach(toggle => {
      toggle.addEventListener('change', () => {
        const field = toggle.value;
        if (toggle.checked) {
          FieldPicker.selected.add(field);
          QueryBuilder.selectedFields.add(field);
        } else {
          FieldPicker.selected.delete(field);
          QueryBuilder.selectedFields.delete(field);
        }
        QueryBuilder.updatePreview();
      });
    });
  },
};

window.FieldPicker = FieldPicker;


/* ============================================================
   GeoAnalytica — Filter Builder
   (Handled inline by QueryBuilder.addFilter)
   ============================================================ */

const FilterBuilder = {
  // Additional helpers if needed
  getActiveFilters() {
    return QueryBuilder._collectFilters();
  },
};

window.FilterBuilder = FilterBuilder;


/* ============================================================
   GeoAnalytica — Query Preview
   (Handled by QueryBuilder.showPreview)
   ============================================================ */

const QueryPreview = {
  show() { QueryBuilder.showPreview(); },
  hide() {
    const el = document.getElementById('query-preview-card');
    if (el) el.hidden = true;
  },
};

window.QueryPreview = QueryPreview;


/* ============================================================
   GeoAnalytica — Query Progress Panel
   Live status updates during query execution
   ============================================================ */

const Progress = {
  STAGES: [
    { key: 'parsing',     label: 'Parsing query' },
    { key: 'routing',     label: 'Identifying sources' },
    { key: 'fetching',    label: 'Fetching data' },
    { key: 'normalizing', label: 'Normalizing values' },
    { key: 'analyzing',   label: 'Running analysis' },
    { key: 'narrative',   label: 'Generating summary' },
  ],

  show() {
    const overlay = document.getElementById('query-progress');
    if (overlay) overlay.hidden = false;
    Progress.reset();
  },

  hide() {
    const overlay = document.getElementById('query-progress');
    if (overlay) overlay.hidden = true;
  },

  reset() {
    const fill    = document.getElementById('progress-bar-fill');
    const message = document.getElementById('progress-message');
    if (fill)    fill.style.width = '0%';
    if (message) message.textContent = 'Starting…';

    document.querySelectorAll('.progress-stage').forEach(el => {
      el.dataset.status = 'pending';
      const icon = el.querySelector('.stage-icon');
      if (icon) icon.textContent = '—';
    });
  },

  update(msg) {
    const fill    = document.getElementById('progress-bar-fill');
    const message = document.getElementById('progress-message');

    if (fill && msg.percent !== undefined) {
      fill.style.width = msg.percent + '%';
    }
    if (message && msg.message) {
      message.textContent = msg.message;
    }

    // Update stage status
    if (msg.stage) {
      const stageEl = document.querySelector(`[data-stage="${msg.stage}"]`);
      if (stageEl) {
        const status = msg.status || 'running';
        stageEl.dataset.status = status;
        const icon = stageEl.querySelector('.stage-icon');
        if (icon) {
          icon.textContent = status === 'done' ? '✓' : status === 'running' ? '⟳' : '—';
        }
        const label = stageEl.querySelector('.stage-label');
        if (label && msg.country_count) {
          label.textContent = `Fetching data (${msg.country_count} complete)`;
        }
      }
    }
  },

  // Build the stage list HTML (call once on page load)
  renderStages(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = Progress.STAGES.map(s => `
      <div class="progress-stage" data-stage="${s.key}" data-status="pending">
        <div class="stage-icon">—</div>
        <span class="stage-label">${s.label}</span>
      </div>
    `).join('');
  },
};

window.Progress = Progress;
