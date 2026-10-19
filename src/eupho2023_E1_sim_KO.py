#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  7th European Physics Olympiad  (EuPhO 2023, Hannover, Germany)
  Experimental Problem E1 :  MAGNETIC PENDULUM
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Apparatus rebuilt from the photographs of the problem sheet: the
    plywood pendulum body with two screw supports and a mirror, the
    tower with its hard points and laser, two rails for the external
    magnets, the pendulum magnets, the black dipoles E, the unknown
    magnets F1/F2, the MDF screen, a stopwatch, masking tape, pencil
    and ruler.  Two tabs only: Assembly and Bench.
    Only what a real instrument shows is displayed: the stopwatch, the
    laser spot against the screen scale, the rail settings, the ruler.
    No frequency, moment of inertia or magnetic moment is ever shown.
    Every hidden true parameter is randomised for each session
    (--seed 2023 reproduces the values of the official solution).

    Run:   python3 eupho2023_E1_sim_KO.py   [--seed N] [--lang ko|en]
"""
import math
import random
import sys

MU0 = 4.0e-7 * math.pi          # N/A^2
GACC = 9.81                     # m/s^2  (local gravity, given)

LANG = "KO"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "KO" else en


# --------------------------------------------------------------------------
#  Hidden truth
# --------------------------------------------------------------------------
OFFICIAL_SEED = 2023


class Truth(object):
    """Per-session hidden parameters.  Never displayed anywhere in the GUI."""

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1, 10 ** 8)
        self.seed = int(seed)
        rng = random.Random(self.seed)
        off = (self.seed == OFFICIAL_SEED)

        # ---- masses (kg) -------------------------------------------------
        # The problem sheet states M_pen + M_mag = (52.3 +- 0.2) g.
        self.M_printed = 52.3e-3
        self.M_tot = 52.38e-3 if off else 52.3e-3 + rng.gauss(0.0, 0.20e-3)
        self.M_mag = 7.68e-3 if off else rng.gauss(7.68e-3, 0.06e-3)
        self.M_pen = self.M_tot - self.M_mag

        # ---- geometry (m) ------------------------------------------------
        self.ell = 0.2300 if off else rng.uniform(0.2265, 0.2335)     # magnet slot - axis
        self.s0 = 0.1200 if off else rng.uniform(0.1165, 0.1235)      # COM(body) - axis
        # radius of gyration of the bare body about the pivot
        kg = 0.148120 if off else rng.uniform(0.1455, 0.1508)
        self.I_pen = self.M_pen * kg * kg

        # ---- magnetisation ----------------------------------------------
        # specific magnetisation of the NdFeB material, A m^2 / g
        self.sigma = 0.12810 if off else rng.gauss(0.12750, 0.00360)
        self.ratio = 2.40                       # j2/j1, given in the problem
        self.j1 = self.sigma * (self.M_mag * 1000.0)
        self.j2 = self.ratio * self.j1

        # ---- unknown external magnets (linear quadrupole) ----------------
        self.qd_gap = 0.01000 if off else rng.uniform(0.0096, 0.0104)
        jqd = 5.156e-3 if off else 5.156e-3 * rng.uniform(0.92, 1.08)
        self.j_q = jqd / self.qd_gap

        # ---- imperfections ----------------------------------------------
        self.Q = 620.0 if off else rng.uniform(430.0, 780.0)
        self.rail_zero = 0.0 if off else rng.gauss(0.0, 0.0004)   # rail scale offset, m
        self.com_offset = 0.0 if off else rng.gauss(0.0, 0.0009)  # COM off symmetry axis, m
        self.react = 0.050                                        # stopwatch reaction sigma, s
        self.read_noise = 0.00035                                 # screen reading sigma, m
        self.tape_noise = 0.0 if off else 1.0                     # tower not taped -> jitter
        self.misalign = 0.0 if off else rng.gauss(0.0, 0.020)      # rad, rails not aligned

        # ---- derived (used only by the marking key) ----------------------
        self.I_nom = self.I_pen + self.M_mag * self.ell ** 2
        self.s1 = (self.M_pen * self.s0 + self.M_mag * self.ell) / self.M_tot
        self.w1sq = self.M_tot * GACC * self.s1 / self.I_nom
        self.w0sq = self.M_pen * GACC * self.s0 / self.I_pen
        self.k_slope = 6.0 * MU0 / (self.I_nom * math.pi) * self.j1 * self.j2 * self.ell ** 2
        self.d_comp = (self.k_slope / self.w1sq) ** 0.2

    # -- public marking key (used by the grader only, never by the GUI) ----
    def answer_key(self):
        return {
            "M_mag_g": self.M_mag * 1000.0,
            "M_pen_g": self.M_pen * 1000.0,
            "M_ratio": self.M_pen / self.M_mag,
            "ell_cm": self.ell * 100.0,
            "s0_cm": self.s0 * 100.0,
            "s1_cm": self.s1 * 100.0,
            "I_gm2": self.I_nom * 1000.0,
            "j1": self.j1,
            "j2": self.j2,
            "j1j2": self.j1 * self.j2,
            "sigma_Am2_per_g": self.sigma,
            "k_cm5_s2": self.k_slope * 1e10,
            "w1sq": self.w1sq,
            "w0sq": self.w0sq,
            "d_comp_cm": self.d_comp * 100.0,
            "alpha_unknown": -6.0,
        }


# --------------------------------------------------------------------------
#  Potential / dynamics
# --------------------------------------------------------------------------
class Potential(object):
    """
    Potential energy of the physical pendulum as a function of the body
    angle theta (rad, measured from vertical, positive towards the +x rail).

        U(th) = -M g Rc cos(th + gam) + U_mag(th)
        U_mag = sgn * j1 * [ Bone(dR, x) + Bone(dL, x) ],   x = 2 lm sin(th/2)

    Bone() is the on-axis y-component of the field of one external magnet
    (a single dipole for the black magnets, a coaxial dipole pair for the
    unknown blue magnets), exactly as in the official derivation.
    """

    def __init__(self, tr, mag_on, xm, ym, kind, dL, dR, sgn, swapped):
        self.tr = tr
        M_pen, M_mag = tr.M_pen, tr.M_mag
        if mag_on:
            Mt = M_pen + M_mag
            Xc = (M_pen * tr.com_offset + M_mag * xm) / Mt
            Yc = (M_pen * tr.s0 + M_mag * ym) / Mt
            self.I = tr.I_pen + M_mag * (xm * xm + ym * ym)
        else:
            Mt = M_pen
            Xc = tr.com_offset
            Yc = tr.s0
            self.I = tr.I_pen
        self.M = Mt
        self.Rc = math.hypot(Xc, Yc)
        self.gam = math.atan2(Xc, Yc)
        self.lm = math.hypot(xm, ym) if mag_on else 0.0
        self.mag_on = mag_on
        self.kind = kind if mag_on else "none"
        self.dL = dL
        self.dR = dR
        self.sgn = sgn

        # dipole source list of one external magnet: (offset, moment)
        if kind == "black":
            self.src = [(0.0, tr.j2)]
        elif kind == "unknown":
            g = tr.qd_gap
            s = -1.0 if swapped else 1.0
            self.src = [(-0.5 * g, s * tr.j_q), (0.5 * g, -s * tr.j_q)]
        else:
            self.src = []
        self.pref = tr.j1 * MU0 / (4.0 * math.pi)
        self.th_ref = 0.0          # alignment angle (set by align())

    # ---- one external magnet, y-component of B on the x-axis ------------
    def _Bone(self, D, x):
        tot = 0.0
        x2 = x * x
        for offs, m in self.src:
            Dk = D + offs
            Dk2 = Dk * Dk
            tot += m * (2.0 * Dk2 - x2) / (x2 + Dk2) ** 2.5
        return tot

    def _dBone(self, D, x):
        tot = 0.0
        x2 = x * x
        for offs, m in self.src:
            Dk = D + offs
            Dk2 = Dk * Dk
            tot += m * (-3.0 * x) * (4.0 * Dk2 - x2) / (x2 + Dk2) ** 3.5
        return tot

    # ---- potential and torque -------------------------------------------
    def U(self, th):
        u = -self.M * GACC * self.Rc * math.cos(th + self.gam)
        if self.src and self.lm > 0.0:
            x = 2.0 * self.lm * math.sin(0.5 * (th - self.th_ref))
            u += self.sgn * self.pref * (self._Bone(self.dR, x) + self._Bone(self.dL, x))
        return u

    def dU(self, th):
        d = self.M * GACC * self.Rc * math.sin(th + self.gam)
        if self.src and self.lm > 0.0:
            h = 0.5 * (th - self.th_ref)
            x = 2.0 * self.lm * math.sin(h)
            dx = self.lm * math.cos(h)
            d += self.sgn * self.pref * (self._dBone(self.dR, x) + self._dBone(self.dL, x)) * dx
        return d

    # ---- equilibrium and small-amplitude frequency ------------------------
    def equilibrium(self, guess=0.0):
        th = guess
        for _ in range(80):
            h = 1e-5
            f = self.dU(th)
            fp = (self.dU(th + h) - self.dU(th - h)) / (2.0 * h)
            if abs(fp) < 1e-14:
                break
            step = f / fp
            step = max(-0.15, min(0.15, step))
            th -= step
            if abs(step) < 1e-12:
                break
        return th

    def minima(self):
        """Return the list of local minima of U within +-60 deg of th_ref."""
        out = []
        lo, hi = self.th_ref - 1.05, self.th_ref + 1.05
        n = 900
        prev = self.dU(lo)
        for i in range(1, n + 1):
            th = lo + (hi - lo) * i / n
            cur = self.dU(th)
            if prev < 0.0 <= cur:
                out.append(self.equilibrium(th))
            prev = cur
        return out

    def omega_sq(self, th=None):
        if th is None:
            th = self.equilibrium()
        h = 2e-5
        d2 = (self.U(th + h) - 2.0 * self.U(th) + self.U(th - h)) / (h * h)
        return d2 / self.I


class Pendulum(object):
    """Damped RK4 integration of the physical pendulum."""

    def __init__(self, pot, Q):
        self.pot = pot
        self.th = pot.equilibrium()
        self.om = 0.0
        w = math.sqrt(max(abs(pot.omega_sq()), 1.0))
        self.b = pot.I * w / Q
        self.moving = False

    def _acc(self, th, om):
        return (-self.pot.dU(th) - self.b * om) / self.pot.I

    def step(self, dt):
        th, om = self.th, self.om
        a1 = self._acc(th, om)
        a2 = self._acc(th + 0.5 * dt * om, om + 0.5 * dt * a1)
        a3 = self._acc(th + 0.5 * dt * (om + 0.5 * dt * a1), om + 0.5 * dt * a2)
        a4 = self._acc(th + dt * (om + 0.5 * dt * a2), om + dt * a3)
        self.th = th + dt * (om + dt * (a1 + a2 + a3) / 6.0)
        self.om = om + dt * (a1 + 2.0 * a2 + 2.0 * a3 + a4) / 6.0


# --------------------------------------------------------------------------
#  Rig - the public API.  Everything the student (or the grader) can do.
# --------------------------------------------------------------------------
class Rig(object):

    PARTS = ["tower", "tape", "body", "laser", "screen", "rails",
             "penmag", "extmag", "stopwatch", "ruler"]

    def __init__(self, seed=None):
        self.truth = Truth(seed)
        self.rng = random.Random(self.truth.seed ^ 0x5EED)
        self.placed = dict((p, False) for p in self.PARTS)
        self.rails_aligned = False

        # configurable state
        self.mag_on = False
        self.xm = 0.0
        self.ym = self.truth.ell
        self.ext_kind = "none"          # none | black | unknown
        self.ext_swapped = False        # F1/F2 exchanged
        self.polarity = "repulsive"     # repulsive | attractive
        self.dL = 0.120
        self.dR = 0.120
        self.screen_D = 0.500
        self.laser_on = True

        # dynamic state
        self.t = 0.0
        self.sw_running = False
        self.sw_t0 = 0.0
        self.sw_val = 0.0
        self.balance_mode = False
        self.pend = None
        self._rebuild()

    # ---------------- assembly ------------------------------------------
    def prereq(self, part):
        p = self.placed
        if part == "tower":
            return True
        if part in ("tape", "body", "laser", "rails"):
            return p["tower"]
        if part == "screen":
            return p["laser"]
        if part == "penmag":
            return p["body"]
        if part == "extmag":
            return p["rails"] and self.rails_aligned
        return True

    def place(self, part):
        if not self.prereq(part):
            return False
        self.placed[part] = True
        if part == "penmag":
            self.mag_on = True
        if part == "extmag" and self.ext_kind == "none":
            self.ext_kind = "black"
        self._rebuild()
        return True

    def remove(self, part):
        deps = {"tower": ["tape", "body", "laser", "rails", "screen", "penmag", "extmag"],
                "body": ["penmag"], "rails": ["extmag"], "laser": ["screen"]}
        for d in deps.get(part, []):
            self.remove(d)
        self.placed[part] = False
        if part == "penmag":
            self.mag_on = False
        if part == "extmag":
            self.ext_kind = "none"
        if part == "rails":
            self.rails_aligned = False
        self._rebuild()
        return True

    def align_rails(self):
        if self.placed["rails"]:
            self.rails_aligned = True
        return self.rails_aligned

    def ready(self):
        return self.placed["tower"] and self.placed["body"]

    # ---------------- configuration --------------------------------------
    def set_external(self, kind):
        """kind: 'none' | 'black' | 'unknown'"""
        if kind != "none" and not self.placed["extmag"]:
            if not self.place("extmag"):
                return False
        self.ext_kind = kind
        self.placed["extmag"] = (kind != "none")
        self._rebuild()
        return True

    def swap_unknown(self):
        self.ext_swapped = not self.ext_swapped
        self._rebuild()

    def set_polarity(self, pol):
        self.polarity = pol
        self._rebuild()

    def flip_polarity(self):
        self.set_polarity("attractive" if self.polarity == "repulsive" else "repulsive")

    def set_distance(self, d_cm, d_cm_right=None):
        """Set the rail scale settings, in cm, as read on the printed scale."""
        self.dL = max(0.030, float(d_cm) / 100.0)
        self.dR = max(0.030, float(d_cm if d_cm_right is None else d_cm_right) / 100.0)
        self._rebuild()

    def set_pendulum_magnets(self, on, x_cm=None, y_cm=None):
        self.mag_on = bool(on)
        self.placed["penmag"] = bool(on) and self.placed["body"]
        if x_cm is not None:
            self.xm = float(x_cm) / 100.0
        if y_cm is not None:
            self.ym = float(y_cm) / 100.0
        self._rebuild()

    def set_screen_distance(self, D_cm):
        self.screen_D = max(0.05, float(D_cm) / 100.0)

    # ---------------- engine ---------------------------------------------
    def _rebuild(self):
        tr = self.truth
        sgn = 1.0 if self.polarity == "repulsive" else -1.0
        # the printed rail scale carries a small unknown zero offset
        dL = self.dL + tr.rail_zero
        dR = self.dR + tr.rail_zero
        kind = self.ext_kind if self.placed.get("extmag") else "none"
        pot = Potential(tr, self.mag_on, self.xm, self.ym, kind, dL, dR,
                        sgn, self.ext_swapped)
        # The rails are aligned with the pendulum AT REST, so the reference
        # angle of the magnetic potential is the undisturbed equilibrium.
        pot.th_ref = -pot.gam
        if not self.rails_aligned:
            pot.th_ref += tr.misalign
        keep = (self.pend.th, self.pend.om) if self.pend else (None, None)
        self.pend = Pendulum(pot, tr.Q)
        if keep[0] is not None:
            self.pend.th, self.pend.om = keep
        self.pot = pot

    # ---------------- actions --------------------------------------------
    def release(self, angle_deg):
        """Pull the pendulum to the pencil mark at `angle_deg` and let go."""
        self.pend.th = math.radians(float(angle_deg))
        self.pend.om = 0.0
        self.balance_mode = False

    def hold(self):
        self.pend.om = 0.0

    def rest(self):
        """Let the pendulum settle at its equilibrium immediately."""
        self.pend.th = self.pot.equilibrium(self.pend.th)
        self.pend.om = 0.0

    def advance(self, dt):
        """Advance the laboratory clock by dt seconds."""
        dt = float(dt)
        if dt <= 0.0:
            return
        w2 = abs(self.pot.omega_sq(self.pend.th))
        w = math.sqrt(max(w2, 4.0))
        hmax = min(1.2e-3, 2.0 * math.pi / w / 600.0)
        n = max(1, int(math.ceil(dt / hmax)))
        h = dt / n
        for _ in range(n):
            self.pend.step(h)
        self.t += dt

    # ---------------- instruments -----------------------------------------
    def stopwatch_start(self):
        if not self.sw_running:
            self.sw_running = True
            self.sw_t0 = self.t + self.rng.gauss(0.0, self.truth.react)

    def stopwatch_stop(self):
        if self.sw_running:
            self.sw_running = False
            self.sw_val += (self.t + self.rng.gauss(0.0, self.truth.react)) - self.sw_t0

    def stopwatch_reset(self):
        self.sw_running = False
        self.sw_val = 0.0

    def read_stopwatch(self):
        v = self.sw_val + ((self.t - self.sw_t0) if self.sw_running else 0.0)
        return max(0.0, round(v, 2))

    def read_screen(self):
        """Laser spot position on the screen scale, in cm.  None = off screen."""
        if not (self.laser_on and self.placed["laser"] and self.placed["screen"]):
            return None
        th = self.pend.th
        if abs(th) > math.radians(80.0):
            return None
        y = self.screen_D * math.tan(th)
        y += self.rng.gauss(0.0, self.truth.read_noise)
        if not self.placed["tape"]:
            y += self.rng.gauss(0.0, 0.0012 * self.truth.tape_noise)
        if abs(y) > 0.155:
            return None
        return round(y * 100.0 / 0.05) * 0.05          # 0.5 mm scale

    def read_magnet_position(self):
        """Ruler reading of where the pendulum magnets sit on the body,
        measured from the pivot mark.  (x, y) in cm, 0.5 mm resolution."""
        q = 0.05
        return (round(self.xm * 100.0 / q) * q, round(self.ym * 100.0 / q) * q)

    def read_screen_distance(self):
        return round(self.screen_D * 100.0, 1)

    def read_rails(self):
        return (round(self.dL * 100.0, 1), round(self.dR * 100.0, 1))

    def balance(self):
        """Balance the pendulum body on the ruler edge.  Reading in cm from
        the pivot mark, resolution 0.5 mm."""
        self.balance_mode = True
        tr = self.truth
        if self.mag_on:
            Y = (tr.M_pen * tr.s0 + tr.M_mag * self.ym) / (tr.M_pen + tr.M_mag)
        else:
            Y = tr.s0
        Y += self.rng.gauss(0.0, 0.0004)
        return round(Y * 100.0 / 0.05) * 0.05

    def observe_split(self):
        """What the eye sees at rest: 1 = single rest position,
        2 = two separate rest positions (double well)."""
        return len(self.pot.minima())

    # -- convenience for the virtual student --------------------------------
    def time_oscillations(self, n_osc, amp_deg=2.0, settle=0.0):
        """Release, wait, then time n_osc full oscillations with the stopwatch,
        exactly as a student would: start the watch on one extreme and stop it
        n_osc extremes later.  Returns the stopwatch reading in seconds."""
        self.release(amp_deg)
        if settle > 0:
            self.advance(settle)
        self.stopwatch_reset()
        # find the moment of maximum excursion by watching the spot
        self._wait_turn()
        self.stopwatch_start()
        for _ in range(n_osc):
            self._wait_turn(full=True)
        self.stopwatch_stop()
        return self.read_stopwatch()

    def _wait_turn(self, full=False):
        """Advance until the pendulum reaches its next turning point on the
        same side (full=True) or the next turning point at all."""
        h = 0.002
        target = 2 if full else 1
        seen = 0
        prev = self.pend.om
        t_guard = 0.0
        while t_guard < 60.0:
            self.advance(h)
            t_guard += h
            cur = self.pend.om
            if prev > 0.0 >= cur or prev < 0.0 <= cur:
                seen += 1
                if seen >= target:
                    return
            prev = cur


# ==========================================================================
#  GUI
# ==========================================================================
import tkinter as tk
from tkinter import ttk

WOOD = "#e3cfa3"
WOOD_D = "#a98b57"
WOOD_E = "#7d6338"
MDF = "#9e7247"
BLACKM = "#242424"
BLUEM = "#2f5fbf"
TEAL = "#1f9e8f"
BG = "#eef1e9"
DESK = "#c9b291"


def _rr(cv, x0, y0, x1, y1, r, **kw):
    """rounded rectangle"""
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


# --------------------------------------------------------------------------
#  Part artwork - reconstructed from Fig. 3 of the problem sheet
# --------------------------------------------------------------------------
def draw_tower(cv, x, y, s=1.0, tag=()):
    """Pendulum tower B: laser-cut plywood frame, grooved hard points on top."""
    w, h = 150 * s, 118 * s
    cv.create_rectangle(x - w / 2, y - h, x - w / 2 + 13 * s, y,
                        fill=WOOD, outline=WOOD_E, tags=tag)
    cv.create_rectangle(x + w / 2 - 13 * s, y - h, x + w / 2, y,
                        fill=WOOD, outline=WOOD_E, tags=tag)
    cv.create_rectangle(x - w / 2, y - h, x + w / 2, y - h + 14 * s,
                        fill=WOOD, outline=WOOD_E, tags=tag)
    cv.create_rectangle(x - w / 2 - 9 * s, y - 10 * s, x + w / 2 + 9 * s, y,
                        fill=WOOD, outline=WOOD_E, tags=tag)
    # grooves for the supporting screws
    for sx in (-1, 1):
        cv.create_polygon(x + sx * (w / 2 - 20 * s) - 6 * s, y - h + 14 * s,
                          x + sx * (w / 2 - 20 * s), y - h + 23 * s,
                          x + sx * (w / 2 - 20 * s) + 6 * s, y - h + 14 * s,
                          fill="#5d4a2b", outline="", tags=tag)


def draw_body(cv, x, y, s=1.0, ang=0.0, xm=0.0, ym=0.23, mag=True, tag=()):
    """Pendulum body A: teardrop plywood paddle, mirror on the crossbar."""
    ca, sa = math.cos(ang), math.sin(ang)

    def P(u, v):                      # body coords (u right, v down) -> canvas
        return (x + (u * ca - v * sa) * s, y + (u * sa + v * ca) * s)

    pts = []
    for u, v in [(-9, -12), (9, -12), (9, 22), (30, 96), (34, 132), (26, 166),
                 (0, 176), (-26, 166), (-34, 132), (-30, 96), (-9, 22)]:
        pts.extend(P(u, v))
    cv.create_polygon(pts, smooth=True, fill=WOOD, outline=WOOD_E, tags=tag)
    # crossbar with the two supporting screws + mirror
    a = P(-40, -6); b = P(40, -6); c = P(40, 6); d = P(-40, 6)
    cv.create_polygon(a[0], a[1], b[0], b[1], c[0], c[1], d[0], d[1],
                      fill="#d3bd8d", outline=WOOD_E, tags=tag)
    m1 = P(-13, -11); m2 = P(13, -11); m3 = P(13, -4); m4 = P(-13, -4)
    cv.create_polygon(m1[0], m1[1], m2[0], m2[1], m3[0], m3[1], m4[0], m4[1],
                      fill="#cfe4ea", outline="#5f7f8a", tags=tag)
    for sx in (-34, 34):
        p = P(sx, 0)
        cv.create_oval(p[0] - 3.5 * s, p[1] - 3.5 * s, p[0] + 3.5 * s, p[1] + 3.5 * s,
                       fill="#8f8f95", outline="#4a4a50", tags=tag)
    # EuPhO teal dot near the tip
    p = P(0, 150)
    cv.create_oval(p[0] - 5 * s, p[1] - 5 * s, p[0] + 5 * s, p[1] + 5 * s,
                   fill=TEAL, outline="", tags=tag)
    if mag:
        # body length 176 units == 23.0 cm of pivot-to-slot distance
        sc = 176.0 / 23.0
        p = P(xm * 100.0 * sc, ym * 100.0 * sc)
        for k, col in ((-1, "#2f8f4a"), (1, "#c0392b")):
            cv.create_oval(p[0] + k * 1 * s - 6 * s, p[1] - 6 * s,
                           p[0] + k * 1 * s + 6 * s, p[1] + 6 * s,
                           fill=col, outline="#1c1c1c", tags=tag)
    return P


def draw_rail(cv, x0, y0, length, s=1.0, tag=(), scale=True):
    h = 15 * s
    cv.create_rectangle(x0, y0 - h, x0 + length, y0 + h,
                        fill=WOOD, outline=WOOD_E, tags=tag)
    if scale:
        n = int(length / (10 * s))
        for i in range(n + 1):
            xx = x0 + i * 10 * s
            big = (i % 5 == 0)
            cv.create_line(xx, y0 - h, xx, y0 - h + (9 if big else 5) * s,
                           fill="#6b5533", tags=tag)


def draw_disc(cv, x, y, r, col, dots=False, tag=(), lbl=None):
    cv.create_oval(x - r, y - r, x + r, y + r, fill=col, outline="#101010", tags=tag)
    cv.create_oval(x - r * 0.45, y - r * 0.45, x + r * 0.45, y + r * 0.45,
                   fill="#f2f2f2", outline="#101010", tags=tag)
    if dots:
        cv.create_oval(x - r * 0.2, y - r - 3, x + r * 0.2, y - r + 1,
                       fill="white", outline="", tags=tag)
    if lbl:
        cv.create_text(x, y + r + 9, text=lbl, font=("TkDefaultFont", 8), tags=tag)


def draw_stopwatch(cv, x, y, s=1.0, txt="0.00", tag=()):
    _rr(cv, x - 24 * s, y - 34 * s, x + 24 * s, y + 30 * s, 9 * s,
        fill="#2b2b2b", outline="#141414", tags=tag)
    cv.create_rectangle(x - 18 * s, y - 22 * s, x + 18 * s, y - 2 * s,
                        fill="#b9c9a8", outline="#4c5a44", tags=tag)
    cv.create_text(x, y - 12 * s, text=txt, font=("Courier", int(11 * s), "bold"),
                   fill="#16210f", tags=tag)
    for k, c in ((-11, "#d6483b"), (11, "#3b6fd6")):
        cv.create_oval(x + k * s - 7 * s, y + 8 * s, x + k * s + 7 * s, y + 22 * s,
                       fill=c, outline="#141414", tags=tag)


def draw_screen_board(cv, x, y, s=1.0, tag=()):
    cv.create_rectangle(x - 34 * s, y - 78 * s, x + 34 * s, y + 78 * s,
                        fill=MDF, outline="#6d4d2e", tags=tag)


def draw_tape(cv, x, y, s=1.0, tag=()):
    cv.create_oval(x - 26 * s, y - 26 * s, x + 26 * s, y + 26 * s,
                   fill="#e5cfa0", outline="#b39a67", tags=tag)
    cv.create_oval(x - 11 * s, y - 11 * s, x + 11 * s, y + 11 * s,
                   fill=BG, outline="#b39a67", tags=tag)


def draw_ruler(cv, x, y, s=1.0, tag=()):
    cv.create_rectangle(x - 92 * s, y - 11 * s, x + 92 * s, y + 11 * s,
                        fill="#1c1c22", outline="#000", tags=tag)
    for i in range(37):
        xx = x - 90 * s + i * 5 * s
        cv.create_line(xx, y - 11 * s, xx, y - 11 * s + (7 if i % 5 == 0 else 4) * s,
                       fill="#dcdcdc", tags=tag)


def draw_laser(cv, x, y, s=1.0, on=True, tag=()):
    cv.create_rectangle(x - 20 * s, y - 8 * s, x + 14 * s, y + 8 * s,
                        fill="#c9a227", outline="#6d5711", tags=tag)
    cv.create_rectangle(x + 14 * s, y - 4 * s, x + 22 * s, y + 4 * s,
                        fill="#8a6a1a", outline="#5b450f", tags=tag)
    cv.create_rectangle(x - 34 * s, y - 10 * s, x - 20 * s, y + 10 * s,
                        fill="#1f1f1f", outline="#000", tags=tag)
    if on:
        cv.create_oval(x + 21 * s, y - 2 * s, x + 25 * s, y + 2 * s,
                       fill="#ff2d2d", outline="", tags=tag)


# --------------------------------------------------------------------------
#  Assembly tab
# --------------------------------------------------------------------------
class AssemblyTab(ttk.Frame):

    HOME = {"tower": (85, 70), "body": (85, 165), "rails": (85, 250),
            "laser": (85, 320), "screen": (85, 385), "penmag": (85, 445),
            "extmag": (85, 500), "tape": (85, 555), "stopwatch": (85, 615),
            "ruler": (85, 680)}

    SLOT = {"tower": (430, 600), "tape": (352, 588), "body": (430, 400),
            "laser": (288, 396), "screen": (800, 522), "rails": (430, 576),
            "penmag": (430, 576), "extmag": (300, 576),
            "stopwatch": (762, 650), "ruler": (610, 648)}

    LABEL = {"tower": ("B  진자 타워", "B  Pendulum tower"),
             "body": ("A  진자 몸체", "A  Pendulum body"),
             "rails": ("C  레일 2개", "C  Rails (2)"),
             "laser": ("레이저 모듈", "Laser module"),
             "screen": ("G  스크린", "G  Screen"),
             "penmag": ("D  진자 자석 2개", "D  Pendulum magnets"),
             "extmag": ("E/F  외부 자석", "E/F  External magnets"),
             "tape": ("I  마스킹 테이프", "I  Masking tape"),
             "stopwatch": ("H  스톱워치", "H  Stopwatch"),
             "ruler": ("J  연필과 자", "J  Pencil and ruler")}

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.rig = app.rig
        self.ox = 0.0
        self.oy = 0.0
        self.drag = None
        self.msg = ""
        self.cv = tk.Canvas(self, width=980, height=700, bg=BG, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Button-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_move)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Button-3>", self.on_right)
        self.cv.bind("<Button-2>", self.on_right)
        self.redraw()

    # ---- helpers ----
    def slot_xy(self, p):
        x, y = self.SLOT[p]
        return x + self.ox, y + self.oy

    def hit_home(self, x, y):
        for p, (hx, hy) in self.HOME.items():
            if self.rig.placed[p]:
                continue
            if abs(x - hx) < 62 and abs(y - hy) < 30:
                return p
        return None

    def hit_placed(self, x, y):
        best = None
        for p in reversed(self.rig.PARTS):
            if not self.rig.placed[p]:
                continue
            sx, sy = self.slot_xy(p)
            r = 70 if p in ("tower", "body", "rails", "screen") else 34
            if abs(x - sx) < r and abs(y - sy) < r:
                best = p
                break
        return best

    # ---- events ----
    def on_press(self, e):
        p = self.hit_home(e.x, e.y)
        if p:
            self.drag = [p, e.x, e.y]
        else:
            self.drag = ["__pan__", e.x, e.y]
        self.redraw()

    def on_move(self, e):
        if not self.drag:
            return
        if self.drag[0] == "__pan__":
            self.ox += e.x - self.drag[1]
            self.oy += e.y - self.drag[2]
            self.ox = max(-220, min(220, self.ox))
            self.oy = max(-160, min(160, self.oy))
            self.drag[1], self.drag[2] = e.x, e.y
        else:
            self.drag[1], self.drag[2] = e.x, e.y
        self.redraw()

    def on_release(self, e):
        if not self.drag or self.drag[0] == "__pan__":
            self.drag = None
            self.redraw()
            return
        p = self.drag[0]
        sx, sy = self.slot_xy(p)
        near = abs(e.x - sx) < 95 and abs(e.y - sy) < 95
        if p == "extmag":
            near = near or (abs(e.x - (self.SLOT["extmag"][0] + 260 + self.ox)) < 95
                            and abs(e.y - sy) < 95)
        if not near:
            self.msg = T("그 위치에는 놓을 수 없다.", "It cannot be placed there.")
        elif not self.rig.prereq(p):
            self.msg = self.prereq_msg(p)
        else:
            self.rig.place(p)
            self.msg = ""
            if p == "rails":
                self.msg = T("레일을 놓았다. [레일 정렬] 을 눌러 모든 자석 중심을 "
                             "한 직선 위에 맞춰라.",
                             "Rails placed.  Press [Align rails] so that all magnet "
                             "centres lie on one line.")
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

    def prereq_msg(self, p):
        m = {"tape": T("먼저 진자 타워를 책상에 세워라.",
                       "Put the pendulum tower on the table first."),
             "body": T("먼저 진자 타워를 책상에 세워라.",
                       "Put the pendulum tower on the table first."),
             "laser": T("먼저 진자 타워를 책상에 세워라.",
                        "Put the pendulum tower on the table first."),
             "rails": T("먼저 진자 타워를 책상에 세워라.",
                        "Put the pendulum tower on the table first."),
             "screen": T("먼저 레이저 모듈을 타워에 장착하라.",
                         "Mount the laser module on the tower first."),
             "penmag": T("먼저 진자 몸체를 받침점에 걸어라.",
                         "Hang the pendulum body on the hard points first."),
             "extmag": T("먼저 레일을 놓고 정렬하라.",
                         "Place and align the rails first.")}
        return m.get(p, T("아직 놓을 수 없다.", "Not possible yet."))

    def align(self):
        if self.rig.align_rails():
            self.msg = T("레일 정렬 완료.", "Rails aligned.")
        else:
            self.msg = T("레일이 아직 없다.", "No rails yet.")
        self.redraw()
        self.app.sync()

    # ---- drawing ----
    def redraw(self):
        cv = self.cv
        cv.delete("all")
        r = self.rig
        # parts box
        cv.create_rectangle(0, 0, 170, 700, fill="#dfe4d6", outline="#b3bba6")
        cv.create_text(85, 16, text=T("부품 상자", "Parts box"),
                       font=("TkDefaultFont", 11, "bold"))
        for p, (hx, hy) in self.HOME.items():
            if r.placed[p]:
                continue
            self.icon(cv, p, hx, hy, 0.62)
            cv.create_text(hx, hy + 30, text=T(*self.LABEL[p]),
                           font=("TkDefaultFont", 8))
        # desk
        ox, oy = self.ox, self.oy
        cv.create_rectangle(170, 0, 980, 700, fill=BG, outline="")
        cv.create_rectangle(170, 600 + oy, 980, 700, fill=DESK, outline="#a68f6e")
        cv.create_line(170, 600 + oy, 980, 600 + oy, fill="#8d7757", width=2)
        # ghost slots
        for p in r.PARTS:
            if r.placed[p]:
                continue
            sx, sy = self.slot_xy(p)
            if sx < 180:
                continue
            cv.create_rectangle(sx - 42, sy - 42, sx + 42, sy + 42,
                                outline="#b9c2ad", dash=(3, 3))
        # placed items in a sensible z-order
        for p in ["tower", "rails", "tape", "body", "penmag", "laser",
                  "extmag", "screen", "stopwatch", "ruler"]:
            if not r.placed[p]:
                continue
            sx, sy = self.slot_xy(p)
            self.icon(cv, p, sx, sy, 1.0)
        if r.placed["laser"] and r.placed["body"] and r.laser_on:
            lx, ly = self.slot_xy("laser")
            bx, by = self.slot_xy("body")
            cv.create_line(lx + 22, ly, bx - 4, by - 6, fill="#ff3b30", width=2)
        if r.placed["rails"] and not r.rails_aligned:
            cv.create_text(430 + ox, 536 + oy,
                           text=T("정렬되지 않음", "not aligned"),
                           fill="#b3261e", font=("TkDefaultFont", 9, "bold"))
        # dragged item
        if self.drag and self.drag[0] != "__pan__":
            self.icon(cv, self.drag[0], self.drag[1], self.drag[2], 1.0)
        # header
        cv.create_text(575, 22, text=T("EuPhO 2023  E1 - 자기 진자 · 장치 조립",
                                       "EuPhO 2023  E1 - Magnetic pendulum · assembly"),
                       font=("TkDefaultFont", 13, "bold"))
        cv.create_text(575, 44, font=("TkDefaultFont", 9), fill="#4a5340",
                       text=T("왼쪽 끌기: 부품 이동 / 오른쪽 클릭: 부품 상자로 되돌림 / "
                              "빈 곳 끌기: 시점 이동",
                              "Left drag: move part / Right click: return to box / "
                              "Drag empty space: pan"))
        if self.msg:
            cv.create_text(575, 66, text=self.msg, fill="#b3261e",
                           font=("TkDefaultFont", 10))

    def icon(self, cv, p, x, y, s):
        r = self.rig
        if p == "tower":
            draw_tower(cv, x, y, 1.78 * s if s > 0.9 else 0.82)
        elif p == "body":
            draw_body(cv, x, y, 1.0 * s if s > 0.9 else 0.45,
                      0.0, r.xm, r.ym, r.mag_on and r.placed["penmag"])
        elif p == "rails":
            L = 330 * s
            draw_rail(cv, x - 380 * s, y, 330 * s, s)
            draw_rail(cv, x + 50 * s, y, 330 * s, s)
        elif p == "laser":
            draw_laser(cv, x, y, 1.0 * s if s > 0.9 else 0.7, r.laser_on)
        elif p == "screen":
            draw_screen_board(cv, x, y, 1.0 * s if s > 0.9 else 0.5)
        elif p == "penmag":
            if s < 0.9:
                draw_disc(cv, x - 12, y, 8, "#2f8f4a")
                draw_disc(cv, x + 12, y, 8, "#c0392b")
        elif p == "extmag":
            if s < 0.9:
                draw_disc(cv, x - 34, y, 10, BLACKM)
                draw_disc(cv, x - 11, y, 10, BLACKM)
                draw_disc(cv, x + 12, y, 10, BLUEM, lbl="F1")
                draw_disc(cv, x + 36, y, 10, BLUEM, dots=True, lbl="F2")
            else:
                col = BLACKM if r.ext_kind == "black" else BLUEM
                dot = (r.ext_kind == "unknown")
                draw_disc(cv, x, y, 13, col, dots=dot)
                draw_disc(cv, x + 260, y, 13, col, dots=dot)
        elif p == "tape":
            draw_tape(cv, x, y, 1.0 * s if s > 0.9 else 0.55)
        elif p == "stopwatch":
            draw_stopwatch(cv, x, y, 1.0 * s if s > 0.9 else 0.62)
        elif p == "ruler":
            draw_ruler(cv, x, y, 1.0 * s if s > 0.9 else 0.55)


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):

    PPC_TOP = 14.0          # px per cm in the top view
    CX_TOP = 500
    CY_TOP = 545
    PIVOT = (300, 102)
    BODY_S = 1.18
    SCR = (760, 150)        # screen panel centre

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.rig = app.rig
        self.spot_hist = []
        self.peak = None
        self.last_bal = None
        self.running = True

        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=6, pady=6)
        self.cv = tk.Canvas(self, width=940, height=650, bg=BG, highlightthickness=0)
        self.cv.pack(side="left", fill="both", expand=True)

        r = self.rig
        self.v_ext = tk.StringVar(value=r.ext_kind)
        self.v_dL = tk.DoubleVar(value=12.0)
        self.v_dR = tk.DoubleVar(value=12.0)
        self.v_sym = tk.BooleanVar(value=True)
        self.v_xm = tk.DoubleVar(value=0.0)
        self.v_ym = tk.DoubleVar(value=round(r.truth.ell * 100.0, 1))
        self.v_mag = tk.BooleanVar(value=True)
        self.v_amp = tk.DoubleVar(value=2.0)
        self.v_scr = tk.DoubleVar(value=50.0)
        self.v_laser = tk.BooleanVar(value=True)
        self.v_sw = tk.StringVar(value="0.00")
        self.v_spot = tk.StringVar(value="-")
        self.v_peak = tk.StringVar(value="-")
        self.v_bal = tk.StringVar(value="-")
        self.v_note = tk.StringVar(value="")

        def sec(txt):
            f = ttk.LabelFrame(left, text=txt)
            f.pack(fill="x", pady=4)
            return f

        f = sec(T("외부 자석", "External magnets"))
        for key, ko, en in (("none", "없음", "none"),
                            ("black", "검정 쌍극자 E ×2", "black dipoles E ×2"),
                            ("unknown", "미지 자석 F1·F2", "unknown F1·F2")):
            ttk.Radiobutton(f, text=T(ko, en), value=key, variable=self.v_ext,
                            command=self.on_ext).pack(anchor="w")
        b = ttk.Frame(f); b.pack(fill="x", pady=2)
        ttk.Button(b, text=T("자석 뒤집기", "Flip magnets"), width=13,
                   command=self.on_flip).pack(side="left", padx=1)
        ttk.Button(b, text=T("F1↔F2 교체", "Swap F1/F2"), width=13,
                   command=self.on_swap).pack(side="left", padx=1)

        f = sec(T("레일 눈금  d [cm]", "Rail setting  d [cm]"))
        g = ttk.Frame(f); g.pack(fill="x")
        ttk.Label(g, text=T("왼쪽", "left")).grid(row=0, column=0, sticky="w")
        ttk.Spinbox(g, from_=3.0, to=40.0, increment=0.1, width=7,
                    textvariable=self.v_dL, command=self.on_d).grid(row=0, column=1)
        ttk.Label(g, text=T("오른쪽", "right")).grid(row=1, column=0, sticky="w")
        self.sp_dR = ttk.Spinbox(g, from_=3.0, to=40.0, increment=0.1, width=7,
                                 textvariable=self.v_dR, command=self.on_d)
        self.sp_dR.grid(row=1, column=1)
        ttk.Checkbutton(f, text=T("대칭 잠금", "lock symmetric"),
                        variable=self.v_sym, command=self.on_d).pack(anchor="w")
        for v in (self.v_dL, self.v_dR):
            v.trace_add("write", lambda *a: self.on_d())

        f = sec(T("진자 자석 D", "Pendulum magnets D"))
        ttk.Checkbutton(f, text=T("몸체에 부착", "attached to body"),
                        variable=self.v_mag, command=self.on_pm).pack(anchor="w")
        g = ttk.Frame(f); g.pack(fill="x")
        ttk.Label(g, text=T("가로 x [cm]", "x [cm]")).grid(row=0, column=0, sticky="w")
        ttk.Spinbox(g, from_=-4.0, to=4.0, increment=0.1, width=7,
                    textvariable=self.v_xm, command=self.on_pm).grid(row=0, column=1)
        ttk.Label(g, text=T("세로 y [cm]", "y [cm]")).grid(row=1, column=0, sticky="w")
        ttk.Spinbox(g, from_=1.0, to=23.5, increment=0.1, width=7,
                    textvariable=self.v_ym, command=self.on_pm).grid(row=1, column=1)
        ttk.Button(f, text=T("자 위에서 균형 잡기", "Balance on the ruler"),
                   command=self.on_balance).pack(fill="x", pady=2)
        ttk.Label(f, textvariable=self.v_bal, font=("Courier", 10)).pack(anchor="w")

        f = sec(T("진자 놓기", "Release"))
        g = ttk.Frame(f); g.pack(fill="x")
        ttk.Label(g, text=T("연필 표시 각 [°]", "mark [deg]")).grid(row=0, column=0)
        ttk.Spinbox(g, from_=0.1, to=75.0, increment=0.1, width=7,
                    textvariable=self.v_amp).grid(row=0, column=1)
        b = ttk.Frame(f); b.pack(fill="x", pady=2)
        ttk.Button(b, text=T("놓기", "release"), width=9,
                   command=self.on_release).pack(side="left", padx=1)
        ttk.Button(b, text=T("잡기", "hold"), width=9,
                   command=lambda: self.rig.hold()).pack(side="left", padx=1)
        ttk.Button(b, text=T("가만히", "settle"), width=9,
                   command=lambda: self.rig.rest()).pack(side="left", padx=1)

        f = sec(T("레이저 · 스크린", "Laser · screen"))
        ttk.Checkbutton(f, text=T("레이저 켜기", "laser on"), variable=self.v_laser,
                        command=self.on_laser).pack(anchor="w")
        g = ttk.Frame(f); g.pack(fill="x")
        ttk.Label(g, text=T("스크린 거리 [cm]", "screen dist [cm]")).grid(row=0, column=0)
        ttk.Spinbox(g, from_=10.0, to=120.0, increment=1.0, width=7,
                    textvariable=self.v_scr, command=self.on_scr).grid(row=0, column=1)
        ttk.Label(f, textvariable=self.v_spot, font=("Courier", 11)).pack(anchor="w")
        ttk.Label(f, textvariable=self.v_peak, font=("Courier", 11)).pack(anchor="w")

        f = sec(T("스톱워치 H", "Stopwatch H"))
        ttk.Label(f, textvariable=self.v_sw, font=("Courier", 20, "bold"),
                  background="#b9c9a8", anchor="e", width=9).pack(fill="x", pady=2)
        b = ttk.Frame(f); b.pack(fill="x")
        ttk.Button(b, text=T("시작", "start"), width=7,
                   command=self.rig.stopwatch_start).pack(side="left", padx=1)
        ttk.Button(b, text=T("정지", "stop"), width=7,
                   command=self.rig.stopwatch_stop).pack(side="left", padx=1)
        ttk.Button(b, text=T("리셋", "reset"), width=7,
                   command=self.rig.stopwatch_reset).pack(side="left", padx=1)

        ttk.Label(left, textvariable=self.v_note, foreground="#b3261e",
                  wraplength=250).pack(fill="x", pady=3)

        self._job = None
        self.on_ext()
        self.tick()

    # ---------------- callbacks ----------------
    def sync_from_rig(self):
        self.v_ext.set(self.rig.ext_kind)
        self.v_mag.set(self.rig.mag_on)

    def _warn(self):
        r = self.rig
        if not r.ready():
            self.v_note.set(T("조립 탭에서 타워와 진자 몸체를 먼저 설치하라.",
                              "Install tower and pendulum body in the Assembly tab."))
            return False
        if r.ext_kind != "none" and not r.rails_aligned:
            self.v_note.set(T("레일이 정렬되지 않았다.", "Rails are not aligned."))
            return True
        self.v_note.set("")
        return True

    def on_ext(self):
        k = self.v_ext.get()
        if k != "none" and not self.rig.placed["rails"]:
            self.v_ext.set("none")
            self.v_note.set(T("레일을 먼저 놓고 정렬하라.",
                              "Place and align the rails first."))
            return
        self.rig.set_external(k)
        self._warn()
        self.app.sync()

    def on_flip(self):
        self.rig.flip_polarity()

    def on_swap(self):
        self.rig.swap_unknown()

    def on_d(self, *a):
        try:
            dl = float(self.v_dL.get())
        except Exception:
            return
        if self.v_sym.get():
            if abs(float(self.v_dR.get()) - dl) > 1e-9:
                self.v_dR.set(round(dl, 2))
            self.rig.set_distance(dl, dl)
            self.sp_dR.state(["disabled"])
        else:
            self.sp_dR.state(["!disabled"])
            self.rig.set_distance(dl, float(self.v_dR.get()))

    def on_pm(self):
        self.rig.set_pendulum_magnets(self.v_mag.get(), self.v_xm.get(), self.v_ym.get())
        self.app.sync()

    def on_balance(self):
        if not self.rig.placed["ruler"]:
            self.v_bal.set(T("자가 없다.", "no ruler"))
            return
        v = self.rig.balance()
        self.last_bal = v
        self.v_bal.set(T("균형점: %.2f cm", "balance: %.2f cm") % v)

    def on_release(self):
        self.rig.release(self.v_amp.get())
        self.peak = None
        self.spot_hist = []

    def on_laser(self):
        self.rig.laser_on = self.v_laser.get()

    def on_scr(self):
        self.rig.set_screen_distance(self.v_scr.get())

    # ---------------- loop ----------------
    def tick(self):
        r = self.rig
        if self.running and r.ready():
            r.advance(0.040)
        s = r.read_screen()
        if s is None:
            self.v_spot.set(T("스크린 눈금: ---", "screen: ---"))
        else:
            self.v_spot.set(T("스크린 눈금: %+6.2f cm", "screen: %+6.2f cm") % s)
            self.spot_hist.append(s)
            if len(self.spot_hist) > 60:
                self.spot_hist.pop(0)
            p = max(abs(v) for v in self.spot_hist)
            self.peak = p
        if self.peak is None:
            self.v_peak.set(T("최근 최대 눈금: ---", "recent max: ---"))
        else:
            self.v_peak.set(T("최근 최대 눈금: %5.2f cm", "recent max: %5.2f cm") % self.peak)
        self.v_sw.set("%.2f" % r.read_stopwatch())
        try:
            self.redraw()
        except tk.TclError:
            return
        self._job = self.after(40, self.tick)

    # ---------------- drawing ----------------
    def redraw(self):
        cv = self.cv
        cv.delete("all")
        r = self.rig
        cv.create_text(470, 16, font=("TkDefaultFont", 12, "bold"),
                       text=T("EuPhO 2023  E1 - 자기 진자 · 실험대",
                              "EuPhO 2023  E1 - Magnetic pendulum · bench"))
        # ---------- side elevation ----------
        cv.create_rectangle(14, 30, 570, 350, fill="#f6f7f2", outline="#c3caba")
        cv.create_text(60, 42, text=T("측면도", "side view"), font=("TkDefaultFont", 9),
                       fill="#6b7360")
        cv.create_rectangle(14, 330, 570, 350, fill=DESK, outline="#a68f6e")
        px, py = self.PIVOT
        if r.placed["tower"]:
            draw_tower(cv, px, 330, 2.05)
        if r.placed["tape"]:
            draw_tape(cv, px - 118, 322, 0.5)
        th = r.pend.th if r.ready() else 0.0
        if r.placed["body"]:
            draw_body(cv, px, py, self.BODY_S, th, r.xm, r.ym,
                      r.mag_on and r.placed["penmag"])
        if r.placed["laser"]:
            draw_laser(cv, px - 96, py - 4, 0.9, r.laser_on)
            if r.laser_on:
                cv.create_line(px - 74, py - 4, px - 4, py - 4, fill="#ff3b30", width=2)
        cv.create_oval(px - 3, py - 3, px + 3, py + 3, fill="#333", outline="")
        # ---------- screen ----------
        sx, sy = self.SCR
        cv.create_rectangle(590, 30, 926, 300, fill="#f6f7f2", outline="#c3caba")
        cv.create_text(640, 42, text=T("스크린 G", "screen G"),
                       font=("TkDefaultFont", 9), fill="#6b7360")
        bx0, bx1 = 606, 910
        cv.create_rectangle(bx0, sy - 62, bx1, sy + 62, fill=MDF, outline="#6d4d2e")
        mid = (bx0 + bx1) / 2.0
        pxcm = (bx1 - bx0) / 32.0
        for i in range(-16, 17):
            xx = mid + i * pxcm
            big = (i % 5 == 0)
            cv.create_line(xx, sy + 40, xx, sy + 40 - (14 if big else 7),
                           fill="#f2e7d5")
            if big:
                cv.create_text(xx, sy + 50, text="%d" % i, fill="#f2e7d5",
                               font=("TkDefaultFont", 7))
        sp = r.read_screen()
        if sp is not None:
            cv.create_oval(mid + sp * pxcm - 4, sy - 4, mid + sp * pxcm + 4, sy + 4,
                           fill="#ff3b30", outline="")
        cv.create_text(758, 286, font=("TkDefaultFont", 8), fill="#6b7360",
                       text=T("스크린 거리 %.0f cm (자로 측정)",
                              "screen distance %.0f cm (by ruler)") % (r.screen_D * 100))
        # ---------- top view ----------
        cv.create_rectangle(14, 366, 926, 640, fill="#f6f7f2", outline="#c3caba")
        cv.create_text(64, 378, text=T("평면도 (위에서)", "top view"),
                       font=("TkDefaultFont", 9), fill="#6b7360")
        cx, cy, pp = self.CX_TOP, self.CY_TOP, self.PPC_TOP
        cv.create_line(24, cy, 916, cy, fill="#9aa38d", dash=(4, 3))
        if r.placed["rails"]:
            draw_rail(cv, 34, cy, cx - 66, 1.0)
            draw_rail(cv, cx + 32, cy, 900 - cx, 1.0)
            col = "#3d7d3d" if r.rails_aligned else "#b3261e"
            cv.create_text(120, cy + 34, fill=col, font=("TkDefaultFont", 9),
                           text=T("레일 정렬됨", "rails aligned") if r.rails_aligned
                           else T("레일 정렬 필요", "rails NOT aligned"))
        # pendulum magnets seen from above
        if r.mag_on and r.placed["penmag"]:
            self._pair(cv, cx, cy, r.polarity == "repulsive", small=True)
        # external magnets
        if r.ext_kind != "none" and r.placed["extmag"]:
            for sgn, dd in ((-1, r.dL), (1, r.dR)):
                x = cx + sgn * dd * 100.0 * pp
                x = max(30, min(910, x))
                if r.ext_kind == "black":
                    self._extblack(cv, x, cy, r.polarity == "repulsive", sgn)
                else:
                    self._extblue(cv, x, cy, sgn, r.ext_swapped)
                cv.create_line(cx, cy + 44, x, cy + 44, fill="#5a6350", arrow="both")
                cv.create_text((cx + x) / 2.0, cy + 56, font=("TkDefaultFont", 9),
                               text="d = %.1f cm" % (dd * 100.0))
        n = r.observe_split() if r.ready() else 1
        if n > 1:
            cv.create_text(cx, 392, fill="#b3261e", font=("TkDefaultFont", 10, "bold"),
                           text=T("정지 위치가 둘로 갈라져 보인다",
                                  "two separate rest positions are visible"))

    def _pair(self, cv, x, y, rep, small=False):
        w = 9 if small else 12
        h = 13 if small else 16
        cv.create_rectangle(x - w, y - h, x, y + h, fill="#c0392b", outline="#111")
        cv.create_rectangle(x, y - h, x + w, y + h, fill="#2f8f4a", outline="#111")
        cv.create_text(x - w / 2, y, text="N", fill="white", font=("TkDefaultFont", 7))
        cv.create_text(x + w / 2, y, text="S", fill="white", font=("TkDefaultFont", 7))

    def _extblack(self, cv, x, y, rep, sgn):
        w, h = 12, 16
        a, b = ("N", "S") if (rep == (sgn > 0)) else ("S", "N")
        ca, cb = ("#c0392b", "#2f8f4a") if a == "N" else ("#2f8f4a", "#c0392b")
        cv.create_rectangle(x - w, y - h, x, y + h, fill=ca, outline="#111")
        cv.create_rectangle(x, y - h, x + w, y + h, fill=cb, outline="#111")
        cv.create_text(x - w / 2, y, text=a, fill="white", font=("TkDefaultFont", 7))
        cv.create_text(x + w / 2, y, text=b, fill="white", font=("TkDefaultFont", 7))

    def _extblue(self, cv, x, y, sgn, swapped):
        cv.create_rectangle(x - 15, y - 17, x + 15, y + 17, fill=BLUEM, outline="#111")
        lbl = "F2" if ((sgn > 0) != swapped) else "F1"
        cv.create_text(x, y, text=lbl, fill="white", font=("TkDefaultFont", 8, "bold"))
        if lbl == "F2":
            cv.create_oval(x - 3, y - 22, x + 3, y - 16, fill="white", outline="")
            cv.create_oval(x - 3, y + 16, x + 3, y + 22, fill="white", outline="")


# --------------------------------------------------------------------------
#  Application
# --------------------------------------------------------------------------
class App(tk.Tk):

    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.title(T("HaslaLab · EuPhO 2023 E1 자기 진자",
                     "HaslaLab · EuPhO 2023 E1 Magnetic Pendulum"))
        self.configure(bg=BG)
        self.rig = Rig(seed)

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=6, pady=4)
        ttk.Label(bar, font=("TkDefaultFont", 10, "bold"),
                  text=T("E1 - 자기 진자 (10점)",
                         "E1 - Magnetic pendulum (10 pts)")).pack(side="left")
        ttk.Button(bar, text=T("레일 정렬", "Align rails"),
                   command=lambda: self.asm.align()).pack(side="right", padx=3)
        self.lbl_state = ttk.Label(bar, text="")
        self.lbl_state.pack(side="right", padx=10)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.asm = AssemblyTab(nb, self)
        self.bench = BenchTab(nb, self)
        nb.add(self.asm, text=T("조립", "Assembly"))
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
