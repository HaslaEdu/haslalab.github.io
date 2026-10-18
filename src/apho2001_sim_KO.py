#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  2nd Asian Physics Olympiad  (APhO 2001, Taipei, Taiwan)
  Experimental Problem :  BASIC CHARACTERISTICS OF SOLAR CELLS
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The solar cell (a-Si:H module) is a diode with series and shunt
  resistance: I = Iph - I0(exp(beta(V + I Rs)) - 1) - (V + I Rs)/Rsh.
  Any wiring of the cell, the 3 V battery, the 10-turn 0-5 kohm resistor
  and the two multimeters (V or mA, with their own resistance) is solved
  by Newton's method.  The resistor burns if its wiper carries the
  battery straight across a small section.
* The light: the lamp's photocurrent falls as (30+a)^2/(d+a)^2 with the
  lamp-to-window distance d; filters (cut-offs 587, 557, 470 nm) and two
  polarizers (Malus's law, leaky below about 470 nm) act on a flat
  spectral response that ends at the hidden lambda0.
* beta, I0, Rs, Rsh, Iph and lambda0 are hidden and randomised.
* Standard library only (tkinter).

    Run:   python3 apho2001_sim_KO.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line

TERMS = ["C+", "C-", "B+", "B-", "R1", "RW", "R2", "M1+", "M1-", "M2+", "M2-"]
FILTERS = {"R": 587.0, "O": 557.0, "Y": 470.0}
MODES = {"off": None, "v2": (1e7, 1.999, "V"), "v20": (1e7, 19.99, "V"), "ma2": (100.0, 1.999, "mA"), "ma20": (10.0, 19.99, "mA")}


def fT(k, l):
    return 0.92 / (1 + math.exp(-(l - FILTERS[k]) / 5.5))


def leak(l):
    return 0.03 + 0.97 / (1 + math.exp((l - 462) / 11.0))


# --------------------------------------------------------------------------
#  Physics core  (V, A, ohm, nm, cm)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.beta = r.uniform(4.2, 6.8)
        self.Voc30 = r.uniform(2.75, 3.10)
        self.Iph30 = r.uniform(2.6, 4.0) * 1e-3
        self.Rs, self.Rsh = r.uniform(30, 80), r.uniform(25e3, 70e3)
        self.lam0 = r.uniform(735, 765)
        self.a0, self.room = 3.0, 0.004
        self.vBat, self.rBat = 3.0 * r.uniform(1.02, 1.06), r.uniform(0.4, 0.9)
        self.Rpot, self.tPol = 5000 * r.uniform(0.995, 1.005), r.uniform(0.32, 0.37)
        self.gM = [r.uniform(0.997, 1.003), r.uniform(0.997, 1.003)]
        self.I0 = self.Iph30 / (math.exp(self.beta * self.Voc30) - 1)

    def resp(self, l):
        if l < 400:
            return 0.0
        return max(0.0, min(1.0, (self.lam0 - l) / 22.0)) * ((l - 400) / 30.0 if l < 430 else 1.0)

    def light(self, lamp_on, d, filt, p1, p2, pol, cover, blocked):
        """photocurrent as a share of the bare lamp at 30 cm"""
        if cover:
            return 0.0
        lamp = 0.0
        if lamp_on and d > 1 and not blocked:
            geo = ((30 + self.a0) / (d + self.a0)) ** 2
            th = math.radians(pol)
            num = den = 0.0
            for l in range(380, 822, 2):
                rr = self.resp(l)
                den += rr
                t = 1.0
                for k in filt:
                    t *= fT(k, l)
                if p1 and p2:
                    t *= self.tPol * (math.cos(th) ** 2 + leak(l) * math.sin(th) ** 2)
                elif p1 or p2:
                    t *= math.sqrt(self.tPol) * 1.05
                num += rr * t
            lamp = geo * num / den
        return lamp + self.room

    def cellI(self, V, Iph):
        I = Iph
        for _ in range(60):
            u = V + I * self.Rs
            e = math.exp(min(60.0, self.beta * u))
            f = I - Iph + self.I0 * (e - 1) + u / self.Rsh
            fp = 1 + self.Rs * (self.I0 * self.beta * e + 1 / self.Rsh)
            dI = f / fp
            I -= dI
            if abs(dI) < 1e-13:
                break
        u = V + I * self.Rs
        g = self.I0 * self.beta * math.exp(min(60.0, self.beta * u)) + 1 / self.Rsh
        return I, -g / (1 + self.Rs * g)


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


def rsolve(A, b):
    n = len(b)
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(A[r][i]))
        A[i], A[p] = A[p], A[i]
        b[i], b[p] = b[p], b[i]
        for r in range(i + 1, n):
            k = A[r][i] / A[i][i]
            for c in range(i, n):
                A[r][c] -= k * A[i][c]
            b[r] -= k * b[i]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (b[i] - sum(A[i][c] * x[c] for c in range(i + 1, n))) / A[i][i]
    return x


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_rail(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 90 * s, y - 6 * s, x + 90 * s, y + 6 * s, fill="#3b4047", outline="#222")
    for i in range(10):
        cv.create_line(x - 85 * s + i * 19 * s, y - 6 * s, x - 85 * s + i * 19 * s, y, fill="#e8eef2")


def art_lamp(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 20 * s, y - 30 * s, x + 14 * s, y, fill="#e9ecef", outline="#888")
    cv.create_oval(x + 8 * s, y - 24 * s, x + 20 * s, y - 6 * s, fill="#fff4c8", outline="")
    cv.create_rectangle(x - 4 * s, y, x + 2 * s, y + 30 * s, fill="#b9bfc4", outline="")


def art_box(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 30 * s, y - 24 * s, x + 30 * s, y + 2 * s, fill="#1b1d20", outline="#555")
    cv.create_rectangle(x - 30 * s, y - 18 * s, x - 24 * s, y - 4 * s, fill="#3b3a6a", outline="")
    cv.create_rectangle(x - 3 * s, y + 2 * s, x + 3 * s, y + 30 * s, fill="#b9bfc4", outline="")


def art_mount(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 16 * s, y - 34 * s, x + 16 * s, y - 2 * s, fill="#2b2e33", outline="")
    cv.create_oval(x - 9 * s, y - 27 * s, x + 9 * s, y - 9 * s, fill="#f2d02c", outline="")
    cv.create_rectangle(x - 3 * s, y - 2 * s, x + 3 * s, y + 30 * s, fill="#b9bfc4", outline="")


def art_filters(cv, x, y, sc=1.0):
    s = sc
    for i, c in enumerate(("#d23a2a", "#ee8a24", "#f2d02c", "#555", "#555")):
        cv.create_oval(x - 46 * s + i * 20 * s, y - 9 * s, x - 30 * s + i * 20 * s, y + 9 * s, fill=c, outline="#222")


def art_shield(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 6 * s, y - 34 * s, x + 6 * s, y + 34 * s, fill="#11151a", outline="#444")


def art_bat(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 30 * s, y - 16 * s, x + 30 * s, y + 16 * s, fill="#1b1d20", outline="#444")
    cv.create_rectangle(x - 26 * s, y - 12 * s, x + 26 * s, y - 2 * s, fill="#c8a24c", outline="")
    cv.create_rectangle(x - 26 * s, y + 2 * s, x + 26 * s, y + 12 * s, fill="#c8a24c", outline="")


def art_pot(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 30 * s, y - 22 * s, x + 30 * s, y + 22 * s, fill="#2b6cb0", outline="#1b4c80")
    cv.create_oval(x - 14 * s, y - 14 * s, x + 14 * s, y + 14 * s, fill="#1b1d20", outline="")


def dmm_art(col):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_rectangle(x - 26 * s, y - 40 * s, x + 26 * s, y + 40 * s, fill=col, outline="#555")
        cv.create_rectangle(x - 18 * s, y - 32 * s, x + 18 * s, y - 14 * s, fill="#9fae8f", outline="")
        cv.create_oval(x - 12 * s, y - 6 * s, x + 12 * s, y + 18 * s, fill="#1b1d20", outline="")
    return art


def art_leads(cv, x, y, sc=1.0):
    s = sc
    for c, r in (("#c0392b", 26), ("#1f2226", 20), ("#2b6cb0", 14)):
        cv.create_oval(x - r * s, y - r * 0.6 * s, x + r * s, y + r * 0.6 * s, outline=c, width=2)


ART = {"rail": art_rail, "lamp": art_lamp, "box": art_box, "mount": art_mount, "filters": art_filters, "shield": art_shield,
       "bat": art_bat, "pot": art_pot, "dmm1": dmm_art("#e3b72d"), "dmm2": dmm_art("#3a8fd5"), "leads": art_leads}

PARTS = [
    ("rail",    ("[9] 광학대", "[9] Optical bench"), []),
    ("lamp",    ("[5] 백색 광원", "[5] White light source"), ["rail"]),
    ("box",     ("[1] 태양전지 상자", "[1] Solar cell box"), ["rail"]),
    ("mount",   ("[8] 광학 거치대", "[8] Optical mount"), ["rail"]),
    ("filters", ("[6][7] 필터 3장 · 편광판 2장", "[6][7] 3 filters · 2 polarizers"), ["mount"]),
    ("shield",  ("[13] 차광판", "[13] Light-shielding boards"), []),
    ("bat",     ("[3] 건전지 1.5 V × 2", "[3] Dry cells 1.5 V × 2"), []),
    ("pot",     ("[4] 정밀 가변저항 0–5 kΩ", "[4] Precision resistor 0-5 kohm"), []),
    ("dmm1",    ("[2] 멀티미터 1", "[2] Multimeter 1"), []),
    ("dmm2",    ("[2] 멀티미터 2", "[2] Multimeter 2"), []),
    ("leads",   ("[10] 연결 도선 (스프링)", "[10] Leads (springs)"), []),
]
ZONES = {
    "rail": (380, 200, 200, 20), "lamp": (240, 160, 50, 60), "box": (500, 160, 70, 60), "mount": (370, 160, 40, 70), "filters": (370, 90, 110, 30),
    "shield": (650, 160, 30, 80), "bat": (180, 380, 70, 40), "pot": (300, 380, 70, 50), "dmm1": (440, 380, 60, 90), "dmm2": (540, 380, 60, 90), "leads": (660, 380, 70, 40),
}
SCENE_TITLE = ("광학대 위의 광원·거치대·태양전지, 앞에는 회로 부품", "Lamp, mount and cell on the bench; the circuit parts in front")
APP_TITLE = ("APhO 2001 실험 — 태양전지의 기본 특성", "APhO 2001 Experiment — Basic characteristics of solar cells")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.leads = []
        self.lamp = tk.BooleanVar(value=False)
        self.dist = 30.0                     # lamp-to-window distance as set on the bench, cm
        self.filt = dict((k, tk.BooleanVar(value=False)) for k in ("R", "O", "Y"))
        self.p1, self.p2 = tk.BooleanVar(value=False), tk.BooleanVar(value=False)
        self.pol = 0
        self.shade = tk.StringVar(value="none")
        self.turns = 5.0
        self.burnt = False
        self.mode = [tk.StringVar(value="off"), tk.StringVar(value="off")]
        self.disp, self.disp_t = [0.0, 0.0], 0.0
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def solve(self):
        ph, f, el = self.ph, make_nets(self.leads), []
        if self.has("bat"):
            el.append((f("B-"), f("B+"), 1 / ph.rBat, ph.vBat / ph.rBat))
        if self.has("pot") and not self.burnt:
            x = self.turns / 10.0
            ra, rb = max(0.5, x * ph.Rpot), max(0.5, (1 - x) * ph.Rpot)
            el.append((f("R1"), f("RW"), 1 / ra, 0.0))
            el.append((f("RW"), f("R2"), 1 / rb, 0.0))
        for i in range(2):
            m = MODES[self.mode[i].get()]
            if self.has("dmm%d" % (i + 1)) and m:
                el.append((f("M%d+" % (i + 1)), f("M%d-" % (i + 1)), 1 / m[0], 0.0))
        cell = (f("C+"), f("C-")) if self.has("box") else None
        filt = [k for k in "ROY" if self.filt[k].get()] if self.has("filters") else []
        Iph = ph.Iph30 * ph.light(self.lamp.get() and self.has("lamp"), self.dist, filt, self.p1.get() and self.has("filters"),
                                  self.p2.get() and self.has("filters"), self.pol, self.shade.get() == "cover", self.shade.get() == "block") if cell else 0.0
        gnd = cell[1] if cell else f("B-")
        names = []
        for p, q, _, _ in el:
            for n in (p, q):
                if n != gnd and n not in names:
                    names.append(n)
        if cell and cell[0] != gnd and cell[0] not in names:
            names.append(cell[0])
        idx = dict((n, i) for i, n in enumerate(names))
        N = len(names)
        x = [0.0] * N
        V = lambda n: 0.0 if n == gnd else (x[idx[n]] if n in idx else 0.0)
        for _ in range(80):
            if not N:
                break
            A = [[1e-9 if i == j else 0.0 for j in range(N)] for i in range(N)]
            b = [0.0] * N
            for p, q, g, I in el:
                i, j = idx.get(p), idx.get(q)
                if i is not None:
                    A[i][i] += g
                    b[i] -= I
                if j is not None:
                    A[j][j] += g
                    b[j] += I
                if i is not None and j is not None:
                    A[i][j] -= g
                    A[j][i] -= g
            if cell and cell[0] != cell[1]:
                v = V(cell[0]) - V(cell[1])
                I, dIdV = ph.cellI(v, Iph)
                g, Ieq = -dIdV, I - dIdV * v
                i, j = idx.get(cell[0]), idx.get(cell[1])
                if i is not None:
                    A[i][i] += g
                    b[i] += Ieq
                if j is not None:
                    A[j][j] += g
                    b[j] -= Ieq
                if i is not None and j is not None:
                    A[i][j] -= g
                    A[j][i] -= g
            xn = rsolve(A, b)
            dmax = 0.0
            for k in range(N):
                dx = max(-0.3, min(0.3, xn[k] - x[k]))
                x[k] += dx
                dmax = max(dmax, abs(dx))
            if dmax < 1e-9:
                break
        return V, f

    def raw(self, i):
        m = MODES[self.mode[i].get()]
        if not self.has("dmm%d" % (i + 1)) or not m:
            return None
        V, f = self.solve()
        v = V(f("M%d+" % (i + 1))) - V(f("M%d-" % (i + 1)))
        return (v if m[2] == "V" else v / m[0] * 1e3) * self.ph.gM[i]

    def pot_power(self):
        if not self.has("pot") or self.burnt:
            return 0.0
        V, f = self.solve()
        x = self.turns / 10.0
        ra, rb = max(0.5, x * self.ph.Rpot), max(0.5, (1 - x) * self.ph.Rpot)
        v1, v2 = V(f("R1")) - V(f("RW")), V(f("RW")) - V(f("R2"))
        return max(v1 * v1 / ra, v2 * v2 / rb)

    def show(self, i):
        m = MODES[self.mode[i].get()]
        if not self.has("dmm%d" % (i + 1)) or not m:
            return "—"
        v = self.disp[i]
        if abs(v) > m[1]:
            return "1"
        return ("%.3f" if m[1] < 2 else "%.2f") % v + " " + m[2]

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("멀티미터", "Multimeters"))
        f.pack(fill="x", pady=2)
        self.lbl = []
        for i in range(2):
            row = ttk.Frame(f)
            row.pack(fill="x")
            l = tk.Label(row, text="", font=("Courier", 15, "bold"), bg="#9fae8f", fg="#1b1d20", width=11)
            l.pack(side="left", pady=1)
            self.lbl.append(l)
            for md, lab in (("off", "OFF"), ("v2", "V2"), ("v20", "V20"), ("ma2", "mA2"), ("ma20", "mA20")):
                ttk.Radiobutton(row, text=lab, value=md, variable=self.mode[i]).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("광원 · 광학대", "Lamp · bench"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Checkbutton(row, text=T("광원 켜기", "Lamp on"), variable=self.lamp).pack(side="left")
        ttk.Radiobutton(row, text=T("가림 없음", "Open"), value="none", variable=self.shade).pack(side="left")
        ttk.Radiobutton(row, text=T("차광판으로 빛 막기", "Board in the beam"), value="block", variable=self.shade).pack(side="left")
        ttk.Radiobutton(row, text=T("상자 창 덮기", "Cover the window"), value="cover", variable=self.shade).pack(side="left")
        stepper(f, T("상자 옮기기", "Move the box"), [("−5", lambda: self.mv(-5)), ("−0.5", lambda: self.mv(-0.5)), ("+0.5", lambda: self.mv(0.5)), ("+5", lambda: self.mv(5))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        for k, lab in (("R", T("빨강", "red")), ("O", T("주황", "orange")), ("Y", T("노랑", "yellow"))):
            ttk.Checkbutton(row, text=lab, variable=self.filt[k]).pack(side="left")
        ttk.Checkbutton(row, text=T("편광판1", "pol 1"), variable=self.p1).pack(side="left")
        ttk.Checkbutton(row, text=T("편광판2", "pol 2"), variable=self.p2).pack(side="left")
        stepper(f, T("편광판2 각도", "Polarizer 2"), [("−5°", lambda: self.rot(-5)), ("−1°", lambda: self.rot(-1)), ("+1°", lambda: self.rot(1)), ("+5°", lambda: self.rot(5))])
        f = ttk.LabelFrame(ctl, text=T("정밀 가변저항 (10회전, 0–5 kΩ)", "Precision resistor (10 turns, 0-5 kohm)"))
        f.pack(fill="x", pady=2)
        self.potl = ttk.Label(f, text="")
        self.potl.pack(anchor="w")
        stepper(f, "", [("−1", lambda: self.turn(-1)), ("−0.1", lambda: self.turn(-0.1)), ("−0.01", lambda: self.turn(-0.01)), ("+0.01", lambda: self.turn(0.01)), ("+0.1", lambda: self.turn(0.1)), ("+1", lambda: self.turn(1))])
        ttk.Button(f, text=T("새 가변저항 받기", "Ask for a new resistor"), command=self.new_pot).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("배선 — 단자 두 개를 골라 잇기", "Wiring — pick two terminals and join them"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.ta, self.tb = ttk.Combobox(row, values=TERMS, width=5, state="readonly"), ttk.Combobox(row, values=TERMS, width=5, state="readonly")
        self.ta.pack(side="left", padx=2)
        self.tb.pack(side="left", padx=2)
        ttk.Button(row, text=T("잇기", "Join"), command=self.join).pack(side="left", padx=2)
        ttk.Button(row, text=T("고른 것 뽑기", "Unplug"), command=self.unplug).pack(side="left", padx=2)
        self.lb = tk.Listbox(f, height=5)
        self.lb.pack(fill="x")
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.note = ttk.Entry(row, width=16)
        self.note.pack(side="left", padx=2)
        ttk.Button(row, text=T("지금 값 적기", "Record"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("a", T("멀티미터 1", "meter 1"), 90), ("b", T("멀티미터 2", "meter 2"), 90), ("n", T("메모", "note"), 110)], height=4)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=380)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("광학대와 회로", "The optical bench and the circuit"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    def mv(self, d):
        self.dist = max(8.0, min(65.0, round(self.dist + d, 1)))

    def rot(self, d):
        self.pol = (self.pol + d) % 360

    def turn(self, d):
        if not self.burnt:
            self.turns = max(0.0, min(10.0, round(self.turns + d, 2)))

    def new_pot(self):
        self.burnt = False

    def join(self):
        a, b = self.ta.get(), self.tb.get()
        if a and b and a != b and len(self.leads) < 12 and self.has("leads"):
            self.leads.append((a, b))
            self.lb.insert("end", "%s — %s" % (a, b))

    def unplug(self):
        sel = self.lb.curselection()
        if sel:
            del self.leads[sel[0]]
            self.lb.delete(sel[0])

    def record(self):
        self.sheet.add((self.show(0), self.show(1), self.note.get()))

    def tick(self, dt):
        self.disp_t -= dt
        if self.disp_t <= 0:
            self.disp_t = 0.4
            for i in range(2):
                r = self.raw(i)
                if r is not None:
                    m = MODES[self.mode[i].get()]
                    self.disp[i] = r + (random.random() - 0.5) * 1.2 * (0.001 if m[1] < 2 else 0.01)
            if self.pot_power() > 0.25:
                self.burnt = True
        msgs = []
        if self.burnt:
            msgs.append(T("가변저항이 타 버렸습니다 (가운데 단자를 건전지에 바로 이었나요?)", "The resistor burnt out (was the wiper wired straight to the battery?)"))
        for i in range(2):
            if self.show(i) == "1":
                msgs.append(T("멀티미터 %d: 범위 초과" % (i + 1), "Multimeter %d: over range" % (i + 1)))
        self.warn.config(text="\n".join(msgs))
        self.refresh()

    def refresh(self):
        for i in range(2):
            self.lbl[i].config(text=self.show(i))
        self.potl.config(text=T("다이얼: ", "Dial: ") + ("--" if self.burnt else "%.2f" % self.turns) + T(" 회전   ·   편광판2: ", " turns   ·   polarizer 2: ") + "%d°" % self.pol)
        self.draw()

    TP = {"C+": (560, 316), "C-": (610, 316), "B+": (110, 470), "B-": (60, 470), "R1": (240, 470), "RW": (290, 470), "R2": (340, 470),
          "M1+": (480, 600), "M1-": (420, 600), "M2+": (660, 600), "M2-": (600, 600)}

    def draw(self):
        cv = self.cv
        cv.delete("all")
        if self.has("rail"):
            z, x0 = 9.0, 60
            cv.create_rectangle(x0 - 9, 250, x0 + 71 * z, 268, fill="#3b4047", outline="")
            for c in range(0, 71):
                ln = 12 if c % 10 == 0 else 8 if c % 5 == 0 else 4
                cv.create_line(x0 + c * z, 250, x0 + c * z, 250 + ln, fill="#e8eef2")
                if c % 10 == 0:
                    cv.create_text(x0 + c * z, 262 + 4, text=str(c), fill="#e8eef2", font=("Helvetica", 8))
            lx, bx, mx = x0 + 2 * z, x0 + (2 + self.dist) * z, x0 + (2 + self.dist * 0.45) * z
            if self.has("lamp"):
                cv.create_rectangle(lx - 25, 150, lx + 25, 200, fill="#e9ecef", outline="#777")
                cv.create_rectangle(lx + 22, 160, lx + 27, 190, fill="#fff4c8" if self.lamp.get() else "#5a5f66", outline="")
                cv.create_line(lx, 200, lx, 250, fill="#b9bfc4", width=5)
                if self.lamp.get() and self.has("box") and self.shade.get() == "none":
                    cv.create_polygon(lx + 27, 166, bx, 158, bx, 192, lx + 27, 184, fill="#f7ecc0", outline="")
            if self.has("mount"):
                cv.create_rectangle(mx - 5, 150, mx + 5, 200, fill="#2b2e33", outline="")
                k0 = 0
                for k, col in (("R", "#d23a2a"), ("O", "#ee8a24"), ("Y", "#f2d02c")):
                    if self.has("filters") and self.filt[k].get():
                        cv.create_rectangle(mx - 4 + 3 * k0, 154, mx - 2 + 3 * k0, 196, fill=col, outline="")
                        k0 += 1
                cv.create_line(mx, 200, mx, 250, fill="#b9bfc4", width=5)
            if self.has("box"):
                cv.create_rectangle(bx, 150, bx + 9 * z, 200, fill="#1b1d20", outline="#555")
                cv.create_rectangle(bx - 2, 158, bx + 2, 192, fill="#11151a" if self.shade.get() == "cover" else "#3b3a6a", outline="")
                cv.create_line(bx + 4.5 * z, 200, bx + 4.5 * z, 250, fill="#b9bfc4", width=5)
                cv.create_line(bx, 140, bx, 275, fill="#e0a800", dash=(3, 3))
            if self.shade.get() == "block":
                sx = (lx + bx) / 2 + 40
                cv.create_rectangle(sx - 3, 110, sx + 3, 230, fill="#11151a", outline="")
        boxes = (("box", 520, 280, 650, 330, "#1b1d20", T("태양전지", "solar cell")), ("bat", 30, 400, 140, 490, "#1b1d20", "1.5 V × 2"),
                 ("pot", 210, 400, 370, 490, "#2b6cb0", "0–5 kΩ"), ("dmm1", 390, 520, 510, 630, "#e3b72d", "M1"), ("dmm2", 570, 520, 690, 630, "#3a8fd5", "M2"))
        for k, x0, y0, x1, y1, col, lab in boxes:
            if self.has(k):
                cv.create_rectangle(x0, y0, x1, y1, fill=col, outline="#555", width=2)
                cv.create_text((x0 + x1) / 2, y0 + 12, text=lab, fill="#fff", font=("Helvetica", 9, "bold"))
        own = {"C": "box", "B": "bat", "R": "pot"}
        for t, (x, y) in self.TP.items():
            k = own.get(t[0]) or ("dmm1" if t[1] == "1" else "dmm2")
            if not self.has(k):
                continue
            col = "#c0392b" if t.endswith("+") or t == "RW" else "#1f2226" if t.endswith("-") else "#c9a64a"
            cv.create_oval(x - 8, y - 8, x + 8, y + 8, fill=col, outline="#111")
            cv.create_text(x, y - 15, text=t, font=("Helvetica", 8, "bold"))
        cols = ["#c0392b", "#1f2226", "#2b6cb0", "#d9a21b", "#2f8f4e", "#8e44ad", "#16a085", "#7f8c8d"]
        for i, (a, b) in enumerate(self.leads):
            (x0, y0), (x1, y1) = self.TP[a], self.TP[b]
            cv.create_line(x0, y0, (x0 + x1) / 2, max(y0, y1) + 30 + 5 * i, x1, y1, smooth=True, fill=cols[i % len(cols)], width=3)
        cv.create_text(380, 60, text=T("광원–상자 창 거리는 광학대 눈금으로 읽으시오.", "Read the lamp-to-window distance on the bench scale."), fill="#555")


def T(ko, en):
    return ko if LANG == "ko" else en


def rr(cv, x0, y0, x1, y1, r, **kw):
    """rounded rectangle on a Tk canvas"""
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


# --------------------------------------------------------------------------
#  Assembly tab: drag each part from the list onto its place, in order
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
        ttk.Label(right, text=T("조립 구역 — 준비 절차 순서대로 놓으시오",
                                "Assembly area — follow the preparation order"),
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
        pitch = min(60, 620 // len(PARTS))     # every part fits in the list
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
        needs = dict((k, n) for k, _, n in PARTS)[key]
        miss = [n for n in needs if n not in self.placed]
        if miss:
            names = ", ".join(T(*dict((k, l) for k, l, _ in PARTS)[m])
                              for m in miss)
            self.msg.config(text=T("먼저 설치해야 합니다: ",
                                   "Install first: ") + names)
            self.redraw()
            return False
        self.placed.add(key)
        self.app.on_assembly_change(self.placed)
        self.redraw()
        return True


# --------------------------------------------------------------------------
#  Data sheet: what the student typed down, nothing more
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
    ttk.Label(row, text=label, width=16).pack(side="left")
    for txt, fn in cmds:
        ttk.Button(row, text=txt, width=max(6, len(txt) + 1), command=fn).pack(side="left", padx=1)
    return row


class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.ph = Physics(seed)
        self.title(T(*APP_TITLE))
        self.geometry("1360x800")
        self.placed = set()
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_asm = AssemblyTab(nb, self)
        self.tab_bench = BenchTab(nb, self)
        nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.tab_bench, text=T(" 실험대 ", " Bench "))
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
