/**
 * RitterRadar — Leaflet map module
 * SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
 */
function _log(level, msg) {
  window.dispatchEvent(new CustomEvent('rr-log', { detail: { level, msg } }));
}

// Tile layer: OpenStreetMap standard tiles
const TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

// Colours per market type (must match CSS)
const TYPE_COLORS = {
  medieval:    '#8b1a1a',
  renaissance: '#1a3a8b',
  viking:      '#3a5a3a',
  fantasy:     '#5a1a8b',
  christmas:   '#7a0020',
};

let map = null;
let markersLayer = null;
let homeMarker = null;
let currentMarkets = [];

// Exposed so other modules can call these
export function initMap() {
  map = L.map('map', {
    center: [51.1657, 10.4515],  // Centre of Germany
    zoom: 6,
    zoomControl: true,
  });

  L.tileLayer(TILE_URL, {
    attribution: TILE_ATTRIBUTION,
    maxZoom: 19,
    subdomains: 'abc',
  }).addTo(map);

  markersLayer = L.layerGroup().addTo(map);

  document.getElementById('map-loading')?.classList.add('hidden');
  _log('info', 'Karte geladen (OpenStreetMap)');
}

export function renderMarkers(markets) {
  if (!markersLayer) return;
  markersLayer.clearLayers();
  currentMarkets = markets;

  const countEl = document.getElementById('market-count');
  if (countEl) countEl.textContent = `${markets.length} Märkte`;

  markets.forEach(market => {
    if (market.latitude == null || market.longitude == null) return;
    const marker = createMarker(market);
    markersLayer.addLayer(marker);
  });
}

function createMarker(market) {
  const color = TYPE_COLORS[market.market_type] || TYPE_COLORS.medieval;
  const uncertain = market.geocode_uncertain;

  const icon = L.divIcon({
    className: '',
    html: `<div class="rr-marker ${market.market_type}${uncertain ? ' rr-marker-uncertain' : ''}"
               style="background:${color}"></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 22],
    popupAnchor: [0, -24],
  });

  const marker = L.marker([market.latitude, market.longitude], { icon });

  // Hover tooltip
  const startFmt = formatDate(market.start_date);
  const endFmt   = formatDate(market.end_date);
  const dateStr  = startFmt === endFmt ? startFmt : `${startFmt} – ${endFmt}`;

  marker.bindTooltip(
    `<b>${escHtml(market.name)}</b><br/>${dateStr}${market.city ? '<br/>' + escHtml(market.city) : ''}`,
    { direction: 'top', offset: [0, -20] }
  );

  // Click → detail panel
  marker.on('click', () => {
    window.dispatchEvent(new CustomEvent('market-selected', { detail: market }));
  });

  return marker;
}

export function setHomePin(lat, lon, label) {
  if (homeMarker) {
    map.removeLayer(homeMarker);
    homeMarker = null;
  }
  if (lat == null || lon == null) return;

  const icon = L.divIcon({
    className: '',
    html: `<div style="
      background:#c5a028;width:18px;height:18px;border-radius:50%;
      border:3px solid #fff;box-shadow:0 0 8px rgba(197,160,40,0.8);
    "></div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });

  homeMarker = L.marker([lat, lon], { icon, zIndexOffset: 1000 })
    .bindTooltip(label || 'Heimatort', { permanent: false });
  homeMarker.addTo(map);
}

export function flyTo(lat, lon, zoom = 8) {
  if (map) map.flyTo([lat, lon], zoom, { duration: 1.2 });
}

function formatDate(isoDate) {
  if (!isoDate) return '';
  const d = new Date(isoDate + 'T00:00:00');
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: 'short', year: 'numeric' });
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Initialise on load — wrap so a missing Leaflet build shows a clear error overlay
try {
  initMap();
} catch (err) {
  const overlay = document.getElementById('map-loading');
  if (overlay) overlay.innerHTML = `<p style="color:#cc4444;padding:1rem">Karte konnte nicht initialisiert werden:<br><code>${err}</code></p>`;
  console.error('RitterRadar map init failed:', err);
}
