#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  1st European Physics Olympiad  (EuPhO 2017, Tartu, Estonia)
  Experimental Problem :  LIGHT-EMITTING DIODE
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Apparatus after the problem sheet: two identical circuit boards
    (LED, heating resistor R1, thermistor RT), two bottles with airtight
    caps and tubes, a water U-tube manometer on a stand read against a
    millimetre strip, a syringe, three multimeters (one voltage-only),
    two 10-turn potentiometers, a power supply and cables.  The LED is a
    real junction (ideality n, gap VG0, series Rs) solved by Newton-
    Raphson nodal analysis; the boards heat, the trapped air expands and
    the menisci move; two facing LEDs make a photocurrent.
    Only what a real instrument shows is displayed: the multimeter LCDs,
    the supply's voltage, the meniscus positions on the mm strip and the
    ruler.  No temperature, efficiency or fit is ever computed.
    Every hidden true parameter is randomised for each session;
    --official reproduces the values of the official solution.

    Run:   python3 eupho2017_E1_sim_KO.py   [--seed=N] [--lang=ko|en] [--official]
"""
import math
import random
import sys

# --------------------------------------------------------------------------
# i18n
# --------------------------------------------------------------------------
LANG = "KO"          # the EN edition differs only in this line


def T(ko, en):
    """Bilingual string selector."""
    return ko if LANG == "KO" else en


# --------------------------------------------------------------------------
# Physical constants (as given in the problem sheet)
# --------------------------------------------------------------------------
K_B = 1.381e-23          # J/K   (value prescribed by the problem)
Q_E = 1.602e-19          # C     (value prescribed by the problem)
G_ACC = 9.81             # m/s^2
RHO_W = 998.0            # kg/m^3, water at ~293 K
S_ACTIVE = 1.56e-6       # m^2, active area of the LED chip (given)
ALPHA_SPHERE = 0.33      # LED radiates uniformly into 33 % of the sphere (given)

# Thermistor calibration, exactly as printed on the problem sheet:
#   T = 2.254 K (ln(RT/kOhm))^2 - 32.46 K ln(RT/kOhm) + 361.09 K
TH_A, TH_B, TH_C = 2.254, 32.46, 361.09


def thermistor_T(R_kohm):
    """Absolute temperature from thermistor resistance in kOhm."""
    x = math.log(max(R_kohm, 1e-9))
    return TH_A * x * x - TH_B * x + TH_C


def thermistor_R(T_kelvin):
    """Inverse of the calibration curve -> resistance in kOhm (falling branch)."""
    disc = TH_B * TH_B - 4.0 * TH_A * (TH_C - T_kelvin)
    if disc < 0.0:
        disc = 0.0
    x = (TH_B - math.sqrt(disc)) / (2.0 * TH_A)
    return math.exp(x)


# --------------------------------------------------------------------------
# Hidden truth -- randomised once per session
# --------------------------------------------------------------------------
OFFICIAL_SEED = 2017     # reproduces the parameters of the official solution


class Truth(object):
    """
    All hidden parameters of the apparatus.  Nothing in this object is ever
    displayed; it is only used to generate instrument readings.
    """

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1, 10 ** 6)
        self.seed = int(seed)
        rng = random.Random(self.seed * 7919 + 13)
        self.rng = rng
        official = (self.seed == OFFICIAL_SEED)
        self.official = official

        def u(a, b, fixed=None):
            v = rng.uniform(a, b)
            return fixed if (official and fixed is not None) else v

        # ---- LED junction ------------------------------------------------
        self.VG0 = u(2.020, 2.150, 2.085)          # V, nominal bandgap voltage
        self.n = u(1.42, 1.70, 1.55)               # ideality factor
        self.A = u(70.0, 200.0, 119.0)             # A, structure parameter
        self.Rs = u(0.55, 0.95, 0.70)              # Ohm, parasitic series R
        self.Rsh = u(1.0e6, 2.6e6, 1.5e6)          # Ohm, junction leakage shunt
        self.eta_int = u(0.42, 0.62, 0.530)        # internal junction efficiency
        self.Vbr = u(4.5, 6.5, 5.5)                # reverse breakdown voltage
        self.Imax_led = u(1.35, 1.75, 1.50)        # A, destructive forward current

        # ---- board -------------------------------------------------------
        self.R1_300 = u(5.50, 6.10, 5.75)          # Ohm heater at 300 K
        self.R1_tcr = u(2.0e-4, 6.0e-4, 3.0e-4)    # 1/K
        self.Rth_jb = u(1.5, 3.5, 2.0)             # K/W junction -> board
        self.G_board = u(0.0200, 0.0270, 0.0230)   # W/K board -> surroundings
        self.C_board = u(5.0, 8.5, 6.0)            # J/K
        self.th_tol = u(-0.008, 0.008, 0.0)        # thermistor tolerance (rel.)

        # ---- bottle / manometer -----------------------------------------
        self.G_bottle = u(0.385, 0.470, 0.4139)    # W/K bottle air -> room
        self.C_bottle = u(45.0, 80.0, 60.0)        # J/K effective
        self.V_bottle = u(4.5e-4, 5.5e-4, 5.0e-4)  # m^3 of trapped air
        self.A_tube = u(2.8e-6, 3.6e-6, 3.14e-6)   # m^2 tube bore
        self.p_atm = u(9.90e4, 1.025e5, 1.0132e5)  # Pa

        # ---- optics ------------------------------------------------------
        self.R_ph = u(0.060, 0.105, 0.0800)        # A/W responsivity of the LED
        self.I_amb = u(0.02e-6, 0.10e-6, 0.05e-6)  # A stray ambient photocurrent

        # ---- environment -------------------------------------------------
        self.T_amb = u(294.0, 299.5, 297.0)
        self.T_drift_ph = rng.uniform(0.0, 6.28)

        # ---- instruments -------------------------------------------------
        self.I_diode_test = u(3.05e-4, 3.60e-4, 3.30e-4)   # A, diode-test mode
        self.meter_gain = [1.0 + u(-0.0012, 0.0012, 0.0) for _ in range(3)]
        self.meter_off = [u(-0.6, 0.6, 0.0) for _ in range(3)]  # in LSB counts
        self.men_noise = u(0.25, 0.55, 0.35)       # mm, meniscus reading noise

        self.bottle_spread = [1.0, 1.0 + u(-0.03, 0.03, 0.02)]

        # per-board tiny spread (the two boards are "identical")
        self.board_spread = [
            {"VG0": 0.0, "A": 1.0, "R1": 1.0, "eta": 1.0},
            {"VG0": u(-0.006, 0.006, 0.0),
             "A": math.exp(u(-0.05, 0.05, 0.0)),
             "R1": 1.0 + u(-0.010, 0.010, 0.0),
             "eta": 1.0 + u(-0.03, 0.03, 0.0)},
        ]

    # -- convenience -------------------------------------------------------
    def led_params(self, board):
        s = self.board_spread[board]
        return (self.VG0 + s["VG0"], self.n, self.A * s["A"],
                self.eta_int * s["eta"])

    def R1_of(self, board, Tb):
        s = self.board_spread[board]
        return self.R1_300 * s["R1"] * (1.0 + self.R1_tcr * (Tb - 300.0))


# --------------------------------------------------------------------------
# Linear algebra + MNA circuit solver
# --------------------------------------------------------------------------
def solve_linear(Amat, b):
    """Gaussian elimination with partial pivoting.  Returns list x or None."""
    n = len(b)
    if n == 0:
        return []
    M = [row[:] + [b[i]] for i, row in enumerate(Amat)]
    for col in range(n):
        piv, pv = col, abs(M[col][col])
        for r in range(col + 1, n):
            if abs(M[r][col]) > pv:
                piv, pv = r, abs(M[r][col])
        if pv < 1e-18:
            return None
        if piv != col:
            M[col], M[piv] = M[piv], M[col]
        inv = 1.0 / M[col][col]
        for r in range(col + 1, n):
            f = M[r][col] * inv
            if f == 0.0:
                continue
            row_r, row_c = M[r], M[col]
            for c in range(col, n + 1):
                row_r[c] -= f * row_c[c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = M[r][n]
        for c in range(r + 1, n):
            s -= M[r][c] * x[c]
        x[r] = s / M[r][r]
    return x


GMIN = 1e-12


class Netlist(object):
    """
    Tiny MNA engine.  Node 0 is the reference node; every node is tied to it
    through GMIN so that floating sub-circuits stay solvable.
    """

    def __init__(self):
        self.nodes = {0: 0}      # name -> index (0 is ground)
        self.res = []            # (a, b, R)
        self.isrc = []           # (a, b, I)  current I flows a -> b inside src
        self.vsrc = []           # (a, b, E)
        self.diodes = []         # dict describing a junction

    def node(self, name):
        if name not in self.nodes:
            self.nodes[name] = len(self.nodes)
        return self.nodes[name]

    def R(self, a, b, r):
        if r <= 0.0:
            r = 1e-9
        self.res.append((self.node(a), self.node(b), r))

    def I(self, a, b, cur):
        self.isrc.append((self.node(a), self.node(b), cur))

    def V(self, a, b, e):
        self.vsrc.append((self.node(a), self.node(b), e))
        return len(self.vsrc) - 1

    def diode(self, a, c, Is, VT_n, Rsh, Iph):
        """Junction between node a and node c (anode, cathode)."""
        d = {"a": self.node(a), "c": self.node(c), "Is": Is,
             "nVT": VT_n, "Rsh": Rsh, "Iph": Iph, "v": 0.0}
        self.diodes.append(d)
        return d

    # ---------------------------------------------------------------- solve
    def solve(self, maxiter=200, tol=1e-10):
        nn = len(self.nodes) - 1                      # unknown node voltages
        nv = len(self.vsrc)
        N = nn + nv
        if N == 0:
            return {}
        idx = {}
        for name, i in self.nodes.items():
            idx[i] = i - 1                            # ground -> -1
        vsol = [0.0] * (len(self.nodes))
        for d in self.diodes:
            d["v"] = 0.0
        x = None
        for it in range(maxiter):
            Amat = [[0.0] * N for _ in range(N)]
            bvec = [0.0] * N

            def sg(a, b, g):
                ia, ib = idx[a], idx[b]
                if ia >= 0:
                    Amat[ia][ia] += g
                if ib >= 0:
                    Amat[ib][ib] += g
                if ia >= 0 and ib >= 0:
                    Amat[ia][ib] -= g
                    Amat[ib][ia] -= g

            def si(a, b, cur):
                ia, ib = idx[a], idx[b]
                if ia >= 0:
                    bvec[ia] -= cur
                if ib >= 0:
                    bvec[ib] += cur

            for i in range(1, len(self.nodes)):
                Amat[idx[i]][idx[i]] += GMIN
            for (a, b, r) in self.res:
                sg(a, b, 1.0 / r)
            for (a, b, cur) in self.isrc:
                si(a, b, cur)
            for k, (a, b, e) in enumerate(self.vsrc):
                row = nn + k
                ia, ib = idx[a], idx[b]
                if ia >= 0:
                    Amat[row][ia] += 1.0
                    Amat[ia][row] += 1.0
                if ib >= 0:
                    Amat[row][ib] -= 1.0
                    Amat[ib][row] -= 1.0
                bvec[row] += e
            # non-linear junctions
            for d in self.diodes:
                v = d["v"]
                nVT = d["nVT"]
                ex = math.exp(min(v / nVT, 80.0))
                Id = d["Is"] * (ex - 1.0) + v / d["Rsh"] - d["Iph"]
                gd = d["Is"] * ex / nVT + 1.0 / d["Rsh"]
                if gd < 1e-14:
                    gd = 1e-14
                Ieq = Id - gd * v
                sg(d["a"], d["c"], gd)
                si(d["a"], d["c"], Ieq)

            x = solve_linear(Amat, bvec)
            if x is None:
                return None
            vs = [0.0] * len(self.nodes)
            for i in range(1, len(self.nodes)):
                vs[i] = x[idx[i]]
            if not self.diodes:
                vsol = vs
                break
            worst = 0.0
            for d in self.diodes:
                vnew = vs[d["a"]] - vs[d["c"]]
                vnew = _pn_limit(vnew, d["v"], d["nVT"])
                worst = max(worst, abs(vnew - d["v"]))
                d["v"] = vnew
            vsol = vs
            if worst < tol:
                break
        self._v = vsol
        self._x = x
        self._nn = nn
        return vsol

    def vnode(self, name):
        return self._v[self.nodes[name]]

    def vsrc_current(self, k):
        """Current flowing from + terminal into the source."""
        return self._x[self._nn + k]

    def r_current(self, a, b, r):
        return (self.vnode(a) - self.vnode(b)) / r


def _pn_limit(vnew, vold, nVT):
    """Classic pn-junction limiting to keep Newton-Raphson stable."""
    vcrit = nVT * math.log(nVT / (math.sqrt(2.0) * 1e-14))
    if vnew > vcrit and abs(vnew - vold) > 2.0 * nVT:
        if vold > 0.0:
            arg = 1.0 + (vnew - vold) / nVT
            if arg > 0.0:
                vnew = vold + nVT * math.log(arg)
            else:
                vnew = vcrit
        else:
            vnew = nVT * math.log(max(vnew / nVT, 1e-12))
    if vnew < -5.0:
        vnew = max(vnew, -12.0)
    if vnew - vold > 0.4:
        vnew = vold + 0.4
    elif vold - vnew > 0.4:
        vnew = vold - 0.4
    return vnew


# --------------------------------------------------------------------------
# Digital multimeter (3 1/2 digits, 1999 counts)
# --------------------------------------------------------------------------
# (name, full-scale in display unit, value->unit factor, unit, decimals)
VDC_RANGES = [("200mV", 199.9, 1e3, "mV", 1),
              ("2V", 1.999, 1.0, "V", 3),
              ("20V", 19.99, 1.0, "V", 2),
              ("200V", 199.9, 1.0, "V", 1)]

ADC_RANGES = [("200uA", 199.9, 1e6, "\u00b5A", 1),
              ("2mA", 1.999, 1e3, "mA", 3),
              ("20mA", 19.99, 1e3, "mA", 2),
              ("200mA", 199.9, 1e3, "mA", 1),
              ("2A", 1.999, 1.0, "A", 3),
              ("10A", 9.99, 1.0, "A", 2)]

OHM_RANGES = [("200", 199.9, 1.0, "\u03a9", 1),
              ("2k", 1.999, 1e-3, "k\u03a9", 3),
              ("20k", 19.99, 1e-3, "k\u03a9", 2),
              ("200k", 199.9, 1e-3, "k\u03a9", 1),
              ("2M", 1.999, 1e-6, "M\u03a9", 3)]

DIODE_RANGE = ("diode", 2.999, 1.0, "V", 3)

ADC_SHUNT = {"200uA": 1000.0, "2mA": 100.0, "20mA": 10.0,
             "200mA": 1.0, "2A": 0.1, "10A": 0.01}
ADC_FUSED = {"200uA": True, "2mA": True, "20mA": True,
             "200mA": True, "2A": False, "10A": False}
FUSE_RATING = 0.25          # A

OHM_ITEST = {"200": 1.0e-3, "2k": 1.0e-4, "20k": 1.0e-5,
             "200k": 1.0e-6, "2M": 1.0e-7}
OHM_COMPLIANCE = 3.0        # V
VOLTMETER_Z = 10.0e6        # Ohm

MODES_FULL = ["OFF", "VDC", "ADC", "OHM", "DIODE"]
MODES_VONLY = ["OFF", "VDC"]


class DMM(object):
    def __init__(self, index, truth, voltage_only=False):
        self.index = index
        self.truth = truth
        self.voltage_only = voltage_only
        self.mode = "OFF"
        self.range = "AUTO"
        self.fuse_ok = True
        self.value = None          # raw SI value of the measured quantity
        self.overload = False
        self.blown_note = False

    # -------------------------------------------------------------- helpers
    def modes(self):
        return MODES_VONLY if self.voltage_only else MODES_FULL

    def range_list(self):
        if self.mode == "VDC":
            return VDC_RANGES
        if self.mode == "ADC":
            return ADC_RANGES
        if self.mode == "OHM":
            return OHM_RANGES
        if self.mode == "DIODE":
            return [DIODE_RANGE]
        return []

    def range_names(self):
        return ["AUTO"] + [r[0] for r in self.range_list()]

    def active_range(self, value):
        rl = self.range_list()
        if not rl:
            return None
        if self.mode == "DIODE":
            return rl[0]
        if self.range != "AUTO":
            for r in rl:
                if r[0] == self.range:
                    return r
            return rl[-1]
        if value is None:
            return rl[0]
        for r in rl:
            if abs(value) * r[2] <= r[1]:
                return r
        return rl[-1]

    def shunt(self):
        """Series resistance the ammeter inserts."""
        if self.mode != "ADC":
            return None
        rname = self.range
        if rname == "AUTO":
            rname = self._auto_adc_range()
        return ADC_SHUNT.get(rname, 1.0)

    def _auto_adc_range(self):
        v = self.value
        if v is None:
            return "200mA"
        for r in ADC_RANGES:
            if abs(v) * r[2] <= r[1]:
                return r[0]
        return "10A"

    # -------------------------------------------------------------- display
    def display(self):
        if self.mode == "OFF":
            return ""
        if self.mode == "ADC" and not self.fuse_ok:
            return "0.0"
        v = self.value
        if v is None:
            return "O.L"
        rng = self.active_range(v)
        if rng is None:
            return ""
        name, fs, fac, unit, dec = rng
        shown = v * fac
        lsb = 10.0 ** (-dec)
        g = self.truth.meter_gain[self.index]
        shown = shown * g + self.truth.meter_off[self.index] * lsb
        shown += random.gauss(0.0, 0.30 * lsb)
        if abs(shown) > fs + 0.5 * lsb:
            return "  1  " if not self.mode == "OHM" else "  1  "
        q = round(shown / lsb) * lsb
        if abs(q) < 0.5 * lsb:
            q = 0.0
        return ("%." + str(dec) + "f") % q

    def display_unit(self):
        rng = self.active_range(self.value)
        if rng is None:
            return ""
        return rng[3]

    def display_range(self):
        rng = self.active_range(self.value)
        if rng is None:
            return ""
        return rng[0]


# --------------------------------------------------------------------------
# Apparatus inventory / assembly bookkeeping
# --------------------------------------------------------------------------
PARTS = ["board1", "board2", "cap1", "cap2",
         "tube1", "tube2", "utube", "scale", "stand"]

SLOTS = {
    # slot id            : (label_ko, label_en)
    "bench1":  ("실험대 - 기판 1", "bench - board 1"),
    "bench2":  ("실험대 - 기판 2", "bench - board 2"),
    "bottle1": ("병 1 내부", "inside bottle 1"),
    "bottle2": ("병 2 내부", "inside bottle 2"),
    "cap1":    ("병 1 마개", "cap of bottle 1"),
    "cap2":    ("병 2 마개", "cap of bottle 2"),
    "tube1":   ("병 1 튜브", "tube of bottle 1"),
    "tube2":   ("병 2 튜브", "tube of bottle 2"),
    "utube":   ("스탠드 - U자관", "stand - U-tube"),
    "scale":   ("스탠드 - 밀리미터 눈금", "stand - millimetre scale"),
    "mountA":  ("대향 거치대 A", "facing mount A"),
    "mountB":  ("대향 거치대 B", "facing mount B"),
    "stand":   ("스탠드", "stand"),
}


# --------------------------------------------------------------------------
# The rig: apparatus state + physics engine + public (instrument-level) API
# --------------------------------------------------------------------------
POT_TOTAL = 10.0             # Ohm, 10-turn wirewound potentiometer
PSU_RINT = 0.05              # Ohm
PSU_ILIM = 2.0               # A
TUBE_ARM_MM = 300.0          # usable length of one arm of the U-tube
UTUBE_AREA_DEFAULT = 3.14e-6


class UnionFind(object):
    def __init__(self):
        self.p = {}

    def add(self, a):
        if a not in self.p:
            self.p[a] = a

    def find(self, a):
        self.add(a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


class Rig(object):
    """Everything the student can touch.  Read-outs are strings only."""

    def __init__(self, seed=None):
        self.truth = Truth(seed)
        tr = self.truth
        self.time = 0.0
        self.free_parts = list(PARTS)
        self.placed = {}                  # slot -> part
        self.water_ml = 0.0
        self.cables = []                  # list of [term_a, term_b]
        self.psu_on = False
        self.psu_V = 0.0
        self.psu_I = 0.0
        self.psu_cc = False
        self.pot = [0.500, 0.500]
        self.meters = [DMM(0, tr), DMM(1, tr), DMM(2, tr, voltage_only=True)]
        self.board_T = [tr.T_amb, tr.T_amb]
        self.air_T = [tr.T_amb, tr.T_amb]
        self.sealed = [None, None]
        self.P_light = [0.0, 0.0]
        self.P_elec = [0.0, 0.0]
        self.P_junc = [0.0, 0.0]
        self.P_heat = [0.0, 0.0]
        self.I_led = [0.0, 0.0]
        self.led_dead = [False, False]
        self.over_time = [0.0, 0.0]
        self.spare_fuses = 3
        self.dist_set_mm = 30.0
        self.dist_off_mm = tr.rng.uniform(-0.4, 0.4)
        self.log = []
        self.water_spilled = False
        self._h_left = 150.0
        self._h_right = 150.0

    # ------------------------------------------------------------ messages
    def note(self, ko, en):
        self.log.append(T(ko, en))
        if len(self.log) > 60:
            self.log.pop(0)

    def pop_notes(self):
        out = self.log[:]
        self.log = []
        return out

    # ------------------------------------------------------------ assembly
    def board_slot(self, i):
        for s, p in self.placed.items():
            if p == "board%d" % i:
                return s
        return None

    def slot_of(self, part):
        for s, p in self.placed.items():
            if p == part:
                return s
        return None

    def can_place(self, part, slot):
        if part not in self.free_parts:
            return False, T("이미 배치된 부품입니다.", "part is already placed")
        if slot in self.placed:
            return False, T("이 자리는 이미 차 있습니다.", "slot already occupied")
        if part in ("board1", "board2"):
            if slot not in ("bench1", "bench2", "bottle1", "bottle2",
                            "mountA", "mountB"):
                return False, T("회로 기판을 놓을 수 없는 자리입니다.",
                                "a circuit board cannot go there")
            if slot in ("bottle1", "bottle2"):
                cap = "cap" + slot[-1]
                if cap in self.placed.values():
                    return False, T("마개를 먼저 열어야 기판을 넣을 수 있습니다.",
                                    "remove the cap before inserting the board")
            return True, ""
        if part in ("cap1", "cap2"):
            if slot != "cap" + part[-1]:
                return False, T("마개는 해당 병에만 끼울 수 있습니다.",
                                "the cap only fits its own bottle")
            return True, ""
        if part in ("tube1", "tube2"):
            k = part[-1]
            if slot != "tube" + k:
                return False, T("튜브 연결 위치가 아닙니다.", "not a tube port")
            if ("cap" + k) not in self.placed:
                return False, T("먼저 병에 마개를 끼우시오.",
                                "fit the cap on the bottle first")
            if "utube" not in self.placed:
                return False, T("먼저 스탠드에 U자관을 만드시오.",
                                "build the U-tube on the stand first")
            return True, ""
        if part == "utube":
            if slot != "utube":
                return False, T("U자관은 스탠드에 설치합니다.",
                                "the U-tube is mounted on the stand")
            if "stand" not in self.placed:
                return False, T("먼저 스탠드를 세우시오.",
                                "put up the stand first")
            return True, ""
        if part == "scale":
            if slot != "scale":
                return False, T("눈금자는 스탠드에 답니다.",
                                "the scale is fixed to the stand")
            if "stand" not in self.placed:
                return False, T("먼저 스탠드를 세우시오.",
                                "put up the stand first")
            return True, ""
        if part == "stand":
            return (slot == "stand"), ""
        if part == "syringe":
            return False, T("주사기는 배치 부품이 아니라 물을 넣는 도구입니다.",
                            "the syringe is a tool, not a placed part")
        return False, T("배치할 수 없습니다.", "cannot be placed")

    def place(self, part, slot):
        ok, msg = self.can_place(part, slot)
        if not ok:
            self.note(msg, msg)
            return False
        self.placed[slot] = part
        self.free_parts.remove(part)
        if slot in ("cap1", "cap2"):
            self._seal(int(slot[-1]) - 1)
        return True

    def remove(self, part):
        slot = self.slot_of(part)
        if slot is None:
            return False
        if part in ("cap1", "cap2"):
            k = part[-1]
            if ("tube" + k) in self.placed:
                self.note(T("튜브를 먼저 빼시오.", "detach the tube first"),
                          "detach the tube first")
                return False
        if part == "utube":
            for k in ("1", "2"):
                if ("tube" + k) in self.placed:
                    self.note(T("튜브를 먼저 빼시오.", "detach the tubes first"),
                              "detach the tubes first")
                    return False
            self.water_ml = 0.0
        if part in ("board1", "board2"):
            i = part[-1]
            self.cables = [c for c in self.cables
                           if not (c[0].startswith("B%s." % i) or
                                   c[1].startswith("B%s." % i))]
        del self.placed[slot]
        self.free_parts.append(part)
        if part in ("cap1", "cap2"):
            self.sealed[int(part[-1]) - 1] = None
        return True

    def _seal(self, b):
        """Record the state of the trapped air at the moment of closing."""
        tr = self.truth
        self.sealed[b] = {"p": tr.p_atm,
                          "V": tr.V_bottle * tr.bottle_spread[b],
                          "T": self.air_T[b]}

    def add_water(self, ml):
        if "utube" not in self.placed:
            self.note(T("U자관이 없습니다.", "no U-tube on the stand"), "")
            return False
        self.water_ml = max(0.0, min(2.0, self.water_ml + ml))
        self.water_spilled = False
        return True

    def water_level0_mm(self):
        """Rest level of both menisci above the bend, in mm."""
        a_mm2 = self.truth.A_tube * 1e6
        return (self.water_ml * 1000.0) / (2.0 * a_mm2)

    def manometer_ready(self):
        if "utube" not in self.placed or "scale" not in self.placed:
            return False
        h0 = self.water_level0_mm()
        return 25.0 < h0 < TUBE_ARM_MM - 25.0 and not self.water_spilled

    def set_distance(self, mm):
        self.dist_set_mm = max(5.0, min(200.0, float(mm)))

    def true_distance_m(self):
        return (self.dist_set_mm + self.dist_off_mm) * 1e-3

    # -------------------------------------------------------------- wiring
    def terminals(self):
        ts = []
        for i in (1, 2):
            if self.board_slot(i):
                ts += ["B%d.%d" % (i, k) for k in range(1, 7)]
        ts += ["PSU.+", "PSU.-"]
        for j in (1, 2):
            ts += ["P%d.A" % j, "P%d.W" % j, "P%d.B" % j]
        for k in (1, 2, 3):
            ts += ["M%d.HI" % k, "M%d.LO" % k]
        return ts

    def connect(self, a, b):
        ts = self.terminals()
        if a not in ts or b not in ts or a == b:
            self.note(T("연결할 수 없는 단자입니다.", "invalid terminal"), "")
            return False
        for c in self.cables:
            if set(c) == set([a, b]):
                return False
        self.cables.append([a, b])
        return True

    def disconnect(self, a, b):
        for c in list(self.cables):
            if set(c) == set([a, b]):
                self.cables.remove(c)
                return True
        return False

    def clear_cables(self):
        self.cables = []

    # ---------------------------------------------------------- instruments
    def set_psu(self, on=None, volts=None):
        if on is not None:
            self.psu_on = bool(on)
        if volts is not None:
            self.psu_V = max(0.0, min(6.0, round(float(volts), 3)))

    def set_pot(self, j, frac):
        self.pot[j] = max(0.0, min(1.0, float(frac)))

    def set_meter(self, k, mode=None, rng=None):
        m = self.meters[k]
        if mode is not None:
            if mode not in m.modes():
                self.note(T("이 멀티미터는 전압 전용입니다.",
                            "this multimeter is voltage-only"), "")
                return False
            m.mode = mode
            m.range = "AUTO"
        if rng is not None:
            if rng in m.range_names():
                m.range = rng
        return True

    def replace_fuse(self, k):
        if self.spare_fuses <= 0:
            self.note(T("여분 퓨즈가 없습니다.", "no spare fuse left"), "")
            return False
        if self.meters[k].fuse_ok:
            return False
        self.meters[k].fuse_ok = True
        self.spare_fuses -= 1
        return True

    # -------------------------------------------------------------- reading
    def display(self, k):
        return self.meters[k].display()

    def display_full(self, k):
        m = self.meters[k]
        s = m.display()
        if not s:
            return ""
        return "%s %s" % (s, m.display_unit())

    def read(self, k):
        """Numeric value of what the display shows (None if blank / O.L)."""
        m = self.meters[k]
        s = m.display()
        if not s or s.strip() == "1":
            return None
        try:
            val = float(s)
        except ValueError:
            return None
        rng = m.active_range(m.value)
        if rng is None:
            return None
        return val / rng[2]

    def read_manometer(self):
        """Meniscus positions as read off the millimetre strip (mm)."""
        if not self.manometer_ready():
            return None
        s = self.truth.men_noise
        left = round(self._h_left + random.gauss(0.0, s))
        right = round(self._h_right + random.gauss(0.0, s))
        return {"left": "%d mm" % left, "right": "%d mm" % right}

    def read_ruler_distance(self):
        d = self.dist_set_mm + self.dist_off_mm + random.gauss(0.0, 0.3)
        return "%d mm" % round(d)

    # ==================================================================
    #  physics engine
    # ==================================================================
    def _ambient(self):
        tr = self.truth
        return tr.T_amb + 0.15 * math.sin(2.0 * math.pi * self.time / 3600.0
                                          + tr.T_drift_ph)

    def _groups(self):
        uf = UnionFind()
        for t in self.terminals():
            uf.add(t)
        for a, b in self.cables:
            if a in uf.p and b in uf.p:
                uf.union(a, b)
        return uf

    def _solve_once(self, iph):
        tr = self.truth
        uf = self._groups()

        def g(t):
            return "N" + uf.find(t)

        gnd = g("PSU.-")
        nl = Netlist()
        nl.nodes = {gnd: 0}
        for t in self.terminals():
            nl.node(g(t))

        # --- boards -------------------------------------------------------
        led_nodes = {}
        for i in (1, 2):
            if not self.board_slot(i):
                continue
            b = i - 1
            Tb = self.board_T[b]
            VG0, n, A, _ = tr.led_params(b)
            Tj = Tb + tr.Rth_jb * max(0.0, self.P_junc[b])
            nVT = n * K_B * Tj / Q_E
            Is = A * math.exp(-VG0 / nVT)
            a_n, c_n, j_n = g("B%d.1" % i), g("B%d.2" % i), "LEDJ%d" % i
            if self.led_dead[b]:
                nl.R(a_n, c_n, 1.0e9)
            else:
                nl.R(a_n, j_n, tr.Rs)
                nl.diode(j_n, c_n, Is, nVT, tr.Rsh, iph[b])
                led_nodes[i] = (a_n, j_n, c_n, nVT, Is)
            nl.R(g("B%d.3" % i), g("B%d.6" % i), tr.R1_of(b, Tb))
            rt = thermistor_R(Tb) * 1000.0 * (1.0 + tr.th_tol)
            nl.R(g("B%d.4" % i), g("B%d.5" % i), rt)

        # --- power supply --------------------------------------------------
        vsrc_k = None
        if self.psu_on:
            vsrc_k = nl.V("PSUINT", gnd, self.psu_V)
            nl.R("PSUINT", g("PSU.+"), PSU_RINT)

        # --- potentiometers ------------------------------------------------
        for j in (1, 2):
            f = self.pot[j - 1]
            nl.R(g("P%d.A" % j), g("P%d.W" % j), max(POT_TOTAL * (1.0 - f), 0.004))
            nl.R(g("P%d.W" % j), g("P%d.B" % j), max(POT_TOTAL * f, 0.004))

        # --- meters ---------------------------------------------------------
        for k in (1, 2, 3):
            m = self.meters[k - 1]
            hi, lo = g("M%d.HI" % k), g("M%d.LO" % k)
            if m.mode == "VDC":
                nl.R(hi, lo, VOLTMETER_Z)
            elif m.mode == "ADC":
                if m.fuse_ok:
                    nl.R(hi, lo, m.shunt())
                else:
                    nl.R(hi, lo, 1.0e9)
            elif m.mode == "OHM":
                rname = m.range if m.range != "AUTO" else self._auto_ohm(m)
                it = OHM_ITEST.get(rname, 1e-5)
                nl.I(lo, hi, it)
                nl.R(hi, lo, 1.0e8)
            elif m.mode == "DIODE":
                nl.I(lo, hi, tr.I_diode_test)
                nl.R(hi, lo, 1.0e8)

        # --- solve with a simple constant-current fold-back ---------------
        E = self.psu_V
        for _ in range(6):
            if vsrc_k is not None:
                nl.vsrc[vsrc_k] = (nl.vsrc[vsrc_k][0], nl.vsrc[vsrc_k][1], E)
            v = nl.solve()
            if v is None:
                return None
            if vsrc_k is None:
                break
            cur = -nl.vsrc_current(vsrc_k)
            self.psu_I = cur
            if cur <= PSU_ILIM + 1e-6 or E <= 1e-4:
                self.psu_cc = False
                break
            self.psu_cc = True
            E = max(0.0, E - 0.6 * (cur - PSU_ILIM) * (PSU_RINT + 0.4))
        if not self.psu_on:
            self.psu_I = 0.0
            self.psu_cc = False
        return nl, uf, led_nodes

    def _auto_ohm(self, m):
        v = m.value
        if v is None:
            return "2M"
        for r in OHM_RANGES:
            if abs(v) * r[2] <= r[1]:
                return r[0]
        return "2M"

    def _step(self, dt):
        tr = self.truth
        iph = [tr.I_amb, tr.I_amb]
        res = None
        for _pass in range(2):
            res = self._solve_once(iph)
            if res is None:
                return
            nl, uf, led_nodes = res

            def g(t):
                return "N" + uf.find(t)

            # LED electrical / optical state
            P_el = [0.0, 0.0]
            P_lt = [0.0, 0.0]
            Iled = [0.0, 0.0]
            Pj = [0.0, 0.0]
            for i in (1, 2):
                b = i - 1
                if i not in led_nodes:
                    continue
                a_n, j_n, c_n, nVT, Is = led_nodes[i]
                va, vj, vc = nl.vnode(a_n), nl.vnode(j_n), nl.vnode(c_n)
                cur = (va - vj) / tr.Rs
                Vj = vj - vc
                Iexp = Is * (math.exp(min(Vj / nVT, 80.0)) - 1.0)
                Iled[b] = cur
                P_el[b] = (va - vc) * cur
                Pj[b] = Vj * Iexp
                if Iexp > 0.0:
                    P_lt[b] = tr.led_params(b)[3] * Pj[b]
                if Vj < -tr.Vbr and not self.led_dead[b]:
                    self.led_dead[b] = True
                    self.note("LED %d 이 역전압으로 파괴되었습니다!" % i,
                              "LED %d destroyed by reverse voltage!" % i)
            # optical coupling between the two facing boards
            sA, sB = self.board_slot(1), self.board_slot(2)
            if sA in ("mountA", "mountB") and sB in ("mountA", "mountB") \
                    and sA != sB:
                d = self.true_distance_m()
                frac = S_ACTIVE / (ALPHA_SPHERE * 4.0 * math.pi * d * d)
                new = [tr.I_amb + tr.R_ph * P_lt[1] * frac,
                       tr.I_amb + tr.R_ph * P_lt[0] * frac]
            else:
                new = [tr.I_amb, tr.I_amb]
            if max(abs(new[0] - iph[0]), abs(new[1] - iph[1])) < 1e-12:
                iph = new
                break
            iph = new

        nl, uf, led_nodes = res

        def g(t):
            return "N" + uf.find(t)

        self.I_led = Iled
        self.P_light = P_lt
        self.P_elec = P_el
        self.P_junc = Pj

        # ---- meter values -------------------------------------------------
        for k in (1, 2, 3):
            m = self.meters[k - 1]
            hi, lo = g("M%d.HI" % k), g("M%d.LO" % k)
            dv = nl.vnode(hi) - nl.vnode(lo)
            if m.mode == "OFF":
                m.value = None
            elif m.mode == "VDC":
                m.value = dv
            elif m.mode == "ADC":
                if not m.fuse_ok:
                    m.value = 0.0
                else:
                    cur = dv / m.shunt()
                    m.value = cur
                    rname = m.range if m.range != "AUTO" else m._auto_adc_range()
                    if ADC_FUSED.get(rname, True) and abs(cur) > FUSE_RATING:
                        m.fuse_ok = False
                        self.note("멀티미터 %d 의 퓨즈가 끊어졌습니다." % k,
                                  "the fuse of multimeter %d has blown" % k)
            elif m.mode == "OHM":
                rname = m.range if m.range != "AUTO" else self._auto_ohm(m)
                it = OHM_ITEST.get(rname, 1e-5)
                if abs(dv) > OHM_COMPLIANCE or dv < -1e-6:
                    m.value = None
                else:
                    m.value = dv / it
            elif m.mode == "DIODE":
                m.value = dv if 0.0 <= dv <= 3.2 else None

        if dt <= 0.0:
            self._update_manometer()
            return

        # ---- heat balance --------------------------------------------------
        Tamb = self._ambient()
        Pheat = [0.0, 0.0]
        for i in (1, 2):
            b = i - 1
            if not self.board_slot(i):
                self.board_T[b] = Tamb
                continue
            p = 0.0
            r1 = tr.R1_of(b, self.board_T[b])
            dv = nl.vnode(g("B%d.3" % i)) - nl.vnode(g("B%d.6" % i))
            p += dv * dv / r1
            rt = thermistor_R(self.board_T[b]) * 1000.0 * (1.0 + tr.th_tol)
            dv = nl.vnode(g("B%d.4" % i)) - nl.vnode(g("B%d.5" % i))
            p += dv * dv / rt
            p += max(0.0, P_el[b] - P_lt[b])
            Pheat[b] = p
        self.P_heat = Pheat

        for b in (0, 1):
            i = b + 1
            slot = self.board_slot(i)
            if slot is None:
                continue
            if slot in ("bottle1", "bottle2"):
                bb = int(slot[-1]) - 1
                Tenv = self.air_T[bb]
            else:
                Tenv = Tamb
            dT = (Pheat[b] - tr.G_board * (self.board_T[b] - Tenv)) / tr.C_board
            self.board_T[b] += dT * dt
            if self.board_T[b] > 480.0:
                self.board_T[b] = 480.0
            # over-current life time
            if abs(self.I_led[b]) > 1.0 and not self.led_dead[b]:
                self._warned = getattr(self, "_warned", [0.0, 0.0])
                if self.time - self._warned[b] > 60.0:
                    self._warned[b] = self.time
                    self.note("주의: LED %d 의 전류가 1 A 를 넘었습니다." % i,
                              "warning: current through LED %d exceeds 1 A" % i)
            if abs(self.I_led[b]) > tr.Imax_led:
                self.over_time[b] += dt
                if self.over_time[b] > 1.5 and not self.led_dead[b]:
                    self.led_dead[b] = True
                    self.note("LED %d 이 과전류로 파괴되었습니다!" % i,
                              "LED %d destroyed by over-current!" % i)
            else:
                self.over_time[b] = max(0.0, self.over_time[b] - 0.5 * dt)

        for bb in (0, 1):
            qin = 0.0
            for i in (1, 2):
                if self.board_slot(i) == "bottle%d" % (bb + 1):
                    qin += tr.G_board * (self.board_T[i - 1] - self.air_T[bb])
            gb = tr.G_bottle * tr.bottle_spread[bb]
            dT = (qin - gb * (self.air_T[bb] - Tamb)) / tr.C_bottle
            self.air_T[bb] += dT * dt
        self.time += dt
        self._update_manometer()

    # ------------------------------------------------------------ manometer
    def _gas_p(self, b, dV):
        """Pressure of the trapped air of bottle b when its volume grows dV."""
        s = self.sealed[b]
        if s is None:
            return self.truth.p_atm
        V = s["V"] + dV
        if V <= 1e-6:
            V = 1e-6
        return s["p"] * (s["V"] / V) * (self.air_T[b] / s["T"])

    def _update_manometer(self):
        tr = self.truth
        h0 = self.water_level0_mm()
        if "utube" not in self.placed or self.water_ml <= 0.0:
            self._h_left = self._h_right = h0
            return
        left_b = 0 if "tube1" in self.placed else None
        right_b = 1 if "tube2" in self.placed else None
        if left_b is None and right_b is None:
            self._h_left = self._h_right = h0
            return
        A = tr.A_tube

        def f(x):
            pl = self._gas_p(left_b, +A * x) if left_b is not None else tr.p_atm
            pr = self._gas_p(right_b, -A * x) if right_b is not None else tr.p_atm
            return pl - pr - 2.0 * RHO_W * G_ACC * x

        x = 0.0
        for _ in range(60):
            fx = f(x)
            dx = 1e-6
            der = (f(x + dx) - fx) / dx
            if abs(der) < 1e-9:
                break
            step = -fx / der
            if step > 0.02:
                step = 0.02
            if step < -0.02:
                step = -0.02
            x += step
            if abs(step) < 1e-9:
                break
        xm = x * 1000.0
        lim = min(h0 - 3.0, TUBE_ARM_MM - h0 - 3.0)
        if abs(xm) > max(lim, 0.0):
            self.water_spilled = True
            xm = math.copysign(max(lim, 0.0), xm)
        self._h_left = h0 - xm
        self._h_right = h0 + xm

    # ---------------------------------------------------------------- clock
    def advance(self, seconds, dt=4.0):
        if seconds <= 0.0:
            self._step(0.0)
            return
        n = max(1, int(math.ceil(seconds / dt)))
        h = seconds / n
        for _ in range(n):
            self._step(h)


# ==========================================================================
#  Graphical user interface
# ==========================================================================
try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except Exception:                                     # pragma: no cover
    tk = None

BG = "#12161c"
PANEL = "#1b222b"
INK = "#e8edf3"
DIM = "#8ea0b5"
ACC = "#4fb3ff"
PCB = "#1f6b45"
PCB2 = "#175236"
WIRE_COLORS = ["#e04b4b", "#f0c419", "#4fb3ff", "#7bd77b", "#d78ad7",
               "#f09a3e", "#9ad7d7", "#cfcfcf"]

TERM_COLORS = {1: "#d63b3b", 2: "#1b1b1b", 3: "#e3c318",
               4: "#9aa3ad", 5: "#9aa3ad", 6: "#e3c318"}


def _rr(cv, x0, y0, x1, y1, r, **kw):
    """Rounded rectangle."""
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


class App(object):
    def __init__(self, root, seed=None):
        self.root = root
        self.rig = Rig(seed)
        self.speed = 1
        self.running = True
        self.sel_part = None
        self.drag_ghost = None
        self.term_pos = {}
        self.sel_term = None
        self.cursor_mm = [140.0, 160.0]
        self.drag_cursor = None
        self.pot_box = [(0, 0, 0, 0), (0, 0, 0, 0)]
        self.psu_box = (0, 0, 0, 0)
        self.ux0, self.ux1 = self.UX_L, self.UX_R
        root.title("HaslaLab \u00b7 EuPhO 2017 Experiment \u00b7 " +
                   T("발광 다이오드", "Light-emitting diode"))
        root.configure(bg=BG)
        self._build_ui()
        self._tick()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        top = tk.Frame(self.root, bg=PANEL)
        top.pack(side="top", fill="x")
        tk.Label(top, text="EuPhO 2017 \u2013 " +
                 T("실험: 발광 다이오드", "Experiment: Light-emitting diode"),
                 bg=PANEL, fg=INK, font=("TkDefaultFont", 13, "bold")).pack(
                     side="left", padx=10, pady=6)
        self.lbl_clock = tk.Label(top, text="", bg=PANEL, fg=ACC,
                                  font=("TkFixedFont", 11))
        self.lbl_clock.pack(side="left", padx=16)
        tk.Label(top, text=T("시간 배속", "time \u00d7"), bg=PANEL,
                 fg=DIM).pack(side="left")
        self.var_speed = tk.StringVar(value="1")
        sp = ttk.Combobox(top, textvariable=self.var_speed, width=5,
                          state="readonly",
                          values=["1", "10", "60", "300", "1000"])
        sp.pack(side="left", padx=4)
        sp.bind("<<ComboboxSelected>>",
                lambda e: setattr(self, "speed", int(self.var_speed.get())))
        self.btn_run = tk.Button(top, text=T("일시정지", "pause"),
                                 command=self._toggle_run, width=9)
        self.btn_run.pack(side="left", padx=6)
        tk.Label(top, text="seed %d" % self.rig.truth.seed, bg=PANEL,
                 fg=DIM).pack(side="right", padx=10)

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True)
        self.tab_asm = tk.Frame(self.nb, bg=BG)
        self.tab_bench = tk.Frame(self.nb, bg=BG)
        self.nb.add(self.tab_asm, text=T("  조립  ", "  Assembly  "))
        self.nb.add(self.tab_bench, text=T("  실험대  ", "  Bench  "))
        self._build_assembly()
        self._build_bench()

        self.status = tk.Label(self.root, text="", bg=PANEL, fg="#ffcf6b",
                               anchor="w")
        self.status.pack(side="bottom", fill="x")

    def _toggle_run(self):
        self.running = not self.running
        self.btn_run.config(text=T("계속", "run") if not self.running
                            else T("일시정지", "pause"))

    # ------------------------------------------------------------ assembly
    def _build_assembly(self):
        f = self.tab_asm
        self.cv_asm = tk.Canvas(f, bg=BG, highlightthickness=0,
                                width=1060, height=640)
        self.cv_asm.pack(side="left", fill="both", expand=True)
        self.cv_asm.bind("<ButtonPress-1>", self._asm_press)
        self.cv_asm.bind("<B1-Motion>", self._asm_motion)
        self.cv_asm.bind("<ButtonRelease-1>", self._asm_release)
        self.cv_asm.bind("<Button-3>", self._asm_right)

        p = tk.Frame(f, bg=PANEL, width=250)
        p.pack(side="right", fill="y")
        p.pack_propagate(False)
        tk.Label(p, text=T("물 (주사기)", "water (syringe)"), bg=PANEL,
                 fg=INK, font=("TkDefaultFont", 11, "bold")).pack(pady=(12, 2))
        self.lbl_water = tk.Label(p, text="", bg=PANEL, fg=ACC,
                                  font=("TkFixedFont", 12))
        self.lbl_water.pack()
        row = tk.Frame(p, bg=PANEL)
        row.pack(pady=4)
        for txt, dv in (("-0.5", -0.5), ("-0.1", -0.1),
                        ("+0.1", 0.1), ("+0.5", 0.5)):
            tk.Button(row, text=txt, width=4,
                      command=lambda d=dv: self._water(d)).pack(side="left")
        tk.Label(p, text=T(
            "· 부품을 끌어다 자리에 놓으시오\n"
            "· 놓인 부품을 오른쪽 클릭하면\n  다시 부품 상자로 돌아갑니다\n"
            "· 병에 마개를 끼우는 순간\n  공기가 갇힙니다",
            "\u00b7 drag a part onto a slot\n"
            "\u00b7 right-click a placed part to\n  return it to the box\n"
            "\u00b7 the air is trapped the moment\n  the cap is fitted"),
            bg=PANEL, fg=DIM, justify="left").pack(pady=14, padx=8)
        self.lst_msg = tk.Text(p, height=14, bg="#0e1219", fg=DIM,
                               relief="flat", wrap="word")
        self.lst_msg.pack(fill="both", expand=True, padx=6, pady=6)

    def _water(self, d):
        self.rig.add_water(d)

    ASM_SLOTS = {
        "bottle1": (60, 300, 150, 90), "cap1": (60, 210, 150, 60),
        "tube1": (60, 150, 150, 46),
        "bottle2": (240, 300, 150, 90), "cap2": (240, 210, 150, 60),
        "tube2": (240, 150, 150, 46),
        "stand": (450, 380, 160, 70), "utube": (450, 300, 160, 66),
        "scale": (450, 220, 160, 66),
        "bench1": (660, 130, 160, 70), "bench2": (660, 215, 160, 70),
        "mountA": (660, 330, 160, 70), "mountB": (660, 415, 160, 70),
    }

    def _asm_slot_at(self, x, y):
        for sid, (sx, sy, w, h) in self.ASM_SLOTS.items():
            if sx <= x <= sx + w and sy <= y <= sy + h:
                return sid
        return None

    def _part_box_pos(self):
        pos = {}
        x, y = 30, 40
        for i, p in enumerate(self.rig.free_parts):
            pos[p] = (x + (i % 8) * 122, y + (i // 8) * 60)
        return pos

    def _asm_press(self, e):
        pos = self._part_box_pos()
        for p, (x, y) in pos.items():
            if x <= e.x <= x + 114 and y <= e.y <= y + 52:
                self.sel_part = p
                self.drag_ghost = (e.x, e.y)
                return
        self.sel_part = None

    def _asm_motion(self, e):
        if self.sel_part:
            self.drag_ghost = (e.x, e.y)

    def _asm_release(self, e):
        if not self.sel_part:
            return
        sid = self._asm_slot_at(e.x, e.y)
        if sid:
            self.rig.place(self.sel_part, sid)
        self.sel_part = None
        self.drag_ghost = None

    def _asm_right(self, e):
        sid = self._asm_slot_at(e.x, e.y)
        if sid and sid in self.rig.placed:
            self.rig.remove(self.rig.placed[sid])

    def _draw_assembly(self):
        cv = self.cv_asm
        cv.delete("all")
        cv.create_text(30, 14, anchor="w", fill=INK,
                       text=T("부품 상자", "parts box"),
                       font=("TkDefaultFont", 11, "bold"))
        for p, (x, y) in self._part_box_pos().items():
            _rr(cv, x, y, x + 114, y + 52, 8, fill="#243040",
                outline="#3a4a60")
            self._icon(cv, x, y + 2, 114, 32, p)
            cv.create_text(x + 57, y + 42, fill=INK, text=self._part_name(p),
                           font=("TkDefaultFont", 9))
        cv.create_line(20, 128, 1040, 128, fill="#2a3542")
        groups = [(T("병 1", "bottle 1"), 60), (T("병 2", "bottle 2"), 240),
                  (T("스탠드 / 마노미터", "stand / manometer"), 450),
                  (T("실험대 · 대향 거치", "bench \u00b7 facing rig"), 660)]
        for name, gx in groups:
            cv.create_text(gx, 140, anchor="w", fill=DIM, text=name)
        for sid, (x, y, w, h) in self.ASM_SLOTS.items():
            part = self.rig.placed.get(sid)
            fill = "#1d2a1f" if part else "#1a2028"
            cv.create_rectangle(x, y, x + w, y + h, outline="#3d4c5e",
                                dash=() if part else (4, 3), fill=fill)
            lab = T(SLOTS[sid][0], SLOTS[sid][1])
            cv.create_text(x + 6, y + 10, anchor="w", fill=DIM, text=lab,
                           font=("TkDefaultFont", 8))
            if part:
                self._icon(cv, x, y + 14, w, h - 34, part)
                cv.create_text(x + w / 2, y + h - 9, fill="#9ff09f",
                               text=self._part_name(part),
                               font=("TkDefaultFont", 9, "bold"))
        if self.rig.water_ml > 0 and "utube" in self.rig.placed:
            x, y, w, h = self.ASM_SLOTS["utube"]
            cv.create_text(x + w - 6, y + 10, anchor="e", fill=ACC,
                           text=T("물 %.1f mL", "water %.1f mL")
                           % self.rig.water_ml, font=("TkDefaultFont", 8))
        if self.sel_part and self.drag_ghost:
            x, y = self.drag_ghost
            _rr(cv, x - 55, y - 16, x + 55, y + 16, 8, fill="#37506e",
                outline=ACC)
            cv.create_text(x, y, fill=INK, text=self._part_name(self.sel_part))
        self.lbl_water.config(text="%.1f mL" % self.rig.water_ml)

    def _icon(self, cv, x, y, w, h, p):
        cx, cy = x + w / 2.0, y + h / 2.0
        if p.startswith("board"):
            cv.create_rectangle(cx - 26, cy - 13, cx + 26, cy + 13,
                                fill=PCB, outline=PCB2)
            cv.create_oval(cx - 20, cy - 6, cx - 8, cy + 6, fill="#ffe9a8",
                           outline="#c8b46a")
            cv.create_rectangle(cx + 2, cy - 5, cx + 18, cy + 5,
                                fill="#d9c7a0", outline="#8d7f63")
        elif p.startswith("cap"):
            cv.create_rectangle(cx - 16, cy - 9, cx + 16, cy + 9,
                                fill="#3a4756", outline="#6c7b8c")
            cv.create_line(cx, cy - 9, cx, cy - 16, fill="#7fd3ea", width=3)
        elif p.startswith("tube"):
            cv.create_line(cx - 26, cy + 8, cx - 6, cy - 8, cx + 10, cy + 8,
                           cx + 26, cy - 6, smooth=True, width=4,
                           fill="#7fd3ea")
        elif p == "utube":
            cv.create_line(cx - 14, cy - 12, cx - 14, cy + 10, cx + 14,
                           cy + 10, cx + 14, cy - 12, smooth=False, width=4,
                           fill="#7fd3ea")
        elif p == "scale":
            cv.create_rectangle(cx - 26, cy - 9, cx + 26, cy + 9,
                                fill="#f2efe2", outline="#b9b6a8")
            for k in range(-24, 25, 4):
                cv.create_line(cx + k, cy - 9, cx + k, cy - 2, fill="#c48b8b")
        elif p == "stand":
            cv.create_line(cx, cy + 12, cx, cy - 12, width=4, fill="#8d99a8")
            cv.create_line(cx - 18, cy + 12, cx + 18, cy + 12, width=5,
                           fill="#8d99a8")
            cv.create_line(cx, cy - 8, cx + 18, cy - 8, width=3,
                           fill="#8d99a8")

    def _part_name(self, p):
        names = {
            "board1": T("회로 기판 1", "board 1"), "board2": T("회로 기판 2", "board 2"),
            "cap1": T("기밀 마개 1", "cap 1"), "cap2": T("기밀 마개 2", "cap 2"),
            "tube1": T("튜브 1", "tube 1"), "tube2": T("튜브 2", "tube 2"),
            "utube": T("U자관", "U-tube"), "scale": T("밀리미터 눈금", "mm scale"),
            "stand": T("스탠드", "stand"), "syringe": T("주사기", "syringe"),
            "bottle1": T("병 1", "bottle 1"), "bottle2": T("병 2", "bottle 2"),
        }
        return names.get(p, p)

    # --------------------------------------------------------------- bench
    def _build_bench(self):
        f = self.tab_bench
        self.cv = tk.Canvas(f, bg=BG, highlightthickness=0,
                            width=1030, height=640)
        self.cv.pack(side="left", fill="both", expand=True)
        self.cv.bind("<Button-1>", self._bench_click)
        self.cv.bind("<B1-Motion>", self._bench_drag)
        self.cv.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag_cursor", None))
        self.cv.bind("<Button-3>", self._bench_right)
        self.cv.bind("<MouseWheel>", self._bench_wheel)
        self.cv.bind("<Button-4>", lambda e: self._bench_wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self._bench_wheel(e, -1))

        p = tk.Frame(f, bg=PANEL, width=290)
        p.pack(side="right", fill="y")
        p.pack_propagate(False)

        def hdr(t):
            tk.Label(p, text=t, bg=PANEL, fg=INK, anchor="w",
                     font=("TkDefaultFont", 10, "bold")).pack(
                         fill="x", padx=8, pady=(10, 2))

        hdr(T("전원 공급 장치", "power supply"))
        r1 = tk.Frame(p, bg=PANEL)
        r1.pack(fill="x", padx=8)
        self.var_psu = tk.IntVar(value=0)
        tk.Checkbutton(r1, text="ON", variable=self.var_psu, bg=PANEL, fg=INK,
                       selectcolor=PANEL, activebackground=PANEL,
                       command=lambda: self.rig.set_psu(on=self.var_psu.get())
                       ).pack(side="left")
        self.var_v = tk.StringVar(value="0.00")
        e = tk.Entry(r1, textvariable=self.var_v, width=7, justify="right")
        e.pack(side="left", padx=6)
        self._ent_v = e
        e.bind("<Return>", lambda ev: self._psu_set())
        tk.Label(r1, text="V", bg=PANEL, fg=DIM).pack(side="left")
        r2 = tk.Frame(p, bg=PANEL)
        r2.pack(fill="x", padx=8, pady=2)
        for txt, d in (("--", -0.5), ("-", -0.05), ("+", 0.05), ("++", 0.5)):
            tk.Button(r2, text=txt, width=3,
                      command=lambda dd=d: self._psu_bump(dd)).pack(side="left")

        hdr(T("가변저항 (10회전, 0\u20131000)", "potentiometers (10-turn)"))
        self.var_pot = []
        for j in (0, 1):
            rr = tk.Frame(p, bg=PANEL)
            rr.pack(fill="x", padx=8, pady=1)
            tk.Label(rr, text="P%d" % (j + 1), bg=PANEL, fg=DIM,
                     width=3).pack(side="left")
            v = tk.StringVar(value="500")
            self.var_pot.append(v)
            tk.Label(rr, textvariable=v, bg="#0e1219", fg=ACC, width=6,
                     font=("TkFixedFont", 11)).pack(side="left", padx=4)
            for txt, d in (("---", -0.05), ("--", -0.01), ("-", -0.002),
                           ("+", 0.002), ("++", 0.01), ("+++", 0.05)):
                tk.Button(rr, text=txt, width=2, padx=0,
                          command=lambda jj=j, dd=d: self._pot_bump(jj, dd)
                          ).pack(side="left")

        hdr(T("멀티미터", "multimeters"))
        self.var_mode, self.var_rng = [], []
        for k in (0, 1, 2):
            rr = tk.Frame(p, bg=PANEL)
            rr.pack(fill="x", padx=8, pady=1)
            nm = "M%d" % (k + 1)
            if k == 2:
                nm += T(" (전압전용)", " (V only)")
            tk.Label(rr, text=nm, bg=PANEL, fg=DIM, width=10,
                     anchor="w").pack(side="left")
            vm = tk.StringVar(value="OFF")
            vr = tk.StringVar(value="AUTO")
            self.var_mode.append(vm)
            self.var_rng.append(vr)
            cm = ttk.Combobox(rr, textvariable=vm, width=6, state="readonly",
                              values=self.rig.meters[k].modes())
            cm.pack(side="left")
            cm.bind("<<ComboboxSelected>>",
                    lambda ev, kk=k: self._meter_mode(kk))
            cr = ttk.Combobox(rr, textvariable=vr, width=7, state="readonly",
                              values=["AUTO"])
            cr.pack(side="left", padx=3)
            cr.bind("<<ComboboxSelected>>",
                    lambda ev, kk=k: self.rig.set_meter(
                        kk, rng=self.var_rng[kk].get()))
            setattr(self, "cbr%d" % k, cr)
        tk.Button(p, text=T("퓨즈 교체 (남은 개수 표시)", "replace fuse"),
                  command=self._replace_fuse).pack(fill="x", padx=8, pady=3)

        hdr(T("대향 거치 간격", "facing distance"))
        rr = tk.Frame(p, bg=PANEL)
        rr.pack(fill="x", padx=8)
        self.var_dist = tk.StringVar(value="30")
        tk.Entry(rr, textvariable=self.var_dist, width=6,
                 justify="right").pack(side="left")
        tk.Label(rr, text="mm", bg=PANEL, fg=DIM).pack(side="left")
        tk.Button(rr, text=T("설정", "set"),
                  command=self._set_dist).pack(side="left", padx=6)

        hdr(T("시간 보내기", "let time pass"))
        rr = tk.Frame(p, bg=PANEL)
        rr.pack(fill="x", padx=8)
        for txt, s in ((T("1분", "1 min"), 60), (T("5분", "5 min"), 300),
                       (T("10분", "10 min"), 600)):
            tk.Button(rr, text=txt, width=6,
                      command=lambda ss=s: self.rig.advance(ss)).pack(side="left")
        tk.Button(p, text=T("모든 케이블 제거", "remove all cables"),
                  command=lambda: self.rig.clear_cables()).pack(
                      fill="x", padx=8, pady=(8, 2))
        self.txt_log = tk.Text(p, height=10, bg="#0e1219", fg="#ffcf6b",
                               relief="flat", wrap="word")
        self.txt_log.pack(fill="both", expand=True, padx=6, pady=6)

    # ------------------------------------------------------------ controls
    def _psu_set(self):
        try:
            self.rig.set_psu(volts=float(self.var_v.get()))
        except ValueError:
            pass
        self.var_v.set("%.2f" % self.rig.psu_V)

    def _psu_bump(self, d):
        self.rig.set_psu(volts=self.rig.psu_V + d)
        self.var_v.set("%.2f" % self.rig.psu_V)

    def _pot_bump(self, j, d):
        self.rig.set_pot(j, self.rig.pot[j] + d)

    def _meter_mode(self, k):
        self.rig.set_meter(k, mode=self.var_mode[k].get())
        cb = getattr(self, "cbr%d" % k)
        cb.config(values=self.rig.meters[k].range_names())
        self.var_rng[k].set("AUTO")

    def _replace_fuse(self):
        for k in (0, 1, 2):
            if not self.rig.meters[k].fuse_ok:
                self.rig.replace_fuse(k)
                return

    def _set_dist(self):
        try:
            self.rig.set_distance(float(self.var_dist.get()))
        except ValueError:
            pass
        self.var_dist.set("%.0f" % self.rig.dist_set_mm)

    # ------------------------------------------------------- bench events
    def _term_at(self, x, y):
        best, bd = None, 1e9
        for t, (tx, ty) in self.term_pos.items():
            d = (tx - x) ** 2 + (ty - y) ** 2
            if d < bd:
                best, bd = t, d
        if bd <= 121:
            return best
        return None

    def _bench_click(self, e):
        if self.rig.manometer_ready():
            for i in (0, 1):
                y = self._mm_to_y(self.cursor_mm[i])
                if self.ux0 - 30 <= e.x <= self.ux1 + 30 and abs(e.y - y) < 7:
                    self.drag_cursor = i
                    return
        t = self._term_at(e.x, e.y)
        if t is None:
            self.sel_term = None
            return
        if self.sel_term is None:
            self.sel_term = t
        elif self.sel_term == t:
            self.sel_term = None
        else:
            self.rig.connect(self.sel_term, t)
            self.sel_term = None

    def _bench_drag(self, e):
        if self.drag_cursor is not None:
            self.cursor_mm[self.drag_cursor] = max(
                0.0, min(TUBE_ARM_MM, self._y_to_mm(e.y)))

    def _bench_right(self, e):
        t = self._term_at(e.x, e.y)
        if t:
            self.rig.cables = [c for c in self.rig.cables if t not in c]
            self.sel_term = None

    def _bench_wheel(self, e, direction=None):
        if direction is None:
            direction = 1 if e.delta > 0 else -1
        step = 0.002
        try:
            if e.state & 0x0001:
                step = 0.0002
        except Exception:
            pass
        for j in (0, 1):
            if self.pot_box[j][0] <= e.x <= self.pot_box[j][2] and \
                    self.pot_box[j][1] <= e.y <= self.pot_box[j][3]:
                self.rig.set_pot(j, self.rig.pot[j] + direction * step)
                return
        if self.psu_box[0] <= e.x <= self.psu_box[2] and \
                self.psu_box[1] <= e.y <= self.psu_box[3]:
            self.rig.set_psu(volts=self.rig.psu_V + direction * 0.05)
            self.var_v.set("%.2f" % self.rig.psu_V)

    # ---------------------------------------------------------- geometry
    UX_L, UX_R = 700.0, 790.0
    UY0, UY1 = 430.0, 30.0            # 0 mm and 300 mm
    PXMM = (430.0 - 30.0) / TUBE_ARM_MM

    def _mm_to_y(self, mm):
        return self.UY0 - mm * self.PXMM

    def _y_to_mm(self, y):
        return (self.UY0 - y) / self.PXMM

    # ------------------------------------------------------------ drawing
    def _post(self, x, y, name, color="#c8c8c8", label=None, r=6):
        cv = self.cv
        act = (self.sel_term == name)
        cv.create_oval(x - r - 2, y - r - 2, x + r + 2, y + r + 2,
                       fill="#0d1117", outline=ACC if act else "#39485c",
                       width=2 if act else 1)
        cv.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="#20272f")
        self.term_pos[name] = (x, y)
        if label:
            cv.create_text(x + r + 5, y, anchor="w", fill=DIM, text=label,
                           font=("TkDefaultFont", 7))

    def _board_terms(self, i, x, y, dy=17):
        for k in range(1, 7):
            self._post(x, y + (k - 1) * dy, "B%d.%d" % (i, k),
                       TERM_COLORS[k], str(k), r=5)

    def _draw_board(self, x, y, w, h, i, label=True):
        cv = self.cv
        b = i - 1
        _rr(cv, x, y, x + w, y + h, 6, fill=PCB, outline=PCB2, width=2)
        for gx in range(int(x) + 10, int(x + w) - 6, 14):
            cv.create_line(gx, y + 6, gx, y + h - 6, fill=PCB2)
        # LED with dome + leads
        lx, ly = x + w * 0.30, y + h * 0.42
        pl = self.rig.P_light[b]
        if pl > 1e-4 and not self.rig.led_dead[b]:
            gl = min(1.0, (pl / 0.5) ** 0.4)
            for k, rr in enumerate((26, 19, 13)):
                shade = int(60 + 150 * gl * (1.0 - k * 0.15))
                col = "#%02x%02x%02x" % (min(255, shade + 60),
                                         min(255, shade + 40), 60)
                cv.create_oval(lx - rr, ly - rr, lx + rr, ly + rr,
                               outline="", fill=col, stipple="gray25")
        cv.create_oval(lx - 9, ly - 9, lx + 9, ly + 9,
                       fill="#8b1c1c" if self.rig.led_dead[b] else "#ffe9a8",
                       outline="#c8b46a")
        cv.create_arc(lx - 9, ly - 9, lx + 9, ly + 9, start=200, extent=140,
                      style="arc", outline="#fff6d0")
        cv.create_line(lx - 4, ly + 9, lx - 4, ly + 20, fill="#c9c9c9", width=2)
        cv.create_line(lx + 4, ly + 9, lx + 4, ly + 18, fill="#c9c9c9", width=2)
        cv.create_text(lx, ly - 16, fill="#dfe8ef", text="LED",
                       font=("TkDefaultFont", 7))
        # heater resistor R1 (axial, colour bands)
        rx, ry = x + w * 0.66, y + h * 0.30
        cv.create_line(rx - 22, ry, rx + 22, ry, fill="#c9c9c9", width=2)
        _rr(cv, rx - 14, ry - 7, rx + 14, ry + 7, 5, fill="#d9c7a0",
            outline="#8d7f63")
        for k, c in enumerate(("#3b2a1a", "#1b1b1b", "#b04a2a")):
            cv.create_line(rx - 8 + k * 7, ry - 7, rx - 8 + k * 7, ry + 7,
                           fill=c, width=3)
        cv.create_text(rx, ry - 14, fill="#dfe8ef", text="R\u2081",
                       font=("TkDefaultFont", 7))
        # thermistor bead
        tx2, ty2 = x + w * 0.66, y + h * 0.70
        cv.create_line(tx2 - 16, ty2, tx2 + 16, ty2, fill="#c9c9c9", width=2)
        cv.create_oval(tx2 - 7, ty2 - 6, tx2 + 7, ty2 + 6, fill="#2c2c2c",
                       outline="#6a6a6a")
        cv.create_text(tx2, ty2 - 13, fill="#dfe8ef", text="R\u209c",
                       font=("TkDefaultFont", 7))
        if label:
            cv.create_text(x + w - 6, y + h - 8, anchor="e", fill="#bfe6cf",
                           text=T("기판 %d", "board %d") % i,
                           font=("TkDefaultFont", 8))

    def _draw_bottle(self, x, y, w, h, b):
        cv = self.cv
        i = b + 1
        capped = ("cap%d" % i) in self.rig.placed
        tubed = ("tube%d" % i) in self.rig.placed
        neck = w * 0.34
        pts = [x + w / 2 - neck / 2, y, x + w / 2 + neck / 2, y,
               x + w / 2 + neck / 2, y + 22, x + w - 4, y + 52,
               x + w, y + 70, x + w, y + h - 14, x + w - 14, y + h,
               x + 14, y + h, x, y + h - 14, x, y + 70,
               x + 4, y + 52, x + w / 2 - neck / 2, y + 22]
        cv.create_polygon(pts, fill="#16303a", outline="#4a7f92", width=2)
        cv.create_line(x + 8, y + 80, x + 8, y + h - 20, fill="#5f9bb0")
        if capped:
            cv.create_rectangle(x + w / 2 - neck / 2 - 4, y - 14,
                                x + w / 2 + neck / 2 + 4, y + 4,
                                fill="#3a4756", outline="#6c7b8c")
            if tubed:
                cv.create_line(x + w / 2, y - 14, x + w / 2, y - 30,
                               fill="#7fd3ea", width=4)
        for s, p in self.rig.placed.items():
            if s == "bottle%d" % i and p.startswith("board"):
                bi = int(p[-1])
                self._draw_board(x + 14, y + h - 96, w - 28, 78, bi,
                                 label=False)
                cv.create_text(x + w / 2, y + h - 8, fill="#bfe6cf",
                               text=T("기판 %d", "board %d") % bi,
                               font=("TkDefaultFont", 8))
        cv.create_text(x + w / 2, y + h + 14, fill=DIM,
                       text=T("병 %d", "bottle %d") % i)

    def _draw_utube(self):
        cv = self.cv
        L, R = self.UX_L, self.UX_R
        y0, y1 = self.UY0, self.UY1
        self.ux0, self.ux1 = L, R
        if "utube" not in self.rig.placed:
            cv.create_text((L + R) / 2, (y0 + y1) / 2, fill=DIM,
                           text=T("U자관 없음", "no U-tube"))
            return
        for cx in (L, R):
            cv.create_rectangle(cx - 8, y1, cx + 8, y0 + 16,
                                outline="#6f8798", width=2, fill="#0e141b")
        cv.create_rectangle(L - 8, y0, R + 8, y0 + 16, outline="#6f8798",
                            width=2, fill="#0e141b")
        hl, hr = self.rig._h_left, self.rig._h_right
        if self.rig.water_ml > 0:
            for cx, hh in ((L, hl), (R, hr)):
                yy = self._mm_to_y(max(0.0, hh))
                cv.create_rectangle(cx - 7, yy, cx + 7, y0 + 15,
                                    fill="#2b7fd0", outline="")
                cv.create_oval(cx - 7, yy - 4, cx + 7, yy + 4,
                               fill="#57a8ef", outline="")
            cv.create_rectangle(L - 7, y0 + 1, R + 7, y0 + 15,
                                fill="#2b7fd0", outline="")
        # millimetre paper strip
        if "scale" in self.rig.placed:
            sx = (L + R) / 2
            cv.create_rectangle(sx - 26, y1 - 6, sx + 26, y0 + 6,
                                fill="#f2efe2", outline="#b9b6a8")
            for mm in range(0, int(TUBE_ARM_MM) + 1, 2):
                yy = self._mm_to_y(mm)
                if mm % 50 == 0:
                    cv.create_line(sx - 26, yy, sx + 26, yy, fill="#a03b3b")
                    cv.create_text(sx, yy - 6, text=str(mm), fill="#7a3030",
                                   font=("TkDefaultFont", 7))
                elif mm % 10 == 0:
                    cv.create_line(sx - 20, yy, sx + 20, yy, fill="#c48b8b")
                else:
                    cv.create_line(sx - 8, yy, sx + 8, yy, fill="#ddd0d0")
            for i in (0, 1):
                yy = self._mm_to_y(self.cursor_mm[i])
                col = "#ff9f43" if i == 0 else "#4fe0a0"
                cv.create_line(L - 26, yy, R + 34, yy, fill=col, width=2)
                cv.create_text(R + 38, yy, anchor="w", fill=col,
                               text="%d mm" % round(self.cursor_mm[i]),
                               font=("TkFixedFont", 9))
            d = abs(self.cursor_mm[0] - self.cursor_mm[1])
            cv.create_text((L + R) / 2, y1 - 18, fill=INK,
                           text=T("커서 간격  %d mm", "cursor gap  %d mm")
                           % round(d), font=("TkFixedFont", 10, "bold"))
        else:
            cv.create_text((L + R) / 2, y1 - 18, fill=DIM,
                           text=T("눈금자 없음", "no scale"))
        if self.rig.water_spilled:
            cv.create_text((L + R) / 2, y0 + 34, fill="#ff6b6b",
                           text=T("물이 밀려 나갔습니다!", "water pushed out!"))

    def _draw_meter(self, k, x, y, w=200, h=175):
        cv = self.cv
        m = self.rig.meters[k]
        _rr(cv, x, y, x + w, y + h, 10, fill="#2a3340", outline="#46586e",
            width=2)
        cv.create_text(x + 10, y + 12, anchor="w", fill=INK,
                       text="M%d%s" % (k + 1, T(" 전압전용", " V-only")
                                       if m.voltage_only else ""),
                       font=("TkDefaultFont", 9, "bold"))
        _rr(cv, x + 10, y + 24, x + w - 10, y + 74, 6, fill="#101c14",
            outline="#33513f")
        txt = m.display()
        cv.create_text(x + w - 22, y + 52, anchor="e", fill="#7dffb0",
                       text=txt if txt else "", font=("TkFixedFont", 20))
        cv.create_text(x + w - 16, y + 68, anchor="e", fill="#5fbd88",
                       text=m.display_unit(), font=("TkDefaultFont", 9))
        cv.create_text(x + 16, y + 68, anchor="w", fill="#5fbd88",
                       text="%s %s" % (m.mode, m.range),
                       font=("TkDefaultFont", 8))
        if not m.fuse_ok:
            cv.create_text(x + w / 2, y + 88, fill="#ff7b7b",
                           text=T("퓨즈 끊김", "FUSE BLOWN"),
                           font=("TkDefaultFont", 9, "bold"))
        self._post(x + 40, y + h - 24, "M%d.HI" % (k + 1), "#d63b3b",
                   "mAV\u03a9")
        self._post(x + 130, y + h - 24, "M%d.LO" % (k + 1), "#1b1b1b", "COM")

    def _draw_psu(self, x, y, w=160, h=175):
        cv = self.cv
        r = self.rig
        _rr(cv, x, y, x + w, y + h, 10, fill="#2a3340", outline="#46586e",
            width=2)
        cv.create_text(x + 10, y + 12, anchor="w", fill=INK,
                       text=T("전원 공급 장치", "power supply"),
                       font=("TkDefaultFont", 9, "bold"))
        _rr(cv, x + 10, y + 24, x + w - 10, y + 62, 6, fill="#101c14",
            outline="#33513f")
        cv.create_text(x + w - 18, y + 43, anchor="e", fill="#7dffb0",
                       text=("%.2f" % r.psu_V) if r.psu_on else "OFF",
                       font=("TkFixedFont", 16))
        cv.create_text(x + 18, y + 43, anchor="w", fill="#5fbd88", text="V")
        if r.psu_cc:
            cv.create_text(x + w / 2, y + 72, fill="#ffb454",
                           text=T("전류 제한", "current limit"),
                           font=("TkDefaultFont", 8))
        cv.create_text(x + w / 2, y + 92, fill=DIM,
                       text=T("빨강 = +, 검정 = \u2212", "red = +, black = \u2212"),
                       font=("TkDefaultFont", 8))
        self._post(x + 45, y + h - 26, "PSU.+", "#d63b3b", "+")
        self._post(x + 112, y + h - 26, "PSU.-", "#1b1b1b", "\u2212")
        self.psu_box = (x, y, x + w, y + h)

    def _draw_pot(self, j, x, y, w=100, h=175):
        cv = self.cv
        f = self.rig.pot[j]
        _rr(cv, x, y, x + w, y + h, 10, fill="#2a3340", outline="#46586e",
            width=2)
        cv.create_text(x + w / 2, y + 12, fill=INK, text="P%d" % (j + 1),
                       font=("TkDefaultFont", 9, "bold"))
        cx, cy, rr = x + w / 2, y + 58, 26
        cv.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, fill="#39465a",
                       outline="#6d8099", width=2)
        ang = math.radians(-135 + 270 * f)
        cv.create_line(cx, cy, cx + rr * 0.8 * math.sin(ang + math.pi / 2 * 0),
                       cy, fill="")
        cv.create_line(cx, cy, cx + rr * 0.82 * math.cos(ang - math.pi / 2),
                       cy + rr * 0.82 * math.sin(ang - math.pi / 2),
                       fill="#ffcf6b", width=3)
        cv.create_text(cx, y + 96, fill=ACC, text="%d" % round(f * 1000),
                       font=("TkFixedFont", 11))
        self._post(x + 18, y + h - 52, "P%d.A" % (j + 1), "#c8c8c8", "A")
        self._post(x + w - 18, y + h - 52, "P%d.B" % (j + 1), "#c8c8c8", "B")
        self._post(x + w / 2, y + h - 20, "P%d.W" % (j + 1), "#ffcf6b", "W")
        self.pot_box[j] = (x, y, x + w, y + h)

    def _draw_cables(self):
        cv = self.cv
        for idx, (a, b) in enumerate(self.rig.cables):
            if a not in self.term_pos or b not in self.term_pos:
                continue
            x1, y1 = self.term_pos[a]
            x2, y2 = self.term_pos[b]
            col = WIRE_COLORS[idx % len(WIRE_COLORS)]
            mx, my = (x1 + x2) / 2, max(y1, y2) + 16
            cv.create_line(x1, y1, mx, my, x2, y2, smooth=True, width=3,
                           fill=col, capstyle="round")

    def _draw_term_panel(self, x, y, w=300, h=140):
        cv = self.cv
        _rr(cv, x, y, x + w, y + h, 8, fill="#232b36", outline="#3d4c5e")
        cv.create_text(x + 8, y + 12, anchor="w", fill=DIM,
                       text=T("기판 단자대 (마개를 통해 나온 배선)",
                              "board terminal block (leads through the cap)"),
                       font=("TkDefaultFont", 8))
        for i in (1, 2):
            if not self.rig.board_slot(i):
                continue
            cx = x + 60 + (i - 1) * 150
            cv.create_text(cx, y + 32, fill=INK,
                           text=T("기판 %d", "board %d") % i,
                           font=("TkDefaultFont", 9, "bold"))
            for k in range(1, 7):
                px = cx - 45 + ((k - 1) % 3) * 45
                py = y + 58 + ((k - 1) // 3) * 40
                self._post(px, py, "B%d.%d" % (i, k), TERM_COLORS[k],
                           str(k), r=6)
            cv.create_text(cx, y + h - 12, fill=DIM,
                           text=T("1,2=LED  3,6=R\u2081  4,5=R\u209c",
                                  "1,2=LED  3,6=R\u2081  4,5=R\u209c"),
                           font=("TkDefaultFont", 7))

    def _draw_facing(self, x, y, w=310, h=145):
        cv = self.cv
        _rr(cv, x, y, x + w, y + h, 8, fill="#1a222c", outline="#3d4c5e")
        cv.create_text(x + 8, y + 12, anchor="w", fill=DIM,
                       text=T("대향 거치대 (LED 를 마주 보게)",
                              "facing mounts (LEDs face each other)"),
                       font=("TkDefaultFont", 8))
        d_px = max(24.0, min(150.0, self.rig.dist_set_mm * 2.2))
        cxm = x + w / 2
        for side, sgn in (("mountA", -1), ("mountB", +1)):
            bx = cxm + sgn * (d_px / 2 + 14)
            part = self.rig.placed.get(side)
            col = "#3a4756" if not part else PCB
            cv.create_rectangle(bx - 14 * (1 if sgn > 0 else 1), y + 40,
                                bx + 14, y + 118, fill=col, outline="#6c7b8c")
            cv.create_rectangle(bx - 14, y + 40, bx + 14, y + 118,
                                outline="#6c7b8c")
            cv.create_line(bx, y + 118, bx, y + h - 4, fill="#6c7b8c", width=3)
            if part:
                i = int(part[-1])
                lx = cxm + sgn * (d_px / 2)
                pl = self.rig.P_light[i - 1]
                if pl > 1e-4:
                    gl = min(1.0, (pl / 0.5) ** 0.4)
                    for rr in (22, 15, 9):
                        sh = int(90 + 140 * gl)
                        cv.create_oval(lx - rr, y + 75 - rr, lx + rr,
                                       y + 75 + rr, outline="",
                                       fill="#%02x%02x3c" % (min(255, sh + 60),
                                                             min(255, sh + 30)),
                                       stipple="gray25")
                cv.create_oval(lx - 7, y + 68, lx + 7, y + 82,
                               fill="#ffe9a8", outline="#c8b46a")
                cv.create_text(bx, y + 30, fill="#bfe6cf",
                               text=T("기판 %d", "board %d") % i,
                               font=("TkDefaultFont", 8))
        yy = y + 132
        cv.create_line(cxm - d_px / 2, yy, cxm + d_px / 2, yy, fill="#f2efe2",
                       arrow="both")
        for mmk in range(0, 220, 5):
            px = cxm - d_px / 2 + mmk * 2.2
            if px > cxm + d_px / 2:
                break
            cv.create_line(px, yy - 4 if mmk % 10 else yy - 7, px, yy,
                           fill="#cfc9b8")
        cv.create_text(cxm, yy - 14, fill="#f2efe2",
                       text=self.rig.read_ruler_distance(),
                       font=("TkFixedFont", 9))

    def _draw_bench(self):
        cv = self.cv
        cv.delete("all")
        self.term_pos = {}
        if not hasattr(self, "pot_box"):
            self.pot_box = [(0, 0, 0, 0), (0, 0, 0, 0)]
        self._draw_bottle(20, 40, 140, 240, 0)
        self._draw_bottle(180, 40, 140, 240, 1)
        for idx, sid in enumerate(("bench1", "bench2")):
            x, y = 340, 20 + idx * 130
            part = self.rig.placed.get(sid)
            if part:
                self._draw_board(x, y, 190, 118, int(part[-1]))
            else:
                cv.create_rectangle(x, y, x + 190, y + 118, dash=(4, 3),
                                    outline="#33414f")
                cv.create_text(x + 95, y + 59, fill="#44546a",
                               text=T(SLOTS[sid][0], SLOTS[sid][1]))
        self._draw_facing(340, 285)
        self._draw_term_panel(20, 300)
        self._draw_utube()
        self._draw_psu(10, 452)
        self._draw_pot(0, 180, 452)
        self._draw_pot(1, 288, 452)
        for k in (0, 1, 2):
            self._draw_meter(k, 398 + k * 208, 452)
        self._draw_cables()
        if self.sel_term:
            cv.create_text(515, 640, fill=ACC,
                           text=T("선택된 단자: %s  (다른 단자를 눌러 연결)",
                                  "selected: %s  (click another terminal)")
                           % self.sel_term)
        cv.create_text(1020, 640, anchor="e", fill=DIM,
                       text=T("여분 퓨즈 %d", "spare fuses %d")
                       % self.rig.spare_fuses, font=("TkDefaultFont", 8))

    # --------------------------------------------------------------- loop
    def _tick(self):
        if self.running:
            self.rig.advance(0.12 * self.speed,
                             dt=4.0 if self.speed > 20 else 0.5)
        else:
            self.rig.advance(0)
        for j in (0, 1):
            self.var_pot[j].set("%d" % round(self.rig.pot[j] * 1000))
        if self.root.focus_get() is not getattr(self, "_ent_v", None):
            self.var_v.set("%.2f" % self.rig.psu_V)
        self.var_psu.set(1 if self.rig.psu_on else 0)
        t = self.rig.time
        self.lbl_clock.config(text="t = %02d:%02d:%02d"
                              % (t // 3600, (t % 3600) // 60, t % 60))
        try:
            if self.nb.index(self.nb.select()) == 0:
                self._draw_assembly()
            else:
                self._draw_bench()
        except Exception as exc:                       # pragma: no cover
            self.status.config(text="draw error: %s" % exc)
        notes = self.rig.pop_notes()
        if notes:
            for n in notes:
                self.txt_log.insert("end", n + "\n")
                self.lst_msg.insert("end", n + "\n")
            self.txt_log.see("end")
            self.lst_msg.see("end")
            self.status.config(text=notes[-1])
        self.root.after(90, self._tick)


def main():
    global LANG
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
        elif a.startswith("--lang="):
            LANG = a.split("=", 1)[1].upper()
        elif a == "--official":
            seed = OFFICIAL_SEED
    if tk is None:
        print("Tkinter is not available.")
        return
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.0)
    except Exception:
        pass
    App(root, seed)
    root.mainloop()


if __name__ == "__main__":
    main()
