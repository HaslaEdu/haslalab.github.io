#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  International distributed Physics Olympiad  (IdPhO 2020, MIPT, online)
  Experimental Problem :  CRYSTALLOGRAPHY
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    A red laser (lambda = 630 nm) illuminates photographic slides carrying
    one- and two-dimensional artificial crystals; the Fraunhofer pattern is
    observed on graph paper about 1 m behind the slide and the spot
    intensities are read with a photodiode circuit and a multimeter.
    Only what a real instrument would show is displayed: the light on the
    screen, the multimeter digits, the tape measure and the millimetre paper.
    Lattice parameters, a/b, symmetries and structure factors are NEVER shown.
"""

import math
import random
import cmath
import argparse
import sys

# --------------------------------------------------------------------------
# 0.  bilingual wrapper
# --------------------------------------------------------------------------
LANG = "en"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


# --------------------------------------------------------------------------
# 1.  physical constants of the kit
# --------------------------------------------------------------------------
LAMBDA_UM = 0.630          # laser wavelength, micrometre
LAMBDA_MM = LAMBDA_UM * 1e-3

BEAM_FULL_MM = 1.20        # laser beam diameter, no pinhole
BEAM_PIN_MM = 0.26         # laser beam diameter behind the needle pinhole
FILM_TRANSMISSION = 0.105  # one layer of the neutral film
VCC = 2.95                 # compliance of the photodiode circuit (V)

GRID_PG = 12               # plane-group unit cell : 12 x 12 squares
PITCH_PG = 10.0            # micrometre  ->  a = 120 um
GRID_MR = 4                # molecular-replacement unit cell : 4 x 4
PITCH_MR = 10.0            # micrometre  ->  a = 40 um


# --------------------------------------------------------------------------
# 2.  small maths helpers
# --------------------------------------------------------------------------
def sinc(u):
    return 1.0 if abs(u) < 1e-14 else math.sin(u) / u


def bessel_j1(x):
    """J1(x) by power series / asymptotic form (enough for |x| < 30)."""
    ax = abs(x)
    if ax < 12.0:
        t = (x * x) / 4.0
        term = x / 2.0
        s = term
        for m in range(1, 40):
            term *= -t / (m * (m + 1.0))
            s += term
            if abs(term) < 1e-16 * (abs(s) + 1e-30):
                break
        return s
    z = 8.0 / ax
    y = z * z
    p = (1.0 + 0.183105e-2 * y - 0.3516396496e-4 * y * y
         + 0.2457520174e-5 * y ** 3 - 0.240337019e-6 * y ** 4)
    q = (0.04687499995 - 0.2002690873e-3 * y + 0.8449199096e-5 * y * y
         - 0.88228987e-6 * y ** 3 + 0.105787412e-6 * y ** 4)
    xx = ax - 2.356194491
    r = math.sqrt(0.636619772 / ax) * (math.cos(xx) * p - z * math.sin(xx) * q)
    return r if x > 0 else -r


def jinc(x):
    """2*J1(x)/x  (Airy/window form factor), jinc(0) = 1."""
    return 1.0 if abs(x) < 1e-12 else 2.0 * bessel_j1(x) / x


# --------------------------------------------------------------------------
# 3.  unit cells of every slide
# --------------------------------------------------------------------------
# ---- plane-group cells (see design notes in README) ----------------------
PG_CELLS = {
    "K": [(2, 3), (2, 4), (2, 5), (2, 6), (2, 7), (2, 8), (3, 2), (3, 5),
          (3, 6), (3, 9), (4, 2), (4, 9), (5, 2), (5, 3), (5, 8), (5, 9),
          (6, 2), (6, 3), (6, 8), (6, 9), (7, 2), (7, 9), (8, 2), (8, 5),
          (8, 6), (8, 9), (9, 3), (9, 4), (9, 5), (9, 6), (9, 7), (9, 8)],
    "L": [(4, 4), (4, 5), (4, 6), (5, 6)],
    "M": [(1, 4), (1, 5), (1, 6), (2, 6), (9, 6), (10, 4), (10, 5), (10, 6)],
    "N": [(2, 5), (2, 6), (2, 7), (3, 7), (4, 2), (4, 3), (5, 2), (5, 9),
          (6, 2), (6, 9), (7, 8), (7, 9), (8, 4), (9, 4), (9, 5), (9, 6)],
    "P": [(3, 7), (4, 7), (4, 8), (4, 9), (7, 2), (7, 3), (7, 4), (8, 4)],
    "Q": [(1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (2, 3), (2, 8),
          (9, 3), (9, 8), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7),
          (10, 8)],
    "R": [(0, 3), (0, 4), (0, 7), (0, 8), (1, 3), (1, 8), (2, 3), (2, 8),
          (3, 0), (3, 1), (3, 2), (3, 9), (3, 10), (3, 11), (4, 0), (4, 11),
          (7, 0), (7, 11), (8, 0), (8, 1), (8, 2), (8, 9), (8, 10), (8, 11),
          (9, 3), (9, 8), (10, 3), (10, 8), (11, 3), (11, 4), (11, 7),
          (11, 8)],
    "S": [(0, 11), (1, 9), (1, 10), (1, 11), (4, 3), (4, 4), (4, 5), (5, 5),
          (6, 6), (7, 6), (7, 7), (7, 8), (10, 0), (10, 1), (10, 2), (11, 0)],
    "T": [(0, 3), (1, 1), (1, 2), (1, 3), (1, 10), (2, 4), (2, 5), (2, 10),
          (3, 4), (3, 10), (3, 11), (4, 4), (4, 7), (4, 8), (4, 9), (5, 9),
          (6, 2), (7, 2), (7, 3), (7, 4), (7, 7), (8, 0), (8, 1), (8, 7),
          (9, 1), (9, 6), (9, 7), (10, 1), (10, 8), (10, 9), (10, 10),
          (11, 8)],
}
PG_GROUP_NAME = {"K": "p4m", "L": "p1", "M": "pm", "N": "p4", "P": "p2",
                 "Q": "pmm", "R": "p4m", "S": "pgg", "T": "p4g"}

# which physical slide carries which unit cell
PG_SLIDE_CELL = {"PG1": "L", "PG2": "M", "PG3": "P", "PG4": "R", "PG5": "N",
                 "PG6": "T", "PG7": "Q", "PG8": "K", "PG9": "S"}

# ---- molecular replacement cells ----------------------------------------
MR_CELLS = {
    "MR0": [(0, 0), (1, 1), (2, 1), (1, 2), (3, 2)],
    "MR1": [(0, 0), (1, 1), (2, 1), (1, 2), (3, 2), (2, 3)],           # = X
    "MR2": [(0, 0), (3, 0), (1, 1), (2, 1), (0, 2), (1, 2), (3, 2)],
}
MR_CANDIDATES = {                       # figure 12 of the problem sheet
    "W": [(0, 0), (1, 1), (2, 1), (1, 2), (2, 2)],
    "X": [(0, 0), (1, 1), (2, 1), (1, 2), (3, 2), (2, 3)],
    "Y": [(0, 0), (1, 1), (2, 1), (1, 2)],
    "Z": [(0, 0), (3, 0), (1, 1), (2, 1), (1, 2), (0, 3)],
}

# reflection phases of MR0 printed in figure 13 of the problem sheet
MR0_PHASE_TABLE = {
    (-2, 2): 3.142, (-1, 2): 0.4636, (0, 2): 0.0, (1, 2): -0.4636, (2, 2): 3.142,
    (-2, 1): 0.0, (-1, 1): -0.4636, (0, 1): 2.034, (1, 1): -1.571, (2, 1): 0.0,
    (-2, 0): 3.142, (-1, 0): -1.571, (0, 0): 0.0, (1, 0): 1.571, (2, 0): 3.142,
    (-2, -1): 0.0, (-1, -1): 1.571, (0, -1): -2.034, (1, -1): 0.4636, (2, -1): 0.0,
    (-2, -2): 3.142, (-1, -2): 0.4636, (0, -2): 0.0, (1, -2): -0.4636, (2, -2): 3.142,
}


class Sample(object):
    """One slide sample.  Everything observable follows from this object."""

    def __init__(self, name, kind, sheet, label=None):
        self.name = name
        self.kind = kind            # '1d' | '2d' | 'quasi'
        self.sheet = sheet          # which transparency sheet carries it
        self.label = label or name
        # 1-D
        self.a = None
        self.b = None
        # 2-D
        self.a1 = None
        self.a2 = None
        self.rects = []             # (x0, y0, w, h) in micrometre
        self.rect_mode = "opaque"   # 'opaque' -> rho = 1 - sum ; 'transparent'
        self._refl = None

    # ------------------------------------------------------------------
    @staticmethod
    def grating(name, sheet, a, b):
        s = Sample(name, "1d", sheet)
        s.a, s.b = a, b
        return s

    @staticmethod
    def crystal2d(name, sheet, a1, a2, rects, mode="opaque"):
        s = Sample(name, "2d", sheet)
        s.a1, s.a2 = a1, a2
        s.rects = list(rects)
        s.rect_mode = mode
        return s

    @staticmethod
    def from_grid(name, sheet, grid, pitch, cells, mode):
        a = grid * pitch
        rects = [(cx * pitch, cy * pitch, pitch, pitch) for (cx, cy) in cells]
        return Sample.crystal2d(name, sheet, (a, 0.0), (0.0, a), rects, mode)

    @staticmethod
    def quasicrystal(name, sheet, a_eff=25.0, window=3.2):
        s = Sample(name, "quasi", sheet)
        s.a = a_eff
        s.window = window
        return s

    # ------------------------------------------------------------------
    @property
    def cell_area(self):
        if self.kind == "1d":
            return self.a
        if self.kind == "2d":
            return abs(self.a1[0] * self.a2[1] - self.a1[1] * self.a2[0])
        return 1.0

    def reciprocal(self):
        x1, y1 = self.a1
        x2, y2 = self.a2
        A = x1 * y2 - y1 * x2
        f = 2.0 * math.pi / A
        return (f * y2, -f * x2), (-f * y1, f * x1)

    # ------------------------------------------------------------------
    def _f_rect(self, r, qx, qy):
        x0, y0, w, h = r
        xc, yc = x0 + w / 2.0, y0 + h / 2.0
        amp = w * h * sinc(qx * w / 2.0) * sinc(qy * h / 2.0)
        return amp * cmath.exp(1j * (qx * xc + qy * yc))

    def F2d(self, h, k):
        """complex structure factor of reflection (h, k) [um^2]."""
        (b1x, b1y), (b2x, b2y) = self.reciprocal()
        qx = h * b1x + k * b2x
        qy = h * b1y + k * b2y
        if h == 0 and k == 0:
            tot = sum(r[2] * r[3] for r in self.rects)
            if self.rect_mode == "opaque":
                return complex(self.cell_area - tot, 0.0)
            return complex(tot, 0.0)
        s = 0j
        for r in self.rects:
            s += self._f_rect(r, qx, qy)
        return -s if self.rect_mode == "opaque" else s

    def F1d(self, h):
        q = 2.0 * math.pi * h / self.a
        return self.b * sinc(q * self.b / 2.0) * cmath.exp(1j * q * self.b / 2.0)

    # ------------------------------------------------------------------
    def reflections(self, s_max=0.30, rel_cut=1e-7):
        """List of (h, k, sx, sy, p_rel).

        sx, sy are direction cosines of the diffracted beam,
        p_rel = |F/A_cell|^2 = fraction of the incident power in this spot.
        """
        if self._refl is not None:
            return self._refl
        out = []
        if self.kind == "1d":
            hmax = int(s_max * self.a / LAMBDA_UM) + 1
            for h in range(-hmax, hmax + 1):
                sx = h * LAMBDA_UM / self.a
                if abs(sx) > s_max:
                    continue
                p = abs(self.F1d(h) / self.a) ** 2
                if p > rel_cut:
                    out.append((h, 0, sx, 0.0, p))
        elif self.kind == "2d":
            (b1x, b1y), (b2x, b2y) = self.reciprocal()
            A = self.cell_area
            lim = 2 * int(s_max * 2.0 * math.pi /
                          (LAMBDA_UM * min(math.hypot(b1x, b1y),
                                           math.hypot(b2x, b2y)))) + 2
            for h in range(-lim, lim + 1):
                for k in range(-lim, lim + 1):
                    qx = h * b1x + k * b2x
                    qy = h * b1y + k * b2y
                    sx = qx * LAMBDA_UM / (2.0 * math.pi)
                    sy = qy * LAMBDA_UM / (2.0 * math.pi)
                    if math.hypot(sx, sy) > s_max:
                        continue
                    p = abs(self.F2d(h, k) / A) ** 2
                    if p > rel_cut:
                        out.append((h, k, sx, sy, p))
        else:                                    # quasicrystal
            g = 2.0 * math.pi / self.a
            par = [(g * math.cos(2 * math.pi * i / 5.0),
                    g * math.sin(2 * math.pi * i / 5.0)) for i in range(5)]
            per = [(math.cos(4 * math.pi * i / 5.0),
                    math.sin(4 * math.pi * i / 5.0)) for i in range(5)]
            seen = {}
            R = 2
            rng = range(-R, R + 1)
            for n0 in rng:
                for n1 in rng:
                    for n2 in rng:
                        for n3 in rng:
                            for n4 in rng:
                                n = (n0, n1, n2, n3, n4)
                                qx = sum(n[i] * par[i][0] for i in range(5))
                                qy = sum(n[i] * par[i][1] for i in range(5))
                                sx = qx * LAMBDA_UM / (2.0 * math.pi)
                                sy = qy * LAMBDA_UM / (2.0 * math.pi)
                                if math.hypot(sx, sy) > s_max:
                                    continue
                                px = sum(n[i] * per[i][0] for i in range(5))
                                py = sum(n[i] * per[i][1] for i in range(5))
                                amp = jinc(self.window * math.hypot(px, py))
                                p = 0.09 * amp * amp
                                key = (round(sx, 7), round(sy, 7))
                                if p > seen.get(key, (0.0, 0, 0))[0]:
                                    seen[key] = (p, n0, n1)
            for (sx, sy), (p, n0, n1) in seen.items():
                if p > 1.2e-3:
                    out.append((n0, n1, sx, sy, p))
        self._refl = out
        return out


# --------------------------------------------------------------------------
# 4.  the four transparency sheets
# --------------------------------------------------------------------------
def build_samples():
    S = {}

    # ---- sheet "Diffraction grating" : 1-D crystals ---------------------
    for nm, a, b in [("DG1", 20.0, 10.0), ("DG2", 50.0, 12.5),
                     ("DG3", 80.0, 10.0), ("DG4", 80.0, 20.0),
                     ("DG5", 80.0, 40.0)]:
        S[nm] = Sample.grating(nm, "DG", a, b)

    # ---- sheet "Unit cell" : simple 2-D crystals -------------------------
    #  figure 6 :  A(a=20, one atom b=10)   B(a=30, one atom b=10)
    #              C(a=30, atoms b=10 and b'=15)   D(a=20, two atoms b=10,
    #              the second one shifted by (a/2, a/2))
    S["UC1"] = Sample.crystal2d("UC1", "UC", (30.0, 0.0), (0.0, 30.0),
                                [(0, 0, 10, 10)])                      # B
    S["UC2"] = Sample.crystal2d("UC2", "UC", (20.0, 0.0), (0.0, 20.0),
                                [(0, 0, 10, 10)])                      # A
    S["UC3"] = Sample.crystal2d("UC3", "UC", (20.0, 0.0), (0.0, 20.0),
                                [(0, 0, 10, 10), (10, 10, 10, 10)])    # D
    S["UC4"] = Sample.crystal2d("UC4", "UC", (30.0, 0.0), (0.0, 30.0),
                                [(0, 0, 10, 10), (13, 14, 15, 15)])    # C
    # ---- oblique / rectangular lattices ---------------------------------
    S["UC5"] = Sample.crystal2d("UC5", "UC", (20.0, 0.0), (0.0, 40.0),
                                [(0, 0, 10, 10)])
    S["UC6"] = Sample.crystal2d("UC6", "UC", (30.0, 20.0), (20.0, -10.0),
                                [(0, 0, 10, 10)])
    S["UC7"] = Sample.crystal2d("UC7", "UC", (40.0, 0.0), (20.0, 30.0),
                                [(0, 0, 10, 10)])
    # ---- five-fold quasicrystal ----------------------------------------
    S["UC8"] = Sample.quasicrystal("UC8", "UC")

    # ---- sheet "Plane group" -------------------------------------------
    for slide, cell in PG_SLIDE_CELL.items():
        S[slide] = Sample.from_grid(slide, "PG", GRID_PG, PITCH_PG,
                                    PG_CELLS[cell], "opaque")

    # ---- sheet "Molecular replacement" ---------------------------------
    for slide, cells in MR_CELLS.items():
        S[slide] = Sample.from_grid(slide, "MR", GRID_MR, PITCH_MR,
                                    cells, "transparent")
    return S


SAMPLES = build_samples()

SHEETS = {
    "DG": ("Diffraction grating", ["DG1", "DG2", "DG3", "DG4", "DG5"]),
    "UC": ("Unit cell", ["UC1", "UC2", "UC3", "UC4",
                         "UC5", "UC6", "UC7", "UC8"]),
    "PG": ("Plane group", ["PG%d" % i for i in range(1, 10)]),
    "MR": ("Molecular replacement", ["MR0", "MR1", "MR2"]),
}


# --------------------------------------------------------------------------
# 5.  hidden, per-session randomised instrument constants
# --------------------------------------------------------------------------
class Truth(object):
    """Everything the student cannot read off directly.

    Only *instrumental* quantities are randomised - the crystals themselves
    are fixed physical objects, exactly as in the real problem.
    """

    def __init__(self, seed=None):
        self.seed = seed if seed is not None else random.randrange(1, 10 ** 9)
        rng = random.Random(self.seed)
        self.rng = rng
        # photodiode / amplifier
        self.gain10k = 53.24 * rng.uniform(0.86, 1.16)     # V per unit p_rel
        self.pd_diameter = rng.uniform(2.7, 3.4)           # mm
        self.v_background = rng.uniform(0.0018, 0.0062)    # V, stray + dark
        self.noise_rel = rng.uniform(0.004, 0.009)
        self.noise_abs = rng.uniform(0.00018, 0.00042)     # V
        # laser
        self.beam_full = BEAM_FULL_MM * rng.uniform(0.9, 1.12)
        self.beam_pin = BEAM_PIN_MM * rng.uniform(0.85, 1.2)
        self.power = rng.uniform(0.88, 1.12)
        # alignment: the primary beam does not hit an exact mm crossing
        self.centre_dx = rng.uniform(-3.4, 3.4)            # mm on the screen
        self.centre_dy = rng.uniform(-3.4, 3.4)
        # film transmission
        self.film_t = FILM_TRANSMISSION * rng.uniform(0.85, 1.18)
        # tape measure: a real tape hooks on the holder frame
        self.tape_bias = rng.uniform(-0.8, 0.8)            # mm


# --------------------------------------------------------------------------
# 6.  the apparatus
# --------------------------------------------------------------------------
ASSEMBLY_SLOTS = ["tablet", "laser_stand", "laser", "holder", "screen",
                  "detector"]

LEADS = ["BAT+", "BAT-", "PD_RED", "PD_BLK", "R_A", "R_B", "MM_RED", "MM_BLK"]


class Rig(object):
    """Public API of the apparatus.  The GUI and the verification harness
    are only ever allowed to touch this object."""

    def __init__(self, truth=None):
        self.truth = truth or Truth()

        # ---- assembly state --------------------------------------------
        self.placed = {k: False for k in ASSEMBLY_SLOTS}
        self.holder_assembled = False       # needs the screwdriver
        self.screen_assembled = False       # cardboard + graph paper + clips
        self.battery_block = False          # battery in its holder
        self.laser_clipped = False          # big clip keeps the button down
        self.pinhole_made = False           # masking tape + needle
        self.film_in_clip = False           # film mounted in a big clip

        # ---- detector circuit ------------------------------------------
        self.connectors = [set(), set(), set(), set()]
        self.resistor = "10k"               # '10k' | '200k'
        self.mm_dial = "OFF"                # 'OFF' | 'DCV200m' | 'DCV2' |
                                            # 'DCV20' | 'OHM' | 'ACV'
        # ---- optics ----------------------------------------------------
        self.laser_on = False
        self.sheet_in_holder = None         # 'DG' | 'UC' | 'PG' | 'MR'
        self.sample = None                  # sample name
        self.slide_flipped = False
        self.n_films = 0
        self.use_pinhole = False
        self.L_mm = 1000.0                  # slide -> screen distance
        self.d_laser_mm = 120.0             # laser -> slide distance
        self.room_light = True
        self.screen_w = 297.0               # A4 millimetre paper
        self.screen_h = 210.0

        # ---- detector position (mm on the screen, screen coordinates) ---
        self.pd_x = 0.0
        self.pd_y = 0.0

    # ==================================================================
    #  assembly
    # ==================================================================
    def prerequisites(self, slot):
        if slot == "tablet":
            return []
        if slot == "laser_stand":
            return ["tablet"]
        if slot == "laser":
            return ["tablet", "laser_stand"]
        if slot == "holder":
            return ["tablet"]
        if slot == "screen":
            return ["tablet"]
        if slot == "detector":
            return ["tablet"]
        return []

    def can_place(self, slot):
        for p in self.prerequisites(slot):
            if not self.placed[p]:
                return False, T("먼저 %s을(를) 놓아야 합니다." % SLOT_KO[p],
                                "place the %s first" % p)
        if slot == "holder" and not self.holder_assembled:
            return False, T("슬라이드 홀더를 먼저 조립하십시오 (드라이버).",
                            "assemble the slide holder first (screwdriver)")
        if slot == "screen" and not self.screen_assembled:
            return False, T("판지에 모눈종이를 클립으로 고정하십시오.",
                            "clip the graph paper onto the cardboard")
        if slot == "detector" and not self.battery_block:
            return False, T("배터리를 홀더에 넣어 전지 블록을 만드십시오.",
                            "put the battery into its holder")
        return True, ""

    def place(self, slot):
        ok, why = self.can_place(slot)
        if ok:
            self.placed[slot] = True
        return ok, why

    def remove(self, slot):
        self.placed[slot] = False
        if slot == "laser_stand":
            self.placed["laser"] = False
        if slot == "laser":
            self.laser_clipped = False
            self.laser_on = False
        if slot == "holder":
            self.sheet_in_holder = None
            self.sample = None
        if slot == "tablet":
            for k in ASSEMBLY_SLOTS:
                self.placed[k] = False
            self.laser_on = False

    # ==================================================================
    #  detector circuit
    # ==================================================================
    def circuit_state(self):
        """'ok' | 'reversed' | 'open' | 'short' - what the wiring does."""
        nodes = [c for c in self.connectors if c]
        if not self.placed["detector"]:
            return "open"

        def node_of(lead):
            for i, c in enumerate(self.connectors):
                if lead in c:
                    return i
            return None

        n = {l: node_of(l) for l in LEADS}
        if any(v is None for v in n.values()):
            return "open"
        # voltmeter must sit across the resistor
        if not (n["MM_RED"] == n["R_A"] and n["MM_BLK"] == n["R_B"]) and \
           not (n["MM_RED"] == n["R_B"] and n["MM_BLK"] == n["R_A"]):
            return "open"
        if n["R_A"] == n["R_B"]:
            return "short"
        # series loop battery - diode - resistor
        if n["BAT+"] == n["PD_RED"] and n["PD_BLK"] in (n["R_A"], n["R_B"]) \
                and n["BAT-"] in (n["R_A"], n["R_B"]) \
                and n["PD_BLK"] != n["BAT-"]:
            return "ok" if n["MM_RED"] == n["PD_BLK"] else "ok_swapped"
        if n["BAT-"] == n["PD_RED"] and n["PD_BLK"] in (n["R_A"], n["R_B"]) \
                and n["BAT+"] in (n["R_A"], n["R_B"]) \
                and n["PD_BLK"] != n["BAT+"]:
            return "reversed"
        return "open"

    def autowire(self):
        """Wire the circuit exactly as figure 17 of the problem sheet."""
        self.connectors = [{"BAT+", "PD_RED"},
                           {"PD_BLK", "R_A", "MM_RED"},
                           {"R_B", "BAT-", "MM_BLK"},
                           set()]

    # ==================================================================
    #  optics
    # ==================================================================
    def beam_diameter(self):
        return self.truth.beam_pin if (self.use_pinhole and self.pinhole_made) \
            else self.truth.beam_full

    def spot_sigma_mm(self):
        """1-sigma radius of a diffraction spot on the screen."""
        w = self.beam_diameter()
        return max(0.10, 0.45 * LAMBDA_MM * self.L_mm / w)

    def beam_ok(self):
        return (self.laser_on and self.placed["laser"] and self.laser_clipped
                and self.placed["screen"])

    def transmission(self):
        t = self.truth.power
        if self.n_films:
            t *= self.truth.film_t ** self.n_films
        if self.use_pinhole and self.pinhole_made:
            w = self.truth.beam_pin / self.truth.beam_full
            t *= w * w
        return t

    def spots(self):
        """[(x_mm, y_mm, power)] of every diffraction spot on the screen."""
        if not self.beam_ok():
            return []
        if self.sample is None or not self.placed["holder"]:
            # bare beam, no slide
            return [(self.truth.centre_dx, self.truth.centre_dy,
                     self.transmission())]
        smp = SAMPLES[self.sample]
        t = self.transmission()
        out = []
        for (h, k, sx, sy, p) in smp.reflections():
            if self.slide_flipped:
                sx = -sx
            s2 = sx * sx + sy * sy
            if s2 >= 0.85:
                continue
            f = self.L_mm / math.sqrt(1.0 - s2)
            x = sx * f + self.truth.centre_dx
            y = sy * f + self.truth.centre_dy
            if abs(x) > self.screen_w / 2.0 + 2.0 or \
               abs(y) > self.screen_h / 2.0 + 2.0:
                continue                       # misses the millimetre paper
            out.append((x, y, p * t))
        return out

    # ==================================================================
    #  instruments
    # ==================================================================
    def observe_screen(self, x0, y0, x1, y1, nx, ny, exposure=1.0):
        """What the eye (or the camera) sees: a brightness raster.

        Each output pixel is the *irradiance averaged over the pixel area*
        (exactly what a camera sensor element records), scaled by the
        exposure and clipped at 1.0 (saturated white-pink laser core).
        Rows run from y1 (top) downwards, columns from x0 (left).
        """
        sig = self.spot_sigma_mm()
        rt2 = sig * math.sqrt(2.0)
        dx = (x1 - x0) / float(nx)
        dy = (y1 - y0) / float(ny)
        rows = [[0.0] * nx for _ in range(ny)]
        ref = 30.0 * exposure / (dx * dy)
        for (sx, sy, p) in self.spots():
            i0 = int(math.floor((sx - 4.5 * sig - x0) / dx))
            i1 = int(math.ceil((sx + 4.5 * sig - x0) / dx))
            j0 = int(math.floor((y1 - sy - 4.5 * sig) / dy))
            j1 = int(math.ceil((y1 - sy + 4.5 * sig) / dy))
            i0, i1 = max(0, i0), min(nx - 1, i1)
            j0, j1 = max(0, j0), min(ny - 1, j1)
            if i0 > i1 or j0 > j1:
                continue
            fx = []
            for i in range(i0, i1 + 1):
                xa = x0 + i * dx
                fx.append(0.5 * (math.erf((xa + dx - sx) / rt2)
                                 - math.erf((xa - sx) / rt2)))
            amp = p * ref
            for j in range(j0, j1 + 1):
                yb = y1 - (j + 1) * dy
                fy = 0.5 * (math.erf((yb + dy - sy) / rt2)
                            - math.erf((yb - sy) / rt2))
                if fy <= 0.0:
                    continue
                r = rows[j]
                for n, i in enumerate(range(i0, i1 + 1)):
                    r[i] += amp * fx[n] * fy
        for r in rows:
            for i in range(nx):
                if r[i] > 1.0:
                    r[i] = 1.0
        return rows

    def photodiode_voltage(self):
        """Exact (noise-free) voltage across the resistor."""
        st = self.circuit_state()
        if st in ("open", "short"):
            return None
        if not self.placed["detector"]:
            return None
        gain = self.truth.gain10k * (20.0 if self.resistor == "200k" else 1.0)
        v = self.truth.v_background
        if st in ("ok", "ok_swapped"):
            sig = self.spot_sigma_mm()
            Rpd = self.truth.pd_diameter / 2.0
            tot = 0.0
            for (sx, sy, p) in self.spots():
                d = math.hypot(sx - self.pd_x, sy - self.pd_y)
                if d > Rpd + 6.0 * sig:
                    continue
                frac = 0.5 * (1.0 - math.erf((d - Rpd) / (sig * math.sqrt(2.0))))
                tot += p * frac
            v += gain * tot
        return min(v, VCC)

    def multimeter(self):
        """The string shown on the multimeter display."""
        if self.mm_dial == "OFF":
            return ""
        if self.mm_dial == "OHM":
            return "  0L "
        if self.mm_dial == "ACV":
            return " 000.0"
        v = self.photodiode_voltage()
        if v is None:
            return "  0.0 "
        tr = self.truth
        v = v * (1.0 + tr.rng.gauss(0.0, tr.noise_rel)) \
            + tr.rng.gauss(0.0, tr.noise_abs)
        v = max(v, 0.0)
        if self.circuit_state() == "ok_swapped":
            v = -v
        if self.mm_dial == "DCV200m":
            if abs(v) > 0.1999:
                return "   1  "
            return "%6.1f" % (v * 1000.0)
        if self.mm_dial == "DCV2":
            if abs(v) > 1.999:
                return "   1  "
            return "%6.3f" % v
        if self.mm_dial == "DCV20":
            if abs(v) > 19.99:
                return "   1  "
            return "%6.2f" % v
        return ""

    def multimeter_value(self):
        """Numeric reading in volt, or None if out of range / no reading."""
        s = self.multimeter().strip()
        if s in ("", "1", "0L", "000.0"):
            return None
        try:
            x = float(s)
        except ValueError:
            return None
        return x * 1e-3 if self.mm_dial == "DCV200m" else x

    def tape_measure(self):
        """Slide -> screen distance as read on the tape, millimetre."""
        return round(self.L_mm + self.truth.tape_bias)

    # ==================================================================
    #  the slide sheets
    # ==================================================================
    def insert_sheet(self, sheet):
        if not self.placed["holder"]:
            return False, T("슬라이드 홀더가 놓여 있지 않습니다.",
                            "the slide holder is not in place")
        self.sheet_in_holder = sheet
        self.sample = None
        return True, ""

    def select_sample(self, name):
        if self.sheet_in_holder is None:
            return False, T("먼저 슬라이드를 홀더에 넣으십시오.",
                            "insert a slide into the holder first")
        if SAMPLES[name].sheet != self.sheet_in_holder:
            return False, T("그 시료는 다른 슬라이드에 있습니다.",
                            "that sample is on another slide")
        self.sample = name
        return True, ""


SLOT_KO = {"tablet": "태블릿", "laser_stand": "레이저 받침대",
           "laser": "레이저", "holder": "슬라이드 홀더",
           "screen": "스크린", "detector": "세기 검출기"}
SLOT_EN = {"tablet": "tablet", "laser_stand": "laser stand", "laser": "laser",
           "holder": "slide holder", "screen": "screen",
           "detector": "intensity detector"}


# ==========================================================================
# 7.  graphical user interface
# ==========================================================================
try:
    import tkinter as tk
    from tkinter import ttk
except Exception:                                     # pragma: no cover
    tk = None

BG = "#eceff2"
PANEL = "#f7f8fa"
INK = "#1d2530"
ACCENT = "#b8321f"


# --------------------------------------------------------------------------
#  vector drawings of the twenty-one items of the kit (figure 14)
# --------------------------------------------------------------------------
def _r(c, x, y, w, h, fill, out="#333", wd=1, tags=()):
    return c.create_rectangle(x, y, x + w, y + h, fill=fill, outline=out,
                              width=wd, tags=tags)


def _o(c, x, y, w, h, fill, out="#333", wd=1, tags=()):
    return c.create_oval(x, y, x + w, y + h, fill=fill, outline=out,
                         width=wd, tags=tags)


def _l(c, pts, fill="#333", wd=2, tags=()):
    return c.create_line(*pts, fill=fill, width=wd, tags=tags)


def icon_multimeter(c, x, y, s, tg):
    _r(c, x, y, 46 * s, 74 * s, "#1f5b3a", "#0d2b1b", 2, tg)
    _r(c, x + 5 * s, y + 6 * s, 36 * s, 20 * s, "#cfd8c8", "#222", 1, tg)
    c.create_text(x + 23 * s, y + 16 * s, text="0.000", font=("Courier", int(8 * s)),
                  fill="#12301f", tags=tg)
    _o(c, x + 12 * s, y + 32 * s, 22 * s, 22 * s, "#e8e8e8", "#222", 1, tg)
    _l(c, [x + 23 * s, y + 43 * s, x + 23 * s, y + 34 * s], "#b02", 2, tg)
    _r(c, x + 10 * s, y + 60 * s, 8 * s, 8 * s, "#111", "#000", 1, tg)
    _r(c, x + 28 * s, y + 60 * s, 8 * s, 8 * s, "#111", "#000", 1, tg)
    _l(c, [x + 14 * s, y + 68 * s, x + 6 * s, y + 78 * s, x - 6 * s, y + 74 * s],
       "#111", 2, tg)
    _l(c, [x + 32 * s, y + 68 * s, x + 44 * s, y + 80 * s, x + 56 * s, y + 74 * s],
       "#c22", 2, tg)


def icon_photodiode(c, x, y, s, tg):
    _r(c, x, y, 34 * s, 22 * s, "#1f7a3c", "#0c3a1c", 1, tg)
    _o(c, x + 6 * s, y + 4 * s, 13 * s, 13 * s, "#20242c", "#000", 1, tg)
    _o(c, x + 9 * s, y + 7 * s, 6 * s, 6 * s, "#5a6a80", "", 0, tg)
    _r(c, x + 22 * s, y + 5 * s, 9 * s, 12 * s, "#8a8f96", "#555", 1, tg)
    _l(c, [x + 4 * s, y + 22 * s, x - 6 * s, y + 34 * s], "#c22", 2, tg)
    _l(c, [x + 14 * s, y + 22 * s, x + 8 * s, y + 34 * s], "#222", 2, tg)


def icon_battery(c, x, y, s, tg):
    _r(c, x, y, 42 * s, 14 * s, "#2b3d7a", "#101a3a", 1, tg)
    _r(c, x + 30 * s, y + 2 * s, 12 * s, 10 * s, "#c9ccd2", "#555", 1, tg)
    _r(c, x + 42 * s, y + 5 * s, 3 * s, 4 * s, "#c9ccd2", "#555", 1, tg)
    c.create_text(x + 15 * s, y + 7 * s, text="AA", fill="#dfe4ef",
                  font=("Helvetica", int(6 * s)), tags=tg)


def icon_resistor(c, x, y, s, tg):
    _l(c, [x, y + 7 * s, x + 34 * s, y + 7 * s], "#8a8a8a", 2, tg)
    _r(c, x + 8 * s, y + 2 * s, 18 * s, 10 * s, "#d8c39a", "#8a7550", 1, tg)
    for i, col in enumerate(("#8a4b1e", "#111", "#e2a10b")):
        _r(c, x + (11 + 4 * i) * s, y + 2 * s, 2.2 * s, 10 * s, col, "", 0, tg)


def icon_connector(c, x, y, s, tg):
    _r(c, x, y + 6 * s, 30 * s, 14 * s, "#cfe4ef", "#7a99a8", 1, tg)
    for i in range(3):
        _r(c, x + (2 + 9 * i) * s, y, 7 * s, 8 * s, "#e8801a", "#a3510a", 1, tg)


def icon_batholder(c, x, y, s, tg):
    _r(c, x, y, 34 * s, 18 * s, "#20242c", "#000", 1, tg)
    _l(c, [x + 34 * s, y + 5 * s, x + 46 * s, y + 2 * s], "#c22", 2, tg)
    _l(c, [x + 34 * s, y + 12 * s, x + 46 * s, y + 15 * s], "#222", 2, tg)


def icon_laser(c, x, y, s, tg):
    _r(c, x, y + 3 * s, 52 * s, 13 * s, "#22262c", "#000", 1, tg)
    _r(c, x + 34 * s, y + 2 * s, 8 * s, 15 * s, "#2f6fb0", "#12385e", 1, tg)
    _r(c, x + 50 * s, y + 5 * s, 5 * s, 9 * s, "#8f959c", "#444", 1, tg)
    _o(c, x + 54 * s, y + 7 * s, 5 * s, 5 * s, "#e84a4a", "", 0, tg)


def icon_laserstand(c, x, y, s, tg):
    _o(c, x, y + 26 * s, 40 * s, 12 * s, "#22262c", "#000", 1, tg)
    _l(c, [x + 20 * s, y + 30 * s, x + 20 * s, y + 10 * s], "#3a4048", 3, tg)
    _r(c, x + 12 * s, y, 18 * s, 12 * s, "#22262c", "#000", 1, tg)


def icon_needle(c, x, y, s, tg):
    _r(c, x, y + 5 * s, 40 * s, 8 * s, "#e9eef3", "#9aa6b2", 1, tg)
    _l(c, [x + 4 * s, y + 9 * s, x + 36 * s, y + 9 * s], "#c85a7a", 2, tg)
    _l(c, [x + 36 * s, y + 9 * s, x + 44 * s, y + 9 * s], "#98a2ad", 1, tg)


def icon_tape(c, x, y, s, tg):
    _o(c, x, y, 34 * s, 34 * s, "#e8d9a8", "#b8a367", 2, tg)
    _o(c, x + 11 * s, y + 11 * s, 12 * s, 12 * s, "#f7f8fa", "#b8a367", 1, tg)


def icon_screwdriver(c, x, y, s, tg):
    _r(c, x, y + 6 * s, 20 * s, 12 * s, "#e8801a", "#a3510a", 1, tg)
    _r(c, x + 18 * s, y + 9 * s, 24 * s, 5 * s, "#b9bec4", "#7a7f85", 1, tg)
    _r(c, x + 40 * s, y + 9 * s, 6 * s, 5 * s, "#5c6166", "#333", 1, tg)


def icon_ruler(c, x, y, s, tg):
    _r(c, x, y + 6 * s, 62 * s, 11 * s, "#dfe3e7", "#8b9096", 1, tg)
    for i in range(13):
        _l(c, [x + (3 + 4.6 * i) * s, y + 6 * s,
               x + (3 + 4.6 * i) * s, y + (11 if i % 5 else 9) * s], "#666", 1, tg)


def icon_bigclip(c, x, y, s, tg):
    _r(c, x + 4 * s, y + 8 * s, 20 * s, 16 * s, "#1a1d21", "#000", 1, tg)
    _l(c, [x + 6 * s, y + 8 * s, x + 2 * s, y, x + 14 * s, y - 3 * s], "#8b9096", 2, tg)
    _l(c, [x + 22 * s, y + 8 * s, x + 26 * s, y, x + 14 * s, y - 3 * s], "#8b9096", 2, tg)


def icon_smallclip(c, x, y, s, tg):
    icon_bigclip(c, x, y + 4 * s, s * 0.62, tg)


def icon_tapemeasure(c, x, y, s, tg):
    _r(c, x, y, 30 * s, 26 * s, "#1f4f8a", "#0e2b52", 2, tg)
    _r(c, x + 4 * s, y + 4 * s, 22 * s, 12 * s, "#e8801a", "#a3510a", 1, tg)
    _r(c, x + 8 * s, y + 22 * s, 22 * s, 5 * s, "#f0e6a8", "#a09040", 1, tg)


def icon_slides(c, x, y, s, tg):
    for i in range(3):
        _r(c, x + i * 5 * s, y + i * 4 * s, 46 * s, 34 * s, "#eaf2f7",
           "#9fb3c0", 1, tg)
    c.create_text(x + 33 * s, y + 14 * s, text="slide", fill="#5a6a7a",
                  font=("Helvetica", int(6 * s)), tags=tg)
    for r in range(2):
        for k in range(3):
            _r(c, x + (16 + 9 * k) * s, y + (20 + 6 * r) * s, 6 * s, 4 * s,
               "#c8d4dd", "#8fa3b0", 1, tg)


def icon_film(c, x, y, s, tg):
    _r(c, x, y, 26 * s, 20 * s, "#4a4f55", "#23262a", 1, tg)
    _r(c, x + 3 * s, y + 3 * s, 20 * s, 14 * s, "#5d646c", "", 0, tg)


def icon_holderkit(c, x, y, s, tg):
    _r(c, x, y, 10 * s, 34 * s, "#f2f4f6", "#a8b0b8", 1, tg)
    _r(c, x + 26 * s, y, 10 * s, 34 * s, "#f2f4f6", "#a8b0b8", 1, tg)
    _l(c, [x + 10 * s, y + 26 * s, x + 26 * s, y + 26 * s], "#b9bec4", 2, tg)
    _o(c, x + 14 * s, y + 4 * s, 8 * s, 8 * s, "#c9ccd2", "#7a7f85", 1, tg)


def icon_graphpaper(c, x, y, s, tg):
    _r(c, x, y, 40 * s, 30 * s, "#fdf6ec", "#c9bfa8", 1, tg)
    for i in range(1, 8):
        _l(c, [x + i * 5 * s, y, x + i * 5 * s, y + 30 * s], "#e2b9a8", 1, tg)
    for j in range(1, 6):
        _l(c, [x, y + j * 5 * s, x + 40 * s, y + j * 5 * s], "#e2b9a8", 1, tg)


def icon_cardboard(c, x, y, s, tg):
    _r(c, x, y, 44 * s, 32 * s, "#6e6a63", "#403d38", 1, tg)


def icon_tablet(c, x, y, s, tg):
    _r(c, x, y, 46 * s, 34 * s, "#2a2d31", "#14171a", 2, tg)
    _r(c, x + 3 * s, y + 3 * s, 40 * s, 28 * s, "#3a3e44", "#22262a", 1, tg)
    _r(c, x + 34 * s, y + 12 * s, 10 * s, 8 * s, "#b9bec4", "#7a7f85", 1, tg)


ITEMS = [
    # id, number, korean, english, drawer, w, h, kind
    ("multimeter", 1, "멀티미터", "multimeter", icon_multimeter, 62, 82, "place"),
    ("photodiode", 2, "포토다이오드", "photodiode", icon_photodiode, 40, 38, "part"),
    ("battery", 3, "배터리", "battery", icon_battery, 48, 18, "tool"),
    ("resistor", 4, "저항 10k/200k", "resistors", icon_resistor, 38, 16, "part"),
    ("connector", 5, "압착 커넥터 x4", "connectors", icon_connector, 34, 22, "part"),
    ("batholder", 6, "배터리 홀더", "battery holder", icon_batholder, 50, 22, "part"),
    ("laser", 7, "빨간색 레이저", "red laser", icon_laser, 62, 20, "place"),
    ("laserstand", 8, "레이저 받침대", "laser stand", icon_laserstand, 44, 40, "place"),
    ("needle", 9, "바늘", "needle", icon_needle, 48, 18, "tool"),
    ("tape", 10, "마스킹 테이프", "masking tape", icon_tape, 38, 38, "tool"),
    ("screwdriver", 11, "드라이버", "screwdriver", icon_screwdriver, 50, 22, "tool"),
    ("ruler", 12, "자", "ruler", icon_ruler, 66, 20, "part"),
    ("bigclip", 13, "큰 클립 x2", "big clips", icon_bigclip, 30, 28, "tool"),
    ("tapemeasure", 14, "줄자", "tape measure", icon_tapemeasure, 34, 30, "part"),
    ("slides", 15, "슬라이드", "slides", icon_slides, 60, 44, "part"),
    ("film", 16, "차광 필름", "neutral film", icon_film, 30, 24, "tool"),
    ("smallclip", 17, "작은 클립 x4", "small clips", icon_smallclip, 24, 24, "tool"),
    ("holderkit", 18, "슬라이드 홀더", "slide holder", icon_holderkit, 40, 38, "place"),
    ("graphpaper", 19, "모눈종이", "graph paper", icon_graphpaper, 44, 34, "tool"),
    ("cardboard", 20, "판지", "cardboard", icon_cardboard, 48, 36, "place"),
    ("tablet", 21, "자성 태블릿", "magnetic tablet", icon_tablet, 50, 38, "place"),
]
ITEM_BY_ID = {it[0]: it for it in ITEMS}

PLACE_SLOT = {"tablet": "tablet", "laserstand": "laser_stand",
              "laser": "laser", "holderkit": "holder",
              "cardboard": "screen", "multimeter": "detector"}


# --------------------------------------------------------------------------
#  assembly tab
# --------------------------------------------------------------------------
class AssemblyTab(ttk.Frame):
    """Drag the parts out of the box and build the optical bench."""

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.rig = app.rig

        left = ttk.Frame(self)
        left.pack(side="left", fill="y")
        ttk.Label(left, text=T("장비 상자", "equipment box"),
                  font=("Helvetica", 11, "bold")).pack(anchor="w", padx=6,
                                                       pady=(6, 0))
        self.box = tk.Canvas(left, width=306, height=770, bg=PANEL,
                             highlightthickness=1, highlightbackground="#c3c9d0")
        self.box.pack(padx=6, pady=4)

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True)
        self.bench = tk.Canvas(right, width=690, height=430, bg="#dfe3e8",
                               highlightthickness=1,
                               highlightbackground="#c3c9d0")
        self.bench.pack(fill="both", expand=True, padx=6, pady=(6, 2))

        self.msg = tk.StringVar(value=T(
            "‘자성 태블릿’을 작업대로 끌어다 놓고 시작하십시오. "
            "부품 위에서 오른쪽 클릭 = 상자로 되돌리기.",
            "drag the magnetic tablet onto the bench to start; "
            "right-click a placed part to return it"))
        ttk.Label(right, textvariable=self.msg, foreground=ACCENT,
                  wraplength=670).pack(anchor="w", padx=8)

        self.wire = WiringPanel(right, app)
        self.wire.pack(fill="x", padx=6, pady=4)

        self.drag = None
        self.box.bind("<ButtonPress-1>", self.press)
        self.box.bind("<B1-Motion>", self.motion)
        self.box.bind("<ButtonRelease-1>", self.release)
        self.bench.bind("<ButtonPress-1>", self.press_bench)
        self.bench.bind("<B1-Motion>", self.motion)
        self.bench.bind("<ButtonRelease-1>", self.release)
        self.bench.bind("<Button-3>", self.remove_click)
        self.redraw()

    # ------------------------------------------------------------------
    def redraw(self):
        self.draw_box()
        self.draw_bench()
        self.wire.redraw()

    def draw_box(self):
        c = self.box
        c.delete("all")
        self.box_pos = {}
        cw, ch, cols = 99, 108, 3
        for k, (iid, num, ko, en, drawer, w, h, kind) in enumerate(ITEMS):
            col, row = k % cols, k // cols
            x0, y0 = 8 + col * cw, 10 + row * ch
            tg = ("part", "part:" + iid)
            c.create_rectangle(x0 + 2, y0, x0 + cw - 6, y0 + ch - 8,
                               outline="#dfe3e8", fill="#ffffff", tags=tg)
            ix = x0 + (cw - 8 - w) / 2.0
            iy = y0 + 6 + (66 - h) / 2.0
            drawer(c, ix, iy, 1.0, tg)
            self.box_pos[iid] = (ix, iy, w, h)
            t = c.create_text(x0 + (cw - 4) / 2.0, y0 + 76,
                              text="%d. %s" % (num, T(ko, en)), width=cw - 14,
                              font=("Helvetica", 7), fill="#40474f",
                              anchor="n", justify="center", tags=tg)
            state = self.item_state(iid)
            if state:
                bb = c.bbox(t)
                c.create_text(x0 + (cw - 4) / 2.0, bb[3] + 1, text=state,
                              font=("Helvetica", 7, "bold"), fill="#1a7a3c",
                              anchor="n", tags=tg)
        c.configure(scrollregion=c.bbox("all"))

    def item_state(self, iid):
        r = self.rig
        if iid in PLACE_SLOT and r.placed[PLACE_SLOT[iid]]:
            return T("설치됨", "placed")
        if iid == "holderkit" and r.holder_assembled:
            return T("조립됨", "assembled")
        if iid == "battery" and r.battery_block:
            return T("장착됨", "in holder")
        if iid == "graphpaper" and r.screen_assembled:
            return T("고정됨", "clipped")
        if iid == "needle" and r.pinhole_made:
            return T("핀홀 완성", "pinhole")
        if iid == "film" and r.film_in_clip:
            return T("클립에 장착", "in clip")
        if iid == "bigclip" and r.laser_clipped:
            return T("레이저 ON 고정", "laser latched")
        return ""

    # ------------------------------------------------------------------
    ZONES = [("tablet", 40, 40, 610, 340, "자성 태블릿 (자기 베이스)",
              "magnetic tablet"),
             ("laser_stand", 60, 150, 130, 120, "레이저", "laser"),
             ("holder", 230, 150, 110, 120, "시료", "sample"),
             ("screen", 430, 90, 190, 240, "스크린", "screen"),
             ("detector", 60, 55, 300, 80, "세기 검출기", "detector")]

    def draw_bench(self):
        c = self.bench
        c.delete("all")
        r = self.rig
        c.create_text(345, 16, text=T("작업대 (위에서 본 모습)",
                                      "work bench, top view"),
                      font=("Helvetica", 10, "bold"), fill="#3b434c")
        if r.placed["tablet"]:
            icon_tablet(c, 40, 40, 12.4, ("bench", "slot:tablet"))
            c.create_text(600, 330, text=T("21", "21"), fill="#9aa4ae")
        else:
            c.create_rectangle(40, 40, 650, 380, dash=(4, 3),
                               outline="#9aa4ae")
            c.create_text(345, 210, text=T("여기에 태블릿을 놓으십시오",
                                           "drop the tablet here"),
                          fill="#7b848d")
            return
        for (slot, zx, zy, zw, zh, ko, en) in self.ZONES[1:]:
            c.create_rectangle(zx, zy, zx + zw, zy + zh, dash=(3, 3),
                               outline="#7e8892")
            c.create_text(zx + 5, zy + 9, text=T(ko, en), anchor="w",
                          fill="#c6ccd3", font=("Helvetica", 8))
        if r.placed["laser_stand"]:
            icon_laserstand(c, 78, 176, 1.6, ("bench", "slot:laser_stand"))
        if r.placed["laser"]:
            icon_laser(c, 66, 196, 1.5, ("bench", "slot:laser"))
            if r.laser_clipped:
                icon_bigclip(c, 96, 178, 1.0, ("bench", "slot:laser"))
        if r.placed["holder"]:
            icon_holderkit(c, 258, 180, 1.7, ("bench", "slot:holder"))
            if r.sheet_in_holder:
                icon_slides(c, 250, 182, 1.1, ("bench", "slot:holder"))
        if r.placed["screen"]:
            icon_cardboard(c, 448, 118, 3.4, ("bench", "slot:screen"))
            icon_graphpaper(c, 456, 126, 3.4, ("bench", "slot:screen"))
        if r.placed["detector"]:
            icon_multimeter(c, 70, 58, 0.85, ("bench", "slot:detector"))
            icon_photodiode(c, 150, 66, 1.0, ("bench", "slot:detector"))
            icon_batholder(c, 210, 66, 1.0, ("bench", "slot:detector"))
            icon_resistor(c, 280, 70, 1.0, ("bench", "slot:detector"))
        if r.beam_ok():
            c.create_line(126, 202, 452, 202, fill="#e0402e", width=2)
            c.create_line(288, 202, 452, 150, fill="#f08c7a", width=1)
            c.create_line(288, 202, 452, 254, fill="#f08c7a", width=1)

    # ------------------------------------------------------------------
    def press(self, ev):
        c = self.box
        for t in c.gettags("current"):
            if t.startswith("part:"):
                iid = t[5:]
                x, y, w, h = self.box_pos[iid]
                self.drag = {"iid": iid, "src": "box", "x": ev.x_root,
                             "y": ev.y_root}
                self.ghost(iid, ev)
                return

    def press_bench(self, ev):
        self.drag = None

    def ghost(self, iid, ev):
        it = ITEM_BY_ID[iid]
        self.gwin = tk.Toplevel(self)
        self.gwin.overrideredirect(True)
        try:
            self.gwin.attributes("-alpha", 0.85)
        except Exception:
            pass
        cv = tk.Canvas(self.gwin, width=it[5] + 20, height=it[6] + 20,
                       bg="#ffffff", highlightthickness=1,
                       highlightbackground=ACCENT)
        cv.pack()
        it[4](cv, 10, 10, 1.0, ())
        self.gwin.geometry("+%d+%d" % (ev.x_root - 20, ev.y_root - 20))

    def motion(self, ev):
        if self.drag and hasattr(self, "gwin") and self.gwin:
            self.gwin.geometry("+%d+%d" % (ev.x_root - 20, ev.y_root - 20))

    def release(self, ev):
        if not self.drag:
            return
        iid = self.drag["iid"]
        if hasattr(self, "gwin") and self.gwin:
            self.gwin.destroy()
            self.gwin = None
        self.drag = None
        bx = self.bench.winfo_rootx()
        by = self.bench.winfo_rooty()
        x, y = ev.x_root - bx, ev.y_root - by
        inside = (0 <= x <= self.bench.winfo_width()
                  and 0 <= y <= self.bench.winfo_height())
        if inside:
            self.drop_on_bench(iid, x, y)
        else:
            tx, ty = ev.x_root - self.box.winfo_rootx(), \
                ev.y_root - self.box.winfo_rooty()
            self.drop_on_box(iid, tx, ty)
        self.redraw()
        self.app.refresh()

    # ------------------------------------------------------------------
    def drop_on_box(self, iid, x, y):
        """dropping a tool onto another item = using it"""
        target = None
        for jid, (bx, by, w, h) in self.box_pos.items():
            if bx - 8 <= x <= bx + w + 8 and by - 8 <= y <= by + h + 14:
                target = jid
        if target is None or target == iid:
            return
        self.combine(iid, target)

    def combine(self, tool, target):
        r = self.rig
        pair = (tool, target)
        if pair in (("screwdriver", "holderkit"), ("holderkit", "screwdriver")):
            r.holder_assembled = True
            self.say(T("드라이버로 슬라이드 홀더를 조립했습니다.",
                       "slide holder assembled with the screwdriver"))
        elif pair in (("battery", "batholder"), ("batholder", "battery")):
            r.battery_block = True
            self.say(T("배터리를 홀더에 넣었습니다 (빨간 선 = +).",
                       "battery inserted (red lead = +)"))
        elif pair in (("graphpaper", "cardboard"), ("cardboard", "graphpaper")):
            self._paper = True
            self.say(T("판지 위에 모눈종이를 올렸습니다. 작은 클립으로 고정하십시오.",
                       "graph paper on the cardboard - now clip it"))
        elif pair in (("smallclip", "cardboard"), ("smallclip", "graphpaper")):
            if getattr(self, "_paper", False):
                r.screen_assembled = True
                self.say(T("모눈종이를 작은 클립으로 고정했습니다.",
                           "graph paper clipped to the cardboard"))
            else:
                self.say(T("먼저 판지 위에 모눈종이를 올리십시오.",
                           "put the graph paper on the cardboard first"))
        elif pair in (("film", "bigclip"), ("bigclip", "film")):
            r.film_in_clip = True
            self.say(T("큰 클립에 차광 필름을 끼웠습니다.",
                       "the neutral film is held by a big clip"))
        elif pair in (("tape", "laser"), ("laser", "tape")):
            self._tape = True
            self.say(T("레이저 구멍을 마스킹 테이프로 막았습니다. 바늘로 뚫으십시오.",
                       "laser aperture covered with tape - pierce it"))
        elif pair in (("needle", "laser"), ("laser", "needle")):
            if getattr(self, "_tape", False):
                r.pinhole_made = True
                self.say(T("바늘로 핀홀을 뚫었습니다 (빔이 가늘어집니다).",
                           "pinhole pierced (narrower beam)"))
            else:
                self.say(T("먼저 마스킹 테이프로 구멍을 막으십시오.",
                           "cover the aperture with tape first"))
        elif pair in (("bigclip", "laser"), ("laser", "bigclip")):
            if self.rig.placed["laser"]:
                r.laser_clipped = True
                self.say(T("큰 클립으로 레이저 버튼을 눌러 고정했습니다.",
                           "the laser button is latched by a big clip"))
            else:
                self.say(T("레이저를 먼저 받침대에 설치하십시오.",
                           "mount the laser first"))
        else:
            self.say(T("그 조합은 의미가 없습니다.",
                       "that combination does nothing"))

    def drop_on_bench(self, iid, x, y):
        r = self.rig
        if iid in PLACE_SLOT:
            slot = PLACE_SLOT[iid]
            ok, why = r.place(slot)
            if ok:
                self.say(T("%s을(를) 설치했습니다." % SLOT_KO[slot],
                           "%s placed" % SLOT_EN[slot]))
            else:
                self.say(why)
            return
        # tools dropped on the bench act on whatever is under the cursor
        for (slot, zx, zy, zw, zh, ko, en) in self.ZONES:
            if zx <= x <= zx + zw and zy <= y <= zy + zh and r.placed[slot]:
                if slot in ("laser", "laser_stand"):
                    self.combine(iid, "laser")
                    return
        self.say(T("작업대 위에서는 그 부품을 그렇게 쓸 수 없습니다.",
                   "that part cannot be used like that on the bench"))

    def remove_click(self, ev):
        for t in self.bench.gettags("current"):
            if t.startswith("slot:"):
                self.rig.remove(t[5:])
                self.say(T("부품을 상자로 되돌렸습니다.",
                           "the part went back to the box"))
                self.redraw()
                self.app.refresh()
                return

    def say(self, s):
        self.msg.set(s)


# --------------------------------------------------------------------------
#  wiring of the intensity detector (figure 17 / 18)
# --------------------------------------------------------------------------
LEAD_KO = {"BAT+": "전지 +(빨강)", "BAT-": "전지 -(검정)",
           "PD_RED": "다이오드 빨강", "PD_BLK": "다이오드 검정",
           "R_A": "저항 A", "R_B": "저항 B",
           "MM_RED": "전압계 빨강", "MM_BLK": "전압계 검정(COM)"}


class WiringPanel(ttk.LabelFrame):
    def __init__(self, master, app):
        ttk.LabelFrame.__init__(self, master, text=T(
            "세기 검출기 배선 (압착 커넥터 4개, 각 커넥터의 3점은 서로 연결됨)",
            "detector wiring (4 lever connectors, all three points joined)"))
        self.app = app
        self.rig = app.rig
        self.sel = tk.StringVar(value="BAT+")
        top = ttk.Frame(self)
        top.pack(fill="x", padx=4, pady=2)
        for l in LEADS:
            ttk.Radiobutton(top, text=T(LEAD_KO[l], l), value=l,
                            variable=self.sel).pack(side="left", padx=2)
        mid = ttk.Frame(self)
        mid.pack(fill="x", padx=4, pady=2)
        self.cbtn = []
        for i in range(4):
            f = ttk.Frame(mid, relief="groove", borderwidth=2)
            f.pack(side="left", padx=4)
            b = ttk.Button(f, text="C%d" % (i + 1), width=14,
                           command=lambda i=i: self.insert(i))
            b.pack()
            lab = ttk.Label(f, text="-", width=22, anchor="w",
                            font=("Helvetica", 8))
            lab.pack()
            self.cbtn.append(lab)
        bot = ttk.Frame(self)
        bot.pack(fill="x", padx=4, pady=2)
        ttk.Button(bot, text=T("커넥터 비우기", "empty connectors"),
                   command=self.clear).pack(side="left", padx=3)
        self.res = tk.StringVar(value="10k")
        ttk.Label(bot, text=T("  회로에 넣은 저항:", "  resistor:")).pack(
            side="left")
        for v in ("10k", "200k"):
            ttk.Radiobutton(bot, text=v + "\u03a9", value=v, variable=self.res,
                            command=self.setres).pack(side="left")
        self.state = tk.StringVar()
        ttk.Label(bot, textvariable=self.state, foreground=ACCENT).pack(
            side="left", padx=10)

    def setres(self):
        self.rig.resistor = self.res.get()
        self.app.refresh()

    def insert(self, i):
        l = self.sel.get()
        for c in self.rig.connectors:
            c.discard(l)
        if len(self.rig.connectors[i]) >= 3:
            return
        self.rig.connectors[i].add(l)
        self.redraw()
        self.app.refresh()

    def clear(self):
        for c in self.rig.connectors:
            c.clear()
        self.redraw()
        self.app.refresh()

    def redraw(self):
        for i in range(4):
            s = ", ".join(sorted(self.rig.connectors[i])) or "-"
            self.cbtn[i].configure(text=s)
        self.state.set("")          # no verdict: read the multimeter


# --------------------------------------------------------------------------
#  the optical bench:  screen view, sample choice, instruments
# --------------------------------------------------------------------------
#  isophote colour ramps:  a real laser spot on cream millimetre paper looks
#  pink-white in the core and only faintly red in the halo; in a dark room
#  only the spots themselves are seen.
SPOT_LEVELS_DARK = [
    (0.0009, "#1c0206"), (0.0025, "#2e0410"), (0.006, "#4a0614"),
    (0.015, "#6d0a1c"), (0.04, "#951024"), (0.10, "#bf162c"),
    (0.30, "#e01f35"), (1.0, "#f43a4c"), (4.0, "#fb6f80"),
    (20.0, "#ffa8b6"), (100.0, "#ffe0e6"), (400.0, "#ffffff")]
SPOT_LEVELS_PAPER = [
    (0.0009, "#f7ded4"), (0.0025, "#f2c6b6"), (0.006, "#eba591"),
    (0.015, "#e5806a"), (0.04, "#dd5340"), (0.10, "#d3301f"),
    (0.30, "#c11a18"), (1.0, "#ad0f18"), (4.0, "#e0405a"),
    (20.0, "#ff9cb0"), (100.0, "#ffe6ea"), (400.0, "#ffffff")]


class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.rig = app.rig
        self.pxmm = 2.1
        self.cx_mm = 0.0
        self.cy_mm = 0.0
        self.exposure = tk.DoubleVar(value=0.0)
        self.pan = None

        # ---------------- left column : the slides -----------------------
        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=4, pady=4)
        ttk.Label(left, text=T("슬라이드 (15)", "slides (15)"),
                  font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.sheetv = tk.StringVar(value="")
        for key in ("DG", "UC", "PG", "MR"):
            ttk.Radiobutton(left, text=SHEETS[key][0], value=key,
                            variable=self.sheetv,
                            command=self.pick_sheet).pack(anchor="w")
        self.slide_cv = tk.Canvas(left, width=210, height=170, bg="#eaf2f7",
                                  highlightthickness=1,
                                  highlightbackground="#9fb3c0")
        self.slide_cv.pack(pady=4)
        self.slide_cv.bind("<Button-1>", self.click_slide)
        self.flip = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text=T("슬라이드를 뒤집어 넣음",
                                     "slide inserted the wrong way round"),
                        variable=self.flip, command=self.set_flip).pack(
            anchor="w")
        ttk.Separator(left).pack(fill="x", pady=6)

        # ---------------- geometry ---------------------------------------
        ttk.Label(left, text=T("광학 배치 (위에서 본 모습)",
                               "optical layout, top view"),
                  font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.rail = tk.Canvas(left, width=210, height=96, bg="#dfe3e8",
                              highlightthickness=1,
                              highlightbackground="#9fb3c0")
        self.rail.pack(pady=3)
        self.rail.bind("<B1-Motion>", self.drag_screen)
        self.tapev = tk.StringVar(value="--")
        f = ttk.Frame(left)
        f.pack(fill="x")
        ttk.Button(f, text=T("줄자로 재기 (14)", "read the tape (14)"),
                   command=self.read_tape).pack(side="left")
        ttk.Label(f, textvariable=self.tapev, font=("Courier", 10, "bold")
                  ).pack(side="left", padx=6)

        # ---------------- centre : the screen ----------------------------
        mid = ttk.Frame(self)
        mid.pack(side="left", fill="both", expand=True)
        self.cv = tk.Canvas(mid, width=690, height=520, bg="#fdf6ec",
                            highlightthickness=1,
                            highlightbackground="#c3c9d0")
        self.cv.pack(fill="both", expand=True, padx=4, pady=4)
        self.cv.bind("<ButtonPress-1>", self.press)
        self.cv.bind("<B1-Motion>", self.motion)
        self.cv.bind("<ButtonRelease-1>", self.release)
        self.cv.bind("<MouseWheel>", self.wheel)
        self.cv.bind("<Button-4>", lambda e: self.wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self.wheel(e, -1))
        self.cv.bind("<Configure>", lambda e: self.draw_screen())
        self.info = tk.StringVar(value="")
        ttk.Label(mid, textvariable=self.info).pack(anchor="w", padx=6)

        # ---------------- right column : instruments ---------------------
        right = ttk.Frame(self)
        right.pack(side="left", fill="y", padx=4, pady=4)
        lf = ttk.LabelFrame(right, text=T("레이저 (7)", "laser (7)"))
        lf.pack(fill="x", pady=3)
        self.laserv = tk.BooleanVar(value=False)
        ttk.Checkbutton(lf, text=T("켜기", "on"), variable=self.laserv,
                        command=self.set_laser).pack(anchor="w")
        self.pinv = tk.BooleanVar(value=False)
        ttk.Checkbutton(lf, text=T("핀홀 사용 (9,10)", "use the pinhole"),
                        variable=self.pinv, command=self.set_pin).pack(
            anchor="w")
        ff = ttk.Frame(lf)
        ff.pack(anchor="w")
        ttk.Label(ff, text=T("차광 필름 장수 (16)", "films (16)")).pack(
            side="left")
        self.filmv = tk.IntVar(value=0)
        tk.Spinbox(ff, from_=0, to=3, width=3, textvariable=self.filmv,
                   command=self.set_film).pack(side="left", padx=4)

        mf = ttk.LabelFrame(right, text=T("멀티미터 (1)", "multimeter (1)"))
        mf.pack(fill="x", pady=3)
        self.mmdisp = tk.Label(mf, text="", bg="#cfd8c8", fg="#12301f",
                               font=("Courier", 20, "bold"), width=8,
                               relief="sunken")
        self.mmdisp.pack(padx=6, pady=4)
        self.dial = tk.StringVar(value="OFF")
        for v, ko, en in (("OFF", "OFF", "OFF"), ("DCV200m", "DCV 200 mV", "DCV 200m"),
                          ("DCV2", "DCV 2 V", "DCV 2"), ("DCV20", "DCV 20 V", "DCV 20"),
                          ("OHM", "저항", "ohm"), ("ACV", "ACV", "ACV")):
            ttk.Radiobutton(mf, text=T(ko, en), value=v, variable=self.dial,
                            command=self.set_dial).pack(anchor="w")

        vf = ttk.LabelFrame(right, text=T("보기", "view"))
        vf.pack(fill="x", pady=3)
        self.dark = tk.BooleanVar(value=False)
        ttk.Checkbutton(vf, text=T("실내 조명 끄기 (암실)", "room light off"),
                        variable=self.dark, command=self.refresh).pack(
            anchor="w")
        ttk.Label(vf, text=T("노출", "exposure")).pack(anchor="w")
        ttk.Scale(vf, from_=-3.0, to=3.0, length=150,
                  variable=self.exposure,
                  command=lambda e: self.refresh()).pack(fill="x", padx=4)
        ttk.Button(vf, text=T("배율 초기화", "reset zoom"),
                   command=self.reset_zoom).pack(fill="x", pady=2)
        ttk.Label(right, text=T(
            "휠 = 확대/축소\n왼쪽 드래그(빈 공간) = 이동\n포토다이오드를 끌어서 측정",
            "wheel = zoom\nleft-drag = pan\ndrag the photodiode to measure"),
            foreground="#5a636c").pack(anchor="w", pady=6)

        self.after(400, self.tick)
        self.refresh()

    # ------------------------------------------------------------------
    def pick_sheet(self):
        ok, why = self.rig.insert_sheet(self.sheetv.get())
        if not ok:
            self.info.set(why)
            self.sheetv.set(self.rig.sheet_in_holder or "")
        self.refresh()

    def set_flip(self):
        self.rig.slide_flipped = self.flip.get()
        self.refresh()

    def set_laser(self):
        r = self.rig
        if self.laserv.get():
            if not r.placed["laser"]:
                self.info.set(T("레이저가 설치되지 않았습니다.",
                                "the laser is not mounted"))
                self.laserv.set(False)
                return
            if not r.laser_clipped:
                self.info.set(T("큰 클립으로 레이저 버튼을 고정해야 합니다.",
                                "latch the laser button with a big clip"))
                self.laserv.set(False)
                return
        r.laser_on = self.laserv.get()
        self.refresh()

    def set_pin(self):
        if self.pinv.get() and not self.rig.pinhole_made:
            self.info.set(T("마스킹 테이프와 바늘로 핀홀을 먼저 만드십시오.",
                            "make the pinhole with tape and needle first"))
            self.pinv.set(False)
            return
        self.rig.use_pinhole = self.pinv.get()
        self.refresh()

    def set_film(self):
        n = int(self.filmv.get())
        if n and not self.rig.film_in_clip:
            self.info.set(T("필름을 큰 클립에 끼워 홀더를 만드십시오.",
                            "mount the film in a big clip first"))
            self.filmv.set(0)
            return
        self.rig.n_films = n
        self.refresh()

    def set_dial(self):
        self.rig.mm_dial = self.dial.get()

    def read_tape(self):
        if not (self.rig.placed["holder"] and self.rig.placed["screen"]):
            self.tapev.set("--")
            return
        self.tapev.set("%d mm" % self.rig.tape_measure())

    def reset_zoom(self):
        self.pxmm = 2.1
        self.cx_mm = self.cy_mm = 0.0
        self.refresh()

    # ------------------------------------------------------------------
    def drag_screen(self, ev):
        x = min(max(ev.x, 40), 205)
        L = (x - 40) / 165.0 * 1200.0 + 200.0
        self.rig.L_mm = round(L)
        self.refresh()

    def draw_rail(self):
        c = self.rail
        c.delete("all")
        r = self.rig
        c.create_line(8, 60, 205, 60, fill="#8b9096", width=3)
        icon_laserstand(c, 6, 40, 0.5, ())
        if r.placed["laser"]:
            icon_laser(c, 4, 48, 0.42, ())
        if r.placed["holder"]:
            icon_holderkit(c, 30, 40, 0.55, ())
        sx = 40 + (r.L_mm - 200.0) / 1200.0 * 165.0
        if r.placed["screen"]:
            c.create_rectangle(sx - 3, 26, sx + 3, 78, fill="#6e6a63",
                               outline="#403d38")
        if r.beam_ok():
            c.create_line(14, 58, sx, 58, fill="#e0402e", width=2)
        c.create_text(105, 12, text=T("슬라이드 - 스크린 거리를 드래그로 조절",
                                      "drag to set the slide-screen distance"),
                      font=("Helvetica", 7), fill="#5a636c")
        c.create_text(105, 88, text=T("줄자로 재세요", "use the tape"),
                      font=("Helvetica", 8, "bold"), fill="#3b434c")

    # ------------------------------------------------------------------
    def draw_slide(self):
        c = self.slide_cv
        c.delete("all")
        key = self.rig.sheet_in_holder
        if key is None:
            c.create_text(105, 85, text=T("슬라이드를 고르십시오",
                                          "choose a slide"), fill="#5a6a7a")
            return
        title, names = SHEETS[key]
        c.create_text(105, 12, text=title, font=("Helvetica", 9, "bold"),
                      fill="#33414d")
        n = len(names)
        cols = 3 if n > 4 else 2
        rows = (n + cols - 1) // cols
        bw, bh = 190 / cols, min(40, 130 / rows)
        self.slide_cells = []
        for i, nm in enumerate(names):
            cxx = 10 + (i % cols) * bw
            cyy = 26 + (i // cols) * (bh + 6)
            sel = (self.rig.sample == nm)
            c.create_rectangle(cxx, cyy, cxx + bw - 8, cyy + bh,
                               fill="#ffffff" if not sel else "#ffe9c9",
                               outline=ACCENT if sel else "#8fa3b0",
                               width=2 if sel else 1)
            c.create_text(cxx + (bw - 8) / 2, cyy + bh / 2, text=nm,
                          font=("Helvetica", 8, "bold"), fill="#33414d")
            self.slide_cells.append((cxx, cyy, cxx + bw - 8, cyy + bh, nm))

    def click_slide(self, ev):
        for (x0, y0, x1, y1, nm) in getattr(self, "slide_cells", []):
            if x0 <= ev.x <= x1 and y0 <= ev.y <= y1:
                ok, why = self.rig.select_sample(nm)
                self.info.set(why if not ok else T(
                    "시료 %s을(를) 레이저 앞에 놓았습니다." % nm,
                    "sample %s is in the beam" % nm))
                self.refresh()
                return

    # ------------------------------------------------------------------
    def to_px(self, xmm, ymm):
        w = self.cv.winfo_width() or 690
        h = self.cv.winfo_height() or 520
        return (w / 2 + (xmm - self.cx_mm) * self.pxmm,
                h / 2 - (ymm - self.cy_mm) * self.pxmm)

    def to_mm(self, px, py):
        w = self.cv.winfo_width() or 690
        h = self.cv.winfo_height() or 520
        return (self.cx_mm + (px - w / 2) / self.pxmm,
                self.cy_mm - (py - h / 2) / self.pxmm)

    def draw_screen(self):
        c = self.cv
        c.delete("all")
        r = self.rig
        w = c.winfo_width() or 690
        h = c.winfo_height() or 520
        dark = self.dark.get()
        c.configure(bg="#14100c" if dark else "#fdf6ec")
        if not r.placed["screen"]:
            c.create_text(w / 2, h / 2, text=T("스크린이 없습니다",
                                               "no screen"), fill="#8b9096")
            return
        # ---- the millimetre paper --------------------------------------
        x0, y0 = self.to_px(-r.screen_w / 2, r.screen_h / 2)
        x1, y1 = self.to_px(r.screen_w / 2, -r.screen_h / 2)
        c.create_rectangle(x0, y0, x1, y1,
                           fill="#1b1712" if dark else "#fdf6ec",
                           outline="#b8ab93")
        minor = "#2a231b" if dark else "#f0d2c2"
        major = "#3a3025" if dark else "#e0a68c"
        if self.pxmm > 3.0:
            m = 1
        elif self.pxmm > 1.2:
            m = 5
        else:
            m = 10
        k = -int(r.screen_w / 2 / m) * m
        while k <= r.screen_w / 2:
            px, _ = self.to_px(k, 0)
            if k % 10 == 0:
                c.create_line(px, y0, px, y1, fill=major)
            elif k % m == 0:
                c.create_line(px, y0, px, y1, fill=minor)
            k += m
        k = -int(r.screen_h / 2 / m) * m
        while k <= r.screen_h / 2:
            _, py = self.to_px(0, k)
            if k % 10 == 0:
                c.create_line(x0, py, x1, py, fill=major)
            elif k % m == 0:
                c.create_line(x0, py, x1, py, fill=minor)
            k += m
        for k in range(-140, 141, 20):
            px, _ = self.to_px(k, 0)
            _, py = self.to_px(0, -r.screen_h / 2)
            c.create_text(px, py + 9, text=str(k), font=("Helvetica", 7),
                          fill="#9a8f7c")
        for k in range(-100, 101, 20):
            _, py = self.to_px(0, k)
            px, _ = self.to_px(-r.screen_w / 2, 0)
            c.create_text(px - 12, py, text=str(k), font=("Helvetica", 7),
                          fill="#9a8f7c")
        # ---- the diffraction spots -------------------------------------
        ramp = SPOT_LEVELS_DARK if dark else SPOT_LEVELS_PAPER
        expo = 10.0 ** self.exposure.get()
        # the eye / the camera add their own blur on top of the spot width
        sig = math.hypot(r.spot_sigma_mm(), 0.45)
        for (sx, sy, p) in r.spots():
            A = expo * p / 3.0e-4
            if A < ramp[0][0]:
                continue
            px, py = self.to_px(sx, sy)
            if px < -40 or px > w + 40 or py < -40 or py > h + 40:
                continue
            for (lev, col) in ramp:
                if A <= lev:
                    continue
                rad = sig * math.sqrt(2.0 * math.log(A / lev)) * self.pxmm
                rad = max(rad, 1.2)
                c.create_oval(px - rad, py - rad, px + rad, py + rad,
                              fill=col, outline="")
        # ---- the photodiode -------------------------------------------
        if r.placed["detector"]:
            px, py = self.to_px(r.pd_x, r.pd_y)
            rad = r.truth.pd_diameter / 2.0 * self.pxmm
            c.create_oval(px - rad, py - rad, px + rad, py + rad,
                          outline="#2f6fb0", width=2, tags="pd")
            c.create_rectangle(px - 17, py - 11, px + 17, py + 11,
                               outline="#1f7a3c", width=2, tags="pd")
            c.create_text(px, py - 18, text=T("포토다이오드", "photodiode"),
                          font=("Helvetica", 7), fill="#1f7a3c", tags="pd")

    # ------------------------------------------------------------------
    def press(self, ev):
        r = self.rig
        if r.placed["detector"]:
            px, py = self.to_px(r.pd_x, r.pd_y)
            if abs(ev.x - px) < 20 and abs(ev.y - py) < 14:
                self.dragpd = True
                return
        self.dragpd = False
        self.pan = (ev.x, ev.y, self.cx_mm, self.cy_mm)

    def motion(self, ev):
        if getattr(self, "dragpd", False):
            self.rig.pd_x, self.rig.pd_y = self.to_mm(ev.x, ev.y)
            self.refresh()
        elif self.pan:
            x0, y0, cx, cy = self.pan
            self.cx_mm = cx - (ev.x - x0) / self.pxmm
            self.cy_mm = cy + (ev.y - y0) / self.pxmm
            self.refresh()

    def release(self, ev):
        self.pan = None
        self.dragpd = False

    def wheel(self, ev, direction=None):
        d = direction if direction is not None else (1 if ev.delta > 0 else -1)
        mx, my = self.to_mm(ev.x, ev.y)
        self.pxmm = min(24.0, max(0.9, self.pxmm * (1.16 ** d)))
        nx, ny = self.to_mm(ev.x, ev.y)
        self.cx_mm += mx - nx
        self.cy_mm += my - ny
        self.refresh()

    # ------------------------------------------------------------------
    def tick(self):
        self.mmdisp.configure(text=self.rig.multimeter() or "      ")
        pos = T("포토다이오드 %.1f, %.1f mm", "photodiode %.1f, %.1f mm") \
            % (self.rig.pd_x, self.rig.pd_y)
        cur = self.info.get()
        if "mm" not in cur or "photodiode" in cur or "포토다이오드" in cur:
            self.info.set(pos)
        self.after(400, self.tick)

    def refresh(self):
        self.laserv.set(self.rig.laser_on)
        self.draw_slide()
        self.draw_rail()
        self.draw_screen()


# --------------------------------------------------------------------------
class App(ttk.Frame):
    def __init__(self, master, seed=None):
        ttk.Frame.__init__(self, master)
        self.master = master
        self.rig = Rig(Truth(seed))
        master.title(T("IdPhO 2020 실험 1 — 결정학 (HaslaLab)",
                       "IdPhO 2020 Experiment 1 - Crystallography (HaslaLab)"))
        bar = ttk.Frame(self)
        bar.pack(fill="x")
        ttk.Label(bar, text=T("IdPhO 2020 · 실험 1 · 결정학",
                              "IdPhO 2020 - Experiment 1 - Crystallography"),
                  font=("Helvetica", 12, "bold")).pack(side="left", padx=8,
                                                       pady=4)
        ttk.Label(bar, text="\u03bb = 630 nm").pack(side="left", padx=12)
        ttk.Button(bar, text=T("새 세션", "new session"),
                   command=self.new_session).pack(side="right", padx=6)
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.tab_a = AssemblyTab(self.nb, self)
        self.tab_b = BenchTab(self.nb, self)
        self.nb.add(self.tab_a, text=T("  조립  ", "  assembly  "))
        self.nb.add(self.tab_b, text=T("  실험대  ", "  bench  "))
        self.nb.bind("<<NotebookTabChanged>>", self._tab_changed)
        self.pack(fill="both", expand=True)

    def _tab_changed(self, _e=None):
        try:
            if self.nb.index("current") == 0:
                self.tab_a.redraw()
            else:
                self.tab_b.refresh()
        except Exception:
            pass

    def refresh(self):
        self.tab_b.rig = self.rig
        self.tab_b.refresh()
        self.tab_a.rig = self.rig

    def new_session(self):
        self.rig = Rig(Truth())
        self.tab_a.rig = self.rig
        self.tab_a.wire.rig = self.rig
        self.tab_a._paper = False
        self.tab_a._tape = False
        self.tab_b.rig = self.rig
        for c in self.tab_a.wire.cbtn:
            c.configure(text="-")
        self.tab_a.redraw()
        self.tab_b.refresh()


def main():
    global LANG
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default=LANG, choices=["ko", "en"])
    ap.add_argument("--seed", type=int, default=None)
    ns = ap.parse_args()
    LANG = ns.lang
    if tk is None:
        print("tkinter is not available")
        return 1
    root = tk.Tk()
    root.geometry("1500x900")
    try:
        root.tk.call("ttk::style", "theme", "use", "clam")
    except Exception:
        pass
    App(root, ns.seed)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
