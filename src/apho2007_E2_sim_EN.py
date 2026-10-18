#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  8th Asian Physics Olympiad  (APhO 2007, Shanghai, China)
  Experimental Problem 2 :  MEASUREMENT OF LIQUID ELECTRIC CONDUCTIVITY
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The sensor: two wound soft-iron rings forming a hollow cylinder.  Any
  conducting loop through it (the thread to the resistor box, the liquid
  in the cylinder) couples winding 11' to winding 22': V2/V1 = K |Y_loop|,
  with the loop's own reactance bending the curve at small R.
* You wire the circuit yourself, terminal to terminal; the voltmeter reads
  whatever two nets its leads end on (the induced emf is a quarter cycle
  behind the drive).  The resistor box puts resistors between neighbouring
  ports; extra leads short sections out.
* The generator amplitude wanders; the salt water layers and warms slowly
  unless stirred.  K, sigma and the loop reactance are never displayed.
* Hidden truths are randomised every session.  Standard library only.

    Run:   python3 apho2007_E2_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line

TERMS = ["G+", "G-", "V+", "V-", "SWc", "SW1", "SW2", "P0", "P1", "P2", "P3", "P4", "P5", "P6", "S1", "S1'", "S2", "S2'", "T1", "T2"]
RBOX = [0.1, 0.2, 0.5, 1, 2, 5]


# --------------------------------------------------------------------------
#  Physics core  (V, ohm, S, mm)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.K = 0.434 * r.uniform(0.95, 1.05)
        self.X, self.rl, self.Xl = r.uniform(0.26, 0.34), r.uniform(0.03, 0.06), r.uniform(0.2, 0.4)
        self.sig0 = r.uniform(1.2e-3, 2.2e-3)
        self.alT, self.T0, self.Troom = 0.021, r.uniform(10, 14), r.uniform(19, 23)
        self.Lmm, self.dmm = 30.5 * r.uniform(0.9995, 1.0005), 13.9 * r.uniform(0.9995, 1.0005)
        self.R = [v * (1 + r.uniform(-0.001, 0.001)) for v in RBOX]
        self.drift = r.uniform(0.012, 0.025)
        self.amp = self.ampTrue = 1.85
        self.Tl, self.strat = self.T0, 0.0

    def sigma(self):
        return self.sig0 * (1 + self.alT * (self.Tl - self.T0)) * (1 + self.strat)

    def Rliq(self):
        return self.Lmm / (self.sigma() * math.pi * self.dmm ** 2 / 4)

    def step(self, dt):
        self.ampTrue += (self.amp - self.ampTrue) * min(1, dt / 2) + self.drift / 60 * math.sqrt(dt) * random.uniform(-1.2, 1.2)
        self.Tl += (self.Troom - self.Tl) * dt / 5400
        self.strat = min(0.03, self.strat + dt * 0.012 / 600)


def make_nets(leads, sw):
    par = dict((t, t) for t in TERMS)

    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for a, b in leads + [("SWc", "SW1" if sw == 1 else "SW2")]:
        par[f(a)] = f(b)
    return f


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_box(cv, x, y, s=1.0):
    cv.create_rectangle(x - 80 * s, y - 40 * s, x + 80 * s, y + 40 * s, fill="#d9dcdf", outline="#8a8f96")
    cv.create_rectangle(x - 20 * s, y - 28 * s, x + 20 * s, y - 12 * s, fill="#0d1f12", outline="")
    for i in range(7):
        cv.create_oval(x - 60 * s + i * 20 * s - 4 * s, y + 24 * s - 4 * s, x - 60 * s + i * 20 * s + 4 * s, y + 24 * s + 4 * s, fill="#c9a64a", outline="")


def art_sensor(cv, x, y, s=1.0):
    cv.create_rectangle(x - 26 * s, y - 16 * s, x - 2 * s, y + 16 * s, fill="#7f868e", outline="#555")
    cv.create_rectangle(x + 2 * s, y - 16 * s, x + 26 * s, y + 16 * s, fill="#7f868e", outline="#555")


def art_beaker(cv, x, y, s=1.0):
    cv.create_rectangle(x - 26 * s, y - 32 * s, x + 26 * s, y + 32 * s, fill="#e1edf2", outline="#8fa7b4")
    cv.create_rectangle(x - 24 * s, y - 8 * s, x + 24 * s, y + 30 * s, fill="#aacde1", outline="")


def art_leads(cv, x, y, s=1.0):
    cv.create_oval(x - 20 * s, y - 10 * s, x + 20 * s, y + 10 * s, outline="#c0392b", width=2)
    cv.create_oval(x - 14 * s, y - 6 * s, x + 14 * s, y + 6 * s, outline="#1f2226", width=2)


ART = {"box": art_box, "sensor": art_sensor, "beaker": art_beaker, "leads": art_leads}
PARTS = [
    ("box",    ("[3] 측정 장치", "[3] Instrument"), []),
    ("sensor", ("[1] 전도도 센서", "[1] Conductivity sensor"), []),
    ("beaker", ("[2] 소금물 용기 + 젓개", "[2] Container + stirring rod"), []),
    ("leads",  ("[4] 도선", "[4] Leads"), ["box", "sensor"]),
]
ZONES = {"box": (260, 400, 160, 80), "sensor": (520, 380, 52, 32), "beaker": (640, 380, 52, 64), "leads": (400, 300, 40, 24)}
SCENE_TITLE = ("측정 장치, 센서, 소금물 용기", "Instrument, sensor and the container of salt water")
APP_TITLE = ("APhO 2007 실험 2 — 액체의 전기 전도도", "APhO 2007 Experiment 2 — Liquid electric conductivity")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.leads = []
        self.sw = tk.IntVar(value=1)
        self.inliq = tk.BooleanVar(value=False)
        self.build()
        self.refresh()

    def ok(self):
        return {"box", "sensor", "leads"} <= self.app.placed

    def thread_R(self, f):
        a, b = f("T1"), f("T2")
        if a == b:
            return 0.0
        ia = [i for i in range(7) if f("P%d" % i) == a]
        ib = [i for i in range(7) if f("P%d" % i) == b]
        if not ia or not ib:
            return float("inf")
        best = float("inf")
        for i in ia:
            for j in ib:
                r = sum(self.ph.R[k] for k in range(min(i, j), max(i, j)) if f("P%d" % k) != f("P%d" % (k + 1)))
                best = min(best, r)
        return best

    def meter(self):
        if not self.ok():
            return None
        ph, f = self.ph, make_nets(self.leads, self.sw.get())
        if f("G+") == f("G-"):
            return 0.0
        V1, pot = ph.ampTrue, {}
        pot[f("G-")] = 0j
        pot[f("G+")] = complex(V1, 0)
        drive = (f("S1") == f("G+") and f("S1'") == f("G-")) or (f("S1") == f("G-") and f("S1'") == f("G+"))
        flo = None
        if drive:
            y = 0j
            R = self.thread_R(f)
            if R != float("inf"):
                y += 1 / complex(R + ph.rl + 0.004 * len(self.leads), ph.X)
            if self.inliq.get():
                y += 1 / complex(ph.Rliq(), ph.Xl)
            e = complex(0, V1 * ph.K * abs(y))
            a, b = f("S2"), f("S2'")
            if b in pot and a not in pot:
                pot[a] = pot[b] + e
            elif a in pot and b not in pot:
                pot[b] = pot[a] - e
            elif a not in pot and b not in pot:
                pot[b], pot[a], flo = 0j, e, b
        p, m = f("V+"), f("V-")
        if p not in pot or m not in pot:
            return 0.0004 * random.random()
        if flo is not None and ((p == flo) != (m == flo)) and f("S2") not in (p, m):
            return 0.0004 * random.random()
        return abs(pot[p] - pot[m])

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("교류 디지털 전압계", "AC digital voltmeter"))
        f.pack(fill="x", pady=2)
        self.dV = tk.Label(f, text="", font=("Courier", 18, "bold"), bg="#0d1f12", fg="#5cff7a", width=12)
        self.dV.pack(pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("스위치:", "Switch:")).pack(side="left")
        ttk.Radiobutton(row, text="1", value=1, variable=self.sw).pack(side="left")
        ttk.Radiobutton(row, text="2", value=2, variable=self.sw).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("신호 발생기 진폭", "Generator amplitude"))
        f.pack(fill="x", pady=2)
        stepper(f, "", [("−0.1", lambda: self.amp(-0.1)), ("−0.01", lambda: self.amp(-0.01)), ("+0.01", lambda: self.amp(0.01)), ("+0.1", lambda: self.amp(0.1))])
        f = ttk.LabelFrame(ctl, text=T("배선 — 단자 두 개를 골라 잇기", "Wiring — pick two terminals and join them"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.ta, self.tb = ttk.Combobox(row, values=TERMS, width=6, state="readonly"), ttk.Combobox(row, values=TERMS, width=6, state="readonly")
        self.ta.pack(side="left", padx=2)
        self.tb.pack(side="left", padx=2)
        ttk.Button(row, text=T("잇기", "Join"), command=self.join).pack(side="left", padx=2)
        self.lb = tk.Listbox(f, height=8)
        self.lb.pack(fill="x")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("고른 도선 뽑기", "Unplug selected"), command=self.unplug).pack(side="left", padx=2)
        ttk.Button(row, text=T("모두 뽑기", "Unplug all"), command=self.unplug_all).pack(side="left", padx=2)
        f = ttk.LabelFrame(ctl, text=T("센서 · 소금물", "Sensor · salt water"))
        f.pack(fill="x", pady=2)
        ttk.Checkbutton(f, text=T("센서를 소금물에 담그기", "Sensor in the salt water"), variable=self.inliq).pack(anchor="w")
        ttk.Button(f, text=T("젓개로 젓기", "Stir"), command=self.stir).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text="R (Ω)").pack(side="left")
        self.rent = ttk.Entry(row, width=7)
        self.rent.pack(side="left", padx=2)
        ttk.Button(row, text=T("지금 읽은 값 적기", "Record the reading"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("R", "R (Ω)", 70), ("s", T("스위치", "switch"), 60), ("V", "V", 110)], height=6)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("배선판", "Wiring board"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=860, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    def amp(self, d):
        self.ph.amp = max(0.0, min(2.2, round(self.ph.amp + d, 2)))

    def join(self):
        a, b = self.ta.get(), self.tb.get()
        if a and b and a != b and len(self.leads) < 12:
            self.leads.append((a, b))
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

    def stir(self):
        self.ph.strat = random.uniform(-0.002, 0.002)

    def fmtV(self, v):
        if v is None:
            return ""
        return "%.3f V" % v if v >= 1 else ("%.1f mV" % (v * 1000) if v >= 0.1 else "%.2f mV" % (v * 1000))

    def record(self):
        self.sheet.add((self.rent.get() or "?", self.sw.get(), self.fmtV(self.meter())))

    def tick(self, dt):
        self.ph.step(dt)
        self.refresh()

    def refresh(self):
        self.dV.config(text=self.fmtV(self.meter()))
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        pos = {"G+": (70, 200), "G-": (120, 200), "V+": (220, 200), "V-": (270, 200), "SW1": (350, 140), "SWc": (380, 230), "SW2": (410, 140)}
        for i in range(7):
            pos["P%d" % i] = (70 + i * 62, 330)
        pos.update({"S1": (580, 120), "S1'": (630, 120), "S2": (700, 120), "S2'": (750, 120), "T1": (610, 420), "T2": (720, 420)})
        cv.create_rectangle(30, 70, 480, 380, fill="#d9dcdf", outline="#8a8f96", width=2)
        cv.create_text(95, 90, text=T("신호 발생기", "Generator"), font=("Helvetica", 10, "bold"))
        cv.create_text(245, 90, text=T("교류 전압계", "AC voltmeter"), font=("Helvetica", 10, "bold"))
        cv.create_rectangle(190, 105, 300, 145, fill="#0d1f12")
        cv.create_text(295, 125, anchor="e", text=self.fmtV(self.meter()), fill="#5cff7a", font=("Courier", 13, "bold"))
        cv.create_text(380, 90, text=T("스위치", "Switch"), font=("Helvetica", 10, "bold"))
        k = pos["SW1"] if self.sw.get() == 1 else pos["SW2"]
        cv.create_line(pos["SWc"][0], pos["SWc"][1], k[0], k[1] + 8, width=3, fill="#555")
        cv.create_text(255, 290, text=T("꽂는 저항 상자", "Plug-in resistor box"), font=("Helvetica", 10, "bold"))
        for i in range(6):
            a, b = pos["P%d" % i], pos["P%d" % (i + 1)]
            cv.create_rectangle(a[0] + 10, a[1] - 6, b[0] - 10, a[1] + 6, fill="#2b2e33")
            cv.create_text((a[0] + b[0]) / 2, a[1] + 20, text="%g Ω" % RBOX[i], font=("Helvetica", 9))
        cv.create_rectangle(560, 170, 655, 300, fill="#7f868e", outline="#555")
        cv.create_rectangle(675, 170, 770, 300, fill="#7f868e", outline="#555")
        cv.create_text(607, 235, text="1 1′", fill="#eee", font=("Helvetica", 11, "bold"))
        cv.create_text(722, 235, text="2 2′", fill="#eee", font=("Helvetica", 11, "bold"))
        cv.create_line(610, 420, 560, 260, 665, 240, 770, 260, 720, 420, smooth=True, fill="#b07a3a", width=2)
        cv.create_text(665, 470, text=T("센서: 소금물 속", "sensor: in salt water") if self.inliq.get() else T("센서: 공기 중", "sensor: in air"), font=("Helvetica", 10, "bold"))
        for t in TERMS:
            x, y = pos[t]
            neg = t.endswith("-") or t.endswith("'")
            col = "#c9a64a" if t[0] == "P" else ("#b07a3a" if t[0] == "T" else ("#1f2226" if neg else "#c0392b"))
            cv.create_oval(x - 8, y - 8, x + 8, y + 8, fill=col, outline="#111")
            cv.create_text(x, y - 16, text=t, font=("Helvetica", 9, "bold"))
        cols = ["#c0392b", "#1f2226", "#2b6cb0", "#d9a21b", "#2f8f4e", "#8e44ad"]
        for i, (a, b) in enumerate(self.leads):
            p, q = pos[a], pos[b]
            mx, my = (p[0] + q[0]) / 2, max(p[1], q[1]) + 40 + i * 4
            cv.create_line(p[0], p[1], mx, my, q[0], q[1], smooth=True, width=3, fill=cols[i % len(cols)])


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
