#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  3rd European Physics Olympiad  (EuPhO 2019, Riga, Latvia)
  Experimental Problem :  PROPAGATION OF RADIO WAVES
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Apparatus after Figure 1 of the problem sheet: the waterproof
    emitter A, the power meter B, the metal tubes C1-C4, the capped
    plastic tube D, the plastic box E, aluminium foil, foam blocks, a
    30 cm ruler, a bucket, a jug and a cup of water, tissue, rope, a
    clip, tape, a rubber band and a wooden rod.  Five set-ups can be
    built: free space, a foil reflector, the water box, the water-filled
    tube and the air-filled metal tubes.  The waves really propagate:
    standing waves in air and water, Debye-model water with its losses,
    evanescent modes below cut-off.
    Only what a real instrument shows is displayed: the receiver's dBm
    reading (one every 15 s) and the ruler's mm scale.  No wavelength,
    attenuation or refractive index is ever computed.  Every hidden
    parameter is randomised for each session.

    Run:   python3 eupho2019_E1_sim_KO.py   [--seed=N] [--lang=ko|en]
"""
import math
import os
import random
import sys
import time

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except Exception:                                            # pragma: no cover
    tk = None

# --------------------------------------------------------------------------- #
#  i18n
# --------------------------------------------------------------------------- #

LANG = "KO"          # the EN edition differs only in this line


def T(ko, en):
    """Bilingual string helper."""
    return ko if LANG == "KO" else en


# --------------------------------------------------------------------------- #
#  Physical constants
# --------------------------------------------------------------------------- #

C0 = 2.99792458e8            # speed of light, m/s
EPS0 = 8.8541878128e-12      # vacuum permittivity
X_TE11 = 1.8411837813406593  # first zero of J1'
X_TM01 = 2.4048255576957728  # first zero of J0
X_TE21 = 3.0542369282271403  # second zero of J1'

MODES = ((X_TE11, 1.00), (X_TM01, 0.34), (X_TE21, 0.13))


def kstar(x, d):
    """Transverse wave number of a circular waveguide mode, k* = 2x/d."""
    return 2.0 * x / d


# --------------------------------------------------------------------------- #
#  Apparatus geometry (metres)  -- reconstructed from Figure 1 of the problem
# --------------------------------------------------------------------------- #

# Emitter "A": white cylindrical waterproof housing.  The dashed line in Fig. 1
# marks the wave source, 6 mm below the nose of the housing.
EM_D = 0.034            # outer diameter
EM_L = 0.105            # length
EM_SRC = 0.006          # source depth below the nose  (the "6 mm" of Fig. 1)

# Receiver "B": hand-held power meter, sensor marked with a red triangle.
RX_W = 0.082
RX_H = 0.148
RX_T = 0.016

# Metal tubes "C" -- inner diameters given in the problem text.
TUBES = (
    {"id": "C1", "d": 0.041, "L": 0.40, "wall": 0.0010, "spiral": False},
    {"id": "C2", "d": 0.046, "L": 0.40, "wall": 0.0010, "spiral": False},
    {"id": "C3", "d": 0.059, "L": 0.40, "wall": 0.0012, "spiral": False},
    {"id": "C4", "d": 0.100, "L": 0.60, "wall": 0.0015, "spiral": True},
)

# Plastic tube "D" (one end closed by a cap)
TUBE_D_ID = 0.050
TUBE_D_L = 0.70
TUBE_D_WALL = 0.003

# Plastic box "E" (inner dimensions)
BOX_W = 0.300
BOX_D = 0.180
BOX_H = 0.135

# Foam blocks "G"
FOAM_W = 0.075
FOAM_H = 0.030

RULER_L = 0.300         # ruler "H", 30 cm, millimetre divisions

JUG_VOL = 250e-6        # jug "J"   250 mL
CUP_VOL = 50e-6         # cup "K"    50 mL
BUCKET_VOL = 6.0e-3     # bucket "I"  6 L


# --------------------------------------------------------------------------- #
#  Hidden truth  (randomised per session)
# --------------------------------------------------------------------------- #

class Truth(object):
    """Hidden parameters of one experimental session.

    Nothing in this class is ever displayed by the GUI; the student can only
    observe the receiver reading and the ruler scale.
    """

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1, 10 ** 8)
        self.seed = int(seed)
        rng = random.Random(self.seed)
        self.rng = rng

        # ---- emitter -------------------------------------------------------
        # The problem only tells the student 200 MHz .. 5 GHz.  The apparatus
        # is designed so that every tube is below cut-off (f < 1.76 GHz) and so
        # that the wavelength in water is comfortably measurable with a ruler.
        self.f = rng.uniform(0.840e9, 0.905e9)
        self.omega = 2.0 * math.pi * self.f
        self.k0 = self.omega / C0
        self.lam_air = C0 / self.f
        self.P_tx = 10.0 ** (rng.uniform(-2.0, 2.0) / 10.0) * 1e-3   # W, EIRP

        # ---- water ---------------------------------------------------------
        self.T_water = rng.uniform(17.5, 24.0)             # degC
        self.sigma = rng.uniform(0.010, 0.050)             # S/m, tap water
        es = 87.9 * math.exp(-0.00458 * self.T_water)
        ei = 5.6
        tau = (1.1109e-11 - 3.824e-13 * self.T_water
               + 6.938e-15 * self.T_water ** 2
               - 5.096e-17 * self.T_water ** 3)
        wt = self.omega * tau
        self.eps_r = ei + (es - ei) / (1.0 + wt * wt)
        self.eps_i = (es - ei) * wt / (1.0 + wt * wt) + self.sigma / (self.omega * EPS0)
        self.tand = self.eps_i / self.eps_r
        rt = math.sqrt(1.0 + self.tand ** 2)
        self.n_water = math.sqrt(self.eps_r) * math.sqrt((1.0 + rt) / 2.0)
        self.kappa = math.sqrt(self.eps_r) * math.sqrt((rt - 1.0) / 2.0)
        self.k_water = self.omega * self.n_water / C0          # bulk wave number
        self.alpha_water = self.omega * self.kappa / C0        # bulk Np/m
        self.lam_water = 2.0 * math.pi / self.k_water

        # ---- receiver ------------------------------------------------------
        self.noise_dbm = rng.uniform(-102.0, -98.0)
        self.noise_W = 10.0 ** (self.noise_dbm / 10.0) * 1e-3
        self.read_sigma_db = rng.uniform(0.10, 0.22)
        self.disp_step = 0.1                                   # dB resolution

        # ---- imperfections -------------------------------------------------
        self.leak_db = self.noise_dbm - rng.uniform(8.0, 14.0)  # foil leakage
        self.r_cap = rng.uniform(0.32, 0.50)                   # foil-on-cap mirror
        self.mode_mix = [m[1] * rng.uniform(0.75, 1.30) for m in MODES]
        self.mode_phase = [rng.uniform(0, 2 * math.pi) for _ in MODES]
        self.room_seed = rng.randrange(1, 10 ** 6)
        self.ruler_sigma = 0.00025                             # 0.25 mm reading
        self.pour_rel = 0.02                                   # pouring accuracy

    # -- derived helpers ---------------------------------------------------- #

    def mu_air(self, d, mode=0):
        """Decay constant of an air-filled tube of inner diameter d."""
        ks = kstar(MODES[mode][0], d)
        v = ks * ks - self.k0 * self.k0
        return math.sqrt(v) if v > 0.0 else 0.0

    def k_air_guide(self, d, mode=0):
        ks = kstar(MODES[mode][0], d)
        v = self.k0 * self.k0 - ks * ks
        return math.sqrt(v) if v > 0.0 else 0.0

    def water_guide(self, d):
        """(k, alpha) of the TE11 mode of a water-filled tube of diameter d."""
        ks = kstar(X_TE11, d)
        kb = self.k_water
        v = kb * kb - ks * ks
        if v <= 0.0:
            mu = math.sqrt(-v)
            return 0.0, mu
        k = math.sqrt(v)
        alpha = self.alpha_water * kb / k
        return k, alpha

    def room_ripple(self, key, x):
        """Deterministic, smooth multipath ripple (dB) of the room."""
        r = random.Random((self.room_seed * 7919 + hash(key)) & 0x7FFFFFFF)
        tot = 0.0
        for _ in range(3):
            amp = r.uniform(0.25, 0.9)
            per = r.uniform(0.35, 1.6)
            ph = r.uniform(0, 2 * math.pi)
            tot += amp * math.sin(2 * math.pi * x / per + ph)
        return tot


# --------------------------------------------------------------------------- #
#  Physics engine -- returns the TRUE received power in watts for each rig
# --------------------------------------------------------------------------- #

class Physics(object):

    def __init__(self, truth):
        self.t = truth

    # ---------------------------------------------------------------- free air
    def free_space(self, r):
        """Emitter and receiver in the open room, separation r (m)."""
        t = self.t
        r = max(r, 0.02)
        pl = (t.lam_air / (4.0 * math.pi * r)) ** 2
        p = t.P_tx * pl
        p *= 10.0 ** (t.room_ripple("free", r) / 10.0)
        return p

    def foil_mirror(self, x_rx, x_mirror):
        """Emitter at x=0, flat aluminium reflector at x=x_mirror,
        receiver on the axis at x=x_rx.  Gives a standing wave of period
        lambda_air/2 superposed on the 1/r^2 decay."""
        t = self.t
        x_rx = min(max(x_rx, 0.05), x_mirror - 0.02)
        r1 = x_rx
        r2 = 2.0 * x_mirror - x_rx
        k = t.k0
        # direct + image (metal sheet: reflection coefficient -1)
        re = math.cos(k * r1) / r1 - 0.92 * math.cos(k * r2) / r2
        im = math.sin(k * r1) / r1 - 0.92 * math.sin(k * r2) / r2
        amp2 = re * re + im * im
        p = t.P_tx * (t.lam_air / (4.0 * math.pi)) ** 2 * amp2
        p *= 10.0 ** (0.18 * t.room_ripple("mirror", x_rx) / 10.0)
        return p

    # ------------------------------------------------------------- water box
    def water_box(self, h_water, r_air):
        """Task 2.  Emitter lying on the aluminium foil at the bottom of box E,
        water surface at height h_water above the foil, receiver r_air above
        the surface.

        Fabry-Perot resonance of the water layer between the foil mirror and the
        water/air interface -> maxima spaced by lambda_water/2.
        """
        t = self.t
        n = t.n_water
        a = t.alpha_water
        k = t.k_water
        h = max(h_water, 1e-3)
        rt = (n - 1.0) / (n + 1.0)                 # water -> air amplitude refl.
        ph = 2.0 * k * h
        dec = math.exp(-2.0 * a * h)
        den_re = 1.0 + rt * math.cos(ph) * dec
        den_im = rt * math.sin(ph) * dec
        den = den_re * den_re + den_im * den_im
        # apparent source depth h/n  ->  geometrical spreading
        reff = r_air + h / n + 0.02
        p = 4.0e-4 * t.P_tx * dec / den * (t.lam_air / (4.0 * math.pi * reff)) ** 2
        p *= 10.0 ** (0.25 * t.room_ripple("box", h + 3.1 * r_air) / 10.0)
        p += 10.0 ** (t.leak_db / 10.0) * 1e-3 * 0.35
        return p

    def water_box_uncovered(self, h_water, r_air, dz):
        """Emitter not (fully) submerged: direct leakage dominates."""
        t = self.t
        reff = max(r_air + 0.02, 0.03)
        frac = min(max(dz / EM_D, 0.0), 1.0)
        p = 2.0e-3 * t.P_tx * (0.05 + 0.95 * (1.0 - frac)) * \
            (t.lam_air / (4.0 * math.pi * reff)) ** 2
        p *= 10.0 ** (0.4 * t.room_ripple("boxu", h_water) / 10.0)
        return p

    # ------------------------------------------------------- water-filled tube
    def water_tube(self, z, h_water, d=TUBE_D_ID, tube_len=TUBE_D_L, gap_rx=0.01):
        """Task 3.  Foil-wrapped plastic tube filled with water to height
        h_water; emitter source at depth z below the water surface; receiver
        just above the open upper end.

        z : depth of the source point below the water surface (m)
        """
        t = self.t
        k, a = self.t.water_guide(d)
        if k <= 0.0:
            return 10.0 ** (t.leak_db / 10.0) * 1e-3
        z = max(z, 0.005)
        u = max(h_water - z, 0.003)               # source height above the cap
        # up-going wave + wave reflected from the foil-covered cap
        ph = 2.0 * k * u
        dec = math.exp(-2.0 * a * u) * t.r_cap
        re = 1.0 - dec * math.cos(ph)
        im = -dec * math.sin(ph)
        cav = re * re + im * im
        p = 2.0e-2 * t.P_tx * math.exp(-2.0 * a * z) * cav
        # evanescent air gap between the water surface and the tube mouth
        gap = max(tube_len - h_water, 0.0)
        mu = t.mu_air(d)
        p *= math.exp(-2.0 * mu * gap)
        # transmission into air + short air path to the sensor
        p *= (0.030 / (0.030 + max(gap_rx, 0.0))) ** 2
        p *= 10.0 ** (0.15 * t.room_ripple("wtube", z) / 10.0)
        p += 10.0 ** (t.leak_db / 10.0) * 1e-3 * 0.6
        return p

    # --------------------------------------------------------- air metal tube
    def air_tube(self, z, d, gap_rx=0.005):
        """Task 4.  Emitter source at distance z inside an air-filled metal tube
        of inner diameter d, receiver at the outlet.

        All tubes are below cut-off, so every mode is evanescent; the lowest
        (TE11) one survives longest.
        """
        t = self.t
        z = max(z, 0.002)
        re = 0.0
        im = 0.0
        for i, (x, _) in enumerate(MODES):
            mu = t.mu_air(d, i)
            if mu <= 0.0:
                continue
            amp = t.mode_mix[i] * math.exp(-mu * z)
            re += amp * math.cos(t.mode_phase[i])
            im += amp * math.sin(t.mode_phase[i])
        amp2 = re * re + im * im
        p = 0.06 * t.P_tx * amp2
        p *= (0.02 / (0.02 + gap_rx)) ** 2
        p *= 10.0 ** (0.12 * t.room_ripple("atube%d" % int(d * 1e4), z) / 10.0)
        p += 10.0 ** (t.leak_db / 10.0) * 1e-3
        return p


# --------------------------------------------------------------------------- #
#  Receiver model
# --------------------------------------------------------------------------- #

class Receiver(object):
    """Power meter "B".  Takes one reading every 15 s (problem statement)."""

    PERIOD = 15.0

    def __init__(self, truth):
        self.t = truth
        self.rng = random.Random(truth.seed ^ 0x5EED)
        self.value = None            # last displayed reading, dBm
        self.history = []            # rolling display graph
        self.count = 0

    def sample(self, p_true_W):
        t = self.t
        p = max(p_true_W, 0.0) + t.noise_W * (0.5 + self.rng.random())
        dbm = 10.0 * math.log10(p / 1e-3)
        dbm += self.rng.gauss(0.0, t.read_sigma_db)
        dbm = round(dbm / t.disp_step) * t.disp_step
        dbm = max(min(dbm, 20.0), -110.0)
        self.value = dbm
        self.count += 1
        self.history.append(dbm)
        if len(self.history) > 90:
            self.history.pop(0)
        return dbm

    def reset(self):
        self.value = None
        self.history = []


# --------------------------------------------------------------------------- #
#  Palette / colours
# --------------------------------------------------------------------------- #

COL = {
    "bg":        "#1c1f24",
    "panel":     "#262a31",
    "panel2":    "#2f343c",
    "line":      "#4a515b",
    "text":      "#e8ecf1",
    "dim":       "#98a1ad",
    "accent":    "#f0a03c",
    "ok":        "#5ec27a",
    "bad":       "#e2645a",
    "table":     "#6b563f",
    "table2":    "#5a4735",
    "cloth":     "#e9e6df",
    "alu":       "#c6ccd2",
    "alu_d":     "#8e979f",
    "alu_l":     "#eef1f4",
    "plastic":   "#3b4046",
    "plastic_l": "#565c64",
    "cap":       "#7d838b",
    "hous":      "#f4f1ea",
    "hous_d":    "#cfc9bd",
    "water":     "#3f97cf",
    "water_d":   "#2a6f9c",
    "water_l":   "#7fc0e8",
    "box":       "#dcecf4",
    "foam":      "#f7f4ec",
    "foam_d":    "#ded9cc",
    "foil":      "#d3d8dd",
    "foil_d":    "#a7aeb5",
    "wood":      "#c9a06a",
    "rope":      "#d9cdb4",
    "rule":      "#f2d98c",
    "rule_d":    "#c9b064",
    "screen":    "#0d1420",
    "screen_g":  "#1d3350",
    "led":       "#7fe0ff",
    "red":       "#e4453a",
}


def _rr(cv, x0, y0, x1, y1, r=6, **kw):
    """Rounded rectangle."""
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


# --------------------------------------------------------------------------- #
#  Parts catalogue
# --------------------------------------------------------------------------- #

PARTS = [
    ("A",  lambda: T("라디오파 송신기", "Radio emitter"),          1),
    ("B",  lambda: T("수신기(전력계)", "Receiver (power meter)"),  1),
    ("C1", lambda: T("금속관 d=41 mm", "Metal tube d=41 mm"),      1),
    ("C2", lambda: T("금속관 d=46 mm", "Metal tube d=46 mm"),      1),
    ("C3", lambda: T("금속관 d=59 mm", "Metal tube d=59 mm"),      1),
    ("C4", lambda: T("금속관 d=100 mm", "Metal tube d=100 mm"),    1),
    ("D",  lambda: T("플라스틱관(마개)", "Plastic tube (capped)"),  1),
    ("E",  lambda: T("플라스틱 상자", "Plastic box"),               1),
    ("F",  lambda: T("알루미늄 포일", "Aluminium foil"),            1),
    ("G",  lambda: T("폼 조각", "Foam pieces"),                     4),
    ("H",  lambda: T("자 (30 cm)", "Ruler (30 cm)"),                1),
    ("I",  lambda: T("물 양동이", "Bucket of water"),               1),
    ("J",  lambda: T("주전자 (250 mL)", "Jug (250 mL)"),            1),
    ("K",  lambda: T("컵 (50 mL)", "Cup (50 mL)"),                  1),
    ("L",  lambda: T("휴지", "Tissues"),                            1),
    ("M",  lambda: T("가는 밧줄", "Thin rope"),                     1),
    ("N",  lambda: T("클립", "Clip"),                               1),
    ("O",  lambda: T("테이프", "Tape"),                             1),
    ("P",  lambda: T("고무줄", "Rubber bands"),                     1),
    ("Q",  lambda: T("나무 막대", "Wooden rod"),                    1),
]

PART_COUNT = dict((p[0], p[2]) for p in PARTS)


def part_name(pid):
    for p in PARTS:
        if p[0] == pid:
            return p[1]()
    return pid


# --------------------------------------------------------------------------- #
#  Rig definitions -- what a complete set-up needs, and in which order
# --------------------------------------------------------------------------- #

RIGS = {
    "free": {
        "name": lambda: T("자유 공간 배치", "Free-space set-up"),
        "note": lambda: T("송신기와 수신기만 탁자 위에 놓는다.",
                          "Emitter and receiver on the table, nothing else."),
        "need": {"A": 1, "B": 1},
        "opt":  {"H": 1, "L": 1},
        "order": {},
    },
    "mirror": {
        "name": lambda: T("포일 반사판 배치", "Foil-reflector set-up"),
        "note": lambda: T("나무 막대에 포일을 테이프로 붙여 평면 반사판을 세운다.",
                          "Tape the foil onto the wooden rod to build a flat reflector."),
        "need": {"A": 1, "B": 1, "F": 1, "Q": 1, "O": 1},
        "opt":  {"H": 1, "L": 1, "P": 1},
        "order": {"F": ["Q"], "O": ["Q", "F"], "A": ["O"], "B": ["A"]},
    },
    "box": {
        "name": lambda: T("물 상자 배치 (그림 2)", "Water-box set-up (Figure 2)"),
        "note": lambda: T("폼 위에 상자를 올리고 포일로 안쪽을 감싼 뒤 송신기를 넣고 물을 붓는다.",
                          "Box on the foam, foil screen inside, emitter in it, then pour water."),
        "need": {"E": 1, "G": 4, "F": 1, "A": 1, "B": 1, "I": 1},
        "opt":  {"H": 1, "J": 1, "K": 1, "L": 1, "O": 1},
        "order": {"E": ["G"], "F": ["E"], "A": ["F"], "I": ["A"], "B": ["A"]},
    },
    "wtube": {
        "name": lambda: T("물 채운 플라스틱관 배치", "Water-filled plastic tube"),
        "note": lambda: T("플라스틱관을 테이프로 세우고 포일로 단단히 감싼 뒤 물을 채우고, "
                          "밧줄과 클립으로 송신기를 매단다.",
                          "Stand the tube with tape, wrap it tightly with foil, fill with "
                          "water and hang the emitter on the rope with the clip."),
        "need": {"D": 1, "O": 1, "F": 1, "I": 1, "M": 1, "N": 1, "A": 1, "B": 1},
        "opt":  {"H": 1, "J": 1, "K": 1, "L": 1, "P": 1, "G": 4},
        "order": {"O": ["D"], "F": ["D", "O"], "I": ["F"], "M": ["F"],
                  "N": ["M"], "A": ["N"], "B": ["A"]},
    },
    "atube": {
        "name": lambda: T("공기 금속관 배치", "Air-filled metal tube"),
        "note": lambda: T("금속관을 놓고 밧줄과 클립으로 송신기를 관 속 깊이 넣는다.",
                          "Lay the metal tube down and pull the emitter into it with the rope."),
        "need": {"C": 1, "M": 1, "N": 1, "A": 1, "B": 1},
        "opt":  {"H": 1, "O": 1, "Q": 1, "L": 1, "G": 4},
        "order": {"M": ["C"], "N": ["M"], "A": ["N"], "B": ["A"]},
    },
}

RIG_ORDER = ["free", "mirror", "box", "wtube", "atube"]


def _norm(pid):
    """C1..C4 all count as the generic tube 'C'."""
    return "C" if pid.startswith("C") else pid


class Assembly(object):
    """Book-keeping of what has been placed on the bench."""

    def __init__(self):
        self.placed = []          # list of concrete part ids, in placement order

    # ------------------------------------------------------------------ query
    def counts(self):
        c = {}
        for p in self.placed:
            k = _norm(p)
            c[k] = c.get(k, 0) + 1
        return c

    def candidates(self):
        """Rigs still compatible with what is on the bench."""
        c = self.counts()
        out = []
        for key in RIG_ORDER:
            spec = RIGS[key]
            ok = True
            for k, v in c.items():
                lim = spec["need"].get(k, 0) + spec["opt"].get(k, 0)
                if v > lim:
                    ok = False
                    break
            if ok:
                out.append(key)
        return out

    def complete(self):
        """Return the rig key if the set-up is a complete, valid one."""
        c = self.counts()
        for key in self.candidates():
            need = RIGS[key]["need"]
            if all(c.get(k, 0) >= v for k, v in need.items()):
                return key
        return None

    def n_placed(self, pid):
        return sum(1 for p in self.placed if p == pid)

    # ------------------------------------------------------------------ mutate
    def can_place(self, pid):
        """(ok, message).  Enforces stock, compatibility and assembly order."""
        if self.n_placed(pid) >= PART_COUNT.get(pid, 1):
            return False, T("%s: 남은 부품이 없습니다." % pid,
                            "%s: no more of this part." % pid)
        trial = Assembly()
        trial.placed = list(self.placed) + [pid]
        cands = trial.candidates()
        if not cands:
            return False, T("%s 은(는) 지금 구성과 맞지 않습니다. 다른 배치를 만들려면 먼저 분해하세요."
                            % part_name(pid),
                            "%s does not fit this set-up. Dismantle first to build another one."
                            % part_name(pid))
        # order rules: satisfied if at least one candidate rig allows it now
        c = self.counts()
        for key in cands:
            need = RIGS[key]["need"]
            if _norm(pid) not in need and _norm(pid) not in RIGS[key]["opt"]:
                continue
            req = RIGS[key]["order"].get(_norm(pid), [])
            if all(c.get(r, 0) > 0 for r in req):
                return True, ""
        # nothing allowed -> report the missing prerequisites of the first rig
        key = cands[0]
        req = RIGS[key]["order"].get(_norm(pid), [])
        miss = [r for r in req if c.get(r, 0) == 0]
        if miss:
            names = ", ".join(part_name(m if m != "C" else "C1") for m in miss)
            return False, T("먼저 %s 을(를) 설치해야 %s 을(를) 놓을 수 있습니다."
                            % (names, part_name(pid)),
                            "Place %s before %s." % (names, part_name(pid)))
        return False, T("지금은 %s 을(를) 놓을 수 없습니다." % part_name(pid),
                        "%s cannot be placed right now." % part_name(pid))

    def place(self, pid):
        ok, msg = self.can_place(pid)
        if ok:
            self.placed.append(pid)
        return ok, msg

    def remove(self, pid):
        """Remove the most recently placed instance, provided nothing depends
        on it."""
        if pid not in self.placed:
            return False, ""
        rest = list(self.placed)
        rest.reverse()
        idx = len(self.placed) - 1 - rest.index(pid)
        trial = list(self.placed)
        trial.pop(idx)
        # verify that the remaining sequence is still order-legal
        probe = Assembly()
        for p in trial:
            ok, _ = probe.can_place(p)
            if not ok:
                return False, T("%s 을(를) 먼저 떼어내야 합니다."
                                % part_name(trial[-1]),
                                "Remove %s first." % part_name(trial[-1]))
            probe.placed.append(p)
        self.placed = trial
        return True, ""

    def clear(self):
        self.placed = []


# --------------------------------------------------------------------------- #
#  Apparatus drawing primitives (pixel space)
# --------------------------------------------------------------------------- #

def _shade(cv, x0, y0, x1, y1, c_edge, c_mid, n=9, tags=()):
    """Vertical cylinder shading between y0 and y1."""
    for i in range(n):
        f = i / float(n - 1)
        t = abs(f - 0.38) / 0.62
        col = _mix(c_mid, c_edge, min(t, 1.0) ** 1.4)
        ya = y0 + (y1 - y0) * i / n
        yb = y0 + (y1 - y0) * (i + 1) / n
        cv.create_rectangle(x0, ya, x1, yb + 1, fill=col, outline=col, tags=tags)


def _mix(c1, c2, f):
    def rgb(c):
        return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
    a, b = rgb(c1), rgb(c2)
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3))


def dr_emitter(cv, x, y, L, D, tags=(), nose="right", src_mark=True):
    """White cylindrical waterproof emitter housing 'A'.
    (x, y) = centre;  nose points right (or left/up/down)."""
    if nose in ("up", "down"):
        # draw vertically
        h, w = L, D
        x0, x1 = x - w / 2.0, x + w / 2.0
        y0, y1 = y - h / 2.0, y + h / 2.0
        cap = min(w / 2.0, h * 0.30)         # hemispherical nose, inside L
        by0 = y0 + (cap if nose == "up" else 0.0)
        by1 = y1 - (cap if nose == "down" else 0.0)
        for i in range(9):
            f = i / 8.0
            t = abs(f - 0.35) / 0.65
            col = _mix(COL["hous"], COL["hous_d"], min(t, 1.0) ** 1.3)
            xa = x0 + w * i / 9.0
            xb = x0 + w * (i + 1) / 9.0
            cv.create_rectangle(xa, by0, xb + 1, by1, fill=col, outline=col,
                                tags=tags)
        cv.create_rectangle(x0, by0, x1, by1, outline=COL["hous_d"], tags=tags)
        ny = by0 if nose == "up" else by1
        sy = y0 + L * (EM_SRC / EM_L) if nose == "up" else y1 - L * (EM_SRC / EM_L)
        cv.create_arc(x0, ny - cap, x1, ny + cap,
                      start=0 if nose == "up" else 180, extent=180,
                      fill=COL["hous"], outline=COL["hous_d"], tags=tags)
        # collar ribs at the tail
        ty = y1 - L * 0.22 if nose == "up" else y0 + L * 0.22
        for i in range(3):
            yy = ty + (i * 3 if nose == "up" else -i * 3)
            cv.create_line(x0, yy, x1, yy, fill=COL["hous_d"], tags=tags)
        if src_mark and L > 18:
            cv.create_line(x0 - 3, sy, x1 + 3, sy, fill="#20242a",
                           dash=(4, 3), tags=tags)
        return
    h, w = D, L
    x0, x1 = x - w / 2.0, x + w / 2.0
    y0, y1 = y - h / 2.0, y + h / 2.0
    cap = min(w / 2.0, h * 0.30)             # hemispherical nose, inside L
    bx0 = x0 + (cap if nose == "left" else 0.0)
    bx1 = x1 - (cap if nose == "right" else 0.0)
    _shade(cv, bx0, y0, bx1, y1, COL["hous_d"], COL["hous"], 9, tags)
    cv.create_rectangle(bx0, y0, bx1, y1, outline=COL["hous_d"], tags=tags)
    nx = bx1 if nose == "right" else bx0
    sx = x1 - w * (EM_SRC / EM_L) if nose == "right" else x0 + w * (EM_SRC / EM_L)
    cv.create_arc(nx - cap, y0, nx + cap, y1,
                  start=270, extent=180 if nose == "right" else -180,
                  fill=COL["hous"], outline=COL["hous_d"], tags=tags)
    tx = bx0 + w * 0.22 if nose == "right" else bx1 - w * 0.22
    for i in range(3):
        xx = tx + (-i * 3 if nose == "right" else i * 3)
        cv.create_line(xx, y0, xx, y1, fill=COL["hous_d"], tags=tags)
    if src_mark and w > 18:
        cv.create_line(sx, y0 - 3, sx, y1 + 3, fill="#20242a", dash=(4, 3), tags=tags)


def dr_receiver(cv, x, y, w, h, reading=None, hist=None, tags=(), label=True,
                landscape=False, flip=False):
    """Hand-held power meter 'B'.

    landscape=False : portrait, sensor triangle on the short edge
    flip=True       : the sensor edge is the bottom / right one
    """
    if landscape:
        w, h = h, w
    _rr(cv, x - w / 2, y - h / 2, x + w / 2, y + h / 2, r=max(3, min(w, h) * 0.09),
        fill="#15181d", outline="#000000", tags=tags)
    sx0, sy0 = x - w * 0.42, y - h * 0.42
    sx1, sy1 = x + w * 0.42, y + h * 0.42
    if landscape:
        sx0 = x - w * 0.36 if not flip else x - w * 0.44
        sx1 = x + w * 0.44 if not flip else x + w * 0.36
    else:
        sy0 = y - h * 0.36 if not flip else y - h * 0.44
        sy1 = y + h * 0.44 if not flip else y + h * 0.36
    cv.create_rectangle(sx0, sy0, sx1, sy1, fill=COL["screen"],
                        outline="#0a0d13", tags=tags)
    # red sensor marker on the outer edge
    tw = max(3.0, min(w, h) * 0.11)
    if landscape:
        ex = (x + w * 0.47) if flip else (x - w * 0.47)
        dx = -tw * 1.3 if flip else tw * 1.3
        cv.create_polygon(ex, y - tw, ex, y + tw, ex + dx, y,
                          fill=COL["red"], outline="", tags=tags)
    else:
        ey = (y + h * 0.47) if flip else (y - h * 0.47)
        dy = -tw * 1.3 if flip else tw * 1.3
        cv.create_polygon(x - tw, ey, x + tw, ey, x, ey + dy,
                          fill=COL["red"], outline="", tags=tags)
    sw, sh = sx1 - sx0, sy1 - sy0
    if sw < 26 or sh < 22:
        return
    for i in range(1, 6):
        yy = sy0 + sh * i / 6.0
        cv.create_line(sx0, yy, sx1, yy, fill=COL["screen_g"], tags=tags)
    for i in range(1, 5):
        xx = sx0 + sw * i / 5.0
        cv.create_line(xx, sy0, xx, sy1, fill=COL["screen_g"], tags=tags)
    txt = "---" if reading is None else "%.1f" % reading
    fs = int(min(sh * 0.28, sw * 0.185))
    if fs >= 7:
        cv.create_text(sx0 + sw * 0.62, sy0 + sh * 0.42, text=txt, fill=COL["led"],
                       font=("DejaVu Sans", fs, "bold"), anchor="e", tags=tags)
        cv.create_text(sx0 + sw * 0.94, sy0 + sh * 0.46, text="dBm", fill="#5f9dc0",
                       font=("DejaVu Sans", max(6, int(fs * 0.45))), anchor="e",
                       tags=tags)
        if label and sh > 60:
            cv.create_text(sx0 + 4, sy0 + 3, text="00054  TERMINAL",
                           fill="#4f7ea0", anchor="nw",
                           font=("DejaVu Sans", max(5, int(fs * 0.32))), tags=tags)
    if hist and sh > 44:
        gx0, gx1 = sx0 + 4, sx1 - 4
        gy0, gy1 = sy0 + sh * 0.62, sy1 - 4
        lo, hi = min(hist), max(hist)
        if hi - lo < 4.0:
            mid = 0.5 * (hi + lo)
            lo, hi = mid - 2.0, mid + 2.0
        pts = []
        n = len(hist)
        for i, v in enumerate(hist):
            gx = gx0 + (gx1 - gx0) * (i / float(max(n - 1, 1)))
            gy = gy1 - (gy1 - gy0) * (v - lo) / (hi - lo)
            pts += [gx, gy]
        if len(pts) >= 4:
            cv.create_line(*pts, fill="#39c07a", width=1, tags=tags)


def dr_tube(cv, x, y, L, dout, horiz=True, spiral=False, alu=True,
            dinner=None, cut=False, tags=()):
    """Metal / plastic tube seen from the side.  If cut, the near wall is
    removed so the bore is visible."""
    c_l = COL["alu_l"] if alu else COL["plastic_l"]
    c_m = COL["alu"] if alu else COL["plastic"]
    c_d = COL["alu_d"] if alu else "#23262a"
    if horiz:
        x0, x1 = x - L / 2.0, x + L / 2.0
        y0, y1 = y - dout / 2.0, y + dout / 2.0
        if dinner is not None and (dout - dinner) * 0.5 < 3.0:
            dinner = max(dout * 0.25, dout - 6.0)
        _shade(cv, x0, y0, x1, y1, c_d, c_l, 11, tags)
        if cut and dinner:
            cv.create_rectangle(x0, y - dinner / 2.0, x1, y + dinner / 2.0,
                                fill="#14171b", outline="", tags=tags)
        if spiral:
            step = max(8.0, dout * 0.55)
            xx = x0
            while xx < x1:
                cv.create_line(xx, y1, xx + dout * 0.9, y0, fill=c_d,
                               width=1, tags=tags)
                xx += step
        cv.create_rectangle(x0, y0, x1, y1, outline=c_d, tags=tags)
        for ex in (x0, x1):
            cv.create_oval(ex - dout * 0.11, y0, ex + dout * 0.11, y1,
                           fill=c_m, outline=c_d, tags=tags)
            if dinner:
                cv.create_oval(ex - dout * 0.075, y - dinner / 2.0,
                               ex + dout * 0.075, y + dinner / 2.0,
                               fill="#101317", outline=c_d, tags=tags)
    else:
        x0, x1 = x - dout / 2.0, x + dout / 2.0
        y0, y1 = y - L / 2.0, y + L / 2.0
        for i in range(11):
            f = i / 10.0
            t = abs(f - 0.34) / 0.66
            col = _mix(c_l, c_d, min(t, 1.0) ** 1.2)
            xa = x0 + dout * i / 11.0
            xb = x0 + dout * (i + 1) / 11.0
            cv.create_rectangle(xa, y0, xb + 1, y1, fill=col, outline=col, tags=tags)
        cv.create_rectangle(x0, y0, x1, y1, outline=c_d, tags=tags)
        cv.create_oval(x0, y0 - dout * 0.10, x1, y0 + dout * 0.10,
                       fill=c_m, outline=c_d, tags=tags)


def dr_foil(cv, x0, y0, x1, y1, tags=(), seed=3, crumple=True):
    """Crumpled aluminium foil."""
    cv.create_rectangle(x0, y0, x1, y1, fill=COL["foil"], outline=COL["foil_d"],
                        tags=tags)
    if not crumple:
        return
    r = random.Random(seed)
    w, h = x1 - x0, y1 - y0
    n = max(6, int((w + h) / 9))
    for _ in range(n):
        ax = x0 + r.random() * w
        ay = y0 + r.random() * h
        bx = ax + r.uniform(-1, 1) * w * 0.22
        by = ay + r.uniform(-1, 1) * h * 0.30
        cv.create_line(ax, ay, bx, by,
                       fill=COL["foil_d"] if r.random() < 0.6 else "#eef1f4",
                       tags=tags)


def dr_foam(cv, x, y, w, h, tags=()):
    _rr(cv, x - w / 2, y - h / 2, x + w / 2, y + h / 2, r=2,
        fill=COL["foam"], outline=COL["foam_d"], tags=tags)
    r = random.Random(11)
    for _ in range(int(w * h / 60) + 3):
        px = x - w / 2 + r.random() * w
        py = y - h / 2 + r.random() * h
        cv.create_oval(px, py, px + 1.5, py + 1.5, fill=COL["foam_d"],
                       outline="", tags=tags)


def dr_water(cv, x0, y0, x1, y1, tags=(), surface=True):
    if y1 <= y0:
        return
    n = 8
    for i in range(n):
        ya = y0 + (y1 - y0) * i / n
        yb = y0 + (y1 - y0) * (i + 1) / n
        col = _mix(COL["water_l"], COL["water_d"], i / float(n - 1))
        cv.create_rectangle(x0, ya, x1, yb + 1, fill=col, outline=col, tags=tags)
    if surface:
        cv.create_line(x0, y0, x1, y0, fill="#bfe6ff", width=2, tags=tags)


def dr_ruler(cv, x0, y0, length, horiz=True, thick=16, tags=(), px_per_m=1000.0,
             reverse=False, offset_cm=0):
    """30 cm ruler with millimetre divisions.  With reverse=True the zero of the
    scale sits at the far end (bottom for a vertical ruler, right for a
    horizontal one)."""
    if horiz:
        cv.create_rectangle(x0, y0, x0 + length, y0 + thick, fill=COL["rule"],
                            outline=COL["rule_d"], tags=tags)
    else:
        cv.create_rectangle(x0, y0, x0 + thick, y0 + length, fill=COL["rule"],
                            outline=COL["rule_d"], tags=tags)
    mm = px_per_m / 1000.0
    n = int(RULER_L * 1000)
    step = 1
    if mm < 0.6:
        step = 5
    if mm < 0.25:
        step = 10
    for i in range(0, n + 1, step):
        p = i * mm
        if p > length:
            break
        if reverse:
            p = length - p
        if i % 100 == 0:
            ln = thick * 0.62
        elif i % 10 == 0:
            ln = thick * 0.40
        elif i % 5 == 0:
            ln = thick * 0.28
        else:
            ln = thick * 0.17
        if horiz:
            cv.create_line(x0 + p, y0, x0 + p, y0 + ln, fill="#5d4b1f", tags=tags)
            if i % 100 == 0 and thick > 11:
                cv.create_text(x0 + p + 1, y0 + thick - 1,
                               text=str(i // 10 + offset_cm), anchor="sw",
                               fill="#4a3c18",
                               font=("DejaVu Sans", max(5, int(thick * 0.34))), tags=tags)
        else:
            cv.create_line(x0, y0 + p, x0 + ln, y0 + p, fill="#5d4b1f", tags=tags)
            if i % 100 == 0 and thick > 11:
                cv.create_text(x0 + thick - 1, y0 + p + 1,
                               text=str(i // 10 + offset_cm), anchor="ne",
                               fill="#4a3c18",
                               font=("DejaVu Sans", max(5, int(thick * 0.34))), tags=tags)


def dr_bucket(cv, x, y, w, h, tags=(), fill_frac=0.7):
    cv.create_polygon(x - w / 2, y - h / 2, x + w / 2, y - h / 2,
                      x + w * 0.40, y + h / 2, x - w * 0.40, y + h / 2,
                      fill="#2f6fb0", outline="#20507f", tags=tags)
    wy = y - h / 2 + h * (1 - fill_frac)
    cv.create_polygon(x - w / 2 + (wy - (y - h / 2)) * 0.1, wy,
                      x + w / 2 - (wy - (y - h / 2)) * 0.1, wy,
                      x + w * 0.40, y + h / 2, x - w * 0.40, y + h / 2,
                      fill=COL["water"], outline="", tags=tags)
    cv.create_oval(x - w / 2, y - h / 2 - h * 0.09, x + w / 2, y - h / 2 + h * 0.09,
                   fill="#3d81c4", outline="#20507f", tags=tags)
    cv.create_arc(x - w * 0.55, y - h * 0.75, x + w * 0.55, y + h * 0.05,
                  start=20, extent=140, style="arc", outline="#7f8a92",
                  width=max(1, int(w * 0.04)), tags=tags)


def dr_jug(cv, x, y, w, h, tags=()):
    _rr(cv, x - w / 2, y - h / 2, x + w * 0.32, y + h / 2, r=w * 0.12,
        fill="#e8eef3", outline="#9fb0bd", tags=tags)
    cv.create_rectangle(x - w * 0.36, y - h * 0.15, x + w * 0.20, y + h * 0.42,
                        fill=COL["water_l"], outline="", tags=tags)
    cv.create_polygon(x + w * 0.32, y - h * 0.42, x + w * 0.56, y - h * 0.30,
                      x + w * 0.32, y - h * 0.16, fill="#e8eef3",
                      outline="#9fb0bd", tags=tags)
    cv.create_arc(x - w * 0.86, y - h * 0.22, x - w * 0.18, y + h * 0.34,
                  start=100, extent=160, style="arc", outline="#9fb0bd",
                  width=max(1, int(w * 0.07)), tags=tags)


def dr_cup(cv, x, y, w, h, tags=()):
    cv.create_polygon(x - w / 2, y - h / 2, x + w / 2, y - h / 2,
                      x + w * 0.33, y + h / 2, x - w * 0.33, y + h / 2,
                      fill="#eef3f7", outline="#a8b6c2", tags=tags)
    cv.create_oval(x - w / 2, y - h / 2 - h * 0.10, x + w / 2, y - h / 2 + h * 0.10,
                   fill="#f6f9fb", outline="#a8b6c2", tags=tags)


def dr_rope(cv, pts, tags=(), width=2):
    if len(pts) >= 4:
        cv.create_line(*pts, fill=COL["rope"], width=width, smooth=True, tags=tags)


def dr_clip(cv, x, y, s, tags=()):
    cv.create_arc(x - s, y - s, x + s, y + s, start=200, extent=300, style="arc",
                  outline="#b9c0c7", width=max(1, s * 0.30), tags=tags)


def dr_tape(cv, x, y, r, tags=()):
    cv.create_oval(x - r, y - r * 0.62, x + r, y + r * 0.62, fill="#e6d7ae",
                   outline="#bda979", tags=tags)
    cv.create_oval(x - r * 0.42, y - r * 0.26, x + r * 0.42, y + r * 0.26,
                   fill=COL["panel"], outline="#bda979", tags=tags)


def dr_band(cv, x, y, r, tags=()):
    cv.create_oval(x - r, y - r * 0.42, x + r, y + r * 0.42, outline="#c98b8b",
                   width=max(2, r * 0.22), tags=tags)


def dr_rod(cv, x, y, L, w, horiz=True, tags=()):
    if horiz:
        cv.create_rectangle(x - L / 2, y - w / 2, x + L / 2, y + w / 2,
                            fill=COL["wood"], outline="#9d7a4b", tags=tags)
    else:
        cv.create_rectangle(x - w / 2, y - L / 2, x + w / 2, y + L / 2,
                            fill=COL["wood"], outline="#9d7a4b", tags=tags)


def dr_tissue(cv, x, y, w, h, tags=()):
    _rr(cv, x - w / 2, y - h / 2, x + w / 2, y + h / 2, r=3, fill="#f8fafc",
        outline="#c9d2da", tags=tags)
    cv.create_polygon(x - w * 0.12, y - h * 0.5, x + w * 0.12, y - h * 0.5,
                      x, y - h * 0.86, fill="#ffffff", outline="#d5dde4", tags=tags)


def dr_box(cv, x0, y0, x1, y1, tags=(), depth=0.0):
    """Transparent plastic box seen from the side / in slight perspective."""
    if depth > 0:
        cv.create_polygon(x0, y0, x0 + depth, y0 - depth * 0.55,
                          x1 + depth, y0 - depth * 0.55, x1, y0,
                          fill="#cfe3ee", outline="#a8c4d4", tags=tags)
        cv.create_polygon(x1, y0, x1 + depth, y0 - depth * 0.55,
                          x1 + depth, y1 - depth * 0.55, x1, y1,
                          fill="#c3dbe9", outline="#a8c4d4", tags=tags)
    cv.create_rectangle(x0, y0, x1, y1, fill="", outline="#7fa8bf", width=2,
                        tags=tags)
    cv.create_line(x0 - 3, y0, x1 + 3, y0, fill="#9cc3d6", width=3, tags=tags)


ICON_DRAW = {}


def draw_icon(cv, pid, cx, cy, s, tags=()):
    """Small pictogram of a part for the palette."""
    if pid == "A":
        dr_emitter(cv, cx, cy, s * 1.5, s * 0.50, tags=tags, src_mark=False)
    elif pid == "B":
        dr_receiver(cv, cx, cy, s * 0.72, s * 1.25, reading=-29.0, tags=tags,
                    label=False)
    elif pid.startswith("C"):
        idx = int(pid[1]) - 1
        d = TUBES[idx]["d"]
        dd = s * (0.30 + 0.62 * (d - 0.041) / 0.059)
        dr_tube(cv, cx, cy, s * 1.7, dd, True, TUBES[idx]["spiral"], True,
                dd * 0.82, True, tags)
    elif pid == "D":
        dr_tube(cv, cx, cy, s * 1.7, s * 0.44, True, False, False, s * 0.34,
                False, tags)
        cv.create_rectangle(cx - s * 0.90, cy - s * 0.26, cx - s * 0.74,
                            cy + s * 0.26, fill=COL["cap"], outline="#5d636a",
                            tags=tags)
    elif pid == "E":
        dr_box(cv, cx - s * 0.85, cy - s * 0.38, cx + s * 0.70, cy + s * 0.45,
               tags=tags, depth=s * 0.22)
    elif pid == "F":
        dr_foil(cv, cx - s * 0.8, cy - s * 0.45, cx + s * 0.8, cy + s * 0.45,
                tags=tags)
    elif pid == "G":
        dr_foam(cv, cx - s * 0.35, cy, s * 0.55, s * 0.95, tags)
        dr_foam(cv, cx + s * 0.35, cy, s * 0.55, s * 0.95, tags)
    elif pid == "H":
        dr_ruler(cv, cx - s * 0.9, cy - s * 0.18, s * 1.8, True,
                 max(9, s * 0.36), tags, px_per_m=s * 1.8 / RULER_L)
    elif pid == "I":
        dr_bucket(cv, cx, cy, s * 1.0, s * 0.95, tags)
    elif pid == "J":
        dr_jug(cv, cx, cy, s * 0.85, s * 1.0, tags)
    elif pid == "K":
        dr_cup(cv, cx, cy, s * 0.62, s * 0.72, tags)
    elif pid == "L":
        dr_tissue(cv, cx, cy, s * 1.1, s * 0.62, tags)
    elif pid == "M":
        dr_rope(cv, [cx - s * 0.85, cy + s * 0.25, cx - s * 0.2, cy - s * 0.3,
                     cx + s * 0.3, cy + s * 0.3, cx + s * 0.85, cy - s * 0.2],
                tags, 3)
    elif pid == "N":
        dr_clip(cv, cx, cy, s * 0.42, tags)
    elif pid == "O":
        dr_tape(cv, cx, cy, s * 0.55, tags)
    elif pid == "P":
        dr_band(cv, cx, cy, s * 0.5, tags)
    elif pid == "Q":
        dr_rod(cv, cx, cy, s * 1.7, s * 0.16, True, tags)


# --------------------------------------------------------------------------- #
#  Rig state -- geometry of the assembled set-up (SI units, metres)
# --------------------------------------------------------------------------- #

class RigState(object):

    TABLE_X0 = -0.45
    TABLE_X1 = 2.10

    def __init__(self, kind, truth, tube_idx=1):
        self.kind = kind
        self.t = truth
        self.tube_idx = tube_idx
        self.water_V = 0.0
        self.rx_gap = 0.060          # receiver sensor distance (rig dependent)
        self.rx_x = 1.00             # free / mirror rigs
        self.mirror_x = 1.20
        self.em_y = 0.30             # wtube: source height above the inner bottom
        self.em_z = 0.040            # atube: source distance from the outlet
        self.foam = True             # foam blocks G under a horizontal tube
        self.ruler_on = False
        self.ruler_pos = 0.0         # sliding offset of the ruler along its axis
        self.reading = None          # last receiver reading (display only)
        self.hist = []               # rolling display graph of the receiver
        self.rng = random.Random(truth.seed ^ 0xABCD)

    # ---------------------------------------------------------------- geometry
    @property
    def tube(self):
        return TUBES[self.tube_idx]

    @property
    def box_floor(self):
        return FOAM_H + 0.003

    @property
    def box_h(self):
        """Water depth above the foil floor of box E."""
        return self.water_V / (BOX_W * BOX_D)

    @property
    def wt_bottom(self):
        return 0.005                  # inner bottom of the plastic tube

    @property
    def wt_H(self):
        return self.water_V / (math.pi * (TUBE_D_ID / 2.0) ** 2)

    @property
    def wt_mouth(self):
        return self.wt_bottom + TUBE_D_L - 0.005

    @property
    def at_axis_y(self):
        base = FOAM_H if self.foam else 0.0
        return base + self.tube["d"] / 2.0 + self.tube["wall"]

    def max_water(self):
        if self.kind == "box":
            return BOX_W * BOX_D * (BOX_H - 0.004)
        if self.kind == "wtube":
            return math.pi * (TUBE_D_ID / 2.0) ** 2 * (TUBE_D_L - 0.012)
        return 0.0

    def clamp(self):
        self.water_V = min(max(self.water_V, 0.0), self.max_water())
        if self.kind == "box":
            self.rx_gap = min(max(self.rx_gap, 0.020), 0.400)
        elif self.kind == "wtube":
            self.rx_gap = min(max(self.rx_gap, 0.005), 0.150)
            self.em_y = min(max(self.em_y, 0.010),
                            max(self.wt_H - 0.008, 0.012))
        elif self.kind == "atube":
            self.rx_gap = min(max(self.rx_gap, 0.002), 0.120)
            self.em_z = min(max(self.em_z, 0.004),
                            self.tube["L"] - EM_L + EM_SRC - 0.005)
        elif self.kind == "free":
            self.rx_x = min(max(self.rx_x, 0.10), 2.00)
        elif self.kind == "mirror":
            self.rx_x = min(max(self.rx_x, 0.10), self.mirror_x - 0.05)

    # ----------------------------------------------------------------- physics
    def true_power(self, phys):
        self.clamp()
        k = self.kind
        if k == "free":
            return phys.free_space(self.rx_x)
        if k == "mirror":
            return phys.foil_mirror(self.rx_x, self.mirror_x)
        if k == "box":
            h = self.box_h
            if h >= EM_D + 0.003:
                return phys.water_box(h, self.rx_gap)
            return phys.water_box_uncovered(h, self.rx_gap, EM_D - h)
        if k == "wtube":
            H = self.wt_H
            z = H - self.em_y
            if z <= 0.004:
                # emitter above the water surface: strong evanescent air path
                gap = max(TUBE_D_L - self.em_y, 0.0)
                return (self.t.P_tx * 2.0e-2
                        * math.exp(-2.0 * self.t.mu_air(TUBE_D_ID) * gap)
                        + 10.0 ** (self.t.leak_db / 10.0) * 1e-3)
            return phys.water_tube(z, H, TUBE_D_ID, TUBE_D_L, self.rx_gap)
        if k == "atube":
            return phys.air_tube(self.em_z, self.tube["d"], self.rx_gap)
        return 1e-30

    # ------------------------------------------------------------ ruler readout
    def ruler_items(self):
        """List of (label, true value in metres) that the ruler can read off.
        Only the raw scale positions of visible features -- nothing derived."""
        k = self.kind
        if k == "free":
            return [(T("송신기-수신기 거리", "emitter-receiver distance"), self.rx_x)]
        if k == "mirror":
            return [(T("송신기-수신기 거리", "emitter-receiver distance"), self.rx_x),
                    (T("송신기-반사판 거리", "emitter-reflector distance"), self.mirror_x)]
        if k == "box":
            return [(T("바닥 포일에서 수면까지", "foil floor to water surface"), self.box_h),
                    (T("수면에서 수신기 센서까지", "water surface to sensor"), self.rx_gap)]
        if k == "wtube":
            return [(T("관 바닥에서 수면까지", "tube bottom to water surface"), self.wt_H),
                    (T("수면에서 파원까지(밧줄)", "water surface to source (rope)"),
                     max(self.wt_H - self.em_y, 0.0)),
                    (T("관 입구에서 수신기까지", "tube mouth to sensor"), self.rx_gap)]
        if k == "atube":
            return [(T("관 출구에서 파원까지(밧줄)", "outlet to source (rope)"), self.em_z),
                    (T("관 출구에서 수신기까지", "outlet to sensor"), self.rx_gap)]
        return []

    def ruler_read(self, value):
        """Quantised, slightly noisy reading of the 1 mm scale."""
        mm = value * 1000.0
        key = int(round(mm * 4))
        r = random.Random((self.t.seed * 131 + key) & 0x7FFFFFFF)
        mm += r.gauss(0.0, self.t.ruler_sigma * 1000.0)
        return round(mm) / 1000.0

    # -------------------------------------------------------------------- water
    def pour(self, vol):
        v = vol * (1.0 + self.rng.gauss(0.0, self.t.pour_rel))
        self.water_V = min(self.water_V + v, self.max_water())
        self.clamp()

    def scoop(self, vol):
        v = vol * (1.0 + self.rng.gauss(0.0, self.t.pour_rel))
        self.water_V = max(self.water_V - v, 0.0)
        self.clamp()


# --------------------------------------------------------------------------- #
#  Scene renderer -- draws the apparatus to scale
# --------------------------------------------------------------------------- #

class Scene(object):

    def __init__(self):
        self.ox = 400.0
        self.oy = 520.0
        self.ppm = 700.0        # pixels per metre

    def w2s(self, x, y):
        return self.ox + x * self.ppm, self.oy - y * self.ppm

    def s2w(self, px, py):
        return (px - self.ox) / self.ppm, (self.oy - py) / self.ppm

    def m(self, v):
        return v * self.ppm

    # ------------------------------------------------------------------ table
    def draw_table(self, cv, x0=RigState.TABLE_X0, x1=RigState.TABLE_X1):
        ax, ay = self.w2s(x0, 0.0)
        bx, by = self.w2s(x1, 0.0)
        cv.create_rectangle(ax, ay, bx, ay + max(10, self.m(0.02)),
                            fill=COL["cloth"], outline="#cfcabf")
        cv.create_rectangle(ax, ay + max(10, self.m(0.02)), bx, ay + max(30, self.m(0.10)),
                            fill=COL["table"], outline=COL["table2"])
        cv.create_line(ax, ay, bx, ay, fill="#ffffff", width=2)

    # ------------------------------------------------------------------ router
    def draw(self, cv, kind, st, present, labels=False):
        cv.delete("all")
        cv.create_rectangle(-4000, -4000, 8000, 8000, fill=COL["bg"], outline="")
        self.draw_table(cv)
        if kind == "free":
            self._free(cv, st, present, labels)
        elif kind == "mirror":
            self._mirror(cv, st, present, labels)
        elif kind == "box":
            self._box(cv, st, present, labels)
        elif kind == "wtube":
            self._wtube(cv, st, present, labels)
        elif kind == "atube":
            self._atube(cv, st, present, labels)
        self._loose(cv, present, kind)

    # ------------------------------------------------------------------ pieces
    def _lab(self, cv, x, y, txt, on):
        if not on:
            return
        cv.create_text(x, y, text=txt, fill=COL["accent"],
                       font=("DejaVu Sans", 11, "bold"))

    def _receiver(self, cv, xs, ys, st, reading, hist, facing="body_right",
                  tag="rx"):
        """Receiver drawn so that its sensor (red marker) sits at (xs, ys)."""
        w = max(24.0, self.m(RX_W))
        h = max(42.0, self.m(RX_H))
        land = facing in ("body_right", "body_left")
        if facing == "body_right":
            cx, cy, flip = xs + h * 0.5, ys, False
        elif facing == "body_left":
            cx, cy, flip = xs - h * 0.5, ys, True
        elif facing == "body_up":
            cx, cy, flip = xs, ys - h * 0.5, True
        else:                                   # body_down
            cx, cy, flip = xs, ys + h * 0.5, False
        dr_receiver(cv, cx, cy, w, h, reading, hist, tags=(tag,),
                    landscape=land, flip=flip)

    def _emitter_h(self, cv, xs, ys, tag="em", nose="right"):
        dr_emitter(cv, xs, ys, max(16.0, self.m(EM_L)), max(6.0, self.m(EM_D)),
                   tags=(tag,), nose=nose)

    def _ruler_v(self, cv, xs, y_zero, tag="ruler", cover=0.0):
        """Vertical ruler standing on the reference level; its zero is at the
        bottom.  If the region of interest is higher than 30 cm the ruler is
        stepped upwards and the offset is written on it."""
        ln = self.m(RULER_L)
        off = 0
        while cover > RULER_L * (off / 30 + 1) and off < 90:
            off += 30
        y0 = y_zero - self.m(off / 100.0)
        dr_ruler(cv, xs, y0 - ln, ln, horiz=False,
                 thick=max(10.0, self.m(0.026)), tags=(tag,), px_per_m=self.ppm,
                 reverse=True, offset_cm=off)

    def _ruler_h(self, cv, x_zero, ys, tag="ruler", flip=False, cover=0.0):
        ln = self.m(RULER_L)
        off = 0
        while cover > RULER_L * (off / 30 + 1) and off < 120:
            off += 30
        shift = self.m(off / 100.0)
        x0 = x_zero - ln - shift if flip else x_zero + shift
        dr_ruler(cv, x0, ys, ln, horiz=True, thick=max(10.0, self.m(0.026)),
                 tags=(tag,), px_per_m=self.ppm, reverse=flip, offset_cm=off)

    # -------------------------------------------------------------- rig: free
    def _free(self, cv, st, present, labels):
        if "A" in present:
            xs, ys = self.w2s(0.0, EM_D / 2.0)
            self._emitter_h(cv, xs, ys)
            self._lab(cv, xs, ys - self.m(EM_D) - 12, "A", labels)
        if "B" in present:
            xs, ys = self.w2s(st.rx_x, RX_W / 2.0)
            self._receiver(cv, xs, ys, st, st.reading, st.hist, "body_right")
            self._lab(cv, xs - 22, ys - self.m(RX_W) * 0.6, "B", labels)
        if "H" in present:
            x0, y0 = self.w2s(0.0, 0.0)
            self._ruler_h(cv, x0, y0 + 6, cover=st.rx_x)

    # ------------------------------------------------------------ rig: mirror
    def _mirror(self, cv, st, present, labels):
        if "Q" in present:
            xs, ys = self.w2s(st.mirror_x, 0.28)
            dr_rod(cv, xs, ys, self.m(0.56), max(3.0, self.m(0.012)), False)
            self._lab(cv, xs + 16, ys + self.m(0.26), "Q", labels)
        if "F" in present:
            xw0, y0 = self.w2s(st.mirror_x, 0.52)
            _, y1 = self.w2s(0.0, 0.0)
            dx = max(14.0, self.m(0.30) * 0.55)      # 30 cm sheet, seen obliquely
            dy = dx * 0.42
            cv.create_polygon(xw0, y0, xw0 + dx, y0 - dy, xw0 + dx, y1 - dy,
                              xw0, y1, fill=COL["foil"], outline=COL["foil_d"])
            r = random.Random(5)
            for _ in range(int(max(10, (dx + (y1 - y0)) / 9))):
                f, g = r.random(), r.random()
                ax = xw0 + dx * f
                ay = y0 - dy * f + (y1 - y0) * g
                cv.create_line(ax, ay, ax + r.uniform(-1, 1) * dx * 0.25,
                               ay + r.uniform(-1, 1) * (y1 - y0) * 0.12,
                               fill=COL["foil_d"] if r.random() < 0.6 else "#eef1f4")
            dr_foil(cv, xw0 - max(3.0, self.m(0.004)), y0, xw0, y1, seed=7)
            self._lab(cv, xw0 + dx + 18, y0 + 20, "F", labels)
        if "O" in present:
            xs, ys = self.w2s(st.mirror_x, 0.50)
            dr_tape(cv, xs + max(6, self.m(0.02)), ys, max(5, self.m(0.018)))
        if "A" in present:
            xs, ys = self.w2s(0.0, EM_D / 2.0)
            self._emitter_h(cv, xs, ys)
            self._lab(cv, xs, ys - self.m(EM_D) - 12, "A", labels)
        if "B" in present:
            xs, ys = self.w2s(st.rx_x, RX_W / 2.0)
            self._receiver(cv, xs, ys, st, st.reading, st.hist, "body_right")
            self._lab(cv, xs - 22, ys - self.m(RX_W) * 0.6, "B", labels)
        if "H" in present:
            x0, y0 = self.w2s(0.0, 0.0)
            self._ruler_h(cv, x0, y0 + 6, cover=max(st.rx_x, st.mirror_x))

    # --------------------------------------------------------------- rig: box
    def _box(self, cv, st, present, labels):
        bx0, _ = self.w2s(-BOX_W / 2.0, 0.0)
        bx1, _ = self.w2s(+BOX_W / 2.0, 0.0)
        if "G" in present:
            for fx in (-BOX_W / 2 + 0.045, -0.045, 0.045, BOX_W / 2 - 0.045):
                xs, ys = self.w2s(fx, FOAM_H / 2.0)
                dr_foam(cv, xs, ys, self.m(FOAM_W), self.m(FOAM_H))
            xs, ys = self.w2s(BOX_W / 2 - 0.045, FOAM_H / 2.0)
            self._lab(cv, xs, ys + self.m(FOAM_H), "G", labels)
        if "E" not in present:
            return
        _, ytop = self.w2s(0.0, FOAM_H + BOX_H)
        _, ybot = self.w2s(0.0, FOAM_H)
        dr_box(cv, bx0, ytop, bx1, ybot, depth=self.m(0.045))
        self._lab(cv, bx1 + 18, ytop + 16, "E", labels)
        fl = st.box_floor
        if "F" in present:
            _, yf = self.w2s(0.0, fl)
            dr_foil(cv, bx0 + 2, yf - max(3, self.m(0.004)), bx1 - 2, yf, seed=7)
            for sx in (bx0 + 2, bx1 - 2):
                dr_foil(cv, sx - max(2, self.m(0.003)), ytop + 4,
                        sx + max(2, self.m(0.003)), yf, seed=9)
            self._lab(cv, bx0 + 16, ytop + 30, "F", labels)
        h = st.box_h
        if "I" in present and h > 1e-4:
            _, yw = self.w2s(0.0, fl + h)
            _, yf = self.w2s(0.0, fl)
            dr_water(cv, bx0 + 3, yw, bx1 - 3, yf)
        if "A" in present:
            xs, ys = self.w2s(0.0, fl + EM_D / 2.0)
            self._emitter_h(cv, xs, ys)
            self._lab(cv, xs - self.m(EM_L) / 2 - 14, ys, "A", labels)
        if "B" in present:
            xs, ys = self.w2s(0.0, fl + max(h, 0.0) + st.rx_gap)
            self._receiver(cv, xs, ys, st, st.reading, st.hist, "body_up")
            self._lab(cv, xs + max(24.0, self.m(RX_W)) * 0.7, ys - 16, "B", labels)
        if "H" in present:
            xs, _ = self.w2s(-BOX_W / 2.0 + 0.014, 0.0)
            _, y0 = self.w2s(0.0, fl)
            self._ruler_v(cv, xs, y0)

    # ------------------------------------------------------------- rig: wtube
    def _wtube(self, cv, st, present, labels):
        if "D" not in present:
            return
        dout = TUBE_D_ID + 2 * TUBE_D_WALL
        x0, _ = self.w2s(-dout / 2.0, 0.0)
        x1, _ = self.w2s(+dout / 2.0, 0.0)
        i0, _ = self.w2s(-TUBE_D_ID / 2.0, 0.0)
        i1, _ = self.w2s(+TUBE_D_ID / 2.0, 0.0)
        if i0 - x0 < 4.0:                       # keep the wall visible
            x0, x1 = i0 - 4.0, i1 + 4.0
        _, ytop = self.w2s(0.0, TUBE_D_L)
        _, ybot = self.w2s(0.0, 0.0)
        _, yin = self.w2s(0.0, st.wt_bottom)
        # cut-away: outer walls only, bore visible
        cv.create_rectangle(x0, ytop, i0, ybot, fill=COL["plastic"],
                            outline="#22262a")
        cv.create_rectangle(i1, ytop, x1, ybot, fill=COL["plastic"],
                            outline="#22262a")
        cv.create_rectangle(i0, ytop, i1, yin, fill="#101317", outline="")
        cv.create_rectangle(x0, yin, x1, ybot, fill=COL["cap"], outline="#5d636a")
        self._lab(cv, x1 + 20, (ytop + ybot) / 2, "D", labels)
        if "O" in present:
            xs, ys = self.w2s(0.0, 0.055)
            dr_tape(cv, xs + self.m(0.055), ys, max(5, self.m(0.018)))
            cv.create_line(x0, ys, x1, ys, fill="#e6d7ae",
                           width=max(2, self.m(0.012)))
        if "F" in present:
            fw = max(4.0, self.m(0.0025))
            dr_foil(cv, x0 - fw, ytop, x0, ybot, seed=13)
            dr_foil(cv, x1, ytop, x1 + fw, ybot, seed=17)
            dr_foil(cv, x0 - fw, ybot - max(3.0, self.m(0.003)), x1 + fw, ybot,
                    seed=19)
            self._lab(cv, x0 - 22, ytop + 40, "F", labels)
        H = st.wt_H
        if "I" in present and H > 1e-4:
            _, yw = self.w2s(0.0, st.wt_bottom + H)
            dr_water(cv, i0, yw, i1, yin)
        if "M" in present:
            top = ytop - self.m(0.05)
            sy = st.wt_bottom + st.em_y + (EM_L - EM_SRC)
            _, ys = self.w2s(0.0, sy)
            xs, _ = self.w2s(0.0, 0.0)
            dr_rope(cv, [xs, ys, xs + 2, (ys + top) / 2, xs, top,
                         xs + self.m(0.09), top - self.m(0.02)], width=2)
        if "N" in present:
            sy = st.wt_bottom + st.em_y + (EM_L - EM_SRC)
            xs, ys = self.w2s(0.0, sy)
            dr_clip(cv, xs, ys - 4, max(3, self.m(0.008)))
        if "A" in present:
            xs, ys = self.w2s(0.0, st.wt_bottom + st.em_y - EM_SRC + EM_L / 2.0)
            dr_emitter(cv, xs, ys, max(16.0, self.m(EM_L)),
                       max(6.0, self.m(EM_D)), tags=("em",), nose="down")
            self._lab(cv, xs - self.m(EM_D) - 16, ys, "A", labels)
        if "B" in present:
            xs, ys = self.w2s(0.0, st.wt_mouth + st.rx_gap)
            self._receiver(cv, xs, ys, st, st.reading, st.hist, "body_up")
            self._lab(cv, xs + max(24.0, self.m(RX_W)) * 0.7, ys - 16, "B", labels)
        if "H" in present:
            xr, _ = self.w2s(dout / 2.0 + 0.026, 0.0)
            _, y0 = self.w2s(0.0, st.wt_bottom)
            self._ruler_v(cv, xr, y0, cover=max(st.wt_H, st.em_y))

    # ------------------------------------------------------------- rig: atube
    def _atube(self, cv, st, present, labels):
        tb = st.tube
        if "C" not in present:
            return
        dout = tb["d"] + 2 * tb["wall"]
        ay = st.at_axis_y
        _, ys = self.w2s(0.0, ay)
        xL, _ = self.w2s(-tb["L"], 0.0)
        xR, _ = self.w2s(0.0, 0.0)
        y0 = ys - self.m(dout / 2.0)
        y1 = ys + self.m(dout / 2.0)
        yi0 = ys - self.m(tb["d"] / 2.0)
        yi1 = ys + self.m(tb["d"] / 2.0)
        if yi0 - y0 < 6.0:                       # keep the wall visible
            y0, y1 = yi0 - 6.0, yi1 + 6.0
        if "G" in present:
            for fx in (-tb["L"] + 0.06, -0.06):
                fxs, fys = self.w2s(fx, FOAM_H / 2.0)
                dr_foam(cv, fxs, fys, self.m(FOAM_W), self.m(FOAM_H))
        _shade(cv, xL, y0, xR, yi0, COL["alu_d"], COL["alu_l"], 7)
        _shade(cv, xL, yi1, xR, y1, COL["alu_d"], COL["alu_l"], 7)
        cv.create_rectangle(xL, yi0, xR, yi1, fill="#0f1216", outline="")
        if tb["spiral"]:
            step = max(9.0, self.m(dout) * 0.55)
            xx = xL
            while xx < xR:
                cv.create_line(xx, y1, xx + self.m(dout) * 0.9, yi1,
                               fill=COL["alu_d"])
                cv.create_line(xx, yi0, xx + self.m(dout) * 0.9, y0,
                               fill=COL["alu_d"])
                xx += step
        cv.create_rectangle(xL, y0, xR, y1, outline=COL["alu_d"])
        cv.create_oval(xR - self.m(dout) * 0.10, y0, xR + self.m(dout) * 0.10, y1,
                       fill=COL["alu"], outline=COL["alu_d"])
        cv.create_oval(xR - self.m(dout) * 0.07, yi0, xR + self.m(dout) * 0.07, yi1,
                       fill="#0b0e12", outline=COL["alu_d"])
        self._lab(cv, (xL + xR) / 2, y0 - 14, tb["id"], labels)
        if "M" in present:
            sx, _ = self.w2s(-st.em_z - (EM_L - EM_SRC), 0.0)
            dr_rope(cv, [sx, ys, xL - self.m(0.02), ys,
                         xL - self.m(0.10), ys + self.m(0.03)], width=2)
        if "N" in present:
            sx, _ = self.w2s(-st.em_z - (EM_L - EM_SRC), 0.0)
            dr_clip(cv, sx - 3, ys, max(3, self.m(0.008)))
        if "A" in present:
            cx, _ = self.w2s(-st.em_z + EM_SRC - EM_L / 2.0, 0.0)
            dr_emitter(cv, cx, ys, max(16.0, self.m(EM_L)),
                       max(6.0, self.m(EM_D)), tags=("em",), nose="right")
        if "B" in present:
            xs, yv = self.w2s(st.rx_gap, ay)
            self._receiver(cv, xs, yv, st, st.reading, st.hist, "body_right")
        if "H" in present:
            xz, _ = self.w2s(0.0, 0.0)
            self._ruler_h(cv, xz, y1 + max(6.0, self.m(0.008)), flip=True)

    # ------------------------------------------------------------- loose parts
    def _loose(self, cv, present, kind):
        """Vessels and consumables that just stand on the table."""
        bx = RigState.TABLE_X1 - 0.20
        if "I" in present:
            xs, ys = self.w2s(bx, 0.085)
            dr_bucket(cv, xs, ys, self.m(0.17), self.m(0.17))
        if "J" in present:
            xs, ys = self.w2s(bx - 0.22, 0.060)
            dr_jug(cv, xs, ys, self.m(0.11), self.m(0.12))
        if "K" in present:
            xs, ys = self.w2s(bx - 0.34, 0.035)
            dr_cup(cv, xs, ys, self.m(0.062), self.m(0.070))
        if "L" in present:
            xs, ys = self.w2s(bx - 0.46, 0.022)
            dr_tissue(cv, xs, ys, self.m(0.10), self.m(0.045))
        if "P" in present and kind != "mirror":
            xs, ys = self.w2s(bx - 0.56, 0.012)
            dr_band(cv, xs, ys, self.m(0.022))
        if "O" in present and kind in (None, "free", "box", "atube"):
            xs, ys = self.w2s(bx - 0.64, 0.016)
            dr_tape(cv, xs, ys, self.m(0.028))
        if "Q" in present and kind != "mirror":
            xs, ys = self.w2s(bx - 0.78, 0.008)
            dr_rod(cv, xs, ys, self.m(0.30), self.m(0.012), True)


# --------------------------------------------------------------------------- #
#  Assembly tab
# --------------------------------------------------------------------------- #

PAL_W = 250
CELL_W = 112
CELL_H = 74


class AssemblyTab(object):

    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent, bg=COL["bg"])
        top = tk.Frame(self.frame, bg=COL["panel"])
        top.pack(fill="x")
        self.msg = tk.Label(top, text="", bg=COL["panel"], fg=COL["dim"],
                            anchor="w", font=("DejaVu Sans", 11), pady=6, padx=10)
        self.msg.pack(side="left", fill="x", expand=True)
        self.btn_go = tk.Button(top, text=T("실험대로 이동 →", "Go to bench →"),
                                command=self.app.goto_bench, state="disabled",
                                bg=COL["panel2"], fg=COL["text"],
                                activebackground=COL["accent"], relief="flat",
                                padx=14, pady=4)
        self.btn_go.pack(side="right", padx=6, pady=4)
        tk.Button(top, text=T("전체 분해", "Dismantle all"),
                  command=self.clear_all, bg=COL["panel2"], fg=COL["text"],
                  relief="flat", padx=10, pady=4).pack(side="right", padx=4)

        self.cv = tk.Canvas(self.frame, bg=COL["bg"], highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Configure>", lambda e: self.redraw())
        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_drag)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Button-3>", self.on_right)
        self.cv.bind("<MouseWheel>", self.on_wheel)
        self.cv.bind("<Button-4>", lambda e: self.on_wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self.on_wheel(e, -1))

        self.scene = Scene()
        self.pal_off = 0
        self.drag = None
        self.chips = []
        self.cells = []
        self.pv_zoom = 1.0
        self.pv_key = "?"

    # ------------------------------------------------------------------ events
    def hit_cell(self, x, y):
        for pid, cx, cy, w, h in self.cells:
            if cx <= x <= cx + w and cy <= y <= cy + h:
                return pid
        return None

    def hit_chip(self, x, y):
        for pid, cx, cy, w, h in self.chips:
            if cx <= x <= cx + w and cy <= y <= cy + h:
                return pid
        return None

    def on_press(self, e):
        if e.x < PAL_W:
            pid = self.hit_cell(e.x, e.y)
            if pid:
                ok, msg = self.app.assembly.can_place(pid)
                self.msg.config(text=msg if not ok else
                                T("%s 을(를) 작업대로 끌어 놓으세요." % part_name(pid),
                                  "Drag %s onto the bench." % part_name(pid)),
                                fg=COL["bad"] if not ok else COL["dim"])
                if ok:
                    self.drag = [pid, e.x, e.y]
                    self.redraw()
            return
        pid = self.hit_chip(e.x, e.y)
        if pid:
            ok, msg = self.app.assembly.remove(pid)
            if not ok and msg:
                self.msg.config(text=msg, fg=COL["bad"])
            else:
                self.msg.config(text=T("%s 을(를) 회수했습니다." % part_name(pid),
                                       "%s returned to the kit." % part_name(pid)),
                                fg=COL["dim"])
            self.after_change()

    def on_drag(self, e):
        if self.drag:
            self.drag[1], self.drag[2] = e.x, e.y
            self.redraw()

    def on_release(self, e):
        if not self.drag:
            return
        pid = self.drag[0]
        self.drag = None
        if e.x > PAL_W:
            ok, msg = self.app.assembly.place(pid)
            if ok:
                self.msg.config(text=T("%s 설치 완료." % part_name(pid),
                                       "%s placed." % part_name(pid)), fg=COL["ok"])
            else:
                self.msg.config(text=msg, fg=COL["bad"])
        self.after_change()

    def on_right(self, e):
        if e.x > PAL_W and self.app.assembly.placed:
            pid = self.app.assembly.placed[-1]
            ok, msg = self.app.assembly.remove(pid)
            if ok:
                self.msg.config(text=T("%s 회수." % part_name(pid),
                                       "%s returned." % part_name(pid)), fg=COL["dim"])
            self.after_change()

    def on_wheel(self, e, direction=None):
        d = direction if direction is not None else (1 if e.delta > 0 else -1)
        if e.x < PAL_W:
            self.pal_off = min(max(self.pal_off - d * 40, 0), 400)
        else:
            self.pv_zoom = min(max(self.pv_zoom * (1.12 if d > 0 else 1 / 1.12),
                                   0.35), 6.0)
        self.redraw()

    def clear_all(self):
        self.app.assembly.clear()
        self.msg.config(text=T("모든 부품을 회수했습니다.", "All parts returned."),
                        fg=COL["dim"])
        self.after_change()

    PV_EXTENT = {                       # world size to fit: (width, height)
        "free":   (1.45, 0.34),
        "mirror": (1.55, 0.62),
        "box":    (0.62, 0.46),
        "wtube":  (0.46, 0.92),
        "atube":  (1.00, 0.34),
        None:     (0.90, 0.44),
    }

    def fit_preview(self, key, W, H):
        """Scale and centre the preview so the whole rig is visible."""
        aw = max(200.0, W - PAL_W - 30.0)
        ah = max(150.0, H - 215.0)
        wx, wy = self.PV_EXTENT.get(key, self.PV_EXTENT[None])
        self.scene.ppm = min(aw / wx, ah / wy) * self.pv_zoom
        self.scene.ppm = min(max(self.scene.ppm, 60.0), 6000.0)
        cxf = 0.30 if key in ("free", "mirror") else (0.62 if key == "atube"
                                                     else 0.48)
        self.scene.ox = PAL_W + 15.0 + aw * cxf
        self.scene.oy = 100.0 + ah

    def after_change(self):
        key = self.app.assembly.complete()
        self.btn_go.config(state="normal" if key else "disabled")
        self.app.on_assembly_change(key)
        self.redraw()

    # ----------------------------------------------------------------- drawing
    def redraw(self):
        cv = self.cv
        W = max(cv.winfo_width(), 900)
        H = max(cv.winfo_height(), 560)
        asm = self.app.assembly
        cands = asm.candidates()
        key = asm.complete() or (cands[0] if asm.placed else None)

        # ---- workspace preview
        present = set(_norm(p) for p in asm.placed)
        st = self.app.preview_state(key)
        if key != self.pv_key:
            self.pv_key, self.pv_zoom = key, 1.0
        self.fit_preview(key, W, H)
        self.scene.draw(cv, key, st, present, labels=True)
        cv.create_rectangle(0, 0, PAL_W, H, fill=COL["panel"], outline=COL["line"])

        # ---- palette
        self.cells = []
        cv.create_text(12, 12, text=T("부품 상자", "Parts kit"), anchor="nw",
                       fill=COL["text"], font=("DejaVu Sans", 12, "bold"))
        y = 40 - self.pal_off
        for i, (pid, namef, cnt) in enumerate(PARTS):
            col = i % 2
            row = i // 2
            cx = 10 + col * (CELL_W + 6)
            cy = y + row * CELL_H
            if cy > H or cy + CELL_H < 30:
                continue
            left = PART_COUNT[pid] - asm.n_placed(pid)
            ok, _ = asm.can_place(pid)
            bg = COL["panel2"] if ok else "#23262b"
            _rr(cv, cx, cy, cx + CELL_W, cy + CELL_H - 6, r=5, fill=bg,
                outline=COL["line"] if ok else "#33373d")
            draw_icon(cv, pid, cx + CELL_W * 0.30, cy + CELL_H * 0.42, 30)
            cv.create_text(cx + 8, cy + 6, text=pid, anchor="nw",
                           fill=COL["accent"] if ok else "#5c626a",
                           font=("DejaVu Sans", 10, "bold"))
            cv.create_text(cx + CELL_W / 2, cy + CELL_H - 18,
                           text=namef(), fill=COL["text"] if ok else "#666c74",
                           font=("DejaVu Sans", 7), width=CELL_W - 6)
            cv.create_text(cx + CELL_W - 8, cy + 6, text="x%d" % left, anchor="ne",
                           fill=COL["dim"] if left else "#55595f",
                           font=("DejaVu Sans", 8))
            self.cells.append((pid, cx, cy, CELL_W, CELL_H - 6))

        # ---- candidate rigs
        bx = PAL_W + 14
        cv.create_text(bx, 12, text=T("만들 수 있는 배치", "Possible set-ups"),
                       anchor="nw", fill=COL["dim"], font=("DejaVu Sans", 10, "bold"))
        yy = 32
        done = asm.complete()
        for k in RIG_ORDER:
            ok = k in cands
            mark = "●" if k == done else ("○" if ok else "·")
            c = COL["ok"] if k == done else (COL["text"] if ok else "#565b62")
            cv.create_text(bx, yy, text="%s %s" % (mark, RIGS[k]["name"]()),
                           anchor="nw", fill=c, font=("DejaVu Sans", 10))
            yy += 18
        if key:
            cv.create_text(bx, yy + 6, text=RIGS[key]["note"](), anchor="nw",
                           fill=COL["dim"], font=("DejaVu Sans", 9),
                           width=(W - PAL_W) * 0.46)

        # ---- placed chips
        self.chips = []
        cy = H - 44
        cv.create_text(PAL_W + 14, cy - 20,
                       text=T("설치된 부품 (클릭하면 회수)",
                              "Placed parts (click to return)"),
                       anchor="nw", fill=COL["dim"], font=("DejaVu Sans", 9))
        cx = PAL_W + 14
        for pid in asm.placed:
            w = 40
            _rr(cv, cx, cy, cx + w, cy + 24, r=5, fill=COL["panel2"],
                outline=COL["line"])
            cv.create_text(cx + w / 2, cy + 12, text=pid, fill=COL["text"],
                           font=("DejaVu Sans", 10, "bold"))
            self.chips.append((pid, cx, cy, w, 24))
            cx += w + 5
            if cx > W - 60:
                break

        # ---- drag ghost
        if self.drag:
            pid, gx, gy = self.drag
            cv.create_oval(gx - 26, gy - 26, gx + 26, gy + 26,
                           fill=COL["panel2"], outline=COL["accent"])
            draw_icon(cv, pid, gx, gy, 24)


# --------------------------------------------------------------------------- #
#  Bench tab
# --------------------------------------------------------------------------- #

class BenchTab(object):

    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent, bg=COL["bg"])
        self.scene = Scene()
        self.drag = None
        self.pan = None

        self.cv = tk.Canvas(self.frame, bg=COL["bg"], highlightthickness=0)
        self.cv.pack(side="left", fill="both", expand=True)
        self.cv.bind("<Configure>", lambda e: self.redraw())
        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_move)
        self.cv.bind("<ButtonRelease-1>", lambda e: self.on_up())
        self.cv.bind("<MouseWheel>", self.on_wheel)
        self.cv.bind("<Button-4>", lambda e: self.on_wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self.on_wheel(e, -1))
        self.cv.bind("<Shift-MouseWheel>", lambda e: self.on_wheel(e, None, True))

        p = tk.Frame(self.frame, bg=COL["panel"], width=336)
        p.pack(side="right", fill="y")
        p.pack_propagate(False)
        self.panel = p

        # -- header
        self.lbl_rig = tk.Label(p, text="", bg=COL["panel"], fg=COL["accent"],
                                font=("DejaVu Sans", 12, "bold"), anchor="w",
                                padx=10, pady=6)
        self.lbl_rig.pack(fill="x")
        self.lbl_clock = tk.Label(p, text="", bg=COL["panel"], fg=COL["dim"],
                                  font=("DejaVu Sans", 9), anchor="w", padx=10)
        self.lbl_clock.pack(fill="x")

        # -- receiver
        f = self._section(p, T("수신기 B", "Receiver B"))
        self.lbl_read = tk.Label(f, text="---", bg=COL["screen"], fg=COL["led"],
                                 font=("DejaVu Sans", 26, "bold"), pady=6)
        self.lbl_read.pack(fill="x", padx=8)
        self.lbl_unit = tk.Label(f, text="dBm", bg=COL["panel"], fg=COL["dim"],
                                 font=("DejaVu Sans", 9))
        self.lbl_unit.pack()
        r = tk.Frame(f, bg=COL["panel"])
        r.pack(fill="x", pady=3)
        self._btn(r, T("새 측정 (+15 s)", "New reading (+15 s)"), self.measure).pack(
            side="left", padx=8)
        self.auto = tk.IntVar(value=1)
        tk.Checkbutton(r, text=T("자동", "Auto"), variable=self.auto,
                       command=self.tick_auto, bg=COL["panel"], fg=COL["text"],
                       selectcolor=COL["panel2"], activebackground=COL["panel"],
                       font=("DejaVu Sans", 9)).pack(side="left")

        # -- ruler
        self.f_ruler = self._section(p, T("자 H 판독", "Ruler H readings"))
        self.lbl_ruler = tk.Label(self.f_ruler, text="", bg=COL["panel"],
                                  fg=COL["text"], justify="left", anchor="w",
                                  font=("DejaVu Sans", 10), padx=10)
        self.lbl_ruler.pack(fill="x")

        # -- controls
        self.f_ctl = self._section(p, T("조작", "Controls"))
        self.ctl_body = tk.Frame(self.f_ctl, bg=COL["panel"])
        self.ctl_body.pack(fill="x")

        # -- notebook
        f = self._section(p, T("실험 노트", "Lab notebook"))
        cols = ("v1", "v2", "p")
        self.tree = ttk.Treeview(f, columns=cols, show="headings", height=9)
        for c, w, tx in zip(cols, (92, 92, 92),
                            (T("눈금1(cm)", "scale1(cm)"),
                             T("눈금2(cm)", "scale2(cm)"),
                             T("P(dBm)", "P(dBm)"))):
            self.tree.heading(c, text=tx)
            self.tree.column(c, width=w, anchor="e")
        self.tree.pack(fill="x", padx=8, pady=2)
        r = tk.Frame(f, bg=COL["panel"])
        r.pack(fill="x", pady=3)
        self._btn(r, T("기록", "Record"), self.record).pack(side="left", padx=(8, 3))
        self._btn(r, T("삭제", "Delete"), self.del_row).pack(side="left", padx=3)
        self._btn(r, T("CSV 저장", "Save CSV"), self.save_csv).pack(side="left", padx=3)

        r = tk.Frame(p, bg=COL["panel"])
        r.pack(side="bottom", fill="x", pady=8)
        self._btn(r, T("← 조립 탭", "← Assembly"), self.app.goto_assembly).pack(
            side="left", padx=8)
        self._btn(r, T("보기 초기화", "Reset view"), self.reset_view).pack(side="left")

        self.rows = []
        self._auto_job = None

    # ------------------------------------------------------------------ helper
    def _section(self, parent, title):
        tk.Frame(parent, bg=COL["line"], height=1).pack(fill="x", pady=(8, 0))
        tk.Label(parent, text=title, bg=COL["panel"], fg=COL["dim"],
                 font=("DejaVu Sans", 9, "bold"), anchor="w", padx=10).pack(fill="x")
        f = tk.Frame(parent, bg=COL["panel"])
        f.pack(fill="x")
        return f

    def _btn(self, parent, text, cmd, w=None):
        return tk.Button(parent, text=text, command=cmd, bg=COL["panel2"],
                         fg=COL["text"], relief="flat", padx=8, pady=3,
                         activebackground=COL["accent"], font=("DejaVu Sans", 9),
                         width=w)

    # ------------------------------------------------------------ set-up entry
    def enter(self):
        st = self.app.state
        self.lbl_rig.config(text=RIGS[st.kind]["name"]() if st else "")
        for w in self.ctl_body.winfo_children():
            w.destroy()
        self.rows = []
        self.tree.delete(*self.tree.get_children())
        self.build_controls()
        self.reset_view()
        self.tick_auto()

    def build_controls(self):
        st = self.app.state
        b = self.ctl_body
        if st is None:
            return
        k = st.kind
        if k in ("free", "mirror"):
            self._mover(b, T("수신기 위치", "Receiver position"),
                        lambda d: self._adj("rx_x", d))
        if k == "box":
            self._water(b)
            self._mover(b, T("수신기 높이", "Receiver height"),
                        lambda d: self._adj("rx_gap", d))
        if k == "wtube":
            self._water(b)
            self._mover(b, T("송신기 깊이(밧줄)", "Emitter depth (rope)"),
                        lambda d: self._adj("em_y", -d))
            self._mover(b, T("수신기 높이", "Receiver height"),
                        lambda d: self._adj("rx_gap", d))
        if k == "atube":
            row = tk.Frame(b, bg=COL["panel"])
            row.pack(fill="x", padx=8, pady=2)
            tk.Label(row, text=T("금속관 교체", "Swap tube"), bg=COL["panel"],
                     fg=COL["text"], font=("DejaVu Sans", 9)).pack(side="left")
            for i, tb in enumerate(TUBES):
                self._btn(row, "%d" % int(tb["d"] * 1000),
                          lambda i=i: self.swap_tube(i)).pack(side="left", padx=2)
            self._mover(b, T("송신기 삽입 깊이", "Emitter insertion depth"),
                        lambda d: self._adj("em_z", d))
            self._mover(b, T("수신기 간격", "Receiver gap"),
                        lambda d: self._adj("rx_gap", d))

    def _mover(self, parent, label, cb):
        row = tk.Frame(parent, bg=COL["panel"])
        row.pack(fill="x", padx=8, pady=2)
        tk.Label(row, text=label, bg=COL["panel"], fg=COL["text"], width=17,
                 anchor="w", font=("DejaVu Sans", 9)).pack(side="left")
        for txt, d in (("−10", -0.010), ("−1", -0.001), ("+1", 0.001), ("+10", 0.010)):
            self._btn(row, txt, lambda d=d: cb(d), w=3).pack(side="left", padx=1)

    def _water(self, parent):
        row = tk.Frame(parent, bg=COL["panel"])
        row.pack(fill="x", padx=8, pady=2)
        tk.Label(row, text=T("물 붓기/덜기", "Pour / remove"), bg=COL["panel"],
                 fg=COL["text"], width=17, anchor="w",
                 font=("DejaVu Sans", 9)).pack(side="left")
        self._btn(row, T("주전자", "Jug"), lambda: self._pour(JUG_VOL)).pack(
            side="left", padx=1)
        self._btn(row, T("컵", "Cup"), lambda: self._pour(CUP_VOL)).pack(
            side="left", padx=1)
        self._btn(row, T("−컵", "−Cup"), lambda: self._pour(-CUP_VOL)).pack(
            side="left", padx=1)
        self._btn(row, T("비움", "Empty"), self._empty).pack(side="left", padx=1)

    # ----------------------------------------------------------------- actions
    def _adj(self, attr, d):
        st = self.app.state
        setattr(st, attr, getattr(st, attr) + d)
        st.clamp()
        self.redraw()

    def _pour(self, v):
        st = self.app.state
        if v > 0:
            st.pour(v)
            self.app.sim_time += 20.0
        else:
            st.scoop(-v)
            self.app.sim_time += 20.0
        self.redraw()

    def _empty(self):
        self.app.state.water_V = 0.0
        self.app.sim_time += 60.0
        self.redraw()

    def swap_tube(self, i):
        st = self.app.state
        st.tube_idx = i
        st.clamp()
        self.app.sim_time += 120.0
        self.reset_view()

    def measure(self):
        st = self.app.state
        if st is None:
            return
        p = st.true_power(self.app.phys)
        v = self.app.rx.sample(p)
        st.reading = v
        st.hist = self.app.rx.history
        self.app.sim_time += Receiver.PERIOD
        self.redraw()

    def tick_auto(self):
        if self._auto_job:
            try:
                self.frame.after_cancel(self._auto_job)
            except Exception:
                pass
            self._auto_job = None
        if self.auto.get() and self.app.state is not None:
            self.measure()
            self._auto_job = self.frame.after(1400, self.tick_auto)

    def record(self):
        st = self.app.state
        if st is None or st.reading is None:
            return
        items = st.ruler_items()
        v1 = st.ruler_read(items[0][1]) * 100.0 if items else 0.0
        v2 = st.ruler_read(items[1][1]) * 100.0 if len(items) > 1 else 0.0
        row = ("%.1f" % v1, "%.1f" % v2, "%.1f" % st.reading)
        self.rows.append(row)
        self.tree.insert("", "end", values=row)
        self.tree.yview_moveto(1.0)

    def del_row(self):
        sel = self.tree.selection()
        for s in sel:
            idx = self.tree.index(s)
            self.tree.delete(s)
            if 0 <= idx < len(self.rows):
                self.rows.pop(idx)

    def save_csv(self):
        if not self.rows:
            return
        fn = filedialog.asksaveasfilename(defaultextension=".csv",
                                          filetypes=[("CSV", "*.csv")])
        if not fn:
            return
        st = self.app.state
        items = st.ruler_items()
        h1 = items[0][0] if items else "x1"
        h2 = items[1][0] if len(items) > 1 else "x2"
        with open(fn, "w", encoding="utf-8") as fh:
            fh.write("# EuPhO 2019 experiment, rig=%s, seed=%d\n"
                     % (st.kind, self.app.truth.seed))
            fh.write("%s [cm],%s [cm],P [dBm]\n" % (h1, h2))
            for r in self.rows:
                fh.write("%s,%s,%s\n" % r)

    # ------------------------------------------------------------- interaction
    def handles(self):
        """[(name, world x, world y, tolerance px)] of draggable objects."""
        st = self.app.state
        if st is None:
            return []
        k = st.kind
        if k in ("free", "mirror"):
            return [("rx_x", st.rx_x, RX_H * 0.5, 40)]
        if k == "box":
            return [("rx_gap", 0.075, st.box_floor + st.box_h + st.rx_gap + RX_H * 0.45, 44)]
        if k == "wtube":
            return [("em_y", 0.0, st.wt_bottom + st.em_y, 30),
                    ("rx_gap", 0.0, st.wt_mouth + st.rx_gap + RX_H * 0.45, 40)]
        if k == "atube":
            return [("em_z", -st.em_z, st.at_axis_y, 30),
                    ("rx_gap", st.rx_gap + RX_W * 0.5, st.at_axis_y, 40)]
        return []

    def on_press(self, e):
        for name, wx, wy, tol in self.handles():
            sx, sy = self.scene.w2s(wx, wy)
            if abs(sx - e.x) < tol and abs(sy - e.y) < tol:
                self.drag = (name, e.x, e.y)
                return
        self.pan = (e.x, e.y, self.scene.ox, self.scene.oy)

    def on_move(self, e):
        st = self.app.state
        if self.drag and st is not None:
            name, x0, y0 = self.drag
            wx, wy = self.scene.s2w(e.x, e.y)
            if name == "rx_x":
                st.rx_x = wx
            elif name == "rx_gap" and st.kind == "box":
                st.rx_gap = wy - (st.box_floor + st.box_h) - RX_H * 0.45
            elif name == "rx_gap" and st.kind == "wtube":
                st.rx_gap = wy - st.wt_mouth - RX_H * 0.45
            elif name == "rx_gap" and st.kind == "atube":
                st.rx_gap = wx - RX_W * 0.5
            elif name == "em_y":
                st.em_y = wy - st.wt_bottom
            elif name == "em_z":
                st.em_z = -wx
            st.clamp()
            self.redraw()
        elif self.pan:
            x0, y0, ox, oy = self.pan
            self.scene.ox = ox + (e.x - x0)
            self.scene.oy = oy + (e.y - y0)
            self.redraw()

    def on_up(self):
        self.drag = None
        self.pan = None

    def on_wheel(self, e, direction=None, fine=False):
        d = direction if direction is not None else (1 if e.delta > 0 else -1)
        st = self.app.state
        step = (0.001 if fine else 0.005) * d
        for name, wx, wy, tol in self.handles():
            sx, sy = self.scene.w2s(wx, wy)
            if abs(sx - e.x) < tol and abs(sy - e.y) < tol:
                if name == "em_y":
                    st.em_y -= step
                else:
                    setattr(st, name, getattr(st, name) + step)
                st.clamp()
                self.redraw()
                return
        old = self.scene.ppm
        self.scene.ppm = min(max(old * (1.12 if d > 0 else 1 / 1.12), 90.0), 14000.0)
        wx, wy = (e.x - self.scene.ox) / old, (self.scene.oy - e.y) / old
        self.scene.ox = e.x - wx * self.scene.ppm
        self.scene.oy = e.y + wy * self.scene.ppm
        self.redraw()

    def reset_view(self):
        st = self.app.state
        W = max(self.cv.winfo_width(), 700)
        H = max(self.cv.winfo_height(), 520)
        if st is None:
            return
        k = st.kind
        if k in ("free", "mirror"):
            self.scene.ppm = min(W * 0.80 / 1.55, 900.0)
            self.scene.ox = W * 0.12
            self.scene.oy = H * 0.80
        elif k == "box":
            self.scene.ppm = min(W * 0.62 / 0.36, H * 0.60 / 0.30)
            self.scene.ox = W * 0.46
            self.scene.oy = H * 0.86
        elif k == "wtube":
            self.scene.ppm = min(H * 0.86 / 0.86, W * 0.5 / 0.35)
            self.scene.ox = W * 0.42
            self.scene.oy = H * 0.95
        else:
            self.scene.ppm = min(W * 0.80 / (st.tube["L"] + 0.30), 2600.0)
            self.scene.ox = W * 0.74
            self.scene.oy = H * 0.72
        self.redraw()

    # ----------------------------------------------------------------- drawing
    def redraw(self):
        st = self.app.state
        if st is None:
            self.cv.delete("all")
            return
        present = set(_norm(p) for p in self.app.assembly.placed)
        st.hist = self.app.rx.history
        self.scene.draw(self.cv, st.kind, st, present, labels=False)
        # hint markers on the draggable handles
        for name, wx, wy, tol in self.handles():
            sx, sy = self.scene.w2s(wx, wy)
            self.cv.create_oval(sx - 7, sy - 7, sx + 7, sy + 7,
                                outline=COL["accent"], dash=(3, 3))
        self.cv.create_text(12, 10, anchor="nw", fill=COL["dim"],
                            font=("DejaVu Sans", 9),
                            text=T("드래그: 부품 이동 / 빈 곳 드래그: 화면 이동 / "
                                   "휠: 확대·축소 (부품 위에서는 이동, Shift=미세)",
                                   "Drag a part to move it, drag empty space to pan, "
                                   "wheel to zoom (over a part: move it, Shift = fine)"))
        self.lbl_read.config(text="---" if st.reading is None else "%.1f" % st.reading)
        h = int(self.app.sim_time // 3600)
        m = int(self.app.sim_time % 3600 // 60)
        s = int(self.app.sim_time % 60)
        self.lbl_clock.config(
            text=T("경과 시간 %d:%02d:%02d  (시험 5시간)  ·  측정 %d회  ·  seed %d",
                   "elapsed %d:%02d:%02d  (5 h exam)  ·  %d readings  ·  seed %d")
            % (h, m, s, self.app.rx.count, self.app.truth.seed))
        txt = []
        for lab, val in st.ruler_items():
            txt.append("%-26s %6.1f cm" % (lab, st.ruler_read(val) * 100.0))
        self.lbl_ruler.config(text="\n".join(txt) if "H" in present else
                              T("자 H 가 배치되어 있지 않습니다.",
                                "Ruler H is not on the bench."))


# --------------------------------------------------------------------------- #
#  Public lab API -- exactly what a student can do and see.
#  (The verification harness is allowed to use *only* this class; it returns
#   display strings, never physical parameters.)
# --------------------------------------------------------------------------- #

class Lab(object):

    def __init__(self, seed=None):
        self.truth = Truth(seed)
        self.phys = Physics(self.truth)
        self.assembly = Assembly()
        self.rx = Receiver(self.truth)
        self.state = None
        self.sim_time = 0.0

    # -------------------------------------------------------------- assembling
    def place(self, *pids):
        for pid in pids:
            ok, msg = self.assembly.place(pid)
            if not ok:
                raise RuntimeError("cannot place %s: %s" % (pid, msg))
        return self.assembly.complete()

    def dismantle(self):
        self.assembly.clear()
        self.state = None

    def build(self, tube_idx=1):
        key = self.assembly.complete()
        if key is None:
            raise RuntimeError("assembly incomplete")
        self.state = RigState(key, self.truth, tube_idx)
        self.state.foam = "G" in self.assembly.placed
        self.state.clamp()
        return key

    def setup(self, kind, tube_idx=1):
        """Convenience: assemble a standard rig from the kit."""
        recipe = {
            "free":   ["A", "B", "H"],
            "mirror": ["Q", "F", "O", "A", "B", "H"],
            "box":    ["G", "G", "G", "G", "E", "F", "A", "I", "B", "H", "J", "K"],
            "wtube":  ["D", "O", "F", "I", "M", "N", "A", "B", "H", "J", "K"],
            "atube":  ["G", "G", "C%d" % (tube_idx + 1), "M", "N", "A", "B", "H"],
        }[kind]
        self.dismantle()
        self.place(*recipe)
        return self.build(tube_idx)

    # ---------------------------------------------------------------- controls
    def set_cm(self, name, value_cm):
        st = self.state
        setattr(st, name, value_cm / 100.0)
        st.clamp()

    def pour(self, vol_mL):
        self.state.pour(vol_mL * 1e-6)
        self.sim_time += 20.0

    def scoop(self, vol_mL):
        self.state.scoop(vol_mL * 1e-6)
        self.sim_time += 20.0

    def swap_tube(self, idx):
        self.state.tube_idx = idx
        self.state.clamp()
        self.sim_time += 120.0

    # ---------------------------------------------------------------- readings
    def read_receiver(self):
        """String shown on the receiver display, in dBm."""
        p = self.state.true_power(self.phys)
        v = self.rx.sample(p)
        self.state.reading = v
        self.sim_time += Receiver.PERIOD
        return "%.1f" % v

    def read_ruler(self):
        """Dict of {label: '12.3'} -- centimetre readings off the 1 mm scale."""
        out = {}
        for lab, val in self.state.ruler_items():
            out[lab] = "%.1f" % (self.state.ruler_read(val) * 100.0)
        return out

    def ruler_list(self):
        return [lab for lab, _ in self.state.ruler_items()]


# --------------------------------------------------------------------------- #
#  Application
# --------------------------------------------------------------------------- #

INTRO = lambda: T(
    "EuPhO 2019 실험 문제 — 라디오파의 전파\n\n"
    "과제 1. 수신기의 감도 (1점)\n"
    "과제 2. 물에서의 파장 (6점)\n"
    "과제 3. 물에서의 감쇠 계수 α (3점)\n"
    "과제 4a. 공기 도파관의 소멸 모드 µ (2점)\n"
    "과제 4b. µ 와 관 지름 d 의 관계 (5점)\n"
    "과제 5. 공기 중 파장과 물의 굴절률 (3점)\n\n"
    "조립 탭에서 부품을 끌어다 배치를 만들고, 실험대 탭에서 측정하세요.\n"
    "수신기는 15초마다 한 번 값을 읽습니다.",
    "EuPhO 2019 Experimental Problem — Propagation of radio waves\n\n"
    "Task 1. Sensitivity of the receiver (1p)\n"
    "Task 2. Wavelength in water (6p)\n"
    "Task 3. Attenuation coefficient α in water (3p)\n"
    "Task 4a. Decaying mode µ in an air-filled waveguide (2p)\n"
    "Task 4b. Dependence of µ on the tube diameter d (5p)\n"
    "Task 5. Wavelength in air and refractive index of water (3p)\n\n"
    "Build a set-up on the Assembly tab, then measure on the Bench tab.\n"
    "The receiver takes one reading every 15 s.")


class App(object):

    def __init__(self, root, seed=None):
        self.root = root
        self.lab = Lab(seed)
        self.truth = self.lab.truth
        self.phys = self.lab.phys
        self.assembly = self.lab.assembly
        self.rx = self.lab.rx
        self.state = None
        self.sim_time = 0.0

        root.title("EuPhO 2019 — %s  [seed %d]"
                   % (T("라디오파의 전파", "Propagation of radio waves"),
                      self.truth.seed))
        root.configure(bg=COL["bg"])
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TNotebook", background=COL["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=COL["panel"],
                        foreground=COL["text"], padding=(18, 7))
        style.map("TNotebook.Tab", background=[("selected", COL["panel2"])])
        style.configure("Treeview", background=COL["panel2"],
                        fieldbackground=COL["panel2"], foreground=COL["text"],
                        borderwidth=0)
        style.configure("Treeview.Heading", background=COL["panel"],
                        foreground=COL["dim"])

        self.nb = ttk.Notebook(root)
        self.nb.pack(fill="both", expand=True)
        self.tab_intro = self._intro_tab()
        self.tab_asm = AssemblyTab(self.nb, self)
        self.tab_bench = BenchTab(self.nb, self)
        self.nb.add(self.tab_intro, text=T(" 문제 ", " Problem "))
        self.nb.add(self.tab_asm.frame, text=T(" 조립 ", " Assembly "))
        self.nb.add(self.tab_bench.frame, text=T(" 실험대 ", " Bench "))
        self.nb.select(1)
        self.tab_asm.after_change()

    def _intro_tab(self):
        f = tk.Frame(self.nb, bg=COL["bg"])
        tk.Label(f, text=INTRO(), bg=COL["bg"], fg=COL["text"], justify="left",
                 font=("DejaVu Sans", 12), padx=28, pady=24).pack(anchor="nw")
        tk.Label(f, text=T(
            "장비: A 송신기 · B 수신기 · C 금속관(41/46/59/100 mm) · D 플라스틱관 · "
            "E 상자 · F 포일 · G 폼 · H 자 · I 양동이 · J 주전자 · K 컵 · L 휴지 · "
            "M 밧줄 · N 클립 · O 테이프 · P 고무줄 · Q 나무 막대",
            "Kit: A emitter · B receiver · C metal tubes (41/46/59/100 mm) · "
            "D plastic tube · E box · F foil · G foam · H ruler · I bucket · "
            "J jug · K cup · L tissues · M rope · N clip · O tape · P bands · "
            "Q wooden rod"),
            bg=COL["bg"], fg=COL["dim"], justify="left", wraplength=820,
            font=("DejaVu Sans", 10), padx=28).pack(anchor="nw")
        return f

    # ------------------------------------------------------------------ hooks
    def preview_state(self, key):
        st = RigState(key or "free", self.truth, 1)
        st.foam = "G" in self.assembly.placed
        if key == "box":
            st.water_V = BOX_W * BOX_D * 0.055
            st.rx_gap = 0.07
        elif key == "wtube":
            st.water_V = math.pi * (TUBE_D_ID / 2.0) ** 2 * 0.62
            st.em_y = 0.30
            st.rx_gap = 0.02
        elif key == "atube":
            st.em_z = 0.05
            st.rx_gap = 0.01
        st.clamp()
        st.reading = None
        st.hist = []
        return st

    def on_assembly_change(self, key):
        if key is None:
            self.state = None
            self.lab.state = None
            return
        if self.state is None or self.state.kind != key:
            self.state = RigState(key, self.truth, 1)
            self.state.foam = "G" in self.assembly.placed
            if key == "box":
                self.state.rx_gap = 0.070
            if key == "wtube":
                self.state.rx_gap = 0.015
                self.state.em_y = 0.30
            if key == "atube":
                self.state.em_z = 0.040
                self.state.rx_gap = 0.005
            self.state.clamp()
            self.lab.state = self.state
            self.rx.reset()

    def goto_bench(self):
        if self.state is None:
            return
        self.nb.select(2)
        self.tab_bench.enter()

    def goto_assembly(self):
        self.tab_bench.auto.set(0)
        self.tab_bench.tick_auto()
        self.nb.select(1)
        self.tab_asm.redraw()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    seed = None
    global LANG
    for a in argv:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
        elif a.startswith("--lang="):
            LANG = a.split("=", 1)[1].upper()
    if tk is None:
        print("Tkinter is not available.")
        return 1
    root = tk.Tk()
    root.geometry("1420x880")
    App(root, seed)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
