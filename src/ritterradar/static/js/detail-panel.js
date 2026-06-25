/**
 * RitterRadar — Market detail side panel
 * SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
 */
import { appLog } from './activity-log.js';

const PANEL  = () => document.getElementById('detail-panel');
const CONTENT = () => document.getElementById('detail-content');

const TYPE_LABELS = {
  medieval:    'Mittelalter',
  renaissance: 'Renaissance',
  viking:      'Wikinger',
  fantasy:     'Fantasy',
  christmas:   'Weihnacht',
};

function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso + 'T00:00:00').toLocaleDateString('de-DE', {
    weekday: 'short', day: '2-digit', month: 'long', year: 'numeric',
  });
}

function renderDetail(market) {
  const startFmt = fmtDate(market.start_date);
  const endFmt   = fmtDate(market.end_date);
  const dateStr  = market.start_date === market.end_date
    ? startFmt
    : `${startFmt}<br/>bis ${endFmt}`;

  const typeBadge = `<span class="detail-type-badge badge-${esc(market.market_type)}">
    ${esc(TYPE_LABELS[market.market_type] || market.market_type)}
  </span>`;

  const uncertainWarn = market.geocode_uncertain
    ? `<div class="detail-uncertain">⚠ Standort-Angabe unsicher</div>`
    : '';

  const location = [market.postal_code, market.city].filter(Boolean).join(' ') || '—';
  const distStr  = market.distance_km != null ? `${market.distance_km.toFixed(0)} km` : '—';

  const programSection = market.program_text
    ? `<hr class="detail-divider"/>
       <div class="detail-section-title">Programm</div>
       <div class="detail-text">${esc(market.program_text)}</div>`
    : '';

  const originalSection = market.original_text
    ? `<hr class="detail-divider"/>
       <details>
         <summary class="detail-section-title" style="cursor:pointer">Originaltext ▸</summary>
         <div class="detail-text" style="margin-top:0.3rem">${esc(market.original_text)}</div>
       </details>`
    : '';

  const html = `
    ${typeBadge}
    ${uncertainWarn}
    <div class="detail-name">${esc(market.name)}</div>

    <div class="detail-row">
      <span class="detail-label">Datum</span>
      <span class="detail-value">${dateStr}</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">Ort</span>
      <span class="detail-value">${esc(location)}</span>
    </div>
    ${market.address ? `<div class="detail-row">
      <span class="detail-label">Adresse</span>
      <span class="detail-value">${esc(market.address)}</span>
    </div>` : ''}
    <div class="detail-row">
      <span class="detail-label">Entfernung</span>
      <span class="detail-value">${distStr}</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">Quelle</span>
      <span class="detail-value">${esc(market.source_name)}</span>
    </div>

    ${programSection}
    ${originalSection}

    <hr class="detail-divider"/>
    <div class="detail-actions">
      <a class="detail-source-link" href="${esc(market.source_url)}" target="_blank" rel="noopener">
        ↗ Zur Originalseite
      </a>
    </div>
    <div class="detail-actions" style="margin-top:0.4rem">
      <button class="btn-ghost" id="btn-hide-market"
              data-id="${market.id}" data-hidden="${market.hidden}">
        ${market.hidden ? '👁 Einblenden' : '🚫 Ausblenden'}
      </button>
      <a class="btn-ghost" style="text-decoration:none"
         href="https://www.openstreetmap.org/search?query=${encodeURIComponent(location)}"
         target="_blank" rel="noopener">🗺 OSM</a>
    </div>
  `;

  const contentEl = CONTENT();
  if (contentEl) contentEl.innerHTML = html;

  // Wire hide button
  document.getElementById('btn-hide-market')?.addEventListener('click', async e => {
    const btn = e.currentTarget;
    const id  = Number(btn.dataset.id);
    try {
      const r = await fetch(`/api/markets/${id}/hide`, { method: 'POST' });
      if (r.ok) {
        const { hidden } = await r.json();
        btn.dataset.hidden = hidden;
        btn.textContent    = hidden ? '👁 Einblenden' : '🚫 Ausblenden';
        appLog('info', hidden ? 'Markt ausgeblendet' : 'Markt wieder eingeblendet');
        window.dispatchEvent(new CustomEvent('markets-refresh'));
      }
    } catch (err) {
      appLog('error', `Ausblenden fehlgeschlagen: ${err.message}`);
    }
  });
}

function openPanel(market) {
  renderDetail(market);
  PANEL()?.classList.remove('hidden');
}

function closePanel() {
  PANEL()?.classList.add('hidden');
}

// Listen for market selection from map.js
window.addEventListener('market-selected', e => {
  openPanel(e.detail);
  const m = e.detail;
  const loc = [m.postal_code, m.city].filter(Boolean).join(' ') || '?';
  appLog('info', `Markt geöffnet: ${m.name} (${loc})`);
});

// Close button
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('detail-close')?.addEventListener('click', closePanel);
});
