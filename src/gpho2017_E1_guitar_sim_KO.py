#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  2nd Gulf Physics Olympiad  (GPhO 2017, Riyadh, Saudi Arabia)
  Experimental Problem E1 :  ELECTRIC GUITAR
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The apparatus of the problem sheet: the stand with its steel guitar
    string over two saddles (the first on a piezo pickup, amplified to
    S+ / S-), the screw tensioner with its knob under the bar, the 5 V
    USB supply between A and the string, a set of seven resistors, the
    AX-100 (3 1/2 digits, manual ranges) and the AX-MS811 (4000 counts,
    autoranging, frequency) multimeters, nine test leads, a 1 m
    measuring tape and the photo of the string magnified 100x.
    Only what a real instrument shows is displayed: the two meters'
    digits, the tape's marks, the knob's white mark.  No length,
    tension, frequency, resistance or temperature is ever computed for
    you.  The string's hidden values (diameter, resistivity, Young's
    modulus, expansion coefficient, initial stretch) are randomised for
    each session; --seed N repeats a session.

    Run:   python3 gpho2017_E1_guitar_sim_KO.py   [--seed N]
"""
import math
import random
import time
import sys
import tkinter as tk
from tkinter import ttk

APP_VERSION = "1.0"
LANG = "KO"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "KO" else en


# ==============================================================================
#  1.  참값  (학생에게는 절대 노출되지 않음)
# ==============================================================================
SEED = None
for i, a in enumerate(sys.argv):
    if a == "--seed" and i + 1 < len(sys.argv):
        SEED = int(sys.argv[i + 1])
RNG = random.Random(SEED)


def gauss():
    return RNG.gauss(0.0, 1.0)


BASE_Y = 4.0                       # cm, 막대 윗면
GEO = {"E0": (8.0, BASE_Y + 0.9), "S1": (11.0, BASE_Y + 2.2), "S2": (61.4, BASE_Y + 2.2),
       "P1": (63.3, BASE_Y + 1.3), "TP": (67.6, BASE_Y + 1.3), "P2": (71.5, BASE_Y + 1.3),
       "E1": (74.9, BASE_Y + 0.5)}
TRUE = {
    "d": 0.195e-3 * (1 + 0.012 * gauss()),       # m
    "rho": 1.89e-7 * (1 + 0.02 * gauss()),       # Ohm m (실온)
    "beta": 0.0020, "Lam": 0.247e-3,            # 1/K, kg/m (문제지 제공값)
    "E": 1.85e11 * (1 + 0.03 * gauss()),         # Pa
    "alpha": 1.12e-5 * (1 + 0.04 * gauss()),     # 1/K
    "slack": 1.25 + 0.15 * gauss(),              # mm, 나사를 끝까지 내렸을 때 이미 늘어난 길이
    "T0": 20.0 + 0.4 * gauss(),                  # C
    "g": 0.037, "c": 460.0, "Rint": 0.16,        # W/(m K), J/(kg K), Ohm
}
TRUE["A"] = math.pi * TRUE["d"] ** 2 / 4
RNOM = [0.1, 1, 3, 10, 30, 100, 1000]
TRUE["R"] = [r * (1 + 0.025 * gauss()) for r in RNOM]
H1 = 0.70                           # mm / 1 회전  (문제지 제공값)
CAL = {"ax": (gauss() * 0.15, gauss()), "ms": (gauss() * 0.2, gauss())}

AX100_DIAL = ["OFF", "DCV 200m", "DCV 2", "DCV 20", "DCV 200", "DCV 600", "ACV 600", "ACV 200",
              "DCA 20µ", "DCA 200µ", "DCA 2m", "DCA 20m", "DCA 200m", "DCA 10", "→|",
              "Ω 200", "Ω 2k", "Ω 20k", "Ω 200k", "Ω 20M"]
AX_LBL = ["OFF", "200mV", "2V", "20V", "200V", "600V", "600V", "200V", "20µA", "200µA", "2mA", "20mA",
          "200mA", "10A", "→|", "200", "2k", "20k", "200k", "20M"]
MS_DIAL = ["V⎓", "V~", "OFF", "Hz", "Ω"]
SHUNT = {"20µ": 1e4, "200µ": 1e3, "2m": 100.0, "20m": 10.0, "200m": 1.0}
R_LEAD, R_CLIP, R_PROBE = 0.035, 0.05, 0.08


class State(object):
    def __init__(self):
        self.turns = 0.0
        self.T = TRUE["T0"]
        self.broken = False
        self.usb = False
        self.pluck_t = -99.0
        self.pluck_amp = 0.0
        self.harm = 2
        self.harm_t = 0.5
        self.leads = []                  # [a, b]   b=None while held
        self.held = None                 # lead index, or "pr:YV" / "pr:YCOM"
        self.probe = {"YV": None, "YCOM": None}
        self.fuse = False
        self.fuse_t = 0.0
        self.t = 0.0
        self.spare = 1
        self.ax_dial = 0
        self.ms = {"dial": 2, "hold": False, "held": None, "rel": None, "sel": 0, "duty": False}


S = State()


# ==============================================================================
#  2.  줄 (cm 단위 기하, SI 단위 물리)
# ==============================================================================
def path_pts():
    dh = S.turns * H1 / 10.0
    if dh > 0:
        return [GEO["E0"], GEO["S1"], GEO["S2"], GEO["P1"], (GEO["TP"][0], GEO["TP"][1] + dh), GEO["P2"], GEO["E1"]]
    return [GEO["E0"], GEO["S1"], GEO["S2"], GEO["P1"], GEO["P2"], GEO["E1"]]


def path_len(p):
    return sum(math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]) for i in range(1, len(p)))


_t = S.turns
S.turns = 0
L_PATH0 = path_len(path_pts())
S.turns = _t
B_VIB = (GEO["S2"][0] - GEO["S1"][0]) / 100.0


def Lu(T):
    return (L_PATH0 * 10 - TRUE["slack"]) / 1000.0 * (1 + TRUE["alpha"] * (T - TRUE["T0"]))


def tension():
    L = path_len(path_pts()) / 100.0
    lu = Lu(S.T)
    return max(0.0, TRUE["E"] * TRUE["A"] * (L - lu) / lu)


def fundamental():
    F = tension()
    return 0.0 if F <= 0 else math.sqrt(F / TRUE["Lam"]) / (2 * B_VIB)


F_BREAK = TRUE["Lam"] * (2 * B_VIB * 432) ** 2


def r_len(cm):
    return TRUE["rho"] * (1 + TRUE["beta"] * (S.T - TRUE["T0"])) * (cm / 100.0) / TRUE["A"]


def path_at(seg, u):
    p = path_pts()
    s = sum(math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]) for i in range(1, seg + 1))
    return s + u * math.hypot(p[seg + 1][0] - p[seg][0], p[seg + 1][1] - p[seg][1])


def point_at(s):
    p = path_pts()
    for i in range(1, len(p)):
        L = math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1])
        if s <= L or i == len(p) - 1:
            u = min(1.0, s / L) if L > 0 else 0
            return (p[i - 1][0] + (p[i][0] - p[i - 1][0]) * u, p[i - 1][1] + (p[i][1] - p[i - 1][1]) * u)
        s -= L
    return p[-1]


def string_amp():
    age = S.t - S.pluck_t
    return 0.0 if (age < 0 or S.broken) else S.pluck_amp * math.exp(-age / 2.6)


# ==============================================================================
#  3.  회로 : 마디 해석
# ==============================================================================
def is_clip(t):
    return t.startswith("c:") or t.startswith("b:")


def elec(t):
    return "body" if t and t.startswith("b:") else t


def node(x):
    return "GND" if x == "Sm" else "B" if x == "body" else x


def gauss_solve(A, b):
    n = len(b)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        piv = M[c][c] or 1e-30
        for r in range(c + 1, n):
            k = M[r][c] / piv
            if k:
                for j in range(c, n + 1):
                    M[r][j] -= k * M[c][j]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = M[r][n] - sum(M[r][j] * x[j] for j in range(r + 1, n))
        x[r] = s / (M[r][r] or 1e-30)
    return x


class Sol(object):
    pass


def solve():
    R, sR = [], []
    ends = []
    for a, b in S.leads:
        if b is None:
            continue
        R.append((elec(a), elec(b), R_LEAD + (R_CLIP if is_clip(a) else 0) + (R_CLIP if is_clip(b) else 0)))
        ends += [a, b]
    for k in ("YV", "YCOM"):
        t = S.probe[k]
        if t:
            R.append((k, elec(t), R_PROBE + (R_CLIP if is_clip(t) else 0)))
            ends.append(t)
    clips = sorted(set(t for t in ends if t.startswith("c:")), key=lambda t: float(t[2:]))
    chain = [("GND", 0.0)] + [(t, float(t[2:])) for t in clips] + [("B", path_len(path_pts()))]
    for i in range(1, len(chain)):
        if S.broken and chain[i - 1][1] < S.broke_at < chain[i][1]:
            continue
        r = (chain[i - 1][0], chain[i][0], max(1e-5, r_len(chain[i][1] - chain[i - 1][1])))
        R.append(r)
        if not S.broken:
            sR.append(r)
    for i in range(7):
        R.append(("R%da" % i, "R%db" % i, TRUE["R"][i]))
    R.append(("Sp", "GND", 1000.0))
    ax = AX100_DIAL[S.ax_dial]
    R.append(("X10A", "XCOM", 0.012))
    if ax.startswith("DCV") or ax.startswith("ACV"):
        R.append(("XV", "XCOM", 1e6))
    if ax.startswith("DCA") and ax != "DCA 10" and not S.fuse:
        R.append(("XV", "XCOM", SHUNT[ax.split(" ")[1]]))
    ms = MS_DIAL[S.ms["dial"]]
    if ms not in ("OFF", "Ω"):
        R.append(("YV", "YCOM", 11e6))
    names = set(["A", "B", "Sp", "XV", "XCOM", "X10A", "YV", "YCOM"])
    for a, b, _ in R:
        names.add(node(a))
        names.add(node(b))
    names.discard("GND")
    nodes = sorted(names)
    idx = dict((n, i) for i, n in enumerate(nodes))
    N = len(nodes)
    G = [[0.0] * N for _ in range(N)]
    I = [0.0] * N

    def stamp(a, b, r):
        g = 1.0 / r
        ia, ib = idx.get(node(a)), idx.get(node(b))
        if ia is not None:
            G[ia][ia] += g
        if ib is not None:
            G[ib][ib] += g
        if ia is not None and ib is not None:
            G[ia][ib] -= g
            G[ib][ia] -= g
    for a, b, r in R:
        stamp(a, b, r)
    if S.usb:
        stamp("A", "GND", TRUE["Rint"])
        I[idx["A"]] += 5.0 / TRUE["Rint"]
    for i in range(N):
        G[i][i] += 1e-12
    V = gauss_solve(G, I)

    def volt(t):
        n = node(elec(t))
        return 0.0 if n == "GND" else V[idx[n]] if n in idx else 0.0
    o = Sol()
    o.volt = volt
    o.P = sum((volt(a) - volt(b)) ** 2 / r for a, b, r in sR)
    o.axV = volt("XV") - volt("XCOM")
    o.ax10 = volt("X10A") - volt("XCOM")
    o.Ima = o.axV / SHUNT[ax.split(" ")[1]] if (ax.startswith("DCA") and ax != "DCA 10" and not S.fuse) else 0.0
    o.axI = o.ax10 / 0.012 if ax == "DCA 10" else o.Ima
    o.msV = volt("YV") - volt("YCOM")

    def ohm(a, b):
        na, nb = node(a), node(b)
        if na == nb:
            return 0.0
        I2 = list(I)
        ia, ib = idx.get(na), idx.get(nb)
        if ia is not None:
            I2[ia] += 1e-3
        if ib is not None:
            I2[ib] -= 1e-3
        V2 = gauss_solve(G, I2)
        va = V2[ia] if ia is not None else 0.0
        vb = V2[ib] if ib is not None else 0.0
        r = (va - vb) / 1e-3
        return float("inf") if r > 1e9 else r
    o.ohm = ohm
    # 어떤 단자끼리 도선으로 이어졌는가
    par = {}

    def f(x):
        par.setdefault(x, x)
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for a, b in S.leads:
        if b is not None:
            par[f(node(elec(a)))] = f(node(elec(b)))
    for k in ("YV", "YCOM"):
        if S.probe[k]:
            par[f(k)] = f(node(elec(S.probe[k])))
    o.f = f
    return o


SOL = None


# ==============================================================================
#  4.  계기의 표시
# ==============================================================================
def fmt(v, dec):
    return ("-" if v < 0 else "") + ("%.*f" % (dec, abs(v)))


def amp_v():
    if not S.usb or S.broken:
        return 0.0
    age = S.t - S.pluck_t
    return 0.0 if age < 0 else 1.6 * S.pluck_amp * math.exp(-age / 2.6)


def across_s(a, b):
    f = SOL.f
    return (f(a) == f("Sp") and f(b) == f("GND")) or (f(a) == f("GND") and f(b) == f("Sp"))


def ax_reading():
    ax = AX100_DIAL[S.ax_dial]
    if ax == "OFF":
        return ""

    def n():
        return 1 + (CAL["ax"][0] + 0.08 * gauss()) / 100

    def dig(dec, k):
        return (CAL["ax"][1] + k * gauss()) * 10 ** (-dec) * 0.5
    kind, rng = ax.split(" ") if " " in ax else (ax, "")
    if kind == "DCV":
        full = {"200m": 0.2, "2": 2, "20": 20, "200": 200, "600": 600}[rng]
        dec = {"200m": 1, "2": 3, "20": 2, "200": 1, "600": 0}[rng]
        if abs(SOL.axV) >= full * 0.9995:
            return "1"
        return fmt(SOL.axV * n() * (1000 if rng == "200m" else 1) + dig(dec, 0.6), dec)
    if kind == "ACV":
        return fmt(abs(amp_v()) * 0.71, 1 if rng == "200" else 0)
    if kind == "DCA":
        full = {"20µ": 20e-6, "200µ": 200e-6, "2m": 2e-3, "20m": 20e-3, "200m": 0.2, "10": 10}[rng]
        mult = {"20µ": 1e6, "200µ": 1e6, "2m": 1e3, "20m": 1e3, "200m": 1e3, "10": 1}[rng]
        dec = {"20µ": 2, "200µ": 1, "2m": 3, "20m": 2, "200m": 1, "10": 2}[rng]
        if abs(SOL.axI) >= full * 0.9995:
            return "1"
        return fmt(SOL.axI * mult * n() + dig(dec, 0.6), dec)
    if kind == "Ω":
        full = {"200": 200, "2k": 2e3, "20k": 2e4, "200k": 2e5, "20M": 2e7}[rng]
        dec = {"200": 1, "2k": 3, "20k": 2, "200k": 1, "20M": 2}[rng]
        div = {"200": 1, "2k": 1e3, "20k": 1e3, "200k": 1e3, "20M": 1e6}[rng]
        r = SOL.ohm("XV", "XCOM") + 0.12
        if r == float("inf") or r >= full * 0.9995:
            return "1"
        if r < 0:
            return "-1"
        return fmt(max(0.0, r * n() / div + dig(dec, 0.8)), dec)
    if kind == "→|":
        r = SOL.ohm("XV", "XCOM")
        return "1" if (r == float("inf") or r > 2000) else "%03d" % int(round(r))
    return "1"


def freq_reading():
    if not S.usb or S.broken or not across_s("YV", "YCOM"):
        return 0.0
    age = S.t - S.pluck_t
    amp = S.pluck_amp * math.exp(-age / 2.6)
    if age < 0 or amp < 0.03:
        return 0.0
    f0 = fundamental() * (1 + 0.0006 * gauss() + 0.0012 * math.sin(S.t * 1.3) * min(1, (S.T - TRUE["T0"]) / 60))
    if age < 0.45 + 0.4 * S.harm_t:
        v = f0 * S.harm
    elif amp > 0.11:
        v = f0
    else:
        v = 20 + RNG.random() * 1400
    return v * (1 + CAL["ms"][0] / 100 * 0.5)


def ms_reading():
    M = S.ms
    mode = MS_DIAL[M["dial"]]
    if mode == "OFF":
        return ("", "", [])
    if M["hold"] and M["held"]:
        return M["held"]

    def n():
        return 1 + (CAL["ms"][0] + 0.1 * gauss()) / 100

    def auto(v, units, ann):
        a = abs(v)
        for lim, div, dec, u in units:
            if a < lim:
                return (fmt(v / div * n() + (CAL["ms"][1] + 0.5 * gauss()) * 10 ** (-dec) * 0.5, dec), u, ann)
        return ("OL", units[-1][3], ann)
    if mode == "V⎓":
        r = auto(SOL.msV - (M["rel"] or 0), [(0.4, 1e-3, 1, "mV"), (4, 1, 3, "V"), (40, 1, 2, "V"), (400, 1, 1, "V"), (500, 1, 0, "V")], ["AUTO", "DC"])
    elif mode == "V~":
        r = auto(amp_v() * 0.71 if across_s("YV", "YCOM") else 0.0, [(4, 1, 3, "V"), (40, 1, 2, "V")], ["AUTO", "AC"])
    elif mode == "Hz":
        fr = freq_reading()
        if M["duty"]:
            r = (("%.1f" % (49 + 2 * RNG.random())) if fr > 0 else "0.0", "%", [])
        elif fr <= 0:
            r = ("0.000", "Hz", ["AUTO"])
        else:
            r = auto(fr, [(5, 1, 3, "Hz"), (50, 1, 2, "Hz"), (500, 1, 1, "Hz"), (5000, 1e3, 3, "kHz"), (5e4, 1e3, 2, "kHz")], ["AUTO"])
    else:
        rr = SOL.ohm("YV", "YCOM") + 0.1 - (M["rel"] or 0)
        inf = rr == float("inf")
        if M["sel"] == 1:
            r = ("OL", "V", ["→|"]) if (inf or rr > 3000) else ("%.3f" % (rr * 1e-3), "V", ["→|"])
        elif M["sel"] == 2:
            r = ("OL", "Ω", ["•))"]) if (inf or rr > 4e7) else auto(rr, [(400, 1, 1, "Ω"), (4e3, 1e3, 3, "kΩ")], ["•))"])
        elif M["sel"] == 3:
            r = ("0.012", "nF", ["AUTO"])
        else:
            r = ("OL", "MΩ", ["AUTO"]) if (inf or rr > 4e7) else auto(rr, [(400, 1, 1, "Ω"), (4e3, 1e3, 3, "kΩ"), (4e4, 1e3, 2, "kΩ"), (4e5, 1e3, 1, "kΩ"), (4e6, 1e6, 3, "MΩ"), (4e7, 1e6, 2, "MΩ")], ["AUTO"])
    if M["rel"] is not None:
        r = (r[0], r[1], list(r[2]) + ["REL"])
    return r


# ==============================================================================
#  5.  화면
# ==============================================================================
BG, PANEL, PANEL2 = "#1c2027", "#22262d", "#2b2f36"
FG, FG_DIM, ACC, BAD = "#e8eef2", "#9aa3ab", "#f2c14e", "#f0a79f"
LEAD_COL = ["#c8262b", "#1d1d1f", "#2b62c4", "#e3b21a", "#2f8a3e", "#e06a1f", "#6b3fa0", "#2aa3a3", "#b0b0b0"]
TERM_X = {"A": 1.5, "B": 3.6, "Sp": 5.7, "Sm": 7.8}
TERM_COL = {"A": "#c8262b", "B": "#1d1d1f", "Sp": "#e3b21a", "Sm": "#2f8a3e"}
TERM_LBL = {"A": "A", "B": "B", "Sp": "S+", "Sm": "S−"}
KNOB_R, KNOB_Y0, KNOB_H = 1.5, 0.35, 1.0

# 7-segment
SEG = {"0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg", "5": "acdfg", "6": "acdefg",
       "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g", "O": "abcdef", "L": "def", " ": ""}


def seg7(cv, ch, x, y, w, h, col, tag):
    s = SEG.get(ch, "")
    t = max(2, h * 0.11)
    sl = h * 0.07

    def P(u, v):
        return (x + u * w + (1 - v) * sl, y + v * h)
    for v, k in ((0.04, "a"), (0.5, "g"), (0.96, "d")):
        if k in s:
            a0, a1 = P(0.14, v), P(0.86, v)
            cv.create_line(a0[0], a0[1], a1[0], a1[1], fill=col, width=t, capstyle="round", tags=tag)
    for u, v0, v1, k in ((0.9, 0.06, 0.48, "b"), (0.9, 0.52, 0.94, "c"), (0.1, 0.52, 0.94, "e"), (0.1, 0.06, 0.48, "f")):
        if k in s:
            a0, a1 = P(u, v0), P(u, v1)
            cv.create_line(a0[0], a0[1], a1[0], a1[1], fill=col, width=t, capstyle="round", tags=tag)


def cells(txt, n):
    out = []
    for ch in txt:
        if ch == "." and out:
            out[-1][1] = True
            continue
        out.append([ch, False])
    while len(out) < n:
        out.insert(0, [" ", False])
    return out[-n:]


def rrect(cv, x1, y1, x2, y2, r=6, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


class Tape(object):
    """a 1 m steel tape lying on a canvas: origin (cm of the canvas' world), angle"""
    def __init__(self, x, y, ang=0.0):
        self.x, self.y, self.ang, self.on = x, y, ang, False

    def to_local(self, wx, wy):
        c, s = math.cos(self.ang), math.sin(self.ang)
        dx, dy = wx - self.x, wy - self.y
        return dx * c + dy * s, -dx * s + dy * c

    def contains(self, wx, wy):
        u, v = self.to_local(wx, wy)
        return -0.5 <= u <= 101 and -1.4 <= v <= 0.1


def draw_tape(cv, tape, W2P, scale, tag="tape"):
    """the tape's top edge carries the marks; it lies below its origin line (world y up)"""
    if not tape.on:
        return
    c, s = math.cos(tape.ang), math.sin(tape.ang)

    def P(u, v):          # u along, v up
        return W2P(tape.x + u * c - v * s, tape.y + u * s + v * c)
    pts = []
    for u, v in ((0, 0), (100, 0), (100, -1.3), (0, -1.3)):
        pts += list(P(u, v))
    cv.create_polygon(pts, fill="#f3cd2f", outline="#a8891c", tags=tag)
    step = 1 if scale * 0.1 >= 3 else 5 if scale * 0.5 >= 3 else 10
    W, H = int(cv.winfo_width()), int(cv.winfo_height())
    for mm in range(0, 1001, step):
        u = mm / 10.0
        a = P(u, 0)
        if a[0] < -50 or a[0] > W + 50 or a[1] < -50 or a[1] > H + 50:
            continue
        ln = 0.55 if mm % 10 == 0 else 0.38 if mm % 5 == 0 else 0.25
        b = P(u, -ln)
        cv.create_line(a[0], a[1], b[0], b[1], fill="#151515", width=1, tags=tag)
        if mm % 10 == 0 and scale > 6:
            q = P(u + 0.08, -0.95)
            cv.create_text(q[0], q[1], text=str(mm // 10), anchor="w", angle=-math.degrees(tape.ang),
                           fill="#c4161c" if mm % 100 == 0 else "#151515",
                           font=("Arial", max(6, int(scale * 0.4)), "bold"), tags=tag)


class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title(T("GPhO 2017 실험 시뮬레이터 — E1 전기 기타", "GPhO 2017 Experiment Simulator — E1 Electric Guitar") + "   v" + APP_VERSION)
        self.geometry("1500x930")
        self.minsize(1200, 800)
        self.configure(bg=BG)
        # 스탠드 보기 (정면) : 세계 cm -> 화면 px
        self.sx = 13.0
        self.ox = 30.0
        self.oy = 300.0
        self.tape = Tape(11.0, BASE_Y + 1.85)
        self.ptape = Tape(1.0, 4.0, -math.pi / 2)
        self.drag = None
        self.mouse = (0, 0, None)
        self.ax_txt = ""
        self.ms_txt = ("", "", [])
        self.last_ax = 0
        self.last_ms = 0
        self.flash = ("", 0)
        self.photo_win = None
        self._build()
        self._last = time.time()
        self.after(30, self._tick)

    # ------------------------------------------------------------------ #
    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", side="top")
        tk.Label(top, text="GPhO 2017  ·  " + T("E1 전기 기타 (20점)", "E1 Electric guitar (20 pts)"),
                 bg=BG, fg=ACC, font=("Segoe UI", 13, "bold")).pack(side="left", padx=14, pady=6)
        tk.Label(top, text=T("회전 수와 줄자 눈금은 직접 세고 읽으세요", "count the turns and read the tape yourself"),
                 bg=BG, fg=FG_DIM, font=("Segoe UI", 9)).pack(side="left")
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, text=T("스탠드 정면 — 휠: 확대 · 우클릭 끌기: 이동 · 줄 클릭: 퉁김 · 손잡이 위 휠/끌기: 나사 · 줄자: 끌기, 줄자 위 휠: 기울이기(Shift 미세)",
                              "stand, front — wheel: zoom · right-drag: pan · click the string: pluck · wheel/drag on the knob: the screw · tape: drag, wheel over it: tilt (Shift: fine)"),
                 bg=BG, fg=FG_DIM, font=("Segoe UI", 9), anchor="w").pack(fill="x")
        self.cs = tk.Canvas(left, bg="#20252c", height=380, highlightthickness=0)
        self.cs.pack(fill="both", expand=True)
        tk.Label(left, text=T("멀티미터·저항·전원 (위에서) — 다이얼 왼/오른쪽 절반 클릭 또는 휠 · 단자를 차례로 클릭해 시험 리드 연결 · 우클릭: 리드 뽑기 / 내려놓기",
                              "meters · resistors · supply (from above) — click the left/right half of a dial or wheel over it · click a terminal, then another, for a test lead · R-click: pull a lead out / put it down"),
                 bg=BG, fg=FG_DIM, font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(6, 0))
        self.cm = tk.Canvas(left, bg="#2e3238", height=330, highlightthickness=0)
        self.cm.pack(fill="x")
        right = tk.Frame(body, bg=PANEL, width=300)
        right.pack(side="left", fill="y", padx=(8, 0))
        right.pack_propagate(False)
        tk.Label(right, text=T("조작", "Controls"), bg=PANEL, fg=ACC, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        bs = dict(bg=PANEL2, fg=FG, activebackground="#343941", activeforeground=FG, relief="flat", bd=0, padx=8, pady=6, font=("Segoe UI", 10))
        tk.Button(right, text=T("줄 퉁기기", "Pluck the string"), command=self.pluck, **bs).pack(fill="x", padx=10, pady=2)
        self.b_usb = tk.Button(right, text="", command=self.toggle_usb, **bs)
        self.b_usb.pack(fill="x", padx=10, pady=2)
        tk.Button(right, text=T("시험 리드 모두 뽑기", "Pull out all test leads"), command=self.clear_leads, **bs).pack(fill="x", padx=10, pady=2)
        self.b_spare = tk.Button(right, text=T("예비 줄로 교체", "Fit the spare string"), command=self.fit_spare, **bs)
        self.b_spare.pack(fill="x", padx=10, pady=2)
        tk.Button(right, text=T("줄자를 스탠드에 / 치우기", "Tape on the stand / away"), command=self.toggle_tape, **bs).pack(fill="x", padx=10, pady=2)
        tk.Button(right, text=T("100배 사진 보기", "Look at the 100× photo"), command=self.open_photo, **bs).pack(fill="x", padx=10, pady=2)
        tk.Label(right, text=T("안내", "Notes"), bg=PANEL, fg=ACC, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(14, 4))
        tk.Label(right, justify="left", wraplength=278, bg=PANEL, fg=FG_DIM, font=("Segoe UI", 9), text=T(
            "• 조임 나사는 한 바퀴에 0.70 mm 올라갑니다. 손잡이의 흰 표시로 회전 수를 세세요.\n"
            "• 작은 멀티미터(AX-MS811)는 USB 전원이 꽂혀 있을 때만 S+와 S− 사이의 진동수를 읽습니다. 퉁긴 직후에는 배음을 보일 수 있습니다.\n"
            "• 400 Hz가 넘도록 줄을 조이지 마세요.\n"
            "• 200 mA가 넘으면 AX-100의 10 A 단자를 쓰세요 (mA 단자는 200 mA 퓨즈).\n"
            "• 리드 끝을 든 채 줄이나 막대를 클릭하면 그곳에 집게를 물립니다.",
            "• The tensioner screw rises 0.70 mm a turn; count the turns by the white mark on its knob.\n"
            "• The small meter (AX-MS811) reads frequency between S+ and S− only with the USB supply plugged in; right after a pluck it may show a harmonic.\n"
            "• Do not tension the string past 400 Hz.\n"
            "• Over 200 mA, use the AX-100's 10 A socket (the mA socket is fused at 200 mA).\n"
            "• Holding a lead end, click the string or the bar to clip it there.")).pack(anchor="w", padx=10)
        self.status = tk.Label(right, justify="left", wraplength=278, bg="#12161b", fg=ACC, font=("Segoe UI", 9), anchor="nw", padx=8, pady=8)
        self.status.pack(fill="both", expand=True, padx=10, pady=10)
        for cv in (self.cs, self.cm):
            cv.bind("<Motion>", self.on_move)
            cv.bind("<Button-1>", self.on_down)
            cv.bind("<B1-Motion>", self.on_drag)
            cv.bind("<ButtonRelease-1>", self.on_up)
            cv.bind("<Button-3>", self.on_rdown)
            cv.bind("<B3-Motion>", self.on_rdrag)
            cv.bind("<ButtonRelease-3>", self.on_rup)
            cv.bind("<MouseWheel>", self.on_wheel)
            cv.bind("<Button-4>", lambda e: self.on_wheel(e, 1))
            cv.bind("<Button-5>", lambda e: self.on_wheel(e, -1))
        self.bind("<Escape>", lambda e: self.drop_held())
        self.tape.on = True

    # ---------------- coordinates -------------------------------------- #
    def W2P(self, x, y):
        return (self.ox + x * self.sx, self.oy - y * self.sx)

    def P2W(self, px, py):
        return ((px - self.ox) / self.sx, (self.oy - py) / self.sx)

    # 위에서 본 계기 배치 (px)
    AXC = (130, 165)
    MSC = (330, 175)
    RBX = 470

    def term_xy(self, t):
        """terminal -> (canvas, x, y)"""
        if t in TERM_X:
            return ("s",) + self.W2P(TERM_X[t], BASE_Y + 2.0)
        if t.startswith("c:"):
            p = point_at(float(t[2:]))
            return ("s",) + self.W2P(p[0], p[1])
        if t.startswith("b:"):
            return ("s",) + self.W2P(float(t[2:]), BASE_Y - 0.5)
        if t[0] == "R":
            i = int(t[1])
            return ("m", self.RBX + 30 + i * 52, 120 if t[2] == "a" else 230)
        if t[0] == "X":
            j = ["X10A", "XCOM", "XV"].index(t)
            return ("m", self.AXC[0] - 50 + j * 50, self.AXC[1] + 112)
        if t in ("YV", "YCOM"):
            return ("m", self.MSC[0] + (18 if t == "YV" else -18), self.MSC[1] + 98)
        return ("m", 0, 0)

    def terminals(self):
        L = ["A", "B", "Sp", "Sm", "X10A", "XCOM", "XV"] + ["R%d%s" % (i, e) for i in range(7) for e in "ab"]
        return L

    # ---------------- drawing ------------------------------------------ #
    def draw_stand(self):
        cv = self.cs
        cv.delete("all")
        W = cv.winfo_width()
        P = self.W2P
        # desk
        x0, y0 = P(-40, 0)
        cv.create_rectangle(-10, y0, W + 10, y0 + 400, fill="#3a3d42", outline="")
        # amplifier box behind, feet, bar
        a, b = P(0.5, 3.4), P(11.2, 0)
        cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#1b1c1f", outline="#2c2d31")
        for x in (1.6, 76.4):
            a, b = P(x - 0.9, BASE_Y - 1), P(x + 0.9, 0)
            cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#202124", outline="")
        # the knob under the bar (it rises with the screw)
        dh = max(0.0, S.turns) * H1 / 10
        kx = GEO["TP"][0]
        a, b = P(kx - 0.27, BASE_Y - 1), P(kx + 0.27, KNOB_Y0 + KNOB_H + dh)
        cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#b9bec2", outline="")
        a, b = P(kx - KNOB_R, KNOB_Y0 + KNOB_H + dh), P(kx + KNOB_R, KNOB_Y0 + dh)
        cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#232427", outline="#121214", tags="knob")
        for i in range(28):
            ang = i / 28.0 * 2 * math.pi
            if math.sin(ang) > 0:
                q = P(kx + KNOB_R * math.cos(ang), 0)[0]
                cv.create_line(q, a[1] + 1, q, b[1] - 1, fill="#121214", tags="knob")
        ang = S.turns * 2 * math.pi
        if math.sin(ang) > 0:
            q = P(kx + KNOB_R * math.cos(ang), 0)[0]
            cv.create_line(q, a[1] + 1, q, b[1] - 1, fill="#f4f4f0", width=max(2, self.sx * 0.12), tags="knob")
        a, b = P(0, BASE_Y), P(78, BASE_Y - 1)
        cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#7a8188", outline="#5d636a", tags="bar")
        # terminal plate and posts
        a, b = P(0.35, BASE_Y + 0.3), P(9.4, BASE_Y)
        cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#18191b", outline="")
        for k, x in TERM_X.items():
            a, b = P(x - 0.42, BASE_Y + 2.0), P(x + 0.42, BASE_Y + 0.3)
            cv.create_rectangle(a[0], a[1], b[0], b[1], fill=TERM_COL[k], outline="#000")
            q = P(x, BASE_Y + 2.6)
            cv.create_text(q[0], q[1], text=TERM_LBL[k], fill=FG, font=("Segoe UI", max(7, int(self.sx * 0.45)), "bold"))
        # anchor, saddles, piezo
        a, b = P(7.4, BASE_Y + 0.55), P(9.3, BASE_Y)
        cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#e7e3d8", outline="")
        a, b = P(GEO["S1"][0] - 1.25, BASE_Y + 0.08), P(GEO["S1"][0] + 1.25, BASE_Y)
        cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#c9a24a", outline="")
        for sx_, yb in ((GEO["S1"][0], BASE_Y + 0.14), (GEO["S2"][0], BASE_Y)):
            pts = list(P(sx_ - 0.95, yb)) + list(P(sx_ + 0.95, yb)) + list(P(sx_, GEO["S1"][1]))
            cv.create_polygon(pts, fill="#ece6d6", outline="#bdb7a8")
        # tensioner body, pins, screw top
        a, b = P(62.6, BASE_Y + 2.3), P(76.2, BASE_Y)
        cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#6b7279", outline="", tags="bar")
        for (px, py), dy in ((GEO["P1"], 0.22), (GEO["P2"], -0.22)):
            q = P(px, py + dy)
            r = 0.22 * self.sx
            cv.create_oval(q[0] - r, q[1] - r, q[0] + r, q[1] + r, fill="#d5d9dd", outline="#8f959b")
        top = GEO["TP"][1] + dh
        a, b = P(kx - 0.27, top - 0.5), P(kx + 0.27, BASE_Y)
        cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#9aa0a6", outline="")
        pts = list(P(kx - 0.45, top - 0.5)) + list(P(kx + 0.45, top - 0.5)) + list(P(kx, top))
        cv.create_polygon(pts, fill="#dcdfe2", outline="#8f959b")
        q = P(*GEO["E1"])
        r = 0.24 * self.sx
        cv.create_oval(q[0] - r, q[1] - r, q[0] + r, q[1] + r, fill="#bfa66a", outline="")
        # the string
        pts = path_pts()
        col = "#f0c6b0" if S.T > 200 else "#eceff2"
        if S.broken:
            L = [GEO["E0"], GEO["S1"], (14, BASE_Y + 0.05), (GEO["S2"][0] - 3, BASE_Y + 0.05), GEO["S2"], (GEO["S2"][0] + 2.2, BASE_Y + 0.05)]
            cv.create_line(*[c for p in L for c in P(*p)], fill=col, width=1.4)
            cv.create_line(*[c for p in pts[3:] for c in P(*p)], fill=col, width=1.4)
        else:
            A = 0.2 * string_amp()
            ph = math.cos(time.time() * 2 * math.pi * 7.3)
            out = [P(*pts[0]), P(*pts[1])]
            if A > 0.004:
                a, b = pts[1], pts[2]
                for j in range(1, 24):
                    u = j / 24.0
                    out.append(P(a[0] + (b[0] - a[0]) * u, a[1] + A * math.sin(math.pi * u) * ph))
            for p in pts[2:]:
                out.append(P(*p))
            cv.create_line(*[c for p in out for c in p], fill=col, width=1.4)
        draw_tape(cv, self.tape, P, self.sx)
        self.draw_leads("s")

    def draw_meters(self):
        cv = self.cm
        cv.delete("all")
        # AX-100
        cx, cy = self.AXC
        rrect(cv, cx - 70, cy - 150, cx + 70, cy + 150, 18, fill="#e8b417", outline="#b88b0c")
        rrect(cv, cx - 62, cy - 142, cx + 62, cy + 142, 12, fill="#5c5f61", outline="")
        cv.create_text(cx - 54, cy - 130, text="AXIO\nMET", anchor="nw", fill="#f4f4f2", font=("Arial", 7, "bold"))
        cv.create_text(cx - 22, cy - 126, text="AX-100", anchor="nw", fill="#f4f4f2", font=("Arial", 9, "bold"))
        cv.create_text(cx + 16, cy - 124, text="DIGITAL MULTIMETER", anchor="nw", fill="#f4f4f2", font=("Arial", 5, "italic"))
        rrect(cv, cx - 56, cy - 112, cx + 56, cy - 58, 6, fill="#3d4042", outline="")
        cv.create_rectangle(cx - 50, cy - 106, cx + 50, cy - 64, fill="#b9bfb3", outline="")
        txt = self.ax_txt
        if txt:
            neg = txt.startswith("-")
            t = txt.lstrip("-")
            half, digs, dec = "", "   ", 0
            if t != "1":
                dec = len(t) - t.index(".") - 1 if "." in t else 0
                nn = int(round(float(t) * 10 ** dec))
                if nn >= 1000:
                    half, nn = "1", nn - 1000
                digs = "%03d" % nn
            else:
                half = "1"
            if neg:
                cv.create_line(cx - 46, cy - 85, cx - 38, cy - 85, fill="#1b1e1c", width=3)
            if half:
                seg7(cv, "1", cx - 44, cy - 101, 14, 32, "#1b1e1c", "ax")
            for i in range(3):
                seg7(cv, digs[i], cx - 26 + i * 24, cy - 101, 20, 32, "#1b1e1c", "ax")
            if dec and digs.strip():
                xx = cx - 26 + (3 - dec) * 24
                cv.create_oval(xx - 2, cy - 71, xx + 2, cy - 67, fill="#1b1e1c", outline="")
        dcx, dcy = cx, cy + 10
        for i, lb in enumerate(AX_LBL):
            a = -math.pi / 2 + i * 2 * math.pi / 20
            cv.create_text(dcx + 50 * math.cos(a), dcy + 50 * math.sin(a), text=lb, fill="#f2f2ee", font=("Arial", 6))
        cv.create_oval(dcx - 36, dcy - 36, dcx + 36, dcy + 36, fill="#2b2d2f", outline="#1a1b1c", tags="axdial")
        a = -math.pi / 2 + S.ax_dial * 2 * math.pi / 20
        c, s = math.cos(a), math.sin(a)
        cv.create_line(dcx - 30 * c, dcy - 30 * s, dcx + 30 * c, dcy + 30 * s, fill="#3a3c3e", width=14, tags="axdial")
        cv.create_line(dcx + 16 * c, dcy + 16 * s, dcx + 30 * c, dcy + 30 * s, fill="#f2f2ee", width=3, tags="axdial")
        for j, lb in enumerate(("10A", "COM", "mAVΩ")):
            x = cx - 50 + j * 50
            cv.create_text(x, cy + 96, text=lb, fill="#f2f2ee", font=("Arial", 7, "bold"))
            cv.create_oval(x - 9, cy + 103, x + 9, cy + 121, fill="#8a3b1e", outline="#5a2410")
            cv.create_oval(x - 4, cy + 108, x + 4, cy + 116, fill="#0b0b0b", outline="")
        # AX-MS811
        cx, cy = self.MSC
        rrect(cv, cx - 50, cy - 140, cx + 50, cy - 82, 10, fill="#2a2d31", outline="")
        rrect(cv, cx - 52, cy - 80, cx + 52, cy + 92, 14, fill="#3a3e43", outline="#24272a")
        rrect(cv, cx - 45, cy - 73, cx + 45, cy + 85, 10, fill="#4a4e52", outline="")
        cv.create_rectangle(cx - 40, cy - 68, cx + 40, cy - 22, fill="#b8bfb2", outline="#2e3134", width=3)
        txt, unit, ann = self.ms_txt
        if txt:
            cv.create_text(cx - 37, cy - 63, text=" ".join(ann + (["HOLD"] if S.ms["hold"] else [])), anchor="w", fill="#1c1f1d", font=("Arial", 5, "bold"))
            cs = cells(" 0L " if txt == "OL" else txt.lstrip("-"), 4)
            if txt.startswith("-"):
                cv.create_line(cx - 38, cy - 41, cx - 33, cy - 41, fill="#1c1f1d", width=2)
            for i, (ch, dp) in enumerate(cs):
                seg7(cv, ch, cx - 32 + i * 16, cy - 55, 14, 26, "#1c1f1d", "ms")
                if dp:
                    xx = cx - 32 + (i + 1) * 16
                    cv.create_oval(xx - 2, cy - 31, xx + 1, cy - 28, fill="#1c1f1d", outline="")
            cv.create_text(cx + 37, cy - 26, text=unit, anchor="e", fill="#1c1f1d", font=("Arial", 6, "bold"))
        for i, lb in enumerate(("SELECT", "RELATIVE", "DATA HOLD", "Hz/DUTY")):
            x = cx - 33 + i * 22
            rrect(cv, x - 9, cy - 12, x + 9, cy - 4, 4, fill="#b4bac0", outline="", tags="msb%d" % i)
            cv.create_text(x, cy + 2, text=lb, fill="#f2f2ee", font=("Arial", 4, "bold"))
        dcx, dcy = cx, cy + 40
        for i, lb in enumerate(MS_DIAL):
            a = -math.pi / 2 + (i - 2) * math.pi / 5.2
            cv.create_text(dcx + 40 * math.cos(a), dcy + 40 * math.sin(a), text={"V⎓": "DCV", "V~": "ACV"}.get(lb, lb),
                           fill="#f0c419" if lb != "OFF" else "#f2f2ee", font=("Arial", 6, "bold"))
        cv.create_oval(dcx - 27, dcy - 27, dcx + 27, dcy + 27, fill="#5a5f65", outline="#3a3e43", tags="msdial")
        a = -math.pi / 2 + (S.ms["dial"] - 2) * math.pi / 5.2
        cv.create_line(dcx + 4 * math.cos(a), dcy + 4 * math.sin(a), dcx + 24 * math.cos(a), dcy + 24 * math.sin(a), fill="#f2f2ee", width=3, tags="msdial")
        cv.create_text(cx, cy + 78, text="AX-MS811", fill="#e8e8e4", font=("Arial", 7, "bold"))
        for k, dx in (("YV", 18), ("YCOM", -18)):
            if not S.probe[k] and S.held != "pr:" + k:
                x = cx + 60 + (0 if k == "YV" else 14)
                cv.create_line(x, cy - 60, x, cy + 60, fill="#c52a25" if k == "YV" else "#18191b", width=7, tags="pr:" + k)
                cv.create_line(x, cy - 75, x, cy - 60, fill="#d8dce0", width=2, tags="pr:" + k)
        # resistors
        x0 = self.RBX
        cv.create_rectangle(x0, 90, x0 + 375, 265, fill="#e9e5da", outline="#c8c3b6")
        for i in range(7):
            x = x0 + 30 + i * 52
            for y, col in ((120, "#c8262b"), (230, "#1d1d1f")):
                cv.create_oval(x - 9, y - 9, x + 9, y + 9, fill=col, outline="#000")
                cv.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#0c0c0c", outline="")
            cv.create_line(x, 130, x, 220, fill="#9aa0a6", width=2)
            if i < 3:
                cv.create_rectangle(x - 10, 150, x + 10, 200, fill="#f3f1ea", outline="#bbb")
            else:
                cv.create_rectangle(x - 6, 158, x + 6, 192, fill="#d6c49a", outline="")
            cv.create_text(x, 252, text=["0.1Ω", "1Ω", "3Ω", "10Ω", "30Ω", "100Ω", "1kΩ"][i], fill="#2a2a2a", font=("Arial", 8, "bold"))
        # USB charger
        x = 900
        cv.create_rectangle(x, 120, x + 70, 190, fill="#f6f6f3" if S.usb else "#d9d9d4", outline="#999", tags="usb")
        cv.create_text(x + 35, 155, text="5V ⎓ 1A\n" + (T("꽂힘", "plugged in") if S.usb else T("빠짐", "unplugged")), fill="#555", font=("Arial", 8), tags="usb")
        self.draw_leads("m")

    def draw_leads(self, which):
        cv = self.cs if which == "s" else self.cm
        H = int(cv.winfo_height())
        mx, my, mcv = self.mouse
        items = [(i, a, b, LEAD_COL[i % 9]) for i, (a, b) in enumerate(S.leads)]
        for k in ("YV", "YCOM"):
            if S.probe[k] or S.held == "pr:" + k:
                items.append(("p" + k, k, S.probe[k], "#c52a25" if k == "YV" else "#18191b"))
        for i, a, b, col in items:
            A = self.term_xy(a)
            Bp = self.term_xy(b) if b else None
            ends = []
            if Bp is None:
                if mcv == which and A[0] == which:
                    ends = [(A[1], A[2]), (mx, my)]
                elif A[0] == which:
                    ends = [(A[1], A[2]), (A[1], A[2] + 60)]
            elif A[0] == which and Bp[0] == which:
                ends = [(A[1], A[2]), (Bp[1], Bp[2])]
            else:
                mine = A if A[0] == which else Bp if Bp[0] == which else None
                if mine is None:
                    continue
                edge = H - 2 if which == "s" else 2
                ends = [(mine[1], mine[2]), (mine[1] + 20, edge)]
                cv.create_text(mine[1] + 26, edge + (-10 if which == "s" else 10), text="↕" + str(i if isinstance(i, int) else k), fill=col if col != "#1d1d1f" else "#bbb", font=("Arial", 8, "bold"))
            if len(ends) < 2:
                continue
            (x1, y1), (x2, y2) = ends
            sag = 30 + abs(x2 - x1) * 0.15
            pts = [x1, y1, x1, y1 + 15, (x1 + x2) / 2, max(y1, y2) + sag, x2, y2 + 15, x2, y2]
            cv.create_line(*pts, smooth=True, fill=col, width=2.2)
            for (x, y) in ends[:1] + (ends[1:] if Bp is not None and Bp[0] == which else []):
                cv.create_oval(x - 4, y - 4, x + 4, y + 4, fill=col, outline="#000")

    # ---------------- hit tests ---------------------------------------- #
    def hit_term(self, which, x, y):
        for t in self.terminals():
            c, tx, ty = self.term_xy(t)
            if c == which and abs(tx - x) < 11 and abs(ty - y) < 11:
                return t
        return None

    def hit_string(self, x, y):
        p = path_pts()
        best = None
        for i in range(len(p) - 1):
            a, b = self.W2P(*p[i]), self.W2P(*p[i + 1])
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = dx * dx + dy * dy
            if L < 1e-9:
                continue
            u = max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / L))
            d = math.hypot(a[0] + u * dx - x, a[1] + u * dy - y)
            if d < 7 and (best is None or d < best[0]):
                best = (d, i, u)
        return best

    # ---------------- actions ------------------------------------------ #
    def say(self, m):
        self.flash = (m, time.time())

    def pluck(self):
        if S.broken:
            return
        S.pluck_t = S.t
        S.pluck_amp = 0.85 + 0.15 * RNG.random()
        S.harm = 2 if RNG.random() < 0.6 else 3
        S.harm_t = RNG.random()
        self.bell()

    def toggle_usb(self):
        S.usb = not S.usb

    def clear_leads(self):
        S.leads = []
        S.held = None
        S.probe = {"YV": None, "YCOM": None}

    def toggle_tape(self):
        self.tape.on = not self.tape.on
        self.tape.x, self.tape.y, self.tape.ang = 11.0, BASE_Y + 1.85, 0.0

    def snap(self):
        S.broken = True
        S.broke_at = path_at(2, 0.6)
        S.pluck_amp = 0
        self.say(T("줄이 끊어졌습니다 — 한계를 넘어 조였습니다. 예비 줄로 교체하세요.", "the string snapped — it was tensioned past its limit. Fit the spare string."))

    def fit_spare(self):
        if S.spare <= 0 or not S.broken:
            return
        S.spare -= 1
        S.broken = False
        S.turns = 0
        S.T = TRUE["T0"]
        TRUE["slack"] = 1.25 + 0.15 * gauss()
        S.leads = [l for l in S.leads if not (l[0].startswith("c:") or (l[1] or "").startswith("c:"))]
        for k in ("YV", "YCOM"):
            if S.probe[k] and S.probe[k].startswith("c:"):
                S.probe[k] = None
        S.held = None

    def turn_knob(self, d):
        S.turns = max(-2.0, min(21.5, S.turns + d))
        if not S.broken and tension() > F_BREAK:
            self.snap()

    def attach(self, t):
        if isinstance(S.held, int):
            l = S.leads[S.held]
            if l[0] != t:
                l[1] = t
                S.held = None
        elif S.held:
            S.probe[S.held[3:]] = t
            S.held = None

    def start_lead(self, t):
        if len(S.leads) >= 9:
            self.say(T("시험 리드 아홉 개를 모두 쓰고 있습니다", "all nine test leads are in use"))
            return
        S.leads.append([t, None])
        S.held = len(S.leads) - 1

    def drop_held(self):
        if isinstance(S.held, int):
            S.leads.pop(S.held)
        elif S.held:
            S.probe[S.held[3:]] = None
        S.held = None

    def read_now(self):
        self.last_ax = self.last_ms = 0

    def ms_turn(self, d):
        M = S.ms
        M["dial"] = max(0, min(4, M["dial"] + d))
        M.update(hold=False, rel=None, sel=0, duty=False)
        self.read_now()

    def ms_key(self, i):
        M = S.ms
        mode = MS_DIAL[M["dial"]]
        if mode == "OFF":
            return
        if i == 0 and mode == "Ω":
            M["sel"] = (M["sel"] + 1) % 4
            M["rel"] = None
        if i == 1:
            if M["rel"] is None:
                v = SOL.msV if mode == "V⎓" else (SOL.ohm("YV", "YCOM") + 0.1) if mode == "Ω" else None
                M["rel"] = v if (v is not None and v != float("inf")) else None
            else:
                M["rel"] = None
        if i == 2:
            M["hold"] = not M["hold"]
            M["held"] = self.ms_txt if M["hold"] else None
        if i == 3 and mode == "Hz":
            M["duty"] = not M["duty"]
        self.read_now()

    # ---------------- mouse -------------------------------------------- #
    def which(self, e):
        return "s" if e.widget is self.cs else "m"

    def on_move(self, e):
        self.mouse = (e.x, e.y, self.which(e))

    def on_down(self, e):
        w = self.which(e)
        self.mouse = (e.x, e.y, w)
        self.drag = None
        if w == "s":
            wx, wy = self.P2W(e.x, e.y)
            if S.held is None and self.tape.on and self.tape.contains(wx, wy):
                self.drag = ("tape", wx - self.tape.x, wy - self.tape.y)
                return
            if S.held is None and "knob" in self.tags_at(self.cs, e.x, e.y):
                self.drag = ("knob", e.x)
                return
            t = self.hit_term("s", e.x, e.y)
            if t:
                return self.attach(t) if S.held is not None else self.start_lead(t)
            hs = self.hit_string(e.x, e.y)
            if hs:
                cm = "c:%.2f" % path_at(hs[1], hs[2])
                if S.held is not None:
                    return self.attach(cm)
                if hs[1] == 1 and not S.broken:
                    return self.pluck()
                return self.start_lead(cm)
            if "bar" in self.tags_at(self.cs, e.x, e.y):
                b = "b:%.1f" % max(0.5, min(77.5, wx))
                return self.attach(b) if S.held is not None else self.start_lead(b)
            if S.held is not None:
                self.drop_held()
            return
        t = self.hit_term("m", e.x, e.y)
        if t:
            return self.attach(t) if S.held is not None else self.start_lead(t)
        tags = self.tags_at(self.cm, e.x, e.y)
        for k in ("YV", "YCOM"):
            if "pr:" + k in tags and S.held is None:
                S.held = "pr:" + k
                S.probe[k] = None
                return
        if S.held is not None:
            return
        if "axdial" in tags:
            S.ax_dial = (S.ax_dial + (1 if e.x > self.AXC[0] else -1)) % 20
            self.read_now()
        elif "msdial" in tags:
            self.ms_turn(1 if e.x > self.MSC[0] else -1)
        elif "usb" in tags:
            self.toggle_usb()
        else:
            for i in range(4):
                if "msb%d" % i in tags:
                    self.ms_key(i)

    def tags_at(self, cv, x, y):
        out = set()
        for it in cv.find_overlapping(x - 2, y - 2, x + 2, y + 2):
            out.update(cv.gettags(it))
        return out

    def on_drag(self, e):
        self.mouse = (e.x, e.y, self.which(e))
        if not self.drag:
            return
        if self.drag[0] == "tape":
            wx, wy = self.P2W(e.x, e.y)
            self.tape.x, self.tape.y = wx - self.drag[1], wy - self.drag[2]
        elif self.drag[0] == "knob":
            self.turn_knob((e.x - self.drag[1]) / 160.0)
            self.drag = ("knob", e.x)

    def on_up(self, e):
        self.drag = None

    def on_rdown(self, e):
        self.rd = (e.x, e.y, False)

    def on_rdrag(self, e):
        if self.which(e) != "s":
            return
        x, y, _ = self.rd
        if abs(e.x - x) + abs(e.y - y) > 3:
            self.ox += e.x - x
            self.oy += e.y - y
            self.rd = (e.x, e.y, True)

    def on_rup(self, e):
        if getattr(self, "rd", (0, 0, True))[2]:
            return
        w = self.which(e)
        if S.held is not None:
            return self.drop_held()
        t = self.hit_term(w, e.x, e.y)
        hs = self.hit_string(e.x, e.y) if w == "s" else None
        for i in range(len(S.leads) - 1, -1, -1):
            a, b = S.leads[i]
            ends = [a] + ([b] if b else [])
            if (t and t in ends) or (hs and any(x.startswith("c:") and abs(float(x[2:]) - path_at(hs[1], hs[2])) < 1.5 for x in ends)):
                S.leads.pop(i)
                return
        for k in ("YV", "YCOM"):
            if S.probe[k] and (S.probe[k] == t):
                S.probe[k] = None
                return

    def on_wheel(self, e, d=None):
        s = d if d is not None else (1 if e.delta > 0 else -1)
        w = self.which(e)
        if w == "m":
            tags = self.tags_at(self.cm, e.x, e.y)
            if "axdial" in tags:
                S.ax_dial = (S.ax_dial + s) % 20
                self.read_now()
            elif "msdial" in tags:
                self.ms_turn(s)
            return
        wx, wy = self.P2W(e.x, e.y)
        if "knob" in self.tags_at(self.cs, e.x, e.y):
            return self.turn_knob(s / 24.0)
        if self.tape.on and self.tape.contains(wx, wy):
            self.tape.ang += s * math.radians(0.1 if (e.state & 1) else 0.5)
            return
        f = 1.15 if s > 0 else 1 / 1.15
        ns = max(4.0, min(260.0, self.sx * f))
        self.ox = e.x - (e.x - self.ox) * ns / self.sx
        self.oy = e.y - (e.y - self.oy) * ns / self.sx
        self.sx = ns

    # ---------------- photo -------------------------------------------- #
    def open_photo(self):
        if self.photo_win and self.photo_win.winfo_exists():
            self.photo_win.lift()
            return
        w = tk.Toplevel(self)
        w.title(T("줄 사진 (100배 확대)", "photo of the string (magnified 100×)"))
        w.configure(bg=BG)
        tk.Label(w, text=T("줄자를 끌어 옮기고, 줄자 위에서 휠로 기울이세요 (Shift: 미세)", "drag the tape; wheel over it to tilt (Shift: fine)"), bg=BG, fg=FG_DIM).pack(fill="x")
        cv = tk.Canvas(w, width=980, height=420, bg="#3a3d42", highlightthickness=0)
        cv.pack()
        self.ptape.on = True
        K = 60.0                     # px per cm of the printed photo

        def W2P(x, y):
            return (40 + x * K, 380 - y * K)

        def P2W(px, py):
            return ((px - 40) / K, (380 - py) / K)
        band = 100 * TRUE["d"] * 100       # cm on the photo
        cy = 3.0

        def draw():
            cv.delete("all")
            a, b = W2P(0, 5.6), W2P(14, 0.4)
            cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#a5a9aa", outline="#ddd", width=4)
            stops = [(0.0, "#6d5a49"), (0.12, "#a9784f"), (0.28, "#e6ded2"), (0.36, "#fbfaf6"), (0.47, "#c5c2bc"), (0.62, "#8c6b4f"), (0.8, "#b0743f"), (1.0, "#5b3e2a")]
            for j in range(len(stops) - 1):
                (t0, c0), (t1, _) = stops[j], stops[j + 1]
                p0, p1 = W2P(0, cy + band / 2 - t0 * band), W2P(14, cy + band / 2 - t1 * band)
                cv.create_rectangle(p0[0], p0[1], p1[0], p1[1], fill=c0, outline="")
            q = W2P(2.8, cy)
            cv.create_text(q[0], q[1], text="string", anchor="w", fill="#000", font=("Arial", int(band * K * 0.62), "bold"))
            for yy, d in ((cy + band / 2, 1), (cy - band / 2, -1)):
                p, r = W2P(6.0, yy), W2P(6.0, yy + d * 0.7)
                cv.create_line(r[0], r[1], p[0], p[1], fill="#000", width=3, arrow="last", arrowshape=(14, 16, 7))
            draw_tape(cv, self.ptape, W2P, K, "ptape")
            w.after(60, draw) if w.winfo_exists() else None
        st = {}

        def down(e):
            x, y = P2W(e.x, e.y)
            if self.ptape.contains(x, y):
                st["d"] = (x - self.ptape.x, y - self.ptape.y)

        def move(e):
            if "d" in st:
                x, y = P2W(e.x, e.y)
                self.ptape.x, self.ptape.y = x - st["d"][0], y - st["d"][1]

        def wheel(e, d=None):
            s = d if d is not None else (1 if e.delta > 0 else -1)
            x, y = P2W(e.x, e.y)
            if self.ptape.contains(x, y):
                self.ptape.ang += s * math.radians(0.1 if (e.state & 1) else 0.5)
        cv.bind("<Button-1>", down)
        cv.bind("<B1-Motion>", move)
        cv.bind("<ButtonRelease-1>", lambda e: st.pop("d", None))
        cv.bind("<MouseWheel>", wheel)
        cv.bind("<Button-4>", lambda e: wheel(e, 1))
        cv.bind("<Button-5>", lambda e: wheel(e, -1))
        self.photo_win = w
        draw()

    # ---------------- the loop ----------------------------------------- #
    def _tick(self):
        global SOL
        now = time.time()
        dt = min(0.1, now - self._last)
        self._last = now
        S.t += dt
        SOL = solve()
        L = path_len(path_pts()) / 100.0
        C = TRUE["Lam"] * TRUE["c"] * L
        gL = TRUE["g"] * L
        for _ in range(5):
            S.T += (SOL.P - gL * (S.T - TRUE["T0"])) / C * dt / 5
        if not S.broken and tension() > F_BREAK:
            self.snap()
        if abs(SOL.Ima) > 0.2:
            S.fuse_t += dt * (10 if abs(SOL.Ima) > 0.3 else 1)
            if S.fuse_t > 1.5 and not S.fuse:
                S.fuse = True
                self.say(T("AX-100의 mA 퓨즈가 끊어졌습니다: VΩmA 단자로 200 mA 넘게 흘렀습니다.", "the AX-100's mA fuse has blown: more than 200 mA went through the VΩmA socket."))
        else:
            S.fuse_t = max(0.0, S.fuse_t - dt)
        if now - self.last_ax > 0.333:
            self.last_ax = now
            self.ax_txt = ax_reading()
        if now - self.last_ms > 0.4:
            self.last_ms = now
            self.ms_txt = ms_reading()
        try:
            self.draw_stand()
            self.draw_meters()
        except tk.TclError:
            return
        self.b_usb.config(text=T("USB 충전기 뽑기", "Unplug the USB charger") if S.usb else T("USB 충전기 꽂기", "Plug in the USB charger"))
        w = []
        if S.broken:
            w.append(T("줄이 끊어졌습니다.", "the string has snapped."))
        if S.fuse:
            w.append(T("AX-100 mA 퓨즈 끊어짐", "AX-100 mA fuse blown"))
        if S.T > 60:
            w.append(T("줄이 뜨겁습니다", "the string is hot"))
        if self.flash[0] and now - self.flash[1] < 4:
            w.append(self.flash[0])
        if S.held is not None:
            w.append(T("리드/프로브 끝을 들고 있음: 단자·줄·막대를 클릭 (우클릭 / Esc: 내려놓기)", "a lead / probe end in your hand: click a terminal, the string or the bar (R-click / Esc: put it down)"))
        w.append(T("5 V 전원: ", "5 V supply: ") + (T("꽂힘", "plugged in") if S.usb else T("빠짐", "unplugged")))
        w.append(T("남은 시험 리드: ", "test leads left: ") + str(9 - len(S.leads)))
        self.status.config(text="\n\n".join(w))
        self.after(30, self._tick)


if __name__ == "__main__":
    S.broke_at = 0.0
    App().mainloop()
