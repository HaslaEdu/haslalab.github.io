#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  43rd International Physics Olympiad  (IPhO 2012, Tartu, Estonia)
  Experimental Problem E2 :  NONLINEAR BLACK BOX
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Only real instrument output is ever shown: the IPhO-measure LCD (n, s, t,
    U, dU/dt, I, dI/dt, P, R) with the resolution of the real device, the
    front panels of the current source and of the black box, and the leads
    that are plugged in.  No I(V) curve, no C(V) curve and no fitted number
    is displayed anywhere.  The black box is solved as a real circuit
    (modified nodal analysis, Newton iteration, charge-conserving model of
    the 2 F double-layer capacitor), so any wiring gives the physically
    correct readings -- wrong wirings included.
    All hidden true parameters are randomised for every session.

    Run:   python3 ipho2012_E2_sim_KO.py   [--seed=N]
"""

import math
import random
import sys
import time
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


APP_TITLE = "IPhO 2012 E2"

# --------------------------------------------------------------------------
#  terminals
# --------------------------------------------------------------------------
TERMINALS = ["cs+", "cs-", "mm_in", "mm_out", "mm_gnd", "bb+", "bb-"]
TERM_LABEL = {"cs+": "+", "cs-": "\u2212", "mm_in": "IN", "mm_out": "OUT",
              "mm_gnd": "GND", "bb+": "+", "bb-": "\u2212"}


# ==========================================================================
#  1.  the devices behind the seals
# ==========================================================================
class NonlinearElement:
    """Tunnel-diode-like element:  a tunnelling branch plus a thermal branch.

        I(V) = Ip (V/Vp) exp(1 - V/Vp) + Is (exp(V/Vt) - 1)

    I(0) = 0, a current peak at Vp, a valley near 0.3 V and a steep rise
    afterwards; the differential resistance is negative between them.
    A capacitance Cp is in parallel with it inside the package.
    """

    def __init__(self, ip, vp, vt, vmax, i0, cp):
        self.Ip, self.Vp, self.Vt, self.Cp = ip, vp, vt, cp
        tun = ip * (vmax / vp) * math.exp(1.0 - vmax / vp)
        self.Is = max(1e-12, (i0 - tun) / (math.exp(vmax / vt) - 1.0))

    def cur(self, v):
        if v < 0.0:                                   # symmetric-ish for negative bias
            return -self.cur(-v)
        e = v / self.Vt
        th = self.Is * (math.exp(min(e, 60.0)) - 1.0)
        return self.Ip * (v / self.Vp) * math.exp(1.0 - v / self.Vp) + th

    def dcur(self, v):
        if v < 0.0:
            return self.dcur(-v)
        e = v / self.Vt
        th = self.Is / self.Vt * math.exp(min(e, 60.0))
        k = v / self.Vp
        return self.Ip / self.Vp * (1.0 - k) * math.exp(1.0 - k) + th

    def peak(self):
        return self.Vp, self.cur(self.Vp)

    def valley(self):
        lo, hi = self.Vp, self.Vp + 1.0
        for _ in range(80):
            m = 0.5 * (lo + hi)
            if self.dcur(m) < 0.0:
                lo = m
            else:
                hi = m
        return lo, self.cur(lo)


class DoubleLayerCap:
    """Electric double layer capacitor, slightly nonlinear:
        C(V) = C0 (1 + a V),  Q(V) = C0 (V + a V^2 / 2)."""

    def __init__(self, c0, a):
        self.C0, self.a = c0, a

    def cap(self, v):
        return self.C0 * (1.0 + self.a * v)

    def charge(self, v):
        return self.C0 * (v + 0.5 * self.a * v * v)

    def volt(self, q):
        v = q / self.C0
        for _ in range(40):
            f = self.charge(v) - q
            d = self.cap(v)
            v -= f / d
        return v


class LCBranch:
    """Nonlinear element in series with the 10 uH inductor.

    Over the slow (second) time scale only the *cycle average* of the branch
    current matters.  Inside the negative differential resistance region the
    loop L - Cp - I(v) has a growing oscillation which settles on a limit
    cycle; the average current on that cycle is computed once by integrating

        L dI/dt = V - v ,     Cp dv/dt = I - I_nl(v)

    and is then tabulated in V.  Outside the NDR region the branch is static.
    """

    def __init__(self, elem, L):
        self.e, self.L = elem, L
        self.tab = None

    def _limit_cycle(self, V, nsub=150, nper=6):
        """Runge-Kutta 4 integration of the fast loop, then the mean current
        over an integer number of periods (upward crossings of v = V)."""
        e, L, Cp = self.e, self.L, self.e.Cp
        dt = 2.0 * math.pi * math.sqrt(L * Cp) / nsub
        v, I = V * 1.001 + 1e-4, e.cur(V)

        def f(vv, ii):
            return (ii - e.cur(vv)) / Cp, (V - vv) / L

        def step(v, I):
            a1, b1 = f(v, I)
            a2, b2 = f(v + 0.5 * dt * a1, I + 0.5 * dt * b1)
            a3, b3 = f(v + 0.5 * dt * a2, I + 0.5 * dt * b2)
            a4, b4 = f(v + dt * a3, I + dt * b3)
            return (v + dt / 6.0 * (a1 + 2 * a2 + 2 * a3 + a4),
                    I + dt / 6.0 * (b1 + 2 * b2 + 2 * b3 + b4))

        for _ in range(nsub * 300):                       # let it settle
            v, I = step(v, I)
        prev = v - V                                      # start at a crossing
        for _ in range(nsub * 60):
            v, I = step(v, I)
            if prev < 0.0 <= v - V:
                break
            prev = v - V
        acc = ta = 0.0
        laps = 0
        prev = v - V
        pmin, pmax = 1e9, -1e9
        for _ in range(nsub * 60):
            iold = I
            v, I = step(v, I)
            acc += 0.5 * (iold + I) * dt
            ta += dt
            pmin, pmax = min(pmin, v), max(pmax, v)
            if prev < 0.0 <= v - V:
                laps += 1
                if laps >= nper:
                    break
            prev = v - V
        self.last_period = ta / max(laps, 1)
        self.last_swing = (pmin, pmax)
        return acc / max(ta, 1e-18)

    def table(self):
        if self.tab is None:
            vp, _ip = self.e.peak()
            vv, _iv = self.e.valley()
            self.v1, self.v2 = vp, vv
            n = 25
            self.tab = []
            self.periods = []
            for i in range(n):
                V = vp + (vv - vp) * i / (n - 1.0)
                self.tab.append(self._limit_cycle(V))
                self.periods.append(getattr(self, "last_period", 0.0))
        return self.tab

    def cur(self, V):
        """Average current drawn by the branch at the (slow) terminal voltage V."""
        if V <= 0.0:
            return self.e.cur(V)
        tb = self.table()
        if V <= self.v1 or V >= self.v2:
            return self.e.cur(V)
        f = (V - self.v1) / (self.v2 - self.v1) * (len(tb) - 1)
        i = min(len(tb) - 2, int(f))
        g = f - i
        return tb[i] * (1.0 - g) + tb[i + 1] * g

    def dcur(self, V):
        h = 1e-4
        return (self.cur(V + h) - self.cur(V - h)) / (2.0 * h)


class Truth:
    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1, 10 ** 9)
        self.seed = int(seed)
        rng = random.Random(self.seed)
        self.rng = rng
        self.noise = random.Random(self.seed ^ 0xC0FFEE)

        self.I0 = 6.0e-3 * rng.uniform(0.985, 1.015)      # current source
        self.Vcompl = 0.6125
        self.I0_ripple = rng.uniform(0.2e-5, 0.6e-5)      # small current drift with voltage

        self.Vmax = rng.uniform(0.500, 0.580)             # I_nl(Vmax) = I0
        self.elem = NonlinearElement(ip=rng.uniform(4.3e-3, 5.1e-3),
                                     vp=rng.uniform(0.062, 0.080),
                                     vt=rng.uniform(0.044, 0.052),
                                     vmax=self.Vmax, i0=self.I0,
                                     cp=rng.uniform(0.8e-9, 1.3e-9))
        self.cap = DoubleLayerCap(c0=rng.uniform(1.78, 1.96), a=rng.uniform(0.14, 0.26))
        self.L = 10e-6
        self.branch = LCBranch(self.elem, self.L)

        self.R_amp = 1.0                                   # ammeter shunt
        self.R_volt = 1.0e6                                # voltmeter, 0..2 V range
        self.R_volt_hi = 57.0e3                            # 2..10 V range
        self.v_noise = rng.uniform(0.04e-3, 0.09e-3)       # voltmeter noise [V]
        self.i_noise = rng.uniform(0.9e-6, 2.2e-6)         # ammeter noise [A]
        self.d_noise = rng.uniform(0.006, 0.013)           # noise on the derivatives [mV/s]


# ==========================================================================
#  2.  circuit solver (MNA + Newton, charge conserving capacitor)
# ==========================================================================
class Circuit:
    """Nodes are built by merging terminals joined with test leads."""

    def __init__(self, rig):
        self.rig = rig

    def nodes(self):
        parent = {t: t for t in TERMINALS}

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        for a, b in self.rig.leads:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
        idx, mapping = {}, {}
        for t in TERMINALS:
            r = find(t)
            if r not in idx:
                idx[r] = len(idx)
            mapping[t] = idx[r]
        return mapping, len(idx)

    def solve(self, dt, v_bb_prev):
        """One implicit time step.  Returns (node voltages, mapping, currents)."""
        rig, t = self.rig, self.rig.truth
        mp, n = self.nodes()
        # reference node: the one carrying the black box negative terminal
        ref = mp["bb-"]
        v = [0.0] * n
        v[mp["bb+"]] = v_bb_prev
        q_prev = t.cap.charge(v_bb_prev)
        for _it in range(60):
            A = [[0.0] * n for _ in range(n)]
            b = [0.0] * n
            for i in range(n):                      # keep the matrix regular
                A[i][i] += 1e-9

            def res(i, j, g):
                A[i][i] += g
                A[j][j] += g
                A[i][j] -= g
                A[j][i] -= g

            def inj(i, j, cur):                     # current from j to i
                b[i] += cur
                b[j] -= cur

            # ---- multimeter -------------------------------------------------
            if rig.mm_on:
                res(mp["mm_in"], mp["mm_out"], 1.0 / t.R_amp)
                rv = t.R_volt if abs(v[mp["mm_out"]] - v[mp["mm_gnd"]]) < 2.0 else t.R_volt_hi
                res(mp["mm_out"], mp["mm_gnd"], 1.0 / rv)
            else:
                res(mp["mm_in"], mp["mm_out"], 1e-12)
                res(mp["mm_out"], mp["mm_gnd"], 1e-12)
            # ---- current source ---------------------------------------------
            vp, vm = mp["cs+"], mp["cs-"]
            if rig.cs_on:
                vcs = v[vp] - v[vm]
                i0 = t.I0 * (1.0 - t.I0_ripple * vcs / 1e-3)
                inj(vp, vm, i0)
                over = 0.0
                if vcs > t.Vcompl:
                    over = vcs - t.Vcompl
                elif vcs < -t.Vcompl:
                    over = vcs + t.Vcompl
                if over != 0.0:                      # compliance: stiff clamp
                    g = 50.0
                    sgn = 1.0 if over > 0.0 else -1.0
                    res(vp, vm, g)
                    inj(vp, vm, sgn * g * t.Vcompl)
            else:
                res(vp, vm, 1e-12)
            # ---- black box ---------------------------------------------------
            bp, bm = mp["bb+"], mp["bb-"]
            vbb = v[bp] - v[bm]
            cc = t.cap.cap(vbb) / dt
            ic = (t.cap.charge(vbb) - q_prev) / dt
            res(bp, bm, cc)
            inj(bp, bm, -(ic - cc * vbb))
            dev = t.branch if rig.bb_inductor else t.elem
            ib = dev.cur(vbb)
            gb = max(dev.dcur(vbb), -0.5)
            res(bp, bm, gb)
            inj(bp, bm, -(ib - gb * vbb))
            if rig.shorting:
                res(bp, bm, 20.0)
            # ---- solve (Gaussian elimination with the reference row removed) --
            free = [i for i in range(n) if i != ref]
            m = len(free)
            M = [[A[free[i]][free[j]] for j in range(m)] + [b[free[i]]] for i in range(m)]
            for i in range(m):
                p = max(range(i, m), key=lambda k: abs(M[k][i]))
                if abs(M[p][i]) < 1e-18:
                    continue
                M[i], M[p] = M[p], M[i]
                for k in range(i + 1, m):
                    f = M[k][i] / M[i][i]
                    if f:
                        for j in range(i, m + 1):
                            M[k][j] -= f * M[i][j]
            x = [0.0] * m
            for i in range(m - 1, -1, -1):
                if abs(M[i][i]) < 1e-18:
                    continue
                s = M[i][m] - sum(M[i][j] * x[j] for j in range(i + 1, m))
                x[i] = s / M[i][i]
            newv = [0.0] * n
            for i, f in enumerate(free):
                newv[f] = x[i]
            step = max(abs(newv[i] - v[i]) for i in range(n))
            damp = 1.0 if step < 0.05 else 0.05 / step
            v = [v[i] + damp * (newv[i] - v[i]) for i in range(n)]
            if step < 1e-10:
                break
        i_amp = (v[mp["mm_in"]] - v[mp["mm_out"]]) / t.R_amp if rig.mm_on else 0.0
        v_volt = v[mp["mm_out"]] - v[mp["mm_gnd"]] if rig.mm_on else 0.0
        return v, mp, i_amp, v_volt


# ==========================================================================
#  3.  IPhO-measure
# ==========================================================================
class Sample:
    __slots__ = ("n", "s", "t", "V", "dV", "I", "dI")

    def __init__(self, n, s, t, V, dV, I, dI):
        self.n, self.s, self.t, self.V, self.dV, self.I, self.dI = n, s, t, V, dV, I, dI


def fmt_v(v):
    if abs(v) < 2.0:
        return "%7.1fmV" % (v * 1e3)
    return "%8.4fV" % v


def fmt_i(i):
    if abs(i) < 1.0:
        return "%6.1fmA" % (i * 1e3)
    return "%7.3fA" % i


def fmt_der(d):
    if d is None:
        return "  +nan/s"
    return "%+7.2f/s" % d


class Multimeter:
    """The instrument: 2000 sample flash memory, sets, and the four line LCD."""

    MEM = 2000

    def __init__(self, truth):
        self.t = truth
        self.on = False
        self.measuring = False
        self.set_no = 0
        self.n = 0
        self.t0 = 0.0
        self.mem = []
        self.browse = None            # index in mem while browsing
        self.frozen = None
        self.live = dict(t=0.0, V=0.0, dV=0.0, I=0.0, dI=0.0, nanV=False, nanI=False)

    # --------------------------------------------------------------- buttons
    def power(self, now=0.0):
        self.on = not self.on
        self.browse = None
        if self.on:
            self.measuring = False             # on, but not measuring until START (manual)
            self.set_no = max([m.s for m in self.mem] + [0])
            self.n = 0
            self.t0 = now
            self.frozen = None
        else:
            self.measuring = False

    def start(self, now):
        if not self.on:
            return
        self.measuring = True
        self.set_no = max([m.s for m in self.mem] + [self.set_no]) + 1
        self.n = 0
        self.t0 = now
        self.frozen = None
        self.browse = None

    def stop(self):
        if not self.on:
            return
        self.measuring = False
        L = self.live
        self.frozen = Sample(self.n, self.set_no, L["t"] - self.t0, L["V"],
                             None if L["nanV"] else L["dV"], L["I"],
                             None if L["nanI"] else L["dI"])

    def sample(self, now):
        if not (self.on and self.measuring):
            return
        self.n += 1
        L = self.live
        s = Sample(self.n, self.set_no, now - self.t0, L["V"],
                   None if L["nanV"] else L["dV"], L["I"],
                   None if L["nanI"] else L["dI"])
        self.mem.append(s)
        if len(self.mem) > self.MEM:
            self.mem.pop(0)

    def step_browse(self, d):
        if not self.on or not self.mem:
            return
        if self.browse is None:
            self.browse = len(self.mem) - 1
        else:
            self.browse = max(0, min(len(self.mem) - 1, self.browse + d))

    # ----------------------------------------------------------------- display
    def lines(self):
        if not self.on:
            return ["", "", "", ""]
        if self.browse is not None and self.mem:
            s = self.mem[self.browse]
            V, dV, I, dI, tt, n, ss = s.V, s.dV, s.I, s.dI, s.t, s.n, s.s
        elif self.measuring:
            L = self.live
            V, I, tt = L["V"], L["I"], L["t"] - self.t0
            dV = None if L["nanV"] else L["dV"]
            dI = None if L["nanI"] else L["dI"]
            n, ss = self.n, self.set_no
        elif self.frozen is not None:
            s = self.frozen
            V, dV, I, dI, tt, n, ss = s.V, s.dV, s.I, s.dI, s.t, s.n, s.s
        else:
            return ["n=000 s=00 t=     0.0s", "U=    ---  ", "I=    ---  ", "P=   ---   R=---"]
        p = V * I
        r = V / I if abs(I) > 1e-9 else None
        l1 = "n=%03d s=%02d t=%8.1fs" % (n, ss, tt)
        l2 = "U=%s %s" % (fmt_v(V), fmt_der(dV))
        l3 = "I=%s %s" % (fmt_i(I), fmt_der(dI))
        pw = "%8.0fuW" % (p * 1e6) if abs(p) < 1.0 else "%8.4fW" % p
        l4 = "P=%s R=%s" % (pw, ("%.3f" % r) if r is not None and abs(r) < 1e6 else "+inf")
        return [l1, l2, l3, l4]


# ==========================================================================
#  4.  the rig
# ==========================================================================
BOXES = [
    ("mm", "IPhO-measure 멀티미터", "IPhO-measure multimeter"),
    ("cs", "전류원 상자", "current source box"),
    ("bb", "블랙박스", "black box"),
]
LEAD_MAX = 4


class Rig:
    def __init__(self, seed=None):
        self.truth = Truth(seed)
        self.mm = Multimeter(self.truth)
        self.placed = set()
        self.leads = []
        self.cs_on = False
        self.bb_inductor = False
        self.mm_on = False
        self.shorting = False
        self.v_bb = 0.0
        self.q_bb = 0.0
        self.t_sim = 0.0
        self.speed = 1.0
        self.circuit = Circuit(self)
        self._hist = []            # (t, V, I) for the instrument derivatives
        self.msg = ""

    # ------------------------------------------------------------- assembly
    def place(self, pid):
        if pid in self.placed or pid not in [b[0] for b in BOXES]:
            return False
        self.placed.add(pid)
        return True

    def boxes_ready(self):
        return all(b[0] in self.placed for b in BOXES)

    def add_lead(self, a, b):
        if not self.boxes_ready():
            self.msg = T("먼저 세 상자를 실험대에 놓아야 한다.", "put the three boxes on the bench first.")
            return False
        if a == b or a not in TERMINALS or b not in TERMINALS:
            return False
        if len(self.leads) >= LEAD_MAX:
            self.msg = T("리드선은 4개뿐이다.", "only four test leads are available.")
            return False
        if (a, b) in self.leads or (b, a) in self.leads:
            return False
        self.leads.append((a, b))
        return True

    def remove_lead(self, i):
        if 0 <= i < len(self.leads):
            self.leads.pop(i)
            return True
        return False

    def clear_leads(self):
        self.leads = []

    def wiring_text(self):
        if not self.leads:
            return T("연결 없음", "nothing connected")
        return " · ".join("%s-%s" % (TERM_LABEL.get(a, a), TERM_LABEL.get(b, b))
                          if False else "%s\u2192%s" % (a, b) for a, b in self.leads)

    # -------------------------------------------------------------- switches
    def set_cs(self, on):
        self.cs_on = bool(on)

    def set_inductor(self, enabled):
        """Rocker on the black box:  "I" shorts the inductor, "0" enables it."""
        self.bb_inductor = bool(enabled)

    def set_mm_power(self):
        self.mm.power(self.t_sim)
        self.mm_on = self.mm.on

    def short_box(self, on):
        self.shorting = bool(on)

    # ------------------------------------------------------------- evolution
    def advance(self, real_dt):
        """Advance the simulated time by real_dt * speed."""
        target = max(real_dt, 1e-6) * self.speed
        done = 0.0
        v_volt = i_amp = 0.0
        while done < target - 1e-12:
            dt = min(0.25, target - done)
            v, mp, i_amp, v_volt = self.circuit.solve(dt, self.v_bb)
            self.v_bb = v[mp["bb+"]] - v[mp["bb-"]]
            done += dt
            self.t_sim += dt
            self._hist.append((self.t_sim, v_volt, i_amp))
            if len(self._hist) > 400:
                self._hist.pop(0)
        self._update_live(v_volt, i_amp)

    def _update_live(self, v_volt, i_amp):
        t = self.truth
        vn = v_volt + t.noise.gauss(0.0, t.v_noise)
        inn = i_amp + t.noise.gauss(0.0, t.i_noise)
        V = round(vn * 1e4) / 1e4 if abs(vn) < 2.0 else round(vn * 1e4) / 1e4   # 0.1 mV
        I = round(inn * 1e4) / 1e4                                              # 0.1 mA
        dV = dI = 0.0
        nanV = nanI = False
        h = [p for p in self._hist if p[0] > self.t_sim - 4.0]
        if len(h) >= 2 and (h[-1][0] - h[0][0]) > 1e-6:
            span = h[-1][0] - h[0][0]
            dV = (h[-1][1] - h[0][1]) / span * 1e3          # mV/s
            dI = (h[-1][2] - h[0][2]) / span * 1e3          # mA/s
            dV += t.noise.gauss(0.0, t.d_noise)
            dI += t.noise.gauss(0.0, t.d_noise * 0.5)
            dV = round(dV * 100) / 100.0
            dI = round(dI * 100) / 100.0
            if abs(dV) > 400.0:
                nanV = True
            if abs(dI) > 400.0:
                nanI = True
        else:
            nanV = nanI = True
        self.mm.live = dict(t=self.t_sim, V=V, dV=dV, I=I, dI=dI, nanV=nanV, nanI=nanI)

    # -------------------------------------------------------------- readouts
    def display(self):
        return self.mm.lines()

    def display_text(self):
        return "\n".join(self.mm.lines())


# ==========================================================================
#  5.  panel geometry and painting  (drawn from the photographs of the kit)
# ==========================================================================
MM_BOX = (30, 26, 400, 258)          # x, y, w, h
CS_BOX = (470, 26, 300, 150)
BB_BOX = (470, 206, 300, 190)

SOCKETS = {
    "mm_in":  (105, 254, "#c02020"),
    "mm_out": (200, 254, "#c02020"),
    "mm_gnd": (295, 254, "#1a1a1a"),
    "cs+":    (545, 140, "#c02020"),
    "cs-":    (640, 140, "#1a1a1a"),
    "bb+":    (545, 355, "#c02020"),
    "bb-":    (640, 355, "#1a1a1a"),
}
SOCK_BOX = {"mm_in": "mm", "mm_out": "mm", "mm_gnd": "mm",
            "cs+": "cs", "cs-": "cs", "bb+": "bb", "bb-": "bb"}

MM_BUTTONS = [("start", "START", 52, 196), ("stop", "STOP", 122, 196),
               ("prev", "PREV", 192, 196), ("next", "NEXT", 262, 196),
               ("sample", "SAMPLE", 332, 196)]
MM_POWER = (404, 52)
CS_SWITCH = (700, 96)
BB_SWITCH = (700, 268)


def rrect(cv, x0, y0, x1, y1, r, **kw):
    cv.create_polygon(
        x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
        x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0,
        smooth=True, **kw)


class Painter:
    """Draws the three instruments; identical in both tabs so that the student
    always sees the same hardware."""

    LCD_FONT = ("Courier", 13, "bold")

    def __init__(self, rig):
        self.rig = rig
        self.lcd_ids = []

    # ------------------------------------------------------------------ boxes
    def _ghost(self, cv, box, label):
        x, y, w, h = box
        cv.create_rectangle(x, y, x + w, y + h, outline="#9aa5b1", width=2, dash=(6, 4))
        cv.create_text(x + w / 2, y + h / 2, text=label, fill="#7b8794",
                       font=("Helvetica", 11))

    def multimeter(self, cv, live=True):
        x, y, w, h = MM_BOX
        if "mm" not in self.rig.placed:
            self._ghost(cv, MM_BOX, T("여기에 IPhO-measure", "IPhO-measure here"))
            return
        rrect(cv, x, y, x + w, y + h, 10, fill="#2b2f33", outline="#15181a", width=2)
        rrect(cv, x + 4, y + 4, x + w - 4, y + h - 4, 8, fill="#3a4046", outline="")
        cv.create_text(x + 14, y + 14, anchor="nw", text="IPhO-measure",
                       fill="#e8eef2", font=("Helvetica", 11, "bold"))
        # LCD
        lx0, ly0, lx1, ly1 = x + 14, y + 34, x + w - 62, y + 152
        cv.create_rectangle(lx0 - 3, ly0 - 3, lx1 + 3, ly1 + 3, fill="#1d2320", outline="")
        on = self.rig.mm.on
        cv.create_rectangle(lx0, ly0, lx1, ly1, fill="#b9cf9a" if on else "#5f6a58",
                            outline="#7d8c6c")
        self.lcd_ids = []
        lines = self.rig.display() if on else ["", "", "", ""]
        for i in range(4):
            tid = cv.create_text(lx0 + 10, ly0 + 12 + i * 27, anchor="nw",
                                 text=lines[i], fill="#12180f", font=self.LCD_FONT)
            self.lcd_ids.append(tid)
        # power button
        px, py = x + MM_POWER[0] - MM_BOX[0], y + MM_POWER[1] - MM_BOX[1]
        cv.create_oval(px - 12, py - 12, px + 12, py + 12,
                       fill="#8f2020" if on else "#4a4f54", outline="#15181a", width=2,
                       tags=("mmbtn:power",))
        cv.create_text(px, py + 22, text="POWER", fill="#c8d2d8", font=("Helvetica", 7))
        # buttons
        for key, lab, bx, by in MM_BUTTONS:
            gx, gy = x + bx - MM_BOX[0], y + by - MM_BOX[1]
            rrect(cv, gx - 30, gy - 13, gx + 30, gy + 13, 5, fill="#5a6068",
                  outline="#22262a", width=1, tags=("mmbtn:" + key,))
            cv.create_text(gx, gy, text=lab, fill="#f2f6f8",
                           font=("Helvetica", 8, "bold"), tags=("mmbtn:" + key,))
        # sockets
        for nm in ("mm_in", "mm_out", "mm_gnd"):
            self.socket(cv, nm)

    def source(self, cv):
        x, y, w, h = CS_BOX
        if "cs" not in self.rig.placed:
            self._ghost(cv, CS_BOX, T("여기에 전류원 상자", "current source here"))
            return
        rrect(cv, x, y, x + w, y + h, 8, fill="#8b8f94", outline="#4a4e52", width=2)
        rrect(cv, x + 4, y + 4, x + w - 4, y + h - 4, 6, fill="#a3a8ad", outline="")
        cv.create_text(x + 14, y + 12, anchor="nw", text=T("전류원", "CURRENT SOURCE"),
                       fill="#20242a", font=("Helvetica", 11, "bold"))
        cv.create_text(x + 14, y + 32, anchor="nw", text="I \u2248 6 mA",
                       fill="#3a3f45", font=("Helvetica", 10))
        self.rocker(cv, CS_SWITCH, self.rig.cs_on, "cssw")
        self.socket(cv, "cs+")
        self.socket(cv, "cs-")

    def blackbox(self, cv):
        x, y, w, h = BB_BOX
        if "bb" not in self.rig.placed:
            self._ghost(cv, BB_BOX, T("여기에 블랙박스", "black box here"))
            return
        rrect(cv, x, y, x + w, y + h, 8, fill="#33373c", outline="#14171a", width=2)
        rrect(cv, x + 4, y + 4, x + w - 4, y + h - 4, 6, fill="#42474d", outline="")
        cv.create_text(x + 14, y + 12, anchor="nw", text=T("비선형 블랙박스", "NONLINEAR BLACK BOX"),
                       fill="#eef2f5", font=("Helvetica", 11, "bold"))
        cv.create_text(x + 14, y + 32, anchor="nw",
                       text=T("봉인 \u2014 열지 마시오", "SEALED \u2014 do not open"),
                       fill="#c0492f", font=("Helvetica", 9))
        cv.create_line(x + 4, y + 58, x + w - 4, y + 58, fill="#c9a227", width=6, dash=(14, 8))
        self.rocker(cv, BB_SWITCH, not self.rig.bb_inductor, "bbsw")
        self.socket(cv, "bb+")
        self.socket(cv, "bb-")

    # --------------------------------------------------------------- details
    def rocker(self, cv, pos, up, tag):
        x, y = pos
        cv.create_rectangle(x - 17, y - 26, x + 17, y + 26, fill="#26292d",
                            outline="#101214", width=2, tags=(tag,))
        if up:
            cv.create_rectangle(x - 13, y - 22, x + 13, y + 2, fill="#e2e6ea",
                                outline="#8b9096", tags=(tag,))
        else:
            cv.create_rectangle(x - 13, y - 2, x + 13, y + 22, fill="#e2e6ea",
                                outline="#8b9096", tags=(tag,))
        cv.create_text(x + 27, y - 15, text="I", font=("Helvetica", 9, "bold"),
                       fill="#e8eef2" if tag == "bbsw" else "#20242a")
        cv.create_text(x + 27, y + 15, text="0", font=("Helvetica", 9, "bold"),
                       fill="#e8eef2" if tag == "bbsw" else "#20242a")

    def socket(self, cv, nm, hilite=False):
        x, y, col = SOCKETS[nm]
        cv.create_oval(x - 14, y - 14, x + 14, y + 14, fill="#d8dde2",
                       outline="#6b7178", width=2, tags=("sock:" + nm,))
        cv.create_oval(x - 9, y - 9, x + 9, y + 9, fill=col, outline="#2a2d31",
                       tags=("sock:" + nm,))
        cv.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#101214", outline="",
                       tags=("sock:" + nm,))
        if hilite:
            cv.create_oval(x - 19, y - 19, x + 19, y + 19, outline="#f5c542", width=3)
        lab = TERM_LABEL[nm]
        dark = nm.startswith("mm") or nm.startswith("bb")
        cv.create_text(x, y - 25, text=lab, font=("Helvetica", 9, "bold"),
                       fill="#e8eef2" if dark else "#20242a")

    def wires(self, cv):
        cols = ["#c62828", "#1565c0", "#2e7d32", "#f9a825"]
        for i, (a, b) in enumerate(self.rig.leads):
            x1, y1, _ = SOCKETS[a]
            x2, y2, _ = SOCKETS[b]
            mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0 + 42
            cv.create_line(x1, y1, mx, my, x2, y2, smooth=True, width=6,
                           fill="#20242a", capstyle="round")
            cv.create_line(x1, y1, mx, my, x2, y2, smooth=True, width=4,
                           fill=cols[i % 4], capstyle="round", tags=("lead:%d" % i,))

    def all(self, cv, sel=None):
        cv.delete("all")
        cv.create_rectangle(0, 0, 820, 430, fill="#eceff1", outline="")
        self.multimeter(cv)
        self.source(cv)
        self.blackbox(cv)
        self.wires(cv)
        if sel:
            self.socket(cv, sel, hilite=True)


# ==========================================================================
#  6.  application
# ==========================================================================
GIVEN = [
    ("전류원: 출력 약 6 mA, 최대 출력 전압 약 0.6 V",
     "current source: about 6 mA, maximum output voltage about 0.6 V"),
    ("블랙박스: 스위치 I = 인덕터 단락, 0 = 인덕터(10 \u00b5H) 삽입",
     "black box: switch I shorts the inductor, 0 inserts it (10 \u00b5H)"),
    ("IPhO-measure: IN\u2013OUT 전류계(내부 1 \u03a9), OUT\u2013GND 전압계(0\u20132 V 범위 1 M\u03a9)",
     "IPhO-measure: ammeter between IN and OUT (1 \u03a9), voltmeter between OUT and GND (1 M\u03a9 on 0\u20132 V)"),
    ("표시: n 샘플 번호, s 세트 번호, t 시각, U 전압, I 전류, P 전력, R 저항",
     "display: n sample, s set, t time, U voltage, I current, P power, R resistance"),
    ("U와 I 뒤의 숫자는 그 값의 시간 미분(단위 mV/s, mA/s)이다",
     "the number after U and I is its time derivative (mV/s, mA/s)"),
    ("메모리 2000 샘플, SAMPLE로 저장, PREV/NEXT로 열람",
     "memory holds 2000 samples; SAMPLE stores, PREV/NEXT browse"),
    ("블랙박스 단자는 단락시켜도 안전하다", "the black box terminals may be short circuited safely"),
]

PARTS = [("mm", "IPhO-measure 멀티미터", "IPhO-measure multimeter"),
         ("cs", "전류원 상자", "current source box"),
         ("bb", "비선형 블랙박스", "nonlinear black box")]


class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        root = self.root = self
        self.rig = Rig(seed)
        self.paint = Painter(self.rig)       # assembly canvas
        self.paintb = Painter(self.rig)      # bench canvas
        self.sel = None
        self.drag = None
        root.title(APP_TITLE + "  \u2014  " + T("비선형 블랙박스", "Nonlinear Black Box"))
        root.geometry("1240x760")
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        self.tab_asm = tk.Frame(nb, bg="#f5f6f7")
        self.tab_ben = tk.Frame(nb, bg="#f5f6f7")
        nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.tab_ben, text=T(" 실험대 ", " Bench "))
        self._build_asm()
        self._build_ben()
        self._redraw_ben()
        self.last = time.time()
        self.tick()

    # ------------------------------------------------------------- assembly
    def _build_asm(self):
        f = self.tab_asm
        left = tk.Frame(f, bg="#f5f6f7")
        left.pack(side="left", fill="y", padx=10, pady=10)
        tk.Label(left, text=T("부품 상자", "parts box"), bg="#f5f6f7",
                 font=("Helvetica", 12, "bold")).pack(anchor="w")
        self.lb = tk.Listbox(left, width=30, height=6, font=("Helvetica", 10),
                             activestyle="none")
        self.lb.pack(pady=(4, 8))
        self.lb.bind("<ButtonPress-1>", self._lb_press)
        tk.Label(left, justify="left", bg="#f5f6f7", fg="#4b5563", wraplength=230,
                 text=T("부품을 오른쪽 작업대로 끌어다 놓는다.\n"
                        "상자를 우클릭하면 부품 상자로 돌아간다.\n\n"
                        "세 상자를 모두 놓으면 단자를 눌러 리드선을 연결할 수 있다.\n"
                        "단자 \u2192 단자 순서로 누르면 리드선 하나가 연결된다.\n"
                        "리드선을 우클릭하면 뽑힌다. 리드선은 4개뿐이다.",
                        "drag a part onto the bench on the right.\n"
                        "right click a box to put it back.\n\n"
                        "once all three boxes are down, click a socket and then another "
                        "socket to plug in a test lead.\nright click a lead to unplug it. "
                        "only four leads are available.")).pack(anchor="w")
        gv = tk.LabelFrame(left, text=T("주어진 값", "given"), bg="#f5f6f7",
                           font=("Helvetica", 10, "bold"))
        gv.pack(fill="x", pady=12)
        for ko, en in GIVEN:
            tk.Label(gv, text="\u2022 " + T(ko, en), justify="left", wraplength=225,
                     bg="#f5f6f7", fg="#374151", font=("Helvetica", 9)).pack(anchor="w")
        self.asm_msg = tk.Label(left, text="", bg="#f5f6f7", fg="#b91c1c",
                                wraplength=230, justify="left", font=("Helvetica", 9))
        self.asm_msg.pack(anchor="w", pady=6)

        right = tk.Frame(f, bg="#f5f6f7")
        right.pack(side="left", fill="both", expand=True, padx=6, pady=10)
        self.cv_asm = tk.Canvas(right, width=830, height=440, bg="#eceff1",
                                highlightthickness=1, highlightbackground="#cfd8dc")
        self.cv_asm.pack(anchor="w")
        self.cv_asm.bind("<ButtonRelease-1>", self._asm_release)
        self.cv_asm.bind("<Button-1>", self._asm_click)
        self.cv_asm.bind("<Button-3>", self._asm_right)
        self.cv_asm.bind("<Motion>", self._asm_motion)
        self.asm_state = tk.Label(right, text="", bg="#f5f6f7", fg="#1f2937",
                                  font=("Helvetica", 10), justify="left")
        self.asm_state.pack(anchor="w", pady=8)
        self._fill_parts()
        self._redraw_asm()

    def _fill_parts(self):
        self.lb.delete(0, "end")
        self.parts_left = [p for p in PARTS if p[0] not in self.rig.placed]
        for pid, ko, en in self.parts_left:
            self.lb.insert("end", "  " + T(ko, en))
        n = LEAD_MAX - len(self.rig.leads)
        self.lb.insert("end", T("  테스트 리드선  \u00d7 %d" % n, "  test leads  \u00d7 %d" % n))

    def _lb_press(self, ev):
        i = self.lb.nearest(ev.y)
        if 0 <= i < len(self.parts_left):
            self.drag = self.parts_left[i][0]

    def _asm_motion(self, ev):
        if self.drag:
            self._redraw_asm()
            self.cv_asm.create_text(ev.x, ev.y, text=T("\u25a0 놓기", "\u25a0 drop"),
                                    fill="#2563eb", font=("Helvetica", 11, "bold"))

    def _asm_release(self, ev):
        if not self.drag:
            return
        pid, self.drag = self.drag, None
        if self.rig.place(pid):
            self.asm_msg.config(text="")
        self._fill_parts()
        self._redraw_asm()

    def _hit_socket(self, cv, ev):
        for it in cv.find_overlapping(ev.x - 3, ev.y - 3, ev.x + 3, ev.y + 3):
            for tg in cv.gettags(it):
                if tg.startswith("sock:"):
                    return tg[5:]
        return None

    def _hit_tag(self, cv, ev, pref):
        for it in cv.find_overlapping(ev.x - 4, ev.y - 4, ev.x + 4, ev.y + 4):
            for tg in cv.gettags(it):
                if tg.startswith(pref):
                    return tg[len(pref):]
        return None

    def _asm_click(self, ev):
        if self.drag:
            return
        nm = self._hit_socket(self.cv_asm, ev)
        if nm is None:
            self.sel = None
            self._redraw_asm()
            return
        if self.sel is None:
            self.sel = nm
        else:
            a, self.sel = self.sel, None
            if not self.rig.add_lead(a, nm):
                self.asm_msg.config(text=self.rig.msg)
                self.rig.msg = ""
            else:
                self.asm_msg.config(text="")
        self._fill_parts()
        self._redraw_asm()

    def _asm_right(self, ev):
        i = self._hit_tag(self.cv_asm, ev, "lead:")
        if i is not None:
            self.rig.remove_lead(int(i))
            self._fill_parts()
            self._redraw_asm()
            return
        for pid, box in (("mm", MM_BOX), ("cs", CS_BOX), ("bb", BB_BOX)):
            x, y, w, h = box
            if x <= ev.x <= x + w and y <= ev.y <= y + h and pid in self.rig.placed:
                if any(SOCK_BOX[a] == pid or SOCK_BOX[b] == pid for a, b in self.rig.leads):
                    self.asm_msg.config(text=T("리드선이 꽂혀 있어 상자를 치울 수 없다.",
                                               "unplug the leads before removing the box."))
                    return
                self.rig.placed.discard(pid)
                self._fill_parts()
                self._redraw_asm()
                return

    def _redraw_asm(self):
        self.paint.all(self.cv_asm, self.sel)
        txt = T("놓인 상자: ", "boxes on the bench: ") + \
            (", ".join(sorted(self.rig.placed)) if self.rig.placed else T("없음", "none"))
        txt += "\n" + T("리드선 %d/4:  " % len(self.rig.leads), "leads %d/4:  " % len(self.rig.leads))
        txt += "   ".join("%s \u2013 %s" % (a, b) for a, b in self.rig.leads) or T("없음", "none")
        self.asm_state.config(text=txt)

    # ---------------------------------------------------------------- bench
    def _build_ben(self):
        f = self.tab_ben
        left = tk.Frame(f, bg="#f5f6f7")
        left.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self.cv_ben = tk.Canvas(left, width=830, height=440, bg="#eceff1",
                                highlightthickness=1, highlightbackground="#cfd8dc")
        self.cv_ben.pack(anchor="w")
        self.cv_ben.bind("<Button-1>", self._ben_click)
        bar = tk.Frame(left, bg="#f5f6f7")
        bar.pack(fill="x", pady=8)
        tk.Label(bar, text=T("시간 배속", "time factor"), bg="#f5f6f7",
                 font=("Helvetica", 10)).pack(side="left")
        self.spd = tk.StringVar(value="1")
        for s in ("1", "5", "20", "60", "200"):
            tk.Radiobutton(bar, text="\u00d7" + s, value=s, variable=self.spd,
                           bg="#f5f6f7", command=self._set_speed,
                           font=("Helvetica", 10)).pack(side="left")
        self.short = tk.IntVar(value=0)
        tk.Checkbutton(bar, variable=self.short, bg="#f5f6f7", font=("Helvetica", 10),
                       command=lambda: self.rig.short_box(self.short.get()),
                       text=T("리드선으로 블랙박스 + / \u2212 단자 단락",
                              "short the black box terminals with a lead")).pack(side="left", padx=18)
        self.ben_state = tk.Label(left, text="", bg="#f5f6f7", fg="#1f2937",
                                  justify="left", font=("Helvetica", 10))
        self.ben_state.pack(anchor="w")

        right = tk.Frame(f, bg="#f5f6f7", width=350)
        right.pack(side="left", fill="both", padx=8, pady=8)
        tk.Label(right, text=T("관측 노트", "notebook"), bg="#f5f6f7",
                 font=("Helvetica", 12, "bold")).pack(anchor="w")
        self.note = tk.Text(right, width=44, height=34, font=("Courier", 9),
                            bg="#ffffff", relief="solid", borderwidth=1)
        self.note.pack(pady=4)
        nb2 = tk.Frame(right, bg="#f5f6f7")
        nb2.pack(fill="x")
        tk.Button(nb2, text=T("표시값을 노트에 적기", "copy the display into the notebook"),
                  command=self._copy_note).pack(side="left")
        tk.Button(nb2, text=T("노트 지우기", "clear"),
                  command=lambda: self.note.delete("1.0", "end")).pack(side="left", padx=6)
        tk.Label(right, justify="left", bg="#f5f6f7", fg="#4b5563", wraplength=330,
                 font=("Helvetica", 9),
                 text=T("계기의 단추는 화면의 계기판에서 직접 누른다. 로커 스위치도 누르면 넘어간다.\n"
                        "표시값은 계기의 분해능(0.1 mV, 0.1 mA, 0.01/s)까지만 읽힌다.",
                        "press the buttons on the drawn panel; the rocker switches toggle "
                        "when clicked.\nreadings carry only the resolution of the "
                        "instrument (0.1 mV, 0.1 mA, 0.01/s).")).pack(anchor="w", pady=6)

    def _set_speed(self):
        self.rig.speed = float(self.spd.get())

    def _copy_note(self):
        self.note.insert("end", "\n".join(self.rig.display()) + "\n\n")
        self.note.see("end")

    def _ben_click(self, ev):
        key = self._hit_tag(self.cv_ben, ev, "mmbtn:")
        if key:
            mm = self.rig.mm
            if key == "power":
                self.rig.set_mm_power()
            elif key == "start":
                mm.start(self.rig.t_sim)
            elif key == "stop":
                mm.stop()
            elif key == "sample":
                mm.sample(self.rig.t_sim)
            elif key == "prev":
                mm.step_browse(-1)
            elif key == "next":
                mm.step_browse(+1)
            self._redraw_ben()
            return
        for it in self.cv_ben.find_overlapping(ev.x - 3, ev.y - 3, ev.x + 3, ev.y + 3):
            tags = self.cv_ben.gettags(it)
            if "cssw" in tags:
                self.rig.set_cs(not self.rig.cs_on)
                self._redraw_ben()
                return
            if "bbsw" in tags:
                self.rig.set_inductor(not self.rig.bb_inductor)
                self._redraw_ben()
                return

    def _redraw_ben(self):
        self.paintb.all(self.cv_ben)
        self._refresh_state()

    # ----------------------------------------------------------------- clock
    def tick(self):
        if not self.winfo_exists():
            return
        now = time.time()
        dt = min(0.4, now - self.last)
        self.last = now
        self.rig.advance(dt)
        if self.rig.mm.on and self.paintb.lcd_ids:
            lines = self.rig.display()
            for i, tid in enumerate(self.paintb.lcd_ids):
                try:
                    self.cv_ben.itemconfig(tid, text=lines[i])
                except tk.TclError:
                    pass
        self._refresh_state()
        self.root.after(100, self.tick)

    def _refresh_state(self):
        st = [T("전류원 스위치: ", "current source: ") +
              ("I (" + T("켜짐", "on") + ")" if self.rig.cs_on
               else "0 (" + T("꺼짐", "off") + ")"),
              T("블랙박스 스위치: ", "black box switch: ") +
              ("0 (" + T("인덕터 삽입", "inductor in") + ")" if self.rig.bb_inductor
               else "I (" + T("인덕터 단락", "inductor shorted") + ")"),
              T("경과 시간 %.1f s" % self.rig.t_sim, "elapsed %.1f s" % self.rig.t_sim),
              T("저장된 샘플 %d개" % len(self.rig.mm.mem),
                "%d samples stored" % len(self.rig.mm.mem))]
        self.ben_state.config(text="   |   ".join(st))


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
    global LANG
    seed = None
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a in ("--en", "--english"):
            LANG = "en"
        elif a.startswith("--seed"):
            seed = int(args[i + 1]) if "=" not in a else int(a.split("=")[1])
    App(seed).mainloop()


if __name__ == "__main__":
    main()
