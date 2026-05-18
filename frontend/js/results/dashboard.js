/* ============================================================
   GeoAnalytica — Results Dashboard
   Panel grid initialization, layout management
   ============================================================ */

const ResultsDashboard = {
  init(result) {
    if (!result) return;

    const fields = [...new Set(result.data_points.map(p => p.field_name))];
    const primary = fields[0];

    // Panel 1: Map
    const mapWrapper = document.getElementById('result-map-wrapper');
    if (mapWrapper && !GeoAnalytica.state.resultMapInit) {
      const mapInst = L.map('result-map', {
        center: [20, 0],
        zoom: 2,
        zoomControl: true,
        preferCanvas: true,
      });
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; CartoDB', subdomains: 'abcd',
      }).addTo(mapInst);

      // Override WorldMap reference for result page
      if (!WorldMap.map) {
        WorldMap.map = mapInst;
        WorldMap.countriesGeoJSON = null;
        fetch('https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson')
          .then(r => r.json())
          .then(geo => {
            WorldMap.countriesGeoJSON = geo;
            const pts = result.data_points.filter(p => p.field_name === primary);
            Choropleth.render(pts, primary);
          }).catch(() => {});
      }
      GeoAnalytica.state.resultMapInit = true;
    }

    // Panel 2: Bar chart
    const rankings = result.entity_rankings || [];
    if (rankings.length > 0 && document.getElementById('bar-chart-canvas')) {
      const top20 = rankings.slice(0, 20);
      Charts.renderBar(
        'bar-chart-canvas',
        top20.map(r => r.entity),
        top20.map(r => r.avg_value),
        (primary || 'value').replace(/_/g, ' ')
      );
    }

    // Panel 3: Line chart
    if (document.getElementById('line-chart-canvas')) {
      const top5 = rankings.slice(0, 5).map(r => r.entity);
      const years = [...new Set(result.data_points.map(p => p.timestamp.slice(0, 4)))].sort();
      const datasets = top5.map(entity => {
        const values = years.map(yr => {
          const pt = result.data_points.find(
            p => p.entity_name === entity &&
                 p.field_name === primary &&
                 p.timestamp.startsWith(yr) &&
                 !p.is_null
          );
          return pt ? pt.field_value : null;
        });
        return { entity, values };
      });
      Charts.renderLine('line-chart-canvas', datasets, years);
    }

    // Panel 4: Scatter (if 2+ fields)
    if (fields.length >= 2 && document.getElementById('scatter-chart-canvas')) {
      const f1 = fields[0], f2 = fields[1];
      const entities = [...new Set(result.data_points.map(p => p.entity_name))];
      const points = entities.map(entity => {
        const v1Pts = result.data_points.filter(p => p.entity_name === entity && p.field_name === f1 && !p.is_null);
        const v2Pts = result.data_points.filter(p => p.entity_name === entity && p.field_name === f2 && !p.is_null);
        if (!v1Pts.length || !v2Pts.length) return null;
        const x = v1Pts.reduce((s, p) => s + p.field_value, 0) / v1Pts.length;
        const y = v2Pts.reduce((s, p) => s + p.field_value, 0) / v2Pts.length;
        return { x, y, entity };
      }).filter(Boolean);
      Charts.renderScatter('scatter-chart-canvas', points, f1.replace(/_/g, ' '), f2.replace(/_/g, ' '));
    }

    // Panel 5: Data table
    if (document.getElementById('data-table')) {
      const { rows, columns } = DataTable.fromDataPoints(result.data_points);
      DataTable.init('data-table', rows, columns);
    }

    // Panel 6: AI Summary
    if (document.getElementById('ai-summary-panel')) {
      ResultsSummary.render(result);
    }
  },
};

window.ResultsDashboard = ResultsDashboard;


/* ============================================================
   GeoAnalytica — Results Panel (right sidebar on analysis page)
   ============================================================ */

const ResultsPanel = {
  render(result) {
    const panel = document.getElementById('results-panel');
    if (!panel) return;

    panel.hidden = false;

    const fields  = [...new Set(result.data_points.map(p => p.field_name))];
    const primary = fields[0];
    const nullRate = result.total_points > 0
      ? ((result.null_count / result.total_points) * 100).toFixed(1)
      : '0';

    // Quick metrics
    GeoAnalytica.setText('rp-total-points',   GeoAnalytica.formatNumber(result.total_points, 0));
    GeoAnalytica.setText('rp-countries',       [...new Set(result.data_points.map(p => p.entity_name))].length);
    GeoAnalytica.setText('rp-null-rate',       nullRate + '%');

    // AI summary
    const summaryEl = document.getElementById('rp-summary');
    if (summaryEl && result.summary_text) {
      summaryEl.textContent = GeoAnalytica.truncate(result.summary_text, 300);
    }

    // Rankings top 10
    const rankingsEl = document.getElementById('rp-rankings');
    if (rankingsEl) {
      const rankings = (result.entity_rankings || []).slice(0, 10);
      rankingsEl.innerHTML = rankings.map(r => `
        <div class="ranking-item" onclick="WorldMap.flyToCountry && CountryPopup.show('${r.country_code}', '${r.entity}')">
          <span class="ranking-num">${r.rank}</span>
          <span class="ranking-name">${r.entity}</span>
          <span class="ranking-val">${GeoAnalytica.formatNumber(r.avg_value)}</span>
          <span class="conf-badge conf-high" style="font-size:9px;">—</span>
        </div>
      `).join('') || '<div style="font-size:12px;color:var(--text-muted);padding:8px 0;">No rankings available</div>';
    }

    // Outliers
    const outliersEl = document.getElementById('rp-outliers');
    if (outliersEl) {
      const outliers = result.data_points.filter(p => p.is_outlier).slice(0, 5);
      if (outliers.length) {
        outliersEl.innerHTML = outliers.map(p => `
          <div class="outlier-item">
            <div class="outlier-entity">${p.entity_name} · ${p.timestamp}</div>
            <div class="outlier-detail">${p.field_name.replace(/_/g,' ')}: ${GeoAnalytica.formatNumber(p.field_value)} (${p.outlier_reason})</div>
          </div>
        `).join('');
      } else {
        outliersEl.innerHTML = '<div style="font-size:12px;color:var(--text-muted);">No outliers detected</div>';
      }
    }

    // Source donut chart
    const apiCount = result.data_points.filter(p => p.source_type === 'api' && !p.is_null).length;
    const webCount = result.data_points.filter(p => p.source_type === 'web' && !p.is_null).length;
    if (document.getElementById('source-donut') && (apiCount + webCount) > 0) {
      Charts.renderDonut(
        'source-donut',
        ['Direct API', 'Web Scrape'],
        [apiCount, webCount],
        ['#3fb950', '#d29922']
      );
    }

    // View full dashboard link
    const viewFull = document.getElementById('rp-view-full');
    if (viewFull && GeoAnalytica.state.currentQuery) {
      viewFull.href = `/results.html?query=${GeoAnalytica.state.currentQuery.id}`;
    }
  },
};

window.ResultsPanel = ResultsPanel;
