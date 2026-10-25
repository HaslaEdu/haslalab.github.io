#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  Nordic-Baltic Physics Olympiad 2022  (NBPhO 2022)
  Problem 5 (experimental) :  FERROMAGNETIC STRIPE
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The sensor reads the field along its white dot,
  V(mV) = (E / 3 V) * B.n / (10 uT) + V0, with an offset V0 that a
  reading over about 500 mV can upset.  Earth's field (about 51 uT,
  dipping some 73 degrees) is always there.
* The magnet is a dipole standing on the stripe, north face down.  The
  stripe is saturated (B = mu0 Js) over its first xs next to it; further
  on the flux leaks through the top and bottom faces,
  Phi(x) = Phi_s sinh((L' - x + xs)/lambda)/sinh(L'/lambda),
  Bz(x, y) = -Phi'(x)/(2 w kappa) g(y), g(0) = 1, kappa = <g>.
  The magnet's flux beyond what the stripe can carry comes back through
  the air close to it.  With the magnet at the centre, both halves are
  saturated alike.
* The stripe can be slid away from under the magnet to measure the
  magnet alone.  Positions are read from the ruler and the graph paper.
  Nothing is computed for you.
* Hidden truths (E, V0, Earth's field and its direction, the magnet's
  moment, mu0 Js, the stripe's profiles) are randomised every session.
* Standard library only (tkinter).

    Run:   python3 nbpho2022_E1_stripe_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the EN edition differs only in this line

MU0 = 4e-7 * math.pi
RANGES = [("off", "OFF", None), ("v20", "20 V", 20.0), ("v2", "2000 mV", 2.0), ("m200", "200 mV", 0.2)]
RMAX = dict((k, c) for k, _, c in RANGES)


def T(ko, en):
    return ko if LANG == "ko" else en


# --------------------------------------------------------------------------
#  Physics core  (SI)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = self.r = random.Random(seed)
        self.E, self.V0 = r.uniform(3.05, 3.19), r.uniform(-2.0, 1.0)
        self.BE, self.inc, self.az = r.uniform(49, 53) * 1e-6, math.radians(r.uniform(70, 76)), r.uniform(-0.8, 0.8)
        self.m, self.hm, self.dm = r.uniform(0.95, 1.2), 0.010, 0.012
        self.Js = r.uniform(2.0, 2.4)
        self.t, self.w, self.L, self.x0 = 0.25e-3, 0.030, 0.70, 0.010
        self.xs, self.l1, self.lam, self.dL, self.exr = r.uniform(0.012, 0.018), r.uniform(0.010, 0.014), r.uniform(0.25, 0.31), r.uniform(0.015, 0.03), r.uniform(1.5, 2.5)
        self.gc, self.gb, self.hs = r.uniform(0.6, 0.9), r.uniform(-0.12, 0.12), 0.0012
        self.kap = 1 + self.gc / 3
        self.rz = r.uniform(0.3, 0.8)          # the ruler's zero before the stripe's end, cm
        # the bench
        self.mag, self.away = "off", False
        self.at, self.sx, self.sy, self.dir, self.phi = "far", 0.30, 0.0, "up", 0.0
        self.burnt = False

    def mag_x(self):
        return self.L / 2 if self.mag == "centre" else self.x0

    def phis(self):
        return self.Js * self.w * self.t

    def phi_side(self, s, Ls):
        Lp, u = Ls - self.xs + self.dL, max(0.0, s - self.xs)
        return self.phis() * math.sinh((Lp - u) / self.lam) / math.sinh(Lp / self.lam)

    def leak_side(self, s, Ls):
        if s < self.xs:
            return 0.0
        Lp, u = Ls - self.xs + self.dL, s - self.xs
        dphi = self.phis() * math.cosh((Lp - u) / self.lam) / (self.lam * math.sinh(Lp / self.lam))
        end = self.phi_side(Ls, Ls) * 0.6 / 0.015 * math.exp(-(Ls - s) / 0.015)
        return (dphi + end) / (2 * self.w * self.kap)

    def bz_side(self, s, Ls):
        return self.leak_side(s, Ls) + self.exr * self.leak_side(0.03, Ls) * math.exp((0.03 - s) / self.l1)

    def stripe_bz(self, x, y):
        if self.mag == "off" or self.away or abs(y) > self.w / 2 + 0.002 or x < -0.002 or x > self.L + 0.002:
            return 0.0
        xm = self.mag_x()
        s = abs(x - xm)
        Ls = self.L - xm if x >= xm else xm
        if s < self.dm / 2:
            return 0.0
        u = max(-1.0, min(1.0, 2 * y / self.w))
        return self.bz_side(s, Ls) * (1 + self.gb * u + self.gc * u * u)

    def mag_b(self, p):
        if self.mag == "off":
            return [0.0, 0.0, 0.0]
        c = [self.mag_x(), 0.0, self.hm / 2 + self.t]
        rv = [p[i] - c[i] for i in range(3)]
        R = math.sqrt(sum(v * v for v in rv))
        if R < self.dm / 2:
            return [0.0, 0.0, 0.4]
        mv = [0.0, 0.0, -self.m]
        k = MU0 / (4 * math.pi)
        md = sum(mv[i] * rv[i] for i in range(3))
        return [k * (3 * md * rv[i] / R ** 5 - mv[i] / R ** 3) for i in range(3)]

    def earth(self):
        h, v = self.BE * math.cos(self.inc), -self.BE * math.sin(self.inc)
        return [h * math.cos(self.az), h * math.sin(self.az), v]

    def along(self):
        n = [0, 0, 1] if self.dir == "up" else [0, 0, -1] if self.dir == "down" else [math.cos(self.phi), math.sin(self.phi), 0]
        B = self.earth()
        if self.at == "stripe":
            p = [self.sx, self.sy, self.t + self.hs]
            bm = self.mag_b(p)
            B = [B[0] + bm[0], B[1] + bm[1], B[2] + bm[2] + self.stripe_bz(self.sx, self.sy)]
        return sum(B[i] * n[i] for i in range(3))

    def sensor_mv(self):
        v = self.E / 3 * self.along() / 10e-6
        if abs(v) > 520 and not self.burnt:
            self.V0 += self.r.uniform(0.6, 3) * self.r.choice((-1, 1))
            self.burnt = True
        if abs(v) < 300:
            self.burnt = False
        return v + self.V0


def show(rng, v):
    if v is None or rng == "off":
        return ""
    R = RMAX[rng]
    if abs(v) >= R * 0.99995:
        return "-1" if v < 0 else "1"
    s = "%.2f" % abs(v) if rng == "v20" else "%.0f" % abs(v * 1000) if rng == "v2" else "%.1f" % abs(v * 1000)
    return ("-" if v < 0 and float(s) != 0 else "") + s


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_paper(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 46 * s, y - 32 * s, x + 46 * s, y + 32 * s, fill="#fbfaf2", outline="#c9a07c")
    for i in range(-40, 41, 8):
        cv.create_line(x + i * s, y - 30 * s, x + i * s, y + 30 * s, fill="#e8b89a")


def art_stripe(cv, x, y, sc=1.0):
    cv.create_rectangle(x - 60 * sc, y - 5 * sc, x + 60 * sc, y + 5 * sc, fill="#a3aab1", outline="#5f666c")


def art_magnet(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 14 * s, y - 8 * s, x + 14 * s, y + 10 * s, fill="#b8bdc3", outline="")
    cv.create_oval(x - 14 * s, y - 14 * s, x + 14 * s, y - 2 * s, fill="#d0d4d8", outline="#888")


def art_sensor(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 22 * s, y - 14 * s, x + 22 * s, y + 14 * s, fill="#2f7d4a", outline="#1d5a31")
    cv.create_rectangle(x - 6 * s, y - 6 * s, x + 6 * s, y + 6 * s, fill="#1b1d20", outline="")
    cv.create_oval(x + 14 * s, y - 10 * s, x + 18 * s, y - 6 * s, fill="#fff", outline="")


def art_batt(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 36 * s, y - 20 * s, x + 36 * s, y + 20 * s, fill="#1b1d20", outline="")
    cv.create_rectangle(x - 32 * s, y - 16 * s, x + 32 * s, y - 2 * s, fill="#c0392b", outline="")
    cv.create_rectangle(x - 32 * s, y + 2 * s, x + 32 * s, y + 16 * s, fill="#2b6cd8", outline="")


def art_dmm(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 26 * s, y - 45 * s, x + 26 * s, y + 45 * s, fill="#e3b72d", outline="#5a3a12")
    cv.create_rectangle(x - 18 * s, y - 36 * s, x + 18 * s, y - 18 * s, fill="#9fae8f", outline="")
    cv.create_oval(x - 12 * s, y - 6 * s, x + 12 * s, y + 18 * s, fill="#1b1d20", outline="")


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


ART = {"paper": art_paper, "stripe": art_stripe, "magnet": art_magnet, "sensor": art_sensor, "batt": art_batt,
       "dmm": art_dmm, "ruler": art_ruler, "caliper": art_caliper}
PARTS = [
    ("paper",   ("모눈종이", "Graph paper"), []),
    ("stripe",  ("연자성 띠 (0.25 mm)", "Soft ferromagnetic stripe (0.25 mm)"), []),
    ("magnet",  ("자석", "Magnet"), []),
    ("sensor",  ("자기장 센서", "Magnetic field sensor"), []),
    ("batt",    ("건전지 홀더 (AA 2개)", "Battery holder (2 × AA)"), []),
    ("dmm",     ("멀티미터 + 집게 도선", "Multimeter + clip wires"), []),
    ("ruler",   ("자", "Ruler"), []),
    ("caliper", ("캘리퍼", "Caliper"), []),
]
ZONES = {
    "paper":   (380, 140, 110, 80),
    "stripe":  (380, 260, 140, 30),
    "magnet":  (150, 140, 50, 50),
    "sensor":  (600, 140, 60, 50),
    "batt":    (600, 260, 90, 60),
    "dmm":     (150, 300, 70, 110),
    "ruler":   (380, 380, 120, 30),
    "caliper": (600, 400, 130, 60),
}
SCENE_TITLE = ("실험대 — 모눈종이, 띠, 자석, 센서, 건전지, 멀티미터, 자, 캘리퍼", "The bench — paper, stripe, magnet, sensor, batteries, multimeter, ruler, caliper")
APP_TITLE = ("NBPhO 2022 실험 (문제 5) — 강자성 띠", "NBPhO 2022 Experiment (Problem 5) — Ferromagnetic stripe")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.rng = tk.StringVar(value="off")
        self.clips = tk.StringVar(value="none")
        self.disp, self.disp_t = None, 0.0
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
        f = ttk.LabelFrame(ctl, text=T("멀티미터", "Multimeter"))
        f.pack(fill="x", pady=2)
        self.dM = tk.Label(f, text="", font=("Courier", 18, "bold"), bg="#9fae8f", fg="#1b1d20", width=14)
        self.dM.pack(pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for k, lb, _ in RANGES:
            ttk.Radiobutton(row, text=lb, value=k, variable=self.rng, command=self.changed).pack(side="left")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("집게", "Clips")).pack(side="left")
        for k, lb in (("none", T("빼 둠", "off")), ("batt", T("건전지 단자", "battery tabs")), ("sensor", T("센서 노랑·빨강", "sensor yellow·red"))):
            ttk.Radiobutton(row, text=lb, value=k, variable=self.clips, command=self.clip_changed).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("센서", "Sensor"))
        f.pack(fill="x", pady=2)
        self.at = tk.StringVar(value="far")
        row = ttk.Frame(f)
        row.pack(fill="x")
        for k, lb in (("far", T("방 안 (멀리)", "in the room (far)")), ("stripe", T("띠 위", "on the stripe"))):
            ttk.Radiobutton(row, text=lb, value=k, variable=self.at, command=self.at_changed).pack(side="left")
        stepper(f, "x", [(t, (lambda d: lambda: self.move(d, 0))(v)) for t, v in (("−10cm", -0.1), ("−1cm", -0.01), ("−1mm", -0.001), ("+1mm", 0.001), ("+1cm", 0.01), ("+10cm", 0.1))])
        stepper(f, "y", [(t, (lambda d: lambda: self.move(0, d))(v)) for t, v in (("−5mm", -0.005), ("−1mm", -0.001), ("+1mm", 0.001), ("+5mm", 0.005))])
        self.dirv = tk.StringVar(value="up")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("흰 점", "White dot"), width=8).pack(side="left")
        for k, lb in (("up", T("위로", "up")), ("down", T("아래로", "down")), ("hor", T("수평", "horizontal"))):
            ttk.Radiobutton(row, text=lb, value=k, variable=self.dirv, command=self.dir_changed).pack(side="left")
        stepper(f, T("수평 회전", "Turn"), [(t, (lambda d: lambda: self.turn(d))(v)) for t, v in (("↺15°", -15), ("↺5°", -5), ("↻5°", 5), ("↻15°", 15))])
        f = ttk.LabelFrame(ctl, text=T("자석과 띠", "Magnet and stripe"))
        f.pack(fill="x", pady=2)
        self.magv = tk.StringVar(value="off")
        row = ttk.Frame(f)
        row.pack(fill="x")
        for k, lb in (("end", T("띠 끝에", "at the end")), ("centre", T("띠 가운데에", "at the centre")), ("off", T("떼어 놓기", "taken off"))):
            ttk.Radiobutton(row, text=lb, value=k, variable=self.magv, command=self.mag_changed).pack(side="left")
        self.bAway = ttk.Button(f, text="", command=self.slide)
        self.bAway.pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("메모", "Memo")).pack(side="left")
        self.cent = ttk.Entry(row, width=20)
        self.cent.pack(side="left", padx=2)
        ttk.Button(row, text=T("지금 값 적기", "Record now"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("c", T("메모 (위치 등)", "memo (position, …)"), 200), ("a", "DMM", 100)], height=7)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.lmsg = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=360)
        self.lmsg.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("띠를 위에서 (자: cm, 모눈: 1 mm, 노란 십자: 센서가 재는 점)", "The stripe from above (ruler: cm, grid: 1 mm, yellow cross: the point measured)"),
                  font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=820, height=640, bg="#d6d3c8", highlightthickness=0)
        self.cv.pack()

    # ---- the hands
    def changed(self):
        if not self.need("dmm"):
            self.rng.set("off")
        self.disp_t = 0

    def clip_changed(self):
        w = self.clips.get()
        if w != "none" and not self.need("dmm", "batt"):
            self.clips.set("none")
        elif w == "sensor" and not self.need("sensor"):
            self.clips.set("none")
        self.disp_t = 0

    def at_changed(self):
        w = self.at.get()
        if not self.need("sensor") or (w == "stripe" and not self.need("stripe")):
            self.at.set(self.ph.at)
            return
        if w == "stripe" and self.ph.dir == "hor":
            self.ph.dir = "up"
            self.dirv.set("up")
        self.ph.at = w
        self.disp_t = 0
        self.refresh()

    def move(self, dx, dy):
        ph = self.ph
        if ph.at != "stripe":
            self.say(T("먼저 센서를 띠 위에 얹으시오.", "Put the sensor on the stripe first."))
            return
        x, y = round(ph.sx + dx, 4), round(ph.sy + dy, 4)
        if x < 0.005 or x > ph.L - 0.005 or abs(y) > 0.0165:
            self.say(T("센서가 띠를 벗어납니다.", "The sensor would leave the stripe."))
            return
        if ph.mag != "off" and math.hypot(x - ph.mag_x(), y) < ph.dm / 2 + 0.004:
            self.say(T("그 자리에는 자석이 있습니다.", "The magnet is there."))
            return
        ph.sx, ph.sy = x, y
        self.disp_t = 0
        self.refresh()

    def dir_changed(self):
        if self.dirv.get() == "hor" and self.ph.at == "stripe":
            self.say(T("띠 위에서는 센서를 눕혀 세울 수 없습니다 — 방 안에서 하시오.", "The sensor cannot stand on edge on the stripe — do it in the room."))
            self.dirv.set(self.ph.dir)
            return
        self.ph.dir = self.dirv.get()
        self.disp_t = 0

    def turn(self, d):
        if self.ph.dir != "hor":
            self.say(T("먼저 센서를 수평으로 두시오.", "Lay the sensor horizontal first."))
            return
        self.ph.phi = (self.ph.phi + math.radians(d)) % (2 * math.pi)
        self.disp_t = 0

    def mag_changed(self):
        ph, w = self.ph, self.magv.get()
        if not self.need("magnet") or (w != "off" and not self.need("stripe")):
            self.magv.set(ph.mag)
            return
        xm = ph.L / 2 if w == "centre" else ph.x0
        if w != "off" and ph.at == "stripe" and math.hypot(ph.sx - xm, ph.sy) < ph.dm / 2 + 0.004:
            self.say(T("그 자리에는 센서가 있습니다.", "The sensor is there."))
            self.magv.set(ph.mag)
            return
        ph.mag = w
        if w == "off":
            ph.away = False
        self.disp_t = 0
        self.refresh()

    def slide(self):
        ph = self.ph
        if not self.need("stripe"):
            return
        if ph.mag == "off" and not ph.away:
            self.say(T("자석이 띠에 붙어 있지 않습니다.", "The magnet is not on the stripe."))
            return
        ph.away = not ph.away
        self.disp_t = 0
        self.refresh()

    def raw(self):
        if not self.has("dmm") or self.rng.get() == "off":
            return None
        c = self.clips.get()
        if c == "batt" and self.has("batt"):
            return self.ph.E
        if c == "sensor" and self.has("sensor") and self.has("batt"):
            return self.ph.sensor_mv() / 1000
        return 0.0

    def text_of(self):
        s = show(self.rng.get(), self.disp)
        if not s:
            return "—"
        return s + (" (OL)" if s in ("1", "-1") else " " + ("V" if self.rng.get() == "v20" else "mV"))

    def record(self):
        self.sheet.add((self.cent.get() or "—", self.text_of()))
        self.cent.delete(0, "end")

    def tick(self, dt):
        self.disp_t -= dt
        if self.disp_t <= 0:
            self.disp_t = 0.4
            r = self.raw()
            self.disp = None if r is None else r + (random.gauss(0, 0.04e-3) if self.rng.get() == "m200" else 0.0)
            self.dM.config(text=self.text_of() if self.disp is not None else "")

    def refresh(self):
        self.bAway.config(text=T("띠 되돌려 넣기", "Slide the stripe back") if self.ph.away else T("자석은 두고 띠만 빼기", "Slide the stripe out, magnet stays"))
        self.draw()

    def draw(self):
        cv, ph = self.cv, self.ph
        cv.delete("all")
        W, H = 820, 640
        if not self.has("stripe"):
            cv.create_text(W / 2, H / 2, text=T("띠를 놓으시오", "Place the stripe"), fill="#69717a")
            return
        cxm = ph.sx * 1000 if ph.at == "stripe" else (60 if ph.mag == "off" else ph.mag_x() * 1000)
        s1 = 6.0
        cy = H * 0.42
        X = lambda u: W / 2 + (u - cxm) * s1
        Y = lambda v: cy - v * s1
        if self.has("paper"):
            cv.create_rectangle(0, 0, W, H * 0.86, fill="#fbfaf2", outline="")
            u = int(math.floor(cxm - W / 2 / s1))
            while u <= cxm + W / 2 / s1:
                cv.create_line(X(u), 0, X(u), H * 0.86, fill="#d6783c" if u % 10 == 0 else "#ebb995" if u % 5 == 0 else "#f6dcc8")
                u += 1
            for v in range(-60, 61):
                y = Y(v + 0.5)
                if 0 <= y <= H * 0.86:
                    cv.create_line(0, y, W, y, fill="#d6783c" if v % 10 == 0 else "#ebb995" if v % 5 == 0 else "#f6dcc8")
        yS = -90 if ph.away else 0
        ws = ph.w * 1000
        cv.create_rectangle(X(0), Y(yS + ws / 2), X(ph.L * 1000), Y(yS - ws / 2), fill="#9aa1a8", outline="#5f666c")
        if self.has("ruler"):
            y0 = Y(-ws / 2 - 0.3)
            cv.create_rectangle(X(-ph.rz * 10 - 5), y0, X(ph.L * 1000 + 15), y0 + 22 * s1 / 2.4, fill="#d6e8f4", outline="#6b8ba3")
            for mm in range(0, 721):
                x = X(mm - ph.rz * 10)
                if -5 <= x <= W + 5:
                    Lt = 9 if mm % 10 == 0 else 6 if mm % 5 == 0 else 3.5
                    cv.create_line(x, y0, x, y0 + Lt * s1 / 2.4, fill="#1d3c55")
                    if mm % 10 == 0:
                        cv.create_text(x, y0 + 15 * s1 / 2.4, text=str(mm // 10), fill="#1d3c55", font=("Helvetica", 11, "bold"))
        if ph.mag != "off":
            mx = ph.mag_x() * 1000
            r = ph.dm * 500 * s1
            cv.create_oval(X(mx) - r, Y(0) - r, X(mx) + r, Y(0) + r, fill="#c9cdd2", outline="#5f666c", width=2)
            cv.create_text(X(mx), Y(0), text="S", font=("Helvetica", 14, "bold"), fill="#3a3f45")
        if ph.at == "stripe" and self.has("sensor"):
            sx, sy = X(ph.sx * 1000), Y(ph.sy * 1000)
            cv.create_rectangle(sx - 4 * s1, sy - 2.6 * s1, sx + 6 * s1, sy + 4.4 * s1, fill="#2f7d4a", outline="#1d5a31")
            cv.create_rectangle(sx - 1.2 * s1, sy - 1.2 * s1, sx + 1.2 * s1, sy + 1.2 * s1, fill="#1b1d20", outline="")
            if ph.dir == "up":
                cv.create_oval(sx + 3.7 * s1, sy - 2.2 * s1, sx + 4.9 * s1, sy - 1.0 * s1, fill="#fff", outline="")
            cv.create_line(sx - 1.6 * s1, sy, sx + 1.6 * s1, sy, fill="#ffcf3a", width=2)
            cv.create_line(sx, sy - 1.6 * s1, sx, sy + 1.6 * s1, fill="#ffcf3a", width=2)
        else:
            cv.create_text(W / 2, 20, text=T("센서는 방 안 멀리 있습니다", "The sensor is far away in the room"), font=("Helvetica", 11, "bold"))
        if ph.away:
            cv.create_text(W / 2, H * 0.9, text=T("띠를 빼냈습니다 — 자석과 센서는 제자리", "Stripe slid out — the magnet and the sensor stay"), fill="#7a2a22", font=("Helvetica", 11, "bold"))
        cv.create_text(10, H - 10, anchor="w", fill="#555", text=T("센서: %s, %s · 1 mV ≈ 10 µT × (3 V / E)", "Sensor: %s, %s · 1 mV ≈ 10 µT × (3 V / E)") % (
            dict(up=T("점 위로", "dot up"), down=T("점 아래로", "dot down"), hor=T("수평 %d°", "horizontal %d°") % round(math.degrees(ph.phi)))[ph.dir],
            T("방 안", "in the room") if ph.at == "far" else T("띠 위", "on the stripe")))


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
