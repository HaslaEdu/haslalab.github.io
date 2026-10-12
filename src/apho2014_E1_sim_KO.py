#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  15th Asian Physics Olympiad  (APhO 2014, Singapore)
  Experimental Problem :  SPEED OF ULTRASONIC SOUND IN SOLUTION
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The simulator shows ONLY what the real instruments show -- tape/ruler
    readings, a vernier caliper reading, a digital balance reading, a
    thermometer reading, the graduated measuring container, and the light
    patterns on the screen.  lambda_s, f_s, v_s, n_corn-syrup and C_s are
    NEVER computed or displayed.  All analysis is left to the student.
"""

import math
import random
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# --------------------------------------------------------------------------
# i18n
# --------------------------------------------------------------------------
LANG = "ko"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


# --------------------------------------------------------------------------
# Fixed apparatus dimensions (cm) - reconstructed from the problem sheet
# --------------------------------------------------------------------------
CELL_INNER = 11.16          # inner width of the glass cell (a + b)
CELL_HEIGHT = 15.0          # inner height
TRANSDUCER_D = 2.00         # active face diameter of the piezo transducer
TRANSDUCER_FACE_H = 2.20    # face height above the inner bottom of the cell
PLATFORM_H = 4.00           # aluminium platform (B)
JACK_H_MIN, JACK_H_MAX = 3.0, 26.0
LASER_LEN = 12.0
MIRROR_W = 7.5
LENS_D = 5.0
SCREEN_W = 30.0
TABLE_W, TABLE_H = 192.0, 130.0
SAT_LIMIT_G_PER_L = 360.0   # NaCl solubility limit


# --------------------------------------------------------------------------
# Physics helpers
# --------------------------------------------------------------------------
def v_water(Tc):
    """Speed of sound in (mineral) water, m/s.  Marczak 1997 polynomial.

    Figure 3 of the question paper is this curve; reading it by eye at 22 C
    gives ~1484 m/s (the organisers' value), 0.3 % below the polynomial,
    which is well inside graph-reading precision.
    """
    return (1402.385 + 5.038813 * Tc - 5.799136e-2 * Tc ** 2
            + 3.287156e-4 * Tc ** 3 - 1.398845e-6 * Tc ** 4
            + 2.787860e-9 * Tc ** 5)


def bessel_j_list(x, nmax):
    """J_0..J_nmax(x) by Miller's downward recurrence (stdlib only)."""
    if abs(x) < 1e-12:
        return [1.0] + [0.0] * nmax
    N = int(nmax + 30 + 1.6 * abs(x))
    jp, jc = 0.0, 1e-30
    out = [0.0] * (nmax + 1)
    ssum = 0.0
    for n in range(N, 0, -1):
        jm = 2.0 * n / x * jc - jp
        jp, jc = jc, jm
        if n - 1 <= nmax:
            out[n - 1] = jc
        if (n - 1) % 2 == 0 and n - 1 > 0:
            ssum += 2.0 * jc
        if abs(jc) > 1e100:
            sc = 1e-100
            jp *= sc
            jc *= sc
            ssum *= sc
            out = [v * sc for v in out]
    norm = jc + ssum          # jc is now J_0 (unnormalised)
    return [v / norm for v in out]


def quantize(value, step):
    return round(value / step) * step


# --------------------------------------------------------------------------
# Hidden, per-session randomised parameters
# --------------------------------------------------------------------------
class Session:
    def __init__(self, seed=None):
        self.seed = seed if seed is not None else random.randrange(1, 10 ** 9)
        r = random.Random(self.seed)
        self.rng = r

        # ---- true, hidden physical parameters -------------------------
        self.f_true = 1.786e6 * r.uniform(0.985, 1.015)      # Hz
        self.lam_air = r.uniform(657e-9, 663e-9)             # m
        self.g_wall = r.uniform(0.495, 0.515)                # cm
        self.n_w = 1.3330
        self.n_g = 1.500
        self.n_air = 1.0000
        self.n_syrup = r.uniform(1.405, 1.435)
        self.v_syrup0 = r.uniform(1858.0, 1902.0)            # m/s at 22 C
        self.k_salt = r.uniform(1150.0, 1230.0)              # dv/dC_s
        salt_per_litre = r.uniform(190.0, 260.0)             # g / L
        self.C_unknown = salt_per_litre / (1000.0 + salt_per_litre)
        self.unknown_g_per_L = salt_per_litre
        self.T_ambient = r.uniform(24.5, 27.5)               # C

        # ---- acousto-optic / visibility model -------------------------
        self.RN0 = r.uniform(26.0, 34.0)     # Raman-Nath parameter at z = 0
        self.z0_water = r.uniform(5.0, 7.5)  # cm, amplitude decay length
        self.z0_syrup = r.uniform(1.2, 1.9)
        self.syrup_amp = r.uniform(0.42, 0.58)
        self.I_thresh = r.uniform(6.0e-4, 1.2e-3)
        self.best_rot = r.uniform(0.0, 180.0)   # best laser rotation, deg
        self.meas_seed = r.randrange(1, 10 ** 9)

    # ---- media -------------------------------------------------------
    def sound_speed(self, medium, Tc, C_s=0.0):
        if medium == "syrup":
            return self.v_syrup0 - 2.0 * (Tc - 22.0)
        return v_water(Tc) + self.k_salt * C_s

    def n_liquid(self, medium):
        # The paper instructs that n of the salt solution may be taken
        # unchanged (1.333); the forward model honours that instruction so
        # that the calibration curve stays linear, as the marking scheme
        # expects.
        return self.n_syrup if medium == "syrup" else self.n_w

    def lambda_s(self, medium, Tc, C_s=0.0):
        return self.sound_speed(medium, Tc, C_s) / self.f_true   # metres

    # ---- acousto-optic strength --------------------------------------
    def raman_nath(self, medium, z_cm, chord_frac, rot_deg):
        if z_cm < 0:
            return 0.0
        if medium == "syrup":
            v = self.RN0 * self.syrup_amp * math.exp(-z_cm / self.z0_syrup)
        else:
            v = self.RN0 * math.exp(-z_cm / self.z0_water)
        return max(0.0, v * chord_frac)

    def visibility(self, rot_deg):
        d = math.radians(2.0 * (rot_deg - self.best_rot))
        return 0.55 + 0.45 * (0.5 + 0.5 * math.cos(d))

    # ---- reproducible measurement noise ------------------------------
    def noise(self, key, sigma):
        h = (hash((self.meas_seed, key)) & 0x7FFFFFFF)
        return random.Random(h).gauss(0.0, sigma)


# --------------------------------------------------------------------------
# 2-D vector helpers (top view of the optical table, x right, y down, cm)
# --------------------------------------------------------------------------
def vadd(a, b):
    return (a[0] + b[0], a[1] + b[1])


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def vmul(a, s):
    return (a[0] * s, a[1] * s)


def vdot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def vlen(a):
    return math.hypot(a[0], a[1])


def vnorm(a):
    L = vlen(a)
    return (a[0] / L, a[1] / L) if L > 1e-12 else (1.0, 0.0)


def deg2vec(d):
    r = math.radians(d)
    return (math.cos(r), math.sin(r))


def refract(d, n_surf, n1, n2):
    """Vector Snell.  n_surf is the unit normal pointing towards the
    incoming side.  Returns the refracted unit direction, or None on TIR."""
    eta = n1 / n2
    cosi = -vdot(n_surf, d)
    if cosi < 0:
        n_surf = vmul(n_surf, -1.0)
        cosi = -vdot(n_surf, d)
    k = 1.0 - eta * eta * (1.0 - cosi * cosi)
    if k < 0.0:
        return None
    return vnorm(vadd(vmul(d, eta), vmul(n_surf, eta * cosi - math.sqrt(k))))


def box_hit(p, d, cx, cy, hw, hh):
    """Slab intersection with an axis-aligned box.
    Returns (t_enter, n_enter, t_exit, n_exit) or None."""
    tmin, tmax = -1e18, 1e18
    n_in, n_out = (0.0, 0.0), (0.0, 0.0)
    for axis, c, h in ((0, cx, hw), (1, cy, hh)):
        o, dd = p[axis], d[axis]
        lo, hi = c - h, c + h
        if abs(dd) < 1e-12:
            if o < lo or o > hi:
                return None
            continue
        t1, t2 = (lo - o) / dd, (hi - o) / dd
        nm = [0.0, 0.0]
        nm[axis] = -1.0 if dd > 0 else 1.0     # normal of the entry face
        nn_in = tuple(nm)
        nm2 = [0.0, 0.0]
        nm2[axis] = 1.0 if dd > 0 else -1.0
        nn_out = tuple(nm2)
        if t1 > t2:
            t1, t2 = t2, t1
        if t1 > tmin:
            tmin, n_in = t1, nn_in
        if t2 < tmax:
            tmax, n_out = t2, nn_out
    if tmax < max(tmin, 1e-9):
        return None
    return tmin, n_in, tmax, n_out


def seg_hit(p, d, a, b):
    """Ray/segment intersection.  Returns (t, unit normal) or None."""
    e = vsub(b, a)
    den = d[0] * (-e[1]) - d[1] * (-e[0])
    if abs(den) < 1e-12:
        return None
    q = vsub(a, p)
    t = (q[0] * (-e[1]) - q[1] * (-e[0])) / den
    u = (d[0] * q[1] - d[1] * q[0]) / den
    if t < 1e-6 or not (0.0 <= u <= 1.0):
        return None
    n = vnorm((-e[1], e[0]))
    if vdot(n, d) > 0:
        n = vmul(n, -1.0)
    return t, n


# --------------------------------------------------------------------------
# Apparatus items placed on the table
# --------------------------------------------------------------------------
class Item:
    def __init__(self, kind, x, y, ang=0.0, parent=None, **kw):
        self.kind = kind
        self.x = x
        self.y = y
        self.ang = ang
        self.parent = parent
        self.data = dict(kw)

    def pos(self):
        return (self.x, self.y)


class Cell:
    """State of one of the three glass cells (A)."""

    def __init__(self, idx, g_wall):
        self.idx = idx
        self.g = g_wall
        self.medium = "none"          # none | water | salt | unknown | syrup
        self.volume_L = 0.0
        self.salt_g = 0.0
        self.salt_added_g = 0.0       # only what the student weighed in
        self.temp = None              # C, None while empty
        self.stirred = True

    @property
    def area(self):
        return CELL_INNER * CELL_INNER          # cm^2

    @property
    def depth(self):
        return min(CELL_HEIGHT, self.volume_L * 1000.0 / self.area)

    @property
    def C_s(self):
        if self.medium in ("salt", "unknown"):
            m_w = self.volume_L * 1000.0
            return self.salt_g / (self.salt_g + m_w) if m_w > 0 else 0.0
        return 0.0

    def label(self):
        return {"none": T("비어 있음", "empty"),
                "water": T("생수", "mineral water"),
                "salt": T("소금물", "salt solution"),
                "unknown": T("미지 농도 용액", "unknown solution"),
                "syrup": T("옥수수 시럽", "corn syrup")}[self.medium]


# --------------------------------------------------------------------------
# Optical bench forward model
# --------------------------------------------------------------------------
class Bench:
    """Holds every placed item and performs the ray trace + pattern model."""

    def __init__(self, session):
        self.s = session
        self.items = {}
        self.cells = [Cell(i + 1, session.g_wall) for i in range(3)]
        self.active_cell = 0
        self.laser_on = False
        self.transducer_on = False
        self.laser_rot = 0.0          # rotation of the laser about its axis
        self.plate_submerged = False
        self.plate_gap = 0.50         # cm above the transducer face
        self.plate_tilt = 0.0         # degrees, 0 = perfectly parallel
        self.t_last = time.time()

    # ---------------- item bookkeeping -------------------------------
    def add(self, kind, x, y, **kw):
        key = kind
        n = 1
        while key in self.items:
            n += 1
            key = "%s%d" % (kind, n)
        self.items[key] = Item(kind, x, y, **kw)
        return key

    def get(self, kind):
        for k, it in self.items.items():
            if it.kind == kind:
                return it
        return None

    def all(self, kind):
        return [it for it in self.items.values() if it.kind == kind]

    def cell(self):
        return self.cells[self.active_cell]

    # ---------------- heights ----------------------------------------
    def cell_base_height(self):
        return PLATFORM_H if self.get("platform") else 0.0

    def face_height(self):
        c = self.get("cell")
        if not c:
            return 0.0
        return self.cell_base_height() + self.cell().g + TRANSDUCER_FACE_H

    def beam_height(self):
        las = self.get("laser")
        if not las:
            return 0.0
        jack = self.items.get(las.parent)
        return jack.data.get("h", 12.0) if jack else 12.0

    # ---------------- thermal drift ----------------------------------
    def tick(self):
        now = time.time()
        dt = min(5.0, now - self.t_last)
        self.t_last = now
        for c in self.cells:
            if c.medium == "none":
                c.temp = None
                continue
            if c.temp is None:
                c.temp = self.s.T_ambient
            drive = 0.0
            if self.transducer_on and c is self.cell() and self.transducer_wet():
                drive = 0.0090
            c.temp += drive * dt
            c.temp += (self.s.T_ambient - c.temp) * (dt / 900.0)
            c.temp = min(c.temp, 45.0)

    def transducer_wet(self):
        c = self.cell()
        tr = self.get("transducer")
        return bool(tr) and c.medium != "none" and c.depth > TRANSDUCER_FACE_H + 0.4

    # ================= ray tracing ===================================
    def cell_pass(self, p, d):
        """Trace a ray through the glass cell.  Returns dict or None."""
        c_it = self.get("cell")
        if not c_it:
            return None
        cell = self.cell()
        g = cell.g
        hw_out = CELL_INNER / 2.0 + g
        hw_in = CELL_INNER / 2.0
        n_air, n_g = self.s.n_air, self.s.n_g
        n_l = self.s.n_liquid(cell.medium) if cell.medium != "none" else n_air

        hit = box_hit(p, d, c_it.x, c_it.y, hw_out, hw_out)
        if hit is None or hit[0] < 1e-6:
            return None
        t_in, nrm, _, _ = hit
        p1 = vadd(p, vmul(d, t_in))
        pts = [p1]
        d1 = refract(d, nrm, n_air, n_g)
        if d1 is None:
            return None

        info = {"entry_outer": p1, "pts": pts, "a": None, "b": None,
                "chord": 0.0, "liquid_seg": None, "grating": None}

        hin = box_hit(p1, d1, c_it.x, c_it.y, hw_in, hw_in)
        if hin is None or cell.medium == "none":
            # the beam clips a corner, or the cell is empty: glass -> air
            hout = box_hit(p1, d1, c_it.x, c_it.y, hw_out, hw_out)
            if hout is None:
                return None
            if hin is not None and cell.medium == "none":
                # empty cell: glass/air/glass, treat inner box as air
                s_in, m_in, s_out, m_out = hin
                p2 = vadd(p1, vmul(d1, s_in))
                d2 = refract(d1, m_in, n_g, n_air)
                if d2 is None:
                    return None
                pts.append(p2)
                h2 = box_hit(p2, d2, c_it.x, c_it.y, hw_in, hw_in)
                p3 = vadd(p2, vmul(d2, h2[2]))
                d3 = refract(d2, h2[3], n_air, n_g)
                if d3 is None:
                    return None
                pts.append(p3)
                h3 = box_hit(p3, d3, c_it.x, c_it.y, hw_out, hw_out)
                p4 = vadd(p3, vmul(d3, h3[2]))
                d4 = refract(d3, h3[3], n_g, n_air)
                if d4 is None:
                    return None
                pts.append(p4)
                info["exit"] = p4
                info["dir_out"] = d4
                info["liquid_seg"] = (p2, p3)
                return info
            p4 = vadd(p1, vmul(d1, hout[2]))
            d4 = refract(d1, hout[3], n_g, n_air)
            if d4 is None:
                return None
            pts.append(p4)
            info["exit"] = p4
            info["dir_out"] = d4
            return info

        s_in, m_in, _, _ = hin
        p2 = vadd(p1, vmul(d1, s_in))
        d2 = refract(d1, m_in, n_g, n_l)
        if d2 is None:
            return None
        pts.append(p2)

        h2 = box_hit(p2, d2, c_it.x, c_it.y, hw_in, hw_in)
        p3 = vadd(p2, vmul(d2, h2[2]))
        d3 = refract(d2, h2[3], n_l, n_g)
        if d3 is None:
            return None
        pts.append(p3)

        h3 = box_hit(p3, d3, c_it.x, c_it.y, hw_out, hw_out)
        p4 = vadd(p3, vmul(d3, h3[2]))
        d4 = refract(d3, h3[3], n_g, n_air)
        if d4 is None:
            return None
        pts.append(p4)

        info["exit"] = p4
        info["dir_out"] = d4
        info["liquid_seg"] = (p2, p3)

        # ---- interaction with the ultrasonic column ------------------
        hold = self.get("holder")
        tr = self.get("transducer")
        if hold and tr:
            axis = (hold.x, hold.y)
            v = vsub(p3, p2)
            Lseg = vlen(v)
            u = vnorm(v)
            t_close = max(0.0, min(Lseg, vdot(vsub(axis, p2), u)))
            closest = vadd(p2, vmul(u, t_close))
            r = vlen(vsub(axis, closest))
            R = TRANSDUCER_D / 2.0
            if r < R:
                info["chord"] = math.sqrt(max(0.0, 1.0 - (r / R) ** 2))
                info["a"] = t_close
                info["b"] = Lseg - t_close
                info["grating"] = closest
        return info

    def trace(self):
        """Full ray trace.  Returns dict with the polyline and geometry."""
        las = self.get("laser")
        out = {"poly": [], "hit_screen": None, "S1": None, "S2": None,
               "cell": None, "lens": None, "ok": False, "spot_u": 0.0}
        if not las or not self.laser_on:
            return out
        d = deg2vec(las.ang)
        p = vadd(las.pos(), vmul(d, LASER_LEN / 2.0))
        poly = [p]
        cellinfo = None
        lens_pt = None
        path_after_cell = 0.0
        path_before_cell_from_lens = None
        mirrors = self.all("mirror")
        scr = self.get("screen")
        lens = self.get("lens")

        for _ in range(14):
            cands = []
            c_it = self.get("cell")
            if c_it and cellinfo is None:
                ci = self.cell_pass(p, d)
                if ci:
                    t = vlen(vsub(ci["entry_outer"], p))
                    cands.append((t, "cell", ci))
            for m in mirrors:
                a = vadd(m.pos(), vmul(deg2vec(m.ang + 90), MIRROR_W / 2))
                b = vadd(m.pos(), vmul(deg2vec(m.ang + 90), -MIRROR_W / 2))
                h = seg_hit(p, d, a, b)
                if h:
                    cands.append((h[0], "mirror", (m, h[1])))
            if scr:
                a = vadd(scr.pos(), vmul(deg2vec(scr.ang + 90), SCREEN_W / 2))
                b = vadd(scr.pos(), vmul(deg2vec(scr.ang + 90), -SCREEN_W / 2))
                h = seg_hit(p, d, a, b)
                if h:
                    cands.append((h[0], "screen", (scr, a, b, h[0])))
            if lens and lens_pt is None:
                a = vadd(lens.pos(), vmul(deg2vec(lens.ang + 90), LENS_D / 2))
                b = vadd(lens.pos(), vmul(deg2vec(lens.ang + 90), -LENS_D / 2))
                h = seg_hit(p, d, a, b)
                if h:
                    cands.append((h[0], "lens", lens))
            if not cands:
                poly.append(vadd(p, vmul(d, 400.0)))
                break
            cands.sort(key=lambda c: c[0])
            t, kind, obj = cands[0]

            if kind == "lens":
                lens_pt = vadd(p, vmul(d, t))
                poly.append(lens_pt)
                p = lens_pt
                path_before_cell_from_lens = 0.0
                continue
            if kind == "cell":
                ci = obj
                if path_before_cell_from_lens is not None:
                    path_before_cell_from_lens += vlen(vsub(ci["entry_outer"], p))
                poly.extend(ci["pts"])
                cellinfo = ci
                p, d = ci["exit"], ci["dir_out"]
                continue
            if kind == "mirror":
                m, n = obj
                q = vadd(p, vmul(d, t))
                poly.append(q)
                if cellinfo:
                    path_after_cell += t
                d = vnorm(vsub(d, vmul(n, 2.0 * vdot(d, n))))
                p = q
                continue
            if kind == "screen":
                sc, a, b, tt = obj
                q = vadd(p, vmul(d, tt))
                poly.append(q)
                if cellinfo:
                    path_after_cell += tt
                out["hit_screen"] = q
                out["spot_u"] = vlen(vsub(q, a)) - SCREEN_W / 2.0
                break

        out["poly"] = poly
        out["cell"] = cellinfo
        out["lens"] = lens_pt
        out["S2"] = path_after_cell if cellinfo else None
        out["S1"] = path_before_cell_from_lens
        out["ok"] = out["hit_screen"] is not None and cellinfo is not None
        return out

    # ================= optical patterns ==============================
    def diffraction(self):
        """Raman-Nath diffraction orders.  Returns list of (i, y_cm, I)."""
        tr = self.trace()
        if not tr["ok"] or not self.transducer_on or not self.transducer_wet():
            return [], tr
        ci = tr["cell"]
        if ci["b"] is None or ci["chord"] <= 0.0:
            return [], tr
        cell = self.cell()
        if not cell.stirred:
            return [], tr
        z = self.beam_height() - self.face_height()
        if z < 0.05 or z > cell.depth - 0.2:
            return [], tr
        medium = cell.medium
        lam_s = self.s.lambda_s(medium, cell.temp or self.s.T_ambient, cell.C_s)
        lam_a = self.s.lam_air
        n_l = self.s.n_liquid(medium)
        n_g, n_a = self.s.n_g, self.s.n_air
        vRN = self.s.raman_nath(medium, z, ci["chord"], self.laser_rot)
        if vRN < 0.35:
            return [], tr
        vis = self.s.visibility(self.laser_rot)
        thr = self.s.I_thresh / vis
        nmax = int(vRN + 14)
        J = bessel_j_list(vRN, nmax)
        imax = 0
        for i in range(nmax + 1):
            if J[i] ** 2 >= thr:
                imax = i          # the envelope, not an interior zero, sets the edge
        b = ci["b"]
        g = cell.g
        L = tr["S2"]
        orders = []
        for i in range(0, imax + 1):
            I = J[i] ** 2
            s_w = i * n_a * lam_a / (n_l * lam_s)
            if abs(s_w) >= 1.0:
                break
            th_w = math.asin(s_w)
            th_g = math.asin(max(-1.0, min(1.0, n_l * s_w / n_g)))
            th_a = math.asin(max(-1.0, min(1.0, n_l * s_w / n_a)))
            y = (b * math.tan(th_w) + g * math.tan(th_g) + L * math.tan(th_a))
            orders.append((i, y, I))
        full = [(-i, -y, I) for (i, y, I) in orders[1:]][::-1] + orders
        return full, tr

    def standing_wave(self):
        """Projection method.  Returns dict describing the band pattern."""
        tr = self.trace()
        res = {"ok": False, "trace": tr}
        if not tr["ok"] or tr["lens"] is None:
            return res
        if not self.transducer_on or not self.transducer_wet():
            return res
        if not self.plate_submerged:
            return res
        ci = tr["cell"]
        if ci["a"] is None:
            return res
        cell = self.cell()
        if not cell.stirred:
            return res
        lens = self.get("lens")
        fL = lens.data.get("f", 5.0)
        S1 = tr["S1"]
        S2 = tr["S2"]
        if S1 is None or S1 <= fL + 0.5:
            return res
        g, n_g, n_w, n_a = cell.g, self.s.n_g, self.s.n_liquid(cell.medium), self.s.n_air
        a = ci["a"]
        ab = ci["a"] + ci["b"]
        num = (S1 - fL) / n_a + 2 * g / n_g + ab / n_w + S2 / n_a
        den = (S1 - fL) / n_a + g / n_g + a / n_w
        M = num / den
        lam_s = self.s.lambda_s(cell.medium, cell.temp or self.s.T_ambient,
                                cell.C_s) * 100.0        # cm
        # beam must sit inside the transducer / plate gap
        z = self.beam_height() - self.face_height()
        gap = self.plate_gap
        if z < -0.35 or z > gap + 0.35:
            return res
        contrast = math.exp(-(self.plate_tilt / 0.9) ** 2)
        contrast *= min(1.0, ci["chord"] * 1.4)
        amp = self.s.raman_nath(cell.medium, max(0.0, z), ci["chord"], self.laser_rot)
        contrast *= min(1.0, amp / 8.0)
        if contrast < 0.08:
            return res
        res.update(ok=True, M=M, period=M * lam_s / 2.0,
                   extent=M * gap, contrast=contrast, S1=S1, S2=S2,
                   a=a, ab=ab, gap=gap)
        return res


# --------------------------------------------------------------------------
# Drawing helpers
# --------------------------------------------------------------------------
LIQ_COLOR = {"none": "", "water": "#cfe8f5", "salt": "#d3ebf6",
             "unknown": "#cfe0ee", "syrup": "#f0d391"}

PART_LIST = [
    ("cell", "A", T("유리 셀", "Glass cell"), 1),
    ("platform", "B", T("알루미늄 받침대", "Al platform"), 1),
    ("transducer", "C", T("압전 변환기", "Piezo transducer"), 1),
    ("holder", "D1", T("변환기 홀더", "Holder"), 1),
    ("plate", "D2", T("조절판(반사판)", "Adjustable plate"), 1),
    ("laser", "E", T("레이저 포인터", "Laser pointer"), 1),
    ("screen", "F", T("스크린 보드", "Screen board"), 1),
    ("jack", "G", T("랩잭", "Lab jack"), 4),
    ("mirror", "H", T("거울", "Mirror"), 2),
    ("lens", "I", T("렌즈", "Lens"), 1),
    ("thermo", "Y", T("온도계", "Thermometer"), 1),
]

PART_SIZE = {"cell": (12.2, 12.2), "platform": (26.0, 26.0),
             "transducer": (2.6, 2.6), "holder": (11.0, 2.6),
             "plate": (8.0, 8.0), "laser": (LASER_LEN, 3.0),
             "screen": (SCREEN_W, 1.6), "jack": (10.0, 10.0),
             "mirror": (1.0, MIRROR_W), "lens": (0.9, LENS_D),
             "thermo": (1.2, 1.2)}


def rot_poly(cx, cy, w, h, ang):
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    out = []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        out.append((cx + dx * ca - dy * sa, cy + dx * sa + dy * ca))
    return out


class TopView(tk.Canvas):
    """Plan view of the optical table, shared by the assembly and bench tabs."""

    SC = 3.40            # px per cm

    def __init__(self, master, bench, mode="bench", on_select=None, **kw):
        w = int(TABLE_W * self.SC) + 24
        h = int(TABLE_H * self.SC) + 24
        tk.Canvas.__init__(self, master, width=w, height=h,
                           bg="#7d1f22", highlightthickness=0, **kw)
        self.bench = bench
        self.mode = mode
        self.on_select = on_select
        self.sel = None
        self.ghost = None
        self.drag = None
        self.tape_mode = False
        self.tape_pts = []
        self.tape_text = ""
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._motion)
        self.bind("<ButtonRelease-1>", self._release)

    # ---- coordinate transforms --------------------------------------
    def px(self, x, y):
        return 12 + x * self.SC, 12 + y * self.SC

    def cm(self, px_, py_):
        return (px_ - 12) / self.SC, (py_ - 12) / self.SC

    def poly_px(self, pts):
        out = []
        for x, y in pts:
            a, b = self.px(x, y)
            out.extend([a, b])
        return out

    # ---- item drawing ------------------------------------------------
    def _draw_item(self, key, it):
        b = self.bench
        k = it.kind
        sel = (key == self.sel)
        oc = "#ffe680" if sel else "#20242b"
        ow = 3 if sel else 1
        if k == "platform":
            self.create_polygon(self.poly_px(rot_poly(it.x, it.y, 26, 26, 0)),
                                fill="#9aa3ad", outline=oc, width=ow)
            self.create_text(*self.px(it.x, it.y - 11), text="B",
                             fill="#33383f", font=("Arial", 8, "bold"))
        elif k == "cell":
            cell = b.cell()
            g = cell.g
            self.create_polygon(self.poly_px(rot_poly(it.x, it.y, CELL_INNER + 2 * g,
                                                      CELL_INNER + 2 * g, 0)),
                                fill="#bcd9e6", outline=oc, width=ow + 1)
            fill = LIQ_COLOR[cell.medium] or "#e8f4fa"
            self.create_polygon(self.poly_px(rot_poly(it.x, it.y, CELL_INNER,
                                                      CELL_INNER, 0)),
                                fill=fill, outline="#8fb6c6", width=1)
            self.create_text(*self.px(it.x - CELL_INNER / 2 + 0.9,
                                      it.y - CELL_INNER / 2 + 0.9),
                             text="A%d" % cell.idx, fill="#40606e",
                             font=("Arial", 8, "bold"))
        elif k == "holder":
            self.create_polygon(self.poly_px(rot_poly(it.x, it.y, 11.0, 2.6, 0)),
                                fill="#f3f3ef", outline=oc, width=ow)
            x0, y0 = self.px(it.x - 1.35, it.y - 1.35)
            x1, y1 = self.px(it.x + 1.35, it.y + 1.35)
            self.create_oval(x0, y0, x1, y1, outline="#9aa0a6", width=1)
        elif k == "transducer":
            r = TRANSDUCER_D / 2.0
            x0, y0 = self.px(it.x - r, it.y - r)
            x1, y1 = self.px(it.x + r, it.y + r)
            col = "#2f6f9e" if b.transducer_on else "#4c5560"
            self.create_oval(x0, y0, x1, y1, fill=col, outline=oc, width=ow)
            if b.transducer_on:
                for rr in (r * 1.6, r * 2.4):
                    a0, b0 = self.px(it.x - rr, it.y - rr)
                    a1, b1 = self.px(it.x + rr, it.y + rr)
                    self.create_oval(a0, b0, a1, b1, outline="#7fc8ef", dash=(2, 3))
        elif k == "plate":
            st = () if b.plate_submerged else (4, 3)
            self.create_polygon(self.poly_px(rot_poly(it.x, it.y, 8, 8, 0)),
                                fill="", outline="#4e8b3a" if b.plate_submerged
                                else "#7d8a72", width=2, dash=st)
            for dx in (-3.4, 3.4):
                for dy in (-3.4, 3.4):
                    a, c = self.px(it.x + dx, it.y + dy)
                    self.create_oval(a - 2, c - 2, a + 2, c + 2,
                                     fill="#c8ccd0", outline="")
        elif k == "jack":
            self.create_polygon(self.poly_px(rot_poly(it.x, it.y, 10, 10, 0)),
                                fill="#2b2f36", outline=oc, width=ow)
            p = rot_poly(it.x, it.y, 8.4, 8.4, 0)
            self.create_line(*self.poly_px([p[0], p[2]]), fill="#6d7480")
            self.create_line(*self.poly_px([p[1], p[3]]), fill="#6d7480")
            self.create_text(*self.px(it.x, it.y),
                             text="%.1f" % it.data.get("h", 12.0),
                             fill="#c8ced8", font=("Arial", 7))
        elif k == "laser":
            self.create_polygon(self.poly_px(rot_poly(it.x, it.y, LASER_LEN, 3.0, it.ang)),
                                fill="#1b1d21", outline=oc, width=ow)
            nose = vadd(it.pos(), vmul(deg2vec(it.ang), LASER_LEN / 2 - 0.7))
            self.create_polygon(self.poly_px(rot_poly(nose[0], nose[1], 1.6, 2.0, it.ang)),
                                fill="#c9302c", outline="")
        elif k == "mirror":
            self.create_polygon(self.poly_px(rot_poly(it.x, it.y, 1.0, MIRROR_W, it.ang)),
                                fill="#20303a", outline=oc, width=ow)
            f = vadd(it.pos(), vmul(deg2vec(it.ang), 0.45))
            self.create_polygon(self.poly_px(rot_poly(f[0], f[1], 0.25, MIRROR_W, it.ang)),
                                fill="#9fd8ee", outline="")
        elif k == "lens":
            self.create_polygon(self.poly_px(rot_poly(it.x, it.y, 0.9, LENS_D, it.ang)),
                                fill="#cfe9f2", outline=oc, width=ow)
            self.create_text(*self.px(it.x, it.y - LENS_D / 2 - 1.4),
                             text="f=%.0fcm" % it.data.get("f", 5.0),
                             fill="#e7e7e7", font=("Arial", 7))
        elif k == "screen":
            self.create_polygon(self.poly_px(rot_poly(it.x, it.y, 1.6, SCREEN_W, it.ang)),
                                fill="#f2efe6", outline=oc, width=ow)
        elif k == "thermo":
            a, c = self.px(it.x, it.y)
            self.create_oval(a - 3, c - 3, a + 3, c + 3, fill="#c9302c", outline="#eee")

    # ---- full redraw --------------------------------------------------
    def redraw(self):
        self.delete("all")
        for gx in range(0, int(TABLE_W) + 1, 10):
            a, c = self.px(gx, 0)
            a2, c2 = self.px(gx, TABLE_H)
            self.create_line(a, c, a2, c2, fill="#8c2b2e")
        for gy in range(0, int(TABLE_H) + 1, 10):
            a, c = self.px(0, gy)
            a2, c2 = self.px(TABLE_W, gy)
            self.create_line(a, c, a2, c2, fill="#8c2b2e")
        order = ["platform", "jack", "cell", "holder", "transducer", "plate",
                 "thermo", "laser", "mirror", "lens", "screen"]
        for kind in order:
            for key, it in self.bench.items.items():
                if it.kind == kind:
                    self._draw_item(key, it)
        if self.mode == "bench":
            self._draw_beam()
            self._draw_tape()
        if self.ghost:
            kind, x, y, ok = self.ghost
            w, h = PART_SIZE.get(kind, (6, 6))
            self.create_polygon(self.poly_px(rot_poly(x, y, w, h, 0)),
                                fill="", width=2,
                                outline="#7CFC00" if ok else "#ff5555", dash=(4, 3))

    def _draw_beam(self):
        b = self.bench
        if not b.laser_on:
            return
        tr = b.trace()
        poly = tr["poly"]
        if len(poly) < 2:
            return
        pts = self.poly_px(poly)
        self.create_line(*pts, fill="#ff3b30", width=2)
        self.create_line(*pts, fill="#ffb0aa", width=1)
        if tr["hit_screen"]:
            a, c = self.px(*tr["hit_screen"])
            self.create_oval(a - 4, c - 4, a + 4, c + 4, outline="#ffe680", width=2)

    def _draw_tape(self):
        for p in self.tape_pts:
            a, c = self.px(*p)
            self.create_line(a - 6, c, a + 6, c, fill="#ffe680", width=2)
            self.create_line(a, c - 6, a, c + 6, fill="#ffe680", width=2)
        if len(self.tape_pts) == 2:
            p0, p1 = self.tape_pts
            self.create_line(*self.poly_px([p0, p1]), fill="#ffe680",
                             width=2, dash=(6, 3))
            mx, my = self.px((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
            self.create_text(mx, my - 12, text=self.tape_text, fill="#fff8d0",
                             font=("Consolas", 10, "bold"))

    # ---- anchors for the measuring tape --------------------------------
    def anchors(self):
        b = self.bench
        out = []
        tr = b.trace()
        names = []
        if tr["poly"]:
            for i, p in enumerate(tr["poly"]):
                names.append((p, "beam%d" % i))
        for key, it in b.items.items():
            if it.kind == "cell":
                g = b.cell().g
                for s in (-1, 1):
                    out.append(((it.x + s * (CELL_INNER / 2 + g), it.y), "cell_out%d" % s))
                    out.append(((it.x + s * CELL_INNER / 2, it.y), "cell_in%d" % s))
                    out.append(((it.x, it.y + s * (CELL_INNER / 2 + g)), "cell_outy%d" % s))
                    out.append(((it.x, it.y + s * CELL_INNER / 2), "cell_iny%d" % s))
            elif it.kind in ("transducer", "holder", "lens", "mirror", "laser", "screen"):
                out.append(((it.x, it.y), key))
        out.extend([(p, n) for p, n in names])
        return out

    def snap(self, x, y):
        best, bd, bn = (x, y), 2.6, "free"
        for (p, n) in self.anchors():
            d = math.hypot(p[0] - x, p[1] - y)
            if d < bd:
                best, bd, bn = p, d, n
        return best, bn

    # ---- mouse ---------------------------------------------------------
    def _press(self, ev):
        x, y = self.cm(ev.x, ev.y)
        if self.tape_mode:
            p, n = self.snap(x, y)
            if len(self.tape_pts) >= 2:
                self.tape_pts = []
                self.tape_text = ""
            self.tape_pts.append(p)
            self._tape_names = getattr(self, "_tape_names", [])
            if len(self.tape_pts) == 1:
                self._tape_names = [n]
            else:
                self._tape_names.append(n)
                p0 = self.tape_pts[0]
                key = tuple(sorted(self._tape_names))
                nz = self.bench.s
                d = math.hypot(p0[0] - p[0], p0[1] - p[1]) + nz.noise(key, 0.045)
                dx = max(0.0, abs(p0[0] - p[0]) + nz.noise(key + ("x",), 0.045))
                dy = max(0.0, abs(p0[1] - p[1]) + nz.noise(key + ("y",), 0.045))
                self.tape_text = "%.1f cm  (dx %.1f / dy %.1f)" % (
                    quantize(d, 0.1), quantize(dx, 0.1), quantize(dy, 0.1))
            self.redraw()
            return
        hit = None
        for key, it in reversed(list(self.bench.items.items())):
            w, h = PART_SIZE.get(it.kind, (6, 6))
            if abs(x - it.x) <= max(w, h) / 2 and abs(y - it.y) <= max(w, h) / 2:
                hit = key
                break
        self.sel = hit
        if hit:
            it = self.bench.items[hit]
            self.drag = (hit, x - it.x, y - it.y)
        if self.on_select:
            self.on_select(hit)
        self.redraw()

    def _motion(self, ev):
        if not self.drag or self.tape_mode:
            return
        key, dx, dy = self.drag
        it = self.bench.items[key]
        ox, oy = it.x, it.y
        x, y = self.cm(ev.x, ev.y)
        nx, ny = x - dx, y - dy
        if it.kind in ("holder",):
            c = self.bench.get("cell")
            if c:
                lim = CELL_INNER / 2 - 1.6
                nx = max(c.x - lim, min(c.x + lim, nx))
                ny = c.y
        it.x = max(2.0, min(TABLE_W - 2.0, nx))
        it.y = max(2.0, min(TABLE_H - 2.0, ny))
        for k2, it2 in self.bench.items.items():
            if it2.parent == key:
                it2.x, it2.y = it.x, it.y
        if it.kind == "holder":
            for k2, it2 in self.bench.items.items():
                if it2.kind in ("transducer", "plate"):
                    it2.x, it2.y = it.x, it.y
        if it.kind == "cell":
            ddx, ddy = it.x - ox, it.y - oy
            for k2, it2 in self.bench.items.items():
                if it2.kind in ("holder", "transducer", "plate", "thermo"):
                    it2.x += ddx
                    it2.y += ddy
        self.redraw()
        if self.on_select:
            self.on_select(self.sel)

    def _release(self, ev):
        self.drag = None


# --------------------------------------------------------------------------
# Screen (F) view - what the observer actually sees on the answer sheet
# --------------------------------------------------------------------------
class ScreenView(tk.Frame):
    W, H = 470, 640

    def __init__(self, master, bench):
        tk.Frame.__init__(self, master, bg="#20242b")
        self.bench = bench
        self.scale = 24.0          # px per cm
        self.pan = 0.0             # cm
        self.marks = []            # y positions in cm
        top = tk.Frame(self, bg="#20242b")
        top.pack(fill="x")
        tk.Label(top, text=T("스크린 (F)", "Screen (F)"), fg="#e8e8e8",
                 bg="#20242b", font=("Arial", 10, "bold")).pack(side="left", padx=6)
        tk.Button(top, text=T("표시 지우기", "clear marks"), font=("Arial", 8),
                  command=self.clear_marks).pack(side="right", padx=4)
        self.cv = tk.Canvas(self, width=self.W, height=self.H, bg="#f4f1e8",
                            highlightthickness=1, highlightbackground="#555")
        self.cv.pack(padx=4, pady=2)
        self.cv.bind("<Button-1>", self._click)
        self.cv.bind("<Button-3>", self._rclick)
        self.cv.bind("<MouseWheel>", self._wheel)
        self.cv.bind("<Button-4>", lambda e: self._zoom(1.15))
        self.cv.bind("<Button-5>", lambda e: self._zoom(1 / 1.15))
        bar = tk.Frame(self, bg="#20242b")
        bar.pack(fill="x", pady=2)
        tk.Label(bar, text=T("배율", "zoom"), fg="#ccc", bg="#20242b",
                 font=("Arial", 8)).pack(side="left", padx=(6, 2))
        self.zv = tk.DoubleVar(value=24.0)
        tk.Scale(bar, from_=8, to=70, resolution=1, orient="horizontal",
                 variable=self.zv, showvalue=0, length=120, bg="#20242b",
                 fg="#ccc", troughcolor="#333", highlightthickness=0,
                 command=lambda v: self.redraw()).pack(side="left")
        tk.Label(bar, text=T("상하", "pan"), fg="#ccc", bg="#20242b",
                 font=("Arial", 8)).pack(side="left", padx=(8, 2))
        self.pv = tk.DoubleVar(value=0.0)
        tk.Scale(bar, from_=-14, to=14, resolution=0.1, orient="horizontal",
                 variable=self.pv, showvalue=0, length=120, bg="#20242b",
                 fg="#ccc", troughcolor="#333", highlightthickness=0,
                 command=lambda v: self.redraw()).pack(side="left")
        self.info = tk.Label(self, text="", fg="#ffe680", bg="#20242b",
                             font=("Consolas", 10), anchor="w", justify="left")
        self.info.pack(fill="x", padx=6, pady=(2, 4))

    # ---- helpers ------------------------------------------------------
    def y2px(self, y_cm):
        return self.H / 2 - (y_cm - self.pv.get()) * self.zv.get()

    def px2y(self, py):
        return (self.H / 2 - py) / self.zv.get() + self.pv.get()

    def clear_marks(self):
        self.marks = []
        self.redraw()

    def _zoom(self, f):
        self.zv.set(max(8, min(70, self.zv.get() * f)))
        self.redraw()

    def _wheel(self, ev):
        self._zoom(1.15 if ev.delta > 0 else 1 / 1.15)

    def _click(self, ev):
        if ev.x < 62:
            return
        self.marks.append(self.px2y(ev.y))
        self.marks.sort()
        self.redraw()

    def _rclick(self, ev):
        if not self.marks:
            return
        y = self.px2y(ev.y)
        i = min(range(len(self.marks)), key=lambda k: abs(self.marks[k] - y))
        if abs(self.marks[i] - y) * self.zv.get() < 14:
            self.marks.pop(i)
        self.redraw()

    # ---- rendering -----------------------------------------------------
    def redraw(self):
        cv = self.cv
        cv.delete("all")
        sc = self.zv.get()
        cv.create_rectangle(0, 0, self.W, self.H, fill="#f4f1e8", outline="")
        # graduated ruler on the left edge
        cv.create_rectangle(0, 0, 60, self.H, fill="#efe9d8", outline="#b9b0a0")
        y0 = self.px2y(self.H)
        y1 = self.px2y(0)
        step = 0.1 if sc >= 22 else (0.5 if sc >= 12 else 1.0)
        n = int(math.floor(y0 / step))
        while n * step <= y1:
            yy = n * step
            py = self.y2px(yy)
            big = abs(yy - round(yy)) < 1e-6
            mid = abs(yy * 2 - round(yy * 2)) < 1e-6
            ln = 22 if big else (14 if mid else 8)
            cv.create_line(60 - ln, py, 60, py, fill="#6b6357",
                           width=2 if big else 1)
            if big:
                cv.create_text(30, py, text="%d" % round(yy), fill="#4d4639",
                               font=("Arial", 8))
            n += 1

        bench = self.bench
        tr = bench.trace()
        lines = []
        if not bench.laser_on:
            lines.append(T("레이저 꺼짐", "laser OFF"))
        elif not tr["ok"]:
            lines.append(T("빔이 스크린에 도달하지 않음",
                           "beam does not reach the screen"))
        else:
            if bench.get("lens") and tr["lens"] is not None:
                self._draw_projection()
            else:
                self._draw_diffraction()
        # marks
        for i, y in enumerate(self.marks):
            py = self.y2px(y)
            cv.create_line(self.W - 92, py, self.W - 66, py, fill="#1a6bb5", width=2)
            if len(self.marks) <= 60:
                cv.create_text(self.W - 52, py, text=str(i + 1), fill="#1a6bb5",
                               font=("Arial", 7))
        txt = ""
        if len(self.marks) >= 2:
            span = abs(self.marks[-1] - self.marks[0])
            span += bench.s.noise(("screen", round(span, 3)), 0.012)
            txt = T("표시 개수 = %d      처음↔마지막 = %.2f cm",
                    "marks = %d      first-last = %.2f cm") % (
                len(self.marks), quantize(span, 0.05))
        elif len(self.marks) == 1:
            txt = T("표시 개수 = 1", "marks = 1")
        if lines:
            txt = ("   ".join(lines) + ("      " + txt if txt else ""))
        self.info.config(text=txt)

    def _draw_diffraction(self):
        cv = self.cv
        orders, tr = self.bench.diffraction()
        cx = (60 + self.W) / 2
        if not orders:
            py = self.y2px(0.0)
            cv.create_oval(cx - 9, py - 3, cx + 9, py + 3, fill="#ff2a1a",
                           outline="")
            return
        Imax = max(o[2] for o in orders)
        for i, y, I in orders:
            py = self.y2px(y)
            if py < -10 or py > self.H + 10:
                continue
            a = max(0.0, min(1.0, (I / Imax) ** 0.42))
            # the fringes are red light on a pale answer sheet: a faint order
            # must fade towards the paper, never towards black
            r = int(244 + (222 - 244) * a)
            g = int(241 + (28 - 241) * a)
            bl = int(232 + (22 - 232) * a)
            col = "#%02x%02x%02x" % (r, g, bl)
            hw = 8 + 4 * a
            hh = max(1.3, 0.05 * self.zv.get() + 0.9)
            cv.create_oval(cx - hw, py - hh, cx + hw, py + hh, fill=col, outline="")

    def _draw_projection(self):
        cv = self.cv
        r = self.bench.standing_wave()
        cx = (60 + self.W) / 2
        if not r["ok"]:
            py = self.y2px(0.0)
            cv.create_oval(cx - 34, py - 26, cx + 34, py + 26,
                           fill="#e0763c", outline="")
            return
        per = r["period"]
        ext = r["extent"]
        con = r["contrast"]
        halfw = 60
        top = self.y2px(ext / 2.0)
        bot = self.y2px(-ext / 2.0)
        for py in range(int(max(0, top)), int(min(self.H, bot)) + 1):
            y = self.px2y(py)
            env = math.exp(-(2.0 * y / max(ext, 1e-6)) ** 6)
            I = 0.5 + 0.5 * math.cos(2 * math.pi * y / per) * con
            I *= env
            R = int(min(255, 40 + 215 * I))
            G = int(min(255, 18 + 150 * I))
            B = int(min(255, 8 + 40 * I))
            cv.create_line(cx - halfw, py, cx + halfw, py,
                           fill="#%02x%02x%02x" % (R, G, B))


# --------------------------------------------------------------------------
# Assembly rules
# --------------------------------------------------------------------------
def free_jack(bench, x, y):
    used = set(it.parent for it in bench.items.values() if it.parent)
    for key, it in bench.items.items():
        if it.kind == "jack" and key not in used:
            if abs(x - it.x) <= 5.6 and abs(y - it.y) <= 5.6:
                return key
    return None


def can_place(bench, kind, x, y):
    cell = bench.get("cell")
    hold = bench.get("holder")
    tr = bench.get("transducer")
    if kind in ("platform", "jack", "screen"):
        return True, "", (x, y), None
    if kind == "cell":
        pf = bench.get("platform")
        if pf and abs(x - pf.x) <= 13 and abs(y - pf.y) <= 13:
            return True, "", (pf.x, pf.y), None
        return True, "", (x, y), None
    if kind == "holder":
        if not cell:
            return False, T("먼저 유리 셀(A)을 테이블에 놓으세요.",
                            "Place the glass cell (A) on the table first."), None, None
        lim = CELL_INNER / 2 - 1.6
        if abs(x - cell.x) > lim + 0.6 or abs(y - cell.y) > CELL_INNER / 2:
            return False, T("홀더(D1)는 유리 셀 안쪽에 놓아야 합니다.",
                            "The holder (D1) must be placed inside the glass cell."), None, None
        return True, "", (max(cell.x - lim, min(cell.x + lim, x)), cell.y), None
    if kind == "transducer":
        if not hold:
            return False, T("압전 변환기(C)는 홀더(D1)의 원형 슬롯에 끼워야 합니다. "
                            "먼저 홀더를 셀 안에 넣으세요.",
                            "The transducer (C) goes into the circular slot of the "
                            "holder (D1).  Place the holder in the cell first."), None, None
        if math.hypot(x - hold.x, y - hold.y) > 4.0:
            return False, T("홀더의 원형 슬롯 위에 놓으세요.",
                            "Drop it onto the circular slot of the holder."), None, None
        return True, "", (hold.x, hold.y), None
    if kind == "plate":
        if not tr:
            return False, T("조절판(D2)은 변환기(C)를 홀더에 끼운 뒤 장착합니다.",
                            "Mount the adjustable plate (D2) after the transducer (C) "
                            "is in the holder."), None, None
        if math.hypot(x - hold.x, y - hold.y) > 5.5:
            return False, T("홀더(D1) 위에 장착하세요.",
                            "Mount it on the holder (D1)."), None, None
        return True, "", (hold.x, hold.y), None
    if kind in ("laser", "mirror", "lens"):
        j = free_jack(bench, x, y)
        if not j:
            return False, T("이 부품은 비어 있는 랩잭(G) 위에 올려야 합니다.",
                            "This component must be mounted on a free lab jack (G)."), None, None
        it = bench.items[j]
        return True, "", (it.x, it.y), j
    if kind == "thermo":
        if not cell:
            return False, T("온도계는 셀 안에 넣습니다.",
                            "The thermometer goes into the cell."), None, None
        if abs(x - cell.x) > CELL_INNER / 2 or abs(y - cell.y) > CELL_INNER / 2:
            return False, T("셀 안쪽에 넣으세요.", "Put it inside the cell."), None, None
        return True, "", (x, y), None
    return False, "?", None, None


class PartsBin(tk.Canvas):
    ROW = 34

    def __init__(self, master, app):
        tk.Canvas.__init__(self, master, width=232, height=len(PART_LIST) * self.ROW + 60,
                           bg="#171a1f", highlightthickness=0)
        self.app = app
        self.dragging = None
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._motion)
        self.bind("<ButtonRelease-1>", self._release)
        self.redraw()

    def counts(self):
        used = {}
        for it in self.app.bench.items.values():
            used[it.kind] = used.get(it.kind, 0) + 1
        return used

    def redraw(self):
        self.delete("all")
        used = self.counts()
        self.create_text(116, 16, text=T("부품 상자 (드래그해서 배치)",
                                         "Parts box (drag onto the table)"),
                         fill="#e6e6e6", font=("Arial", 9, "bold"))
        for i, (kind, tag, name, nmax) in enumerate(PART_LIST):
            y = 34 + i * self.ROW
            left = used.get(kind, 0) < nmax
            col = "#e8e8e8" if left else "#5a5f66"
            self.create_rectangle(8, y, 224, y + self.ROW - 4,
                                  fill="#22262d" if left else "#1b1e23",
                                  outline="#333")
            self.create_text(26, y + 15, text=tag, fill="#ffd166" if left else "#5a5f66",
                             font=("Arial", 9, "bold"))
            self.create_text(56, y + 15, text=name, fill=col, anchor="w",
                             font=("Arial", 9))
            self.create_text(214, y + 15, text="%d/%d" % (used.get(kind, 0), nmax),
                             fill="#8a929c", anchor="e", font=("Arial", 8))

    def _kind_at(self, y):
        i = int((y - 34) // self.ROW)
        if 0 <= i < len(PART_LIST):
            kind, tag, name, nmax = PART_LIST[i]
            if self.counts().get(kind, 0) < nmax:
                return kind
        return None

    def _press(self, ev):
        self.dragging = self._kind_at(ev.y)

    def _motion(self, ev):
        if not self.dragging:
            return
        tv = self.app.asm_view
        px = self.winfo_pointerx() - tv.winfo_rootx()
        py = self.winfo_pointery() - tv.winfo_rooty()
        if 0 <= px <= tv.winfo_width() and 0 <= py <= tv.winfo_height():
            x, y = tv.cm(px, py)
            ok, msg, pos, par = can_place(self.app.bench, self.dragging, x, y)
            tv.ghost = (self.dragging, x, y, ok)
        else:
            tv.ghost = None
        tv.redraw()

    def _release(self, ev):
        kind, self.dragging = self.dragging, None
        tv = self.app.asm_view
        tv.ghost = None
        if not kind:
            return
        px = self.winfo_pointerx() - tv.winfo_rootx()
        py = self.winfo_pointery() - tv.winfo_rooty()
        if not (0 <= px <= tv.winfo_width() and 0 <= py <= tv.winfo_height()):
            tv.redraw()
            return
        x, y = tv.cm(px, py)
        ok, msg, pos, par = can_place(self.app.bench, kind, x, y)
        if not ok:
            messagebox.showwarning(T("조립 순서", "Assembly order"), msg)
            tv.redraw()
            return
        kw = {}
        if kind == "jack":
            kw["h"] = 12.0
        if kind == "lens":
            kw["f"] = float(self.app.lens_f.get())
        if kind in ("laser", "mirror", "lens", "screen"):
            kw["ang"] = 0.0
        if par:
            kw["parent"] = par
        self.app.bench.add(kind, pos[0], pos[1], **kw)
        self.redraw()
        tv.redraw()
        self.app.refresh()


# --------------------------------------------------------------------------
# Main application
# --------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.title(T("APhO 2014 실험 - 용액 속 초음파의 속력",
                     "APhO 2014 Experiment - Speed of Ultrasonic Sound in Solution"))
        self.configure(bg="#141619")
        self.geometry("1250x915")
        self.session = Session(seed)
        self.bench = Bench(self.session)
        self.lens_f = tk.StringVar(value="5.0")
        self.scale_read = tk.StringVar(value="---.- g")
        self.pending_salt = 0.0

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.nb = nb
        self.tab_asm = tk.Frame(nb, bg="#141619")
        self.tab_bench = tk.Frame(nb, bg="#141619")
        nb.add(self.tab_asm, text=T("  1. 조립  ", "  1. Assembly  "))
        nb.add(self.tab_bench, text=T("  2. 실험대  ", "  2. Bench  "))
        nb.bind("<<NotebookTabChanged>>", lambda e: self.refresh())

        self._build_assembly()
        self._build_bench()
        self.after(300, self._tick)

    # ================= assembly tab ==================================
    def _build_assembly(self):
        f = self.tab_asm
        left = tk.Frame(f, bg="#141619")
        left.pack(side="left", fill="y", padx=6, pady=6)
        self.bin = PartsBin(left, self)
        self.bin.pack()
        lf = tk.Frame(left, bg="#141619")
        lf.pack(fill="x", pady=6)
        tk.Label(lf, text=T("렌즈 초점거리", "lens focal length"), fg="#ccc",
                 bg="#141619", font=("Arial", 8)).pack(side="left")
        ttk.Combobox(lf, textvariable=self.lens_f, values=["5.0", "15.0"],
                     width=6, state="readonly").pack(side="left", padx=4)
        tk.Button(left, text=T("선택 부품 제거", "remove selected"),
                  command=self.remove_selected).pack(fill="x", pady=2)
        tk.Button(left, text=T("전체 해체", "clear table"),
                  command=self.clear_table).pack(fill="x", pady=2)
        self.asm_msg = tk.Label(left, text="", fg="#9fd8ee", bg="#141619",
                                wraplength=230, justify="left",
                                font=("Arial", 8))
        self.asm_msg.pack(fill="x", pady=6)

        right = tk.Frame(f, bg="#141619")
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.asm_view = TopView(right, self.bench, mode="assembly",
                                on_select=self._on_select)
        self.asm_view.pack()
        tk.Label(right, fg="#8a929c", bg="#141619", justify="left",
                 font=("Arial", 8),
                 text=T("· 부품 상자에서 끌어다 테이블 위에 놓으세요.\n"
                        "· D1(홀더)은 셀 안에, C(변환기)는 D1의 원형 슬롯에, "
                        "D2는 D1 위에 장착합니다.\n"
                        "· E(레이저)·H(거울)·I(렌즈)는 비어 있는 G(랩잭) 위에만 올라갑니다.",
                        "- Drag a component out of the parts box onto the table.\n"
                        "- D1 goes inside the cell, C into the circular slot of D1, "
                        "D2 on top of D1.\n"
                        "- E, H and I can only be mounted on a free lab jack (G).")
                 ).pack(anchor="w", pady=4)

    def remove_selected(self):
        key = self.asm_view.sel or self.bench_view.sel
        if not key or key not in self.bench.items:
            return
        for k2, it2 in list(self.bench.items.items()):
            if it2.parent == key:
                del self.bench.items[k2]
        del self.bench.items[key]
        self.asm_view.sel = None
        self.bench_view.sel = None
        self.refresh()

    def clear_table(self):
        if messagebox.askyesno(T("확인", "Confirm"),
                               T("테이블의 모든 부품을 치울까요?",
                                 "Remove every component from the table?")):
            self.bench.items.clear()
            self.refresh()

    # ================= bench tab =====================================
    def _build_bench(self):
        f = self.tab_bench
        left = tk.Frame(f, bg="#141619")
        left.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.bench_view = TopView(left, self.bench, mode="bench",
                                  on_select=self._on_select)
        self.bench_view.pack()
        ctl = tk.Frame(left, bg="#141619")
        ctl.pack(fill="both", expand=True, pady=4)
        self._build_controls(ctl)
        right = tk.Frame(f, bg="#20242b")
        right.pack(side="left", fill="y", padx=5, pady=5)
        self.screen = ScreenView(right, self.bench)
        self.screen.pack()

    def _lf(self, parent, title, col):
        g = tk.LabelFrame(parent, text=title, fg="#ffd166", bg="#1b1e23",
                          font=("Arial", 9, "bold"), labelanchor="nw",
                          bd=1, relief="groove")
        g.grid(row=0, column=col, sticky="nsew", padx=3)
        parent.grid_columnconfigure(col, weight=1)
        return g

    def _spin(self, p, r, label, frm, to, inc, cb, width=7):
        tk.Label(p, text=label, fg="#ccc", bg="#1b1e23",
                 font=("Arial", 8)).grid(row=r, column=0, sticky="w", padx=3)
        v = tk.DoubleVar()
        s = ttk.Spinbox(p, from_=frm, to=to, increment=inc, width=width,
                        textvariable=v, command=cb)
        s.grid(row=r, column=1, sticky="w", padx=3, pady=1)
        s.bind("<Return>", lambda e: cb())
        return v, s

    def _build_controls(self, ctl):
        # ---------- selected component ----------
        g = self._lf(ctl, T("선택한 부품", "Selected component"), 0)
        self.sel_lbl = tk.Label(g, text="-", fg="#e8e8e8", bg="#1b1e23",
                                font=("Arial", 9, "bold"))
        self.sel_lbl.grid(row=0, column=0, columnspan=2, sticky="w", padx=4, pady=2)
        self.v_x, _ = self._spin(g, 1, "X (cm)", 0, TABLE_W, 0.1, self._apply_sel)
        self.v_y, _ = self._spin(g, 2, "Y (cm)", 0, TABLE_H, 0.1, self._apply_sel)
        self.v_ang, _ = self._spin(g, 3, T("각도 (°)", "angle (deg)"), -180, 360, 0.1,
                                   self._apply_sel)
        self.v_h, _ = self._spin(g, 4, T("랩잭 높이 (cm)", "jack height (cm)"),
                                 JACK_H_MIN, JACK_H_MAX, 0.1, self._apply_sel)
        tk.Button(g, text=T("제거", "remove"), font=("Arial", 8),
                  command=self.remove_selected).grid(row=5, column=0,
                                                     columnspan=2, sticky="ew",
                                                     padx=4, pady=3)

        # ---------- liquids ----------
        g = self._lf(ctl, T("셀과 액체", "Cell and liquids"), 1)
        tk.Label(g, text=T("사용 중인 셀", "active cell"), fg="#ccc", bg="#1b1e23",
                 font=("Arial", 8)).grid(row=0, column=0, sticky="w", padx=3)
        self.cellsel = tk.StringVar(value="A1")
        cb = ttk.Combobox(g, textvariable=self.cellsel, values=["A1", "A2", "A3"],
                          width=5, state="readonly")
        cb.grid(row=0, column=1, sticky="w", padx=3)
        cb.bind("<<ComboboxSelected>>", lambda e: self._switch_cell())
        self.v_vol, _ = self._spin(g, 1, T("계량컵 (L)", "container (L)"),
                                   0.05, 2.0, 0.05, lambda: None)
        self.v_vol.set(1.50)
        tk.Button(g, text=T("생수 붓기", "pour mineral water"), font=("Arial", 8),
                  command=lambda: self.pour("water")).grid(row=2, column=0,
                                                           columnspan=2, sticky="ew",
                                                           padx=4, pady=1)
        self.v_salt, _ = self._spin(g, 3, T("소금 (g)", "salt (g)"), 0, 600, 5.0,
                                    lambda: None)
        tk.Button(g, text=T("전자저울에 달기", "weigh on balance"), font=("Arial", 8),
                  command=self.weigh).grid(row=4, column=0, columnspan=2,
                                           sticky="ew", padx=4, pady=1)
        tk.Label(g, textvariable=self.scale_read, fg="#7CFC00", bg="#0d0f12",
                 font=("Consolas", 11)).grid(row=5, column=0, columnspan=2,
                                             sticky="ew", padx=4)
        tk.Button(g, text=T("셀에 넣고 젓기", "add to cell and stir"), font=("Arial", 8),
                  command=self.add_salt).grid(row=6, column=0, columnspan=2,
                                              sticky="ew", padx=4, pady=1)
        tk.Button(g, text=T("미지 농도 용액 (L) 붓기", "pour unknown solution (L)"),
                  font=("Arial", 8),
                  command=lambda: self.pour("unknown")).grid(row=7, column=0,
                                                             columnspan=2,
                                                             sticky="ew", padx=4, pady=1)
        tk.Button(g, text=T("옥수수 시럽 (M) 붓기", "pour corn syrup (M)"),
                  font=("Arial", 8),
                  command=lambda: self.pour("syrup")).grid(row=8, column=0,
                                                           columnspan=2,
                                                           sticky="ew", padx=4, pady=1)
        tk.Button(g, text=T("셀 비우기", "empty the cell"), font=("Arial", 8),
                  command=self.empty).grid(row=9, column=0, columnspan=2,
                                           sticky="ew", padx=4, pady=1)
        self.liq_lbl = tk.Label(g, text="", fg="#9fd8ee", bg="#1b1e23",
                                font=("Arial", 8), justify="left", wraplength=210)
        self.liq_lbl.grid(row=10, column=0, columnspan=2, sticky="w", padx=4, pady=2)

        # ---------- instruments ----------
        g = self._lf(ctl, T("장치", "Instruments"), 2)
        self.laser_var = tk.IntVar()
        tk.Checkbutton(g, text=T("레이저 (E) ON", "laser (E) ON"), variable=self.laser_var,
                       command=self.toggle_laser, fg="#e8e8e8", bg="#1b1e23",
                       selectcolor="#0d0f12", activebackground="#1b1e23",
                       font=("Arial", 9)).grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Label(g, text=T("레이저 회전 (°)", "laser rotation (deg)"), fg="#ccc",
                 bg="#1b1e23", font=("Arial", 8)).grid(row=1, column=0, sticky="w", padx=3)
        self.rot_var = tk.DoubleVar(value=0.0)
        tk.Scale(g, from_=0, to=180, resolution=1, orient="horizontal",
                 variable=self.rot_var, showvalue=1, length=120, bg="#1b1e23",
                 fg="#ccc", troughcolor="#333", highlightthickness=0,
                 font=("Arial", 7),
                 command=lambda v: self._set_rot()).grid(row=1, column=1, padx=3)
        self.us_var = tk.IntVar()
        tk.Checkbutton(g, text=T("압전 변환기 (C) ON", "transducer (C) ON"),
                       variable=self.us_var, command=self.toggle_us,
                       fg="#e8e8e8", bg="#1b1e23", selectcolor="#0d0f12",
                       activebackground="#1b1e23",
                       font=("Arial", 9)).grid(row=2, column=0, columnspan=2, sticky="w")
        self.plate_var = tk.IntVar()
        tk.Checkbutton(g, text=T("D2 판을 물에 잠기게", "submerge plate D2"),
                       variable=self.plate_var, command=self.toggle_plate,
                       fg="#e8e8e8", bg="#1b1e23", selectcolor="#0d0f12",
                       activebackground="#1b1e23",
                       font=("Arial", 9)).grid(row=3, column=0, columnspan=2, sticky="w")
        self.v_gap, _ = self._spin(g, 4, T("D2 높이 조절 (cm)", "D2 height (cm)"),
                                   0.10, 3.00, 0.05, self._set_plate)
        self.v_gap.set(0.50)
        self.v_tilt, _ = self._spin(g, 5, T("D2 수평 나사 (°)", "D2 levelling (deg)"),
                                    -3.0, 3.0, 0.05, self._set_plate)
        self.v_tilt.set(0.60)

        # ---------- measuring tools ----------
        g = self._lf(ctl, T("측정 도구", "Measuring tools"), 3)
        self.tape_var = tk.IntVar()
        tk.Checkbutton(g, text=T("줄자/자 모드 (두 점 클릭)",
                                 "tape / ruler mode (click 2 points)"),
                       variable=self.tape_var, command=self._toggle_tape,
                       fg="#e8e8e8", bg="#1b1e23", selectcolor="#0d0f12",
                       activebackground="#1b1e23",
                       font=("Arial", 9)).grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Button(g, text=T("버니어 캘리퍼로 벽 두께 재기",
                            "measure wall with vernier caliper"),
                  font=("Arial", 8), command=self.caliper).grid(row=1, column=0,
                                                                columnspan=2,
                                                                sticky="ew", padx=4, pady=2)
        self.cal_lbl = tk.Label(g, text="--.--- mm", fg="#7CFC00", bg="#0d0f12",
                                font=("Consolas", 11))
        self.cal_lbl.grid(row=2, column=0, columnspan=2, sticky="ew", padx=4)
        tk.Label(g, text=T("온도계 (Y)", "thermometer (Y)"), fg="#ccc", bg="#1b1e23",
                 font=("Arial", 8)).grid(row=3, column=0, sticky="w", padx=3, pady=(6, 0))
        self.temp_lbl = tk.Label(g, text="--.- C", fg="#7CFC00", bg="#0d0f12",
                                 font=("Consolas", 11))
        self.temp_lbl.grid(row=4, column=0, columnspan=2, sticky="ew", padx=4)
        self.warn = tk.Label(g, text="", fg="#ff9d7a", bg="#1b1e23",
                             font=("Arial", 8), justify="left", wraplength=210)
        self.warn.grid(row=5, column=0, columnspan=2, sticky="w", padx=4, pady=4)

    # ================= handlers ======================================
    def _on_select(self, key):
        self.asm_view.sel = key
        self.bench_view.sel = key
        if key and key in self.bench.items:
            it = self.bench.items[key]
            name = {"cell": "A", "platform": "B", "transducer": "C",
                    "holder": "D1", "plate": "D2", "laser": "E", "screen": "F",
                    "jack": "G", "mirror": "H", "lens": "I",
                    "thermo": "Y"}.get(it.kind, "?")
            self.sel_lbl.config(text="%s  (%s)" % (name, key))
            self.v_x.set(round(it.x, 2))
            self.v_y.set(round(it.y, 2))
            self.v_ang.set(round(it.ang, 2))
            self.v_h.set(round(it.data.get("h", 12.0), 2))
        else:
            self.sel_lbl.config(text="-")
        self.asm_view.redraw()
        self.bench_view.redraw()

    def _apply_sel(self):
        key = self.bench_view.sel or self.asm_view.sel
        if not key or key not in self.bench.items:
            return
        it = self.bench.items[key]
        ox, oy = it.x, it.y
        it.x = max(0.5, min(TABLE_W - 0.5, float(self.v_x.get())))
        it.y = max(0.5, min(TABLE_H - 0.5, float(self.v_y.get())))
        it.ang = float(self.v_ang.get())
        if it.kind == "jack":
            it.data["h"] = max(JACK_H_MIN, min(JACK_H_MAX, float(self.v_h.get())))
        dx, dy = it.x - ox, it.y - oy
        for k2, it2 in self.bench.items.items():
            if it2.parent == key:
                it2.x += dx
                it2.y += dy
        if it.kind == "holder":
            for it2 in self.bench.items.values():
                if it2.kind in ("transducer", "plate"):
                    it2.x, it2.y = it.x, it.y
        if it.kind == "cell":
            for it2 in self.bench.items.values():
                if it2.kind in ("holder", "transducer", "plate", "thermo"):
                    it2.x += dx
                    it2.y += dy
        self.refresh()

    def _switch_cell(self):
        self.bench.active_cell = int(self.cellsel.get()[1]) - 1
        self.refresh()

    def pour(self, medium):
        if not self.bench.get("cell"):
            messagebox.showwarning(T("주의", "Note"),
                                   T("유리 셀을 먼저 배치하세요.",
                                     "Place the glass cell first."))
            return
        c = self.bench.cell()
        if c.medium not in ("none", medium):
            messagebox.showwarning(T("주의", "Note"),
                                   T("셀에 다른 액체가 들어 있습니다. 먼저 비우세요.\n"
                                     "(셀은 세 개가 제공됩니다.)",
                                     "Another liquid is already in this cell.  Empty it "
                                     "first (three cells are provided)."))
            return
        if medium == "syrup":
            vol = 1.53
        elif medium == "unknown":
            vol = 1.50
        else:
            vol = float(self.v_vol.get())
        vol += self.bench.s.noise(("pour", medium, round(vol, 3)), 0.008)
        if c.volume_L + vol > 1.75:
            messagebox.showwarning(T("주의", "Note"),
                                   T("셀이 넘칩니다.", "The cell would overflow."))
            return
        c.medium = medium
        c.volume_L += vol
        c.stirred = True
        if medium == "unknown":
            c.salt_g += self.bench.s.unknown_g_per_L * vol
        if c.temp is None:
            c.temp = self.bench.s.T_ambient
        self.refresh()

    def empty(self):
        c = self.bench.cell()
        c.medium = "none"
        c.volume_L = 0.0
        c.salt_g = 0.0
        c.salt_added_g = 0.0
        c.temp = None
        c.stirred = True
        self.refresh()

    def weigh(self):
        m = float(self.v_salt.get())
        m += self.bench.s.noise(("scale", round(m, 2)), 0.06)
        self.pending_salt = max(0.0, quantize(m, 0.1))
        self.scale_read.set("%6.1f g" % self.pending_salt)

    def add_salt(self):
        c = self.bench.cell()
        if c.medium not in ("water", "salt"):
            messagebox.showwarning(T("주의", "Note"),
                                   T("소금은 생수가 든 셀에만 넣을 수 있습니다.",
                                     "Salt can only be added to a cell of mineral water."))
            return
        if self.pending_salt <= 0:
            messagebox.showinfo(T("안내", "Note"),
                                T("먼저 전자저울로 소금을 다세요.",
                                  "Weigh the salt on the balance first."))
            return
        if (c.salt_g + self.pending_salt) / max(c.volume_L, 1e-6) > SAT_LIMIT_G_PER_L:
            messagebox.showwarning(T("주의", "Note"),
                                   T("소금이 더 이상 녹지 않고 바닥에 가라앉습니다.",
                                     "The salt no longer dissolves; it settles at the bottom."))
            return
        c.salt_g += self.pending_salt
        c.salt_added_g += self.pending_salt
        c.medium = "salt"
        c.stirred = True
        self.pending_salt = 0.0
        self.scale_read.set("   0.0 g")
        self.refresh()

    def toggle_laser(self):
        if self.laser_var.get() and not self.bench.get("laser"):
            messagebox.showwarning(T("주의", "Note"),
                                   T("레이저 포인터(E)가 랩잭 위에 없습니다.",
                                     "The laser pointer (E) is not mounted on a lab jack."))
            self.laser_var.set(0)
            return
        self.bench.laser_on = bool(self.laser_var.get())
        self.refresh()

    def toggle_us(self):
        if self.us_var.get():
            if not self.bench.get("transducer"):
                messagebox.showwarning(T("주의", "Note"),
                                       T("압전 변환기(C)가 홀더에 장착되어 있지 않습니다.",
                                         "The transducer (C) is not mounted in the holder."))
                self.us_var.set(0)
                return
            if not self.bench.transducer_wet():
                messagebox.showwarning(
                    T("안전 수칙 (2)", "Safety precaution (2)"),
                    T("압전 변환기는 유리 셀의 물 속에 확실히 잠긴 뒤에만 켜야 합니다.",
                      "The transducer may only be switched ON after it is securely "
                      "placed inside the water in the glass cell."))
                self.us_var.set(0)
                return
        self.bench.transducer_on = bool(self.us_var.get())
        self.refresh()

    def toggle_plate(self):
        if self.plate_var.get() and not self.bench.get("plate"):
            messagebox.showwarning(T("주의", "Note"),
                                   T("조절판(D2)이 장착되어 있지 않습니다.",
                                     "The adjustable plate (D2) is not mounted."))
            self.plate_var.set(0)
            return
        self.bench.plate_submerged = bool(self.plate_var.get())
        self.refresh()

    def _set_plate(self):
        self.bench.plate_gap = float(self.v_gap.get())
        self.bench.plate_tilt = float(self.v_tilt.get())
        self.refresh()

    def _set_rot(self):
        self.bench.laser_rot = float(self.rot_var.get())
        self.screen.redraw()

    def _toggle_tape(self):
        self.bench_view.tape_mode = bool(self.tape_var.get())
        self.bench_view.tape_pts = []
        self.bench_view.tape_text = ""
        self.bench_view.redraw()

    def caliper(self):
        if not self.bench.get("cell"):
            return
        g = self.bench.cell().g * 10.0        # mm
        g += self.bench.s.noise(("caliper", self.bench.active_cell), 0.018)
        self.cal_lbl.config(text="%6.3f mm" % quantize(g, 0.005))

    # ================= periodic refresh ==============================
    def refresh(self):
        self.bin.redraw()
        self.asm_view.redraw()
        self.bench_view.redraw()
        self.screen.redraw()
        c = self.bench.cell()
        if c.medium == "unknown":
            self.liq_lbl.config(text=T("셀 A%d: %s, %.2f L",
                                       "Cell A%d: %s, %.2f L")
                                % (c.idx, c.label(), c.volume_L))
        else:
            self.liq_lbl.config(text=T("셀 A%d: %s, %.2f L, 넣은 소금 %.1f g",
                                       "Cell A%d: %s, %.2f L, salt added %.1f g")
                                % (c.idx, c.label(), c.volume_L, c.salt_added_g))
        msgs = []
        if self.bench.get("transducer") and self.bench.transducer_on \
                and not self.bench.transducer_wet():
            msgs.append(T("변환기가 물에 잠겨 있지 않습니다!",
                          "The transducer is not immersed!"))
        if self.bench.laser_on and not self.bench.get("screen"):
            msgs.append(T("스크린(F)이 없습니다.", "No screen (F) on the table."))
        self.warn.config(text="\n".join(msgs))

    def _tick(self):
        self.bench.tick()
        c = self.bench.cell()
        if self.bench.get("thermo") and c.temp is not None:
            t = c.temp + self.bench.s.noise(("thermo", round(c.temp, 1)), 0.12)
            self.temp_lbl.config(text="%5.1f C" % quantize(t, 0.5))
        else:
            self.temp_lbl.config(text=" --.- C")
        if self.nb.index("current") == 1:
            self.bench_view.redraw()
            self.screen.redraw()
        self.after(700, self._tick)


def main():
    global LANG
    import sys
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--lang="):
            LANG = a.split("=", 1)[1]
        elif a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
    App(seed).mainloop()


if __name__ == "__main__":
    main()
