#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  40th International Physics Olympiad  (IPhO 2009, Merida, Mexico)
  Experimental Problem 1 :  WAVELENGTH OF A DIODE LASER
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The laser beam (radius a), turned by the mirror, passes a lens of a
  few cm focal length; its focus F is a point source.  A razor blade on
  a 10 cm rail cuts the cone before (Case I) or after (Case II) F.
* The pattern on the screen is the Fresnel field behind a straight edge,
  with the edge wave given a quarter turn through the focus, so that the
  dark fringes satisfy (n + 5/8) lambda in Case I and (n + 7/8) lambda
  in Case II, exactly as in the problem.
* The mirror's knob tilts the beam: off the lens's centre the cone is
  deflected and the fringes' origin moves.  The blade must be brought
  across the cone with its screw.
* lambda, f, the beam radius and the mirror's start are hidden and
  randomised.  Standard library only (tkinter).

    Run:   python3 ipho2009_E1_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line


# --------------------------------------------------------------------------
#  Physics core  (cm unless marked)
# --------------------------------------------------------------------------
FW, FD = 12.0, 0.002


def _tables():
    n = int(round(2 * FW / FD)) + 1
    C, S = [0.0] * n, [0.0] * n
    i0 = int(round(FW / FD))
    for i in range(i0 + 1, n):
        a, b = (i - 1 - i0) * FD, (i - i0) * FD
        C[i] = C[i - 1] + FD * (math.cos(math.pi * a * a / 2) + math.cos(math.pi * b * b / 2)) / 2
        S[i] = S[i - 1] + FD * (math.sin(math.pi * a * a / 2) + math.sin(math.pi * b * b / 2)) / 2
        C[2 * i0 - i], S[2 * i0 - i] = -C[i], -S[i]
    return C, S


FC, FS = _tables()


def fres(w):
    if w >= FW - 0.01:
        return 0.5, 0.5
    if w <= -FW + 0.01:
        return -0.5, -0.5
    f = (w + FW) / FD
    i = int(f)
    t = f - i
    return FC[i] * (1 - t) + FC[i + 1] * t, FS[i] * (1 - t) + FS[i + 1] * t


def edgeI(w, gouy):
    """behind a straight edge, relative to the free wave (w > 0 lit); a focus gives the edge wave a quarter turn"""
    c, s = fres(w)
    a, b = c + 0.5, s + 0.5
    ur, ui = (a + b) / 2, (b - a) / 2
    if not gouy:
        return ur * ur + ui * ui
    H = 1.0 if w > 0 else 0.0
    dr, di = ur - H, ui
    vr, vi = H - di, dr
    return vr * vr + vi * vi


class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.lam = r.uniform(645, 672) * 1e-9
        self.f = r.uniform(2.6, 3.4)
        self.beam = r.uniform(0.10, 0.14)
        self.knob0 = r.uniform(-0.08, 0.08)        # the mirror's start: the beam's miss at the lens per cm of knob error
        self.tapeOff = r.uniform(-0.04, 0.04)


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_laser(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 45 * s, y - 8 * s, x + 35 * s, y + 8 * s, fill="#2a2d33", outline="")
    cv.create_oval(x + 32 * s, y - 3 * s, x + 38 * s, y + 3 * s, fill="#c9ced3", outline="")


def art_mirror(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 16 * s, y - 16 * s, x + 16 * s, y + 16 * s, fill="#2a2d33", outline="")
    cv.create_rectangle(x - 12 * s, y - 12 * s, x + 12 * s, y + 12 * s, fill="#c9d6de", outline="")


def art_lens(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 14 * s, y - 14 * s, x + 14 * s, y + 14 * s, fill="#d6eaf0", outline="#3a3d42", width=3)


def art_rail(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 50 * s, y + 6 * s, x + 50 * s, y + 14 * s, fill="#c9ced3", outline="#888")
    cv.create_rectangle(x - 4 * s, y - 20 * s, x + 4 * s, y + 6 * s, fill="#d7dbe0", outline="#888")


def art_screen(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 40 * s, y - 28 * s, x + 40 * s, y + 24 * s, fill="#f4f4f0", outline="#999")
    cv.create_rectangle(x - 40 * s, y + 24 * s, x + 40 * s, y + 32 * s, fill="#c9ced3", outline="")


def art_tool(col):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_oval(x - 18 * s, y - 18 * s, x + 18 * s, y + 18 * s, fill=col, outline="#555")
    return art


ART = {"laser": art_laser, "mirror": art_mirror, "lens": art_lens, "rail": art_rail, "screen": art_screen,
       "tape": art_tool("#f2c14e"), "caliper": art_tool("#c9ced3"), "magnifier": art_tool("#d6eaf0")}
PARTS = [
    ("laser",     ("[A] 다이오드 레이저", "[A] Diode laser"), []),
    ("mirror",    ("[B] 거울 (손잡이 2개)", "[B] Mirror (two knobs)"), []),
    ("lens",      ("[C] 렌즈", "[C] Lens"), []),
    ("rail",      ("[D] 면도날 + 레일", "[D] Razor blade + rail"), []),
    ("screen",    ("[E] 스크린 (1/20 mm 눈금)", "[E] Screen (1/20 mm scale)"), []),
    ("tape",      ("[I] 줄자", "[I] Measuring tape"), []),
    ("caliper",   ("[H] 캘리퍼", "[H] Caliper"), []),
    ("magnifier", ("[F] 돋보기", "[F] Magnifying glass"), []),
]
ZONES = {"laser": (150, 160, 90, 30), "mirror": (620, 160, 40, 40), "lens": (560, 250, 30, 30), "rail": (470, 270, 110, 40),
         "screen": (180, 330, 90, 70), "tape": (380, 420, 40, 40), "caliper": (480, 420, 40, 40), "magnifier": (580, 420, 40, 40)}
SCENE_TITLE = ("나무 광학 테이블: 레이저 → 거울 → 렌즈 → 면도날 → 스크린", "Wooden optical table: laser → mirror → lens → blade → screen")
APP_TITLE = ("IPhO 2009 실험 1 — 다이오드 레이저의 파장", "IPhO 2009 Experiment 1 — Wavelength of a diode laser")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.laser = tk.BooleanVar(value=False)
        self.knob = 0.0              # the mirror's H knob (deg from its start)
        self.railAt = 2.0            # the rail's zero, cm after the lens
        self.u = 50.0                # the carriage, mm along the rail
        self.e = 1.5                 # the blade's edge across the beam, mm
        self.Ls = 70.0               # lens to screen, cm
        self.cur = 50.0              # the screen cursor, mm
        self.zoom = 1.0
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def geom(self):
        """the cone: its axis's sideways shift and the distances along it (cm)"""
        ph = self.ph
        if not (self.laser.get() and self.has("laser") and self.has("mirror")):
            return None
        miss = (ph.knob0 + self.knob * 0.087) * 30.0          # the beam's miss at the lens: 30 cm lever from the mirror
        lens = self.has("lens") and abs(miss) < 0.9
        sF = ph.f if lens else None
        tb = self.railAt + self.u / 10.0
        tilt = -miss / ph.f if lens else 0.0                  # off the lens's centre the cone is turned
        g = {"lens": lens, "sF": sF, "tb": tb, "ts": self.Ls, "miss": miss}
        g["hc"] = (miss + tilt * (tb - 0)) if lens else miss
        g["xc"] = (miss + tilt * self.Ls) if lens else miss
        g["R"] = abs(self.Ls - sF) * ph.beam / ph.f if lens else ph.beam
        g["rb"] = max(0.0015, abs(tb - sF) * ph.beam / ph.f) if lens else ph.beam
        return g

    def fringe(self, g, x):
        if not self.has("rail"):
            return 1.0
        lam = self.ph.lam
        e1 = self.e / 10.0 - g["hc"]
        if not g["lens"]:
            Lm = (g["ts"] - g["tb"]) / 100.0
            return edgeI((e1 - x + g["xc"]) / 100.0 * math.sqrt(2 / (lam * Lm)), False)
        sF, tb, ts = g["sF"], g["tb"], g["ts"]
        if abs(tb - sF) < 0.002:
            return 1.0 if x - g["xc"] < 0 else 0.0
        L0, Lb = (ts - sF) / 100.0, (ts - tb) / 100.0
        before = tb < sF
        M = (ts - sF) / (tb - sF)
        xb = g["xc"] + M * e1
        K = 1 / L0 - 1 / Lb if before else 1 / Lb - 1 / L0
        k = math.sqrt(2 * abs(K) / lam) / 100.0
        return edgeI((x - xb) * k, True) if before else edgeI((xb - x) * k, False)

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("레이저 · 거울", "Laser · mirror"))
        f.pack(fill="x", pady=2)
        ttk.Checkbutton(f, text=T("레이저 켜기", "Laser on"), variable=self.laser).pack(anchor="w")
        stepper(f, T("거울 손잡이 H", "Mirror knob H"), [("−0.5°", lambda: self.turn(-0.5)), ("−0.05°", lambda: self.turn(-0.05)), ("+0.05°", lambda: self.turn(0.05)), ("+0.5°", lambda: self.turn(0.5))])
        f = ttk.LabelFrame(ctl, text=T("레일 · 면도날 · 스크린", "Rail · blade · screen"))
        f.pack(fill="x", pady=2)
        stepper(f, T("레일 위치 (렌즈 뒤)", "Rail (after the lens)"), [("−1 cm", lambda: self.mv("railAt", -1, 0, 8)), ("+1 cm", lambda: self.mv("railAt", 1, 0, 8))])
        stepper(f, T("받침대 (mm)", "Carriage (mm)"), [("−5", lambda: self.mv("u", -5, 0, 100)), ("−0.5", lambda: self.mv("u", -0.5, 0, 100)), ("−0.05", lambda: self.mv("u", -0.05, 0, 100)),
                                                    ("+0.05", lambda: self.mv("u", 0.05, 0, 100)), ("+0.5", lambda: self.mv("u", 0.5, 0, 100)), ("+5", lambda: self.mv("u", 5, 0, 100))])
        stepper(f, T("날 가로 (mm)", "Blade across (mm)"), [("◀0.5", lambda: self.mv("e", -0.5, -6, 6)), ("◀0.1", lambda: self.mv("e", -0.1, -6, 6)), ("◀0.02", lambda: self.mv("e", -0.02, -6, 6)),
                                                         ("0.02▶", lambda: self.mv("e", 0.02, -6, 6)), ("0.1▶", lambda: self.mv("e", 0.1, -6, 6)), ("0.5▶", lambda: self.mv("e", 0.5, -6, 6))])
        stepper(f, T("스크린 (렌즈에서)", "Screen (from the lens)"), [("−5 cm", lambda: self.mv("Ls", -5, 30, 90)), ("−1", lambda: self.mv("Ls", -1, 30, 90)), ("+1", lambda: self.mv("Ls", 1, 30, 90)), ("+5 cm", lambda: self.mv("Ls", 5, 30, 90))])
        f = ttk.LabelFrame(ctl, text=T("스크린 커서 · 돋보기", "Screen cursor · magnifier"))
        f.pack(fill="x", pady=2)
        stepper(f, "", [("−0.5", lambda: self.mv("cur", -0.5, 0, 100)), ("−0.05", lambda: self.mv("cur", -0.05, 0, 100)), ("+0.05", lambda: self.mv("cur", 0.05, 0, 100)), ("+0.5 mm", lambda: self.mv("cur", 0.5, 0, 100))])
        stepper(f, T("확대", "Zoom"), [("×1", lambda: self.setzoom(1)), ("×2", lambda: self.setzoom(2)), ("×4", lambda: self.setzoom(4))])
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.ent = [ttk.Entry(row, width=7) for _ in range(3)]
        for lab, e in zip(("n", "l (mm)", T("경우", "case")), self.ent):
            ttk.Label(row, text=lab).pack(side="left")
            e.pack(side="left", padx=1)
        ttk.Button(row, text=T("적기", "Record"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("n", "n", 50), ("l", "l (mm)", 90), ("c", T("경우", "case"), 70)], height=6)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=380)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("빔의 길(위에서) · 스크린(뒤에서, 1/20 mm 버니어) · 줄자 · 캘리퍼", "Beam (from above) · screen (from behind, 1/20 mm vernier) · tape · caliper"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    def turn(self, d):
        self.knob = round(self.knob + d, 3)

    def mv(self, k, d, lo, hi):
        setattr(self, k, max(lo, min(hi, round(getattr(self, k) + d, 3))))

    def setzoom(self, z):
        if z > 1 and not self.has("magnifier"):
            return
        self.zoom = z

    def record(self):
        self.sheet.add(tuple(e.get() for e in self.ent))

    def tick(self, dt):
        g = self.geom()
        msg = ""
        if self.laser.get() and g and not g["lens"] and self.has("lens"):
            msg = T("빔이 렌즈를 비켜 갑니다 — 거울 손잡이로 맞추세요.", "The beam misses the lens: steer it with the mirror's knob.")
        elif self.laser.get() and g and abs(g["xc"]) > 5.5 and self.has("screen"):
            msg = T("빛이 스크린을 비켜 갑니다 — 빔이 렌즈 가운데를 지나도록 거울을 맞추세요.", "The light misses the screen: bring the beam through the lens's centre with the mirror.")
        self.warn.config(text=msg)
        self.refresh()

    def refresh(self):
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        g = self.geom()
        # 1. the beam from above (not to scale across)
        cv.create_rectangle(10, 10, 750, 120, fill="#c99a62", outline="")
        z = 8.0
        X = lambda t: 70 + t * z
        cv.create_text(20, 22, anchor="w", text=T("렌즈 →", "lens →"), font=("Helvetica", 8))
        if self.has("lens"):
            cv.create_line(X(0), 40, X(0), 100, fill="#3a3d42", width=4)
        if self.has("rail"):
            cv.create_rectangle(X(self.railAt), 85, X(self.railAt + 10), 95, fill="#c9ced3", outline="#888")
            xb = X(self.railAt + self.u / 10)
            cv.create_line(xb, 70 - self.e * 2, xb, 50, fill="#2b6cb0", width=3)
        if self.has("screen"):
            cv.create_line(X(self.Ls), 30, X(self.Ls), 110, fill="#f4f4f0", width=5)
        if g:
            y = lambda off: 70 + off * 8
            if g["lens"]:
                cv.create_line(10, y(g["miss"]), X(0), y(g["miss"]), fill="red")
                for sg in (-1, 1):
                    cv.create_line(X(0), y(g["miss"] + sg * self.ph.beam), X(g["sF"]), y(g["miss"] - g["miss"] * 1.0), X(self.Ls), y(g["xc"] - sg * g["R"]), fill="#ff6a50")
            else:
                cv.create_line(10, y(g["miss"]), X(self.Ls), y(g["miss"]), fill="red")
        # 2. the screen from behind
        sx, sy, sw, sh = 20, 140, 720, 300
        cv.create_rectangle(sx, sy, sx + sw, sy + sh, fill="#b0aca4", outline="#777")
        W = 110.0 / self.zoom
        c0 = 50 if self.zoom == 1 else max(W / 2 - 5, min(105 - W / 2, self.cur))
        m0 = c0 - W / 2
        pxmm = sw / W
        if g and self.has("screen"):
            R = max(0.05, g["R"])
            amp = min(1.1, (1.5 / R) ** 2 * 0.4 + 0.75)
            step = 2
            for i in range(0, sw, step):
                mm = m0 + (i + 1) / pxmm
                x = (mm - 50) / 10.0
                fr = self.fringe(g, x)
                env = math.exp(-2 * (x - g["xc"]) ** 2 / (R * R)) * amp
                gg = min(1.0, fr * env * 0.8)
                col = "#%02x%02x%02x" % (int(176 + 79 * gg), int(172 - 112 * gg), int(164 - 119 * gg))
                cv.create_rectangle(sx + i, sy + 20, sx + i + step, sy + sh - 20, fill=col, outline="")
        # the scale and the vernier
        y0 = sy + sh + 4
        cv.create_rectangle(sx, y0, sx + sw, y0 + 50, fill="#c9ced3", outline="#888")
        for mm in range(int(math.ceil(m0)), int(m0 + W) + 1):
            if 0 <= mm <= 100:
                ln = 16 if mm % 10 == 0 else 11 if mm % 5 == 0 else 7
                X2 = sx + (mm - m0) * pxmm
                cv.create_line(X2, y0, X2, y0 + ln, fill="#111")
                if mm % 10 == 0:
                    cv.create_text(X2, y0 + 24, text=str(mm // 10), font=("Helvetica", 9, "bold"))
        cx = sx + (self.cur - m0) * pxmm
        for i in range(21):
            xx = cx + i * 0.95 * pxmm
            if xx < sx + sw:
                cv.create_line(xx, y0 + 50, xx, y0 + 50 - (12 if i % 10 == 0 else 9 if i % 5 == 0 else 6), fill="#111")
        cv.create_line(cx, sy, cx, y0 + 50, fill="#111")
        # 3. tape and caliper readings, drawn as their scales
        y1 = y0 + 60
        if self.has("tape") and self.has("rail") and self.has("screen"):
            Lt = (self.Ls - self.railAt - self.u / 10) + self.ph.tapeOff
            cv.create_rectangle(sx, y1, sx + 340, y1 + 40, fill="#f7e7a1", outline="#a77d12")
            mz = 340 / 60.0
            c0t = Lt * 10 - 30
            for mm in range(int(math.ceil(c0t)), int(c0t + 60) + 1):
                xx = sx + (mm - c0t) * mz
                cv.create_line(xx, y1, xx, y1 + (18 if mm % 10 == 0 else 12 if mm % 5 == 0 else 7), fill="#111")
                if mm % 10 == 0:
                    cv.create_text(xx, y1 + 28, text=str(mm // 10), font=("Helvetica", 8, "bold"))
            cv.create_rectangle(sx + 170, y1 - 4, sx + 340, y1 + 44, fill="#eeeeea", outline="#555")
            cv.create_text(sx + 255, y1 + 20, text=T("← 스크린 면 (줄자: 면도날→스크린, cm)", "← screen face (tape: blade→screen, cm)"), font=("Helvetica", 8))
        if self.has("rail"):
            rx = 400
            cv.create_rectangle(rx, y1, rx + 340, y1 + 22, fill="#c9ced3", outline="#888")
            rz = 340 / 110.0
            for mm in range(0, 101):
                xx = rx + (mm + 5) * rz
                cv.create_line(xx, y1, xx, y1 + (10 if mm % 10 == 0 else 7 if mm % 5 == 0 else 4), fill="#111")
                if mm % 20 == 0:
                    cv.create_text(xx, y1 + 16, text=str(mm), font=("Helvetica", 7))
            cx2 = rx + (self.u + 5) * rz
            cv.create_line(cx2, y1 - 8, cx2, y1 + 22, fill="#c0392b", width=2)
            if self.has("caliper"):
                # a magnified vernier of the carriage: 1/20 mm
                vz = 14.0
                cv.create_rectangle(rx, y1 + 26, rx + 340, y1 + 62, fill="#e9ecef", outline="#666")
                base = int(self.u) - 2
                for mm in range(base, base + 25):
                    xx = rx + 20 + (mm - base) * vz
                    if xx < rx + 336:
                        cv.create_line(xx, y1 + 26, xx, y1 + 26 + (12 if mm % 10 == 0 else 8 if mm % 5 == 0 else 5), fill="#111")
                        if mm % 10 == 0:
                            cv.create_text(xx, y1 + 42, text=str(mm), font=("Helvetica", 7))
                for i in range(21):
                    xx = rx + 20 + (self.u - base + i * 0.95) * vz
                    if xx < rx + 336:
                        cv.create_line(xx, y1 + 62, xx, y1 + 62 - (10 if i % 10 == 0 else 7 if i % 5 == 0 else 4), fill="#c0392b")


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
