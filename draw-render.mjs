/* Draws a scene (draw-scene.mjs) as an exam figure: black lines on white, hatched floors and walls, serif labels with
   subscripts. The same SVG text is the editor's canvas (with ids to pick objects, a grid and the selection), the file
   that is downloaded, the picture put on a test paper (teach.js) and the frame of a running simulation (with the bodies
   where the solver has them, their trails and the forces on them). Labels are written in a small part of TeX
   (texRuns): m_1, v_0^2, \theta, \mu, \vec{F}, \frac{a}{b}, $…$; the SVG keeps no fonts or scripts of its own. */
import {isBody, bodyPose, surfaceFrame, inclineCorners, attachPoint, anchorPoint, stringPath, vec} from './draw-scene.mjs?v=821b2b258cf0';

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const f = n => (Math.round(n * 100) / 100).toString();
const GREEK = {alpha: 'α', beta: 'β', gamma: 'γ', delta: 'δ', epsilon: 'ε', varepsilon: 'ε', zeta: 'ζ', eta: 'η', theta: 'θ', vartheta: 'ϑ', iota: 'ι', kappa: 'κ',
  lambda: 'λ', mu: 'μ', nu: 'ν', xi: 'ξ', pi: 'π', rho: 'ρ', sigma: 'σ', tau: 'τ', phi: 'φ', varphi: 'φ', chi: 'χ', psi: 'ψ', omega: 'ω',
  Gamma: 'Γ', Delta: 'Δ', Theta: 'Θ', Lambda: 'Λ', Xi: 'Ξ', Pi: 'Π', Sigma: 'Σ', Phi: 'Φ', Psi: 'Ψ', Omega: 'Ω',
  circ: '°', degree: '°', cdot: '·', times: '×', pm: '±', approx: '≈', le: '≤', ge: '≥', leq: '≤', geq: '≥', neq: '≠', to: '→', infty: '∞', ell: 'ℓ', parallel: '∥', perp: '⊥', propto: '∝'};

/** A label as runs of text: [{t, it (italic), sh ('' | 'sub' | 'sup')}]. Inside $…$ every Latin letter is italic; a
 *  label without $ and without Hangul is read as maths too, but there only a single letter is italic ("2 kg" stays
 *  upright, "m_1" is an italic m). */
export function texRuns(src) {
  const text = String(src ?? '');
  const parts = text.includes('$') ? text.split('$').map((t, i) => ({t, math: i % 2 === 1, all: true})) : [{t: text, math: !/[가-힣]/.test(text), all: false}];
  const runs = [];
  const push = (t, it, sh) => { if (!t) return; const last = runs[runs.length - 1]; if (last && last.it === it && last.sh === sh) last.t += t; else runs.push({t, it, sh}); };
  for (const part of parts) {
    const s = part.t;
    const emit = (str, sh) => {
      /* a plain piece: letters italic in maths (a run of letters only when it is one letter, outside $…$) */
      const re = /[A-Za-z]+|[^A-Za-z]+/g; let m;
      while ((m = re.exec(str))) { const w = m[0], letters = /^[A-Za-z]/.test(w); push(w, part.math && letters && (part.all || w.length === 1), sh); }
    };
    const walk = (str, sh) => {
      let k = 0;
      while (k < str.length) {
        const c = str[k];
        if (c === '\\') {
          const m = /^\\([A-Za-z]+|.)/.exec(str.slice(k)); const name = m ? m[1] : ''; k += m ? m[0].length : 1;
          const arg = () => { if (str[k] === '{') { let depth = 1, j = k + 1; while (j < str.length && depth) { if (str[j] === '{') depth++; else if (str[j] === '}') depth--; j++; } const g = str.slice(k + 1, j - 1); k = j; return g; } return str[k++] || ''; };
          if (GREEK[name]) push(GREEK[name], false, sh);
          else if (name === 'vec') { walk(arg(), sh); push('⃗', false, sh); }
          else if (name === 'hat') { walk(arg(), sh); push('̂', false, sh); }
          else if (name === 'bar' || name === 'overline') { walk(arg(), sh); push('̄', false, sh); }
          else if (name === 'frac') { const a = arg(), b = arg(); walk(a, sh); push('/', false, sh); walk(b, sh); }
          else if (name === 'sqrt') { push('√', false, sh); walk(arg(), sh); }
          else if (name === 'text' || name === 'mathrm' || name === 'rm') push(arg(), false, sh);
          else if (name === ',' || name === ';' || name === ' ' || name === 'quad') push(' ', false, sh);
          else if (name === '%' || name === '$' || name === '{' || name === '}' || name === '_') push(name, false, sh);
          else push(name, false, sh);
        } else if ((c === '_' || c === '^') && !sh) {
          k++;
          let g;
          if (str[k] === '{') { let depth = 1, j = k + 1; while (j < str.length && depth) { if (str[j] === '{') depth++; else if (str[j] === '}') depth--; j++; } g = str.slice(k + 1, j - 1); k = j; }
          else if (str[k] === '\\') { const m = /^\\([A-Za-z]+|.)/.exec(str.slice(k)); g = m ? m[0] : ''; k += g.length; }
          else g = str[k++] || '';
          walk(g, c === '_' ? 'sub' : 'sup');
        } else if (c === '{' || c === '}') k++;
        else { let j = k; while (j < str.length && !'\\_^{}'.includes(str[j])) j++; if (j === k) j = k + 1; emit(str.slice(k, j), sh); k = j; }
      }
    };
    walk(s, '');
  }
  return runs;
}
const FONT = `'Times New Roman','STIX Two Text','Noto Serif KR','Nanum Myeongjo',serif`;
/** an SVG <text> of a label at (x, y) px, anchored 'start' | 'middle' | 'end', its middle on y */
export function texText(src, x, y, size = 16, anchor = 'middle', extra = '') {
  const runs = texRuns(src);
  if (!runs.length) return '';
  let dy = 0, body = '';
  for (const r of runs) {
    const target = r.sh === 'sub' ? 0.32 * size : r.sh === 'sup' ? -0.42 * size : 0;
    const shift = target - dy; dy = target;
    body += `<tspan${shift ? ` dy="${f(shift)}"` : ''}${r.sh ? ` font-size="${f(size * 0.7)}"` : ''}${r.it ? ' font-style="italic"' : ''}>${esc(r.t)}</tspan>`;
  }
  return `<text x="${f(x)}" y="${f(y + size * 0.34)}" font-size="${f(size)}" text-anchor="${anchor}" font-family="${FONT}" fill="#000"${extra}>${body}</text>`;
}

const FORCE_LABEL = {gravity: '$mg$', normal: '$N$', friction: '$f$', tension: '$T$', spring: '$F_s$', applied: '$F$'};
/** The scene as SVG text. opts: width (px of the drawing, 800), view (the world rectangle; else scene.view),
 *  edit (ids on the objects, a grid when grid, the selected id), forces (map body → [{kind, v, at}]),
 *  trails (map body → [{x,y}]), anchors (map 'spring:end' → point), conical (list of {centre, radius}), background. */
export function renderSVG(scene, opts = {}) {
  const W = opts.width || 800, view = opts.view || scene.view || {x: -0.5, y: -0.5, w: 4, h: 3};
  const S = W / view.w, H = Math.max(40, Math.round(view.h * S));
  const X = x => (x - view.x) * S, Y = y => (view.y + view.h - y) * S, P = p => `${f(X(p.x))},${f(Y(p.y))}`;
  const byId = new Map(scene.objects.map(o => [o.id, o]));
  const edit = !!opts.edit, sel = opts.selected || '';
  const out = [];
  const ink = '#000', lw = 1.7, thin = 1.15;
  const group = (o, inner) => edit ? `<g data-id="${esc(o.id)}" class="obj${o.id === sel ? ' sel' : ''}">${inner}</g>` : inner;
  const hit = d => edit ? `<path d="${d}" fill="none" stroke="transparent" stroke-width="12" pointer-events="stroke"/>` : '';
  const hatch = (x1, y1, x2, y2, nx, ny) => {
    /* short slanted strokes on the solid side (nx, ny: the side, in screen px) of the line from (x1,y1) to (x2,y2) */
    const L = Math.hypot(x2 - x1, y2 - y1), n = Math.max(1, Math.floor(L / 9)), ux = (x2 - x1) / L, uy = (y2 - y1) / L;
    let d = '';
    for (let i = 0; i <= n; i++) { const px = x1 + ux * (i * L / n), py = y1 + uy * (i * L / n); d += `M${f(px)},${f(py)}l${f(nx * 7 - ux * 6)},${f(ny * 7 - uy * 6)}`; }
    return `<path d="${d}" stroke="${ink}" stroke-width="0.9" fill="none"/>`;
  };
  const arrow = (from, to, {color = ink, width = 1.6, head = 9} = {}) => {
    const dx = to.x - from.x, dy = to.y - from.y, L = Math.hypot(dx, dy);
    if (L < 1) return '';
    const ux = dx / L, uy = dy / L, hb = {x: to.x - ux * head, y: to.y - uy * head};
    return `<line x1="${f(from.x)}" y1="${f(from.y)}" x2="${f(hb.x + ux * 1)}" y2="${f(hb.y + uy * 1)}" stroke="${color}" stroke-width="${width}"/>`
      + `<path d="M${f(to.x)},${f(to.y)}L${f(hb.x - uy * head * 0.38)},${f(hb.y + ux * head * 0.38)}L${f(hb.x + uy * head * 0.38)},${f(hb.y - ux * head * 0.38)}Z" fill="${color}"/>`;
  };
  const screen = p => ({x: X(p.x), y: Y(p.y)});
  const poseOf = o => isBody(o) ? bodyPose(scene, o) : {x: o.x, y: o.y, angle: 0};

  if (opts.background !== null) out.push(`<rect x="0" y="0" width="${W}" height="${H}" fill="${opts.background || '#fff'}"/>`);
  if (edit && opts.grid) {
    const g = scene.grid || 0.1; let step = g; while (step * S < 9) step *= 2;
    let d = '';
    for (let x = Math.ceil(view.x / step) * step; x <= view.x + view.w; x += step) d += `M${f(X(x))},0V${H}`;
    for (let y = Math.ceil(view.y / step) * step; y <= view.y + view.h; y += step) d += `M0,${f(Y(y))}H${W}`;
    out.push(`<path d="${d}" stroke="#d9dee8" stroke-width="0.6" fill="none" class="grid"/>`);
    const o = {x: X(0), y: Y(0)}; if (o.x >= 0 && o.x <= W && o.y >= 0 && o.y <= H) out.push(`<circle cx="${f(o.x)}" cy="${f(o.y)}" r="2.2" fill="#9aa3b5"/>`);
  }
  /* trails first, under everything */
  for (const [id, pts] of opts.trails || []) if (pts.length > 1) out.push(`<polyline points="${pts.map(p => P(p)).join(' ')}" fill="none" stroke="#666" stroke-width="1" stroke-dasharray="4 3" data-trail="${esc(id)}"/>`);
  for (const c of opts.conical || []) out.push(`<ellipse cx="${f(X(c.centre.x))}" cy="${f(Y(c.centre.y))}" rx="${f(c.radius * S)}" ry="${f(c.radius * S * 0.22)}" fill="none" stroke="#555" stroke-width="1" stroke-dasharray="5 4"/>`);

  /* order: surfaces, connections, bodies, marks (so a string ends under the block it pulls) */
  const rank = o => ({floor: 0, ceiling: 0, wall: 0, incline: 1, line: 2, pulley: 4, pivot: 4, string: 3, rod: 3, spring: 3, block: 5, ball: 5, force: 6, label: 7, dim: 7, arc: 7, axes: 2}[o.type] ?? 8);
  const order = [...scene.objects].sort((a, b) => rank(a) - rank(b));
  for (const o of order) {
    let s = '';
    if (o.type === 'floor') {
      const a = screen(o), b = screen({x: o.x + o.w, y: o.y});
      s = `<line x1="${f(a.x)}" y1="${f(a.y)}" x2="${f(b.x)}" y2="${f(b.y)}" stroke="${ink}" stroke-width="${lw}"/>${o.hatch ? hatch(a.x, a.y, b.x, b.y, 0, 1) : ''}${hit(`M${f(a.x)},${f(a.y)}H${f(b.x)}`)}`;
    } else if (o.type === 'ceiling') {
      const a = screen(o), b = screen({x: o.x + o.w, y: o.y});
      s = `<line x1="${f(a.x)}" y1="${f(a.y)}" x2="${f(b.x)}" y2="${f(b.y)}" stroke="${ink}" stroke-width="${lw}"/>${o.hatch ? hatch(a.x, a.y, b.x, b.y, 0, -1) : ''}${hit(`M${f(a.x)},${f(a.y)}H${f(b.x)}`)}`;
    } else if (o.type === 'wall') {
      const a = screen(o), b = screen({x: o.x, y: o.y + o.h}), side = o.side === 'left' ? -1 : 1;
      s = `<line x1="${f(a.x)}" y1="${f(a.y)}" x2="${f(b.x)}" y2="${f(b.y)}" stroke="${ink}" stroke-width="${lw}"/>${hatch(b.x, b.y, a.x, a.y, side, 0)}${hit(`M${f(a.x)},${f(a.y)}V${f(b.y)}`)}`;
    } else if (o.type === 'incline') {
      const c = inclineCorners(o), foot = screen(c.foot), top = screen(c.top), right = screen(c.right);
      s = `<path d="M${f(foot.x)},${f(foot.y)}L${f(top.x)},${f(top.y)}L${f(right.x)},${f(right.y)}Z" fill="#fff" stroke="${ink}" stroke-width="${lw}" stroke-linejoin="round"/>`;
      if (o.angleLabel) {
        const r = Math.min(34, 0.35 * Math.hypot(right.x - foot.x, right.y - foot.y)), th = o.angle * Math.PI / 180, dir = o.flip ? -1 : 1;
        const p1 = {x: foot.x + dir * r, y: foot.y}, p2 = {x: foot.x + dir * r * Math.cos(th), y: foot.y - r * Math.sin(th)};
        const mid = {x: foot.x + dir * (r + 13) * Math.cos(th / 2), y: foot.y - (r + 13) * Math.sin(th / 2)};
        s += `<path d="M${f(p1.x)},${f(p1.y)}A${f(r)},${f(r)} 0 0 ${o.flip ? 1 : 0} ${f(p2.x)},${f(p2.y)}" fill="none" stroke="${ink}" stroke-width="1"/>${texText(o.angleLabel, mid.x + dir * 4, mid.y, 15)}`;
      }
    } else if (o.type === 'pulley') {
      const c = screen(o), r = o.r * S, m = byId.get(o.mount);
      if (m) {
        let to = null;
        if (m.type === 'ceiling') to = {x: o.x, y: m.y};
        else if (m.type === 'incline') to = inclineCorners(m).top;
        else if (m.type === 'floor') to = {x: Math.abs(o.x - m.x) < Math.abs(o.x - m.x - m.w) ? m.x : m.x + m.w, y: m.y};
        else if (m.type === 'wall') to = {x: m.x, y: o.y};
        if (to) { const t = screen(to); s += `<line x1="${f(c.x)}" y1="${f(c.y)}" x2="${f(t.x)}" y2="${f(t.y)}" stroke="${ink}" stroke-width="2.2"/>`; }
      }
      s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r)}" fill="#fff" stroke="${ink}" stroke-width="${lw}"/><circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(Math.max(1.6, r * 0.14))}" fill="${ink}"/>`;
    } else if (o.type === 'pivot') {
      const c = screen(o), onCeiling = scene.objects.some(x => x.type === 'ceiling' && Math.abs(x.y - o.y) < 0.02 && o.x >= x.x && o.x <= x.x + x.w);
      if (!onCeiling) s += `<line x1="${f(c.x - 13)}" y1="${f(c.y - 7)}" x2="${f(c.x + 13)}" y2="${f(c.y - 7)}" stroke="${ink}" stroke-width="${lw}"/>${hatch(c.x - 13, c.y - 7, c.x + 13, c.y - 7, 0, -1)}<line x1="${f(c.x)}" y1="${f(c.y - 7)}" x2="${f(c.x)}" y2="${f(c.y)}" stroke="${ink}" stroke-width="1.4"/>`;
      s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="3.2" fill="#fff" stroke="${ink}" stroke-width="1.4"/>`;
    } else if (o.type === 'string') {
      const path = stringPath(scene, o, opts.poses);
      if (path) {
        let d = '';
        path.segs.forEach((sg, i) => {
          d += `M${P(sg[0])}L${P(sg[1])}`;
          const w = path.wraps[i];
          if (w && i < path.wraps.length + 1 && path.wraps[i]) {
            const a0 = Math.atan2(w.from.y - w.c.y, w.from.x - w.c.x), a1 = Math.atan2(w.to.y - w.c.y, w.to.x - w.c.x);
            let sweep = w.s > 0 ? a1 - a0 : a0 - a1; while (sweep < 0) sweep += 2 * Math.PI;
            d += `M${P(w.from)}A${f(w.r * S)},${f(w.r * S)} 0 ${sweep > Math.PI ? 1 : 0} ${w.s > 0 ? 0 : 1} ${P(w.to)}`;
          }
        });
        s = `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${thin}"/>${hit(d)}`;
        if (o.label && path.segs.length === 1) { const a = screen(path.segs[0][0]), b = screen(path.segs[0][1]), n = vec.unit({x: -(b.y - a.y), y: b.x - a.x}); s += texText(o.label, (a.x + b.x) / 2 + n.x * 13, (a.y + b.y) / 2 + n.y * 13, 15); }
      }
    } else if (o.type === 'rod') {
      const A = byId.get(o.a), B = byId.get(o.b);
      if (A && B) { const a = screen(poseOf(A)), b = screen(opts.poses?.get?.(B.id) || poseOf(B)); s = `<line x1="${f(a.x)}" y1="${f(a.y)}" x2="${f(b.x)}" y2="${f(b.y)}" stroke="${ink}" stroke-width="3.2" stroke-linecap="round"/>${hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`)}`;
        if (o.label) { const n = vec.unit({x: -(b.y - a.y), y: b.x - a.x}); s += texText(o.label, (a.x + b.x) / 2 + n.x * 14, (a.y + b.y) / 2 + n.y * 14, 15); } }
    } else if (o.type === 'spring') {
      const A = byId.get(o.a), B = byId.get(o.b);
      if (A && B) {
        const pose = x => opts.poses?.get?.(x.id) || poseOf(x);
        const end = (me, other) => {
          if (isBody(me)) return attachPoint(scene, me, isBody(other) ? pose(other) : anchorPoint(other, pose(me)), pose(me));
          return opts.anchors?.get?.(o.id + ':' + me.id) || anchorPoint(me, isBody(other) ? attachPoint(scene, other, pose(other), pose(other)) : {x: other.x, y: other.y});
        };
        const a = screen(end(A, B)), b = screen(end(B, A)), L = Math.hypot(b.x - a.x, b.y - a.y);
        if (L > 2) {
          const ux = (b.x - a.x) / L, uy = (b.y - a.y) / L, lead = Math.min(12, L * 0.15), n = Math.round(o.coils) * 2, amp = 6.5;
          let d = `M${f(a.x)},${f(a.y)}l${f(ux * lead)},${f(uy * lead)}`;
          const seg = (L - 2 * lead) / n;
          for (let i = 0; i < n; i++) { const t = lead + seg * (i + 0.5), side = i % 2 ? -1 : 1; d += `L${f(a.x + ux * t - uy * amp * side)},${f(a.y + uy * t + ux * amp * side)}`; }
          d += `L${f(b.x - ux * lead)},${f(b.y - uy * lead)}L${f(b.x)},${f(b.y)}`;
          s = `<path d="${d}" fill="none" stroke="${ink}" stroke-width="1.3" stroke-linejoin="round"/>${hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`)}`;
          /* the label beside the middle: above a lying spring, right of a standing one */
          if (o.label) { let nx = -uy, ny = ux; if (Math.abs(uy) > 0.7 ? nx < 0 : ny > 0) { nx = -nx; ny = -ny; } s += texText(o.label, (a.x + b.x) / 2 + nx * 20, (a.y + b.y) / 2 + ny * 20, 15); }
        }
      }
    } else if (o.type === 'block') {
      const p = poseOf(o), ca = Math.cos(p.angle), sa = Math.sin(p.angle), hw = o.w / 2, hh = o.h / 2;
      const pts = [[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]].map(([u, v]) => P({x: p.x + u * ca - v * sa, y: p.y + u * sa + v * ca}));
      const c = screen(p);
      s = `<polygon points="${pts.join(' ')}" fill="#fff" stroke="${ink}" stroke-width="${lw}" stroke-linejoin="round"/>${o.label ? texText(o.label, c.x, c.y, Math.max(11, Math.min(17, Math.min(o.w, o.h) * S * 0.45))) : ''}`;
    } else if (o.type === 'ball') {
      const p = poseOf(o), c = screen(p), r = o.r * S;
      s = `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(Math.max(2.5, r))}" fill="#fff" stroke="${ink}" stroke-width="${lw}"/>`;
      if (o.label) s += r >= 13 ? texText(o.label, c.x, c.y, Math.min(16, r * 0.9)) : texText(o.label, c.x + r + 5, c.y - r - 6, 15, 'start');
    } else if (o.type === 'force') {
      const b = byId.get(o.on);
      if (b) { const p = screen(opts.poses?.get?.(b.id) || poseOf(b)), th = o.angle * Math.PI / 180, L = o.len * S, tip = {x: p.x + Math.cos(th) * L, y: p.y - Math.sin(th) * L};
        s = arrow(p, tip, {width: 1.8, head: 10}) + (o.label ? texText(o.label, tip.x + Math.cos(th) * 12, tip.y - Math.sin(th) * 12, 16) : '') + hit(`M${f(p.x)},${f(p.y)}L${f(tip.x)},${f(tip.y)}`); }
    } else if (o.type === 'label') {
      const c = screen(o); s = texText(o.text || (edit ? '…' : ''), c.x, c.y, o.size) + (edit ? `<rect x="${f(c.x - 14)}" y="${f(c.y - 12)}" width="28" height="24" fill="transparent"/>` : '');
    } else if (o.type === 'dim') {
      const a = screen({x: o.x1, y: o.y1}), b = screen({x: o.x2, y: o.y2}), L = Math.hypot(b.x - a.x, b.y - a.y);
      if (L > 1) {
        const nx = -(b.y - a.y) / L, ny = (b.x - a.x) / L, off = -o.offset * S, a2 = {x: a.x + nx * off, y: a.y + ny * off}, b2 = {x: b.x + nx * off, y: b.y + ny * off};
        const ext = (p, q) => `<line x1="${f(p.x)}" y1="${f(p.y)}" x2="${f(q.x + nx * Math.sign(off) * 4)}" y2="${f(q.y + ny * Math.sign(off) * 4)}" stroke="${ink}" stroke-width="0.8"/>`;
        const m = {x: (a2.x + b2.x) / 2, y: (a2.y + b2.y) / 2};
        s = ext(a, a2) + ext(b, b2) + arrow(m, a2, {width: 1, head: 7}) + arrow(m, b2, {width: 1, head: 7}) + (o.text ? `<rect x="${f(m.x - 3 - o.text.length * 4.2)}" y="${f(m.y - 9)}" width="${f(6 + o.text.length * 8.4)}" height="18" fill="#fff"/>` + texText(o.text, m.x, m.y, 15) : '') + hit(`M${f(a2.x)},${f(a2.y)}L${f(b2.x)},${f(b2.y)}`);
      }
    } else if (o.type === 'arc') {
      const c = screen(o), r = o.r * S, t0 = o.from * Math.PI / 180, t1 = o.to * Math.PI / 180;
      const p0 = {x: c.x + r * Math.cos(t0), y: c.y - r * Math.sin(t0)}, p1 = {x: c.x + r * Math.cos(t1), y: c.y - r * Math.sin(t1)};
      let sw = t1 - t0; while (sw < 0) sw += 2 * Math.PI; while (sw >= 2 * Math.PI) sw -= 2 * Math.PI;
      const mid = (t0 + sw / 2), tm = {x: c.x + (r + 13) * Math.cos(mid), y: c.y - (r + 13) * Math.sin(mid)};
      s = `<path d="M${f(p0.x)},${f(p0.y)}A${f(r)},${f(r)} 0 ${sw > Math.PI ? 1 : 0} 0 ${f(p1.x)},${f(p1.y)}" fill="none" stroke="${ink}" stroke-width="1"/>${o.text ? texText(o.text, tm.x, tm.y, 15) : ''}${hit(`M${f(p0.x)},${f(p0.y)}A${f(r)},${f(r)} 0 ${sw > Math.PI ? 1 : 0} 0 ${f(p1.x)},${f(p1.y)}`)}`;
    } else if (o.type === 'axes') {
      const c = screen(o), ex = {x: c.x + o.lx * S, y: c.y}, ey = {x: c.x, y: c.y - o.ly * S};
      s = (o.lx > 0 ? arrow(c, ex, {width: 1, head: 8}) + texText(o.xlabel, ex.x + 4, ex.y + 13, 15, 'start') : '') + (o.ly > 0 ? arrow(c, ey, {width: 1, head: 8}) + texText(o.ylabel, ey.x - 12, ey.y + 4, 15) : '')
        + hit(`M${f(ex.x)},${f(ex.y)}L${f(c.x)},${f(c.y)}L${f(ey.x)},${f(ey.y)}`);
    } else if (o.type === 'line') {
      const a = screen({x: o.x1, y: o.y1}), b = screen({x: o.x2, y: o.y2});
      s = `<line x1="${f(a.x)}" y1="${f(a.y)}" x2="${f(b.x)}" y2="${f(b.y)}" stroke="${ink}" stroke-width="0.9"${o.dash ? ' stroke-dasharray="5 4"' : ''}/>${hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`)}`;
    }
    /* a velocity arrow of a body */
    const vNow = opts.velocities?.get?.(o.id), vx = vNow ? vNow.x : o.vx, vy = vNow ? vNow.y : o.vy;
    if (isBody(o) && o.showV && Math.hypot(vx, vy) > 1e-6) {
      const p = screen(opts.poses?.get?.(o.id) || poseOf(o)), sp = Math.hypot(vx, vy), L = Math.max(0.35, Math.min(1.4, sp * 0.08)) * S, ux = vx / sp, uy = vy / sp;
      const tip = {x: p.x + ux * L, y: p.y - uy * L};
      s += arrow(p, tip, {width: 1.5, head: 9}) + (o.vLabel ? texText(o.vLabel, tip.x + ux * 10 - uy * 10, tip.y - uy * 10 - ux * 10, 15) : '');
    }
    if (s) out.push(group(o, s));
  }
  /* the free-body diagram: every force on each body, from its centre, the longest arrow 90 px */
  if (opts.forces) {
    let max = 0;
    for (const list of opts.forces.values()) for (const x of list) max = Math.max(max, vec.len(x.v));
    const color = opts.forceColor || '#b42318';
    for (const [id, list] of opts.forces) for (const x of list) {
      const m = vec.len(x.v); if (m < 1e-9 || !max) continue;
      const L = Math.max(16, 90 * m / max), u = vec.unit(x.v), a = screen(x.at), tip = {x: a.x + u.x * L, y: a.y - u.y * L};
      out.push(`<g class="fbd" data-body="${esc(id)}" data-kind="${x.kind}">${arrow(a, tip, {color, width: 2, head: 9})}${texText(FORCE_LABEL[x.kind] || '', tip.x + u.x * 12, tip.y - u.y * 12, 14, 'middle', ` fill="${color}"`).replace('fill="#000"', '')}</g>`);
    }
  }
  if (edit && sel) {
    const o = byId.get(sel);
    if (o) { const b = objectBox(scene, o, opts.poses); if (b) out.push(`<rect x="${f(X(b.x) - 5)}" y="${f(Y(b.y + b.h) - 5)}" width="${f(b.w * S + 10)}" height="${f(b.h * S + 10)}" fill="none" stroke="#3b6fd8" stroke-width="1.3" stroke-dasharray="5 3" pointer-events="none" class="selbox"/>`); }
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" font-family="${FONT}">${opts.title ? `<title>${esc(opts.title)}</title>` : ''}${out.join('')}</svg>`;
}

/** the world box around one object (for the selection outline and for picking) */
export function objectBox(scene, o, poses) {
  const byId = new Map(scene.objects.map(x => [x.id, x]));
  const box = pts => { const xs = pts.map(p => p.x), ys = pts.map(p => p.y), x = Math.min(...xs), y = Math.min(...ys); return {x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y}; };
  if (isBody(o)) { const p = poses?.get?.(o.id) || bodyPose(scene, o), r = o.type === 'ball' ? o.r : Math.hypot(o.w, o.h) / 2; return {x: p.x - r, y: p.y - r, w: 2 * r, h: 2 * r}; }
  switch (o.type) {
    case 'floor': case 'ceiling': return {x: o.x, y: o.y - 0.04, w: o.w, h: 0.08};
    case 'wall': return {x: o.x - 0.04, y: o.y, w: 0.08, h: o.h};
    case 'incline': { const c = inclineCorners(o); return box([c.foot, c.top, c.right]); }
    case 'pulley': return {x: o.x - o.r, y: o.y - o.r, w: 2 * o.r, h: 2 * o.r};
    case 'pivot': return {x: o.x - 0.05, y: o.y - 0.05, w: 0.1, h: 0.1};
    case 'label': return {x: o.x - 0.12, y: o.y - 0.08, w: 0.24, h: 0.16};
    case 'dim': case 'line': return box([{x: o.x1, y: o.y1}, {x: o.x2, y: o.y2}]);
    case 'arc': return {x: o.x - o.r, y: o.y - o.r, w: 2 * o.r, h: 2 * o.r};
    case 'axes': return {x: o.x, y: o.y, w: Math.max(0.05, o.lx), h: Math.max(0.05, o.ly)};
    case 'string': case 'rod': case 'spring': { const A = byId.get(o.a), B = byId.get(o.b); if (!A || !B) return null; const pa = isBody(A) ? (poses?.get?.(A.id) || bodyPose(scene, A)) : A, pb = isBody(B) ? (poses?.get?.(B.id) || bodyPose(scene, B)) : B; return box([pa, pb, ...((o.over || []).map(id => byId.get(id)).filter(Boolean))]); }
    case 'force': { const b = byId.get(o.on); if (!b) return null; const p = poses?.get?.(b.id) || bodyPose(scene, b), th = o.angle * Math.PI / 180; return box([p, {x: p.x + Math.cos(th) * o.len, y: p.y + Math.sin(th) * o.len}]); }
  }
  return null;
}
export {surfaceFrame};
