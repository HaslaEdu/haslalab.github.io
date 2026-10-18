#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  6th Asian Physics Olympiad  (APhO 2005, Pekanbaru, Indonesia)
  Experimental Problem 2 :  MAGNETIC BRAKING ON AN INCLINED PLANE
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* A ring NdFeB magnet (21.5 g, 25.4 mm across, 6.3 mm thick) rolls down
  the groove of an acrylic plane; sin(theta) = h / l with l = 425 mm.
* Each aluminium bar brakes it with half of k0 d^p v^n (d from the
  magnet's centre to the bar's face); the rolling magnet's inertia,
  a small rolling friction and the drag of the earth's field twisting it
  (least when the plane runs east-west) are included.
* The motion is integrated in real time; you time it yourself with the
  stopwatch between marks of the groove's scale.
* n, p, k0, north and the frictions are hidden and randomised.
* Standard library only (tkinter).

    Run:   python3 apho2005_E2_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line

G = 9.8
M, RO, RI, TM = 0.0215, 0.0127, 0.0040, 0.0063
MEFF = M * (1 + (RO * RO + RI * RI) / (2 * RO * RO))
LSUP, PLATE, TRK0, TRK1, BAR0, BAR1 = 425.0, 500.0, 20.0, 470.0, 40.0, 440.0


# --------------------------------------------------------------------------
#  Physics core  (SI; positions along the plate in mm)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.n = r.uniform(0.93, 1.06)
        self.p = r.uniform(-2.40, -1.95)
        self.vref = r.uniform(0.022, 0.028)
        self.north = r.uniform(0, 360)
        self.tw = r.uniform(0.004, 0.007)
        self.roll = r.uniform(0.0002, 0.0005)
        self.scat = r.uniform(0.004, 0.010)
        self.K5 = M * G * 0.118 / self.vref ** self.n


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_plane(cv, x, y, sc=1.0):
    s = sc
    cv.create_polygon(x - 80 * s, y + 10 * s, x + 80 * s, y - 20 * s, x + 80 * s, y - 14 * s, x - 80 * s, y + 16 * s, fill="#c8dfe8", outline="#7f9fb0")


def art_stand(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 12 * s, y - 25 * s, x + 12 * s, y + 25 * s, fill="#f2f2ee", outline="#999")


def art_bars(cv, x, y, sc=1.0):
    s = sc
    for dy in (-8, 8):
        cv.create_rectangle(x - 70 * s, y + (dy - 4) * s, x + 70 * s, y + (dy + 4) * s, fill="#b9bfc6", outline="#777")


def art_magnet(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 16 * s, y - 16 * s, x + 16 * s, y + 16 * s, fill="#6a7078", outline="#333")
    cv.create_oval(x - 5 * s, y - 5 * s, x + 5 * s, y + 5 * s, fill="#e9e7e0", outline="")


def art_watch(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 18 * s, y - 24 * s, x + 18 * s, y + 24 * s, fill="#2b2e33", outline="#555")
    cv.create_rectangle(x - 13 * s, y - 18 * s, x + 13 * s, y - 4 * s, fill="#9fae8f", outline="")


def art_ruler(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 60 * s, y - 6 * s, x + 60 * s, y + 6 * s, fill="#d6e4ea", outline="#8fa7b4")
    for i in range(13):
        cv.create_line(x - 60 * s + i * 10 * s, y - 6 * s, x - 60 * s + i * 10 * s, y - 1 * s, fill="#223")


ART = {"plane": art_plane, "stand": art_stand, "bars": art_bars, "magnet": art_magnet, "watch": art_watch, "ruler": art_ruler}
PARTS = [
    ("plane",  ("[3] 아크릴 경사판 (홈·눈금)", "[3] Acrylic inclined plane (groove, scale)"), []),
    ("stand",  ("[4] 플라스틱 받침", "[4] Plastic stand"), ["plane"]),
    ("bars",   ("[2] 알루미늄 막대 2개", "[2] Aluminium bars x2"), ["plane"]),
    ("magnet", ("[1] 고리 자석 (NdFeB)", "[1] Ring magnet (NdFeB)"), ["plane"]),
    ("watch",  ("[5] 디지털 스톱워치", "[5] Digital stopwatch"), []),
    ("ruler",  ("[6] 자", "[6] Ruler"), []),
]
ZONES = {"plane": (380, 240, 170, 40), "stand": (520, 270, 30, 50), "bars": (380, 200, 150, 30), "magnet": (250, 200, 35, 35), "watch": (660, 380, 40, 50), "ruler": (300, 400, 130, 20)}
SCENE_TITLE = ("경사판 위의 막대와 자석, 옆에는 스톱워치와 자", "Bars and magnet on the plane; the stopwatch and ruler beside")
APP_TITLE = ("APhO 2005 실험 2 — 경사면 위의 자기 제동", "APhO 2005 Experiment 2 — Magnetic braking on an inclined plane")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.h, self.psi = 50.0, 0.0
        self.dL, self.dR = 5.0, 5.0
        self.s, self.v, self.ang, self.rolling, self.krun = TRK1 - RO * 1000, 0.0, 0.0, False, 1.0
        self.wrun, self.wt = False, 0.0
        self.view = tk.StringVar(value="side")
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def sin_th(self):
        return min(0.6, self.h / LSUP) if self.has("stand") else 0.0

    def brake(self, v):
        if not self.has("bars") or v <= 0:
            return 0.0
        f = ((self.dL / 5) ** self.ph.p + (self.dR / 5) ** self.ph.p) / 2
        return self.ph.K5 * f * v ** self.ph.n * self.krun

    def twist(self):
        return self.ph.tw * abs(math.cos(math.radians(self.psi - self.ph.north)))

    def step(self, dt):
        if self.wrun:
            self.wt += dt
        if not self.rolling or not self.has("magnet"):
            return
        st = self.sin_th()
        n = max(1, int(math.ceil(dt / 0.0005)))
        h = dt / n
        for _ in range(n):
            v = self.v / 1000
            drive = M * G * st
            fr = self.ph.roll + self.twist()
            drag = self.brake(v) + (fr if (v > 1e-5 or drive > fr) else drive)
            nv = max(0.0, v + (drive - drag) / MEFF * h)
            self.v = nv * 1000
            self.s -= self.v * h
            self.ang += nv * h / RO
            if self.s <= TRK0 + RO * 1000:
                self.s, self.v, self.rolling = TRK0 + RO * 1000, 0.0, False
                break

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("스톱워치 (Space: 시작/정지, R: 영점)", "Stopwatch (Space: start/stop, R: zero)"))
        f.pack(fill="x", pady=2)
        self.wl = tk.Label(f, text="0.00 s", font=("Courier", 22, "bold"), bg="#9fae8f", fg="#1b1d20", width=10)
        self.wl.pack(anchor="w", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("시작 / 정지", "Start / stop"), command=self.ss).pack(side="left", padx=2)
        ttk.Button(row, text=T("영점", "Zero"), command=self.zero).pack(side="left", padx=2)
        f = ttk.LabelFrame(ctl, text=T("자석", "Magnet"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("놓기", "Let go"), command=self.release).pack(side="left", padx=2)
        ttk.Button(row, text=T("위로 가져오기", "Back to the top"), command=self.to_top).pack(side="left", padx=2)
        f = ttk.LabelFrame(ctl, text=T("경사 · 판의 방향 · 막대", "Slope · direction · bars"))
        f.pack(fill="x", pady=2)
        stepper(f, T("받침 높이 h", "Stand height h"), [("−10", lambda: self.seth(-10)), ("−1", lambda: self.seth(-1)), ("+1", lambda: self.seth(1)), ("+10", lambda: self.seth(10))])
        stepper(f, T("판 돌리기", "Turn the plane"), [("⟲15°", lambda: self.turn(-15)), ("⟲5°", lambda: self.turn(-5)), ("⟳5°", lambda: self.turn(5)), ("⟳15°", lambda: self.turn(15))])
        stepper(f, T("왼쪽 막대", "Left bar"), [("◀", lambda: self.bar("L", -1)), ("▶", lambda: self.bar("L", 1))])
        stepper(f, T("오른쪽 막대", "Right bar"), [("◀", lambda: self.bar("R", -1)), ("▶", lambda: self.bar("R", 1))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Radiobutton(row, text=T("옆에서 (자를 받침 옆에)", "Side (ruler at the stand)"), value="side", variable=self.view).pack(side="left")
        ttk.Radiobutton(row, text=T("홈 단면 (자를 가로로)", "Groove end-on (ruler across)"), value="end", variable=self.view).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.note = ttk.Entry(row, width=24)
        self.note.pack(side="left", padx=2)
        ttk.Button(row, text=T("시간 적기", "Record time"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("t", T("시간 (s)", "time (s)"), 80), ("n", T("메모 (h, d, 구간)", "note (h, d, marks)"), 200)], height=5)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("경사판 (자석을 클릭: 놓기 / 위로)", "The plane (click the magnet: let go / back to the top)"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#f4f2ec", highlightthickness=0)
        self.cv.pack()
        self.cv.bind("<Button-1>", self.click)
        self.bind_all("<space>", lambda e: self.ss() if not isinstance(e.widget, (tk.Entry, ttk.Entry)) else None)
        self.bind_all("<KeyPress-r>", lambda e: self.zero() if not isinstance(e.widget, (tk.Entry, ttk.Entry)) else None)

    def ss(self):
        if self.has("watch"):
            self.wrun = not self.wrun

    def zero(self):
        if not self.wrun:
            self.wt = 0.0

    def release(self):
        if self.has("magnet") and not self.rolling:
            self.krun = 1 + self.ph.scat * (random.random() * 2 - 1) * 1.7
            self.rolling, self.v = True, 0.0

    def to_top(self):
        self.rolling, self.v, self.s = False, 0.0, TRK1 - RO * 1000

    def seth(self, d):
        self.h = max(10.0, min(200.0, self.h + d))

    def turn(self, d):
        if not self.rolling:
            self.psi = (self.psi + d) % 360

    def bar(self, side, dr):
        if self.rolling or not self.has("bars"):
            return
        mn = TM * 500 + 0.4
        if side == "L":
            self.dL = max(mn, min(14.0, round(self.dL - dr * 0.5, 1)))
        else:
            self.dR = max(mn, min(14.0, round(self.dR + dr * 0.5, 1)))

    def record(self):
        self.sheet.add(("%.2f" % self.wt, self.note.get()))

    def click(self, e):
        if self.view.get() != "side" or not self.has("magnet"):
            return
        x, y = self.mag_xy()
        if math.hypot(e.x - x, e.y - y) < 25:
            if self.rolling or self.s < TRK1 - RO * 1000 - 1:
                self.to_top()
            else:
                self.release()

    def pp(self, s, up):
        st = self.sin_th()
        ct = math.sqrt(1 - st * st)
        z = 700.0 / (PLATE + 20)
        return 30 + (s * ct - up * st) * z, 580 - (s * st + up * ct) * z

    def mag_xy(self):
        return self.pp(self.s, RO * 1000)

    def tick(self, dt):
        self.step(dt)                    # the stopwatch runs on the same clock as the magnet
        self.refresh()

    def refresh(self):
        self.wl.config(text="%.2f s" % self.wt)
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        if not self.has("plane"):
            cv.create_text(380, 300, text=T("경사판을 실험대에 놓으세요", "Put the plane on the bench"), fill="#69717a")
            return
        if self.view.get() == "end":
            self.draw_end()
            return
        z = 700.0 / (PLATE + 20)
        cv.create_rectangle(0, 580, 760, 640, fill="#d6d3c8", outline="")
        pts = [self.pp(0, 0), self.pp(PLATE, 0), self.pp(PLATE, -6), self.pp(0, -6)]
        cv.create_polygon(*[c for p in pts for c in p], fill="#c8dfe8", outline="#7f9fb0")
        for mm in range(0, 481, 5):
            ln = 12 if mm % 50 == 0 else 7 if mm % 10 == 0 else 4
            cv.create_line(*(self.pp(mm, 0) + self.pp(mm, ln * 0.6)), fill="#223")
            if mm % 50 == 0:
                cv.create_text(*self.pp(mm, -14), text=str(mm), font=("Helvetica", 8, "bold"))
        for s in (TRK0, TRK1):
            cv.create_line(*(self.pp(s, 0) + self.pp(s, 9)), fill="#555", width=4)
        if self.has("stand"):
            x, y = self.pp(LSUP, -6)
            cv.create_rectangle(x - 10, y, x + 10, 580, fill="#f2f2ee", outline="#999")
        if self.has("ruler"):
            x, y = self.pp(LSUP, 0)
            X = x + 16
            cv.create_rectangle(X, 580 - 200 * z - 6, X + 22, 580, fill="#d6e4ea", outline="#8fa7b4")
            for mm in range(201):
                ln = 10 if mm % 10 == 0 else 7 if mm % 5 == 0 else 4
                cv.create_line(X, 580 - mm * z, X + ln, 580 - mm * z, fill="#223")
                if mm % 50 == 0:
                    cv.create_text(X + 16, 580 - mm * z, text=str(mm // 10), font=("Helvetica", 7))
            cv.create_line(x, y, X + 22, y, fill="#c0392b", dash=(3, 3))
        if self.has("magnet"):
            x, y = self.mag_xy()
            R = RO * 1000 * z
            cv.create_oval(x - R, y - R, x + R, y + R, fill="#6a7078", outline="#2a2d33", width=2)
            r = RI * 1000 * z
            cv.create_oval(x - r, y - r, x + r, y + r, fill="#f4f2ec", outline="")
            cv.create_line(x + r * math.cos(self.ang), y + r * math.sin(self.ang), x + R * 0.95 * math.cos(self.ang), y + R * 0.95 * math.sin(self.ang), fill="#f2c14e", width=3)
        if self.has("bars"):
            pts = [self.pp(BAR0, 0), self.pp(BAR1, 0), self.pp(BAR1, 16), self.pp(BAR0, 16)]
            cv.create_polygon(*[c for p in pts for c in p], fill="", outline="#8a9098", width=2)
        cx, cy, r = 700, 60, 30
        q = math.radians(self.ph.north)
        cv.create_oval(cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6, fill="#fff", outline="#bbb")
        cv.create_line(cx, cy, cx + r * math.cos(q), cy + r * math.sin(q), fill="#c0392b", width=3)
        cv.create_text(cx + (r + 12) * math.cos(q), cy + (r + 12) * math.sin(q), text="N", fill="#c0392b", font=("Helvetica", 9, "bold"))
        pq = math.radians(self.psi)
        cv.create_line(cx - r * 0.8 * math.cos(pq), cy - r * 0.8 * math.sin(pq), cx + r * 0.8 * math.cos(pq), cy + r * 0.8 * math.sin(pq), fill="#2b6cb0", width=2)
        cv.create_text(cx, cy + r + 16, text=T("파랑: 판의 방향", "blue: the plane"), font=("Helvetica", 8), fill="#555")

    def draw_end(self):
        cv = self.cv
        z, cx, y0 = 8.0, 380, 380
        X = lambda c: cx + c * z
        Y = lambda u: y0 - u * z
        cv.create_rectangle(X(-45), Y(0), X(45), Y(-6), fill="#c8dfe8", outline="#7f9fb0")
        if self.has("bars"):
            for c0, c1 in ((-self.dL - 12, -self.dL), (self.dR, self.dR + 12)):
                cv.create_rectangle(X(c0), Y(16), X(c1), Y(0), fill="#b9bfc6", outline="#6b7177")
        if self.has("magnet"):
            cv.create_rectangle(X(-TM * 500), Y(2 * RO * 1000), X(TM * 500), Y(0), fill="#6a7078", outline="#2a2d33")
            cv.create_line(X(0), Y(-2), X(0), Y(28), fill="#c0392b", dash=(3, 3))
        if self.has("ruler"):
            yR = Y(-9)
            cv.create_rectangle(X(-40), yR, X(40), yR + 9 * z, fill="#d6e4ea", outline="#8fa7b4")
            for mm in range(81):
                ln = 3.2 if mm % 10 == 0 else 2.2 if mm % 5 == 0 else 1.4
                cv.create_line(X(-40 + mm), yR, X(-40 + mm), yR + ln * z, fill="#223")
                if mm % 10 == 0:
                    cv.create_text(X(-40 + mm), yR + 5.5 * z, text=str(mm // 10), font=("Helvetica", 8))


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
