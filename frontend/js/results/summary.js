/* ============================================================
   GeoAnalytica — AI Summary Card Renderer
   ============================================================ */

const ResultsSummary = {
  expanded: false,

  render(result) {
    const panel = document.getElementById('ai-summary-panel');
    if (!panel) return;

    const summary      = result.summary_text     || 'Analysis complete.';
    const findings     = result.key_findings     || [];
    const anomalies    = result.anomalies        || [];
    const qualityNote  = result.data_quality_note || '';

    panel.innerHTML = `
      <div class="ai-summary-full">
        <div class="ai-summary-header">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="8" cy="8" r="3"/>
            <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41"/>
          </svg>
          AI Analysis Summary
          <span class="badge badge-blue" style="margin-left:auto;font-size:10px;">Claude</span>
        </div>

        <div class="summary-text-full">
          ${summary.split('\n').filter(p => p.trim()).map(p => `<p>${p}</p>`).join('')}
        </div>

        ${findings.length ? `
          <h4 style="font-size:var(--text-sm);font-weight:600;color:var(--text-primary);margin-bottom:var(--space-3);">
            Key Findings
          </h4>
          <div class="findings-grid">
            ${findings.map(f => `
              <div class="finding-item">
                <span class="finding-bullet">→</span>
                <span>${f}</span>
              </div>
            `).join('')}
          </div>
        ` : ''}

        ${anomalies.length ? `
          <h4 style="font-size:var(--text-sm);font-weight:600;color:var(--text-primary);margin-bottom:var(--space-3);margin-top:var(--space-5);">
            Anomalies Detected
          </h4>
          ${anomalies.map(a => `
            <div class="anomaly-item">
              <span class="anomaly-icon" style="display:inline-block;width:14px;height:14px;vertical-align:middle;margin-right:6px;color:var(--status-danger)"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2L14 13H2L8 2z"/><path d="M8 7v3M8 11.5v.5"/></svg></span>
              <span>${a}</span>
            </div>
          `).join('')}
        ` : ''}

        ${qualityNote ? `
          <div class="data-quality-card" style="margin-top:var(--space-5);">
            <strong style="color:var(--text-secondary);">Data Quality:</strong> ${qualityNote}
          </div>
        ` : ''}
      </div>
    `;
  },

  // Compact version for right panel
  renderCompact(result, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const summary = result.summary_text || '';
    const truncated = GeoAnalytica.truncate(summary, 280);

    container.innerHTML = `
      <div class="ai-summary-card">
        <div class="ai-summary-header">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="8" cy="8" r="3"/>
            <path d="M8 1v2M8 13v2M1 8h2M13 8h2"/>
          </svg>
          AI Summary
        </div>
        <div class="ai-summary-text ${ResultsSummary.expanded ? '' : 'ai-summary-collapsed'}" id="compact-summary-text">
          ${truncated}
        </div>
        ${summary.length > 280 ? `
          <button class="btn btn-ghost btn-xs" style="margin-top:var(--space-2);" id="summary-expand-btn">
            Read more
          </button>
        ` : ''}
      </div>
    `;

    const expandBtn = document.getElementById('summary-expand-btn');
    if (expandBtn) {
      expandBtn.addEventListener('click', () => {
        const textEl = document.getElementById('compact-summary-text');
        ResultsSummary.expanded = !ResultsSummary.expanded;
        if (ResultsSummary.expanded) {
          textEl.classList.remove('ai-summary-collapsed');
          textEl.textContent = summary;
          expandBtn.textContent = 'Show less';
        } else {
          textEl.classList.add('ai-summary-collapsed');
          textEl.textContent = truncated;
          expandBtn.textContent = 'Read more';
        }
      });
    }
  },
};

window.ResultsSummary = ResultsSummary;


/* ============================================================
   GeoAnalytica — GeoJSON Layer (for results page map)
   ============================================================ */

const GeoJSONLayer = {
  layer: null,

  render(mapInstance, geojson, field) {
    if (!mapInstance || !geojson) return;

    if (GeoJSONLayer.layer) {
      mapInstance.removeLayer(GeoJSONLayer.layer);
      GeoJSONLayer.layer = null;
    }

    if (!geojson.features || geojson.features.length === 0) return;

    // Extract values for color scale
    const values = geojson.features
      .map(f => f.properties[field])
      .filter(v => v !== null && v !== undefined && !isNaN(v));

    const scale = ColorScale.build(values);

    GeoJSONLayer.layer = L.geoJSON(geojson, {
      pointToLayer(feature, latlng) {
        const val   = feature.properties[field];
        const color = val !== null ? scale.getColor(val) : '#2d333b';
        return L.circleMarker(latlng, {
          radius:      8,
          fillColor:   color,
          color:       '#fff',
          weight:      1,
          opacity:     0.9,
          fillOpacity: 0.85,
        });
      },
      onEachFeature(feature, layer) {
        const name = feature.properties.entity_name || '';
        const val  = feature.properties[field];
        layer.bindTooltip(`
          <strong>${name}</strong><br>
          ${(field || '').replace(/_/g, ' ')}: ${val !== null ? GeoAnalytica.formatNumber(val) : 'N/A'}
        `, { sticky: true });
      },
    }).addTo(mapInstance);
  },

  clear(mapInstance) {
    if (GeoJSONLayer.layer && mapInstance) {
      mapInstance.removeLayer(GeoJSONLayer.layer);
      GeoJSONLayer.layer = null;
    }
  },
};

window.GeoJSONLayer = GeoJSONLayer;
