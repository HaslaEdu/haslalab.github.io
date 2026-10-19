#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  7th European Physics Olympiad  (EuPhO 2023, Hannover, Germany)
  Experimental Problem E2 :  OPTICAL BLACK-BOX
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Apparatus rebuilt from the photographs of the problem sheet: the
    sealed plywood box with ports A-D, the laser in its mount with a
    wheel, the transparent block, the mm paper with a diagonal scale,
    masking tape, pencil and ruler.  Two tabs only: Setup and Bench.
    The inside of the box is never drawn.  Only what can be seen and
    read is shown: the spots on the paper (position, width,
    brightness), the wheel reading, the ruler.  No focal length, pitch
    or angle of an element is ever computed.
    Every hidden true parameter is randomised for each session
    (--seed 2023 reproduces the box of the official solution).

    Run:   python3 eupho2023_E2_sim_EN.py   [--seed N] [--lang ko|en]
"""
import math
import random
import sys

LANG = "EN"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "KO" else en


OFFICIAL_SEED = 2023
PORTS = ("A", "B", "C", "D")
# unit vectors of the ports as seen from above (x right, y up)
PDIR = {"A": (0.0, 1.0), "B": (1.0, 0.0), "C": (0.0, -1.0), "D": (-1.0, 0.0)}


# --------------------------------------------------------------------------
#  Hidden truth
# --------------------------------------------------------------------------
class Truth(object):

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1, 10 ** 8)
        self.seed = int(seed)
        rng = random.Random(self.seed)
        off = (self.seed == OFFICIAL_SEED)

        self.a = 3.80                       # box half width, cm
        self.t_glass = 0.013                # protective window, cm
        self.lam = 650.0e-7 if off else rng.uniform(646.0, 654.0) * 1e-7   # cm
        self.lam_spec = 650.0e-7            # value quoted in the problem
        self.w0 = 0.380 if off else rng.uniform(0.300, 0.560)              # cm

        # ---- central element: always a semi-transparent mirror at 45 deg --
        # diag = +1 : reflective plane along y = -x  (A<->B, C<->D)
        # diag = -1 : reflective plane along y = +x  (A<->D, B<->C)
        self.diag = 1 if off else rng.choice((1, -1))
        self.split_t = 0.50 if off else rng.uniform(0.44, 0.56)
        self.depol = 0.020                  # unpolarised light scattered by the foil

        # ---- port elements -----------------------------------------------
        kinds = ["convex", "concave", "grating", "polarizer"]
        if off:
            order = ["convex", "concave", "grating", "polarizer"]   # A B C D
        else:
            order = kinds[:]
            rng.shuffle(order)
        self.slot = {}
        for p, k in zip(PORTS, order):
            self.slot[p] = k
        self.f = {}
        self.pos = {}
        for p in PORTS:
            k = self.slot[p]
            if k == "convex":
                self.f[p] = 6.50 if off else rng.uniform(5.6, 7.6)
                self.pos[p] = 2.20 if off else rng.uniform(1.85, 2.55)
            elif k == "concave":
                self.f[p] = -9.20 if off else rng.uniform(-10.8, -7.9)
                self.pos[p] = 2.10 if off else rng.uniform(1.85, 2.55)
            elif k == "grating":
                self.pitch = 2.000e-4 if off else rng.uniform(1.65, 2.45) * 1e-4  # cm
                self.pos[p] = 3.12 if off else rng.uniform(2.85, 3.35)
                self.f[p] = 0.0
            else:
                self.pol_angle = 65.0 if off else rng.uniform(18.0, 82.0)  # from vertical
                self.pos[p] = 2.50 if off else rng.uniform(2.0, 3.0)
                self.f[p] = 0.0
        # wheel scale has an arbitrary zero
        self.wheel_zero = 0.0 if off else rng.uniform(0.0, 360.0)
        self.n_block = 1.500
        # reading imperfections
        self.w_noise = 0.020                # cm rms on a spot width
        self.y_noise = 0.030                # cm rms on a spot position
        self.see_min = 0.0030               # relative intensity still visible

    def port_of(self, kind):
        for p in PORTS:
            if self.slot[p] == kind:
                return p
        return None

    def answer_key(self):
        gp = self.port_of("grating")
        cx = self.port_of("convex")
        cc = self.port_of("concave")
        pol = self.port_of("polarizer")
        return {
            "central": "semi-transparent mirror",
            "diag": self.diag,
            "slots": dict(self.slot),
            "convex_port": cx, "f_convex_cm": self.f[cx], "x_convex_cm": self.pos[cx],
            "concave_port": cc, "f_concave_cm": self.f[cc], "x_concave_cm": self.pos[cc],
            "grating_port": gp, "pitch_um": self.pitch * 1e4, "x_grating_cm": self.pos[gp],
            "polarizer_port": pol, "pol_angle_deg": self.pol_angle,
            "w0_mm": self.w0 * 10.0,
            "brewster_deg": math.degrees(math.atan(self.n_block)),
        }


# --------------------------------------------------------------------------
#  Optics
# --------------------------------------------------------------------------
class Ray(object):
    __slots__ = ("w", "m", "y", "ang", "I", "pol", "unpol", "order")

    def __init__(self, w, m, y, ang, I, pol, unpol=0.0, order=0):
        self.w = w          # signed beam width, cm
        self.m = m          # dw/dz, cm/cm
        self.y = y          # transverse offset, cm
        self.ang = ang      # transverse angle, rad
        self.I = I          # relative intensity of the polarised part
        self.pol = pol      # polarisation angle from vertical, rad
        self.unpol = unpol  # unpolarised fraction
        self.order = order

    def prop(self, z):
        self.w += self.m * z
        self.y += math.tan(self.ang) * z

    def copy(self):
        return Ray(self.w, self.m, self.y, self.ang, self.I, self.pol,
                   self.unpol, self.order)


class Optics(object):
    """Forward ray/beam-envelope model of the sealed box."""

    WINDOW = 0.55          # half width of an optical port window, cm

    def __init__(self, tr):
        self.tr = tr

    # ---- connectivity ---------------------------------------------------
    def partners(self, p):
        """(reflected port, transmitted port, weak port) for an input port."""
        opp = {"A": "C", "C": "A", "B": "D", "D": "B"}
        if self.tr.diag > 0:
            refl = {"A": "B", "B": "A", "C": "D", "D": "C"}
        else:
            refl = {"A": "D", "D": "A", "B": "C", "C": "B"}
        t = opp[p]
        r = refl[p]
        weak = [q for q in PORTS if q not in (p, t, r)][0]
        return r, t, weak

    # ---- single element -------------------------------------------------
    def apply(self, rays, port):
        tr = self.tr
        k = tr.slot[port]
        out = []
        for ry in rays:
            if k in ("convex", "concave"):
                f = tr.f[port]
                ry.m -= ry.w / f
                ry.ang = math.atan(math.tan(ry.ang) - ry.y / f)
                out.append(ry)
            elif k == "polarizer":
                th = math.radians(tr.pol_angle)
                c = math.cos(ry.pol - th)
                ry.I *= c * c
                ry.I += 0.5 * ry.unpol
                ry.unpol = 0.0
                ry.pol = th
                out.append(ry)
            elif k == "grating":
                for n in (-2, -1, 0, 1, 2):
                    s = n * tr.lam / tr.pitch
                    if abs(s) > 0.985:
                        continue
                    w = {0: 0.58, 1: 0.155, 2: 0.028}[abs(n)]
                    q = ry.copy()
                    q.I *= w
                    q.unpol *= w
                    q.ang = ry.ang + math.asin(s)
                    q.order = n
                    out.append(q)
            else:
                out.append(ry)
        return out

    # ---- full path ------------------------------------------------------
    def trace(self, p_in, p_out, wheel_deg, x_card):
        """Return the list of spots on a card placed x_card cm from the
        outer wall of port `p_out`."""
        tr = self.tr
        a = tr.a
        refl, trans, weak = self.partners(p_in)
        if p_out == p_in:
            return []
        pol0 = math.radians((wheel_deg + tr.wheel_zero) % 360.0)
        rays = [Ray(tr.w0, 0.0, 0.0, 0.0, 1.0, pol0)]

        # into the box, up to the entrance element
        for ry in rays:
            ry.prop(a - tr.pos[p_in])
        rays = self.apply(rays, p_in)
        for ry in rays:
            ry.prop(tr.pos[p_in])

        # the beam splitter
        if p_out == refl:
            fac = 1.0 - tr.split_t
            for ry in rays:
                ry.I *= fac * (1.0 + 0.09 * math.cos(2.0 * ry.pol))
                ry.unpol = ry.unpol * fac + ry.I * tr.depol
                # a 90 deg fold mirrors the transverse coordinate
                ry.y = -ry.y
                ry.ang = -ry.ang
        elif p_out == trans:
            fac = tr.split_t
            for ry in rays:
                ry.I *= fac
                ry.unpol *= fac
        else:                       # the weak corner path
            for ry in rays:
                ry.I *= 0.021
                ry.unpol = ry.unpol * 0.021 + ry.I * tr.depol

        for ry in rays:
            ry.prop(tr.pos[p_out])
        rays = self.apply(rays, p_out)
        # the optical port windows are narrow: everything that misses them is
        # clipped inside the box (this is why the high diffraction orders of
        # an entrance grating never leave the box)
        keep = []
        for ry in rays:
            ry.prop(a - tr.pos[p_out])
            if abs(ry.y) <= self.WINDOW:
                ry.prop(x_card)
                keep.append(ry)
        return keep


# --------------------------------------------------------------------------
#  Rig - public API
# --------------------------------------------------------------------------
LEVELS = [(0.25, "bright"), (0.060, "medium"), (0.012, "faint"),
          (0.0030, "very faint")]


def level_of(I):
    for th, name in LEVELS:
        if I >= th:
            return name
    return "invisible"


LEVEL_TXT = {"bright": ("밝음", "bright"), "medium": ("보통", "medium"),
             "faint": ("희미함", "faint"), "very faint": ("매우 희미함", "very faint"),
             "invisible": ("보이지 않음", "invisible")}


class Rig(object):

    PARTS = ["box", "laser", "block", "card", "tape", "ruler"]

    def __init__(self, seed=None):
        self.truth = Truth(seed)
        self.opt = Optics(self.truth)
        self.rng = random.Random(self.truth.seed ^ 0xB07)
        self.placed = dict((p, False) for p in self.PARTS)
        self.p_in = "A"
        self.p_out = "C"
        self.wheel = 0.0
        self.x_card = 5.0
        self.laser_on = True
        self.mode = "box"            # box | free | brewster
        self.incidence = 45.0

    # ---------------- assembly ------------------------------------------
    def prereq(self, part):
        if part in ("box", "laser", "ruler", "tape"):
            return True
        if part == "card":
            return self.placed["laser"]
        if part == "block":
            return self.placed["laser"]
        return True

    def place(self, part):
        if not self.prereq(part):
            return False
        self.placed[part] = True
        return True

    def remove(self, part):
        if part == "box":
            self.placed["card"] = False
        if part == "laser":
            self.placed["card"] = False
            self.placed["block"] = False
        self.placed[part] = False
        return True

    def ready(self):
        return self.placed["box"] and self.placed["laser"] and self.placed["card"]

    # ---------------- configuration --------------------------------------
    def set_input_port(self, p):
        if p in PORTS:
            self.p_in = p
            if self.p_out == p:
                self.p_out = {"A": "C", "B": "D", "C": "A", "D": "B"}[p]

    def set_exit_port(self, p):
        if p in PORTS and p != self.p_in:
            self.p_out = p

    def set_wheel(self, deg):
        self.wheel = float(deg) % 360.0

    def read_wheel(self):
        return round(self.wheel, 1)

    def set_card_distance(self, x_cm):
        self.x_card = max(0.0, float(x_cm))

    def read_card_distance(self):
        return round(self.x_card, 1)

    def set_mode(self, m):
        self.mode = m

    def set_incidence(self, deg):
        self.incidence = max(5.0, min(85.0, float(deg)))

    # ---------------- observations ----------------------------------------
    def read_card(self):
        """What can be seen and measured on the millimetre card.

        Each entry: dict(pos_cm, width_mm, level).  `pos_cm` is read against
        the printed scale (diagonal scale, 0.01 cm), `width_mm` with the
        millimetre paper (0.1 mm)."""
        if not self.laser_on or not self.placed["card"] or not self.placed["laser"]:
            return []
        if self.mode == "free":
            # the laser shines straight onto the card, no box in the way
            rays = [Ray(self.truth.w0, 0.0, 0.0, 0.0, 1.0,
                        math.radians((self.wheel + self.truth.wheel_zero) % 360.0))]
        elif self.mode == "box":
            if not self.placed["box"]:
                return []
            rays = self.opt.trace(self.p_in, self.p_out, self.wheel, self.x_card)
        else:
            return []
        out = []
        for ry in rays:
            I = ry.I + ry.unpol
            lv = level_of(I)
            if lv == "invisible":
                continue
            w = abs(ry.w) + self.rng.gauss(0.0, self.truth.w_noise)
            w = max(0.030, w)
            y = ry.y + self.rng.gauss(0.0, self.truth.y_noise)
            out.append({"pos_cm": round(y, 2),
                        "width_mm": round(w * 10.0, 1),
                        "level": lv,
                        "raw_I": I})
        out.sort(key=lambda d: d["pos_cm"])
        return out

    def read_reflection(self):
        """Brewster set-up: brightness of the beam reflected off the block."""
        if self.mode != "brewster" or not self.placed["block"] or not self.laser_on:
            return "invisible"
        n = self.truth.n_block
        i = math.radians(self.incidence)
        s = math.sin(i) / n
        if s >= 1.0:
            return "bright"
        t = math.asin(s)
        rs = (math.sin(i - t) / math.sin(i + t)) ** 2 if abs(i - t) > 1e-9 else 0.0
        rp = (math.tan(i - t) / math.tan(i + t)) ** 2 if abs(i + t - math.pi / 2) > 1e-9 else 0.0
        # polarisation angle measured from the horizontal plane of incidence
        thv = math.radians((self.wheel + self.truth.wheel_zero) % 360.0)
        th_h = thv - math.pi / 2.0
        I = rp * math.cos(th_h) ** 2 + rs * math.sin(th_h) ** 2
        return level_of(I / 0.16)

    def observe_exits(self):
        """Which ports show light for the current input port and wheel angle,
        with their brightness - the qualitative observation matrix."""
        res = {}
        keep = self.p_out
        for q in PORTS:
            if q == self.p_in:
                continue
            self.p_out = q
            spots = self.read_card()
            res[q] = spots
        self.p_out = keep
        return res


# ==========================================================================
#  GUI
# ==========================================================================
import tkinter as tk
from tkinter import ttk

WOOD = "#e3cfa3"
WOOD_E = "#8a6c3c"
BG = "#eef1e9"
DESK = "#c9b291"
PAPER = "#fbfaf4"
GLASS = "#dcecf2"
RED = "#ff2d2d"


def _spot_colour(level):
    return {"bright": "#ff2020", "medium": "#ff5a45", "faint": "#e08072",
            "very faint": "#c79a92"}.get(level, "#bbb")


def draw_box(cv, cx, cy, half, tag=()):
    """The black box seen from above (never drawn open)."""
    cv.create_rectangle(cx - half, cy - half, cx + half, cy + half,
                        fill=WOOD, outline=WOOD_E, width=2, tags=tag)
    for i in range(1, 8):                      # finger joints
        t = -half + 2 * half * i / 8.0
        cv.create_line(cx + t, cy - half, cx + t, cy - half + 5, fill=WOOD_E, tags=tag)
        cv.create_line(cx + t, cy + half, cx + t, cy + half - 5, fill=WOOD_E, tags=tag)
        cv.create_line(cx - half, cy + t, cx - half + 5, cy + t, fill=WOOD_E, tags=tag)
        cv.create_line(cx + half, cy + t, cx + half - 5, cy + t, fill=WOOD_E, tags=tag)
    w = max(4.0, half * 0.15)
    for p, (dx, dy) in PDIR.items():
        px = cx + dx * half
        py = cy - dy * half
        if dx == 0:
            cv.create_rectangle(px - w, py - 3, px + w, py + 3,
                                fill="#3a3a3a", outline="#1c1c1c", tags=tag)
            cv.create_text(px, py - dy * (0.0) + (14 if dy > 0 else -14) * -1,
                           text=p, font=("TkDefaultFont", 9, "bold"), tags=tag)
        else:
            cv.create_rectangle(px - 3, py - w, px + 3, py + w,
                                fill="#3a3a3a", outline="#1c1c1c", tags=tag)
            cv.create_text(px - dx * 14, py, text=p,
                           font=("TkDefaultFont", 9, "bold"), tags=tag)
    cv.create_text(cx, cy + half * 0.45, text="7. EuPhO 23",
                   fill="#8a6c3c", font=("TkDefaultFont", int(max(6, half * 0.13))),
                   tags=tag)


def draw_laser_mount(cv, x, y, ang, wheel_deg, on=True, s=1.0, tag=()):
    """Laser diode on the wheeled mount; `ang` is the beam direction (rad)."""
    ca, sa = math.cos(ang), math.sin(ang)

    def P(u, v):
        return (x + (u * ca - v * sa) * s, y + (u * sa + v * ca) * s)

    pts = []
    for u, v in ((-34, -13), (6, -13), (6, 13), (-34, 13)):
        pts.extend(P(u, v))
    cv.create_polygon(pts, fill="#1f1f1f", outline="#000", tags=tag)
    pts = []
    for u, v in ((-6, -7), (16, -7), (16, 7), (-6, 7)):
        pts.extend(P(u, v))
    cv.create_polygon(pts, fill="#c9a227", outline="#6d5711", tags=tag)
    # the wheel with the pencil mark
    c = P(-14, 0)
    rr = 17 * s
    cv.create_oval(c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr,
                   fill="#efe6cf", outline="#8c8060", tags=tag)
    for k in range(12):
        t = math.radians(k * 30)
        cv.create_line(c[0] + rr * 0.82 * math.cos(t), c[1] + rr * 0.82 * math.sin(t),
                       c[0] + rr * math.cos(t), c[1] + rr * math.sin(t),
                       fill="#8c8060", tags=tag)
    t = math.radians(-wheel_deg - 90)
    cv.create_line(c[0], c[1], c[0] + rr * 0.95 * math.cos(t),
                   c[1] + rr * 0.95 * math.sin(t), fill="#b3261e", width=2, tags=tag)
    if on:
        p = P(18, 0)
        cv.create_oval(p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3, fill=RED,
                       outline="", tags=tag)


def draw_card(cv, x, y, ang, half, tag=()):
    ca, sa = math.cos(ang), math.sin(ang)

    def P(u, v):
        return (x + u * ca - v * sa, y + u * sa + v * ca)

    pts = []
    for u, v in ((-4, -half), (4, -half), (4, half), (-4, half)):
        pts.extend(P(u, v))
    cv.create_polygon(pts, fill=PAPER, outline="#9aa38d", tags=tag)


def draw_block(cv, x, y, s=1.0, tag=()):
    cv.create_rectangle(x - 46 * s, y - 34 * s, x + 46 * s, y + 34 * s,
                        fill=GLASS, outline="#8fb2bd", width=2, tags=tag)
    cv.create_line(x - 46 * s, y - 34 * s, x - 30 * s, y - 46 * s,
                   fill="#8fb2bd", tags=tag)
    cv.create_line(x + 46 * s, y - 34 * s, x + 62 * s, y - 46 * s,
                   fill="#8fb2bd", tags=tag)
    cv.create_line(x - 30 * s, y - 46 * s, x + 62 * s, y - 46 * s,
                   fill="#8fb2bd", tags=tag)


def draw_tape(cv, x, y, s=1.0, tag=()):
    cv.create_oval(x - 24 * s, y - 24 * s, x + 24 * s, y + 24 * s,
                   fill="#e5cfa0", outline="#b39a67", tags=tag)
    cv.create_oval(x - 10 * s, y - 10 * s, x + 10 * s, y + 10 * s,
                   fill=BG, outline="#b39a67", tags=tag)


def draw_ruler(cv, x, y, s=1.0, tag=()):
    cv.create_rectangle(x - 88 * s, y - 10 * s, x + 88 * s, y + 10 * s,
                        fill="#1c1c22", outline="#000", tags=tag)
    for i in range(36):
        xx = x - 86 * s + i * 5 * s
        cv.create_line(xx, y - 10 * s, xx, y - 10 * s + (7 if i % 5 == 0 else 4) * s,
                       fill="#dcdcdc", tags=tag)


# --------------------------------------------------------------------------
#  Assembly tab
# --------------------------------------------------------------------------
class AssemblyTab(ttk.Frame):

    HOME = {"box": (85, 80), "laser": (85, 200), "block": (85, 300),
            "card": (85, 385), "tape": (85, 455), "ruler": (85, 520)}
    SLOT = {"box": (470, 330), "laser": (470, 500), "block": (760, 500),
            "card": (700, 250), "tape": (270, 560), "ruler": (500, 610)}
    LABEL = {"box": ("A  블랙박스", "A  Black box"),
             "laser": ("B  레이저 모듈 (바퀴 거치대)", "B  Laser module (wheel mount)"),
             "block": ("C  투명 블록", "C  Transparent block"),
             "card": ("D  mm 측정지 (대각선 눈금)", "D  mm card (diagonal scale)"),
             "tape": ("마스킹 테이프", "Masking tape"),
             "ruler": ("연필과 자", "Pencil and ruler")}

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.rig = app.rig
        self.ox = self.oy = 0.0
        self.drag = None
        self.msg = ""
        self.cv = tk.Canvas(self, width=940, height=680, bg=BG, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Button-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_move)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Button-3>", self.on_right)
        self.cv.bind("<Button-2>", self.on_right)
        self.redraw()

    def slot_xy(self, p):
        x, y = self.SLOT[p]
        return x + self.ox, y + self.oy

    def hit_home(self, x, y):
        for p, (hx, hy) in self.HOME.items():
            if self.rig.placed[p]:
                continue
            if abs(x - hx) < 66 and abs(y - hy) < 32:
                return p
        return None

    def hit_placed(self, x, y):
        for p in reversed(self.rig.PARTS):
            if not self.rig.placed[p]:
                continue
            sx, sy = self.slot_xy(p)
            if abs(x - sx) < 60 and abs(y - sy) < 60:
                return p
        return None

    def on_press(self, e):
        p = self.hit_home(e.x, e.y)
        self.drag = [p, e.x, e.y] if p else ["__pan__", e.x, e.y]
        self.redraw()

    def on_move(self, e):
        if not self.drag:
            return
        if self.drag[0] == "__pan__":
            self.ox = max(-200, min(200, self.ox + e.x - self.drag[1]))
            self.oy = max(-140, min(140, self.oy + e.y - self.drag[2]))
        self.drag[1], self.drag[2] = e.x, e.y
        self.redraw()

    def on_release(self, e):
        if not self.drag or self.drag[0] == "__pan__":
            self.drag = None
            self.redraw()
            return
        p = self.drag[0]
        sx, sy = self.slot_xy(p)
        if abs(e.x - sx) > 100 or abs(e.y - sy) > 100:
            self.msg = T("그 위치에는 놓을 수 없다.", "It cannot be placed there.")
        elif not self.rig.prereq(p):
            self.msg = {"card": T("먼저 레이저 모듈을 책상에 놓아라.",
                                  "Put the laser module on the table first."),
                        "block": T("먼저 레이저 모듈을 책상에 놓아라.",
                                   "Put the laser module on the table first.")
                        }.get(p, T("아직 놓을 수 없다.", "Not possible yet."))
        else:
            self.rig.place(p)
            self.msg = ""
        self.drag = None
        self.redraw()
        self.app.sync()

    def on_right(self, e):
        p = self.hit_placed(e.x, e.y)
        if p:
            self.rig.remove(p)
            self.msg = ""
            self.redraw()
            self.app.sync()

    def redraw(self):
        cv = self.cv
        cv.delete("all")
        r = self.rig
        cv.create_rectangle(0, 0, 170, 680, fill="#dfe4d6", outline="#b3bba6")
        cv.create_text(85, 16, text=T("부품 상자", "Parts box"),
                       font=("TkDefaultFont", 11, "bold"))
        for p, (hx, hy) in self.HOME.items():
            if r.placed[p]:
                continue
            self.icon(cv, p, hx, hy, 0.55)
            cv.create_text(hx, hy + 34, text=T(*self.LABEL[p]),
                           font=("TkDefaultFont", 8), width=150)
        cv.create_rectangle(170, 120 + self.oy, 940, 680, fill=DESK, outline="#a68f6e")
        for p in r.PARTS:
            if r.placed[p]:
                continue
            sx, sy = self.slot_xy(p)
            cv.create_rectangle(sx - 46, sy - 46, sx + 46, sy + 46,
                                outline="#b0a389", dash=(3, 3))
        for p in ("tape", "ruler", "box", "block", "card", "laser"):
            if r.placed[p]:
                sx, sy = self.slot_xy(p)
                self.icon(cv, p, sx, sy, 1.0)
        if self.drag and self.drag[0] != "__pan__":
            self.icon(cv, self.drag[0], self.drag[1], self.drag[2], 1.0)
        cv.create_text(555, 26, font=("TkDefaultFont", 13, "bold"),
                       text=T("EuPhO 2023  E2 - 광학 블랙박스 · 장치 배치",
                              "EuPhO 2023  E2 - Optical black box · setup"))
        cv.create_text(555, 48, font=("TkDefaultFont", 9), fill="#4a5340",
                       text=T("왼쪽 끌기: 부품 이동 / 오른쪽 클릭: 부품 상자로 되돌림 / "
                              "빈 곳 끌기: 시점 이동",
                              "Left drag: move part / Right click: return to box / "
                              "Drag empty space: pan"))
        cv.create_text(555, 74, fill="#b3261e", font=("TkDefaultFont", 10, "bold"),
                       text=T("경고: 블랙박스를 열거나 흔들지 마라. 광학 포트의 창을 "
                              "만지지 마라.",
                              "WARNING: do not open or shake the black box, do not "
                              "touch the port windows."))
        if self.msg:
            cv.create_text(555, 96, text=self.msg, fill="#b3261e",
                           font=("TkDefaultFont", 10))

    def icon(self, cv, p, x, y, s):
        if p == "box":
            draw_box(cv, x, y, 82 * s if s > 0.9 else 40)
        elif p == "laser":
            draw_laser_mount(cv, x, y, -math.pi / 2 if s > 0.9 else 0.0,
                             self.rig.wheel, self.rig.laser_on, s)
        elif p == "block":
            draw_block(cv, x, y, s)
        elif p == "card":
            if s > 0.9:
                cv.create_rectangle(x - 46, y - 34, x + 46, y + 34,
                                    fill=PAPER, outline="#9aa38d")
                for i in range(19):
                    cv.create_line(x - 45 + i * 5, y + 24, x - 45 + i * 5, y + 30,
                                   fill="#9aa38d")
            else:
                cv.create_rectangle(x - 30, y - 22, x + 30, y + 22,
                                    fill=PAPER, outline="#9aa38d")
        elif p == "tape":
            draw_tape(cv, x, y, s)
        elif p == "ruler":
            draw_ruler(cv, x, y, s)


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.rig = app.rig
        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=6, pady=6)
        self.cv = tk.Canvas(self, width=920, height=660, bg=BG, highlightthickness=0)
        self.cv.pack(side="left", fill="both", expand=True)

        r = self.rig
        self.v_mode = tk.StringVar(value="box")
        self.v_in = tk.StringVar(value=r.p_in)
        self.v_out = tk.StringVar(value=r.p_out)
        self.v_wheel = tk.DoubleVar(value=0.0)
        self.v_x = tk.DoubleVar(value=5.0)
        self.v_inc = tk.DoubleVar(value=50.0)
        self.v_on = tk.BooleanVar(value=True)
        self.v_refl = tk.StringVar(value="-")
        self.v_note = tk.StringVar(value="")

        def sec(t):
            f = ttk.LabelFrame(left, text=t)
            f.pack(fill="x", pady=4)
            return f

        f = sec(T("측정 모드", "Mode"))
        for k, ko, en in (("box", "블랙박스", "black box"),
                          ("free", "레이저만 (자유 빔)", "laser only (free beam)"),
                          ("brewster", "투명 블록 반사", "reflection off the block")):
            ttk.Radiobutton(f, text=T(ko, en), value=k, variable=self.v_mode,
                            command=self.on_mode).pack(anchor="w")

        f = sec(T("레이저를 대는 포트", "Laser at port"))
        g = ttk.Frame(f); g.pack()
        for i, p in enumerate(PORTS):
            ttk.Radiobutton(g, text=p, value=p, variable=self.v_in,
                            command=self.on_in).grid(row=0, column=i, padx=6)

        f = sec(T("관찰하는 포트", "Watching port"))
        g = ttk.Frame(f); g.pack()
        self.rb_out = []
        for i, p in enumerate(PORTS):
            b = ttk.Radiobutton(g, text=p, value=p, variable=self.v_out,
                                command=self.on_out)
            b.grid(row=0, column=i, padx=6)
            self.rb_out.append((p, b))

        f = sec(T("레이저 회전 바퀴 [°]", "Laser wheel [deg]"))
        ttk.Spinbox(f, from_=0.0, to=359.5, increment=0.5, width=8,
                    textvariable=self.v_wheel, command=self.on_wheel).pack(anchor="w")
        ttk.Scale(f, from_=0.0, to=359.5, variable=self.v_wheel,
                  command=lambda *a: self.on_wheel()).pack(fill="x")
        ttk.Checkbutton(f, text=T("레이저 켜기", "laser on"), variable=self.v_on,
                        command=self.on_laser).pack(anchor="w")

        f = sec(T("측정지 거리 x [cm]", "Card distance x [cm]"))
        ttk.Spinbox(f, from_=0.0, to=30.0, increment=0.1, width=8,
                    textvariable=self.v_x, command=self.on_x).pack(anchor="w")
        ttk.Scale(f, from_=0.0, to=30.0, variable=self.v_x,
                  command=lambda *a: self.on_x()).pack(fill="x")

        f = sec(T("투명 블록 입사각 [°]", "Block incidence [deg]"))
        ttk.Spinbox(f, from_=5.0, to=85.0, increment=0.5, width=8,
                    textvariable=self.v_inc, command=self.on_inc).pack(anchor="w")
        ttk.Label(f, textvariable=self.v_refl, font=("TkDefaultFont", 10, "bold"),
                  foreground="#a03020").pack(anchor="w")

        ttk.Label(left, text=T("상자 바깥 한 변 7.6 cm (자로 측정)",
                               "box outer size 7.6 cm (by ruler)"),
                  font=("TkDefaultFont", 9)).pack(anchor="w", pady=2)
        ttk.Label(left, textvariable=self.v_note, foreground="#b3261e",
                  wraplength=250).pack(fill="x")

        self._job = None
        self.on_mode()
        self.tick()

    # -------- callbacks --------
    def on_mode(self):
        self.rig.set_mode(self.v_mode.get())
        if self.v_mode.get() == "brewster" and not self.rig.placed["block"]:
            self.v_note.set(T("투명 블록을 먼저 놓아라.", "Place the transparent block."))
        else:
            self.v_note.set("")

    def on_in(self):
        self.rig.set_input_port(self.v_in.get())
        self.v_out.set(self.rig.p_out)

    def on_out(self):
        self.rig.set_exit_port(self.v_out.get())
        self.v_out.set(self.rig.p_out)

    def on_wheel(self):
        try:
            self.rig.set_wheel(self.v_wheel.get())
        except Exception:
            pass

    def on_x(self):
        try:
            self.rig.set_card_distance(self.v_x.get())
        except Exception:
            pass

    def on_inc(self):
        self.rig.set_incidence(self.v_inc.get())

    def on_laser(self):
        self.rig.laser_on = self.v_on.get()

    def sync_from_rig(self):
        self.v_in.set(self.rig.p_in)
        self.v_out.set(self.rig.p_out)

    # -------- loop --------
    def tick(self):
        r = self.rig
        lv = r.read_reflection() if r.mode == "brewster" else None
        if lv is None:
            self.v_refl.set(T("반사광: -", "reflection: -"))
        else:
            self.v_refl.set(T("반사광: %s", "reflection: %s") % T(*LEVEL_TXT[lv]))
        try:
            self.redraw()
        except tk.TclError:
            return
        self._job = self.after(120, self.tick)

    # -------- drawing --------
    def redraw(self):
        cv = self.cv
        cv.delete("all")
        r = self.rig
        cv.create_text(460, 16, font=("TkDefaultFont", 12, "bold"),
                       text=T("EuPhO 2023  E2 - 광학 블랙박스 · 실험대",
                              "EuPhO 2023  E2 - Optical black box · bench"))
        cv.create_rectangle(12, 32, 560, 640, fill="#f6f7f2", outline="#c3caba")
        cv.create_text(64, 44, text=T("위에서 본 모습", "top view"),
                       font=("TkDefaultFont", 9), fill="#6b7360")
        if r.mode == "brewster":
            self.draw_brewster(cv)
        elif r.mode == "free":
            self.draw_free(cv)
        else:
            self.draw_box_view(cv)
        self.draw_card_panel(cv)

    # ---- top views ----
    def draw_box_view(self, cv):
        r = self.rig
        if not r.placed["box"]:
            cv.create_text(286, 330, text=T("블랙박스가 없다.", "no black box"),
                           fill="#8a8f80")
            return
        a = r.truth.a
        x = r.x_card
        sc = max(6.0, min(19.0, 215.0 / (a + x + 3.0)))
        cx, cy = 286, 336
        half = a * sc
        draw_box(cv, cx, cy, half)
        din = PDIR[r.p_in]
        # laser outside the input port
        lx = cx + din[0] * (half + 42)
        ly = cy - din[1] * (half + 42)
        ang = math.atan2(-din[1], -din[0])
        if r.placed["laser"]:
            draw_laser_mount(cv, lx, ly, ang, r.wheel, r.laser_on, 0.85)
            if r.laser_on:
                cv.create_line(lx + math.cos(ang) * 18, ly + math.sin(ang) * 18,
                               cx + din[0] * half, cy - din[1] * half,
                               fill=RED, width=2)
        # card outside the exit port
        dout = PDIR[r.p_out]
        px = cx + dout[0] * (half + x * sc)
        py = cy - dout[1] * (half + x * sc)
        cang = math.atan2(dout[1], dout[0])
        if r.placed["card"]:
            draw_card(cv, px, py, cang, 60)
        spots = r.read_card()
        for d in spots:
            if not r.placed["card"]:
                break
            ox = -dout[1] * d["pos_cm"] * sc
            oy = -dout[0] * d["pos_cm"] * sc
            cv.create_line(cx + dout[0] * half, cy - dout[1] * half,
                           px + ox, py + oy, fill=_spot_colour(d["level"]))
        cv.create_text(286, 616, font=("TkDefaultFont", 9), fill="#6b7360",
                       text=T("측정지 거리 x = %.1f cm (자로 측정)",
                              "card distance x = %.1f cm (by ruler)") % x)

    def draw_free(self, cv):
        r = self.rig
        cx, cy = 286, 336
        if not r.placed["laser"]:
            cv.create_text(cx, cy, text=T("레이저가 없다.", "no laser"), fill="#8a8f80")
            return
        draw_laser_mount(cv, 110, cy, 0.0, r.wheel, r.laser_on, 0.95)
        sc = max(6.0, min(14.0, 340.0 / max(r.x_card + 2.0, 4.0)))
        px = 130 + r.x_card * sc
        if r.placed["card"]:
            draw_card(cv, px, cy, 0.0, 60)
        if r.laser_on:
            cv.create_line(130, cy, px, cy, fill=RED, width=2)
        cv.create_text(286, 616, font=("TkDefaultFont", 9), fill="#6b7360",
                       text=T("레이저에서 측정지까지 %.1f cm",
                              "laser to card %.1f cm") % r.x_card)

    def draw_brewster(self, cv):
        r = self.rig
        cx, cy = 300, 360
        if not r.placed["block"]:
            cv.create_text(cx, cy, text=T("투명 블록이 없다.", "no block"),
                           fill="#8a8f80")
            return
        draw_block(cv, cx, cy, 1.25)
        i = math.radians(r.incidence)
        L = 210
        sx = cx - L * math.sin(i)
        sy = cy - 42 - L * math.cos(i)
        hit = (cx, cy - 42)
        if r.placed["laser"]:
            draw_laser_mount(cv, sx, sy, math.atan2(hit[1] - sy, hit[0] - sx),
                             r.wheel, r.laser_on, 0.8)
        if r.laser_on:
            cv.create_line(sx, sy, hit[0], hit[1], fill=RED, width=2)
            lv = r.read_reflection()
            rx = cx + L * math.sin(i)
            ry = cy - 42 - L * math.cos(i)
            col = _spot_colour(lv)
            if lv != "invisible":
                cv.create_line(hit[0], hit[1], rx, ry, fill=col, width=2)
                cv.create_oval(rx - 4, ry - 4, rx + 4, ry + 4, fill=col, outline="")
            # refracted beam inside the glass
            t = math.asin(min(0.999, math.sin(i) / r.truth.n_block))
            cv.create_line(hit[0], hit[1], hit[0] + 84 * math.tan(t), cy + 42,
                           fill="#ff8a80", width=2)
        cv.create_text(300, 616, font=("TkDefaultFont", 9), fill="#6b7360",
                       text=T("입사각 %.1f°", "incidence %.1f deg") % r.incidence)

    # ---- the millimetre card, enlarged ----
    def draw_card_panel(self, cv):
        r = self.rig
        cv.create_rectangle(576, 32, 908, 372, fill="#f6f7f2", outline="#c3caba")
        cv.create_text(630, 44, text=T("측정지 (확대)", "card (enlarged)"),
                       font=("TkDefaultFont", 9), fill="#6b7360")
        x0, x1, ym = 590, 894, 190
        cv.create_rectangle(x0, ym - 92, x1, ym + 92, fill=PAPER, outline="#9aa38d")
        spots0 = r.read_card()
        mx = max([abs(d["pos_cm"]) for d in spots0], default=0.0)
        span = max(3.0, min(20.0, 2.4 * mx + 1.6))     # cm shown across the card
        mid = (x0 + x1) / 2.0
        pxcm = (x1 - x0 - 16) / span
        nt = int(span * 5) + 1
        for i in range(-nt, nt + 1):
            v = i * 0.1
            xx = mid + v * pxcm
            if xx < x0 + 3 or xx > x1 - 3:
                continue
            big = (i % 10 == 0)
            mid_t = (i % 5 == 0)
            if span > 9.0 and not mid_t:
                continue
            cv.create_line(xx, ym + 78, xx, ym + 78 - (13 if big else (8 if mid_t else 4)),
                           fill="#9aa38d")
            if big:
                cv.create_text(xx, ym + 87, text="%d" % (i // 10),
                               font=("TkDefaultFont", 7), fill="#6b7360")
        spots = spots0
        for d in spots:
            xx = mid + d["pos_cm"] * pxcm
            rr = max(2.0, d["width_mm"] * 0.1 * pxcm * 0.5)
            if x0 < xx < x1:
                cv.create_oval(xx - rr, ym - rr, xx + rr, ym + rr,
                               fill=_spot_colour(d["level"]), outline="")
        # numeric readings
        cv.create_rectangle(576, 384, 908, 640, fill="#f6f7f2", outline="#c3caba")
        cv.create_text(742, 296, font=("TkDefaultFont", 8), fill="#6b7360",
                       text=T("눈금 1칸 = 1 mm (한 변 %.0f cm 표시)",
                              "1 division = 1 mm (%.0f cm shown)") % span)
        cv.create_text(660, 398, text=T("측정지 눈금 판독", "readings on the card"),
                       font=("TkDefaultFont", 9, "bold"), fill="#3d4437")
        if not spots:
            cv.create_text(742, 440, fill="#8a8f80",
                           text=T("보이는 점이 없다.", "no visible spot"))
            return
        cv.create_text(600, 424, anchor="w", font=("Courier", 9, "bold"),
                       text=T("  위치[cm]   폭[mm]   밝기",
                              "  pos[cm]   width[mm]  brightness"))
        for i, d in enumerate(spots[:8]):
            cv.create_text(600, 444 + i * 20, anchor="w", font=("Courier", 10),
                           text="  %+6.2f     %5.1f    %s"
                                % (d["pos_cm"], d["width_mm"],
                                   T(*LEVEL_TXT[d["level"]])))


# --------------------------------------------------------------------------
#  Application
# --------------------------------------------------------------------------
class App(tk.Tk):

    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.title(T("HaslaLab · EuPhO 2023 E2 광학 블랙박스",
                     "HaslaLab · EuPhO 2023 E2 Optical Black Box"))
        self.configure(bg=BG)
        self.rig = Rig(seed)
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=6, pady=4)
        ttk.Label(bar, font=("TkDefaultFont", 10, "bold"),
                  text=T("E2 - 광학 블랙박스 (10점)",
                         "E2 - Optical black box (10 pts)")).pack(side="left")
        self.lbl_state = ttk.Label(bar, text="")
        self.lbl_state.pack(side="right", padx=10)
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.asm = AssemblyTab(nb, self)
        self.bench = BenchTab(nb, self)
        nb.add(self.asm, text=T("배치", "Setup"))
        nb.add(self.bench, text=T("실험대", "Bench"))
        self.nb = nb
        self.sync()

    def destroy(self):
        try:
            if getattr(self.bench, "_job", None):
                self.bench.after_cancel(self.bench._job)
                self.bench._job = None
        except Exception:
            pass
        tk.Tk.destroy(self)

    def sync(self):
        r = self.rig
        n = sum(1 for p in r.PARTS if r.placed[p])
        self.lbl_state.config(
            text=T("설치된 부품 %d/%d", "parts placed %d/%d") % (n, len(r.PARTS)))
        try:
            self.asm.redraw()
            self.bench.sync_from_rig()
        except Exception:
            pass


def main(argv):
    global LANG
    seed = None
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--seed" and i + 1 < len(argv):
            seed = int(argv[i + 1]); i += 1
        elif a == "--lang" and i + 1 < len(argv):
            LANG = "EN" if argv[i + 1].lower().startswith("e") else "KO"; i += 1
        i += 1
    App(seed).mainloop()


if __name__ == "__main__":
    main(sys.argv)
