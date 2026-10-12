#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
13th Asian Physics Olympiad (New Delhi, India, 2012)
Experimental Competition -- Question 2 : ELECTROMAGNETIC INDUCTION
Virtual laboratory simulator.

HaslaLab / HaslaEdu.

Design rules obeyed by this file
--------------------------------
*  The only number the simulator ever shows is the reading of the digital
   multimeter (20 V / 200 V ac ranges, 0.01 V resolution, 1 % + 4 digit
   accuracy) and the values printed on the resistance boards.  Z, R, X, L, M,
   k, R_PE, X_PE, R_R, X_R, dP are never computed for the student.
*  The circuit is solved from the wiring the student actually builds, with a
   complex modified-nodal-analysis solver.  The aluminium core is a genuine
   pair of coupled eddy-current loops, not a fitted correction.
*  Hidden parameters are re-randomised every session.
*  Standard library only.
"""

import cmath
import math
import random
import sys
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


# ============================================================================
#  complex modified nodal analysis
# ============================================================================
def _solve_linear(A, b):
    n = len(b)
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(A[r][i]))
        if abs(A[p][i]) < 1e-40:
            raise ValueError("singular network matrix")
        if p != i:
            A[i], A[p] = A[p], A[i]
            b[i], b[p] = b[p], b[i]
        piv = A[i][i]
        for r in range(i + 1, n):
            f = A[r][i] / piv
            if f != 0:
                Ai, Ar = A[i], A[r]
                for c in range(i, n):
                    Ar[c] -= f * Ai[c]
                b[r] -= f * b[i]
    x = [0j] * n
    for i in range(n - 1, -1, -1):
        s = b[i]
        Ai = A[i]
        for c in range(i + 1, n):
            s -= Ai[c] * x[c]
        x[i] = s / Ai[i]
    return x


def solve_net(nodes, resistors, sources, lbranches, Mmat, omega, gnd,
              leak=1e-9):
    """
    nodes      : iterable of node names (gnd included)
    resistors  : [(a, b, R)]
    sources    : [(a, b, E)]           ideal source, V(a) - V(b) = E
    lbranches  : [(a, b, Rseries, Lself)]
    Mmat       : Mmat[i][j] mutual inductance between lbranches i and j
                 (the diagonal is ignored, Lself is used instead)
    Returns (node_voltage_dict, source_currents, l_currents)
    """
    nodes = list(dict.fromkeys(nodes))
    vmap, k = {}, 0
    for n in nodes:
        if n != gnd:
            vmap[n] = k
            k += 1
    ns, nl = len(sources), len(lbranches)
    N = k + ns + nl
    A = [[0j] * N for _ in range(N)]
    b = [0j] * N

    def add(r, c, val):
        if r is not None and c is not None:
            A[r][c] += val

    def vi(n):
        return vmap.get(n, None)

    for a, bn, R in resistors:
        g = 1.0 / R
        ia, ib = vi(a), vi(bn)
        add(ia, ia, g)
        add(ib, ib, g)
        add(ia, ib, -g)
        add(ib, ia, -g)
    for n in nodes:
        i = vi(n)
        add(i, i, leak)

    for j, (a, bn, E) in enumerate(sources):
        row = k + j
        ia, ib = vi(a), vi(bn)
        add(ia, row, 1.0)
        add(ib, row, -1.0)
        add(row, ia, 1.0)
        add(row, ib, -1.0)
        b[row] = E

    for j, (a, bn, Rs, Ls) in enumerate(lbranches):
        row = k + ns + j
        ia, ib = vi(a), vi(bn)
        add(ia, row, 1.0)
        add(ib, row, -1.0)
        add(row, ia, 1.0)
        add(row, ib, -1.0)
        for l in range(nl):
            col = k + ns + l
            if l == j:
                A[row][col] -= (Rs + 1j * omega * Ls)
            else:
                A[row][col] -= 1j * omega * Mmat[j][l]

    x = _solve_linear(A, b)
    V = {gnd: 0j}
    for n, i in vmap.items():
        V[n] = x[i]
    return V, x[k:k + ns], x[k + ns:]


# ============================================================================
#  hidden physics of the apparatus
# ============================================================================
#  Reference parameter set.  These are the values that reproduce, exactly, the
#  numbers printed in the official model solution of Experiment 2 (R1, L1, R2,
#  L2, M, and the aluminium-core values R1*, L1*, R2*, L2*).
REF = dict(
    f=1000.0,
    R1=52.57, L1=71.40e-3,
    R2=42.96, L2=55.18e-3,
    k12=0.844,
    # two independent eddy-current loops in the aluminium rod: an inner shell
    # coupled mainly to the inner coil and an outer shell coupled to both
    Ra=1.000e-4, La=5.25217e-8,
    Rb=1.000e-4, Lb=4.13866e-8,
    M1a=3.31708e-5, M2a=1.67065e-5,
    M1b=2.01123e-5, M2b=1.94528e-5,
    Mab=0.0,
    E=10.45, rint=33.0,
)


def _cholesky_ok(Mm):
    """True when the inductance matrix is positive definite (passive)."""
    n = len(Mm)
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = Mm[i][j] - sum(L[i][t] * L[j][t] for t in range(j))
            if i == j:
                if s <= 0.0:
                    return False
                L[i][i] = math.sqrt(s)
            else:
                L[i][j] = s / L[j][j]
    return True


class Model(object):
    """Everything in here is invisible to the student."""

    LIDX = {"coil1": 0, "coil2": 1, "coreA": 2, "coreB": 3}

    def __init__(self, seed=None, reference=False):
        if seed is None:
            seed = random.randrange(1, 10 ** 9)
        self.seed = int(seed)
        r = random.Random(self.seed)
        self._r = r
        for _ in range(200):
            p = dict(REF)
            if not reference:
                p["f"] = round(r.uniform(997.0, 1003.0), 1)
                p["L1"] *= r.uniform(0.955, 1.045)
                p["L2"] *= r.uniform(0.955, 1.045)
                p["R1"] *= r.uniform(0.94, 1.06)
                p["R2"] *= r.uniform(0.94, 1.06)
                p["k12"] = r.uniform(0.815, 0.872)
                for key in ("Ra", "Rb", "La", "Lb"):
                    p[key] *= r.uniform(0.90, 1.10)
                for key in ("M1a", "M2a", "M1b", "M2b"):
                    p[key] *= r.uniform(0.94, 1.06)
            p["M12"] = p["k12"] * math.sqrt(p["L1"] * p["L2"])
            Mm = [[p["L1"], p["M12"], p["M1a"], p["M1b"]],
                  [p["M12"], p["L2"], p["M2a"], p["M2b"]],
                  [p["M1a"], p["M2a"], p["Ra"] * 0 + p["La"], p["Mab"]],
                  [p["M1b"], p["M2b"], p["Mab"], p["Lb"]]]
            if _cholesky_ok(Mm):
                break
        else:
            raise RuntimeError("could not draw a passive inductance matrix")
        self.p = p
        self.Mm = Mm
        # instrument imperfections
        self.asym = r.uniform(0.0015, 0.0035) if not reference else 0.0022
        self.drift = r.uniform(0.0015, 0.0030) if not reference else 0.0020
        self.Emax = p["E"] * (1.0 if reference else r.uniform(0.98, 1.03))
        self.rint = p["rint"] * (1.0 if reference else r.uniform(0.88, 1.14))
        # printed tolerance of the resistance boards, per resistor
        self.tolA = [1.0 + (0.0 if reference else r.gauss(0.0, 0.004))
                     for _ in range(10)]
        self.tolB = [1.0 + (0.0 if reference else r.gauss(0.0, 0.006))
                     for _ in range(10)]
        self.tol300 = 1.0 + (0.0 if reference else r.gauss(0.0, 0.003))

    @property
    def omega(self):
        return 2.0 * math.pi * self.p["f"]

    # --- "truth" helpers, used only by the verification harness -------------
    def true_coil(self, which, core):
        """Complex impedance R + jX of one coil, other coil open."""
        p, w = self.p, self.omega
        if which == 1:
            R, L, M = p["R1"], p["L1"], (p["M1a"], p["M1b"])
        else:
            R, L, M = p["R2"], p["L2"], (p["M2a"], p["M2b"])
        Z = R + 1j * w * L
        if core:
            Za = p["Ra"] + 1j * w * p["La"]
            Zb = p["Rb"] + 1j * w * p["Lb"]
            Z += (w * M[0]) ** 2 / Za + (w * M[1]) ** 2 / Zb
        return Z


# ============================================================================
#  the bench:  instruments, sockets, wires
# ============================================================================
#  Instrument sockets.  Their screen positions live in LAYOUT below; the names
#  are what the netlist is built from.
BOARD_A_N = 10          # ten 100 ohm resistors in series
BOARD_B_N = 10          # ten  10 ohm resistors in series
R_A, R_B, R_300 = 100.0, 10.0, 300.0

COMPONENTS = ["gen", "dmm", "coils", "boardA", "boardB", "board300", "wires", "rod"]


def sockets_of(placed):
    out = []
    if "gen" in placed:
        out += ["GEN+", "GEN-"]
    if "coils" in placed:
        out += ["CB1", "CB2", "CG1", "CG2"]
    if "boardA" in placed:
        out += ["RA%d" % i for i in range(BOARD_A_N + 1)]
    if "boardB" in placed:
        out += ["RB%d" % i for i in range(BOARD_B_N + 1)]
    if "board300" in placed:
        out += ["S0", "S1"]
    if "dmm" in placed:
        out += ["DMMV", "DMMC"]
    return out


class Rig(object):
    """The wired-up bench.  Shared by the GUI and by the verification harness."""

    def __init__(self, model):
        self.m = model
        self.placed = set()
        self.wires = []               # list of (socket, socket)
        self.rod = False              # aluminium rod inside the bobbin
        self.power = True
        self.amp = 1.0                # amplitude knob, 0 .. 1
        self.rng = 20.0               # DMM range: 20.0, 200.0 or None (OFF)
        self.probe_v = None           # socket touched by the red  (V/ohm) probe
        self.probe_c = None           # socket touched by the black (COM) probe
        self.polarity = +1            # +1 normal, -1 probes interchanged

    # ---------------- topology ----------------
    def _classes(self):
        parent = {}

        def find(a):
            parent.setdefault(a, a)
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for s in sockets_of(self.placed):
            find(s)
        for a, b in self.wires:
            if a in parent and b in parent:
                union(a, b)
        return {s: find(s) for s in parent}

    def netlist(self):
        m, cls = self.m, self._classes()
        if not cls:
            return None
        nodes = set(cls.values())
        R, V, Ls = [], [], []
        Lnames = []

        def nd(s):
            return cls[s]

        if "gen" in self.placed:
            nodes.add("GEN_INT")
            E = self.m.Emax * self.amp if self.power else 0.0
            V.append(("GEN_INT", nd("GEN-"), complex(E, 0.0)))
            R.append(("GEN_INT", nd("GEN+"), max(self.m.rint, 1e-3)))
        if "boardA" in self.placed:
            for i in range(BOARD_A_N):
                R.append((nd("RA%d" % i), nd("RA%d" % (i + 1)),
                          R_A * m.tolA[i]))
        if "boardB" in self.placed:
            for i in range(BOARD_B_N):
                R.append((nd("RB%d" % i), nd("RB%d" % (i + 1)),
                          R_B * m.tolB[i]))
        if "board300" in self.placed:
            R.append((nd("S0"), nd("S1"), R_300 * m.tol300))
        if "coils" in self.placed:
            Ls.append((nd("CB1"), nd("CB2"), m.p["R1"], m.p["L1"]))
            Lnames.append("coil1")
            Ls.append((nd("CG1"), nd("CG2"), m.p["R2"], m.p["L2"]))
            Lnames.append("coil2")
            if self.rod:
                nodes.update(["CA1", "CA2", "CC1", "CC2"])
                Ls.append(("CA1", "CA2", m.p["Ra"], m.p["La"]))
                Lnames.append("coreA")
                V.append(("CA2", "CA1", 0j))
                Ls.append(("CC1", "CC2", m.p["Rb"], m.p["Lb"]))
                Lnames.append("coreB")
                V.append(("CC2", "CC1", 0j))
        if "dmm" in self.placed and self.rng is not None:
            if self.probe_v and self.probe_c:
                R.append((nd(self.probe_v), nd(self.probe_c), 1.0e7))
        if not Ls and not V:
            return None
        # mutual inductance sub-matrix in the order the branches were added
        n = len(Ls)
        Mm = [[0.0] * n for _ in range(n)]
        for i, a in enumerate(Lnames):
            for j, b in enumerate(Lnames):
                if i != j:
                    Mm[i][j] = m.Mm[m.LIDX[a]][m.LIDX[b]]
        gnd = nd("GEN-") if "gen" in self.placed else sorted(nodes)[0]
        return list(nodes), R, V, Ls, Mm, gnd, cls, Lnames

    def solve(self):
        nl = self.netlist()
        if nl is None:
            return None
        nodes, R, V, Ls, Mm, gnd, cls, Lnames = nl
        try:
            Vn, Is, Il = solve_net(nodes, R, V, Ls, Mm, self.m.omega, gnd)
        except ValueError:
            return None
        return dict(V=Vn, Isrc=Is, Il=Il, cls=cls, Lnames=Lnames)

    # ---------------- the multimeter ----------------
    def true_voltage(self, sa, sb):
        sol = self.solve()
        if sol is None:
            return None
        cls = sol["cls"]
        if sa not in cls or sb not in cls:
            return None
        return abs(sol["V"][cls[sa]] - sol["V"][cls[sb]])

    def read(self):
        """The number on the DMM display, or None when it cannot read."""
        if "dmm" not in self.placed or self.rng is None:
            return None
        if not self.probe_v or not self.probe_c:
            return None
        v = self.true_voltage(self.probe_v, self.probe_c)
        if v is None:
            return None
        # ac asymmetry of the generator: swapping the probes shifts the reading
        v *= (1.0 + self.polarity * self.m.asym)
        v += self.m._r.gauss(0.0, self.m.drift)
        step = 0.01 if self.rng == 20.0 else 0.1
        if v > self.rng * 1.05:
            return "OL"
        return round(math.floor(v / step + 0.5) * step, 3)

    def read_both(self):
        """Both polarities and their mean -- the correction the paper asks for."""
        p0 = self.polarity
        self.polarity = +1
        a = self.read()
        self.polarity = -1
        b = self.read()
        self.polarity = p0
        if isinstance(a, str) or isinstance(b, str) or a is None or b is None:
            return a, b, None
        return a, b, 0.5 * (a + b)

    def display(self):
        """Exactly the characters standing on the multimeter display."""
        if "dmm" not in self.placed or self.rng is None:
            return ""
        v = self.read()
        if v is None:
            return "- - - -"
        if isinstance(v, str):
            return v
        return ("%.2f" % v) if self.rng == 20.0 else ("%.1f" % v)

    def measure(self, sa, sb):
        """Convenience for the harness: mean of the two probe polarities."""
        self.probe_v, self.probe_c = sa, sb
        return self.read_both()[2]

    # ---------------- true eddy-current dissipation (harness only) ----------
    def true_eddy_power(self):
        sol = self.solve()
        if sol is None or not self.rod:
            return 0.0
        P = 0.0
        for name, I in zip(sol["Lnames"], sol["Il"]):
            if name == "coreA":
                P += abs(I) ** 2 * self.m.p["Ra"]
            elif name == "coreB":
                P += abs(I) ** 2 * self.m.p["Rb"]
        return P


# ============================================================================
#  screen layout of the bench  (reconstructed from the apparatus photographs)
# ============================================================================
LAYOUT = {
    "gen":      dict(x=16, y=14, w=258, h=150,
                     name=T("정현파 발생기", "Sine wave generator")),
    "coils":    dict(x=296, y=14, w=268, h=220,
                     name=T("동축 코일 조립체", "Coaxial coil assembly")),
    "dmm":      dict(x=882, y=14, w=246, h=272,
                     name=T("디지털 멀티미터", "Digital multimeter")),
    "boardA":   dict(x=16, y=252, w=690, h=82,
                     name=T("저항판  100 Ω x 10", "Resistance board  100 R x 10")),
    "boardB":   dict(x=16, y=348, w=690, h=82,
                     name=T("저항판  10 Ω x 10", "Resistance board  10 R x 10")),
    "board300": dict(x=726, y=252, w=150, h=82,
                     name=T("저항판  300 Ω", "Resistance board  300 R")),
    "rod":      dict(x=596, y=120, w=124, h=46,
                     name=T("알루미늄 봉", "Aluminium rod")),
    "wires":    dict(x=726, y=348, w=150, h=82,
                     name=T("연결선 다발", "Set of connecting wires")),
}


def socket_xy(name):
    if name == "GEN+":
        g = LAYOUT["gen"]
        return (g["x"] + 168, g["y"] + 122)
    if name == "GEN-":
        g = LAYOUT["gen"]
        return (g["x"] + 212, g["y"] + 122)
    if name in ("CB1", "CB2", "CG1", "CG2"):
        c = LAYOUT["coils"]
        dx = {"CB1": 40, "CB2": 84, "CG1": 184, "CG2": 228}[name]
        return (c["x"] + dx, c["y"] + 164)
    if name.startswith("RA"):
        i = int(name[2:])
        b = LAYOUT["boardA"]
        return (b["x"] + 30 + i * 63, b["y"] + 58)
    if name.startswith("RB"):
        i = int(name[2:])
        b = LAYOUT["boardB"]
        return (b["x"] + 30 + i * 63, b["y"] + 58)
    if name == "S0":
        b = LAYOUT["board300"]
        return (b["x"] + 34, b["y"] + 58)
    if name == "S1":
        b = LAYOUT["board300"]
        return (b["x"] + 144, b["y"] + 58)
    if name == "DMMV":
        d = LAYOUT["dmm"]
        return (d["x"] + 66, d["y"] + 244)
    if name == "DMMC":
        d = LAYOUT["dmm"]
        return (d["x"] + 156, d["y"] + 244)
    raise KeyError(name)


SOCKET_COLOR = {"GEN+": "#c0392b", "GEN-": "#222222",
                "CB1": "#2f6fb0", "CB2": "#2f6fb0",
                "CG1": "#2e8b57", "CG2": "#2e8b57",
                "S0": "#d6b656", "S1": "#d6b656",
                "DMMV": "#c0392b", "DMMC": "#222222"}


def socket_color(name):
    if name.startswith("RA") or name.startswith("RB"):
        return "#d6b656"
    return SOCKET_COLOR.get(name, "#d6b656")


# ---------------------------------------------------------------- instruments
def draw_socket(cv, name, r=8, active=False, tag="sock"):
    x, y = socket_xy(name)
    col = socket_color(name)
    cv.create_oval(x - r - 2, y - r - 2, x + r + 2, y + r + 2,
                   fill="#cfcfc8", outline="#8f8f88", tags=(tag, "s:" + name))
    cv.create_oval(x - r, y - r, x + r, y + r, fill=col,
                   outline="#3a3a3a", tags=(tag, "s:" + name))
    cv.create_oval(x - r * 0.4, y - r * 0.4, x + r * 0.4, y + r * 0.4,
                   fill="#1b1b1b", outline="", tags=(tag, "s:" + name))
    if active:
        cv.create_oval(x - r - 6, y - r - 6, x + r + 6, y + r + 6,
                       outline="#e07b00", width=3, tags=(tag,))


def draw_generator(cv):
    """The white bench-top sine generator of Fig. 2."""
    g = LAYOUT["gen"]
    x, y, w, h = g["x"], g["y"], g["w"], g["h"]
    cv.create_polygon(x, y + 34, x + w, y + 34, x + w - 16, y + 10,
                      x + 16, y + 10, fill="#e9e7de", outline="#9b988c")
    cv.create_rectangle(x, y + 34, x + w, y + h, fill="#f1efe6",
                        outline="#9b988c")
    cv.create_text(x + w / 2, y + 24, text="SINE WAVE GENERATOR",
                   font=("TkDefaultFont", 8, "bold"), fill="#3b3b3b")
    # frequency window
    cv.create_rectangle(x + 12, y + 44, x + 120, y + 74, fill="#20303c",
                        outline="#7c8790", width=2)
    cv.create_text(x + 66, y + 59, text="1.000 kHz",
                   font=("Courier", 12, "bold"), fill="#7fe0c8")
    # amplitude knob
    kx, ky = x + 40, y + 106
    cv.create_oval(kx - 22, ky - 22, kx + 22, ky + 22, fill="#3c3c3c",
                   outline="#1c1c1c", width=2)
    cv.create_oval(kx - 15, ky - 15, kx + 15, ky + 15, fill="#5a5a5a",
                   outline="#2a2a2a")
    cv.create_line(kx, ky, kx + 15, ky - 9, width=3, fill="#f2f2f2",
                   capstyle="round")
    cv.create_text(kx, ky + 32, text="AMPLITUDE",
                   font=("TkDefaultFont", 6), fill="#4a4a4a")
    # power rocker
    px, py = x + 98, y + 100
    cv.create_rectangle(px - 13, py - 15, px + 13, py + 15, fill="#c9c6ba",
                        outline="#8c887c")
    cv.create_rectangle(px - 10, py - 12, px + 10, py, fill="#7fbf6a",
                        outline="#5b8c4c")
    cv.create_rectangle(px - 10, py, px + 10, py + 12, fill="#a8a49a",
                        outline="#8c887c")
    cv.create_text(px, py + 26, text="POWER", font=("TkDefaultFont", 6),
                   fill="#4a4a4a")
    # output terminals
    ox, oy = socket_xy("GEN+")
    cv.create_rectangle(ox - 26, oy - 34, ox + 70, oy + 22, fill="#e6e3d8",
                        outline="#a09d90")
    cv.create_text(ox + 22, oy - 24, text="OUTPUT",
                   font=("TkDefaultFont", 7, "bold"), fill="#3b3b3b")
    cv.create_text(ox, oy + 17, text="+", font=("TkDefaultFont", 8, "bold"),
                   fill="#8a2b12")
    cv.create_text(socket_xy("GEN-")[0], oy + 17, text="-",
                   font=("TkDefaultFont", 9, "bold"), fill="#333333")
    cv.create_text(x + 196, y + 52,
                   text=T("출력 약 10 V rms", "output approx. 10 V rms"),
                   font=("TkDefaultFont", 7), fill="#777777")


def draw_coils(cv, rod_in):
    """
    The pair of coaxial coils of Fig. 2: two windings, one over the other, on a
    hollow non-conducting bobbin standing on a small terminal base.
    """
    c = LAYOUT["coils"]
    x, y, w, h = c["x"], c["y"], c["w"], c["h"]
    cv.create_rectangle(x, y, x + w, y + h, fill="#eef4f6", outline="#9fb3b9")
    cv.create_text(x + w / 2, y + 13, text=T("동축 코일 (하나 위에 다른 하나)",
                                             "coaxial coils, one over the other"),
                   font=("TkDefaultFont", 7), fill="#7d8f95")
    cx, cy = x + w / 2, y + 78
    L, RY = 74.0, 40.0            # half length and outer radius of the winding
    # ---- bobbin end flanges (white plastic)
    for sx in (-1, 1):
        cv.create_oval(cx + sx * (L + 12) - 9, cy - RY - 8,
                       cx + sx * (L + 12) + 9, cy + RY + 8,
                       fill="#f0efe9", outline="#a9a79c")
    # ---- inner winding, visible just inside the flanges
    cv.create_rectangle(cx - L - 6, cy - 27, cx + L + 6, cy + 27,
                        fill="#c98b3a", outline="#8d6a3a")
    for i in range(int((2 * L + 12) / 5.0)):
        xx = cx - L - 6 + i * 5.0
        cv.create_line(xx, cy - 26, xx + 3, cy + 26, fill="#8f5e22", width=2)
    # ---- outer winding over the middle
    cv.create_rectangle(cx - L, cy - RY, cx + L, cy + RY,
                        fill="#d99a4e", outline="#a3722b")
    for i in range(int(2 * L / 5.6)):
        xx = cx - L + i * 5.6
        cv.create_line(xx, cy - RY + 1, xx + 3.4, cy + RY - 1,
                       fill="#b8762b", width=3)
    cv.create_line(cx - L, cy - RY * 0.55, cx + L, cy - RY * 0.55,
                   fill="#f0c890", width=2)
    # ---- the bore, seen on the near end face
    ex = cx + L + 12
    cv.create_oval(ex - 9, cy - 15, ex + 9, cy + 15,
                   fill="#b9bec6" if rod_in else "#20211f", outline="#7d838b")
    if rod_in:
        cv.create_rectangle(ex, cy - 13, ex + 54, cy + 13, fill="#c3c8d0",
                            outline="#8f959d")
        cv.create_oval(ex + 45, cy - 13, ex + 63, cy + 13, fill="#dfe3e9",
                       outline="#8f959d")
        cv.create_line(ex + 6, cy - 6, ex + 50, cy - 6, fill="#e2e6ec")
        cv.create_text(ex + 30, cy + 26, text="Al",
                       font=("TkDefaultFont", 8, "bold"), fill="#5a5a5a")
    # ---- terminal base
    b1 = socket_xy("CB1")
    cv.create_rectangle(x + 18, b1[1] - 15, x + w - 18, b1[1] + 15,
                        fill="#e4e8ea", outline="#a2b0b5")
    for a, bb, col in (("CB1", "CB2", "#2f6fb0"), ("CG1", "CG2", "#2e8b57")):
        xa, ya = socket_xy(a)
        xb, yb = socket_xy(bb)
        cv.create_line(xa, ya - 14, xa, cy + RY - 4, fill=col, width=2)
        cv.create_line(xb, yb - 14, xb, cy + RY - 4, fill=col, width=2)


def draw_dmm(cv, text, rng, probe_v, probe_c):
    """The yellow hand-held DMM of Fig. 2, used on its ac voltage ranges."""
    d = LAYOUT["dmm"]
    x, y, w, h = d["x"], d["y"], d["w"], d["h"]
    cv.create_rectangle(x, y, x + w, y + h, fill="#e8c220", outline="#9c8410",
                        width=2)
    cv.create_rectangle(x + 6, y + 6, x + w - 6, y + h - 6, outline="#c8a713")
    cv.create_rectangle(x + 18, y + 16, x + w - 18, y + 76, fill="#c8d6c0",
                        outline="#6f7d68", width=2)
    cv.create_text(x + w / 2 + 8, y + 42, text=text,
                   font=("Courier", 25, "bold"), fill="#1d2a1a")
    cv.create_text(x + w - 26, y + 66, text="AC V", anchor="e",
                   font=("TkDefaultFont", 8), fill="#33402f")
    cv.create_text(x + 26, y + 66, text="rms", anchor="w",
                   font=("TkDefaultFont", 7), fill="#556150")
    # ---- rotary function selector
    cxp, cyp = x + w / 2, y + 152
    cv.create_oval(cxp - 54, cyp - 54, cxp + 54, cyp + 54, fill="#f2df8c",
                   outline="#b39a12")
    cv.create_oval(cxp - 40, cyp - 40, cxp + 40, cyp + 40, fill="#2b2b2b",
                   outline="#111111")
    for ang, lab in ((150.0, "OFF"), (90.0, "V~20"), (30.0, "V~200")):
        a = math.radians(ang)
        cv.create_text(cxp + 68 * math.cos(a), cyp - 68 * math.sin(a),
                       text=lab, font=("TkDefaultFont", 7, "bold"),
                       fill="#4a3f08")
        cv.create_line(cxp + 44 * math.cos(a), cyp - 44 * math.sin(a),
                       cxp + 52 * math.cos(a), cyp - 52 * math.sin(a),
                       fill="#7a6708", width=2)
    a = math.radians({None: 150.0, 20.0: 90.0, 200.0: 30.0}[rng])
    cv.create_line(cxp, cyp, cxp + 34 * math.cos(a), cyp - 34 * math.sin(a),
                   width=6, fill="#f4f4f4", capstyle="round")
    cv.create_oval(cxp - 9, cyp - 9, cxp + 9, cyp + 9, fill="#8a8a8a",
                   outline="#111111")
    # ---- input jacks
    vx, vy = socket_xy("DMMV")
    ux, uy = socket_xy("DMMC")
    cv.create_text(vx, vy - 19, text="V/Ω", font=("TkDefaultFont", 7, "bold"),
                   fill="#4a3f08")
    cv.create_text(ux, uy - 19, text="COM", font=("TkDefaultFont", 7, "bold"),
                   fill="#4a3f08")
    cv.create_text(x + w / 2, y + h - 10,
                   text=T("±(1.0 % rdg + 4 dgt)", "+-(1.0 % rdg + 4 dgt)"),
                   font=("TkDefaultFont", 6), fill="#6a5a08")


def draw_board(cv, key, n, value, label):
    b = LAYOUT[key]
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    cv.create_rectangle(x, y, x + w, y + h, fill="#eef2f4", outline="#9fb3b9")
    cv.create_text(x + 8, y + 12, anchor="w", text=label,
                   font=("TkDefaultFont", 8, "bold"), fill="#43555c")
    pre = "RA" if key == "boardA" else ("RB" if key == "boardB" else "S")
    for i in range(n):
        a = socket_xy("%s%d" % (pre, i))
        bb = socket_xy("%s%d" % (pre, i + 1))
        mx = 0.5 * (a[0] + bb[0])
        cv.create_line(a[0], a[1] - 22, mx - 16, a[1] - 22, fill="#7a7a7a", width=2)
        cv.create_line(mx + 16, a[1] - 22, bb[0], bb[1] - 22, fill="#7a7a7a",
                       width=2)
        cv.create_line(a[0], a[1] - 22, a[0], a[1] - 8, fill="#7a7a7a", width=2)
        cv.create_line(bb[0], bb[1] - 22, bb[0], bb[1] - 8, fill="#7a7a7a", width=2)
        cv.create_rectangle(mx - 16, a[1] - 30, mx + 16, a[1] - 14,
                            fill="#d8cba8", outline="#8d8360")
        for j, col in enumerate(("#8b4513", "#000000", "#b22222")):
            cv.create_line(mx - 10 + j * 7, a[1] - 29, mx - 10 + j * 7, a[1] - 15,
                           fill=col, width=2)
        cv.create_text(mx, a[1] + 16, text=value,
                       font=("TkDefaultFont", 7), fill="#3d3d3d")


def draw_rod_part(cv):
    r = LAYOUT["rod"]
    x, y, w, h = r["x"], r["y"], r["w"], r["h"]
    cv.create_rectangle(x + 10, y + 12, x + w - 10, y + h - 12, fill="#c3c8d0",
                        outline="#8f959d")
    cv.create_oval(x + w - 22, y + 12, x + w - 2, y + h - 12, fill="#dfe3e9",
                   outline="#8f959d")
    cv.create_oval(x + 2, y + 12, x + 22, y + h - 12, fill="#aeb3ba",
                   outline="#8f959d")


def draw_wire_bundle(cv):
    b = LAYOUT["wires"]
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    cv.create_rectangle(x, y, x + w, y + h, fill="#f4f2ea", outline="#b0aa98")
    cv.create_text(x + w / 2, y + 14, text=T("연결선 (적 5, 흑 5)",
                                             "wires (5 red, 5 black)"),
                   font=("TkDefaultFont", 7), fill="#5c5647")
    for i in range(5):
        cv.create_arc(x + 14, y + 24 + i * 4, x + w - 14, y + 66 + i * 4,
                      start=200, extent=140, style="arc",
                      outline="#c0392b" if i % 2 == 0 else "#222222", width=3)


# ============================================================================
#  the parts tray
# ============================================================================
def parts_catalogue():
    return [
        dict(key="gen", zone="gen",
             name=T("정현파 발생기", "Sine wave generator"),
             note=T("1000 Hz, 약 10 V rms", "1000 Hz, about 10 V rms")),
        dict(key="dmm", zone="dmm",
             name=T("디지털 멀티미터", "Digital multimeter"),
             note=T("교류 전압계로 사용", "used as an ac voltmeter")),
        dict(key="coils", zone="coils",
             name=T("동축 코일 조립체", "Coaxial coils"),
             note=T("청색 = 코일 1, 녹색 = 코일 2",
                    "blue = coil 1, green = coil 2")),
        dict(key="boardA", zone="boardA",
             name=T("저항판 100 Ω x 10", "Board, 100 R x 10"),
             note=T("직렬 저항 10 개", "ten resistors in series")),
        dict(key="boardB", zone="boardB",
             name=T("저항판 10 Ω x 10", "Board, 10 R x 10"),
             note=T("직렬 저항 10 개", "ten resistors in series")),
        dict(key="board300", zone="board300",
             name=T("저항판 300 Ω", "Board, 300 R"),
             note=T("표본 저항용", "for use as sampling resistor")),
        dict(key="wires", zone="wires",
             name=T("연결선 한 벌", "Set of connecting wires"),
             note=T("적 5, 흑 5 + 긴 프로브 한 쌍",
                    "5 red, 5 black + long probe pair")),
        dict(key="rod", zone="coils",
             name=T("알루미늄 봉", "Aluminium rod"),
             note=T("코일 보빈 속에 끼운다", "slides inside the coil bobbin")),
    ]


MAX_WIRES = 10          # five red and five black pieces


def zone_boxes(dy=0):
    out = {}
    for k, b in LAYOUT.items():
        out[k] = (b["x"], b["y"] + dy, b["x"] + b["w"], b["y"] + b["h"] + dy)
    return out


def draw_bench(cv, rig, active=None, tag="bench"):
    """Draw every installed instrument, the wiring and the probes."""
    n0 = len(cv.find_all())
    if "gen" in rig.placed:
        draw_generator(cv)
    if "coils" in rig.placed:
        draw_coils(cv, rig.rod)
    if "boardA" in rig.placed:
        draw_board(cv, "boardA", BOARD_A_N, "100 " + u"\u03a9",
                   LAYOUT["boardA"]["name"])
    if "boardB" in rig.placed:
        draw_board(cv, "boardB", BOARD_B_N, "10 " + u"\u03a9",
                   LAYOUT["boardB"]["name"])
    if "board300" in rig.placed:
        draw_board(cv, "board300", 1, "300 " + u"\u03a9",
                   LAYOUT["board300"]["name"])
    if "wires" in rig.placed:
        draw_wire_bundle(cv)
    # ---- wire pieces
    for i, (a, b) in enumerate(rig.wires):
        try:
            xa, ya = socket_xy(a)
            xb, yb = socket_xy(b)
        except KeyError:
            continue
        col = "#c0392b" if i % 2 == 0 else "#1c1c1c"
        mx, my = 0.5 * (xa + xb), 0.5 * (ya + yb) + 26 + 6 * (i % 3)
        cv.create_line(xa, ya, mx, my, xb, yb, smooth=True, width=4,
                       fill=col, capstyle="round", tags=("wire", "w:%d" % i))
    # ---- dmm last, so its probes sit on top
    if "dmm" in rig.placed:
        draw_dmm(cv, rig.display(), rig.rng, rig.probe_v, rig.probe_c)
        for sock, hub, col in ((rig.probe_v, "DMMV", "#c0392b"),
                               (rig.probe_c, "DMMC", "#1c1c1c")):
            if not sock:
                continue
            try:
                xs, ys = socket_xy(sock)
            except KeyError:
                continue
            xh, yh = socket_xy(hub)
            cv.create_line(xh, yh, 0.5 * (xh + xs), 0.5 * (yh + ys) + 36,
                           xs, ys, smooth=True, width=5, fill=col,
                           capstyle="round")
            cv.create_polygon(xs - 5, ys - 14, xs + 5, ys - 14, xs, ys,
                              fill=col, outline="#111111")
    if "coils" in rig.placed:
        c, yb = LAYOUT["coils"], socket_xy("CB1")[1]
        for dx, txt, col in ((62, T("코일 1 (청색)", "coil 1 (blue)"), "#2f6fb0"),
                             (206, T("코일 2 (녹색)", "coil 2 (green)"), "#2e8b57")):
            cv.create_rectangle(c["x"] + dx - 42, yb + 21, c["x"] + dx + 42,
                                yb + 39, fill="#e4e8ea", outline="")
            cv.create_text(c["x"] + dx, yb + 30, text=txt,
                           font=("TkDefaultFont", 7, "bold"), fill=col)
    for s in sockets_of(rig.placed):
        draw_socket(cv, s, active=(s == active))
    for it in cv.find_all()[n0:]:
        cv.addtag_withtag(tag, it)


# ============================================================================
#  assembly tab -- put the instruments on the bench
# ============================================================================
class AssemblyTab(ttk.Frame):
    TRAY_H = 116

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.parts = parts_catalogue()
        self.drag = None
        self.dxy = (0, 0)

        ttk.Label(self, font=("TkDefaultFont", 10, "bold"),
                  text=T("위쪽 부품 보관대에서 기구를 끌어다 실험대의 알맞은 자리에 "
                         "놓으세요.  놓인 기구를 오른쪽 클릭하면 치웁니다.",
                         "Drag an instrument from the tray onto its place on the "
                         "bench.  Right-click an instrument to take it away.")
                  ).pack(anchor="w", padx=10, pady=(8, 2))
        self.cv = tk.Canvas(self, width=1150, height=self.TRAY_H + 448,
                            bg="#f2efe6", highlightthickness=0)
        self.cv.pack(padx=8, pady=2)
        self.msg = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.msg,
                  foreground="#8a2b12").pack(anchor="w", padx=12)
        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_move)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Button-3>", self.on_right)
        self.redraw()

    # ---------------- tray geometry ----------------
    def tray_slots(self):
        out, w = [], 1150 // len(self.parts)
        for i, p in enumerate(self.parts):
            out.append((p, 4 + i * w, 26, 4 + i * w + w - 8, 26 + 82))
        return out

    def placed(self, key):
        if key == "rod":
            return self.app.rig.rod
        return key in self.app.rig.placed

    # ---------------- drawing ----------------
    def redraw(self):
        cv, rig = self.cv, self.app.rig
        cv.delete("all")
        cv.create_rectangle(0, 0, 1150, self.TRAY_H - 4, fill="#e7e2d2",
                            outline="#c9c2b0")
        cv.create_text(10, 12, anchor="w", text=T("부품 보관대", "Parts tray"),
                       font=("TkDefaultFont", 10, "bold"), fill="#5a5344")
        for p, x0, y0, x1, y1 in self.tray_slots():
            done = self.placed(p["key"])
            cv.create_rectangle(x0, y0, x1, y1,
                                fill="#dfe6d6" if done else "#ffffff",
                                outline="#9aa39a")
            self.part_icon(cv, p["key"], (x0 + x1) / 2, y0 + 26)
            cv.create_text((x0 + x1) / 2, y0 + 52, text=p["name"],
                           font=("TkDefaultFont", 8, "bold"), width=x1 - x0 - 8,
                           fill="#4b6b3a" if done else "#222222")
            cv.create_text((x0 + x1) / 2, y0 + 70, text=p["note"],
                           font=("TkDefaultFont", 6), width=x1 - x0 - 8,
                           fill="#666666")
            if done:
                cv.create_text(x1 - 10, y0 + 8, text="OK",
                               font=("TkDefaultFont", 7, "bold"), fill="#3f7a2a")
        # ---- bench surface with the empty places outlined
        cv.create_rectangle(0, self.TRAY_H, 1150, self.TRAY_H + 446,
                            fill="#efece2", outline="")
        for i in range(7):
            cv.create_line(0, self.TRAY_H + 8 + i * 64, 1150,
                           self.TRAY_H + 8 + i * 64, fill="#e6e2d6")
        boxes = zone_boxes(self.TRAY_H)
        for key, (x0, y0, x1, y1) in boxes.items():
            if key == "rod":
                continue
            if key in rig.placed:
                continue
            cv.create_rectangle(x0, y0, x1, y1, dash=(5, 4), outline="#8fa6c0")
            cv.create_text((x0 + x1) / 2, (y0 + y1) / 2,
                           text=LAYOUT[key]["name"], fill="#7d93ad",
                           font=("TkDefaultFont", 8), width=x1 - x0 - 12)
        draw_bench(cv, rig, tag="bench")
        cv.move("bench", 0, self.TRAY_H)
        if self.drag is not None:
            self.draw_ghost()

    def draw_ghost(self):
        x, y = self.dxy
        self.part_icon(self.cv, self.drag["key"], x, y, ghost=True)
        boxes = zone_boxes(self.TRAY_H)
        x0, y0, x1, y1 = boxes[self.drag["zone"]]
        self.cv.create_rectangle(x0, y0, x1, y1, dash=(3, 3), width=2,
                                 outline="#2f6fb0")

    def part_icon(self, cv, key, cx, cy, ghost=False):
        s = 17
        out = "#2f6fb0" if ghost else "#555555"
        if key == "gen":
            cv.create_rectangle(cx - s, cy - s * .6, cx + s, cy + s * .6,
                                fill="#f1efe6", outline=out)
            cv.create_arc(cx - s * .7, cy - s * .35, cx, cy + s * .35,
                          start=0, extent=180, style="arc", outline="#28527a")
            cv.create_arc(cx, cy - s * .35, cx + s * .7, cy + s * .35,
                          start=180, extent=180, style="arc", outline="#28527a")
        elif key == "dmm":
            cv.create_rectangle(cx - s * .75, cy - s * .8, cx + s * .75, cy + s * .8,
                                fill="#e8c220", outline=out)
            cv.create_rectangle(cx - s * .55, cy - s * .6, cx + s * .55, cy - s * .1,
                                fill="#c8d6c0", outline="#6f7d68")
            cv.create_oval(cx - s * .3, cy + s * .1, cx + s * .3, cy + s * .65,
                           fill="#2b2b2b", outline="")
        elif key == "coils":
            cv.create_rectangle(cx - s * .9, cy - s * .55, cx + s * .9, cy + s * .55,
                                fill="#d9cbb0", outline=out)
            for i in range(6):
                cv.create_line(cx - s * .8 + i * s * .32, cy - s * .5,
                               cx - s * .65 + i * s * .32, cy + s * .5,
                               fill="#b8762b", width=2)
            cv.create_oval(cx - s * .25, cy - s * .2, cx + s * .25, cy + s * .2,
                           fill="#2c2c2c", outline="")
        elif key in ("boardA", "boardB", "board300"):
            cv.create_rectangle(cx - s, cy - s * .45, cx + s, cy + s * .45,
                                fill="#eef2f4", outline=out)
            n = 2 if key == "board300" else 4
            for i in range(n):
                cv.create_oval(cx - s * .8 + i * (1.6 * s / max(n - 1, 1)) - 2.5,
                               cy + s * .1, cx - s * .8 + i * (1.6 * s / max(n - 1, 1)) + 2.5,
                               cy + s * .35, fill="#d6b656", outline="#8d8360")
            cv.create_rectangle(cx - s * .5, cy - s * .3, cx + s * .5, cy - s * .05,
                                fill="#d8cba8", outline="#8d8360")
        elif key == "wires":
            for i in range(4):
                cv.create_arc(cx - s, cy - s * .5 + i * 3, cx + s, cy + s * .5 + i * 3,
                              start=200, extent=140, style="arc", width=3,
                              outline="#c0392b" if i % 2 == 0 else "#1c1c1c")
        elif key == "rod":
            cv.create_rectangle(cx - s * .9, cy - s * .3, cx + s * .9, cy + s * .3,
                                fill="#c3c8d0", outline=out)
            cv.create_oval(cx + s * .6, cy - s * .3, cx + s * 1.05, cy + s * .3,
                           fill="#dfe3e9", outline="#8f959d")

    # ---------------- mouse ----------------
    def on_press(self, ev):
        for p, x0, y0, x1, y1 in self.tray_slots():
            if x0 <= ev.x <= x1 and y0 <= ev.y <= y1:
                if self.placed(p["key"]):
                    self.msg.set(T("이미 실험대에 놓여 있습니다.",
                                   "It is already on the bench."))
                    return
                self.drag = p
                self.dxy = (ev.x, ev.y)
                self.redraw()
                return

    def on_move(self, ev):
        if self.drag is not None:
            self.dxy = (ev.x, ev.y)
            self.redraw()

    def on_release(self, ev):
        if self.drag is None:
            return
        p, self.drag = self.drag, None
        x0, y0, x1, y1 = zone_boxes(self.TRAY_H)[p["zone"]]
        if not (x0 - 24 <= ev.x <= x1 + 24 and y0 - 24 <= ev.y <= y1 + 24):
            self.msg.set(T("그 자리는 이 기구의 자리가 아닙니다.",
                           "That is not the place for this instrument."))
            self.redraw()
            return
        ok, why = self.app.install(p["key"])
        self.redraw()
        self.msg.set(why)
        self.app.tab_bench.refresh()

    def on_right(self, ev):
        boxes = zone_boxes(self.TRAY_H)
        rig = self.app.rig
        if rig.rod:
            x0, y0, x1, y1 = boxes["coils"]
            if x0 <= ev.x <= x1 and y0 <= ev.y <= y1:
                ok, why = self.app.remove("rod")
                self.redraw()
                self.msg.set(why)
                self.app.tab_bench.refresh()
                return
        for key, (x0, y0, x1, y1) in boxes.items():
            if key == "rod" or key not in rig.placed:
                continue
            if x0 <= ev.x <= x1 and y0 <= ev.y <= y1:
                ok, why = self.app.remove(key)
                self.redraw()
                self.msg.set(why)
                self.app.tab_bench.refresh()
                return


# ============================================================================
#  bench tab -- wire the circuit up and read the multimeter
# ============================================================================
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.pending = None            # first socket of a wire being laid
        self.mode = tk.StringVar(value="wire")

        head = ttk.Frame(self)
        head.pack(fill="x", padx=10, pady=(6, 0))
        ttk.Label(head, font=("TkDefaultFont", 10, "bold"),
                  text=T("소켓을 두 번 눌러 연결선을 꽂습니다.  연결선을 누르면 "
                         "뽑힙니다.",
                         "Click two sockets to plug a wire in.  Click a wire to "
                         "pull it out.")).pack(side="left")
        for val, txt in (("wire", T("연결선", "wire piece")),
                         ("probe_v", T("적색 프로브 (V/Ω)", "red probe (V/Ohm)")),
                         ("probe_c", T("흑색 프로브 (COM)", "black probe (COM)"))):
            ttk.Radiobutton(head, text=txt, value=val,
                            variable=self.mode,
                            command=self.cancel_pending).pack(side="right", padx=4)

        self.cv = tk.Canvas(self, width=1150, height=446, bg="#efece2",
                            highlightthickness=0)
        self.cv.pack(padx=8, pady=4)
        self.cv.bind("<Button-1>", self.on_click)

        bot = ttk.Frame(self)
        bot.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        gbox = ttk.LabelFrame(bot, text=T("발생기", "Generator"))
        gbox.grid(row=0, column=0, sticky="nsw", padx=(2, 8))
        self.pwr = tk.IntVar(value=1)
        ttk.Checkbutton(gbox, text=T("전원", "POWER"), variable=self.pwr,
                        command=self.on_power).grid(row=0, column=0, sticky="w",
                                                    padx=6, pady=2)
        ttk.Label(gbox, text=T("진폭 손잡이", "amplitude knob")).grid(
            row=1, column=0, sticky="w", padx=6)
        self.amp = tk.DoubleVar(value=100.0)
        ttk.Scale(gbox, from_=20.0, to=100.0, orient="horizontal",
                  variable=self.amp, length=150,
                  command=lambda *_: self.on_amp()).grid(row=2, column=0,
                                                         padx=6, pady=(0, 2))
        self.amplbl = tk.StringVar(value="100 %")
        ttk.Label(gbox, textvariable=self.amplbl,
                  font=("TkDefaultFont", 8)).grid(row=3, column=0, sticky="w",
                                                  padx=6, pady=(0, 4))

        dbox = ttk.LabelFrame(bot, text=T("멀티미터", "Multimeter"))
        dbox.grid(row=0, column=1, sticky="nsw", padx=(0, 8))
        self.rngv = tk.StringVar(value="20")
        for i, (v, txt) in enumerate((("off", "OFF"), ("20", "V~ 20"),
                                      ("200", "V~ 200"))):
            ttk.Radiobutton(dbox, text=txt, value=v, variable=self.rngv,
                            command=self.on_range).grid(row=i, column=0,
                                                        sticky="w", padx=6)
        ttk.Button(dbox, text=T("프로브 극성 바꿈", "interchange probes"),
                   command=self.swap).grid(row=3, column=0, padx=6, pady=(4, 4))

        abox = ttk.LabelFrame(bot, text=T("조작", "Actions"))
        abox.grid(row=0, column=2, sticky="nsw", padx=(0, 8))
        self.rodbtn = ttk.Button(abox, text="", command=self.toggle_rod)
        self.rodbtn.grid(row=0, column=0, sticky="ew", padx=6, pady=2)
        ttk.Button(abox, text=T("연결선 모두 뽑기", "pull out all wires"),
                   command=self.clear_wires).grid(row=1, column=0, sticky="ew",
                                                  padx=6, pady=2)
        ttk.Button(abox, text=T("프로브 떼기", "lift the probes"),
                   command=self.clear_probes).grid(row=2, column=0, sticky="ew",
                                                   padx=6, pady=2)
        ttk.Button(abox, text=T("눈금 기록", "record the reading"),
                   command=self.record).grid(row=3, column=0, sticky="ew",
                                             padx=6, pady=(6, 2))

        lbox = ttk.LabelFrame(bot, text=T("실험 기록", "Laboratory notebook"))
        lbox.grid(row=0, column=3, sticky="nsew")
        bot.columnconfigure(3, weight=1)
        bot.rowconfigure(0, weight=1)
        self.log = tk.Listbox(lbox, height=8, font=("Courier", 9))
        sb = ttk.Scrollbar(lbox, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.status = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status,
                  foreground="#8a2b12").pack(anchor="w", padx=12)
        self.refresh()
        self.tick()

    # ---------------- helpers ----------------
    def cancel_pending(self):
        self.pending = None
        self.refresh()

    def nearest_socket(self, x, y, rmax=15.0):
        best, bd = None, rmax
        for s in sockets_of(self.app.rig.placed):
            sx, sy = socket_xy(s)
            d = math.hypot(sx - x, sy - y)
            if d < bd:
                best, bd = s, d
        return best

    def hit_wire(self, x, y, rmax=8.0):
        for i, (a, b) in enumerate(self.app.rig.wires):
            try:
                xa, ya = socket_xy(a)
                xb, yb = socket_xy(b)
            except KeyError:
                continue
            mx, my = 0.5 * (xa + xb), 0.5 * (ya + yb) + 26 + 6 * (i % 3)
            for t in range(21):
                u = t / 20.0
                px = (1 - u) ** 2 * xa + 2 * (1 - u) * u * mx + u * u * xb
                py = (1 - u) ** 2 * ya + 2 * (1 - u) * u * my + u * u * yb
                if math.hypot(px - x, py - y) < rmax:
                    return i
        return None

    # ---------------- mouse ----------------
    def on_click(self, ev):
        rig = self.app.rig
        s = self.nearest_socket(ev.x, ev.y)
        if s is None:
            i = self.hit_wire(ev.x, ev.y)
            if i is not None:
                rig.wires.pop(i)
                self.status.set(T("연결선을 뽑았습니다.", "Wire pulled out."))
                self.refresh()
            else:
                self.cancel_pending()
            return
        mode = self.mode.get()
        if mode == "probe_v":
            rig.probe_v = s
            self.status.set("")
        elif mode == "probe_c":
            rig.probe_c = s
            self.status.set("")
        else:
            if "wires" not in rig.placed:
                self.status.set(T("연결선이 실험대에 없습니다. 조립 탭에서 가져오세요.",
                                  "There are no wires on the bench -- fetch them "
                                  "in the assembly tab."))
                self.refresh()
                return
            if self.pending is None:
                self.pending = s
                self.status.set("")
            elif self.pending == s:
                self.pending = None
            else:
                pair = (self.pending, s)
                rev = (s, self.pending)
                if pair in rig.wires or rev in rig.wires:
                    self.status.set(T("이미 그 두 소켓은 연결되어 있습니다.",
                                      "Those two sockets are already joined."))
                elif len(rig.wires) >= MAX_WIRES:
                    self.status.set(T("연결선을 모두 썼습니다 (적 5, 흑 5).",
                                      "All ten wire pieces are in use."))
                else:
                    rig.wires.append(pair)
                    self.status.set("")
                self.pending = None
        self.refresh()

    # ---------------- controls ----------------
    def on_power(self):
        self.app.rig.power = bool(self.pwr.get())
        self.refresh()

    def on_amp(self):
        self.app.rig.amp = self.amp.get() / 100.0
        self.amplbl.set("%.0f %%" % self.amp.get())
        self.refresh()

    def on_range(self):
        v = self.rngv.get()
        self.app.rig.rng = None if v == "off" else float(v)
        self.refresh()

    def swap(self):
        rig = self.app.rig
        rig.probe_v, rig.probe_c = rig.probe_c, rig.probe_v
        rig.polarity = -rig.polarity
        self.refresh()

    def toggle_rod(self):
        ok, why = (self.app.remove("rod") if self.app.rig.rod
                   else self.app.install("rod"))
        self.status.set(why)
        self.refresh()
        self.app.tab_asm.redraw()

    def clear_wires(self):
        self.app.rig.wires = []
        self.pending = None
        self.refresh()

    def clear_probes(self):
        self.app.rig.probe_v = None
        self.app.rig.probe_c = None
        self.refresh()

    def record(self):
        rig = self.app.rig
        txt = rig.display()
        if not rig.probe_v or not rig.probe_c:
            self.status.set(T("프로브를 두 소켓에 대세요.",
                              "Put both probes on sockets."))
            return
        pol = "+" if rig.polarity > 0 else "-"
        self.log.insert("end", " %-6s %-6s  %s  %s"
                        % (rig.probe_v, rig.probe_c, pol, txt))
        self.log.see("end")

    # ---------------- drawing ----------------
    def refresh(self):
        rig = self.app.rig
        self.rodbtn.configure(
            text=T("알루미늄 봉 빼기", "take the Al rod out") if rig.rod
            else T("알루미늄 봉 넣기", "put the Al rod in"))
        self.cv.delete("all")
        for i in range(7):
            self.cv.create_line(0, 8 + i * 64, 1150, 8 + i * 64, fill="#e6e2d6")
        if not rig.placed:
            self.cv.create_text(575, 215, text=T("조립 탭에서 기구를 실험대에 "
                                                 "놓으세요.",
                                                 "Place the instruments on the "
                                                 "bench in the assembly tab."),
                                font=("TkDefaultFont", 12), fill="#8d8878")
            return
        draw_bench(self.cv, rig, active=self.pending, tag="bench")

    def tick(self):
        """The multimeter display flickers in its last digit, like a real one."""
        if self.app.rig.rng is not None and "dmm" in self.app.rig.placed:
            self.refresh()
        self.after(800, self.tick)


# ============================================================================
class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.title(T("APhO 2012 실험 2 - 전자기 유도 (HaslaLab)",
                     "APhO 2012 Experiment 2 - Electromagnetic induction "
                     "(HaslaLab)"))
        self.model = Model(seed)
        self.rig = Rig(self.model)
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.tab_asm = AssemblyTab(self.nb, self)
        self.tab_bench = BenchTab(self.nb, self)
        self.nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        self.nb.add(self.tab_bench, text=T(" 실험대 ", " Bench "))
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.sync())
        bar = ttk.Frame(self)
        bar.pack(fill="x")
        ttk.Label(bar, text="APhO 2012 - Q2 ELECTROMAGNETIC INDUCTION     "
                            "seed = %d" % self.model.seed,
                  font=("TkDefaultFont", 8),
                  foreground="#777777").pack(side="right", padx=8, pady=2)

    def sync(self):
        self.tab_asm.redraw()
        self.tab_bench.refresh()

    # ---------------- installation rules ----------------
    def install(self, key):
        rig = self.rig
        if key == "rod":
            if "coils" not in rig.placed:
                return False, T("먼저 코일 조립체를 실험대에 놓으세요.",
                                "Put the coil assembly on the bench first.")
            if rig.rod:
                return False, T("봉이 이미 보빈 속에 있습니다.",
                                "The rod is already inside the bobbin.")
            rig.placed.add("rod")
            rig.rod = True
            return True, ""
        if key in rig.placed:
            return False, T("이미 놓여 있습니다.", "Already on the bench.")
        rig.placed.add(key)
        return True, ""

    def remove(self, key):
        rig = self.rig
        if key == "rod":
            rig.rod = False
            rig.placed.discard("rod")
            return True, T("알루미늄 봉을 빼냈습니다.", "The Al rod is out.")
        if key not in rig.placed:
            return False, ""
        socks = set(sockets_of({key}))
        if any(a in socks or b in socks for a, b in rig.wires):
            return False, T("그 기구에 꽂힌 연결선을 먼저 뽑으세요.",
                            "Pull out the wires plugged into it first.")
        if key == "coils" and rig.rod:
            rig.rod = False
            rig.placed.discard("rod")
        if key == "wires" and rig.wires:
            return False, T("꽂혀 있는 연결선을 먼저 뽑으세요.",
                            "Pull out the wires that are plugged in first.")
        if rig.probe_v in socks:
            rig.probe_v = None
        if rig.probe_c in socks:
            rig.probe_c = None
        rig.placed.discard(key)
        return True, T("기구를 치웠습니다.", "Instrument taken away.")


def main():
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
    App(seed).mainloop()


if __name__ == "__main__":
    main()
