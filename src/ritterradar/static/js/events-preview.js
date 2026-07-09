/**
 * RitterRadar — Chronological preview list for the current market filters
 * SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
 */
import { appLog } from './activity-log.js';

let currentMarkets = [];

const TYPE_LABELS = {
  medieval: 'Mittelalter',
  renaissance: 'Renaissance',
  viking: 'Wikinger',
  fantasy: 'Fantasy',
  christmas: 'Weihnacht',
};

function byDateThenName(a, b) {
  const dateCompare = String(a.start_date || '').localeCompare(String(b.start_date || ''));
  if (dateCompare !== 0) return dateCompare;
  return String(a.name || '').localeCompare(String(b.name || ''), 'de');
}

function formatDateRange(market) {
  const start = formatDate(market.start_date);
  const end = formatDate(market.end_date);
  if (!start) return 'Datum offen';
  return start === end || !end ? start : `${start} - ${end}`;
}

function formatDate(iso) {
  if (!iso) return '';
  return new Date(iso + 'T00:00:00').toLocaleDateString('de-DE', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

function locationText(market) {
  return [market.postal_code, market.city].filter(Boolean).join(' ') || market.country || 'Ort offen';
}

function distanceText(market) {
  return market.distance_km != null ? `${Math.round(market.distance_km)} km` : '';
}

function copyLine(market) {
  const distance = distanceText(market);
  const suffix = distance ? ` (${distance})` : '';
  return `${formatDateRange(market)} | ${market.name} | ${locationText(market)}${suffix}`;
}

function renderPreview(markets) {
  const sorted = [...markets].sort(byDateThenName);
  const list = document.getElementById('preview-list');
  const count = document.getElementById('preview-count');
  if (count) count.textContent = String(sorted.length);
  if (!list) return;

  if (!sorted.length) {
    list.className = 'preview-empty';
    list.textContent = 'Keine Märkte im aktuellen Filter.';
    return;
  }

  list.className = 'preview-list';
  list.innerHTML = sorted.map(market => {
    const typeLabel = TYPE_LABELS[market.market_type] || market.market_type || 'Markt';
    const dist = distanceText(market);
    return `<button class="preview-row" data-market-id="${market.id}">
      <span class="preview-date">${esc(formatDateRange(market))}</span>
      <span class="preview-main">
        <span class="preview-name">${esc(market.name)}</span>
        <span class="preview-meta">${esc(locationText(market))}${dist ? ' · ' + esc(dist) : ''}</span>
      </span>
      <span class="preview-type badge-${esc(market.market_type)}">${esc(typeLabel)}</span>
    </button>`;
  }).join('');
}

export function updateEventsPreview(markets) {
  currentMarkets = Array.isArray(markets) ? markets : [];
  renderPreview(currentMarkets);
}

function copyCurrentList() {
  const sorted = [...currentMarkets].sort(byDateThenName);
  if (!sorted.length) {
    appLog('warn', 'Keine Märkte zum Kopieren vorhanden');
    return;
  }

  const text = sorted.map(copyLine).join('\n');
  navigator.clipboard.writeText(text)
    .then(() => appLog('info', `${sorted.length} Märkte als Liste kopiert`))
    .catch(() => appLog('error', 'Liste konnte nicht kopiert werden'));
}

function togglePreview() {
  const panel = document.getElementById('events-preview-panel');
  const toggle = document.getElementById('preview-toggle');
  if (!panel) return;
  const collapsed = panel.classList.toggle('preview-collapsed');
  if (toggle) toggle.textContent = collapsed ? '▲' : '▼';
}

function openMarketFromPreview(id) {
  const market = currentMarkets.find(item => Number(item.id) === id);
  if (market) {
    window.dispatchEvent(new CustomEvent('market-selected', { detail: market }));
  }
}

function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('preview-toggle')?.addEventListener('click', togglePreview);
  document.getElementById('preview-copy')?.addEventListener('click', copyCurrentList);
  document.getElementById('preview-list')?.addEventListener('click', e => {
    const row = e.target.closest('.preview-row');
    if (row) openMarketFromPreview(Number(row.dataset.marketId));
  });
});
