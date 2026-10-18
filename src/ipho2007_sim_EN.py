#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  38th International Physics Olympiad  (IPhO 2007, Isfahan, Iran)
  Experimental Problem :  ENERGY BAND GAP OF SEMICONDUCTOR THIN FILMS
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* A halogen lamp, a lens and a 600 lines/mm transmission grating; the
  photoresistor at the end of the rotatable arm reads 1/R = C(lambda) I.
  The arm accepts a spread of angles (wider when the lamp sits close to
  the lens), so each reading averages the spectrum over a few nm; the
  orders follow n lambda = d [sin(theta - theta0) + sin theta0], with
  theta0 the grating's tilt that the student sets by the reflection on a
  card with a hole.
* The film: -ln T = A t (h nu - Eg)^(1/2) / h nu + a loss below the gap,
  with an Urbach tail and a few pinholes; A = 0.071 eV^(1/2)/nm.
* The photoresistor creeps towards its value, slowest in the dark (3-4
  minutes at a hundred megohms); the room's light enters with the cover
  open; the ohmmeter switches itself off after 15 minutes untouched.
* Eg, t, the vernier's and the arm's start, the grating's tilt and lean
  and the lamp-detector response are hidden and randomised.
* Standard library only (tkinter).

    Run:   python3 ipho2007_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line

RAD = math.pi / 180
DG = 1e6 / 600.0
GTAB = [(360, 0), (380, 0.02), (400, 0.10), (420, 0.22), (440, 0.38), (460, 0.62), (480, 1.05), (500, 1.6), (520, 2.5), (540, 3.7), (555, 4.6), (565, 5.1),
        (575, 4.9), (585, 3.9), (595, 2.7), (610, 1.7), (625, 1.3), (640, 1.17), (660, 1.0), (680, 0.78), (700, 0.55), (720, 0.40), (740, 0.28), (760, 0.18),
        (800, 0.08), (850, 0.03), (900, 0)]
RANGES = [("200", 199.9e-6, "Ω", 1e6, 1), ("2k", 1.999e-3, "kΩ", 1e3, 3), ("20k", 19.99e-3, "kΩ", 1e3, 2), ("200k", 199.9e-3, "kΩ", 1e3, 1),
          ("2M", 1.999, "MΩ", 1, 3), ("20M", 19.99, "MΩ", 1, 2), ("200M", 199.9, "MΩ", 1, 1)]
KW = []
for _i in range(15):
    _x = -2.6 + 5.2 * _i / 14
    KW.append((_x, math.exp(-_x * _x / 2)))
_s = sum(w for _, w in KW)
KW = [(x, w / _s) for x, w in KW]


def wl_rgb(l):
    r = g = b = 0.0
    if 380 <= l < 440:
        r, b = -(l - 440) / 60.0, 1.0
    elif 440 <= l < 490:
        g, b = (l - 440) / 50.0, 1.0
    elif 490 <= l < 510:
        g, b = 1.0, -(l - 510) / 20.0
    elif 510 <= l < 580:
        r, g = (l - 510) / 70.0, 1.0
    elif 580 <= l < 645:
        r, g = 1.0, -(l - 645) / 65.0
    elif 645 <= l <= 780:
        r = 1.0
    return r, g, b


# --------------------------------------------------------------------------
#  Physics core
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.r = r
        self.Eg, self.t, self.bk = r.uniform(2.10, 2.26), r.uniform(180, 232), r.uniform(0.62, 0.85)
        self.grad, self.leak, self.Eu = r.uniform(-0.05, 0.05), r.uniform(0.008, 0.016), 0.035
        self.gs, self.gsh, self.effM = r.uniform(0.8, 1.25), r.uniform(-6, 6), r.uniform(1.15, 1.55)
        self.gN, self.psi0, self.a = r.uniform(-7, 7), r.uniform(-2.2, 2.2), r.uniform(6.6, 7.4)
        self.z0, self.th0 = r.uniform(-4, 4), r.uniform(-9, 9)
        self.g0 = self.gN + r.uniform(1.5, 8) * r.choice((-1, 1))

    def G(self, l):
        l -= self.gsh
        if l <= GTAB[0][0] or l >= GTAB[-1][0]:
            return 0.0
        i = 1
        while GTAB[i][0] < l:
            i += 1
        x0, y0 = GTAB[i - 1]
        x1, y1 = GTAB[i]
        return self.gs * (y0 + (y1 - y0) * (l - x0) / (x1 - x0)) / 0.92

    def film_od(self, l, t):
        E = 1239.84 / l
        x = (E - self.Eg) / self.Eu
        sp = x if x > 30 else math.log1p(math.exp(x))
        return 0.071 * t * math.sqrt(self.Eu * sp) / E + self.bk

    def sample_T(self, l, frame, u):
        if frame == "open":
            return 1.0
        c = max(0.0, 1 - max(0.0, abs(u) - 2.5) / 3)
        if frame == "glass":
            T = 0.92
        else:
            T = 0.92 * ((1 - self.leak) * math.exp(-self.film_od(l, self.t * (1 + self.grad * u))) + self.leak)
        return c * T + (1 - c)

    def orders(self, thp, th0):
        s = DG * (math.sin((thp - th0) * RAD) + math.sin(th0 * RAD))
        return [(s, 1.0) if s > 0 else (-s, self.effM), (abs(s) / 2, 0.18)]

    def light(self, st, th):
        """1/R (1/Mohm) on the photoresistor with the arm at its true angle th"""
        G = 0.0
        if st["lamp"]:
            lamp = (1 - math.exp(-st["warm"] / 20.0)) * (0.86 + 0.14 * st["lpos"]) * (0.15 if st["card"] else 1)
            sg = 0.5 + 0.45 * (1 - st["lpos"])
            th0 = st["g"] - self.gN
            tz = wz = 0.0
            for l in range(400, 761, 20):
                g = self.G(l)
                tz += g * self.sample_T(l, st["frame"], st["u"])
                wz += g
            G += 46 * self.gs * math.exp(-th * th / (2 * sg * sg)) * tz / wz
            for x, w in (KW if st["grating"] else []):
                thp = th + x * sg
                s = sum(e * self.G(l) * self.sample_T(l, st["frame"], st["u"]) for l, e in self.orders(thp, th0))
                v = (st["tilt"] - self.psi0) * math.sin(abs(thp) * RAD) / 0.55
                G += w * s * math.exp(-v * v / 2)
            if not st["grating"]:
                G *= 1.1
            G *= lamp
        return G + (0 if st["cover"] else 2.6) + 0.0002

    def seen(self, st, th):
        """the colour on a card at the arm's end, or None"""
        if not st["lamp"]:
            return None
        sg = 0.5 + 0.45 * (1 - st["lpos"])
        if abs(th) < 2.5 * sg:
            return (255, 248, 225)
        if not st["grating"]:
            return None
        th0 = st["g"] - self.gN
        c = [0.0, 0.0, 0.0]
        I = 0.0
        for x, w in KW:
            thp = th + x * sg
            for l, e in self.orders(thp, th0):
                if 380 <= l <= 780:
                    s = w * e * (0.4 + l / 700.0) * math.exp(-((l - 555) / 85.0) ** 2) * self.sample_T(l, st["frame"], st["u"])
                    q = wl_rgb(l)
                    c = [c[k] + q[k] * s for k in range(3)]
                    I += s
        if I < 0.01:
            return None
        m = max(c) or 1
        f = min(1.0, I * 1.6)
        return tuple(int(232 + (v / m * 255 - 232) * (0.3 + 0.7 * f)) for v in c)


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def box_art(col, w, h):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_rectangle(x - w * s, y - h * s, x + w * s, y + h * s, fill=col, outline="#555")
    return art


def art_spec(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 60 * s, y - 28 * s, x + 60 * s, y + 28 * s, fill="#f4f4f0", outline="#999")
    cv.create_rectangle(x - 54 * s, y - 8 * s, x - 38 * s, y + 8 * s, fill="#2a2d33", outline="")
    cv.create_oval(x - 8 * s, y - 8 * s, x + 8 * s, y + 8 * s, fill="#8d939b", outline="")
    cv.create_line(x, y, x + 54 * s, y + 14 * s, fill="#9aa1a8", width=max(1, 4 * s))


ART = {"spectro": art_spec, "grating": box_art("#3a3d42", 10, 12), "detector": box_art("#c9b27a", 12, 8), "sample": box_art("#3a3d42", 18, 9),
       "card": box_art("#fbfbf8", 12, 16), "dmm": box_art("#2b2d31", 22, 34), "ruler": box_art("#d6e4ec", 60, 5), "labels": box_art("#f4f4f0", 14, 9)}
PARTS = [
    ("spectro",  ("[1] 분광기 (램프·렌즈·각도기)", "[1] Spectrometer (lamp, lens, goniometer)"), []),
    ("grating",  ("[2] 회절격자 600줄/mm", "[2] Grating 600 lines/mm"), ["spectro"]),
    ("card",     ("[3] 구멍 뚫린 카드", "[3] Card with a hole"), ["spectro"]),
    ("detector", ("[4] 광저항 검출기", "[4] Photoresistor detector"), ["spectro"]),
    ("sample",   ("[5] 시료틀 (박막 S2·유리 S3)", "[5] Sample frame (film S2, glass S3)"), ["spectro"]),
    ("dmm",      ("[6] 멀티미터 (저항)", "[6] Multimeter (ohms)"), []),
    ("ruler",    ("[7] 자", "[7] Ruler"), []),
    ("labels",   ("[8] 빈 라벨", "[8] Blank labels"), []),
]
ZONES = {"spectro": (330, 200, 130, 70), "grating": (360, 200, 24, 28), "card": (300, 200, 28, 36), "detector": (440, 230, 28, 20), "sample": (420, 270, 40, 22),
         "dmm": (620, 220, 50, 72), "ruler": (330, 400, 124, 14), "labels": (560, 400, 32, 22)}
SCENE_TITLE = ("분광기에 격자·카드·광저항·시료틀을 끼우고 멀티미터를 이으시오", "Fit the grating, card, photoresistor and frame to the spectrometer; connect the meter")
APP_TITLE = ("IPhO 2007 실험 — 반도체 박막의 에너지 띠틈", "IPhO 2007 Experiment — Energy band gap of semiconductor thin films")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        ph = self.ph
        self.st = {"lamp": False, "warm": 0.0, "lpos": 0.25, "card": False, "cover": False, "g": ph.g0, "tilt": 0.0, "frame": "open", "u": 0.0, "grating": False}
        self.lamp = tk.BooleanVar(value=False)
        self.cover = tk.BooleanVar(value=False)
        self.card_in = tk.BooleanVar(value=True)
        self.frame = tk.StringVar(value="open")
        self.lock18, self.lock9, self.lock12 = tk.BooleanVar(value=False), tk.BooleanVar(value=True), tk.BooleanVar(value=False)
        self.th, self.z = ph.th0, ph.z0
        self.rng = tk.StringVar(value="2M")
        self.speed = tk.IntVar(value=1)
        self.power, self.idle, self.clock = "on", 0.0, 0.0
        self.logR = math.log(5000.0)
        self.disp, self.disp_t = "", 0.0
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def sync(self):
        s = self.st
        s["lamp"] = self.lamp.get() and self.has("spectro")
        s["cover"] = self.cover.get()
        s["card"] = self.card_in.get() and self.has("card")
        s["frame"] = self.frame.get() if self.has("sample") else "open"
        s["grating"] = self.has("grating")

    def reading(self):
        return self.th - self.z

    def show(self):
        if not self.has("dmm"):
            return "—"
        if self.power != "on":
            return ""
        return self.disp

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("멀티미터 (광저항)", "Multimeter (photoresistor)"))
        f.pack(fill="x", pady=2)
        self.lbl = tk.Label(f, text="", font=("Courier", 18, "bold"), bg="#9fae8f", fg="#1b1d20", width=14)
        self.lbl.pack(anchor="w", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for key, _, unit, _, _ in RANGES:
            ttk.Radiobutton(row, text=key, value=key, variable=self.rng, command=self.touch).pack(side="left")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("전원 M1", "Power M1"), command=self.pwr).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("램프 · 덮개 · 카드", "Lamp · cover · card"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Checkbutton(row, text=T("램프 켜기", "Lamp on"), variable=self.lamp).pack(side="left")
        ttk.Checkbutton(row, text=T("덮개 닫기", "Cover closed"), variable=self.cover).pack(side="left", padx=4)
        ttk.Checkbutton(row, text=T("카드를 램프 앞에", "Card before the lamp"), variable=self.card_in).pack(side="left")
        stepper(f, T("램프 팔 길이", "Lamp arm"), [("◀", lambda: self.lp(-0.125)), ("▶", lambda: self.lp(0.125))])
        f = ttk.LabelFrame(ctl, text=T("회전 팔 · 버니어 · 격자대", "Arm · vernier · grating stage"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Checkbutton(row, text=T("나사 18 잠금", "screw 18 tight"), variable=self.lock18).pack(side="left")
        ttk.Checkbutton(row, text=T("나사 9 잠금", "screw 9 tight"), variable=self.lock9).pack(side="left")
        ttk.Checkbutton(row, text=T("나사 12 잠금", "screw 12 tight"), variable=self.lock12).pack(side="left")
        stepper(f, T("팔 (풀림)", "Arm (loose)"), [("−1°", lambda: self.arm(-1, False)), ("−0.1°", lambda: self.arm(-0.1, False)), ("+0.1°", lambda: self.arm(0.1, False)), ("+1°", lambda: self.arm(1, False))])
        stepper(f, T("팔 미세 19", "Arm fine 19"), [("−5′", lambda: self.arm(-5 / 60.0, True)), ("−1′", lambda: self.arm(-1 / 60.0, True)), ("+1′", lambda: self.arm(1 / 60.0, True)), ("+5′", lambda: self.arm(5 / 60.0, True))])
        stepper(f, T("버니어 영점", "Vernier zero"), [("−1°", lambda: self.zero(-1, False)), ("−0.1°", lambda: self.zero(-0.1, False)), ("+0.1°", lambda: self.zero(0.1, False)), ("+1°", lambda: self.zero(1, False)),
                                                   ("−1′", lambda: self.zero(-1 / 60.0, True)), ("+1′", lambda: self.zero(1 / 60.0, True))])
        stepper(f, T("격자대 돌리기", "Turn the stage"), [("−1°", lambda: self.stage(-1)), ("−0.1°", lambda: self.stage(-0.1)), ("−0.02°", lambda: self.stage(-0.02)),
                                                     ("+0.02°", lambda: self.stage(0.02)), ("+0.1°", lambda: self.stage(0.1)), ("+1°", lambda: self.stage(1))])
        stepper(f, T("격자대 수평", "Stage levelling"), [("−0.2°", lambda: self.lev(-0.2)), ("+0.2°", lambda: self.lev(0.2))])
        f = ttk.LabelFrame(ctl, text=T("시료틀 · 시간", "Sample frame · time"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for v, lab in (("film", T("박막 S2", "film S2")), ("glass", T("유리 S3", "glass S3")), ("open", T("빈 칸", "empty"))):
            ttk.Radiobutton(row, text=lab, value=v, variable=self.frame).pack(side="left")
        stepper(f, T("틀 위치", "Frame place"), [("−0.5", lambda: self.slide(-0.5)), ("−0.1", lambda: self.slide(-0.1)), ("+0.1", lambda: self.slide(0.1)), ("+0.5", lambda: self.slide(0.5))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        for s in (1, 10, 30):
            ttk.Radiobutton(row, text="×%d" % s, value=s, variable=self.speed).pack(side="left")
        self.clk = ttk.Label(row, text="")
        self.clk.pack(side="left", padx=8)
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("φ (읽은 값)", "φ (as read)")).pack(side="left")
        self.eph = ttk.Entry(row, width=10)
        self.eph.pack(side="left", padx=2)
        ttk.Button(row, text=T("적기", "Write"), command=self.record).pack(side="left")
        self.sheet = DataSheet(f, [("p", "φ", 80), ("w", T("시료", "sample"), 70), ("r", "R", 110)], height=5)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=400)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("분광기 (위에서) · 버니어 (돋보기) · 카드의 반사광", "The spectrometer from above · the vernier · the card's reflection"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    def touch(self):
        self.idle = 0.0
        self.disp_t = 0

    def pwr(self):
        self.touch()
        self.power = "off" if self.power in ("on", "auto") else "on"

    def lp(self, d):
        self.st["lpos"] = min(1.0, max(0.0, self.st["lpos"] + d))

    def arm(self, d, fine):
        if not self.has("spectro") or fine != self.lock18.get():
            return
        self.th = max(-60.0, min(60.0, self.th + d))

    def zero(self, d, fine):
        if not self.has("spectro") or fine != self.lock9.get():
            return
        self.z += d

    def stage(self, d):
        if self.has("grating") and not self.lock12.get():
            self.st["g"] += d

    def lev(self, d):
        self.st["tilt"] = round(self.st["tilt"] + d, 2)

    def slide(self, d):
        if self.has("sample"):
            self.st["u"] = max(-6.0, min(6.0, round(self.st["u"] + d, 2)))

    def record(self):
        self.sheet.add((self.eph.get(), self.frame.get(), self.show() + " " + dict((k, u) for k, _, u, _, _ in RANGES)[self.rng.get()]))

    def step(self, dt):
        st = self.st
        if st["lamp"]:
            st["warm"] += dt
        else:
            st["warm"] = max(0.0, st["warm"] - 2 * dt)
        R = 1 / self.ph.light(st, self.th)
        tgt, cur = math.log(R), self.logR
        tau = 2.5 * (math.exp(tgt) / 0.2) ** 0.4 if tgt > cur else 1.2 * (math.exp(cur) / 0.2) ** 0.2
        self.logR += (tgt - cur) * (1 - math.exp(-dt / max(0.3, tau)))
        if self.has("dmm"):
            self.idle += dt
            if self.power == "on" and self.idle > 900:
                self.power = "auto"

    def raw(self):
        """the photoresistor's resistance now (Mohm), or None"""
        return math.exp(self.logR) if self.has("detector") else None

    def tick(self, dt):
        self.sync()
        T_ = dt * self.speed.get()
        self.clock += T_
        while T_ > 0:
            h = min(0.5, T_)
            self.step(h)
            T_ -= h
        self.disp_t -= dt
        if self.disp_t <= 0 and self.power == "on":
            self.disp_t = 0.4
            key, full, _, k, dec = [r for r in RANGES if r[0] == self.rng.get()][0]
            R = self.raw()
            if R is None or R > full:
                self.disp = "1"
            else:
                v = R * (1 + (random.random() - 0.5) * 0.003) + (random.random() - 0.5) * 10 ** (-dec) / k * 1.2
                self.disp = "%.*f" % (dec, v * k)
        msg = []
        if self.has("detector") and not self.cover.get():
            msg.append(T("덮개가 열려 방의 빛이 광저항에 들어갑니다.", "The cover is open: the room's light reaches the photoresistor."))
        if self.power == "auto":
            msg.append(T("멀티미터가 자동으로 꺼졌습니다 — 전원을 두 번 누르세요.", "The meter switched itself off: press Power twice."))
        if self.st["lamp"] and self.st["warm"] < 60:
            msg.append(T("램프가 데워지는 중…", "The lamp is warming up…"))
        self.warn.config(text="\n".join(msg))
        self.refresh()

    def refresh(self):
        s = self.show()
        unit = dict((k, u) for k, _, u, _, _ in RANGES)[self.rng.get()]
        self.lbl.config(text=(s + " " + unit) if s not in ("—", "") else s)
        self.clk.config(text="%d:%02d" % (self.clock // 60, self.clock % 60))
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        if not self.has("spectro"):
            cv.create_text(380, 320, text=T("분광기를 조립 탭에서 놓으세요", "Place the spectrometer in the Assembly tab"), fill="#69717a")
            return
        ph, st = self.ph, self.st
        cx, cy, k = 300, 230, 7.0
        lx = cx - (24 + 8 * st["lpos"]) * k
        cv.create_rectangle(lx - 50, cy - 26, lx, cy + 26, fill="#2a2d33", outline="")
        if st["lamp"]:
            cv.create_line(lx, cy, cx, cy, fill="#f5e6b0", width=4)
        cv.create_rectangle(cx - 100, cy - 20, cx - 95, cy + 20, fill="#2a2d33", outline="")
        if st["card"]:
            cv.create_rectangle(cx - ph.a * k - 2, cy - 24, cx - ph.a * k + 2, cy + 24, fill="#fbfbf8", outline="#999")
        # the protractor
        for v in range(-90, 91):
            a = (v + self.z) * RAD
            L0 = 10 if v % 10 == 0 else (6 if v % 5 == 0 else 3)
            cv.create_line(cx + math.cos(a) * (80 - L0), cy + math.sin(a) * (80 - L0), cx + math.cos(a) * 80, cy + math.sin(a) * 80, fill="#222")
            if v % 10 == 0:
                cv.create_text(cx + math.cos(a) * 64, cy + math.sin(a) * 64, text=str(abs(v)), font=("Helvetica", 7))
        cv.create_oval(cx - 26, cy - 26, cx + 26, cy + 26, fill="#8d939b", outline="")
        if self.has("grating"):
            n = (st["g"] - ph.gN) * RAD
            cv.create_line(cx - math.sin(n) * 14, cy + math.cos(n) * 14, cx + math.sin(n) * 14, cy - math.cos(n) * 14, fill="#2b6cb0", width=3)
            if st["lamp"]:
                th0 = st["g"] - ph.gN
                for l in range(420, 701, 20):
                    for sg in (1, -1):
                        s = sg * l / DG - math.sin(th0 * RAD)
                        th = math.asin(s) / RAD + th0
                        r, g, b = wl_rgb(l)
                        cv.create_line(cx, cy, cx + math.cos(th * RAD) * 208, cy + math.sin(th * RAD) * 208, fill="#%02x%02x%02x" % (int(150 + 100 * r), int(150 + 100 * g), int(150 + 100 * b)))
        u = (math.cos(self.th * RAD), math.sin(self.th * RAD))
        E = (cx + u[0] * 208, cy + u[1] * 208)
        cv.create_line(cx, cy, E[0], E[1], fill="#9aa1a8", width=12)
        cv.create_line(cx + u[0] * 78, cy + u[1] * 78, cx + u[0] * 96, cy + u[1] * 96, fill="#c0392b", width=2)
        if self.has("detector"):
            cv.create_oval(E[0] - 9, E[1] - 9, E[0] + 9, E[1] + 9, fill="#c9b27a", outline="#7a6a3a")
        else:
            c = ph.seen(st, self.th)
            cv.create_oval(E[0] - 10, E[1] - 10, E[0] + 10, E[1] + 10, fill="#%02x%02x%02x" % c if c else "#fbfbf8", outline="#999")
        # the vernier through the magnifier
        x0, y0, w, h = 520, 40, 230, 150
        phi = self.reading()
        cv.create_rectangle(x0, y0, x0 + w, y0 + h, fill="#fbfaf4", outline="#888")
        ppd, vx, ym = w / 7.5, x0 + w / 2, y0 + h * 0.5
        v = math.floor((phi - 3.6) * 2) / 2
        while v <= phi + 3.6:
            X = vx + (v - phi) * ppd
            full = abs(v - round(v)) < 1e-6
            cv.create_line(X, ym, X, ym - (24 if full else 13), fill="#222", width=2 if full else 1)
            if full:
                cv.create_text(X, ym - 36, text=str(abs(int(round(v)))), font=("Helvetica", 10, "bold"))
            v += 0.5
        cv.create_rectangle(x0 + 1, ym, x0 + w - 1, y0 + h - 1, fill="#d9dde1", outline="")
        for i in range(-6, 7):
            X = vx + i * (25 / 60.0) * ppd
            cv.create_line(X, ym, X, ym + (22 if i % 3 == 0 else 14), fill="#c0392b" if i == 0 else "#222", width=2 if i == 0 else 1)
            if i % 3 == 0:
                cv.create_text(X, ym + 34, text="%d′" % (abs(i) * 5), font=("Helvetica", 8))
        cv.create_text(x0 + w / 2, y0 - 12, text=T("버니어 (위 30′, 아래 5′)", "Vernier (top 30′, bottom 5′)"), font=("Helvetica", 9, "bold"))
        # the card's face: the hole and the grating's reflection
        if st["card"]:
            x0, y0 = 520, 420
            cv.create_rectangle(x0, y0, x0 + 230, y0 + 200, fill="#fbfbf8", outline="#999")
            hx, hy, kk = x0 + 115, y0 + 100, 3.4
            cv.create_oval(hx - 6, hy - 6, hx + 6, hy + 6, fill="#111", outline="")
            for mm in range(-30, 31, 5):
                cv.create_line(hx + mm * kk, y0 + 186, hx + mm * kk, y0 + 194, fill="#999")
            if st["lamp"] and self.has("grating"):
                r = ph.a * 10 * math.tan(2 * (st["g"] - ph.gN) * RAD)
                if abs(r) < 32:
                    cv.create_oval(hx - r * kk - 9, hy - 9, hx - r * kk + 9, hy + 9, fill="#ffe7a0", outline="")
            cv.create_text(x0 + 115, y0 - 12, text=T("카드 (격자 쪽에서, 눈금 5 mm) · a = %.1f cm" % ph.a, "Card (from the grating, ticks 5 mm) · a = %.1f cm" % ph.a), font=("Helvetica", 9, "bold"))
        if self.has("sample"):
            cv.create_text(260, 520, text=T("입구 구멍 앞: ", "At the entrance hole: ") + {"film": T("박막 S2", "film S2"), "glass": T("유리 S3", "glass S3"), "open": T("빈 칸", "empty")}[st["frame"]] + "   u = %+.1f mm" % st["u"], font=("Helvetica", 10))


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
