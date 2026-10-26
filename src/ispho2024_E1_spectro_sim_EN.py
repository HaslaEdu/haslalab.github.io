#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  International Scientific Physics Olympiad  (ISPhO 2024)
  Experimental Problem 1 :  ABSORPTION SPECTROSCOPY AND CHEMICAL KINETICS
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Apparatus after the problem sheet: an optical table with the holder
    for the light source, lens L1, the holder for 1.05 cm cuvettes, lens
    L2 carrying a diffraction grating, a diaphragm and the screen with a
    CCD array of about 3650 pixels read by the "Spectroscopy" program
    (intensity in arbitrary units, overflow at 4095, adjustable
    Sensitivity, single spectra and time series); three light sources
    (LED-RGB 620 / 520 / 460 nm, the full-spectrum LED-CON and LED-UNK)
    on a DC supply up to 15 V through an adapter with a switch and a 4-
    or 2-output connector; a sunshield.  Chemistry: distilled water,
    NaOH granules of the mass printed on the microtube, indigo carmine
    IC 0.70 mg/ml, phenolphthalein In, glucose Gl 0.50 mol/l, NaCl
    0.30 mol/l, insulin syringes 0.5 ml that squeeze drops of their own
    volume, 3 ml syringes, 10 cuvettes with caps, gloves.
    The light obeys the Beer-Lambert law through the cuvette; IC has its
    own absorption cross-section; In2- fades by
    In2- + p OH-  <->  In2-(OH)p  at a rate set by [OH-] and the ionic
    strength; IC in glucose + NaOH uses up the dissolved oxygen and then
    runs through its coloured states (the chemical traffic light), and
    shaking the capped cuvette brings oxygen back.
    Only what the real program shows is displayed: intensity against
    pixel number.  No wavelength, cross-section, concentration or fit is
    ever computed for you.  Every hidden true parameter is randomised for
    each session.

    Run:   python3 ispho2024_E1_spectro_sim_EN.py   [--seed=N]
"""
import math
import random
import sys
import time
import tkinter as tk
from tkinter import ttk, filedialog

# --------------------------------------------------------------------------
# i18n
# --------------------------------------------------------------------------
LANG = "EN"          # the EN edition differs only in this line


def T(ko, en):
    """Bilingual string selector."""
    return ko if LANG == "KO" else en


# --------------------------------------------------------------------------
# Constants as printed on the problem sheet
# --------------------------------------------------------------------------
N_A = 6.02e23
MU = {"NaOH": 40.0, "IC": 466.4, "Gl": 180.0, "NaCl": 58.4}
L_CUV = 1.05e-2         # m, between the smooth inner walls of the cuvette
NPIX = 3650
OVERFLOW = 4095
PSU_MAX = 15.0
TABLE_L = 70.0          # cm
CUV_MAX = 4.5           # ml


def U(a, b):
    return random.uniform(a, b)


def G(l, l0, w):
    return math.exp(-0.5 * ((l - l0) / w) ** 2)


# --------------------------------------------------------------------------
# The hidden truth of this session
# --------------------------------------------------------------------------
class Truth:
    """Everything the student is meant to find out."""

    def __init__(self):
        self.con = [(U(447, 453), U(9, 11), 1.0), (U(548, 562), U(50, 58), U(0.20, 0.24)), (U(615, 630), U(32, 40), U(0.08, 0.12))]
        self.rgb = {"R": (U(617, 623), U(8, 10)), "G": (U(514, 522), U(15, 19)), "B": (U(458, 464), U(10, 12))}
        self.unk = (U(582, 596), U(7, 9))
        self.vth = {"con": U(2.6, 2.9), "rgb": U(1.8, 2.1), "unk": U(1.9, 2.2)}
        self.F1, self.F2 = U(11.6, 12.4), U(11.6, 12.4)
        self.k00, self.l00 = -0.0752 * U(0.97, 1.03), U(664, 678)
        self.dark, self.ron, self.room = U(30, 45), U(1.5, 3), U(0.75, 1.0)
        self.mNaOH = round(U(0.55, 0.66), 3)                     # g, printed on the microtube
        self.Vd = [U(4.2, 5.8) * 1e-3 for _ in range(4)]          # ml, drop of each insulin syringe
        self.ic = dict(a=U(4.8, 5.3) * 1e-21, l1=U(606, 614), w1=U(28, 32), l2=U(560, 572), w2=U(26, 32), a2=U(0.32, 0.40),
                       l3=U(415, 425), w3=U(25, 32), a3=U(0.14, 0.20))
        self.inA, self.inL, self.inW = U(0.20, 0.25), U(548, 556), U(36, 42)
        self.chi, self.p, self.psiR, self.jSlope = U(0.032, 0.042), 1, U(0.03, 0.05), U(0.7, 1.1)
        self.tr = dict(iL=U(535, 545), iW=U(32, 38), fL=U(418, 428), fW=U(30, 36), fA=U(0.55, 0.70), iA=U(0.75, 0.9),
                       kg=U(0.38, 0.52), k1=U(0.10, 0.16), k2=U(0.025, 0.04), kox=U(0.15, 0.25), gA=U(0.5, 0.6), gL=U(440, 450))

    def sig_ic(self, l):
        c = self.ic
        return c["a"] * (G(l, c["l1"], c["w1"]) + c["a2"] * G(l, c["l2"], c["w2"]) + c["a3"] * G(l, c["l3"], c["w3"]))

    def shp_in(self, l):
        return G(l, self.inL, self.inW) + 0.08 * G(l, 370, 25)

    def shp_i(self, l):
        t = self.tr
        return G(l, t["iL"], t["iW"]) + 0.25 * G(l, t["iL"] - 90, 30)

    def shp_f(self, l):
        t = self.tr
        return G(l, t["fL"], t["fW"]) + 0.18 * G(l, 470, 30)


TR = None


# --------------------------------------------------------------------------
# A cuvette and what is in it
# --------------------------------------------------------------------------
class Cuvette:
    def __init__(self, i):
        self.i = i
        self.V = {"w": 0.0, "naoh": 0.0, "nacl": 0.0, "gl": 0.0}
        self.cNaOH = 0.0
        self.icV = 0.0
        self.inV = 0.0
        self.mixed = True
        self.unmix = 1.0
        self.bubbles = 0.0
        self.cap = False
        self.rot = False
        self.label = ""
        self.ph = {"h": 0.0, "n": 0.0, "b": 0.0}
        self.tr = None

    def vol(self):
        return sum(self.V.values()) + self.icV + self.inV

    def conc(self):
        V = max(1e-6, self.vol())
        return {"OH": self.cNaOH * self.V["naoh"] / V, "Na": (self.cNaOH * self.V["naoh"] + 0.30 * self.V["nacl"]) / V,
                "Cl": 0.30 * self.V["nacl"] / V, "Gl": 0.50 * self.V["gl"] / V}

    def ionJ(self):
        q = self.conc()
        return 0.5 * (q["Na"] + q["OH"] + q["Cl"])

    def nIC(self):
        V = self.vol() * 1e-6
        if V <= 0:
            return 0.0
        m = 0.70e-3 * self.icV
        return m / MU["IC"] * N_A / V

    def absorb(self, l):
        A = 0.0
        n = self.nIC()
        if n > 0:
            if self.tr:
                t, R = self.tr, TR.tr
                s = (TR.sig_ic(l) + TR.ic["a"] * R["gA"] * G(l, R["gL"], 30)) * n * L_CUV
                A += s * t["n"] + n * L_CUV * TR.ic["a"] * (R["iA"] * TR.shp_i(l) * t["i"] + R["fA"] * TR.shp_f(l) * t["f"])
            else:
                A += TR.sig_ic(l) * n * L_CUV
        if self.inV > 0:
            A += TR.inA * self.ph["n"] * TR.shp_in(l) * 3.0 / max(1.0, self.vol())
        return A

    def step(self, dt):
        q = self.conc()
        if self.inV > 0 and q["OH"] >= 1e-4:
            p = self.ph
            f = max(0.2, 1 + TR.jSlope * (math.sqrt(self.ionJ()) - math.sqrt(0.30)))
            p["n"] += p["h"]
            p["h"] = 0.0
            kf = TR.chi * q["OH"] ** TR.p * f
            kb = TR.psiR * TR.chi * 0.30
            tot = p["n"] + p["b"]
            ne = tot * kb / (kf + kb)
            p["n"] = ne + (p["n"] - ne) * math.exp(-(kf + kb) * dt)
            p["b"] = tot - p["n"]
        if self.tr:
            t, R = self.tr, TR.tr
            r = max(0.0, q["OH"] * q["Gl"]) / (0.15 * 0.25)
            t["O"] = max(0.0, t["O"] - R["kg"] * 0.0375 * r * dt)
            sw = 1 / (1 + (t["O"] / 0.08) ** 4)
            k1, k2, ko = R["k1"] * r * sw, R["k2"] * r * sw, R["kox"] * t["O"]
            n = max(1, int(math.ceil(dt / 0.2)))
            h = dt / n
            for _ in range(n):
                dn = -k1 * t["n"] + ko * t["i"]
                di = k1 * t["n"] - k2 * t["i"] - ko * t["i"] + ko * t["f"] * 0.5
                df = k2 * t["i"] - ko * t["f"] * 0.5
                t["n"] += dn * h
                t["i"] += di * h
                t["f"] += df * h
            s = t["n"] + t["i"] + t["f"]
            if s > 0:
                for k in ("n", "i", "f"):
                    t[k] /= s
        if self.bubbles > 0 and not self.cap:
            self.bubbles = max(0.0, self.bubbles - dt / 400)

    def colour(self):
        if self.vol() < 0.05:
            return "#e1eef5"
        ch = []
        for l0, w in ((600, 40), (545, 35), (450, 30)):
            s = n = 0.0
            for l in range(400, 701, 10):
                g = G(l, l0, w)
                s += g * math.exp(-self.absorb(l) * 0.9)
                n += g
            ch.append(int(25 + 230 * s / n))
        return "#%02x%02x%02x" % tuple(ch)


# --------------------------------------------------------------------------
# The bench: optics, light source, sensor
# --------------------------------------------------------------------------
class Bench:
    def __init__(self):
        self.x = {"holder": 4.0, "L1": 18.0, "cuvhold": 24.0, "L2": 32.0, "screen": 40.0}
        self.diaphragm = False
        self.sunshield = True
        self.src = "ledrgb"          # in the holder
        self.plugged = True          # the right connector on the board in the holder
        self.pin = "R"
        self.psu_on = False
        self.psu_v = 0.0
        self.ad_sw = False
        self.jit = 0.0
        self.sens = 4
        self.t = 0.0
        self.cuv = [Cuvette(i) for i in range(10)]
        self.in_holder = None
        self.naoh = None             # (V ml, c mol/l) of the stock made from the granules

    def nudge(self, s):
        self.jit += random.gauss(0, s)

    def brightness(self):
        if not (self.src and self.plugged and self.psu_on and self.ad_sw):
            return 0.0
        k = {"ledcon": "con", "ledrgb": "rgb", "ledunk": "unk"}[self.src]
        return max(0.0, self.psu_v - TR.vth[k]) / (PSU_MAX - TR.vth[k])

    def optics(self):
        x = self.x
        if not (x["holder"] < x["L1"] < x["L2"] < x["screen"]):
            return None
        e1 = (x["L1"] - x["holder"]) - TR.F1
        e2 = (x["screen"] - x["L2"]) - TR.F2
        amp = 1 / (1 + (e1 / 1.4) ** 2) / (1 + (e2 / 4) ** 2)
        return e1, e2, amp, 0.4 + 2.0 * abs(e2) + 1.1 * abs(e1)

    def scale(self):
        L2S = max(4.0, self.x["screen"] - self.x["L2"])
        k0 = TR.k00 * TR.F2 / L2S
        lc = TR.l00 + TR.k00 * NPIX / 2
        return k0, lc - k0 * NPIX / 2 + self.jit

    def emission(self, l):
        b = self.brightness()
        if b <= 0:
            return 0.0
        if self.src == "ledcon":
            return 1.6 * b * sum(a * G(l, l0, w) for l0, w, a in TR.con)
        if self.src == "ledrgb":
            l0, w = TR.rgb[self.pin]
            return 1.2 * b * G(l, l0, w)
        l0, w = TR.unk
        return 1.1 * b * G(l, l0, w)

    def room(self, l):
        return (0.06 if self.sunshield else 1.0) * TR.room * (0.55 * G(l, 546, 6) + 0.4 * G(l, 612, 8) + 0.35 * G(l, 436, 5) + 0.25 * G(l, 560, 60))

    def trans(self, l):
        if self.in_holder is None:
            return 1.0
        c = self.cuv[self.in_holder]
        V = c.vol()
        T0 = 0.93 if V > 0.2 else 0.86
        if c.rot:
            T0 *= 0.33
        if c.bubbles > 0:
            T0 *= math.exp(-0.25 * c.bubbles)
        fill = max(0.0, min(1.0, (V - 1.6) / 0.6))
        A = c.absorb(l)
        if not c.mixed:
            A *= c.unmix
        return T0 * (fill * math.exp(-A) + (1 - fill))

    def frame(self):
        o = self.optics()
        k0, l0 = self.scale()
        gain = 2.0 ** (self.sens - 4)
        dia, roomF = (0.55, 0.7) if self.diaphragm else (1.0, 1.0)
        rot = self.in_holder is not None and self.cuv[self.in_holder].rot
        out = []
        cache = {}
        for n in range(NPIX):
            l = l0 + k0 * n
            s = 0.0
            if o and self.src:
                key = round(l, 1)
                if key not in cache:
                    w = o[3]
                    cache[key] = (0.5 * self.emission(l) + 0.25 * self.emission(l - w) + 0.25 * self.emission(l + w)) * self.trans(l) * o[2] * dia
                s = cache[key]
            v = TR.dark + gain * (2600 * s + 620 * self.room(l) * roomF) + random.gauss(0, TR.ron * (1 + 0.25 * gain))
            if rot:
                v += random.gauss(0, 25 * s * gain)
            out.append(max(0.0, min(OVERFLOW, v)))
        return out

    def step(self, dt):
        for c in self.cuv:
            c.step(dt)
        self.t += dt

    # ---------------- the chemistry ----------------
    def add(self, c, src, v):
        """Pour v ml of reagent src into cuvette c; returns a message."""
        if c.cap:
            return T("뚜껑을 열어야 넣을 수 있습니다.", "Take the cap off to add anything.")
        if src == "water":
            c.V["w"] += v
        elif src == "nacl":
            c.V["nacl"] += v
        elif src == "gl":
            c.V["gl"] += v
        elif src == "naoh":
            cs = self.naoh[1]
            c.cNaOH = (c.cNaOH * c.V["naoh"] + cs * v) / (c.V["naoh"] + v)
            c.V["naoh"] += v
        elif src == "ic":
            c.icV += v
        elif src == "ind":
            c.inV += v
            c.ph["h"] += v / 0.005
        msg = T("큐벳 %d에 넣었습니다.", "Added to cuvette %d.") % (c.i + 1)
        V = c.vol()
        if V > CUV_MAX:
            f = CUV_MAX / V
            for k in c.V:
                c.V[k] *= f
            c.icV *= f
            c.inV *= f
            for k in c.ph:
                c.ph[k] *= f
            msg = T("큐벳이 넘칩니다 — 넘친 만큼은 흘러 버렸습니다.", "The cuvette overflows — the excess is spilt.")
        c.mixed = False
        c.unmix = U(0.35, 1.9)
        q = c.conc()
        if c.tr is None and c.icV > 0 and q["OH"] > 1e-3 and q["Gl"] > 1e-3:
            c.tr = {"n": 1.0, "i": 0.0, "f": 0.0, "O": 1.0}
        return msg


REAG = [("water", T("증류수", "water")), ("naoh", T("NaOH 용액", "NaOH solution")), ("nacl", "NaCl 0.30 M"), ("gl", "Gl 0.50 M")]


# --------------------------------------------------------------------------
# The window
# --------------------------------------------------------------------------
class App:
    def __init__(self, root, seed=None):
        global TR
        if seed is not None:
            random.seed(seed)
        TR = Truth()
        self.root = root
        self.B = Bench()
        self.live = False
        self.hold = None
        self.cur = None
        self.ts = None
        self.ts_done = None
        self.ts_next = 0.0
        self.ts_dt = 2.0
        self.speed = 1
        self.sw_run, self.sw_t = False, 0.0
        self.view = [0, NPIX]
        self.mouse = None
        self.last = time.time()
        self.acc = 0.0
        self.gloves = False
        self.syr3 = [None, 0.0]                       # reagent, ml
        self.ins = [[None, 0.0] for _ in range(4)]    # reagent, ml
        root.title(T("ISPhO 2024 실험 — 흡수 분광과 화학 반응 속도  ·  HaslaLab",
                     "ISPhO 2024 Experiment — Absorption Spectroscopy and Chemical Kinetics  ·  HaslaLab"))
        root.geometry("1400x880")
        self.build()
        self.tick()

    # ---------------- layout ----------------
    def build(self):
        left = ttk.Frame(self.root, padding=6)
        left.pack(side="left", fill="y")
        right = ttk.Frame(self.root, padding=6)
        right.pack(side="left", fill="both", expand=True)
        nb = ttk.Notebook(left, width=460)
        nb.pack(fill="both", expand=True)
        f_opt, f_src, f_chem = ttk.Frame(nb, padding=6), ttk.Frame(nb, padding=6), ttk.Frame(nb, padding=6)
        nb.add(f_opt, text=T("광학", "Optics"))
        nb.add(f_src, text=T("광원", "Light source"))
        nb.add(f_chem, text=T("화학", "Chemistry"))

        # optics
        ttk.Label(f_opt, text=T("광학대 위 위치 (cm, 왼쪽 끝부터) — 보정한 뒤에는 광원·큐벳·조리개 말고는\n건드리지 마세요. 스펙트럼을 보며 맞추세요.",
                                "Positions on the optical table (cm from its left end) — after calibrating\ntouch nothing but the source, the cuvette and the diaphragm.")).pack(anchor="w")
        self.sx = {}
        for k, lab in [("holder", T("광원 받침대", "source holder")), ("L1", "L1"), ("cuvhold", T("큐벳 받침대", "cuvette holder")),
                       ("L2", "L2 + G"), ("screen", T("스크린 + CCD", "screen + CCD"))]:
            fr = ttk.Frame(f_opt)
            fr.pack(fill="x", pady=2)
            ttk.Label(fr, text=lab, width=14).pack(side="left")
            v = tk.DoubleVar(value=self.B.x[k])
            tk.Scale(fr, from_=1, to=TABLE_L - 1, resolution=0.1, orient="horizontal", variable=v, showvalue=False,
                     length=190, command=lambda _v, k=k: self.on_pos(k)).pack(side="left")
            for d in (-0.1, 0.1):
                ttk.Button(fr, text=("%+.1f" % d), width=4, command=lambda k=k, d=d: self.nudge_pos(k, d)).pack(side="left")
            self.sx[k] = v
        self.dia_v = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_opt, text=T("조리개를 놓음", "diaphragm in place"), variable=self.dia_v,
                        command=lambda: setattr(self.B, "diaphragm", self.dia_v.get())).pack(anchor="w", pady=2)
        self.shield_v = tk.BooleanVar(value=True)
        ttk.Checkbutton(f_opt, text=T("차광판을 세움", "sunshield in place"), variable=self.shield_v,
                        command=lambda: setattr(self.B, "sunshield", self.shield_v.get())).pack(anchor="w", pady=2)
        self.screen_cv = tk.Canvas(f_opt, width=220, height=220, bg="#e6e8ea", highlightthickness=0)
        self.screen_cv.pack(pady=8)

        # light source
        ttk.Label(f_src, text=T("광원 받침대에 꽂은 것", "In the source holder")).pack(anchor="w")
        self.src_v = tk.StringVar(value="ledrgb")
        for val, lab in [("ledrgb", "LED-RGB"), ("ledcon", "LED-CON"), ("ledunk", "LED-UNK"), ("", T("없음", "nothing"))]:
            ttk.Radiobutton(f_src, text=lab, value=val, variable=self.src_v, command=self.on_src).pack(anchor="w")
        self.plug_btn = ttk.Button(f_src, text="", command=self.toggle_plug)
        self.plug_btn.pack(anchor="w", pady=4)
        ttk.Label(f_src, text=T("LED-RGB 단자 (4단자 커넥터)", "LED-RGB output (4-output connector)")).pack(anchor="w", pady=(8, 0))
        self.pin_v = tk.StringVar(value="R")
        fr = ttk.Frame(f_src)
        fr.pack(anchor="w")
        for val in ("R", "G", "B"):
            ttk.Radiobutton(fr, text=val, value=val, variable=self.pin_v, command=lambda: setattr(self.B, "pin", self.pin_v.get())).pack(side="left")
        ttk.Label(f_src, text=T("직류 전원 (0–15 V)", "DC supply (0–15 V)")).pack(anchor="w", pady=(10, 0))
        fr = ttk.Frame(f_src)
        fr.pack(fill="x")
        self.psu_btn = ttk.Button(fr, text="", command=self.toggle_psu)
        self.psu_btn.pack(side="left")
        self.knob_l = tk.Label(fr, text="", font=("Consolas", 16, "bold"), fg="#c0392b")
        self.knob_l.pack(side="left", padx=8)
        fr = ttk.Frame(f_src)
        fr.pack(fill="x", pady=2)
        for d in (-1, -0.1, 0.1, 1):
            ttk.Button(fr, text="%+g V" % d, width=6, command=lambda d=d: self.knob(d)).pack(side="left")
        self.ad_btn = ttk.Button(f_src, text="", command=self.toggle_ad)
        self.ad_btn.pack(anchor="w", pady=4)

        # chemistry
        self.cuv_i = tk.IntVar(value=0)
        fr = ttk.Frame(f_chem)
        fr.pack(fill="x")
        ttk.Label(fr, text=T("큐벳", "Cuvette")).pack(side="left")
        for i in range(10):
            ttk.Radiobutton(fr, text=str(i + 1), value=i, variable=self.cuv_i).pack(side="left")
        fr = ttk.Frame(f_chem)
        fr.pack(fill="x", pady=2)
        for lab, cmd in [(T("뚜껑", "Cap"), self.cap), (T("흔들기", "Shake"), self.shake), (T("톡톡", "Tap"), self.tap),
                         (T("90° 돌리기", "Turn 90°"), self.rot), (T("비우고 씻기", "Empty"), self.empty)]:
            ttk.Button(fr, text=lab, command=cmd).pack(side="left")
        fr = ttk.Frame(f_chem)
        fr.pack(fill="x", pady=2)
        ttk.Button(fr, text=T("받침대에 넣기/빼기", "Into / out of the holder"), command=self.holder).pack(side="left")
        self.label_v = tk.StringVar()
        ttk.Entry(fr, textvariable=self.label_v, width=12).pack(side="left", padx=4)
        ttk.Button(fr, text=T("테이프에 쓰기", "Label"), command=self.label).pack(side="left")
        self.cuv_cv = tk.Canvas(f_chem, width=440, height=110, bg="#e9e7e0", highlightthickness=0)
        self.cuv_cv.pack(pady=4)

        lf = ttk.LabelFrame(f_chem, text=T("NaOH 원액 (장갑!)", "NaOH stock (gloves!)"), padding=4)
        lf.pack(fill="x", pady=2)
        ttk.Label(lf, text=T("알갱이 질량(인쇄): %.3f g", "granule mass (printed): %.3f g") % TR.mNaOH).pack(anchor="w")
        fr = ttk.Frame(lf)
        fr.pack(fill="x")
        self.glove_v = tk.BooleanVar(value=False)
        ttk.Checkbutton(fr, text=T("장갑 낌", "gloves on"), variable=self.glove_v, command=lambda: setattr(self, "gloves", self.glove_v.get())).pack(side="left")
        ttk.Label(fr, text=T("  물을 부어 (ml)", "  water up to (ml)")).pack(side="left")
        self.stock_v = tk.DoubleVar(value=50.0)
        tk.Spinbox(fr, from_=1, to=100, increment=0.1, width=6, textvariable=self.stock_v).pack(side="left")
        ttk.Button(fr, text=T("녹이기", "Dissolve"), command=self.dissolve).pack(side="left", padx=4)

        lf = ttk.LabelFrame(f_chem, text=T("3 ml 주사기 (눈금 0.1 ml)", "3 ml syringe (0.1 ml marks)"), padding=4)
        lf.pack(fill="x", pady=2)
        fr = ttk.Frame(lf)
        fr.pack(fill="x")
        self.r3_v = tk.StringVar(value="water")
        for val, lab in REAG:
            ttk.Radiobutton(fr, text=lab, value=val, variable=self.r3_v).pack(side="left")
        fr = ttk.Frame(lf)
        fr.pack(fill="x")
        for d in (-1, -0.1, 0.1, 1):
            ttk.Button(fr, text="%+g ml" % d, width=7, command=lambda d=d: self.draw3(d)).pack(side="left")
        ttk.Button(fr, text=T("큐벳에", "into cuvette"), command=self.inj3).pack(side="left")
        ttk.Button(fr, text=T("폐액", "waste"), command=lambda: self.syr3.__setitem__(1, 0.0)).pack(side="left")
        self.s3_cv = tk.Canvas(lf, width=430, height=44, bg="#e9e7e0", highlightthickness=0)
        self.s3_cv.pack()

        lf = ttk.LabelFrame(f_chem, text=T("인슐린 주사기 0.5 ml (눈금 0.01 ml)", "Insulin syringe 0.5 ml (0.01 ml marks)"), padding=4)
        lf.pack(fill="x", pady=2)
        fr = ttk.Frame(lf)
        fr.pack(fill="x")
        self.insk = tk.IntVar(value=0)
        for k in range(4):
            ttk.Radiobutton(fr, text="#%d" % (k + 1), value=k, variable=self.insk).pack(side="left")
        ttk.Button(fr, text=T("IC 채우기", "fill IC"), command=lambda: self.fill_ins("ic")).pack(side="left")
        ttk.Button(fr, text=T("In 채우기", "fill In"), command=lambda: self.fill_ins("ind")).pack(side="left")
        fr = ttk.Frame(lf)
        fr.pack(fill="x")
        ttk.Button(fr, text=T("한 방울→큐벳", "drop→cuvette"), command=lambda: self.drop(True)).pack(side="left")
        ttk.Button(fr, text=T("한 방울→폐액", "drop→waste"), command=lambda: self.drop(False)).pack(side="left")
        ttk.Button(fr, text="0.01 ml→", command=lambda: self.push(0.01)).pack(side="left")
        ttk.Button(fr, text="0.05 ml→", command=lambda: self.push(0.05)).pack(side="left")
        self.ins_cv = tk.Canvas(lf, width=430, height=44, bg="#e9e7e0", highlightthickness=0)
        self.ins_cv.pack()

        self.status = tk.Label(left, text="", fg="#b3261e", wraplength=450, justify="left")
        self.status.pack(fill="x", pady=4)

        # right: the Spectroscopy program
        bar = ttk.Frame(right)
        bar.pack(fill="x")
        ttk.Button(bar, text="Launch", command=self.launch).pack(side="left")
        ttk.Button(bar, text="Pause", command=self.pause).pack(side="left")
        ttk.Button(bar, text="Single spectrum", command=self.single).pack(side="left")
        ttk.Button(bar, text="Save spectrum", command=self.save_single).pack(side="left")
        self.ts_btn = ttk.Button(bar, text="Time Series", command=self.time_series)
        self.ts_btn.pack(side="left")
        ttk.Button(bar, text="Save time series", command=self.save_ts).pack(side="left")
        ttk.Label(bar, text="  Δt, s").pack(side="left")
        self.dt_v = tk.StringVar(value="2")
        ttk.OptionMenu(bar, self.dt_v, "2", "0.5", "1", "2", "5", "10").pack(side="left")
        ttk.Label(bar, text="  Sensitivity").pack(side="left")
        self.sens_v = tk.IntVar(value=4)
        tk.Spinbox(bar, from_=1, to=8, width=3, textvariable=self.sens_v,
                   command=lambda: setattr(self.B, "sens", self.sens_v.get())).pack(side="left")
        self.cv = tk.Canvas(right, bg="white", highlightthickness=0)
        self.cv.pack(fill="both", expand=True, pady=4)
        self.cv.bind("<Motion>", lambda e: setattr(self, "mouse", (e.x, e.y)))
        self.cv.bind("<MouseWheel>", self.wheel)
        self.cv.bind("<Button-4>", lambda e: self.wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self.wheel(e, -1))
        self.cv.bind("<Double-Button-1>", lambda e: setattr(self, "view", [0, NPIX]))
        bot = ttk.Frame(right)
        bot.pack(fill="x")
        ttk.Label(bot, text=T("시간 배속", "Time speed")).pack(side="left")
        for s in (1, 5, 20, 60):
            ttk.Button(bot, text="×%d" % s, width=4, command=lambda s=s: setattr(self, "speed", s)).pack(side="left")
        self.sw_l = tk.Label(bot, text="0:00.0", font=("Consolas", 16, "bold"))
        self.sw_l.pack(side="left", padx=12)
        ttk.Button(bot, text=T("스톱워치 시작/정지", "Stopwatch start/stop"), command=lambda: setattr(self, "sw_run", not self.sw_run)).pack(side="left")
        ttk.Button(bot, text=T("리셋", "Reset"), command=self.sw_reset).pack(side="left")

    # ---------------- controls ----------------
    def say(self, s):
        self.status.config(text=s)

    def on_pos(self, k):
        old = self.B.x[k]
        self.B.x[k] = round(self.sx[k].get(), 1)
        if k in ("holder", "cuvhold") and abs(old - self.B.x[k]) > 0.05:
            self.B.nudge(0.3)

    def nudge_pos(self, k, d):
        self.sx[k].set(min(TABLE_L - 1, max(1, round(self.sx[k].get() + d, 1))))
        self.on_pos(k)

    def on_src(self):
        self.B.src = self.src_v.get() or None
        self.B.plugged = False
        self.B.nudge(0.05)
        self.say(T("광원을 바꿨습니다 — 커넥터를 꽂으세요.", "Source changed — plug the connector in."))

    def toggle_plug(self):
        if not self.B.src:
            return
        self.B.plugged = not self.B.plugged
        self.B.nudge(1.2)
        self.say(T("받침대에 꽂힌 LED에 선을 꽂거나 빼서 받침대가 움직였습니다 — 보정이 달라졌을 수 있습니다.",
                   "Plugging the LED in the holder moved the holder — the calibration may have changed."))

    def toggle_psu(self):
        self.B.psu_on = not self.B.psu_on

    def knob(self, d):
        self.B.psu_v = min(PSU_MAX, max(0.0, round(self.B.psu_v + d, 1)))

    def toggle_ad(self):
        self.B.ad_sw = not self.B.ad_sw

    def cur_cuv(self):
        return self.B.cuv[self.cuv_i.get()]

    def cap(self):
        c = self.cur_cuv()
        c.cap = not c.cap

    def shake(self):
        c = self.cur_cuv()
        if not c.cap:
            self.say(T("흔들기 전에 뚜껑을 닫으세요.", "Cap the cuvette before shaking it."))
            return
        c.mixed = True
        c.bubbles = U(0.5, 1.3) if c.vol() > 0.1 else 0.0
        if c.tr:
            # oxygen from the air above the liquid; the capped cuvette's air holds less each time,
            # so a restart turns purple sooner
            c.tr["k"] = c.tr.get("k", 0) + 1
            c.tr["O"] = max(c.tr["O"], 0.7 ** (c.tr["k"] - 1))
        self.say(T("흔들어 섞었습니다 (벽에 거품이 생겼을 수 있습니다).", "Shaken and mixed (there may be bubbles on the walls)."))

    def tap(self):
        self.cur_cuv().bubbles = 0.0

    def rot(self):
        c = self.cur_cuv()
        c.rot = not c.rot

    def empty(self):
        i = self.cuv_i.get()
        lab = self.B.cuv[i].label
        self.B.cuv[i] = Cuvette(i)
        self.B.cuv[i].label = lab

    def label(self):
        self.cur_cuv().label = self.label_v.get()[:12]

    def holder(self):
        i = self.cuv_i.get()
        self.B.in_holder = None if self.B.in_holder == i else i

    def dissolve(self):
        if not self.gloves:
            self.say(T("장갑부터 끼세요 — NaOH는 매우 부식성이 강합니다.", "Put the gloves on first — NaOH is extremely caustic."))
            return
        try:
            V = float(self.stock_v.get())
        except ValueError:
            return
        Vt = V * (1 + random.gauss(0, 0.004))
        self.B.naoh = [V, TR.mNaOH / MU["NaOH"] / (Vt * 1e-3)]
        self.say(T("NaOH 용액 %.1f ml를 만들었습니다.", "%.1f ml of NaOH solution made.") % V)

    def draw3(self, d):
        r = self.r3_v.get()
        s = self.syr3
        if s[1] > 0 and s[0] != r:
            self.say(T("주사기에 다른 시약이 들어 있습니다 — 먼저 비우세요.", "The syringe holds another reagent — empty it first."))
            return
        if r == "naoh":
            if not self.gloves:
                self.say(T("장갑부터 끼세요.", "Gloves first."))
                return
            if not self.B.naoh:
                self.say(T("NaOH 원액부터 만드세요.", "Make the NaOH stock first."))
                return
        s[0] = r
        if d > 0:
            v = min(3 - s[1], d + random.gauss(0, 0.006))
            if r == "naoh":
                v = min(v, self.B.naoh[0])
                self.B.naoh[0] -= v
            s[1] += v
        else:
            v = min(s[1], -d + random.gauss(0, 0.006))
            s[1] = max(0.0, s[1] - v)
            if r == "naoh":
                self.B.naoh[0] += v

    def inj3(self):
        s = self.syr3
        if s[1] <= 0:
            return
        if s[0] == "naoh" and not self.gloves:
            self.say(T("장갑부터 끼세요.", "Gloves first."))
            return
        msg = self.B.add(self.cur_cuv(), s[0], s[1])
        if not self.cur_cuv().cap:
            s[1] = 0.0
        self.say(msg)

    def fill_ins(self, r):
        s = self.ins[self.insk.get()]
        s[0], s[1] = r, 0.5

    def drop(self, to_cuv):
        k = self.insk.get()
        s = self.ins[k]
        if s[1] <= 0:
            self.say(T("인슐린 주사기가 비었습니다.", "The insulin syringe is empty."))
            return
        v = min(s[1], TR.Vd[k] * (1 + random.gauss(0, 0.03)))
        if to_cuv:
            c = self.cur_cuv()
            if c.cap:
                self.say(T("뚜껑을 열어야 넣을 수 있습니다.", "Take the cap off to add anything."))
                return
            self.say(self.B.add(c, s[0], v))
        else:
            self.say(T("한 방울 떨어졌습니다.", "One drop fell."))
        s[1] = max(0.0, s[1] - v)

    def push(self, dv):
        s = self.ins[self.insk.get()]
        v = min(s[1], dv)
        c = self.cur_cuv()
        if v <= 0 or c.cap:
            return
        self.say(self.B.add(c, s[0], v * (1 + random.gauss(0, 0.01))))
        s[1] = max(0.0, s[1] - v)

    # ---------------- the program ----------------
    def launch(self):
        self.live = True

    def pause(self):
        self.live = False
        if self.ts is not None:
            self.ts_done, self.ts = self.ts, None

    def single(self):
        self.hold = self.B.frame()

    def save_single(self):
        data = self.cur if self.live else self.hold
        if not data:
            self.say(T("먼저 Single spectrum으로 한 장을 찍으세요.", "Take a Single spectrum first."))
            return
        fn = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="spectrum.csv")
        if fn:
            with open(fn, "w", encoding="utf-8") as f:
                f.write("N,I\n")
                for n, v in enumerate(data):
                    f.write("%d,%d\n" % (n, round(v)))

    def time_series(self):
        if self.ts is not None:
            self.ts_done, self.ts = self.ts, None
            return
        if not self.live:
            self.say(T("Time Series는 Launch를 누른 다음에만 켤 수 있습니다.", "Time Series can only be started after Launch."))
            return
        self.ts_dt = float(self.dt_v.get())
        self.ts = []
        self.ts_t0 = self.B.t
        self.ts_next = self.B.t

    def save_ts(self):
        ts = self.ts if self.ts is not None else self.ts_done
        if not ts:
            self.say(T("저장할 Time Series 기록이 없습니다.", "No time series recorded yet."))
            return
        fn = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="time_series.csv")
        if fn:
            with open(fn, "w", encoding="utf-8") as f:
                f.write("t_s," + ",".join("N%d" % n for n in range(NPIX)) + "\n")
                for t, fr in ts:
                    f.write("%.2f," % t + ",".join(str(int(round(v))) for v in fr) + "\n")

    def wheel(self, e, sign=None):
        s = sign if sign is not None else (1 if e.delta > 0 else -1)
        W = self.cv.winfo_width()
        x0, x1 = 60, W - 20
        f = min(1, max(0, (e.x - x0) / max(1, x1 - x0)))
        n0, n1 = self.view
        c = n0 + f * (n1 - n0)
        span = max(20, min(NPIX, (n1 - n0) * (0.8 if s > 0 else 1.25)))
        n0 = max(0, c - f * span)
        n1 = n0 + span
        if n1 > NPIX:
            n1 = NPIX
            n0 = n1 - span
        self.view = [n0, n1]

    def sw_reset(self):
        self.sw_run, self.sw_t = False, 0.0

    # ---------------- drawing ----------------
    def draw_plot(self):
        cv = self.cv
        cv.delete("all")
        W, H = cv.winfo_width(), cv.winfo_height()
        x0, y0, x1, y1 = 60, 20, W - 20, H - 40
        data = self.cur if self.live else self.hold
        n0, n1 = self.view
        mx = 64
        if data:
            mx = max(mx, max(data[int(n0):int(n1)]))
        ym = 1
        p = 10 ** math.floor(math.log10(mx * 1.12))
        for m in (1, 2, 2.5, 5, 10):
            if m * p >= mx * 1.12:
                ym = m * p
                break
        ym = min(ym, 4500)
        cv.create_rectangle(x0, y0, x1, y1, outline="#9aa3ab")
        st = next((s for s in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000) if (n1 - n0) / s <= 10), 1000)
        n = math.ceil(n0 / st) * st
        while n <= n1:
            x = x0 + (n - n0) / (n1 - n0) * (x1 - x0)
            cv.create_line(x, y0, x, y1, fill="#e3e6ea")
            cv.create_text(x, y1 + 12, text=str(int(n)), font=("Arial", 9))
            n += st
        for i in range(6):
            v = ym * i / 5
            y = y1 - v / ym * (y1 - y0)
            cv.create_line(x0, y, x1, y, fill="#e3e6ea")
            cv.create_text(x0 - 6, y, text=str(int(v)), anchor="e", font=("Arial", 9))
        cv.create_text((x0 + x1) / 2, y1 + 28, text="N", font=("Arial", 10, "bold"))
        cv.create_text(20, (y0 + y1) / 2, text="I, a.u.", angle=90, font=("Arial", 10, "bold"))
        if data:
            pts = []
            a, b = int(n0), min(NPIX - 1, int(math.ceil(n1)))
            stp = max(1, (b - a) // (x1 - x0))
            for n in range(a, b + 1, stp):
                v = max(data[n:n + stp]) if stp > 1 else data[n]
                pts += [x0 + (n - n0) / (n1 - n0) * (x1 - x0), y1 - min(v, ym) / ym * (y1 - y0)]
            if len(pts) >= 4:
                cv.create_line(*pts, fill="#1f5fbf")
            if max(data) >= OVERFLOW:
                cv.create_rectangle(x1 - 100, y0 + 24, x1 - 6, y0 + 44, fill="#c0392b", outline="")
                cv.create_text(x1 - 53, y0 + 34, text="Overflow", fill="white", font=("Arial", 10, "bold"))
            if self.mouse and x0 <= self.mouse[0] <= x1:
                n = int(round(n0 + (self.mouse[0] - x0) / (x1 - x0) * (n1 - n0)))
                if 0 <= n < NPIX:
                    xx = x0 + (n - n0) / (n1 - n0) * (x1 - x0)
                    cv.create_line(xx, y0, xx, y1, fill="#e09090")
                    cv.create_text(x0 + 8, y0 + 12, anchor="w", fill="#b3261e", font=("Arial", 10, "bold"),
                                   text="N = %d   I = %d" % (n, round(data[n])))
        mode = (T("기록 중 %d 장", "recording %d frames") % len(self.ts)) if self.ts is not None else \
            (T("실시간", "live") if self.live else (T("한 장", "single") if self.hold else ""))
        cv.create_text(x1 - 6, y0 + 12, anchor="e", text=mode, font=("Arial", 10, "bold"))

    def ccd_plate(self, c, cx, y0, y1):
        """the CCD as on the sheet: a black square plate, four screws, the long chip down its middle"""
        s = (y1 - y0) / 2
        c.create_rectangle(cx - s, y0, cx + s, y1, fill="#141416", outline="#000")
        c.create_polygon(cx - 0.55 * s, y1, cx - 0.55 * s, y1 - 0.6 * s, cx, y1 - 0.95 * s, cx + 0.55 * s, y1 - 0.6 * s, cx + 0.55 * s, y1, fill="#1d1e21", outline="")
        c.create_rectangle(cx - 0.2 * s, y0 + 0.08 * s, cx + 0.2 * s, y1 - 0.08 * s, fill="#2b2c30", outline="#b89a5a")
        c.create_rectangle(cx - 0.1 * s, y0 + 0.18 * s, cx + 0.1 * s, y1 - 0.18 * s, fill="#7a7f88", outline="")
        for dx in (-0.78, 0.78):
            for dy in (0.22, 1.78):
                x, y = cx + dx * s, y0 + dy * s
                c.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#c3c8cd", outline="#7b8087")
        for i, col in enumerate(("#e8463c", "#f39a2e", "#f1d93a", "#43b649", "#2f8fd6", "#a347b8")):
            x = cx - 0.3 * s + i * 0.12 * s
            c.create_line(x, y1, x, y1 + 0.35 * s, fill=col, width=2)

    def draw_screen(self):
        c = self.screen_cv
        c.delete("all")
        c.create_text(8, 10, anchor="w", text=T("스크린 면", "screen face"), font=("Arial", 9, "bold"))
        cx, zy, sz = 110, 196, 12
        top, h = zy - 7.2 * sz, 4.6 * sz
        self.ccd_plate(c, cx, top - 0.4 * sz, top + h + 0.4 * sz)
        o = self.B.optics()
        if not o or self.B.brightness() <= 0.01:
            return
        bl = min(30, 2 + o[3] * 3)
        c.create_oval(cx - bl, zy - bl, cx + bl, zy + bl, fill="#fff6e0", outline="")
        k0, l0 = self.B.scale()
        S = []
        for i in range(-60, 201, 3):
            n = i / 140 * NPIX
            l = l0 + k0 * n
            S.append((n, l, self.B.emission(l) * self.B.trans(l) if 380 < l < 780 else 0.0))
        mx = max(v for _, _, v in S) or 1
        for n, l, v in S:
            a = math.sqrt(min(1, v / mx))
            y = top + n / NPIX * h
            if a < 0.05 or y < 20 or y > zy - bl:
                continue
            r, g, b = wl_rgb(l)
            col = "#%02x%02x%02x" % (int(230 + (r - 230) * a), int(232 + (g - 232) * a), int(234 + (b - 234) * a))
            c.create_rectangle(cx - bl * 0.4 - 6, y, cx + bl * 0.4 + 6, y + 3.2, fill=col, outline="")

    def draw_chem(self):
        c = self.cuv_cv
        c.delete("all")
        for i, cu in enumerate(self.B.cuv):
            x = 12 + i * 43
            V = cu.vol()
            lv = min(1, V / CUV_MAX) * 70
            if lv > 0.5:
                c.create_rectangle(x + 2, 92 - lv, x + 28, 92, fill=cu.colour(), outline="")
            c.create_rectangle(x, 20, x + 30, 94, outline="#2f6fd0" if i == self.cuv_i.get() else "#7a95a8", width=2 if i == self.cuv_i.get() else 1)
            if cu.cap:
                c.create_rectangle(x - 2, 12, x + 32, 20, fill="#e8e8e4", outline="#999")
            if cu.bubbles > 0.05:
                for k in range(4):
                    c.create_oval(x + 6 + k * 5, 70 - k * 8, x + 9 + k * 5, 73 - k * 8, outline="#fff")
            tag = str(i + 1) + ("*" if self.B.in_holder == i else "")
            c.create_text(x + 15, 104, text=tag, font=("Arial", 9, "bold"))
            if cu.label:
                c.create_text(x + 15, 32, text=cu.label[:5], font=("Arial", 7))
            if not cu.mixed and V > 0:
                c.create_text(x + 15, 6, text="~", fill="#a33", font=("Arial", 10, "bold"))
        for cvs, (r, V), Vmax, step in ((self.s3_cv, self.syr3, 3.0, 0.1), (self.ins_cv, self.ins[self.insk.get()], 0.5, 0.01)):
            cvs.delete("all")
            x0, x1 = 30, 400
            if V > 0:
                col = "#3c4fbe" if r == "ic" else "#e6eef4"
                cvs.create_rectangle(x0, 8, x0 + (x1 - x0) * V / Vmax, 24, fill=col, outline="")
            cvs.create_rectangle(x0, 6, x1 + 8, 26, outline="#7d8790")
            cvs.create_line(4, 16, x0, 16, fill="#999")
            xv = x0 + (x1 - x0) * V / Vmax
            cvs.create_rectangle(xv, 7, xv + 4, 25, fill="#2a2c30", outline="")
            nt = int(round(Vmax / step))
            for i in range(nt + 1):
                x = x0 + (x1 - x0) * i / nt
                L = 10 if i % 10 == 0 else 7 if i % 5 == 0 else 4
                cvs.create_line(x, 26, x, 26 - L, fill="#222")
                if i % 10 == 0 or (Vmax == 3.0 and i % 5 == 0):
                    cvs.create_text(x, 35, text=("%g" % (i * step)), font=("Arial", 8))

    # ---------------- the loop ----------------
    def tick(self):
        now = time.time()
        dt = min(0.1, now - self.last)
        self.last = now
        rem = dt * self.speed
        while rem > 1e-9:
            h = min(0.25, rem)
            self.B.step(h)
            rem -= h
            if self.sw_run:
                self.sw_t += h
            if self.live and self.ts is not None and self.B.t >= self.ts_next:
                self.ts.append((self.B.t - self.ts_t0, self.B.frame()))
                self.ts_next = self.B.t + self.ts_dt
        self.acc += dt
        if self.acc > 0.3:
            self.acc = 0.0
            if self.live:
                self.cur = self.B.frame()
            self.knob_l.config(text=("%.1f V" % self.B.psu_v) if self.B.psu_on else "—")
            self.psu_btn.config(text=T("전원 끄기", "Supply off") if self.B.psu_on else T("전원 켜기", "Supply on"))
            self.ad_btn.config(text=T("어댑터 스위치: ", "Adapter switch: ") + ("ON" if self.B.ad_sw else "OFF"))
            self.plug_btn.config(text=(T("커넥터 빼기", "Unplug the connector") if self.B.plugged else T("커넥터 꽂기", "Plug the connector in")))
            self.ts_btn.config(text="Time Series ●" if self.ts is not None else "Time Series")
            st = self.sw_t
            self.sw_l.config(text="%d:%04.1f" % (int(st // 60), st % 60))
            self.draw_plot()
            self.draw_screen()
            self.draw_chem()
        self.root.after(40, self.tick)


def wl_rgb(l):
    r = g = b = 0.0
    if l < 440:
        r, b = (440 - l) / 60, 1
    elif l < 490:
        g, b = (l - 440) / 50, 1
    elif l < 510:
        g, b = 1, (510 - l) / 20
    elif l < 580:
        r, g = (l - 510) / 70, 1
    elif l < 645:
        r, g = 1, (645 - l) / 65
    else:
        r = 1
    return tuple(int(255 * max(0, min(1, v))) for v in (r, g, b))


def main():
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
    root = tk.Tk()
    App(root, seed)
    root.mainloop()


if __name__ == "__main__":
    main()
