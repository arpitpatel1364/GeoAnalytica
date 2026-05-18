/* ============================================================
   GeoAnalytica — Charts (Chart.js)
   Bar, Line, Scatter, Donut chart renderers
   ============================================================ */

const Charts = {
  instances: {},

  _destroy(canvasId) {
    if (Charts.instances[canvasId]) {
      Charts.instances[canvasId].destroy();
      delete Charts.instances[canvasId];
    }
  },

  _getCtx(canvasId) {
    const canvas = document.getElementById(canvasId);
    return canvas ? canvas.getContext('2d') : null;
  },

  _chartDefaults() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#8b949e', font: { size: 11, family: "'Inter', sans-serif" }, boxWidth: 12 } },
        tooltip: {
          backgroundColor: 'rgba(22,27,34,0.95)',
          titleColor: '#e6edf3',
          bodyColor: '#8b949e',
          borderColor: '#30363d',
          borderWidth: 1,
          padding: 10,
          cornerRadius: 8,
        },
      },
      scales: {
        x: {
          grid:  { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#8b949e', font: { size: 11 } },
        },
        y: {
          grid:  { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#8b949e', font: { size: 11 } },
        },
      },
    };
  },

  // ── Bar Chart ─────────────────────────────────────────────
  renderBar(canvasId, labels, values, fieldLabel) {
    Charts._destroy(canvasId);
    const ctx = Charts._getCtx(canvasId);
    if (!ctx) return;

    const defaults = Charts._chartDefaults();
    Charts.instances[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels.slice(0, 20),
        datasets: [{
          label: fieldLabel || 'Value',
          data:  values.slice(0, 20),
          backgroundColor: values.slice(0, 20).map((_, i) => {
            const alpha = 0.9 - (i / 20) * 0.3;
            return `rgba(47,129,247,${alpha})`;
          }),
          borderColor:   'rgba(47,129,247,0.8)',
          borderWidth:   1,
          borderRadius:  4,
          hoverBackgroundColor: 'rgba(56,139,253,0.9)',
        }],
      },
      options: {
        ...defaults,
        indexAxis: 'y',
        plugins: {
          ...defaults.plugins,
          legend: { display: false },
          tooltip: {
            ...defaults.plugins.tooltip,
            callbacks: {
              label: ctx => ' ' + GeoAnalytica.formatNumber(ctx.raw),
            },
          },
        },
        scales: {
          x: { ...defaults.scales.x },
          y: {
            grid:  { display: false },
            ticks: { color: '#e6edf3', font: { size: 11 }, maxTicksLimit: 20 },
          },
        },
      },
    });
  },

  // ── Line Chart ────────────────────────────────────────────
  renderLine(canvasId, datasets, years) {
    Charts._destroy(canvasId);
    const ctx = Charts._getCtx(canvasId);
    if (!ctx) return;

    const palette = ['#2f81f7', '#3fb950', '#d29922', '#f85149', '#bc8cff', '#39d353', '#ff7b72'];
    const defaults = Charts._chartDefaults();

    Charts.instances[canvasId] = new Chart(ctx, {
      type: 'line',
      data: {
        labels: years,
        datasets: datasets.map((ds, i) => ({
          label:           ds.entity,
          data:            ds.values,
          borderColor:     palette[i % palette.length],
          backgroundColor: palette[i % palette.length] + '20',
          pointBackgroundColor: palette[i % palette.length],
          tension:         0.35,
          fill:            false,
          pointRadius:     3,
          pointHoverRadius: 5,
          borderWidth:     2,
          spanGaps:        true,
        })),
      },
      options: {
        ...defaults,
        plugins: {
          ...defaults.plugins,
          tooltip: {
            ...defaults.plugins.tooltip,
            mode:      'index',
            intersect: false,
            callbacks: {
              label: ctx => ` ${ctx.dataset.label}: ${GeoAnalytica.formatNumber(ctx.raw)}`,
            },
          },
        },
      },
    });
  },

  // ── Scatter Chart ─────────────────────────────────────────
  renderScatter(canvasId, points, xLabel, yLabel) {
    Charts._destroy(canvasId);
    const ctx = Charts._getCtx(canvasId);
    if (!ctx) return;

    const defaults = Charts._chartDefaults();

    Charts.instances[canvasId] = new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: [{
          label:           `${xLabel} vs ${yLabel}`,
          data:            points.map(p => ({ x: p.x, y: p.y, label: p.entity })),
          backgroundColor: 'rgba(47,129,247,0.55)',
          pointRadius:     5,
          pointHoverRadius: 7,
          borderColor:     'rgba(47,129,247,0.8)',
          borderWidth:     1,
        }],
      },
      options: {
        ...defaults,
        plugins: {
          ...defaults.plugins,
          legend: { display: false },
          tooltip: {
            ...defaults.plugins.tooltip,
            callbacks: {
              label: ctx => `${ctx.raw.label}: (${GeoAnalytica.formatNumber(ctx.raw.x)}, ${GeoAnalytica.formatNumber(ctx.raw.y)})`,
            },
          },
        },
        scales: {
          x: {
            ...defaults.scales.x,
            title: { display: true, text: xLabel, color: '#8b949e', font: { size: 11 } },
          },
          y: {
            ...defaults.scales.y,
            title: { display: true, text: yLabel, color: '#8b949e', font: { size: 11 } },
          },
        },
      },
    });
  },

  // ── Donut Chart ───────────────────────────────────────────
  renderDonut(canvasId, labels, values, colors) {
    Charts._destroy(canvasId);
    const ctx = Charts._getCtx(canvasId);
    if (!ctx) return;

    Charts.instances[canvasId] = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data:            values,
          backgroundColor: colors || ['#2f81f7', '#d29922'],
          borderColor:     '#161b22',
          borderWidth:     3,
          hoverOffset:     4,
        }],
      },
      options: {
        responsive:          true,
        maintainAspectRatio: false,
        cutout:              '68%',
        plugins: {
          legend: {
            position: 'right',
            labels: {
              color:   '#8b949e',
              font:    { size: 11 },
              boxWidth: 10,
              padding: 12,
            },
          },
          tooltip: {
            backgroundColor: 'rgba(22,27,34,0.95)',
            titleColor:      '#e6edf3',
            bodyColor:       '#8b949e',
            borderColor:     '#30363d',
            borderWidth:     1,
            padding:         10,
            cornerRadius:    8,
            callbacks: {
              label: ctx => ` ${ctx.label}: ${GeoAnalytica.formatNumber(ctx.raw, 0)}`,
            },
          },
        },
      },
    });
  },

  // ── Destroy all ───────────────────────────────────────────
  destroyAll() {
    Object.keys(Charts.instances).forEach(id => Charts._destroy(id));
  },
};

window.Charts = Charts;
