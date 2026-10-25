#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  Nordic-Baltic Physics Olympiad 2024  (NBPhO 2024)
  Problem 10 (experimental) :  KITCHEN PHYSICS
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* Part i: a strip of n straight runs, each Ls long, cut zigzag from the
  aluminium-laminated paper bag (both faces, a run within the bag's
  27 cm).  Its resistance is rho l <1/w> / t with the hand-cut width w
  wandering along it, plus the two end contacts: through the varnish
  they are poor and wander (15-600 ohm), scraped with the sponge they
  are a few hundredths of an ohm.  The leads and clips add 0.2-0.3 ohm,
  seen by clipping them to each other.
* Part ii: plastic wrap (1-4 layers) between two aluminium foils.  Air
  left between the layers is a thin capacitor in series with the wrap:
  14-26 um of it unpressed, 2-4 um under the plate, a few tenths of a
  um with the foam under the plate.  The plate is 20 cm square; foil
  beyond it keeps 18-30 um of air.  The display wanders as the air
  does; the highest reading is the least air.
* The micrometer (0.01 mm) closes on the folded wrap or foil, one ply of
  the bag or the strip's width at one place; the ruler is laid on a run
  or the top foil's edges.  Both are drawn with their scales.  Nothing
  is computed for you.
* Hidden truths (the aluminium's and the wrap's thickness, the wrap's
  permittivity, the leads, the micrometer's zero) are randomised every
  session.
* Standard library only (tkinter).

    Run:   python3 nbpho2024_E2_kitchen_sim_KO.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line

EPS0 = 8.854e-12
PLATE = 0.20                      # the wooden plate, m square
BAG_W, BAG_H, BAG_SIDES = 0.27, 0.36, 2
FOIL = 0.30
RANGES = [("off", "OFF", None), ("o200", "Ω 200", 200.0), ("o2k", "Ω 2k", 2000.0), ("o20k", "Ω 20k", 20000.0),
          ("c2n", "F 2n", 2e-9), ("c20n", "F 20n", 20e-9), ("c200n", "F 200n", 200e-9), ("c2u", "F 2µ", 2e-6)]
RMAX = dict((k, c) for k, _, c in RANGES)


def T(ko, en):
    return ko if LANG == "ko" else en


def gauss(r):
    return r.gauss(0.0, 1.0)


# --------------------------------------------------------------------------
#  Physics core  (SI)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = self.r = random.Random(seed)
        self.rho = 2.7e-8
        self.tAl = r.uniform(5.2, 7.6) * 1e-6        # the answer of (i)
        self.paper = r.uniform(52, 64) * 1e-6
        self.Rlead = r.uniform(0.18, 0.34)
        self.tWrap = r.uniform(11.5, 15.0) * 1e-6
        self.eps = r.uniform(4.3, 5.3)                # the answer of (ii)
        self.foil = r.uniform(10.5, 12.5) * 1e-6
        self.mic0 = r.uniform(-0.004, 0.004) * 1e-3   # the micrometer's zero error
        self.gain = r.uniform(0.995, 1.005)
        self.r_off = r.uniform(0.4, 1.0)              # where the ruler's zero sits, cm
        self.r_sh = r.uniform(0.3, 2.0)
        # the strip
        self.w, self.Ls, self.n = 6e-3, 0.25, 4
        self.cut, self.scraped, self.wloc, self.LsTrue, self.cE = False, 0, [], 0.25, [100.0, 100.0]
        # the capacitor
        self.a, self.b, self.layers, self.built, self.press = 0.15, 0.15, 1, False, "none"

    @staticmethod
    def fits(w, Ls, n):
        return Ls <= BAG_W - 0.01 and n * (w + 1.2e-3) <= BAG_H * BAG_SIDES

    def length(self):
        return self.n * (self.LsTrue if self.cut else self.Ls)

    def cut_strip(self):
        r = self.r
        wt = max(1e-3, self.w + gauss(r) * 0.25e-3)
        self.wloc = [wt + gauss(r) * 0.22e-3 for _ in range(40)]
        self.LsTrue = self.Ls + gauss(r) * 0.6e-3
        self.cE = [r.uniform(15, 600), r.uniform(15, 600)]
        self.cut, self.scraped = True, 0

    def strip_R(self):
        r = self.r
        inv = sum(1.0 / w for w in self.wloc) / len(self.wloc)
        body = self.rho * self.length() * inv / self.tAl
        if self.scraped >= 2:
            ends = r.uniform(0.03, 0.07)
        else:
            ends = self.cE[0] * r.uniform(0.6, 1.4) + (0.05 if self.scraped else self.cE[1] * r.uniform(0.6, 1.4))
        return body + ends

    def cap_F(self, flick):
        if not self.built:
            return 0.0
        r = self.r
        S = self.a * self.b
        Sp = min(self.a, PLATE) * min(self.b, PLATE)
        g = r.uniform(0.08, 0.45) if self.press == "foam" else r.uniform(1.8, 3.6) if self.press == "plate" else r.uniform(14, 26)
        gapP = g * 1e-6 * flick * (1 + 0.6 * (self.layers - 1))
        gapO = r.uniform(18, 30) * 1e-6 * flick
        t = self.tWrap * self.layers
        if self.press == "none":
            return EPS0 * S / (t / self.eps + gapP)
        return EPS0 * Sp / (t / self.eps + gapP) + EPS0 * (S - Sp) / (t / self.eps + gapO)

    def meter(self, rng, probe, flick):
        """what the meter's clips see"""
        if rng == "off":
            return None
        r = self.r
        if rng[0] == "o":
            if probe == "short":
                return self.Rlead + r.uniform(0, 0.04)
            if probe == "strip" and self.cut:
                return (self.strip_R() + self.Rlead) * self.gain
            return float("inf")
        if probe == "cap" and self.built:
            return self.cap_F(flick) * self.gain
        if probe == "short":
            return float("nan")
        return r.uniform(0, 2e-12)

    def micrometer(self, target, N):
        r = self.r
        if target == "wrap":
            v = N * self.tWrap + (N - 1) * r.uniform(0.15, 0.4) * 1e-6
        elif target == "foil":
            v = N * self.foil + (N - 1) * r.uniform(0.1, 0.3) * 1e-6
        elif target == "bag":
            v = self.tAl + self.paper + r.uniform(0, 1.5) * 1e-6
        else:
            v = r.choice(self.wloc)
        return v + self.mic0


def show_meter(rng, v):
    """the 3½-digit display"""
    if v is None or rng == "off":
        return ""
    R = RMAX[rng]
    if v != v or v == float("inf") or v > R * 0.9995:
        return "1   "
    if rng[0] == "o":
        return "%.1f" % v if R == 200 else ("%.3f" if R == 2000 else "%.2f") % (v / 1000)
    if rng == "c2u":
        return "%.3f" % (v * 1e6)
    x = v * 1e9
    return "%.3f" % x if rng == "c2n" else "%.2f" % x if rng == "c20n" else "%.1f" % x


def unit_of(rng):
    return "" if rng == "off" else "Ω" if rng == "o200" else "kΩ" if rng[0] == "o" else "µF" if rng == "c2u" else "nF"


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_bag(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 40 * s, y - 28 * s, x + 40 * s, y + 28 * s, fill="#a7784a", outline="#6e4c2a")
    cv.create_rectangle(x - 34 * s, y - 22 * s, x + 34 * s, y - 10 * s, fill="#c4c9ce", outline="")


def art_sponge(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 30 * s, y - 4 * s, x + 30 * s, y + 12 * s, fill="#f2d23c", outline="#a88a10")
    cv.create_rectangle(x - 30 * s, y - 14 * s, x + 30 * s, y - 4 * s, fill="#2f8f4e", outline="#1d5a31")


def art_foil(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 36 * s, y - 30 * s, x + 30 * s, y + 24 * s, fill="#cfd4d9", outline="#8a9096")
    cv.create_rectangle(x - 30 * s, y - 24 * s, x + 36 * s, y + 30 * s, fill="#d7dce1", outline="#8a9096")


def art_foam(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 34 * s, y - 26 * s, x + 34 * s, y + 26 * s, fill="#eef0f5", outline="#9aa0aa")
    for i in range(-2, 3):
        for j in range(-1, 2):
            cv.create_oval(x + i * 12 * s - 2 * s, y + j * 14 * s - 2 * s, x + i * 12 * s + 2 * s, y + j * 14 * s + 2 * s, fill="#cfd4dc", outline="")


def art_plate(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 30 * s, y - 30 * s, x + 30 * s, y + 30 * s, fill="#c49a62", outline="#8a6a40", width=2)


def art_wrap(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 46 * s, y - 10 * s, x + 46 * s, y + 10 * s, fill="#e0e6ea", outline="#8e979e")
    cv.create_rectangle(x - 46 * s, y - 10 * s, x - 30 * s, y + 10 * s, fill="#b7c0c6", outline="#8e979e")


def art_scissors(cv, x, y, sc=1.0):
    s = sc
    cv.create_line(x - 10 * s, y - 6 * s, x + 36 * s, y + 4 * s, fill="#9aa3ab", width=3)
    cv.create_line(x - 10 * s, y + 6 * s, x + 36 * s, y - 4 * s, fill="#9aa3ab", width=3)
    for d in (-1, 1):
        cv.create_oval(x - 30 * s, y + d * 9 * s - 7 * s, x - 16 * s, y + d * 9 * s + 7 * s, outline="#c0392b", width=3)


def art_mic(cv, x, y, sc=1.0):
    s = sc
    cv.create_arc(x - 34 * s, y - 20 * s, x + 2 * s, y + 24 * s, start=90, extent=180, style="arc", outline="#2f6fb3", width=6)
    cv.create_rectangle(x - 10 * s, y - 24 * s, x + 4 * s, y - 16 * s, fill="#9aa1a8", outline="")
    cv.create_rectangle(x + 4 * s, y - 27 * s, x + 40 * s, y - 13 * s, fill="#b8bdc3", outline="#666")


def art_ruler(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 46 * s, y - 8 * s, x + 46 * s, y + 8 * s, fill="#dbe9f3", outline="#6b8ba3")
    for i in range(-42, 43, 6):
        cv.create_line(x + i * s, y - 8 * s, x + i * s, y + (2 if i % 12 == 0 else -2) * s, fill="#1d3c55")


def art_dmm(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 22 * s, y - 36 * s, x + 22 * s, y + 36 * s, fill="#e3b72d", outline="#5a3a12")
    cv.create_rectangle(x - 16 * s, y - 30 * s, x + 16 * s, y - 14 * s, fill="#9fae8f", outline="")
    cv.create_oval(x - 10 * s, y - 6 * s, x + 10 * s, y + 14 * s, fill="#1b1d20", outline="")
    cv.create_line(x - 8 * s, y + 30 * s, x - 30 * s, y + 46 * s, fill="#c0392b", width=2)
    cv.create_line(x + 8 * s, y + 30 * s, x + 30 * s, y + 46 * s, fill="#1f2226", width=2)


def art_marker(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 40 * s, y - 6 * s, x + 26 * s, y + 6 * s, fill="#16191d", outline="")
    cv.create_rectangle(x + 26 * s, y - 4 * s, x + 38 * s, y + 4 * s, fill="#2b3a99", outline="")


ART = {"bag": art_bag, "sponge": art_sponge, "foil": art_foil, "foam": art_foam, "plate": art_plate, "wrap": art_wrap,
       "scissors": art_scissors, "mic": art_mic, "ruler": art_ruler, "dmm": art_dmm, "marker": art_marker}
PARTS = [
    ("bag",      ("알루미늄 코팅 종이봉투 ⋆", "Aluminium-laminated paper bag ⋆"), []),
    ("sponge",   ("주방 스펀지 (초록 연마면)", "Kitchen sponge (green abrasive side)"), []),
    ("foil",     ("알루미늄 호일 2장 ⋆", "2 sheets of aluminium foil ⋆"), []),
    ("foam",     ("완충 폼 2장 ⋆", "2 sheets of cushioning foam ⋆"), []),
    ("plate",    ("나무 합판 (20 cm 정사각)", "Wooden plate (20 cm square)"), []),
    ("wrap",     ("주방용 랩 ⋆", "Kitchen plastic wrap ⋆"), []),
    ("scissors", ("가위", "Scissors"), []),
    ("mic",      ("마이크로미터 (0.01 mm)", "Micrometer (0.01 mm)"), []),
    ("ruler",    ("자 (30 cm)", "Ruler (30 cm)"), []),
    ("dmm",      ("멀티미터 + 악어 클립", "Multimeter + crocodile clips"), []),
    ("marker",   ("유성 마커", "Permanent marker"), []),
]
ZONES = {
    "bag":      (110, 130, 100, 70),
    "sponge":   (250, 120, 80, 40),
    "foil":     (390, 140, 90, 80),
    "foam":     (540, 140, 90, 70),
    "plate":    (670, 140, 80, 80),
    "wrap":     (130, 280, 110, 40),
    "scissors": (280, 280, 90, 40),
    "mic":      (420, 290, 90, 70),
    "ruler":    (570, 280, 110, 30),
    "dmm":      (130, 410, 80, 110),
    "marker":   (300, 410, 100, 30),
}
SCENE_TITLE = ("실험대 — 봉투, 스펀지, 호일, 폼, 합판, 랩, 가위, 마이크로미터, 자, 멀티미터, 마커",
               "The bench — bag, sponge, foil, foam, plate, wrap, scissors, micrometer, ruler, multimeter, marker")
APP_TITLE = ("NBPhO 2024 실험 (문제 10) — 부엌의 물리", "NBPhO 2024 Experiment (Problem 10) — Kitchen physics")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.rng = tk.StringVar(value="off")
        self.probe = tk.StringVar(value="open")
        self.press = tk.StringVar(value="none")
        self.ruler = tk.StringVar(value="off")
        self.target = tk.StringVar(value="wrap")
        self.N = 8
        self.mic = None              # what the micrometer reads, m; None: open
        self.mic_shown = 5.2         # mm, eased towards the reading
        self.disp, self.disp_t, self.flick = None, 0.0, 1.0
        self.msg = ""
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
        self.msg = s
        self.lmsg.config(text=s)

    # ---- the controls
    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=4, pady=4)
        colA, colB = ttk.Frame(ctl), ttk.Frame(ctl)
        colA.pack(side="left", fill="y", padx=2)
        colB.pack(side="left", fill="y", padx=2)
        f = ttk.LabelFrame(colA, text=T("(i) 알루미늄 띠 — 자르기 전에만 바꿈", "(i) Aluminium strip — set before cutting"))
        f.pack(fill="x", pady=2)
        self.lW = stepper(f, T("띠 폭", "Width"), [(t, (lambda d: lambda: self.strip_set(d, 0, 0))(v)) for t, v in
                                                  (("−1", -1e-3), ("−0.5", -0.5e-3), ("+0.5", 0.5e-3), ("+1", 1e-3))])
        self.lL = stepper(f, T("한 줄", "Run"), [(t, (lambda d: lambda: self.strip_set(0, d, 0))(v)) for t, v in
                                                (("−5", -0.05), ("−1", -0.01), ("+1", 0.01), ("+5", 0.05))])
        self.lN = stepper(f, T("줄 수", "Runs"), [(t, (lambda d: lambda: self.strip_set(0, 0, d))(v)) for t, v in
                                                 (("−5", -5), ("−1", -1), ("+1", 1), ("+5", 5))])
        self.vStrip = ttk.Label(f, text="", foreground="#1a4fb4")
        self.vStrip.pack(anchor="w")
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.bCut = ttk.Button(row, text="", command=self.cut)
        self.bCut.pack(side="left", padx=1)
        self.bScr = ttk.Button(row, text="", command=self.scrape)
        self.bScr.pack(side="left", padx=1)
        ttk.Label(f, text=T("같은 폭의 줄을 지그재그로 이어 자릅니다(봉투 앞뒤, 한 줄은 27 cm 이내). 손으로 자른 실제 폭은 표시한 폭과 조금씩 다릅니다.",
                            "Runs of equal width are cut joined zigzag (both faces, a run within 27 cm). Cut by hand, the real width differs a little from the marked one."),
                  foreground="#555", wraplength=300).pack(anchor="w")
        f = ttk.LabelFrame(colA, text=T("(ii) 랩 축전기", "(ii) Wrap capacitor"))
        f.pack(fill="x", pady=2)
        stepper(f, T("윗 호일 a", "Top foil a"), [(t, (lambda d: lambda: self.cap_set(d, 0, 0))(v)) for t, v in (("−5", -0.05), ("−1", -0.01), ("+1", 0.01), ("+5", 0.05))])
        stepper(f, T("윗 호일 b", "Top foil b"), [(t, (lambda d: lambda: self.cap_set(0, d, 0))(v)) for t, v in (("−5", -0.05), ("−1", -0.01), ("+1", 0.01), ("+5", 0.05))])
        stepper(f, T("랩 겹수", "Layers"), [("−1", lambda: self.cap_set(0, 0, -1)), ("+1", lambda: self.cap_set(0, 0, 1))])
        self.vCap = ttk.Label(f, text="", foreground="#1a4fb4")
        self.vCap.pack(anchor="w")
        self.bBld = ttk.Button(f, text="", command=self.build_cap)
        self.bBld.pack(anchor="w")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("누르기", "Press"), width=8).pack(side="left")
        for k, lb in (("none", T("안 누름", "none")), ("plate", T("합판만", "plate")), ("foam", T("폼+합판", "foam+plate"))):
            ttk.Radiobutton(row, text=lb, value=k, variable=self.press, command=self.press_changed).pack(side="left")
        ttk.Label(f, text=T("아래 호일(30 cm) 위에 더 넓은 랩, 그 위에 a × b 로 자른 윗 호일. 합판은 20 cm 정사각형입니다.",
                            "Lower foil (30 cm), the wider wrap, the top foil cut to a × b. The plate is a 20 cm square."),
                  foreground="#555", wraplength=300).pack(anchor="w")
        f = ttk.LabelFrame(colA, text=T("자 대기", "Ruler on"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for k, lb in (("off", T("치움", "off")), ("run", T("띠 한 줄", "one run")), ("capA", T("윗 호일 a", "top foil a")), ("capB", T("윗 호일 b", "top foil b"))):
            ttk.Radiobutton(row, text=lb, value=k, variable=self.ruler, command=self.ruler_changed).pack(side="left")
        f = ttk.LabelFrame(colB, text=T("마이크로미터", "Micrometer"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for k, lb in (("wrap", T("접은 랩", "wrap")), ("foil", T("접은 호일", "foil")), ("bag", T("봉투 한 겹", "bag ply")), ("width", T("띠 폭", "strip width"))):
            ttk.Radiobutton(row, text=lb, value=k, variable=self.target, command=self.open_mic).pack(side="left")
        stepper(f, T("접은 겹수", "Folds"), [(t, (lambda d: lambda: self.fold(d))(v)) for t, v in (("−4", -4), ("−1", -1), ("+1", 1), ("+4", 4))])
        self.vN = ttk.Label(f, text="", foreground="#1a4fb4")
        self.vN.pack(anchor="w")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("래칫 돌려 물리기", "Close with the ratchet"), command=self.measure).pack(side="left", padx=1)
        ttk.Button(row, text=T("열기", "Open"), command=self.open_mic).pack(side="left", padx=1)
        f = ttk.LabelFrame(colB, text=T("멀티미터 (DT-9205)", "Multimeter (DT-9205)"))
        f.pack(fill="x", pady=2)
        self.dM = tk.Label(f, text="", font=("Courier", 18, "bold"), bg="#9fae8f", fg="#1b1d20", width=12)
        self.dM.pack(pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for j, (k, lb, _) in enumerate(RANGES):
            ttk.Radiobutton(row, text=lb, value=k, variable=self.rng, command=self.range_changed).grid(row=j // 4, column=j % 4, sticky="w", padx=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("클립", "Clips"), width=6).pack(side="left")
        for k, lb in (("open", T("빼 둠", "off")), ("strip", T("띠 양 끝", "strip")), ("cap", T("두 호일", "foils")), ("short", T("클립끼리", "together"))):
            ttk.Radiobutton(row, text=lb, value=k, variable=self.probe, command=self.probe_changed).pack(side="left")
        ttk.Label(f, text=T("표시는 약 0.5초마다 바뀝니다. 클립끼리 물리면 리드 저항이 보입니다.", "The display changes about every 0.5 s. The clips on each other show the leads' resistance."),
                  foreground="#555", wraplength=300).pack(anchor="w")
        f = ttk.LabelFrame(colB, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("메모", "Memo")).pack(side="left")
        self.cent = ttk.Entry(row, width=16)
        self.cent.pack(side="left", padx=2)
        ttk.Button(row, text=T("적기", "Record"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("c", T("메모 (읽은 눈금 등)", "memo (scales read, …)"), 190), ("a", "DMM", 90)], height=7)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.lmsg = ttk.Label(colB, text="", foreground="#8a1b1b", wraplength=300)
        self.lmsg.pack(anchor="w", pady=2)
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        ttk.Label(right, text=T("작업대 (위에서) · 멀티미터 · 마이크로미터 — 눈금은 직접 읽으시오", "Work from above · multimeter · micrometer — read the scales yourself"),
                  font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=780, height=760, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    # ---- what the hands do
    def strip_set(self, dw, dL, dn):
        ph = self.ph
        if not self.need("bag"):
            return
        if ph.cut:
            self.say(T("이미 자른 띠입니다 — 바꾸려면 새 봉투를 받으시오.", "Already cut: get a new bag to change it."))
            return
        w = round(max(2e-3, min(20e-3, ph.w + dw)), 5)
        L = round(max(0.05, min(0.26, ph.Ls + dL)), 5)
        n = max(1, min(200, ph.n + dn))
        if not ph.fits(w, L, n):
            self.say(T("봉투에 그만큼 자를 자리가 없습니다.", "There is not that much room on the bag."))
            return
        ph.w, ph.Ls, ph.n = w, L, n
        self.refresh()

    def cut(self):
        ph = self.ph
        if ph.cut:
            if self.probe.get() == "strip":
                self.say(T("먼저 클립을 빼시오.", "Take the clips off first."))
                return
            ph.cut, ph.scraped = False, 0
            self.say(T("새 봉투를 받았습니다.", "Got a new bag."))
        elif self.need("bag", "scissors", "marker", "ruler"):
            ph.cut_strip()
            self.say(T("띠를 잘랐습니다.", "Strip cut."))
        self.refresh()

    def scrape(self):
        ph = self.ph
        if not self.need("sponge"):
            return
        if not ph.cut:
            self.say(T("먼저 띠를 자르시오.", "Cut the strip first."))
            return
        ph.scraped = min(2, ph.scraped + 1)
        self.say(T("끝의 바니시를 벗겼습니다 (%d/2).", "Varnish scraped off an end (%d/2).") % ph.scraped)
        self.refresh()

    def cap_set(self, da, db, dl):
        ph = self.ph
        if not self.need("foil"):
            return
        if ph.built:
            self.say(T("먼저 축전기를 푸시오.", "Take the capacitor apart first."))
            return
        ph.a = round(max(0.03, min(FOIL, ph.a + da)), 5)
        ph.b = round(max(0.03, min(FOIL, ph.b + db)), 5)
        ph.layers = max(1, min(4, ph.layers + dl))
        self.refresh()

    def build_cap(self):
        ph = self.ph
        if ph.built:
            if self.probe.get() == "cap":
                self.say(T("먼저 클립을 빼시오.", "Take the clips off first."))
                return
            ph.built, ph.press = False, "none"
            self.press.set("none")
        elif self.need("foil", "wrap"):
            ph.built = True
        self.refresh()

    def press_changed(self):
        ph, p = self.ph, self.press.get()
        if not ph.built:
            self.say(T("먼저 축전기를 겹치시오.", "Stack the capacitor first."))
            self.press.set("none")
            return
        if (p == "plate" and not self.need("plate")) or (p == "foam" and not self.need("foam", "plate")):
            self.press.set(ph.press)
            return
        ph.press = p
        self.disp_t = 0

    def ruler_changed(self):
        w = self.ruler.get()
        if w != "off" and not self.need("ruler"):
            self.ruler.set("off")
        elif w == "run" and not self.need("bag"):
            self.ruler.set("off")
        elif w in ("capA", "capB") and not self.ph.built:
            self.say(T("먼저 축전기를 겹치시오.", "Stack the capacitor first."))
            self.ruler.set("off")
        self.draw()

    def fold(self, d):
        if self.target.get() not in ("wrap", "foil"):
            self.say(T("겹수는 접은 랩·호일에만 있습니다.", "Only folded wrap or foil has layers."))
            return
        self.N = max(1, min(40, self.N + d))
        self.mic = None
        self.refresh()

    def open_mic(self):
        self.mic = None

    def measure(self):
        w = self.target.get()
        if not self.need("mic", {"wrap": "wrap", "foil": "foil", "bag": "bag", "width": "bag"}[w]):
            return
        if w == "width" and not self.ph.cut:
            self.say(T("먼저 띠를 자르시오.", "Cut the strip first."))
            return
        self.mic = self.ph.micrometer(w, self.N)

    def range_changed(self):
        if not self.need("dmm"):
            self.rng.set("off")
        self.disp_t = 0

    def probe_changed(self):
        p = self.probe.get()
        if p != "open" and not self.need("dmm"):
            self.probe.set("open")
        elif p == "strip" and not self.ph.cut:
            self.say(T("먼저 띠를 자르시오.", "Cut the strip first."))
            self.probe.set("open")
        elif p == "cap" and not self.ph.built:
            self.say(T("먼저 축전기를 겹치시오.", "Stack the capacitor first."))
            self.probe.set("open")
        self.disp_t = 0

    def text_of(self):
        s = show_meter(self.rng.get(), self.disp)
        if not s:
            return "—"
        if s.endswith("   "):
            s = "OL"
        return s + " " + unit_of(self.rng.get())

    def record(self):
        self.sheet.add((self.cent.get() or "—", self.text_of()))
        self.cent.delete(0, "end")

    def tick(self, dt):
        self.disp_t -= dt
        if self.disp_t <= 0:
            self.disp_t = 0.45
            self.flick = 1 + 0.6 * random.random() ** 2
            self.disp = self.ph.meter(self.rng.get(), self.probe.get(), self.flick) if self.has("dmm") else None
        target = 5.2 if self.mic is None else self.mic * 1e3
        self.mic_shown += (target - self.mic_shown) * min(1.0, dt * 6)
        self.refresh()

    def refresh(self):
        ph = self.ph
        self.vStrip.config(text=T("표시: 폭 %.1f mm, 한 줄 %.0f cm × %d 줄", "marked: width %.1f mm, run %.0f cm × %d") % (ph.w * 1e3, ph.Ls * 100, ph.n))
        self.vCap.config(text=T("윗 호일 %.0f × %.0f cm, 랩 %d 겹", "top foil %.0f × %.0f cm, wrap %d layer(s)") % (ph.a * 100, ph.b * 100, ph.layers))
        self.vN.config(text=T("접은 겹수 %d", "folds: %d") % self.N)
        self.bCut.config(text=T("새 봉투 받기", "Get a new bag") if ph.cut else T("마커로 긋고 가위로 자르기", "Mark and cut"))
        self.bScr.config(text=T("스펀지로 끝 문지르기 (%d/2)", "Scrape an end (%d/2)") % ph.scraped)
        self.bBld.config(text=T("축전기 풀기", "Take apart") if ph.built else T("호일–랩–호일 겹치기", "Stack foil–wrap–foil"))
        self.dM.config(text=self.text_of() if show_meter(self.rng.get(), self.disp) else "")
        self.draw()

    # ---- the drawings
    def draw(self):
        cv = self.cv
        cv.delete("all")
        self.draw_bag(10, 28, 250, 340)
        self.draw_cap(280, 28, 250)
        self.draw_ruler_zoom(560, 28)
        self.draw_dmm(20, 400)
        self.draw_mic(260, 400, 510, 340)

    def draw_bag(self, x0, y0, W, H):
        cv, ph = self.cv, self.ph
        cv.create_text(x0, y0 - 10, text=T("펼친 봉투 (알루미늄 면, 27 × 36 cm)", "Opened bag (aluminium side, 27 × 36 cm)"), anchor="w", font=("Helvetica", 9, "bold"))
        if not self.has("bag"):
            cv.create_text(x0 + W / 2, y0 + 120, text=T("봉투를 놓으시오", "Place the bag"), fill="#69717a")
            return
        s = min(W / 27.0, H / 36.0)
        X, Y = (lambda x: x0 + x * s), (lambda y: y0 + y * s)
        cv.create_rectangle(X(0), Y(0), X(27), Y(36), fill="#c3c8cd", outline="#7b8288")
        w, Ls = ph.w * 100, (ph.LsTrue if ph.cut else ph.Ls) * 100
        nF = min(ph.n, int((36 - 1.2) / (w + 0.12)))
        for i in range(nF):
            y = 1.2 + i * (w + 0.12)
            if ph.cut:
                cv.create_rectangle(X(1.2), Y(y), X(1.2 + Ls), Y(y + w), fill="#e4e8ec", outline="#4a5056")
            else:
                cv.create_rectangle(X(1.2), Y(y), X(1.2 + Ls), Y(y + w), outline="#16191d", dash=(4, 3))
        if ph.cut and ph.scraped:
            cv.create_rectangle(X(1.2), Y(1.2), X(2.7), Y(1.2 + w), fill="#f8f9fa", outline="")
        if ph.n > nF:
            cv.create_text(X(13.5), Y(35), text=T("뒷면에 %d줄 더", "%d more runs on the back") % (ph.n - nF), font=("Helvetica", 9, "bold"))
        if self.ruler.get() == "run":
            cv.create_rectangle(X(1.2 - self.ph.r_sh - self.ph.r_off), Y(1.2), X(1.2 - self.ph.r_sh - self.ph.r_off + 31.4), Y(3.8), outline="#6b8ba3", stipple="gray25", fill="#d6e8f4")

    def draw_cap(self, x0, y0, W):
        cv, ph = self.cv, self.ph
        cv.create_text(x0, y0 - 10, text=T("축전기 (위에서)", "Capacitor (from above)"), anchor="w", font=("Helvetica", 9, "bold"))
        if not self.has("foil"):
            cv.create_text(x0 + W / 2, y0 + 120, text=T("호일을 놓으시오", "Place the foil"), fill="#69717a")
            return
        s = W / 30.0
        X, Y = (lambda x: x0 + x * s), (lambda y: y0 + y * s)
        cv.create_rectangle(X(0), Y(0), X(30), Y(30), fill="#d7dce1", outline="#8a9096")
        if not ph.built:
            cv.create_text(X(15), Y(15), text=T("아직 겹치지 않음", "not stacked yet"), fill="#555")
            return
        a, b = ph.a * 100, ph.b * 100
        ox, oy = (30 - a) / 2, (30 - b) / 2
        cv.create_rectangle(X(-0.6), Y(-0.6), X(30.6), Y(30.6), outline="#7fb0d8", dash=(2, 2))
        cv.create_rectangle(X(ox), Y(oy), X(ox + a), Y(oy + b), fill="#eef1f3", outline="#555b61")
        if ph.press != "none":
            p = PLATE * 100
            cv.create_rectangle(X((30 - p) / 2), Y((30 - p) / 2), X((30 + p) / 2), Y((30 + p) / 2), outline="#8a6a40", width=2, dash=(6, 4))
        # the section, thickness exaggerated
        L = []
        if ph.press != "none":
            L.append(("#c49a62", T("합판", "plate")))
        if ph.press == "foam":
            L.append(("#eef0f5", T("폼", "foam")))
        L.append(("#d7dce1", T("호일", "foil")))
        L += [("#a8cde8", T("랩", "wrap"))] * ph.layers
        L += [("#d7dce1", T("호일", "foil")), ("#d6d3c8", T("책상", "table"))]
        yy = y0 + W + 14
        for col, name in L:
            cv.create_rectangle(x0, yy, x0 + 70, yy + 13, fill=col, outline="#777")
            cv.create_text(x0 + 76, yy + 7, text=name, anchor="w", font=("Helvetica", 8))
            yy += 13 + (3 if ph.press == "none" else 0)

    def ruler_box(self, x0, y0, w, h, edge_at, obj_right, title):
        """the ruler magnified 8x around one edge of the object; edge_at is the ruler reading there (cm)"""
        cv = self.cv
        k = 60.0                     # px per cm in the box
        cv.create_rectangle(x0, y0, x0 + w, y0 + h, fill="#fbfaf6", outline="#333", width=2)
        xe = x0 + w / 2
        if obj_right:
            cv.create_rectangle(xe, y0 + 1, x0 + w - 1, y0 + h - 1, fill="#dfe3e7", outline="")
        else:
            cv.create_rectangle(x0 + 1, y0 + 1, xe, y0 + h - 1, fill="#dfe3e7", outline="")
        cv.create_line(xe, y0 + 1, xe, y0 + h - 1, fill="#4a5056", width=2)
        cv.create_rectangle(x0 + 1, y0 + 1, x0 + w - 1, y0 + 0.55 * h, fill="#d6e8f4", outline="", stipple="gray50")
        for mm in range(int((edge_at - w / 2 / k) * 10) - 1, int((edge_at + w / 2 / k) * 10) + 2):
            if mm < 0 or mm > 300:
                continue
            x = xe + (mm / 10.0 - edge_at) * k
            if x < x0 + 2 or x > x0 + w - 2:
                continue
            L = 0.6 if mm % 10 == 0 else 0.42 if mm % 5 == 0 else 0.26
            cv.create_line(x, y0 + 1, x, y0 + 1 + L * k * 0.5, fill="#1d3c55", width=2 if mm % 10 == 0 else 1)
            if mm % 10 == 0:
                cv.create_text(x, y0 + 0.45 * k + 4, text=str(mm // 10), font=("Helvetica", 10, "bold"), fill="#1d3c55")
        cv.create_text(x0 + w / 2, y0 + h + 10, text=title, font=("Helvetica", 9, "bold"))

    def draw_ruler_zoom(self, x0, y0):
        ph, w = self.ph, self.ruler.get()
        self.cv.create_text(x0, y0 - 10, text=T("자 확대 (눈금 cm)", "Ruler magnified (cm)"), anchor="w", font=("Helvetica", 9, "bold"))
        if w == "run" and self.has("bag"):
            L = (ph.LsTrue if ph.cut else ph.Ls) * 100
            self.ruler_box(x0, y0, 200, 110, ph.r_sh, True, T("줄 시작", "run start"))
            self.ruler_box(x0, y0 + 150, 200, 110, ph.r_sh + L, False, T("줄 끝", "run end"))
        elif w in ("capA", "capB") and ph.built:
            L = (ph.a if w == "capA" else ph.b) * 100
            self.ruler_box(x0, y0, 200, 110, ph.r_sh, True, T("한쪽 모서리", "one edge"))
            self.ruler_box(x0, y0 + 150, 200, 110, ph.r_sh + L, False, T("다른 모서리", "other edge"))
        else:
            self.cv.create_text(x0 + 100, y0 + 120, text=T("자를 대지 않음", "no ruler laid on"), fill="#69717a")

    def draw_dmm(self, x0, y0):
        cv = self.cv
        if not self.has("dmm"):
            cv.create_text(x0 + 110, y0 + 150, text=T("멀티미터를 놓으시오", "Place the multimeter"), fill="#69717a")
            return
        cv.create_rectangle(x0, y0, x0 + 220, y0 + 340, fill="#e3b72d", outline="#5a3a12", width=2)
        cv.create_rectangle(x0 + 12, y0 + 12, x0 + 208, y0 + 328, fill="#2a2d33", outline="")
        cv.create_text(x0 + 110, y0 + 28, text="DT-9205", fill="#e8eef2", font=("Helvetica", 11, "bold"))
        cv.create_rectangle(x0 + 26, y0 + 44, x0 + 194, y0 + 110, fill="#9fae8f", outline="#5f6b52")
        s = show_meter(self.rng.get(), self.disp)
        cv.create_text(x0 + 186, y0 + 76, text=s.replace("1   ", "1"), font=("Courier", 26, "bold"), anchor="e")
        cv.create_text(x0 + 186, y0 + 102, text=unit_of(self.rng.get()), font=("Helvetica", 9, "bold"), anchor="e")
        cx, cy = x0 + 110, y0 + 190
        cv.create_oval(cx - 40, cy - 40, cx + 40, cy + 40, fill="#1b1d20", outline="#000")
        keys = [k for k, _, _ in RANGES]
        for i, (k, lb, _) in enumerate(RANGES):
            a = math.pi * (0.5 + 0.25 * i)
            cv.create_text(cx + 62 * math.cos(a), cy - 62 * math.sin(a), text=lb.split(" ")[-1], fill="#ffcf3a" if k == self.rng.get() else "#e8eef2", font=("Helvetica", 8, "bold"))
        a = math.pi * (0.5 + 0.25 * keys.index(self.rng.get()))
        cv.create_line(cx, cy, cx + 36 * math.cos(a), cy - 36 * math.sin(a), fill="#e8eef2", width=3)
        for dx, col, lb in ((-40, "#c0392b", "VΩ"), (40, "#1b1d20", "COM")):
            cv.create_oval(cx + dx - 10, y0 + 290, cx + dx + 10, y0 + 310, fill=col, outline="#111")
            cv.create_text(cx + dx, y0 + 278, text=lb, fill="#e8eef2", font=("Helvetica", 8))
        p = dict((("open", T("빼 둠", "off")), ("strip", T("띠 양 끝", "strip ends")), ("cap", T("두 호일", "two foils")), ("short", T("클립끼리", "together"))))[self.probe.get()]
        cv.create_text(x0 + 110, y0 + 352, text=T("클립: ", "Clips: ") + p, font=("Helvetica", 9, "bold"))

    def draw_mic(self, x0, y0, W, H):
        cv = self.cv
        cv.create_text(x0, y0, text=T("마이크로미터 눈금 (mm) — 슬리브 + 딤블 × 0.01", "Micrometer scales (mm) — sleeve + thimble × 0.01"), anchor="w", font=("Helvetica", 9, "bold"))
        if not self.has("mic"):
            cv.create_text(x0 + W / 2, y0 + 150, text=T("마이크로미터를 놓으시오", "Place the micrometer"), fill="#69717a")
            return
        r, yl, px = self.mic_shown, y0 + H * 0.46, 34.0
        fx, fw, fh = x0, 110, 90
        cv.create_polygon(fx, yl - 14, fx, yl + fh, fx + fw, yl + fh, fx + fw, yl + 14, fx + fw - 22, yl + 14, fx + fw - 22, yl + 64, fx + 22, yl + 64, fx + 22, yl - 14, fill="#2f6fb3", outline="#1d4a7c")
        cv.create_rectangle(fx + 22, yl - 9, fx + 32, yl + 9, fill="#c8cdd2", outline="#6d747a")
        gap = min(48, 4 + r * 7)
        if self.mic is not None:
            cv.create_rectangle(fx + 32, yl - 14, fx + 32 + gap, yl + 14, fill="#a8cde8" if self.target.get() == "wrap" else "#e4e8ec" if self.target.get() != "bag" else "#b88a5a", outline="")
        cv.create_rectangle(fx + 32 + gap, yl - 8, fx + fw, yl + 8, fill="#d4d8dc", outline="#6d747a")
        xs, xz = fx + fw, fx + fw + px * 0.5
        xt = xz + r * px
        cv.create_rectangle(xs, yl - 26, xt, yl + 26, fill="#cfd3d7", outline="#7d848a")
        cv.create_line(xs, yl, xt, yl, fill="#1b1d20", width=1)
        k = 0
        while k * 0.5 <= r + 1e-9 and k < 60:
            x = xz + k * 0.5 * px
            up = k % 2 == 0
            cv.create_line(x, yl, x, yl - 15 if up else yl + 12, fill="#1b1d20")
            if up and (k // 2) % 5 == 0:
                cv.create_text(x, yl - 22, text=str(k // 2), font=("Helvetica", 10, "bold"))
            k += 1
        tw, R = px * 3.4, 100.0
        cv.create_rectangle(xt, yl - R, xt + tw, yl + R, fill="#c9ced3", outline="#5f666c")
        ph_ = (r % 0.5) / 0.01
        for kk in range(int(ph_) - 11, int(ph_) + 12):
            a = (kk - ph_) * 2 * math.pi / 50
            if abs(a) > 1.35:
                continue
            y = yl - R * math.sin(a)
            m = kk % 50
            big = m % 5 == 0
            cv.create_line(xt, y, xt + (24 if big else 14), y, fill="#1b1d20", width=2 if big else 1)
            if big and abs(a) < 1.1:
                cv.create_text(xt + 28, y, text=str(m), anchor="w", font=("Helvetica", 10, "bold"))
        cv.create_rectangle(xt + tw, yl - 38, xt + tw + 56, yl + 38, fill="#8c939a", outline="#5f666c")
        cv.create_text(xt + tw + 28, yl + 50, text=T("래칫", "ratchet"), font=("Helvetica", 8), fill="#555")
        names = {"wrap": T("접은 랩 %d겹", "the wrap folded to %d layers") % self.N, "foil": T("접은 호일 %d겹", "the foil folded to %d layers") % self.N,
                 "bag": T("봉투 한 겹 (알루미늄 + 종이)", "one ply of the bag (aluminium + paper)"), "width": T("띠의 폭 (한 곳)", "the strip's width (one place)")}
        cv.create_text(x0, y0 + H - 10, anchor="w", font=("Helvetica", 10, "bold"),
                       text=T("턱이 열려 있음", "the jaws are open") if self.mic is None else T("물고 있는 것: ", "holding: ") + names[self.target.get()])


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
        self.geometry("1440x880")
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
