#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APhO 2011 (12th Asian Physics Olympiad, Israel) - Experimental Question 1
"Levitation of Conductors in an Oscillating Magnetic Field"

HaslaLab virtual laboratory simulator.
- Standard library only (tkinter).
- Instruments show ONLY what the real hardware displays.
  No physical quantity is ever computed or displayed for the student.
- Hidden true parameters are randomised every session.
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


# ----------------------------------------------------------------------------
#  physics : elliptic integrals & coaxial-loop mutual inductance
# ----------------------------------------------------------------------------
MU0 = 4.0e-7 * math.pi
G_TELAVIV = 9.80          # N/kg  (given on the problem sheet)
F_LINE = 50.0             # Hz
OMEGA = 2.0 * math.pi * F_LINE
RHO_ALLOY_NOM = 3.586e-8  # Ohm*m
RHO_MASS = 2700.0         # kg/m^3
SCREW_STEP = 1.41e-3      # m  (given on the problem sheet)


def ellip_KE(m):
    """Complete elliptic integrals K(m), E(m), parameter m = k^2, by AGM."""
    if m < 0.0 or m >= 1.0:
        raise ValueError("m out of range: %r" % (m,))
    a, b, c = 1.0, math.sqrt(1.0 - m), math.sqrt(m)
    s = 0.5 * c * c
    p = 1.0
    for _ in range(60):
        an = 0.5 * (a + b)
        bn = math.sqrt(a * b)
        cn = 0.5 * (a - b)
        a, b, c = an, bn, cn
        p *= 2.0
        s += 0.5 * p * c * c
        if c < 1e-16:
            break
    K = math.pi / (2.0 * a)
    return K, K * (1.0 - s)


def mutual_loops(a, r, s):
    """Mutual inductance [H] of two coaxial circular loops of radii a, r
    separated axially by s (Maxwell's formula)."""
    m = 4.0 * a * r / ((a + r) ** 2 + s * s)
    k = math.sqrt(m)
    K, E = ellip_KE(m)
    return MU0 * math.sqrt(a * r) * ((2.0 / k - k) * K - (2.0 / k) * E)


class Solenoid(object):
    """Iron-filled solenoid modelled as a uniformly magnetised cylinder,
    i.e. an equivalent surface-current sheet of density K_sheet [A/m].

    Flux linked by a coaxial ring of radius r whose plane is a distance z
    below the solenoid's lower end:
        Phi(z) = K_sheet * Integral_0^L  M(a_s, r, z + z0 + t) dt
    """

    def __init__(self, rng):
        self.a_s = 0.0263 * rng.uniform(0.97, 1.03)   # equivalent sheet radius [m]
        self.ell = 0.0672 * rng.uniform(0.97, 1.03)   # equivalent sheet length [m]
        self.z0 = 0.0092 * rng.uniform(0.90, 1.10)    # pole recess at contact [m]
        self.K_sheet = 77634.0 * rng.uniform(0.96, 1.04)  # A/m (rms)
        self._n = 40

    def flux_rms(self, z, r):
        tot = 0.0
        for i in range(self._n):
            t = self.ell * (i + 0.5) / self._n
            tot += mutual_loops(self.a_s, r, max(z, 0.0) + self.z0 + t)
        return self.K_sheet * tot * self.ell / self._n

    def emf_rms(self, z, r):
        """True rms EMF [V] induced on a coaxial ring of radius r at height z."""
        return OMEGA * self.flux_rms(z, r)

    def demf2_dz(self, z, r, h=2.0e-5):
        """d(eps_rms^2)/dz  [V^2/m]  (negative: EMF falls with z)."""
        zp = max(z, 0.0)
        e1 = self.emf_rms(zp + h, r)
        e0 = self.emf_rms(max(zp - h, 0.0), r)
        dz = (zp + h) - max(zp - h, 0.0)
        return (e1 * e1 - e0 * e0) / dz


# ----------------------------------------------------------------------------
#  rings
# ----------------------------------------------------------------------------
class Ring(object):
    def __init__(self, name, d_out, d_in, height, gap, rho):
        self.name = name
        self.d_out = d_out          # m
        self.d_in = d_in            # m
        self.height = height        # m (axial)
        self.gap = gap              # m (0.0 for the closed ring)
        self.rho = rho
        self.width = 0.5 * (d_out - d_in)
        self.d_mean = 0.5 * (d_out + d_in)
        self.r_mean = 0.5 * self.d_mean
        self.area = self.width * self.height
        self.length = math.pi * self.d_mean - self.gap
        self.volume = self.area * self.length
        self.mass = RHO_MASS * self.volume            # kg
        self.resistance = rho * self.length / self.area  # Ohm

    def arc_resistance(self, arc_len):
        return self.rho * arc_len / self.area

    def inductance(self):
        """Self-inductance of a broad ring; rectangular cross-section GMD."""
        gmd = 0.2235 * (self.width + self.height)
        r = self.r_mean
        return MU0 * r * (math.log(8.0 * r / gmd) - 2.0) * 0.850


# ----------------------------------------------------------------------------
#  apparatus  (all hidden truth lives here)
# ----------------------------------------------------------------------------
class Apparatus(object):
    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1 << 30)
        self.seed = seed
        rng = random.Random(seed)
        self.rng = rng
        self.rho = RHO_ALLOY_NOM * rng.uniform(0.97, 1.03)

        # --- thin open ring -------------------------------------------------
        d_out = 0.0960 * rng.uniform(0.995, 1.005)
        width = 0.00300 * rng.uniform(0.96, 1.04)
        self.thin = Ring("thin", d_out, d_out - 2 * width,
                         0.00190 * rng.uniform(0.95, 1.05),
                         0.0100 * rng.uniform(0.93, 1.07), self.rho)
        # --- broad closed ring ----------------------------------------------
        dc_out = 0.1005 * rng.uniform(0.995, 1.005)
        wc = 0.01225 * rng.uniform(0.98, 1.02)
        self.closed = Ring("closed", dc_out, dc_out - 2 * wc,
                           0.00520 * rng.uniform(0.97, 1.03), 0.0, self.rho)
        # --- broad open ring : identical but for the removed segment --------
        self.open_broad = Ring("open", self.closed.d_out, self.closed.d_in,
                               self.closed.height,
                               0.0100 * rng.uniform(0.93, 1.07), self.rho)

        self.L_closed = self.closed.inductance()
        self.solenoid = Solenoid(rng)

        # --- 0.7 V circuit ---------------------------------------------------
        self.v_source = 0.70 * rng.uniform(0.95, 1.05)
        self.r_internal = 0.035 * rng.uniform(0.85, 1.15)
        self.r_wire_short = 0.0150 * rng.uniform(0.85, 1.15)
        self.r_wire_long = 0.0350 * rng.uniform(0.85, 1.15)
        self.r_amm_shunt = 0.0100 * rng.uniform(0.9, 1.1)
        self.r_contact0 = 0.0090 * rng.uniform(0.6, 1.5)   # per crocodile clip
        self.r_volt_lead = 0.4        # voltmeter burden (huge vs. ring)
        self.r_volt_in = 1.0e7

        # instrument imperfections
        self.scale_zero_drift = rng.uniform(-0.02, 0.02)   # g
        self.emf_bias = rng.uniform(-0.03, 0.03)           # mV
        # near-iron attraction on the closed ring (reduces net downward force)
        self.f_iron0 = 0.25e-3 * G_TELAVIV * rng.uniform(0.7, 1.3)   # N
        self.lam_iron = 0.0025 * rng.uniform(0.8, 1.2)               # m
        # untwisted leads enclose part of the flux: a fixed share per set-up
        self.lead_pick = rng.uniform(0.08, 0.16)
        # warming of the closed ring above the room [K] (its resistivity rises)
        self.T_closed = 0.0

    # ---------------- part (c) truth -------------------------------------
    def r_closed(self):
        return self.closed.resistance * (1.0 + 0.0039 * self.T_closed)

    def k_true(self):
        """slope  L / (2 (R^2 + w^2 L^2))  [N m / V^2]"""
        L = self.L_closed
        R = self.r_closed()
        return L / (2.0 * (R * R + OMEGA * OMEGA * L * L))

    def force_true(self, z):
        """time-averaged downward force [N] on the closed ring at height z."""
        r = self.closed.r_mean
        f_mag = self.k_true() * abs(self.solenoid.demf2_dz(z, r))
        f_iron = self.f_iron0 * math.exp(-max(z, 0.0) / self.lam_iron)
        return f_mag - f_iron

    def emf_true(self, z):
        return self.solenoid.emf_rms(max(z, 0.0), self.open_broad.r_mean)


# ----------------------------------------------------------------------------
#  complex modified-nodal-analysis solver (AC, single frequency)
# ----------------------------------------------------------------------------
class MNA(object):
    def __init__(self):
        self.nodes = {}
        self.res = []      # (na, nb, Z)
        self.vsrc = []     # (na, nb, V)   V = phasor of (Va - Vb)

    def n(self, name):
        if name == "GND":
            return -1
        if name not in self.nodes:
            self.nodes[name] = len(self.nodes)
        return self.nodes[name]

    def add_z(self, a, b, Z):
        if Z is None:
            return
        self.res.append((self.n(a), self.n(b), complex(Z)))

    def add_v(self, a, b, V):
        self.vsrc.append((self.n(a), self.n(b), complex(V)))

    def solve(self):
        N = len(self.nodes)
        M = len(self.vsrc)
        size = N + M
        if size == 0:
            return {}, []
        A = [[0j] * size for _ in range(size)]
        z = [0j] * size

        def stamp(i, j, v):
            if i >= 0 and j >= 0:
                A[i][j] += v

        for (a, b, Z) in self.res:
            if abs(Z) < 1e-15:
                Z = complex(1e-12)
            y = 1.0 / Z
            stamp(a, a, y)
            stamp(b, b, y)
            stamp(a, b, -y)
            stamp(b, a, -y)
        for k, (a, b, V) in enumerate(self.vsrc):
            r = N + k
            if a >= 0:
                A[r][a] += 1.0
                A[a][r] += 1.0
            if b >= 0:
                A[r][b] -= 1.0
                A[b][r] -= 1.0
            z[r] += V
        # tiny leakage to ground for numerical stability of floating sections
        for i in range(N):
            A[i][i] += 1e-12

        # Gaussian elimination with partial pivoting
        for col in range(size):
            piv, best = col, abs(A[col][col])
            for r in range(col + 1, size):
                if abs(A[r][col]) > best:
                    piv, best = r, abs(A[r][col])
            if best < 1e-18:
                continue
            if piv != col:
                A[col], A[piv] = A[piv], A[col]
                z[col], z[piv] = z[piv], z[col]
            inv = 1.0 / A[col][col]
            for r in range(col + 1, size):
                f = A[r][col] * inv
                if f == 0:
                    continue
                for c in range(col, size):
                    A[r][c] -= f * A[col][c]
                z[r] -= f * z[col]
        x = [0j] * size
        for r in range(size - 1, -1, -1):
            if abs(A[r][r]) < 1e-18:
                x[r] = 0j
                continue
            acc = z[r]
            for c in range(r + 1, size):
                acc -= A[r][c] * x[c]
            x[r] = acc / A[r][r]
        volts = {}
        for name, idx in self.nodes.items():
            volts[name] = x[idx]
        currents = [x[N + k] for k in range(M)]
        return volts, currents


# ----------------------------------------------------------------------------
#  bench state : wiring, instruments, readings
# ----------------------------------------------------------------------------
DIAL_OFF = "OFF"
DIAL_200MV = "200mV~"
DIAL_20A = "20A~"
DIAL_20MA = "20mA~"
DIAL_OHM = "200\u03a9"


class Bench(object):
    """Holds the assembled configuration and produces instrument readings."""

    def __init__(self, app):
        self.app = app
        self.placed = set()            # component ids placed on the desk
        self.wires = []                # (nodeA, nodeB, kind)
        self.clips = []                # list of dicts: id, arc (m), kind
        self.ring_station = None       # the ring that carries the crocodiles
        self.station_loc = "desk"      # "desk" or "block"
        self.ring_block_only = None    # a ring on the block, not wired
        self.braid = False
        self.dial_v = DIAL_OFF
        self.dial_a = DIAL_OFF
        self.scale_on = False
        self.scale_tare = 0.0
        self.power = False
        self.power_seconds = 0.0
        self.hot_seconds = 0.0
        self.screw_steps = 0           # 0 = solenoid touching the ring
        self.contact_scale = 1.0
        self.messages = []
        self._sol = None
        self._noise = None

    # ------------------------------------------------------------------
    @property
    def ring_on_block(self):
        if self.station_loc == "block" and self.ring_station:
            return self.ring_station
        return self.ring_block_only

    @property
    def ring_on_bench(self):
        return self.ring_station if self.station_loc == "desk" else None

    def z(self):
        return self.screw_steps * SCREW_STEP

    def ring_obj(self, key):
        return {"thin": self.app.thin, "open": self.app.open_broad,
                "closed": self.app.closed}.get(key)

    def note(self, msg):
        self.messages.append(msg)
        if len(self.messages) > 40:
            self.messages.pop(0)

    # ------------------------------------------------------------------
    def _wired_nodes(self):
        s = set()
        for a, b, _ in self.wires:
            s.add(a)
            s.add(b)
        return s

    def build_network(self):
        """Assemble the AC network for the present wiring. Returns (mna, info)."""
        app = self.app
        m = MNA()
        info = {"amm_idx": None, "src_idx": []}

        for a, b, kind in self.wires:
            r = app.r_wire_short if kind == "short" else app.r_wire_long
            m.add_z(a, b, r)

        # ---- power supply -------------------------------------------------
        if "psu" in self.placed and self.power:
            m.add_z("PS07A", "PS07i", app.r_internal)
            m.add_v("PS07i", "GND", app.v_source)
            m.add_z("PS07B", "GND", 1e-6)
            info["src_idx"].append(len(m.vsrc) - 1)
            m.add_z("PS24A", "PS24i", 0.5)
            m.add_v("PS24i", "GND", 24.0 * 1.0)
            m.add_z("PS24B", "GND", 1e-6)
        else:
            for nd in ("PS07A", "PS07B", "PS24A", "PS24B"):
                m.add_z(nd, "GND", 1e9)

        # ---- solenoid -----------------------------------------------------
        if "solenoid" in self.placed:
            m.add_z("SOLA", "SOLB", complex(2.0, OMEGA * 0.026))

        # ---- ammeter ------------------------------------------------------
        if "ammeter" in self.placed:
            if self.dial_a == DIAL_20A:
                m.add_z("AMCOM", "AMA", app.r_amm_shunt)
            elif self.dial_a == DIAL_20MA:
                m.add_z("AMCOM", "AMMA", 10.0)
            m.add_z("AMA", "AMA_open", 1e9)

        # ---- voltmeter ----------------------------------------------------
        if "voltmeter" in self.placed:
            if self.dial_v in (DIAL_200MV, DIAL_OHM):
                m.add_z("VMCOM", "VMV", app.r_volt_in)

        # ---- the ring being wired ----------------------------------------
        self._stamp_ring(m)
        return m, info

    def _stamp_ring(self, m):
        """Stamp the clipped ring (arc resistances + contacts + induced EMF)."""
        key = self.ring_on_bench or self.ring_on_block
        if key is None or not self.clips:
            return
        ring = self.ring_obj(key)
        clips = sorted(self.clips, key=lambda c: c["arc"])
        # chain of internal nodes along the conductor
        pts = [0.0] + [c["arc"] for c in clips] + [ring.length]
        names = ["RN%d" % i for i in range(len(pts))]
        emf = 0.0
        if self.power and key == self.ring_on_block and self._solenoid_energised():
            emf = self.app.emf_true(self.z())
            if not self.braid:
                emf *= 1.0 + self.app.lead_pick
        # the induced EMF is distributed uniformly along the conductor:
        # every arc carries its own share  eps * (arc / L_ring)
        for i in range(len(pts) - 1):
            seg = max(pts[i + 1] - pts[i], 1e-9)
            Rseg = ring.arc_resistance(seg)
            if emf != 0.0:
                mid = "RS%d" % i
                m.add_z(names[i], mid, Rseg)
                m.add_v(mid, names[i + 1], emf * seg / ring.length)
            else:
                m.add_z(names[i], names[i + 1], Rseg)
        if ring.gap <= 0.0:
            # closed ring : conductor wraps around
            m.add_z(names[-1], names[0], ring.arc_resistance(1e-4))
        # contacts (fixed the moment the crocodile is snapped on)
        for i, c in enumerate(clips):
            rc = c.get("rc", self.app.r_contact0) * self.contact_scale
            m.add_z(c["id"], names[i + 1], rc)

    def _solenoid_energised(self):
        """True when the solenoid is actually connected to the 24 V terminals."""
        need = {("PS24A", "SOLA"), ("PS24A", "SOLB"),
                ("PS24B", "SOLA"), ("PS24B", "SOLB")}
        seen = set()
        for a, b, _ in self.wires:
            for pair in ((a, b), (b, a)):
                if pair in need:
                    seen.add(pair)
        pos = any(p in seen for p in (("PS24A", "SOLA"), ("PS24A", "SOLB")))
        neg = any(p in seen for p in (("PS24B", "SOLA"), ("PS24B", "SOLB")))
        return pos and neg and "solenoid" in self.placed

    # ------------------------------------------------------------------
    def invalidate(self):
        self._sol = None
        self._noise = None

    def solution(self):
        """Solve the network once; both meters read the same instant."""
        if getattr(self, "_sol", None) is None:
            try:
                m, _ = self.build_network()
                volts, _ = m.solve()
            except Exception:
                volts = {}
            self._sol = volts
            self._noise = (self.app.rng.gauss(0.0, 0.030),
                           self.app.rng.gauss(0.0, 0.0035))
        return self._sol

    def read_voltmeter(self):
        """Return the string shown on the voltmeter display."""
        if "voltmeter" not in self.placed or self.dial_v == DIAL_OFF:
            return ""
        if self.dial_v in (DIAL_20A, DIAL_20MA):
            return "  0.00"        # no current flows into the V/Ohm jack
        if self.dial_v == DIAL_OHM:
            return "  0.2"          # useless for milliohms (contact dominated)
        volts = self.solution()
        v = abs(volts.get("VMV", 0j) - volts.get("VMCOM", 0j))
        mv = v * 1e3 * (1.0 + self.drift()) + self.app.emf_bias + self._noise[0]
        if mv > 199.9:
            return "   1."
        return "%5.1f" % (round(mv * 10.0) / 10.0)

    def read_ammeter(self):
        if "ammeter" not in self.placed or self.dial_a == DIAL_OFF:
            return ""
        if self.dial_a in (DIAL_200MV, DIAL_OHM):
            return "  0.0"         # nothing is wired to the V/Ohm jack of meter B
        volts = self.solution()
        if self.dial_a == DIAL_20A:
            i = abs(volts.get("AMCOM", 0j) - volts.get("AMA", 0j)) / \
                self.app.r_amm_shunt
        elif self.dial_a == DIAL_20MA:
            i = abs(volts.get("AMCOM", 0j) - volts.get("AMMA", 0j)) / 10.0
            if i > 0.02:
                return "   1."
        else:
            return ""
        i = i * (1.0 + self.drift()) + self._noise[1]
        if i > 19.99:
            return "   1."
        return "%6.2f" % (round(i * 100.0) / 100.0)

    def drift(self):
        """Slow rise of current/voltage while the 0.7 V circuit is loaded
        (contacts bedding in) - the ratio V/I stays constant."""
        t = min(self.power_seconds, 60.0)
        return 0.030 * (1.0 - math.exp(-t / 18.0))

    def read_scale(self):
        if not self.scale_on or "scale" not in self.placed:
            return ""
        grams = self.app.scale_zero_drift
        if self.ring_on_block is not None and "block" in self.placed:
            grams += self.ring_obj(self.ring_on_block).mass * 1e3
        elif self.ring_on_block is not None:
            grams += self.ring_obj(self.ring_on_block).mass * 1e3
        if self.ring_on_block == "closed" and self.power and self._solenoid_energised():
            grams += self.app.force_true(self.z()) / G_TELAVIV * 1e3
        elif self.ring_on_block == "open" and self.power and self._solenoid_energised():
            # open ring : no closed current loop -> almost no magnetic force
            grams += 0.02 * self.app.rng.uniform(-1, 1)
        grams -= self.scale_tare
        grams += self.app.rng.gauss(0.0, 0.012)
        return "%8.2f" % (round(grams * 100.0) / 100.0)

    def tick(self, dt):
        app = self.app
        heat = 0.0
        if self.power:
            self.power_seconds += dt
            if self._solenoid_energised() and self.ring_on_block == "closed":
                self.hot_seconds += dt
                # the induced current warms the ring: P = I^2 R
                R = app.r_closed()
                i = app.emf_true(self.z()) / math.hypot(R, OMEGA * app.L_closed)
                heat = i * i * R / (app.closed.mass * 900.0)
        else:
            self.power_seconds = max(0.0, self.power_seconds - dt * 0.5)
            self.hot_seconds = max(0.0, self.hot_seconds - dt)
        app.T_closed += (heat - app.T_closed / 240.0) * dt
        # heating slightly changes the closed ring resistivity
        if self.hot_seconds > 25.0:
            self.note(T("경고: 닫힌 링이 가열되고 있습니다. 전원을 잠시 끄십시오.",
                        "Warning: the closed ring is heating up. Release the power button."))
            self.hot_seconds = 0.0


# ============================================================================
#                                   GUI
# ============================================================================
PX_MM = 3.0          # canvas pixels per millimetre (drawn to scale)
BG = "#e8e4d9"
DESK = "#5f7d6e"
PAPER = "#f4f2e6"

COMPONENTS = [
    ("psu", T("50 Hz 교류 전원공급기", "50 Hz AC power supply")),
    ("solenoid", T("철심 솔레노이드 (수직 스크류)", "Iron-filled solenoid on screw")),
    ("voltmeter", T("멀티미터 A", "Multimeter A")),
    ("ammeter", T("멀티미터 B", "Multimeter B")),
    ("scale", T("디지털 저울 0.01 g", "Digital scale 0.01 g")),
    ("block", T("폴리스티렌 블록", "Polystyrene block")),
    ("ring_thin", T("얇은 열린 링", "Thin open ring")),
    ("ring_open", T("넓은 열린 링", "Broad open ring")),
    ("ring_closed", T("넓은 닫힌 링", "Broad closed ring")),
]

SLOTS = {
    "psu": (168, 40, 336, 176),
    "solenoid": (356, 26, 534, 214),
    "ringblock": (386, 216, 504, 244),
    "block": (380, 246, 510, 306),
    "scale": (352, 308, 538, 382),
    "voltmeter": (166, 196, 300, 344),
    "ammeter": (166, 360, 300, 508),
    "station": (556, 24, 1152, 612),
}

TERMINALS = {
    "PS24A": ("psu", 24, 118), "PS24B": ("psu", 48, 118),
    "PS07A": ("psu", 104, 118), "PS07B": ("psu", 136, 118),
    "SOLA": ("solenoid", 14, 150), "SOLB": ("solenoid", 14, 172),
    "VMCOM": ("voltmeter", 62, 132), "VMV": ("voltmeter", 98, 132),
    "AMA": ("ammeter", 26, 132), "AMMA": ("ammeter", 62, 132),
    "AMCOM": ("ammeter", 98, 132),
}
TERM_LABEL = {"PS24A": "24V", "PS24B": "24V", "PS07A": "0.7V", "PS07B": "0.7V",
              "SOLA": "SOL", "SOLB": "SOL", "VMCOM": "COM", "VMV": "V/\u03a9",
              "AMA": "20A", "AMMA": "mA", "AMCOM": "COM"}

RING_KEY = {"ring_thin": "thin", "ring_open": "open", "ring_closed": "closed"}


def rr(c, x0, y0, x1, y1, r=8, **kw):
    """rounded rectangle"""
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, **kw)


class Sim(object):
    def __init__(self, root, seed=None):
        self.root = root
        self.app = Apparatus(seed)
        self.b = Bench(self.app)
        root.title("HaslaLab \u2014 APhO 2011 E1 : " +
                   T("진동하는 자기장 속 도체의 부양",
                     "Levitation of Conductors in an Oscillating Magnetic Field"))
        root.configure(bg=BG)
        self.drag = None
        self.pending_term = None
        self.wire_kind = tk.StringVar(value="short")
        self.tool = tk.StringVar(value="none")
        self.ruler_pts = []
        self.ruler_label = tk.StringVar(value="")
        self.bench_ruler = []
        self.bench_ruler_label = tk.StringVar(value="")
        self.status = tk.StringVar(value=T("부품을 끌어다 놓아 실험을 조립하십시오.",
                                           "Drag the parts onto the desk to build the setup."))
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        self.tab_asm = tk.Frame(nb, bg=BG)
        self.tab_bench = tk.Frame(nb, bg=BG)
        nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.tab_bench, text=T(" 실험대 ", " Bench "))
        self._build_assembly()
        self._build_bench()
        self.redraw_asm()
        self.tick()

    # ================================================================
    #  assembly tab
    # ================================================================
    def _build_assembly(self):
        bar = tk.Frame(self.tab_asm, bg=BG)
        bar.pack(fill="x", padx=6, pady=3)
        tk.Label(bar, text=T("전선:", "Wire:"), bg=BG).pack(side="left")
        for val, txt in (("short", T("짧은 전선(3개)", "short (3)")),
                         ("long", T("긴 전선(2개)", "long (2)"))):
            tk.Radiobutton(bar, text=txt, value=val, variable=self.wire_kind,
                           bg=BG).pack(side="left")
        tk.Label(bar, text="   ", bg=BG).pack(side="left")
        tk.Radiobutton(bar, text=T("배선/집게 모드", "wire / clip"), value="none",
                       variable=self.tool, bg=BG).pack(side="left")
        tk.Radiobutton(bar, text=T("자(ruler) 모드", "ruler"), value="ruler",
                       variable=self.tool, bg=BG).pack(side="left")
        tk.Label(bar, textvariable=self.ruler_label, bg=BG, fg="#8a1c1c",
                 font=("TkDefaultFont", 10, "bold")).pack(side="left", padx=10)
        tk.Button(bar, text=T("배선 전체 삭제", "clear wiring"),
                  command=self.clear_wires).pack(side="right")
        tk.Label(self.tab_asm, textvariable=self.status, bg=BG,
                 anchor="w").pack(fill="x", padx=8)
        self.ca = tk.Canvas(self.tab_asm, width=1160, height=624, bg=DESK,
                            highlightthickness=0)
        self.ca.pack(padx=6, pady=4)
        self.ca.bind("<ButtonPress-1>", self.on_press)
        self.ca.bind("<B1-Motion>", self.on_motion)
        self.ca.bind("<ButtonRelease-1>", self.on_release)
        self.ca.bind("<Button-3>", self.on_right)

    # ---------------- drawing helpers ------------------------------
    def draw_psu(self, c, x, y):
        rr(c, x, y, x + 168, y + 136, 10, fill="#f2f1ec", outline="#8d8d86")
        c.create_text(x + 84, y + 12, text=T("교류 50 Hz", "AC 50 Hz"),
                      font=("TkDefaultFont", 8))
        c.create_oval(x + 12, y + 26, x + 30, y + 44,
                      fill="#ff5a3c" if self.b.power else "#8a3b30",
                      outline="#5a5a55")
        c.create_text(x + 21, y + 52, text=T("전원", "ON"), font=("TkDefaultFont", 7))
        # green push button
        c.create_oval(x + 118, y + 26, x + 152, y + 60,
                      fill="#2fa02f" if self.b.power else "#1c6b1c",
                      outline="#4a4a45", width=2)
        c.create_text(x + 135, y + 68, text=T("누름버튼", "push"),
                      font=("TkDefaultFont", 7))
        for nm in ("PS24A", "PS24B"):
            _, dx, dy = TERMINALS[nm]
            c.create_oval(x + dx - 6, y + dy - 6, x + dx + 6, y + dy + 6,
                          fill="#d33", outline="#222")
        for nm in ("PS07A", "PS07B"):
            _, dx, dy = TERMINALS[nm]
            c.create_oval(x + dx - 10, y + dy - 10, x + dx + 10, y + dy + 10,
                          fill="#222", outline="#111")
        c.create_text(x + 36, y + 96, text="24 V", font=("TkDefaultFont", 8))
        c.create_text(x + 120, y + 96, text="0.7 V", font=("TkDefaultFont", 8))

    def draw_solenoid(self, c, x, y):
        # vertical screw with handle
        c.create_rectangle(x + 78, y + 4, x + 92, y + 118, fill="#b9b9b0",
                           outline="#7a7a72")
        for i in range(14):
            yy = y + 8 + i * 8
            c.create_line(x + 78, yy, x + 92, yy + 4, fill="#8b8b83")
        ang = (self.b.screw_steps % 8) * math.pi / 4.0
        hx, hy = x + 85 + 26 * math.cos(ang), y + 8 + 9 * math.sin(ang)
        c.create_line(x + 85, y + 8, hx, hy, width=5, fill="#3a3a36")
        c.create_oval(hx - 5, hy - 5, hx + 5, hy + 5, fill="#222", outline="")
        # coil + iron rods
        gap_px = self.b.screw_steps * SCREW_STEP * 1e3 * PX_MM
        top = y + 118
        c.create_rectangle(x + 40, top, x + 130, top + 56, fill="#8a4a22",
                           outline="#5c2f14")
        for i in range(11):
            yy = top + 4 + i * 5
            c.create_line(x + 40, yy, x + 130, yy, fill="#a86230")
        for i in range(5):
            xx = x + 58 + i * 14
            c.create_rectangle(xx, top + 56, xx + 8, top + 62, fill="#4a4a4a",
                               outline="#2e2e2e")
        c.create_text(x + 85, top - 8, text=T("솔레노이드", "solenoid"),
                      font=("TkDefaultFont", 8), fill="#fff")
        for nm in ("SOLA", "SOLB"):
            _, dx, dy = TERMINALS[nm]
            c.create_oval(x + dx - 5, y + dy - 5, x + dx + 5, y + dy + 5,
                          fill="#c33", outline="#222")
        return top + 62, gap_px

    def draw_meter(self, c, x, y, dial, title):
        rr(c, x, y, x + 134, y + 148, 12, fill="#e8850f", outline="#a35c05")
        rr(c, x + 10, y + 8, x + 124, y + 140, 8, fill="#3b3b3b", outline="#222")
        rr(c, x + 18, y + 14, x + 116, y + 50, 4, fill="#c8d6c0", outline="#7d8a76")
        c.create_text(x + 67, y + 4, text=title, font=("TkDefaultFont", 8),
                      fill="#fff")
        txt = self.b.read_voltmeter() if dial is self.b.dial_v and \
            title.endswith("A") else self.b.read_ammeter()
        c.create_text(x + 112, y + 32, text=txt, anchor="e",
                      font=("Courier", 12, "bold"), fill="#101810")
        c.create_oval(x + 42, y + 58, x + 92, y + 108, fill="#1d1d1d",
                      outline="#555", width=2)
        order = [DIAL_OFF, DIAL_200MV, DIAL_20A, DIAL_20MA, DIAL_OHM]
        idx = order.index(dial) if dial in order else 0
        a = -math.pi / 2 + idx * 0.9
        c.create_line(x + 67, y + 83, x + 67 + 22 * math.cos(a),
                      y + 83 + 22 * math.sin(a), width=4, fill="#ddd")
        c.create_text(x + 67, y + 116, text=dial, font=("TkDefaultFont", 8),
                      fill="#ffd")
        for nm, dx, dy in [(k, v[1], v[2]) for k, v in TERMINALS.items()
                           if v[0] in ("voltmeter", "ammeter")]:
            pass
        return None

    def draw_scale(self, c, x, y, w=186, h=74):
        rr(c, x, y, x + w, y + h, 6, fill="#1d1d1d", outline="#000")
        c.create_rectangle(x + 0.06 * w, y + 0.08 * h, x + 0.94 * w,
                           y + 0.60 * h, fill="#c9ccce", outline="#888")
        rr(c, x + 0.09 * w, y + 0.68 * h, x + 0.45 * w, y + 0.92 * h, 4,
           fill="#a8b8a0", outline="#555")
        c.create_text(x + 0.63 * w, y + 0.80 * h, text="TARE",
                      font=("TkDefaultFont", 7), fill="#ddd")
        c.create_text(x + 0.84 * w, y + 0.80 * h, text="ON/OFF",
                      font=("TkDefaultFont", 7), fill="#ddd")

    def draw_block(self, c, x, y, w=130, h=60):
        d = 0.22 * h
        c.create_polygon(x, y + d, x + d, y, x + w, y, x + w, y + h - d,
                         x + w - d, y + h, x, y + h, fill="#f0f0ee",
                         outline="#b5b5ae")
        c.create_line(x, y + d, x + w - d, y + d, fill="#c8c8c2")
        c.create_line(x + w - d, y + d, x + w - d, y + h, fill="#c8c8c2")
        c.create_line(x + w - d, y + d, x + w, y, fill="#c8c8c2")
        c.create_text(x + 0.45 * w, y + 0.55 * h,
                      text=T("폴리스티렌 8\u00d77\u00d77 cm",
                             "polystyrene 8\u00d77\u00d77 cm"),
                      font=("TkDefaultFont", 7), fill="#8a8a84")

    def draw_ring_side(self, c, x, y, key):
        ring = self.b.ring_obj(key)
        w = ring.d_out * 1e3 * PX_MM
        h = max(ring.height * 1e3 * PX_MM, 4)
        c.create_rectangle(x - w / 2, y - h, x + w / 2, y, fill="#c9ccd0",
                           outline="#7d8085")

    # ---------------- station (ring + clips + mm paper) -------------
    def station_geom(self):
        x0, y0, x1, y1 = SLOTS["station"]
        return (x0 + x1) / 2.0, (y0 + y1) / 2.0 + 6

    def clip_xy(self, arc, key):
        ring = self.b.ring_obj(key)
        cx, cy = self.station_geom()
        d = ring.gap / (2.0 * ring.r_mean)
        th = math.pi / 2 + d + arc / ring.r_mean
        r = ring.r_mean * 1e3 * PX_MM
        return cx + r * math.cos(th), cy - r * math.sin(th)

    def xy_to_arc(self, x, y, key):
        ring = self.b.ring_obj(key)
        cx, cy = self.station_geom()
        dx, dy = x - cx, cy - y
        rad = math.hypot(dx, dy) / PX_MM / 1e3
        if abs(rad - ring.r_mean) > 0.004:
            return None
        th = math.atan2(dy, dx)
        d = ring.gap / (2.0 * ring.r_mean)
        s = (th - math.pi / 2 - d) % (2 * math.pi) * ring.r_mean
        if s > ring.length:
            return None
        return s

    def draw_station(self, c):
        x0, y0, x1, y1 = SLOTS["station"]
        c.create_rectangle(x0, y0, x1, y1, fill=PAPER, outline="#c9c6b5")
        for gx in range(int(x0), int(x1), 3):
            c.create_line(gx, y0, gx, y1, fill="#e3e0cf")
        for gy in range(int(y0), int(y1), 3):
            c.create_line(x0, gy, x1, gy, fill="#e3e0cf")
        for gx in range(int(x0), int(x1), 30):
            c.create_line(gx, y0, gx, y1, fill="#c7c0a6")
        for gy in range(int(y0), int(y1), 30):
            c.create_line(x0, gy, x1, gy, fill="#c7c0a6")
        c.create_text(x0 + 96, y0 + 12,
                      text=T("배선 스테이션 \u2014 밀리미터 모눈종이 (1 mm 격자)",
                             "wiring station \u2014 millimetre paper (1 mm grid)"),
                      font=("TkDefaultFont", 8), fill="#7a7663")
        key = self.b.ring_station
        if key is None:
            c.create_text((x0 + x1) / 2, (y0 + y1) / 2,
                          text=T("링을 여기로 끌어다 놓으십시오",
                                 "drag a ring here"), fill="#a9a493")
            return
        ring = self.b.ring_obj(key)
        cx, cy = self.station_geom()
        ro = ring.d_out * 1e3 * PX_MM / 2
        ri = ring.d_in * 1e3 * PX_MM / 2
        c.create_oval(cx - ro, cy - ro, cx + ro, cy + ro, fill="#c9ccd0",
                      outline="#6f7378", width=1)
        c.create_oval(cx - ri, cy - ri, cx + ri, cy + ri, fill=PAPER,
                      outline="#6f7378", width=1)
        if ring.gap > 0:
            half = math.degrees(ring.gap / (2.0 * ring.r_mean))
            c.create_arc(cx - ro, cy - ro, cx + ro, cy + ro,
                         start=90 - half, extent=2 * half, style="pieslice",
                         fill=PAPER, outline=PAPER)
            c.create_arc(cx - ro, cy - ro, cx + ro, cy + ro,
                         start=90 - half, extent=2 * half, style="arc",
                         outline=PAPER, width=2)
        for cl in self.b.clips:
            px, py = self.clip_xy(cl["arc"], key)
            c.create_oval(px - 7, py - 7, px + 7, py + 7, fill="#1c1c1c",
                          outline="#dd3")
            c.create_text(px, py, text=cl["id"][-1], fill="#fff",
                          font=("TkDefaultFont", 7, "bold"))
        c.create_text(cx, cy - 12, text={"thin": T("얇은 열린 링", "thin open"),
                                         "open": T("넓은 열린 링", "broad open"),
                                         "closed": T("넓은 닫힌 링", "broad closed")}[key],
                      fill="#8a8676", font=("TkDefaultFont", 8))
        c.create_text(cx, cy + 10,
                      text=T("위치: ", "location: ") +
                      (T("책상 위", "on the desk") if self.b.station_loc == "desk"
                       else T("블록 위(솔레노이드 아래)", "on the block")),
                      fill="#8a8676", font=("TkDefaultFont", 8))
        if self.ruler_pts:
            for (px, py) in self.ruler_pts:
                c.create_line(px - 6, py, px + 6, py, fill="#b02", width=2)
                c.create_line(px, py - 6, px, py + 6, fill="#b02", width=2)
            if len(self.ruler_pts) == 2:
                c.create_line(self.ruler_pts[0][0], self.ruler_pts[0][1],
                              self.ruler_pts[1][0], self.ruler_pts[1][1],
                              fill="#b02", width=1, dash=(3, 2))

    # ---------------- full assembly redraw --------------------------
    def redraw_asm(self):
        c = self.ca
        c.delete("all")
        # palette
        c.create_rectangle(4, 4, 158, 618, fill="#cfd8cf", outline="#93a093")
        c.create_text(81, 16, text=T("부품 상자", "parts box"),
                      font=("TkDefaultFont", 9, "bold"))
        self.palette_boxes = []
        yy = 32
        for key, label in COMPONENTS:
            placed = (key in self.b.placed or
                      (key in RING_KEY and RING_KEY[key] in
                       (self.b.ring_station, self.b.ring_block_only)))
            fill = "#9fae9f" if placed else "#f3f6f3"
            rr(c, 10, yy, 152, yy + 56, 6, fill=fill, outline="#7d8a7d")
            c.create_text(81, yy + 12, text=label, font=("TkDefaultFont", 8),
                          width=136)
            c.create_text(81, yy + 40,
                          text=T("(배치됨)", "(placed)") if placed
                          else T("끌어다 놓기", "drag me"),
                          font=("TkDefaultFont", 7), fill="#555")
            self.palette_boxes.append((key, 10, yy, 152, yy + 56))
            yy += 62
        # slots
        for name, (x0, y0, x1, y1) in SLOTS.items():
            if name == "station":
                continue
            c.create_rectangle(x0, y0, x1, y1, outline="#8fa39a", dash=(4, 3))
        self.draw_station(c)
        b = self.b
        if "scale" in b.placed:
            x0, y0, _, _ = SLOTS["scale"]
            self.draw_scale(c, x0, y0)
        if "block" in b.placed:
            x0, y0, _, _ = SLOTS["block"]
            self.draw_block(c, x0, y0)
        if b.ring_on_block:
            x0, y0, x1, y1 = SLOTS["ringblock"]
            self.draw_ring_side(c, (x0 + x1) / 2, y1, b.ring_on_block)
        if "solenoid" in b.placed:
            x0, y0, _, _ = SLOTS["solenoid"]
            self.draw_solenoid(c, x0, y0)
        if "psu" in b.placed:
            x0, y0, _, _ = SLOTS["psu"]
            self.draw_psu(c, x0, y0)
        if "voltmeter" in b.placed:
            x0, y0, _, _ = SLOTS["voltmeter"]
            self.draw_meter(c, x0, y0, b.dial_v, T("멀티미터 A", "Multimeter A"))
        if "ammeter" in b.placed:
            x0, y0, _, _ = SLOTS["ammeter"]
            self.draw_meter(c, x0, y0, b.dial_a, T("멀티미터 B", "Multimeter B"))
        # terminals
        self.term_xy = {}
        for nm, (dev, dx, dy) in TERMINALS.items():
            if dev not in b.placed:
                continue
            x0, y0, _, _ = SLOTS[dev]
            px, py = x0 + dx, y0 + dy
            self.term_xy[nm] = (px, py)
            if dev in ("voltmeter", "ammeter"):
                c.create_oval(px - 7, py - 7, px + 7, py + 7, fill="#111",
                              outline="#e8850f", width=2)
                c.create_text(px, py + 15, text=TERM_LABEL[nm], fill="#fff",
                              font=("TkDefaultFont", 7))
            if self.pending_term == nm:
                c.create_oval(px - 11, py - 11, px + 11, py + 11,
                              outline="#ffd400", width=2)
        for cl in b.clips:
            if b.ring_station:
                self.term_xy[cl["id"]] = self.clip_xy(cl["arc"], b.ring_station)
        # wires
        for (a, bb, kind) in b.wires:
            if a in self.term_xy and bb in self.term_xy:
                x1, y1 = self.term_xy[a]
                x2, y2 = self.term_xy[bb]
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2 + (30 if kind == "long" else 14)
                c.create_line(x1, y1, mx, my, x2, y2, smooth=True, width=3,
                              fill="#c0392b" if kind == "short" else "#2c3e88")
        if self.drag:
            x, y, key = self.drag
            rr(c, x - 40, y - 16, x + 40, y + 16, 5, fill="#fffbe0",
               outline="#b8a800")
            c.create_text(x, y, text=dict(COMPONENTS)[key],
                          font=("TkDefaultFont", 7), width=76)

    # ---------------- assembly interaction --------------------------
    def on_press(self, e):
        if self.tool.get() == "ruler":
            x0, y0, x1, y1 = SLOTS["station"]
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                self.ruler_pts.append((e.x, e.y))
                if len(self.ruler_pts) > 2:
                    self.ruler_pts = [(e.x, e.y)]
                if len(self.ruler_pts) == 2:
                    (ax, ay), (bx, by) = self.ruler_pts
                    mm = math.hypot(bx - ax, by - ay) / PX_MM
                    mm = round(mm * 2.0) / 2.0
                    self.ruler_label.set(T("자 판독: %.2f cm", "ruler: %.2f cm")
                                         % (mm / 10.0))
                else:
                    self.ruler_label.set(T("두 번째 점을 클릭", "click 2nd point"))
                self.redraw_asm()
            return
        # clip on the ring?
        key = self.b.ring_station
        if key:
            for cl in self.b.clips:
                px, py = self.clip_xy(cl["arc"], key)
                if math.hypot(e.x - px, e.y - py) < 10:
                    self.dragclip = cl
                    return
        # terminal / clip click -> wiring
        for nm, (px, py) in getattr(self, "term_xy", {}).items():
            if math.hypot(e.x - px, e.y - py) < 11:
                self.click_terminal(nm)
                return
        # palette pick-up
        for (k, x0, y0, x1, y1) in getattr(self, "palette_boxes", []):
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                self.drag = (e.x, e.y, k)
                self.redraw_asm()
                return
        # empty click on the ring -> add clip
        if key:
            arc = self.xy_to_arc(e.x, e.y, key)
            if arc is not None:
                self.add_clip(arc)

    def on_motion(self, e):
        if getattr(self, "dragclip", None):
            key = self.b.ring_station
            arc = self.xy_to_arc(e.x, e.y, key)
            if arc is not None:
                self.dragclip["arc"] = arc
                self.b.invalidate()
                self.redraw_asm()
            return
        if self.drag:
            self.drag = (e.x, e.y, self.drag[2])
            self.redraw_asm()

    def on_release(self, e):
        if getattr(self, "dragclip", None):
            self.dragclip = None
            return
        if not self.drag:
            return
        key = self.drag[2]
        self.drag = None
        self.place(key, e.x, e.y)
        self.redraw_asm()

    def on_right(self, e):
        key = self.b.ring_station
        if key:
            for cl in list(self.b.clips):
                px, py = self.clip_xy(cl["arc"], key)
                if math.hypot(e.x - px, e.y - py) < 10:
                    self.b.wires = [w for w in self.b.wires
                                    if cl["id"] not in (w[0], w[1])]
                    self.b.clips.remove(cl)
                    self.b.invalidate()
                    self.redraw_asm()
                    return
        for w in list(self.b.wires):
            if w[0] in self.term_xy and w[1] in self.term_xy:
                x1, y1 = self.term_xy[w[0]]
                x2, y2 = self.term_xy[w[1]]
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2 + (30 if w[2] == "long" else 14)
                if math.hypot(e.x - mx, e.y - my) < 14:
                    self.b.wires.remove(w)
                    self.b.invalidate()
                    self.redraw_asm()
                    return
        # right click on a placed component -> take it back
        for name, (x0, y0, x1, y1) in SLOTS.items():
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                self.remove_slot(name)
                self.redraw_asm()
                return

    def in_slot(self, name, x, y):
        x0, y0, x1, y1 = SLOTS[name]
        return x0 <= x <= x1 and y0 <= y <= y1

    def place(self, key, x, y):
        b = self.b
        if key in RING_KEY:
            rk = RING_KEY[key]
            if self.in_slot("station", x, y):
                if b.ring_station and b.ring_station != rk:
                    self.status.set(T("스테이션에는 링을 하나만 놓을 수 있습니다.",
                                      "only one ring fits on the station."))
                    return
                b.ring_station = rk
                b.station_loc = "desk"
                b.clips = []
                self.status.set(T("링을 스테이션에 놓았습니다. 링 위를 클릭하여 악어집게를 부착하십시오.",
                                  "Ring on the station. Click on the ring to snap crocodile clips."))
            elif self.in_slot("ringblock", x, y) or self.in_slot("block", x, y):
                if "block" not in b.placed:
                    self.status.set(T("먼저 저울 위에 폴리스티렌 블록을 놓으십시오.",
                                      "Place the polystyrene block on the scale first."))
                    return
                if b.ring_on_block:
                    self.status.set(T("블록 위에 이미 링이 있습니다.",
                                      "A ring is already on the block."))
                    return
                b.ring_block_only = rk
                self.status.set(T("링을 블록 위에 놓았습니다.", "Ring placed on the block."))
            else:
                self.status.set(T("링은 배선 스테이션 또는 블록 위에만 놓을 수 있습니다.",
                                  "Rings go on the wiring station or on the block."))
                return
            b.invalidate()
            return
        if key == "block" and "scale" not in b.placed:
            self.status.set(T("블록은 저울 위에 놓아야 합니다. 저울을 먼저 배치하십시오.",
                              "The block must rest on the scale - place the scale first."))
            return
        if not self.in_slot(key, x, y):
            self.status.set(T("점선으로 표시된 자리에 놓으십시오.",
                              "Drop it on the dashed outline for that part."))
            return
        b.placed.add(key)
        b.invalidate()
        self.status.set(T("배치 완료: ", "placed: ") + dict(COMPONENTS)[key])

    def remove_slot(self, name):
        b = self.b
        if name == "station" and b.ring_station:
            b.wires = [w for w in b.wires
                       if not (w[0].startswith("CLIP") or w[1].startswith("CLIP"))]
            b.clips = []
            b.ring_station = None
        elif name in ("ringblock",) and b.ring_block_only:
            b.ring_block_only = None
        elif name in b.placed:
            if name == "scale" and "block" in b.placed:
                self.status.set(T("블록을 먼저 치우십시오.", "Remove the block first."))
                return
            if name == "block" and b.ring_on_block:
                self.status.set(T("블록 위의 링을 먼저 치우십시오.",
                                  "Remove the ring from the block first."))
                return
            b.placed.discard(name)
            b.wires = [w for w in b.wires
                       if TERMINALS.get(w[0], ("", 0, 0))[0] != name and
                       TERMINALS.get(w[1], ("", 0, 0))[0] != name]
        b.invalidate()

    def add_clip(self, arc):
        b = self.b
        if len(b.clips) >= 4:
            self.status.set(T("악어집게는 4개뿐입니다.", "Only four crocodile clips."))
            return
        n = len(b.clips) + 1
        rc = self.app.r_contact0 * self.app.rng.uniform(0.6, 1.6)
        b.clips.append({"id": "CLIP%d" % n, "arc": arc, "kind": "?", "rc": rc})
        b.invalidate()
        self.status.set(T("집게 %d 부착. 끌어서 위치를 조정할 수 있습니다.",
                          "clip %d attached; drag to move.") % n)
        self.redraw_asm()

    def click_terminal(self, nm):
        if self.pending_term is None:
            self.pending_term = nm
            self.status.set(T("%s 선택 \u2014 연결할 상대 단자를 클릭하십시오.",
                              "%s selected - click the other terminal.") % nm)
        elif self.pending_term == nm:
            self.pending_term = None
            self.status.set("")
        else:
            kind = self.wire_kind.get()
            used = sum(1 for w in self.b.wires if w[2] == kind)
            if (kind == "short" and used >= 3) or (kind == "long" and used >= 2):
                self.status.set(T("그 종류의 전선을 모두 사용했습니다.",
                                  "No more wires of that type."))
            else:
                self.b.wires.append((self.pending_term, nm, kind))
                self.b.invalidate()
                self.status.set(T("연결: %s \u2014 %s", "connected %s - %s")
                                % (self.pending_term, nm))
            self.pending_term = None
        self.redraw_asm()

    def clear_wires(self):
        self.b.wires = []
        self.b.invalidate()
        self.redraw_asm()

    # ================================================================
    #  bench tab
    # ================================================================
    def _build_bench(self):
        left = tk.Frame(self.tab_bench, bg=BG)
        left.pack(side="left", fill="y", padx=8, pady=6)

        # ---- power supply ------------------------------------------
        f = tk.LabelFrame(left, text=T("교류 전원공급기 (50 Hz)", "AC power supply (50 Hz)"),
                          bg=BG, padx=6, pady=4)
        f.pack(fill="x")
        self.lamp = tk.Label(f, text="\u25cf", font=("TkDefaultFont", 18),
                             fg="#8a3b30", bg=BG)
        self.lamp.grid(row=0, column=0)
        bt = tk.Button(f, text=T("초록 버튼 (누르고 있기)", "green button (hold)"),
                       bg="#2fa02f", activebackground="#57c957", fg="#fff")
        bt.grid(row=0, column=1, padx=6)
        bt.bind("<ButtonPress-1>", lambda e: self.set_power(True))
        bt.bind("<ButtonRelease-1>", lambda e: self.set_power(False))
        self.lock = tk.IntVar(value=0)
        tk.Checkbutton(f, text=T("버튼 고정", "latch"), variable=self.lock, bg=BG,
                       command=lambda: self.set_power(bool(self.lock.get()))
                       ).grid(row=0, column=2)

        # ---- multimeters -------------------------------------------
        self.disp_v = tk.StringVar(value="")
        self.disp_a = tk.StringVar(value="")
        for title, var, dialvar, setter in (
                (T("멀티미터 A", "Multimeter A"), self.disp_v, "dial_v", "v"),
                (T("멀티미터 B", "Multimeter B"), self.disp_a, "dial_a", "a")):
            g = tk.LabelFrame(left, text=title, bg=BG, padx=6, pady=4)
            g.pack(fill="x", pady=3)
            tk.Label(g, textvariable=var, font=("Courier", 22, "bold"),
                     bg="#c8d6c0", fg="#101810", width=9, anchor="e"
                     ).grid(row=0, column=0, rowspan=2, padx=(0, 8))
            cb = ttk.Combobox(g, values=[DIAL_OFF, DIAL_200MV, DIAL_20A,
                                         DIAL_20MA, DIAL_OHM],
                              state="readonly", width=8)
            cb.set(DIAL_OFF)
            cb.grid(row=0, column=1)
            cb.bind("<<ComboboxSelected>>",
                    lambda e, s=setter, c=cb: self.set_dial(s, c.get()))
            if setter == "v":
                self.cb_v = cb
            else:
                self.cb_a = cb
            tk.Label(g, text=T("다이얼", "dial"), bg=BG,
                     font=("TkDefaultFont", 7)).grid(row=1, column=1)

        # ---- scale --------------------------------------------------
        g = tk.LabelFrame(left, text=T("디지털 저울", "digital scale"), bg=BG,
                          padx=6, pady=4)
        g.pack(fill="x", pady=3)
        self.disp_s = tk.StringVar(value="")
        tk.Label(g, textvariable=self.disp_s, font=("Courier", 20, "bold"),
                 bg="#a8b8a0", fg="#101810", width=10, anchor="e"
                 ).grid(row=0, column=0, rowspan=2, padx=(0, 8))
        self.scale_var = tk.IntVar(value=0)
        tk.Checkbutton(g, text="ON/OFF", variable=self.scale_var, bg=BG,
                       command=self.toggle_scale).grid(row=0, column=1)
        tk.Button(g, text="TARE", command=self.do_tare).grid(row=1, column=1)
        tk.Label(g, text=T("(g 단위, 0.01 g)", "(grams, 0.01 g)"), bg=BG,
                 font=("TkDefaultFont", 7)).grid(row=2, column=0, columnspan=2)

        # ---- screw --------------------------------------------------
        g = tk.LabelFrame(left, text=T("솔레노이드 수직 스크류", "solenoid screw"),
                          bg=BG, padx=6, pady=4)
        g.pack(fill="x", pady=3)
        self.steps_var = tk.StringVar(value="0")
        tk.Label(g, textvariable=self.steps_var, font=("Courier", 16, "bold"),
                 bg=BG).grid(row=0, column=0, columnspan=4)
        tk.Label(g, text=T("스크류 회전 단계 수(계수)", "screw steps counted"),
                 bg=BG, font=("TkDefaultFont", 7)).grid(row=1, column=0, columnspan=4)
        for i, (txt, d) in enumerate((("\u25bc\u25bc", -5), ("\u25bc", -1),
                                      ("\u25b2", +1), ("\u25b2\u25b2", +5))):
            tk.Button(g, text=txt, width=4,
                      command=lambda d=d: self.turn(d)).grid(row=2, column=i)
        self.contact_var = tk.StringVar(value="")
        tk.Label(g, textvariable=self.contact_var, bg=BG, fg="#8a1c1c",
                 font=("TkDefaultFont", 8)).grid(row=3, column=0, columnspan=4)

        # ---- ring location / braid ---------------------------------
        g = tk.LabelFrame(left, text=T("배선한 링의 위치", "location of the wired ring"),
                          bg=BG, padx=6, pady=4)
        g.pack(fill="x", pady=3)
        self.loc_var = tk.StringVar(value="desk")
        for val, txt in (("desk", T("책상 위", "on the desk")),
                         ("block", T("블록 위(솔레노이드 아래)", "on the block"))):
            tk.Radiobutton(g, text=txt, value=val, variable=self.loc_var,
                           bg=BG, command=self.set_loc).pack(anchor="w")
        self.braid_var = tk.IntVar(value=0)
        tk.Checkbutton(g, text=T("리드선을 꼬아 묶음", "twist the leads into a braid"),
                       variable=self.braid_var, bg=BG,
                       command=self.set_braid).pack(anchor="w")

        tk.Button(left, text=T("계기 판독값 기록", "record the readings"),
                  command=self.record).pack(fill="x", pady=(6, 2))
        self.log = tk.Text(left, width=52, height=13, font=("Courier", 8))
        self.log.pack(fill="both", expand=True)

        # ---- bench canvas ------------------------------------------
        right = tk.Frame(self.tab_bench, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        tb = tk.Frame(right, bg=BG)
        tb.pack(fill="x")
        tk.Radiobutton(tb, text=T("보기", "view"), value="none",
                       variable=self.tool, bg=BG).pack(side="left")
        tk.Radiobutton(tb, text=T("자(ruler)", "ruler"), value="ruler",
                       variable=self.tool, bg=BG).pack(side="left")
        tk.Label(tb, textvariable=self.bench_ruler_label, bg=BG, fg="#8a1c1c",
                 font=("TkDefaultFont", 10, "bold")).pack(side="left", padx=8)
        self.cb = tk.Canvas(right, width=660, height=600, bg=DESK,
                            highlightthickness=0)
        self.cb.pack(padx=4, pady=4)
        self.cb.bind("<Button-1>", self.bench_click)

    # ---------------- bench actions -----------------------------------
    def set_power(self, on):
        if self.lock.get() and not on:
            return
        self.b.power = on and ("psu" in self.b.placed)
        self.b.invalidate()
        self.refresh()

    def set_dial(self, which, value):
        if which == "v":
            self.b.dial_v = value
            if hasattr(self, "cb_v"):
                self.cb_v.set(value)
        else:
            self.b.dial_a = value
            if hasattr(self, "cb_a"):
                self.cb_a.set(value)
        self.b.invalidate()
        self.refresh()
        self.redraw_asm()

    def toggle_scale(self):
        self.b.scale_on = bool(self.scale_var.get())
        if not self.b.scale_on:
            self.b.scale_tare = 0.0
        self.refresh()

    def do_tare(self):
        if not self.b.scale_on:
            return
        s = self.b.read_scale()
        try:
            self.b.scale_tare += float(s)
        except ValueError:
            pass
        self.refresh()

    def turn(self, d):
        self.b.screw_steps = max(0, self.b.screw_steps + d)
        self.b.invalidate()
        self.refresh()
        self.redraw_asm()

    def set_loc(self):
        loc = self.loc_var.get()
        if loc == "block":
            if "block" not in self.b.placed:
                self.loc_var.set("desk")
                self.status.set(T("먼저 저울 위에 블록을 놓으십시오.",
                                  "Place the block on the scale first."))
                return
            if self.b.ring_block_only:
                self.loc_var.set("desk")
                self.status.set(T("블록 위에 이미 다른 링이 있습니다.",
                                  "Another ring already occupies the block."))
                return
        self.b.station_loc = loc
        self.b.invalidate()
        self.refresh()
        self.redraw_asm()

    def set_braid(self):
        self.b.braid = bool(self.braid_var.get())
        self.b.invalidate()

    def record(self):
        b = self.b
        row = T("스크류 %3d 단 | A: %s | B: %s | 저울: %s g",
                "screw %3d | A: %s | B: %s | scale: %s g") % (
            b.screw_steps, b.read_voltmeter() or "----",
            b.read_ammeter() or "----", b.read_scale() or "-----")
        self.log.insert("end", row + "\n")
        self.log.see("end")

    def bench_click(self, e):
        if self.tool.get() != "ruler":
            return
        self.bench_ruler.append((e.x, e.y))
        if len(self.bench_ruler) > 2:
            self.bench_ruler = [(e.x, e.y)]
        if len(self.bench_ruler) == 2:
            (ax, ay), (bx, by) = self.bench_ruler
            mm = round(math.hypot(bx - ax, by - ay) / PX_MM * 2.0) / 2.0
            self.bench_ruler_label.set(T("자 판독: %.1f mm", "ruler: %.1f mm") % mm)
        else:
            self.bench_ruler_label.set(T("두 번째 점을 클릭", "click 2nd point"))
        self.draw_bench()

    # ---------------- bench drawing -----------------------------------
    def draw_bench(self):
        c = self.cb
        c.delete("all")
        c.create_rectangle(0, 0, 660, 600, fill=PAPER, outline="")
        for gx in range(0, 660, 3):
            c.create_line(gx, 0, gx, 600, fill="#e6e3d2")
        for gy in range(0, 600, 3):
            c.create_line(0, gy, 660, gy, fill="#e6e3d2")
        for gx in range(0, 660, 30):
            c.create_line(gx, 0, gx, 600, fill="#cbc4aa")
        for gy in range(0, 600, 30):
            c.create_line(0, gy, 660, gy, fill="#cbc4aa")
        c.create_text(120, 12, text=T("실험대 정면도 (실제 축척 1 mm 격자)",
                                      "bench elevation (true scale, 1 mm grid)"),
                      font=("TkDefaultFont", 8), fill="#7a7663")
        b = self.b
        cx = 330
        base = 588
        if "scale" in b.placed:
            self.draw_scale(c, cx - 165, base - 46, 330, 46)
        else:
            c.create_text(cx, base - 20, text=T("(저울 없음)", "(no scale)"),
                          fill="#999")
        top_of = base - 46
        if "block" in b.placed:
            self.draw_block(c, cx - 120, top_of - 116, 240, 116)
            c.create_text(cx + 150, top_of - 58, text="\u2248",
                          font=("TkDefaultFont", 14), fill="#999")
            top_of -= 116
        ring_top = top_of
        if b.ring_on_block:
            ring = b.ring_obj(b.ring_on_block)
            h = max(ring.height * 1e3 * PX_MM, 4)
            w = ring.d_out * 1e3 * PX_MM
            wi = ring.d_in * 1e3 * PX_MM
            c.create_rectangle(cx - w / 2, top_of - h, cx - wi / 2, top_of,
                               fill="#c9ccd0", outline="#6f7378")
            c.create_rectangle(cx + wi / 2, top_of - h, cx + w / 2, top_of,
                               fill="#c9ccd0", outline="#6f7378")
            c.create_line(cx - wi / 2, top_of - h / 2, cx + wi / 2,
                          top_of - h / 2, fill="#b9bcc0", dash=(2, 2))
            ring_top = top_of - h
        else:
            c.create_text(cx, top_of - 14, text=T("(링 없음)", "(no ring)"),
                          fill="#999", font=("TkDefaultFont", 8))
        gap_px = b.screw_steps * SCREW_STEP * 1e3 * PX_MM
        sol_bottom = ring_top - gap_px
        c.create_rectangle(cx - 90, sol_bottom - 168, cx + 90, sol_bottom - 12,
                           fill="#8a4a22", outline="#5c2f14")
        for i in range(16):
            yy = sol_bottom - 164 + i * 10
            c.create_line(cx - 90, yy, cx + 90, yy, fill="#a86230")
        for i in range(7):
            xx = cx - 63 + i * 18
            c.create_rectangle(xx, sol_bottom - 12, xx + 10, sol_bottom,
                               fill="#4a4a4a", outline="#2e2e2e")
        c.create_text(cx, sol_bottom - 180, text=T("솔레노이드 (철심)",
                                                   "solenoid (iron core)"),
                      font=("TkDefaultFont", 8), fill="#7a7663")
        c.create_rectangle(cx - 12, 24, cx + 12, sol_bottom - 168,
                           fill="#b9b9b0", outline="#7a7a72")
        yy = 30
        while yy < sol_bottom - 172:
            c.create_line(cx - 12, yy, cx + 12, yy + 6, fill="#8b8b83")
            yy += 12
        ang = (b.screw_steps % 8) * math.pi / 4.0
        c.create_line(cx, 30, cx + 40 * math.cos(ang), 30 + 12 * math.sin(ang),
                      width=6, fill="#3a3a36")
        if gap_px > 2:
            c.create_line(cx + 130, sol_bottom, cx + 130, ring_top,
                          fill="#b02", arrow="both")
            c.create_text(cx + 150, (sol_bottom + ring_top) / 2, text="z",
                          fill="#b02", font=("TkDefaultFont", 11, "bold"))
        elif b.ring_on_block:
            c.create_text(cx + 150, ring_top - 8, text=T("접촉 (z = 0)",
                                                         "contact (z = 0)"),
                          fill="#b02", font=("TkDefaultFont", 9, "bold"))
        if b.power and b._solenoid_energised():
            for k in range(6):
                rad = 22 + k * 16
                c.create_arc(cx - rad, sol_bottom - rad * 0.5, cx + rad,
                             sol_bottom + rad * 0.5, start=200, extent=140,
                             style="arc", outline="#3a6ea5", dash=(2, 3))
        for (px, py) in self.bench_ruler:
            c.create_line(px - 6, py, px + 6, py, fill="#b02", width=2)
            c.create_line(px, py - 6, px, py + 6, fill="#b02", width=2)
        if len(self.bench_ruler) == 2:
            c.create_line(self.bench_ruler[0][0], self.bench_ruler[0][1],
                          self.bench_ruler[1][0], self.bench_ruler[1][1],
                          fill="#b02", dash=(3, 2))

    # ---------------- refresh / timer ---------------------------------
    def refresh(self):
        b = self.b
        self.disp_v.set(b.read_voltmeter())
        self.disp_a.set(b.read_ammeter())
        self.disp_s.set(b.read_scale())
        self.steps_var.set("%d" % b.screw_steps)
        self.lamp.configure(fg="#ff5a3c" if b.power else "#8a3b30")
        if b.screw_steps == 0 and b.ring_on_block:
            self.contact_var.set(T("솔레노이드가 링에 닿아 있습니다.",
                                   "the solenoid touches the ring"))
        else:
            self.contact_var.set("")
        if b.messages:
            self.status.set(b.messages[-1])
        self.draw_bench()

    def tick(self):
        self.b.tick(0.25)
        self.b.invalidate()
        self.refresh()
        self.root.after(250, self.tick)


def main():
    import sys
    seed = None
    global LANG
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--seed" and i + 1 < len(args):
            seed = int(args[i + 1])
        if a == "--lang" and i + 1 < len(args):
            LANG = args[i + 1]
    root = tk.Tk()
    Sim(root, seed)
    root.mainloop()


if __name__ == "__main__":
    main()
