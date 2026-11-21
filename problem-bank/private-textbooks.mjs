const ROUTE = '/api/problem-bank/private-textbooks';
const PREFIX = 'textbook-intake/2026-11-21/viewer-v1';
const HEX = /^[0-9a-f]{64}$/;
const BOOKS = new Set(['goldstein', 'guopei', 'savchenko', 'estonian', 'russian', 'general', 'aptitude']);
const BATCH_SIZE = 24;
const LIST_SIZE = 24;
const MAX_JSON = 6 * 1024 * 1024;
const MAX_IMAGE = 2 * 1024 * 1024;
const HEADERS = {
  'Cache-Control': 'private, no-store',
  'X-Content-Type-Options': 'nosniff',
  'X-Robots-Tag': 'noindex, nofollow, noarchive',
};

const status = (error, code) => Response.json({error}, {status: code, headers: HEADERS});
const json = value => Response.json(value, {headers: HEADERS});
const integer = (value, low, high) => Number.isSafeInteger(value) && value >= low && value <= high;
const index = value => /^[1-9]\d{0,5}$/.test(value) ? Number(value) : NaN;
const text = (value, size) => typeof value === 'string' ? value.slice(0, size) : '';
const sha256 = async bytes => [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))]
  .map(value => value.toString(16).padStart(2, '0')).join('');

async function verifiedObject(bucket, key, expected, limit, range) {
  const object = await bucket.get(key, range ? {range: {offset: range.offset, length: range.length}} : undefined);
  const length = range?.length ?? object?.size;
  const actualRange = object?.range;
  if (!object || !integer(length, 1, limit) ||
      range && (object.size !== range.pack_size || actualRange?.offset !== range.offset ||
                actualRange?.length !== range.length) ||
      !range && actualRange && (actualRange.offset !== 0 || actualRange.length !== length)) {
    await object?.body?.cancel?.().catch(() => {});
    throw Error('textbook_integrity');
  }
  const bytes = await object.arrayBuffer();
  if (bytes.byteLength !== length || await sha256(bytes) !== expected) throw Error('textbook_integrity');
  return bytes;
}

async function readJson(bucket, key, expected) {
  if (!HEX.test(expected)) throw Error('textbook_integrity');
  const bytes = await verifiedObject(bucket, key, expected, MAX_JSON);
  return JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
}

function publicBook(book) {
  return {id: book.id, title: text(book.title, 250), count: book.count,
          korean_count: book.korean_count, limitation: text(book.limitation, 600)};
}

function mediaView(attrs, endpoint) {
  return {id: attrs.id, page: attrs.page ?? null, kind: attrs.kind,
          label: text(attrs.label, 180), url: endpoint + '/media/' + attrs.id};
}

function privVersion(value) {
  return value && typeof value.text === 'string' && value.text.length ? {
    text: text(value.text, 120000),
    review_status: text(value.review_status, 64),
    ...(value.review_basis === 'structured_english_russian' ? {review_basis: value.review_basis} : {}),
  } : null;
}

export const isPrivateTextbookRoute = pathname => pathname === ROUTE || pathname.startsWith(ROUTE + '/');

export async function privateTextbookRoute(request, env, url, user) {
  if (request.method !== 'GET') return status('not_found', 404);
  if (!user) return status('login_required', 401);
  const owners = String(env.BANK_TEXTBOOK_OWNER_IDS || '').split(',').map(id => id.trim());
  if (user.role !== 'admin' || !owners.includes(String(user.id))) return status('private_textbook_access_required', 403);
  const release = String(env.BANK_TEXTBOOK_RELEASE || '');
  if (!HEX.test(release) || !env.LIBRARY?.get) return status('private_textbooks_unavailable', 503);

  const relative = url.pathname.slice(ROUTE.length);
  const list = relative === '/books';
  const match = /^\/books\/([a-z][a-z0-9-]{0,31})(?:\/questions\/([1-9]\d{0,5})(?:\/media\/([1-9]\d{0,5}))?)?$/.exec(relative);
  if (!list && (!match || !BOOKS.has(match[1]))) return status('not_found', 404);
  const query = url.searchParams;
  if ([...query.keys()].some(key => list || match[2] || !['page', 'q'].includes(key)) ||
      query.getAll('page').length > 1 || query.getAll('q').length > 1) return status('invalid_textbook_query', 400);
  const page = query.has('page') ? index(query.get('page')) : 1;
  const search = (query.get('q') || '').trim();
  if (!integer(page, 1, 5000) || search.length > 160 || /[\x00-\x1f\x7f]/.test(search)) {
    return status('invalid_textbook_query', 400);
  }

  const base = PREFIX + '/releases/' + release;
  try {
    const manifest = await readJson(env.LIBRARY, base + '/manifest.json', release);
    if (manifest.schema !== 'haslalab-private-textbook-viewer/v1' ||
        !Array.isArray(manifest.books) || manifest.books.length > 32) throw Error('textbook_integrity');
    const books = manifest.books;
    for (const book of books) {
      if (!BOOKS.has(book?.id) || !integer(book.count, 1, 30000) ||
          !integer(book.korean_count, 0, book.count) || !HEX.test(book.index_sha256) ||
          !Array.isArray(book.batches) || book.batches.length !== Math.ceil(book.count / BATCH_SIZE)) {
        throw Error('textbook_integrity');
      }
    }
    if (list) return json({books: books.map(publicBook)});
    const book = books.find(item => item.id === match[1]);
    if (!book) return status('not_found', 404);
    const bookBase = base + '/' + book.id;
    if (!match[2]) {
      const directory = await readJson(env.LIBRARY, bookBase + '/index.json', book.index_sha256);
      if (!Array.isArray(directory) || directory.length !== book.count) throw Error('textbook_integrity');
      const keyword = search.normalize('NFKC').toLowerCase();
      const found = keyword ? directory.filter(item => [item.number, item.label, item.chapter, item.kind]
        .some(value => text(value, 300).normalize('NFKC').toLowerCase().includes(keyword))) : directory;
      const pages = Math.max(1, Math.ceil(found.length / LIST_SIZE));
      if (page > pages) return status('not_found', 404);
      const items = found.slice((page - 1) * LIST_SIZE, page * LIST_SIZE).map(item => ({
        ordinal: item.ordinal, number: text(item.number, 100), label: text(item.label, 140),
        chapter: text(item.chapter, 160), kind: text(item.kind, 40), has_korean: item.has_korean === true,
      }));
      return json({book: publicBook(book), items, page, pages, total: found.length});
    }
    const ordinal = index(match[2]);
    if (ordinal > book.count) return status('not_found', 404);
    const batch = Math.floor((ordinal - 1) / BATCH_SIZE);
    const rows = await readJson(env.LIBRARY, bookBase + '/batches/' + batch + '.json', book.batches[batch]);
    const row = rows[(ordinal - 1) % BATCH_SIZE];
    if (row?.ordinal !== ordinal || !Array.isArray(row.media) || row.media.length > 100) throw Error('textbook_integrity');
    if (!match[3]) {
      const credit = book.id === 'savchenko' && /^https:\/\/savchenkosolutions\.com\/en\/[0-9]+(?:\.[0-9]+){2}$/.test(row.credit?.source_url)
        ? {source_url: row.credit.source_url, license_url: 'https://creativecommons.org/licenses/by-sa/4.0/'} : null;
      return json({
        book: publicBook(book), ordinal, number: text(row.number, 100), label: text(row.label, 140),
        chapter: text(row.chapter, 160), kind: text(row.kind, 40),
        en: privVersion(row.en), ko: privVersion(row.ko),
        media: row.media.map(item => mediaView(item, url.pathname)),
        ...(credit ? {credit} : {}),
      });
    }
    const asset = row.media.find(item => item.id === index(match[3]));
    if (!asset) return status('not_found', 404);
    if (!HEX.test(asset.pack_sha256) || !HEX.test(asset.sha256) ||
        !integer(asset.pack_size, 12, 1024 * 1024 * 1024) ||
        !integer(asset.offset, 0, asset.pack_size - 1) ||
        !integer(asset.length, 12, Math.min(MAX_IMAGE, asset.pack_size - asset.offset))) {
      throw Error('textbook_integrity');
    }
    const bytes = await verifiedObject(env.LIBRARY, PREFIX + '/media/' + asset.pack_sha256 + '.bin',
                                       asset.sha256, MAX_IMAGE, asset);
    const signature = new Uint8Array(bytes);
    const ascii = position => String.fromCharCode(...signature.subarray(position, position + 4));
    if (ascii(0) !== 'RIFF' || ascii(8) !== 'WEBP') throw Error('textbook_integrity');
    return new Response(bytes, {headers: {
      ...HEADERS, 'Content-Type': 'image/webp', 'Content-Length': String(bytes.byteLength),
      'Content-Security-Policy': "default-src 'none'; sandbox",
    }});
  } catch {
    return status('private_textbooks_unavailable', 503);
  }
}
