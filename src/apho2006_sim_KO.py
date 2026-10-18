#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  7th Asian Physics Olympiad  (APhO 2006, Almaty, Kazakhstan)
  Experimental Problem :  SPECIFIC HEAT OF ALUMINIUM AND
                          LATENT HEAT OF EVAPORATION OF NITROGEN
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* Part 1: hot water in a plastic cup cools by Newton's law; the loss
  coefficient grows with the water level, so the two cooling runs compare
  only if the levels match.  The cup's own small heat capacity is real
  (the sheet tells you to neglect it).  Cap off: faster, evaporative loss.
* Part 2: liquid nitrogen in a foam cup boils off at a rate that grows with
  the wetted wall; the plunged cylinder film-boils down to the Leidenfrost
  point, then finishes fast.  Aluminium's c(T) is Debye-like (theta 390 K).
* The scales show whole grams, switch themselves off after ~60 s left alone
  and zero to whatever is on them when switched on again.
* Hidden truths are randomised every session.
* Standard library only (tkinter).

    Run:   python3 apho2006_sim_KO.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line

RHO_N = 0.808


def c_al_k(tk_):
    """specific heat of aluminium, J/(g K), against absolute temperature (unnormalised)"""
    if tk_ < 2:
        return 0.0
    x, n, s = 390.0 / tk_, 120, 0.0
    for i in range(1, n + 1):
        u = x * (i - 0.5) / n
        s += u ** 4 * math.exp(u) / (math.exp(u) - 1) ** 2
    return 9 * 8.314 / 26.98 * (s * x / n) / x ** 3 * (1 + 1.5e-4 * (tk_ - 50))


# --------------------------------------------------------------------------
#  Physics core  (g, degC, s, J)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.Tr = r.uniform(22.0, 25.0)
        self.Tdew = r.uniform(78, 84)
        self.mAl = r.uniform(66, 72)
        self.cw = 4.20
        self.cAl0 = 0.897 * r.uniform(0.985, 1.015)
        self.Ccup = r.uniform(4, 8)
        self.a0, self.a1 = r.uniform(0.055, 0.065), r.uniform(0.050, 0.060)
        self.rCup = 3.6
        self.mCup, self.mFoam = r.uniform(5, 7), r.uniform(7, 10)
        self.lam = 199 * r.uniform(0.985, 1.015)
        self.kN = r.uniform(5.4, 6.4)
        self.Hf, self.TL = r.uniform(0.56, 0.66), r.uniform(100, 112)
        self.norm = self.cAl0 / c_al_k(328.15)
        # state
        self.mw, self.Tw, self.cap = 0.0, self.Tr, True
        self.TAl, self.al = self.Tr, "desk"           # desk / cup / foam
        self.mN, self.capF, self.cold = 0.0, True, 0.0
        self.Tth, self.probe = self.Tr, False
        self.boil = 0.0

    def c_al(self, tc):
        return c_al_k(tc + 273.15) * self.norm

    def level(self):
        return (self.mw + (self.mAl / 2.70 if self.al == "cup" else 0)) / (math.pi * self.rCup ** 2)

    def step(self, dt):
        if self.mw > 0.5:
            a = self.a0 + self.a1 * self.level() + (0 if self.cap else 0.10 * math.exp((self.Tw - 60) / 14))
            C = self.cw * self.mw + self.Ccup
            self.Tw -= a * (self.Tw - self.Tr) * dt / C
            if self.al == "cup":
                Ca = self.mAl * self.c_al(self.TAl)
                Teq = (C * self.Tw + Ca * self.TAl) / (C + Ca)
                k = 1 - math.exp(-dt * (C + Ca) / (C * 8))
                self.TAl += (Teq - self.TAl) * k
                self.Tw += (Teq - self.Tw) * k
            if not self.cap:
                self.mw = max(0.0, self.mw - dt * 0.0004 * math.exp((self.Tw - 60) / 14))
        if self.al == "desk":
            self.TAl += (self.Tr - self.TAl) * min(1, dt / 420)
        src = self.Tw if (self.probe and self.mw > 2) else self.Tr
        self.Tth += (src - self.Tth) * min(1, dt / 4)
        self.boil = 0.0
        if self.mN > 0.2:
            V = self.mN / RHO_N + (self.mAl / 2.70 if self.al == "foam" else 0)
            rate = self.kN / 60 * (V / (250 / RHO_N)) ** 1.8 * (1 if self.capF else 1.35) + self.cold * 0.55
            self.cold = max(0.0, self.cold - dt / 150)
            if self.al == "foam":
                T = self.TAl + 273.15
                H = self.Hf if T > self.TL else self.Hf * 9
                P = H * (T - 77.3)
                C = self.mAl * c_al_k(T) * self.norm
                dT = min(T - 77.3, P * dt / C)
                self.TAl -= dT
                rate += dT * C / dt / self.lam
                self.boil = P
            self.mN = max(0.0, self.mN - rate * dt)
        self.Tdew -= dt * 0.0008


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_scale(cv, x, y, s=1.0):
    cv.create_oval(x - 40 * s, y - 14 * s, x + 40 * s, y + 14 * s, fill="#eef0f2", outline="#999")
    cv.create_rectangle(x - 12 * s, y + 6 * s, x + 12 * s, y + 14 * s, fill="#2b2e33", outline="")


def art_cup(cv, x, y, s=1.0):
    cv.create_polygon(x - 18 * s, y - 28 * s, x + 18 * s, y - 28 * s, x + 14 * s, y + 28 * s, x - 14 * s, y + 28 * s, fill="#eceef0", outline="#999")


def art_therm(cv, x, y, s=1.0):
    cv.create_rectangle(x - 16 * s, y - 26 * s, x + 16 * s, y + 26 * s, fill="#e9ecef", outline="#999")
    cv.create_rectangle(x - 12 * s, y - 20 * s, x + 12 * s, y, fill="#b9c6a6", outline="")


def art_al(cv, x, y, s=1.0):
    cv.create_rectangle(x - 12 * s, y - 12 * s, x + 12 * s, y + 12 * s, fill="#c3c8cd", outline="#7c8288")


def art_dewar(cv, x, y, s=1.0):
    cv.create_rectangle(x - 18 * s, y - 40 * s, x + 18 * s, y + 40 * s, fill="#c0392b", outline="#7a1c17")


def art_jar(cv, x, y, s=1.0):
    cv.create_rectangle(x - 20 * s, y - 24 * s, x + 20 * s, y + 24 * s, fill="#e1edf2", outline="#8fa7b4")


def art_foam(cv, x, y, s=1.0):
    cv.create_polygon(x - 22 * s, y - 30 * s, x + 22 * s, y - 30 * s, x + 17 * s, y + 30 * s, x - 17 * s, y + 30 * s, fill="#f7f7f2", outline="#999")


def art_ln2(cv, x, y, s=1.0):
    cv.create_rectangle(x - 22 * s, y - 36 * s, x + 22 * s, y + 36 * s, fill="#aeb4ba", outline="#666")
    cv.create_text(x, y, text="LN2", fill="#2b6cb0", font=("Helvetica", max(6, int(9 * s)), "bold"))


ART = {"scale": art_scale, "cup": art_cup, "therm": art_therm, "alcyl": art_al, "dewar": art_dewar,
       "jar": art_jar, "foam": art_foam, "ln2": art_ln2}
PARTS = [
    ("scale", ("[4] 전자저울 (1 g)", "[4] Electronic scales (1 g)"), []),
    ("cup",   ("[1] 플라스틱 컵 + 뚜껑", "[1] Plastic cup + cap"), []),
    ("therm", ("[2] 디지털 온도계", "[2] Digital thermometer"), ["cup"]),
    ("alcyl", ("[3] 알루미늄 원기둥", "[3] Aluminium cylinder"), []),
    ("dewar", ("[6] 뜨거운 물 보온병", "[6] Dewar, hot water"), []),
    ("jar",   ("[7] 헌 물 통", "[7] Jar for used water"), []),
    ("foam",  ("스티로폼 컵 + 뚜껑", "Styrofoam cup + cap"), []),
    ("ln2",   ("액체 질소 듀어병", "Dewar of liquid nitrogen"), ["foam"]),
]
ZONES = {"scale": (380, 440, 120, 40), "cup": (300, 380, 50, 70), "therm": (220, 400, 40, 60), "alcyl": (460, 400, 30, 30),
         "dewar": (120, 380, 50, 110), "jar": (600, 410, 50, 60), "foam": (520, 300, 55, 70), "ln2": (660, 300, 55, 90)}
SCENE_TITLE = ("실험 장치 — 1부: 컵·온도계·저울·보온병, 2부: 스티로폼 컵·액체 질소",
               "The apparatus — part 1: cup, thermometer, scales, Dewar; part 2: foam cup and liquid nitrogen")
APP_TITLE = ("APhO 2006 실험 — 알루미늄의 비열과 액체 질소의 증발 잠열",
             "APhO 2006 Experiment — Specific heat of aluminium and latent heat of nitrogen")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.t = 0.0
        self.speed = tk.IntVar(value=1)
        self.on_scale = tk.StringVar(value="none")
        self.al_at = tk.StringVar(value="desk")
        self.scale_on, self.zero, self.idle = False, 0.0, 0.0
        self.sw_acc, self.sw_run, self.sw_t0 = 0.0, False, 0.0
        self.mark = None
        self.build()
        self.refresh()

    def P(self):
        return self.app.placed

    def load(self):
        ph, w = self.ph, self.on_scale.get()
        if w == "cup":
            return ph.mCup + ph.mw + (ph.mAl if ph.al == "cup" else 0)
        if w == "foam":
            return ph.mFoam + ph.mN + (ph.mAl if ph.al == "foam" else 0)
        if w == "alcyl":
            return ph.mAl
        return 0.0

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("전자저울", "Scales"))
        f.pack(fill="x", pady=2)
        self.dM = tk.Label(f, text="", font=("Courier", 18, "bold"), bg="#a9c4a0", width=10)
        self.dM.pack(pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("켜기 / 영점", "On / zero"), command=self.tare).pack(side="left", padx=2)
        ttk.Button(row, text=T("윗면 누르기", "Press the top"), command=self.press).pack(side="left", padx=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("저울 위:", "On the pan:")).pack(side="left")
        for v, lab in (("none", T("없음", "nothing")), ("cup", T("컵", "cup")), ("foam", T("스티로폼 컵", "foam cup")), ("alcyl", T("원기둥", "cylinder"))):
            ttk.Radiobutton(row, text=lab, value=v, variable=self.on_scale, command=self.press).pack(side="left")

        f = ttk.LabelFrame(ctl, text=T("온도계 (위: 탐침, 아래: 실온)", "Thermometer (top: probe, bottom: room)"))
        f.pack(fill="x", pady=2)
        self.dT = tk.Label(f, text="", font=("Courier", 18, "bold"), bg="#b9c6a6", width=10)
        self.dT.pack()
        self.dTr = tk.Label(f, text="", font=("Courier", 11), bg="#b9c6a6", width=14)
        self.dTr.pack()

        f = ttk.LabelFrame(ctl, text=T("뜨거운 물 (컵)", "Hot water (cup)"))
        f.pack(fill="x", pady=2)
        stepper(f, T("붓기 / 덜기", "Pour / remove"), [("+10 g", lambda: self.pour(10)), ("+2 g", lambda: self.pour(2)), ("−5 g", lambda: self.out(5)), ("−1 g", lambda: self.out(1))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.cap_btn = ttk.Button(row, text="", command=self.toggle_cap)
        self.cap_btn.pack(side="left", padx=2)
        ttk.Button(row, text=T("펜으로 수위 표시", "Mark the level"), command=self.do_mark).pack(side="left", padx=2)
        ttk.Button(row, text=T("컵 비우기", "Empty the cup"), command=lambda: self.out(999)).pack(side="left", padx=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("원기둥:", "Cylinder:")).pack(side="left")
        for v, lab in (("desk", T("책상", "desk")), ("cup", T("컵 속", "in the cup")), ("foam", T("질소 속", "in nitrogen"))):
            ttk.Radiobutton(row, text=lab, value=v, variable=self.al_at, command=self.move_al).pack(side="left")
        self.probe = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text=T("온도계 탐침을 컵에 꽂기", "Probe in the cup"), variable=self.probe, command=self.set_probe).pack(anchor="w")

        f = ttk.LabelFrame(ctl, text=T("액체 질소 (스티로폼 컵)", "Liquid nitrogen (foam cup)"))
        f.pack(fill="x", pady=2)
        stepper(f, T("붓기", "Pour"), [("+25 g", lambda: self.pour_n(25)), ("+5 g", lambda: self.pour_n(5))])

        f = ttk.LabelFrame(ctl, text=T("타이머 · 시간 빠르게", "Timer · speed up"))
        f.pack(fill="x", pady=2)
        self.sw_lbl = tk.Label(f, text="0:00.0", font=("Courier", 18, "bold"), bg="#101317", fg="#e8eef2", width=10)
        self.sw_lbl.pack()
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.sw_btn = ttk.Button(row, text=T("시작", "Start"), command=self.sw_toggle)
        self.sw_btn.pack(side="left", padx=2)
        ttk.Button(row, text=T("리셋", "Reset"), command=self.sw_reset).pack(side="left", padx=2)
        for v in (1, 5, 20):
            ttk.Radiobutton(row, text="×%d" % v, value=v, variable=self.speed).pack(side="left")

        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        ttk.Button(f, text=T("시간·온도·질량 적기", "Record time, T and mass"), command=self.record).pack(fill="x")
        self.sheet = DataSheet(f, [("t", "t (s)", 70), ("T", "T (°C)", 70), ("M", "M (g)", 70)], height=6)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=360)
        self.warn.pack(anchor="w")

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("두 컵의 단면", "The two cups in section"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cups = tk.Canvas(right, width=860, height=330, bg="#eceae4", highlightthickness=0)
        self.cups.pack()
        ttk.Label(right, text=T("그림 1 — 알루미늄 비열 (임의 단위) 대 T (K); 한 칸 10 K × 0.25", "Fig. 1 — c_Al (arb. units) against T (K); one cell 10 K × 0.25"),
                  font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(6, 0))
        self.graph = tk.Canvas(right, width=860, height=300, bg="#ffffff", highlightthickness=0)
        self.graph.pack()
        self.draw_graph()

    # ---- controls -----------------------------------------------------------
    def tare(self):
        if "scale" not in self.P():
            return
        self.scale_on, self.zero, self.idle = True, self.load(), 0.0

    def press(self):
        self.idle = 0.0

    def pour(self, m):
        ph = self.ph
        if not {"cup", "dewar"} <= self.P():
            self.warn.config(text=T("컵과 보온병이 필요합니다.", "Needs the cup and the Dewar."))
            return
        if ph.cap:
            self.warn.config(text=T("컵 뚜껑을 먼저 여세요.", "Open the cup's cap first."))
            return
        dm = m * random.uniform(0.8, 1.2)
        ph.Tw = (ph.mw * ph.Tw + dm * ph.Tdew) / (ph.mw + dm) if ph.mw > 0.5 else ph.Tdew - 1.5
        ph.mw += dm
        self.press()

    def out(self, m):
        ph = self.ph
        if ph.mw < 0.5 or "jar" not in self.P() or ph.cap:
            return
        ph.mw -= min(ph.mw, ph.mw if m >= 999 else m * random.uniform(0.8, 1.2))
        if ph.mw < 0.5:
            ph.mw = 0.0
        self.press()

    def toggle_cap(self):
        self.ph.cap = not self.ph.cap

    def do_mark(self):
        if self.ph.mw > 1:
            self.mark = self.ph.level()

    def move_al(self):
        v, ph = self.al_at.get(), self.ph
        if ph.al == "foam" and ph.TAl < -60 and v != "foam":
            self.warn.config(text=T("액체 질소에 넣었던 원기둥은 만지지 마세요!", "Never touch the cylinder after it has been in nitrogen!"))
            self.al_at.set("foam")
            return
        if v == "cup" and ph.cap:
            self.warn.config(text=T("컵 뚜껑을 먼저 여세요.", "Open the cup's cap first."))
            self.al_at.set(ph.al)
            return
        if v == "foam" and "foam" not in self.P():
            self.al_at.set(ph.al)
            return
        ph.al = v

    def set_probe(self):
        self.ph.probe = self.probe.get() and "therm" in self.P()

    def pour_n(self, m):
        ph = self.ph
        if not {"foam", "ln2"} <= self.P():
            return
        dm = m * random.uniform(0.8, 1.2)
        ph.cold = 1.0 if ph.mN < 1 else min(1.0, ph.cold + dm / 300)
        ph.mN += dm
        self.press()

    def sw_value(self):
        return self.sw_acc + (self.t - self.sw_t0 if self.sw_run else 0.0)

    def sw_toggle(self):
        if self.sw_run:
            self.sw_acc += self.t - self.sw_t0
        else:
            self.sw_t0 = self.t
        self.sw_run = not self.sw_run
        self.sw_btn.config(text=T("정지", "Stop") if self.sw_run else T("시작", "Start"))

    def sw_reset(self):
        self.sw_acc, self.sw_run = 0.0, False
        self.sw_btn.config(text=T("시작", "Start"))

    def scale_text(self):
        if "scale" not in self.P():
            return ""
        if not self.scale_on:
            return "- - -"
        return "%d g" % round(self.load() - self.zero)

    def therm_text(self):
        if "therm" not in self.P():
            return ""
        return "H" if self.ph.Tth > 70 else "%.1f °C" % self.ph.Tth

    def record(self):
        self.sheet.add(("%.1f" % self.sw_value(), self.therm_text(), self.scale_text()))

    # ---- loop -------------------------------------------------------------
    def tick(self, dt):
        dt *= self.speed.get()
        self.t += dt
        n = max(1, int(dt / 0.05))
        for _ in range(n):
            self.ph.step(dt / n)
        if self.scale_on:
            self.idle += dt
            if self.idle > 60:
                self.scale_on = False
        self.refresh()

    def refresh(self):
        self.dM.config(text=self.scale_text())
        self.dT.config(text=self.therm_text())
        self.dTr.config(text=("%.1f °C" % self.ph.Tr) if "therm" in self.P() else "")
        v = self.sw_value()
        self.sw_lbl.config(text="%d:%04.1f" % (int(v // 60), v % 60))
        self.cap_btn.config(text=T("컵 뚜껑 열기", "Open the cap") if self.ph.cap else T("컵 뚜껑 닫기", "Close the cap"))
        msgs = []
        if self.scale_on and self.idle > 45:
            msgs.append(T("저울이 곧 꺼집니다 — 윗면을 누르세요.", "The scales switch off soon — press the top."))
        if self.ph.mw > 0.5 and not self.ph.cap:
            msgs.append(T("컵 뚜껑이 열려 있습니다.", "The cup's cap is off."))
        if msgs:
            self.warn.config(text="\n".join(msgs))
        self.draw_cups()

    def draw_cups(self):
        cv, ph = self.cups, self.ph
        cv.delete("all")
        z, base = 26.0, 300
        if "cup" in self.P():
            X = lambda x: 220 + x * z
            Y = lambda y: base - y * z
            r, h = ph.rCup, 9.5
            if ph.mw > 0.5:
                cv.create_rectangle(X(-r), Y(ph.level()), X(r), Y(0), fill="#9fc3df", outline="")
            if ph.al == "cup":
                hA = ph.mAl / 2.7 / (math.pi * 1.6 ** 2)
                cv.create_rectangle(X(-1.6), Y(hA), X(1.6), Y(0), fill="#b9bec4", outline="#6b7177")
            if self.probe.get():
                cv.create_line(X(1.2), Y(0.4), X(1.2), Y(h + 2), width=3, fill="#7b8188")
            cv.create_line(X(-r - 0.4), Y(h), X(-r), Y(0), X(r), Y(0), X(r + 0.4), Y(h), width=2, fill="#7c8288")
            if ph.cap:
                cv.create_rectangle(X(-r - 0.6), Y(h + 0.5), X(r + 0.6), Y(h), fill="#f3f3f0", outline="#999")
            if self.mark is not None:
                cv.create_line(X(r - 0.2), Y(self.mark), X(r + 0.9), Y(self.mark), width=2, fill="#1d3fa0")
            cv.create_text(220, base + 18, text=T("플라스틱 컵", "plastic cup"), font=("Helvetica", 10, "bold"))
        if "foam" in self.P():
            X = lambda x: 620 + x * z
            Y = lambda y: base - y * z
            r, h = 4.6, 10.5
            cv.create_rectangle(X(-r), Y(h), X(r), Y(0), fill="#f7f7f2", outline="#aaa")
            cv.create_rectangle(X(-r + 0.5), Y(h), X(r - 0.5), Y(0.6), fill="#ffffff", outline="")
            if ph.mN > 0.2:
                lev = (ph.mN / RHO_N + (ph.mAl / 2.7 if ph.al == "foam" else 0)) / (math.pi * (r - 0.5) ** 2)
                cv.create_rectangle(X(-r + 0.5), Y(0.6 + lev), X(r - 0.5), Y(0.6), fill="#c4dcec", outline="")
                for i in range(min(40, int(ph.boil / 2 + ph.cold * 12))):
                    xx = X(-r + 0.7 + random.random() * (2 * r - 1.4))
                    yy = Y(0.7 + random.random() * lev)
                    cv.create_oval(xx - 2, yy - 2, xx + 2, yy + 2, fill="white", outline="")
            if ph.al == "foam":
                hA = ph.mAl / 2.7 / (math.pi * 1.6 ** 2)
                cv.create_rectangle(X(-1.6), Y(0.6 + hA), X(1.6), Y(0.6), fill="#b9bec4", outline="#6b7177")
            cv.create_text(620, base + 18, text=T("스티로폼 컵", "foam cup"), font=("Helvetica", 10, "bold"))

    def draw_graph(self):
        cv = self.graph
        pl, pt, W, H = 50, 14, 790, 250
        X = lambda T_: pl + T_ / 350.0 * W
        Y = lambda a: pt + H - a / 5.0 * H
        for T_ in range(0, 351, 10):
            cv.create_line(X(T_), pt, X(T_), pt + H, fill="#c9a3a3" if T_ % 50 == 0 else "#f0d8d8")
        for i in range(0, 21):
            a = i * 0.25
            cv.create_line(pl, Y(a), pl + W, Y(a), fill="#c9a3a3" if i % 4 == 0 else "#f0d8d8")
        cv.create_rectangle(pl, pt, pl + W, pt + H, outline="#222")
        for T_ in range(0, 351, 50):
            cv.create_text(X(T_), pt + H + 12, text=str(T_), font=("Helvetica", 8))
        for a in range(0, 6):
            cv.create_text(pl - 10, Y(a), text=str(a), font=("Helvetica", 8))
        pts = []
        for T_ in range(5, 346, 3):
            pts += [X(T_), Y(c_al_k(T_) / 0.2)]
        cv.create_line(pts, fill="#1d3fa0", width=2)


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
