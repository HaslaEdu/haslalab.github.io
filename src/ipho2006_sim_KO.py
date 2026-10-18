#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  37th International Physics Olympiad  (IPhO 2006, Singapore)
  Experimental Problem :  MICROWAVE INTERFERENCE, REFLECTION, DIFFRACTION
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The transmitter rides on the goniometer's fixed arm, the receiver on
  the movable arm; the receiver's output (mA) is proportional to the
  microwave's AMPLITUDE.  Every path from transmitter to receiver is
  summed as a complex amplitude: straight across, by reflection on the
  object on the rotating table (images), through the beam splitter and
  the two reflectors (Michelson), by tunnelling across the prisms' gap,
  or scattered by every rod of the hidden lattice.
* The slab reflects with the Airy two-surface amplitude; the horns'
  beams are Gaussian in angle, narrower with the lens 3 cm before the
  transmitter's horn.
* lambda, the slab's index and thickness, the prisms' index, the
  lattice constant and the receiver's gain are hidden and randomised.
* Standard library only (tkinter).

    Run:   python3 ipho2006_sim_KO.py
"""

import cmath
import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line

RAD = math.pi / 180
ARML, TABR, PRISM, NL = 62.0, 9.0, 14.0, 6


def vdir(a):
    return (math.cos(a * RAD), -math.sin(a * RAD))


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def vadd(a, b):
    return (a[0] + b[0], a[1] + b[1])


def vmul(a, k):
    return (a[0] * k, a[1] * k)


def vdot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def ang_between(u, v):
    lu, lv = math.hypot(*u) or 1, math.hypot(*v) or 1
    return math.acos(max(-1.0, min(1.0, vdot(u, v) / (lu * lv)))) / RAD


# --------------------------------------------------------------------------
#  Physics core
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.lam = r.uniform(2.82, 2.90)
        self.nF = r.uniform(1.48, 1.58)
        self.tF = 5 * self.lam / (2 * math.sqrt(self.nF ** 2 - math.sin(r.uniform(45, 51) * RAD) ** 2))
        self.nP, self.aL, self.g0 = r.uniform(1.39, 1.48), r.uniform(3.6, 4.0), r.uniform(1.05, 1.25)
        self.rBS, self.tBS = r.uniform(0.50, 0.58), r.uniform(0.76, 0.82)
        self.gh, self.latOff = r.uniform(0.25, 0.45), r.uniform(-0.6, 0.6)

    def k(self):
        return 2 * math.pi / self.lam

    def slab(self, th):
        n, t = self.nF, self.tF
        s, c1 = math.sin(th * RAD), math.cos(th * RAD)
        c2 = math.sqrt(max(1e-9, 1 - s * s / (n * n)))
        r12 = (c1 - n * c2) / (c1 + n * c2)
        d = 2 * self.k() * n * t * c2
        e = cmath.exp(1j * d)
        den = 1 - r12 * r12 * e
        return r12 * (1 - e) / den, (1 - r12 * r12) * cmath.exp(1j * d / 2) / den


class Bench(object):
    """the goniometer's state and the field at the receiver"""
    def __init__(self, ph):
        self.ph = ph
        self.c = (0.0, 0.0)
        self.sT, self.sL, self.sR, self.arm, self.tab = 50.0, 47.0, 50.0, 0.0, 0.0
        self.lens = False
        self.table = None              # bs, film, prisms, lattice
        self.mirrors = {}              # name -> (axis angle, distance)
        self.gap, self.slide = 0.6, 0.0
        self.on = False

    def lensQ(self):
        if not self.lens:
            return 0.0
        e = self.sT - self.sL - 3
        return math.exp(-e * e / (2 * 1.69))

    def beamT(self, psi):
        s = 13 - 7 * self.lensQ()
        return math.exp(-psi * psi / (2 * s * s))

    @staticmethod
    def beamR(psi):
        return math.exp(-psi * psi / (2 * 169.0))

    def spread(self, r):
        q = self.lensQ()
        return (1 + 0.25 * q) * (100 / (r + 30)) ** (0.8 - 0.4 * q)

    def prism_face(self):
        return PRISM * math.sqrt(3) / 4 + self.gap / 2

    def pT(self):
        return vadd(self.c, (-self.sT, 0))

    def pR(self):
        p = vadd(self.c, vmul(vdir(self.arm), self.sR))
        if self.table == "prisms":
            u = vdir(self.arm)
            p = vadd(p, vmul((-u[1], u[0]), self.slide))
        return p

    def plane_r(self, pl, th):
        if pl["k"] == "refl":
            return -0.62
        if pl["k"] == "bs":
            return self.ph.rBS
        return self.ph.slab(th)[0]

    @staticmethod
    def reflect(p, pl):
        d = vdot(vsub(p, pl["c"]), pl["n"])
        return vsub(p, vmul(pl["n"], 2 * d))

    @staticmethod
    def hit(a, b, pl):
        da, db = vdot(vsub(a, pl["c"]), pl["n"]), vdot(vsub(b, pl["c"]), pl["n"])
        if da * db > 0:
            return None
        t = da / (da - db)
        q = vadd(a, vmul(vsub(b, a), t))
        return q, abs(vdot(vsub(q, pl["c"]), (-pl["n"][1], pl["n"][0])))

    def refl_path(self, pT, pR, planes, coef):
        imgs = [pT]
        for pl in planes:
            imgs.append(self.reflect(imgs[-1], pl))
        tgt, pts, soft = pR, [pR], 1.0
        for i in range(len(planes) - 1, -1, -1):
            h = self.hit(imgs[i + 1], tgt, planes[i])
            if h is None:
                return None
            q, along = h
            if along > planes[i]["hw"]:
                soft *= math.exp(-((along - planes[i]["hw"]) / 1.5) ** 2)
            if soft < 1e-3:
                return None
            tgt = q
            pts.append(q)
        pts.append(pT)
        pts.reverse()
        L = math.hypot(*vsub(pR, imgs[-1]))
        a = soft * self.beamT(ang_between((1, 0), vsub(pts[1], pT))) * self.beamR(ang_between(vmul(vdir(self.arm), -1), vsub(pts[-2], pR))) * self.spread(L)
        a = complex(a)
        for i, pl in enumerate(planes):
            inc = ang_between(vmul(vsub(pts[i + 1], pts[i]), -1), pl["n"])
            th = min(inc, 180 - inc)
            a *= self.plane_r(pl, th)
            if pl.get("onTab"):
                R = 10 / (2.2 + 4 * (1 - self.lensQ()))
                a *= math.erf(R * math.cos(th * RAD) / math.sqrt(2))
        for c in coef:
            a *= c
        return a * cmath.exp(1j * self.ph.k() * L)

    def field(self):
        ph = self.ph
        if not self.on:
            return 0j
        pT, pR, tk = self.pT(), self.pR(), self.table
        L = math.hypot(*vsub(pR, pT))
        a = complex(self.beamT(ang_between((1, 0), vsub(pR, pT))) * self.beamR(ang_between(vmul(vdir(self.arm), -1), vsub(pT, pR))) * self.spread(L))
        nn = vsub(pR, pT)
        ln = math.hypot(*nn) or 1
        cross = abs(vdot(vsub(self.c, pT), (-nn[1] / ln, nn[0] / ln))) < 9
        if cross and tk == "bs":
            a *= ph.tBS
        elif cross and tk == "film":
            th = ang_between((1, 0), vdir(self.tab))
            a *= ph.slab(min(th, 180 - th))[1]
        elif cross and tk == "prisms":
            a *= 0.004
        elif cross and tk == "lattice":
            a *= 0.3
        E = a * cmath.exp(1j * ph.k() * L)
        tp = None
        if tk in ("bs", "film"):
            tp = {"k": tk, "c": self.c, "n": vdir(self.tab), "hw": 9 if tk == "bs" else 8, "onTab": tk == "film"}
            p = self.refl_path(pT, pR, [tp], [])
            E += p or 0
        for name, (ax, dist) in self.mirrors.items():
            u = vdir(ax)
            m = {"k": name, "c": vadd(self.c, vmul(u, dist)), "n": vmul(u, -1), "hw": 11 if name == "refl" else 8}
            for path in (self.refl_path(pT, pR, [m], []),) + ((self.refl_path(pT, pR, [m, tp], [ph.tBS]), self.refl_path(pT, pR, [tp, m], [ph.tBS])) if tp and tp["k"] == "bs" else ()):
                E += path or 0
        if tk == "prisms" and abs(self.arm) <= 14:
            th1 = 60 + self.tab / ph.nP
            s = ph.nP * math.sin(th1 * RAD)
            g = ph.k() * math.sqrt(max(0.0, s * s - 1))
            best = ph.latOff + ph.gh * self.gap
            amp = 1.95 * (0.55 + 0.45 * self.lensQ()) * math.exp(-g * self.gap) * math.exp(-((self.slide - best) / 1.6) ** 2)
            amp *= math.exp(-(max(0.0, self.sR - self.prism_face()) / 2.5) ** 2) * math.exp(-(self.arm / 5) ** 2) * math.exp(-(self.tab / 6) ** 2)
            E += amp * cmath.exp(1j * (ph.k() * (self.sT + self.sR) + 0.3 * self.gap))
        if tk == "lattice":
            q, s = self.lensQ(), 0
            h = (NL - 1) / 2.0
            for i in range(NL):
                for j in range(NL):
                    l = ((i - h) * ph.aL, (j - h) * ph.aL)
                    ca, sa = math.cos(self.tab * RAD), math.sin(self.tab * RAD)
                    r = vadd(self.c, (l[0] * ca + l[1] * sa, -l[0] * sa + l[1] * ca))
                    dT, dR = math.hypot(*vsub(r, pT)), math.hypot(*vsub(pR, r))
                    ph_ = ph.k() * ((r[0] - pT[0] if q > 0.5 else dT) + dR)
                    w = self.beamT(ang_between((1, 0), vsub(r, pT))) * self.beamR(ang_between(vmul(vdir(self.arm), -1), vsub(r, pR))) * self.spread(dT) * (60 / (dR + 20)) ** 0.6
                    s += w * cmath.exp(1j * ph_)
            E += 0.028 * s + complex(0.045 * math.cos(0.7 * self.arm * RAD + 1.3), 0.03)
        return E

    def meter(self):
        return self.ph.g0 * abs(self.field())


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def box_art(col, w, h):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_rectangle(x - w * s, y - h * s, x + w * s, y + h * s, fill=col, outline="#555")
    return art


def art_gonio(cv, x, y, sc=1.0):
    s = sc
    cv.create_line(x - 60 * s, y, x + 60 * s, y, fill="#9aa1a8", width=max(1, 6 * s))
    cv.create_oval(x - 14 * s, y - 14 * s, x + 14 * s, y + 14 * s, fill="#8d939b", outline="#555")


ART = {"gonio": art_gonio, "tx": box_art("#2b6cb0", 18, 12), "rx": box_art("#c0392b", 18, 12), "psu": box_art("#5a6168", 16, 12), "dmm": box_art("#e3b72d", 18, 28),
       "lens": box_art("#ece6d2", 6, 18), "bs": box_art("#5a8cdc", 3, 18), "refl": box_art("#d9dde2", 3, 18), "film": box_art("#f1efe6", 7, 18),
       "prisms": box_art("#efe2b8", 18, 14), "lattice": box_art("#d7c8a6", 22, 22), "ruler": box_art("#d6e4ec", 50, 5), "caliper": box_art("#c9ced3", 30, 6)}
PARTS = [
    ("gonio",   ("[J·L] 각도기와 회전대", "[J·L] Goniometer and rotating table"), []),
    ("tx",      ("[A] 마이크로파 송신기", "[A] Microwave transmitter"), ["gonio"]),
    ("rx",      ("[B] 마이크로파 수신기", "[B] Microwave receiver"), ["gonio"]),
    ("psu",     ("[E] 송신기 전원", "[E] Transmitter power supply"), []),
    ("dmm",     ("[D] 멀티미터", "[D] Multimeter"), []),
    ("lens",    ("[N] 평면-원통 렌즈", "[N] Plano-cylindrical lens"), ["gonio"]),
    ("bs",      ("[H] 반투과판", "[H] Beam splitter"), ["gonio"]),
    ("refl",    ("[G] 반사판", "[G] Reflector"), []),
    ("film",    ("[F] 고분자 판", "[F] Polymer slab"), []),
    ("prisms",  ("[O] 왁스 프리즘 2개", "[O] Two wax prisms"), ["gonio"]),
    ("lattice", ("[I] 금속봉 격자 상자", "[I] Metal-rod lattice box"), ["gonio"]),
    ("ruler",   ("자 (30 cm)", "Ruler (30 cm)"), []),
    ("caliper", ("버니어 캘리퍼", "Vernier caliper"), []),
]
ZONES = {"gonio": (330, 200, 130, 30), "tx": (220, 140, 36, 24), "rx": (440, 140, 36, 24), "psu": (90, 330, 32, 24), "dmm": (620, 330, 36, 56),
         "lens": (280, 140, 12, 36), "bs": (330, 260, 10, 36), "refl": (520, 260, 10, 36), "film": (580, 260, 14, 36), "prisms": (200, 260, 36, 28),
         "lattice": (110, 200, 44, 44), "ruler": (330, 420, 100, 14), "caliper": (560, 420, 60, 14)}
SCENE_TITLE = ("각도기·송신기·수신기·렌즈·회전대 위 부품과 멀티미터", "Goniometer, transmitter, receiver, lens, table parts and the multimeter")
APP_TITLE = ("IPhO 2006 실험 — 마이크로파의 간섭·반사·회절", "IPhO 2006 Experiment — Microwave interference, reflection and diffraction")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    PARTSET = {"1": "bs", "2": "film", "3": "prisms", "4": "lattice"}

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.b = Bench(self.ph)
        self.part = tk.StringVar(value="1")
        self.on = tk.BooleanVar(value=False)
        self.lens = tk.BooleanVar(value=False)
        self.rng = tk.StringVar(value="2m")
        self.posG = 12.0            # the reflector G on its axis, cm from the ruler's zero
        self.disp, self.disp_t = 0.0, 0.0
        self.build()
        self.setup()

    def has(self, k):
        return k in self.app.placed

    def setup(self):
        """a new part: lay it out, the receiver's horn against the prism in Part 3"""
        self.sync()
        b = self.b
        if self.part.get() == "3" and b.table == "prisms":
            b.arm, b.tab = 0.0, 0.0
            b.sR = b.prism_face()

    def sync(self):
        """what each part of the problem needs, as far as the parts are on the bench"""
        b = self.b
        p = self.part.get()
        k = self.PARTSET[p]
        b.table = k if self.has(k) else None
        b.mirrors = {}
        if p == "1":
            if self.has("refl"):
                b.mirrors["refl"] = (0, TABR + 4 + self.posG)
            if self.has("film"):
                b.mirrors["film"] = (-90, 30)

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("멀티미터 (수신기 출력)", "Multimeter (receiver output)"))
        f.pack(fill="x", pady=2)
        self.lbl = tk.Label(f, text="", font=("Courier", 18, "bold"), bg="#9fae8f", fg="#1b1d20", width=12)
        self.lbl.pack(anchor="w", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for md in ("200u", "2m", "20m"):
            ttk.Radiobutton(row, text=md.replace("u", "µ"), value=md, variable=self.rng).pack(side="left")
        ttk.Checkbutton(row, text=T("송신기 켜기", "Transmitter on"), variable=self.on).pack(side="left", padx=8)
        f = ttk.LabelFrame(ctl, text=T("실험 파트 (회전대 위의 부품)", "Part (what stands on the table)"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for v, lab in (("1", T("1 마이클슨", "1 Michelson")), ("2", T("2 박막", "2 Thin film")), ("3", T("3 FTIR", "3 FTIR")), ("4", T("4 브래그", "4 Bragg"))):
            ttk.Radiobutton(row, text=lab, value=v, variable=self.part, command=self.setup).pack(side="left")
        ttk.Checkbutton(f, text=T("렌즈 N을 송신기 앞에", "Lens N before the transmitter"), variable=self.lens).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("각도기", "Goniometer"))
        f.pack(fill="x", pady=2)
        stepper(f, T("움직이는 팔", "Movable arm"), [("−5°", lambda: self.turn("arm", -5)), ("−1°", lambda: self.turn("arm", -1)), ("−0.5°", lambda: self.turn("arm", -0.5)),
                                                  ("+0.5°", lambda: self.turn("arm", 0.5)), ("+1°", lambda: self.turn("arm", 1)), ("+5°", lambda: self.turn("arm", 5))])
        stepper(f, T("회전대", "Table"), [("−5°", lambda: self.turn("tab", -5)), ("−1°", lambda: self.turn("tab", -1)), ("−0.5°", lambda: self.turn("tab", -0.5)),
                                         ("+0.5°", lambda: self.turn("tab", 0.5)), ("+1°", lambda: self.turn("tab", 1)), ("+5°", lambda: self.turn("tab", 5))])
        stepper(f, T("송신기 A · 렌즈 N", "Transmitter A · lens N"), [("A−1", lambda: self.mv("sT", -1)), ("A+1", lambda: self.mv("sT", 1)), ("N−0.5", lambda: self.mv("sL", -0.5)), ("N+0.5", lambda: self.mv("sL", 0.5))])
        stepper(f, T("수신기 B", "Receiver B"), [("−1", lambda: self.mv("sR", -1)), ("+1", lambda: self.mv("sR", 1))])
        f = ttk.LabelFrame(ctl, text=T("반사판 G · 프리즘", "Reflector G · prisms"))
        f.pack(fill="x", pady=2)
        stepper(f, T("G (자 위)", "G (on the ruler)"), [("−1 cm", lambda: self.g(-1)), ("−1 mm", lambda: self.g(-0.1)), ("+1 mm", lambda: self.g(0.1)), ("+1 cm", lambda: self.g(1))])
        stepper(f, T("틈 d · B 밀기", "Gap d · slide B"), [("d−1mm", lambda: self.gap(-0.1)), ("d+1mm", lambda: self.gap(0.1)), ("B⇠", lambda: self.sl(-0.1)), ("B⇢", lambda: self.sl(0.1))])
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("x (읽은 값)", "x (as read)")).pack(side="left")
        self.ex = ttk.Entry(row, width=10)
        self.ex.pack(side="left", padx=2)
        ttk.Button(row, text=T("적기", "Write"), command=self.record).pack(side="left")
        self.sheet = DataSheet(f, [("x", "x", 90), ("p", T("파트", "part"), 50), ("s", "S", 100)], height=5)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=420)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("각도기를 위에서 · 눈금 · 자와 캘리퍼", "The goniometer from above · scales · ruler and caliper"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#c99a62", highlightthickness=0)
        self.cv.pack()

    def turn(self, which, d):
        if not self.has("gonio"):
            return
        b = self.b
        if which == "arm":
            b.arm = max(-150.0, min(150.0, round(b.arm + d, 2)))
        else:
            b.tab = round(((b.tab + d + 180) % 360) - 180, 2)

    def mv(self, which, d):
        b = self.b
        if which == "sT":
            b.sT = max(b.sL + 1 if b.lens else 14, min(ARML, b.sT + d))
        elif which == "sL":
            b.sL = max(TABR + 3, min(b.sT - 1, b.sL + d))
        else:
            lo = b.prism_face() if b.table == "prisms" else (TABR + 4 if b.table else 8)
            b.sR = max(lo, min(ARML, b.sR + d))

    def g(self, d):
        self.posG = max(0.0, min(30.0, round(self.posG + d, 2)))

    def gap(self, d):
        b = self.b
        touching = b.sR - b.prism_face() < 0.3
        b.gap = max(0.2, min(3.0, round(b.gap + d, 2)))
        if touching:
            b.sR = b.prism_face()

    def sl(self, d):
        self.b.slide = max(-5.0, min(5.0, round(self.b.slide + d, 2)))

    def show(self):
        if not self.has("dmm"):
            return "—"
        full = {"200u": 0.1999, "2m": 1.999, "20m": 19.99}[self.rng.get()]
        v = self.disp
        if v > full:
            return "1"
        if self.rng.get() == "200u":
            return "%.1f µA" % (v * 1000)
        return ("%.3f" if full < 2 else "%.2f") % v + " mA"

    def record(self):
        self.sheet.add((self.ex.get(), self.part.get(), self.show()))

    def tick(self, dt):
        b = self.b
        b.on = self.on.get() and self.has("tx") and self.has("rx") and self.has("psu") and self.has("gonio")
        b.lens = self.lens.get() and self.has("lens")
        self.sync()
        self.disp_t -= dt
        if self.disp_t <= 0:
            self.disp_t = 0.4
            self.disp = b.meter() + (random.random() - 0.5) * 0.003 + 0.002
        msg = ""
        if self.part.get() == "1" and not (self.has("refl") and self.has("film") and self.has("bs")):
            msg = T("마이클슨에는 반투과판 H, 반사판 G, 고분자 판 F가 필요합니다.", "The Michelson needs the splitter H, reflector G and slab F.")
        self.warn.config(text=msg)
        self.refresh()

    def refresh(self):
        self.lbl.config(text=self.show())
        self.draw()

    def draw(self):
        cv, b, ph = self.cv, self.b, self.ph
        cv.delete("all")
        if not self.has("gonio"):
            cv.create_text(380, 320, text=T("각도기를 조립 탭에서 놓으세요", "Place the goniometer in the Assembly tab"))
            return
        z = 4.0
        b.c = (0.0, 0.0)
        X = lambda p: 280 + p[0] * z
        Y = lambda p: 300 + p[1] * z
        cv.create_line(X((-ARML, 0)), Y((0, 0)), X((0, 0)), Y((0, 0)), fill="#c3c8ce", width=12)
        e = vmul(vdir(b.arm), ARML)
        cv.create_line(X((0, 0)), Y((0, 0)), X(e), Y(e), fill="#b7bdc3", width=12)
        cv.create_oval(X((-TABR, 0)), Y((0, -TABR)), X((TABR, 0)), Y((0, TABR)), fill="#8d939b", outline="#555")
        if self.has("tx"):
            p = b.pT()
            cv.create_rectangle(X(p) - 48, Y(p) - 18, X(p), Y(p) + 18, fill="#2b6cb0", outline="")
        if b.lens:
            p = (-b.sL, 0)
            cv.create_rectangle(X(p) - 4, Y(p) - 30, X(p) + 6, Y(p) + 30, fill="#ece6d2", outline="#999")
        if self.has("rx"):
            p = b.pR()
            u = vdir(b.arm)
            cv.create_line(X(p), Y(p), X(vadd(p, vmul(u, 12))), Y(vadd(p, vmul(u, 12))), fill="#c0392b", width=30)
        t = b.table
        if t in ("bs", "film"):
            n = vdir(b.tab)
            r = (-n[1], n[0])
            w = 9
            cv.create_line(X(vmul(r, -w)), Y(vmul(r, -w)), X(vmul(r, w)), Y(vmul(r, w)), fill="#5a8cdc" if t == "bs" else "#f1efe6", width=4 if t == "bs" else max(4, ph.tF * z))
        if t == "prisms":
            s, h, g = PRISM, PRISM * math.sqrt(3) / 2, b.gap
            off = (0.5 * g, -math.sqrt(3) / 2 * g)
            for tri in (((-h / 2, -s / 4), (-h / 2, 3 * s / 4), (h / 2, s / 4)), tuple(vadd(p, off) for p in ((-h / 2, -s / 4), (h / 2, s / 4), (h / 2, -3 * s / 4)))):
                cv.create_polygon(*[c for p in tri for c in (X(p), Y(p))], fill="#efe2b8", outline="#9a8a5a")
        if t == "lattice":
            u, v, hw = vdir(b.tab), (-vdir(b.tab)[1], vdir(b.tab)[0]), 13
            q = [vadd(vmul(u, i * hw), vmul(v, j * hw)) for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            cv.create_polygon(*[c for p in q for c in (X(p), Y(p))], fill="#d7c8a6", outline="#8a7a5a")
            cv.create_line(X(q[0]), Y(q[0]), X(q[2]), Y(q[2]), fill="#c0392b", width=2)
        for name, (ax, dist) in b.mirrors.items():
            p = vmul(vdir(ax), dist)
            n = vdir(ax)
            r = (-n[1], n[0])
            cv.create_line(X(vadd(p, vmul(r, -8))), Y(vadd(p, vmul(r, -8))), X(vadd(p, vmul(r, 8))), Y(vadd(p, vmul(r, 8))), fill="#d9dde2" if name == "refl" else "#f1efe6", width=5)
        # the scales read through the magnifier
        cv.create_rectangle(560, 20, 750, 140, fill="#fbfaf4", outline="#888")
        cv.create_text(655, 34, text=T("팔 눈금 / 회전대 눈금", "arm scale / table scale"), font=("Helvetica", 9, "bold"))
        for row, val in ((70, abs(b.arm)), (115, (180 - b.tab) % 360)):
            for a in range(int(val) - 8, int(val) + 9):
                xx = 655 + (a - val) * 10
                L0 = 14 if a % 5 == 0 else 7
                cv.create_line(xx, row, xx, row - L0, fill="#222")
                if a % 5 == 0:
                    cv.create_text(xx, row - 22, text=str(a % 360), font=("Helvetica", 8))
            cv.create_line(655, row + 4, 655, row - 16, fill="#c0392b", width=2)
        if self.part.get() == "1" and self.has("ruler") and "refl" in b.mirrors:
            cv.create_rectangle(560, 160, 750, 220, fill="#d6e4ec", outline="#8aa")
            v = self.posG
            for mm in range(int((v - 2) * 10), int((v + 2) * 10) + 1):
                if 0 <= mm <= 300:
                    xx = 655 + (mm / 10.0 - v) * 45
                    if 562 < xx < 748:
                        cv.create_line(xx, 160, xx, 160 + (18 if mm % 10 == 0 else 11 if mm % 5 == 0 else 6), fill="#111")
                        if mm % 10 == 0:
                            cv.create_text(xx, 190, text=str(mm // 10), font=("Helvetica", 9, "bold"))
            cv.create_line(655, 150, 655, 220, fill="#c0392b", width=2)
            cv.create_text(655, 232, text=T("자 위의 G 앞면", "G's face on the ruler"), font=("Helvetica", 9))
        if self.has("caliper") and self.has("film"):
            cv.create_text(655, 260, text=T("캘리퍼: F 두께", "Caliper: F's thickness"), font=("Helvetica", 9, "bold"))
            v = ph.tF * 10
            zz = 2.4
            x0 = 562
            cv.create_rectangle(x0, 280, x0 + 60 * zz, 300, fill="#d9dde2", outline="#777")
            for mm in range(0, 61):
                cv.create_line(x0 + mm * zz, 280, x0 + mm * zz, 280 + (10 if mm % 10 == 0 else 5), fill="#111")
                if mm % 10 == 0:
                    cv.create_text(x0 + mm * zz, 296, text=str(mm // 10), font=("Helvetica", 7))
            vx = x0 + v * zz
            for i in range(21):
                cv.create_line(vx + i * 0.95 * zz, 302, vx + i * 0.95 * zz, 302 + (10 if i % 10 == 0 else 5), fill="#111")
        if b.table == "prisms":
            cv.create_text(655, 360, text=T("틈 d = %.1f cm (캘리퍼)" % b.gap, "gap d = %.1f cm (caliper)" % b.gap), font=("Helvetica", 10))
        cv.create_text(20, 620, anchor="w", text="A %.1f  N %.1f  B %.1f   B slide %+.1f" % (b.sT, b.sL, b.sR, b.slide), font=("Courier", 10))


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
