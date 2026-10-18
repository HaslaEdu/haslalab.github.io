#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  8th Asian Physics Olympiad  (APhO 2007, Shanghai, China)
  Experimental Problem 1 :  INTERFERENCE METHOD FOR THE THERMAL EXPANSION
                            AND THE TEMPERATURE COEFFICIENT OF THE
                            REFRACTIVE INDEX OF GLASS
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The sample: glass cylinder A (L = 10.12 mm) with wedged plates B, B' glued
  on its ends; region c is the air gap where A is cut away (order 2L/lambda),
  region a is where the plates are cut away (order 2nL/lambda), region b
  gives two plain spots.  The platform's three screws tilt the reflections
  across the graph paper; the fringe spot's rings move as the order changes.
* The oven is a thermostatted plate feeding an aluminium block; the sample
  lags the block and the probe lags its hole, as in a real heater.
* Only the thermometer, the graph paper and the timer are shown; beta and
  gamma are never displayed.  Hidden truths are randomised every session.
* Standard library only (tkinter).

    Run:   python3 apho2007_E1_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line

DSCR = 300.0         # sample to screen, mm


# --------------------------------------------------------------------------
#  Physics core
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.beta = r.uniform(6.6e-6, 7.8e-6)
        self.gam = r.uniform(1.6e-6, 3.0e-6)
        self.n0, self.L, self.lam = 1.515, 10.12e-3 * r.uniform(0.998, 1.002), 632.8e-9
        self.Tr = r.uniform(20, 24)
        self.wB, self.wB2 = r.uniform(10, 14) * 1e-3, r.uniform(10, 14) * 1e-3
        self.tilt0 = [r.uniform(-6, 6) * 1e-3, r.uniform(-6, 6) * 1e-3]
        self.Pmax, self.Cp, self.Cb, self.Gpb, self.Gb, self.Gp = 95.0, 180.0, 520.0, 2.6, 0.35, 0.25
        self.tauS, self.tauP = 25.0, 8.0
        self.Tp = self.Tb = self.Ts = self.Tth = self.Tr
        self.heating = False

    def step(self, dt, on, knob, basin):
        setp = 25 + knob * 9
        self.heating = on and knob > 0 and self.Tp < setp
        Pin = self.Pmax * min(1, 0.35 + knob / 10.0) if self.heating else 0.0
        q = self.Gpb * (self.Tp - self.Tb) if not basin else 0.0
        self.Tp += (Pin - q - self.Gp * (self.Tp - self.Tr)) * dt / self.Cp
        G, Te = (14.0, 18.0) if basin else (self.Gb, self.Tr)
        self.Tb += (q - G * (self.Tb - Te)) * dt / self.Cb
        self.Ts += (self.Tb - self.Ts) * min(1, dt / self.tauS)
        self.Tth += (self.Tb - self.Tth) * min(1, dt / self.tauP)

    def order(self, region):
        T = self.Ts
        Lt = self.L * (1 + self.beta * (T - 25))
        if region == "c":
            return 2 * Lt / self.lam
        if region == "a":
            return 2 * (self.n0 + self.gam * (T - 25)) * Lt / self.lam
        return None


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_stand(cv, x, y, s=1.0):
    cv.create_rectangle(x - 50 * s, y + 70 * s, x + 50 * s, y + 80 * s, fill="#3b4047", outline="")
    cv.create_rectangle(x - 40 * s, y - 90 * s, x - 34 * s, y + 70 * s, fill="#b9bec4", outline="")
    cv.create_rectangle(x - 6 * s, y - 90 * s, x + 6 * s, y - 30 * s, fill="#c0392b", outline="")
    cv.create_line(x - 30 * s, y - 20 * s, x + 30 * s, y - 26 * s, width=max(1, int(4 * s)), fill="#c3c8cd")


def art_platform(cv, x, y, s=1.0):
    cv.create_oval(x - 40 * s, y - 10 * s, x + 40 * s, y + 10 * s, fill="#4a5059", outline="#222")


def art_oven(cv, x, y, s=1.0):
    cv.create_rectangle(x - 45 * s, y, x + 45 * s, y + 22 * s, fill="#e5e1d6", outline="#999")
    cv.create_rectangle(x - 30 * s, y - 34 * s, x + 30 * s, y, fill="#a9afb6", outline="#666")


def art_big(cv, x, y, s=1.0):
    cv.create_rectangle(x - 26 * s, y - 26 * s, x + 26 * s, y + 26 * s, fill="#c3c8cd", outline="#7c8288")
    cv.create_rectangle(x - 8 * s, y - 26 * s, x + 8 * s, y - 6 * s, fill="#3a3d42", outline="")


def art_sample(cv, x, y, s=1.0):
    cv.create_rectangle(x - 12 * s, y - 8 * s, x + 12 * s, y + 8 * s, fill="#c8e6eb", outline="#7fa7b4")


def art_small(cv, x, y, s=1.0):
    cv.create_rectangle(x - 7 * s, y - 24 * s, x + 7 * s, y + 24 * s, fill="#cfd3d7", outline="#7c8288")


def art_therm(cv, x, y, s=1.0):
    cv.create_rectangle(x - 16 * s, y - 26 * s, x + 16 * s, y + 26 * s, fill="#e9ecef", outline="#999")
    cv.create_rectangle(x - 12 * s, y - 20 * s, x + 12 * s, y, fill="#b9c6a6", outline="")


def art_basin(cv, x, y, s=1.0):
    cv.create_oval(x - 45 * s, y - 16 * s, x + 45 * s, y + 16 * s, fill="#7fb0d0", outline="#557")


def art_towel(cv, x, y, s=1.0):
    cv.create_rectangle(x - 30 * s, y - 14 * s, x + 30 * s, y + 14 * s, fill="#d9c48a", outline="#a8975a")


ART = {"stand": art_stand, "platform": art_platform, "oven": art_oven, "bigal": art_big, "sample": art_sample,
       "smallal": art_small, "therm": art_therm, "basin": art_basin, "towel": art_towel}
PARTS = [
    ("stand",    ("[3] 레이저 받침 + 스크린", "[3] Laser holder + screen"), []),
    ("platform", ("[4] 수평 조절 받침대", "[4] Levelling platform"), ["stand"]),
    ("oven",     ("[2] 전기 오븐 + 컵", "[2] Electric oven + cup"), ["platform"]),
    ("bigal",    ("큰 알루미늄 원기둥", "Big aluminium cylinder"), ["oven"]),
    ("sample",   ("[1] 유리 시료", "[1] Glass sample"), ["bigal"]),
    ("smallal",  ("작은 알루미늄 원기둥", "Small aluminium cylinder"), ["sample"]),
    ("therm",    ("[5] 디지털 온도계", "[5] Digital thermometer"), ["smallal"]),
    ("basin",    ("[7] 찬물 대야", "[7] Basin of cold water"), []),
    ("towel",    ("[8] 수건", "[8] Towel"), []),
]
ZONES = {"stand": (300, 330, 110, 180), "platform": (300, 440, 90, 26), "oven": (300, 410, 100, 40), "bigal": (300, 370, 56, 56),
         "sample": (300, 384, 28, 18), "smallal": (300, 352, 18, 50), "therm": (420, 400, 40, 60), "basin": (600, 440, 100, 36), "towel": (600, 380, 66, 30)}
SCENE_TITLE = ("그림 2·3 — 레이저 아래 받침대, 그 위 오븐, 원기둥 속 시료", "Figs. 2 and 3 — platform under the laser, oven on it, sample in the cylinder")
APP_TITLE = ("APhO 2007 실험 1 — 간섭법으로 유리의 열팽창과 굴절률 온도계수", "APhO 2007 Experiment 1 — Thermal expansion and dn/dT of glass by interference")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.t = 0.0
        self.on, self.knob, self.laser, self.basin = False, 0, False, False
        self.scr = [0.0, 0.0, 0.0]
        self.slide = 0.0
        self.speed = tk.IntVar(value=1)
        self.count = 0
        self.sw_acc, self.sw_run, self.sw_t0 = 0.0, False, 0.0
        self.build()
        self.refresh()

    def ready(self):
        return {"stand", "platform", "oven", "bigal", "sample", "smallal"} <= self.app.placed

    def region(self):
        return "c" if self.slide < -3.5 else ("a" if self.slide > 3.5 else "b")

    def tilt(self):
        a, b, c = [t * 0.5e-3 for t in self.scr]
        s = 60e-3
        return self.ph.tilt0[0] + (b - c) / s, self.ph.tilt0[1] + (a - (b + c) / 2) / (s * 0.866)

    def spots(self):
        if not (self.laser and self.ready()) or self.basin:
            return []
        tx, ty = self.tilt()
        bx, by, n, ph = 2 * tx * DSCR, 2 * ty * DSCR, self.ph.n0, self.ph
        r = self.region()
        if r == "a":
            return [(bx, by, True)]
        out = [(bx + 2 * ph.wB * DSCR, by, False), (bx - 2 * n * ph.wB2 * DSCR * 0.8, by + 2 * n * ph.wB2 * DSCR * 0.45, False)]
        if r == "c":
            out.append((bx + 2 * (n - 1) * ph.wB * DSCR * 0.15, by - 0.4, True))
        return out

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("전기 오븐", "Electric oven"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.on_btn = ttk.Button(row, text="", command=self.toggle)
        self.on_btn.pack(side="left", padx=2)
        ttk.Button(row, text="◀", width=3, command=lambda: self.setk(-1)).pack(side="left")
        self.k_lbl = ttk.Label(row, text="", width=12)
        self.k_lbl.pack(side="left")
        ttk.Button(row, text="▶", width=3, command=lambda: self.setk(1)).pack(side="left")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("손잡이 최소", "Knob min"), command=lambda: self.setk(-10)).pack(side="left", padx=2)
        ttk.Button(row, text=T("손잡이 최대", "Knob max"), command=lambda: self.setk(10)).pack(side="left", padx=2)
        self.basin_btn = ttk.Button(row, text="", command=self.toggle_basin)
        self.basin_btn.pack(side="left", padx=2)
        f = ttk.LabelFrame(ctl, text=T("온도계", "Thermometer"))
        f.pack(fill="x", pady=2)
        self.dT = tk.Label(f, text="", font=("Courier", 18, "bold"), bg="#b9c6a6", width=10)
        self.dT.pack()
        f = ttk.LabelFrame(ctl, text=T("레이저 · 받침대", "Laser · platform"))
        f.pack(fill="x", pady=2)
        self.las_btn = ttk.Button(f, text="", command=self.toggle_laser)
        self.las_btn.pack(anchor="w", padx=2)
        for i, lab in enumerate("abc"):
            stepper(f, T("나사 ", "screw ") + lab, [("↺", lambda i=i: self.screw(i, -0.25)), ("↻", lambda i=i: self.screw(i, 0.25))])
        self.scr_lbl = ttk.Label(f, text="")
        self.scr_lbl.pack(anchor="w")
        stepper(f, T("받침대 밀기", "Slide"), [("◀◀", lambda: self.slide_by(-1)), ("◀", lambda: self.slide_by(-0.2)), ("▶", lambda: self.slide_by(0.2)), ("▶▶", lambda: self.slide_by(1))])
        f = ttk.LabelFrame(ctl, text=T("타이머 · 시간 빠르게", "Timer · speed up"))
        f.pack(fill="x", pady=2)
        self.sw_lbl = tk.Label(f, text="0:00.0", font=("Courier", 16, "bold"), bg="#101317", fg="#e8eef2", width=10)
        self.sw_lbl.pack()
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.sw_btn = ttk.Button(row, text=T("시작", "Start"), command=self.sw_toggle)
        self.sw_btn.pack(side="left", padx=2)
        for v in (1, 5, 10):
            ttk.Radiobutton(row, text="×%d" % v, value=v, variable=self.speed).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("무늬 세기", "Counting fringes"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("무늬 하나 지나감 → 온도 적기", "A fringe passed → note T"), command=self.fringe).pack(side="left", padx=2)
        ttk.Button(row, text=T("번호 처음부터", "Restart"), command=self.reset_count).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("m", "m", 50), ("T", "T (°C)", 80), ("r", T("영역", "region"), 60), ("t", "t (s)", 70)], height=7)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=360)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("레이저 아래 모눈종이 (1 mm 눈금, 가운데 검은 구멍)", "Graph paper under the laser (1 mm grid, black hole in the middle)"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.scr_cv = tk.Canvas(right, width=860, height=470, bg="#f6f4e8", highlightthickness=0)
        self.scr_cv.pack()
        ttk.Label(right, text=T("시료 단면 — 빛이 닿는 영역", "The sample in section — where the beam falls"), font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(6, 0))
        self.sec = tk.Canvas(right, width=860, height=180, bg="#eceae4", highlightthickness=0)
        self.sec.pack()

    def toggle(self):
        if "oven" in self.app.placed:
            self.on = not self.on

    def setk(self, d):
        self.knob = max(0, min(10, self.knob + d))

    def toggle_basin(self):
        if "basin" in self.app.placed:
            self.basin = not self.basin

    def toggle_laser(self):
        if "stand" in self.app.placed:
            self.laser = not self.laser

    def screw(self, i, d):
        self.scr[i] = round(self.scr[i] + d, 2)

    def slide_by(self, d):
        self.slide = max(-10.0, min(10.0, round(self.slide + d, 1)))

    def fringe(self):
        self.count += 1
        self.sheet.add((self.count, "%.1f" % self.ph.Tth, self.region(), "%.1f" % self.sw_value()))

    def reset_count(self):
        self.count = 0

    def sw_value(self):
        return self.sw_acc + (self.t - self.sw_t0 if self.sw_run else 0.0)

    def sw_toggle(self):
        if self.sw_run:
            self.sw_acc += self.t - self.sw_t0
        else:
            self.sw_t0 = self.t
        self.sw_run = not self.sw_run
        self.sw_btn.config(text=T("정지", "Stop") if self.sw_run else T("시작", "Start"))

    def tick(self, dt):
        dt *= self.speed.get()
        self.t += dt
        n = max(1, int(dt / 0.05))
        for _ in range(n):
            self.ph.step(dt / n, self.on and self.ready(), self.knob, self.basin)
        self.refresh()

    def refresh(self):
        self.on_btn.config(text=T("오븐 끄기", "Oven off") if self.on else T("오븐 켜기", "Oven on"))
        self.k_lbl.config(text=T("손잡이 ", "knob ") + "%d/10%s" % (self.knob, " ●" if self.ph.heating else ""))
        self.basin_btn.config(text=T("오븐에 다시 넣기", "Back in the oven") if self.basin else T("찬물에 식히기", "Cool in water"))
        self.las_btn.config(text=T("레이저 끄기", "Laser off") if self.laser else T("레이저 켜기", "Laser on"))
        self.scr_lbl.config(text="a %.2f   b %.2f   c %.2f %s" % (self.scr[0], self.scr[1], self.scr[2], T("바퀴", "turns")))
        self.dT.config(text=("%.1f °C" % self.ph.Tth) if "therm" in self.app.placed else "")
        v = self.sw_value()
        self.sw_lbl.config(text="%d:%04.1f" % (int(v // 60), v % 60))
        self.warn.config(text=T("너무 뜨겁습니다 — 손잡이를 최소로!", "Too hot — knob to minimum!") if self.ph.Tb > 92 else "")
        self.draw_screen()
        self.draw_section()

    def draw_screen(self):
        cv = self.scr_cv
        cv.delete("all")
        z, cx, cy = 9.0, 430, 235
        for mm in range(-48, 49):
            col = "#d9a49a" if mm % 10 == 0 else ("#ecc6be" if mm % 5 == 0 else "#f3dcd6")
            cv.create_line(cx + mm * z, 0, cx + mm * z, 470, fill=col)
            if abs(mm) <= 26:
                cv.create_line(0, cy + mm * z, 860, cy + mm * z, fill=col)
        cv.create_oval(cx - 3.5 * z, cy - 3.5 * z, cx + 3.5 * z, cy + 3.5 * z, fill="#1b1d20", outline="")
        for (x, y, fr) in self.spots():
            if math.hypot(x, y) < 3.4:
                continue
            px, py = cx + x * z, cy + y * z
            for rr, col in ((3.0, "#ffc0b8"), (2.2, "#ff8a7a"), (1.4, "#ff5040")):
                cv.create_oval(px - rr * z, py - rr * z, px + rr * z, py + rr * z, fill=col, outline="")
            if fr:
                m = self.ph.order(self.region())
                frac = m - math.floor(m)
                for k in range(0, 6):
                    rk = 1.25 * z * math.sqrt(2 * (k + frac))
                    if rk > 4.3 * z:
                        break
                    cv.create_oval(px - rk, py - rk, px + rk, py + rk, outline="#7a0d05", width=2)
        if not self.laser:
            cv.create_text(430, 14, text=T("레이저 꺼짐", "laser off"), fill="#555")

    def draw_section(self):
        cv = self.sec
        cv.delete("all")
        z, cx, base = 22.0, 430, 140
        X = lambda x: cx + x * z
        Y = lambda y: base - y * z * 0.45
        L = self.ph.L * 1000
        cv.create_polygon(X(-12), Y(-1.8), X(4), Y(-1.5), X(4), Y(0), X(-12), Y(0), fill="#aad7e1", outline="#5f8f9c")
        cv.create_rectangle(X(-4), Y(L), X(12), Y(0), fill="#aad7e1", outline="#5f8f9c")
        cv.create_polygon(X(-12), Y(L), X(4), Y(L), X(4), Y(L + 1.7), X(-12), Y(L + 1.4), fill="#aad7e1", outline="#5f8f9c")
        for x, l in ((-8, "c"), (0, "b"), (8, "a")):
            cv.create_text(X(x), base + 20, text=l, font=("Helvetica", 12, "bold"))
        cv.create_line(X(self.slide), 0, X(self.slide), Y(-1.8), fill="#e03020" if self.laser else "#c99", width=2, dash=() if self.laser else (4, 4))
        cv.create_text(X(self.slide) + 8, 12, anchor="w", text=T("영역 ", "region ") + self.region(), font=("Helvetica", 11, "bold"))


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
