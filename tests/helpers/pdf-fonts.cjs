// Minimal PDF reader for the publication tests: lists a PDF's font dictionaries, whether each font program is
// embedded, and whether its ToUnicode map (or name) carries Hangul. Objects inside compressed object streams
// (/Type /ObjStm) are read too. Only object dictionaries, object streams and ToUnicode CMaps are decoded, so a
// large scanned PDF costs one pass over its bytes, not its image data.
const zlib = require('node:zlib');

const HANGUL = cp => (cp >= 0xac00 && cp <= 0xd7a3) || (cp >= 0x1100 && cp <= 0x11ff) || (cp >= 0x3130 && cp <= 0x318f);
const KOREAN_NAME = /KR\b|KR-|Korean|CJK|Hangul|Malgun|Nanum|Batang|Gulim|Dotum|Gungsuh|Myeongjo|Gothic|HY[A-Z]|Pretendard|Spoqa/i;

function inflate(data) {
  try {
    return zlib.inflateSync(data, {finishFlush: zlib.constants.Z_SYNC_FLUSH});
  } catch {
    return null;
  }
}

function readObjects(buffer) {
  const text = buffer.toString('latin1');
  const objects = new Map();
  const streams = new Map();
  const at = new Map();   // where each object was defined: a later definition (an incremental update) wins
  const head = /(\d+)\s+(\d+)\s+obj\b/g;
  let match;
  while ((match = head.exec(text))) {
    const num = Number(match[1]);
    const start = head.lastIndex;
    const endobj = text.indexOf('endobj', start);
    if (endobj < 0) break;
    const s = text.indexOf('stream', start);
    if (s >= 0 && s < endobj && text.startsWith('stream', s) && !text.startsWith('endstream', s - 3)) {
      const dict = text.slice(start, s);
      let dataStart = s + 6;
      if (text[dataStart] === '\r') dataStart++;
      if (text[dataStart] === '\n') dataStart++;
      const endstream = text.indexOf('endstream', dataStart);
      if (endstream < 0) break;
      objects.set(num, dict);
      at.set(num, match.index);
      streams.set(num, [dataStart, endstream]);
      const after = text.indexOf('endobj', endstream);
      head.lastIndex = after < 0 ? text.length : after + 6;
    } else {
      objects.set(num, text.slice(start, endobj));
      at.set(num, match.index);
      streams.delete(num);
      head.lastIndex = endobj + 6;
    }
  }
  const decode = num => {
    const range = streams.get(num);
    if (!range) return null;
    const data = buffer.subarray(range[0], range[1]);
    return /\/FlateDecode/.test(objects.get(num)) ? inflate(data) : data;
  };
  for (const [num, dict] of [...objects]) {
    if (!/\/Type\s*\/ObjStm\b/.test(dict)) continue;
    const data = decode(num);
    if (!data) continue;
    const body = data.toString('latin1');
    const n = Number(dict.match(/\/N\s+(\d+)/)?.[1]);
    const first = Number(dict.match(/\/First\s+(\d+)/)?.[1]);
    const pairs = body.slice(0, first).trim().split(/\s+/).map(Number);
    for (let i = 0; i < n; i++) {
      const from = first + pairs[2 * i + 1];
      const to = i + 1 < n ? first + pairs[2 * i + 3] : body.length;
      // an object kept in a stream is newer than a plain definition earlier in the file
      if (!(at.get(pairs[2 * i]) > at.get(num))) {
        objects.set(pairs[2 * i], body.slice(from, to));
        at.set(pairs[2 * i], at.get(num));
        streams.delete(pairs[2 * i]);
      }
    }
  }
  const roots = [...text.matchAll(/\/Root\s+(\d+)\s+\d+\s+R/g)];
  return {objects, decode, root: roots.length ? Number(roots[roots.length - 1][1]) : undefined, encrypted: /\/Encrypt\s+\d+\s+\d+\s+R/.test(text.slice(-4096)) || [...objects.values()].some(dict => /\/Type\s*\/XRef\b/.test(dict) && /\/Encrypt\s/.test(dict))};
}

function hexCodes(hex) {
  const codes = [];
  for (let i = 0; i + 4 <= hex.length; i += 4) codes.push(parseInt(hex.slice(i, i + 4), 16));
  return codes;
}

function cmapHasHangul(cmap) {
  for (const section of cmap.matchAll(/beginbfchar([\s\S]*?)endbfchar/g)) {
    const tokens = [...section[1].matchAll(/<([0-9A-Fa-f\s]*)>/g)].map(m => m[1].replace(/\s/g, ''));
    for (let i = 1; i < tokens.length; i += 2) if (hexCodes(tokens[i]).some(HANGUL)) return true;
  }
  for (const section of cmap.matchAll(/beginbfrange([\s\S]*?)endbfrange/g)) {
    for (const line of section[1].matchAll(/<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(<[0-9A-Fa-f\s]*>|\[[^\]]*\])/g)) {
      const lo = parseInt(line[1], 16);
      const hi = parseInt(line[2], 16);
      if (line[3].startsWith('[')) {
        if ([...line[3].matchAll(/<([0-9A-Fa-f\s]*)>/g)].some(m => hexCodes(m[1].replace(/\s/g, '')).some(HANGUL))) return true;
      } else {
        const dst = hexCodes(line[3].slice(1, -1).replace(/\s/g, ''));
        if (!dst.length) continue;
        const base = dst[dst.length - 1];
        for (let cp = base; cp <= base + (hi - lo); cp++) if (HANGUL(cp)) return true;
      }
    }
  }
  return false;
}

// -> {encrypted, pages, fonts: [{object, name, subtype, embedded, hangul}]}. An encrypted PDF's strings and streams
// cannot be read without decrypting them, so it reports {encrypted: true} only.
module.exports = function pdfFonts(buffer) {
  const {objects, decode, root, encrypted} = readObjects(buffer);
  if (encrypted) return {encrypted, pages: undefined, fonts: []};
  const ref = (dict, key) => Number(dict.match(new RegExp('/' + key + '\\s+(\\d+)\\s+\\d+\\s+R'))?.[1]);
  // the page count of the document's page tree (the trailer's /Root; an incremental update appends a newer trailer)
  const catalog = objects.get(root) || '';
  const pages = Number(objects.get(ref(catalog, 'Pages'))?.match(/\/Count\s+(\d+)/)?.[1]);
  const descriptorEmbedded = dict => {
    const descriptor = dict.match(/\/FontDescriptor\s*(<<[\s\S]*?>>)/)?.[1] ?? objects.get(ref(dict, 'FontDescriptor'));
    return !!descriptor && /\/FontFile[23]?\s/.test(descriptor);
  };
  const fonts = [];
  for (const [num, dict] of objects) {
    if (!/\/Type\s*\/Font(?![a-zA-Z])/.test(dict)) continue;
    const subtype = dict.match(/\/Subtype\s*\/(\w+)/)?.[1];
    if (subtype === 'CIDFontType0' || subtype === 'CIDFontType2') continue;   // reached through their Type0 parent
    const name = (dict.match(/\/BaseFont\s*\/([^\s/<>\[\]()]+)/)?.[1] || '').replace(/#([0-9A-Fa-f]{2})/g, (m, h) => String.fromCharCode(parseInt(h, 16)));
    let embedded;
    if (subtype === 'Type3') embedded = true;   // glyphs are content streams inside the PDF
    else if (subtype === 'Type0') {
      // /DescendantFonts [12 0 R], 13 0 R (an array object) or [<< … >>]
      const array = dict.match(/\/DescendantFonts\s*(\[[\s\S]*)/)?.[1] ?? objects.get(ref(dict, 'DescendantFonts')) ?? '';
      const id = array.match(/^\s*\[\s*(\d+)\s+\d+\s+R/)?.[1];
      const child = id ? objects.get(Number(id)) : /^\s*\[\s*<</.test(array) ? array : undefined;
      embedded = !!child && descriptorEmbedded(child);
    } else embedded = descriptorEmbedded(dict);
    const toUnicode = ref(dict, 'ToUnicode');
    const cmap = Number.isInteger(toUnicode) ? decode(toUnicode) : null;
    const hangul = cmap ? cmapHasHangul(cmap.toString('latin1')) : KOREAN_NAME.test(name);
    fonts.push({object: num, name, subtype, embedded, hangul});
  }
  return {pages, fonts};
};
