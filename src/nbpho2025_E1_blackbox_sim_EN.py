#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  Nordic-Baltic Physics Olympiad 2025  (NBPhO 2025)
  Problem 4 (experimental) :  BLACK BOX
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The box holds three diodes and a resistor, wired as in the official
  solution's "option 2": D1 alone from the blue lead to the yellow one;
  from the yellow lead, D2 into a node N, and from N the resistor R and
  D3 side by side to the blue lead.  Each diode follows
  I = Is (exp(Vj / nVt) - 1) behind a small series resistance, fitted
  to the organisers' measured V-I table (red, green and blue LEDs).
* Power comes only through the yellow supply lead with its built-in
  limiting resistor; the supply's own display shows the voltage before
  that resistor, not the voltage across the box.
* Two 3 1/2-digit multimeters (V, mA, ohm, diode test) are solved with
  the circuit by Newton's method every reading, so any wiring works,
  including wrong ones (a mA range is a 100/10/1 ohm shunt, a V range
  10 Mohm).
* Hidden truths (R, the diodes, the limiting resistor, the meters'
  calibrations) are randomised every session.
* Standard library only (tkinter).

    Run:   python3 nbpho2025_E1_blackbox_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the EN edition differs only in this line

TERMS = ["Y", "B", "PY", "PN", "V1", "C1", "V2", "C2"]
RANGES = [("off", "OFF", None), ("v2", "V⎓ 2", 2.0), ("v20", "V⎓ 20", 20.0), ("v200", "V⎓ 200", 200.0),
          ("m2", "mA 2", 2.0), ("m20", "mA 20", 20.0), ("m200", "mA 200", 200.0),
          ("o2k", "Ω 2k", 2000.0), ("o20k", "Ω 20k", 20000.0), ("dio", "→|", 2.0)]
RMAX = dict((k, c) for k, _, c in RANGES)
SHUNT = {"m2": 100.0, "m20": 10.0, "m200": 1.0}
OHM = {"o2k": (1.0, 1000.0), "o20k": (1.0, 10000.0), "dio": (2.8, 2800.0)}     # (open voltage, internal R)


def T(ko, en):
    return ko if LANG == "ko" else en


# --------------------------------------------------------------------------
#  Physics core  (V, ohm, A)
# --------------------------------------------------------------------------
class Diode(object):
    def __init__(self, v1m, nvt, rs):
        self.nvt, self.rs = nvt, rs
        self.vj = v1m - 1e-3 * rs                     # junction voltage at 1 mA
        self.Is = 1e-3 / (math.exp(self.vj / nvt) - 1)
        self.amax = (self.vj + nvt * math.log(1000.0)) / nvt   # exponential up to 1 A, straight beyond

    def iv(self, v):
        a = v / self.nvt
        if a < self.amax:
            e = math.exp(a)
            return self.Is * (e - 1), self.Is * e / self.nvt
        e = math.exp(self.amax)
        g = self.Is * e / self.nvt
        return self.Is * (e - 1) + g * (v - self.amax * self.nvt), g


class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.R = r.uniform(960, 1060)                                      # the resistor
        self.D1 = Diode(r.uniform(2.93, 3.07), r.uniform(0.205, 0.235), 5)  # blue LED, the reverse branch
        self.D2 = Diode(r.uniform(1.71, 1.80), r.uniform(0.031, 0.038), 3)  # red LED, in series with R
        self.D3 = Diode(r.uniform(2.53, 2.68), r.uniform(0.045, 0.055), 15) # green LED, across R
        self.Rlim = r.uniform(455, 485)                                    # inside the yellow supply lead
        self.Vmax = 15.0
        self.gain = [r.uniform(0.996, 1.004), r.uniform(0.996, 1.004)]
        self.ish = [r.uniform(0.99, 1.01), r.uniform(0.99, 1.01)]


def make_nets(leads):
    par = dict((t, t) for t in TERMS)

    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for a, b in leads:
        par[f(a)] = f(b)
    return f


def lsolve(A, b):
    n = len(b)
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(A[r][i]))
        A[i], A[p] = A[p], A[i]
        b[i], b[p] = b[p], b[i]
        for r in range(i + 1, n):
            k = A[r][i] / A[i][i]
            if k:
                for c in range(i, n):
                    A[r][c] -= k * A[i][c]
                b[r] -= k * b[i]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = b[i] - sum(A[i][c] * x[c] for c in range(i + 1, n))
        x[i] = s / A[i][i]
    return x


class Circuit(object):
    """the box, the supply and the meters, joined by the leads; solved by Newton's method"""

    def __init__(self, ph):
        self.ph = ph
        self.warm = {}

    def solve(self, placed, leads, out, vset, rng):
        ph, f = self.ph, make_nets(leads)
        gnd = f("PN")
        G, Dd, Is = [], [], []
        if "box" in placed:
            y, b = f("Y"), f("B")
            Dd += [(b, "j1", ph.D1), (y, "j2", ph.D2), ("N", "j3", ph.D3)]
            G += [("j1", y, 1 / ph.D1.rs), ("j2", "N", 1 / ph.D2.rs), ("N", b, 1 / ph.R), ("j3", b, 1 / ph.D3.rs)]
        if "psu" in placed:
            p = f("PY")
            G.append((p, gnd, 1 / ph.Rlim))
            if out:
                Is.append((gnd, p, vset / ph.Rlim))
        for i in range(2):
            if "dmm%d" % (i + 1) not in placed:
                continue
            r, c, v = rng[i], f("C%d" % (i + 1)), f("V%d" % (i + 1))
            if r[0] == "v":
                G.append((v, c, 1e-7))
            elif r[0] == "m":
                G.append((v, c, 1 / (SHUNT[r] * ph.ish[i])))
            elif r in OHM:
                voc, ri = OHM[r]
                G.append((v, c, 1 / ri))
                Is.append((c, v, voc / ri))
        names = []
        for e in G + Is:
            for n in e[:2]:
                if n != gnd and n not in names:
                    names.append(n)
        for e in Dd:
            for n in e[:2]:
                if n != gnd and n not in names:
                    names.append(n)
        idx = dict((n, i) for i, n in enumerate(names))
        N = len(names)
        x = [self.warm.get(n, 0.0) for n in names]

        def V(n):
            return 0.0 if n == gnd else x[idx[n]] if n in idx else 0.0
        for _ in range(400):
            A = [[0.0] * N for _ in range(N)]
            bb = [0.0] * N
            for i in range(N):
                A[i][i] = 1e-12

            def stamp(p, q, g):
                i, j = idx.get(p), idx.get(q)
                if i is not None:
                    A[i][i] += g
                if j is not None:
                    A[j][j] += g
                if i is not None and j is not None:
                    A[i][j] -= g
                    A[j][i] -= g

            def inj(p, q, I):                 # current I flowing from p to q through the element
                i, j = idx.get(p), idx.get(q)
                if i is not None:
                    bb[i] -= I
                if j is not None:
                    bb[j] += I
            for p, q, g in G:
                stamp(p, q, g)
            for p, q, I in Is:
                inj(p, q, I)
            for p, q, D in Dd:
                v = V(p) - V(q)
                I, g = D.iv(v)
                stamp(p, q, g)
                inj(p, q, I - g * v)
            xn = lsolve(A, bb)
            dm = max([abs(a - b) for a, b in zip(xn, x)] or [0.0])
            k = 0.05 / dm if dm > 0.05 else 1.0
            x = [a + k * (b - a) for a, b in zip(x, xn)]
            if dm < 1e-10:
                break
        self.warm = dict((n, x[i]) for i, n in enumerate(names))
        return V, f


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_box(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 50 * s, y - 32 * s, x + 30 * s, y + 32 * s, fill="#1d1f23", outline="#000")
    cv.create_text(x - 10 * s, y, text="BLACK BOX", fill="#e9e5da", font=("Helvetica", max(6, int(9 * s)), "bold"))
    cv.create_line(x + 30 * s, y - 6 * s, x + 60 * s, y - 20 * s, fill="#e7c21a", width=3)
    cv.create_line(x + 30 * s, y + 6 * s, x + 60 * s, y + 20 * s, fill="#2b6cd8", width=3)


def art_psu(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 55 * s, y - 40 * s, x + 55 * s, y + 40 * s, fill="#2a2d33", outline="#888")
    cv.create_rectangle(x - 48 * s, y - 32 * s, x - 6 * s, y - 12 * s, fill="#140b0b", outline="")
    cv.create_rectangle(x + 6 * s, y - 32 * s, x + 48 * s, y - 12 * s, fill="#08120b", outline="")
    cv.create_oval(x - 40 * s, y, x - 20 * s, y + 20 * s, fill="#1b1d20", outline="#555")
    cv.create_oval(x + 10 * s, y + 18 * s, x + 20 * s, y + 28 * s, fill="#c0392b", outline="")
    cv.create_oval(x + 28 * s, y + 18 * s, x + 38 * s, y + 28 * s, fill="#1b1d20", outline="#666")


def art_dmm(col):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_rectangle(x - 26 * s, y - 45 * s, x + 26 * s, y + 45 * s, fill=col, outline="#5a3a12")
        cv.create_rectangle(x - 18 * s, y - 36 * s, x + 18 * s, y - 18 * s, fill="#9fae8f", outline="")
        cv.create_oval(x - 12 * s, y - 6 * s, x + 12 * s, y + 18 * s, fill="#1b1d20", outline="")
        cv.create_oval(x - 4 * s, y + 28 * s, x + 4 * s, y + 36 * s, fill="#c0392b", outline="")
        cv.create_oval(x + 10 * s, y + 28 * s, x + 18 * s, y + 36 * s, fill="#111", outline="")
    return art


def art_leads(cv, x, y, sc=1.0):
    s = sc
    for c, r in (("#c0392b", 26), ("#1f2226", 20), ("#2f8f4e", 14)):
        cv.create_oval(x - r * s, y - r * 0.6 * s, x + r * s, y + r * 0.6 * s, outline=c, width=2)


ART = {"box": art_box, "psu": art_psu, "dmm1": art_dmm("#e3b72d"), "dmm2": art_dmm("#e0622e"), "leads": art_leads}
PARTS = [
    ("psu",   ("직류 전원 장치 0–15 V (제한 저항 든 노란 도선)", "DC supply 0–15 V (yellow lead with limiting R)"), []),
    ("box",   ("블랙박스 (다이오드 3, 저항 1)", "Black box (3 diodes, 1 resistor)"), []),
    ("dmm1",  ("멀티미터 1 (노랑)", "Multimeter 1 (yellow)"), []),
    ("dmm2",  ("멀티미터 2 (주황)", "Multimeter 2 (orange)"), []),
    ("leads", ("집게 도선", "Clip leads"), []),
]
ZONES = {
    "psu":   (150, 280, 130, 100),
    "box":   (340, 300, 130, 90),
    "dmm1":  (520, 290, 70, 110),
    "dmm2":  (630, 290, 70, 110),
    "leads": (400, 420, 70, 40),
}
SCENE_TITLE = ("실험대 — 전원 장치, 블랙박스, 멀티미터 2대, 도선", "The bench — supply, black box, two multimeters, leads")
APP_TITLE = ("NBPhO 2025 실험 (문제 4) — 블랙박스", "NBPhO 2025 Experiment (Problem 4) — Black box")
TNAME = {"Y": ("상자 노랑", "box yellow"), "B": ("상자 파랑", "box blue"), "PY": ("전원 노란 도선", "supply yellow lead"),
         "PN": ("전원 −", "supply −"), "V1": ("멀티1 VΩmA", "meter1 VΩmA"), "C1": ("멀티1 COM", "meter1 COM"),
         "V2": ("멀티2 VΩmA", "meter2 VΩmA"), "C2": ("멀티2 COM", "meter2 COM")}


def tn(t):
    return T(*TNAME[t])


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    TP = {"PY": (190, 330), "PN": (250, 190), "Y": (330, 420), "B": (330, 520),
          "V1": (600, 560), "C1": (660, 560), "V2": (790, 560), "C2": (850, 560)}

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.cir = Circuit(self.ph)
        self.leads = []
        self.out = tk.BooleanVar(value=False)
        self.vset = tk.DoubleVar(value=0.0)
        self.rng = [tk.StringVar(value="off"), tk.StringVar(value="off")]
        self.disp, self.disp_t = [0.0, 0.0], [0.0, 0.0]
        self.points = []
        self.build()
        self.refresh()

    def solve(self):
        return self.cir.solve(self.app.placed, self.leads, self.out.get(), self.vset.get(), [r.get() for r in self.rng])

    def raw(self, i):
        r = self.rng[i].get()
        if "dmm%d" % (i + 1) not in self.app.placed or r == "off":
            return None
        V, f = self.solve()
        c, v = V(f("C%d" % (i + 1))), V(f("V%d" % (i + 1)))
        g = self.ph.gain[i]
        if r[0] == "v" or r == "dio":
            return (v - c) * g
        if r[0] == "m":
            return (v - c) / (SHUNT[r] * self.ph.ish[i]) * 1e3 * g
        voc, ri = OHM[r]
        ix = (voc - (v - c)) / ri
        return (v - c) / ix * g if ix > 1e-12 else float("inf")

    def supply_i(self):
        if "psu" not in self.app.placed or not self.out.get():
            return 0.0
        V, f = self.solve()
        return (self.vset.get() - V(f("PY"))) / self.ph.Rlim

    def show(self, i):
        r = self.rng[i].get()
        if "dmm%d" % (i + 1) not in self.app.placed or r == "off":
            return ""
        R, v = RMAX[r], self.disp[i]
        if r[0] == "o":
            R2 = R / 1000
            if v != v or v == float("inf") or v / 1000 > R2 * 0.9995:
                return "1   "
            return ("%.3f" if R2 == 2 else "%.2f") % (v / 1000)
        if abs(v) > R * 0.9995:
            return "-1   " if v < 0 else "1   "
        s = ("%.3f" if R == 2 else "%.2f" if R == 20 else "%.1f") % abs(v)
        return ("-" if v < 0 and float(s) != 0 else "") + s

    @staticmethod
    def unit(r):
        return "V" if r[0] == "v" or r == "dio" else "mA" if r[0] == "m" else "kΩ" if r[0] == "o" else ""

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("직류 전원 장치 0–15 V", "DC power supply 0–15 V"))
        f.pack(fill="x", pady=2)
        self.dP = tk.Label(f, text="", font=("Courier", 16, "bold"), bg="#140b0b", fg="#ff4a3a", width=20)
        self.dP.pack(pady=2)
        ttk.Checkbutton(f, text="OUTPUT", variable=self.out).pack(anchor="w")
        stepper(f, T("전압", "Voltage"), [(t, (lambda d: lambda: self.nudge(d))(dv)) for t, dv in
                                         (("−1", -1), ("−0.1", -0.1), ("−0.01", -0.01), ("+0.01", 0.01), ("+0.1", 0.1), ("+1", 1))])
        ttk.Label(f, text=T("+ 소켓에는 제한 저항이 든 노란 도선이 꽂혀 있습니다. V 표시는 저항 앞의 전압입니다.",
                            "The yellow lead with the limiting resistor sits in the + socket. The V display is the voltage before the resistor."),
                  foreground="#555", wraplength=330).pack(anchor="w")
        self.dM = []
        for i in range(2):
            f = ttk.LabelFrame(ctl, text=T("멀티미터 %d (%s)" % (i + 1, "노랑" if i == 0 else "주황"), "Multimeter %d (%s)" % (i + 1, "yellow" if i == 0 else "orange")))
            f.pack(fill="x", pady=2)
            lab = tk.Label(f, text="", font=("Courier", 18, "bold"), bg="#9fae8f", fg="#1b1d20", width=12)
            lab.pack(pady=2)
            self.dM.append(lab)
            row = ttk.Frame(f)
            row.pack(fill="x")
            for j, (k, lb, _) in enumerate(RANGES):
                ttk.Radiobutton(row, text=lb, value=k, variable=self.rng[i], command=(lambda n: lambda: self.range_changed(n))(i)).grid(row=j // 5, column=j % 5, sticky="w", padx=2)
        ttk.Label(ctl, text=T("VΩmA 와 COM 단자를 씁니다. '1'만 보이면 범위 초과. mA 범위의 계기 저항: 2m 100 Ω, 20m 10 Ω, 200m 1 Ω.",
                              "Use the VΩmA and COM jacks. A lone '1' means over range. Meter resistance on mA: 2m 100 Ω, 20m 10 Ω, 200m 1 Ω."),
                  foreground="#555", wraplength=330).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("배선 — 단자 두 개를 골라 잇기", "Wiring — pick two terminals and join them"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        names = [tn(t) for t in TERMS]
        self.ta, self.tb = ttk.Combobox(row, values=names, width=14, state="readonly"), ttk.Combobox(row, values=names, width=14, state="readonly")
        self.ta.pack(side="left", padx=2)
        self.tb.pack(side="left", padx=2)
        ttk.Button(row, text=T("잇기", "Join"), command=self.join).pack(side="left", padx=2)
        self.lb = tk.Listbox(f, height=5)
        self.lb.pack(fill="x")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("고른 도선 뽑기", "Unplug selected"), command=self.unplug).pack(side="left", padx=2)
        ttk.Button(row, text=T("모두 뽑기", "Unplug all"), command=self.unplug_all).pack(side="left", padx=2)
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("메모", "Memo")).pack(side="left")
        self.cent = ttk.Entry(row, width=12)
        self.cent.pack(side="left", padx=2)
        ttk.Button(row, text=T("지금 읽은 값 적기", "Record the readings"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("c", T("메모", "memo"), 70), ("a", "DMM1", 90), ("b", "DMM2", 90), ("s", T("전원 V", "supply V"), 60)], height=6)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("배선 (위에서 본 모습) — 측정마다 회로도도 그리시오", "Wiring, from above — draw the circuit for each series too"),
                  font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=900, height=660, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    def nudge(self, dv):
        self.vset.set(max(0.0, min(self.ph.Vmax, round(self.vset.get() + dv, 2))))

    def range_changed(self, i):
        self.disp_t[i] = 0.0

    def join(self):
        names = [tn(t) for t in TERMS]
        a, b = self.ta.get(), self.tb.get()
        if a in names and b in names and a != b and len(self.leads) < 8 and "leads" in self.app.placed:
            ta, tb = TERMS[names.index(a)], TERMS[names.index(b)]
            self.leads.append((ta, tb))
            self.lb.insert("end", "%s — %s" % (a, b))

    def unplug(self):
        sel = self.lb.curselection()
        if sel:
            i = sel[0]
            del self.leads[i]
            self.lb.delete(i)

    def unplug_all(self):
        self.leads = []
        self.lb.delete(0, "end")

    def text_of(self, i):
        s = self.show(i)
        if not s:
            return "—"
        if s.endswith("   "):
            s = "-OL" if s[0] == "-" else "OL"
        return s + " " + self.unit(self.rng[i].get())

    def record(self):
        memo = self.cent.get() or ""
        self.sheet.add((memo or "—", self.text_of(0), self.text_of(1), "%.2f" % self.vset.get() if "psu" in self.app.placed else "—"))
        rg = [r.get() for r in self.rng]
        iv = [i for i in (0, 1) if rg[i][0] == "v"]
        im = [i for i in (0, 1) if rg[i][0] == "m"]
        if iv and im:
            sv, si = self.show(iv[0]), self.show(im[0])
            if sv and si and not sv.endswith("   ") and not si.endswith("   "):
                self.points.append((float(sv), float(si), memo))
                self.app.tab_graph.draw()

    def tick(self, dt):
        for i in range(2):
            self.disp_t[i] -= dt
            if self.disp_t[i] <= 0:
                self.disp_t[i] = 0.4
                r = self.raw(i)
                if r is not None:
                    rg = self.rng[i].get()
                    R = RMAX[rg]
                    lsd = (1.0 if R == 2000 else 10.0) if rg[0] == "o" else 0.001 if R == 2 else 0.01 if R == 20 else 0.1
                    self.disp[i] = r + (random.random() - 0.5) * 1.4 * lsd if r == r and r != float("inf") else r
        self.refresh()

    def refresh(self):
        self.ia = self.supply_i()
        self.dP.config(text=("%5.2f V  %.3f A" % (self.vset.get(), self.ia)) if "psu" in self.app.placed else "—")
        for i in range(2):
            self.dM[i].config(text=self.text_of(i) if self.show(i) else "")
        self.draw()

    def draw(self):
        cv, pl = self.cv, self.app.placed
        cv.delete("all")
        if "psu" in pl:
            cv.create_rectangle(40, 30, 380, 230, fill="#2a2d33", outline="#111", width=2)
            cv.create_text(210, 45, text="DC POWER SUPPLY  0–15 V", fill="#e8eef2", font=("Helvetica", 10, "bold"))
            cv.create_rectangle(60, 65, 200, 115, fill="#140b0b", outline="")
            cv.create_rectangle(220, 65, 360, 115, fill="#08120b", outline="")
            cv.create_text(190, 90, text="%5.2f" % self.vset.get(), fill="#ff4a3a", font=("Courier", 24, "bold"), anchor="e")
            cv.create_text(350, 90, text="%.3f" % self.ia, fill="#3dff7a", font=("Courier", 24, "bold"), anchor="e")
            cv.create_oval(80, 135, 130, 185, fill="#1b1d20", outline="#000")
            cv.create_rectangle(300, 140, 350, 170, fill="#46d36a" if self.out.get() else "#3b4a40", outline="#111")
            cv.create_text(325, 182, text="OUTPUT", fill="#cfd6dd", font=("Helvetica", 8, "bold"))
            cv.create_oval(180, 180, 200, 200, fill="#c0392b", outline="#111")
            cv.create_text(170, 190, text="+", fill="#ff8a7a", font=("Helvetica", 12, "bold"))
            cv.create_text(232, 190, text="−", fill="#cfd6dd", font=("Helvetica", 12, "bold"))
            cv.create_line(190, 190, 190, 330, fill="#e7c21a", width=4)
            cv.create_rectangle(182, 245, 198, 285, fill="#d8b315", outline="#8a7008")
            cv.create_text(205, 265, text=T("제한 저항", "limiting R"), anchor="w", font=("Helvetica", 9, "bold"), fill="#5a4700")
        else:
            cv.create_text(210, 130, text=T("조립 탭에서 전원 장치를 놓으시오", "Place the supply in the Assembly tab"), fill="#69717a")
        if "box" in pl:
            cv.create_rectangle(60, 400, 240, 540, fill="#1d1f23", outline="#000", width=2)
            cv.create_text(150, 455, text="BLACK BOX", fill="#e9e5da", font=("Helvetica", 14, "bold"))
            cv.create_text(150, 485, text=T("열지 마시오", "DO NOT OPEN"), fill="#e07a6a", font=("Helvetica", 9))
            cv.create_line(240, 460, 280, 460, 300, 420, 330, 420, smooth=True, fill="#e7c21a", width=4)
            cv.create_line(240, 480, 280, 480, 300, 520, 330, 520, smooth=True, fill="#2b6cd8", width=4)
        else:
            cv.create_text(150, 470, text=T("블랙박스를 놓으시오", "Place the black box"), fill="#69717a")
        for i, col in ((0, "#e3b72d"), (1, "#e0622e")):
            x0 = 560 + 190 * i
            if "dmm%d" % (i + 1) not in pl:
                cv.create_text(x0 + 70, 400, text=T("멀티미터 %d 를 놓으시오" % (i + 1), "Place multimeter %d" % (i + 1)), fill="#69717a")
                continue
            cv.create_rectangle(x0, 240, x0 + 140, 600, fill=col, outline="#5a3a12", width=2)
            cv.create_rectangle(x0 + 10, 250, x0 + 130, 590, fill="#2a2d33", outline="")
            cv.create_text(x0 + 70, 265, text="DMM %d" % (i + 1), fill="#e8eef2", font=("Helvetica", 10, "bold"))
            cv.create_rectangle(x0 + 18, 280, x0 + 122, 335, fill="#9fae8f", outline="")
            cv.create_text(x0 + 116, 308, text=self.show(i).replace("1   ", "1"), font=("Courier", 20, "bold"), anchor="e")
            lb = dict((k, l) for k, l, _ in RANGES)[self.rng[i].get()]
            cv.create_oval(x0 + 40, 380, x0 + 100, 440, fill="#1b1d20", outline="#000")
            cv.create_text(x0 + 70, 460, text=lb, fill="#ffcf3a", font=("Helvetica", 10, "bold"))
            cv.create_oval(x0 + 12, 553, x0 + 26, 567, fill="#c0392b", outline="#111")
            cv.create_text(x0 + 19, 540, text="10A", fill="#e8eef2", font=("Helvetica", 8))
            cv.create_text(x0 + 40, 540, text="VΩmA", fill="#e8eef2", font=("Helvetica", 8))
            cv.create_text(x0 + 100, 540, text="COM", fill="#e8eef2", font=("Helvetica", 8))
        for t, (x, y) in self.TP.items():
            here = ("box" in pl) if t in ("Y", "B") else ("psu" in pl) if t in ("PY", "PN") else ("dmm" + t[1]) in pl
            if not here:
                continue
            col = {"Y": "#e7c21a", "B": "#2b6cd8", "PY": "#e7c21a", "PN": "#1b1d20"}.get(t, "#c0392b" if t[0] == "V" else "#1f2226")
            cv.create_oval(x - 9, y - 9, x + 9, y + 9, fill=col, outline="#111", width=2)
            if t in ("Y", "B", "PY"):
                cv.create_text(x + 14, y, text=tn(t), anchor="w", font=("Helvetica", 9, "bold"))
        cols = ["#c0392b", "#1f2226", "#c0392b", "#1f2226", "#2f8f4e", "#8e44ad", "#d35400", "#16a085"]
        for i, (a, b) in enumerate(self.leads):
            (x0, y0), (x1, y1) = self.TP[a], self.TP[b]
            mx, my = (x0 + x1) / 2, max(y0, y1) + 30 + 5 * i
            cv.create_line(x0, y0, mx, my, x1, y1, smooth=True, fill=cols[i % len(cols)], width=3)


# --------------------------------------------------------------------------
#  Graph paper tab: the recorded (V, mA) pairs, coloured by memo
# --------------------------------------------------------------------------
class GraphTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        ttk.Label(self, text=T("모눈종이 — 한 멀티미터는 V⎓, 다른 하나는 mA 범위일 때 기록한 값이 점으로 찍힙니다 (메모가 같으면 같은 색).",
                               "Graph paper — readings recorded with one meter on V⎓ and the other on mA are plotted (same memo, same colour)."),
                  font=("Helvetica", 10, "bold")).pack(anchor="w", padx=6, pady=4)
        row = ttk.Frame(self)
        row.pack(anchor="w", padx=6)
        ttk.Button(row, text=T("점 모두 지우기", "Clear the points"), command=self.clear).pack(side="left")
        self.cv = tk.Canvas(self, width=1100, height=640, bg="#fbfaf4", highlightthickness=0)
        self.cv.pack(padx=6, pady=6)

    def clear(self):
        self.app.tab_bench.points = []
        self.draw()

    def draw(self):
        cv, P = self.cv, self.app.tab_bench.points
        cv.delete("all")
        L, R, Tp, B = 70, 1070, 30, 590

        def nice(v):
            e = 10 ** math.floor(math.log10(v))
            m = v / e
            return (1 if m <= 1 else 2 if m <= 2 else 5 if m <= 5 else 10) * e
        x0, x1, y0, y1 = 0.0, 1.0, 0.0, 1.0
        for v, i, _ in P:
            x0, x1, y0, y1 = min(x0, v), max(x1, v), min(y0, i), max(y1, i)
        xs, ys = nice((x1 - x0) / 10), nice((y1 - y0) / 8)
        x0, x1 = math.floor(x0 / xs) * xs, math.ceil(x1 / xs) * xs
        y0, y1 = math.floor(y0 / ys) * ys, math.ceil(y1 / ys) * ys
        X = lambda v: L + (v - x0) / (x1 - x0) * (R - L)
        Y = lambda v: B - (v - y0) / (y1 - y0) * (B - Tp)
        nx, ny = int(round((x1 - x0) / xs)) * 10, int(round((y1 - y0) / ys)) * 10
        for k in range(nx + 1):
            c = "#d6783c" if k % 10 == 0 else "#ebb995" if k % 5 == 0 else "#f6dcc8"
            cv.create_line(X(x0 + k * xs / 10), Tp, X(x0 + k * xs / 10), B, fill=c)
        for k in range(ny + 1):
            c = "#d6783c" if k % 10 == 0 else "#ebb995" if k % 5 == 0 else "#f6dcc8"
            cv.create_line(L, Y(y0 + k * ys / 10), R, Y(y0 + k * ys / 10), fill=c)
        cv.create_line(X(0), Tp, X(0), B, fill="#222", width=2)
        cv.create_line(L, Y(0), R, Y(0), fill="#222", width=2)
        for k in range(int(round((x1 - x0) / xs)) + 1):
            v = x0 + k * xs
            cv.create_text(X(v), B + 12, text=("%g" % round(v, 6)), font=("Helvetica", 9))
        for k in range(int(round((y1 - y0) / ys)) + 1):
            v = y0 + k * ys
            cv.create_text(L - 6, Y(v), text=("%g" % round(v, 6)), anchor="e", font=("Helvetica", 9))
        cv.create_text(R, B + 28, text="V (V)", anchor="e", font=("Helvetica", 11, "bold"))
        cv.create_text(L + 4, Tp + 10, text="I (mA)", anchor="w", font=("Helvetica", 11, "bold"))
        tags = []
        for _, _, g in P:
            if g not in tags:
                tags.append(g)
        cols = ["#1a4fb4", "#c0392b", "#2f8f4e", "#8e44ad", "#d35400", "#16a085"]
        for k, g in enumerate(tags):
            if len(tags) < 2 and not g:
                break
            y = Tp + 14 + 16 * k
            cv.create_text(R - 150, y, text="×  " + (g or "—"), anchor="w", fill=cols[k % 6], font=("Helvetica", 10, "bold"))
        for v, i, g in P:
            x, y, c = X(v), Y(i), cols[tags.index(g) % 6]
            cv.create_line(x - 4, y - 4, x + 4, y + 4, fill=c, width=2)
            cv.create_line(x - 4, y + 4, x + 4, y - 4, fill=c, width=2)
        if not P:
            cv.create_text(570, 320, text=T("아직 찍힌 점이 없습니다", "No points yet"), fill="#888", font=("Helvetica", 12))


def rr(cv, x0, y0, x1, y1, r, **kw):
    """rounded rectangle on a Tk canvas"""
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


# --------------------------------------------------------------------------
#  Assembly tab: drag each part from the list onto its place
# --------------------------------------------------------------------------
class AssemblyTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.placed = set()
        self.drag = None

        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Label(left, text=T("장치 목록", "Apparatus list"),
                  font=("Helvetica", 11, "bold")).pack(anchor="w")
        self.tray = tk.Canvas(left, width=215, height=640, bg="#f2f3f5",
                              highlightthickness=1,
                              highlightbackground="#c3c7cc")
        self.tray.pack()
        self.msg = ttk.Label(left, text="", wraplength=205,
                             foreground="#8a1b1b")
        self.msg.pack(anchor="w", pady=4)

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("조립 구역 — 장치를 끌어다 제자리에 놓으시오",
                                "Assembly area — drag each item to its place"),
                  font=("Helvetica", 11, "bold")).pack(anchor="w")
        self.scene = tk.Canvas(right, width=760, height=640, bg="#e9ebee",
                               highlightthickness=1,
                               highlightbackground="#c3c7cc")
        self.scene.pack(fill="both", expand=True)

        self.tray.bind("<ButtonPress-1>", self.on_press)
        self.tray.bind("<B1-Motion>", self.on_move)
        self.tray.bind("<ButtonRelease-1>", self.on_release)
        self.redraw()

    def redraw(self):
        self.tray.delete("all")
        pitch = min(60, 620 // len(PARTS))
        y, self.slots, self.half = 10 + pitch // 2, [], pitch // 2 - 2
        for key, lab, _ in PARTS:
            if key in self.placed:
                continue
            self.tray.create_rectangle(8, y - self.half, 205, y + self.half,
                                       fill="#ffffff", outline="#d3d7dc")
            ART[key](self.tray, 50, y, 0.5 * pitch / 60.0)
            self.tray.create_text(98, y, text=T(*lab), width=104,
                                  font=("Helvetica", 8), anchor="w")
            self.slots.append((key, y))
            y += pitch
        self.paint_scene()

    def paint_scene(self):
        cv = self.scene
        cv.delete("all")
        cv.create_text(380, 20, text=T(*SCENE_TITLE),
                       font=("Helvetica", 10, "bold"), fill="#4a5058")
        cv.create_rectangle(20, 470, 740, 500, fill="#d6d3c8", outline="")
        for key, (cx, cy, w, h) in ZONES.items():
            if key in self.placed:
                continue
            cv.create_rectangle(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2,
                                dash=(4, 3), outline="#b0b5bb")
        for key, _, _ in PARTS:
            if key in self.placed:
                cx, cy, w, h = ZONES[key]
                ART[key](cv, cx, cy, 1.0)
        if len(self.placed) == len(PARTS):
            cv.create_text(380, 610, fill="#14532d",
                           font=("Helvetica", 11, "bold"),
                           text=T("조립 완료 — '실험대' 탭으로 이동하시오.",
                                  "Assembly complete — go to the Bench tab."))

    def on_press(self, ev):
        self.drag = None
        for key, y in self.slots:
            if abs(ev.y - y) <= self.half:
                self.drag = key
                return

    def on_move(self, ev):
        if not self.drag:
            return
        x = self.tray.winfo_rootx() + ev.x - self.scene.winfo_rootx()
        y = self.tray.winfo_rooty() + ev.y - self.scene.winfo_rooty()
        self.paint_scene()
        ART[self.drag](self.scene, x, y, 0.9)

    def on_release(self, ev):
        if not self.drag:
            return
        key, self.drag = self.drag, None
        x = self.tray.winfo_rootx() + ev.x - self.scene.winfo_rootx()
        y = self.tray.winfo_rooty() + ev.y - self.scene.winfo_rooty()
        self.drop(key, x, y)

    def drop(self, key, x, y):
        cx, cy, w, h = ZONES[key]
        self.msg.config(text="")
        if not (abs(x - cx) < w / 2 + 28 and abs(y - cy) < h / 2 + 28):
            self.msg.config(text=T("그 위치에는 놓을 수 없습니다.",
                                   "That part does not belong there."))
            self.redraw()
            return False
        self.placed.add(key)
        self.app.on_assembly_change(self.placed)
        self.redraw()
        return True


# --------------------------------------------------------------------------
#  Data sheet: what the student wrote down, nothing more
# --------------------------------------------------------------------------
class DataSheet(ttk.Frame):
    def __init__(self, master, cols, height=12):
        ttk.Frame.__init__(self, master)
        self.cols = cols
        self.tv = ttk.Treeview(self, columns=[c[0] for c in cols],
                               show="headings", height=height)
        for key, head, wd in cols:
            self.tv.heading(key, text=head)
            self.tv.column(key, width=wd, anchor="center")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")

    def add(self, row):
        self.tv.insert("", "end", values=row)
        self.tv.yview_moveto(1.0)

    def del_last(self):
        kids = self.tv.get_children()
        if kids:
            self.tv.delete(kids[-1])

    def clear(self):
        for k in self.tv.get_children():
            self.tv.delete(k)

    def as_text(self):
        out = ["\t".join(c[1] for c in self.cols)]
        for k in self.tv.get_children():
            out.append("\t".join(str(v) for v in self.tv.item(k, "values")))
        return "\n".join(out)


def sheet_buttons(parent, sheet, app):
    row = ttk.Frame(parent)
    row.pack(fill="x", pady=2)
    ttk.Button(row, text=T("마지막 줄 삭제", "Delete last"),
               command=sheet.del_last).pack(side="left", padx=2)
    ttk.Button(row, text=T("모두 지우기", "Clear"),
               command=sheet.clear).pack(side="left", padx=2)

    def copy():
        app.clipboard_clear()
        app.clipboard_append(sheet.as_text())
    ttk.Button(row, text=T("표 복사", "Copy table"),
               command=copy).pack(side="left", padx=2)


def stepper(parent, label, cmds):
    """a row of buttons: label  [−1] [−0.1] … ; cmds = [(text, fn), …]"""
    row = ttk.Frame(parent)
    row.pack(fill="x", pady=1)
    ttk.Label(row, text=label, width=8).pack(side="left")
    for txt, fn in cmds:
        ttk.Button(row, text=txt, width=max(5, len(txt) + 1), command=fn).pack(side="left", padx=1)
    return row


class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.ph = Physics(seed)
        self.title(T(*APP_TITLE))
        self.geometry("1360x860")
        self.placed = set()
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_asm = AssemblyTab(nb, self)
        self.tab_bench = BenchTab(nb, self)
        self.tab_graph = GraphTab(nb, self)
        nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.tab_bench, text=T(" 실험대 ", " Bench "))
        nb.add(self.tab_graph, text=T(" 모눈종이 ", " Graph paper "))
        self.tab_graph.draw()
        self.after(40, self.tick)

    def on_assembly_change(self, placed):
        self.placed = set(placed)
        self.tab_bench.refresh()

    def tick(self):
        self.tab_bench.tick(0.04)
        self.after(40, self.tick)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
