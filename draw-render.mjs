/* Draws a scene (draw-scene.mjs) as an exam figure. The same SVG text is the editor's canvas (with ids to pick objects,
   a grid, the selection and its handles), the file that is downloaded, the picture put on a test paper (teach.js) and
   the frame of a running simulation (with the bodies where the solver has them, their trails and the forces on them).

   Labels are typeset here by a small TeX engine (texLayout): sub- and superscripts, \frac, \sqrt, accents (\vec \hat
   \dot \ddot \bar \tilde \overline \overrightarrow), \mathrm \text \mathbf \boldsymbol \mathcal, the Greek letters
   with their variants, and the physics symbols (∇ ∂ ∫ ∮ ∑ ∏ ∞ ± ∓ × · ∘ ≈ ≠ ≤ ≥ ∝ ∼ ≡ ⟨ ⟩ \ket \bra \braket ħ Å °
   ⊙ ⊗ ⊥ ∥ ∠ △ → ⇒ ↔ ⇌ …). Glyph advances come from a width table of a Times-like serif (or Helvetica for sans
   styles), every run is placed at its own x, and accents, fraction bars and radicals are drawn as paths, so a label
   looks the same in the editor, in the downloaded SVG and in the PNG without fonts or scripts in the file.

   The figure style ("그림체", STYLES) sets line weights, arrowheads, hatching, fills, the label face and size, and the
   vector notation (an arrow over the letter, or bold). The presets follow the conventions of university problem
   sets, olympiad papers and JEE papers as drawn from general knowledge of how such figures look; nothing is traced
   or copied from them. */
import {isBody, bodyPose, surfaceFrame, inclineCorners, attachPoint, anchorPoint, stringPath, vec, objectExtent, compileExpr} from './draw-scene.mjs?v=db9a7a5f3c86';
import {fieldLines, equipotentials, chargePath, circuitNodes, elementPath, processPoints, gasCycle, traceRay, principalRays, opticImage, prismCorners,
  slitIntensity, slitRange, fringeSpacing, wellModel, levelModel, clockTicks, lorentzGamma} from './draw-physics.mjs?v=356d0090fae5';

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const f = n => (Math.round(n * 100) / 100).toString();
const SERIF = `'Times New Roman','STIX Two Text','Nimbus Roman','Liberation Serif','Noto Serif KR','Nanum Myeongjo',serif`;
const SANS = `'Helvetica Neue',Helvetica,Arial,'Liberation Sans','Noto Sans KR',sans-serif`;

/* ── figure styles ── */
export const STYLES = {
  textbook: {name: {ko: '교과서 (기본)', en: 'Textbook (default)'}, lw: 1.7, thin: 1.15, hair: 0.85, hatchGap: 9, hatchLen: 7, hatchW: 0.9, head: 'filled', headLen: 9, font: SERIF, sans: false, labelScale: 1, vec: 'arrow', fill: '#fff', light: '#f1f1f1', gray: '#d2d2d2', accent: '#b42318', dimHead: 'filled', resistor: 'zigzag', polarity: false},
  university: {name: {ko: '대학 과제', en: 'University problem set'}, lw: 1.45, thin: 1.0, hair: 0.75, hatchGap: 7, hatchLen: 6, hatchW: 0.8, head: 'stealth', headLen: 10, font: SERIF, sans: false, labelScale: 1, vec: 'arrow', fill: '#ececec', light: '#f3f3f3', gray: '#c6c6c6', accent: '#1d4ed8', dimHead: 'open', resistor: 'zigzag', polarity: true},
  olympiad: {name: {ko: '올림피아드', en: 'Olympiad'}, lw: 1.35, thin: 0.95, hair: 0.7, hatchGap: 6, hatchLen: 5.5, hatchW: 0.75, head: 'stealth', headLen: 9.5, font: SANS, sans: true, labelScale: 0.96, vec: 'bold', fill: '#f2f2f2', light: '#f5f5f5', gray: '#cbcbcb', accent: '#000', dimHead: 'open', resistor: 'box', polarity: true},
  jee: {name: {ko: 'JEE', en: 'JEE'}, lw: 1.25, thin: 0.9, hair: 0.7, hatchGap: 5, hatchLen: 5, hatchW: 0.8, head: 'filled', headLen: 8, font: SERIF, sans: false, labelScale: 0.95, vec: 'arrow', fill: '#fff', light: '#f4f4f4', gray: '#dadada', accent: '#000', dimHead: 'filled', resistor: 'zigzag', polarity: false},
  print: {name: {ko: '흑백 인쇄용', en: 'Black and white print'}, lw: 2.3, thin: 1.6, hair: 1.2, hatchGap: 9, hatchLen: 8, hatchW: 1.3, head: 'filled', headLen: 11.5, font: SERIF, sans: false, labelScale: 1.18, vec: 'arrow', fill: '#fff', light: '#fff', gray: null, accent: '#000', dimHead: 'filled', resistor: 'zigzag', polarity: false}
};
let CUR = {...STYLES.textbook, ls: 1, ss: 1};

/* ── the TeX subset ── */
const SYM = {alpha: 'α', beta: 'β', gamma: 'γ', delta: 'δ', epsilon: 'ϵ', varepsilon: 'ε', zeta: 'ζ', eta: 'η', theta: 'θ', vartheta: 'ϑ', iota: 'ι', kappa: 'κ', varkappa: 'ϰ',
  lambda: 'λ', mu: 'μ', nu: 'ν', xi: 'ξ', omicron: 'ο', pi: 'π', varpi: 'ϖ', rho: 'ρ', varrho: 'ϱ', sigma: 'σ', varsigma: 'ς', tau: 'τ', upsilon: 'υ', phi: 'ϕ', varphi: 'φ', chi: 'χ', psi: 'ψ', omega: 'ω',
  Alpha: 'Α', Beta: 'Β', Gamma: 'Γ', Delta: 'Δ', Epsilon: 'Ε', Zeta: 'Ζ', Eta: 'Η', Theta: 'Θ', Iota: 'Ι', Kappa: 'Κ', Lambda: 'Λ', Mu: 'Μ', Nu: 'Ν', Xi: 'Ξ', Omicron: 'Ο', Pi: 'Π', Rho: 'Ρ', Sigma: 'Σ', Tau: 'Τ', Upsilon: 'Υ', Phi: 'Φ', Chi: 'Χ', Psi: 'Ψ', Omega: 'Ω',
  nabla: '∇', partial: '∂', int: '∫', iint: '∬', iiint: '∭', oint: '∮', sum: '∑', prod: '∏', infty: '∞', pm: '±', mp: '∓', times: '×', cdot: '·', circ: '∘', bullet: '•', div: '÷', ast: '∗', star: '⋆',
  approx: '≈', neq: '≠', ne: '≠', le: '≤', ge: '≥', leq: '≤', geq: '≥', ll: '≪', gg: '≫', propto: '∝', sim: '∼', simeq: '≃', cong: '≅', equiv: '≡', in: '∈', notin: '∉',
  langle: '⟨', rangle: '⟩', vert: '|', mid: '|', Vert: '‖', hbar: 'ħ', hslash: 'ℏ', AA: 'Å', degree: '°', ell: 'ℓ', Re: 'ℜ', Im: 'ℑ', wp: '℘', aleph: 'ℵ', emptyset: '∅',
  odot: '⊙', otimes: '⊗', oplus: '⊕', perp: '⊥', parallel: '∥', angle: '∠', measuredangle: '∡', triangle: '△', square: '□', forall: '∀', exists: '∃', neg: '¬', wedge: '∧', vee: '∨',
  to: '→', rightarrow: '→', leftarrow: '←', gets: '←', uparrow: '↑', downarrow: '↓', leftrightarrow: '↔', updownarrow: '↕', Rightarrow: '⇒', Leftarrow: '⇐', Leftrightarrow: '⇔', implies: '⇒', iff: '⇔',
  rightleftharpoons: '⇌', leftrightharpoons: '⇋', mapsto: '↦', nearrow: '↗', searrow: '↘', circlearrowleft: '↺', circlearrowright: '↻', longrightarrow: '⟶',
  ldots: '…', cdots: '⋯', vdots: '⋮', prime: '′', dagger: '†', ddagger: '‡', '%': '%', '$': '$', '{': '{', '}': '}', '_': '_', '#': '#', '&': '&', '|': '‖', lbrace: '{', rbrace: '}',
  sin: 'sin', cos: 'cos', tan: 'tan', cot: 'cot', sec: 'sec', csc: 'csc', ln: 'ln', log: 'log', exp: 'exp', lim: 'lim', max: 'max', min: 'min', det: 'det', sinh: 'sinh', cosh: 'cosh', tanh: 'tanh', arcsin: 'arcsin', arccos: 'arccos', arctan: 'arctan',
  deg: '°', ohm: 'Ω', micro: 'µ', imath: 'ı', jmath: 'ȷ'};
const OPNAMES = new Set(['sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'ln', 'log', 'exp', 'lim', 'max', 'min', 'det', 'sinh', 'cosh', 'tanh', 'arcsin', 'arccos', 'arctan']);
const SPACES = {',': 0.17, ':': 0.22, ';': 0.28, ' ': 0.25, quad: 1, qquad: 2, '!': -0.1, enspace: 0.5, thinspace: 0.17};
const ACCENTS = {vec: 'vec', hat: 'hat', widehat: 'hat', dot: 'dot', ddot: 'ddot', bar: 'bar', overline: 'bar', tilde: 'tilde', widetilde: 'tilde', overrightarrow: 'arrow', check: 'check', breve: 'breve', underline: 'under'};
const FONTS = {mathrm: 'rm', text: 'rm', textrm: 'rm', rm: 'rm', operatorname: 'rm', mathbf: 'bf', bf: 'bf', textbf: 'bf', boldsymbol: 'bfit', bm: 'bfit', mathit: 'it', textit: 'it', mathsf: 'rm', mathcal: 'cal', mathscr: 'cal'};
const CAL = {A: '𝒜', B: 'ℬ', C: '𝒞', D: '𝒟', E: 'ℰ', F: 'ℱ', G: '𝒢', H: 'ℋ', I: 'ℐ', J: '𝒥', K: '𝒦', L: 'ℒ', M: 'ℳ', N: '𝒩', O: '𝒪', P: '𝒫', Q: '𝒬', R: 'ℛ', S: '𝒮', T: '𝒯', U: '𝒰', V: '𝒱', W: '𝒲', X: '𝒳', Y: '𝒴', Z: '𝒵'};
const IGNORE = new Set(['left', 'right', 'big', 'Big', 'bigg', 'Bigg', 'displaystyle', 'textstyle', 'limits', 'nolimits', 'mathstrut']);

/* a parsed label: nodes {k:'t', s, font} | {k:'g', body} | {k:'scr', base, sub, sup} | {k:'frac', num, den} |
   {k:'sqrt', body, index} | {k:'acc', a, body} | {k:'sp', w} */
function parseTex(str) {
  let k = 0;
  const group = () => { let depth = 1, j = k + 1; while (j < str.length && depth) { if (str[j] === '\\') { j += 2; continue; } if (str[j] === '{') depth++; else if (str[j] === '}') depth--; j++; } const g = str.slice(k + 1, j - 1); k = j; return g; };
  const arg = () => { while (str[k] === ' ') k++; if (str[k] === '{') return parseList(group()); if (str[k] === '\\') { const m = /^\\([A-Za-z]+|.)/.exec(str.slice(k)); k += m ? m[0].length : 1; return command(m ? m[1] : ''); } const c = str[k++]; return c === undefined ? [] : [{k: 't', s: c, font: 'auto'}]; };
  const command = name => {
    if (SYM[name]) return [{k: 't', s: SYM[name], font: OPNAMES.has(name) ? 'rm' : 'auto', sym: true}];
    if (SPACES[name] !== undefined) return [{k: 'sp', w: SPACES[name]}];
    if (IGNORE.has(name)) return [];
    if (ACCENTS[name]) return [{k: 'acc', a: ACCENTS[name], body: arg()}];
    if (FONTS[name]) { const body = arg(), font = FONTS[name]; const set = list => list.map(n => n.k === 't' ? {...n, font: font === 'cal' ? 'cal' : n.sym && font !== 'bf' && font !== 'bfit' ? n.font : font} : n.k === 'g' || n.k === 'acc' ? {...n, body: set(n.body)} : n); return [{k: 'g', body: set(body)}]; }
    if (name === 'frac' || name === 'dfrac' || name === 'tfrac') { const a = arg(), b = arg(); return [{k: 'frac', num: a, den: b, t: name === 'tfrac'}]; }
    if (name === 'sqrt') { let index = null; if (str[k] === '[') { const j = str.indexOf(']', k); if (j > k) { index = parseList(str.slice(k + 1, j)); k = j + 1; } } return [{k: 'sqrt', body: arg(), index}]; }
    if (name === 'ket') return [{k: 't', s: '|', font: 'rm'}, ...arg(), {k: 't', s: '⟩', font: 'rm'}];
    if (name === 'bra') return [{k: 't', s: '⟨', font: 'rm'}, ...arg(), {k: 't', s: '|', font: 'rm'}];
    if (name === 'braket') return [{k: 't', s: '⟨', font: 'rm'}, ...arg(), {k: 't', s: '⟩', font: 'rm'}];
    if (name === 'abs') return [{k: 't', s: '|', font: 'rm'}, ...arg(), {k: 't', s: '|', font: 'rm'}];
    if (name === 'norm') return [{k: 't', s: '‖', font: 'rm'}, ...arg(), {k: 't', s: '‖', font: 'rm'}];
    if (name === 'unit' || name === 'si' || name === 'SI') { const body = arg(); return [{k: 'sp', w: 0.17}, {k: 'g', body: body.map(n => n.k === 't' ? {...n, font: 'rm'} : n)}]; }
    if (name === 'cal') return [];
    return [{k: 't', s: name, font: 'rm'}];
  };
  function parseList(s) {
    const saved = [str, k]; str = s; k = 0; const out = [];
    while (k < str.length) {
      const c = str[k];
      if (c === '\\') { const m = /^\\([A-Za-z]+|.)/.exec(str.slice(k)); k += m ? m[0].length : 1; if (m && /^[A-Za-z]/.test(m[1])) while (str[k] === ' ') k++; out.push(...command(m ? m[1] : '')); }
      else if (c === '{') out.push({k: 'g', body: parseList(group())});
      else if (c === '}') k++;
      else if (c === '_' || c === '^') {
        k++;
        let base = out.pop() || {k: 't', s: '', font: 'auto'};
        /* a word: only its last letter takes the script */
        if (base.k === 't' && base.s.length > 1 && !base.sym) { out.push({...base, s: base.s.slice(0, -1)}); base = {...base, s: base.s.slice(-1)}; }
        let a = arg();
        /* ^\circ is the degree sign */
        if (c === '^' && a.length === 1 && a[0].k === 't' && (a[0].s === '∘' || a[0].s === '°')) { out.push(base, {k: 't', s: '°', font: 'rm'}); continue; }
        const scr = base.k === 'scr' ? base : {k: 'scr', base: [base], sub: null, sup: null};
        if (c === '_') scr.sub = a; else scr.sup = a;
        out.push(scr);
      } else if (c === "'") { k++; out.push({k: 't', s: '′', font: 'rm'}); }
      else { let j = k; while (j < str.length && !'\\{}_^\''.includes(str[j])) j++; const s = str.slice(k, j); k = j;
        /* keep a run splittable into words so a script attaches to the last character only */
        const last = out[out.length - 1]; if (last && last.k === 't' && last.font === 'auto' && !last.sym) last.s += s; else out.push({k: 't', s, font: 'auto'}); }
    }
    [str, k] = saved;
    return out;
  }
  return parseList(str);
}

/* advance widths (em) of a Times-like face; Helvetica is about 8 % wider */
const WT = ' 250!333"408#500$500%833&778\'180(333)333*500+564,250-333.250/2780500150025003500450055006500750085009500:278;278<564=564>564?444@921A722B667C667D722E611F556G722H722I333J389K722L611M889N722O722P556Q722R667S556T611U722V722W944X722Y722Z611[333\\278]333^469_500`333a444b500c444d500e444f333g500h500i278j278k500l278m778n500o500p500q500r333s389t278u500v500w722x500y500z444{480|200}480~541';
const ADV = (() => { const m = {}; for (let i = 0; i < WT.length;) { const c = WT[i]; m[c] = +WT.slice(i + 1, i + 4) / 1000; i += 4; } return m; })();
const XLOW = new Set('acemnorsuvwxzαεικνοπρστυωϵ·×+−-=<>~∼≈:,.'.split(''));
function charW(c, it) {
  if (ADV[c] !== undefined) return ADV[c] * (it && c === 'f' ? 0.9 : 1);
  if (/[α-ω]/.test(c)) return c === 'ω' ? 0.68 : c === 'ι' ? 0.32 : c === 'μ' ? 0.55 : 0.52;
  if (/[Α-Ω]/.test(c)) return 0.68;
  if ('ϑϕϵϱςϖϰ'.includes(c)) return 0.55;
  if (/[가-힣ㄱ-ㅎ]/.test(c)) return 0.92;
  if ('→←↔⇒⇐⇔⇌⇋↦⟶'.includes(c)) return 0.95;
  if ('↑↓↕'.includes(c)) return 0.5;
  if ('∑∏∫∬∭∮'.includes(c)) return 0.62;
  if ('·∘•'.includes(c)) return 0.3;
  if ('°′″'.includes(c)) return 0.36;
  if ('⟨⟩|‖'.includes(c)) return 0.36;
  if ('×±∓÷≈≠≤≥∝∼≡≃≅−'.includes(c)) return 0.58;
  if ('∞⊙⊗⊕'.includes(c)) return 0.78;
  if ('ħℏℓ∂∇'.includes(c)) return 0.52;
  if (/[\u{1D49C}-\u{1D4CF}ℬℰℱℋℐℒℳℛ]/u.test(c)) return 0.72;
  if ('…⋯'.includes(c)) return 0.95;
  return 0.6;
}
const textWidth = (s, sz, it, bold) => { let w = 0; for (const c of s) w += charW(c, it); return w * sz * (CUR.sans ? 1.08 : 1) * (bold ? 1.04 : 1); };
const highChar = c => !XLOW.has(c);

/* the layout: a box {w, a (ascent), d (descent), items: [{x, y, t, size, it, bf}], paths: [{d (path data with
   coordinates relative to the box), sw, fill}]} with the baseline at y = 0 and y down */
function layout(nodes, sz, ctx) {
  let x = 0, a = sz * 0.46, d = sz * 0.05; const items = [], paths = [];
  const put = (b, dy = 0) => {
    for (const it of b.items) items.push({...it, x: it.x + x, y: it.y + dy});
    for (const p of b.paths) paths.push({...p, ox: (p.ox || 0) + x, oy: (p.oy || 0) + dy});
    a = Math.max(a, b.a - dy); d = Math.max(d, b.d + dy); x += b.w;
  };
  for (let i = 0; i < nodes.length; i++) {
    const n = nodes[i];
    if (n.k === 't') put(textBox(n, sz, {...ctx, lead: x === 0 && !items.length}));
    else if (n.k === 'g') put(layout(n.body, sz, ctx));
    else if (n.k === 'sp') x += n.w * sz;
    else if (n.k === 'scr') {
      const base = layout(n.base, sz, ctx), s2 = Math.max(7, sz * (ctx.level ? 0.8 : 0.7)), c2 = {...ctx, level: (ctx.level || 0) + 1};
      put(base);
      const it = base.items.length === 1 && base.items[0].it ? sz * 0.06 : 0;
      const sub = n.sub ? layout(n.sub, s2, c2) : null, sup = n.sup ? layout(n.sup, s2, c2) : null;
      const x0 = x;
      if (sup) { x = x0 + it; put(sup, -Math.max(sz * 0.4, base.a - s2 * 0.38)); }
      const xs = x;
      if (sub) { x = x0; put(sub, Math.max(sz * (sup ? 0.26 : 0.2), base.d + s2 * 0.12)); }
      x = Math.max(xs, x) + sz * 0.04;
    } else if (n.k === 'frac') {
      const s2 = Math.max(8, sz * (n.t ? 0.66 : sz >= 13 ? 0.8 : 0.86)), c2 = {...ctx, level: (ctx.level || 0) + 1};
      const num = layout(n.num, s2, c2), den = layout(n.den, s2, c2), w = Math.max(num.w, den.w) + sz * 0.2, axis = sz * 0.27, gap = sz * 0.1;
      const box = {w, a: 0, d: 0, items: [], paths: [{d: `M${f(sz * 0.06)},${f(-axis)}H${f(w - sz * 0.06)}`, sw: Math.max(0.7, sz * 0.055)}]};
      const plc = (b, dx, dy) => { for (const it of b.items) box.items.push({...it, x: it.x + dx, y: it.y + dy}); for (const p of b.paths) box.paths.push({...p, ox: (p.ox || 0) + dx, oy: (p.oy || 0) + dy}); };
      const ny = -axis - gap - num.d, dy = -axis + gap + den.a;
      plc(num, (w - num.w) / 2, ny); plc(den, (w - den.w) / 2, dy);
      box.a = -ny + num.a; box.d = dy + den.d;
      x += sz * 0.05; put(box); x += sz * 0.05;
    } else if (n.k === 'sqrt') {
      const b = layout(n.body, sz, ctx), top = b.a + sz * 0.12, rw = sz * 0.56, sw = Math.max(0.7, sz * 0.055);
      const box = {w: rw + b.w + sz * 0.1, a: top + sz * 0.08, d: Math.max(b.d, sz * 0.12), items: [], paths: [{d: `M${f(sz * 0.03)},${f(-sz * 0.24)}L${f(sz * 0.14)},${f(-sz * 0.3)}L${f(sz * 0.27)},${f(b.d + sz * 0.02)}L${f(rw - sz * 0.06)},${f(-top)}H${f(rw + b.w + sz * 0.06)}`, sw, join: true}]};
      for (const it of b.items) box.items.push({...it, x: it.x + rw});
      for (const p of b.paths) box.paths.push({...p, ox: (p.ox || 0) + rw});
      if (n.index) { const ix = layout(n.index, Math.max(7, sz * 0.5), {...ctx, level: 2}); for (const it of ix.items) box.items.push({...it, x: it.x + sz * 0.02, y: it.y - sz * 0.42}); }
      put(box);
    } else if (n.k === 'acc') {
      if (n.a === 'vec' && ctx.vec === 'bold') { put(layout(n.body, sz, {...ctx, bold: true})); continue; }
      const b = layout(n.body, sz, ctx), single = b.items.length === 1 && [...b.items[0].t].length === 1, slant = single && b.items[0].it ? sz * 0.09 : 0;
      const cx = b.w / 2 + slant, top = -b.a, sw = Math.max(0.65, sz * 0.055), extra = [];
      if (n.a === 'vec' || n.a === 'arrow') {
        const half = n.a === 'arrow' || !single ? Math.max(b.w / 2, sz * 0.25) : Math.max(sz * 0.24, b.w * 0.42), y = top - sz * 0.16, x2 = cx + half;
        extra.push({d: `M${f(cx - half)},${f(y)}H${f(x2)}M${f(x2 - sz * 0.15)},${f(y - sz * 0.085)}L${f(x2)},${f(y)}L${f(x2 - sz * 0.15)},${f(y + sz * 0.085)}`, sw, join: true});
      } else if (n.a === 'hat') extra.push({d: `M${f(cx - sz * 0.17)},${f(top - sz * 0.07)}L${f(cx)},${f(top - sz * 0.23)}L${f(cx + sz * 0.17)},${f(top - sz * 0.07)}`, sw, join: true});
      else if (n.a === 'check') extra.push({d: `M${f(cx - sz * 0.15)},${f(top - sz * 0.22)}L${f(cx)},${f(top - sz * 0.08)}L${f(cx + sz * 0.15)},${f(top - sz * 0.22)}`, sw, join: true});
      else if (n.a === 'dot') extra.push({dot: [cx, top - sz * 0.13, sz * 0.06]});
      else if (n.a === 'ddot') extra.push({dot: [cx - sz * 0.12, top - sz * 0.13, sz * 0.06]}, {dot: [cx + sz * 0.12, top - sz * 0.13, sz * 0.06]});
      else if (n.a === 'bar') { const half = single ? Math.max(sz * 0.2, b.w * 0.42) : b.w / 2; extra.push({d: `M${f(cx - half)},${f(top - sz * 0.1)}H${f(cx + half)}`, sw}); }
      else if (n.a === 'tilde') { const w = Math.max(sz * 0.36, single ? 0 : b.w * 0.9), y = top - sz * 0.13; extra.push({d: `M${f(cx - w / 2)},${f(y + sz * 0.04)}C${f(cx - w / 4)},${f(y - sz * 0.1)} ${f(cx - w / 12)},${f(y + sz * 0.1)} ${f(cx + w / 6)},${f(y - sz * 0.02)}S${f(cx + w / 2)},${f(y - sz * 0.06)} ${f(cx + w / 2)},${f(y - sz * 0.06)}`, sw}); }
      else if (n.a === 'breve') extra.push({d: `M${f(cx - sz * 0.15)},${f(top - sz * 0.22)}Q${f(cx)},${f(top - sz * 0.02)} ${f(cx + sz * 0.15)},${f(top - sz * 0.22)}`, sw});
      else if (n.a === 'under') extra.push({d: `M0,${f(b.d + sz * 0.08)}H${f(b.w)}`, sw});
      put({...b, a: b.a + (n.a === 'under' ? 0 : sz * 0.26), d: b.d + (n.a === 'under' ? sz * 0.12 : 0), paths: [...b.paths, ...extra]});
    }
  }
  return {w: x, a, d, items, paths};
}
function textBox(n, sz, ctx) {
  const items = []; let x = 0, high = false;
  const bold = ctx.bold || n.font === 'bf' || n.font === 'bfit';
  const add = (t, it) => { if (!t) return; const w = textWidth(t, sz, it, bold); items.push({x, y: 0, t, size: sz, it, bf: bold}); x += w; if ([...t].some(highChar)) high = true; };
  let s = n.s;
  /* in maths: a true minus sign, and room around relations */
  if (ctx.math && n.font === 'auto' && !n.sym) s = s.replace(/-/g, '−').replace(/\s*([=≈≠≤≥<>≡∝→⇒])\s*/g, ' $1 ').replace(/\s*([−+±∓×])\s*/g, (m, op, off) => off === 0 && ctx.lead ? op : ` ${op} `);
  if (n.font === 'cal') s = [...s].map(c => CAL[c] || c).join('');
  if (n.font === 'rm' || n.font === 'bf' || n.font === 'cal') add(s, false);
  else if (n.font === 'it' || n.font === 'bfit') add(s, true);
  else {
    /* auto: a maths letter is italic (a single letter, or every letter inside $…$), except function names; lower-case
       Greek is italic in maths, capitals and digits upright */
    const re = /[A-Za-z]+|[α-ωϑϕϵϱςϖϰ]+|[^A-Za-zα-ωϑϕϵϱςϖϰ]+/g; let m;
    while ((m = re.exec(s))) {
      const w = m[0], latin = /^[A-Za-z]/.test(w), greek = /^[α-ωϑϕϵϱςϖϰ]/.test(w);
      const it = ctx.math && ((latin && (ctx.all ? !OPNAMES.has(w) : w.length === 1)) || (greek && !CUR.sans));
      add(w, !!it);
    }
  }
  return {w: x, a: sz * (high ? 0.7 : 0.47), d: sz * ([...s].some(c => 'gjpqyβγζημξρφχψϕϱς,;()[]{}|/'.includes(c)) ? 0.22 : 0.04), items, paths: []};
}
/** a label laid out at size sz (px): {w, a, d, items, paths}. $…$ is maths (every letter italic); outside $, a label
 *  without Hangul is maths too but only single letters are italic ("2 kg" stays upright, "m_1" is an italic m). */
export function texLayout(src, sz = 16) {
  const text = String(src ?? '');
  const parts = text.includes('$') ? text.split('$').map((t, i) => ({t, math: i % 2 === 1, all: true})) : [{t: text, math: !/[가-힣]/.test(text), all: false}];
  let x = 0, a = sz * 0.47, d = sz * 0.05; const items = [], paths = [];
  for (const p of parts) {
    if (!p.t) continue;
    const b = layout(parseTex(p.t), sz, {math: p.math, all: p.all, vec: CUR.vec, level: 0});
    for (const it of b.items) items.push({...it, x: it.x + x});
    for (const q of b.paths) paths.push({...q, ox: (q.ox || 0) + x});
    a = Math.max(a, b.a); d = Math.max(d, b.d); x += b.w;
  }
  return {w: x, a, d, items, paths};
}
/** the runs of a label (for tests and the editor): [{t, it, sh: '' | 'sub' | 'sup'}] */
export function texRuns(src) {
  const b = texLayout(src, 100);
  return b.items.map(it => ({t: it.t, it: !!it.it, sh: it.y > 5 ? 'sub' : it.y < -5 ? 'sup' : ''}));
}
/** SVG of a label at (x, y) px, anchored 'start' | 'middle' | 'end', its middle on y */
export function texText(src, x, y, size = 16, anchor = 'middle', extra = '', opts = {}) {
  const sz = size * (opts.raw ? 1 : CUR.ls), b = texLayout(src, sz);
  if (!b.items.length && !b.paths.length) return '';
  const x0 = anchor === 'start' ? x : anchor === 'end' ? x - b.w : x - b.w / 2, base = y + (b.a - b.d) / 2;
  const color = /fill="([^"]+)"/.exec(extra)?.[1] || '#000';
  const halo = opts.halo ? ` stroke="#fff" stroke-width="${f(Math.max(2, sz * 0.22))}" stroke-linejoin="round" paint-order="stroke"` : '';
  let t = '';
  for (const it of b.items) t += `<tspan x="${f(x0 + it.x)}" y="${f(base + it.y)}"${Math.abs(it.size - sz) > 0.01 ? ` font-size="${f(it.size)}"` : ''}${it.it ? ' font-style="italic"' : ''}${it.bf ? ' font-weight="bold"' : ''}>${esc(it.t)}</tspan>`;
  let p = '';
  for (const q of b.paths) {
    const ox = x0 + (q.ox || 0), oy = base + (q.oy || 0);
    if (q.dot) p += `<circle cx="${f(ox + q.dot[0])}" cy="${f(oy + q.dot[1])}" r="${f(q.dot[2])}" fill="${color}"/>`;
    else p += `<path d="${q.d}" transform="translate(${f(ox)},${f(oy)})" fill="none" stroke="${color}" stroke-width="${f(q.sw)}"${q.join ? ' stroke-linejoin="round" stroke-linecap="round"' : ''}/>`;
  }
  return `<g class="tex"${extra.replace(/fill="[^"]+"/, '')}>${t ? `<text font-size="${f(sz)}" font-family="${esc(CUR.font).replace(/&#39;/g, "'")}" fill="${color}"${halo}>${t}</text>` : ''}${p}</g>`;
}
/** a label on its own, as an SVG document (the editor's previews and the symbol picker) */
export function texSVG(src, size = 18, style = 'textbook') {
  const saved = CUR; CUR = {...STYLES[style] || STYLES.textbook, ls: 1, ss: 1};
  const b = texLayout(src, size), pad = 3, W = Math.max(8, b.w + 2 * pad), H = b.a + b.d + 2 * pad;
  const out = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${f(W)} ${f(H)}" width="${f(W)}" height="${f(H)}">${texText(src, pad, pad + b.a - (b.a - b.d) / 2, size, 'start')}</svg>`;
  CUR = saved; return out;
}

const FORCE_LABEL = {gravity: '$mg$', normal: '$N$', friction: '$f$', tension: '$T$', spring: '$F_s$', applied: '$F$'};
const DASH = {solid: '', dashed: '6 4', dotted: '1.2 3.2', dashdot: '9 3 2 3', none: ''};
const fmtSI = (v0, unit) => {
  const v = +(+v0).toPrecision(6), a = Math.abs(v); if (!Number.isFinite(v)) return '—';
  const [k, p] = a >= 1e6 ? [1e-6, 'M'] : a >= 1e3 ? [1e-3, 'k'] : a >= 1 || a === 0 ? [1, ''] : a >= 1e-3 ? [1e3, 'm'] : a >= 1e-6 ? [1e6, 'μ'] : [1e9, 'n'];
  const x = v * k; return `${Math.abs(x) >= 100 ? x.toFixed(0) : Math.abs(x) >= 10 ? x.toFixed(1) : x.toFixed(2)} ${p}${unit}`;
};
let CLIP = 0;

/** The scene as SVG text. opts: width (px of the drawing, 800), view (the world rectangle; else scene.view),
 *  edit (ids on the objects, a grid when grid, the selected id and its handles), style (else scene.style),
 *  labelScale and strokeScale (labels and lines larger, e.g. for a printed paper or a phone), forces (map body →
 *  [{kind, v, at}]), trails (map body → [{x,y}]), anchors (map 'spring:end' → point), conical (list of {centre,
 *  radius}), circuit (solveCircuit's result: readings drawn on the elements), background. */
export function renderSVG(scene, opts = {}) {
  const W = opts.width || 800, view = opts.view || scene.view || {x: -0.5, y: -0.5, w: 4, h: 3};
  const S = W / view.w, H = Math.max(40, Math.round(view.h * S));
  const st = STYLES[opts.style || scene.style] || STYLES.textbook, ss = opts.strokeScale || 1;
  CUR = {...st, ls: (opts.labelScale || 1) * st.labelScale, ss};
  const X = x => (x - view.x) * S, Y = y => (view.y + view.h - y) * S, P = p => `${f(X(p.x))},${f(Y(p.y))}`;
  const byId = new Map(scene.objects.map(o => [o.id, o]));
  const edit = !!opts.edit, sel = opts.selected || '';
  const out = [];
  const ink = '#000', lw = st.lw * ss, thin = st.thin * ss, hair = st.hair * ss, HL = st.headLen * Math.sqrt(ss);
  const gray = st.gray, light = st.light, fill = st.fill;
  const lbl = (s, x, y, size = 15, anchor = 'middle', extra = '', o2) => texText(s, x, y, size, anchor, extra, o2);
  const group = (o, inner) => edit ? `<g data-id="${esc(o.id)}" class="obj${o.id === sel ? ' sel' : ''}">${inner}</g>` : inner;
  const hit = d => edit ? `<path d="${d}" fill="none" stroke="transparent" stroke-width="12" pointer-events="stroke"/>` : '';
  const hitBox = (x, y, w, h) => edit ? `<rect x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(h)}" fill="transparent"/>` : '';
  const dash = (pattern, k = 1) => DASH[pattern] ? ` stroke-dasharray="${DASH[pattern].split(' ').map(v => f(v * ss * k)).join(' ')}"${pattern === 'dotted' ? ' stroke-linecap="round"' : ''}` : '';
  const line = (a, b, w = lw, extra = '') => `<line x1="${f(a.x)}" y1="${f(a.y)}" x2="${f(b.x)}" y2="${f(b.y)}" stroke="${ink}" stroke-width="${f(w)}"${extra}/>`;
  const poly = (pts, w = lw, extra = '') => `<polyline points="${pts.map(p => `${f(p.x)},${f(p.y)}`).join(' ')}" fill="none" stroke="${ink}" stroke-width="${f(w)}" stroke-linejoin="round"${extra}/>`;
  const hatch = (x1, y1, x2, y2, nx, ny, gap = st.hatchGap) => {
    /* short slanted strokes on the solid side (nx, ny: the side, in screen px) of the line from (x1,y1) to (x2,y2) */
    const L = Math.hypot(x2 - x1, y2 - y1); if (L < 1) return '';
    const n = Math.max(1, Math.floor(L / gap)), ux = (x2 - x1) / L, uy = (y2 - y1) / L, hl = st.hatchLen * Math.sqrt(ss);
    let d = '';
    for (let i = 0; i <= n; i++) { const px = x1 + ux * (i * L / n), py = y1 + uy * (i * L / n); d += `M${f(px)},${f(py)}l${f(nx * hl - ux * hl * 0.85)},${f(ny * hl - uy * hl * 0.85)}`; }
    return `<path d="${d}" stroke="${ink}" stroke-width="${f(st.hatchW * ss)}" fill="none"/>`;
  };
  /* an arrowhead at tip pointing along (ux, uy): returns [svg, the point the shaft should end at] */
  const head = (tip, ux, uy, {color = ink, len = HL, kind = st.head, w = thin} = {}) => {
    const px = -uy, py = ux, hw = len * (kind === 'stealth' ? 0.42 : 0.38), base = {x: tip.x - ux * len, y: tip.y - uy * len};
    if (kind === 'none') return ['', tip];
    if (kind === 'open') return [`<path d="M${f(base.x + px * hw)},${f(base.y + py * hw)}L${f(tip.x)},${f(tip.y)}L${f(base.x - px * hw)},${f(base.y - py * hw)}" fill="none" stroke="${color}" stroke-width="${f(Math.max(w, 1))}" stroke-linejoin="miter"/>`, tip];
    if (kind === 'stealth') { const notch = {x: tip.x - ux * len * 0.68, y: tip.y - uy * len * 0.68}; return [`<path d="M${f(tip.x)},${f(tip.y)}L${f(base.x + px * hw)},${f(base.y + py * hw)}L${f(notch.x)},${f(notch.y)}L${f(base.x - px * hw)},${f(base.y - py * hw)}Z" fill="${color}"/>`, notch]; }
    return [`<path d="M${f(tip.x)},${f(tip.y)}L${f(base.x + px * hw)},${f(base.y + py * hw)}L${f(base.x - px * hw)},${f(base.y - py * hw)}Z" fill="${color}"/>`, {x: base.x + ux, y: base.y + uy}];
  };
  const arrow = (from, to, {color = ink, width = 1.6 * ss, head: hl = HL, kind = st.head, pattern = 'solid'} = {}) => {
    const dx = to.x - from.x, dy = to.y - from.y, L = Math.hypot(dx, dy);
    if (L < 1) return '';
    const ux = dx / L, uy = dy / L, [hs, end] = head(to, ux, uy, {color, len: Math.min(hl, L * 0.7), kind, w: width});
    return `<line x1="${f(from.x)}" y1="${f(from.y)}" x2="${f(end.x)}" y2="${f(end.y)}" stroke="${color}" stroke-width="${f(width)}"${dash(pattern)}/>` + hs;
  };
  /* an arrowhead in the middle of a polyline (screen points) */
  const midHead = (pts, at = 0.5, opt = {}) => {
    if (pts.length < 2) return '';
    let L = 0; const seg = []; for (let i = 1; i < pts.length; i++) { const l = Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y); seg.push(l); L += l; }
    let goal = L * at, i = 0; while (i < seg.length - 1 && goal > seg[i]) { goal -= seg[i]; i++; }
    const a = pts[i], b = pts[i + 1], l = seg[i] || 1, ux = (b.x - a.x) / l, uy = (b.y - a.y) / l, len = opt.len || HL * 0.9;
    const tip = {x: a.x + ux * Math.min(l, goal + len / 2), y: a.y + uy * Math.min(l, goal + len / 2)};
    return head(tip, ux, uy, {len, ...opt})[0];
  };
  const screen = p => ({x: X(p.x), y: Y(p.y)});
  const poseOf = o => isBody(o) ? bodyPose(scene, o) : {x: o.x, y: o.y, angle: 0};
  const plus = (c, r, w = thin) => `<path d="M${f(c.x - r)},${f(c.y)}H${f(c.x + r)}M${f(c.x)},${f(c.y - r)}V${f(c.y + r)}" stroke="${ink}" stroke-width="${f(w)}"/>`;
  const minus = (c, r, w = thin) => `<path d="M${f(c.x - r)},${f(c.y)}H${f(c.x + r)}" stroke="${ink}" stroke-width="${f(w)}"/>`;
  const dotSym = (c, r) => `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r)}" fill="#fff" stroke="${ink}" stroke-width="${f(thin)}"/><circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(Math.max(1, r * 0.28))}" fill="${ink}"/>`;
  const crossSym = (c, r) => `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r)}" fill="#fff" stroke="${ink}" stroke-width="${f(thin)}"/><path d="M${f(c.x - r * 0.7)},${f(c.y - r * 0.7)}L${f(c.x + r * 0.7)},${f(c.y + r * 0.7)}M${f(c.x + r * 0.7)},${f(c.y - r * 0.7)}L${f(c.x - r * 0.7)},${f(c.y + r * 0.7)}" stroke="${ink}" stroke-width="${f(thin)}"/>`;
  /* a fill: gray, or hatching when the style prints without gray */
  const shade = (shapeAttr, kind = 'gray') => {
    if (kind === 'none') return '';
    if (kind === 'gray' && gray) return '';
    const id = 'hl' + (++CLIP);
    const pat = kind === 'dots' ? `<pattern id="${id}" width="7" height="7" patternUnits="userSpaceOnUse"><circle cx="3.5" cy="3.5" r="0.9" fill="${ink}"/></pattern>`
      : `<pattern id="${id}" width="${f(st.hatchGap * 0.8)}" height="${f(st.hatchGap * 0.8)}" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="${f(st.hatchGap * 0.8)}" stroke="${ink}" stroke-width="${f(st.hatchW * ss * 0.8)}"/></pattern>`;
    return `<defs>${pat}</defs><${shapeAttr} fill="url(#${id})" stroke="none"/>`;
  };
  const fillOf = kind => kind === 'gray' && gray ? gray : kind === 'light' ? light : 'none';

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

  /* graphs: their ranges, fitted to what is plotted on them when auto */
  const ranges = new Map();
  for (const g of scene.objects.filter(o => o.type === 'graph')) {
    let r = {x0: g.xmin, x1: g.xmax, y0: g.ymin, y1: g.ymax};
    if (g.auto) {
      const pts = [];
      for (const c of scene.objects) if ((c.type === 'curve' || c.type === 'cycle') && c.graph === g.id) {
        if (c.type === 'cycle') gasCycle(c).legs.forEach(l => pts.push(...l.pts));
        else if (c.kind === 'func') { const fn = compileExpr(c.expr); for (let i = 0; i <= 60; i++) { const x = c.x1 + (c.x2 - c.x1) * i / 60, y = fn ? fn(x) : NaN; if (Number.isFinite(y) && Math.abs(y) < 1e6) pts.push({x, y}); } }
        else pts.push(...processPoints(c.kind, c, 40));
      }
      if (pts.length) {
        const xs = pts.map(p => p.x), ys = pts.map(p => p.y), lo = Math.min(...xs), hi = Math.max(...xs), ylo = Math.min(...ys), yhi = Math.max(...ys);
        r = {x0: Math.min(0, lo - 0.1 * (hi - lo)), x1: hi + 0.15 * (hi - Math.min(0, lo)), y0: Math.min(0, ylo - 0.1 * (yhi - ylo)), y1: yhi + 0.15 * (yhi - Math.min(0, ylo))};
        if (r.x1 - r.x0 < 1e-12) r.x1 = r.x0 + 1; if (r.y1 - r.y0 < 1e-12) r.y1 = r.y0 + 1;
      } else r = {x0: 0, x1: 1, y0: 0, y1: 1};
    }
    ranges.set(g.id, r);
  }
  const toGraph = (g, p) => { const r = ranges.get(g.id); return {x: X(g.x + (p.x - r.x0) / (r.x1 - r.x0) * g.w), y: Y(g.y + (p.y - r.y0) / (r.y1 - r.y0) * g.h)}; };
  /* where a circuit's labels go: away from the middle of all elements */
  const els = scene.objects.filter(o => o.type === 'element');
  const ccen = els.length ? {x: els.reduce((s, e) => s + e.x1 + e.x2, 0) / (2 * els.length), y: els.reduce((s, e) => s + e.y1 + e.y2, 0) / (2 * els.length)} : {x: 0, y: 0};

  /* order: regions and frames, surfaces, connections, bodies, marks (so a string ends under the block it pulls) */
  const RANK = {region: -3, field: -2, graph: -2, well: -1, levels: -1, spacetime: -1, reservoir: -1, fieldlines: -0.5, floor: 0, ceiling: 0, wall: 0, incline: 1, line: 2, axes: 2, slab: 1, prism: 1,
    curve: 2.5, cycle: 2.5, worldline: 2.5, pulley: 4, pivot: 4, string: 3, rod: 3, spring: 3, block: 5, ball: 5, force: 6, label: 7, dim: 7, arc: 7, point: 7, vector: 6, oarrow: 6, ray: 5.5, charge: 5, element: 3};
  const order = [...scene.objects].sort((a, b) => (RANK[a.type] ?? 4) - (RANK[b.type] ?? 4));
  for (const o of order) {
    let s = '';
    const T = o.type;
    if (T === 'floor') {
      const a = screen(o), b = screen({x: o.x + o.w, y: o.y});
      s = `${line(a, b)}${o.hatch ? hatch(a.x, a.y, b.x, b.y, 0, 1) : ''}${hit(`M${f(a.x)},${f(a.y)}H${f(b.x)}`)}`;
    } else if (T === 'ceiling') {
      const a = screen(o), b = screen({x: o.x + o.w, y: o.y});
      s = `${line(a, b)}${o.hatch ? hatch(a.x, a.y, b.x, b.y, 0, -1) : ''}${hit(`M${f(a.x)},${f(a.y)}H${f(b.x)}`)}`;
    } else if (T === 'wall') {
      const a = screen(o), b = screen({x: o.x, y: o.y + o.h}), side = o.side === 'left' ? -1 : 1;
      s = `${line(a, b)}${hatch(b.x, b.y, a.x, a.y, side, 0)}${hit(`M${f(a.x)},${f(a.y)}V${f(b.y)}`)}`;
    } else if (T === 'incline') {
      const c = inclineCorners(o), foot = screen(c.foot), top = screen(c.top), right = screen(c.right);
      s = `<path d="M${f(foot.x)},${f(foot.y)}L${f(top.x)},${f(top.y)}L${f(right.x)},${f(right.y)}Z" fill="${fill}" stroke="${ink}" stroke-width="${f(lw)}" stroke-linejoin="round"/>`;
      if (o.angleLabel) {
        const r = Math.min(34, 0.35 * Math.hypot(right.x - foot.x, right.y - foot.y)), th = o.angle * Math.PI / 180, dir = o.flip ? -1 : 1;
        const p1 = {x: foot.x + dir * r, y: foot.y}, p2 = {x: foot.x + dir * r * Math.cos(th), y: foot.y - r * Math.sin(th)};
        const mid = {x: foot.x + dir * (r + 13) * Math.cos(th / 2), y: foot.y - (r + 13) * Math.sin(th / 2)};
        s += `<path d="M${f(p1.x)},${f(p1.y)}A${f(r)},${f(r)} 0 0 ${o.flip ? 1 : 0} ${f(p2.x)},${f(p2.y)}" fill="none" stroke="${ink}" stroke-width="${f(hair * 1.2)}"/>${lbl(o.angleLabel, mid.x + dir * 4, mid.y, 15)}`;
      }
    } else if (T === 'pulley') {
      const c = screen(o), r = o.r * S, m = byId.get(o.mount);
      if (m) {
        let to = null;
        if (m.type === 'ceiling') to = {x: o.x, y: m.y};
        else if (m.type === 'incline') to = inclineCorners(m).top;
        else if (m.type === 'floor') to = {x: Math.abs(o.x - m.x) < Math.abs(o.x - m.x - m.w) ? m.x : m.x + m.w, y: m.y};
        else if (m.type === 'wall') to = {x: m.x, y: o.y};
        if (to) s += line(c, screen(to), 2.2 * ss);
      }
      s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r)}" fill="${fill}" stroke="${ink}" stroke-width="${f(lw)}"/><circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(Math.max(1.6, r * 0.14))}" fill="${ink}"/>`;
    } else if (T === 'pivot') {
      const c = screen(o), onCeiling = scene.objects.some(x => x.type === 'ceiling' && Math.abs(x.y - o.y) < 0.02 && o.x >= x.x && o.x <= x.x + x.w);
      if (!onCeiling) s += line({x: c.x - 13, y: c.y - 7}, {x: c.x + 13, y: c.y - 7}) + hatch(c.x - 13, c.y - 7, c.x + 13, c.y - 7, 0, -1) + line({x: c.x, y: c.y - 7}, c, 1.4 * ss);
      s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(3.2 * Math.sqrt(ss))}" fill="#fff" stroke="${ink}" stroke-width="${f(1.4 * ss)}"/>`;
    } else if (T === 'string') {
      const path = stringPath(scene, o, opts.poses);
      if (path) {
        let d = '';
        path.segs.forEach((sg, i) => {
          d += `M${P(sg[0])}L${P(sg[1])}`;
          const w = path.wraps[i];
          if (w) {
            const a0 = Math.atan2(w.from.y - w.c.y, w.from.x - w.c.x), a1 = Math.atan2(w.to.y - w.c.y, w.to.x - w.c.x);
            let sweep = w.s > 0 ? a1 - a0 : a0 - a1; while (sweep < 0) sweep += 2 * Math.PI;
            d += `M${P(w.from)}A${f(w.r * S)},${f(w.r * S)} 0 ${sweep > Math.PI ? 1 : 0} ${w.s > 0 ? 0 : 1} ${P(w.to)}`;
          }
        });
        s = `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(thin)}"/>${hit(d)}`;
        if (o.label && path.segs.length === 1) { const a = screen(path.segs[0][0]), b = screen(path.segs[0][1]), n = vec.unit({x: -(b.y - a.y), y: b.x - a.x}); s += lbl(o.label, (a.x + b.x) / 2 + n.x * 13, (a.y + b.y) / 2 + n.y * 13, 15); }
      }
    } else if (T === 'rod') {
      const A = byId.get(o.a), B = byId.get(o.b);
      if (A && B) { const a = screen(poseOf(A)), b = screen(opts.poses?.get?.(B.id) || poseOf(B)); s = `${line(a, b, 3.2 * ss, ' stroke-linecap="round"')}${hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`)}`;
        if (o.label) { const n = vec.unit({x: -(b.y - a.y), y: b.x - a.x}); s += lbl(o.label, (a.x + b.x) / 2 + n.x * 14, (a.y + b.y) / 2 + n.y * 14, 15); } }
    } else if (T === 'spring') {
      const A = byId.get(o.a), B = byId.get(o.b);
      if (A && B) {
        const pose = x => opts.poses?.get?.(x.id) || poseOf(x);
        const end = (me, other) => {
          if (isBody(me)) return attachPoint(scene, me, isBody(other) ? pose(other) : anchorPoint(other, pose(me)), pose(me));
          return opts.anchors?.get?.(o.id + ':' + me.id) || anchorPoint(me, isBody(other) ? attachPoint(scene, other, pose(other), pose(other)) : {x: other.x, y: other.y});
        };
        const a = screen(end(A, B)), b = screen(end(B, A)), L = Math.hypot(b.x - a.x, b.y - a.y);
        if (L > 2) {
          const ux = (b.x - a.x) / L, uy = (b.y - a.y) / L, lead = Math.min(12, L * 0.15), n = Math.round(o.coils) * 2, amp = 6.5 * Math.sqrt(ss);
          let d = `M${f(a.x)},${f(a.y)}l${f(ux * lead)},${f(uy * lead)}`;
          const seg = (L - 2 * lead) / n;
          for (let i = 0; i < n; i++) { const t = lead + seg * (i + 0.5), side = i % 2 ? -1 : 1; d += `L${f(a.x + ux * t - uy * amp * side)},${f(a.y + uy * t + ux * amp * side)}`; }
          d += `L${f(b.x - ux * lead)},${f(b.y - uy * lead)}L${f(b.x)},${f(b.y)}`;
          s = `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(1.3 * ss)}" stroke-linejoin="round"/>${hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`)}`;
          if (o.label) { let nx = -uy, ny = ux; if (Math.abs(uy) > 0.7 ? nx < 0 : ny > 0) { nx = -nx; ny = -ny; } s += lbl(o.label, (a.x + b.x) / 2 + nx * 20, (a.y + b.y) / 2 + ny * 20, 15); }
        }
      }
    } else if (T === 'block') {
      const p = poseOf(o), ca = Math.cos(p.angle), sa = Math.sin(p.angle), hw = o.w / 2, hh = o.h / 2;
      const pts = [[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]].map(([u, v]) => P({x: p.x + u * ca - v * sa, y: p.y + u * sa + v * ca}));
      const c = screen(p);
      s = `<polygon points="${pts.join(' ')}" fill="${fill}" stroke="${ink}" stroke-width="${f(lw)}" stroke-linejoin="round"/>${o.label ? lbl(o.label, c.x, c.y, Math.min(Math.max(11, Math.min(17, Math.min(o.w, o.h) * S * 0.45)), Math.min(o.w, o.h) * S * 0.62 / CUR.ls)) : ''}`;
    } else if (T === 'ball') {
      const p = poseOf(o), c = screen(p), r = o.r * S;
      s = `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(Math.max(2.5, r))}" fill="${fill}" stroke="${ink}" stroke-width="${f(lw)}"/>`;
      if (o.label) s += r >= 13 * CUR.ls ? lbl(o.label, c.x, c.y, Math.min(16, r * 0.9 / CUR.ls)) : lbl(o.label, c.x + r + 5, c.y - r - 6, 15, 'start');
    } else if (T === 'force') {
      const b = byId.get(o.on);
      if (b) { const p = screen(opts.poses?.get?.(b.id) || poseOf(b)), th = o.angle * Math.PI / 180, L = o.len * S, tip = {x: p.x + Math.cos(th) * L, y: p.y - Math.sin(th) * L};
        s = arrow(p, tip, {width: 1.8 * ss, head: HL * 1.1}) + (o.label ? lbl(o.label, tip.x + Math.cos(th) * 13, tip.y - Math.sin(th) * 13, 16) : '') + hit(`M${f(p.x)},${f(p.y)}L${f(tip.x)},${f(tip.y)}`); }

    /* ── electromagnetism ── */
    } else if (T === 'element') {
      s = drawElement(o);
    } else if (T === 'ground') {
      const c = screen(o), w = 12 * Math.sqrt(ss);
      s = line(c, {x: c.x, y: c.y + 10}, thin) + line({x: c.x - w, y: c.y + 10}, {x: c.x + w, y: c.y + 10}, lw) + line({x: c.x - w * 0.62, y: c.y + 14.5}, {x: c.x + w * 0.62, y: c.y + 14.5}, lw) + line({x: c.x - w * 0.25, y: c.y + 19}, {x: c.x + w * 0.25, y: c.y + 19}, lw)
        + (o.label ? lbl(o.label, c.x + w + 6, c.y + 14, 14, 'start') : '') + hitBox(c.x - w, c.y, 2 * w, 20);
    } else if (T === 'charge') {
      const c = screen(o), r = Math.max(6, o.r * S), pos = o.q >= 0;
      if (o.trail) { const pts = chargePath(scene, o, view).map(screen); if (pts.length > 1) s += poly(pts, thin, dash('dashed')) + midHead(pts, 0.35, {len: HL * 0.8}) + midHead(pts, 0.8, {len: HL * 0.8}); }
      s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r)}" fill="${pos ? fill : gray || '#fff'}" stroke="${ink}" stroke-width="${f(thin * 1.15)}"/>` + (pos ? plus(c, r * 0.55, Math.max(1, r * 0.16)) : minus(c, r * 0.55, Math.max(1, r * 0.16)));
      if (o.showV && Math.hypot(o.vx, o.vy) > 1e-9) { const sp = Math.hypot(o.vx, o.vy), ux = o.vx / sp, uy = -o.vy / sp, L = Math.max(34, Math.min(80, 0.12 * W)), tip = {x: c.x + ux * (r + L), y: c.y + uy * (r + L)};
        s += arrow({x: c.x + ux * r, y: c.y + uy * r}, tip, {width: 1.5 * ss}) + (o.vLabel ? (() => { let nx = -uy, ny = ux; if (ny > 0) { nx = -nx; ny = -ny; } return lbl(o.vLabel, c.x + ux * (r + L * 0.55) + nx * 14, c.y + uy * (r + L * 0.55) + ny * 14, 15, 'middle', '', {halo: true}); })() : ''); }
      if (o.label) s += lbl(o.label, c.x + r * 0.75 + 4, c.y - r - 9, 15, 'start', '', {halo: true});
    } else if (T === 'plate') {
      const a = screen({x: o.x1, y: o.y1}), b = screen({x: o.x2, y: o.y2}), L = Math.hypot(b.x - a.x, b.y - a.y), u = {x: (b.x - a.x) / L, y: (b.y - a.y) / L};
      let n = {x: -u.y, y: u.x};
      const plates = scene.objects.filter(p => p.type === 'plate'), pc = screen({x: plates.reduce((t, p) => t + p.x1 + p.x2, 0) / (2 * plates.length), y: plates.reduce((t, p) => t + p.y1 + p.y2, 0) / (2 * plates.length)});
      if (plates.length > 1 && (n.x * (pc.x - (a.x + b.x) / 2) + n.y * (pc.y - (a.y + b.y) / 2)) > 0) n = {x: -n.x, y: -n.y};
      if (plates.length === 1 && n.y > 0) n = {x: -n.x, y: -n.y};
      s = line(a, b, Math.max(3, lw * 2), ' stroke-linecap="butt"');
      if (o.marks && o.q) { const k = Math.max(2, Math.floor(L / 26)); for (let i = 0; i < k; i++) { const t = (i + 0.5) / k, c = {x: a.x + (b.x - a.x) * t + n.x * 10, y: a.y + (b.y - a.y) * t + n.y * 10}; s += o.q > 0 ? plus(c, 4) : minus(c, 4); } }
      if (o.label) s += lbl(o.label, b.x + n.x * 12 + u.x * 12, b.y + n.y * 12 + u.y * 12, 15, 'start');
      s += hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`);
    } else if (T === 'fieldlines') {
      const lines = fieldLines(scene, view, {n: o.n});
      for (const L of lines) { const pts = L.pts.map(screen); s += poly(pts, thin * 0.85); if (o.arrows && L.arrow) s += midHead(pts, L.arrow.at, {len: HL * 0.85}); }
      if (o.equip) for (const e of equipotentials(scene, view, {levels: o.levels})) s += poly(e.pts.map(screen), hair, ` stroke-opacity="0.85"${dash('dashed', 0.8)}`);
    } else if (T === 'field') {
      const p0 = screen({x: o.x, y: o.y + o.h}), w = o.w * S, h = o.h * S;
      if (o.pattern !== 'none') s += `<rect x="${f(p0.x)}" y="${f(p0.y)}" width="${f(w)}" height="${f(h)}" fill="none" stroke="${ink}" stroke-width="${f(hair)}"${dash(o.pattern)}/>`;
      const sp = o.spacing * S, r = Math.max(3.5, Math.min(7, sp * 0.18)) * Math.sqrt(ss);
      if (o.dir === 'arrow') {
        const a = o.angle * Math.PI / 180, u = {x: Math.cos(a), y: -Math.sin(a)}, nn = {x: -u.y, y: u.x}, c = {x: p0.x + w / 2, y: p0.y + h / 2}, R = Math.hypot(w, h) / 2;
        for (let t = -Math.floor(R / sp) * sp; t <= R; t += sp) {
          /* the line c + nn t + u s clipped to the rectangle */
          let lo = -1e9, hi = 1e9; const q = {x: c.x + nn.x * t, y: c.y + nn.y * t};
          for (const [pp, uu, mn, mx] of [[q.x, u.x, p0.x, p0.x + w], [q.y, u.y, p0.y, p0.y + h]]) { if (Math.abs(uu) < 1e-9) { if (pp < mn || pp > mx) { lo = 1; hi = 0; } } else { const s1 = (mn - pp) / uu, s2 = (mx - pp) / uu; lo = Math.max(lo, Math.min(s1, s2)); hi = Math.min(hi, Math.max(s1, s2)); } }
          if (hi - lo < sp * 0.6) continue;
          const A = {x: q.x + u.x * (lo + 3), y: q.y + u.y * (lo + 3)}, B = {x: q.x + u.x * (hi - 3), y: q.y + u.y * (hi - 3)};
          s += arrow(A, B, {width: thin, head: HL * 0.85});
        }
      } else {
        const nx = Math.max(1, Math.floor(w / sp)), ny = Math.max(1, Math.floor(h / sp)), ox = (w - (nx - 1) * sp) / 2, oy = (h - (ny - 1) * sp) / 2;
        for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) { const c = {x: p0.x + ox + i * sp, y: p0.y + oy + j * sp}; if (nx * ny > 900) break; s += o.dir === 'out' ? dotSym(c, r) : crossSym(c, r); }
      }
      if (o.label) s += lbl(o.label, p0.x + w + 6, p0.y + 10, 16, 'start');
      s += hitBox(p0.x, p0.y, w, h);
    } else if (T === 'cwire') {
      const a = screen({x: o.x1, y: o.y1}), b = screen({x: o.x2, y: o.y2}), L = Math.hypot(b.x - a.x, b.y - a.y), u = {x: (b.x - a.x) / L, y: (b.y - a.y) / L}, m = {x: (a.x + b.x) / 2, y: (a.y + b.y) / 2}, sg = o.I < 0 ? -1 : 1;
      s = line(a, b, lw * 1.25);
      if (o.arrow) s += head({x: m.x + sg * u.x * HL * 0.6, y: m.y + sg * u.y * HL * 0.6}, sg * u.x, sg * u.y, {len: HL * 1.1})[0];
      if (o.label) { let n = {x: -u.y, y: u.x}; if (n.y > 0) n = {x: -n.x, y: -n.y}; s += lbl(o.label, m.x + n.x * 15, m.y + n.y * 15, 15); }
      s += hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`);
    } else if (T === 'current') {
      const c = screen(o), r = Math.max(5, o.r * S);
      for (let k = 1; k <= o.rings; k++) {
        const R = r + k * Math.max(16, r * 1.6), ccw = (o.dir === 'out') === (o.I >= 0);
        s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(R)}" fill="none" stroke="${ink}" stroke-width="${f(hair)}"${dash('dashed', 0.8)}/>`;
        /* the arrow on the ring's top runs left for an anticlockwise B (seen with y up on the page) */
        s += head({x: c.x + (ccw ? -1 : 1) * 2, y: c.y - R}, ccw ? -1 : 1, 0, {len: HL * 0.8})[0];
      }
      s += o.dir === 'out' ? dotSym(c, r) : crossSym(c, r);
      if (o.label) s += lbl(o.label, c.x + r + 4, c.y + r + 8, 15, 'start', '', {halo: true});
    } else if (T === 'solenoid') {
      const p0 = screen({x: o.x, y: o.y + o.h}), w = o.w * S, h = o.h * S, n = Math.round(o.turns), pitch = w / n, cy = p0.y + h / 2;
      if (o.core) s += `<rect x="${f(p0.x - 4)}" y="${f(cy - h * 0.28)}" width="${f(w + 8)}" height="${f(h * 0.56)}" fill="${gray || 'none'}" stroke="${ink}" stroke-width="${f(hair)}"/>`;
      /* a prolate cycloid: one loop a turn */
      let d = ''; const N = n * 36, aa = pitch * 0.42;
      for (let i = 0; i <= N; i++) { const t = 2 * Math.PI * i / 36, x = p0.x + pitch * (t / (2 * Math.PI)) - aa * Math.sin(t), y = cy + (h / 2) * Math.cos(t); d += (i ? 'L' : 'M') + f(x + pitch * 0.25) + ',' + f(y); }
      s += `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(thin * 1.1)}" stroke-linejoin="round"/>`;
      const e0 = {x: p0.x + pitch * 0.25, y: cy + h / 2}, e1 = {x: p0.x + pitch * (n + 0.25), y: cy + h / 2};
      s += line(e0, {x: e0.x, y: e0.y + 18}, thin) + line(e1, {x: e1.x, y: e1.y + 18}, thin);
      s += head({x: e0.x, y: e0.y + 6}, 0, -1, {len: HL * 0.8})[0] + head({x: e1.x, y: e1.y + 14}, 0, 1, {len: HL * 0.8})[0];
      if (o.label) s += lbl(o.label, e0.x - 9, e0.y + 14, 15, 'end');
      if (o.showB) s += arrow({x: p0.x + w * 0.2, y: cy}, {x: p0.x + w * 0.85, y: cy}, {width: lw}) + lbl('\\vec{B}', p0.x + w * 0.88 + 6, cy - 12, 15, 'start', '', {halo: true});
      s += hitBox(p0.x, p0.y, w, h);
    } else if (T === 'loop') {
      const c = screen(o), rx = o.r * S, ry = o.r * o.tilt * S;
      s = `<ellipse cx="${f(c.x)}" cy="${f(c.y)}" rx="${f(rx)}" ry="${f(ry)}" fill="none" stroke="${ink}" stroke-width="${f(lw)}"/>`;
      s += head({x: c.x + (o.ccw ? 1 : -1) * HL * 0.5, y: c.y + ry}, o.ccw ? 1 : -1, 0, {len: HL})[0];
      if (o.label) s += lbl(o.label, c.x, c.y + ry + 15, 15);
      s += hitBox(c.x - rx, c.y - ry, 2 * rx, 2 * ry);
    } else if (T === 'magnet') {
      const p0 = screen({x: o.x, y: o.y + o.h}), w = o.w * S, h = o.h * S, left = o.flip ? 'S' : 'N', right = o.flip ? 'N' : 'S', nLeft = !o.flip;
      const nRect = nLeft ? `rect x="${f(p0.x)}" y="${f(p0.y)}" width="${f(w / 2)}" height="${f(h)}"` : `rect x="${f(p0.x + w / 2)}" y="${f(p0.y)}" width="${f(w / 2)}" height="${f(h)}"`;
      s += `<${nRect} fill="${gray || '#fff'}" stroke="none"/>` + shade(nRect, 'gray');
      s += `<rect x="${f(p0.x)}" y="${f(p0.y)}" width="${f(w)}" height="${f(h)}" fill="none" stroke="${ink}" stroke-width="${f(lw)}"/>` + line({x: p0.x + w / 2, y: p0.y}, {x: p0.x + w / 2, y: p0.y + h}, thin);
      s += lbl(`\\mathrm{${left}}`, p0.x + w / 4, p0.y + h / 2, Math.min(18, h * 0.6 / CUR.ls), 'middle', '', {halo: !gray}) + lbl(`\\mathrm{${right}}`, p0.x + 3 * w / 4, p0.y + h / 2, Math.min(18, h * 0.6 / CUR.ls));
      if (o.showB) {
        const nx = nLeft ? p0.x : p0.x + w, sx = nLeft ? p0.x + w : p0.x;
        for (const k of [1, 2]) for (const sg of [-1, 1]) {
          const lift = h * (0.5 + k * 0.9), y0 = p0.y + h / 2 + sg * h * 0.25, d = `M${f(nx)},${f(y0)}C${f(nx - (sx - nx) * 0.35 * k)},${f(y0 - sg * lift * -1)} ${f(sx + (sx - nx) * 0.35 * k)},${f(y0 - sg * lift * -1)} ${f(sx)},${f(y0)}`;
          s += `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(hair)}"/>`;
          const top = {x: (nx + sx) / 2, y: y0 + sg * lift * 0.75}; s += head(top, Math.sign(sx - nx), 0, {len: HL * 0.75})[0];
        }
      }
      s += hitBox(p0.x, p0.y, w, h);

    /* ── thermodynamics ── */
    } else if (T === 'cylinder') {
      const p0 = screen({x: o.x, y: o.y + o.h}), w = o.w * S, h = o.h * S, bot = p0.y + h, wall = Math.max(3, lw * 1.8);
      const py = bot - o.piston * h, pt = Math.max(7, h * 0.07);
      if (o.gas) { let k = 1; const n = Math.round(Math.min(90, (w * (bot - py)) / 260)); for (let i = 0; i < n; i++) { k = (k * 16807) % 2147483647; const rx = (k % 1000) / 1000; k = (k * 16807) % 2147483647; const ry = (k % 1000) / 1000; s += `<circle cx="${f(p0.x + 6 + rx * (w - 12))}" cy="${f(py + pt / 2 + 6 + ry * (bot - py - pt / 2 - 12))}" r="${f(1.4 * Math.sqrt(ss))}" fill="${ink}"/>`; } }
      s += `<path d="M${f(p0.x)},${f(p0.y)}V${f(bot)}H${f(p0.x + w)}V${f(p0.y)}" fill="none" stroke="${ink}" stroke-width="${f(wall)}" stroke-linejoin="miter"/>`;
      s += hatch(p0.x - wall / 2, bot, p0.x - wall / 2, p0.y, -1, 0) + hatch(p0.x + w + wall / 2, p0.y, p0.x + w + wall / 2, bot, 1, 0);
      const pr = `rect x="${f(p0.x + wall / 2)}" y="${f(py - pt / 2)}" width="${f(w - wall)}" height="${f(pt)}"`;
      s += `<${pr} fill="${gray || '#fff'}" stroke="${ink}" stroke-width="${f(thin)}"/>` + shade(pr, 'gray');
      if (o.weight) { const bw = w * 0.42, bh = Math.max(12, h * 0.14); s += `<rect x="${f(p0.x + (w - bw) / 2)}" y="${f(py - pt / 2 - bh)}" width="${f(bw)}" height="${f(bh)}" fill="${fill}" stroke="${ink}" stroke-width="${f(lw)}"/>`; }
      if (o.heat !== 'none') { const x0 = p0.x + w / 2, a = {x: x0, y: bot + 28}, b = {x: x0, y: bot + 6}; s += o.heat === 'in' ? arrow(a, b, {width: lw}) : arrow(b, a, {width: lw}); s += lbl('Q', x0 + 10, bot + 18, 15, 'start'); }
      if (o.label) s += lbl(o.label, p0.x + w / 2, (py + bot) / 2, 15, 'middle', '', {halo: true});
      s += hitBox(p0.x, p0.y, w, h);
    } else if (T === 'reservoir') {
      const p0 = screen({x: o.x, y: o.y + o.h}), w = o.w * S, h = o.h * S, r = `rect x="${f(p0.x)}" y="${f(p0.y)}" width="${f(w)}" height="${f(h)}"`;
      s += `<${r} fill="${gray ? (o.hot ? gray : light) : '#fff'}" stroke="${ink}" stroke-width="${f(lw)}"/>` + (o.hot ? shade(r, 'gray') : '');
      if (o.label) s += lbl(o.label, p0.x + w / 2, p0.y + h / 2, 16, 'middle', '', {halo: true});
      s += hitBox(p0.x, p0.y, w, h);
    } else if (T === 'engine') {
      const c = screen(o), k = o.size * S, bw = 2.2 * k, bh = 0.5 * k, r = 0.36 * k, fr = o.kind === 'fridge';
      const hot = {x: c.x - bw / 2, y: c.y - 1.45 * k}, cold = {x: c.x - bw / 2, y: c.y + 0.95 * k};
      for (const [b, t, isHot] of [[hot, o.th, true], [cold, o.tc, false]]) { const rr = `rect x="${f(b.x)}" y="${f(b.y)}" width="${f(bw)}" height="${f(bh)}"`; s += `<${rr} fill="${gray ? (isHot ? gray : light) : '#fff'}" stroke="${ink}" stroke-width="${f(lw)}"/>` + (isHot ? shade(rr, 'gray') : '') + lbl(t, c.x, b.y + bh / 2, 16, 'middle', '', {halo: true}); }
      s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r)}" fill="${fill}" stroke="${ink}" stroke-width="${f(lw)}"/>`;
      const up = {x: c.x, y: hot.y + bh}, dn = {x: c.x, y: cold.y}, aw = lw * 1.1;
      s += fr ? arrow({x: c.x, y: c.y - r}, up, {width: aw}) + arrow(dn, {x: c.x, y: c.y + r}, {width: aw}) + arrow({x: c.x + r + 0.75 * k, y: c.y}, {x: c.x + r, y: c.y}, {width: aw})
        : arrow(up, {x: c.x, y: c.y - r}, {width: aw}) + arrow({x: c.x, y: c.y + r}, dn, {width: aw}) + arrow({x: c.x + r, y: c.y}, {x: c.x + r + 0.75 * k, y: c.y}, {width: aw});
      s += lbl(o.qh, c.x + 10, (up.y + c.y - r) / 2, 15, 'start') + lbl(o.qc, c.x + 10, (dn.y + c.y + r) / 2, 15, 'start') + lbl(o.wl, c.x + r + 0.4 * k, c.y - 13, 15);
      s += hitBox(c.x - bw / 2, hot.y, bw, cold.y + bh - hot.y);
    } else if (T === 'graph') {
      const r = ranges.get(o.id), p0 = screen({x: o.x, y: o.y}), w = o.w * S, h = o.h * S;
      const ax = r.y0 <= 0 && r.y1 >= 0 ? toGraph(o, {x: r.x0, y: 0}).y : p0.y, ay = r.x0 <= 0 && r.x1 >= 0 ? toGraph(o, {x: 0, y: r.y0}).x : p0.x;
      if (o.grid || o.ticks) {
        const step = v => { const raw = v / 6, p = Math.pow(10, Math.floor(Math.log10(raw))), m = raw / p; return (m < 1.5 ? 1 : m < 3.5 ? 2 : m < 7.5 ? 5 : 10) * p; };
        const sx = step(r.x1 - r.x0), sy = step(r.y1 - r.y0);
        for (let v = Math.ceil(r.x0 / sx) * sx; v <= r.x1 + 1e-9; v += sx) { const q = toGraph(o, {x: v, y: r.y0}); if (o.grid) s += line({x: q.x, y: p0.y}, {x: q.x, y: p0.y - h}, 0.5, ' stroke="#bbb"'); if (o.ticks && Math.abs(v) > sx * 1e-6) s += line({x: q.x, y: ax}, {x: q.x, y: ax + 4}, hair) + lbl(`\\mathrm{${+v.toPrecision(3)}}`, q.x, ax + 13, 11); }
        for (let v = Math.ceil(r.y0 / sy) * sy; v <= r.y1 + 1e-9; v += sy) { const q = toGraph(o, {x: r.x0, y: v}); if (o.grid) s += line({x: p0.x, y: q.y}, {x: p0.x + w, y: q.y}, 0.5, ' stroke="#bbb"'); if (o.ticks && Math.abs(v) > sy * 1e-6) s += line({x: ay, y: q.y}, {x: ay - 4, y: q.y}, hair) + lbl(`\\mathrm{${+v.toPrecision(3)}}`, ay - 6, q.y, 11, 'end'); }
      }
      s += arrow({x: p0.x - 4, y: ax}, {x: p0.x + w + 0.07 * w, y: ax}, {width: thin}) + arrow({x: ay, y: p0.y + 4}, {x: ay, y: p0.y - h - 0.07 * h}, {width: thin});
      s += lbl(o.xlabel, p0.x + w * 1.07 + 6, ax + 2, 16, 'start') + lbl(o.ylabel, ay - 6, p0.y - h * 1.07 - 4, 16, 'end');
      if (o.origin) s += lbl(o.origin, ay - 8, ax + 11, 14, 'middle');
      s += hitBox(p0.x, p0.y - h, w, h);
    } else if (T === 'curve') {
      const g = byId.get(o.graph); if (g && ranges.has(g.id)) {
        const r = ranges.get(g.id), segs = [[]];
        if (o.kind === 'func') {
          const fn = compileExpr(o.expr), N = 400, x0 = Math.max(o.x1, r.x0), x1 = Math.min(o.x2, r.x1), ylo = r.y0 - (r.y1 - r.y0) * 0.02, yhi = r.y1 + (r.y1 - r.y0) * 0.02;
          for (let i = 0; i <= N && fn; i++) { const x = x0 + (x1 - x0) * i / N, y = fn(x); if (Number.isFinite(y) && y >= ylo && y <= yhi) segs[segs.length - 1].push(toGraph(g, {x, y})); else if (segs[segs.length - 1].length) segs.push([]); }
        } else segs[0] = processPoints(o.kind, o).map(p => toGraph(g, p));
        for (const sg of segs) if (sg.length > 1) s += poly(sg, lw * 0.9, dash(o.pattern)) + hit('M' + sg.map(p => `${f(p.x)},${f(p.y)}`).join('L'));
        const main = segs.reduce((a, b) => b.length > a.length ? b : a, []);
        if (main.length > 1) {
          if (o.heads === 'mid') s += midHead(main, 0.5); else if (o.heads === 'end') { const a = main[main.length - 2], b = main[main.length - 1], l = Math.hypot(b.x - a.x, b.y - a.y) || 1; s += head(b, (b.x - a.x) / l, (b.y - a.y) / l)[0]; }
          if (o.label) { const e = main[main.length - 1]; s += lbl(o.label, e.x + 6, e.y - 10, 15, 'start', '', {halo: true}); }
        }
      }
    } else if (T === 'cycle') {
      const g = byId.get(o.graph); if (g && ranges.has(g.id)) {
        const c = gasCycle(o), all = c.legs.flatMap(l => l.pts.map(p => toGraph(g, p)));
        if (o.shade && all.length > 2) { const pg = `polygon points="${all.map(p => `${f(p.x)},${f(p.y)}`).join(' ')}"`; s += `<${pg} fill="${gray ? light : 'none'}" stroke="none"/>` + (gray ? '' : shade(pg, 'hatch')); }
        for (const l of c.legs) { const pts = l.pts.map(p => toGraph(g, p)); s += poly(pts, lw) + (o.arrows ? midHead(pts, 0.55) : ''); }
        const cen = {x: all.reduce((t, p) => t + p.x, 0) / all.length, y: all.reduce((t, p) => t + p.y, 0) / all.length};
        if (o.labels) {
          for (const st2 of c.states) { const p = toGraph(g, {x: st2.V, y: st2.P}), u = vec.unit(vec.sub(p, cen)); s += `<circle cx="${f(p.x)}" cy="${f(p.y)}" r="${f(2.4 * Math.sqrt(ss))}" fill="${ink}"/>` + lbl(st2.name, p.x + u.x * 13, p.y + u.y * 13, 15); }
          c.legs.forEach(l => { if (l.kind !== 'isotherm') return; const m = l.pts[Math.floor(l.pts.length / 2)], p = toGraph(g, m), u = vec.unit(vec.sub(p, cen)); s += lbl(l.from === 'A' ? 'T_H' : 'T_C', p.x + u.x * 18, p.y + u.y * 18, 14, 'middle', '', {halo: true}); });
        }
        s += hit('M' + all.map(p => `${f(p.x)},${f(p.y)}`).join('L'));
      }

    /* ── optics ── */
    } else if (T === 'lens') {
      const c = screen(o), h = o.h * S / 2, t = Math.min(16, Math.max(7, h * 0.16)) * Math.sqrt(ss);
      const d = o.f > 0 ? `M${f(c.x)},${f(c.y - h)}Q${f(c.x + t * 2)},${f(c.y)} ${f(c.x)},${f(c.y + h)}Q${f(c.x - t * 2)},${f(c.y)} ${f(c.x)},${f(c.y - h)}Z`
        : `M${f(c.x - t)},${f(c.y - h)}H${f(c.x + t)}Q${f(c.x + t * 0.15)},${f(c.y)} ${f(c.x + t)},${f(c.y + h)}H${f(c.x - t)}Q${f(c.x - t * 0.15)},${f(c.y)} ${f(c.x - t)},${f(c.y - h)}Z`;
      s += `<path d="${d}" fill="${light}" stroke="${ink}" stroke-width="${f(thin * 1.1)}" stroke-linejoin="round"/>`;
      if (o.showF) for (const sg of [-1, 1]) { const q = screen({x: o.x + sg * Math.abs(o.f), y: o.y}); if (q.x > -50 && q.x < W + 50) s += `<circle cx="${f(q.x)}" cy="${f(q.y)}" r="${f(2.6 * Math.sqrt(ss))}" fill="${ink}"/>` + lbl(sg < 0 ? 'F' : "F'", q.x, q.y + 14, 14); }
      if (o.label) s += lbl(o.label, c.x, c.y - h - 12, 15);
      s += hitBox(c.x - t - 4, c.y - h, 2 * t + 8, 2 * h);
    } else if (T === 'mirror') {
      const c = screen(o), h = o.h * S / 2, back = o.face === 'left' ? 1 : -1;
      let d;
      if (!o.f) d = `M${f(c.x)},${f(c.y - h)}V${f(c.y + h)}`;
      else { const sag = Math.min(0.14 * h * 2, h * h / (4 * Math.abs(o.f) * S)), bend = (o.f > 0 ? -back : back) * sag; d = `M${f(c.x + bend)},${f(c.y - h)}Q${f(c.x - bend)},${f(c.y)} ${f(c.x + bend)},${f(c.y + h)}`; }
      s += `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(lw * 1.2)}"/>`;
      /* hatching on the back: the curve is x = c.x + bend·τ², τ = (y − c.y)/h */
      const bend2 = o.f ? Math.min(0.14 * h * 2, h * h / (4 * Math.abs(o.f) * S)) * (o.f > 0 ? -back : back) : 0, N = Math.max(4, Math.floor(2 * h / st.hatchGap)); let hd = '';
      for (let i = 0; i <= N; i++) { const tt = -1 + 2 * i / N; hd += `M${f(c.x + bend2 * tt * tt)},${f(c.y + h * tt)}l${f(back * 7)},${f(5)}`; }
      s += `<path d="${hd}" stroke="${ink}" stroke-width="${f(st.hatchW * ss)}" fill="none"/>`;
      if (o.showF && o.f) { const pts = [[o.x - (o.face === 'left' ? 1 : -1) * o.f, 'F'], [o.x - (o.face === 'left' ? 1 : -1) * 2 * o.f, 'C']]; for (const [xx, t] of pts) { const q = screen({x: xx, y: o.y}); if (q.x > -50 && q.x < W + 50) s += `<circle cx="${f(q.x)}" cy="${f(q.y)}" r="${f(2.6 * Math.sqrt(ss))}" fill="${ink}"/>` + lbl(t, q.x, q.y + 14, 14); } }
      if (o.label) s += lbl(o.label, c.x, c.y - h - 12, 15);
      s += hitBox(c.x - 8, c.y - h, 16, 2 * h);
    } else if (T === 'prism' || T === 'slab') {
      const pts = (T === 'prism' ? prismCorners(o) : [{x: o.x, y: o.y}, {x: o.x + o.w, y: o.y}, {x: o.x + o.w, y: o.y + o.h}, {x: o.x, y: o.y + o.h}]).map(screen);
      s += `<polygon points="${pts.map(p => `${f(p.x)},${f(p.y)}`).join(' ')}" fill="${light}" stroke="${ink}" stroke-width="${f(lw)}" stroke-linejoin="round"/>`;
      const cen = {x: pts.reduce((t, p) => t + p.x, 0) / pts.length, y: pts.reduce((t, p) => t + p.y, 0) / pts.length};
      if (o.label) s += lbl(o.label, cen.x + (T === 'slab' ? pts[1].x - cen.x - 16 : 0), cen.y + (T === 'prism' ? 10 : pts[2].y - cen.y + 14), 15);
    } else if (T === 'oarrow') {
      const base = screen(o), tip = screen({x: o.x, y: o.y + o.h}), span = Math.hypot(view.w, view.h) * 1.6;
      if (o.rays) {
        const rays = principalRays(scene, o, span), im = o.image ? opticImage(scene, o, span) : null;
        for (const r of rays) { const pts = r.trace.pts.map(screen); s += poly(pts, thin); s += midHead(pts.slice(0, 2), 0.55, {len: HL * 0.8});
          if (im && !im.real) { const last = screen(r.trace.pts[r.trace.pts.length - 2]); s += line(last, screen(im.top), hair, dash('dashed')); } }
        if (im && Math.abs(im.h) < 1e3) { const b2 = screen({x: im.x, y: o.y}), t2 = screen(im.top); s += arrow(b2, t2, {width: lw, pattern: im.real ? 'solid' : 'dashed'}) + (o.imageLabel ? lbl(o.imageLabel, t2.x + 9, t2.y + (im.h > 0 ? -6 : 8), 15, 'start') : ''); }
      }
      s += arrow(base, tip, {width: lw * 1.05}) + (o.label ? lbl(o.label, tip.x - 9, tip.y + (o.h > 0 ? -4 : 6), 15, 'end') : '') + hit(`M${f(base.x)},${f(base.y)}L${f(tip.x)},${f(tip.y)}`);
    } else if (T === 'ray') {
      const a = o.angle * Math.PI / 180, tr = traceRay(scene, {x: o.x, y: o.y}, {x: Math.cos(a), y: Math.sin(a)}, {len: o.len}), pts = tr.pts.map(screen);
      s += poly(pts, thin * 1.15);
      if (o.arrow) for (let i = 0; i + 1 < pts.length; i++) s += midHead([pts[i], pts[i + 1]], 0.5, {len: HL * 0.8});
      if (o.label) s += lbl(o.label, pts[0].x - 6, pts[0].y - 10, 15, 'end');
      s += hit('M' + pts.map(p => `${f(p.x)},${f(p.y)}`).join('L'));
    } else if (T === 'slits') {
      const c = screen(o), h = o.h * S / 2, xs = screen({x: o.x + o.screen, y: o.y}).x, n = Math.round(o.n);
      const sep = n > 1 ? Math.min(h * 1.2 / (n - 1), h * 0.36) : 0, gw = Math.max(4, Math.min(sep * 0.3 || 10, 10));
      const ys = Array.from({length: n}, (_, i) => c.y + (i - (n - 1) / 2) * sep);
      let y = c.y - h; let bar = '';
      for (const sy of ys) { bar += `M${f(c.x)},${f(y)}V${f(sy - gw / 2)}`; y = sy + gw / 2; }
      bar += `M${f(c.x)},${f(y)}V${f(c.y + h)}`;
      s += `<path d="${bar}" stroke="${ink}" stroke-width="${f(Math.max(3, lw * 1.8))}" fill="none"/>`;
      s += line({x: xs, y: c.y - h}, {x: xs, y: c.y + h}, Math.max(2.5, lw * 1.4)) + hatch(xs + 2, c.y - h, xs + 2, c.y + h, 1, 0);
      if (o.waves) {
        for (let k = 1; k <= 4; k++) { const x = c.x - k * 16 * Math.sqrt(ss); s += line({x, y: c.y - h * 0.7}, {x, y: c.y + h * 0.7}, hair); }
        s += arrow({x: c.x - 82, y: c.y + h * 0.82}, {x: c.x - 18, y: c.y + h * 0.82}, {width: thin, head: HL * 0.8}) + lbl(`\\lambda = ${o.lambda}\\,\\mathrm{nm}`, c.x - 10, c.y + h * 0.82 + 14, 12, 'end', '', {halo: true});
        for (const sy of ys) for (let k = 1; k <= 3; k++) { const R = k * 22 * Math.sqrt(ss); s += `<path d="M${f(c.x + R * Math.cos(1.1))},${f(sy - R * Math.sin(1.1))}A${f(R)},${f(R)} 0 0 1 ${f(c.x + R * Math.cos(1.1))},${f(sy + R * Math.sin(1.1))}" fill="none" stroke="${ink}" stroke-width="${f(hair)}"${dash('dashed', 0.7)}/>`; }
      }
      if (o.pattern) {
        const Yr = slitRange(o), pts = [], amp = Math.min(0.75 * S, W - xs - 30);
        for (let i = 0; i <= 600; i++) { const yy = -Yr + 2 * Yr * i / 600, I = slitIntensity(o, yy); pts.push({x: xs + 8 + I * amp, y: c.y - yy / Yr * h}); }
        s += poly(pts, thin);
        if (o.labels) {
          const dy = fringeSpacing(o), q1 = c.y, q2 = c.y - dy / Yr * h, xd = xs - 12;
          if (n > 1 && dy < Yr) s += line({x: xd - 4, y: q1}, {x: xd + 4, y: q1}, hair) + line({x: xd - 4, y: q2}, {x: xd + 4, y: q2}, hair) + line({x: xd, y: q1}, {x: xd, y: q2}, hair) + lbl('\\Delta y', xd - 5, (q1 + q2) / 2, 14, 'end', '', {halo: true});
        }
      }
      if (o.labels) {
        if (n === 2) { s += lbl('S_1', c.x - 7, ys[0] - 3, 13, 'end', '', {halo: true}) + lbl('S_2', c.x - 7, ys[1] + 3, 13, 'end', '', {halo: true}); s += lbl('d', c.x + 9, c.y, 14, 'start', '', {halo: true}); }
        const yb = c.y + h + 14; s += arrow({x: (c.x + xs) / 2, y: yb}, {x: c.x, y: yb}, {width: hair, head: HL * 0.75, kind: st.dimHead}) + arrow({x: (c.x + xs) / 2, y: yb}, {x: xs, y: yb}, {width: hair, head: HL * 0.75, kind: st.dimHead}) + lbl('L', (c.x + xs) / 2, yb + 11, 14, 'middle', '', {halo: true});
      }
      s += hitBox(c.x - 6, c.y - h, xs - c.x + 12, 2 * h);
    } else if (T === 'wavefront') {
      const c = screen(o), sp = o.spacing * S;
      if (o.kind === 'circular') for (let k = 1; k <= o.n; k++) s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(k * sp)}" fill="none" stroke="${ink}" stroke-width="${f(thin)}"/>`;
      else { const a = o.angle * Math.PI / 180, u = {x: Math.cos(a), y: -Math.sin(a)}, nn = {x: -u.y, y: u.x}, h = o.h * S / 2;
        for (let k = 0; k < o.n; k++) { const m = {x: c.x + u.x * k * sp, y: c.y + u.y * k * sp}; s += line({x: m.x - nn.x * h, y: m.y - nn.y * h}, {x: m.x + nn.x * h, y: m.y + nn.y * h}, thin); } }
      s += hitBox(c.x - 10, c.y - 10, 20, 20);

    /* ── waves ── */
    } else if (T === 'wave') {
      const N = 400, k = o.kind === 'standing' ? o.n * Math.PI / o.len : 2 * Math.PI / o.lambda, ph = o.phase * Math.PI / 180;
      const yAt = x => o.kind === 'standing' ? o.A * Math.sin(k * x) : o.A * Math.sin(k * x + ph);
      const pts = [], env = [];
      for (let i = 0; i <= N; i++) { const x = o.len * i / N; pts.push(screen({x: o.x + x, y: o.y + yAt(x)})); env.push(screen({x: o.x + x, y: o.y - yAt(x)})); }
      const a0 = screen({x: o.x, y: o.y}), a1 = screen({x: o.x + o.len, y: o.y});
      if (o.axis) s += arrow(a0, {x: a1.x + 16, y: a1.y}, {width: hair}) + lbl('x', a1.x + 22, a1.y + 2, 15, 'start');
      if (o.kind === 'standing') { s += line(a0, a1, hair, dash('dotted')); if (o.envelope) s += poly(env, thin, dash('dashed')); }
      s += poly(pts, lw);
      if (o.ends === 'fixed') for (const p of [a0, a1]) { const sg = p === a0 ? -1 : 1, h2 = Math.max(16, o.A * S * 0.9); s += line({x: p.x, y: p.y - h2}, {x: p.x, y: p.y + h2}, lw * 1.3) + hatch(p.x, p.y - h2, p.x, p.y + h2, sg, 0); }
      const lam = o.kind === 'standing' ? 2 * o.len / o.n : o.lambda;
      if (o.showLambda) {
        let x1, yy;
        if (o.kind === 'standing') { x1 = 0; yy = o.y - o.A - 0.18 * o.A - 14 / S; }
        else { x1 = (((Math.PI / 2 - ph) / k) % lam + lam) % lam; yy = o.y + o.A + 14 / S; }
        if (x1 + lam <= o.len + 1e-9) { const p1 = screen({x: o.x + x1, y: yy}), p2 = screen({x: o.x + x1 + lam, y: yy}), m = {x: (p1.x + p2.x) / 2, y: p1.y};
          s += arrow(m, p1, {width: hair, head: HL * 0.75, kind: st.dimHead}) + arrow(m, p2, {width: hair, head: HL * 0.75, kind: st.dimHead}) + line({x: p1.x, y: p1.y - 5}, {x: p1.x, y: p1.y + 5}, hair) + line({x: p2.x, y: p2.y - 5}, {x: p2.x, y: p2.y + 5}, hair) + lbl('\\lambda', m.x, m.y - 10, 15, 'middle', '', {halo: true}); }
      }
      if (o.showA) {
        const xc = o.kind === 'standing' ? o.len / (2 * o.n) : ((((Math.PI / 2 - ph) / k) % lam + lam) % lam) + lam * (o.len > 1.6 * lam ? 1 : 0);
        if (xc <= o.len) { const p1 = screen({x: o.x + xc, y: o.y}), p2 = screen({x: o.x + xc, y: o.y + o.A}), xx = p1.x + 10; s += line(p2, {x: xx + 4, y: p2.y}, hair, dash('dotted')) + arrow({x: xx, y: (p1.y + p2.y) / 2}, {x: xx, y: p2.y}, {width: hair, head: HL * 0.7, kind: st.dimHead}) + arrow({x: xx, y: (p1.y + p2.y) / 2}, {x: xx, y: p1.y}, {width: hair, head: HL * 0.7, kind: st.dimHead}) + lbl('A', xx + 6, (p1.y + p2.y) / 2, 15, 'start', '', {halo: true}); }
      }
      if (o.arrow && o.kind === 'travel') { const p = screen({x: o.x + o.len * 0.78, y: o.y + o.A * 1.0 + 0.45 * Math.max(o.A, 0.3)}); s += arrow(p, {x: p.x + 0.12 * W, y: p.y}, {width: lw}) + (o.label ? lbl(o.label, p.x + 0.06 * W, p.y - 12, 15) : ''); }
      else if (o.label) s += lbl(o.label, a1.x, screen({x: 0, y: o.y + o.A}).y - 14, 15, 'end');
      s += hit('M' + pts.map(p => `${f(p.x)},${f(p.y)}`).join('L'));

    /* ── modern physics ── */
    } else if (T === 'well') {
      const m = wellModel(o), p0 = screen({x: o.x, y: o.y}), w = o.w * S, h = o.h * S, [x0, x1] = m.xs;
      const XW = x => p0.x + (x - x0) / (x1 - x0) * w, YE = E => p0.y - Math.min(1.05, E / m.Emax) * h;
      s += arrow({x: p0.x, y: p0.y}, {x: p0.x + w + 14, y: p0.y}, {width: thin}) + arrow({x: p0.x, y: p0.y}, {x: p0.x, y: p0.y - h - 14}, {width: thin}) + lbl('x', p0.x + w + 20, p0.y + 1, 15, 'start') + lbl('E', p0.x - 8, p0.y - h - 10, 15, 'end');
      /* V(x) */
      const vp = []; for (let i = 0; i <= 500; i++) { const x = x0 + (x1 - x0) * i / 500, V = m.V(x); vp.push({x: XW(x), y: Number.isFinite(V) ? YE(V) : p0.y - h * 1.02}); }
      if (o.kind === 'infinite') { const a = XW(m.walls[0]), b = XW(m.walls[1]); s += `<path d="M${f(a)},${f(p0.y - h)}V${f(p0.y)}H${f(b)}V${f(p0.y - h)}" fill="none" stroke="${ink}" stroke-width="${f(lw * 1.2)}"/>` + hatch(a, p0.y, a, p0.y - h, -1, 0) + hatch(b, p0.y - h, b, p0.y, 1, 0); }
      else s += poly(vp, lw * 1.2);
      if (o.kind !== 'infinite' && o.kind !== 'harmonic' && o.labels) s += lbl('V_0', XW(m.walls[m.walls.length - 1]) + 8, YE(o.V0) - 10, 14, 'start', '', {halo: true});
      if (o.kind === 'infinite' || o.kind === 'finite' || o.kind === 'barrier') { const a = XW(m.walls[0]), b = XW(m.walls[1]), yb = p0.y + 14; s += arrow({x: (a + b) / 2, y: yb}, {x: a, y: yb}, {width: hair, head: HL * 0.7, kind: st.dimHead}) + arrow({x: (a + b) / 2, y: yb}, {x: b, y: yb}, {width: hair, head: HL * 0.7, kind: st.dimHead}) + lbl('L', (a + b) / 2, yb + 11, 14); }
      const L = m.levels, gaps = L.map((l, i) => i ? YE(L[i - 1].E) - YE(l.E) : Infinity), amp = Math.max(6, Math.min(0.42 * Math.min(...gaps, h * 0.4), h * 0.18));
      L.forEach(l => {
        const yb = YE(l.E);
        s += line({x: p0.x, y: yb}, {x: p0.x + w, y: yb}, hair, dash('dashed', 0.7));
        if (o.psi !== 'none') {
          const vals = []; for (let i = 0; i <= 400; i++) { const x = x0 + (x1 - x0) * i / 400, v = l.psi(x); vals.push([x, o.psi === 'prob' ? v * v : v]); }
          const mx = Math.max(...vals.map(v => Math.abs(v[1]))) || 1;
          s += poly(vals.map(([x, v]) => ({x: XW(x), y: yb - amp * v / mx})), thin * 1.1);
        }
        if (o.labels) s += lbl(o.kind === 'barrier' || o.kind === 'step' ? `E` : o.kind === 'harmonic' ? `E_${l.n}` : `E_${l.n}`, p0.x + w + 6, yb, 14, 'start', '', {halo: true});
      });
      if (o.psi !== 'none' && o.labels && L.length) s += lbl(o.psi === 'prob' ? '|\\psi|^2' : '\\psi', p0.x + 8, p0.y - h + 8, 15, 'start', '', {halo: true});
      if (m.T !== undefined && o.labels) s += lbl(`T \\approx ${m.T < 1e-3 ? m.T.toExponential(1) : m.T.toFixed(3)}`, p0.x + w - 4, p0.y - h + 8, 13, 'end', '', {halo: true});
      s += hitBox(p0.x, p0.y - h, w, h);
    } else if (T === 'levels') {
      const m = levelModel(o), p0 = screen({x: o.x, y: o.y}), w = o.w * S, h = o.h * S, E = m.levels;
      if (E.length) {
        const lo = Math.min(...E.map(l => l.E)), hi = o.kind === 'hydrogen' ? 0 : Math.max(...E.map(l => l.E)), YE = e => p0.y - (e - lo) / ((hi - lo) || 1) * h;
        let lastY = Infinity; for (const l of [...E].sort((a2, b2) => a2.E - b2.E)) { const y = YE(l.E); s += line({x: p0.x, y}, {x: p0.x + w, y}, lw); const room = lastY - y > 11 * CUR.ls && (o.kind !== 'hydrogen' || -YE(0) + y > 11 * CUR.ls); if (room) lastY = y; if (o.labels && room) s += lbl(o.kind === 'hydrogen' ? `n = ${l.n}` : `E_${l.n}`, p0.x - 6, y, 13, 'end') + lbl(`\\mathrm{${l.E.toFixed(2)}\\,eV}`, p0.x + w + 6, y, 12, 'start'); }
        if (o.kind === 'hydrogen') { const y = YE(0); s += line({x: p0.x, y}, {x: p0.x + w, y}, thin, dash('dashed')) + (o.labels ? lbl('n = \\infty', p0.x - 6, y, 13, 'end') + lbl('\\mathrm{0\\,eV}', p0.x + w + 6, y, 12, 'start') : ''); }
        m.trans.forEach((t, i) => {
          const x = p0.x + w * (0.18 + 0.64 * (m.trans.length > 1 ? i / (m.trans.length - 1) : 0.5)), a = {x, y: YE(E[t.from - 1].E)}, b = {x, y: YE(E[t.to - 1].E)};
          s += arrow(a, b, {width: thin * 1.2});
          if (o.showLambda) s += lbl(`\\mathrm{${t.lambda.toFixed(0)}\\,nm}`, x + 4, (a.y + b.y) / 2, 11, 'start', '', {halo: true});
        });
      }
      s += hitBox(p0.x, p0.y - h, w, h);
    } else if (T === 'phototube') {
      const p0 = screen({x: o.x, y: o.y + o.h}), w = o.w * S, h = o.h * S, tw = w * 0.62, th = h * 0.46, tx = p0.x + (w - tw) / 2, ty = p0.y + h * 0.04;
      s += `<rect x="${f(tx)}" y="${f(ty)}" width="${f(tw)}" height="${f(th)}" rx="${f(th / 2)}" fill="${light}" stroke="${ink}" stroke-width="${f(lw)}"/>`;
      const cx = tx + tw * 0.2, ax = tx + tw * 0.82, cy = ty + th / 2;
      s += `<path d="M${f(cx + 6)},${f(cy - th * 0.32)}Q${f(cx - 8)},${f(cy)} ${f(cx + 6)},${f(cy + th * 0.32)}" fill="none" stroke="${ink}" stroke-width="${f(lw * 1.8)}"/>` + line({x: ax, y: cy - th * 0.25}, {x: ax, y: cy + th * 0.25}, lw * 1.8);
      for (let k = 0; k < 3; k++) { const y = cy - th * 0.15 + k * th * 0.15; s += arrow({x: cx + 10, y}, {x: ax - 10, y: y + (k - 1) * 2}, {width: hair, head: HL * 0.6}); }
      s += lbl('e^-', (cx + ax) / 2, cy - th * 0.3, 12, 'middle', '', {halo: true});
      for (let k = 0; k < 3; k++) { const sx = tx - 30 + k * 12, sy = p0.y - 6 + k * 3; let d = `M${f(sx)},${f(sy)}`; for (let i = 1; i <= 24; i++) { const t = i / 24; d += `L${f(sx + (cx - sx - 4) * t + Math.sin(t * 18) * 2.2)},${f(sy + (cy - sy - 6) * t - Math.cos(t * 18) * 2.2)}`; } s += `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(hair)}"/>`; }
      if (o.label) s += lbl(o.label, tx - 34, p0.y - 4, 15, 'end');
      /* the outer circuit: cathode down, a battery, an ammeter, up to the anode */
      const yb = p0.y + h * 0.85;
      s += poly([{x: cx - 2, y: cy + th * 0.32}, {x: cx - 2, y: yb}, {x: (p0.x + w / 2) - 22, y: yb}], thin * 1.1) + poly([{x: (p0.x + w / 2) + 22, y: yb}, {x: ax + 26, y: yb}, {x: ax + 26, y: cy}, {x: ax, y: cy}], thin * 1.1);
      const bx = p0.x + w / 2; s += line({x: bx - 22, y: yb}, {x: bx - 4, y: yb}, thin * 1.1) + line({x: bx - 4, y: yb - 11}, {x: bx - 4, y: yb + 11}, thin * 1.2) + line({x: bx + 4, y: yb - 5.5}, {x: bx + 4, y: yb + 5.5}, lw * 1.8) + line({x: bx + 4, y: yb}, {x: bx + 22, y: yb}, thin * 1.1);
      const am = {x: ax + 26, y: (yb + cy) / 2}; s += `<circle cx="${f(am.x)}" cy="${f(am.y)}" r="11" fill="#fff" stroke="${ink}" stroke-width="${f(thin * 1.1)}"/>` + lbl('\\mathrm{A}', am.x, am.y, 13, 'middle', '', {raw: true});
      s += lbl('V', bx, yb + 20, 14);
      s += hitBox(p0.x, p0.y, w, h);
    } else if (T === 'spacetime') {
      const O = screen(o), u = o.size / o.units * S, top = o.size * S, left = o.size * 0.55 * S;
      if (o.grid) for (let k = -o.units; k <= o.units; k++) { const g = lorentzGamma(o.beta), b = o.beta; /* lines of constant x′ and ct′ */
        const A = {x: O.x + (k * g) * u, y: O.y - (k * g * b) * u}, B = {x: A.x + b * top, y: A.y - top}; s += line(A, B, 0.5, ' stroke="#aaa"');
        const C = {x: O.x + (k * g * b) * u, y: O.y - (k * g) * u}, D = {x: C.x + top, y: C.y - b * top}; s += line(C, D, 0.5, ' stroke="#aaa"'); }
      s += arrow({x: O.x - left, y: O.y}, {x: O.x + top + 12, y: O.y}, {width: thin}) + arrow({x: O.x, y: O.y + 6}, {x: O.x, y: O.y - top - 12}, {width: thin});
      s += lbl(o.xlabel, O.x + top + 18, O.y + 2, 15, 'start') + lbl(o.ylabel, O.x - 8, O.y - top - 10, 15, 'end');
      for (let k = 1; k <= o.units; k++) { s += line({x: O.x + k * u, y: O.y - 3}, {x: O.x + k * u, y: O.y + 3}, hair) + line({x: O.x - 3, y: O.y - k * u}, {x: O.x + 3, y: O.y - k * u}, hair); }
      if (o.cone) { s += line(O, {x: O.x + top, y: O.y - top}, thin, dash('dashed')) + line(O, {x: O.x - Math.min(left, top), y: O.y - Math.min(left, top)}, thin, dash('dashed')) + lbl('$x = ct$', O.x + top * 0.98, O.y - top * 0.98 - 8, 12, 'end', '', {halo: true}); }
      if (o.primed) { const b = o.beta, tA = {x: O.x + b * top, y: O.y - top}, xA = {x: O.x + top, y: O.y - b * top};
        s += arrow(O, tA, {width: thin * 1.1}) + arrow(O, xA, {width: thin * 1.1}) + lbl(o.ylabel + "'", tA.x + 8, tA.y + 4, 15, 'start', '', {halo: true}) + lbl(o.xlabel + "'", xA.x + 4, xA.y - 10, 15, 'start', '', {halo: true}); }
      if (o.hyperbola) { let d = '', d2 = ''; for (let i = -40; i <= 40; i++) { const r = i / 40 * 1.6, ct = Math.cosh(r), x = Math.sinh(r); const p = {x: O.x + x * u, y: O.y - ct * u}; if (p.y > O.y - top && p.x > O.x - left) d += (d ? 'L' : 'M') + f(p.x) + ',' + f(p.y); const q = {x: O.x + ct * u, y: O.y - x * u}; if (q.x < O.x + top && q.y > O.y - top && q.y < O.y) d2 += (d2 ? 'L' : 'M') + f(q.x) + ',' + f(q.y); }
        s += `<path d="${d}${d2}" fill="none" stroke="${ink}" stroke-width="${f(hair)}"${dash('dotted')}/>`; }
      s += hitBox(O.x - left, O.y - top, left + top, top);
    } else if (T === 'worldline') {
      const D = byId.get(o.diagram); if (D) {
        const O = screen(D), u = D.size / D.units * S, max = D.units;
        const p = (x, ct) => ({x: O.x + x * u, y: O.y - ct * u}), ctEnd = Math.min(max, o.beta > 0 ? (D.units - o.x0) / o.beta : o.beta < 0 ? (-0.55 * D.units - o.x0) / o.beta : max);
        const a = p(o.x0, 0), b = p(o.x0 + o.beta * ctEnd, ctEnd);
        s += line(a, b, lw) + hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`);
        if (o.ticks) for (const t of clockTicks(o, ctEnd)) { const q = p(t.x, t.ct); s += `<circle cx="${f(q.x)}" cy="${f(q.y)}" r="${f(2.8 * Math.sqrt(ss))}" fill="${ink}"/>`; if (t.k <= 3) s += lbl(`\\tau = ${+(t.k * o.tau).toPrecision(3)}`, q.x + 7, q.y + 5, 11, 'start', '', {halo: true}); }
        if (o.label) s += lbl(o.label, b.x + 6, b.y - 4, 14, 'start', '', {halo: true});
      }
    } else if (T === 'frames') {
      const O = screen(o), L = o.size * S, O2 = {x: O.x + o.gap * S, y: O.y - 0.12 * S};
      for (const [c, pr, nm] of [[O, '', 'S'], [O2, "'", "S'"]]) s += arrow(c, {x: c.x + L, y: c.y}, {width: thin}) + arrow(c, {x: c.x, y: c.y - L}, {width: thin}) + lbl('x' + pr, c.x + L + 6, c.y + 2, 15, 'start') + lbl('y' + pr, c.x - 6, c.y - L - 6, 15, 'end') + lbl(`\\mathrm{${nm}}`, c.x - 10, c.y + 12, 15) + lbl('O' + pr, c.x + 2, c.y + 13, 12, 'start');
      s += arrow({x: O2.x + L * 0.2, y: O2.y - L * 0.55}, {x: O2.x + L * 0.85, y: O2.y - L * 0.55}, {width: lw}) + (o.label ? lbl(o.label, O2.x + L * 0.52, O2.y - L * 0.55 - 12, 15) : '');
      s += hitBox(O.x - 10, O2.y - L - 10, O2.x + L - O.x + 20, L + 30);

    /* ── marks ── */
    } else if (T === 'label') {
      const c = screen(o);
      if (o.box && o.text) { const b = texLayout(o.text, o.size * CUR.ls), pw = 6; s += `<rect x="${f(c.x - b.w / 2 - pw)}" y="${f(c.y - (b.a + b.d) / 2 - pw * 0.7)}" width="${f(b.w + 2 * pw)}" height="${f(b.a + b.d + pw * 1.4)}" fill="#fff" stroke="${ink}" stroke-width="${f(thin)}"/>`; }
      s += lbl(o.text || (edit ? '…' : ''), c.x, c.y, o.size) + (edit ? `<rect x="${f(c.x - 14)}" y="${f(c.y - 12)}" width="28" height="24" fill="transparent"/>` : '');
    } else if (T === 'dim') {
      const a = screen({x: o.x1, y: o.y1}), b = screen({x: o.x2, y: o.y2}), L = Math.hypot(b.x - a.x, b.y - a.y);
      if (L > 1) {
        const nx = -(b.y - a.y) / L, ny = (b.x - a.x) / L, off = -o.offset * S, a2 = {x: a.x + nx * off, y: a.y + ny * off}, b2 = {x: b.x + nx * off, y: b.y + ny * off};
        const ext = (p, q) => Math.abs(off) > 1 ? line(p, {x: q.x + nx * Math.sign(off) * 4, y: q.y + ny * Math.sign(off) * 4}, hair) : line({x: q.x - nx * 5, y: q.y - ny * 5}, {x: q.x + nx * 5, y: q.y + ny * 5}, hair);
        const m = {x: (a2.x + b2.x) / 2, y: (a2.y + b2.y) / 2};
        s = ext(a, a2) + ext(b, b2) + arrow(m, a2, {width: hair * 1.1, head: HL * 0.75, kind: st.dimHead}) + arrow(m, b2, {width: hair * 1.1, head: HL * 0.75, kind: st.dimHead});
        if (o.text) { const bx = texLayout(o.text, 15 * CUR.ls); s += `<rect x="${f(m.x - bx.w / 2 - 3)}" y="${f(m.y - (bx.a + bx.d) / 2 - 2)}" width="${f(bx.w + 6)}" height="${f(bx.a + bx.d + 4)}" fill="#fff"/>` + lbl(o.text, m.x, m.y, 15); }
        s += hit(`M${f(a2.x)},${f(a2.y)}L${f(b2.x)},${f(b2.y)}`);
      }
    } else if (T === 'arc') {
      const c = screen(o), r = o.r * S, t0 = o.from * Math.PI / 180, t1 = o.to * Math.PI / 180;
      const p0 = {x: c.x + r * Math.cos(t0), y: c.y - r * Math.sin(t0)}, p1 = {x: c.x + r * Math.cos(t1), y: c.y - r * Math.sin(t1)};
      let sw = t1 - t0; while (sw < 0) sw += 2 * Math.PI; while (sw >= 2 * Math.PI) sw -= 2 * Math.PI;
      const mid = (t0 + sw / 2), tm = {x: c.x + (r + 13) * Math.cos(mid), y: c.y - (r + 13) * Math.sin(mid)};
      const d = `M${f(p0.x)},${f(p0.y)}A${f(r)},${f(r)} 0 ${sw > Math.PI ? 1 : 0} 0 ${f(p1.x)},${f(p1.y)}`;
      s = `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(hair * 1.2)}"/>${o.arrow ? head(p1, -Math.sin(t1), -Math.cos(t1), {len: HL * 0.8})[0] : ''}${o.text ? lbl(o.text, tm.x, tm.y, 15) : ''}${hit(d)}`;
    } else if (T === 'axes') {
      const c = screen(o), ex = {x: c.x + o.lx * S, y: c.y}, ey = {x: c.x, y: c.y - o.ly * S};
      s = (o.lx > 0 ? arrow(c, ex, {width: thin, head: HL * 0.9}) + lbl(o.xlabel, ex.x + 4, ex.y + 13, 15, 'start') : '') + (o.ly > 0 ? arrow(c, ey, {width: thin, head: HL * 0.9}) + lbl(o.ylabel, ey.x - 12, ey.y + 4, 15) : '')
        + hit(`M${f(ex.x)},${f(ex.y)}L${f(c.x)},${f(c.y)}L${f(ey.x)},${f(ey.y)}`);
    } else if (T === 'line') {
      const a = screen({x: o.x1, y: o.y1}), b = screen({x: o.x2, y: o.y2}), L = Math.hypot(b.x - a.x, b.y - a.y) || 1, u = {x: (b.x - a.x) / L, y: (b.y - a.y) / L};
      if (o.pattern !== 'none') s += line(a, b, hair * 1.05, dash(o.pattern));
      if (o.heads === 'end' || o.heads === 'both') s += head(b, u.x, u.y, {len: HL * 0.85})[0];
      if (o.heads === 'start' || o.heads === 'both') s += head(a, -u.x, -u.y, {len: HL * 0.85})[0];
      if (o.heads === 'mid') s += midHead([a, b], 0.5, {len: HL * 0.85});
      s += hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`);
    } else if (T === 'vector') {
      const a = screen({x: o.x1, y: o.y1}), b = screen({x: o.x2, y: o.y2}), L = Math.hypot(b.x - a.x, b.y - a.y) || 1, n = {x: -(b.y - a.y) / L, y: (b.x - a.x) / L};
      s += arrow(a, b, {width: o.width * ss, kind: o.head === 'auto' ? st.head : o.head, head: HL * Math.max(0.9, Math.sqrt(o.width / 1.6))});
      if (o.label) { const side = n.y > 0 ? -1 : 1; s += lbl(o.label, (a.x + b.x) / 2 + side * n.x * 15, (a.y + b.y) / 2 + side * n.y * 15, 16, 'middle', '', {halo: true}); }
      s += hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`);
    } else if (T === 'region') {
      const p0 = screen({x: o.x, y: o.y + o.h}), w = o.w * S, h = o.h * S;
      const shape = o.shape === 'ellipse' ? `ellipse cx="${f(p0.x + w / 2)}" cy="${f(p0.y + h / 2)}" rx="${f(w / 2)}" ry="${f(h / 2)}"` : `rect x="${f(p0.x)}" y="${f(p0.y)}" width="${f(w)}" height="${f(h)}"`;
      if (o.fill === 'gray' && gray) s += `<${shape} fill="${light}" stroke="none"/>`; else s += shade(shape, o.fill === 'gray' ? 'hatch' : o.fill);
      if (o.pattern !== 'none') s += `<${shape} fill="none" stroke="${ink}" stroke-width="${f(thin)}"${dash(o.pattern)}/>`;
      if (o.label) s += lbl(o.label, p0.x + w * 0.5, p0.y + h * 0.3, 16, 'middle', '', {halo: true});
      s += hitBox(p0.x, p0.y, w, h);
    } else if (T === 'point') {
      const c = screen(o), r = 2.8 * Math.sqrt(ss);
      s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r)}" fill="${o.filled ? ink : '#fff'}" stroke="${ink}" stroke-width="${f(thin)}"/>` + (o.label ? lbl(o.label, c.x + 6, c.y - 10, 15, 'start', '', {halo: true}) : '') + hitBox(c.x - 8, c.y - 8, 16, 16);
    }
    /* a velocity arrow of a body */
    if (isBody(o)) {
      const vNow = opts.velocities?.get?.(o.id), vx = vNow ? vNow.x : o.vx, vy = vNow ? vNow.y : o.vy;
      if (o.showV && Math.hypot(vx, vy) > 1e-6) {
        const p = screen(opts.poses?.get?.(o.id) || poseOf(o)), sp = Math.hypot(vx, vy), L = Math.max(0.35, Math.min(1.4, sp * 0.08)) * S, ux = vx / sp, uy = vy / sp;
        const tip = {x: p.x + ux * L, y: p.y - uy * L};
        s += arrow(p, tip, {width: 1.5 * ss, head: HL}) + (o.vLabel ? lbl(o.vLabel, tip.x + ux * 10 - uy * 10, tip.y - uy * 10 - ux * 10, 15) : '');
      }
    }
    if (s) out.push(group(o, s));
  }

  /* circuit readings, the junction dots of the circuit */
  if (els.length) out.push(circuitMarks());
  /* the free-body diagram: every force on each body, from its centre, the longest arrow 90 px */
  if (opts.forces) {
    let max = 0;
    for (const list of opts.forces.values()) for (const x of list) max = Math.max(max, vec.len(x.v));
    const color = opts.forceColor || st.accent;
    for (const [id, list] of opts.forces) for (const x of list) {
      const m = vec.len(x.v); if (m < 1e-9 || !max) continue;
      const L = Math.max(16, 90 * m / max), u = vec.unit(x.v), a = screen(x.at), tip = {x: a.x + u.x * L, y: a.y - u.y * L};
      out.push(`<g class="fbd" data-body="${esc(id)}" data-kind="${x.kind}">${arrow(a, tip, {color, width: 2 * ss, head: HL})}${lbl(FORCE_LABEL[x.kind] || '', tip.x + u.x * 12, tip.y - u.y * 12, 14, 'middle', ` fill="${color}"`)}</g>`);
    }
  }
  if (edit && sel) {
    const o = byId.get(sel);
    if (o) {
      const b = objectBox(scene, o, opts.poses); if (b) out.push(`<rect x="${f(X(b.x) - 5)}" y="${f(Y(b.y + b.h) - 5)}" width="${f(b.w * S + 10)}" height="${f(b.h * S + 10)}" fill="none" stroke="#3b6fd8" stroke-width="1.3" stroke-dasharray="5 3" pointer-events="none" class="selbox"/>`);
      if ('x1' in o && 'y2' in o) for (const k of [1, 2]) { const p = screen({x: o['x' + k], y: o['y' + k]}); out.push(`<circle data-handle="${k}" cx="${f(p.x)}" cy="${f(p.y)}" r="7" fill="#fff" fill-opacity="0.85" stroke="#3b6fd8" stroke-width="1.6" class="handle"/>`); }
    }
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" font-family="${esc(st.font).replace(/&#39;/g, "'")}">${opts.title ? `<title>${esc(opts.title)}</title>` : ''}${out.join('')}</svg>`;

  /* ── a circuit element: leads from the two terminals to a symbol in the middle ── */
  function drawElement(e) {
    const a = screen({x: e.x1, y: e.y1}), b = screen({x: e.x2, y: e.y2}), L = Math.hypot(b.x - a.x, b.y - a.y);
    if (e.kind === 'wire') { const pts = elementPath(e).map(screen); return poly(pts, thin * 1.15) + hit('M' + pts.map(p => `${f(p.x)},${f(p.y)}`).join('L')); }
    if (L < 2) return '';
    const u = {x: (b.x - a.x) / L, y: (b.y - a.y) / L}; let n = {x: -u.y, y: u.x};
    const m = {x: (a.x + b.x) / 2, y: (a.y + b.y) / 2}, k = Math.sqrt(ss) * Math.min(1.25, Math.max(0.8, CUR.ls));
    const P2 = (s1, t) => ({x: m.x + u.x * s1 + n.x * t, y: m.y + u.y * s1 + n.y * t}), pt = (s1, t) => { const q = P2(s1, t); return `${f(q.x)},${f(q.y)}`; };
    const W2 = thin * 1.15;
    let half = 0, body = '', halfW = 12 * k;
    const leads = h => line(a, P2(-h, 0), W2) + line(P2(h, 0), b, W2);
    const K = e.kind;
    if (K === 'resistor') {
      half = Math.min(L * 0.32, 22 * k);
      const look = e.look === 'auto' ? st.resistor : e.look;
      if (look === 'box') { body = `<polygon points="${pt(-half, -6.5 * k)} ${pt(half, -6.5 * k)} ${pt(half, 6.5 * k)} ${pt(-half, 6.5 * k)}" fill="#fff" stroke="${ink}" stroke-width="${f(W2 * 1.1)}"/>`; halfW = 8 * k; }
      else { let d = `M${pt(-half, 0)}`; for (let i = 0; i < 6; i++) d += `L${pt(-half + half * 2 * (2 * i + 1) / 12, (i % 2 ? -1 : 1) * 6.5 * k)}`; d += `L${pt(half, 0)}`; body = `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(W2 * 1.1)}" stroke-linejoin="round"/>`; halfW = 8 * k; }
    } else if (K === 'battery' || K === 'cell') {
      const plates = K === 'cell' ? [[-3.5, 'neg'], [3.5, 'pos']] : [[-10.5, 'neg'], [-3.5, 'pos'], [3.5, 'neg'], [10.5, 'pos']];
      half = (K === 'cell' ? 3.5 : 10.5) * k;
      for (const [s1, kind] of plates) body += kind === 'pos' ? line(P2(s1 * k, -12 * k), P2(s1 * k, 12 * k), W2) : line(P2(s1 * k, -6 * k), P2(s1 * k, 6 * k), Math.max(2.6, lw * 1.7));
      if (K === 'battery') body += line(P2(-3.5 * k, 0), P2(3.5 * k, 0), W2, dash('dashed', 0.5));
      if (st.polarity) body += plus(P2(half + 6 * k, -11 * k), 3.2 * k, hair) + minus(P2(-half - 6 * k, -11 * k), 3.2 * k, hair);
      halfW = 12 * k;
    } else if (K === 'dc' || K === 'ac') {
      half = 13 * k; body = `<circle cx="${f(m.x)}" cy="${f(m.y)}" r="${f(half)}" fill="#fff" stroke="${ink}" stroke-width="${f(W2 * 1.1)}"/>`;
      if (K === 'dc') { body += plus(P2(5.5 * k, 0), 3.4 * k, hair * 1.2); body += `<path d="M${pt(-5.5 * k, -3.4 * k)}L${pt(-5.5 * k, 3.4 * k)}" stroke="${ink}" stroke-width="${f(hair * 1.2)}"/>`; }
      else { let d = ''; for (let i = 0; i <= 20; i++) { const sx = (-8 + 16 * i / 20) * k, ty = -4.5 * k * Math.sin(Math.PI * (-8 + 16 * i / 20) / 8); const q = {x: m.x + sx, y: m.y + ty}; d += (i ? 'L' : 'M') + f(q.x) + ',' + f(q.y); } body += `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(hair * 1.2)}"/>`; }
      halfW = half;
    } else if (K === 'capacitor') {
      half = 4 * k; body = line(P2(-half, -12 * k), P2(-half, 12 * k), Math.max(2, lw * 1.25)) + line(P2(half, -12 * k), P2(half, 12 * k), Math.max(2, lw * 1.25)); halfW = 12 * k;
    } else if (K === 'inductor') {
      half = Math.min(L * 0.32, 22 * k); const r = half / 4; let d = `M${pt(-half, 0)}`;
      for (let i = 0; i < 4; i++) { const q = P2(-half + (i + 1) * 2 * r, 0); d += `A${f(r)},${f(r)} 0 0 ${n.y > 0 || (n.y === 0 && n.x < 0) ? 0 : 1} ${f(q.x)},${f(q.y)}`; }
      body = `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(W2 * 1.15)}"/>`; halfW = r + 4;
    } else if (K === 'switch') {
      half = Math.min(L * 0.3, 18 * k); const r = 2.6 * k, c1 = P2(-half, 0), c2 = P2(half, 0);
      const tipS = e.closed ? c2 : P2(half * 0.85, -half * 0.95);
      body = line(c1, tipS, W2 * 1.1) + `<circle cx="${f(c1.x)}" cy="${f(c1.y)}" r="${f(r)}" fill="#fff" stroke="${ink}" stroke-width="${f(W2)}"/><circle cx="${f(c2.x)}" cy="${f(c2.y)}" r="${f(r)}" fill="#fff" stroke="${ink}" stroke-width="${f(W2)}"/>`;
      halfW = e.closed ? 6 : half;
    } else if (K === 'diode' || K === 'led') {
      half = 8 * k; body = `<polygon points="${pt(-half, -8 * k)} ${pt(-half, 8 * k)} ${pt(half, 0)}" fill="${ink}" stroke="${ink}" stroke-width="${f(W2)}" stroke-linejoin="round"/>` + line(P2(half, -8 * k), P2(half, 8 * k), W2 * 1.3) + line(P2(-half, 0), P2(half, 0), W2);
      if (K === 'led') for (const o2 of [-3, 3]) { const s0 = P2(o2 * k, -11 * k), e0 = P2(o2 * k + 7 * k, -19 * k); body += arrow(s0, {x: e0.x, y: e0.y}, {width: hair, head: 5 * k, kind: 'filled'}); }
      halfW = 10 * k;
    } else if (K === 'bulb') {
      half = 11 * k; body = `<circle cx="${f(m.x)}" cy="${f(m.y)}" r="${f(half)}" fill="#fff" stroke="${ink}" stroke-width="${f(W2 * 1.1)}"/><path d="M${f(m.x - half * 0.7)},${f(m.y - half * 0.7)}L${f(m.x + half * 0.7)},${f(m.y + half * 0.7)}M${f(m.x + half * 0.7)},${f(m.y - half * 0.7)}L${f(m.x - half * 0.7)},${f(m.y + half * 0.7)}" stroke="${ink}" stroke-width="${f(W2)}"/>`; halfW = half;
    } else if (K === 'ammeter' || K === 'voltmeter' || K === 'galvanometer') {
      half = 12 * k; body = `<circle cx="${f(m.x)}" cy="${f(m.y)}" r="${f(half)}" fill="#fff" stroke="${ink}" stroke-width="${f(W2 * 1.1)}"/>` + texText(`\\mathrm{${K === 'ammeter' ? 'A' : K === 'voltmeter' ? 'V' : 'G'}}`, m.x, m.y, 14 * k, 'middle', '', {raw: true}); halfW = half;
    }
    /* labels away from the middle of the circuit; readings on the other side */
    if ((n.x * (X(ccen.x) - m.x) + n.y * (Y(ccen.y) - m.y)) > 0) n = {x: -n.x, y: -n.y};
    let t = '';
    const place = (text, side, size = 15) => { const d = halfW + 8 + 6 * CUR.ls, q = {x: m.x + n.x * d * side, y: m.y + n.y * d * side}; const anchor = Math.abs(n.x) > 0.6 ? ((n.x * side) > 0 ? 'start' : 'end') : 'middle'; return lbl(text, q.x, q.y + (Math.abs(n.x) > 0.6 ? 0 : n.y * side * 2), size, anchor, '', {halo: true}); };
    if (e.label) t += place(e.label, 1);
    const r = opts.circuit?.el?.get?.(e.id);
    if (r && opts.circuit.ok) {
      const I = r.I, drop = r.drop;
      const read = K === 'voltmeter' ? `${fmtSI(-drop, 'V')}` : K === 'capacitor' ? `${fmtSI(Math.abs(drop), 'V')}` : Math.abs(I) > 1e-9 ? `${fmtSI(Math.abs(I), 'A')}` : K === 'ammeter' || K === 'galvanometer' ? '0 A' : '';
      if (read) t += place(`\\mathrm{${read.replace(/ /g, '\\,')}}`, -1, 12);
      if (Math.abs(I) > 1e-9 && K !== 'voltmeter') { const sg = I > 0 ? 1 : -1, q = P2(-sg * (half + Math.min(14, (L / 2 - half) * 0.55)), 0); if (L / 2 - half > 10) t += head({x: q.x + sg * u.x * 4, y: q.y + sg * u.y * 4}, sg * u.x, sg * u.y, {len: 7, color: st.accent === '#000' ? ink : st.accent})[0]; }
    }
    return leads(half) + body + t + hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`);
  }
  function circuitMarks() {
    const net = circuitNodes(scene), pts = new Map(), key = p => `${Math.round(p.x * 1000)},${Math.round(p.y * 1000)}`;
    for (const t of net.terms) { const k2 = key(t.p); pts.set(k2, {p: t.p, n: (pts.get(k2)?.n || 0) + 1}); }
    const wires = net.els.filter(e => e.kind === 'wire');
    let d = '';
    for (const {p, n} of pts.values()) {
      let deg = n;
      for (const w of wires) { const P0 = elementPath(w); for (let i = 0; i + 1 < P0.length; i++) { const A = P0[i], B = P0[i + 1], ab = vec.sub(B, A), t = vec.dot(vec.sub(p, A), ab) / (vec.dot(ab, ab) || 1); if (t > 0.001 && t < 0.999 && vec.len(vec.sub(p, vec.add(A, vec.mul(ab, t)))) < 0.01) deg += 2; } }
      if (deg >= 3) { const c = screen(p); d += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(3.1 * Math.sqrt(ss))}" fill="${ink}"/>`; }
    }
    return d;
  }
}

/** the world box around one object (for the selection outline and for picking) */
export function objectBox(scene, o, poses) {
  const byId = new Map(scene.objects.map(x => [x.id, x]));
  const box = pts => { const xs = pts.map(p => p.x), ys = pts.map(p => p.y), x = Math.min(...xs), y = Math.min(...ys); return {x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y}; };
  if (isBody(o)) { const p = poses?.get?.(o.id) || bodyPose(scene, o), r = o.type === 'ball' ? o.r : Math.hypot(o.w, o.h) / 2; return {x: p.x - r, y: p.y - r, w: 2 * r, h: 2 * r}; }
  switch (o.type) {
    case 'string': case 'rod': case 'spring': { const A = byId.get(o.a), B = byId.get(o.b); if (!A || !B) return null; const pa = isBody(A) ? (poses?.get?.(A.id) || bodyPose(scene, A)) : A, pb = isBody(B) ? (poses?.get?.(B.id) || bodyPose(scene, B)) : B; return box([pa, pb, ...((o.over || []).map(id => byId.get(id)).filter(Boolean))]); }
    case 'force': { const b = byId.get(o.on); if (!b) return null; const p = poses?.get?.(b.id) || bodyPose(scene, b), th = o.angle * Math.PI / 180; return box([p, {x: p.x + Math.cos(th) * o.len, y: p.y + Math.sin(th) * o.len}]); }
    case 'curve': case 'cycle': { const g = byId.get(o.graph); return g ? objectExtent(g) : null; }
    case 'worldline': { const g = byId.get(o.diagram); return g ? objectExtent(g) : null; }
    case 'fieldlines': return null;
  }
  return objectExtent(o);
}
export {surfaceFrame};
