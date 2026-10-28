#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  Nordic-Baltic Physics Olympiad 2017  (NBPhO 2017)
  Problem 5 (experimental) :  VIRTUAL MASS   (Jaan Kalda)
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* A ball of d = 72.0 mm on a massless spring hangs from the clamp of a
  stand.  The official solution measured T1 = 1.066 s in air,
  T2 = 1.136 s in water and m = 720 g from the two elongations, giving
  m_v = 98 g, which is the ideal added mass of a sphere, rho V / 2.
  m and T1 vary a little from session to session.
* In water the ball carries rho V_sub / 2 of added mass and feels the
  buoyancy rho g V_sub and a quadratic drag (C_d = 0.45); the water
  level in the container rises with what the ball displaces, so a
  partly submerged ball swings faster, as a real one does.
* Lowering the clamp dips the ball into the container on the bench;
  taking the container away leaves the ball in air at the same clamp
  height.  A 1 m ruler stands beside the container and a set square's
  level edge is moved up and down; two magnifiers show the ruler at the
  edge and the bottom of the ball.  The stopwatch runs in real time.
  Nothing is computed for you.
* Standard library only (tkinter).

    Run:   python3 nbpho2017_E1_virtualmass_sim_KO.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


GRAV, RHO, RB = 9.815, 998.0, 0.036
VB = 4.0 / 3.0 * math.pi * RB ** 3
JAR_RI, JAR_RO, JAR_H, JAR_ZB = 0.070, 0.0745, 0.30, 0.010
JAR_VW = math.pi * JAR_RI ** 2 * 0.24
XB, XROD, XRUL = 50.0, 26.0, 39.5          # cm, across the front view


def vsub(y, S):
    h = max(0.0, min(2 * RB, S - (y - RB)))
    return math.pi * h * h * (3 * RB - h) / 3.0, h


# --------------------------------------------------------------------------
#  Physics core  (SI; the drawings work in cm)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.m = r.uniform(0.714, 0.726)
        self.T1 = r.uniform(1.060, 1.072)
        self.k = 4 * math.pi ** 2 * self.m / self.T1 ** 2
        self.L0, self.Cd, self.gam = 0.12, 0.45, r.uniform(0.010, 0.014)
        self.zh, self.y, self.v = 0.80, 0.0, 0.0
        self.mode, self.steady_t = "free", 0.0
        self.jar = False
        self.y = self.eq_y()

    def relaxed(self):
        return self.zh - self.L0 - RB

    def floor(self):
        return JAR_ZB if self.jar else 0.0

    def surf(self, y):
        if not self.jar:
            return -1.0
        A = math.pi * JAR_RI ** 2
        S = JAR_ZB + JAR_VW / A
        for _ in range(6):
            S = JAR_ZB + (JAR_VW + vsub(y, S)[0]) / A
        return S

    def force(self, y):
        S = self.surf(y)
        Vs = vsub(y, S)[0] if S > 0 else 0.0
        return self.k * (self.relaxed() - y) - self.m * GRAV + RHO * GRAV * Vs

    def eq_y(self):
        a, b = self.floor() + RB, self.relaxed() + 0.02
        if self.force(a) <= 0:
            return a
        for _ in range(60):
            c = (a + b) / 2
            if self.force(c) > 0:
                a = c
            else:
                b = c
        return (a + b) / 2

    def acc(self, y, v, extra):
        S = self.surf(y)
        Vs, h = vsub(y, S) if S > 0 else (0.0, 0.0)
        Aw = 0.0 if h <= 0 else (math.pi * (2 * RB * h - h * h) if h < RB else math.pi * RB * RB)
        F = (self.k * (self.relaxed() - y) - self.m * GRAV + RHO * GRAV * Vs
             - 0.5 * RHO * self.Cd * Aw * v * abs(v) - 2 * self.gam * self.m * v - extra * self.m * v)
        return F / (self.m + 0.5 * RHO * Vs)

    def step(self, dt):
        if self.mode == "held":
            self.y, self.v = max(self.relaxed(), self.floor() + RB), 0.0
            return
        n = max(1, int(math.ceil(dt / 0.002)))
        h = dt / n
        ex = 2 * math.sqrt(self.k / self.m) if self.mode == "steady" else 0.0
        for _ in range(n):
            a1 = self.acc(self.y, self.v, ex)
            vh = self.v + 0.5 * h * a1
            self.y += h * vh
            self.v = vh + 0.5 * h * self.acc(self.y, vh, ex)
            fl = self.floor() + RB
            if self.y < fl:
                self.y = fl
                if self.v < 0:
                    self.v = -0.25 * self.v
        if self.mode == "steady":
            self.steady_t -= dt
            if self.steady_t <= 0:
                self.mode = "free"


def fmt_sw(t):
    t = round(t, 2)
    m = int(t // 60)
    return "%02d:%05.2f" % (m, t - 60 * m)


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_stand(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 30 * s, y + 34 * s, x + 20 * s, y + 42 * s, fill="#3a3f46", outline="")
    cv.create_rectangle(x - 22 * s, y - 42 * s, x - 18 * s, y + 34 * s, fill="#b9bec4", outline="")
    cv.create_rectangle(x - 22 * s, y - 36 * s, x + 18 * s, y - 32 * s, fill="#b9bec4", outline="")
    pts = []
    for i in range(17):
        pts += [x + 16 * s + (3 if i % 2 else -3) * s, y - 32 * s + i * 2.6 * s]
    cv.create_line(*pts, fill="#7d848b")
    cv.create_oval(x + 6 * s, y + 12 * s, x + 26 * s, y + 32 * s, fill="#e8c547", outline="#7a5a10")


def art_jar(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 26 * s, y - 34 * s, x + 26 * s, y + 34 * s, fill="#e4f0f4", outline="#7fa6b4", width=2)
    cv.create_rectangle(x - 24 * s, y - 14 * s, x + 24 * s, y + 32 * s, fill="#9cc4e2", outline="")


def art_ruler(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 6 * s, y - 42 * s, x + 6 * s, y + 42 * s, fill="#e6c36a", outline="#8a6a20")
    for i in range(-40, 41, 5):
        cv.create_line(x + 6 * s, y + i * s, x + (0 if i % 10 else -2) * s, y + i * s, fill="#222")


def art_watch(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 26 * s, y - 32 * s, x + 26 * s, y + 32 * s, fill="#2b2e33", outline="#000")
    cv.create_rectangle(x - 20 * s, y - 24 * s, x + 20 * s, y - 4 * s, fill="#9fae8f", outline="")
    cv.create_oval(x - 16 * s, y + 8 * s, x - 4 * s, y + 20 * s, fill="#c0392b", outline="")
    cv.create_oval(x + 4 * s, y + 8 * s, x + 16 * s, y + 20 * s, fill="#e8eef2", outline="")


ART = {"stand": art_stand, "jar": art_jar, "ruler": art_ruler, "watch": art_watch}
PARTS = [
    ("stand", ("스탠드 + 용수철에 고정된 공", "Stand + ball fixed to a spring"), []),
    ("jar",   ("물이 담긴 통", "Container with water"), []),
    ("ruler", ("자 (1 m)", "Ruler (1 m)"), []),
    ("watch", ("스톱워치", "Stopwatch"), []),
]
ZONES = {
    "stand": (200, 300, 110, 150),
    "jar":   (380, 360, 90, 110),
    "ruler": (300, 300, 40, 150),
    "watch": (580, 380, 70, 80),
}
SCENE_TITLE = ("실험대 — 스탠드와 공, 물통, 자, 스톱워치", "The bench — stand and ball, container, ruler, stopwatch")
APP_TITLE = ("NBPhO 2017 실험 (문제 5) — 부가 질량", "NBPhO 2017 Experiment (Problem 5) — Virtual mass")


# --------------------------------------------------------------------------
#  Bench tab: the front view to scale, two magnifiers, the controls
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    W, H = 900, 660

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.sight = 0.30
        self.sw_run, self.sw_t = False, 0.0
        self.msg = ""
        self.fdrag = None
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("공과 용수철", "Ball and spring"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("2 cm 당겼다 놓기", "Pull 2 cm, release"), command=lambda: self.pull(0.02)).pack(side="left", padx=2)
        ttk.Button(row, text=T("4 cm 당겼다 놓기", "Pull 4 cm, release"), command=lambda: self.pull(0.04)).pack(side="left", padx=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("손으로 멈추기", "Stop it by hand"), command=self.steady).pack(side="left", padx=2)
        self.bHold = ttk.Button(row, text="", command=self.hold)
        self.bHold.pack(side="left", padx=2)
        ttk.Label(f, text=T("받쳐 들면 용수철이 늘어나지 않은 길이가 됩니다. 진동 횟수는 공이 같은 쪽 끝에 올 때마다 셉니다.",
                            "Held up, the spring is at its unstretched length. Count oscillations each time the ball comes back to the same turning point."),
                  foreground="#555", wraplength=330).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("스탠드 클램프 높이 (내리면 공이 물에 잠김)", "Stand clamp height (lower it to dip the ball)"))
        f.pack(fill="x", pady=2)
        stepper(f, T("클램프", "Clamp"), [("−1cm", lambda: self.clamp(-0.01)), ("−1mm", lambda: self.clamp(-0.001)),
                                         ("+1mm", lambda: self.clamp(0.001)), ("+1cm", lambda: self.clamp(0.01))])
        f = ttk.LabelFrame(ctl, text=T("삼각자 가장자리 (눈금 읽기)", "Set-square edge (reading)"))
        f.pack(fill="x", pady=2)
        stepper(f, T("가장자리", "Edge"), [("−1cm", lambda: self.move_sight(-0.01)), ("−1mm", lambda: self.move_sight(-0.001)),
                                          ("+1mm", lambda: self.move_sight(0.001)), ("+1cm", lambda: self.move_sight(0.01))])
        ttk.Label(f, text=T("오른쪽 화면에서 끌어도 됩니다(확대경 안에서 끌면 미세하게).", "You can also drag it in the view (finely inside a magnifier)."),
                  foreground="#555", wraplength=330).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("스톱워치 (Space: 시작·멈춤)", "Stopwatch (Space: start/stop)"))
        f.pack(fill="x", pady=2)
        self.dS = tk.Label(f, text="", font=("Courier", 18, "bold"), bg="#9fae8f", fg="#1b1d20", width=12)
        self.dS.pack(pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.bSS = ttk.Button(row, text="", command=self.sw_start)
        self.bSS.pack(side="left", padx=2)
        ttk.Button(row, text=T("0으로", "Reset"), command=self.sw_reset).pack(side="left", padx=2)
        f = ttk.LabelFrame(ctl, text=T("기록 — 읽은 값을 직접 적으시오", "Record — type what you read"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.cent = ttk.Entry(row, width=26)
        self.cent.pack(side="left", padx=2)
        ttk.Button(row, text=T("적기", "Write"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("c", T("메모", "memo"), 220), ("t", T("스톱워치", "stopwatch"), 90)], height=8)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.lMsg = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=330)
        self.lMsg.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("정면에서 본 모습 (왼쪽: 축척 그대로, 오른쪽: 확대경)", "Seen from the front (left: to scale, right: magnifiers)"),
                  font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=self.W, height=self.H, bg="#2a2d33", highlightthickness=0)
        self.cv.pack()
        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_drag)
        self.app.bind("<space>", lambda e: self.sw_start() if not isinstance(e.widget, (tk.Entry, ttk.Entry)) else None)

    # ---- geometry of the view
    def geo(self):
        z0, z1 = -2.0, 102.0
        k = (self.H - 24) / (z1 - z0)
        x0 = XROD - 6
        sw = (XB + 10 - x0) * k
        R = 120
        return dict(k=k, x0=x0, z0=z0, sw=sw, R=R, cx=sw + 40 + (self.W - sw - 40) / 2, cyA=self.H * 0.26, cyB=self.H * 0.72, M=R / 2.8)

    def X(self, g, x):
        return 12 + (x - g["x0"]) * g["k"]

    def Y(self, g, z):
        return self.H - 12 - (z - g["z0"]) * g["k"]

    # ---- the ball
    def warn(self, s):
        self.msg = s

    def pull(self, a):
        if not self.has("stand"):
            return self.warn(T("먼저 스탠드를 놓으시오.", "Place the stand first."))
        ph = self.ph
        ph.mode = "free"
        ph.y = max(ph.floor() + RB, ph.eq_y() - a)
        ph.v = 0.0
        self.warn("")

    def steady(self):
        if self.has("stand") and self.ph.mode != "held":
            self.ph.mode, self.ph.steady_t = "steady", 2.5

    def hold(self):
        if not self.has("stand"):
            return
        ph = self.ph
        if ph.mode == "held":
            ph.mode, ph.steady_t, ph.v = "steady", 2.5, 0.0
        else:
            ph.mode = "held"

    def clamp(self, dz):
        if not self.has("stand"):
            return self.warn(T("먼저 스탠드를 놓으시오.", "Place the stand first."))
        ph = self.ph
        nz = round(ph.zh + dz, 4)
        if nz > 0.97:
            return self.warn(T("클램프가 막대 끝에 닿았습니다.", "The clamp is at the top of the rod."))
        ny = ph.y + dz
        if ny - RB < ph.floor() + 0.004 or nz - ph.L0 - 2 * RB < ph.floor() + 0.004:
            return self.warn(T("더 내리면 공이 바닥에 닿습니다.", "Any lower and the ball would sit on the bottom."))
        ph.zh = nz
        if ph.mode != "held":
            ph.y, ph.mode, ph.steady_t = ny, "steady", 2.0
        self.warn("")

    def move_sight(self, ds):
        self.sight = max(0.0, min(1.0, round((self.sight + ds) * 1000) / 1000.0))

    def on_assembly(self, placed):
        ph = self.ph
        jar = "jar" in placed
        if jar and not ph.jar and "stand" in placed and ph.y - RB < JAR_H + 0.004:
            self.app.tab_asm.placed.discard("jar")
            self.app.placed.discard("jar")
            self.app.tab_asm.redraw()
            return self.warn(T("공이 물통보다 낮게 걸려 있습니다 — 클램프를 먼저 올리시오.", "The ball hangs below the container's rim: raise the clamp first."))
        if jar != ph.jar:
            ph.jar = jar
            ph.mode, ph.steady_t = "steady", 2.5

    # ---- stopwatch and record
    def sw_start(self):
        if self.has("watch"):
            self.sw_run = not self.sw_run

    def sw_reset(self):
        self.sw_run, self.sw_t = False, 0.0

    def record(self):
        memo = self.cent.get().strip()
        if not memo:
            return self.warn(T("적을 내용을 먼저 입력하시오.", "Type something to write first."))
        self.sheet.add((memo, fmt_sw(self.sw_t) if self.has("watch") else "—"))
        self.cent.delete(0, "end")
        self.warn("")

    # ---- mouse: drag the edge
    def on_press(self, ev):
        g = self.geo()
        inl = any(math.hypot(ev.x - g["cx"], ev.y - cy) < g["R"] for cy in (g["cyA"], g["cyB"]))
        if inl:
            self.fdrag = (True, ev.y, self.sight)
        elif ev.x < g["sw"] + 24:
            self.fdrag = (False, 0, 0)
            self.on_drag(ev)
        else:
            self.fdrag = None

    def on_drag(self, ev):
        if not self.fdrag:
            return
        g = self.geo()
        fine, y0, s0 = self.fdrag
        c = s0 * 100 - (ev.y - y0) / g["M"] if fine else (self.H - 12 - ev.y) / g["k"] + g["z0"]
        self.sight = max(0.0, min(1.0, c / 100.0))

    # ---- time
    def tick(self, dt):
        if self.sw_run:
            self.sw_t += dt
        if self.has("stand"):
            self.ph.step(dt)
        self.refresh()

    def refresh(self):
        self.dS.config(text=fmt_sw(self.sw_t) if self.has("watch") else "—")
        self.bSS.config(text=T("멈춤", "Stop") if self.sw_run else T("시작", "Start"))
        self.bHold.config(text=T("받친 손 떼기", "Let go of it") if self.ph.mode == "held" else T("공 받쳐 들기", "Hold the ball up"))
        self.lMsg.config(text=self.msg)
        self.draw()

    def ball(self, cv, x, y, r):
        cv.create_oval(x - r, y - r, x + r, y + r, fill="#e8c547", outline="#5a420c", width=2)
        cv.create_oval(x - r * 0.6, y - r * 0.7, x - r * 0.1, y - r * 0.25, fill="#fff3bf", outline="")

    def draw(self):
        cv, ph, g = self.cv, self.ph, self.geo()
        cv.delete("all")
        X = lambda x: self.X(g, x)
        Y = lambda z: self.Y(g, z)
        k = g["k"]
        cv.create_rectangle(0, 0, g["sw"] + 24, self.H, fill="#e9e7e0", outline="")
        cv.create_rectangle(0, Y(0), g["sw"] + 24, self.H, fill="#cfcabb", outline="")
        if self.has("ruler"):
            cv.create_rectangle(X(XRUL - 1.25), Y(100), X(XRUL + 1.25), Y(0), fill="#e6c36a", outline="#8a6a20")
            for c in range(101):
                L = (1.1 if c % 10 == 0 else 0.75 if c % 5 == 0 else 0.45) * k
                cv.create_line(X(XRUL + 1.25), Y(c), X(XRUL + 1.25) - L, Y(c), fill="#333")
            for c in range(10, 100, 10):
                cv.create_text(X(XRUL - 0.9), Y(c) - 6, text=str(c), anchor="w", font=("Helvetica", 7, "bold"))
        S = ph.surf(ph.y) * 100
        if self.has("jar"):
            cv.create_rectangle(X(XB - JAR_RI * 100), Y(S), X(XB + JAR_RI * 100), Y(JAR_ZB * 100), fill="#a9cbe4", outline="")
            cv.create_rectangle(X(XB - JAR_RO * 100), Y(JAR_H * 100), X(XB + JAR_RO * 100), Y(0), outline="#7fa6b4", width=2)
        if self.has("stand"):
            zh = ph.zh * 100
            cv.create_rectangle(X(XROD - 4), Y(1.6), X(XROD + 18), Y(0), fill="#3a3f46", outline="")
            cv.create_rectangle(X(XROD - 0.65), Y(100), X(XROD + 0.65), Y(1.6), fill="#b9bec4", outline="#888")
            cv.create_rectangle(X(XROD - 1.6), Y(zh + 3.6), X(XROD + 1.6), Y(zh + 0.4), fill="#2b2e33", outline="")
            cv.create_rectangle(X(XROD + 1.6), Y(zh + 2.45), X(XB), Y(zh + 1.55), fill="#b9bec4", outline="#888")
            top, bot, N = Y(zh + 0.6), Y((ph.y + RB) * 100 + 0.6), 26
            pts = []
            for i in range(2 * N + 1):
                pts += [X(XB) + (0 if i in (0, 2 * N) else (1 if i % 2 else -1) * 0.85 * k), top + (bot - top) * i / (2 * N)]
            cv.create_line(*pts, fill="#7d848b")
            self.ball(cv, X(XB), Y(ph.y * 100), RB * 100 * k)
        else:
            cv.create_text(g["sw"] / 2, self.H / 2, text=T("스탠드를 놓으시오", "Place the stand"), fill="#69717a")
        s = self.sight * 100
        cv.create_line(X(XRUL + 1.25), Y(s), X(XB + 5), Y(s), fill="#d9a400", width=2)
        cv.create_polygon(X(XRUL + 1.25), Y(s), X(XRUL + 1.25) + 28, Y(s), X(XRUL + 1.25), Y(s) - 28, fill="#f6e3a8", outline="#b58a00")
        # the magnifiers
        R, M, cx = g["R"], g["M"], g["cx"]
        for cy, wx, lab in ((g["cyA"], XRUL + 0.6, T("자 (가장자리 높이)", "ruler (at the edge)")), (g["cyB"], XB, T("공의 아래 끝", "bottom of the ball"))):
            LX = lambda x: cx + (x - wx) * M
            LY = lambda z: cy - (z - s) * M
            cv.create_oval(cx - R, cy - R, cx + R, cy + R, fill="#f4f2ea", outline="")
            if cy == g["cyA"]:
                if self.has("ruler"):
                    x0, x1 = max(cx - R, LX(XRUL - 1.25)), min(cx + R, LX(XRUL + 1.25))
                    if x1 > x0:
                        n = 24
                        xs = [x0 + (x1 - x0) * i / n for i in range(n + 1)]
                        h = [math.sqrt(max(0.0, R * R - (xx - cx) ** 2)) for xx in xs]
                        poly = [c for xx, hh in zip(xs, h) for c in (xx, cy - hh)] + [c for xx, hh in zip(xs[::-1], h[::-1]) for c in (xx, cy + hh)]
                        cv.create_polygon(*poly, fill="#e6c36a", outline="")
                    for mm in range(int((s - R / M - 1) * 10), int((s + R / M + 1) * 10) + 1):
                        if mm < 0 or mm > 1000:
                            continue
                        yy = LY(mm / 10.0)
                        if abs(yy - cy) > R * 0.97:
                            continue
                        L = (1.1 if mm % 10 == 0 else 0.75 if mm % 5 == 0 else 0.45) * M
                        cv.create_line(LX(XRUL + 1.25), yy, LX(XRUL + 1.25) - L, yy, fill="#222", width=2 if mm % 10 == 0 else 1)
                        if mm % 10 == 0:
                            cv.create_text(LX(XRUL - 1.0), yy, text=str(mm // 10), anchor="w", font=("Helvetica", 13, "bold"))
                cv.create_line(LX(XRUL + 1.25), cy, cx + R * 0.95, cy, fill="#d9a400", width=2)
            else:
                if self.has("jar") and S > 0:
                    yt = max(cy - R, LY(S))
                    if yt < cy + R:
                        cv.create_rectangle(cx - R * 0.95, yt, cx + R * 0.95, cy + R * 0.95, fill="#c9dcea", outline="")
                if self.has("stand"):
                    yc, r = LY(ph.y * 100), RB * 100 * M
                    if abs(yc - cy) < R + r:
                        self.ball(cv, cx, yc, r)
                cv.create_line(cx - R * 0.95, cy, cx + R * 0.95, cy, fill="#d9a400", width=2)
            # the frame hides what falls outside the disc
            cv.create_rectangle(g["sw"] + 24, cy - R - 40, self.W, cy - R, fill="#2a2d33", outline="")
            cv.create_rectangle(g["sw"] + 24, cy + R, self.W, cy + R + 10, fill="#2a2d33", outline="")
            cv.create_oval(cx - R, cy - R, cx + R, cy + R, outline="#2b2e33", width=6)
            cv.create_text(cx, cy + R + 16, text=lab, fill="#e8eef2", font=("Helvetica", 10, "bold"))
        cv.create_text(self.W - 10, 18, text=fmt_sw(self.sw_t), anchor="e", fill="#ffcf3a", font=("Courier", 14, "bold"))


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
        nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.tab_bench, text=T(" 실험대 ", " Bench "))
        self.last = None
        self.after(20, self.tick)

    def on_assembly_change(self, placed):
        self.placed = set(placed)
        self.tab_bench.on_assembly(self.placed)
        self.tab_bench.refresh()

    def tick(self):
        import time
        now = time.time()
        dt = 0.02 if self.last is None else min(0.05, now - self.last)
        self.last = now
        self.tab_bench.tick(dt)
        self.after(20, self.tick)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
