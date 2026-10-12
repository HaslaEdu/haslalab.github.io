# -*- coding: utf-8 -*-
"""
=======================================================================
  19th Asian Physics Olympiad  (APhO 2018, Hanoi - Vietnam)
  Experimental Problem :  GIANT MAGNETORESISTANCE (GMR)
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------

Single file, Python standard library only (tkinter).

Design rule (non-negotiable):
    The simulator shows ONLY what the real instruments would show.
    No physical quantity is ever computed or displayed for the student.
"""

import math
import random
import sys
import time
import tkinter as tk
from tkinter import ttk

# --------------------------------------------------------------------------
#  i18n
# --------------------------------------------------------------------------
LANG = "en"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


APP_TITLE = T("APhO 2018 실험 1 — 거대 자기저항 (GMR)",
              "APhO 2018 Experiment 1 - Giant Magnetoresistance (GMR)")

MU0 = 4.0e-7 * math.pi


# ==========================================================================
#  PHYSICS
# ==========================================================================
class Session:
    """Hidden true parameters of one laboratory session (randomised)."""

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1, 10 ** 9)
        self.seed = seed
        r = random.Random(seed)
        self.rnd = random.Random(seed ^ 0x5DEECE66)

        # ---- circular coil [8] : specified by the manufacturer -----------
        self.N_coil = 500
        self.d_coil = 0.100                        # m, mean diameter
        # B = k * I ; k in mT/mA
        self.k_coil = MU0 * self.N_coil / self.d_coil * 1.0e3 / 1.0e3
        self.R_coil = 21.0 + r.uniform(-1.0, 1.0)  # ohm, winding resistance

        # ---- flat coil [5] ----------------------------------------------
        self.k_flat = 1.15 * r.uniform(0.94, 1.06)  # mT per A
        self.R_flat = 0.55 + r.uniform(-0.1, 0.1)

        # ---- GMR elements -------------------------------------------------
        #  bridge:  a = 8-5, b = 5-4, c = 1-4, d = 8-1
        #  a and c are exposed;  b and d are magnetically shielded
        base = 4950.0 * r.uniform(0.97, 1.03)
        self.R0 = {
            "a": base * r.uniform(0.995, 1.008),
            "b": base * r.uniform(0.980, 1.000),
            "c": base * r.uniform(0.996, 1.004),
            "d": base * r.uniform(0.998, 1.012),
        }
        self.sensitive = ("a", "c")

        # relative change of resistance  delta(B) = -ds * f(|h|)
        self.ds = 0.1354 * r.uniform(0.96, 1.04)
        self.B0f = 1.918 * r.uniform(0.95, 1.05)   # saturation scale, mT
        self.nf = 10.89 * r.uniform(0.96, 1.04)
        self.mf = 0.1048 * r.uniform(0.96, 1.04)

        # hysteresis : reversible part + one play (backlash) operator
        #   h = (1-beta)*B + beta*p ,  p = clamp(p, B-r, B+r) , r = Bc/beta
        #   -> major loop is shifted by exactly +-Bc (the coercive field)
        #   -> small excursions are attenuated by the same factor (1-beta)
        #   on the major loop  h = B -+ beta*rp , so the observed coercive
        #   field is beta*rp ; rp must be below half the largest field the
        #   circular coil can produce (~3 mT) for the loop to open fully
        self.Bc = 0.100 * r.uniform(0.85, 1.15)    # coercive field, mT
        self.r_play = 1.20 * r.uniform(0.9, 1.1)   # play threshold, mT
        self.beta = self.Bc / self.r_play
        self._p = 0.0                              # play operator state

        # ---- battery [4] : 5 sockets -------------------------------------
        cell = 1.575 * r.uniform(0.985, 1.015)
        self.E_tap = [0.0]
        acc = 0.0
        for i in range(4):
            acc += cell * r.uniform(0.985, 1.015)
            self.E_tap.append(acc)
        self.R_batt = 1.2

        # ---- variable DC current source [6] -------------------------------
        self.I_max = 1.05 * r.uniform(0.96, 1.04)    # A (knob is quadratic)
        self.V_compliance = 10.0 * r.uniform(0.98, 1.02)

        # ---- rheostat [2] --------------------------------------------------
        self.Rh_min, self.Rh_max = 1.0e5, 2.0e7

        # ---- earth field ---------------------------------------------------
        self.Bh = 0.0350 * r.uniform(0.94, 1.06)     # mT, horizontal
        self.theta = math.radians(31.0 * r.uniform(0.93, 1.07))
        self.Bv = self.Bh * math.tan(self.theta)

        # ---- permanent magnet plate [19] -----------------------------------
        self.Bm0 = 4.6 * r.uniform(0.9, 1.1)         # mT at zero distance
        self.xm0 = 11.0 * r.uniform(0.9, 1.1)        # mm

        # ---- external flux concentrator [18] --------------------------------
        self.n_fc = 0.56 * r.uniform(0.93, 1.07)
        self.L2 = 25.0                               # mm, sheet length

        # ---- double filament bulb [21] ---------------------------------------
        self.bulb = [
            dict(Rc=1.55 * r.uniform(0.95, 1.05), krad=9.3e-14, kcond=2.2e-4),
            dict(Rc=0.92 * r.uniform(0.95, 1.05), krad=1.4e-13, kcond=3.1e-4),
        ]

        # ---- printed circuit boards [9] ---------------------------------------
        #  polylines in board coordinates (mm on the 0..30 grid),
        #  current flows from the first vertex to the last
        self.pcb_paths = {
            1: [(3.0, 26.0), (15.0, 2.0), (27.0, 26.0)],
            2: [(26.0, 27.0), (26.0, 4.0), (3.0, 27.0), (3.0, 4.0)],
        }
        self.pcb_z = 2.6 + r.uniform(-0.3, 0.3)      # mm, sensor above traces
        self.R_pcb = 3.4 + r.uniform(-0.4, 0.4)

        # ---- instrument imperfections ------------------------------------------
        self.meter_gain = [1.0 + r.uniform(-4e-4, 4e-4) for _ in range(3)]
        self.t0 = time.time()

    # -------------------------------------------------------------- GMR law
    def f_sat(self, b):
        """normalised saturation function, f(0)=0, f(inf)=1"""
        b = abs(b)
        if b <= 1e-9:
            return 0.0
        x = (b / self.B0f) ** self.nf
        if x > 1e12:
            return 1.0
        return (x / (1.0 + x)) ** self.mf

    def update_history(self, B_axis):
        """Prandtl-Ishlinskii play operator + reversible part."""
        rr = self.r_play
        self._p = max(B_axis - rr, min(B_axis + rr, self._p))
        return (1.0 - self.beta) * B_axis + self.beta * self._p

    def delta(self, B_axis):
        h = self.update_history(B_axis)
        return -self.ds * self.f_sat(h)

    def element_R(self, B_axis):
        d = self.delta(B_axis)
        out = {}
        for k, v in self.R0.items():
            out[k] = v * (1.0 + d) if k in self.sensitive else v
        return out


# --------------------------------------------------------------------------
#  Geometry / field superposition
# --------------------------------------------------------------------------
#  lab frame :  x = East , y = North , z = Up
#  Earth field  =  (0, +Bh, -Bv)
# --------------------------------------------------------------------------
def sensor_axis(plate_vertical, alpha_deg):
    """Unit vector of the sensitivity axis.

    plate horizontal : alpha = 0 -> axis points East (perpendicular to N-S)
    plate vertical (in the N-S plane) : alpha measured from the horizontal,
    alpha = 0 -> axis points North.
    """
    a = math.radians(alpha_deg)
    if not plate_vertical:
        return (math.cos(a), math.sin(a), 0.0)
    return (0.0, math.cos(a), math.sin(a))


def dot(u, v):
    return u[0] * v[0] + u[1] * v[1] + u[2] * v[2]


def seg_field(p0, p1, r, I):
    """Biot-Savart field (mT) of a finite straight segment carrying I (A).
    Coordinates in mm."""
    ax, ay, az = p0[0] - r[0], p0[1] - r[1], p0[2] - r[2]
    bx, by, bz = p1[0] - r[0], p1[1] - r[1], p1[2] - r[2]
    dx, dy, dz = bx - ax, by - ay, bz - az
    L2 = dx * dx + dy * dy + dz * dz
    if L2 < 1e-12:
        return (0.0, 0.0, 0.0)
    na = math.sqrt(ax * ax + ay * ay + az * az)
    nb = math.sqrt(bx * bx + by * by + bz * bz)
    if na < 1e-6 or nb < 1e-6:
        return (0.0, 0.0, 0.0)
    cx = ay * bz - az * by
    cy = az * bx - ax * bz
    cz = ax * by - ay * bx
    c2 = cx * cx + cy * cy + cz * cz
    if c2 < 1e-18:
        return (0.0, 0.0, 0.0)
    #  mu0 I /(4 pi) * (cosA - cosB) / d   ; with vectors:
    fac = (dot((dx, dy, dz), (bx, by, bz)) / nb
           - dot((dx, dy, dz), (ax, ay, az)) / na) / c2
    #  mu0/(4pi) = 1e-7 T*m/A ; lengths in mm -> multiply by 1e3 ;
    #  result in T -> mT : *1e3
    k = 1.0e-7 * I * 1.0e3 * 1.0e3
    return (k * cx * fac, k * cy * fac, k * cz * fac)


# ==========================================================================
#  APPARATUS  (parts, placement, wiring, circuit)
# ==========================================================================
PARTS = [
    # id, number, korean, english, zone it may be dropped on, prerequisites
    ("lead",    1,  "리드선",                "Lead wires",              "elec",   []),
    ("rheo",    2,  "가변저항기",             "Variable resistor",       "elec",   []),
    ("accord",  3,  "220 V AC 전원 코드",     "220 V AC power cord",     "elec",   []),
    ("batt",    4,  "배터리",                "Battery",                 "elec",   []),
    ("flat",    5,  "평면 코일",              "Flat coil",               "sensor", ["sensor"]),
    ("dcsrc",   6,  "가변 DC 전류원",         "Variable DC source",      "elec",   ["accord"]),
    ("post",    7,  "긴 기둥이 있는 받침대",   "Stand with long post",    "post",   []),
    ("coil",    8,  "원형 코일",              "Circular coil",           "rail",   ["platform"]),
    ("pcb",     9,  "인쇄회로기판",           "Printed circuit board",   "rotplate", ["rotplate"]),
    ("trail",  10,  "횡방향 레일",            "Transverse rail",         "rail",   ["platform"]),
    ("rotplate",11, "회전판",                "Rotating plate",          "rail",   ["trail"]),
    ("platform",12, "종방향 레일 플랫폼",      "Platform with rail",      "rail",   []),
    ("sensor", 13,  "자기 센서",              "Magnetic sensor",         "holder", ["holder"]),
    ("holder", 14,  "센서 거치대",            "Sensor holder",           "table",  ["table"]),
    ("table",  15,  "원형 테이블 (각도 눈금)", "Graduated circular table","post",   ["post"]),
    ("sbox",   16,  "센서 연결 박스",         "Sensor connection box",   "elec",   ["sensor"]),
    ("cbox",   17,  "연결 박스",              "Connection box",          "elec",   []),
    ("sheets", 18,  "강자성 시트",            "Ferromagnetic sheets",    "sensor", ["sensor"]),
    ("magnet", 19,  "영구자석 판",            "Permanent magnet plate",  "sensor", ["sensor"]),
    ("dmm",    20,  "멀티미터 (3개)",         "Multimeters (3)",         "elec",   []),
    ("bulb",   21,  "이중 필라멘트 전구",      "Double filament bulb",    "elec",   []),
]
PART_BY_ID = {p[0]: p for p in PARTS}

ZONES = {
    "rail":     (T("실험대 (레일)", "Bench (rails)")),
    "post":     (T("기둥 / 받침대", "Post / stand")),
    "table":    (T("원형 테이블", "Circular table")),
    "holder":   (T("센서 거치대", "Sensor holder")),
    "sensor":   (T("센서 주변", "Around the sensor")),
    "rotplate": (T("회전판", "Rotating plate")),
    "elec":     (T("전기 장치", "Electrical devices")),
}

# terminals: id -> (owner part, label, korean tooltip)
TERMINALS = [
    ("S1", "sbox", "1"), ("S2", "sbox", "2"), ("S3", "sbox", "3"), ("S4", "sbox", "4"),
    ("S5", "sbox", "5"), ("S6", "sbox", "6"), ("S7", "sbox", "7"), ("S8", "sbox", "8"),
    ("B0", "batt", "0"), ("B1", "batt", "1"), ("B2", "batt", "2"),
    ("B3", "batt", "3"), ("B4", "batt", "4"),
    ("C+", "dcsrc", "+"), ("C-", "dcsrc", "-"),
    ("K1", "coil", "a"), ("K2", "coil", "b"),
    ("F1", "flat", "a"), ("F2", "flat", "b"),
    ("P1", "rheo", "a"), ("P2", "rheo", "b"),
    ("W1", "pcb", "+"), ("W2", "pcb", "-"),
    ("L1", "bulb", "1"), ("L2", "bulb", "2"), ("L3", "bulb", "3"),
    ("J1a", "cbox", "1"), ("J1b", "cbox", "1"), ("J1c", "cbox", "1"),
    ("J2a", "cbox", "2"), ("J2b", "cbox", "2"), ("J2c", "cbox", "2"),
    ("J3a", "cbox", "3"), ("J3b", "cbox", "3"), ("J3c", "cbox", "3"),
    ("J4a", "cbox", "4"), ("J4b", "cbox", "4"), ("J4c", "cbox", "4"),
    ("M1C", "dmm", "COM"), ("M1V", "dmm", "V/O"), ("M1A", "dmm", "A"),
    ("M2C", "dmm", "COM"), ("M2V", "dmm", "V/O"), ("M2A", "dmm", "A"),
    ("M3C", "dmm", "COM"), ("M3V", "dmm", "V/O"), ("M3A", "dmm", "A"),
]
TERM_OWNER = {t[0]: t[1] for t in TERMINALS}

MODES = ["OFF", "V", "OHM", "A", "mA"]


class Rig:
    """Everything the student has physically set up plus every knob setting."""

    def __init__(self, session):
        self.S = session
        self.installed = set()
        self.wires = []                       # list of (t1, t2)

        # knobs -------------------------------------------------------------
        self.plate_vertical = False           # circular table orientation
        self.alpha = 0.0                      # deg, holder angle on the table
        self.coil_pos = 100.0                 # mm along longitudinal rail
        self.sensor_pos = 100.0               # mm (fixed)
        self.src_knob = 0.0                   # 0..1
        self.src_reverse = False
        self.batt_on = False
        self.rheo_knob = 0.5                  # 0..1
        self.magnet_on = False
        self.magnet_dist = 25.0               # mm
        self.sheets_on = False
        self.L1 = 10.0                        # mm gap between the sheets
        self.pcb_index = 1
        self.pcb_x = 15.0                     # mm, transverse rail
        self.pcb_y = 15.0                     # mm, longitudinal rail
        self.pcb_rot = 0.0                    # deg, rotating plate
        self.meter_mode = ["OFF", "OFF", "OFF"]

        # results ------------------------------------------------------------
        self.readings = [None, None, None]
        self.B_axis = 0.0
        self._Rel = dict(session.R0)
        self._noise = random.Random(session.seed ^ 0xABCDEF)

    # ------------------------------------------------------------------ misc
    def has(self, pid):
        return pid in self.installed

    def can_place(self, pid):
        p = PART_BY_ID[pid]
        for pre in p[5]:
            if pre not in self.installed:
                return False, pre
        return True, None

    def wired(self):
        return self.has("lead")

    # ------------------------------------------------------------- net solve
    def _nets(self):
        """union-find over terminals joined by wires and internal shorts"""
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for t, _, _ in TERMINALS:
            find(t)
        for g in ("J1", "J2", "J3", "J4"):
            union(g + "a", g + "b")
            union(g + "b", g + "c")
        for a, b in self.wires:
            union(a, b)
        # internal nodes
        for extra in ("BN0", "BN1", "BN2", "BN3", "BN4"):
            find(extra)
        union("BN4", "B4")
        union("BN3", "B3")
        union("BN2", "B2")
        union("BN1", "B1")
        if self.batt_on:
            union("BN0", "B0")
        return {t: find(t) for t in parent}

    def _elements(self):
        """list of (kind, na, nb, value) with kind in R / I / V"""
        el = []
        S = self.S
        if self.has("sbox") and self.has("sensor"):
            R = self._Rel
            el.append(("R", "S8", "S5", R["a"]))
            el.append(("R", "S5", "S4", R["b"]))
            el.append(("R", "S1", "S4", R["c"]))
            el.append(("R", "S8", "S1", R["d"]))
        if self.has("batt"):
            for i in range(4):
                dv = S.E_tap[i + 1] - S.E_tap[i]
                el.append(("V", "BN%d" % i, "BN%d" % (i + 1), dv, S.R_batt / 4.0))
        if self.has("coil"):
            el.append(("R", "K1", "K2", S.R_coil))
        if self.has("flat"):
            el.append(("R", "F1", "F2", S.R_flat))
        if self.has("rheo"):
            lg = math.log(S.Rh_min) + self.rheo_knob * (
                math.log(S.Rh_max) - math.log(S.Rh_min))
            el.append(("R", "P1", "P2", math.exp(lg)))
        if self.has("pcb"):
            el.append(("R", "W1", "W2", S.R_pcb))
        if self.has("bulb"):
            for k, term in enumerate(("L2", "L3")):
                el.append(("BULB", "L1", term, k))
        for i in range(3):
            m = self.meter_mode[i]
            c, v, a = "M%dC" % (i + 1), "M%dV" % (i + 1), "M%dA" % (i + 1)
            if m == "V":
                el.append(("R", v, c, 1.0e7))
            elif m == "OHM":
                el.append(("R", v, c, 1.0e8))
                el.append(("I", v, c, 1.0e-4))
            elif m == "A":
                el.append(("R", a, c, 0.02))
            elif m == "mA":
                el.append(("R", a, c, 12.0))
        return el

    def _bulb_R(self, k, I):
        key = (k, round(I, 4))
        c = getattr(self, "_bulbcache", None)
        if c is None:
            c = self._bulbcache = {}
        if key in c:
            return c[key]
        b = self.S.bulb[k]
        Rc, krad, kcond = b["Rc"], b["krad"], b["kcond"]
        Tk = 300.0
        for _ in range(14):
            R = Rc * (1.0 + 4.5e-3 * (Tk - 293.0))
            P = I * I * R
            # P = krad*(T^4 - T0^4) + kcond*(T-T0)
            lo, hi = 293.0, 4000.0
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                q = krad * (mid ** 4 - 293.0 ** 4) + kcond * (mid - 293.0)
                if q < P:
                    lo = mid
                else:
                    hi = mid
            Tn = 0.5 * (lo + hi)
            if abs(Tn - Tk) < 0.5:
                Tk = Tn
                break
            Tk = 0.6 * Tk + 0.4 * Tn
        val = Rc * (1.0 + 4.5e-3 * (Tk - 293.0))
        if len(c) > 4000:
            c.clear()
        c[key] = val
        return val

    def solve_circuit(self):
        """returns dict node->V  plus branch currents of interest"""
        nets = self._nets()
        el = self._elements()
        bulbI = [0.0, 0.0]
        Vn, extra = {}, {}
        for _ in range(6):
            Vn, extra = self._mna(nets, el, bulbI)
            newI = list(bulbI)
            for kind, na, nb, val, *rest in el:
                if kind == "BULB":
                    R = self._bulb_R(val, abs(bulbI[val]))
                    dv = Vn.get(nets[na], 0.0) - Vn.get(nets[nb], 0.0)
                    newI[val] = dv / R
            if max(abs(newI[i] - bulbI[i]) for i in (0, 1)) < 1e-4:
                bulbI = newI
                break
            bulbI = [0.5 * bulbI[i] + 0.5 * newI[i] for i in (0, 1)]
        return nets, Vn, extra

    def _mna(self, nets, el, bulbI):
        nodes = sorted(set(nets.values()))
        idx = {n: i for i, n in enumerate(nodes)}
        nN = len(nodes)
        vsrc = [e for e in el if e[0] == "V"]
        # variable DC current source
        isrc_dc = None
        if self.has("dcsrc") and self.has("accord"):
            Iset = (self.src_knob ** 2) * self.S.I_max
            if self.src_reverse:
                Iset = -Iset
            isrc_dc = Iset
        nV = len(vsrc)
        size = nN + nV
        A = [[0.0] * size for _ in range(size)]
        z = [0.0] * size

        def gstamp(na, nb, g):
            i, j = idx[nets[na]], idx[nets[nb]]
            A[i][i] += g
            A[j][j] += g
            A[i][j] -= g
            A[j][i] -= g

        def istamp(na, nb, I):
            """inject current I into node na, draw it out of node nb"""
            A_i, A_j = idx[nets[na]], idx[nets[nb]]
            z[A_i] += I
            z[A_j] -= I

        for n in nodes:                       # leakage to keep matrix regular
            A[idx[n]][idx[n]] += 1.0e-11
        for e in el:
            kind = e[0]
            if kind == "R":
                gstamp(e[1], e[2], 1.0 / max(e[3], 1e-9))
            elif kind == "I":
                istamp(e[1], e[2], e[3])
            elif kind == "BULB":
                R = self._bulb_R(e[3], abs(bulbI[e[3]]))
                gstamp(e[1], e[2], 1.0 / R)
        for k, e in enumerate(vsrc):
            _, na, nb, val, rs = e
            gstamp(na, nb, 1.0 / max(rs, 1e-6))   # series resistance folded in
        # voltage sources with series resistance -> Norton equivalent
        for k, e in enumerate(vsrc):
            _, na, nb, val, rs = e
            istamp(na, nb, -val / max(rs, 1e-6))
        if isrc_dc:
            istamp("C+", "C-", isrc_dc)
        # ground = node 0
        g0 = 0
        for j in range(size):
            A[g0][j] = 0.0
        A[g0][g0] = 1.0
        z[g0] = 0.0
        x = _lin_solve(A, z)
        Vn = {n: x[idx[n]] for n in nodes}
        # compliance of the current source
        if isrc_dc:
            dv = Vn[nets["C+"]] - Vn[nets["C-"]]
            if abs(dv) > self.S.V_compliance:
                gg = 1.0 / 0.2
                A2 = [row[:] for row in A]
                z2 = z[:]
                i, j = idx[nets["C-"]], idx[nets["C+"]]
                z2[i] += isrc_dc
                z2[j] -= isrc_dc          # remove the current source
                A2[i][i] += gg
                A2[j][j] += gg
                A2[i][j] -= gg
                A2[j][i] -= gg
                vv = math.copysign(self.S.V_compliance, isrc_dc)
                z2[j] += vv * gg
                z2[i] -= vv * gg
                for jj in range(size):
                    A2[g0][jj] = 0.0
                A2[g0][g0] = 1.0
                z2[g0] = 0.0
                x = _lin_solve(A2, z2)
                Vn = {n: x[idx[n]] for n in nodes}
        return Vn, {}

    # ------------------------------------------------------------- field
    def field_axis(self, nets, Vn):
        S = self.S
        ax = sensor_axis(self.plate_vertical, self.alpha)
        # --- Earth ------------------------------------------------------
        Bu = [0.0, S.Bh, -S.Bv]
        # --- circular coil ---------------------------------------------
        Icoil = 0.0
        if self.has("coil"):
            dv = Vn.get(nets["K1"], 0.0) - Vn.get(nets["K2"], 0.0)
            Icoil = dv / S.R_coil
            zoff = (self.coil_pos - self.sensor_pos) / 1000.0
            Rr = S.d_coil / 2.0
            fall = (Rr * Rr / (Rr * Rr + zoff * zoff)) ** 1.5
            Bc = S.k_coil * 1000.0 * Icoil * fall      # mT  (k is mT/mA)
            Bu[0] += Bc                                # coil axis = East
        Bax = dot(Bu, ax)
        # --- external flux concentrator --------------------------------
        if self.sheets_on and self.has("sheets"):
            Bax *= (1.0 + S.n_fc * S.L2 / max(self.L1, 1.0))
        # --- flat coil --------------------------------------------------
        Iflat = 0.0
        if self.has("flat"):
            dv = Vn.get(nets["F1"], 0.0) - Vn.get(nets["F2"], 0.0)
            Iflat = dv / S.R_flat
            Bax += S.k_flat * Iflat
        # --- bias magnet ------------------------------------------------
        if self.magnet_on and self.has("magnet"):
            Bax += S.Bm0 / (1.0 + (self.magnet_dist / S.xm0) ** 3)
        # --- buried circuit ---------------------------------------------
        Ipcb = 0.0
        if self.has("pcb") and self.has("rotplate"):
            dv = Vn.get(nets["W1"], 0.0) - Vn.get(nets["W2"], 0.0)
            Ipcb = dv / S.R_pcb
            if abs(Ipcb) > 1e-6:
                path = S.pcb_paths[self.pcb_index]
                th = math.radians(self.pcb_rot)
                ct, st = math.cos(th), math.sin(th)
                pts = []
                for (bx, by) in path:
                    # board centre 15,15 sits at (pcb_x, pcb_y) of the plate
                    dx, dy = bx - 15.0, by - 15.0
                    X = self.pcb_x + dx * ct - dy * st
                    Y = self.pcb_y + dx * st + dy * ct
                    pts.append((X - 20.0, Y - 20.0, -S.pcb_z))
                Bp = [0.0, 0.0, 0.0]
                for i in range(len(pts) - 1):
                    b = seg_field(pts[i], pts[i + 1], (0.0, 0.0, 0.0), Ipcb)
                    Bp = [Bp[0] + b[0], Bp[1] + b[1], Bp[2] + b[2]]
                Bax += dot(Bp, ax)
        return Bax, Icoil, Iflat, Ipcb

    # ------------------------------------------------------------ update
    def update(self):
        nets, Vn, _ = self.solve_circuit()
        Bax, *_ = self.field_axis(nets, Vn)
        self.B_axis = Bax
        self._Rel = self.S.element_R(Bax)
        nets, Vn, _ = self.solve_circuit()
        self.readings = [self._read_meter(i, nets, Vn) for i in range(3)]
        return nets, Vn

    def _read_meter(self, i, nets, Vn):
        m = self.meter_mode[i]
        if m == "OFF" or not self.has("dmm"):
            return None
        c, v, a = "M%dC" % (i + 1), "M%dV" % (i + 1), "M%dA" % (i + 1)
        g = self.S.meter_gain[i]
        if m == "V":
            val = (Vn.get(nets[v], 0.0) - Vn.get(nets[c], 0.0)) * g
            return ("V", val)
        if m == "OHM":
            dv = Vn.get(nets[v], 0.0) - Vn.get(nets[c], 0.0)
            return ("OHM", dv / 1.0e-4 * g)
        if m in ("A", "mA"):
            Rs = 0.02 if m == "A" else 12.0
            val = (Vn.get(nets[a], 0.0) - Vn.get(nets[c], 0.0)) / Rs * g
            return (m, val)
        return None


def _lin_solve(A, b):
    n = len(b)
    M = [A[i][:] + [b[i]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-18:
            M[col][col] = 1.0e-12
            piv = col
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        for r in range(n):
            if r == col:
                continue
            f = M[r][col] / pv
            if f == 0.0:
                continue
            for k in range(col, n + 1):
                M[r][k] -= f * M[col][k]
    return [M[i][n] / M[i][i] for i in range(n)]


# --------------------------------------------------------------------------
#  Multimeter display formatting (KYORITSU 1009, 4000 counts, autorange)
# --------------------------------------------------------------------------
V_RANGES = [(0.4, 4), (4.0, 3), (40.0, 2), (400.0, 1), (600.0, 1)]
O_RANGES = [(400.0, 1), (4e3, 0), (40e3, -1), (400e3, -2), (4e6, -3), (40e6, -4)]
A_RANGES = [(10.0, 3)]
MA_RANGES = [(40.0, 2), (400.0, 1)]


def _fmt(val, ranges, unit, noise_rel, noise_abs, rnd):
    a = abs(val)
    for top, dec in ranges:
        if a < top * 0.9999:
            break
    else:
        return "O.L"
    val = val * (1.0 + rnd.gauss(0.0, noise_rel)) + rnd.gauss(0.0, noise_abs)
    step = 10.0 ** (-dec)
    q = round(val / step) * step
    if abs(q) >= top:
        return "O.L"
    return ("%%.%df" % max(dec, 0)) % q + " " + unit


def format_reading(rd, rnd):
    if rd is None:
        return ""
    kind, val = rd
    if kind == "V":
        a = abs(val)
        if a < 0.4:
            return _fmt(val * 1000.0, [(400.0, 1)], "mV", 6e-5, 0.05, rnd)
        return _fmt(val, V_RANGES[1:], "V", 6e-5, 5e-4, rnd)
    if kind == "OHM":
        if val < -1.0 or val > 40e6:
            return "O.L"
        a = abs(val)
        if a < 400:
            return _fmt(val, [(400.0, 1)], "\u03a9", 2e-4, 0.15, rnd)
        if a < 4e3:
            return _fmt(val, [(4e3, 0)], "\u03a9", 2e-4, 0.7, rnd)
        if a < 40e3:
            return _fmt(val / 1e3, [(40.0, 2)], "k\u03a9", 2e-4, 0.006, rnd)
        if a < 400e3:
            return _fmt(val / 1e3, [(400.0, 1)], "k\u03a9", 3e-4, 0.06, rnd)
        if a < 4e6:
            return _fmt(val / 1e6, [(4.0, 3)], "M\u03a9", 5e-4, 0.0015, rnd)
        return _fmt(val / 1e6, [(40.0, 2)], "M\u03a9", 1e-3, 0.02, rnd)
    if kind == "A":
        return _fmt(val, A_RANGES, "A", 3e-4, 3e-4, rnd)
    if kind == "mA":
        return _fmt(val * 1000.0, MA_RANGES, "mA", 3e-4, 0.02, rnd)
    return ""


# ==========================================================================
#  2-D ARTWORK  (reconstructed from the official apparatus photograph)
# ==========================================================================
CLR = dict(
    table="#e8e4d9", panel="#f4f2ec", ink="#22252b", grey="#9aa0a6",
    white="#fbfbf9", teal="#2f7f86", darkred="#5d1f24", copper="#b87333",
    coppr2="#8a5522", green="#5fb54a", lime="#c9e07a", blue="#2b5fa8",
    red="#c0392b", yellow="#e6c34a", black="#1a1a1a", zone="#b9b2a0",
    boxwhite="#f0eee6", magnet="#2b2b2b", steel="#b0b4b8", pcbgrid="#3b4a9e",
)


def rr(cv, x0, y0, x1, y1, r, **kw):
    """rounded rectangle"""
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


def draw_icon(cv, pid, x, y, s=1.0, tags=()):
    """small pictogram of part `pid` centred on (x, y)"""
    o = []
    a = lambda i: o.append(i)

    def R(dx0, dy0, dx1, dy1, **kw):
        return cv.create_rectangle(x + dx0 * s, y + dy0 * s, x + dx1 * s,
                                   y + dy1 * s, tags=tags, **kw)

    def O(dx0, dy0, dx1, dy1, **kw):
        return cv.create_oval(x + dx0 * s, y + dy0 * s, x + dx1 * s,
                              y + dy1 * s, tags=tags, **kw)

    def L(pts, **kw):
        p = []
        for i in range(0, len(pts), 2):
            p += [x + pts[i] * s, y + pts[i + 1] * s]
        return cv.create_line(p, tags=tags, **kw)

    if pid == "lead":
        for i, c in enumerate((CLR["red"], CLR["blue"], CLR["yellow"])):
            a(cv.create_line(x - 16 * s, y + (i - 1) * 6 * s - 2 * s,
                             x - 4 * s, y + (i - 1) * 6 * s - 9 * s,
                             x + 6 * s, y + (i - 1) * 6 * s + 3 * s,
                             x + 16 * s, y + (i - 1) * 6 * s - 4 * s,
                             smooth=True, width=2.4 * s, fill=c, tags=tags))
    elif pid == "rheo":
        a(R(-16, -11, 16, 11, fill=CLR["boxwhite"], outline=CLR["ink"]))
        a(O(-6, -8, 6, 4, fill="#7d99c4", outline=CLR["ink"]))
        a(L([0, -2, 0, -9], width=2 * s, fill=CLR["ink"]))
        a(O(-13, 3, -8, 8, fill="#2b5fa8", outline=CLR["ink"]))
        a(O(8, 3, 13, 8, fill="#2b5fa8", outline=CLR["ink"]))
    elif pid == "accord":
        a(R(-16, -7, 8, 7, fill="#2b2b2b", outline=CLR["ink"]))
        for i in range(3):
            a(O(-13 + i * 8, -3, -9 + i * 8, 3, fill="#e5e1d5", outline=""))
        a(L([8, 0, 17, 0], width=2.4 * s, fill="#2b2b2b"))
    elif pid == "batt":
        a(R(-17, -12, 17, 12, fill=CLR["boxwhite"], outline=CLR["ink"]))
        for i in range(3):
            a(O(-11 + i * 10, -9, -6 + i * 10, -4, fill=CLR["red"], outline=CLR["ink"]))
        a(O(-15, 4, -10, 9, fill="#2b5fa8", outline=CLR["ink"]))
        a(O(10, 4, 15, 9, fill="#2b5fa8", outline=CLR["ink"]))
        a(O(-4, 2, 4, 10, fill=CLR["green"], outline=CLR["ink"]))
    elif pid == "flat":
        a(R(-13, -5, 13, 5, fill=CLR["copper"], outline=CLR["coppr2"]))
        for i in range(9):
            a(L([-12 + i * 3, -5, -12 + i * 3, 5], fill=CLR["coppr2"], width=1.2 * s))
        a(L([13, 0, 18, 4], fill=CLR["yellow"], width=2 * s))
    elif pid == "dcsrc":
        a(R(-17, -12, 17, 12, fill="#1e1e22", outline=CLR["ink"]))
        a(O(-9, -6, 5, 8, fill="#4a4a52", outline="#8a8a92"))
        a(L([-2, 1, -2, -5], width=2.4 * s, fill="#e8e8e8"))
        a(O(9, -6, 14, -1, fill="#2b5fa8", outline="#cfcfcf"))
        a(O(9, 3, 14, 8, fill="#c0392b", outline="#cfcfcf"))
    elif pid == "post":
        a(R(-15, 6, 15, 12, fill="#efe9cf", outline=CLR["ink"]))
        a(R(-2, -14, 2, 6, fill="#d9d4c0", outline=CLR["ink"]))
        a(O(-5, -18, 5, -10, fill=CLR["white"], outline=CLR["ink"]))
    elif pid == "coil":
        a(O(-15, -15, 15, 15, outline=CLR["copper"], width=4 * s))
        a(O(-10, -10, 10, 10, outline=CLR["coppr2"], width=2.5 * s))
        a(R(-16, 11, 16, 16, fill=CLR["white"], outline=CLR["ink"]))
    elif pid == "pcb":
        a(O(-15, -15, 15, 15, fill="#e9e9e4", outline=CLR["ink"]))
        for i in range(-8, 9, 4):
            a(L([i, -9, i, 9], fill=CLR["pcbgrid"], width=0.8))
            a(L([-9, i, 9, i], fill=CLR["pcbgrid"], width=0.8))
    elif pid == "trail":
        a(R(-18, -4, 18, 4, fill="#f1efdc", outline=CLR["ink"]))
        a(L([-18, 0, 18, 0], fill=CLR["grey"], width=1.4 * s))
    elif pid == "rotplate":
        a(O(-14, -14, 14, 14, fill=CLR["white"], outline=CLR["ink"]))
        a(O(-2, -2, 2, 2, fill=CLR["ink"], outline=""))
    elif pid == "platform":
        a(R(-19, -12, 19, 12, fill=CLR["lime"], outline=CLR["ink"]))
        a(R(-17, 3, 17, 8, fill="#f2efc9", outline=CLR["ink"]))
        for i in range(-16, 17, 3):
            a(L([i, 3, i, 6], fill=CLR["ink"], width=0.8))
    elif pid == "sensor":
        a(R(-8, -5, 8, 5, fill=CLR["black"], outline="#444"))
        for i in range(4):
            a(L([-8 + i * 5 + 1, -5, -8 + i * 5 + 1, -8], fill=CLR["steel"], width=1.6 * s))
            a(L([-8 + i * 5 + 1, 5, -8 + i * 5 + 1, 8], fill=CLR["steel"], width=1.6 * s))
        a(O(-6, -3, -4, -1, outline="#999"))
    elif pid == "holder":
        a(R(-19, -5, 19, 5, fill="#7fc98f", outline=CLR["ink"]))
        a(R(6, -3, 12, 3, fill=CLR["black"], outline=""))
        for i in range(-17, 18, 3):
            a(L([i, -5, i, -2], fill=CLR["ink"], width=0.7))
    elif pid == "table":
        a(O(-16, -16, 16, 16, fill=CLR["white"], outline=CLR["ink"]))
        for k in range(0, 360, 15):
            t = math.radians(k)
            a(L([13 * math.cos(t), 13 * math.sin(t),
                 16 * math.cos(t), 16 * math.sin(t)], fill=CLR["ink"], width=0.8))
        a(O(-2, -2, 2, 2, fill=CLR["ink"], outline=""))
    elif pid == "sbox":
        a(R(-19, -12, 19, 12, fill=CLR["boxwhite"], outline=CLR["ink"]))
        for r_ in range(2):
            for c_ in range(4):
                col = CLR["red"] if r_ == 0 else CLR["black"]
                a(O(-15 + c_ * 8, -8 + r_ * 10, -11 + c_ * 8, -4 + r_ * 10,
                    fill=col, outline=CLR["ink"]))
    elif pid == "cbox":
        a(R(-19, -12, 19, 12, fill=CLR["boxwhite"], outline=CLR["ink"]))
        for r_ in range(2):
            for c_ in range(3):
                a(O(-14 + c_ * 10, -8 + r_ * 10, -10 + c_ * 10, -4 + r_ * 10,
                    fill=CLR["red"] if r_ == 0 else CLR["black"], outline=CLR["ink"]))
                a(L([-12 + c_ * 10, -4, -12 + c_ * 10, 6], fill=CLR["ink"], width=1))
    elif pid == "sheets":
        a(R(-16, -8, -3, 8, fill=CLR["steel"], outline=CLR["ink"]))
        a(R(3, -8, 16, 8, fill=CLR["steel"], outline=CLR["ink"]))
    elif pid == "magnet":
        a(R(-9, -9, 9, 9, fill=CLR["magnet"], outline="#555"))
        a(L([-9, 0, 9, 0], fill="#777", width=1.2))
    elif pid == "dmm":
        a(rr(cv, x - 14 * s, y - 18 * s, x + 14 * s, y + 18 * s, 5 * s,
             fill=CLR["teal"], outline=CLR["ink"], tags=tags))
        a(R(-10, -15, 10, -7, fill="#9fb8a0", outline=CLR["darkred"]))
        a(O(-8, -3, 8, 13, fill="#3d6f52", outline=CLR["ink"]))
        a(L([0, 5, 0, -2], fill=CLR["white"], width=2 * s))
        for i in range(3):
            a(O(-9 + i * 8, 14, -5 + i * 8, 18, fill=CLR["ink"], outline=CLR["grey"]))
    elif pid == "bulb":
        a(O(-9, -14, 9, 4, fill="#fff6cc", outline=CLR["ink"]))
        a(R(-5, 4, 5, 12, fill=CLR["steel"], outline=CLR["ink"]))
        a(L([-3, -2, 0, -8, 3, -2], fill=CLR["ink"], width=1.2))
    else:
        a(R(-12, -8, 12, 8, fill=CLR["grey"], outline=CLR["ink"]))
    return o


# ==========================================================================
#  ASSEMBLY TAB
# ==========================================================================
BIN_W = 268
ZONE_RECTS = {
    "post":     (300, 116, 520, 400),
    "table":    (540, 116, 700, 400),
    "holder":   (720, 116, 880, 400),
    "sensor":   (900, 116, 1060, 400),
    "rail":     (300, 430, 720, 700),
    "rotplate": (300, 720, 720, 800),
    "elec":     (1080, 116, 1240, 800),
}


class AssemblyTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.rig = app.rig
        self.cv = tk.Canvas(self, bg=CLR["table"], highlightthickness=0,
                            width=1250, height=800, scrollregion=(0, 0, 1250, 800))
        self.cv.pack(fill="both", expand=True)
        self.msg = tk.StringVar(value=T("부품을 오른쪽 영역으로 끌어다 놓으세요.  (설치된 부품 위에서 오른쪽 클릭 = 제거)",
                                        "Drag a part onto a zone on the right.  (right-click an installed part to remove it)"))
        self.bar = ttk.Label(self, textvariable=self.msg, anchor="w")
        self.bar.pack(fill="x")
        self.bin_scroll = 0
        self.drag = None
        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_move)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Button-3>", self.on_right)
        self.cv.bind("<MouseWheel>", self.on_wheel)
        self.cv.bind("<Button-4>", lambda e: self.on_wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self.on_wheel(e, -1))
        self.redraw()

    # ------------------------------------------------------------------
    def on_wheel(self, e, d=None):
        if e.x > BIN_W:
            return
        d = d if d is not None else (1 if e.delta > 0 else -1)
        self.bin_scroll = max(-540, min(0, self.bin_scroll + d * 40))
        self.redraw()

    def redraw(self):
        cv = self.cv
        cv.delete("all")
        cv.create_rectangle(0, 0, BIN_W, 800, fill=CLR["panel"], outline="")
        cv.create_text(BIN_W / 2, 22, text=T("부품 상자", "Parts box"),
                       font=("", 13, "bold"), fill=CLR["ink"])
        cv.create_line(BIN_W, 0, BIN_W, 800, fill=CLR["zone"])
        y = 52 + self.bin_scroll
        self.bin_hits = []
        for pid, num, ko, en, zone, pre in PARTS:
            if pid in self.rig.installed:
                continue
            if -40 < y < 810:
                cv.create_rectangle(12, y - 20, BIN_W - 12, y + 20,
                                    fill=CLR["white"], outline="#d8d4c6")
                draw_icon(cv, pid, 42, y, 0.62)
                cv.create_text(72, y - 7, anchor="w", font=("", 10, "bold"),
                               text="[%d] %s" % (num, T(ko, en)), fill=CLR["ink"])
                pren = ", ".join("[%d]" % PART_BY_ID[p][1] for p in pre)
                cv.create_text(72, y + 9, anchor="w", font=("", 8),
                               fill="#7a7469",
                               text=(T("필요: ", "needs: ") + pren) if pre else "")
                self.bin_hits.append((pid, 12, y - 20, BIN_W - 12, y + 20))
            y += 46
        # ---- zones ----
        for zid, (x0, y0, x1, y1) in ZONE_RECTS.items():
            cv.create_rectangle(x0, y0, x1, y1, outline=CLR["zone"], dash=(5, 4))
            cv.create_text(x0 + 8, y0 + 12, anchor="w", font=("", 9, "bold"),
                           fill="#8b8474", text=ZONES[zid])
        self.draw_installed()

    def draw_installed(self):
        cv = self.cv
        self.inst_hits = []
        slots = {}
        for pid, num, ko, en, zone, pre in PARTS:
            if pid not in self.rig.installed:
                continue
            x0, y0, x1, y1 = ZONE_RECTS[zone]
            k = slots.get(zone, 0)
            slots[zone] = k + 1
            percol = max(1, int((y1 - y0 - 26) // 62))
            cx = x0 + 42 + (k // percol) * 92
            cy = y0 + 50 + (k % percol) * 62
            draw_icon(cv, pid, cx, cy, 0.72)
            cv.create_text(cx, cy + 26, text="[%d]" % num, font=("", 8, "bold"),
                           fill="#6d6759")
            self.inst_hits.append((pid, cx - 26, cy - 26, cx + 26, cy + 26))

    # ------------------------------------------------------------------
    def on_press(self, e):
        for pid, x0, y0, x1, y1 in getattr(self, "bin_hits", []):
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                self.drag = pid
                self.ghost = draw_icon(self.cv, pid, e.x, e.y, 0.8, tags=("ghost",))
                return

    def on_move(self, e):
        if self.drag:
            self.cv.delete("ghost")
            draw_icon(self.cv, self.drag, e.x, e.y, 0.8, tags=("ghost",))

    def on_release(self, e):
        if not self.drag:
            return
        pid = self.drag
        self.drag = None
        self.cv.delete("ghost")
        target = None
        for zid, (x0, y0, x1, y1) in ZONE_RECTS.items():
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                target = zid
        p = PART_BY_ID[pid]
        if target is None:
            self.msg.set(T("부품을 점선 영역 안에 놓아야 합니다.",
                           "The part must be dropped inside a dashed zone."))
            return
        if target != p[4]:
            self.msg.set(T("[%d] %s 은(는) '%s' 영역에 설치할 수 없습니다.",
                           "[%d] %s cannot be installed in '%s'.")
                         % (p[1], T(p[2], p[3]), ZONES[target]))
            return
        ok, missing = self.rig.can_place(pid)
        if not ok:
            mp = PART_BY_ID[missing]
            self.msg.set(T("먼저 [%d] %s 을(를) 설치해야 합니다.",
                           "You must install [%d] %s first.")
                         % (mp[1], T(mp[2], mp[3])))
            return
        self.rig.installed.add(pid)
        self.msg.set(T("[%d] %s 설치 완료.", "[%d] %s installed.")
                     % (p[1], T(p[2], p[3])))
        self.redraw()
        self.app.bench.rebuild()

    def on_right(self, e):
        for pid, x0, y0, x1, y1 in getattr(self, "inst_hits", []):
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                dep = [q[0] for q in PARTS
                       if q[0] in self.rig.installed and pid in q[5]]
                if dep:
                    d = PART_BY_ID[dep[0]]
                    self.msg.set(T("[%d] %s 이(가) 이 부품 위에 설치되어 있습니다.",
                                   "[%d] %s is mounted on this part.")
                                 % (d[1], T(d[2], d[3])))
                    return
                self.rig.installed.discard(pid)
                self.rig.wires = [w for w in self.rig.wires
                                  if TERM_OWNER.get(w[0]) != pid
                                  and TERM_OWNER.get(w[1]) != pid]
                self.msg.set(T("[%d] 제거됨.", "[%d] removed.")
                             % PART_BY_ID[pid][1])
                self.redraw()
                self.app.bench.rebuild()
                return


# ==========================================================================
#  BENCH TAB
# ==========================================================================
WIRE_COLORS = ["#c0392b", "#2b5fa8", "#e0b83a", "#3f9c52", "#8e44ad",
               "#e07b39", "#17868f", "#7a5230"]

APX, APY, APW, APH = 18, 16, 640, 452           # apparatus panel
DEV = {
    "sbox":  (676, 16, 1002, 150),
    "batt":  (676, 162, 1002, 296),
    "dcsrc": (676, 308, 1002, 438),
    "rheo":  (676, 450, 836, 560),
    "bulb":  (846, 450, 1002, 560),
    "cbox":  (676, 572, 1002, 706),
    "dmm1":  (1014, 16, 1232, 366),
    "dmm2":  (1244, 16, 1462, 366),
    "dmm3":  (1474, 16, 1692, 366),
    "appt":  (1014, 380, 1692, 508),           # coil / flat coil / pcb terminals
}


class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.rig = app.rig
        self.cv = tk.Canvas(self, bg=CLR["table"], highlightthickness=0,
                            scrollregion=(0, 0, 1710, 1010))
        hs = ttk.Scrollbar(self, orient="horizontal", command=self.cv.xview)
        vs = ttk.Scrollbar(self, orient="vertical", command=self.cv.yview)
        self.cv.configure(xscrollcommand=hs.set, yscrollcommand=vs.set)
        self.cv.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.status = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status, anchor="w").grid(
            row=2, column=0, columnspan=2, sticky="ew")

        self.term_xy = {}
        self.sel_term = None
        self.widgets = []
        self.vars = {}
        self.cv.bind("<Button-1>", self.on_click)
        self.cv.bind("<Button-3>", self.on_rclick)
        self.rebuild()

    # ------------------------------------------------------------------
    def cx(self, e):
        return self.cv.canvasx(e.x), self.cv.canvasy(e.y)

    def rebuild(self):
        for w in self.widgets:
            w.destroy()
        self.widgets = []
        self.cv.delete("all")
        self.term_xy = {}
        self.build_controls()
        self.draw_devices()
        self.refresh()

    # ---------------------------------------------------------- controls
    def _scale(self, x, y, w, lo, hi, var, cb, res=1.0):
        s = ttk.Scale(self.cv, from_=lo, to=hi, variable=var, length=w,
                      command=lambda v: cb())
        self.cv.create_window(x, y, window=s, anchor="w")
        self.widgets.append(s)
        return s

    def _lab(self, x, y, txt, anchor="w", font=("", 9), fill=None):
        return self.cv.create_text(x, y, text=txt, anchor=anchor, font=font,
                                   fill=fill or CLR["ink"])

    def build_controls(self):
        R = self.rig
        cvw = self.cv
        y0 = APY + APH + 16
        self.cv.create_rectangle(APX, y0 - 8, APX + APW, 992,
                                 fill=CLR["panel"], outline=CLR["zone"])
        self._lab(APX + 12, y0 + 8, T("장치 조작", "Apparatus controls"),
                  font=("", 11, "bold"))
        y = y0 + 34
        self.vars = {}

        def add_var(key, val):
            v = tk.DoubleVar(value=val)
            self.vars[key] = v
            return v

        # -- circular table orientation ---------------------------------
        if R.has("table"):
            ov = tk.StringVar(value="V" if R.plate_vertical else "H")
            self.vars["orient"] = ov

            def set_or():
                R.plate_vertical = (ov.get() == "V")
                self.refresh()
            self._lab(APX + 12, y, T("원형 판 [15] 방향", "Circular table [15]"))
            f = ttk.Frame(cvw)
            ttk.Radiobutton(f, text=T("수평 (짧은 기둥)", "horizontal"),
                            variable=ov, value="H", command=set_or).pack(side="left")
            ttk.Radiobutton(f, text=T("수직 (남북면, 긴 기둥)", "vertical (N-S plane)"),
                            variable=ov, value="V", command=set_or).pack(side="left")
            cvw.create_window(APX + 150, y, window=f, anchor="w")
            self.widgets.append(f)
            y += 26
            v = add_var("alpha", R.alpha)

            def set_a():
                R.alpha = round(v.get(), 0)
                self.refresh()
            self._lab(APX + 12, y, T("거치대 각도  \u03b1", "holder angle  \u03b1"))
            self._scale(APX + 150, y, 330, 0, 360, v, set_a)
            self.lbl_alpha = self._lab(APX + 495, y, "")
            y += 28

        # -- circular coil ------------------------------------------------
        if R.has("coil"):
            v = add_var("coilpos", R.coil_pos)

            def set_c():
                R.coil_pos = round(v.get(), 0)
                self.refresh()
            self._lab(APX + 12, y, T("원형 코일 [8] 위치", "circular coil [8] pos."))
            self._scale(APX + 150, y, 330, 0, 200, v, set_c)
            self.lbl_coil = self._lab(APX + 495, y, "")
            y += 28

        # -- magnet -------------------------------------------------------
        if R.has("magnet"):
            bv = tk.IntVar(value=int(R.magnet_on))
            self.vars["magnet_on"] = bv
            v = add_var("magdist", R.magnet_dist)

            def set_m():
                R.magnet_on = bool(bv.get())
                R.magnet_dist = round(v.get(), 1)
                self.refresh()
            c = ttk.Checkbutton(cvw, text=T("영구자석 판 [19] 부착",
                                            "attach magnet [19]"),
                                variable=bv, command=set_m)
            cvw.create_window(APX + 12, y, window=c, anchor="w")
            self.widgets.append(c)
            self._scale(APX + 200, y, 280, 2, 40, v, set_m)
            self.lbl_mag = self._lab(APX + 495, y, "")
            y += 28

        # -- ferromagnetic sheets ----------------------------------------
        if R.has("sheets"):
            bv = tk.IntVar(value=int(R.sheets_on))
            self.vars["sheets_on"] = bv
            v = add_var("L1", R.L1)

            def set_s():
                R.sheets_on = bool(bv.get())
                R.L1 = round(v.get(), 1)
                self.refresh()
            c = ttk.Checkbutton(cvw, text=T("강자성 시트 [18] 설치",
                                            "place sheets [18]"),
                                variable=bv, command=set_s)
            cvw.create_window(APX + 12, y, window=c, anchor="w")
            self.widgets.append(c)
            self._scale(APX + 200, y, 280, 4, 30, v, set_s)
            self.lbl_L1 = self._lab(APX + 495, y, "")
            y += 28

        # -- pcb ----------------------------------------------------------
        if R.has("pcb"):
            iv = tk.IntVar(value=R.pcb_index)
            self.vars["pcbidx"] = iv
            vx = add_var("pcbx", R.pcb_x)
            vy = add_var("pcby", R.pcb_y)
            vr = add_var("pcbrot", R.pcb_rot)

            def set_p():
                R.pcb_index = iv.get()
                R.pcb_x = round(vx.get(), 1)
                R.pcb_y = round(vy.get(), 1)
                R.pcb_rot = round(vr.get(), 0)
                self.refresh()
            f = ttk.Frame(cvw)
            ttk.Label(f, text=T("기판 [9]", "board [9]")).pack(side="left")
            ttk.Radiobutton(f, text="1", variable=iv, value=1,
                            command=set_p).pack(side="left")
            ttk.Radiobutton(f, text="2", variable=iv, value=2,
                            command=set_p).pack(side="left")
            cvw.create_window(APX + 12, y, window=f, anchor="w")
            self.widgets.append(f)
            y += 24
            for key, var, lo, hi, txt in (
                    ("x", vx, 0, 40, T("횡방향 레일 [10]", "transverse rail [10]")),
                    ("y", vy, 0, 40, T("종방향 레일 [12]", "longitudinal rail [12]")),
                    ("r", vr, 0, 360, T("회전판 [11] 각도", "rotating plate [11]"))):
                self._lab(APX + 12, y, txt)
                self._scale(APX + 150, y, 330, lo, hi, var, set_p)
                self.vars["lbl_pcb" + key] = self._lab(APX + 495, y, "")
                y += 26

        # -- battery / source / rheostat widgets on the device panels ----
        self.build_device_widgets()

    def build_device_widgets(self):
        R = self.rig
        cvw = self.cv
        if R.has("batt"):
            x0, y0, x1, y1 = DEV["batt"]
            b = ttk.Button(cvw, text=T("전원 버튼", "power"),
                           command=self.toggle_batt)
            cvw.create_window(x1 - 60, y1 - 26, window=b)
            self.widgets.append(b)
        if R.has("dcsrc"):
            x0, y0, x1, y1 = DEV["dcsrc"]
            v = tk.DoubleVar(value=R.src_knob * 100)
            self.vars["src"] = v

            def set_src(_=None):
                R.src_knob = v.get() / 100.0
                self.refresh()
            s = ttk.Scale(cvw, from_=0, to=100, variable=v, length=210,
                          command=set_src)
            cvw.create_window(x0 + 18, y1 - 30, window=s, anchor="w")
            self.widgets.append(s)
            b = ttk.Button(cvw, text=T("극성 전환", "reverse"),
                           command=self.toggle_rev)
            cvw.create_window(x1 - 52, y1 - 30, window=b)
            self.widgets.append(b)
        if R.has("rheo"):
            x0, y0, x1, y1 = DEV["rheo"]
            v = tk.DoubleVar(value=R.rheo_knob * 100)
            self.vars["rheo"] = v

            def set_rh(_=None):
                R.rheo_knob = v.get() / 100.0
                self.refresh()
            s = ttk.Scale(cvw, from_=0, to=100, variable=v, length=120,
                          command=set_rh)
            cvw.create_window(x0 + 16, y1 - 22, window=s, anchor="w")
            self.widgets.append(s)
        if R.has("dmm"):
            for i in range(3):
                x0, y0, x1, y1 = DEV["dmm%d" % (i + 1)]
                var = tk.StringVar(value=R.meter_mode[i])
                self.vars["mm%d" % i] = var
                f = ttk.Frame(cvw)
                for md in MODES:
                    ttk.Radiobutton(f, text=md, variable=var, value=md,
                                    command=self.apply_modes).pack(anchor="w")
                cvw.create_window((x0 + x1) / 2, y0 + 210, window=f)
                self.widgets.append(f)
        b = ttk.Button(cvw, text=T("배선 모두 제거", "clear all wires"),
                       command=self.clear_wires)
        cvw.create_window(DEV["appt"][0] + 10, DEV["appt"][3] + 26,
                          window=b, anchor="w")
        self.widgets.append(b)

    def toggle_batt(self):
        self.rig.batt_on = not self.rig.batt_on
        self.refresh()

    def toggle_rev(self):
        self.rig.src_reverse = not self.rig.src_reverse
        self.refresh()

    def clear_wires(self):
        self.rig.wires = []
        self.sel_term = None
        self.refresh()

    def apply_modes(self):
        for i in range(3):
            v = self.vars.get("mm%d" % i)
            if v is not None:
                self.rig.meter_mode[i] = v.get()
        self.refresh()

    # ---------------------------------------------------------- devices
    def _panel(self, key, title, sub=""):
        x0, y0, x1, y1 = DEV[key]
        rr(self.cv, x0, y0, x1, y1, 8, fill=CLR["boxwhite"], outline=CLR["ink"])
        self.cv.create_text(x0 + 10, y0 + 13, anchor="w", font=("", 10, "bold"),
                            text=title, fill=CLR["ink"])
        if sub:
            self.cv.create_text(x1 - 10, y0 + 13, anchor="e", font=("", 8),
                                text=sub, fill="#7a7469")
        return x0, y0, x1, y1

    def _socket(self, tid, x, y, label, color="#b03030"):
        self.term_xy[tid] = (x, y)
        self.cv.create_oval(x - 8, y - 8, x + 8, y + 8, fill=color,
                            outline=CLR["ink"], width=1.4, tags=("term", tid))
        self.cv.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#111", outline="")
        if label:
            self.cv.create_text(x, y + 16, text=label, font=("", 8, "bold"),
                                fill=CLR["ink"])

    def draw_devices(self):
        R = self.rig
        cv = self.cv
        # ---- sensor connection box [16] -------------------------------
        if R.has("sbox"):
            x0, y0, x1, y1 = self._panel(
                "sbox", T("[16] 센서 연결 박스", "[16] Sensor connection box"),
                T("[13] 센서 연결됨", "[13] sensor plugged in"))
            for i in range(8):
                col, row = i % 4, i // 4
                self._socket("S%d" % (i + 1), x0 + 52 + col * 62,
                             y0 + 52 + row * 46, str(i + 1),
                             "#b03030" if row == 0 else "#303030")
        # ---- battery [4] ------------------------------------------------
        if R.has("batt"):
            x0, y0, x1, y1 = self._panel("batt", T("[4] 배터리", "[4] Battery"))
            for i in range(5):
                self._socket("B%d" % i, x0 + 40 + i * 52, y0 + 52, str(i),
                             "#2b5fa8" if i in (0, 4) else "#b03030")
            self.batt_led = cv.create_oval(x0 + 20, y1 - 34, x0 + 36, y1 - 18,
                                           fill="#444", outline=CLR["ink"])
        # ---- variable DC source [6] --------------------------------------
        if R.has("dcsrc"):
            x0, y0, x1, y1 = self._panel(
                "dcsrc", T("[6] 가변 DC 전류원", "[6] Variable DC source"),
                "" if R.has("accord") else T("전원 코드 [3] 필요", "needs cord [3]"))
            cv.create_rectangle(x0 + 8, y0 + 22, x1 - 8, y1 - 46,
                                fill="#1e1e22", outline="#3a3a40")
            self._socket("C+", x1 - 120, y0 + 60, "+", "#c0392b")
            self._socket("C-", x1 - 60, y0 + 60, "\u2212", "#2b5fa8")
            self.src_txt = cv.create_text(x0 + 30, y0 + 60, anchor="w",
                                          font=("", 9), fill="#dfe4ea", text="")
        # ---- rheostat [2] --------------------------------------------------
        if R.has("rheo"):
            x0, y0, x1, y1 = self._panel("rheo", T("[2] 가변저항기", "[2] Rheostat"))
            self._socket("P1", x0 + 40, y0 + 52, "a", "#2b5fa8")
            self._socket("P2", x0 + 110, y0 + 52, "b", "#2b5fa8")
        # ---- bulb [21] -----------------------------------------------------
        if R.has("bulb"):
            x0, y0, x1, y1 = self._panel(
                "bulb", T("[21] 이중 필라멘트 전구", "[21] Double filament bulb"))
            draw_icon(cv, "bulb", x0 + 34, y0 + 60, 1.0)
            for i, t in enumerate(("L1", "L2", "L3")):
                self._socket(t, x0 + 76 + i * 30, y0 + 60, str(i + 1),
                             "#303030")
        # ---- connection box [17] --------------------------------------------
        if R.has("cbox"):
            x0, y0, x1, y1 = self._panel(
                "cbox", T("[17] 연결 박스 (세 구멍끼리 단락)",
                          "[17] Connection box (3 sockets tied)"))
            for g in range(4):
                for k, suf in enumerate("abc"):
                    self._socket("J%d%s" % (g + 1, suf), x0 + 46 + g * 76,
                                 y0 + 50 + k * 26, "", "#7a7f86")
                cv.create_line(x0 + 46 + g * 76 + 14, y0 + 50,
                               x0 + 46 + g * 76 + 14, y0 + 102,
                               fill=CLR["ink"], width=1.4)
                cv.create_text(x0 + 46 + g * 76, y0 + 122, text=str(g + 1),
                               font=("", 8, "bold"), fill=CLR["ink"])
        # ---- multimeters -----------------------------------------------------
        if R.has("dmm"):
            for i in range(3):
                x0, y0, x1, y1 = self._panel("dmm%d" % (i + 1),
                                             T("[20] 멀티미터 %d", "[20] Multimeter %d") % (i + 1),
                                             "KYORITSU 1009")
                rr(cv, x0 + 10, y0 + 24, x1 - 10, y1 - 10, 8,
                   fill=CLR["teal"], outline=CLR["darkred"], width=2)
                cv.create_rectangle(x0 + 24, y0 + 40, x1 - 24, y0 + 100,
                                    fill="#9fb8a0", outline=CLR["darkred"], width=2)
                setattr(self, "disp%d" % i,
                        cv.create_text((x0 + x1) / 2, y0 + 70, text="",
                                       font=("Courier", 19, "bold"), fill="#1b2b1b"))
                cv.create_text((x0 + x1) / 2, y0 + 114, text="DIGITAL MULTIMETER",
                               font=("", 7, "bold"), fill="#e7e7e7")
                cv.create_rectangle(x0 + 34, y0 + 132, x1 - 34, y0 + 290,
                                    fill="#256a71", outline="#1c565c")
                for k, (tid, lab, col) in enumerate((
                        ("M%dA" % (i + 1), "A", "#c0392b"),
                        ("M%dC" % (i + 1), "COM", "#303030"),
                        ("M%dV" % (i + 1), "V/\u03a9", "#c0392b"))):
                    self._socket(tid, x0 + 44 + k * 62, y1 - 34, lab, col)
        # ---- coil / flat coil / pcb terminals ---------------------------------
        x0, y0, x1, y1 = self._panel(
            "appt", T("장치 단자", "Apparatus terminals"))
        col = x0 + 60
        if R.has("coil"):
            draw_icon(cv, "coil", col, y0 + 62, 0.75)
            self._socket("K1", col + 46, y0 + 48, "a", "#c0392b")
            self._socket("K2", col + 46, y0 + 84, "b", "#2b5fa8")
            cv.create_text(col, y0 + 100, text=T("[8] 원형 코일", "[8] circular coil"),
                           font=("", 8), fill=CLR["ink"])
            col += 190
        if R.has("flat"):
            draw_icon(cv, "flat", col, y0 + 62, 0.9)
            self._socket("F1", col + 46, y0 + 48, "a", "#c0392b")
            self._socket("F2", col + 46, y0 + 84, "b", "#2b5fa8")
            cv.create_text(col, y0 + 100, text=T("[5] 평면 코일", "[5] flat coil"),
                           font=("", 8), fill=CLR["ink"])
            col += 190
        if R.has("pcb"):
            draw_icon(cv, "pcb", col, y0 + 62, 0.75)
            self._socket("W1", col + 46, y0 + 48, "+", "#c0392b")
            self._socket("W2", col + 46, y0 + 84, "\u2212", "#2b5fa8")
            cv.create_text(col, y0 + 100, text=T("[9] 인쇄회로기판", "[9] PCB"),
                           font=("", 8), fill=CLR["ink"])

    # ---------------------------------------------------------- wiring
    def on_click(self, e):
        x, y = self.cx(e)
        hit = None
        for tid, (tx, ty) in self.term_xy.items():
            if (x - tx) ** 2 + (y - ty) ** 2 <= 121:
                hit = tid
                break
        if hit is None:
            return
        if not self.rig.wired():
            self.status.set(T("리드선 [1]을 먼저 설치하세요.",
                              "Install the lead wires [1] first."))
            return
        if self.sel_term is None:
            self.sel_term = hit
        elif self.sel_term == hit:
            self.sel_term = None
        else:
            self.rig.wires.append((self.sel_term, hit))
            self.sel_term = None
        self.refresh()

    def on_rclick(self, e):
        x, y = self.cx(e)
        for tid, (tx, ty) in self.term_xy.items():
            if (x - tx) ** 2 + (y - ty) ** 2 <= 121:
                self.rig.wires = [w for w in self.rig.wires if tid not in w]
                self.sel_term = None
                self.refresh()
                return

    def draw_wires(self):
        cv = self.cv
        cv.delete("wire")
        for i, (a, b) in enumerate(self.rig.wires):
            if a not in self.term_xy or b not in self.term_xy:
                continue
            x1, y1 = self.term_xy[a]
            x2, y2 = self.term_xy[b]
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2 + 26 + (i % 4) * 9
            cv.create_line(x1, y1, mx, my, x2, y2, smooth=True, width=3.2,
                           fill=WIRE_COLORS[i % len(WIRE_COLORS)], tags="wire")
        if self.sel_term and self.sel_term in self.term_xy:
            x, y = self.term_xy[self.sel_term]
            cv.create_oval(x - 13, y - 13, x + 13, y + 13, outline="#00a2ff",
                           width=3, tags="wire")

    # ---------------------------------------------------------- apparatus
    def draw_apparatus(self):
        cv = self.cv
        R = self.rig
        cv.delete("app")
        rr(cv, APX, APY, APX + APW, APY + APH, 8, fill=CLR["panel"],
           outline=CLR["ink"])
        cv.create_text(APX + 12, APY + 14, anchor="w", font=("", 10, "bold"),
                       tags="app", fill=CLR["ink"],
                       text=T("실험 배치 (윗면도)", "Set-up (top view)")
                       if not R.plate_vertical else
                       T("실험 배치 (남북 수직면)", "Set-up (vertical N-S plane)"))
        if not R.plate_vertical:
            self.draw_top_view()
        else:
            self.draw_side_view()

    def draw_top_view(self):
        cv = self.cv
        R = self.rig
        cx0, cy0 = APX + 240, APY + 170
        # compass
        cv.create_line(APX + 596, APY + 96, APX + 596, APY + 46, arrow="last",
                       width=2, fill=CLR["ink"], tags="app")
        cv.create_text(APX + 596, APY + 36, text="N", font=("", 10, "bold"),
                       fill=CLR["ink"], tags="app")
        cv.create_text(APX + 596, APY + 108, text="S", font=("", 9),
                       fill=CLR["ink"], tags="app")
        cv.create_text(APX + 622, APY + 72, text="E", font=("", 9),
                       fill="#8b8474", tags="app")
        if R.has("platform"):
            cv.create_rectangle(APX + 22, APY + 236, APX + 614, APY + 336,
                                fill=CLR["lime"], outline=CLR["ink"], tags="app")
            cv.create_rectangle(APX + 30, APY + 304, APX + 452, APY + 328,
                                fill="#f4f1cf", outline=CLR["ink"], tags="app")
            for mm in range(0, 201, 10):
                xx = APX + 40 + mm * 2.0
                cv.create_line(xx, APY + 304, xx,
                               APY + 312 if mm % 50 else APY + 320,
                               fill=CLR["ink"], width=0.8, tags="app")
                if mm % 50 == 0:
                    cv.create_text(xx, APY + 332, text=str(mm), font=("", 7),
                                   fill=CLR["ink"], tags="app")
        if R.has("trail"):
            cv.create_rectangle(APX + 468, APY + 240, APX + 492, APY + 436,
                                fill="#f4f1cf", outline=CLR["ink"], tags="app")
            for mm in range(0, 41, 5):
                yy = APY + 430 - mm * 4.6
                cv.create_line(APX + 468, yy, APX + 476, yy, fill=CLR["ink"],
                               width=0.8, tags="app")
        if R.has("rotplate"):
            px, py = APX + 528, APY + 356
            cv.create_oval(px - 72, py - 72, px + 72, py + 72, fill=CLR["white"],
                           outline=CLR["ink"], tags="app")
            if R.has("pcb"):
                self.draw_pcb(px, py)
        if R.has("table"):
            self.draw_table(cx0, cy0, horizontal=True)
        if R.has("coil"):
            xx = APX + 40 + R.coil_pos * 2.0
            cv.create_oval(xx - 15, cy0 - 82, xx + 15, cy0 + 82, outline=CLR["copper"],
                           width=7, tags="app")
            cv.create_oval(xx - 9, cy0 - 74, xx + 9, cy0 + 74, outline=CLR["coppr2"],
                           width=3, tags="app")
            cv.create_line(xx, cy0 + 82, xx, APY + 282, fill=CLR["grey"],
                           width=3, tags="app")
            cv.create_rectangle(xx - 30, APY + 282, xx + 30, APY + 296,
                                fill=CLR["white"], outline=CLR["ink"], tags="app")
            cv.create_text(xx, APY + 289, text="[8]", font=("", 7),
                           fill=CLR["ink"], tags="app")

    def draw_side_view(self):
        cv = self.cv
        R = self.rig
        cv.create_line(APX + 300, APY + 250, APX + 300, APY + 424, width=8,
                       fill="#d9d4c0", tags="app")
        cv.create_rectangle(APX + 250, APY + 424, APX + 350, APY + 440,
                            fill="#efe9cf", outline=CLR["ink"], tags="app")
        cv.create_line(APX + 496, APY + 60, APX + 596, APY + 60, arrow="last",
                       width=2, fill=CLR["ink"], tags="app")
        cv.create_text(APX + 608, APY + 60, text="N", font=("", 10, "bold"),
                       fill=CLR["ink"], tags="app")
        cv.create_text(APX + 484, APY + 60, text="S", font=("", 9),
                       fill=CLR["ink"], tags="app")
        cv.create_line(APX + 80, APY + 250, APX + 560, APY + 250, dash=(4, 4),
                       fill="#a49c8c", tags="app")
        if R.has("table"):
            self.draw_table(APX + 300, APY + 250, horizontal=False)

    def draw_table(self, cx0, cy0, horizontal=True):
        cv = self.cv
        R = self.rig
        rad = 92
        cv.create_oval(cx0 - rad, cy0 - rad, cx0 + rad, cy0 + rad,
                       fill=CLR["white"], outline=CLR["ink"], width=1.6, tags="app")
        for k in range(0, 360, 5):
            th = math.radians(k)
            r2 = rad - (11 if k % 30 == 0 else 5)
            cv.create_line(cx0 + r2 * math.cos(th), cy0 - r2 * math.sin(th),
                           cx0 + rad * math.cos(th), cy0 - rad * math.sin(th),
                           fill=CLR["ink"], width=1.1 if k % 30 == 0 else 0.6,
                           tags="app")
            if k % 30 == 0:
                cv.create_text(cx0 + (rad - 21) * math.cos(th),
                               cy0 - (rad - 21) * math.sin(th), text=str(k),
                               font=("", 7), fill="#6d6759", tags="app")
        if not R.has("holder"):
            return
        a = math.radians(R.alpha)
        ux, uy = math.cos(a), -math.sin(a)
        px, py = -uy, ux
        Wd = 12
        pts = [cx0 - 108 * ux + px * Wd, cy0 - 108 * uy + py * Wd,
               cx0 + 108 * ux + px * Wd, cy0 + 108 * uy + py * Wd,
               cx0 + 108 * ux - px * Wd, cy0 + 108 * uy - py * Wd,
               cx0 - 108 * ux - px * Wd, cy0 - 108 * uy - py * Wd]
        cv.create_polygon(pts, fill="#7fc98f", outline=CLR["ink"], tags="app")
        for k in range(-10, 11):
            d = k * 10
            cv.create_line(cx0 + d * ux + px * Wd, cy0 + d * uy + py * Wd,
                           cx0 + d * ux + px * (Wd - 5), cy0 + d * uy + py * (Wd - 5),
                           fill=CLR["ink"], width=0.7, tags="app")
        if R.has("sheets") and R.sheets_on:
            for sgn in (-1, 1):
                d = sgn * (R.L1 / 2.0) * 1.6
                d2 = d + sgn * 34
                mx, my = cx0 + d * ux, cy0 + d * uy
                nx, ny = cx0 + d2 * ux, cy0 + d2 * uy
                cv.create_polygon(mx + px * 17, my + py * 17,
                                  nx + px * 17, ny + py * 17,
                                  nx - px * 17, ny - py * 17,
                                  mx - px * 17, my - py * 17,
                                  fill=CLR["steel"], outline=CLR["ink"], tags="app")
        if R.has("magnet") and R.magnet_on:
            d = R.magnet_dist * 1.6
            mx, my = cx0 - d * ux, cy0 - d * uy
            cv.create_polygon(mx + px * 10 + ux * 7, my + py * 10 + uy * 7,
                              mx - px * 10 + ux * 7, my - py * 10 + uy * 7,
                              mx - px * 10 - ux * 7, my - py * 10 - uy * 7,
                              mx + px * 10 - ux * 7, my + py * 10 - uy * 7,
                              fill=CLR["magnet"], outline="#666", tags="app")
        if R.has("flat"):
            cv.create_polygon(cx0 + px * 15 + ux * 22, cy0 + py * 15 + uy * 22,
                              cx0 - px * 15 + ux * 22, cy0 - py * 15 + uy * 22,
                              cx0 - px * 15 - ux * 22, cy0 - py * 15 - uy * 22,
                              cx0 + px * 15 - ux * 22, cy0 + py * 15 - uy * 22,
                              outline=CLR["copper"], width=3, tags="app")
        if R.has("sensor"):
            cv.create_polygon(cx0 + px * 8 + ux * 13, cy0 + py * 8 + uy * 13,
                              cx0 - px * 8 + ux * 13, cy0 - py * 8 + uy * 13,
                              cx0 - px * 8 - ux * 13, cy0 - py * 8 - uy * 13,
                              cx0 + px * 8 - ux * 13, cy0 + py * 8 - uy * 13,
                              fill=CLR["black"], outline="#666", tags="app")
            cv.create_line(cx0 - ux * 30, cy0 - uy * 30, cx0 + ux * 30,
                           cy0 + uy * 30, arrow="both", fill="#e0b83a",
                           width=2, tags="app")

    def draw_pcb(self, px, py):
        cv = self.cv
        R = self.rig
        sc = 2.1
        th = math.radians(R.pcb_rot)
        ct, st = math.cos(th), math.sin(th)

        def b2s(bx, by):
            dx, dy = bx - 15.0, by - 15.0
            X = R.pcb_x + dx * ct - dy * st
            Y = R.pcb_y + dx * st + dy * ct
            return px + (X - 20.0) * sc, py - (Y - 20.0) * sc
        cv.create_oval(px - 70, py - 70, px + 70, py + 70, fill="#f2f1ec",
                       outline=CLR["ink"], tags="app")
        for g in range(0, 31, 2):
            x1, y1 = b2s(g, 0)
            x2, y2 = b2s(g, 30)
            cv.create_line(x1, y1, x2, y2, fill=CLR["pcbgrid"],
                           width=1.0 if g % 10 == 0 else 0.5, tags="app")
            x1, y1 = b2s(0, g)
            x2, y2 = b2s(30, g)
            cv.create_line(x1, y1, x2, y2, fill=CLR["pcbgrid"],
                           width=1.0 if g % 10 == 0 else 0.5, tags="app")
        for g in (0, 10, 20, 30):
            x1, y1 = b2s(g, -2.6)
            cv.create_text(x1, y1, text=str(g), font=("", 6), fill=CLR["ink"],
                           tags="app")
            x1, y1 = b2s(-2.6, g)
            cv.create_text(x1, y1, text=str(g), font=("", 6), fill=CLR["ink"],
                           tags="app")
        cv.create_text(px, py - 80, text=T("기판 %d", "board %d") % R.pcb_index,
                       font=("", 8, "bold"), fill=CLR["ink"], tags="app")
        # sensor position marker (the sensor sits above the board)
        cv.create_line(px - 8, py, px + 8, py, fill="#d01b1b", width=2, tags="app")
        cv.create_line(px, py - 8, px, py + 8, fill="#d01b1b", width=2, tags="app")

    # ---------------------------------------------------------- refresh
    def refresh(self):
        R = self.rig
        R.update()
        self.draw_apparatus()
        self.draw_wires()
        rnd = R._noise
        for i in range(3):
            if hasattr(self, "disp%d" % i):
                txt = format_reading(R.readings[i], rnd) if R.has("dmm") else ""
                self.cv.itemconfig(getattr(self, "disp%d" % i), text=txt)
        if R.has("batt"):
            self.cv.itemconfig(self.batt_led,
                               fill="#3ddc5c" if R.batt_on else "#444")
        if R.has("dcsrc"):
            self.cv.itemconfig(
                self.src_txt,
                text=T("노브 %3.0f %%\n방향 %s", "knob %3.0f %%\ndirection %s")
                % (R.src_knob * 100, "\u2192" if not R.src_reverse else "\u2190"))
        if hasattr(self, "lbl_alpha"):
            self.cv.itemconfig(self.lbl_alpha, text="%3.0f\u00b0" % R.alpha)
        if hasattr(self, "lbl_coil"):
            self.cv.itemconfig(self.lbl_coil, text="%3.0f mm" % R.coil_pos)
        if hasattr(self, "lbl_mag"):
            self.cv.itemconfig(self.lbl_mag, text="%.1f mm" % R.magnet_dist)
        if hasattr(self, "lbl_L1"):
            self.cv.itemconfig(self.lbl_L1, text="L\u2081 = %.1f mm" % R.L1)
        for k, val in (("x", R.pcb_x), ("y", R.pcb_y), ("r", R.pcb_rot)):
            it = self.vars.get("lbl_pcb" + k)
            if it:
                self.cv.itemconfig(it, text=("%.1f mm" % val) if k != "r"
                                   else ("%3.0f\u00b0" % val))
        if self.sel_term:
            self.status.set(T("단자 %s 선택됨 — 연결할 단자를 클릭하세요 (오른쪽 클릭 = 그 단자의 배선 제거)",
                              "terminal %s selected - click another terminal "
                              "(right click removes wires)") % self.sel_term)
        else:
            self.status.set(T("단자를 클릭해 리드선을 연결합니다.",
                              "Click a terminal to connect a lead."))


# ==========================================================================
#  APPLICATION
# ==========================================================================
class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.session = Session(seed)
        self.rig = Rig(self.session)
        self.title("%s   [session %d]" % (APP_TITLE, self.session.seed))
        self.geometry("1320x880")
        self.minsize(1040, 700)
        try:
            ttk.Style().theme_use("clam")
        except Exception:
            pass
        menu = tk.Menu(self)
        m = tk.Menu(menu, tearoff=0)
        m.add_command(label=T("새 세션 (숨은 값 재생성)", "New session"),
                      command=self.new_session)
        m.add_separator()
        m.add_command(label=T("종료", "Quit"), command=self.destroy)
        menu.add_cascade(label=T("파일", "File"), menu=m)
        self.config(menu=menu)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.assembly = AssemblyTab(self.nb, self)
        self.bench = BenchTab(self.nb, self)
        self.nb.add(self.assembly, text=T("  조립  ", "  Assembly  "))
        self.nb.add(self.bench, text=T("  실험대  ", "  Bench  "))
        self.after(900, self.tick)

    def new_session(self):
        self.session = Session(None)
        self.rig = Rig(self.session)
        self.assembly.rig = self.rig
        self.bench.rig = self.rig
        self.title("%s   [session %d]" % (APP_TITLE, self.session.seed))
        self.assembly.redraw()
        self.bench.rebuild()

    def tick(self):
        try:
            if self.nb.index(self.nb.select()) == 1:
                R = self.rig
                rnd = R._noise
                for i in range(3):
                    if hasattr(self.bench, "disp%d" % i):
                        txt = format_reading(R.readings[i], rnd) if R.has("dmm") else ""
                        self.bench.cv.itemconfig(
                            getattr(self.bench, "disp%d" % i), text=txt)
        except Exception:
            pass
        self.after(900, self.tick)


def main():
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
    App(seed).mainloop()


if __name__ == "__main__":
    main()
