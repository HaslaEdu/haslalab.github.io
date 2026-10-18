#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  33rd International Physics Olympiad  (IPhO 2002, Bali, Indonesia)
  Experimental Problem 2 :  OPTICAL BLACK BOX
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* A sealed 8 cm cube with a horizontal slit (red plastic) in two
  opposite faces.  By slit A sits a grating whose lines cross the slit;
  by slit B one whose lines run along it; in the middle a plane-parallel
  plate, a prism or a thin lens (n = 1.47 at 670 nm), chosen at random.
* The laser's ray is traced in 3D: gratings by their equations (orders
  that cannot leave are lost), glass by Snell's law, the lens as a thin
  lens; only rays leaving through the far slit reach the screen.
* The box turns on its platform about the slit facing the laser and
  can be turned round; the platform slides along the scaled rail.  The
  rail and the graph paper share one arbitrary unit.
* Everything about the box is hidden and randomised.  Standard library
  only (tkinter).

    Run:   python3 ipho2002_E2_sim_KO.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line

LAM, NG = 670e-7, 1.47
LB, SLW, SLH = 8.0, 3.5, 0.1
RX0, XLAS, XSCR, XP_MIN, XP_MAX = 8.0, 12.0, 108.0, 22.0, 99.0
PW, PH = 14.0, 11.2
ORD1 = [(0, 0.46), (1, 0.2), (-1, 0.2), (2, 0.05), (-2, 0.05)]
ORD2 = [(0, 0.5), (1, 0.24), (-1, 0.24)]


def refr2(d, n, r):
    ci = -(d[0] * n[0] + d[1] * n[1])
    k = 1 - r * r * (1 - ci * ci)
    if k < 0:
        return None
    s = r * ci - math.sqrt(k)
    return (r * d[0] + s * n[0], r * d[1] + s * n[1])


def poly_hit(P, p, d, s0):
    best = None
    cx, cy = sum(v[0] for v in P) / len(P), sum(v[1] for v in P) / len(P)
    for i in range(len(P)):
        A, B = P[i], P[(i + 1) % len(P)]
        e = (B[0] - A[0], B[1] - A[1])
        den = d[0] * e[1] - d[1] * e[0]
        if abs(den) < 1e-12:
            continue
        w = (A[0] - p[0], A[1] - p[1])
        s, q = (w[0] * e[1] - w[1] * e[0]) / den, (w[0] * d[1] - w[1] * d[0]) / den
        if s <= s0 or q < 0 or q > 1:
            continue
        if best is None or s < best[0]:
            L = math.hypot(e[1], e[0])
            n = (e[1] / L, -e[0] / L)
            if (A[0] - cx) * n[0] + (A[1] - cy) * n[1] < 0:
                n = (-n[0], -n[1])
            best = (s, n)
    return best


# --------------------------------------------------------------------------
#  Physics core
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.u = r.uniform(0.085, 0.093)
        self.d1, self.d2 = r.uniform(1.85, 2.15) * 1e-4, r.uniform(0.92, 1.08) * 1e-4
        self.g1, self.g2 = r.uniform(0.03, 0.08), LB - r.uniform(0.03, 0.08)
        self.mid = r.choice(["plate", "plate", "prism", "lens"])
        sg = lambda: r.choice((-1, 1))
        if self.mid == "plate":
            self.h, self.beta = r.uniform(1.8, 2.2), sg() * r.uniform(45, 58)
        elif self.mid == "prism":
            self.A, self.side, self.rho = r.uniform(30, 45), sg(), r.uniform(-10, 10)
        else:
            self.f, self.aL = sg() * r.uniform(6, 14), r.uniform(3.0, 5.0)
        self.off = (r.uniform(-2.5, 2.5), r.uniform(-2, 2))
        self.poly = self.mid_poly()

    def mid_poly(self):
        c = (LB / 2, 0.0)
        if self.mid == "plate":
            n = (math.cos(math.radians(self.beta)), math.sin(math.radians(self.beta)))
            t, h, w = (-n[1], n[0]), self.h / 2, 3.0
            return [(c[0] + n[0] * h * s + t[0] * w * q, c[1] + n[1] * h * s + t[1] * w * q) for s, q in ((1, 1), (1, -1), (-1, -1), (-1, 1))]
        if self.mid == "prism":
            H = 3.0
            hw, s, rr_ = H * math.tan(math.radians(self.A / 2)), self.side, math.radians(self.rho)
            pts = [(0, s * H / 2), (hw, -s * H / 2), (-hw, -s * H / 2)]
            return [(c[0] + x * math.cos(rr_) - y * math.sin(rr_), c[1] + x * math.sin(rr_) + y * math.cos(rr_)) for x, y in pts]
        return None

    def trace(self, p0, k0):
        out, stack, n = [], [(p0, k0, 1.0)], 0
        while stack and n < 200:
            n += 1
            p, k, I = stack.pop()
            sgn = 1 if k[0] > 0 else -1
            ev = []
            for ga, key in ((self.g1, "g1"), (self.g2, "g2")):
                s = (ga - p[0]) / k[0]
                if s > 1e-6:
                    ev.append((s, key, None))
            if self.mid == "lens":
                s = (self.aL - p[0]) / k[0]
                if s > 1e-6:
                    ev.append((s, "lens", None))
            if self.poly and abs(k[2]) < 1e-9:
                k2 = math.hypot(k[0], k[1])
                h = poly_hit(self.poly, p, (k[0] / k2, k[1] / k2), 1e-6)
                if h:
                    ev.append((h[0] / k2, "poly", h[1]))
            ev.append((((LB if sgn > 0 else 0) - p[0]) / k[0], "wall", None))
            s, key, nrm = min(ev, key=lambda e: e[0])
            q = (p[0] + k[0] * s, p[1] + k[1] * s, p[2] + k[2] * s)
            if abs(q[1]) > LB / 2 - 0.05 or abs(q[2]) > LB / 2:
                continue
            if key == "wall":
                if abs(q[1]) <= SLW and abs(q[2]) <= SLH:
                    out.append((q, k, I))
                continue
            if key in ("g1", "g2"):
                ax, dd, ords = (1, self.d1, ORD1) if key == "g1" else (2, self.d2, ORD2)
                for m, w in ords:
                    kk = list(k)
                    kk[ax] += m * LAM / dd
                    t = 1 - kk[1] ** 2 - kk[2] ** 2
                    if t > 0 and I * w > 0.004:
                        kk[0] = sgn * math.sqrt(t)
                        stack.append((q, tuple(kk), I * w))
                continue
            if key == "lens":
                if abs(q[1]) > 2.5:
                    stack.append((q, k, I))
                    continue
                sl = k[1] / abs(k[0]) - q[1] / self.f
                ka = math.sqrt(max(0.0, (1 - k[2] ** 2) / (1 + sl * sl)))
                stack.append((q, (sgn * ka, sl * ka, k[2]), I))
                continue
            din = refr2((k[0], k[1]), nrm, 1 / NG)
            if not din:
                continue
            h2 = poly_hit(self.poly, (q[0], q[1]), din, 1e-6)
            if not h2:
                continue
            q2 = (q[0] + din[0] * h2[0], q[1] + din[1] * h2[0], q[2])
            dout = refr2(din, (-h2[1][0], -h2[1][1]), NG)
            if dout:
                stack.append((q2, (dout[0], dout[1], 0.0), I * 0.92))
        return out

    def spots(self, xp, psi, flip):
        """spots on the screen: (x, z, I) in cm from the beam's straight line, as seen from the laser"""
        e = math.radians(psi + (180 if flip else 0))
        c, s, a0 = math.cos(e), math.sin(e), (LB if flip else 0.0)
        res = []
        for q, k, I in self.trace((a0, 0.0, 0.0), (c, -s, 0.0)):
            X, Y = xp + c * (q[0] - a0) - s * q[1], s * (q[0] - a0) + c * q[1]
            kx, ky = c * k[0] - s * k[1], s * k[0] + c * k[1]
            if kx <= 1e-6:
                continue
            t = (XSCR - X) / kx
            y, z = Y + ky * t, q[2] + k[2] * t
            if abs(y) < 16 and -12 < z < 14:
                res.append((-y, z, I))
        return res

    def to_paper(self, x, z):
        return ((x + PW - self.off[0]) / self.u, (z + PH - self.off[1]) / self.u)


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def box_art(col, w, h):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_rectangle(x - w * s, y - h * s, x + w * s, y + h * s, fill=col, outline="#555")
    return art


def art_box(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 24 * s, y - 24 * s, x + 24 * s, y + 24 * s, fill="#1d1f23", outline="#555")
    cv.create_rectangle(x - 26 * s, y - 3 * s, x - 22 * s, y + 3 * s, fill="#c81e1e", outline="")
    cv.create_rectangle(x + 22 * s, y - 3 * s, x + 26 * s, y + 3 * s, fill="#c81e1e", outline="")


ART = {"rail": box_art("#3b4048", 90, 6), "laser": box_art("#1f2226", 26, 8), "platform": box_art("#d8dbe0", 30, 10), "box": art_box,
       "screen": box_art("#f2f2ee", 8, 50), "paper": box_art("#fbfaf2", 34, 26)}
PARTS = [
    ("rail",     ("광학 레일 (눈금)", "Optical rail (scaled)"), []),
    ("laser",    ("레이저 (670 nm)", "Laser (670 nm)"), ["rail"]),
    ("platform", ("상자 받침대 (회전판)", "Box platform (turntable)"), ["rail"]),
    ("box",      ("광학 블랙박스", "Optical black box"), ["platform"]),
    ("screen",   ("스크린", "Screen"), ["rail"]),
    ("paper",    ("모눈종이", "Graph paper"), ["screen"]),
]
ZONES = {"rail": (380, 330, 190, 14), "laser": (120, 290, 56, 18), "platform": (430, 290, 64, 22), "box": (430, 240, 52, 52),
         "screen": (650, 260, 18, 104), "paper": (650, 180, 70, 54)}
SCENE_TITLE = ("레일 · 레이저 · 받침대와 상자 · 스크린과 모눈종이", "Rail · laser · platform and box · screen and graph paper")
APP_TITLE = ("IPhO 2002 실험 2 — 광학 블랙박스", "IPhO 2002 Experiment 2 — Optical black box")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.xp, self.psi, self.flip = 60.0, random.uniform(-4, 4), False
        self.laser = tk.BooleanVar(value=False)
        self.zoom, self.cen = 1.0, None
        self.marks, self.hover = [], None
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("레이저 · 받침대 · 상자", "Laser · platform · box"))
        f.pack(fill="x", pady=2)
        ttk.Checkbutton(f, text=T("레이저 켜기", "Laser on"), variable=self.laser, command=self.refresh).pack(anchor="w")
        stepper(f, T("받침대 (cm)", "Platform (cm)"), [("−10", lambda: self.move(-10)), ("−1", lambda: self.move(-1)), ("−0.1", lambda: self.move(-0.1)),
                                                      ("+0.1", lambda: self.move(0.1)), ("+1", lambda: self.move(1)), ("+10", lambda: self.move(10))])
        stepper(f, T("상자 돌리기", "Turn the box"), [("−5°", lambda: self.turn(-5)), ("−1°", lambda: self.turn(-1)), ("−0.2°", lambda: self.turn(-0.2)),
                                                      ("+0.2°", lambda: self.turn(0.2)), ("+1°", lambda: self.turn(1)), ("+5°", lambda: self.turn(5))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("상자 뒤집기 (A↔B)", "Turn the box round (A↔B)"), command=self.do_flip).pack(side="left")
        self.fl = ttk.Label(row, text="")
        self.fl.pack(side="left", padx=6)
        f = ttk.LabelFrame(ctl, text=T("모눈종이 보기", "Graph paper view"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for z in (1, 3, 8):
            ttk.Button(row, text="×%d" % z, command=lambda z=z: self.set_zoom(z)).pack(side="left")
        ttk.Button(row, text=T("표시 지우기", "Erase marks"), command=self.clear).pack(side="left", padx=4)
        ttk.Label(f, text=T("왼쪽 클릭: 연필 표시 · 오른쪽 클릭: 그곳을 가운데로", "L-click: pencil mark · R-click: centre there"), foreground="#555").pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        ttk.Button(f, text=T("지금 상태와 마지막 표시 적기", "Write down the setting and the last mark"), command=self.record).pack(anchor="w")
        self.sheet = DataSheet(f, [("x", T("받침대 눈금", "platform"), 90), ("a", T("각도", "angle"), 60), ("m", T("표시 (u, v)", "mark (u, v)"), 110)], height=6)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=420)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("스크린의 모눈종이 · 받침대 위 · 레일 눈금", "Graph paper on the screen · platform from above · rail scale"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#cfd2d6", highlightthickness=0)
        self.cv.pack()
        self.cv.bind("<Button-1>", self.on_click)
        self.cv.bind("<Button-3>", self.on_center)
        self.cv.bind("<Motion>", self.on_hover)

    # the paper's view: paper units → canvas
    def pw(self):
        return 2 * PW / self.ph.u, 2 * PH / self.ph.u

    def view(self):
        W, H = self.pw()
        s = min(740 / W, 400 / H) * self.zoom
        c = self.cen or (W / 2, H / 2)
        return s, c

    def P(self, u, v):
        s, c = self.view()
        return 380 + (u - c[0]) * s, 210 - (v - c[1]) * s

    def unP(self, x, y):
        s, c = self.view()
        return c[0] + (x - 380) / s, c[1] - (y - 210) / s

    def on_click(self, e):
        if e.y < 420 and self.has("paper"):
            u, v = self.unP(e.x, e.y)
            W, H = self.pw()
            if 0 <= u <= W and 0 <= v <= H:
                self.marks.append((u, v))
                self.refresh()

    def on_center(self, e):
        if e.y < 420:
            self.cen = self.unP(e.x, e.y)
            self.refresh()

    def on_hover(self, e):
        self.hover = self.unP(e.x, e.y) if e.y < 420 else None
        self.refresh()

    def set_zoom(self, z):
        self.zoom = z
        if z == 1:
            self.cen = None
        self.refresh()

    def clear(self):
        self.marks = []
        self.refresh()

    def move(self, d):
        if self.has("platform"):
            self.xp = max(XP_MIN, min(XP_MAX, round(self.xp + d, 3)))
            self.refresh()

    def turn(self, d):
        if self.has("box"):
            self.psi = max(-80, min(80, round(self.psi + d, 2)))
            self.refresh()

    def do_flip(self):
        if self.has("box"):
            self.flip = not self.flip
            self.refresh()

    def record(self):
        m = "(%.1f, %.1f)" % self.marks[-1] if self.marks else "—"
        self.sheet.add(("%.1f" % ((self.xp - RX0) / self.ph.u), "%.1f°" % self.psi, m))

    def spots(self):
        if not (self.laser.get() and self.has("laser") and self.has("screen")):
            return []
        if self.has("box"):
            return self.ph.spots(self.xp, self.psi, self.flip)
        return [(0.0, 0.0, 1.0)]

    def tick(self, dt):
        pass

    def refresh(self):
        self.fl.config(text=T("레이저 쪽 틈: ", "slit facing the laser: ") + ("B" if self.flip else "A"))
        self.warn.config(text=T("상자를 지난 빛이 스크린에 닿지 않습니다.", "No light from the box reaches the screen.") if self.laser.get() and self.has("box") and not self.spots() else "")
        self.draw()

    def draw(self):
        cv, ph = self.cv, self.ph
        cv.delete("all")
        W, H = self.pw()
        s, c = self.view()
        if self.has("paper"):
            x0, y1 = self.P(0, 0)
            x1, y0 = self.P(W, H)
            cv.create_rectangle(x0, y0, x1, y1, fill="#fbfaf2", outline="")
            step = 10 if s < 2.2 else (5 if s < 5 else 1)
            n = 0
            while n <= W:
                x, _ = self.P(n, 0)
                if -5 < x < 765:
                    cv.create_line(x, max(0, y0), x, min(420, y1), fill="#d77" if n % 50 == 0 else ("#e9a" if n % 10 == 0 else "#f3d0c8"))
                n += step
            n = 0
            while n <= H:
                _, y = self.P(0, n)
                if -5 < y < 425:
                    cv.create_line(max(0, x0), y, min(760, x1), y, fill="#d77" if n % 50 == 0 else ("#e9a" if n % 10 == 0 else "#f3d0c8"))
                n += step
            for n in range(0, int(W) + 1, 50):
                x, _ = self.P(n, 0)
                if 0 < x < 760:
                    cv.create_text(x + 2, min(410, y1 - 8), text=str(n), anchor="w", fill="#b0503a", font=("Helvetica", 8))
            for n in range(50, int(H) + 1, 50):
                _, y = self.P(0, n)
                if 0 < y < 420:
                    cv.create_text(max(4, x0 + 3), y - 7, text=str(n), anchor="w", fill="#b0503a", font=("Helvetica", 8))
        for x, z, I in self.spots():
            u, v = ph.to_paper(x, z)
            px, py = self.P(u, v)
            r = max(2.5, 1.4 * s) * (0.6 + 0.8 * min(1, I * 3))
            cv.create_oval(px - r, py - r, px + r, py + r, fill="#e01010", outline="")
        for u, v in self.marks:
            px, py = self.P(u, v)
            cv.create_line(px - 6, py, px + 6, py, fill="#222", width=2)
            cv.create_line(px, py - 6, px, py + 6, fill="#222", width=2)
        if self.hover:
            cv.create_text(750, 410, text="(%.1f, %.1f)" % self.hover, anchor="e", font=("Helvetica", 9))
        cv.create_rectangle(0, 420, 760, 640, fill="#e9e7e0", outline="")
        # the platform from above
        cx, cy, k = 130, 530, 11
        cv.create_line(5, cy, cx, cy, fill="#d02020", width=2)
        cv.create_oval(cx - 8 * k, cy - 8 * k, cx + 8 * k, cy + 8 * k, fill="#d8dbe0", outline="#888")
        for g in range(0, 360, 5):
            a = math.radians(g)
            r0 = 7.0 if g % 30 == 0 else 7.5
            cv.create_line(cx + r0 * k * math.cos(a), cy + r0 * k * math.sin(a), cx + 8 * k * math.cos(a), cy + 8 * k * math.sin(a), fill="#333")
            if g % 30 == 0:
                cv.create_text(cx + 6.2 * k * math.cos(a), cy + 6.2 * k * math.sin(a), text=str(g if g <= 180 else g - 360), font=("Helvetica", 7))
        if self.has("box"):
            e = math.radians(self.psi + (180 if self.flip else 0))
            ea, eb, a0 = (math.cos(e), math.sin(e)), (-math.sin(e), math.cos(e)), (LB if self.flip else 0)
            Wp = lambda a, b: (cx + ((a - a0) * ea[0] + b * eb[0]) * k, cy + ((a - a0) * ea[1] + b * eb[1]) * k)
            pts = [Wp(0, -LB / 2), Wp(LB, -LB / 2), Wp(LB, LB / 2), Wp(0, LB / 2)]
            cv.create_polygon(*[v for p in pts for v in p], fill="#1d1f23", outline="#000")
            for a, lab in ((0, "A"), (LB, "B")):
                p, q = Wp(a, -SLW), Wp(a, SLW)
                cv.create_line(p[0], p[1], q[0], q[1], fill="#d02020", width=3)
                t = Wp(a + (-1.2 if a else 1.2), 0)
                cv.create_text(t[0], t[1], text=lab, fill="#e8eef2", font=("Helvetica", 10, "bold"))
            pa = math.radians(self.psi)
            cv.create_line(cx, cy, cx + 7.9 * k * math.cos(pa), cy + 7.9 * k * math.sin(pa), fill="#f2c14e", width=2)
        # the rail's scale at the platform's and the screen's index lines
        for i, (x, lab, on) in enumerate(((self.xp, T("받침대 표시선", "platform index"), self.has("platform")), (XSCR, T("스크린 표시선", "screen index"), self.has("screen")))):
            y0, x0, w = 450 + i * 95, 280, 460
            r = (x - RX0) / ph.u
            cv.create_text(x0, y0 - 10, text=lab, anchor="w", font=("Helvetica", 9, "bold"))
            cv.create_rectangle(x0, y0, x0 + w, y0 + 60, fill="#e9e6dc", outline="#999")
            for n in range(int(r - 30), int(r + 31)):
                if n < 0:
                    continue
                X = x0 + w / 2 + (n - r) * w / 60.0
                if X < x0 or X > x0 + w:
                    continue
                L = 26 if n % 10 == 0 else (18 if n % 5 == 0 else 11)
                cv.create_line(X, y0, X, y0 + L, fill="#111", width=2 if n % 10 == 0 else 1)
                if n % 10 == 0:
                    cv.create_text(X, y0 + 38, text=str(n), font=("Helvetica", 9, "bold"))
            if on:
                cv.create_line(x0 + w / 2, y0 - 4, x0 + w / 2, y0 + 60, fill="#c08a10", width=2)


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
