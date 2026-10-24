#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  Nordic-Baltic Physics Olympiad 2025  (NBPhO 2025)
  Problem 9 (experimental) :  HOT PLATE
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* Lumped heat flows, stepped every 0.2 s of experiment time: two
  40 x 40 mm aluminium plates (one black, one polished), the 220 ohm
  resistor sunk in the foam plate, four silicone pads (with a small heat
  capacity of their own), and the cup of hot water.
* Each face loses heat by free convection and by radiation
  eps*sigma*(T^4 - T0^4); a plate on the foam loses little through its
  bottom, on the bench top much more; pads pass heat by kappa*A/t.
* The infrared thermometer reads eps*T + (1 - eps)*T0 (calibrated for a
  black body), plus its own offset; a wet plate reads like water.
* The supply's voltage display is true; its current display is not.
  Left on with no plate on it, the resistor melts the foam and the
  invigilator switches the supply off.
* Hidden truths (the room, the polished plate's emissivity, the
  convection, the plates' heat capacity, the silicone's conductivity,
  the water) are randomised every session.
* Standard library only (tkinter).

    Run:   python3 nbpho2025_E2_hotplate_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the EN edition differs only in this line

SIG = 5.67e-8
A_TOP, A_EDGE = 1.6e-3, 3.2e-4
SPOTS = ["cup", "res", "foam", "table"]
AIMS = ["B", "P", "water", "pads", "res", "room"]


def T(ko, en):
    return ko if LANG == "ko" else en


def K(t):
    return t + 273.15


def rad(eps, t, t0):
    return eps * SIG * (K(t) ** 4 - K(t0) ** 4)


# --------------------------------------------------------------------------
#  Physics core  (W, J, K, s; temperatures in deg C)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.T0 = r.uniform(21.5, 24.0)          # the room
        self.epsP = r.uniform(0.045, 0.085)      # the polished plate: the answer of (i)
        self.epsB, self.epsSil, self.epsFoam, self.epsRes = 0.97, 0.92, 0.9, 0.95
        self.hc = r.uniform(11.5, 14.0)          # free convection from a face, W m^-2 K^-1
        self.C = r.uniform(15.6, 17.4)           # each plate's heat capacity
        # the silicone; the plate's edges and the foam leak heat beside the pads, so reading
        # R = 1/(gamma C) per layer as the solution does comes out about 2x high (0.05-0.1)
        self.kap = r.uniform(0.030, 0.042)
        self.t, self.Cpad = 0.8e-3, 1.4
        self.R = 220 * r.uniform(0.99, 1.01)
        self.Cres, self.Gres, self.Hres = 1.2, 0.45, 0.006
        self.Gfoam, self.Gtable, self.Gwater = 0.0025, 0.09, 2.0
        self.Cw, self.Gw = 620.0, 0.24
        self.irBias = r.uniform(-0.6, 0.6)
        self.Ibias = r.uniform(0.6, 1.5)
        # the state
        self.Tw = r.uniform(78, 85)
        self.Tres = self.T0
        self.pl = {"B": {"T": self.T0, "at": "table", "wet": 0.0}, "P": {"T": self.T0, "at": "table", "wet": 0.0}}
        self.pads_on, self.pads_n, self.padT = None, 0, [self.T0] * 4
        self.out, self.vset, self.scorch = False, 0.0, 0
        self.melted = False

    def eps(self, k):
        e = self.epsB if k == "B" else self.epsP
        return max(e, 0.95) if self.pl[k]["wet"] > 0.02 else e

    def p_in(self):
        return self.vset ** 2 / self.R if self.out and self.scorch < 2 else 0.0

    def pad_top(self):
        n = self.pads_n
        if not n:
            return None
        tn, g, t0 = self.padT[n - 1], 2 * self.kap * A_TOP / self.t, self.T0
        s = tn
        for _ in range(20):
            q = A_TOP * self.hc * (s - t0) + A_TOP * rad(self.epsSil, s, t0)
            dq = A_TOP * (self.hc + 4 * self.epsSil * SIG * K(s) ** 3)
            s -= (q - g * (tn - s)) / (dq + g)
        return s

    def step(self, dt):
        t0, gp = self.T0, self.kap * A_TOP / self.t
        covered = any(self.pl[k]["at"] == "res" for k in "BP")
        qres = self.p_in()
        for k in "BP":
            p = self.pl[k]
            q, e, padded = 0.0, self.eps(k), self.pads_on == k and self.pads_n > 0
            if p["at"] == "cup":
                q += self.Gwater * (self.Tw - p["T"])
                self.Tw -= self.Gwater * (self.Tw - p["T"]) * dt / self.Cw
                p["wet"] = 1.0
            else:
                q -= A_EDGE * (self.hc * (p["T"] - t0) + rad(e, p["T"], t0))
                if padded:
                    q -= 2 * gp * (p["T"] - self.padT[0])
                else:
                    q -= A_TOP * (self.hc * (p["T"] - t0) + rad(e, p["T"], t0))
                q -= (self.Gtable if p["at"] == "table" else self.Gfoam) * (p["T"] - t0)
                if p["at"] == "res":
                    g = self.Gres * (0.7 if self.scorch else 1.0)
                    q += g * (self.Tres - p["T"])
                    qres -= g * (self.Tres - p["T"])
                if p["wet"] > 0:
                    pe = (0.010 * (p["T"] - t0 + 6) + 0.01) * p["wet"]
                    q -= pe
                    p["wet"] = max(0.0, p["wet"] - pe * dt / 22 - dt * 1e-3)
            p["T"] += q * dt / self.C
        qres -= (0.0015 if covered else self.Hres) * (self.Tres - t0)
        self.Tres += qres * dt / self.Cres
        n, pd = self.pads_n, self.padT
        for i in range(4):
            q = 0.0
            if self.pads_on and i < n:
                below = self.pl[self.pads_on]["T"] if i == 0 else pd[i - 1]
                q += (2 * gp if i == 0 else gp) * (below - pd[i])
                if i < n - 1:
                    q += gp * (pd[i + 1] - pd[i])
                else:
                    q -= 2 * gp * (pd[i] - self.pad_top())
                q -= A_EDGE * 0.4 * self.hc * (pd[i] - t0)
            else:
                q -= 0.02 * (pd[i] - t0)
            pd[i] += q * dt / self.Cpad
        self.Tw -= self.Gw * (self.Tw - t0) * dt / self.Cw
        if self.Tres > 100 and self.out:
            self.out = False
            self.scorch = min(2, self.scorch + 1)
            self.melted = True

    def target(self, a):
        if a in ("B", "P"):
            p = self.pl[a]
            if p["at"] == "cup":
                return self.Tw, 1.0
            if self.pads_on == a and self.pads_n:
                return self.pad_top(), self.epsSil
            return p["T"], self.eps(a)
        if a == "water":
            return self.Tw, 1.0
        if a == "res":
            k = [k for k in "BP" if self.pl[k]["at"] == "res"]
            return self.target(k[0]) if k else (self.Tres, self.epsRes)
        if a == "pads":
            return (self.pad_top(), self.epsSil) if self.pads_on and self.pads_n else (self.padT[3], self.epsSil)
        return self.T0, self.epsFoam

    def ir(self, a):
        t, e = self.target(a)
        v = e * t + (1 - e) * self.T0 + self.irBias + (random.random() - 0.5) * 0.24
        return round(v * 10) / 10


def fmt_sw(t):
    m = int(t // 60)
    return "%02d:%04.1f" % (m, t - 60 * m)


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_foam(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 60 * s, y - 35 * s, x + 60 * s, y + 35 * s, fill="#dde9f0", outline="#8aa0b0")
    cv.create_rectangle(x + 25 * s, y - 25 * s, x + 45 * s, y - 17 * s, fill="#1b1b1b", outline="")


def art_psu(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 50 * s, y - 35 * s, x + 50 * s, y + 35 * s, fill="#2a2d33", outline="#888")
    cv.create_rectangle(x - 42 * s, y - 27 * s, x - 5 * s, y - 10 * s, fill="#140b0b", outline="")
    cv.create_rectangle(x + 5 * s, y - 27 * s, x + 42 * s, y - 10 * s, fill="#08120b", outline="")
    cv.create_oval(x + 10 * s, y + 15 * s, x + 20 * s, y + 25 * s, fill="#c0392b", outline="")


def art_cup(cv, x, y, sc=1.0):
    s = sc
    cv.create_polygon(x - 30 * s, y - 40 * s, x + 30 * s, y - 40 * s, x + 22 * s, y + 40 * s, x - 22 * s, y + 40 * s, fill="#f3f1ea", outline="#a9a59a")
    cv.create_rectangle(x - 27 * s, y - 30 * s, x + 27 * s, y - 24 * s, fill="#78aadc", outline="")


def art_plates(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 45 * s, y - 18 * s, x - 9 * s, y + 18 * s, fill="#16181b", outline="#000")
    cv.create_rectangle(x + 9 * s, y - 18 * s, x + 45 * s, y + 18 * s, fill="#dfe3e7", outline="#8d939a")


def art_pads(cv, x, y, sc=1.0):
    s = sc
    for i in range(4):
        cv.create_rectangle(x - 25 * s + 3 * i * s, y + 10 * s - 7 * i * s, x + 25 * s + 3 * i * s, y + 16 * s - 7 * i * s, fill="#de6a52" if i % 2 else "#c8432f", outline="#7a2a1e")


def art_tweezers(cv, x, y, sc=1.0):
    s = sc
    cv.create_line(x - 40 * s, y - 6 * s, x + 40 * s, y - 1 * s, fill="#9aa3ab", width=3)
    cv.create_line(x - 40 * s, y + 6 * s, x + 40 * s, y + 1 * s, fill="#9aa3ab", width=3)


def art_ir(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 40 * s, y - 18 * s, x + 25 * s, y + 6 * s, fill="#e8a33d", outline="#8a5a12")
    cv.create_rectangle(x - 10 * s, y + 6 * s, x + 12 * s, y + 38 * s, fill="#2b2e33", outline="")


def art_watch(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 22 * s, y - 30 * s, x + 22 * s, y + 30 * s, fill="#2b2e33", outline="#000")
    cv.create_rectangle(x - 15 * s, y - 22 * s, x + 15 * s, y - 5 * s, fill="#9fae8f", outline="")


def art_tissue(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 40 * s, y - 15 * s, x + 40 * s, y + 20 * s, fill="#7fb6d6", outline="#4a7a96")
    cv.create_polygon(x - 12 * s, y - 15 * s, x + 12 * s, y - 15 * s, x + 16 * s, y - 35 * s, x - 16 * s, y - 35 * s, fill="#fbfbf8", outline="#ccc")


ART = {"foam": art_foam, "psu": art_psu, "cup": art_cup, "plates": art_plates, "pads": art_pads,
       "tweezers": art_tweezers, "ir": art_ir, "watch": art_watch, "tissue": art_tissue}
PARTS = [
    ("foam",     ("발포 판 + 저항 220 Ω", "Foam plate + 220 Ω resistor"), []),
    ("psu",      ("직류 전원 장치", "DC power supply"), ["foam"]),
    ("cup",      ("뜨거운 물 컵", "Cup of hot water"), []),
    ("plates",   ("알루미늄 판 2장 (검정·광택)", "Two aluminium plates (black, polished)"), []),
    ("pads",     ("실리콘 패드 4장", "Four silicone pads"), []),
    ("tweezers", ("핀셋", "Tweezers"), []),
    ("ir",       ("적외선 온도계", "IR thermometer"), []),
    ("watch",    ("스톱워치", "Stopwatch"), []),
    ("tissue",   ("휴지", "Tissues"), []),
]
ZONES = {
    "foam": (330, 300, 140, 90), "psu": (130, 290, 120, 90), "cup": (520, 290, 80, 100),
    "plates": (330, 400, 110, 50), "pads": (470, 410, 70, 40), "tweezers": (640, 230, 100, 30),
    "ir": (650, 330, 90, 70), "watch": (620, 430, 60, 70), "tissue": (130, 410, 100, 60),
}
SCENE_TITLE = ("실험대 — 발포 판·저항, 전원, 뜨거운 물, 판 두 장, 패드, 핀셋, 온도계, 스톱워치, 휴지",
               "The bench — foam plate and resistor, supply, hot water, two plates, pads, tweezers, thermometer, stopwatch, tissues")
APP_TITLE = ("NBPhO 2025 실험 (문제 9) — 뜨거운 판", "NBPhO 2025 Experiment (Problem 9) — Hot plate")
PN = {"B": ("검은 판", "black plate"), "P": ("광택 판", "polished plate")}
SPOT = {"cup": ("컵", "cup"), "res": ("저항", "resistor"), "foam": ("폼판", "foam"), "table": ("책상", "bench")}
AIMN = {"B": ("검은 판", "black plate"), "P": ("광택 판", "polished plate"), "water": ("물", "water"),
        "pads": ("맨 위 패드", "top pad"), "res": ("저항", "resistor"), "room": ("실온 (책상)", "room (bench)")}


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.speed = tk.IntVar(value=1)
        self.aim = tk.StringVar(value="room")
        self.ir_show, self.ir_busy = None, 0.0
        self.sw_run, self.sw_t = False, 0.0
        self.points = []
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def warn(self, s):
        self.msg.config(text=s)

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("시간 흐름 (빨리 감기)", "Time flow (fast-forward)"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for v in (1, 5, 20, 60):
            ttk.Radiobutton(row, text="×%d" % v, value=v, variable=self.speed).pack(side="left", padx=3)
        f = ttk.LabelFrame(ctl, text=T("직류 전원 장치 → 저항 (15 V를 넘기지 마시오)", "DC supply → resistor (do not exceed 15 V)"))
        f.pack(fill="x", pady=2)
        self.dP = tk.Label(f, text="", font=("Courier", 15, "bold"), bg="#140b0b", fg="#ff4a3a", width=20)
        self.dP.pack(pady=2)
        self.outv = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="OUTPUT", variable=self.outv, command=self.toggle_out).pack(anchor="w")
        stepper(f, T("전압", "Voltage"), [(t, (lambda d: lambda: self.nudge(d))(dv)) for t, dv in (("−1", -1), ("−0.1", -0.1), ("+0.1", 0.1), ("+1", 1))])
        f = ttk.LabelFrame(ctl, text=T("핀셋으로 판 옮기기 · 휴지 · 패드", "Plates with the tweezers · tissue · pads"))
        f.pack(fill="x", pady=2)
        for k in "BP":
            row = ttk.Frame(f)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=T(*PN[k]), width=9).pack(side="left")
            for s in SPOTS:
                ttk.Button(row, text=T(*SPOT[s]), width=6, command=(lambda kk, ss: lambda: self.move(kk, ss))(k, s)).pack(side="left", padx=1)
            row = ttk.Frame(f)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text="", width=9).pack(side="left")
            ttk.Button(row, text=T("닦기", "Dry"), width=6, command=(lambda kk: lambda: self.wipe(kk))(k)).pack(side="left", padx=1)
            ttk.Button(row, text=T("패드 −1", "Pad −1"), width=7, command=(lambda kk: lambda: self.pads(kk, -1))(k)).pack(side="left", padx=1)
            ttk.Button(row, text=T("패드 +1", "Pad +1"), width=7, command=(lambda kk: lambda: self.pads(kk, 1))(k)).pack(side="left", padx=1)
        f = ttk.LabelFrame(ctl, text=T("적외선 온도계 (방사율 1로 보정)", "IR thermometer (calibrated for emissivity 1)"))
        f.pack(fill="x", pady=2)
        self.dI = tk.Label(f, text="", font=("Courier", 18, "bold"), bg="#9fae8f", fg="#1b1d20", width=12)
        self.dI.pack(pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for j, a in enumerate(AIMS):
            ttk.Radiobutton(row, text=T(*AIMN[a]), value=a, variable=self.aim, command=self.aim_changed).grid(row=j // 3, column=j % 3, sticky="w", padx=2)
        ttk.Button(f, text=T("단추 두 번 누르기 (측정)", "Press twice (measure)"), command=self.trigger).pack(fill="x", pady=2)
        f = ttk.LabelFrame(ctl, text=T("스톱워치", "Stopwatch"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.dS = tk.Label(row, text="", font=("Courier", 16, "bold"), bg="#9fae8f", fg="#1b1d20", width=9)
        self.dS.pack(side="left", padx=2)
        ttk.Button(row, text="START/STOP", command=self.sw_toggle).pack(side="left", padx=2)
        ttk.Button(row, text="RESET", command=self.sw_reset).pack(side="left", padx=2)
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("메모", "Memo")).pack(side="left")
        self.cent = ttk.Entry(row, width=12)
        self.cent.pack(side="left", padx=2)
        ttk.Button(row, text=T("지금 읽은 값 적기", "Record the reading"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("c", T("메모", "memo"), 80), ("t", "t", 70), ("T", "T_IR (°C)", 70), ("a", T("겨눈 곳", "aimed at"), 80)], height=5)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("단면 — 무엇이 어디에 (온도는 적외선 온도계로만 잼)", "Section — what lies where (temperatures only from the IR thermometer)"),
                  font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=860, height=520, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()
        self.msg = ttk.Label(right, text="", foreground="#8a1b1b", wraplength=840)
        self.msg.pack(anchor="w", pady=4)

    # ---- actions ----
    def toggle_out(self):
        if not (self.has("psu") and self.has("foam")):
            self.outv.set(False)
            self.warn(T("전원 장치와 발포 판을 먼저 놓으시오.", "Place the supply and the foam plate first."))
            return
        self.ph.out = self.outv.get()

    def nudge(self, dv):
        self.ph.vset = max(0.0, min(30.0, round(self.ph.vset + dv, 2)))
        if self.ph.vset > 15.05:
            self.warn(T("15 V를 넘기지 마시오!", "Do not exceed 15 V!"))

    def move(self, k, to):
        ph = self.ph
        if not (self.has("plates") and self.has("tweezers")):
            self.warn(T("판과 핀셋을 먼저 놓으시오.", "Place the plates and the tweezers first."))
            return
        if to == "cup" and not self.has("cup") or to in ("res", "foam") and not self.has("foam"):
            self.warn(T("그 장비가 실험대에 없습니다.", "That item is not on the bench."))
            return
        other = "P" if k == "B" else "B"
        if to in ("res", "foam") and ph.pl[other]["at"] == to:
            self.warn(T("그 자리에는 다른 판이 있습니다.", "The other plate is there."))
            return
        if ph.pads_on == k:
            ph.pads_on, ph.pads_n = None, 0
        if ph.pl[k]["at"] == "cup" and to != "cup":
            ph.pl[k]["wet"] = 1.0
        ph.pl[k]["at"] = to
        self.warn("")

    def wipe(self, k):
        ph = self.ph
        if not self.has("tissue"):
            self.warn(T("휴지를 먼저 놓으시오.", "Place the tissues first."))
            return
        if ph.pl[k]["at"] == "cup" or (ph.pads_on == k and ph.pads_n):
            self.warn(T("물속이거나 패드가 덮인 판은 닦을 수 없습니다.", "Cannot dry a plate in water or under pads."))
            return
        p = ph.pl[k]
        p["T"] -= 0.006 * (p["T"] - ph.T0)
        p["wet"] = 0.0

    def pads(self, k, dn):
        ph = self.ph
        if not (self.has("pads") and self.has("tweezers") and self.has("plates")) or ph.pl[k]["at"] == "cup":
            self.warn(T("패드는 핀셋으로, 컵 밖에 있는 판 위에만 올립니다.", "Pads go with the tweezers, only on a plate out of the cup."))
            return
        if ph.pads_on and ph.pads_on != k:
            self.warn(T("패드는 이미 다른 판 위에 있습니다.", "The pads are on the other plate."))
            return
        n = max(0, min(4, (ph.pads_n if ph.pads_on else 0) + dn))
        ph.pads_on, ph.pads_n = (k, n) if n else (None, 0)

    def aim_changed(self):
        self.ir_show = None

    def trigger(self):
        if not self.has("ir"):
            self.warn(T("적외선 온도계를 먼저 놓으시오.", "Place the IR thermometer first."))
            return
        self.ir_busy, self.ir_show = 0.6, None

    def sw_toggle(self):
        if self.has("watch"):
            self.sw_run = not self.sw_run

    def sw_reset(self):
        self.sw_run, self.sw_t = False, 0.0

    def record(self):
        memo = self.cent.get() or ""
        ir = "—" if self.ir_show is None else "%.1f" % self.ir_show
        self.sheet.add((memo or "—", fmt_sw(self.sw_t) if self.has("watch") else "—", ir, T(*AIMN[self.aim.get()])))
        if self.has("watch") and self.ir_show is not None:
            self.points.append((self.sw_t / 60.0, self.ir_show, memo))
            self.app.tab_graph.draw()

    def tick(self, dt_real):
        dt = dt_real * self.speed.get()
        left = dt
        while left > 1e-9:
            h = min(0.2, left)
            self.ph.step(h)
            left -= h
        if self.sw_run:
            self.sw_t += dt
        if self.ir_busy > 0:
            self.ir_busy -= dt_real
            if self.ir_busy <= 0:
                self.ir_show = self.ph.ir(self.aim.get())
        if self.ph.melted:
            self.ph.melted = False
            self.outv.set(False)
            self.warn(T("발포 판이 녹기 시작해 감독관이 전원을 껐습니다!", "The foam started to melt and the invigilator switched the supply off!"))
        self.refresh()

    def refresh(self):
        ph = self.ph
        amps = round(ph.p_in() / max(ph.vset, 1e-6) * ph.Ibias * 100) / 100 if ph.out else 0.0
        self.dP.config(text=("%5.2f V  %.2f A" % (ph.vset, amps)) if self.has("psu") else "—")
        self.dI.config(text="···" if self.ir_busy > 0 else "—" if self.ir_show is None else "%.1f °C" % self.ir_show)
        self.dS.config(text=fmt_sw(self.sw_t) if self.has("watch") else "—")
        self.draw()

    def draw(self):
        cv, ph = self.cv, self.ph
        cv.delete("all")
        sc, X0, Y0 = 22, 40, 420
        X = lambda u: X0 + u * sc
        Y = lambda v: Y0 - v * sc
        cv.create_line(X(-1), Y(0), X(36), Y(0), fill="#888")
        if self.has("foam"):
            cv.create_rectangle(X(0), Y(2), X(22), Y(0), fill="#dde9f0", outline="#8aa0b0")
            cv.create_rectangle(X(16.2), Y(2.3), X(18.4), Y(1.7), fill="#1b1b1b", outline="")
            if ph.scorch:
                cv.create_rectangle(X(15), Y(2.05), X(19.6), Y(1.8), fill="#a58a5c", outline="")
            cv.create_text(X(4), Y(1), text=T("발포 판 · 저항", "foam plate · resistor"), anchor="w", fill="#3b4650")
            for k in "BP":
                at = ph.pl[k]["at"]
                if at not in ("res", "foam"):
                    continue
                u0, z0 = (15.3, 2.3) if at == "res" else (4.5, 2.0)
                cv.create_rectangle(X(u0), Y(z0 + 0.45), X(u0 + 4), Y(z0), fill="#16181b" if k == "B" else "#c9ced4", outline="#555")
                if ph.pl[k]["wet"] > 0.02:
                    cv.create_text(X(u0 + 2), Y(z0 + 1.2), text=T("젖음", "wet"), fill="#3a7bd5")
                if ph.pads_on == k:
                    for i in range(ph.pads_n):
                        cv.create_rectangle(X(u0), Y(z0 + 0.45 + (i + 1) * 0.42), X(u0 + 4), Y(z0 + 0.45 + i * 0.42), fill="#de6a52" if i % 2 else "#c8432f", outline="#7a2a1e")
        if self.has("cup"):
            cu = 28
            cv.create_polygon(X(cu - 3.6), Y(8.5), X(cu + 3.6), Y(8.5), X(cu + 2.8), Y(0), X(cu - 2.8), Y(0), fill="#f3f1ea", outline="#a9a59a")
            cv.create_polygon(X(cu - 3.3), Y(7), X(cu + 3.3), Y(7), X(cu + 2.65), Y(0.4), X(cu - 2.65), Y(0.4), fill="#9cc2e6", outline="")
            for i, k in enumerate("BP"):
                if ph.pl[k]["at"] == "cup":
                    u = cu - 1.5 + 2.2 * i
                    cv.create_polygon(X(u - 0.2), Y(0.6), X(u + 0.3), Y(0.6), X(u + 1.1), Y(8.6), X(u + 0.6), Y(8.6), fill="#16181b" if k == "B" else "#c9ced4", outline="#555")
        if self.has("plates"):
            for i, k in enumerate("BP"):
                if ph.pl[k]["at"] == "table":
                    cv.create_rectangle(X(32), Y(0.45 + 0.6 * i), X(35), Y(0.6 * i), fill="#16181b" if k == "B" else "#c9ced4", outline="#555")
                    cv.create_text(X(33.5), Y(1.3 + 0.6 * i), text=T(*PN[k]), font=("Helvetica", 8))
        if self.has("psu") and self.has("foam"):
            cv.create_line(X(17.3), Y(2.3), X(17.3), Y(9), X(2), Y(9), fill="#c0392b", width=2)
            cv.create_text(X(2), Y(9.5), text="DC  %.2f V%s" % (ph.vset, "  ON" if ph.out else ""), anchor="w", fill="#c0392b", font=("Helvetica", 10, "bold"))


# --------------------------------------------------------------------------
#  Graph paper tab: (stopwatch time, thermometer reading) for every record, coloured by memo
# --------------------------------------------------------------------------
class GraphTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        ttk.Label(self, text=T("모눈종이 — 기록할 때의 스톱워치 시각(분)과 온도계 값 (메모가 같으면 같은 색)",
                               "Graph paper — stopwatch time (min) and thermometer reading at each record (same memo, same colour)"),
                  font=("Helvetica", 10, "bold")).pack(anchor="w", padx=6, pady=4)
        ttk.Button(self, text=T("점 모두 지우기", "Clear the points"), command=self.clear).pack(anchor="w", padx=6)
        self.cv = tk.Canvas(self, width=1100, height=640, bg="#fbfaf4", highlightthickness=0)
        self.cv.pack(padx=6, pady=6)

    def clear(self):
        self.app.tab_bench.points = []
        self.draw()

    def draw(self):
        cv, P = self.cv, self.app.tab_bench.points
        cv.delete("all")
        L, R, Tp, B = 70, 1070, 30, 590

        def nice(v):
            e = 10 ** math.floor(math.log10(v))
            m = v / e
            return (1 if m <= 1 else 2 if m <= 2 else 5 if m <= 5 else 10) * e
        x0, x1 = 0.0, 1.0
        y0, y1 = (min(p[1] for p in P), max(p[1] for p in P)) if P else (20.0, 80.0)
        for t, _, _ in P:
            x1 = max(x1, t)
        xs, ys = nice((x1 - x0) / 10), nice(max(1.0, y1 - y0) / 8)
        x1 = math.ceil(x1 / xs) * xs
        y0, y1 = math.floor(y0 / ys) * ys, math.ceil(y1 / ys) * ys
        if y1 == y0:
            y1 = y0 + ys
        X = lambda v: L + (v - x0) / (x1 - x0) * (R - L)
        Y = lambda v: B - (v - y0) / (y1 - y0) * (B - Tp)
        for k in range(int(round((x1 - x0) / xs)) * 10 + 1):
            c = "#d6783c" if k % 10 == 0 else "#ebb995" if k % 5 == 0 else "#f6dcc8"
            cv.create_line(X(x0 + k * xs / 10), Tp, X(x0 + k * xs / 10), B, fill=c)
        for k in range(int(round((y1 - y0) / ys)) * 10 + 1):
            c = "#d6783c" if k % 10 == 0 else "#ebb995" if k % 5 == 0 else "#f6dcc8"
            cv.create_line(L, Y(y0 + k * ys / 10), R, Y(y0 + k * ys / 10), fill=c)
        cv.create_line(L, Tp, L, B, R, B, fill="#222", width=2)
        for k in range(int(round((x1 - x0) / xs)) + 1):
            cv.create_text(X(x0 + k * xs), B + 12, text="%g" % round(x0 + k * xs, 6), font=("Helvetica", 9))
        for k in range(int(round((y1 - y0) / ys)) + 1):
            cv.create_text(L - 6, Y(y0 + k * ys), text="%g" % round(y0 + k * ys, 6), anchor="e", font=("Helvetica", 9))
        cv.create_text(R, B + 28, text=T("t (분)", "t (min)"), anchor="e", font=("Helvetica", 11, "bold"))
        cv.create_text(L + 4, Tp + 10, text="T_IR (°C)", anchor="w", font=("Helvetica", 11, "bold"))
        tags = []
        for _, _, g in P:
            if g not in tags:
                tags.append(g)
        cols = ["#1a4fb4", "#c0392b", "#2f8f4e", "#8e44ad", "#d35400", "#16a085"]
        for k, g in enumerate(tags):
            if len(tags) < 2 and not g:
                break
            cv.create_text(R - 170, Tp + 14 + 16 * k, text="×  " + (g or "—"), anchor="w", fill=cols[k % 6], font=("Helvetica", 10, "bold"))
        for t, v, g in P:
            x, y, c = X(t), Y(v), cols[tags.index(g) % 6]
            cv.create_line(x - 4, y - 4, x + 4, y + 4, fill=c, width=2)
            cv.create_line(x - 4, y + 4, x + 4, y - 4, fill=c, width=2)
        if not P:
            cv.create_text(570, 320, text=T("아직 찍힌 점이 없습니다", "No points yet"), fill="#888", font=("Helvetica", 12))


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
        self.geometry("1360x860")
        self.placed = set()
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_asm = AssemblyTab(nb, self)
        self.tab_bench = BenchTab(nb, self)
        self.tab_graph = GraphTab(nb, self)
        nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.tab_bench, text=T(" 실험대 ", " Bench "))
        nb.add(self.tab_graph, text=T(" 모눈종이 ", " Graph paper "))
        self.tab_graph.draw()
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
