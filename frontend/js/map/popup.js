/* ============================================================
   GeoAnalytica — Country Popup
   Click-to-open popup with metrics and sparkline
   ============================================================ */

const CountryPopup = {
  currentPopup: null,

  async show(countryCode, countryName) {
    if (!WorldMap.map) return;

    // Close previous
    if (CountryPopup.currentPopup) {
      WorldMap.map.closePopup(CountryPopup.currentPopup);
    }

    // Find country center from GeoJSON
    let lat = 0, lon = 0;
    if (WorldMap.countriesGeoJSON) {
      const feature = WorldMap.countriesGeoJSON.features.find(f =>
        (f.properties.ISO_A2 || f.properties.iso_a2) === countryCode
      );
      if (feature && feature.geometry) {
        const bounds = L.geoJSON(feature).getBounds();
        const center = bounds.getCenter();
        lat = center.lat;
        lon = center.lng;
      }
    }

    if (!lat && !lon) return;

    // Get current result data for this country
    const result = GeoAnalytica.state.currentResult;
    let metrics = [];
    let sparklineData = null;

    if (result && result.data_points) {
      const countryPts = result.data_points.filter(
        p => p.country_code === countryCode
      );

      // Group by field, get average
      const byField = {};
      countryPts.forEach(p => {
        if (!p.is_null && p.field_value !== null) {
          if (!byField[p.field_name]) byField[p.field_name] = [];
          byField[p.field_name].push({ val: p.field_value, year: p.timestamp.slice(0, 4) });
        }
      });

      Object.entries(byField).forEach(([field, pts]) => {
        const avg = pts.reduce((s, p) => s + p.val, 0) / pts.length;
        metrics.push({
          label: field.replace(/_/g, ' '),
          value: avg,
          isOutlier: countryPts.some(p => p.field_name === field && p.is_outlier),
        });
        // Use primary field for sparkline
        if (!sparklineData && pts.length > 1) {
          sparklineData = pts.sort((a, b) => a.year.localeCompare(b.year));
        }
      });
    }

    // If no result yet, show basic info
    if (!metrics.length) {
      const vals = Choropleth.data[countryCode];
      if (vals && vals.length) {
        const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
        metrics.push({
          label: (Choropleth.field || 'value').replace(/_/g, ' '),
          value: avg,
          isOutlier: false,
        });
      }
    }

    const metricsHTML = metrics.slice(0, 5).map(m => `
      <div class="country-popup-metric">
        <span class="country-popup-metric-label">${m.label}</span>
        <span class="country-popup-metric-value ${m.isOutlier ? 'outlier' : ''}">
          ${GeoAnalytica.formatNumber(m.value)}
        </span>
      </div>
    `).join('') || `
      <div class="country-popup-metric">
        <span class="country-popup-metric-label">No data available</span>
        <span class="country-popup-metric-value null-val">—</span>
      </div>
    `;

    const sparklineHTML = sparklineData && sparklineData.length > 1
      ? `<div class="sparkline-container" style="height:48px;margin-top:8px;">
           <canvas id="sparkline-${countryCode}" class="sparkline-canvas"></canvas>
         </div>`
      : '';

    const popupContent = `
      <div class="country-popup">
        <div class="country-popup-header">
          <div>
            <div class="country-popup-name">${countryName}</div>
            <div class="country-popup-code">${countryCode}</div>
          </div>
        </div>
        <div class="country-popup-body">
          ${metricsHTML}
          ${sparklineHTML}
        </div>
        <div class="country-popup-footer">
          <span class="country-popup-source">Click for full analysis</span>
        </div>
      </div>
    `;

    CountryPopup.currentPopup = L.popup({
      closeButton: true,
      autoClose: true,
      className: 'ga-popup',
      maxWidth: 280,
      offset: [0, -5],
    })
      .setLatLng([lat, lon])
      .setContent(popupContent)
      .openOn(WorldMap.map);

    // Render sparkline after popup is in DOM
    if (sparklineData && sparklineData.length > 1) {
      setTimeout(() => {
        const canvas = document.getElementById(`sparkline-${countryCode}`);
        if (canvas && window.Chart) {
          new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
              labels: sparklineData.map(p => p.year),
              datasets: [{
                data: sparklineData.map(p => p.val),
                borderColor: '#2f81f7',
                borderWidth: 1.5,
                pointRadius: 0,
                fill: true,
                backgroundColor: 'rgba(47,129,247,0.15)',
                tension: 0.4,
              }],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { display: false }, tooltip: { enabled: false } },
              scales: {
                x: { display: false },
                y: { display: false },
              },
              animation: { duration: 400 },
            },
          });
        }
      }, 50);
    }
  },
};

window.CountryPopup = CountryPopup;
