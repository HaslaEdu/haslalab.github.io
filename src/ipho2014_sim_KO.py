#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  45th International Physics Olympiad  (IPhO 2014, Astana, Kazakhstan)
  Experimental Problem :  TO SEE INVISIBLE!
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The simulator shows ONLY what the real instruments show -- the colours
    seen through the analyser, the screen scale, the multimeter display and
    the knobs.  Phase differences, filter transmittance, threshold voltages
    and the strip curvature are NEVER computed or displayed.
    All hidden true parameters are randomised for every session.
    
    Run:   python3 ipho2014_sim_KO.py
"""

import math
import random
import sys
import tkinter as tk
from tkinter import ttk

# --------------------------------------------------------------------------
#  language
# --------------------------------------------------------------------------
LANG = "ko"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


APP_TITLE = T("IPhO 2014 실험 - 보이지 않는 것을 보라!",
              "IPhO 2014 Experiment - To see invisible!")

# --------------------------------------------------------------------------
#  colours of the interface
# --------------------------------------------------------------------------
C_BG = "#1b1d21"
C_PANEL = "#25282e"
C_PANEL2 = "#2e323a"
C_TEXT = "#e6e8ea"
C_DIM = "#9aa0a8"
C_ACCENT = "#4da3ff"
C_OK = "#57c98a"
C_WARN = "#e2b33c"
C_TABLE = "#5a3b23"
C_BENCH = "#d8d5cc"
C_METAL = "#b9bcc2"

# ==========================================================================
#  1.  SPECTRAL COLOUR ENGINE
# ==========================================================================
# CIE 1931 2-degree colour matching functions, 400..700 nm / 10 nm
_CIE = [
    (400, 0.0143, 0.0004, 0.0679), (410, 0.0435, 0.0012, 0.2074),
    (420, 0.1344, 0.0040, 0.6456), (430, 0.2839, 0.0116, 1.3856),
    (440, 0.3483, 0.0230, 1.7471), (450, 0.3362, 0.0380, 1.7721),
    (460, 0.2908, 0.0600, 1.6692), (470, 0.1954, 0.0910, 1.2876),
    (480, 0.0956, 0.1390, 0.8130), (490, 0.0320, 0.2080, 0.4652),
    (500, 0.0049, 0.3230, 0.2720), (510, 0.0093, 0.5030, 0.1582),
    (520, 0.0633, 0.7100, 0.0782), (530, 0.1655, 0.8620, 0.0422),
    (540, 0.2904, 0.9540, 0.0203), (550, 0.4334, 0.9950, 0.0087),
    (560, 0.5945, 0.9950, 0.0039), (570, 0.7621, 0.9520, 0.0021),
    (580, 0.9163, 0.8700, 0.0017), (590, 1.0263, 0.7570, 0.0011),
    (600, 1.0622, 0.6310, 0.0008), (610, 1.0026, 0.5030, 0.0003),
    (620, 0.8544, 0.3810, 0.0002), (630, 0.6424, 0.2650, 0.0000),
    (640, 0.4479, 0.1750, 0.0000), (650, 0.2835, 0.1070, 0.0000),
    (660, 0.1649, 0.0610, 0.0000), (670, 0.0874, 0.0320, 0.0000),
    (680, 0.0468, 0.0170, 0.0000), (690, 0.0227, 0.0082, 0.0000),
    (700, 0.0114, 0.0041, 0.0000),
]


def _led_spectrum(lam):
    """phosphor converted white LED : InGaN blue peak + broad phosphor band"""
    b = math.exp(-0.5 * ((lam - 455.0) / 11.0) ** 2)
    y = math.exp(-0.5 * ((lam - 562.0) / 50.0) ** 2)
    return 1.30 * b + 1.00 * y


class Colour:
    """retardance (nm) -> sRGB between crossed / parallel polarisers"""

    def __init__(self):
        self.ws = [(w, _led_spectrum(w), x, y, z) for (w, x, y, z) in _CIE]
        self.norm = sum(s * y for (w, s, x, y, z) in self.ws)
        self._cache = {}

    def rgb(self, R_nm, gain=1.0, crossed=True):
        key = (int(R_nm * 0.5), int(gain * 60), crossed)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        X = Y = Z = 0.0
        for (w, s, xb, yb, zb) in self.ws:
            t = math.sin(math.pi * R_nm / w) ** 2
            if not crossed:
                t = 1.0 - t
            p = s * t
            X += p * xb
            Y += p * yb
            Z += p * zb
        k = gain / self.norm
        X *= k
        Y *= k
        Z *= k
        r = 3.2406 * X - 1.5372 * Y - 0.4986 * Z
        g = -0.9689 * X + 1.8758 * Y + 0.0415 * Z
        b = 0.0557 * X - 0.2040 * Y + 1.0570 * Z
        out = []
        for c in (r, g, b):
            c = 0.0 if c < 0.0 else (1.0 if c > 1.0 else c)
            c = 1.055 * c ** (1 / 2.4) - 0.055 if c > 0.0031308 else 12.92 * c
            c = 0.0 if c < 0.0 else (1.0 if c > 1.0 else c)
            out.append(int(round(c * 255)))
        res = "#%02x%02x%02x" % tuple(out)
        self._cache[key] = res
        return res


COLOUR = Colour()

# ==========================================================================
#  2.  NUMERICS
# ==========================================================================


def _tanh_sinh(f, a, b, n=64, h=0.085):
    c = 0.5 * (b + a)
    d = 0.5 * (b - a)
    s = 0.0
    for k in range(-n, n + 1):
        t = k * h
        sh = math.sinh(t)
        u = 0.5 * math.pi * sh
        if abs(u) > 300.0:
            continue
        x = math.tanh(u)
        w = (0.5 * math.pi * math.cosh(t)) / (math.cosh(u) ** 2)
        xx = c + d * x
        if xx <= a or xx >= b:
            continue
        s += w * f(xx)
    return s * d * h


def lsq(xs, ys):
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    a = sxy / sxx if sxx else 0.0
    return a, my - a * mx


# ==========================================================================
#  3.  LIQUID CRYSTAL CELL  -  Frederiks transition (Deuling 1972)
# ==========================================================================
class LiquidCrystal:
    """Planar (ECB) nematic cell.  Solves the exact one-dimensional
    director profile and returns the optical retardation versus voltage."""

    def __init__(self, kappa=1.0, gam=25.0, no=1.500, ne=1.6097):
        self.kappa = kappa      # (K33-K11)/K11
        self.gam = gam          # (eps_par-eps_perp)/eps_perp
        self.no = no
        self.ne = ne
        self.table = self._build()

    def _pair(self, m):
        kap, gam, no, ne = self.kappa, self.gam, self.no, self.ne

        def f2(psi):
            s2 = math.sin(psi) ** 2
            return math.sqrt((1.0 + kap * m * s2) /
                             ((1.0 + gam * m * s2) * (1.0 - m * s2)))

        def f1(psi):
            s2 = math.sin(psi) ** 2
            return math.sqrt((1.0 + kap * m * s2) * (1.0 + gam * m * s2) /
                             (1.0 - m * s2))

        def fn(psi):
            s2 = math.sin(psi) ** 2
            sth2 = m * s2
            cth2 = 1.0 - sth2
            neff = no * ne / math.sqrt(no * no * cth2 + ne * ne * sth2)
            return (neff - no) * math.sqrt((1.0 + kap * m * s2) *
                                           (1.0 + gam * m * s2) / (1.0 - m * s2))

        half = math.pi / 2
        I2 = _tanh_sinh(f2, 0.0, half)
        I1 = _tanh_sinh(f1, 0.0, half)
        In = _tanh_sinh(fn, 0.0, half)
        u = (2.0 / math.pi) * math.sqrt(1.0 + gam * m) * I2
        r = (In / I1) / (self.ne - self.no)
        return u, r

    def _build(self, n=180):
        pts = [(1.0, 1.0)]
        for i in range(n):
            m = 1.0 - 10.0 ** (-(0.004 + 7.0 * (i / (n - 1.0)) ** 1.6))
            u, r = self._pair(m)
            pts.append((u, r))
        pts.sort()
        # strictly increasing in u
        out = [pts[0]]
        for p in pts[1:]:
            if p[0] > out[-1][0] + 1e-9:
                out.append(p)
        return out

    def ratio(self, u_over_uth):
        t = self.table
        u = u_over_uth
        if u <= t[0][0]:
            return 1.0
        if u >= t[-1][0]:
            return t[-1][1] * t[-1][0] / u          # asymptotic 1/U tail
        lo, hi = 0, len(t) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if t[mid][0] <= u:
                lo = mid
            else:
                hi = mid
        (u0, r0), (u1, r1) = t[lo], t[hi]
        f = (u - u0) / (u1 - u0)
        return r0 + f * (r1 - r0)


LC_MODEL = None       # built lazily (about 0.4 s)


def lc_model():
    global LC_MODEL
    if LC_MODEL is None:
        LC_MODEL = LiquidCrystal()
    return LC_MODEL


# ==========================================================================
#  4.  PHOTODIODE  (photovoltaic mode, loaded by R)
# ==========================================================================
class PhotoDiode:
    def __init__(self, I_L0, V_oc0, nth, R_sh=4.0e6):
        self.I_L0 = I_L0        # short circuit photocurrent, full beam  [A]
        self.V_oc0 = V_oc0      # open circuit voltage at I_L0           [V]
        self.nth = nth          # m*kT/q                                 [V]
        self.R_sh = R_sh
        self.Is = I_L0 * math.exp(-V_oc0 / nth)

    def current(self, V, I_L):
        """net current delivered to the external circuit at terminal voltage V"""
        e = V / self.nth
        e = 60.0 if e > 60.0 else e
        return I_L - self.Is * (math.exp(e) - 1.0) - V / self.R_sh

    def dIdV(self, V):
        e = V / self.nth
        e = 60.0 if e > 60.0 else e
        return -self.Is * math.exp(e) / self.nth - 1.0 / self.R_sh

    def load_voltage(self, I_L, R):
        """voltage across a pure resistive load R (used for quick checks)"""
        if R <= 0.0 or I_L <= 0.0:
            return 0.0
        lo, hi = 0.0, self.V_oc0 * 1.5
        for _ in range(90):
            V = 0.5 * (lo + hi)
            if V / R - self.current(V, I_L) > 0.0:
                hi = V
            else:
                lo = V
        return 0.5 * (lo + hi)


# ==========================================================================
#  5.  SESSION  -  hidden, per-session randomised truth
# ==========================================================================
LAM_REF = 650.0            # nm, red laser diode


class Session:
    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1, 10 ** 9)
        self.seed = seed
        rnd = random.Random(seed)
        self.rnd = rnd

        # ---- light sources -------------------------------------------
        self.lam = 645.0 + 10.0 * rnd.random()                    # nm

        # ---- polarisers ----------------------------------------------
        # transmission plane of polariser 1: +45 deg or -45 deg from horizontal
        self.pol1_deg = rnd.choice([45.0, -45.0])
        self.pol2_deg = self.pol1_deg + 90.0
        # polarisation plane of the laser when the ring 5a reads zero
        self.laser_pol0 = rnd.uniform(-30.0, 30.0)

        # ---- photodiode + electronics --------------------------------
        self.pd = PhotoDiode(I_L0=(35.0 + 6.0 * rnd.random()) * 1e-6,
                             V_oc0=0.470 + 0.025 * rnd.random(),
                             nth=0.049 + 0.004 * rnd.random())
        self.gamma = 0.572 + 0.022 * rnd.random()                 # filter transmittance
        self.R_max = 100e3 + 12e3 * rnd.random()                  # variable resistor
        self.R_min = 120.0 + 80.0 * rnd.random()

        # ---- rulers ---------------------------------------------------
        # retardance gradients, nm per mm  (Dphi = 2 pi R / lambda)
        self.g1 = (0.0565 + 0.0055 * rnd.random()) * LAM_REF / (2 * math.pi)
        self.c1 = -(0.85 + 0.20 * rnd.random()) * LAM_REF / (2 * math.pi)
        self.g2 = (0.0262 + 0.0042 * rnd.random()) * LAM_REF / (2 * math.pi)
        self.c2 = (0.43 + 0.18 * rnd.random()) * LAM_REF / (2 * math.pi)
        self.ruler1_axis = rnd.choice([0.0, 90.0])   # deg from the long edge of the ruler
        self.ruler2_axis = self.ruler1_axis

        # ---- flexible strip -------------------------------------------
        # 10 pi + a fold of about 2.2 - 2.9 rad, exactly as in the official
        # solution (Dphi_0 = 10 pi + 2 arcsin sqrt(U0/Umax) ~ 33.9 rad)
        self.strip_dphi0 = 10.0 * math.pi + 2.15 + 0.55 * rnd.random()
        self.strip_Rc = 24.0 + 10.0 * rnd.random()                # mm, curvature
        self.strip_n = 1.4
        self.strip_axis = rnd.choice([1.0, -1.0]) * (7.0 + 6.0 * rnd.random())
        self.strip_xc = 54.0 + 14.0 * rnd.random()                # mm on screen scale

        # ---- liquid crystal cell ---------------------------------------
        self.lcc_dphi0 = 10.20 + 0.80 * rnd.random()              # rad @ LAM_REF
        self.lcc_Uth = 0.615 + 0.055 * rnd.random()               # V (rms)
        self.lcc_axis = rnd.choice([0.0, 90.0])                   # horizontal / vertical

        # ---- transmittances (calibrated so that the measured maxima are
        #      close to the values quoted in the official solution) -------
        self.k_pol2 = 0.86 + 0.05 * rnd.random()
        self.k_slit = 0.49 + 0.05 * rnd.random()
        self.k_ruler = 0.86 + 0.06 * rnd.random()
        self.k_stack = 0.27 + 0.05 * rnd.random()   # extra loss, two rulers stacked
        self.k_strip = 0.64 + 0.07 * rnd.random()
        self.k_lcc = 0.85 + 0.07 * rnd.random()

        # ---- instrument noise ------------------------------------------
        self.drift = 0.004 + 0.004 * rnd.random()
        self.noise_seed = rnd.randrange(1 << 30)

    # ------------------------------------------------------------------
    #  retardance of each optical element, in nm
    # ------------------------------------------------------------------
    def ruler_R(self, which, x_mm):
        if which == 1:
            return self.g1 * x_mm + self.c1
        return self.g2 * x_mm + self.c2

    def strip_R(self, x_mm):
        z = x_mm - self.strip_xc
        R0 = self.strip_dphi0 * LAM_REF / (2 * math.pi)
        return R0 * (1.0 + z * z / (2.0 * self.strip_n ** 2 * self.strip_Rc ** 2))

    def lcc_R(self, U_rms):
        R0 = self.lcc_dphi0 * LAM_REF / (2 * math.pi)
        if U_rms <= self.lcc_Uth:
            return R0
        return R0 * lc_model().ratio(U_rms / self.lcc_Uth)

    # ------------------------------------------------------------------
    def sample_axis_deg(self, sample):
        """orientation of the optic axis, degrees from horizontal"""
        if sample in ("ruler1", "ruler2", "both"):
            return self.ruler1_axis
        if sample == "strip":
            return self.strip_axis
        if sample == "lcc":
            return self.lcc_axis
        return 0.0


# ==========================================================================
#  6.  CIRCUIT  -  small nodal solver with a non-linear photodiode
# ==========================================================================
TERMINALS = [
    ("PD1", T("광검출기 15b (+)", "photodetector 15b (+)")),
    ("PD2", T("광검출기 15b (-)", "photodetector 15b (-)")),
    ("RA", T("가변저항 7a", "variable resistor 7a")),
    ("RB", T("가변저항 7b", "variable resistor 7b")),
    ("RW", T("가변저항 7c (와이퍼)", "variable resistor 7c (wiper)")),
    ("S1", T("스위치 8a", "switch 8a")),
    ("S2", T("스위치 8b", "switch 8b")),
    ("MC", T("멀티미터 11d (COM)", "multimeter 11d (COM)")),
    ("MV", T("멀티미터 11e (V/Ω)", "multimeter 11e (V/Ohm)")),
    ("L1", T("LCC 전원 10b (1)", "LCC supply 10b (1)")),
    ("L2", T("LCC 전원 10b (2)", "LCC supply 10b (2)")),
]
TERM_IDS = [t[0] for t in TERMINALS]

R_WIRE = 1.0e-3
R_OPEN = 1.0e12
R_MM_V = 1.0e7
I_OHM_TEST = 1.0e-6          # 200 kOhm range test current


class Circuit:
    """Newton solver.  Elements:
         ('R', a, b, value)
         ('I', a, b, amps)          current forced from a to b through source
         ('PD', a, b, diode, I_L)
    """

    def __init__(self):
        self.elems = []
        self.nodes = set()

    def add_R(self, a, b, v):
        self.elems.append(("R", a, b, max(v, 1e-9)))
        self.nodes.update((a, b))

    def add_I(self, a, b, amps):
        self.elems.append(("I", a, b, amps))
        self.nodes.update((a, b))

    def add_PD(self, a, b, diode, I_L):
        self.elems.append(("PD", a, b, diode, I_L))
        self.nodes.update((a, b))

    def solve(self):
        nodes = sorted(self.nodes)
        idx = {n: i for i, n in enumerate(nodes)}
        n = len(nodes)
        if n == 0:
            return {}
        V = [0.0] * n
        for _ in range(80):
            G = [[0.0] * n for _ in range(n)]
            I = [0.0] * n
            for i in range(n):
                G[i][i] += 1.0 / R_OPEN            # keep the matrix regular
            for e in self.elems:
                if e[0] == "R":
                    a, b, v = idx[e[1]], idx[e[2]], e[3]
                    g = 1.0 / v
                    G[a][a] += g
                    G[b][b] += g
                    G[a][b] -= g
                    G[b][a] -= g
                elif e[0] == "I":
                    a, b, amps = idx[e[1]], idx[e[2]], e[3]
                    I[a] -= amps
                    I[b] += amps
                else:
                    a, b, d, I_L = idx[e[1]], idx[e[2]], e[3], e[4]
                    v = V[a] - V[b]
                    f = d.current(v, I_L)
                    fp = d.dIdV(v)
                    g = -fp
                    ieq = f - fp * v
                    G[a][a] += g
                    G[b][b] += g
                    G[a][b] -= g
                    G[b][a] -= g
                    I[a] += ieq
                    I[b] -= ieq
            # ground node 0
            for j in range(n):
                G[0][j] = 1.0 if j == 0 else 0.0
            I[0] = 0.0
            newV = _gauss(G, I)
            if newV is None:
                return {nm: 0.0 for nm in nodes}
            step = max(abs(newV[i] - V[i]) for i in range(n))
            if step > 0.15:                        # damping
                lam = 0.15 / step
                newV = [V[i] + lam * (newV[i] - V[i]) for i in range(n)]
            done = max(abs(newV[i] - V[i]) for i in range(n)) < 1e-10
            V = newV
            if done:
                break
        return {nm: V[idx[nm]] for nm in nodes}


def _gauss(A, b):
    n = len(b)
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


# ==========================================================================
#  7.  BENCH  -  everything the student has physically set up
# ==========================================================================
SLOTS = ["1a", "1c", "1e", "1d", "1b"]
SLOT_LABEL = {
    "1a": T("1a 광원 지지대", "1a light source support"),
    "1c": T("1c 편광판 스탠드", "1c polariser stand"),
    "1e": T("1e 스크린 / LCC 스탠드", "1e screen / LCC stand"),
    "1d": T("1d 편광판 스탠드", "1d polariser stand"),
    "1b": T("1b 광검출기 지지대", "1b photodetector support"),
}
SLOT_ACCEPT = {
    "1a": ("led", "laser"),
    "1c": ("pol1", "pol2"),
    "1e": ("screen", "lcc"),
    "1d": ("pol1", "pol2"),
    "1b": ("pd",),
}

PART_NAME = {
    "led": T("4 발광 다이오드 (LED)", "4 light emitting diode (LED)"),
    "laser": T("5 레이저", "5 laser"),
    "pol1": T("2a 편광판 1", "2a polariser 1"),
    "pol2": T("2b 편광판 2", "2b polariser 2"),
    "screen": T("3 슬릿·눈금 스크린", "3 screen with slit and scale"),
    "lcc": T("9a 액정 셀 (LCC)", "9a liquid crystal cell (LCC)"),
    "pd": T("15 광검출기 (포토다이오드)", "15 photodetector (photodiode)"),
    "supply": T("6 광원 전원", "6 light source power supply"),
    "lccsupply": T("10 LCC 전원", "10 LCC power supply"),
    "res": T("7 가변저항", "7 variable resistor"),
    "switch": T("8 스위치", "8 switch"),
    "mm": T("11 멀티미터", "11 multimeter"),
    "ruler1": T("12a 플라스틱 자 №1", "12a plastic ruler No.1"),
    "ruler2": T("12b 플라스틱 자 №2", "12b plastic ruler No.2"),
    "strip": T("13 유연한 스트립", "13 flexible strip"),
    "filters": T("14 광학 필터 세트", "14 set of filters"),
    "paper": T("흰 종이", "sheet of white paper"),
}


class Bench:
    def __init__(self, session):
        self.s = session
        self.slot = {k: None for k in SLOTS}
        self.on_table = set()             # 'supply','lccsupply','res','switch','mm'
        self.screen_sample = None         # None/'ruler1'/'ruler2'/'both'/'strip'
        self.filters_mounted = False
        self.filters_n = 0
        self.paper_on_pol1 = False
        self.wires = []                   # list of (a,b)

        self.src_on = False
        self.src_connected = False
        self.laser_width = 5.5            # mm spot
        self.laser_ring = 0.0             # deg, ring 5a
        self.beam_ok = True

        self.lcc_connected = False
        self.lcc_on = False
        self.lcc_knob = 0.0               # 0..1  -> 0..7.4 V rms

        self.screen_x = 50.0              # mm read on the screen scale
        self.sample_rot = 0.0             # deg, rotation of the sample in its plane
        self.hold_by_hand = False

        self.R_knob = 0.10
        self.switch_closed = False
        self.mm_mode = "off"              # off / ohm / dc / ac

    # -------------------------------------------------- helpers
    def source(self):
        v = self.slot["1a"]
        return v if v in ("led", "laser") else None

    def pol_at(self, slot):
        return self.slot[slot] if self.slot[slot] in ("pol1", "pol2") else None

    def polarisers(self):
        """(first, second) along the beam"""
        return self.pol_at("1c"), self.pol_at("1d")

    def R_value(self):
        return self.s.R_min + self.R_knob * self.s.R_max

    def lcc_voltage(self):
        if not (self.lcc_connected and self.lcc_on):
            return 0.0
        return 7.4 * self.lcc_knob

    # -------------------------------------------------- optics
    def _beta(self):
        """angle between the optic axis of the sample and polariser 1 (deg)"""
        smp = self.active_sample()
        if smp is None:
            return None
        ax = self.s.sample_axis_deg(smp) + self.sample_rot
        return ax - self.s.pol1_deg

    def active_sample(self):
        if self.slot["1e"] == "lcc":
            return "lcc"
        if self.slot["1e"] == "screen":
            return self.screen_sample
        if self.hold_by_hand and self.screen_sample:
            return self.screen_sample
        return None

    def retardance(self, x_mm):
        """retardance in nm of the sample at the point x on the screen scale"""
        smp = self.active_sample()
        s = self.s
        lo, hi = self.sample_extent()
        if smp is not None and not (lo <= x_mm <= hi):
            return 0.0
        if smp == "ruler1":
            return s.ruler_R(1, x_mm)
        if smp == "ruler2":
            return s.ruler_R(2, x_mm)
        if smp == "both":
            return s.ruler_R(1, x_mm) + s.ruler_R(2, x_mm)
        if smp == "strip":
            return s.strip_R(x_mm)
        if smp == "lcc":
            return s.lcc_R(self.lcc_voltage())
        return 0.0

    def sample_extent(self):
        """(x_lo, x_hi) in mm on the screen scale where the sample exists"""
        smp = self.active_sample()
        if smp == "strip":
            return (self.s.strip_xc - 30.0, self.s.strip_xc + 30.0)
        if smp == "lcc":
            return (-1e9, 1e9)
        if smp:
            return (0.0, 140.0)
        return (0.0, 0.0)

    def sample_transmittance(self):
        smp = self.active_sample()
        s = self.s
        if smp == "ruler1" or smp == "ruler2":
            return s.k_ruler
        if smp == "both":
            return s.k_ruler * s.k_ruler * s.k_stack
        if smp == "strip":
            return s.k_strip
        if smp == "lcc":
            return s.k_lcc
        return 1.0

    # -------------------------------------------------- photocurrent
    def photocurrent(self):
        s = self.s
        src = self.source()
        if src is None or not (self.src_on and self.src_connected):
            return 0.0
        if self.slot["1b"] != "pd":
            return 0.0
        p1, p2 = self.polarisers()
        if p1 is None and p2 is None:
            base = s.pd.I_L0 * 1.15       # both polarisers removed
        elif p1 is None or p2 is None:
            base = s.pd.I_L0
        else:
            base = s.pd.I_L0
        if src == "laser":
            if p1 is not None:
                ang = self.laser_ring + s.laser_pol0 - s.pol1_deg
                base *= math.cos(math.radians(ang)) ** 2
            if not (4.4 <= self.laser_width <= 6.6):
                base *= 0.45               # spot larger / smaller than the window
        if src == "led":
            base *= 0.06                   # the LED is a weak, wide-angle source
        if self.paper_on_pol1:
            base *= 0.09                   # diffusing paper
        if self.filters_mounted:
            base *= s.gamma ** self.filters_n
        # slit screen
        if self.slot["1e"] == "screen":
            base *= s.k_slit
        # sample
        base *= self.sample_transmittance()
        # crossed polarisers + retarder
        if p1 is not None and p2 is not None:
            crossed = abs(((s.pol1_deg - s.pol2_deg) % 180.0) - 90.0) < 1.0
            b = self._beta()
            base *= s.k_pol2
            if b is None:
                base *= 0.0 if crossed else 1.0
            else:
                m = math.sin(math.radians(2.0 * b)) ** 2
                d = 2.0 * math.pi * self.retardance(self.screen_x) / s.lam
                t = m * math.sin(d / 2.0) ** 2
                base *= t if crossed else (1.0 - t)
        elif p2 is not None:
            base *= s.k_pol2
        if not self.beam_ok:
            base *= 0.12
        return max(base, 0.0)

    # -------------------------------------------------- multimeter
    def build_circuit(self, ohm_test=False):
        c = Circuit()
        for n in TERM_IDS:
            c.nodes.add(n)
        for a, b in self.wires:
            c.add_R(a, b, R_WIRE)
        if "res" in self.on_table:
            rt = self.s.R_max
            c.add_R("RA", "RW", self.s.R_min + self.R_knob * rt)
            c.add_R("RW", "RB", self.s.R_min + (1.0 - self.R_knob) * rt)
        if "switch" in self.on_table:
            c.add_R("S1", "S2", 2.0e-2 if self.switch_closed else R_OPEN)
        if self.slot["1b"] == "pd":
            c.add_PD("PD1", "PD2", self.s.pd, self.photocurrent())
        if "mm" in self.on_table and self.mm_mode != "off":
            if ohm_test:
                c.add_R("MC", "MV", 2.0e9)
                c.add_I("MC", "MV", I_OHM_TEST)
            else:
                c.add_R("MC", "MV", R_MM_V)
        return c

    def multimeter(self):
        """returns (text, unit_text)"""
        if "mm" not in self.on_table or self.mm_mode == "off":
            return ("", "")
        if self.mm_mode == "ac":
            v = self._ac_reading()
            if v is None:
                return ("0.00", "V~")
            if v > 19.99:
                return ("1  ", "V~")
            return ("%.2f" % v, "V~")
        if self.mm_mode == "dc":
            c = self.build_circuit()
            V = c.solve()
            v = V.get("MV", 0.0) - V.get("MC", 0.0)
            v += self._noise() * 0.0012
            if abs(v) > 1.9995:
                return ("1   ", "V")
            return ("%.3f" % v, "V")
        # resistance
        c = self.build_circuit(ohm_test=True)
        V = c.solve()
        dv = V.get("MV", 0.0) - V.get("MC", 0.0)
        r = dv / I_OHM_TEST
        if r > 199.9e3 or r < -1e3:
            return ("1    ", "kΩ")
        r = r / 1000.0 + self._noise() * 0.06
        if r < 0.0:
            r = 0.0
        return ("%.1f" % r, "kΩ")

    def _ac_reading(self):
        if not ("mm" in self.on_table):
            return None
        parent = {n: n for n in TERM_IDS}

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        for a, b in self.wires:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
        ok = ((find("MV") == find("L1") and find("MC") == find("L2")) or
              (find("MC") == find("L1") and find("MV") == find("L2")))
        if not ok:
            return 0.0
        return self.lcc_voltage() * (1.0 + 0.0008 * self._noise())

    _nz = 0

    def _noise(self):
        self._nz += 1
        r = random.Random("%d-%d" % (self.s.noise_seed, self._nz // 3))
        return r.gauss(0.0, 1.0)


# ==========================================================================
#  8.  APPARATUS DRAWING  (2-D vector art built from the problem photographs)
# ==========================================================================
def rrect(cv, x0, y0, x1, y1, r=6, **kw):
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


def draw_bench_rail(cv, x0, y0, w, h, tag):
    """optical bench 1 : moulded plastic rail with holders"""
    rrect(cv, x0, y0 + h * 0.45, x0 + w, y0 + h, r=10,
          fill="#e9e6dd", outline="#a8a498", width=2, tags=tag)
    cv.create_rectangle(x0 + 18, y0 + h * 0.52, x0 + w - 18, y0 + h * 0.66,
                        fill="#d3cfc4", outline="#b3afa4", tags=tag)
    for i in range(int(w // 12)):
        xx = x0 + 24 + i * 12
        if xx < x0 + w - 24:
            cv.create_line(xx, y0 + h * 0.53, xx, y0 + h * 0.65,
                           fill="#bdb9ae", tags=tag)


def draw_pad(cv, cx, y, tag, big=False):
    """round support pad (1a / 1b)"""
    r = 26 if big else 20
    cv.create_oval(cx - r, y - r * 0.34, cx + r, y + r * 0.34,
                   fill="#efece4", outline="#a8a498", width=2, tags=tag)
    for k in range(16):
        a = 2 * math.pi * k / 16
        cv.create_line(cx + r * math.cos(a), y + r * 0.34 * math.sin(a),
                       cx + (r - 4) * math.cos(a), y + (r - 4) * 0.34 * math.sin(a),
                       fill="#b9b5aa", tags=tag)


def draw_slot(cv, cx, y, tag):
    cv.create_rectangle(cx - 26, y - 5, cx + 26, y + 5,
                        fill="#c9c5ba", outline="#a29e93", tags=tag)


def draw_polariser(cv, cx, cy, num, tag, scale=1.0, dim=False):
    w = 62 * scale
    h = 72 * scale
    body = "#4b4f57" if dim else "#eceae3"
    rrect(cv, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, r=5,
          fill=body, outline="#9d9a90", width=2, tags=tag)
    a = 22 * scale
    cv.create_rectangle(cx - a, cy - a - 4 * scale, cx + a, cy + a - 4 * scale,
                        fill="#2b2f36", outline="#6f6c64", tags=tag)
    cv.create_text(cx, cy + h / 2 - 11 * scale, text=str(num),
                   fill="#3a3d43" if not dim else "#c9ccd2",
                   font=("Helvetica", int(10 * scale), "bold"), tags=tag)
    # stand
    cv.create_rectangle(cx - 5, cy + h / 2, cx + 5, cy + h / 2 + 16 * scale,
                        fill="#d5d2c8", outline="#a8a498", tags=tag)


def draw_screen(cv, cx, cy, tag, scale=1.0):
    w = 96 * scale
    h = 80 * scale
    rrect(cv, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, r=6,
          fill="#eeece5", outline="#9d9a90", width=2, tags=tag)
    cv.create_rectangle(cx - w / 2 + 6, cy - h / 2 + 6, cx + w / 2 - 6, cy + h / 2 - 16,
                        fill="#fbfbf8", outline="#cfccc2", tags=tag)
    cv.create_rectangle(cx - w / 2 + 10, cy - 6 * scale, cx + w / 2 - 10, cy - 1 * scale,
                        fill="#15171a", outline="", tags=tag)          # slit 3a
    # scale 3b
    y = cy + h / 2 - 11
    cv.create_line(cx - w / 2 + 8, y, cx + w / 2 - 8, y, fill="#4a4a4a", tags=tag)
    for i in range(15):
        xx = cx - w / 2 + 8 + i * (w - 16) / 14.0
        cv.create_line(xx, y, xx, y - 4, fill="#4a4a4a", tags=tag)
    cv.create_rectangle(cx - 5, cy + h / 2, cx + 5, cy + h / 2 + 16 * scale,
                        fill="#d5d2c8", outline="#a8a498", tags=tag)


def draw_lcc(cv, cx, cy, tag, scale=1.0):
    w = 84 * scale
    h = 84 * scale
    rrect(cv, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, r=6,
          fill="#eeece5", outline="#9d9a90", width=2, tags=tag)
    cv.create_rectangle(cx - 24 * scale, cy - 24 * scale, cx + 24 * scale, cy + 20 * scale,
                        fill="#dcdad2", outline="#b6b3a9", tags=tag)
    cv.create_oval(cx - 13 * scale, cy - 15 * scale, cx + 13 * scale, cy + 11 * scale,
                   fill="#8d9199", outline="#63666c", tags=tag)
    cv.create_line(cx + w / 2 - 6, cy + h / 2 - 10, cx + w / 2 + 26, cy + h / 2 + 4,
                   fill="#e7e7e7", width=3, tags=tag)
    cv.create_rectangle(cx - 5, cy + h / 2, cx + 5, cy + h / 2 + 16 * scale,
                        fill="#d5d2c8", outline="#a8a498", tags=tag)


def draw_led(cv, cx, cy, tag, on=False, scale=1.0):
    w = 26 * scale
    h = 62 * scale
    rrect(cv, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, r=4,
          fill="#e7e4dc", outline="#a09d94", width=2, tags=tag)
    cv.create_oval(cx - 7 * scale, cy - h / 2 + 5, cx + 7 * scale, cy - h / 2 + 19,
                   fill="#ff5f4d" if on else "#7a3a34", outline="#5a2a26", tags=tag)
    cv.create_line(cx, cy + h / 2, cx + 22, cy + h / 2 + 12, fill="#c03028",
                   width=3, tags=tag)


def draw_laser(cv, cx, cy, tag, on=False, scale=1.0):
    w = 34 * scale
    h = 46 * scale
    rrect(cv, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, r=4,
          fill="#e7e4dc", outline="#a09d94", width=2, tags=tag)
    cv.create_oval(cx - 15 * scale, cy - 15 * scale, cx + 15 * scale, cy + 15 * scale,
                   fill="#cfccc2", outline="#8f8c84", width=2, tags=tag)     # ring 5a
    cv.create_oval(cx - 7 * scale, cy - 7 * scale, cx + 7 * scale, cy + 7 * scale,
                   fill="#ff3b25" if on else "#5c2a22", outline="#3a3a3a", tags=tag)
    cv.create_line(cx, cy + h / 2, cx + 20, cy + h / 2 + 12, fill="#c03028",
                   width=3, tags=tag)


def draw_photodiode(cv, cx, cy, tag, scale=1.0):
    w = 22 * scale
    h = 54 * scale
    rrect(cv, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, r=3,
          fill="#d9c9a8", outline="#a2916f", width=2, tags=tag)
    cv.create_rectangle(cx - 7 * scale, cy - 12 * scale, cx + 7 * scale, cy + 2 * scale,
                        fill="#2a2d33", outline="#6b6b6b", tags=tag)
    cv.create_line(cx, cy + h / 2, cx + 18, cy + h / 2 + 10, fill="#d02a2a",
                   width=3, tags=tag)
    cv.create_line(cx, cy + h / 2, cx + 18, cy + h / 2 + 18, fill="#d8c33a",
                   width=3, tags=tag)


def draw_black_box(cv, x0, y0, w, h, tag, label=""):
    rrect(cv, x0 + 6, y0 + 6, x0 + w + 6, y0 + h + 6, r=6, fill="#0d0e10",
          outline="", tags=tag)
    rrect(cv, x0, y0, x0 + w, y0 + h, r=6, fill="#232529", outline="#3c3f45",
          width=2, tags=tag)
    if label:
        cv.create_text(x0 + w - 8, y0 + h - 8, text=label, anchor="se",
                       fill="#8b8f96", font=("Helvetica", 8), tags=tag)


def draw_multimeter(cv, x0, y0, tag, text="", unit="", mode="off"):
    w, h = 150, 220
    rrect(cv, x0, y0, x0 + w, y0 + h, r=12, fill="#d9a327", outline="#a97c19",
          width=2, tags=tag)
    rrect(cv, x0 + 10, y0 + 10, x0 + w - 10, y0 + h - 10, r=8, fill="#3a3d42",
          outline="#26282c", width=2, tags=tag)
    rrect(cv, x0 + 20, y0 + 20, x0 + w - 20, y0 + 62, r=4, fill="#b9c9a8",
          outline="#7c8a6e", width=2, tags=tag)
    cv.create_text(x0 + w - 28, y0 + 44, text=text, anchor="e", fill="#14180f",
                   font=("Courier", 20, "bold"), tags=tag)
    cv.create_text(x0 + w - 26, y0 + 56, text=unit, anchor="e", fill="#14180f",
                   font=("Helvetica", 9, "bold"), tags=tag)
    cv.create_oval(x0 + 38, y0 + 78, x0 + w - 38, y0 + 152, fill="#2a2c30",
                   outline="#101114", width=3, tags=tag)
    ang = {"off": 90.0, "ohm": 200.0, "dc": 150.0, "ac": 20.0}.get(mode, 90.0)
    a = math.radians(ang)
    cx, cy = x0 + w / 2, y0 + 115
    cv.create_line(cx, cy, cx + 30 * math.cos(a), cy - 30 * math.sin(a),
                   fill="#e8e8e8", width=4, tags=tag)
    cv.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill="#8f9298", outline="",
                   tags=tag)
    for lbl, an in (("OFF", 90.0), ("200k", 200.0), ("2V", 150.0), ("20V~", 20.0)):
        aa = math.radians(an)
        cv.create_text(cx + 50 * math.cos(aa), cy - 44 * math.sin(aa), text=lbl,
                       fill="#cfd2d6", font=("Helvetica", 7), tags=tag)


# ==========================================================================
#  9.  ASSEMBLY TAB
# ==========================================================================
RAIL_Y = 168
SLOT_X = {"1a": 130, "1c": 330, "1e": 530, "1d": 730, "1b": 930}
COMP_Y = 112

TRAY_X = 1092
TRAY_ITEMS = ["led", "laser", "pol1", "pol2", "screen", "lcc", "pd",
              "ruler1", "ruler2", "strip", "filters", "paper",
              "res", "switch", "mm", "supply", "lccsupply"]

TERM_POS = {
    "PD1": (952, 268), "PD2": (992, 268),
    "RA": (96, 470), "RB": (96, 516), "RW": (196, 470),
    "S1": (372, 470), "S2": (452, 470),
    "MC": (620, 604), "MV": (676, 604),
    "L1": (884, 470), "L2": (944, 470),
}
TERM_COLOUR = {"PD1": "#d02a2a", "PD2": "#d8c33a", "RA": "#20222a", "RB": "#20222a",
               "RW": "#d02a2a", "S1": "#d02a2a", "S2": "#d02a2a",
               "MC": "#20222a", "MV": "#d02a2a", "L1": "#d02a2a", "L2": "#20222a"}
WIRE_COLOURS = ["#3aa0ff", "#5fd18a", "#e0a53a", "#c86ce0", "#e06a6a", "#6fd8d0"]


class AssemblyTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.b = app.bench
        self.drag = None
        self.pending_term = None

        self.cv = tk.Canvas(self, bg=C_TABLE, highlightthickness=0,
                            width=1330, height=720)
        self.cv.pack(side="left", fill="both", expand=True)

        side = tk.Frame(self, bg=C_PANEL, width=250)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)
        tk.Label(side, text=T("부품함", "parts tray"), bg=C_PANEL, fg=C_TEXT,
                 font=("Helvetica", 12, "bold")).pack(pady=(12, 2))
        tk.Label(side, text=T("부품을 끌어다 놓으세요.\n오른쪽 버튼으로 제거합니다.",
                              "Drag a part onto the setup.\nRight-click to remove."),
                 bg=C_PANEL, fg=C_DIM, font=("Helvetica", 9), justify="left").pack()

        self.btn_src = tk.Button(side, text="", width=26, command=self.toggle_src_lead)
        self.btn_src.pack(pady=(14, 4))
        self.btn_lcc = tk.Button(side, text="", width=26, command=self.toggle_lcc_lead)
        self.btn_lcc.pack(pady=4)
        tk.Button(side, text=T("모든 배선 제거", "clear all wires"), width=26,
                  command=self.clear_wires).pack(pady=4)

        self.info = tk.Label(side, text="", bg=C_PANEL, fg=C_WARN, wraplength=230,
                             justify="left", font=("Helvetica", 9))
        self.info.pack(pady=10, padx=8, fill="x")

        self.chk = tk.Label(side, text="", bg=C_PANEL, fg=C_DIM, wraplength=230,
                            justify="left", font=("Helvetica", 9))
        self.chk.pack(pady=6, padx=8, fill="x", expand=True, anchor="n")

        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_motion)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Button-3>", self.on_right)
        self.redraw()

    # ------------------------------------------------------------- helpers
    def msg(self, t):
        self.info.config(text=t)

    def toggle_src_lead(self):
        b = self.b
        if not b.source():
            return self.msg(T("먼저 1a 지지대에 광원을 놓으세요.",
                              "Put a light source on support 1a first."))
        if "supply" not in b.on_table:
            return self.msg(T("6번 전원을 탁자에 놓으세요.",
                              "Put power supply 6 on the table."))
        b.src_connected = not b.src_connected
        self.app.refresh()

    def toggle_lcc_lead(self):
        b = self.b
        if b.slot["1e"] != "lcc":
            return self.msg(T("1e 스탠드에 LCC를 놓으세요.",
                              "Put the LCC on stand 1e."))
        if "lccsupply" not in b.on_table:
            return self.msg(T("10번 LCC 전원을 탁자에 놓으세요.",
                              "Put the LCC power supply 10 on the table."))
        b.lcc_connected = not b.lcc_connected
        self.app.refresh()

    def clear_wires(self):
        self.b.wires = []
        self.app.refresh()

    # ------------------------------------------------------------- events
    def _tray_hit(self, x, y):
        for i, key in enumerate(TRAY_ITEMS):
            yy = 46 + i * 39
            if TRAY_X - 6 <= x <= TRAY_X + 218 and yy - 17 <= y <= yy + 17:
                return key
        return None

    def _term_hit(self, x, y):
        for k, (tx, ty) in TERM_POS.items():
            if (x - tx) ** 2 + (y - ty) ** 2 < 150:
                return k
        return None

    def on_press(self, ev):
        t = self._term_hit(ev.x, ev.y)
        if t is not None:
            if not self._term_available(t):
                self.msg(T("그 부품이 아직 탁자 위에 없습니다.",
                           "That component is not on the table yet."))
                return
            if self.pending_term is None:
                self.pending_term = t
            elif self.pending_term == t:
                self.pending_term = None
            else:
                pair = (self.pending_term, t)
                if pair not in self.b.wires and (t, self.pending_term) not in self.b.wires:
                    self.b.wires.append(pair)
                self.pending_term = None
            self.app.refresh()
            return
        # wire removal
        for i, (a, b) in enumerate(self.b.wires):
            ax, ay = TERM_POS[a]
            bx, by = TERM_POS[b]
            mx, my = (ax + bx) / 2.0, (ay + by) / 2.0 + 26
            if (ev.x - mx) ** 2 + (ev.y - my) ** 2 < 130:
                self.b.wires.pop(i)
                self.app.refresh()
                return
        key = self._tray_hit(ev.x, ev.y)
        if key and self._tray_enabled(key):
            self.drag = [key, ev.x, ev.y]
            self.redraw()

    def on_motion(self, ev):
        if self.drag:
            self.drag[1], self.drag[2] = ev.x, ev.y
            self.redraw()

    def on_release(self, ev):
        if not self.drag:
            return
        key = self.drag[0]
        self.drag = None
        self.place(key, ev.x, ev.y)
        self.app.refresh()

    def on_right(self, ev):
        b = self.b
        for s, cx in SLOT_X.items():
            if abs(ev.x - cx) < 55 and 40 < ev.y < RAIL_Y + 10:
                if b.slot[s]:
                    if b.slot[s] == "screen":
                        b.screen_sample = None
                    if b.slot[s] == "lcc":
                        b.lcc_connected = False
                    if b.slot[s] in ("pol1", "pol2"):
                        if not (b.pol_at("1c") or b.pol_at("1d")):
                            b.filters_mounted = False
                            b.paper_on_pol1 = False
                    if b.slot[s] in ("led", "laser"):
                        b.src_connected = False
                    b.slot[s] = None
                self.app.refresh()
                return
        for key, box in self._table_boxes().items():
            x0, y0, x1, y1 = box
            if x0 <= ev.x <= x1 and y0 <= ev.y <= y1 and key in b.on_table:
                b.on_table.discard(key)
                if key == "supply":
                    b.src_connected = False
                if key == "lccsupply":
                    b.lcc_connected = False
                b.wires = [w for w in b.wires
                           if not (self._owner(w[0]) == key or self._owner(w[1]) == key)]
                self.app.refresh()
                return
        self.app.refresh()

    # ------------------------------------------------------------- logic
    def _owner(self, term):
        return {"RA": "res", "RB": "res", "RW": "res", "S1": "switch", "S2": "switch",
                "MC": "mm", "MV": "mm", "L1": "lccsupply", "L2": "lccsupply",
                "PD1": "pd", "PD2": "pd"}[term]

    def _term_available(self, term):
        o = self._owner(term)
        if o == "pd":
            return self.b.slot["1b"] == "pd"
        return o in self.b.on_table

    def _table_boxes(self):
        return {"res": (70, 400, 300, 540), "switch": (350, 420, 500, 520),
                "mm": (590, 380, 740, 620), "lccsupply": (860, 400, 1010, 520),
                "supply": (80, 590, 240, 680)}

    def _tray_enabled(self, key):
        b = self.b
        if key in ("ruler1", "ruler2", "strip"):
            return True
        if key in ("filters", "paper"):
            return bool(b.pol_at("1c") or b.pol_at("1d"))
        return True

    def place(self, key, x, y):
        b = self.b
        # bench slots
        for s, cx in SLOT_X.items():
            if abs(x - cx) < 60 and 30 < y < RAIL_Y + 20:
                if key in SLOT_ACCEPT[s]:
                    if key in ("pol1", "pol2"):
                        for other in ("1c", "1d"):
                            if other != s and b.slot[other] == key:
                                b.slot[other] = None
                    if key in ("led", "laser"):
                        b.src_connected = False
                    if b.slot[s] == "screen" and key != "screen":
                        b.screen_sample = None
                    b.slot[s] = key
                    b.hold_by_hand = False
                    self.msg("")
                else:
                    self.msg(T("%s 에는 놓을 수 없습니다.", "%s does not accept that part.")
                             % SLOT_LABEL[s])
                return
        # on the screen  (samples)
        if key in ("ruler1", "ruler2", "strip"):
            cx = SLOT_X["1e"]
            near = abs(x - cx) < 70 and 30 < y < RAIL_Y + 20
            if near and b.slot["1e"] == "screen":
                if key == "strip":
                    b.screen_sample = "strip"
                else:
                    cur = b.screen_sample
                    if key == "ruler1":
                        b.screen_sample = "both" if cur in ("ruler2", "both") else "ruler1"
                    else:
                        b.screen_sample = "both" if cur in ("ruler1", "both") else "ruler2"
                b.hold_by_hand = False
                self.msg("")
            elif 30 < y < RAIL_Y + 20 and SLOT_X["1c"] < x < SLOT_X["1d"]:
                b.screen_sample = "strip" if key == "strip" else key
                b.hold_by_hand = True
                self.msg(T("시료를 손으로 들고 있습니다 (스크린 없음).",
                           "The sample is held by hand (no screen)."))
            else:
                self.msg(T("편광판 사이, 스크린 위에 놓으세요.",
                           "Place it between the polarisers, on the screen."))
            return
        if key in ("filters", "paper"):
            for s in ("1c", "1d"):
                if b.slot[s] == "pol1" and abs(x - SLOT_X[s]) < 70 and 30 < y < RAIL_Y + 20:
                    if key == "filters":
                        b.filters_mounted = True
                    else:
                        b.paper_on_pol1 = True
                    self.msg("")
                    return
            self.msg(T("편광판 1의 면에 부착하세요.", "Clamp it on polariser 1."))
            return
        # table components
        for k, (x0, y0, x1, y1) in self._table_boxes().items():
            if k == key and x0 - 40 <= x <= x1 + 40 and y0 - 40 <= y <= y1 + 40:
                b.on_table.add(key)
                self.msg("")
                return
        if y > 260:
            b.on_table.add(key)
            self.msg("")
            return
        self.msg(T("놓을 수 없는 위치입니다.", "Cannot place the part there."))


    # ------------------------------------------------------------- drawing
    def redraw(self):
        cv = self.cv
        b = self.b
        cv.delete("all")
        cv.create_rectangle(0, 0, 1330, 720, fill=C_TABLE, outline="")
        for i in range(0, 720, 26):
            cv.create_line(0, i, 1330, i + 8, fill="#513521", width=1)
        cv.create_rectangle(1080, 0, 1330, 720, fill="#1f2126", outline="")
        cv.create_text(1200, 22, text=T("부품함", "PARTS"), fill=C_DIM,
                       font=("Helvetica", 11, "bold"))

        # ---- optical bench --------------------------------------------
        cv.create_text(60, 44, text=T("1  광학 벤치", "1  optical bench"),
                       anchor="w", fill="#e8dfd2", font=("Helvetica", 11, "bold"))
        draw_bench_rail(cv, 60, RAIL_Y - 30, 950, 62, "bench")
        for s, cx in SLOT_X.items():
            if s in ("1a", "1b"):
                draw_pad(cv, cx, RAIL_Y + 2, "bench", big=True)
            else:
                draw_slot(cv, cx, RAIL_Y - 2, "bench")
            cv.create_text(cx, RAIL_Y + 34, text=s, fill="#d7cbba",
                           font=("Helvetica", 9, "bold"))
            if b.slot[s] is None:
                cv.create_text(cx, COMP_Y, text="", fill="#7a6350")
                cv.create_rectangle(cx - 44, COMP_Y - 46, cx + 44, COMP_Y + 46,
                                    outline="#7a6350", dash=(3, 4))
        # beam
        if b.source() and b.src_on and b.src_connected:
            col = "#ff4a35" if b.source() == "laser" else "#ffd9a0"
            x1 = SLOT_X["1b"] if b.slot["1b"] == "pd" else 1010
            cv.create_line(SLOT_X["1a"] + 16, COMP_Y, x1, COMP_Y, fill=col,
                           width=3 if b.source() == "laser" else 8,
                           stipple="" if b.source() == "laser" else "gray50")
        # installed parts
        for s, cx in SLOT_X.items():
            k = b.slot[s]
            if k == "led":
                draw_led(cv, cx, COMP_Y, "p", on=b.src_on and b.src_connected)
            elif k == "laser":
                draw_laser(cv, cx, COMP_Y, "p", on=b.src_on and b.src_connected)
            elif k in ("pol1", "pol2"):
                draw_polariser(cv, cx, COMP_Y, 1 if k == "pol1" else 2, "p")
                if k == "pol1" and b.paper_on_pol1:
                    cv.create_rectangle(cx - 34, COMP_Y - 40, cx - 20, COMP_Y + 40,
                                        fill="#fdfdfa", outline="#cfccc2")
                if k == "pol1" and b.filters_mounted:
                    for i in range(3):
                        cv.create_rectangle(cx + 20 + i * 5, COMP_Y - 26,
                                            cx + 32 + i * 5, COMP_Y + 22,
                                            fill="#cfd3d6", outline="#9aa0a6",
                                            stipple="gray50")
            elif k == "screen":
                draw_screen(cv, cx, COMP_Y, "p")
                if b.screen_sample:
                    self._draw_sample_on_screen(cx, COMP_Y, b.screen_sample)
            elif k == "lcc":
                draw_lcc(cv, cx, COMP_Y, "p")
            elif k == "pd":
                draw_photodiode(cv, cx, COMP_Y, "p")
        if b.hold_by_hand and b.screen_sample and b.slot["1e"] is None:
            self._draw_sample_on_screen(SLOT_X["1e"], COMP_Y, b.screen_sample)
            cv.create_text(SLOT_X["1e"], COMP_Y + 62, text=T("(손으로 듦)", "(held by hand)"),
                           fill="#e8dfd2", font=("Helvetica", 8))

        # ---- table components ------------------------------------------
        cv.create_text(60, 246, text=T("탁자 위 (전기 부품과 배선)",
                                       "on the table  (electrical parts and wiring)"),
                       anchor="w", fill="#e8dfd2", font=("Helvetica", 11, "bold"))
        boxes = self._table_boxes()
        for key, (x0, y0, x1, y1) in boxes.items():
            if key not in b.on_table:
                cv.create_rectangle(x0, y0, x1, y1, outline="#7a6350", dash=(3, 4))
                cv.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=PART_NAME[key],
                               fill="#8d7358", font=("Helvetica", 8), width=x1 - x0 - 10)
        if "res" in b.on_table:
            draw_black_box(cv, 70, 400, 230, 140, "t", "7")
            cv.create_oval(238, 424, 286, 466, fill="#2c56b8", outline="#16327a",
                           width=2)
            cv.create_text(262, 486, text="7d", fill="#8b8f96",
                           font=("Helvetica", 8))
        if "switch" in b.on_table:
            draw_black_box(cv, 350, 420, 150, 100, "t", "8")
            cv.create_line(412, 500, 412 + (16 if b.switch_closed else -16),
                           474, fill="#d5d7da", width=7)
            cv.create_oval(404, 494, 420, 508, fill="#8f9298", outline="")
        if "mm" in b.on_table:
            t, u = b.multimeter()
            draw_multimeter(cv, 590, 380, "t", t, u, b.mm_mode)
        if "lccsupply" in b.on_table:
            draw_black_box(cv, 860, 400, 150, 120, "t", "10")
            cv.create_oval(966, 424, 998, 452, fill="#3a3d42", outline="#1a1c20",
                           width=2)
            cv.create_text(982, 462, text="10a", fill="#8b8f96",
                           font=("Helvetica", 8))
        if "supply" in b.on_table:
            draw_black_box(cv, 80, 590, 160, 90, "t", "6")
            cv.create_rectangle(96, 606, 118, 620, fill="#8f9298", outline="")
            cv.create_text(107, 630, text="6a", fill="#8b8f96", font=("Helvetica", 8))
        if b.slot["1b"] == "pd":
            cv.create_line(SLOT_X["1b"] + 18, COMP_Y + 40, 952, 268,
                           fill="#d02a2a", width=3, smooth=True)
            cv.create_line(SLOT_X["1b"] + 18, COMP_Y + 46, 992, 268,
                           fill="#d8c33a", width=3, smooth=True)
            cv.create_text(972, 240, text=T("광검출기 리드 15b", "photodetector leads 15b"),
                           fill="#e8dfd2", font=("Helvetica", 8))
        # power leads
        if b.src_connected and b.source():
            cv.create_line(160, 590, SLOT_X["1a"] + 12, COMP_Y + 34,
                           fill="#c03028", width=3, smooth=True)
        if b.lcc_connected and b.slot["1e"] == "lcc":
            cv.create_line(966, 438, SLOT_X["1e"] + 40, COMP_Y + 42,
                           fill="#e7e7e7", width=3, smooth=True)

        # ---- terminals + wires ------------------------------------------
        for i, (a, c) in enumerate(b.wires):
            ax, ay = TERM_POS[a]
            bx, by = TERM_POS[c]
            col = WIRE_COLOURS[i % len(WIRE_COLOURS)]
            cv.create_line(ax, ay, (ax + bx) / 2, (ay + by) / 2 + 44, bx, by,
                           fill=col, width=4, smooth=True)
        for k, (tx, ty) in TERM_POS.items():
            if not self._term_available(k):
                continue
            act = (self.pending_term == k)
            cv.create_oval(tx - 8, ty - 8, tx + 8, ty + 8,
                           fill=TERM_COLOUR[k], outline="#f0f0f0" if act else "#8a8d92",
                           width=3 if act else 2)
            cv.create_text(tx, ty - 17, text=k, fill="#e8dfd2",
                           font=("Helvetica", 8, "bold"))

        # ---- tray --------------------------------------------------------
        for i, key in enumerate(TRAY_ITEMS):
            yy = 46 + i * 39
            en = self._tray_enabled(key)
            used = self._tray_used(key)
            bg = "#2a2d33" if en else "#232529"
            cv.create_rectangle(TRAY_X - 6, yy - 17, TRAY_X + 218, yy + 17,
                                fill=bg, outline="#3a3d43")
            self._tray_icon(key, TRAY_X + 16, yy)
            cv.create_text(TRAY_X + 40, yy, anchor="w", text=PART_NAME[key],
                           fill="#5b6068" if used else (C_TEXT if en else "#585c63"),
                           font=("Helvetica", 8), width=176)
        if self.drag:
            k, x, y = self.drag
            cv.create_rectangle(x - 60, y - 14, x + 60, y + 14, fill="#101216",
                                outline=C_ACCENT)
            cv.create_text(x, y, text=PART_NAME[k], fill=C_TEXT,
                           font=("Helvetica", 8), width=112)

        self.btn_src.config(text=T("6b 광원 리드 %s", "6b source lead %s")
                            % (T("해제", "disconnect") if b.src_connected
                               else T("연결", "connect")))
        self.btn_lcc.config(text=T("10a LCC 커넥터 %s", "10a LCC connector %s")
                            % (T("해제", "disconnect") if b.lcc_connected
                               else T("연결", "connect")))
        self._status()

    def _tray_used(self, key):
        b = self.b
        if key in ("led", "laser", "pol1", "pol2", "screen", "lcc", "pd"):
            return key in b.slot.values()
        if key in ("res", "switch", "mm", "supply", "lccsupply"):
            return key in b.on_table
        if key == "filters":
            return b.filters_mounted
        if key == "paper":
            return b.paper_on_pol1
        if key == "ruler1":
            return b.screen_sample in ("ruler1", "both")
        if key == "ruler2":
            return b.screen_sample in ("ruler2", "both")
        if key == "strip":
            return b.screen_sample == "strip"
        return False

    def _tray_icon(self, key, x, y):
        cv = self.cv
        if key == "led":
            draw_led(cv, x, y, "ic", scale=0.42)
        elif key == "laser":
            draw_laser(cv, x, y, "ic", scale=0.52)
        elif key in ("pol1", "pol2"):
            draw_polariser(cv, x, y, 1 if key == "pol1" else 2, "ic", scale=0.36)
        elif key == "screen":
            draw_screen(cv, x, y, "ic", scale=0.30)
        elif key == "lcc":
            draw_lcc(cv, x, y, "ic", scale=0.30)
        elif key == "pd":
            draw_photodiode(cv, x, y, "ic", scale=0.45)
        elif key in ("ruler1", "ruler2"):
            cv.create_rectangle(x - 13, y - 5, x + 13, y + 5, fill="#57c7e0",
                                outline="#2e94ad")
        elif key == "strip":
            cv.create_rectangle(x - 13, y - 4, x + 13, y + 4, fill="#e7e9ea",
                                outline="#b8bcbe")
        elif key == "filters":
            for i in range(3):
                cv.create_rectangle(x - 11 + i * 5, y - 8, x - 3 + i * 5, y + 8,
                                    fill="#cfd3d6", outline="#9aa0a6")
        elif key == "paper":
            cv.create_rectangle(x - 10, y - 9, x + 10, y + 9, fill="#fdfdfa",
                                outline="#c8c8c2")
        elif key == "res":
            cv.create_rectangle(x - 13, y - 8, x + 13, y + 8, fill="#232529",
                                outline="#4a4d53")
            cv.create_oval(x + 3, y - 5, x + 12, y + 4, fill="#2c56b8", outline="")
        elif key == "switch":
            cv.create_rectangle(x - 13, y - 8, x + 13, y + 8, fill="#232529",
                                outline="#4a4d53")
            cv.create_line(x, y + 4, x + 6, y - 5, fill="#d5d7da", width=3)
        elif key == "mm":
            cv.create_rectangle(x - 10, y - 12, x + 10, y + 12, fill="#d9a327",
                                outline="#a97c19")
            cv.create_rectangle(x - 7, y - 9, x + 7, y - 2, fill="#b9c9a8",
                                outline="")
        elif key in ("supply", "lccsupply"):
            cv.create_rectangle(x - 12, y - 8, x + 12, y + 8, fill="#232529",
                                outline="#4a4d53")

    def _draw_sample_on_screen(self, cx, cy, smp):
        cv = self.cv
        if smp == "strip":
            cv.create_rectangle(cx - 46, cy - 8, cx + 46, cy + 2, fill="#e9ebec",
                                outline="#b8bcbe")
            return
        n = 2 if smp == "both" else 1
        for i in range(n):
            cv.create_rectangle(cx - 46, cy - 10 + i * 4, cx + 46, cy + 2 + i * 4,
                                fill="#57c7e0", outline="#2e94ad", stipple="gray75")

    def _status(self):
        b = self.b
        ok = []
        need = []
        (need, ok)[bool(b.source())].append(T("광원", "light source"))
        (need, ok)[bool(b.pol_at("1c"))].append(T("편광판(1c)", "polariser (1c)"))
        (need, ok)[bool(b.pol_at("1d"))].append(T("편광판(1d)", "polariser (1d)"))
        (need, ok)[b.slot["1b"] == "pd"].append(T("광검출기", "photodetector"))
        (need, ok)[bool(b.slot["1e"])].append(T("스크린/LCC", "screen / LCC"))
        (need, ok)["mm" in b.on_table].append(T("멀티미터", "multimeter"))
        (need, ok)["res" in b.on_table].append(T("가변저항", "variable resistor"))
        (need, ok)["switch" in b.on_table].append(T("스위치", "switch"))
        txt = T("설치됨: ", "installed: ") + (", ".join(ok) if ok else "-")
        txt += "\n\n" + T("미설치: ", "not installed: ") + (", ".join(need) if need else "-")
        txt += "\n\n" + T("배선 %d개", "%d wires") % len(b.wires)
        self.chk.config(text=txt)


# ==========================================================================
#  10.  BENCH TAB
# ==========================================================================
VIEW_W, VIEW_H = 720, 150
PTR_X = 360
PX_PER_MM = 4.6


class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.b = app.bench
        self._img = None

        left = tk.Frame(self, bg=C_BG)
        left.pack(side="left", fill="both", expand=True)
        right = tk.Frame(self, bg=C_PANEL, width=430)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        self.cv = tk.Canvas(left, bg=C_BG, highlightthickness=0, width=780, height=740)
        self.cv.pack(fill="both", expand=True)

        self.mmcv = tk.Canvas(right, bg=C_PANEL, highlightthickness=0,
                              width=420, height=250)
        self.mmcv.pack(pady=(8, 0))

        self._build_controls(right)
        self._tick()

    # ------------------------------------------------------------------
    def _lf(self, parent, title):
        f = tk.LabelFrame(parent, text=title, bg=C_PANEL, fg=C_ACCENT,
                          font=("Helvetica", 9, "bold"), bd=1, relief="groove")
        f.pack(fill="x", padx=10, pady=4)
        return f

    def _scale(self, parent, lo, hi, res, var, cmd, width=250):
        s = tk.Scale(parent, from_=lo, to=hi, resolution=res, orient="horizontal",
                     variable=var, command=lambda *_: cmd(), bg=C_PANEL, fg=C_TEXT,
                     troughcolor=C_PANEL2, highlightthickness=0, length=width,
                     font=("Helvetica", 8), sliderrelief="flat")
        return s

    def _build_controls(self, p):
        b = self.b
        ch = self.changed

        f = self._lf(p, T("광원  (4 LED / 5 레이저, 전원 6)", "light source (4 LED / 5 laser, supply 6)"))
        self.v_src = tk.IntVar(value=0)
        tk.Checkbutton(f, text=T("6a 전원 켜기", "6a power on"), variable=self.v_src,
                       command=ch, bg=C_PANEL, fg=C_TEXT, selectcolor=C_PANEL2,
                       activebackground=C_PANEL, font=("Helvetica", 9)).grid(
            row=0, column=0, sticky="w", padx=6, pady=2)
        self.v_ring = tk.DoubleVar(value=0.0)
        tk.Label(f, text=T("5a 회전 링 [°]", "5a rotation ring [deg]"), bg=C_PANEL,
                 fg=C_DIM, font=("Helvetica", 8)).grid(row=1, column=0, sticky="w", padx=6)
        self._scale(f, -90, 90, 1, self.v_ring, ch, 240).grid(row=2, column=0, padx=6)
        self.v_wid = tk.DoubleVar(value=5.5)
        tk.Label(f, text=T("5c 빔 폭 [mm]", "5c beam width [mm]"), bg=C_PANEL,
                 fg=C_DIM, font=("Helvetica", 8)).grid(row=3, column=0, sticky="w", padx=6)
        self._scale(f, 2.0, 10.0, 0.1, self.v_wid, ch, 240).grid(row=4, column=0, padx=6)

        f = self._lf(p, T("시료와 스크린", "sample and screen"))
        self.lbl_smp = tk.Label(f, text="", bg=C_PANEL, fg=C_TEXT,
                                font=("Helvetica", 9))
        self.lbl_smp.grid(row=0, column=0, columnspan=3, sticky="w", padx=6, pady=2)
        tk.Label(f, text=T("스크린 위치  x [mm]", "screen position  x [mm]"),
                 bg=C_PANEL, fg=C_DIM, font=("Helvetica", 8)).grid(
            row=1, column=0, sticky="w", padx=6)
        self.v_x = tk.DoubleVar(value=50.0)
        self._scale(f, 0, 140, 0.5, self.v_x, ch, 240).grid(row=2, column=0,
                                                            columnspan=2, padx=6)
        tk.Button(f, text="◀", width=2, command=lambda: self.step_x(-0.5)).grid(row=2, column=2)
        tk.Button(f, text="▶", width=2, command=lambda: self.step_x(+0.5)).grid(row=3, column=2)
        tk.Label(f, text=T("시료 회전 [°]", "sample rotation [deg]"), bg=C_PANEL,
                 fg=C_DIM, font=("Helvetica", 8)).grid(row=4, column=0, sticky="w", padx=6)
        self.v_rot = tk.DoubleVar(value=0.0)
        self._scale(f, -90, 90, 1, self.v_rot, ch, 240).grid(row=5, column=0,
                                                             columnspan=2, padx=6)

        f = self._lf(p, T("14 광학 필터", "14 optical filters"))
        self.v_n = tk.IntVar(value=0)
        tk.Label(f, text=T("필터 개수 n", "number of filters n"), bg=C_PANEL,
                 fg=C_DIM, font=("Helvetica", 8)).grid(row=0, column=0, padx=6)
        for i in range(6):
            tk.Radiobutton(f, text=str(i), variable=self.v_n, value=i, command=ch,
                           bg=C_PANEL, fg=C_TEXT, selectcolor=C_PANEL2,
                           activebackground=C_PANEL,
                           font=("Helvetica", 9)).grid(row=0, column=1 + i, padx=1)

        f = self._lf(p, T("회로  (7 가변저항, 8 스위치)",
                          "circuit (7 variable resistor, 8 switch)"))
        tk.Label(f, text=T("7d 저항 노브", "7d resistance knob"), bg=C_PANEL,
                 fg=C_DIM, font=("Helvetica", 8)).grid(row=0, column=0, sticky="w", padx=6)
        self.v_R = tk.DoubleVar(value=0.10)
        self._scale(f, 0.0, 1.0, 0.001, self.v_R, ch, 240).grid(row=1, column=0,
                                                                columnspan=2, padx=6)
        tk.Button(f, text="◀", width=2, command=lambda: self.step_R(-0.002)).grid(row=1, column=2)
        tk.Button(f, text="▶", width=2, command=lambda: self.step_R(+0.002)).grid(row=2, column=2)
        self.v_sw = tk.IntVar(value=0)
        tk.Checkbutton(f, text=T("8 스위치 단락(닫음)", "8 switch shorted (closed)"),
                       variable=self.v_sw, command=ch, bg=C_PANEL, fg=C_TEXT,
                       selectcolor=C_PANEL2, activebackground=C_PANEL,
                       font=("Helvetica", 9)).grid(row=3, column=0, columnspan=3,
                                                   sticky="w", padx=6, pady=2)

        f = self._lf(p, T("10 LCC 전원", "10 LCC power supply"))
        self.v_lcc = tk.IntVar(value=0)
        tk.Checkbutton(f, text=T("10d 전원", "10d power"), variable=self.v_lcc,
                       command=ch, bg=C_PANEL, fg=C_TEXT, selectcolor=C_PANEL2,
                       activebackground=C_PANEL, font=("Helvetica", 9)).grid(
            row=0, column=0, sticky="w", padx=6)
        tk.Label(f, text=T("10c 전압 노브", "10c voltage knob"), bg=C_PANEL, fg=C_DIM,
                 font=("Helvetica", 8)).grid(row=1, column=0, sticky="w", padx=6)
        self.v_lccv = tk.DoubleVar(value=0.0)
        self._scale(f, 0.0, 1.0, 0.0005, self.v_lccv, ch, 240).grid(row=2, column=0,
                                                                    columnspan=2, padx=6)
        tk.Button(f, text="◀", width=2, command=lambda: self.step_lcc(-0.0015)).grid(row=2, column=2)
        tk.Button(f, text="▶", width=2, command=lambda: self.step_lcc(+0.0015)).grid(row=3, column=2)

        f = self._lf(p, T("11 멀티미터 레인지", "11 multimeter range"))
        self.v_mm = tk.StringVar(value="off")
        for i, (val, txt) in enumerate([("off", "OFF"), ("ohm", "200 kΩ"),
                                        ("dc", "2 V ⎓"), ("ac", "20 V ~")]):
            tk.Radiobutton(f, text=txt, variable=self.v_mm, value=val, command=ch,
                           bg=C_PANEL, fg=C_TEXT, selectcolor=C_PANEL2,
                           activebackground=C_PANEL,
                           font=("Helvetica", 9)).grid(row=0, column=i, padx=6, pady=4)

        self.warn = tk.Label(p, text="", bg=C_PANEL, fg=C_WARN, wraplength=400,
                             justify="left", font=("Helvetica", 9))
        self.warn.pack(padx=10, pady=6, fill="x")

    # ------------------------------------------------------------------
    def step_x(self, d):
        self.v_x.set(round(min(140.0, max(0.0, self.v_x.get() + d)), 1))
        self.changed()

    def step_R(self, d):
        self.v_R.set(round(min(1.0, max(0.0, self.v_R.get() + d)), 4))
        self.changed()

    def step_lcc(self, d):
        self.v_lccv.set(round(min(1.0, max(0.0, self.v_lccv.get() + d)), 5))
        self.changed()

    def changed(self):
        b = self.b
        b.src_on = bool(self.v_src.get())
        b.laser_ring = self.v_ring.get()
        b.laser_width = self.v_wid.get()
        b.screen_x = self.v_x.get()
        b.sample_rot = self.v_rot.get()
        b.filters_n = self.v_n.get()
        b.R_knob = self.v_R.get()
        b.switch_closed = bool(self.v_sw.get())
        b.lcc_on = bool(self.v_lcc.get())
        b.lcc_knob = self.v_lccv.get()
        b.mm_mode = self.v_mm.get()
        self.app.refresh()

    def sync(self):
        b = self.b
        self.v_src.set(1 if b.src_on else 0)
        self.v_n.set(b.filters_n)
        self.v_mm.set(b.mm_mode)

    def _tick(self):
        self.redraw()
        self.after(500, self._tick)

    # ------------------------------------------------------------- view
    def _crossed(self):
        b = self.b
        p1, p2 = b.polarisers()
        if p1 is None or p2 is None:
            return None
        return abs(((self.b.s.pol1_deg - self.b.s.pol2_deg) % 180.0) - 90.0) < 1.0

    def _beta_factor(self):
        b = self.b
        bb = b._beta()
        if bb is None:
            return None
        return math.sin(math.radians(2.0 * bb)) ** 2

    def _field_row(self):
        """list of 180 colour strings for the observation window"""
        b = self.b
        s = b.s
        cols = []
        cross = self._crossed()
        bf = self._beta_factor()
        lo, hi = b.sample_extent()
        smp = b.active_sample()
        lit = b.source() is not None and b.src_on and b.src_connected
        led = b.source() == "led"
        base_gain = 1.15 if b.paper_on_pol1 else 0.85
        for j in range(180):
            x = b.screen_x + (j * 4 + 2 - PTR_X) / PX_PER_MM
            if not lit or not led:
                cols.append("#0a0b0d")
                continue
            if cross is None:
                g = 210 if (smp is None or lo <= x <= hi) else 190
                cols.append("#%02x%02x%02x" % (g, g - 4, g - 14))
                continue
            inside = smp is not None and lo <= x <= hi
            if not inside or bf is None:
                cols.append("#0d0e11" if cross else "#d7d3c8")
                continue
            R = b.retardance(x)
            cols.append(COLOUR.rgb(abs(R), base_gain * bf, crossed=cross))
        return cols

    def redraw(self):
        cv = self.cv
        b = self.b
        s = b.s
        cv.delete("all")
        VX = 30
        cv.create_text(VX, 18, anchor="w",
                       text=T("관측  ―  편광판 2를 통해 본 모습",
                              "observation  ―  view through polariser 2"),
                       fill=C_TEXT, font=("Helvetica", 11, "bold"))
        cv.create_rectangle(VX - 2, 34, VX + VIEW_W + 2, 34 + VIEW_H + 2,
                            outline="#43474e")
        cols = self._field_row()
        img = tk.PhotoImage(width=180, height=1)
        img.put("{" + " ".join(cols) + "}", to=(0, 0))
        self._img = img.zoom(4, VIEW_H)
        cv.create_image(VX, 36, image=self._img, anchor="nw")
        # laser spot
        if b.source() == "laser" and b.src_on and b.src_connected:
            cross = self._crossed()
            bf = self._beta_factor()
            lo, hi = b.sample_extent()
            smp = b.active_sample()
            t = 1.0
            if cross is not None:
                if smp is None or not (lo <= b.screen_x <= hi) or bf is None:
                    t = 0.0 if cross else 1.0
                else:
                    d = 2 * math.pi * abs(b.retardance(b.screen_x)) / s.lam
                    t = bf * math.sin(d / 2.0) ** 2
                    if not cross:
                        t = 1.0 - t
            r = max(3.0, b.laser_width * 2.4)
            v = int(40 + 215 * min(1.0, t ** 0.6))
            cv.create_oval(VX + PTR_X - r, 36 + VIEW_H / 2 - r,
                           VX + PTR_X + r, 36 + VIEW_H / 2 + r,
                           fill="#%02x%02x%02x" % (v, int(v * 0.16), int(v * 0.12)),
                           outline="")
        # screen scale
        y0 = 36 + VIEW_H + 12
        cv.create_rectangle(VX, y0, VX + VIEW_W, y0 + 34, fill="#f3f1ea",
                            outline="#b9b5aa")
        if b.slot["1e"] == "screen" or b.hold_by_hand:
            for mm in range(0, 141):
                px = VX + PTR_X + (mm - b.screen_x) * PX_PER_MM
                if px < VX + 2 or px > VX + VIEW_W - 2:
                    continue
                if mm % 10 == 0:
                    cv.create_line(px, y0 + 2, px, y0 + 16, fill="#2a2a2a")
                    cv.create_text(px, y0 + 25, text=str(mm // 10),
                                   fill="#2a2a2a", font=("Helvetica", 8))
                elif mm % 5 == 0:
                    cv.create_line(px, y0 + 2, px, y0 + 12, fill="#4a4a4a")
                else:
                    cv.create_line(px, y0 + 2, px, y0 + 8, fill="#7a7a7a")
        else:
            cv.create_text(VX + VIEW_W / 2, y0 + 17,
                           text=T("(눈금 스크린이 설치되지 않음)",
                                  "(screen with the scale not installed)"),
                           fill="#8a8a8a", font=("Helvetica", 9))
        cv.create_polygon(VX + PTR_X - 8, 36 + VIEW_H + 2, VX + PTR_X + 8,
                          36 + VIEW_H + 2, VX + PTR_X, 36 + VIEW_H + 12,
                          fill="#e04a3a", outline="")
        cv.create_text(VX + PTR_X, y0 + 46,
                       text=T("홀더 왼쪽 모서리 (원점 포인터)",
                              "left edge of the holder (origin pointer)"),
                       fill=C_DIM, font=("Helvetica", 8))

        # ---------------- schematic of the bench ----------------------
        yb = y0 + 80
        cv.create_text(VX, yb - 16, anchor="w",
                       text=T("광학 벤치 배치", "layout of the optical bench"),
                       fill=C_TEXT, font=("Helvetica", 11, "bold"))
        draw_bench_rail(cv, VX, yb + 58, VIEW_W, 46, "sb")
        xs = {"1a": VX + 70, "1c": VX + 210, "1e": VX + 355, "1d": VX + 505,
              "1b": VX + 650}
        if b.source() and b.src_on and b.src_connected:
            col = "#ff4a35" if b.source() == "laser" else "#ffd9a0"
            cv.create_line(xs["1a"] + 12, yb + 34, xs["1b"], yb + 34, fill=col,
                           width=3 if b.source() == "laser" else 7)
        for k, cx in xs.items():
            v = b.slot[k]
            cv.create_text(cx, yb + 92, text=k, fill=C_DIM, font=("Helvetica", 8))
            if v == "led":
                draw_led(cv, cx, yb + 34, "sb", on=b.src_on and b.src_connected, scale=0.8)
            elif v == "laser":
                draw_laser(cv, cx, yb + 34, "sb", on=b.src_on and b.src_connected, scale=0.8)
            elif v in ("pol1", "pol2"):
                draw_polariser(cv, cx, yb + 34, 1 if v == "pol1" else 2, "sb", scale=0.7)
            elif v == "screen":
                draw_screen(cv, cx, yb + 34, "sb", scale=0.7)
            elif v == "lcc":
                draw_lcc(cv, cx, yb + 34, "sb", scale=0.7)
            elif v == "pd":
                draw_photodiode(cv, cx, yb + 34, "sb", scale=0.8)
            else:
                cv.create_rectangle(cx - 26, yb + 6, cx + 26, yb + 62,
                                    outline="#3d4148", dash=(3, 4))
        if b.paper_on_pol1:
            for k, cx in xs.items():
                if b.slot[k] == "pol1":
                    cv.create_rectangle(cx - 26, yb + 8, cx - 18, yb + 60,
                                        fill="#fdfdfa", outline="#c8c8c2")
        if b.filters_mounted:
            for k, cx in xs.items():
                if b.slot[k] == "pol1":
                    for i in range(max(1, b.filters_n)):
                        cv.create_rectangle(cx + 16 + i * 4, yb + 14,
                                            cx + 24 + i * 4, yb + 54,
                                            fill="#cfd3d6", outline="#9aa0a6",
                                            stipple="gray50")

        # ---------------- status --------------------------------------
        ys = yb + 120
        smp = b.active_sample()
        name = {"ruler1": PART_NAME["ruler1"], "ruler2": PART_NAME["ruler2"],
                "both": T("자 №1 + №2 겹침", "rulers No.1 + No.2 stacked"),
                "strip": PART_NAME["strip"], "lcc": PART_NAME["lcc"]}.get(smp, "-")
        self.lbl_smp.config(text=T("시료: ", "sample: ") + name)
        lines = []
        if b.source() is None:
            lines.append(T("• 1a 지지대에 광원이 없습니다.", "• no light source on support 1a."))
        elif not b.src_connected:
            lines.append(T("• 광원이 전원 6에 연결되지 않았습니다.",
                           "• the light source is not connected to supply 6."))
        if b.slot["1b"] != "pd":
            lines.append(T("• 1b 지지대에 광검출기가 없습니다.",
                           "• no photodetector on support 1b."))
        if "mm" in b.on_table and b.mm_mode == "ohm" and b.switch_closed:
            lines.append(T("• 저항 측정 중에는 스위치를 열어야 합니다 (전원과 분리).",
                           "• for a resistance measurement the element must be "
                           "disconnected from any supply."))
        if b.slot["1e"] == "lcc" and not b.lcc_connected:
            lines.append(T("• LCC가 전원 10에 연결되지 않았습니다.",
                           "• the LCC is not connected to supply 10."))
        self.warn.config(text="\n".join(lines))
        cv.create_text(VX, ys, anchor="nw", fill=C_DIM, font=("Helvetica", 9),
                       text=T("포인터 위치  x = %.1f mm        7d 저항 노브 %.1f %%",
                              "pointer at  x = %.1f mm        7d knob %.1f %%")
                       % (b.screen_x, 100.0 * b.R_knob))

        # ---------------- multimeter ----------------------------------
        mc = self.mmcv
        mc.delete("all")
        if "mm" in b.on_table:
            t, u = b.multimeter()
            draw_multimeter(mc, 130, 12, "m", t, u, b.mm_mode)
            mc.create_text(20, 20, anchor="nw", fill=C_DIM, font=("Helvetica", 9),
                           text=T("11d COM\n11e V/Ω", "11d COM\n11e V/Ohm"))
        else:
            mc.create_text(210, 120, text=T("멀티미터가 탁자에 없습니다",
                                            "the multimeter is not on the table"),
                           fill=C_DIM, font=("Helvetica", 10))


# ==========================================================================
#  11.  APPLICATION
# ==========================================================================
class App(tk.Tk):
    def __init__(self, seed=None):
        super().__init__()
        self.title(APP_TITLE)
        self.configure(bg=C_BG)
        self.geometry("1600x900")
        self.session = Session(seed)
        self.bench = Bench(self.session)

        top = tk.Frame(self, bg=C_PANEL2, height=38)
        top.pack(fill="x")
        tk.Label(top, text=APP_TITLE, bg=C_PANEL2, fg=C_TEXT,
                 font=("Helvetica", 12, "bold")).pack(side="left", padx=12, pady=6)
        tk.Label(top, text=T("45회 국제물리올림피아드 · 2014 · 아스타나",
                             "45th International Physics Olympiad · 2014 · Astana"),
                 bg=C_PANEL2, fg=C_DIM, font=("Helvetica", 9)).pack(side="left", padx=6)
        tk.Button(top, text=T("새 세션", "new session"),
                  command=self.new_session).pack(side="right", padx=10, pady=4)
        self.lbl_seed = tk.Label(top, text="", bg=C_PANEL2, fg=C_DIM,
                                 font=("Courier", 9))
        self.lbl_seed.pack(side="right", padx=10)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=C_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=C_PANEL, foreground=C_TEXT,
                        padding=(18, 8), font=("Helvetica", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", C_PANEL2)])
        style.configure("TFrame", background=C_BG)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.tab_asm = AssemblyTab(self.nb, self)
        self.tab_bench = BenchTab(self.nb, self)
        self.nb.add(self.tab_asm, text=T("  조립  ", "  assembly  "))
        self.nb.add(self.tab_bench, text=T("  실험대  ", "  bench  "))
        self.refresh()

    def new_session(self):
        self.session = Session()
        self.bench = Bench(self.session)
        self.tab_asm.b = self.bench
        self.tab_bench.b = self.bench
        self.tab_bench.sync()
        self.refresh()

    def refresh(self):
        self.lbl_seed.config(text="session %09d" % self.session.seed)
        self.tab_asm.redraw()
        self.tab_bench.redraw()


def main():
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
        elif a.startswith("--lang="):
            globals()["LANG"] = a.split("=", 1)[1]
    lc_model()
    App(seed).mainloop()


if __name__ == "__main__":
    main()
