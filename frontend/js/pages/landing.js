/* ============================================================
   GeoAnalytica — Landing Page Controller
   ============================================================ */

const LandingPage = {
  async init() {
    // Init demo map with sample GDP data
    await LandingPage._initDemoMap();

    // Animate hero text
    const heroTitle = document.getElementById('hero-title');
    if (heroTitle) {
      heroTitle.style.opacity = '0';
      heroTitle.style.transform = 'translateY(20px)';
      setTimeout(() => {
        heroTitle.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        heroTitle.style.opacity = '1';
        heroTitle.style.transform = 'translateY(0)';
      }, 100);
    }
  },

  async _initDemoMap() {
    const container = document.getElementById('demo-map');
    if (!container) return;

    const map = L.map('demo-map', {
      center: [20, 10], zoom: 1.5, zoomControl: false,
      attributionControl: false, dragging: false, scrollWheelZoom: false,
      doubleClickZoom: false, keyboard: false,
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      subdomains: 'abcd',
    }).addTo(map);

    // Sample choropleth with hardcoded GDP data
    const sampleData = {
      'US': 63544, 'DE': 51204, 'GB': 47334, 'FR': 43659, 'JP': 39285,
      'CN': 12556, 'IN': 2277, 'BR': 7507, 'RU': 11585, 'AU': 55057,
      'CA': 52051, 'IT': 35657, 'KR': 35196, 'MX': 10046, 'ID': 4351,
      'SA': 24253, 'TR': 9661, 'NG': 2085, 'ZA': 6994, 'AR': 10636,
      'EG': 3699, 'TH': 7806, 'PL': 18000, 'PH': 3460, 'MY': 12000,
      'VN': 2786, 'BD': 1947, 'PK': 1357, 'ET': 936, 'KE': 2088,
      'AO': 3437, 'MA': 3819, 'CM': 1680, 'TZ': 1121, 'UG': 912,
      'GH': 2366, 'SN': 1530, 'MZ': 488, 'ZM': 1270, 'ZW': 1463,
    };

    const values = Object.values(sampleData);
    const min = Math.min(...values), max = Math.max(...values);
    const colorStops = ['#0d2b45','#0e4d6c','#0f7094','#1a9bb5','#39c0c8','#6ddac2','#a8f0d4'];

    const getColor = (v) => {
      if (!v) return '#2d333b';
      const t = (v - min) / (max - min);
      return colorStops[Math.min(Math.floor(t * colorStops.length), colorStops.length - 1)];
    };

    try {
      const res = await fetch('https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson');
      const geo = await res.json();

      L.geoJSON(geo, {
        style(feature) {
          const code = feature.properties.ISO_A2;
          return {
            fillColor:   getColor(sampleData[code]),
            weight:      0.4,
            opacity:     0.8,
            color:       '#21262d',
            fillOpacity: 0.85,
          };
        },
      }).addTo(map);

      // Animate year loop
      let yearIdx = 0;
      const years = ['2019', '2020', '2021', '2022', '2023'];
      const yearEl = document.getElementById('demo-year-badge');
      setInterval(() => {
        yearIdx = (yearIdx + 1) % years.length;
        if (yearEl) yearEl.textContent = years[yearIdx];
      }, 2000);

    } catch (e) {
      // Gracefully degrade if GeoJSON fails to load
    }
  },
};

window.LandingPage = LandingPage;

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => LandingPage.init());
} else {
  LandingPage.init();
}
