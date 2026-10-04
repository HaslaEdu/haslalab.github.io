#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPhO 2024 (Isfahan, Iran) - Experimental Problem E1
"Heat Conduction in a Copper Rod" (10 points) - virtual laboratory

The apparatus delivers nothing but what the real one delivers: the AVA-T403
monitor (thermistors 1-7, theta_b or R9, the PT100 resistance R, its timer and
its saved LAP data), the four switches and the five keys.  Nothing is computed
for the user: no fit, no slope, no logarithm, no C_S, gamma, E_g, lambda, A, B,
h, k or P3, no score.  The graphs of A-3, A-5, A-7, B-2, B-6 and C-2 are the
user's work on paper.  The two plots shown are the raw R(t) trace of the PT100
and the raw temperatures of the seven thermistors against their position.

Run:  python ipho2024_E1_sim_KO.py   (EN edition: ipho2024_E1_sim_EN.py)
Needs numpy and matplotlib (pip install numpy matplotlib).

--------------------------------------------------------------------------
PHYSICAL MODEL (forward model, not a replay of the official table)
  short rod   C_S dtheta/dt = P1 - C_S gamma (theta - theta_env)
              so the cooling branch is exactly R - R_env = A exp(-gamma t)
  PT100       R = R0 (1 + alpha theta),  R0 = 100.00 ohm, alpha = 0.0039083 /C
  R9          R9 = R9_0 exp(E_g / 2 k_B T)
  long rod    steady state = superposition of the two end heaters
                 theta(x) - theta_b = P2 g(x) + P3 g(L - x)
                 g(x) = g0 ( e^{-lam x} + e^{-2 lam d} e^{+lam x} )
              i.e. eq. (6) of the sheet with B = A e^{-2 lam d};
              single relaxation (tau = 420 s) towards it.

CALIBRATION (official solution E1_S)
    A.1  R_env = 110.11 ohm      A.3  C_S = 52 +- 2 J/C
    A.5  gamma = (710 +- 3)e-6 /s   A.7  E_g = 0.698 +- 0.007 eV
    B.7  lambda = 0.053 +- 0.008 /cm      C.3  P3 = 0.60 P2
  built-in truth  P1 = 1.95 W, P2 = 5.00 W, P3 = 0.600 P2, C_S = 49.8 J/C
                  (the straight-line fit of A-3, which ignores the small loss,
                  then returns 52 J/C), lambda = 0.0530 /cm, d = 44.0 cm

INSTRUMENT LIMITS
  AVA refreshes every 2 s; temperatures 0.01 C, R 0.01 ohm, R9 1 ohm;
  thermal dead time of a thermistor in its hole ~32 s; the LAP key carries
  the human reaction time.  The apparatus is redrawn (+-1 %) at every new
  session.
--------------------------------------------------------------------------
"""

import csv
import math
from collections import deque

import numpy as np

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


LANG = "EN"          # the EN edition differs only in this line
TR = {
    "IPhO 2024 E1 - Heat Conduction in a Copper Rod : Virtual Lab":
        "IPhO 2024 E1 - 구리 막대의 열전도 : 가상 실험실",
    "AVA-T403  control panel": "AVA-T403  제어판",
    "FAN": "팬",
    "HEATER 1": "히터 1",
    "HEATER 2": "히터 2",
    "HEATER 3": "히터 3",
    "START / STOP": "START / STOP",
    "LAP / RESET": "LAP / RESET",
    "PREV": "PREV",
    "NEXT": "NEXT",
    "ERASE DATA": "데이터 지우기",
    "time factor": "시간 배속",
    "New session": "새 장치",
    "Saved LAP data": "저장된 LAP 데이터",
    "Export CSV": "CSV 내보내기",
    "view": "보기",
    "PT100 resistance R vs time (raw)": "PT100 저항 R 대 시간 (원자료)",
    "thermistors 1-7 vs position (raw)": "서미스터 1-7 대 위치 (원자료)",
    "Save PNG": "PNG 저장",
    "live PT100": "실시간 PT100",
    "LAP data": "LAP 데이터",
    "live": "실시간",
    "PT100 resistance": "PT100 저항",
    "temperatures along the rod": "막대를 따라 잰 온도",
    "Ready.  Switch HEATER 2 and the FAN on first (Part B needs about 15 min "
    "of experiment time), then do Part A with HEATER 1.\n":
        "준비 완료.  먼저 히터 2와 팬을 켜 두고 (B 부분은 실험 시간으로 약 15분이 "
        "걸립니다), 그동안 히터 1로 A 부분을 하세요.\n",
    "Timer reset (saved data kept).\n": "타이머를 0으로 돌렸습니다 (저장된 데이터는 그대로).\n",
    "Erase": "지우기",
    "Erase all saved LAP data?": "저장된 LAP 데이터를 모두 지울까요?",
    "Restart with a freshly randomised apparatus?": "새로 무작위로 정한 장치로 다시 시작할까요?",
    "\n=== New apparatus. ===\n": "\n=== 새 장치 ===\n",
    "!! AVA: \"Turn off Heater1\" - switch heater 1 off now.\n":
        "!! AVA: \"Turn off Heater1\" - 지금 히터 1을 끄세요.\n",
    "No LAP data yet.": "아직 LAP 데이터가 없습니다.",
    "rows exported": "행을 내보냈습니다",
    "figure saved": "그림을 저장했습니다",
    "On the bench the timer, the LAP key and the display are those of AVA. "
    "Hold the time factor at 1x for reaction-time-sensitive readings.\n":
        "타이머·LAP 키·화면은 모두 AVA의 것입니다. 반응 시간이 중요한 읽기는 "
        "배속 1x로 하세요.\n",
}


def T(s):
    return TR.get(s, s) if LANG != "EN" else s


def _setup_hangul_font(root):
    """Point every named Tk font, and matplotlib, at a family that has Hangul."""
    import tkinter.font as _tkfont
    want = ("Malgun Gothic", "AppleGothic", "Apple SD Gothic Neo",
            "NanumGothic", "NanumBarunGothic", "Noto Sans CJK KR",
            "Noto Sans KR", "UnDotum", "Gulim", "Batang")
    have = set(_tkfont.families(root))
    fam = next((f for f in want if f in have), None)
    if not fam:
        return
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont",
                 "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont",
                 "TkIconFont", "TkTooltipFont"):
        try:
            _tkfont.nametofont(name, root).configure(family=fam)
        except Exception:
            pass
    try:
        matplotlib.rcParams["font.family"] = [fam, "DejaVu Sans"]
        matplotlib.rcParams["axes.unicode_minus"] = False
    except Exception:
        pass


# ---------------------------------------------------------------------------
#  physical constants given on the problem sheet
# ---------------------------------------------------------------------------
KB = 8.61733e-5           # eV / K
R0_PT100 = 100.00         # ohm
ALPHA_PT100 = 0.0039083   # 1/C
ROD_LENGTH = 57.0         # cm
ROD_RADIUS = 0.60         # cm  (diameter 1.20 cm)
SENSOR_X = np.array([0.0, 7.0, 14.0, 21.0, 28.0, 35.0, 42.0])   # cm
D_FAR = 44.0              # cm   (B-4)

# ---------------------------------------------------------------------------
#  ground truth (randomised slightly at every session)
# ---------------------------------------------------------------------------
TRUE = dict(
    P1=1.95,              # W   nameplate of heater 1
    P2=5.00,              # W   nameplate of heater 2
    P3_over_P2=0.600,     # -   unknown power of heater 3
    CS=49.8,              # J/C total heat capacity of the short rod assembly
    gamma=710e-6,         # 1/s cooling constant of the short rod
    Eg=0.6983,            # eV  band gap of the thermistor material
    R9_0=0.012012,        # ohm prefactor of R9 = R9_0 exp(Eg/2kT)
    lam=0.0530,           # 1/cm  decay constant of the long rod
    g0=3.446,             # C/W   (theta(0)-theta_b) per watt, heater at x=0
    theta_room=24.60,     # C     box air with everything off
    box_gain=0.42,        # C/W   rise of theta_b per watt of heater power
    theta_env=25.87,      # C     ambient seen by the short (isolated) rod
)


def q(value, step):
    """Quantise a reading the way the AVA display does."""
    return round(round(value / step) * step, 6)


def pt100_from_theta(th):
    return R0_PT100 * (1.0 + ALPHA_PT100 * th)


# ===========================================================================
#  PHYSICS ENGINE
# ===========================================================================
class HeatRodModel:

    SENSOR_DELAY = 32.0        # s   dead time of a thermistor in a drilled hole
    TAU_LONG = 420.0           # s   relaxation time of the 57 cm rod
    TAU_BOX = 240.0            # s   relaxation time of the box air

    def __init__(self, seed=None):
        rng = np.random.default_rng(seed)
        t = dict(TRUE)
        t["CS"] *= 1.0 + rng.normal(0, 0.010)
        t["gamma"] *= 1.0 + rng.normal(0, 0.008)
        t["Eg"] *= 1.0 + rng.normal(0, 0.004)
        t["lam"] *= 1.0 + rng.normal(0, 0.012)
        t["g0"] *= 1.0 + rng.normal(0, 0.010)
        t["P3_over_P2"] *= 1.0 + rng.normal(0, 0.010)
        t["theta_env"] += rng.normal(0, 0.25)
        t["theta_room"] += rng.normal(0, 0.25)
        self.t = t
        self.rng = rng

        self.time = 0.0
        self.fan = False
        self.heater = [False, False, False]          # heaters 1, 2, 3

        self.theta_short = t["theta_env"]
        self.theta_b = t["theta_room"]
        self.theta_long = np.full(len(SENSOR_X), t["theta_room"])

        self._buf_short = deque()
        self._buf_long = deque()
        self._buf_box = deque()
        self._push_buffers()
        self._last = None
        self._last_t = -1e9

    @property
    def P2(self):
        return self.t["P2"] if self.heater[1] else 0.0

    @property
    def P3(self):
        return self.t["P2"] * self.t["P3_over_P2"] if self.heater[2] else 0.0

    def g(self, x):
        lam, d = self.t["lam"], D_FAR
        return self.t["g0"] * (np.exp(-lam * x) + math.exp(-2 * lam * d) * np.exp(lam * x))

    def steady_long(self):
        """Steady-state temperatures of thermistors 1..7 and of the box air."""
        theta_b = self.t["theta_room"] + self.t["box_gain"] * (self.P2 + self.P3)
        prof = theta_b + self.P2 * self.g(SENSOR_X) + self.P3 * self.g(42.0 - SENSOR_X)
        if not self.fan:            # weaker convection without the fans
            prof = theta_b + (prof - theta_b) * 1.35
        return prof, theta_b

    def step(self, dt):
        """Advance the simulation by dt seconds of experiment time."""
        if dt <= 0:
            return
        n = max(1, int(dt / 2.0))
        h = dt / n
        for _ in range(n):
            P1 = self.t["P1"] if self.heater[0] else 0.0
            dth = (P1 / self.t["CS"]) - self.t["gamma"] * (self.theta_short - self.t["theta_env"])
            self.theta_short += dth * h
            prof, tb = self.steady_long()
            self.theta_long += (prof - self.theta_long) * (1.0 - math.exp(-h / self.TAU_LONG))
            self.theta_b += (tb - self.theta_b) * (1.0 - math.exp(-h / self.TAU_BOX))
            self.time += h
            self._push_buffers()

    def _push_buffers(self):
        self._buf_short.append((self.time, self.theta_short))
        self._buf_long.append((self.time, self.theta_long.copy()))
        self._buf_box.append((self.time, self.theta_b))
        cut = self.time - self.SENSOR_DELAY - 5.0
        for b in (self._buf_short, self._buf_long, self._buf_box):
            while len(b) > 2 and b[1][0] < cut:
                b.popleft()

    def _delayed(self, buf):
        target = self.time - self.SENSOR_DELAY
        prev = buf[0]
        for item in buf:
            if item[0] >= target:
                return item[1]
            prev = item
        return prev[1]

    def read(self):
        """What the AVA monitor shows: refreshed every 2 s of experiment time."""
        if self._last is not None and self.time - self._last_t < 2.0:
            return self._last
        th_s = self._delayed(self._buf_short)
        th_l = self._delayed(self._buf_long)
        th_b = self._delayed(self._buf_box)

        n = self.rng.normal
        R_pt = pt100_from_theta(th_s + n(0, 0.004))
        T_ = th_s + 273.15 + n(0, 0.010)
        R9 = self.t["R9_0"] * math.exp(self.t["Eg"] / (2 * KB * T_))

        self._last = dict(
            t=self.time,
            R_pt100=q(R_pt, 0.01),
            R9=int(round(R9 * (1.0 + n(0, 0.0015)))),
            theta=[q(v + n(0, 0.012), 0.01) for v in th_l],
            theta_b=q(th_b + n(0, 0.012), 0.01),
        )
        self._last_t = self.time
        return self._last


# ===========================================================================
#  GUI
# ===========================================================================
class App(tk.Tk):

    SPEEDS = [1, 2, 5, 10, 30, 60, 120, 300]
    TICK_MS = 100

    def __init__(self):
        super().__init__()
        _setup_hangul_font(self)
        self.title(T("IPhO 2024 E1 - Heat Conduction in a Copper Rod : Virtual Lab"))
        self.geometry("1440x880")
        self.minsize(1180, 760)

        self.model = HeatRodModel()
        self.speed = tk.IntVar(value=1)
        self.show_R9 = tk.BooleanVar(value=False)
        self.timer_running = False
        self.timer_t0 = 0.0
        self.timer_value = 0.0
        self.laps = []
        self.lap_cursor = -1
        self.warned_120 = False
        self.status_msg = ""
        self.trace_t, self.trace_R = [], []

        self._build_ui()
        self.after(self.TICK_MS, self._tick)

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = ttk.Frame(self, padding=8)
        root.pack(fill="both", expand=True)
        left = ttk.Frame(root)
        left.pack(side="left", fill="y", padx=(0, 8))
        right = ttk.Frame(root)
        right.pack(side="left", fill="both", expand=True)
        self._build_panel(left)
        self._build_laptable(left)
        self._build_plots(right)

    def _build_panel(self, parent):
        box = ttk.LabelFrame(parent, text=T("AVA-T403  control panel"), padding=6)
        box.pack(fill="x")

        self.disp = tk.Canvas(box, width=470, height=232, bg="#0b0b0b",
                              highlightthickness=1, highlightbackground="#444")
        self.disp.pack()

        sw = ttk.Frame(box)
        sw.pack(fill="x", pady=(8, 2))
        self.v_fan = tk.BooleanVar(value=False)
        self.v_h1 = tk.BooleanVar(value=False)
        self.v_h2 = tk.BooleanVar(value=False)
        self.v_h3 = tk.BooleanVar(value=False)
        # the panel prints the power of heater 1 and the nameplate that of heater 2
        ttk.Checkbutton(sw, text=T("FAN"), variable=self.v_fan,
                        command=self._switches).grid(row=0, column=0, padx=6, sticky="w")
        ttk.Checkbutton(sw, text=T("HEATER 1") + "  (1.95 W)", variable=self.v_h1,
                        command=self._switches).grid(row=0, column=1, padx=6, sticky="w")
        ttk.Checkbutton(sw, text=T("HEATER 2") + "  (P2 = 5.0 ± 0.1 W)", variable=self.v_h2,
                        command=self._switches).grid(row=1, column=0, padx=6, pady=3, sticky="w")
        ttk.Checkbutton(sw, text=T("HEATER 3") + "  ( ? W)", variable=self.v_h3,
                        command=self._switches).grid(row=1, column=1, padx=6, pady=3, sticky="w")

        bt = ttk.Frame(box)
        bt.pack(fill="x", pady=(6, 0))
        ttk.Button(bt, text=T("START / STOP"), width=14,
                   command=self._start_stop).grid(row=0, column=0, padx=2)
        ttk.Button(bt, text=T("LAP / RESET"), width=13,
                   command=self._lap).grid(row=0, column=1, padx=2)
        ttk.Button(bt, text="θb ↔ R9", width=11,
                   command=lambda: self.show_R9.set(not self.show_R9.get())
                   ).grid(row=0, column=2, padx=2)
        ttk.Button(bt, text=T("PREV"), width=7,
                   command=lambda: self._browse(-1)).grid(row=1, column=0, pady=4)
        ttk.Button(bt, text=T("NEXT"), width=7,
                   command=lambda: self._browse(+1)).grid(row=1, column=1, pady=4)
        ttk.Button(bt, text=T("ERASE DATA"), width=13,
                   command=self._erase).grid(row=1, column=2, pady=4)

        sp = ttk.Frame(box)
        sp.pack(fill="x", pady=(8, 0))
        ttk.Label(sp, text=T("time factor")).pack(side="left")
        cb = ttk.Combobox(sp, width=8, state="readonly",
                          values=[f"{s}x" for s in self.SPEEDS])
        cb.set("1x")
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>",
                lambda e: self.speed.set(int(cb.get()[:-1])))
        ttk.Button(sp, text=T("New session"), command=self._new_session
                   ).pack(side="right")

    def _build_laptable(self, parent):
        box = ttk.LabelFrame(parent, text=T("Saved LAP data"), padding=4)
        box.pack(fill="both", expand=True, pady=(8, 0))
        cols = ("n", "t", "R", "R9", "thb") + tuple(f"th{i}" for i in range(1, 8))
        heads = ("#", "t (s)", "R (Ω)", "R9 (Ω)", "θb") + \
            tuple(f"θ{i}" for i in range(1, 8))
        self.tree = ttk.Treeview(box, columns=cols, show="headings", height=13)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width={"n": 30, "t": 52, "R": 56, "R9": 50}.get(c, 44),
                             anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        bar = ttk.Frame(parent)
        bar.pack(fill="x", pady=4)
        ttk.Button(bar, text=T("Export CSV"), command=self._export).pack(side="left", padx=2)

    def _build_plots(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x")
        ttk.Label(top, text=T("view")).pack(side="left")
        self.view = ttk.Combobox(top, width=40, state="readonly", values=[
            T("PT100 resistance R vs time (raw)"),
            T("thermistors 1-7 vs position (raw)"),
        ])
        self.view.current(0)
        self.view.pack(side="left", padx=6)
        self.view.bind("<<ComboboxSelected>>", lambda e: self._redraw())
        ttk.Button(top, text=T("Save PNG"), command=self._save_png).pack(side="right")

        self.fig = Figure(figsize=(7.6, 7.0), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, pady=4)

        self.log = tk.Text(parent, height=8, wrap="word", font=("Consolas", 9))
        self.log.pack(fill="x")
        self._say(T("Ready.  Switch HEATER 2 and the FAN on first (Part B needs about 15 min "
                    "of experiment time), then do Part A with HEATER 1.\n"))
        self._say(T("On the bench the timer, the LAP key and the display are those of AVA. "
                    "Hold the time factor at 1x for reaction-time-sensitive readings.\n"))

    # ------------------------------------------------------------------
    def _say(self, text):
        self.log.insert("end", text)
        self.log.see("end")

    def _switches(self):
        m = self.model
        m.fan = self.v_fan.get()
        m.heater = [self.v_h1.get(), self.v_h2.get(), self.v_h3.get()]
        if not self.v_h1.get():
            self.warned_120 = False

    def _start_stop(self):
        if self.timer_running:
            self.timer_running = False
        else:
            self.timer_running = True
            self.timer_t0 = self.model.time - self.timer_value

    def _lap(self):
        if not self.timer_running:
            self.timer_value = 0.0
            self._say(T("Timer reset (saved data kept).\n"))
            return
        r = self.model.read()
        rec = dict(n=len(self.laps) + 1,
                   t=int(self.timer_value),           # AVA's timer counts whole seconds
                   R=r["R_pt100"], R9=r["R9"], theta=list(r["theta"]),
                   theta_b=r["theta_b"])
        self.laps.append(rec)
        self.lap_cursor = len(self.laps) - 1
        self.tree.insert("", "end", values=(
            rec["n"], rec["t"], f"{rec['R']:.2f}", rec["R9"], f"{rec['theta_b']:.2f}",
            *[f"{v:.2f}" for v in rec["theta"]]))
        self.tree.see(self.tree.get_children()[-1])
        self._redraw()

    def _browse(self, d):
        if not self.laps:
            return
        self.lap_cursor = max(0, min(len(self.laps) - 1, self.lap_cursor + d))
        kids = self.tree.get_children()
        self.tree.selection_set(kids[self.lap_cursor])
        self.tree.see(kids[self.lap_cursor])
        self._redraw()

    def _erase(self):
        if messagebox.askyesno(T("Erase"), T("Erase all saved LAP data?")):
            self._erase_silent()
            self._redraw()

    def _erase_silent(self):
        self.laps.clear()
        self.lap_cursor = -1
        for k in self.tree.get_children():
            self.tree.delete(k)

    def _new_session(self):
        if not messagebox.askyesno(T("New session"),
                                   T("Restart with a freshly randomised apparatus?")):
            return
        self.model = HeatRodModel()
        self.timer_running = False
        self.timer_value = 0.0
        self.trace_t.clear()
        self.trace_R.clear()
        self._erase_silent()
        for v in (self.v_fan, self.v_h1, self.v_h2, self.v_h3):
            v.set(False)
        self._switches()
        self._say(T("\n=== New apparatus. ===\n"))

    # ------------------------------------------------------------------
    def _tick(self):
        dt = self.TICK_MS / 1000.0 * self.speed.get()
        self.model.step(dt)
        if self.timer_running:
            self.timer_value = self.model.time - self.timer_t0

        r = self.model.read()
        if not self.trace_t or self.trace_t[-1] != r["t"]:
            self.trace_t.append(r["t"])
            self.trace_R.append(r["R_pt100"])
            if len(self.trace_t) > 20000:
                del self.trace_t[:4000], self.trace_R[:4000]

        if self.v_h1.get() and r["R_pt100"] >= 120.0:
            self.status_msg = "Turn off Heater1"
            if not self.warned_120:
                self.warned_120 = True
                self._say(T("!! AVA: \"Turn off Heater1\" - switch heater 1 off now.\n"))
        else:
            self.status_msg = ""

        self._draw_display(r)
        self._n = getattr(self, "_n", 0) + 1
        if self._n % 10 == 0:
            self._redraw()
        self.after(self.TICK_MS, self._tick)

    def _draw_display(self, r):
        c = self.disp
        c.delete("all")
        F = ("Consolas", 12, "bold")
        G = "#7dff6a"
        O = "#ff9a3c"
        c.create_rectangle(6, 6, 464, 226, outline="#2a2a2a")
        c.create_text(80, 18, text="NTC", fill=O, font=("Consolas", 9, "bold"))
        c.create_text(345, 18, text="RTD", fill=O, font=("Consolas", 9, "bold"))
        for i, th in enumerate(r["theta"]):
            c.create_text(18, 40 + 23 * i, anchor="w",
                          text=f"0{i+1}: {th:6.2f} °C", fill=G, font=F)
        last = f"R9: {r['R9']:6d} Ω" if self.show_R9.get() else f"θb: {r['theta_b']:6.2f} °C"
        c.create_text(18, 40 + 23 * 7, anchor="w", text=last, fill=G, font=F)
        c.create_line(220, 10, 220, 222, fill="#333")
        c.create_text(345, 40, text=f"R: {r['R_pt100']:.2f} Ω", fill=G,
                      font=("Consolas", 14, "bold"))
        c.create_text(345, 64, text="Timer (Second)", fill=O, font=("Consolas", 8))
        c.create_text(345, 86, text=f"{int(self.timer_value):05d}", fill=G,
                      font=("Consolas", 18, "bold"))
        c.create_text(290, 112, text="Status", fill=O, font=("Consolas", 8))
        c.create_text(290, 132, text="Run" if self.timer_running else "Stop",
                      fill=G if self.timer_running else "#ff5555", font=("Consolas", 12, "bold"))
        c.create_text(400, 112, text="Count Lap", fill=O, font=("Consolas", 8))
        shown = self.lap_cursor + 1 if self.laps else 0
        c.create_text(400, 132, text=f"{shown:02d}", fill=G, font=("Consolas", 12, "bold"))
        st = [("Fan", self.v_fan.get()), ("Heater1", self.v_h1.get()),
              ("Heater2", self.v_h2.get()), ("Heater3", self.v_h3.get())]
        for i, (nm, on) in enumerate(st):
            c.create_text(240, 150 + 14 * i, anchor="w", text=f"{nm}: {'ON ' if on else 'OFF'}",
                          fill=G if on else "#cc4444", font=("Consolas", 9, "bold"))
        if self.status_msg:
            c.create_text(345, 220, text=self.status_msg, fill="#ff4444",
                          font=("Consolas", 11, "bold"))

    # ------------------------------------------------------------------
    def _redraw(self):
        ax = self.ax
        ax.clear()
        ax.grid(True, which="both", alpha=0.3)
        if self.view.current() == 0:
            ax.plot(self.trace_t, self.trace_R, "-", color="#1f77b4", lw=1.0,
                    label=T("live PT100"))
            ax.set_xlabel("t (s)")
            ax.set_ylabel("R (Ω)")
            ax.set_title(T("PT100 resistance"))
            ax.legend(loc="best", fontsize=8)
        else:
            r = self.model.read()
            ax.plot(SENSOR_X, r["theta"], "o", color="#1f77b4", ms=6, label=T("live"))
            if self.laps:
                l = self.laps[self.lap_cursor]
                ax.plot(SENSOR_X, l["theta"], "s", color="#ff7f0e", ms=5,
                        label=f"LAP #{l['n']}")
            ax.set_xlabel("x (cm)")
            ax.set_ylabel("θ (°C)")
            ax.set_title(T("temperatures along the rod"))
            ax.legend(loc="best", fontsize=8)
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def _save_png(self):
        p = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if p:
            self.fig.savefig(p, dpi=150)
            self._say(f"{T('figure saved')} -> {p}\n")

    def _export(self):
        if not self.laps:
            messagebox.showinfo(T("Export CSV"), T("No LAP data yet."))
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not p:
            return
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["n", "t_s", "R_PT100_ohm", "R9_ohm", "theta_b_C"] +
                       [f"theta_{i+1}_C" for i in range(7)])
            for l in self.laps:
                w.writerow([l["n"], l["t"], l["R"], l["R9"], l["theta_b"]] +
                           [f"{v:.2f}" for v in l["theta"]])
        self._say(f"{len(self.laps)} {T('rows exported')} -> {p}\n")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
