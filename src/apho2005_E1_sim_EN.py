#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  6th Asian Physics Olympiad  (APhO 2005, Pekanbaru, Indonesia)
  Experimental Problem 1 :  DETERMINATION OF SHAPES BY REFLECTION
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* Each closed cylindrical box (inner radius 100 mm) holds a mirror-sided
  object turning about the box's axis.  Box A: a triangle or a
  quadrilateral; box B: five sides, one re-entrant corner (light can be
  reflected twice) and one side hollowed into a concave arc.
* The laser, fitted at 180 deg on the wall's scale, sends a 1.2 mm beam
  towards the axis; the beam is traced (as a fan of rays) off the object
  until it reaches the wall; spots coming back to the laser are hidden.
* The shapes, their starting angles against the lid's scale, and the
  laser's aim are hidden and randomised.  The laser's batteries fade.
* Standard library only (tkinter).

    Run:   python3 apho2005_E1_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line

RBOX = 100.0


def inside(P, q):
    c, j = False, len(P) - 1
    for i in range(len(P)):
        a, b = P[i], P[j]
        if (a[1] > q[1]) != (b[1] > q[1]) and q[0] < (b[0] - a[0]) * (q[1] - a[1]) / (b[1] - a[1]) + a[0]:
            c = not c
        j = i
    return c


def area(P):
    return abs(sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))) / 2


# --------------------------------------------------------------------------
#  Physics core  (mm, degrees)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.r = r
        while True:
            A = self.shapeA()
            if inside(A, (0, 0)) and area(A) > 150:
                break
        while True:
            B = self.shapeB()
            if inside(B, (0, 0)) and area(B) > 150:
                break
        self.obj = {"A": A, "B": B}
        self.off = {"A": r.uniform(0, 360), "B": r.uniform(0, 360)}
        self.aim = r.uniform(-0.6, 0.6)
        self.tau = r.uniform(240, 420)

    def shapeA(self):
        r = self.r
        n = 3 if r.random() < 0.6 else 4
        a0 = r.uniform(0, 360)
        out = []
        for i in range(n):
            a = math.radians(a0 + i * 360.0 / n + r.uniform(-22, 22))
            rr = r.uniform(14, 27)
            out.append((rr * math.cos(a), rr * math.sin(a)))
        return out

    def shapeB(self):
        r = self.r
        a0 = r.uniform(0, 360)
        V = []
        for i in range(5):
            a = math.radians(a0 + i * 72 + r.uniform(-10, 10))
            rr = r.uniform(6, 9) if i == 0 else r.uniform(19, 25)
            V.append((rr * math.cos(a), rr * math.sin(a)))
        k = 2 + r.randrange(2)
        A, B = V[k], V[k + 1]
        L = math.hypot(B[0] - A[0], B[1] - A[1])
        s = r.uniform(1.6, 3.0)
        Rc = (L * L / 4 + s * s) / (2 * s)
        m = ((A[0] + B[0]) / 2, (A[1] + B[1]) / 2)
        lm = math.hypot(*m)
        C = (m[0] + m[0] / lm * (Rc - s), m[1] + m[1] / lm * (Rc - s))
        pts = []
        for i in range(5):
            pts.append(V[i])
            if i == k:
                a1, a2 = math.atan2(A[1] - C[1], A[0] - C[0]), math.atan2(B[1] - C[1], B[0] - C[0])
                da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
                for j in range(1, 24):
                    a = a1 + da * j / 24.0
                    pts.append((C[0] + Rc * math.cos(a), C[1] + Rc * math.sin(a)))
        return pts

    def trace(self, box, rot, p, u):
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        P = [(x * c - y * s, x * s + y * c) for x, y in self.obj[box]]
        for _ in range(8):
            best = None
            for i in range(len(P)):
                a, b = P[i], P[(i + 1) % len(P)]
                e = (b[0] - a[0], b[1] - a[1])
                den = u[0] * e[1] - u[1] * e[0]
                if abs(den) < 1e-12:
                    continue
                w = (a[0] - p[0], a[1] - p[1])
                t = (w[0] * e[1] - w[1] * e[0]) / den
                q = (w[0] * u[1] - w[1] * u[0]) / den
                if t > 1e-6 and 0 <= q <= 1 and (best is None or t < best[0]):
                    best = (t, e)
            if best is None:
                break
            t, e = best
            p = (p[0] + u[0] * t, p[1] + u[1] * t)
            le = math.hypot(*e)
            n = (-e[1] / le, e[0] / le)
            dn = u[0] * n[0] + u[1] * n[1]
            u = (u[0] - 2 * dn * n[0], u[1] - 2 * dn * n[1])
        b = p[0] * u[0] + p[1] * u[1]
        cc = p[0] ** 2 + p[1] ** 2 - RBOX ** 2
        t = -b + math.sqrt(b * b - cc)
        return math.degrees(math.atan2(p[1] + u[1] * t, p[0] + u[0] * t)) % 360

    def spots(self, box, rot):
        out = []
        for i in range(9):
            b = self.trace(box, rot, (-RBOX + 0.5, self.aim + (i - 4) * 0.15), (1.0, 0.0))
            if abs((b - 180 + 540) % 360 - 180) >= 4.5:
                out.append(b)
        cl = []
        for b in out:
            for c in cl:
                if abs((b - c[0] + 540) % 360 - 180) < 4:
                    d = (b - c[0] + 540) % 360 - 180
                    c[1] += 1
                    c[2] += d
                    c[3], c[4] = min(c[3], d), max(c[4], d)
                    break
            else:
                cl.append([b, 1, 0.0, 0.0, 0.0])
        return [((c[0] + c[2] / c[1]) % 360, c[1] / 9.0, c[4] - c[3]) for c in cl]


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def box_art(lab):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_oval(x - 40 * s, y - 40 * s, x + 40 * s, y + 40 * s, fill="#dfe5ea", outline="#8a959e", width=2)
        cv.create_oval(x - 10 * s, y - 10 * s, x + 10 * s, y + 10 * s, fill="#3a3d42", outline="")
        cv.create_line(x, y, x + 18 * s, y - 12 * s, fill="#f2c14e", width=2)
        cv.create_text(x, y + 24 * s, text=lab, font=("Helvetica", 10, "bold"))
    return art


def art_laser(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 40 * s, y - 5 * s, x + 30 * s, y + 5 * s, fill="#2a2d33", outline="")
    cv.create_rectangle(x - 10 * s, y - 5 * s, x - 2 * s, y + 5 * s, fill="#c0392b", outline="")


def art_batt(cv, x, y, sc=1.0):
    s = sc
    for dy in (-6, 6):
        cv.create_rectangle(x - 18 * s, y + (dy - 4) * s, x + 18 * s, y + (dy + 4) * s, fill="#2f6fb5", outline="")


def art_ruler(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 60 * s, y - 6 * s, x + 60 * s, y + 6 * s, fill="#d6e4ea", outline="#8fa7b4")
    for i in range(13):
        cv.create_line(x - 60 * s + i * 10 * s, y - 6 * s, x - 60 * s + i * 10 * s, y - 1 * s, fill="#223")


ART = {"boxA": box_art("A"), "boxB": box_art("B"), "laser": art_laser, "batt": art_batt, "ruler": art_ruler}
PARTS = [
    ("boxA",  ("[1A][2] 원통 상자 A (속에 물체)", "[1A][2] Cylindrical box A (object inside)"), []),
    ("boxB",  ("[1B][2] 원통 상자 B (속에 물체)", "[1B][2] Cylindrical box B (object inside)"), []),
    ("laser", ("[4] 레이저 포인터", "[4] Laser pointer"), []),
    ("batt",  ("[5] 여분 건전지", "[5] Spare batteries"), []),
    ("ruler", ("[6] 자", "[6] Ruler"), []),
]
ZONES = {"boxA": (230, 240, 90, 90), "boxB": (470, 240, 90, 90), "laser": (120, 240, 70, 20), "batt": (650, 380, 40, 30), "ruler": (420, 400, 130, 20)}
SCENE_TITLE = ("원통 상자 두 개와 레이저", "Two cylindrical boxes and the laser")
APP_TITLE = ("APhO 2005 실험 1 — 반사로 모양 알아내기", "APhO 2005 Experiment 1 — Determination of shapes by reflection")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.box = tk.StringVar(value="A")       # the box the laser is fitted to, and on view
        self.rot = {"A": 0.0, "B": 0.0}
        self.laser = tk.BooleanVar(value=False)
        self.use = 0.0
        self.view = {"A": 0.0, "B": 0.0}
        self.ruler = tk.BooleanVar(value=False)
        self.drag = None
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def top(self, b):
        return (self.rot[b] + self.ph.off[b]) % 360

    def bright(self):
        return math.exp(-self.use / self.ph.tau) if self.laser.get() and self.has("laser") and self.has("box" + self.box.get()) else 0.0

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("상자 · 레이저", "Box · laser"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Radiobutton(row, text=T("레이저를 상자 A에", "Laser on box A"), value="A", variable=self.box).pack(side="left")
        ttk.Radiobutton(row, text=T("레이저를 상자 B에", "Laser on box B"), value="B", variable=self.box).pack(side="left")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Checkbutton(row, text=T("레이저 켜기 (돌리기)", "Laser on (twist)"), variable=self.laser).pack(side="left")
        ttk.Button(row, text=T("건전지 갈기", "Change batteries"), command=self.new_batt).pack(side="left", padx=4)
        ttk.Checkbutton(row, text=T("자 대기", "Lay the ruler"), variable=self.ruler).pack(side="left")
        self.ll = ttk.Label(f, text="")
        self.ll.pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("손잡이 (물체 돌리기)", "Knob (turns the object)"))
        f.pack(fill="x", pady=2)
        stepper(f, "", [("−10°", lambda: self.turn(-10)), ("−5°", lambda: self.turn(-5)), ("−1°", lambda: self.turn(-1)), ("−0.5°", lambda: self.turn(-0.5))])
        stepper(f, "", [("+0.5°", lambda: self.turn(0.5)), ("+1°", lambda: self.turn(1)), ("+5°", lambda: self.turn(5)), ("+10°", lambda: self.turn(10))])
        ttk.Label(f, text=T("화면의 손잡이를 끌어도 돌아갑니다. 둘레 눈금을 클릭하면 그곳을 확대합니다.", "Dragging the knob on the picture turns it too; click the wall's scale to magnify there."), wraplength=380).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("기록 (읽은 α, β)", "Record (your α, β readings)"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text="α").pack(side="left")
        self.ea = ttk.Entry(row, width=8)
        self.ea.pack(side="left", padx=2)
        ttk.Label(row, text="β").pack(side="left")
        self.eb = ttk.Entry(row, width=8)
        self.eb.pack(side="left", padx=2)
        ttk.Button(row, text=T("적기", "Record"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("b", T("상자", "box"), 50), ("a", "α (°)", 80), ("c", "β (°)", 80)], height=6)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=380)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("상자를 위에서 본 모습 (손잡이를 끌어 돌리기)", "The box from above (drag the knob)"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()
        self.cv.bind("<Button-1>", self.press)
        self.cv.bind("<B1-Motion>", self.motion)
        self.cv.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag", None))

    CX, CY, R = 330, 250, 210

    def ang(self, x, y):
        return math.degrees(math.atan2(self.CY - y, x - self.CX))

    def press(self, e):
        r = math.hypot(e.x - self.CX, e.y - self.CY)
        if r < self.R * 0.45:
            self.drag = self.ang(e.x, e.y)
        elif r < self.R + 30:
            self.view[self.box.get()] = round(self.ang(e.x, e.y) % 360)

    def motion(self, e):
        if self.drag is None:
            return
        a = self.ang(e.x, e.y)
        da = (a - self.drag + 180) % 360 - 180
        self.drag = a
        self.turn(da)

    def turn(self, d):
        b = self.box.get()
        self.rot[b] = round(self.rot[b] + d, 1)

    def new_batt(self):
        if self.has("batt"):
            self.use = 0.0

    def record(self):
        self.sheet.add((self.box.get(), self.ea.get(), self.eb.get()))

    def tick(self, dt):
        if self.laser.get():
            self.use += dt
        self.warn.config(text=T("레이저 빛이 흐립니다 — 건전지를 갈아 주세요.", "The laser is dim: change its batteries.") if self.laser.get() and self.bright() < 0.35 else "")
        self.refresh()

    def refresh(self):
        b = self.box.get()
        self.ll.config(text=T("뚜껑 눈금 α (상자 %s): 화면에서 읽으세요   ·   밝기 %d %%", "Lid scale α (box %s): read it on the picture   ·   brightness %d %%") % (b, round(self.bright() * 100)))
        self.draw()

    def draw(self):
        cv, cx, cy, R = self.cv, self.CX, self.CY, self.R
        cv.delete("all")
        b = self.box.get()
        if not self.has("box" + b):
            cv.create_text(380, 300, text=T("상자 %s를 실험대에 놓으세요" % b, "Put box %s on the bench" % b), fill="#69717a")
            return
        at = lambda a, r: (cx + r * math.cos(math.radians(a)), cy - r * math.sin(math.radians(a)))
        cv.create_oval(cx - R - 6, cy - R - 6, cx + R + 6, cy + R + 6, fill="#cfd6db", outline="#8a959e", width=2)
        cv.create_oval(cx - R + 4, cy - R + 4, cx + R - 4, cy + R - 4, fill="#dfe5ea", outline="#9aa3ab")
        for a in range(360):
            ln = 10 if a % 10 == 0 else 7 if a % 5 == 0 else 4
            cv.create_line(*(at(a, R + 6) + at(a, R + 6 - ln)), fill="#223")
            if a % 30 == 0:
                cv.create_text(*at(a, R + 18), text=str(a), font=("Helvetica", 8, "bold"))
        r1 = R * 0.42
        for a in range(0, 360, 2):
            ln = 8 if a % 10 == 0 else 4
            cv.create_line(*(at(a, r1) + at(a, r1 - ln)), fill="#334")
            if a % 30 == 0:
                cv.create_text(*at(a, r1 + 11), text=str(a), font=("Helvetica", 7))
        cv.create_oval(cx - R * 0.16, cy - R * 0.16, cx + R * 0.16, cy + R * 0.16, fill="#3a3d42", outline="")
        cv.create_line(cx, cy, *at(self.top(b), r1 - 2), fill="#f2c14e", width=3)
        if self.has("laser"):
            x, y = at(180, R + 8)
            cv.create_rectangle(x - 62, y - 7, x - 6, y + 7, fill="#2a2d33", outline="")
            cv.create_rectangle(x - 40, y - 7, x - 32, y + 7, fill="#c0392b" if self.laser.get() else "#5a2a24", outline="")
        B = self.bright()
        S = self.ph.spots(b, self.rot[b]) if B > 0 else []
        for be, w, sp in S:
            x, y = at(be, R + 1)
            rr = 6 + sp
            cv.create_oval(x - rr, y - rr, x + rr, y + rr, fill=self.red(B * (0.4 + 0.6 * w)), outline="")
        if self.ruler.get() and self.has("ruler"):
            z = R / (RBOX + 3)
            y0, x0 = cy + R * 0.55, cx - (RBOX + 3) * z - 6
            cv.create_rectangle(x0, y0 - 12, x0 + (2 * RBOX + 6) * z + 40, y0 + 12, fill="#d6e4ea", outline="#8fa7b4")
            for mm in range(int(((2 * RBOX + 6) * z + 40) / z) + 1):
                X = x0 + 6 + mm * z
                ln = 10 if mm % 10 == 0 else 7 if mm % 5 == 0 else 4
                cv.create_line(X, y0 - 12, X, y0 - 12 + ln, fill="#223")
                if mm % 50 == 0:
                    cv.create_text(X, y0 + 4, text=str(mm // 10), font=("Helvetica", 7))
        # the magnified strip
        sv, sx, sy, sw, sh = self.view[b], 20, 520, 720, 100
        cv.create_rectangle(sx, sy, sx + sw, sy + sh, fill="#dfe5ea", outline="#8a959e")
        pxd = sw / 30.0
        for i in range(-15, 16):
            a = int(round(sv)) + i
            for h in (0, 1):
                aa = a + h * 0.5
                X = sx + sw / 2 + (aa - sv) * pxd
                if X < sx + 2 or X > sx + sw - 2:
                    continue
                ln = 8 if h else (26 if a % 10 == 0 else 18 if a % 5 == 0 else 13)
                cv.create_line(X, sy + sh - 4, X, sy + sh - 4 - ln, fill="#223")
                if not h and a % 5 == 0:
                    cv.create_text(X, sy + sh - 40, text=str(a % 360), font=("Helvetica", 9, "bold"))
        for be, w, sp in S:
            dd = (be - sv + 540) % 360 - 180
            if abs(dd) <= 15.5:
                X = sx + sw / 2 + dd * pxd
                hw = (0.7 + sp) * pxd / 2 + 3
                cv.create_oval(X - hw, sy + 8, X + hw, sy + 50, fill=self.red(B * (0.4 + 0.6 * w)), outline="")
        cv.create_text(sx + 6, sy + 10, anchor="w", text=T("둘레 눈금 확대 (가운데 %d°)", "wall's scale magnified (centre %d°)") % round(sv), fill="#555", font=("Helvetica", 8))

    @staticmethod
    def red(k):
        k = max(0.0, min(1.0, k))
        r0, g0, b0 = 0xdf, 0xe5, 0xea
        return "#%02x%02x%02x" % (int(r0 + (255 - r0) * k), int(g0 + (50 - g0) * k), int(b0 + (40 - b0) * k))


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
