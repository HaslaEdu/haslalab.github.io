#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  10th Asian Physics Olympiad  (APhO 2009, Bangkok, Thailand)
  Experimental Problem 1 :  THE EARTH'S HORIZONTAL MAGNETIC FIELD
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* A bar magnet hangs on nylon string on the axis of a 130-turn square coil.
  The coil field comes from Biot-Savart over the four sides; the swing is
  integrated with the string's torsion (kappa ~ 1/l^2) and air damping, so
  a short string really does change the period.
* The bench shows only what the instruments show: the voltmeter across the
  coil, the stopwatch, the ruler under the magnet and the side view.
  B_H, the moment m, the current and the coil field are never displayed.
* The coil warms up after switching on: its resistance creeps for minutes.
* Hidden truths are randomised every session.
* Standard library only (tkinter).

    Run:   python3 apho2009_E1_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line

MU0 = 4e-7 * math.pi


# --------------------------------------------------------------------------
#  Physics core  (SI)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.BH = r.uniform(3.0e-5, 4.1e-5)       # Earth's horizontal field [T]
        self.a = 0.100 * r.uniform(0.992, 1.008)  # side of the square coil [m]
        self.N = 130
        self.R0 = 5.2 * r.uniform(0.965, 1.035)   # coil resistance, cold [ohm]
        self.alphaR = 0.0039
        self.Rth = 1.4                            # K per W
        self.tauTh = 110.0                        # s
        self.M = 0.0150 * r.uniform(0.99, 1.01)   # magnet mass [kg]
        self.L = 0.0300 * r.uniform(0.98, 1.02)   # magnet length [m]
        self.r = 0.0050 * r.uniform(0.97, 1.03)   # magnet radius [m]
        self.mom = r.uniform(1.05, 1.55)          # magnetic moment [A m^2]
        self.kap = 2.7e-9 * r.uniform(0.8, 1.25)  # string torsion, kappa = kap / l^2
        self.tau = 55.0 * r.uniform(0.85, 1.15)   # damping time [s]
        self.hc = 0.140                           # coil centre above platform [m]
        self.hs = 0.320                           # string support above platform [m]
        self.Vmax = 12.0
        self.Tc = 0.0                             # coil temperature rise [K]
        self.phi = 0.0                            # heading of the magnet [rad]
        self.dphi = 0.0
        self.phi0 = 0.0                           # heading of the untwisted string

    def I_mag(self):
        return self.M * (self.L ** 2 / 12.0 + self.r ** 2 / 4.0)

    def R_coil(self):
        return self.R0 * (1.0 + self.alphaR * self.Tc)

    def current(self, V, on, rev):
        return (-1.0 if rev else 1.0) * V / self.R_coil() if on else 0.0

    @staticmethod
    def seg_B(p1, p2, p, I):
        r1 = [p1[k] - p[k] for k in range(3)]
        r2 = [p2[k] - p[k] for k in range(3)]
        cx = r1[1] * r2[2] - r1[2] * r2[1]
        cy = r1[2] * r2[0] - r1[0] * r2[2]
        cz = r1[0] * r2[1] - r1[1] * r2[0]
        c2 = cx * cx + cy * cy + cz * cz
        if c2 < 1e-14:
            return [0.0, 0.0, 0.0]
        l1 = math.sqrt(sum(v * v for v in r1))
        l2 = math.sqrt(sum(v * v for v in r2))
        dot = sum(r1[k] * r2[k] for k in range(3))
        k = MU0 * I / (4 * math.pi) * (l1 + l2) / (l1 * l2 * (l1 * l2 + dot))
        return [cx * k, cy * k, cz * k]

    def coil_B(self, p, i):
        h, z0 = self.a / 2, self.hc
        c = [(0, -h, z0 - h), (0, h, z0 - h), (0, h, z0 + h), (0, -h, z0 + h)]
        B = [0.0, 0.0, 0.0]
        for k in range(4):
            b = self.seg_B(c[k], c[(k + 1) % 4], p, i * self.N)
            B = [B[j] + b[j] for j in range(3)]
        return B

    def net_B(self, x, ell, V, on, rev):
        Bc = self.coil_B((x, 0.0, self.hs - ell), self.current(V, on, rev))
        return self.BH + Bc[0], Bc[1]

    def step(self, dt, x, ell, V, on, rev, hung):
        P = V * V / self.R_coil() if on else 0.0
        self.Tc += (P * self.Rth - self.Tc) * min(1.0, dt / self.tauTh)
        if not hung:
            return
        bx, by = self.net_B(x, ell, V, on, rev)
        Bh, eq = math.hypot(bx, by), math.atan2(by, bx)
        I = self.I_mag()
        kap = self.kap / max(0.01, ell) ** 2
        d = math.atan2(math.sin(self.phi - eq), math.cos(self.phi - eq))
        acc = (-self.mom * Bh * math.sin(d) - kap * (self.phi - self.phi0)
               - 2 * I / self.tau * self.dphi) / I
        self.dphi += acc * dt
        self.phi += self.dphi * dt


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_stand(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 150 * s, y + 20 * s, x + 150 * s, y + 34 * s, fill="#c9a06a", outline="#8a6a3a")
    cv.create_rectangle(x - 120 * s, y - 40 * s, x - 108 * s, y + 20 * s, fill="#b5642d", outline="#7a3f18")
    cv.create_rectangle(x - 126 * s, y - 46 * s, x - 102 * s, y - 34 * s, fill="#b5642d", outline="#7a3f18")
    cv.create_rectangle(x + 130 * s, y - 120 * s, x + 140 * s, y + 20 * s, fill="#a87f4a", outline="#6f5430")
    cv.create_rectangle(x - 95 * s, y - 124 * s, x + 140 * s, y - 116 * s, fill="#a87f4a", outline="#6f5430")


def art_magnet(cv, x, y, sc=1.0):
    s = sc
    cv.create_line(x, y - 40 * s, x, y - 6 * s, fill="#888")
    cv.create_rectangle(x - 16 * s, y - 6 * s, x, y + 6 * s, fill="#c0392b", outline="#7a1c17")
    cv.create_rectangle(x, y - 6 * s, x + 16 * s, y + 6 * s, fill="#9aa0a6", outline="#5f656b")


def art_dmm(cv, x, y, sc=1.0):
    s = sc
    rr(cv, x - 26 * s, y - 40 * s, x + 26 * s, y + 40 * s, 6 * s, fill="#e8c02a", outline="#9a7c10")
    cv.create_rectangle(x - 18 * s, y - 32 * s, x + 18 * s, y - 14 * s, fill="#b9c6a6", outline="")
    cv.create_oval(x - 10 * s, y - 2 * s, x + 10 * s, y + 18 * s, fill="#1e2023", outline="")


def art_psu(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 40 * s, y - 26 * s, x + 40 * s, y + 26 * s, fill="#d9dcdf", outline="#8a8f96")
    cv.create_rectangle(x - 32 * s, y - 18 * s, x + 2 * s, y - 2 * s, fill="#0d1f12", outline="")
    cv.create_oval(x + 12 * s, y - 16 * s, x + 30 * s, y + 2 * s, fill="#2b2e33", outline="")


def art_ruler(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 60 * s, y - 7 * s, x + 60 * s, y + 7 * s, fill="#e1edf2", outline="#8fa7b4")
    for i in range(13):
        cv.create_line(x - 58 * s + i * 9.6 * s, y - 7 * s, x - 58 * s + i * 9.6 * s, y - (1 if i % 5 else -1) * s, fill="#333")


def art_prot(cv, x, y, sc=1.0):
    s = sc
    cv.create_arc(x - 30 * s, y - 30 * s, x + 30 * s, y + 30 * s, start=0, extent=180, fill="#e1edf2", outline="#8fa7b4")


ART = {"stand": art_stand, "magnet": art_magnet, "dmm": art_dmm, "psu": art_psu,
       "ruler": art_ruler, "prot": art_prot}

PARTS = [
    ("stand",  ("[5] 나무 받침대 + 정사각형 코일", "[5] Wooden stand + square coil"), []),
    ("magnet", ("[2] 막대자석 + 나일론 실", "[2] Bar magnet + nylon string"), ["stand"]),
    ("psu",    ("[4] 전원 장치 (책상 밑)", "[4] Power supply (under the table)"), ["stand"]),
    ("dmm",    ("[3] 전압계 (코일 양단)", "[3] Voltmeter (across the coil)"), ["psu"]),
    ("ruler",  ("[7] 자", "[7] Ruler"), ["stand"]),
    ("prot",   ("[8] 각도기", "[8] Protractor"), ["stand"]),
]

ZONES = {
    "stand":  (360, 400, 320, 170),
    "magnet": (470, 330, 50, 90),
    "psu":    (600, 560, 90, 60),
    "dmm":    (660, 400, 60, 90),
    "ruler":  (430, 432, 130, 20),
    "prot":   (300, 432, 70, 40),
}
SCENE_TITLE = ("그림 2의 장치 — 전원 장치는 자석에서 멀리, 책상 밑에",
               "The set-up of Figure 2 — the power supply far below the table")
APP_TITLE = ("APhO 2009 실험 1 — 지구 자기장의 수평 성분",
             "APhO 2009 Experiment 1 — The Earth's horizontal magnetic field")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.V = 0.0
        self.on = False
        self.rev = False
        self.x = 0.200               # magnet along the axis [m] (read on the ruler)
        self.ell = 0.180             # string length [m]
        self.on_t = None
        self.t = 0.0
        self.sw_acc, self.sw_run, self.sw_t0 = 0.0, False, 0.0
        self.noise = 0.0
        self.build()
        self.refresh()

    def ready(self):
        return {"stand", "magnet"} <= self.app.placed

    # ---- UI ---------------------------------------------------------------
    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("전원 장치 (책상 밑)", "Power supply (under the table)"))
        f.pack(fill="x", pady=3)
        self.ps_lbl = tk.Label(f, text="--.- V", font=("Courier", 18, "bold"), bg="#0d1f12", fg="#5cff7a", width=10)
        self.ps_lbl.pack(pady=2)
        stepper(f, T("전압", "Voltage"), [("−1", lambda: self.setV(-1)), ("−0.1", lambda: self.setV(-0.1)),
                                         ("+0.1", lambda: self.setV(0.1)), ("+1", lambda: self.setV(1))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.on_btn = ttk.Button(row, text=T("전원 켜기", "Switch on"), command=self.toggle)
        self.on_btn.pack(side="left", padx=2)
        self.rev_btn = ttk.Button(row, text=T("극성: 정방향", "Polarity: normal"), command=self.toggle_rev)
        self.rev_btn.pack(side="left", padx=2)

        f = ttk.LabelFrame(ctl, text=T("전압계 (코일 양단)", "Voltmeter (across the coil)"))
        f.pack(fill="x", pady=3)
        self.dmm = tk.Label(f, text="- . - - -", font=("Courier", 18, "bold"), bg="#b9c6a6", fg="#1b2316", width=10)
        self.dmm.pack(pady=2)

        f = ttk.LabelFrame(ctl, text=T("매단 자석", "Hanging magnet"))
        f.pack(fill="x", pady=3)
        stepper(f, T("위치 (축 방향)", "Along the axis"), [("◀1cm", lambda: self.move(-0.01)), ("◀1mm", lambda: self.move(-0.001)),
                                                     ("1mm▶", lambda: self.move(0.001)), ("1cm▶", lambda: self.move(0.01))])
        stepper(f, T("실 길이", "String"), [(T("1cm 짧게", "−1 cm"), lambda: self.string(-0.01)), (T("1cm 길게", "+1 cm"), lambda: self.string(0.01))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("살짝 비틀기", "Small twist"), command=self.twist).pack(side="left", padx=2)
        ttk.Button(row, text=T("멈추기", "Hold still"), command=self.hold).pack(side="left", padx=2)

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
        ttk.Label(row, text=T("자 눈금 x (cm)", "ruler x (cm)")).pack(side="left")
        self.x_entry = ttk.Entry(row, width=7)
        self.x_entry.pack(side="left", padx=2)
        ttk.Label(row, text=T("진동 수", "swings")).pack(side="left")
        self.n_entry = ttk.Entry(row, width=4)
        self.n_entry.insert(0, "20")
        self.n_entry.pack(side="left", padx=2)
        ttk.Button(f, text=T("전압·시간과 함께 적기", "Record with V and time"), command=self.record).pack(fill="x", pady=2)
        self.sheet = DataSheet(f, [("x", T("x (cm)", "x (cm)"), 70), ("n", T("진동 수", "swings"), 60),
                                   ("V", T("전압계 (V)", "voltmeter (V)"), 90), ("t", T("시간 (s)", "time (s)"), 80)], height=8)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=330)
        self.warn.pack(anchor="w")

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("위에서 본 받침대 — 자석 위치는 자로 직접 읽으시오",
                                "The stand from above — read the magnet's position on the ruler"),
                  font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.top = tk.Canvas(right, width=900, height=330, bg="#2a2d33", highlightthickness=0)
        self.top.pack(fill="x")
        ttk.Label(right, text=T("옆에서 본 모습 — 코일 중심(점선)과 자석의 높이",
                                "From the side — the coil centre (dashed) and the magnet's height"),
                  font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(6, 0))
        self.side = tk.Canvas(right, width=900, height=300, bg="#f4f2ec", highlightthickness=0)
        self.side.pack(fill="x")

    # ---- controls -----------------------------------------------------------
    def setV(self, dv):
        self.V = max(0.0, min(self.ph.Vmax, round(self.V + dv, 1)))

    def toggle(self):
        if "stand" not in self.app.placed or "psu" not in self.app.placed:
            self.warn.config(text=T("받침대와 전원 장치를 먼저 조립하시오.", "Assemble the stand and the power supply first."))
            return
        self.on = not self.on
        self.on_t = self.t if self.on else None
        self.on_btn.config(text=T("전원 끄기", "Switch off") if self.on else T("전원 켜기", "Switch on"))

    def toggle_rev(self):
        self.rev = not self.rev
        self.rev_btn.config(text=T("극성: 반대", "Polarity: reversed") if self.rev else T("극성: 정방향", "Polarity: normal"))

    def move(self, dx):
        if self.ready():
            self.x = max(0.05, min(0.46, round(self.x + dx, 4)))
            self.ph.dphi *= 0.4

    def string(self, dl):
        if self.ready():
            self.ell = max(0.02, min(0.26, round(self.ell + dl, 3)))
            self.ph.dphi *= 0.3

    def twist(self):
        if self.ready():
            self.ph.dphi += random.choice((-1, 1)) * random.uniform(0.9, 1.2)

    def hold(self):
        bx, by = self.ph.net_B(self.x, self.ell, self.V, self.on, self.rev)
        self.ph.phi, self.ph.dphi = math.atan2(by, bx), 0.0

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

    def dmm_text(self):
        if "dmm" not in self.app.placed:
            return "- . - - -"
        if not self.on:
            return " 0.000"
        v = (-1 if self.rev else 1) * self.V * 0.9985 + self.noise
        return "%6.3f" % v

    def record(self):
        self.sheet.add((self.x_entry.get() or "?", self.n_entry.get() or "?", self.dmm_text().strip(), "%.2f" % self.sw_value()))

    # ---- loop -------------------------------------------------------------
    def tick(self, dt):
        self.t += dt
        n = max(1, int(dt / 0.002))
        for _ in range(n):
            self.ph.step(dt / n, self.x, self.ell, self.V, self.on, self.rev, self.ready())
        if int(self.t * 3) != int((self.t - dt) * 3):
            self.noise = random.uniform(-0.001, 0.001)
        self.refresh()

    def refresh(self):
        self.ps_lbl.config(text=("%4.1f V" % self.V) if self.on else "--.- V")
        self.dmm.config(text=self.dmm_text())
        v = self.sw_value()
        self.sw_lbl.config(text="%d:%05.2f" % (int(v // 60), v % 60))
        msgs = []
        if not self.ready():
            msgs.append(T("받침대와 자석을 먼저 조립하시오.", "Assemble the stand and the magnet first."))
        if self.on and self.on_t is not None and self.t - self.on_t < 300:
            msgs.append(T("전원을 켠 지 %d초 — 코일이 아직 데워지는 중" % (self.t - self.on_t),
                          "On for %d s — the coil is still warming up" % (self.t - self.on_t)))
        if self.ell < 0.06:
            msgs.append(T("실이 매우 짧습니다 — 비틀림이 주기에 영향을 줄 수 있습니다.", "Very short string — its torsion may change the period."))
        self.warn.config(text="\n".join(msgs))
        self.draw_top()
        self.draw_side()

    def draw_top(self):
        cv = self.top
        cv.delete("all")
        W, H = 900, 330
        z = 1500.0                        # px per metre
        X = lambda xm: 70 + xm * z
        Y = lambda ym: H / 2 + ym * z
        if "stand" not in self.app.placed:
            cv.create_text(W / 2, H / 2, text=T("받침대를 조립하면 보입니다", "assemble the stand to see this"), fill="#9aa3ab")
            return
        cv.create_rectangle(X(-0.04), Y(-0.09), X(0.52), Y(0.09), fill="#d2ac78", outline="")
        h = self.ph.a / 2
        cv.create_rectangle(X(-0.006), Y(-h - 0.006), X(0.006), Y(h + 0.006), fill="#b5642d", outline="#7a3f18")
        cv.create_text(W - 14, 14, anchor="ne", fill="#9aa3ab", text=T("자북 (지구 자기장) →", "magnetic north (Earth's field) →"))
        if "ruler" in self.app.placed:
            y0 = Y(0.035)
            cv.create_rectangle(X(-0.035), y0, X(0.275), y0 + 0.032 * z, fill="#e1edf2", outline="#8fa7b4")
            for mm in range(0, 301):
                xx = X(-0.03 + mm / 1000.0)
                ln = 13 if mm % 10 == 0 else 9 if mm % 5 == 0 else 5
                cv.create_line(xx, y0, xx, y0 + ln, fill="#222")
                if mm % 10 == 0:
                    cv.create_text(xx, y0 + 22, text=str(mm // 10), font=("Helvetica", 8), fill="#222")
        if "prot" in self.app.placed:
            cx, cy = X(0.30), Y(0.0)
            R = 0.05 * z
            cv.create_arc(cx - R, cy - R, cx + R, cy + R, start=180, extent=180, fill="#dfe8ee", outline="#8fa7b4", style="pieslice")
            for dg in range(0, 181, 10):
                a = math.radians(180 + dg)
                cv.create_line(cx + R * math.cos(a), cy - R * math.sin(a), cx + (R - 9) * math.cos(a), cy - (R - 9) * math.sin(a), fill="#223")
        if self.ready():
            cx, cy = X(self.x), Y(0.0)
            L, r, p = self.ph.L * z / 2, self.ph.r * z, self.ph.phi
            u = (math.cos(p), -math.sin(p))
            n = (-u[1], u[0])
            for sgn, col in ((-1, "#c0392b"), (1, "#9aa0a6")):
                pts = []
                for a, b in ((0, -1), (sgn, -1), (sgn, 1), (0, 1)):
                    pts += [cx + u[0] * a * L + n[0] * b * r, cy + u[1] * a * L + n[1] * b * r]
                cv.create_polygon(pts, fill=col, outline="#333")
            cv.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, fill="#fff", outline="")

    def draw_side(self):
        cv = self.side
        cv.delete("all")
        W, H = 900, 300
        z = 750.0
        X = lambda xm: 70 + xm * z
        Y = lambda zm: H - 20 - zm * z
        if "stand" not in self.app.placed:
            return
        cv.create_rectangle(X(-0.04), Y(0), X(0.52), Y(-0.016), fill="#c9a06a", outline="")
        h = self.ph.a / 2
        cv.create_rectangle(X(-0.006), Y(self.ph.hc + h + 0.006), X(0.006), Y(self.ph.hc - h - 0.006), fill="#b5642d", outline="")
        cv.create_rectangle(X(-0.022), Y(self.ph.hc - h - 0.006), X(0.022), Y(0), fill="#a87f4a", outline="")
        cv.create_line(X(-0.02), Y(self.ph.hc), X(0.5), Y(self.ph.hc), dash=(5, 4), fill="#a0603a")
        cv.create_rectangle(X(0.492), Y(self.ph.hs + 0.012), X(0.508), Y(0), fill="#a87f4a", outline="")
        cv.create_rectangle(X(0.03), Y(self.ph.hs + 0.012), X(0.50), Y(self.ph.hs), fill="#a87f4a", outline="")
        if "ruler" in self.app.placed:     # an upright ruler beside the post
            x0 = X(0.44)
            cv.create_rectangle(x0, Y(0.30), x0 + 18, Y(0), fill="#e1edf2", outline="#8fa7b4")
            for mm in range(0, 301, 5):
                ln = 10 if mm % 10 == 0 else 5
                cv.create_line(x0, Y(mm / 1000.0), x0 + ln, Y(mm / 1000.0), fill="#222")
                if mm % 50 == 0:
                    cv.create_text(x0 + 26, Y(mm / 1000.0), text=str(mm // 10), font=("Helvetica", 7))
        if self.ready():
            xm, zm = X(self.x), self.ph.hs - self.ell
            cv.create_line(xm, Y(self.ph.hs), xm, Y(zm + self.ph.r), fill="#777")
            Lh = self.ph.L * z * abs(math.cos(self.ph.phi)) / 2 + self.ph.r * z * abs(math.sin(self.ph.phi))
            cv.create_rectangle(xm - Lh, Y(zm + self.ph.r), xm + Lh, Y(zm - self.ph.r), fill="#9aa0a6", outline="#555")


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
