/**
 * RitterRadar — Filter controls and market data fetching
 * SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
 */
import { renderMarkers, setHomePin, flyTo } from './map.js';
import { updateEventsPreview } from './events-preview.js';
import { appLog } from './activity-log.js';

function _log(level, msg) { appLog(level, msg); }

// ── Month selector initialisation ──────────────────────────
const MONTH_NAMES = [
  'Januar','Februar','März','April','Mai','Juni',
  'Juli','August','September','Oktober','November','Dezember'
];

const TITLE_STOP_WORDS = new Set([
  'am', 'an', 'auf', 'bei', 'das', 'de', 'der', 'des', 'die', 'in', 'im', 'und',
  'vom', 'von', 'zu', 'zum', 'zur',
]);

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

function dedupeMarkets(markets) {
  const groups = [];
  for (const market of markets) {
    const match = groups.find(group => areDuplicateMarkets(group.keep, market));
    if (match) {
      if (isBetterDuplicateCandidate(market, match.keep)) {
        match.keep = market;
      }
      continue;
    }
    groups.push({ keep: market });
  }

  const keep = new Set(groups.map(group => group.keep));
  return markets.filter(market => keep.has(market));
}

function areDuplicateMarkets(a, b) {
  if ((a.start_date || '') !== (b.start_date || '') || (a.end_date || '') !== (b.end_date || '')) {
    return false;
  }

  const postalA = normalisePostalCode(a.postal_code);
  const postalB = normalisePostalCode(b.postal_code);
  if (postalA && postalB && postalA === postalB) {
    return true;
  }

  const titlesRelated = areTitlesRelated(a.name, b.name);
  if (!titlesRelated) {
    return false;
  }

  const placeA = normalisePlace(a);
  const placeB = normalisePlace(b);
  if (placeA && placeB && placeA === placeB) {
    return true;
  }

  return coordinatesClose(a, b);
}

function isBetterDuplicateCandidate(candidate, current) {
  const candidateName = String(candidate.name || '');
  const currentName = String(current.name || '');
  if (candidateName.length !== currentName.length) {
    return candidateName.length > currentName.length;
  }
  return Number(candidate.id || 0) > Number(current.id || 0);
}

function normalisePostalCode(value) {
  return String(value || '').replace(/\D/g, '');
}

function normalisePlace(market) {
  const postalCode = normalisePostalCode(market.postal_code);
  if (postalCode) return `plz:${postalCode}`;

  const city = normaliseText(market.city || '');
  if (!city || city.length < 4) return '';
  return `city:${city}`;
}

function normaliseTitle(value) {
  const spaced = String(value || '').replace(/([a-zäöüß])([A-ZÄÖÜ])/g, '$1 $2');
  return normaliseText(spaced)
    .replace(/\b20\d{2}\b/g, ' ')
    .replace(/\b[a-z]{2}\b/g, word => TITLE_STOP_WORDS.has(word) ? ' ' : word)
    .replace(/\s+/g, ' ')
    .trim();
}

function normaliseText(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/ä/g, 'ae')
    .replace(/ö/g, 'oe')
    .replace(/ü/g, 'ue')
    .replace(/ß/g, 'ss')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function titleTokens(value) {
  return normaliseTitle(value)
    .split(/\s+/)
    .filter(token => token.length > 2 && !TITLE_STOP_WORDS.has(token));
}

function areTitlesRelated(a, b) {
  const titleA = normaliseTitle(a);
  const titleB = normaliseTitle(b);
  if (!titleA || !titleB) return false;
  if (titleA === titleB || titleA.includes(titleB) || titleB.includes(titleA)) {
    return true;
  }

  const tokensA = new Set(titleTokens(a));
  const tokensB = new Set(titleTokens(b));
  if (!tokensA.size || !tokensB.size) return false;

  const intersection = [...tokensA].filter(token => tokensB.has(token)).length;
  const union = new Set([...tokensA, ...tokensB]).size;
  return intersection / union >= 0.72;
}

function coordinatesClose(a, b) {
  if (a.latitude == null || a.longitude == null || b.latitude == null || b.longitude == null) {
    return false;
  }

  return distanceKm(a.latitude, a.longitude, b.latitude, b.longitude) <= 1.5;
}

function distanceKm(lat1, lon1, lat2, lon2) {
  const toRad = degrees => degrees * Math.PI / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 6371.0 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// ── Fetch and render ────────────────────────────────────────
let homeCoords = { lat: null, lon: null };
let settingsReady = Promise.resolve();
let latestFetchId = 0;

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

export async function fetchAndRender(silent = false) {
  const fetchId = ++latestFetchId;
  await settingsReady;
  if (fetchId !== latestFetchId) return;

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
    if (!r.ok) { if (!silent) _log('error', `Marktdaten: Serverfehler ${r.status}`); return; }
    const markets = await r.json();
    if (fetchId !== latestFetchId) return;
    const dedupedMarkets = dedupeMarkets(markets);
    renderMarkers(dedupedMarkets);
    updateEventsPreview(dedupedMarkets);
    if (!silent) {
      const hiddenDuplicates = markets.length - dedupedMarkets.length;
      const suffix = hiddenDuplicates ? `, ${hiddenDuplicates} Duplikate ausgeblendet` : '';
      _log('info', `${dedupedMarkets.length} Märkte geladen${suffix}`);
    }
  } catch (err) {
    if (!silent) _log('error', `Marktdaten konnten nicht geladen werden: ${err.message}`);
  }
}

// ── Home geocoding ──────────────────────────────────────────
async function geocodeHome(query) {
  const statusEl = document.getElementById('home-status');
  if (!query.trim()) return;

  statusEl?.classList.remove('hidden', 'ok', 'err');
  statusEl && (statusEl.textContent = 'Suche…');
  _log('info', `Ortssuche: „${query}"…`);

  try {
    const r = await fetch(`/api/settings/geocode?q=${encodeURIComponent(query)}`);
    const data = await r.json();
    if (!data.found) {
      statusEl?.classList.add('err');
      statusEl && (statusEl.textContent = 'Ort nicht gefunden.');
      _log('warn', `Ort nicht gefunden: „${query}"`);
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

    if (data.uncertain) {
      statusEl?.classList.add('ok');
      statusEl && (statusEl.textContent = '⚠ Ungefährer Ort: ' + data.display_name);
      _log('warn', `Ungefährer Ort gefunden: ${data.display_name}`);
    } else {
      statusEl?.classList.add('ok');
      statusEl && (statusEl.textContent = '✓ ' + data.display_name);
      _log('info', `Heimatort gesetzt: ${data.display_name}`);
    }
    await fetchAndRender();
  } catch (err) {
    statusEl?.classList.add('err');
    statusEl && (statusEl.textContent = 'Fehler bei der Suche.');
    _log('error', `Geocoding fehlgeschlagen: ${err.message}`);
  }
}

// ── Wire up events ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  buildMonthOptions();
  settingsReady = loadSettings();
  settingsReady.then(() => fetchAndRender());

  // Radius slider live label
  const radiusEl    = document.getElementById('radius-slider');
  const radiusValEl = document.getElementById('radius-value');
  radiusEl?.addEventListener('input', () => {
    if (radiusValEl) radiusValEl.textContent = radiusEl.value;
  });

  // Apply button
  document.getElementById('btn-apply')?.addEventListener('click', () => {
    _log('info', 'Filter angewendet, Karte wird aktualisiert…');
    fetchAndRender();
  });

  // Refresh button in header
  document.getElementById('btn-refresh')?.addEventListener('click', () => {
    _log('info', 'Manuelle Aktualisierung…');
    fetchAndRender();
  });

  // Geocode button
  document.getElementById('btn-geocode')?.addEventListener('click', () => {
    const q = document.getElementById('home-input')?.value || '';
    geocodeHome(q);
  });

  // Enter key in home input
  document.getElementById('home-input')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') geocodeHome(e.target.value);
  });

  // Auto-refresh every 8 seconds (silent — no log spam)
  settingsReady.then(() => {
    setInterval(() => fetchAndRender(true), 8_000);
  });
});
