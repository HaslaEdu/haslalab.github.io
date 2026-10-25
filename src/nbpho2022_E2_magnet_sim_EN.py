#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  Nordic-Baltic Physics Olympiad 2022  (NBPhO 2022)
  Problem 9 (experimental) :  MAGNET IN GLASS
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* A glass cylinder (outer glass n_o) with a core of slightly denser glass
  (n_c) as wide as the magnet in its middle.  What the eye sees through
  it is traced ray by ray in the cross-section: refraction at the outer
  surface, at the core (or a stop on the magnet), and out at the back.
  Marks are drawn with the marker on the front surface, on the back
  surface where a point of the front looks through, or across (height).
  Seen from nearby, the magnet's ends show parallax.
* Rolling down a slope, a cylinder accelerates at g sin(a)/(1 + kappa);
  kappa of the glass cylinder follows from its parts (glass 2.5, magnet
  7.5 g/cm3), 1/2 for the solid one.  Two boards rest on one brick, one
  shifted up by s; both cylinders are released by hand with a little
  scatter, and the result says which reached the box first.
* The caliper measures the cylinders and the distance between the last
  two marks.  Nothing is computed for you.
* Hidden truths (the cylinder's and the magnet's sizes, n_o, n_c, the
  run length) are randomised every session.
* Standard library only (tkinter).

    Run:   python3 nbpho2022_E2_magnet_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


# --------------------------------------------------------------------------
#  Physics core  (mm)
# --------------------------------------------------------------------------
def nrm(a):
    l = math.hypot(a[0], a[1])
    return (a[0] / l, a[1] / l)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def hit_circle(p, dv, rho, far):
    b = dot(p, dv)
    c = dot(p, p) - rho * rho
    D = b * b - c
    if D < 0:
        return None
    s = math.sqrt(D)
    t1, t2 = -b - s, -b + s
    t = t2 if far else (t1 if t1 > 1e-7 else t2 if t2 > 1e-7 else None)
    if t is None or t <= 1e-7:
        return None
    return (p[0] + t * dv[0], p[1] + t * dv[1])


def refract(dv, n, n1, n2):
    ci = -dot(n, dv)
    e = n1 / n2
    k = 1 - e * e * (1 - ci * ci)
    if k < 0:
        return None
    f = e * ci - math.sqrt(k)
    return nrm((e * dv[0] + f * n[0], e * dv[1] + f * n[1]))


def angdiff(a, b):
    x = (a - b) % (2 * math.pi)
    return x - 2 * math.pi if x > math.pi else x


class Physics(object):
    def __init__(self, seed=None):
        r = self.r = random.Random(seed)
        self.R, self.Hc, self.rc, self.hm = r.uniform(12.45, 12.65), r.uniform(21, 25), r.uniform(5.85, 6.15), r.uniform(9.3, 9.7)
        self.no = r.uniform(1.49, 1.53)
        self.nc = self.no * (1 + r.uniform(0.015, 0.035))
        self.Rs = r.uniform(12.4, 12.6)
        self.cal0 = r.uniform(-0.02, 0.02)
        self.board, self.brick, self.run, self.jit = 600.0, 56.0, r.uniform(470, 500), 0.012
        rg, rm = 2.5, 7.5
        Mg = rg * (math.pi * self.R ** 2 * self.Hc - math.pi * self.rc ** 2 * self.hm)
        Mm = rm * math.pi * self.rc ** 2 * self.hm
        I = rg * (math.pi * self.R ** 4 * self.Hc / 2 - math.pi * self.rc ** 4 * self.hm / 2) + rm * math.pi * self.rc ** 4 * self.hm / 2
        self.kap = I / ((Mg + Mm) * self.R ** 2)
        # the bench
        self.rot, self.eye = 0.0, 3000.0
        self.marks, self.hmarks = [], []
        self.s, self.swap = 0, False

    def trace(self, x, level):
        R = self.R
        if abs(x) >= R:
            return None
        P1 = (x, -math.sqrt(R * R - x * x))
        E = (0.0, -R - self.eye)
        dv = refract(nrm((P1[0] - E[0], P1[1] - E[1])), (P1[0] / R, P1[1] / R), 1.0, self.no)
        if dv is None:
            return None
        p = P1
        P2 = hit_circle(p, dv, self.rc, False)
        if P2 and dot((P2[0] - p[0], P2[1] - p[1]), dv) > 0:
            if level == "mag":
                return "stop"
            dv = refract(dv, (P2[0] / self.rc, P2[1] / self.rc), self.no, self.nc)
            if dv is None:
                return "stop"
            P3 = hit_circle(P2, dv, self.rc, True)
            if P3 is None:
                return "stop"
            dv = refract(dv, (-P3[0] / self.rc, -P3[1] / self.rc), self.nc, self.no)
            if dv is None:
                return "stop"
            p = P3
        P4 = hit_circle(p, dv, R, True)
        if P4 is None:
            return "stop"
        return math.atan2(P4[1], P4[0])

    def to_cyl(self, psi):
        return psi - math.radians(self.rot)

    def to_lab(self, phi):
        return phi + math.radians(self.rot)

    def apparent_z(self, z):
        return z * self.eye / (self.eye + (self.R - self.rc) / self.no)

    def caliper(self, k):
        r = self.r
        if k == "dia":
            v = 2 * self.R
        elif k == "solid":
            v = 2 * self.Rs
        elif k == "hm":
            if len(self.hmarks) < 2:
                return None
            a, b = self.hmarks[-2:]
            v = abs(a - b) + r.uniform(-0.03, 0.03)
        else:
            if len(self.marks) < 2:
                return None
            a, b = self.marks[-2:]
            v = 2 * self.R * abs(math.sin(angdiff(a, b) / 2)) + r.uniform(-0.04, 0.04)
        return round(v + self.cal0, 2)

    def race(self):
        cyl = ("solid", "glass") if self.swap else ("glass", "solid")
        T_ = []
        for i in (0, 1):
            sa = self.brick / (self.board - (self.s if i == 1 else 0))
            k = self.kap if cyl[i] == "glass" else 0.5
            a = 9810 * sa / (1 + k)
            T_.append(math.sqrt(2 * self.run / a) + self.r.gauss(0, self.jit))
        d = T_[0] - T_[1]
        if abs(d) < 0.004:
            return T("거의 동시", "nearly together")
        first = cyl[0] if d < 0 else cyl[1]
        return T("자석 원통이 먼저", "magnet cylinder first") if first == "glass" else T("꽉 찬 원통이 먼저", "solid cylinder first")


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_boards(cv, x, y, sc=1.0):
    s = sc
    cv.create_polygon(x - 60 * s, y - 14 * s, x + 60 * s, y + 4 * s, x + 60 * s, y + 12 * s, x - 60 * s, y - 6 * s, fill="#d3ab72", outline="#8a6a40")


def art_brick(cv, x, y, sc=1.0):
    cv.create_rectangle(x - 34 * sc, y - 14 * sc, x + 34 * sc, y + 14 * sc, fill="#c4624a", outline="#7a2a22")


def art_box(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 30 * s, y - 20 * s, x + 30 * s, y + 20 * s, fill="#d9c49a", outline="#8a6a40")
    cv.create_rectangle(x - 24 * s, y - 14 * s, x + 24 * s, y + 14 * s, fill="#cdb586", outline="")


def art_glass(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 22 * s, y - 26 * s, x + 22 * s, y + 26 * s, fill="#d4e8f0", outline="#6b8ba3")
    cv.create_rectangle(x - 22 * s, y - 9 * s, x + 22 * s, y + 9 * s, fill="#3a3f45", outline="")


def art_solid(cv, x, y, sc=1.0):
    cv.create_rectangle(x - 22 * sc, y - 24 * sc, x + 22 * sc, y + 24 * sc, fill="#f2efe8", outline="#888")


def art_ruler(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 50 * s, y - 8 * s, x + 50 * s, y + 8 * s, fill="#dbe9f3", outline="#6b8ba3")
    for i in range(-46, 47, 6):
        cv.create_line(x + i * s, y - 8 * s, x + i * s, y + (2 if i % 12 == 0 else -2) * s, fill="#1d3c55")


def art_caliper(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 50 * s, y - 4 * s, x + 50 * s, y + 4 * s, fill="#c9cdd2", outline="#777")
    cv.create_rectangle(x - 50 * s, y - 4 * s, x - 42 * s, y + 24 * s, fill="#c9cdd2", outline="#777")
    cv.create_rectangle(x - 20 * s, y - 14 * s, x + 10 * s, y + 6 * s, fill="#2b2e33", outline="")


def art_marker(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 40 * s, y - 6 * s, x + 26 * s, y + 6 * s, fill="#16191d", outline="")
    cv.create_rectangle(x + 26 * s, y - 4 * s, x + 38 * s, y + 4 * s, fill="#c0392b", outline="")


ART = {"boards": art_boards, "brick": art_brick, "box": art_box, "glass": art_glass, "solid": art_solid,
       "ruler": art_ruler, "caliper": art_caliper, "marker": art_marker}
PARTS = [
    ("boards",  ("판자 두 개 (60 cm)", "Two boards (60 cm)"), []),
    ("brick",   ("벽돌", "Brick"), []),
    ("box",     ("받는 상자", "Catching box"), []),
    ("glass",   ("자석이 든 유리 원통", "Glass cylinder with a magnet"), []),
    ("solid",   ("꽉 찬 원통 (균일)", "Solid cylinder (homogeneous)"), []),
    ("ruler",   ("자", "Ruler"), []),
    ("caliper", ("캘리퍼", "Caliper"), []),
    ("marker",  ("유성 마커", "Permanent marker"), []),
]
ZONES = {
    "boards":  (380, 150, 140, 50),
    "brick":   (150, 150, 80, 40),
    "box":     (620, 150, 70, 50),
    "glass":   (150, 300, 60, 70),
    "solid":   (280, 300, 60, 70),
    "ruler":   (450, 300, 120, 30),
    "caliper": (620, 300, 130, 60),
    "marker":  (400, 420, 100, 30),
}
SCENE_TITLE = ("실험대 — 판자, 벽돌, 상자, 두 원통, 자, 캘리퍼, 마커", "The bench — boards, brick, box, two cylinders, ruler, caliper, marker")
APP_TITLE = ("NBPhO 2022 실험 (문제 9) — 유리 속 자석", "NBPhO 2022 Experiment (Problem 9) — Magnet in glass")


# --------------------------------------------------------------------------
#  Bench tab: looking into the cylinder, the caliper
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.mode = tk.StringVar(value="front")
        self.eye = tk.IntVar(value=3000)
        self.sel = None
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def need(self, *ks):
        for k in ks:
            if not self.has(k):
                self.say(T("먼저 조립 탭에서 '%s'을(를) 놓으시오.", "Place the '%s' in the Assembly tab first.") % T(*dict((a, b) for a, b, _ in PARTS)[k]))
                return False
        return True

    def say(self, s):
        self.lmsg.config(text=s)

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("원통 들여다보기", "Looking into the cylinder"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("눈 거리", "Eye at"), width=8).pack(side="left")
        for v, lb in ((250, "25 cm"), (500, "50 cm"), (3000, "3 m")):
            ttk.Radiobutton(row, text=lb, value=v, variable=self.eye, command=self.eye_changed).pack(side="left")
        stepper(f, T("돌리기", "Turn"), [(t, (lambda d: lambda: self.turn(d))(v)) for t, v in (("↺10°", -10), ("↺1°", -1), ("↺0.2°", -0.2), ("↻0.2°", 0.2), ("↻1°", 1), ("↻10°", 10))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("마커", "Marker"), width=8).pack(side="left")
        for k, lb in (("front", T("앞면 세로선", "line on front")), ("back", T("뒤에 보이는 곳", "line seen behind")), ("h", T("앞면 가로선", "line across"))):
            ttk.Radiobutton(row, text=lb, value=k, variable=self.mode).pack(side="left")
        ttk.Button(f, text=T("표시 모두 지우기", "Erase all marks"), command=self.erase).pack(anchor="w")
        ttk.Label(f, text=T("오른쪽 그림을 클릭하면 그 자리에 마커로 표시합니다.", "Click the picture on the right to mark it there."), foreground="#555", wraplength=330).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("캘리퍼 (0.01 mm)", "Caliper (0.01 mm)"))
        f.pack(fill="x", pady=2)
        row = None
        for i, (k, lb) in enumerate((("dia", T("유리 원통 지름", "glass cylinder diameter")), ("solid", T("꽉 찬 원통 지름", "solid cylinder diameter")),
                                     ("hm", T("가로선 둘 사이", "between two lines across")), ("chord", T("세로선 둘 사이", "between two lines")))):
            if i % 2 == 0:
                row = ttk.Frame(f)
                row.pack(fill="x")
            ttk.Button(row, text=lb, command=(lambda kk: lambda: self.measure(kk))(k)).pack(side="left", padx=1)
        self.dC = tk.Label(f, text="", font=("Courier", 16, "bold"), bg="#9fae8f", fg="#1b1d20", width=12)
        self.dC.pack(pady=2)
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.cent = ttk.Entry(row, width=30)
        self.cent.pack(side="left", padx=2)
        ttk.Button(row, text=T("적기", "Write"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("c", T("읽은 값", "what was read"), 300)], height=6)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.lmsg = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=340)
        self.lmsg.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.lTitle = ttk.Label(right, text="", font=("Helvetica", 10, "bold"))
        self.lTitle.pack(anchor="w")
        self.cv = tk.Canvas(right, width=860, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()
        self.cv.bind("<Button-1>", self.click)

    def eye_changed(self):
        self.ph.eye = float(self.eye.get())
        self.refresh()

    def turn(self, d):
        if self.need("glass"):
            self.ph.rot = round(self.ph.rot + d, 1)
            self.refresh()

    def erase(self):
        self.ph.marks, self.ph.hmarks = [], []
        self.refresh()

    def measure(self, k):
        if not self.need("caliper"):
            return
        if k == "solid" and not self.need("solid"):
            return
        if k != "solid" and not self.need("glass"):
            return
        v = self.ph.caliper(k)
        self.dC.config(text=("%.2f mm" % v) if v is not None else "-.--")
        if v is None:
            self.say(T("선이 두 개 있어야 합니다.", "Two lines are needed."))

    def record(self):
        if self.cent.get().strip():
            self.sheet.add((self.cent.get().strip(),))
            self.cent.delete(0, "end")

    # the front view's geometry
    def geo(self):
        ph = self.ph
        s = min(470 / (2 * ph.R * 1.15), 560 / (ph.Hc * 1.08))
        return 260, 330, s

    def click(self, e):
        ph = self.ph
        if not self.has("glass"):
            return
        cx, cz, s = self.geo()
        x, z = (e.x - cx) / s, (cz - e.y) / s
        if abs(x) >= ph.R * 0.995 or abs(z) > ph.Hc / 2:
            return
        if not self.need("marker"):
            return
        lev = "mag" if abs(z) < ph.apparent_z(ph.hm / 2) else "core"
        self.sel = x
        m = self.mode.get()
        if m == "front":
            ph.marks.append(ph.to_cyl(math.atan2(-math.sqrt(ph.R ** 2 - x * x), x)))
        elif m == "back":
            r = ph.trace(x, lev)
            if r is None or r == "stop":
                self.say(T("그 자리로는 자석에 가려 뒤가 보이지 않습니다.", "The magnet hides the back there."))
                return
            ph.marks.append(ph.to_cyl(r))
        else:
            ph.hmarks.append(z)
        self.refresh()

    def refresh(self):
        ph = self.ph
        self.lTitle.config(text=T("옆에서 들여다본 모습 (눈 %s, 회전 %.1f°) · 오른쪽: 가로 단면", "Seen from the side (eye at %s, turned %.1f°) · right: the cross-section") % (
            ("%g m" % (ph.eye / 1000)) if ph.eye >= 1000 else ("%g cm" % (ph.eye / 10)), ph.rot))
        self.draw()

    def draw(self):
        cv, ph = self.cv, self.ph
        cv.delete("all")
        cv.create_rectangle(10, 20, 510, 630, fill="#cfd6dc", outline="")
        if not self.has("glass"):
            cv.create_text(260, 330, text=T("유리 원통을 놓으시오", "Place the glass cylinder"), fill="#555")
            return
        cx, cz, s = self.geo()
        R, zt = ph.R, ph.Hc / 2
        za = ph.apparent_z(ph.hm / 2)
        X = lambda x: cx + x * s
        Z = lambda z: cz - z * s
        step = 2.0 / s
        x = -R + step / 2
        while x < R:
            for lev in ("core", "mag"):
                r = ph.trace(x, lev)
                if r is None or r == "stop":
                    col = "#2b2e33" if lev == "mag" else "#3c4148"
                else:
                    col = "#e8eef2"
                    phi = ph.to_cyl(r)
                    for m in ph.marks:
                        if abs(angdiff(phi, m)) < 0.012:
                            col = "#8b1e1e"
                            break
                if lev == "mag":
                    cv.create_rectangle(X(x) - 1, Z(za), X(x) + 1.2, Z(-za), fill=col, outline="")
                else:
                    cv.create_rectangle(X(x) - 1, Z(zt), X(x) + 1.2, Z(za), fill=col, outline="")
                    cv.create_rectangle(X(x) - 1, Z(-za), X(x) + 1.2, Z(-zt), fill=col, outline="")
            x += step
        cv.create_rectangle(X(-R), Z(zt + 0.8), X(R), Z(zt), fill="#c9cdd2", outline="#888")
        cv.create_rectangle(X(-R), Z(-zt), X(R), Z(-zt - 0.8), fill="#c9cdd2", outline="#888")
        cv.create_rectangle(X(-R), Z(zt), X(R), Z(-zt), outline="#6b8ba3")
        for m in ph.marks:
            psi = ph.to_lab(m)
            if math.sin(psi) < -0.05:
                cv.create_line(X(R * math.cos(psi)), Z(zt), X(R * math.cos(psi)), Z(-zt), fill="#c0392b", width=3)
        for z in ph.hmarks:
            cv.create_line(X(-R * 0.85), Z(z), X(R * 0.85), Z(z), fill="#c0392b", width=3)
        # the cross-section
        sx, sy = 690, 330
        k = 150 / (R * 1.25)
        cv.create_text(690, 40, text=T("가로 단면 (위에서), 눈은 아래쪽", "Cross-section (from above), the eye below"), font=("Helvetica", 9, "bold"))
        cv.create_oval(sx - R * k, sy - R * k, sx + R * k, sy + R * k, fill="#dbeaf2", outline="#6b8ba3", width=2)
        cv.create_oval(sx - ph.rc * k, sy - ph.rc * k, sx + ph.rc * k, sy + ph.rc * k, fill="#c3dbea", outline="#6b8ba3")
        for m in ph.marks:
            psi = ph.to_lab(m)
            px, py = sx + R * math.cos(psi) * k, sy - R * math.sin(psi) * k
            cv.create_oval(px - 4, py - 4, px + 4, py + 4, fill="#c0392b", outline="")
        if self.sel is not None:
            cv.create_line(sx + self.sel * k, sy + R * k * 1.4, sx + self.sel * k, sy + math.sqrt(max(0, R * R - self.sel ** 2)) * k, fill="#e08a00", width=2, arrow="last")


# --------------------------------------------------------------------------
#  Race tab: two slopes, s, which cylinder first
# --------------------------------------------------------------------------
class RaceTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        ph = app.ph
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("경사면 경주", "Race down the slopes"))
        f.pack(fill="x")
        stepper(f, T("더 올림 s", "Shift s"), [(t, (lambda d: lambda: self.set_s(d))(v)) for t, v in (("−10", -10), ("−1", -1), ("+1", 1), ("+10", 10))])
        self.vS = ttk.Label(f, text="", foreground="#1a4fb4")
        self.vS.pack(anchor="w")
        self.bSwap = ttk.Button(f, text="", command=self.swap)
        self.bSwap.pack(anchor="w")
        ttk.Button(f, text=T("자로 동시에 놓기", "Release both with the ruler"), command=self.go).pack(anchor="w")
        ttk.Label(f, text=T("판자 60 cm, 벽돌 56 mm. s는 가파른 판자가 벽돌 모서리 너머로 더 올라간 길이(판자 따라)입니다. 손으로 놓기 때문에 여러 번 되풀이하세요.",
                            "Board 60 cm, brick 56 mm. s is how much further the steeper board reaches past the brick's edge (along it). The release is by hand: repeat many times."),
                  foreground="#555", wraplength=320).pack(anchor="w")
        self.lb = tk.Listbox(ctl, height=24, width=46)
        self.lb.pack(fill="both", expand=True, pady=4)
        self.lmsg = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=320)
        self.lmsg.pack(anchor="w")
        self.cv = tk.Canvas(self, width=820, height=500, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack(side="left", padx=6, pady=6)
        self.refresh()

    def ok(self):
        for k in ("boards", "brick", "box", "glass", "solid"):
            if k not in self.app.placed:
                self.lmsg.config(text=T("먼저 조립 탭에서 '%s'을(를) 놓으시오.", "Place the '%s' in the Assembly tab first.") % T(*dict((a, b) for a, b, _ in PARTS)[k]))
                return False
        self.lmsg.config(text="")
        return True

    def set_s(self, d):
        self.app.ph.s = max(0, min(150, self.app.ph.s + d))
        self.refresh()

    def swap(self):
        self.app.ph.swap = not self.app.ph.swap
        self.refresh()

    def go(self):
        if self.ok():
            ph = self.app.ph
            self.lb.insert("end", "%d)  s = %d mm · %s" % (self.lb.size() + 1, ph.s, ph.race()))
            self.lb.yview_moveto(1.0)

    def refresh(self):
        ph = self.app.ph
        self.vS.config(text="s = %d mm" % ph.s)
        self.bSwap.config(text=T("가파른 쪽: 자석 원통 (바꾸기)", "steeper: magnet cylinder (swap)") if ph.swap else T("가파른 쪽: 꽉 찬 원통 (바꾸기)", "steeper: solid cylinder (swap)"))
        cv = self.cv
        cv.delete("all")
        sc = 1.2
        X = lambda x: 40 + x * sc
        Y = lambda z: 400 - z * sc * 3
        L, h = ph.board, ph.brick
        cv.create_rectangle(X(-10), Y(h), X(50), Y(0), fill="#c4624a", outline="#7a2a22")
        for i in (0, 1):
            s = ph.s if i else 0
            sa = h / (L - s)
            ca = math.sqrt(1 - sa * sa)
            xlo = 50 + ca * (L - s)
            cv.create_line(X(xlo), Y(0), X(xlo - ca * L), Y(sa * L), fill="#a87838" if i else "#c49a62", width=5)
            cv.create_text(X(xlo - ca * L) + 60, Y(sa * L) - 12 + 26 * i, text=T("판자 2 (s만큼 가파름)", "board 2 (steeper by s)") if i else T("판자 1", "board 1"), fill="#7a4e18", font=("Helvetica", 9, "bold"))
        cv.create_text(400, 470, text=T("판자 2에: %s", "on board 2: %s") % (T("자석 원통", "magnet cylinder") if ph.swap else T("꽉 찬 원통", "solid cylinder")), font=("Helvetica", 10, "bold"))


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
        self.geometry("1320x860")
        self.placed = set()
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_asm = AssemblyTab(nb, self)
        self.tab_bench = BenchTab(nb, self)
        self.tab_race = RaceTab(nb, self)
        nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.tab_bench, text=T(" 원통 들여다보기 ", " Looking into the cylinder "))
        nb.add(self.tab_race, text=T(" 경사면 경주 ", " Race "))

    def on_assembly_change(self, placed):
        self.placed = set(placed)
        self.tab_bench.refresh()
        self.tab_race.refresh()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
