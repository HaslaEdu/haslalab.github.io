#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  3rd Asian Physics Olympiad  (APhO 2002, Singapore)
  Experimental Problem, Part A :  MEASUREMENT OF REFLECTANCE AND
                                  DETERMINATION OF REFRACTIVE INDEX
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* A 650 nm diode laser on a rotary stage gives partially polarized light
  (a hidden axis and degree of polarization); a polarizer on its own
  rotary stage has a hidden axis (the stages' 0 deg means nothing).
* The sample block on the sample stage carries glass (n = 1.57) on one
  face and the semiconductor wafer (hidden n) on the other; reflectances
  follow the absorption-free Fresnel equations.  The detector on its
  revolving arm catches the beam only when it points along 2*theta, and
  shades the incoming beam near 0 deg.
* The power meter gives a reading only when its button is pressed.
* Hidden truths are randomised every session.
* Standard library only (tkinter).

    Run:   python3 apho2002_E1_sim_KO.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line
RAD = math.pi / 180


def n360(a):
    return a % 360.0


def n180(a):
    return (a + 180.0) % 360.0 - 180.0


def fresnel(n, th):
    ti = th * RAD
    st = math.sin(ti) / n
    ct = math.sqrt(1 - st * st)
    ci = math.cos(ti)
    rs = (ci - n * ct) / (ci + n * ct)
    rp = (n * ci - ct) / (ct + n * ci)
    return rp * rp, rs * rs


# --------------------------------------------------------------------------
#  Physics core  (µW, degrees)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.nW, self.nG = r.uniform(3.45, 3.95), 1.57
        self.psiL, self.psiP = r.uniform(0, 180), r.uniform(0, 180)
        self.pol, self.ext = r.uniform(0.86, 0.94), r.uniform(0.002, 0.004)
        self.P0, self.amb = r.uniform(1500, 2600), r.uniform(0.2, 0.6)
        self.wob_s = r.uniform(0.002, 0.005)
        self.wob = 1.0

    def step(self, dt):
        self.wob += (1 - self.wob) * dt / 30 + self.wob_s * math.sqrt(dt) * (random.random() - 0.5) * 1.6

    def reading(self, ang, laser_on, has_pol, block, det, board):
        """power on the detector, µW, and whether the beam is shaded"""
        P = 0.0
        blocked = False
        if laser_on:
            I = self.P0 * self.wob / (0.5 + 0.5 * self.pol)
            eL = n360(ang["laser"] + self.psiL)
            if has_pol:
                ap = n360(ang["pol"] + self.psiP)
                dd = (eL - ap) * RAD
                I *= self.pol * (math.cos(dd) ** 2 + self.ext * math.sin(dd) ** 2) + (1 - self.pol) * 0.5 * (1 + self.ext)
                a, pure = ap, True
            else:
                a, pure = eL, False
            out, R = 180.0, 1.0
            if block:
                th = n360(ang["stage"])
                face, thi = ("glass", n180(th)) if (th < 90 or th > 270) else ("wafer", n180(th - 180))
                thi = abs(thi)
                if thi > 89:
                    return self.amb, True
                Rp, Rs = fresnel(self.nG if face == "glass" else self.nW, thi)
                ca, sa = math.cos(a * RAD) ** 2, math.sin(a * RAD) ** 2
                R = Rp * ca + Rs * sa if pure else self.pol * (Rp * ca + Rs * sa) + (1 - self.pol) * 0.5 * (Rp + Rs)
                out = n360(2 * ang["stage"])
            if det:
                if abs(n180(ang["det"])) < 14:
                    blocked = True
                else:
                    miss = abs(n180(ang["det"] - out))
                    c = 1.0 if miss < 1.4 else (math.cos((miss - 1.4) / 1.2 * math.pi / 2) ** 2 if miss < 2.6 else 0.0)
                    P = I * R * c
        return P + self.amb * (0.15 if board else 1.0), blocked


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_rail(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 90 * s, y - 6 * s, x + 90 * s, y + 6 * s, fill="#2b2e33", outline="#111")


def art_laser(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 26 * s, y - 10 * s, x + 20 * s, y + 6 * s, fill="#1b1d20", outline="#555")
    cv.create_oval(x - 30 * s, y - 6 * s, x - 22 * s, y + 2 * s, fill="#c0392b", outline="")
    cv.create_rectangle(x - 3 * s, y + 6 * s, x + 3 * s, y + 30 * s, fill="#2b2e33", outline="")


def art_pol(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 18 * s, y - 30 * s, x + 18 * s, y + 6 * s, fill="#1b1d20", outline="")
    cv.create_oval(x - 11 * s, y - 23 * s, x + 11 * s, y - 1 * s, fill="#5a5f6a", outline="")
    cv.create_rectangle(x - 3 * s, y + 6 * s, x + 3 * s, y + 30 * s, fill="#2b2e33", outline="")


def art_stage(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 34 * s, y - 14 * s, x + 34 * s, y + 10 * s, fill="#1b1d20", outline="#c9ced3")
    cv.create_rectangle(x - 3 * s, y + 6 * s, x + 3 * s, y + 30 * s, fill="#2b2e33", outline="")


def art_block(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 16 * s, y - 16 * s, x + 16 * s, y + 16 * s, fill="#6b7177", outline="#333")
    cv.create_rectangle(x - 19 * s, y - 14 * s, x - 15 * s, y + 14 * s, fill="#c8e6f0", outline="")
    cv.create_rectangle(x + 15 * s, y - 14 * s, x + 19 * s, y + 14 * s, fill="#3a3f5c", outline="")


def art_det(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 16 * s, y - 14 * s, x + 16 * s, y + 6 * s, fill="#2b2e33", outline="#111")
    cv.create_rectangle(x - 3 * s, y + 6 * s, x + 3 * s, y + 30 * s, fill="#1b1d20", outline="")


def art_meter(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 34 * s, y - 26 * s, x + 34 * s, y + 26 * s, fill="#2b6cb0", outline="#1b4c80")
    cv.create_rectangle(x - 26 * s, y - 18 * s, x + 26 * s, y - 2 * s, fill="#0d1f12", outline="")
    cv.create_oval(x - 6 * s, y + 8 * s, x + 6 * s, y + 20 * s, fill="#e04a3a", outline="")


def art_board(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 6 * s, y - 34 * s, x + 6 * s, y + 34 * s, fill="#11151a", outline="#444")


ART = {"rail": art_rail, "laser": art_laser, "pol": art_pol, "stage": art_stage, "block": art_block, "det": art_det, "meter": art_meter, "board": art_board}

PARTS = [
    ("rail",  ("[6] 광학대", "[6] Optical bench"), []),
    ("laser", ("[1] 다이오드 레이저 (회전대)", "[1] Diode laser (rotary stage)"), ["rail"]),
    ("pol",   ("[2] 편광판 (회전대)", "[2] Polarizer (rotary stage)"), ["rail"]),
    ("stage", ("[4] 시료 회전대", "[4] Sample rotary stage"), ["rail"]),
    ("block", ("[3] 시료 블록 (유리 | 웨이퍼)", "[3] Sample block (glass | wafer)"), ["stage"]),
    ("det",   ("[5] 광검출기 (도는 팔)", "[5] Detector (revolving arm)"), ["stage"]),
    ("meter", ("[5] 레이저 파워미터", "[5] Laser power meter"), []),
    ("board", ("[9] 차광판", "[9] Light-shielding board"), []),
]
ZONES = {"rail": (380, 330, 200, 20), "laser": (560, 280, 70, 60), "pol": (440, 280, 50, 70), "stage": (280, 290, 80, 60), "block": (280, 240, 50, 40),
         "det": (180, 220, 50, 50), "meter": (640, 420, 80, 60), "board": (120, 400, 30, 80)}
SCENE_TITLE = ("광학대 — 레이저, 편광판, 시료 회전대와 검출기", "The bench — laser, polarizer, sample stage and detector")
APP_TITLE = ("APhO 2002 실험 1 — 반사율 측정과 굴절률", "APhO 2002 Experiment 1 — Reflectance and refractive index")
STG = [("laser", ("레이저", "laser")), ("pol", ("편광판", "polarizer")), ("stage", ("시료", "sample")), ("det", ("검출기 팔", "detector arm"))]


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.ang = {"laser": 0.0, "pol": 0.0, "stage": 0.0, "det": 180.0}
        self.laser = tk.BooleanVar(value=False)
        self.lock = tk.BooleanVar(value=False)
        self.held = None
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("레이저 파워미터", "Laser power meter"))
        f.pack(fill="x", pady=2)
        self.dP = tk.Label(f, text="—", font=("Courier", 20, "bold"), bg="#0d1f12", fg="#5cff7a", width=12)
        self.dP.pack(pady=2)
        ttk.Button(f, text=T("측정 버튼 누르기", "Press to measure"), command=self.measure).pack(fill="x")
        f = ttk.LabelFrame(ctl, text=T("레이저", "Laser"))
        f.pack(fill="x", pady=2)
        ttk.Checkbutton(f, text=T("레이저 켜기", "Laser on"), variable=self.laser).pack(anchor="w")
        ttk.Checkbutton(f, text=T("레이저와 편광판을 함께 돌리기", "Turn laser and polarizer together"), variable=self.lock).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("회전대 돌리기", "Turn the stages"))
        f.pack(fill="x", pady=2)
        for k, lab in STG:
            stepper(f, T(*lab), [("−10", lambda k=k: self.turn(k, -10)), ("−1", lambda k=k: self.turn(k, -1)), ("−½", lambda k=k: self.turn(k, -0.5)),
                                 ("+½", lambda k=k: self.turn(k, 0.5)), ("+1", lambda k=k: self.turn(k, 1)), ("+10", lambda k=k: self.turn(k, 10))])
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.note = ttk.Entry(row, width=20)
        self.note.pack(side="left", padx=2)
        ttk.Button(row, text=T("지금 값 적기", "Record"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("p", "P (µW)", 90), ("n", T("메모", "note"), 180)], height=8)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=360)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("위에서 본 광학대와 회전대 눈금 (기준선에서 확대)", "The bench from above, and each stage's scale at its index line"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=780, height=600, bg="#2a2f36", highlightthickness=0)
        self.cv.pack()

    def turn(self, k, d):
        self.ang[k] = n360(self.ang[k] + d)
        if self.lock.get() and k in ("laser", "pol"):
            o = "pol" if k == "laser" else "laser"
            self.ang[o] = n360(self.ang[o] + d)

    def raw(self):
        if not (self.has("meter") and self.has("det")):
            return None, False
        return self.ph.reading(self.ang, self.laser.get() and self.has("laser"), self.has("pol"), self.has("block"), self.has("det"), self.has("board"))

    def measure(self):
        v, _ = self.raw()
        self.held = None if v is None else v * (1 + (random.random() - 0.5) * 0.004)

    def show(self):
        if self.held is None:
            return "----"
        v = self.held
        return ("%.0f" if v >= 1000 else "%.1f" if v >= 100 else "%.2f") % v

    def record(self):
        self.sheet.add((self.show(), self.note.get()))

    def tick(self, dt):
        self.ph.step(dt)
        _, blocked = self.raw()
        self.warn.config(text=T("검출기 팔이 들어오는 빔을 가립니다.", "The detector arm shades the incoming beam.") if blocked and self.laser.get() else "")
        self.refresh()

    def refresh(self):
        self.dP.config(text=self.show() + " µW")
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        z, X0, Y0 = 13.0, 60.0, 250.0                     # px per cm; the stage's centre at (X0 + 22 z, Y0)
        sx, sy = X0 + 22 * z, Y0
        cv.create_rectangle(X0, Y0 - 34, X0 + 54 * z, Y0 + 34, fill="#3b4047", outline="")
        if self.laser.get() and self.has("laser"):
            x1 = sx if self.has("block") else X0
            if self.has("det") and abs(n180(self.ang["det"])) < 14:
                x1 = sx + 11 * z * math.cos(self.ang["det"] * RAD) + 10
            cv.create_line(X0 + 50 * z, Y0, x1, Y0, fill="#ff3c28", width=2)
            if self.has("block"):
                d = n360(2 * self.ang["stage"]) * RAD
                cv.create_line(sx, sy, sx + 30 * z * math.cos(d), sy - 30 * z * math.sin(d), fill="#ff3c28", width=1)
        if self.has("laser"):
            cv.create_rectangle(X0 + 50 * z, Y0 - 12, X0 + 54 * z, Y0 + 12, fill="#1b1d20", outline="#666")
        if self.has("pol"):
            cv.create_rectangle(X0 + 36 * z - 5, Y0 - 34, X0 + 36 * z + 5, Y0 + 34, fill="#555", outline="#999")
        if self.has("stage"):
            R = 3.6 * z
            cv.create_oval(sx - R, sy - R, sx + R, sy + R, fill="#1b1d20", outline="#c9ced3", width=2)
            if self.has("block"):
                a = -self.ang["stage"] * RAD
                P = lambda u, v: (sx + (u * math.cos(a) - v * math.sin(a)) * z, sy + (u * math.sin(a) + v * math.cos(a)) * z)
                cv.create_polygon(P(-1.2, -1.6) + P(1.2, -1.6) + P(1.2, 1.6) + P(-1.2, 1.6), fill="#6b7177", outline="#333")
                cv.create_polygon(P(1.2, -1.5) + P(1.4, -1.5) + P(1.4, 1.5) + P(1.2, 1.5), fill="#c8e6f0", outline="")
                cv.create_polygon(P(-1.4, -1.5) + P(-1.2, -1.5) + P(-1.2, 1.5) + P(-1.4, 1.5), fill="#3a3f5c", outline="")
            if self.has("det"):
                a = self.ang["det"] * RAD
                dx, dy = sx + 11 * z * math.cos(a), sy - 11 * z * math.sin(a)
                cv.create_line(sx, sy, dx, dy, fill="#9ea4ab", width=6)
                cv.create_oval(dx - 14, dy - 14, dx + 14, dy + 14, fill="#2b2e33", outline="#111")
        # the scale windows
        for i, (k, lab) in enumerate(STG):
            x, y, w, h = 10 + i * 192, 470, 182, 120
            cv.create_rectangle(x, y, x + w, y + h, fill="#1b1d20", outline="#555")
            a, ppd, cx = self.ang[k], w / 22.0, x + w / 2
            for dg in range(int(math.floor(a)) - 11, int(math.ceil(a)) + 12):
                xx = cx + (dg - a) * ppd
                if xx < x + 2 or xx > x + w - 2:
                    continue
                ln = 30 if dg % 10 == 0 else 20 if dg % 5 == 0 else 12
                cv.create_line(xx, y + 38, xx, y + 38 + ln, fill="#e8eef2")
                if dg % 10 == 0:
                    cv.create_text(xx, y + 22, text=str(dg % 360), fill="#e8eef2", font=("Helvetica", 11, "bold"))
            cv.create_line(cx, y + 34, cx, y + 86, fill="#ff4a3a", width=2)
            cv.create_text(cx, y + 104, text=T(*lab), fill="#ffcf3a", font=("Helvetica", 10, "bold"))


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
