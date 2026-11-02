// Numeric equivalence of two final expressions, as Math-Verify does it for answers (extract, normalise, compare), with
// the comparison done by evaluation at random points: the official expression from the marking scheme and the
// candidate's, both written by a model in plain ASCII math (2*g*L*h^2*(rho_1-rho_0)^2/(k^2*rho_1)). The parser is
// small and closed: numbers, variables, + - * / ^, parentheses and a fixed list of functions; nothing is executed.
const FUNCS = { sqrt: Math.sqrt, exp: Math.exp, ln: Math.log, log: Math.log, log10: Math.log10, sin: Math.sin, cos: Math.cos, tan: Math.tan,
  asin: Math.asin, acos: Math.acos, atan: Math.atan, arcsin: Math.asin, arccos: Math.acos, arctan: Math.atan, sinh: Math.sinh, cosh: Math.cosh,
  tanh: Math.tanh, abs: Math.abs, cot: x => 1 / Math.tan(x), sec: x => 1 / Math.cos(x), csc: x => 1 / Math.sin(x) };
const CONSTS = { pi: Math.PI };
const GREEK = { "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon", "ζ": "zeta", "η": "eta", "θ": "theta", "κ": "kappa", "λ": "lambda",
  "μ": "mu", "ν": "nu", "ξ": "xi", "π": "pi", "ρ": "rho", "σ": "sigma", "τ": "tau", "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
  "Γ": "Gamma", "Δ": "Delta", "Θ": "Theta", "Λ": "Lambda", "Σ": "Sigma", "Φ": "Phi", "Ψ": "Psi", "Ω": "Omega" };

/* the right-hand side of «x = …», Unicode tidied: × · → *, − → -, ², ³ → ^2, ^3, Greek letters spelled out */
function normalise(text) {
  let s = String(text ?? "").slice(0, 600);
  if (/[<>≤≥≈∝]/.test(s)) s = s.split(/[<>≤≥≈∝]/).pop();
  if (s.includes("=")) s = s.slice(s.lastIndexOf("=") + 1);
  s = s.replace(/[×·⋅]/g, "*").replace(/[−–]/g, "-").replace(/÷/g, "/").replace(/\*\*/g, "^")
    .replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹]+/g, d => "^" + [...d].map(c => "⁰¹²³⁴⁵⁶⁷⁸⁹".indexOf(c)).join("")).replace(/⁻\^/g, "^-").replace(/√/g, " sqrt").replace(/[{\[]/g, "(").replace(/[}\]]/g, ")");
  return s.replace(/[Ͱ-Ͽ]/g, ch => GREEK[ch] ? " " + GREEK[ch] + " " : ch).trim();
}

function tokenize(s) {
  const out = [], re = /\s*(?:(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)|([A-Za-z][A-Za-z0-9_']*)|([-+*/^(),]))/y;
  let at = 0;
  while (at < s.length) {
    if (/^\s*$/.test(s.slice(at))) break;
    re.lastIndex = at; const m = re.exec(s);
    if (!m) return null;                                                   // a character outside the grammar
    out.push(m[1] != null ? { t: "num", v: +m[1] } : m[2] != null ? { t: "id", v: m[2] } : { t: m[3] });
    at = re.lastIndex;
  }
  /* implicit products: 2g, g L, 2(…), )(…), x(… when x is not a function */
  const full = [];
  for (const tok of out) {
    const prev = full.at(-1);
    const ends = prev && (prev.t === "num" || prev.t === ")" || (prev.t === "id" && !FUNCS[prev.v]));
    const starts = tok.t === "num" || tok.t === "id" || tok.t === "(";
    if (ends && starts) full.push({ t: "*" });
    full.push(tok);
  }
  return full.length && full.length <= 400 ? full : null;
}

/* recursive descent: expr := term (± term)*, term := unary ((*|/) unary)*, unary := -unary | power, power := atom (^ unary)? */
function parse(tokens) {
  let i = 0;
  const peek = () => tokens[i], take = t => tokens[i]?.t === t ? tokens[i++] : null;
  const expr = () => { let a = term(); for (;;) { if (take("+")) { const b = term(); a = ["+", a, b]; } else if (take("-")) { const b = term(); a = ["-", a, b]; } else return a; } };
  const term = () => { let a = unary(); for (;;) { if (take("*")) { const b = unary(); a = ["*", a, b]; } else if (take("/")) { const b = unary(); a = ["/", a, b]; } else return a; } };
  const unary = () => take("-") ? ["neg", unary()] : take("+") ? unary() : power();
  const power = () => { const a = atom(); return take("^") ? ["^", a, unary()] : a; };
  const atom = () => {
    const tok = peek(); if (!tok) throw 0;
    if (tok.t === "num") { i++; return ["num", tok.v]; }
    if (tok.t === "(") { i++; const e = expr(); if (!take(")")) throw 0; return e; }
    if (tok.t === "id") {
      i++;
      if (FUNCS[tok.v]) { const open = take("("); const arg = open ? expr() : power(); if (open && !take(")")) throw 0; return ["fn", tok.v, arg]; }
      return CONSTS[tok.v] != null ? ["num", CONSTS[tok.v]] : ["var", tok.v];
    }
    throw 0;
  };
  try { const e = expr(); return i === tokens.length ? e : null; } catch { return null; }
}

function rename(node, map) {
  if (node[0] === "var") return map.has(node[1]) ? ["var", map.get(node[1])] : node;
  return node.map(child => Array.isArray(child) ? rename(child, map) : child);
}
/* a candidate's name for an official variable written another way (R_s for R_sun, P for p, mu_0 for mu, I0 for I_0):
   the same letters ignoring case and underscores, or one a prefix of the other, when only one official name fits */
const plain = name => name.replace(/[_']/g, "").toLowerCase();
function aliases(official, candidate) {
  const map = new Map(), free = [...official].filter(v => !candidate.has(v));
  for (const name of [...candidate].filter(v => !official.has(v))) {
    const p = plain(name), fits = free.filter(o => { const q = plain(o); return q === p || q.startsWith(p) || p.startsWith(q); });
    if (fits.length === 1) { map.set(name, fits[0]); free.splice(free.indexOf(fits[0]), 1); }
  }
  return map;
}
function vars(node, out = new Set()) {
  if (node[0] === "var") out.add(node[1]);
  else if (node[0] !== "num") for (const child of node.slice(1)) if (Array.isArray(child)) vars(child, out);
  return out;
}
function evaluate(node, at) {
  switch (node[0]) {
    case "num": return node[1];
    case "var": return at[node[1]];
    case "neg": return -evaluate(node[1], at);
    case "fn": return FUNCS[node[1]](evaluate(node[2], at));
    case "+": return evaluate(node[1], at) + evaluate(node[2], at);
    case "-": return evaluate(node[1], at) - evaluate(node[2], at);
    case "*": return evaluate(node[1], at) * evaluate(node[2], at);
    case "/": return evaluate(node[1], at) / evaluate(node[2], at);
    case "^": return Math.pow(evaluate(node[1], at), evaluate(node[2], at));
  }
  return NaN;
}
export function parseExpr(text) { const tokens = tokenize(normalise(text)); return tokens ? parse(tokens) : null; }

/* deterministic pseudo-random points (the same verdict every time for the same pair) */
function points(names, n, seed) {
  let x = seed >>> 0 || 1;
  const rnd = () => { x ^= x << 13; x >>>= 0; x ^= x >>> 17; x ^= x << 5; x >>>= 0; return x / 4294967296; };
  return Array.from({ length: n }, () => Object.fromEntries(names.map(v => [v, 0.3 + 0.9 * rnd() + (rnd() < .5 ? 0 : 0.7 * rnd())])));
}

/** the variables of the paper's official expressions (a task's scheme items), for compareExpr's `known` */
export function schemeSymbols(exprs) {
  const out = new Set();
  for (const e of exprs || []) { const node = typeof e === "string" ? parseExpr(e) : null; if (node) vars(node, out); }
  return out;
}

/** {verdict:'equal'|'differs'|'factor', ratio?, missing?, extra?} or null when either side cannot be parsed or evaluated.
    known: the paper's own symbols (schemeSymbols of the task); a candidate's extra variable among them is a real
    dependence on a quantity of the problem (an L too many), not another notation */
export function compareExpr(official, candidate, { known = null } = {}) {
  const a = parseExpr(official); let b = parseExpr(candidate);
  if (!a || !b) return null;
  const va = vars(a); b = rename(b, aliases(va, vars(b)));
  const vb = vars(b), names = [...new Set([...va, ...vb])].sort();
  const missing = [...va].filter(v => !vb.has(v)), extra = [...vb].filter(v => !va.has(v));
  /* a name of the candidate's own that matches no official one, or more than one official name gone, is most likely a
     different notation (or a misreading), not a different answer: no verdict */
  if (extra.some(v => !known?.has(v)) || missing.length > 1) return null;
  const ratios = [];
  for (const at of points(names, 24, names.join(",").length * 7919 + 17)) {
    const x = evaluate(a, at), y = evaluate(b, at);
    if (!Number.isFinite(x) || !Number.isFinite(y) || Math.abs(x) < 1e-300) continue;
    ratios.push(y / x);
  }
  if (ratios.length < 4) return null;
  const close = (p, q) => Math.abs(p - q) <= 1e-6 * Math.max(1, Math.abs(p), Math.abs(q));
  if (ratios.every(r => close(r, 1))) return { verdict: "equal" };
  if (ratios.every(r => close(r, ratios[0]))) return { verdict: "factor", ratio: +ratios[0].toPrecision(4), missing, extra };
  return { verdict: "differs", missing, extra };
}

/* a short English statement for the re-check prompt */
export function describeCheck(c) {
  if (!c) return null;
  if (c.verdict === "equal") return "the candidate's final expression equals the official one at random values of its variables (an equivalent form)";
  const vars = [c.missing?.length ? `missing ${c.missing.join(", ")}` : "", c.extra?.length ? `extra ${c.extra.join(", ")}` : ""].filter(Boolean).join("; ");
  if (c.verdict === "factor") return `the candidate's final expression is ${c.ratio} times the official one at every random point (a wrong constant factor or sign)${vars ? "; " + vars : ""}`;
  const extract = c.extra?.length ? ". First make sure this is the candidate's final answer as written in the answer box, not a line of the working (IPhO 2021 T2: a grader quoted E_r = -q r/(8 pi eps0 R^3) for the boxed beta = 1/(16 pi eps0 R^3)); if it is not, judge the boxed answer." : "";
  return `the candidate's final expression differs from the official one at random values of its variables (not equivalent)${vars ? "; " + vars : ""}${extract}`;
}
