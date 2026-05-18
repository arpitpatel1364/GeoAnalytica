/* ============================================================
   GeoAnalytica — Format Utilities
   ============================================================ */

const Format = {
  number:  (n, d = 2)  => GeoAnalytica.formatNumber(n, d),
  percent: (n, d = 1)  => GeoAnalytica.formatPercent(n, d),
  date:    (s)         => GeoAnalytica.formatDate(s),
  dateTime:(s)         => GeoAnalytica.formatDateTime(s),
  relative:(s)         => GeoAnalytica.formatRelativeTime(s),

  bytes(bytes) {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0, n = bytes;
    while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
    return n.toFixed(1) + ' ' + units[i];
  },

  duration(seconds) {
    if (!seconds) return '—';
    if (seconds < 60)  return seconds.toFixed(1) + 's';
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return `${m}m ${s}s`;
  },

  fieldName(field) {
    return (field || '')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  },

  countryCode(code) {
    return (code || '').toUpperCase();
  },
};

window.Format = Format;


/* ============================================================
   GeoAnalytica — Color Scale
   Choropleth color generation from data range
   ============================================================ */

const ColorScale = {
  stops: [
    '#0d2b45', '#0e4d6c', '#0f7094',
    '#1a9bb5', '#39c0c8', '#6ddac2', '#a8f0d4',
  ],

  build(values) {
    const clean = (values || []).filter(v => v !== null && v !== undefined && !isNaN(v));

    if (!clean.length) {
      return {
        min: 0, max: 1,
        getColor: () => '#2d333b',
        getLabels: () => ColorScale.stops.map(() => '—'),
      };
    }

    const min = Math.min(...clean);
    const max = Math.max(...clean);
    const range = max - min || 1;

    return {
      min,
      max,
      getColor(value) {
        if (value === null || value === undefined || isNaN(value)) {
          return getComputedStyle(document.documentElement)
            .getPropertyValue('--choro-null').trim() || '#2d333b';
        }
        const t   = Math.max(0, Math.min(1, (value - min) / range));
        const idx = Math.min(
          Math.floor(t * ColorScale.stops.length),
          ColorScale.stops.length - 1
        );
        return ColorScale.stops[idx];
      },
      getLabels() {
        return ColorScale.stops.map((_, i) => {
          const v = min + (i / (ColorScale.stops.length - 1)) * range;
          return GeoAnalytica.formatNumber(v, 1);
        });
      },
    };
  },

  // Diverging scale (for values that go negative to positive)
  buildDiverging(values) {
    const clean = (values || []).filter(v => v !== null && !isNaN(v));
    if (!clean.length) return ColorScale.build(values);

    const max = Math.max(...clean.map(Math.abs));
    const negStops = ['#f85149', '#d9534f', '#e07070'];
    const posStops = ['#6ddac2', '#39c0c8', '#3fb950'];

    return {
      min: -max, max,
      getColor(value) {
        if (value === null || value === undefined || isNaN(value)) return '#2d333b';
        if (value < 0) {
          const t = Math.min(1, Math.abs(value) / max);
          const idx = Math.floor(t * negStops.length);
          return negStops[Math.min(idx, negStops.length - 1)];
        }
        const t = Math.min(1, value / max);
        const idx = Math.floor(t * posStops.length);
        return posStops[Math.min(idx, posStops.length - 1)];
      },
      getLabels() {
        return [`-${GeoAnalytica.formatNumber(max, 1)}`, '0', GeoAnalytica.formatNumber(max, 1)];
      },
    };
  },
};

window.ColorScale = ColorScale;


/* ============================================================
   GeoAnalytica — CSV Download Utility
   ============================================================ */

const CSVUtil = {
  download(data, filename) {
    if (!data || !data.length) {
      Toast.warning('No data to export');
      return;
    }

    const headers = Object.keys(data[0]);
    const rows    = data.map(row =>
      headers.map(h => {
        const v = row[h];
        if (v === null || v === undefined) return '';
        const str = String(v);
        // Escape fields containing commas, quotes, or newlines
        if (str.includes(',') || str.includes('"') || str.includes('\n')) {
          return `"${str.replace(/"/g, '""')}"`;
        }
        return str;
      }).join(',')
    );

    const csv  = [headers.join(','), ...rows].join('\n');
    const blob = new Blob(['\xef\xbb\xbf' + csv], { type: 'text/csv;charset=utf-8;' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = (filename || 'export') + '.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  fromDataPoints(dataPoints, filename) {
    const rows = dataPoints.map(pt => ({
      entity_name:      pt.entity_name,
      country_code:     pt.country_code || '',
      latitude:         pt.latitude     || '',
      longitude:        pt.longitude    || '',
      timestamp:        pt.timestamp,
      field_name:       pt.field_name,
      field_value:      pt.is_null ? '' : (pt.field_value ?? ''),
      source_type:      pt.source_type,
      source_name:      pt.source_name  || '',
      confidence_score: pt.confidence_score,
      is_outlier:       pt.is_outlier,
      is_null:          pt.is_null,
    }));
    CSVUtil.download(rows, filename || 'geoanalytica_export');
  },
};

window.CSVUtil = CSVUtil;


/* ============================================================
   GeoAnalytica — Form Validation
   ============================================================ */

const Validate = {
  // Returns null if valid, error string if invalid
  email(v) {
    if (!v || !v.trim()) return 'Email is required';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim())) return 'Invalid email address';
    return null;
  },

  required(v, label = 'This field') {
    if (!v || !String(v).trim()) return `${label} is required`;
    return null;
  },

  minLength(v, min, label = 'This field') {
    if (!v || v.length < min) return `${label} must be at least ${min} characters`;
    return null;
  },

  maxLength(v, max, label = 'This field') {
    if (v && v.length > max) return `${label} must be no more than ${max} characters`;
    return null;
  },

  match(v1, v2, label = 'Passwords') {
    if (v1 !== v2) return `${label} do not match`;
    return null;
  },

  number(v, label = 'This field') {
    if (v === '' || v === null || v === undefined) return `${label} is required`;
    if (isNaN(parseFloat(v))) return `${label} must be a number`;
    return null;
  },

  url(v) {
    if (!v || !v.trim()) return null; // URL optional
    try { new URL(v); return null; }
    catch { return 'Invalid URL'; }
  },

  passwordStrength(password) {
    if (!password) return { score: 0, label: 'Too short', color: 'var(--accent-red)', width: '0%' };
    if (password.length < 8) return { score: 1, label: 'Too short', color: 'var(--accent-red)', width: '20%' };
    let score = 1;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    const levels = [
      null,
      { label: 'Weak',        color: 'var(--accent-orange)', width: '40%' },
      { label: 'Fair',        color: 'var(--accent-orange)', width: '60%' },
      { label: 'Strong',      color: 'var(--accent-green)',  width: '80%' },
      { label: 'Very strong', color: 'var(--accent-green)',  width: '100%' },
    ];
    return { score, ...levels[score] };
  },

  // Show inline error on a form field
  showError(fieldId, message) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    field.classList.add('error');
    let errEl = field.parentElement.querySelector('.form-error');
    if (!errEl) {
      errEl = document.createElement('div');
      errEl.className = 'form-error';
      field.parentElement.appendChild(errEl);
    }
    errEl.textContent = message;
  },

  clearError(fieldId) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    field.classList.remove('error');
    const errEl = field.parentElement.querySelector('.form-error');
    if (errEl) errEl.textContent = '';
  },

  clearAllErrors(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    form.querySelectorAll('.form-error').forEach(el => el.textContent = '');
    form.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
  },
};

window.Validate = Validate;
