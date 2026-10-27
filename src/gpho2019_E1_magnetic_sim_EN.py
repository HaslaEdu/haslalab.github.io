#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  3rd Gulf Physics Olympiad  (GPhO 2019, Muscat, Oman)
  Experimental Problem E1 :  MAGNETIC PROPERTIES OF MATTER
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The apparatus of the problem sheet: a green laser (532 nm) clipped
    to the upright syringe, a white and a green syringe needle, a piece
    of foam, a foldable mirror, the stand with graph paper as the screen,
    a silicone tube with water, a Petri dish, a graphite bar, the magnet
    wrapped in film, two ferromagnetic strips with a spacer, a
    magnetoresistive sensor, a battery holder and a multimeter.
    Only what the student would see is shown: the fringes on the paper,
    the water level and the needle against the tape, the chip against
    the ruler, the meter's digits.  No diameter, surface tension,
    susceptibility or permeability is computed for you.  The hidden
    values are randomised each session; --seed N repeats a session.

    Run:   python3 gpho2019_E1_magnetic_sim_EN.py   [--seed N]
"""
import math
import random
import time
import sys
import tkinter as tk

APP_VERSION = "1.0"
LANG = "EN"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "KO" else en


SEED = None
for i, a in enumerate(sys.argv):
    if a == "--seed" and i + 1 < len(sys.argv):
        SEED = int(sys.argv[i + 1])
RNG = random.Random(SEED)


def gauss():
    return RNG.gauss(0.0, 1.0)


# ==============================================================================
#  1.  참값 (학생에게 보이지 않음) — 공식 해설에 맞춤
# ==============================================================================
LAM, RHO, G, CHI_W, DELTA = 532e-9, 1000.0, 9.81, -9.05e-9, 0.27e-3
NEEDLE = {"W": 0.31e-3 * (1 + 0.02 * gauss()), "G": 0.24e-3 * (1 + 0.025 * gauss())}
NCOL = {"W": "#eef0f2", "G": "#3fb35a"}
SIGMA = 0.0652 * (1 + 0.03 * gauss())
LC = math.sqrt(SIGMA / (RHO * G))
CHI_G = -6.2e-8 * (1 + 0.1 * gauss())
MAG_D, GAP = 1.0 + 0.015 * gauss(), 0.77 * (1 + 0.03 * gauss())      # cm
MU_N, BK, B_END = 57000 * (1 + 0.08 * gauss()), 1.05 * (1 + 0.04 * gauss()), 0.227e-3 * (1 + 0.06 * gauss())
E_BAT, V0_MV, S_OFF = 3.12 + 0.1 * RNG.random(), 2.0 + 1.0 * gauss(), 0.8 * gauss()

# 문제지 그림 7 (메니스커스 기울기) 과 그림 8 (자기 압력 기울기) 을 읽은 값
FIG7 = [(0, 1.32), (0.1, 0.973), (0.25, 0.708), (0.5, 0.471), (0.75, 0.322), (1, 0.223), (1.25, 0.156), (1.5, 0.109), (2, 0.0537),
        (2.5, 0.0265), (3, 0.0129), (3.5, 0.00638), (4, 0.00315), (4.5, 0.00156), (4.8, 0.00102)]
FIG8 = [(0, 4.64e7), (0.5, 4.28e7), (1, 3.66e7), (1.5, 3.06e7), (2, 2.44e7), (3, 1.44e7), (4, 8.29e6), (5, 4.57e6), (6, 2.56e6), (7, 1.46e6),
        (8, 8.49e5), (9, 5.16e5), (10, 3.16e5), (11, 2.0e5), (12, 1.31e5), (13, 8.7e4), (14, 5.88e4), (16, 2.87e4), (18, 1.48e4), (20, 8.15e3)]


def log_interp(Tb, x):
    if x <= Tb[0][0]:
        return Tb[0][1]
    n = len(Tb) - 1
    if x >= Tb[n][0]:
        s = math.log(Tb[n][1] / Tb[n - 1][1]) / (Tb[n][0] - Tb[n - 1][0])
        return Tb[n][1] * math.exp(s * (x - Tb[n][0]))
    for i in range(n):
        if x <= Tb[i + 1][0]:
            f = (x - Tb[i][0]) / (Tb[i + 1][0] - Tb[i][0])
            return Tb[i][1] * (Tb[i + 1][1] / Tb[i][1]) ** f


def slope_at(l_m):
    return log_interp(FIG7, l_m / LC)


def grad_at(r_mm):
    return log_interp(FIG8, r_mm)


# ---- 부분 D: 틈의 자기장 (자석 없는 끝 z = 0 에서 자석까지) ---- #
STRIP_A, STRIP_L = 0.030, 60


def s_profile(s_mm):
    q, k = abs(s_mm - S_OFF), 1 + 0.008 * (s_mm - S_OFF)
    return k * (1 - 0.1 * (q / 12) ** 2 if q <= 12 else 0.9 * math.exp(-((q - 12) / 5.5) ** 2))


A_EFF = sum(s_profile(-40 + 0.05 * i) * 0.05 for i in range(1601)) / 1000


def _gap_table():
    a, h, mui, dz = STRIP_A, GAP / 100, MU_N * A_EFF / STRIP_A, 1e-4

    def f(Bg, Phi):
        Bin = Phi / (a * DELTA)
        return A_EFF * Bg, 2 * Bin / (h * mui / (1 + (Bin / BK) ** 5))
    Bg, Phi, out = B_END, 0.0, []
    for i in range(STRIP_L * 100 + 1):
        if i % 10 == 0:
            out.append(Bg)
        k1 = f(Bg, Phi)
        k2 = f(Bg + dz / 2 * k1[1], Phi + dz / 2 * k1[0])
        k3 = f(Bg + dz / 2 * k2[1], Phi + dz / 2 * k2[0])
        k4 = f(Bg + dz * k3[1], Phi + dz * k3[0])
        Phi += dz / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        Bg = min(0.012, Bg + dz / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]))
    return out


BG_T = _gap_table()


def gap_field(zf):
    n = len(BG_T) - 1
    L = n / 10.0
    if zf < 0:
        return BG_T[0] * math.exp(zf / 0.9)
    if zf > L:
        return BG_T[n] * math.exp(-(zf - L) / 0.9)
    i = min(n - 1, int(zf * 10))
    f = zf * 10 - i
    return BG_T[i] * (1 - f) + BG_T[i + 1] * f


# ---- 부분 B: 관 (cm) ---- #
TUBE_HALF, TUBE_A, KQ = 28.0, 0.126, 1.2e-11
CLIP_Y, CLIP_DZ = 29.4, 10.0


def tate(d):
    return 2 * math.pi * (d / 2) * SIGMA * 0.62 / (RHO * G)


def arm_at(B, C, s, t):
    return (B[0] + (C[0] - B[0]) * t, B[1] + (C[1] - B[1]) * t - 4 * s * t * (1 - t))


def arm_len(B, C, s):
    L, p = 0.0, B
    for i in range(1, 49):
        q = arm_at(B, C, s, i / 48.0)
        L += math.hypot(q[0] - p[0], q[1] - p[1])
        p = q
    return L


def sag_for(B, C):
    if arm_len(B, C, 0) >= TUBE_HALF:
        return 0.0
    a, b = 0.0, 40.0
    for _ in range(36):
        m = (a + b) / 2
        if arm_len(B, C, m) < TUBE_HALF:
            a = m
        else:
            b = m
    return (a + b) / 2


YB_MIN = CLIP_Y - math.sqrt(TUBE_HALF ** 2 - CLIP_DZ ** 2) + 0.05
YB_MAX = CLIP_Y - 1.5

# ---- 부분 C: 접시 (cm) ---- #
R_IN, DISH_H, WATER_Y = 4.4, 1.5, 0.75
MAGN = (math.sqrt(0.5), -math.sqrt(0.5))
DIAL = ["OFF", "DCV 200m", "DCV 2", "DCV 20", "DCV 200", "DCA 200m", "DCA 10", "Ω 200", "Ω 2k", "Ω 20k"]


class State(object):
    def __init__(self):
        self.laser = False
        self.mir = 121.5                 # 거울: 바늘에서 x cm 쪽 (바늘은 3 cm 에)
        self.needle = {"W": "box", "G": "box"}
        self.hung = False
        self.yb = 14.0
        self.Sw = 38.0
        self.drop = 0.0
        self.falling = []
        self.puddle = 0
        self.water = False
        self.chip = None
        self.mag = "desk"                # desk | syringe | strips
        self.mx, self.my = -2.8, 1.0
        self.sx, self.sz = 45.0, 3.0      # 센서: 띠 줄자의 z (cm), 띠 중심에서 가로 s (cm)
        self.clamp = False
        self.tilt = 0.7
        self.pow = False
        self.meter = None                # None | holder | sensor
        self.dial = 0


S = State()
_tube_cache = {"key": None, "val": None}


def tube_shape():
    key = (round(S.yb, 4), round(S.Sw, 4))
    if _tube_cache["key"] == key:
        return _tube_cache["val"]
    B = (0.0, S.yb)
    arms = []
    for sg in (-1, 1):
        C = (sg * CLIP_DZ, CLIP_Y)
        s = sag_for(B, C)
        arms.append([arm_at(B, C, s, i / 48.0) for i in range(49)])
    level, wet, acc, P = CLIP_Y, 48.0, 0.0, arms[1]
    for i in range(1, 49):
        d = math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1])
        if acc + d >= S.Sw / 2:
            f = (S.Sw / 2 - acc) / d
            level = P[i - 1][1] + (P[i][1] - P[i - 1][1]) * f
            wet = i - 1 + f
            break
        acc += d
    val = {"arms": arms, "level": level, "wet": wet, "tip": S.yb - 1.4}
    _tube_cache["key"], _tube_cache["val"] = key, val
    return val


def tube_needle():
    for k in ("W", "G"):
        if S.needle[k] == "tube":
            return k
    return None


def step_tube(dt):
    for f in S.falling:
        f[1] += 981 * dt
        f[0] -= f[1] * dt
    n0 = len(S.falling)
    S.falling = [f for f in S.falling if f[0] > 0.15]
    S.puddle += n0 - len(S.falling)
    k = tube_needle()
    if not S.hung or not k or S.Sw <= 0:
        S.drop = 0.0
        return
    sh = tube_shape()
    d = NEEDLE[k]
    h = (sh["level"] - sh["tip"]) / 100
    Vh = 2.0 / 3 * math.pi * (d / 2) ** 3
    R = max(d / 2, (3 * (Vh + S.drop) / (4 * math.pi)) ** (1 / 3.0)) if S.drop > 0 else d / 2
    P = RHO * G * h - 2 * SIGMA / R
    if S.drop > 0 or P > 0:
        S.drop = max(0.0, S.drop + KQ * P * dt)
    if Vh + S.drop >= tate(d):
        S.falling.append([sh["tip"] - 0.1, 0.0])
        S.drop = 0.0
        S.Sw = max(0.0, S.Sw - tate(d) * 1e6 / TUBE_A)


def chip_accel(px):
    am = -G * slope_at((R_IN - px) / 100) + G * slope_at((R_IN + px) / 100)
    if S.mag != "syringe":
        return am
    dx, dy = px - S.mx, -S.my
    r = math.hypot(dx, dy)
    c = (dx * MAGN[0] + dy * MAGN[1]) / r
    return am + abs(CHI_G - CHI_W) * grad_at(r * 10) * max(0.0, c) * dx / r


def step_chip(dt):
    if S.chip is None or not S.water:
        return
    n = int(math.ceil(dt / 0.001))
    h = dt / n
    for _ in range(n):
        v = max(-3.0, min(3.0, 60 * chip_accel(S.chip)))
        S.chip = max(-R_IN + 0.08, min(R_IN - 0.08, S.chip + v * h))


def mag_clamp():
    S.my = max(0.5 * MAG_D * math.sqrt(0.5) - 0.03, min(6.0, S.my))
    S.mx = max(-R_IN + 1.2, min(R_IN - 0.5 * MAG_D * math.sqrt(0.5) - 0.08, S.mx))


def sensor_B():
    if S.mag != "strips" or abs(S.sz) > 6:
        return 0.0
    return gap_field(S.sx) * s_profile(S.sz * 10) * math.cos(0.02 if S.clamp else S.tilt)


def meter_volts():
    if S.meter == "holder":
        return E_BAT
    if S.meter == "sensor":
        return (V0_MV + sensor_B() / 1e-5 * E_BAT / 3 + 0.08 * gauss()) / 1000 if S.pow else 0.00004 * gauss()
    return 0.00003 * gauss()


def meter_reading():
    r = DIAL[S.dial]
    if r == "OFF":
        return ""
    V = meter_volts()

    def fmt(x, full, dec):
        return ("-1" if x < 0 else "1") if abs(x) >= full else "%.*f" % (dec, x)
    if r == "DCV 200m":
        return fmt(V * 1000, 199.95, 1)
    if r == "DCV 2":
        return fmt(V, 1.9995, 3)
    if r == "DCV 20":
        return fmt(V, 19.995, 2)
    if r == "DCV 200":
        return fmt(V, 199.95, 1)
    if r.startswith("DCA"):
        return "1" if S.meter == "holder" else ("0.0" if r == "DCA 200m" else "0.00")
    return "1"


def rise_table():
    out, acc, u = [], 0.0, 6.0
    while u >= -1e-9:
        acc += math.tan(log_interp(FIG7, u)) * 0.01
        out.append((u, acc))
        u -= 0.01
    out.reverse()
    return out


RISE = rise_table()


def rise_at(l_cm):
    u = max(0.0, l_cm / 100 / LC)
    i = min(len(RISE) - 1, int(round(u / 0.01)))
    return RISE[i][1] * LC * 100


def surf_y(px):
    return WATER_Y + rise_at(R_IN - px) + rise_at(R_IN + px)


# ==============================================================================
#  2.  화면
# ==============================================================================
BG, PANEL, PANEL2 = "#1c2027", "#22262d", "#2b2f36"
FG, FG_DIM, ACC = "#e8eef2", "#9aa3ab", "#f2c14e"
FX = 3.0                                   # 바늘의 위치 (책상 위 x, cm)
XS, SCZ_OFF = 3.0, 14.0                    # 스탠드: 바늘과 같은 x, 빛줄기에서 14 cm 옆


def beam_L():
    return (S.mir - FX) + math.hypot(S.mir - XS - 0.45, SCZ_OFF)


class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title(T("GPhO 2019 실험 시뮬레이터 — E1 물질의 자기적 성질", "GPhO 2019 Experiment Simulator — E1 Magnetic properties of matter") + "   v" + APP_VERSION)
        self.geometry("1480x920")
        self.configure(bg=BG)
        self.msg = ("", 0)
        self.disp = ""
        self.last_read = 0
        self.tab = "A"
        self.pK = 40.0                     # 종이 확대 (px/cm)
        self.pO = [0.0, 0.0]
        self.tape_b = 6.0                  # 부분 B: 세운 줄자의 가로 위치 (cm, 관 중심에서)
        self.ruler_c = -5.6                # 부분 C: 자의 0 눈금 위치 (접시 중심에서 cm)
        self.ruler_d = 2.5                 # 부분 D: 가로지른 자가 센서에서 떨어진 거리 (cm)
        self.drag = None
        self._build()
        self._last = time.time()
        self.after(30, self._tick)

    def say(self, m):
        self.msg = (m, time.time())

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x")
        tk.Label(top, text="GPhO 2019  ·  " + T("E1 물질의 자기적 성질 (20점)", "E1 Magnetic properties of matter (20 pts)"), bg=BG, fg=ACC,
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=14, pady=6)
        self.tabs = {}
        for k, t in (("A", T("A 회절", "A diffraction")), ("B", T("B 표면장력", "B surface tension")), ("C", T("C 흑연", "C graphite")), ("D", T("D 강자성 띠", "D ferromagnetic strip"))):
            b = tk.Button(top, text=t, command=lambda k=k: self.set_tab(k), bg=PANEL2, fg=FG, relief="flat", bd=0, padx=12, pady=4, font=("Segoe UI", 10))
            b.pack(side="left", padx=3)
            self.tabs[k] = b
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        self.cap = tk.Label(left, anchor="w", justify="left", bg=BG, fg=FG_DIM, font=("Segoe UI", 9), wraplength=1100)
        self.cap.pack(fill="x")
        self.cv = tk.Canvas(left, bg="#2e3238", highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        right = tk.Frame(body, bg=PANEL, width=310)
        right.pack(side="left", fill="y", padx=(8, 0))
        right.pack_propagate(False)
        self.bs = dict(bg=PANEL2, fg=FG, activebackground="#343941", activeforeground=FG, relief="flat", bd=0, padx=8, pady=5, font=("Segoe UI", 10))

        def H(t):
            tk.Label(right, text=t, bg=PANEL, fg=ACC, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        H(T("조작", "Controls"))
        self.ctl = tk.Frame(right, bg=PANEL)
        self.ctl.pack(fill="x")
        H(T("멀티미터", "Multimeter"))
        self.lcd = tk.Label(right, text="", bg="#b9bfb3", fg="#1b1e1c", font=("Consolas", 26, "bold"), width=8, anchor="e")
        self.lcd.pack(padx=10, pady=2)
        row = tk.Frame(right, bg=PANEL)
        row.pack(fill="x", padx=10)
        tk.Button(row, text="◀", command=lambda: self.turn(-1), **self.bs).pack(side="left")
        self.dl = tk.Label(row, text="", bg=PANEL, fg=FG, font=("Segoe UI", 10, "bold"), width=12)
        self.dl.pack(side="left", expand=True)
        tk.Button(row, text="▶", command=lambda: self.turn(1), **self.bs).pack(side="left")
        H(T("안내", "Notes"))
        tk.Label(right, justify="left", wraplength=288, bg=PANEL, fg=FG_DIM, font=("Segoe UI", 8), text=T(
            "• λ = 532 nm; ρw = 1000 kg/m³, g = 9.81 m/s²; χw = −9.05×10⁻⁹ m³/kg; δ = 0.27 mm.\n• E = 3 V일 때 센서 1 mV가 10 µT이며 읽음은 E에 비례합니다.\n• 그림 7, 8: 문제지를 보세요.\n• 레이저는 주사기에 물려 있습니다: 자석을 주사기에 붙이면 레이저가 빠집니다.",
            "• λ = 532 nm; ρw = 1000 kg/m³, g = 9.81 m/s²; χw = −9.05×10⁻⁹ m³/kg; δ = 0.27 mm.\n• With E = 3 V each mV of the sensor is 10 µT; the reading is proportional to E.\n• Figs. 7 and 8: see the problem sheet.\n• The laser rides on the syringe: tape the magnet to it and the laser comes off.")).pack(anchor="w", padx=10)
        self.status = tk.Label(right, justify="left", wraplength=288, bg="#12161b", fg=ACC, font=("Segoe UI", 9), anchor="nw", padx=8, pady=8)
        self.status.pack(fill="both", expand=True, padx=10, pady=10)
        self.cv.bind("<Button-1>", self.down)
        self.cv.bind("<B1-Motion>", self.move)
        self.cv.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag", None))
        self.cv.bind("<MouseWheel>", self.wheel)
        self.cv.bind("<Button-4>", lambda e: self.wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self.wheel(e, -1))
        self.set_tab("A")

    # ---- controls ---- #
    def set_tab(self, k):
        self.tab = k
        for kk, b in self.tabs.items():
            b.config(bg=ACC if kk == k else PANEL2, fg="#1c2027" if kk == k else FG)
        for w in self.ctl.winfo_children():
            w.destroy()
        self.btns = []

        def B(fn):
            b = tk.Button(self.ctl, command=fn, **self.bs)
            b.pack(fill="x", padx=10, pady=1)
            self.btns.append((b, fn))
            return b
        if k == "A":
            self.b1 = B(self.t_laser)
            self.b2 = B(lambda: self.foam("W"))
            self.b3 = B(lambda: self.foam("G"))
            self.cap.config(text=T("위: 옆에서 본 실험대 — 거울을 끌어 옮기기, 아래 줄자로 거리 읽기 · 아래: 스탠드의 모눈종이 (1 mm 칸) — 휠: 확대, 끌기: 이동",
                                   "top: the bench from the side — drag the mirror, read distances on the tape below · bottom: the stand's graph paper (1 mm squares) — wheel: zoom, drag: pan"))
        elif k == "B":
            self.b1 = B(self.t_hang)
            self.b2 = B(lambda: self.tube_n("W"))
            self.b3 = B(lambda: self.tube_n("G"))
            self.cap.config(text=T("앞에서 본 스탠드와 관 — 관의 가장 낮은 곳을 위아래로 끌기 · 관 위 휠: 물 더하기/빼기 · 세운 줄자: 좌우로 끌기",
                                   "the stand and the tube from the front — drag the tube's lowest point up or down · wheel over the tube: add or draw off water · the upright tape: drag sideways"))
        elif k == "C":
            self.b1 = B(self.t_water)
            self.b2 = B(self.t_chip)
            self.b3 = B(self.t_magC)
            self.cap.config(text=T("옆에서 본 페트리 접시 — 자석 끌기 (45° 유지) · 아래 자: 좌우로 끌기",
                                   "the Petri dish from the side — drag the magnet (it stays at 45°) · the ruler below: drag sideways"))
        else:
            self.b1 = B(self.t_magD)
            self.b2 = B(self.t_clamp)
            self.b3 = B(self.t_pow)
            self.b4 = B(self.t_meter)
            self.cap.config(text=T("위: 위에서 본 띠 — 센서 끌기 · 아래: 센서 둘레 확대 (띠의 줄자 = z, 가로지른 자 = s; 자는 끌어 옮기기)",
                                   "top: the strips from above — drag the sensor · bottom: close-up round the sensor (the strip's tape = z, the ruler across = s; drag the ruler)"))

    def turn(self, d):
        S.dial = (S.dial + d) % len(DIAL)
        self.last_read = 0

    def t_laser(self):
        if S.mag == "syringe":
            self.say(T("주사기가 자석을 들고 있어 레이저가 책상에 놓여 있습니다", "the syringe holds the magnet: the laser lies on the desk"))
            return
        S.laser = not S.laser

    def foam(self, k):
        o = "G" if k == "W" else "W"
        if S.needle[k] == "foam":
            S.needle[k] = "box"
        else:
            if S.needle[o] == "foam":
                S.needle[o] = "box"
            if S.needle[k] == "tube":
                S.drop = 0
            S.needle[k] = "foam"

    def t_hang(self):
        S.hung = not S.hung
        if not S.hung:
            for k in ("W", "G"):
                if S.needle[k] == "tube":
                    S.needle[k] = "box"

    def tube_n(self, k):
        if not S.hung:
            self.say(T("먼저 관을 스탠드에 거세요", "hang the tube on the stand first"))
            return
        o = "G" if k == "W" else "W"
        if S.needle[k] == "tube":
            S.needle[k] = "box"
        else:
            if S.needle[o] == "tube":
                S.needle[o] = "box"
            S.needle[k] = "tube"
        S.drop = 0

    def t_water(self):
        S.water = True

    def t_chip(self):
        if not S.water:
            self.say(T("먼저 접시에 물을 부으세요", "pour water into the dish first"))
            return
        S.chip = 0.6 * (RNG.random() - 0.5)

    def t_magC(self):
        if S.mag == "syringe":
            S.mag = "desk"
        else:
            S.mag, S.mx, S.my, S.laser = "syringe", -2.8, 1.0, False
            mag_clamp()

    def t_magD(self):
        S.mag = "desk" if S.mag == "strips" else "strips"

    def t_clamp(self):
        S.clamp = not S.clamp

    def t_pow(self):
        S.pow = not S.pow

    def t_meter(self):
        S.meter = {None: "holder", "holder": "sensor", "sensor": None}[S.meter]

    # ---- geometry of each view ---- #
    def geo(self):
        W, H = max(600, self.cv.winfo_width()), max(400, self.cv.winfo_height())
        return W, H

    def a_bench(self):
        W, H = self.geo()
        k = (W - 80) / 160.0
        return (lambda x: 40 + (x + 12) * k), 120, k

    def b_map(self):
        W, H = self.geo()
        k = min((H - 40) / 32.0, (W - 300) / 34.0)
        return (lambda z, y: (W / 2 + z * k, H - 20 - y * k)), k

    def c_map(self):
        W, H = self.geo()
        k = min((W - 80) / 11.0, (H - 80) / 7.8)
        return (lambda x, y: (W / 2 + x * k, 40 + (5.2 - y) * k)), k

    def d_map(self):
        W, H = self.geo()
        k = (W - 80) / 68.0
        return (lambda z, s: (40 + (z + 4) * k, 30 + (4 - s) * k)), k

    def d_zoom(self):
        W, H = self.geo()
        k = min((W - 40) / 16.0, (H - 230) / 9.0)
        return (lambda z, s: (W / 2 + (z - S.sx) * k, 220 + (H - 230) / 2 - s * k)), k

    # ---- mouse ---- #
    def down(self, e):
        self.drag = None
        if self.tab == "A":
            X, yb, k = self.a_bench()
            if abs(e.x - X(S.mir)) < 14 and abs(e.y - yb) < 50:
                self.drag = ("mir",)
            elif e.y > 220:
                self.drag = ("pan", e.x, e.y, self.pO[0], self.pO[1])
        elif self.tab == "B":
            P, k = self.b_map()
            sh = tube_shape()
            if S.hung and math.hypot(e.x - P(0, sh["tip"] + 1)[0], e.y - P(0, sh["tip"] + 1)[1]) < 30:
                self.drag = ("yb",)
            elif abs(e.x - P(self.tape_b, 0)[0]) < 22:
                self.drag = ("tapeB", e.x, self.tape_b)
        elif self.tab == "C":
            P, k = self.c_map()
            if S.mag == "syringe":
                c = P(S.mx - 0.3, S.my + 0.3)
                if math.hypot(e.x - c[0], e.y - c[1]) < 0.9 * k:
                    self.drag = ("mag", e.x, e.y, S.mx, S.my)
                    return
            if e.y > P(0, 0)[1] + 20:
                self.drag = ("rulerC", e.x, self.ruler_c)
        else:
            P, k = self.d_map()
            Z, kz = self.d_zoom()
            c = P(S.sx, S.sz)
            if math.hypot(e.x - c[0], e.y - c[1]) < 14:
                self.drag = ("sens", e.x, e.y, S.sx, S.sz, k)
                if not S.clamp:
                    S.tilt = 0.5 + 0.6 * RNG.random()
            elif e.y > 220:
                c2 = Z(S.sx, S.sz)
                if math.hypot(e.x - c2[0], e.y - c2[1]) < 0.4 * kz:
                    self.drag = ("sens", e.x, e.y, S.sx, S.sz, kz)
                    if not S.clamp:
                        S.tilt = 0.5 + 0.6 * RNG.random()
                else:
                    self.drag = ("rulerD", e.x, self.ruler_d, kz)

    def move(self, e):
        d = self.drag
        if not d:
            return
        if d[0] == "mir":
            X, yb, k = self.a_bench()
            S.mir = max(70.0, min(146.0, (e.x - 40) / k - 12))
        elif d[0] == "pan":
            self.pO = [d[3] + e.x - d[1], d[4] + e.y - d[2]]
        elif d[0] == "yb":
            P, k = self.b_map()
            W, H = self.geo()
            S.yb = max(YB_MIN, min(YB_MAX, (H - 20 - e.y) / k + 0.4))
        elif d[0] == "tapeB":
            P, k = self.b_map()
            self.tape_b = d[2] + (e.x - d[1]) / k
        elif d[0] == "mag":
            P, k = self.c_map()
            S.mx, S.my = d[3] + (e.x - d[1]) / k, d[4] - (e.y - d[2]) / k
            mag_clamp()
        elif d[0] == "rulerC":
            P, k = self.c_map()
            self.ruler_c = d[2] + (e.x - d[1]) / k
        elif d[0] == "sens":
            S.sx = max(-6.0, min(66.0, d[3] + (e.x - d[1]) / d[5]))
            S.sz = max(-6.0, min(6.0, d[4] - (e.y - d[2]) / d[5]))
        elif d[0] == "rulerD":
            self.ruler_d = d[2] + (e.x - d[1]) / d[3]

    def wheel(self, e, d=None):
        if d is None:
            d = 1 if e.delta > 0 else -1
        if self.tab == "A" and e.y > 220:
            f = 1.15 if d > 0 else 1 / 1.15
            self.pK = max(15.0, min(160.0, self.pK * f))
        elif self.tab == "B" and S.hung:
            S.Sw = max(0.0, min(2 * TUBE_HALF - 6, S.Sw + 0.5 * d))

    # ---- drawing ---- #
    def draw_A(self):
        c = self.cv
        W, H = self.geo()
        X, yb, k = self.a_bench()
        # 종이
        K = self.pK
        x0, y0 = W / 2 - 9 * K + self.pO[0], 230 + (H - 230) / 2 - 6 * K + self.pO[1]
        c.create_rectangle(x0, y0, x0 + 18 * K, y0 + 12 * K, fill="#fbf8f4", outline="#9aa3ab")
        step = 1 if K >= 30 else 5
        for i in range(0, 181, step):
            col = "#d9708c" if i % 10 == 0 else "#e7a0b3" if i % 5 == 0 else "#f2c9d4"
            c.create_line(x0 + i * K / 10, y0, x0 + i * K / 10, y0 + 12 * K, fill=col)
        for i in range(0, 121, step):
            col = "#d9708c" if i % 10 == 0 else "#e7a0b3" if i % 5 == 0 else "#f2c9d4"
            c.create_line(x0, y0 + i * K / 10, x0 + 18 * K, y0 + i * K / 10, fill=col)
        if S.laser and S.mag != "syringe":
            nk = "W" if S.needle["W"] == "foam" else "G" if S.needle["G"] == "foam" else None
            L = beam_L() / 100.0
            cy = y0 + 7.5 * K
            px = max(int(x0), 0)
            while px < min(x0 + 18 * K, W):
                w = (px - (x0 + 9 * K)) / K
                spot = math.exp(-(w / 0.13) ** 2)
                I = 0.0
                if nk:
                    a = math.pi * NEEDLE[nk] * (w / 100.0 / L) / LAM
                    I = 1.0 if a == 0 else (math.sin(a) / a) ** 2
                v = min(1.0, (8 * spot + 300 * I) ** 0.45)
                if v > 0.04:
                    wh = max(0.0, v - 0.85) * 4
                    col = "#%02x%02x%02x" % (int(251 * (1 - v) + (60 + 190 * wh) * v), int(248 * (1 - v) + 255 * v), int(244 * (1 - v) + (90 + 160 * wh) * v))
                    h = max(1.0, 0.11 * K)
                    c.create_line(px, cy - h, px, cy + h, fill=col)
                px += 1
        c.create_rectangle(0, 0, W, 222, fill="#2e3238", outline="")
        c.create_rectangle(0, yb + 30, W, yb + 34, fill="#3a3d42", outline="")
        if S.mag != "syringe":
            c.create_rectangle(X(-9.8), yb - 70, X(-8.2), yb + 30, fill="#dfe6ea", outline="#9aa3ab")
            c.create_rectangle(X(-16), yb - 6, X(-3), yb + 6, fill="#1d1f22")
            c.create_rectangle(X(-11.8), yb - 7, X(-10.4), yb + 7, fill="#e9c21b")
        else:
            c.create_rectangle(X(-16), yb + 18, X(-3), yb + 30, fill="#1d1f22")
        c.create_rectangle(X(FX) - 7, yb + 2, X(FX) + 7, yb + 30, fill="#5fc0dc", outline="")
        for kk in ("W", "G"):
            if S.needle[kk] == "foam":
                c.create_line(X(FX), yb + 4, X(FX), yb - 30, fill="#c6ccd2", width=2)
                c.create_rectangle(X(FX) - 3, yb - 38, X(FX) + 3, yb - 30, fill=NCOL[kk])
        c.create_rectangle(X(S.mir), yb - 60, X(S.mir) + 4, yb + 30, fill="#c9d4da", outline="#7e2a8c")
        c.create_polygon(X(S.mir) + 4, yb - 60, X(S.mir) + 30, yb + 30, X(S.mir) + 4, yb + 30, fill="#7e2a8c")
        c.create_rectangle(X(XS) - 2, yb - 150, X(XS) + 2, yb + 30, fill="#a9c3cf", outline="")
        if S.laser and S.mag != "syringe":
            c.create_line(X(-3), yb, X(S.mir), yb, fill="#5aff78")
            c.create_line(X(S.mir), yb - 1, X(XS) + 2, yb - 3, fill="#5aff78", dash=(4, 3))
        for cm in range(-10, 151):
            x = X(cm)
            ln = 12 if cm % 10 == 0 else 8 if cm % 5 == 0 else 4
            c.create_line(x, yb + 34, x, yb + 34 + ln, fill="#f3cd2f")
            if cm % 10 == 0:
                c.create_text(x + 2, yb + 52, text=str(cm), anchor="w", fill="#f3cd2f", font=("Arial", 8, "bold"))
        c.create_text(X(-9), yb - 80, text=T("레이저 / 주사기", "laser / syringe"), fill=FG_DIM, font=("Segoe UI", 8))
        c.create_text(X(FX) + 30, yb - 46, text=T("바늘 (스펀지)", "needle (foam)"), fill=FG_DIM, font=("Segoe UI", 8))
        c.create_text(X(S.mir), yb - 74, text=T("거울", "mirror"), fill=FG_DIM, font=("Segoe UI", 8))
        c.create_text(X(XS) + 4, yb - 160, text=T("스탠드 (스크린, 빛줄기에서 14 cm 옆)", "stand (screen, 14 cm beside the beam)"), anchor="w", fill=FG_DIM, font=("Segoe UI", 8))

    def draw_B(self):
        c = self.cv
        W, H = self.geo()
        P, k = self.b_map()
        x0, y0 = P(-12, 0)
        x1, y1 = P(12, 30)
        c.create_rectangle(x0, y1, x1, y0, fill="#3b4750", outline="#9fb6c2")
        p0, p1 = P(-9, 13), P(9, 1)
        c.create_rectangle(p0[0], p0[1], p1[0], p1[1], fill="#f6e4e9", outline="")
        c.create_line(0, y0, W, y0, fill="#55595f", width=3)
        if S.hung:
            sh = tube_shape()
            for arm in sh["arms"]:
                pts = [P(p[0], p[1]) for p in arm]
                wet = sh["wet"]
                iw = int(wet)
                dry = pts[iw:]
                wetp = pts[:iw + 1]
                if len(wetp) > 1:
                    c.create_line(*[v for p in wetp for v in p], fill="#5f93c8", width=max(3, 0.6 * k), capstyle="round")
                if len(dry) > 1:
                    c.create_line(*[v for p in dry for v in p], fill="#cfd6dc", width=max(3, 0.6 * k), capstyle="round")
                cl = pts[-1]
                c.create_rectangle(cl[0] - 10, cl[1] - 6, cl[0] + 10, cl[1] + 6, fill="#c42f76", outline="")
            nk = tube_needle()
            if nk:
                a, b = P(0, sh["tip"]), P(0, S.yb + 0.15)
                c.create_line(a[0], a[1], b[0], b[1], fill="#c6ccd2", width=2)
                q0, q1 = P(-0.12, S.yb - 0.3), P(0.12, S.yb - 0.62)
                c.create_rectangle(q0[0], q0[1], q1[0], q1[1], fill=NCOL[nk], outline="")
                d = NEEDLE[nk]
                if S.drop > 0:
                    R = (3 * (2.0 / 3 * math.pi * (d / 2) ** 3 + S.drop) / (4 * math.pi)) ** (1 / 3.0) * 100 * k
                    c.create_oval(a[0] - R, a[1], a[0] + R, a[1] + 2 * R, fill="#a9cdf0", outline="")
            for f in S.falling:
                p = P(0, f[0])
                c.create_oval(p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3, fill="#a9cdf0", outline="")
            if S.puddle:
                r = min(2.2, 0.25 + 0.15 * math.sqrt(S.puddle)) * k
                c.create_oval(P(0, 0)[0] - r, y0 - 3, P(0, 0)[0] + r, y0 + 3, fill="#7896b4", outline="")
        else:
            c.create_text(W / 2, H / 2, text=T("관이 책상 위에 있습니다 — '관을 스탠드에 걸기'", "the tube lies on the desk — 'hang the tube'"), fill=FG_DIM, font=("Segoe UI", 11))
        # 세운 줄자
        tx = P(self.tape_b, 0)[0]
        top = P(0, 31)[1]
        c.create_rectangle(tx, top, tx + 1.3 * k, y0, fill="#f3cd2f", outline="#a8891c")
        for mm in range(0, 311):
            y = P(0, mm / 10.0)[1]
            ln = 0.45 if mm % 10 == 0 else 0.3 if mm % 5 == 0 else 0.18
            c.create_line(tx, y, tx + ln * 1.3 * k, y, fill="#151515")
            if mm % 10 == 0:
                c.create_text(tx + 1.25 * k, y, text=str(mm // 10), anchor="e", fill="#c4161c" if mm % 100 == 0 else "#151515", font=("Arial", 8, "bold"))

    def draw_C(self):
        c = self.cv
        W, H = self.geo()
        P, k = self.c_map()
        a, b = P(-4.6, 0 - WATER_Y), P(4.6, DISH_H - WATER_Y)
        c.create_rectangle(a[0], b[1], b[0], a[1], fill="#2f363d", outline="#c8dde6", width=2)
        if S.water:
            pts = [P(-R_IN, -WATER_Y + 0.12)]
            for i in range(-80, 81):
                px = i / 80.0 * (R_IN - 0.005)
                pts.append(P(px, surf_y(px) - WATER_Y))
            pts.append(P(R_IN, -WATER_Y + 0.12))
            c.create_polygon(*[v for p in pts for v in p], fill="#4d7ea8", outline="#8cc0e8")
        if S.chip is not None and S.water:
            p = P(S.chip, surf_y(S.chip) - WATER_Y)
            c.create_rectangle(p[0] - 0.07 * k, p[1] - 0.03 * k, p[0] + 0.07 * k, p[1] + 0.02 * k, fill="#1e2023", outline="#5a5e64")
        if S.mag == "syringe":
            n = (-MAGN[0], -MAGN[1])
            u = (-n[1], n[0])
            r = MAG_D / 2

            def Q(t, s):
                return P(S.mx + n[0] * t + u[0] * s, S.my + n[1] * t + u[1] * s)
            body = [Q(0, -r), Q(0, r), Q(GAP, r), Q(GAP, -r)]
            c.create_polygon(*[v for p in body for v in p], fill="#9ea4aa", outline="#dfe4e8")
            syr = [Q(GAP + 0.3, -0.75), Q(GAP + 0.3, 0.75), Q(GAP + 10, 0.75), Q(GAP + 10, -0.75)]
            c.create_polygon(*[v for p in syr for v in p], fill="#c9d3da", outline="#9aa3ab")
            c.create_line(*Q(GAP, 0), *Q(GAP + 0.3, 0), fill="#d9e1e7", width=4)
        # 자
        y = P(0, -WATER_Y)[1] + 0.3 * k
        x0 = P(self.ruler_c, 0)[0]
        c.create_rectangle(x0 - 0.5 * k, y, x0 + 10.5 * k, y + 1.4 * k, fill="#f4f5f1", outline="#9aa3ab")
        for mm in range(0, 101):
            x = x0 + mm * k / 10
            ln = 0.42 if mm % 10 == 0 else 0.3 if mm % 5 == 0 else 0.18
            c.create_line(x, y, x, y + ln * k, fill="#1a1a1a")
            if mm % 10 == 0:
                c.create_text(x, y + 0.75 * k, text=str(mm // 10), fill="#1a1a1a", font=("Arial", 9, "bold"))

    def draw_D(self):
        c = self.cv
        W, H = self.geo()
        P, k = self.d_map()
        a, b = P(0, 1.5), P(60, -1.5)
        c.create_rectangle(a[0], a[1], b[0], b[1], fill="#a3aab1", outline="")
        if S.mag == "strips":
            m = P(59.2, 0)
            c.create_oval(m[0] - 0.5 * k, m[1] - 0.5 * k, m[0] + 0.5 * k, m[1] + 0.5 * k, fill="#9ea4aa")
            a2, b2 = P(0, 1.0), P(60, -1.0)
            c.create_rectangle(a2[0], a2[1], b2[0], b2[1], fill="#c9cdd1", outline="#8a9096")
        else:
            a2, b2 = P(0, 8.0), P(60, 5.0)
            c.create_rectangle(a2[0], a2[1], b2[0], b2[1], fill="#a3aab1", outline="")
        for cm in range(0, 61, 5):
            p = P(cm, 1.0 if S.mag == "strips" else 8.0)
            c.create_text(p[0], p[1] - 6, text=str(cm), fill=FG_DIM, font=("Arial", 7))
        s = P(S.sx, S.sz)
        c.create_rectangle(s[0] - 3, s[1] - 3, s[0] + 3, s[1] + 3, fill="#18191b", outline=ACC)
        c.create_line(s[0], s[1], s[0], s[1] + 60, fill="#2b62c4")
        # 확대
        Z, kz = self.d_zoom()
        y0 = 220
        c.create_rectangle(0, y0, W, H, fill="#33373d", outline="")
        if S.mag == "strips":
            a, b = Z(S.sx - 20, 1.5), Z(S.sx + 20, -1.5)
            c.create_rectangle(max(a[0], Z(0, 0)[0]), a[1], min(b[0], Z(60, 0)[0]), b[1], fill="#a3aab1", outline="")
            a, b = Z(S.sx - 20, 1.0), Z(S.sx + 20, -1.0)
            c.create_rectangle(max(a[0], Z(0, 0)[0]), a[1], min(b[0], Z(60, 0)[0]), b[1], fill="#c9cdd1", outline="")
            ty0, ty1 = Z(0, 0.6)[1], Z(0, -0.6)[1]
            c.create_rectangle(max(0, Z(0, 0)[0]), ty0, min(W, Z(61, 0)[0]), ty1, fill="#f6f2df", outline="")
            for mm in range(max(0, int((S.sx - 9) * 10)), min(610, int((S.sx + 9) * 10)) + 1):
                x = Z(mm / 10.0, 0)[0]
                ln = 0.45 if mm % 10 == 0 else 0.3 if mm % 5 == 0 else 0.18
                c.create_line(x, ty0, x, ty0 + ln * 1.2 * kz, fill="#151515")
                if mm % 10 == 0:
                    c.create_text(x + 3, ty1 - 3, text=str(mm // 10), anchor="sw", fill="#151515", font=("Arial", 9, "bold"))
        # 가로지른 자
        rx = Z(S.sx + self.ruler_d, 0)[0]
        c.create_rectangle(rx, Z(0, 4.2)[1], rx + 2.6 * kz, Z(0, -4.2)[1], fill="#f4f5f1", outline="#9aa3ab")
        for mm in range(-40, 41):
            y = Z(0, mm / 10.0)[1]
            ln = 0.42 if mm % 10 == 0 else 0.3 if mm % 5 == 0 else 0.18
            c.create_line(rx, y, rx + ln * 2.6 * kz, y, fill="#1a1a1a")
            if mm % 10 == 0:
                c.create_text(rx + 1.4 * kz, y, text=str(mm // 10 + 4), fill="#1a1a1a", font=("Arial", 9, "bold"))
        s = Z(S.sx, S.sz)
        c.create_rectangle(s[0] - 0.2 * kz, s[1] - 0.15 * kz, s[0] + 0.2 * kz, s[1] + 0.25 * kz, fill="#18191b", outline=ACC)
        for i, col in enumerate(("#2b62c4", "#1d1d1f", "#c8262b", "#eeeeea")):
            c.create_line(s[0] + (i - 1.5) * 3, s[1] + 0.25 * kz, s[0] + (i - 1.5) * 3, H, fill=col, width=2)
        if S.clamp:
            c.create_rectangle(s[0] - 0.35 * kz, s[1] + 1.6 * kz, s[0] + 0.35 * kz, s[1] + 2.3 * kz, fill="#e6e9eb", outline="")

    def _tick(self):
        now = time.time()
        dt = min(0.05, now - self._last)
        self._last = now
        step_tube(dt)
        step_chip(dt)
        if now - self.last_read > 0.333:
            self.last_read = now
            self.disp = meter_reading()
        try:
            self.cv.delete("all")
            {"A": self.draw_A, "B": self.draw_B, "C": self.draw_C, "D": self.draw_D}[self.tab]()
        except tk.TclError:
            return
        self.lcd.config(text=self.disp)
        self.dl.config(text=DIAL[S.dial])
        if self.tab == "A":
            self.b1.config(text=T("레이저: 고정구로 버튼 누름", "Laser: button held by the fixator") if S.laser and S.mag != "syringe" else T("레이저: 꺼짐", "Laser: off"))
            self.b2.config(text=T("흰 바늘: 스펀지에 꽂힘", "white needle: in the foam") if S.needle["W"] == "foam" else T("흰 바늘을 스펀지에 꽂기", "Stand the white needle in the foam"))
            self.b3.config(text=T("초록 바늘: 스펀지에 꽂힘", "green needle: in the foam") if S.needle["G"] == "foam" else T("초록 바늘을 스펀지에 꽂기", "Stand the green needle in the foam"))
        elif self.tab == "B":
            self.b1.config(text=T("관: 스탠드에 걸림", "Tube: hung on the stand") if S.hung else T("관을 스탠드에 걸기", "Hang the tube on the stand"))
            self.b2.config(text=T("흰 바늘: 관에 꽂힘", "white needle: in the tube") if S.needle["W"] == "tube" else T("흰 바늘을 관에 꽂기", "Puncture the tube with the white needle"))
            self.b3.config(text=T("초록 바늘: 관에 꽂힘", "green needle: in the tube") if S.needle["G"] == "tube" else T("초록 바늘을 관에 꽂기", "Puncture the tube with the green needle"))
        elif self.tab == "C":
            self.b1.config(text=T("접시에 물: 있음", "Water in the dish") if S.water else T("접시에 물 붓기 (절반 높이)", "Pour water into the dish (half)"))
            self.b2.config(text=T("흑연 조각 새로 띄우기", "Float a new graphite chip"))
            self.b3.config(text=T("자석: 주사기에 붙임 (클릭: 떼기)", "Magnet: on the syringe (click: take off)") if S.mag == "syringe" else T("자석을 주사기에 45°로 붙이기", "Tape the magnet to the syringe at 45°"))
        else:
            self.b1.config(text=T("자석·간격재: 띠 사이 (클릭: 빼기)", "Magnet and spacer: between the strips") if S.mag == "strips" else T("자석·간격재를 띠 사이에 넣기", "Put the magnet and spacer between the strips"))
            self.b2.config(text=T("센서 클램프: 끼움", "Sensor clamp: on") if S.clamp else T("센서 클램프: 빼 놓음", "Sensor clamp: off"))
            self.b3.config(text=T("센서 파랑·검정 선: 건전지에", "Sensor blue/black: on the batteries") if S.pow else T("센서 전원 없음", "Sensor unpowered"))
            self.b4.config(text={None: T("멀티미터 리드: 연결 안 됨", "Meter leads: free"), "holder": T("멀티미터 리드: 건전지 홀더 출력", "Meter leads: battery holder output"),
                                 "sensor": T("멀티미터 리드: 센서 빨강·흰 선", "Meter leads: sensor red/white")}[S.meter])
        w = []
        if self.msg[0] and now - self.msg[1] < 5:
            w.append(self.msg[0])
        self.status.config(text="\n\n".join(w))
        self.after(30, self._tick)


if __name__ == "__main__":
    App().mainloop()
