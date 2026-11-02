// Units in code: a unit as written (J·T^-1, A m², km/s, \mathrm{m\,s^{-1}}, μm, Ω) is parsed into its SI dimensions and
// scale, so that a value in an equivalent unit is right (A·m² is J/T; 32 T1 F.1.b lost a full point to it) and its
// conversion is done by code, not by the model. A unit that cannot be parsed returns null and the grader's own
// judgement stands. No code is evaluated: a closed table of units and prefixes.

// dimensions: m, kg, s, A, K, mol, cd
const D = (m = 0, kg = 0, s = 0, A = 0, K = 0, mol = 0, cd = 0) => [m, kg, s, A, K, mol, cd];
const UNITS = {
  m: [1, D(1)], g: [1e-3, D(0, 1)], s: [1, D(0, 0, 1)], A: [1, D(0, 0, 0, 1)], K: [1, D(0, 0, 0, 0, 1)], mol: [1, D(0, 0, 0, 0, 0, 1)], cd: [1, D(0, 0, 0, 0, 0, 0, 1)],
  N: [1, D(1, 1, -2)], J: [1, D(2, 1, -2)], W: [1, D(2, 1, -3)], Pa: [1, D(-1, 1, -2)], C: [1, D(0, 0, 1, 1)], V: [1, D(2, 1, -3, -1)],
  Ω: [1, D(2, 1, -3, -2)], ohm: [1, D(2, 1, -3, -2)], S: [1, D(-2, -1, 3, 2)], F: [1, D(-2, -1, 4, 2)], H: [1, D(2, 1, -2, -2)],
  T: [1, D(0, 1, -2, -1)], Wb: [1, D(2, 1, -2, -1)], Hz: [1, D(0, 0, -1)], Bq: [1, D(0, 0, -1)], rad: [1, D()], sr: [1, D()],
  eV: [1.602176634e-19, D(2, 1, -2)], L: [1e-3, D(3)], l: [1e-3, D(3)], min: [60, D(0, 0, 1)], h: [3600, D(0, 0, 1)], d: [86400, D(0, 0, 1)],
  yr: [3.15576e7, D(0, 0, 1)], au: [1.495978707e11, D(1)], AU: [1.495978707e11, D(1)], pc: [3.0857e16, D(1)], ly: [9.4607e15, D(1)],
  "Å": [1e-10, D(1)], bar: [1e5, D(-1, 1, -2)], atm: [101325, D(-1, 1, -2)], u: [1.66053906660e-27, D(0, 1)], Da: [1.66053906660e-27, D(0, 1)],
  G: [1e-4, D(0, 1, -2, -1)], erg: [1e-7, D(2, 1, -2)], cal: [4.184, D(2, 1, -2)], deg: [Math.PI / 180, D()], "°": [Math.PI / 180, D()],
};
const PREFIX = { Y: 1e24, Z: 1e21, E: 1e18, P: 1e15, T: 1e12, G: 1e9, M: 1e6, k: 1e3, h: 1e2, da: 1e1, d: 1e-1, c: 1e-2, m: 1e-3, μ: 1e-6, µ: 1e-6, u: 1e-6, n: 1e-9, p: 1e-12, f: 1e-15, a: 1e-18 };
const SUP = { "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "⁻": "-", "⁺": "+" };

/* one unit symbol, with a prefix where the symbol alone is not a unit */
const own = (o, k) => Object.hasOwn(o, k);
function symbol(word) {
  if (own(UNITS, word)) return UNITS[word];
  for (const p of Object.keys(PREFIX).sort((a, b) => b.length - a.length))
    if (word.length > p.length && word.startsWith(p) && own(UNITS, word.slice(p.length))) { const [f, d] = UNITS[word.slice(p.length)]; return [f * PREFIX[p], d]; }
  return null;
}

/** {scale, dims} of a unit as written, or null when it cannot be read with certainty */
export function parseUnit(text) {
  let t = String(text ?? "").trim();
  if (!t || t.length > 60) return null;
  if (/°\s*[CF]|℃|℉/.test(t)) return null;                                  // affine temperature scales: no conversion
  t = t.replace(/\\(mathrm|text|textrm|mathit|operatorname)\s*/g, "").replace(/\\(,|;|!|quad|qquad)/g, " ").replace(/\\(cdot|times)/g, "·")
    .replace(/\\Omega/g, "Ω").replace(/\\(mu|micro)/g, "μ").replace(/\\AA/g, "Å").replace(/\\circ/g, "°").replace(/[{}]/g, "")
    .replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+/g, m => "^" + [...m].map(c => SUP[c]).join("")).replace(/\*\*/g, "^").replace(/[−–]/g, "-")
    .replace(/^\[|\]$/g, "").replace(/\s*\^\s*/g, "^").replace(/\/\s*\(([^()]*)\)\s*$/, "/ $1").trim();   // J/(mol K): a group closing the unit
  if (!t || /[0-9]/.test(t.replace(/\^\(?-?\d+(\/\d+)?\)?/g, ""))) return null;   // a number outside an exponent
  let scale = 1, dims = D(), sign = 1;
  for (const tok of t.split(/(\/)|[\s·.*⋅]+/).filter(x => x !== undefined && x !== "")) {
    if (tok === "/") { sign = -1; continue; }
    const m = tok.match(/^([A-Za-zÅΩμµ°]+)(?:\^\(?(-?\d+)(?:\/(\d+))?\)?)?$/);
    if (!m) return null;
    const u = symbol(m[1]);
    if (!u) return null;
    const e = sign * (m[2] ? +m[2] / (m[3] ? +m[3] : 1) : 1);
    scale *= u[0] ** e; dims = dims.map((x, i) => x + u[1][i] * e);
  }
  return Number.isFinite(scale) && scale > 0 ? { scale, dims } : null;
}

/** null when either unit cannot be read; else {same: equal dimensions, factor: multiply a value in `written` by it for `official`} */
export function compareUnits(official, written) {
  const a = parseUnit(official), b = parseUnit(written);
  if (!a || !b) return null;
  const same = a.dims.every((x, i) => Math.abs(x - b.dims[i]) < 1e-9);
  return { same, factor: same ? b.scale / a.scale : null };
}
