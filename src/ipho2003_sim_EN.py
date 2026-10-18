#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  34th International Physics Olympiad  (IPhO 2003, Taipei, Taiwan)
  Experimental Problem :  OPTICAL PROPERTIES OF A LASER DIODE AND OF
                          NEMATIC LIQUID CRYSTALS
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The laser diode is fed from a 3 V battery through a 0-100 ohm
  variable resistor and the ammeter; its light rises from a faint glow
  to a straight line above the threshold and bends over at high current;
  the photodetector saturates near 8 V on LO gain.
* The light is partially polarized; polarizers, the 90 degree twisted
  nematic cell (a rotator whose twist unwinds above its critical voltage,
  with a small "bounce" just before) and the parallel-aligned cell (a
  retarder whose retardation falls with the rms voltage) act on Jones
  vectors.  The function generator's waveform sets the rms voltage.
* The threshold current, the polarization, the cells' critical voltage,
  birefringence and directors are hidden and randomised.
* Standard library only (tkinter).

    Run:   python3 ipho2003_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line

RAD = math.pi / 180


# --------------------------------------------------------------------------
#  Physics core
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.Ith, self.slope, self.roll = r.uniform(21.5, 25.5), r.uniform(0.95, 1.12), r.uniform(36, 42)
        self.pol, self.psiL = r.uniform(0.86, 0.94), r.uniform(-25, 25)
        self.Vc, self.w10 = r.uniform(1.25, 1.45), r.uniform(0.17, 0.21)
        self.tTN, self.tPA = r.uniform(0.33, 0.38), r.uniform(0.40, 0.44)
        self.dn0, self.Vth, self.pa, self.pp = r.uniform(0.219, 0.232), r.uniform(0.80, 0.90), r.uniform(1.0, 1.12), r.uniform(1.35, 1.5)
        self.dirTN, self.dirPA = r.uniform(-40, 40), r.uniform(-40, 40)
        self.rBat, self.eBat = r.uniform(0.5, 1.0), r.uniform(2.95, 3.15)

    @staticmethod
    def vLD(I):
        return 1.75 + 0.045 * math.log(1 + I / 2e-4) + 4.5 * I

    def current(self, knob, rA):
        R = 100 * (1 - knob) + 21 + rA + self.rBat
        a, b = 0.0, 0.08
        for _ in range(50):
            I = (a + b) / 2
            if self.eBat - self.vLD(I) - I * R > 0:
                a = I
            else:
                b = I
        return (a + b) / 2

    def light(self, ImA):
        if ImA <= self.Ith:
            return max(0.0, 0.012 * math.exp((ImA - self.Ith) / 4) * max(0.0, ImA) / self.Ith)
        return max(0.0, self.slope * (ImA - self.Ith) * (1 - (max(0.0, ImA - self.Ith) / (self.roll * 1.6)) ** 3) + 0.012)

    @staticmethod
    def sat(v):
        return v if v < 7 else 8.28 - 1.28 * math.exp(-(v - 7) / 1.28)

    def twist(self, V):
        if V < self.Vc:
            return 90.0
        x = (V - self.Vc) / self.w10
        S = 1 / (1 + math.exp(-(x - 2.2) * 1.35)) - 1 / (1 + math.exp(2.2 * 1.35))
        return 90 * (1 - min(1.0, S / 0.95))

    def bounce(self, V):
        return 0.035 * math.exp(-((V - (self.Vc - 0.13)) / 0.09) ** 2)

    def delta(self, V):
        d0 = 2 * math.pi * 7.7e-6 * self.dn0 / 650e-9
        return d0 if V <= self.Vth else d0 / (1 + self.pa * (V - self.Vth) ** self.pp)

    def chain(self, items, ang, V):
        """the share of the laser's light through the parts in order"""
        def run(E):
            for k in items:
                if k in ("p1", "p2"):
                    a = ang[k] * RAD
                    s, c = math.sin(a), math.cos(a)
                    along, across = E[0] * s + E[1] * c, E[0] * c - E[1] * s
                    ta, tc = math.sqrt(0.85), math.sqrt(0.0025)
                    E = (ta * along * s + tc * across * c, ta * along * c - tc * across * s)
                elif k == "tn":
                    r = self.twist(V) * RAD
                    c, s, t = math.cos(r), math.sin(r), math.sqrt(self.tTN)
                    E = (t * (c * E[0] + s * E[1]), t * (-s * E[0] + c * E[1]))
                elif k == "pa":
                    a = (ang["pa"] + self.dirPA) * RAD
                    s, c = math.sin(a), math.cos(a)
                    e1, e2 = E[0] * s + E[1] * c, (E[0] * c - E[1] * s) * complex(math.cos(self.delta(V)), math.sin(self.delta(V)))
                    t = math.sqrt(self.tPA)
                    E = (t * (e1 * s + e2 * c), t * (e1 * c - e2 * s))
            return abs(E[0]) ** 2 + abs(E[1]) ** 2
        q = self.psiL * RAD
        return self.pol * run((complex(math.sin(q)), complex(math.cos(q)))) + (1 - self.pol) / 2 * (run((1 + 0j, 0j)) + run((0j, 1 + 0j)))


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def box_art(col, w, h):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_rectangle(x - w * s, y - h * s, x + w * s, y + h * s, fill=col, outline="#555")
    return art


ART = {"rail": box_art("#9aa1a8", 120, 6), "ld": box_art("#2a2d33", 20, 8), "pd": box_art("#2a2d33", 14, 14), "p1": box_art("#3a3d42", 4, 18), "p2": box_art("#3a3d42", 4, 18),
       "tn": box_art("#c9a13a", 4, 18), "pa": box_art("#d6833c", 4, 18), "fg": box_art("#d9dde2", 30, 18), "dmm": box_art("#e3b72d", 18, 28), "rvar": box_art("#3a3d42", 14, 12)}
PARTS = [
    ("rail", ("[K] 광학대", "[K] Optical bench"), []),
    ("ld",   ("[E] 레이저 다이오드", "[E] Laser diode"), ["rail"]),
    ("pd",   ("[A] 광검출기", "[A] Photodetector"), ["rail"]),
    ("rvar", ("[H·I·J] 가변저항·전지", "[H·I·J] Variable resistor, batteries"), []),
    ("dmm",  ("[F] 멀티미터 2대", "[F] Two multimeters"), []),
    ("p1",   ("[B] 편광판 1", "[B] Polarizer 1"), ["rail"]),
    ("p2",   ("[B] 편광판 2", "[B] Polarizer 2"), ["rail"]),
    ("tn",   ("[C] 90° TN 액정", "[C] 90° TN LC cell"), ["rail"]),
    ("pa",   ("[G] 평행 배향 액정", "[G] Parallel LC cell"), ["rail"]),
    ("fg",   ("[D] 함수 발생기", "[D] Function generator"), []),
]
ZONES = {"rail": (380, 150, 250, 16), "ld": (160, 120, 44, 20), "pd": (600, 120, 32, 32), "rvar": (120, 300, 32, 28), "dmm": (260, 320, 40, 60),
         "p1": (250, 120, 12, 40), "p2": (510, 120, 12, 40), "tn": (380, 110, 12, 40), "pa": (420, 220, 12, 40), "fg": (560, 330, 64, 40)}
SCENE_TITLE = ("광학대 위 LD · 편광판 · 액정 · PD, 그리고 계기", "LD, polarizers, LC cell and PD on the bench, with the meters")
APP_TITLE = ("IPhO 2003 실험 — 레이저 다이오드와 액정", "IPhO 2003 Experiment — Laser diode and liquid crystals")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    CONFIG = {"A": [], "A2": ["p1", "p2"], "B": ["p1", "tn", "p2"], "C": ["p1", "pa", "p2"]}

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.cfg = tk.StringVar(value="A")
        self.bat = tk.BooleanVar(value=False)
        self.hi = tk.BooleanVar(value=False)
        self.wave = tk.StringVar(value="sq")
        self.knob, self.amp, self.f = 0.0, 0.0, 100.0
        self.ang = {"p1": random.uniform(0, 180), "p2": random.uniform(0, 180), "tn": random.uniform(0, 90), "pa": random.uniform(0, 90)}
        self.sel = tk.StringVar(value="p1")
        self.xy = [random.uniform(-0.25, 0.25), random.uniform(-0.25, 0.25)]
        self.disp, self.disp_t = ("", ""), 0.0
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def items(self):
        return [k for k in self.CONFIG[self.cfg.get()] if self.has(k)]

    def I(self):
        if not (self.bat.get() and self.has("ld") and self.has("rvar")):
            return 0.0
        rA = 1.0 if self.has("dmm") and self.cfg.get() == "A" else 0.0
        return self.ph.current(self.knob, rA)

    def vrms(self):
        a = self.amp / 2
        return a if self.wave.get() == "sq" else (a / math.sqrt(2) if self.wave.get() == "sin" else a / math.sqrt(3))

    def J(self):
        ph = self.ph
        if not (self.has("ld") and self.has("pd")):
            return 0.0
        al = math.exp(-(self.xy[0] ** 2 + self.xy[1] ** 2) / (2 * 0.07 ** 2))
        V = self.vrms() if self.has("fg") else 0.0
        items = self.items()
        T = ph.chain(items, self.ang, V)
        if "tn" in items:
            T += math.sin(2 * (self.ang["tn"] + ph.dirTN - self.ang["p1"]) * RAD) ** 2 * 0.18 * ph.tTN * 0.36 + ph.bounce(V) * 1.6 * ph.tTN * 0.36
        return ph.sat(ph.light(self.I() * 1000) * al * T * (10 if self.hi.get() else 1)) + 0.004

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("멀티미터", "Multimeters"))
        f.pack(fill="x", pady=2)
        self.l1 = tk.Label(f, text="", font=("Courier", 16, "bold"), bg="#9fae8f", width=20)
        self.l1.pack(anchor="w", pady=1)
        self.l2 = tk.Label(f, text="", font=("Courier", 16, "bold"), bg="#9fae8f", width=20)
        self.l2.pack(anchor="w", pady=1)
        f = ttk.LabelFrame(ctl, text=T("배치 (광학대 위)", "Layout (on the bench)"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for v, lab in (("A", T("A: LD–PD", "A: LD–PD")), ("A2", "P–A"), ("B", "P–TN–A"), ("C", "P–∥–A")):
            ttk.Radiobutton(row, text=lab, value=v, variable=self.cfg).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("LD 전류 · 광검출기", "LD current · photodetector"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Checkbutton(row, text=T("전지 켜기", "Battery on"), variable=self.bat).pack(side="left")
        ttk.Checkbutton(row, text=T("HI 이득", "HI gain"), variable=self.hi).pack(side="left", padx=6)
        stepper(f, T("가변저항", "Resistor"), [("◀◀", lambda: self.kn(-0.1)), ("◀", lambda: self.kn(-0.01)), ("‹", lambda: self.kn(-0.001)), ("›", lambda: self.kn(0.001)), ("▶", lambda: self.kn(0.01)), ("▶▶", lambda: self.kn(0.1))])
        stepper(f, T("PD 위치", "PD place"), [("◀", lambda: self.mvpd(0, -0.02)), ("▶", lambda: self.mvpd(0, 0.02)), ("▼", lambda: self.mvpd(1, -0.02)), ("▲", lambda: self.mvpd(1, 0.02))])
        f = ttk.LabelFrame(ctl, text=T("함수 발생기 · 회전 마운트", "Function generator · rotary mounts"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for v, lab in (("sq", T("사각파", "square")), ("sin", T("사인파", "sine")), ("tri", T("삼각파", "triangle"))):
            ttk.Radiobutton(row, text=lab, value=v, variable=self.wave).pack(side="left")
        stepper(f, T("진폭 (Vpp)", "Amplitude (Vpp)"), [("−1", lambda: self.am(-1)), ("−0.1", lambda: self.am(-0.1)), ("−0.02", lambda: self.am(-0.02)), ("+0.02", lambda: self.am(0.02)), ("+0.1", lambda: self.am(0.1)), ("+1", lambda: self.am(1))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        for v, lab in (("p1", "P"), ("tn", "TN"), ("pa", "∥"), ("p2", "A")):
            ttk.Radiobutton(row, text=lab, value=v, variable=self.sel).pack(side="left")
        stepper(f, T("돌리기", "Turn"), [("−10°", lambda: self.rot(-10)), ("−1°", lambda: self.rot(-1)), ("−0.2°", lambda: self.rot(-0.2)), ("+0.2°", lambda: self.rot(0.2)), ("+1°", lambda: self.rot(1)), ("+10°", lambda: self.rot(10))])
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        ttk.Button(f, text=T("지금 두 계기 적기", "Write down both meters"), command=self.record).pack(anchor="w")
        self.sheet = DataSheet(f, [("a", "F1", 150), ("b", "F2", 120)], height=5)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("광학대 위 · 회전 마운트 눈금 · 광검출기 앞면", "On the bench · rotary scales · photodetector face"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    def kn(self, d):
        self.knob = max(0.0, min(1.0, round(self.knob + d, 4)))

    def mvpd(self, i, d):
        self.xy[i] = round(self.xy[i] + d, 3)

    def am(self, d):
        self.amp = max(0.0, min(20.0, round(self.amp + d, 3)))

    def rot(self, d):
        k = self.sel.get()
        self.ang[k] = round((self.ang[k] + d) % 360, 2)

    def read(self):
        if not self.has("dmm"):
            return "—", "—"
        if self.cfg.get() in ("A", "A2"):
            a = "I = %.1f mA" % (self.I() * 1000 * (1 + random.uniform(-0.001, 0.001)))
        else:
            a = "Vrms = %.3f V" % (self.vrms() if self.has("fg") else 0.0)
        return a, "J = %.2f V" % (self.J() + random.uniform(-0.004, 0.004))

    def record(self):
        self.sheet.add(self.disp)

    def tick(self, dt):
        self.disp_t -= dt
        if self.disp_t <= 0:
            self.disp_t = 0.35
            self.disp = self.read()
        self.refresh()

    def refresh(self):
        self.l1.config(text="F1: " + self.disp[0])
        self.l2.config(text="F2: " + self.disp[1])
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        y, x0, k = 130, 40, 8.0
        cv.create_rectangle(x0, y - 8, x0 + 86 * k, y + 8, fill="#9aa1a8", outline="#666")
        pos = {"ld": 5, "p1": 15, "tn": 35, "pa": 35, "p2": 55, "pd": 65}
        if self.has("ld") and self.I() * 1000 > self.ph.Ith - 1:
            cv.create_line(x0 + 5 * k, y, x0 + 65 * k, y, fill="#e0302a", width=2)
        for kk in ["ld", "pd"] + self.items():
            if self.has(kk):
                X = x0 + pos[kk] * k
                cv.create_rectangle(X - 6, y - 26, X + 6, y + 26, fill={"tn": "#c9a13a", "pa": "#d6833c"}.get(kk, "#2a2d33"), outline="#f2c14e" if kk == self.sel.get() else "#555", width=2 if kk == self.sel.get() else 1)
                cv.create_text(X, y - 38, text={"ld": "LD", "pd": "PD", "p1": "P", "p2": "A", "tn": "TN", "pa": "∥"}[kk], font=("Helvetica", 10, "bold"))
                if kk in self.ang:
                    cv.create_text(X, y + 40, text="%.1f°" % self.ang[kk], font=("Helvetica", 9))
        # the chosen mount's scale, magnified
        s, cx, cy = self.sel.get(), 200, 400
        cv.create_rectangle(40, 300, 360, 470, fill="#fbfaf4", outline="#888")
        val = self.ang[s]
        for a in range(int(val) - 12, int(val) + 13):
            X = cx + (a - val) * 12
            if 45 < X < 355:
                L0 = 40 if a % 10 == 0 else (28 if a % 5 == 0 else 16)
                cv.create_line(X, cy + 20, X, cy + 20 - L0, fill="#222")
                if a % 10 == 0:
                    cv.create_text(X, cy - 34, text=str(a % 360), font=("Helvetica", 10, "bold"))
        cv.create_line(cx, cy + 50, cx, cy + 10, fill="#c0392b", width=2)
        cv.create_text(cx, 488, text=T("고른 마운트의 눈금", "the chosen mount's scale"), font=("Helvetica", 9))
        # the detector's face
        fx, fy, kk = 560, 400, 80
        cv.create_rectangle(fx - 85, fy - 85, fx + 85, fy + 85, fill="#1b1d20", outline="#555")
        cv.create_oval(fx + self.xy[0] * kk - 12, fy - self.xy[1] * kk - 12, fx + self.xy[0] * kk + 12, fy - self.xy[1] * kk + 12, fill="#050506", outline="#666")
        if self.has("ld") and self.I() * 1000 > self.ph.Ith - 1:
            cv.create_oval(fx - 6, fy - 6, fx + 6, fy + 6, fill="#ff3c28", outline="")
        cv.create_text(fx, fy + 100, text=T("PD 앞면: 구멍과 빔", "PD face: hole and beam"), font=("Helvetica", 9))
        cv.create_text(40, 600, anchor="w", text=T("가변저항 %.1f %% · FG %.2f Vpp · %s", "resistor %.1f %% · FG %.2f Vpp · %s") % (self.knob * 100, self.amp, self.wave.get()), font=("Courier", 10))


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
