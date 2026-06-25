/**
 * RitterRadar — Filter controls and market data fetching
 * SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
 */
import { renderMarkers, setHomePin, flyTo } from './map.js';

// ── Month selector initialisation ──────────────────────────
const MONTH_NAMES = [
  'Januar','Februar','März','April','Mai','Juni',
  'Juli','August','September','Oktober','November','Dezember'
];

function buildMonthOptions() {
  const now   = new Date();
  const fromEl = document.getElementById('month-from');
  const toEl   = document.getElementById('month-to');
  if (!fromEl || !toEl) return;

  for (let offset = 0; offset <= 12; offset++) {
    const d = new Date(now.getFullYear(), now.getMonth() + offset, 1);
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    const label = `${MONTH_NAMES[d.getMonth()]} ${d.getFullYear()}`;
    fromEl.add(new Option(label, value));
    toEl.add(new Option(label, value));
  }

  fromEl.selectedIndex = 0;
  toEl.selectedIndex   = 12;
}

// ── Read filter state ───────────────────────────────────────
function getFilters() {
  const fromEl = document.getElementById('month-from');
  const toEl   = document.getElementById('month-to');
  const radiusEl = document.getElementById('radius-slider');

  const dateFrom = fromEl?.value ? fromEl.value + '-01' : null;
  // date_to: last day of the selected month
  let dateTo = null;
  if (toEl?.value) {
    const [y, m] = toEl.value.split('-').map(Number);
    const last = new Date(y, m, 0).getDate();
    dateTo = `${toEl.value}-${String(last).padStart(2, '0')}`;
  }

  const types = [...document.querySelectorAll('#type-filters input:checked')]
    .map(cb => cb.value);

  return { dateFrom, dateTo, radiusKm: Number(radiusEl?.value || 100), types };
}

// ── Fetch and render ────────────────────────────────────────
let homeCoords = { lat: null, lon: null };

async function loadSettings() {
  try {
    const r = await fetch('/api/settings');
    if (!r.ok) return;
    const s = await r.json();
    if (s.home_latitude != null) {
      homeCoords = { lat: s.home_latitude, lon: s.home_longitude };
      setHomePin(s.home_latitude, s.home_longitude, s.home_label);
      document.getElementById('home-input').value = s.home_label || '';
    }
    const radiusEl = document.getElementById('radius-slider');
    const radiusValEl = document.getElementById('radius-value');
    if (radiusEl) { radiusEl.value = s.default_radius_km; }
    if (radiusValEl) { radiusValEl.textContent = s.default_radius_km; }
  } catch (_) { /* non-fatal */ }
}

export async function fetchAndRender() {
  const { dateFrom, dateTo, radiusKm, types } = getFilters();
  const params = new URLSearchParams();
  if (dateFrom)              params.set('date_from', dateFrom);
  if (dateTo)                params.set('date_to', dateTo);
  if (homeCoords.lat != null) {
    params.set('lat', homeCoords.lat);
    params.set('lon', homeCoords.lon);
    params.set('radius_km', radiusKm);
  }
  types.forEach(t => params.append('market_type', t));

  try {
    const r = await fetch(`/api/markets?${params}`);
    if (!r.ok) return;
    const markets = await r.json();
    renderMarkers(markets);
  } catch (_) { /* network error — silently skip */ }
}

// ── Home geocoding ──────────────────────────────────────────
async function geocodeHome(query) {
  const statusEl = document.getElementById('home-status');
  if (!query.trim()) return;

  statusEl?.classList.remove('hidden', 'ok', 'err');
  statusEl && (statusEl.textContent = 'Suche…');

  try {
    const r = await fetch(`/api/settings/geocode?q=${encodeURIComponent(query)}`);
    const data = await r.json();
    if (!data.found) {
      statusEl?.classList.add('err');
      statusEl && (statusEl.textContent = 'Ort nicht gefunden.');
      return;
    }
    homeCoords = { lat: data.latitude, lon: data.longitude };
    setHomePin(data.latitude, data.longitude, data.display_name);
    flyTo(data.latitude, data.longitude);

    // Save to settings
    await fetch('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        home_latitude: data.latitude,
        home_longitude: data.longitude,
        home_label: data.display_name,
      }),
    });

    statusEl?.classList.add('ok');
    statusEl && (statusEl.textContent = data.uncertain ? '⚠ Ungefährer Ort' : '✓ ' + data.display_name);
    await fetchAndRender();
  } catch (_) {
    statusEl?.classList.add('err');
    statusEl && (statusEl.textContent = 'Fehler bei der Suche.');
  }
}

// ── Wire up events ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  buildMonthOptions();
  loadSettings();
  fetchAndRender();

  // Radius slider live label
  const radiusEl    = document.getElementById('radius-slider');
  const radiusValEl = document.getElementById('radius-value');
  radiusEl?.addEventListener('input', () => {
    if (radiusValEl) radiusValEl.textContent = radiusEl.value;
  });

  // Apply button
  document.getElementById('btn-apply')?.addEventListener('click', fetchAndRender);

  // Refresh button in header
  document.getElementById('btn-refresh')?.addEventListener('click', fetchAndRender);

  // Geocode button
  document.getElementById('btn-geocode')?.addEventListener('click', () => {
    const q = document.getElementById('home-input')?.value || '';
    geocodeHome(q);
  });

  // Enter key in home input
  document.getElementById('home-input')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') geocodeHome(e.target.value);
  });

  // Auto-refresh every 8 seconds
  setInterval(fetchAndRender, 8_000);
});
