#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  Nordic-Baltic Physics Olympiad (NBPhO 2026), problem 10
  BALL MAGNET
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Apparatus after the problem sheet: a ball-shaped neodymium magnet
    (d = 10 mm, Br = 1.2 T), a flat iron disk, a wooden plate with rails,
    a holder (wooden plate with an iron pin), a titanium piece on a string
    hanging from a stand, a ruler, a measuring tape and a permanent marker.
    The ball's moment lines up perpendicular to the iron disk, along the
    local field on wood, and along the pin on the holder.  On the tilted
    rail plate the ball can only roll about the horizontal axis across the
    rails; it rolls away once m g r sin(beta) exceeds the field's largest
    restoring torque mu B_perp^2 / B.  The titanium follows the pulled
    magnet until m g tan(theta) (+ m a) exceeds
    F = 3 chi V mu0 mu^2 / (4 pi^2 r^7) on the axis (less off it).
    Iron on the bench bends the Earth's field near it.  Only scales are
    shown: the marks on the ball, a ruler at the plate, a tape under the
    pendulum.  B_E, chi and the poles are never shown.  Every hidden value
    is drawn afresh for each session.

    Run:   python3 nbpho2026_E2_ballmagnet_sim_KO.py   [--seed=N]
"""
import math
import random
import sys
import time
import tkinter as tk

LANG = "KO"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "KO" else en


def U(a, b):
    return random.uniform(a, b)


MU0, G0 = 4e-7 * math.pi, 9.81


# ── vectors and rotations (the ball's frame is kept as three column vectors) ──
def add(a, b): return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]
def sub(a, b): return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
def mul(a, k): return [a[0] * k, a[1] * k, a[2] * k]
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
def norm(a): return math.sqrt(dot(a, a))
def unit(a):
    n = norm(a) or 1.0
    return [a[0] / n, a[1] / n, a[2] / n]


def rot(v, ax, ang):
    k = unit(ax)
    c, s = math.cos(ang), math.sin(ang)
    d, x = dot(k, v), cross(k, v)
    return [v[i] * c + x[i] * s + k[i] * d * (1 - c) for i in range(3)]


def ortho(R):
    x = unit(R[0])
    z = unit(cross(x, R[1]))
    return [x, cross(z, x), z]


def apply(R, v): return [R[0][i] * v[0] + R[1][i] * v[1] + R[2][i] * v[2] for i in range(3)]
def apply_t(R, w): return [dot(R[0], w), dot(R[1], w), dot(R[2], w)]


def align(R, w):
    """turn the ball the shortest way so that its axis (column z) points along w"""
    m, w = R[2], unit(w)
    c = max(-1.0, min(1.0, dot(m, w)))
    if c > 0.999999:
        return R
    ax = cross(m, w)
    if norm(ax) < 1e-9:
        ax = cross(m, [1, 0, 0]) if abs(m[0]) < 0.9 else cross(m, [0, 1, 0])
    return ortho([rot(col, ax, math.acos(c)) for col in R])


class Truth:
    def __init__(self):
        self.Br = U(1.18, 1.22)
        self.R = 0.005
        self.rho = U(7450, 7550)
        self.m = self.rho * 4 / 3 * math.pi * self.R ** 3
        self.mu = 4 / 3 * math.pi * self.R ** 3 * self.Br / MU0
        self.BE = U(48, 53) * 1e-6
        self.dip = math.radians(U(70, 74.5))
        self.north = U(0, 2 * math.pi)
        self.chi = U(1.6e-4, 1.88e-4)
        self.rhoTi, self.dTi, self.lTi = U(4480, 4520), 0.0024, 0.0034
        self.V = math.pi * (self.dTi / 2) ** 2 * self.lTi
        self.mTi = self.rhoTi * self.V
        self.Ls = U(700, 800)          # mm, string: knot to the titanium's centre
        self.Lp = U(186, 198)          # mm, the rail plate
        self.tape0 = U(28, 72)         # mm, tape zero short of the titanium's rest
        h = math.cos(self.dip)
        self.B = [self.BE * h * math.cos(self.north), -self.BE * h * math.sin(self.north), -self.BE * math.sin(self.dip)]


class Rig:
    def __init__(self, tr):
        self.t = tr
        R = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        for _ in range(4):
            R = [rot(c, [random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1)], U(0, math.pi)) for c in R]
        self.R = ortho(R)
        self.where = "box"
        self.marks = []                       # [kind, body vector]
        self.az, self.h, self.raise_ = 0.0, 0.0, 0.0
        self.s, self.roll, self.rolled, self.f_plate = tr.Lp / 2, 0.0, False, 1.0
        self.hx, self.att, self.v, self.vset = 25.0, False, 0.0, 0.0
        self.dz, self.adj, self.grip, self.eps, self.f_pend = U(-2.2, 2.2), 0.0, "pin", 0.0, 1.0
        self.theta, self.om, self.iron_near = 0.0, 0.0, False

    # the field at the ball: the Earth's, bent when iron is close
    def field(self):
        B = list(self.t.B)
        if self.iron_near:
            n = unit([0.7, 0.2, 0.68])
            k = 0.22
            B = add(B, mul(sub(mul(n, 3 * dot(self.t.B, n)), self.t.B), k))
        return B

    def beta(self):
        return math.asin(min(0.9, self.h / self.t.Lp))

    def put(self, w):
        self.where = w
        if w == "rails":
            self.s, self.roll, self.rolled = self.t.Lp / 2, 0.0, False
            self.f_plate = max(0.96, min(1.03, random.gauss(1, 0.013)))
        if w == "pin":
            self.att, self.hx, self.theta, self.om, self.vset, self.v = False, 25.0, 0.0, 0.0, 0.0, 0.0
        self.settle(0.01)

    def settle(self, dt):
        w = self.where
        if w in ("box",):
            return
        if w == "disk":
            self.R = align(self.R, [0, 0, 1] if self.R[2][2] >= 0 else [0, 0, -1])
            return
        if w == "pin":
            self.R = align(self.R, [-1, 0, 0])
            return
        B = self.field()
        if w == "table":
            self.R = align(self.R, B)
            return
        d = [math.cos(self.az), -math.sin(self.az), 0.0]
        n = unit(cross([0, 0, 1], d))
        b = self.beta()
        if self.roll:
            self.roll = min(320.0, self.roll + 900 * math.sin(b) * dt * 9.8 / 1.4)
            s0 = self.s
            self.s = max(12.0, self.s - self.roll * dt)
            self.R = ortho([rot(c, n, -(s0 - self.s) / (self.t.R * 1000)) for c in self.R])
            if self.s <= 12:
                self.roll, self.rolled = 0.0, True
            return
        if b < 1e-4 or self.rolled:
            if not self.rolled:
                self.R = align(self.R, B)
            return
        Bn = dot(B, n)
        Bp = norm(sub(B, mul(n, Bn)))
        tmax = self.t.mu * Bp * Bp / norm(B) * self.f_plate
        tg = self.t.m * G0 * self.t.R * math.sin(b)
        if tg > tmax:
            self.roll = 1.0
            app.say(T("공이 굴러 내려갑니다!", "The ball starts rolling down!"))
            if self.raise_:
                app.after(int(U(200, 450)), self.stop_raise)
            return
        R0 = align(self.R, B)
        phi = math.asin(tg / tmax * 0.9999) * (Bp / norm(B))
        self.R = ortho([rot(c, n, -phi) for c in R0])

    def stop_raise(self):
        self.raise_ = 0.0

    def fmag(self):
        t = self.t
        r = t.R + t.dTi / 2
        e = math.atan2(abs((self.dz - self.adj) / 1000), r) + self.eps
        return 3 * t.chi * t.V * MU0 * t.mu ** 2 / (4 * math.pi ** 2 * r ** 7) * (1 + 3 * math.cos(e) ** 2) / 4 * math.cos(e) * self.f_pend

    def attach(self):
        self.att, self.theta, self.om = True, 0.0, 0.0
        self.f_pend = max(0.95, min(1.02, random.gauss(1, 0.012)))
        self.eps = U(0.25, 0.6) if self.grip == "hand" else 0.0

    def step(self, dt):
        if self.raise_:
            self.h = max(0.0, min(60.0, self.h + self.raise_ * dt))
        self.settle(dt)
        vold = self.v
        self.v = 0.0 if self.vset == 0 else self.v + (self.vset - self.v) * min(1.0, dt / 0.35)
        a = (self.v - vold) / dt / 1000
        if self.v:
            self.hx = max(0.0, min(400.0, self.hx + self.v * dt))
            if self.hx == 0 and self.v < 0 and not self.att:
                self.vset = self.v = 0.0
        if self.att:
            th = math.asin(min(0.95, self.hx / self.t.Ls))
            need = self.t.mTi * (G0 * math.tan(th) + max(0.0, a) + abs(random.gauss(0, 0.05)) * abs(self.v) / 6)
            if need > self.fmag():
                self.att, self.theta, self.om, self.vset, self.v = False, th, 0.0, 0.0, 0.0
                app.say(T("티타늄이 자석에서 떨어져 되돌아갑니다!", "The titanium came off the magnet and swings back!"))
            return
        L = self.t.Ls / 1000
        self.om += (-G0 / L * math.sin(self.theta) - 0.35 * self.om) * dt
        self.theta += self.om * dt
        if self.where == "pin" and self.hx <= 0 and abs(self.theta) < 0.004:
            self.hx, self.vset, self.v = 0.0, 0.0, 0.0
            self.attach()
            app.say(T("자석의 극이 티타늄에 닿아 붙었습니다.", "The pole touched the titanium and holds it."))


class App:
    def __init__(self, root, seed=None):
        if seed is not None:
            random.seed(seed)
        self.root = root
        self.tr = Truth()
        self.rig = Rig(self.tr)
        self.pen = "dot"
        self.view = "ball"
        self.zoom = {"plate": [None], "pend": [None]}
        root.title(T("NBPhO 2026 실험 10 — 공 자석", "NBPhO 2026 Experiment 10 — Ball Magnet"))
        self.build()
        self.last = time.time()
        self.tick()

    def build(self):
        r = self.root
        left = tk.Frame(r, bg="#1c2027")
        left.pack(side="left", fill="both", expand=True)
        bar = tk.Frame(left, bg="#1c2027")
        bar.pack(fill="x")
        for k, lab in (("ball", T("공 자석 (위에서)", "Ball (from above)")), ("plate", T("레일 판 (옆에서)", "Rail plate (side)")), ("pend", T("진자 (옆에서)", "Pendulum (side)"))):
            tk.Button(bar, text=lab, command=lambda k=k: self.set_view(k)).pack(side="left", padx=2, pady=2)
        self.cv = tk.Canvas(left, width=900, height=560, bg="#eceae4", highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Button-1>", self.click)
        self.cv.bind("<Button-3>", self.rclick)
        self.cv.bind("<MouseWheel>", self.wheel)
        self.cv.bind("<Button-4>", lambda e: self.wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self.wheel(e, -1))
        self.cv.bind("<B1-Motion>", self.drag)
        self.cv.bind("<Motion>", self.motion)
        self.mouse = (-1, -1)
        pn = tk.Frame(r, bg="#23272e", padx=6, pady=6)
        pn.pack(side="right", fill="y")

        def head(s):
            tk.Label(pn, text=s, fg="#f2c14e", bg="#23272e", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(8, 2))

        def row(*items):
            f = tk.Frame(pn, bg="#23272e")
            f.pack(fill="x")
            for lab, cmd in items:
                tk.Button(f, text=lab, command=cmd).pack(side="left", padx=1, pady=1)
        head(T("공 자석", "Ball magnet"))
        row((T("철판 위에", "On the iron disk"), lambda: self.put("disk")), (T("나무 탁자 위에", "On the table"), lambda: self.put("table")))
        row((T("레일 사이에", "Between the rails"), lambda: self.put("rails")), (T("홀더 철 핀에", "On the holder's pin"), lambda: self.put("pin")))
        row((T("뒤집어 다시 놓기", "Turn it over"), self.flip), (T("감독관에게 제출", "Hand to the invigilator"), self.check))
        row((T("마커: 점", "Marker: dot"), lambda: self.set_pen("dot")), (T("마커: ×", "Marker: cross"), lambda: self.set_pen("x")))
        self.iron = tk.BooleanVar(value=False)
        tk.Checkbutton(pn, text=T("철 물체(스탠드) 가까이에서", "Near iron (the stand)"), variable=self.iron, command=self.iron_set,
                       fg="#e8eef2", bg="#23272e", selectcolor="#333").pack(anchor="w")
        head(T("레일 판", "Rail plate"))
        row(("⟲15°", lambda: self.turn(-15)), ("⟲2°", lambda: self.turn(-2)), ("⟳2°", lambda: self.turn(2)), ("⟳15°", lambda: self.turn(15)))
        row(("−1 mm", lambda: self.lift(-1)), ("+0.2 mm", lambda: self.lift(0.2)), ("+1 mm", lambda: self.lift(1)))
        row((T("천천히 들기/멈춤", "Lift slowly / stop"), self.slow), (T("평평하게, 공 가운데로", "Flat, ball to middle"), self.flat))
        head(T("티타늄 진자", "Titanium pendulum"))
        row((T("클램프 +0.2 mm", "Clamp +0.2 mm"), lambda: self.clamp(0.2)), (T("클램프 −0.2 mm", "Clamp −0.2 mm"), lambda: self.clamp(-0.2)))
        row((T("철 핀으로 잡기", "Hold on the pin"), lambda: self.set_grip("pin")), (T("손가락으로", "In the fingers"), lambda: self.set_grip("hand")))
        row((T("아주 천천히", "Very slowly"), lambda: self.pull(2)), (T("보통", "Normal"), lambda: self.pull(6)), (T("빠르게", "Fast"), lambda: self.pull(20)))
        row((T("멈춤", "Stop"), lambda: self.pull(0)), (T("홀더 되돌리기", "Bring the holder back"), lambda: self.pull(-12)))
        self.tape_up = False
        row((T("줄자 바닥/세우기", "Tape floor / standing"), self.toggle_tape),)
        self.msg = tk.Label(pn, text="", fg="#e8eef2", bg="#23272e", wraplength=260, justify="left")
        self.msg.pack(anchor="w", pady=8)

    def say(self, s):
        self.msg.config(text=s)

    def set_view(self, k):
        self.view = k

    def put(self, w):
        self.rig.put(w)
        self.say({"disk": T("공을 철판 위에 놓았습니다.", "Ball on the iron disk."), "table": T("공을 나무 탁자 위에 놓았습니다.", "Ball on the wooden table."),
                  "rails": T("공을 레일 사이에 놓았습니다.", "Ball between the rails."), "pin": T("공을 홀더의 철 핀에 붙였습니다.", "Ball stuck on the holder's pin.")}[w])
        self.view = "pend" if w == "pin" else ("plate" if w == "rails" and self.view == "pend" else self.view)

    def flip(self):
        g = self.rig
        if g.where == "box":
            return
        g.R = ortho([rot(c, [random.gauss(0, 1), random.gauss(0, 1), 0], math.pi) for c in g.R])
        g.R = ortho([rot(c, [0, 0, 1], U(0, 6.28)) for c in g.R])
        g.rolled, g.roll, g.att = False, 0.0, False
        g.settle(0.01)
        self.say(T("공을 뒤집어 다시 놓았습니다.", "Ball turned over and put back."))

    def check(self):
        Rmm = self.tr.R * 1000

        def near(kind, pole):
            best = None
            for k, v in self.rig.marks:
                if k != kind:
                    continue
                a = math.acos(max(-1, min(1, dot(unit(v), pole)))) * Rmm
                best = a if best is None or a < best else best
            return best
        a, b = near("dot", [0, 0, 1]), near("x", [0, 0, -1])
        f = lambda x: T("없음", "none") if x is None else T("참 위치에서 %.1f mm" % x, "%.1f mm from the true point" % x)
        self.say(T("감독관 확인 — N극의 점: ", "Invigilator — dot at N: ") + f(a) + T(" · S극의 ×: ", " · cross at S: ") + f(b))

    def set_pen(self, p):
        self.pen = p

    def iron_set(self):
        self.rig.iron_near = self.iron.get()
        self.rig.settle(0.01)

    def turn(self, a):
        self.rig.az += math.radians(a)
        if self.rig.where == "rails" and self.rig.h < 0.05:
            self.rig.settle(0.01)

    def lift(self, dh):
        self.rig.raise_ = 0.0
        self.rig.h = max(0.0, min(60.0, self.rig.h + dh))

    def slow(self):
        self.rig.raise_ = 0.0 if self.rig.raise_ else 0.5

    def flat(self):
        g = self.rig
        g.raise_, g.h = 0.0, 0.0
        if g.where == "rails":
            g.put("rails")

    def clamp(self, d):
        self.rig.adj += d

    def set_grip(self, k):
        self.rig.grip = k
        if self.rig.att:
            self.rig.eps = U(0.25, 0.6) if k == "hand" else 0.0

    def pull(self, v):
        if self.rig.where != "pin":
            self.say(T("공 자석을 홀더의 철 핀에 붙인 다음에 하세요.", "Stick the ball on the holder's pin first."))
            return
        self.rig.vset = float(v)
        if v == 0:
            self.rig.v = 0.0

    def toggle_tape(self):
        self.tape_up = not self.tape_up

    # ── the 2-D views in mm, zoomable ──
    def vw(self):
        z = self.zoom[self.view]
        if z[0] is None:
            W, H = self.cv.winfo_width() or 900, self.cv.winfo_height() or 560
            z[0] = [self.tr.Lp / 2 + 20, 40, min(W / (self.tr.Lp + 140), H / 150)] if self.view == "plate" else [150, self.tr.Ls / 2 + 40, H / (self.tr.Ls + 160)]
        return z[0]

    def X(self, v, x): return (self.cv.winfo_width() or 900) / 2 + (x - v[0]) * v[2]
    def Y(self, v, y): return (self.cv.winfo_height() or 560) / 2 - (y - v[1]) * v[2]

    def wheel(self, e, sign=None):
        if self.view == "ball":
            return
        v = self.vw()
        s = sign if sign is not None else (1 if e.delta > 0 else -1)
        W, H = self.cv.winfo_width(), self.cv.winfo_height()
        mx, my = v[0] + (e.x - W / 2) / v[2], v[1] - (e.y - H / 2) / v[2]
        v[2] = max(0.05, min(80, v[2] * (1.25 if s > 0 else 0.8)))
        v[0], v[1] = mx - (e.x - W / 2) / v[2], my + (e.y - H / 2) / v[2]

    def drag(self, e):
        if self.view == "ball" or not hasattr(self, "dr"):
            return
        v = self.vw()
        v[0] = self.dr[2] - (e.x - self.dr[0]) / v[2]
        v[1] = self.dr[3] + (e.y - self.dr[1]) / v[2]

    def motion(self, e):
        self.mouse = (e.x, e.y)

    def click(self, e):
        if self.view != "ball":
            v = self.vw()
            self.dr = (e.x, e.y, v[0], v[1])
            return
        g = self.rig
        if g.where == "box":
            return
        cx, cy, R = self.ball_geom()
        dx, dy = (e.x - cx) / R, (e.y - cy) / R
        if dx * dx + dy * dy >= 1:
            return
        w = [dx, dy, math.sqrt(1 - dx * dx - dy * dy)]
        g.marks.append([self.pen, apply_t(g.R, w)])

    def rclick(self, e):
        if self.view != "ball":
            self.zoom[self.view][0] = None
            return
        cx, cy, R = self.ball_geom()
        dx, dy = (e.x - cx) / R, (e.y - cy) / R
        best, bi = 1e9, -1
        for i, (k, v) in enumerate(self.rig.marks):
            q = apply(self.rig.R, v)
            if q[2] <= 0:
                continue
            dd = math.hypot(q[0] - dx, q[1] - dy)
            if dd < best:
                best, bi = dd, i
        if bi >= 0 and best < 0.4:
            self.rig.marks.pop(bi)

    def ball_geom(self):
        W, H = self.cv.winfo_width() or 900, self.cv.winfo_height() or 560
        R = min(H * 0.36, W * 0.22)
        return W * 0.45, H * 0.5, R

    def draw(self):
        c = self.cv
        c.delete("all")
        getattr(self, "draw_" + self.view)()

    def draw_ball(self):
        c, g = self.cv, self.rig
        W, H = c.winfo_width() or 900, c.winfo_height() or 560
        if g.where == "box":
            c.create_text(W / 2, H / 2, text=T("공 자석을 어딘가에 놓으세요", "Put the ball somewhere"), fill="#69717a")
            return
        cx, cy, R = self.ball_geom()
        bg = {"disk": "#7c838a", "rails": "#d6b47e", "pin": "#2a2d33", "table": "#c7a06a"}[g.where]
        c.create_rectangle(0, 0, W, H, fill=bg, outline="")
        mm = R / 5
        if g.where == "rails":
            a = g.az
            d0, n = (math.cos(a), -math.sin(a)), (math.sin(a), math.cos(a))
            for o0, o1, col in ((-9.5, 9.5, "#3a3c40"), (9.7, 13.3, "#8a6a3e"), (-13.3, -9.7, "#8a6a3e")):
                pts = []
                for o, s in ((o0, -1), (o0, 1), (o1, 1), (o1, -1)):
                    pts += [cx + n[0] * o * mm + d0[0] * s * W, cy + n[1] * o * mm + d0[1] * s * W]
                c.create_polygon(pts, fill=col, outline="")
        if g.where == "pin":
            c.create_rectangle(cx + R * 0.85, cy - R * 0.09, W, cy + R * 0.09, fill="#8d939a", outline="")
        c.create_oval(cx - R + 6, cy - R + 8, cx + R + 6, cy + R + 8, fill="#555", outline="")
        for i in range(20, 0, -1):          # shaded sphere
            f = i / 20
            col = "#%02x%02x%02x" % (int(110 + 140 * (1 - f) ** 0.7), int(116 + 136 * (1 - f) ** 0.7), int(122 + 130 * (1 - f) ** 0.7))
            rr = R * f
            ox, oy = -0.32 * R * (1 - f), -0.36 * R * (1 - f)
            c.create_oval(cx + ox - rr, cy + oy - rr, cx + ox + rr, cy + oy + rr, fill=col, outline="")
        for k, v in g.marks:
            q = apply(g.R, v)
            if q[2] <= 0.02:
                continue
            x, y, s = cx + q[0] * R, cy + q[1] * R, 0.55 * mm
            if k == "dot":
                c.create_oval(x - s, y - s, x + s, y + s, fill="#111", outline="")
            else:
                c.create_line(x - s * 1.2, y - s * 1.2, x + s * 1.2, y + s * 1.2, fill="#1b2a8f", width=3)
                c.create_line(x - s * 1.2, y + s * 1.2, x + s * 1.2, y - s * 1.2, fill="#1b2a8f", width=3)
        c.create_rectangle(W - 120, H - 30, W - 120 + 2 * mm, H - 25, fill="#222")
        c.create_text(W - 120, H - 40, text="2 mm", anchor="w")
        c.create_text(12, 14, anchor="w", text=T("마커: ", "Marker: ") + ("●" if self.pen == "dot" else "×") + T("   좌클릭 그리기 · 우클릭 지우기", "   L-click draw · R-click erase"), fill="#eee")

    def scale(self, v, a, d, length, col):
        c = self.cv
        n = (-d[1], d[0])
        Wd = 24
        P = lambda s, w: (a[0] + d[0] * s + n[0] * w, a[1] + d[1] * s + n[1] * w)
        pts = []
        for s, w in ((-6, 0), (length + 6, 0), (length + 6, Wd), (-6, Wd)):
            p = P(s, w)
            pts += [self.X(v, p[0]), self.Y(v, p[1])]
        c.create_polygon(pts, fill=col, outline="#789")
        step = 1 if v[2] > 3 else 5 if v[2] > 0.7 else 10
        for mm in range(0, int(length) + 1, step):
            Lm = Wd * (0.55 if mm % 10 == 0 else 0.38 if mm % 5 == 0 else 0.22)
            p0, p1 = P(mm, 0), P(mm, Lm)
            c.create_line(self.X(v, p0[0]), self.Y(v, p0[1]), self.X(v, p1[0]), self.Y(v, p1[1]), fill="#1b1d20")
            if mm % 10 == 0 and v[2] * 10 > 14:
                q = P(mm, Wd * 0.8)
                c.create_text(self.X(v, q[0]), self.Y(v, q[1]), text=str(mm // 10), font=("TkDefaultFont", 8, "bold"))

    def draw_plate(self):
        c, g, v = self.cv, self.rig, self.vw()
        W, H = c.winfo_width() or 900, c.winfo_height() or 560
        c.create_rectangle(0, self.Y(v, 0), W, H, fill="#d9c7a6", outline="")
        Lp, b = self.tr.Lp, g.beta()
        u, n = (math.cos(b), math.sin(b)), (-math.sin(b), math.cos(b))
        P = lambda s, w: (u[0] * s + n[0] * w, u[1] * s + n[1] * w)
        poly = lambda pts, col: c.create_polygon(sum(([self.X(v, p[0]), self.Y(v, p[1])] for p in pts), []), fill=col, outline="#5d4526")
        e = P(Lp, 0)
        if g.h > 0.3:
            poly([(e[0] - 2, 0), (e[0] + 22, 0), (e[0] + 22, e[1]), (e[0] - 2, e[1])], "#6f7b86")
        poly([P(0, 0), P(Lp, 0), P(Lp, 9), P(0, 9)], "#c9a46c")
        for s in (0, Lp - 5):
            poly([P(s, 9), P(s + 5, 9), P(s + 5, 21), P(s, 21)], "#8a6a3e")
        if g.where == "rails":
            ctr = P(g.s, 14)
            r = 5 * v[2]
            X, Y = self.X(v, ctr[0]), self.Y(v, ctr[1])
            c.create_oval(X - r, Y - r, X + r, Y + r, fill="#c9cdd2", outline="#555")
        self.scale(v, (e[0] + 26, 0), (0, 1), 300, "#d6e4ec")
        my = self.mouse[1]
        c.create_line(0, my, W, my, fill="#c0392b", dash=(3, 3))

    def draw_pend(self):
        c, g, v = self.cv, self.rig, self.vw()
        W, H = c.winfo_width() or 900, c.winfo_height() or 560
        c.create_rectangle(0, self.Y(v, 0), W, H, fill="#d9c7a6", outline="")
        L = self.tr.Ls
        kx, kz = 0.0, 24 + L
        th = math.asin(min(0.95, g.hx / L)) if g.att else g.theta
        tx, tz = kx + L * math.sin(th), kz - L * math.cos(th)
        sx = -280
        line = lambda a, b, col, w=1: c.create_line(self.X(v, a[0]), self.Y(v, a[1]), self.X(v, b[0]), self.Y(v, b[1]), fill=col, width=w)
        rect = lambda x0, y0, x1, y1, col: c.create_rectangle(self.X(v, x0), self.Y(v, y1), self.X(v, x1), self.Y(v, y0), fill=col, outline="#555")
        rect(sx - 90, 0, sx + 90, 16, "#3d4248")
        rect(sx - 6, 16, sx + 6, kz + 60, "#b8bdc3")
        rect(sx, kz - 4.5, kx + 6, kz + 4.5, "#b8bdc3")
        line((kx, kz), (tx, tz + 1.7), "#666")
        rect(tx - 1.2, tz - 1.7, tx + 1.2, tz + 1.7, "#a9adb3")
        if g.where == "pin":
            gap = (self.tr.R + self.tr.dTi / 2) * 1000
            bx = gap + g.hx
            bz = (tz if g.att else 24) - (g.dz - g.adj)
            rect(bx + 4.5, bz - 1.3, bx + 66, bz + 1.3, "#8d939a")
            r = 5 * v[2]
            X, Y = self.X(v, bx), self.Y(v, bz)
            c.create_oval(X - r, Y - r, X + r, Y + r, fill="#c9cdd2", outline="#555")
        if self.tape_up:
            self.scale(v, (-14, 0), (0, 1), 1000, "#f2d13a")
        else:
            self.scale(v, (-self.tr.tape0, -1), (1, 0), 600, "#f2d13a")
        mx, my = self.mouse
        c.create_line(mx, 0, mx, H, fill="#c0392b", dash=(3, 3))
        c.create_line(0, my, W, my, fill="#c0392b", dash=(3, 3))

    def tick(self):
        now = time.time()
        dt = min(0.05, now - self.last)
        self.last = now
        n = max(1, int(dt / 0.01))
        for _ in range(n):
            self.rig.step(dt / n)
        self.draw()
        self.root.after(33, self.tick)


def main():
    global app
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
    root = tk.Tk()
    root.geometry("1280x720")
    app = App(root, seed)
    root.mainloop()


if __name__ == "__main__":
    main()
