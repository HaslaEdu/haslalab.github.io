#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  Nordic-Baltic Physics Olympiad 2024  (NBPhO 2024)
  Problem 5 (experimental) :  STRING AND PENDULUM
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* Part i: two steel nuts on orange threads clamped between wooden
  blocks.  Each is a physical pendulum (the nut's radius of gyration k
  about its centre) integrated at any amplitude by RK4, with a little air
  drag, so a large swing slowly loses amplitude, as a real one does.  The
  period grows with amplitude as the exact pendulum does
  (A = 1/16 for small amplitudes, a little more at large ones).
* There is no stopwatch, as in the problem: pull both nuts aside, release
  them together, and see whether they keep in step.
* Part ii: the red string tied between two knots on the level bar, the
  staple (0.0889 g) at its middle.  Each half is a catenary of the
  string's own weight; the angles at the staple and at the knots follow.
* The protractor and the tape are drawn with their scales; magnifiers
  show them close up.  Nothing is computed for you.
* Hidden truths (the string's mass per metre, the nut's k, the drag, the
  tape's zero, the bar's small tilt) are randomised every session.
* Standard library only (tkinter).

    Run:   python3 nbpho2024_E1_pendulum_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


# --------------------------------------------------------------------------
#  Physics core  (SI)
# --------------------------------------------------------------------------
class Pend(object):
    def __init__(self, L):
        self.L, self.th, self.om = L, 0.0, 0.0
        self.held, self.hold, self.swinging = False, 0.0, False


class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.g = 9.818
        self.k = r.uniform(0.0060, 0.0075)
        self.lin, self.quad = r.uniform(0.004, 0.008), r.uniform(0.03, 0.05)
        self.lam = r.uniform(0.115, 0.155) * 1e-3          # kg per metre: the answer of (ii)
        self.m_staple = 0.0889e-3
        self.tape0 = r.uniform(-0.4, 0.4) * 1e-3
        self.tilt = math.radians(r.uniform(-0.15, 0.15))
        self.P = [Pend(0.415), Pend(0.365)]
        self.knots, self.sLen = [0.08, 0.48], 0.52
        self.tied, self.staple = False, False

    def acc(self, p, th, om):
        w2 = self.g * p.L / (p.L ** 2 + self.k ** 2)
        return -w2 * math.sin(th) - self.lin * om - self.quad * p.L * om * abs(om)

    def step(self, dt):
        for p in self.P:
            if p.held:
                p.th, p.om = p.hold, 0.0
                continue
            if not p.swinging:
                continue
            n = max(1, int(math.ceil(dt / 0.002)))
            h = dt / n
            for _ in range(n):
                t, w = p.th, p.om
                k1t, k1w = w, self.acc(p, t, w)
                k2t, k2w = w + h / 2 * k1w, self.acc(p, t + h / 2 * k1t, w + h / 2 * k1w)
                k3t, k3w = w + h / 2 * k2w, self.acc(p, t + h / 2 * k2t, w + h / 2 * k2w)
                k4t, k4w = w + h * k3w, self.acc(p, t + h * k3t, w + h * k3w)
                p.th += h / 6 * (k1t + 2 * k2t + 2 * k3t + k4t)
                p.om += h / 6 * (k1w + 2 * k2w + 2 * k3w + k4w)

    def shape(self):
        """half the string from the staple (s = 0) to a knot: slope tangent u0 + s/a"""
        d, l = self.knots[1] - self.knots[0], self.sLen
        m = self.m_staple if self.staple else 0.0
        if l <= d + 1e-4:
            return None

        def xhalf(a):
            u0 = m / (2 * self.lam * a)
            return a * (math.asinh(u0 + l / 2 / a) - math.asinh(u0))
        lo, hi = 1e-6, 1e3
        for _ in range(200):
            mid = math.sqrt(lo * hi)
            if xhalf(mid) > d / 2:
                hi = mid
            else:
                lo = mid
        a = math.sqrt(lo * hi)
        u0 = m / (2 * self.lam * a)
        u1 = u0 + l / 2 / a
        sag = a * (math.sqrt(1 + u1 * u1) - math.sqrt(1 + u0 * u0))
        return d, l, a, u0, u1, sag

    def string_pts(self, n=40):
        S = self.shape()
        if S is None:
            d = self.knots[1] - self.knots[0]
            return [(0.0, 0.0), (d, 0.0)]
        d, l, a, u0, u1, sag = S
        half = []
        for i in range(n + 1):
            s = l / 2 * i / n
            u = u0 + s / a
            half.append((a * (math.asinh(u) - math.asinh(u0)), a * (math.sqrt(1 + u * u) - math.sqrt(1 + u0 * u0))))
        pts = [(d / 2 - x, sag - y) for x, y in reversed(half)]
        pts += [(d / 2 + x, sag - y) for x, y in half[1:]]
        return pts


# --------------------------------------------------------------------------
#  Drawing: protractor and tape on a Tk canvas, through a view (X, Y, s)
# --------------------------------------------------------------------------
class View(object):
    def __init__(self, ox, oy, s):
        self.ox, self.oy, self.s = ox, oy, s

    def X(self, x):
        return self.ox + x * self.s

    def Y(self, z):
        return self.oy + z * self.s

    def zoom(self, px, py, cx, cy, z):
        """a view showing world-screen point (px,py) of this view at (cx,cy), magnified z times"""
        return View(cx + (self.ox - px) * z, cy + (self.oy - py) * z, self.s * z)


def protractor(cv, v, cx, cz, R, down=True):
    x0, y0, s = v.X(cx), v.Y(cz), v.s
    sgn = 1 if down else -1
    cv.create_arc(x0 - R * s, y0 - R * s, x0 + R * s, y0 + R * s, start=180 if down else 0, extent=180,
                  fill="#dbe9f3", outline="#4f7896", style="pieslice", stipple="gray50")
    step = 1 if s > 25 else 5 if s > 9 else 10
    lab = 10 if s > 25 else 30 if s > 9 else 90
    for deg in range(0, 181, step):
        a = math.radians(deg)
        c, sn = math.cos(a), math.sin(a) * sgn
        ln = 0.9 if deg % 10 == 0 else 0.6 if deg % 5 == 0 else 0.35
        cv.create_line(x0 - c * R * s, y0 + sn * R * s, x0 - c * (R - ln) * s, y0 + sn * (R - ln) * s, fill="#1d3c55", width=1)
        if deg % lab == 0:
            cv.create_text(x0 - c * (R - 1.6) * s, y0 + sn * (R - 1.6) * s, text=str(deg), fill="#1d3c55", font=("Helvetica", 8))


def tape(cv, v, x0, z0, ux, uz, length):
    s, nx, nz, w = v.s, -uz, ux, 1.6
    P = lambda a, b: (v.X(x0 + ux * a + nx * b), v.Y(z0 + uz * a + nz * b))
    pts = [P(0, 0), P(length, 0), P(length, w), P(0, w)]
    cv.create_polygon(*[c for p in pts for c in p], fill="#f6d23c", outline="")
    step = 1 if s > 12 else 5 if s > 4 else 10
    every = 10 if s >= 14 else 50 if s >= 5 else 100
    for mm in range(0, int(length * 10) + 1, step):
        a = mm / 10.0
        ln = 0.7 if mm % 10 == 0 else 0.48 if mm % 5 == 0 else 0.3
        p, q = P(a, 0), P(a, ln)
        cv.create_line(p[0], p[1], q[0], q[1], fill="#1b1d20")
        if mm % every == 0:
            c = P(a, 1.12)
            cv.create_text(c[0], c[1], text=str(mm // 10), fill="#c0201c" if mm % 100 == 0 else "#1b1d20", font=("Helvetica", 8, "bold"))


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_stand(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 30 * s, y + 30 * s, x + 30 * s, y + 40 * s, fill="#3d4248", outline="")
    cv.create_rectangle(x - 2 * s, y - 45 * s, x + 2 * s, y + 30 * s, fill="#b8bdc3", outline="")


def art_blocks(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 25 * s, y - 12 * s, x - 3 * s, y + 12 * s, fill="#c49a62", outline="#8a6a40")
    cv.create_rectangle(x + 3 * s, y - 12 * s, x + 25 * s, y + 12 * s, fill="#c49a62", outline="#8a6a40")


def art_nuts(cv, x, y, sc=1.0):
    s = sc
    for dx in (-14, 14):
        pts = []
        for i in range(6):
            a = i * math.pi / 3
            pts += [x + dx * s + 11 * s * math.cos(a), y + 11 * s * math.sin(a)]
        cv.create_polygon(*pts, fill="#9aa1a8", outline="#555")
        cv.create_line(x + dx * s, y - 30 * s, x + dx * s, y - 8 * s, fill="#ff8a1a", width=2)


def art_bar(cv, x, y, sc=1.0):
    cv.create_rectangle(x - 40 * sc, y - 4 * sc, x + 40 * sc, y + 4 * sc, fill="#c9cdd2", outline="#777")


def art_red(cv, x, y, sc=1.0):
    cv.create_line(x - 35 * sc, y - 10 * sc, x, y + 20 * sc, x + 35 * sc, y - 10 * sc, smooth=True, fill="#d0242b", width=2)


def art_staple(cv, x, y, sc=1.0):
    cv.create_line(x - 10 * sc, y + 8 * sc, x - 10 * sc, y - 8 * sc, x + 10 * sc, y - 8 * sc, x + 10 * sc, y + 8 * sc, fill="#8d939a", width=2)


def art_tape(cv, x, y, sc=1.0):
    cv.create_oval(x - 20 * sc, y - 20 * sc, x + 20 * sc, y + 20 * sc, fill="#f2c418", outline="#9a7a08")


def art_prot(cv, x, y, sc=1.0):
    cv.create_arc(x - 30 * sc, y - 20 * sc, x + 30 * sc, y + 40 * sc, start=0, extent=180, fill="#dbe9f3", outline="#6b8ba3")


def art_marker(cv, x, y, sc=1.0):
    cv.create_rectangle(x - 30 * sc, y - 5 * sc, x + 25 * sc, y + 5 * sc, fill="#16191d", outline="")


ART = {"stand": art_stand, "blocks": art_blocks, "nuts": art_nuts, "bar": art_bar, "red": art_red,
       "staple": art_staple, "tape": art_tape, "prot": art_prot, "marker": art_marker}
PARTS = [
    ("stand",  ("클램프가 달린 스탠드", "Stand with a clamp"), []),
    ("blocks", ("나무 블록 두 개 (클램프에)", "Two wooden blocks (in the clamp)"), ["stand"]),
    ("nuts",   ("주황 실 두 가닥 + 강철 너트 두 개", "Two orange threads + two steel nuts"), ["blocks"]),
    ("bar",    ("실 걸이 막대 (수평)", "Thread bar (level)"), ["stand"]),
    ("red",    ("빨간 실", "Red string"), ["bar"]),
    ("staple", ("스테이플 m = 0.0889 g", "Staple m = 0.0889 g"), []),
    ("tape",   ("줄자", "Tape measure"), []),
    ("prot",   ("각도기", "Protractor"), []),
    ("marker", ("유성 마커", "Permanent marker"), []),
]
ZONES = {
    "stand": (380, 280, 80, 170), "blocks": (300, 180, 70, 40), "nuts": (300, 290, 60, 60), "bar": (480, 250, 140, 30),
    "red": (480, 320, 110, 50), "staple": (480, 390, 50, 30), "tape": (150, 420, 60, 60), "prot": (240, 430, 80, 50),
    "marker": (630, 430, 80, 30),
}
SCENE_TITLE = ("실험대 — 스탠드, 블록, 너트, 막대, 실, 스테이플, 줄자, 각도기, 마커",
               "The bench — stand, blocks, nuts, bar, string, staple, tape, protractor, marker")
APP_TITLE = ("NBPhO 2024 실험 (문제 5) — 실과 진자", "NBPhO 2024 Experiment (Problem 5) — String and pendulum")
PIV = [(-3.0, 2.2), (3.0, 2.2)]
BAR_LEN = 60.0


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.tapeW = tk.StringVar(value="none")
        self.protW = tk.StringVar(value="none")
        self.view = tk.StringVar(value="pend")
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def warn(self, s):
        self.msg.config(text=s)

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        for i, n in enumerate("AB"):
            f = ttk.LabelFrame(ctl, text=T("진자 %s (%s)" % (n, "앞" if i == 0 else "뒤"), "Pendulum %s (%s)" % (n, "front" if i == 0 else "back")))
            f.pack(fill="x", pady=2)
            stepper(f, T("실 길이", "Thread"), [(t, (lambda ii, dd: lambda: self.length(ii, dd))(i, dv)) for t, dv in (("−1cm", -1), ("−1mm", -0.1), ("+1mm", 0.1), ("+1cm", 1))])
            stepper(f, T("당겨 잡기", "Pull aside"), [(t, (lambda ii, dd: lambda: self.hold(ii, dd))(i, dv)) for t, dv in (("◀5°", -5), ("◀1°", -1), ("1°▶", 1), ("5°▶", 5))])
            stepper(f, "", [(T("놓기", "Release"), (lambda ii: lambda: self.release(ii))(i)), (T("멈추기", "Stop"), (lambda ii: lambda: self.stop(ii))(i))])
        ttk.Button(ctl, text=T("둘 다 동시에 놓기", "Release both together"), command=self.release_both).pack(fill="x", pady=2)
        f = ttk.LabelFrame(ctl, text=T("막대와 빨간 실", "Bar and red string"))
        f.pack(fill="x", pady=2)
        stepper(f, T("왼 매듭", "Left knot"), [(t, (lambda dd: lambda: self.knot(0, dd))(dv)) for t, dv in (("−1cm", -1), ("−1mm", -0.1), ("+1mm", 0.1), ("+1cm", 1))])
        stepper(f, T("오른 매듭", "Right knot"), [(t, (lambda dd: lambda: self.knot(1, dd))(dv)) for t, dv in (("−1cm", -1), ("−1mm", -0.1), ("+1mm", 0.1), ("+1cm", 1))])
        stepper(f, T("실 길이", "String"), [(t, (lambda dd: lambda: self.slen(dd))(dv)) for t, dv in (("−1cm", -1), ("−1mm", -0.1), ("+1mm", 0.1), ("+1cm", 1))])
        stepper(f, "", [(T("묶기 / 풀기", "Tie / untie"), self.tie), (T("스테이플 걸기 / 떼기", "Staple on / off"), self.staple)])
        f = ttk.LabelFrame(ctl, text=T("재기", "Measure"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("줄자", "Tape"), width=8).pack(side="left")
        for k, lab in (("none", T("치움", "off")), ("A", T("실 A", "thread A")), ("B", T("실 B", "thread B")), ("bar", T("막대", "bar")), ("str", T("빨간 실", "red string"))):
            ttk.Radiobutton(row, text=lab, value=k, variable=self.tapeW, command=self.refresh).pack(side="left")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("각도기", "Protractor"), width=8).pack(side="left")
        for k, lab in (("none", T("치움", "off")), ("A", "A"), ("B", "B"), ("stp", T("스테이플", "staple")), ("k1", T("왼 매듭", "left knot")), ("k2", T("오른 매듭", "right knot"))):
            ttk.Radiobutton(row, text=lab, value=k, variable=self.protW, command=self.refresh).pack(side="left")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("보기", "View"), width=8).pack(side="left")
        ttk.Radiobutton(row, text=T("진자", "pendulums"), value="pend", variable=self.view, command=self.refresh).pack(side="left")
        ttk.Radiobutton(row, text=T("막대와 실", "bar and string"), value="str", variable=self.view, command=self.refresh).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.cent = ttk.Entry(row, width=30)
        self.cent.pack(side="left", padx=2)
        ttk.Button(row, text=T("적기", "Write"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("n", "#", 30), ("c", T("읽은 값", "reading"), 280)], height=5)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        top = ttk.Frame(right)
        top.pack(anchor="w")
        self.cv = tk.Canvas(top, width=640, height=600, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack(side="left")
        side = ttk.Frame(top)
        side.pack(side="left", padx=6)
        ttk.Label(side, text=T("확대경 1", "Magnifier 1")).pack()
        self.z1 = tk.Canvas(side, width=240, height=240, bg="#fbfaf6", highlightthickness=1, highlightbackground="#333")
        self.z1.pack()
        ttk.Label(side, text=T("확대경 2", "Magnifier 2")).pack()
        self.z2 = tk.Canvas(side, width=240, height=240, bg="#fbfaf6", highlightthickness=1, highlightbackground="#333")
        self.z2.pack()
        self.msg = ttk.Label(right, text="", foreground="#8a1b1b", wraplength=880)
        self.msg.pack(anchor="w", pady=4)

    # ---- actions ----
    def length(self, i, dcm):
        p = self.ph.P[i]
        if not self.has("nuts"):
            return self.warn(T("너트를 먼저 거시오.", "Hang the nuts first."))
        if p.swinging and not p.held:
            return self.warn(T("흔들리는 진자를 먼저 멈추시오.", "Stop the swinging pendulum first."))
        p.L = max(0.10, min(0.70, round(p.L + dcm / 100, 4)))

    def hold(self, i, ddeg):
        p = self.ph.P[i]
        if not self.has("nuts"):
            return self.warn(T("너트를 먼저 거시오.", "Hang the nuts first."))
        if p.swinging and not p.held:
            return self.warn(T("흔들리는 진자를 먼저 멈추시오.", "Stop the swinging pendulum first."))
        p.held, p.swinging = True, False
        p.hold = max(-1.45, min(1.45, p.hold + math.radians(ddeg)))
        p.th, p.om = p.hold, 0.0

    def release(self, i):
        p = self.ph.P[i]
        if not p.held:
            return self.warn(T("먼저 너트를 옆으로 당겨 잡으시오.", "Pull the nut aside first."))
        p.held, p.swinging, p.hold = False, True, 0.0

    def release_both(self):
        if not all(p.held for p in self.ph.P):
            return self.warn(T("두 너트를 모두 당겨 잡은 뒤 놓으시오.", "Pull both nuts aside first."))
        self.release(0)
        self.release(1)

    def stop(self, i):
        p = self.ph.P[i]
        p.held, p.swinging, p.hold, p.th, p.om = False, False, 0.0, 0.0, 0.0

    def knot(self, k, dcm):
        ph = self.ph
        if not self.has("red"):
            return self.warn(T("빨간 실을 먼저 거시오.", "Hang the red string first."))
        v = round(ph.knots[k] + dcm / 100, 3)
        o = ph.knots[1 - k]
        if v < 0.02 or v > 0.58 or (v > o - 0.05 if k == 0 else v < o + 0.05):
            return
        old = ph.knots[k]
        ph.knots[k] = v
        if ph.tied and ph.knots[1] - ph.knots[0] > ph.sLen:
            ph.knots[k] = old
            self.warn(T("실이 두 매듭 사이 거리보다 짧습니다.", "The string is shorter than the knots' distance."))

    def slen(self, dcm):
        ph = self.ph
        if ph.tied:
            return self.warn(T("묶인 실은 길이를 바꿀 수 없습니다.", "Untie the string first."))
        ph.sLen = max(0.12, min(0.58, round(ph.sLen + dcm / 100, 3)))

    def tie(self):
        ph = self.ph
        if not self.has("red"):
            return self.warn(T("빨간 실을 먼저 거시오.", "Hang the red string first."))
        if ph.tied:
            if ph.staple:
                return self.warn(T("스테이플을 먼저 떼시오.", "Take the staple off first."))
            ph.tied = False
        elif ph.knots[1] - ph.knots[0] > ph.sLen:
            return self.warn(T("실이 너무 짧습니다.", "The string is too short."))
        else:
            ph.tied = True

    def staple(self):
        ph = self.ph
        if not (self.has("staple") and ph.tied):
            return self.warn(T("스테이플을 놓고 실을 먼저 묶으시오.", "Place the staple and tie the string first."))
        ph.staple = not ph.staple

    def record(self):
        c = self.cent.get().strip()
        if c:
            self.sheet.add((len(self.sheet.tv.get_children()) + 1, c))
            self.cent.delete(0, "end")

    def tick(self, dt):
        self.ph.step(dt)
        self.refresh()

    # ---- drawing ----
    def refresh(self):
        for c in (self.cv, self.z1, self.z2):
            c.delete("all")
        if self.view.get() == "pend":
            self.draw_pend()
        else:
            self.draw_str()

    def pend_scene(self, cv, v):
        ph, tw, pw = self.ph, self.tapeW.get(), self.protW.get()
        if not (self.has("stand") and self.has("blocks") and self.has("nuts")):
            cv.create_text(v.X(0), v.Y(30), text=T("스탠드에 블록과 너트를 거시오", "Hang the blocks and nuts on the stand"), fill="#69717a")
            return
        if tw in ("A", "B") and self.has("tape"):
            i = 0 if tw == "A" else 1
            tape(cv, v, PIV[i][0] + (1.4 if i else -1.4), PIV[i][1] + ph.tape0 * 100, 0, 1, 72)
        cv.create_rectangle(v.X(-9), v.Y(-2), v.X(9), v.Y(2.2), fill="#c49a62", outline="#8a6a40")

        def thread(i):
            p = ph.P[i]
            L = p.L * 100
            q = (v.X(PIV[i][0]), v.Y(PIV[i][1]))
            n = (v.X(PIV[i][0] + L * math.sin(p.th)), v.Y(PIV[i][1] + L * math.cos(p.th)))
            cv.create_line(q[0], q[1], n[0], n[1], fill="#e0761a" if i else "#ff8a1a", width=2)
            pts = []
            for j in range(6):
                a = p.th + j * math.pi / 3
                pts += [n[0] + 0.95 * v.s * math.cos(a), n[1] + 0.95 * v.s * math.sin(a)]
            cv.create_polygon(*pts, fill="#8b9299" if i else "#a3aab1", outline="#4a4f55")
            r = 0.42 * v.s
            cv.create_oval(n[0] - r, n[1] - r, n[0] + r, n[1] + r, fill="#e9e7e0", outline="#4a4f55")
            cv.create_oval(n[0] - 1.5, n[1] - 1.5, n[0] + 1.5, n[1] + 1.5, fill="#1b1d20")
        if pw in ("A", "B") and self.has("prot"):
            i = 0 if pw == "A" else 1
            thread(1 - i)
            protractor(cv, v, PIV[i][0], PIV[i][1], 9, True)
            thread(i)
        else:
            thread(1)
            thread(0)

    def draw_pend(self):
        v = View(300, 20, 7.5)
        self.pend_scene(self.cv, v)
        ph, tw, pw = self.ph, self.tapeW.get(), self.protW.get()
        if pw in ("A", "B"):
            i = 0 if pw == "A" else 1
            th = ph.P[i].th
            px, py = v.X(PIV[i][0] + 8.4 * math.sin(th)), v.Y(PIV[i][1] + 8.4 * math.cos(th))
            self.pend_scene(self.z1, v.zoom(px, py, 120, 120, 6))
        if tw in ("A", "B"):
            i = 0 if tw == "A" else 1
            px, py = v.X(PIV[i][0] + (0.7 if i else -0.7)), v.Y(PIV[i][1] + ph.P[i].L * 100)
            self.pend_scene(self.z2, v.zoom(px, py, 120, 120, 7))

    def str_scene(self, cv, v):
        ph = self.ph
        if not (self.has("stand") and self.has("bar")):
            cv.create_text(v.X(30), v.Y(10), text=T("스탠드에 막대를 거시오", "Hang the bar on the stand"), fill="#69717a")
            return
        tl = math.tan(ph.tilt)
        if self.tapeW.get() == "bar" and self.has("tape"):
            tape(cv, v, -0.3, -1.0, 1, -tl, BAR_LEN + 0.3)
        cv.create_polygon(v.X(0), v.Y(0), v.X(BAR_LEN), v.Y(-BAR_LEN * tl), v.X(BAR_LEN), v.Y(-BAR_LEN * tl - 1), v.X(0), v.Y(-1), fill="#c9cdd2", outline="#777")
        if not (self.has("red") and ph.tied):
            return
        k0 = ph.knots[0] * 100
        pts = [(k0 + x * 100, y * 100 - (k0 + x * 100) * tl) for x, y in ph.string_pts(40)]

        def string():
            cv.create_line(*[c for x, y in pts for c in (v.X(x), v.Y(y))], fill="#d0242b", width=2)
        string()
        for k in (0, 1):
            x = ph.knots[k] * 100
            cv.create_oval(v.X(x) - 3, v.Y(-x * tl) - 3, v.X(x) + 3, v.Y(-x * tl) + 3, fill="#b31d23", outline="")
        if ph.staple and len(pts) > 40:
            m = pts[40]
            cv.create_line(v.X(m[0] - 0.6), v.Y(m[1] + 0.6), v.X(m[0] - 0.6), v.Y(m[1]), v.X(m[0] + 0.6), v.Y(m[1]), v.X(m[0] + 0.6), v.Y(m[1] + 0.6), fill="#6d737a", width=2)
        c = self.prot_centre(pts)
        if c and self.has("prot"):
            protractor(cv, v, c[0], c[1], 7, self.protW.get() != "stp")
            string()

    def prot_centre(self, pts):
        ph, w, tl = self.ph, self.protW.get(), math.tan(self.ph.tilt)
        if w in ("k1", "k2"):
            x = ph.knots[0 if w == "k1" else 1] * 100
            return (x, -x * tl)
        if w == "stp" and len(pts) > 40:
            return pts[40]
        return None

    def draw_str(self):
        ph = self.ph
        v = View(20, 60, 10)
        self.str_scene(self.cv, v)
        if not (self.has("red") and ph.tied):
            return
        tl = math.tan(ph.tilt)
        k0 = ph.knots[0] * 100
        pts = [(k0 + x * 100, y * 100 - (k0 + x * 100) * tl) for x, y in ph.string_pts(400)]
        c = self.prot_centre([(k0 + x * 100, y * 100 - (k0 + x * 100) * tl) for x, y in ph.string_pts(40)])
        if c and self.has("prot"):
            w = self.protW.get()
            best = None
            for p in pts:
                side = p[0] > c[0] if w == "k1" else p[0] < c[0]
                if not side:
                    continue
                r = math.hypot(p[0] - c[0], p[1] - c[1])
                if best is None or abs(r - 6.6) < abs(best[0] - 6.6):
                    best = (r, p)
            if best:
                self.str_scene(self.z1, v.zoom(v.X(best[1][0]), v.Y(best[1][1]), 120, 120, 5))
        tw = self.tapeW.get()
        if tw == "bar" and self.has("tape"):
            for k, z in ([(1, self.z2)] if c else [(0, self.z1), (1, self.z2)]):
                x = ph.knots[k] * 100
                self.str_scene(z, v.zoom(v.X(x), v.Y(-x * tl - 1.4), 120, 120, 7))
        if tw == "str" and self.has("tape"):
            off, y0 = 3.1, 470
            vv = View(20, y0, 10)

            def straight(cv, vw):
                tape(cv, vw, 0, 0, 1, 0, 60)
                cv.create_line(vw.X(0.8), vw.Y(-0.35), vw.X(59), vw.Y(-0.35), fill="#d0242b", width=2)
                for x in (off, off + ph.sLen * 100):
                    cv.create_line(vw.X(x), vw.Y(-0.7), vw.X(x), vw.Y(0.1), fill="#1b2a8f", width=2)
            straight(self.cv, vv)
            self.cv.create_text(20, y0 - 18, anchor="w", text=T("실을 펴서 줄자에 대고 두 매듭 자리를 마커로 표시함", "The string straightened along the tape, the knot points marked"), font=("Helvetica", 9, "bold"))
            straight(self.z1, vv.zoom(vv.X(off), vv.Y(0.5), 120, 120, 6))
            straight(self.z2, vv.zoom(vv.X(off + ph.sLen * 100), vv.Y(0.5), 120, 120, 6))


def rr(cv, x0, y0, x1, y1, r, **kw):
    """rounded rectangle on a Tk canvas"""
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


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
        needs = dict((k, n) for k, _, n in PARTS)[key]
        miss = [n for n in needs if n not in self.placed]
        if miss:
            names = ", ".join(T(*dict((k, l) for k, l, _ in PARTS)[m]) for m in miss)
            self.msg.config(text=T("먼저 설치해야 합니다: ", "Install first: ") + names)
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
    ttk.Label(row, text=label, width=9).pack(side="left")
    for txt, fn in cmds:
        ttk.Button(row, text=txt, width=max(5, len(txt) + 1), command=fn).pack(side="left", padx=1)
    return row


class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.ph = Physics(seed)
        self.title(T(*APP_TITLE))
        self.geometry("1400x900")
        self.placed = set()
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_asm = AssemblyTab(nb, self)
        self.tab_bench = BenchTab(nb, self)
        nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.tab_bench, text=T(" 실험대 ", " Bench "))
        self.after(30, self.tick)

    def on_assembly_change(self, placed):
        self.placed = set(placed)
        self.tab_bench.refresh()

    def tick(self):
        self.tab_bench.tick(0.03)
        self.after(30, self.tick)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
