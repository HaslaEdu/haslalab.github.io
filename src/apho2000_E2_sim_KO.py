#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  1st Asian Physics Olympiad  (APhO 2000, Karawaci, Indonesia)
  Experimental Problem 2 :  DETERMINATION OF THE STEFAN-BOLTZMANN CONSTANT
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* A heater on a porcelain base warms an aluminium cylinder that covers
  it.  The cylinder loses heat by free convection (k dT^1.25), by
  radiation e*sigma*S*(T^4 - T0^4) and through the base; polished it
  hardly radiates, under candle soot it is nearly black.  Heater and
  cylinder are two bodies with their own heat capacities, so equilibrium
  takes 20-30 minutes (a speed control is provided).
* The DC supply, voltmeter, ammeter, heater, mV-meter and the iron-
  constantan thermocouple (reference junction in ice water) are wired by
  the student and solved as a dc network; the supply limits at 3 A.
* The thermocouple reading follows the NIST type-J polynomial; the
  student converts it with the table.  Cylinder size by vernier caliper.
* Hidden truths are randomised every session.
* Standard library only (tkinter).

    Run:   python3 apho2000_E2_sim_KO.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line

SIGMA = 5.670e-8
JC = [0, 5.0381187815e-2, 3.0475836930e-5, -8.5681065720e-8, 1.3228195295e-10, -1.7052958337e-13,
      2.0948090697e-16, -1.2538395336e-19, 1.5631725697e-23]
TERMS = ["PS+", "PS-", "H1", "H2", "A+", "A-", "V+", "V-", "M+", "M-", "J+", "J-"]


def emfJ(t):
    return sum(c * t ** i for i, c in enumerate(JC))


# --------------------------------------------------------------------------
#  Physics core  (SI)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.T0 = r.uniform(297.0, 300.0)
        self.Lmm = 60.0 * r.uniform(0.995, 1.005)
        self.Dmm = 12.5 * r.uniform(0.995, 1.005)
        self.kc = r.uniform(0.0145, 0.0175)
        self.epsP, self.epsB = r.uniform(0.03, 0.06), r.uniform(0.92, 0.97)
        self.kb = r.uniform(0.012, 0.020)
        self.G = r.uniform(0.50, 0.70)
        self.Ch, self.Cc = 45 * r.uniform(0.9, 1.1), 7.0
        self.R0, self.alR = 6.2 * r.uniform(0.97, 1.03), 4e-4
        self.tcOff = r.uniform(-0.010, 0.010)
        self.gV, self.gA, self.gM = r.uniform(0.997, 1.003), r.uniform(0.997, 1.003), r.uniform(0.998, 1.002)
        self.S = (math.pi * self.Dmm * self.Lmm + math.pi * self.Dmm ** 2 / 4) * 1e-6
        self.calE = r.uniform(-0.03, 0.03)
        self.Th = self.Tc = self.T0
        self.soot = 0.0

    def eps(self):
        return self.epsP + (self.epsB - self.epsP) * self.soot

    def Rh(self):
        return self.R0 * (1 + self.alR * (self.Th - 293))

    def tc_emf(self, junc):
        tref = 0.0 if junc else self.T0 - 273.15
        return emfJ(self.Tc - 273.15) - emfJ(tref) + self.tcOff

    def step(self, dt, P, on):
        T0 = self.T0
        q = self.G * (self.Th - self.Tc) if on else 0.0
        lossH = self.kb * (self.Th - T0) + (0 if on else 0.012 * max(0.0, self.Th - T0) ** 1.25 + 0.9 * SIGMA * 3e-4 * (self.Th ** 4 - T0 ** 4))
        d = self.Tc - T0
        lossC = self.kc * math.copysign(abs(d) ** 1.25, d) + self.eps() * SIGMA * self.S * (self.Tc ** 4 - T0 ** 4)
        self.Th += (P - q - lossH) / self.Ch * dt
        self.Tc += (q - lossC) / self.Cc * dt


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
def box_art(col, lab):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_rectangle(x - 26 * s, y - 34 * s, x + 26 * s, y + 34 * s, fill=col, outline="#555")
        cv.create_rectangle(x - 18 * s, y - 26 * s, x + 18 * s, y - 10 * s, fill="#9fae8f", outline="")
        cv.create_text(x, y + 10 * s, text=lab, fill="#fff", font=("Helvetica", max(7, int(10 * s)), "bold"))
    return art


def art_ps(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 50 * s, y - 36 * s, x + 50 * s, y + 36 * s, fill="#d9dcdf", outline="#8a8f96")
    cv.create_rectangle(x - 40 * s, y - 26 * s, x, y - 8 * s, fill="#0d1f12", outline="")
    cv.create_oval(x + 16 * s, y - 26 * s, x + 40 * s, y - 2 * s, fill="#1b1d20", outline="")


def art_heater(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 40 * s, y + 20 * s, x + 40 * s, y + 40 * s, fill="#efe9dc", outline="#a99f8a")
    cv.create_rectangle(x - 5 * s, y - 30 * s, x + 5 * s, y + 28 * s, fill="#d8cfbe", outline="#a99f8a")


def art_cyl(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 8 * s, y - 34 * s, x + 8 * s, y + 34 * s, fill="#d9dde1", outline="#777")


def art_ice(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 22 * s, y - 40 * s, x + 22 * s, y + 40 * s, fill="#2b6cb0", outline="#1b4c80")
    cv.create_text(x, y, text="0 °C", fill="#fff", font=("Helvetica", max(7, int(10 * s)), "bold"))


def art_caliper(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 60 * s, y - 6 * s, x + 60 * s, y + 4 * s, fill="#c9ced3", outline="#666")
    cv.create_rectangle(x - 60 * s, y - 6 * s, x - 52 * s, y + 24 * s, fill="#b9bfc4", outline="#666")
    cv.create_rectangle(x - 20 * s, y - 10 * s, x + 4 * s, y + 24 * s, fill="#aab0b6", outline="#555")


def art_candle(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 7 * s, y - 24 * s, x + 7 * s, y + 30 * s, fill="#f4efe2", outline="#bbb")
    cv.create_rectangle(x + 14 * s, y + 16 * s, x + 34 * s, y + 30 * s, fill="#c0392b", outline="")


def art_leads(cv, x, y, sc=1.0):
    s = sc
    for c, r in (("#c0392b", 26), ("#1f2226", 20), ("#2b6cb0", 14)):
        cv.create_oval(x - r * s, y - r * 0.6 * s, x + r * s, y + r * 0.6 * s, outline=c, width=2)


ART = {"ps": art_ps, "heater": art_heater, "cyl": art_cyl, "vm": box_art("#e3b72d", "V"), "am": box_art("#d9822b", "A"),
       "mv": box_art("#3a8fd5", "mV"), "ice": art_ice, "caliper": art_caliper, "candle": art_candle, "leads": art_leads}

PARTS = [
    ("ps",      ("[1] 직류 전원", "[1] DC power supply"), []),
    ("heater",  ("[2] 히터 (세라믹 받침)", "[2] Heater on a ceramic base"), []),
    ("cyl",     ("[5] 알루미늄 원통 (열전대)", "[5] Aluminium cylinder (thermocouple)"), ["heater"]),
    ("vm",      ("[3] 디지털 전압계 V", "[3] Digital voltmeter V"), []),
    ("am",      ("[3] 디지털 전류계 A", "[3] Digital ammeter A"), []),
    ("mv",      ("[7] 디지털 mV계", "[7] Digital mV-meter"), []),
    ("ice",     ("[6] 얼음물 (기준 접점)", "[6] Ice water (reference junction)"), ["cyl"]),
    ("caliper", ("[4] 캘리퍼스", "[4] Caliper"), []),
    ("candle",  ("[10] 양초와 성냥", "[10] Candle and matches"), []),
    ("leads",   ("[9] 전선", "[9] Electric cables"), []),
]
ZONES = {
    "ps": (130, 250, 110, 80), "heater": (330, 290, 90, 80), "cyl": (330, 230, 30, 70), "vm": (480, 250, 60, 75), "am": (560, 250, 60, 75),
    "mv": (640, 250, 60, 75), "ice": (430, 380, 50, 85), "caliper": (180, 430, 130, 40), "candle": (650, 400, 60, 70), "leads": (540, 420, 70, 40),
}
SCENE_TITLE = ("실험대 — 전원, 히터와 원통, 계기, 얼음물", "The bench — supply, heater and cylinder, meters, ice water")
APP_TITLE = ("APhO 2000 실험 2 — 스테판–볼츠만 상수", "APhO 2000 Experiment 2 — Determination of the Stefan-Boltzmann constant")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.leads = []
        self.vset = tk.DoubleVar(value=0.0)
        self.out = tk.BooleanVar(value=False)
        self.on = tk.BooleanVar(value=True)       # cylinder over the heater
        self.junc = tk.BooleanVar(value=False)
        self.lit = tk.BooleanVar(value=False)
        self.speed = tk.IntVar(value=1)
        self.cal = tk.StringVar(value="L")
        self.t = 0.0
        self.disp, self.disp_t = {"v": None, "a": None, "m": None}, 0.0
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def solve(self, limit=False):
        ph, f = self.ph, make_nets(self.leads)
        el = []
        emf = self.vset.get() if (self.out.get() and self.has("ps")) else 0.0
        if self.has("ps"):
            el.append((f("PS-"), f("PS+"), 1e-6, 3.0) if limit else (f("PS-"), f("PS+"), 1 / 0.05, emf / 0.05))
        if self.has("heater"):
            el.append((f("H1"), f("H2"), 1 / ph.Rh(), 0.0))
        if self.has("am"):
            el.append((f("A+"), f("A-"), 1 / 0.05, 0.0))
        if self.has("vm"):
            el.append((f("V+"), f("V-"), 1e-7, 0.0))
        if self.has("mv"):
            el.append((f("M+"), f("M-"), 1e-7, 0.0))
        if self.has("cyl") and self.has("ice"):
            e = ph.tc_emf(self.junc.get()) * 1e-3
            el.append((f("J-"), f("J+"), 1 / 12.0, e / 12.0))
        gnd = f("PS-")
        names = []
        for p, q, _, _ in el:
            for n in (p, q):
                if n != gnd and n not in names:
                    names.append(n)
        idx = dict((n, i) for i, n in enumerate(names))
        N = len(names)
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
        x = rsolve(A, b) if N else []
        V = lambda n: 0.0 if n == gnd else (x[idx[n]] if n in idx else 0.0)
        if not limit and self.has("ps"):
            I = (emf - (V(f("PS+")) - V(f("PS-")))) / 0.05
            if I > 3.0:
                return self.solve(True)
        return V, f

    def readings(self):
        V, f = self.solve()
        ph = self.ph
        Vh = V(f("H1")) - V(f("H2"))
        return {"v": (V(f("V+")) - V(f("V-"))) * ph.gV if self.has("vm") else None,
                "a": (V(f("A+")) - V(f("A-"))) / 0.05 * ph.gA if self.has("am") else None,
                "m": (V(f("M+")) - V(f("M-"))) * 1e3 * ph.gM if self.has("mv") else None,
                "P": Vh * Vh / ph.Rh(), "I": Vh / ph.Rh()}

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("계기", "Meters"))
        f.pack(fill="x", pady=2)
        self.lbl = {}
        for k, unit in (("v", "V"), ("a", "A"), ("m", "mV")):
            self.lbl[k] = tk.Label(f, text="", font=("Courier", 17, "bold"), bg="#9fae8f", fg="#1b1d20", width=12)
            self.lbl[k].pack(pady=1)
        f = ttk.LabelFrame(ctl, text=T("직류 전원 (0–15 V, 3 A)", "DC supply (0-15 V, 3 A)"))
        f.pack(fill="x", pady=2)
        self.vlbl = ttk.Label(f, text="")
        self.vlbl.pack(anchor="w")
        stepper(f, "", [("−1 V", lambda: self.dv(-1)), ("−0.1", lambda: self.dv(-0.1)), ("+0.1", lambda: self.dv(0.1)), ("+1 V", lambda: self.dv(1))])
        ttk.Checkbutton(f, text="OUTPUT", variable=self.out).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("원통 · 열전대 · 양초", "Cylinder · thermocouple · candle"))
        f.pack(fill="x", pady=2)
        ttk.Checkbutton(f, text=T("원통을 히터에 씌움", "Cylinder over the heater"), variable=self.on, command=self.toggle_on).pack(anchor="w")
        ttk.Checkbutton(f, text=T("기준 접점을 얼음물에", "Reference junction in the ice"), variable=self.junc).pack(anchor="w")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Checkbutton(row, text=T("촛불 켜기", "Candle lit"), variable=self.lit).pack(side="left")
        ttk.Button(row, text=T("불꽃에 그을리기", "Soot it in the flame"), command=self.soot).pack(side="left", padx=4)
        f = ttk.LabelFrame(ctl, text=T("배선 — 단자 두 개를 골라 잇기", "Wiring — pick two terminals and join them"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.ta, self.tb = ttk.Combobox(row, values=TERMS, width=5, state="readonly"), ttk.Combobox(row, values=TERMS, width=5, state="readonly")
        self.ta.pack(side="left", padx=2)
        self.tb.pack(side="left", padx=2)
        ttk.Button(row, text=T("잇기", "Join"), command=self.join).pack(side="left", padx=2)
        self.lb = tk.Listbox(f, height=6)
        self.lb.pack(fill="x")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("고른 전선 뽑기", "Unplug selected"), command=self.unplug).pack(side="left", padx=2)
        ttk.Button(row, text=T("모두 뽑기", "Unplug all"), command=self.unplug_all).pack(side="left", padx=2)
        f = ttk.LabelFrame(ctl, text=T("시간", "Time"))
        f.pack(fill="x", pady=2)
        self.clk = ttk.Label(f, text="", font=("Courier", 14, "bold"))
        self.clk.pack(side="left")
        for s in (1, 10, 30, 60):
            ttk.Radiobutton(f, text="×%d" % s, value=s, variable=self.speed).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.note = ttk.Entry(row, width=16)
        self.note.pack(side="left", padx=2)
        ttk.Button(row, text=T("지금 값 적기", "Record the readings"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("t", T("시간", "time"), 60), ("v", "V", 55), ("a", "A", 55), ("m", "mV", 60), ("n", T("메모", "note"), 90)], height=5)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=330)
        self.warn.pack(anchor="w")
        right = ttk.Notebook(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        fr = ttk.Frame(right)
        right.add(fr, text=T("배선", "Wiring"))
        self.cv = tk.Canvas(fr, width=760, height=600, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()
        fr = ttk.Frame(right)
        right.add(fr, text=T("열전대 표 (J형)", "Thermocouple table (type J)"))
        tv = tk.Text(fr, width=96, height=36, font=("Courier", 9))
        tv.pack(fill="both", expand=True)
        tv.insert("end", T("J형 열전대 기전력 (mV), 기준 접점 0 °C\n\n", "Type J thermocouple emf (mV), reference junction at 0 °C\n\n"))
        tv.insert("end", "  °C " + "".join("%8d" % c for c in range(10)) + "\n")
        for r in range(31):
            tv.insert("end", "%5d" % (r * 10) + "".join("%8.3f" % emfJ(r * 10 + c) for c in range(10)) + "\n")
        tv.config(state="disabled")
        fr = ttk.Frame(right)
        right.add(fr, text=T("캘리퍼스", "Caliper"))
        row = ttk.Frame(fr)
        row.pack(fill="x")
        ttk.Radiobutton(row, text=T("길이", "Length"), value="L", variable=self.cal).pack(side="left")
        ttk.Radiobutton(row, text=T("바깥 지름", "Outside diameter"), value="D", variable=self.cal).pack(side="left")
        self.cc = tk.Canvas(fr, width=760, height=300, bg="#15181d", highlightthickness=0)
        self.cc.pack()

    def toggle_on(self):
        if self.ph.Tc > 323 or self.ph.Th > 323:
            self.on.set(not self.on.get())
            self.warn.config(text=T("너무 뜨겁습니다 — 식을 때까지 기다리시오.", "Too hot to handle: wait until it cools."))

    def soot(self):
        if self.on.get() or not self.lit.get() or not self.has("candle"):
            self.warn.config(text=T("원통을 히터에서 내리고 촛불을 켜시오.", "Take the cylinder off the heater and light the candle."))
            return
        self.ph.soot = min(1.0, self.ph.soot + (1 - self.ph.soot) * 0.35)
        self.ph.Tc += 6

    def dv(self, d):
        self.vset.set(max(0.0, min(15.0, round(self.vset.get() + d, 1))))

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

    def unplug_all(self):
        self.leads = []
        self.lb.delete(0, "end")

    def show(self, k):
        v = self.disp[k]
        if v is None:
            return "—"
        lim = 199.99 if k == "m" else 19.99
        if abs(v) > lim:
            return "1"
        return "%.2f" % v

    def record(self):
        self.sheet.add((self.clock(), self.show("v"), self.show("a"), self.show("m"), self.note.get()))

    def clock(self):
        t = int(self.t)
        return "%02d:%02d" % (t // 60, t % 60) if t < 3600 else "%d:%02d:%02d" % (t // 3600, t // 60 % 60, t % 60)

    def tick(self, dt):
        dt *= self.speed.get()
        self.t += dt
        r = self.readings()
        n = max(1, int(dt / 0.05))
        for _ in range(n):
            self.ph.step(dt / n, max(0.0, r["P"]), self.on.get() and self.has("cyl"))
        self.disp_t -= dt / self.speed.get()
        if self.disp_t <= 0:
            self.disp_t = 0.5
            r = self.readings()
            for k in ("v", "a", "m"):
                self.disp[k] = None if r[k] is None else r[k] + (random.random() - 0.5) * 0.016
        msgs = []
        if abs(r["I"]) > 2.0:
            msgs.append(T("히터 전류가 2 A를 넘었습니다!", "The heater current is above 2 A!"))
        if self.has("ice") and not self.junc.get():
            msgs.append(T("기준 접점이 얼음물에 있지 않습니다.", "The reference junction is not in the ice."))
        self.warn.config(text="\n".join(msgs))
        self.refresh()

    def refresh(self):
        for k, u in (("v", " V"), ("a", " A"), ("m", " mV")):
            self.lbl[k].config(text=self.show(k) + u)
        self.vlbl.config(text=T("설정 전압: ", "Set: ") + "%.1f V" % self.vset.get())
        self.clk.config(text=self.clock() + "  ")
        self.draw()
        self.draw_cal()

    TP = {"PS+": (90, 230), "PS-": (150, 230), "H1": (300, 230), "H2": (380, 230), "J+": (520, 230), "J-": (580, 230),
          "A+": (140, 500), "A-": (80, 500), "V+": (370, 500), "V-": (310, 500), "M+": (600, 500), "M-": (540, 500)}

    def draw(self):
        cv = self.cv
        cv.delete("all")
        boxes = (("ps", 40, 60, 200, 260, "#d9dcdf", T("직류 전원", "DC supply")), ("heater", 260, 60, 420, 260, "#efe9dc", T("히터 + 원통", "heater + cylinder")),
                 ("ice", 480, 60, 620, 260, "#2b6cb0", T("얼음물", "ice water")), ("am", 40, 330, 180, 530, "#d9822b", "A"),
                 ("vm", 270, 330, 410, 530, "#e3b72d", "V"), ("mv", 500, 330, 640, 530, "#3a8fd5", "mV"))
        for k, x0, y0, x1, y1, col, lab in boxes:
            if not self.has(k):
                continue
            cv.create_rectangle(x0, y0, x1, y1, fill=col, outline="#555", width=2)
            cv.create_text((x0 + x1) / 2, y0 + 20, text=lab, font=("Helvetica", 11, "bold"), fill="#111" if k in ("ps", "heater") else "#fff")
        if self.has("heater") and self.has("cyl") and self.on.get():
            s = self.ph.soot
            c = "#%02x%02x%02x" % (int(217 - 190 * s), int(221 - 195 * s), int(225 - 198 * s))
            cv.create_rectangle(325, 90, 355, 190, fill=c, outline="#777")
        for t, (x, y) in self.TP.items():
            own = {"P": "ps", "H": "heater", "J": "ice", "A": "am", "V": "vm", "M": "mv"}[t[0]]
            if not self.has(own):
                continue
            col = "#c0392b" if t.endswith("+") or t == "H1" else "#1f2226"
            cv.create_oval(x - 8, y - 8, x + 8, y + 8, fill=col, outline="#111")
            cv.create_text(x, y - 16, text=t, font=("Helvetica", 9, "bold"))
        cols = ["#c0392b", "#1f2226", "#2b6cb0", "#d9a21b", "#2f8f4e", "#8e44ad", "#16a085", "#7f8c8d"]
        for i, (a, b) in enumerate(self.leads):
            (x0, y0), (x1, y1) = self.TP[a], self.TP[b]
            mx, my = (x0 + x1) / 2, max(y0, y1) + 30 + 5 * i
            cv.create_line(x0, y0, mx, my, x1, y1, smooth=True, fill=cols[i % len(cols)], width=3)
        cv.create_text(700, 80, text=T("실온", "Room"), font=("Helvetica", 10, "bold"))
        cv.create_text(700, 100, text="%.1f °C" % (self.ph.T0 - 273.15), font=("Courier", 13, "bold"), fill="#c0392b")

    def draw_cal(self):
        cv = self.cc
        cv.delete("all")
        ph = self.ph
        if not (self.has("caliper") and self.has("cyl")):
            return
        if self.on.get() and ph.Tc > 330:
            cv.create_text(380, 150, text=T("원통이 뜨겁습니다", "the cylinder is hot"), fill="#f0b35a")
            return
        read = (ph.Lmm if self.cal.get() == "L" else ph.Dmm) + ph.calE
        ppm, X = 6.8, (lambda mm: 50 + mm * 6.8)
        cv.create_rectangle(20, 60, 740, 106, fill="#d4d8dc", outline="#666")
        for mm in range(0, 101):
            x = X(mm)
            ln = 20 if mm % 10 == 0 else 14 if mm % 5 == 0 else 9
            cv.create_line(x, 106, x, 106 - ln, fill="#111")
            if mm % 10 == 0:
                cv.create_text(x, 74, text=str(mm // 10), font=("Helvetica", 11, "bold"))
        cv.create_rectangle(X(0), 120, X(read), 200, fill="#d9dde1", outline="#555")
        s0 = X(read)
        cv.create_rectangle(s0 - 30, 104, s0 + 40 * ppm + 40, 150, fill="#b8bec4", outline="#555")
        for i in range(21):
            x = s0 + i * 1.95 * ppm
            cv.create_line(x, 106, x, 106 + (16 if i % 2 == 0 else 10), fill="#111")
            if i % 2 == 0:
                cv.create_text(x, 132, text=str(i // 2), font=("Helvetica", 9))


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
