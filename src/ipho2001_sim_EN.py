#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  32nd International Physics Olympiad  (IPhO 2001, Antalya, Turkey)
  Experimental Problem :  ROTATING LIQUID
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* A cup of glycerin (radius R, depth h0) turns with the turntable; the
  liquid follows the table's angular speed with a lag of some 15 s and
  its surface is the paraboloid y = y0 + w^2 r^2 / 2g with
  y0 = h0 - w^2 R^2 / 4g.
* The laser's rays are traced in 3D: through the transparent screen,
  reflected at the surface (and, dimly, refracted down, reflected at
  the bottom and refracted out), back up to the screen at height H.
* The shaped head sends an "F" of rays a degree or so wide.
* Part 3: a grating (500 or 1000 lines/mm) in air in front of a scale
  card, or upright in the glycerin at the cup's centre with the orders
  on the cup's side scale (arc length R alpha).
* g is 9.80 m/s^2; R, h0, n, the wavelength and the motor are hidden
  and randomised.  Standard library only (tkinter).

    Run:   python3 ipho2001_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line

G = 980.0
CUPH = 8.0
FSHAPE = [(0, -1 + i * 0.2) for i in range(11)] + [(i * 0.13, 1) for i in range(1, 7)] + [(i * 0.13, 0.15) for i in range(1, 5)]


def nrm(a):
    l = math.sqrt(sum(v * v for v in a)) or 1.0
    return [v / l for v in a]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


# --------------------------------------------------------------------------
#  Physics core
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.R, self.h0 = r.uniform(7.0, 7.4), r.uniform(1.9, 2.5)
        self.n, self.lam = r.uniform(1.462, 1.476), r.uniform(640, 670) * 1e-7
        self.kMot, self.v0, self.tau = r.uniform(1.25, 1.45), r.uniform(0.6, 1.0), r.uniform(14, 20)
        self.bOff = r.uniform(0.2, 0.8)
        self.wMax = math.sqrt(4 * G * self.h0) / self.R

    def surf(self, w):
        return w * w / (2 * G), self.h0 - w * w * self.R * self.R / (4 * G)

    def zs(self, w, r):
        a, y0 = self.surf(w)
        return max(0.0, y0 + a * r * r)

    def hit(self, w, p, d):
        a, y0 = self.surf(w)
        X, Y, Z = p[0], p[1], p[2] - y0
        A = a * (d[0] ** 2 + d[1] ** 2)
        B = 2 * a * (X * d[0] + Y * d[1]) - d[2]
        C = a * (X * X + Y * Y) - Z
        if abs(A) < 1e-12:
            t = -C / B
        else:
            D = B * B - 4 * A * C
            if D < 0:
                return None
            r1, r2 = (-B - math.sqrt(D)) / (2 * A), (-B + math.sqrt(D)) / (2 * A)
            t = min(r1, r2) if min(r1, r2) > 1e-6 else max(r1, r2)
        if not t > 1e-6:
            return None
        q = [p[i] + d[i] * t for i in range(3)]
        if math.hypot(q[0], q[1]) > self.R or q[2] < 0:
            return None
        return q, nrm([-2 * a * q[0], -2 * a * q[1], 1])

    @staticmethod
    def refract(d, n, r):
        c = -dot(d, n)
        if c < 0:
            n, c = [-v for v in n], -c
        k = 1 - r * r * (1 - c * c)
        if k < 0:
            return None
        return [d[i] * r + n[i] * (r * c - math.sqrt(k)) for i in range(3)]

    def trace(self, w, p, d, H, cup=True):
        """hits on the screen (height H above the turntable; the axis at x = y = 0): (x, y, I, kind)"""
        out = []
        toz = lambda a, v, z: [a[i] + v[i] * (z - a[2]) / v[2] for i in range(3)]
        if p[2] > H:
            q = toz(p, d, H)
            out.append((q[0], q[1], 0.35, "in"))
        if not cup:
            return out
        h = self.hit(w, p, d)
        if not h:
            return out
        q, n = h
        r = [d[i] - 2 * dot(d, n) * n[i] for i in range(3)]
        if r[2] > 0:
            e = toz(q, r, H)
            out.append((e[0], e[1], 1.0, "top"))
        t = self.refract(d, n, 1 / self.n)
        if t and t[2] < 0:
            b = toz(q, t, 0.0)
            if math.hypot(b[0], b[1]) < self.R:
                t2 = [t[0], t[1], -t[2]]
                up = self.hit(w, [b[i] + t2[i] * 1e-4 for i in range(3)], t2)
                if up:
                    o = self.refract(t2, [-v for v in up[1]], self.n)
                    if o and o[2] > 0:
                        e = toz(up[0], o, H)
                        out.append((e[0], e[1], 0.16, "bot"))
        return out

    def orders(self, lines, where, L=20.0):
        res, dg = [], 0.1 / lines
        for m in range(-3, 4):
            s = m * self.lam / dg / (self.n if where == "cup" else 1.0)
            if abs(s) >= 1:
                continue
            a = math.asin(s)
            x = self.R * a if where == "cup" else L * math.tan(a)
            if where == "cup" and abs(a) < 1.3 or where == "air" and abs(x) < 10:
                res.append((m, x))
        return res


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def box_art(col, w, h):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_rectangle(x - w * s, y - h * s, x + w * s, y + h * s, fill=col, outline="#555")
    return art


def art_table(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 40 * s, y, x + 40 * s, y + 24 * s, fill="#2f3338", outline="")
    cv.create_oval(x - 38 * s, y - 10 * s, x + 38 * s, y + 10 * s, fill="#d9dadb", outline="#888")


def art_cup(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 26 * s, y - 20 * s, x + 26 * s, y + 20 * s, fill="#e1ecf4", outline="#889")
    cv.create_rectangle(x - 25 * s, y + 6 * s, x + 25 * s, y + 19 * s, fill="#e8d68c", outline="")


ART = {"table": art_table, "cup": art_cup, "screen": box_art("#cfe3ee", 36, 6), "laser": box_art("#1f2226", 6, 26),
       "grating": box_art("#aac8e6", 12, 12), "card": box_art("#fbfaf2", 8, 30), "watch": box_art("#2a2d33", 14, 16)}
PARTS = [
    ("table",   ("턴테이블 + 모터 조절기", "Turntable + motor controller"), []),
    ("cup",     ("글리세린 컵 (mm 눈금)", "Glycerin cup (mm scales)"), ["table"]),
    ("screen",  ("투명 스크린 스탠드", "Transparent screen stand"), ["table"]),
    ("laser",   ("레이저 포인터 스탠드", "Laser pointer stand"), []),
    ("grating", ("투과 격자 (500·1000 /mm)", "Transmission grating (500·1000 /mm)"), []),
    ("card",    ("눈금 카드 (스탠드)", "Scale card (on a stand)"), []),
    ("watch",   ("스톱워치", "Stopwatch"), []),
]
ZONES = {"table": (380, 360, 100, 60), "cup": (380, 300, 60, 46), "screen": (380, 170, 90, 18), "laser": (380, 80, 16, 60),
         "grating": (620, 300, 30, 30), "card": (120, 300, 22, 70), "watch": (620, 420, 34, 38)}
SCENE_TITLE = ("턴테이블과 글리세린 컵 · 스크린 · 레이저 · 격자와 카드", "Turntable and glycerin cup · screen · laser · grating and card")
APP_TITLE = ("IPhO 2001 실험 — 회전하는 액체", "IPhO 2001 Experiment — Rotating liquid")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.knob, self.wT, self.wL, self.ang, self.clock = 0.0, 0.0, 0.0, 0.0, 0.0
        self.H, self.lx, self.tilt, self.gL = 30.0, 3.0, 0.0, 20.0
        self.laser, self.head, self.aim, self.lines, self.gpos = tk.BooleanVar(value=False), tk.StringVar(value="dot"), tk.StringVar(value="down"), tk.IntVar(value=500), tk.StringVar(value="off")
        self.speed = tk.IntVar(value=1)
        self.watch_t, self.watch_run, self.zoom = 0.0, False, 1
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("모터 조절기 · 스톱워치", "Motor controller · stopwatch"))
        f.pack(fill="x", pady=2)
        stepper(f, T("손잡이", "Knob"), [("−1", lambda: self.setk(-1)), ("−0.1", lambda: self.setk(-0.1)), ("−0.01", lambda: self.setk(-0.01)),
                                       ("+0.01", lambda: self.setk(0.01)), ("+0.1", lambda: self.setk(0.1)), ("+1", lambda: self.setk(1))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.kl = ttk.Label(row, text="", font=("Courier", 12, "bold"))
        self.kl.pack(side="left")
        self.wl = tk.Label(row, text="", font=("Courier", 14, "bold"), bg="#9fae8f", fg="#1b1d20", width=9)
        self.wl.pack(side="left", padx=6)
        self.wb = ttk.Button(row, text="", command=self.watch)
        self.wb.pack(side="left")
        ttk.Button(row, text=T("영점", "Reset"), command=lambda: setattr(self, "watch_t", 0.0)).pack(side="left")
        row = ttk.Frame(f)
        row.pack(fill="x")
        for s in (1, 5, 20):
            ttk.Radiobutton(row, text="×%d" % s, value=s, variable=self.speed).pack(side="left")
        self.clk = ttk.Label(row, text="")
        self.clk.pack(side="left", padx=8)
        f = ttk.LabelFrame(ctl, text=T("레이저 · 스크린", "Laser · screen"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Checkbutton(row, text=T("레이저 켜기", "Laser on"), variable=self.laser).pack(side="left")
        ttk.Radiobutton(row, text=T("점", "dot"), value="dot", variable=self.head).pack(side="left", padx=4)
        ttk.Radiobutton(row, text=T("모양 (F)", "shape (F)"), value="shape", variable=self.head).pack(side="left")
        row = ttk.Frame(f)
        row.pack(fill="x")
        for v, lab in (("down", T("아래로", "down")), ("cup", T("컵 쪽", "at cup")), ("card", T("카드 쪽", "at card"))):
            ttk.Radiobutton(row, text=lab, value=v, variable=self.aim).pack(side="left")
        stepper(f, T("레이저 x (cm)", "Laser x (cm)"), [("−1", lambda: self.mv("lx", -1)), ("−0.1", lambda: self.mv("lx", -0.1)), ("+0.1", lambda: self.mv("lx", 0.1)), ("+1", lambda: self.mv("lx", 1))])
        stepper(f, T("기울기", "Tilt"), [("−0.5°", lambda: self.mv("tilt", -0.5)), ("+0.5°", lambda: self.mv("tilt", 0.5))])
        stepper(f, T("스크린 H (cm)", "Screen H (cm)"), [("−5", lambda: self.mv("H", -5)), ("−1", lambda: self.mv("H", -1)), ("−0.1", lambda: self.mv("H", -0.1)),
                                                       ("+0.1", lambda: self.mv("H", 0.1)), ("+1", lambda: self.mv("H", 1)), ("+5", lambda: self.mv("H", 5))])
        f = ttk.LabelFrame(ctl, text=T("격자 (3부)", "Grating (Part 3)"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for v in (500, 1000):
            ttk.Radiobutton(row, text="%d /mm" % v, value=v, variable=self.lines).pack(side="left")
        for v, lab in (("off", T("빼기", "out")), ("cup", T("컵 속", "in cup")), ("air", T("공기 중", "in air"))):
            ttk.Radiobutton(row, text=lab, value=v, variable=self.gpos).pack(side="left")
        stepper(f, T("카드까지 L (cm)", "L to card (cm)"), [("−1", lambda: self.mv("gL", -1)), ("−0.1", lambda: self.mv("gL", -0.1)), ("+0.1", lambda: self.mv("gL", 0.1)), ("+1", lambda: self.mv("gL", 1))])
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        ttk.Button(f, text=T("지금 스톱워치와 H 적기", "Write down the stopwatch and H"), command=self.record).pack(anchor="w")
        self.sheet = DataSheet(f, [("t", T("스톱워치", "watch"), 100), ("h", "H", 80)], height=4)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=420)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        row = ttk.Frame(right)
        row.pack(fill="x")
        ttk.Label(row, text=T("스크린 (위에서) · 턴테이블 · 단면과 눈금 · 격자 무늬", "Screen from above · turntable · section and scales · grating orders"), font=("Helvetica", 10, "bold")).pack(side="left")
        for z in (1, 3, 8):
            ttk.Button(row, text="×%d" % z, command=lambda z=z: setattr(self, "zoom", z)).pack(side="right")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    def setk(self, d):
        if self.has("table"):
            self.knob = max(0.0, min(10.0, round(self.knob + d, 2)))

    def mv(self, k, d):
        lim = {"lx": (-9, 9), "tilt": (-6, 6), "H": (9, 45), "gL": (5, 30)}[k]
        setattr(self, k, max(lim[0], min(lim[1], round(getattr(self, k) + d, 2))))

    def watch(self):
        if self.has("watch"):
            self.watch_run = not self.watch_run

    def record(self):
        self.sheet.add(("%.2f s" % self.watch_t, "%.1f cm" % self.H))

    def rays(self):
        t = math.radians(self.tilt)
        p, d0 = [self.lx, 0.0, 56.0], nrm([math.sin(t), 0, -math.cos(t)])
        if self.head.get() == "dot":
            return [(p, d0)]
        sc = 0.022
        return [(p, nrm([d0[0] + u * sc * math.cos(t), v * sc, d0[2] + u * sc * math.sin(t)])) for u, v in FSHAPE]

    def hits(self):
        if not (self.laser.get() and self.has("laser") and self.aim.get() == "down" and self.has("screen")):
            return []
        out = []
        for p, d in self.rays():
            out += self.ph.trace(self.wL, p, d, self.H, self.has("cup"))
        return out

    def tick(self, dt):
        T_ = dt * self.speed.get()
        self.clock += T_
        if self.watch_run:
            self.watch_t += T_
        wt = max(0.0, self.ph.kMot * (self.knob - self.ph.v0)) if self.has("table") else 0.0
        steps = max(1, int(T_ / 0.02))
        h = T_ / steps
        for _ in range(steps):
            self.wT += (wt - self.wT) * (1 - math.exp(-h / 1.2))
            self.ang = (self.ang + self.wT * h) % (2 * math.pi)
            self.wL += (self.wT - self.wL) * (1 - math.exp(-h / self.ph.tau))
        if self.gpos.get() == "cup" and self.wT > 0.05:
            self.gpos.set("off")
        msg = []
        if self.wL > 0.97 * self.ph.wMax:
            msg.append(T("가운데가 컵 바닥에 닿을 만큼 빠릅니다.", "So fast the centre nearly touches the bottom."))
        if abs(self.wL - self.wT) > 0.05:
            msg.append(T("액체가 아직 턴테이블을 따라잡는 중입니다.", "The liquid is still catching up with the turntable."))
        self.warn.config(text="\n".join(msg))
        self.refresh()

    def refresh(self):
        self.kl.config(text="%.2f" % self.knob)
        self.wl.config(text="%.2f s" % self.watch_t)
        self.wb.config(text=T("정지", "Stop") if self.watch_run else T("시작", "Start"))
        self.clk.config(text="%d:%02d" % (self.clock // 60, self.clock % 60))
        self.draw()

    def draw(self):
        cv, ph = self.cv, self.ph
        cv.delete("all")
        # the screen from above: 30 x 22 cm of mm paper
        x0, y0, W, Hh = 10, 10, 470, 345
        s = W / 30.0 * self.zoom
        cv.create_rectangle(x0, y0, x0 + W, y0 + Hh, fill="#f8f7ee", outline="#999")
        P = lambda x, y: (x0 + W / 2 + x * s, y0 + Hh / 2 + y * s)
        step = 1.0 if s < 25 else (0.5 if s < 60 else 0.1)
        n = -15.0
        while n <= 15.0 + 1e-6:
            X = P(n, 0)[0]
            if x0 <= X <= x0 + W:
                big = abs(n - round(n / 5) * 5) < 1e-6
                cv.create_line(X, y0, X, y0 + Hh, fill="#6f8fbf" if big else "#c9d4e6")
            n += step
        n = -11.0
        while n <= 11.0 + 1e-6:
            Y = P(0, n)[1]
            if y0 <= Y <= y0 + Hh:
                big = abs(n - round(n / 5) * 5) < 1e-6
                cv.create_line(x0, Y, x0 + W, Y, fill="#6f8fbf" if big else "#c9d4e6")
            n += step
        for x, y, I, kind in self.hits():
            px, py = P(x, y)
            if x0 <= px <= x0 + W and y0 <= py <= y0 + Hh:
                r = max(1.5, (0.04 if self.head.get() != "dot" else 0.12) * s)
                cv.create_oval(px - r, py - r, px + r, py + r, fill="#ff9a8a" if kind == "in" else ("#e01010" if kind == "top" else "#f0b0a8"), outline="")
        cv.create_text(x0 + 4, y0 + Hh + 10, anchor="w", text=T("스크린의 mm 종이 (위에서, 가운데 = 회전축)", "mm sheet on the screen (from above, centre = axis)"), font=("Helvetica", 9))
        # the turntable from above
        cx, cy, R = 620, 150, 120
        cv.create_oval(cx - R, cy - R, cx + R, cy + R, fill="#d9dadb", outline="#888")
        if self.has("cup"):
            rc = R * ph.R / 10.5
            cv.create_oval(cx - rc, cy - rc, cx + rc, cy + rc, fill="#e8d68c", outline="#998")
        a = self.ang
        cv.create_line(cx + R * 0.72 * math.cos(a), cy + R * 0.72 * math.sin(a), cx + R * 0.98 * math.cos(a), cy + R * 0.98 * math.sin(a), fill="#c0392b", width=6)
        cv.create_line(cx + R + 4, cy, cx + R + 16, cy, fill="#333")
        # the scales: the level at the wall, the screen's height H, the cup's bottom
        def scale(y, lab, v, ok, rng=4.0):
            cv.create_text(500, y - 10, anchor="w", text=lab, font=("Helvetica", 9, "bold"))
            cv.create_rectangle(500, y, 750, y + 40, fill="#fbfaf2", outline="#999")
            if not ok:
                return
            ppm = 250 / (rng * 10)
            for mm in range(int(v * 10 - rng * 5) - 1, int(v * 10 + rng * 5) + 2):
                X = 625 + (mm - v * 10) * ppm
                if mm < 0 or X < 500 or X > 750:
                    continue
                L = 18 if mm % 10 == 0 else (12 if mm % 5 == 0 else 7)
                cv.create_line(X, y, X, y + L, fill="#111", width=2 if mm % 10 == 0 else 1)
                if mm % 10 == 0:
                    cv.create_text(X, y + 28, text=str(mm // 10), font=("Helvetica", 8, "bold"))
            cv.create_line(625, y, 625, y + 40, fill="#c08a10", width=2)
        scale(310, T("컵 옆면: 벽에서의 액면 (cm)", "cup side: level at the wall (cm)"), ph.zs(self.wL, ph.R), self.has("cup"))
        scale(380, T("기둥: 스크린 높이 H (cm)", "post: screen height H (cm)"), self.H, self.has("screen"))
        # the cup's bottom scale between the inner walls
        y = 450
        cv.create_text(10, y - 10, anchor="w", text=T("컵 바닥 눈금 (cm) — 안쪽 벽 사이", "cup bottom scale (cm) — between the inner walls"), font=("Helvetica", 9, "bold"))
        cv.create_rectangle(10, y, 750, y + 40, fill="#fbfaf2", outline="#999")
        if self.has("cup"):
            ppc = 740 / (2 * ph.R + 3)
            for mm in range(0, int((2 * ph.R + 2.5) * 10)):
                X = 10 + (1.5 - ph.bOff) * ppc + mm / 10.0 * ppc
                if X > 750:
                    break
                L = 16 if mm % 10 == 0 else (11 if mm % 5 == 0 else 6)
                cv.create_line(X, y, X, y + L, fill="#111")
                if mm % 10 == 0:
                    cv.create_text(X, y + 26, text=str(mm // 10), font=("Helvetica", 8))
            for sg in (-1, 1):
                X = 10 + (1.5 + ph.R + sg * ph.R) * ppc
                cv.create_line(X, y, X, y + 40, fill="#7a8a96", width=3)
        # Part 3: the grating's orders on the cup wall (arc length) or on the card
        y = 540
        where = self.gpos.get()
        cv.create_text(10, y - 10, anchor="w", text=T("3부: 컵 옆면(호의 길이) 또는 카드의 mm 눈금", "Part 3: the cup's side (arc length) or the card, mm"), font=("Helvetica", 9, "bold"))
        cv.create_rectangle(10, y, 750, y + 60, fill="#fbfaf2", outline="#999")
        for mm in range(-100, 101):
            X = 380 + mm * 3.6
            L = 16 if mm % 10 == 0 else (11 if mm % 5 == 0 else 6)
            cv.create_line(X, y + 60, X, y + 60 - L, fill="#111")
            if mm % 10 == 0:
                cv.create_text(X, y + 32, text=str(abs(mm) // 10), font=("Helvetica", 8))
        ok = self.laser.get() and self.has("laser") and self.has("grating") and ((where == "cup" and self.aim.get() == "cup" and self.has("cup") and self.wL < 0.05) or (where == "air" and self.aim.get() == "card" and self.has("card")))
        if ok:
            for m, x in ph.orders(self.lines.get(), where, self.gL):
                X = 380 + x * 36
                if 10 < X < 750:
                    cv.create_oval(X - 5, y + 10, X + 5, y + 20, fill="#e01010", outline="")
        if where == "air":
            cv.create_text(750, y + 74, anchor="e", text=T("격자–카드 거리 L = %.1f cm (자로 읽음)", "grating–card L = %.1f cm (on the ruler)") % self.gL, font=("Helvetica", 9))


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
