/* HaslaLab naked-eye sky — the real sky over an observation site at a given night, for the observation rounds that
   are worked with the eyes and the hands only (IAO, APAO, IOAA Jr).  Stars to V 6.5 from skydata.js, the planets
   (JPL approximate elements), the Moon (Meeus, main terms) with its phase, atmospheric extinction and refraction,
   and the brightness of the sky from the night sky, the Moon (Krisciunas & Schaefer 1991) and the town; the faintest
   star the eye catches follows from it (Schaefer).  The view turns with the mouse; widening it does not magnify.
   Tools: look, point (what you show the examiner), trace (sweep the hand across the sky) and the hand held at
   arm's length (finger 1°, three fingers 5°, fist 10°, spread hand 20°).  overcast: true covers the sky with cloud.

   NightSky.astro  — the astronomy, usable alone
   NightSky.create({el, site: {lat, lon, tz, name}, start: [y, m, d, localHour], look: {az, alt, fov}, lang,
                    skyline(az) -> deg, ground: {sea: [az0, az1], lights: [[az, strength]]}, mags: [[ra, dec, V]],
                    tools: [..], overcast, onPoint(p), onTrace(points), drawOver(g, view)}) */
(function () {
  "use strict";
  const DEG = Math.PI / 180, norm360 = (a) => ((a % 360) + 360) % 360;
  /* ---------------------------------------------------------------- astronomy */
  function jdUT(y, m, d, h) { if (m <= 2) { y--; m += 12; } const A = Math.floor(y / 100), B = 2 - A + Math.floor(A / 4);
    return Math.floor(365.25 * (y + 4716)) + Math.floor(30.6001 * (m + 1)) + d + B - 1524.5 + h / 24; }
  const gmstDeg = (J) => { const T = (J - 2451545) / 36525; return norm360(280.46061837 + 360.98564736629 * (J - 2451545) + 0.000387933 * T * T); };
  const vec = (ra, dec) => [Math.cos(dec * DEG) * Math.cos(ra * DEG), Math.cos(dec * DEG) * Math.sin(ra * DEG), Math.sin(dec * DEG)];
  const radec = (v) => { const n = Math.hypot(v[0], v[1], v[2]); return [norm360(Math.atan2(v[1], v[0]) / DEG), Math.asin(v[2] / n) / DEG]; };
  const mv = (M, v) => [M[0][0] * v[0] + M[0][1] * v[1] + M[0][2] * v[2], M[1][0] * v[0] + M[1][1] * v[1] + M[1][2] * v[2], M[2][0] * v[0] + M[2][1] * v[1] + M[2][2] * v[2]];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const sep = (a, b) => Math.acos(Math.max(-1, Math.min(1, dot(a, b) / Math.hypot(...a) / Math.hypot(...b)))) / DEG;
  function precession(J) { const T = (J - 2451545) / 36525, as = DEG / 3600;
    const z = (2306.2181 * T + 1.09468 * T * T) * as, ze = (2306.2181 * T + 0.30188 * T * T) * as, th = (2004.3109 * T - 0.42665 * T * T) * as;
    const cz = Math.cos(z), sz = Math.sin(z), ce = Math.cos(ze), se = Math.sin(ze), ct = Math.cos(th), st = Math.sin(th);
    return [[cz * ct * ce - sz * se, -cz * ct * se - sz * ce, -cz * st], [sz * ct * ce + cz * se, -sz * ct * se + cz * ce, -sz * st], [st * ce, -st * se, ct]]; }
  const EPS = 23.4393 * DEG, ecl2eq = (v) => [v[0], v[1] * Math.cos(EPS) - v[2] * Math.sin(EPS), v[1] * Math.sin(EPS) + v[2] * Math.cos(EPS)];
  const ELEM = {
    mercury: [0.38709927, 0.00000037, 0.20563593, 0.00001906, 7.00497902, -0.00594749, 252.25032350, 149472.67411175, 77.45779628, 0.16047689, 48.33076593, -0.12534081],
    venus: [0.72333566, 0.00000390, 0.00677672, -0.00004107, 3.39467605, -0.00078890, 181.97909950, 58517.81538729, 131.60246718, 0.00268329, 76.67984255, -0.27769418],
    earth: [1.00000261, 0.00000562, 0.01671123, -0.00004392, -0.00001531, -0.01294668, 100.46457166, 35999.37244981, 102.93768193, 0.32327364, 0, 0],
    mars: [1.52371034, 0.00001847, 0.09339410, 0.00007882, 1.84969142, -0.00813131, -4.55343205, 19140.30268499, -23.94362959, 0.44441088, 49.55953891, -0.29257343],
    jupiter: [5.20288700, -0.00011607, 0.04838624, -0.00013253, 1.30439695, -0.00183714, 34.39644051, 3034.74612775, 14.72847983, 0.21252668, 100.47390909, 0.20469106],
    saturn: [9.53667594, -0.00125060, 0.05386179, -0.00050991, 2.48599187, 0.00193609, 49.95424423, 1222.49362201, 92.59887831, -0.41897216, 113.66242448, -0.28867794]};
  function helio(p, J) { const T = (J - 2451545) / 36525, E0 = ELEM[p], el = (i) => E0[2 * i] + E0[2 * i + 1] * T;
    const a = el(0), e = el(1), I = el(2) * DEG, L = el(3), w = el(4), O = el(5), om = (w - O) * DEG, M = norm360(L - w) * DEG; let E = M + e * Math.sin(M);
    for (let k = 0; k < 8; k++) E -= (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E));
    const xp = a * (Math.cos(E) - e), yp = a * Math.sqrt(1 - e * e) * Math.sin(E), Or = O * DEG, co = Math.cos(om), so = Math.sin(om), cO = Math.cos(Or), sO = Math.sin(Or), cI = Math.cos(I), sI = Math.sin(I);
    return [(co * cO - so * sO * cI) * xp + (-so * cO - co * sO * cI) * yp, (co * sO + so * cO * cI) * xp + (-so * sO + co * cO * cI) * yp, so * sI * xp + co * sI * yp]; }
  function planetGeo(p, J) { const e = helio("earth", J); let g = null, Jt = J;
    for (let k = 0; k < 2; k++) { const h = helio(p, Jt); g = [h[0] - e[0], h[1] - e[1], h[2] - e[2]]; Jt = J - Math.hypot(...g) * 0.0057755; }
    return ecl2eq(g); }
  function sunGeo(J) { const e = helio("earth", J); return ecl2eq([-e[0], -e[1], -e[2]]); }
  function moonGeo(J) { const T = (J - 2451545) / 36525;
    const Lp = norm360(218.3164477 + 481267.88123421 * T), D = norm360(297.8501921 + 445267.1114034 * T) * DEG, M = norm360(357.5291092 + 35999.0502909 * T) * DEG,
          Mp = norm360(134.9633964 + 477198.8675055 * T) * DEG, F = norm360(93.2720950 + 483202.0175233 * T) * DEG;
    const lon = Lp + 6.288774 * Math.sin(Mp) + 1.274027 * Math.sin(2 * D - Mp) + 0.658314 * Math.sin(2 * D) + 0.213618 * Math.sin(2 * Mp) - 0.185116 * Math.sin(M) - 0.114332 * Math.sin(2 * F)
              + 0.058793 * Math.sin(2 * D - 2 * Mp) + 0.057066 * Math.sin(2 * D - M - Mp) + 0.053322 * Math.sin(2 * D + Mp) + 0.045758 * Math.sin(2 * D - M);
    const lat = 5.128122 * Math.sin(F) + 0.280602 * Math.sin(Mp + F) + 0.277693 * Math.sin(Mp - F) + 0.173237 * Math.sin(2 * D - F) + 0.055413 * Math.sin(2 * D - Mp + F) + 0.046271 * Math.sin(2 * D - Mp - F);
    const km = 385000.56 - 20905.355 * Math.cos(Mp) - 3699.111 * Math.cos(2 * D - Mp) - 2955.968 * Math.cos(2 * D) - 569.925 * Math.cos(2 * Mp);
    return {v: ecl2eq(vec(lon - 1.396971 * T, lat)), km}; }
  /* topocentric Moon (parallax up to 1°): geocentric vector minus the observer, J2000 */
  function moonTopo(J, site) { const m = moonGeo(J), lst = norm360(gmstDeg(J) + site.lon), P = precession(J), R = 6378 / m.km;
    const o = vec(lst, site.lat), oJ = [P[0][0] * o[0] + P[1][0] * o[1] + P[2][0] * o[2], P[0][1] * o[0] + P[1][1] * o[1] + P[2][1] * o[2], P[0][2] * o[0] + P[1][2] * o[1] + P[2][2] * o[2]];
    const t = [m.v[0] - R * oJ[0], m.v[1] - R * oJ[1], m.v[2] - R * oJ[2]], n = Math.hypot(...t); return {v: t.map((x) => x / n), km: m.km * n}; }
  /* the rotation from J2000 equatorial to the local horizon (x east, y north, z up) */
  function horMatrix(J, site) { const P = precession(J), th = norm360(gmstDeg(J) + site.lon) * DEG, p = site.lat * DEG, c = Math.cos(th), s = Math.sin(th);
    const R = [[-s, c, 0], [-Math.sin(p) * c, -Math.sin(p) * s, Math.cos(p)], [Math.cos(p) * c, Math.cos(p) * s, Math.sin(p)]];
    const M = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]; for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) for (let k = 0; k < 3; k++) M[i][j] += R[i][k] * P[k][j]; return M; }
  const altaz = (h) => [Math.asin(Math.max(-1, Math.min(1, h[2]))) / DEG, norm360(Math.atan2(h[0], h[1]) / DEG)];
  const hvec = (alt, az) => [Math.sin(az * DEG) * Math.cos(alt * DEG), Math.cos(az * DEG) * Math.cos(alt * DEG), Math.sin(alt * DEG)];
  const refr = (a) => a > -2 ? 1.02 / Math.tan((a + 10.3 / (a + 5.11)) * DEG) / 60 : 0;
  const airmass = (a) => 1 / (Math.sin(Math.max(0.5, a) * DEG) + 0.50572 * Math.pow(Math.max(0.5, a) + 6.07995, -1.6364));
  /* spherical triangle area (deg²) from three unit vectors (L'Huilier through the solid angle) */
  function triArea(a, b, c) { const n = (v) => v.map((x) => x / Math.hypot(...v)); a = n(a); b = n(b); c = n(c);
    const cr = [b[1] * c[2] - b[2] * c[1], b[2] * c[0] - b[0] * c[2], b[0] * c[1] - b[1] * c[0]];
    const om = 2 * Math.atan2(Math.abs(dot(a, cr)), 1 + dot(a, b) + dot(b, c) + dot(c, a)); return om / DEG / DEG; }
  /* the brightness of the sky in nanolamberts: dark sky, moonlight (Krisciunas & Schaefer 1991), the town */
  const nL = (V) => 34.08 * Math.exp(20.7233 - 0.92104 * V), magOf = (B) => (20.7233 - Math.log(B / 34.08)) / 0.92104;
  function moonSky(rho, z, zm, phase, k) { if (zm >= 90) return 0; const I = Math.pow(10, -0.4 * (3.84 + 0.026 * Math.abs(phase) + 4e-9 * Math.pow(phase, 4)));
    const f = Math.pow(10, 5.36) * (1.06 + Math.cos(rho * DEG) ** 2) + Math.pow(10, 6.15 - Math.max(rho, 2) / 40), X = (zz) => 1 / Math.sqrt(1 - 0.96 * Math.sin(zz * DEG) ** 2);
    return f * I * Math.pow(10, -0.4 * k * X(zm)) * (1 - Math.pow(10, -0.4 * k * X(Math.min(z, 89.5)))); }
  const nelm = (q) => 7.93 - 5 * Math.log10(Math.pow(10, 4.316 - q / 5) + 1);
  const astro = {DEG, norm360, jdUT, gmstDeg, vec, radec, mv, dot, sep, precession, planetGeo, sunGeo, moonGeo, moonTopo, horMatrix, altaz, hvec, refr, airmass, triArea, nL, magOf, moonSky, nelm};
  let STARS = null;
  function stars() { if (STARS) return STARS; const D = window.SKY_DATA.stars, bin = atob(D.b64), n = D.n, X = new Float32Array(n * 3), M = new Float32Array(n), BV = new Float32Array(n);
    for (let i = 0; i < n; i++) { const o = i * 7, b = (j) => bin.charCodeAt(o + j), ra = (b(0) | b(1) << 8) / 180, de = ((b(2) | b(3) << 8) << 16 >> 16) / 360, m = ((b(4) | b(5) << 8) << 16 >> 16) / 100;
      const v = vec(ra, de); X[i * 3] = v[0]; X[i * 3 + 1] = v[1]; X[i * 3 + 2] = v[2]; M[i] = m; BV[i] = b(6) / 80 - 0.5; }
    return STARS = {n, X, M, BV}; }

  /* ---------------------------------------------------------------- the view */
  const T = {
    ko: {look: "둘러보기", point: "가리키기", trace: "손으로 그리기", hand: "손 재기", f1: "손가락 1°", f3: "세 손가락 5°", fist: "주먹 10°", span: "편 손 20°", wide: "시야", hint: "끌기: 둘러보기 / 휠: 시야 넓히기·좁히기(배율은 그대로) / 가리키기: 클릭한 곳을 시험관에게 가리킵니다 / 손으로 그리기: 끌어서 하늘에 손을 움직인 길을 그립니다 / 손 재기: 팔을 쭉 뻗은 손",
         dirs: ["북", "동", "남", "서"], local: "현지 시각"},
    en: {look: "Look", point: "Point", trace: "Trace by hand", hand: "Hand", f1: "Finger 1°", f3: "Three fingers 5°", fist: "Fist 10°", span: "Spread hand 20°", wide: "Field", hint: "Drag: look around / wheel: wider or narrower view (no magnification) / Point: show the examiner where you click / Trace: drag to sweep your hand across the sky / Hand: your hand at arm's length",
         dirs: ["N", "E", "S", "W"], local: "local time"}};
  const CSS = `.ns{display:flex;flex-direction:column;gap:6px}.ns-bar{display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.ns-bar button{height:30px;margin:0;padding:0 10px;border-radius:6px;border:1px solid #3a3f47;background:#2b2f36;color:#e8eef2;font:600 12.5px "Segoe UI","Malgun Gothic",sans-serif;cursor:pointer}
.ns-bar button.on{background:#f2c14e;border-color:#f2c14e;color:#1c2027}.ns-bar .sep{width:1px;height:20px;background:#3a3f47;margin:0 4px}
.ns-bar .clock{margin-left:auto;font:600 13px ui-monospace,Consolas,monospace;color:#f3d58a}
.ns-wrap{position:relative;border-radius:8px;overflow:hidden;background:#000;touch-action:none;cursor:grab}.ns-wrap canvas{display:block;width:100%}
.ns-hint{font-size:11.5px;color:#9aa3ab}`;
  let cssDone = false;

  function create(o) {
    if (!cssDone) { const s = document.createElement("style"); s.textContent = CSS; document.head.appendChild(s); cssDone = true; }
    const L = () => T[(o.lang && o.lang()) === "en" ? "en" : "ko"], site = o.site, S = stars();
    const root = document.createElement("div"); root.className = "ns";
    const bar = document.createElement("div"); bar.className = "ns-bar";
    const wrap = document.createElement("div"); wrap.className = "ns-wrap";
    const cv = document.createElement("canvas"); wrap.appendChild(cv);
    const hint = document.createElement("div"); hint.className = "ns-hint";
    root.append(bar, wrap, hint); o.el.appendChild(root);
    const g = cv.getContext("2d"), BG = document.createElement("canvas"); BG.width = 240; BG.height = 150; const bgx = BG.getContext("2d", {willReadFrequently: false});
    /* the sky background is computed on a coarse grid and scaled up: 240 × 150 at rest, half that while the view is being dragged */
    const BGF = bgx.createImageData(240, 150), BGH = bgx.createImageData(120, 75); let BGI = BGF;
    const view = {W: 900, H: 560, dpr: 1, az: o.look ? o.look.az : 90, alt: o.look ? o.look.alt : 30, fov: o.look ? o.look.fov : 90};
    const clock = {J0: jdUT(o.start[0], o.start[1], o.start[2], o.start[3] - site.tz), t0: performance.now(), off: 0, run: true};
    let tool = "look", hand = "fist", mouse = null, drag = null, raf = 0, solved = false;
    const K = 0.2;                                                          /* extinction, mag per air mass */
    /* individual magnitudes the examination gives (variable stars) */
    const OVR = new Map(); for (const [ra, de, m] of o.mags || []) { const v = vec(ra, de); let bi = -1, bd = 1; for (let i = 0; i < S.n; i++) { const d = 1 - (S.X[i * 3] * v[0] + S.X[i * 3 + 1] * v[1] + S.X[i * 3 + 2] * v[2]); if (d < bd) { bd = d; bi = i; } } if (bi >= 0) OVR.set(bi, m); }
    for (const [i, m] of OVR) S.M[i] = m;
    const J = () => clock.J0 + (clock.off + (clock.run ? (performance.now() - clock.t0) / 1000 : 0)) / 86400;
    function basis() { const a = view.az * DEG, h = view.alt * DEG, f = [Math.sin(a) * Math.cos(h), Math.cos(a) * Math.cos(h), Math.sin(h)], r = [Math.cos(a), -Math.sin(a), 0];
      const u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]; return {f, r, u, s: (view.W / 2) / (2 * Math.tan(view.fov / 4 * DEG))}; }
    function proj(B, x) { const X = dot(x, B.r), Y = dot(x, B.u), Z = dot(x, B.f); if (Z < -0.3) return null; const k = 2 * B.s / (1 + Z); return [view.W / 2 + X * k, view.H / 2 - Y * k]; }
    function unproj(B, px, py) { const X = (px - view.W / 2) / B.s, Y = -(py - view.H / 2) / B.s, r2 = X * X + Y * Y, d = 4 + r2, a = 4 * X / d, b = 4 * Y / d, c = (4 - r2) / d;
      return [a * B.r[0] + b * B.u[0] + c * B.f[0], a * B.r[1] + b * B.u[1] + c * B.f[1], a * B.r[2] + b * B.u[2] + c * B.f[2]]; }
    const skyline = o.skyline || (() => 0);
    /* the state of the sky at time J, recomputed every few seconds */
    let ST = null;
    function state(j) { if (ST && Math.abs(ST.J - j) < 3 / 86400) return ST;
      const HM = horMatrix(j, site), sun = sunGeo(j), su = sun.map((x) => x / Math.hypot(...sun)), mo = moonTopo(j, site), mh = mv(HM, mo.v);
      const phase = sep(mo.v, su.map((x) => -x)), sh = altaz(mv(HM, su)), [ma, mz] = altaz(mh);
      const PL = []; for (const p of ["venus", "mars", "jupiter", "saturn", "mercury"]) { const gq = planetGeo(p, j), u = gq.map((x) => x / Math.hypot(...gq)); PL.push({p, u, h: mv(HM, u)}); }
      return ST = {J: j, HM, moon: {v: mo.v, h: mh, alt: ma + refr(ma), az: mz, phase, km: mo.km, sun: mv(HM, su)}, sunAlt: sh[0], planets: PL}; }
    function skyB(alt, az, s) { const z = 90 - Math.max(0.3, alt), X = airmass(alt);
      let B = nL(21.7) * (0.6 + 0.4 * X) * Math.pow(10, -0.4 * K * (X - 1)) * 1.1;
      if (s.moon.alt > -1) { const rho = sep(hvec(alt, az), s.moon.h); B += moonSky(rho, z, 90 - Math.max(0.3, s.moon.alt), s.moon.phase, K); }
      for (const [A, str, hs] of (o.ground && o.ground.domes) || []) { const d = Math.abs(((az - A + 540) % 360) - 180); B += nL(21.7) * str * Math.exp(-Math.max(0.3, alt) / hs) * Math.exp(-((d / 40) ** 2)); }
      if (s.sunAlt > -18) B += nL(21.7) * 60 * Math.pow((s.sunAlt + 18) / 6, 3) * Math.exp(-alt / 30);
      return B; }
    const limAt = (alt, az, s) => nelm(magOf(skyB(alt, az, s))) - 0.3;
    /* an overcast sky: the cloud deck lit from below by the town, a little texture, no stars */
    const vn = (x, y) => { const h = (a, b) => { const n = Math.sin(a * 127.1 + b * 311.7) * 43758.5453; return n - Math.floor(n); }, X = Math.floor(x), Y = Math.floor(y), fx = x - X, fy = y - Y, u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy);
      return h(X, Y) * (1 - u) * (1 - v) + h(X + 1, Y) * u * (1 - v) + h(X, Y + 1) * (1 - u) * v + h(X + 1, Y + 1) * u * v; };
    function paintCloud(B) { const d = BGI.data, W = BGI.width, H = BGI.height, t = performance.now() / 60000;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const v = unproj(B, (x + 0.5) * view.W / W, (y + 0.5) * view.H / H), [alt, az] = altaz(v), i = (y * W + x) * 4;
        let glow = 0.18; for (const [A, str, hs] of (o.ground && o.ground.domes) || []) { const dd = Math.abs(((az - A + 540) % 360) - 180); glow += 0.5 * str * Math.exp(-Math.max(0.3, alt) / (hs * 2.5)) * Math.exp(-((dd / 60) ** 2)); }
        const r = 1 / Math.max(0.12, Math.sin(Math.max(1, alt) * DEG)), px = v[0] * r * 3 + t, py = v[1] * r * 3, tex = 0.55 * vn(px, py) + 0.3 * vn(px * 2.3, py * 2.3) + 0.15 * vn(px * 5, py * 5);
        const L = Math.min(1, glow * (0.75 + 0.5 * tex));
        d[i] = 14 + 70 * L; d[i + 1] = 13 + 58 * L; d[i + 2] = 16 + 50 * L; d[i + 3] = 255; }
      bgx.putImageData(BGI, 0, 0); }
    function paintBG(B, s) { if (o.overcast) return paintCloud(B); const d = BGI.data, W = BGI.width, H = BGI.height;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const v = unproj(B, (x + 0.5) * view.W / W, (y + 0.5) * view.H / H), [alt, az] = altaz(v); const i = (y * W + x) * 4;
        const q = magOf(skyB(Math.max(0.3, alt), az, s)), b = Math.max(0, Math.min(1, (22 - q) / 6.5)), lum = Math.pow(b, 1.6);
        const moonish = s.moon.alt > 0 ? Math.min(1, s.moon.phase < 90 ? 1 : 1.6 - s.moon.phase / 150) : 0;
        d[i] = 5 + 42 * lum * (1 - 0.3 * moonish) + 6 * lum; d[i + 1] = 7 + 56 * lum; d[i + 2] = 12 + 92 * lum * (0.75 + 0.25 * moonish); d[i + 3] = 255; }
      bgx.putImageData(BGI, 0, 0); }
    function bvRGB(bv) { const t = Math.max(-0.4, Math.min(2, bv)); let r, gg, b; if (t < 0.4) { r = 0.72 + 0.7 * (t + 0.4); gg = 0.8 + 0.4 * (t + 0.4); b = 1; } else { r = 1; gg = 1.05 - 0.28 * (t - 0.4); b = 1 - 0.45 * (t - 0.4); }
      return [Math.min(1, r), Math.min(1, gg), Math.max(0.35, Math.min(1, b))]; }
    const SPR = {};
    function sprite(bv) { const k = Math.round((Math.max(-0.4, Math.min(2, bv)) + 0.4) * 4); if (SPR[k]) return SPR[k];
      const c = document.createElement("canvas"); c.width = c.height = 32; const x = c.getContext("2d"), [r, gg, b] = bvRGB(k / 4 - 0.4).map((v) => Math.round(255 * (0.86 + (v - 0.86) * 0.7))), col = r + "," + gg + "," + b, gr = x.createRadialGradient(16, 16, 0, 16, 16, 16);
      gr.addColorStop(0, "rgba(" + col + ",1)"); gr.addColorStop(0.12, "rgba(" + col + ",0.9)"); gr.addColorStop(0.3, "rgba(" + col + ",0.3)"); gr.addColorStop(0.6, "rgba(" + col + ",0.05)"); gr.addColorStop(1, "rgba(" + col + ",0)");
      x.fillStyle = gr; x.fillRect(0, 0, 32, 32); return SPR[k] = c; }
    function point(x, y, d, bv) { if (d <= 0) return; const a = Math.min(1, 0.05 + 0.17 * d), sp = sprite(bv), s0 = 8 + Math.min(4, d * 0.6);
      g.globalAlpha = a; g.drawImage(sp, x - s0 / 2, y - s0 / 2, s0, s0);
      if (d > 3) { const s1 = Math.min(38, 10 + 4.5 * (d - 3)); g.globalAlpha = Math.min(0.4, 0.06 + 0.05 * (d - 3)); g.drawImage(sp, x - s1 / 2, y - s1 / 2, s1, s1); } g.globalAlpha = 1; }
    const tw = (i, X, t) => 2.5 * Math.log10(Math.max(0.3, 1 + Math.min(0.5, 0.05 * Math.pow(X, 1.5)) * Math.sin(t * (9 + (i % 7)) + i * 1.7) * Math.sin(t * (5.3 + (i % 5) * 0.6) + i * 0.37)));
    let bgKey = "", bgLow = false, LIMS = null, LIM = null, starKey = "", VIS = [];
    function draw() {
      const j = J(), s = state(j), B = basis(), t = performance.now() / 1000, W = view.W, H = view.H;
      g.setTransform(view.dpr, 0, 0, view.dpr, 0, 0);
      const vkey = view.az.toFixed(2) + "," + view.alt.toFixed(2) + "," + view.fov.toFixed(2) + "," + W + "," + H, key = vkey + "," + Math.floor(j * 1440), low = !!drag;
      if (key !== bgKey || low !== bgLow) { BGI = low ? BGH : BGF; paintBG(B, s); bgKey = key; bgLow = low; }
      g.imageSmoothingEnabled = true; g.drawImage(BG, 0, 0, BGI.width, BGI.height, 0, 0, W, H);
      if (!o.overcast) {
      g.globalCompositeOperation = "lighter";
      /* the naked-eye limit over the sky, on a 5° × 10° grid; it changes only with the sky's state (every few seconds) */
      if (LIMS !== s) { LIM = new Float32Array(36 * 18); for (let a = 0; a < 18; a++) for (let z = 0; z < 36; z++) LIM[a * 36 + z] = limAt(a * 5 + 2.5, z * 10 + 5, s); LIMS = s; starKey = ""; }
      /* under a bright sky the eye still sees a bright star as bright: the steps above the limit count for more */
      const bk = (alt, az) => Math.max(1, Math.min(2.4, 6.6 / Math.max(1, lim(alt, az))));
      const lim = (alt, az) => LIM[Math.min(17, Math.max(0, Math.floor(alt / 5))) * 36 + (Math.floor(norm360(az) / 10) % 36)];
      /* where each visible star lands on the screen changes only with the view and the sky's state; only the twinkle is per frame */
      const sk = vkey + "," + s.J;
      if (sk !== starKey) { VIS = [];
        for (let i = 0; i < S.n; i++) { const m = S.M[i]; if (m > 6.6) continue; const h = mv(s.HM, [S.X[i * 3], S.X[i * 3 + 1], S.X[i * 3 + 2]]); let [alt, az] = altaz(h); if (alt < -1) continue; alt += refr(alt);
          if (alt < skyline(az)) continue; const X = airmass(alt), dd = lim(alt, az) - (m + K * X); if (dd < -0.3) continue; const p = proj(B, hvec(alt, az)); if (!p || p[0] < -6 || p[0] > W + 6 || p[1] < -6 || p[1] > H + 6) continue;
          VIS.push([p[0], p[1], dd, X, bk(alt, az), i]); }
        starKey = sk; }
      for (const [x, y, dd, X, b, i] of VIS) { let d = (dd + tw(i, X, t)) * b; if (d < 0.25) { if (Math.sin(t * 0.9 + i * 2.71) * Math.sin(t * 0.37 + i * 1.13) < 0.3) continue; d = 0.25; } point(x, y, d, S.BV[i]); }
      for (const P of s.planets) { let [alt, az] = altaz(P.h); alt += refr(alt); if (alt < skyline(az)) continue; const p = proj(B, hvec(alt, az)); if (!p) continue;
        const m0 = {jupiter: -2.8, saturn: 0.6, mars: 1.2, venus: -4.0, mercury: 0}[P.p]; point(p[0], p[1], (lim(alt, az) - (m0 + K * airmass(alt))) * bk(alt, az), {jupiter: 0.85, saturn: 1.05, mars: 1.5, venus: 0.8, mercury: 0.9}[P.p]); }
      g.globalCompositeOperation = "source-over";
      /* the Moon with its phase */
      if (s.moon.alt > skyline(s.moon.az) - 0.5) { const p = proj(B, hvec(s.moon.alt, s.moon.az)); if (p) {
          const R = Math.max(3, 0.2595 * 384400 / s.moon.km * DEG * B.s), ps = proj(B, s.moon.sun), ang = ps ? Math.atan2(ps[1] - p[1], ps[0] - p[0]) : 0, k = Math.cos(s.moon.phase * DEG);
          const gl = g.createRadialGradient(p[0], p[1], R, p[0], p[1], R * 9); gl.addColorStop(0, "rgba(220,230,255,0.25)"); gl.addColorStop(1, "rgba(220,230,255,0)"); g.fillStyle = gl; g.beginPath(); g.arc(p[0], p[1], R * 9, 0, 7); g.fill();
          g.save(); g.translate(p[0], p[1]); g.rotate(ang); g.fillStyle = "rgba(40,44,56,0.9)"; g.beginPath(); g.arc(0, 0, R, 0, 7); g.fill();
          g.fillStyle = "#f6f2e2"; g.beginPath(); g.arc(0, 0, R, -Math.PI / 2, Math.PI / 2); g.ellipse(0, 0, Math.abs(k) * R, R, 0, Math.PI / 2, -Math.PI / 2, k < 0); g.fill(); g.restore(); } }
      }
      drawGround(B, s);
      if (o.drawOver) o.drawOver(g, {proj: (v) => proj(B, v), hor: (v) => { const h = mv(s.HM, v); let [a, z] = altaz(h); a += refr(a); return hvec(a, z); }, J: j, state: s, W, H, solved});
      for (const P of points) { const p = proj(B, P.h); if (!p) continue; g.strokeStyle = "rgba(255,90,70,0.9)"; g.lineWidth = 2; g.beginPath(); g.moveTo(W / 2, H + 10); g.lineTo(p[0], p[1]); g.stroke();
        g.fillStyle = "#ff5a46"; g.beginPath(); g.arc(p[0], p[1], 4, 0, 7); g.fill(); g.font = "bold 13px 'Segoe UI',sans-serif"; g.fillText(P.n, p[0] + 7, p[1] - 6); }
      for (const tr of traces.concat(cur ? [cur] : [])) drawTrace(B, tr);
      if (tool === "hand" && mouse) drawHand(B, mouse);
      clk.textContent = L().local + " " + timeStr(j); }
    function timeStr(j) { const h = ((j + 0.5 + site.tz / 24) % 1) * 24, hh = Math.floor(h), mm = Math.floor((h - hh) * 60), ss = Math.floor(((h - hh) * 60 - mm) * 60); return (hh < 10 ? "0" : "") + hh + ":" + (mm < 10 ? "0" : "") + mm + ":" + (ss < 10 ? "0" : "") + ss; }
    /* the horizon's outline on screen, found by walking down each column until the ground; it depends only on the view */
    let groundKey = "", groundTop = [];
    function drawGround(B, s) { const W = view.W, H = view.H, N = 180, gk = view.az.toFixed(2) + "," + view.alt.toFixed(2) + "," + view.fov.toFixed(2) + "," + W + "," + H;
      if (gk !== groundKey) { groundTop = []; groundKey = gk;
        for (let i = 0; i <= N; i++) { const x = i * W / N, v = unproj(B, x, H / 2), [, az] = altaz(v); let best = null;
          for (let y = -H; y < H * 2; y += 6) { const [a2, z2] = altaz(unproj(B, x, y)); if (a2 < skyline(z2)) { best = y; break; } } groundTop.push([x, best == null ? H * 2 : best, az]); } }
      const top = groundTop;
      const sea = o.ground && o.ground.sea, inSea = (az) => sea && ((sea[0] < sea[1]) ? az > sea[0] && az < sea[1] : az > sea[0] || az < sea[1]);
      g.beginPath(); g.moveTo(0, H * 3); for (const [x, y] of top) g.lineTo(x, Math.min(H * 3, y)); g.lineTo(W, H * 3); g.closePath();
      const gr = g.createLinearGradient(0, 0, 0, H); gr.addColorStop(0, "#07090c"); gr.addColorStop(1, "#020203"); g.fillStyle = gr; g.fill();
      if (sea) { g.save(); g.clip(); for (let i = 0; i < N; i++) if (inSea(top[i][2])) { const [x, y] = top[i]; const sg = g.createLinearGradient(0, y, 0, y + 60); sg.addColorStop(0, "rgba(60,70,90,0.35)"); sg.addColorStop(1, "rgba(20,24,32,0)"); g.fillStyle = sg; g.fillRect(x, y, W / N + 1, 60); } g.restore(); }
      for (const [A, str] of (o.ground && o.ground.lights) || []) { const p = proj(B, hvec(skyline(A) + 0.15, A)); if (!p) continue; for (let k = 0; k < str; k++) { const dx = (Math.sin(A * 7 + k * 3.1) * 0.5) * 30, c = k % 3 ? "rgba(255,200,120,0.85)" : "rgba(240,240,255,0.8)"; g.fillStyle = c; g.fillRect(p[0] + dx, p[1] + 1 + (k % 2), 1.5, 1.5); } }
      g.font = "600 13px 'Segoe UI',sans-serif"; g.textAlign = "center"; g.fillStyle = "rgba(242,193,78,0.75)";
      ["N", "E", "S", "W"].forEach((n, i) => { const p = proj(B, hvec(skyline(i * 90) - 2.5, i * 90)); if (p && p[0] > 0 && p[0] < W && p[1] < H + 20) g.fillText(L().dirs[i], p[0], Math.min(H - 6, p[1] + 14)); }); g.textAlign = "left"; }
    /* a hand at arm's length, seen from behind: its size is an angle on the sky */
    function drawHand(B, m) { const pxDeg = (a) => { const c = unproj(B, m[0], m[1]), q = proj(B, rot(c, a)); return q ? Math.hypot(q[0] - m[0], q[1] - m[1]) : a * B.s * DEG; };
      const rot = (v, a) => { const up = [0, 0, 1], e = [v[1] * up[2] - v[2] * up[1], v[2] * up[0] - v[0] * up[2], v[0] * up[1] - v[1] * up[0]], n = Math.hypot(...e) || 1, c = Math.cos(a * DEG), sn = Math.sin(a * DEG); return v.map((x, i) => x * c + e[i] / n * sn); };
      const w = {f1: 1, f3: 5, fist: 10, span: 20}[hand], s = pxDeg(w) / w, x = m[0], y = m[1];
      g.save(); g.translate(x, y); g.fillStyle = "rgba(14,12,12,0.93)"; g.strokeStyle = "rgba(242,193,78,0.8)"; g.lineWidth = 1.2;
      const R = (x0, y0, ww, hh, r) => { g.beginPath(); g.roundRect ? g.roundRect(x0, y0, ww, hh, r) : g.rect(x0, y0, ww, hh); g.fill(); g.stroke(); };
      if (hand === "f1") { R(-0.5 * s, -2.6 * s, s, 9 * s, 0.5 * s); }
      else if (hand === "f3") { for (let k = 0; k < 3; k++) R(-2.5 * s + k * 1.67 * s, -3.6 * s + (k === 1 ? -0.5 : 0) * s, 1.6 * s, 9 * s, 0.8 * s); R(-2.6 * s, 3 * s, 5.4 * s, 8 * s, 1.2 * s); }
      else if (hand === "fist") { R(-4.6 * s, 1.5 * s, 9.2 * s, 7 * s, 2 * s); R(-4.2 * s, 7.5 * s, 7.6 * s, 7 * s, 1.5 * s);
        for (let k = 0; k < 4; k++) R(-5 * s + k * 2.5 * s, -3.5 * s + (k === 1 || k === 2 ? -0.3 * s : 0.2 * s), 2.5 * s, 5.4 * s, 1.2 * s);
        g.save(); g.rotate(-0.25); R(-5.2 * s, 1.2 * s, 7.4 * s, 2.6 * s, 1.3 * s); g.restore(); }
      else { R(-4.5 * s, -2 * s, 13 * s, 11 * s, 3 * s); for (let k = 0; k < 4; k++) { g.save(); g.rotate((k - 1.5) * 0.12); R(-3.6 * s + k * 2.4 * s, -10 * s, 1.9 * s, 9 * s, 0.9 * s); g.restore(); }
        g.save(); g.rotate(-1.05); R(-3.5 * s, -14.5 * s, 2.2 * s, 8 * s, 1.1 * s); g.restore(); }
      g.restore(); g.font = "600 12px 'Segoe UI',sans-serif"; g.fillStyle = "#f2c14e"; g.textAlign = "center"; g.fillText(L()[hand], x, y - (hand === "span" ? 16 : hand === "f1" ? 4 : 5) * s - 10); g.textAlign = "left"; }
    const points = [], traces = []; let cur = null;
    /* a sweep of the hand across the sky, with arrowheads along it to show the direction */
    function drawTrace(B, tr) { const P = tr.pts.map((h) => proj(B, h)); g.strokeStyle = tr.col || "rgba(120,220,255,0.95)"; g.fillStyle = g.strokeStyle; g.lineWidth = 2.5; g.lineCap = g.lineJoin = "round";
      g.beginPath(); let on = false; for (const p of P) { if (!p) { on = false; continue; } on ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]); on = true; } g.stroke();
      let acc = 0; for (let i = 1; i < P.length; i++) { const a = P[i - 1], b = P[i]; if (!a || !b) continue; const l = Math.hypot(b[0] - a[0], b[1] - a[1]); acc += l;
        if (acc > 70 && l > 0.5) { acc = 0; const ux = (b[0] - a[0]) / l, uy = (b[1] - a[1]) / l; g.beginPath(); g.moveTo(b[0] + ux * 6, b[1] + uy * 6); g.lineTo(b[0] - ux * 6 - uy * 6, b[1] - uy * 6 + ux * 6); g.lineTo(b[0] - ux * 6 + uy * 6, b[1] - uy * 6 - ux * 6); g.closePath(); g.fill(); } }
      if (tr.label && P.length && P[0]) { g.font = "bold 13px 'Segoe UI',sans-serif"; g.fillText(tr.label, P[0][0] + 8, P[0][1] - 8); } }
    function layout() { const w = wrap.clientWidth || 900; view.dpr = Math.min(window.devicePixelRatio || 1, 2); view.W = w; view.H = Math.round(Math.min(w * 0.62, Math.max(380, innerHeight - 220)));
      cv.width = Math.round(view.W * view.dpr); cv.height = Math.round(view.H * view.dpr); cv.style.height = view.H + "px"; bgKey = ""; starKey = ""; groundKey = ""; }
    function buildBar() { const t = L(); bar.innerHTML = "";
      const mk = (lab, on, fn) => { const b = document.createElement("button"); b.textContent = lab; if (on) b.className = "on"; b.onclick = fn; bar.appendChild(b); return b; };
      for (const k of o.tools || ["look", "point", "hand"]) mk(t[k], tool === k, () => setTool(k));
      if (tool === "hand") { const s = document.createElement("span"); s.className = "sep"; bar.appendChild(s); for (const k of ["f1", "f3", "fist", "span"]) mk(t[k], hand === k, () => { hand = k; buildBar(); }); }
      bar.appendChild(clk); hint.textContent = t.hint; }
    const clk = document.createElement("span"); clk.className = "clock";
    function setTool(k) { tool = k; wrap.style.cursor = k === "look" ? "grab" : k === "point" || k === "trace" ? "crosshair" : "none"; buildBar(); }
    const pos = (e) => { const r = cv.getBoundingClientRect(); return [(e.clientX - r.left) * view.W / r.width, (e.clientY - r.top) * view.H / r.height]; };
    cv.addEventListener("pointerdown", (e) => { const p = pos(e); cv.setPointerCapture(e.pointerId);
      if (tool === "point" && e.button === 0) { const B = basis(), h = unproj(B, p[0], p[1]); if (o.onPoint) o.onPoint({h, eq: horToEq(h)}); return; }
      if (tool === "trace" && e.button === 0) { cur = {pts: [unproj(basis(), p[0], p[1])]}; return; }
      drag = {p, az: view.az, alt: view.alt}; if (tool === "look") wrap.style.cursor = "grabbing"; });
    cv.addEventListener("pointermove", (e) => { const p = pos(e); mouse = p;
      if (cur) { const h = unproj(basis(), p[0], p[1]), last = cur.pts[cur.pts.length - 1]; if (dot(h, last) < Math.cos(0.8 * DEG)) cur.pts.push(h); return; }
      if (!drag) return; const k = view.fov / view.W;
      view.az = norm360(drag.az - (p[0] - drag.p[0]) * k); view.alt = Math.max(-5, Math.min(90, drag.alt + (p[1] - drag.p[1]) * k)); });
    cv.addEventListener("pointerup", () => { if (cur) { const c = cur; cur = null; if (c.pts.length > 2 && o.onTrace) o.onTrace(c.pts); } drag = null; if (tool === "look") wrap.style.cursor = "grab"; });
    cv.addEventListener("pointerleave", () => { mouse = null; });
    cv.addEventListener("wheel", (e) => { e.preventDefault(); view.fov = Math.max(50, Math.min(130, view.fov * (e.deltaY > 0 ? 1.08 : 1 / 1.08))); }, {passive: false});
    /* the inverse of the horizon rotation: a direction in the local sky -> J2000, for checking what was pointed at */
    function horToEq(h) { const s = state(J()), M = s.HM; return [M[0][0] * h[0] + M[1][0] * h[1] + M[2][0] * h[2], M[0][1] * h[0] + M[1][1] * h[1] + M[2][1] * h[2], M[0][2] * h[0] + M[1][2] * h[1] + M[2][2] * h[2]]; }
    function loop() { try { draw(); } catch (err) { console.error(err); } raf = requestAnimationFrame(loop); }
    addEventListener("resize", layout); layout(); buildBar(); loop();
    return {J, state: () => state(J()), view, lang: buildBar, setPoints(list) { points.length = 0; for (const p of list) points.push(p); }, setTraces(list) { traces.length = 0; for (const t of list) traces.push(t); }, horToEq,
      solve(v) { solved = v; }, setTime(localHour) { clock.J0 = jdUT(o.start[0], o.start[1], o.start[2], localHour - site.tz); clock.t0 = performance.now(); clock.off = 0; ST = null; },
      show(v) { root.style.display = v ? "" : "none"; if (v) layout(); }};
  }
  window.NightSky = {create, astro};
})();
