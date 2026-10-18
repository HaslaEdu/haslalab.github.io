#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  11th Asian Physics Olympiad  (APhO 2010, Taipei, Taiwan)
  Experimental Problem 1 :  MAGNETIC FORCE PROBE
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* A sine-wave generator drives a brass reed with a tip magnet (MT) and a
  mirror; a laser beam reflected off the mirror draws a line on the screen.
  The reed is a driven damped oscillator; its amplitude settles over
  ~Q/(pi f) seconds after every change of frequency.
* The extra stiffness from a magnet below comes from the curvature of the
  dipole-dipole energy of two N-to-N magnets (finite-size offset r0), so the
  resonance rises steeply as MC approaches and dips a little off to the
  side, where the force turns attractive.
* The bench shows only the generator display, the screen scale, the
  vertical slider scale and the stage scale.  f_R0, Q, the depths and the
  positions of the hidden magnets are never displayed.
* Hidden truths are randomised every session.
* Standard library only (tkinter).

    Run:   python3 apho2010_E1_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line


def u_dd(z, p):
    return (2 * z * z - p * p) / (z * z + p * p) ** 2.5


def s2(z, p):
    h = 1e-3
    return (u_dd(z + h, p) - 2 * u_dd(z, p) + u_dd(z - h, p)) / (h * h)


# --------------------------------------------------------------------------
#  Physics core  (cm, Hz)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.f0 = r.uniform(26.4, 27.6)       # bare reed resonance [Hz]
        self.Q = r.uniform(68, 92)
        self.A1 = r.uniform(6.2, 7.4)         # spot amplitude at resonance, full drive [cm]
        self.K0 = r.uniform(6.2, 8.2)         # shift at a nominal 0.40 cm on axis [Hz]
        self.r0 = r.uniform(0.56, 0.68)       # magnet centres beyond the faces [cm]
        self.zTip = r.uniform(6.30, 6.50)     # tip-magnet bottom on the slider scale [cm]
        self.zBox = r.uniform(4.92, 5.02)     # black-box lid on the slider scale [cm]
        self.dA = r.uniform(0.12, 0.22)       # depths of MA and MB [cm]
        self.dB = r.uniform(0.28, 0.42)
        self.AB = r.uniform(2.7, 3.3)         # their spacing [cm]
        self.yA = r.uniform(2.0, 2.3)         # stage reading with MA under the tip [cm]
        self.yB = self.yA + self.AB
        self.aim = r.uniform(-0.6, 0.6)       # laser tilt that hits the mirror [deg]
        self.sn = s2(0.40 + self.r0, 0.0)
        self.re, self.im = 0.0, 0.0

    def shift(self, ztip, zc, box, y):
        s = 0.0
        if box:
            for yy, dd in ((self.yA, self.dA), (self.yB, self.dB)):
                s += s2(ztip - self.zBox + dd + self.r0, abs(y - yy))
        elif zc is not None:
            s += s2(ztip - zc + self.r0, 0.02)
        return self.K0 * s / self.sn

    def step(self, dt, fR, f, drive):
        re = im = 0.0
        if drive > 0 and f > 0:
            a = self.A1 * drive * fR * fR / self.Q
            dr, di = fR * fR - f * f, f * fR / self.Q
            den = dr * dr + di * di
            re, im = a * dr / den, -a * di / den
        k = 1 - math.exp(-dt * math.pi * fR / self.Q)
        self.re += (re - self.re) * k
        self.im += (im - self.im) * k

    def amp(self):
        return math.hypot(self.re, self.im)


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_track(cv, x, y, sc=1.0):
    cv.create_rectangle(x - 300 * sc, y - 8 * sc, x + 300 * sc, y + 8 * sc, fill="#3d434b", outline="#22262b")


def art_gen(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 50 * s, y - 30 * s, x + 50 * s, y + 30 * s, fill="#dcdfe2", outline="#8a8f96")
    cv.create_rectangle(x - 42 * s, y - 22 * s, x - 2 * s, y - 4 * s, fill="#0d1f12", outline="")
    for dx in (14, 34):
        cv.create_oval(x + (dx - 8) * s, y - 20 * s, x + (dx + 8) * s, y - 4 * s, fill="#2b2e33", outline="")


def art_cld(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 30 * s, y - 8 * s, x + 24 * s, y + 8 * s, fill="#2b2f35", outline="")
    cv.create_rectangle(x + 24 * s, y - 6 * s, x + 30 * s, y + 6 * s, fill="#c0392b", outline="")


def art_reed(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 30 * s, y - 14 * s, x, y + 14 * s, fill="#1f2226", outline="")
    cv.create_rectangle(x, y - 2 * s, x + 50 * s, y + 2 * s, fill="#c9a64a", outline="")
    cv.create_rectangle(x + 44 * s, y + 2 * s, x + 50 * s, y + 8 * s, fill="#c0392b", outline="")


def art_screen(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 6 * s, y - 50 * s, x + 6 * s, y + 50 * s, fill="#f6f4ee", outline="#999")


def art_slider(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 8 * s, y - 45 * s, x + 8 * s, y + 45 * s, fill="#e9e3cf", outline="#a99f80")
    cv.create_rectangle(x + 8 * s, y + 4 * s, x + 30 * s, y + 8 * s, fill="#8a9097", outline="")


def art_box(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 30 * s, y - 18 * s, x + 30 * s, y + 18 * s, fill="#191b1e", outline="#444")
    cv.create_line(x, y - 18 * s, x, y + 18 * s, fill="#ddd")


def art_wires(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 20 * s, y - 10 * s, x + 20 * s, y + 10 * s, outline="#c0392b", width=2)
    cv.create_oval(x - 14 * s, y - 6 * s, x + 14 * s, y + 6 * s, outline="#202327", width=2)


ART = {"track": art_track, "gen": art_gen, "cld": art_cld, "reed": art_reed, "screen": art_screen,
       "slider": art_slider, "box": art_box, "wires": art_wires}

PARTS = [
    ("track",  ("[C-A] 광학 레일", "[C-A] Optical track"), []),
    ("cld",    ("[C-C] 평행광 레이저", "[C-C] Collimated laser diode"), ["track"]),
    ("reed",   ("[I-I] 황동 리드 + 구동 상자", "[I-I] Brass reed + driving box"), ["track"]),
    ("screen", ("[I-J] 진폭 측정 스크린", "[I-J] Amplitude screen"), ["track"]),
    ("gen",    ("[C-D] 사인파 발생기", "[C-D] Sine-wave generator"), []),
    ("wires",  ("[C-F] 전선 (BNC, 5 V)", "[C-F] Wires (BNC, 5 V)"), ["gen", "cld", "reed"]),
    ("slider", ("[I-K] 수직 슬라이더 + 자석 MC", "[I-K] Vertical slider + magnet MC"), ["track"]),
    ("box",    ("[I-H] 블랙박스 + 1차원 이동대", "[I-H] Black box on a 1-D stage"), ["track"]),
]
ZONES = {
    "track":  (380, 400, 600, 16),
    "cld":    (180, 330, 60, 20),
    "reed":   (400, 350, 80, 30),
    "screen": (600, 320, 20, 100),
    "gen":    (640, 550, 100, 60),
    "wires":  (520, 520, 40, 24),
    "slider": (470, 360, 20, 90),
    "box":    (440, 430, 60, 36),
}
SCENE_TITLE = ("그림 I-A-1, I-B-1의 장치 — 레이저, 리드, 스크린은 레일 위에",
               "The set-up of Figs. I-A-1 and I-B-1 — laser, reed and screen on the track")
APP_TITLE = ("APhO 2010 실험 1 — 자기력 탐침", "APhO 2010 Experiment 1 — Magnetic force probe")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.pwr, self.f, self.ampl = False, 0.0, 5
        self.aim, self.cover = 0.0, True
        self.dz, self.zc, self.y = 0.0, 2.0, 0.5
        self.box_in = False
        self.t = 0.0
        self.build()
        self.refresh()

    def ztip(self):
        return self.ph.zTip + self.dz

    def touching(self):
        if self.box_in:
            return self.ztip() - self.ph.zBox < 0.05
        return "slider" in self.app.placed and self.ztip() - self.zc < 0.05

    def fR(self):
        zc = self.zc if "slider" in self.app.placed else None
        return self.ph.f0 + self.ph.shift(self.ztip(), zc, self.box_in, self.y)

    def beam(self):
        return self.pwr and {"cld", "wires"} <= self.app.placed

    def hits(self):
        return self.beam() and "reed" in self.app.placed and abs(self.aim - self.ph.aim) < 0.35

    def drive(self):
        ok = self.pwr and {"reed", "wires"} <= self.app.placed and not self.cover and not self.touching()
        return self.ampl / 10.0 if ok else 0.0

    # ---- UI ---------------------------------------------------------------
    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("사인파 발생기", "Sine-wave generator"))
        f.pack(fill="x", pady=2)
        self.f_lbl = tk.Label(f, text="--.-- Hz", font=("Courier", 18, "bold"), bg="#0d1f12", fg="#5cff7a", width=11)
        self.f_lbl.pack(pady=2)
        stepper(f, "FREQ", [("−1", lambda: self.setf(-1)), ("−0.1", lambda: self.setf(-0.1)), ("−0.05", lambda: self.setf(-0.05)),
                            ("+0.05", lambda: self.setf(0.05)), ("+0.1", lambda: self.setf(0.1)), ("+1", lambda: self.setf(1))])
        self.a_row = stepper(f, "AMPL ADJ", [("−", lambda: self.seta(-1)), ("+", lambda: self.seta(1))])
        self.a_lbl = ttk.Label(self.a_row, text="")
        self.a_lbl.pack(side="left", padx=4)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.pwr_btn = ttk.Button(row, text=T("전원 켜기", "Switch on"), command=self.toggle)
        self.pwr_btn.pack(side="left", padx=2)
        ttk.Button(row, text="RESET", command=self.reset).pack(side="left", padx=2)

        f = ttk.LabelFrame(ctl, text=T("레이저 · 리드", "Laser · reed"))
        f.pack(fill="x", pady=2)
        stepper(f, T("레이저 기울기", "Laser tilt"), [("▲0.1°", lambda: self.setaim(0.1)), ("▼0.1°", lambda: self.setaim(-0.1))])
        self.cov_btn = ttk.Button(f, text=T("보호 종이 떼기", "Remove the paper cover"), command=self.uncover)
        self.cov_btn.pack(anchor="w", padx=2)
        stepper(f, T("리드 높이", "Reed height"), [("▼1mm", lambda: self.setdz(-0.1)), ("▼0.1", lambda: self.setdz(-0.01)),
                                                ("▲0.1", lambda: self.setdz(0.01)), ("▲1mm", lambda: self.setdz(0.1))])

        f = ttk.LabelFrame(ctl, text=T("자석 MC · 블랙박스", "Magnet MC · black box"))
        f.pack(fill="x", pady=2)
        stepper(f, T("MC 높이", "MC height"), [("▼1cm", lambda: self.setzc(-1)), ("▼1mm", lambda: self.setzc(-0.1)),
                                             ("▲1mm", lambda: self.setzc(0.1)), ("▲1cm", lambda: self.setzc(1))])
        self.box_btn = ttk.Button(f, text=T("블랙박스를 리드 끝 아래에", "Black box under the tip"), command=self.toggle_box)
        self.box_btn.pack(anchor="w", padx=2)
        stepper(f, T("이동대 y", "Stage y"), [("−1cm", lambda: self.sety(-1)), ("−1mm", lambda: self.sety(-0.1)), ("−0.5", lambda: self.sety(-0.05)),
                                            ("+0.5", lambda: self.sety(0.05)), ("+1mm", lambda: self.sety(0.1)), ("+1cm", lambda: self.sety(1))])

        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.ents = {}
        for k, lab in (("A", T("A (cm)", "A (cm)")), ("z", T("z / y (cm)", "z / y (cm)"))):
            ttk.Label(row, text=lab).pack(side="left")
            e = ttk.Entry(row, width=7)
            e.pack(side="left", padx=2)
            self.ents[k] = e
        ttk.Button(f, text=T("진동수와 함께 적기", "Record with the frequency"), command=self.record).pack(fill="x", pady=2)
        self.sheet = DataSheet(f, [("f", "f (Hz)", 80), ("A", "A (cm)", 80), ("z", "z / y (cm)", 90)], height=7)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=360)
        self.warn.pack(anchor="w")

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        row = ttk.Frame(right)
        row.pack(fill="x")
        c1 = ttk.Frame(row)
        c1.pack(side="left")
        ttk.Label(c1, text=T("스크린 — 진폭을 눈금으로 읽으시오", "Screen — read the amplitude"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.scr = tk.Canvas(c1, width=300, height=640, bg="#2a2d33", highlightthickness=0)
        self.scr.pack()
        c2 = ttk.Frame(row)
        c2.pack(side="left", padx=6)
        ttk.Label(c2, text=T("리드 끝 (옆에서) — 슬라이더 눈금", "Reed tip (side) — slider scale"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.tip = tk.Canvas(c2, width=560, height=330, bg="#eef0ee", highlightthickness=0)
        self.tip.pack()
        ttk.Label(c2, text=T("블랙박스 (위에서) — 이동대 눈금", "Black box (above) — stage scale"), font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(6, 0))
        self.boxv = tk.Canvas(c2, width=560, height=280, bg="#2a2d33", highlightthickness=0)
        self.boxv.pack()

    # ---- controls -----------------------------------------------------------
    def setf(self, d):
        if self.pwr:
            self.f = max(0.0, min(99.99, round(self.f + d, 2)))

    def seta(self, d):
        self.ampl = max(0, min(10, self.ampl + d))

    def toggle(self):
        if "gen" not in self.app.placed:
            return
        self.pwr = not self.pwr
        if not self.pwr:
            self.f = 0.0
        self.pwr_btn.config(text=T("전원 끄기", "Switch off") if self.pwr else T("전원 켜기", "Switch on"))

    def reset(self):
        if self.pwr:
            self.f = 0.0

    def setaim(self, d):
        self.aim = round(self.aim + d, 2)

    def uncover(self):
        if "reed" in self.app.placed:
            self.cover = False
            self.cov_btn.state(["disabled"])

    def setdz(self, d):
        self.dz = max(-2.5, min(1.5, round(self.dz + d, 2)))

    def setzc(self, d):
        if not self.box_in:
            self.zc = max(0.3, min(10.5, round(self.zc + d, 2)))

    def toggle_box(self):
        if "box" not in self.app.placed:
            return
        self.box_in = not self.box_in
        self.box_btn.config(text=T("블랙박스 치우기", "Take the box away") if self.box_in else T("블랙박스를 리드 끝 아래에", "Black box under the tip"))

    def sety(self, d):
        if self.box_in:
            self.y = max(0.0, min(7.5, round(self.y + d, 2)))

    def record(self):
        self.sheet.add(("%.2f" % self.f if self.pwr else "--", self.ents["A"].get() or "?", self.ents["z"].get() or "?"))

    # ---- loop -------------------------------------------------------------
    def tick(self, dt):
        self.t += dt
        fr = self.fR()
        for _ in range(4):
            self.ph.step(dt / 4, fr, self.f, self.drive())
        self.refresh()

    def refresh(self):
        self.f_lbl.config(text=("%5.2f Hz" % self.f) if self.pwr else "--.-- Hz")
        self.a_lbl.config(text="%d / 10" % self.ampl)
        msgs = []
        if self.cover and "reed" in self.app.placed:
            msgs.append(T("리드에 보호 종이가 씌워져 있습니다.", "The paper cover is still on the reed."))
        if self.beam() and "reed" in self.app.placed and not self.hits():
            msgs.append(T("레이저 빛이 거울을 벗어났습니다 — 기울기를 조절하시오.", "The beam misses the mirror — adjust the tilt."))
        if self.touching():
            msgs.append(T("리드 끝 자석이 아래 것에 닿았습니다.", "The tip magnet touches what is below it."))
        self.warn.config(text="\n".join(msgs))
        self.draw_screen()
        self.draw_tip()
        self.draw_box()

    def draw_screen(self):
        cv = self.scr
        cv.delete("all")
        if "screen" not in self.app.placed:
            return
        z, cx, cy = 30.0, 150, 320
        cv.create_rectangle(cx - 70, 20, cx + 70, 620, fill="#f6f4ee", outline="#bbb")
        for mm in range(-95, 96):
            yy = cy - mm / 10.0 * z
            ln = 22 if mm % 10 == 0 else 14 if mm % 5 == 0 else 7
            cv.create_line(cx - 70, yy, cx - 70 + ln, yy, fill="#333")
            if mm % 10 == 0:
                cv.create_text(cx - 70 + 34, yy, text=str(mm // 10), font=("Helvetica", 8))
        if not self.beam():
            cv.create_text(cx, 10, text=T("레이저 꺼짐", "laser off"), fill="#c9d1d8")
            return
        if not self.hits():
            return
        zs = 1.8 + (self.aim - self.ph.aim) * 3.0
        A = self.ph.amp()
        y0, y1 = cy - (zs + A) * z, cy - (zs - A) * z
        cv.create_rectangle(cx + 20, y0, cx + 30, y1, fill="#ff9a92", outline="")
        cv.create_oval(cx + 19, y0 - 5, cx + 31, y0 + 5, fill="#ff3020", outline="")
        cv.create_oval(cx + 19, y1 - 5, cx + 31, y1 + 5, fill="#ff3020", outline="")

    def draw_tip(self):
        cv = self.tip
        cv.delete("all")
        z = 60.0
        X = lambda x: 280 + x * z
        Y = lambda h: 110 - (h - self.ztip()) * z
        if self.box_in:
            cv.create_rectangle(X(-2.2), Y(self.ph.zBox), X(3.2), 330, fill="#191b1e", outline="")
            cv.create_line(X(-2.2), Y(self.ph.zBox), X(3.2), Y(self.ph.zBox), fill="#e8e8e0")
        if "slider" in self.app.placed:
            x0 = X(-2.6)
            cv.create_rectangle(x0 - 28, Y(11), x0, Y(0), fill="#e9e3cf", outline="#a99f80")
            for mm in range(0, 111):
                ln = 18 if mm % 10 == 0 else 12 if mm % 5 == 0 else 7
                cv.create_line(x0 - ln, Y(mm / 10.0), x0, Y(mm / 10.0), fill="#222")
                if mm % 10 == 0:
                    cv.create_text(x0 - 22, Y(mm / 10.0) - 7, text=str(mm // 10), font=("Helvetica", 8, "bold"))
        if "reed" in self.app.placed:
            yt = Y(self.ztip())
            cv.create_rectangle(X(-6), yt - 0.35 * z, X(0.4), yt - 0.3 * z, fill="#c9a64a", outline="")
            cv.create_rectangle(X(-0.15), yt - 0.3 * z, X(0.15), yt, fill="#c0392b", outline="#7a1c17")
            if self.cover:
                cv.create_rectangle(X(-6), yt - 0.5 * z, X(0.6), yt - 0.18 * z, fill="#f2efe6", outline="#bbb")
        if "slider" in self.app.placed and not self.box_in:
            cv.create_rectangle(X(-0.15), Y(self.zc), X(0.15), Y(self.zc - 0.3), fill="#c0392b", outline="#7a1c17")
            cv.create_rectangle(X(-2.6), Y(self.zc - 0.3), X(0.15), Y(self.zc - 0.4), fill="#8a9097", outline="")

    def draw_box(self):
        cv = self.boxv
        cv.delete("all")
        if not self.box_in:
            cv.create_text(280, 140, text=T("블랙박스를 리드 끝 아래에 놓으면 보입니다", "put the black box under the tip to see this"), fill="#9aa3ab")
            return
        z, cx, cy = 28.0, 250, 120
        Y = lambda q: cy + (self.y - self.ph.yA + q) * z
        cv.create_rectangle(cx - 3.2 * z, Y(-4.2), cx + 3.2 * z, Y(5.8), fill="#191b1e", outline="#444")
        cv.create_line(cx, Y(-4.2), cx, Y(5.8), fill="#e8e8e0", width=2)
        cv.create_line(cx - 1.5 * z, Y(0), cx + 1.5 * z, Y(0), fill="#e8e8e0", width=2)
        cv.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, outline="#ffcf3a", width=2)
        sx = cx + 5 * z
        cv.create_rectangle(sx, 0, sx + 1.4 * z, 280, fill="#c3c8cd", outline="")
        for mm in range(-50, 121):
            yy = cy + (self.y - mm / 10.0) * z
            if yy < -5 or yy > 285:
                continue
            ln = 16 if mm % 10 == 0 else 11 if mm % 5 == 0 else 6
            cv.create_line(sx, yy, sx + ln, yy, fill="#222")
            if mm % 10 == 0:
                cv.create_text(sx + 26, yy, text=str(mm // 10), font=("Helvetica", 8, "bold"))
        cv.create_polygon(sx - 2, cy, sx - 14, cy - 6, sx - 14, cy + 6, fill="#ffcf3a")


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
