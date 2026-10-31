/* ------------------------------------------------------------------
   기기 내 문서 스캔 엔진
   ------------------------------------------------------------------
   사진의 문서 모서리를 찾아 원근을 보정합니다. 기본 출력은 원래 색상이며
   A4 비율은 사용자가 선택한 경우에만 적용합니다.

   흐름:
     사진 → (EXIF 회전 보정) → 작업용 캔버스
          → Worker의 인쇄 마커 / DocAligner 추론 + 원본 경계 검증
          → 불확실하면 작업 이미지 유지 · 수동 모서리 확인
          → 원근 보정 (겹샘플링 + 이중선형)
          → 선택한 경우에만 그림자 제거 · 이진화
          → 품질 점검 (흔들림 · 반사광)

   설계 원칙
   - 계산의 핵심은 캔버스를 모르는 순수 함수입니다. (data, W, H) 만 받습니다.
     그래서 node 에서 그대로 테스트하고 Worker에서도 공유합니다.
   - 적분영상 대신 **슬라이딩 합**을 씁니다. A4 200dpi(1654×2339)에서
     적분영상은 Float64 로 30MB 넘게 잡아먹어 저사양 폰에서 터집니다.
   - 모델·ONNX Runtime은 같은 출처의 고정 정적 파일로 지연 로드합니다.
     사진이나 토큰을 모델 다운로드·추론 요청에 보내지 않습니다. 라이선스는 README 참조.
------------------------------------------------------------------- */

/* A4 = 210 × 297 mm */
export const A4_RATIO = 297 / 210;

/** 200dpi 기준 A4 가로 픽셀. 손글씨 OCR 은 150dpi 부터 급격히 나빠집니다. */
export const DEFAULT_DPI = 200;
export const dpiToWidth = (dpi) => Math.round((210 / 25.4) * dpi);

/* 원본을 줄여 담을 최대 변. 출력보다 넉넉해야 겹샘플링 이득이 있습니다. */
const WORK_MAX_SIDE = 2400;

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

const pageCross = (a, b, c) => (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
function pageHull(points) {
  points.sort((a, b) => a.x - b.x || a.y - b.y);
  const lower = [], upper = [];
  for (const p of points) { while (lower.length > 1 && pageCross(lower.at(-2), lower.at(-1), p) <= 0) lower.pop(); lower.push(p); }
  for (let i = points.length - 1; i >= 0; i--) { const p = points[i]; while (upper.length > 1 && pageCross(upper.at(-2), upper.at(-1), p) <= 0) upper.pop(); upper.push(p); }
  lower.pop(); upper.pop(); return lower.concat(upper);
}
function pageFour(hull) {
  if (hull.length < 4) return null;
  hull = [...hull];
  while (hull.length > 4) {
    let at = 0, least = Infinity;
    for (let i = 0; i < hull.length; i++) { const area = Math.abs(pageCross(hull[(i + hull.length - 1) % hull.length], hull[i], hull[(i + 1) % hull.length])); if (area < least) { least = area; at = i; } }
    hull.splice(at, 1);
  }
  return orderCorners(hull);
}
function pagePixel(g, w, h, x, y) {
  x = Math.max(0, Math.min(w - 1, x)); y = Math.max(0, Math.min(h - 1, y));
  const ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy;
  const j = iy * w + ix, right = Math.min(ix + 1, w - 1), down = Math.min(iy + 1, h - 1) * w;
  return (g[j] * (1 - fx) + g[iy * w + right] * fx) * (1 - fy) + (g[down + ix] * (1 - fx) + g[down + right] * fx) * fy;
}
function pageIntersection(a, b) {
  const det = a.nx * b.ny - a.ny * b.nx;
  return Math.abs(det) < .12 ? null : { x: (a.r * b.ny - a.ny * b.r) / det, y: (a.nx * b.r - a.r * b.nx) / det };
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
function pageEvidence(corners, g, w, h, refine = false) {
  if (!corners || corners.some(p => !p || !Number.isFinite(p.x + p.y))) return null;
  const q = orderCorners(corners), poly = [q[0], q[1], q[3], q[2]], margin = Math.max(1.5, Math.min(w, h) * .007);
  if (quadScore(q, w, h) < .18 || q.some(p => p.x < margin || p.y < margin || p.x > w - 1 - margin || p.y > h - 1 - margin)) return null;
  let area = 0; for (let i = 0; i < 4; i++) area += poly[i].x * poly[(i + 1) % 4].y - poly[(i + 1) % 4].x * poly[i].y;
  area = Math.abs(area) / 2; const cover = area / (w * h);
  if (cover < .095 || cover > .94) return null;
  const lengths = poly.map((p, i) => Math.hypot(p.x - poly[(i + 1) % 4].x, p.y - poly[(i + 1) % 4].y));
  if (Math.min(...lengths) < Math.min(w, h) * .14 || Math.max(...lengths) / Math.min(...lengths) > 5) return null;
  const cx = q.reduce((s, p) => s + p.x, 0) / 4, cy = q.reduce((s, p) => s + p.y, 0) / 4;
  const interior = [];
  for (const u of [.25, .5, .75]) for (const v of [.25, .5, .75]) {
    const x = (q[0].x * (1 - u) + q[1].x * u) * (1 - v) + (q[2].x * (1 - u) + q[3].x * u) * v;
    const y = (q[0].y * (1 - u) + q[1].y * u) * (1 - v) + (q[2].y * (1 - u) + q[3].y * u) * v;
    interior.push(pagePixel(g, w, h, x, y));
  }
  interior.sort((a, b) => a - b);
  if (interior[4] < 55) return null; // a solid black diagram is not white paper
  const supports = [], contrasts = [], lines = [];
  for (let side = 0; side < 4; side++) {
    const a = poly[side], b = poly[(side + 1) % 4], len = lengths[side];
    let nx = -(b.y - a.y) / len, ny = (b.x - a.x) / len;
    if ((cx - (a.x + b.x) / 2) * nx + (cy - (a.y + b.y) / 2) * ny < 0) { nx = -nx; ny = -ny; }
    const far = Math.max(3, Math.min(8, len * .028)), count = refine ? 36 : 18, offsets = [];
    let supported = 0, contrast = 0;
    for (let i = 0; i < count; i++) {
      const t = .06 + .88 * (i + .5) / count, x = a.x + (b.x - a.x) * t, y = a.y + (b.y - a.y) * t;
      let best = -1, bestOffset = 0;
      const range = refine ? 5 : 2;
      for (let offset = -range; offset <= range; offset++) {
        const px = x + nx * offset, py = y + ny * offset;
        const gradient = Math.abs(pagePixel(g, w, h, px + nx * 1.3, py + ny * 1.3) - pagePixel(g, w, h, px - nx * 1.3, py - ny * 1.3));
        const value = gradient - Math.abs(offset) * .3;
        if (value > best) { best = value; bestOffset = offset; }
      }
      const px = x + nx * bestOffset, py = y + ny * bestOffset;
      const inside = (pagePixel(g, w, h, px + nx * far, py + ny * far) + pagePixel(g, w, h, px + nx * far * 1.5, py + ny * far * 1.5)) / 2;
      const outside = (pagePixel(g, w, h, px - nx * far, py - ny * far) + pagePixel(g, w, h, px - nx * far * 1.5, py - ny * far * 1.5)) / 2;
      const difference = Math.abs(inside - outside);
      const innerSlope = Math.abs(pagePixel(g, w, h, px + nx * (far + 1.3), py + ny * (far + 1.3)) - pagePixel(g, w, h, px + nx * (far - 1.3), py + ny * (far - 1.3)));
      const outerSlope = Math.abs(pagePixel(g, w, h, px - nx * (far + 1.3), py - ny * (far + 1.3)) - pagePixel(g, w, h, px - nx * (far - 1.3), py - ny * (far - 1.3)));
      // A broad illumination ramp is not a paper boundary: the transition must
      // be sharper than the normal gradient on either side of it.
      if (best >= Math.max(2.2, Math.max(innerSlope, outerSlope) * 1.35 + .8) && difference >= 4) { supported++; contrast += difference; offsets.push(bestOffset); }
    }
    supports.push(supported / count); contrasts.push(supported ? contrast / supported : 0);
    offsets.sort((a, b) => a - b); const shift = offsets.length ? offsets[offsets.length >> 1] : 0;
    lines.push({ nx, ny, r: nx * a.x + ny * a.y + shift });
  }
  const support = supports.reduce((s, v) => s + v, 0) / 4, weakest = Math.min(...supports);
  if (weakest < .44 || support < .64 || Math.min(...contrasts) < 4) return null;
  if (refine) {
    const fitted = lines.map((line, i) => pageIntersection(lines[(i + 3) % 4], line));
    const improved = pageEvidence(fitted, g, w, h, false);
    if (improved) return improved;
  }
  const strength = Math.min(1, Math.min(...contrasts) / 18);
  const score = Math.min(.96, .34 + .32 * support + .16 * weakest + .12 * strength + .02 * Math.min(1, cover / .3));
  return { corners: q, score, edgeSupport: support, weakestEdge: weakest, clipped: false, cover,
    autoCaptureEligible: score >= .78 && support >= .83 && weakest >= .72 };
}

/** A bounded, markerless detector: both intensity polarities, closed edge regions,
 * and gradient-directed lines propose quads. Only four supported OUTER paper
 * transitions may win; an inner printed frame or the image boundary is not a page. */
export function findPageQuadGray(gray, W, H) {
  const none = { corners: null, score: 0, method: 'page', edgeSupport: 0, clipped: false, autoCaptureEligible: false, paperStatus: 'not_found', paperAssessment: null };
  if (W < 32 || H < 32 || gray.length < W * H) return none;
  const scale = Math.min(1, 320 / Math.max(W, H)), w = Math.round(W * scale), h = Math.round(H * scale), n = w * h;
  const g = new Uint8Array(n), sx = W / w, sy = H / h;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let sum = 0, count = 0;
    for (let j = Math.floor(y * sy); j < Math.floor((y + 1) * sy); j++) for (let i = Math.floor(x * sx); i < Math.floor((x + 1) * sx); i++) { sum += gray[j * W + i]; count++; }
    g[y * w + x] = sum / count;
  }
  const smooth = boxMean(g, w, h, 1), bytes = Uint8Array.from(smooth), gx = new Float32Array(n), gy = new Float32Array(n), mag = new Float32Array(n);
  let strong = 0, low = 255, high = 0;
  for (let i = 0; i < n; i++) { if (g[i] < low) low = g[i]; if (g[i] > high) high = g[i]; }
  if (high - low < 5) return none;
  for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
    const i = y * w + x;
    gx[i] = (smooth[i - w + 1] + 2 * smooth[i + 1] + smooth[i + w + 1] - smooth[i - w - 1] - 2 * smooth[i - 1] - smooth[i + w - 1]) / 4;
    gy[i] = (smooth[i + w - 1] + 2 * smooth[i + w] + smooth[i + w + 1] - smooth[i - w - 1] - 2 * smooth[i - w] - smooth[i - w + 1]) / 4;
    mag[i] = Math.abs(gx[i]) + Math.abs(gy[i]); if (mag[i] >= 4) strong++;
  }
  const candidates = [], stack = new Int32Array(n), seen = new Uint8Array(n), mask = new Uint8Array(n);
  const regions = () => {
    seen.fill(0);
    for (let seed = 0; seed < n; seed++) {
      if (!mask[seed] || seen[seed]) continue;
      let sp = 0, size = 0, x0 = w, x1 = 0, y0 = h, y1 = 0; const boundary = [];
      stack[sp++] = seed; seen[seed] = 1;
      while (sp) {
        const i = stack[--sp], y = (i / w) | 0, x = i - y * w; size++;
        x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
        let edge = false;
        if (!x || !mask[i - 1]) edge = true; else if (!seen[i - 1]) { seen[i - 1] = 1; stack[sp++] = i - 1; }
        if (x === w - 1 || !mask[i + 1]) edge = true; else if (!seen[i + 1]) { seen[i + 1] = 1; stack[sp++] = i + 1; }
        if (!y || !mask[i - w]) edge = true; else if (!seen[i - w]) { seen[i - w] = 1; stack[sp++] = i - w; }
        if (y === h - 1 || !mask[i + w]) edge = true; else if (!seen[i + w]) { seen[i + w] = 1; stack[sp++] = i + w; }
        if (edge) boundary.push(i);
      }
      if (size < n * .015 || (x1 - x0) * (y1 - y0) < n * .095 || x0 <= 1 || y0 <= 1 || x1 >= w - 2 || y1 >= h - 2 || boundary.length < 4) continue;
      const quad = pageFour(pageHull(boundary.map(i => ({ x: i % w, y: (i / w) | 0 })))); if (quad) candidates.push(quad);
    }
  };
  const border = [];
  for (let y = 0; y < h; y += 3) for (let x = 0; x < w; x += 3) if (x < w * .06 || x > w * .94 || y < h * .06 || y > h * .94) border.push(g[y * w + x]);
  border.sort((a, b) => a - b); const background = border[border.length >> 1];
  const thresholds = [...new Set([otsu(bytes), background - 6, background + 6].map(v => Math.max(1, Math.min(254, Math.round(v)))))];
  for (const threshold of thresholds) for (const polarity of [1, -1]) { for (let i = 0; i < n; i++) mask[i] = polarity > 0 ? smooth[i] > threshold : smooth[i] < threshold; regions(); }
  for (const threshold of [5, 16]) {
    mask.fill(1);
    for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) if (mag[y * w + x] >= threshold) {
      const i = y * w + x; mask[i] = mask[i - 1] = mask[i + 1] = mask[i - w] = mask[i + w] = 0;
    }
    regions();
  }
  const finish = best => {
    const fitted = pageEvidence(best.corners, smooth, w, h, true) || best;
    // Classify only the winning outer boundary. An A4-shaped printed rectangle
    // inside a different object must never replace its real outside corners.
    return assessedDocument({ ...fitted, corners: fitted.corners.map(p => ({ x: (p.x + .5) * sx, y: (p.y + .5) * sy })), method: 'page' }, W, H);
  };
  let regionBest = null;
  for (const candidate of candidates) {
    const result = pageEvidence(candidate, smooth, w, h);
    if (result && (!regionBest || result.cover > regionBest.cover * 1.04 || result.cover >= regionBest.cover * .96 && result.score > regionBest.score)) regionBest = result;
  }
  // A closed region with four measured boundaries already supplies the outer
  // page. Avoid letting noisier Hough intersections move its corners outward.
  if (regionBest && regionBest.score >= .85 && regionBest.weakestEdge >= .72) return finish(regionBest);
  // At most 10k points, 60 normal directions, 24 lines and 24 opposite-line
  // pairs: dense handwriting/noise cannot create an unbounded combinatorial pass.
  const regionCount = candidates.length;
  const points = [], stride = Math.max(1, Math.ceil(strong / 10000)); let at = 0;
  for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) { const i = y * w + x; if (mag[i] >= 4 && at++ % stride === 0) points.push({ x, y, nx: gx[i] / Math.hypot(gx[i], gy[i]), ny: gy[i] / Math.hypot(gx[i], gy[i]) }); }
  const bins = 60, diag = Math.ceil(Math.hypot(w, h)), width = 2 * diag + 1, votes = new Uint16Array(bins * width);
  const cos = Array.from({ length: bins }, (_, i) => Math.cos(i * Math.PI / bins)), sin = cos.map((_, i) => Math.sin(i * Math.PI / bins));
  for (const p of points) { let angle = Math.atan2(p.ny, p.nx); if (angle < 0) angle += Math.PI; const center = Math.round(angle * bins / Math.PI) % bins;
    for (let d = -1; d <= 1; d++) { const t = (center + d + bins) % bins, r = Math.round(p.x * cos[t] + p.y * sin[t]) + diag; votes[t * width + r]++; } }
  const peaks = [];
  for (let t = 0; t < bins; t++) for (let r = 0; r < width; r++) if (votes[t * width + r] >= Math.max(10, Math.min(w, h) * .08)) peaks.push({ nx: cos[t], ny: sin[t], r: r - diag, votes: votes[t * width + r] });
  peaks.sort((a, b) => b.votes - a.votes); const lines = [];
  for (const p of peaks) {
    if (lines.some(q => Math.abs(p.nx * q.nx + p.ny * q.ny) > .99 && Math.abs(p.r - (p.nx * q.nx + p.ny * q.ny > 0 ? q.r : -q.r)) < 7)) continue;
    lines.push(p); if (lines.length === 24) break;
  }
  const pairs = [];
  for (let i = 0; i < lines.length; i++) for (let j = i + 1; j < lines.length; j++) {
    const a = lines[i], b = lines[j], dot = a.nx * b.nx + a.ny * b.ny, sign = dot > 0 ? 1 : -1;
    const distance = Math.abs(a.r - a.nx * w / 2 - a.ny * h / 2 - sign * (b.r - b.nx * w / 2 - b.ny * h / 2));
    if (Math.abs(dot) > .80 && distance > Math.min(w, h) * .18) pairs.push({ a, b, score: (a.votes + b.votes) * distance });
  }
  pairs.sort((a, b) => b.score - a.score); pairs.length = Math.min(pairs.length, 24);
  for (let i = 0; i < pairs.length; i++) for (let j = i + 1; j < pairs.length; j++) {
    const a = pairs[i], b = pairs[j]; if (Math.abs(a.a.nx * b.a.nx + a.a.ny * b.a.ny) > .82) continue;
    const quad = [pageIntersection(a.a, b.a), pageIntersection(a.a, b.b), pageIntersection(a.b, b.a), pageIntersection(a.b, b.b)];
    if (quad.every(p => p && p.x > 0 && p.x < w && p.y > 0 && p.y < h)) candidates.push(quad);
  }
  // Rank and merge cheap geometric hypotheses before sampling any pixels.
  // Large enclosing boundaries precede strong printed rectangles inside a page.
  const unique = new Map();
  for (let index = 0; index < candidates.length; index++) {
    const candidate = candidates[index];
    if (candidate.some(p => !p)) continue;
    const q = orderCorners(candidate);
    if (quadScore(q, w, h) < .18) continue;
    const poly = [q[0], q[1], q[3], q[2]]; let area = 0;
    for (let i = 0; i < 4; i++) area += poly[i].x * poly[(i + 1) % 4].y - poly[(i + 1) % 4].x * poly[i].y;
    const cover = Math.abs(area) / (2 * n);
    if (cover < .095 || cover > .94) continue;
    const key = q.map(p => Math.round(p.x / 5) + ',' + Math.round(p.y / 5)).join('|');
    if (!unique.has(key)) unique.set(key, { q, cover, region: index < regionCount });
  }
  const shortlist = [...unique.values()].sort((a, b) => b.cover - a.cover).slice(0, 40);
  let best = null;
  for (const { q: candidate, region } of shortlist) {
    const result = pageEvidence(candidate, smooth, w, h);
    if (result && (!best || region && result.score >= .90 && !best.region && result.cover >= best.cover * .75 ||
        result.cover > best.cover * 1.06 && !(best.region && best.score >= .90 && result.cover < best.cover * 1.14) ||
        result.cover >= best.cover * .94 && result.score > best.score)) best = { ...result, region };
  }
  if (!best) return none;
  return finish(best);
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
export function detectDocumentQuadGray(g, W, H) {
  const marker = findSheetMarkersGray(g, W, H);
  if (marker && marker.score >= .75) return assessedDocument({ ...marker, clipped: false, autoCaptureEligible: true }, W, H);
  const page = findPageQuadGray(g, W, H);
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
  return detectDocumentQuadGray(toGray(img.data, W, H), W, H);
}

/** Lazy, entirely on-device detector. No camera image is sent to an API.
 * Classical candidates remain editable when a worker/model is unavailable. */
export async function detectDocumentQuad(canvas, options = {}) {
  if (typeof Worker !== 'undefined' && typeof createImageBitmap === 'function') {
    try {
      const { getDocumentDetector } = await import(new URL('./document-detector.mjs?v=d4f342e770a6', import.meta.url));
      return await getDocumentDetector().detect(canvas, options);
    } catch (error) { if (error?.name === 'AbortError') throw error; }
  }
  if (options.preview) return { corners: null, score: 0, method: 'frame', engine: 'manual-fallback', scanEligible: false,
    autoCaptureEligible: false, reason: 'document_model_unavailable' };
  const proposed = detectQuad(canvas);
  return { ...proposed, engine: 'manual-fallback', scanEligible: false, autoCaptureEligible: false,
    reason: 'document_model_unavailable' };
}

export async function warmDocumentDetector(options) {
  if (typeof Worker === 'undefined') return false;
  try { const { getDocumentDetector } = await import(new URL('./document-detector.mjs?v=d4f342e770a6', import.meta.url)); await getDocumentDetector().warm(options); return true; }
  catch { return false; }
}

async function renderInWorker(base, corners, mode, dpi, inset, pageFormat, signal, includeBaseline = false) {
  if (typeof Worker === 'undefined' || typeof createImageBitmap !== 'function') return null;
  try {
    const { getDocumentDetector } = await import(new URL('./document-detector.mjs?v=d4f342e770a6', import.meta.url));
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
    const base = toCanvas(bmp), out = document.createElement('canvas');
    out.width = base.height; out.height = base.width;
    const ctx = out.getContext('2d');
    ctx.translate(out.width, 0); ctx.rotate(Math.PI / 2); ctx.drawImage(base, 0, 0);
    const blob = await new Promise(resolve => out.toBlob(resolve, 'image/png'));
    if (!blob) throw { code: 'bad_image' };
    return blob;
  } finally { try { bmp.close?.(); } catch { /* release decoded camera pixels */ } }
}

/** Optional desktop/weekly corner editor. The caller still decides when to upload. */
export async function editCorners(baseUrl, corners, { marker = false, lang = 'ko', pageFormat = 'auto' } = {}) {
  const image = await loadImage(baseUrl), W = image.naturalWidth || image.width, H = image.naturalHeight || image.height;
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
    const finish = result => { if (done) return; done = true; dialog.close(); dialog.remove(); resolve(result); };
    cancel.onclick = () => finish(null); dialog.oncancel = e => { e.preventDefault(); finish(null); }; dialog.onclose = () => finish(null);
    apply.onclick = () => { const ordered = orderCorners(points); if (quadScore(ordered, W, H) < 0.1) { hint.textContent = txt('네 점을 서로 다른 네 귀퉁이에 맞춰 주세요.', 'Place the four points at four different corners.'); return; } finish({ corners: ordered, marker: select.value === 'marker', pageFormat: format.value }); };
    dialog.showModal(); handles[0].focus();
  });
}

/* 무거운 단계 사이에 한 틱 쉬어 화면이 얼지 않게 합니다 */
const breathe = () => new Promise((r) => setTimeout(r, 0));
const blobPreview = blob => new Promise((resolve, reject) => {
  const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = () => reject(new Error('bad_image')); reader.readAsDataURL(blob);
});

/**
 * 사진 한 장을 답안지로 다듬습니다.
 *
 * @param {File|Blob} file
 * @param {{corners?, mode?, dpi?, onProgress?}} opts
 * @returns {{blob, previewUrl, corners, autoScore, method, quality, width, height, baseUrl, baseW, baseH}}
 */
export async function processShot(file, opts = {}) {
  const { corners = null, mode = 'original', dpi = DEFAULT_DPI, onProgress, pageFormat = 'auto' } = opts;
  const say = (pct, label) => { try { onProgress?.(pct, label); } catch { /* 무시 */ } };

  say(5, '사진 읽는 중');
  const bmp = await loadBitmap(file);
  const base = toCanvas(bmp);
  try { bmp.close?.(); } catch { /* 무시 */ }
  await breathe();

  say(25, '모서리 찾는 중');
  let pts = corners ? orderCorners(corners) : null;
  let autoScore = 1, method = 'manual', cornersReliable = true, paperStatus = pageFormat === 'a4' ? 'manual_a4' : 'manual', scanEligible = !!pts;
  if (!pts) {
    const d = await detectDocumentQuad(base, { signal: opts.signal, onProgress: stage => say(30, stage === 'download' ? '기기 내 문서 모델 준비 중' : '문서 모서리 찾는 중') });
    pts = d.corners; autoScore = d.score; method = d.method; cornersReliable = d.scanEligible === true;
    paperStatus = d.paperStatus || 'not_found'; scanEligible = d.scanEligible === true;
  }
  await breathe();

  const warpApplied = scanEligible && method !== 'frame', outputFormat = pageFormat === 'a4' ? 'a4' : 'auto';
  const a4WarpApplied = warpApplied && outputFormat === 'a4';
  say(50, warpApplied ? '기울기 펴는 중' : '원본 유지');
  /* 마커로 찾았을 때만 인셋을 씁니다. 종이 테두리로 찾았다면
     그 네 점이 곧 지면 모서리이므로 인셋이 필요 없습니다. */
  const inset = method === 'marker' ? MARKER_INSET : null;
  const rendered = warpApplied ? await renderInWorker(base, pts, mode, dpi, inset, outputFormat, opts.signal, true) : null;
  let out = rendered ? null : warpApplied ? warp(base, pts, dpiToWidth(dpi), inset, { pageFormat: outputFormat }) : base;
  const quality = rendered?.quality || inspectDocument(out);
  await breathe();

  say(72, '그림자 지우는 중');
  if (warpApplied && out) out = enhance(out, mode);
  await breathe();

  say(90, '선명도 확인 중');

  const blob = rendered?.blob || await new Promise((r) =>
    !warpApplied || mode === 'mono' ? out.toBlob(r, 'image/png') : out.toBlob(r, 'image/jpeg', 0.94)
  );
  if (!blob) throw { code: 'bad_image' };
  say(100, '완료');

  return {
    blob,
    previewUrl: rendered ? await blobPreview(blob) : out.toDataURL('image/jpeg', 0.94),
    corners: pts,
    cornersReliable,
    paperStatus,
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
    sourceShortSide: Math.min(Math.hypot(pts[1].x - pts[0].x, pts[1].y - pts[0].y), Math.hypot(pts[2].x - pts[0].x, pts[2].y - pts[0].y)),
  };
}

/** 이미 잡아둔 원본에서 모서리·모드만 바꿔 다시 만듭니다 */
export async function reprocess(baseDataUrl, corners, mode = 'original', dpi = DEFAULT_DPI, inset = null, options = {}) {
  const img = await loadImage(baseDataUrl);
  const base = toCanvas(img);
  const warpApplied = options.preserveOriginal !== true, outputFormat = options.pageFormat === 'a4' ? 'a4' : 'auto';
  const a4WarpApplied = warpApplied && outputFormat === 'a4';
  const ordered = orderCorners(corners), rendered = warpApplied ? await renderInWorker(base, ordered, mode, dpi, inset, outputFormat, options.signal) : null;
  let out = rendered ? null : warpApplied ? warp(base, ordered, dpiToWidth(dpi), inset, { pageFormat: outputFormat }) : base;
  const quality = rendered?.quality || inspectDocument(out);
  if (warpApplied && out) out = enhance(out, mode);
  const blob = rendered?.blob || await new Promise((r) =>
    !warpApplied || mode === 'mono' ? out.toBlob(r, 'image/png') : out.toBlob(r, 'image/jpeg', 0.94)
  );
  if (!blob) throw { code: 'bad_image' };
  const pts = orderCorners(corners);
  return { blob, previewUrl: rendered ? await blobPreview(blob) : out.toDataURL('image/jpeg', 0.94), quality, width: rendered?.width || out.width, height: rendered?.height || out.height, a4WarpApplied, warpApplied, outputFormat,
    sourceShortSide: Math.min(Math.hypot(pts[1].x - pts[0].x, pts[1].y - pts[0].y), Math.hypot(pts[2].x - pts[0].x, pts[2].y - pts[0].y)) };
}
