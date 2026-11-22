// Model and command interpreter for HPhO mock 1, experiment E1 (water creeping into paper).
// No DOM and no network: app.mjs drives it in the browser, check.mjs drives it in node.

export const C = { gw: 0.0720, mw: 1.00e-3, ms: 1.05e-3, rho: 1000, dip: 5, len: 300, strips: 12, maxFill: 50 };

export function mulberry(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function gauss(r) { let u = 0; while (!u) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); }

// Hidden instrument parameters. SI units except where the name says otherwise.
export function drawParams(seed, nominal = false) {
  const r = mulberry(seed ^ 0x9E3779B9);
  const u = (a, b) => nominal ? (a + b) / 2 : a + (b - a) * r();
  const p = {
    Kw: 2.0e-5 * u(0.88, 1.12),       // water imbibition constant, m^2/s
    gs: 0.032 * u(0.88, 1.12),        // surfactant surface tension, N/m
    cosRatio: nominal ? 1.02 : u(1.00, 1.05), // cos(theta_s)/cos(theta_w), surfactant wets better
    t: 0.18e-3 * u(0.93, 1.07),       // mean sheet thickness, m
    phi: 0.65 * u(0.93, 1.07),        // porosity
    b: 15.0e-3 * u(0.993, 1.007),     // strip width, m
    E: 1.0e-5 * u(0.80, 1.25),        // evaporation from a wet face in open air, kg m^-2 s^-1
    dishFrac: u(0.55, 0.80),          // free-water surface evaporates slower than wet paper
    boxFrac: u(0.005, 0.02),          // residual evaporation inside the closed container
    rhoCell: 1500 * u(0.95, 1.05),    // cellulose density, kg/m^3
    dishD: [u(86, 94), u(86, 94)],    // inner diameters, mm
    tare: [u(28, 34), u(28, 34)],     // empty dish masses, g
    strips: []
  };
  for (let i = 0; i < C.strips; i++) p.strips.push({ k: 1 + 0.03 * gauss(r), t: 1 + 0.02 * gauss(r), oil: 0 });
  return p;
}

export function newState(seed = (Math.random() * 2 ** 32) >>> 0) {
  return {
    v: 1, seed, ns: (seed * 2654435761) >>> 0, clock: 0, next: 1, n: 0,
    dishes: [0, 1].map(i => ({ id: 'd' + (i + 1), i, liquid: null, liq: 0, env: 'open', t: 0, mount: null })),
    wet: null, records: [], inside: false, pendingReset: false
  };
}

export const liquidK = (p, liq) => liq === 'water' ? p.Kw : p.Kw * (p.gs / C.ms) / (C.gw / C.mw) * p.cosRatio;
const stripE = (p, env) => env === 'box' ? p.E * p.boxFrac : p.E;
const dishE = (p, env) => p.E * p.dishFrac * (env === 'box' ? p.boxFrac : 1);
const thick = (p, n) => p.t * p.strips[n - 1].t;

function mountConst(p, m) {
  const K = liquidK(p, m.liquid) * p.strips[m.strip - 1].k, th = thick(p, m.strip), E = stripE(p, m.env);
  return { K, U: p.phi * C.rho * th * K / (4 * E) };
}
// True wetted length above the liquid surface (m) a time tau after contact. d(L^2)/dt = K(1 - L^2/Lmax^2).
export function frontL(p, m, tau) {
  if (tau <= 0) return 0;
  const { K, U } = mountConst(p, m);
  return Math.min(Math.sqrt(-U * Math.expm1(-K * tau / U)), (C.len - C.dip) / 1000);
}
export function timeTo(p, m, L) {
  const { K, U } = mountConst(p, m), u = L * L;
  if (L > (C.len - C.dip) / 1000 || u >= U) return Infinity;
  return -U / K * Math.log1p(-u / U);
}

const fmtClock = s => { s = Math.round(s); return [s / 3600 | 0, (s / 60 | 0) % 60, s % 60].map(x => String(x).padStart(2, '0')).join(':'); };
const dw = s => [...String(s)].reduce((a, ch) => a + (/[\u1100-\u11ff\u3000-\u9fff\uac00-\ud7af\uff00-\uffef]/.test(ch) ? 2 : 1), 0);
const pad = (s, n) => String(s) + ' '.repeat(Math.max(0, n - dw(s)));
const lpad = (s, n) => String(s).padStart(n);
const table = (head, rows) => {
  const w = head.map((h, i) => Math.max(dw(h), ...rows.map(r => dw(r[i]))));
  return [head, ...rows].map(r => r.map((c, i) => pad(c, w[i])).join('  ').trimEnd()).join('\n');
};

const T = {
  ko: {
    banner: 'WickLab  종이 침투 실험 장치\n스트립 12장 | 접시 d1, d2 | 뚜껑 있는 용기 1개 | 모든 시간은 모의 시계\nhelp 로 명령어를 확인하세요.',
    unknown: c => `${c}: 알 수 없는 명령어입니다. help 를 입력하세요.`,
    dish: '접시는 d1 또는 d2 로 지정하세요.',
    noLiquid: d => `${d} 에 액체가 없습니다. 먼저 fill ${d} water 30 처럼 채우세요.`,
    mounted: d => `${d} 에 스트립이 걸려 있습니다. 먼저 lift ${d} 로 꺼내세요.`,
    noMount: d => `${d} 에 걸린 스트립이 없습니다.`,
    which: '스트립이 둘 이상 걸려 있습니다. 접시를 지정하세요 (예: read d1).',
    none: '걸린 스트립이 없습니다. dip d1 처럼 먼저 스트립을 담그세요.',
    noStrip: '남은 스트립이 없습니다.',
    boxFull: d => `용기 안에는 접시 하나만 들어갑니다. ${d} 가 이미 들어 있습니다.`,
    fill: (d, l, v) => `${d} 를 헹군 뒤 ${l} ${v} mL 를 눈금 실린더로 채웠습니다.`,
    place: (d, e) => e === 'box' ? `${d} 를 투명 용기 안에 넣고 뚜껑을 닫았습니다.` : `${d} 를 용기 밖 실험대 위에 두었습니다.`,
    dip: (d, n, e) => `스트립 #${n} 의 아래 끝을 ${d} 에 5 mm 담그고 스톱워치를 눌렀습니다.${e === 'box' ? ' (뚜껑 닫힌 용기 안)' : ' (뚜껑 없음)'}\n눈금자의 0 은 액면에 맞추어 두었습니다.`,
    lift: (d, n) => `스트립 #${n} 을 ${d} 에서 꺼냈습니다. 바로 weigh wet 로 질량을 잴 수 있습니다.`,
    wait: s => `기다림 ${s}`,
    past: (mk) => `젖은 앞면이 이미 ${mk} mm 를 지났습니다.`,
    notReached: (mk) => `60 분 동안 지켜보았지만 앞면이 ${mk} mm 에 닿지 않았습니다.`,
    badMark: `눈금은 1-${C.len - C.dip} mm 범위의 정수로 지정하세요.`,
    badWait: '예: wait 30 s, wait 5 min, wait 1 h (한 번에 4 h 까지)',
    badFill: `예: fill d1 water 30 (액체 water 또는 surf, 10-${C.maxFill} mL)`,
    badPlace: '예: place d1 box, place d2 open',
    badWeigh: '예: weigh strip, weigh strip 5, weigh wet, weigh d1',
    badCal: '예: caliper stack 10, caliper width, caliper d1',
    noWet: '저울에 올릴 젖은 스트립이 없습니다. lift 로 먼저 꺼내세요.',
    few: n => `남은 마른 스트립은 ${n} 장입니다.`,
    resetAsk: '장치를 새로 뽑고 모든 기록과 시계를 지웁니다. 계속하려면 reset yes 를 입력하세요.',
    resetDone: '새 장치를 준비했습니다. 기록과 시계를 지웠습니다.',
    empty: '저장된 측정이 없습니다.',
    csv: n => `측정 ${n} 개를 CSV 로 내려받습니다.`,
    status: '상태', water: '증류수', surf: '계면활성제액', box: '용기 안', open: '열린 곳',
    stripsLeft: n => `남은 스트립 ${n} 장`,
    helpHead: '명령어 (시간이 드는 동작은 모의 시계를 앞으로 돌립니다)',
    help: [
      ['status', '시계, 접시, 스트립 상태', 'status'],
      ['fill <d> <water|surf> [mL]', '접시를 헹구고 액체를 채움 (기본 30 mL)', 'fill d1 water 30'],
      ['place <d> <box|open>', '접시를 뚜껑 있는 용기 안 또는 밖에 둠', 'place d1 box'],
      ['dip <d>', '새 스트립을 5 mm 담그고 스톱워치 시작', 'dip d1'],
      ['wait <n> <s|min|h>', '모의 시간을 보냄', 'wait 5 min'],
      ['read [d]', '앞면 위치(눈금자)와 스톱워치를 읽음', 'read d1'],
      ['until [d] <mm>', '앞면이 그 눈금에 닿을 때까지 지켜보고 시각을 읽음', 'until d1 50'],
      ['lift [d]', '스트립을 액체에서 꺼냄 (흡수가 멈춤)', 'lift d1'],
      ['weigh strip [n]', '다음에 쓸 마른 스트립 n 장의 질량', 'weigh strip 5'],
      ['weigh wet', '마지막으로 꺼낸 젖은 스트립의 질량', 'weigh wet'],
      ['weigh <d>', '접시와 액체의 질량 (스트립을 뺀 상태)', 'weigh d2'],
      ['caliper stack <n>', '마른 스트립 n 장을 겹친 두께', 'caliper stack 10'],
      ['caliper <width|d>', '스트립 폭 또는 접시 안지름', 'caliper d2'],
      ['log [all]', '측정 기록 (기본: 최근 20 개)', 'log'],
      ['csv', '모든 측정을 CSV 로 내려받음', 'csv'],
      ['reset', '새 장치를 뽑고 기록을 지움 (확인 필요)', 'reset'],
      ['clear / exit', '화면 지우기 / 장치에서 나가기', 'exit']
    ]
  },
  en: {
    banner: 'WickLab  paper imbibition apparatus\n12 strips | dishes d1, d2 | 1 lidded container | all times on a simulated clock\nType help for the commands.',
    unknown: c => `${c}: unknown command. Type help.`,
    dish: 'Name a dish: d1 or d2.',
    noLiquid: d => `${d} is empty. Fill it first, e.g. fill ${d} water 30.`,
    mounted: d => `A strip is hanging in ${d}. Take it out first with lift ${d}.`,
    noMount: d => `No strip is hanging in ${d}.`,
    which: 'More than one strip is hanging. Name the dish, e.g. read d1.',
    none: 'No strip is hanging. Dip one first, e.g. dip d1.',
    noStrip: 'No strips are left.',
    boxFull: d => `The container holds one dish only. ${d} is already inside.`,
    fill: (d, l, v) => `Rinsed ${d} and filled it with ${v} mL of ${l} from the measuring cylinder.`,
    place: (d, e) => e === 'box' ? `Put ${d} inside the transparent container and closed the lid.` : `Put ${d} on the bench outside the container.`,
    dip: (d, n, e) => `Dipped the lower end of strip #${n} 5 mm into ${d} and started the stopwatch.${e === 'box' ? ' (inside the closed container)' : ' (no lid)'}\nThe zero of the ruler is at the liquid surface.`,
    lift: (d, n) => `Took strip #${n} out of ${d}. You can weigh it now with weigh wet.`,
    wait: s => `Waited ${s}`,
    past: mk => `The wet front is already past ${mk} mm.`,
    notReached: mk => `Watched for 60 min. The front did not reach ${mk} mm.`,
    badMark: `Give the mark as a whole number of mm, 1-${C.len - C.dip}.`,
    badWait: 'e.g. wait 30 s, wait 5 min, wait 1 h (at most 4 h at a time)',
    badFill: `e.g. fill d1 water 30 (liquid water or surf, 10-${C.maxFill} mL)`,
    badPlace: 'e.g. place d1 box, place d2 open',
    badWeigh: 'e.g. weigh strip, weigh strip 5, weigh wet, weigh d1',
    badCal: 'e.g. caliper stack 10, caliper width, caliper d1',
    noWet: 'There is no wet strip to weigh. Take one out with lift first.',
    few: n => `${n} dry strips are left.`,
    resetAsk: 'This draws a new apparatus and erases all records and the clock. Type reset yes to continue.',
    resetDone: 'A new apparatus is ready. Records and clock erased.',
    empty: 'No measurements yet.',
    csv: n => `Downloading ${n} measurements as CSV.`,
    status: 'Status', water: 'water', surf: 'surfactant', box: 'in box', open: 'open',
    stripsLeft: n => `${n} strips left`,
    helpHead: 'Commands (actions that take time move the simulated clock forward)',
    help: [
      ['status', 'clock, dishes and strips', 'status'],
      ['fill <d> <water|surf> [mL]', 'rinse a dish and fill it (default 30 mL)', 'fill d1 water 30'],
      ['place <d> <box|open>', 'put a dish inside the lidded container or outside', 'place d1 box'],
      ['dip <d>', 'dip a fresh strip 5 mm deep and start the stopwatch', 'dip d1'],
      ['wait <n> <s|min|h>', 'let simulated time pass', 'wait 5 min'],
      ['read [d]', 'read the front on the ruler and the stopwatch', 'read d1'],
      ['until [d] <mm>', 'watch until the front reaches a mark, then read the stopwatch', 'until d1 50'],
      ['lift [d]', 'take the strip out of the liquid (imbibition stops)', 'lift d1'],
      ['weigh strip [n]', 'mass of the next n unused dry strips', 'weigh strip 5'],
      ['weigh wet', 'mass of the strip you took out last', 'weigh wet'],
      ['weigh <d>', 'mass of a dish with its liquid (no strip in it)', 'weigh d2'],
      ['caliper stack <n>', 'thickness of n dry strips stacked', 'caliper stack 10'],
      ['caliper <width|d>', 'strip width or inner diameter of a dish', 'caliper d2'],
      ['log [all]', 'measurement log (default: last 20)', 'log'],
      ['csv', 'download all measurements as CSV', 'csv'],
      ['reset', 'draw a new apparatus and erase records (asks first)', 'reset'],
      ['clear / exit', 'clear the screen / leave the apparatus', 'exit']
    ]
  }
};

export function helpText(lang) {
  const t = T[lang] || T.ko;
  return t.helpHead + '\n\n' + table(lang === 'en' ? ['command', 'action', 'example'] : ['명령', '동작', '예'], t.help);
}

function advance(p, s, to) {
  for (const d of s.dishes) {
    if (d.liquid) d.liq = Math.max(0, d.liq - dishE(p, d.env) * Math.PI * (p.dishD[d.i] / 2000) ** 2 * (to - d.t) * 1000);
    d.t = to;
  }
  s.clock = to;
}
const liftUptake = (p, m, tau) => {
  // liquid drawn from the dish by a strip: what it holds plus what evaporated from it while hanging
  const L = frontL(p, m, tau), th = thick(p, m.strip), E = stripE(p, m.env);
  let integ = 0; const N = 200;
  for (let i = 0; i < N; i++) integ += frontL(p, m, tau * (i + 0.5) / N) * tau / N;
  return (p.phi * C.rho * p.b * th * (L + C.dip / 1000) + 2 * E * p.b * integ) * 1000;
};

function record(s, r) { s.records.push({ n: ++s.n, clock: Math.round(s.clock), ...r }); }

export function csvText(s) {
  const head = 'no,clock_s,kind,dish,strip,liquid,env,stopwatch_s,value,unit,count';
  return [head, ...s.records.map(r => [r.n, r.clock, r.kind, r.dish || '', r.strip || '', r.liquid || '', r.env || '', r.t ?? '', r.value, r.unit, r.count || ''].join(','))].join('\n') + '\n';
}

function parseDur(args) {
  const m = /^(\d+(?:\.\d+)?)\s*(s|sec|min|m|h)?$/i.exec(args.join(' ').trim());
  if (!m) return null;
  const v = +m[1], u = (m[2] || 's').toLowerCase();
  const s = v * (u === 'h' ? 3600 : u === 'min' || u === 'm' ? 60 : 1);
  return s > 0 && s <= 4 * 3600 ? s : null;
}
const durText = s => s % 3600 === 0 ? s / 3600 + ' h' : s % 60 === 0 ? s / 60 + ' min' : s + ' s';

// Run one command. Returns {text, ok, clear?, csv?, filename?, exit?, reset?}.
export function exec(s, input, lang = 'ko', params) {
  const t = T[lang] || T.ko;
  let p = params || drawParams(s.seed);
  const r = mulberry(s.ns);
  const out = (text, ok = true, extra = {}) => { s.ns = (r() * 2 ** 32) >>> 0; return { text, ok, ...extra }; };
  const words = input.trim().split(/\s+/).filter(Boolean);
  const cmd = (words[0] || '').toLowerCase(), args = words.slice(1).map(w => w.toLowerCase());
  if (cmd !== 'reset') s.pendingReset = false;
  const head = () => `[${fmtClock(s.clock)}]`;
  const dishOf = a => s.dishes.find(d => d.id === a);
  const pickMounted = a => {
    if (a) { const d = dishOf(a); if (!d) return [null, t.dish]; if (!d.mount) return [null, t.noMount(d.id)]; return [d]; }
    const ms = s.dishes.filter(d => d.mount);
    if (!ms.length) return [null, t.none];
    if (ms.length > 1) return [null, t.which];
    return [ms[0]];
  };
  const liqName = l => t[l];
  const tick = sec => advance(p, s, s.clock + sec);
  switch (cmd) {
    case '': return out('');
    case 'help': case '?': return out(helpText(lang));
    case 'status': {
      const rows = s.dishes.map(d => [d.id, d.liquid ? liqName(d.liquid) : '-', t[d.env], d.mount ? '#' + d.mount.strip : '-']);
      return out(`${head()} ${t.status}  ·  ${t.stripsLeft(C.strips - s.next + 1)}\n` + table(lang === 'en' ? ['dish', 'liquid', 'place', 'strip'] : ['접시', '액체', '위치', '스트립'], rows) + (s.wet ? `\n${lang === 'en' ? 'wet strip on bench' : '꺼낸 젖은 스트립'}: #${s.wet.strip}` : ''));
    }
    case 'fill': {
      const d = dishOf(args[0]); if (!d) return out(t.dish, false);
      const liq = args[1] === 'water' || args[1] === 'surf' ? args[1] : null;
      const v = args[2] === undefined ? 30 : Number(args[2]);
      if (!liq || !Number.isFinite(v) || v < 10 || v > C.maxFill) return out(t.badFill, false);
      if (d.mount) return out(t.mounted(d.id), false);
      tick(60);
      const vol = Math.round(v);
      d.liquid = liq; d.liq = (vol + 0.3 * gauss(r)) * 1.00;
      return out(`${head()} ${t.fill(d.id, liqName(liq), vol)}`);
    }
    case 'place': {
      const d = dishOf(args[0]); if (!d) return out(t.dish, false);
      if (args[1] !== 'box' && args[1] !== 'open') return out(t.badPlace, false);
      if (d.mount) return out(t.mounted(d.id), false);
      const other = s.dishes.find(o => o !== d && o.env === 'box');
      if (args[1] === 'box' && other) return out(t.boxFull(other.id), false);
      tick(15); d.env = args[1];
      return out(`${head()} ${t.place(d.id, d.env)}`);
    }
    case 'dip': {
      const d = dishOf(args[0]); if (!d) return out(t.dish, false);
      if (!d.liquid) return out(t.noLiquid(d.id), false);
      if (d.mount) return out(t.mounted(d.id), false);
      if (s.next > C.strips) return out(t.noStrip, false);
      tick(20);
      d.mount = { strip: s.next++, liquid: d.liquid, env: d.env, c0: s.clock, d0: Math.max(0, 0.3 + 0.2 * gauss(r)), sig: 0.5 + 0.3 * r() };
      return out(`${head()} ${t.dip(d.id, d.mount.strip, d.env)}`);
    }
    case 'wait': {
      const sec = parseDur(args); if (sec === null) return out(t.badWait, false);
      tick(sec);
      return out(`${head()} ${t.wait(durText(sec))}`);
    }
    case 'read': {
      const [d, err] = pickMounted(args[0]); if (!d) return out(err, false);
      tick(5);
      const m = d.mount, tau = s.clock - m.c0, L = frontL(p, m, tau) * 1000;
      const sig = (m.sig + 0.004 * L) * (m.env === 'box' ? 1.2 : 1);
      const Lr = Math.max(0, Math.round(L + sig * gauss(r)));
      const sw = Math.max(0, tau - m.d0 + 0.3 * gauss(r));
      record(s, { kind: 'front', dish: d.id, strip: m.strip, liquid: m.liquid, env: m.env, t: +sw.toFixed(2), value: Lr, unit: 'mm' });
      return out(`${head()} ${d.id} #${m.strip} ${liqName(m.liquid)}, ${t[m.env]}\n` + table(['t (s)', 'L (mm)'], [[sw.toFixed(2), Lr]]));
    }
    case 'until': {
      let a = args.slice();
      if (a.length === 1) a = [null, a[0]];
      const [d, err] = pickMounted(a[0]); if (!d) return out(err, false);
      const mk = Number(a[1]);
      if (!Number.isInteger(mk) || mk < 1 || mk > C.len - C.dip) return out(t.badMark, false);
      const m = d.mount, tauNow = s.clock - m.c0;
      const sig = (m.sig + 0.004 * mk) * (m.env === 'box' ? 1.2 : 1);
      const T0 = timeTo(p, m, Math.max(0.0002, (mk + sig * gauss(r)) / 1000));
      if (T0 <= tauNow) return out(t.past(mk), false);
      if (T0 - tauNow > 3600) {
        tick(3600);
        return out(`${head()} ${t.notReached(mk)}`);
      }
      const react = Math.max(0.05, 0.25 + 0.12 * gauss(r));
      advance(p, s, m.c0 + T0 + react);
      const sw = s.clock - m.c0 - m.d0;
      record(s, { kind: 'front', dish: d.id, strip: m.strip, liquid: m.liquid, env: m.env, t: +sw.toFixed(2), value: mk, unit: 'mm' });
      return out(`${head()} ${d.id} #${m.strip} ${liqName(m.liquid)}, ${t[m.env]}\n` + table(['t (s)', 'L (mm)'], [[sw.toFixed(2), mk]]));
    }
    case 'lift': {
      const [d, err] = pickMounted(args[0]); if (!d) return out(err, false);
      tick(3);
      const m = d.mount, tau = s.clock - m.c0, L = frontL(p, m, tau);
      d.liq = Math.max(0, d.liq - liftUptake(p, m, tau));
      const th = thick(p, m.strip);
      s.wet = { strip: m.strip, liquid: m.liquid, clock: s.clock, Lw: L + C.dip / 1000,
        absorbed: p.phi * C.rho * p.b * th * (L + C.dip / 1000) * 1000 + 0.002 + 0.01 * r() };
      d.mount = null;
      return out(`${head()} ${t.lift(d.id, s.wet.strip)}`);
    }
    case 'weigh': {
      const what = args[0];
      const bal = g => (Math.round((g + 0.004 * gauss(r)) * 100) / 100).toFixed(2);
      if (what === 'strip') {
        const n = args[1] === undefined ? 1 : Number(args[1]), left = C.strips - s.next + 1;
        if (!Number.isInteger(n) || n < 1) return out(t.badWeigh, false);
        if (n > left) return out(t.few(left), false);
        tick(15);
        let g = 0; for (let i = 0; i < n; i++) g += p.rhoCell * (1 - p.phi) * p.b * thick(p, s.next + i) * (C.len / 1000) * 1000;
        const v = bal(g), ids = n === 1 ? '#' + s.next : `#${s.next}-#${s.next + n - 1}`;
        record(s, { kind: 'mass_dry', strip: ids, value: v, unit: 'g', count: n });
        return out(`${head()} ${lang === 'en' ? 'dry strips' : '마른 스트립'} ${ids} (${n})\n` + table(['m (g)'], [[v]]));
      }
      if (what === 'wet') {
        if (!s.wet) return out(t.noWet, false);
        tick(10);
        const w = s.wet, loss = 2 * p.E * p.b * w.Lw * (s.clock - w.clock) * 1000;
        const dry = p.rhoCell * (1 - p.phi) * p.b * thick(p, w.strip) * (C.len / 1000) * 1000;
        const v = bal(dry + Math.max(0, w.absorbed - loss));
        const dt = Math.round(s.clock - w.clock);
        record(s, { kind: 'mass_wet', strip: w.strip, liquid: w.liquid, value: v, unit: 'g' });
        return out(`${head()} ${lang === 'en' ? 'wet strip' : '젖은 스트립'} #${w.strip}, ${lang === 'en' ? `${dt} s after lifting` : `꺼낸 뒤 ${dt} s`}\n` + table(['m (g)'], [[v]]));
      }
      const d = dishOf(what);
      if (!d) return out(t.badWeigh, false);
      if (d.mount) return out(t.mounted(d.id), false);
      tick(20);
      const v = bal(p.tare[d.i] + (d.liquid ? d.liq : 0));
      record(s, { kind: 'mass_dish', dish: d.id, liquid: d.liquid || '', env: d.env, value: v, unit: 'g' });
      return out(`${head()} ${d.id} ${lang === 'en' ? 'with liquid' : '접시와 액체'} (${d.liquid ? liqName(d.liquid) : '-'}, ${t[d.env]})\n` + table(['m (g)'], [[v]]));
    }
    case 'caliper': {
      const what = args[0];
      const vern = mm => (Math.round(mm / 0.02) * 0.02).toFixed(2);
      if (what === 'stack') {
        const n = Number(args[1]), left = C.strips - s.next + 1;
        if (!Number.isInteger(n) || n < 1) return out(t.badCal, false);
        if (n > left) return out(t.few(left), false);
        tick(30);
        let mm = 0; for (let i = 0; i < n; i++) mm += thick(p, s.next + i) * 1000;
        mm += n * 0.002 * r() + 0.008 * gauss(r);
        const v = vern(mm);
        record(s, { kind: 'thickness', strip: n === 1 ? '#' + s.next : `#${s.next}-#${s.next + n - 1}`, value: v, unit: 'mm', count: n });
        return out(`${head()} ${lang === 'en' ? `${n} dry strips stacked` : `마른 스트립 ${n} 장 겹침`}\n` + table(['d (mm)'], [[v]]));
      }
      if (what === 'width') {
        tick(15);
        const v = vern(p.b * 1000 + 0.01 * gauss(r));
        record(s, { kind: 'width', value: v, unit: 'mm' });
        return out(`${head()} ${lang === 'en' ? 'strip width' : '스트립 폭'}\n` + table(['b (mm)'], [[v]]));
      }
      const d = dishOf(what); if (!d) return out(t.badCal, false);
      tick(20);
      const v = vern(p.dishD[d.i] + 0.08 * gauss(r));
      record(s, { kind: 'diameter', dish: d.id, value: v, unit: 'mm' });
      return out(`${head()} ${d.id} ${lang === 'en' ? 'inner diameter' : '안지름'}\n` + table(['D (mm)'], [[v]]));
    }
    case 'log': {
      if (!s.records.length) return out(t.empty);
      const list = args[0] === 'all' ? s.records : s.records.slice(-20);
      return out(table(['#', 'clock', 'kind', 'dish', 'strip', 'liquid', 'env', 't (s)', 'value'],
        list.map(x => [x.n, fmtClock(x.clock), x.kind, x.dish || '-', x.strip || '-', x.liquid || '-', x.env || '-', x.t === undefined ? '-' : x.t.toFixed(2), `${x.value} ${x.unit}${x.count > 1 ? ' (n=' + x.count + ')' : ''}`])));
    }
    case 'csv': case 'export':
      if (!s.records.length) return out(t.empty);
      return out(t.csv(s.records.length), true, { csv: csvText(s), filename: 'hpho-e1-wicklab.csv' });
    case 'reset':
      if (args[0] === 'yes' && s.pendingReset) return out(t.resetDone, true, { reset: true });
      s.pendingReset = true;
      return out(t.resetAsk);
    case 'clear': return out('', true, { clear: true });
    case 'exit': case 'quit': return out('', true, { exit: true });
    default: return out(t.unknown(words[0]), false);
  }
}
export const banner = lang => (T[lang] || T.ko).banner;
export const helpRows = lang => (T[lang] || T.ko).help;
