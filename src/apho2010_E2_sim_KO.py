#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  11th Asian Physics Olympiad  (APhO 2010, Taipei, Taiwan)
  Experimental Problem 2 :  UNDERSTANDING SEMICONDUCTOR LASERS
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The collimated laser diode is driven from 5 V DC through a 10-turn 5 kOhm
  variable resistor and an ammeter; the current follows from the diode's
  knee voltage and the series resistance.
* Light out = weak spontaneous light + a lasing step about a hidden
  threshold, saturating near 19 mA.  The lasing light is mostly linearly
  polarized, the spontaneous light hardly at all, so beta depends on I.
* Filters and two real polarizers (finite extinction) feed a photoconductor
  whose conductance grows sub-linearly with light and saturates; room light
  adds a stray background.
* The bench shows only the two multimeters and the dial scales.  P, J,
  beta, the threshold and the PC law are never displayed.
* Hidden truths are randomised every session.
* Standard library only (tkinter).

    Run:   python3 apho2010_E2_sim_KO.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line


# --------------------------------------------------------------------------
#  Physics core  (mA, mW, ohm)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.Pmax = 3.0
        self.Ic = r.uniform(15.6, 16.6)          # centre of the lasing step [mA]
        self.w = r.uniform(0.78, 0.98)           # its width [mA]
        self.sp = r.uniform(0.0025, 0.0035)      # spontaneous light per mA (share of Pmax)
        self.bst, self.bsp = r.uniform(0.88, 0.95), 0.05
        self.phiL = r.uniform(-40, 40)           # laser polarization direction [deg]
        self.Vf, self.Rd = 2.05, 4.0
        self.Rin = 138 * r.uniform(0.97, 1.03)
        self.t1, self.t2 = r.uniform(0.82, 0.88), r.uniform(0.0004, 0.0012)
        self.F = [r.uniform(0.45, 0.55), r.uniform(0.22, 0.30), r.uniform(0.09, 0.13), r.uniform(0.035, 0.055)]
        self.Cd, self.Cs = r.uniform(1.6e-6, 2.4e-6), r.uniform(2.0e-3, 2.4e-3)
        self.a, self.gam = r.uniform(1.4e-3, 1.8e-3), r.uniform(0.64, 0.72)
        self.amb = r.uniform(0.006, 0.010)
        self.Imax = (5 - self.Vf) / (self.Rin + self.Rd) * 1000
        self.Rpc = 1e7

    def lg(self, I):
        return 1 / (1 + math.exp(-(I - self.Ic) / self.w))

    def laser(self, I):
        if I <= 0:
            return 0.0, 0.0
        psp, pst = self.sp * I, max(0.0, self.lg(I) - self.lg(0))
        n = self.sp * self.Imax + self.lg(self.Imax)
        return self.Pmax * (psp + pst) / n, (self.bsp * psp + self.bst * pst) / (psp + pst)

    def current(self, on, deg):
        if not on:
            return 0.0
        return max(0.0, (5 - self.Vf) / (self.Rin + 5000 * deg / 3600.0 + self.Rd) * 1000)

    def pol(self, th_deg):
        th = math.radians(th_deg)
        return self.t1 * math.cos(th) ** 2 + self.t2 * math.sin(th) ** 2

    def light(self, I, fin, p1, a1, p2, a2, lights):
        E = 0.0
        if I > 0:
            P, b = self.laser(I)
            for i, on in enumerate(fin):
                if on:
                    P *= self.F[i]
            pp, pu, d = P * b, P * (1 - b), self.phiL
            for use, a in ((p1, a1), (p2, a2)):
                if use:
                    pp, pu, d = pp * self.pol(a - d) + pu * (self.t1 + self.t2) / 2, 0.0, a
            E = pp + pu
        return E + (self.amb if lights else 0.0)

    def C(self, E):
        return self.Cd + self.Cs * (1 - math.exp(-self.a * max(0.0, E) ** self.gam / self.Cs))

    def step(self, dt, E):
        lr = math.log(self.Rpc)        # the photoconductor settles in a few tenths of a second
        self.Rpc = math.exp(lr + (math.log(1 / self.C(E)) - lr) * min(1.0, dt / 0.25))


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_track(cv, x, y, sc=1.0):
    cv.create_rectangle(x - 300 * sc, y - 8 * sc, x + 300 * sc, y + 8 * sc, fill="#3d434b", outline="#22262b")


def art_gen(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 50 * s, y - 30 * s, x + 50 * s, y + 30 * s, fill="#dcdfe2", outline="#8a8f96")
    cv.create_rectangle(x - 42 * s, y - 22 * s, x - 2 * s, y - 4 * s, fill="#0d1f12", outline="")


def art_vres(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 22 * s, y - 22 * s, x + 22 * s, y + 22 * s, fill="#2f3338", outline="#111")
    cv.create_oval(x - 14 * s, y - 14 * s, x + 14 * s, y + 14 * s, fill="#16181b", outline="#555")


def art_dmm(cv, x, y, sc=1.0):
    s = sc
    rr(cv, x - 26 * s, y - 40 * s, x + 26 * s, y + 40 * s, 6 * s, fill="#e8c02a", outline="#9a7c10")
    cv.create_rectangle(x - 18 * s, y - 32 * s, x + 18 * s, y - 14 * s, fill="#b9c6a6", outline="")
    cv.create_oval(x - 10 * s, y - 2 * s, x + 10 * s, y + 18 * s, fill="#1e2023", outline="")


def art_cld(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 30 * s, y - 8 * s, x + 24 * s, y + 8 * s, fill="#2b2f35", outline="")
    cv.create_rectangle(x + 24 * s, y - 6 * s, x + 30 * s, y + 6 * s, fill="#c0392b", outline="")


def art_filt(cv, x, y, sc=1.0):
    s = sc
    for i in range(4):
        cv.create_rectangle(x - 16 * s + i * 8 * s, y - 20 * s, x - 11 * s + i * 8 * s, y + 20 * s, fill="#555", outline="#222")


def art_pol(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 22 * s, y - 22 * s, x + 22 * s, y + 22 * s, fill="#2a2d31", outline="#666")
    cv.create_oval(x - 14 * s, y - 14 * s, x + 14 * s, y + 14 * s, fill="#5a646e", outline="")
    cv.create_line(x - 14 * s, y, x + 14 * s, y, fill="#ffcf3a", width=2)


def art_pc(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 14 * s, y - 14 * s, x + 14 * s, y + 14 * s, fill="#2b2f35", outline="")
    cv.create_oval(x - 8 * s, y - 8 * s, x + 8 * s, y + 8 * s, fill="#c55a2a", outline="")


def art_wires(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 20 * s, y - 10 * s, x + 20 * s, y + 10 * s, outline="#c0392b", width=2)
    cv.create_oval(x - 14 * s, y - 6 * s, x + 14 * s, y + 6 * s, outline="#141414", width=2)


ART = {"track": art_track, "gen": art_gen, "vres": art_vres, "dmmA": art_dmm, "dmmR": art_dmm, "cld": art_cld,
       "filt": art_filt, "p1": art_pol, "p2": art_pol, "pc": art_pc, "leads": art_wires, "pcl": art_wires}

PARTS = [
    ("track", ("[C-A] 광학 레일", "[C-A] Optical track"), []),
    ("cld",   ("[C-C] 평행광 레이저 다이오드", "[C-C] Collimated laser diode"), ["track"]),
    ("filt",  ("[II-T/U] 필터 홀더 + 필터", "[II-T/U] Filter holder + filters"), ["track"]),
    ("p1",    ("[II-Q] 편광판 P1", "[II-Q] Polarizer P1"), ["track"]),
    ("p2",    ("[II-P] 편광판 P2 (지시선)", "[II-P] Polarizer P2 (indicator)"), ["track"]),
    ("pc",    ("[II-W] 광전도체", "[II-W] Photoconductor"), ["track"]),
    ("gen",   ("[C-D] 사인파 발생기 (5 V DC)", "[C-D] Generator (5 V DC)"), []),
    ("vres",  ("[C-E] 가변저항 5 kΩ", "[C-E] Variable resistor 5 kΩ"), []),
    ("dmmA",  ("[II-X] 멀티미터 (전류)", "[II-X] Multimeter (current)"), []),
    ("leads", ("[C-F] 회로 전선", "[C-F] Circuit leads"), ["gen", "vres", "dmmA", "cld"]),
    ("dmmR",  ("[II-Y] 멀티미터 (저항)", "[II-Y] Multimeter (resistance)"), []),
    ("pcl",   ("PC 전선", "PC leads"), ["dmmR", "pc"]),
]
ZONES = {
    "track": (380, 300, 600, 16), "cld": (130, 270, 60, 20), "filt": (250, 270, 40, 44), "p1": (360, 270, 48, 48),
    "p2": (470, 270, 48, 48), "pc": (620, 270, 32, 32),
    "gen": (130, 450, 100, 60), "vres": (270, 450, 48, 48), "dmmA": (380, 450, 56, 84), "leads": (270, 380, 44, 24),
    "dmmR": (620, 450, 56, 84), "pcl": (620, 370, 44, 24),
}
SCENE_TITLE = ("그림 IIA-1, IIA-3의 구성 — 레이저, 필터, P1, P2, 광전도체", "The set-up of Figs. IIA-1 and IIA-3 — laser, filters, P1, P2, photoconductor")
APP_TITLE = ("APhO 2010 실험 2 — 반도체 레이저 이해하기", "APhO 2010 Experiment 2 — Understanding semiconductor lasers")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.pwr, self.deg, self.lights = False, 720.0, True
        self.fin = [tk.BooleanVar(value=False) for _ in range(4)]
        self.use = {k: tk.BooleanVar(value=True) for k in ("p1", "p2")}
        self.a1, self.a2 = 0.0, 0.0
        self.noise = 0.0
        self.t = 0.0
        self.drag = None
        self.build()
        self.refresh()

    def I(self):
        return self.ph.current(self.pwr and "leads" in self.app.placed, self.deg)

    def E(self):
        P = self.app.placed
        if "pc" not in P:
            return 0.0
        fin = [v.get() and "filt" in P for v in self.fin]
        return self.ph.light(self.I(), fin, "p1" in P and self.use["p1"].get(), self.a1,
                             "p2" in P and self.use["p2"].get(), self.a2, self.lights)

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("전원 · 가변저항", "Power · variable resistor"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.pwr_btn = ttk.Button(row, text=T("5 V 켜기", "5 V on"), command=self.toggle)
        self.pwr_btn.pack(side="left", padx=2)
        self.light_btn = ttk.Button(row, text=T("실내등 끄기", "Room light off"), command=self.toggle_light)
        self.light_btn.pack(side="left", padx=2)
        stepper(f, T("돌리기", "Turn"), [("−90°", lambda: self.turn(-90)), ("−10°", lambda: self.turn(-10)), ("−1°", lambda: self.turn(-1)),
                                       ("+1°", lambda: self.turn(1)), ("+10°", lambda: self.turn(10)), ("+90°", lambda: self.turn(90))])
        f = ttk.LabelFrame(ctl, text=T("멀티미터", "Multimeters"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text="X (mA)").pack(side="left")
        self.dI = tk.Label(row, text="- - -", font=("Courier", 16, "bold"), bg="#b9c6a6", width=9)
        self.dI.pack(side="left", padx=4)
        ttk.Label(row, text="Y (Ω)").pack(side="left")
        self.dR = tk.Label(row, text="- - -", font=("Courier", 16, "bold"), bg="#b9c6a6", width=9)
        self.dR.pack(side="left", padx=4)
        f = ttk.LabelFrame(ctl, text=T("필터 · 편광판", "Filters · polarizers"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for i in range(4):
            ttk.Checkbutton(row, text=T("필터 ", "Filter ") + str(i + 1), variable=self.fin[i]).pack(side="left", padx=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Checkbutton(row, text=T("P1 빛길에 둠", "P1 in the beam"), variable=self.use["p1"]).pack(side="left", padx=2)
        ttk.Checkbutton(row, text=T("P2 빛길에 둠", "P2 in the beam"), variable=self.use["p2"]).pack(side="left", padx=2)
        stepper(f, "P1", [("−10°", lambda: self.rot("p1", -10)), ("−1°", lambda: self.rot("p1", -1)), ("+1°", lambda: self.rot("p1", 1)), ("+10°", lambda: self.rot("p1", 10))])
        stepper(f, "P2", [("−10°", lambda: self.rot("p2", -10)), ("−1°", lambda: self.rot("p2", -1)), ("+1°", lambda: self.rot("p2", 1)), ("+10°", lambda: self.rot("p2", 10))])
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        ttk.Button(f, text=T("전류·저항·눈금 적기", "Record current, R and dials"), command=self.record).pack(fill="x", pady=2)
        self.sheet = DataSheet(f, [("I", "I (mA)", 70), ("R", "R (Ω)", 80), ("p1", "P1 (°)", 60), ("p2", "P2 (°)", 60), ("F", T("필터", "filters"), 60)], height=9)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=380)
        self.warn.pack(anchor="w")

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("레이저 쪽에서 본 편광판 — 눈금을 읽으시오 (끌어서 돌리기)", "The polarizers from the laser side — read the dials (drag to turn)"),
                  font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.dials = tk.Canvas(right, width=820, height=380, bg="#2a2d33", highlightthickness=0)
        self.dials.pack()
        ttk.Label(right, text=T("10회전 가변저항 다이얼 (창: 바퀴 수, 눈금: 1/100 바퀴)", "10-turn resistor dial (window: turns, scale: 1/100 turn)"),
                  font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(6, 0))
        self.vr = tk.Canvas(right, width=820, height=250, bg="#2a2d33", highlightthickness=0)
        self.vr.pack()
        self.dials.bind("<ButtonPress-1>", self.press)
        self.dials.bind("<B1-Motion>", self.motion)
        self.dials.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag", None))

    # ---- controls -----------------------------------------------------------
    def toggle(self):
        if "gen" in self.app.placed:
            self.pwr = not self.pwr
            self.pwr_btn.config(text=T("5 V 끄기", "5 V off") if self.pwr else T("5 V 켜기", "5 V on"))

    def toggle_light(self):
        self.lights = not self.lights
        self.light_btn.config(text=T("실내등 끄기", "Room light off") if self.lights else T("실내등 켜기", "Room light on"))

    def turn(self, d):
        self.deg = max(0.0, min(3600.0, self.deg + d))

    def rot(self, k, d):
        if k == "p1":
            self.a1 = (self.a1 + d) % 360
        else:
            self.a2 = (self.a2 + d) % 360

    def press(self, ev):
        for k, cx in (("p1", 220), ("p2", 600)):
            if math.hypot(ev.x - cx, ev.y - 190) < 160:
                self.drag = (k, cx, math.atan2(ev.y - 190, ev.x - cx), self.a1 if k == "p1" else self.a2)

    def motion(self, ev):
        if not self.drag:
            return
        k, cx, a0, v0 = self.drag
        d = math.degrees(math.atan2(ev.y - 190, ev.x - cx) - a0)
        v = round((v0 - d) % 360, 0)
        if k == "p1":
            self.a1 = v
        else:
            self.a2 = v

    def fmtR(self, R):
        if "pcl" not in self.app.placed:
            return "  0L"
        if R >= 1e6:
            return "%.2fM" % (R / 1e6)
        if R >= 1e5:
            return "%.0fk" % (R / 1e3)
        if R >= 1e4:
            return "%.1fk" % (R / 1e3)
        if R >= 1e3:
            return "%.2fk" % (R / 1e3)
        return "%.0f" % R

    def record(self):
        fl = "".join(str(i + 1) for i, v in enumerate(self.fin) if v.get()) or "-"
        self.sheet.add(("%.2f" % self.I(), self.fmtR(self.ph.Rpc * (1 + self.noise)), "%.0f" % self.a1, "%.0f" % self.a2, fl))

    # ---- loop -------------------------------------------------------------
    def tick(self, dt):
        self.t += dt
        self.ph.step(dt, self.E())
        if int(self.t * 2.5) != int((self.t - dt) * 2.5):
            self.noise = random.uniform(-0.0015, 0.0015)
        self.refresh()

    def refresh(self):
        P = self.app.placed
        self.dI.config(text=("%.2f" % self.I()) if "dmmA" in P else "- - -")
        self.dR.config(text=self.fmtR(self.ph.Rpc * (1 + self.noise)) if "dmmR" in P else "- - -")
        msgs = []
        if self.lights and "pc" in P:
            msgs.append(T("실내등이 켜져 있습니다 — 주변 빛이 광전도체에 들어갑니다.", "The room light is on: stray light reaches the photoconductor."))
        if "pcl" in P and self.ph.Rpc < 1.3 / self.ph.Cs:
            msgs.append(T("광전도체가 포화에 가깝습니다 — 필터를 더 넣으시오.", "The photoconductor is close to saturation: add filters."))
        self.warn.config(text="\n".join(msgs))
        self.draw_dials()
        self.draw_vr()

    def dial(self, cv, cx, cy, R, ang, label):
        cv.create_oval(cx - R * 1.08, cy - R * 1.08, cx + R * 1.08, cy + R * 1.08, fill="#2a2d31", outline="#111")
        for dg in range(360):
            a = -math.radians(dg)
            l = 0.13 if dg % 10 == 0 else 0.09 if dg % 5 == 0 else 0.05
            cv.create_line(cx + R * math.cos(a), cy + R * math.sin(a), cx + R * (1 - l) * math.cos(a), cy + R * (1 - l) * math.sin(a), fill="#d8dde2")
            if dg % 30 == 0:
                cv.create_text(cx + R * 0.78 * math.cos(a), cy + R * 0.78 * math.sin(a), text=str(dg), fill="#e8eef2", font=("Helvetica", 8))
        a = -math.radians(ang)
        cv.create_oval(cx - R * 0.62, cy - R * 0.62, cx + R * 0.62, cy + R * 0.62, fill="#4f5964", outline="")
        cv.create_line(cx - R * 0.62 * math.cos(a), cy - R * 0.62 * math.sin(a), cx + R * 1.02 * math.cos(a), cy + R * 1.02 * math.sin(a), fill="#ffcf3a", width=2, arrow="last")
        cv.create_text(cx, cy + R * 1.2, text=label, fill="#e8eef2", font=("Helvetica", 11, "bold"))

    def draw_dials(self):
        cv = self.dials
        cv.delete("all")
        for k, cx, ang in (("p1", 220, self.a1), ("p2", 600, self.a2)):
            if k in self.app.placed:
                self.dial(cv, cx, 175, 145, ang, k.upper())

    def draw_vr(self):
        cv = self.vr
        cv.delete("all")
        if "vres" not in self.app.placed:
            return
        cx, cy, R = 410, 125, 100
        cv.create_oval(cx - R * 1.12, cy - R * 1.12, cx + R * 1.12, cy + R * 1.12, fill="#202327", outline="#111")
        for k in range(100):
            a = -math.pi / 2 + k / 100.0 * 2 * math.pi
            l = 0.14 if k % 10 == 0 else 0.09 if k % 5 == 0 else 0.05
            cv.create_line(cx + R * math.cos(a), cy + R * math.sin(a), cx + R * (1 - l) * math.cos(a), cy + R * (1 - l) * math.sin(a), fill="#d8dde2")
            if k % 10 == 0:
                cv.create_text(cx + R * 0.76 * math.cos(a), cy + R * 0.76 * math.sin(a), text=str(k), fill="#e8eef2", font=("Helvetica", 8))
        turns = self.deg / 360.0
        a = -math.pi / 2 + (turns % 1) * 2 * math.pi
        cv.create_line(cx, cy, cx + R * 0.95 * math.cos(a), cy + R * 0.95 * math.sin(a), fill="#ffcf3a", width=3)
        cv.create_rectangle(cx - 20, cy - 34, cx + 20, cy - 12, fill="#0b0c0e", outline="#555")
        cv.create_text(cx, cy - 23, text=str(int(turns + 1e-9)), fill="#e8eef2", font=("Courier", 12, "bold"))


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
