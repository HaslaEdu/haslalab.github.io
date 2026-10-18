#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  10th Asian Physics Olympiad  (APhO 2009, Bangkok, Thailand)
  Experimental Problem 2 :  OSCILLATION OF A WATER-FILLED VESSEL
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* An aluminium vessel (cylinder + two 0.60 cm end plates) full of water
  hangs from two strings (bifilar suspension), upright (a = R) or on its
  side (a = h/2).  The twist is integrated with the exact bifilar restoring
  torque, so large swings really are slower.
* Upright, the water stays still (ideal fluid); on its side, only a hidden
  share of the water near the end plates turns with the vessel.
* The bench shows only the stopwatch, the ruler against the vessel and the
  strings, and the protractor under the swing.  t, M, I and the share of
  water are never displayed.  Units: g, cm, s (g = 978 cm/s^2).
* Hidden truths are randomised every session.
* Standard library only (tkinter).

    Run:   python3 apho2009_E2_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line


# --------------------------------------------------------------------------
#  Physics core  (g, cm, s)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.t = r.uniform(0.57, 0.67)            # wall thickness [cm]
        self.R = 2.50 * r.uniform(0.996, 1.004)   # outer radius [cm]
        self.h = 9.20 * r.uniform(0.996, 1.004)   # total length [cm]
        self.tp = 0.60                            # end plate [cm]
        self.rho, self.g = 2.70, 978.0
        self.fw = r.uniform(0.23, 0.34)           # share of water turning end over end
        self.fa = r.uniform(0.0, 0.006)           # ... and about the axis
        self.tau = r.uniform(70.0, 110.0)         # air damping [s]
        self.L = self.h - 2 * self.tp
        self.th, self.w = 0.0, 0.0

    def Ri(self):
        return self.R - self.t

    def masses(self):
        m1 = self.rho * math.pi * (self.R ** 2 - self.Ri() ** 2) * self.L
        m2 = self.rho * math.pi * self.tp * self.R ** 2
        m3 = math.pi * self.Ri() ** 2 * self.L
        return m1, m2, m3

    def M(self):
        m1, m2, m3 = self.masses()
        return m1 + 2 * m2 + m3

    def Iy(self):
        m1, m2, m3 = self.masses()
        return 0.5 * m1 * (self.R ** 2 + self.Ri() ** 2) + m2 * self.R ** 2 + self.fa * 0.5 * m3 * self.Ri() ** 2

    def Ix(self):
        m1, m2, m3 = self.masses()
        L, r = self.L, self.Ri()
        Ls = (1 - self.fw) * L
        shell = m1 * (L * L / 12 + (self.R ** 2 + r * r) / 4) + 2 * m2 * (self.tp ** 2 / 12 + self.R ** 2 / 4 + (L / 2 + self.tp / 2) ** 2)
        water = m3 * (L * L / 12 + r * r / 4) - math.pi * r * r * Ls * (Ls * Ls / 12 + r * r / 4)
        return shell + water

    def step(self, dt, mode, ell):
        a = self.R if mode == "a" else self.h / 2
        I = self.Iy() if mode == "a" else self.Ix()
        s = math.sin(self.th / 2)
        q = max(1e-6, ell * ell - 4 * a * a * s * s)
        tq = -self.M() * self.g * a * a * math.sin(self.th) / math.sqrt(q)
        self.w += (tq / I - self.w / self.tau) * dt
        self.th += self.w * dt


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_stand(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 110 * s, y + 70 * s, x + 110 * s, y + 82 * s, fill="#3b4047", outline="#1b1d20")
    cv.create_rectangle(x - 100 * s, y - 150 * s, x - 92 * s, y + 70 * s, fill="#9ea4ab", outline="#6b7177")
    cv.create_rectangle(x - 96 * s, y - 146 * s, x + 110 * s, y - 138 * s, fill="#9ea4ab", outline="#6b7177")


def art_string(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 22 * s, y - 14 * s, x + 2 * s, y + 10 * s, fill="#e6d9a8", outline="#a8975a")
    cv.create_oval(x - 14 * s, y - 6 * s, x - 6 * s, y + 2 * s, fill="#8c7a4a", outline="")
    cv.create_oval(x + 4 * s, y - 8 * s, x + 26 * s, y + 6 * s, outline="#bbb", width=2)


def art_vessel(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 18 * s, y - 34 * s, x + 18 * s, y + 34 * s, fill="#c3c8cd", outline="#7c8288")
    cv.create_rectangle(x - 18 * s, y - 34 * s, x + 18 * s, y - 28 * s, fill="#aeb4ba", outline="#7c8288")
    cv.create_rectangle(x - 18 * s, y + 28 * s, x + 18 * s, y + 34 * s, fill="#aeb4ba", outline="#7c8288")


def art_ruler(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 60 * s, y - 7 * s, x + 60 * s, y + 7 * s, fill="#e1edf2", outline="#8fa7b4")
    for i in range(13):
        cv.create_line(x - 58 * s + i * 9.6 * s, y - 7 * s, x - 58 * s + i * 9.6 * s, y - (1 if i % 5 else -1) * s, fill="#333")


def art_prot(cv, x, y, sc=1.0):
    s = sc
    cv.create_arc(x - 30 * s, y - 30 * s, x + 30 * s, y + 30 * s, start=0, extent=180, fill="#e1edf2", outline="#8fa7b4")


def art_sw(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 22 * s, y - 22 * s, x + 22 * s, y + 22 * s, fill="#2b2e33", outline="#111")
    cv.create_rectangle(x - 14 * s, y - 7 * s, x + 14 * s, y + 7 * s, fill="#b9c6a6", outline="")
    cv.create_rectangle(x - 4 * s, y - 30 * s, x + 4 * s, y - 22 * s, fill="#555", outline="")


ART = {"stand": art_stand, "string": art_string, "vessel": art_vessel, "ruler": art_ruler, "prot": art_prot, "sw": art_sw}

PARTS = [
    ("stand",  ("[2] 스탠드", "[2] Stand"), []),
    ("string", ("[5] 나일론 실 + [7] 마스킹 테이프", "[5] Nylon string + [7] masking tape"), ["stand"]),
    ("vessel", ("[1] 물을 채운 용기", "[1] Water-filled vessel"), ["string"]),
    ("prot",   ("[6] 각도기", "[6] Protractor"), ["stand"]),
    ("ruler",  ("[4] 자", "[4] Ruler"), []),
    ("sw",     ("[3] 초시계", "[3] Stopwatch"), []),
]
ZONES = {
    "stand":  (330, 300, 230, 250),
    "string": (380, 170, 60, 40),
    "vessel": (380, 330, 50, 80),
    "prot":   (380, 445, 70, 40),
    "ruler":  (600, 450, 130, 20),
    "sw":     (640, 360, 60, 60),
}
SCENE_TITLE = ("쌍선 매달기 — 스탠드 가로대에 실 두 가닥, 그 아래 용기",
               "Bifilar suspension — two strings from the stand's bar, the vessel below")
APP_TITLE = ("APhO 2009 실험 2 — 물을 채운 용기의 진동",
             "APhO 2009 Experiment 2 — Oscillation of a water-filled vessel")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.mode = "a"
        self.ell = 30.0
        self.t = 0.0
        self.sw_acc, self.sw_run, self.sw_t0 = 0.0, False, 0.0
        self.laps = []
        self.rul_v = 0.0              # where the upright ruler's zero sits below the bar [cm]
        self.drag_turn = None
        self.build()
        self.refresh()

    def ready(self):
        return {"stand", "string", "vessel"} <= self.app.placed

    def a(self):
        return self.ph.R if self.mode == "a" else self.ph.h / 2

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("용기", "Vessel"))
        f.pack(fill="x", pady=3)
        self.mode_lbl = ttk.Label(f, text="")
        self.mode_lbl.pack(anchor="w")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("세워 매달기 (a = R)", "Hang upright (a = R)"), command=lambda: self.set_mode("a")).pack(side="left", padx=2)
        ttk.Button(row, text=T("눕혀 매달기 (a = h/2)", "Hang on its side (a = h/2)"), command=lambda: self.set_mode("b")).pack(side="left", padx=2)
        row = ttk.Frame(f)
        row.pack(fill="x", pady=2)
        ttk.Button(row, text=T("살짝 비틀었다 놓기", "Small twist & let go"), command=self.twist).pack(side="left", padx=2)
        ttk.Button(row, text=T("멈추기", "Hold still"), command=self.hold).pack(side="left", padx=2)
        ttk.Label(f, text=T("위 그림의 용기를 끌어 돌렸다 놓아도 됩니다.", "Or drag the vessel round in the top view and let go."),
                  foreground="#555").pack(anchor="w")

        f = ttk.LabelFrame(ctl, text=T("실 길이 (다시 묶기)", "String length (re-tie)"))
        f.pack(fill="x", pady=3)
        stepper(f, "", [("−1 cm", lambda: self.string(-1)), ("−1 mm", lambda: self.string(-0.1)),
                        ("+1 mm", lambda: self.string(0.1)), ("+1 cm", lambda: self.string(1))])
        stepper(f, T("자 올리기/내리기", "Ruler up/down"), [("▲", lambda: self.ruler(-0.5)), ("▼", lambda: self.ruler(0.5)),
                                                    ("▲1mm", lambda: self.ruler(-0.1)), ("▼1mm", lambda: self.ruler(0.1))])

        f = ttk.LabelFrame(ctl, text=T("초시계", "Stopwatch"))
        f.pack(fill="x", pady=3)
        self.sw_lbl = tk.Label(f, text="0:00.00", font=("Courier", 18, "bold"), bg="#101317", fg="#e8eef2", width=10)
        self.sw_lbl.pack(pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.sw_btn = ttk.Button(row, text=T("시작", "Start"), command=self.sw_toggle)
        self.sw_btn.pack(side="left", padx=2)
        ttk.Button(row, text=T("리셋", "Reset"), command=self.sw_reset).pack(side="left", padx=2)

        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=3)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("ℓ (cm)", "ℓ (cm)")).pack(side="left")
        self.l_entry = ttk.Entry(row, width=6)
        self.l_entry.pack(side="left", padx=2)
        ttk.Label(row, text=T("진동 수", "swings")).pack(side="left")
        self.n_entry = ttk.Entry(row, width=4)
        self.n_entry.insert(0, "50")
        self.n_entry.pack(side="left", padx=2)
        ttk.Button(f, text=T("시간과 함께 적기", "Record with the time"), command=self.record).pack(fill="x", pady=2)
        self.sheet = DataSheet(f, [("m", T("매달기", "hang"), 70), ("l", "ℓ (cm)", 70), ("n", T("진동 수", "swings"), 60),
                                   ("t", T("시간 (s)", "time (s)"), 80)], height=8)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=330)
        self.warn.pack(anchor="w")

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        top = ttk.Frame(right)
        top.pack(fill="x")
        c1 = ttk.Frame(top)
        c1.pack(side="left")
        ttk.Label(c1, text=T("앞에서 — 자로 실의 길이 ℓ을 재시오", "From the front — measure ℓ with the ruler"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.front = tk.Canvas(c1, width=470, height=560, bg="#f4f2ec", highlightthickness=0)
        self.front.pack()
        c2 = ttk.Frame(top)
        c2.pack(side="left", padx=6)
        ttk.Label(c2, text=T("위에서 — 각도기로 진폭을 보시오", "From above — the swing on the protractor"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.topv = tk.Canvas(c2, width=420, height=290, bg="#3b4047", highlightthickness=0)
        self.topv.pack()
        ttk.Label(c2, text=T("용기 재기 — 자를 대어 h와 2R을 읽으시오", "Measure the vessel — read h and 2R on the ruler"), font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(6, 0))
        self.meas = tk.Canvas(c2, width=420, height=240, bg="#e6e2d6", highlightthickness=0)
        self.meas.pack()
        self.topv.bind("<ButtonPress-1>", self.turn_press)
        self.topv.bind("<B1-Motion>", self.turn_move)
        self.topv.bind("<ButtonRelease-1>", self.turn_release)

    # ---- controls -----------------------------------------------------------
    def set_mode(self, m):
        self.mode = m
        self.ph.th = self.ph.w = 0.0

    def twist(self):
        if self.ready():
            self.ph.th = random.choice((-1, 1)) * math.radians(random.uniform(8, 12))
            self.ph.w = 0.0

    def hold(self):
        self.ph.th = self.ph.w = 0.0

    def string(self, dl):
        self.ell = max(12.0, min(50.0, round(self.ell + dl, 1)))
        self.hold()

    def ruler(self, d):
        self.rul_v = round(self.rul_v + d, 2)

    def turn_press(self, ev):
        if self.ready():
            self.drag_turn = (math.atan2(ev.y - 145, ev.x - 210), self.ph.th)

    def turn_move(self, ev):
        if self.drag_turn:
            a0, th0 = self.drag_turn
            d = math.atan2(ev.y - 145, ev.x - 210) - a0
            self.ph.th = max(-1.2, min(1.2, th0 + math.atan2(math.sin(d), math.cos(d))))
            self.ph.w = 0.0

    def turn_release(self, ev):
        self.drag_turn = None

    def sw_value(self):
        return self.sw_acc + (self.t - self.sw_t0 if self.sw_run else 0.0)

    def sw_toggle(self):
        if "sw" not in self.app.placed:
            return
        if self.sw_run:
            self.sw_acc += self.t - self.sw_t0
        else:
            self.sw_t0 = self.t
        self.sw_run = not self.sw_run
        self.sw_btn.config(text=T("정지", "Stop") if self.sw_run else T("시작", "Start"))

    def sw_reset(self):
        self.sw_acc, self.sw_run = 0.0, False
        self.sw_btn.config(text=T("시작", "Start"))

    def record(self):
        self.sheet.add((T("세움", "upright") if self.mode == "a" else T("눕힘", "side"), self.l_entry.get() or "?",
                        self.n_entry.get() or "?", "%.2f" % self.sw_value()))

    # ---- loop -------------------------------------------------------------
    def tick(self, dt):
        self.t += dt
        if self.ready() and not self.drag_turn:
            n = max(1, int(dt / 0.001))
            for _ in range(n):
                self.ph.step(dt / n, self.mode, self.ell)
        self.refresh()

    def refresh(self):
        v = self.sw_value()
        self.sw_lbl.config(text="%d:%05.2f" % (int(v // 60), v % 60))
        self.mode_lbl.config(text=T("지금: 세워 매달기 — 옆면에 실", "Now: upright — strings on the side") if self.mode == "a"
                             else T("지금: 눕혀 매달기 — 끝판에 실", "Now: on its side — strings on the end plates"))
        msgs = []
        if not self.ready():
            msgs.append(T("스탠드, 실, 용기를 먼저 조립하시오.", "Assemble the stand, string and vessel first."))
        if abs(self.ph.th) > 0.35:
            msgs.append(T("진폭이 큽니다 — 주기 공식은 작은 진폭에서만 맞습니다.", "Large amplitude — the period formula holds only for small swings."))
        self.warn.config(text="\n".join(msgs))
        self.draw_front()
        self.draw_top()
        self.draw_meas()

    def draw_front(self):
        cv = self.front
        cv.delete("all")
        z = 8.5                                  # px per cm
        X = lambda x: 235 + x * z
        Y = lambda h: 40 + h * z                 # h: depth below the bar
        if "stand" not in self.app.placed:
            return
        cv.create_rectangle(X(-21), Y(-2), X(-20), Y(64), fill="#9ea4ab", outline="")
        cv.create_rectangle(X(-21), Y(-0.6), X(14), Y(0.6), fill="#9ea4ab", outline="")
        if "string" not in self.app.placed:
            return
        a, th, ph = self.a(), self.ph.th, self.ph
        dz = math.sqrt(max(1, self.ell ** 2 - 4 * a * a * math.sin(th / 2) ** 2))
        for k in (-1, 1):
            cv.create_rectangle(X(k * a) - 5, Y(-1.2), X(k * a) + 5, Y(0.6), fill="#2e3237", outline="")
            if self.ready():
                cv.create_line(X(k * a), Y(0.6), X(k * a * math.cos(th)), Y(dz), fill="#8a8a80")
        if self.ready():
            c, s = abs(math.cos(th)), abs(math.sin(th))
            if self.mode == "a":
                cv.create_rectangle(X(-ph.R), Y(dz - 0.5), X(ph.R), Y(dz - 0.5 + ph.h), fill="#c3c8cd", outline="#6b7177")
            else:
                Lp = ph.h * c + 2 * ph.R * s
                cv.create_rectangle(X(-Lp / 2), Y(dz), X(Lp / 2), Y(dz + 2 * ph.R), fill="#c3c8cd", outline="#6b7177")
            for k in (-1, 1):
                xx = X(k * a * math.cos(th))
                cv.create_rectangle(xx - 4, Y(dz - 0.4), xx + 4, Y(dz + 0.9), fill="#e6d9a8", outline="#a8975a")
        if "ruler" in self.app.placed:           # an upright ruler hung beside the strings, zero at the top
            x0, y0 = X(-a - 4.5), self.rul_v
            cv.create_rectangle(x0, Y(y0 - 0.5), x0 + 3.2 * z, Y(y0 + 30.5), fill="#e1edf2", outline="#8fa7b4")
            for mm in range(0, 301):
                ln = 0.9 * z if mm % 10 == 0 else 0.6 * z if mm % 5 == 0 else 0.35 * z
                cv.create_line(x0 + 3.2 * z - ln, Y(y0 + mm / 10.0), x0 + 3.2 * z, Y(y0 + mm / 10.0), fill="#222")
                if mm % 10 == 0:
                    cv.create_text(x0 + 0.9 * z, Y(y0 + mm / 10.0), text=str(mm // 10), font=("Helvetica", 7))

    def draw_top(self):
        cv = self.topv
        cv.delete("all")
        z, cx, cy = 22.0, 210, 145
        if "prot" in self.app.placed:
            R = 6.2 * z
            cv.create_arc(cx - R, cy - R + 30, cx + R, cy + R + 30, start=0, extent=180, fill="#53606b", outline="#9fb3c0")
            for dg in range(0, 181, 5):
                a = math.radians(dg)
                ln = 12 if dg % 10 == 0 else 6
                cv.create_line(cx + R * math.cos(a), cy + 30 - R * math.sin(a), cx + (R - ln) * math.cos(a), cy + 30 - (R - ln) * math.sin(a), fill="#e6edf2")
                if dg % 30 == 0:
                    cv.create_text(cx + (R - 22) * math.cos(a), cy + 30 - (R - 22) * math.sin(a), text=str(dg), fill="#e6edf2", font=("Helvetica", 8))
        cv.create_rectangle(cx - 16 * z, cy - 0.5 * z, cx + 16 * z, cy + 0.5 * z, fill="#6f757c", outline="")
        if not self.ready():
            return
        ph, th = self.ph, self.ph.th
        u, n = (math.cos(th), -math.sin(th)), (math.sin(th), math.cos(th))
        if self.mode == "a":
            cv.create_oval(cx - ph.R * z, cy - ph.R * z, cx + ph.R * z, cy + ph.R * z, fill="#c3c8cd", outline="#6b7177")
            for k in (-1, 1):
                px, py = cx + k * ph.R * z * u[0], cy + k * ph.R * z * u[1]
                cv.create_oval(px - 5, py - 5, px + 5, py + 5, fill="#e6d9a8", outline="#a8975a")
        else:
            hl, rr_ = ph.h / 2 * z, ph.R * z
            pts = []
            for a_, b_ in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                pts += [cx + u[0] * a_ * hl + n[0] * b_ * rr_, cy + u[1] * a_ * hl + n[1] * b_ * rr_]
            cv.create_polygon(pts, fill="#c3c8cd", outline="#6b7177")
            for k in (-1, 1):
                px, py = cx + k * hl * u[0], cy + k * hl * u[1]
                cv.create_oval(px - 5, py - 5, px + 5, py + 5, fill="#e6d9a8", outline="#a8975a")
        for k in (-1, 1):
            cv.create_oval(cx + k * self.a() * z - 3, cy - 3, cx + k * self.a() * z + 3, cy + 3, fill="#2e3237", outline="")

    def draw_meas(self):
        cv = self.meas
        cv.delete("all")
        if "vessel" not in self.app.placed or "ruler" not in self.app.placed:
            cv.create_text(210, 120, text=T("용기와 자가 있어야 잴 수 있습니다", "needs the vessel and the ruler"), fill="#69717a")
            return
        ph, z = self.ph, 30.0
        X = lambda x: 40 + x * z
        Y = lambda y: 130 - y * z
        cv.create_rectangle(X(0.4), Y(ph.R), X(0.4 + ph.h), Y(-ph.R), fill="#c3c8cd", outline="#6b7177")
        for xx in (0.4 + 0.6, 0.4 + ph.h - 0.6):
            cv.create_line(X(xx), Y(ph.R), X(xx), Y(-ph.R), fill="#8c9298")
        cv.create_rectangle(X(-0.3), Y(-ph.R), X(11), Y(-ph.R - 1.4), fill="#e1edf2", outline="#8fa7b4")
        for mm in range(0, 106):
            ln = 0.6 if mm % 10 == 0 else 0.4 if mm % 5 == 0 else 0.25
            cv.create_line(X(mm / 10.0), Y(-ph.R), X(mm / 10.0), Y(-ph.R - ln), fill="#222")
            if mm % 10 == 0:
                cv.create_text(X(mm / 10.0), Y(-ph.R - 1.0), text=str(mm // 10), font=("Helvetica", 7))
        x0 = X(0.4 + ph.h + 0.15)            # an upright ruler at the end, zero on the bench
        cv.create_rectangle(x0, Y(-ph.R + 0.0), x0 + 1.4 * z, Y(-ph.R + 6.5), fill="#e1edf2", outline="#8fa7b4")
        for mm in range(0, 61):
            ln = 0.6 if mm % 10 == 0 else 0.4 if mm % 5 == 0 else 0.25
            cv.create_line(x0, Y(-ph.R + mm / 10.0), x0 + ln * z, Y(-ph.R + mm / 10.0), fill="#222")
            if mm % 10 == 0:
                cv.create_text(x0 + 1.0 * z, Y(-ph.R + mm / 10.0), text=str(mm // 10), font=("Helvetica", 7))


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
