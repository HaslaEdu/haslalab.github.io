#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  33rd International Physics Olympiad  (IPhO 2002, Bali, Indonesia)
  Experimental Problem 1 :  DETERMINATION OF e/kB THROUGH
                            ELECTROLYSIS
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The test tube and the graph paper carry the same arbitrary scale.
  Part A calibrates it: a steel ball hangs from the clamp on a wire
  with that scale, L = L0 + n u, and the period follows
  T = 2 pi sqrt(L/g) (1 + theta0^2/16).  You time the swings yourself.
* Part B: the tube, filled with water and turned over the cathode,
  collects hydrogen at It/(2e) molecules; each takes kB T / P of
  volume.  The current is set by the supply, the cell's back emf and
  its resistance, and flows only through the multimeter on a mA range.
* u, L0, the tube's diameter, the cell and the room are hidden and
  randomised.  Standard library only (tkinter).

    Run:   python3 ipho2002_E1_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line

E_CH, KB, GRAV = 1.602176634e-19, 1.380649e-23, 9.78
MODES = {"off": None, "mA20": (19.99, 2, "mA", 10), "mA200": (199.9, 1, "mA", 1), "V20": (19.99, 2, "V", 1e7), "V200": (199.9, 1, "V", 1e7)}
TUBE_L = 0.15


# --------------------------------------------------------------------------
#  Physics core
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.u = r.uniform(0.85, 0.93) * 1e-3
        self.L0 = r.uniform(0.30, 0.36)
        self.Dout = r.uniform(12.6, 13.4) * 1e-3
        self.alpha = 0.82
        self.T, self.P = r.uniform(298, 303), r.uniform(0.995, 1.012) * 1e5
        self.Rcell, self.Vback = r.uniform(3.2, 5.5) * 1e3, r.uniform(1.7, 2.0)
        self.bubble, self.z0, self.strip = r.uniform(1.5, 4.5), r.uniform(2, 6), r.uniform(-0.35, 0.35)

    def period(self, mark, amp):
        return 2 * math.pi * math.sqrt((self.L0 + mark * self.u) / GRAV) * (1 + amp * amp / 16)

    def r_in(self):
        return self.alpha * self.Dout / 2

    def current(self, V, rA):
        return max(0.0, (V - self.Vback) / (self.Rcell + rA))

    def marks_of(self, vol):
        return vol / (math.pi * self.r_in() ** 2) / self.u


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def box_art(col, w, h):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_rectangle(x - w * s, y - h * s, x + w * s, y + h * s, fill=col, outline="#555")
    return art


def art_stand(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 30 * s, y + 40 * s, x + 30 * s, y + 50 * s, fill="#3a3d42", outline="")
    cv.create_rectangle(x - 22 * s, y - 60 * s, x - 18 * s, y + 40 * s, fill="#b8bec5", outline="")
    cv.create_rectangle(x - 22 * s, y - 60 * s, x + 26 * s, y - 56 * s, fill="#b8bec5", outline="")


def art_pend(cv, x, y, sc=1.0):
    s = sc
    cv.create_line(x, y - 30 * s, x, y + 20 * s, fill="#7a4a2a", width=2)
    cv.create_oval(x - 8 * s, y + 18 * s, x + 8 * s, y + 34 * s, fill="#c9ced3", outline="#555")


def art_tube(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 7 * s, y - 34 * s, x + 7 * s, y + 34 * s, fill="#e1eef8", outline="#889")
    for i in range(-30, 31, 6):
        cv.create_line(x - 5 * s, y + i * s, x + 1 * s, y + i * s, fill="#333")


ART = {"stand": art_stand, "pend": art_pend, "container": box_art("#bcd6e6", 44, 26), "electrodes": box_art("#c8a243", 16, 8), "tube": art_tube,
       "psu": box_art("#d8dbe0", 36, 26), "dmm": box_art("#e3b72d", 18, 28), "watch": box_art("#2a2d33", 14, 16), "paper": box_art("#f6f6ee", 30, 20)}
PARTS = [
    ("stand",      ("수직 스탠드 (집게)", "Vertical stand (clamp)"), []),
    ("pend",       ("강철 공 진자 (눈금 줄)", "Steel-ball pendulum (scaled wire)"), ["stand"]),
    ("watch",      ("스톱워치", "Stopwatch"), []),
    ("container",  ("플라스틱 용기 (물)", "Plastic container (water)"), []),
    ("electrodes", ("전극 (황동 집게·판·파란 선)", "Electrodes (clamp, plate, wire)"), ["container"]),
    ("tube",       ("눈금 시험관 + 나무 받침", "Scaled test tube + holder"), ["electrodes"]),
    ("psu",        ("정전압 전원 0–60 V", "Regulated supply 0–60 V"), []),
    ("dmm",        ("멀티미터 (직렬)", "Multimeter (in series)"), ["psu", "electrodes"]),
    ("paper",      ("모눈종이·종이띠", "Graph paper, paper strip"), []),
]
ZONES = {"stand": (150, 230, 50, 80), "pend": (190, 250, 20, 60), "watch": (300, 380, 30, 30), "container": (560, 270, 90, 50), "electrodes": (620, 200, 30, 20),
         "tube": (520, 210, 16, 48), "psu": (620, 400, 60, 40), "dmm": (470, 400, 40, 50), "paper": (300, 470, 60, 30)}
SCENE_TITLE = ("스탠드와 진자 · 용기 · 전극 · 시험관 · 전원 · 멀티미터", "Stand and pendulum · container · electrodes · test tube · supply · multimeter")
APP_TITLE = ("IPhO 2002 실험 1 — 전기분해로 재는 e/k_B", "IPhO 2002 Experiment 1 — e/k_B through electrolysis")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.mark = random.uniform(95, 105)
        self.amp, self.phase = 0.0, 0.0
        self.watch_t, self.watch_run = 0.0, False
        self.V, self.clock, self.gas = 0.0, 0.0, 0.0
        self.psu, self.filled, self.cathode = tk.BooleanVar(value=False), False, True
        self.mode = tk.StringVar(value="off")
        self.speed = tk.IntVar(value=1)
        self.disp, self.disp_t = "", 0.0
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def cell_ok(self):
        return self.has("container") and self.has("electrodes") and self.has("tube") and self.filled and self.has("psu") and self.psu.get()

    def current(self):
        m = MODES[self.mode.get()]
        if not self.cell_ok() or not self.has("dmm") or not m:
            return 0.0
        return self.ph.current(self.V, m[3])

    def level(self):
        return self.ph.z0 + self.ph.marks_of(self.gas)

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("부분 A — 진자", "Part A — pendulum"))
        f.pack(fill="x", pady=2)
        stepper(f, T("줄 옮기기", "Move the wire"), [("−10", lambda: self.move(-10)), ("−1", lambda: self.move(-1)), ("−0.2", lambda: self.move(-0.2)),
                                                    ("+0.2", lambda: self.move(0.2)), ("+1", lambda: self.move(1)), ("+10", lambda: self.move(10))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.rel = ttk.Button(row, text="", command=self.release)
        self.rel.pack(side="left")
        self.wl = tk.Label(row, text="", font=("Courier", 14, "bold"), bg="#9fae8f", fg="#1b1d20", width=9)
        self.wl.pack(side="left", padx=6)
        self.wb = ttk.Button(row, text="", command=self.watch)
        self.wb.pack(side="left")
        ttk.Button(row, text=T("영점", "Reset"), command=self.wreset).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("부분 B — 전기분해", "Part B — electrolysis"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("시험관 채워 거꾸로 세우기", "Fill and invert the tube"), command=self.fill).pack(side="left")
        self.pol = ttk.Button(row, text="", command=self.swap)
        self.pol.pack(side="left", padx=4)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Checkbutton(row, text=T("전원 켜기", "Supply on"), variable=self.psu).pack(side="left")
        self.vl = ttk.Label(row, text="", font=("Courier", 12, "bold"))
        self.vl.pack(side="left", padx=6)
        stepper(f, T("전압", "Voltage"), [("−10", lambda: self.setv(-10)), ("−1", lambda: self.setv(-1)), ("−0.1", lambda: self.setv(-0.1)),
                                          ("+0.1", lambda: self.setv(0.1)), ("+1", lambda: self.setv(1)), ("+10", lambda: self.setv(10))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("멀티미터", "Multimeter"), width=9).pack(side="left")
        self.ml = tk.Label(row, text="", font=("Courier", 14, "bold"), bg="#9fae8f", fg="#1b1d20", width=11)
        self.ml.pack(side="left", padx=2)
        ttk.OptionMenu(row, self.mode, "off", *MODES.keys()).pack(side="left")
        row = ttk.Frame(f)
        row.pack(fill="x")
        for s in (1, 10, 60):
            ttk.Radiobutton(row, text="×%d" % s, value=s, variable=self.speed).pack(side="left")
        self.clk = ttk.Label(row, text="")
        self.clk.pack(side="left", padx=8)
        f = ttk.LabelFrame(ctl, text=T("주어진 값", "Given"))
        f.pack(fill="x", pady=2)
        ttk.Label(f, text="T = %.1f °C,  P = %.0f hPa,  g = 9.78 m/s²,  α = 0.82" % (self.ph.T - 273.15, self.ph.P / 100)).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        ttk.Button(f, text=T("지금 스톱워치와 전류 적기", "Write down the stopwatch and current"), command=self.record).pack(anchor="w")
        self.sheet = DataSheet(f, [("t", T("스톱워치", "watch"), 100), ("i", T("전류", "current"), 100)], height=5)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=420)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("집게의 줄 눈금 · 진자 · 시험관 눈금 · 종이띠", "Wire scale at the clamp · pendulum · tube scale · paper strip"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    def move(self, d):
        if self.has("pend") and self.amp == 0:
            self.mark = max(20.0, min(215.0, self.mark + d * random.uniform(0.97, 1.03)))

    def release(self):
        if not self.has("pend"):
            return
        if self.amp > 0:
            self.amp = 0.0
        else:
            self.amp, self.phase = math.radians(random.uniform(4.5, 5.5)), math.pi / 2

    def watch(self):
        if self.has("watch"):
            self.watch_run = not self.watch_run

    def wreset(self):
        self.watch_t = 0.0

    def fill(self):
        if self.has("tube") and self.has("container"):
            self.filled = True
            self.gas = self.ph.bubble * math.pi * self.ph.r_in() ** 2 * self.ph.u * random.uniform(0.8, 1.2)

    def swap(self):
        self.cathode = not self.cathode

    def setv(self, d):
        if self.has("psu"):
            self.V = max(0.0, min(60.0, round(self.V + d, 1)))

    def record(self):
        self.sheet.add(("%.2f s" % self.watch_t, self.show()))

    def show(self):
        if not self.has("dmm"):
            return "—"
        if not MODES[self.mode.get()]:
            return "OFF"
        return (self.disp + " " + MODES[self.mode.get()][2]) if self.disp and self.disp != "1" else self.disp

    def tick(self, dt):
        T_ = dt * self.speed.get()
        self.clock += T_
        if self.watch_run:
            self.watch_t += T_
        if self.amp > 0:
            self.phase += 2 * math.pi * T_ / self.ph.period(self.mark, self.amp)
            self.amp *= math.exp(-T_ / 900)
        I = self.current()
        self.gas += I * T_ / (2 * E_CH) * (1 if self.cathode else 0.5) * KB * self.ph.T / self.ph.P
        self.gas = min(self.gas, TUBE_L * math.pi * self.ph.r_in() ** 2)
        self.disp_t -= dt
        if self.disp_t <= 0:
            self.disp_t = 0.4
            m = MODES[self.mode.get()]
            if not self.has("dmm") or not m:
                self.disp = ""
            else:
                r = I * 1000 if self.mode.get().startswith("mA") else (self.V if self.cell_ok() else 0.0)
                self.disp = "1" if r > m[0] else "%.*f" % (m[1], r * (1 + (random.random() - 0.5) * 0.004) + (random.random() - 0.5) * 10 ** (-m[1]))
        msg = []
        if self.cell_ok() and self.has("dmm") and not self.mode.get().startswith("mA"):
            msg.append(T("멀티미터가 mA 범위가 아니어서 전류가 거의 흐르지 않습니다.", "The multimeter is not on a mA range: hardly any current flows."))
        if self.has("tube") and not self.filled:
            msg.append(T("시험관을 채워 거꾸로 세우세요.", "Fill the tube and turn it over the electrode."))
        self.warn.config(text="\n".join(msg))
        self.refresh()

    def refresh(self):
        self.rel.config(text=T("공 잡기", "Catch the ball") if self.amp > 0 else T("공 놓기 (약 5°)", "Let go (about 5°)"))
        self.wb.config(text=T("정지", "Stop") if self.watch_run else T("시작", "Start"))
        self.wl.config(text="%.2f s" % self.watch_t)
        self.pol.config(text=T("관 속: 음극 (H₂)", "In the tube: cathode (H₂)") if self.cathode else T("관 속: 양극 (O₂)", "In the tube: anode (O₂)"))
        self.vl.config(text="%.1f V" % self.V if self.psu.get() else "OFF")
        self.ml.config(text=self.show())
        self.clk.config(text="%d:%02d" % (self.clock // 60, self.clock % 60))
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        ph = self.ph
        # the wire's scale at the clamp
        jx, jy, ppm = 80, 170, 9.0
        cv.create_rectangle(jx - 22, 20, jx + 14, 320, fill="#fbfaf2", outline="#bbb")
        if self.has("pend"):
            for m in range(int(self.mark - 17), int(self.mark + 18)):
                y = jy - (m - self.mark) * ppm
                if y < 22 or y > 318:
                    continue
                L = 14 if m % 10 == 0 else (10 if m % 5 == 0 else 6)
                cv.create_line(jx + 14 - L, y, jx + 14, y, fill="#222", width=2 if m % 10 == 0 else 1)
                if m % 10 == 0:
                    cv.create_text(jx - 9, y, text=str(m), font=("Helvetica", 8, "bold"))
            cv.create_line(jx + 17, 20, jx + 17, 320, fill="#7a4a2a", width=3)
        cv.create_rectangle(jx - 40, jy - 36, jx + 40, jy, fill="#e8e2d0", outline="#555")
        cv.create_line(jx - 46, jy, jx + 46, jy, fill="#c0392b")
        cv.create_text(jx, jy - 18, text=T("집게", "clamp"))
        # the pendulum
        px, py, Lp = 290, 30, 270
        cv.create_rectangle(px - 70, py - 10, px + 70, py, fill="#b8bec5", outline="")
        if self.has("pend"):
            a = self.amp * math.sin(self.phase)
            bx, by = px + Lp * math.sin(a), py + Lp * math.cos(a)
            cv.create_line(px, py, bx, by, fill="#7a4a2a", width=2)
            cv.create_oval(bx - 10, by - 10, bx + 10, by + 10, fill="#c9ced3", outline="#555")
        for g in range(-10, 11):
            aa = math.radians(g)
            r0, r1 = Lp + (8 if g % 5 == 0 else 12), Lp + 18
            cv.create_line(px + r0 * math.sin(aa), py + r0 * math.cos(aa), px + r1 * math.sin(aa), py + r1 * math.cos(aa), fill="#555")
        # the tube's scale round the water surface
        tx, w = 520, 90
        cv.create_rectangle(tx - w / 2, 20, tx + w / 2, 340, fill="#e8f2fa", outline="#778")
        if self.has("tube") and self.filled:
            lev = self.level()
            c0 = max(0, int(round(lev / 10.0)) * 10 - 15)
            Y = lambda m: 20 + (m - c0) * 10.0
            yl = Y(lev)
            if yl < 340:
                cv.create_rectangle(tx - w / 2, max(20, yl), tx + w / 2, 340, fill="#a8c8e0", outline="")
            for m in range(c0, c0 + 33):
                y = Y(m)
                if y > 340:
                    break
                L = 30 if m % 10 == 0 else (20 if m % 5 == 0 else 12)
                cv.create_line(tx - w / 2, y, tx - w / 2 + L, y, fill="#111", width=2 if m % 10 == 0 else 1)
                if m % 10 == 0:
                    cv.create_text(tx - w / 2 + 42, y, text=str(m), font=("Helvetica", 9, "bold"))
        else:
            cv.create_text(tx, 180, text=T("시험관을\n채우세요", "fill the\ntube"), justify="center")
        cv.create_text(tx, 352, text=T("시험관 눈금 (닫힌 끝이 위)", "tube scale (closed end up)"), font=("Helvetica", 9))
        # the paper strip on the graph paper
        x0, y0, n, g = 30, 400, 60, 11.5
        if self.has("paper"):
            for i in range(n + 1):
                cv.create_line(x0 + i * g, y0, x0 + i * g, y0 + 12 * g, fill="#d77" if i % 10 == 0 else ("#e9a" if i % 5 == 0 else "#f3d0c8"))
            for j in range(13):
                cv.create_line(x0, y0 + j * g, x0 + n * g, y0 + j * g, fill="#d77" if j % 10 == 0 else ("#e9a" if j % 5 == 0 else "#f3d0c8"))
            C = math.pi * ph.Dout / ph.u + ph.strip
            cv.create_rectangle(x0 + 5 * g, y0 + 5 * g, x0 + (9 + C) * g, y0 + 8 * g, fill="#ffffff", outline="#888")
            cv.create_line(x0 + (5 + C) * g, y0 + 4.6 * g, x0 + (5 + C) * g, y0 + 8.4 * g, fill="#1b3fa0", width=2)
            cv.create_text(x0, y0 + 13 * g + 10, anchor="w", text=T("종이띠: 시작 끝에서 파란 표시까지가 바깥 둘레", "paper strip: from its start to the blue mark is the outer circumference"), font=("Helvetica", 9))


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
