'use strict';

// Canonical IDs are resolved by archive/open; collection and kind are hints.
// This retired entry carries public navigation data only.
const ARCHIVE_COLLECTIONS = new Set(['physics', 'astronomy', 'mathematics', 'chemistry', 'biology', 'earth_science', 'informatics']);
const ARCHIVE_SUBJECTS = new Set(['classical_mechanics', 'electromagnetism', 'thermodynamics', 'optics', 'quantum_mechanics', 'relativity', 'special_relativity', 'general_relativity', 'statistical_mechanics', 'oscillations_waves', 'mathematical_methods', 'astronomy_astrophysics', 'mathematics', 'chemistry', 'biology', 'earth_science', 'informatics', 'mixed']);
const ARCHIVE_QUERY_RULES = {
  problem: value => /^q_[a-f0-9]{64}$/.test(value),
  source: value => /^src_[a-f0-9]{64}$/.test(value),
  collection: value => ARCHIVE_COLLECTIONS.has(value),
  kind: value => ['contest', 'book', 'course'].includes(value),
  subject: value => ARCHIVE_SUBJECTS.has(value),
  lang: value => ['ko', 'en'].includes(value),
  stars: value => /^[1-5]$/.test(value),
  competition: value => /^[a-z][a-z0-9_-]{1,49}$/.test(value),
  year: value => /^\d{4}$/.test(value) && Number(value) >= 1800 && Number(value) <= 2199,
  type: value => ['theory', 'experiment'].includes(value),
  q: value => value.length <= 600 && value.trim().length > 0 && !/[\u0000-\u001f\u007f-\u009f]/.test(value),
};

function archiveRedirectTarget(href) {
  const target = new URL('https://haslalab.org/');
  target.hash = '/archive/books/phys';
  let legacy;
  try { legacy = new URL(href); } catch { return target.href; }
  const params = new URLSearchParams();
  for (const [key, accepts] of Object.entries(ARCHIVE_QUERY_RULES)) {
    const values = legacy.searchParams.getAll(key);
    // Ambiguous duplicates are dropped rather than given a first/last meaning.
    if (values.length === 1 && accepts(values[0])) params.set(key, key === 'q' ? values[0].trim() : values[0]);
  }
  const language = params.get('lang');
  if (language) target.searchParams.set('lang', language);
  if ([...params.keys()].some(key => key !== 'lang')) target.hash = '/archive/open?' + params.toString();
  return target.href;
}

function redirectToArchive() {
  const target = archiveRedirectTarget(window.location.href);
  const link = document.getElementById('archiveLink');
  if (link) link.href = target;
  if (new URL(target).searchParams.get('lang') === 'en') {
    document.documentElement.lang = 'en';
    document.title = 'Archive · HaslaLab';
    const heading = document.getElementById('archiveHeading');
    const message = document.getElementById('archiveMessage');
    if (heading) heading.textContent = 'Opening the archive';
    if (message) message.textContent = 'Problem materials are available in the archive.';
    if (link) link.textContent = 'Open archive';
  }
  // Keep the manual link usable when browser navigation is blocked.
  try { window.location.replace(target); } catch { /* The validated link stays visible. */ }
}

if (typeof window !== 'undefined' && typeof document !== 'undefined') redirectToArchive();
