/* ============================================================
   GeoAnalytica — Timeline Slider
   Year navigation and animated playback
   ============================================================ */

const Timeline = {
  years:        [],
  currentIndex: 0,
  allDataPoints:[],
  isPlaying:    false,
  playInterval: null,
  playSpeed:    1200, // ms per frame

  init(containerId, years, dataPoints) {
    Timeline.years         = [...years].sort();
    Timeline.allDataPoints = dataPoints || [];
    Timeline.currentIndex  = 0;
    Timeline.isPlaying     = false;

    if (Timeline.years.length === 0) return;

    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="timeline-inner">
        <span class="timeline-year" id="tl-year">${Timeline.years[0]}</span>
        <div class="timeline-controls">
          <button class="timeline-btn" id="tl-prev" title="Previous year">◀</button>
          <button class="timeline-btn play-btn" id="tl-play" title="Play/Pause">▶</button>
          <button class="timeline-btn" id="tl-next" title="Next year">▶</button>
        </div>
        <div class="timeline-slider-wrapper">
          <input
            type="range"
            class="timeline-slider"
            id="tl-slider"
            min="0"
            max="${Timeline.years.length - 1}"
            value="0"
            step="1"
          >
          <div class="timeline-markers" id="tl-markers"></div>
        </div>
        <select class="timeline-speed-select" id="tl-speed" title="Playback speed">
          <option value="2000">0.5×</option>
          <option value="1200" selected>1×</option>
          <option value="600">2×</option>
          <option value="300">4×</option>
        </select>
      </div>
    `;

    container.classList.remove('hidden');

    // Render year markers (show ~5 evenly spaced)
    Timeline._renderMarkers();

    // Event listeners
    document.getElementById('tl-slider').addEventListener('input', e => {
      Timeline.goTo(parseInt(e.target.value));
    });

    document.getElementById('tl-prev').addEventListener('click', () => {
      if (Timeline.currentIndex > 0) Timeline.goTo(Timeline.currentIndex - 1);
    });

    document.getElementById('tl-next').addEventListener('click', () => {
      if (Timeline.currentIndex < Timeline.years.length - 1)
        Timeline.goTo(Timeline.currentIndex + 1);
    });

    document.getElementById('tl-play').addEventListener('click', Timeline.togglePlay);

    document.getElementById('tl-speed').addEventListener('change', e => {
      Timeline.playSpeed = parseInt(e.target.value);
      if (Timeline.isPlaying) {
        Timeline._stopPlay();
        Timeline._startPlay();
      }
    });
  },

  _renderMarkers() {
    const container = document.getElementById('tl-markers');
    if (!container || Timeline.years.length === 0) return;

    const maxMarkers = 7;
    const step = Math.max(1, Math.floor(Timeline.years.length / maxMarkers));
    const markerIndexes = [];
    for (let i = 0; i < Timeline.years.length; i += step) {
      markerIndexes.push(i);
    }
    if (!markerIndexes.includes(Timeline.years.length - 1)) {
      markerIndexes.push(Timeline.years.length - 1);
    }

    container.innerHTML = markerIndexes.map(i =>
      `<span class="timeline-marker ${i === Timeline.currentIndex ? 'active' : ''}"
             data-idx="${i}">${Timeline.years[i]}</span>`
    ).join('');
  },

  goTo(index) {
    if (index < 0 || index >= Timeline.years.length) return;
    Timeline.currentIndex = index;

    const slider = document.getElementById('tl-slider');
    const yearEl = document.getElementById('tl-year');

    if (slider) slider.value = index;
    if (yearEl) {
      yearEl.textContent = Timeline.years[index];
      yearEl.classList.add('changing');
      setTimeout(() => yearEl.classList.remove('changing'), 200);
    }

    // Update markers
    document.querySelectorAll('.timeline-marker').forEach(el => {
      el.classList.toggle('active', parseInt(el.dataset.idx) === index);
    });

    // Update choropleth
    Choropleth.filterToYear(Timeline.years[index], Timeline.allDataPoints);
  },

  togglePlay() {
    Timeline.isPlaying = !Timeline.isPlaying;
    const btn = document.getElementById('tl-play');
    if (Timeline.isPlaying) {
      if (btn) btn.innerHTML = '⏸';
      Timeline._startPlay();
    } else {
      if (btn) btn.innerHTML = '▶';
      Timeline._stopPlay();
    }
  },

  _startPlay() {
    Timeline.playInterval = setInterval(() => {
      const next = (Timeline.currentIndex + 1) % Timeline.years.length;
      Timeline.goTo(next);
    }, Timeline.playSpeed);
  },

  _stopPlay() {
    clearInterval(Timeline.playInterval);
    Timeline.playInterval = null;
  },

  destroy() {
    Timeline._stopPlay();
    Timeline.years = [];
    Timeline.allDataPoints = [];
    Timeline.currentIndex = 0;
    Timeline.isPlaying = false;
  },

  updateDataPoints(dataPoints) {
    Timeline.allDataPoints = dataPoints || [];
  },
};

window.Timeline = Timeline;
