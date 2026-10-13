#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  47th International Physics Olympiad  (IPhO 2016, Zurich, Switzerland)
  Experimental Problem E2 :  JUMPING BEADS
  (a model for phase transitions and instabilities)
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Apparatus rebuilt from the photographs of the problem sheet: loudspeaker
    with a two-compartment cylinder, poppy seeds, glove cover, signal
    generator (saw-tooth, speaker output, amplitude monitor), multimeter,
    pencil and millimetre paper for the calibration.
    Only what the apparatus shows is displayed -- the seeds themselves, the
    pencil trace on the millimetre paper and the multimeter.  Nothing is
    counted, fitted or computed for the student.
    All hidden true parameters are randomised for every session.

    Run:   python3 ipho2016_E2_sim_KO.py   [--seed=N]
"""

import math, random, sys

# --------------------------------------------------------------------------
# language
# --------------------------------------------------------------------------
LANG = "ko"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


# ===========================================================================
#  hidden ground truth
# ===========================================================================
CYL_R = 15.0                 # inner radius of the plastic cylinder [mm]
WALL_H = 4.0                 # height of the dividing wall [mm]
F_DRIVE = 50.0               # saw-tooth frequency [Hz]


class Session(object):
    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1, 10 ** 9)
        self.seed = seed
        rng = random.Random(seed)
        self.rng = rng
        # ---- speaker calibration  A(A_D) : stroke per period, in mm
        self.k0 = 0.40 * rng.uniform(0.75, 1.30)          # mm
        self.k1 = 3.12 * rng.uniform(0.96, 1.04)          # mm / V
        self.A_knee = 4.60 * rng.uniform(0.97, 1.03)
        self.A_max = 5.30 * rng.uniform(0.97, 1.03)
        # ---- critical stroke of the poppy seeds
        self.A_c = 4.30 * rng.uniform(0.96, 1.04)
        if self.A_c > self.A_knee - 0.15:                 # keep it in the linear part
            self.A_c = self.A_knee - 0.15
        self.K = 1.70 * rng.uniform(0.97, 1.03)
        self.beta = 0.66 * rng.uniform(0.96, 1.04)
        self.kappa = 1.45 * rng.uniform(0.9, 1.1)         # counting scatter
        self.minority = rng.choice((0, 1))                # 0 = left half
        self.n_stuck = rng.randint(0, 2)                  # electrostatically stuck
        self.pot_max = 2.40 * rng.uniform(0.97, 1.03)     # full-scale A_D
        self.paper_zero = rng.uniform(-0.35, 0.35)        # mm-paper alignment

    # ------------------------------------------------------------------ ---
    def amplitude(self, AD):
        """Maximum travel of the membrane during one period [mm]."""
        lin = self.k0 + self.k1 * AD
        if lin <= self.A_knee:
            return max(0.0, lin)
        d = self.A_max - self.A_knee
        return self.A_knee + d * (1.0 - math.exp(-(lin - self.A_knee) / d))

    def order_parameter(self, A):
        """m = (N2 - N1) / (N1 + N2)  in the steady state."""
        if A >= self.A_c:
            return 0.0
        t = (self.A_c ** 2 - A ** 2) / self.A_c ** 2
        return min(1.0, self.K * t ** self.beta)

    def AD_crit(self):
        return (self.A_c - self.k0) / self.k1


# ===========================================================================
#  signal generator / multimeter
# ===========================================================================
DMM_V_RANGES = [("200 mV", 0.1999, 1e-4), ("2 V", 1.999, 1e-3),
                ("20 V", 19.99, 1e-2), ("200 V", 199.9, 1e-1)]


class DMM(object):
    def __init__(self, name="M1"):
        self.name = name
        self.mode = "V"
        self.vr = 1
        self.raw = 0.0
        self.connected = False

    def range_label(self):
        return DMM_V_RANGES[self.vr][0]

    def display(self, rng):
        if self.mode == "OFF" or not self.connected:
            return "     "
        lab, full, step = DMM_V_RANGES[self.vr]
        unit = "mV" if self.vr == 0 else "V"
        scale = 1000.0 if self.vr == 0 else 1.0
        v = self.raw * (1.0 + rng.gauss(0.0, 0.0010)) + rng.gauss(0.0, 0.4) * step
        if abs(v) > full * 1.0001:
            return " O L "
        q = round(v / step) * step
        digits = max(0, int(round(-math.log10(step * scale))))
        return ("%%.%df" % digits) % (q * scale) + " " + unit


class SignalGen(object):
    def __init__(self):
        self.powered = False
        self.turns_v = 0.0
        self.turns_a = 0.0
        self.spk_on = False

    def monitor(self, ses):
        if not (self.powered and self.spk_on):
            return 0.0
        return max(0.0, min(ses.pot_max, ses.pot_max * self.turns_a / 12.0))


# ===========================================================================
#  the bench
# ===========================================================================
TERMINALS = ["SG.SPK+", "SG.SPK-", "SG.MON", "SG.GND",
             "SPK.a", "SPK.b", "M1.IN", "M1.COM"]


class Bench(object):
    def __init__(self, ses):
        self.ses = ses
        self.rng = random.Random(ses.seed ^ 0xbead)
        self.sg = SignalGen()
        self.m1 = DMM()
        self.wires = []
        self.have = set()
        # cylinder state
        self.n_seeds = 0                # seeds counted into the cylinder
        self.covered = False            # glove piece taped on top
        self.seeds = []                 # (side, x, y, stuck)
        self.m_eff = 1.0
        self.settle = 0.0               # seconds since the last change
        self.hop_t = 0.0
        self.n_resample = 0             # increases every time the gas reshuffles
        # calibration rig
        self.pencil = False
        self.mmpaper = False
        self.view = "top"               # "top" | "side"
        self.tally = [0, 0]

    # -------------------------------------------------------------- wiring
    def add_wire(self, a, b):
        if a == b:
            return False
        for p, q in self.wires:
            if {p, q} == {a, b}:
                return False
        self.wires.append((a, b))
        return True

    def del_wire(self, i):
        if 0 <= i < len(self.wires):
            self.wires.pop(i)

    def _groups(self):
        par = {t: t for t in TERMINALS}

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x
        for a, b in self.wires:
            ra, rb = find(a), find(b)
            if ra != rb:
                par[ra] = rb
        return {t: find(t) for t in TERMINALS}

    def speaker_driven(self):
        g = self._groups()
        pos = (g["SPK.a"] == g["SG.SPK+"] and g["SPK.b"] == g["SG.SPK-"])
        neg = (g["SPK.a"] == g["SG.SPK-"] and g["SPK.b"] == g["SG.SPK+"])
        if not (pos or neg):
            return 0
        if g["SG.SPK+"] == g["SG.SPK-"]:      # short circuit
            return 0
        return 1 if pos else -1

    def meter_reads_monitor(self):
        g = self._groups()
        return (g["M1.IN"] == g["SG.MON"] and g["M1.COM"] == g["SG.GND"]) or \
               (g["M1.COM"] == g["SG.MON"] and g["M1.IN"] == g["SG.GND"])

    # ----------------------------------------------------------- physics --
    def A_D(self):
        return self.sg.monitor(self.ses)

    def stroke(self):
        """Real membrane stroke [mm]; zero if the speaker is not driven."""
        if self.speaker_driven() == 0:
            return 0.0
        return self.ses.amplitude(self.A_D())

    def load_seeds(self, n):
        self.n_seeds = max(0, min(140, int(n)))
        self.seeds = []
        ns = min(self.ses.n_stuck, self.n_seeds)
        for i in range(ns):
            self.seeds.append([self.rng.choice((0, 1)), 0.0, 0.0, True])
        self.m_eff = 1.0
        self.settle = 0.0
        self.resample(force=True)

    def n_mobile(self):
        return self.n_seeds - min(self.ses.n_stuck, self.n_seeds)

    def resample(self, force=False):
        """Draw a new instantaneous configuration of the mobile seeds."""
        self.n_resample += 1
        N = self.n_mobile()
        if N <= 0:
            self.seeds = [s for s in self.seeds if s[3]]
            return
        m = self.m_eff
        p = 0.5 * (1.0 - m)
        mean = N * p
        sd = self.ses.kappa * math.sqrt(max(1e-9, N * p * (1 - p))) + 0.6
        n_min = int(round(self.rng.gauss(mean, sd)))
        n_min = max(0, min(N, n_min))
        stuck = [s for s in self.seeds if s[3]]
        self.seeds = list(stuck)
        mi = self.ses.minority
        for k in range(N):
            side = mi if k < n_min else 1 - mi
            self.seeds.append([side, 0.0, 0.0, False])
        self.scatter()

    def scatter(self):
        r = CYL_R - 1.4
        for s in self.seeds:
            if s[3]:
                continue
            while True:
                x = self.rng.uniform(-r, r)
                y = self.rng.uniform(-r, r)
                if x * x + y * y <= r * r and abs(x) > 1.2:
                    break
            if (x < 0) != (s[0] == 0):
                x = -x
            s[1], s[2] = x, y
        for s in self.seeds:
            if s[3] and s[1] == 0.0 and s[2] == 0.0:
                a = self.rng.uniform(0, 2 * math.pi)
                rr = self.rng.uniform(0.75, 0.95) * r
                s[1], s[2] = rr * math.cos(a), rr * math.sin(a)
                s[0] = 0 if s[1] < 0 else 1

    def step(self, dt):
        """Advance the granular gas.  tau ~ 2.5 s, reshuffle every 3.5 s."""
        A = self.stroke()
        if not self.covered or self.n_seeds == 0:
            return
        target = self.ses.order_parameter(A) if A > 0.05 else 1.0
        tau = 2.5
        self.m_eff += (target - self.m_eff) * (1.0 - math.exp(-dt / tau))
        self.settle += dt
        self.hop_t += dt
        if A > 0.05 and self.hop_t > 3.5:
            self.hop_t = 0.0
            self.resample()
        elif A > 0.05:
            self.jitter()

    def jitter(self):
        r = CYL_R - 1.4
        for s in self.seeds:
            if s[3]:
                continue
            s[1] += self.rng.gauss(0, 0.7)
            s[2] += self.rng.gauss(0, 0.7)
            if abs(s[1]) < 1.2:
                s[1] = 1.2 * (1 if s[0] else -1)
            if (s[1] < 0) != (s[0] == 0):
                s[1] = -s[1]
            d = math.hypot(s[1], s[2])
            if d > r:
                s[1] *= r / d
                s[2] *= r / d

    def trace_length(self):
        """Length of the pencil trace on the millimetre paper [mm].
           Zero unless the rig is set up."""
        if not (self.pencil and self.mmpaper):
            return None
        return self.stroke()

    def counts(self):
        """What a student sees when counting (stuck seeds excluded)."""
        a = sum(1 for s in self.seeds if not s[3] and s[0] == 0)
        b = sum(1 for s in self.seeds if not s[3] and s[0] == 1)
        return a, b

    def evaluate(self):
        self.m1.connected = (self.m1.mode != "OFF") and self.meter_reads_monitor()
        self.m1.raw = self.A_D() if self.m1.connected else 0.0


# ===========================================================================
#  GUI
# ===========================================================================
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

BG = "#f2f0ea"
PANEL = "#e6e2d8"
INK = "#20242b"
ACC = "#8fb339"

PARTS = [
    ("battery", "USB 케이블이 있는 배터리 팩", "Battery pack with USB cable", "power", []),
    ("siggen", "조절 가능한 신호 발생기", "Adjustable signal generator", "power", ["battery"]),
    ("speaker", "플라스틱 원통이 달린 스피커 조립체", "Speaker with plastic cylinder",
     "exp", []),
    ("seeds", "양귀비 씨앗 (플라스틱 용기)", "Poppy seeds (plastic pot)", "exp", ["speaker"]),
    ("dmm", "디지털 멀티미터", "Digital multimeter", "power", []),
    ("cables", "4 mm 플러그 / 악어클립 케이블", "4 mm plug / clip cables", "wire",
     ["siggen", "speaker", "dmm"]),
    ("glove", "장갑", "Glove", "tool", []),
    ("tape", "접착 테이프", "Adhesive tape", "tool", []),
    ("tools", "드라이버 · 가위 · 연필 · 자", "Driver, scissors, pencil, ruler", "tool", []),
    ("mmpaper", "밀리미터 종이", "Millimetre paper", "tool", []),
]

ZONES = {
    "power": (30, 30, 330, 210, "전원 · 계측", "Power / meter"),
    "exp":   (345, 30, 640, 210, "실험 장치", "Experiment"),
    "wire":  (30, 225, 330, 355, "배선", "Wiring"),
    "tool":  (345, 225, 640, 470, "도구 · 재료", "Tools / materials"),
}
PART_POS = {"battery": (16, 30), "siggen": (16, 100), "dmm": (200, 40),
            "speaker": (20, 40), "seeds": (170, 60),
            "cables": (30, 40),
            "glove": (16, 34), "tape": (150, 40), "tools": (16, 120),
            "mmpaper": (170, 140)}
REQUIRED = ["battery", "siggen", "speaker", "seeds", "dmm", "cables",
            "glove", "tape", "tools", "mmpaper"]


class AssemblyTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.placed = {}
        self.drag = None
        left = tk.Frame(self, bg=PANEL, width=300)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Label(left, text=T("부품 상자", "Parts box"), bg=PANEL, fg=INK,
                 font=("TkDefaultFont", 12, "bold")).pack(pady=(10, 4))
        tk.Label(left, text=T("부품을 작업대의 알맞은 구역으로 끌어다 놓아라.",
                              "Drag each part to the right area of the bench."),
                 bg=PANEL, fg="#555", wraplength=275, justify="left").pack(padx=12)
        self.bin = tk.Canvas(left, bg=PANEL, highlightthickness=0, width=290, height=570)
        self.bin.pack(padx=6, pady=8)
        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        self.cv = tk.Canvas(right, bg=BG, highlightthickness=0, width=680, height=520)
        self.cv.pack(padx=8, pady=8, anchor="nw")
        self.log = tk.Text(right, height=8, bg="#fbfaf6", fg=INK, wrap="word",
                           relief="flat", font=("TkFixedFont", 9))
        self.log.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.bin.bind("<ButtonPress-1>", self.on_press)
        self.bin.bind("<B1-Motion>", self.on_move)
        self.bin.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<ButtonPress-1>", self.on_bench_click)
        self.redraw_bin()
        self.redraw_bench()
        self.say(T("실험 E-II 장비를 조립하라.  스피커 조립체를 먼저 놓아야 씨앗을 꺼낼 수 있다.",
                   "Assemble the E-II apparatus.  The speaker must be placed before the seeds."))

    def say(self, s):
        self.log.insert("end", "  " + s + "\n")
        self.log.see("end")

    def redraw_bin(self):
        self.bin.delete("all")
        y = 12
        self.bin_items = []
        for pid, ko, en, zone, req in PARTS:
            if pid in self.placed:
                continue
            self.bin.create_rectangle(10, y, 278, y + 46, fill="#fffdf7",
                                      outline="#b9b3a2")
            self.bin.create_text(20, y + 23, anchor="w", text=T(ko, en), fill=INK,
                                 font=("TkDefaultFont", 9))
            self.bin_items.append((pid, y))
            y += 52

    def zone_at(self, x, y):
        for z, (x0, y0, x1, y1, ko, en) in ZONES.items():
            if x0 <= x <= x1 and y0 <= y <= y1:
                return z
        return None

    def redraw_bench(self):
        c = self.cv
        c.delete("all")
        c.create_rectangle(8, 8, 672, 512, fill="#ece7db", outline="#c9c2af", width=2)
        for z, (x0, y0, x1, y1, ko, en) in ZONES.items():
            c.create_rectangle(x0, y0, x1, y1, fill="#f6f4ec", outline="#c1baa6",
                               dash=(4, 3))
            c.create_text(x0 + 8, y0 + 12, anchor="w", text=T(ko, en), fill="#8a8371",
                          font=("TkDefaultFont", 9, "bold"))
        for pid, (x, y) in self.placed.items():
            self.draw_part(pid, x, y)
        ok = all(p in self.placed for p in REQUIRED)
        c.create_rectangle(450, 478, 665, 506, fill=ACC if ok else "#cfc9b8", outline="")
        c.create_text(557, 492, text=T("조립 완료 — 실험대로", "Assembled - go to bench")
                      if ok else T("부품이 더 필요하다", "More parts required"),
                      fill="white" if ok else "#7a7462",
                      font=("TkDefaultFont", 9, "bold"), tags="donebtn")
        self.assembled = ok
        if ok:
            self.app.enable_bench()

    def draw_part(self, pid, x, y):
        c = self.cv
        if pid == "battery":
            c.create_rectangle(x, y, x + 92, y + 34, fill="#f7f7f7", outline="#999")
            c.create_rectangle(x + 6, y + 6, x + 30, y + 28, fill="#5f7fb8",
                               outline="#3d5a8a")
            c.create_text(x + 62, y + 17, text="POWER", font=("TkFixedFont", 7),
                          fill="#333")
        elif pid == "siggen":
            c.create_rectangle(x, y, x + 118, y + 62, fill="#cfe0c2", outline="#7f9a6c",
                               width=2)
            c.create_rectangle(x + 30, y + 2, x + 88, y + 16, fill="#222", outline="#111")
            for i in range(2):
                c.create_oval(x + 18 + i * 58, y + 22, x + 34 + i * 58, y + 38,
                              fill="#3c6fb0", outline="#20406b")
            for i, col in enumerate(("#c9a227", "#d8d8d8", "#222")):
                c.create_oval(x + 24 + i * 28, y + 44, x + 38 + i * 28, y + 58,
                              fill=col, outline="#555")
        elif pid == "dmm":
            c.create_rectangle(x, y, x + 60, y + 96, fill="#2f62a8", outline="#1d3f6e",
                               width=2)
            c.create_rectangle(x + 7, y + 8, x + 53, y + 30, fill="#cfe6c8",
                               outline="#5c7a52")
            c.create_oval(x + 16, y + 38, x + 44, y + 66, fill="#e8e8e8", outline="#888")
        elif pid == "speaker":
            c.create_rectangle(x, y, x + 112, y + 112, fill="#f2f2f2", outline="#bbb",
                               width=2)
            c.create_oval(x + 8, y + 8, x + 104, y + 104, fill="#232323", outline="#111")
            c.create_oval(x + 28, y + 28, x + 84, y + 84, fill="#3a3a3a", outline="#222")
            c.create_oval(x + 34, y + 22, x + 78, y + 46, fill="#d8e4ea", outline="#9ab")
            c.create_rectangle(x + 34, y + 34, x + 78, y + 74, fill="#e6eef2",
                               outline="#9ab")
            c.create_oval(x + 34, y + 62, x + 78, y + 86, fill="#cfe0e8", outline="#9ab")
            c.create_line(x + 112, y + 30, x + 140, y + 22, fill="#c33", width=3)
            c.create_line(x + 112, y + 40, x + 140, y + 48, fill="#222", width=3)
        elif pid == "seeds":
            c.create_oval(x, y, x + 54, y + 54, fill="#fdfdfd", outline="#bbb", width=2)
            c.create_oval(x + 6, y + 6, x + 48, y + 48, fill="#2b2521", outline="#191512")
            c.create_oval(x + 60, y + 2, x + 104, y + 46, fill="#2f5aa8", outline="#1d3a6e")
        elif pid == "cables":
            for i, col in enumerate(("#c33", "#333", "#2a7", "#25c")):
                c.create_line(x, y + 6 + i * 10, x + 40, y + 2 + i * 10,
                              x + 84, y + 10 + i * 10, fill=col, width=3, smooth=True)
        elif pid == "glove":
            c.create_polygon(x, y + 40, x + 6, y + 12, x + 16, y + 8, x + 22, y,
                             x + 30, y + 8, x + 40, y + 4, x + 46, y + 18,
                             x + 52, y + 30, x + 44, y + 56, x + 10, y + 56,
                             fill="#7fc4e6", outline="#4f95b8", smooth=True)
        elif pid == "tape":
            c.create_oval(x, y, x + 44, y + 44, fill="#9fd14f", outline="#6f9b2f",
                          width=3)
            c.create_oval(x + 14, y + 14, x + 30, y + 30, fill=BG, outline="#6f9b2f")
        elif pid == "tools":
            c.create_line(x, y + 12, x + 34, y + 12, fill="#c9a227", width=4)
            c.create_rectangle(x + 34, y + 7, x + 46, y + 17, fill="#3b7", outline="#295")
            c.create_line(x + 56, y, x + 84, y + 20, fill="#999", width=3)
            c.create_line(x + 56, y + 20, x + 84, y, fill="#999", width=3)
            c.create_polygon(x, y + 34, x + 60, y + 34, x + 66, y + 39, x + 60, y + 44,
                             x, y + 44, fill="#e8c15a", outline="#a8862f")
            c.create_rectangle(x + 90, y + 32, x + 180, y + 44, fill="#f6e7a8",
                               outline="#b5a35c")
            for i in range(10):
                c.create_line(x + 94 + i * 9, y + 44, x + 94 + i * 9, y + 38,
                              fill="#8a7c55")
        elif pid == "mmpaper":
            c.create_rectangle(x, y, x + 92, y + 68, fill="#fdfbf0", outline="#bbb")
            for i in range(1, 10):
                c.create_line(x + i * 9.2, y, x + i * 9.2, y + 68, fill="#cfd8e8")
            for i in range(1, 8):
                c.create_line(x, y + i * 8.5, x + 92, y + i * 8.5, fill="#cfd8e8")

    # -------------------------------------------------------------- dragging
    def on_press(self, ev):
        for pid, y in getattr(self, "bin_items", []):
            if y <= ev.y <= y + 46:
                self.drag = pid
                self.ghost = self.bin.create_text(ev.x, ev.y, text="●", fill=ACC)
                return

    def on_move(self, ev):
        if self.drag:
            self.bin.coords(self.ghost, ev.x, ev.y)

    def on_release(self, ev):
        if not self.drag:
            return
        pid = self.drag
        self.drag = None
        self.bin.delete(self.ghost)
        gx = self.bin.winfo_rootx() + ev.x - self.cv.winfo_rootx()
        gy = self.bin.winfo_rooty() + ev.y - self.cv.winfo_rooty()
        self.try_place(pid, gx, gy)

    def on_bench_click(self, ev):
        it = self.cv.find_withtag("current")
        if it and "donebtn" in self.cv.gettags(it[0]) and getattr(self, "assembled", False):
            self.app.nb.select(1)

    def try_place(self, pid, x, y):
        spec = [p for p in PARTS if p[0] == pid][0]
        _, ko, en, zone, req = spec
        z = self.zone_at(x, y)
        if z is None:
            self.say(T("작업대 밖이다. 부품을 상자로 되돌린다.",
                       "Outside the bench - the part goes back into the box."))
            return
        if z != zone:
            self.say(T("%s: 이 구역에 놓을 수 없다." % T(ko, en),
                       "%s cannot be placed in this area." % T(ko, en)))
            return
        for r in req:
            if r not in self.placed:
                nm = [T(p[1], p[2]) for p in PARTS if p[0] == r][0]
                self.say(T("%s 먼저 필요하다 → %s" % (nm, T(ko, en)),
                           "%s is required first -> %s" % (nm, T(ko, en))))
                return
        x0, y0, _, _, _, _ = ZONES[zone]
        dx, dy = PART_POS.get(pid, (16, 30))
        self.placed[pid] = (x0 + dx, y0 + dy)
        if pid == "siggen":
            self.app.bench.sg.powered = True
        self.app.bench.have.add(pid)
        self.say(T("놓음: %s" % T(ko, en), "Placed: %s" % T(ko, en)))
        self.redraw_bin()
        self.redraw_bench()


# ===========================================================================
WIRE_COLORS = ["#cc2b2b", "#1b1b1b", "#1f7a3f", "#2255cc", "#d8b800", "#8a3fb0"]


class BenchTab(ttk.Frame):
    SX, SY, SW, SH = 12, 26, 620, 566

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.b = app.bench
        self.term = {}
        self.sel_term = None
        self.cv = tk.Canvas(self, bg=BG, highlightthickness=0, width=1420, height=612)
        self.cv.pack(side="top", padx=6, pady=(6, 2))
        self.cv.bind("<Button-1>", self.on_click)
        self.build_controls()
        self.redraw()
        self.last = None
        self.tick()

    # ------------------------------------------------------------- controls
    def build_controls(self):
        f = tk.Frame(self, bg=BG)
        f.pack(side="top", fill="both", expand=True, padx=6)

        def box(title, col):
            g = tk.LabelFrame(f, text=title, bg=BG, fg=INK, padx=6, pady=4)
            g.grid(row=0, column=col, sticky="nsew", padx=4)
            return g

        g = box(T("원통", "Cylinder"), 0)
        r = tk.Frame(g, bg=BG); r.pack(anchor="w")
        tk.Button(r, text=T("씨앗 넣기", "pour seeds"), width=11,
                  command=self.pour).pack(side="left")
        tk.Button(r, text=T("비우기", "empty"), width=8,
                  command=self.empty).pack(side="left")
        self.v_cov = tk.IntVar(value=0)
        tk.Checkbutton(g, text=T("장갑 조각으로 덮기 (가위+테이프)",
                                 "cover with glove piece (scissors+tape)"),
                       variable=self.v_cov, bg=BG, command=self.cover).pack(anchor="w")
        self.v_view = tk.StringVar(value="top")
        r = tk.Frame(g, bg=BG); r.pack(anchor="w", pady=(4, 0))
        for val, ko, en in (("top", "원통 위에서", "cylinder, top"),
                            ("side", "보정 (옆에서)", "calibration, side")):
            tk.Radiobutton(r, text=T(ko, en), variable=self.v_view, value=val, bg=BG,
                           command=self.setview).pack(side="left")

        g = box(T("보정 장치", "Calibration rig"), 1)
        self.v_pen = tk.IntVar(value=0)
        tk.Checkbutton(g, text=T("연필을 원통에 테이프로 고정",
                                 "tape the pencil to the cylinder"),
                       variable=self.v_pen, bg=BG, command=self.rig).pack(anchor="w")
        self.v_pap = tk.IntVar(value=0)
        tk.Checkbutton(g, text=T("밀리미터 종이를 세워 둠",
                                 "stand the millimetre paper"),
                       variable=self.v_pap, bg=BG, command=self.rig).pack(anchor="w")
        tk.Label(g, text=T("연필 끝이 그리는 흔적의 길이가\n한 주기 동안의 최대 이동 거리이다.",
                           "The length of the trace drawn by the pencil tip\n"
                           "is the travel during one period."),
                 bg=BG, fg="#666", justify="left").pack(anchor="w", pady=(4, 0))

        g = box(T("신호 발생기", "Signal generator"), 2)
        tk.Label(g, text="speaker amplitude (4)", bg=BG).pack()
        r = tk.Frame(g, bg=BG); r.pack()
        for lab, d in (("◀◀", -0.4), ("◀", -0.04), ("▶", 0.04), ("▶▶", 0.4)):
            tk.Button(r, text=lab, width=3,
                      command=lambda d=d: self.turn(d)).pack(side="left")
        self.v_spk = tk.IntVar(value=0)
        tk.Checkbutton(g, text=T("토글 스위치 (8)", "toggle switch (8)"),
                       variable=self.v_spk, bg=BG, command=self.setspk).pack(pady=(6, 0))
        self.v_mm = tk.StringVar(value="V")
        r = tk.Frame(g, bg=BG); r.pack(pady=(4, 0))
        for val in ("OFF", "V"):
            tk.Radiobutton(r, text=val, variable=self.v_mm, value=val, bg=BG,
                           command=self.setmm).pack(side="left")
        self.lbr = tk.Listbox(g, height=4, width=10, exportselection=False)
        self.lbr.pack()
        for rg in DMM_V_RANGES:
            self.lbr.insert("end", rg[0])
        self.lbr.selection_set(1)
        self.lbr.bind("<<ListboxSelect>>", self.setrange)

        g = box(T("계수기 (손 탤리)", "Hand tally counters"), 3)
        self.lbl_t = []
        for i, (ko, en) in enumerate((("구획 A", "compartment A"),
                                      ("구획 B", "compartment B"))):
            r = tk.Frame(g, bg=BG); r.pack(anchor="w", pady=2)
            tk.Label(r, text=T(ko, en), bg=BG, width=9, anchor="w").pack(side="left")
            tk.Button(r, text="−", width=2,
                      command=lambda i=i: self.tally(i, -1)).pack(side="left")
            l = tk.Label(r, text="0", bg="#fffdf5", width=4, relief="sunken")
            l.pack(side="left", padx=3)
            self.lbl_t.append(l)
            tk.Button(r, text="+", width=2,
                      command=lambda i=i: self.tally(i, 1)).pack(side="left")
        tk.Button(g, text=T("계수기 초기화", "reset counters"),
                  command=self.tally_reset).pack(anchor="w", pady=(4, 0))

        g = box(T("배선", "Wiring"), 4)
        tk.Label(g, text=T("단자를 두 번 눌러 케이블을 연결한다.",
                           "Click two terminals to lay a cable."),
                 bg=BG, fg="#666", wraplength=200, justify="left").pack(anchor="w")
        self.lbw = tk.Listbox(g, height=6, width=24, exportselection=False)
        self.lbw.pack(pady=2)
        r = tk.Frame(g, bg=BG); r.pack(anchor="w")
        tk.Button(r, text=T("선택 제거", "remove"), command=self.delw).pack(side="left")
        tk.Button(r, text=T("전부 제거", "clear"), command=self.clrw).pack(side="left")
        self.msg = tk.Label(f, text="", bg=BG, fg="#8a3a1a", anchor="w")
        self.msg.grid(row=1, column=0, columnspan=5, sticky="we", pady=(4, 6))
        for c in range(5):
            f.grid_columnconfigure(c, weight=1)

    # -------------------------------------------------------------- actions
    def note(self, s):
        self.msg.config(text=s)

    def pour(self):
        if "seeds" not in self.b.have:
            self.note(T("씨앗 용기가 없다.", "The seed pot is not on the bench."))
            return
        n = simpledialog.askinteger(
            T("양귀비 씨앗", "Poppy seeds"),
            T("원통에 넣을 씨앗의 개수를 세어라 (최대 120개):",
              "Count the seeds you put into the cylinder (max 120):"),
            parent=self, minvalue=1, maxvalue=120, initialvalue=50)
        if n:
            self.b.load_seeds(n)
            self.note(T("씨앗 %d개를 넣었다." % n, "%d seeds poured in." % n))
            self.redraw()

    def empty(self):
        self.b.load_seeds(0)
        self.redraw()

    def cover(self):
        if self.v_cov.get() and not ({"glove", "tape", "tools"} <= self.b.have):
            self.note(T("장갑 · 테이프 · 가위가 모두 필요하다.",
                        "Glove, tape and scissors are all required."))
            self.v_cov.set(0)
            return
        self.b.covered = bool(self.v_cov.get())
        self.redraw()

    def setview(self):
        self.b.view = self.v_view.get()
        self.redraw()

    def rig(self):
        if self.v_pen.get() and "tape" not in self.b.have:
            self.v_pen.set(0)
            self.note(T("테이프가 필요하다.", "Adhesive tape is required."))
        if self.v_pap.get() and "mmpaper" not in self.b.have:
            self.v_pap.set(0)
            self.note(T("밀리미터 종이가 필요하다.", "Millimetre paper is required."))
        self.b.pencil = bool(self.v_pen.get())
        self.b.mmpaper = bool(self.v_pap.get())
        self.redraw()

    def turn(self, d):
        self.b.sg.turns_a = max(0.0, min(12.0, self.b.sg.turns_a + d))
        self.b.settle = 0.0
        self.redraw()

    def setspk(self):
        self.b.sg.spk_on = bool(self.v_spk.get())
        self.b.settle = 0.0
        self.redraw()

    def setmm(self):
        self.b.m1.mode = self.v_mm.get()
        self.redraw()

    def setrange(self, ev=None):
        s = self.lbr.curselection()
        if s:
            self.b.m1.vr = s[0]

    def tally(self, i, d):
        self.b.tally[i] = max(0, self.b.tally[i] + d)
        self.lbl_t[i].config(text=str(self.b.tally[i]))

    def tally_reset(self):
        self.b.tally = [0, 0]
        for l in self.lbl_t:
            l.config(text="0")

    def delw(self):
        s = self.lbw.curselection()
        if s:
            self.b.del_wire(s[0])
            self.refresh_w()
            self.redraw()

    def clrw(self):
        self.b.wires = []
        self.refresh_w()
        self.redraw()

    def refresh_w(self):
        self.lbw.delete(0, "end")
        for a, b in self.b.wires:
            self.lbw.insert("end", "%-8s — %s" % (a, b))

    # -------------------------------------------------------------- drawing
    def redraw(self):
        c = self.cv
        c.delete("all")
        self.term = {}
        c.create_rectangle(self.SX, self.SY, self.SX + self.SW, self.SY + self.SH,
                           fill="#ded8c8", outline="#b6ae98", width=2)
        if self.b.view == "top":
            self.draw_top()
        else:
            self.draw_side()
        self.draw_siggen(650, 30)
        self.draw_dmm(1050, 30)
        self.draw_speaker_panel(650, 300)
        self.draw_wires()

    # ----- cylinder from above
    def draw_top(self):
        c = self.cv
        cx, cy = self.SX + self.SW / 2, self.SY + self.SH / 2 - 10
        k = 9.0                                # px per mm
        R = CYL_R * k
        c.create_text(cx, self.SY + 16, text=T("스피커 위 플라스틱 원통 (위에서)",
                                               "plastic cylinder on the speaker, top view"),
                      fill="#6b6553", font=("TkDefaultFont", 10, "bold"))
        c.create_oval(cx - R - 16, cy - R - 16, cx + R + 16, cy + R + 16,
                      fill="#c9c2b0", outline="#a49b85", width=2)
        c.create_oval(cx - R - 8, cy - R - 8, cx + R + 8, cy + R + 8,
                      fill="#dfe7ea", outline="#9fb3bb", width=3)
        c.create_oval(cx - R, cy - R, cx + R, cy + R, fill="#f4f1e6", outline="#9fb3bb")
        # dividing wall
        c.create_rectangle(cx - 4, cy - R, cx + 4, cy + R, fill="#c8d3d8",
                           outline="#8fa4ad")
        c.create_text(cx - R / 2, cy - R - 14, text="A", fill="#5a6a72",
                      font=("TkDefaultFont", 12, "bold"))
        c.create_text(cx + R / 2, cy - R - 14, text="B", fill="#5a6a72",
                      font=("TkDefaultFont", 12, "bold"))
        if not self.b.covered and self.b.n_seeds:
            c.create_text(cx, cy + R + 40,
                          text=T("원통이 덮여 있지 않다 — 씨앗이 튀어나간다.",
                                 "The cylinder is open - the seeds would fly out."),
                          fill="#a33", font=("TkDefaultFont", 9))
        for s in self.b.seeds:
            x = cx + s[1] * k
            y = cy - s[2] * k
            if s[3]:
                c.create_oval(x - 2.6, y - 2.2, x + 2.6, y + 2.2, fill="#6a6058",
                              outline="")
            else:
                c.create_oval(x - 2.9, y - 2.5, x + 2.9, y + 2.5, fill="#2b2118",
                              outline="#120d08")
        if self.b.covered:
            c.create_oval(cx - R - 8, cy - R - 8, cx + R + 8, cy + R + 8,
                          outline="#7fc4e6", width=3)
            c.create_text(cx, cy + R + 24, text=T("장갑 조각으로 덮음",
                                                  "closed with a piece of glove"),
                          fill="#4f95b8", font=("TkDefaultFont", 8))
        drv = self.b.speaker_driven()
        if drv == -1:
            c.create_text(cx, self.SY + 36, text=T("주의: 스피커 극성이 반대이다.",
                                                   "note: the speaker polarity is reversed."),
                          fill="#a36", font=("TkDefaultFont", 9))

    # ----- calibration, side view
    def draw_side(self):
        c = self.cv
        b = self.b
        x0 = self.SX + 60
        base = self.SY + 430
        c.create_text(self.SX + self.SW / 2, self.SY + 16,
                      text=T("보정 장치 (옆에서)", "calibration rig, side view"),
                      fill="#6b6553", font=("TkDefaultFont", 10, "bold"))
        c.create_rectangle(self.SX + 10, base, self.SX + self.SW - 10, base + 18,
                           fill="#cdbf9c", outline="#a59468")
        # loudspeaker box
        c.create_rectangle(x0, base - 92, x0 + 150, base, fill="#f2f2f2", outline="#bbb",
                           width=2)
        c.create_arc(x0 + 20, base - 84, x0 + 130, base - 6, start=0, extent=180,
                     fill="#232323", outline="#111")
        # cylinder + membrane offset
        A = b.stroke()
        ph = 0.0
        if A > 0.05:
            ph = (self.tickcount % 6) / 6.0
        off = (ph - 0.5) * A * 6.0
        cyl_top = base - 150 + off
        c.create_rectangle(x0 + 56, cyl_top, x0 + 94, base - 74 + off,
                           fill="#e6eef2", outline="#9ab", width=2)
        c.create_text(x0 + 75, base - 160, text=T("원통", "cylinder"), fill="#6b6553",
                      font=("TkDefaultFont", 8))
        tip_rest = base - 150 + 23          # mean height of the pencil tip
        if b.pencil:
            c.create_rectangle(x0 + 94, cyl_top + 16, x0 + 116, cyl_top + 30,
                               fill="#9fd14f", outline="#6f9b2f")     # tape
            c.create_polygon(x0 + 100, cyl_top + 18, x0 + 300, cyl_top + 18,
                             x0 + 300, cyl_top + 28, x0 + 100, cyl_top + 28,
                             fill="#e8c15a", outline="#a8862f")
            c.create_polygon(x0 + 272, cyl_top + 18, x0 + 290, cyl_top + 23,
                             x0 + 272, cyl_top + 28, fill="#e9d9b6", outline="#a8862f")
            c.create_polygon(x0 + 284, cyl_top + 20, x0 + 290, cyl_top + 23,
                             x0 + 284, cyl_top + 26, fill="#2a2a2a", outline="")
        if b.mmpaper:
            self.draw_mm_paper(x0 + 288, base, tip_rest, A)
        if not (b.pencil and b.mmpaper):
            c.create_text(self.SX + self.SW / 2, base + 60,
                          text=T("연필과 밀리미터 종이를 설치하라.",
                                 "Set up the pencil and the millimetre paper."),
                          fill="#8a8371", font=("TkDefaultFont", 9))

    def draw_mm_paper(self, px, base, tipy, A):
        """Millimetre paper standing on the table, seen from the side.
           The pencil tip draws a vertical stroke whose length is the
           travel of the membrane during one period."""
        c = self.cv
        k = 11.0                              # px per mm
        W = 22 * k
        H = 26 * k
        top = base - H
        c.create_rectangle(px, top, px + W, base, fill="#fdfbf0", outline="#b7b09a",
                           width=2)
        n = int(H / k)
        for i in range(0, n + 1):
            y = base - i * k
            if i % 10 == 0:
                c.create_line(px, y, px + W, y, fill="#7f95c8", width=2)
                c.create_text(px + 5, y - 8, anchor="w", text="%d cm" % (i // 10),
                              fill="#5a6a90", font=("TkDefaultFont", 7))
            else:
                c.create_line(px, y, px + W, y,
                              fill="#a9bade" if i % 5 == 0 else "#d5dcea")
        m = int(W / k)
        for j in range(0, m + 1):
            x = px + j * k
            c.create_line(x, top, x, base,
                          fill="#7f95c8" if j % 10 == 0 else
                          ("#a9bade" if j % 5 == 0 else "#d5dcea"))
        if not self.b.pencil:
            return
        yc = tipy + self.b.ses.paper_zero * k
        half = A * k / 2.0
        if A > 0.02:
            c.create_rectangle(px + 26, yc - half - 1.5, px + 62, yc + half + 1.5,
                               fill="#555555", outline="", stipple="gray25")
            c.create_rectangle(px + 30, yc - half, px + 58, yc + half,
                               fill="#2a2a2a", outline="")
        else:
            c.create_line(px + 30, yc, px + 58, yc, fill="#2a2a2a", width=2)
        c.create_text(px + W / 2, base + 16, text=T("연필 흔적", "pencil trace"),
                      fill="#555", font=("TkDefaultFont", 8))

    # ----- panels
    def draw_siggen(self, x, y):
        c = self.cv
        sg = self.b.sg
        c.create_rectangle(x, y, x + 380, y + 250, fill="#dbe7d0", outline="#8ca57a",
                           width=2)
        c.create_text(x + 10, y + 14, anchor="w",
                      text=T("신호 발생기 (톱니파 · 스피커 구동)",
                             "Signal generator (saw-tooth, speaker drive)"),
                      fill="#3d5230", font=("TkDefaultFont", 10, "bold"))
        c.create_rectangle(x + 20, y + 32, x + 130, y + 64, fill="#1c1c1c", outline="#000")
        c.create_rectangle(x + 40, y + 38, x + 66, y + 58, fill="#d02020", outline="#600")
        c.create_rectangle(x + 78, y + 38, x + 104, y + 58, fill="#111", outline="#000")
        self.term_dot(x + 53, y + 48, "SG.SPK+", "#d02020")
        self.term_dot(x + 91, y + 48, "SG.SPK-", "#111111")
        c.create_text(x + 75, y + 74, text=T("(2) 스피커 단자", "(2) speaker terminals"),
                      fill="#4a5a40", font=("TkDefaultFont", 8))
        px = x + 250
        c.create_oval(px - 24, y + 30, px + 24, y + 78, fill="#3c6fb0", outline="#20406b",
                      width=2)
        a = math.radians(-90 + sg.turns_a * 300.0)
        c.create_line(px, y + 54, px + 20 * math.cos(a), y + 54 + 20 * math.sin(a),
                      fill="#fff", width=3)
        c.create_text(px, y + 90, text="(4) speaker amplitude", fill="#4a5a40",
                      font=("TkDefaultFont", 8))
        self.socket(x + 60, y + 140, "SG.MON", "#e8e8e8", "(6) spk. monitor")
        self.socket(x + 180, y + 140, "SG.GND", "#222222", "(7) GND")
        c.create_rectangle(x + 268, y + 120, x + 316, y + 160, fill="#cfcfcf",
                           outline="#888")
        on = sg.spk_on
        c.create_rectangle(x + 274, y + 126 if on else y + 142, x + 310,
                           y + 142 if on else y + 154, fill="#c33" if on else "#666",
                           outline="")
        c.create_text(x + 292, y + 170, text=T("(8) 스위치", "(8) switch"),
                      fill="#4a5a40", font=("TkDefaultFont", 8))
        c.create_text(x + 10, y + 200, anchor="w",
                      text=T("배터리 팩 연결됨" if sg.powered else "전원 없음",
                             "battery pack connected" if sg.powered else "no power"),
                      fill="#3d5230" if sg.powered else "#a33",
                      font=("TkDefaultFont", 8))
        c.create_text(x + 10, y + 222, anchor="w",
                      text=T("톱니파 진동수 %.0f Hz" % F_DRIVE,
                             "saw-tooth frequency %.0f Hz" % F_DRIVE),
                      fill="#6f7d63", font=("TkDefaultFont", 8))

    def socket(self, x, y, name, col, lab):
        c = self.cv
        c.create_oval(x - 13, y - 13, x + 13, y + 13, fill="#b9b9b9", outline="#777")
        self.term_dot(x, y, name, col)
        c.create_text(x, y + 24, text=lab, fill="#4a5a40", font=("TkDefaultFont", 7))

    def term_dot(self, x, y, name, col):
        c = self.cv
        sel = (self.sel_term == name)
        c.create_oval(x - 8, y - 8, x + 8, y + 8, fill=col,
                      outline=ACC if sel else "#555", width=3 if sel else 1,
                      tags=("term:" + name,))
        self.term[name] = (x, y)

    def draw_dmm(self, x, y):
        c = self.cv
        m = self.b.m1
        c.create_rectangle(x, y, x + 170, y + 250, fill="#2f62a8", outline="#1d3f6e",
                           width=2)
        c.create_text(x + 85, y + 14, text=T("디지털 멀티미터", "Digital multimeter"),
                      fill="#dfe9f5", font=("TkDefaultFont", 9, "bold"))
        c.create_rectangle(x + 12, y + 26, x + 158, y + 74, fill="#cfe6c8",
                           outline="#4d6a45", width=2, tags="disp")
        c.create_text(x + 150, y + 50, anchor="e", text=m.display(self.b.rng),
                      fill="#12240e", font=("TkFixedFont", 18, "bold"), tags="disp")
        c.create_text(x + 85, y + 90, text="%s   %s" % (m.mode, m.range_label()),
                      fill="#dfe9f5", font=("TkDefaultFont", 8))
        c.create_oval(x + 50, y + 104, x + 120, y + 174, fill="#e8e8e8", outline="#999",
                      width=2)
        ar = math.radians(-90 if m.mode == "OFF" else 200)
        c.create_line(x + 85, y + 139, x + 85 + 28 * math.cos(ar),
                      y + 139 + 28 * math.sin(ar), fill="#222", width=4)
        self.term_dot(x + 50, y + 214, "M1.IN", "#d8b800")
        c.create_text(x + 50, y + 230, text="V mA Ω", fill="#dfe9f5",
                      font=("TkDefaultFont", 7))
        self.term_dot(x + 120, y + 214, "M1.COM", "#111111")
        c.create_text(x + 120, y + 230, text="GND", fill="#dfe9f5",
                      font=("TkDefaultFont", 7))

    def draw_speaker_panel(self, x, y):
        c = self.cv
        c.create_rectangle(x, y, x + 380, y + 130, fill="#efece2", outline="#c1baa6")
        c.create_text(x + 10, y + 14, anchor="w",
                      text=T("스피커 조립체 단자", "speaker assembly terminals"),
                      fill="#6b6553", font=("TkDefaultFont", 9, "bold"))
        c.create_rectangle(x + 30, y + 40, x + 150, y + 110, fill="#f2f2f2",
                           outline="#bbb", width=2)
        c.create_oval(x + 40, y + 48, x + 140, y + 104, fill="#232323", outline="#111")
        c.create_oval(x + 70, y + 62, x + 110, y + 90, fill="#e6eef2", outline="#9ab")
        c.create_line(x + 150, y + 60, x + 220, y + 52, fill="#c33", width=3)
        c.create_line(x + 150, y + 88, x + 220, y + 96, fill="#222", width=3)
        self.term_dot(x + 228, y + 52, "SPK.a", "#d02020")
        c.create_text(x + 246, y + 52, anchor="w", text=T("빨강", "red"), fill="#4a4536",
                      font=("TkDefaultFont", 8))
        self.term_dot(x + 228, y + 96, "SPK.b", "#111111")
        c.create_text(x + 246, y + 96, anchor="w", text=T("검정", "black"), fill="#4a4536",
                      font=("TkDefaultFont", 8))

    def draw_wires(self):
        c = self.cv
        for i, (a, b) in enumerate(self.b.wires):
            if a not in self.term or b not in self.term:
                continue
            x0, y0 = self.term[a]
            x1, y1 = self.term[b]
            c.create_line(x0, y0, (x0 + x1) / 2, max(y0, y1) + 28, x1, y1, smooth=True,
                          width=3, fill=WIRE_COLORS[i % len(WIRE_COLORS)],
                          capstyle="round", tags=("wire%d" % i,))

    # --------------------------------------------------------------- events
    def on_click(self, ev):
        it = self.cv.find_withtag("current")
        if not it:
            return
        for tg in self.cv.gettags(it[0]):
            if tg.startswith("term:"):
                self.click_term(tg[5:])
                return
            if tg.startswith("wire"):
                self.b.del_wire(int(tg[4:]))
                self.refresh_w()
                self.redraw()
                return

    def click_term(self, name):
        if self.sel_term is None:
            self.sel_term = name
        elif self.sel_term == name:
            self.sel_term = None
        else:
            self.b.add_wire(self.sel_term, name)
            self.sel_term = None
            self.refresh_w()
        self.redraw()

    # ---------------------------------------------------------------- timer
    tickcount = 0

    def tick(self):
        self.tickcount += 1
        self.b.step(0.35)
        self.b.evaluate()
        if self.b.view == "top":
            self.redraw()
        else:
            self.redraw()
        self.after(350, self.tick)


# ===========================================================================
class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.title(T("IPhO 2016 실험 E-II — 튀는 알갱이  |  HaslaLab",
                     "IPhO 2016 Experiment E-II - Jumping beads  |  HaslaLab"))
        self.configure(bg=BG)
        self.geometry("1440x900")
        self.session = Session(seed)
        self.bench = Bench(self.session)
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.asm = AssemblyTab(self.nb, self)
        self.nb.add(self.asm, text=T("  조립  ", "  Assembly  "))
        self.bt = BenchTab(self.nb, self)
        self.nb.add(self.bt, text=T("  실험대  ", "  Bench  "))
        self.nb.tab(1, state="disabled")

    def enable_bench(self):
        try:
            self.nb.tab(1, state="normal")
            self.bt.redraw()
        except Exception:
            pass


def main():
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
    App(seed).mainloop()


if __name__ == "__main__":
    main()
