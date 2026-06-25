/**
 * RitterRadar — Crawler status bar and jobs panel
 * SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
 */
import { fetchAndRender } from './filters.js';
import { appLog } from './activity-log.js';

const STATUS_POLL_MS = 4_000;
let _prevCompleted = -1;
let _prevFailed = -1;

function setBadge(id, count, label) {
  const el = document.getElementById(id);
  if (el) el.textContent = `${count} ${label}`;
}

const STATUS_LABELS = {
  pending:   'wartend',
  running:   'läuft',
  completed: 'fertig',
  failed:    'Fehler',
  skipped:   'übersprungen',
};

function renderJobsPanel(jobs) {
  const list = document.getElementById('jobs-list');
  if (!list) return;
  if (!jobs?.length) {
    list.innerHTML = '<div class="job-empty">Keine Crawler-Jobs vorhanden. Klicke ⟳ Neu laden.</div>';
    return;
  }
  const header = `<div class="job-row job-header">
    <span>Quelle</span><span>Status</span><span>Funde</span><span>Neu</span><span>Fehler</span>
  </div>`;
  const rows = jobs.map(j => {
    const ts = j.finished_at
      ? new Date(j.finished_at).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
      : (j.started_at ? new Date(j.started_at).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }) + '…' : '');
    return `<div class="job-row">
      <span class="job-source" title="${escHtml(j.source_name)}">${escHtml(j.source_name)}</span>
      <span class="job-status ${j.status}" title="${ts}">${STATUS_LABELS[j.status] ?? j.status}</span>
      <span class="job-count">${j.events_discovered ?? 0}</span>
      <span class="job-count">${j.events_inserted ?? 0}</span>
      <span class="job-error" title="${j.error_message ? escHtml(j.error_message) : ''}">${j.error_message ? '⚠ ' + escHtml(j.error_message.substring(0, 60)) : '—'}</span>
    </div>`;
  }).join('');
  list.innerHTML = header + rows;
}

async function pollStatus() {
  try {
    const r = await fetch('/api/crawl/status');
    if (!r.ok) return;
    const data = await r.json();

    setBadge('status-pending',   data.pending   ?? 0, 'wartend');
    setBadge('status-running',   data.running   ?? 0, 'läuft');
    setBadge('status-completed', data.completed ?? 0, 'fertig');
    setBadge('status-failed',    data.failed    ?? 0, 'Fehler');

    renderJobsPanel(data.recent_jobs ?? []);

    // Log transitions
    const completed = data.completed ?? 0;
    const failed    = data.failed ?? 0;
    if (_prevCompleted >= 0 && completed > _prevCompleted) {
      // Find newly completed jobs
      const newJobs = (data.recent_jobs ?? []).slice(0, completed - _prevCompleted);
      newJobs.forEach(j => {
        if (j.status === 'completed') {
          appLog('info', `Crawler fertig: ${j.source_name} — ${j.events_discovered ?? 0} Funde, ${j.events_inserted ?? 0} neu`);
        }
      });
      fetchAndRender();
    }
    if (_prevFailed >= 0 && failed > _prevFailed) {
      const failedJobs = (data.recent_jobs ?? []).filter(j => j.status === 'failed');
      failedJobs.slice(0, failed - _prevFailed).forEach(j => {
        appLog('error', `Crawler-Fehler: ${j.source_name} — ${j.error_message || 'unbekannt'}`);
      });
    }
    _prevCompleted = completed;
    _prevFailed    = failed;
  } catch (_) { /* ignore network errors */ }

  // Geocoding progress
  try {
    const gr = await fetch('/api/crawl/geo-progress');
    if (gr.ok) {
      const gd = await gr.json();
      const geoEl = document.getElementById('status-geo');
      if (geoEl) {
        if (gd.pending > 0) {
          geoEl.textContent = `${gd.geocoded}/${gd.total} geocodiert`;
        } else {
          geoEl.textContent = `${gd.total} geocodiert`;
        }
      }
    }
  } catch (_) { /* ignore */ }
}

document.addEventListener('DOMContentLoaded', () => {
  // Trigger crawl button
  document.getElementById('btn-trigger-crawl')?.addEventListener('click', async () => {
    try {
      const r = await fetch('/api/crawl/trigger', { method: 'POST' });
      const data = await r.json();
      appLog('info', `Crawl gestartet: ${data.enqueued ?? 0} Quellen eingereiht`);
    } catch (err) {
      appLog('error', `Crawl konnte nicht gestartet werden: ${err.message}`);
    }
  });

  // Toggle jobs panel (starts open)
  const jobsPanel = document.getElementById('jobs-panel');
  const toggleBtn = document.getElementById('btn-toggle-jobs');
  toggleBtn?.addEventListener('click', () => {
    const isOpen = !jobsPanel?.classList.contains('hidden');
    jobsPanel?.classList.toggle('hidden');
    if (toggleBtn) toggleBtn.textContent = isOpen ? 'Jobs ▾' : 'Jobs ▲';
  });

  // Listen for hide-market events to re-fetch markers
  window.addEventListener('markets-refresh', () => fetchAndRender());

  // Start polling
  pollStatus();
  setInterval(pollStatus, STATUS_POLL_MS);
});

function escHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
