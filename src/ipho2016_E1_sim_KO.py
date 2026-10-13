#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  47th International Physics Olympiad  (IPhO 2016, Zurich, Switzerland)
  Experimental Problem E1 :  ELECTRICAL CONDUCTIVITY IN TWO DIMENSIONS
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Apparatus rebuilt from the photographs of the problem sheet: graphite
    coated paper (210 x 297 mm), Cr coated Si wafer (D = 100 mm, one flat),
    Plexiglas plate with 8 spring loaded pins (P1..P4 collinear, s = 20 mm;
    P5..P8 a 66 mm square), signal generator in DC mode, two 3 1/2 digit
    multimeters and a reference resistor.
    Only the instrument readings and the visible geometry are shown.  Sheet
    resistances, contact resistances and correction factors are never
    computed or shown.  The sample is solved as a real 2D conductor (Green
    functions with image charges) inside a nodal circuit analysis.
    All hidden true parameters are randomised for every session.

    Run:   python3 ipho2016_E1_sim_KO.py   [--seed=N]
"""

import math, random, sys, os

# --------------------------------------------------------------------------
# language
# --------------------------------------------------------------------------
LANG = "ko"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


# ===========================================================================
#  linear algebra helpers (standard library only)
# ===========================================================================
def mat_solve(A, b):
    """Gaussian elimination with partial pivoting. A is modified."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-18:
            return None
        M[c], M[p] = M[p], M[c]
        pv = M[c][c]
        for r in range(n):
            if r == c:
                continue
            f = M[r][c] / pv
            if f == 0.0:
                continue
            for k in range(c, n + 1):
                M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] for i in range(n)]


def mat_inv(A):
    n = len(A)
    M = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-18:
            return None
        M[c], M[p] = M[p], M[c]
        pv = M[c][c]
        for k in range(2 * n):
            M[c][k] /= pv
        for r in range(n):
            if r == c:
                continue
            f = M[r][c]
            if f == 0.0:
                continue
            for k in range(2 * n):
                M[r][k] -= f * M[c][k]
    return [row[n:] for row in M]


# ===========================================================================
#  2-D Green's functions  (potential of a point source on a thin sheet)
#     V(r) = rho_sheet * sum_j G(r, r_j) * I_j        with   sum_j I_j = 0
#  Lengths in mm, resistances in ohm.
# ===========================================================================
PI = math.pi
LN2 = math.log(2.0)
R_CONTACT_TIP = 0.35          # effective radius of a spring pin tip [mm]


def G_strip(x1, y1, x2, y2, W, rc=R_CONTACT_TIP):
    """Infinitely long strip 0 < y < W, insulating edges (Neumann)."""
    a = PI * abs(x1 - x2) / W
    if a > 350.0:                      # avoid cosh overflow: 1-D limit
        return -(1.0 / (2 * PI)) * (a - math.log(2.0))
    ch = math.cosh(a)
    f1 = ch - math.cos(PI * (y1 - y2) / W)
    f2 = ch - math.cos(PI * (y1 + y2) / W)
    fmin = (PI * rc / W) ** 2 / 2.0
    if f1 < fmin:
        f1 = fmin
    if f2 < fmin:
        f2 = fmin
    return -(1.0 / (4 * PI)) * (math.log(f1) + math.log(f2))


def G_disc(x1, y1, x2, y2, a, rc=R_CONTACT_TIP):
    """Disc of radius a, insulating rim (Neumann).  Centre at the origin."""
    d2 = (x1 - x2) ** 2 + (y1 - y2) ** 2
    r1s = x1 * x1 + y1 * y1
    r2s = x2 * x2 + y2 * y2
    img = r1s * r2s / (a * a) - 2.0 * (x1 * x2 + y1 * y2) + a * a
    if d2 < rc * rc:
        d2 = rc * rc
    if img < rc * rc:
        img = rc * rc
    return -(1.0 / (4 * PI)) * (math.log(d2) + math.log(img))


# ===========================================================================
#  Modified nodal analysis
# ===========================================================================
class Circuit(object):
    def __init__(self):
        self.idx = {}
        self.res = []            # (na, nb, R)
        self.vsrc = []           # (na, nb, V)
        self.ports = []          # (nodelist, Y indefinite)

    def n(self, name):
        if name not in self.idx:
            self.idx[name] = len(self.idx)
        return self.idx[name]

    def R(self, a, b, r):
        if r <= 0:
            r = 1e-9
        self.res.append((self.n(a), self.n(b), r))

    def V(self, a, b, v):
        self.vsrc.append((self.n(a), self.n(b), v))

    def port(self, nodes, Y):
        self.ports.append(([self.n(k) for k in nodes], Y))

    def solve(self, ground):
        g = self.n(ground)
        N = len(self.idx)
        M = len(self.vsrc)
        sz = N + M
        A = [[0.0] * sz for _ in range(sz)]
        rhs = [0.0] * sz
        for (a, b, r) in self.res:
            gg = 1.0 / r
            A[a][a] += gg; A[b][b] += gg; A[a][b] -= gg; A[b][a] -= gg
        for nodes, Y in self.ports:
            for i, ni in enumerate(nodes):
                for j, nj in enumerate(nodes):
                    A[ni][nj] += Y[i][j]
        for k in range(N):                      # leakage to keep matrix regular
            A[k][k] += 1e-13
        for m, (a, b, v) in enumerate(self.vsrc):
            r = N + m
            A[a][r] += 1.0; A[b][r] -= 1.0
            A[r][a] += 1.0; A[r][b] -= 1.0
            rhs[r] = v
        for k in range(sz):                     # ground
            A[g][k] = 0.0
        A[g][g] = 1.0
        rhs[g] = 0.0
        x = mat_solve(A, rhs)
        if x is None:
            return None
        return {name: x[i] for name, i in self.idx.items()}


def indefinite_Y(Z):
    """n-terminal impedance description (V_i = sum_j Z_ij I_j, sum I = 0)
       -> indefinite nodal admittance matrix."""
    n = len(Z)
    if n < 2:
        return None
    m = n - 1
    M = [[Z[i + 1][j + 1] - Z[0][j + 1] - Z[i + 1][0] + Z[0][0] for j in range(m)]
         for i in range(m)]
    Yr = mat_inv(M)
    if Yr is None:
        return None
    Y = [[0.0] * n for _ in range(n)]
    for i in range(m):
        for j in range(m):
            Y[i + 1][j + 1] = Yr[i][j]
    for j in range(m):
        s = sum(Yr[i][j] for i in range(m))
        Y[0][j + 1] = -s
    for i in range(m):
        s = sum(Yr[i][j] for j in range(m))
        Y[i + 1][0] = -s
    Y[0][0] = sum(sum(r) for r in Yr)
    return Y


# ===========================================================================
#  Apparatus
# ===========================================================================
S_PITCH = 20.0                       # pin pitch of the collinear row [mm]
SQ_HALF = 33.0                       # half side of the van-der-Pauw square [mm]
PLATE_R = 52.0                       # radius of the Plexiglas plate [mm]

#   local pin coordinates on the plate  (plate centre = origin)
PIN_XY = [(-1.5 * S_PITCH, 0.0), (-0.5 * S_PITCH, 0.0),
          (0.5 * S_PITCH, 0.0), (1.5 * S_PITCH, 0.0),
          (-SQ_HALF, SQ_HALF), (SQ_HALF, SQ_HALF),
          (SQ_HALF, -SQ_HALF), (-SQ_HALF, -SQ_HALF)]
PIN_NAME = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]

WAFER_D = 100.0
WAFER_FLAT = 32.5                    # chord length of the wafer flat [mm]
CR_THICK_NM = 8.0
PAPER_L0 = 297.0
PAPER_W0 = 210.0


class Session(object):
    """Hidden, per-session ground truth.  Never shown to the student."""

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1, 10 ** 9)
        self.seed = seed
        rng = random.Random(seed)
        self.rng = rng
        self.rho_paper = 4600.0 * rng.uniform(0.94, 1.06)     # ohm/square
        self.rho_cr = 165.0 * rng.uniform(0.94, 1.06)         # ohm/square
        self.t_cr = CR_THICK_NM * 1e-9                        # m  (nominal 8 nm)
        self.wafer_id = rng.randint(1, 450)
        self.Rc = [rng.uniform(80.0, 620.0) for _ in range(8)]  # contact resistance
        self.R_ohmic = 1000.0 * rng.uniform(0.97, 1.03)
        self.paper_W = PAPER_W0 + rng.uniform(-1.0, 1.0)
        self.paper_L = PAPER_L0 + rng.uniform(-1.0, 1.0)


# ---------------------------------------------------------------- samples ---
class Sample(object):
    kind = "none"

    def contains(self, x, y):
        return False

    def G(self, x1, y1, x2, y2):
        return 0.0


class PaperSample(Sample):
    """Graphite paper.  Long side (length L) is horizontal on the bench,
       width W is vertical.  Origin at the centre of the sheet."""
    kind = "paper"

    def __init__(self, ses):
        self.ses = ses
        self.W = ses.paper_W
        self.L = ses.paper_L
        self.cuts = []

    def contains(self, x, y):
        return abs(x) <= self.L / 2.0 + 1e-9 and abs(y) <= self.W / 2.0 + 1e-9

    def G(self, x1, y1, x2, y2):
        return G_strip(x1, y1 + self.W / 2.0, x2, y2 + self.W / 2.0, self.W)

    def rho(self):
        return self.ses.rho_paper

    def cut(self, new_W):
        self.cuts.append((self.W, new_W))
        self.W = new_W


class WaferSample(Sample):
    """Cr coated Si wafer, radius 50 mm, one flat.  Origin at the centre.
       `flat_ang` is the direction of the outward normal of the flat."""
    kind = "wafer"

    def __init__(self, ses):
        self.ses = ses
        self.a = WAFER_D / 2.0
        self.flat_ang = 0.0
        hc = WAFER_FLAT / 2.0
        self.flat_d = math.sqrt(self.a ** 2 - hc ** 2)

    def contains(self, x, y):
        if x * x + y * y > self.a ** 2:
            return False
        d = x * math.cos(self.flat_ang) + y * math.sin(self.flat_ang)
        return d <= self.flat_d

    def G(self, x1, y1, x2, y2):
        return G_disc(x1, y1, x2, y2, self.a)

    def rho(self):
        return self.ses.rho_cr


class ResistorSample(Sample):
    kind = "resistor"


# ------------------------------------------------------------- plate -------
class ProbePlate(object):
    def __init__(self):
        self.cx = 0.0
        self.cy = 0.0
        self.ang = 0.0                        # deg
        self.down = [False] * 8
        self.placed_on = None                 # "paper" / "wafer" / None

    def pin_pos(self, i):
        a = math.radians(self.ang)
        x, y = PIN_XY[i]
        return (self.cx + x * math.cos(a) - y * math.sin(a),
                self.cy + x * math.sin(a) + y * math.cos(a))


# ------------------------------------------------------- signal generator --
class SignalGen(object):
    """Battery driven adjustable generator, used here as a DC source."""

    def __init__(self):
        self.powered = False                  # USB cable from battery pack
        self.turns_v = 0.0                    # left pot, 'adjust voltage'
        self.turns_a = 0.0                    # right pot, 'speaker amplitude'
        self.spk_on = False                   # toggle switch (8)
        self.R_out = 22.0

    def voltage(self):
        if not self.powered:
            return 0.0
        return max(0.0, min(5.0, 5.0 * self.turns_v / 12.0))

    def monitor(self):
        if not (self.powered and self.spk_on):
            return 0.0
        return max(0.0, min(2.4, 2.4 * self.turns_a / 12.0))


# ------------------------------------------------------------ multimeter ---
DMM_V_RANGES = [("200 mV", 0.1999, 1e-4), ("2 V", 1.999, 1e-3),
                ("20 V", 19.99, 1e-2), ("200 V", 199.9, 1e-1)]
DMM_A_RANGES = [("200 uA", 199.9e-6, 1e-7, 1000.0), ("2 mA", 1.999e-3, 1e-6, 100.0),
                ("20 mA", 19.99e-3, 1e-5, 10.0), ("200 mA", 199.9e-3, 1e-4, 1.0)]


class DMM(object):
    def __init__(self, name):
        self.name = name
        self.mode = "V"                # "V" / "A" / "OFF"
        self.vr = 1                    # index into DMM_V_RANGES
        self.ar = 1
        self.raw = 0.0                 # SI value delivered by the circuit
        self.connected = False

    def burden(self):
        if self.mode == "A":
            return DMM_A_RANGES[self.ar][3]
        return 1.0e7                   # 10 Mohm input impedance

    def range_label(self):
        return DMM_V_RANGES[self.vr][0] if self.mode == "V" else DMM_A_RANGES[self.ar][0]

    def display(self, rng):
        if self.mode == "OFF" or not self.connected:
            return "     "
        if self.mode == "V":
            lab, full, step = DMM_V_RANGES[self.vr]
            unit = "mV" if self.vr == 0 else "V"
            scale = 1000.0 if self.vr == 0 else 1.0
        else:
            lab, full, step, _ = DMM_A_RANGES[self.ar]
            unit = "uA" if self.ar == 0 else "mA"
            scale = 1e6 if self.ar == 0 else 1e3
        val = self.raw
        val *= 1.0 + rng.gauss(0.0, 0.0012)          # 0.12 % rms noise
        val += rng.gauss(0.0, 0.4) * step            # digit noise
        if abs(val) > full * 1.0001:
            return " O L "
        q = round(val / step) * step
        digits = max(0, int(round(-math.log10(step * scale))))
        return ("%%.%df" % digits) % (q * scale) + " " + unit


# ===========================================================================
#  Bench = wiring + circuit evaluation
# ===========================================================================
TERMINALS = ["SG.V", "SG.MON", "SG.GND", "SG.SPK+", "SG.SPK-",
             "M1.IN", "M1.COM", "M2.IN", "M2.COM",
             "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8",
             "R.a", "R.b"]


class Bench(object):
    def __init__(self, ses):
        self.ses = ses
        self.sg = SignalGen()
        self.m1 = DMM("M1")
        self.m2 = DMM("M2")
        self.plate = ProbePlate()
        self.paper = PaperSample(ses)
        self.wafer = WaferSample(ses)
        self.wires = []                       # (a, b)
        self.have = set()                     # assembled items
        self.active = None                    # "paper" / "wafer" / None
        self.rng = random.Random(ses.seed ^ 0x5eed)

    # -------------------------------------------------- wiring bookkeeping --
    def add_wire(self, a, b):
        if a == b:
            return False
        for (p, q) in self.wires:
            if {p, q} == {a, b}:
                return False
        self.wires.append((a, b))
        return True

    def del_wire(self, i):
        if 0 <= i < len(self.wires):
            self.wires.pop(i)

    def _union(self):
        par = {t: t for t in TERMINALS}

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x
        for a, b in self.wires:
            ra, rb = find(a), find(b)
            if ra != rb:
                par[ra] = rb
        return {t: find(t) for t in TERMINALS}

    # ------------------------------------------------------- sample matrix --
    def active_sample(self):
        if self.active == "paper":
            return self.paper
        if self.active == "wafer":
            return self.wafer
        return None

    def contacting_pins(self):
        smp = self.active_sample()
        if smp is None or self.plate.placed_on != self.active:
            return []
        out = []
        for i in range(8):
            if not self.plate.down[i]:
                continue
            x, y = self.plate.pin_pos(i)
            if smp.contains(x, y):
                out.append(i)
        return out

    def sample_Z(self, pins):
        smp = self.active_sample()
        rho = smp.rho()
        pos = [self.plate.pin_pos(i) for i in pins]
        n = len(pins)
        Z = [[rho * smp.G(pos[i][0], pos[i][1], pos[j][0], pos[j][1])
              for j in range(n)] for i in range(n)]
        for i, p in enumerate(pins):
            Z[i][i] += self.ses.Rc[p]
        return Z

    # ------------------------------------------------------------- solve ----
    def evaluate(self):
        ck = Circuit()
        u = self._union()
        gnd = u["SG.GND"]
        ck.n(gnd)
        # signal generator, DC mode
        ck.V("SG_INT", gnd, self.sg.voltage())
        ck.R("SG_INT", u["SG.V"], self.sg.R_out)
        ck.R(u["SG.MON"], gnd, 1.0e6)          # monitor output, quiet in DC mode
        # multimeters
        for m, a, b in ((self.m1, "M1.IN", "M1.COM"), (self.m2, "M2.IN", "M2.COM")):
            m.connected = (m.mode != "OFF")
            if m.mode == "OFF":
                ck.R(u[a], u[b], 1.0e11)
            else:
                ck.R(u[a], u[b], m.burden())
        # ohmic resistor
        if "resistor" in self.have:
            ck.R(u["R.a"], u["R.b"], self.ses.R_ohmic)
        else:
            ck.R(u["R.a"], u["R.b"], 1.0e11)
        # sample
        pins = self.contacting_pins()
        if len(pins) >= 2:
            Y = indefinite_Y(self.sample_Z(pins))
            if Y is not None:
                ck.port([u[PIN_NAME[i]] for i in pins], Y)
        sol = ck.solve(gnd)
        if sol is None:
            self.m1.raw = self.m2.raw = 0.0
            return
        for m, a, b in ((self.m1, "M1.IN", "M1.COM"), (self.m2, "M2.IN", "M2.COM")):
            dv = sol.get(u[a], 0.0) - sol.get(u[b], 0.0)
            if m.mode == "V":
                m.raw = dv
            elif m.mode == "A":
                m.raw = dv / m.burden()
            else:
                m.raw = 0.0


# ===========================================================================
#  GUI
# ===========================================================================
import tkinter as tk
from tkinter import ttk, messagebox

BG = "#f2f0ea"
PANEL = "#e6e2d8"
INK = "#20242b"
ACC = "#8fb339"

PARTS = [
    ("battery",  "USB 케이블이 있는 배터리 팩", "Battery pack with USB cable", "power",  []),
    ("siggen",   "조절 가능한 신호 발생기",      "Adjustable signal generator", "power",  ["battery"]),
    ("dmm1",     "디지털 멀티미터 1",            "Digital multimeter 1",       "meter",  []),
    ("dmm2",     "디지털 멀티미터 2",            "Digital multimeter 2",       "meter",  []),
    ("paper",    "흑연 코팅 전도성 종이",        "Graphite conductive paper",  "sample", []),
    ("wafer",    "크로뮴 코팅 실리콘 웨이퍼",    "Cr coated silicon wafer",    "sample", []),
    ("plate",    "스프링 핀 8개 플렉시글라스 판", "Plexiglas plate, 8 pins",   "sample", ["paper|wafer"]),
    ("resistor", "옴 저항기",                    "Ohmic resistor",             "meter",  []),
    ("cables",   "케이블 세트 (악어클립/4 mm)",  "Cable set (clips / 4 mm)",   "cable",
     ["siggen", "dmm1", "dmm2", "plate"]),
    ("tools",    "드라이버 · 가위 · 자 · 스티커", "Driver, scissors, ruler, stickers", "tool", []),
]

ZONES = {
    "power":  (30, 30, 300, 200, "전원부", "Power"),
    "meter":  (320, 30, 620, 200, "계측기", "Instruments"),
    "sample": (30, 215, 620, 400, "시료 / 탐침", "Sample / probes"),
    "cable":  (30, 415, 320, 545, "배선", "Wiring"),
    "tool":   (335, 415, 620, 545, "도구", "Tools"),
}

REQUIRED = ["battery", "siggen", "dmm1", "dmm2", "plate", "cables", "tools"]

#   fixed resting place of each part inside its zone (keeps the bench tidy)
PART_POS = {
    "battery": (14, 26), "siggen": (14, 96),
    "dmm1": (14, 26), "dmm2": (96, 26), "resistor": (180, 60),
    "paper": (14, 30), "wafer": (188, 40), "plate": (300, 34),
    "cables": (20, 40), "tools": (14, 42),
}


class AssemblyTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.placed = {}
        self.drag = None

        left = tk.Frame(self, bg=PANEL, width=290)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Label(left, text=T("부품 상자", "Parts box"), bg=PANEL, fg=INK,
                 font=("TkDefaultFont", 12, "bold")).pack(pady=(10, 4))
        tk.Label(left, text=T("부품을 작업대 위 알맞은 구역으로 끌어다 놓아라.",
                              "Drag each part onto the correct area of the bench."),
                 bg=PANEL, fg="#555", wraplength=265, justify="left").pack(padx=12)
        self.bin = tk.Canvas(left, bg=PANEL, highlightthickness=0, width=280, height=560)
        self.bin.pack(padx=6, pady=8)

        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        self.cv = tk.Canvas(right, bg=BG, highlightthickness=0, width=660, height=570)
        self.cv.pack(padx=8, pady=8, anchor="nw")
        self.log = tk.Text(right, height=8, bg="#fbfaf6", fg=INK, wrap="word",
                           relief="flat", font=("TkFixedFont", 9))
        self.log.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.bin.bind("<ButtonPress-1>", self.on_press)
        self.bin.bind("<B1-Motion>", self.on_move)
        self.bin.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<ButtonPress-1>", self.on_press_bench)

        self.redraw_bin()
        self.redraw_bench()
        self.say(T("실험 E-I 장비를 조립하라.  배터리 팩 → 신호 발생기 순서를 지켜야 한다.",
                   "Assemble the E-I apparatus.  Battery pack must come before the generator."))

    # ------------------------------------------------------------------ log
    def say(self, s):
        self.log.insert("end", "  " + s + "\n")
        self.log.see("end")

    # ------------------------------------------------------------- drawing
    def redraw_bin(self):
        self.bin.delete("all")
        y = 12
        self.bin_items = []
        for pid, ko, en, zone, req in PARTS:
            if pid in self.placed:
                continue
            r = self.bin.create_rectangle(10, y, 268, y + 46, fill="#fffdf7",
                                          outline="#b9b3a2", width=1)
            t = self.bin.create_text(20, y + 23, anchor="w", text=T(ko, en),
                                     fill=INK, font=("TkDefaultFont", 9))
            self.bin_items.append((pid, r, t, y))
            y += 52

    def zone_at(self, x, y):
        for z, (x0, y0, x1, y1, ko, en) in ZONES.items():
            if x0 <= x <= x1 and y0 <= y <= y1:
                return z
        return None

    def redraw_bench(self):
        c = self.cv
        c.delete("all")
        c.create_rectangle(8, 8, 652, 562, fill="#ece7db", outline="#c9c2af", width=2)
        c.create_text(330, 574, text="", fill=INK)
        for z, (x0, y0, x1, y1, ko, en) in ZONES.items():
            c.create_rectangle(x0, y0, x1, y1, fill="#f6f4ec", outline="#c1baa6",
                               dash=(4, 3))
            c.create_text(x0 + 8, y0 + 12, anchor="w", text=T(ko, en),
                          fill="#8a8371", font=("TkDefaultFont", 9, "bold"))
        for pid, (zx, zy) in self.placed.items():
            self.draw_part(pid, zx, zy)
        ok = all(p in self.placed for p in REQUIRED) and \
            ("paper" in self.placed or "wafer" in self.placed)
        c.create_rectangle(430, 528, 645, 556, fill=ACC if ok else "#cfc9b8",
                           outline="")
        c.create_text(537, 542, text=T("조립 완료 — 실험대로", "Assembled - go to bench")
                      if ok else T("부품이 더 필요하다", "More parts required"),
                      fill="white" if ok else "#7a7462",
                      font=("TkDefaultFont", 9, "bold"), tags="donebtn")
        self.assembled = ok
        if ok:
            self.app.enable_bench()

    def draw_part(self, pid, x, y):
        c = self.cv
        if pid == "battery":
            c.create_rectangle(x, y, x + 92, y + 34, fill="#f7f7f7", outline="#999")
            c.create_rectangle(x + 6, y + 6, x + 30, y + 28, fill="#5f7fb8", outline="#3d5a8a")
            c.create_text(x + 62, y + 17, text="POWER", font=("TkFixedFont", 7), fill="#333")
            c.create_line(x + 92, y + 17, x + 118, y + 8, fill="#444", width=2, smooth=True)
        elif pid == "siggen":
            c.create_rectangle(x, y, x + 118, y + 62, fill="#cfe0c2", outline="#7f9a6c", width=2)
            c.create_rectangle(x + 30, y + 2, x + 88, y + 16, fill="#222", outline="#111")
            for i, col in enumerate(("#3c6fb0", "#3c6fb0")):
                c.create_oval(x + 18 + i * 58, y + 22, x + 34 + i * 58, y + 38,
                              fill=col, outline="#20406b")
            for i, col in enumerate(("#c9a227", "#d8d8d8", "#222")):
                c.create_oval(x + 24 + i * 28, y + 44, x + 38 + i * 28, y + 58,
                              fill=col, outline="#555")
        elif pid in ("dmm1", "dmm2"):
            c.create_rectangle(x, y, x + 60, y + 96, fill="#2f62a8", outline="#1d3f6e", width=2)
            c.create_rectangle(x + 7, y + 8, x + 53, y + 30, fill="#cfe6c8", outline="#5c7a52")
            c.create_oval(x + 16, y + 38, x + 44, y + 66, fill="#e8e8e8", outline="#888")
            c.create_oval(x + 14, y + 76, x + 22, y + 84, fill="#111", outline="#000")
            c.create_oval(x + 38, y + 76, x + 46, y + 84, fill="#c33", outline="#000")
        elif pid == "paper":
            c.create_rectangle(x, y, x + 150, y + 106, fill="#26262a", outline="#111")
            c.create_rectangle(x + 150, y, x + 156, y + 106, fill="#8a6b45", outline="#111")
        elif pid == "wafer":
            c.create_oval(x, y, x + 88, y + 88, fill="#8f9296", outline="#5d6064", width=2)
            c.create_polygon(x + 84, y + 28, x + 88, y + 34, x + 88, y + 54, x + 84, y + 60,
                             fill=BG, outline="")
            c.create_arc(x + 8, y + 8, x + 80, y + 80, start=200, extent=140,
                         style="arc", outline="#c9ccd0")
        elif pid == "plate":
            c.create_oval(x, y, x + 104, y + 104, fill="#dfe9ee", outline="#9fb4bd", width=2)
            for px, py in PIN_XY:
                cx = x + 52 + px * 0.47
                cy = y + 52 - py * 0.47
                c.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill="#c9a227", outline="#7d6516")
        elif pid == "resistor":
            c.create_line(x, y + 10, x + 12, y + 10, fill="#666", width=2)
            c.create_rectangle(x + 12, y + 3, x + 44, y + 17, fill="#d8c9a0", outline="#8a7c55")
            c.create_line(x + 44, y + 10, x + 56, y + 10, fill="#666", width=2)
        elif pid == "cables":
            cols = ["#c33", "#333", "#2a7", "#25c", "#dd0"]
            for i, col in enumerate(cols):
                c.create_line(x, y + 6 + i * 9, x + 40, y + 2 + i * 9, x + 82, y + 10 + i * 9,
                              fill=col, width=3, smooth=True)
        elif pid == "tools":
            c.create_line(x, y + 20, x + 40, y + 20, fill="#c9a227", width=4)
            c.create_rectangle(x + 40, y + 15, x + 52, y + 25, fill="#3b7", outline="#295")
            c.create_line(x + 60, y + 6, x + 92, y + 26, fill="#999", width=3)
            c.create_line(x + 60, y + 26, x + 92, y + 6, fill="#999", width=3)
            c.create_rectangle(x + 100, y + 12, x + 190, y + 24, fill="#f6e7a8", outline="#b5a35c")
            for i in range(10):
                c.create_line(x + 104 + i * 9, y + 24, x + 104 + i * 9, y + 18, fill="#8a7c55")

    # ------------------------------------------------------------ dragging
    def on_press(self, ev):
        for pid, r, t, y in getattr(self, "bin_items", []):
            if y <= ev.y <= y + 46:
                self.drag = pid
                self.ghost = self.bin.create_text(ev.x, ev.y, text="●", fill=ACC)
                return

    def on_move(self, ev):
        if self.drag:
            self.bin.coords(self.ghost, ev.x, ev.y)

    def on_release(self, ev):
        if not self.drag:
            return
        pid = self.drag
        self.drag = None
        self.bin.delete(self.ghost)
        gx = self.bin.winfo_rootx() + ev.x - self.cv.winfo_rootx()
        gy = self.bin.winfo_rooty() + ev.y - self.cv.winfo_rooty()
        self.try_place(pid, gx, gy)

    def on_press_bench(self, ev):
        it = self.cv.find_withtag("current")
        if it and "donebtn" in self.cv.gettags(it[0]) and getattr(self, "assembled", False):
            self.app.nb.select(1)

    def try_place(self, pid, x, y):
        spec = [p for p in PARTS if p[0] == pid][0]
        _, ko, en, zone, req = spec
        z = self.zone_at(x, y)
        if z is None:
            self.say(T("작업대 밖이다. 부품을 상자로 되돌린다.",
                       "Outside the bench - the part goes back into the box."))
            return
        if z != zone:
            self.say(T("%s: 이 구역에 놓을 수 없다." % T(ko, en),
                       "%s cannot be placed in this area." % T(ko, en)))
            return
        for r in req:
            alts = r.split("|")
            if not any(a in self.placed for a in alts):
                names = " / ".join(T(p[1], p[2]) for p in PARTS if p[0] in alts)
                self.say(T("%s 먼저 필요하다 → %s" % (names, T(ko, en)),
                           "%s is required first -> %s" % (names, T(ko, en))))
                return
        x0, y0, x1, y1, _, _ = ZONES[zone]
        dx, dy = PART_POS.get(pid, (14, 26))
        self.placed[pid] = (x0 + dx, y0 + dy)
        if pid == "paper":
            self.app.bench.have.add("paper")
            if self.app.bench.active is None:
                self.app.bench.active = "paper"
        if pid == "wafer":
            self.app.bench.have.add("wafer")
            if self.app.bench.active is None:
                self.app.bench.active = "wafer"
        if pid == "resistor":
            self.app.bench.have.add("resistor")
        if pid == "siggen":
            self.app.bench.sg.powered = True
        self.say(T("놓음: %s" % T(ko, en), "Placed: %s" % T(ko, en)))
        self.redraw_bin()
        self.redraw_bench()


WIRE_COLORS = ["#cc2b2b", "#1b1b1b", "#1f7a3f", "#2255cc", "#d8b800",
               "#8a3fb0", "#0f9fa8", "#c06010", "#777777", "#b02b6a"]


class BenchTab(ttk.Frame):
    SX, SY = 12, 26                  # sample viewport origin
    SW, SH = 664, 566

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.b = app.bench
        self.term = {}
        self.sel_term = None
        self.mode = "probe"          # "probe" | "cut" | "ruler"
        self.drag_plate = None
        self.cut_y = None

        self.cv = tk.Canvas(self, bg=BG, highlightthickness=0, width=1466, height=612)
        self.cv.pack(side="top", padx=6, pady=(6, 2))
        self.cv.bind("<Button-1>", self.on_click)
        self.cv.bind("<B1-Motion>", self.on_drag)
        self.cv.bind("<ButtonRelease-1>", self.on_up)
        self.cv.bind("<Motion>", self.on_hover)

        self.build_controls()
        self.redraw()
        self.tick()

    # ==================================================================== UI
    def build_controls(self):
        f = tk.Frame(self, bg=BG)
        f.pack(side="top", fill="both", expand=True, padx=6)

        def box(title, col):
            g = tk.LabelFrame(f, text=title, bg=BG, fg=INK, padx=6, pady=4)
            g.grid(row=0, column=col, sticky="nsew", padx=4)
            return g

        # ---- sample / plate
        g = box(T("시료 · 탐침판", "Sample / probe plate"), 0)
        self.v_sample = tk.StringVar(value=self.b.active or "paper")
        for val, ko, en in (("paper", "전도성 종이", "conductive paper"),
                            ("wafer", "실리콘 웨이퍼", "silicon wafer")):
            tk.Radiobutton(g, text=T(ko, en), variable=self.v_sample, value=val,
                           bg=BG, command=self.set_sample).pack(anchor="w")
        r = tk.Frame(g, bg=BG); r.pack(anchor="w", pady=(4, 0))
        tk.Button(r, text=T("판 올림", "plate on"), width=8,
                  command=self.plate_on).pack(side="left")
        tk.Button(r, text=T("판 내림", "plate off"), width=8,
                  command=self.plate_off).pack(side="left")
        r = tk.Frame(g, bg=BG); r.pack(anchor="w")
        tk.Button(r, text="⟲ 15°", width=8, command=lambda: self.rot(15)).pack(side="left")
        tk.Button(r, text="⟳ 15°", width=8, command=lambda: self.rot(-15)).pack(side="left")
        r = tk.Frame(g, bg=BG); r.pack(anchor="w")
        tk.Button(r, text=T("모든 핀 올림", "all pins up"), width=17,
                  command=self.pins_up).pack(side="left")
        r = tk.Frame(g, bg=BG); r.pack(anchor="w", pady=(4, 0))
        self.v_mode = tk.StringVar(value="probe")
        for val, ko, en in (("probe", "탐침", "probe"), ("ruler", "자", "ruler"),
                            ("cut", "가위", "scissors")):
            tk.Radiobutton(r, text=T(ko, en), variable=self.v_mode, value=val,
                           bg=BG, command=self.set_mode).pack(side="left")

        # ---- signal generator
        g = box(T("신호 발생기", "Signal generator"), 1)
        tk.Label(g, text=T("adjust voltage (3)", "adjust voltage (3)"), bg=BG).pack()
        r = tk.Frame(g, bg=BG); r.pack()
        for lab, d in (("◀◀", -0.5), ("◀", -0.05), ("▶", 0.05), ("▶▶", 0.5)):
            tk.Button(r, text=lab, width=3,
                      command=lambda d=d: self.turn_v(d)).pack(side="left")
        tk.Label(g, text=T("speaker amplitude (4)", "speaker amplitude (4)"),
                 bg=BG).pack(pady=(6, 0))
        r = tk.Frame(g, bg=BG); r.pack()
        for lab, d in (("◀◀", -0.5), ("◀", -0.05), ("▶", 0.05), ("▶▶", 0.5)):
            tk.Button(r, text=lab, width=3,
                      command=lambda d=d: self.turn_a(d)).pack(side="left")
        self.v_spk = tk.IntVar(value=0)
        tk.Checkbutton(g, text=T("토글 스위치 (8)", "toggle switch (8)"),
                       variable=self.v_spk, bg=BG,
                       command=self.set_spk).pack(pady=(6, 0))

        # ---- multimeters
        for k, (m, col) in enumerate(((self.b.m1, 2), (self.b.m2, 3))):
            g = box(T("멀티미터 %d" % (k + 1), "Multimeter %d" % (k + 1)), col)
            mv = tk.StringVar(value=m.mode)
            setattr(self, "v_mm%d" % k, mv)
            r = tk.Frame(g, bg=BG); r.pack()
            for val in ("OFF", "V", "A"):
                tk.Radiobutton(r, text=val, variable=mv, value=val, bg=BG,
                               command=lambda m=m, mv=mv: self.set_mm(m, mv)).pack(side="left")
            lb = tk.Listbox(g, height=4, exportselection=False, width=12)
            lb.pack(pady=2)
            setattr(self, "lb%d" % k, lb)
            lb.bind("<<ListboxSelect>>", lambda e, m=m, k=k: self.set_range(m, k))
            self.fill_ranges(m, lb)

        # ---- wiring
        g = box(T("배선", "Wiring"), 4)
        tk.Label(g, text=T("단자를 두 번 눌러 케이블을 연결한다.",
                           "Click two terminals to lay a cable."),
                 bg=BG, fg="#666", wraplength=210, justify="left").pack(anchor="w")
        self.lbw = tk.Listbox(g, height=7, width=26, exportselection=False)
        self.lbw.pack(pady=2)
        r = tk.Frame(g, bg=BG); r.pack(anchor="w")
        tk.Button(r, text=T("선택 제거", "remove"), command=self.del_wire).pack(side="left")
        tk.Button(r, text=T("전부 제거", "clear all"), command=self.clear_wires).pack(side="left")
        self.msg = tk.Label(f, text="", bg=BG, fg="#8a3a1a", anchor="w")
        self.msg.grid(row=1, column=0, columnspan=5, sticky="we", pady=(4, 6))
        for c in range(5):
            f.grid_columnconfigure(c, weight=1)

    def fill_ranges(self, m, lb):
        lb.delete(0, "end")
        rows = DMM_V_RANGES if m.mode != "A" else DMM_A_RANGES
        for r in rows:
            lb.insert("end", r[0])
        lb.selection_clear(0, "end")
        lb.selection_set(m.vr if m.mode != "A" else m.ar)

    def set_mm(self, m, mv):
        m.mode = mv.get()
        k = 0 if m is self.b.m1 else 1
        self.fill_ranges(m, getattr(self, "lb%d" % k))
        self.redraw()

    def set_range(self, m, k):
        lb = getattr(self, "lb%d" % k)
        s = lb.curselection()
        if not s:
            return
        if m.mode == "A":
            m.ar = s[0]
        else:
            m.vr = s[0]

    def note(self, s):
        self.msg.config(text=s)

    # =============================================================== actions
    def set_sample(self):
        self.b.active = self.v_sample.get()
        if self.b.plate.placed_on and self.b.plate.placed_on != self.b.active:
            self.b.plate.placed_on = None
            self.note(T("탐침판을 다른 시료 위로 옮겨야 한다.",
                        "The probe plate must be moved onto the other sample."))
        self.redraw()

    def set_mode(self):
        self.mode = self.v_mode.get()
        if self.mode == "cut" and self.b.active != "paper":
            self.note(T("가위는 전도성 종이에만 사용한다.",
                        "The scissors are only for the conductive paper."))
        self.redraw()

    def plate_on(self):
        if "plate" not in self.app.asm.placed:
            self.note(T("탐침판이 조립되어 있지 않다.", "The probe plate is not assembled."))
            return
        self.b.plate.placed_on = self.b.active
        self.b.plate.cx = self.b.plate.cy = 0.0
        self.redraw()

    def plate_off(self):
        self.b.plate.placed_on = None
        self.redraw()

    def rot(self, d):
        self.b.plate.ang = (self.b.plate.ang + d) % 360
        self.redraw()

    def pins_up(self):
        self.b.plate.down = [False] * 8
        self.redraw()

    def turn_v(self, d):
        self.b.sg.turns_v = max(0.0, min(12.0, self.b.sg.turns_v + d))
        self.redraw()

    def turn_a(self, d):
        self.b.sg.turns_a = max(0.0, min(12.0, self.b.sg.turns_a + d))
        self.redraw()

    def set_spk(self):
        self.b.sg.spk_on = bool(self.v_spk.get())
        self.redraw()

    def del_wire(self):
        s = self.lbw.curselection()
        if s:
            self.b.del_wire(s[0])
            self.refresh_wirelist()
            self.redraw()

    def clear_wires(self):
        self.b.wires = []
        self.refresh_wirelist()
        self.redraw()

    def refresh_wirelist(self):
        self.lbw.delete(0, "end")
        for a, b in self.b.wires:
            self.lbw.insert("end", "%-7s — %s" % (a, b))

    # ============================================================== geometry
    def scale(self):
        return 2.0 if self.b.active == "paper" else 4.4

    def w2s(self, x, y):
        k = self.scale()
        return (self.SX + self.SW / 2.0 + x * k, self.SY + self.SH / 2.0 - y * k)

    def s2w(self, sx, sy):
        k = self.scale()
        return ((sx - self.SX - self.SW / 2.0) / k,
                (self.SY + self.SH / 2.0 - sy) / k)

    # =============================================================== drawing
    def redraw(self):
        c = self.cv
        c.delete("all")
        self.term = {}
        self.draw_sample_area()
        self.draw_siggen(694, 34)
        self.draw_dmm(self.b.m1, 1088, 34, T("멀티미터 1", "Multimeter 1"))
        self.draw_dmm(self.b.m2, 1258, 34, T("멀티미터 2", "Multimeter 2"))
        self.draw_resistor(694, 300)
        self.draw_pinstrip(694, 380)
        self.draw_wires()
        self.draw_legend(940, 300)

    # --------------------------------------------------------- sample area
    def draw_sample_area(self):
        c = self.cv
        c.create_rectangle(self.SX, self.SY, self.SX + self.SW, self.SY + self.SH,
                           fill="#ded8c8", outline="#b6ae98", width=2)
        c.create_text(self.SX + 8, self.SY - 12, anchor="w",
                      text=T("작업대 (위에서 본 모습)", "Bench, top view"),
                      fill="#6b6553", font=("TkDefaultFont", 9, "bold"))
        smp = self.b.active
        if smp == "paper":
            self.draw_paper()
        elif smp == "wafer":
            self.draw_wafer()
        if self.b.plate.placed_on == smp and smp:
            self.draw_plate()
        if self.mode == "ruler" or self.mode == "cut":
            self.draw_ruler()
        if self.mode == "cut" and self.cut_y is not None and smp == "paper":
            x0, _ = self.w2s(-self.b.paper.L / 2, 0)
            x1, _ = self.w2s(self.b.paper.L / 2, 0)
            c.create_line(x0, self.cut_y, x1, self.cut_y, fill="#e04a2f",
                          width=2, dash=(6, 4))

    def draw_paper(self):
        c = self.cv
        p = self.b.paper
        x0, y0 = self.w2s(-p.L / 2, p.W / 2)
        x1, y1 = self.w2s(p.L / 2, -p.W / 2)
        c.create_rectangle(x0 + 4, y0 + 4, x1 + 4, y1 + 4, fill="#c6bfae", outline="")
        c.create_rectangle(x0, y0, x1, y1, fill="#2a2a2e", outline="#101012", width=1)
        for i in range(140):                       # graphite speckle
            rx = self.b.rng.uniform(x0 + 2, x1 - 2)
            ry = self.b.rng.uniform(y0 + 2, y1 - 2)
            c.create_oval(rx, ry, rx + 1.4, ry + 1.4, fill="#3a3a40", outline="")
        c.create_text((x0 + x1) / 2, y0 - 12, text=T("코팅면(검은색)이 위",
                                                     "coated (black) side up"),
                      fill="#6b6553", font=("TkDefaultFont", 8))
        c.create_oval(x0 + 8, y0 + 8, x0 + 20, y0 + 20, fill="#ff5a2b", outline="")

    def draw_wafer(self):
        c = self.cv
        w = self.b.wafer
        k = self.scale()
        cx, cy = self.w2s(0, 0)
        r = w.a * k
        c.create_oval(cx - r + 3, cy - r + 3, cx + r + 3, cy + r + 3,
                      fill="#c6bfae", outline="")
        c.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#9aa0a6",
                      outline="#5f646a", width=2)
        hc = WAFER_FLAT / 2.0 * k
        d = w.flat_d * k
        ang = w.flat_ang
        ux, uy = math.cos(ang), -math.sin(ang)
        px, py = -uy, ux
        c.create_polygon(cx + ux * d + px * hc, cy + uy * d + py * hc,
                         cx + ux * d - px * hc, cy + uy * d - py * hc,
                         cx + ux * r * 1.1 - px * hc * 1.6, cy + uy * r * 1.1 - py * hc * 1.6,
                         cx + ux * r * 1.1 + px * hc * 1.6, cy + uy * r * 1.1 + py * hc * 1.6,
                         fill="#ded8c8", outline="")
        c.create_arc(cx - r * .82, cy - r * .82, cx + r * .82, cy + r * .82,
                     start=110, extent=110, style="arc", outline="#c8ced4", width=6)
        c.create_text(cx, cy - r - 16, text=T("웨이퍼 홀더 번호  No. %d" % self.b.ses.wafer_id,
                                              "wafer holder No. %d" % self.b.ses.wafer_id),
                      fill="#6b6553", font=("TkDefaultFont", 9, "bold"))
        c.create_text(cx + ux * (r + 22), cy + uy * (r + 22), text="flat",
                      fill="#6b6553", font=("TkDefaultFont", 8))

    def draw_plate(self):
        c = self.cv
        pl = self.b.plate
        k = self.scale()
        cx, cy = self.w2s(pl.cx, pl.cy)
        r = PLATE_R * k
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#7fa3b5", width=2,
                      dash=(3, 2))
        a = math.radians(pl.ang)
        for i in range(8):
            x, y = pl.pin_pos(i)
            sx, sy = self.w2s(x, y)
            down = pl.down[i]
            smp = self.b.active_sample()
            on = down and smp is not None and smp.contains(x, y)
            fill = "#3a2f0a" if on else ("#c9a227" if down else "#efe3b4")
            c.create_oval(sx - 6, sy - 6, sx + 6, sy + 6, fill=fill,
                          outline="#7d6516", width=2, tags=("pin%d" % i,))
            c.create_text(sx, sy - 13, text=PIN_NAME[i], fill="#33506b",
                          font=("TkDefaultFont", 7, "bold"))
        # row axis marker
        p0 = self.w2s(*pl.pin_pos(0)); p3 = self.w2s(*pl.pin_pos(3))
        c.create_line(p0[0], p0[1], p3[0], p3[1], fill="#7fa3b5", dash=(2, 3))

    def draw_ruler(self):
        c = self.cv
        k = self.scale()
        smp = self.b.active_sample()
        if smp is None:
            return
        if self.b.active == "paper":
            W = self.b.paper.W
            L = self.b.paper.L
            xr, _ = self.w2s(-L / 2, 0)
            xr -= 26
            ybot = self.w2s(0, -W / 2)[1]
            c.create_rectangle(xr - 4, self.w2s(0, W / 2)[1], xr + 22, ybot,
                               fill="#f6e7a8", outline="#b5a35c")
            n = int(W)
            for mm in range(0, n + 1):
                y = ybot - mm * k
                ln = 6 if mm % 10 else (12 if mm % 50 else 18)
                c.create_line(xr + 22 - ln, y, xr + 22, y, fill="#7a6b34",
                              width=2 if mm % 10 == 0 else 1)
                if mm % 20 == 0:
                    c.create_text(xr + 2, y, text=str(mm // 10), anchor="w",
                                  fill="#5a4d20", font=("TkDefaultFont", 7))
            c.create_text(xr + 9, self.w2s(0, W / 2)[1] - 10, text="cm",
                          fill="#5a4d20", font=("TkDefaultFont", 7))
        else:
            cx, cy = self.w2s(0, 0)
            r = self.b.wafer.a * k
            c.create_rectangle(cx - r, cy + r + 8, cx + r, cy + r + 30,
                               fill="#f6e7a8", outline="#b5a35c")
            for mm in range(0, int(2 * self.b.wafer.a) + 1):
                x = cx - r + mm * k
                ln = 6 if mm % 10 else (12 if mm % 50 else 18)
                c.create_line(x, cy + r + 30 - ln, x, cy + r + 30, fill="#7a6b34",
                              width=2 if mm % 10 == 0 else 1)
                if mm % 20 == 0:
                    c.create_text(x, cy + r + 14, text=str(mm // 10), fill="#5a4d20",
                                  font=("TkDefaultFont", 7))

    # ------------------------------------------------------- signal gen ----
    def draw_siggen(self, x, y):
        c = self.cv
        sg = self.b.sg
        c.create_rectangle(x, y, x + 380, y + 244, fill="#dbe7d0", outline="#8ca57a",
                           width=2)
        c.create_text(x + 10, y + 14, anchor="w", text=T("신호 발생기 (DC 모드)",
                                                         "Signal generator (DC mode)"),
                      fill="#3d5230", font=("TkDefaultFont", 10, "bold"))
        c.create_rectangle(x + 20, y + 30, x + 130, y + 62, fill="#1c1c1c", outline="#000")
        c.create_rectangle(x + 40, y + 36, x + 66, y + 56, fill="#d02020", outline="#600")
        c.create_rectangle(x + 78, y + 36, x + 104, y + 56, fill="#111", outline="#000")
        c.create_text(x + 75, y + 72, text=T("스피커 단자 (2)", "speaker terminals (2)"),
                      fill="#4a5a40", font=("TkDefaultFont", 8))
        self.term_dot(x + 53, y + 46, "SG.SPK+", "#d02020")
        self.term_dot(x + 91, y + 46, "SG.SPK-", "#111111")
        # pots
        for (px, tn, lab, turns) in ((x + 190, "3", T("adjust voltage", "adjust voltage"),
                                      sg.turns_v),
                                     (x + 300, "4", T("speaker amplitude", "speaker amplitude"),
                                      sg.turns_a)):
            c.create_oval(px - 22, y + 28, px + 22, y + 72, fill="#3c6fb0",
                          outline="#20406b", width=2)
            a = math.radians(-90 + turns * 300.0)
            c.create_line(px, y + 50, px + 18 * math.cos(a), y + 50 + 18 * math.sin(a),
                          fill="#ffffff", width=3)
            c.create_text(px, y + 84, text="(%s) %s" % (tn, lab), fill="#4a5a40",
                          font=("TkDefaultFont", 8))
        # sockets
        c.create_text(x + 10, y + 112, anchor="w", text=T("출력 소켓", "output sockets"),
                      fill="#4a5a40", font=("TkDefaultFont", 8))
        self.socket(x + 46, y + 142, "SG.V", "#d8b800", "(5) voltage")
        self.socket(x + 146, y + 142, "SG.MON", "#e8e8e8", "(6) spk. monitor")
        self.socket(x + 246, y + 142, "SG.GND", "#222222", "(7) GND")
        # switch
        c.create_rectangle(x + 300, y + 122, x + 348, y + 162, fill="#cfcfcf",
                           outline="#888")
        on = sg.spk_on
        c.create_rectangle(x + 306, y + 128 if on else y + 144, x + 342,
                           y + 144 if on else y + 156, fill="#c33" if on else "#666",
                           outline="")
        c.create_text(x + 324, y + 172, text=T("(8) 스위치", "(8) switch"),
                      fill="#4a5a40", font=("TkDefaultFont", 8))
        c.create_text(x + 10, y + 200, anchor="w",
                      text=T("배터리 팩 연결됨" if sg.powered else "전원 없음",
                             "battery pack connected" if sg.powered else "no power"),
                      fill="#3d5230" if sg.powered else "#a33",
                      font=("TkDefaultFont", 8))
        c.create_text(x + 10, y + 220, anchor="w",
                      text=T("가변저항은 스토퍼가 없다 (여러 바퀴).",
                             "The pots are multi-turn and have no end stop."),
                      fill="#6f7d63", font=("TkDefaultFont", 8))

    def socket(self, x, y, name, col, lab):
        c = self.cv
        c.create_oval(x - 13, y - 13, x + 13, y + 13, fill="#b9b9b9", outline="#777")
        self.term_dot(x, y, name, col)
        c.create_text(x, y + 24, text=lab, fill="#4a5a40", font=("TkDefaultFont", 7))

    def term_dot(self, x, y, name, col):
        c = self.cv
        sel = (self.sel_term == name)
        c.create_oval(x - 8, y - 8, x + 8, y + 8, fill=col,
                      outline=ACC if sel else "#555", width=3 if sel else 1,
                      tags=("term:" + name,))
        self.term[name] = (x, y)

    # ------------------------------------------------------------- meters --
    def draw_dmm(self, m, x, y, title):
        c = self.cv
        c.create_rectangle(x, y, x + 160, y + 250, fill="#2f62a8", outline="#1d3f6e",
                           width=2)
        c.create_text(x + 80, y + 14, text=title, fill="#dfe9f5",
                      font=("TkDefaultFont", 9, "bold"))
        c.create_rectangle(x + 12, y + 26, x + 148, y + 74, fill="#cfe6c8",
                           outline="#4d6a45", width=2)
        c.create_text(x + 140, y + 50, anchor="e", text=m.display(self.b.rng),
                      fill="#12240e", font=("TkFixedFont", 17, "bold"))
        c.create_text(x + 80, y + 88, text="%s   %s" % (m.mode, m.range_label()),
                      fill="#dfe9f5", font=("TkDefaultFont", 8))
        c.create_oval(x + 44, y + 100, x + 116, y + 172, fill="#e8e8e8", outline="#999",
                      width=2)
        a = {"OFF": -90, "V": 200, "A": 340}[m.mode]
        ar = math.radians(a)
        c.create_line(x + 80, y + 136, x + 80 + 28 * math.cos(ar),
                      y + 136 + 28 * math.sin(ar), fill="#222", width=4)
        c.create_text(x + 80, y + 186, text="OFF   V   A", fill="#dfe9f5",
                      font=("TkDefaultFont", 8))
        self.term_dot(x + 46, y + 216, m.name + ".IN", "#d8b800")
        c.create_text(x + 46, y + 232, text="V mA Ω", fill="#dfe9f5",
                      font=("TkDefaultFont", 7))
        self.term_dot(x + 114, y + 216, m.name + ".COM", "#111111")
        c.create_text(x + 114, y + 232, text="GND", fill="#dfe9f5",
                      font=("TkDefaultFont", 7))

    def draw_resistor(self, x, y):
        c = self.cv
        c.create_rectangle(x, y, x + 232, y + 62, fill="#efece2", outline="#c1baa6")
        c.create_text(x + 8, y + 12, anchor="w", text=T("옴 저항기", "ohmic resistor"),
                      fill="#6b6553", font=("TkDefaultFont", 8, "bold"))
        c.create_line(x + 40, y + 38, x + 84, y + 38, fill="#666", width=3)
        c.create_rectangle(x + 84, y + 28, x + 148, y + 48, fill="#d8c9a0",
                           outline="#8a7c55")
        for i, col in enumerate(("#8a5a2b", "#111", "#c00", "#c9a227")):
            c.create_rectangle(x + 92 + i * 13, y + 28, x + 97 + i * 13, y + 48,
                               fill=col, outline="")
        c.create_line(x + 148, y + 38, x + 192, y + 38, fill="#666", width=3)
        self.term_dot(x + 34, y + 38, "R.a", "#999999")
        self.term_dot(x + 198, y + 38, "R.b", "#999999")

    def draw_pinstrip(self, x, y):
        c = self.cv
        c.create_rectangle(x, y, x + 380, y + 96, fill="#efece2", outline="#c1baa6")
        c.create_text(x + 8, y + 14, anchor="w",
                      text=T("탐침판 단자 (스프링 핀 1–8)", "probe plate terminals (pins 1-8)"),
                      fill="#6b6553", font=("TkDefaultFont", 8, "bold"))
        for i in range(8):
            px = x + 30 + (i % 4) * 92
            py = y + 44 + (i // 4) * 36
            self.term_dot(px, py, PIN_NAME[i], "#c9a227")
            c.create_text(px + 16, py, anchor="w", text=PIN_NAME[i], fill="#4a4536",
                          font=("TkDefaultFont", 8))

    def draw_legend(self, x, y):
        c = self.cv
        c.create_rectangle(x, y, x + 520, y + 62, fill="#efece2", outline="#c1baa6")
        pins = self.b.contacting_pins()
        c.create_text(x + 10, y + 16, anchor="w",
                      text=T("시료에 닿아 있는 핀: ", "pins in contact: ") +
                           (", ".join(PIN_NAME[i] for i in pins) if pins else "-"),
                      fill="#4a4536", font=("TkDefaultFont", 9))
        c.create_text(x + 10, y + 40, anchor="w",
                      text=T("핀을 눌러 내리거나 올린다.  판은 끌어서 옮긴다.",
                             "Click a pin to lower/raise it.  Drag the plate to move it."),
                      fill="#8a8371", font=("TkDefaultFont", 8))

    def draw_wires(self):
        c = self.cv
        for i, (a, b) in enumerate(self.b.wires):
            if a not in self.term or b not in self.term:
                continue
            x0, y0 = self.term[a]
            x1, y1 = self.term[b]
            mx = (x0 + x1) / 2
            my = max(y0, y1) + 26
            c.create_line(x0, y0, mx, my, x1, y1, smooth=True, width=3,
                          fill=WIRE_COLORS[i % len(WIRE_COLORS)],
                          capstyle="round", tags=("wire%d" % i,))

    # ================================================================ events
    def on_click(self, ev):
        it = self.cv.find_withtag("current")
        if it:
            for tg in self.cv.gettags(it[0]):
                if tg.startswith("term:"):
                    self.click_term(tg[5:])
                    return
                if tg.startswith("pin"):
                    i = int(tg[3:])
                    self.b.plate.down[i] = not self.b.plate.down[i]
                    self.redraw()
                    return
                if tg.startswith("wire"):
                    self.b.del_wire(int(tg[4:]))
                    self.refresh_wirelist()
                    self.redraw()
                    return
        if not (self.SX <= ev.x <= self.SX + self.SW and
                self.SY <= ev.y <= self.SY + self.SH):
            return
        if self.mode == "cut":
            self.do_cut(ev.y)
            return
        if self.b.plate.placed_on == self.b.active:
            wx, wy = self.s2w(ev.x, ev.y)
            d = math.hypot(wx - self.b.plate.cx, wy - self.b.plate.cy)
            if d < PLATE_R:
                self.drag_plate = (wx - self.b.plate.cx, wy - self.b.plate.cy)

    def on_drag(self, ev):
        if self.drag_plate:
            wx, wy = self.s2w(ev.x, ev.y)
            self.b.plate.cx = wx - self.drag_plate[0]
            self.b.plate.cy = wy - self.drag_plate[1]
            self.redraw()

    def on_up(self, ev):
        self.drag_plate = None

    def on_hover(self, ev):
        if self.mode == "cut" and self.b.active == "paper":
            if self.SY <= ev.y <= self.SY + self.SH:
                self.cut_y = ev.y
                self.redraw()

    def click_term(self, name):
        if self.sel_term is None:
            self.sel_term = name
            self.note(T("%s 선택됨 — 연결할 다른 단자를 눌러라." % name,
                        "%s selected - click the other terminal." % name))
        elif self.sel_term == name:
            self.sel_term = None
            self.note("")
        else:
            if self.b.add_wire(self.sel_term, name):
                self.note(T("연결: %s — %s" % (self.sel_term, name),
                            "connected: %s - %s" % (self.sel_term, name)))
            else:
                self.note(T("이미 연결되어 있다.", "already connected."))
            self.sel_term = None
            self.refresh_wirelist()
        self.redraw()

    def do_cut(self, sy):
        p = self.b.paper
        ybot = self.w2s(0, -p.W / 2)[1]
        neww = (ybot - sy) / self.scale()
        neww = round(neww)
        if neww < 4 or neww > p.W - 1:
            self.note(T("자를 수 없는 위치이다.", "the paper cannot be cut here."))
            return
        if not messagebox.askyesno(T("가위", "Scissors"),
                                   T("종이를 자른다. 되돌릴 수 없다. 계속하겠는가?",
                                     "Cutting the paper is irreversible. Continue?")):
            return
        p.cut(neww + self.b.rng.gauss(0.0, 0.4))
        self.v_mode.set("probe")
        self.mode = "probe"
        self.note(T("종이를 잘랐다. 남은 조각의 너비를 자로 측정하라.",
                    "Paper cut. Measure the width of the remaining strip with the ruler."))
        self.redraw()

    # ================================================================= timer
    def tick(self):
        try:
            self.b.evaluate()
        except Exception:
            pass
        c = self.cv
        for m, x in ((self.b.m1, 1088), (self.b.m2, 1258)):
            c.delete("disp" + m.name)
            c.create_rectangle(x + 12, 60, x + 148, 108, fill="#cfe6c8",
                               outline="#4d6a45", width=2, tags="disp" + m.name)
            c.create_text(x + 140, 84, anchor="e", text=m.display(self.b.rng),
                          fill="#12240e", font=("TkFixedFont", 17, "bold"),
                          tags="disp" + m.name)
        self.after(420, self.tick)


# ===========================================================================
class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.title(T("IPhO 2016 실험 E-I — 2차원에서의 전기 전도  |  HaslaLab",
                     "IPhO 2016 Experiment E-I - Electrical conductivity in 2D  |  HaslaLab"))
        self.configure(bg=BG)
        self.geometry("1490x900")
        self.session = Session(seed)
        self.bench = Bench(self.session)
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.asm = AssemblyTab(self.nb, self)
        self.nb.add(self.asm, text=T("  조립  ", "  Assembly  "))
        self.bt = BenchTab(self.nb, self)
        self.nb.add(self.bt, text=T("  실험대  ", "  Bench  "))
        self.nb.tab(1, state="disabled")

    def enable_bench(self):
        try:
            self.nb.tab(1, state="normal")
            self.bt.redraw()
        except Exception:
            pass


def main():
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
    App(seed).mainloop()


if __name__ == "__main__":
    main()
