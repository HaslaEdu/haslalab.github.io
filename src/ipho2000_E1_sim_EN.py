#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  31st International Physics Olympiad  (IPhO 2000, Leicester, UK)
  Experimental Problem 1 :  CD-ROM SPECTROMETER
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* Bulbs A and B (12 V 50 W) and the small bulb C are tungsten
  filaments: R follows tungsten's resistivity table, the temperature
  balances electrical power against radiation (and a little loss
  through the leads).  B is A's twin; C is fed from 2 V through a
  rheostat and must be matched to B (its loop vanishes against B's).
* The CD strip is a 620 lines/mm reflection grating; the LDR on its
  track at distance L sees the first order (and a faint second) of
  A's light, Planck's law times the LDR's spectral response, through
  a 3 mm window.  G = 1/R is taken as proportional to the light.
* The resistances, the bulbs' temperatures and L are hidden and
  randomised.  Standard library only (tkinter).

    Run:   python3 ipho2000_E1_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line

RHO = [(300, 5.65), (400, 8.06), (500, 10.56), (600, 13.23), (700, 16.0), (800, 18.8), (900, 21.7), (1000, 24.9), (1200, 31.1), (1400, 37.5),
       (1600, 44.0), (1800, 50.6), (2000, 57.2), (2200, 64.0), (2400, 71.0), (2600, 78.0), (2800, 85.3), (3000, 92.6), (3200, 100.0), (3400, 107.5)]
T0, C2 = 300.0, 1.4388e-2
MODES = {"off": None, "Ω200": ("ohm", 199.9, 1, 1, "Ω"), "Ω2k": ("ohm", 1999, 1, 0, "Ω"), "Ω20k": ("ohm", 19.99e3, 1e-3, 2, "kΩ"), "Ω200k": ("ohm", 199.9e3, 1e-3, 1, "kΩ"),
         "Ω2M": ("ohm", 1.999e6, 1e-6, 3, "MΩ"), "V2": ("V", 1.999, 1, 3, "V"), "V20": ("V", 19.99, 1, 2, "V")}


def rho(T):
    if T <= RHO[0][0]:
        return RHO[0][1]
    for (a, ra), (b, rb) in zip(RHO, RHO[1:]):
        if T <= b:
            return ra + (rb - ra) * (T - a) / (b - a)
    return RHO[-1][1]


def planck(l, T):
    return 1 / (l ** 5 * (math.exp(min(700, C2 / (l * T))) - 1))


# --------------------------------------------------------------------------
#  Physics core
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.RA, TA12, self.kcA = r.uniform(0.19, 0.23), r.uniform(2850, 3050), 0.001
        self.RC, TC2, self.kcC = r.uniform(1.0, 1.4), r.uniform(2250, 2400), 0.00001
        self.rB, self.L, self.d = r.uniform(0.99, 1.01), r.uniform(18, 22), 1 / 620e3
        self.Gd, self.gk = r.uniform(0.5, 0.9) * 1e-6, r.uniform(0.9, 1.2)
        self.krA = (144 / (self.RA * rho(TA12) / rho(T0)) - self.kcA * (TA12 - T0)) / (TA12 ** 4 - T0 ** 4)
        self.krC = (4 / (self.RC * rho(TC2) / rho(T0)) - self.kcC * (TC2 - T0)) / (TC2 ** 4 - T0 ** 4)

    @staticmethod
    def bulb(R300, kr, kc, E, Rs):
        if E <= 0:
            return T0, 0.0, 0.0
        lo, hi = T0, 3600.0
        for _ in range(50):
            T = (lo + hi) / 2
            R = R300 * rho(T) / rho(T0)
            I = E / (R + Rs)
            if I * I * R > kr * (T ** 4 - T0 ** 4) + kc * (T - T0):
                lo = T
            else:
                hi = T
        T = (lo + hi) / 2
        R = R300 * rho(T) / rho(T0)
        I = E / (R + Rs)
        return T, I, I * R

    def A(self, V):
        return self.bulb(self.RA, self.krA, self.kcA, V, 0.015)

    def B(self, on):
        return self.bulb(self.RA * self.rB, self.krA, self.kcA, 2.0 if on else 0.0, 0.01)

    def C(self, on, Rv):
        return self.bulb(self.RC, self.krC, self.kcC, 2.0 if on else 0.0, Rv)

    def ldr_G(self, x, TA):
        E = 0.0
        if TA > 900:
            for dx in (-0.15, -0.075, 0, 0.075, 0.15):
                xx = x + dx
                if xx <= 0.4:
                    continue
                th = math.atan(xx / self.L)
                for m, w in ((1, 1.0), (2, 0.22)):
                    l = self.d * math.sin(th) / m
                    if 380e-9 <= l <= 760e-9:
                        n = l * 1e9
                        S = math.exp(-((n - 555) / (62 if n < 555 else 48)) ** 2)
                        E += w * S * planck(l, TA) * math.cos(th)
            E /= 5
        return self.Gd + self.gk * E * 5e-32


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def box_art(col, w, h):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_rectangle(x - w * s, y - h * s, x + w * s, y + h * s, fill=col, outline="#555")
    return art


def art_can(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 22 * s, y - 22 * s, x + 22 * s, y + 22 * s, fill="#1d1f23", outline="#555")
    cv.create_rectangle(x + 20 * s, y - 3 * s, x + 24 * s, y + 3 * s, fill="#ffd27a", outline="")


ART = {"can": art_can, "grating": box_art("#bcd0e6", 6, 22), "track": box_art("#8a6a40", 8, 40), "dmm": box_art("#e3b72d", 18, 28),
       "board": box_art("#a8784a", 44, 26), "graphs": box_art("#fbfaf2", 34, 22)}
PARTS = [
    ("can",     ("전구 A (캔) + 0–12 V 전원 + 전류계", "Bulb A (can) + 0–12 V supply + ammeter"), []),
    ("grating", ("CD 오목 격자 (620 /mm)", "CD concave grating (620 /mm)"), []),
    ("track",   ("LDR과 눈금 트랙", "LDR on its scaled track"), ["grating"]),
    ("dmm",     ("멀티미터 X", "Multimeter X"), []),
    ("board",   ("전구 B·C 판 (2 V, 가변저항)", "Bulbs B and C board (2 V, rheostat)"), []),
    ("graphs",  ("그래프 (비저항, 플랑크 곡선)", "Graphs (resistivity, Planck curves)"), []),
]
ZONES = {"can": (120, 260, 50, 50), "grating": (520, 260, 16, 50), "track": (340, 340, 20, 90), "dmm": (640, 420, 40, 60),
         "board": (620, 150, 96, 56), "graphs": (200, 450, 76, 50)}
SCENE_TITLE = ("전구 A의 캔 · CD 격자 · LDR 트랙 · 멀티미터 X · 전구 B·C 판", "Bulb A's can · CD grating · LDR track · multimeter X · bulbs B and C")
APP_TITLE = ("IPhO 2000 실험 1 — CD-ROM 분광기", "IPhO 2000 Experiment 1 — CD-ROM spectrometer")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.VA, self.xl, self.Rv = 0.0, 4.0, 40.0
        self.two = tk.BooleanVar(value=False)
        self.mode, self.conn = tk.StringVar(value="off"), tk.StringVar(value="none")
        self.disp, self.disp_t, self.amm = "", 0.0, ("0.000", "0.000", "0.000")
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("멀티미터 X", "Multimeter X"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.xl_ = tk.Label(row, text="", font=("Courier", 14, "bold"), bg="#9fae8f", fg="#1b1d20", width=12)
        self.xl_.pack(side="left", padx=2)
        ttk.OptionMenu(row, self.mode, "off", *MODES.keys()).pack(side="left")
        row = ttk.Frame(f)
        row.pack(fill="x")
        for v, lab in (("none", T("분리", "off")), ("ldr", "LDR"), ("A", T("전구 A", "bulb A")), ("B", T("전구 B", "bulb B")), ("C", T("전구 C", "bulb C"))):
            ttk.Radiobutton(row, text=lab, value=v, variable=self.conn).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("전구 A 전원 · 전류계", "Bulb A supply · ammeter"))
        f.pack(fill="x", pady=2)
        self.al = ttk.Label(f, text="", font=("Courier", 12, "bold"))
        self.al.pack(anchor="w")
        stepper(f, T("다이얼 (V)", "Dial (V)"), [("0", lambda: self.setv(-99)), ("−1", lambda: self.setv(-1)), ("−0.1", lambda: self.setv(-0.1)), ("+0.1", lambda: self.setv(0.1)), ("+1", lambda: self.setv(1)), ("12", lambda: self.setv(99))])
        f = ttk.LabelFrame(ctl, text=T("전구 B·C (2 V)", "Bulbs B and C (2 V)"))
        f.pack(fill="x", pady=2)
        ttk.Checkbutton(f, text=T("2 V 켜기", "2 V on"), variable=self.two).pack(anchor="w")
        self.bl = ttk.Label(f, text="", font=("Courier", 12, "bold"))
        self.bl.pack(anchor="w")
        stepper(f, T("가변저항", "Rheostat"), [("−5", lambda: self.setr(-5)), ("−1", lambda: self.setr(-1)), ("−0.1", lambda: self.setr(-0.1)), ("+0.1", lambda: self.setr(0.1)), ("+1", lambda: self.setr(1)), ("+5", lambda: self.setr(5))])
        f = ttk.LabelFrame(ctl, text=T("LDR 위치 (트랙)", "LDR position (track)"))
        f.pack(fill="x", pady=2)
        stepper(f, "", [("−1", lambda: self.setx(-1)), ("−0.1", lambda: self.setx(-0.1)), ("−0.02", lambda: self.setx(-0.02)), ("+0.02", lambda: self.setx(0.02)), ("+0.1", lambda: self.setx(0.1)), ("+1", lambda: self.setx(1))])
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        ttk.Button(f, text=T("지금 X와 전류계 적기", "Write down X and the ammeters"), command=self.record).pack(anchor="w")
        self.sheet = DataSheet(f, [("x", "X", 90), ("a", "I_A", 70), ("b", "I_B", 70), ("c", "I_C", 70)], height=5)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=420)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("트랙 눈금 · 자 · 필라멘트 B와 C · 그래프", "Track scale · ruler · filaments B and C · graphs"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    def setv(self, d):
        if self.has("can"):
            self.VA = max(0.0, min(12.0, round(self.VA + d, 1)))

    def setr(self, d):
        if self.has("board"):
            self.Rv = max(0.0, min(50.0, round(self.Rv + d, 2)))

    def setx(self, d):
        if self.has("track"):
            self.xl = max(1.6, min(14.6, round(self.xl + d, 2)))

    def live(self, c):
        return (c == "A" and self.VA > 0 and self.has("can")) or (c in ("B", "C") and self.two.get() and self.has("board"))

    def raw(self):
        m, c, ph = MODES[self.mode.get()], self.conn.get(), self.ph
        if not self.has("dmm") or not m or c == "none":
            return None
        if m[0] == "ohm":
            if self.live(c):
                return "live"
            if c == "ldr":
                TA = ph.A(self.VA if self.has("can") else 0)[0]
                return 1 / ph.ldr_G(self.xl, TA) if self.has("track") and self.has("grating") else float("inf")
            return {"A": ph.RA, "B": ph.RA * ph.rB, "C": ph.RC}[c] + 0.012
        if c == "A":
            return ph.A(self.VA if self.has("can") else 0)[2]
        if c == "B":
            return ph.B(self.two.get() and self.has("board"))[2]
        if c == "C":
            return ph.C(self.two.get() and self.has("board"), self.Rv)[2]
        return 0.0

    def record(self):
        self.sheet.add((self.show(), self.amm[0], self.amm[1], self.amm[2]))

    def show(self):
        m = MODES[self.mode.get()]
        if not self.has("dmm"):
            return "—"
        if not m:
            return "OFF"
        return (self.disp + " " + m[4]) if self.disp and self.disp not in ("1", "Err") else self.disp

    def tick(self, dt):
        self.disp_t -= dt
        if self.disp_t <= 0:
            self.disp_t = 0.4
            ph, on = self.ph, self.two.get() and self.has("board")
            jit = lambda I: "%.3f" % (I * (1 + (random.random() - 0.5) * 0.001))
            self.amm = (jit(ph.A(self.VA if self.has("can") else 0)[1]), jit(ph.B(on)[1]), jit(ph.C(on, self.Rv)[1]))
            m, r = MODES[self.mode.get()], self.raw()
            if r is None or not m:
                self.disp = ""
            elif r == "live":
                self.disp = "Err"
            elif r == float("inf") or r > m[1]:
                self.disp = "1"
            else:
                q = 10 ** (-m[3]) / m[2]
                self.disp = "%.*f" % (m[3], (r * (1 + (random.random() - 0.5) * 0.002) + (random.random() - 0.5) * q * 0.8) * m[2])
        self.warn.config(text=T("전원이 켜진 회로에 저항 범위로 연결했습니다!", "Resistance range on a live circuit!") if self.disp == "Err" else "")
        self.refresh()

    def refresh(self):
        self.xl_.config(text=self.show())
        self.al.config(text=T("다이얼 %.1f V   I_A = %s A", "dial %.1f V   I_A = %s A") % (self.VA, self.amm[0]))
        self.bl.config(text="I_B = %s A   I_C = %s A   (%s %.1f %%)" % (self.amm[1], self.amm[2], T("가변저항", "rheostat"), self.Rv / 50 * 100))
        self.draw()

    def draw(self):
        cv, ph = self.cv, self.ph
        cv.delete("all")
        # the track's scale at the LDR's window, the ruler at the track
        def scale(y, lab, v, ok):
            cv.create_text(10, y - 10, anchor="w", text=lab, font=("Helvetica", 9, "bold"))
            cv.create_rectangle(10, y, 750, y + 50, fill="#fbfaf2", outline="#999")
            if not ok:
                return
            for mm in range(int(v * 10) - 40, int(v * 10) + 41):
                X = 380 + (mm - v * 10) * 9
                if mm < 0 or X < 10 or X > 750:
                    continue
                L = 22 if mm % 10 == 0 else (15 if mm % 5 == 0 else 9)
                cv.create_line(X, y, X, y + L, fill="#111", width=2 if mm % 10 == 0 else 1)
                if mm % 10 == 0:
                    cv.create_text(X, y + 34, text=str(mm // 10), font=("Helvetica", 9, "bold"))
            cv.create_line(380, y, 380, y + 50, fill="#b5462f", width=2)
        scale(24, T("트랙 눈금 — LDR 창의 위치 (cm, 0은 0차 방향)", "track scale — the LDR's window (cm, 0 along the zeroth order)"), self.xl, self.has("track"))
        scale(104, T("자 — 격자 면에서 트랙까지 (cm)", "ruler — from the grating's face to the track (cm)"), ph.L, self.has("track") and self.has("grating"))
        # filaments B and C
        cx, cy = 200, 300
        cv.create_rectangle(10, 180, 390, 420, fill="#141619", outline="")
        if self.has("board"):
            on = self.two.get()
            TB, TC = ph.B(on)[0], ph.C(on, self.Rv)[0]
            rad = lambda T: 0 if T < 700 else planck(600e-9, T) / planck(600e-9, 2000)
            def col(r):
                v = min(1, r ** 0.35 * 0.55) if r > 0 else 0
                return "#%02x%02x%02x" % (int(60 + 195 * v), int(30 + 200 * v * v), int(10 + 160 * v ** 3))
            rb, rc = rad(TB), rad(TC)
            pts = []
            for i in range(121):
                s = i / 120.0
                pts += [cx - 140 + s * 280, cy + math.sin(s * math.pi * 14) * 14]
            cv.create_line(*pts, fill=col(rb), width=6)
            vis = max(-1, min(1, (rc - rb) / (rb * 0.03 + 1e-9))) if rb > 0 else 0
            lc = col(rb) if abs(vis) < 0.15 else (col(rb * (1 + 3 * vis)) if vis > 0 else "#0a0806")
            cv.create_arc(cx - 36, cy - 28, cx + 36, cy + 20, start=20, extent=320, style="arc", outline=lc, width=3)
            cv.create_text(cx, 405, text=T("C의 고리가 사라지면 B와 같은 온도", "C's loop vanishes: same temperature as B"), fill="#9aa2aa", font=("Helvetica", 9))
        # the handouts
        x0, x1, y0, y1 = 430, 750, 190, 410
        cv.create_rectangle(x0, y0, x1, y1, fill="#fbfaf6", outline="#333")
        X = lambda T: x0 + (T - 300) / 3100.0 * (x1 - x0)
        Y = lambda r: y1 - r / 110.0 * (y1 - y0)
        for T_ in range(500, 3401, 500):
            cv.create_line(X(T_), y0, X(T_), y1, fill="#ddd")
            cv.create_text(X(T_), y1 + 10, text=str(T_), font=("Helvetica", 7))
        for r in range(0, 111, 20):
            cv.create_line(x0, Y(r), x1, Y(r), fill="#ddd")
            cv.create_text(x0 - 10, Y(r), text=str(r), font=("Helvetica", 7))
        cv.create_line(*[v for T_ in range(300, 3401, 50) for v in (X(T_), Y(rho(T_)))], fill="#1b1d20", width=2)
        cv.create_text(x0, y0 - 8, anchor="w", text=T("텅스텐 비저항 µΩ cm / T (K)", "tungsten resistivity µΩ cm / T (K)"), font=("Helvetica", 8, "bold"))
        x0, x1, y0, y1 = 40, 750, 450, 630
        cv.create_rectangle(x0, y0, x1, y1, fill="#fbfaf6", outline="#333")
        Xl = lambda n: x0 + (n - 400) / 350.0 * (x1 - x0)
        ref = planck(750e-9, 3250)
        for n in range(400, 751, 50):
            cv.create_line(Xl(n), y0, Xl(n), y1, fill="#ddd")
            cv.create_text(Xl(n), y1 + 9, text=str(n), font=("Helvetica", 7))
        for i, T_ in enumerate((2000, 2250, 2500, 2750, 3000, 3250)):
            c = ["#6b3fa0", "#2c6f9b", "#2f8f4e", "#c08a10", "#d0661d", "#b02020"][i]
            cv.create_line(*[v for n in range(400, 751, 10) for v in (Xl(n), y1 - planck(n * 1e-9, T_) / ref * (y1 - y0))], fill=c, width=2)
            cv.create_text(x1 - 4, y1 - planck(750e-9, T_) / ref * (y1 - y0) - 7, anchor="e", text="%d K" % T_, fill=c, font=("Helvetica", 8, "bold"))
        cv.create_text(x0, y0 - 8, anchor="w", text=T("흑체의 상대 세기 / λ (nm)", "black-body relative intensity / λ (nm)"), font=("Helvetica", 8, "bold"))


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
