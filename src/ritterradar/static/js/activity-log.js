/**
 * RitterRadar — Activity log panel
 * SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
 *
 * Usage: import { appLog } from './activity-log.js'; appLog('info', 'Karte geladen');
 * Or fire a CustomEvent: window.dispatchEvent(new CustomEvent('rr-log', { detail: { level:'info', msg:'...' } }));
 */

const MAX_ENTRIES = 50;
let entries = [];

export function appLog(level, msg) {
  const ts = new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  entries.unshift({ level, msg, ts, id: Date.now() });
  if (entries.length > MAX_ENTRIES) entries.pop();
  _render();
  _flashEntry();
}

// Allow modules without a direct import to log via events
window.addEventListener('rr-log', e => {
  const { level = 'info', msg = '' } = e.detail || {};
  appLog(level, msg);
});

function _render() {
  const list = document.getElementById('log-list');
  if (!list) return;
  if (!entries.length) {
    list.innerHTML = '<span class="log-empty">Keine Ereignisse.</span>';
    return;
  }
  list.innerHTML = entries.map(e => `
    <div class="log-entry log-${e.level}">
      <span class="log-ts">${e.ts}</span>
      <span class="log-msg">${escHtml(e.msg)}</span>
    </div>
  `).join('');
}

function _flashEntry() {
  const panel = document.getElementById('activity-log');
  if (!panel) return;
  panel.classList.add('log-flash');
  setTimeout(() => panel.classList.remove('log-flash'), 600);
}

document.addEventListener('DOMContentLoaded', () => {
  const panel   = document.getElementById('activity-log');
  const toggle  = document.getElementById('log-toggle');
  const body    = document.getElementById('log-body');
  const clearBtn = document.getElementById('log-clear');

  toggle?.addEventListener('click', () => {
    body?.classList.toggle('hidden');
    if (toggle) toggle.textContent = body?.classList.contains('hidden') ? '▲' : '▼';
  });

  clearBtn?.addEventListener('click', () => {
    entries = [];
    _render();
  });

  _render();
  appLog('info', 'Anwendung gestartet');
});

function escHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
