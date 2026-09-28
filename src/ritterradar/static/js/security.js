// SPDX-License-Identifier: GPL-3.0-or-later
export function safeWebUrl(value) {
  if (typeof value !== 'string' || value.length > 2048 || /[\s\x00-\x1f\x7f\\]/.test(value)) return null;
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch (_) { return null; }
}
export function apiFetch(url, options = {}) {
  return fetch(url, { ...options, headers: { ...options.headers, 'X-RitterRadar-Request': '1' } });
}
