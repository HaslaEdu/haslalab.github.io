#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  International Scientific Physics Olympiad  (ISPhO 2025, MIPT)
  Experimental Problem 1 :  LED COLOR
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Apparatus after the problem sheet: a magnetic optical table with the
    LED stand, lens L1, lens L2 carrying a diffraction grating and the
    screen with a CCD array of 3650 pixels read by a computer program;
    an "RGB" LED (620 / 520 / 460 nm) for the calibration; a "MAIN" LED
    in a cuvette (and a reserve), an adapter with a switch, a DC source
    up to 15 V, two multimeters (input ~1 MOhm on DC volts), a resistor
    R0, distilled water, a pipette, liquid nitrogen scooped with a tube
    on a thread, a waste beaker and a shielding box.
    The LED is a real junction: I = I0(T) (exp(eU/(eta k T)) - 1) with a
    series resistance, its band gap follows eq. (1) of the sheet,
    Eg(T) = E0 (1 - alpha T^2/(theta + T)), and its junction heats with
    the power U I through a fast junction-to-package and a slower
    package-to-surroundings path (air, water or liquid nitrogen).
    Only what a real instrument shows is displayed: the multimeter
    readings and the sensor program's intensity against pixel number.
    No wavelength, temperature or fit is ever computed for you.
    Every hidden true parameter is randomised for each session.

    Run:   python3 ispho2025_E1_led_sim_EN.py   [--seed=N]
"""
import math
import random
import sys
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# --------------------------------------------------------------------------
# i18n
# --------------------------------------------------------------------------
LANG = "EN"          # the KO edition differs only in this line


def T(ko, en):
    """Bilingual string selector."""
    return ko if LANG == "KO" else en


# --------------------------------------------------------------------------
# Constants as printed on the problem sheet
# --------------------------------------------------------------------------
HBAR = 1.05e-34
C_LIGHT = 3.0e8
K_B = 1.38e-23
Q_E = 1.602e-19
T_ROOM = 298.0
T_N2 = 77.0
THETA_D = 500.0
NPIX = 3650
TABLE_L = 66.0          # cm, length of the optical table
PSU_MAX = 15.0


def U(a, b):
    return random.uniform(a, b)


class Truth:
    """The hidden parameters of this session (SI units unless marked)."""

    def __init__(self):
        self.lam_room = U(586, 595) * 1e-9
        self.alpha = U(3.45e-4, 4.10e-4)
        eg_room = 2 * math.pi * HBAR * C_LIGHT / self.lam_room
        self.E0 = eg_room / (1 - self.alpha * T_ROOM ** 2 / (THETA_D + T_ROOM))
        self.eta_r = U(1.95, 2.15)
        self.eta_p = U(0.78, 0.86)
        iref = U(0.7e-5, 1.4e-5)
        self.ln_i0r = math.log(iref) - 1.60 * Q_E / (self.eta_r * K_B * T_ROOM)
        self.beta = U(0.18, 0.20)  # I0 grows ~6.7x per 10 K (official solution, F3)
        eta77 = self.eta_r * (T_ROOM / T_N2) ** self.eta_p
        ln77 = math.log(U(3.5e-7, 9e-7)) - 2.10 * Q_E / (eta77 * K_B * T_N2)
        dd = T_N2 - T_ROOM
        self.gamma = (ln77 - self.ln_i0r - self.beta * dd) / (dd * dd)
        self.rs_r = U(4.0, 5.0)
        self.rsh = U(4e8, 9e8)
        self.i_amb = U(2e-11, 5e-11)
        self.i_stray = U(1.5e-10, 3.5e-10)
        self.pol = random.choice([1, -1])
        self.rjp = U(170, 230)
        self.cj = U(0.004, 0.006)
        self.env = {"air": (1 / U(235, 280), U(0.16, 0.20)),
                    "water": (1 / U(110, 135), U(0.032, 0.040)),
                    "n2": (1 / U(80, 100), U(0.026, 0.034))}
        self.eff = U(0.08, 0.12)
        self.eff_t = U(220, 300)
        self.fwhm = U(24, 30)          # nm at T0
        self.fwhm_t = U(0.04, 0.06)    # nm/K
        self.lobes = [(0.0, 1.0), (U(-9, -5), U(0.22, 0.38)), (U(4, 8), U(0.15, 0.30))]
        self.R0 = U(45.5, 46.8)
        self.RV = U(0.988, 1.000) * 1e6
        self.RV200m = -U(0.0005, 0.0015) * 1e6
        self.rgb = {"R": (U(618, 624), U(15, 19)), "G": (U(514, 522), U(30, 36)),
                    "B": (U(461, 469), U(22, 27))}
        self.F1 = U(11.6, 12.4)
        self.F2 = U(11.6, 12.4)
        self.slope0 = -0.102 * U(0.97, 1.03)
        self.shift0 = U(702, 718)
        self.dark = U(3, 6)
        self.ron = U(0.8, 1.4)
        self.n2rate = U(1 / 110, 1 / 80)
        self.gain = [1 + U(-0.0012, 0.0012) for _ in range(2)]
        self.off = [U(-0.6, 0.6) for _ in range(2)]
        self.rv = [1 + U(-0.004, 0.004) for _ in range(2)]

    def Eg(self, Tk):
        return self.E0 * (1 - self.alpha * Tk * Tk / (THETA_D + Tk))

    def lam(self, Tk):
        return 2 * math.pi * HBAR * C_LIGHT / self.Eg(Tk)

    def eta(self, Tk):
        return self.eta_r * (T_ROOM / Tk) ** self.eta_p

    def ln_i0(self, Tk):
        d = Tk - T_ROOM
        return self.ln_i0r + self.beta * d + self.gamma * d * d

    def rs(self, Tk):
        return self.rs_r * (1 + 0.25 * math.exp(-(Tk - T_N2) / 60))


TR = None


# --------------------------------------------------------------------------
# A small nodal solver with a real pn junction
# --------------------------------------------------------------------------
def lin_solve(A, b):
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-18:
            return None
        M[c], M[p] = M[p], M[c]
        inv = 1 / M[c][c]
        for r in range(c + 1, n):
            f = M[r][c] * inv
            if f:
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = M[r][n] - sum(M[r][k] * x[k] for k in range(r + 1, n))
        x[r] = s / M[r][r]
    return x


def pn_limit(vn, vo, nvt):
    if vn - vo > 0.3:
        vn = vo + 0.3
    elif vo - vn > 0.3:
        vn = vo - 0.3
    return vn


class Net:
    def __init__(self, gnd):
        self.nodes = {gnd: 0}
        self.res, self.isrc, self.vsrc, self.di = [], [], [], []

    def node(self, n):
        if n not in self.nodes:
            self.nodes[n] = len(self.nodes)
        return self.nodes[n]

    def R(self, a, b, r):
        self.res.append((self.node(a), self.node(b), max(r, 1e-9)))

    def I(self, a, b, c):
        self.isrc.append((self.node(a), self.node(b), c))

    def V(self, a, b, e):
        self.vsrc.append([self.node(a), self.node(b), e])
        return len(self.vsrc) - 1

    def D(self, a, c, Is, nvt, rsh, iph, v0):
        d = {"a": self.node(a), "c": self.node(c), "Is": Is, "nvt": nvt, "rsh": rsh, "iph": iph, "v": v0}
        self.di.append(d)
        return d

    def solve(self):
        nn = len(self.nodes) - 1
        nv = len(self.vsrc)
        N = nn + nv
        x = None
        for _ in range(400):
            A = [[0.0] * N for _ in range(N)]
            b = [0.0] * N

            def sg(p, q, g):
                i, j = p - 1, q - 1
                if i >= 0:
                    A[i][i] += g
                if j >= 0:
                    A[j][j] += g
                if i >= 0 and j >= 0:
                    A[i][j] -= g
                    A[j][i] -= g

            def si(p, q, c):
                i, j = p - 1, q - 1
                if i >= 0:
                    b[i] -= c
                if j >= 0:
                    b[j] += c
            for i in range(nn):
                A[i][i] += 1e-13
            for p, q, r in self.res:
                sg(p, q, 1 / r)
            for p, q, c in self.isrc:
                si(p, q, c)
            for k, (p, q, e) in enumerate(self.vsrc):
                row = nn + k
                if p > 0:
                    A[row][p - 1] += 1
                    A[p - 1][row] += 1
                if q > 0:
                    A[row][q - 1] -= 1
                    A[q - 1][row] -= 1
                b[row] += e
            for d in self.di:
                ex = math.exp(min(d["v"] / d["nvt"], 200))
                Id = d["Is"] * (ex - 1) + d["v"] / d["rsh"] - d["iph"]
                gd = max(d["Is"] * ex / d["nvt"] + 1 / d["rsh"], 1e-15)
                sg(d["a"], d["c"], gd)
                si(d["a"], d["c"], Id - gd * d["v"])
            x = lin_solve(A, b)
            if x is None:
                return False
            vs = [0.0] + x[:nn]
            if not self.di:
                break
            worst = 0
            for d in self.di:
                vn = pn_limit(vs[d["a"]] - vs[d["c"]], d["v"], d["nvt"])
                worst = max(worst, abs(vn - d["v"]))
                d["v"] = vn
            if worst < 1e-11:
                break
        self.vs = [0.0] + x[:nn]
        self.x = x
        self.nn = nn
        return True

    def v(self, n):
        return self.vs[self.nodes[n]]

    def isrc_of(self, k):
        return self.x[self.nn + k]


# --------------------------------------------------------------------------
# Multimeters (3 1/2 digits), one rotary dial each
# --------------------------------------------------------------------------
RANGES = {"VDC": {"200mV": (199.9, 1e3, "mV", 1), "2V": (1.999, 1, "V", 3), "20V": (19.99, 1, "V", 2),
                  "200V": (199.9, 1, "V", 1), "600V": (600, 1, "V", 0)},
          "ADC": {"2000uA": (1999, 1e6, "uA", 0), "20mA": (19.99, 1e3, "mA", 2), "200mA": (199.9, 1e3, "mA", 1),
                  "10A": (9.99, 1, "A", 2)},
          "OHM": {"200": (199.9, 1, "Ohm", 1), "2k": (1.999, 1e-3, "kOhm", 3), "20k": (19.99, 1e-3, "kOhm", 2),
                  "200k": (199.9, 1e-3, "kOhm", 1), "2M": (1.999, 1e-6, "MOhm", 3)}}
SHUNT = {"2000uA": 100, "20mA": 10, "200mA": 1, "10A": 0.01}
ITEST = {"200": 1e-3, "2k": 1e-4, "20k": 1e-5, "200k": 1e-6, "2M": 1e-7}
DIAL = ["OFF"] + ["VDC " + r for r in ["600V", "200V", "20V", "2V", "200mV"]] + \
       ["ADC " + r for r in ["2000uA", "20mA", "200mA", "10A"]] + \
       ["OHM " + r for r in ["200", "2k", "20k", "200k", "2M"]]


class DMM:
    def __init__(self, i):
        self.i = i
        self.mode, self.range = "OFF", "20V"
        self.fuse = True
        self.value = None

    def set_dial(self, s):
        if s == "OFF":
            self.mode = "OFF"
        else:
            self.mode, self.range = s.split()

    def r_in(self):
        r = TR.RV + (TR.RV200m if self.range == "200mV" else 0)
        return r * TR.rv[self.i]

    def display(self):
        if self.mode == "OFF":
            return "", ""
        fs, fac, unit, dec = RANGES[self.mode][self.range]
        if self.mode == "ADC" and not self.fuse:
            return "0", unit
        if self.value is None:
            return "1", unit
        lsb = 10 ** (-dec)
        s = self.value * fac * TR.gain[self.i] + TR.off[self.i] * lsb + random.gauss(0, 0.3 * lsb)
        if abs(s) > fs + 0.5 * lsb:
            return "1", unit
        q = round(s / lsb) * lsb
        if abs(q) < 0.5 * lsb:
            q = 0.0
        return ("%." + str(dec) + "f") % q, unit


# --------------------------------------------------------------------------
# The bench
# --------------------------------------------------------------------------
TERMS = ["PSU+", "PSU-", "V1.HI", "V1.COM", "V2.HI", "V2.COM", "R0.A", "R0.B", "AD.red", "AD.black"]


class Cuvette:
    def __init__(self):
        self.med, self.lvl, self.frost, self.dead = "air", 0.0, 0.0, False
        self.Tj = self.Tp = T_ROOM


class Bench:
    def __init__(self):
        self.x = {"stand": 6.0, "L1": 18.0, "L2": 34.0, "screen": 47.0}
        self.shield = True
        self.source = "rgb"                    # rgb | main1 | main2 | none
        self.rgb_sel = "R"
        self.cuv = {"main1": Cuvette(), "main2": Cuvette()}
        self.ad_sw = False
        self.wires = []
        self.psu_on, self.psu_v = False, 0.0
        self.psu_cc = False
        self.meters = [DMM(0), DMM(1)]
        self.I, self.U = 0.0, 0.0
        self.lastv = 0.0
        self.over = 0.0
        self.stand_jit, self.lobe_jit = 0.0, 0.0
        self.t = 0.0
        self.tube_in = None
        self.tube_fill = 0.0
        self.sens = 4

    def main(self):
        return self.source if self.source.startswith("main") else None

    def linked(self):
        m = self.main()
        return bool(m) and self.ad_sw and not self.cuv[m].dead

    def nudge(self, s):
        self.stand_jit += random.gauss(0, s)
        self.lobe_jit = random.gauss(0, 0.4)

    # ---- the circuit ----
    def groups(self):
        par = {t: t for t in TERMS}

        def f(a):
            while par[a] != a:
                par[a] = par[par[a]]
                a = par[a]
            return a
        for a, b in self.wires:
            ra, rb = f(a), f(b)
            if ra != rb:
                par[ra] = rb
        return f

    def solve(self):
        f = self.groups()

        def g(t):
            return "N" + f(t)
        nl = Net(g("PSU-"))
        for t in TERMS:
            nl.node(g(t))
        led = None
        m = self.main()
        if m and self.linked():
            c = self.cuv[m]
            Tk = c.Tj
            nvt = TR.eta(Tk) * K_B * Tk / Q_E
            an, ca = ("AD.red", "AD.black") if TR.pol > 0 else ("AD.black", "AD.red")
            iph = TR.i_amb + (0 if self.shield else TR.i_stray)
            nl.R(g(an), "LEDJ", TR.rs(Tk))
            nl.D("LEDJ", g(ca), math.exp(TR.ln_i0(Tk)), nvt, TR.rsh, iph, self.lastv)
            led = (g(an), "LEDJ", g(ca), Tk)
        nl.R(g("R0.A"), g("R0.B"), TR.R0)
        vk = None
        if self.psu_on:
            vk = nl.V("PSUINT", g("PSU-"), self.psu_v)
            nl.R("PSUINT", g("PSU+"), 0.3)
        for k in range(2):
            mm = self.meters[k]
            hi, lo = g("V%d.HI" % (k + 1)), g("V%d.COM" % (k + 1))
            if mm.mode == "VDC":
                nl.R(hi, lo, mm.r_in())
            elif mm.mode == "ADC":
                nl.R(hi, lo, SHUNT[mm.range] if mm.fuse else 1e9)
            elif mm.mode == "OHM":
                nl.I(lo, hi, ITEST[mm.range])
                nl.R(hi, lo, 1e11)
        E = self.psu_v
        self.psu_cc = False
        for _ in range(6):
            if vk is not None:
                nl.vsrc[vk][2] = E
            if not nl.solve():
                return None
            if vk is None:
                break
            cur = -nl.isrc_of(vk)
            if cur <= 1.0 or E <= 1e-4:
                break
            self.psu_cc = True
            E = max(0, E - 0.6 * (cur - 1.0) * 2.3)
        return nl, g, led

    def env(self, c):
        if c.med == "water":
            return (T_ROOM,) + TR.env["water"]
        if c.med == "n2":
            if c.lvl > 0.32:
                return (T_N2,) + TR.env["n2"]
            f = max(0, c.lvl) / 0.32
            return (T_N2 + (T_ROOM - T_N2) * (0.55 - 0.4 * f), TR.env["air"][0] * 1.4, TR.env["air"][1])
        return (T_ROOM,) + TR.env["air"]

    def step(self, dt):
        res = self.solve()
        if res is None:
            return []
        nl, g, led = res
        msgs = []
        I = Ud = 0.0
        if led:
            va, vj, vc = nl.v(led[0]), nl.v(led[1]), nl.v(led[2])
            I = (va - vj) / TR.rs(led[3])
            Ud = va - vc
            self.lastv = vj - vc
        else:
            self.lastv = 0.0
        self.I, self.U = I, Ud
        for k in range(2):
            mm = self.meters[k]
            dv = nl.v(g("V%d.HI" % (k + 1))) - nl.v(g("V%d.COM" % (k + 1)))
            if mm.mode == "VDC":
                mm.value = dv
            elif mm.mode == "ADC":
                cur = dv / SHUNT[mm.range] if mm.fuse else 0
                mm.value = cur
                if mm.fuse and mm.range != "10A" and abs(cur) > 0.25:
                    mm.fuse = False
                    msgs.append(T("V%d 멀티미터의 퓨즈가 끊어졌습니다." % (k + 1), "Fuse blown in multimeter V%d." % (k + 1)))
            elif mm.mode == "OHM":
                it = ITEST[mm.range]
                mm.value = None if (abs(dv) > 2.5 or dv < -1e-6) else dv / it
            else:
                mm.value = None
        if dt <= 0:
            return msgs
        for key, c in self.cuv.items():
            Te, gg, C = self.env(c)
            P = max(0, Ud * I * (1 - 0.25 * TR.eff)) if (key == self.main() and led) else 0.0
            n = max(1, int(math.ceil(dt / 0.25)))
            h = dt / n
            for _ in range(n):
                q = (c.Tj - c.Tp) / TR.rjp
                c.Tj += (P - q) / TR.cj * h
                c.Tp += (q - gg * (c.Tp - Te)) / C * h
            if c.med == "n2":
                c.lvl = max(0, c.lvl - TR.n2rate * dt * (1 + P * 3))
                c.frost = min(1, c.frost + dt / 45)
                if c.lvl <= 0:
                    c.med = "air"
            elif c.frost > 0:
                c.frost = max(0, c.frost - dt / 240)
            if key == self.main() and led:
                if abs(I) > 0.16 and not c.dead:
                    c.dead = True
                if abs(I) > 0.1005:
                    # a few per cent over wears it slowly (about a minute), 115 mA kills it in seconds
                    self.over += dt * (1 if abs(I) > 0.115 else 0.05)
                    if self.over > 3 and not c.dead:
                        c.dead = True
                else:
                    self.over = max(0, self.over - dt * 0.5)
                if c.dead:
                    msgs.append(T("LED가 과전류로 망가졌습니다 — 예비 큐벳을 쓰세요.",
                                  "The LED was destroyed by over-current — use the reserve cuvette."))
        if self.tube_in is not None:
            self.tube_in += dt
        self.t += dt
        return msgs

    # ---- the spectrometer ----
    def optics(self):
        x = self.x
        if not (x["stand"] < x["L1"] < x["L2"] < x["screen"]):
            return None
        e1 = (x["L1"] - x["stand"]) - TR.F1
        e2 = (x["screen"] - x["L2"]) - TR.F2
        amp = 1 / (1 + (e1 / 1.4) ** 2) / (1 + (e2 / 4) ** 2)
        return amp, 0.35 + 2.6 * abs(e2) + 1.4 * abs(e1)

    def scale(self):
        L2S = max(4, self.x["screen"] - self.x["L2"])
        return TR.slope0 * TR.F2 / L2S, TR.shift0 + self.stand_jit

    def sources(self):
        out = []
        if self.source == "rgb" and self.rgb_sel != "off":
            l0, w = TR.rgb[self.rgb_sel]
            out.append((l0, w, {"R": 1.15, "G": 0.62, "B": 0.9}[self.rgb_sel], self.rgb_sel == "R"))
        m = self.main()
        if m and self.linked() and self.I > 0:
            c = self.cuv[m]
            l0 = TR.lam(c.Tj) * 1e9
            w = max(8, TR.fwhm + TR.fwhm_t * (c.Tj - T_ROOM))
            out.append((l0, w, self.I * 1000 * TR.eff * math.exp(-(c.Tj - T_ROOM) / TR.eff_t) * 0.11, False))
        return out

    def frame(self):
        o = self.optics()
        slope, shift = self.scale()
        gain = 2 ** (self.sens - 4)
        m = self.main()
        frost = self.cuv[m].frost if m else 0.0
        stray = 0 if self.shield else 1
        dark = TR.dark * (0.6 + 0.4 * gain) * (1 + 3 * stray)
        src = self.sources() if o else []
        out = [0.0] * NPIX
        for n in range(NPIX):
            lam = shift + slope * n
            s = 0.0
            for l0, w, a, red in src:
                sig = math.sqrt(w * w / (8 * math.log(2)) + o[1] ** 2 + (frost * 4) ** 2)
                ss = 0.0
                lobes = [(0, 1), (22, 0.42)] if red else TR.lobes
                for dl, aa in lobes:
                    ll = lam - (l0 + dl + (0 if red else self.lobe_jit))
                    if abs(ll) < 6 * sig:
                        ss += aa * math.exp(-ll * ll / (2 * sig * sig))
                s += ss * a
            amp = o[0] if o else 0.0
            v = dark + s * amp * math.exp(-2.2 * frost) * 420 * gain + (18 * gain if stray else 0) \
                + random.gauss(0, TR.ron * (1 + 0.3 * gain))
            out[n] = max(0.0, min(4095.0, v))
        return out


# --------------------------------------------------------------------------
# The window
# --------------------------------------------------------------------------
class App:
    def __init__(self, root, seed=None):
        global TR
        if seed is not None:
            random.seed(seed)
        TR = Truth()
        self.root = root
        self.B = Bench()
        self.live = False
        self.hold = None
        self.cur = None
        self.ts = None
        self.ts_done = None
        self.ts_next = 0.0
        self.speed = 1
        self.sw_run, self.sw_t = False, 0.0
        self.view = [0, NPIX]
        self.mouse = None
        self.last = time.time()
        self.acc = 0.0
        root.title(T("ISPhO 2025 실험 — LED의 색  ·  HaslaLab", "ISPhO 2025 Experiment — LED Color  ·  HaslaLab"))
        root.geometry("1360x860")
        self.build()
        self.tick()

    # ---------------- layout ----------------
    def build(self):
        left = ttk.Frame(self.root, padding=6)
        left.pack(side="left", fill="y")
        right = ttk.Frame(self.root, padding=6)
        right.pack(side="left", fill="both", expand=True)
        nb = ttk.Notebook(left, width=430)
        nb.pack(fill="both", expand=True)
        f_opt, f_cir, f_cuv = ttk.Frame(nb, padding=6), ttk.Frame(nb, padding=6), ttk.Frame(nb, padding=6)
        nb.add(f_opt, text=T("광학", "Optics"))
        nb.add(f_cir, text=T("회로", "Circuit"))
        nb.add(f_cuv, text=T("큐벳", "Cuvette"))

        # optics
        ttk.Label(f_opt, text=T("광학대 위 위치 (cm, 왼쪽 끝부터) — 눈금은 광학대에 없습니다:\n"
                                "스펙트럼과 스크린의 모습을 보며 맞추세요.",
                                "Positions on the optical table (cm from its left end) — the table\n"
                                "carries no scale: adjust while watching the spectrum.")).pack(anchor="w")
        self.sx = {}
        for k, lab in [("stand", T("LED 받침대", "LED stand")), ("L1", "L1"), ("L2", "L2 + G"), ("screen", T("스크린 + CCD", "screen + CCD"))]:
            fr = ttk.Frame(f_opt)
            fr.pack(fill="x", pady=2)
            ttk.Label(fr, text=lab, width=14).pack(side="left")
            v = tk.DoubleVar(value=self.B.x[k])
            sc = tk.Scale(fr, from_=1, to=TABLE_L - 1, resolution=0.1, orient="horizontal", variable=v, showvalue=False,
                          length=190, command=lambda _v, k=k: self.on_pos(k))
            sc.pack(side="left")
            for d in (-0.1, 0.1):
                ttk.Button(fr, text=("%+.1f" % d), width=4, command=lambda k=k, d=d: self.nudge_pos(k, d)).pack(side="left")
            self.sx[k] = v
        self.shield_v = tk.BooleanVar(value=True)
        ttk.Checkbutton(f_opt, text=T("차광 상자를 씌움", "shielding box in place"), variable=self.shield_v,
                        command=lambda: setattr(self.B, "shield", self.shield_v.get())).pack(anchor="w", pady=4)
        ttk.Label(f_opt, text=T("받침대에 꽂은 것", "In the stand")).pack(anchor="w", pady=(8, 0))
        self.src_v = tk.StringVar(value="rgb")
        for val, lab in [("rgb", T("\"RGB\" LED 기판", "\"RGB\" LED board")), ("main1", T("\"MAIN\" LED 큐벳", "\"MAIN\" LED cuvette")),
                         ("main2", T("예비 \"MAIN\" 큐벳", "reserve \"MAIN\" cuvette")), ("none", T("없음", "nothing"))]:
            ttk.Radiobutton(f_opt, text=lab, value=val, variable=self.src_v, command=self.on_src).pack(anchor="w")
        ttk.Label(f_opt, text=T("제어판 토글 (RGB)", "Control-board toggle (RGB)")).pack(anchor="w", pady=(8, 0))
        self.rgb_v = tk.StringVar(value="R")
        fr = ttk.Frame(f_opt)
        fr.pack(anchor="w")
        for val in ("R", "G", "B", "off"):
            ttk.Radiobutton(fr, text=val, value=val, variable=self.rgb_v,
                            command=lambda: setattr(self.B, "rgb_sel", self.rgb_v.get())).pack(side="left")
        self.screen_cv = tk.Canvas(f_opt, width=200, height=200, bg="#e6e8ea", highlightthickness=0)
        self.screen_cv.pack(pady=8)

        # circuit
        ttk.Label(f_cir, text=T("직류 전원 (0–15 V)", "DC source (0–15 V)")).pack(anchor="w")
        fr = ttk.Frame(f_cir)
        fr.pack(fill="x")
        self.psu_btn = ttk.Button(fr, text=T("전원 켜기", "Source on"), command=self.toggle_psu)
        self.psu_btn.pack(side="left")
        self.knob_l = ttk.Label(fr, text="")
        self.knob_l.pack(side="left", padx=8)
        fr = ttk.Frame(f_cir)
        fr.pack(fill="x", pady=2)
        for d in (-1, -0.1, -0.01, 0.01, 0.1, 1):
            ttk.Button(fr, text="%+g" % d, width=5, command=lambda d=d: self.knob(d)).pack(side="left")
        ttk.Button(f_cir, text=T("노브를 맨 왼쪽(0 V)으로", "Knob fully left (0 V)"), command=lambda: self.knob(None)).pack(anchor="w")
        self.ad_btn = ttk.Button(f_cir, text="", command=self.toggle_ad)
        self.ad_btn.pack(anchor="w", pady=4)
        ttk.Label(f_cir, text=T("배선 (바나나 선)", "Wiring (banana leads)")).pack(anchor="w", pady=(8, 0))
        fr = ttk.Frame(f_cir)
        fr.pack(fill="x")
        self.wa, self.wb = tk.StringVar(value=TERMS[0]), tk.StringVar(value=TERMS[6])
        ttk.OptionMenu(fr, self.wa, TERMS[0], *TERMS).pack(side="left")
        ttk.Label(fr, text="↔").pack(side="left")
        ttk.OptionMenu(fr, self.wb, TERMS[6], *TERMS).pack(side="left")
        ttk.Button(fr, text=T("연결", "Join"), command=self.add_wire).pack(side="left", padx=4)
        self.wire_lb = tk.Listbox(f_cir, height=8)
        self.wire_lb.pack(fill="x", pady=2)
        ttk.Button(f_cir, text=T("고른 선 빼기", "Remove selected lead"), command=self.del_wire).pack(anchor="w")
        ttk.Label(f_cir, text=T("어댑터의 빨강·검정 소켓은 2가닥 리본으로 MAIN LED에 이어집니다\n(어느 쪽이 양극인지는 직접 확인하세요).",
                                "The adapter's red and black sockets reach the MAIN LED through the\n2-lead ribbon (find out yourself which is the anode)."),
                  foreground="#555").pack(anchor="w", pady=4)
        self.dial_v = []
        self.lcd = []
        for k in range(2):
            fr = ttk.LabelFrame(f_cir, text=T("멀티미터 V%d" % (k + 1), "Multimeter V%d" % (k + 1)), padding=4)
            fr.pack(fill="x", pady=3)
            v = tk.StringVar(value="OFF")
            ttk.OptionMenu(fr, v, "OFF", *DIAL, command=lambda s, k=k: self.B.meters[k].set_dial(s)).pack(side="left")
            lab = tk.Label(fr, text="", font=("Consolas", 22, "bold"), bg="#b9c4a3", width=8, anchor="e")
            lab.pack(side="left", padx=8)
            u = ttk.Label(fr, text="")
            u.pack(side="left")
            self.dial_v.append(v)
            self.lcd.append((lab, u))
        ttk.Button(f_cir, text=T("퓨즈 갈기", "Replace fuse"), command=self.fuse).pack(anchor="w")

        # cuvette
        self.cuv_l = ttk.Label(f_cuv, text="", justify="left")
        self.cuv_l.pack(anchor="w")
        for lab, cmd in [(T("스포이트로 증류수 채우기", "Fill with distilled water (pipette)"), self.fill_water),
                         (T("큐벳을 빼서 폐액 비커에 비우고 다시 꽂기", "Take the cuvette out, empty it, put it back"), self.empty_cuv),
                         (T("관을 보온병의 액체질소에 내리기", "Lower the tube into the liquid nitrogen"), self.tube_down),
                         (T("관을 들어 올려 큐벳에 붓기", "Lift the tube and pour into the cuvette"), self.tube_up),
                         (T("큐벳 앞면 서리 닦기", "Wipe the frost off the front"), self.wipe)]:
            ttk.Button(f_cuv, text=lab, command=cmd).pack(fill="x", pady=2)
        self.cuv_cv = tk.Canvas(f_cuv, width=160, height=300, bg="#e9e7e0", highlightthickness=0)
        self.cuv_cv.pack(pady=8)

        # status
        self.status = tk.Label(left, text="", fg="#b3261e", wraplength=420, justify="left")
        self.status.pack(fill="x", pady=4)

        # right: the sensor program
        bar = ttk.Frame(right)
        bar.pack(fill="x")
        ttk.Button(bar, text="Launch", command=self.launch).pack(side="left")
        ttk.Button(bar, text="Pause", command=self.pause).pack(side="left")
        ttk.Button(bar, text="Single spectrum", command=self.single).pack(side="left")
        ttk.Button(bar, text="Save spectrum", command=self.save_single).pack(side="left")
        self.ts_btn = ttk.Button(bar, text="Time Series", command=self.time_series)
        self.ts_btn.pack(side="left")
        ttk.Button(bar, text="Save time series", command=self.save_ts).pack(side="left")
        ttk.Label(bar, text=T("  감도", "  sensitivity")).pack(side="left")
        self.sens_v = tk.IntVar(value=4)
        tk.Spinbox(bar, from_=1, to=8, width=3, textvariable=self.sens_v,
                   command=lambda: setattr(self.B, "sens", self.sens_v.get())).pack(side="left")
        self.cv = tk.Canvas(right, bg="white", highlightthickness=0)
        self.cv.pack(fill="both", expand=True, pady=4)
        self.cv.bind("<Motion>", lambda e: setattr(self, "mouse", (e.x, e.y)))
        self.cv.bind("<MouseWheel>", self.wheel)
        self.cv.bind("<Button-4>", lambda e: self.wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self.wheel(e, -1))
        self.cv.bind("<Double-Button-1>", lambda e: setattr(self, "view", [0, NPIX]))
        bot = ttk.Frame(right)
        bot.pack(fill="x")
        ttk.Label(bot, text=T("시간 배속", "Time speed")).pack(side="left")
        for s in (1, 5, 20, 60):
            ttk.Button(bot, text="×%d" % s, width=4, command=lambda s=s: setattr(self, "speed", s)).pack(side="left")
        self.sw_l = tk.Label(bot, text="0:00.0", font=("Consolas", 16, "bold"))
        self.sw_l.pack(side="left", padx=12)
        ttk.Button(bot, text=T("스톱워치 시작/정지", "Stopwatch start/stop"), command=lambda: setattr(self, "sw_run", not self.sw_run)).pack(side="left")
        ttk.Button(bot, text=T("리셋", "Reset"), command=self.sw_reset).pack(side="left")

    # ---------------- controls ----------------
    def say(self, s):
        self.status.config(text=s)

    def on_pos(self, k):
        old = self.B.x[k]
        self.B.x[k] = round(self.sx[k].get(), 1)
        if k == "stand" and abs(old - self.B.x[k]) > 0.05:
            self.B.nudge(0.3)

    def nudge_pos(self, k, d):
        self.sx[k].set(min(TABLE_L - 1, max(1, round(self.sx[k].get() + d, 1))))
        self.on_pos(k)

    def on_src(self):
        new = self.src_v.get()
        if new != self.B.source:
            self.B.source = new
            self.B.nudge(0.35)
            self.say(T("받침대를 건드려 아주 조금 움직였을 수 있습니다 — 보정이 달라질 수 있습니다.",
                       "The stand may have moved very slightly — the calibration may have changed."))

    def toggle_psu(self):
        self.B.psu_on = not self.B.psu_on

    def knob(self, d):
        self.B.psu_v = 0.0 if d is None else min(PSU_MAX, max(0.0, round(self.B.psu_v + d, 2)))

    def toggle_ad(self):
        self.B.ad_sw = not self.B.ad_sw

    def add_wire(self):
        a, b = self.wa.get(), self.wb.get()
        if a == b:
            return
        self.B.wires.append((a, b))
        self.wire_lb.insert("end", a + "  ↔  " + b)

    def del_wire(self):
        sel = self.wire_lb.curselection()
        if sel:
            i = sel[0]
            self.wire_lb.delete(i)
            del self.B.wires[i]

    def fuse(self):
        for m in self.B.meters:
            m.fuse = True

    def cur_cuv(self):
        m = self.B.main()
        if not m:
            self.say(T("받침대에 큐벳을 꽂으세요.", "Put a cuvette into the stand."))
        return self.B.cuv[m] if m else None

    def fill_water(self):
        c = self.cur_cuv()
        if not c:
            return
        if c.med == "n2":
            self.say(T("액체질소가 든 큐벳에 물을 넣으면 얼어붙습니다.", "Water poured into liquid nitrogen would freeze solid."))
            return
        c.med, c.lvl = "water", 1.0

    def empty_cuv(self):
        c = self.cur_cuv()
        if not c:
            return
        c.med, c.lvl = "air", 0.0
        self.B.nudge(0.45)
        self.say(T("큐벳을 비웠습니다. LED 위치가 조금 바뀌었을 수 있습니다.", "Cuvette emptied. The LED may have shifted slightly."))

    def tube_down(self):
        self.B.tube_in = 0.0
        self.say(T("관을 액체질소에 내렸습니다. 충분히 식을 때까지 기다리세요.", "Tube lowered into the liquid nitrogen. Let it cool down."))

    def tube_up(self):
        if self.B.tube_in is None:
            self.say(T("관이 보온병 안에 없습니다.", "The tube is not in the thermos."))
            return
        fill = 1.0 if self.B.tube_in > 12 else 0.3
        self.B.tube_in = None
        c = self.cur_cuv()
        if not c:
            return
        if c.med == "water":
            self.say(T("물이 든 큐벳에는 액체질소를 붓지 마세요 — 먼저 물을 비우세요.", "Do not pour liquid nitrogen onto water — empty the cuvette first."))
            return
        c.med = "n2"
        c.lvl = min(1.0, c.lvl + 0.95 * fill)
        self.say(T("액체질소를 부었습니다." if fill > 0.8 else "관이 덜 식어 액체질소가 격하게 끓어 조금밖에 붓지 못했습니다.",
                   "Liquid nitrogen poured." if fill > 0.8 else "The tube was still warm: little liquid nitrogen was left to pour."))

    def wipe(self):
        c = self.cur_cuv()
        if c:
            c.frost = 0.0

    # ---------------- the program ----------------
    def launch(self):
        self.live = True

    def pause(self):
        self.live = False
        if self.ts is not None:
            self.ts_done, self.ts = self.ts, None

    def single(self):
        self.hold = self.B.frame()

    def save_single(self):
        data = self.hold or self.cur
        if not data:
            self.say(T("먼저 Single spectrum으로 한 장을 찍으세요.", "Take a Single spectrum first."))
            return
        fn = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="spectrum.csv")
        if fn:
            with open(fn, "w", encoding="utf-8") as f:
                f.write("N,I\n")
                for n, v in enumerate(data):
                    f.write("%d,%d\n" % (n, round(v)))

    def time_series(self):
        if self.ts is not None:
            self.ts_done, self.ts = self.ts, None
            return
        if not self.live:
            self.say(T("Time Series는 Launch를 누른 다음에만 켤 수 있습니다.", "Time Series can only be started after Launch."))
            return
        self.ts = []
        self.ts_t0 = self.B.t
        self.ts_next = self.B.t

    def save_ts(self):
        ts = self.ts if self.ts is not None else self.ts_done
        if not ts:
            self.say(T("저장할 Time Series 기록이 없습니다.", "No time series recorded yet."))
            return
        fn = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="time_series.csv")
        if fn:
            with open(fn, "w", encoding="utf-8") as f:
                f.write("t_s," + ",".join("N%d" % n for n in range(NPIX)) + "\n")
                for t, fr in ts:
                    f.write("%.2f," % t + ",".join(str(int(round(v))) for v in fr) + "\n")

    def wheel(self, e, sign=None):
        s = sign if sign is not None else (1 if e.delta > 0 else -1)
        W = self.cv.winfo_width()
        x0, x1 = 60, W - 20
        f = min(1, max(0, (e.x - x0) / max(1, x1 - x0)))
        n0, n1 = self.view
        c = n0 + f * (n1 - n0)
        span = max(20, min(NPIX, (n1 - n0) * (0.8 if s > 0 else 1.25)))
        n0 = max(0, c - f * span)
        n1 = n0 + span
        if n1 > NPIX:
            n1 = NPIX
            n0 = n1 - span
        self.view = [n0, n1]

    def sw_reset(self):
        self.sw_run, self.sw_t = False, 0.0

    # ---------------- drawing ----------------
    def draw_plot(self):
        cv = self.cv
        cv.delete("all")
        W, H = cv.winfo_width(), cv.winfo_height()
        x0, y0, x1, y1 = 60, 20, W - 20, H - 40
        data = self.cur if self.live else self.hold
        n0, n1 = self.view
        mx = 64
        if data:
            mx = max(mx, max(data[int(n0):int(n1)]))
        ym = 1
        p = 10 ** math.floor(math.log10(mx * 1.12))
        for m in (1, 2, 2.5, 5, 10):
            if m * p >= mx * 1.12:
                ym = m * p
                break
        cv.create_rectangle(x0, y0, x1, y1, outline="#9aa3ab")
        st = next((s for s in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000) if (n1 - n0) / s <= 10), 1000)
        n = math.ceil(n0 / st) * st
        while n <= n1:
            x = x0 + (n - n0) / (n1 - n0) * (x1 - x0)
            cv.create_line(x, y0, x, y1, fill="#e3e6ea")
            cv.create_text(x, y1 + 12, text=str(int(n)), font=("Arial", 9))
            n += st
        for i in range(6):
            v = ym * i / 5
            y = y1 - v / ym * (y1 - y0)
            cv.create_line(x0, y, x1, y, fill="#e3e6ea")
            cv.create_text(x0 - 6, y, text=str(int(v)), anchor="e", font=("Arial", 9))
        cv.create_text((x0 + x1) / 2, y1 + 28, text="N", font=("Arial", 10, "bold"))
        cv.create_text(20, (y0 + y1) / 2, text="I, a.u.", angle=90, font=("Arial", 10, "bold"))
        if data:
            pts = []
            a, b = int(n0), min(NPIX - 1, int(math.ceil(n1)))
            stp = max(1, (b - a) // (x1 - x0))
            for n in range(a, b + 1, stp):
                v = max(data[n:n + stp]) if stp > 1 else data[n]
                pts += [x0 + (n - n0) / (n1 - n0) * (x1 - x0), y1 - min(v, ym) / ym * (y1 - y0)]
            if len(pts) >= 4:
                cv.create_line(*pts, fill="#1f5fbf")
            if self.mouse and x0 <= self.mouse[0] <= x1:
                n = int(round(n0 + (self.mouse[0] - x0) / (x1 - x0) * (n1 - n0)))
                if 0 <= n < NPIX:
                    xx = x0 + (n - n0) / (n1 - n0) * (x1 - x0)
                    cv.create_line(xx, y0, xx, y1, fill="#e09090")
                    cv.create_text(x0 + 8, y0 + 12, anchor="w", fill="#b3261e", font=("Arial", 10, "bold"),
                                   text="N = %d   I = %d" % (n, round(data[n])))
        mode = (T("기록 중 %d 장", "recording %d frames") % len(self.ts)) if self.ts is not None else \
            (T("실시간", "live") if self.live else (T("한 장", "single") if self.hold else ""))
        cv.create_text(x1 - 6, y0 + 12, anchor="e", text=mode, font=("Arial", 10, "bold"))

    def ccd_plate(self, c, cx, y0, y1):
        """the CCD as on the sheet: a black square plate, four screws, the long chip down its middle"""
        s = (y1 - y0) / 2
        c.create_rectangle(cx - s, y0, cx + s, y1, fill="#141416", outline="#000")
        c.create_polygon(cx - 0.55 * s, y1, cx - 0.55 * s, y1 - 0.6 * s, cx, y1 - 0.95 * s, cx + 0.55 * s, y1 - 0.6 * s, cx + 0.55 * s, y1, fill="#1d1e21", outline="")
        c.create_rectangle(cx - 0.2 * s, y0 + 0.08 * s, cx + 0.2 * s, y1 - 0.08 * s, fill="#2b2c30", outline="#b89a5a")
        c.create_rectangle(cx - 0.1 * s, y0 + 0.18 * s, cx + 0.1 * s, y1 - 0.18 * s, fill="#7a7f88", outline="")
        for dx in (-0.78, 0.78):
            for dy in (0.22, 1.78):
                x, y = cx + dx * s, y0 + dy * s
                c.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#c3c8cd", outline="#7b8087")
        for i, col in enumerate(("#e8463c", "#f39a2e", "#f1d93a", "#43b649", "#2f8fd6", "#a347b8")):
            x = cx - 0.3 * s + i * 0.12 * s
            c.create_line(x, y1, x, y1 + 0.35 * s, fill=col, width=2)

    def draw_screen(self):
        c = self.screen_cv
        c.delete("all")
        o = self.B.optics()
        c.create_text(8, 10, anchor="w", text=T("스크린 면", "screen face"), font=("Arial", 9, "bold"))
        cx, zy, sz = 100, 180, 12
        self.ccd_plate(c, cx, zy - 6.3 * sz, zy - 1.6 * sz)
        lit = o and self.B.sources()
        if lit:
            bl = min(30, 2 + o[1] * 3)
            c.create_oval(cx - bl, zy - bl, cx + bl, zy + bl, fill="#fff6e0", outline="")
            for l0, w, a, red in self.B.sources():
                s = min(0.9, l0 * 1e-9 / 1.667e-6)
                y = zy - TR.F2 * math.tan(math.asin(s)) * sz
                col = "#ff4628" if l0 > 600 else "#ffb41e" if l0 > 565 else "#3ce650" if l0 > 500 else "#466eff"
                hh = max(2, bl * 0.5)
                c.create_rectangle(cx - bl * 0.6 - 5, y - hh, cx + bl * 0.6 + 5, y + hh, fill=col, outline="")

    def draw_cuv(self):
        c = self.cuv_cv
        c.delete("all")
        m = self.B.main()
        if not m:
            c.create_text(80, 150, text=T("큐벳 없음", "no cuvette"))
            self.cuv_l.config(text="")
            return
        cu = self.B.cuv[m]
        x0, y0, w, h = 50, 20, 60, 260
        base = y0 + h
        if cu.med != "air":
            lv = 0.84 if cu.med == "water" else max(0, cu.lvl) * 0.86
            c.create_rectangle(x0 + 3, base - lv * h, x0 + w - 3, base - 2,
                               fill="#9cc8e8" if cu.med == "water" else "#e0eeff", outline="")
        ly = base - h * 1.2 / 4.6
        c.create_oval(80 - 9, ly - 9, 80 + 9, ly + 9, fill="#3a2a2a" if cu.dead else "#f6d36a")
        if cu.frost > 0.02:
            g = int(160 + 90 * cu.frost)
            c.create_rectangle(x0, y0 + h * 0.15, x0 + w, base, stipple="gray50", fill="#%02x%02x%02x" % (g, g, g), outline="")
        c.create_rectangle(x0, y0, x0 + w, base, outline="#7a95a8", width=2)
        med = {"air": T("공기", "air"), "water": T("증류수", "distilled water"), "n2": T("액체질소", "liquid nitrogen")}[cu.med]
        self.cuv_l.config(text=med + ("" if not cu.dead else T("  ·  LED 고장", "  ·  LED dead")))

    # ---------------- the loop ----------------
    def tick(self):
        now = time.time()
        dt = min(0.1, now - self.last)
        self.last = now
        rem = dt * self.speed
        msgs = []
        while rem > 1e-9:
            h = min(0.25, rem)
            msgs += self.B.step(h)
            rem -= h
            if self.sw_run:
                self.sw_t += h
        if msgs:
            self.say(msgs[-1])
        self.acc += dt
        if self.acc > 0.3:
            self.acc = 0.0
            if self.live:
                self.cur = self.B.frame()
                if self.ts is not None and self.B.t >= self.ts_next:
                    self.ts.append((self.B.t - self.ts_t0, self.cur))
                    self.ts_next = self.B.t + 0.5
            for k in range(2):
                s, u = self.B.meters[k].display()
                self.lcd[k][0].config(text=s)
                self.lcd[k][1].config(text=u)
            self.knob_l.config(text=T("노브 %.2f V", "knob %.2f V") % self.B.psu_v + ("" if self.B.psu_on else T(" (꺼짐)", " (off)")))
            self.psu_btn.config(text=T("전원 끄기", "Source off") if self.B.psu_on else T("전원 켜기", "Source on"))
            self.ad_btn.config(text=T("어댑터 스위치: ", "Adapter switch: ") + ("ON" if self.B.ad_sw else "OFF"))
            self.ts_btn.config(text="Time Series ●" if self.ts is not None else "Time Series")
            st = self.sw_t
            self.sw_l.config(text="%d:%04.1f" % (int(st // 60), st % 60))
            if abs(self.B.I) > 0.1:
                self.say(T("LED 전류가 100 mA를 넘었습니다 — 곧 망가집니다!", "The LED current is over 100 mA — it will be damaged!"))
            self.draw_plot()
            self.draw_screen()
            self.draw_cuv()
        self.root.after(40, self.tick)


def main():
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
    root = tk.Tk()
    App(root, seed)
    root.mainloop()


if __name__ == "__main__":
    main()
