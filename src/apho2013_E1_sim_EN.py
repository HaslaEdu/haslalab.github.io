#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  14th Asian Physics Olympiad  (APhO 2013, Bogor - Indonesia)
  Experimental Question 1 :  WIND POWER AND ITS METROLOGIES
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  DESIGN RULES (do not violate)
   * The simulator only ever shows what a real instrument would show.
     No derived physical quantity (v, P_W, eta, tan(theta), C_D, n, c,
     b/a, TSR, ...) is ever computed or displayed for the student.
   * Every hidden "true" parameter is re-randomised each session.
   * Apparatus graphics are reconstructed from the official problem
     sheet photographs (Fig. 1, 4, 6, 8, 9, 10, 11, 12, 13).
   * Forward physical models only - no data replay.
=======================================================================
"""

import math
import random
import sys

# =====================================================================
#  0.  i18n
# =====================================================================
LANG = "en"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


# =====================================================================
#  1.  Given constants (printed on the problem sheet, page 2)
# =====================================================================
G_ACC = 9.81                 # m/s^2
RHO_A = 1.2                  # kg/m^3
D_BALL = 0.0395              # m   (39.5 +- 0.1 mm)
ALPHA_W = 4.5e-3             # 1/degC  (tungsten)
C1_TUNNEL = 0.0873           # m       v = 0.0873 * f_M      (Eq. 4)
R_BRIDGE = 10.0              # Ohm     the two 10 ohm bridge resistors
R_TURBINE_BLADE = 0.055      # m       swept radius of the turbine


# =====================================================================
#  2.  Hidden truth of one session
# =====================================================================
class Truth(object):
    """All hidden parameters.  Re-drawn for every session."""

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1, 10 ** 9)
        self.seed = seed
        rng = random.Random(seed)
        self.rng = rng

        # ---- wind tunnel -------------------------------------------
        # inner diameter, to be measured by the student with the ruler
        self.D_tunnel = rng.uniform(0.132, 0.138)          # m
        self.A0 = math.pi * (self.D_tunnel / 2.0) ** 2

        # ---- wind generator (computer fan + motor) ------------------
        # empirical fan characteristic  V = k2 f^2 + k1 f + k0
        # (fitted to the official APhO-2013 V-f data, then jittered)
        self.fan_k2 = 0.027070 * rng.uniform(0.94, 1.06)
        self.fan_k1 = -0.25702 * rng.uniform(0.92, 1.08)
        self.fan_k0 = 2.886 * rng.uniform(0.92, 1.08)
        self.fan_fmin = rng.uniform(6.2, 7.0)              # stall speed
        self.fan_Vmin = (self.fan_k2 * self.fan_fmin ** 2
                         + self.fan_k1 * self.fan_fmin + self.fan_k0)
        # mechanical efficiency  eta_M = eta0 * (v/1.7)^eps
        self.eta0 = rng.uniform(0.0245, 0.0335)
        self.eta_eps = rng.uniform(-0.045, 0.045)
        # below the start-up voltage the rotor is stalled: it buzzes and
        # draws a small current.  The stall resistance is chosen so that
        # the I(V) curve is continuous at V = fan_Vmin (this also keeps the
        # network iteration from chattering right at the threshold).
        _v0 = C1_TUNNEL * self.fan_fmin
        _PW0 = 0.5 * RHO_A * self.A0 * _v0 ** 3
        _I0 = (_PW0 / (self.eta0 * (_v0 / 1.7) ** self.eta_eps)) / self.fan_Vmin
        self.fan_Rstall = self.fan_Vmin / _I0

        # ---- ping-pong ball ----------------------------------------
        #   printed on the ball, in gram, one decimal
        self.m_ball = round(rng.uniform(2.35, 2.75), 1) * 1e-3      # kg
        self.A_ball = math.pi * D_BALL ** 2 / 4.0
        self.CD0 = rng.uniform(0.397, 0.443)     # drag coeff. at v = 1 m/s
        self.CD_gamma = rng.uniform(0.06, 0.22)  # weak Re dependence
        self.pend_h = rng.uniform(0.185, 0.215)  # thread length L, m

        # ---- hot wire ----------------------------------------------
        self.R0_wire = rng.uniform(6.2, 7.9)               # Ohm at T0
        I_runaway = rng.uniform(0.188, 0.200)              # A
        self.k_wire = I_runaway ** 2 * self.R0_wire        # k = a*A_w/alpha
        self.beta_wire = rng.uniform(1.20, 1.45)           # b/a
        self.c_wire = rng.uniform(0.748, 0.792)              # King's law power
        self.pot_max = 30.0                                # Ohm, CTA pot
        self.cca_Imax = 0.200                              # A, source range
        self.wire_burn_dT = 1100.0                         # degC -> destroyed

        # ---- wind turbine (small DC motor used as generator) --------
        self.A_turb = math.pi * R_TURBINE_BLADE ** 2
        self.R_M = rng.uniform(0.66, 0.86)                 # Ohm
        self.kT = rng.uniform(0.95e-3, 1.10e-3)            # V s / rad
        self.C_tau0 = rng.uniform(0.290, 0.340)
        self.lambda0 = rng.uniform(2.00, 2.40)
        self.v_start = rng.uniform(1.16, 1.34)             # m/s, static frict.
        # q  and  s  of  tau = q v^2 - s v omega - tau_f
        self.q_t = 0.5 * RHO_A * self.A_turb * R_TURBINE_BLADE * self.C_tau0
        self.s_t = self.q_t * R_TURBINE_BLADE / self.lambda0
        self.tau_f = self.q_t * self.v_start ** 2

        # ---- nichrome wire -----------------------------------------
        self.lam_R = rng.uniform(0.196, 0.222)             # Ohm / cm
        self.nic_len = 50.0                                # cm printed scale

        # ---- parasitics / instruments ------------------------------
        self.R_lead = rng.uniform(0.08, 0.13)              # per probe lead
        self.R_contact_nic = rng.uniform(0.003, 0.010)       # crocodile clips
        self.brush_dyn = rng.uniform(0.01, 0.04)           # seated brush
        self.brush_extra = rng.uniform(0.20, 0.40)         # static scatter
        self.T0 = rng.uniform(24.0, 28.0)                  # degC

    # -----------------------------------------------------------------
    #  wind generator
    # -----------------------------------------------------------------
    def fan_freq(self, V):
        """rotation frequency f_M (Hz) of the wind generator at voltage V"""
        if V < self.fan_Vmin:
            return 0.0
        a, b, c = self.fan_k2, self.fan_k1, self.fan_k0 - V
        disc = b * b - 4 * a * c
        if disc <= 0:
            return 0.0
        f = (-b + math.sqrt(disc)) / (2 * a)
        return max(self.fan_fmin, f)

    def wind_speed(self, f_M):
        return C1_TUNNEL * f_M

    def eta_M(self, v):
        if v <= 0:
            return self.eta0
        return self.eta0 * (v / 1.7) ** self.eta_eps

    def fan_current(self, V):
        """electrical current drawn by the wind generator at terminal V"""
        if V <= 0:
            return 0.0
        f = self.fan_freq(V)
        if f <= 0:                       # stalled rotor
            return V / self.fan_Rstall
        v = self.wind_speed(f)
        P_W = 0.5 * RHO_A * self.A0 * v ** 3
        P_M = P_W / self.eta_M(v)
        return P_M / V

    # -----------------------------------------------------------------
    #  ping-pong ball anemometer
    # -----------------------------------------------------------------
    def ball_tan_theta(self, v):
        if v <= 0:
            return 0.0
        CD = self.CD0 * v ** self.CD_gamma
        FD = 0.5 * CD * RHO_A * self.A_ball * v * v
        return FD / (self.m_ball * G_ACC)

    def ball_theta(self, v):
        return math.atan(self.ball_tan_theta(v))

    def ball_dx(self, v):
        """horizontal displacement of the ball centre, in metres"""
        return self.pend_h * math.sin(self.ball_theta(v))     # L sin(theta)

    def ball_drop(self, v):
        """vertical distance pivot -> ball centre, in metres"""
        return self.pend_h * math.cos(self.ball_theta(v))     # L cos(theta)

    # -----------------------------------------------------------------
    #  hot wire  (King's law forward model)
    # -----------------------------------------------------------------
    def G_wire(self, v):
        """G = (k/R0)(1 + (b/a) v^c)   [see D.1.1 / D.2.1]"""
        g = self.k_wire / self.R0_wire
        if v > 0:
            g *= (1.0 + self.beta_wire * v ** self.c_wire)
        return g

    def cta_Rw(self, V_inp, v):
        """steady state hot-wire resistance in the Wheatstone bridge.
           V_inp^2 * Rw/(Rw+RB)^2 = G(v) (Rw - R0)"""
        if V_inp <= 1e-9:
            return self.R0_wire
        G = self.G_wire(v)
        R0 = self.R0_wire

        def f(R):
            return V_inp ** 2 * R / (R + R_BRIDGE) ** 2 - G * (R - R0)

        lo, hi = R0 + 1e-9, R0 + 4000.0
        if f(hi) > 0:
            return hi
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if f(mid) > 0:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def cca_Rw(self, I, v):
        """R_w = G R0 /(G - I^2)   (thermal runaway when I^2 -> G)"""
        G = self.G_wire(v)
        d = G - I * I
        if d <= 1e-9:
            return 1e6
        return G * self.R0_wire / d

    def wire_dT(self, Rw):
        return (Rw - self.R0_wire) / (self.R0_wire * ALPHA_W)

    # -----------------------------------------------------------------
    #  wind turbine
    # -----------------------------------------------------------------
    def turbine_omega(self, v, R_load):
        """steady angular velocity of the turbine, rad/s.
           q v^2 - s v w - tau_f = kT^2 w /(R_M + R_load)"""
        drive = self.q_t * v * v - self.tau_f
        if drive <= 0:
            return 0.0
        if R_load is None:            # open circuit
            K = 0.0
        else:
            K = self.kT ** 2 / max(1e-6, (self.R_M + R_load))
        den = self.s_t * v + K
        if den <= 0:
            return 0.0
        w = drive / den
        lam_max = self.lambda0 * 0.999
        w = min(w, lam_max * v / R_TURBINE_BLADE)
        return w

    def turbine_emf(self, v, R_load):
        return self.kT * self.turbine_omega(v, R_load)

    # -----------------------------------------------------------------
    #  nichrome
    # -----------------------------------------------------------------
    def nichrome_R(self, l_cm):
        return self.lam_R * max(0.0, l_cm)


# =====================================================================
#  3.  Tiny resistive-network solver (Norton form, dense Gauss)
# =====================================================================
class Net(object):
    """Nodal analysis on a pure-conductance network.
       Sources are entered in Norton form, so the matrix stays SPD."""

    def __init__(self):
        self.n = 0
        self.idx = {}
        self.G = []
        self.I = []
        self._elems = []

    def node(self, name):
        if name not in self.idx:
            self.idx[name] = self.n
            self.n += 1
        return self.idx[name]

    def R(self, a, b, value):
        self._elems.append(("R", a, b, max(1e-9, value)))

    def V(self, a, b, volt, rs=0.05):
        """voltage source, + at a"""
        self._elems.append(("V", a, b, volt, max(1e-6, rs)))

    def I_src(self, a, b, amps, rout=1e7):
        """current source pushing `amps` out of node a into the net"""
        self._elems.append(("I", a, b, amps, rout))

    # ------------------------------------------------------------------
    def solve(self, ground=None):
        for e in self._elems:
            for nm in (e[1], e[2]):
                self.node(nm)
        n = self.n
        if n == 0:
            return {}
        G = [[0.0] * n for _ in range(n)]
        I = [0.0] * n
        for e in self._elems:
            if e[0] == "R":
                a, b, val = self.idx[e[1]], self.idx[e[2]], e[3]
                g = 1.0 / val
                G[a][a] += g
                G[b][b] += g
                G[a][b] -= g
                G[b][a] -= g
            elif e[0] == "V":
                a, b, volt, rs = self.idx[e[1]], self.idx[e[2]], e[3], e[4]
                g = 1.0 / rs
                G[a][a] += g
                G[b][b] += g
                G[a][b] -= g
                G[b][a] -= g
                I[a] += volt * g
                I[b] -= volt * g
            elif e[0] == "I":
                a, b, amps, rout = self.idx[e[1]], self.idx[e[2]], e[3], e[4]
                g = 1.0 / rout
                G[a][a] += g
                G[b][b] += g
                G[a][b] -= g
                G[b][a] -= g
                I[a] += amps
                I[b] -= amps
        # leak to ground everywhere (keeps the matrix non singular)
        for i in range(n):
            G[i][i] += 1e-12
        if ground is None:
            gi = 0
        else:
            gi = self.idx[ground]
        # ground the reference node
        for j in range(n):
            G[gi][j] = 0.0
        G[gi][gi] = 1.0
        I[gi] = 0.0
        v = _gauss(G, I)
        return {name: v[i] for name, i in self.idx.items()}


def _gauss(A, b):
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-18:
            M[c][c] = 1.0
            continue
        M[c], M[p] = M[p], M[c]
        piv = M[c][c]
        for j in range(c, n + 1):
            M[c][j] /= piv
        for r in range(n):
            if r != c and M[r][c] != 0.0:
                f = M[r][c]
                for j in range(c, n + 1):
                    M[r][j] -= f * M[c][j]
    return [M[i][n] for i in range(n)]


# =====================================================================
#  4.  Apparatus inventory  (numbering follows Figure 1 of the sheet)
# =====================================================================
ITEMS = [
    # key          fig#  needs
    ("tunnel",      1,  []),
    ("fan",         2,  ["tunnel"]),
    ("pendulum",    3,  ["tunnel"]),
    ("hotwire",     4,  ["tunnel", "stand"]),
    ("ebox",        5,  []),
    ("turbine",     6,  ["tunnel", "stand"]),
    ("dmm1",        7,  []),
    ("dmm2",        8,  []),
    ("dmm3",        8,  []),
    ("psu",         9,  []),
    ("ruler",      10,  []),
    ("stand",      11,  []),
    ("battery",    12,  ["fan"]),
]
ITEM_NEEDS = {k: n for k, _, n in ITEMS}
ITEM_FIG = {k: f for k, f, _ in ITEMS}

# the hot-wire and the turbine share the single steel rod / tunnel port
TUNNEL_PORT = ("hotwire", "turbine")


def item_name(k):
    return {
        "tunnel":   T("풍동 (니크롬선 포함)", "Wind tunnel (with nichrom wire)"),
        "fan":      T("컴퓨터 팬 (풍력 발생기)", "Computer fan (wind generator)"),
        "pendulum": T("탁구공 진자", "Ping pong ball pendulum"),
        "hotwire":  T("열선 필라멘트", "Hotwire filament"),
        "ebox":     T("열선용 전자회로 박스", "Electronic box for hotwire"),
        "turbine":  T("풍력 터빈", "Wind turbine"),
        "dmm1":     T("디지털 멀티미터 #1", "Digital multimeter #1"),
        "dmm2":     T("디지털 멀티미터 #2", "Digital multimeter #2"),
        "dmm3":     T("디지털 멀티미터 #3", "Digital multimeter #3"),
        "psu":      T("전원 공급 장치", "Power supply"),
        "ruler":    T("자 (50 cm)", "Ruler (50 cm)"),
        "stand":    T("스탠드 + 강철봉", "Static stand + steel rod"),
        "battery":  T("9 V 건전지 (광센서용)", "9 V battery (opto-sensor)"),
    }[k]


TERMINALS = {
    "psu":      ["PS.15+", "PS.15-", "PS.9+", "PS.9-"],
    "fan":      ["FAN.+", "FAN.-", "OM.R", "OM.K", "OM.B"],
    "turbine":  ["TU.+", "TU.-", "OT.R", "OT.K", "OT.B"],
    "battery":  ["BAT.+", "BAT.-"],
    "hotwire":  ["HW.1", "HW.2"],
    "ebox":     ["EB.V+", "EB.V-"] + ["EB.%d" % i for i in range(1, 14)],
    "tunnel":   ["NIC.A", "NIC.B"],
    "dmm1":     ["D1.V", "D1.COM", "D1.mA", "D1.10A"],
    "dmm2":     ["D2.V", "D2.COM", "D2.mA", "D2.10A"],
    "dmm3":     ["D3.V", "D3.COM", "D3.mA", "D3.10A"],
}

TERM_LABEL = {
    "PS.15+": "15+", "PS.15-": "15-", "PS.9+": "9+", "PS.9-": "9-",
    "FAN.+": "M+", "FAN.-": "M-",
    "OM.R": "R", "OM.K": "K", "OM.B": "B",
    "OT.R": "R", "OT.K": "K", "OT.B": "B",
    "TU.+": "T+", "TU.-": "T-",
    "BAT.+": "+", "BAT.-": "-",
    "HW.1": "a", "HW.2": "b",
    "NIC.A": "CLIP A", "NIC.B": "CLIP B",
    "EB.V+": "V+", "EB.V-": "V-",
}
for _i in range(1, 14):
    TERM_LABEL["EB.%d" % _i] = str(_i)
for _d in (1, 2, 3):
    TERM_LABEL["D%d.V" % _d] = u"V\u03a9Hz"
    TERM_LABEL["D%d.COM" % _d] = "COM"
    TERM_LABEL["D%d.mA" % _d] = "mA"
    TERM_LABEL["D%d.10A" % _d] = "10A"

DMM_MODES = ["OFF", "V", "mA", "10A", "OHM", "HZ"]


# =====================================================================
#  5.  The rig  -  placement, wiring, instruments, readings
# =====================================================================
class Rig(object):

    def __init__(self, seed=None):
        self.truth = Truth(seed)
        self.placed = set()
        self.wires = []                      # list of (t1, t2)
        # ---- instrument state -------------------------------------
        self.V15 = 0.0
        self.V9 = 0.0
        self.ps_on = False
        self.dmm = {i: {"mode": "OFF", "fuse": True} for i in (1, 2, 3)}
        self.spare_fuse = 1
        self.spare_hotwire = 1
        self.ebox_mode = "CTA"               # "CTA" | "CCA"
        self.pot = 0.50                      # 0..1
        self.clipA = 5.0                     # cm along the nichrome scale
        self.clipB = 30.0
        self.blade_angle = 0.0               # deg, for manual rotation (B.1)
        self.hotwire_dead = False
        self.log = []
        self._cache = None
        # numeric caches
        self._brush = self.truth.brush_dyn
        self._noise = random.Random(self.truth.seed ^ 0x5f3759df)

    # -----------------------------------------------------------------
    #  placement
    # -----------------------------------------------------------------
    def can_place(self, key):
        if key in self.placed:
            return False, T("이미 설치되어 있습니다.", "Already installed.")
        for need in ITEM_NEEDS.get(key, []):
            if need not in self.placed:
                return False, T("먼저 %s 을(를) 설치해야 합니다." % item_name(need),
                                "Install the %s first." % item_name(need))
        if key in TUNNEL_PORT:
            other = TUNNEL_PORT[1 - TUNNEL_PORT.index(key)]
            if other in self.placed:
                return False, T("풍동의 강철봉 포트에는 하나만 장착할 수 있습니다.",
                                "Only one probe can occupy the tunnel port.")
        return True, ""

    def place(self, key):
        ok, msg = self.can_place(key)
        if not ok:
            return False, msg
        self.placed.add(key)
        return True, ""

    def remove(self, key):
        if key not in self.placed:
            return False, ""
        # remove dependants first
        for k, _, needs in ITEMS:
            if key in needs and k in self.placed:
                self.remove(k)
        self.placed.discard(key)
        self.wires = [w for w in self.wires
                      if self._owner(w[0]) in self.placed
                      and self._owner(w[1]) in self.placed]
        return True, ""

    @staticmethod
    def _owner(term):
        for k, ts in TERMINALS.items():
            if term in ts:
                return k
        return None

    def available_terminals(self):
        out = []
        for k in sorted(TERMINALS):
            if k in self.placed:
                out.extend(TERMINALS[k])
        return out

    # -----------------------------------------------------------------
    #  wiring
    # -----------------------------------------------------------------
    def connect(self, a, b):
        if a == b:
            return False, T("같은 단자입니다.", "Same terminal.")
        for t in (a, b):
            if self._owner(t) not in self.placed:
                return False, T("설치되지 않은 부품의 단자입니다.",
                                "That part is not installed.")
        if (a, b) in self.wires or (b, a) in self.wires:
            return False, T("이미 연결되어 있습니다.", "Already connected.")
        if len(self.wires) >= 18:
            return False, T("케이블이 부족합니다.", "No cable left.")
        self.wires.append((a, b))
        return True, ""

    def disconnect(self, a, b):
        for w in list(self.wires):
            if set(w) == set((a, b)):
                self.wires.remove(w)
                return True
        return False

    def clear_wires(self):
        self.wires = []

    # ---- union-find over terminals ----------------------------------
    def _nodes(self):
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        for t in self.available_terminals():
            find(t)
        for a, b in self.wires:
            union(a, b)
        # internal short circuits of the electronic box
        if "ebox" in self.placed:
            if self.ebox_mode == "CTA":
                union("EB.1", "EB.V+")
                union("EB.2", "EB.V-")
                union("EB.5", "EB.V+")
            else:
                union("EB.11", "EB.8")
                union("EB.13", "EB.8")
                union("EB.10", "EB.V-")
                union("EB.12", "EB.V-")
        return {t: find(t) for t in self.available_terminals()}

    # -----------------------------------------------------------------
    #  physical state that does not depend on the wiring
    # -----------------------------------------------------------------
    def fan_terminal_voltage(self):
        n = self._nodes()
        if "fan" not in self.placed or not self.ps_on:
            return 0.0
        sol = self._solve()
        if sol is None:
            return 0.0
        return abs(sol.get(n.get("FAN.+"), 0.0) - sol.get(n.get("FAN.-"), 0.0))

    def f_M(self):
        return self.truth.fan_freq(self.fan_terminal_voltage())

    def v_wind(self):
        return self.truth.wind_speed(self.f_M())

    def f_T(self):
        if "turbine" not in self.placed:
            return 0.0
        w = self._turb_omega
        return w / (2 * math.pi)

    # -----------------------------------------------------------------
    #  network assembly + nonlinear iteration
    # -----------------------------------------------------------------
    def _build(self, n, Rfan, Rw, emf_t, ohm_probe=None, kill_sources=False):
        tr = self.truth
        net = Net()

        def N(t):
            return n[t]

        if "psu" in self.placed and self.ps_on and not kill_sources:
            net.V(N("PS.15+"), N("PS.15-"), self.V15, 0.05)
            net.V(N("PS.9+"), N("PS.9-"), self.V9, 0.05)
        elif "psu" in self.placed:
            net.R(N("PS.15+"), N("PS.15-"), 1e7)
            net.R(N("PS.9+"), N("PS.9-"), 1e7)

        if "fan" in self.placed:
            net.R(N("FAN.+"), N("FAN.-"), Rfan)

        if "battery" in self.placed:
            if kill_sources:
                net.R(N("BAT.+"), N("BAT.-"), 1.0)
            else:
                net.V(N("BAT.+"), N("BAT.-"), 8.55, 1.0)

        # opto sensors : supply branch + output stage
        for pref, spin in (("OM", "fan"), ("OT", "turbine")):
            if spin in self.placed:
                net.R(N(pref + ".R"), N(pref + ".K"), 2200.0)
                lvl = self._opto_level(pref)
                if kill_sources:
                    net.R(N(pref + ".B"), N(pref + ".K"), 10000.0)
                else:
                    net.V(N(pref + ".B"), N(pref + ".K"), lvl, 10000.0)

        if "turbine" in self.placed:
            rs = tr.R_M + self._brush
            if kill_sources:
                net.R(N("TU.+"), N("TU.-"), rs)
            else:
                net.V(N("TU.+"), N("TU.-"), emf_t, rs)

        if "tunnel" in self.placed:
            l = abs(self.clipB - self.clipA)
            net.R(N("NIC.A"), N("NIC.B"),
                  tr.nichrome_R(l) + 2 * tr.R_contact_nic)

        if "hotwire" in self.placed and not self.hotwire_dead:
            net.R(N("HW.1"), N("HW.2"), Rw)
        elif "hotwire" in self.placed:
            net.R(N("HW.1"), N("HW.2"), 1e9)

        if "ebox" in self.placed:
            if self.ebox_mode == "CTA":
                Rp = max(0.3, self.pot * tr.pot_max)
                net.R(N("EB.V+"), N("EB.3"), R_BRIDGE)      # A - ML
                net.R(N("EB.3"), N("EB.V-"), Rp)            # ML - B
                net.R(N("EB.4"), N("EB.V-"), R_BRIDGE)      # MR - B
                net.R(N("EB.6"), N("EB.4"), 1e-3)           # jack 6 == MR
            else:
                Iset = self.pot * tr.cca_Imax
                if kill_sources or not self.ps_on:
                    net.R(N("EB.9"), N("EB.V-"), 1e7)
                else:
                    net.I_src(N("EB.9"), N("EB.V-"), Iset, 1e6)
                net.R(N("EB.9"), N("EB.V-"), 2e6)

        # meters
        for d in (1, 2, 3):
            if ("dmm%d" % d) not in self.placed:
                continue
            m = self.dmm[d]["mode"]
            fuse = self.dmm[d]["fuse"]
            p = "D%d." % d
            if m == "V" or m == "HZ":
                net.R(N(p + "V"), N(p + "COM"), 1.0e7)
            elif m == "OHM":
                if ohm_probe == d:
                    net.I_src(N(p + "V"), N(p + "COM"), 1.0e-3, 1e9)
                    net.R(N(p + "V"), N(p + "COM"), 1e9)
                else:
                    net.R(N(p + "V"), N(p + "COM"), 1e6)
            elif m == "mA":
                net.R(N(p + "mA"), N(p + "COM"), 1.0 if fuse else 1e9)
            elif m == "10A":
                net.R(N(p + "10A"), N(p + "COM"), 0.01)
            # unused jacks stay open
        return net

    def _opto_level(self, pref):
        """output voltage of the opto sensor (V)"""
        hi, lo = 4.30, 0.22
        if pref == "OM":
            f = self._f_fan_cache
            if f > 0.05:
                return lo + (hi - lo) * 0.13      # DMM shows the mean
            a = self.blade_angle % 360.0
            return hi if a < 42.0 else lo
        else:
            f = self._turb_omega / (2 * math.pi)
            if f > 0.05:
                return lo + (hi - lo) * 0.13
            return lo

    # -----------------------------------------------------------------
    def read_all(self):
        """one network solve shared by the three meters (GUI refresh)"""
        self._cache = {}
        out = {d: self.read(d) for d in (1, 2, 3)}
        self._cache = None
        return out

    def _solve(self, ohm_probe=None, kill_sources=False):
        ck = (ohm_probe, kill_sources)
        if getattr(self, "_cache", None) is not None and ck in self._cache:
            return self._cache[ck]
        out = self._solve_raw(ohm_probe, kill_sources)
        if getattr(self, "_cache", None) is not None:
            self._cache[ck] = out
        return out

    def _solve_raw(self, ohm_probe=None, kill_sources=False):
        tr = self.truth
        n = self._nodes()
        if not n:
            return None
        Rfan = 1e7
        Rw = tr.R0_wire
        emf = 0.0
        self._f_fan_cache = 0.0
        self._turb_omega = 0.0
        sol = None
        prev = None
        for it in range(90):
            net = self._build(n, Rfan, Rw, emf, ohm_probe, kill_sources)
            try:
                sol = net.solve()
            except Exception:
                return None
            # ---- fan --------------------------------------------------
            if "fan" in self.placed:
                Vf = abs(sol.get(n["FAN.+"], 0.0) - sol.get(n["FAN.-"], 0.0))
                f = tr.fan_freq(Vf)
                I = tr.fan_current(Vf)
                newR = (Vf / I) if I > 1e-9 else 1e7
                Rfan = Rfan + 0.45 * (min(newR, 1e7) - Rfan)
                self._f_fan_cache = f
            v = tr.wind_speed(self._f_fan_cache)
            # ---- hot wire --------------------------------------------
            if "hotwire" in self.placed and not self.hotwire_dead:
                Ihw = abs(sol.get(n["HW.1"], 0.0) - sol.get(n["HW.2"], 0.0)) / Rw
                newRw = tr.cca_Rw(Ihw, v)
                newRw = min(newRw, 5000.0)
                Rw = Rw + 0.35 * (newRw - Rw)
            # ---- turbine ---------------------------------------------
            if "turbine" in self.placed:
                rs = tr.R_M + self._brush
                Vt = sol.get(n["TU.+"], 0.0) - sol.get(n["TU.-"], 0.0)
                It = (emf - Vt) / rs
                drive = tr.q_t * v * v - tr.tau_f
                if drive <= 0:
                    w = 0.0
                else:
                    w = (drive - tr.kT * abs(It)) / (tr.s_t * v)
                    w = max(0.0, min(w, tr.lambda0 * v / R_TURBINE_BLADE))
                self._turb_omega = self._turb_omega + 0.4 * (w - self._turb_omega)
                emf = tr.kT * self._turb_omega
            cur = (Rfan, Rw, emf)
            if prev is not None and it > 8:
                if all(abs(a - b) <= 1e-7 * (1 + abs(b))
                       for a, b in zip(cur, prev)):
                    break
            prev = cur
        return sol

    # -----------------------------------------------------------------
    #  hazards
    # -----------------------------------------------------------------
    def _check_hazards(self, sol, n):
        tr = self.truth
        # blown fuse on the mA range
        for d in (1, 2, 3):
            if ("dmm%d" % d) not in self.placed:
                continue
            if self.dmm[d]["mode"] == "mA" and self.dmm[d]["fuse"]:
                p = "D%d." % d
                if p + "mA" in n:
                    I = abs(sol.get(n[p + "mA"], 0.0) -
                            sol.get(n[p + "COM"], 0.0)) / 1.0
                    if I > 0.21:
                        # nothing announces it: the meter simply reads 0 on mA
                        self.dmm[d]["fuse"] = False
        # hot wire burn out
        if "hotwire" in self.placed and not self.hotwire_dead:
            v = self.truth.wind_speed(self._f_fan_cache)
            Rw = self._last_Rw
            if tr.wire_dT(Rw) > tr.wire_burn_dT:
                self.hotwire_dead = True
                self.log.append(T("열선 필라멘트가 과열되어 끊어졌습니다!",
                                  "The hotwire filament has burned out!"))

    # -----------------------------------------------------------------
    #  DMM reading
    # -----------------------------------------------------------------
    def read(self, d):
        """returns (text, raw_value_or_None)"""
        key = "dmm%d" % d
        if key not in self.placed:
            return "", None
        mode = self.dmm[d]["mode"]
        if mode == "OFF":
            return "", None
        n = self._nodes()
        p = "D%d." % d

        # ---------- frequency -------------------------------------
        if mode == "HZ":
            f = self._hz_reading(n, p)
            if f is None:
                return "  0.00", 0.0
            f = f * (1 + self._nz(0.0015)) + self._nz(0.02)
            return "%7.2f" % f, f

        # ---------- resistance ------------------------------------
        if mode == "OHM":
            if self.ps_on:
                return "   ---- ", None
            self._brush = (self.truth.brush_dyn +
                           self._noise.random() * self.truth.brush_extra)
            sol = self._solve(ohm_probe=d, kill_sources=True)
            self._brush = self.truth.brush_dyn
            if sol is None:
                return "  O.L ", None
            a, b = n.get(p + "V"), n.get(p + "COM")
            if a is not None and a == b:          # probes shorted together
                R = 2 * self.truth.R_lead
                R = R * (1 + self._nz(0.0012)) + self._nz(0.006)
                return self._fmt_ohm(R), R
            if a is None or b is None:
                return "  O.L ", None
            dv = abs(sol.get(a, 0.0) - sol.get(b, 0.0))
            R = dv / 1.0e-3 + 2 * self.truth.R_lead
            if R > 1.5e5:
                return "  O.L ", None
            R = R * (1 + self._nz(0.0012)) + self._nz(0.006)
            return self._fmt_ohm(R), R

        sol = self._solve()
        if sol is None:
            return "  O.L ", None
        self._last_Rw = self._Rw_now(sol, n)
        self._check_hazards(sol, n)

        # ---------- voltage ---------------------------------------
        if mode == "V":
            a, b = n.get(p + "V"), n.get(p + "COM")
            if a is None or b is None:
                return "  0.000", 0.0
            val = sol.get(a, 0.0) - sol.get(b, 0.0)
            if self._is_opto_pair(n, a, b) and self._f_fan_cache > 0.05:
                val += self._nz(0.30)          # unstable while spinning
            val = val * (1 + self._nz(0.0006)) + self._nz(4e-5)
            return self._fmt_volt(val), val

        # ---------- current ---------------------------------------
        if mode in ("mA", "10A"):
            jack = p + ("mA" if mode == "mA" else "10A")
            a, b = n.get(jack), n.get(p + "COM")
            if a is None or b is None:
                return ("  0.0" if mode == "mA" else "  0.000"), 0.0
            sh = 1.0 if mode == "mA" else 0.01
            if mode == "mA" and not self.dmm[d]["fuse"]:
                return "  0.0", 0.0
            I = (sol.get(a, 0.0) - sol.get(b, 0.0)) / sh
            I = I * (1 + self._nz(0.0025)) + self._nz(2e-5)
            if mode == "mA":
                if abs(I) > 0.2:
                    return "   1  ", None       # over range
                return "%7.1f" % (I * 1000.0), I
            return "%7.3f" % I, I
        return "", None

    # ---- helpers -----------------------------------------------------
    def _Rw_now(self, sol, n):
        if "hotwire" not in self.placed or self.hotwire_dead:
            return self.truth.R0_wire
        v = self.truth.wind_speed(self._f_fan_cache)
        # recover current through the wire from the converged solution
        # (Rw is the fixed point of  Rw = G R0/(G - I^2) )
        Rw = self.truth.R0_wire
        for _ in range(60):
            I = abs(sol.get(n["HW.1"], 0.0) - sol.get(n["HW.2"], 0.0)) / Rw
            Rw2 = min(self.truth.cca_Rw(I, v), 5000.0)
            if abs(Rw2 - Rw) < 1e-9:
                Rw = Rw2
                break
            Rw += 0.35 * (Rw2 - Rw)
        return Rw

    def _is_opto_pair(self, n, a, b):
        for pref in ("OM", "OT"):
            if (pref + ".B") in n and (pref + ".K") in n:
                if set((a, b)) == set((n[pref + ".B"], n[pref + ".K"])):
                    return True
        return False

    def _hz_reading(self, n, p):
        a, b = n.get(p + "V"), n.get(p + "COM")
        if a is None or b is None:
            return None
        self._solve()
        for pref, which in (("OM", "fan"), ("OT", "turbine")):
            if which not in self.placed:
                continue
            if (pref + ".B") not in n:
                continue
            if set((a, b)) != set((n[pref + ".B"], n[pref + ".K"])):
                continue
            if not self._opto_powered(n, pref):
                return 0.0
            if pref == "OM":
                return self._f_fan_cache
            return self._turb_omega / (2 * math.pi)
        return 0.0

    def _opto_powered(self, n, pref):
        if "battery" not in self.placed:
            return False
        try:
            return (n["BAT.+"] == n[pref + ".R"]) and (n["BAT.-"] == n[pref + ".K"])
        except KeyError:
            return False

    def _nz(self, s):
        return self._noise.gauss(0.0, s)

    # -----------------------------------------------------------------
    #  purely visual quantities (the student reads them off a ruler)
    # -----------------------------------------------------------------
    def pendulum_dx(self):
        """true horizontal displacement of the ball centre, metres"""
        if "pendulum" not in self.placed:
            return 0.0
        return self.truth.ball_dx(self.v_wind())

    def pendulum_h(self):
        """true vertical distance pivot -> ball centre, metres"""
        if "pendulum" not in self.placed:
            return 0.0
        return self.truth.ball_drop(self.v_wind())

    def tunnel_diameter(self):
        return self.truth.D_tunnel

    def ball_mass_printed(self):
        """the value printed on the ball, in gram"""
        return round(self.truth.m_ball * 1e3, 1)

    def read_scale(self, value_m, res_mm=0.5):
        """emulate reading a printed scale: nearest `res_mm`/2 plus jitter"""
        step = res_mm * 1e-3 / 2.0
        x = value_m + self._noise.gauss(0.0, step * 0.35)
        return round(x / step) * step

    @staticmethod
    def _fmt_volt(v):
        a = abs(v)
        if a < 0.19999:
            return "%8.5f" % v
        if a < 1.9999:
            return "%8.4f" % v
        if a < 19.999:
            return "%8.3f" % v
        return "%8.2f" % v

    @staticmethod
    def _fmt_ohm(r):
        if r < 199.99:
            return "%8.2f" % r
        if r < 1999.9:
            return "%8.1f" % r
        return "%8.0f" % r


# =====================================================================
#  6.  GUI  -  common helpers
# =====================================================================
import tkinter as tk
from tkinter import ttk, messagebox

BG_APP = "#20242b"
BG_PANEL = "#2b3038"
FG_TXT = "#e8eaed"
BG_TABLE = "#7a6a55"
LCD_BG = "#12301c"
LCD_FG = "#9dffb0"
FONT_UI = ("Helvetica", 10)
FONT_SM = ("Helvetica", 8)
FONT_LCD = ("Courier", 17, "bold")
WIRE_COLORS = ["#d23b3b", "#111111", "#2f6fd0", "#159c58", "#d38b1e",
               "#8e44ad", "#c0392b", "#16a085", "#7f8c8d", "#e67e22",
               "#2c3e50", "#27ae60", "#9b59b6", "#e74c3c", "#34495e",
               "#f39c12", "#1abc9c", "#95a5a6"]


def rrect(cv, x1, y1, x2, y2, r=8, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


# ---------------------------------------------------------------------
#  zone / terminal geometry of the assembly canvas
# ---------------------------------------------------------------------
ZONES = {
    "psu":      (200, 18, 215, 100),
    "ruler":    (440, 18, 480, 44),
    "fan":      (215, 205, 112, 150),
    "tunnel":   (332, 188, 432, 172),
    "stand":    (782, 172, 120, 205),
    "pendulum": (556, 122, 96, 62),
    "probe":    (420, 122, 120, 62),
    "hotwire":  (420, 122, 120, 62),
    "turbine":  (420, 122, 120, 62),
    "dmm1":     (200, 470, 152, 160),
    "dmm2":     (366, 470, 152, 160),
    "dmm3":     (532, 470, 152, 160),
    "ebox":     (700, 462, 262, 168),
    "battery":  (980, 470, 120, 96),
}

TERM_OFF = {
    "PS.15+": ("psu", 22, 80), "PS.15-": ("psu", 52, 80),
    "PS.9+": ("psu", 152, 80), "PS.9-": ("psu", 182, 80),
    "FAN.+": ("fan", 14, 128), "FAN.-": ("fan", 36, 128),
    "OM.R": ("fan", 62, 128), "OM.K": ("fan", 82, 128), "OM.B": ("fan", 102, 128),
    "NIC.A": ("tunnel", 70, 12), "NIC.B": ("tunnel", 330, 12),
    "HW.1": ("probe", 24, 50), "HW.2": ("probe", 48, 50),
    "TU.+": ("probe", 14, 50), "TU.-": ("probe", 36, 50),
    "OT.R": ("probe", 64, 50), "OT.K": ("probe", 84, 50), "OT.B": ("probe", 104, 50),
    "BAT.+": ("battery", 34, 66), "BAT.-": ("battery", 74, 66),
    "EB.V+": ("ebox", 20, 44), "EB.V-": ("ebox", 20, 76),
    "EB.5": ("ebox", 74, 34), "EB.6": ("ebox", 104, 34),
    "EB.12": ("ebox", 186, 34), "EB.13": ("ebox", 216, 34),
    "EB.3": ("ebox", 74, 82), "EB.4": ("ebox", 104, 82),
    "EB.10": ("ebox", 186, 82), "EB.11": ("ebox", 216, 82),
    "EB.1": ("ebox", 74, 130), "EB.2": ("ebox", 104, 130),
    "EB.8": ("ebox", 186, 130), "EB.9": ("ebox", 216, 130),
}
for _d in (1, 2, 3):
    z = "dmm%d" % _d
    TERM_OFF["D%d.10A" % _d] = (z, 24, 136)
    TERM_OFF["D%d.mA" % _d] = (z, 58, 136)
    TERM_OFF["D%d.COM" % _d] = (z, 92, 136)
    TERM_OFF["D%d.V" % _d] = (z, 126, 136)


def term_xy(t):
    z, dx, dy = TERM_OFF[t]
    x, y, w, h = ZONES[z]
    return x + dx, y + dy


# =====================================================================
#  7.  Assembly canvas
# =====================================================================
class AssemblyCanvas(tk.Canvas):

    W, H = 1180, 660

    def __init__(self, master, app):
        tk.Canvas.__init__(self, master, width=self.W, height=self.H,
                           bg=BG_APP, highlightthickness=0)
        self.app = app
        self.rig = app.rig
        self.mode = "place"
        self.drag = None
        self.pending = None
        self.hover = None
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_motion)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Button-3>", self.on_right)
        self.bind("<Motion>", self.on_hover)

    # -----------------------------------------------------------------
    def palette_items(self):
        out = []
        y = 46
        for k, fig, need in ITEMS:
            if k in self.rig.placed:
                continue
            out.append((k, 10, y, 158, 34))
            y += 40
        return out

    # -----------------------------------------------------------------
    def redraw(self):
        self.delete("all")
        self.create_rectangle(0, 0, 175, self.H, fill="#171a1f", outline="")
        self.create_text(88, 22, text=T("부품 상자", "PARTS"), fill="#9fb3c8",
                         font=("Helvetica", 11, "bold"))
        for k, x, y, w, h in self.palette_items():
            rrect(self, x, y, x + w, y + h, 6, fill="#31373f", outline="#586275")
            self.create_text(x + 8, y + h / 2, anchor="w",
                             text="%d. %s" % (ITEM_FIG[k], item_name(k)),
                             fill=FG_TXT, font=FONT_SM)
        # bench
        self.create_rectangle(178, 0, self.W, self.H, fill=BG_TABLE, outline="")
        for k in ZONES:
            if k in ("probe", "hotwire", "turbine"):
                continue
            if k not in self.rig.placed:
                x, y, w, h = ZONES[k]
                self.create_rectangle(x, y, x + w, y + h, dash=(4, 4),
                                      outline="#c8b89c")
                self.create_text(x + w / 2, y + h / 2, text=item_name(k),
                                 fill="#efe4cf", font=FONT_SM)
        if not (set(TUNNEL_PORT) & self.rig.placed):
            x, y, w, h = ZONES["probe"]
            self.create_rectangle(x, y, x + w, y + h, dash=(4, 4),
                                  outline="#c8b89c")
            self.create_text(x + w / 2, y + h / 2,
                             text=T("열선 / 터빈", "hotwire / turbine"),
                             fill="#efe4cf", font=FONT_SM)
        for k in ("tunnel", "fan", "stand", "hotwire", "turbine", "pendulum",
                  "psu", "ebox", "dmm1", "dmm2", "dmm3", "battery", "ruler"):
            if k in self.rig.placed:
                getattr(self, "draw_" + (k if not k.startswith("dmm") else "dmm"))(k)
        self.draw_wires()
        if self.mode == "wire":
            self.draw_terminals()
        if self.drag:
            k, mx, my = self.drag
            rrect(self, mx - 70, my - 15, mx + 70, my + 15, 6,
                  fill="#4a5568", outline="#e2e8f0")
            self.create_text(mx, my, text=item_name(k), fill="#fff", font=FONT_SM)

    # ---------------- individual apparatus drawings ------------------
    def draw_tunnel(self, k="tunnel"):
        x, y, w, h = ZONES["tunnel"]
        cy = y + h / 2
        self.create_rectangle(x, y + 24, x + w, y + h - 24,
                              fill="#f2f1ec", outline="#9a978d", width=2)
        self.create_oval(x + w - 20, y + 24, x + w + 20, y + h - 24,
                         fill="#e3e1d8", outline="#9a978d", width=2)
        self.create_oval(x + w - 8, y + 36, x + w + 8, y + h - 36,
                         fill="#2d2f32", outline="")
        # printed vertical scale on the shell (Fig. 1)
        for i in range(0, 15):
            yy = y + 30 + i * (h - 60) / 14.0
            self.create_line(x + 16, yy, x + 16 + (10 if i % 5 == 0 else 5), yy,
                             fill="#6a6a6a")
        # nichrome wire with its printed cm scale
        self.create_line(x + 30, y + 12, x + w - 30, y + 12,
                         fill="#8a8f96", width=3)
        for i in range(0, 51, 5):
            xx = x + 30 + (w - 60) * i / 50.0
            self.create_line(xx, y + 4, xx, y + 8, fill="#3a3a3a")
        self.create_text(x + w / 2, y + h - 12,
                         text=T("풍동 (내부에 니크롬선)", "wind tunnel"),
                         fill="#6b6558", font=FONT_SM)

    def draw_fan(self, k="fan"):
        x, y, w, h = ZONES["fan"]
        rrect(self, x, y, x + w, y + h - 34, 6, fill="#8e9299", outline="#5c6068",
              width=2)
        cx, cy = x + w / 2, y + (h - 34) / 2
        self.create_oval(cx - 40, cy - 40, cx + 40, cy + 40, fill="#3b3f45",
                         outline="#22252a", width=2)
        ph = self.app.blade_phase
        for i in range(7):
            a = ph + i * 2 * math.pi / 7
            self.create_line(cx, cy, cx + 36 * math.cos(a), cy + 36 * math.sin(a),
                             fill="#1d2024", width=6)
        a0 = ph
        self.create_oval(cx + 30 * math.cos(a0) - 4, cy + 30 * math.sin(a0) - 4,
                         cx + 30 * math.cos(a0) + 4, cy + 30 * math.sin(a0) + 4,
                         fill="#f5f5f5", outline="")
        self.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, fill="#6d7178", outline="")
        # opto sensor block
        self.create_rectangle(x + 56, y + h - 48, x + 110, y + h - 34,
                              fill="#20242a", outline="#000")
        self.create_text(x + 83, y + h - 41, text="OPTO", fill="#9aa6b2",
                         font=("Helvetica", 6))

    def draw_stand(self, k="stand"):
        x, y, w, h = ZONES["stand"]
        self.create_rectangle(x + 10, y + h - 16, x + w - 10, y + h,
                              fill="#d8d5cc", outline="#8a8880")
        self.create_line(x + w / 2, y + 6, x + w / 2, y + h - 16,
                         fill="#b9bcc2", width=7)
        self.create_line(330, y + 16, x + w / 2, y + 16, fill="#b9bcc2", width=5)

    def draw_pendulum(self, k="pendulum"):
        x, y, w, h = ZONES["pendulum"]
        self.create_line(x + w / 2, y + 6, x + w / 2, y + h + 60,
                         fill="#6a6252", width=1)
        self.create_oval(x + w / 2 - 9, y + h + 52, x + w / 2 + 9, y + h + 70,
                         fill="#f0a01e", outline="#b57612")

    def draw_hotwire(self, k="hotwire"):
        x, y, w, h = ZONES["probe"]
        self.create_line(x + 30, y, x + 30, y + h + 70, fill="#c2c5ca", width=5)
        self.create_oval(x + 22, y + h + 60, x + 38, y + h + 78,
                         fill="#2b2b2b", outline="#111")
        glow = self.app.hotwire_glow()
        self.create_line(x + 26, y + h + 74, x + 30, y + h + 66, x + 34, y + h + 74,
                         fill=glow, width=2)
        self.create_text(x + w / 2 + 20, y + 12, text="HOTWIRE", fill="#4a4438",
                         font=FONT_SM)

    def draw_turbine(self, k="turbine"):
        x, y, w, h = ZONES["probe"]
        self.create_line(x + 30, y, x + 30, y + h + 46, fill="#c2c5ca", width=5)
        cx, cy = x + 30, y + h + 62
        ph = self.app.turb_phase
        self.create_oval(cx - 26, cy - 26, cx + 26, cy + 26, fill="", outline="#555")
        for i in range(7):
            a = ph + i * 2 * math.pi / 7
            self.create_line(cx, cy, cx + 24 * math.cos(a), cy + 24 * math.sin(a),
                             fill="#141414", width=5)
        self.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill="#8e9299", outline="")
        self.create_text(x + w / 2 + 22, y + 12, text="TURBINE", fill="#4a4438",
                         font=FONT_SM)

    def draw_psu(self, k="psu"):
        x, y, w, h = ZONES["psu"]
        rrect(self, x, y, x + w, y + h, 6, fill="#b9bcc0", outline="#7d8085", width=2)
        self.create_rectangle(x + 14, y + 10, x + 84, y + 34, fill="#3a0d0d",
                              outline="#222")
        self.create_rectangle(x + 128, y + 10, x + 198, y + 34, fill="#3a0d0d",
                              outline="#222")
        self.create_text(x + 49, y + 22, text="%5.2f" % self.rig.V15,
                         fill="#ff6a5a", font=("Courier", 11, "bold"))
        self.create_text(x + 163, y + 22, text="%5.2f" % self.rig.V9,
                         fill="#ff6a5a", font=("Courier", 11, "bold"))
        self.create_text(x + 49, y + 44, text="15 V", fill="#33373c", font=FONT_SM)
        self.create_text(x + 163, y + 44, text="9 V", fill="#33373c", font=FONT_SM)
        self.create_oval(x + 100, y + 12, x + 116, y + 28,
                         fill="#e04b3a" if self.rig.ps_on else "#5b5f64",
                         outline="#333")

    def draw_ebox(self, k="ebox"):
        x, y, w, h = ZONES["ebox"]
        rrect(self, x, y, x + w, y + h, 8, fill="#232629", outline="#0d0f11", width=2)
        self.create_text(x + w / 2, y + 12, text="HOTWIRE   CTA / CCA   HOTWIRE",
                         fill="#cfd3d8", font=FONT_SM)
        self.create_rectangle(x + 8, y + 30, x + 34, y + 44, fill="#c02b1e",
                              outline="#000")
        self.create_rectangle(x + 8, y + 62, x + 34, y + 76, fill="#101010",
                              outline="#000")
        # toggle switch
        sx, sy = x + 150, y + 74
        self.create_oval(sx - 12, sy - 12, sx + 12, sy + 12, fill="#8b8f95",
                         outline="#000")
        ang = -0.8 if self.rig.ebox_mode == "CTA" else 0.8
        self.create_line(sx, sy, sx + 18 * math.cos(ang - math.pi / 2),
                         sy + 18 * math.sin(ang - math.pi / 2),
                         fill="#e8eaed", width=4)
        self.create_text(x + 150, y + 100, text=self.rig.ebox_mode,
                         fill="#8fd0ff", font=FONT_SM)
        for tx, ty, lab in ((89, 20, "HOTWIRE"), (201, 20, "HOTWIRE"),
                            (89, 64, "V CALIB"), (201, 64, "V METER"),
                            (89, 112, "V INPUT"), (201, 112, "AMPERE")):
            self.create_text(x + tx, y + ty, text=lab, fill="#7d848c",
                             font=("Helvetica", 6))
        self.create_text(x + w / 2, y + h - 8,
                         text=T("열선용 전자회로 박스", "hotwire electronic box"),
                         fill="#7d848c", font=FONT_SM)

    def draw_dmm(self, k):
        x, y, w, h = ZONES[k]
        d = int(k[-1])
        rrect(self, x, y, x + w, y + h, 8, fill="#d8b93a", outline="#7a6712", width=2)
        self.create_rectangle(x + 12, y + 12, x + w - 12, y + 52, fill=LCD_BG,
                              outline="#20301f")
        txt, _ = self.rig.read(d)
        self.create_text(x + w - 18, y + 32, anchor="e",
                         text=(txt if txt else " "), fill=LCD_FG,
                         font=("Courier", 13, "bold"))
        self.create_text(x + 20, y + 32, anchor="w", text=self.rig.dmm[d]["mode"],
                         fill="#5f9f6f", font=FONT_SM)
        cx, cy = x + w / 2, y + 90
        self.create_oval(cx - 26, cy - 26, cx + 26, cy + 26, fill="#26292d",
                         outline="#111")
        a = {"OFF": -90, "V": -30, "mA": 20, "10A": 70, "OHM": 130,
             "HZ": 190}[self.rig.dmm[d]["mode"]] * math.pi / 180.0
        self.create_line(cx, cy, cx + 22 * math.cos(a), cy + 22 * math.sin(a),
                         fill="#f2f2f2", width=4)
        self.create_text(x + w / 2, y + h - 6, text="DMM#%d" % d, fill="#4a4008",
                         font=FONT_SM)

    def draw_battery(self, k="battery"):
        x, y, w, h = ZONES["battery"]
        rrect(self, x + 20, y + 6, x + w - 20, y + 56, 4, fill="#2b57a8",
              outline="#16305f", width=2)
        self.create_text(x + w / 2, y + 30, text="9V", fill="#e8eaed",
                         font=("Helvetica", 12, "bold"))

    def draw_ruler(self, k="ruler"):
        x, y, w, h = ZONES["ruler"]
        rrect(self, x, y, x + w, y + h, 3, fill="#f2d98b", outline="#b39b47")
        for i in range(0, 51):
            xx = x + 8 + (w - 16) * i / 50.0
            ln = 14 if i % 10 == 0 else (9 if i % 5 == 0 else 5)
            self.create_line(xx, y + 2, xx, y + 2 + ln, fill="#5a4a12")
            if i % 10 == 0:
                self.create_text(xx, y + h - 9, text=str(i), fill="#5a4a12",
                                 font=("Helvetica", 7))

    # ---------------- wires & terminals -------------------------------
    def draw_wires(self):
        for i, (a, b) in enumerate(self.rig.wires):
            try:
                x1, y1 = term_xy(a)
                x2, y2 = term_xy(b)
            except KeyError:
                continue
            c = WIRE_COLORS[i % len(WIRE_COLORS)]
            mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0 + 26
            self.create_line(x1, y1, mx, my, x2, y2, smooth=True, width=3,
                             fill=c, tags=("wire", "wire%d" % i))

    def draw_terminals(self):
        for t in self.rig.available_terminals():
            if t not in TERM_OFF:
                continue
            x, y = term_xy(t)
            col = "#ffd54a" if t == self.pending else (
                "#7fd6ff" if t == self.hover else "#d9dde3")
            self.create_oval(x - 6, y - 6, x + 6, y + 6, fill=col,
                             outline="#101418", width=2)
            self.create_text(x, y - 13, text=TERM_LABEL.get(t, t),
                             fill="#241f16", font=("Helvetica", 7))

    # ---------------- interaction -------------------------------------
    def _hit_term(self, mx, my):
        best, bd = None, 1e9
        for t in self.rig.available_terminals():
            if t not in TERM_OFF:
                continue
            x, y = term_xy(t)
            d = (x - mx) ** 2 + (y - my) ** 2
            if d < 121 and d < bd:
                best, bd = t, d
        return best

    def _hit_zone(self, mx, my):
        for k, (x, y, w, h) in ZONES.items():
            if x <= mx <= x + w and y <= my <= y + h:
                return k
        return None

    def on_press(self, e):
        if self.mode == "wire":
            t = self._hit_term(e.x, e.y)
            if t:
                if self.pending is None:
                    self.pending = t
                else:
                    ok, msg = self.rig.connect(self.pending, t)
                    self.pending = None
                    if not ok:
                        self.app.say(msg)
                    else:
                        self.app.say(T("연결됨", "connected"))
                self.redraw()
            return
        for k, x, y, w, h in self.palette_items():
            if x <= e.x <= x + w and y <= e.y <= y + h:
                self.drag = (k, e.x, e.y)
                self.redraw()
                return
        z = self._hit_zone(e.x, e.y)
        if z in self.rig.placed:
            self.app.say(T("우클릭하면 해체됩니다.", "right-click to remove."))

    def on_motion(self, e):
        if self.drag:
            self.drag = (self.drag[0], e.x, e.y)
            self.redraw()

    def on_release(self, e):
        if not self.drag:
            return
        k = self.drag[0]
        self.drag = None
        z = self._hit_zone(e.x, e.y)
        target = k
        if k in TUNNEL_PORT:
            okzone = (z in ("probe", "hotwire", "turbine"))
        else:
            okzone = (z == k)
        if not okzone:
            self.app.say(T("올바른 위치가 아닙니다.", "That is not the right place."))
            self.redraw()
            return
        ok, msg = self.rig.place(target)
        self.app.say(msg if not ok else
                     T("%s 설치 완료" % item_name(target),
                       "%s installed" % item_name(target)))
        self.app.refresh_all()

    def on_right(self, e):
        if self.mode == "wire":
            items = self.find_overlapping(e.x - 4, e.y - 4, e.x + 4, e.y + 4)
            for it in items:
                for tg in self.gettags(it):
                    if tg.startswith("wire") and tg != "wire":
                        i = int(tg[4:])
                        if 0 <= i < len(self.rig.wires):
                            self.rig.wires.pop(i)
                            self.redraw()
                            return
            self.pending = None
            self.redraw()
            return
        z = self._hit_zone(e.x, e.y)
        if z in ("probe",):
            for k in TUNNEL_PORT:
                if k in self.rig.placed:
                    z = k
        if z in self.rig.placed:
            self.rig.remove(z)
            self.app.say(T("해체했습니다.", "removed."))
            self.app.refresh_all()

    def on_hover(self, e):
        if self.mode != "wire":
            return
        t = self._hit_term(e.x, e.y)
        if t != self.hover:
            self.hover = t
            self.redraw()


# =====================================================================
#  8.  Bench canvas  (side elevation of the tunnel, zoom + pan + ruler)
# =====================================================================
class BenchCanvas(tk.Canvas):

    W, H = 720, 430

    def __init__(self, master, app):
        tk.Canvas.__init__(self, master, width=self.W, height=self.H,
                           bg="#101317", highlightthickness=0)
        self.app = app
        self.rig = app.rig
        self.s = 620.0                       # px per metre
        self.ox, self.oy = 0.255, -0.025     # world point at canvas centre
        self.ruler_on = False
        self.ruler_pos = [0.44, -0.27]
        self.ruler_vert = False
        self._grab = None
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "_grab", None))
        self.bind("<MouseWheel>", self.on_wheel)
        self.bind("<Button-4>", lambda e: self.zoom_at(e.x, e.y, 1.15))
        self.bind("<Button-5>", lambda e: self.zoom_at(e.x, e.y, 1 / 1.15))

    # ---- transforms --------------------------------------------------
    def sx(self, wx):
        return self.W / 2.0 + (wx - self.ox) * self.s

    def sy(self, wy):
        return self.H / 2.0 + (wy - self.oy) * self.s

    def wx(self, px):
        return self.ox + (px - self.W / 2.0) / self.s

    def wy(self, py):
        return self.oy + (py - self.H / 2.0) / self.s

    def zoom_at(self, px, py, k):
        wx0, wy0 = self.wx(px), self.wy(py)
        self.s = max(180.0, min(14000.0, self.s * k))
        self.ox = wx0 - (px - self.W / 2.0) / self.s
        self.oy = wy0 - (py - self.H / 2.0) / self.s
        self.redraw()

    def on_wheel(self, e):
        self.zoom_at(e.x, e.y, 1.15 if e.delta > 0 else 1 / 1.15)

    # ---- geometry ----------------------------------------------------
    def geo(self):
        R = self.rig.truth.D_tunnel / 2.0
        t = 0.004
        return dict(R=R, t=t, x0=0.0, x1=0.55, ytop=-(R + t), ybot=(R + t),
                    xrod=0.16, xpiv=0.30, ytab=0.175,
                    ynic=-(R + t) - 0.030, ypivot=-(R + t) - 0.118)

    # ---- interaction -------------------------------------------------
    def on_press(self, e):
        g = self.geo()
        wx, wy = self.wx(e.x), self.wy(e.y)
        if self.ruler_on:
            rx, ry = self.ruler_pos
            if self.ruler_vert:
                if abs(wx - rx) < 0.016 and ry <= wy <= ry + 0.50:
                    self._grab = ("ruler", wx - rx, wy - ry)
                    return
            else:
                if abs(wy - ry) < 0.016 and rx <= wx <= rx + 0.50:
                    self._grab = ("ruler", wx - rx, wy - ry)
                    return
        if "tunnel" in self.rig.placed and abs(wy - g["ynic"]) < 0.014:
            for nm, val in (("A", self.rig.clipA), ("B", self.rig.clipB)):
                if abs(wx - (0.02 + val * 0.01)) < 0.012:
                    self._grab = ("clip" + nm, 0, 0)
                    return
        self._grab = ("pan", wx, wy)

    def on_drag(self, e):
        if not self._grab:
            return
        kind = self._grab[0]
        wx, wy = self.wx(e.x), self.wy(e.y)
        if kind == "pan":
            self.ox += self._grab[1] - wx
            self.oy += self._grab[2] - wy
        elif kind == "ruler":
            self.ruler_pos = [wx - self._grab[1], wy - self._grab[2]]
        elif kind in ("clipA", "clipB"):
            v = max(0.0, min(50.0, (wx - 0.02) / 0.01))
            if kind == "clipA":
                self.rig.clipA = v
            else:
                self.rig.clipB = v
        self.redraw()

    # ---- drawing -----------------------------------------------------
    def redraw(self):
        self.delete("all")
        g = self.geo()
        S = self.s
        # table
        self.create_rectangle(0, self.sy(g["ytab"]), self.W, self.H,
                              fill="#5d5140", outline="")
        if "tunnel" not in self.rig.placed:
            self.create_text(self.W / 2, self.H / 2,
                             text=T("장비를 먼저 조립하십시오.",
                                    "Assemble the apparatus first."),
                             fill="#8b98a8", font=FONT_UI)
            return
        self._draw_tunnel(g)
        if "fan" in self.rig.placed:
            self._draw_fan(g)
        if "stand" in self.rig.placed:
            self._draw_stand(g)
        if "hotwire" in self.rig.placed:
            self._draw_hotwire(g)
        if "turbine" in self.rig.placed:
            self._draw_turbine(g)
        if "pendulum" in self.rig.placed:
            self._draw_pendulum(g)
        self._draw_nichrome(g)
        if self.ruler_on and "ruler" in self.rig.placed:
            self._draw_ruler()
        self.create_text(8, 8, anchor="nw",
                         text=T("휠: 확대/축소   드래그: 이동",
                                "wheel: zoom    drag: pan"),
                         fill="#6f7d8c", font=FONT_SM)

    def _draw_tunnel(self, g):
        x0, x1, R, t = g["x0"], g["x1"], g["R"], g["t"]
        # inside (far wall of the cylinder)
        self.create_rectangle(self.sx(x0), self.sy(-R), self.sx(x1), self.sy(R),
                              fill="#43484f", outline="")
        self.create_rectangle(self.sx(x0), self.sy(-R), self.sx(x1),
                              self.sy(-R + 0.018), fill="#565c64", outline="")
        self.create_rectangle(self.sx(x0), self.sy(R - 0.018), self.sx(x1),
                              self.sy(R), fill="#31353b", outline="")
        # wind arrows (flow towards -x : suction fan at the left end)
        if self.rig.f_M() > 0.2:
            ph = (self.app.tick * 0.014) % 0.10
            for k in range(5):
                yy = -R + (2 * R) * (k + 0.5) / 5.0
                for m in range(5):
                    xa = x0 + 0.05 + m * 0.10 + ph
                    if xa + 0.05 > x1:
                        continue
                    self.create_line(self.sx(xa + 0.05), self.sy(yy),
                                     self.sx(xa), self.sy(yy),
                                     fill="#5f8fb8", width=2, arrow="last")
        # shell
        for ya, yb in ((-R - t, -R), (R, R + t)):
            self.create_rectangle(self.sx(x0), self.sy(ya), self.sx(x1),
                                  self.sy(yb), fill="#efedE6".upper(),
                                  outline="#8d8a80")
        self.create_oval(self.sx(x1) - 0.016 * self.s, self.sy(-R - t),
                         self.sx(x1) + 0.016 * self.s, self.sy(R + t),
                         fill="#e2e0d7", outline="#8d8a80")
        self.create_oval(self.sx(x1) - 0.010 * self.s, self.sy(-R),
                         self.sx(x1) + 0.010 * self.s, self.sy(R),
                         fill="#22262b", outline="#8d8a80")
        # printed scale on the shell (Fig. 1)
        for i in range(0, 21):
            yy = -R + i * (2 * R) / 20.0
            ln = 0.012 if i % 5 == 0 else 0.006
            self.create_line(self.sx(x0 + 0.02), self.sy(yy),
                             self.sx(x0 + 0.02 + ln), self.sy(yy),
                             fill="#a5a29a")
        # slot for the pendulum thread + hole for the steel rod
        self.create_rectangle(self.sx(g["xpiv"] - 0.006), self.sy(-R - t),
                              self.sx(g["xpiv"] + 0.006), self.sy(-R),
                              fill="#5a5750", outline="")
        self.create_rectangle(self.sx(g["xrod"] - 0.005), self.sy(-R - t),
                              self.sx(g["xrod"] + 0.005), self.sy(-R),
                              fill="#5a5750", outline="")

    def _draw_fan(self, g):
        R = g["R"]
        self.create_rectangle(self.sx(-0.105), self.sy(-R - 0.018),
                              self.sx(0.0), self.sy(R + 0.018),
                              fill="#8e9299", outline="#5c6068")
        cx, cy = self.sx(-0.052), self.sy(0.0)
        rr = R * self.s * 0.95
        self.create_oval(cx - 8, cy - rr, cx + 8, cy + rr, fill="#2e3237",
                         outline="#1b1e22")
        ph = self.app.blade_phase
        for i in range(7):
            a = ph + i * 2 * math.pi / 7
            self.create_line(cx, cy, cx + 8 * math.cos(a), cy + rr * math.sin(a),
                             fill="#15181b", width=3)
        a0 = ph
        self.create_oval(cx - 3, cy + rr * 0.8 * math.sin(a0) - 3,
                         cx + 3, cy + rr * 0.8 * math.sin(a0) + 3,
                         fill="#fafafa", outline="")
        self.create_rectangle(self.sx(-0.03), self.sy(-R - 0.030),
                              self.sx(-0.01), self.sy(-R - 0.018),
                              fill="#1d2126", outline="#000")
        self.create_text(self.sx(-0.052), self.sy(R + 0.034),
                         text="OPTO", fill="#9aa6b2", font=FONT_SM)

    def _draw_stand(self, g):
        self.create_rectangle(self.sx(0.60), self.sy(g["ytab"] - 0.012),
                              self.sx(0.72), self.sy(g["ytab"]),
                              fill="#cfccc3", outline="#8a8880")
        self.create_line(self.sx(0.66), self.sy(-0.235), self.sx(0.66),
                         self.sy(g["ytab"] - 0.012), fill="#b9bcc2", width=4)
        self.create_line(self.sx(g["xrod"]), self.sy(-0.235), self.sx(0.66),
                         self.sy(-0.235), fill="#b9bcc2", width=3)
        self.create_line(self.sx(g["xrod"]), self.sy(-0.235),
                         self.sx(g["xrod"]), self.sy(-0.02),
                         fill="#c2c5ca", width=3)

    def _draw_hotwire(self, g):
        x = g["xrod"]
        self.create_rectangle(self.sx(x) - 0.008 * self.s, self.sy(-0.026),
                              self.sx(x) + 0.008 * self.s, self.sy(0.002),
                              fill="#2b2b2b", outline="#111")
        col = self.app.hotwire_glow()
        w = max(2, int(0.0016 * self.s))
        self.create_line(self.sx(x) - 0.006 * self.s, self.sy(0.001),
                         self.sx(x), self.sy(0.010),
                         self.sx(x) + 0.006 * self.s, self.sy(0.001),
                         fill=col, width=w)

    def _draw_turbine(self, g):
        x = g["xrod"]
        cy = self.sy(0.0)
        cx = self.sx(x)
        rr = R_TURBINE_BLADE * self.s
        ph = self.app.turb_phase
        self.create_oval(cx - 7, cy - rr, cx + 7, cy + rr, fill="#22262b",
                         outline="#6f757d")
        for i in range(7):
            a = ph + i * 2 * math.pi / 7
            self.create_line(cx, cy, cx + 7 * math.cos(a), cy + rr * math.sin(a),
                             fill="#1b1e22", width=4)
            self.create_line(cx, cy, cx + 7 * math.cos(a), cy + rr * math.sin(a),
                             fill="#787f88", width=1)
        self.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill="#b9bcc2",
                         outline="")
        self.create_rectangle(self.sx(x) - 3, self.sy(-g["R"] - 0.030),
                              self.sx(x) + 9, self.sy(-g["R"] - 0.018),
                              fill="#1d2126", outline="#000")

    def _draw_pendulum(self, g):
        xp, yp = g["xpiv"], g["ypivot"]
        dx = self.rig.pendulum_dx()
        h = self.rig.pendulum_h()
        bx, by = xp - dx, yp + h
        # mast
        self.create_line(self.sx(xp), self.sy(g["ytop"]), self.sx(xp), self.sy(yp),
                         fill="#a8adb5", width=3)
        self.create_line(self.sx(xp), self.sy(yp), self.sx(bx), self.sy(by),
                         fill="#f4f4f4", width=1)
        rb = D_BALL / 2.0 * self.s
        self.create_oval(self.sx(bx) - rb, self.sy(by) - rb,
                         self.sx(bx) + rb, self.sy(by) + rb,
                         fill="#f2a11d", outline="#b47512")
        self.create_text(self.sx(bx), self.sy(by),
                         text="%.1f" % self.rig.ball_mass_printed(),
                         fill="#6b4a08", font=("Helvetica", max(6, int(self.s * 0.02))))
        # imprinted scale on the far wall, at the rest height of the ball
        y0 = yp + self.rig.truth.pend_h
        self.create_line(self.sx(0.255), self.sy(y0 - 0.026),
                         self.sx(0.355), self.sy(y0 - 0.026), fill="#cfd4da")
        for i in range(0, 101):
            xx = 0.345 - i * 0.001
            if xx < 0.2545:
                break
            ln = 0.009 if i % 10 == 0 else (0.006 if i % 5 == 0 else 0.003)
            if i % 5 or self.s > 900:
                self.create_line(self.sx(xx), self.sy(y0 - 0.026),
                                 self.sx(xx), self.sy(y0 - 0.026 + ln),
                                 fill="#cfd4da")
            if i % 10 == 0 and self.s > 700:
                self.create_text(self.sx(xx), self.sy(y0 - 0.026 + 0.016),
                                 text=str(i // 10), fill="#cfd4da",
                                 font=("Helvetica", max(6, int(self.s * 0.014))))

    def _draw_nichrome(self, g):
        y = g["ynic"]
        self.create_line(self.sx(0.02), self.sy(y), self.sx(0.52), self.sy(y),
                         fill="#9aa0a8", width=2)
        for i in range(0, 51):
            xx = 0.02 + i * 0.01
            ln = 0.008 if i % 10 == 0 else (0.005 if i % 5 == 0 else 0.0025)
            if i % 5 or self.s > 800:
                self.create_line(self.sx(xx), self.sy(y - 0.004),
                                 self.sx(xx), self.sy(y - 0.004 - ln),
                                 fill="#8f959d")
            if i % 10 == 0 and self.s > 500:
                self.create_text(self.sx(xx), self.sy(y - 0.020),
                                 text=str(i), fill="#8f959d",
                                 font=("Helvetica", max(6, int(self.s * 0.013))))
        for nm, val, col in (("A", self.rig.clipA, "#d23b3b"),
                             ("B", self.rig.clipB, "#111318")):
            xx = 0.02 + val * 0.01
            self.create_polygon(self.sx(xx), self.sy(y),
                                self.sx(xx) - 7, self.sy(y) + 14,
                                self.sx(xx) + 7, self.sy(y) + 14,
                                fill=col, outline="#f0f0f0")
            self.create_text(self.sx(xx), self.sy(y) + 22, text=nm,
                             fill="#e8eaed", font=FONT_SM)

    def _draw_ruler(self):
        rx, ry = self.ruler_pos
        L = 0.50
        if self.ruler_vert:
            x1, y1, x2, y2 = rx - 0.014, ry, rx + 0.014, ry + L
        else:
            x1, y1, x2, y2 = rx, ry - 0.014, rx + L, ry + 0.014
        self.create_rectangle(self.sx(x1), self.sy(y1), self.sx(x2), self.sy(y2),
                              fill="#f3dc9a", outline="#a8903f", stipple="gray50")
        for i in range(0, 501):
            u = i * 0.001
            ln = 0.010 if i % 10 == 0 else (0.006 if i % 5 == 0 else 0.003)
            if i % 5 and self.s < 1400:
                continue
            if self.ruler_vert:
                self.create_line(self.sx(rx - 0.014), self.sy(ry + u),
                                 self.sx(rx - 0.014 + ln), self.sy(ry + u),
                                 fill="#4c3f10")
            else:
                self.create_line(self.sx(rx + u), self.sy(ry - 0.014),
                                 self.sx(rx + u), self.sy(ry - 0.014 + ln),
                                 fill="#4c3f10")
            if i % 10 == 0 and self.s > 480:
                fs = max(6, int(self.s * 0.013))
                if self.ruler_vert:
                    self.create_text(self.sx(rx + 0.004), self.sy(ry + u),
                                     text=str(i // 10), fill="#4c3f10",
                                     font=("Helvetica", fs))
                else:
                    self.create_text(self.sx(rx + u), self.sy(ry + 0.006),
                                     text=str(i // 10), fill="#4c3f10",
                                     font=("Helvetica", fs))


# =====================================================================
#  9.  Application
# =====================================================================
class App(tk.Tk):

    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.title(T("APhO 2013 실험 1 - 풍력과 그 계측  |  HaslaLab",
                     "APhO 2013 Experiment 1 - Wind Power and its Metrologies"
                     "  |  HaslaLab"))
        self.configure(bg=BG_APP)
        self.rig = Rig(seed)
        self.blade_phase = 0.0
        self.turb_phase = 0.0
        self.tick = 0
        self._msg = tk.StringVar(value="")
        self._readings = {1: "", 2: "", 3: ""}
        self._build_ui()
        self.refresh_all()
        self.after(60, self._loop)

    # -----------------------------------------------------------------
    def _build_ui(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("TNotebook", background=BG_APP, borderwidth=0)
        st.configure("TNotebook.Tab", padding=(18, 6))
        st.configure("TFrame", background=BG_APP)
        st.configure("TLabel", background=BG_APP, foreground=FG_TXT, font=FONT_UI)
        st.configure("TLabelframe", background=BG_PANEL, foreground="#9fb3c8")
        st.configure("TLabelframe.Label", background=BG_PANEL,
                     foreground="#9fb3c8", font=("Helvetica", 9, "bold"))
        st.configure("TRadiobutton", background=BG_PANEL, foreground=FG_TXT,
                     font=FONT_SM)
        st.configure("TCheckbutton", background=BG_PANEL, foreground=FG_TXT,
                     font=FONT_SM)
        st.configure("TButton", font=FONT_SM)

        head = ttk.Frame(self)
        head.pack(fill="x", padx=8, pady=(6, 0))
        ttk.Label(head, font=("Helvetica", 13, "bold"),
                  text=T("14회 아시아물리올림피아드 (2013, 보고르) 실험 1 : "
                         "풍력과 그 계측  [20점]",
                         "14th Asian Physics Olympiad (2013, Bogor)  Experiment 1 : "
                         "Wind Power and its Metrologies  [20 pts]")).pack(side="left")
        ttk.Label(head, textvariable=self._msg,
                  foreground="#ffd54a").pack(side="right")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=6)

        # ---------------- assembly ---------------------------------
        f1 = ttk.Frame(nb)
        nb.add(f1, text=T("  1. 장비 조립  ", "  1. Assembly  "))
        bar = ttk.Frame(f1)
        bar.pack(fill="x", pady=4)
        self.amode = tk.StringVar(value="place")
        for val, lab in (("place", T("장비 배치", "place apparatus")),
                         ("wire", T("배선", "wiring"))):
            ttk.Radiobutton(bar, text=lab, value=val, variable=self.amode,
                            command=self._set_amode).pack(side="left", padx=6)
        ttk.Button(bar, text=T("배선 모두 해제", "clear all wires"),
                   command=self._clear_wires).pack(side="left", padx=16)
        ttk.Label(bar, text=T("좌클릭 드래그: 배치 / 단자 클릭: 연결 / "
                              "우클릭: 해체·배선 삭제",
                              "drag to place / click terminals to wire / "
                              "right click to remove")).pack(side="left", padx=10)
        self.acv = AssemblyCanvas(f1, self)
        self.acv.pack(pady=4)

        # ---------------- bench ------------------------------------
        f2 = ttk.Frame(nb)
        nb.add(f2, text=T("  2. 실험대  ", "  2. Bench  "))
        left = ttk.Frame(f2)
        left.pack(side="left", padx=4, pady=4)
        self.bcv = BenchCanvas(left, self)
        self.bcv.pack()
        self._build_meter_row(left)
        right = ttk.Frame(f2)
        right.pack(side="left", fill="y", padx=6, pady=4)
        self._build_controls(right)

    # -----------------------------------------------------------------
    def _build_meter_row(self, parent):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=6)
        self.meter_lbl = {}
        self.meter_mode = {}
        for d in (1, 2, 3):
            g = ttk.Labelframe(row, text="DMM #%d" % d)
            g.pack(side="left", padx=4)
            lb = tk.Label(g, text="", bg=LCD_BG, fg=LCD_FG, font=FONT_LCD,
                          width=9, anchor="e", relief="sunken", bd=2)
            lb.pack(padx=4, pady=3)
            self.meter_lbl[d] = lb
            var = tk.StringVar(value="OFF")
            self.meter_mode[d] = var
            cb = ttk.Combobox(g, textvariable=var, values=DMM_MODES, width=6,
                              state="readonly", font=FONT_SM)
            cb.pack(padx=4, pady=(0, 2))
            cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_all())
            fz = ttk.Frame(g)
            fz.pack(pady=(0, 4))
            fl = ttk.Label(fz, text="", font=FONT_SM)
            fl.pack(side="left", padx=3)
            ttk.Button(fz, text=T("퓨즈교체", "fuse"), width=8,
                       command=lambda dd=d: self._replace_fuse(dd)).pack(side="left")
            g.fuse_label = fl

    # -----------------------------------------------------------------
    def _build_controls(self, p):
        # ---- power supply ------------------------------------------
        g = ttk.Labelframe(p, text=T("9. 전원 공급 장치", "9. Power supply"))
        g.pack(fill="x", pady=3)
        self.ps_on = tk.IntVar(value=0)
        ttk.Checkbutton(g, text=T("전원 ON", "MAIN ON"), variable=self.ps_on,
                        command=self.refresh_all).pack(anchor="w", padx=6)
        self.vstep = tk.StringVar(value="0.100")
        srow = ttk.Frame(g)
        srow.pack(anchor="w", padx=6, pady=2)
        ttk.Label(srow, text=T("조정 폭", "step"), font=FONT_SM).pack(side="left")
        ttk.Combobox(srow, textvariable=self.vstep, width=6, state="readonly",
                     values=["1.000", "0.100", "0.010", "0.001"],
                     font=FONT_SM).pack(side="left", padx=4)
        self.v15 = tk.DoubleVar(value=0.0)
        self.v9 = tk.DoubleVar(value=0.0)
        for lab, var, hi in ((T("15 V 출력 (팬)", "15 V output (fan)"),
                              self.v15, 15.0),
                             (T("9 V 출력 (전자박스)", "9 V output (e-box)"),
                              self.v9, 9.0)):
            fr = ttk.Frame(g)
            fr.pack(fill="x", padx=6, pady=1)
            ttk.Label(fr, text=lab, font=FONT_SM).pack(anchor="w")
            r2 = ttk.Frame(fr)
            r2.pack(fill="x")
            sc = tk.Scale(r2, from_=0.0, to=hi, resolution=0.001,
                          orient="horizontal", variable=var, length=176,
                          showvalue=1, bg=BG_PANEL, fg=FG_TXT, font=FONT_SM,
                          highlightthickness=0, troughcolor="#1b1f24",
                          command=lambda e: self.refresh_all())
            sc.pack(side="left")
            ttk.Button(r2, text="-", width=2,
                       command=lambda v=var, h=hi: self._bump(v, -1, h)
                       ).pack(side="left", padx=1)
            ttk.Button(r2, text="+", width=2,
                       command=lambda v=var, h=hi: self._bump(v, +1, h)
                       ).pack(side="left")

        # ---- electronic box ----------------------------------------
        g = ttk.Labelframe(p, text=T("5. 열선용 전자회로 박스",
                                     "5. Hotwire electronic box"))
        g.pack(fill="x", pady=3)
        self.ebmode = tk.StringVar(value="CTA")
        r = ttk.Frame(g)
        r.pack(anchor="w", padx=6)
        for v in ("CTA", "CCA"):
            ttk.Radiobutton(r, text=v, value=v, variable=self.ebmode,
                            command=self.refresh_all).pack(side="left", padx=6)
        self.potv = tk.DoubleVar(value=50.0)
        pr = ttk.Frame(g)
        pr.pack(fill="x", padx=6, pady=2)
        tk.Scale(pr, from_=0.0, to=100.0, resolution=0.05, orient="horizontal",
                 variable=self.potv, length=176, bg=BG_PANEL, fg=FG_TXT,
                 font=FONT_SM, highlightthickness=0, troughcolor="#1b1f24",
                 label="POT", command=lambda e: self.refresh_all()).pack(side="left")
        ttk.Button(pr, text="-", width=2,
                   command=lambda: self._bumpp(-1)).pack(side="left", padx=1)
        ttk.Button(pr, text="+", width=2,
                   command=lambda: self._bumpp(+1)).pack(side="left")

        # ---- tools --------------------------------------------------
        g = ttk.Labelframe(p, text=T("도구 / 상태", "Tools / status"))
        g.pack(fill="x", pady=3)
        self.ruler_on = tk.IntVar(value=0)
        self.ruler_v = tk.IntVar(value=0)
        ttk.Checkbutton(g, text=T("10. 자 (50 cm) 꺼내기", "10. take out the ruler"),
                        variable=self.ruler_on,
                        command=self.refresh_all).pack(anchor="w", padx=6)
        ttk.Checkbutton(g, text=T("자를 세로로", "ruler vertical"),
                        variable=self.ruler_v,
                        command=self.refresh_all).pack(anchor="w", padx=6)
        self.hand = tk.DoubleVar(value=0.0)
        tk.Scale(g, from_=0.0, to=360.0, resolution=1.0, orient="horizontal",
                 variable=self.hand, length=200, bg=BG_PANEL, fg=FG_TXT,
                 font=FONT_SM, highlightthickness=0, troughcolor="#1b1f24",
                 label=T("팬 날개 수동 회전 (deg)", "rotate fan blade by hand (deg)"),
                 command=lambda e: self.refresh_all()).pack(padx=6)
        ttk.Button(g, text=T("열선 필라멘트 교체 (예비 1개)",
                             "replace hotwire filament (1 spare)"),
                   command=self._replace_wire).pack(fill="x", padx=6, pady=2)
        self.status = ttk.Label(g, text="", font=FONT_SM, foreground="#9fb3c8")
        self.status.pack(anchor="w", padx=6, pady=(0, 4))
        ttk.Label(p, text=T("세션 번호 : %d" % self.rig.truth.seed,
                            "session : %d" % self.rig.truth.seed),
                  font=FONT_SM, foreground="#6f7d8c").pack(anchor="w", pady=4)

    # -----------------------------------------------------------------
    def _bump(self, var, sgn, hi):
        st = float(self.vstep.get())
        var.set(max(0.0, min(hi, round(var.get() + sgn * st, 4))))
        self.refresh_all()

    def _bumpp(self, sgn):
        self.potv.set(max(0.0, min(100.0, round(self.potv.get() + sgn * 0.05, 3))))
        self.refresh_all()

    def _set_amode(self):
        self.acv.mode = self.amode.get()
        self.acv.pending = None
        self.acv.redraw()

    def _clear_wires(self):
        self.rig.clear_wires()
        self.refresh_all()

    def _replace_fuse(self, d):
        if self.rig.dmm[d]["fuse"]:
            self.say(T("퓨즈는 정상입니다.", "the fuse is fine."))
            return
        if self.rig.spare_fuse <= 0:
            self.say(T("예비 퓨즈가 없습니다.", "no spare fuse left."))
            return
        self.rig.spare_fuse -= 1
        self.rig.dmm[d]["fuse"] = True
        self.say(T("퓨즈를 교체했습니다.", "fuse replaced."))
        self.refresh_all()

    def _replace_wire(self):
        if not self.rig.hotwire_dead:
            self.say(T("열선은 정상입니다.", "the hotwire is fine."))
            return
        if self.rig.spare_hotwire <= 0:
            self.say(T("예비 열선이 없습니다.", "no spare hotwire left."))
            return
        self.rig.spare_hotwire -= 1
        self.rig.hotwire_dead = False
        self.say(T("열선을 교체했습니다.", "hotwire replaced."))
        self.refresh_all()

    def say(self, m):
        self._msg.set(m)

    # -----------------------------------------------------------------
    def hotwire_glow(self):
        if self.rig.hotwire_dead:
            return "#3b3f44"
        dT = self.rig.truth.wire_dT(getattr(self.rig, "_last_Rw",
                                            self.rig.truth.R0_wire))
        if dT < 120:
            return "#7c8188"
        if dT < 350:
            return "#a06a3a"
        if dT < 650:
            return "#d5741d"
        if dT < 1000:
            return "#ffa62b"
        return "#fff1c0"

    # -----------------------------------------------------------------
    def refresh_all(self):
        r = self.rig
        r.ps_on = bool(self.ps_on.get())
        r.V15 = float(self.v15.get())
        r.V9 = float(self.v9.get())
        r.ebox_mode = self.ebmode.get()
        r.pot = self.potv.get() / 100.0
        r.blade_angle = self.hand.get()
        for d in (1, 2, 3):
            r.dmm[d]["mode"] = self.meter_mode[d].get()
        self.bcv.ruler_on = bool(self.ruler_on.get())
        self.bcv.ruler_vert = bool(self.ruler_v.get())
        vals = r.read_all()
        for d in (1, 2, 3):
            txt = vals[d][0] if ("dmm%d" % d) in r.placed else "  ----"
            self.meter_lbl[d].configure(text=txt)
            par = self.meter_lbl[d].master
            par.fuse_label.configure(text="")
        s = []
        if r.hotwire_dead:
            s.append(T("열선 끊어짐", "hotwire burned out"))
        s.append(T("예비 퓨즈 %d / 예비 열선 %d" % (r.spare_fuse, r.spare_hotwire),
                   "spare fuse %d / spare hotwire %d"
                   % (r.spare_fuse, r.spare_hotwire)))
        self.status.configure(text="   ".join(s))
        if r.log:
            self.say(r.log[-1])
            r.log = r.log[-3:]
        self.acv.redraw()
        self.bcv.redraw()

    # -----------------------------------------------------------------
    def _loop(self):
        self.tick += 1
        f = self.rig.f_M()
        if f > 0.05:
            self.blade_phase += 2 * math.pi * f * 0.06 / 6.0
        else:
            self.blade_phase = math.radians(self.rig.blade_angle)
        self.turb_phase += 2 * math.pi * self.rig.f_T() * 0.06 / 3.0
        if self.tick % 3 == 0:
            self.refresh_all()
        else:
            self.acv.redraw()
            self.bcv.redraw()
        self.after(60, self._loop)


def main():
    global LANG
    seed = None
    for a in sys.argv[1:]:
        if a in ("--en", "-en"):
            LANG = "en"
        elif a in ("--ko", "-ko"):
            LANG = "ko"
        elif a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
    App(seed).mainloop()


if __name__ == "__main__":
    main()
