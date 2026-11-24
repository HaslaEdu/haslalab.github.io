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
import {isBody, isRound, bodyPose, vectorPoints, surfaceFrame, inclineCorners, attachPoint, anchorPoint, stringPath, vec, objectExtent, compileExpr, boundExpr, bezierPoints, rotCentre, INERTIA, GEO_TYPES, computeGeometry, geoExtent, geoLinePoint, polyArea, CONE_TILT, curveVar, isPhysShape, nnLayers, nnWeights} from './draw-scene.mjs?v=7959e10d8eeb';
import {funcFeatures, derivative, integrate, jointEnds, fieldLines, equipotentials, chargePath, circuitNodes, elementPath, processPoints, gasCycle, traceRay, principalRays, opticImage, prismCorners,
  slitIntensity, slitRange, fringeSpacing, wellModel, qpotModel, levelModel, clockTicks, lorentzGamma, bridgeJockey, motionalEMF} from './draw-physics.mjs?v=f6b4ee63f834';
/* the types drawn turned by a transform about their centre (a block and a plank turn their own corners) */
const ROT_WRAP = new Set(['transformer', 'solenoid', 'magnet', 'cylinder', 'lens', 'mirror', 'screen', 'eye', 'source', 'label', 'region', 'rect', 'ellipse']);
/* the drawing tools' stroke colours (draw-scene.mjs COLORS) and the light tints their fill 'tint' uses */
export const COLOR_HEX = {black: '#000', gray: '#6b7280', lightgray: '#b4bac4', blue: '#1d4ed8', red: '#c0262d', green: '#15803d', orange: '#c2410c'};
const FILL_HEX = {white: '#fff', lightgray: '#e6e8ec', gray: '#c3c8d0', dark: '#4b5058'};

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const f = n => (Math.round(n * 100) / 100).toString();
const SERIF = `'Times New Roman','STIX Two Text','Nimbus Roman','Liberation Serif','Noto Serif KR','Nanum Myeongjo',serif`;

/* ── figure styles ("그림체") ──
   STYLE_TABLE holds what was MEASURED from public exam papers (numbers only; no figure, image or text of a paper is
   kept here or anywhere in the repository). Each source's figures were found on the pages of the PDFs and measured
   with PyMuPDF: vector figures from page.get_drawings() (stroke widths weighted by path length, filled arrowhead
   polygons, dash arrays, fill grays, filled marker circles, short parallel segments for hatching) and
   get_text('dict') (label fonts and sizes inside the figure, the body text size and the text column width); raster
   figures (most KICE and JEE figures are images) from their pixels at the image's own resolution (stroke width = 2 ×
   the distance transform on the ink's ridge − 1 px, gray = pixels between 50 and 235 that survive a 0.35 pt erosion,
   label glyph heights from connected components). Values are medians over the sample; pt = 1/72 in.
   Where a value could not be measured it is marked est (estimated from looking at a few crops) or assumed (no
   source); textbook and print are design choices with no measured source.

   source        sample                                                         fig w  label  line thin/main/thick   head len, w/len, shape      dash on/off   gray   dot
   suneung       KICE 수능 물리학 I·II, 2025–2027학년도 (6 papers): 136 raster   148    9 est  0.33 / 0.36 / 0.53       4.5 est, 0.5 est, filled    2.2/1.4 est   0.80   2.2 est
                 figures at 600–700 dpi; body 11.2 pt (신명 중명조); labels in an equation serif (italic variables, upright
                 object names A B p q), Hangul in a gothic face, (가)(나) captions in myeongjo; floors as a bare line
                 (수평면), walls and ceilings as gray strips; 62 % of figures use gray (median level 0.80, IQR 0.70–0.85)
   olympiad      IPhO 2003, 2005, 2006, APhO 2005, 2018, EuPhO 2019 papers in    194    10     0.5 / 0.75 / 1.0        4.0, 0.95, filled triangle  2.25/3.0      0.52   3.0
                 pdfx/ (30 vector figures with strokes from 13 files, + 71 raster); labels = body size (ratio 1.00), Times
                 New Roman, italic variables; 125 arrowheads (tip 42–53°, length 4–14 × line, median ≈ 8 ×); dashes on
                 41 paths ([2.25 3] at 0.75 pt); 43 gray fills (IQR 0.33–0.75); hatching from 3 figures only: gap
                 8.5–14 pt (median 12.8), stroke 9.3 pt long, 0.75 pt wide
   (university   MIT OCW 8.01SC / 8.02T problem sets, measured: 239 pt figures, 12 pt labels, lines 0.52/0.8/1.04, stealth
                 heads. It looked too close to textbook to be worth a style of its own, so it was merged into textbook:
                 a figure written with 'university' reads as 'textbook' (draw-scene.mjs LEGACY_STYLES).)
   jee           JEE Advanced 2022, 2024, 2025 Paper 1, physics part (8 vector   160    8.5    0.38 / 0.72 / 1.1       4.5 est, 0.65 est, filled   3/2 est       0.47   4.4
                 figures in 2022, 40 raster at ~200 dpi); labels 0.81 × body (8.5 of 10.4 pt), Times New Roman, point
                 names upright; gray rarely (one paper, level 0.47)
   textbook      designed (no measured source; the earlier default look kept)                 220    10     0.77 / 1.13 / 1.4       6.0, 0.76, filled           4/2.7         0.82   3.7
   classic       designed: an old letterpress textbook — a heavier schoolbook serif (Century  220    10.5   0.9 / 1.4 / 1.9         7.0, 0.62, open             5/3           none   3.6
                 Schoolbook), hatching instead of gray, open arrowheads, square line ends
   modern        designed: a clean digital textbook — thin even strokes, round caps and joins, 220    10     0.6 / 0.85 / 1.1        6.5, 0.75, filled           3.5/2.5       0.88   3.4
                 a sans-serif face with italic variables, light fills, one accent colour
                 (blue, for vectors and forces) and grays
   print         designed: the earlier black-and-white look kept (heavier, no gray)           220    11     1.17 / 1.69 / 2.0       8.4, 0.76, filled           4.4/2.9       none   4
   basis: 'measured' rows hold numbers measured from the sources named; 'designed' rows are choices made here, and
   their sources say so. Within a measured row, est lists what was estimated by eye and measured what was measured.

   How the table drives a preset: the drawing is 800 px wide and a label's base size is 15 px, so one pt of the
   source is 15 / label pt px. Every line width, arrowhead, hatch, dash and dot keeps the measured ratio to the label;
   printed (printScale) at the source's typical width, a figure comes out with the measured absolute sizes. */
export const STYLE_TABLE = {
  suneung: {basis: 'measured', source: 'KICE 수능 물리학 I·II 2025–2027 (6 papers, 136 raster figures, 600–700 dpi)', n: 136, widthPt: 148, labelPt: 9, bodyPt: 11.2, thin: 0.33, main: 0.36, thick: 0.53, hair: 0.25,
    headLen: 4.5, headW: 0.5, head: 'filled', dash: [2.2, 1.4], gray: 0.80, light: 0.88, dark: 0.70, dot: 2.2, hatchGap: 4, hatchLen: 3.5, hatchAngle: 45,
    measured: ['widthPt', 'thin', 'main', 'thick', 'gray', 'light', 'dark', 'bodyPt'], est: ['labelPt', 'headLen', 'headW', 'dash', 'dot', 'hatchGap', 'hatchLen']},
  olympiad: {basis: 'measured', source: 'IPhO 2003/2005/2006, APhO 2005/2018, EuPhO 2019 (30 vector + 71 raster figures, 13 + 16 files)', n: 101, widthPt: 194, labelPt: 10, bodyPt: 11.6, thin: 0.5, main: 0.75, thick: 1.0, hair: 0.25,
    headLen: 4.0, headW: 0.95, head: 'filled', dash: [2.25, 3.0], gray: 0.52, light: 0.76, dark: 0.33, dot: 3.0, hatchGap: 12.8, hatchLen: 9.3, hatchAngle: 45,
    measured: ['widthPt', 'labelPt', 'bodyPt', 'thin', 'main', 'thick', 'headLen', 'headW', 'dash', 'gray', 'dot', 'hatchGap', 'hatchLen'], est: []},
  jee: {basis: 'measured', source: 'JEE Advanced 2022/2024/2025 Paper 1 physics (8 vector + 40 raster figures, ~200 dpi)', n: 48, widthPt: 160, labelPt: 8.5, bodyPt: 10.4, thin: 0.38, main: 0.72, thick: 1.1, hair: 0.3,
    headLen: 4.5, headW: 0.65, head: 'filled', dash: [3, 2], gray: 0.47, light: 0.85, dark: 0.35, dot: 4.4, hatchGap: 4, hatchLen: 4, hatchAngle: 45,
    measured: ['widthPt', 'labelPt', 'bodyPt', 'thin', 'main', 'thick', 'gray', 'dot'], est: ['headLen', 'headW', 'dash', 'hatchGap', 'hatchLen']},
  textbook: {basis: 'designed', source: 'assumed', n: 0, widthPt: 220, labelPt: 10, bodyPt: 10, thin: 0.77, main: 1.13, thick: 1.4, hair: 0.57, headLen: 6, headW: 0.76, head: 'filled', dash: [4, 2.7], gray: 0.82, light: 0.95, dark: 0.6, dot: 3.7,
    hatchGap: 6, hatchLen: 4.7, hatchAngle: 45, measured: [], est: [], designed: ['all: the earlier default look; it also stands for the merged university style']},
  classic: {basis: 'designed', source: 'assumed', n: 0, widthPt: 220, labelPt: 10.5, bodyPt: 10.5, thin: 0.9, main: 1.4, thick: 1.9, hair: 0.6, headLen: 7, headW: 0.62, head: 'open', dash: [5, 3], gray: null, light: 1, dark: 0, dot: 3.6,
    hatchGap: 4.5, hatchLen: 5, hatchAngle: 45, measured: [], est: [], designed: ['face: a schoolbook serif (Century Schoolbook / TeX Gyre Schola), heavier than Times', 'no gray: hatching for every fill', 'open arrowheads', 'heavier main lines, square ends (letterpress)']},
  modern: {basis: 'designed', source: 'assumed', n: 0, widthPt: 220, labelPt: 10, bodyPt: 10, thin: 0.6, main: 0.85, thick: 1.1, hair: 0.45, headLen: 6.5, headW: 0.75, head: 'filled', dash: [3.5, 2.5], gray: 0.88, light: 0.95, dark: 0.55, dot: 3.4,
    hatchGap: 6, hatchLen: 4.5, hatchAngle: 45, measured: [], est: [], designed: ['face: a sans serif (Inter / Helvetica) with italic variables', 'thin, even strokes with round caps and joins', 'light fills', 'one accent colour (blue) for vectors and forces, the rest in grays', 'filled arrowheads']},
  print: {basis: 'designed', source: 'assumed', n: 0, widthPt: 220, labelPt: 11, bodyPt: 11, thin: 1.17, main: 1.69, thick: 2.0, hair: 0.88, headLen: 8.4, headW: 0.76, head: 'filled', dash: [4.4, 2.9], gray: null, light: 1, dark: 0, dot: 4,
    hatchGap: 6.6, hatchLen: 5.9, hatchAngle: 45, measured: [], est: [], designed: ['all: the earlier black-and-white look, heavier, no gray']}
};
const KR_GOTHIC = `'Noto Sans KR','Noto Sans CJK KR','Malgun Gothic','Apple SD Gothic Neo','NanumGothic','Nanum Gothic',sans-serif`;
const KR_MYEONGJO = `'Noto Serif KR','Noto Serif CJK KR','Nanum Myeongjo','Batang','AppleMyungjo',serif`;
const CM_SERIF = `'Latin Modern Roman','CMU Serif','Computer Modern','STIX Two Text','Times New Roman','Nimbus Roman','Liberation Serif',serif`;
const SCHOOLBOOK = `'TeX Gyre Schola','Century Schoolbook','New Century Schoolbook','Century Schoolbook L','C059','Georgia','Noto Serif KR',serif`;
const MODERN_SANS = `'Inter','Helvetica Neue','Helvetica','Arial','Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif`;
const hex = g => { const v = Math.round(Math.max(0, Math.min(1, g)) * 255).toString(16).padStart(2, '0'); return '#' + v + v + v; };
/** a preset from its row of STYLE_TABLE: px at the 800 px drawing, where a base label is 15 px */
function preset(key, extra) {
  const t = STYLE_TABLE[key], u = 15 / t.labelPt;
  return {key, lw: t.main * u, thin: t.thin * u, hair: t.hair * u, thick: t.thick * u, headLen: t.headLen * u, headW: t.headW / 2, head: t.head,
    hatchGap: t.hatchGap * u, hatchLen: t.hatchLen * u, hatchW: t.thin * u, hatchAngle: t.hatchAngle, dash: t.dash.map(v => v * u), dot: t.dot * u / 2,
    gray: t.gray == null ? null : hex(t.gray), light: hex(t.light ?? 0.95), dark: hex(t.dark ?? 0.5), labelScale: 1, widthPt: t.widthPt, labelPt: t.labelPt,
    font: SERIF, hangul: null, caption: null, sans: false, vec: 'arrow', fill: '#fff', accent: '#000', dimHead: 'filled', resistor: 'zigzag', polarity: false, uprightNames: false, floor: 'hatch', wall: 'hatch',
    ink: '#000', vecInk: null, round: false, wscale: 1, ...extra};
}
export const STYLES = {
  textbook: preset('textbook', {name: {ko: '교과서 (기본)', en: 'Textbook (default)'}, accent: '#b42318'}),
  classic: preset('classic', {name: {ko: '클래식 (오래된 인쇄 교재)', en: 'Classic (old printed textbook)'}, font: SCHOOLBOOK, caption: KR_MYEONGJO, wscale: 1.1, accent: '#000', dimHead: 'open'}),
  modern: preset('modern', {name: {ko: '모던 (디지털 교재)', en: 'Modern (digital textbook)'}, font: MODERN_SANS, hangul: KR_GOTHIC, sans: true, wscale: 1.08, ink: '#1f2937', accent: '#2563eb', vecInk: '#2563eb', round: true, fill: '#f1f5f9'}),
  olympiad: preset('olympiad', {name: {ko: '올림피아드 (IPhO·APhO 실측)', en: 'Olympiad (measured, IPhO/APhO)'}, vec: 'bold', dimHead: 'filled', resistor: 'box', polarity: true}),
  jee: preset('jee', {name: {ko: 'JEE (실측)', en: 'JEE (measured)'}, uprightNames: true}),
  suneung: preset('suneung', {name: {ko: '수능 (평가원 실측)', en: 'CSAT 수능 (measured, KICE)'}, font: CM_SERIF, hangul: KR_GOTHIC, caption: KR_MYEONGJO, uprightNames: true, floor: 'line', wall: 'gray', dimHead: 'filled'}),
  print: preset('print', {name: {ko: '흑백 인쇄용', en: 'Black and white print'}, labelScale: 1.1})
};
/** the scale (labels and lines together) at which a figure printed `printWmm` wide (else the style's typical
 *  width) shows the style's measured sizes: k = label pt · 800 / (width pt · 15) */
/** the label scale for the editor's canvas: the W-px drawing (svgH px high) is shown at most availW wide and maxH
 *  high, so labels grow by what it is shrunk, keeping about 12 px on screen (never smaller than the drawing's own) */
export function labelScaleFor(availW, maxH, svgH, W = 800) {
  const shown = Math.min(Math.max(1, availW), maxH > 0 ? maxH * W / Math.max(1, svgH) : Infinity);
  return Math.max(1, Math.min(2.6, 0.8 * W / Math.max(120, shown)));
}
export function printScale(style, printWmm, W = 800) {
  const st = STYLES[style] || STYLES.textbook, wpt = printWmm ? printWmm * 72 / 25.4 : st.widthPt;
  const k = st.labelPt * W / (wpt * 15);
  return {labelScale: k, strokeScale: k, widthPt: wpt};
}
let CUR = {...STYLES.textbook, ls: 1, ss: 1};
const LETTER_FONTS = {
  serif: "'Times New Roman','Noto Serif CJK KR','Batang',serif",
  sans: "'Arial','Noto Sans CJK KR','Malgun Gothic',sans-serif",
  mono: "'Courier New','Noto Sans Mono CJK KR','Malgun Gothic',monospace",
};
function letterFont() {
  return Object.hasOwn(LETTER_FONTS, CUR.letterFamily) ? LETTER_FONTS[CUR.letterFamily] : null;
}

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
  ldots: '…', cdots: '⋯', vdots: '⋮', ddots: '⋱', iddots: '⋰', Box: '□', prime: '′', dagger: '†', ddagger: '‡', '%': '%', '$': '$', '{': '{', '}': '}', '_': '_', '#': '#', '&': '&', '|': '‖', lbrace: '{', rbrace: '}',
  sin: 'sin', cos: 'cos', tan: 'tan', cot: 'cot', sec: 'sec', csc: 'csc', ln: 'ln', log: 'log', exp: 'exp', lim: 'lim', max: 'max', min: 'min', det: 'det', sinh: 'sinh', cosh: 'cosh', tanh: 'tanh', arcsin: 'arcsin', arccos: 'arccos', arctan: 'arctan',
  deg: '°', ohm: 'Ω', micro: 'µ', imath: 'ı', jmath: 'ȷ'};
const OPNAMES = new Set(['sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'ln', 'log', 'exp', 'lim', 'max', 'min', 'det', 'sinh', 'cosh', 'tanh', 'arcsin', 'arccos', 'arctan']);
const SPACES = {',': 0.17, ':': 0.22, ';': 0.28, ' ': 0.25, quad: 1, qquad: 2, '!': -0.1, enspace: 0.5, thinspace: 0.17};
const ACCENTS = {vec: 'vec', hat: 'hat', widehat: 'hat', dot: 'dot', ddot: 'ddot', bar: 'bar', overline: 'bar', tilde: 'tilde', widetilde: 'tilde', overrightarrow: 'arrow', check: 'check', breve: 'breve', underline: 'under'};
const FONTS = {mathrm: 'rm', text: 'rm', textrm: 'rm', rm: 'rm', operatorname: 'rm', mathbf: 'bf', bf: 'bf', textbf: 'bf', boldsymbol: 'bfit', bm: 'bfit', mathit: 'it', textit: 'it', mathsf: 'rm', mathcal: 'cal', mathscr: 'cal'};
const CAL = {A: '𝒜', B: 'ℬ', C: '𝒞', D: '𝒟', E: 'ℰ', F: 'ℱ', G: '𝒢', H: 'ℋ', I: 'ℐ', J: '𝒥', K: '𝒦', L: 'ℒ', M: 'ℳ', N: '𝒩', O: '𝒪', P: '𝒫', Q: '𝒬', R: 'ℛ', S: '𝒮', T: '𝒯', U: '𝒰', V: '𝒱', W: '𝒲', X: '𝒳', Y: '𝒴', Z: '𝒵'};
const IGNORE = new Set(['left', 'right', 'big', 'Big', 'bigg', 'Bigg', 'displaystyle', 'textstyle', 'limits', 'nolimits', 'mathstrut']);

/* a font command over its argument: every text node in it (in scripts, fractions and roots too) takes the font; a
   symbol keeps its own unless the font is bold */
function fontSet(list, font) {
  return list.map(n => n.k === 't' ? {...n, font: font === 'cal' ? 'cal' : n.sym && font !== 'bf' && font !== 'bfit' ? n.font : font}
    : n.k === 'g' || n.k === 'acc' || n.k === 'sqrt' ? {...n, body: fontSet(n.body, font)}
    : n.k === 'scr' ? {...n, base: fontSet(n.base, font), sub: n.sub && fontSet(n.sub, font), sup: n.sup && fontSet(n.sup, font)}
    : n.k === 'frac' ? {...n, num: fontSet(n.num, font), den: fontSet(n.den, font)} : n);
}
/* the placeholder a structure of the symbol picker leaves to be filled (drawn as a tinted box) */
export const PLACEHOLDER = '⬚';
/** a chemical formula as TeX: a number after an element or a bracket is a subscript, a charge after ^ (or a + or −
 *  closing a species) a superscript, -> <- <-> <=> are arrows, (aq) (s) (l) (g) states; a number before a species
 *  is its coefficient. Upright throughout (the caller sets it in \mathrm). */
export function ceTex(src) {
  const s = String(src ?? ''); let out = '', i = 0, prev = '';
  const arrows = [['<=>', '\\rightleftharpoons '], ['<->', '\\leftrightarrow '], ['->', '\\rightarrow '], ['<-', '\\leftarrow '], ['⇌', '\\rightleftharpoons '], ['→', '\\rightarrow ']];
  while (i < s.length) {
    const a = arrows.find(([t]) => s.startsWith(t, i));
    if (a) { out = out.trimEnd() + a[1].trim() + ' '; i += a[0].length; while (s[i] === ' ') i++; prev = 'op'; continue; }
    const st = /^\((aq|s|l|g)\)/.exec(s.slice(i));
    if (st) { out += '(' + st[1] + ')'; i += st[0].length; prev = 'state'; continue; }
    const c = s[i];
    if (/[A-Z]/.test(c)) { const m = /^[A-Z][a-z]?/.exec(s.slice(i)); out += m[0]; i += m[0].length; prev = 'el'; continue; }
    if (/[0-9]/.test(c)) { const m = /^[0-9]+/.exec(s.slice(i)); out += prev === 'el' || prev === 'close' ? '_{' + m[0] + '}' : m[0]; i += m[0].length; prev = prev === 'el' || prev === 'close' ? 'sub' : 'coef'; continue; }
    if (c === '^') { const m = /^\^\{?([0-9]*[+\-−])\}?/.exec(s.slice(i)); if (m) { out += '^{' + m[1].replace(/-/g, '−') + '}'; i += m[0].length; prev = 'charge'; continue; } }
    if ((c === '+' || c === '-') && (prev === 'el' || prev === 'sub' || prev === 'close') && (i + 1 === s.length || /[\s)\]]/.test(s[i + 1]))) { out += '^{' + (c === '-' ? '−' : '+') + '}'; i++; prev = 'charge'; continue; }
    if (c === ')' || c === ']') { out += c; i++; prev = 'close'; continue; }
    if (c === '\\' || c === '{' || c === '}') { out += c; i++; prev = ''; continue; }
    out += c === '-' ? '−' : c; i++; prev = c === ' ' ? 'space' : c === '(' || c === '[' ? 'open' : prev === 'space' && c === '+' ? 'op' : '';
  }
  return out;
}

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
    if (FONTS[name]) return [{k: 'g', body: fontSet(arg(), FONTS[name])}];
    /* \ce{H2SO4}, \ce{SO4^2-}, \ce{2H2 + O2 -> 2H2O}: a chemical formula (draw-render.mjs ceTex) */
    if (name === 'ce') { while (str[k] === ' ') k++; const raw = str[k] === '{' ? group() : ''; return [{k: 'g', body: fontSet(parseList(ceTex(raw)), 'rm'), chem: true}]; }
    if (name === 'frac' || name === 'dfrac' || name === 'tfrac') { const a = arg(), b = arg(); return [{k: 'frac', num: a, den: b, t: name === 'tfrac'}]; }
    if (name === 'sqrt') { let index = null; if (str[k] === '[') { const j = str.indexOf(']', k); if (j > k) { index = parseList(str.slice(k + 1, j)); k = j + 1; } } return [{k: 'sqrt', body: arg(), index}]; }
    /* matrices and cases: \begin{pmatrix} a & b \\ c & d \end{pmatrix} (also bmatrix, vmatrix, matrix, cases), or the
       short \pmatrix{a & b \\ c & d}, \bmatrix{…}, \vmatrix{…}, \cases{…} */
    /* also array (with a column spec like {cc|c}: l c r and | for a rule) and amatrix (bracketed, a rule before its last
       column: an augmented matrix) */
    const MATS = ['pmatrix', 'bmatrix', 'vmatrix', 'Vmatrix', 'matrix', 'cases', 'array', 'amatrix'];
    if (name === 'begin' || MATS.includes(name)) {
      let env = name, raw = '', spec = '';
      if (name === 'begin') { while (str[k] === ' ') k++; env = str[k] === '{' ? group().trim() : ''; while (str[k] === ' ') k++; if (env === 'array' && str[k] === '{') spec = group(); const endTag = '\\end{' + env + '}', j = str.indexOf(endTag, k); raw = j >= 0 ? str.slice(k, j) : str.slice(k); k = j >= 0 ? j + endTag.length : str.length; }
      else { while (str[k] === ' ') k++; if (env === 'array' && str[k] === '[') { const j = str.indexOf(']', k); spec = str.slice(k + 1, j); k = j + 1; } raw = str[k] === '{' ? group() : ''; }
      if (!MATS.includes(env)) return [];
      const rows = raw.split(/\\\\/).map(r => r.trim()).filter((r, i, a) => r || i < a.length - 1).slice(0, 16).map(r => r.split('&').slice(0, 16).map(c => parseList(c.trim())));
      const ncol = Math.max(0, ...rows.map(r => r.length)), align = [], bars = new Set();
      for (const c of spec.replace(/\s/g, '')) { if (c === '|') bars.add(align.length); else if ('lcr'.includes(c)) align.push(c); }
      if (env === 'amatrix') bars.add(ncol - 1);
      return rows.length ? [{k: 'mat', env, rows, align, bars}] : [];
    }
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
/* advances (em) of the symbols outside the table, set at or above the widest of the faces a browser falls back to for
   them (Times New Roman, STIX Two, Cambria Math, DejaVu Serif): a glyph drawn wider than its advance would run into the
   next one (∇×B came out with ∇, × and B on top of each other with ∇ at 0.52) */
const SYMW = {'∇': 0.725, '∂': 0.54, 'ħ': 0.54, 'ℏ': 0.54, 'ℓ': 0.46, '∑': 0.78, '∏': 0.84, '∫': 0.5, '∬': 0.78, '∭': 1.04, '∮': 0.54, '×': 0.62, '±': 0.62, '∓': 0.62, '÷': 0.62, '−': 0.62,
  '≈': 0.62, '≠': 0.62, '≤': 0.62, '≥': 0.62, '∝': 0.66, '∼': 0.62, '≡': 0.62, '≃': 0.62, '≅': 0.62, '·': 0.28, '∘': 0.46, '•': 0.4, '∞': 0.82, '⊙': 0.8, '⊗': 0.8, '⊕': 0.8, '°': 0.4, '′': 0.3, '″': 0.5,
  '⟨': 0.4, '⟩': 0.4, '‖': 0.4, '†': 0.5, '‡': 0.5,
  /* Greek: the italic advance or the ink's right edge, whichever is wider (measured on the serif stack in Chromium), so a
     subscript sits right after the letter (ε₀, not ε 0) and the next glyph does not run into it */
  'α': 0.55, 'β': 0.5, 'γ': 0.44, 'δ': 0.48, 'ε': 0.42, 'ϵ': 0.44, 'ζ': 0.47, 'η': 0.5, 'θ': 0.49, 'ϑ': 0.52, 'ι': 0.28, 'κ': 0.5, 'λ': 0.48, 'μ': 0.53, 'ν': 0.45, 'ξ': 0.44, 'π': 0.53, 'ρ': 0.48, 'ϱ': 0.48, 'σ': 0.53, 'ς': 0.44, 'τ': 0.4, 'υ': 0.47, 'φ': 0.56, 'ϕ': 0.52, 'χ': 0.47, 'ψ': 0.64, 'ω': 0.7, 'ϖ': 0.66,
  'Ω': 0.74, 'Φ': 0.76, 'Ψ': 0.78, 'Θ': 0.72, 'Σ': 0.6, 'Γ': 0.6, 'Λ': 0.72, 'Δ': 0.64, 'Π': 0.76, 'Ξ': 0.64,
  '→': 1.0, '←': 1.0, '↔': 1.0, '⇒': 1.0, '⇐': 1.0, '⇔': 1.0, '⇌': 1.0, '⇋': 1.0, '↦': 1.0, '⟶': 1.4, '↑': 0.52, '↓': 0.52, '↕': 0.52, '…': 1.0, '⋯': 1.0, '⋮': 0.4, '⋱': 1.0, '⋰': 1.0, '∈': 0.66, '∉': 0.66, '⊥': 0.7, '∥': 0.4, '∠': 0.72, [PLACEHOLDER]: 0.62};
function charW(c, it) {
  if (ADV[c] !== undefined) return ADV[c] * (it && c === 'f' ? 0.9 : 1);
  if (SYMW[c] !== undefined) return SYMW[c];
  if (/[α-ω]/.test(c)) return 0.54;
  if (/[Α-Ω]/.test(c)) return 0.7;
  if ('ϑϕϵϱςϖϰ'.includes(c)) return 0.56;
  if (/[가-힣ㄱ-ㅎ]/.test(c)) return 0.92;
  if (/[\u{1D49C}-\u{1D4CF}ℬℰℱℋℐℒℳℛ]/u.test(c)) return 0.74;
  return 0.62;
}
const textWidth = (s, sz, it, bold) => {
  let w = 0;
  for (const c of s) w += CUR.letterFamily === 'mono' && c.codePointAt(0) < 128 ? 0.6 : charW(c, it);
  const scale = CUR.letterFamily === 'sans' ? 1.08 : letterFont() ? 1 : CUR.wscale || (CUR.sans ? 1.08 : 1);
  return w * sz * scale * (bold && CUR.letterFamily !== 'mono' ? 1.04 : 1);
};
/* ── maths spacing: TeX's atom classes and the spaces between them (in em; none in scripts but around operators) ── */
const BIN_CH = '+−-±∓×·∘•÷∗⋆∧∨⊕⊗∩∪', REL_CH = '=≈≠≤≥<>∝∼≃≅≡∈∉→←↔⇒⇐⇔⇌⇋↦⟶≪≫⊥∥', LOP_CH = '∑∏∫∬∭∮', OPEN_CH = '([{⟨', CLOSE_CH = ')]}⟩', PUNCT_CH = ',;';
const charClass = c => !c ? 'ord' : LOP_CH.includes(c) ? 'op' : BIN_CH.includes(c) ? 'bin' : REL_CH.includes(c) ? 'rel' : OPEN_CH.includes(c) ? 'open' : CLOSE_CH.includes(c) ? 'close' : PUNCT_CH.includes(c) ? 'punct' : 'ord';
/* the class a node has on its left and on its right */
function nodeClass(n) {
  if (n.k === 't') {
    if (n.sym && n.font === 'rm' && n.s.length > 1) return {l: 'op', r: 'op'};
    const t = n.s.trim(); if (!t) return null;
    if (n.sym) { const c = charClass(t[0]); return {l: c, r: c}; }
    /* a sign closing the run after a relation or an operator is unary: it binds to what follows ("= −ρ") */
    const last = charClass(t[t.length - 1]), before = t.length > 1 ? charClass(t.slice(0, -1).trimEnd().slice(-1)) : null;
    return {l: charClass(t[0]), r: last === 'bin' && ['rel', 'bin', 'open', 'punct'].includes(before) ? 'ord' : last};
  }
  if (n.k === 'scr') { const b = n.base.length === 1 ? nodeClass(n.base[0]) : null; return b && b.r === 'op' ? {l: 'op', r: 'op'} : {l: b?.l || 'ord', r: 'ord'}; }
  if (n.k === 'sp') return null;
  return {l: 'ord', r: 'ord'};
}
const MATH_SPACE = (L, R, script) => {
  if (!L) return 0;
  if ((L === 'op' && (R === 'ord' || R === 'op' || R === 'open')) || ((L === 'ord' || L === 'close') && R === 'op')) return 0.167;
  if (script) return 0;
  if (R === 'bin' && (L === 'ord' || L === 'close')) return 0.222;
  if (L === 'bin' && (R === 'ord' || R === 'op' || R === 'open')) return 0.222;
  if (R === 'rel' && (L === 'ord' || L === 'op' || L === 'close')) return 0.278;
  if (L === 'rel' && (R === 'ord' || R === 'op' || R === 'open')) return 0.278;
  if (L === 'punct' && R !== 'close' && R !== 'punct') return 0.167;
  return 0;
};
const UNARY_AFTER = new Set([null, 'bin', 'rel', 'open', 'op', 'punct']);
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
  let prev = null;
  for (let i = 0; i < nodes.length; i++) {
    const n = nodes[i];
    /* the space TeX puts between this atom and the one before (∇ × B, a = b, \sin x, ∑ x) */
    const cls = ctx.math ? nodeClass(n) : null, before = prev; let left = cls?.l;
    if (cls) { if (left === 'bin' && UNARY_AFTER.has(prev)) left = 'ord'; x += MATH_SPACE(prev, left, (ctx.level || 0) > 0) * sz; }
    /* an italic letter followed by an upright one leans into it: its italic correction */
    if (n.k === 't' && items.length && items[items.length - 1].it && !/^[\s]/.test(n.s) && n.font !== 'it' && !(n.font === 'auto' && /^[A-Za-z]/.test(n.s))) x += sz * 0.05;
    if (cls) prev = left === 'ord' && cls.r === 'bin' && cls.l === 'bin' ? 'ord' : cls.r;
    if (n.k === 't') put(textBox(n, sz, {...ctx, lead: x === 0 && !items.length, prev: before}));
    else if (n.k === 'g') put(layout(n.body, sz, ctx));
    else if (n.k === 'sp') x += n.w * sz;
    else if (n.k === 'scr') {
      const base = layout(n.base, sz, ctx), s2 = Math.max(7, sz * (ctx.level ? 0.8 : 0.7)), c2 = {...ctx, level: (ctx.level || 0) + 1};
      put(base);
      const it = base.items.length === 1 && base.items[0].it ? sz * 0.06 : 0;
      /* ∇'s advance is set for the widest fallback face; its scripts tuck in by what the usual faces leave empty */
      const last = base.items[base.items.length - 1]; if (last && /∇$/.test(last.t)) x -= sz * 0.05;
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
    } else if (n.k === 'mat') {
      /* a matrix: cells centred in their columns (cases: to the left), rows about the maths axis, its brackets drawn */
      const s2 = ctx.level ? sz * 0.85 : sz, cells = n.rows.map(r => r.map(c => layout(c, s2, ctx))), ncol = Math.max(...n.rows.map(r => r.length)), al = j => n.env === 'cases' ? 'l' : n.align?.[j] || 'c';
      const colW = Array.from({length: ncol}, (_, j) => Math.max(s2 * 0.4, ...cells.map(r => r[j] ? r[j].w : 0)));
      const rowA = cells.map(r => Math.max(s2 * 0.62, ...r.map(c => c.a))), rowD = cells.map(r => Math.max(s2 * 0.2, ...r.map(c => c.d)));
      const gx = s2 * (n.env === 'cases' ? 1 : 0.7), gy = s2 * 0.24, totH = rowA.reduce((t, v, i) => t + v + rowD[i], 0) + gy * (cells.length - 1), axis = sz * 0.27, top = -axis - totH / 2;
      const dw = n.env === 'matrix' || n.env === 'array' ? 0 : sz * 0.38, cw = colW.reduce((t, v) => t + v, 0) + gx * (ncol - 1), sw = Math.max(0.7, sz * 0.055);
      const box = {w: dw + cw + (n.env === 'cases' ? sz * 0.1 : dw) + sz * 0.1, a: -top + sz * 0.05, d: top + totH + sz * 0.05, items: [], paths: []};
      let yy = top;
      cells.forEach((r, i) => {
        const base = yy + rowA[i]; let xx = dw + sz * 0.05;
        r.forEach((c, j) => { const dx = al(j) === 'l' ? 0 : al(j) === 'r' ? colW[j] - c.w : (colW[j] - c.w) / 2; for (const it of c.items) box.items.push({...it, x: it.x + xx + dx, y: it.y + base}); for (const p of c.paths) box.paths.push({...p, ox: (p.ox || 0) + xx + dx, oy: (p.oy || 0) + base}); xx += colW[j] + gx; });
        yy = base + rowD[i] + gy;
      });
      const y0 = top - sz * 0.04, y1 = top + totH + sz * 0.04, ym = (y0 + y1) / 2, R = box.w - sz * 0.05;
      if (n.env === 'pmatrix') box.paths.push({d: `M${f(dw * 0.85)},${f(y0)}Q${f(dw * 0.05)},${f(ym)} ${f(dw * 0.85)},${f(y1)}M${f(R - dw * 0.85)},${f(y0)}Q${f(R - dw * 0.05)},${f(ym)} ${f(R - dw * 0.85)},${f(y1)}`, sw, join: true});
      /* the rules of an array or an augmented matrix, between columns */
      for (const j of n.bars || []) { if (j <= 0 || j >= ncol) continue; let xx = dw + sz * 0.05; for (let q = 0; q < j; q++) xx += colW[q] + gx; xx -= gx / 2; box.paths.push({d: `M${f(xx)},${f(y0)}V${f(y1)}`, sw: sw * 0.8}); }
      if (n.env === 'bmatrix' || n.env === 'amatrix') box.paths.push({d: `M${f(dw * 0.8)},${f(y0)}H${f(dw * 0.3)}V${f(y1)}H${f(dw * 0.8)}M${f(R - dw * 0.8)},${f(y0)}H${f(R - dw * 0.3)}V${f(y1)}H${f(R - dw * 0.8)}`, sw});
      else if (n.env === 'vmatrix') box.paths.push({d: `M${f(dw * 0.5)},${f(y0)}V${f(y1)}M${f(R - dw * 0.5)},${f(y0)}V${f(y1)}`, sw});
      else if (n.env === 'Vmatrix') box.paths.push({d: `M${f(dw * 0.35)},${f(y0)}V${f(y1)}M${f(dw * 0.65)},${f(y0)}V${f(y1)}M${f(R - dw * 0.35)},${f(y0)}V${f(y1)}M${f(R - dw * 0.65)},${f(y0)}V${f(y1)}`, sw});
      else if (n.env === 'cases') { const xr = dw * 0.85, xl = dw * 0.15, xm = dw * 0.5; box.paths.push({d: `M${f(xr)},${f(y0)}Q${f(xm)},${f(y0)} ${f(xm)},${f(y0 + (ym - y0) * 0.3)}V${f(ym - (ym - y0) * 0.25)}Q${f(xm)},${f(ym)} ${f(xl)},${f(ym)}Q${f(xm)},${f(ym)} ${f(xm)},${f(ym + (y1 - ym) * 0.25)}V${f(y1 - (y1 - ym) * 0.3)}Q${f(xm)},${f(y1)} ${f(xr)},${f(y1)}`, sw, join: true}); }
      x += sz * 0.08; put(box); x += sz * 0.08;
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
  const style = CUR.letterStyle;
  const forcedItalic = style === 'italic' || style === 'boldItalic';
  const bold = ctx.bold || n.font === 'bf' || n.font === 'bfit' || style === 'bold' || style === 'boldItalic';
  const add = (t, it) => {
    if (!t) return;
    if (n.font === 'auto' && style && style !== 'auto') it = forcedItalic;
    /* a placeholder of the symbol picker is an item of its own, drawn as a box */
    if (t.includes(PLACEHOLDER) && t !== PLACEHOLDER) { for (const part of t.split(new RegExp(`(${PLACEHOLDER})`))) add(part, it); return; }
    const last = items[items.length - 1];
    if (last && last.it && !it && !/^\s/.test(t)) x += sz * 0.05;
    const w = textWidth(t, sz, it, bold), ko = /[가-힣ㄱ-ㅎ]/.test(t);
    items.push({x, y: 0, t, size: sz, it: it && (!ko || forcedItalic) && t !== PLACEHOLDER, bf: bold, ko, ...(t === PLACEHOLDER ? {ph: true} : {})}); x += w; if ([...t].some(highChar)) high = true;
  };
  let s = n.s;
  /* in maths: a true minus sign, and room around relations and binary operators inside the run (a sign is unary at
     the start, after a relation, an operator or an opening bracket); at the run's ends the spacing between atoms in
     layout() does it, so the run is trimmed there */
  if (ctx.math && n.font === 'auto' && !n.sym) {
    const orig = s, OPS = '=≈≠≤≥<>≡∝→⇒−+±∓×·-';
    s = s.replace(/-/g, '−').replace(/\s*([=≈≠≤≥<>≡∝→⇒])\s*/g, ' $1 ').replace(/\s*([−+±∓×·])\s*/g, (m, op, off, all) => {
      const before = all.slice(0, off).trimEnd();
      const unary = before === '' ? (ctx.lead || UNARY_AFTER.has(ctx.prev ?? null)) : /[=≈≠≤≥<>≡∝→⇒(\[{,−+±∓×·]$/.test(before);
      return unary ? (before === '' ? op : ' ' + op) : ` ${op} `;
    });
    if (OPS.includes(orig.trimStart()[0])) s = s.trimStart();
    if (OPS.includes(orig.trimEnd().slice(-1))) s = s.trimEnd();
  }
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
/** the glyph boxes of a label laid out at size sz (for tests): [{t, x, w, y, size, it}] in reading order, each its
 *  advance wide — the next glyph on the same line must start at or after x + w */
export function glyphBoxes(src, sz = 100, style = 'textbook') {
  const saved = CUR; CUR = {...STYLES[style] || STYLES.textbook, ls: 1, ss: 1};
  const b = texLayout(src, sz), out = b.items.map(it => ({t: it.t, x: it.x, w: textWidth(it.t, it.size, it.it, it.bf), y: it.y, size: it.size, it: !!it.it}));
  CUR = saved; return out;
}
/** the runs of a label (for tests and the editor): [{t, it, sh: '' | 'sub' | 'sup'}] */
export function texRuns(src) {
  const b = texLayout(src, 100);
  return b.items.map(it => ({t: it.t, it: !!it.it, sh: it.y > 5 ? 'sub' : it.y < -5 ? 'sup' : ''}));
}
/** SVG of a label at (x, y) px, anchored 'start' | 'middle' | 'end', its middle on y */
export function texText(src, x, y, size = 16, anchor = 'middle', extra = '', opts = {}) {
  /* object names (A, B, P, a point's p) set upright in the styles that do so (수능, JEE) */
  if ((!CUR.letterStyle || CUR.letterStyle === 'auto') && CUR.uprightNames && (opts.name || opts.point) && typeof src === 'string' && (opts.point ? /^[A-Za-z]('|_\{?[0-9A-Za-z]{1,3}\}?)?$/ : /^[A-Z]('|_\{?[0-9]{1,3}\}?)?$/).test(src)) src = `\\mathrm{${src[0]}}${src.slice(1)}`;
  const sz = size * (opts.raw ? 1 : CUR.ls), b = texLayout(src, sz);
  if (!b.items.length && !b.paths.length) return '';
  const x0 = anchor === 'start' ? x : anchor === 'end' ? x - b.w : x - b.w / 2, base = y + (b.a - b.d) / 2;
  const color = /fill="([^"]+)"/.exec(extra)?.[1] || '#000';
  const halo = opts.halo ? ` stroke="#fff" stroke-width="${f(Math.max(2, sz * 0.22))}" stroke-linejoin="round" paint-order="stroke"` : '';
  let t = '';
  const family = letterFont();
  const kfont = it => !family && it.ko && (opts.caption ? CUR.caption : CUR.hangul) ? ` font-family="${esc(opts.caption ? CUR.caption : CUR.hangul).replace(/&#39;/g, "'")}"` : '';
  let ph = '';
  for (const it of b.items) if (it.ph) { const w = textWidth(PLACEHOLDER, it.size, false, false); ph += `<rect class="ph" x="${f(x0 + it.x + it.size * 0.06)}" y="${f(base + it.y - it.size * 0.66)}" width="${f(w - it.size * 0.12)}" height="${f(it.size * 0.78)}" rx="${f(it.size * 0.08)}" fill="#dbeafe" stroke="#2563eb" stroke-width="${f(Math.max(0.6, it.size * 0.05))}" stroke-dasharray="${f(it.size * 0.12)} ${f(it.size * 0.08)}"/>`; }
  for (const it of b.items) if (!it.ph) t += `<tspan x="${f(x0 + it.x)}" y="${f(base + it.y)}"${Math.abs(it.size - sz) > 0.01 ? ` font-size="${f(it.size)}"` : ''}${it.it ? ' font-style="italic"' : ''}${it.bf ? ' font-weight="bold"' : ''}${kfont(it)}>${esc(it.t)}</tspan>`;
  let p = '';
  for (const q of b.paths) {
    const ox = x0 + (q.ox || 0), oy = base + (q.oy || 0);
    if (q.dot) p += `<circle cx="${f(ox + q.dot[0])}" cy="${f(oy + q.dot[1])}" r="${f(q.dot[2])}" fill="${color}"/>`;
    else p += `<path d="${q.d}" transform="translate(${f(ox)},${f(oy)})" fill="none" stroke="${color}" stroke-width="${f(q.sw)}"${q.join ? ' stroke-linejoin="round" stroke-linecap="round"' : ''}/>`;
  }
  return `<g class="tex"${extra.replace(/fill="[^"]+"/, '')}>${ph}${t ? `<text font-size="${f(sz)}" font-family="${esc(family || CUR.font).replace(/&#39;/g, "'")}" fill="${color}"${halo}>${t}</text>` : ''}${p}</g>`;
}
/** a label on its own, as an SVG document (the editor's previews and the symbol picker) */
export function texSVG(src, size = 18, style = 'textbook', {letterStyle, letterFamily} = {}) {
  const saved = CUR; CUR = {...STYLES[style] || STYLES.textbook, ls: 1, ss: 1, letterStyle, letterFamily};
  const b = texLayout(src, size), pad = 3, W = Math.max(8, b.w + 2 * pad), H = b.a + b.d + 2 * pad;
  const out = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${f(W)} ${f(H)}" width="${f(W)}" height="${f(H)}">${texText(src, pad, pad + b.a - (b.a - b.d) / 2, size, 'start')}</svg>`;
  CUR = saved; return out;
}

/** the points of a data curve: "x,y x,y …" (or ; between points) */
export function dataPoints(src) { return String(src || '').trim().split(/[\s;]+/).map(t => t.split(',').map(Number)).filter(p => p.length === 2 && p.every(Number.isFinite)).map(([x, y]) => ({x, y})).slice(0, 80); }
const FORCE_LABEL = {gravity: '$mg$', normal: '$N$', friction: '$f$', tension: '$T$', spring: '$F_s$', applied: '$F$', centripetal: '$m\\omega^2 r$'};
/* dash patterns in px: dashed from the style's measured dash; dotted and dash-dot from it */
const dashOf = (pattern, st) => { const [a, b] = st.dash; return pattern === 'dashed' ? [a, b] : pattern === 'dotted' ? [Math.max(0.6, st.thin * 0.9), b * 1.1] : pattern === 'dashdot' ? [a * 1.6, b * 0.8, Math.max(0.8, st.thin), b * 0.8] : null; };
const fmtSI = (v0, unit) => {
  const v = +(+v0).toPrecision(6), a = Math.abs(v); if (!Number.isFinite(v)) return '—';
  const [k, p] = a >= 1e6 ? [1e-6, 'M'] : a >= 1e3 ? [1e-3, 'k'] : a >= 1 || a === 0 ? [1, ''] : a >= 1e-3 ? [1e3, 'm'] : a >= 1e-6 ? [1e6, 'μ'] : [1e9, 'n'];
  const x = v * k; return `${Math.abs(x) >= 100 ? x.toFixed(0) : Math.abs(x) >= 10 ? x.toFixed(1) : x.toFixed(2)} ${p}${unit}`;
};
let CLIP = 0;
/* a smooth path through screen points (Catmull–Rom turned into cubic Béziers) */
function smoothPath(pts, closed) {
  const n = pts.length; if (n < 3) return 'M' + pts.map(q => `${f(q.x)},${f(q.y)}`).join('L') + (closed ? 'Z' : '');
  const at = i => closed ? pts[(i + n) % n] : pts[Math.max(0, Math.min(n - 1, i))];
  let d = `M${f(pts[0].x)},${f(pts[0].y)}`;
  for (let i = 0; i < (closed ? n : n - 1); i++) {
    const p0 = at(i - 1), p1 = at(i), p2 = at(i + 1), p3 = at(i + 2);
    d += `C${f(p1.x + (p2.x - p0.x) / 6)},${f(p1.y + (p2.y - p0.y) / 6)} ${f(p2.x - (p3.x - p1.x) / 6)},${f(p2.y - (p3.y - p1.y) / 6)} ${f(p2.x)},${f(p2.y)}`;
  }
  return d + (closed ? 'Z' : '');
}
const X2U = {resistor: 'Ω', rheostat: 'Ω', bulb: 'Ω', galvanometer: 'Ω', battery: 'V', cell: 'V', dc: 'V', ac: 'V', diode: 'V', led: 'V', capacitor: 'μF', dielectric: 'μF', inductor: 'H'};

/** The scene as SVG text. opts: width (px of the drawing, 800), view (the world rectangle; else scene.view),
 *  edit (ids on the objects, a grid when grid, the selected id and its handles), style (else scene.style),
 *  labelScale and strokeScale (labels and lines larger, e.g. for a printed paper or a phone), forces (map body →
 *  [{kind, v, at}]), trails (map body → [{x,y}]), anchors (map 'spring:end' → point), conical (list of {centre,
 *  radius}), circuit (solveCircuit's result: readings drawn on the elements), background. */
export function renderSVG(scene, opts = {}) {
  const W = opts.width || 800, view = opts.view || scene.view || {x: -0.5, y: -0.5, w: 4, h: 3};
  const S = W / view.w, H = Math.max(40, Math.round(view.h * S));
  /* the figure's style; an object with a style of its own is drawn in that one (setStyle, in the loop below) */
  const st0 = STYLES[opts.style || scene.style] || STYLES.textbook, ss = opts.strokeScale || 1;
  let st = st0, baseLs = (opts.labelScale || 1) * st.labelScale;
  CUR = {...st, ls: baseLs, ss};
  const X = x => (x - view.x) * S, Y = y => (view.y + view.h - y) * S, P = p => `${f(X(p.x))},${f(Y(p.y))}`;
  const byId = new Map(scene.objects.map(o => [o.id, o]));
  const edit = !!opts.edit, selSet = new Set(Array.isArray(opts.selected) ? opts.selected : opts.selected ? [opts.selected] : []), sel = selSet.size === 1 ? [...selSet][0] : '';
  const showValues = opts.values ?? !!scene.values;
  const out = [];
  const minW = opts.edit ? 0.75 : 0;
  const weights = s => ({lw: Math.max(minW, s.lw * ss), thin: Math.max(minW * 0.8, s.thin * ss), hair: Math.max(minW * 0.7, s.hair * ss), thick: Math.max(minW, s.thick * ss), HL: s.headLen * ss});
  let ink = st.ink, B0 = weights(st);
  let lw = B0.lw, thin = B0.thin, hair = B0.hair, thick = B0.thick, HL = B0.HL, om = 1;
  let gray = st.gray, light = st.light, fill = st.fill, cap = st.round ? ' stroke-linecap="round" stroke-linejoin="round"' : '';
  const setStyle = s => { st = s; ink = s.ink; B0 = weights(s); gray = s.gray; light = s.light; fill = s.fill; cap = s.round ? ' stroke-linecap="round" stroke-linejoin="round"' : ''; baseLs = (opts.labelScale || 1) * s.labelScale; CUR = {...s, ls: baseLs, ss}; };
  const geo = scene.objects.some(o => GEO_TYPES.includes(o.type)) ? computeGeometry(scene) : null;
  const lbl = (s, x, y, size = 15, anchor = 'middle', extra = '', o2) => texText(s, x, y, size, anchor, extra, o2);
  const group = (o, inner) => edit ? `<g data-id="${esc(o.id)}" class="obj${selSet.has(o.id) ? ' sel' : ''}${o.lock ? ' locked' : ''}">${inner}</g>` : inner;
  const hit = d => edit ? `<path d="${d}" fill="none" stroke="transparent" stroke-width="12" pointer-events="stroke"/>` : '';
  const hitBox = (x, y, w, h) => edit ? `<rect x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(h)}" fill="transparent"/>` : '';
  const dash = (pattern, k = 1) => { const d = dashOf(pattern, st); return d ? ` stroke-dasharray="${d.map(v => f(v * ss * k * om)).join(' ')}"${pattern === 'dotted' ? ' stroke-linecap="round"' : ''}` : ''; };
  /* (an extra stroke colour replaces the ink: a doubled attribute would make the file invalid XML) */
  const line = (a, b, w = lw, extra = '') => `<line x1="${f(a.x)}" y1="${f(a.y)}" x2="${f(b.x)}" y2="${f(b.y)}"${/ stroke="/.test(extra) ? '' : ` stroke="${ink}"`} stroke-width="${f(w)}"${extra.includes('linecap') ? '' : cap}${extra}/>`;
  const poly = (pts, w = lw, extra = '') => `<polyline points="${pts.map(p => `${f(p.x)},${f(p.y)}`).join(' ')}" fill="none" stroke="${ink}" stroke-width="${f(w)}" stroke-linejoin="round"${extra}/>`;
  const hatch = (x1, y1, x2, y2, nx, ny, gap = st.hatchGap) => {
    /* short slanted strokes on the solid side (nx, ny: the side, in screen px) of the line from (x1,y1) to (x2,y2) */
    const L = Math.hypot(x2 - x1, y2 - y1); if (L < 1) return '';
    const g2 = gap * ss, n = Math.max(1, Math.floor(L / g2)), ux = (x2 - x1) / L, uy = (y2 - y1) / L, hl = st.hatchLen * ss, ta = 1 / Math.tan(st.hatchAngle * Math.PI / 180);
    let d = '';
    for (let i = 0; i <= n; i++) { const px = x1 + ux * (i * L / n), py = y1 + uy * (i * L / n); d += `M${f(px)},${f(py)}l${f(nx * hl - ux * hl * ta)},${f(ny * hl - uy * hl * ta)}`; }
    return `<path d="${d}" stroke="${ink}" stroke-width="${f(Math.max(0.4, st.hatchW * ss * om))}" fill="none"/>`;
  };
  /* an arrowhead at tip pointing along (ux, uy): returns [svg, the point the shaft should end at] */
  const head = (tip, ux, uy, {color = ink, len = HL, kind = st.head, w = thin} = {}) => {
    const px = -uy, py = ux, hw = len * (kind === 'stealth' ? Math.max(0.3, st.headW) : kind === 'open' ? 0.38 : st.headW), base = {x: tip.x - ux * len, y: tip.y - uy * len};
    if (kind === 'none') return ['', tip];
    if (kind === 'open') return [`<path d="M${f(base.x + px * hw)},${f(base.y + py * hw)}L${f(tip.x)},${f(tip.y)}L${f(base.x - px * hw)},${f(base.y - py * hw)}" fill="none" stroke="${color}" stroke-width="${f(Math.max(w, 1))}" stroke-linejoin="miter"/>`, tip];
    if (kind === 'stealth') { const notch = {x: tip.x - ux * len * 0.68, y: tip.y - uy * len * 0.68}; return [`<path d="M${f(tip.x)},${f(tip.y)}L${f(base.x + px * hw)},${f(base.y + py * hw)}L${f(notch.x)},${f(notch.y)}L${f(base.x - px * hw)},${f(base.y - py * hw)}Z" fill="${color}"/>`, notch]; }
    return [`<path d="M${f(tip.x)},${f(tip.y)}L${f(base.x + px * hw)},${f(base.y + py * hw)}L${f(base.x - px * hw)},${f(base.y - py * hw)}Z" fill="${color}"/>`, {x: base.x + ux, y: base.y + uy}];
  };
  const arrow = (from, to, {color = ink, width = thin * 1.25, head: hl = HL, kind = st.head, pattern = 'solid'} = {}) => {
    const dx = to.x - from.x, dy = to.y - from.y, L = Math.hypot(dx, dy);
    if (L < 1) return '';
    const ux = dx / L, uy = dy / L, [hs, end] = head(to, ux, uy, {color, len: Math.min(hl, L * 0.7), kind, w: width});
    return `<line x1="${f(from.x)}" y1="${f(from.y)}" x2="${f(end.x)}" y2="${f(end.y)}" stroke="${color}" stroke-width="${f(width)}"${cap}${dash(pattern)}/>` + hs;
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
    const gp = Math.max(4, Math.min(st.hatchGap, 9) * 0.8 * ss);
    const pat = kind === 'dots' ? `<pattern id="${id}" width="${f(7 * ss)}" height="${f(7 * ss)}" patternUnits="userSpaceOnUse"><circle cx="${f(3.5 * ss)}" cy="${f(3.5 * ss)}" r="${f(0.9 * ss)}" fill="${ink}"/></pattern>`
      : kind === 'lines' ? `<pattern id="${id}" width="${f(8 * ss)}" height="${f(gp)}" patternUnits="userSpaceOnUse"><line x1="0" y1="1" x2="${f(5 * ss)}" y2="1" stroke="${ink}" stroke-width="${f(Math.max(0.4, st.hatchW * ss * 0.8))}"/></pattern>`
      : `<pattern id="${id}" width="${f(gp)}" height="${f(gp)}" patternUnits="userSpaceOnUse" patternTransform="rotate(${kind === 'hatch2' ? -45 : 45})"><line x1="0" y1="0" x2="0" y2="${f(gp)}" stroke="${ink}" stroke-width="${f(Math.max(0.4, st.hatchW * ss * 0.8))}"/></pattern>`;
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
    /* the world's origin: the two grid lines through it a little darker (a dot there read as a stray point) */
    const o = {x: X(0), y: Y(0)}, ax = [];
    if (o.x >= 0 && o.x <= W) ax.push(`M${f(o.x)},0V${H}`); if (o.y >= 0 && o.y <= H) ax.push(`M0,${f(o.y)}H${W}`);
    if (ax.length) out.push(`<path d="${ax.join('')}" stroke="#c3cad8" stroke-width="0.9" fill="none" class="grid origin"/>`);
  }
  /* trails first, under everything */
  for (const [id, pts] of opts.trails || []) if (pts.length > 1) out.push(`<polyline points="${pts.map(p => P(p)).join(' ')}" fill="none" stroke="#666" stroke-width="1" stroke-dasharray="4 3" data-trail="${esc(id)}"/>`);


  /* graphs: their ranges, fitted to what is plotted on them when auto */
  const ranges = new Map();
  for (const g of scene.objects.filter(o => o.type === 'graph')) {
    let r = {x0: g.xmin, x1: g.xmax, y0: g.ymin, y1: g.ymax};
    if (g.auto) {
      const pts = [];
      for (const c of scene.objects) if ((c.type === 'curve' || c.type === 'cycle') && c.graph === g.id) {
        if (c.type === 'cycle') gasCycle(c).legs.forEach(l => pts.push(...l.pts));
        else if (c.kind === 'points') pts.push(...dataPoints(c.data));
        else if (c.kind === 'func') { const fn = boundExpr(c.expr, c.params); for (let i = 0; i <= 60; i++) { const x = c.x1 + (c.x2 - c.x1) * i / 60, y = fn ? fn(x) : NaN; if (Number.isFinite(y) && Math.abs(y) < 1e6) pts.push({x, y}); } }
        else if (c.kind === 'param' || c.kind === 'polar') { const fx = boundExpr(c.expr, c.params, 't'), fy = c.kind === 'param' ? boundExpr(c.expr2, c.params, 't') : null; for (let i = 0; i <= 120 && fx; i++) { const t = c.x1 + (c.x2 - c.x1) * i / 120, v = fx(t), p = c.kind === 'polar' ? {x: v * Math.cos(t), y: v * Math.sin(t)} : {x: v, y: fy ? fy(t) : NaN}; if (Number.isFinite(p.x) && Number.isFinite(p.y) && Math.abs(p.x) < 1e6 && Math.abs(p.y) < 1e6) pts.push(p); } }
        else if (c.kind === 'ineq') continue;
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
  const RANK = {nnet: 3, fbox: 4, farrow: 3.5, gpoly: 1.5, gcircle: 2, gline: 2.2, gangle: 6.5, gpoint: 7.5, joint: 3.2, panel: -4, region: -3, container: -1.5, utube: -1.5, gasbox: -1, track: 0, plank: 4.5, wheel: 5, bridge: 3, rails: 2, transformer: 3, parrows: 6, brace: 7, callout: 7, particle: 6, nucleus: 5, interference: 1, pulse: 2, screen: 1, eye: 5, source: 5, fiber: 2, thermometer: 5, heater: 4, field: -2, graph: -2, well: -1, levels: -1, spacetime: -1, reservoir: -1, fieldlines: -0.5, floor: 0, ceiling: 0, wall: 0, incline: 1, line: 2, axes: 2, slab: 1, prism: 1,
    curve: 2.5, cycle: 2.5, worldline: 2.5, pulley: 4, pivot: 4, string: 3, rod: 3, spring: 3, block: 5, ball: 5, force: 6, label: 7, dim: 7, arc: 7, point: 7, vector: 6, oarrow: 6, ray: 5.5, charge: 5, element: 3};
  const order = [...scene.objects].sort((a, b) => (RANK[a.type] ?? 4) - (RANK[b.type] ?? 4));
  /* a gray strip on the solid side of a fixed surface (수능 draws walls and ceilings so) */
  const strip = (a, b, nx, ny) => { const t = Math.max(3, 4.2 * ss * (15 / st.labelPt) * 0.6); return `<path d="M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}L${f(b.x + nx * t)},${f(b.y + ny * t)}L${f(a.x + nx * t)},${f(a.y + ny * t)}Z" fill="${st.light}" stroke="none"/>`; };
  /* the values written on the figure when the scene asks for them (2 kg, 30°, k = 40 N/m, 10 Ω …) */
  const nv = v => `${+(+v).toPrecision(3)}`.replace('-', '−');
  const valueMark = o => {
    const T = o.type, at = (p, t, dx = 0, dy = 0, anchor = 'middle') => lbl(t, p.x + dx, p.y + dy, 12.5, anchor, '', {halo: true});
    if (isBody(o)) { const p = screen(opts.poses?.get?.(o.id) || poseOf(o)), r = (isRound(o) ? o.r : o.h / 2) * S; return at(p, `\\mathrm{${nv(o.mass)}\\,kg}`, 0, r + 11); }
    if (T === 'incline') { const c = inclineCorners(o), q = screen(c.foot); return at(q, `${nv(o.angle)}^\\circ`, (o.flip ? -1 : 1) * 46, -7); }
    if (T === 'spring') { const A = byId.get(o.a), B = byId.get(o.b); if (!A || !B) return ''; const a = screen(isBody(A) ? poseOf(A) : A), b = screen(isBody(B) ? poseOf(B) : B); return at({x: (a.x + b.x) / 2, y: (a.y + b.y) / 2}, `\\mathrm{${nv(o.k)}\\,N/m}`, 0, 18); }
    if (T === 'force') { const b = byId.get(o.on); if (!b) return ''; const p = screen(poseOf(b)), th = o.angle * Math.PI / 180, L = o.len * S; return at({x: p.x + Math.cos(th) * L, y: p.y - Math.sin(th) * L}, `\\mathrm{${nv(o.F)}\\,N}`, 0, 16); }
    if (T === 'element' && X2U[o.kind]) { const m = screen({x: (o.x1 + o.x2) / 2, y: (o.y1 + o.y2) / 2}), vert = Math.abs(o.x2 - o.x1) < Math.abs(o.y2 - o.y1); return at(m, `\\mathrm{${nv(o.value)}\\,${X2U[o.kind]}}`, vert ? -22 : 0, vert ? 0 : 22, vert ? 'end' : 'middle'); }
    if (T === 'lens' || T === 'mirror') { const c = screen(o); return o.f ? at(c, `f = \\mathrm{${nv(o.f)}\\,m}`, 0, o.h * S / 2 + 14) : ''; }
    if (T === 'charge') { const c = screen(o); return at(c, `\\mathrm{${nv(o.q)}\\,\\mu C}`, 0, Math.max(6, o.r * S) + 12); }
    if (T === 'rails') { const m = motionalEMF(o), p = screen({x: o.x + o.w / 2, y: o.y}); return at(p, `\\mathcal{E} = \\mathrm{${nv(m.emf)}\\,V}`, 0, 30); }
    if (T === 'container') { const p = screen({x: o.x + o.w / 2, y: o.y}); return at(p, `\\rho = \\mathrm{${nv(o.rho)}\\,kg/m^3}`, 0, 14); }
    if (T === 'bridge') { const p = screen(bridgeJockey(o)); return at(p, `l = \\mathrm{${nv(o.at * 100)}\\,cm}`, 0, 30); }
    if (T === 'pulley' || T === 'wheel') { const c = screen(o); return at(c, `\\mathrm{${nv(o.r)}\\,m}`, 0, o.r * S + 12); }
    return '';
  };
  for (const o of order) {
    let s = '';
    const T = o.type;
    /* an object drawn in a style of its own */
    const ost = (o.style && STYLES[o.style]) || st0;
    if (ost !== st) setStyle(ost);
    /* the object's own line weight and label size */
    om = o.lw || 1; lw = B0.lw * om; thin = B0.thin * om; hair = B0.hair * om; thick = B0.thick * om; HL = B0.HL * Math.sqrt(om); CUR.ls = baseLs * (o.ls || 1);
    CUR.letterStyle = o.letterStyle;
    CUR.letterFamily = o.letterFamily;
    if (T === 'floor') {
      const a = screen(o), b = screen({x: o.x + o.w, y: o.y});
      s = `${line(a, b)}${o.hatch && st.floor !== 'line' ? hatch(a.x, a.y, b.x, b.y, 0, 1) : ''}${hit(`M${f(a.x)},${f(a.y)}H${f(b.x)}`)}`;
    } else if (T === 'ceiling') {
      const a = screen(o), b = screen({x: o.x + o.w, y: o.y});
      s = `${st.wall === 'gray' && o.hatch ? strip(a, b, 0, -1) : ''}${line(a, b)}${o.hatch && st.wall !== 'gray' ? hatch(a.x, a.y, b.x, b.y, 0, -1) : ''}${hit(`M${f(a.x)},${f(a.y)}H${f(b.x)}`)}`;
    } else if (T === 'wall') {
      const a = screen(o), b = screen({x: o.x, y: o.y + o.h}), side = o.side === 'left' ? -1 : 1;
      s = `${st.wall === 'gray' ? strip(a, b, side, 0) : ''}${line(a, b)}${st.wall !== 'gray' ? hatch(b.x, b.y, a.x, a.y, side, 0) : ''}${hit(`M${f(a.x)},${f(a.y)}V${f(b.y)}`)}`;
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
        if (to) s += line(c, screen(to), thick * 1.4);
      }
      s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r)}" fill="${fill}" stroke="${ink}" stroke-width="${f(lw)}"/><circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(Math.max(1.6, r * 0.14))}" fill="${ink}"/>`;
    } else if (T === 'pivot') {
      const c = screen(o), onCeiling = scene.objects.some(x => x.type === 'ceiling' && Math.abs(x.y - o.y) < 0.02 && o.x >= x.x && o.x <= x.x + x.w);
      if (!onCeiling) s += line({x: c.x - 13, y: c.y - 7}, {x: c.x + 13, y: c.y - 7}) + hatch(c.x - 13, c.y - 7, c.x + 13, c.y - 7, 0, -1) + line({x: c.x, y: c.y - 7}, c, 1.4 * ss);
      s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(Math.max(2, st.dot * ss * 1.15))}" fill="#fff" stroke="${ink}" stroke-width="${f(thin)}"/>`;
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
      if (o.mode === 'conical') s = conicalMarks(o) + s;
    } else if (T === 'rod') {
      const A = byId.get(o.a), B = byId.get(o.b);
      if (A && B) { const a = screen(poseOf(A)), b = screen(opts.poses?.get?.(B.id) || poseOf(B)); s = `${line(a, b, Math.max(thick * 2.2, 2 * ss), ' stroke-linecap="round"')}${hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`)}`;
        if (o.label) { const n = vec.unit({x: -(b.y - a.y), y: b.x - a.x}); s += lbl(o.label, (a.x + b.x) / 2 + n.x * 14, (a.y + b.y) / 2 + n.y * 14, 15); } }
      if (o.mode === 'conical') s = conicalMarks(o) + s;
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
          const ux = (b.x - a.x) / L, uy = (b.y - a.y) / L, lead = Math.min(12 * ss, L * 0.15), n = Math.round(o.coils) * 2, amp = 6.5 * ss;
          let d = `M${f(a.x)},${f(a.y)}l${f(ux * lead)},${f(uy * lead)}`;
          const seg = (L - 2 * lead) / n;
          for (let i = 0; i < n; i++) { const t = lead + seg * (i + 0.5), side = i % 2 ? -1 : 1; d += `L${f(a.x + ux * t - uy * amp * side)},${f(a.y + uy * t + ux * amp * side)}`; }
          d += `L${f(b.x - ux * lead)},${f(b.y - uy * lead)}L${f(b.x)},${f(b.y)}`;
          s = `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(thin * 1.15)}" stroke-linejoin="round"/>${hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`)}`;
          if (o.label) { let nx = -uy, ny = ux; if (Math.abs(uy) > 0.7 ? nx < 0 : ny > 0) { nx = -nx; ny = -ny; } s += lbl(o.label, (a.x + b.x) / 2 + nx * 20, (a.y + b.y) / 2 + ny * 20, 15); }
        }
      }
    } else if (T === 'block') {
      const p = opts.poses?.get?.(o.id) || poseOf(o), ca = Math.cos(p.angle), sa = Math.sin(p.angle), hw = o.w / 2, hh = o.h / 2;
      const L2W = (u, v) => ({x: p.x + u * ca - v * sa, y: p.y + u * sa + v * ca});
      let c = screen(p), bh = hh, by = 0;
      if (o.look === 'cart' || o.look === 'car') {
        /* wheels under the body: the block's height holds them */
        const rw = Math.min(o.h * 0.22, o.w * 0.14), wy = -hh + rw;
        bh = (o.h - 2 * rw) / 2 * (o.look === 'car' ? 0.62 : 1); by = -hh + 2 * rw + bh;
        const body = [[-hw, by - bh], [hw, by - bh], [hw, by + bh], [-hw, by + bh]].map(([u, v]) => P(L2W(u, v)));
        s = `<polygon points="${body.join(' ')}" fill="${fill}" stroke="${ink}" stroke-width="${f(lw)}" stroke-linejoin="round"/>`;
        if (o.look === 'car') { const top = by + bh, ch = o.h - 2 * rw - 2 * bh; const cab = [[-hw * 0.62, top], [-hw * 0.38, top + ch], [hw * 0.32, top + ch], [hw * 0.6, top]].map(([u, v]) => P(L2W(u, v))); s += `<polyline points="${cab.join(' ')}" fill="${fill}" stroke="${ink}" stroke-width="${f(lw)}" stroke-linejoin="round"/>`; }
        for (const u of [-hw + rw * 1.4, hw - rw * 1.4]) { const q = screen(L2W(u, wy)); s += `<circle cx="${f(q.x)}" cy="${f(q.y)}" r="${f(rw * S)}" fill="#fff" stroke="${ink}" stroke-width="${f(lw)}"/><circle cx="${f(q.x)}" cy="${f(q.y)}" r="${f(Math.max(1, rw * S * 0.22))}" fill="${ink}"/>`; }
        c = screen(L2W(0, by));
      } else {
        const pts = [[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]].map(([u, v]) => P(L2W(u, v)));
        s = `<polygon points="${pts.join(' ')}" fill="${fill}" stroke="${ink}" stroke-width="${f(lw)}" stroke-linejoin="round"/>`;
      }
      const room = Math.min(o.w, 2 * bh);
      if (o.label) s += lbl(o.label, c.x, c.y, Math.min(Math.max(11, Math.min(17, room * S * 0.45)), room * S * 0.62 / CUR.ls), 'middle', '', {name: true});
    } else if (T === 'ball') {
      const p = poseOf(o), c = screen(p), r = o.r * S;
      s = `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(Math.max(2.5, r))}" fill="${fill}" stroke="${ink}" stroke-width="${f(lw)}"/>`;
      if (o.label) s += r >= 13 * CUR.ls ? lbl(o.label, c.x, c.y, Math.min(16, r * 0.9 / CUR.ls), 'middle', '', {name: true}) : lbl(o.label, c.x + r + 5, c.y - r - 6, 15, 'start', '', {name: true});
    } else if (T === 'force') {
      const b = byId.get(o.on);
      if (b) { const p = screen(opts.poses?.get?.(b.id) || poseOf(b)), th = o.angle * Math.PI / 180, L = o.len * S, tip = {x: p.x + Math.cos(th) * L, y: p.y - Math.sin(th) * L};
        s = arrow(p, tip, {width: lw * 1.15, head: HL * 1.1, color: st.vecInk || ink}) + (o.label ? lbl(o.label, tip.x + Math.cos(th) * 13, tip.y - Math.sin(th) * 13, 16, 'middle', st.vecInk ? ` fill="${st.vecInk}"` : '') : '') + hit(`M${f(p.x)},${f(p.y)}L${f(tip.x)},${f(tip.y)}`); }

    /* ── electromagnetism ── */
    } else if (T === 'element') {
      s = drawElement(o);
    } else if (T === 'ground') {
      const c = screen(o), w = 12 * ss;
      s = line(c, {x: c.x, y: c.y + 10}, thin) + line({x: c.x - w, y: c.y + 10}, {x: c.x + w, y: c.y + 10}, lw) + line({x: c.x - w * 0.62, y: c.y + 14.5}, {x: c.x + w * 0.62, y: c.y + 14.5}, lw) + line({x: c.x - w * 0.25, y: c.y + 19}, {x: c.x + w * 0.25, y: c.y + 19}, lw)
        + (o.label ? lbl(o.label, c.x + w + 6, c.y + 14, 14, 'start') : '') + hitBox(c.x - w, c.y, 2 * w, 20);
    } else if (T === 'charge') {
      const c = screen(o), r = Math.max(6, o.r * S), pos = o.q >= 0;
      if (o.trail) { const pts = chargePath(scene, o, view).map(screen); if (pts.length > 1) s += poly(pts, thin, dash('dashed')) + midHead(pts, 0.35, {len: HL * 0.8}) + midHead(pts, 0.8, {len: HL * 0.8}); }
      s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r)}" fill="${pos ? fill : gray || '#fff'}" stroke="${ink}" stroke-width="${f(thin * 1.15)}"/>` + (pos ? plus(c, r * 0.55, Math.max(1, r * 0.16)) : minus(c, r * 0.55, Math.max(1, r * 0.16)));
      if (o.showV && Math.hypot(o.vx, o.vy) > 1e-9) { const sp = Math.hypot(o.vx, o.vy), ux = o.vx / sp, uy = -o.vy / sp, L = Math.max(34, Math.min(80, 0.12 * W)), tip = {x: c.x + ux * (r + L), y: c.y + uy * (r + L)};
        s += arrow({x: c.x + ux * r, y: c.y + uy * r}, tip, {width: thin * 1.25}) + (o.vLabel ? (() => { let nx = -uy, ny = ux; if (ny > 0) { nx = -nx; ny = -ny; } return lbl(o.vLabel, c.x + ux * (r + L * 0.55) + nx * 14, c.y + uy * (r + L * 0.55) + ny * 14, 15, 'middle', '', {halo: true}); })() : ''); }
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
      const sp = o.spacing * S, r = Math.max(3.5, Math.min(7, sp * 0.18)) * ss;
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
      if (o.gas) { let k = 1; const n = Math.round(Math.min(90, (w * (bot - py)) / 260)); for (let i = 0; i < n; i++) { k = (k * 16807) % 2147483647; const rx = (k % 1000) / 1000; k = (k * 16807) % 2147483647; const ry = (k % 1000) / 1000; s += `<circle cx="${f(p0.x + 6 + rx * (w - 12))}" cy="${f(py + pt / 2 + 6 + ry * (bot - py - pt / 2 - 12))}" r="${f(Math.max(1, st.dot * ss * 0.45))}" fill="${ink}"/>`; } }
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
        const sx = o.xstep > 0 && (r.x1 - r.x0) / o.xstep <= 200 ? o.xstep : step(r.x1 - r.x0), sy = o.ystep > 0 && (r.y1 - r.y0) / o.ystep <= 200 ? o.ystep : step(r.y1 - r.y0);
        for (let v = Math.ceil(r.x0 / sx) * sx; v <= r.x1 + 1e-9; v += sx) { const q = toGraph(o, {x: v, y: r.y0}); if (o.grid) s += line({x: q.x, y: p0.y}, {x: q.x, y: p0.y - h}, 0.5, ' stroke="#bbb"'); if (o.ticks && Math.abs(v) > sx * 1e-6) s += line({x: q.x, y: ax}, {x: q.x, y: ax + 4}, hair) + lbl(`\\mathrm{${(+v.toPrecision(3) + "").replace("-", "−")}}`, q.x, ax + 13, 11); }
        for (let v = Math.ceil(r.y0 / sy) * sy; v <= r.y1 + 1e-9; v += sy) { const q = toGraph(o, {x: r.x0, y: v}); if (o.grid) s += line({x: p0.x, y: q.y}, {x: p0.x + w, y: q.y}, 0.5, ' stroke="#bbb"'); if (o.ticks && Math.abs(v) > sy * 1e-6) s += line({x: ay, y: q.y}, {x: ay - 4, y: q.y}, hair) + lbl(`\\mathrm{${(+v.toPrecision(3) + "").replace("-", "−")}}`, ay - 6, q.y, 11, 'end'); }
      }
      s += arrow({x: p0.x - 4, y: ax}, {x: p0.x + w + 0.07 * w, y: ax}, {width: thin}) + arrow({x: ay, y: p0.y + 4}, {x: ay, y: p0.y - h - 0.07 * h}, {width: thin});
      /* custom ticks "1:t_0, 2:2t_0": a tick, its label and a dotted guide across the plot */
      for (const [axis, src] of [['x', o.xt], ['y', o.yt]]) for (const part of String(src || '').split(',')) {
        const m = /^\s*(-?[\d.]+(?:e-?\d+)?)\s*:\s*(.+?)\s*$/i.exec(part); if (!m) continue; const v = +m[1]; if (!Number.isFinite(v)) continue;
        if (axis === 'x') { const q = toGraph(o, {x: v, y: r.y0}); s += line({x: q.x, y: ax}, {x: q.x, y: ax + 4}, hair) + line({x: q.x, y: ax}, {x: q.x, y: p0.y - h}, hair, dash(st.key === 'suneung' ? 'dashed' : 'dotted', 0.7)) + lbl(m[2], q.x, ax + 13, 14); }
        else { const q = toGraph(o, {x: r.x0, y: v}); s += line({x: ay, y: q.y}, {x: ay - 4, y: q.y}, hair) + line({x: ay, y: q.y}, {x: p0.x + w, y: q.y}, hair, dash(st.key === 'suneung' ? 'dashed' : 'dotted', 0.7)) + lbl(m[2], ay - 7, q.y, 14, 'end'); }
      }
      s += lbl(o.xlabel, p0.x + w * 1.07 + 6, ax + 2, 16, 'start') + lbl(o.ylabel, ay - 6, p0.y - h * 1.07 - 4, 16, 'end');
      if (o.origin) s += lbl(o.origin, ay - 8, ax + 11, 14, 'middle');
      s += hitBox(p0.x, p0.y - h, w, h);
    } else if (T === 'curve') {
      const g = byId.get(o.graph); if (g && ranges.has(g.id)) {
        const r = ranges.get(g.id), segs = [[]], col = o.color && o.color !== 'black' ? COLOR_HEX[o.color] : ink, ylo = r.y0 - (r.y1 - r.y0) * 0.02, yhi = r.y1 + (r.y1 - r.y0) * 0.02;
        const xlo = r.x0 - (r.x1 - r.x0) * 0.02, xhi = r.x1 + (r.x1 - r.x0) * 0.02, inside = p => Number.isFinite(p.x) && Number.isFinite(p.y) && p.x >= xlo && p.x <= xhi && p.y >= ylo && p.y <= yhi;
        const num = v => (+(+v).toPrecision(3)).toString().replace('-', '−');
        const tint = pts => { const pg = `polygon points="${pts.map(p => `${f(p.x)},${f(p.y)}`).join(' ')}"`; return gray ? `<${pg} fill="${col}" fill-opacity="${col === ink ? 0.12 : 0.18}" stroke="none"/>` : shade(pg, 'hatch'); };
        const fn = o.kind === 'func' || o.kind === 'ineq' ? boundExpr(o.expr, o.params) : null;
        const x0 = Math.max(o.x1, r.x0), x1 = Math.min(o.x2, r.x1);
        if (o.kind === 'func') {
          const N = 400;
          for (let i = 0; i <= N && fn; i++) { const x = x0 + (x1 - x0) * i / N, y = fn(x); if (Number.isFinite(y) && y >= ylo && y <= yhi) segs[segs.length - 1].push(toGraph(g, {x, y})); else if (segs[segs.length - 1].length) segs.push([]); }
        } else if (o.kind === 'param' || o.kind === 'polar') {
          const fx = boundExpr(o.expr, o.params, 't'), fy = o.kind === 'param' ? boundExpr(o.expr2, o.params, 't') : null, N = 720;
          for (let i = 0; i <= N && fx && (fy || o.kind === 'polar'); i++) {
            const t = o.x1 + (o.x2 - o.x1) * i / N, rr = fx(t), p = o.kind === 'polar' ? {x: rr * Math.cos(t), y: rr * Math.sin(t)} : {x: rr, y: fy(t)};
            if (inside(p)) segs[segs.length - 1].push(toGraph(g, p)); else if (segs[segs.length - 1].length) segs.push([]);
          }
        } else if (o.kind === 'ineq') {
          /* the part of the plot where y < f(x) (or >, ≤, ≥): shaded, its edge dashed when strict */
          const N = 300, below = o.rel === 'lt' || o.rel === 'le'; let poly2 = [];
          const flush = () => { if (poly2.length > 1) { const yb = toGraph(g, {x: r.x0, y: below ? r.y0 : r.y1}).y; s += tint([{x: poly2[0].x, y: yb}, ...poly2, {x: poly2[poly2.length - 1].x, y: yb}]); } poly2 = []; };
          for (let i = 0; i <= N && fn; i++) { const x = r.x0 + (r.x1 - r.x0) * i / N, y = fn(x); if (!Number.isFinite(y)) { flush(); continue; } poly2.push(toGraph(g, {x, y: Math.max(r.y0, Math.min(r.y1, y))})); const yy = fn(x); if (yy >= ylo && yy <= yhi) segs[segs.length - 1].push(toGraph(g, {x, y: yy})); else if (segs[segs.length - 1].length) segs.push([]); }
          flush();
        } else if (o.kind === 'points') segs[0] = dataPoints(o.data).map(p => toGraph(g, p));
        else segs[0] = processPoints(o.kind, o).map(p => toGraph(g, p));
        if (o.shade && o.kind !== 'ineq') { const y0 = toGraph(g, {x: r.x0, y: Math.max(r.y0, Math.min(r.y1, 0))}).y; for (const sg of segs) if (sg.length > 1) s += `<polygon points="${[{x: sg[0].x, y: y0}, ...sg, {x: sg[sg.length - 1].x, y: y0}].map(p => `${f(p.x)},${f(p.y)}`).join(' ')}" fill="${gray ? light : 'none'}" stroke="none"/>` + (gray ? '' : shade(`polygon points="${[{x: sg[0].x, y: y0}, ...sg, {x: sg[sg.length - 1].x, y: y0}].map(p => `${f(p.x)},${f(p.y)}`).join(' ')}"`, 'hatch')); }
        /* the area under a function from a1 to a2, its value written */
        if (o.kind === 'func' && o.area && fn) {
          const a1 = Math.max(Math.min(o.a1, o.a2), r.x0), a2 = Math.min(Math.max(o.a1, o.a2), r.x1);
          if (a2 > a1) {
            const pts = [], y0 = toGraph(g, {x: r.x0, y: Math.max(r.y0, Math.min(r.y1, 0))}).y;
            for (let i = 0; i <= 160; i++) { const x = a1 + (a2 - a1) * i / 160, y = fn(x); if (Number.isFinite(y)) pts.push(toGraph(g, {x, y: Math.max(r.y0, Math.min(r.y1, y))})); }
            if (pts.length > 1) { s += tint([{x: pts[0].x, y: y0}, ...pts, {x: pts[pts.length - 1].x, y: y0}]); const xm = (a1 + a2) / 2, ym = fn(xm), q = toGraph(g, {x: xm, y: Number.isFinite(ym) ? Math.max(r.y0, Math.min(r.y1, ym / 2)) : 0});
              s += lbl(`S = ${num(integrate(fn, Math.min(o.a1, o.a2), Math.max(o.a1, o.a2)) * (o.a2 < o.a1 ? -1 : 1))}`, q.x, q.y, 13, 'middle', '', {halo: true}); }
          }
        }
        for (const sg of segs) if (sg.length > 1) s += `<polyline points="${sg.map(p => `${f(p.x)},${f(p.y)}`).join(' ')}" fill="none" stroke="${col}" stroke-width="${f(['points', 'func', 'param', 'polar', 'ineq'].includes(o.kind) ? thick : lw * 0.9)}" stroke-linejoin="round"${st.round ? ' stroke-linecap="round"' : ''}${dash(o.kind === 'ineq' && (o.rel === 'lt' || o.rel === 'gt') ? 'dashed' : o.pattern)}/>` + hit('M' + sg.map(p => `${f(p.x)},${f(p.y)}`).join('L'));
        if (o.kind === 'func' && fn) {
          /* the tangent at x = tx */
          if (o.tangent && Number.isFinite(fn(o.tx))) {
            const y0 = fn(o.tx), m = derivative(fn, o.tx), bb = y0 - m * o.tx;
            let ta = r.x0, tb = r.x1;
            if (Math.abs(m) > 1e-12) { const u = (r.y0 - bb) / m, v = (r.y1 - bb) / m; ta = Math.max(ta, Math.min(u, v)); tb = Math.min(tb, Math.max(u, v)); }
            if (tb > ta && Number.isFinite(m)) { const A = toGraph(g, {x: ta, y: bb + m * ta}), B = toGraph(g, {x: tb, y: bb + m * tb}), q = toGraph(g, {x: o.tx, y: y0});
              s += `<line x1="${f(A.x)}" y1="${f(A.y)}" x2="${f(B.x)}" y2="${f(B.y)}" stroke="${st.accent && st.accent !== '#000' ? st.accent : ink}" stroke-width="${f(thin)}"${cap}/>` + `<circle cx="${f(q.x)}" cy="${f(q.y)}" r="${f(Math.max(2, st.dot * ss))}" fill="${ink}"/>`;
              s += lbl(`y = ${num(m)}x ${bb < 0 ? '−' : '+'} ${num(Math.abs(bb))}`, q.x + 8, q.y + 16, 12, 'start', '', {halo: true}); }
          }
          if (o.roots || o.extrema) {
            const ft = funcFeatures(fn, x0, x1);
            if (o.roots && r.y0 <= 0 && r.y1 >= 0) for (const x of ft.roots.slice(0, 12)) { const q = toGraph(g, {x, y: 0}); s += `<circle cx="${f(q.x)}" cy="${f(q.y)}" r="${f(Math.max(2.4, st.dot * ss * 1.1))}" fill="#fff" stroke="${col}" stroke-width="${f(thin * 1.2)}"/>`; if (ft.roots.length <= 6) s += lbl(num(x), q.x, q.y + 13, 11, 'middle', '', {halo: true}); }
            if (o.extrema) for (const e of ft.extrema.slice(0, 12)) { if (e.y < r.y0 || e.y > r.y1) continue; const q = toGraph(g, e); s += `<circle cx="${f(q.x)}" cy="${f(q.y)}" r="${f(Math.max(2.4, st.dot * ss * 1.1))}" fill="${col}"/>`; if (ft.extrema.length <= 6) s += lbl(`(${num(e.x)}, ${num(e.y)})`, q.x, q.y + (e.kind === 'max' ? -12 : 14), 11, 'middle', '', {halo: true}); }
          }
        }
        const main = segs.reduce((a, b) => b.length > a.length ? b : a, []);
        if (main.length > 1) {
          if (o.heads === 'mid') s += midHead(main, 0.5); else if (o.heads === 'end') { const a = main[main.length - 2], b = main[main.length - 1], l = Math.hypot(b.x - a.x, b.y - a.y) || 1; s += head(b, (b.x - a.x) / l, (b.y - a.y) / l)[0]; }
          if (o.label) { const e = main[main.length - 1]; s += lbl(o.label, e.x + 6, e.y - 10, 15, 'start', col !== ink ? ` fill="${col}"` : '', {halo: true}); }
        }
      }
    } else if (T === 'cycle') {
      const g = byId.get(o.graph); if (g && ranges.has(g.id)) {
        const c = gasCycle(o), all = c.legs.flatMap(l => l.pts.map(p => toGraph(g, p)));
        if (o.shade && all.length > 2) { const pg = `polygon points="${all.map(p => `${f(p.x)},${f(p.y)}`).join(' ')}"`; s += `<${pg} fill="${gray ? light : 'none'}" stroke="none"/>` + (gray ? '' : shade(pg, 'hatch')); }
        for (const l of c.legs) { const pts = l.pts.map(p => toGraph(g, p)); s += poly(pts, lw) + (o.arrows ? midHead(pts, 0.55) : ''); }
        const cen = {x: all.reduce((t, p) => t + p.x, 0) / all.length, y: all.reduce((t, p) => t + p.y, 0) / all.length};
        if (o.labels) {
          for (const st2 of c.states) { const p = toGraph(g, {x: st2.V, y: st2.P}), u = vec.unit(vec.sub(p, cen)); s += `<circle cx="${f(p.x)}" cy="${f(p.y)}" r="${f(st.dot * ss)}" fill="${ink}"/>` + lbl(st2.name, p.x + u.x * 13, p.y + u.y * 13, 15); }
          c.legs.forEach(l => { if (l.kind !== 'isotherm') return; const m = l.pts[Math.floor(l.pts.length / 2)], p = toGraph(g, m), u = vec.unit(vec.sub(p, cen)); s += lbl(l.from === 'A' ? 'T_H' : 'T_C', p.x + u.x * 18, p.y + u.y * 18, 14, 'middle', '', {halo: true}); });
        }
        s += hit('M' + all.map(p => `${f(p.x)},${f(p.y)}`).join('L'));
      }

    /* ── optics ── */
    } else if (T === 'lens') {
      const c = screen(o), h = o.h * S / 2, t = Math.min(16 * ss, Math.max(7 * ss, h * 0.16));
      const d = o.f > 0 ? `M${f(c.x)},${f(c.y - h)}Q${f(c.x + t * 2)},${f(c.y)} ${f(c.x)},${f(c.y + h)}Q${f(c.x - t * 2)},${f(c.y)} ${f(c.x)},${f(c.y - h)}Z`
        : `M${f(c.x - t)},${f(c.y - h)}H${f(c.x + t)}Q${f(c.x + t * 0.15)},${f(c.y)} ${f(c.x + t)},${f(c.y + h)}H${f(c.x - t)}Q${f(c.x - t * 0.15)},${f(c.y)} ${f(c.x - t)},${f(c.y - h)}Z`;
      s += `<path d="${d}" fill="${light}" stroke="${ink}" stroke-width="${f(thin * 1.1)}" stroke-linejoin="round"/>`;
      if (o.showF) for (const sg of [-1, 1]) { const q = screen({x: o.x + sg * Math.abs(o.f), y: o.y}); if (q.x > -50 && q.x < W + 50) s += `<circle cx="${f(q.x)}" cy="${f(q.y)}" r="${f(st.dot * ss)}" fill="${ink}"/>` + lbl(sg < 0 ? 'F' : "F'", q.x, q.y + 14, 14); }
      if (o.label) s += lbl(o.label, c.x, c.y - h - 12, 15);
      s += hitBox(c.x - t - 4, c.y - h, 2 * t + 8, 2 * h);
    } else if (T === 'mirror') {
      const c = screen(o), h = o.h * S / 2, back = o.face === 'left' ? 1 : -1;
      let d;
      if (!o.f) d = `M${f(c.x)},${f(c.y - h)}V${f(c.y + h)}`;
      else { const sag = Math.min(0.14 * h * 2, h * h / (4 * Math.abs(o.f) * S)), bend = (o.f > 0 ? -back : back) * sag; d = `M${f(c.x + bend)},${f(c.y - h)}Q${f(c.x - bend)},${f(c.y)} ${f(c.x + bend)},${f(c.y + h)}`; }
      if (o.half) { s += `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(thin)}"/><path d="${d}" transform="translate(${f(-back * 3 * ss)},0)" fill="none" stroke="${ink}" stroke-width="${f(thin)}"${dash('dashed', 0.6)}/>` + (o.label ? lbl(o.label, c.x, c.y - h - 12, 15) : '') + hitBox(c.x - 8, c.y - h, 16, 2 * h); }
      else {
      s += `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(lw * 1.2)}"/>`;
      /* hatching on the back: the curve is x = c.x + bend·τ², τ = (y − c.y)/h */
      const bend2 = o.f ? Math.min(0.14 * h * 2, h * h / (4 * Math.abs(o.f) * S)) * (o.f > 0 ? -back : back) : 0, N = Math.max(4, Math.floor(2 * h / st.hatchGap)); let hd = '';
      for (let i = 0; i <= N; i++) { const tt = -1 + 2 * i / N; hd += `M${f(c.x + bend2 * tt * tt)},${f(c.y + h * tt)}l${f(back * 7)},${f(5)}`; }
      s += `<path d="${hd}" stroke="${ink}" stroke-width="${f(st.hatchW * ss)}" fill="none"/>`;
      if (o.showF && o.f) { const pts = [[o.x - (o.face === 'left' ? 1 : -1) * o.f, 'F'], [o.x - (o.face === 'left' ? 1 : -1) * 2 * o.f, 'C']]; for (const [xx, t] of pts) { const q = screen({x: xx, y: o.y}); if (q.x > -50 && q.x < W + 50) s += `<circle cx="${f(q.x)}" cy="${f(q.y)}" r="${f(st.dot * ss)}" fill="${ink}"/>` + lbl(t, q.x, q.y + 14, 14); } }
      if (o.label) s += lbl(o.label, c.x, c.y - h - 12, 15);
      s += hitBox(c.x - 8, c.y - h, 16, 2 * h);
      }
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
      const drawTrace = t => { const q = t.pts.map(screen); let r = poly(q, thin * 1.15); if (o.arrow) for (let i = 0; i + 1 < q.length; i++) if (Math.hypot(q[i + 1].x - q[i].x, q[i + 1].y - q[i].y) > 18) r += midHead([q[i], q[i + 1]], 0.5, {len: HL * 0.8}); for (const fk of t.forks || []) r += drawTrace(fk); return r; };
      s += drawTrace(tr);
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
        for (let k = 1; k <= 4; k++) { const x = c.x - k * 16 * ss; s += line({x, y: c.y - h * 0.7}, {x, y: c.y + h * 0.7}, hair); }
        s += arrow({x: c.x - 82, y: c.y + h * 0.82}, {x: c.x - 18, y: c.y + h * 0.82}, {width: thin, head: HL * 0.8}) + lbl(`\\lambda = ${o.lambda}\\,\\mathrm{nm}`, c.x - 10, c.y + h * 0.82 + 14, 12, 'end', '', {halo: true});
        for (const sy of ys) for (let k = 1; k <= 3; k++) { const R = k * 22 * ss; s += `<path d="M${f(c.x + R * Math.cos(1.1))},${f(sy - R * Math.sin(1.1))}A${f(R)},${f(R)} 0 0 1 ${f(c.x + R * Math.cos(1.1))},${f(sy + R * Math.sin(1.1))}" fill="none" stroke="${ink}" stroke-width="${f(hair)}"${dash('dashed', 0.7)}/>`; }
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
        if (o.ticks) for (const t of clockTicks(o, ctEnd)) { const q = p(t.x, t.ct); s += `<circle cx="${f(q.x)}" cy="${f(q.y)}" r="${f(st.dot * ss)}" fill="${ink}"/>`; if (t.k <= 3) s += lbl(`\\tau = ${+(t.k * o.tau).toPrecision(3)}`, q.x + 7, q.y + 5, 11, 'start', '', {halo: true}); }
        if (o.label) s += lbl(o.label, b.x + 6, b.y - 4, 14, 'start', '', {halo: true});
      }
    } else if (T === 'frames') {
      const O = screen(o), L = o.size * S, O2 = {x: O.x + o.gap * S, y: O.y - 0.12 * S};
      for (const [c, pr, nm] of [[O, '', 'S'], [O2, "'", "S'"]]) s += arrow(c, {x: c.x + L, y: c.y}, {width: thin}) + arrow(c, {x: c.x, y: c.y - L}, {width: thin}) + lbl('x' + pr, c.x + L + 6, c.y + 2, 15, 'start') + lbl('y' + pr, c.x - 6, c.y - L - 6, 15, 'end') + lbl(`\\mathrm{${nm}}`, c.x - 10, c.y + 12, 15) + lbl('O' + pr, c.x + 2, c.y + 13, 12, 'start');
      s += arrow({x: O2.x + L * 0.2, y: O2.y - L * 0.55}, {x: O2.x + L * 0.85, y: O2.y - L * 0.55}, {width: lw}) + (o.label ? lbl(o.label, O2.x + L * 0.52, O2.y - L * 0.55 - 12, 15) : '');
      s += hitBox(O.x - 10, O2.y - L - 10, O2.x + L - O.x + 20, L + 30);

    /* ── added elements ── */
    } else if (T === 'wheel') {
      const p = opts.poses?.get?.(o.id) || poseOf(o), c = screen(p), r = Math.max(3, o.r * S), spin = (o.rot || 0) * Math.PI / 180 + (p.spin || 0);
      s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r)}" fill="${o.kind === 'sphere' || o.kind === 'shell' ? st.fill : st.fill}" stroke="${ink}" stroke-width="${f(lw)}"/>`;
      if (o.kind === 'ring' || o.kind === 'shell') s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r * 0.8)}" fill="none" stroke="${ink}" stroke-width="${f(thin)}"/>`;
      if (o.kind === 'sphere') s += `<ellipse cx="${f(c.x)}" cy="${f(c.y)}" rx="${f(r)}" ry="${f(r * 0.3)}" fill="none" stroke="${ink}" stroke-width="${f(hair)}"${dash('dashed', 0.6)}/>`;
      const nsp = o.spokes || (o.kind === 'wheel' ? 6 : (o.omega !== 'none' && p.spin !== undefined ? 1 : 0));
      if (nsp === 1) s += line(c, {x: c.x + Math.cos(spin) * r * 0.92, y: c.y - Math.sin(spin) * r * 0.92}, thin);
      for (let i = nsp === 1 ? 1 : 0; i < nsp; i++) { const a = spin + i * Math.PI / nsp; s += line({x: c.x + Math.cos(a) * r * 0.92, y: c.y - Math.sin(a) * r * 0.92}, {x: c.x - Math.cos(a) * r * 0.92, y: c.y + Math.sin(a) * r * 0.92}, hair); }
      if (o.kind === 'wheel') s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r * 0.86)}" fill="none" stroke="${ink}" stroke-width="${f(thin)}"/>`;
      s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(Math.max(1.4, st.dot * ss * 0.8))}" fill="${ink}"/>`;
      const showOmega = o.omega !== 'none' && (p.omega === undefined || Math.abs(p.omega) > 1e-5);
      if (showOmega) { const R = r * 1.28 + 4, a0 = 0.35, a1 = 2.4, ccw = p.omega === undefined ? o.omega === 'ccw' : p.omega > 0, d = `M${f(c.x + R * Math.cos(a0))},${f(c.y - R * Math.sin(a0))}A${f(R)},${f(R)} 0 0 0 ${f(c.x + R * Math.cos(a1))},${f(c.y - R * Math.sin(a1))}`;
        const ta = ccw ? a1 : a0, tip = {x: c.x + R * Math.cos(ta), y: c.y - R * Math.sin(ta)}, dir = ccw ? {x: -Math.sin(ta), y: -Math.cos(ta)} : {x: Math.sin(ta), y: Math.cos(ta)};
        s += `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(thin)}"/>` + head(tip, dir.x, dir.y, {len: HL * 0.9})[0] + lbl('\\omega', c.x, c.y - R - 9, 15); }
      if (o.label) s += r >= 13 * CUR.ls ? lbl(o.label, c.x, c.y + r * 0.45, Math.min(16, r * 0.6 / CUR.ls), 'middle', '', {name: true, halo: true}) : lbl(o.label, c.x + r + 5, c.y - r - 6, 15, 'start', '', {name: true});
    } else if (T === 'plank') {
      const a = o.rot * Math.PI / 180, u = {x: Math.cos(a), y: Math.sin(a)}, nn = {x: -u.y, y: u.x}, P = (s1, t) => screen({x: o.x + u.x * s1 + nn.x * t, y: o.y + u.y * s1 + nn.y * t}), L2 = o.len / 2, t2 = o.thick / 2;
      const pts = [P(-L2, -t2), P(L2, -t2), P(L2, t2), P(-L2, t2)];
      s += `<polygon points="${pts.map(q => `${f(q.x)},${f(q.y)}`).join(' ')}" fill="${st.gray ? st.light : '#fff'}" stroke="${ink}" stroke-width="${f(lw)}" stroke-linejoin="round"/>`;
      const sp = (o.at - 0.5) * o.len, q = P(sp, -t2), qc = P(sp, 0), pr = Math.max(2.4, st.dot * ss * 1.1);
      if (o.support === 'fulcrum') { const hh = Math.max(14, o.thick * S * 2.6), wb = hh * 0.62; s += `<path d="M${f(q.x)},${f(q.y)}L${f(q.x - wb)},${f(q.y + hh)}H${f(q.x + wb)}Z" fill="${st.fill}" stroke="${ink}" stroke-width="${f(lw)}" stroke-linejoin="round"/>` + line({x: q.x - wb * 1.6, y: q.y + hh}, {x: q.x + wb * 1.6, y: q.y + hh}) + (st.floor === 'line' ? '' : hatch(q.x - wb * 1.6, q.y + hh, q.x + wb * 1.6, q.y + hh, 0, 1)); }
      else if (o.support === 'pivot' || o.support === 'hinge') { s += `<circle cx="${f(qc.x)}" cy="${f(qc.y)}" r="${f(pr)}" fill="#fff" stroke="${ink}" stroke-width="${f(thin)}"/>`; if (o.support === 'hinge') s += line({x: qc.x - 13, y: qc.y + 16}, {x: qc.x + 13, y: qc.y + 16}) + hatch(qc.x - 13, qc.y + 16, qc.x + 13, qc.y + 16, 0, 1) + `<path d="M${f(qc.x - 7)},${f(qc.y + 16)}L${f(qc.x)},${f(qc.y)}L${f(qc.x + 7)},${f(qc.y + 16)}" fill="none" stroke="${ink}" stroke-width="${f(thin)}"/>`; }
      else if (o.support === 'wall') { const e = P(sp < 0 ? -L2 : L2, 0), side = sp < 0 ? -1 : 1, hw = Math.max(16, o.thick * S * 3); s += line({x: e.x, y: e.y - hw}, {x: e.x, y: e.y + hw}) + (st.wall === 'gray' ? strip({x: e.x, y: e.y - hw}, {x: e.x, y: e.y + hw}, side, 0) : hatch(e.x, e.y + hw, e.x, e.y - hw, side, 0)) + `<circle cx="${f(e.x)}" cy="${f(e.y)}" r="${f(pr)}" fill="#fff" stroke="${ink}" stroke-width="${f(thin)}"/>`; }
      if (o.label) { const m = P(0, t2); s += lbl(o.label, m.x, m.y - 11, 15, 'middle', '', {name: true, halo: true}); }
      s += hit(`M${f(P(-L2, 0).x)},${f(P(-L2, 0).y)}L${f(P(L2, 0).x)},${f(P(L2, 0).y)}`);
    } else if (T === 'track') {
      const c = screen(o), R = o.r * S, a0 = o.from * Math.PI / 180, a1 = o.to * Math.PI / 180, N = Math.max(12, Math.ceil(Math.abs(a1 - a0) * R / 6)), pts = [];
      for (let i = 0; i <= N; i++) { const t = a0 + (a1 - a0) * i / N; pts.push({x: c.x + R * Math.cos(t), y: c.y - R * Math.sin(t)}); }
      s += poly(pts, lw);
      if (o.hatch && st.floor !== 'line') { const k = Math.max(2, Math.floor(Math.abs(a1 - a0) * R / (st.hatchGap * ss))), hl = st.hatchLen * ss, sg = o.side === 'out' ? 1 : -1; let d = '';
        for (let i = 0; i <= k; i++) { const t = a0 + (a1 - a0) * i / k, q = {x: c.x + R * Math.cos(t), y: c.y - R * Math.sin(t)}, nr = {x: Math.cos(t) * sg, y: -Math.sin(t) * sg}, tg = {x: -Math.sin(t), y: -Math.cos(t)}; d += `M${f(q.x)},${f(q.y)}l${f(nr.x * hl + tg.x * hl * 0.7)},${f(nr.y * hl + tg.y * hl * 0.7)}`; }
        s += `<path d="${d}" stroke="${ink}" stroke-width="${f(Math.max(0.4, st.hatchW * ss * om))}" fill="none"/>`; }
      if (o.label) { const m = (a0 + a1) / 2; const rl = o.side === 'out' ? R - 16 : R + 16; s += lbl(o.label, c.x + rl * Math.cos(m), c.y - rl * Math.sin(m), 15, 'middle', '', {halo: true, name: true}); }
      s += hit('M' + pts.map(q => `${f(q.x)},${f(q.y)}`).join('L'));
    } else if (T === 'bridge') {
      const a = screen({x: o.x1, y: o.y1}), b = screen({x: o.x2, y: o.y2}), J = screen(bridgeJockey(o)), L = Math.hypot(b.x - a.x, b.y - a.y) || 1, u = {x: (b.x - a.x) / L, y: (b.y - a.y) / L}, nn = {x: u.y, y: -u.x};
      s += line(a, b, thick * 1.6);
      if (o.scale) { const off = 7 * ss; for (let i = 0; i <= 20; i++) { const q = {x: a.x + u.x * L * i / 20 - nn.x * off, y: a.y + u.y * L * i / 20 - nn.y * off}, tl = i % 10 === 0 ? 6 : i % 2 === 0 ? 4 : 2.5; s += line(q, {x: q.x - nn.x * tl * ss, y: q.y - nn.y * tl * ss}, hair); }
        for (const [i, t] of [[0, '0'], [10, o.kind === 'meter' ? '50' : ''], [20, o.kind === 'meter' ? '100\\,\\mathrm{cm}' : '']]) if (t) { const q = {x: a.x + u.x * L * i / 20 - nn.x * (off + 16 * ss), y: a.y + u.y * L * i / 20 - nn.y * (off + 16 * ss)}; s += lbl(`\\mathrm{${t}}`, q.x, q.y, 11); } }
      const top = {x: J.x + nn.x * 26 * ss, y: J.y + nn.y * 26 * ss};
      s += arrow(top, {x: J.x + nn.x * 1.5, y: J.y + nn.y * 1.5}, {width: thin * 1.2, head: HL * 0.9}) + `<circle cx="${f(top.x)}" cy="${f(top.y)}" r="${f(Math.max(1.5, st.dot * ss * 0.8))}" fill="${ink}"/>`;
      if (o.label) s += lbl(o.label, top.x + 8, top.y - 4, 15, 'start', '', {halo: true});
      s += hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`);
    } else if (T === 'transformer') {
      const c = screen(o), h = o.h * S, coil = (x0, n, sgn) => { const pitch = h * 0.8 / n, r = pitch / 2; let d = `M${f(x0)},${f(c.y - h * 0.4)}`; for (let i = 0; i < n; i++) d += `A${f(r * 1.2)},${f(r)} 0 0 ${sgn > 0 ? 1 : 0} ${f(x0)},${f(c.y - h * 0.4 + (i + 1) * pitch)}`; return d; };
      const xl = c.x - h * 0.2, xr = c.x + h * 0.2;
      s += `<path d="${coil(xl, Math.round(o.np), -1)}${coil(xr, Math.round(o.ns), 1)}" fill="none" stroke="${ink}" stroke-width="${f(lw)}"/>`;
      s += line({x: c.x - h * 0.05, y: c.y - h * 0.45}, {x: c.x - h * 0.05, y: c.y + h * 0.45}, thin) + line({x: c.x + h * 0.05, y: c.y - h * 0.45}, {x: c.x + h * 0.05, y: c.y + h * 0.45}, thin);
      for (const [x0, sg] of [[xl, -1], [xr, 1]]) s += line({x: x0, y: c.y - h * 0.4}, {x: x0 + sg * h * 0.3, y: c.y - h * 0.4}, thin) + line({x: x0, y: c.y + h * 0.4}, {x: x0 + sg * h * 0.3, y: c.y + h * 0.4}, thin);
      s += lbl('N_1', xl - h * 0.16, c.y, 14, 'end', '', {halo: true}) + lbl('N_2', xr + h * 0.16, c.y, 14, 'start', '', {halo: true}) + (o.label ? lbl(o.label, c.x, c.y + h * 0.5 + 12, 15) : '');
      s += hitBox(c.x - h * 0.5, c.y - h / 2, h, h);
    } else if (T === 'rails') {
      const p0 = screen({x: o.x, y: o.y}), p1 = screen({x: o.x + o.w, y: o.y}), q0 = screen({x: o.x, y: o.y + o.h}), q1 = screen({x: o.x + o.w, y: o.y + o.h}), rx = screen({x: o.x + Math.min(o.at, o.w), y: o.y}).x, H = p0.y - q0.y;
      if (o.field !== 'none') { const sp = Math.max(18, H / 3.2), r = Math.max(3, Math.min(6, sp * 0.16)) * ss; for (let x = p0.x + sp * 0.9; x < p1.x - sp * 0.3; x += sp) for (let y = q0.y + sp * 0.5; y < p0.y; y += sp) s += o.field === 'out' ? dotSym({x, y}, r) : crossSym({x, y}, r); s += lbl('\\vec{B}', p1.x + 8, q1.y + 2, 15, 'start'); }
      s += line(p0, p1, lw * 1.3) + line(q0, q1, lw * 1.3);
      /* the resistor across the left end */
      const zr = Math.min(H * 0.32, 22), m = (p0.y + q0.y) / 2; let d = `M${f(p0.x)},${f(p0.y)}V${f(m + zr)}`; for (let i = 0; i < 6; i++) d += `L${f(p0.x + (i % 2 ? -6 : 6) * ss)},${f(m + zr - zr * 2 * (2 * i + 1) / 12)}`; d += `L${f(p0.x)},${f(m - zr)}V${f(q0.y)}`;
      s += `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(thin * 1.1)}" stroke-linejoin="round"/>` + lbl('R', p0.x - 12, m, 15, 'end');
      const ext = 8 * ss; s += line({x: rx, y: p0.y + ext}, {x: rx, y: q0.y - ext}, Math.max(thick * 2.4, 3 * ss), ' stroke-linecap="round"');
      if (Math.abs(o.v) > 1e-12) { const dir = Math.sign(o.v), y = m; s += arrow({x: rx + dir * 6, y}, {x: rx + dir * (6 + 0.09 * W), y}, {width: lw * 1.1}) + lbl('\\vec{v}', rx + dir * (6 + 0.045 * W), y - 13, 15, 'middle', '', {halo: true}); }
      s += lbl('L', rx - 10, q0.y + H * 0.2, 15, 'end', '', {halo: true}) + (o.label ? lbl(o.label, (p0.x + p1.x) / 2, p0.y + 16, 15) : '');
      s += hitBox(p0.x - 10, q0.y - 10, p1.x - p0.x + 20, H + 20);
    } else if (T === 'container' || T === 'utube') {
      const p0 = screen({x: o.x, y: o.y + o.h}), w = o.w * S, h = o.h * S, bot = p0.y + h, W2 = lw * 1.3;
      const liquid = (shape) => o.fill === 'none' ? '' : o.fill === 'lines' || !st.gray ? (() => { const id = 'lq' + (++CLIP); return `<defs><pattern id="${id}" width="8" height="${f(5 * ss)}" patternUnits="userSpaceOnUse"><line x1="0" y1="1" x2="5" y2="1" stroke="${ink}" stroke-width="${f(hair)}"/></pattern></defs><${shape} fill="url(#${id})" stroke="none"/>`; })() : `<${shape} fill="${st.light}" stroke="none"/>`;
      if (T === 'container') {
        const ly = bot - o.level * h, shape = `rect x="${f(p0.x)}" y="${f(ly)}" width="${f(w)}" height="${f(bot - ly)}"`;
        s += liquid(shape) + line({x: p0.x, y: ly}, {x: p0.x + w, y: ly}, thin);
        s += `<path d="M${f(p0.x)},${f(p0.y)}V${f(bot)}H${f(p0.x + w)}V${f(p0.y)}${o.open ? '' : 'Z'}" fill="none" stroke="${ink}" stroke-width="${f(W2)}" stroke-linejoin="miter"/>`;
        const tx = p0.x + w * 0.8, tr = 5 * ss; s += `<path d="M${f(tx - tr)},${f(ly - tr * 1.6)}H${f(tx + tr)}L${f(tx)},${f(ly - 1)}Z" fill="none" stroke="${ink}" stroke-width="${f(hair)}"/>` + line({x: tx - tr * 0.6, y: ly + 3}, {x: tx + tr * 0.6, y: ly + 3}, hair);
        if (o.label) s += lbl(o.label, p0.x + w * 0.12, (ly + bot) / 2, 15, 'start', '', {halo: true});
      } else {
        const t = o.tube * S, yl = bot - t - o.left * (h - t), yr = bot - t - o.right * (h - t), x1 = p0.x, x2 = p0.x + w;
        s += liquid(`path d="M${f(x1)},${f(yl)}V${f(bot)}H${f(x2)}V${f(yr)}H${f(x2 - t)}V${f(bot - t)}H${f(x1 + t)}V${f(yl)}Z"`);
        s += line({x: x1, y: yl}, {x: x1 + t, y: yl}, thin) + line({x: x2 - t, y: yr}, {x: x2, y: yr}, thin);
        s += `<path d="M${f(x1)},${f(p0.y)}V${f(bot)}H${f(x2)}V${f(p0.y)}M${f(x1 + t)},${f(p0.y)}V${f(bot - t)}H${f(x2 - t)}V${f(p0.y)}" fill="none" stroke="${ink}" stroke-width="${f(W2)}"/>`;
        if (Math.abs(yl - yr) > 6) { const xm = (x1 + x2) / 2; s += line({x: x1 + t, y: yl}, {x: x2 - t, y: yl}, hair, dash('dashed', 0.7)) + line({x: x2 - t, y: yr}, {x: xm, y: yr}, hair, dash('dashed', 0.7)) + arrow({x: xm, y: (yl + yr) / 2}, {x: xm, y: yl}, {width: hair, head: HL * 0.7, kind: st.dimHead}) + arrow({x: xm, y: (yl + yr) / 2}, {x: xm, y: yr}, {width: hair, head: HL * 0.7, kind: st.dimHead}) + lbl('h', xm + 6, (yl + yr) / 2, 15, 'start', '', {halo: true}); }
        if (o.label) s += lbl(o.label, (x1 + x2) / 2, bot + 14, 15);
      }
      s += hitBox(p0.x, p0.y, w, h);
    } else if (T === 'thermometer') {
      const c = screen(o), h = o.h * S, r = Math.max(5, h * 0.07), tw = r * 0.9, top = c.y - h, ly = c.y - r - o.level * (h - r * 2);
      s += `<path d="M${f(c.x - tw / 2)},${f(c.y - r * 0.8)}V${f(top + tw / 2)}A${f(tw / 2)},${f(tw / 2)} 0 0 1 ${f(c.x + tw / 2)},${f(top + tw / 2)}V${f(c.y - r * 0.8)}" fill="#fff" stroke="${ink}" stroke-width="${f(thin)}"/>`;
      s += `<rect x="${f(c.x - tw * 0.2)}" y="${f(ly)}" width="${f(tw * 0.4)}" height="${f(c.y - ly)}" fill="${ink}"/><circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r)}" fill="${ink}" stroke="${ink}" stroke-width="${f(thin)}"/>`;
      for (let i = 1; i < 8; i++) { const y = c.y - r - i * (h - r * 2) / 8; s += line({x: c.x + tw / 2, y}, {x: c.x + tw / 2 + (i % 2 ? 3 : 6) * ss, y}, hair); }
      if (o.label) s += lbl(o.label, c.x + tw + 10, top + 8, 15, 'start');
      s += hitBox(c.x - r, top, 2 * r, h + r);
    } else if (T === 'heater') {
      const c = screen(o), w = o.w * S;
      if (o.kind === 'flame') { const fh = w * 0.42; s += `<rect x="${f(c.x - w * 0.22)}" y="${f(c.y)}" width="${f(w * 0.44)}" height="${f(w * 0.16)}" fill="${st.fill}" stroke="${ink}" stroke-width="${f(lw)}"/>` + `<path d="M${f(c.x)},${f(c.y - fh)}C${f(c.x + w * 0.2)},${f(c.y - fh * 0.5)} ${f(c.x + w * 0.16)},${f(c.y - 2)} ${f(c.x)},${f(c.y - 2)}C${f(c.x - w * 0.16)},${f(c.y - 2)} ${f(c.x - w * 0.2)},${f(c.y - fh * 0.5)} ${f(c.x)},${f(c.y - fh)}Z" fill="${st.gray ? st.light : '#fff'}" stroke="${ink}" stroke-width="${f(thin)}"/>` + `<path d="M${f(c.x)},${f(c.y - fh * 0.55)}C${f(c.x + w * 0.08)},${f(c.y - fh * 0.3)} ${f(c.x + w * 0.06)},${f(c.y - 4)} ${f(c.x)},${f(c.y - 4)}C${f(c.x - w * 0.06)},${f(c.y - 4)} ${f(c.x - w * 0.08)},${f(c.y - fh * 0.3)} ${f(c.x)},${f(c.y - fh * 0.55)}Z" fill="none" stroke="${ink}" stroke-width="${f(hair)}"/>`; }
      else if (o.kind === 'coil') { let d = `M${f(c.x - w / 2)},${f(c.y)}H${f(c.x - w * 0.3)}`; const n = 7; for (let i = 0; i <= n * 8; i++) { const t = i / (n * 8), a = t * n * 2 * Math.PI; d += `L${f(c.x - w * 0.3 + w * 0.6 * t + Math.sin(a) * w * 0.03)},${f(c.y - Math.sin(a) * w * 0.1 - (1 - Math.cos(a)) * w * 0.02)}`; } d += `H${f(c.x + w / 2)}`; s += `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(thin * 1.1)}"/>`; }
      else { s += `<rect x="${f(c.x - w / 2)}" y="${f(c.y)}" width="${f(w)}" height="${f(w * 0.14)}" fill="${st.gray || '#fff'}" stroke="${ink}" stroke-width="${f(lw)}"/>`; for (let k = -1; k <= 1; k++) { const x0 = c.x + k * w * 0.25; let d = `M${f(x0)},${f(c.y - 4)}`; for (let i = 1; i <= 12; i++) d += `L${f(x0 + Math.sin(i / 12 * 2 * Math.PI) * 3 * ss)},${f(c.y - 4 - i * w * 0.02)}`; s += `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(hair)}"/>`; } }
      if (o.label) s += lbl(o.label, c.x + w * 0.3 + 6, c.y + w * 0.05, 15, 'start');
      s += hitBox(c.x - w / 2, c.y - w * 0.45, w, w * 0.65);
    } else if (T === 'gasbox') {
      const p0 = screen({x: o.x, y: o.y + o.h}), w = o.w * S, h = o.h * S; let k = (o.seed * 7919) % 2147483647 || 1; const rnd = () => (k = (k * 16807) % 2147483647) / 2147483647;
      s += `<rect x="${f(p0.x)}" y="${f(p0.y)}" width="${f(w)}" height="${f(h)}" fill="none" stroke="${ink}" stroke-width="${f(lw * 1.2)}"/>`;
      const r = Math.max(2, st.dot * ss * 1.1), al = Math.min(w, h) * 0.12;
      for (let i = 0; i < Math.round(o.n); i++) { const x = p0.x + 8 + rnd() * (w - 16), y = p0.y + 8 + rnd() * (h - 16), a = rnd() * 2 * Math.PI, L = al * (0.5 + rnd());
        s += `<circle cx="${f(x)}" cy="${f(y)}" r="${f(r)}" fill="${ink}"/>`; if (o.arrows) s += arrow({x: x + Math.cos(a) * r, y: y + Math.sin(a) * r}, {x: x + Math.cos(a) * (r + L), y: y + Math.sin(a) * (r + L)}, {width: hair, head: HL * 0.65}); }
      if (o.label) s += lbl(o.label, p0.x + w / 2, p0.y + h + 14, 15);
      s += hitBox(p0.x, p0.y, w, h);
    } else if (T === 'screen') {
      const c = screen(o), h = o.h * S / 2;
      s += line({x: c.x, y: c.y - h}, {x: c.x, y: c.y + h}, Math.max(2, lw * 2)) + hatch(c.x + 1, c.y - h, c.x + 1, c.y + h, 1, 0) + (o.label ? lbl(o.label, c.x, c.y - h - 12, 15) : '') + hitBox(c.x - 6, c.y - h, 14, 2 * h);
    } else if (T === 'eye') {
      const c = screen(o), r = o.size * S / 2;
      s += `<path d="M${f(c.x - r)},${f(c.y)}Q${f(c.x)},${f(c.y - r * 0.95)} ${f(c.x + r * 0.55)},${f(c.y)}Q${f(c.x)},${f(c.y + r * 0.95)} ${f(c.x - r)},${f(c.y)}Z" fill="#fff" stroke="${ink}" stroke-width="${f(lw)}"/><circle cx="${f(c.x + r * 0.18)}" cy="${f(c.y)}" r="${f(r * 0.32)}" fill="${st.gray || '#fff'}" stroke="${ink}" stroke-width="${f(thin)}"/><circle cx="${f(c.x + r * 0.24)}" cy="${f(c.y)}" r="${f(r * 0.13)}" fill="${ink}"/>`;
      if (o.label) s += lbl(o.label, c.x - r * 0.2, c.y + r * 0.75 + 10, 15);
      s += hitBox(c.x - r, c.y - r / 2, 1.6 * r, r);
    } else if (T === 'source') {
      const c = screen(o), r = o.size * S / 2;
      if (o.kind === 'laser') { s += `<rect x="${f(c.x - r * 1.6)}" y="${f(c.y - r * 0.45)}" width="${f(r * 1.6)}" height="${f(r * 0.9)}" fill="${st.gray ? st.light : '#fff'}" stroke="${ink}" stroke-width="${f(lw)}"/>` + line({x: c.x, y: c.y - r * 0.18}, {x: c.x, y: c.y + r * 0.18}, lw * 1.6); }
      else { const rr = o.kind === 'point' ? Math.max(2.5, st.dot * ss * 1.2) : r * 0.45; s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(rr)}" fill="${o.kind === 'point' ? ink : '#fff'}" stroke="${ink}" stroke-width="${f(lw)}"/>`;
        if (o.kind === 'bulb') s += `<path d="M${f(c.x - rr * 0.4)},${f(c.y + rr * 0.3)}L${f(c.x - rr * 0.2)},${f(c.y - rr * 0.3)}L${f(c.x)},${f(c.y + rr * 0.3)}L${f(c.x + rr * 0.2)},${f(c.y - rr * 0.3)}L${f(c.x + rr * 0.4)},${f(c.y + rr * 0.3)}" fill="none" stroke="${ink}" stroke-width="${f(hair)}"/>`;
        const n = o.kind === 'sun' ? 12 : 8; for (let i = 0; i < n; i++) { const a = i * 2 * Math.PI / n; s += line({x: c.x + Math.cos(a) * (rr + 3), y: c.y + Math.sin(a) * (rr + 3)}, {x: c.x + Math.cos(a) * (rr + Math.max(6, r * 0.45)), y: c.y + Math.sin(a) * (rr + Math.max(6, r * 0.45))}, thin); } }
      if (o.label) s += lbl(o.label, c.x, c.y + r * 0.9 + 10, 15);
      s += hitBox(c.x - r * 1.6, c.y - r, r * 2.6, 2 * r);
    } else if (T === 'fiber') {
      const a = screen({x: o.x1, y: o.y1}), b = screen({x: o.x2, y: o.y2}), L = Math.hypot(b.x - a.x, b.y - a.y) || 1, u = {x: (b.x - a.x) / L, y: (b.y - a.y) / L}, nn = {x: -u.y, y: u.x}, r = o.r * S;
      const Pt = (s1, t) => ({x: a.x + u.x * s1 + nn.x * t, y: a.y + u.y * s1 + nn.y * t});
      s += line(Pt(0, -r), Pt(L, -r), lw) + line(Pt(0, r), Pt(L, r), lw) + line(Pt(0, -r * 1.7), Pt(L, -r * 1.7), hair) + line(Pt(0, r * 1.7), Pt(L, r * 1.7), hair);
      const th = o.angle * Math.PI / 180, step = 2 * r / Math.max(Math.tan(th), 1e-3), pts = [Pt(0, 0)]; let x = r / Math.max(Math.tan(th), 1e-3), side = 1;
      if (th > 0.01) { while (x < L) { pts.push(Pt(x, side * r)); side = -side; x += step; } const rem = L - (x - step); pts.push(Pt(L, -side * r + side * Math.min(2 * r, rem * Math.tan(th)))); } else pts.push(Pt(L, 0));
      s += poly(pts, thin) + midHead(pts.slice(0, 2), 0.6, {len: HL * 0.8}) + (o.label ? lbl(o.label, (a.x + b.x) / 2 + nn.x * (r * 1.7 + 12), (a.y + b.y) / 2 + nn.y * (r * 1.7 + 12), 15) : '') + hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`);
    } else if (T === 'pulse') {
      const x0 = screen({x: o.x, y: o.y}), x1 = screen({x: o.x + o.len, y: o.y}), cx = o.x + o.pos * o.len, hw = o.width / 2, pts = [];
      const yAt = x => { const dx = x - cx; return o.shape === 'gauss' ? o.A * Math.exp(-((dx / (hw * 0.55)) ** 2)) : o.shape === 'tri' ? (Math.abs(dx) < hw ? o.A * (1 - Math.abs(dx) / hw) : 0) : (Math.abs(dx) < hw ? o.A : 0); };
      if (o.shape === 'square') { for (const [xx, yy] of [[o.x, 0], [cx - hw, 0], [cx - hw, o.A], [cx + hw, o.A], [cx + hw, 0], [o.x + o.len, 0]]) pts.push(screen({x: Math.max(o.x, Math.min(o.x + o.len, xx)), y: o.y + yy})); }
      else for (let i = 0; i <= 300; i++) { const x = o.x + o.len * i / 300; pts.push(screen({x, y: o.y + yAt(x)})); }
      if (o.axis) s += line(x0, {x: x1.x, y: x1.y}, hair, dash('dotted'));
      s += poly(pts, lw);
      if (o.dir !== 'none') { const pc = screen({x: cx, y: o.y + o.A}), sg = o.dir === 'right' ? 1 : -1, y = pc.y - (o.A >= 0 ? 14 : -14); s += arrow({x: pc.x - sg * 0.05 * W, y}, {x: pc.x + sg * 0.06 * W, y}, {width: thin * 1.2}) + (o.label ? lbl(o.label, pc.x + sg * 0.08 * W, y - 4, 15, sg > 0 ? 'start' : 'end') : ''); }
      else if (o.label) { const pc = screen({x: cx, y: o.y + o.A}); s += lbl(o.label, pc.x, pc.y - 14, 15); }
      s += hit('M' + pts.map(q => `${f(q.x)},${f(q.y)}`).join('L'));
    } else if (T === 'interference') {
      const a = (o.rot || 0) * Math.PI / 180, u = {x: Math.cos(a), y: Math.sin(a)}, nn = {x: -u.y, y: u.x}, W2 = (s1, t) => screen({x: o.x + u.x * s1 + nn.x * t, y: o.y + u.y * s1 + nn.y * t});
      const c1 = W2(-o.d / 2, 0), c2 = W2(o.d / 2, 0), lam = o.lambda * S, R = o.n * o.lambda;
      for (const c of [c1, c2]) for (let k = 1; k <= o.n; k++) { s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(k * lam)}" fill="none" stroke="${ink}" stroke-width="${f(thin)}"/><circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f((k - 0.5) * lam)}" fill="none" stroke="${ink}" stroke-width="${f(hair)}"${dash('dashed', 0.6)}/>`; }
      if (o.nodal) { const cc = o.d / 2; for (let m = 0; (m + 0.5) * o.lambda < o.d; m++) for (const sg of [-1, 1]) { const A = (m + 0.5) * o.lambda / 2, Bq = Math.sqrt(Math.max(0, cc * cc - A * A)); if (Bq <= 0) continue; const pts = []; for (let i = -60; i <= 60; i++) { const t = i / 60 * 3, xs = sg * A * Math.cosh(t), ys = Bq * Math.sinh(t); if (Math.hypot(xs, ys) > R + o.d) continue; pts.push(W2(xs, ys)); } if (pts.length > 1) s += poly(pts, hair, dash('dotted')); } }
      for (const [c, t] of [[c1, 'S_1'], [c2, 'S_2']]) s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(Math.max(2, st.dot * ss))}" fill="${ink}"/>` + (o.labels ? lbl(t, c.x, c.y + 14, 14, 'middle', '', {halo: true}) : '');
      s += hitBox(Math.min(c1.x, c2.x) - 10, Math.min(c1.y, c2.y) - 10, Math.abs(c2.x - c1.x) + 20, Math.abs(c2.y - c1.y) + 20);
    } else if (T === 'nucleus') {
      const c = screen(o), R = o.r * S, N = Math.max(1, Math.round(o.np) + Math.round(o.nn)), rr = Math.max(2.5, R / Math.sqrt(N) * 0.95);
      let k = 7; const kinds = Array.from({length: N}, (_, i) => i < o.np); for (let i = N - 1; i > 0; i--) { k = (k * 16807) % 2147483647; const j = k % (i + 1); [kinds[i], kinds[j]] = [kinds[j], kinds[i]]; }
      for (let i = N - 1; i >= 0; i--) { const rad = (R - rr) * Math.sqrt((i + 0.5) / N), th = i * 2.39996; const x = c.x + rad * Math.cos(th), y = c.y + rad * Math.sin(th); s += `<circle cx="${f(x)}" cy="${f(y)}" r="${f(rr)}" fill="${kinds[i] ? st.gray || '#999' : '#fff'}" stroke="${ink}" stroke-width="${f(hair)}"/>`; }
      if (o.label) s += lbl(o.label, c.x + R + 6, c.y - R * 0.6, 15, 'start');
      s += hitBox(c.x - R, c.y - R, 2 * R, 2 * R);
    } else if (T === 'particle') {
      const c = screen(o), a = o.angle * Math.PI / 180, u = {x: Math.cos(a), y: -Math.sin(a)}, L = o.len * S;
      if (o.kind === 'photon') { const n = Math.max(3, Math.round(L / 9)), pts = []; for (let i = 0; i <= n * 10; i++) { const t = i / (n * 10), w = Math.sin(t * n * 2 * Math.PI) * 4.5 * ss * Math.min(1, t * 6, (1 - t) * 6 + 0.3); pts.push({x: c.x + u.x * L * 0.9 * t - u.y * w, y: c.y + u.y * L * 0.9 * t + u.x * w}); }
        s += poly(pts, thin) + (o.arrow ? head({x: c.x + u.x * L, y: c.y + u.y * L}, u.x, u.y, {len: HL})[0] : '') + lbl(o.label || '\\gamma', c.x + u.x * L * 0.5 + u.y * 14, c.y + u.y * L * 0.5 - u.x * 14 - 2, 15, 'middle', '', {halo: true}); }
      else {
        const r = Math.max(7, 9 * ss), sym = {electron: '−', positron: '+', proton: '+', neutron: '', alpha: '', neutrino: ''}[o.kind];
        if (o.arrow && L > 1) s += arrow({x: c.x + u.x * r, y: c.y + u.y * r}, {x: c.x + u.x * (r + L), y: c.y + u.y * (r + L)}, {width: thin * 1.2});
        if (o.kind === 'alpha') for (const [dx, dy, p] of [[-0.45, -0.45, 1], [0.45, -0.45, 0], [-0.45, 0.45, 0], [0.45, 0.45, 1]]) s += `<circle cx="${f(c.x + dx * r)}" cy="${f(c.y + dy * r)}" r="${f(r * 0.6)}" fill="${p ? st.gray || '#999' : '#fff'}" stroke="${ink}" stroke-width="${f(hair)}"/>`;
        else s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(o.kind === 'electron' || o.kind === 'positron' || o.kind === 'neutrino' ? r * 0.75 : r)}" fill="${o.kind === 'proton' ? st.gray || '#fff' : '#fff'}" stroke="${ink}" stroke-width="${f(thin)}"/>` + (sym ? lbl(`\\mathrm{${sym}}`, c.x, c.y, 12, 'middle', '', {raw: true}) : '');
        const def = {electron: 'e^-', positron: 'e^+', proton: 'p', neutron: 'n', alpha: '\\alpha', neutrino: '\\nu'}[o.kind];
        s += lbl(o.label || def, c.x - u.y * (r + 10) + (Math.abs(u.y) > 0.7 ? r + 6 : 0), c.y + u.x * (r + 10) * -1 + 0, 14, 'middle', '', {halo: true});
      }
      s += hitBox(c.x - 9, c.y - 9, 18, 18);
    } else if (T === 'panel') {
      const p0 = screen({x: o.x, y: o.y + o.h}), w = o.w * S, h = o.h * S;
      if (o.frame) s += `<rect x="${f(p0.x)}" y="${f(p0.y)}" width="${f(w)}" height="${f(h)}" fill="none" stroke="${ink}" stroke-width="${f(hair)}"/>`;
      if (o.caption) s += lbl(o.caption, p0.x + w / 2, p0.y + h + 15 * CUR.ls * 0.9, 16, 'middle', '', {caption: true});
      s += edit ? `<rect x="${f(p0.x)}" y="${f(p0.y)}" width="${f(w)}" height="${f(h)}" fill="none" stroke="#c5cde0" stroke-width="0.8" stroke-dasharray="3 3" pointer-events="none"/>${hitBox(p0.x + w / 2 - 30, p0.y + h, 60, 26 * CUR.ls)}` : '';
    } else if (T === 'brace') {
      const a = screen({x: o.x1, y: o.y1}), b = screen({x: o.x2, y: o.y2}), L = Math.hypot(b.x - a.x, b.y - a.y) || 1, u = {x: (b.x - a.x) / L, y: (b.y - a.y) / L}; let nn = {x: u.y, y: -u.x}; const off = o.offset * S; if (off < 0) nn = {x: -nn.x, y: -nn.y};
      const q = Math.max(7, 9 * ss), r = Math.min(q, L / 4), base = Math.abs(off) > 1 ? Math.abs(off) - q * 0.5 : 2, P2 = (s1, t) => `${f(a.x + u.x * s1 + nn.x * (base + t))},${f(a.y + u.y * s1 + nn.y * (base + t))}`;
      const d = o.kind === 'bracket' ? `M${P2(0, 0)}L${P2(0, q * 0.6)}L${P2(L, q * 0.6)}L${P2(L, 0)}` : `M${P2(0, 0)}Q${P2(0, q / 2)} ${P2(r, q / 2)}L${P2(L / 2 - r, q / 2)}Q${P2(L / 2, q / 2)} ${P2(L / 2, q)}Q${P2(L / 2, q / 2)} ${P2(L / 2 + r, q / 2)}L${P2(L - r, q / 2)}Q${P2(L, q / 2)} ${P2(L, 0)}`;
      s += `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(thin)}" stroke-linejoin="round"/>`;
      if (o.text) { const t = {x: a.x + u.x * L / 2 + nn.x * (base + q + 12), y: a.y + u.y * L / 2 + nn.y * (base + q + 12)}; s += lbl(o.text, t.x, t.y, 15, 'middle', '', {halo: true}); }
      s += hit(`M${P2(0, q / 2)}L${P2(L, q / 2)}`);
    } else if (T === 'callout') {
      const t = screen(o), q = screen({x: o.x2, y: o.y2}), bx = o.text ? texLayout(o.text, 15 * CUR.ls) : {w: 0};
      const from = {x: q.x + (t.x < q.x ? -bx.w / 2 - 3 : bx.w / 2 + 3), y: q.y};
      s += line(from, t, hair * 1.1) + (o.end === 'dot' ? `<circle cx="${f(t.x)}" cy="${f(t.y)}" r="${f(Math.max(1.5, st.dot * ss * 0.8))}" fill="${ink}"/>` : o.end === 'arrow' ? head(t, (t.x - from.x) / (Math.hypot(t.x - from.x, t.y - from.y) || 1), (t.y - from.y) / (Math.hypot(t.x - from.x, t.y - from.y) || 1), {len: HL * 0.85})[0] : '');
      if (o.text) s += lbl(o.text, q.x, q.y, 15, 'middle', '', {halo: true});
      s += hit(`M${f(from.x)},${f(from.y)}L${f(t.x)},${f(t.y)}`) + hitBox(q.x - bx.w / 2 - 4, q.y - 10, bx.w + 8, 20);
    } else if (T === 'parrows') {
      const a = screen({x: o.x1, y: o.y1}), b = screen({x: o.x2, y: o.y2}), L = Math.hypot(b.x - a.x, b.y - a.y) || 1, u = {x: (b.x - a.x) / L, y: (b.y - a.y) / L}, nn = {x: u.y, y: -u.x}, len = o.len * S, n = Math.round(o.n);
      for (let i = 0; i < n; i++) { const t = n === 1 ? 0.5 : i / (n - 1), p = {x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t}, q = {x: p.x + nn.x * len, y: p.y + nn.y * len}; s += o.dir === 'out' ? arrow(p, q, {width: thin * 1.15}) : arrow(q, p, {width: thin * 1.15}); }
      if (o.label) { const m = {x: (a.x + b.x) / 2 + nn.x * (len + 14), y: (a.y + b.y) / 2 + nn.y * (len + 14)}; s += lbl(o.label, m.x, m.y, 15, 'middle', '', {halo: true}); }
      s += hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`);

    /* ── marks ── */
    } else if (T === 'label') {
      const c = screen(o);
      if (o.box && o.text) { const b = texLayout(o.text, o.size * CUR.ls), pw = 6; s += `<rect x="${f(c.x - b.w / 2 - pw)}" y="${f(c.y - (b.a + b.d) / 2 - pw * 0.7)}" width="${f(b.w + 2 * pw)}" height="${f(b.a + b.d + pw * 1.4)}" fill="#fff" stroke="${ink}" stroke-width="${f(thin)}"/>`; }
      s += lbl(o.text || (edit ? '…' : ''), c.x, c.y, o.size, 'middle', o.color && o.color !== 'black' ? ` fill="${COLOR_HEX[o.color]}"` : '') + (edit ? `<rect x="${f(c.x - 14)}" y="${f(c.y - 12)}" width="28" height="24" fill="transparent"/>` : '');
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
      const ac = COLOR_HEX[o.color] || ink;
      s = `<path d="${d}" fill="none" stroke="${ac}" stroke-width="${f(hair * 1.2 * (o.text ? 1 : 1.25))}"${dash(o.pattern)}/>${o.arrow ? head(p1, -Math.sin(t1), -Math.cos(t1), {len: HL * 0.8, color: ac})[0] : ''}${o.text ? lbl(o.text, tm.x, tm.y, 15) : ''}${hit(d)}`;
    } else if (T === 'axes') {
      const c = screen(o), ex = {x: c.x + o.lx * S, y: c.y}, ey = {x: c.x, y: c.y - o.ly * S};
      s = (o.lx > 0 ? arrow(c, ex, {width: thin, head: HL * 0.9}) + lbl(o.xlabel, ex.x + 4, ex.y + 13, 15, 'start') : '') + (o.ly > 0 ? arrow(c, ey, {width: thin, head: HL * 0.9}) + lbl(o.ylabel, ey.x - 12, ey.y + 4, 15) : '')
        + hit(`M${f(ex.x)},${f(ex.y)}L${f(c.x)},${f(c.y)}L${f(ey.x)},${f(ey.y)}`);
    } else if (T === 'line') {
      const a = screen({x: o.x1, y: o.y1}), b = screen({x: o.x2, y: o.y2}), L = Math.hypot(b.x - a.x, b.y - a.y) || 1, u = {x: (b.x - a.x) / L, y: (b.y - a.y) / L};
      const lc = COLOR_HEX[o.color] || ink, lwd = o.pattern === 'solid' ? thin * 1.1 : hair * 1.05;
      if (o.pattern !== 'none') s += `<line x1="${f(a.x)}" y1="${f(a.y)}" x2="${f(b.x)}" y2="${f(b.y)}" stroke="${lc}" stroke-width="${f(lwd)}"${dash(o.pattern)}/>`;
      if (o.heads === 'end' || o.heads === 'both') s += head(b, u.x, u.y, {len: HL * 0.85, color: lc})[0];
      if (o.heads === 'start' || o.heads === 'both') s += head(a, -u.x, -u.y, {len: HL * 0.85, color: lc})[0];
      if (o.heads === 'mid') s += midHead([a, b], 0.5, {len: HL * 0.85, color: lc});
      s += hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`);
    } else if (T === 'vector') {
      const [a,b] = vectorPoints(scene, o, opts.poses).map(screen), L = Math.hypot(b.x - a.x, b.y - a.y) || 1, n = {x: -(b.y - a.y) / L, y: (b.x - a.x) / L};
      const vc = st.vecInk || ink;
      s += arrow(a, b, {width: o.width * ss, kind: o.head === 'auto' ? st.head : o.head, head: HL * Math.max(0.9, Math.sqrt(o.width / 1.6)), color: vc});
      if (o.label) { const side = n.y > 0 ? -1 : 1; s += lbl(o.label, (a.x + b.x) / 2 + side * n.x * 15, (a.y + b.y) / 2 + side * n.y * 15, 16, 'middle', st.vecInk ? ` fill="${vc}"` : '', {halo: true}); }
      s += hit(`M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`);
    } else if (T === 'region') {
      const p0 = screen({x: o.x, y: o.y + o.h}), w = o.w * S, h = o.h * S;
      const shape = o.shape === 'ellipse' ? `ellipse cx="${f(p0.x + w / 2)}" cy="${f(p0.y + h / 2)}" rx="${f(w / 2)}" ry="${f(h / 2)}"` : `rect x="${f(p0.x)}" y="${f(p0.y)}" width="${f(w)}" height="${f(h)}"`;
      if (o.fill === 'gray' && gray) s += `<${shape} fill="${light}" stroke="none"/>`; else if (o.fill === 'dark') s += `<${shape} fill="${gray ? st.dark : ink}" fill-opacity="${gray ? 1 : 0.55}" stroke="none"/>`; else if (o.fill === 'cross') s += shade(shape, 'hatch') + shade(shape, 'hatch2'); else s += shade(shape, o.fill === 'gray' ? 'hatch' : o.fill);
      if (o.pattern !== 'none') s += `<${shape} fill="none" stroke="${ink}" stroke-width="${f(thin)}"${dash(o.pattern)}/>`;
      if (o.label) s += lbl(o.label, p0.x + w * 0.5, p0.y + h * 0.3, 16, 'middle', '', {halo: true});
      s += hitBox(p0.x, p0.y, w, h);
    } else if (T === 'rect' || T === 'ellipse' || T === 'poly' || T === 'bezier') {
      const sc = COLOR_HEX[o.color] || ink, sw = thin * 1.15;
      let shapeAttr = '', open = null;
      if (T === 'rect') { const p0 = screen({x: o.x, y: o.y + o.h}), w = o.w * S, h = o.h * S, r = Math.min(o.r * S, w / 2, h / 2); shapeAttr = `rect x="${f(p0.x)}" y="${f(p0.y)}" width="${f(w)}" height="${f(h)}"${r > 0 ? ` rx="${f(r)}" ry="${f(r)}"` : ''}`; }
      else if (T === 'ellipse') { const p0 = screen({x: o.x, y: o.y + o.h}), w = o.w * S, h = o.h * S; shapeAttr = `ellipse cx="${f(p0.x + w / 2)}" cy="${f(p0.y + h / 2)}" rx="${f(w / 2)}" ry="${f(h / 2)}"`; }
      else if (T === 'poly') { const pts = o.pts.map(q => screen({x: q[0], y: q[1]})); shapeAttr = `path d="${o.smooth ? smoothPath(pts, o.closed) : 'M' + pts.map(q => `${f(q.x)},${f(q.y)}`).join('L') + (o.closed ? 'Z' : '')}"`; if (!o.closed) open = {a: pts[0], a2: pts[1], b: pts[pts.length - 1], b2: pts[pts.length - 2]}; }
      else { const P1 = screen({x: o.x1, y: o.y1}), C1 = screen({x: o.cx1, y: o.cy1}), C2 = screen({x: o.cx2, y: o.cy2}), P2 = screen({x: o.x2, y: o.y2}); shapeAttr = `path d="M${f(P1.x)},${f(P1.y)}C${f(C1.x)},${f(C1.y)} ${f(C2.x)},${f(C2.y)} ${f(P2.x)},${f(P2.y)}"`; open = {a: P1, a2: Math.hypot(C1.x - P1.x, C1.y - P1.y) > 1 ? C1 : C2, b: P2, b2: Math.hypot(C2.x - P2.x, C2.y - P2.y) > 1 ? C2 : C1}; }
      const closed = T === 'rect' || T === 'ellipse' || (T === 'poly' && o.closed);
      if (closed && o.fill && o.fill !== 'none') {
        if (FILL_HEX[o.fill]) s += `<${shapeAttr} fill="${FILL_HEX[o.fill]}" stroke="none"/>`;
        else if (o.fill === 'tint') s += `<${shapeAttr} fill="${sc}" fill-opacity="0.16" stroke="none"/>`;
        else if (o.fill === 'cross') s += shade(shapeAttr, 'hatch') + shade(shapeAttr, 'hatch2');
        else s += shade(shapeAttr, o.fill);
      }
      if (o.pattern !== 'none') s += `<${shapeAttr} fill="none" stroke="${sc}" stroke-width="${f(sw)}" stroke-linejoin="round" stroke-linecap="round"${dash(o.pattern)}/>`;
      if (open && o.heads && o.heads !== 'none') {
        const tip = (p, q) => { const L = Math.hypot(p.x - q.x, p.y - q.y) || 1; return head(p, (p.x - q.x) / L, (p.y - q.y) / L, {len: HL * 0.9, color: sc})[0]; };
        if (o.heads === 'end' || o.heads === 'both') s += tip(open.b, open.b2);
        if (o.heads === 'start' || o.heads === 'both') s += tip(open.a, open.a2);
      }
      if (edit) s += closed ? `<${shapeAttr} fill="transparent" stroke="transparent" stroke-width="12"/>` : `<${shapeAttr} fill="none" stroke="transparent" stroke-width="12" pointer-events="stroke"/>`;
    } else if (geo && GEO_TYPES.includes(T)) {
      s += drawGeo(o);
    } else if (T === 'joint') {
      s += drawJoint(o);
    } else if (T === 'nnet') {
      s += drawNet(o);
    } else if (T === 'fbox') {
      s += drawFbox(o);
    } else if (T === 'farrow') {
      s += drawFarrow(o);
    } else if (T === 'qpot') {
      s += drawQpot(o);
    } else if (T === 'point') {
      const c = screen(o), r = Math.max(1.5, st.dot * ss);
      s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r)}" fill="${o.filled ? ink : '#fff'}" stroke="${ink}" stroke-width="${f(thin)}"/>` + (o.label ? lbl(o.label, c.x + 6, c.y - 10, 15, 'start', '', {halo: true, point: true}) : '') + hitBox(c.x - 8, c.y - 8, 16, 16);
    }
    /* a velocity arrow of a body */
    if (isBody(o)) {
      const vNow = opts.velocities?.get?.(o.id), vx = vNow ? vNow.x : o.vx, vy = vNow ? vNow.y : o.vy;
      if (o.showV && Math.hypot(vx, vy) > 1e-6) {
        const p = screen(opts.poses?.get?.(o.id) || poseOf(o)), sp = Math.hypot(vx, vy), L = Math.max(0.35, Math.min(1.4, sp * 0.08)) * S, ux = vx / sp, uy = vy / sp;
        const tip = {x: p.x + ux * L, y: p.y - uy * L};
        s += arrow(p, tip, {width: thin * 1.25, head: HL}) + (o.vLabel ? lbl(o.vLabel, tip.x + ux * 10 - uy * 10, tip.y - uy * 10 - ux * 10, 15) : '');
      }
    }
    if (s && o.rot && ROT_WRAP.has(T)) { const c = screen(rotCentre(o)); s = `<g transform="rotate(${f(-o.rot)} ${f(c.x)} ${f(c.y)})">${s}</g>`; }
    /* a drawn shape given physics: its velocity (the start velocity while editing, dashed; the simulation's while it runs) */
    if (s && isPhysShape(o) && o.phys === 'dynamic') {
      const vNow = opts.rigidV?.get?.(o.id), v = vNow || (edit && !opts.poses ? {x: o.pvx, y: o.pvy} : null), sp = v ? Math.hypot(v.x, v.y) : 0;
      if (sp > 1e-6) {
        const p = opts.poses?.get?.(o.id) || (() => { const b = objectExtent(o); return b ? {x: b.x + b.w / 2, y: b.y + b.h / 2} : null; })();
        if (p) { const c = screen(p), L = Math.max(0.3, Math.min(1.4, sp * 0.12)) * S, ux = v.x / sp, uy = v.y / sp; s += arrow(c, {x: c.x + ux * L, y: c.y - uy * L}, {width: thin * 1.2, color: st.vecInk || st.accent || ink, pattern: vNow ? 'solid' : 'dashed'}); }
      }
    }
    if (s && showValues) s += valueMark(o);
    if (s) out.push(group(o, s));
  }
  if (st !== st0) setStyle(st0);
  om = 1; lw = B0.lw; thin = B0.thin; hair = B0.hair; thick = B0.thick; HL = B0.HL; CUR.ls = baseLs;
  CUR.letterStyle = CUR.letterFamily = undefined;

  /* circuit readings, the junction dots of the circuit */
  if (els.length) out.push(circuitMarks());
  /* the free-body diagram: every force on each body, from its centre, the longest arrow 90 px */
  if (opts.forces) {
    let max = 0;
    for (const list of opts.forces.values()) for (const x of list) max = Math.max(max, vec.len(x.v));
    const color = opts.forceColor || st.accent;
    /* every arrow reaches out of its body; its label goes beyond the tip, clear of the body's outline and of the other
       labels on the same body (moved sideways when two would meet) */
    for (const [id, list] of opts.forces) {
      const bo = byId.get(id), ext = bo && !isBody(bo) ? objectExtent(bo) : null;
      const rB = bo ? (isRound(bo) ? bo.r : isBody(bo) ? Math.hypot(bo.w, bo.h) / 2 : ext ? Math.hypot(ext.w, ext.h) / 2 : 0) * S : 0, placed = [];
      for (const x of list) {
        const m = vec.len(x.v); if (m < 1e-9 || !max) continue;
        const u = vec.unit(x.v), a = screen(x.at), text = FORCE_LABEL[x.kind] || '', b = texLayout(text, 14 * CUR.ls), hw = b.w / 2 + 3, hh = (b.a + b.d) / 2 + 2;
        const off = 6 + Math.abs(u.x) * hw + Math.abs(u.y) * hh;
        /* shortened (not below the body's edge) so the arrow and its label stay on the figure */
        let L = rB + Math.max(20, 80 * m / max);
        const room = Math.min(u.x > 1e-9 ? (W - 4 - a.x) / u.x : u.x < -1e-9 ? (a.x - 4) / -u.x : Infinity, -u.y > 1e-9 ? (H - 4 - a.y) / -u.y : -u.y < -1e-9 ? (a.y - 4) / u.y : Infinity) - off - Math.max(hw, hh);
        L = Math.max(rB + 14, Math.min(L, room));
        const tip = {x: a.x + u.x * L, y: a.y - u.y * L};
        let q = {x: tip.x + u.x * off, y: tip.y - u.y * off};
        const clash = p => placed.some(o => Math.abs(o.x - p.x) < (o.hw + hw) && Math.abs(o.y - p.y) < (o.hh + hh));
        for (let k = 1; k <= 6 && (clash(q) || Math.hypot(q.x - a.x, q.y - a.y) < rB + hw); k++) q = {x: tip.x + u.x * off - u.y * 14 * k * (k % 2 ? 1 : -1), y: tip.y - u.y * off - u.x * 14 * k * (k % 2 ? 1 : -1)};
        placed.push({...q, hw, hh});
        /* from the body's edge when the body is drawn large enough to carry its own label inside */
        const from = rB > 10 && bo?.label ? {x: a.x + u.x * rB * 0.95, y: a.y - u.y * rB * 0.95} : a;
        out.push(`<g class="fbd" data-body="${esc(id)}" data-kind="${x.kind}">${arrow(from, tip, {color, width: 2 * ss, head: HL, pattern: x.kind === 'centripetal' ? 'dashed' : 'solid'})}${lbl(text, q.x, q.y, 14, 'middle', ` fill="${color}"`, {halo: true})}</g>`);
      }
    }
  }
  if (edit && selSet.size) {
    for (const id of selSet) {
      const o = byId.get(id); if (!o) continue;
      const b = objectBox(scene, o, opts.poses); if (b) out.push(`<rect x="${f(X(b.x) - 5)}" y="${f(Y(b.y + b.h) - 5)}" width="${f(b.w * S + 10)}" height="${f(b.h * S + 10)}" fill="none" stroke="${o.lock ? '#9aa3b5' : '#3b6fd8'}" stroke-width="1.3" stroke-dasharray="5 3" pointer-events="none" class="selbox"/>`);
      if (id !== sel || o.lock) continue;
      if (('x1' in o && 'y2' in o) || o.type === 'callout') for (const k of [1, 2]) { const p = o.type === 'callout' ? screen(k === 1 ? {x: o.x, y: o.y} : {x: o.x2, y: o.y2}) : screen(o.type === 'vector' ? vectorPoints(scene, o, opts.poses)[k - 1] : {x: o['x' + k], y: o['y' + k]}); out.push(`<circle data-handle="${k}" cx="${f(p.x)}" cy="${f(p.y)}" r="7" fill="#fff" fill-opacity="0.85" stroke="#3b6fd8" stroke-width="1.6" class="handle"/>`); }
      const hd = (k, p, extra = '') => `<circle data-handle="${k}" cx="${f(p.x)}" cy="${f(p.y)}" r="6.5" fill="#fff" fill-opacity="0.9" stroke="#3b6fd8" stroke-width="1.6" class="handle"${extra}/>`;
      if (o.type === 'poly') o.pts.forEach((q, i) => out.push(hd('p' + i, screen({x: q[0], y: q[1]}))));
      if (o.type === 'bezier') for (const k of [1, 2]) { const a = screen({x: o['x' + k], y: o['y' + k]}), c = screen({x: o['cx' + k], y: o['cy' + k]}); out.push(`<line x1="${f(a.x)}" y1="${f(a.y)}" x2="${f(c.x)}" y2="${f(c.y)}" stroke="#3b6fd8" stroke-width="1" stroke-dasharray="3 2" pointer-events="none"/>` + hd('c' + k, c, ' data-ctrl="1"')); }
      if (['rect', 'ellipse', 'region', 'qpot', 'graph', 'panel'].includes(o.type) && !o.rot) out.push(hd('wh', screen({x: o.x + o.w, y: o.y + o.h})));
      if (o.type === 'arc') { const t = o.to * Math.PI / 180; out.push(hd('r', screen({x: o.x + o.r * Math.cos(t), y: o.y + o.r * Math.sin(t)}))); }
      /* the turning handle above a turnable object */
      if ('rot' in o && b && !(isBody(o) && o.on)) { const cx = X(b.x + b.w / 2), top = Y(b.y + b.h) - 5; out.push(`<line x1="${f(cx)}" y1="${f(top)}" x2="${f(cx)}" y2="${f(top - 22)}" stroke="#3b6fd8" stroke-width="1.2" pointer-events="none"/><circle data-rot="1" cx="${f(cx)}" cy="${f(top - 26)}" r="7" fill="#fff" stroke="#3b6fd8" stroke-width="1.6" class="handle rot"/><path d="M${f(cx - 3.5)},${f(top - 28)}a3.6,3.6 0 1 1 1,3" fill="none" stroke="#3b6fd8" stroke-width="1.1" pointer-events="none"/>`); }
    }
  }
  if (edit && opts.marquee) { const m = opts.marquee; out.push(`<rect x="${f(Math.min(X(m.x0), X(m.x1)))}" y="${f(Math.min(Y(m.y0), Y(m.y1)))}" width="${f(Math.abs(X(m.x1) - X(m.x0)))}" height="${f(Math.abs(Y(m.y1) - Y(m.y0)))}" fill="#3b6fd8" fill-opacity="0.08" stroke="#3b6fd8" stroke-width="1" stroke-dasharray="4 3" pointer-events="none" class="marquee"/>`); }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" font-family="${esc(st.font).replace(/&#39;/g, "'")}">${opts.title ? `<title>${esc(opts.title)}</title>` : ''}${out.join('')}</svg>`;

  /* ── the geometric construction (computeGeometry): points, segments, lines and rays, circles, polygons, angles ── */
  function drawGeo(o) {
    const G = geo.get(o.id); if (!G) return '';
    const col = o.color && o.color !== 'black' ? COLOR_HEX[o.color] : ink, num = v => (+v.toFixed(2)).toString().replace('-', '−');
    let s = '';
    const fillShape = (shapeAttr, kind) => {
      if (!kind || kind === 'none') return '';
      if (FILL_HEX[kind]) return `<${shapeAttr} fill="${FILL_HEX[kind]}" stroke="none"/>`;
      if (kind === 'tint') return gray ? `<${shapeAttr} fill="${col}" fill-opacity="0.14" stroke="none"/>` : shade(shapeAttr, 'hatch');
      if (kind === 'cross') return shade(shapeAttr, 'hatch') + shade(shapeAttr, 'hatch2');
      return shade(shapeAttr, kind);
    };
    if (G.k === 'pt') {
      if (!o.show && !edit) return '';
      const c = screen(G), r = Math.max(2, st.dot * ss * 1.05);
      if (edit && o.kind === 'free') s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r + 4)}" fill="#3b6fd8" fill-opacity="0.16" stroke="none" class="free"/>`;
      if (edit && o.kind === 'on') s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r + 4)}" fill="none" stroke="#3b6fd8" stroke-opacity="0.5" stroke-width="1"/>`;
      s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r)}" fill="${col}"${!o.show ? ' fill-opacity="0.35"' : ''}/>`;
      if (o.label) s += lbl(o.label, c.x + 7, c.y - 10, 15, 'start', '', {halo: true, point: true});
      return s + hitBox(c.x - 9, c.y - 9, 18, 18);
    }
    if (G.k === 'line') {
      /* the part inside the view (Liang–Barsky) */
      let t0 = G.t0, t1 = G.t1;
      for (const [p, d, lo, hi] of [[G.p.x, G.d.x, view.x, view.x + view.w], [G.p.y, G.d.y, view.y, view.y + view.h]]) {
        if (Math.abs(d) < 1e-15) { if (p < lo || p > hi) return ''; continue; }
        const a = (lo - p) / d, b = (hi - p) / d; t0 = Math.max(t0, Math.min(a, b)); t1 = Math.min(t1, Math.max(a, b));
      }
      if (!(t1 > t0)) return '';
      const a = screen(geoLinePoint(G, t0)), b = screen(geoLinePoint(G, t1)), d = `M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`;
      s += `<path d="${d}" fill="none" stroke="${col}" stroke-width="${f(thin * 1.15)}"${cap}${dash(o.pattern)}/>`;
      const P = byId.get(o.a), Q = o.kind === 'perp' || o.kind === 'par' ? null : byId.get(o.b);
      const pa = geo.get(P?.id), pb = Q ? geo.get(Q.id) : null;
      if ((o.measure || o.label) && pa) {
        const m = pb ? screen({x: (pa.x + pb.x) / 2, y: (pa.y + pb.y) / 2}) : screen(geoLinePoint(G, Math.max(t0, Math.min(t1, 1)))), L = Math.hypot(b.x - a.x, b.y - a.y) || 1;
        /* below the segment (its points' labels sit above and to the right) */
        let nx = -(b.y - a.y) / L, ny = (b.x - a.x) / L; if (ny < 0) { nx = -nx; ny = -ny; }
        const val = pb ? Math.hypot(pb.x - pa.x, pb.y - pa.y) : null, text = o.measure && val != null ? (o.label ? `${o.label} = ${num(val)}` : num(val)) : o.label;
        s += lbl(text, m.x + nx * 13, m.y + ny * 13, 14, 'middle', '', {halo: true});
      }
      return s + hit(d);
    }
    if (G.k === 'circ') {
      const c = screen(G.c), r = G.r * S, shapeAttr = `circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(r)}"`;
      s += fillShape(shapeAttr, o.fill) + `<${shapeAttr} fill="none" stroke="${col}" stroke-width="${f(thin * 1.15)}"${dash(o.pattern)}/>`;
      if (o.measure || o.label) s += lbl(o.measure ? `${o.label || 'r'} = ${num(G.r)}` : o.label, c.x + r * 0.72 + 6, c.y - r * 0.72 - 6, 14, 'start', '', {halo: true});
      return s + (edit ? `<${shapeAttr} fill="none" stroke="transparent" stroke-width="12" pointer-events="stroke"/>` : '');
    }
    if (G.k === 'poly') {
      const pts = G.pts.map(screen), shapeAttr = `path d="M${pts.map(p => `${f(p.x)},${f(p.y)}`).join('L')}Z"`;
      s += fillShape(shapeAttr, o.fill) + `<${shapeAttr} fill="none" stroke="${col}" stroke-width="${f(thin * 1.15)}" stroke-linejoin="round"${dash(o.pattern)}/>`;
      if (o.measure || o.label) { const cx = pts.reduce((t, p) => t + p.x, 0) / pts.length, cy = pts.reduce((t, p) => t + p.y, 0) / pts.length; s += lbl(o.measure ? `${o.label ? o.label + ' = ' : ''}${num(polyArea(G.pts))}` : o.label, cx, cy, 14, 'middle', '', {halo: true}); }
      return s + (edit ? `<${shapeAttr} fill="transparent" stroke="none"/>` : '');
    }
    if (G.k === 'ang') {
      const b = G.b, aA = Math.atan2(G.a.y - b.y, G.a.x - b.x), small = G.deg <= 180, start = small ? aA : Math.atan2(G.c.y - b.y, G.c.x - b.x), sweep = (small ? G.deg : 360 - G.deg) * Math.PI / 180, val = small ? G.deg : 360 - G.deg;
      const at = t => screen({x: b.x + o.r * Math.cos(t), y: b.y + o.r * Math.sin(t)});
      if (Math.abs(val - 90) < 0.05) { const u = {x: Math.cos(start), y: Math.sin(start)}, v = {x: Math.cos(start + sweep), y: Math.sin(start + sweep)}, k = o.r * 0.6;
        const p1 = screen({x: b.x + u.x * k, y: b.y + u.y * k}), p2 = screen({x: b.x + (u.x + v.x) * k, y: b.y + (u.y + v.y) * k}), p3 = screen({x: b.x + v.x * k, y: b.y + v.y * k});
        s += `<path d="M${f(p1.x)},${f(p1.y)}L${f(p2.x)},${f(p2.y)}L${f(p3.x)},${f(p3.y)}" fill="none" stroke="${ink}" stroke-width="${f(hair * 1.2)}"/>`; }
      else { const pts = []; for (let i = 0; i <= 24; i++) pts.push(at(start + sweep * i / 24)); s += `<path d="M${pts.map(p => `${f(p.x)},${f(p.y)}`).join('L')}" fill="none" stroke="${ink}" stroke-width="${f(hair * 1.2)}"/>`; }
      const mid = start + sweep / 2, lp = screen({x: b.x + o.r * Math.cos(mid), y: b.y + o.r * Math.sin(mid)}), c = screen(b), ux = (lp.x - c.x) / (o.r * S || 1), uy = (lp.y - c.y) / (o.r * S || 1);
      const text = o.measure ? `${o.label ? o.label + ' = ' : ''}${val.toFixed(1)}^\\circ` : o.label;
      if (text) s += lbl(text, lp.x + ux * 16, lp.y + uy * 12, 13, 'middle', '', {halo: true});
      return s + hitBox(lp.x - 10, lp.y - 10, 20, 20);
    }
    return '';
  }
  /* ── a neural network: layers left to right, every node joined to every node of the next layer; with weights the
     edges are as thick as |w| (or blue for w > 0, red for w < 0), w_ij written on them when asked; bias nodes (+1, dashed)
     on top of every layer but the last ── */
  function drawNet(o) {
    const L = nnLayers(o.layers); if (!L) return '';
    const W8 = o.weights ? nnWeights(o.weights, L) : null, wmax = W8 ? Math.max(1e-12, ...W8.flat(2).filter(v => v != null).map(Math.abs)) : 1;
    const p0 = screen({x: o.x, y: o.y + o.h}), w = o.w * S, h = o.h * S, r = Math.max(4, o.nodeR * S), nmax = Math.max(...L.map((n, l) => n + (o.bias && l < L.length - 1 ? 1 : 0)));
    const gap = Math.min(h / Math.max(1, nmax), r * 3.4), col = l => p0.x + r + (w - 2 * r) * l / (L.length - 1);
    const pos = (l, i, n) => ({x: col(l), y: p0.y + h / 2 + (i - (n - 1) / 2) * gap});
    const nodes = L.map((n, l) => { const nb = o.bias && l < L.length - 1 ? 1 : 0, tot = n + nb; return Array.from({length: tot}, (_, i) => ({...pos(l, i, tot), bias: nb && i === 0})); });
    const inL = String(o.inLabels || '').split(',').map(t => t.trim()), outL = String(o.outLabels || '').split(',').map(t => t.trim());
    let s = '', lab = '';
    const pos2 = '#1d4ed8', neg = '#c0262d';
    for (let l = 0; l + 1 < L.length; l++) {
      const A = nodes[l], B = nodes[l + 1].filter(q => !q.bias), many = A.length * B.length;
      A.forEach((a, ii) => B.forEach((b, j) => {
        const i = a.bias ? -1 : ii - (A[0].bias ? 1 : 0), wv = !a.bias && W8 ? W8[l][i]?.[j] : null;
        const dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 1, ux = dx / d, uy = dy / d, A2 = {x: a.x + ux * r, y: a.y + uy * r}, B2 = {x: b.x - ux * r, y: b.y - uy * r};
        const width = wv != null && o.wstyle === 'width' ? hair + (thick * 2.2 - hair) * Math.abs(wv) / wmax : hair;
        const color = wv != null && o.wstyle === 'color' ? (wv >= 0 ? pos2 : neg) : wv != null && o.wstyle === 'width' && wv < 0 ? st.dark || '#666' : ink;
        const op = wv != null && o.wstyle === 'color' ? ` stroke-opacity="${f(0.35 + 0.65 * Math.abs(wv) / wmax)}"` : '';
        s += `<line x1="${f(A2.x)}" y1="${f(A2.y)}" x2="${f(B2.x)}" y2="${f(B2.y)}" stroke="${color}" stroke-width="${f(width)}"${op}${a.bias ? dash('dashed', 0.7) : ''}/>`;
        if (o.wlabels && !a.bias && many <= 24) { const q = {x: A2.x + (B2.x - A2.x) * 0.3, y: A2.y + (B2.y - A2.y) * 0.3}; lab += lbl(wv != null ? `${+wv.toPrecision(3)}`.replace('-', '−') : `w_{${i + 1}${j + 1}}`, q.x, q.y - 6, 10, 'middle', '', {halo: true}); }
        if (o.wlabels && !a.bias && many > 24 && ii === 0 && j === 0) lab += lbl(`W^{(${l + 1})}`, (a.x + b.x) / 2, p0.y - 4, 13, 'middle', '', {halo: true});
      }));
    }
    nodes.forEach((list, l) => list.forEach((q, i) => {
      const hidden = l > 0 && l < L.length - 1;
      s += `<circle cx="${f(q.x)}" cy="${f(q.y)}" r="${f(r)}" fill="${q.bias ? '#fff' : l === 0 ? fill : hidden ? (gray ? light : '#fff') : fill}" stroke="${ink}" stroke-width="${f(thin * 1.1)}"${q.bias ? dash('dashed', 0.8) : ''}/>`;
      if (q.bias) s += lbl('+1', q.x, q.y, Math.min(13, r * 0.9 / CUR.ls), 'middle');
      else if (hidden && o.act && r >= 7) s += lbl(o.act, q.x, q.y, Math.min(14, r * 0.95 / CUR.ls), 'middle');
      const k = i - (list[0].bias ? 1 : 0);
      if (l === 0 && !q.bias && inL[k]) s += lbl(inL[k], q.x - r - 6, q.y, 15, 'end');
      if (l === L.length - 1 && outL[k]) s += lbl(outL[k], q.x + r + 6, q.y, 15, 'start');
    }));
    if (o.label) s += lbl(o.label, p0.x + w / 2, p0.y + h + 14, 15);
    return s + lab + hitBox(p0.x, p0.y, w, h);
  }
  /* ── a block diagram: a box (rectangle, rounded, circle, diamond, or a summing junction ⊗) with its text, and an arrow
     from one box's edge to another's, straight or with one bend ── */
  function fboxEdge(b, toward) {
    const dx = toward.x - b.x, dy = toward.y - b.y, hw = b.w / 2, hh = b.h / 2;
    if (Math.abs(dx) < 1e-12 && Math.abs(dy) < 1e-12) return {x: b.x, y: b.y};
    let k;
    if (b.shape === 'circle' || b.shape === 'sum') { const rr = Math.min(hw, hh); k = rr / Math.hypot(dx, dy); }
    else if (b.shape === 'diamond') k = 1 / (Math.abs(dx) / hw + Math.abs(dy) / hh);
    else k = Math.min(Math.abs(dx) > 1e-12 ? hw / Math.abs(dx) : Infinity, Math.abs(dy) > 1e-12 ? hh / Math.abs(dy) : Infinity);
    return {x: b.x + dx * k, y: b.y + dy * k};
  }
  function drawFbox(o) {
    const c = screen(o), w = o.w * S, h = o.h * S, col = ink;
    let shapeAttr;
    if (o.shape === 'circle' || o.shape === 'sum') shapeAttr = `circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(Math.min(w, h) / 2)}"`;
    else if (o.shape === 'diamond') shapeAttr = `path d="M${f(c.x)},${f(c.y - h / 2)}L${f(c.x + w / 2)},${f(c.y)}L${f(c.x)},${f(c.y + h / 2)}L${f(c.x - w / 2)},${f(c.y)}Z"`;
    else shapeAttr = `rect x="${f(c.x - w / 2)}" y="${f(c.y - h / 2)}" width="${f(w)}" height="${f(h)}"${o.shape === 'round' ? ` rx="${f(Math.min(w, h) * 0.22)}"` : ''}`;
    let s = '';
    if (o.fill && o.fill !== 'none') s += FILL_HEX[o.fill] ? `<${shapeAttr} fill="${FILL_HEX[o.fill]}" stroke="none"/>` : o.fill === 'tint' ? `<${shapeAttr} fill="${st.vecInk || '#1d4ed8'}" fill-opacity="0.12" stroke="none"/>` : shade(shapeAttr, o.fill === 'cross' ? 'hatch' : o.fill);
    s += `<${shapeAttr} fill="${o.fill && o.fill !== 'none' ? 'none' : '#fff'}" stroke="${col}" stroke-width="${f(lw)}" stroke-linejoin="round"/>`;
    if (o.shape === 'sum') { const rr = Math.min(w, h) / 2 * 0.707; s += `<path d="M${f(c.x - rr)},${f(c.y - rr)}L${f(c.x + rr)},${f(c.y + rr)}M${f(c.x + rr)},${f(c.y - rr)}L${f(c.x - rr)},${f(c.y + rr)}" stroke="${col}" stroke-width="${f(thin)}"/>`; }
    if (o.text) s += o.shape === 'sum' ? lbl(o.text, c.x + w / 2 + 4, c.y - h / 2 - 4, 13, 'start') : lbl(o.text, c.x, c.y, Math.min(16, h * 0.5 / CUR.ls), 'middle');
    return s + hitBox(c.x - w / 2, c.y - h / 2, w, h);
  }
  function drawFarrow(o) {
    const A = byId.get(o.a), B = byId.get(o.b); if (!A || !B) return '';
    let pts;
    if (o.route === 'hv' || o.route === 'vh') {
      const corner = o.route === 'hv' ? {x: B.x, y: A.y} : {x: A.x, y: B.y};
      pts = [fboxEdge(A, corner), corner, fboxEdge(B, corner)];
    } else pts = [fboxEdge(A, B), fboxEdge(B, A)];
    const sp = pts.map(screen), d = 'M' + sp.map(p => `${f(p.x)},${f(p.y)}`).join('L');
    const last = sp[sp.length - 1], prev = sp[sp.length - 2], L = Math.hypot(last.x - prev.x, last.y - prev.y) || 1;
    const [hs, end] = head(last, (last.x - prev.x) / L, (last.y - prev.y) / L, {len: HL});
    const body = [...sp.slice(0, -1), end];
    let s = `<polyline points="${body.map(p => `${f(p.x)},${f(p.y)}`).join(' ')}" fill="none" stroke="${ink}" stroke-width="${f(thin * 1.2)}" stroke-linejoin="round"${dash(o.pattern)}/>` + hs;
    const m = sp.length === 3 ? sp[1] : {x: (sp[0].x + last.x) / 2, y: (sp[0].y + last.y) / 2}, seg = sp.length === 3 ? [sp[1], sp[2]] : [sp[0], last], ux = seg[1].x - seg[0].x, uy = seg[1].y - seg[0].y, ul = Math.hypot(ux, uy) || 1;
    let nx = -uy / ul, ny = ux / ul; if (ny > 0) { nx = -nx; ny = -ny; }
    if (o.label) s += lbl(o.label, (sp.length === 3 ? (sp[1].x + last.x) / 2 : m.x) + nx * 12, (sp.length === 3 ? (sp[1].y + last.y) / 2 : m.y) + ny * 12, 14, 'middle', '', {halo: true});
    if (o.sign) s += lbl(o.sign === '-' ? '−' : o.sign, last.x - (last.x - prev.x) / L * 12 + nx * 10, last.y - (last.y - prev.y) / L * 12 + ny * 10, 13, 'middle');
    return s + hit(d);
  }
  /* ── a joint between drawn shapes given physics: a spring, a rod or a string (to a fixed point: a small pivot) ── */
  function drawJoint(o) {
    const e = opts.jointEnds?.get?.(o.id) || jointEnds(scene, o); if (!e) return '';
    const a = screen(e.a), b = screen(e.b), L = Math.hypot(b.x - a.x, b.y - a.y); let s = '';
    if (L < 1) return '';
    const ux = (b.x - a.x) / L, uy = (b.y - a.y) / L, d0 = `M${f(a.x)},${f(a.y)}L${f(b.x)},${f(b.y)}`;
    if (o.kind === 'spring') {
      const lead = Math.min(12 * ss, L * 0.15), n = Math.round(o.coils) * 2, amp = 6 * ss, seg = (L - 2 * lead) / n;
      let d = `M${f(a.x)},${f(a.y)}l${f(ux * lead)},${f(uy * lead)}`;
      for (let i = 0; i < n; i++) { const t = lead + seg * (i + 0.5), side = i % 2 ? -1 : 1; d += `L${f(a.x + ux * t - uy * amp * side)},${f(a.y + uy * t + ux * amp * side)}`; }
      d += `L${f(b.x - ux * lead)},${f(b.y - uy * lead)}L${f(b.x)},${f(b.y)}`;
      s += `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(thin * 1.15)}" stroke-linejoin="round"/>`;
    } else s += line(a, b, o.kind === 'rod' ? Math.max(thick * 2, 2 * ss) : thin, o.kind === 'rod' ? ' stroke-linecap="round"' : '');
    for (const p of [a, ...(e.fixed ? [] : [b])]) s += `<circle cx="${f(p.x)}" cy="${f(p.y)}" r="${f(Math.max(1.6, st.dot * ss * 0.8))}" fill="${ink}"/>`;
    if (e.fixed) s += line({x: b.x - 11, y: b.y - 6}, {x: b.x + 11, y: b.y - 6}) + hatch(b.x - 11, b.y - 6, b.x + 11, b.y - 6, 0, -1) + line({x: b.x, y: b.y - 6}, b, thin) + `<circle cx="${f(b.x)}" cy="${f(b.y)}" r="${f(Math.max(2, st.dot * ss))}" fill="#fff" stroke="${ink}" stroke-width="${f(thin)}"/>`;
    if (o.label) { let nx = -uy, ny = ux; if (ny > 0) { nx = -nx; ny = -ny; } s += lbl(o.label, (a.x + b.x) / 2 + nx * 16, (a.y + b.y) / 2 + ny * 16, 15); }
    return s + hit(d0);
  }

  /* ── a conical pendulum in an oblique view: the bob's horizontal circle as an ellipse (the half behind the axis dashed),
     the vertical axis through the pivot, the radius r from the circle's centre to the bob and the angle θ of the string
     from the vertical ── */
  function conicalMarks(o) {
    const A = byId.get(o.a), Bo = byId.get(o.b), P = [A, Bo].find(x => x?.type === 'pivot'), b = [A, Bo].find(isBody);
    if (!P || !b) return '';
    const given = (opts.conical || []).find(c => c.id === o.id);
    let C, R;
    if (given) { C = given.centre; R = given.radius; } else { const p = bodyPose(scene, b); C = {x: P.x, y: p.y}; R = Math.abs(p.x - P.x); }
    if (!(R > 1e-6)) return '';
    const c = screen(C), rx = R * S, ry = rx * CONE_TILT, pv = screen(P), q = screen(opts.poses?.get?.(b.id) || poseOf(b));
    let s = `<path d="M${f(c.x - rx)},${f(c.y)}A${f(rx)},${f(ry)} 0 0 1 ${f(c.x + rx)},${f(c.y)}" fill="none" stroke="${ink}" stroke-width="${f(hair)}"${dash('dashed', 0.8)}/>`;
    s += `<path d="M${f(c.x + rx)},${f(c.y)}A${f(rx)},${f(ry)} 0 0 1 ${f(c.x - rx)},${f(c.y)}" fill="none" stroke="${ink}" stroke-width="${f(thin)}"/>`;
    s += line(pv, {x: c.x, y: c.y + ry + 12 * ss}, hair, dash('dashdot', 0.8));
    s += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(Math.max(1.4, st.dot * ss * 0.7))}" fill="${ink}"/>`;
    s += line(c, q, hair, dash('dashed', 0.7));
    /* r near the axis end of the radius, so a force drawn from the bob along it keeps its own label */
    const mr = {x: c.x + (q.x - c.x) * 0.3, y: c.y + (q.y - c.y) * 0.3};
    s += lbl('r', mr.x, mr.y + (q.y >= c.y ? -11 : 11), 14, 'middle', '', {halo: true});
    const L = Math.hypot(q.x - pv.x, q.y - pv.y), ar = Math.max(16, Math.min(40, L * 0.28)), a1 = Math.atan2(q.y - pv.y, q.x - pv.x), a0 = Math.PI / 2;
    if (Math.abs(a1 - a0) > 0.04) {
      const p1 = {x: pv.x + ar * Math.cos(a0), y: pv.y + ar * Math.sin(a0)}, p2 = {x: pv.x + ar * Math.cos(a1), y: pv.y + ar * Math.sin(a1)}, mid = (a0 + a1) / 2;
      s += `<path d="M${f(p1.x)},${f(p1.y)}A${f(ar)},${f(ar)} 0 0 ${a1 < a0 ? 0 : 1} ${f(p2.x)},${f(p2.y)}" fill="none" stroke="${ink}" stroke-width="${f(hair * 1.2)}"/>`;
      s += lbl('\\theta', pv.x + (ar + 11) * Math.cos(mid), pv.y + (ar + 11) * Math.sin(mid), 14, 'middle', '', {halo: true});
    }
    return s;
  }

  /* ── a typed potential: V(x), its bound states, a scattering state at E and T(E) beside it (E upwards in both) ── */
  function drawQpot(o) {
    const m = qpotModel(o), p0 = screen({x: o.x, y: o.y}), W0 = o.w * S, h = o.h * S;
    let s = '';
    if (!m.ok) return `<rect x="${f(p0.x)}" y="${f(p0.y - h)}" width="${f(W0)}" height="${f(h)}" fill="none" stroke="${ink}" stroke-dasharray="4 3" stroke-width="${f(hair)}"/>` + lbl('V(x)\,?', p0.x + W0 / 2, p0.y - h / 2, 15) + hitBox(p0.x, p0.y - h, W0, h);
    const w = m.curve ? W0 * 0.66 : W0, gx = p0.x + W0 * 0.74, gw = W0 * 0.26;
    const Elo = m.Vmin, Ehi = m.Emax, XW = x => p0.x + (x - m.x0) / (m.x1 - m.x0) * w, YE = E => p0.y - (E - Elo) / ((Ehi - Elo) || 1) * h;
    const y0 = YE(0);
    s += arrow({x: p0.x, y: y0}, {x: p0.x + w + 14, y: y0}, {width: thin}) + arrow({x: p0.x, y: p0.y}, {x: p0.x, y: p0.y - h - 14}, {width: thin}) + lbl('x', p0.x + w + 20, y0 + 1, 15, 'start') + lbl('E', p0.x - 8, p0.y - h - 10, 15, 'end');
    if (o.showV) {
      const segs = [[]];
      for (const q of m.vs) { if (Number.isFinite(q.V)) segs[segs.length - 1].push({x: XW(q.x), y: Math.max(p0.y - h * 1.04, YE(q.V))}); else if (segs[segs.length - 1].length) segs.push([]); }
      for (const sg of segs) if (sg.length > 1) s += poly(sg, lw * 1.2);
      if (o.labels) { const top = m.vs.reduce((a, q) => Number.isFinite(q.V) && q.V > a.V ? q : a, {V: -Infinity, x: m.x0}); if (Number.isFinite(top.V) && top.V > 0) s += lbl('V(x)', Math.min(p0.x + w - 4, XW(top.x) + 6), Math.max(p0.y - h, YE(top.V)) - 11, 14, 'start', '', {halo: true}); }
    }
    const L = m.states.filter(q => q.bound), gaps = L.map((l, i) => i ? YE(L[i - 1].E) - YE(l.E) : Infinity);
    const amp = Math.max(6, Math.min(0.42 * Math.min(...gaps, h * 0.4), h * 0.16));
    L.forEach(l => {
      const yb = YE(l.E);
      s += line({x: p0.x, y: yb}, {x: p0.x + w, y: yb}, hair, dash('dashed', 0.7));
      if (o.psi !== 'none') {
        const vals = Array.from(l.psi, (v, i) => [l.xs[i], o.psi === 'prob' ? v * v : v]), mx = Math.max(...vals.map(v => Math.abs(v[1]))) || 1, step = Math.max(1, Math.floor(vals.length / 300));
        const pts = [{x: XW(m.x0), y: yb}]; for (let i = 0; i < vals.length; i += step) pts.push({x: XW(vals[i][0]), y: yb - amp * vals[i][1] / mx}); pts.push({x: XW(m.x1), y: yb});
        s += poly(pts, thin * 1.1);
      }
      if (o.labels) s += lbl(`E_${l.n}`, p0.x + w + 6, yb, 14, 'start', '', {halo: true});
    });
    if (m.scatter && m.scatter.ok && o.E <= Ehi) {
      const yb = YE(o.E), sc = m.scatter;
      s += line({x: p0.x, y: yb}, {x: p0.x + w, y: yb}, hair, dash('dashed', 0.7));
      if (o.psi !== 'none') {
        const vals = sc.psi.map(q => [q.x, o.psi === 'prob' ? q.re * q.re + q.im * q.im : q.re]), mx = Math.max(...vals.map(v => Math.abs(v[1]))) || 1, a2 = Math.min(h * 0.16, Math.max(8, (p0.y - h - yb) * -0.4));
        s += poly(vals.map(([x, v]) => ({x: XW(x), y: yb - a2 * v / mx})), thin * 1.1);
      }
      if (o.labels) s += lbl('E', p0.x + w + 6, yb, 14, 'start', '', {halo: true}) + lbl(`T = ${sc.T < 1e-3 ? sc.T.toExponential(1) : sc.T.toFixed(3)}`, p0.x + w - 4, p0.y - h + 8, 13, 'end', '', {halo: true});
    }
    if (o.psi !== 'none' && o.labels && (L.length || m.scatter?.ok)) s += lbl(o.psi === 'prob' ? '|\\psi|^2' : (m.scatter?.ok && !L.length ? '\\mathrm{Re}\\,\\psi' : '\\psi'), p0.x + 8, p0.y - h + 8, 15, 'start', '', {halo: true});
    if (m.curve) {
      /* T(E): T to the right (0 … 1), E upwards on the same scale as the potential */
      s += arrow({x: gx, y: p0.y}, {x: gx + gw + 10, y: p0.y}, {width: thin}) + arrow({x: gx, y: p0.y}, {x: gx, y: p0.y - h - 14}, {width: thin}) + lbl('T', gx + gw + 14, p0.y + 1, 15, 'start') + lbl('E', gx - 6, p0.y - h - 10, 15, 'end');
      s += line({x: gx + gw, y: p0.y}, {x: gx + gw, y: p0.y - h}, hair, dash('dotted')) + lbl('1', gx + gw, p0.y + 12, 12);
      const pts = m.curve.filter(q => q.E >= Elo).map(q => ({x: gx + q.T * gw, y: YE(q.E)}));
      if (pts.length > 1) s += poly([{x: gx, y: YE(Math.max(0, Elo))}, ...pts], thin * 1.15);
      if (m.scatter?.ok) { const yb = YE(o.E), xt = gx + m.scatter.T * gw; s += `<circle cx="${f(xt)}" cy="${f(yb)}" r="${f(Math.max(2, st.dot * ss * 1.2))}" fill="${ink}"/>` + line({x: gx, y: yb}, {x: xt, y: yb}, hair, dash('dotted')); }
    }
    return s + hitBox(p0.x, p0.y - h, W0, h);
  }

  /* ── a circuit element: leads from the two terminals to a symbol in the middle ── */
  function drawElement(e) {
    const a = screen({x: e.x1, y: e.y1}), b = screen({x: e.x2, y: e.y2}), L = Math.hypot(b.x - a.x, b.y - a.y);
    if (e.kind === 'wire') { const pts = elementPath(e).map(screen); return poly(pts, thin * 1.15) + hit('M' + pts.map(p => `${f(p.x)},${f(p.y)}`).join('L')); }
    if (L < 2) return '';
    const u = {x: (b.x - a.x) / L, y: (b.y - a.y) / L}; let n = {x: -u.y, y: u.x};
    const m = {x: (a.x + b.x) / 2, y: (a.y + b.y) / 2}, k = ss * Math.min(1.25, Math.max(0.8, CUR.ls / ss));
    const P2 = (s1, t) => ({x: m.x + u.x * s1 + n.x * t, y: m.y + u.y * s1 + n.y * t}), pt = (s1, t) => { const q = P2(s1, t); return `${f(q.x)},${f(q.y)}`; };
    const W2 = thin * 1.15;
    let half = 0, body = '', halfW = 12 * k;
    const leads = h => line(a, P2(-h, 0), W2) + line(P2(h, 0), b, W2);
    const K = e.kind;
    if (K === 'resistor' || K === 'rheostat') {
      half = Math.min(L * 0.32, 22 * k);
      const look = e.look === 'auto' ? st.resistor : e.look;
      if (look === 'box') { body = `<polygon points="${pt(-half, -6.5 * k)} ${pt(half, -6.5 * k)} ${pt(half, 6.5 * k)} ${pt(-half, 6.5 * k)}" fill="#fff" stroke="${ink}" stroke-width="${f(W2 * 1.1)}"/>`; halfW = 8 * k; }
      else { let d = `M${pt(-half, 0)}`; for (let i = 0; i < 6; i++) d += `L${pt(-half + half * 2 * (2 * i + 1) / 12, (i % 2 ? -1 : 1) * 6.5 * k)}`; d += `L${pt(half, 0)}`; body = `<path d="${d}" fill="none" stroke="${ink}" stroke-width="${f(W2 * 1.1)}" stroke-linejoin="round"/>`; halfW = 8 * k; }
      if (K === 'rheostat') body += arrow(P2(-half * 0.9, 11 * k), P2(half * 0.95, -13 * k), {width: W2, head: 7 * k}); halfW = K === 'rheostat' ? 13 * k : halfW;
    } else if (K === 'dielectric') {
      half = 6 * k; const pr = `polygon points="${pt(-half, -11 * k)} ${pt(half, -11 * k)} ${pt(half, 11 * k)} ${pt(-half, 11 * k)}"`;
      body = (st.gray ? `<${pr} fill="${st.light}" stroke="none"/>` : shade(pr, 'dots')) + line(P2(-half, -13 * k), P2(-half, 13 * k), Math.max(2, lw * 1.25)) + line(P2(half, -13 * k), P2(half, 13 * k), Math.max(2, lw * 1.25)); halfW = 13 * k;
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
      const read = K === 'voltmeter' ? `${fmtSI(-drop, 'V')}` : K === 'capacitor' || K === 'dielectric' ? `${fmtSI(Math.abs(drop), 'V')}` : Math.abs(I) > 1e-9 ? `${fmtSI(Math.abs(I), 'A')}` : K === 'ammeter' || K === 'galvanometer' ? '0 A' : '';
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
      if (deg >= 3) { const c = screen(p); d += `<circle cx="${f(c.x)}" cy="${f(c.y)}" r="${f(st.dot * ss * 1.1)}" fill="${ink}"/>`; }
    }
    return d;
  }
}

/** the world box around one object (for the selection outline and for picking) */
export function objectBox(scene, o, poses, opts2 = {}) {
  const byId = new Map(scene.objects.map(x => [x.id, x]));
  const box = pts => { const xs = pts.map(p => p.x), ys = pts.map(p => p.y), x = Math.min(...xs), y = Math.min(...ys); return {x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y}; };
  if (isBody(o)) { const p = poses?.get?.(o.id) || bodyPose(scene, o), r = isRound(o) ? o.r : Math.hypot(o.w, o.h) / 2; return {x: p.x - r, y: p.y - r, w: 2 * r, h: 2 * r}; }
  switch (o.type) {
    case 'string': case 'rod': case 'spring': { const A = byId.get(o.a), B = byId.get(o.b); if (!A || !B) return null; const pa = isBody(A) ? (poses?.get?.(A.id) || bodyPose(scene, A)) : A, pb = isBody(B) ? (poses?.get?.(B.id) || bodyPose(scene, B)) : B; return box([pa, pb, ...((o.over || []).map(id => byId.get(id)).filter(Boolean))]); }
    case 'vector': return box(vectorPoints(scene, o, poses));
    case 'force': { const b = byId.get(o.on); if (!b) return null; const p = poses?.get?.(b.id) || bodyPose(scene, b), th = o.angle * Math.PI / 180; return box([p, {x: p.x + Math.cos(th) * o.len, y: p.y + Math.sin(th) * o.len}]); }
    case 'curve': case 'cycle': { const g = byId.get(o.graph); return g ? objectExtent(g) : null; }
    case 'worldline': { const g = byId.get(o.diagram); return g ? objectExtent(g) : null; }
    case 'fieldlines': return null;
    case 'joint': { const e = opts2.jointEnds?.get?.(o.id) || jointEnds(scene, o); return e ? box([e.a, e.b]) : null; }
    case 'farrow': { const A = byId.get(o.a), B = byId.get(o.b); return A && B ? box([A, B]) : null; }
  }
  if (GEO_TYPES.includes(o.type)) return geoExtent(opts2.geo || computeGeometry(scene), o);
  return objectExtent(o);
}
export {surfaceFrame};
