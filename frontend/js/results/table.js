/* ============================================================
   GeoAnalytica — Data Table (Tabulator.js)
   ============================================================ */

const DataTable = {
  instance: null,

  init(containerId, data, columns) {
    if (DataTable.instance) {
      DataTable.instance.destroy();
      DataTable.instance = null;
    }

    if (!window.Tabulator) {
      console.warn('Tabulator not loaded');
      return;
    }

    DataTable.instance = new Tabulator('#' + containerId, {
      data,
      columns: columns.map(col => ({
        title:        col.label,
        field:        col.field,
        width:        col.width || undefined,
        sorter:       col.type === 'number' ? 'number' : 'string',
        headerFilter: col.type === 'string' ? 'input' : (col.type === 'number' ? 'number' : undefined),
        formatter:    col.type === 'number'
          ? (cell) => {
              const v = cell.getValue();
              if (v === null || v === undefined) return `<span class="tabulator-cell-null">—</span>`;
              return GeoAnalytica.formatNumber(v);
            }
          : col.type === 'confidence'
          ? (cell) => {
              const v = cell.getValue();
              if (v === null || v === undefined) return `<span class="conf-badge conf-null">—</span>`;
              const cls   = GeoAnalytica.getConfidenceClass(v);
              const label = GeoAnalytica.getConfidenceLabel(v);
              return `<span class="conf-badge ${cls}">${label}</span>`;
            }
          : col.type === 'status'
          ? (cell) => {
              const v = cell.getValue();
              return `<span class="status-badge status-${v}">${v}</span>`;
            }
          : undefined,
        headerFilterPlaceholder: 'Filter…',
        resizable: true,
      })),
      pagination:           'local',
      paginationSize:        50,
      paginationSizeSelector:[25, 50, 100, 250],
      layout:                'fitColumns',
      responsiveLayout:      'hide',
      placeholder:           'No data available',
      height:                '500px',
      movableColumns:        true,
      resizableRows:         false,
      selectable:            false,
      initialSort:           columns[0] ? [{ column: columns[0].field, dir: 'asc' }] : [],
      rowFormatter(row) {
        const data = row.getData();
        if (data.is_outlier) row.getElement().classList.add('is-outlier');
      },
    });
  },

  // ── Pivot data_points into table-friendly rows ────────────
  fromDataPoints(dataPoints) {
    const fields = [...new Set(dataPoints.map(p => p.field_name))];

    // One row per entity + timestamp
    const pivoted = {};
    dataPoints.forEach(pt => {
      const key = `${pt.country_code || pt.entity_name}_${pt.timestamp}`;
      if (!pivoted[key]) {
        pivoted[key] = {
          entity_name:    pt.entity_name,
          country_code:   pt.country_code || '',
          timestamp:      pt.timestamp,
          confidence_score: pt.confidence_score,
          is_outlier:     pt.is_outlier,
        };
      }
      if (!pt.is_null && pt.field_value !== null) {
        pivoted[key][pt.field_name] = pt.field_value;
      } else {
        pivoted[key][pt.field_name] = null;
      }
      pivoted[key][pt.field_name + '_source'] = pt.source_type;
    });

    const rows = Object.values(pivoted);

    const columns = [
      { field: 'entity_name',    label: 'Country',    type: 'string',     width: 160 },
      { field: 'country_code',   label: 'Code',       type: 'string',     width: 60  },
      { field: 'timestamp',      label: 'Year',       type: 'string',     width: 70  },
      ...fields.map(f => ({
        field: f,
        label: f.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
        type: 'number',
      })),
      { field: 'confidence_score', label: 'Confidence', type: 'confidence', width: 100 },
    ];

    return { rows, columns };
  },

  // Download current table data as CSV
  downloadCSV(filename) {
    if (DataTable.instance) {
      DataTable.instance.download('csv', (filename || 'geoanalytica') + '.csv');
    }
  },

  // Filter rows
  setFilter(field, type, value) {
    if (DataTable.instance) {
      DataTable.instance.setFilter(field, type, value);
    }
  },

  clearFilters() {
    if (DataTable.instance) DataTable.instance.clearFilter();
  },

  destroy() {
    if (DataTable.instance) {
      DataTable.instance.destroy();
      DataTable.instance = null;
    }
  },
};

window.DataTable = DataTable;
