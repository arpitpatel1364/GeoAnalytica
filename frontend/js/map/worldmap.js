/* ============================================================
   GeoAnalytica — World Map (Leaflet)
   Initialization, base tile layers, country GeoJSON
   ============================================================ */

const WorldMap = {
  map:             null,
  baseLayer:       null,
  countriesGeoJSON: null,
  _initCallbacks:  [],
  _ready:          false,

  // ── Initialize ────────────────────────────────────────────
  async init(containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) {
      console.error('WorldMap: container not found:', containerId);
      return null;
    }

    WorldMap.map = L.map(containerId, {
      center: options.center  || [20, 0],
      zoom:   options.zoom    || 2,
      minZoom: 1.5,
      maxZoom: 10,
      zoomControl: false,
      attributionControl: true,
      preferCanvas: true,
      worldCopyJump: false,
    });

    // Base tile layer
    const tileStyle = options.style || GeoAnalytica.state.theme;
    WorldMap._setTileLayer(tileStyle);

    // Custom zoom control
    L.control.zoom({ position: 'topright' }).addTo(WorldMap.map);

    // Load world GeoJSON
    try {
      const res = await fetch(
        'https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson'
      );
      WorldMap.countriesGeoJSON = await res.json();
    } catch (e) {
      console.warn('WorldMap: Could not load GeoJSON, using fallback');
      WorldMap.countriesGeoJSON = { type: 'FeatureCollection', features: [] };
    }

    // Render empty base choropleth
    Choropleth.render(null, null);

    // Fit world bounds
    WorldMap.map.fitBounds([[-60, -180], [80, 180]], { animate: false });

    GeoAnalytica.state.mapInstance = WorldMap.map;
    WorldMap._ready = true;
    WorldMap._initCallbacks.forEach(fn => fn(WorldMap.map));
    WorldMap._initCallbacks = [];

    return WorldMap.map;
  },

  onReady(fn) {
    if (WorldMap._ready) fn(WorldMap.map);
    else WorldMap._initCallbacks.push(fn);
  },

  // ── Tile Layers ───────────────────────────────────────────
  _setTileLayer(style) {
    const tiles = {
      dark:      'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      light:     'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
      satellite: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      terrain:   'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    };

    const attribs = {
      dark:      '&copy; <a href="https://carto.com">CartoDB</a>',
      light:     '&copy; <a href="https://carto.com">CartoDB</a>',
      satellite: '&copy; Esri',
      terrain:   '&copy; OpenTopoMap',
    };

    const url  = tiles[style]  || tiles.dark;
    const attr = attribs[style] || attribs.dark;

    if (WorldMap.baseLayer) {
      WorldMap.map.removeLayer(WorldMap.baseLayer);
    }

    WorldMap.baseLayer = L.tileLayer(url, {
      attribution: attr,
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(WorldMap.map);
  },

  setStyle(style) {
    if (!WorldMap.map) return;
    WorldMap._setTileLayer(style);
  },

  // ── Fly to country ────────────────────────────────────────
  flyToCountry(lat, lon, zoom = 5) {
    if (!WorldMap.map) return;
    WorldMap.map.flyTo([lat, lon], zoom, { duration: 1.2 });
  },

  // ── Reset view ────────────────────────────────────────────
  resetView() {
    if (!WorldMap.map) return;
    WorldMap.map.flyToBounds([[-60, -180], [80, 180]], { duration: 0.8 });
  },

  // ── Invalidate size (after panel resize) ──────────────────
  invalidateSize() {
    if (WorldMap.map) WorldMap.map.invalidateSize();
  },
};

window.WorldMap = WorldMap;
