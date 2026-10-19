#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  8th European Physics Olympiad  (EuPhO 2024, Kutaisi, Georgia)
  Experimental Problem E :  PHYSICS OF PIEZOELECTRICITY
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Apparatus rebuilt from the photographs of the problem sheet: the
    piezo element between its wooden plates, the UT33 multimeter, the AA
    battery, the capacitor with its diode, four push-button switches,
    crocodile clamps, the kitchen scales, a stopwatch, two rubber balls,
    the wooden stand with its release, the 50 cm ruler, sticks, a screw
    and a peg.  The circuit is wired terminal by terminal and solved by
    nodal analysis; the balls really bounce.
    Only what a real instrument shows is displayed: the multimeter LCD,
    the scales LCD, the stopwatch and the ruler's mm scale.  No
    capacitance, slope, exponent or contact time is ever computed.
    Every hidden true parameter is randomised for each session.

    Run:   python3 eupho2024_E1_sim_EN.py   [--seed N] [--lang ko|en]
"""
import sys, math, random, argparse

LANG = "EN"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "KO" else en


# =====================================================================
#  HIDDEN TRUTH  -  randomised once per session from the seed.
#  Nothing in here is ever shown to the user.
# =====================================================================
class Truth:
    METER_MODELS = {"UT33B+": 9.65e6, "UT33C+": 9.91e6, "UT33D+": 9.70e6}

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1, 10 ** 9)
        self.seed = int(seed)
        r = random.Random(self.seed)
        self.rng = r

        # ---- multimeter ------------------------------------------------
        self.meter_model = r.choice(list(self.METER_MODELS))
        self.R_200mV = self.METER_MODELS[self.meter_model]
        self.R_2V = 11.1e6
        self.meter_gain = 1.0 + r.gauss(0.0, 0.0020)   # systematic, |.|<0.7 %

        # ---- passive components ---------------------------------------
        self.C = 2.28e-6 * (1.0 + r.uniform(-0.022, 0.022))
        self.R_leak_C = 10 ** r.uniform(10.3, 10.9)      # film cap leakage
        self.Vf = 0.56 + r.gauss(0.0, 0.004)             # diode forward drop
        self.U_batt = r.uniform(1.380, 1.470)
        self.R_batt = r.uniform(0.6, 2.0)

        # ---- piezo element --------------------------------------------
        self.Cp = 23.5e-9 * (1.0 + r.uniform(-0.05, 0.05))
        self.beta0 = r.uniform(3.66, 3.90)               # V/N, small signal
        self.Usat = r.uniform(85.0, 95.0)                # saturation voltage
        self.r_piezo = r.uniform(0.0112, 0.0116)         # m, crystal radius
        self.R_leak_P = 10 ** r.uniform(9.2, 9.7)        # piezo self-leakage
        # small-area (stick through the hole) response: identical within 3 %
        self.stick_factor = 1.0 + r.gauss(0.0, 0.012)

        # ---- geometry --------------------------------------------------
        self.h_piezo_top = r.uniform(0.0215, 0.0228)     # m above bench
        self.h_scale_top = r.uniform(0.0335, 0.0355)     # m, scale platform
        self.ruler_zero = r.uniform(0.0048, 0.0053)      # m, scale start
        self.ruler_len = 0.500

        # ---- balls ------------------------------------------------------
        self.m1 = r.uniform(0.0075, 0.0085)              # elastic ball
        self.eta1 = r.uniform(0.795, 0.825)
        self.d1 = r.uniform(0.030, 0.034)                # diameter
        self.alpha = r.uniform(0.815, 0.865)
        Fref = r.uniform(11.3, 12.3)
        Eref = self.m1 * 9.81 * 0.334
        a = self.alpha
        self.k = (Fref / ((a + 1.0) * Eref) ** (a / (a + 1.0))) ** (a + 1.0)

        self.m2 = r.uniform(0.018, 0.023)                # inelastic ball
        self.eta2 = r.uniform(0.34, 0.44)
        self.d2 = r.uniform(0.026, 0.030)
        self.tau2 = r.uniform(0.0060, 0.0085)            # contact time, ~const

        # ---- misc -------------------------------------------------------
        self.g = 9.807
        self.scale_res = 0.001                            # kg
        self.scale_max = 10.0
        self.scale_drift = r.gauss(0.0, 0.0006)
        self.hand_tremor = r.uniform(0.006, 0.014)

    def area(self):
        return math.pi * self.r_piezo ** 2

    # charge produced by the piezo crystal under total normal force F
    def Qgen(self, F):
        if F <= 0.0:
            return 0.0
        Qs = self.Cp * self.Usat
        d = self.beta0 * self.Cp
        return Qs * math.tanh(d * F / Qs)


# =====================================================================
#  CIRCUIT  -  nodal analysis with backward-Euler companion models
# =====================================================================
TERMINALS = ["BAT+", "BAT-", "PZ+", "PZ-", "C1", "C2", "CD",
             "V+", "V-",
             "S1a", "S1b", "S2a", "S2b", "S3a", "S3b", "S4a", "S4b"]

TERM_LABEL = {
    "BAT+": ("전지 +", "battery +"), "BAT-": ("전지 -", "battery -"),
    "PZ+": ("압전 리드(빨강)", "piezo lead (red)"),
    "PZ-": ("압전 리드(검정)", "piezo lead (black)"),
    "C1": ("축전기 다리 1", "capacitor leg 1"),
    "C2": ("축전기 다리 2", "capacitor leg 2"),
    "CD": ("다이오드 끝", "diode end"),
    "V+": ("멀티미터 VΩmA", "multimeter VΩmA"),
    "V-": ("멀티미터 COM", "multimeter COM"),
}
for _i in (1, 2, 3, 4):
    TERM_LABEL["S%da" % _i] = ("스위치 %d 좌" % _i, "switch %d L" % _i)
    TERM_LABEL["S%db" % _i] = ("스위치 %d 우" % _i, "switch %d R" % _i)

METER_RANGES = {
    "200mV": (0.19999, 1e-4, "%6.1f", 1e3, "mV"),
    "2V":    (1.9999, 1e-3, "%6.3f", 1.0, "V"),
    "20V":   (19.999, 1e-2, "%6.2f", 1.0, "V"),
    "200V":  (199.99, 1e-1, "%6.1f", 1.0, "V"),
    "600V":  (599.9, 1.0,  "%6.0f", 1.0, "V"),
}
DIAL_ORDER = ["OFF", "200mV", "2V", "20V", "200V", "600V", "OHM", "A"]


class Circuit:
    """Terminals are merged by wires and by closed push-button switches.
    Elements are stamped as Norton equivalents so a plain nodal solve works."""

    R_ON = 8.0          # diode on-resistance
    R_OFF = 2.0e11      # diode reverse resistance
    G_FLOAT = 1.0e-14   # keeps the matrix regular for floating nets

    def __init__(self, truth):
        self.tr = truth
        self.wires = []                       # list of (t1, t2)
        self.sw = [False, False, False, False]
        self.dial = "OFF"
        self.vC = 0.0                         # V(C1) - V(C2)
        self.vP = 0.0                         # V(PZ+) - V(PZ-)
        self.diode_on = False
        self.meter_v = 0.0
        self.blown = False                    # multimeter short-circuited
        self._nodes = None
        self._dirty = True

    # ---------------- topology -------------------------------------
    def add_wire(self, a, b):
        if a == b:
            return False
        for w in self.wires:
            if set(w) == {a, b}:
                return False
        self.wires.append((a, b))
        self._dirty = True
        return True

    def remove_wire(self, idx):
        if 0 <= idx < len(self.wires):
            self.wires.pop(idx)
            self._dirty = True

    def clear_wires(self):
        self.wires = []
        self._dirty = True

    def set_switch(self, i, down):
        if self.sw[i] != down:
            self.sw[i] = down
            self._dirty = True

    def set_dial(self, d):
        if d in DIAL_ORDER and d != self.dial:
            self.dial = d
            self._dirty = True

    def _build_nodes(self):
        parent = {t: t for t in TERMINALS}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for a, b in self.wires:
            union(a, b)
        for i in range(4):
            if self.sw[i]:
                union("S%da" % (i + 1), "S%db" % (i + 1))
        roots = {}
        node = {}
        for t in TERMINALS:
            r = find(t)
            if r not in roots:
                roots[r] = len(roots)
            node[t] = roots[r]
        self._nodes = node
        self._nnode = len(roots)
        self._dirty = False

    def n(self, t):
        if self._dirty:
            self._build_nodes()
        return self._nodes[t]

    # ---------------- solve ----------------------------------------
    def meter_R(self):
        if self.dial == "200mV":
            return self.tr.R_200mV
        if self.dial in ("2V", "20V", "200V", "600V"):
            return self.tr.R_2V
        return None      # OFF / OHM / A -> no defined DC voltmeter loading

    def _solve(self, dt, Igen):
        tr = self.tr
        if self._dirty:
            self._build_nodes()
        N = self._nnode
        G = [[0.0] * N for _ in range(N)]
        I = [0.0] * N

        def stampG(a, b, g):
            G[a][a] += g
            G[b][b] += g
            G[a][b] -= g
            G[b][a] -= g

        def stampI(a, b, cur):        # current source a -> b (into b)
            I[a] -= cur
            I[b] += cur

        for i in range(N):
            G[i][i] += self.G_FLOAT

        nC1, nC2, nCD = self.n("C1"), self.n("C2"), self.n("CD")
        nP, nM = self.n("PZ+"), self.n("PZ-")
        nBp, nBn = self.n("BAT+"), self.n("BAT-")
        nVp, nVm = self.n("V+"), self.n("V-")

        # capacitor C (backward Euler companion)
        gC = tr.C / dt
        stampG(nC1, nC2, gC)
        I[nC1] += gC * self.vC
        I[nC2] -= gC * self.vC
        stampG(nC1, nC2, 1.0 / tr.R_leak_C)

        # piezo: Cp + leakage + charge generator
        gP = tr.Cp / dt
        stampG(nP, nM, gP)
        I[nP] += gP * self.vP
        I[nM] -= gP * self.vP
        stampG(nP, nM, 1.0 / tr.R_leak_P)
        I[nP] += Igen
        I[nM] -= Igen

        # battery (Thevenin -> Norton)
        gB = 1.0 / tr.R_batt
        stampG(nBp, nBn, gB)
        I[nBp] += tr.U_batt * gB
        I[nBn] -= tr.U_batt * gB

        # voltmeter
        Rm = self.meter_R()
        if Rm:
            stampG(nVp, nVm, 1.0 / Rm)
        elif self.dial in ("OHM", "A"):
            stampG(nVp, nVm, 1.0 / 0.5)      # low impedance -> shorts things

        # diode: anode CD, cathode C1  (charge flows into the capacitor)
        gD = 1.0 / (self.R_ON if self.diode_on else self.R_OFF)
        stampG(nCD, nC1, gD)
        if self.diode_on:
            I[nCD] -= tr.Vf * gD
            I[nC1] += tr.Vf * gD

        v = gauss_solve(G, I, N)
        return v, nC1, nC2, nCD, nP, nM, nVp, nVm

    def step(self, dt, Igen=0.0):
        if dt <= 0:
            return
        for _ in range(12):
            v, nC1, nC2, nCD, nP, nM, nVp, nVm = self._solve(dt, Igen)
            vd = v[nCD] - v[nC1]
            if self.diode_on:
                cur = (vd - self.tr.Vf) / self.R_ON
                if cur < -1e-12:
                    self.diode_on = False
                    continue
            else:
                if vd > self.tr.Vf:
                    self.diode_on = True
                    continue
            break
        self.vC = v[nC1] - v[nC2]
        self.vP = v[nP] - v[nM]
        self.meter_v = v[nVp] - v[nVm]
        if self.dial in ("OHM", "A"):
            # shorting a charged capacitor through the meter is harmless here
            pass

    # ---------------- display ---------------------------------------
    def display(self):
        """Exactly what the multimeter LCD shows."""
        d = self.dial
        if d == "OFF":
            return ""
        if d == "OHM":
            return T("--- (저항 측정)", "--- (ohm)")
        if d == "A":
            return T("--- (전류 측정)", "--- (amp)")
        vmax, res, fmt, mul, unit = METER_RANGES[d]
        val = self.meter_v * self.tr.meter_gain
        val += self.tr.rng.gauss(0.0, 1.1 * res)      # +-1 count of noise
        if abs(val) > vmax:
            return "OL"
        q = round(val * mul / (res * mul)) * res * mul
        return (fmt % q).strip()


def gauss_solve(A, b, n):
    M = [A[i][:] + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-30:
            M[c][c] += 1e-18
            p = c
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


# =====================================================================
#  PARTS / ASSEMBLY
# =====================================================================
PARTS = [
    ("A",  "압전 소자",            "Piezo element",        ("desk", "scale")),
    ("B",  "멀티미터",             "Multimeter",           ("tray",)),
    ("C",  "1.5 V AA 건전지",      "1.5 V AA battery",     ("tray",)),
    ("D",  "축전기(다이오드 부착)", "Capacitor with diode", ("tray",)),
    ("E",  "누름 버튼 스위치 4개",  "4 push-button switches", ("tray",)),
    ("G",  "디지털 저울",           "Digital scales",       ("desk",)),
    ("H",  "디지털 스톱워치",       "Digital stopwatch",    ("tray",)),
    ("I1", "고무공 1 (파랑, 큰 것)", "Rubber ball 1 (blue)", ("release", "tray")),
    ("I2", "고무공 2 (검정)",       "Rubber ball 2 (black)", ("release", "tray")),
    ("J",  "나무 스탠드 + 낙하 장치", "Wooden stand + release", ("desk",)),
    ("K",  "50 cm 자",             "50 cm ruler",          ("stand", "tray")),
    ("L1", "나무 막대 (짧은 것)",    "Wooden stick (short)", ("hole", "tray")),
    ("L2", "나무 막대 (긴 것)",      "Wooden stick (long)",  ("hole", "tray")),
    ("M",  "큰 금속 나사",          "Large metal screw",    ("tray",)),
    ("N",  "나무 빨래집게",         "Wooden peg",           ("stand",)),
    ("O",  "연필 / 펜",            "Pencil / pen",         ("tray",)),
]
PART_NAME = {p[0]: (p[1], p[2]) for p in PARTS}
SLOT_NAME = {
    "desk":    ("책상 위", "on the desk"),
    "scale":   ("저울 위", "on the scales"),
    "release": ("낙하 장치", "in the release mechanism"),
    "stand":   ("스탠드 날개", "on the stand wing"),
    "hole":    ("덮개판 구멍", "in the cover-plate hole"),
    "tray":    ("작업대", "on the work top"),
}


class Rig:
    """The whole apparatus.  Everything the virtual student can touch."""

    def __init__(self, seed=None):
        self.tr = Truth(seed)
        self.cir = Circuit(self.tr)
        self.t = 0.0
        self.placed = {}                    # part id -> slot
        # mechanics -------------------------------------------------
        self.press_target = 0.0             # N the student intends
        self.press_now = 0.0
        self.press_via_stick = False
        self.release_h = 0.200              # m, ball bottom height
        self.release_over = "desk"          # "desk" | "piezo"
        self.ball = None                    # flying ball dict
        self.apex_mm = []                   # ruler readings of successive apices
        self.bounces = 0
        self.settled = True
        self._apex_y = 0.0
        self._last_v = 0.0
        # instruments -----------------------------------------------
        self.sw_disp = 0.0
        self.sw_run = False
        self.scale_filt = 0.0
        self.scale_tare = 0.0
        self.log = []

    # ---------------- assembly ---------------------------------------
    def slot_of(self, pid):
        return self.placed.get(pid)

    def place(self, pid, slot):
        if pid not in PART_NAME:
            return False, T("그런 부품이 없습니다.", "No such part.")
        allowed = [p[3] for p in PARTS if p[0] == pid][0]
        if slot not in allowed:
            return False, T("%s은(는) %s에 놓을 수 없습니다." % (PART_NAME[pid][0], SLOT_NAME[slot][0]),
                            "%s cannot go %s." % (PART_NAME[pid][1], SLOT_NAME[slot][1]))
        # prerequisites
        if slot == "scale" and self.placed.get("G") != "desk":
            return False, T("먼저 디지털 저울을 책상에 놓으십시오.",
                            "Put the digital scales on the desk first.")
        if slot == "release" and self.placed.get("J") != "desk":
            return False, T("먼저 나무 스탠드를 책상에 놓으십시오.",
                            "Put the wooden stand on the desk first.")
        if slot == "release":
            for other in ("I1", "I2"):
                if other != pid and self.placed.get(other) == "release":
                    return False, T("낙하 장치에는 공을 하나만 걸 수 있습니다.",
                                    "The release mechanism holds only one ball.")
        if slot == "stand" and self.placed.get("J") != "desk":
            return False, T("먼저 나무 스탠드를 책상에 놓으십시오.",
                            "Put the wooden stand on the desk first.")
        if pid == "K" and slot == "stand" and self.placed.get("N") != "stand":
            return False, T("자를 고정하려면 빨래집게가 스탠드에 있어야 합니다.",
                            "The peg must be on the stand to hold the ruler.")
        if slot == "hole" and self.placed.get("A") not in ("desk", "scale"):
            return False, T("먼저 압전 소자를 놓으십시오.",
                            "Place the piezo element first.")
        if slot == "hole":
            for other in ("L1", "L2"):
                if other != pid and self.placed.get(other) == "hole":
                    return False, T("구멍에는 막대를 하나만 넣을 수 있습니다.",
                                    "Only one stick fits in the hole.")
        # dependants that must be cleared first
        if pid == "G" and self.placed.get("A") == "scale":
            return False, T("압전 소자가 저울 위에 있습니다.", "The piezo is on the scales.")
        self.placed[pid] = slot
        return True, T("%s → %s" % (PART_NAME[pid][0], SLOT_NAME[slot][0]),
                       "%s -> %s" % (PART_NAME[pid][1], SLOT_NAME[slot][1]))

    def remove(self, pid):
        for t in PART_TERMS.get(pid, ()):
            self.cir.wires = [w for w in self.cir.wires if t not in w]
        self.cir._dirty = True
        if pid == "J":
            for d in ("I1", "I2", "K", "N"):
                if self.placed.get(d) in ("release", "stand"):
                    self.placed.pop(d, None)
        if pid == "G" and self.placed.get("A") == "scale":
            self.placed["A"] = "desk"
        if pid == "A":
            for d in ("L1", "L2"):
                if self.placed.get(d) == "hole":
                    self.placed.pop(d, None)
        if pid == "N" and self.placed.get("K") == "stand":
            self.placed.pop("K", None)
        if self.placed.get(pid) == "release":
            self.ball = None
        self.placed.pop(pid, None)

    def piezo_placed(self):
        return self.placed.get("A") in ("desk", "scale")

    def piezo_top_y(self):
        s = self.placed.get("A")
        if s == "scale":
            return self.tr.h_scale_top + self.tr.h_piezo_top
        if s == "desk":
            return self.tr.h_piezo_top
        return None

    def stick_in_hole(self):
        return self.placed.get("L1") == "hole" or self.placed.get("L2") == "hole"

    def loaded_ball(self):
        for b in ("I1", "I2"):
            if self.placed.get(b) == "release":
                return b
        return None

    # ---------------- ruler ------------------------------------------
    def ruler_ready(self):
        return self.placed.get("K") == "stand"

    def _read(self, y, sigma):
        """Read the printed mm scale of the 50 cm ruler at height y (m)."""
        if not self.ruler_ready():
            return None
        if y < self.tr.ruler_zero or y > self.tr.ruler_zero + self.tr.ruler_len:
            return None
        mm = (y - self.tr.ruler_zero) * 1000.0
        return float(round(mm + self.tr.rng.gauss(0.0, sigma)))

    def read_hanging_ball(self):
        """Ruler reading at the lowest point of the ball held by the release."""
        if self.loaded_ball() is None:
            return None
        return self._read(self.release_h, 0.7)

    def read_object(self, what):
        """Ruler reading of a fixed feature; what in {'piezo_top','desk','scale_top'}."""
        y = {"desk": 0.0, "scale_top": self.tr.h_scale_top,
             "piezo_top": self.piezo_top_y() or 0.0}.get(what)
        if y is None:
            return None
        return self._read(max(y, self.tr.ruler_zero + 1e-6), 0.7)

    # ---------------- scales -----------------------------------------
    def scale_force(self):
        if self.placed.get("G") != "desk":
            return None
        f = 0.0
        if self.placed.get("A") == "scale":
            f += 0.085 * self.tr.g          # piezo assembly weight
            f += self.press_now
            if self.ball is not None and self.ball.get("contactF"):
                f += self.ball["contactF"]
        return f

    def scale_display(self):
        if self.placed.get("G") != "desk":
            return None
        m = self.scale_filt / self.tr.g - self.scale_tare + self.tr.scale_drift
        if m > self.tr.scale_max:
            return "-----"
        q = round(m / self.tr.scale_res) * self.tr.scale_res
        if abs(q) < 1e-9:
            q = 0.0
        return "%.3f" % q

    def tare(self):
        if self.placed.get("G") == "desk":
            self.scale_tare = self.scale_filt / self.tr.g

    # ---------------- stopwatch --------------------------------------
    def sw_start_stop(self):
        self.sw_run = not self.sw_run

    def sw_reset(self):
        if not self.sw_run:
            self.sw_disp = 0.0

    def sw_display(self):
        if self.placed.get("H") != "tray":
            return None
        cs = int(self.sw_disp * 100.0)
        return "%02d:%02d.%02d" % (cs // 6000, (cs // 100) % 60, cs % 100)

    # ---------------- pressing ----------------------------------------
    def set_press(self, newtons):
        self.press_target = max(0.0, min(120.0, newtons))

    def press_ok(self):
        """Can the student press at all?"""
        return self.piezo_placed()

    # ---------------- ball --------------------------------------------
    def set_release_height(self, y):
        self.release_h = max(0.040, min(0.430, y))

    def drop(self):
        b = self.loaded_ball()
        if b is None:
            return False, T("낙하 장치에 공이 없습니다.", "No ball in the release mechanism.")
        if self.ball is not None:
            return False, T("공이 아직 튀고 있습니다.", "The ball is still bouncing.")
        surf = 0.0
        if self.release_over == "piezo":
            if not self.piezo_placed():
                return False, T("압전 소자가 놓여 있지 않습니다.", "The piezo element is not placed.")
            surf = self.piezo_top_y()
        if self.release_h <= surf + 0.002:
            return False, T("낙하 높이가 너무 낮습니다.", "Release height too low.")
        self.ball = dict(which=b, y=self.release_h, v=0.0, surf=surf,
                         contactF=0.0, nb=0)
        self.apex_mm = []
        self.bounces = 0
        self.settled = False
        self._apex_y = self.release_h
        return True, ""

    def ball_y(self):
        return None if self.ball is None else self.ball["y"]

    # ---------------- impact ------------------------------------------
    def _impact(self, vin):
        """Run the contact.  Returns (v_out, duration).  Drives the circuit."""
        tr = self.tr
        b = self.ball["which"]
        on_piezo = (self.ball["surf"] > 1e-9) and self.piezo_placed()
        if b == "I1":
            m, eta, k, a = tr.m1, tr.eta1, tr.k, tr.alpha
            E = 0.5 * m * vin * vin
            xm = ((a + 1.0) * E / k) ** (1.0 / (a + 1.0))
            dt = max(1e-6, xm / abs(vin) / 220.0)
            x, v, tt = 0.0, abs(vin), 0.0
            phase = 0
            Fmax = 0.0
            hist = []
            for _ in range(20000):
                F = k * (x ** a) if x > 0 else 0.0
                if phase == 1:
                    F *= eta
                Fmax = max(Fmax, F)
                v -= (F / m) * dt
                x += v * dt
                tt += dt
                hist.append((tt, F))
                if phase == 0 and v <= 0.0:
                    phase = 1
                if phase == 1 and x <= 0.0:
                    break
            vout = abs(v)
        else:
            m, eta, tau = tr.m2, tr.eta2, tr.tau2
            tau = tau * (1.0 + tr.rng.gauss(0.0, 0.02))
            vout = math.sqrt(max(eta * (1.0 + tr.rng.gauss(0.0, 0.03)), 0.0)) * abs(vin)
            dp = m * (abs(vin) + vout)
            Fmax = math.pi * dp / (2.0 * tau)
            n = 400
            dt = tau / n
            hist = [((i + 1) * dt, Fmax * math.sin(math.pi * (i + 1) * dt / tau))
                    for i in range(n)]
        # drive the electrical model
        if on_piezo:
            gain = self._piezo_gain()
            Qprev = tr.Qgen(self.press_now) * gain
            tprev = 0.0
            for (tt, F) in hist:
                d = tt - tprev
                if d <= 0:
                    continue
                Q = tr.Qgen(self.press_now + F) * gain
                self.cir.step(d, (Q - Qprev) / d)
                Qprev, tprev = Q, tt
            Q = tr.Qgen(self.press_now) * gain
            self.cir.step(1e-4, (Q - Qprev) / 1e-4)
            self.ball["contactF"] = 0.0
        dur = hist[-1][0] if hist else 1e-3
        if b == "I1":
            vout *= (1.0 + tr.rng.gauss(0.0, 0.010))
        return vout, dur, Fmax

    # ---------------- main integrator ---------------------------------
    def advance(self, dt):
        tr = self.tr
        if dt <= 1e-12:
            return
        n = max(1, int(math.ceil(dt / 0.02)))
        h = dt / n
        for _ in range(n):
            self.t += h
            if self.sw_run:
                self.sw_disp += h
            # hand pressing: tremor + slow drift
            if self.press_ok():
                tgt = self.press_target
                if tgt > 0:
                    tgt *= (1.0 + tr.rng.gauss(0.0, tr.hand_tremor * 0.35))
                self.press_now += (tgt - self.press_now) * min(1.0, h / 0.08)
            else:
                self.press_now = 0.0
            # ball
            if self.ball is not None:
                self._step_ball(h)
            # scales low-pass
            f = self.scale_force()
            if f is not None:
                self.scale_filt += (f - self.scale_filt) * min(1.0, h / 0.25)
            # circuit
            Q0 = tr.Qgen(self._piezo_force_static()) * self._piezo_gain()
            self.cir.step(h, (Q0 - self._Qprev()) / h)
            self._Qset(Q0)

    _Q_last = 0.0

    def _Qprev(self):
        return self._Q_last

    def _Qset(self, q):
        self._Q_last = q

    def _piezo_force_static(self):
        if not self.piezo_placed():
            return 0.0
        return self.press_now

    def _piezo_gain(self):
        """Pressing through the hole with a stick loads a much smaller area,
        but the stiff cover plate spreads the stress over the whole crystal."""
        return self.tr.stick_factor if self.stick_in_hole() else 1.0

    def _step_ball(self, h):
        """Exact ballistic flight with event detection at the impact surface."""
        tr = self.tr
        g = tr.g
        b = self.ball
        t_rem = h
        guard = 0
        while t_rem > 1e-12 and self.ball is not None:
            guard += 1
            if guard > 40:
                break
            y, v, surf = b["y"], b["v"], b["surf"]
            disc = v * v + 2.0 * g * (y - surf)
            t_hit = None
            if disc >= 0.0:
                th = (v + math.sqrt(disc)) / g
                if th > 1e-12:
                    t_hit = th
            if t_hit is not None and t_hit <= t_rem:
                self._track_apex(y, v, t_hit)
                b["y"] = surf
                b["v"] = v - g * t_hit
                t_rem -= t_hit
                vout, dur, Fm = self._impact(b["v"])
                b["nb"] += 1
                self.bounces += 1
                b["v"] = vout
                self._apex_y = surf
                t_rem = max(0.0, t_rem - dur)
                if vout < 0.30:
                    self.ball = None
                    self.settled = True
                    return
            else:
                self._track_apex(y, v, t_rem)
                b["y"] = y + v * t_rem - 0.5 * g * t_rem * t_rem
                b["v"] = v - g * t_rem
                t_rem = 0.0
        if self.ball is not None and b["y"] > 0.62:
            b["y"] = 0.62
            b["v"] = min(b["v"], 0.0)

    def _track_apex(self, y, v, dt):
        """Follow the highest point reached inside [0, dt] and read the ruler
        the moment the ball has visibly turned over."""
        b = self.ball
        top = max(y, y + v * dt - 0.5 * self.tr.g * dt * dt)
        turned = False
        if v > 0.0:
            t_ap = v / self.tr.g
            if t_ap <= dt:
                top = max(top, y + 0.5 * v * v / self.tr.g)
                turned = True
        elif v <= 0.0:
            turned = True
        if top > self._apex_y:
            self._apex_y = top
        if turned and b["nb"] > 0 and len(self.apex_mm) < b["nb"] \
                and self._apex_y > b["surf"] + 1e-4:
            self.apex_mm.append(self._read(self._apex_y, 1.8))


# =====================================================================
#  GRAPHICAL USER INTERFACE
# =====================================================================
import tkinter as tk
from tkinter import ttk

PPM = 900.0          # pixels per metre in the bench view
DESK_Y = 590.0       # world y of the desk surface
WORLD_W, WORLD_H = 1210, 690

C_BG = "#e9ece7"
C_DESK = "#b58b57"
C_DESK_DK = "#7d5f39"
C_WOOD = "#dcb87c"
C_WOOD_DK = "#a8823f"
C_WOOD_LT = "#efd8a9"
C_METAL = "#b9bec4"
C_METAL_DK = "#7c848c"
C_RED = "#c22a22"
C_RED_DK = "#7e1a15"
C_LCD = "#c3d2ae"
C_LCD_DK = "#22301c"
C_BLACK = "#2b2b2b"
C_WIRE = "#2f4f7f"
C_TERM = "#e0a800"
C_BALL1 = "#3f6fbf"
C_BALL2 = "#3a3a3a"


def rrect(cv, x0, y0, x1, y1, r, **kw):
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


# ---------------------------------------------------------------- assembly
ASM_SLOTS = [
    ("desk",    330,  62,  700, 252),
    ("scale",   715,  62,  952, 162),
    ("stand",   966,  62, 1132, 252),
    ("release", 715, 176,  952, 252),
    ("hole",    330, 266,  700, 352),
    ("tray",    330, 366, 1132, 640),
]
SLOT_HINT = {
    "desk": ("저울 · 스탠드 · 압전 소자", "scales, stand, piezo"),
    "scale": ("저울을 먼저 놓을 것", "scales first"),
    "stand": ("빨래집게→자", "peg, ruler"),
    "release": ("공 1개", "one ball"),
    "hole": ("나무 막대", "wooden stick"),
    "tray": ("나머지 장비", "the rest of the kit"),
}


class AssemblyTab(ttk.Frame):
    CW, CH = 1150, 662
    CARD_W, CARD_H = 132, 44

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.rig = app.rig
        top = ttk.Frame(self)
        top.pack(fill="x")
        self.msg = ttk.Label(top, text=T(
            "부품을 끌어다 자리에 놓으십시오.  오른쪽 클릭 = 부품 상자로 되돌림.",
            "Drag a part onto a slot.  Right-click returns it to the parts box."))
        self.msg.pack(side="left", padx=8, pady=4)
        self.cv = tk.Canvas(self, width=self.CW, height=self.CH, bg=C_BG,
                            highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.drag = None
        self.cards = {}
        self.cv.bind("<Button-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_move)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Button-3>", self.on_right)
        self.redraw()

    # ------------------------------------------------------------
    def layout(self):
        self.cards = {}
        free = [p[0] for p in PARTS if p[0] not in self.rig.placed]
        for i, pid in enumerate(free):
            x = 82 + (i % 2) * 146
            y = 78 + (i // 2) * 52
            self.cards[pid] = (x, y, None)
        cnt = {}
        for name, x0, y0, x1, y1 in ASM_SLOTS:
            cols = max(1, int((x1 - x0 - 12) // (self.CARD_W + 8)))
            k = 0
            for pid in [p[0] for p in PARTS]:
                if self.rig.placed.get(pid) != name:
                    continue
                x = x0 + 12 + (k % cols) * (self.CARD_W + 8) + self.CARD_W / 2
                y = y0 + 34 + (k // cols) * (self.CARD_H + 6) + self.CARD_H / 2
                self.cards[pid] = (x, y, name)
                k += 1

    def redraw(self):
        cv = self.cv
        cv.delete("all")
        rrect(cv, 10, 40, 300, 650, 10, fill="#dfe4dc", outline="#9aa596")
        cv.create_text(155, 24, text=T("부품 상자 (장비 A–O)", "Parts box (kit A-O)"),
                       font=("TkDefaultFont", 11, "bold"), fill="#3f4a37")
        rrect(cv, 315, 40, 1140, 650, 10, fill="#f4f6f2", outline="#9aa596")
        for name, x0, y0, x1, y1 in ASM_SLOTS:
            cv.create_rectangle(x0, y0, x1, y1, dash=(5, 4), outline="#8fa07f",
                                fill="#e9efe3")
            cv.create_text(x0 + 10, y0 + 14, anchor="w",
                           text="%s   %s" % (T(*SLOT_NAME[name]), T(*SLOT_HINT[name])),
                           font=("TkDefaultFont", 9, "bold"), fill="#4a5a3f")
        self.layout()
        for pid, (x, y, slot) in self.cards.items():
            self.draw_card(pid, x, y)
        if self.drag:
            pid, x, y = self.drag
            self.draw_card(pid, x, y, ghost=True)

    def draw_card(self, pid, x, y, ghost=False):
        cv = self.cv
        w, h = self.CARD_W, self.CARD_H
        rrect(cv, x - w / 2, y - h / 2, x + w / 2, y + h / 2, 7,
              fill=("#fff3c4" if ghost else "#ffffff"), outline="#6b7a5f")
        cv.create_text(x - w / 2 + 13, y, text=pid,
                       font=("TkDefaultFont", 10, "bold"), fill=C_RED_DK)
        cv.create_text(x - w / 2 + 26, y, anchor="w", text=T(*PART_NAME[pid]),
                       font=("TkDefaultFont", 8), width=w - 32)

    def hit(self, ex, ey):
        for pid, (x, y, slot) in self.cards.items():
            if abs(ex - x) < self.CARD_W / 2 and abs(ey - y) < self.CARD_H / 2:
                return pid
        return None

    # ------------------------------------------------------------
    def on_press(self, e):
        pid = self.hit(e.x, e.y)
        if pid:
            if pid in self.rig.placed:
                self.rig.remove(pid)
            self.drag = (pid, e.x, e.y)
            self.redraw()

    def on_move(self, e):
        if self.drag:
            self.drag = (self.drag[0], e.x, e.y)
            self.redraw()

    def on_release(self, e):
        if not self.drag:
            return
        pid = self.drag[0]
        self.drag = None
        target = None
        for name, x0, y0, x1, y1 in ASM_SLOTS:
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                target = name
        if target:
            ok, m = self.rig.place(pid, target)
            self.msg.config(text=m)
        else:
            self.msg.config(text=T("%s → 부품 상자", "%s -> parts box")
                            % T(*PART_NAME[pid]))
        self.redraw()
        self.app.bench.mark()

    def on_right(self, e):
        pid = self.hit(e.x, e.y)
        if pid and pid in self.rig.placed:
            self.rig.remove(pid)
            self.msg.config(text=T("%s을(를) 부품 상자로 되돌렸습니다.",
                                   "%s returned to the parts box.")
                            % T(*PART_NAME[pid]))
            self.redraw()
            self.app.bench.mark()


PART_TERMS = {
    "C": ("BAT+", "BAT-"), "D": ("C1", "C2", "CD"), "B": ("V+", "V-"),
    "E": ("S1a", "S1b", "S2a", "S2b", "S3a", "S3b", "S4a", "S4b"),
    "A": ("PZ+", "PZ-"),
}


class BenchTab(ttk.Frame):
    CW, CH = 1160, 640

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.rig = app.rig
        self.sc = 0.94
        self.ox, self.oy = 4.0, 4.0
        self.x_stand = 305.0
        self.term = {}
        self.pending = None          # first terminal of a wire being made
        self.trail = []
        self.static_dirty = True
        self.pan = None
        self.dragging_stand = False

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=2)
        ttk.Button(bar, text=T("공 놓기", "Release ball"), command=self.do_drop).pack(side="left", padx=3)
        ttk.Button(bar, text=T("손 떼기", "Hands off"), command=self.hands_off).pack(side="left", padx=3)
        ttk.Button(bar, text=T("저울 0점", "Tare"), command=self.do_tare).pack(side="left", padx=3)
        ttk.Button(bar, text=T("스톱워치 ▶/■", "Stopwatch"), command=self.rig.sw_start_stop).pack(side="left", padx=3)
        ttk.Button(bar, text=T("스톱워치 0", "Reset"), command=self.rig.sw_reset).pack(side="left", padx=3)
        ttk.Button(bar, text=T("배선 모두 제거", "Clear wiring"), command=self.clear_wires).pack(side="left", padx=8)
        ttk.Label(bar, text=T("  시간 배속:", "  time rate:")).pack(side="left")
        self.spd = tk.StringVar(value="1x")
        cb = ttk.Combobox(bar, textvariable=self.spd, width=6, state="readonly",
                          values=("0.1x", "0.25x", "1x", "2x", "5x"))
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.app.set_speed(self.spd.get()))
        self.hint = ttk.Label(bar, text="")
        self.hint.pack(side="left", padx=10)

        self.cv = tk.Canvas(self, width=self.CW, height=self.CH, bg=C_BG,
                            highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Button-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_drag)
        self.cv.bind("<ButtonRelease-1>", self.on_up)
        self.cv.bind("<Button-3>", self.on_right)
        self.cv.bind("<MouseWheel>", self.on_wheel)
        self.cv.bind("<Button-4>", lambda e: self.on_wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self.on_wheel(e, -1))

    # ------------------------------------------------- transforms
    def w2s(self, x, y):
        return x * self.sc + self.ox, y * self.sc + self.oy

    def s2w(self, x, y):
        return (x - self.ox) / self.sc, (y - self.oy) / self.sc

    def mark(self):
        self.static_dirty = True

    # ------------------------------------------------- geometry
    def geom(self):
        tr = self.rig.tr
        g = {}
        g["scale_top"] = DESK_Y - tr.h_scale_top * PPM
        slot = self.rig.placed.get("A")
        g["pz_slot"] = slot
        g["cx_piezo"] = 155.0 if slot == "scale" else 66.0
        base = g["scale_top"] if slot == "scale" else DESK_Y
        g["pz_base"] = base
        g["pz_top"] = base - tr.h_piezo_top * PPM
        g["nozzle"] = self.x_stand - 150.0
        g["ruler_x"] = g["nozzle"] + 62.0
        return g

    # ------------------------------------------------- actions
    def do_drop(self):
        ok, m = self.rig.drop()
        self.trail = []
        self.hint.config(text=m)

    def hands_off(self):
        self.rig.set_press(0.0)

    def do_tare(self):
        self.rig.tare()

    def clear_wires(self):
        self.rig.cir.clear_wires()
        self.pending = None
        self.mark()

    # ------------------------------------------------- drawing
    def redraw(self):
        cv = self.cv
        if self.static_dirty:
            cv.delete("all")
            self.draw_static()
            self.static_dirty = False
        cv.delete("dyn")
        self.draw_dynamic()

    def L(self, x0, y0, x1, y1, **kw):
        a = self.w2s(x0, y0); b = self.w2s(x1, y1)
        return self.cv.create_line(a[0], a[1], b[0], b[1], **kw)

    def R(self, x0, y0, x1, y1, **kw):
        a = self.w2s(x0, y0); b = self.w2s(x1, y1)
        return self.cv.create_rectangle(a[0], a[1], b[0], b[1], **kw)

    def O(self, x0, y0, x1, y1, **kw):
        a = self.w2s(x0, y0); b = self.w2s(x1, y1)
        return self.cv.create_oval(a[0], a[1], b[0], b[1], **kw)

    def TX(self, x, y, text, **kw):
        a = self.w2s(x, y)
        return self.cv.create_text(a[0], a[1], text=text, **kw)

    def RR(self, x0, y0, x1, y1, r, **kw):
        a = self.w2s(x0, y0); b = self.w2s(x1, y1)
        return rrect(self.cv, a[0], a[1], b[0], b[1], r * self.sc, **kw)

    def fnt(self, size, bold=False, mono=False):
        f = "Courier" if mono else "TkDefaultFont"
        return (f, max(6, int(size * self.sc)), "bold" if bold else "normal")

    # ---------------------------------------------------------- static
    def draw_static(self):
        rig = self.rig
        self.update_target()
        g = self.geom()
        self.term = {}
        # desk
        self.R(-20, DESK_Y, 560, DESK_Y + 120, fill=C_DESK, outline="")
        self.L(-20, DESK_Y, 560, DESK_Y, fill=C_DESK_DK, width=3)
        self.R(560, -40, 1240, DESK_Y + 120, fill="#dfe2db", outline="")
        self.L(560, -40, 560, DESK_Y + 120, fill="#b0b6ab", width=2)
        self.TX(900, 22, text=T("전기 부품", "electrical components"),
                fill="#818a7e", font=self.fnt(11, True))
        if rig.placed.get("J") == "desk":
            self.draw_stand(g)
        if rig.placed.get("K") == "stand":
            self.draw_ruler(g)
        if rig.placed.get("G") == "desk":
            self.draw_scales(g)
        if g["pz_slot"]:
            self.draw_piezo(g)
        if rig.placed.get("B") == "tray":
            self.draw_meter()
        if rig.placed.get("C") == "tray":
            self.draw_battery()
        if rig.placed.get("D") == "tray":
            self.draw_capacitor()
        if rig.placed.get("E") == "tray":
            self.draw_switches()
        if rig.placed.get("H") == "tray":
            self.draw_stopwatch()
        if rig.placed.get("M") == "tray":
            self.draw_screw()
        self.draw_wires()
        for name, (x, y) in self.term.items():
            col = C_TERM if self.pending != name else "#ff5522"
            self.O(x - 5, y - 5, x + 5, y + 5, fill=col, outline="#6b5200")

    # -- scales ------------------------------------------------------
    def draw_scales(self, g):
        top = g["scale_top"]
        self.O(52, top - 7, 262, top + 13, fill="#f5f5f2", outline="#b4b4ad")
        self.RR(52, top, 262, DESK_Y, 7, fill="#e7e7e2", outline="#a9a9a2")
        self.O(52, DESK_Y - 11, 262, DESK_Y + 7, fill="#d9d9d4", outline="#a9a9a2")
        self.RR(180, DESK_Y - 27, 260, DESK_Y - 5, 3, fill=C_LCD, outline="#8d9a7e")
        self.TX(62, DESK_Y - 16, anchor="w", text="MAX 10 kg", font=self.fnt(7),
                fill="#8a8a84")

    # -- piezo -------------------------------------------------------
    def draw_piezo(self, g):
        cx = g["cx_piezo"]
        b = g["pz_base"]
        t = g["pz_top"]
        h = b - t
        self.RR(cx - 48, b - h * 0.42, cx + 48, b, 3, fill=C_WOOD, outline=C_WOOD_DK)
        self.R(cx - 34, t + h * 0.40, cx + 34, b - h * 0.40, fill="#8d8f92", outline="#5f6164")
        self.RR(cx - 44, t, cx + 44, t + h * 0.44, 3, fill=C_WOOD_LT, outline=C_WOOD_DK)
        self.O(cx - 7, t - 1, cx + 7, t + h * 0.44 + 1, fill="#9aa0a6", outline="#5f6164")
        # leads run down onto the desk and away to the right
        a = self.w2s
        for col, yoff, tx, ty in ((C_RED, 0.20, 452, DESK_Y - 26),
                                  (C_BLACK, 0.34, 452, DESK_Y - 8)):
            p = [a(cx + 44, t + h * yoff), a(cx + 96, b - 4), a(tx - 60, DESK_Y - 3),
                 a(tx, ty)]
            self.cv.create_line([c for q in p for c in q], smooth=True,
                                width=max(2, int(3 * self.sc)), fill=col)
        self.term["PZ+"] = (452, DESK_Y - 26)
        self.term["PZ-"] = (452, DESK_Y - 8)
        st = self.rig.stick_in_hole()
        if st:
            ln = 120 if self.rig.placed.get("L2") == "hole" else 74
            self.R(cx - 3, t - ln, cx + 3, t + 4, fill=C_WOOD_LT, outline=C_WOOD_DK)

    # -- stand -------------------------------------------------------
    def draw_stand(self, g):
        xs = self.x_stand
        nz = g["nozzle"]
        self.RR(xs - 58, DESK_Y - 12, xs + 58, DESK_Y, 3, fill=C_WOOD, outline=C_WOOD_DK)
        self.RR(xs - 11, DESK_Y - 470, xs + 11, DESK_Y - 8, 3, fill=C_WOOD, outline=C_WOOD_DK)
        ya = DESK_Y - self.rig.release_h * PPM - 20
        self.RR(nz - 12, ya - 9, xs + 8, ya + 9, 4, fill=C_WOOD_LT, outline=C_WOOD_DK)
        for dy in (-5, 5):
            self.O(xs - 6, ya + dy - 5, xs + 6, ya + dy + 5, fill=C_METAL, outline=C_METAL_DK)
        self.R(nz - 5, ya + 6, nz + 5, ya + 22, fill="#1e1e1e", outline="#000000")
        # wing that carries the peg + ruler
        self.RR(nz + 32, DESK_Y - 474, xs - 8, DESK_Y - 456, 3, fill=C_WOOD, outline=C_WOOD_DK)
        if self.rig.placed.get("N") == "stand":
            self.RR(g["ruler_x"] - 16, DESK_Y - 480, g["ruler_x"] + 16, DESK_Y - 450, 3,
                    fill="#c8a76a", outline=C_WOOD_DK)

    # -- ruler -------------------------------------------------------
    def draw_ruler(self, g):
        x = g["ruler_x"]
        z = self.rig.tr.ruler_zero * PPM
        top = DESK_Y - self.rig.tr.ruler_len * PPM - z
        self.RR(x - 13, top, x + 13, DESK_Y, 2, fill="#f0e2b0", outline="#b09a5c")
        for mm in range(0, 501):
            y = DESK_Y - z - mm * PPM / 1000.0
            if mm % 10 == 0:
                ln = 11
            elif mm % 5 == 0:
                ln = 7
            else:
                ln = 4
            self.L(x - 13, y, x - 13 + ln, y, fill="#6b5a2a", width=1)
            if mm % 50 == 0 and mm > 0:
                self.TX(x + 5, y, text=str(mm // 10), font=self.fnt(7), fill="#4a3d17")

    # -- multimeter --------------------------------------------------
    def draw_meter(self):
        self.RR(580, 52, 764, 364, 14, fill=C_RED, outline=C_RED_DK)
        self.RR(590, 62, 754, 354, 12, fill="#d8443a", outline="")
        self.RR(598, 76, 746, 144, 6, fill=C_LCD, outline="#7d8a6e")
        self.TX(746, 158, text=self.rig.tr.meter_model, anchor="e",
                font=self.fnt(9, True), fill="#ffe9e6")
        cxm, cym, r = 672, 250, 60
        self.O(cxm - r, cym - r, cxm + r, cym + r, fill="#2f2f2f", outline="#111111")
        self.O(cxm - 34, cym - 34, cxm + 34, cym + 34, fill="#4a4a4a", outline="#222222")
        for i, name in enumerate(DIAL_ORDER):
            a = math.radians(-90 + i * 360.0 / len(DIAL_ORDER))
            lx = cxm + (r + 13) * math.cos(a)
            ly = cym + (r + 13) * math.sin(a)
            self.TX(lx, ly, text=name, font=self.fnt(6, True), fill="#ffffff")
        self.O(624, 328, 640, 344, fill="#111111", outline="#000000")
        self.O(704, 328, 720, 344, fill="#111111", outline="#000000")
        self.TX(632, 320, text="COM", font=self.fnt(6), fill="#ffffff")
        self.TX(712, 320, text=u"V\u03a9mA", font=self.fnt(6), fill="#ffffff")
        self.term["V-"] = (632, 386)
        self.term["V+"] = (712, 386)
        self.L(632, 344, 632, 386, fill=C_BLACK, width=3)
        self.L(712, 344, 712, 386, fill=C_RED, width=3)
        self.meter_dial_xy = (cxm, cym, r)

    # -- battery -----------------------------------------------------
    def draw_battery(self):
        self.RR(806, 176, 938, 222, 6, fill="#4c4f53", outline="#2b2d30")
        self.RR(816, 184, 914, 214, 4, fill="#c8b16a", outline="#8d7a3f")
        self.TX(865, 199, text="AA 1.5 V", font=self.fnt(8, True), fill="#3a3218")
        self.L(938, 186, 966, 186, fill=C_RED, width=3)
        self.L(938, 212, 966, 212, fill=C_BLACK, width=3)
        self.term["BAT+"] = (972, 186)
        self.term["BAT-"] = (972, 212)

    # -- capacitor + diode -------------------------------------------
    def draw_capacitor(self):
        self.RR(806, 300, 862, 372, 4, fill="#26418f", outline="#152a63")
        self.TX(834, 336, text="C", font=self.fnt(12, True), fill="#e9eefc")
        self.L(862, 316, 896, 316, fill=C_METAL_DK, width=2)
        self.L(862, 356, 896, 356, fill=C_METAL_DK, width=2)
        self.term["C1"] = (896, 316)
        self.term["C2"] = (896, 356)
        self.L(902, 316, 950, 316, fill=C_METAL_DK, width=2)
        self.RR(912, 307, 938, 325, 2, fill="#1b1b1b", outline="#000000")
        self.R(914, 307, 918, 325, fill="#dddddd", outline="")
        self.term["CD"] = (956, 316)
        self.TX(925, 294, text=T("다이오드", "diode"), font=self.fnt(7), fill="#555555")

    # -- switches ----------------------------------------------------
    def draw_switches(self):
        self.sw_btn = []
        for i in range(4):
            y = 90 + i * 92
            self.RR(1062, y - 22, 1130, y + 22, 6, fill="#3d4249", outline="#22262b")
            self.O(1082, y - 14, 1110, y + 14, fill="#8d959e", outline="#4a5058")
            self.TX(1096, y + 32, text="S%d" % (i + 1), font=self.fnt(8, True), fill="#3a3f45")
            self.L(1062, y, 1034, y, fill=C_BLACK, width=2)
            self.L(1130, y, 1162, y, fill=C_BLACK, width=2)
            self.term["S%da" % (i + 1)] = (1034, y)
            self.term["S%db" % (i + 1)] = (1162, y)
            self.sw_btn.append((1096, y))

    def draw_stopwatch(self):
        self.RR(800, 60, 880, 150, 8, fill="#1f1f22", outline="#0d0d0f")
        self.RR(806, 80, 874, 112, 4, fill=C_LCD, outline="#7d8a6e")

    def draw_screw(self):
        self.RR(816, 442, 884, 454, 3, fill=C_METAL, outline=C_METAL_DK)
        self.O(806, 440, 828, 458, fill=C_METAL, outline=C_METAL_DK)

    # -- wires -------------------------------------------------------
    def draw_wires(self):
        for a, b in self.rig.cir.wires:
            if a in self.term and b in self.term:
                x0, y0 = self.term[a]
                x1, y1 = self.term[b]
                mx = (x0 + x1) / 2.0
                my = (y0 + y1) / 2.0 + 18 + 0.06 * math.hypot(x1 - x0, y1 - y0)
                p0 = self.w2s(x0, y0); p1 = self.w2s(mx, my); p2 = self.w2s(x1, y1)
                self.cv.create_line(p0[0], p0[1], p1[0], p1[1], p2[0], p2[1],
                                    smooth=True, width=max(2, int(3 * self.sc)),
                                    fill=C_WIRE)

    # ---------------------------------------------------------- dynamic
    def draw_dynamic(self):
        rig = self.rig
        g = self.geom()
        cv = self.cv
        # multimeter LCD
        if rig.placed.get("B") == "tray":
            s = rig.cir.display()
            self.TX(738, 116, text=s, anchor="e", font=self.fnt(22, True, True),
                    fill=C_LCD_DK, tags="dyn")
            d = rig.cir.dial
            if d != "OFF":
                unit = "" if d in ("OHM", "A") else METER_RANGES[d][4]
                self.TX(738, 90, text=unit + "  DC", anchor="e",
                        font=self.fnt(9, True), fill="#4d5b41", tags="dyn")
            cxm, cym, r = self.meter_dial_xy
            i = DIAL_ORDER.index(d)
            a = math.radians(-90 + i * 360.0 / len(DIAL_ORDER))
            self.L(cxm, cym, cxm + (r - 6) * math.cos(a), cym + (r - 6) * math.sin(a),
                   fill="#ffd24a", width=max(2, int(5 * self.sc)), tags="dyn")
            self.O(cxm - 6, cym - 6, cxm + 6, cym + 6, fill="#d9dde2",
                   outline="#5a5f66", tags="dyn")
        # scales LCD
        if rig.placed.get("G") == "desk":
            s = rig.scale_display()
            self.TX(256, DESK_Y - 16, text=(s or "") + " kg", anchor="e",
                    font=self.fnt(11, True, True), fill=C_LCD_DK, tags="dyn")
        # stopwatch LCD
        if rig.placed.get("H") == "tray":
            self.TX(870, 96, text=rig.sw_display() or "", anchor="e",
                    font=self.fnt(11, True, True), fill=C_LCD_DK, tags="dyn")
        # pressed switches
        if rig.placed.get("E") == "tray":
            for i, (bx, by) in enumerate(self.sw_btn):
                if rig.cir.sw[i]:
                    self.O(bx - 14, by - 14, bx + 14, by + 14, fill="#f0553c",
                           outline="#8d2718", tags="dyn")
        # hand pressing the piezo
        if g["pz_slot"] and rig.press_now > 0.05:
            cx = g["cx_piezo"]
            t = g["pz_top"]
            ln = 0
            if rig.stick_in_hole():
                ln = 120 if rig.placed.get("L2") == "hole" else 74
            yy = t - ln - 8
            self.O(cx - 17, yy - 16, cx + 17, yy + 6, fill="#f0c9a4",
                   outline="#c39a72", tags="dyn")
            self.TX(cx - 44, yy - 8, text=u"\u2193", font=self.fnt(15, True),
                    fill="#a3522a", tags="dyn")
        # ball
        self.draw_ball(g)

    def draw_ball(self, g):
        rig = self.rig
        held = rig.loaded_ball()
        if held is None:
            return
        d = (rig.tr.d1 if held == "I1" else rig.tr.d2) * PPM
        col = C_BALL1 if held == "I1" else C_BALL2
        if rig.ball is None:
            y = rig.release_h
            x = g["nozzle"]
        else:
            y = rig.ball["y"]
            x = g["nozzle"]
            self.trail.append((x, y))
            if len(self.trail) > 90:
                self.trail.pop(0)
        for i, (tx, ty) in enumerate(self.trail):
            f = i / max(1.0, len(self.trail) - 1.0)
            gcol = "#%02x%02x%02x" % (int(200 - 60 * f), int(206 - 40 * f), int(214 - 30 * f))
            yy = DESK_Y - ty * PPM - d / 2.0
            self.O(tx - d / 2 * 0.55, yy - d / 2 * 0.55, tx + d / 2 * 0.55,
                   yy + d / 2 * 0.55, fill=gcol, outline="", tags="dyn")
        cy = DESK_Y - y * PPM - d / 2.0
        self.O(x - d / 2, cy - d / 2, x + d / 2, cy + d / 2, fill=col,
               outline="#1c1c1c", tags="dyn")
        self.O(x - d / 2 + d * 0.16, cy - d / 2 + d * 0.14,
               x - d / 2 + d * 0.36, cy - d / 2 + d * 0.32,
               fill="#ffffff", outline="", tags="dyn")

    # ---------------------------------------------------------- input
    def find_term(self, wx, wy):
        best, bd = None, 13.0
        for name, (x, y) in self.term.items():
            d = math.hypot(wx - x, wy - y)
            if d < bd:
                best, bd = name, d
        return best

    def on_press(self, e):
        wx, wy = self.s2w(e.x, e.y)
        rig = self.rig
        g = self.geom()
        # switches
        if rig.placed.get("E") == "tray":
            for i, (bx, by) in enumerate(self.sw_btn):
                if math.hypot(wx - bx, wy - by) < 17:
                    rig.cir.set_switch(i, True)
                    return
        t = self.find_term(wx, wy)
        if t:
            if self.pending is None:
                self.pending = t
            elif self.pending == t:
                self.pending = None
            else:
                if len(rig.cir.wires) >= 12:
                    self.hint.config(text=T("악어 클립이 부족합니다.", "No spare crocodile clips."))
                else:
                    rig.cir.add_wire(self.pending, t)
                self.pending = None
            self.mark()
            return
        # stand dragging
        if rig.placed.get("J") == "desk" and abs(wx - self.x_stand) < 62 and wy > DESK_Y - 24:
            self.dragging_stand = True
            return
        self.pan = (e.x, e.y, self.ox, self.oy)

    def on_drag(self, e):
        if self.dragging_stand:
            wx, wy = self.s2w(e.x, e.y)
            self.x_stand = max(190.0, min(640.0, wx))
            self.update_target()
            self.mark()
            return
        if self.pan:
            x0, y0, ox, oy = self.pan
            self.ox = ox + (e.x - x0)
            self.oy = oy + (e.y - y0)
            self.mark()

    def on_up(self, e):
        self.dragging_stand = False
        self.pan = None
        for i in range(4):
            self.rig.cir.set_switch(i, False)

    def on_right(self, e):
        wx, wy = self.s2w(e.x, e.y)
        t = self.find_term(wx, wy)
        if self.pending:
            self.pending = None
            self.mark()
            return
        if t:
            for i, (a, b) in enumerate(list(self.rig.cir.wires)):
                if a == t or b == t:
                    self.rig.cir.remove_wire(i)
                    break
            self.mark()
            return
        # remove the wire whose midpoint is nearest
        best, bi = 18.0, None
        for i, (a, b) in enumerate(self.rig.cir.wires):
            if a in self.term and b in self.term:
                x0, y0 = self.term[a]; x1, y1 = self.term[b]
                mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0 + 11
                d = math.hypot(wx - mx, wy - my)
                if d < best:
                    best, bi = d, i
        if bi is not None:
            self.rig.cir.remove_wire(bi)
            self.mark()

    def update_target(self):
        g = self.geom()
        if self.rig.piezo_placed() and abs(g["nozzle"] - g["cx_piezo"]) < 26:
            self.rig.release_over = "piezo"
        else:
            self.rig.release_over = "desk"

    def on_wheel(self, e, direction=None):
        if direction is None:
            direction = 1 if e.delta > 0 else -1
        wx, wy = self.s2w(e.x, e.y)
        rig = self.rig
        g = self.geom()
        fine = bool(getattr(e, "state", 0) & 0x0001)
        # multimeter dial
        if rig.placed.get("B") == "tray":
            cxm, cym, r = self.meter_dial_xy
            if math.hypot(wx - cxm, wy - cym) < r + 18:
                i = (DIAL_ORDER.index(rig.cir.dial) + (1 if direction > 0 else -1)) % len(DIAL_ORDER)
                rig.cir.set_dial(DIAL_ORDER[i])
                return
        # release height (wing nuts / column)
        if rig.placed.get("J") == "desk" and abs(wx - self.x_stand) < 40:
            step = 0.001 if fine else 0.005
            rig.set_release_height(rig.release_h + direction * step)
            self.mark()
            return
        # pressing the piezo
        if g["pz_slot"]:
            cx = g["cx_piezo"]
            if abs(wx - cx) < 60 and g["pz_top"] - 130 < wy < g["pz_base"] + 10:
                step = 0.5 if fine else 4.0
                rig.set_press(rig.press_target + direction * step)
                return
        # otherwise zoom
        f = 1.08 if direction > 0 else 1 / 1.08
        ns = max(0.45, min(2.4, self.sc * f))
        self.ox = e.x - (e.x - self.ox) * ns / self.sc
        self.oy = e.y - (e.y - self.oy) * ns / self.sc
        self.sc = ns
        self.mark()


# =====================================================================
class App(tk.Tk):
    def __init__(self, seed=None):
        super().__init__()
        self.title(T("EuPhO 2024 실험 E — 압전 현상의 물리  |  HaslaLab",
                     "EuPhO 2024 Experiment E - Physics of Piezoelectricity  |  HaslaLab"))
        self.geometry("1180x780")
        self.rig = Rig(seed)
        self.speed = 1.0
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.bench = BenchTab(nb, self)
        self.asm = AssemblyTab(nb, self)
        nb.add(self.asm, text=T(" 1. 조립 ", " 1. Assembly "))
        nb.add(self.bench, text=T(" 2. 실험대 ", " 2. Bench "))
        nb.bind("<<NotebookTabChanged>>", lambda e: (self.bench.mark(),
                                                     self.bench.redraw()))
        self.after(30, self.tick)

    def set_speed(self, s):
        self.speed = float(s.replace("x", ""))

    def tick(self):
        if not self.winfo_exists():
            return
        self.rig.advance(0.030 * self.speed)
        try:
            self.bench.redraw()
            self.after(30, self.tick)
        except tk.TclError:
            return


def main():
    global LANG
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default=None, choices=["ko", "en"])
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.lang:
        LANG = a.lang.upper()
    if a.selftest:
        app = App(a.seed)
        app.update()
        for pid, slot in (("G", "desk"), ("J", "desk"), ("N", "stand"), ("K", "stand"),
                          ("A", "scale"), ("B", "tray"), ("C", "tray"), ("D", "tray"),
                          ("E", "tray"), ("H", "tray"), ("M", "tray"), ("I1", "release")):
            app.rig.place(pid, slot)
        app.asm.redraw()
        app.bench.mark()
        app.rig.cir.add_wire("PZ+", "S2a")
        app.rig.cir.add_wire("S2b", "C1")
        app.rig.cir.add_wire("C2", "PZ-")
        app.rig.cir.set_dial("2V")
        for _ in range(40):
            app.update()
            app.rig.advance(0.03)
        app.bench.redraw()
        app.update()
        print("selftest OK  seed=%d  meter=%s" % (app.rig.tr.seed, app.rig.tr.meter_model))
        app.destroy()
        return
    App(a.seed).mainloop()


if __name__ == "__main__":
    main()
