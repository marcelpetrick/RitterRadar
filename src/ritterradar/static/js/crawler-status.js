/**
 * RitterRadar — Crawler status bar and jobs panel
 * SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
 */
import { fetchAndRender } from './filters.js';

const STATUS_POLL_MS = 4_000;

function setBadge(id, count, label) {
  const el = document.getElementById(id);
  if (el) el.textContent = `${count} ${label}`;
}

function renderJobsPanel(jobs) {
  const list = document.getElementById('jobs-list');
  if (!list) return;
  if (!jobs?.length) {
    list.innerHTML = '<div style="padding:0.6rem 1rem;color:var(--text-muted);font-size:0.82rem">Keine Jobs.</div>';
    return;
  }
  list.innerHTML = jobs.map(j => `
    <div class="job-row">
      <span class="job-source" title="${escHtml(j.source_name)}">${escHtml(j.source_name)}</span>
      <span class="job-status ${j.status}">${j.status}</span>
      <span class="job-count">${j.events_discovered ?? 0} Funde</span>
      <span class="job-count">${j.events_inserted ?? 0} neu</span>
      <span class="job-error">${j.error_message ? escHtml(j.error_message) : ''}</span>
    </div>
  `).join('');
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
  } catch (_) { /* ignore network errors */ }
}

document.addEventListener('DOMContentLoaded', () => {
  // Trigger crawl button
  document.getElementById('btn-trigger-crawl')?.addEventListener('click', async () => {
    try {
      const r = await fetch('/api/crawl/trigger', { method: 'POST' });
      const data = await r.json();
      alert(`${data.enqueued ?? 0} Quellen zur Neuindizierung eingereiht.`);
    } catch (_) { /* ignore */ }
  });

  // Toggle jobs panel
  const jobsPanel = document.getElementById('jobs-panel');
  document.getElementById('btn-toggle-jobs')?.addEventListener('click', () => {
    jobsPanel?.classList.toggle('hidden');
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
