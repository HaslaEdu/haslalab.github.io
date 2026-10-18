#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  39th International Physics Olympiad  (IPhO 2008, Hanoi, Vietnam)
  Experimental Problem :  DIFFERENTIAL THERMOMETRIC METHOD
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* Two silicon diodes, each fed about 0.84 mA by the circuit box (9 V,
  10 kohm), drop V(T) = V(T0) - alpha (T - T0) with alpha close to
  2.00 mV/C.  The box shows Delta V = V2 - V1 and V2 on two sockets.
* Task 1: the lamp turned up heats a steel plate under the dish holder;
  the reference dish D1 stays empty, the sample dish D2 holds 20 mg of
  a substance that solidifies at the hidden Ts.  The plate, the dishes
  and the substance (latent heat on its plateau) are integrated in
  time; draughts stir the open dishes when the cover is off.
* Task 2: the lamp hangs at height d.  The cone detector (C = 0.69 J/K,
  hidden loss k) warms as C dT/dt = E pi R^2 - k (T - T0); the solar
  cell (diode with Rs, Rsh) feeds the variable resistor through the
  20 mA range (10 ohm).
* Ts, the latent heat, V(T0), alpha, k, E at 12 cm and the cell are
  hidden and randomised.
* Standard library only (tkinter).

    Run:   python3 ipho2008_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line


# --------------------------------------------------------------------------
#  Physics core
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.r = r
        self.T0 = r.uniform(24.5, 28.0)
        self.V1 = r.uniform(0.555, 0.590)
        self.V2 = self.V1 + r.uniform(-0.02, 0.02)
        self.a1, self.a2 = r.uniform(1.97e-3, 2.03e-3), r.uniform(1.97e-3, 2.03e-3)
        self.Ts, self.latent = r.uniform(52, 68), r.uniform(1.6, 2.4)
        self.gR, self.gS = r.uniform(0.046, 0.054), r.uniform(0.046, 0.054)
        self.E12 = r.uniform(125, 155)
        self.Cdet, self.kdet, self.Rdet = r.uniform(0.67, 0.71), r.uniform(6.6e-3, 8.4e-3), r.uniform(12.6, 13.4) * 1e-3
        self.cw, self.ch = r.uniform(18.6, 19.4) * 1e-3, r.uniform(23.6, 24.4) * 1e-3
        self.Iph140 = r.uniform(10.8, 12.4) * 1e-3
        self.nVt, self.Rs, self.Rsh = r.uniform(0.038, 0.043), r.uniform(2.5, 4.0), r.uniform(800, 1500)
        self.I0 = self.Iph140 * math.exp(-r.uniform(0.475, 0.50) / self.nVt)
        self.Rpot = 330 * r.uniform(0.97, 1.03)
        self.reset()

    def reset(self):
        T0 = self.T0
        self.glass, self.Tp, self.T1, self.T2, self.H2 = T0, T0, T0, T0, 0.0
        self.Tc, self.Tw = T0, T0

    def irradiance(self, lamp_on, d):
        glow = 1.0 if lamp_on else max(0.0, (self.glass - self.T0) / 120) * 0.22
        return self.E12 * glow * ((12 + 2.5) / (d + 2.5)) ** 2

    def step(self, dt, lamp_on, lamp_up, holder, poured, cover, det_under, d):
        T0 = self.T0
        self.glass += ((T0 + 150 if lamp_on else T0) - self.glass) * dt / 25
        on_lamp = holder and lamp_up
        self.Tp += ((18 if on_lamp and lamp_on else 0) - 0.15 * (self.Tp - T0)) * dt / (120 if on_lamp else 30)
        air = 0 if cover else (self.r.random() - 0.5) * 0.9
        CS, h = 0.5 + (0.04 if poured else 0), 0.004
        self.T1 += (self.gR * (self.Tp - self.T1) - h * (self.T1 - T0) + air * 0.004) * dt / 0.5
        q = (self.gS * (self.Tp - self.T2) - h * (self.T2 - T0) + air * 0.004) * dt
        if poured:
            if q > 0 and self.T2 >= self.Ts and self.H2 < 1:
                use = min(q, (1 - self.H2) * self.latent)
                self.H2 += use / self.latent
                q -= use
            elif q < 0 and self.T2 <= self.Ts and self.H2 > 0:
                use = min(-q, self.H2 * self.latent)
                self.H2 -= use / self.latent
                q += use
        self.T2 += q / CS
        if poured and 0 < self.H2 < 1:
            self.T2 = self.Ts
        E = self.irradiance(lamp_on, d) if det_under else 0.0
        self.Tc += (E * math.pi * self.Rdet ** 2 - self.kdet * (self.Tc - T0)) * dt / self.Cdet
        self.Tw += ((0.02 * E / 140) - (self.Tw - T0) / 60) * dt / 5

    def drops(self, Ta, Tb):
        """the two diodes' voltages at the box's sockets (about 0.84 mA through each, 15 ohm in each junction)"""
        i = (9.3 - 0.57) / 1e4
        return (self.V1 - self.a1 * (Ta - self.T0) + 15 * i, self.V2 - self.a2 * (Tb - self.T0) + 15 * i)

    def cell_I(self, V, Iph):
        I = Iph
        for _ in range(80):
            u = V + I * self.Rs
            e = math.exp(min(60, u / self.nVt))
            f = I - Iph + self.I0 * (e - 1) + u / self.Rsh
            fp = 1 + self.Rs * (self.I0 * e / self.nVt + 1 / self.Rsh)
            dI = f / fp
            I -= dI
            if abs(dI) < 1e-14:
                break
        return I

    def cell_load(self, Iph, R):
        """the cell across R (ohm): its voltage and current"""
        lo, hi = 0.0, 0.8
        for _ in range(80):
            v = (lo + hi) / 2
            if self.cell_I(v, Iph) > v / R:
                lo = v
            else:
                hi = v
        return v, v / R


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def box_art(col, w, h):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_rectangle(x - w * s, y - h * s, x + w * s, y + h * s, fill=col, outline="#555")
    return art


def art_lamp(cv, x, y, sc=1.0):
    s = sc
    cv.create_line(x - 20 * s, y + 30 * s, x - 20 * s, y - 30 * s, fill="#888", width=max(1, 3 * s))
    cv.create_polygon(x - 32 * s, y - 22 * s, x + 32 * s, y - 22 * s, x + 14 * s, y - 2 * s, x - 14 * s, y - 2 * s, fill="#c9ccd1", outline="#777")
    cv.create_rectangle(x - 34 * s, y + 30 * s, x - 6 * s, y + 36 * s, fill="#2a2d33", outline="")


def art_round(col, r):
    def art(cv, x, y, sc=1.0):
        cv.create_oval(x - r * sc, y - r * sc, x + r * sc, y + r * sc, fill=col, outline="#555")
    return art


ART = {"lamp": art_lamp, "holder": box_art("#6b4a2b", 34, 8), "cover": box_art("#9aa1a8", 36, 14), "ampoule": box_art("#f4f1e6", 4, 16),
       "detector": art_round("#d3d5d8", 18), "cell": box_art("#1d2c5c", 16, 20), "box": box_art("#2f5fa8", 38, 18), "pot": art_round("#2a2d33", 12),
       "dmm1": box_art("#e3b72d", 22, 34), "dmm2": box_art("#3a86d0", 22, 34), "watch": art_round("#2a2d33", 14), "ruler": box_art("#f0efe8", 60, 5)}
PARTS = [
    ("lamp",     ("[1] 할로겐 램프 20 W (갓·스탠드)", "[1] Halogen lamp 20 W (shade, stand)"), []),
    ("holder",   ("[2] 접시 받침 (D1 기준, D2 시료)", "[2] Dish holder (D1 reference, D2 sample)"), ["lamp"]),
    ("cover",    ("[3] 회색 덮개 상자", "[3] Grey cover box"), ["holder"]),
    ("ampoule",  ("[4] 시료 앰플 (약 20 mg)", "[4] Sample ampoule (about 20 mg)"), ["holder"]),
    ("detector", ("[5] 복사 검출기 (원뿔)", "[5] Radiation detector (cone)"), ["lamp"]),
    ("cell",     ("[6] 태양전지", "[6] Solar cell"), ["lamp"]),
    ("box",      ("[7] 회로 상자 (9 V)", "[7] Circuit box (9 V)"), []),
    ("pot",      ("[8] 가변저항", "[8] Variable resistor"), []),
    ("dmm1",     ("[9] 멀티미터 1", "[9] Multimeter 1"), ["box"]),
    ("dmm2",     ("[9] 멀티미터 2", "[9] Multimeter 2"), ["box"]),
    ("watch",    ("[10] 스톱워치", "[10] Stopwatch"), []),
    ("ruler",    ("[11] 자 (30 cm)", "[11] Ruler (30 cm)"), []),
]
ZONES = {"lamp": (150, 250, 80, 90), "holder": (170, 340, 70, 20), "cover": (170, 300, 76, 34), "ampoule": (60, 330, 14, 36),
         "detector": (300, 380, 40, 40), "cell": (380, 380, 36, 44), "box": (520, 160, 80, 40), "pot": (660, 160, 30, 30),
         "dmm1": (480, 300, 50, 72), "dmm2": (580, 300, 50, 72), "watch": (680, 300, 30, 30), "ruler": (560, 420, 124, 14)}
SCENE_TITLE = ("램프 · 접시 받침 · 검출기 · 태양전지 · 회로 상자 · 멀티미터", "Lamp · dish holder · detector · solar cell · circuit box · multimeters")
APP_TITLE = ("IPhO 2008 실험 — 시차 열측정법", "IPhO 2008 Experiment — Differential thermometric method")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.job = tk.StringVar(value="holder")       # what stands at the lamp: holder / detector / cell
        self.lamp = tk.BooleanVar(value=False)
        self.cover = tk.BooleanVar(value=False)
        self.poured = False
        self.d = 16.0
        self.pot = 0.5
        self.speed = tk.IntVar(value=1)
        self.watch_run, self.watch_t = False, 0.0
        self.disp, self.disp_t = [0.0, 0.0], 0.0
        self.trace = []
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def lamp_up(self):
        return self.job.get() == "holder"

    def at_lamp(self):
        k = self.job.get()
        return k if self.has("lamp") and self.has(k) else None

    def raw(self):
        """the two meters: (Delta V, V2) in mV, or (cell V in mV, cell I in mA)"""
        ph, out = self.ph, [None, None]
        k = self.at_lamp()
        if k == "cell":
            E = ph.irradiance(self.lamp.get(), self.d) if self.has("lamp") else 0.0
            Iph = ph.Iph140 * E / 140 + ph.Iph140 * 0.002
            v, i = ph.cell_load(Iph, max(0.3, self.pot * ph.Rpot) + 10.0)
            if self.has("dmm1"):
                out[0] = v * 1e3
            if self.has("dmm2"):
                out[1] = i * 1e3
            return out
        if not self.has("box") or k is None:
            return out
        if k == "holder":
            v1, v2 = ph.drops(ph.T1, ph.T2)
        else:
            v1, v2 = ph.drops(ph.Tw, ph.Tc)
        if self.has("dmm1"):
            out[0] = (v2 - v1) * 1e3
        if self.has("dmm2"):
            out[1] = v2 * 1e3
        return out

    def show(self, i):
        if not self.has("dmm%d" % (i + 1)):
            return "—"
        v = self.disp[i]
        if self.at_lamp() == "cell":
            return ("%.0f mV" % v) if i == 0 else ("%.2f mA" % v)
        if i == 0:
            return "1" if abs(v) > 199.9 else "%.1f mV" % v
        return "%.0f mV" % v

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("멀티미터", "Multimeters"))
        f.pack(fill="x", pady=2)
        self.lbl = [tk.Label(f, text="", font=("Courier", 16, "bold"), bg="#9fae8f", fg="#1b1d20", width=18) for _ in range(2)]
        for w in self.lbl:
            w.pack(anchor="w", pady=1)
        self.what = ttk.Label(f, text="", foreground="#4a5058")
        self.what.pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("램프 아래에 둘 것", "What stands at the lamp"))
        f.pack(fill="x", pady=2)
        for v, lab in (("holder", T("접시 받침 (램프 뒤집어 열원)", "Dish holder (lamp turned up as heater)")),
                       ("detector", T("복사 검출기 (램프 매달기)", "Detector (lamp hanging)")),
                       ("cell", T("태양전지 (램프 매달기)", "Solar cell (lamp hanging)"))):
            ttk.Radiobutton(f, text=lab, value=v, variable=self.job, command=self.rejob).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("램프 · 시료", "Lamp · sample"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Checkbutton(row, text=T("램프 켜기", "Lamp on"), variable=self.lamp).pack(side="left")
        ttk.Checkbutton(row, text=T("덮개 덮기", "Cover on"), variable=self.cover).pack(side="left", padx=6)
        ttk.Button(row, text=T("시료를 D2에 붓기", "Pour sample into D2"), command=self.pour).pack(side="left")
        stepper(f, T("매단 높이 d", "Hanging height d"), [("−1 cm", lambda: self.hd(-1)), ("−1 mm", lambda: self.hd(-0.1)), ("+1 mm", lambda: self.hd(0.1)), ("+1 cm", lambda: self.hd(1))])
        stepper(f, T("가변저항 손잡이", "Resistor knob"), [("−10%", lambda: self.knob(-0.1)), ("−1%", lambda: self.knob(-0.01)), ("+1%", lambda: self.knob(0.01)), ("+10%", lambda: self.knob(0.1))])
        f = ttk.LabelFrame(ctl, text=T("스톱워치 · 시간 배속", "Stopwatch · time speed"))
        f.pack(fill="x", pady=2)
        self.wl = tk.Label(f, text="0.0 s", font=("Courier", 16, "bold"), bg="#1b1d20", fg="#e8eef2", width=10)
        self.wl.pack(anchor="w")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("시작/정지", "Start/stop"), command=self.ss).pack(side="left")
        ttk.Button(row, text=T("영점", "Reset"), command=self.wreset).pack(side="left", padx=2)
        for s in (1, 5, 10):
            ttk.Radiobutton(row, text="×%d" % s, value=s, variable=self.speed).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        ttk.Button(f, text=T("지금 값 적기 (시각, 계기 1, 계기 2)", "Write down now (time, meter 1, meter 2)"), command=self.record).pack(anchor="w")
        self.sheet = DataSheet(f, [("t", T("시각", "time"), 80), ("a", T("계기 1", "meter 1"), 100), ("b", T("계기 2", "meter 2"), 100)], height=6)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=380)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("옆에서 본 램프와 자 · 계기 1의 기록", "The lamp and ruler from the side · meter 1 over time"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    def rejob(self):
        self.trace = []

    def pour(self):
        if self.has("ampoule") and self.has("holder"):
            self.poured = True

    def hd(self, x):
        self.d = round(min(30.0, max(4.0, self.d + x)), 2)

    def knob(self, x):
        self.pot = round(min(1.0, max(0.0, self.pot + x)), 3)

    def ss(self):
        if self.has("watch"):
            self.watch_run = not self.watch_run

    def wreset(self):
        self.watch_t = 0.0

    def record(self):
        self.sheet.add(("%.1f s" % self.watch_t, self.show(0), self.show(1)))

    def tick(self, dt):
        ph = self.ph
        T = dt * self.speed.get()
        n = max(1, int(round(T / 0.1)))
        for _ in range(n):
            ph.step(T / n, self.lamp.get() and self.has("lamp"), self.lamp_up(), self.at_lamp() == "holder", self.poured,
                    self.cover.get() and self.has("cover"), self.at_lamp() == "detector", self.d)
        if self.watch_run:
            self.watch_t += T
        self.disp_t -= dt
        if self.disp_t <= 0:
            self.disp_t = 0.5
            r = self.raw()
            for i in range(2):
                if r[i] is not None:
                    self.disp[i] = r[i] + (random.random() - 0.5) * (0.14 if i == 0 else 1.4) * (0.1 if self.at_lamp() == "cell" and i else 1)
            if r[0] is not None:
                self.trace.append(r[0])
                self.trace = self.trace[-600:]
        msg = ""
        if self.at_lamp() is None:
            msg = T("램프와 고른 부품을 조립 탭에서 놓으세요.", "Place the lamp and the chosen part in the Assembly tab.")
        elif self.job.get() == "holder" and self.poured and not self.cover.get():
            msg = T("덮개가 없으면 바람이 ΔV를 흔듭니다.", "Without the cover, draughts shake ΔV.")
        self.warn.config(text=msg)
        self.refresh()

    def refresh(self):
        for i in range(2):
            self.lbl[i].config(text="%d: %s" % (i + 1, self.show(i)))
        if self.at_lamp() == "cell":
            self.what.config(text=T("계기 1: 태양전지 전압 · 계기 2: 전류 (20 mA, 10 Ω)", "Meter 1: cell voltage · meter 2: current (20 mA, 10 Ω)"))
        else:
            self.what.config(text=T("계기 1: ΔV = V2 − V1 (200 mV) · 계기 2: V2 (2000 mV)", "Meter 1: ΔV = V2 − V1 (200 mV) · meter 2: V2 (2000 mV)"))
        self.wl.config(text="%.1f s" % self.watch_t)
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        cv.create_rectangle(0, 0, 760, 380, fill="#f2f0ea", outline="")
        y0, ppc = 350, 10.0                  # the table, pixels per cm
        cv.create_rectangle(0, y0, 760, y0 + 30, fill="#c99a62", outline="")
        if self.has("ruler"):
            cv.create_rectangle(440, y0 - 300, 456, y0, fill="#f7f7f3", outline="#777")
            for mm in range(0, 301, 5):
                L = 10 if mm % 50 == 0 else (6 if mm % 10 == 0 else 3)
                y = y0 - mm * ppc / 10
                cv.create_line(440, y, 440 + L, y, fill="#222")
                if mm % 50 == 0:
                    cv.create_text(462, y, text=str(mm // 10), anchor="w", font=("Helvetica", 8))
        if not self.has("lamp"):
            return
        cv.create_rectangle(80, y0 - 8, 180, y0, fill="#2a2d33", outline="")
        cv.create_line(130, y0 - 8, 130, y0 - 290, fill="#9aa1a8", width=5)
        glow = "#ffd36b" if self.lamp.get() else "#d9dbe0"
        if self.lamp_up():
            hx, hz = 300, 6.0
            cv.create_line(130, y0 - 60, hx, y0 - 60, fill="#9aa1a8", width=4)
            cv.create_polygon(hx - 70, y0 - 140, hx + 70, y0 - 140, hx + 22, y0 - 64, hx - 22, y0 - 64, fill="#c9ccd1", outline="#777")
            cv.create_oval(hx - 10, y0 - 88, hx + 10, y0 - 68, fill=glow, outline="")
            if self.has("holder"):
                cv.create_rectangle(hx - 80, y0 - 148, hx + 80, y0 - 140, fill="#6b4a2b", outline="")
                for dx, k in ((-40, "D1"), (40, "D2")):
                    cv.create_rectangle(hx + dx - 16, y0 - 156, hx + dx + 16, y0 - 148, fill="#b8bcc2", outline="#666")
                    cv.create_text(hx + dx, y0 - 132, text=k, font=("Helvetica", 9, "bold"), fill="#f2f0ea")
                if self.poured:
                    cv.create_rectangle(hx + 28, y0 - 154, hx + 52, y0 - 150, fill="#efe6c8" if self.ph.H2 < 0.5 else "#e7eef3", outline="")
                if self.cover.get() and self.has("cover"):
                    cv.create_rectangle(hx - 86, y0 - 200, hx + 86, y0 - 148, outline="#555", fill="", width=2, dash=(6, 3))
        else:
            hx = 300
            hz = self.d * ppc
            cv.create_line(130, y0 - hz - 60, hx, y0 - hz - 60, fill="#9aa1a8", width=4)
            cv.create_line(hx, y0 - hz - 60, hx, y0 - hz - 30, fill="#9aa1a8", width=3)
            cv.create_polygon(hx - 22, y0 - hz - 30, hx + 22, y0 - hz - 30, hx + 70, y0 - hz + 40, hx - 70, y0 - hz + 40, fill="#c9ccd1", outline="#777")
            cv.create_oval(hx - 10, y0 - hz - 10, hx + 10, y0 - hz + 10, fill=glow, outline="")
            cv.create_line(hx, y0 - hz, 440, y0 - hz, fill="#c0392b", dash=(3, 3))
            k = self.at_lamp()
            if k == "detector":
                cv.create_rectangle(hx - 40, y0 - 45, hx + 40, y0, fill="#d3d5d8", outline="#666")
                cv.create_line(hx - 40, y0 - 45, hx + 40, y0 - 45, fill="#111", width=3)
                cv.create_line(hx, y0 - 45, 440, y0 - 45, fill="#2471a3", dash=(3, 3))
            elif k == "cell":
                cv.create_rectangle(hx - 30, y0 - 18, hx + 30, y0, fill="#1d2c5c", outline="#666")
                cv.create_line(hx, y0 - 18, 440, y0 - 18, fill="#2471a3", dash=(3, 3))
        # meter 1's history
        g0, g1, gy0, gy1 = 40, 740, 400, 630
        cv.create_rectangle(g0, gy0, g1, gy1, fill="#fbfaf6", outline="#999")
        if len(self.trace) > 1:
            lo, hi = min(self.trace), max(self.trace)
            if hi - lo < 2:
                lo, hi = (lo + hi) / 2 - 1, (lo + hi) / 2 + 1
            pts = []
            for i, v in enumerate(self.trace):
                pts += [g0 + (g1 - g0) * i / 599.0, gy1 - 10 - (gy1 - gy0 - 20) * (v - lo) / (hi - lo)]
            cv.create_line(*pts, fill="#2471a3", width=2)
            cv.create_text(g0 + 6, gy0 + 10, anchor="w", text="%.1f" % hi, font=("Helvetica", 8))
            cv.create_text(g0 + 6, gy1 - 10, anchor="w", text="%.1f" % lo, font=("Helvetica", 8))
        cv.create_text(g1 - 6, gy0 + 10, anchor="e", text=T("계기 1 (최근 600 표시, 0.5 s마다)", "Meter 1 (last 600 readings, every 0.5 s)"), font=("Helvetica", 8))


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
