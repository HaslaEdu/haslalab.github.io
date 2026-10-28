/* ------------------------------------------------------------------
   문서 스캔 엔진 v2
   ------------------------------------------------------------------
   답안지를 찍은 사진 한 장을 A4 비율의 반듯한 흑백 문서로 만듭니다.

   흐름:
     사진 → (EXIF 회전 보정) → 작업용 캔버스
          → 네 꼭짓점 찾기  ① 인쇄된 검은 마커
                            ② 종이 테두리 (마커 실패 시)
                            ③ 전체 화면 (둘 다 실패 시 · 사용자가 조정)
          → 원근 보정 (겹샘플링 + 이중선형)
          → 그림자 제거 · 이진화
          → 품질 점검 (흔들림 · 반사광)

   설계 원칙
   - 계산의 핵심은 캔버스를 모르는 순수 함수입니다. (data, W, H) 만 받습니다.
     그래서 node 에서 그대로 테스트할 수 있고, 나중에 Worker 로 옮기기도 쉽습니다.
   - 적분영상 대신 **슬라이딩 합**을 씁니다. A4 200dpi(1654×2339)에서
     적분영상은 Float64 로 30MB 넘게 잡아먹어 저사양 폰에서 터집니다.
   - 외부 라이브러리 없음. 폰 브라우저에서 바로 돕니다.
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

  if (found < 4) return { corners, score: found / 4 * 0.5, method: 'marker' };

  const ordered = orderCorners(corners);
  const s = quadScore(ordered, W, H);
  return { corners: ordered, score: s, method: 'marker' };
}

/* ---------- ② 종이 테두리 찾기 (마커 없는 사진) ---------- */

/**
 * 배경보다 밝은 종이 덩어리를 찾아 그 극점 네 개를 꼭짓점으로 씁니다.
 *
 * 가로 240px 정도로 줄여서 계산합니다. 원본 해상도로 하면 느리기만 하고
 * 정확도는 오히려 떨어집니다 — 글씨와 격자선이 덩어리를 갈라놓기 때문입니다.
 * 줄이면 그런 잔무늬가 뭉개져서 종이 전체가 하나로 붙습니다.
 */
export function findPageQuadGray(gray, W, H) {
  const target = 240;
  const step = Math.max(1, Math.floor(Math.max(W, H) / target));
  const w = Math.floor(W / step), h = Math.floor(H / step);
  if (w < 24 || h < 24) return { corners: null, score: 0, method: 'page' };

  const small = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) small[y * w + x] = gray[y * step * W + x * step];
  }

  const blurred = boxMean(small, w, h, 2);
  const bytes = new Uint8Array(w * h);
  for (let i = 0; i < bytes.length; i++) bytes[i] = blurred[i];
  const t = otsu(bytes);

  /* 가운데에서 시작해 밝은 영역을 채웁니다. 종이가 화면 중앙에 있다는
     가정인데, 문서 촬영에서는 사실상 항상 맞습니다. */
  const seen = new Uint8Array(w * h);
  const stack = new Int32Array(w * h);
  let bestSet = null, bestN = 0;

  const seeds = [];
  for (let sy = 0.35; sy <= 0.66; sy += 0.15) {
    for (let sx = 0.35; sx <= 0.66; sx += 0.15) {
      seeds.push(((h * sy) | 0) * w + ((w * sx) | 0));
    }
  }

  for (const seed of seeds) {
    if (seen[seed] || bytes[seed] <= t) continue;
    let sp = 0, n = 0;
    const members = [];
    stack[sp++] = seed; seen[seed] = 1;
    while (sp > 0) {
      const cur = stack[--sp];
      members.push(cur); n++;
      const cy = (cur / w) | 0, cx = cur - cy * w;
      for (let k = 0; k < 4; k++) {
        const nx = cx + (k === 0 ? 1 : k === 1 ? -1 : 0);
        const ny = cy + (k === 2 ? 1 : k === 3 ? -1 : 0);
        if (nx < 0 || nx >= w || ny < 0 || ny >= h) continue;
        const np = ny * w + nx;
        if (seen[np] || bytes[np] <= t) continue;
        seen[np] = 1; stack[sp++] = np;
      }
    }
    if (n > bestN) { bestN = n; bestSet = members; }
  }

  if (!bestSet || bestN < w * h * 0.15) return { corners: null, score: 0, method: 'page' };

  /* 네 극점: x+y 최소=좌상, 최대=우하, x-y 최대=우상, 최소=좌하 */
  let tl = null, br = null, tr = null, bl = null;
  let minSum = Infinity, maxSum = -Infinity, minDif = Infinity, maxDif = -Infinity;
  for (const p of bestSet) {
    const y = (p / w) | 0, x = p - y * w;
    const s = x + y, d = x - y;
    if (s < minSum) { minSum = s; tl = { x, y }; }
    if (s > maxSum) { maxSum = s; br = { x, y }; }
    if (d > maxDif) { maxDif = d; tr = { x, y }; }
    if (d < minDif) { minDif = d; bl = { x, y }; }
  }

  const up = (p) => ({ x: (p.x + 0.5) * step, y: (p.y + 0.5) * step });
  const corners = [up(tl), up(tr), up(bl), up(br)];
  const score = quadScore(corners, W, H) * 0.85; // 마커보다는 덜 믿습니다
  if (score < 0.3) return { corners: null, score: 0, method: 'page' };
  return { corners, score, method: 'page' };
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

/** 마커 → 종이 테두리 → 전체 화면 순으로 시도합니다. */
export function detectQuad(canvas) {
  const img = imgData(canvas);
  const W = canvas.width, H = canvas.height;
  const g = toGray(img.data, W, H);

  const m = findMarkersGray(g, W, H);
  if (m.score >= 0.62) return m;

  const p = findPageQuadGray(g, W, H);
  if (p.corners && p.score > m.score) return p;
  if (m.score > 0) return m;

  return {
    corners: [
      { x: W * 0.05, y: H * 0.05 }, { x: W * 0.95, y: H * 0.05 },
      { x: W * 0.05, y: H * 0.95 }, { x: W * 0.95, y: H * 0.95 },
    ],
    score: 0,
    method: 'frame',
  };
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
export function warp(canvas, corners, outW = dpiToWidth(DEFAULT_DPI), inset = null) {
  const pts = orderCorners(corners);
  const top = Math.hypot(pts[1].x - pts[0].x, pts[1].y - pts[0].y);
  const left = Math.hypot(pts[2].x - pts[0].x, pts[2].y - pts[0].y);
  /* 가로로 누운 종이면 A4 가로로 냅니다 */
  const landscape = top > left * 1.12;
  const w = landscape ? Math.round(outW * A4_RATIO) : outW;
  const h = landscape ? outW : Math.round(outW * A4_RATIO);

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

/* 무거운 단계 사이에 한 틱 쉬어 화면이 얼지 않게 합니다 */
const breathe = () => new Promise((r) => setTimeout(r, 0));

/**
 * 사진 한 장을 답안지로 다듬습니다.
 *
 * @param {File|Blob} file
 * @param {{corners?, mode?, dpi?, onProgress?}} opts
 * @returns {{blob, previewUrl, corners, autoScore, method, quality, width, height, baseUrl, baseW, baseH}}
 */
export async function processShot(file, opts = {}) {
  const { corners = null, mode = 'clean', dpi = DEFAULT_DPI, onProgress } = opts;
  const say = (pct, label) => { try { onProgress?.(pct, label); } catch { /* 무시 */ } };

  say(5, '사진 읽는 중');
  const bmp = await loadBitmap(file);
  const base = toCanvas(bmp);
  try { bmp.close?.(); } catch { /* 무시 */ }
  await breathe();

  say(25, '모서리 찾는 중');
  let pts = corners ? orderCorners(corners) : null;
  let autoScore = 1, method = 'manual';
  if (!pts) {
    const d = detectQuad(base);
    pts = d.corners; autoScore = d.score; method = d.method;
  }
  await breathe();

  say(50, '기울기 펴는 중');
  /* 마커로 찾았을 때만 인셋을 씁니다. 종이 테두리로 찾았다면
     그 네 점이 곧 지면 모서리이므로 인셋이 필요 없습니다. */
  let out = warp(base, pts, dpiToWidth(dpi), method === 'marker' ? MARKER_INSET : null);
  await breathe();

  say(72, '그림자 지우는 중');
  out = enhance(out, mode);
  await breathe();

  say(90, '선명도 확인 중');
  const quality = inspect(out);

  const blob = await new Promise((r) =>
    mode === 'mono' ? out.toBlob(r, 'image/png') : out.toBlob(r, 'image/jpeg', 0.92)
  );
  say(100, '완료');

  return {
    blob: blob || file,
    previewUrl: out.toDataURL('image/jpeg', 0.6),
    corners: pts,
    autoScore,
    method,
    quality,
    width: out.width,
    height: out.height,
    baseUrl: base.toDataURL('image/jpeg', 0.65), // 모서리 조정 화면에서 씁니다
    baseW: base.width,
    baseH: base.height,
  };
}

/** 이미 잡아둔 원본에서 모서리·모드만 바꿔 다시 만듭니다 */
export async function reprocess(baseDataUrl, corners, mode = 'clean', dpi = DEFAULT_DPI, inset = null) {
  const img = await loadImage(baseDataUrl);
  const base = toCanvas(img);
  let out = warp(base, orderCorners(corners), dpiToWidth(dpi), inset);
  out = enhance(out, mode);
  const quality = inspect(out);
  const blob = await new Promise((r) =>
    mode === 'mono' ? out.toBlob(r, 'image/png') : out.toBlob(r, 'image/jpeg', 0.92)
  );
  return { blob, previewUrl: out.toDataURL('image/jpeg', 0.6), quality, width: out.width, height: out.height };
}
