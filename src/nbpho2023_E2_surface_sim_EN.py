#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  Nordic-Baltic Physics Olympiad 2023  (NBPhO 2023)
  Problem 9 (experimental) :  SURFACE TENSION
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* A small drop on the glass is a spherical cap meeting the glass at the
  contact angle alpha: a plano-convex lens, f = R/(n - 1).  It forms an
  image of the ceiling lights (about 2.8 m up) on the screen beneath the
  plate, through the plate's glass; the image is sharp at one height of
  the top nut and blurred, in proportion to the drop's diameter, off it.
* The holder: a pipe, a nut that moves over its own thickness, spare
  nuts to stack, a cap that brings the screen up to the pipe's top.
* A large pool is flat on top, t = sqrt(2 sigma (1 - cos alpha)/(rho g)),
  with a slightly thinner rim; spread over the whole glossy part it can
  only grow deeper.  Its outline is drawn on the graph paper.
* The syringe reads 0.1 ml; the caliper is digital (0.01 mm).
  Nothing is computed for you.
* Hidden truths (sigma, alpha, the plate's thickness, the pipe and
  nuts, the cap, the lights' height, each drop's volume) are randomised
  every session.
* Standard library only (tkinter).

    Run:   python3 nbpho2023_E2_surface_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the EN edition differs only in this line

GW, GH, MATTE = 38.0, 38.0, 12.0            # the glossy square and the frosted strip, mm
TUBES = [(-300.0, -260.0, 1200.0, 32.0), (-300.0, 340.0, 1200.0, 32.0)]   # the ceiling's two tubes (x, y, length, width), mm


def T(ko, en):
    return ko if LANG == "ko" else en


# --------------------------------------------------------------------------
#  Physics core  (mm, ml)
# --------------------------------------------------------------------------
def cap_v(a, al):
    R = a / math.sin(al)
    h = R * (1 - math.cos(al))
    return math.pi * h * (3 * a * a + h * h) / 6


class Physics(object):
    def __init__(self, seed=None):
        r = self.r = random.Random(seed)
        self.sigma = r.uniform(0.066, 0.075)
        self.alpha = math.radians(r.uniform(28, 38))
        self.nw, self.rho, self.g = 1.33, 998.0, 9.82
        self.tg, self.ng = r.uniform(1.0, 1.2), 1.52
        self.Hp, self.tn, self.capOff = r.uniform(19.6, 20.4), r.uniform(4.9, 5.1), r.uniform(-0.3, 0.3)
        self.u = r.uniform(2650, 2950)
        self.rim = r.uniform(0.25, 0.4)
        self.cal0 = r.uniform(-0.02, 0.02)
        self.t = math.sqrt(2 * self.sigma * (1 - math.cos(self.alpha)) / (self.rho * self.g)) * 1000
        self.k = [r.uniform(0.02, 0.05), r.uniform(0.02, 0.04)]
        self.ph = [r.uniform(0, 6), r.uniform(0, 6)]
        self.c = [r.uniform(-1.5, 1.5), r.uniform(-1.5, 1.5)]
        self.po = [round(r.uniform(-3, 3)) + r.uniform(0.2, 0.8), round(r.uniform(-3, 3)) + r.uniform(0.2, 0.8)]
        # the bench
        self.p, self.nk, self.cap = 2.5, 0, False
        self.plate_at = "table"
        self.syr, self.water = 0.0, 0.0
        self._pool = (-1, None)

    def is_drop(self):
        return 0 < self.water < 0.05

    def lens(self):
        if not self.is_drop():
            return None
        V = self.water * 1000
        lo, hi = 0.1, 20.0
        for _ in range(60):
            m = (lo + hi) / 2
            if cap_v(m, self.alpha) < V:
                lo = m
            else:
                hi = m
        a = (lo + hi) / 2
        R = a / math.sin(self.alpha)
        return a, R, R / (self.nw - 1)

    def shape(self, r):
        gx, gy = GW / 2 - 0.2, GH / 2 - 0.2
        pts, touch = [], 0
        for i in range(180):
            th = i / 180.0 * 2 * math.pi
            rr = r * (1 + self.k[0] * math.sin(3 * th + self.ph[0]) + self.k[1] * math.sin(5 * th + self.ph[1]))
            x, y = self.c[0] + rr * math.cos(th), self.c[1] + rr * math.sin(th)
            cx, cy = max(-gx, min(gx, x)), max(-gy, min(gy, y))
            if cx != x or cy != y:
                touch += 1
            pts.append((cx, cy))
        A = P = 0.0
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            A += p[0] * q[1] - q[0] * p[1]
            P += math.hypot(q[0] - p[0], q[1] - p[1])
        return pts, abs(A) / 2, P, touch / 180.0

    def pool(self):
        """the pool's outline, area and depth (None while the water is a drop)"""
        if self.water < 0.05:
            return None
        if self._pool[0] == self.water:
            return self._pool[1]
        V = self.water * 1000
        lo, hi = 1.0, 60.0
        for _ in range(50):
            m = (lo + hi) / 2
            pts, A, P, tc = self.shape(m)
            if A * self.t - P * self.rim < V:
                lo = m
            else:
                hi = m
        pts, A, P, tc = self.shape(lo)
        depth, full = self.t, False
        if tc > 0.97:
            depth, full = V / A, True
        res = (pts, A, depth, full)
        self._pool = (self.water, res)
        return res

    def seat(self):
        return self.Hp + self.p + self.nk * self.tn

    def gap(self):
        return self.p + self.nk * self.tn - self.capOff if self.cap else self.seat()

    def image(self):
        L = self.lens()
        if not L or self.plate_at != "holder":
            return None
        a, R, f = L
        v = 1 / (1 / f - 1 / self.u)
        sharp = v - self.tg / self.ng
        D = self.gap()
        blur = max(0.03, 2 * a * abs(D - sharp) / v)
        return f, v, sharp, D, blur, (D + self.tg / self.ng) / self.u

    def caliper(self, k):
        L = self.lens()
        v = {"plate": self.tg, "pipe": self.Hp, "nut": self.tn, "seat": self.seat(), "above": self.p + self.nk * self.tn,
             "drop": (2 * L[0] + self.r.uniform(-0.12, 0.12)) if L else None}[k]
        return None if v is None else round(v + self.cal0, 2)


def mix(c1, c2, k):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_paper(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 30 * s, y - 40 * s, x + 30 * s, y + 40 * s, fill="#fbfaf2", outline="#c9a07c")
    for i in range(-24, 25, 8):
        cv.create_line(x + i * s, y - 38 * s, x + i * s, y + 38 * s, fill="#e8b89a")
        cv.create_line(x - 28 * s, y + i * s, x + 28 * s, y + i * s, fill="#e8b89a")


def art_holder(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 16 * s, y - 6 * s, x + 16 * s, y + 30 * s, fill="#eef0f2", outline="#8a9096")
    cv.create_polygon(x - 26 * s, y - 6 * s, x + 26 * s, y - 6 * s, x + 30 * s, y - 14 * s, x + 26 * s, y - 22 * s, x - 26 * s, y - 22 * s, x - 30 * s, y - 14 * s, fill="#aeb4ba", outline="#666")


def art_plate(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 22 * s, y - 30 * s, x + 22 * s, y + 30 * s, fill="#d4e8f0", outline="#6b8ba3")
    cv.create_rectangle(x - 22 * s, y + 16 * s, x + 22 * s, y + 30 * s, fill="#eceff1", outline="#6b8ba3")


def art_cup(cv, x, y, sc=1.0):
    s = sc
    cv.create_polygon(x - 26 * s, y - 30 * s, x + 26 * s, y - 30 * s, x + 20 * s, y + 30 * s, x - 20 * s, y + 30 * s, fill="#eef1f4", outline="#8a9096")
    cv.create_rectangle(x - 23 * s, y - 12 * s, x + 23 * s, y + 28 * s, fill="#9cc4e8", outline="")


def art_syringe(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 40 * s, y - 7 * s, x + 20 * s, y + 7 * s, fill="#eef2f5", outline="#777")
    cv.create_rectangle(x - 40 * s, y - 6 * s, x - 15 * s, y + 6 * s, fill="#9cc4e8", outline="")
    cv.create_rectangle(x + 20 * s, y - 2 * s, x + 40 * s, y + 2 * s, fill="#ddd", outline="#777")
    cv.create_line(x - 52 * s, y, x - 40 * s, y, fill="#999", width=2)


def art_caliper(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 50 * s, y - 4 * s, x + 50 * s, y + 4 * s, fill="#c9cdd2", outline="#777")
    cv.create_rectangle(x - 50 * s, y - 4 * s, x - 42 * s, y + 24 * s, fill="#c9cdd2", outline="#777")
    cv.create_rectangle(x - 20 * s, y - 14 * s, x + 10 * s, y + 6 * s, fill="#2b2e33", outline="")
    cv.create_rectangle(x - 16 * s, y - 11 * s, x + 6 * s, y - 3 * s, fill="#9fae8f", outline="")


ART = {"paper": art_paper, "holder": art_holder, "plate": art_plate, "cup": art_cup, "syringe": art_syringe, "caliper": art_caliper}
PARTS = [
    ("paper",   ("모눈종이", "Graph paper"), []),
    ("holder",  ("유리판 받침 (관·너트·마개)", "Plate holder (pipe, nuts, cap)"), []),
    ("plate",   ("유리판", "Glass plate"), []),
    ("cup",     ("물컵", "Cup of water"), []),
    ("syringe", ("주사기 (3 ml)", "Syringe (3 ml)"), []),
    ("caliper", ("디지털 캘리퍼", "Digital caliper"), []),
]
ZONES = {
    "paper":   (150, 260, 100, 120),
    "holder":  (330, 250, 80, 70),
    "plate":   (480, 250, 70, 90),
    "cup":     (620, 250, 70, 80),
    "syringe": (230, 420, 120, 40),
    "caliper": (450, 420, 130, 60),
}
SCENE_TITLE = ("실험대 — 모눈종이, 받침, 유리판, 물컵, 주사기, 캘리퍼", "The bench — graph paper, holder, glass plate, cup, syringe, caliper")
APP_TITLE = ("NBPhO 2023 실험 (문제 9) — 표면장력", "NBPhO 2023 Experiment (Problem 9) — Surface tension")
CAL = [("plate", ("유리판 두께", "plate thickness")), ("pipe", ("관 높이", "pipe height")), ("nut", ("너트 두께", "nut thickness")),
       ("seat", ("바닥→너트 윗면", "base→nut top")), ("above", ("관 윗면→너트 윗면", "pipe top→nut top")), ("drop", ("방울 지름", "drop diameter"))]


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.cal, self.cal_read = None, None
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
        f = ttk.LabelFrame(ctl, text=T("받침", "Holder"))
        f.pack(fill="x", pady=2)
        stepper(f, T("윗 너트", "Top nut"), [(t, (lambda d: lambda: self.nut(d))(v)) for t, v in (("▼1", -1), ("▼0.1", -0.1), ("▲0.1", 0.1), ("▲1", 1))])
        stepper(f, T("예비 너트", "Spare nuts"), [("−1", lambda: self.spare(-1)), ("+1", lambda: self.spare(1))])
        self.bCap = ttk.Button(f, text="", command=self.cap)
        self.bCap.pack(anchor="w")
        self.vHold = ttk.Label(f, text="", foreground="#1a4fb4")
        self.vHold.pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("유리판 놓을 곳", "Put the plate"))
        f.pack(fill="x", pady=2)
        self.at = tk.StringVar(value="table")
        row = ttk.Frame(f)
        row.pack(fill="x")
        for k, lb in (("holder", T("받침 위", "on the holder")), ("paper", T("모눈종이 위", "on the paper")), ("table", T("책상", "on the table"))):
            ttk.Radiobutton(row, text=lb, value=k, variable=self.at, command=self.plate_to).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("주사기와 물 (눈금 0.1 ml)", "Syringe and water (0.1 ml marks)"))
        f.pack(fill="x", pady=2)
        stepper(f, T("컵에서", "From cup"), [("+0.1 ml", lambda: self.suck(0.1)), ("+0.5 ml", lambda: self.suck(0.5))])
        stepper(f, T("판에 짜기", "Onto plate"), [("−0.1 ml", lambda: self.expel(0.1)), ("−0.5 ml", lambda: self.expel(0.5))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("작은 방울 하나", "One small drop"), command=self.drop).pack(side="left", padx=2)
        ttk.Button(row, text=T("판 닦기", "Wipe the plate"), command=self.wipe).pack(side="left", padx=2)
        f = ttk.LabelFrame(ctl, text=T("캘리퍼로 재기 (0.01 mm)", "Caliper (0.01 mm)"))
        f.pack(fill="x", pady=2)
        row = None
        for i, (k, lb) in enumerate(CAL):
            if i % 3 == 0:
                row = ttk.Frame(f)
                row.pack(fill="x")
            ttk.Button(row, text=T(*lb), command=(lambda kk: lambda: self.measure(kk))(k)).pack(side="left", padx=1)
        self.dC = tk.Label(f, text="", font=("Courier", 16, "bold"), bg="#9fae8f", fg="#1b1d20", width=12)
        self.dC.pack(pady=2)
        self.lC = ttk.Label(f, text="")
        self.lC.pack()
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
        ttk.Label(right, text=T("받침 (옆에서 본 단면) · 스크린에 맺힌 상 · 주사기 눈금", "The holder (section from the side) · the image on the screen · the syringe"),
                  font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=860, height=700, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    # ---- the hands
    def nut(self, d):
        ph = self.ph
        if not self.need("holder"):
            return
        p = round(ph.p + d, 2)
        if p < 0 or p > ph.tn:
            self.say(T("너트가 더 돌아가지 않습니다 (너트 두께만큼만).", "The nut turns no further (only over its own thickness)."))
            return
        ph.p = p
        self.refresh()

    def spare(self, d):
        ph = self.ph
        if not self.need("holder"):
            return
        if ph.plate_at == "holder":
            self.say(T("먼저 유리판을 받침에서 내리시오.", "Take the plate off the holder first."))
            return
        ph.nk = max(0, min(3, ph.nk + d))
        self.refresh()

    def cap(self):
        ph = self.ph
        if not self.need("holder"):
            return
        if ph.plate_at == "holder":
            self.say(T("먼저 유리판을 받침에서 내리시오.", "Take the plate off the holder first."))
            return
        ph.cap = not ph.cap
        self.refresh()

    def plate_to(self):
        w = self.at.get()
        if not self.need("plate") or (w == "holder" and not self.need("holder")) or (w == "paper" and not self.need("paper")):
            self.at.set(self.ph.plate_at)
            return
        self.ph.plate_at = w
        self.refresh()
        self.app.tab_top.draw()

    def suck(self, v):
        if self.need("syringe", "cup"):
            self.ph.syr = min(3.0, round(self.ph.syr + v, 2))
            self.refresh()

    def expel(self, v):
        if self.need("syringe", "plate"):
            out = min(self.ph.syr, v)
            self.ph.syr = round(self.ph.syr - out, 3)
            self.ph.water = round(self.ph.water + out, 4)
            self.refresh()
            self.app.tab_top.draw()

    def drop(self):
        if self.need("syringe", "plate"):
            if self.ph.syr < 0.02:
                self.say(T("주사기가 비었습니다.", "The syringe is empty."))
                return
            v = self.ph.r.uniform(7, 13) / 1000
            self.ph.syr = max(0.0, round(self.ph.syr - v, 3))
            self.ph.water += v
            self.refresh()
            self.app.tab_top.draw()

    def wipe(self):
        if self.need("plate"):
            self.ph.water = 0.0
            self.refresh()
            self.app.tab_top.draw()

    def measure(self, k):
        if not self.need("caliper"):
            return
        if k == "plate" and not self.need("plate"):
            return
        if k in ("pipe", "nut", "seat", "above") and not self.need("holder"):
            return
        self.cal, self.cal_read = k, self.ph.caliper(k)
        if self.cal_read is None:
            self.say(T("판에 작은 물방울이 없습니다.", "There is no small drop on the plate."))
        self.refresh()

    def record(self):
        if self.cent.get().strip():
            self.sheet.add((self.cent.get().strip(),))
            self.cent.delete(0, "end")

    def refresh(self):
        ph = self.ph
        self.vHold.config(text=T("예비 너트 %d개 · 마개 %s", "%d spare nut(s) · cap %s") % (ph.nk, T("끼움", "in") if ph.cap else T("뺌", "out")))
        self.bCap.config(text=T("마개 빼기", "Take the cap out") if ph.cap else T("마개 끼우기", "Put the cap in"))
        lab = dict((k, T(*v)) for k, v in CAL)
        on = self.cal_read is not None and self.has("caliper")
        self.dC.config(text=("%.2f mm" % self.cal_read) if on else "")
        self.lC.config(text=(T("무는 것: ", "jaws on: ") + lab[self.cal]) if on else "")
        self.draw()

    # ---- the drawing: holder section, the screen's image, the syringe
    def draw(self):
        cv, ph = self.cv, self.ph
        cv.delete("all")
        x0, base = 230, 640
        top = max(30.0, ph.seat() + ph.tg + 4)
        s = min(400 / 40.0, 560 / top)
        X = lambda u: x0 + u * s
        Y = lambda z: base - z * s
        cv.create_rectangle(10, base, 450, base + 8, fill="#fbfaf2" if self.has("paper") else "#d6d3c8", outline="")
        if self.has("holder"):
            r, rin, R = 10.5, 9.2, 15.5
            for sg in (-1, 1):
                xa = X(-r) if sg < 0 else X(rin)
                cv.create_rectangle(xa, Y(ph.Hp), xa + (r - rin) * s, Y(0), fill="#eef0f2", outline="#8a9096")
            if ph.cap:
                cv.create_rectangle(X(-rin), Y(ph.Hp - ph.capOff), X(rin), Y(ph.Hp - ph.capOff - 2.5), fill="#3d6fb6", outline="#24497c")
                cv.create_rectangle(X(-r - 0.4), Y(ph.Hp - ph.capOff + 0.8), X(r + 0.4), Y(ph.Hp - ph.capOff), fill="#4a7fc8", outline="#24497c")
            for i in range(ph.nk + 1):
                z0 = ph.Hp + ph.p - ph.tn + i * ph.tn
                for sg in (-1, 1):
                    xa = X(-R) if sg < 0 else X(r)
                    cv.create_rectangle(xa, Y(z0 + ph.tn), xa + (R - r) * s, Y(z0 + 0.02), fill="#b9bfc5", outline="#5f666c")
            if ph.plate_at == "holder":
                zb = ph.seat()
                zt = zb + ph.tg
                cv.create_rectangle(X(-19), Y(zt), X(19), Y(zb), fill="#cfe4ee", outline="#6b8ba3")
                L = ph.lens()
                if L:
                    a, Rr, f = L
                    c = Rr * math.cos(ph.alpha)
                    pts = []
                    for i in range(41):
                        u = -a + 2 * a * i / 40
                        pts += [X(u), Y(zt + math.sqrt(Rr * Rr - u * u) - c)]
                    cv.create_polygon(*pts, fill="#9cc8ee", outline="#3a7bd5")
                P = ph.pool()
                if P:
                    cv.create_rectangle(X(-17), Y(zt + P[2]), X(17), Y(zt), fill="#9cc8ee", outline="")
        else:
            cv.create_text(230, 400, text=T("받침을 놓으시오", "Place the holder"), fill="#69717a")
        # the screen
        cx, cy, Rs = 640, 200, 130
        k = Rs / 7.0
        bg = "#4a7fc8" if ph.cap else "#f4f2e8" if self.has("paper") else "#cfccc0"
        bg = mix(bg, "#000000", 0.18)
        cv.create_text(cx, cy - Rs - 14, text=T("스크린에 맺힌 상 (14 mm 시야)", "Image on the screen (14 mm field)"), font=("Helvetica", 10, "bold"))
        cv.create_oval(cx - Rs, cy - Rs, cx + Rs, cy + Rs, fill=bg, outline="#333", width=2)
        if not ph.cap and self.has("paper"):
            for i in range(-6, 7):
                col = "#d6a080" if i % 5 == 0 else "#e2c2ac"
                hw = math.sqrt(max(0, Rs * Rs - (i * k) ** 2))
                cv.create_line(cx + i * k, cy - hw, cx + i * k, cy + hw, fill=col)
                cv.create_line(cx - hw, cy + i * k, cx + hw, cy + i * k, fill=col)
        im = ph.image()
        if im:
            f, v, sharp, D, blur, sc = im
            bright = min(1.0, 0.18 / blur + 0.15)
            col = mix(bg, "#fffae1", bright)
            for (tx, ty, tl, tw) in TUBES:
                x = cx - (tx + tl / 2) * sc * k
                y = cy - ty * sc * k
                hw = max(0.6, tw * sc * k / 2 + blur * k / 2)
                hl = tl * sc * k / 2 + blur * k / 2
                cv.create_rectangle(x - hl, y - hw, x + hl, y + hw, fill=col, outline="")
        cv.create_text(cx, cy + Rs + 14, text=T("스크린: 마개 윗면", "screen: the cap's top") if ph.cap else T("스크린: 모눈종이", "screen: graph paper") if self.has("paper") else T("스크린: 책상", "screen: the table"), font=("Helvetica", 9))
        # the syringe
        if self.has("syringe"):
            x1, yc, Lb, rr = 470, 470, 360, 22
            mlpx = Lb / 3.2
            xz = x1 + Lb * 0.04
            cv.create_text(x1, yc - 60, text=T("주사기 (ml)", "Syringe (ml)"), anchor="w", font=("Helvetica", 10, "bold"))
            cv.create_rectangle(x1, yc - rr, x1 + Lb, yc + rr, fill="#eef2f5", outline="#777")
            if ph.syr > 0:
                cv.create_rectangle(xz, yc - rr + 2, xz + ph.syr * mlpx, yc + rr - 2, fill="#9cc4e8", outline="")
            for i in range(31):
                x = xz + i * 0.1 * mlpx
                cv.create_line(x, yc - rr, x, yc - rr + (18 if i % 10 == 0 else 12 if i % 5 == 0 else 8), fill="#1b1d20", width=2 if i % 5 == 0 else 1)
                if i % 5 == 0:
                    cv.create_text(x, yc - rr - 10, text=("%g" % (i / 10.0)), font=("Helvetica", 9, "bold"))
            xp = xz + ph.syr * mlpx
            cv.create_rectangle(xp, yc - rr + 1, xp + 8, yc + rr - 1, fill="#1b1d20", outline="")
            cv.create_rectangle(xp + 8, yc - 6, x1 + Lb + 24, yc + 6, fill="#f2f3f4", outline="#999")
        else:
            cv.create_text(650, 470, text=T("주사기를 놓으시오", "Place the syringe"), fill="#69717a")
        P = ph.pool()
        if P and P[3]:
            cv.create_text(650, 600, width=380, fill="#8a1b1b", text=T("물이 유리판 가장자리 전체에 닿았습니다 — 물층이 더 두꺼워질 수 있습니다.",
                                                                 "The water touches the plate's edge all round — the layer can grow thicker."))


# --------------------------------------------------------------------------
#  Graph paper tab: the plate on the paper from above; zoom and drag
# --------------------------------------------------------------------------
class TopTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.z, self.cx, self.cy, self.dr = 1.0, 0.0, 0.0, None
        row = ttk.Frame(self)
        row.pack(anchor="w", padx=6, pady=4)
        ttk.Label(row, text=T("모눈종이 위의 유리판 (1 mm 눈금, 굵은 선 10 mm) — 휠/단추로 확대, 끌어서 이동", "The plate on the graph paper (1 mm grid, heavy lines 10 mm) — wheel/buttons zoom, drag to move"),
                  font=("Helvetica", 10, "bold")).pack(side="left")
        ttk.Button(row, text="+", width=3, command=lambda: self.zoom(1.25)).pack(side="left", padx=2)
        ttk.Button(row, text="−", width=3, command=lambda: self.zoom(0.8)).pack(side="left", padx=2)
        ttk.Button(row, text=T("처음 배율", "Reset"), command=self.reset).pack(side="left", padx=2)
        self.cv = tk.Canvas(self, width=1200, height=720, bg="#fbfaf2", highlightthickness=0)
        self.cv.pack(padx=6, pady=6)
        self.cv.bind("<ButtonPress-1>", self.press)
        self.cv.bind("<B1-Motion>", self.move)
        self.cv.bind("<MouseWheel>", lambda e: self.zoom(1.2 if e.delta > 0 else 1 / 1.2))
        self.cv.bind("<Button-4>", lambda e: self.zoom(1.2))
        self.cv.bind("<Button-5>", lambda e: self.zoom(1 / 1.2))

    def zoom(self, k):
        self.z = max(1.0, min(14.0, self.z * k))
        self.draw()

    def reset(self):
        self.z, self.cx, self.cy = 1.0, 0.0, 0.0
        self.draw()

    def press(self, e):
        self.dr = (e.x, e.y, self.cx, self.cy)

    def move(self, e):
        if self.dr:
            s = 720 / 70.0 * self.z
            self.cx = self.dr[2] - (e.x - self.dr[0]) / s
            self.cy = self.dr[3] - (e.y - self.dr[1]) / s
            self.draw()

    def draw(self):
        cv, ph = self.cv, self.app.ph
        cv.delete("all")
        W, H = 1200, 720
        if "paper" not in self.app.placed:
            cv.create_text(W / 2, H / 2, text=T("모눈종이를 놓으시오", "Place the graph paper"), fill="#69717a")
            return
        s = 720 / 70.0 * self.z
        X = lambda u: W / 2 + (u - self.cx) * s
        Y = lambda w: H / 2 + (w - self.cy) * s
        u0, u1 = int(math.floor(self.cx - W / 2 / s)) - 1, int(math.ceil(self.cx + W / 2 / s)) + 1
        w0, w1 = int(math.floor(self.cy - H / 2 / s)) - 1, int(math.ceil(self.cy + H / 2 / s)) + 1
        for u in range(u0, u1 + 1):
            cv.create_line(X(u), 0, X(u), H, fill="#d6783c" if u % 10 == 0 else "#ebb995" if u % 5 == 0 else "#f6dcc8", width=2 if u % 10 == 0 else 1)
        for w in range(w0, w1 + 1):
            cv.create_line(0, Y(w), W, Y(w), fill="#d6783c" if w % 10 == 0 else "#ebb995" if w % 5 == 0 else "#f6dcc8", width=2 if w % 10 == 0 else 1)
        if ph.plate_at != "paper":
            cv.create_text(W / 2, 24, text=T("유리판을 모눈종이 위에 놓으시오 (실험대 탭)", "Put the plate on the paper (Bench tab)"), fill="#69717a", font=("Helvetica", 11, "bold"))
            return
        ox, oy = ph.po
        cv.create_rectangle(X(ox - GW / 2), Y(oy - GH / 2), X(ox + GW / 2), Y(oy + GH / 2 + MATTE), outline="#6b8ba3", width=2)
        cv.create_rectangle(X(ox - GW / 2), Y(oy + GH / 2), X(ox + GW / 2), Y(oy + GH / 2 + MATTE), fill="#eceff1", outline="#6b8ba3")
        cv.create_text(X(ox), Y(oy + GH / 2 + MATTE / 2), text=T("불투명한 부분", "matte part"), fill="#6b7177")
        L = ph.lens()
        if L:
            a = L[0]
            cv.create_oval(X(ox - a), Y(oy - a), X(ox + a), Y(oy + a), outline="#285a96", width=max(1, int(s * 0.08)))
        P = ph.pool()
        if P:
            pts = []
            for u, w in P[0]:
                pts += [X(ox + u), Y(oy + w)]
            cv.create_polygon(*pts, fill="#bcdcf2", stipple="gray50", outline="#285a96", width=max(1, int(s * 0.08)))


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
        self.geometry("1360x880")
        self.placed = set()
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_asm = AssemblyTab(nb, self)
        self.tab_top = TopTab(nb, self)
        self.tab_bench = BenchTab(nb, self)
        nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.tab_bench, text=T(" 실험대 ", " Bench "))
        nb.add(self.tab_top, text=T(" 모눈종이 ", " Graph paper "))
        self.tab_top.draw()

    def on_assembly_change(self, placed):
        self.placed = set(placed)
        self.tab_bench.refresh()
        self.tab_top.draw()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
