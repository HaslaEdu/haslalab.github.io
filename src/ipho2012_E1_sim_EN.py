#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  43rd International Physics Olympiad  (IPhO 2012, Tartu, Estonia)
  Experimental Problem E1 :  THE MAGNETIC PERMEABILITY OF WATER
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The simulator shows ONLY what the real instruments show -- the digital
    caliper LCD (laser carriage position x), the laser spot on the mm graph
    paper (height y) and what the eye sees of the setup (side view, top view,
    the reflection of a straight edge in the water).  No slope, no integral,
    no permeability and no fitted curve is ever computed or displayed.
    All hidden true parameters (magnet, susceptibility of the water, beam
    angle, screen distance, tray placement, water depth, noise) are randomised
    for every session.

    Run:   python3 ipho2012_E1_sim_KO.py   [--seed=N]
"""

import math
import random
import sys
import tkinter as tk
from tkinter import ttk

# --------------------------------------------------------------------------
# language
# --------------------------------------------------------------------------
LANG = "en"          # the KO edition differs only in this line


def T(ko, en):
    """Bilingual string helper."""
    return ko if LANG == "ko" else en


# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------
MU0 = 4.0e-7 * math.pi
RHO_W = 1000.0
G_ACC = 9.8
GAMMA_W = 0.0728            # surface tension of water, N/m (real surface, not asked for)

APP_TITLE = "IPhO 2012 E1"
PAPER_Z0 = 320.0        # height above the table of the graph-paper origin (y = 0)
PAPER_H = 180.0         # usable height of the graph paper [mm]
PAPER_W = 120.0         # usable width of the graph paper [mm]


# ==========================================================================
#  1.  complete elliptic integrals and the field of a cylindrical magnet
# ==========================================================================
def ellip_ke(m):
    """Complete elliptic integrals K(m), E(m), parameter m = k^2, by AGM."""
    if m < 0.0:
        m = 0.0
    if m > 1.0 - 1e-15:
        m = 1.0 - 1e-15
    a, b, c = 1.0, math.sqrt(1.0 - m), math.sqrt(m)
    s = 0.5 * c * c
    p = 1.0
    for _ in range(40):
        if abs(c) < 1e-17:
            break
        a, b, c = 0.5 * (a + b), math.sqrt(a * b), 0.5 * (a - b)
        p *= 2.0
        s += p * 0.5 * c * c
    kk = 0.5 * math.pi / a
    return kk, kk * (1.0 - s)


def loop_field(a, r, zeta):
    """(Br, Bz) of a circular loop, radius a, unit current, field point (r, zeta)."""
    if r < 1e-12:
        d = a * a + zeta * zeta
        return 0.0, MU0 * a * a / (2.0 * d * math.sqrt(d))
    s = (a + r) ** 2 + zeta * zeta
    d = (a - r) ** 2 + zeta * zeta
    kk, ee = ellip_ke(4.0 * a * r / s)
    rs = math.sqrt(s)
    bz = MU0 / (2.0 * math.pi) / rs * (kk + (a * a - r * r - zeta * zeta) / d * ee)
    br = MU0 / (2.0 * math.pi) * zeta / (r * rs) * (-kk + (a * a + r * r + zeta * zeta) / d * ee)
    return br, bz


def _gauss_legendre(n):
    xs, ws = [], []
    for i in range(1, n + 1):
        x = math.cos(math.pi * (i - 0.25) / (n + 0.5))
        dp = 1.0
        for _ in range(100):
            p0, p1 = 1.0, x
            for k in range(2, n + 1):
                p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
            dp = n * (x * p1 - p0) / (x * x - 1.0)
            dx = -p1 / dp
            x += dx
            if abs(dx) < 1e-15:
                break
        xs.append(x)
        ws.append(2.0 / ((1.0 - x * x) * dp * dp))
    return xs, ws


_GX, _GW = _gauss_legendre(8)


class CylinderMagnet:
    """Uniformly axially magnetised cylinder, radius R, length L, remanence Br.
    Occupies -L <= z <= 0 (flat top face at z = 0), axis at r = 0.
    Equivalent solenoid: azimuthal surface current density K = Br/mu0."""

    def __init__(self, radius, length, remanence):
        self.R, self.L, self.Br = radius, length, remanence
        self.K = remanence / MU0
        edges = [e for e in (0.0, -0.05e-3, -0.15e-3, -0.5e-3, -1.5e-3, -4e-3, -10e-3) if e > -length]
        edges.append(-length)
        self.nodes = []
        for i in range(len(edges) - 1):
            z1, z2 = edges[i], edges[i + 1]
            hm, hc = 0.5 * (z2 - z1), 0.5 * (z1 + z2)
            for x, w in zip(_GX, _GW):
                self.nodes.append((hc + hm * x, abs(hm) * w * self.K))

    def bmag(self, r, z):
        br = bz = 0.0
        for zp, w in self.nodes:
            b1, b2 = loop_field(self.R, r, z - zp)
            br += b1 * w
            bz += b2 * w
        return math.hypot(br, bz)

    def bz_axis(self, z):
        """Closed form on-axis field (used for calibration / cross checks)."""
        r2 = self.R * self.R
        f = ((z + self.L) / math.sqrt((z + self.L) ** 2 + r2) - z / math.sqrt(z * z + r2))
        return 0.5 * self.Br * f


def remanence_for(radius, length, z0, b0):
    """Remanence giving |B| = b0 on the axis at height z0 above the top face."""
    return b0 / CylinderMagnet(radius, length, 1.0).bz_axis(z0)


# ==========================================================================
#  2.  shape of the water surface
# ==========================================================================
class WaterSurface:
    """Static free surface of the water above the magnet.

    Balance of pressures at the surface (linearised curvature):

        rho g eta  -  gamma * lap(eta)  =  chi * B(r, d+eta)^2 / (2 mu0)

    with chi = mu - 1 < 0 for a diamagnetic liquid, so eta < 0 (depression).
    Surface tension is *physically* present in the real tray; the official
    analysis is allowed to neglect it, the simulator is not.
    """

    def __init__(self, magnet, depth, chi, gamma=GAMMA_W, rmax=0.070, dr=0.00025):
        self.magnet, self.depth, self.chi = magnet, depth, chi
        self.dr, self.n = dr, int(rmax / dr) + 1
        n, self.eta = self.n, [0.0] * (int(rmax / dr) + 1)
        b2, db2 = [], []
        for i in range(n):
            r = i * dr
            b1 = magnet.bmag(r, depth)
            bh = magnet.bmag(r, depth + 20e-6)
            b2.append(b1 * b1)
            db2.append((bh * bh - b1 * b1) / 20e-6)
        rg, dr2 = RHO_W * G_ACC, dr * dr
        for _ in range(4):
            f = [chi * (b2[i] + db2[i] * self.eta[i]) / (2.0 * MU0) for i in range(n)]
            a = [0.0] * n
            b = [0.0] * n
            c = [0.0] * n
            rhs = [0.0] * n
            b[0] = rg + gamma * 4.0 / dr2
            c[0] = -gamma * 4.0 / dr2
            rhs[0] = f[0]
            for i in range(1, n - 1):
                r = i * dr
                a[i] = -gamma * (1.0 / dr2 - 1.0 / (2.0 * r * dr))
                b[i] = rg + gamma * 2.0 / dr2
                c[i] = -gamma * (1.0 / dr2 + 1.0 / (2.0 * r * dr))
                rhs[i] = f[i]
            b[n - 1] = 1.0
            rhs[n - 1] = 0.0
            for i in range(1, n):                       # Thomas
                w = a[i] / b[i - 1]
                b[i] -= w * c[i - 1]
                rhs[i] -= w * rhs[i - 1]
            x = [0.0] * n
            x[n - 1] = rhs[n - 1] / b[n - 1]
            for i in range(n - 2, -1, -1):
                x[i] = (rhs[i] - c[i] * x[i + 1]) / b[i]
            self.eta = x

    def at(self, r):
        """eta(r) [m] and d eta/dr, Catmull-Rom interpolation of the radial grid."""
        r = abs(r)
        t = r / self.dr
        i = int(t)
        if i >= self.n - 2:
            return 0.0, 0.0
        f = t - i
        e = self.eta
        p0 = e[i - 1] if i >= 1 else e[1]
        p1, p2, p3 = e[i], e[i + 1], e[i + 2]
        c0 = p1
        c1 = 0.5 * (p2 - p0)
        c2 = p0 - 2.5 * p1 + 2.0 * p2 - 0.5 * p3
        c3 = -0.5 * p0 + 1.5 * p1 - 1.5 * p2 + 0.5 * p3
        return (c0 + f * (c1 + f * (c2 + f * c3)),
                (c1 + f * (2.0 * c2 + 3.0 * f * c3)) / self.dr)


# ==========================================================================
#  3.  hidden truth of one session
# ==========================================================================
class Truth:
    """Everything the student is not allowed to know."""

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1, 10 ** 9)
        self.seed = int(seed)
        rng = random.Random(self.seed)
        self.rng = rng

        # --- magnet (cylindrical NdFeB, axially magnetised) -----------------
        self.R_mag = rng.uniform(11.6, 12.4) * 1e-3          # radius
        self.L_mag = rng.uniform(16.0, 20.0) * 1e-3          # length
        self.B0_axis = rng.uniform(0.487, 0.513)             # |B| on axis, 1 mm above face
        self.B0_sheet = 0.50                                 # value printed on the problem sheet
        self.Br = remanence_for(self.R_mag, self.L_mag, 1.0e-3, self.B0_axis)
        self.magnet = CylinderMagnet(self.R_mag, self.L_mag, self.Br)

        # --- the liquid ----------------------------------------------------
        #  true volume susceptibility of water at room temperature,
        #  chi = mu - 1 = -9.05e-6, with a small per-session spread
        self.chi = -9.05e-6 * rng.uniform(0.96, 1.22)
        self.gamma = GAMMA_W * rng.uniform(0.97, 1.03)

        # --- optics / geometry (mm unless stated) --------------------------
        self.alpha0 = math.radians(rng.uniform(35.5, 40.5))  # beam angle to horizontal
        self.L0_sheet = 490.0                                # printed value
        self.L0 = self.L0_sheet * rng.uniform(0.995, 1.005)  # real magnet-screen distance
        self.z_rail = 150.0                                  # beam exit height above table
        self.caliper_zero = rng.uniform(100.0, 118.0)         # arbitrary mechanical origin
        self.screen_y0 = rng.uniform(-8.0, 8.0)              # graph-paper origin height offset

        # --- tray / magnet placement --------------------------------------
        self.tray_v = rng.uniform(-8.0, 8.0)     # lateral offset of magnet axis from beam plane
        self.tray_t = rng.uniform(-18.0, 18.0)   # along-beam offset from the black line
        self.depth0 = rng.uniform(0.86, 1.14)    # initial water depth above the magnet [mm]
        # tray: 130 x 100 mm inner, 34 mm inner depth, 3 mm walls, 4 mm floor,
        # standing on the 3 mm support plate.  13 ml <-> 1 mm of level (130*100 mm^2).
        self.tray_inner = (130.0, 100.0)
        self.z_plate = 3.0
        self.z_floor = self.z_plate + 4.0
        self.z_rim = self.z_floor + 34.0
        self.ml_per_mm = 13.0

        # --- noise ---------------------------------------------------------
        self.jitter = rng.uniform(0.03, 0.07)    # mechanical / thermal spot jitter [mm]
        self.eye = rng.uniform(0.03, 0.06)       # reading error on mm paper [mm]
        self.dust = False
        self.noise = random.Random(self.seed ^ 0x5EED)


# ==========================================================================
#  4.  the rig  --  the only public interface of the experiment
# ==========================================================================
PARTS = [
    # id            n   ko                         en                        needs
    ("stand",       1, "스탠드",                   "stand",                  None),
    ("plate",      12, "받침판(검은 기준선)",       "support plate (black line)", "stand"),
    ("tray",        5, "물 트레이 + 자석",          "water tray + magnet",    "plate"),
    ("caliper",     3, "디지털 캘리퍼",            "digital caliper",        "stand"),
    ("laser",       4, "레이저 포인터",            "laser pointer",          "caliper"),
    ("screen",      2, "모눈종이 스크린 + 자석편",  "graph paper + tablets",  "stand"),
    ("tube",       13, "흰 원뿔관",                "white conical tube",     "laser"),
    ("water",      15, "물컵 + 주사기",            "cup of water + syringe", "tray"),
]
CORE = ("stand", "plate", "tray", "caliper", "laser", "screen")


class Rig:
    """The apparatus.  Every method here is something a real student can do or
    read; the GUI and the verification harness use nothing else."""

    def __init__(self, seed=None):
        self.truth = Truth(seed)
        t = self.truth
        self.placed = set()
        self.laser_pressed = False       # button held down by the conical tube
        self.laser_switch = False
        self.caliper_on = True
        self.caliper_inch = False
        self.caliper_offset = 0.0        # ORIGIN button
        self.carriage = t.caliper_zero + 50.0   # true carriage coordinate [mm]
        self.depth = t.depth0            # water depth above the magnet [mm]
        self.tray_v = t.tray_v
        self.tray_t = t.tray_t
        self.water_added = 0.0
        self._cache = {}
        self._surface = None
        self.log = []

    # ------------------------------------------------------------- assembly
    def part_info(self, pid):
        for p in PARTS:
            if p[0] == pid:
                return p
        return None

    def can_place(self, pid):
        p = self.part_info(pid)
        if p is None or pid in self.placed:
            return False
        return p[4] is None or p[4] in self.placed

    def place(self, pid):
        if not self.can_place(pid):
            return False
        self.placed.add(pid)
        if pid == "tube":
            self.laser_pressed = True
        self.log.append("place " + pid)
        return True

    def remove(self, pid):
        if pid not in self.placed:
            return False
        for p in PARTS:                       # cannot remove what carries something else
            if p[4] == pid and p[0] in self.placed:
                return False
        self.placed.discard(pid)
        if pid == "tube":
            self.laser_pressed = False
        return True

    def assembled(self):
        return all(p in self.placed for p in CORE)

    def assembly_status(self):
        if self.assembled():
            return T("조립 완료", "assembly complete")
        miss = [p for p in CORE if p not in self.placed]
        names = [T(self.part_info(m)[2], self.part_info(m)[3]) for m in miss]
        return T("미설치: ", "missing: ") + ", ".join(names)

    # ------------------------------------------------------------ alignment
    def nudge_tray(self, dv=0.0, dt=0.0):
        if "tray" not in self.placed:
            return False
        self.tray_v = max(-25.0, min(25.0, self.tray_v + dv))
        self.tray_t = max(-40.0, min(40.0, self.tray_t + dt))
        return True

    def observe_alignment(self):
        """What the eye sees from above (quantised to the 0.5 mm one can judge)."""
        if "tray" not in self.placed:
            return T("트레이 없음", "no tray")
        ok_v = abs(self.tray_v) < 1.0          # what the eye can judge: about 1 mm
        ok_t = abs(self.tray_t) < 1.0
        return (T("빔면: ", "beam plane: ") + (T("맞아 보인다", "looks aligned") if ok_v else T("어긋나 보인다", "looks off")) +
                T(" / 기준선: ", " / black line: ") + (T("맞아 보인다", "looks aligned") if ok_t else T("어긋나 보인다", "looks off")))

    # ---------------------------------------------------------------- water
    def add_water(self, ml):
        """Syringe: 13 ml raises the level in the tray by 1 mm."""
        if "water" not in self.placed or "tray" not in self.placed:
            return False
        self.depth = max(0.05, min(20.0, self.depth + ml / 13.0))
        self.water_added += ml
        self._surface = None
        return True

    def blow_dust(self):
        self.truth.dust = False

    # -------------------------------------------------------------- caliper
    def set_carriage(self, x_mm):
        lo = self.truth.caliper_zero
        self.carriage = max(lo, min(lo + 150.0, float(x_mm)))

    def move_carriage(self, dx):
        self.set_carriage(self.carriage + dx)

    def caliper_reading(self):
        """Mechanical reading of the caliper in its current unit."""
        v = self.carriage - self.truth.caliper_zero - self.caliper_offset
        return v / 25.4 if self.caliper_inch else v

    def caliper_display(self):
        if not self.caliper_on:
            return ""
        if self.caliper_inch:
            return "%8.4f in" % self.caliper_reading()
        return "%8.2f mm" % self.caliper_reading()

    def caliper_zero_button(self):
        self.caliper_offset = self.carriage - self.truth.caliper_zero

    # -------------------------------------------------------------- surface
    def surface(self):
        key = round(self.depth, 4)
        if self._surface is not None and abs(self._surface.depth * 1e3 - key) < 1e-9:
            return self._surface
        if key in self._cache:
            self._surface = self._cache[key]
            return self._surface
        s = WaterSurface(self.truth.magnet, key * 1e-3, self.truth.chi, self.truth.gamma)
        if len(self._cache) > 24:
            self._cache.clear()
        self._cache[key] = s
        self._surface = s
        return s

    def water_level_z(self):
        """Height of the undisturbed water surface above the table [mm]."""
        t = self.truth
        return t.z_floor + t.L_mag * 1e3 + self.depth

    def freeboard(self):
        """Distance from the water surface up to the tray rim [mm]."""
        return self.truth.z_rim - self.water_level_z()

    # ------------------------------------------------------------ ray trace
    def trace(self):
        """Full geometric ray trace.  Returns a dict describing what is visible:
        hit point, surface height at the hit point, reflected direction, and the
        spot height on the graph paper (None if the beam misses)."""
        t = self.truth
        out = {"ok": False, "reason": "off"}
        if not (self.assembled() and self.laser_on()):
            return out
        zw = self.water_level_z()
        tana = math.tan(t.alpha0)
        # horizontal run from the beam exit down to the (flat) water level
        run = (t.z_rail - zw) / tana
        x_flat = self.carriage - run                     # scene x of the flat-surface hit point
        u = x_flat - self.tray_t                         # distance from the magnet axis, along beam
        S = self.surface()
        uh = u
        for _ in range(4):
            r = math.hypot(uh, self.tray_v) * 1e-3
            e, _d = S.at(r)
            uh = u + e * 1e3 / tana
        r = math.hypot(uh, self.tray_v) * 1e-3
        e, der = S.at(r)
        sig = der * (uh * 1e-3 / r) if r > 1e-9 else 0.0     # d eta / d(beam coordinate)
        x_hit = uh + self.tray_t
        out["x_hit"] = x_hit
        out["u"] = uh
        out["eta_mm"] = e * 1e3
        # inside the tray?
        half = t.tray_inner[0] / 2.0
        if abs(uh) > half or abs(self.tray_v) > t.tray_inner[1] / 2.0:
            out["reason"] = "dry"
            return out
        # too thin a layer over the magnet: the film breaks above the magnet
        if self.depth < 0.30 and abs(uh) < t.R_mag * 1e3 + 4.0:
            out["reason"] = "broken"
            return out
        # the incident beam has to clear the near rim, the reflected one the far rim
        fb = self.freeboard()
        if (half - uh) * tana < fb:
            out["reason"] = "wall_in"
            return out
        ang = t.alpha0 - 2.0 * sig
        if (half + uh) * math.tan(max(ang, 1e-3)) < fb:
            out["reason"] = "wall_out"
            return out
        D = t.L0 + x_hit                                  # horizontal run to the screen
        if D <= 20.0:
            out["reason"] = "geometry"
            return out
        z_spot = zw + e * 1e3 + D * math.tan(ang)
        out.update(ok=True, reason="", z_spot=z_spot, angle=ang, D=D, x_screen=-t.L0)
        return out

    def laser_on(self):
        return self.laser_switch and self.laser_pressed

    def set_laser(self, on):
        self.laser_switch = bool(on)

    # ------------------------------------------------------------- the spot
    def spot_y(self, noisy=True):
        """True height of the spot on the graph paper [mm], measured from the
        paper origin, or None when there is no spot on the paper."""
        tr = self.trace()
        if not tr["ok"]:
            return None
        y = tr["z_spot"] - PAPER_Z0 - self.truth.screen_y0
        if noisy:
            y += self.truth.noise.gauss(0.0, self.truth.jitter)
        if y < 0.0 or y > PAPER_H:               # sheet of graph paper on the vertical plate
            return None
        return y

    def read_spot(self):
        """What the experimenter writes down after reading the mm paper."""
        y = self.spot_y()
        if y is None:
            tr = self.trace()
            if not self.assembled():
                return T("조립이 끝나지 않았다", "setup incomplete")
            if not self.laser_on():
                return T("레이저 꺼짐", "laser off")
            if tr.get("reason") == "dry":
                return T("빔이 물 밖(트레이 벽/바닥)을 맞음", "beam misses the water")
            if tr.get("reason") in ("wall_in", "wall_out"):
                return T("빔이 트레이 벽에 막힘", "beam blocked by the tray wall")
            if tr.get("reason") == "broken":
                return T("자석 위 물이 갈라졌다 (수심 부족)", "the film over the magnet has broken")
            return T("스크린 밖 - 점이 보이지 않음", "spot off the screen")
        e = self.truth.eye
        if self.truth.dust:
            e *= 4.0
        y += self.truth.noise.gauss(0.0, e)
        return "y = %.1f mm" % (round(y * 10.0) / 10.0)

    def read_spot_value(self):
        s = self.read_spot()
        if s.startswith("y ="):
            return float(s.split("=")[1].split("mm")[0])
        return None

    # ------------------------------------------- qualitative surface shape
    def reflection_profile(self, npts=61, span=45.0):
        """Apparent lateral displacement [mm] of the mirror image of a straight
        edge held above the tray - this is what part A is observed with."""
        S = self.surface()
        out = []
        for i in range(npts):
            u = -span + 2.0 * span * i / (npts - 1)
            r = math.hypot(u, self.tray_v) * 1e-3
            e, der = S.at(r)
            sig = der * (u * 1e-3 / r) if r > 1e-9 else 0.0
            out.append((u, e * 1e3, sig))
        return out


# ==========================================================================
#  5.  drawing helpers
# ==========================================================================
COL_BG = "#101418"
COL_PANEL = "#1a2026"
COL_TXT = "#e8eef2"
COL_TABLE = "#cfc7ae"
COL_STAND = "#3d4a52"
COL_RAIL = "#5b7183"
COL_TRAY = "#2b2f33"
COL_WATER = "#2f6f9e"
COL_MAG = "#1b1d1f"
COL_BEAM = "#ff2b3c"
COL_PAPER = "#f4f1e4"
COL_GRID = "#9aa38c"
COL_ACC = "#7fd1ff"


class View:
    """mm <-> pixel mapping for a side/top view canvas."""

    def __init__(self, canvas, scale=1.0, ox=0.0, oz=0.0, flip=True):
        self.c, self.s, self.ox, self.oz, self.flip = canvas, scale, ox, oz, flip

    def px(self, x, z):
        w = int(self.c["width"])
        h = int(self.c["height"])
        X = w * 0.5 + (x - self.ox) * self.s
        Y = (h * 0.5 - (z - self.oz) * self.s) if self.flip else (h * 0.5 + (z - self.oz) * self.s)
        return X, Y

    def line(self, x1, z1, x2, z2, **kw):
        a = self.px(x1, z1)
        b = self.px(x2, z2)
        return self.c.create_line(a[0], a[1], b[0], b[1], **kw)

    def rect(self, x1, z1, x2, z2, **kw):
        a = self.px(x1, z1)
        b = self.px(x2, z2)
        return self.c.create_rectangle(a[0], a[1], b[0], b[1], **kw)

    def oval(self, x1, z1, x2, z2, **kw):
        a = self.px(x1, z1)
        b = self.px(x2, z2)
        return self.c.create_oval(a[0], a[1], b[0], b[1], **kw)

    def text(self, x, z, txt, **kw):
        a = self.px(x, z)
        return self.c.create_text(a[0], a[1], text=txt, **kw)


# ==========================================================================
#  6.  the application
# ==========================================================================
class App(tk.Tk):
    def __init__(self, seed=None):
        super().__init__()
        self.rig = Rig(seed)
        self.title("%s  -  %s [seed %d]" % (APP_TITLE,
                   T("물의 자기투자율", "magnetic permeability of water"), self.rig.truth.seed))
        self.configure(bg=COL_BG)
        self.geometry("1330x850")
        self.minsize(1100, 720)
        self.zoom = 1.0
        self.pan = [0.0, 0.0]
        self.paper_zoom = 4.0
        self.paper_center = 90.0
        self.status = tk.StringVar(value=T("부품을 설치하십시오.", "install the parts."))
        self.reading = tk.StringVar(value="--")
        self._drag = None
        self._build_style()
        self._build()
        self.after(120, self._tick)

    # ------------------------------------------------------------------ ui
    def _build_style(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TNotebook", background=COL_BG, borderwidth=0)
        st.configure("TNotebook.Tab", background=COL_PANEL, foreground=COL_TXT,
                     padding=(18, 8), font=("TkDefaultFont", 11, "bold"))
        st.map("TNotebook.Tab", background=[("selected", "#2b3a45")])
        st.configure("TFrame", background=COL_BG)
        st.configure("P.TFrame", background=COL_PANEL)
        st.configure("TLabel", background=COL_PANEL, foreground=COL_TXT)
        st.configure("H.TLabel", background=COL_PANEL, foreground=COL_ACC,
                     font=("TkDefaultFont", 10, "bold"))
        st.configure("TButton", padding=3)
        st.configure("TLabelframe", background=COL_PANEL, foreground=COL_ACC)
        st.configure("TLabelframe.Label", background=COL_PANEL, foreground=COL_ACC,
                     font=("TkDefaultFont", 10, "bold"))

    def _build(self):
        top = tk.Frame(self, bg=COL_BG)
        top.pack(fill="x", padx=8, pady=(6, 0))
        tk.Label(top, text="IPhO 2012  E1 · " + T("물의 자기투자율", "Magnetic permeability of water"),
                 bg=COL_BG, fg=COL_ACC, font=("TkDefaultFont", 13, "bold")).pack(side="left")
        tk.Label(top, textvariable=self.status, bg=COL_BG, fg="#b9c6cf").pack(side="right")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=6)
        self.tab_asm = ttk.Frame(self.nb)
        self.tab_bench = ttk.Frame(self.nb)
        self.nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        self.nb.add(self.tab_bench, text=T(" 실험대 ", " Bench "))
        self._build_assembly(self.tab_asm)
        self._build_bench(self.tab_bench)

    # -------------------------------------------------------- assembly tab
    def _build_assembly(self, root):
        left = tk.Frame(root, bg=COL_BG)
        left.pack(side="left", fill="both", expand=True)
        self.ca = tk.Canvas(left, width=880, height=470, bg=COL_BG, highlightthickness=0)
        self.ca.pack(fill="both", expand=True, padx=(0, 6), pady=(0, 4))
        self.ct = tk.Canvas(left, width=880, height=250, bg=COL_BG, highlightthickness=0)
        self.ct.pack(fill="x", padx=(0, 6))

        right = tk.Frame(root, bg=COL_PANEL, width=380)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        box = ttk.Labelframe(right, text=T(" 부품 상자 ", " parts box "))
        box.pack(fill="x", padx=8, pady=8)
        self.part_rows = {}
        for pid, num, ko, en in [(p[0], p[1], p[2], p[3]) for p in PARTS]:
            row = tk.Frame(box, bg=COL_PANEL)
            row.pack(fill="x", pady=1)
            lb = tk.Label(row, text="%2d" % num, width=3, bg="#33414c", fg="#ffe08a",
                          font=("TkFixedFont", 10, "bold"))
            lb.pack(side="left", padx=(2, 6))
            nm = tk.Label(row, text=T(ko, en), bg=COL_PANEL, fg=COL_TXT, anchor="w", width=22)
            nm.pack(side="left")
            b = ttk.Button(row, text=T("설치", "install"), width=6,
                           command=lambda p=pid: self.do_place(p))
            b.pack(side="right", padx=2)
            self.part_rows[pid] = (nm, b)

        al = ttk.Labelframe(right, text=T(" 정렬 (자석축 = 빔 · 기준선) ",
                                          " alignment (magnet axis = beam · line) "))
        al.pack(fill="x", padx=8, pady=6)
        g = tk.Frame(al, bg=COL_PANEL)
        g.pack(pady=4)
        for i, (lab, dv, dt) in enumerate([("◀ 2", -2, 0), ("◀ .5", -0.5, 0),
                                           (".5 ▶", 0.5, 0), ("2 ▶", 2, 0)]):
            ttk.Button(g, text=lab, width=5,
                       command=lambda a=dv, b=dt: self.do_nudge(a, b)).grid(row=0, column=i, padx=1)
        for i, (lab, dv, dt) in enumerate([("▲ 2", 0, 2), ("▲ .5", 0, 0.5),
                                           (".5 ▼", 0, -0.5), ("2 ▼", 0, -2)]):
            ttk.Button(g, text=lab, width=5,
                       command=lambda a=dv, b=dt: self.do_nudge(a, b)).grid(row=1, column=i, padx=1)
        self.lab_align = tk.Label(al, text="", bg=COL_PANEL, fg="#ffd479", font=("TkFixedFont", 9))
        self.lab_align.pack(pady=(2, 4))

        wf = ttk.Labelframe(right, text=T(" 물 높이 (주사기 13 ml = 1 mm) ",
                                          " water level (13 ml = 1 mm) "))
        wf.pack(fill="x", padx=8, pady=6)
        g2 = tk.Frame(wf, bg=COL_PANEL)
        g2.pack(pady=4)
        for i, ml in enumerate((-13, -6.5, -1.3, 1.3, 6.5, 13)):
            ttk.Button(g2, text="%+.1f ml" % ml, width=8,
                       command=lambda m=ml: self.do_water(m)).grid(row=i // 3, column=i % 3, padx=1, pady=1)
        self.lab_water = tk.Label(wf, text="", bg=COL_PANEL, fg="#bfe6ff",
                                  font=("TkFixedFont", 9), justify="left")
        self.lab_water.pack(pady=(2, 4))
        ttk.Button(wf, text=T("수면 먼지 불어내기", "blow dust off the surface"),
                   command=self.rig.blow_dust).pack(pady=(0, 5))

        info = tk.Label(right, bg=COL_PANEL, fg="#93a4ae", justify="left", anchor="w",
                        font=("TkDefaultFont", 9),
                        text=T("주어진 값\n  L₀ = 490 mm (자석 중심–스크린)\n  B₀ = 0.50 T (평면에서 1 mm)\n"
                               "  ρ = 1000 kg/m³,  g = 9.8 m/s²\n  μ₀ = 4π×10⁻⁷ H/m\n\n"
                               "· 자석 위 물 두께는 1 mm 근처로 맞춰져 있다\n"
                               "· 레이저는 원뿔관으로 눌러 켠다\n"
                               "· 불확도 평가는 요구되지 않는다",
                               "given\n  L₀ = 490 mm (magnet centre - screen)\n  B₀ = 0.50 T (1 mm above face)\n"
                               "  ρ = 1000 kg/m³,  g = 9.8 m/s²\n  μ₀ = 4π×10⁻⁷ H/m\n\n"
                               "· water above the magnet is preset near 1 mm\n"
                               "· the conical tube holds the laser button\n"
                               "· no uncertainty estimation is required"))
        info.pack(fill="x", padx=10, pady=8)

    # ----------------------------------------------------------- bench tab
    def _build_bench(self, root):
        left = tk.Frame(root, bg=COL_BG)
        left.pack(side="left", fill="both", expand=True)
        self.cb = tk.Canvas(left, width=900, height=720, bg=COL_BG, highlightthickness=0)
        self.cb.pack(fill="both", expand=True, padx=(0, 6))
        self.cb.bind("<MouseWheel>", self._wheel_bench)
        self.cb.bind("<Button-4>", lambda e: self._wheel_bench(e, 1))
        self.cb.bind("<Button-5>", lambda e: self._wheel_bench(e, -1))
        self.cb.bind("<ButtonPress-1>", self._press)
        self.cb.bind("<B1-Motion>", self._drag_move)
        self.cb.bind("<ButtonRelease-1>", lambda e: setattr(self, "_drag", None))

        right = tk.Frame(root, bg=COL_PANEL, width=410)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # --- caliper -------------------------------------------------------
        cf = ttk.Labelframe(right, text=T(" 디지털 캘리퍼 (3) ", " digital caliper (3) "))
        cf.pack(fill="x", padx=8, pady=(8, 4))
        self.lcd = tk.Label(cf, text="", bg="#b9c9a8", fg="#16211a", width=13,
                            font=("TkFixedFont", 22, "bold"), anchor="e", padx=6)
        self.lcd.pack(pady=(6, 4))
        r1 = tk.Frame(cf, bg=COL_PANEL)
        r1.pack()
        ttk.Button(r1, text=T("ON/OFF (8)", "ON/OFF (8)"), width=11,
                   command=self.do_power).pack(side="left", padx=2)
        ttk.Button(r1, text="mm/inch (10)", width=11, command=self.do_unit).pack(side="left", padx=2)
        ttk.Button(r1, text="ORIGIN (9)", width=10, command=self.do_origin).pack(side="left", padx=2)
        r2 = tk.Frame(cf, bg=COL_PANEL)
        r2.pack(pady=5)
        for lab, d in (("◀◀", -5.0), ("◀", -1.0), ("◀·", -0.1),
                       ("·▶", 0.1), ("▶", 1.0), ("▶▶", 5.0)):
            ttk.Button(r2, text=lab, width=4,
                       command=lambda dd=d: self.do_move(dd)).pack(side="left", padx=1)
        self.sld = tk.Scale(cf, from_=0.0, to=150.0, resolution=0.01, orient="horizontal",
                            bg=COL_PANEL, fg=COL_TXT, troughcolor="#0d1216",
                            highlightthickness=0, showvalue=False, length=360,
                            command=self.do_slider)
        self.sld.pack(pady=(0, 6))
        tk.Label(cf, text=T("스크롤: 0.1 mm · Shift+스크롤: 0.01 mm (캔버스 위)",
                            "wheel: 0.1 mm · Shift+wheel: 0.01 mm (over canvas)"),
                 bg=COL_PANEL, fg="#8fa0ab", font=("TkDefaultFont", 8)).pack()

        # --- laser ---------------------------------------------------------
        lf = ttk.Labelframe(right, text=T(" 레이저 포인터 (4) ", " laser pointer (4) "))
        lf.pack(fill="x", padx=8, pady=4)
        self.laser_var = tk.IntVar(value=0)
        tk.Checkbutton(lf, text=T("레이저 ON", "laser ON"), variable=self.laser_var,
                       command=self.do_laser, bg=COL_PANEL, fg=COL_TXT,
                       selectcolor="#0d1216", activebackground=COL_PANEL,
                       activeforeground=COL_TXT).pack(side="left", padx=8, pady=4)
        self.lab_laser = tk.Label(lf, text="", bg=COL_PANEL, fg="#ff9a9a",
                                  font=("TkDefaultFont", 9))
        self.lab_laser.pack(side="left")

        # --- screen --------------------------------------------------------
        sf = ttk.Labelframe(right, text=T(" 모눈종이 스크린 (2) ", " graph paper screen (2) "))
        sf.pack(fill="both", expand=True, padx=8, pady=4)
        self.cp = tk.Canvas(sf, width=380, height=300, bg="#20262b", highlightthickness=0)
        self.cp.pack(padx=4, pady=4, fill="both", expand=True)
        self.cp.bind("<MouseWheel>", self._wheel_paper)
        self.cp.bind("<Button-4>", lambda e: self._wheel_paper(e, 1))
        self.cp.bind("<Button-5>", lambda e: self._wheel_paper(e, -1))
        rr = tk.Frame(sf, bg=COL_PANEL)
        rr.pack(fill="x", pady=(0, 4))
        ttk.Button(rr, text=T("눈금 판독", "read the paper"), width=12,
                   command=self.do_read).pack(side="left", padx=4)
        tk.Label(rr, textvariable=self.reading, bg=COL_PANEL, fg="#ffe08a",
                 font=("TkFixedFont", 14, "bold")).pack(side="left", padx=6)
        ttk.Button(rr, text=T("수면 반사 관찰", "observe reflection"), width=14,
                   command=self.open_reflection).pack(side="right", padx=4)

        nf = ttk.Labelframe(right, text=T(" 관측 노트 ", " notebook "))
        nf.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.notes = tk.Text(nf, height=7, bg="#0d1216", fg=COL_TXT, insertbackground=COL_TXT,
                             font=("TkFixedFont", 9), wrap="none")
        self.notes.pack(fill="both", expand=True, padx=4, pady=4)

    # ------------------------------------------------------------- actions
    def do_place(self, pid):
        if self.rig.place(pid):
            self.status.set(T("설치: ", "installed: ") +
                            T(self.rig.part_info(pid)[2], self.rig.part_info(pid)[3]))
        else:
            p = self.rig.part_info(pid)
            if pid in self.rig.placed:
                self.status.set(T("이미 설치되어 있다.", "already installed."))
            else:
                need = self.rig.part_info(p[4])
                self.status.set(T("먼저 %s 를 설치해야 한다.", "install %s first.")
                                % T(need[2], need[3]))
        self.refresh()

    def do_nudge(self, dv, dt):
        if not self.rig.nudge_tray(dv, dt):
            self.status.set(T("트레이가 없다.", "no tray."))
        self.refresh()

    def do_water(self, ml):
        if not self.rig.add_water(ml):
            self.status.set(T("물컵/주사기와 트레이가 필요하다.", "need tray, cup and syringe."))
        elif self.rig.freeboard() < 1.0:
            self.status.set(T("트레이가 거의 넘친다 - 빔이 벽에 막힐 수 있다.",
                              "the tray is nearly overflowing."))
        self.refresh()

    def do_power(self):
        self.rig.caliper_on = not self.rig.caliper_on
        self.refresh()

    def do_unit(self):
        self.rig.caliper_inch = not self.rig.caliper_inch
        self.refresh()

    def do_origin(self):
        self.rig.caliper_zero_button()
        self.refresh()

    def do_move(self, d):
        self.rig.move_carriage(d)
        self.refresh()

    def do_slider(self, v):
        if getattr(self, "_sync", False):
            return
        lo = self.rig.truth.caliper_zero
        self.rig.set_carriage(lo + float(v))
        self.refresh()

    def do_laser(self):
        self.rig.set_laser(bool(self.laser_var.get()))
        self.refresh()

    def do_read(self):
        self.reading.set(self.rig.read_spot())
        self.refresh()

    # ------------------------------------------------------------- events
    def _wheel_bench(self, e, direction=None):
        d = direction if direction is not None else (1 if e.delta > 0 else -1)
        if getattr(e, "state", 0) & 0x0004:                # ctrl -> zoom
            self.zoom = max(0.35, min(14.0, self.zoom * (1.12 ** d)))
        elif getattr(e, "state", 0) & 0x0001:              # shift -> fine move
            self.rig.move_carriage(0.01 * d)
        else:
            self.rig.move_carriage(0.1 * d)
        self.refresh()

    def _wheel_paper(self, e, direction=None):
        d = direction if direction is not None else (1 if e.delta > 0 else -1)
        self.paper_zoom = max(0.9, min(9.0, self.paper_zoom * (1.15 ** d)))
        self.refresh()

    def _press(self, e):
        self._drag = (e.x, e.y, self.pan[0], self.pan[1])

    def _drag_move(self, e):
        if self._drag:
            x0, y0, p0, p1 = self._drag
            self.pan = [p0 - (e.x - x0) / self.zoom, p1 + (e.y - y0) / self.zoom]
            self.refresh()

    def _tick(self):
        if not self.winfo_exists():
            return
        self.refresh()
        self.after(700, self._tick)

    # ------------------------------------------------------------ redraw
    def refresh(self):
        r = self.rig
        for pid, (nm, b) in self.part_rows.items():
            done = pid in r.placed
            nm.configure(fg="#7ee08a" if done else COL_TXT)
            b.configure(text=T("설치됨", "done") if done else T("설치", "install"))
        self.lab_align.configure(text=r.observe_alignment())
        self.lab_water.configure(text=T("주사기로 넣은 물 누계 %+.1f ml",
                                        "water added with the syringe %+.1f ml")
                                 % r.water_added)
        self.lcd.configure(text=r.caliper_display())
        lo = r.truth.caliper_zero
        if abs(self.sld.get() - (r.carriage - lo)) > 0.02:
            self._sync = True
            self.sld.set(r.carriage - lo)
            self._sync = False
        if not r.laser_pressed:
            self.lab_laser.configure(text=T("버튼이 눌려 있지 않다 (13번 필요)",
                                            "button not held (part 13)"))
        elif r.laser_on():
            self.lab_laser.configure(text=T("빔 조사 중", "beam on"))
        else:
            self.lab_laser.configure(text="")
        self.draw_scene(self.ca, View(self.ca, 0.0, 0.0, 0.0), assembly=True)
        self.draw_top(self.ct)
        self.draw_scene(self.cb, None, assembly=False)
        self.draw_paper(self.cp)

    # --------------------------------------------------------- side view
    def draw_scene(self, c, _v, assembly):
        c.delete("all")
        r = self.rig
        t = r.truth
        w = c.winfo_width() or int(c["width"])
        h = c.winfo_height() or int(c["height"])
        c.configure(width=w, height=h)
        if assembly:
            s = min(w / 900.0, h / 580.0)
            ox, oz = -80.0, 240.0
        else:
            s = self.zoom * min(w / 900.0, h / 580.0)
            ox, oz = -80.0 + self.pan[0], 240.0 + self.pan[1]
        v = View(c, s, ox, oz)
        v.c = c

        # table
        v.rect(-700, -40, 400, 0, fill=COL_TABLE, outline="")
        # stand
        if "stand" in r.placed:
            v.rect(-505, 0, -470, 500, fill=COL_STAND, outline="#22292e")     # vertical plate
            v.rect(215, 0, 245, 152, fill=COL_STAND, outline="#22292e")       # post
            v.rect(-505, -6, 260, 4, fill="#46545d", outline="")              # base bar
            v.rect(-500, 140, 250, 152, fill=COL_RAIL, outline="#2a343b")     # top rail
        if "plate" in r.placed:
            v.rect(-90, 0, 150, t.z_plate, fill="#e9e6dc", outline="#b7b3a4")
            v.line(0, t.z_plate + 0.4, 0, t.z_plate + 0.4, fill="#111")
            a = v.px(0, t.z_plate)
            c.create_line(a[0], a[1] - 1, a[0], a[1] + 1, fill="#111")
            v.text(0, -12, T("기준선 12", "line 12"), fill="#5b5b52",
                   font=("TkDefaultFont", 7))
        # tray + magnet + water
        if "tray" in r.placed:
            x0 = r.tray_t - t.tray_inner[0] / 2.0 - 3.0
            x1 = r.tray_t + t.tray_inner[0] / 2.0 + 3.0
            v.rect(x0, t.z_plate, x1, t.z_rim, fill="", outline="#0d0f10")
            v.rect(x0, t.z_plate, x0 + 3, t.z_rim, fill=COL_TRAY, outline="")
            v.rect(x1 - 3, t.z_plate, x1, t.z_rim, fill=COL_TRAY, outline="")
            v.rect(x0, t.z_plate, x1, t.z_floor, fill=COL_TRAY, outline="")
            zw = r.water_level_z()
            v.rect(x0 + 3, t.z_floor, x1 - 3, zw, fill=COL_WATER, outline="", stipple="gray50")
            v.line(x0 + 3, zw, x1 - 3, zw, fill="#9fd8ff")
            mr = t.R_mag * 1e3
            v.rect(r.tray_t - mr, t.z_floor, r.tray_t + mr, t.z_floor + t.L_mag * 1e3,
                   fill=COL_MAG, outline="#3a3f44")
            v.oval(r.tray_t - mr, t.z_floor + t.L_mag * 1e3 - 2.2,
                   r.tray_t + mr, t.z_floor + t.L_mag * 1e3 + 2.2, fill="#26292c", outline="#4a5055")
            v.text(r.tray_t, t.z_floor + t.L_mag * 1e3 * 0.5, "7", fill="#8b949b",
                   font=("TkDefaultFont", 8, "bold"))
        # caliper + laser
        if "caliper" in r.placed:
            v.rect(-30, 152, 300, 168, fill="#2f5f8a", outline="#1d3b57")
            for k in range(0, 160, 10):
                xx = t.caliper_zero + k
                v.line(xx, 168, xx, 172 if k % 50 else 176, fill="#dfe8ee")
            v.rect(r.carriage - 26, 150, r.carriage + 26, 186, fill="#3b6f9e", outline="#1d3b57")
            v.rect(r.carriage - 22, 158, r.carriage + 22, 180, fill="#b9c9a8", outline="")
            v.text(r.carriage, 169, r.caliper_display().strip(), fill="#16211a",
                   font=("TkFixedFont", 7, "bold"))
        if "laser" in r.placed:
            ln = 42.0
            ca, sa = math.cos(t.alpha0), math.sin(t.alpha0)
            x2, z2 = r.carriage, t.z_rail
            x1, z1 = x2 + ln * ca, z2 + ln * sa
            a = v.px(x1, z1)
            b = v.px(x2, z2)
            c.create_line(a[0], a[1], b[0], b[1], fill="#101418", width=max(3, int(9 * s)),
                          capstyle="round")
            c.create_line(a[0], a[1], b[0], b[1], fill="#2b3138", width=max(2, int(6 * s)),
                          capstyle="round")
            if "tube" in r.placed:
                mx, mz = x2 + 20 * ca, z2 + 20 * sa
                a2 = v.px(mx + 16 * ca, mz + 16 * sa)
                b2 = v.px(mx - 10 * ca, mz - 10 * sa)
                c.create_line(a2[0], a2[1], b2[0], b2[1], fill="#f2f2ee",
                              width=max(3, int(12 * s)), capstyle="round")
        # screen
        if "screen" in r.placed:
            v.rect(-503, PAPER_Z0, -468, PAPER_Z0 + PAPER_H, fill=COL_PAPER, outline="#b5ae94")
            for k in range(0, int(PAPER_H) + 1, 10):
                v.line(-503, PAPER_Z0 + k, -468, PAPER_Z0 + k, fill=COL_GRID)
            v.text(-486, PAPER_Z0 + PAPER_H + 12, "2", fill="#93a4ae",
                   font=("TkDefaultFont", 8, "bold"))
        # cup + syringe
        if "water" in r.placed:
            v.rect(300, 0, 340, 40, fill="#dfe9ef", outline="#9fb0bb")
            v.rect(300, 4, 340, 26, fill="#9ed0ef", outline="", stipple="gray50")
            v.rect(255, 2, 295, 10, fill="#cfe8f5", outline="#8fb6c9")
        # beam
        tr = r.trace()
        if r.laser_on() and "laser" in r.placed:
            ca, sa = math.cos(t.alpha0), math.sin(t.alpha0)
            zw = r.water_level_z()
            if tr["ok"] or tr.get("reason") in ("dry", "wall_in", "wall_out"):
                xh = tr.get("x_hit", r.carriage - (t.z_rail - zw) / math.tan(t.alpha0))
                v.line(r.carriage, t.z_rail, xh, zw + tr.get("eta_mm", 0.0),
                       fill=COL_BEAM, width=2)
                if tr["ok"]:
                    v.line(xh, zw + tr["eta_mm"], -t.L0, tr["z_spot"], fill=COL_BEAM, width=2)
                    a = v.px(-t.L0, tr["z_spot"])
                    c.create_oval(a[0] - 4, a[1] - 4, a[0] + 4, a[1] + 4,
                                  fill="#ff5566", outline="#ffd0d5")
        # annotation
        if not assembly:
            c.create_text(10, 10, anchor="nw", fill="#7d8f9b", font=("TkDefaultFont", 9),
                          text=T("드래그: 이동 · Ctrl+스크롤: 확대 · 스크롤: 캘리퍼 0.1 mm",
                                 "drag: pan · Ctrl+wheel: zoom · wheel: caliper 0.1 mm"))
            if tr.get("reason") in ("wall_in", "wall_out"):
                c.create_text(w / 2, 26, fill="#ff9a9a", font=("TkDefaultFont", 10, "bold"),
                              text=T("빔이 트레이 벽에 막혔다", "beam blocked by the tray wall"))
            elif tr.get("reason") == "dry":
                c.create_text(w / 2, 26, fill="#ff9a9a", font=("TkDefaultFont", 10, "bold"),
                              text=T("빔이 수면 밖을 맞는다", "beam misses the water surface"))
        else:
            c.create_text(10, 10, anchor="nw", fill="#7d8f9b", font=("TkDefaultFont", 9),
                          text=T("측면도 - 부품을 순서대로 설치하십시오",
                                 "side view - install the parts in order"))

    # ---------------------------------------------------------- top view
    def draw_top(self, c):
        c.delete("all")
        r = self.rig
        t = r.truth
        w = c.winfo_width() or int(c["width"])
        h = c.winfo_height() or int(c["height"])
        s = min(w / 240.0, h / 150.0)
        cx, cy = w * 0.5, h * 0.55

        def P(x, y):
            return cx + x * s, cy - y * s
        c.create_text(10, 8, anchor="nw", fill="#7d8f9b", font=("TkDefaultFont", 9),
                      text=T("위에서 본 모습 - 자석 축을 빔(붉은 선)과 기준선(검은 선)에 맞춘다",
                             "top view - bring the magnet axis onto the beam and the black line"))
        if "plate" in r.placed:
            a, b = P(-100, -55), P(120, 55)
            c.create_rectangle(a[0], a[1], b[0], b[1], fill="#e9e6dc", outline="#b7b3a4")
            hy = t.tray_inner[1] / 2.0 + 3 if "tray" in r.placed else 0.0
            for y1, y2 in ((-55, -hy), (hy, 55)):
                a, b = P(0, y1), P(0, y2)
                c.create_line(a[0], a[1], b[0], b[1], fill="#111", width=2)
            for yy in (-55, 55):
                a = P(0, yy)
                c.create_text(a[0], a[1] + (10 if yy < 0 else -10), text="12",
                              fill="#5b5b52", font=("TkDefaultFont", 7))
        if "tray" in r.placed:
            hx, hy = t.tray_inner[0] / 2.0 + 3, t.tray_inner[1] / 2.0 + 3
            a, b = P(r.tray_t - hx, -hy), P(r.tray_t + hx, hy)
            c.create_rectangle(a[0], a[1], b[0], b[1], fill=COL_TRAY, outline="#0d0f10")
            a, b = P(r.tray_t - hx + 3, -hy + 3), P(r.tray_t + hx - 3, hy - 3)
            c.create_rectangle(a[0], a[1], b[0], b[1], fill="#25506e", outline="")
            mr = t.R_mag * 1e3
            a, b = P(r.tray_t - mr, -mr), P(r.tray_t + mr, mr)
            c.create_oval(a[0], a[1], b[0], b[1], fill=COL_MAG, outline="#4a5055")
            a = P(r.tray_t, 0)
            c.create_line(a[0] - 4, a[1], a[0] + 4, a[1], fill="#ffd479")
            c.create_line(a[0], a[1] - 4, a[0], a[1] + 4, fill="#ffd479")
        # beam plane (y = tray_v is where the magnet axis sits relative to it)
        a, b = P(-100, -r.tray_v), P(120, -r.tray_v)
        c.create_line(a[0], a[1], b[0], b[1], fill=COL_BEAM, width=1, dash=(4, 3))
        tr = r.trace()
        if tr.get("ok") or tr.get("reason") in ("dry",):
            a = P(tr.get("x_hit", 0.0), -r.tray_v)
            c.create_oval(a[0] - 3, a[1] - 3, a[0] + 3, a[1] + 3, fill="#ff5566", outline="")

    # -------------------------------------------------------- graph paper
    def draw_paper(self, c):
        c.delete("all")
        r = self.rig
        w = c.winfo_width() or int(c["width"])
        h = c.winfo_height() or int(c["height"])
        s = self.paper_zoom
        y = r.spot_y(noisy=False)
        if y is not None:
            self.paper_center = y
        yc = self.paper_center
        x0 = w * 0.5

        def P(xx, yy):
            return x0 + xx * s, h * 0.5 - (yy - yc) * s
        # paper
        a, b = P(-PAPER_W / 2, 0), P(PAPER_W / 2, PAPER_H)
        c.create_rectangle(a[0], a[1], b[0], b[1], fill=COL_PAPER, outline="#b5ae94")
        ymin = max(0.0, yc - h / (2 * s) - 2)
        ymax = min(PAPER_H, yc + h / (2 * s) + 2)
        k = int(ymin)
        while k <= ymax:
            col, wd = ("#c8cbb4", 1) if k % 5 else ("#a7ad90", 1)
            if k % 10 == 0:
                col, wd = "#6f7a5f", 2
            a, b = P(-PAPER_W / 2, k), P(PAPER_W / 2, k)
            c.create_line(a[0], a[1], b[0], b[1], fill=col, width=wd)
            if k % 10 == 0:
                c.create_text(a[0] + 6, a[1] - 7, text="%d" % k, fill="#6f7a5f",
                              anchor="w", font=("TkDefaultFont", 7))
            k += 1
        xx = -PAPER_W / 2
        while xx <= PAPER_W / 2 + 1e-9:
            col, wd = ("#c8cbb4", 1) if int(round(xx)) % 5 else ("#a7ad90", 1)
            if int(round(xx)) % 10 == 0:
                col, wd = "#6f7a5f", 2
            a, b = P(xx, ymin), P(xx, ymax)
            c.create_line(a[0], a[1], b[0], b[1], fill=col, width=wd)
            xx += 1.0
        if y is None:
            c.create_text(w / 2, 14, fill="#ff9a9a", font=("TkDefaultFont", 10, "bold"),
                          text=T("점이 보이지 않는다", "no spot visible"))
        else:
            a = P(0.0, y)
            rr = max(2.0, 0.9 * s)
            for i, cl in ((2.6, "#ff8a95"), (1.8, "#ff4d5e"), (1.0, "#fff0f0")):
                c.create_oval(a[0] - rr * i, a[1] - rr * i, a[0] + rr * i, a[1] + rr * i,
                              fill=cl, outline="")
            if self.rig.truth.dust:
                c.create_text(w / 2, h - 12, fill="#ffd479", font=("TkDefaultFont", 9),
                              text=T("점이 번져 있다 - 수면 먼지", "spot smeared - dust"))
        c.create_text(6, h - 10, anchor="w", fill="#8fa0ab", font=("TkDefaultFont", 8),
                      text=T("스크롤: 확대", "wheel: zoom"))

    # ------------------------------------------------- reflection window
    def open_reflection(self):
        if not ("tray" in self.rig.placed and "water" in self.rig.placed):
            self.status.set(T("트레이에 물이 있어야 한다.", "the tray must hold water."))
            return
        win = tk.Toplevel(self)
        win.title(T("수면 반사 관찰 (Part A)", "reflection on the water surface (part A)"))
        win.configure(bg=COL_BG)
        c = tk.Canvas(win, width=680, height=380, bg="#0b0e11", highlightthickness=0)
        c.pack(padx=8, pady=8)
        tk.Label(win, bg=COL_BG, fg="#93a4ae", font=("TkDefaultFont", 9),
                 text=T("종이의 곧은 모서리를 수면에 비춰 본 모습. 상의 휘어짐이 수면 기울기를 보여준다.",
                        "mirror image of the straight edge of a sheet of paper in the water surface.")
                 ).pack(pady=(0, 8))
        prof = self.rig.reflection_profile(121, 48.0)
        for j in range(9):
            pts = []
            for (u, e, sig) in prof:
                base = 40.0 + j * 38.0
                pts.extend([340 + u * 6.4, base - sig * 5200.0 - e * 1e3 * 0.0])
            c.create_line(*pts, fill="#7fd1ff" if j % 2 == 0 else "#4a90b8", width=2, smooth=True)
        c.create_text(340, 366, fill="#5f7480", font=("TkDefaultFont", 9),
                      text=T("트레이 폭 방향 위치 (자석 중심 = 화면 중앙)",
                             "position across the tray (magnet centre = middle)"))


    def destroy(self):
        try:                                   # cancel any pending timers first
            for aid in self.tk.call("after", "info"):
                try:
                    self.after_cancel(aid)
                except Exception:
                    pass
        except Exception:
            pass
        tk.Tk.destroy(self)

def main():
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=")[1])
    App(seed).mainloop()


if __name__ == "__main__":
    main()
