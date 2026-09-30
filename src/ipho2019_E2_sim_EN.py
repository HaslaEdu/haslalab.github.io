#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPhO 2019 (Israel) - Experimental Problem Q2
"Wiedemann-Franz Law"  -  Virtual laboratory

Single file, standard library only (tkinter).  Same design rules as the
IPhO 2017 / APhO 2022-2025 simulators:

  * the apparatus is drawn from the photographs of the official problem
    sheet (figures 1, 2.a, 2.b, 3, 4, 5) - colours, proportions and
    markings are taken from those images
  * the student assembles and places everything by hand: pours the water,
    screws the rod onto the pot, plugs the thermometer cable, wires the
    heater circuit terminal by terminal, turns the range selectors
  * the simulator NEVER computes or displays a physical result.  Only what
    a real instrument shows appears on screen: the eight thermometer
    digits, the box timer, the two multimeter displays, the stopwatch.
    No conductivity, no gradient, no fit, no hint.

Run:  python ipho2019_E2_sim_KO.py   (EN edition: ipho2019_E2_sim_EN.py)
"""

LANG = "EN"          # the KO edition differs only in this line

import math
import random
import tkinter as tk
from tkinter import ttk

# ==========================================================================
#  i18n
# ==========================================================================
S = {
    "title": ("IPhO 2019  Q2 - 비데만-프란츠 법칙  가상 실험실",
              "IPhO 2019  Q2 - Wiedemann-Franz Law  Virtual Lab"),
    "tab_bench": ("실험대 (B·C·D)", "Bench (B/C/D)"),
    "tab_tubes": ("A. 도체 튜브", "A. Conducting tubes"),
    "tab_info": ("장비 목록", "Equipment"),
    "tray": ("장비 트레이 - 끌어다 놓으세요", "Equipment tray - drag onto the bench"),
    "speed": ("시간 배속", "Time scale"),
    "hold_btn": ("빨간 버튼 누른 채 유지", "hold the red button down"),
    "reset_timer": ("타이머 리셋 (3초 길게 누름)", "reset timer (3 s long press)"),
    "press": ("빨간 버튼 누름", "press the red button"),
    "swap": ("Rod #1 / Rod #2 교체", "swap Rod #1 / Rod #2"),
    "wire_hint": ("단자를 두 번 클릭하면 전선이 연결/제거됩니다",
                  "click two terminals to add or remove a wire"),
    "timer_mode": ("Timer mode", "Timer mode"),
    "cal_ok": ("보정 완료", "calibrated"),
    "cal_no": ("미보정", "not calibrated"),
    "drop_water": ("물병을 냄비 위로 끌어다 놓으면 물이 채워집니다",
                   "drag a bottle onto the pot to fill it"),
    "tube_cu": ("구리 튜브", "Copper tube"),
    "tube_br": ("황동 튜브", "Brass tube"),
    "tube_al": ("알루미늄 튜브", "Aluminum tube"),
    "magnet": ("자석 (1.2 g)", "magnet (1.2 g)"),
    "drop_magnet": ("자석을 튜브 입구로 끌어다 놓으세요",
                    "drag the magnet to the top of a tube"),
    "no_power": ("판독 박스에 12 V 어댑터를 연결하세요 (실험대 탭)",
                 "plug the 12 V adapter into the readout box (bench tab)"),
    "start_stop": ("시작 / 정지", "start / stop"),
    "zero": ("0 으로", "reset to zero"),
    "warn_immerse": ("경고: 막대를 물에 담그지 마시오",
                     "WARNING: do not immerse the rods in water"),
    "note_cal": ("주의: 막대를 냄비에 체결하거나 가열하기 전에 보정하십시오",
                 "note: calibrate BEFORE attaching the rod or heating it"),
    "items": (
        ["1. 구리 튜브 (200.0 mm, 안지름 6.0 mm, 바깥지름 20.0 mm)",
         "2. 황동 튜브 (200.0 mm, 안지름 6.0 mm, 바깥지름 19.0 mm)",
         "3. 알루미늄 튜브 (200.0 mm, 안지름 6.0 mm, 바깥지름 20.0 mm)",
         "4. 영구자석 1.2 g",
         "5. 물 저장조 (뚜껑 안에 열교환기, 2 L 물병 2개)",
         "6. Rod #1 - 구리 막대 지름 20.0 mm, 온도센서 8개 + 내장 히터",
         "7. Rod #2 - 복합 막대 (구리 88 / 황동 50 / 알루미늄 50 / 구리 65 mm)",
         "8. 단열 종단 캡",
         "9. 판독 박스용 12 V DC 전원",
         "10. 디지털 판독 박스 (온도계 8채널 + 스톱워치)",
         "11. 온도계 케이블",
         "12. 전압계 - 20 V DC 위치",
         "13. 전류계 - 10 A DC 위치",
         "14. 전선",
         "15. 히터용 9 V DC 전원"],
        ["1. Copper tube (200.0 mm, 6.0 mm bore, 20.0 mm OD)",
         "2. Brass tube (200.0 mm, 6.0 mm bore, 19.0 mm OD)",
         "3. Aluminum tube (200.0 mm, 6.0 mm bore, 20.0 mm OD)",
         "4. Permanent magnet, 1.2 g",
         "5. Water reservoir (heat exchanger in the cover, 2 x 2 L bottles)",
         "6. Rod #1 - copper rod 20.0 mm dia, 8 sensors + built-in heater",
         "7. Rod #2 - composite rod (Cu 88 / brass 50 / Al 50 / Cu 65 mm)",
         "8. Thermally insulating termination cap",
         "9. 12 V DC supply for the readout box",
         "10. Digital readout box (8 thermometers + stopwatch)",
         "11. Thermometer cable",
         "12. Voltmeter - 20 V DC position",
         "13. Ammeter - 10 A DC position",
         "14. Electrical wires",
         "15. 9 V DC supply for the heater"]),
}


def _(k):
    v = S[k]
    return v[0] if LANG == "KO" else v[1]


# ==========================================================================
#  palette sampled from the official photographs
# ==========================================================================
C_TABLE = "#cdb692"
C_TABLE2 = "#c0a684"
C_WOODLN = "#b99b74"
C_COPPER = "#b0693a"
C_COPPER_HI = "#d99263"
C_BRASS = "#b08d2e"
C_BRASS_HI = "#d8b95c"
C_ALU = "#c0c4c8"
C_ALU_HI = "#e8ebee"
C_FOAM = "#2c2321"
C_FOAM_HI = "#332a27"
C_POT = "#b7bcc0"
C_POT_HI = "#e2e7ea"
C_POT_SH = "#8e9599"
C_BOX = "#0d2ba6"
C_BOX_HI = "#1c47cf"
C_LCD = "#1878e0"
C_LCD_TXT = "#f1fbff"
C_DMM = "#232228"
C_DMM_HI = "#3a3941"
C_DMM_LCD = "#bcc3b3"
C_RED = "#cf2f26"
C_BLACK = "#141414"
C_LABEL = "#f2f2f0"
C_GHOST = "#8d7a5c"

# ==========================================================================
#  physics
# ==========================================================================
G0 = 9.80
MU0 = 4.0e-7 * math.pi
ROD_D = 0.0200
ROD_A = math.pi * (ROD_D / 2.0) ** 2

TUBE_L = 0.200
MAG_M = 1.2e-3

# Descent time per unit conductivity [s m / S], one per tube.  The tubes do
# not share one constant: the brass tube is thinner (19.0 mm OD) and the
# terminal speed is not reached at the very top, so each tube is fitted on
# its own to the official solution (Cu 17.96 s, Al 9.32 s, brass 5.97 s for
# sigma = 5.97e7, 2.89e7, 1.60e7 S/m).
TUBE_K = {"Cu": 17.96 / 5.97e7, "Al": 9.32 / 2.89e7, "Br": 5.97 / 1.60e7}
DROP_JITTER = 0.004             # release-to-release scatter of one drop

ROD1_X = [0.015, 0.040, 0.065, 0.090, 0.115, 0.140, 0.165, 0.190]
ROD1_ORDER = [7, 6, 5, 4, 3, 2, 1, 0]          # display T1..T8
ROD2_X = [0.049, 0.077, 0.099, 0.127, 0.149, 0.177, 0.199, 0.227]
ROD2_ORDER = [0, 1, 2, 3, 4, 5, 6, 7]

END_G = 0.030        # W/K lost through an uncapped end face (Part C)

CU = (8960.0, 386.0)
BRASS = (8500.0, 377.0)
ALU = (2700.0, 900.0)


def thomas(a, b, c, d):
    n = len(d)
    cp = [0.0] * n
    dp = [0.0] * n
    cp[0] = c[0] / b[0]
    dp[0] = d[0] / b[0]
    for i in range(1, n):
        m = b[i] - a[i] * cp[i - 1]
        cp[i] = (c[i] / m) if i < n - 1 else 0.0
        dp[i] = (d[i] - a[i] * dp[i - 1]) / m
    x = [0.0] * n
    x[-1] = dp[-1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x


class Rod:
    """1-D transient conduction, backward Euler, tridiagonal solve."""

    def __init__(self, segs, dx=0.001, mass=None, T0=22.7):
        self.L = sum(s[0] for s in segs)
        n = int(round(self.L / dx)) + 1
        self.n = n
        self.dx = self.L / (n - 1)
        self.x = [i * self.dx for i in range(n)]
        edges = []
        acc = 0.0
        for s in segs:
            acc += s[0]
            edges.append(acc)
        k = [0.0] * n
        rho = [0.0] * n
        cp = [0.0] * n
        for i, xi in enumerate(self.x):
            j = 0
            while j < len(edges) - 1 and xi > edges[j] - 1e-9:
                j += 1
            k[i], rho[i], cp[i] = segs[j][1], segs[j][2], segs[j][3]
        self.dxl = [self.dx] * n
        self.dxl[0] *= 0.5
        self.dxl[-1] *= 0.5
        self.C = [self.dxl[i] * ROD_A * rho[i] * cp[i] for i in range(n)]
        if mass is not None:
            tot = sum(self.dxl[i] * ROD_A * rho[i] for i in range(n))
            f = mass / tot
            self.C = [v * f for v in self.C]
        self.G = [2.0 * k[i] * k[i + 1] / (k[i] + k[i + 1]) * ROD_A / self.dx
                  for i in range(n - 1)]
        self.T = [T0] * n
        self._heat_n = max(1, int(0.015 / self.dx))

    def step(self, dt, P, attached, Tw, Tamb, U, Rc, end_g=0.0):
        n = self.n
        a = [0.0] * n
        c = [0.0] * n
        b = [self.C[i] / dt + U * self.dxl[i] for i in range(n)]
        d = [self.C[i] / dt * self.T[i] + U * self.dxl[i] * Tamb
             for i in range(n)]
        for i in range(n - 1):
            b[i] += self.G[i]
            c[i] = -self.G[i]
            b[i + 1] += self.G[i]
            a[i + 1] = -self.G[i]
        if P > 0.0:
            hs = sum(self.dxl[:self._heat_n])
            for i in range(self._heat_n):
                d[i] += P * self.dxl[i] / hs
        if attached:
            b[-1] += 1.0 / Rc
            d[-1] += Tw / Rc
        elif end_g > 0.0:                 # bare end face, no insulating cap
            b[-1] += end_g
            d[-1] += end_g * Tamb
        self.T = thomas(a, b, c, d)
        return (self.T[-1] - Tw) / Rc if attached else 0.0

    def at(self, pos):
        u = pos / self.dx
        i = int(u)
        if i >= self.n - 1:
            return self.T[-1]
        f = u - i
        return self.T[i] * (1 - f) + self.T[i + 1] * f


# --------------------------------------------------------------------------
#  small linear solver (Gaussian elimination) for the heater circuit
# --------------------------------------------------------------------------
def solve(M, rhs):
    n = len(rhs)
    A = [row[:] + [rhs[i]] for i, row in enumerate(M)]
    for col in range(n):
        p = max(range(col, n), key=lambda r: abs(A[r][col]))
        if abs(A[p][col]) < 1e-14:
            return None
        A[col], A[p] = A[p], A[col]
        pv = A[col][col]
        for r in range(n):
            if r == col:
                continue
            f = A[r][col] / pv
            if f:
                for cc in range(col, n + 1):
                    A[r][cc] -= f * A[col][cc]
    return [A[i][n] / A[i][i] for i in range(n)]


class Circuit:
    """
    Terminals:
       PS+  PS-      9 V supply (emf, internal resistance)
       H1   H2       heater (red wires of the rod)
       A1   ACOM     ammeter
       V1   VCOM     voltmeter
    Wires are unordered pairs of terminal names.  Modified nodal analysis
    with one voltage source gives the true reading of every instrument, so
    a wrong circuit gives a wrong (but physical) reading.
    """
    TERMS = ["PS+", "PS-", "H1", "H2", "A1", "ACOM", "V1", "VCOM"]

    def __init__(self, emf, r_int, r_heat):
        self.emf = emf
        self.r_int = r_int
        self.r_heat = r_heat
        self.wires = []
        self.amm_range = "OFF"
        self.volt_range = "OFF"

    def toggle(self, t1, t2):
        key = tuple(sorted((t1, t2)))
        for w in self.wires:
            if tuple(sorted(w)) == key:
                self.wires.remove(w)
                return
        self.wires.append((t1, t2))

    # ------------------------------------------------------------------ #
    def _r_of(self, kind):
        if kind == "A":
            if self.amm_range == "10A":
                return 0.012
            if self.amm_range in ("200m", "20m", "2000u", "200u"):
                return 2.0
            if self.amm_range == "OFF":
                return None
            return 1.0e7          # voltage / resistance ranges
        if self.volt_range in ("1000", "200", "20", "2000m", "200m"):
            return 1.0e7
        if self.volt_range == "OFF":
            return None
        if self.volt_range == "10A":
            return 0.012
        return 1.0e7

    def solve(self):
        """Return dict with heater power and the two meter readings."""
        par = {t: t for t in self.TERMS}

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x

        for t1, t2 in self.wires:
            a, b = find(t1), find(t2)
            if a != b:
                par[a] = b
        nodes = sorted({find(t) for t in self.TERMS})
        idx = {nd: i for i, nd in enumerate(nodes)}
        nn = len(nodes)

        comps = []                    # (nodeA, nodeB, resistance)
        comps.append((find("H1"), find("H2"), self.r_heat))
        ra = self._r_of("A")
        if ra is not None:
            comps.append((find("A1"), find("ACOM"), ra))
        rv = self._r_of("V")
        if rv is not None:
            comps.append((find("V1"), find("VCOM"), rv))
        # supply: ideal source between PS- (=n_m) and internal node, then r_int
        # model with an extra node "PSX"
        psx = "PSX"
        idx[psx] = nn
        nn += 1
        comps.append((psx, find("PS+"), self.r_int))

        size = nn + 1                 # + source current
        M = [[0.0] * size for _ in range(size)]
        rhs = [0.0] * size
        for a, b, R in comps:
            ia, ib = idx[a], idx[b]
            g = 1.0 / R
            M[ia][ia] += g
            M[ib][ib] += g
            M[ia][ib] -= g
            M[ib][ia] -= g
        for i in range(nn):             # 1 nS leak: an unwired meter or a
            M[i][i] += 1e-9             # loose node must not make M singular
        ip, im = idx[psx], idx[find("PS-")]
        M[ip][nn] += 1.0
        M[im][nn] -= 1.0
        M[nn][ip] += 1.0
        M[nn][im] -= 1.0
        rhs[nn] = self.emf
        gnd = idx[find("PS-")]
        for j in range(size):
            M[gnd][j] = 0.0
        M[gnd][gnd] = 1.0
        rhs[gnd] = 0.0

        sol = solve(M, rhs)
        if sol is None:
            return dict(P=0.0, I=0.0, V=0.0, ok=False)
        v = {nd: sol[idx[nd]] for nd in idx}
        vh = v[find("H1")] - v[find("H2")]
        P = vh * vh / self.r_heat
        I = 0.0
        if ra is not None:
            I = (v[find("A1")] - v[find("ACOM")]) / ra
        Vm = v[find("V1")] - v[find("VCOM")]
        return dict(P=P, I=I, V=Vm, ok=True)


class Lab:
    """The whole Q2 bench."""
    DT = 1.0

    def __init__(self, seed=None):
        rng = random.Random(seed)
        self.rng = rng
        self.T_amb = rng.uniform(22.4, 23.1)
        self.T_water = self.T_amb
        self.C_water = 4.0 * 4186.0 + 900.0
        self.U = rng.uniform(0.190, 0.220)
        self.Rc = rng.uniform(0.55, 0.72)
        self.k_cu = rng.uniform(378.0, 392.0)
        self.k_br = rng.uniform(115.0, 125.0)
        self.k_al = rng.uniform(230.0, 242.0)
        self.mass_rod1 = 0.58

        self.circ = Circuit(rng.uniform(8.92, 9.08),
                            rng.uniform(1.45, 1.75),
                            rng.uniform(11.0, 11.6))

        self.sigma = {"Cu": rng.uniform(5.85e7, 6.08e7),
                      "Al": rng.uniform(2.80e7, 2.98e7),
                      "Br": rng.uniform(1.55e7, 1.67e7)}

        self.rod = {
            1: Rod([(0.200, self.k_cu) + CU], mass=self.mass_rod1,
                   T0=self.T_amb),
            2: Rod([(0.088, self.k_cu) + CU, (0.050, self.k_br) + BRASS,
                    (0.050, self.k_al) + ALU, (0.065, self.k_cu) + CU],
                   T0=self.T_amb)}
        self.off = {r: [rng.gauss(0.0, 0.16) for _ in range(8)]
                    for r in (1, 2)}
        self.calib = {1: None, 2: None}       # offsets the box learnt

        # placement / state
        self.water = 0                 # bottles poured (0,1,2)
        self.lid = False
        self.place = {1: "table", 2: "tray"}      # tray|table|pot
        self.cap = {1: False, 2: False}   # one cap in the kit, starts in the tray
        self.cable_box = False
        self.cable_rod = 0             # 0 = unplugged, 1 or 2
        self.adapter = False
        self.on_bench = set()
        self.t = 0.0
        self.watch = 0.0
        self.watch_run = False
        self.wired_rod = 0
        self.hold = False              # display frozen
        self.heat_time = {1: 0.0, 2: 0.0}

    # ------------------------------------------------------------------ #
    def fall_time(self, tube):
        t = TUBE_K[tube] * self.sigma[tube]
        return t * (1.0 + self.rng.gauss(0.0, DROP_JITTER))

    # ------------------------------------------------------------------ #
    def power_to(self, rod):
        if self.place[rod] == "tray":
            return 0.0
        res = self.circ.solve()
        return max(res["P"], 0.0) if res["ok"] else 0.0

    def advance(self, seconds):
        steps = max(1, int(round(seconds / self.DT)))
        dt = seconds / steps
        for _ in range(steps):
            for r in (1, 2):
                P = self.power_to(r) if self.wired_rod == r else 0.0
                if P > 0:
                    self.heat_time[r] += dt
                att = (self.place[r] == "pot")
                eg = 0.0 if (att or self.cap[r]) else END_G
                fl = self.rod[r].step(dt, P, att, self.T_water, self.T_amb,
                                      self.U, self.Rc, eg)
                self.T_water += fl * dt / self.C_water
            self.T_water -= (self.T_water - self.T_amb) * dt * 0.9 / \
                self.C_water
        self.t += seconds
        if self.watch_run or self.cable_rod:
            self.watch += seconds

    # ------------------------------------------------------------------ #
    def read_sensors(self):
        r = self.cable_rod
        if not r:
            return None
        xs = ROD1_X if r == 1 else ROD2_X
        order = ROD1_ORDER if r == 1 else ROD2_ORDER
        cal = self.calib[r]
        out = []
        for j, i in enumerate(order):
            v = self.rod[r].at(xs[i]) + self.off[r][j]
            if cal:
                v -= cal[j]
            v += self.rng.gauss(0.0, 0.010)
            out.append(round(v, 2))
        return out

    def raw(self, r):
        xs = ROD1_X if r == 1 else ROD2_X
        order = ROD1_ORDER if r == 1 else ROD2_ORDER
        return [self.rod[r].at(xs[i]) + self.off[r][j]
                for j, i in enumerate(order)]

    def press(self):
        """The one red button on the box.  With the thermometer cable in,
        it freezes / releases the display; without it the box is a timer
        (start -> stop -> clear)."""
        if not self.adapter:
            return
        if self.cable_rod:
            self.hold = not self.hold
        elif not self.watch_run and self.watch == 0:
            self.watch_run = True
        elif self.watch_run:
            self.watch_run = False
        else:
            self.watch = 0.0

    def calibrate(self):
        """The box learns the spread of the eight sensors right now.  On a
        rod at one uniform temperature that removes the offsets; on a rod
        with a gradient it bakes the gradient in."""
        r = self.cable_rod
        if r:
            raw = self.raw(r)
            m = sum(raw) / len(raw)
            self.calib[r] = [v - m for v in raw]

    def meters(self):
        res = self.circ.solve()
        if not res["ok"]:
            return 0.0, 0.0
        i = res["I"] + self.rng.gauss(0.0, 0.004)
        v = res["V"] + self.rng.gauss(0.0, 0.006)
        return i, v


# ==========================================================================
#  drawing helpers
# ==========================================================================
def rr(cv, x0, y0, x1, y1, r, **kw):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0),
                       (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(0, 91, 15):
            a = math.radians(a0 + k)
            pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
    return cv.create_polygon(pts, smooth=False, **kw)


def wood(cv, x0, y0, x1, y1):
    cv.create_rectangle(x0, y0, x1, y1, fill=C_TABLE, outline="")
    y = y0 + 18
    n = 0
    while y < y1:
        cv.create_line(x0, y, x1, y, fill=C_WOODLN, width=1)
        y += 34 + (n % 3) * 9
        n += 1
    cv.create_rectangle(x0, y0, x1, y0 + 6, fill=C_TABLE2, outline="")


def grad_rect(cv, x0, y0, x1, y1, c_lo, c_hi, horiz=False, n=14, tags=()):
    """cheap linear gradient made of stripes"""
    r0, g0, b0 = cv.winfo_rgb(c_lo)
    r1, g1, b1 = cv.winfo_rgb(c_hi)
    for i in range(n):
        f = i / (n - 1.0)
        col = "#%02x%02x%02x" % (int((r0 + (r1 - r0) * f) / 256),
                                 int((g0 + (g1 - g0) * f) / 256),
                                 int((b0 + (b1 - b0) * f) / 256))
        if horiz:
            a = x0 + (x1 - x0) * i / n
            b = x0 + (x1 - x0) * (i + 1) / n
            cv.create_rectangle(a, y0, b + 1, y1, fill=col, outline="",
                                tags=tags)
        else:
            a = y0 + (y1 - y0) * i / n
            b = y0 + (y1 - y0) * (i + 1) / n
            cv.create_rectangle(x0, a, x1, b + 1, fill=col, outline="",
                                tags=tags)


def metal_tube(cv, x0, y0, x1, y1, base, hi, tags=()):
    grad_rect(cv, x0, y0, x1, y1, base, hi, horiz=False, n=16, tags=tags)
    grad_rect(cv, x0, (y0 + y1) / 2, x1, y1, hi, base, horiz=False, n=16,
              tags=tags)
    cv.create_rectangle(x0, y0, x1, y1, outline="#3a3a3a", tags=tags)


# ==========================================================================
#  Bench tab  (parts B, C, D)
# ==========================================================================
TRAY_ITEMS = [
    ("pot", "5"), ("water", "5"), ("rod1", "6"), ("rod2", "7"),
    ("cap", "8"), ("adapter", "9"), ("box", "10"), ("cable", "11"),
    ("volt", "12"), ("amm", "13"), ("psu", "15"),
]

SLOTS = {
    "pot":     (690, 320, 200, 150),
    "rodtable": (300, 505, 260, 48),
    "box":     (195, 195, 205, 116),
    "adapter": (185, 345, 120, 60),
    "amm":     (895, 430, 132, 184),
    "volt":    (1055, 430, 132, 184),
    "psu":     (1030, 190, 130, 66),
}

AMM_POS = ["OFF", "10A", "200m", "20m", "2000u", "200u", "1000", "200", "20"]
VOLT_POS = ["OFF", "1000", "200", "20", "2000m", "200m", "10A", "200u"]

TERM_XY = {
    "PS+": (1078, 232), "PS-": (1078, 254),
    "H1": None, "H2": None,               # follow the rod
    "A1": (933, 480), "ACOM": (933, 504),
    "V1": (1093, 480), "VCOM": (1093, 504),
}


class Bench(ttk.Frame):
    W, H = 1220, 700

    def __init__(self, master, lab, app):
        super().__init__(master)
        self.lab = lab
        self.app = app
        self.cv = tk.Canvas(self, width=self.W, height=self.H,
                            highlightthickness=0, bg=C_TABLE)
        self.cv.pack(side="top", fill="both", expand=True)
        bar = ttk.Frame(self)
        bar.pack(side="top", fill="x", pady=3)
        ttk.Label(bar, text=_("speed")).pack(side="left", padx=(6, 2))
        self.speed = tk.IntVar(value=1)
        for lb, v in (("1x", 1), ("10x", 10), ("60x", 60), ("300x", 300),
                      ("1200x", 1200)):
            ttk.Radiobutton(bar, text=lb, value=v,
                            variable=self.speed).pack(side="left")
        self.hold_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text=_("hold_btn"), variable=self.hold_var,
                        command=self.on_hold).pack(side="left", padx=12)
        ttk.Button(bar, text=_("reset_timer"),
                   command=self.reset_timer).pack(side="left")
        ttk.Label(bar, text="   " + _("wire_hint")).pack(side="left")

        self.drag = None
        self.sel_term = None
        self.tray = list(TRAY_ITEMS)
        self.cv.bind("<Button-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_move)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.knob_drag = None
        self.redraw()

    # ------------------------------------------------------------------ #
    def on_hold(self):
        self.lab.hold = False          # the latch is for calibration only

    def reset_timer(self):
        self.lab.watch = 0.0

    # ------------------------------------------------------------------ #
    def tray_slot(self, i):
        return 40 + i * 104, self.H - 62

    def hit_tray(self, x, y):
        for i, (name, _n) in enumerate(self.tray):
            cx, cy = self.tray_slot(i)
            if abs(x - cx) < 46 and abs(y - cy) < 40:
                return name
        return None

    def hit_slot(self, x, y):
        for name, (cx, cy, w, h) in SLOTS.items():
            if abs(x - cx) < w / 2 + 26 and abs(y - cy) < h / 2 + 26:
                return name
        return None

    def hit_term(self, x, y):
        for t, p in self.term_xy().items():
            if p and (x - p[0]) ** 2 + (y - p[1]) ** 2 < 100:
                return t
        return None

    def term_xy(self):
        d = dict(TERM_XY)
        lab = self.lab
        for r in (1, 2):
            if lab.place[r] == "pot":
                d["H1"] = (670, 100)
                d["H2"] = (692, 100)
            elif lab.place[r] == "table" and r == self._rod_on_table():
                cx, cy, w, h = SLOTS["rodtable"]
                d["H1"] = (cx - w / 2 - 12, cy - 8)
                d["H2"] = (cx - w / 2 - 12, cy + 8)
        return d

    def _rod_on_table(self):
        for r in (1, 2):
            if self.lab.place[r] == "table":
                return r
        return 0

    def _rod_on_pot(self):
        for r in (1, 2):
            if self.lab.place[r] == "pot":
                return r
        return 0

    # ------------------------------------------------------------------ #
    def on_press(self, ev):
        x, y = ev.x, ev.y
        lab = self.lab
        # knobs
        for m, (cx, cy) in (("amm", (SLOTS["amm"][0], SLOTS["amm"][1] + 8)),
                            ("volt", (SLOTS["volt"][0],
                                      SLOTS["volt"][1] + 8))):
            if m in lab.on_bench and (x - cx) ** 2 + (y - cy) ** 2 < 34 ** 2:
                self.knob_drag = m
                self.turn_knob(m, x, y)
                return
        # red button of the box
        if "box" in lab.on_bench:
            bx, by, bw, bh = SLOTS["box"]
            if abs(x - bx) < 16 and abs(y - (by + bh / 2 + 12)) < 12:
                self.press_button()
                return
        t = self.hit_term(x, y)
        if t:
            if self.sel_term and self.sel_term != t:
                lab.circ.toggle(self.sel_term, t)
                self.sel_term = None
                self.sync_heater()
            else:
                self.sel_term = t
            self.redraw()
            return
        n = self.hit_tray(x, y)
        if n:
            self.drag = dict(name=n, x=x, y=y, from_tray=True)
            self.redraw()
            return
        # pick a placed object
        for name in ("rod1", "rod2", "cap", "cable"):
            if self.grab_test(name, x, y):
                self.drag = dict(name=name, x=x, y=y, from_tray=False)
                self.redraw()
                return

    def grab_test(self, name, x, y):
        lab = self.lab
        if name in ("rod1", "rod2"):
            r = 1 if name == "rod1" else 2
            if lab.place[r] == "table":
                cx, cy, w, h = SLOTS["rodtable"]
                return abs(x - cx) < w / 2 and abs(y - cy) < h / 2
            if lab.place[r] == "pot":
                return abs(x - 690) < 40 and 70 < y < 300
        if name == "cap":
            r = self._rod_on_table()
            if r and lab.cap[r]:
                cx, cy, w, h = SLOTS["rodtable"]
                return abs(x - (cx + w / 2 - 10)) < 16 and abs(y - cy) < 22
        if name == "cable" and lab.cable_box:
            return abs(x - 300) < 20 and abs(y - 250) < 14
        return False

    def on_move(self, ev):
        if self.knob_drag:
            self.turn_knob(self.knob_drag, ev.x, ev.y)
            return
        if self.drag:
            self.drag["x"], self.drag["y"] = ev.x, ev.y
            self.redraw()

    def on_release(self, ev):
        self.knob_drag = None
        if not self.drag:
            return
        x, y = ev.x, ev.y
        name = self.drag["name"]
        lab = self.lab
        slot = self.hit_slot(x, y)
        if name == "water":
            if slot == "pot" and "pot" in lab.on_bench and lab.water < 2:
                lab.water += 1
                if lab.water == 2:
                    lab.lid = True
        elif name in ("rod1", "rod2"):
            r = 1 if name == "rod1" else 2
            if slot == "pot" and lab.lid and lab.water == 2 \
                    and not self._rod_on_pot():
                lab.place[r] = "pot"
                if lab.cap[r]:
                    lab.cap[r] = False              # the cap comes off
                    if not any(t[0] == "cap" for t in self.tray):
                        self.tray.append(("cap", "8"))
            elif slot == "rodtable" and (self._rod_on_table() in (0, r)):
                lab.place[r] = "table"
            elif self.drag["from_tray"]:
                lab.place[r] = "table"
        elif name == "cap":
            r = self._rod_on_table()
            end = SLOTS["rodtable"][0] + SLOTS["rodtable"][2] / 2
            if r and abs(x - end) < 60 and abs(y - SLOTS["rodtable"][1]) < 50:
                lab.cap[r] = True
            else:
                if r:
                    lab.cap[r] = False
                if not any(t[0] == "cap" for t in self.tray):
                    self.tray.append(("cap", "8"))      # back in the tray
                self.drag["from_tray"] = False
        elif name == "cable":
            bx, by, bw, bh = SLOTS["box"]
            if abs(x - bx) < bw and abs(y - by) < bh:
                lab.cable_box = True
                if self.hold_var.get() and lab.cable_rod:
                    lab.calibrate()
            elif slot == "rodtable" or (abs(x - 780) < 60 and y < 260):
                r = self._rod_on_table() if slot == "rodtable" \
                    else self._rod_on_pot()
                lab.cable_rod = r
                if self.hold_var.get() and lab.cable_box:
                    lab.calibrate()
            else:
                lab.cable_box = False
                lab.cable_rod = 0
        elif name in ("pot", "box", "adapter", "amm", "volt", "psu"):
            if slot == name or self.drag["from_tray"]:
                lab.on_bench.add(name)
                if name == "adapter":
                    lab.adapter = True
        if self.drag["from_tray"]:
            self.tray = [t for t in self.tray if t[0] != name] \
                if name not in ("water",) or lab.water >= 2 else self.tray
        self.drag = None
        self.sync_heater()
        self.redraw()

    def sync_heater(self):
        """the rod whose red wires are in the circuit gets the power"""
        lab = self.lab
        used = any(t in ("H1", "H2") for w in lab.circ.wires for t in w)
        lab.wired_rod = (self._rod_on_pot() or self._rod_on_table()) \
            if used else 0

    def press_button(self):
        self.lab.press()

    def turn_knob(self, m, x, y):
        cx, cy = (SLOTS[m][0], SLOTS[m][1] + 8)
        a = math.degrees(math.atan2(y - cy, x - cx))
        pos = AMM_POS if m == "amm" else VOLT_POS
        n = len(pos)
        k = int(round(((a + 90) % 360) / 360.0 * n)) % n
        if m == "amm":
            self.lab.circ.amm_range = pos[k]
        else:
            self.lab.circ.volt_range = pos[k]
        self.redraw()

    # ------------------------------------------------------------------ #
    def tick(self, dt_real):
        self.lab.advance(dt_real * self.speed.get())
        self.redraw()

    # ------------------------------------------------------------------ #
    def redraw(self):
        cv = self.cv
        cv.delete("all")
        lab = self.lab
        wood(cv, 0, 0, self.W, self.H - 110)
        cv.create_rectangle(0, self.H - 110, self.W, self.H,
                            fill="#3a3630", outline="")
        cv.create_text(12, self.H - 104, anchor="nw", text=_("tray"),
                       fill="#d9d2c4", font=("", 9))
        cv.create_text(self.W - 12, 12, anchor="ne",
                       text=_("warn_immerse") + "\n" + _("note_cal"),
                       fill="#7a5b3a", font=("", 9), justify="right")

        for name, (cx, cy, w, h) in SLOTS.items():
            if name not in lab.on_bench and name not in ("rodtable",):
                cv.create_rectangle(cx - w / 2, cy - h / 2, cx + w / 2,
                                    cy + h / 2, dash=(4, 4),
                                    outline=C_GHOST)
                cv.create_text(cx, cy, text=name, fill=C_GHOST,
                               font=("", 9))
        if not self._rod_on_table():
            cx, cy, w, h = SLOTS["rodtable"]
            cv.create_rectangle(cx - w / 2, cy - h / 2, cx + w / 2,
                                cy + h / 2, dash=(4, 4), outline=C_GHOST)

        if "pot" in lab.on_bench:
            self.draw_pot(cv)
        if "psu" in lab.on_bench:
            self.draw_psu(cv)
        if "adapter" in lab.on_bench:
            self.draw_adapter(cv)
        if "box" in lab.on_bench:
            self.draw_box(cv)
        for m in ("amm", "volt"):
            if m in lab.on_bench:
                self.draw_dmm(cv, m)
        r = self._rod_on_table()
        if r:
            self.draw_rod_table(cv, r)
        r = self._rod_on_pot()
        if r:
            self.draw_rod_pot(cv, r)
        self.draw_wires(cv)
        self.draw_tray(cv)
        if self.drag:
            self.draw_icon(cv, self.drag["name"], self.drag["x"],
                           self.drag["y"], 1.0, ghost=True)

    # ------------------------------------------------------------------ #
    def draw_tray(self, cv):
        for i, (name, num) in enumerate(self.tray):
            cx, cy = self.tray_slot(i)
            cv.create_rectangle(cx - 46, cy - 40, cx + 46, cy + 40,
                                fill="#4a453c", outline="#6b6558")
            self.draw_icon(cv, name, cx, cy, 0.55)
            cv.create_text(cx - 42, cy - 36, anchor="nw", text=num,
                           fill="#ffe9a8", font=("", 9, "bold"))

    def draw_icon(self, cv, name, x, y, s=1.0, ghost=False):
        if name == "pot":
            cv.create_oval(x - 46 * s, y - 26 * s, x + 46 * s, y + 26 * s,
                           fill=C_POT, outline=C_POT_SH)
            cv.create_oval(x - 36 * s, y - 19 * s, x + 36 * s, y + 15 * s,
                           fill=C_POT_HI, outline="")
        elif name == "water":
            cv.create_rectangle(x - 12 * s, y - 34 * s, x + 12 * s,
                                y + 30 * s, fill="#bcd8ee", outline="#88a8c0")
            cv.create_rectangle(x - 8 * s, y - 42 * s, x + 8 * s, y - 34 * s,
                                fill="#1b5fc0", outline="")
        elif name in ("rod1", "rod2"):
            cv.create_rectangle(x - 48 * s, y - 12 * s, x + 48 * s,
                                y + 12 * s, fill=C_FOAM, outline="#000")
            cv.create_rectangle(x - 16 * s, y - 7 * s, x + 22 * s, y + 7 * s,
                                fill=C_LABEL, outline="#999")
            cv.create_text(x + 3 * s, y, text="Rod #%s" % name[-1],
                           font=("", int(7 * s + 3)), fill="#222")
        elif name == "cap":
            cv.create_rectangle(x - 16 * s, y - 18 * s, x + 16 * s,
                                y + 18 * s, fill="#cfc7b4", outline="#8b8570")
            cv.create_oval(x - 13 * s, y - 15 * s, x + 13 * s, y + 15 * s,
                           fill=C_FOAM, outline="")
        elif name == "adapter":
            cv.create_rectangle(x - 22 * s, y - 16 * s, x + 22 * s,
                                y + 16 * s, fill="#1e1e20", outline="#000")
            cv.create_line(x + 22 * s, y, x + 40 * s, y + 10 * s,
                           fill="#111", width=3)
        elif name == "box":
            rr(cv, x - 40 * s, y - 26 * s, x + 40 * s, y + 26 * s, 6 * s,
               fill=C_BOX, outline="#061a63")
            cv.create_rectangle(x - 30 * s, y - 17 * s, x + 30 * s,
                                y + 12 * s, fill=C_LCD, outline="#000")
        elif name == "cable":
            cv.create_line(x - 34 * s, y + 8 * s, x - 6 * s, y - 12 * s,
                           x + 22 * s, y + 10 * s, smooth=True,
                           fill="#c9c3b2", width=int(4 * s + 2))
            cv.create_rectangle(x + 20 * s, y + 2 * s, x + 36 * s,
                                y + 16 * s, fill="#bdb7a6", outline="#7c765f")
        elif name in ("amm", "volt"):
            rr(cv, x - 24 * s, y - 38 * s, x + 24 * s, y + 38 * s, 5 * s,
               fill=C_DMM, outline="#000")
            cv.create_rectangle(x - 17 * s, y - 32 * s, x + 17 * s,
                                y - 16 * s, fill=C_DMM_LCD, outline="#000")
            cv.create_oval(x - 14 * s, y - 10 * s, x + 14 * s, y + 18 * s,
                           fill="#1a1a1c", outline="#000")
        elif name == "psu":
            cv.create_rectangle(x - 30 * s, y - 16 * s, x + 30 * s,
                                y + 16 * s, fill="#1e1e20", outline="#000")
            cv.create_text(x, y, text="9V DC", fill="#cfcfcf",
                           font=("", int(6 * s + 3)))

    # ------------------------------------------------------------------ #
    def draw_pot(self, cv):
        cx, cy, w, h = SLOTS["pot"]
        lab = self.lab
        R, Rb = 100, 82
        cv.create_oval(cx - R - 8, cy + 34, cx + R + 8, cy + 64,
                       fill="#9a8d78", outline="")
        body = []
        for i in range(0, 21):
            f = i / 20.0
            body.append((cx - R + (R - Rb) * f, cy - 18 + 62 * f))
        pts = []
        for x, y in body:
            pts += [x, y]
        for x, y in reversed(body):
            pts += [2 * cx - x, y]
        cv.create_polygon(pts, fill=C_POT, outline=C_POT_SH)
        grad_rect(cv, cx - R + 10, cy - 16, cx + R - 10, cy + 42,
                  C_POT_SH, C_POT_HI, horiz=True, n=20)
        grad_rect(cv, cx - 10, cy - 16, cx + R - 10, cy + 42,
                  C_POT_HI, C_POT_SH, horiz=True, n=20)
        cv.create_oval(cx - Rb, cy + 30, cx + Rb, cy + 56, fill=C_POT,
                       outline=C_POT_SH)
        cv.create_oval(cx - R, cy - 34, cx + R, cy - 2, fill=C_POT_HI,
                       outline=C_POT_SH)
        if not lab.lid:
            cv.create_oval(cx - R + 10, cy - 30, cx + R - 10, cy - 6,
                           fill="#7f868b", outline="")
            if lab.water:
                k = 6 + 6 * lab.water
                cv.create_oval(cx - R + 12 + k, cy - 27 + k * 0.3,
                               cx + R - 12 - k, cy - 9 + k * 0.3,
                               fill="#a8cfe8", outline="#7fb0d0")
            for i in range(14):                      # heat exchanger fins
                fx = cx - 60 + i * 9
                cv.create_line(fx, cy - 26, fx, cy - 12, fill="#aeb4b8")
        else:
            cv.create_oval(cx - R - 4, cy - 44, cx + R + 4, cy - 4,
                           fill=C_POT, outline=C_POT_SH)
            cv.create_oval(cx - R + 22, cy - 39, cx + R - 22, cy - 13,
                           fill=C_POT_HI, outline="")
            cv.create_oval(cx - 11, cy - 32, cx + 11, cy - 20,
                           fill="#9aa2a7", outline="#6f7679")
        cv.create_line(cx - R, cy + 40, cx + R - 20, cy + 40,
                       fill="#e6eaec", width=1)

    def draw_rod_pot(self, cv, r):
        cx, cy, w, h = SLOTS["pot"]
        x0, x1 = cx - 30, cx + 30
        top = 74
        bot = cy - 30
        grad_rect(cv, x0, top, x1, bot, "#171314", C_FOAM_HI, horiz=True,
                  n=12)
        for yy in range(top + 16, int(bot) - 6, 20):
            cv.create_line(x0 + 1, yy, x1 - 1, yy, fill="#0e0b0c")
        cv.create_oval(x0 - 12, bot - 20, x1 + 12, bot + 12, fill="#171314",
                       outline="")
        cv.create_rectangle(x0 + 8, top - 16, x1 - 8, top + 2,
                            fill="#bdb7a6", outline="#7c765f")
        cv.create_rectangle(x0 + 2, top + 26, x1 - 2, top + 54,
                            fill=C_LABEL, outline="#9a9a9a")
        cv.create_text((x0 + x1) / 2, top + 40, text="Rod #%d" % r,
                       fill="#222", font=("", 8))
        for t, dx in (("H1", 10), ("H2", 30)):
            p = (x0 + dx, top + 22)
            cv.create_line(p[0], p[1], p[0] - 60, top + 120, cx + 210,
                           cy + 130, smooth=True, fill=C_RED, width=3)

    def draw_rod_table(self, cv, r):
        cx, cy, w, h = SLOTS["rodtable"]
        x0, x1 = cx - w / 2, cx + w / 2
        lab = self.lab
        cv.create_rectangle(x0 - 4, cy + h / 2, x1 + 4, cy + h / 2 + 7,
                            fill="#9a8d78", outline="")
        grad_rect(cv, x0, cy - h / 2, x1, cy + h / 2, "#171314", C_FOAM_HI,
                  horiz=False, n=12)
        for i in range(8):
            xx = x0 + 18 + i * (w - 34) / 7.0
            cv.create_line(xx, cy - h / 2, xx, cy - h / 2 + 9,
                           fill="#0e0b0c", width=2)
        cv.create_rectangle(cx - 36, cy - 11, cx + 26, cy + 11,
                            fill=C_LABEL, outline="#9a9a9a")
        cv.create_text(cx - 5, cy, text="Rod #%d" % r, font=("", 9),
                       fill="#222")
        cv.create_line(x0 + 4, cy - 6, x0 - 26, cy - 30, fill=C_RED, width=3)
        cv.create_line(x0 + 4, cy + 6, x0 - 26, cy + 22, fill=C_RED, width=3)
        cv.create_rectangle(x1 - 8, cy - 15, x1 + 10, cy + 15,
                            fill="#bdb7a6", outline="#7c765f")
        if lab.cap[r]:
            cv.create_rectangle(x1 + 8, cy - 21, x1 + 44, cy + 21,
                                fill="#cfc7b4", outline="#8b8570")
            cv.create_oval(x1 + 12, cy - 17, x1 + 40, cy + 17,
                           fill="#171314", outline="")

    def draw_adapter(self, cv):
        cx, cy, w, h = SLOTS["adapter"]
        rr(cv, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, 5,
           fill="#1e1e20", outline="#000")
        cv.create_text(cx, cy - 8, text="AC ADAPTOR", fill="#b9b9b9",
                       font=("", 7))
        cv.create_text(cx, cy + 8, text="12V DC", fill="#b9b9b9",
                       font=("", 8, "bold"))
        bx = SLOTS["box"]
        cv.create_line(cx + w / 2, cy, bx[0] - 60, bx[1] + 30, bx[0] - 96,
                       bx[1], smooth=True, fill="#111", width=3)

    def draw_box(self, cv):
        cx, cy, w, h = SLOTS["box"]
        lab = self.lab
        rr(cv, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, 9,
           fill=C_BOX, outline="#061a63")
        rr(cv, cx - w / 2 + 6, cy - h / 2 + 5, cx + w / 2 - 6,
           cy + h / 2 - 16, 5, fill="#0a0a12", outline="#000")
        lx0, ly0 = cx - w / 2 + 13, cy - h / 2 + 11
        lx1, ly1 = cx + w / 2 - 13, cy + h / 2 - 22
        cv.create_rectangle(lx0, ly0, lx1, ly1, fill=C_LCD, outline="#0d3f88")
        if lab.adapter:
            if lab.cable_rod and not lab.hold:
                vals = lab.read_sensors()
            elif lab.cable_rod and lab.hold:
                vals = getattr(self, "_frozen", None) or lab.read_sensors()
            else:
                vals = None
            if lab.cable_rod and not lab.hold:
                self._frozen = vals
            fnt = ("Consolas", 12)
            if vals:
                for i, v in enumerate(vals):
                    r_, c_ = divmod(i, 3)
                    cv.create_text(lx0 + 12 + c_ * 52, ly0 + 12 + r_ * 17,
                                   anchor="w", text="%5.2f" % v,
                                   fill=C_LCD_TXT, font=fnt)
                cv.create_text(lx0 + 12, ly1 - 11, anchor="w",
                               text="Time: %07.2f [s]" % lab.watch,
                               fill=C_LCD_TXT, font=fnt)
            else:
                cv.create_text((lx0 + lx1) / 2, ly0 + 20, text="Timer mode",
                               fill=C_LCD_TXT, font=fnt)
                cv.create_text((lx0 + lx1) / 2, ly1 - 14,
                               text="%07.2f [s]" % lab.watch,
                               fill=C_LCD_TXT, font=("Consolas", 14, "bold"))
        cv.create_oval(cx - 9, cy + h / 2 + 3, cx + 9, cy + h / 2 + 21,
                       fill=C_RED, outline="#7d1a14")
        cv.create_text(cx, cy + h / 2 + 30, text="B", fill="#6b5a3c",
                       font=("", 8))
        cv.create_text(cx - w / 2, cy - h / 2 - 8, anchor="w",
                       text=(_("cal_ok") if lab.calib.get(lab.cable_rod)
                             else _("cal_no")) if lab.cable_rod else "",
                       fill="#6b5a3c", font=("", 9))
        if lab.cable_box:
            cv.create_rectangle(cx + w / 2 - 4, cy - 10, cx + w / 2 + 22,
                                cy + 10, fill="#bdb7a6", outline="#7c765f")
            tgt = None
            if lab.cable_rod == self._rod_on_pot() and lab.cable_rod:
                tgt = (SLOTS["pot"][0], 66)
            elif lab.cable_rod:
                tgt = (SLOTS["rodtable"][0] + SLOTS["rodtable"][2] / 2 + 2,
                       SLOTS["rodtable"][1])
            if tgt:
                cv.create_line(cx + w / 2 + 20, cy, cx + 190, cy - 70,
                               tgt[0], tgt[1], smooth=True, fill="#c9c3b2",
                               width=4)

    def draw_psu(self, cv):
        cx, cy, w, h = SLOTS["psu"]
        rr(cv, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, 5,
           fill="#1e1e20", outline="#000")
        cv.create_text(cx - 10, cy, text="9V DC", fill="#cfcfcf",
                       font=("", 9, "bold"))
        for t, col in (("PS+", C_RED), ("PS-", C_BLACK)):
            p = TERM_XY[t]
            cv.create_oval(p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6, fill=col,
                           outline="#d8d8d8")

    def draw_dmm(self, cv, m):
        cx, cy, w, h = SLOTS[m]
        lab = self.lab
        y0, y1 = cy - h / 2, cy + h / 2
        rr(cv, cx - w / 2, y0, cx + w / 2, y1, 10, fill=C_DMM,
           outline="#000")
        rr(cv, cx - w / 2 + 5, y0 + 5, cx + w / 2 - 5, y0 + 46, 5,
           fill="#101014", outline="#000")
        rr(cv, cx - w / 2 + 10, y0 + 9, cx + w / 2 - 10, y0 + 42, 3,
           fill=C_DMM_LCD, outline="#0d0d0d")
        i, v = lab.meters()
        if m == "amm":
            rng = lab.circ.amm_range
            txt = ("%5.2f" % abs(i)) if rng == "10A" else (
                "" if rng == "OFF" else
                (" 1  " if rng in ("200m", "20m", "2000u", "200u")
                 else " 0.00"))
        else:
            rng = lab.circ.volt_range
            txt = ("%5.2f" % v) if rng == "20" else (
                "" if rng == "OFF" else
                (" 1  " if rng in ("2000m", "200m", "200u") else
                 ("%5.2f" % abs(i)) if rng == "10A" else "%5.1f" % v))
        cv.create_text(cx + w / 2 - 16, y0 + 26, anchor="e", text=txt,
                       fill="#101010", font=("Consolas", 18, "bold"))
        kx, ky = cx - 6, cy + 6
        pos = AMM_POS if m == "amm" else VOLT_POS
        cur = lab.circ.amm_range if m == "amm" else lab.circ.volt_range
        n = len(pos)
        for k, p in enumerate(pos):
            a = math.radians(-90 + 360.0 * k / n)
            tx, ty = kx + 45 * math.cos(a), ky + 45 * math.sin(a)
            cv.create_text(tx, ty, text=p,
                           fill="#ffd45e" if p == cur else "#cfc9b6",
                           font=("", 6, "bold" if p == cur else "normal"))
            cv.create_oval(kx + 36 * math.cos(a) - 1.5,
                           ky + 36 * math.sin(a) - 1.5,
                           kx + 36 * math.cos(a) + 1.5,
                           ky + 36 * math.sin(a) + 1.5,
                           fill="#e8e2cf", outline="")
        cv.create_oval(kx - 31, ky - 31, kx + 31, ky + 31, fill="#17171a",
                       outline="#4a4a4f")
        a = math.radians(-90 + 360.0 * pos.index(cur) / n)
        cv.create_line(kx - 8 * math.cos(a), ky - 8 * math.sin(a),
                       kx + 28 * math.cos(a), ky + 28 * math.sin(a),
                       fill="#c8c8c8", width=8, capstyle="round")
        cv.create_rectangle(cx - w / 2 + 6, y1 - 40, cx + 6, y1 - 6,
                            fill=C_LABEL, outline="#9a9a9a")
        cv.create_text(cx - w / 2 + 42, y1 - 30,
                       text="Ampere Meter" if m == "amm" else "Voltmeter",
                       font=("", 7), fill="#333")
        cv.create_text(cx - w / 2 + 42, y1 - 16, text="# 389", font=("", 7),
                       fill="#333")
        for t, col in ((("A1", C_RED), ("ACOM", C_BLACK)) if m == "amm"
                       else (("V1", C_RED), ("VCOM", C_BLACK))):
            p = TERM_XY[t]
            cv.create_oval(p[0] - 9, p[1] - 9, p[0] + 9, p[1] + 9,
                           fill="#0d0d0f", outline="#3a3a3f")
            cv.create_oval(p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6, fill=col,
                           outline="#d8d8d8")

    def draw_wires(self, cv):
        xy = self.term_xy()
        for t1, t2 in self.lab.circ.wires:
            p, q = xy.get(t1), xy.get(t2)
            if not p or not q:
                continue
            mx = (p[0] + q[0]) / 2
            my = min(max((p[1] + q[1]) / 2 + 34, 40), self.H - 130)
            col = C_RED if "1" in t1 or "+" in t1 else C_BLACK
            cv.create_line(p[0], p[1], mx, my, q[0], q[1], smooth=True,
                           fill=col, width=4)
        if self.sel_term and xy.get(self.sel_term):
            p = xy[self.sel_term]
            cv.create_oval(p[0] - 11, p[1] - 11, p[0] + 11, p[1] + 11,
                           outline="#ffd45e", width=2)


# ==========================================================================
#  Tubes tab  (part A)
# ==========================================================================
class Tubes(ttk.Frame):
    W, H = 1200, 640
    TUBEX = {"Al": 300, "Br": 520, "Cu": 740}
    TOP, BOT = 120, 520

    def __init__(self, master, lab, app):
        super().__init__(master)
        self.lab = lab
        self.app = app
        self.cv = tk.Canvas(self, width=self.W, height=self.H,
                            highlightthickness=0, bg=C_TABLE)
        self.cv.pack(fill="both", expand=True)
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=3)
        ttk.Button(bar, text=_("start_stop"),
                   command=self.press).pack(side="left", padx=4)
        ttk.Button(bar, text=_("zero"), command=self.zero).pack(side="left")
        ttk.Label(bar, text="   " + _("drop_magnet")).pack(side="left")
        self.magnet = [980, 470]
        self.falling = None
        self.drag = False
        self.cv.bind("<Button-1>", self.press_ev)
        self.cv.bind("<B1-Motion>", self.move_ev)
        self.cv.bind("<ButtonRelease-1>", self.rel_ev)
        self.redraw()

    def press(self):
        self.lab.press()

    def zero(self):
        if self.lab.cable_rod:
            return
        self.lab.watch = 0.0
        self.lab.watch_run = False

    def press_ev(self, ev):
        if self.falling:
            return
        if (ev.x - self.magnet[0]) ** 2 + (ev.y - self.magnet[1]) ** 2 < 400:
            self.drag = True

    def move_ev(self, ev):
        if self.drag:
            self.magnet = [ev.x, ev.y]
            self.redraw()

    def rel_ev(self, ev):
        if not self.drag:
            return
        self.drag = False
        for k, x in self.TUBEX.items():
            if abs(ev.x - x) < 40 and abs(ev.y - self.TOP) < 60:
                self.falling = dict(tube=k, t=0.0,
                                    T=self.lab.fall_time(k))
                self.magnet = [x, self.TOP]
                break
        self.redraw()

    def tick(self, dt_real):
        sp = self.app.bench.speed.get()
        sp = min(sp, 10)
        dt = dt_real * sp            # the box clock itself runs in Lab.advance
        if self.falling:
            f = self.falling
            f["t"] += dt
            u = min(f["t"] / f["T"], 1.0)
            self.magnet = [self.TUBEX[f["tube"]],
                           self.TOP + (self.BOT - self.TOP) * u]
            if u >= 1.0:
                self.falling = None
                self.magnet = [self.TUBEX[f["tube"]], self.BOT + 26]
        self.redraw()

    def redraw(self):
        cv = self.cv
        cv.delete("all")
        wood(cv, 0, 0, self.W, self.H)
        cv.create_rectangle(120, self.BOT + 6, 900, self.BOT + 18,
                            fill="#8f7f66", outline="")
        specs = (("Al", C_ALU, C_ALU_HI, 30, _("tube_al")),
                 ("Br", C_BRASS, C_BRASS_HI, 28, _("tube_br")),
                 ("Cu", C_COPPER, C_COPPER_HI, 30, _("tube_cu")))
        for k, base, hi, halfw, name in specs:
            x = self.TUBEX[k]
            metal_tube(cv, x - halfw, self.TOP, x + halfw, self.BOT, base, hi)
            cv.create_oval(x - halfw, self.TOP - 9, x + halfw, self.TOP + 9,
                           fill=hi, outline="#3a3a3a")
            cv.create_oval(x - 9, self.TOP - 3, x + 9, self.TOP + 3,
                           fill="#241d18", outline="#3a3a3a")
            cv.create_text(x, self.BOT + 40, text=name, font=("", 10),
                           fill="#4a3a26")
        vis = True
        if self.falling:
            vis = False
        if vis or self.magnet[1] < self.TOP or self.magnet[1] > self.BOT:
            mx, my = self.magnet
            cv.create_rectangle(mx - 7, my - 7, mx + 7, my + 7,
                                fill="#8c8c92", outline="#40404a")
            cv.create_rectangle(mx - 7, my - 7, mx + 7, my, fill="#b9b9c2",
                                outline="")
        else:
            cv.create_text(self.TUBEX[self.falling["tube"]], self.TOP - 30,
                           text="...", font=("", 14), fill="#666")
        # the readout box acting as a stopwatch
        bx, by = 1030, 200
        rr(cv, bx - 95, by - 54, bx + 95, by + 54, 9, fill=C_BOX,
           outline="#061a63")
        rr(cv, bx - 89, by - 49, bx + 89, by + 38, 5, fill="#0a0a12",
           outline="#000")
        lab = self.lab
        cv.create_rectangle(bx - 82, by - 43, bx + 82, by + 32,
                            fill=C_LCD if lab.adapter else "#1b2a3a",
                            outline="#0d3f88")
        if not lab.adapter:
            cv.create_text(bx, by - 60, text=_("no_power"), fill="#7a5b3a",
                           font=("", 9))
        elif lab.cable_rod:
            vals = lab.read_sensors()
            for i, v in enumerate(vals):
                r_, c_ = divmod(i, 3)
                cv.create_text(bx - 74 + c_ * 52, by - 32 + r_ * 17,
                               anchor="w", text="%5.2f" % v,
                               fill=C_LCD_TXT, font=("Consolas", 11))
            cv.create_text(bx - 74, by + 22, anchor="w",
                           text="Time: %07.2f [s]" % lab.watch,
                           fill=C_LCD_TXT, font=("Consolas", 11))
        else:
            cv.create_text(bx, by - 22, text="Timer mode", fill=C_LCD_TXT,
                           font=("Consolas", 12))
            cv.create_text(bx, by + 12, text="%07.2f [s]" % lab.watch,
                           fill=C_LCD_TXT, font=("Consolas", 16, "bold"))
        cv.create_oval(bx - 9, by + 56, bx + 9, by + 74, fill=C_RED,
                       outline="#7d1a14")
        cv.create_text(60, 40, anchor="nw", text=_("magnet"), fill="#4a3a26",
                       font=("", 10))


# ==========================================================================
#  Equipment tab
# ==========================================================================
class Info(ttk.Frame):
    def __init__(self, master, lab, app):
        super().__init__(master)
        cv = tk.Canvas(self, width=1200, height=640, bg=C_TABLE,
                       highlightthickness=0)
        cv.pack(fill="both", expand=True)
        wood(cv, 0, 0, 1200, 640)
        y = 26
        for line in _("items"):
            cv.create_text(30, y, anchor="nw", text=line, font=("", 10),
                           fill="#3d2f1c")
            y += 26
        cv.create_text(30, y + 14, anchor="nw",
                       text=_("warn_immerse"), font=("", 10, "bold"),
                       fill="#8a2b20")


# ==========================================================================
class App:
    def __init__(self, root):
        self.root = root
        root.title(_("title"))
        root.geometry("1216x760")
        self.lab = Lab()
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        self.bench = Bench(nb, self.lab, self)
        self.tubes = Tubes(nb, self.lab, self)
        self.info = Info(nb, self.lab, self)
        nb.add(self.bench, text=_("tab_bench"))
        nb.add(self.tubes, text=_("tab_tubes"))
        nb.add(self.info, text=_("tab_info"))
        self.nb = nb
        self.dt = 0.1
        self._tick()

    def _tick(self):
        if not self.root.winfo_exists():
            return
        try:
            i = self.nb.index(self.nb.select())
        except Exception:
            i = 0
        if i == 0:
            self.bench.tick(self.dt)
        elif i == 1:
            self.tubes.tick(self.dt)
            self.lab.advance(self.dt * min(self.bench.speed.get(), 10))
        else:
            self.lab.advance(self.dt * self.bench.speed.get())
        self.root.after(int(self.dt * 1000), self._tick)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
