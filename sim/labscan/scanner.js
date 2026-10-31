/* ------------------------------------------------------------------
   기기 내 문서 스캔 엔진 (v2)
   ------------------------------------------------------------------
   사진의 종이 모서리를 찾아 원근을 보정하고 또렷하게(clean) 다듬습니다.
   모델도, 외부 요청도 없습니다. 모든 계산은 이 기기 안에서 끝납니다.

   흐름:
     사진 → (EXIF 회전 보정) → 작업용 캔버스
          → 인쇄 마커가 있으면 마커로
          → 없으면 아래 findPage (nonsul 스캐너의 방식): 가운데에서 자라는
            밝고 무채색인 영역 = 종이 → 네 변 → 각 변을 실제 경계선에 직선으로 맞춤
          → 원근 보정 (원본 해상도에서 겹샘플링 + 이중선형)
          → 그림자 제거 · 대비 (clean)
          → 품질 점검 (흔들림 · 반사광)

   설계 원칙
   - 계산의 핵심은 캔버스를 모르는 순수 함수입니다. (data, W, H) 만 받습니다.
     그래서 node 에서 그대로 테스트하고 Worker에서도 공유합니다.
   - 적분영상 대신 **슬라이딩 합**을 씁니다. A4 200dpi(1654×2339)에서
     적분영상은 Float64 로 30MB 넘게 잡아먹어 저사양 폰에서 터집니다.
------------------------------------------------------------------- */

/* A4 = 210 × 297 mm */
export const A4_RATIO = 297 / 210;

/** 200dpi 기준 A4 가로 픽셀. 손글씨 OCR 은 150dpi 부터 급격히 나빠집니다. */
export const DEFAULT_DPI = 200;
export const dpiToWidth = (dpi) => Math.round((210 / 25.4) * dpi);

/* 원본을 줄여 담을 최대 변. 출력보다 넉넉해야 겹샘플링 이득이 있습니다. */
const WORK_MAX_SIDE = 2400;
/* The page is straightened from the photo at up to this size, not from the 2400px working copy: shrinking a 12 MP
   photo to 2400px and then enlarging the page to 1654px wide lost about a third of the stroke sharpness. Detection,
   the editable baseline and corner coordinates stay in the working copy's space. */
export const SOURCE_MAX_SIDE = 4096;
/* corners are found on a copy at most this large (about three times faster than on the working copy); the page is
   cut out of the decoded photo and resampled so that its short side is at most PAGE_SOURCE_SIDE (1.45 × the 1654px
   output) before it is straightened in the worker */
const DETECT_MAX_SIDE = 1600, PAGE_SOURCE_SIDE = 2400;

/**
 * 답안지에 인쇄한 마커 **중심**이 A4 지면에서 차지하는 위치 (0~1).
 * ⚠ 답안지 조판을 바꾸면 이 값도 같이 바꿔야 합니다.
 *   기본값은 좌우 여백 9.45mm, 상하 여백 10.4mm 자리에 마커 중심을
 *   찍는 조판을 가정합니다.
 */
export const MARKER_INSET = { left: 0.045, top: 0.035, right: 0.955, bottom: 0.965 };

/* ==================================================================
   1. 순수 계산 코어  (캔버스를 모릅니다)
   ================================================================== */

/** RGBA → 밝기 (Rec.601) */
export function toGray(data, W, H) {
  const g = new Uint8Array(W * H);
  for (let p = 0, i = 0; p < W * H; p++, i += 4) {
    g[p] = (data[i] * 299 + data[i + 1] * 587 + data[i + 2] * 114) / 1000;
  }
  return g;
}

/**
 * 박스 평균 — 슬라이딩 합으로 O(W·H).
 * 적분영상과 결과는 같지만 메모리는 두 줄짜리 버퍼만 씁니다.
 * @param {Float32Array|Uint8Array} src
 * @returns {Float32Array} 각 픽셀의 (2r+1)² 창 평균
 */
export function boxMean(src, W, H, r) {
  const tmp = new Float32Array(W * H);
  const out = new Float32Array(W * H);

  /* 가로 방향 */
  for (let y = 0; y < H; y++) {
    const row = y * W;
    let sum = 0;
    for (let x = 0; x <= r && x < W; x++) sum += src[row + x];
    let count = Math.min(r + 1, W);
    for (let x = 0; x < W; x++) {
      tmp[row + x] = sum / count;
      const add = x + r + 1;
      const sub = x - r;
      if (add < W) { sum += src[row + add]; count++; }
      if (sub >= 0) { sum -= src[row + sub]; count--; }
    }
  }

  /* 세로 방향 */
  for (let x = 0; x < W; x++) {
    let sum = 0;
    for (let y = 0; y <= r && y < H; y++) sum += tmp[y * W + x];
    let count = Math.min(r + 1, H);
    for (let y = 0; y < H; y++) {
      out[y * W + x] = sum / count;
      const add = y + r + 1;
      const sub = y - r;
      if (add < H) { sum += tmp[add * W + x]; count++; }
      if (sub >= 0) { sum -= tmp[sub * W + x]; count--; }
    }
  }
  return out;
}

/** 오츠 임계값 — 밝기 히스토그램을 두 덩어리로 가장 잘 가르는 지점 */
export function otsu(gray, step = 1) {
  const hist = new Float64Array(256);
  let n = 0;
  for (let i = 0; i < gray.length; i += step) { hist[gray[i]]++; n++; }
  let sum = 0;
  for (let v = 0; v < 256; v++) sum += v * hist[v];

  /* 최대값이 여러 칸에 걸쳐 평평할 때(두 봉우리 사이가 텅 빈 경우)
     첫 칸을 집으면 임계값이 한쪽 봉우리에 딱 붙습니다. 평평한 구간의
     한가운데를 잡아야 잡음에 흔들리지 않습니다. */
  let sumB = 0, wB = 0, lo = 0, hi = 0, bestVar = -1;
  for (let v = 0; v < 256; v++) {
    wB += hist[v];
    if (!wB) continue;
    const wF = n - wB;
    if (!wF) break;
    sumB += v * hist[v];
    const mB = sumB / wB;
    const mF = (sum - sumB) / wF;
    const between = wB * wF * (mB - mF) * (mB - mF);
    if (between > bestVar * 1.000001) { bestVar = between; lo = hi = v; }
    else if (between >= bestVar * 0.999999) hi = v;
  }
  return Math.round((lo + hi) / 2);
}

/**
 * 네 점을 좌상·우상·좌하·우하 순으로 정렬합니다.
 * 무게중심에서의 각도로 나눕니다. 뒤집힌 사진에도 안전합니다.
 */
export function orderCorners(pts) {
  if (!pts || pts.length !== 4) return pts;
  const cx = pts.reduce((a, p) => a + p.x, 0) / 4;
  const cy = pts.reduce((a, p) => a + p.y, 0) / 4;
  const tag = pts.map((p) => ({ ...p, left: p.x < cx, top: p.y < cy }));
  const pick = (l, t) => tag.find((p) => p.left === l && p.top === t);
  const tl = pick(true, true), tr = pick(false, true);
  const bl = pick(true, false), br = pick(false, false);
  /* 사분면이 하나라도 비면(찌그러진 사각형) 각도순으로 대체 */
  if (!tl || !tr || !bl || !br) {
    const sorted = [...pts].sort(
      (a, b) => Math.atan2(a.y - cy, a.x - cx) - Math.atan2(b.y - cy, b.x - cx)
    );
    /* 각도순은 좌상에서 시작한다는 보장이 없으니 x+y 가 최소인 점을 앞으로 */
    let s = 0, min = Infinity;
    sorted.forEach((p, i) => { if (p.x + p.y < min) { min = p.x + p.y; s = i; } });
    const r = [...sorted.slice(s), ...sorted.slice(0, s)]; // 시계방향 tl,tr,br,bl
    return [r[0], r[1], r[3], r[2]];
  }
  return [
    { x: tl.x, y: tl.y }, { x: tr.x, y: tr.y },
    { x: bl.x, y: bl.y }, { x: br.x, y: br.y },
  ];
}

/** 사각형이 문서로 말이 되는지 (평행 정도 · 크기 · 볼록성) */
export function quadScore(corners, W, H) {
  if (!corners || corners.length !== 4) return 0;
  const [tl, tr, bl, br] = corners;
  const top = Math.hypot(tr.x - tl.x, tr.y - tl.y);
  const bottom = Math.hypot(br.x - bl.x, br.y - bl.y);
  const left = Math.hypot(bl.x - tl.x, bl.y - tl.y);
  const right = Math.hypot(br.x - tr.x, br.y - tr.y);
  if (!top || !bottom || !left || !right) return 0;

  const hBal = Math.min(top, bottom) / Math.max(top, bottom);
  const vBal = Math.min(left, right) / Math.max(left, right);

  /* 넓이 (신발끈 공식) */
  const poly = [tl, tr, br, bl];
  let area = 0;
  for (let i = 0; i < 4; i++) {
    const a = poly[i], b = poly[(i + 1) % 4];
    area += a.x * b.y - b.x * a.y;
  }
  area = Math.abs(area) / 2;
  const cover = area / (W * H);

  /* 볼록한가 — 외적 부호가 네 번 다 같아야 합니다 */
  let sign = 0, convex = true;
  for (let i = 0; i < 4; i++) {
    const a = poly[i], b = poly[(i + 1) % 4], c = poly[(i + 2) % 4];
    const cross = (b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x);
    const s = Math.sign(cross);
    if (!sign) sign = s;
    else if (s && s !== sign) convex = false;
  }
  if (!convex) return 0;

  const sizeOk = Math.min(1, cover / 0.28);
  return Math.max(0, Math.min(1, hBal * vBal * sizeOk));
}

/* ---------- ① 인쇄 마커 찾기 ---------- */

/**
 * 답안지 네 귀퉁이의 검은 정사각 마커를 찾습니다.
 *
 * 우리는 답안지를 직접 인쇄하므로 마커를 심어둘 수 있습니다.
 * 일반 스캐너가 종이 테두리를 더듬는 것보다 훨씬 정확합니다.
 *
 * v1 대비 고친 것
 *  - 덩어리 채우기를 사분면 안에 가두지 않습니다. 경계에 걸친 마커가
 *    잘려서 크기 검사에 떨어지던 문제를 없앴습니다. (씨앗만 사분면 안)
 *  - 사분면을 44% 로 넓혀 여백이 큰 촬영에서도 잡힙니다.
 *  - 채움률·정사각도 외에 **외곽 근접도**를 함께 점수화합니다.
 *
 * @returns {{corners:{x,y}[], score:number, method:string}}
 */
export function findMarkersGray(gray, W, H) {
  /* 밝기 분포로 "어둡다"의 기준을 정합니다.
     130 같은 절대값은 어두운 방에서 전부 실패합니다. */
  const hist = new Uint32Array(256);
  for (let i = 0; i < gray.length; i += 3) hist[gray[i]]++;
  let total = 0;
  for (let v = 0; v < 256; v++) total += hist[v];

  let acc = 0, p5 = 0, p60 = 255;
  for (let v = 0; v < 256; v++) {
    acc += hist[v];
    if (!p5 && acc > total * 0.05) p5 = v;
    if (acc > total * 0.6) { p60 = v; break; }
  }
  let dark = Math.round(p5 + (p60 - p5) * 0.32);
  dark = Math.max(p5 + 6, Math.min(dark, p60 - 4));
  if (dark < 8) dark = 8;

  const zone = 0.44;
  const quads = [
    { x0: 0, y0: 0, x1: W * zone, y1: H * zone, ox: 0, oy: 0 },
    { x0: W * (1 - zone), y0: 0, x1: W, y1: H * zone, ox: 1, oy: 0 },
    { x0: 0, y0: H * (1 - zone), x1: W * zone, y1: H, ox: 0, oy: 1 },
    { x0: W * (1 - zone), y0: H * (1 - zone), x1: W, y1: H, ox: 1, oy: 1 },
  ];

  const px = W * H;
  const minBlob = Math.max(6, Math.round(px / 120000));
  const maxBlob = Math.round(px / 220);

  const seen = new Uint8Array(px);
  const stack = new Int32Array(Math.min(px, maxBlob * 6 + 256));

  const corners = [];
  let found = 0;

  for (const q of quads) {
    const X0 = Math.max(0, Math.floor(q.x0)), Y0 = Math.max(0, Math.floor(q.y0));
    const X1 = Math.min(W, Math.ceil(q.x1)), Y1 = Math.min(H, Math.ceil(q.y1));
    const anchorX = q.ox ? W : 0, anchorY = q.oy ? H : 0;
    let best = null;

    for (let y = Y0; y < Y1; y++) {
      for (let x = X0; x < X1; x++) {
        const seed = y * W + x;
        if (seen[seed] || gray[seed] >= dark) continue;

        /* 씨앗은 사분면 안에서만 고르지만, 채우기는 사진 전체로 퍼집니다 */
        let sp = 0, n = 0, sx = 0, sy = 0;
        let bx0 = x, by0 = y, bx1 = x, by1 = y;
        let overflow = false;
        stack[sp++] = seed;
        seen[seed] = 1;

        while (sp > 0) {
          const cur = stack[--sp];
          const cy = (cur / W) | 0, cx = cur - cy * W;
          n++; sx += cx; sy += cy;
          if (cx < bx0) bx0 = cx; if (cx > bx1) bx1 = cx;
          if (cy < by0) by0 = cy; if (cy > by1) by1 = cy;
          if (n > maxBlob) { overflow = true; break; }

          for (let k = 0; k < 4; k++) {
            const nx = cx + (k === 0 ? 1 : k === 1 ? -1 : 0);
            const ny = cy + (k === 2 ? 1 : k === 3 ? -1 : 0);
            if (nx < 0 || nx >= W || ny < 0 || ny >= H) continue;
            const np = ny * W + nx;
            if (seen[np] || gray[np] >= dark) continue;
            seen[np] = 1;
            if (sp < stack.length) stack[sp++] = np;
          }
        }
        if (overflow || n < minBlob) continue;

        /* 마커는 정사각형에 가깝고 속이 꽉 찹니다.
           글씨·그림자·머리카락은 길쭉하거나 성깁니다. */
        const bw = bx1 - bx0 + 1, bh = by1 - by0 + 1;
        const square = Math.min(bw, bh) / Math.max(bw, bh);
        const fill = n / (bw * bh);
        if (square < 0.62 || fill < 0.6) continue;

        const cx = sx / n, cy = sy / n;
        /* 무게중심이 자기 사분면 밖으로 나가면 남의 것입니다 */
        if (cx < X0 - 2 || cx > X1 + 2 || cy < Y0 - 2 || cy > Y1 + 2) continue;

        const dist = Math.hypot(cx - anchorX, cy - anchorY);
        const quality = square * fill;
        const rank = dist / Math.max(0.05, quality);
        if (!best || rank < best.rank) best = { x: cx, y: cy, rank, square, fill };
      }
    }

    if (best) { corners.push({ x: best.x, y: best.y }); found++; }
    else corners.push({ x: q.ox ? W * 0.94 : W * 0.06, y: q.oy ? H * 0.94 : H * 0.06 });
  }

  if (found < 4) return { corners, score: found / 4 * 0.5, method: 'marker', found };

  const ordered = orderCorners(corners);
  const s = quadScore(ordered, W, H);
  return { corners: ordered, score: s, method: 'marker', found };
}

/* ---------- ①′ 인쇄 마커 찾기 v3: 조명에 따라 바뀌는 문턱 + 네 마커의 기하 검증 ---------- */

/** 마커 네 중심이 이루는 사각형의 짧은 변 · 긴 변 (mm) 과 마커 한 변 (mm) — sheets.html 의 조판 */
export const MARKER_GEOM = { short: 191.1, long: 276.2, side: 7 };

/**
 * v2 는 사진 전체에 문턱 하나를 쓰고 사분면마다 가장 그럴듯한 덩어리를 따로 골랐습니다. 그래서 한쪽이 어두운
 * 사진이나 원근이 센 사진에서는 엉뚱한 덩어리를 마커로 집었습니다. v3 는
 *  - 둘레 평균보다 확실히 어두운 곳을 어둡다고 봅니다 (그늘 · 조명 기울기에 강함).
 *  - 정사각에 가깝고 꽉 찬 덩어리를 후보로 모은 뒤, 네 개 묶음마다 «마커 크기가 그 자리의 종이 크기에 맞는가»,
 *    «네 점이 A4 마커 사각형처럼 볼록하고 비율이 맞는가»를 따져 가장 잘 맞는 묶음을 고릅니다.
 *  - 고른 마커의 중심은 원본 해상도에서 다시 잽니다.
 * @returns {{corners:{x,y}[], score:number, method:'marker'}|null}
 */
export function findSheetMarkersGray(gray, W, H) {
  /* 1. 작업 크기로 줄이기 (평균 풀링) */
  const f = Math.max(1, Math.ceil(Math.max(W, H) / 900));
  const w = Math.floor(W / f), h = Math.floor(H / f);
  const g = new Float32Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let a = 0;
    for (let j = 0; j < f; j++) { const row = (y * f + j) * W + x * f; for (let i = 0; i < f; i++) a += gray[row + i]; }
    g[y * w + x] = a / (f * f);
  }
  /* 2. 둘레보다 어두운 곳 */
  const mean = boxMean(g, w, h, Math.max(8, Math.round(Math.min(w, h) / 16)));
  const dark = new Uint8Array(w * h);
  for (let i = 0; i < w * h; i++) dark[i] = g[i] < mean[i] * 0.62 && g[i] < mean[i] - 18 ? 1 : 0;
  /* 3. 덩어리 → 후보 */
  const minSide = Math.min(w, h), maxArea = (minSide * 0.12) ** 2, seen = new Uint8Array(w * h), stack = new Int32Array(w * h);
  const cands = [];
  for (let s0 = 0; s0 < w * h; s0++) {
    if (!dark[s0] || seen[s0]) continue;
    let sp = 0, n = 0, sx = 0, sy = 0, x0 = w, y0 = h, x1 = 0, y1 = 0;
    stack[sp++] = s0; seen[s0] = 1;
    while (sp) {
      const c = stack[--sp], cy = (c / w) | 0, cx = c - cy * w;
      n++; sx += cx; sy += cy;
      if (cx < x0) x0 = cx; if (cx > x1) x1 = cx; if (cy < y0) y0 = cy; if (cy > y1) y1 = cy;
      if (cx > 0 && dark[c - 1] && !seen[c - 1]) { seen[c - 1] = 1; stack[sp++] = c - 1; }
      if (cx < w - 1 && dark[c + 1] && !seen[c + 1]) { seen[c + 1] = 1; stack[sp++] = c + 1; }
      if (cy > 0 && dark[c - w] && !seen[c - w]) { seen[c - w] = 1; stack[sp++] = c - w; }
      if (cy < h - 1 && dark[c + w] && !seen[c + w]) { seen[c + w] = 1; stack[sp++] = c + w; }
    }
    if (n < 20 || n > maxArea) continue;
    const bw = x1 - x0 + 1, bh = y1 - y0 + 1, square = Math.min(bw, bh) / Math.max(bw, bh), fill = n / (bw * bh);
    if (square < 0.55 || fill < 0.62) continue;
    cands.push({ x: sx / n, y: sy / n, side: Math.sqrt(n), q: square * fill, x0, y0, x1, y1 });
  }
  if (cands.length < 4) return null;
  cands.sort((a, b) => b.q * b.side - a.q * a.side);
  const C = cands.slice(0, 16);
  /* 4. 네 개 묶음마다 기하 점수 */
  const { short: S, long: L, side: M } = MARKER_GEOM;
  let best = null;
  for (let a = 0; a < C.length; a++) for (let b = a + 1; b < C.length; b++) for (let c = b + 1; c < C.length; c++) for (let d = c + 1; d < C.length; d++) {
    const set = [C[a], C[b], C[c], C[d]];
    const o = orderCorners(set);
    const pick = o.map((p) => set.find((q) => q.x === p.x && q.y === p.y));
    if (pick.some((q) => !q)) continue;
    const qs = quadScore(o, w, h);
    if (qs <= 0) continue;
    const [tl, tr, bl, br] = o, len = (p, q) => Math.hypot(p.x - q.x, p.y - q.y);
    const top = len(tl, tr), bot = len(bl, br), lef = len(tl, bl), rig = len(tr, br);
    const hor = (top + bot) / 2, ver = (lef + rig) / 2;
    const ratio = Math.max(hor, ver) / Math.min(hor, ver);
    if (ratio < 1.05 || ratio > 2.3) continue;                         // A4 마커 사각형은 1.45
    /* 그 모서리에서 종이 1mm 가 몇 픽셀인가 → 마커가 있어야 할 크기 */
    const adj = [[top, lef], [top, rig], [bot, lef], [bot, rig]];
    let off = 0;
    for (let i = 0; i < 4; i++) {
      const [ha, va] = adj[i], mm = Math.sqrt((Math.max(ha, va) / L) * (Math.min(ha, va) / S));
      const r = pick[i].side / (M * mm);
      if (r < 0.55 || r > 1.8) { off = Infinity; break; }
      off += Math.abs(Math.log(r));
    }
    if (!isFinite(off)) continue;
    const sides = pick.map((q) => q.side), even = Math.min(...sides) / Math.max(...sides);
    const score = qs * Math.exp(-off / 2) * (0.5 + 0.5 * even) * Math.exp(-Math.abs(Math.log(ratio / (L / S))));
    if (!best || score > best.score) best = { score, pick };
  }
  if (!best) return null;
  /* 5. 원본 해상도에서 중심 다시 재기 */
  const corners = best.pick.map((q) => {
    const pad = Math.max(2, (q.x1 - q.x0) * 0.3);
    const X0 = Math.max(0, Math.floor((q.x0 - pad) * f)), X1 = Math.min(W - 1, Math.ceil((q.x1 + 1 + pad) * f));
    const Y0 = Math.max(0, Math.floor((q.y0 - pad) * f)), Y1 = Math.min(H - 1, Math.ceil((q.y1 + 1 + pad) * f));
    let lo = 255, hi = 0;
    for (let y = Y0; y <= Y1; y++) for (let x = X0; x <= X1; x++) { const v = gray[y * W + x]; if (v < lo) lo = v; if (v > hi) hi = v; }
    const thr = (lo + hi) / 2;
    let n = 0, sx = 0, sy = 0;
    for (let y = Y0; y <= Y1; y++) for (let x = X0; x <= X1; x++) { const v = thr - gray[y * W + x]; if (v > 0) { n += v; sx += v * x; sy += v * y; } }
    return n ? { x: sx / n + 0.5, y: sy / n + 0.5 } : { x: (q.x + 0.5) * f, y: (q.y + 0.5) * f };
  });
  return { corners: orderCorners(corners), score: Math.min(1, 0.35 + best.score), method: 'marker' };
}

/* ---------- ② 종이 테두리 찾기 (마커 없는 사진) ---------- */

/* ---------- page finder (v2, after nonsul's scanner): where the sheet of paper is, from the photo's own pixels, with no model.

   1. Region. On a copy of about 320px, every pixel gets a "paperness": bright and colourless (paper) against coloured or
      dark (wood, desks, cloth). Otsu splits it, and the bright region grown from the middle of the frame is the sheet.
      Small detail (writing, grid lines, boxes) disappears at that size, so the sheet is one piece. Unlike edge or model
      based finders this does not depend on the sheet being whole in the frame or evenly lit.
   2. Four sides. The region's convex hull is cut down to four corners by dropping, one at a time, the corner whose
      removal loses the least area.
   3. Edges. At about 1600px each side is fitted again on the same paperness (so a dark seam in light wood beside the
      sheet is not an edge): along 64 normals the step from bright inside to darker outside is measured, and a straight line is fitted through those points (outliers dropped twice). Sides lying on the border of
      the frame, where the sheet runs out of the photo, stay on the border. Neighbouring lines meet at the corners.

   The result is verified when every side inside the frame was seen along most of its length. */

const COARSE = 320, FINE = 1600, SAMPLES = 64;

const pfCross = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);

/** corners as top-left, top-right, bottom-left, bottom-right */
function orderFour(pts) {
  const c = pts.reduce((s, p) => ({ x: s.x + p.x / 4, y: s.y + p.y / 4 }), { x: 0, y: 0 });
  const byAngle = [...pts].sort((a, b) => Math.atan2(a.y - c.y, a.x - c.x) - Math.atan2(b.y - c.y, b.x - c.x));
  let start = 0, least = Infinity;
  byAngle.forEach((p, i) => { if (p.x + p.y < least) { least = p.x + p.y; start = i; } });
  const ring = [0, 1, 2, 3].map(i => byAngle[(start + i) % 4]);       // clockwise from top-left: tl, tr, br, bl
  return [ring[0], ring[1], ring[3], ring[2]];
}

function pfHull(points) {
  points.sort((a, b) => a.x - b.x || a.y - b.y);
  const lower = [], upper = [];
  for (const p of points) { while (lower.length > 1 && pfCross(lower.at(-2), lower.at(-1), p) <= 0) lower.pop(); lower.push(p); }
  for (let i = points.length - 1; i >= 0; i--) { const p = points[i]; while (upper.length > 1 && pfCross(upper.at(-2), upper.at(-1), p) <= 0) upper.pop(); upper.push(p); }
  lower.pop(); upper.pop(); return lower.concat(upper);
}

function fourOf(ring) {
  if (ring.length < 4) return null;
  ring = [...ring];
  while (ring.length > 4) {
    let at = 0, least = Infinity;
    for (let i = 0; i < ring.length; i++) {
      const area = Math.abs(pfCross(ring[(i + ring.length - 1) % ring.length], ring[i], ring[(i + 1) % ring.length]));
      if (area < least) { least = area; at = i; }
    }
    ring.splice(at, 1);
  }
  return orderFour(ring);
}

function pfOtsu(values) {
  const hist = new Float64Array(256);
  for (const v of values) hist[v]++;
  const n = values.length; let sum = 0;
  for (let i = 0; i < 256; i++) sum += i * hist[i];
  let sumB = 0, wB = 0, best = 0, t = 128;
  for (let i = 0; i < 256; i++) {
    wB += hist[i]; if (!wB) continue;
    const wF = n - wB; if (!wF) break;
    sumB += i * hist[i];
    const mB = sumB / wB, mF = (sum - sumB) / wF, between = wB * wF * (mB - mF) ** 2;
    if (between > best) { best = between; t = i; }
  }
  return t;
}

/* an area-averaged copy: paperness (from RGBA) or grey, of at most `side` pixels on the long side */
function pfShrink(src, W, H, side, rgba) {
  const k = Math.max(1, Math.ceil(Math.max(W, H) / side)), w = Math.max(1, Math.floor(W / k)), h = Math.max(1, Math.floor(H / k));
  const out = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let s = 0, n = 0;
    for (let yy = y * k; yy < (y + 1) * k; yy++) for (let xx = x * k; xx < (x + 1) * k; xx++) {
      const i = yy * W + xx;
      if (rgba) {
        const r = src[i * 4], g = src[i * 4 + 1], b = src[i * 4 + 2], hi = Math.max(r, g, b), lo = Math.min(r, g, b);
        s += Math.max(0, (r * 299 + g * 587 + b * 114) / 1000 - 1.6 * (hi - lo));    // bright and colourless
      } else s += src[i];
      n++;
    }
    out[y * w + x] = Math.round(s / n);
  }
  return { data: out, w, h, k };
}

/* the brightest value around each cell: paper keeps its own white though writing darkens part of every cell */
function pfMax3(src, w, h) {
  const out = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let m = 0;
    for (let dy = -1; dy <= 1; dy++) { const yy = y + dy; if (yy < 0 || yy >= h) continue; for (let dx = -1; dx <= 1; dx++) { const xx = x + dx; if (xx >= 0 && xx < w && src[yy * w + xx] > m) m = src[yy * w + xx]; } }
    out[y * w + x] = m;
  }
  return out;
}
function pfBlur(src, w, h) {
  const tmp = new Float32Array(w * h), out = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let s = 0, n = 0; for (let d = -2; d <= 2; d++) { const xx = x + d; if (xx >= 0 && xx < w) { s += src[y * w + xx]; n++; } }
    tmp[y * w + x] = s / n;
  }
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let s = 0, n = 0; for (let d = -2; d <= 2; d++) { const yy = y + d; if (yy >= 0 && yy < h) { s += tmp[yy * w + x]; n++; } }
    out[y * w + x] = Math.round(s / n);
  }
  return out;
}

/* a binary mask closed by `r` cells: thin dark lines (a printed frame, ruled lines, writing) no longer split the sheet */
function pfClose(mask, w, h, r) {
  const pass = (src, grow) => {
    const tmp = new Uint8Array(w * h), out = new Uint8Array(w * h);
    for (let y = 0; y < h; y++) { let run = 0; for (let x = -r; x < w; x++) {
      if (x + r < w) run += src[y * w + x + r]; if (x - r - 1 >= 0) run -= src[y * w + x - r - 1];
      if (x >= 0) tmp[y * w + x] = grow ? +(run > 0) : +(run === Math.min(w, x + r + 1) - Math.max(0, x - r)); } }
    for (let x = 0; x < w; x++) { let run = 0; for (let y = -r; y < h; y++) {
      if (y + r < h) run += tmp[(y + r) * w + x]; if (y - r - 1 >= 0) run -= tmp[(y - r - 1) * w + x];
      if (y >= 0) out[y * w + x] = grow ? +(run > 0) : +(run === Math.min(h, y + r + 1) - Math.max(0, y - r)); } }
    return out;
  };
  return pass(pass(mask, true), false);
}
/* connected pieces of a mask, each with its cells and the frame sides it touches */
function pfPieces(mask, w, h, allowed = null) {
  const label = new Int32Array(w * h).fill(-1), stack = new Int32Array(w * h), pieces = [];
  for (let start = 0; start < w * h; start++) {
    if (!mask[start] || label[start] >= 0 || (allowed && !allowed[start])) continue;
    const id = pieces.length, cells = []; let sp = 0, sides = 0; stack[sp++] = start; label[start] = id;
    while (sp) {
      const cur = stack[--sp]; cells.push(cur);
      const y = (cur / w) | 0, x = cur - y * w;
      if (x === 0) sides |= 1; if (x === w - 1) sides |= 2; if (y === 0) sides |= 4; if (y === h - 1) sides |= 8;
      for (const next of [x + 1 < w ? cur + 1 : -1, x > 0 ? cur - 1 : -1, y + 1 < h ? cur + w : -1, y > 0 ? cur - w : -1])
        if (next >= 0 && mask[next] && label[next] < 0 && (!allowed || allowed[next])) { label[next] = id; stack[sp++] = next; }
    }
    pieces.push({ cells, sides: [1, 2, 4, 8].filter(bit => sides & bit).length });
  }
  return pieces;
}
/* how sheet-like a piece is: its four-sided outline, how fully (and not more than fully) the piece fills it, how
   smooth it is inside, how large and central */
function pfSheet(piece, small, w, h) {
  const n = piece.cells.length, frame = w * h;
  if (n < frame * .04 || n > frame * .92 || piece.sides > 2) return null;
  let x0 = w, x1 = 0, y0 = h, y1 = 0, sum = 0, sq = 0;
  const inPiece = new Uint8Array(frame); for (const i of piece.cells) inPiece[i] = 1;
  const edge = [];
  for (const i of piece.cells) {
    const y = (i / w) | 0, x = i - y * w; sum += small[i]; sq += small[i] * small[i];
    if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
    if (x === 0 || y === 0 || x === w - 1 || y === h - 1 || !inPiece[i - 1] || !inPiece[i + 1] || !inPiece[i - w] || !inPiece[i + w]) edge.push({ x: x + .5, y: y + .5 });
  }
  if (Math.min(x1 - x0, y1 - y0) < Math.min(w, h) * .14) return null;                 // a stripe or a sliver
  const four = fourOf(pfHull(edge));
  if (!four) return null;
  const fill = n / Math.max(1, pfArea(four));
  if (fill < .82 || fill > 1.12) return null;                                            // not a filled four-sided shape (a blob of glare is round)
  const cx = (x0 + x1) / 2 / w - .5, cy = (y0 + y1) / 2 / h - .5, mean = sum / n;
  return { four, inPiece, n, mean, spread: Math.sqrt(Math.max(0, sq / n - mean * mean)), sides: piece.sides,
    score: Math.min(1, fill) ** 2 * Math.sqrt(n / frame) * (1 - Math.hypot(cx, cy)) * (piece.sides ? .8 : 1) };
}
/* whether a quad's sides are steps: most of the change across ±10 cells happens within ±3 */
function pfSharp(small, w, h, four) {
  const ring = [four[0], four[1], four[3], four[2]], cx = ring.reduce((s, p) => s + p.x, 0) / 4, cy = ring.reduce((s, p) => s + p.y, 0) / 4, ratios = [];
  const at = (x, y) => small[Math.max(0, Math.min(h - 1, Math.round(y))) * w + Math.max(0, Math.min(w - 1, Math.round(x)))];
  for (let side = 0; side < 4; side++) {
    const a = ring[side], b = ring[(side + 1) % 4], len = Math.hypot(b.x - a.x, b.y - a.y) || 1;
    let nx = -(b.y - a.y) / len, ny = (b.x - a.x) / len;
    if ((cx - a.x) * nx + (cy - a.y) * ny < 0) { nx = -nx; ny = -ny; }
    for (let s = 1; s < 16; s++) {
      const x = a.x + (b.x - a.x) * s / 16, y = a.y + (b.y - a.y) * s / 16;
      const near = at(x + nx * 3, y + ny * 3) - at(x - nx * 3, y - ny * 3), far = at(x + nx * 10, y + ny * 10) - at(x - nx * 10, y - ny * 10);
      if (far > 4) ratios.push(near / far);
    }
  }
  if (ratios.length < 24) return false;
  ratios.sort((p, q) => p - q);
  return ratios[ratios.length >> 1] >= .6;
}
/* cells of a piece within `r` of its outside */
function pfBand(inPiece, w, h, r) {
  const outside = new Uint8Array(w * h); for (let i = 0; i < w * h; i++) outside[i] = inPiece[i] ? 0 : 1;
  const near = pfClose(outside, w, h, 0);                                                // copy
  const grown = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (near[y * w + x])
    for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) { const xx = x + dx, yy = y + dy; if (xx >= 0 && yy >= 0 && xx < w && yy < h) grown[yy * w + xx] = 1; }
  for (let i = 0; i < w * h; i++) grown[i] &= inPiece[i];
  return grown;
}
const pfOtsuOf = (small, keep) => { const v = []; for (let i = 0; i < small.length; i++) if (keep(small[i])) v.push(small[i]); return v.length > 50 ? pfOtsu(v) : null; };
/* the sheet: the most sheet-like piece at any of three thresholds (Otsu, and Otsu again within each side of it), bright
   on a darker surface or, if smooth and not black, grey on a brighter one; then, inside a bright one, a clearly brighter
   sheet-like piece clear of its border (paper lying on a desk) */
function pfRegion(small, w, h) {
  const t = pfOtsu(small), r = Math.max(2, Math.round(Math.min(w, h) / 80)), best = [];
  const thresholds = [t, pfOtsuOf(small, v => v > t), pfOtsuOf(small, v => v <= t)].filter(v => v != null);
  for (const level of thresholds) for (const polarity of [1, -1]) {
    const mask = new Uint8Array(w * h);
    for (let i = 0; i < mask.length; i++) mask[i] = polarity > 0 ? +(small[i] > level) : +(small[i] <= level);
    for (const piece of pfPieces(pfClose(mask, w, h, r), w, h)) {
      const sheet = pfSheet(piece, small, w, h);
      if (!sheet) continue;
      if (polarity < 0) {                                                                  // grey paper on a brighter surface:
        if (sheet.mean < 80 || sheet.spread > 22) continue;                                // ink, diagrams and writing are not paper
        const band = pfBand(sheet.inPiece.map(v => 1 - v), w, h, Math.max(2, r));         // just outside it
        let out = 0, outN = 0; for (let i = 0; i < w * h; i++) if (band[i]) { out += small[i]; outN++; }
        if (!outN || out / outN - sheet.mean < 25) continue;                               // and clearly darker than what is around it
      }
      best.push({ ...sheet, polarity, score: sheet.score * (polarity > 0 ? 1 : .9) });
    }
  }
  if (!best.length) return null;
  best.sort((a, b) => b.score - a.score);
  let chosen = best[0];
  if (chosen.polarity > 0) {
    const band = pfBand(chosen.inPiece, w, h, Math.max(2, r * 2)), values = [];
    for (let i = 0; i < w * h; i++) if (chosen.inPiece[i]) values.push(small[i]);
    /* writing splits off first; the paper/desk split is the second threshold, among the brighter values */
    const levels = [pfOtsu(values)];
    for (let k = 0; k < 2; k++) { const upper = values.filter(v => v > levels.at(-1)); if (upper.length < 50) break; levels.push(pfOtsu(upper)); }
    search: for (const level of levels) {
    const inner = new Uint8Array(w * h);
    for (let i = 0; i < w * h; i++) inner[i] = +(chosen.inPiece[i] && small[i] > level);
    for (const piece of pfPieces(pfClose(inner, w, h, r), w, h, chosen.inPiece)) {
      if (piece.cells.length > chosen.n * .85) continue;
      const sheet = pfSheet(piece, small, w, h);
      if (!sheet) continue;
      let onBand = 0; for (const i of piece.cells) onBand += band[i];
      if (onBand > piece.cells.length * .02) continue;                                     // a brighter half of the same sheet reaches its border
      if (!pfSharp(small, w, h, sheet.four)) continue;                                      // glare fades out; paper ends in a step
      let rest = 0, restN = 0; for (let i = 0; i < w * h; i++) if (chosen.inPiece[i] && !sheet.inPiece[i]) { rest += small[i]; restN++; }
      if (restN && sheet.mean - rest / restN >= 6) { chosen = { ...sheet, polarity: 1 }; break search; }
    }
    }
  }
  return { four: chosen.four, polarity: chosen.polarity };
}

const pfPixel = (g, w, h, x, y) => {
  x = Math.max(0, Math.min(w - 1.001, x)); y = Math.max(0, Math.min(h - 1.001, y));
  const ix = x | 0, iy = y | 0, fx = x - ix, fy = y - iy, j = iy * w + ix;
  return (g[j] * (1 - fx) + g[j + 1] * fx) * (1 - fy) + (g[j + w] * (1 - fx) + g[j + w + 1] * fx) * fy;
};

/* a line n·p = r through points, least squares on the normal direction, outliers dropped twice */
function lineThrough(pts, nx, ny) {
  const mx = pts.reduce((s, p) => s + p.x, 0) / pts.length, my = pts.reduce((s, p) => s + p.y, 0) / pts.length;
  let sxx = 0, sxy = 0, syy = 0;
  for (const p of pts) { const dx = p.x - mx, dy = p.y - my; sxx += dx * dx; sxy += dx * dy; syy += dy * dy; }
  const angle = .5 * Math.atan2(2 * sxy, sxx - syy);
  let lnx = -Math.sin(angle), lny = Math.cos(angle);
  if (lnx * nx + lny * ny < 0) { lnx = -lnx; lny = -lny; }
  return { nx: lnx, ny: lny, r: lnx * mx + lny * my, n: pts.length };
}
function fitLine(points, nx, ny) {
  let line = lineThrough(points, nx, ny), pts = points;
  for (let round = 0; round < 2; round++) {
    const res = pts.map(p => Math.abs(line.nx * p.x + line.ny * p.y - line.r)), sorted = [...res].sort((a, b) => a - b);
    const kept = pts.filter((_, i) => res[i] <= Math.max(1.5, 2.5 * sorted[sorted.length >> 1]));
    if (kept.length < 6) break;
    pts = kept; line = lineThrough(pts, nx, ny);
  }
  return line;
}

const pfMeet = (a, b) => {
  const det = a.nx * b.ny - a.ny * b.nx;
  return Math.abs(det) < .15 ? null : { x: (a.r * b.ny - a.ny * b.r) / det, y: (a.nx * b.r - a.r * b.nx) / det };
};

/* each side of a coarse quad moved onto the measured edge */
function pfRefine(gray, w, h, quad, polarity = 1) {
  const ring = [quad[0], quad[1], quad[3], quad[2]], cx = ring.reduce((s, p) => s + p.x, 0) / 4, cy = ring.reduce((s, p) => s + p.y, 0) / 4;
  const border = Math.max(2, Math.max(w, h) * .006), search = Math.max(6, Math.max(w, h) * .035), lines = [], support = [], onFrame = [];
  /* the paper's own level: the median over a grid inside the quad (writing is a small share of it) */
  const grid = [];
  for (let u = .15; u < .9; u += .1) for (let v = .15; v < .9; v += .1)
    grid.push(pfPixel(gray, w, h, (quad[0].x * (1 - u) + quad[1].x * u) * (1 - v) + (quad[2].x * (1 - u) + quad[3].x * u) * v,
      (quad[0].y * (1 - u) + quad[1].y * u) * (1 - v) + (quad[2].y * (1 - u) + quad[3].y * u) * v));
  grid.sort((p, q) => p - q);
  const level = grid[grid.length >> 1], tolerance = Math.max(18, level * .15);
  for (let side = 0; side < 4; side++) {
    const a = ring[side], b = ring[(side + 1) % 4], len = Math.hypot(b.x - a.x, b.y - a.y) || 1;
    let nx = -(b.y - a.y) / len, ny = (b.x - a.x) / len;
    if ((cx - a.x) * nx + (cy - a.y) * ny < 0) { nx = -nx; ny = -ny; }                 // n points into the sheet
    const along = (p, q) => (Math.abs(p.x - q.x) < border * 2 && (p.x < border || p.x > w - 1 - border)) || (Math.abs(p.y - q.y) < border * 2 && (p.y < border || p.y > h - 1 - border));
    if (along(a, b)) { lines.push({ nx, ny, r: nx * a.x + ny * a.y }); support.push(1); onFrame.push(true); continue; }
    const found = [];
    for (let s = 0; s < SAMPLES; s++) {
      const t = .08 + .84 * (s + .5) / SAMPLES, x = a.x + (b.x - a.x) * t, y = a.y + (b.y - a.y) * t;
      /* the sheet's edge is the outermost strong step: ruled lines and answer boxes inside it step the same way */
      const steps = [];
      for (let o = -search; o <= search; o += .5) {
        const px = x + nx * o, py = y + ny * o;
        steps.push(px < 1 || py < 1 || px > w - 2 || py > h - 2 ? 0 : polarity * (pfPixel(gray, w, h, px + nx * 2, py + ny * 2) - pfPixel(gray, w, h, px - nx * 2, py - ny * 2)));
      }
      /* from outside (o = -search) inwards, the first step that leads onto the paper itself: a seam in the floor leads
         onto more floor, a printed line inside the sheet is preceded by the sheet's real edge */
      let at = -1;
      for (let i = 0; i < steps.length; i++) {
        if (steps[i] < 8) continue;
        const o = -search + i * .5, inside = pfPixel(gray, w, h, x + nx * (o + 4), y + ny * (o + 4));
        if (Math.abs(inside - level) <= tolerance) { at = i; break; }
      }
      if (at < 0) continue;
      while (at + 1 < steps.length && steps[at + 1] >= steps[at]) at++;               // up to that step's peak
      const o = -search + at * .5;
      found.push({ x: x + nx * o, y: y + ny * o });
    }
    const line = found.length >= SAMPLES * .3 ? fitLine(found, nx, ny) : null;
    lines.push(line || { nx, ny, r: nx * a.x + ny * a.y });
    support.push(line ? line.n / SAMPLES : 0); onFrame.push(false);
  }
  const met = [pfMeet(lines[3], lines[0]), pfMeet(lines[0], lines[1]), pfMeet(lines[1], lines[2]), pfMeet(lines[2], lines[3])];   // tl, tr, br, bl
  if (met.some(p => !p || p.x < -w * .02 || p.y < -h * .02 || p.x > w * 1.02 || p.y > h * 1.02)) return { corners: quad, support, onFrame, refined: false };
  const clip = p => ({ x: Math.max(0, Math.min(w - 1, p.x)), y: Math.max(0, Math.min(h - 1, p.y)) });
  return { corners: [clip(met[0]), clip(met[1]), clip(met[3]), clip(met[2])], support, onFrame, refined: true };
}

const pfArea = q => Math.abs(pfCross(q[0], q[1], q[3]) + pfCross(q[0], q[3], q[2])) / 2;

/**
 * The sheet in a photo.
 * @param {Uint8Array|Uint8ClampedArray} gray  luminance, W×H
 * @param {Uint8ClampedArray} [rgba]           the same photo's RGBA, to tell colourless paper from coloured surfaces
 * @returns {{corners, score, method:'page', verified, edgeSupport, weakestEdge, sidesOnFrame}|{corners:null}}
 */
export function findPage(gray, W, H, rgba = null) {
  const coarse = pfShrink(rgba || gray, W, H, COARSE, !!rgba), small = pfMax3(pfBlur(coarse.data, coarse.w, coarse.h), coarse.w, coarse.h);
  const found = pfRegion(small, coarse.w, coarse.h);
  if (!found) return { corners: null, score: 0, method: 'page', verified: false };
  const { w, h } = coarse, four = found.four;
  /* the fine copy, where the edges are fitted */
  const fine = pfShrink(rgba || gray, W, H, FINE, !!rgba), fs = coarse.k / fine.k;
  const snap = p => ({ x: p.x < 1 ? 0 : p.x > w - 1 ? fine.w - 1 : p.x * fs, y: p.y < 1 ? 0 : p.y > h - 1 ? fine.h - 1 : p.y * fs });
  const r = pfRefine(fine.data, fine.w, fine.h, four.map(snap), found.polarity);
  const corners = r.corners.map(p => ({ x: (p.x + .5) * fine.k, y: (p.y + .5) * fine.k }));
  const inner = r.support.filter((_, i) => !r.onFrame[i]), cover = pfArea(corners) / (W * H);
  const edgeSupport = inner.length ? inner.reduce((a, b) => a + b, 0) / inner.length : 1, weakestEdge = inner.length ? Math.min(...inner) : 1;
  const edgeOfPhoto = Math.max(2, Math.min(W, H) * .008), onBorder = corners.some(p => p.x < edgeOfPhoto || p.y < edgeOfPhoto || p.x > W - 1 - edgeOfPhoto || p.y > H - 1 - edgeOfPhoto);
  const sidesOnFrame = r.onFrame.filter(Boolean).length + (onBorder && !r.onFrame.some(Boolean) ? 1 : 0);
  /* a sheet running out of the photo is cropped to what is visible, but never counts as verified */
  const verified = r.refined && cover >= .06 && weakestEdge >= .45 && sidesOnFrame === 0;
  const score = Math.min(1, .35 + .45 * edgeSupport + .2 * Math.min(1, cover / .3));
  return { corners, score, method: 'page', verified, edgeSupport, weakestEdge, sidesOnFrame, cover };
}

/** Projected A-series shape candidate, never a physical size measurement.
 * A3/A4/A5 share a ratio, and an unknown camera pose can make another rectangle
 * look identical. Keep perspective-ambiguous corners for manual confirmation.
 * The 5% near-frontal tolerance excludes Letter, cards, screens and squares
 * without rejecting ordinary corner-fit error or in-plane page rotation. */
export function assessA4Candidate(corners, W, H) {
  const uncertain = { status: 'perspective_uncertain', projectedRatio: null, aspectError: null,
    angleError: null, parallelError: null, oppositeBalance: null, skewQuality: 0 };
  if (!Array.isArray(corners) || corners.length !== 4 || !Number.isFinite(W) || !Number.isFinite(H) || !(W > 0 && H > 0) ||
      corners.some(p => !p || !Number.isFinite(p.x) || !Number.isFinite(p.y))) return uncertain;
  const q = orderCorners(corners), poly = [q[0], q[1], q[3], q[2]];
  if (quadScore(q, W, H) <= 0 || q.some(p => p.x < 0 || p.y < 0 || p.x > W || p.y > H)) return uncertain;
  const edges = poly.map((p, i) => ({ x: poly[(i + 1) % 4].x - p.x, y: poly[(i + 1) % 4].y - p.y }));
  const lengths = edges.map(p => Math.hypot(p.x, p.y));
  if (Math.min(...lengths) < 8) return uncertain;
  const dot = (a, b) => Math.abs(edges[a].x * edges[b].x + edges[a].y * edges[b].y) / (lengths[a] * lengths[b]);
  const cross = (a, b) => Math.abs(edges[a].x * edges[b].y - edges[a].y * edges[b].x) / (lengths[a] * lengths[b]);
  const angleError = Math.max(...edges.map((_, i) => dot(i, (i + 1) % 4)));
  const parallelError = Math.max(cross(0, 2), cross(1, 3));
  const oppositeBalance = Math.min(Math.min(lengths[0], lengths[2]) / Math.max(lengths[0], lengths[2]),
    Math.min(lengths[1], lengths[3]) / Math.max(lengths[1], lengths[3]));
  const horizontal = (lengths[0] + lengths[2]) / 2, vertical = (lengths[1] + lengths[3]) / 2;
  const projectedRatio = Math.max(horizontal, vertical) / Math.min(horizontal, vertical), aspectError = Math.abs(projectedRatio / A4_RATIO - 1);
  const skewQuality = Math.max(0, 1 - Math.max(angleError, parallelError, 1 - oppositeBalance));
  const nearFrontal = angleError <= .15 && parallelError <= .12 && oppositeBalance >= .88;
  return { status: !nearFrontal ? 'perspective_uncertain' : aspectError <= .05 ? 'a4_candidate' : 'aspect_mismatch',
    projectedRatio, aspectError, angleError, parallelError, oppositeBalance, skewQuality };
}
function assessedDocument(result, W, H) {
  const paperAssessment = assessA4Candidate(result.corners, W, H);
  return { ...result, paperStatus: paperAssessment.status, paperAssessment,
    autoCaptureEligible: result.autoCaptureEligible === true && paperAssessment.status === 'a4_candidate' };
}
/** The width/height ratio of the rectangle a quad is the picture of, with the perspective undone
 * (Zhang & He, "Whiteboard scanning and image enhancement", 2007: the focal length and the aspect ratio follow from
 * the quad's two vanishing points, square pixels and the principal point at the image centre). With fewer than two
 * vanishing points (straight on, or tilted about one axis only) the focal length is unknown; `focal` then says what
 * to assume, and a typical phone camera's (a 26 mm equivalent lens, about 0.6 of the image diagonal) is the default.
 * Returns the long/short ratio and whether the focal length was measured. */
function rectify(corners, W, H, focal) {
  if (!Array.isArray(corners) || corners.length !== 4 || corners.some(p => !p || !Number.isFinite(p.x + p.y))) return null;
  const q = orderCorners(corners), u0 = W / 2, v0 = H / 2, diag = Math.hypot(W, H);
  const [m1, m2, m3, m4] = q.map(p => [p.x - u0, p.y - v0, 1]);
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const d2 = dot(cross(m2, m4), m3), d3 = dot(cross(m3, m4), m2);
  if (Math.abs(d2) < 1e-9 || Math.abs(d3) < 1e-9) return null;
  const k2 = dot(cross(m1, m4), m3) / d2, k3 = dot(cross(m1, m4), m2) / d3;
  const n2 = m2.map((v, i) => k2 * v - m1[i]), n3 = m3.map((v, i) => k3 * v - m1[i]);
  /* each vanishing direction makes n's third component non-zero; f follows only when both are */
  let f = null; const tiny = 1e-3 * Math.hypot(n2[0], n2[1]) * 1e-3 * Math.hypot(n3[0], n3[1]);
  if (Math.abs(n2[2] * n3[2]) > tiny / (diag * diag)) { const f2 = -(n2[0] * n3[0] + n2[1] * n3[1]) / (n2[2] * n3[2]); if (f2 > 0) f = Math.sqrt(f2); }
  const measured = f >= diag * .25 && f <= diag * 4;
  if (!measured) f = (focal || .6) * diag;
  const len = n => Math.sqrt((n[0] * n[0] + n[1] * n[1]) / (f * f) + n[2] * n[2]);
  const a = len(n2), b = len(n3);
  return a > 0 && b > 0 ? { ratio: Math.max(a, b) / Math.min(a, b), measured } : null;
}
export function rectifiedRatio(corners, W, H) { const r = rectify(corners, W, H); return r ? r.ratio : null; }
/** How far the quad is from A4 once the perspective is undone. Where the focal length cannot be measured, the
 * closest ratio over the focal lengths of phone main cameras (24–35 mm equivalent, 0.5–0.8 of the diagonal) counts. */
export function a4RatioMiss(corners, W, H) {
  const first = rectify(corners, W, H);
  if (!first) return Infinity;
  const miss = r => Math.abs(r / A4_RATIO - 1);
  if (first.measured) return miss(first.ratio);
  let best = Infinity;
  for (let focal = .5; focal <= .801; focal += .05) { const r = rectify(corners, W, H, focal); if (r) best = Math.min(best, miss(r.ratio)); }
  return best;
}
const a4Miss = a4RatioMiss;
/** v2 page finder on a grey image, with the photo's RGBA when there is one (paper is colourless, wood and desks are not) */
export function findPageQuadGray(gray, W, H, rgba = null) {
  const none = { corners: null, score: 0, method: 'page', edgeSupport: 0, clipped: false, autoCaptureEligible: false, paperStatus: 'not_found', paperAssessment: null };
  if (W < 32 || H < 32 || gray.length < W * H) return none;
  const found = findPage(gray, W, H, rgba && rgba.length >= W * H * 4 ? rgba : null);
  if (!found.corners) return none;
  const corners = orderCorners(found.corners);
  /* the A-series shape is reported, but a sheet seen at an angle is still a sheet: automatic capture asks for four
     strongly measured edges and a sheet that fills a fair part of the frame, not a front-on view */
  const paperAssessment = assessA4Candidate(corners, W, H);
  return { corners, score: found.score, method: 'page', edgeSupport: found.edgeSupport, weakestEdge: found.weakestEdge,
    verified: found.verified, clipped: found.sidesOnFrame > 0, cover: found.cover, paperStatus: paperAssessment.status, paperAssessment,
    autoCaptureEligible: found.verified && found.weakestEdge >= .7 && found.edgeSupport >= .8 && found.cover >= .12 &&
      (paperAssessment.status === 'a4_candidate' || paperAssessment.status === 'perspective_uncertain' && a4RatioMiss(corners, W, H) < .07) };   // Letter misses A4 by .085
}

/* ---------- 원근 보정 ---------- */

/** 네 점 대응에서 3×3 사영변환 행렬 (가우스 소거) */
export function solveHomography(src, dst) {
  const M = [];
  for (let i = 0; i < 4; i++) {
    const { x, y } = src[i];
    const { x: u, y: v } = dst[i];
    M.push([x, y, 1, 0, 0, 0, -u * x, -u * y, u]);
    M.push([0, 0, 0, x, y, 1, -v * x, -v * y, v]);
  }
  for (let i = 0; i < 8; i++) {
    let p = i;
    for (let j = i + 1; j < 8; j++) if (Math.abs(M[j][i]) > Math.abs(M[p][i])) p = j;
    [M[i], M[p]] = [M[p], M[i]];
    if (Math.abs(M[i][i]) < 1e-10) return null;
    for (let j = i + 1; j < 8; j++) {
      const f = M[j][i] / M[i][i];
      for (let k = i; k <= 8; k++) M[j][k] -= f * M[i][k];
    }
  }
  const hh = new Array(8);
  for (let i = 7; i >= 0; i--) {
    let s = M[i][8];
    for (let j = i + 1; j < 8; j++) s -= M[i][j] * hh[j];
    hh[i] = s / M[i][i];
  }
  return [hh[0], hh[1], hh[2], hh[3], hh[4], hh[5], hh[6], hh[7], 1];
}

/**
 * 원근 보정 + 겹샘플링.
 *
 * v1 은 가장 가까운 픽셀 하나를 집어왔습니다(nearest). 사진을 줄이면서
 * 그러면 획이 끊기고 계단이 집니다 — OCR 정확도에 직결됩니다.
 * 여기서는 출력 픽셀 하나마다 ss×ss 개의 위치를 **이중선형**으로 읽어
 * 평균냅니다. 축소 배율이 클 때만 ss 를 올려 속도를 아낍니다.
 *
 * @param {Uint8ClampedArray} src RGBA
 * @returns {{data:Uint8ClampedArray, width:number, height:number}}
 */
export function warpPixels(src, sw, sh, corners, outW, outH, dstQuad = null) {
  const dst = dstQuad || [
    { x: 0, y: 0 }, { x: outW, y: 0 },
    { x: 0, y: outH }, { x: outW, y: outH },
  ];
  const Hm = solveHomography(dst, corners); // 목적지 → 원본
  const out = new Uint8ClampedArray(outW * outH * 4);
  if (!Hm) return { data: out, width: outW, height: outH };

  /* 원본에서 출력 한 칸이 차지하는 크기로 겹샘플 수를 정합니다 */
  const srcSpan = Math.hypot(corners[1].x - corners[0].x, corners[1].y - corners[0].y);
  const ratio = srcSpan / outW;
  const ss = ratio > 2.2 ? 3 : ratio > 1.25 ? 2 : 1;
  const inv = 1 / (ss * ss);
  const off = [];
  for (let j = 0; j < ss; j++) for (let i = 0; i < ss; i++) off.push([(i + 0.5) / ss, (j + 0.5) / ss]);

  for (let y = 0; y < outH; y++) {
    for (let x = 0; x < outW; x++) {
      let r = 0, g = 0, b = 0, hit = 0;
      for (let k = 0; k < off.length; k++) {
        const ox = x + off[k][0], oy = y + off[k][1];
        const w = Hm[6] * ox + Hm[7] * oy + Hm[8];
        if (!w) continue;
        const fx = (Hm[0] * ox + Hm[1] * oy + Hm[2]) / w;
        const fy = (Hm[3] * ox + Hm[4] * oy + Hm[5]) / w;
        if (fx < 0 || fy < 0 || fx > sw - 1 || fy > sh - 1) continue;

        /* 이중선형 */
        const x0 = fx | 0, y0 = fy | 0;
        const x1 = x0 + 1 < sw ? x0 + 1 : x0;
        const y1 = y0 + 1 < sh ? y0 + 1 : y0;
        const ax = fx - x0, ay = fy - y0;
        const i00 = (y0 * sw + x0) * 4, i10 = (y0 * sw + x1) * 4;
        const i01 = (y1 * sw + x0) * 4, i11 = (y1 * sw + x1) * 4;
        const w00 = (1 - ax) * (1 - ay), w10 = ax * (1 - ay);
        const w01 = (1 - ax) * ay, w11 = ax * ay;
        r += src[i00] * w00 + src[i10] * w10 + src[i01] * w01 + src[i11] * w11;
        g += src[i00 + 1] * w00 + src[i10 + 1] * w10 + src[i01 + 1] * w01 + src[i11 + 1] * w11;
        b += src[i00 + 2] * w00 + src[i10 + 2] * w10 + src[i01 + 2] * w01 + src[i11 + 2] * w11;
        hit++;
      }
      const o = (y * outW + x) * 4;
      if (hit) {
        const k = hit === off.length ? inv : 1 / hit;
        out[o] = r * k; out[o + 1] = g * k; out[o + 2] = b * k;
      } else {
        out[o] = out[o + 1] = out[o + 2] = 255; // 틀 밖은 흰 종이로
      }
      out[o + 3] = 255;
    }
  }
  return { data: out, width: outW, height: outH };
}

/* ---------- 보정 필터 ---------- */

/**
 * 'clean' — 그림자를 걷어내고 대비를 세웁니다. 색은 살립니다.
 *   창가에서 찍어 한쪽만 어두운 사진도 고르게 펴집니다.
 *   파란 볼펜 답안과 빨간 첨삭이 구분되어야 하므로 색을 버리지 않습니다.
 *
 * 'mono' — 사우볼라(Sauvola) 국소 이진화.
 *   단순히 밝기로 자르면 연필처럼 흐린 획이 통째로 날아갑니다.
 *   사우볼라는 창 안의 **표준편차**를 함께 봅니다. 아무것도 없는
 *   여백(편차 작음)에서는 기준을 올려 잡티를 지우고, 획이 지나가는
 *   자리(편차 큼)에서는 기준을 낮춰 흐린 획도 살립니다.
 *     T(x,y) = m(x,y) · [1 + k · (s(x,y)/R − 1)]
 *
 * 'original' — 손대지 않음.
 */
/**
 * 국소 통계 지도.
 *
 * 배경 밝기와 국소 편차는 아주 천천히 변합니다. 그래서 원본 해상도로
 * 계산할 이유가 없습니다. ds 배로 줄여서 구한 뒤 필요할 때 이중선형으로
 * 읽으면 결과는 사실상 같고 계산은 ds² 배 빨라집니다.
 * A4 200dpi 에서 이 한 줄이 이진화를 4배 빠르게 만듭니다.
 *
 * @param {boolean} withSquare 제곱평균도 함께 (사우볼라용)
 */
export function localStats(gray, W, H, r, ds = 1, withSquare = false) {
  const w = Math.max(2, Math.ceil(W / ds));
  const h = Math.max(2, Math.ceil(H / ds));

  const small = new Float32Array(w * h);
  const smallSq = withSquare ? new Float32Array(w * h) : null;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      let s = 0, s2 = 0, n = 0;
      for (let j = 0; j < ds; j++) {
        const sy = y * ds + j;
        if (sy >= H) break;
        const row = sy * W;
        for (let i = 0; i < ds; i++) {
          const sx = x * ds + i;
          if (sx >= W) break;
          const v = gray[row + sx];
          s += v; if (withSquare) s2 += v * v;
          n++;
        }
      }
      if (!n) n = 1;
      small[y * w + x] = s / n;
      if (withSquare) smallSq[y * w + x] = s2 / n;
    }
  }

  const rr = Math.max(1, Math.round(r / ds));
  const mean = boxMean(small, w, h, rr);
  const meanSq = withSquare ? boxMean(smallSq, w, h, rr) : null;

  /* 이중선형 읽기 */
  const sample = (map) => (x, y) => {
    const fx = Math.min(w - 1.001, Math.max(0, (x + 0.5) / ds - 0.5));
    const fy = Math.min(h - 1.001, Math.max(0, (y + 0.5) / ds - 0.5));
    const x0 = fx | 0, y0 = fy | 0, x1 = x0 + 1, y1 = y0 + 1;
    const ax = fx - x0, ay = fy - y0;
    return (
      map[y0 * w + x0] * (1 - ax) * (1 - ay) +
      map[y0 * w + x1] * ax * (1 - ay) +
      map[y1 * w + x0] * (1 - ax) * ay +
      map[y1 * w + x1] * ax * ay
    );
  };

  return { mean: sample(mean), meanSq: meanSq ? sample(meanSq) : null, w, h };
}

export function enhancePixels(data, W, H, mode = 'clean') {
  if (mode === 'original') return data;

  const gray = toGray(data, W, H);
  /* 창 반지름: 글자보다 확실히 크고 페이지보다는 작게 */
  const r = Math.max(7, Math.round(Math.min(W, H) / 22));
  /* 큰 사진일수록 통계를 더 줄여 구합니다 */
  const px = W * H;
  const ds = px > 3.2e6 ? 4 : px > 1.1e6 ? 3 : px > 3e5 ? 2 : 1;

  const out = new Uint8ClampedArray(W * H * 4);

  // Document colour mode corrects uneven illumination without the clean mode's
  // hard paper/ink threshold. Faint grid lines and coloured directional marks
  // remain distinct; all channels use the same local lighting correction.
  if (mode === 'color') {
    const st = localStats(gray, W, H, r, ds, false);
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const o = (y * W + x) * 4, gain = 255 / Math.max(70, st.mean(x, y));
      for (let c = 0; c < 3; c++) out[o + c] = Math.max(0, Math.min(255, Math.round((data[o + c] * gain - 8) * 255 / 247)));
      out[o + 3] = 255;
    }
    return out;
  }

  if (mode === 'mono') {
    const st = localStats(gray, W, H, r, ds, true);
    const k = 0.18, R = 96; // R = 밝기 편차의 최대 기대치
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const i = y * W + x, o = i * 4;
        const m = st.mean(x, y);
        const s = Math.sqrt(Math.max(0, st.meanSq(x, y) - m * m));
        const T = m * (1 + k * (s / R - 1));
        const v = gray[i] <= T ? 0 : 255;
        out[o] = out[o + 1] = out[o + 2] = v;
        out[o + 3] = 255;
      }
    }
    return out;
  }

  /* clean — 배경 밝기로 나눠 그림자를 지우고, 부드러운 S 곡선으로 대비 */
  const st = localStats(gray, W, H, r, ds, false);
  const LO = 0.72, HI = 0.99;
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const o = (y * W + x) * 4;
      const bg = Math.max(st.mean(x, y), 1);
      for (let c = 0; c < 3; c++) {
        let t = (data[o + c] / bg - LO) / (HI - LO);
        t = t < 0 ? 0 : t > 1 ? 1 : t;
        t = t * t * (3 - 2 * t);          // smoothstep — 계조가 뚝 끊기지 않게
        out[o + c] = Math.round(t * 255);
      }
      out[o + 3] = 255;
    }
  }
  return out;
}

/* ---------- 품질 점검 ---------- */

/**
 * 흔들림(초점)과 반사광을 재서 "다시 찍으세요"를 말해줍니다.
 * 흐린 사진을 그대로 올려 채점이 어긋나는 게 제일 나쁩니다.
 *
 * focus  라플라시안 분산. 클수록 또렷합니다.
 * glare  거의 흰 픽셀의 비율. 형광등이 종이에 비치면 올라갑니다.
 */
export function inspectPixels(data, W, H) {
  const gray = toGray(data, W, H);
  const step = Math.max(1, Math.round(Math.min(W, H) / 700));

  let sum = 0, sum2 = 0, n = 0, blown = 0, total = 0;
  for (let y = step; y < H - step; y += step) {
    for (let x = step; x < W - step; x += step) {
      const p = y * W + x;
      const lap =
        4 * gray[p] - gray[p - 1] - gray[p + 1] - gray[p - W] - gray[p + W];
      sum += lap; sum2 += lap * lap; n++;
      total++;
      if (gray[p] > 249) blown++;
    }
  }
  const focus = n ? sum2 / n - (sum / n) * (sum / n) : 0;
  const glare = total ? blown / total : 0;

  let hint = null;
  if (focus < 22) hint = '사진이 흔들렸습니다. 종이에 손을 대고 다시 찍어 주세요.';
  else if (glare > 0.3) hint = '형광등 반사가 심합니다. 조명을 등지지 말고 옆에서 찍어 주세요.';

  return { focus: Math.round(focus), glare: Math.round(glare * 100) / 100, ok: !hint, hint };
}

/* ==================================================================
   2. 브라우저 껍데기  (여기서만 캔버스를 씁니다)
   ================================================================== */

export function canProcess() {
  try {
    return (
      typeof document !== 'undefined' &&
      typeof URL?.createObjectURL === 'function' &&
      !!document.createElement('canvas').getContext?.('2d')
    );
  } catch { return false; }
}

export function loadImage(src) {
  return new Promise((res, rej) => {
    const i = new Image();
    i.onload = () => res(i);
    i.onerror = rej;
    i.src = src;
  });
}

/**
 * 파일을 비트맵으로 읽습니다.
 * createImageBitmap 에 imageOrientation:'from-image' 를 주면 EXIF 회전이
 * 반영됩니다. 이게 없으면 아이폰 세로 사진이 눕는 고질병이 생깁니다.
 */
export async function loadBitmap(file) {
  if (typeof createImageBitmap === 'function') {
    try {
      return await createImageBitmap(file, { imageOrientation: 'from-image' });
    } catch { /* 구형 브라우저는 아래로 */ }
  }
  const url = URL.createObjectURL(file);
  try { return await loadImage(url); }
  finally { setTimeout(() => URL.revokeObjectURL(url), 0); }
}

export function toCanvas(source, maxSide = WORK_MAX_SIDE) {
  const sw = source.width, sh = source.height;
  const scale = Math.min(1, maxSide / Math.max(sw, sh));
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.round(sw * scale));
  c.height = Math.max(1, Math.round(sh * scale));
  c.getContext('2d', { willReadFrequently: true }).drawImage(source, 0, 0, c.width, c.height);
  return c;
}

const imgData = (canvas) =>
  canvas.getContext('2d', { willReadFrequently: true })
    .getImageData(0, 0, canvas.width, canvas.height);

const fromPixels = (data, W, H) => {
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  c.getContext('2d').putImageData(new ImageData(data, W, H), 0, 0);
  return c;
};

/** v1 호환 — 캔버스를 받아 마커를 찾습니다. LiveCamera 가 이걸 씁니다. */
export function findMarkers(canvas) {
  const img = imgData(canvas);
  const g = toGray(img.data, canvas.width, canvas.height);
  return findMarkersGray(g, canvas.width, canvas.height);
}

/** Shared by live camera and full-resolution capture. Partial dark blobs never
 * acquire marker insets, and automatic capture requires measured edge evidence. */
export function detectDocumentQuadGray(g, W, H, rgba = null) {
  const marker = findSheetMarkersGray(g, W, H);
  if (marker && marker.score >= .75) return assessedDocument({ ...marker, clipped: false, autoCaptureEligible: true }, W, H);
  const page = findPageQuadGray(g, W, H, rgba);
  if (page.corners) return page;
  if (marker && marker.score >= .5) return assessedDocument({ ...marker, clipped: false, autoCaptureEligible: false }, W, H);
  const legacy = findMarkersGray(g, W, H);
  if (legacy.found === 4 && legacy.score >= .82) return assessedDocument({ ...legacy, clipped: false, autoCaptureEligible: false }, W, H);
  return {
    corners: [
      { x: W * 0.05, y: H * 0.05 }, { x: W * 0.95, y: H * 0.05 },
      { x: W * 0.05, y: H * 0.95 }, { x: W * 0.95, y: H * 0.95 },
    ],
    score: 0,
    method: 'frame',
    paperStatus: 'not_found',
    paperAssessment: null,
    autoCaptureEligible: false,
    clipped: false,
  };
}

export function detectQuad(canvas) {
  const img = imgData(canvas), W = canvas.width, H = canvas.height;
  return detectDocumentQuadGray(toGray(img.data, W, H), W, H, img.data);
}

/** The page in a canvas, found in the scanner's worker (or here, where there is no worker). Entirely on-device:
 * no model, no request. A quad whose edges were not measured is still offered (cropped, for a check), but only a
 * verified one may be used for automatic capture or for reusing a live frame. */
export async function detectDocumentQuad(canvas, options = {}) {
  if (typeof Worker !== 'undefined' && typeof createImageBitmap === 'function') {
    try {
      const { getDocumentDetector } = await import(new URL('./document-detector.mjs?v=8e31e6b73e0b', import.meta.url));
      return await getDocumentDetector().detect(canvas, options);
    } catch (error) { if (error?.name === 'AbortError') throw error; }
  }
  const found = detectQuad(canvas), usable = !!found.corners && found.method !== 'frame';
  const verified = usable && (found.method === 'marker' || found.verified === true);
  return { ...found, engine: 'main-thread', scanEligible: usable, verified, autoCaptureEligible: verified && found.autoCaptureEligible === true,
    paperStatus: usable ? found.paperStatus || 'document' : 'not_found' };
}

/* corners on a copy of at most DETECT_MAX_SIDE, returned in the canvas's own coordinates */
export async function detectOnProbe(canvas, options = {}) {
  const probe = Math.max(canvas.width, canvas.height) > DETECT_MAX_SIDE ? toCanvas(canvas, DETECT_MAX_SIDE) : canvas;
  const d = await detectDocumentQuad(probe, options);
  if (probe === canvas || !d?.corners) return d;
  const sx = canvas.width / probe.width, sy = canvas.height / probe.height;
  return { ...d, corners: d.corners.map(p => ({ x: p.x * sx, y: p.y * sy })) };
}

export async function warmDocumentDetector(options) {
  if (typeof Worker === 'undefined') return false;
  try { const { getDocumentDetector } = await import(new URL('./document-detector.mjs?v=8e31e6b73e0b', import.meta.url)); await getDocumentDetector().warm(options); return true; }
  catch { return false; }
}

async function renderInWorker(base, corners, mode, dpi, inset, pageFormat, signal, includeBaseline = false) {
  if (typeof Worker === 'undefined' || typeof createImageBitmap !== 'function') return null;
  try {
    const { getDocumentDetector } = await import(new URL('./document-detector.mjs?v=8e31e6b73e0b', import.meta.url));
    return await getDocumentDetector().render(base, { corners, mode, outW: dpiToWidth(dpi), inset, pageFormat, includeBaseline }, { signal });
  } catch (error) { if (error?.name === 'AbortError') throw error; return null; }
}

/** Auto preserves the observed document aspect; only an explicit A4 choice
 * applies the A-series ratio. Neither a quadrilateral nor an ML model measures
 * physical sheet size. The output short side targets the existing 200dpi size. */
export function documentOutputSize(corners, outW = dpiToWidth(DEFAULT_DPI), pageFormat = 'auto', inset = null) {
  const pts = orderCorners(corners), length = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
  const horizontal = Math.max(length(pts[0], pts[1]), length(pts[2], pts[3]));
  const vertical = Math.max(length(pts[0], pts[2]), length(pts[1], pts[3]));
  const landscape = horizontal > vertical * 1.12;
  const measured = vertical / horizontal * (inset ? (inset.right - inset.left) / (inset.bottom - inset.top) : 1);
  const ratio = pageFormat === 'a4' ? (landscape ? 1 / A4_RATIO : A4_RATIO) : Math.max(.2, Math.min(5, measured));
  let width = ratio >= 1 ? outW : outW / ratio, height = width * ratio;
  const cap = Math.min(1, 3200 / Math.max(width, height));
  return { width: Math.max(2, Math.round(width * cap)), height: Math.max(2, Math.round(height * cap)) };
}

/**
 * 캔버스를 A4 직사각형으로 폅니다.
 *
 * @param {*} inset 마커가 A4 지면 안에서 차지하는 위치(0~1).
 *   마커는 종이 가장자리가 아니라 안쪽에 인쇄됩니다. 마커 네 점을
 *   그대로 출력 네 귀퉁이에 맞추면 종이 여백이 잘려나가고, 비율도
 *   1.414 가 아니라 1.43 쯤으로 미묘하게 늘어납니다. 마커가 놓인
 *   자리를 알려주면 지면 전체를 정확한 A4 로 복원합니다.
 *   종이 테두리로 찾은 경우에는 null 을 주세요.
 */
export function warp(canvas, corners, outW = dpiToWidth(DEFAULT_DPI), inset = null, options = {}) {
  const pts = orderCorners(corners);
  const { width: w, height: h } = documentOutputSize(pts, outW, options.pageFormat || 'a4', inset);

  let dstQuad = null;
  if (inset) {
    dstQuad = [
      { x: inset.left * w, y: inset.top * h },
      { x: inset.right * w, y: inset.top * h },
      { x: inset.left * w, y: inset.bottom * h },
      { x: inset.right * w, y: inset.bottom * h },
    ];
  }

  const img = imgData(canvas);
  const r = warpPixels(img.data, canvas.width, canvas.height, pts, w, h, dstQuad);
  return fromPixels(r.data, w, h);
}

export function enhance(canvas, mode = 'clean') {
  if (mode === 'original') return canvas;
  const img = imgData(canvas);
  const out = enhancePixels(img.data, canvas.width, canvas.height, mode);
  return fromPixels(out, canvas.width, canvas.height);
}

export function inspect(canvas) {
  const img = imgData(canvas);
  return inspectPixels(img.data, canvas.width, canvas.height);
}

/** White paper is expected to be mostly white; its white-pixel ratio alone is not glare.
 * Measure focus before the clean/mono filters can turn pencil strokes into sharp edges. */
export function inspectDocumentPixels(data, W, H) {
  const q = inspectPixels(data, W, H);
  const blurry = q.focus < 22;
  return { ...q, ok: !blurry, hint: blurry ? '사진이 흐립니다. 다시 촬영해 주세요.' : null };
}
const inspectDocument = canvas => {
  const img = imgData(canvas);
  return inspectDocumentPixels(img.data, canvas.width, canvas.height);
};

/** Keep PNG/B&W and already-small JPEG/WebP bytes intact. For oversized photos,
 * try JPEG qualities at the same resolution before a single 2400→2339px step.
 * Never repeatedly shrink an A4 page below the scanner's 200dpi output. */
export async function encodeUpload(blob, { maxBytes = 1850000 } = {}) {
  if (!blob || !/^image\/(jpeg|png|webp)$/.test(blob.type)) throw { code: 'bad_image' };
  if (blob.size <= maxBytes) return blob;
  if (!canProcess()) throw { code: 'image_too_big' };
  const bmp = await loadBitmap(blob);
  try {
    const longSide = Math.max(bmp.width, bmp.height);
    const sides = [Math.min(WORK_MAX_SIDE, longSide)];
    const a4Side = Math.round(dpiToWidth(DEFAULT_DPI) * A4_RATIO);
    if (sides[0] > a4Side) sides.push(a4Side);
    for (const side of sides) {
      const canvas = toCanvas(bmp, side), ctx = canvas.getContext('2d');
      ctx.globalCompositeOperation = 'destination-over';
      ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, canvas.width, canvas.height);
      for (const quality of [0.92, 0.88, 0.84, 0.8, 0.76]) {
        const out = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', quality));
        if (out && out.size <= maxBytes) return out;
      }
    }
    throw { code: 'image_too_big' };
  } finally { try { bmp.close?.(); } catch { /* release decoded camera pixels */ } }
}

/** A quarter turn from the captured pixels, not from a compressed preview. */
export async function rotatePhoto(file) {
  const bmp = await loadBitmap(file);
  try {
    const base = toCanvas(bmp, SOURCE_MAX_SIDE), out = document.createElement('canvas');   // keep the photo's detail through a turn
    out.width = base.height; out.height = base.width;
    const ctx = out.getContext('2d');
    ctx.translate(out.width, 0); ctx.rotate(Math.PI / 2); ctx.drawImage(base, 0, 0);
    const blob = await new Promise(resolve => out.toBlob(resolve, 'image/png'));
    if (!blob) throw { code: 'bad_image' };
    return blob;
  } finally { try { bmp.close?.(); } catch { /* release decoded camera pixels */ } }
}

/** Optional desktop/weekly corner editor. The caller still decides when to upload. */
export async function editCorners(baseUrl, corners, { marker = false, lang = 'ko', pageFormat = 'a4', signal } = {}) {
  if (signal?.aborted) return null;
  const image = await loadImage(baseUrl), W = image.naturalWidth || image.width, H = image.naturalHeight || image.height;
  if (signal?.aborted) return null;
  const ko = lang !== 'en', txt = (a, b) => ko ? a : b;
  const points = (corners || [{ x: 0, y: 0 }, { x: W, y: 0 }, { x: 0, y: H }, { x: W, y: H }]).map(p => ({ ...p }));
  const dialog = document.createElement('dialog');
  Object.assign(dialog.style, { width: 'min(900px,95vw)', maxHeight: '94dvh', overflow: 'auto', background: '#171c24', color: '#eef2f8', border: '1px solid #596573', borderRadius: '12px', padding: '18px' });
  const title = document.createElement('h2'); title.textContent = txt('모서리 맞추기', 'Fix corners'); title.style.fontSize = '18px';
  const select = document.createElement('select');
  for (const [value, label] of [['marker', txt('검은 표식 중심 (여백 보존)', 'Black marker centres (keep margins)')], ['page', txt('종이의 네 귀퉁이', 'Four paper corners')]]) {
    const option = document.createElement('option'); option.value = value; option.textContent = label; select.append(option);
  }
  select.value = marker ? 'marker' : 'page'; select.setAttribute('aria-label', txt('기준점', 'Corner reference'));
  const format = document.createElement('select');
  for (const [value, label] of [['auto', txt('문서 비율 유지', 'Keep document proportions')], ['a4', txt('A4 답안지 · 200dpi', 'A4 answer sheet · 200dpi')]]) {
    const option = document.createElement('option'); option.value = value; option.textContent = label; format.append(option);
  }
  format.value = pageFormat === 'a4' ? 'a4' : 'auto'; format.setAttribute('aria-label', txt('출력 용지', 'Output format'));
  const hint = document.createElement('p'); hint.textContent = txt('네 점을 선택한 기준에 맞게 끌어 옮기세요.', 'Drag all four points to the selected reference.'); hint.style.fontSize = '13px';
  const wrap = document.createElement('div'); Object.assign(wrap.style, { position: 'relative', width: 'fit-content', maxWidth: '100%', margin: '16px auto' });
  Object.assign(image.style, { display: 'block', maxWidth: '100%', maxHeight: '64vh', width: 'auto', height: 'auto' }); wrap.append(image);
  const handles = points.map((p, i) => {
    const handle = document.createElement('button'); handle.type = 'button'; handle.textContent = String(i + 1);
    handle.setAttribute('aria-label', txt('모서리 ', 'Corner ') + (i + 1));
    Object.assign(handle.style, { position: 'absolute', width: '34px', height: '34px', border: '2px solid #fff', borderRadius: '50%', background: '#e1b844', color: '#171c24', padding: '0', transform: 'translate(-50%,-50%)', touchAction: 'none', fontSize: '13px', fontWeight: '700' });
    const place = () => { handle.style.left = points[i].x / W * 100 + '%'; handle.style.top = points[i].y / H * 100 + '%'; };
    handle.onpointerdown = e => { e.preventDefault(); handle.setPointerCapture(e.pointerId); };
    handle.onpointermove = e => { if (!handle.hasPointerCapture(e.pointerId)) return; const r = image.getBoundingClientRect(); points[i] = { x: Math.max(0, Math.min(W, (e.clientX - r.left) / r.width * W)), y: Math.max(0, Math.min(H, (e.clientY - r.top) / r.height * H)) }; place(); };
    handle.onpointerup = e => { if (handle.hasPointerCapture(e.pointerId)) handle.releasePointerCapture(e.pointerId); };
    wrap.append(handle); place(); return handle;
  });
  const controls = document.createElement('div'); Object.assign(controls.style, { display: 'flex', gap: '10px' });
  const cancel = document.createElement('button'), apply = document.createElement('button');
  cancel.textContent = txt('취소', 'Cancel'); apply.textContent = txt('모서리 적용', 'Apply corners');
  for (const button of [cancel, apply]) { button.type = 'button'; Object.assign(button.style, { flex: '1', padding: '12px', cursor: 'pointer', borderRadius: '7px' }); controls.append(button); }
  dialog.append(title, select, format, hint, wrap, controls); document.body.append(dialog);
  return new Promise(resolve => {
    let done = false;
    const abort = () => finish(null);
    const finish = result => { if (done) return; done = true; signal?.removeEventListener('abort', abort); dialog.close(); dialog.remove(); resolve(result); };
    cancel.onclick = () => finish(null); dialog.oncancel = e => { e.preventDefault(); finish(null); }; dialog.onclose = () => finish(null);
    apply.onclick = () => { const ordered = orderCorners(points); if (quadScore(ordered, W, H) < 0.1) { hint.textContent = txt('네 점을 서로 다른 네 귀퉁이에 맞춰 주세요.', 'Place the four points at four different corners.'); return; } finish({ corners: ordered, marker: select.value === 'marker', pageFormat: format.value }); };
    signal?.addEventListener('abort', abort, { once: true });
    if (signal?.aborted) return finish(null);
    dialog.showModal(); handles[0].focus();
  });
}

/* 무거운 단계 사이에 한 틱 쉬어 화면이 얼지 않게 합니다 */
const breathe = () => new Promise((r) => setTimeout(r, 0));
const blobPreview = blob => new Promise((resolve, reject) => {
  const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = () => reject(new Error('bad_image')); reader.readAsDataURL(blob);
});

/** Only a detector result from these exact captured video pixels may bypass a
 * second detector pass. Native-camera photos can have another field of view and
 * must be detected independently. Normalised coordinates survive working-size
 * downscaling without leaking preview coordinates into full-size geometry. */
export function validatedDetectionHint(hint, width, height) {
  if (hint?.source !== 'same-video-frame' || hint.scanEligible !== true || !['ml', 'marker', 'page'].includes(hint.method) ||
      !Number.isFinite(hint.score) || hint.score < .25 || !Array.isArray(hint.corners) || hint.corners.length !== 4 ||
      hint.corners.some(p => !p || !Number.isFinite(p.x) || !Number.isFinite(p.y) || p.x <= 0 || p.y <= 0 || p.x >= 1 || p.y >= 1)) return null;
  const corners = orderCorners(hint.corners.map(p => ({ x: p.x * width, y: p.y * height })));
  if (quadScore(corners, width, height) < .1) return null;
  return { corners, method: hint.method, score: Math.min(1, hint.score), scanEligible: true, paperStatus: 'document', engine: 'matched-video-frame' };
}

/* the page cut out of the decoded photo for the worker: the quad's bounding box, scaled down only when the page's
   short side exceeds PAGE_SOURCE_SIDE, with the corners moved into the piece. Null where it cannot be cut. */
async function pagePiece(photo, cornersOnBase, base) {
  if (typeof createImageBitmap !== 'function' || !photo || !(photo.width > 0)) return null;
  const fx = photo.width / base.width, fy = photo.height / base.height, pts = cornersOnBase.map(p => ({ x: p.x * fx, y: p.y * fy }));
  const pad = 4, x0 = Math.max(0, Math.floor(Math.min(...pts.map(p => p.x)) - pad)), y0 = Math.max(0, Math.floor(Math.min(...pts.map(p => p.y)) - pad));
  const x1 = Math.min(photo.width, Math.ceil(Math.max(...pts.map(p => p.x)) + pad)), y1 = Math.min(photo.height, Math.ceil(Math.max(...pts.map(p => p.y)) + pad));
  if (!(x1 - x0 > 8 && y1 - y0 > 8)) return null;
  const k = Math.min(1, PAGE_SOURCE_SIDE / Math.max(1, shortSide(orderCorners(pts))));
  const w = Math.max(1, Math.round((x1 - x0) * k)), h = Math.max(1, Math.round((y1 - y0) * k));
  try {
    const bitmap = await createImageBitmap(photo, x0, y0, x1 - x0, y1 - y0, k < 1 ? { resizeWidth: w, resizeHeight: h, resizeQuality: 'high' } : undefined);
    return { bitmap, corners: pts.map(p => ({ x: (p.x - x0) * bitmap.width / (x1 - x0), y: (p.y - y0) * bitmap.height / (y1 - y0) })), photoCorners: pts };
  } catch { return null; }
}
const shortSide = pts => Math.min(Math.hypot(pts[1].x - pts[0].x, pts[1].y - pts[0].y), Math.hypot(pts[2].x - pts[0].x, pts[2].y - pts[0].y));

/**
 * 사진 한 장을 답안지로 다듬습니다.
 *
 * @param {File|Blob} file
 * @param {{corners?, mode?, dpi?, onProgress?}} opts
 * @returns {{blob, previewUrl, corners, autoScore, method, quality, width, height, baseUrl, baseW, baseH}}
 */
export async function processShot(file, opts = {}) {
  /* The defaults are those of the first exam-mode scans (IPhO 2023, b900f59), whose pages read and graded well: the
     clean mode (shadows divided out, ink contrast raised) on an A4 page at 200dpi. Colour and auto proportions remain
     choices. */
  const { corners = null, mode = 'clean', dpi = DEFAULT_DPI, onProgress, pageFormat = 'a4' } = opts;
  const say = (pct, label) => { try { onProgress?.(pct, label); } catch { /* 무시 */ } };

  say(5, '사진 읽는 중');
  const bmp = await loadBitmap(file);
  try {
  const base = toCanvas(bmp);
  await breathe();

  say(25, '모서리 찾는 중');
  let pts = corners ? orderCorners(corners) : null;
  let autoScore = 1, method = 'manual', cornersReliable = true, paperStatus = pageFormat === 'a4' ? 'manual_a4' : 'manual', scanEligible = !!pts;
  let detectionReason = null;
  if (!pts) {
    const d = validatedDetectionHint(opts.detectionHint, base.width, base.height) || await detectOnProbe(base, { retry: true, signal: opts.signal, onProgress: () => say(30, '문서 모서리 찾는 중') });
    pts = d.corners; autoScore = d.score; method = d.method; cornersReliable = d.scanEligible === true && d.verified !== false;
    paperStatus = d.paperStatus || 'not_found'; scanEligible = d.scanEligible === true;
    detectionReason = d.reason || null;
  }
  await breathe();

  const warpApplied = scanEligible && method !== 'frame', outputFormat = pageFormat === 'a4' ? 'a4' : 'auto';
  const a4WarpApplied = warpApplied && outputFormat === 'a4';
  say(50, warpApplied ? '기울기 펴는 중' : '원본 유지');
  /* 마커로 찾았을 때만 인셋을 씁니다. 종이 테두리로 찾았다면
     그 네 점이 곧 지면 모서리이므로 인셋이 필요 없습니다. */
  const inset = method === 'marker' ? MARKER_INSET : null;
  const piece = warpApplied ? await pagePiece(bmp, pts, base) : null;
  let rendered;
  try { rendered = warpApplied ? await renderInWorker(piece?.bitmap || base, piece?.corners || pts, mode, dpi, inset, outputFormat, opts.signal) : null; }
  finally { try { piece?.bitmap.close(); } catch { /* 무시 */ } }
  /* a photo whose corners were not found is still cleaned, as a scan is, at its own proportions */
  let out = rendered ? null : warpApplied ? warp(base, pts, dpiToWidth(dpi), inset, { pageFormat: outputFormat }) : base;
  const quality = rendered?.quality || inspectDocument(out);
  await breathe();

  say(72, '그림자 지우는 중');
  if (out) out = enhance(out, mode);
  await breathe();

  say(90, '선명도 확인 중');

  const blob = rendered?.blob || await new Promise((r) =>
    mode === 'mono' || mode === 'original' && !warpApplied ? out.toBlob(r, 'image/png') : out.toBlob(r, 'image/jpeg', 0.94)
  );
  if (!blob) throw { code: 'bad_image' };
  say(100, '완료');

  return {
    blob,
    previewUrl: rendered ? await blobPreview(blob) : out.toDataURL('image/jpeg', 0.94),
    corners: pts,
    cornersReliable,
    paperStatus,
    detectionReason,
    a4WarpApplied,
    warpApplied,
    outputFormat,
    autoScore,
    method,
    quality,
    width: rendered?.width || out.width,
    height: rendered?.height || out.height,
    baseUrl: rendered?.baseBlob ? await blobPreview(rendered.baseBlob) : base.toDataURL('image/png'), // lossless editable baseline
    baseW: base.width,
    baseH: base.height,
    sourceBlob: file,            // reprocess straightens from it again, at full resolution
    sourceShortSide: shortSide(piece?.photoCorners || pts.map(p => ({ x: p.x * bmp.width / base.width, y: p.y * bmp.height / base.height }))),
  };
  } finally { try { bmp.close?.(); } catch { /* 무시 */ } }
}

/** 이미 잡아둔 원본에서 모서리·모드만 바꿔 다시 만듭니다 */
export async function reprocess(baseDataUrl, corners, mode = 'clean', dpi = DEFAULT_DPI, inset = null, options = {}) {
  const img = await loadImage(baseDataUrl);
  const base = toCanvas(img);
  const warpApplied = options.preserveOriginal !== true, outputFormat = options.pageFormat === 'auto' ? 'auto' : 'a4';
  const a4WarpApplied = warpApplied && outputFormat === 'a4';
  /* options.source: the photo processShot read (its result's sourceBlob), straightened again at full resolution */
  const ordered = orderCorners(corners);
  let piece = null, photo = null;
  if (warpApplied && options.source) {
    try { photo = await loadBitmap(options.source); piece = await pagePiece(photo, ordered, base); }
    catch { piece = null; } finally { try { photo?.close?.(); } catch {} }
  }
  let rendered;
  try { rendered = warpApplied ? await renderInWorker(piece?.bitmap || base, piece?.corners || ordered, mode, dpi, inset, outputFormat, options.signal) : null; }
  finally { try { piece?.bitmap.close(); } catch {} }
  let out = rendered ? null : warpApplied ? warp(base, ordered, dpiToWidth(dpi), inset, { pageFormat: outputFormat }) : base;
  const quality = rendered?.quality || inspectDocument(out);
  if (out) out = enhance(out, mode);
  const blob = rendered?.blob || await new Promise((r) =>
    mode === 'mono' || mode === 'original' && !warpApplied ? out.toBlob(r, 'image/png') : out.toBlob(r, 'image/jpeg', 0.94)
  );
  if (!blob) throw { code: 'bad_image' };
  return { blob, previewUrl: rendered ? await blobPreview(blob) : out.toDataURL('image/jpeg', 0.94), quality, width: rendered?.width || out.width, height: rendered?.height || out.height, a4WarpApplied, warpApplied, outputFormat,
    ...(options.source ? { sourceBlob: options.source } : {}), sourceShortSide: shortSide(piece?.photoCorners || ordered) };
}
