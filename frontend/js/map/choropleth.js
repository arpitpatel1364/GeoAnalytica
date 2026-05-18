/* ============================================================
   GeoAnalytica — Choropleth Layer
   Data-driven country fill colors, legend rendering
   ============================================================ */

const Choropleth = {
  data:       {},   // { iso2: [values] }
  field:      null,
  colorScale: null,
  layer:      null,
  opacity:    0.8,

  // ── Render ────────────────────────────────────────────────
  render(dataPoints, field) {
    Choropleth.field = field;
    Choropleth.data  = {};

    if (dataPoints && dataPoints.length) {
      dataPoints.forEach(pt => {
        if (!pt.is_null && pt.field_value !== null && pt.field_value !== undefined) {
          const code = pt.country_code;
          if (code) {
            if (!Choropleth.data[code]) Choropleth.data[code] = [];
            Choropleth.data[code].push(pt.field_value);
          }
        }
      });
    }

    // Build color scale from actual data range
    const values = Object.values(Choropleth.data).flat();
    Choropleth.colorScale = ColorScale.build(values);

    if (!WorldMap.map || !WorldMap.countriesGeoJSON) return;

    // Remove old layer
    if (Choropleth.layer) {
      WorldMap.map.removeLayer(Choropleth.layer);
      Choropleth.layer = null;
    }

    Choropleth.layer = L.geoJSON(WorldMap.countriesGeoJSON, {
      style:         Choropleth._styleFeature,
      onEachFeature: Choropleth._onEachFeature,
    }).addTo(WorldMap.map);

    // Update legend
    Legend.render(Choropleth.colorScale, field);
  },

  // ── Style ─────────────────────────────────────────────────
  _styleFeature(feature) {
    const code = feature.properties.ISO_A2 || feature.properties.iso_a2;
    const values = Choropleth.data[code];
    let fillColor;

    if (values && values.length > 0) {
      const avg = values.reduce((a, b) => a + b, 0) / values.length;
      fillColor = Choropleth.colorScale
        ? Choropleth.colorScale.getColor(avg)
        : '#1a9bb5';
    } else {
      fillColor = getComputedStyle(document.documentElement)
        .getPropertyValue('--choro-null').trim() || '#2d333b';
    }

    return {
      fillColor,
      weight:      0.5,
      opacity:     0.8,
      color:       '#30363d',
      fillOpacity: Choropleth.opacity,
    };
  },

  // ── Events ────────────────────────────────────────────────
  _onEachFeature(feature, layer) {
    const code = feature.properties.ISO_A2 || feature.properties.iso_a2;
    const name = feature.properties.ADMIN  || feature.properties.name || code;

    layer.on({
      mouseover(e) {
        e.target.setStyle({ weight: 2, opacity: 1, color: '#60697a' });
        e.target.bringToFront();

        const vals = Choropleth.data[code];
        const val  = vals ? vals.reduce((a, b) => a + b, 0) / vals.length : null;

        // Show tooltip
        const tooltip = document.getElementById('map-tooltip');
        if (tooltip) {
          const countryEl  = tooltip.querySelector('.tooltip-country');
          const valueEl    = tooltip.querySelector('.tooltip-value');
          if (countryEl) countryEl.textContent = name;
          if (valueEl) {
            if (val !== null) {
              valueEl.textContent = GeoAnalytica.formatNumber(val);
              valueEl.className = 'tooltip-value';
            } else {
              valueEl.textContent = 'No data';
              valueEl.className = 'tooltip-value tooltip-null';
            }
          }
          tooltip.style.display = 'block';

          // Position relative to map
          const mapEl = document.getElementById('world-map') ||
                        document.getElementById('result-map') ||
                        document.getElementById('demo-map');
          if (mapEl) {
            const mapRect = mapEl.getBoundingClientRect();
            const point   = e.containerPoint;
            tooltip.style.left = (point.x + mapRect.left) + 'px';
            tooltip.style.top  = (point.y + mapRect.top) + 'px';
          }
        }
      },

      mouseout(e) {
        if (Choropleth.layer) Choropleth.layer.resetStyle(e.target);
        const tooltip = document.getElementById('map-tooltip');
        if (tooltip) tooltip.style.display = 'none';
      },

      click() {
        CountryPopup.show(code, name);
      },
    });
  },

  // ── Progressive update (during query) ────────────────────
  updateCountry(countryCode, value) {
    if (!Choropleth.layer || !countryCode) return;

    if (!Choropleth.data[countryCode]) Choropleth.data[countryCode] = [];
    Choropleth.data[countryCode].push(value);

    // Rebuild color scale with new data
    const allValues = Object.values(Choropleth.data).flat();
    Choropleth.colorScale = ColorScale.build(allValues);

    const avg = Choropleth.data[countryCode].reduce((a, b) => a + b, 0) /
                Choropleth.data[countryCode].length;
    const newColor = Choropleth.colorScale.getColor(avg);

    Choropleth.layer.eachLayer(layer => {
      const code = layer.feature?.properties?.ISO_A2 ||
                   layer.feature?.properties?.iso_a2;
      if (code === countryCode) {
        layer.setStyle({ fillColor: newColor, fillOpacity: Choropleth.opacity });
      }
    });

    // Update legend
    Legend.render(Choropleth.colorScale, Choropleth.field);
  },

  // ── Filter to a specific year ─────────────────────────────
  filterToYear(year, allDataPoints) {
    if (!allDataPoints) return;
    const yearStr = String(year);
    const yearPts = allDataPoints.filter(p =>
      p.timestamp && p.timestamp.startsWith(yearStr)
    );
    Choropleth.render(yearPts, Choropleth.field);
  },

  // ── Set opacity ───────────────────────────────────────────
  setOpacity(value) {
    Choropleth.opacity = parseFloat(value);
    if (Choropleth.layer) {
      Choropleth.layer.setStyle({ fillOpacity: Choropleth.opacity });
    }
  },
};

// ── Legend ──────────────────────────────────────────────────
const Legend = {
  render(colorScale, fieldName) {
    const container = document.getElementById('map-legend');
    if (!container) return;

    if (!colorScale || colorScale.min === colorScale.max) {
      container.innerHTML = `
        <div class="legend-title">
          <span>${fieldName ? fieldName.replace(/_/g, ' ') : 'No data'}</span>
        </div>
        <div style="font-size:10px;color:var(--text-muted);margin-top:4px;">Run a query to see data</div>
      `;
      return;
    }

    const stops = ColorScale.stops;
    const labels = colorScale.getLabels ? colorScale.getLabels() : [];

    container.innerHTML = `
      <div class="legend-title">
        <span>${(fieldName || '').replace(/_/g, ' ')}</span>
      </div>
      <div class="legend-gradient-bar"></div>
      <div class="legend-gradient-labels">
        <span>${labels[0] || ''}</span>
        <span>${labels[Math.floor(labels.length / 2)] || ''}</span>
        <span>${labels[labels.length - 1] || ''}</span>
      </div>
      <div class="legend-null-item">
        <div class="legend-swatch" style="background:var(--choro-null)"></div>
        <span>No data</span>
      </div>
    `;
  },
};

window.Choropleth = Choropleth;
window.Legend = Legend;
