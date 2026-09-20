/** SPDX-License-Identifier: GPL-3.0-or-later */
const TITLE_STOP_WORDS = new Set([
  'am', 'an', 'auf', 'bei', 'das', 'de', 'der', 'des', 'die', 'in', 'im', 'und',
  'vom', 'von', 'zu', 'zum', 'zur',
]);

export function dedupeMarkets(markets) {
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

  if (a.country && b.country && a.country !== b.country) return false;
  if (!areTitlesRelated(a.name, b.name)) return false;

  const postalA = normalisePostalCode(a.postal_code);
  const postalB = normalisePostalCode(b.postal_code);
  if (postalA && postalB && postalA === postalB) {
    return true;
  }

  const placeA = normalisePlace(a);
  const placeB = normalisePlace(b);
  if (placeA && placeB && placeA === placeB) {
    return true;
  }

  return coordinatesClose(a, b);
}

function isBetterDuplicateCandidate(candidate, current) {
  const hasCoordinates = market => market.latitude != null && market.longitude != null;
  if (hasCoordinates(candidate) !== hasCoordinates(current)) return hasCoordinates(candidate);
  if (Boolean(candidate.geocode_uncertain) !== Boolean(current.geocode_uncertain)) {
    return !candidate.geocode_uncertain;
  }
  const candidateName = String(candidate.name || '');
  const currentName = String(current.name || '');
  if (candidateName.length !== currentName.length) {
    return candidateName.length > currentName.length;
  }
  return Number(candidate.id || 0) > Number(current.id || 0);
}

function normalisePostalCode(value) {
  return String(value || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
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
