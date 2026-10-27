#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  1st Gulf Physics Olympiad  (GPhO 2016, Riyadh, Saudi Arabia)
  Experimental Problem E2 :  TUNGSTEN FILAMENT
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The apparatus of the problem sheet: three incandescent bulbs, the
    broken bulb whose straightened filament is bare (for diffraction), a
    ~12 V adapter, a 2 x 1.5 V battery pack feeding a red laser, a
    rheostat, one multimeter (its 10 A socket joined to COM through a
    few ohm), a 47 mF electrolytic capacitor, a screen, a measuring
    tape and seven leads.
    Only what the student would see is shown: the meter's digits, the
    fringes on the paper, the tape's marks.  No diameter, resistance,
    temperature or heat is computed for you.  The filament's hidden
    values are randomised each session; --seed N repeats a session.

    Run:   python3 gpho2016_E2_tungsten_sim_KO.py   [--seed N]
"""
import math
import random
import time
import sys
import tkinter as tk

APP_VERSION = "1.0"
LANG = "KO"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "KO" else en


SEED = None
for i, a in enumerate(sys.argv):
    if a == "--seed" and i + 1 < len(sys.argv):
        SEED = int(sys.argv[i + 1])
RNG = random.Random(SEED)


def gauss():
    return RNG.gauss(0.0, 1.0)


# ==============================================================================
#  1.  참값 (학생에게 보이지 않음) — 공식 해설에 맞춤
# ==============================================================================
SIG, RHO25, DW, T0 = 5.67e-8, 5.65e-8, 19250.0, 298.15
FIL = {"d": 46.3e-6 * (1 + 0.025 * gauss()), "l": 0.023 * (1 + 0.04 * gauss()),
       "k": 0.38 + 0.02 * gauss(), "Gc": 0.8e-4 * (1 + 0.1 * gauss()), "c": 190 * (1 + 0.04 * gauss())}
FIL["A"] = math.pi * FIL["d"] * FIL["l"]
FIL["R25"] = RHO25 * FIL["l"] / (math.pi * FIL["d"] ** 2 / 4)
FIL["Cth"] = DW * math.pi * FIL["d"] ** 2 / 4 * FIL["l"] * FIL["c"]
R400 = (216 - math.sqrt(216 * 216 - 4 * 2.46 * (400 - 104))) / (2 * 2.46)
RHEO = 25.3 * (1 + 0.025 * gauss())
C_CAP, ESR, R_LEAD, R_10A, R_MA = 0.047, 0.04, 0.03, 2.4 * (1 + 0.05 * gauss()), 1.2
LAMBDA = 650e-9
FOCUS_BEST = 0.42 + 0.08 * gauss()
CAL = (gauss() * 0.15, gauss())


def r_ratio(Tk):
    if Tk <= 400:
        return 1 + (R400 - 1) * (Tk - T0) / (400 - T0)
    return (216 - math.sqrt(max(0.0, 216 * 216 - 4 * 2.46 * (Tk - 104)))) / (2 * 2.46)


class Fil(object):
    def __init__(self):
        self.T = T0
        self.broken = False
        self.Tb = 3010 + 50 * gauss()

    def R(self):
        return FIL["R25"] * r_ratio(self.T)

    def loss(self):
        return FIL["A"] * FIL["k"] * SIG * (self.T ** 4 - T0 ** 4) + FIL["Gc"] * (self.T - T0)


DIAL = ["OFF", "DCV 200m", "DCV 2", "DCV 20", "DCV 200", "DCA 200m", "DCA 10", "Ω 200", "Ω 2k", "Ω 20k"]
TERMS = ["PSP", "PSN", "BT0", "BT1", "BT2", "RA", "RB", "RC", "CP", "CN", "L0a", "L0b", "L1a", "L1b", "L2a", "L2b", "X10A", "XCOM", "XV"]
# 리드: 0 테스터(바나나-탐침) ×2, 1 바나나-악어 ×3, 2 악어-악어 ×2
LEADS = [(0, "#c8262b"), (0, "#1d1d1f"), (1, "#c8262b"), (1, "#1d1d1f"), (1, "#e3b21a"), (2, "#2f8a3e"), (2, "#2b62c4")]


class State(object):
    def __init__(self):
        self.bulbs = [Fil(), Fil(), Fil()]
        self.leads = []            # [n, a, b]
        self.held = None
        self.slider = 0.5
        self.mains = True
        self.laser = False
        self.Vc = 0.0
        self.cap_dead = False
        self.fuse = False
        self.dial = 0
        self.spares = 3
        self.screen = 95.0          # cm from the laser's end; the filament is at 14 cm
        self.focus = 0.7
        self.goggles = False


S = State()
X_FIL = 14.0


def gauss_solve(A, b):
    n = len(b)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        piv = M[c][c] or 1e-30
        for r in range(c + 1, n):
            k = M[r][c] / piv
            if k:
                for j in range(c, n + 1):
                    M[r][j] -= k * M[c][j]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (M[r][n] - sum(M[r][j] * x[j] for j in range(r + 1, n))) / (M[r][r] or 1e-30)
    return x


def elements():
    E = []
    for n, a, b in S.leads:
        if b:
            E.append((a, b, "R", R_LEAD))
    E += [("RA", "RC", "R", max(0.05, S.slider * RHEO)), ("RC", "RB", "R", max(0.05, (1 - S.slider) * RHEO))]
    for i, f in enumerate(S.bulbs):
        if not f.broken:
            E.append(("L%da" % i, "L%db" % i, "F", i))
    if S.mains:
        E.append(("PSP", "PSN", "V", 12.3, 0.9))
    E += [("BT1", "BT0", "V", 1.55, 0.25), ("BT2", "BT1", "V", 1.55, 0.25)]
    if S.laser:
        E.append(("BT2", "BT0", "R", 110.0))
    if not S.cap_dead:
        E.append(("CP", "CN", "C", C_CAP))
    d = DIAL[S.dial]
    E.append(("X10A", "XCOM", "R", R_10A))
    if d.startswith("DCV"):
        E.append(("XV", "XCOM", "R", 10e6))
    if d == "DCA 200m" and not S.fuse:
        E.append(("XV", "XCOM", "R", R_MA))
    return E


def solve_at(dt, extra=None):
    E = elements()
    if extra:
        E.append(extra)
    nodes = [n for n in TERMS if n != "BT0"]
    idx = dict((n, i) for i, n in enumerate(nodes))
    N = len(nodes)
    G = [[0.0] * N for _ in range(N)]
    I = [0.0] * N

    def st(a, b, g):
        ia, ib = idx.get(a), idx.get(b)
        if ia is not None:
            G[ia][ia] += g
        if ib is not None:
            G[ib][ib] += g
        if ia is not None and ib is not None:
            G[ia][ib] -= g
            G[ib][ia] -= g

    def inj(a, i):
        ia = idx.get(a)
        if ia is not None:
            I[ia] += i
    for e in E:
        a, b, k = e[0], e[1], e[2]
        if k == "R":
            st(a, b, 1.0 / e[3])
        elif k == "F":
            st(a, b, 1.0 / S.bulbs[e[3]].R())
        elif k == "V":
            st(a, b, 1.0 / e[4])
            inj(a, e[3] / e[4])
            inj(b, -e[3] / e[4])
        elif k == "C":
            g = 1.0 / (ESR + dt / e[3])
            st(a, b, g)
            inj(a, S.Vc * g)
            inj(b, -S.Vc * g)
        elif k == "I":
            inj(a, -e[3])
            inj(b, e[3])
    for i in range(N):
        G[i][i] += 1e-10
    V = gauss_solve(G, I)
    return lambda t: 0.0 if t == "BT0" else V[idx[t]]


VOLT = solve_at(0.004)


def step(dt_total, say):
    global VOLT
    left, n = dt_total, 0
    while left > 1e-9 and n < 1500:
        n += 1
        dt = min(left, 0.004)
        VOLT = solve_at(dt)
        P, rate = [], 0.0
        for i, f in enumerate(S.bulbs):
            if f.broken:
                P.append(0.0)
                continue
            u = VOLT("L%da" % i) - VOLT("L%db" % i)
            p = u * u / f.R()
            P.append(p)
            rate = max(rate, abs(p - f.loss()) / FIL["Cth"])
        if rate * dt > 15:
            dt = max(2e-7, 15 / rate)
            VOLT = solve_at(dt)
            for i, f in enumerate(S.bulbs):
                if not f.broken:
                    u = VOLT("L%da" % i) - VOLT("L%db" % i)
                    P[i] = u * u / f.R()
        for i, f in enumerate(S.bulbs):
            if f.broken:
                continue
            f.T = max(T0, f.T + (P[i] - f.loss()) / FIL["Cth"] * dt)
            if f.T > f.Tb:
                f.broken, f.T = True, T0
                say(T("전구 %d의 필라멘트가 끊어졌습니다" % (i + 1), "bulb %d: the filament has broken" % (i + 1)))
        if not S.cap_dead:
            v = VOLT("CP") - VOLT("CN")
            g = 1.0 / (ESR + dt / C_CAP)
            S.Vc += (v - S.Vc) * g * dt / C_CAP
            if S.Vc < -0.8:
                S.cap_dead, S.Vc = True, 0.0
                say(T("축전기가 거꾸로 연결되어 부풀며 전해액을 뿜었습니다 — 못 쓰게 되었습니다", "the capacitor was reversed: it bulged and spat electrolyte — it is ruined"))
        if DIAL[S.dial] == "DCA 200m" and not S.fuse and abs(VOLT("XV") - VOLT("XCOM")) / R_MA > 0.4:
            S.fuse = True
            say(T("멀티미터의 mA 퓨즈가 끊어졌습니다", "the meter's mA fuse has blown"))
        left -= dt


def meter_reading():
    d = DIAL[S.dial]
    if d == "OFF":
        return ""
    kind, rng = d.split(" ")
    n = 1 + (CAL[0] + 0.1 * gauss()) / 100

    def dig(dec, k):
        return (CAL[1] + k * gauss()) * 10 ** (-dec) * 0.5
    if kind == "DCV":
        full = {"200m": 0.2, "2": 2, "20": 20, "200": 200}[rng]
        dec = {"200m": 1, "2": 3, "20": 2, "200": 1}[rng]
        v = VOLT("XV") - VOLT("XCOM")
        if abs(v) >= full * 0.9995:
            return "1"
        return "%.*f" % (dec, v * n * (1000 if rng == "200m" else 1) + dig(dec, 0.6))
    if kind == "DCA":
        i = (VOLT("X10A") - VOLT("XCOM")) / R_10A if rng == "10" else (0.0 if S.fuse else (VOLT("XV") - VOLT("XCOM")) / R_MA)
        full, dec = (10, 2) if rng == "10" else (0.2, 1)
        if abs(i) >= full * 0.9995:
            return "1"
        return "%.*f" % (dec, i * n * (1 if rng == "10" else 1000) + dig(dec, 0.7))
    full = {"200": 200, "2k": 2000, "20k": 20000}[rng]
    dec = {"200": 1, "2k": 3, "20k": 2}[rng]
    div = 1 if rng == "200" else 1000
    vf = solve_at(1e-3, ("XCOM", "XV", "I", 1e-3))
    r = (vf("XV") - vf("XCOM")) / 1e-3 + 0.3
    if r >= full * 0.9995 or r > 1e8:
        return "1"
    if r < 0:
        return "-1"
    return "%.*f" % (dec, max(0.0, r * n / div + dig(dec, 1.0)))


def fringe(y_cm, L_cm):
    th = (y_cm / 100.0) / (L_cm / 100.0)
    b = math.pi * FIL["d"] * th / LAMBDA
    s = 1.0 if abs(b) < 1e-6 else math.sin(b) / b
    return s * s


# ==============================================================================
#  2.  화면
# ==============================================================================
BG, PANEL, PANEL2 = "#1c2027", "#22262d", "#2b2f36"
FG, FG_DIM, ACC = "#e8eef2", "#9aa3ab", "#f2c14e"
TPOS = {"PSP": (90, 90), "PSN": (120, 90), "BT0": (90, 210), "BT1": (120, 210), "BT2": (150, 210),
        "RA": (230, 150), "RB": (520, 150), "RC": (505, 95), "CP": (600, 110), "CN": (640, 110),
        "L0a": (705, 150), "L0b": (735, 150), "L1a": (785, 150), "L1b": (815, 150), "L2a": (865, 150), "L2b": (895, 150),
        "X10A": (420, 330), "XCOM": (470, 330), "XV": (520, 330)}
LBL = {"PSP": "+12V", "PSN": "−", "BT0": "−", "BT1": "1.5V", "BT2": "+3V", "RA": "A", "RB": "B", "RC": "C", "CP": "+", "CN": "−",
       "X10A": "10A", "XCOM": "COM", "XV": "VΩmA"}


class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title(T("GPhO 2016 실험 시뮬레이터 — E2 텅스텐 필라멘트", "GPhO 2016 Experiment Simulator — E2 Tungsten filament") + "   v" + APP_VERSION)
        self.geometry("1480x900")
        self.configure(bg=BG)
        self.kind = None
        self.msg = ("", 0)
        self.disp = ""
        self.last_read = 0
        self.tape = [10.0, 7.0, 0.0]     # on the paper canvas: x, y (cm on the paper), angle
        self.tdrag = None
        self.sdrag = False
        self._build()
        self._last = time.time()
        self.after(30, self._tick)

    def say(self, m):
        self.msg = (m, time.time())

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x")
        tk.Label(top, text="GPhO 2016  ·  " + T("E2 텅스텐 필라멘트 (13점)", "E2 Tungsten filament (13 pts)"), bg=BG, fg=ACC,
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=14, pady=6)
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, anchor="w", bg=BG, fg=FG_DIM, font=("Segoe UI", 9), text=T(
            "회로 — 리드 종류를 고른 뒤 단자 두 개를 차례로 클릭 · 우클릭: 리드 뽑기 · 가변저항 슬라이더 끌기 · 다이얼 왼/오른쪽 클릭 또는 휠 · 전구 클릭(예비 전구 들고): 교체",
            "circuit — pick a lead kind, then click two terminals · R-click: pull a lead · drag the rheostat's slider · dial: click left/right or wheel · click a bulb (holding a spare): replace it")).pack(fill="x")
        self.cv = tk.Canvas(left, bg="#2e3238", height=420, highlightthickness=0)
        self.cv.pack(fill="x")
        tk.Label(left, anchor="w", bg=BG, fg=FG_DIM, font=("Segoe UI", 9), text=T(
            "광학대 (옆에서) — 스크린을 끌어 옮기기 · 레이저 캡 위 휠: 초점   |   스크린의 종이 — 줄자 끌기, 줄자 위 휠: 기울이기",
            "optical bench, side — drag the screen · wheel over the laser's cap: focus   |   the paper — drag the tape, wheel over it: tilt")).pack(fill="x", pady=(6, 0))
        row = tk.Frame(left, bg=BG)
        row.pack(fill="both", expand=True)
        self.ob = tk.Canvas(row, bg="#2e3238", width=560, highlightthickness=0)
        self.ob.pack(side="left", fill="both", expand=True)
        self.pp = tk.Canvas(row, bg="#2e3238", width=520, highlightthickness=0)
        self.pp.pack(side="left", fill="both", padx=(6, 0))
        right = tk.Frame(body, bg=PANEL, width=300)
        right.pack(side="left", fill="y", padx=(8, 0))
        right.pack_propagate(False)
        bs = dict(bg=PANEL2, fg=FG, activebackground="#343941", activeforeground=FG, relief="flat", bd=0, padx=8, pady=5, font=("Segoe UI", 10))

        def H(t):
            tk.Label(right, text=t, bg=PANEL, fg=ACC, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        H(T("리드", "Leads"))
        self.kbtn = []
        for k, txt in enumerate((T("테스터 리드 (바나나–탐침)", "tester lead (banana–probe)"), T("바나나–악어", "banana–crocodile"), T("악어–악어", "crocodile–crocodile"))):
            b = tk.Button(right, text=txt, command=lambda k=k: self.pick_kind(k), **bs)
            b.pack(fill="x", padx=10, pady=1)
            self.kbtn.append(b)
        tk.Button(right, text=T("리드 모두 뽑기", "Pull out all leads"), command=self.clear, **bs).pack(fill="x", padx=10, pady=(4, 1))
        H(T("조작", "Controls"))
        self.b_mains = tk.Button(right, command=self.t_mains, **bs)
        self.b_mains.pack(fill="x", padx=10, pady=1)
        self.b_laser = tk.Button(right, command=self.t_laser, **bs)
        self.b_laser.pack(fill="x", padx=10, pady=1)
        self.b_spare = tk.Button(right, command=self.t_spare, **bs)
        self.b_spare.pack(fill="x", padx=10, pady=1)
        self.b_gog = tk.Button(right, command=self.t_gog, **bs)
        self.b_gog.pack(fill="x", padx=10, pady=1)
        H(T("안내", "Notes"))
        tk.Label(right, justify="left", wraplength=278, bg=PANEL, fg=FG_DIM, font=("Segoe UI", 8), text=T(
            "• λ = 650 nm, D(W) = 19.25 g/cm³, ρ25 = 5.65×10⁻⁸ Ω·m, C = 47 mF, σ = 5.67×10⁻⁸.\n• T(ρ/ρ25) = 104 K + 216 K·(ρ/ρ25) − 2.46 K·(ρ/ρ25)².\n• 10 A 단자와 COM은 다이얼과 상관없이 수 Ω의 저항으로 이어져 있습니다.\n• 축전기를 거꾸로 연결하지 마세요(회색 띠 = −). 보안경을 쓰세요.",
            "• λ = 650 nm, D(W) = 19.25 g/cm³, ρ25 = 5.65×10⁻⁸ Ω·m, C = 47 mF, σ = 5.67×10⁻⁸.\n• T(ρ/ρ25) = 104 K + 216 K·(ρ/ρ25) − 2.46 K·(ρ/ρ25)².\n• The 10 A and COM sockets stay joined through a few ohm, whatever the dial says.\n• Never reverse the capacitor (grey band = minus). Wear the goggles.")).pack(anchor="w", padx=10)
        self.status = tk.Label(right, justify="left", wraplength=278, bg="#12161b", fg=ACC, font=("Segoe UI", 9), anchor="nw", padx=8, pady=8)
        self.status.pack(fill="both", expand=True, padx=10, pady=10)
        self.cv.bind("<Button-1>", self.c_down)
        self.cv.bind("<B1-Motion>", self.c_drag)
        self.cv.bind("<ButtonRelease-1>", lambda e: setattr(self, "sdrag", False))
        self.cv.bind("<Button-3>", self.c_right)
        self.cv.bind("<Motion>", lambda e: setattr(self, "mouse", (e.x, e.y)))
        self.cv.bind("<MouseWheel>", self.c_wheel)
        self.cv.bind("<Button-4>", lambda e: self.c_wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self.c_wheel(e, -1))
        self.ob.bind("<Button-1>", self.o_down)
        self.ob.bind("<B1-Motion>", self.o_drag)
        self.ob.bind("<MouseWheel>", self.o_wheel)
        self.ob.bind("<Button-4>", lambda e: self.o_wheel(e, 1))
        self.ob.bind("<Button-5>", lambda e: self.o_wheel(e, -1))
        self.pp.bind("<Button-1>", self.p_down)
        self.pp.bind("<B1-Motion>", self.p_drag)
        self.pp.bind("<MouseWheel>", self.p_wheel)
        self.pp.bind("<Button-4>", lambda e: self.p_wheel(e, 1))
        self.pp.bind("<Button-5>", lambda e: self.p_wheel(e, -1))
        self.mouse = (0, 0)

    # ---- buttons ---- #
    def pick_kind(self, k):
        if S.held is not None:
            S.leads.pop(S.held)
            S.held = None
        self.kind = None if self.kind == k else k

    def clear(self):
        S.leads, S.held = [], None

    def t_mains(self):
        S.mains = not S.mains

    def t_laser(self):
        S.laser = not S.laser

    def t_spare(self):
        self.kind = None
        self.spare_hand = not getattr(self, "spare_hand", False) and S.spares > 0

    def t_gog(self):
        S.goggles = not S.goggles

    # ---- circuit canvas ---- #
    def term_at(self, x, y):
        best = None
        for t, (tx, ty) in TPOS.items():
            d = math.hypot(tx - x, ty - y)
            if d < 12 and (best is None or d < best[0]):
                best = (d, t)
        return best[1] if best else None

    def free_lead(self, k):
        used = [n for n, a, b in S.leads]
        for n, (kk, col) in enumerate(LEADS):
            if kk == k and n not in used:
                return n
        return None

    def c_down(self, e):
        t = self.term_at(e.x, e.y)
        if getattr(self, "spare_hand", False):
            for i in range(3):
                bx = 720 + 80 * i
                if abs(e.x - bx) < 30 and 40 < e.y < 130 and S.bulbs[i].broken:
                    S.bulbs[i] = Fil()
                    S.spares -= 1
                    self.spare_hand = False
            return
        if t:
            if S.held is not None:
                n, a, b = S.leads[S.held]
                if t == a:
                    return
                k = LEADS[n][0]
                if (k == 2 and t[0] == "X") or (t[0] == "X" and a[0] == "X"):
                    self.say(T("멀티미터 단자에는 바나나 플러그만, 한쪽 끝만 들어갑니다", "only one banana end goes into the meter's sockets"))
                    return
                S.leads[S.held][2] = t
                S.held = None
                self.kind = None
                return
            if self.kind is not None:
                n = self.free_lead(self.kind)
                if n is None:
                    self.say(T("그 종류의 리드가 남아 있지 않습니다", "no lead of that kind left"))
                    return
                if self.kind == 2 and t[0] == "X":
                    self.say(T("멀티미터 단자에는 바나나 플러그만 들어갑니다", "only a banana plug goes into the meter's sockets"))
                    return
                S.leads.append([n, t, None])
                S.held = len(S.leads) - 1
            return
        if 240 <= e.x <= 510 and 80 <= e.y <= 175:
            self.sdrag = True
            self.c_drag(e)
            return
        if math.hypot(e.x - 470, e.y - 265) < 34:
            S.dial = (S.dial + (1 if e.x > 470 else -1)) % len(DIAL)

    def c_drag(self, e):
        if self.sdrag:
            S.slider = max(0.0, min(1.0, (e.x - 250) / 250.0))

    def c_right(self, e):
        if S.held is not None:
            S.leads.pop(S.held)
            S.held = None
            return
        t = self.term_at(e.x, e.y)
        if t:
            for i in range(len(S.leads) - 1, -1, -1):
                if t in S.leads[i][1:]:
                    S.leads.pop(i)
                    return
        self.kind = None

    def c_wheel(self, e, d=None):
        s = d if d is not None else (1 if e.delta > 0 else -1)
        if math.hypot(e.x - 470, e.y - 265) < 40:
            S.dial = (S.dial + s) % len(DIAL)

    # ---- optical bench / paper ---- #
    def o_down(self, e):
        self.o_drag(e)

    def o_drag(self, e):
        W = int(self.ob.winfo_width())
        sx = (W - 60) / 165.0
        x = (e.x - 30) / sx
        if x > X_FIL + 20:
            S.screen = max(X_FIL + 25, min(160, x))

    def o_wheel(self, e, d=None):
        s = d if d is not None else (1 if e.delta > 0 else -1)
        S.focus = max(0.0, min(1.0, S.focus + s * (0.002 if e.state & 1 else 0.01)))

    def p_local(self, x, y):
        K = 24.0
        return ((x - 20) / K, (y - 20) / K)

    def on_tape(self, px, py):
        tx, ty, a = self.tape
        dx, dy = px - tx, py - ty
        u = dx * math.cos(a) + dy * math.sin(a)
        v = -dx * math.sin(a) + dy * math.cos(a)
        return -0.5 < u < 100 and -0.1 < v < 1.4

    def p_down(self, e):
        px, py = self.p_local(e.x, e.y)
        self.tdrag = (px - self.tape[0], py - self.tape[1]) if self.on_tape(px, py) else None

    def p_drag(self, e):
        if self.tdrag:
            px, py = self.p_local(e.x, e.y)
            self.tape[0], self.tape[1] = px - self.tdrag[0], py - self.tdrag[1]

    def p_wheel(self, e, d=None):
        s = d if d is not None else (1 if e.delta > 0 else -1)
        px, py = self.p_local(e.x, e.y)
        if self.on_tape(px, py):
            self.tape[2] += s * math.radians(0.1 if e.state & 1 else 0.5)

    # ---- drawing ---- #
    def draw_circuit(self):
        c = self.cv
        c.delete("all")
        c.create_rectangle(60, 70, 150, 110, fill="#202226", outline="")
        c.create_text(105, 60, text=T("어댑터 12 V", "adapter 12 V") + ("" if S.mains else T(" (빠짐)", " (unplugged)")), fill=FG_DIM, font=("Segoe UI", 8))
        c.create_rectangle(70, 190, 170, 230, fill="#1a1b1e", outline="")
        c.create_text(120, 180, text=T("배터리 팩", "battery pack") + (" · LASER ON" if S.laser else ""), fill=FG_DIM, font=("Segoe UI", 8))
        c.create_rectangle(240, 125, 510, 175, fill="#e5dcc8", outline="#a8865a")
        for x in range(244, 508, 4):
            c.create_line(x, 126, x, 174, fill="#a8865a")
        xs = 250 + S.slider * 250
        c.create_rectangle(xs - 10, 85, xs + 10, 110, fill="#1d1f22")
        c.create_line(xs, 110, xs, 125, fill="#c9a24a", width=3)
        c.create_line(250, 95, 505, 95, fill="#9aa0a6", width=3)
        c.create_text(375, 190, text="25 Ω  2 A", fill=FG_DIM, font=("Segoe UI", 8))
        c.create_oval(590, 40, 650, 100, fill="#2c3e78" if not S.cap_dead else "#3b4f8a", outline="#9aa0a6", width=3)
        c.create_text(620, 30, text="47000 µF 25 V", fill=FG_DIM, font=("Segoe UI", 8))
        for i, f in enumerate(S.bulbs):
            bx = 720 + 80 * i
            glow = 0 if f.broken else max(0.0, min(1.0, (f.T - 900) / 1800))
            col = "#%02x%02x%02x" % (int(200 + 55 * glow), int(205 + 40 * glow), int(210 - 120 * glow)) if glow > 0 else "#c8ced3"
            c.create_oval(bx - 18, 60, bx + 18, 96, fill=col, outline="#888")
            c.create_line(bx - 8, 80, bx + 8, 80, fill="#555" if f.broken else ("#fff3c0" if glow > 0.05 else "#555"), width=2, dash=(3, 3) if f.broken else None)
            c.create_rectangle(bx - 25, 100, bx + 25, 135, fill="#2b2e33", outline="")
            c.create_text(bx, 118, text=str(i + 1), fill=FG_DIM)
        # meter
        c.create_rectangle(400, 200, 540, 345, fill="#e8b417", outline="#b88b0c", width=2)
        c.create_rectangle(410, 207, 530, 242, fill="#b9bfb3", outline="#333", width=3)
        c.create_text(520, 225, text=self.disp, anchor="e", font=("Consolas", 20, "bold"), fill="#1b1e1c")
        c.create_oval(436, 231, 504, 299, fill="#2b2d2f", outline="")
        a = -math.pi / 2 + S.dial * 2 * math.pi / len(DIAL)
        c.create_line(470 - 28 * math.cos(a), 265 - 28 * math.sin(a), 470 + 28 * math.cos(a), 265 + 28 * math.sin(a), fill="#4a4c4e", width=10)
        c.create_line(470 + 14 * math.cos(a), 265 + 14 * math.sin(a), 470 + 28 * math.cos(a), 265 + 28 * math.sin(a), fill="#f2f2ee", width=3)
        c.create_text(470, 312, text=DIAL[S.dial], fill="#1b1e1c", font=("Segoe UI", 8, "bold"))
        for t, (x, y) in TPOS.items():
            col = "#8a3b1e" if t[0] == "X" else "#c8262b" if t in ("PSP", "BT2", "RA", "RB", "CP") else "#1d1d1f" if t in ("PSN", "BT0", "RC", "CN") else "#c9ced3"
            c.create_oval(x - 7, y - 7, x + 7, y + 7, fill=col, outline="#000")
            if t in LBL:
                c.create_text(x, y + 16 if t[0] != "X" else y + 16, text=LBL[t], fill=FG_DIM, font=("Segoe UI", 7))
        mx, my = getattr(self, "mouse", (0, 0))
        for j, (n, a, b) in enumerate(S.leads):
            col = LEADS[n][1]
            x1, y1 = TPOS[a]
            x2, y2 = TPOS[b] if b else (mx, my)
            sag = 40 + abs(x2 - x1) * 0.12
            c.create_line(x1, y1, x1, y1 + 20, (x1 + x2) / 2, max(y1, y2) + sag, x2, y2 + 20, x2, y2, smooth=True, fill=col if col != "#1d1d1f" else "#111", width=3)

    def draw_bench(self):
        c = self.ob
        c.delete("all")
        W, H = int(c.winfo_width()), int(c.winfo_height())
        sx = (W - 60) / 165.0

        def X(x):
            return 30 + x * sx
        yb = H * 0.55
        c.create_line(0, yb + 30, W, yb + 30, fill="#3a3d42", width=60)
        c.create_rectangle(X(-6), yb - 8, X(2.6), yb + 8, fill="#1a1b1e")
        c.create_rectangle(X(2.6), yb - 9, X(4), yb + 9, fill="#b8954a", outline="#7c6330")
        c.create_line(X(X_FIL), yb - 16, X(X_FIL), yb + 16, fill="#3a3a3a", width=2)
        c.create_rectangle(X(X_FIL) - 8, yb + 16, X(X_FIL) + 8, yb + 60, fill="#2b2e33")
        if S.laser:
            c.create_line(X(4), yb, X(S.screen), yb, fill="#ff3020", width=1)
        c.create_rectangle(X(S.screen), yb - 80, X(S.screen) + 30, yb + 60, fill="#c94a2a")
        c.create_rectangle(X(S.screen) - 3, yb - 75, X(S.screen), yb + 55, fill="#f4f2ec")
        c.create_text(X(2), yb - 30, text=T("레이저 (캡: 휠로 초점)", "laser (cap: wheel to focus)"), fill=FG_DIM, font=("Segoe UI", 8))
        c.create_text(X(X_FIL), yb + 72, text=T("드러난 필라멘트", "bare filament"), fill=FG_DIM, font=("Segoe UI", 8))

    def draw_paper(self):
        c = self.pp
        c.delete("all")
        K = 24.0
        W, H = int(c.winfo_width()), int(c.winfo_height())
        c.create_rectangle(20, 20, 20 + 19 * K, 20 + 15 * K, fill="#f4f2ec", outline="#c94a2a", width=6)
        if S.laser:
            L = S.screen - X_FIL
            df = abs(S.focus - FOCUS_BEST)
            con = 1 / (1 + (df / 0.07) ** 2)
            cy, cz = 20 + 7.5 * K, 20 + 9.5 * K
            for px in range(22, int(20 + 19 * K) - 2, 2):
                y = (px - cz) / K
                v = min(1.0, (2.5 * math.exp(-(y / (0.12 + 1.4 * df)) ** 2) * (1 - 0.5 * con) + 14 * fringe(y, L) * con) ** 0.6)
                if v < 0.03:
                    continue
                h = (0.18 + 1.6 * df) * K
                col = "#%02x%02x%02x" % (int(244 + (255 - 244) * v), int(242 * (1 - 0.9 * v)), int(236 * (1 - 0.9 * v)))
                c.create_line(px, cy - h, px, cy + h, fill=col, width=2)
        tx, ty, a = self.tape
        ca, sa = math.cos(a), math.sin(a)

        def P(u, v):
            return (20 + (tx + u * ca - v * sa) * K, 20 + (ty + u * sa + v * ca) * K)
        pts = [P(0, 0), P(100, 0), P(100, 1.3), P(0, 1.3)]
        c.create_polygon(*[v for p in pts for v in p], fill="#f3cd2f", outline="#a8891c")
        for mm in range(0, 400):
            u = mm / 10.0
            p1 = P(u, 0)
            if p1[0] > W + 20:
                break
            ln = 0.55 if mm % 10 == 0 else 0.38 if mm % 5 == 0 else 0.25
            p2 = P(u, ln)
            c.create_line(p1[0], p1[1], p2[0], p2[1], fill="#151515")
            if mm % 10 == 0:
                q = P(u + 0.08, 0.95)
                c.create_text(q[0], q[1], text=str(mm // 10), anchor="w", fill="#151515", font=("Arial", 8, "bold"), angle=-math.degrees(a))

    def _tick(self):
        now = time.time()
        dt = min(0.05, now - self._last)
        self._last = now
        step(dt, self.say)
        if now - self.last_read > 0.333:
            self.last_read = now
            self.disp = meter_reading()
        try:
            self.draw_circuit()
            self.draw_bench()
            self.draw_paper()
        except tk.TclError:
            return
        self.b_mains.config(text=T("어댑터: 콘센트에 꽂힘", "Adapter: in the socket") if S.mains else T("어댑터: 빠짐", "Adapter: unplugged"))
        self.b_laser.config(text=T("배터리 팩 스위치: ON", "Battery pack switch: ON") if S.laser else T("배터리 팩 스위치: OFF", "Battery pack switch: OFF"))
        self.b_spare.config(text=(T("예비 전구 들고 있음 — 끊어진 전구 클릭", "spare bulb in hand — click a broken one") if getattr(self, "spare_hand", False) else T("예비 전구 집기 (남음 %d)", "Take a spare bulb (%d left)") % S.spares))
        self.b_gog.config(text=T("보안경: 씀", "Goggles: on") if S.goggles else T("보안경: 안 씀", "Goggles: off"))
        for k, b in enumerate(self.kbtn):
            b.config(bg=ACC if self.kind == k else PANEL2, fg="#1c2027" if self.kind == k else FG)
        w = []
        if self.msg[0] and now - self.msg[1] < 5:
            w.append(self.msg[0])
        if any(b and ("CP" in (a, b) or "CN" in (a, b)) for n, a, b in S.leads) and not S.goggles:
            w.append(T("축전기를 쓰기 전에 보안경을 쓰세요", "put on the goggles before you use the capacitor"))
        if S.held is not None:
            w.append(T("리드를 들고 있음: 다른 끝을 꽂을 단자 클릭", "a lead in hand: click a terminal for its other end"))
        self.status.config(text="\n\n".join(w))
        self.after(30, self._tick)


if __name__ == "__main__":
    App().mainloop()
