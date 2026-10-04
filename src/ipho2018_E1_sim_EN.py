#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPhO 2018 (Lisbon) - Experimental Problem 1
Paper transistor

Virtual apparatus.  Nothing is computed for the student: the multimeter
shows what a 3 1/2 digit DMM shows on the range you selected, and nothing
else.  R_square, rho, kappa, V_DS, R_DS, I_DSS, V_P, g, tau_1 all have to
be worked out on paper.

Free-form cabling: any terminal may be wired to any other terminal.  The
circuit is then solved node by node, so miswiring behaves the way real
miswiring behaves - including blowing the 315 mA fuse.

The sheet is drawn the way it lies in Figs. 4, 7 and 10 of the problem:
the common Z track on top, R1 and R2 hanging from it (R1 wide end at Z,
R2 narrow end at Z), V and W at the bottom, the paper TFT in the upper
right corner.  The DC current ranges are the three of Table 1.

Run:  python ipho2018_E1_sim_KO.py   (EN edition: ipho2018_E1_sim_EN.py)
"""
import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "EN"          # the KO edition differs only in this line
TR = {
    'IPhO 2018 Experimental Problem 1 - Paper transistor': 'IPhO 2018 실험 1 - 종이 트랜지스터',
    '1. Assembly': '1. 조립',
    '2. Bench': '2. 실험대',
    'Click each item in the tray to take it out onto the bench.': '쟁반의 항목을 눌러 실험대로 꺼내세요.',
    'Take the mini-breadboard out first.': '먼저 미니 브레드보드를 꺼내세요.',
    'Everything is on the bench. Go to the Bench tab.\nWarning: the low current ranges are protected by a 315 mA fuse. A short between the battery and the multimeter in current mode will blow it.': '모두 실험대에 있습니다. 실험대 탭으로 이동하세요.\n주의: 낮은 전류 레인지는 315 mA 퓨즈로 보호됩니다. 전류 모드에서 전지와 멀티미터를 단락시키면 퓨즈가 끊어집니다.',
    '%d of %d items on the bench.': '%d / %d 개를 꺼냈습니다.',
    'Multimeter': '멀티미터',
    'Ask for a new fuse': '퓨즈 교체 요청',
    'Tool': '도구',
    'cable (click two terminals)': '케이블 (단자 두 곳 클릭)',
    'red probe': '빨강 프로브',
    'black probe': '검정 프로브',
    'remove a cable': '케이블 제거',
    'Draw 7 silver lines on R1': 'R1 에 은선 7개 긋기',
    'Draw 7 silver lines on R2': 'R2 에 은선 7개 긋기',
    'pencil stroke': '연필 덧칠',
    'eraser': '지우개',
    'Chronometer': '스톱워치',
    'time scale': '시간 배속',
    'Fuse replaced. You lost two minutes.': '퓨즈를 교체했습니다. 2분을 잃었습니다.',
    'Take the silver ink pen out first.': '먼저 은잉크 펜을 꺼내세요.',
    'Z  common': 'Z  공통',
    'Take the cables out first.': '먼저 케이블을 꺼내세요.',
    'Only 10 cables are provided.': '케이블은 10개뿐입니다.',
    'printed circuit sheet': '인쇄 회로 종이',
    'paper TFT': '종이 TFT',
    'mini-breadboard': '미니 브레드보드',
    'battery pack 4 x 1.5 V': '전지 팩 4 x 1.5 V',
    'pencil track': '연필 트랙',
    'FUSE BLOWN - current ranges are dead': '퓨즈 끊김 - 전류 레인지 사용 불가',
    'Printed paper sheet': '인쇄 회로 종이',
    'Battery pack (4 x 1.5 V)': '전지 팩 (4 x 1.5 V)',
    'Mini-breadboard': '미니 브레드보드',
    'JFET transistor': 'JFET 트랜지스터',
    'Cables with alligator clips': '악어클립 케이블',
    'Silver ink pen': '은잉크 펜',
    'HB pencil': 'HB 연필',
    'START/STOP': '시작/정지',
    'RESET': '리셋',
}



import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _setup_hangul_font(root):
    """Point every named Tk font at a family that actually has Hangul."""
    import tkinter.font as _tkfont
    want = ("Malgun Gothic", "AppleGothic", "Apple SD Gothic Neo",
            "NanumGothic", "NanumBarunGothic", "Noto Sans CJK KR",
            "Noto Sans KR", "UnDotum", "Gulim", "Batang")
    have = set(_tkfont.families(root))
    fam = next((f for f in want if f in have), None)
    if not fam:
        return
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont",
                 "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont",
                 "TkIconFont", "TkTooltipFont"):
        try:
            _tkfont.nametofont(name, root).configure(family=fam)
        except Exception:
            pass


def T(s):
    return TR.get(s, s) if LANG != "EN" else s


# ==========================================================================
#  PHYSICS  (calibrated against the official solution E1_S v1.4)
# ==========================================================================
RSQ_NOM = 123.94
T_FILM = 20e-6
SEG_W = [5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 2.0, 1.5]     # mm, wide -> narrow
SEG_L = 5.0                                            # mm
KAPPA = sum(SEG_L / w for w in SEG_W)                  # 14.2897

IDSS_NOM, VP_NOM = 11.89e-3, -1.42

TFT_A, TFT_T1 = 88.5e-6, 44.0
TFT_B, TFT_T2 = 265.5e-6, 880.0
TFT_VT, TFT_NV, TFT_ROFF = -1.85, 0.170, 894e3

FUSE_A = 0.315
VOLT_RIN = 10e6

# range name -> (full scale in base units, internal resistance)
A_RANGES = [("200mA", 0.2, 1.0), ("20mA", 0.02, 10.0),
            ("2mA", 2e-3, 100.0)]
V_RANGES = [("1000V", 1000.0), ("200V", 200.0), ("20V", 20.0),
            ("2V", 2.0), ("200mV", 0.2)]
O_RANGES = [("200", 200.0), ("2k", 2e3), ("20k", 2e4),
            ("200k", 2e5), ("2M", 2e6), ("20M", 2e7)]

# (mode, range) -> (base unit per displayed unit, full scale displayed, label)
RANGE_TBL = {
    "V:200mV": (1e-3, 200, "mV"), "V:2V": (1.0, 2, "V"),
    "V:20V": (1.0, 20, "V"), "V:200V": (1.0, 200, "V"),
    "V:1000V": (1.0, 1000, "V"),
    "A:2mA": (1e-3, 2, "mA"),
    "A:20mA": (1e-3, 20, "mA"), "A:200mA": (1e-3, 200, "mA"),
    "OHM:200": (1.0, 200, "ohm"), "OHM:2k": (1e3, 2, "kohm"),
    "OHM:20k": (1e3, 20, "kohm"), "OHM:200k": (1e3, 200, "kohm"),
    "OHM:2M": (1e6, 2, "Mohm"), "OHM:20M": (1e6, 20, "Mohm"),
}


class Sheet:
    def __init__(self, rng):
        j = lambda s: 1.0 + rng.gauss(0.0, s)
        self.rng = rng
        self.Rsq = RSQ_NOM * j(0.02)
        self.Rt = [self.Rsq * j(0.004) * f for f in (0.987, 1.012, 1.012)]
        # screen printing makes the staircase a shade narrower than nominal,
        # so the measured kappa sits a few 0.1 % above the geometric value -
        # exactly what the official A.5 shows (14.33 / 14.42 vs 14.2897)
        bias = 1.004 * j(0.004)
        self.R1 = KAPPA * self.Rsq * bias * j(0.004)
        self.R2 = KAPPA * self.Rsq * bias * j(0.004)
        self.off1 = [rng.gauss(0.0, 0.35) for _ in range(7)]
        self.off2 = [rng.gauss(0.0, 0.35) for _ in range(7)]
        self.rc1 = [45.0 + rng.gauss(0.0, 12.0) for _ in range(7)]
        self.rc2 = [45.0 + rng.gauss(0.0, 12.0) for _ in range(7)]
        self.drawn1 = False
        self.drawn2 = False

    def _frac(self, widths, off_mm, i):
        r = sum(SEG_L / w for w in widths[:i + 1])
        if i + 1 < len(widths):
            r += off_mm / widths[i + 1]
        return r / KAPPA

    def frac1(self, i):
        return self._frac(SEG_W, self.off1[i], i)          # Z at the wide end

    def frac2(self, i):
        return self._frac(SEG_W[::-1], self.off2[i], i)    # Z at the narrow end

    def segs1(self):
        """resistances of the 8 pieces of R1, from Z upwards"""
        f = [0.0] + [self.frac1(i) for i in range(7)] + [1.0]
        return [self.R1 * (f[i + 1] - f[i]) for i in range(8)]

    def segs2(self):
        f = [0.0] + [self.frac2(i) for i in range(7)] + [1.0]
        return [self.R2 * (f[i + 1] - f[i]) for i in range(8)]


class JFET:
    def __init__(self, rng):
        self.IDSS = IDSS_NOM * (1.0 + rng.gauss(0.0, 0.04))
        self.VP = VP_NOM * (1.0 + rng.gauss(0.0, 0.03))

    def _fwd(self, Vds, Vgs):
        ov = Vgs - self.VP
        if ov <= 0.0 or Vds <= 0.0:
            return 0.0
        b = self.IDSS / self.VP ** 2
        if Vds < ov:
            return b * (2.0 * ov * Vds - Vds * Vds)
        return b * ov * ov

    def current(self, Vds, Vgs):
        """current flowing from drain to source"""
        if Vds >= 0.0:
            return self._fwd(Vds, Vgs)
        return -self._fwd(-Vds, Vgs - Vds)      # source and drain swap roles


class TFT:
    """Electrolyte-gated paper TFT.  The two ionic branches relax separately."""

    def __init__(self, rng):
        j = lambda s: 1.0 + rng.gauss(0.0, s)
        self.VT = TFT_VT * j(0.03)
        self.nv = TFT_NV * j(0.10)
        self.Roff = TFT_ROFF * j(0.08)
        self.t1 = TFT_T1 * j(0.08)
        self.t2 = TFT_T2 * j(0.10)
        self.a = TFT_A / (TFT_A + TFT_B) * j(0.06)
        # switching off is fast: the gate actively drives the ions back.
        # Switching on is slow, and in two stages.  That asymmetry is why
        # the problem sheet says one minute is enough to close the device
        # but five minutes are not enough to open it.
        self.t_off = 12.0 * j(0.15)
        self.Ifull = (TFT_A + TFT_B) * j(0.05)
        self.beta = 2.0 * self.Ifull / self._ov(0.0) ** 2
        self.I1 = self.a * self.Ifull
        self.I2 = (1.0 - self.a) * self.Ifull
        self.Vgs = 0.0

    def _ov(self, Vgs):
        x = (Vgs - self.VT) / self.nv
        return self.nv * math.log1p(math.exp(min(x, 40.0)))

    @property
    def Isat(self):
        return self.I1 + self.I2

    def advance(self, dt, Vgs):
        self.Vgs = Vgs
        tgt = 0.5 * self.beta * self._ov(Vgs) ** 2
        for br, (cur, tau) in enumerate(((self.I1, self.t1),
                                         (self.I2, self.t2))):
            aim = (self.a if br == 0 else 1 - self.a) * tgt
            tc = tau if aim > cur else self.t_off
            cur += (aim - cur) * (1.0 - math.exp(-dt / tc))
            if br == 0:
                self.I1 = cur
            else:
                self.I2 = cur

    def _fwd(self, Vds, Vgs):
        ov = self._ov(Vgs)
        if Vds >= ov:
            ich = self.Isat
        else:
            ich = self.Isat * (2.0 * ov * Vds - Vds * Vds) / (ov * ov)
        return ich

    def current(self, Vds, Vgs):
        leak = Vds / self.Roff
        if Vds >= 0.0:
            return self._fwd(Vds, Vgs) + leak
        return -self._fwd(-Vds, Vgs - Vds) + leak


# ==========================================================================
#  a very small MNA solver (dense, no external dependencies)
# ==========================================================================
def gauss(A, b):
    n = len(b)
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(A[r][c]))
        if abs(A[p][c]) < 1e-18:
            A[c][c] += 1e-12
            p = c
        A[c], A[p] = A[p], A[c]
        b[c], b[p] = b[p], b[c]
        pv = A[c][c]
        for r in range(c + 1, n):
            f = A[r][c] / pv
            if f == 0.0:
                continue
            for k in range(c, n):
                A[r][k] -= f * A[c][k]
            b[r] -= f * b[c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = b[r] - sum(A[r][k] * x[k] for k in range(r + 1, n))
        x[r] = s / A[r][r]
    return x


class Circuit:
    """Nodes are strings.  'GND' is the reference."""

    def __init__(self):
        self.res = []        # (n1, n2, R)
        self.vsrc = []       # (np, nn, V, Rint)
        self.isrc = []       # (n_from, n_to, I)  current pushed from->to
        self.nl = []         # (nd, ns, ng, device)
        self.nodes = {"GND"}

    def _n(self, *names):
        for x in names:
            self.nodes.add(x)

    def R(self, a, b, r):
        self._n(a, b); self.res.append((a, b, max(r, 1e-9)))

    def V(self, p, n, v, rint=0.4):
        self._n(p, n); self.vsrc.append((p, n, v, rint))

    def I(self, a, b, i):
        self._n(a, b); self.isrc.append((a, b, i))

    def NL(self, d, s, g, dev):
        self._n(d, s, g); self.nl.append((d, s, g, dev))

    def live_nodes(self, keep):
        """components containing a source or a probe; the rest is invisible"""
        par = {k: k for k in self.nodes}

        def f(a):
            while par[a] != a:
                par[a] = par[par[a]]
                a = par[a]
            return a

        def u(a, b):
            ra, rb = f(a), f(b)
            if ra != rb:
                par[ra] = rb
        for a, c, _r in self.res:
            u(a, c)
        for d, sn, g, _dv in self.nl:
            u(d, sn); u(d, g)
        for p, n, _v, _r in self.vsrc:
            u(p, n)
        for a, c, _i in self.isrc:
            u(a, c)
        live = {f(x) for x in keep if x in par}
        for p, n, _v, _r in self.vsrc:
            live.add(f(p))
        return {nd for nd in self.nodes if f(nd) in live}

    def solve(self, guess=None, keep=()):
        alive = self.live_nodes(set(keep) | {"GND"})
        idx = {}
        for nd in sorted(alive):
            if nd != "GND":
                idx[nd] = len(idx)
        nn = len(idx)
        ns = len(self.vsrc)
        size = nn + ns
        v = {nd: 0.0 for nd in self.nodes}
        if guess:
            for k, val in guess.items():
                if k in v:
                    v[k] = val
        for _ in range(80):
            A = [[0.0] * size for _ in range(size)]
            b = [0.0] * size

            def stamp_g(a, c, g):
                ia, ic = idx.get(a), idx.get(c)
                if ia is not None:
                    A[ia][ia] += g
                if ic is not None:
                    A[ic][ic] += g
                if ia is not None and ic is not None:
                    A[ia][ic] -= g
                    A[ic][ia] -= g

            def stamp_i(a, c, cur):     # current forced from a into c
                ia, ic = idx.get(a), idx.get(c)
                if ia is not None:
                    b[ia] -= cur
                if ic is not None:
                    b[ic] += cur

            for a, c, r in self.res:
                stamp_g(a, c, 1.0 / r)
            for nd in idx:
                A[idx[nd]][idx[nd]] += 1e-12       # keeps floating nodes finite
            for a, c, i in self.isrc:
                stamp_i(a, c, i)
            for k, (p, n, val, rint) in enumerate(self.vsrc):
                row = nn + k
                ip, iq = idx.get(p), idx.get(n)
                if ip is not None:
                    A[ip][row] += 1.0
                    A[row][ip] += 1.0
                if iq is not None:
                    A[iq][row] -= 1.0
                    A[row][iq] -= 1.0
                A[row][row] -= rint
                b[row] = val

            # nonlinear devices, linearised about the present operating point
            for d, s, g, dev in self.nl:
                vd, vs, vg = v[d], v[s], v[g]
                vds, vgs = vd - vs, vg - vs
                i0 = dev.current(vds, vgs)
                h = 1e-5
                gds = (dev.current(vds + h, vgs) - dev.current(vds - h, vgs)) / (2 * h)
                gm = (dev.current(vds, vgs + h) - dev.current(vds, vgs - h)) / (2 * h)
                gds = max(gds, 1e-12)
                stamp_g(d, s, gds)
                ig, isn, idn = idx.get(g), idx.get(s), idx.get(d)
                if ig is not None:
                    if idn is not None:
                        A[idn][ig] += gm
                    if isn is not None:
                        A[isn][ig] -= gm
                if isn is not None:
                    if idn is not None:
                        A[idn][isn] -= gm
                    A[isn][isn] += gm
                ieq = i0 - gds * vds - gm * vgs
                stamp_i(d, s, ieq)

            x = gauss(A, b)
            step = 0.0
            for nd, i in idx.items():
                nv = x[i]
                d = nv - v[nd]
                if abs(d) > 0.35:
                    nv = v[nd] + 0.35 * (1 if d > 0 else -1)
                step = max(step, abs(nv - v[nd]))
                v[nd] = nv
            self._src_i = x[nn:]
            if step < 1e-10:
                break
        return v


# ==========================================================================
#  the multimeter
# ==========================================================================
class Meter:
    def __init__(self, rng):
        self.rng = rng
        self.mode = "OFF"          # OFF / V / A / OHM
        self.range = None
        self.red = None            # node the red probe touches
        self.black = None
        self.fuse_ok = True
        self.reading = None        # base units, or None
        self.ol = False

    def element(self, ck):
        """add the meter to the circuit; returns a callback that reads it"""
        if self.mode == "OFF" or not self.red or not self.black \
                or self.red == self.black:
            return None
        if self.mode == "V":
            ck.R(self.red, self.black, VOLT_RIN)
            return ("V", None)
        if self.mode == "A":
            if not self.fuse_ok:
                ck.R(self.red, self.black, 1e9)
                return ("A", None)
            rint = dict((n, r) for n, _f, r in A_RANGES)[self.range]
            ck.R(self.red, self.black, rint)
            return ("A", rint)
        # ohmmeter: inject a test current, read the voltage it develops
        itest = 0.2 / dict(O_RANGES)[self.range]
        ck.I(self.black, self.red, itest)
        ck.R(self.red, self.black, 1e9)
        return ("OHM", itest)

    def read(self, v, info):
        if info is None:
            self.reading, self.ol = None, False
            return
        kind, aux = info
        gv = lambda k: v.get(k, 0.0)
        if kind == "V":
            val = gv(self.red) - gv(self.black)
        elif kind == "A":
            if aux is None:
                self.reading, self.ol = 0.0, False
                return
            val = (gv(self.red) - gv(self.black)) / aux
            if abs(val) > FUSE_A:
                self.fuse_ok = False
        else:
            val = (gv(self.red) - gv(self.black)) / aux
        self.reading = val

    def display(self):
        if self.mode == "OFF":
            return ""
        if self.reading is None:
            return "  . "
        if self.mode == "A" and not self.fuse_ok:
            return " 0.00"
        scale, fs, _u = RANGE_TBL[self.mode + ":" + self.range]
        val = self.reading / scale
        step = fs / 2000.0
        val += self.rng.gauss(0.0, step * 0.35)      # last-digit flicker
        if abs(val) > fs - step / 2:
            return " 1   " if val > 0 else "-1   "
        val = round(val / step) * step
        dec = max(0, 4 - len(str(int(fs))))
        return ("%6." + str(dec) + "f") % val

    def unit(self):
        if self.mode == "OFF":
            return ""
        return RANGE_TBL[self.mode + ":" + self.range][2]


# ==========================================================================
#  terminals on the bench
# ==========================================================================
TAPS1 = ["A", "B", "C", "D", "E", "F", "G"]
STAIR_TOP = 190                     # canvas y of the Z end of R1 and R2
TAPS2 = ["H", "I", "J", "K", "L", "M", "N"]

PARTS = [
    ("sheet", "Printed paper sheet"),
    ("meter", "Multimeter"),
    ("batt", "Battery pack (4 x 1.5 V)"),
    ("board", "Mini-breadboard"),
    ("jfet", "JFET transistor"),
    ("cables", "Cables with alligator clips"),
    ("pen", "Silver ink pen"),
    ("pencil", "HB pencil"),
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(T("IPhO 2018 Experimental Problem 1 - Paper transistor"))
        self.geometry("1360x830")
        _setup_hangul_font(self)
        self.rng = random.Random()
        self.sheet = Sheet(self.rng)
        self.jfet = JFET(self.rng)
        self.tft = TFT(self.rng)
        self.meter = Meter(self.rng)
        self.vbat_p = 3.00 * (1 + self.rng.gauss(0, 0.008))
        self.vbat_m = 2.99 * (1 + self.rng.gauss(0, 0.008))
        self.placed = set()
        self.wires = []                     # (t1, t2)
        self.RL = None                      # pencil track, ohm
        self.rl_strokes = 0
        self.mode = tk.StringVar(value="cable")
        self.pending = None
        self.t_sim = 0.0
        self.watch_t = 0.0
        self.watch_run = False
        self.speed = tk.IntVar(value=1)
        self.volt = {}
        self.term = {}
        self._guess = {}
        self._build()
        self.after(60, self._tick)

    # ------------------------------------------------------------------
    def _build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.nb = nb
        self.tab_asm = tk.Frame(nb, bg="#f4f2ee")
        self.tab_bench = tk.Frame(nb, bg="#f4f2ee")
        nb.add(self.tab_asm, text=T("1. Assembly"))
        nb.add(self.tab_bench, text=T("2. Bench"))
        self._build_asm()
        self._build_bench()

    # ---------------- assembly ------------------------------------------
    def _build_asm(self):
        f = self.tab_asm
        tk.Label(f, bg="#f4f2ee", font=("TkDefaultFont", 10),
                 text=T("Click each item in the tray to take it out onto the bench.")
                 ).pack(anchor="w", padx=12, pady=8)
        self.asm_box = tk.Frame(f, bg="#f4f2ee")
        self.asm_box.pack(fill="both", expand=True, padx=16, pady=8)
        self.asm_btn = {}
        for i, (k, name) in enumerate(PARTS):
            b = tk.Button(self.asm_box, text=T(name), width=34, anchor="w",
                          command=lambda k=k: self._take(k))
            b.grid(row=i, column=0, sticky="w", pady=3)
            self.asm_btn[k] = b
        self.asm_note = tk.Label(self.asm_box, bg="#f4f2ee", fg="#4a443a",
                                 justify="left", wraplength=680, text="")
        self.asm_note.grid(row=len(PARTS), column=0, sticky="w", pady=14)
        self._asm_refresh()

    def _take(self, k):
        need = {"jfet": "board"}.get(k)
        if need and need not in self.placed:
            self.asm_note.config(text=T("Take the mini-breadboard out first."))
            return
        self.placed.add(k)
        self._asm_refresh()

    def _asm_refresh(self):
        for k, name in PARTS:
            self.asm_btn[k].config(
                text=("[x] " if k in self.placed else "[ ] ") + T(name),
                relief="sunken" if k in self.placed else "raised")
        if len(self.placed) == len(PARTS):
            self.asm_note.config(text=T(
                "Everything is on the bench. Go to the Bench tab.\n"
                "Warning: the low current ranges are protected by a 315 mA "
                "fuse. A short between the battery and the multimeter in "
                "current mode will blow it."))
        else:
            self.asm_note.config(text=T("%d of %d items on the bench.")
                                 % (len(self.placed), len(PARTS)))

    # ---------------- bench ----------------------------------------------
    def _build_bench(self):
        f = self.tab_bench
        self.c = tk.Canvas(f, bg="#fbfaf7", highlightthickness=0, width=1000)
        self.c.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self.c.bind("<Button-1>", self._click)
        self.c.bind("<Button-3>", self._rclick)

        r = tk.Frame(f, bg="#f4f2ee", width=340)
        r.pack(side="right", fill="y")
        r.pack_propagate(False)

        # ---- multimeter -------------------------------------------------
        mm = tk.LabelFrame(r, text=T("Multimeter"), bg="#f4f2ee", padx=8, pady=6)
        mm.pack(fill="x", padx=8, pady=(8, 4))
        self.lbl_disp = tk.Label(mm, text="", bg="#0d1410", fg="#8ef7a8",
                                 font=("Courier New", 24, "bold"), anchor="e",
                                 width=7)
        self.lbl_disp.pack(fill="x")
        self.lbl_unit = tk.Label(mm, text="", bg="#f4f2ee", anchor="e",
                                 font=("TkDefaultFont", 10, "bold"))
        self.lbl_unit.pack(fill="x")
        self.sel = tk.StringVar(value="OFF")
        grid = tk.Frame(mm, bg="#f4f2ee"); grid.pack(fill="x", pady=4)
        tk.Radiobutton(grid, text="OFF", variable=self.sel, value="OFF",
                       bg="#f4f2ee", command=self._set_mode).grid(row=0, column=0,
                                                                  sticky="w")
        row = 0
        for i, (n, _f) in enumerate(V_RANGES):
            row = 1 + i // 3
            tk.Radiobutton(grid, text="V " + n, variable=self.sel, value="V:" + n,
                           bg="#f4f2ee", command=self._set_mode
                           ).grid(row=row, column=i % 3, sticky="w")
        base = row + 1
        for i, (n, _f, _r) in enumerate(A_RANGES):
            tk.Radiobutton(grid, text="A " + n, variable=self.sel, value="A:" + n,
                           bg="#f4f2ee", command=self._set_mode
                           ).grid(row=base + i // 3, column=i % 3, sticky="w")
        base = base + (len(A_RANGES) + 2) // 3
        for i, (n, _f) in enumerate(O_RANGES):
            tk.Radiobutton(grid, text="\u03a9 " + n, variable=self.sel,
                           value="OHM:" + n, bg="#f4f2ee", command=self._set_mode
                           ).grid(row=base + i // 3, column=i % 3, sticky="w")
        self.lbl_fuse = tk.Label(mm, text="", bg="#f4f2ee", fg="#a33")
        self.lbl_fuse.pack(anchor="w")
        tk.Button(mm, text=T("Ask for a new fuse"), command=self._new_fuse
                  ).pack(anchor="w", pady=2)

        # ---- tools ------------------------------------------------------
        tl = tk.LabelFrame(r, text=T("Tool"), bg="#f4f2ee", padx=8, pady=6)
        tl.pack(fill="x", padx=8, pady=4)
        for val, lab in (("cable", T("cable (click two terminals)")),
                         ("red", T("red probe")),
                         ("black", T("black probe")),
                         ("cut", T("remove a cable"))):
            tk.Radiobutton(tl, text=lab, variable=self.mode, value=val,
                           bg="#f4f2ee", anchor="w").pack(fill="x")
        tk.Button(tl, text=T("Draw 7 silver lines on R1"),
                  command=lambda: self._draw_lines(1)).pack(fill="x", pady=(6, 1))
        tk.Button(tl, text=T("Draw 7 silver lines on R2"),
                  command=lambda: self._draw_lines(2)).pack(fill="x", pady=1)
        pf = tk.Frame(tl, bg="#f4f2ee"); pf.pack(fill="x", pady=(6, 0))
        tk.Button(pf, text=T("pencil stroke"), command=lambda: self._pencil(+1)
                  ).pack(side="left", expand=True, fill="x")
        tk.Button(pf, text=T("eraser"), command=lambda: self._pencil(-1)
                  ).pack(side="left", expand=True, fill="x")

        # ---- clock ------------------------------------------------------
        ck = tk.LabelFrame(r, text=T("Chronometer"), bg="#f4f2ee", padx=8, pady=6)
        ck.pack(fill="x", padx=8, pady=4)
        self.lbl_watch = tk.Label(ck, text="0:00.0", bg="#141414", fg="#e8e8e8",
                                  font=("Courier New", 17, "bold"))
        self.lbl_watch.pack(fill="x")
        wf = tk.Frame(ck, bg="#f4f2ee"); wf.pack(fill="x", pady=3)
        tk.Button(wf, text=T("START/STOP"), command=self._watch).pack(side="left")
        tk.Button(wf, text=T("RESET"), command=self._watch_rst).pack(side="left",
                                                                    padx=4)
        sf = tk.Frame(ck, bg="#f4f2ee"); sf.pack(fill="x")
        tk.Label(sf, text=T("time scale"), bg="#f4f2ee").pack(side="left")
        for v in (1, 5, 20):
            tk.Radiobutton(sf, text="x%d" % v, variable=self.speed, value=v,
                           bg="#f4f2ee").pack(side="left")
        self.lbl_hint = tk.Label(r, bg="#f4f2ee", fg="#6a6254", justify="left",
                                 wraplength=310, text="")
        self.lbl_hint.pack(anchor="w", padx=10, pady=8)

    # ---------------- tools ----------------------------------------------
    def _set_mode(self):
        s = self.sel.get()
        if s == "OFF":
            self.meter.mode, self.meter.range = "OFF", None
        else:
            m, rg = s.split(":")
            self.meter.mode, self.meter.range = m, rg

    def _new_fuse(self):
        if not self.meter.fuse_ok:
            self.meter.fuse_ok = True
            self.t_sim += 120.0
            self.lbl_hint.config(text=T("Fuse replaced. You lost two minutes."))

    def _draw_lines(self, which):
        if "pen" not in self.placed or "sheet" not in self.placed:
            self.lbl_hint.config(text=T("Take the silver ink pen out first."))
            return
        if which == 1:
            self.sheet.drawn1 = True
        else:
            self.sheet.drawn2 = True
        self.draw()

    def _pencil(self, s):
        if "pencil" not in self.placed:
            return
        self.rl_strokes = max(0, self.rl_strokes + s)
        if self.rl_strokes == 0:
            self.RL = None
        else:
            n = self.rl_strokes
            self.RL = 2.6e6 / (n ** 1.35) * (1 + self.rng.gauss(0, 0.05))
        self.draw()

    def _watch(self):
        self.watch_run = not self.watch_run

    def _watch_rst(self):
        if not self.watch_run:
            self.watch_t = 0.0

    # ---------------- terminals and geometry ------------------------------
    def _layout(self):
        t = {}
        # Z on top; R1 (wide end at Z) and R2 (narrow end at Z) hang from it
        t["Z"] = (300, 160, T("Z  common"))
        t["V"] = (200, 610, "V")
        t["W"] = (400, 610, "W")
        for i, nm in enumerate(TAPS1):
            t[nm] = (200, STAIR_TOP + 46 * (i + 1), nm)
        for i, nm in enumerate(TAPS2):
            t[nm] = (400, STAIR_TOP + 46 * (i + 1), nm)
        for i in range(3):
            t["T%da" % (i + 1)] = (520, 480 + 60 * i, "T%d" % (i + 1))
            t["T%db" % (i + 1)] = (600, 480 + 60 * i, "")
        # the paper TFT sits in the upper right corner of the sheet
        t["TG"] = (470, 100, "G")
        t["TS"] = (530, 100, "S")
        t["TD"] = (590, 100, "D")
        t["VIN"] = (620, 200, "Vin")
        t["JG"] = (740, 430, "G")
        t["JS"] = (790, 430, "S")
        t["JD"] = (840, 430, "D")
        t["BP"] = (720, 640, "+3V")
        t["BC"] = (790, 640, "com")
        t["BM"] = (860, 640, "-3V")
        return t

    def visible(self):
        v = set()
        if "sheet" in self.placed:
            v |= {"Z", "V", "W", "VIN", "TG", "TS", "TD"}
            v |= {"T%d%s" % (i, s) for i in (1, 2, 3) for s in "ab"}
            if self.sheet.drawn1:
                v |= set(TAPS1)
            if self.sheet.drawn2:
                v |= set(TAPS2)
        if "batt" in self.placed:
            v |= {"BP", "BC", "BM"}
        if "jfet" in self.placed:
            v |= {"JG", "JS", "JD"}
        return v

    # ---------------- interaction ----------------------------------------
    def _hit(self, x, y):
        best, bd = None, 18
        for k, (tx, ty, _lab) in self.term.items():
            if k not in self.visible():
                continue
            d = math.hypot(x - tx, y - ty)
            if d < bd:
                best, bd = k, d
        return best

    def _click(self, e):
        m = self.mode.get()
        k = self._hit(e.x, e.y)
        if m == "cut":
            self._cut(e.x, e.y)
            return
        if k is None:
            return
        if m == "red":
            self.meter.red = k
        elif m == "black":
            self.meter.black = k
        else:
            if "cables" not in self.placed:
                self.lbl_hint.config(text=T("Take the cables out first."))
                return
            if self.pending is None:
                self.pending = k
            elif self.pending == k:
                self.pending = None
            else:
                w = tuple(sorted((self.pending, k)))
                if w not in [tuple(sorted(x)) for x in self.wires]:
                    if len(self.wires) >= 10:
                        self.lbl_hint.config(text=T("Only 10 cables are provided."))
                    else:
                        self.wires.append((self.pending, k))
                self.pending = None
        self.draw()

    def _rclick(self, e):
        self._cut(e.x, e.y)

    def _cut(self, x, y):
        best, bd = None, 12
        for i, (a, b) in enumerate(self.wires):
            ax, ay, _ = self.term[a]
            bx, by, _ = self.term[b]
            for s in range(1, 20):
                u = s / 20.0
                px, py = ax + (bx - ax) * u, ay + (by - ay) * u + 14 * math.sin(math.pi * u)
                d = math.hypot(px - x, py - y)
                if d < bd:
                    best, bd = i, d
        if best is not None:
            self.wires.pop(best)
            self.draw()

    # ---------------- circuit --------------------------------------------
    def _netroot(self):
        """union-find over terminals joined by cables"""
        p = {k: k for k in self.term}

        def find(a):
            while p[a] != a:
                p[a] = p[p[a]]
                a = p[a]
            return a
        # the TFT source is printed onto the Z track (Figs. 10 and 12)
        p[find("TS")] = find("Z")
        for a, b in self.wires:
            ra, rb = find(a), find(b)
            if ra != rb:
                p[ra] = rb
        return {k: find(k) for k in p}

    def build_and_solve(self):
        root = self._netroot()
        ck = Circuit()

        def n(name):
            return root[name]

        keep = []
        if "sheet" in self.placed:
            # the taps exist as points on the film whether or not a silver
            # line has been drawn; the line is what makes them contactable,
            # and it brings its own contact resistance with it
            for which, segs, taps, ends, drawn, rc in (
                    (1, self.sheet.segs1(), TAPS1, ("Z", "V"),
                     self.sheet.drawn1, self.sheet.rc1),
                    (2, self.sheet.segs2(), TAPS2, ("Z", "W"),
                     self.sheet.drawn2, self.sheet.rc2)):
                node = [n(ends[0])] + ["r%dn%d" % (which, i + 1)
                                       for i in range(7)] + [n(ends[1])]
                for i in range(8):
                    ck.R(node[i], node[i + 1], segs[i])
                if drawn:
                    for i, nm in enumerate(taps):
                        ck.R(n(nm), node[i + 1], rc[i])
            for i in range(3):
                ck.R(n("T%da" % (i + 1)), n("T%db" % (i + 1)),
                     self.sheet.Rt[i] * (1 + self.rng.gauss(0, 4e-4)))
            ck.NL(n("TD"), n("TS"), n("TG"), self.tft)
            ck.R(n("TG"), n("TS"), 1e8)
            keep += [n("TD"), n("TS"), n("TG")]
            if self.RL:
                ck.R(n("TD"), n("VIN"), self.RL)
        if "batt" in self.placed:
            ck.V(n("BP"), n("BC"), self.vbat_p)
            ck.V(n("BC"), n("BM"), self.vbat_m)
        if "jfet" in self.placed:
            ck.NL(n("JD"), n("JS"), n("JG"), self.jfet)
            ck.R(n("JG"), n("JS"), 1e9)
            keep += [n("JD"), n("JS"), n("JG")]

        info = None
        have_probes = ("meter" in self.placed and self.meter.red
                       and self.meter.black)
        if have_probes:
            rr, bb = n(self.meter.red), n(self.meter.black)
            save = (self.meter.red, self.meter.black)
            self.meter.red, self.meter.black = rr, bb
            info = self.meter.element(ck)
            keep += [rr, bb]
        v = ck.solve(self._guess, keep)
        self._guess = v
        if have_probes:
            self.meter.read(v, info)
            self.meter.red, self.meter.black = save
        else:
            self.meter.reading = None
        self.volt = {k: v.get(root[k], 0.0) for k in self.term}
        return v

    # ---------------- drawing ---------------------------------------------
    def draw(self):
        c = self.c
        c.delete("all")
        vis = self.visible()
        if "sheet" in self.placed:
            c.create_rectangle(30, 40, 640, 700, fill="#fdfcf7", outline="#ddd6c8")
            c.create_text(40, 52, anchor="nw", fill="#b4ab99",
                          text=T("printed circuit sheet"))
            # TFT block
            c.create_rectangle(440, 70, 640, 140, fill="#efeadd", outline="#c9c0ad")
            c.create_rectangle(606, 76, 632, 102, fill="#46566c", outline="#2b3a4f")
            c.create_text(445, 76, anchor="nw", fill="#8d8677", text=T("paper TFT"))
            # Z track on top, V and W tracks at the bottom
            c.create_line(150, 175, 450, 175, fill="#b4b8bc", width=7)
            c.create_line(150, 595, 250, 595, fill="#b4b8bc", width=7)
            c.create_line(350, 595, 450, 595, fill="#b4b8bc", width=7)
            # staircases
            self._stair(c, 200, SEG_W, self.sheet.drawn1)
            self._stair(c, 400, SEG_W[::-1], self.sheet.drawn2)
            # test squares
            for i in range(3):
                y = 480 + 60 * i
                c.create_rectangle(535, y - 22, 585, y + 22, fill="#5b5347",
                                   outline="")
                c.create_rectangle(510, y - 22, 535, y + 22, fill="#c9c3b8",
                                   outline="")
                c.create_rectangle(585, y - 22, 610, y + 22, fill="#c9c3b8",
                                   outline="")
        if "board" in self.placed:
            # mini-breadboard (17 x 10, two halves) on its dark blue support, as in Fig. 3
            c.create_rectangle(680, 318, 910, 470, fill="#22378f", outline="#0f1a55")
            for i in range(19):
                for j in range(12):
                    x, y = 688 + i * 12, 324 + j * 12
                    c.create_rectangle(x, y, x + 4, y + 4, fill="#1a2b78", outline="")
            c.create_rectangle(706, 330, 884, 412, fill="#f1efe7", outline="#c9c5b8")
            c.create_rectangle(710, 368, 880, 374, fill="#dedad0", outline="")
            for r0 in range(10):
                for c0 in range(17):
                    x = 715 + c0 * 10
                    y = 336 + r0 * 7 + (6 if r0 >= 5 else 0)
                    c.create_rectangle(x - 1.5, y - 1.5, x + 1.5, y + 1.5,
                                       fill="#3b3a36", outline="")
            c.create_text(684, 458, anchor="w", fill="#c9d0f0",
                          text=T("mini-breadboard"), font=("TkDefaultFont", 8))
        if "jfet" in self.placed:
            for x in (740, 790, 840):
                c.create_line(x, 430, 790 + (x - 790) * 0.25, 412, fill="#b9b9b9", width=2)
            c.create_arc(768, 392, 812, 432, start=0, extent=180,
                         fill="#2b2b2b", outline="#111")
            c.create_text(790, 386, text="T281", fill="#dfe3ea", font=("TkDefaultFont", 7))
        if "batt" in self.placed:
            # two 2 x AA holders stacked one on the other (Fig. 3 item 6, Fig. 7)
            c.create_rectangle(702, 664, 892, 700, fill="#0e0e10", outline="#000")
            c.create_rectangle(694, 656, 884, 692, fill="#1d1d20", outline="#000")
            for k in range(2):
                y = 660 + k * 16
                c.create_rectangle(700, y, 878, y + 13, fill="#c99a2a", outline="#5a4012")
                c.create_rectangle(700 + (130 if k == 0 else 10), y, 738 + (130 if k == 0 else 10), y + 13,
                                   fill="#b7261e", outline="")
            for x, col in ((720, "#c8241e"), (790, "#1a1a1a"), (860, "#1a1a1a")):
                c.create_line(x, 646, x, 656, fill=col, width=3)
            c.create_text(696, 708, anchor="w", fill="#8d8677",
                          text=T("battery pack 4 x 1.5 V"))
        # wires
        for a, b in self.wires:
            ax, ay, _ = self.term[a]
            bx, by, _ = self.term[b]
            pts = []
            for s in range(21):
                u = s / 20.0
                pts += [ax + (bx - ax) * u,
                        ay + (by - ay) * u + 14 * math.sin(math.pi * u)]
            c.create_line(*pts, fill="#3c6ea5", width=3, smooth=True)
        # probes
        for who, col in (("red", "#c02b2b"), ("black", "#222")):
            k = getattr(self.meter, who)
            if k and k in vis:
                x, y, _ = self.term[k]
                c.create_line(x, y, x + (30 if who == "red" else -30), y - 40,
                              fill=col, width=3)
                c.create_oval(x - 7, y - 7, x + 7, y + 7, outline=col, width=2)
        # terminals
        for k, (x, y, lab) in self.term.items():
            if k not in vis:
                continue
            fill = "#e8e3d8" if k != self.pending else "#ffd873"
            c.create_oval(x - 6, y - 6, x + 6, y + 6, fill=fill, outline="#6a6254")
            if lab:
                c.create_text(x - 14, y, text=lab, anchor="e",
                          fill="#e8eef2" if k in ("JG", "JS", "JD") else "#4a443a",
                              font=("TkDefaultFont", 8))
        if self.RL:
            x1, y1, _ = self.term["TD"]
            x2, y2, _ = self.term["VIN"]
            c.create_line(x1, y1 - 22, x2, y2 - 22, fill="#4a4a4a",
                          width=1 + min(6, self.rl_strokes // 3))
            c.create_text((x1 + x2) / 2, y1 - 34, fill="#6a6254",
                          text=T("pencil track"))

    def _stair(self, c, cx, widths, drawn):
        y = STAIR_TOP
        for w in widths:                     # from the Z end downwards
            px = w * 10
            c.create_rectangle(cx - px / 2, y, cx + px / 2, y + 46,
                               fill="#1d1d1d", outline="")
            y += 46
        if drawn:
            for i in range(7):
                yy = STAIR_TOP + 46 * (i + 1)
                c.create_line(cx - 30, yy, cx + 30, yy, fill="#cfd4d8", width=3)

    # ---------------- main loop -------------------------------------------
    def _tick(self):
        dt = 0.06 * self.speed.get()
        self.t_sim += dt
        if self.watch_run:
            self.watch_t += dt
        if "sheet" in self.placed:
            vg = self.volt.get("TG", 0.0) - self.volt.get("TS", 0.0)
            self.tft.advance(dt, vg)
        self.term = self._layout()
        try:
            self.build_and_solve()
        except Exception:
            pass
        self.lbl_disp.config(text=self.meter.display())
        self.lbl_unit.config(text=self.meter.unit())
        self.lbl_fuse.config(text="" if self.meter.fuse_ok
                             else T("FUSE BLOWN - current ranges are dead"))
        self.lbl_watch.config(text="%d:%04.1f" % (int(self.watch_t // 60),
                                                  self.watch_t % 60))
        if self.nb.index(self.nb.select()) == 1:
            self.draw()
        self.after(60, self._tick)


if __name__ == "__main__":
    App().mainloop()
