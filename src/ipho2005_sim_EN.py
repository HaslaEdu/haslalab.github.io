#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  36th International Physics Olympiad  (IPhO 2005, Salamanca, Spain)
  Experimental Problem :  PLANCK'S CONSTANT IN THE LIGHT OF AN
                          INCANDESCENT LAMP
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The battery feeds the bulb through the 10-turn potentiometer (a
  loaded divider with contact resistance at its ends), the ammeter in
  series (its shunt depends on the range) and the voltmeter across the
  bulb.  The filament's temperature balances electrical power against
  radiation and conduction, with T = a R^0.83 fixed by the room.
* The light through the liquid filter (peak 590 nm) is Planck's law
  integrated over the filter's band; the LDR follows R = b E^-gamma,
  creeping towards its value over minutes.  The cover keeps the room's
  light out; the grey filter passes 51.2 %.
* The room's temperature, R_B0, gamma and the filament's losses are
  hidden and randomised.
* Standard library only (tkinter).

    Run:   python3 ipho2005_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line

C2 = 1.4388e-2
MODES = {"off": None, "Ω2k": ("ohm", 1999, 1, 0, "Ω"), "Ω20k": ("ohm", 19.99e3, 1e-3, 2, "kΩ"), "Ω200k": ("ohm", 199.9e3, 1e-3, 1, "kΩ"),
         "V200m": ("V", 0.1999, 1e3, 1, "mV"), "V2": ("V", 1.999, 1, 3, "V"), "V20": ("V", 19.99, 1, 2, "V"),
         "A2m": ("A", 1.999e-3, 1e3, 3, "mA", 100), "A20m": ("A", 19.99e-3, 1e3, 2, "mA", 10), "A200m": ("A", 199.9e-3, 1e3, 1, "mA", 1),
         "°C": ("T", 0, 1, 0, "°C")}


def filt(l):
    s = 21.2 if l < 590 else 25.5
    return 0.27 * math.exp(-((l - 590) / s) ** 2 / 2) + (0.004 * (l - 660) / 40 if l > 660 else 0)


# --------------------------------------------------------------------------
#  Physics core
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.T0, self.RB0 = r.uniform(294, 300), r.uniform(10.8, 12.2)
        self.kr, self.kc = r.uniform(5.2e-14, 6.0e-14), r.uniform(4e-6, 8e-6)
        self.gam, R115 = r.uniform(0.66, 0.74), r.uniform(4.6, 5.6) * 1e3
        self.rEnd, self.rBat, self.eBat, self.Rpot = r.uniform(0.6, 1.0), r.uniform(0.3, 0.8), r.uniform(12.3, 12.8), 1000 * r.uniform(0.98, 1.02)
        self.a = self.T0 / self.RB0 ** 0.83
        self.b = R115 * self.filtered(2100) ** self.gam

    def Rof(self, T):
        return (T / self.a) ** (1 / 0.83)

    @staticmethod
    def filtered(T):
        if T < 700:
            return 0.0
        s = 0.0
        for l in range(440, 761, 4):
            L = l * 1e-9
            s += filt(l) * 0.45 / (L ** 5 * (math.exp(min(700, C2 / (L * T))) - 1))
        return s * 4e-9

    @staticmethod
    def unfiltered(T):
        if T < 700:
            return 0.0
        s = 0.0
        for l in range(400, 1101, 10):
            L = l * 1e-9
            s += 0.45 / (L ** 5 * (math.exp(min(700, C2 / (L * T))) - 1))
        return s * 10e-9 * 0.12

    def circuit(self, turns, rA, rV):
        """(I through the ammeter, V across the bulb, I in the bulb, T)"""
        x, R, re = turns / 10.0, self.Rpot, self.rEnd
        lo, hi = x * R + re, (1 - x) * R + re + self.rBat
        Vth, Rth = self.eBat * lo / (lo + hi), lo * hi / (lo + hi)

        def at(T):
            RL = self.Rof(T)
            Rp = 1 / (1 / RL + (1 / rV if rV else 0))
            I = Vth / (Rth + rA + Rp)
            return RL, I, I * Rp
        a, b = self.T0, 3600.0
        for _ in range(60):
            T = (a + b) / 2
            RL, I, VL = at(T)
            IL = VL / RL
            if IL * IL * RL > self.kr * (T ** 4 - self.T0 ** 4) + self.kc * (T - self.T0):
                a = T
            else:
                b = T
        T = (a + b) / 2
        RL, I, VL = at(T)
        return I, VL, VL / RL, T


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def box_art(col, w, h):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_rectangle(x - w * s, y - h * s, x + w * s, y + h * s, fill=col, outline="#555")
    return art


def art_plat(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 40 * s, y - 10 * s, x + 40 * s, y + 18 * s, fill="#3a3d42", outline="")
    cv.create_oval(x - 34 * s, y - 22 * s, x + 34 * s, y + 4 * s, fill="#d9dde2", outline="#888")


ART = {"platform": art_plat, "cover": box_art("#1f2226", 32, 24), "pot": box_art("#2b6cb0", 22, 14), "battery": box_art("#2a2d33", 22, 14),
       "tube": box_art("#e8782a", 5, 22), "grey": box_art("#46464b", 10, 10), "dmmO": box_art("#e3b72d", 18, 28), "dmmV": box_art("#e3b72d", 18, 28),
       "dmmA": box_art("#e3b72d", 18, 28), "leads": box_art("#c0392b", 20, 4)}
PARTS = [
    ("platform", ("[1] 받침대 (전구·시험관 받침·LDR)", "[1] Platform (bulb, tube support, LDR)"), []),
    ("cover",    ("[2] 차광 덮개", "[2] Protecting cover"), ["platform"]),
    ("pot",      ("[3] 10회전 전위차계", "[3] 10-turn potentiometer"), []),
    ("battery",  ("[4] 12 V 배터리", "[4] 12 V battery"), []),
    ("leads",    ("[5·6] 연결 도선", "[5·6] Leads"), ["platform", "pot"]),
    ("dmmO",     ("[7] 저항계", "[7] Ohmmeter"), []),
    ("dmmV",     ("[8] 전압계", "[8] Voltmeter"), []),
    ("dmmA",     ("[9] 전류계", "[9] Ammeter"), []),
    ("tube",     ("[10] 시험관 (액체 필터)", "[10] Test tube (liquid filter)"), []),
    ("grey",     ("[12] 회색 필터", "[12] Grey filter"), []),
]
ZONES = {"platform": (200, 220, 90, 60), "cover": (200, 110, 70, 50), "pot": (420, 200, 50, 32), "battery": (560, 200, 50, 32), "leads": (420, 290, 44, 14),
         "dmmO": (120, 380, 40, 60), "dmmV": (330, 380, 40, 60), "dmmA": (450, 380, 40, 60), "tube": (620, 330, 14, 48), "grey": (660, 420, 24, 24)}
SCENE_TITLE = ("받침대 · 전위차계 · 배터리 · 멀티미터 셋 · 시험관", "Platform · potentiometer · battery · three multimeters · test tube")
APP_TITLE = ("IPhO 2005 실험 — 백열등 빛으로 재는 플랑크 상수", "IPhO 2005 Experiment — Planck's constant in the light of an incandescent lamp")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.turns = 0.0
        self.bat, self.cover, self.tube, self.grey, self.touch = (tk.BooleanVar(value=False) for _ in range(5))
        self.sup = random.uniform(25, 60)
        self.mode = {k: tk.StringVar(value="off") for k in ("dmmO", "dmmV", "dmmA")}
        self.speed = tk.IntVar(value=1)
        self.logR, self.T, self.clock = math.log(2e6), self.ph.T0, 0.0
        self.disp, self.disp_t = {k: "" for k in self.mode}, 0.0
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def r_meter(self, k):
        m = MODES[self.mode[k].get()]
        if not self.has(k) or not m:
            return float("inf")
        return m[5] if m[0] == "A" else (1e7 if m[0] == "V" else float("inf"))

    def circ(self):
        if not (self.has("platform") and self.has("pot") and self.has("leads") and self.has("battery") and self.bat.get()):
            return 0.0, 0.0, 0.0, self.ph.T0
        rA = self.r_meter("dmmA") if self.has("dmmA") else 0.0
        if rA == float("inf"):
            return 0.0, 0.0, 0.0, self.ph.T0
        rV = self.r_meter("dmmV") if self.has("dmmV") else float("inf")
        return self.ph.circuit(self.turns, rA, None if rV == float("inf") else rV)

    def ldr_target(self):
        ph = self.ph
        I, VL, IL, T = self.circ()
        self.T = T
        al = max(0.0, math.cos(math.radians(self.sup % 180))) ** 40
        E = 0.0
        if self.has("platform"):
            E = (ph.filtered(T) if self.tube.get() else ph.unfiltered(T) * 0.6 + ph.filtered(T)) * al * (1 if self.touch.get() else 0.35) * (0.512 if self.grey.get() else 1)
        G = (E ** ph.gam / ph.b if E > 0 else 0) + 1 / 2.2e6 + (0 if self.cover.get() else 1 / 1.4e3)
        return 1 / G

    def raw(self, k):
        m = MODES[self.mode[k].get()]
        if not self.has(k) or not m:
            return None
        if m[0] == "T":
            return self.ph.T0 - 273.15
        I, VL, IL, T = self.circ()
        if k == "dmmO":
            return math.exp(self.logR) if m[0] == "ohm" else 0.0
        if k == "dmmV":
            return VL if m[0] == "V" else (VL / m[5] if m[0] == "A" else float("inf"))
        return I if m[0] == "A" else (I * 1e7 if m[0] == "V" else float("inf"))

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("멀티미터", "Multimeters"))
        f.pack(fill="x", pady=2)
        self.lbl = {}
        for k, lab in (("dmmO", T("저항계", "Ohmmeter")), ("dmmV", T("전압계", "Voltmeter")), ("dmmA", T("전류계", "Ammeter"))):
            row = ttk.Frame(f)
            row.pack(fill="x")
            ttk.Label(row, text=lab, width=9).pack(side="left")
            self.lbl[k] = tk.Label(row, text="", font=("Courier", 14, "bold"), bg="#9fae8f", fg="#1b1d20", width=12)
            self.lbl[k].pack(side="left", padx=2)
            ttk.OptionMenu(row, self.mode[k], "off", *MODES.keys()).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("전위차계 · 배터리 · 덮개", "Potentiometer · battery · cover"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Checkbutton(row, text=T("배터리 선 꽂기", "Battery plugged in"), variable=self.bat).pack(side="left")
        ttk.Checkbutton(row, text=T("덮개 씌우기", "Cover on"), variable=self.cover).pack(side="left", padx=6)
        self.tl = ttk.Label(f, text="", font=("Courier", 12, "bold"))
        self.tl.pack(anchor="w")
        stepper(f, T("회전", "Turns"), [("−1", lambda: self.turn(-1)), ("−0.1", lambda: self.turn(-0.1)), ("−0.01", lambda: self.turn(-0.01)), ("−0.001", lambda: self.turn(-0.001))])
        stepper(f, "", [("+0.001", lambda: self.turn(0.001)), ("+0.01", lambda: self.turn(0.01)), ("+0.1", lambda: self.turn(0.1)), ("+1", lambda: self.turn(1))])
        f = ttk.LabelFrame(ctl, text=T("받침대 위", "On the platform"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Checkbutton(row, text=T("LDR을 받침에", "LDR up to the support"), variable=self.touch).pack(side="left")
        ttk.Checkbutton(row, text=T("시험관", "Test tube"), variable=self.tube).pack(side="left", padx=4)
        ttk.Checkbutton(row, text=T("회색 필터", "Grey filter"), variable=self.grey).pack(side="left")
        stepper(f, T("받침 돌리기", "Turn the support"), [("−10°", lambda: self.rot(-10)), ("−1°", lambda: self.rot(-1)), ("+1°", lambda: self.rot(1)), ("+10°", lambda: self.rot(10))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        for s in (1, 10, 30):
            ttk.Radiobutton(row, text="×%d" % s, value=s, variable=self.speed).pack(side="left")
        self.clk = ttk.Label(row, text="")
        self.clk.pack(side="left", padx=8)
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        ttk.Button(f, text=T("지금 세 계기 적기", "Write down the three meters"), command=self.record).pack(anchor="w")
        self.sheet = DataSheet(f, [("o", "Ω", 100), ("v", "V", 100), ("a", "A", 100)], height=5)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=420)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("받침대 위 · 전위차계 눈금 · 필터 투과율 (F-6)", "On the platform · potentiometer dial · filter transmittance (F-6)"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    def turn(self, d):
        if self.has("pot"):
            self.turns = max(0.0, min(10.0, round(self.turns + d, 4)))

    def rot(self, d):
        if not self.tube.get():
            self.sup = (self.sup + d) % 360

    def show(self, k):
        m = MODES[self.mode[k].get()]
        if not self.has(k):
            return "—"
        if not m:
            return "OFF"
        s = self.disp[k]
        return (s + " " + m[4]) if s and s != "1" else s

    def record(self):
        self.sheet.add(tuple(self.show(k) for k in ("dmmO", "dmmV", "dmmA")))

    def tick(self, dt):
        T_ = dt * self.speed.get()
        self.clock += T_
        while T_ > 0:
            h = min(0.5, T_)
            tgt, cur = math.log(self.ldr_target()), self.logR
            tau = 120.0 if tgt > cur else 110.0
            self.logR += (tgt - cur) * (1 - math.exp(-h / tau))
            T_ -= h
        self.disp_t -= dt
        if self.disp_t <= 0:
            self.disp_t = 0.4
            for k in self.mode:
                m, r = MODES[self.mode[k].get()], self.raw(k)
                if r is None or not m:
                    self.disp[k] = ""
                elif m[0] == "T":
                    self.disp[k] = str(int(round(r + (random.random() - 0.5) * 0.6)))
                elif r == float("inf") or abs(r) > m[1]:
                    self.disp[k] = "1"
                else:
                    q = 10 ** (-m[3]) / m[2]
                    self.disp[k] = "%.*f" % (m[3], (r * (1 + (random.random() - 0.5) * 0.0006) + (random.random() - 0.5) * q * 0.9) * m[2])
        msg = []
        if self.has("platform") and not self.cover.get():
            msg.append(T("덮개가 없어 방의 빛이 LDR에 들어갑니다.", "No cover: the room's light reaches the LDR."))
        if self.tube.get() and abs(math.cos(math.radians(self.sup % 180))) < 0.98:
            msg.append(T("받침의 구멍이 전구와 LDR을 향하지 않습니다.", "The support's holes do not face the bulb and the LDR."))
        self.warn.config(text="\n".join(msg))
        self.refresh()

    def refresh(self):
        for k in self.mode:
            self.lbl[k].config(text=self.show(k))
        self.tl.config(text=T("전위차계 %.3f 회전", "potentiometer %.3f turns") % self.turns)
        self.clk.config(text="%d:%02d" % (self.clock // 60, self.clock % 60))
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        cx, cy, k = 200, 200, 22
        cv.create_oval(cx - 7.2 * k, cy - 7.2 * k, cx + 7.2 * k, cy + 7.2 * k, fill="#d9dde2", outline="#888")
        if self.cover.get():
            cv.create_oval(cx - 7.6 * k, cy - 7.6 * k, cx + 7.6 * k, cy + 7.6 * k, fill="#1f2226", outline="")
            cv.create_text(cx, cy, text=T("덮개", "cover"), fill="#e8eef2")
        else:
            on = self.T > 1100
            cv.create_oval(cx - 5 * k, cy - 0.8 * k, cx - 3.4 * k, cy + 0.8 * k, fill="#ffe39a" if on else "#f4f4f0", outline="#888")
            if self.grey.get():
                cv.create_rectangle(cx - 2.25 * k, cy - 1.4 * k, cx - 1.95 * k, cy + 1.4 * k, fill="#46464b", outline="")
            a = math.radians(self.sup)
            cv.create_oval(cx - 1.5 * k, cy - 1.5 * k, cx + 1.5 * k, cy + 1.5 * k, fill="#2a2d33", outline="")
            cv.create_line(cx - math.cos(a) * 1.5 * k, cy + math.sin(a) * 1.5 * k, cx + math.cos(a) * 1.5 * k, cy - math.sin(a) * 1.5 * k, fill="#f2c14e", width=0.9 * k)
            if self.tube.get():
                cv.create_oval(cx - 0.75 * k, cy - 0.75 * k, cx + 0.75 * k, cy + 0.75 * k, fill="#e8782a", outline="")
            dx = 0 if self.touch.get() else 1.6
            cv.create_rectangle(cx + (4.4 + dx) * k, cy - 1.4 * k, cx + (6 + dx) * k, cy + 1.4 * k, fill="#2a2d33", outline="")
        # the potentiometer's dial
        px, py, R = 560, 150, 110
        cv.create_oval(px - R, py - R, px + R, py + R, fill="#f4f4f0", outline="#2b6cb0", width=6)
        for i in range(100):
            a = -math.pi / 2 + i / 100.0 * 2 * math.pi
            L0 = 14 if i % 10 == 0 else (9 if i % 5 == 0 else 5)
            cv.create_line(px + math.cos(a) * R, py + math.sin(a) * R, px + math.cos(a) * (R - L0), py + math.sin(a) * (R - L0), fill="#222")
            if i % 10 == 0:
                cv.create_text(px + math.cos(a) * (R - 26), py + math.sin(a) * (R - 26), text=str(i), font=("Helvetica", 9, "bold"))
        f = self.turns - math.floor(self.turns + 1e-9)
        a = -math.pi / 2 + f * 2 * math.pi
        cv.create_line(px, py, px + math.cos(a) * R * 0.95, py + math.sin(a) * R * 0.95, fill="#c0392b", width=3)
        cv.create_rectangle(px - 18, py + 20, px + 18, py + 44, fill="#fff", outline="#000")
        cv.create_text(px, py + 32, text=str(min(10, int(math.floor(self.turns + 1e-9)))), font=("Helvetica", 14, "bold"))
        # the filter's transmittance, F-6
        x0, x1, y0, y1 = 60, 720, 400, 610
        X = lambda l: x0 + (l - 450) / 300.0 * (x1 - x0)
        Y = lambda v: y1 - v / 30.0 * (y1 - y0)
        cv.create_rectangle(x0, y0, x1, y1, fill="#fbfaf6", outline="#333")
        for l in range(450, 751, 10):
            cv.create_line(X(l), y0, X(l), y1, fill="#ccc" if l % 50 else "#999")
            if l % 50 == 0:
                cv.create_text(X(l), y1 + 12, text=str(l), font=("Helvetica", 8))
        for v in range(0, 31, 5):
            cv.create_line(x0, Y(v), x1, Y(v), fill="#ccc")
            cv.create_text(x0 - 12, Y(v), text=str(v), font=("Helvetica", 8))
        pts = []
        for l in range(450, 751, 2):
            pts += [X(l), Y(filt(l) * 100)]
        cv.create_line(*pts, fill="#1b1d20", width=2)
        cv.create_text(x1 - 20, y0 + 14, text="F-6  % / λ nm", font=("Helvetica", 9, "bold"), anchor="e")


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
