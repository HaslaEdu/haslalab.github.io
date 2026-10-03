#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPhO 2025 (France) Experimental Problem Q1
"Earth's magnetic field measurement"

Virtual laboratory.

The apparatus delivers nothing but what the real one delivers: the two lines
of the Arduino LCD, the multimeter display, the millimetre scale of the sensor
board, the 40 cm ruler, the two protractors and the chronometer.  Nothing is
computed for the user: no alpha, no m_m, no C_f, no B_e, no fit, no graph, no
score.  The plots of A.2-A.5, B.2, B.5 and B.6 are the user's work on paper.

Run:  python ipho2025_E1_sim_KO.py   (EN edition: ipho2025_E1_sim_EN.py)
Needs numpy and matplotlib (pip install numpy matplotlib).

────────────────────────────────────────────────────────────────────────
HOW THE REAL EXPERIMENT RUNS  (problem sheet)

 PART A
  A.1  9 V / 300 mA.h battery, coils drawing ~2 A  ->  tau ~ 9 min.
       The coil battery really runs down here: watch the ammeter fall.
  A.2  field sensor (d) inside the coils (e), i0 = 1.0 A, read B versus the
       position z on the board scale; find where the field stops being linear.
  A.3  two positions z1, z2 in the linear zone, sweep the current, read B.
  A.4  swap to the force sensor (b), coils turned so that the transducer is
       vertical; read the gram-force versus current.
       The sensor is zeroed every time it is switched on, and it breaks
       above 200 g.
  A.5  third magnet stuck at the zero of the 40 cm ruler, field sensor slid
       along the axis.  Near field: not a dipole.  Far field: the display
       quantisation (0.01 mT) takes over.

 PART B
  B.1-B.2  pod hanging on a wire of length L, magnet inside; put sticky paste
       of mass m_a at both ends of the inertia bar at a radius r_a, displace
       the pod and time several oscillations with the chronometer.
  B.3  same without the magnet (the wire alone drives the pod, T ~ 4 s).
  B.5-B.6  turn the upper piece (f2a) to impose theta_0 - the wire takes
       several turns - damp the pod by hand and read theta_eq on the lower
       protractor with the toothpick.  Repeat for other wire lengths.

────────────────────────────────────────────────────────────────────────
PHYSICAL MODEL

  coils      B(z) = C [ f(z-z1) - f(z-z2) ],  f(u) = (u^2+a^2)^(-3/2),
             C = mu0 N a^2 i/2, a = 15 mm, z2-z1 = 30 mm, N = 50.6
             -> dB/dz = -alpha i at the centre, alpha = 0.150 T/m/A,
                +-2.0 mT plateau at 1.0 A, linear between 15 and 32 mm
  Gouy       F = m_m dB/dz = m_m alpha i          (eq. 1, 2)
  magnet     axial field of a uniformly magnetised cylinder
             (R = 5 mm, L = 10 mm), which tends to mu0 m/(2 pi r^3)   (eq. 3)
  pod        J th'' = -(C_f/L)(th - th0) - m_m B_e sin(th - th_e) - c th'
                                                                     (eq. 4)

CALIBRATION against the official Marking Scheme & Solution
  built-in truth   alpha = 0.150 T/m/A,  m_m = 0.335 A.m2,
                   B_e = 47 uT,  C_f = 5.1e-7 N.m2/rad,
                   J_pod = 6.7e-7 kg.m2,  r_a = 40 mm
  a correct measurement then returns
      linear zone  [15 ; 32] mm            (A.2  accepts 12-18 / 29-35 mm)
      alpha        0.150 +- 0.004 T/m/A    (A.3  accepts 0.13 - 0.17)
      m_m          0.33  +- 0.01  A.m2     (A.4, A.5, A.6)
      T1           4.2 s at L = 34 cm, no magnet, no paste     (B.3)
      T2           15.4 s with 2.6 g of paste at r_a = 4 cm    (B.3)
      C_f          5.1e-7 N.m2/rad         (B.3  accepts 3 - 8 e-7)
      B_e          45 - 52 uT              (B.2, B.5, B.6 accept 15 - 70 uT)

ERROR MODEL (re-drawn at every new kit)
  m_m +-3 %, B_e +-3 %, C_f +-3 %, J +-3 %, Hall zero +-0.004 mT,
  Hall noise 0.003 mT, display step 0.01 mT, force zero +-0.15 g,
  force noise 0.12 g, display step 0.1 g, sensor placement +-0.4 mm,
  ruler placement +-0.5 mm, protractor reading +-0.5 deg,
  chronometer reaction +-0.12 s
────────────────────────────────────────────────────────────────────────
"""

import math
import time
import tkinter as tk
from tkinter import ttk, filedialog

import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Circle, Wedge, Polygon
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


LANG = "KO"          # the EN edition differs only in this line
TR = {
    'Arduino  (c)': '아두이노  (c)',
    'field sensor (d)': '자기장 센서 (d)',
    'force sensor (b)': '힘 센서 (b)',
    'switch the force sensor on  (it zeroes itself)': '힘 센서 켜기  (켜질 때 0으로 맞춰짐)',
    'Multimeter  (g)   10 A range': '멀티미터  (g)   10 A 범위',
    'OFF': 'OFF',
    '10 A': '10 A',
    'Coil supply': '코일 전원',
    'close the switch (vi)': '스위치 (vi) 닫기',
    'current knob (vii)': '전류 손잡이 (vii)',
    'replace the 9 V battery with a spare': '9 V 전지를 여분으로 바꾸기',
    'Note book': '기록장',
    'write down': '적기',
    'erase': '지우기',
    'new page': '새 쪽',
    'export the page as CSV': '이 쪽을 CSV로 내보내기',
    'Drag the sensor board along the coil axis and read its position on the board scale (1 mm divisions).  For the Gouy balance the coils are turned so that the transducer is vertical (Fig. 2 iii-iv).': '센서 기판을 코일 축을 따라 끌고, 기판의 눈금(1 mm)으로 위치를 읽으세요.  구이 저울에서는 변환기가 수직이 되도록 코일을 돌려 세웁니다 (그림 2 iii-iv).',
    'anti-Helmholtz coils (e), sensor sliding on the axis (Fig. 2 i)': '앤티-헬름홀츠 코일 (e), 축을 따라 미끄러지는 센서 (그림 2 i)',
    'position of the sensor on the coil axis (mm)': '코일 축 위 센서의 위치 (mm)',
    'coil': '코일',
    'field sensor board (d)': '자기장 센서 기판 (d)',
    'coils turned so that the transducer is vertical (Fig. 2 iii-iv)': '변환기가 수직이 되도록 세운 코일 (그림 2 iii-iv)',
    'F': 'F',
    'coil\nsupply': '코일\n전원',
    '3D view': '3D 보기',
    'no spare battery left': '여분 전지가 없습니다',
    'spare batteries: %d': '여분 전지: %d',
    'The third magnet is stuck at the zero of the 40 cm ruler (i).  Drag the field sensor along the revolution axis and read its position on the ruler.': '세 번째 자석이 40 cm 자 (i)의 0 눈금에 붙어 있습니다.  자기장 센서를 회전축을 따라 끌고, 자에서 위치를 읽으세요.',
    'Pod (f3) and wire': '포드 (f3)와 철사',
    'wire length L (cm)': '철사 길이 L (cm)',
    'set': '설정',
    'magnet (a) inserted in the pod': '포드에 자석 (a) 넣음',
    'sticky paste at both ends  m_a (g per side)': '양 끝의 접착 반죽  m_a (한쪽당 g)',
    'radius of the paste  r_a (cm)': '반죽의 반지름  r_a (cm)',
    'Upper piece (f2a)   theta_0': '윗부품 (f2a)   theta_0',
    'damp the pod by hand until it rests': '포드를 손으로 잡아 멈추기',
    'Oscillation': '진동',
    'displace by': '돌리는 각',
    'release': '놓기',
    'speed ': '배속 ',
    'Chronometer (k)': '스톱워치 (k)',
    'Start': '시작',
    'Lap': '랩',
    'Reset': '리셋',
    'Stop': '정지',
    'Read theta_eq with the toothpick on the lower protractor (f1a), 1 deg divisions.  Turning the upper piece twists the wire by several turns while the pod only moves by a fraction of one.': '아래 각도기 (f1a)에서 이쑤시개로 theta_eq 를 읽으세요 (1° 눈금).  윗부품을 돌리면 철사가 여러 바퀴 꼬이지만 포드는 한 바퀴의 일부만 움직입니다.',
    'm_a = %.2f g per side (total %.2f g)': 'm_a = 한쪽 %.2f g (모두 %.2f g)',
    'theta_0 = %+.0f deg  (%.2f turns)': 'theta_0 = %+.0f°  (%.2f 바퀴)',
    'stand (f) - front view': '스탠드 (f) - 앞모습',
    'f2a  (turn to set theta_0)': 'f2a  (돌려서 theta_0 맞추기)',
    'lower protractor (f1a) seen from above': '위에서 본 아래 각도기 (f1a)',
    'pod (f3)\nwith the\ninertia bar\nand the\ntoothpick': '포드 (f3)\n관성 막대와\n이쑤시개',
    "IPhO 2025 Q1 - Earth's magnetic field measurement (virtual laboratory)": 'IPhO 2025 Q1 - 지구 자기장 측정 (가상 실험실)',
    '  Part A - coils (A.1 - A.4)  ': '  Part A - 코일 (A.1 - A.4)  ',
    '  Part A - free magnet (A.5)  ': '  Part A - 자유 자석 (A.5)  ',
    '  Part B - pod on the stand  ': '  Part B - 스탠드의 포드  ',
    '40 cm ruler (i), magnet (a) stuck at its zero, field sensor (d) on the axis': '40 cm 자 (i), 0 눈금에 붙인 자석 (a), 축 위의 자기장 센서 (d)',
    '-1 turn': '-1 바퀴',
    '+1 turn': '+1 바퀴',
    'magnet at 0': '0 눈금의 자석',
    'close-up: read the position of the sensor on the millimetre scale': '확대: 밀리미터 눈금에서 센서 위치 읽기',
    'its magnet, at the centre of the device': '센서의 자석, 장치 한가운데',
    'sticky paste, m_a each': '접착 반죽, 각각 m_a',
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
        import matplotlib
        matplotlib.rcParams["font.family"] = [fam, "DejaVu Sans"]
        matplotlib.rcParams["axes.unicode_minus"] = False
    except Exception:
        pass

MU0 = 4.0e-7 * math.pi
G0 = 9.81

# ───────────────────────── apparatus ─────────────────────────
COIL_A = 0.015          # m, coil radius
COIL_S = 0.030          # m, coil separation
COIL_N = 50.64          # turns
Z0_COIL = 0.023         # m, centre of the device on the board scale
BOARD_LEN = 0.060       # m, useful travel of the sensor board

MAG_R = 0.005           # m, magnet radius
MAG_L = 0.010           # m, magnet length
RULER_LEN = 0.400       # m, 40 cm ruler

R_A_DEFAULT = 0.040     # m, radius of the inertia bar
BATT_FULL = 0.300 * 3600.0      # A.s, 9 V / 300 mA.h
FORCE_MAX = 200.0       # gram-force, destructive limit
HALL_STEP = 1e-5        # T, 0.01 mT display step
FORCE_STEP = 0.1        # gram-force display step
MULTIMETER_SLEEP = 900.0        # s of inactivity before it switches off


class Bench:
    """One kit.  Every imperfection is drawn once, at the start."""

    def __init__(self, seed=None):
        rng = np.random.default_rng(seed)
        self.rng = rng

        self.N = COIL_N * (1 + rng.normal(0, 0.015))
        self.z1 = Z0_COIL - COIL_S / 2
        self.z2 = Z0_COIL + COIL_S / 2

        self.m_m = float(rng.normal(0.335, 0.010))
        self.Br = self.m_m * MU0 / (math.pi * MAG_R ** 2 * MAG_L)
        self.face = float(rng.normal(0.002, 0.001))     # ruler zero -> pole face

        self.B_e = float(rng.normal(47.0e-6, 1.5e-6))
        self.C_f = float(rng.normal(5.1e-7, 0.15e-7))
        self.J_pod = float(rng.normal(6.70e-7, 0.20e-7))
        self.J_mag = float(rng.normal(1.30e-7, 0.10e-7))

        self.hall_off = float(rng.normal(0.0, 4.0e-6))
        self.hall_noise = 3.0e-6
        self.force_off = float(rng.normal(0.0, 0.15))
        self.force_noise = 0.12
        self.force_broken = False

        self.pos_sigma = 4.0e-4        # m, sensor placement in the coils
        self.dist_sigma = 5.0e-4       # m, sensor placement on the ruler

        self.batt = BATT_FULL
        self.spares = 2

        self.theta = 0.0               # rad, pod angle
        self.omega = 0.0

    # ---------------- fields ----------------
    def _f(self, u):
        return 1.0 / (u * u + COIL_A * COIL_A) ** 1.5

    def B_coils(self, z, i):
        C = MU0 * self.N * COIL_A ** 2 / 2.0 * i
        return C * (self._f(z - self.z1) - self._f(z - self.z2))

    def alpha(self):
        C = MU0 * self.N * COIL_A ** 2 / 2.0
        return 3.0 * C * COIL_S / (((COIL_S / 2) ** 2 + COIL_A ** 2) ** 2.5)

    def B_magnet(self, d):
        d = max(d, 1e-4)
        return (self.Br / 2.0) * (
            (d + MAG_L) / math.sqrt((d + MAG_L) ** 2 + MAG_R ** 2)
            - d / math.sqrt(d * d + MAG_R * MAG_R))

    # ---------------- battery / current ----------------
    def max_current(self):
        f = self.batt / BATT_FULL
        if f <= 0:
            return 0.0
        return 2.50 if f > 0.15 else 2.50 * f / 0.15

    def drain(self, i, dt):
        if i > 0:
            self.batt = max(0.0, self.batt - i * dt)

    def swap_battery(self):
        if self.spares <= 0:
            return False
        self.spares -= 1
        self.batt = BATT_FULL
        return True

    # ---------------- readings ----------------
    def read_hall(self, B):
        v = B + self.hall_off + self.rng.normal(0, self.hall_noise)
        v = max(-0.19999, min(0.19999, v))
        return round(v / HALL_STEP) * HALL_STEP

    def read_force(self, i):
        if self.force_broken:
            return None
        mf = self.m_m * self.alpha() * abs(i) / G0 * 1000.0
        mf += self.force_off + self.rng.normal(0, self.force_noise)
        if abs(mf) > FORCE_MAX:
            self.force_broken = True
            return None
        return round(mf / FORCE_STEP) * FORCE_STEP

    def read_protractor(self, th):
        return int(round(math.degrees(th) + self.rng.normal(0, 0.45)))

    def jitter(self, s):
        return float(self.rng.normal(0.0, s))

    # ---------------- pod ----------------
    def inertia(self, magnet, m_a, r_a):
        return self.J_pod + (self.J_mag if magnet else 0.0) + 2 * m_a * r_a * r_a

    def step(self, dt, L, magnet, th0, m_a, r_a, zeta=None):
        J = self.inertia(magnet, m_a, r_a)
        k = self.C_f / L + (self.m_m * self.B_e if magnet else 0.0)
        c = 2 * J / 110.0 if zeta is None else 2 * zeta * math.sqrt(k * J)
        tq = -(self.C_f / L) * (self.theta - th0)
        if magnet:
            tq -= self.m_m * self.B_e * math.sin(self.theta)
        self.omega += (tq - c * self.omega) / J * dt
        self.theta += self.omega * dt

    def settle(self, L, magnet, th0, m_a, r_a, t=45.0, dt=0.005):
        for _ in range(int(t / dt)):
            self.step(dt, L, magnet, th0, m_a, r_a, zeta=0.85)
        self.omega = 0.0
        return self.theta


# ══════════════════════════════════════════════════════════════════
#  shared widgets
# ══════════════════════════════════════════════════════════════════
def lcd(parent, lines, width=17, size=17, fg="#39ff88"):
    box = tk.Frame(parent, bg="#0d1a12", bd=2, relief="sunken")
    labels = []
    for _ in range(lines):
        l = tk.Label(box, text="", font=("Consolas", size, "bold"),
                     fg=fg, bg="#0d1a12", anchor="w", width=width)
        l.pack(fill="x", padx=7, pady=2)
        labels.append(l)
    return box, labels


def notebook_table(parent, columns, widths):
    tv = ttk.Treeview(parent, columns=[c[0] for c in columns],
                      show="headings", height=9)
    for (key, title), w in zip(columns, widths):
        tv.heading(key, text=title)
        tv.column(key, width=w, anchor="e")
    return tv


def ruler(ax, x0, x1, y, step, label_every, tick, color="#3a3a3a",
          fontsize=7, below=True, origin=0.0):
    """Millimetre scale between x0 and x1; the label of a tick is its own
    coordinate minus `origin`, so a close-up carries the true numbers."""
    k0 = int(math.ceil((x0 - origin) / step - 1e-9))
    k1 = int(math.floor((x1 - origin) / step + 1e-9))
    for k in range(k0, k1 + 1):
        x = origin + k * step
        big = (k % label_every == 0)
        mid = (k % max(label_every // 2, 1) == 0)
        h = tick * (1.0 if big else (0.60 if mid else 0.36))
        ax.plot([x, x], [y, y - h if below else y + h], color=color,
                lw=0.9 if big else 0.5, zorder=6)
        if big:
            ax.text(x, y - h - tick * 0.3 if below else y + h + tick * 0.3,
                    "%g" % (k * step), ha="center",
                    va="top" if below else "bottom",
                    fontsize=fontsize, color=color, zorder=6)
    ax.plot([x0, x1], [y, y], color=color, lw=1.0, zorder=6)


# ══════════════════════════════════════════════════════════════════
#  TAB 1 : the coils  (A.1 - A.4)
# ══════════════════════════════════════════════════════════════════
class CoilTab(ttk.Frame):
    def __init__(self, master, bench):
        super().__init__(master, padding=7)
        self.b = bench
        self.shown_B = 0.0
        self.last_B = 0.0
        self.last_mf = 0.0
        self.i_real = 0.0
        self.mm_on = True
        self.mm_idle = 0.0
        self.force_on = False
        self.drag = False
        self._last = time.perf_counter()

        self._controls()
        self._figure()
        self.redraw()
        self._tick()

    # ---------------- controls ----------------
    def _controls(self):
        c = ttk.Frame(self)
        c.grid(row=0, column=0, sticky="ns")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        r = 0

        ttk.Label(c, text=T("Arduino  (c)"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        box, self.lcd_lines = lcd(c, 2)
        box.grid(row=r, column=0, sticky="ew", pady=(3, 4))
        r += 1
        row = ttk.Frame(c)
        row.grid(row=r, column=0, sticky="w")
        self.var_sensor = tk.StringVar(value="field")
        ttk.Radiobutton(row, text=T("field sensor (d)"), value="field",
                        variable=self.var_sensor,
                        command=self.swap_sensor).pack(side="left")
        ttk.Radiobutton(row, text=T("force sensor (b)"), value="force",
                        variable=self.var_sensor,
                        command=self.swap_sensor).pack(side="left", padx=(8, 0))
        r += 1
        ttk.Button(c, text=T("switch the force sensor on  (it zeroes itself)"),
                   command=self.zero_force).grid(row=r, column=0, sticky="ew",
                                                 pady=(3, 2))
        r += 1

        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=7)
        r += 1
        ttk.Label(c, text=T("Multimeter  (g)   10 A range"),
                  font=("", 10, "bold")).grid(row=r, column=0, sticky="w")
        r += 1
        box, self.amm_lines = lcd(c, 1, width=12, size=19, fg="#8fd6ff")
        box.grid(row=r, column=0, sticky="ew", pady=(3, 2))
        r += 1
        row = ttk.Frame(c)
        row.grid(row=r, column=0, sticky="w", pady=(0, 4))
        ttk.Button(row, text=T("OFF"), width=6,
                   command=lambda: self.multimeter(False)).pack(side="left")
        ttk.Button(row, text=T("10 A"), width=6,
                   command=lambda: self.multimeter(True)).pack(side="left", padx=4)
        r += 1

        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=7)
        r += 1
        ttk.Label(c, text=T("Coil supply"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        self.var_switch = tk.BooleanVar(value=False)
        ttk.Checkbutton(c, text=T("close the switch (vi)"), variable=self.var_switch,
                        command=self.redraw).grid(row=r, column=0, sticky="w")
        r += 1
        ttk.Label(c, text=T("current knob (vii)")).grid(row=r, column=0, sticky="w",
                                                     pady=(4, 0))
        r += 1
        self.var_knob = tk.DoubleVar(value=40.0)
        ttk.Scale(c, from_=0.0, to=100.0, variable=self.var_knob, length=250,
                  orient="horizontal").grid(row=r, column=0, sticky="ew")
        r += 1
        ttk.Button(c, text=T("replace the 9 V battery with a spare"),
                   command=self.swap_batt).grid(row=r, column=0, sticky="ew",
                                                pady=(5, 2))
        r += 1
        self.lbl_batt = ttk.Label(c, text="", foreground="#666")
        self.lbl_batt.grid(row=r, column=0, sticky="w")
        r += 1

        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=7)
        r += 1
        ttk.Label(c, text=T("Note book"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        bt = ttk.Frame(c)
        bt.grid(row=r, column=0, sticky="ew", pady=(3, 2))
        ttk.Button(bt, text=T("write down"), command=self.record).pack(side="left")
        ttk.Button(bt, text=T("erase"), command=self.erase).pack(side="left", padx=4)
        ttk.Button(bt, text=T("new page"), command=self.clear).pack(side="left")
        r += 1
        self.rows = []
        self.tree = notebook_table(
            c, [("z", "z (mm)"), ("B", "B (mT)"), ("i", "i (A)"), ("m", "m (g)")],
            [62, 72, 62, 62])
        self.tree.grid(row=r, column=0, sticky="ew", pady=3)
        r += 1
        ttk.Button(c, text=T("export the page as CSV"),
                   command=self.export).grid(row=r, column=0, sticky="ew")
        r += 1
        self.msg = ttk.Label(c, text="", wraplength=255, foreground="#a33")
        self.msg.grid(row=r, column=0, sticky="w", pady=(6, 0))
        r += 1
        ttk.Label(c, wraplength=255, foreground="#555",
                  text=T("Drag the sensor board along the coil axis and read its "
                        "position on the board scale (1 mm divisions).  For the "
                        "Gouy balance the coils are turned so that the "
                        "transducer is vertical (Fig. 2 iii-iv).")
                  ).grid(row=r, column=0, sticky="w", pady=(6, 0))

    # ---------------- figure ----------------
    def _figure(self):
        self.fig = Figure(figsize=(8.4, 8.0), dpi=96)
        gs = self.fig.add_gridspec(2, 1, height_ratios=[1.28, 1.0], hspace=0.10)
        self.axm = self.fig.add_subplot(gs[0])
        self.ax3 = self.fig.add_subplot(gs[1], projection="3d")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew")
        self.canvas.mpl_connect("button_press_event", self._press)
        self.canvas.mpl_connect("motion_notify_event", self._motion)
        self.canvas.mpl_connect("button_release_event", self._release)
        self.z_probe = 0.023            # m, position read on the board scale

    # ---------------- drawing ----------------
    def redraw(self):
        mm = 1000.0
        field = (self.var_sensor.get() == "field")
        z1, z2 = self.b.z1 * mm, self.b.z2 * mm
        a = self.axm
        a.clear()

        if field:
            a.set_title(T("anti-Helmholtz coils (e), sensor sliding on the axis "
                        "(Fig. 2 i)"), fontsize=10)
            # ---- scale the user reads, above the assembly ----
            ruler(a, 0, BOARD_LEN * mm, 34, 1, 10, 5.0, below=False)
            a.text(30, 47, T("position of the sensor on the coil axis (mm)"),
                   ha="center", fontsize=7.5, color="#555")
            # ---- coil windings ----
            for zc in (z1, z2):
                a.add_patch(Rectangle((zc - 6.5, -15), 13, 30,
                                      facecolor="#8f959c", edgecolor="#5a5f66",
                                      lw=0.8, alpha=0.35, zorder=3))
                for s_ in (1, -1):
                    y0 = 15 if s_ > 0 else -25
                    a.add_patch(Rectangle((zc - 5, y0), 10, 10,
                                          facecolor="#c8862a",
                                          edgecolor="#7a4d12", lw=1.0, zorder=4))
                    for k in range(1, 10):
                        a.plot([zc - 5 + k] * 2, [y0, y0 + 10],
                               color="#a76d1f", lw=0.45, zorder=5)
                a.add_patch(Rectangle((zc - 7.5, -26), 15, 4,
                                      facecolor="#3f4348", edgecolor="#25282c",
                                      zorder=3))
            a.text(z1, 27, T("coil"), ha="center", fontsize=8)
            a.text(z2, 27, T("coil"), ha="center", fontsize=8)
            # ---- support ----
            a.add_patch(Rectangle((-16, -36), 92, 10, facecolor="#3f4348",
                                  edgecolor="#25282c", zorder=2))
            a.plot([-16, 76], [0, 0], "--", color="#aab", lw=0.7, zorder=2)
            # ---- sensor board ----
            zp = self.z_probe * mm
            a.add_patch(Rectangle((zp - 78, -3.2), 78, 6.4, facecolor="#1d6b3a",
                                  edgecolor="#0d3a1f", lw=0.8, zorder=7))
            for k in range(0, 76, 2):
                a.plot([zp - 78 + k] * 2, [1.0, 3.2], color="#d8e8dc",
                       lw=0.4, zorder=8)
            a.add_patch(Rectangle((zp - 4.2, -2.6), 4.2, 5.2,
                                  facecolor="#eceff1", edgecolor="#333",
                                  lw=0.7, zorder=8))
            a.plot([zp], [0], "o", color="#d8322a", ms=4.5, zorder=9)
            a.text(zp - 74, 6.0, T("field sensor board (d)"), fontsize=8,
                   color="#1d6b3a")
            a.plot([zp, zp], [0, 34], "-", color="#d8322a", lw=1.0,
                   alpha=0.85, zorder=7)
        else:
            a.set_title(T("coils turned so that the transducer is vertical "
                        "(Fig. 2 iii-iv)"), fontsize=10)
            yc1, yc2 = -15.0, 15.0          # the axis is now vertical
            for yc in (yc1, yc2):
                a.add_patch(Rectangle((-15, yc - 6.5), 30, 13,
                                      facecolor="#8f959c", edgecolor="#5a5f66",
                                      lw=0.8, alpha=0.35, zorder=3))
                for s_ in (1, -1):
                    x0 = 15 if s_ > 0 else -25
                    a.add_patch(Rectangle((x0, yc - 5), 10, 10,
                                          facecolor="#c8862a",
                                          edgecolor="#7a4d12", lw=1.0, zorder=4))
                    for k in range(1, 10):
                        a.plot([x0, x0 + 10], [yc - 5 + k] * 2,
                               color="#a76d1f", lw=0.45, zorder=5)
            a.add_patch(Rectangle((-34, -40), 68, 6, facecolor="#3f4348",
                                  edgecolor="#25282c", zorder=2))
            a.add_patch(Rectangle((-27, -34), 8, 12, facecolor="#3f4348",
                                  edgecolor="#25282c", zorder=2))
            a.add_patch(Rectangle((19, -34), 8, 12, facecolor="#3f4348",
                                  edgecolor="#25282c", zorder=2))
            # force sensor, transducer vertical
            a.add_patch(Rectangle((-4, 8), 8, 42, facecolor="#2e3d52",
                                  edgecolor="#101820", lw=0.9, zorder=7))
            a.add_patch(Rectangle((-2.6, 2), 5.2, 6, facecolor="#9aa0a6",
                                  edgecolor="#333", lw=0.8, zorder=8))
            a.add_patch(Rectangle((-2.2, -2.5), 4.4, 4.5, facecolor="#b9bcc2",
                                  edgecolor="#555", lw=0.8, zorder=8))
            a.text(6, 44, T("force sensor (b)"), fontsize=8, va="top")
            a.annotate(T("its magnet, at the centre of the device"),
                       xy=(2.4, -0.3), xytext=(9, -8), fontsize=8,
                       arrowprops=dict(arrowstyle="-", color="#777", lw=0.7))
            a.annotate("", xy=(-10, -9), xytext=(-10, 1), zorder=9,
                       arrowprops=dict(arrowstyle="-|>", color="#c00", lw=1.8))
            a.text(-15, -4, T("F"), color="#c00", fontsize=10, va="center")
            a.plot([-34, 34], [0, 0], "--", color="#aab", lw=0.7, zorder=2)

        # ---- supply box with its LED ----
        on = self.var_switch.get() and self.i_real > 0.005
        bx, by = (62, -20) if field else (44, -20)
        a.add_patch(Rectangle((bx, by), 20, 12, facecolor="#1f6b3f",
                              edgecolor="#0d3a1f", lw=0.8, zorder=6))
        a.add_patch(Circle((bx + 4.5, by + 6), 2.2,
                           facecolor="#ff4030" if on else "#4a2020",
                           edgecolor="#301010", zorder=7))
        a.text(bx + 9, by + 6, T("coil\nsupply"), fontsize=7, color="#eaf3ec",
               va="center", zorder=7)

        a.set_xlim(-38 if not field else -30, 88)
        a.set_ylim(-46, 54)
        a.set_aspect("equal")
        a.set_xticks([])
        a.set_yticks([])
        for sp in a.spines.values():
            sp.set_visible(False)

        # ---------------- 3D ----------------
        t = self.ax3
        t.clear()
        t.set_title(T("3D view"), fontsize=10)
        th = np.linspace(0, 2 * np.pi, 60)
        if field:
            for zc in (z1, z2):
                for rr in (15, 19, 23):
                    t.plot(np.full_like(th, zc), rr * np.cos(th),
                           rr * np.sin(th), color="#c8862a", lw=1.1, alpha=0.9)
                t.plot([zc, zc], [0, 0], [-26, -15], color="#5a5f66", lw=3)
            t.plot([-16, 76], [0, 0], [-26, -26], color="#3f4348", lw=6)
            zp = self.z_probe * mm
            t.plot([zp - 78, zp], [0, 0], [0, 0], color="#1d6b3a", lw=6)
            t.plot([zp], [0], [0], "o", color="#d8322a", ms=7)
        else:
            for zc in (Z0_COIL * mm - 15, Z0_COIL * mm + 15):
                for rr in (15, 19, 23):
                    t.plot(Z0_COIL * mm + rr * np.cos(th), rr * np.sin(th),
                           np.full_like(th, zc - Z0_COIL * mm),
                           color="#c8862a", lw=1.1, alpha=0.9)
            t.plot([-16, 76], [0, 0], [-26, -26], color="#3f4348", lw=6)
            t.plot([Z0_COIL * mm] * 2, [0, 0], [-4, 28], color="#2e3d52", lw=7)
        t.set_xlim(-20, 80)
        t.set_ylim(-30, 30)
        t.set_zlim(-30, 30)
        try:
            t.set_box_aspect((100, 60, 60))
        except Exception:
            pass
        t.view_init(elev=18, azim=-64)
        t.set_axis_off()
        self.canvas.draw_idle()

    # ---------------- dragging ----------------
    def _press(self, ev):
        if ev.inaxes is self.axm and ev.xdata is not None \
                and self.var_sensor.get() == "field":
            if abs(ev.xdata - self.z_probe * 1000) < 8 and abs(ev.ydata) < 8:
                self.drag = True

    def _motion(self, ev):
        if self.drag and ev.inaxes is self.axm and ev.xdata is not None:
            self.z_probe = float(np.clip(round(ev.xdata), 0,
                                         BOARD_LEN * 1000)) / 1000.0
            self.redraw()

    def _release(self, ev):
        self.drag = False

    # ---------------- actions ----------------
    def swap_sensor(self):
        self.b.force_broken = False if self.var_sensor.get() == "field" \
            else self.b.force_broken
        self.force_on = False
        self.redraw()

    def zero_force(self):
        self.force_on = True
        self.b.force_off = float(self.b.rng.normal(0, 0.05))
        self.msg.config(text="")

    def multimeter(self, on):
        self.mm_on = on
        self.mm_idle = 0.0

    def swap_batt(self):
        if self.b.swap_battery():
            self.msg.config(text="")
        else:
            self.msg.config(text=T("no spare battery left"))

    def record(self):
        z = "%.0f" % (self.z_probe * 1000) if self.var_sensor.get() == "field" \
            else "-"
        B = "%.2f" % (self.last_B * 1000) if self.var_sensor.get() == "field" \
            else "-"
        m = "-" if self.var_sensor.get() == "field" else (
            "broken" if self.last_mf is None else "%.1f" % self.last_mf)
        i = self.amm_lines[0].cget("text").strip()
        self.rows.append((z, B, i, m))
        self.tree.insert("", "end", values=(z, B, i, m))

    def erase(self):
        for it in self.tree.selection():
            k = self.tree.index(it)
            self.tree.delete(it)
            del self.rows[k]

    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self.rows.clear()

    def export(self):
        if not self.rows:
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv",
                                         filetypes=[("CSV", "*.csv")],
                                         initialfile="Q1_partA.csv")
        if not p:
            return
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("z_mm,B_mT,i_A,m_g\n")
            for row in self.rows:
                fh.write(",".join(str(v) for v in row) + "\n")

    # ---------------- loop ----------------
    def _tick(self):
        now = time.perf_counter()
        dt = min(now - self._last, 0.5)
        self._last = now

        want = self.var_knob.get() / 100.0 * 2.5
        if self.var_switch.get():
            self.i_real = min(want, self.b.max_current())
            self.b.drain(self.i_real, dt)
        else:
            self.i_real = 0.0

        # multimeter auto power off
        self.mm_idle += dt
        if self.mm_on and self.mm_idle > MULTIMETER_SLEEP:
            self.mm_on = False
        if self.mm_on:
            self.amm_lines[0].config(
                text=T("%6.2f A") % (self.i_real + self.b.rng.normal(0, 0.004)))
        else:
            self.amm_lines[0].config(text=T("  ---   "))

        # Arduino LCD
        zt = self.z_probe + self.b.jitter(self.b.pos_sigma)
        self.last_B = self.b.read_hall(self.b.B_coils(zt, self.i_real))
        line1 = "B: %+7.2f mT" % (self.last_B * 1000)
        if self.var_sensor.get() == "force":
            if not self.force_on:
                line2 = "m:  ---- g"
                self.last_mf = 0.0
            else:
                self.last_mf = self.b.read_force(self.i_real)
                line2 = "m:  BROKEN" if self.last_mf is None \
                    else "m: %+7.1f g" % self.last_mf
            line1 = "B:   ---- mT"
        else:
            line2 = "m:    -0.0 g"
        self.lcd_lines[0].config(text=line1)
        self.lcd_lines[1].config(text=line2)

        f = self.b.batt / BATT_FULL
        self.lbl_batt.config(
            text=T("spare batteries: %d") % self.b.spares
            + ("" if f > 0.02 else "   (the coil battery is flat)"))

        self.after(140, self._tick)


# ══════════════════════════════════════════════════════════════════
#  TAB 2 : the free magnet on the 40 cm ruler  (A.5)
# ══════════════════════════════════════════════════════════════════
class MagnetTab(ttk.Frame):
    def __init__(self, master, bench):
        super().__init__(master, padding=7)
        self.b = bench
        self.d = 0.040
        self.last_B = 0.0
        self.drag = False

        self._controls()
        self._figure()
        self.redraw()
        self._tick()

    def _controls(self):
        c = ttk.Frame(self)
        c.grid(row=0, column=0, sticky="ns")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        r = 0
        ttk.Label(c, text=T("Arduino  (c)"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        box, self.lcd_lines = lcd(c, 2)
        box.grid(row=r, column=0, sticky="ew", pady=(3, 6))
        r += 1
        ttk.Label(c, wraplength=255, foreground="#555",
                  text=T("The third magnet is stuck at the zero of the 40 cm "
                        "ruler (i).  Drag the field sensor along the "
                        "revolution axis and read its position on the ruler.")
                  ).grid(row=r, column=0, sticky="w", pady=(0, 6))
        r += 1
        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=6)
        r += 1
        ttk.Label(c, text=T("Note book"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        bt = ttk.Frame(c)
        bt.grid(row=r, column=0, sticky="ew", pady=(3, 2))
        ttk.Button(bt, text=T("write down"), command=self.record).pack(side="left")
        ttk.Button(bt, text=T("erase"), command=self.erase).pack(side="left", padx=4)
        ttk.Button(bt, text=T("new page"), command=self.clear).pack(side="left")
        r += 1
        self.rows = []
        self.tree = notebook_table(c, [("d", "d (mm)"), ("B", "B (mT)")],
                                   [110, 120])
        self.tree.grid(row=r, column=0, sticky="ew", pady=3)
        r += 1
        ttk.Button(c, text=T("export the page as CSV"),
                   command=self.export).grid(row=r, column=0, sticky="ew")

    def _figure(self):
        self.fig = Figure(figsize=(8.4, 8.0), dpi=96)
        gs = self.fig.add_gridspec(2, 1, height_ratios=[1.0, 2.3], hspace=0.18)
        self.axm = self.fig.add_subplot(gs[0])
        self.axz = self.fig.add_subplot(gs[1])
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew")
        self.canvas.mpl_connect("button_press_event", self._press)
        self.canvas.mpl_connect("motion_notify_event", self._motion)
        self.canvas.mpl_connect("button_release_event", self._release)

    def _scene(self, a, x0, x1, y0, y1, step, label_every, tick, title):
        a.clear()
        a.set_title(title, fontsize=10)
        # ---- table and 40 cm ruler ----
        a.add_patch(Rectangle((x0 - 5, -tick * 2.6), (x1 - x0) + 10,
                              tick * 2.6, facecolor="#f3f1e6",
                              edgecolor="#8a8578", lw=0.9, zorder=2))
        ruler(a, max(x0, 0.0), min(x1, RULER_LEN * 1000), 0.0, step,
              label_every, tick)
        # ---- magnet stuck at the zero of the ruler ----
        mw, mh = MAG_L * 1000, 2 * MAG_R * 1000
        a.add_patch(Rectangle((-mw, 0), mw, mh, facecolor="#b9bcc2",
                              edgecolor="#555", lw=1.1, zorder=5))
        a.add_patch(Rectangle((-mw - 2.5, -1.5), 3.0, mh + 3,
                              facecolor="#f2d24b", edgecolor="#b39a2a",
                              lw=0.7, zorder=4))
        a.annotate("", xy=(1.5, mh / 2), xytext=(-mw + 1.5, mh / 2), zorder=6,
                   arrowprops=dict(arrowstyle="-|>", color="#c00", lw=1.5))
        # ---- the sliding field sensor ----
        dm = self.d * 1000
        bl = min(x1 - dm + 10, 120)
        a.add_patch(Rectangle((dm, mh / 2 - 3.2), bl, 6.4,
                              facecolor="#1d6b3a", edgecolor="#0d3a1f",
                              lw=0.8, zorder=6))
        a.add_patch(Rectangle((dm, mh / 2 - 2.6), 4.2, 5.2,
                              facecolor="#eceff1", edgecolor="#333",
                              lw=0.7, zorder=7))
        a.plot([dm], [mh / 2], "o", color="#d8322a", ms=4.5, zorder=8)
        a.plot([dm, dm], [-tick * 2.6, mh / 2], "-", color="#d8322a",
               lw=1.0, zorder=7)
        a.set_xlim(x0, x1)
        a.set_ylim(y0, y1)
        a.set_aspect("equal")
        a.set_xticks([])
        a.set_yticks([])
        for sp in a.spines.values():
            sp.set_visible(False)

    def redraw(self):
        self._scene(self.axm, -30, 415, -32, 34, 10, 5, 7,
                    T("40 cm ruler (i), magnet (a) stuck at its zero, "
                      "field sensor (d) on the axis"))
        self.axm.text(0, 20, T("magnet at 0"), fontsize=8, ha="left")
        lo = max(-14.0, self.d * 1000 - 26)
        self._scene(self.axz, lo, lo + 66, -15, 21, 1, 10, 3.4,
                    T("close-up: read the position of the sensor on the "
                      "millimetre scale"))
        self.canvas.draw_idle()

    def _press(self, ev):
        if ev.inaxes in (self.axm, self.axz) and ev.xdata is not None:
            if abs(ev.xdata - self.d * 1000) < (16 if ev.inaxes is self.axm else 8):
                self.drag = True

    def _motion(self, ev):
        if self.drag and ev.inaxes in (self.axm, self.axz) and ev.xdata is not None:
            self.d = float(np.clip(round(ev.xdata), 2, 400)) / 1000.0
            self.redraw()

    def _release(self, ev):
        self.drag = False

    def record(self):
        d = "%.0f" % (self.d * 1000)
        B = "%.2f" % (self.last_B * 1000)
        self.rows.append((d, B))
        self.tree.insert("", "end", values=(d, B))

    def erase(self):
        for it in self.tree.selection():
            k = self.tree.index(it)
            self.tree.delete(it)
            del self.rows[k]

    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self.rows.clear()

    def export(self):
        if not self.rows:
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv",
                                         filetypes=[("CSV", "*.csv")],
                                         initialfile="Q1_A5.csv")
        if not p:
            return
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("d_mm,B_mT\n")
            for row in self.rows:
                fh.write("%s,%s\n" % row)

    def _tick(self):
        dt = self.d - self.b.face + self.b.jitter(self.b.dist_sigma)
        self.last_B = self.b.read_hall(self.b.B_magnet(max(dt, 1e-4)))
        self.lcd_lines[0].config(text=T("B: %+7.2f mT") % (self.last_B * 1000))
        self.lcd_lines[1].config(text=T("m:    -0.0 g"))
        self.after(160, self._tick)


# ══════════════════════════════════════════════════════════════════
#  TAB 3 : the pod on the stand  (B.1 - B.6)
# ══════════════════════════════════════════════════════════════════
class PodTab(ttk.Frame):
    def __init__(self, master, bench):
        super().__init__(master, padding=7)
        self.b = bench
        self.L = 0.34
        self.th0 = 0.0
        self.sim_t = 0.0
        self.speed = 5.0
        self.sw_run = False
        self.sw_t0 = 0.0
        self.sw_val = 0.0
        self.laps = []
        self._last = time.perf_counter()

        self._controls()
        self._figure()
        self.redraw()
        self._tick()

    # ---------------- controls ----------------
    def _controls(self):
        c = ttk.Frame(self)
        c.grid(row=0, column=0, sticky="ns")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        r = 0
        ttk.Label(c, text=T("Pod (f3) and wire"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        row = ttk.Frame(c)
        row.grid(row=r, column=0, sticky="w", pady=(2, 2))
        ttk.Label(row, text=T("wire length L (cm)")).pack(side="left")
        self.var_L = tk.StringVar(value="34")
        e = ttk.Entry(row, textvariable=self.var_L, width=6)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda *_: self.set_L())
        ttk.Button(row, text=T("set"), width=5, command=self.set_L).pack(side="left")
        r += 1
        self.var_mag = tk.BooleanVar(value=True)
        ttk.Checkbutton(c, text=T("magnet (a) inserted in the pod"),
                        variable=self.var_mag,
                        command=self.redraw).grid(row=r, column=0, sticky="w")
        r += 1
        ttk.Label(c, text=T("sticky paste at both ends  m_a (g per side)")).grid(
            row=r, column=0, sticky="w", pady=(5, 0))
        r += 1
        self.var_ma = tk.DoubleVar(value=0.0)
        ttk.Scale(c, from_=0.0, to=3.0, variable=self.var_ma, length=250,
                  orient="horizontal",
                  command=lambda *_: self.redraw()).grid(row=r, column=0,
                                                         sticky="ew")
        r += 1
        self.lbl_ma = ttk.Label(c, text="")
        self.lbl_ma.grid(row=r, column=0, sticky="w")
        r += 1
        ttk.Label(c, text=T("radius of the paste  r_a (cm)")).grid(
            row=r, column=0, sticky="w", pady=(4, 0))
        r += 1
        self.var_ra = tk.DoubleVar(value=4.0)
        ttk.Scale(c, from_=2.0, to=6.0, variable=self.var_ra, length=250,
                  orient="horizontal",
                  command=lambda *_: self.redraw()).grid(row=r, column=0,
                                                         sticky="ew")
        r += 1

        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=6)
        r += 1
        ttk.Label(c, text=T("Upper piece (f2a)   theta_0"),
                  font=("", 10, "bold")).grid(row=r, column=0, sticky="w")
        r += 1
        row = ttk.Frame(c)
        row.grid(row=r, column=0, sticky="w", pady=(2, 2))
        for lab, dv in ((T("-1 turn"), -360), ("-90", -90), ("-10", -10),
                        ("+10", 10), ("+90", 90), (T("+1 turn"), 360)):
            ttk.Button(row, text=lab, width=6,
                       command=lambda d=dv: self.turn(d)).pack(side="left")
        r += 1
        self.lbl_th0 = ttk.Label(c, text="")
        self.lbl_th0.grid(row=r, column=0, sticky="w")
        r += 1
        ttk.Button(c, text=T("damp the pod by hand until it rests"),
                   command=self.settle).grid(row=r, column=0, sticky="ew",
                                             pady=(3, 2))
        r += 1

        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=6)
        r += 1
        ttk.Label(c, text=T("Oscillation"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        row = ttk.Frame(c)
        row.grid(row=r, column=0, sticky="w", pady=(2, 2))
        ttk.Label(row, text=T("displace by")).pack(side="left")
        self.var_amp = tk.DoubleVar(value=15.0)
        ttk.Scale(row, from_=2.0, to=40.0, variable=self.var_amp,
                  length=110, orient="horizontal").pack(side="left", padx=4)
        ttk.Button(row, text=T("release"), command=self.release).pack(side="left")
        r += 1
        row = ttk.Frame(c)
        row.grid(row=r, column=0, sticky="w", pady=(2, 4))
        ttk.Label(row, text=T("speed ")).pack(side="left")
        self.var_speed = tk.StringVar(value="5")
        cb = ttk.Combobox(row, textvariable=self.var_speed, width=6,
                          state="readonly",
                          values=["1", "2", "5", "10", "20"])
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>",
                lambda *_: setattr(self, "speed", float(self.var_speed.get())))
        ttk.Label(row, text=T(" x")).pack(side="left")
        r += 1

        ttk.Label(c, text=T("Chronometer (k)"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w", pady=(4, 0))
        r += 1
        box, self.sw_lines = lcd(c, 1, width=12, size=19, fg="#8fd6ff")
        box.grid(row=r, column=0, sticky="ew", pady=(3, 2))
        r += 1
        row = ttk.Frame(c)
        row.grid(row=r, column=0, sticky="ew")
        self.btn_sw = ttk.Button(row, text=T("Start"), width=7, command=self.sw_toggle)
        self.btn_sw.pack(side="left")
        ttk.Button(row, text=T("Lap"), width=6, command=self.sw_lap).pack(side="left",
                                                                      padx=3)
        ttk.Button(row, text=T("Reset"), width=7,
                   command=self.sw_reset).pack(side="left")
        r += 1
        self.lst = tk.Listbox(c, height=7, font=("Consolas", 9))
        self.lst.grid(row=r, column=0, sticky="ew", pady=4)
        r += 1
        ttk.Label(c, wraplength=255, foreground="#555",
                  text=T("Read theta_eq with the toothpick on the lower "
                        "protractor (f1a), 1 deg divisions.  Turning the upper "
                        "piece twists the wire by several turns while the pod "
                        "only moves by a fraction of one.")
                  ).grid(row=r, column=0, sticky="w", pady=(4, 0))

    # ---------------- figure ----------------
    def _figure(self):
        self.fig = Figure(figsize=(8.4, 6.6), dpi=96)
        gs = self.fig.add_gridspec(1, 2, width_ratios=[1.0, 1.05], wspace=0.12)
        self.axf = self.fig.add_subplot(gs[0])
        self.axp = self.fig.add_subplot(gs[1])
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew")
        self.background = None
        self.canvas.mpl_connect("draw_event", self._on_draw)

    def _on_draw(self, ev):
        self.background = self.canvas.copy_from_bbox(self.fig.bbox)

    # ---------------- drawing ----------------
    def redraw(self):
        L = self.L * 100.0           # cm
        ra = self.var_ra.get()
        ma = self.var_ma.get()
        self.lbl_ma.config(text=T("m_a = %.2f g per side (total %.2f g)") % (ma, 2 * ma))
        self.lbl_th0.config(text=T("theta_0 = %+.0f deg  (%.2f turns)") % (self.th0, self.th0 / 360.0))

        # ---------------- front view (the wire is drawn with a break) ------
        a = self.axf
        a.clear()
        a.set_title(T("stand (f) - front view"), fontsize=10)
        Y_TOP, Y_BR1, Y_BR2 = 27.0, 15.0, 19.0
        a.add_patch(Rectangle((-9, -3.4), 20, 3.4, facecolor="#d8b98a",
                              edgecolor="#8a7048", lw=1.0, zorder=1))
        for y0, y1 in ((0, Y_BR1), (Y_BR2, Y_TOP + 2.5)):
            a.add_patch(Rectangle((-0.8, y0), 1.6, y1 - y0, facecolor="#a8adb3",
                                  edgecolor="#5c6166", lw=0.8, zorder=2))
        # break symbol
        for y in (Y_BR1, Y_BR2):
            xx = np.array([-2.2, -0.8, 0.8, 2.2])
            a.plot(xx, y + np.array([0.0, 0.9, -0.9, 0.0]), "-",
                   color="#5c6166", lw=1.0, zorder=3)
        # upper arm (f2) and its piece (f2a)
        a.add_patch(Rectangle((0.7, Y_TOP - 1.1), 6.0, 2.2,
                              facecolor="#3a3f45", edgecolor="#22262a", zorder=3))
        a.add_patch(Circle((6.7, Y_TOP), 2.3, facecolor="#e9ecef",
                           edgecolor="#3a3f45", lw=1.1, zorder=4))
        a.text(9.4, Y_TOP + 1.4, T("f2a  (turn to set theta_0)"), fontsize=8)
        # wire, twisted by theta_0
        yy = np.concatenate([np.linspace(9.6, Y_BR1 - 0.4, 200),
                             np.linspace(Y_BR2 + 0.4, Y_TOP - 2.3, 200)])
        tw = min(abs(self.th0) / 360.0, 8.0)
        a.plot(6.7 + 0.32 * np.sin(2 * np.pi * tw * 1.6 *
                                   (yy - 9.6) / max(Y_TOP - 12.0, 1e-6)),
               yy, "-", color="#6b7076", lw=1.1, zorder=3)
        a.annotate("", xy=(12.6, Y_TOP - 2.3), xytext=(12.6, 9.6), zorder=5,
                   arrowprops=dict(arrowstyle="<|-|>", color="#2a8f5a", lw=1.2))
        a.text(13.2, (Y_TOP + 9.6) / 2 - 1.0, T("L = %.0f cm") % L,
               fontsize=9, color="#2a8f5a", va="center")
        # lower arm (f1) with the protractor (f1a)
        a.add_patch(Rectangle((0.7, 2.2), 6.0, 2.0, facecolor="#3a3f45",
                              edgecolor="#22262a", zorder=3))
        a.add_patch(Circle((6.7, 3.2), 3.4, facecolor="#e9ecef",
                           edgecolor="#3a3f45", lw=1.1, zorder=3))
        a.text(10.6, 2.0, T("f1a"), fontsize=8)
        # pod (f3)
        a.add_patch(Rectangle((5.6, 6.0), 2.2, 3.6, facecolor="#3a3f45",
                              edgecolor="#22262a", zorder=6))
        a.plot([6.7 - ra, 6.7 + ra], [7.0, 7.0], "-", color="#2b3036",
               lw=3.4, zorder=8)
        a.plot([6.7, 6.7], [4.6, 6.0], "-", color="#c08a3e", lw=1.6, zorder=7)
        if ma > 0.02:
            for sgn in (-1, 1):
                a.add_patch(Circle((6.7 + sgn * ra, 7.0),
                                   0.30 + 0.60 * ma ** (1 / 3.),
                                   facecolor="#ffd94a", edgecolor="#a8862a",
                                   zorder=9))
            a.annotate(T("sticky paste, m_a each"),
                       xy=(6.7 + ra, 7.6), xytext=(9.4, 12.0), fontsize=8,
                       arrowprops=dict(arrowstyle="-", color="#777", lw=0.7))
        if self.var_mag.get():
            a.add_patch(Rectangle((6.3, 6.5), 0.8, 2.0, facecolor="#b9bcc2",
                                  edgecolor="#555", zorder=7))
        a.annotate("", xy=(6.7 + ra, 8.9), xytext=(6.7 - ra, 8.9), zorder=6,
                   arrowprops=dict(arrowstyle="<|-|>", color="#2a8f5a", lw=1.0))
        a.text(6.7 + ra + 0.4, 8.9, T("2 r_a = %.1f cm") % (2 * ra), fontsize=8,
               color="#2a8f5a", ha="left", va="center")
        a.text(-8.4, 8.4, T("pod (f3)\nwith the\ninertia bar\nand the\ntoothpick"),
               fontsize=8, va="top")
        a.set_xlim(-10, 22)
        a.set_ylim(-5, 32)
        a.set_aspect("equal")
        a.set_xticks([])
        a.set_yticks([])
        for sp in a.spines.values():
            sp.set_visible(False)

        # ---------------- protractor, seen from above ----------------
        p = self.axp
        p.clear()
        p.set_title(T("lower protractor (f1a) seen from above"), fontsize=10)
        p.add_patch(Circle((0, 0), 10.0, facecolor="#f4f6f8",
                           edgecolor="#3a3f45", lw=1.4, zorder=1))
        for k in range(360):
            th = math.radians(k)
            if k % 10 == 0:
                r0, lw = 8.4, 0.9
            elif k % 5 == 0:
                r0, lw = 8.9, 0.7
            else:
                r0, lw = 9.3, 0.4
            p.plot([r0 * math.sin(th), 10.0 * math.sin(th)],
                   [r0 * math.cos(th), 10.0 * math.cos(th)],
                   color="#3a3f45", lw=lw, zorder=2)
            if k % 30 == 0:
                p.text(7.4 * math.sin(th), 7.4 * math.cos(th),
                       T("%d") % (k if k <= 180 else k - 360),
                       ha="center", va="center", fontsize=7.5, zorder=2)
        p.plot([0], [0], "o", color="#3a3f45", ms=4, zorder=3)
        (self.bar,) = p.plot([], [], "-", color="#2b3036", lw=4.0,
                             solid_capstyle="round", zorder=4, animated=True)
        (self.tooth,) = p.plot([], [], "-", color="#c08a3e", lw=2.0,
                               zorder=5, animated=True)
        (self.pastes,) = p.plot([], [], "o", color="#ffd94a", ms=9,
                                markeredgecolor="#a8862a", zorder=6,
                                animated=True)
        p.set_xlim(-11.5, 11.5)
        p.set_ylim(-11.5, 11.5)
        p.set_aspect("equal")
        p.set_xticks([])
        p.set_yticks([])
        for sp in p.spines.values():
            sp.set_visible(False)

        self.background = None
        self.canvas.draw_idle()

    # ---------------- actions ----------------
    def set_L(self):
        try:
            v = float(self.var_L.get())
        except ValueError:
            return
        self.L = float(np.clip(v, 5.0, 40.0)) / 100.0
        self.var_L.set("%.0f" % (self.L * 100))
        self.redraw()

    def turn(self, d):
        self.th0 += d
        self.redraw()

    def settle(self):
        self.b.settle(self.L, self.var_mag.get(), math.radians(self.th0),
                      self.var_ma.get() / 1000.0, self.var_ra.get() / 100.0)

    def release(self):
        # the pod is turned by hand from where it rests and let go:
        # the displacement is counted from the present position, so the
        # oscillation is centred on the true equilibrium in every case
        self.b.theta += math.radians(self.var_amp.get())
        self.b.omega = 0.0

    def sw_toggle(self):
        if self.sw_run:
            self.sw_run = False
            self.btn_sw.config(text=T("Start"))
        else:
            self.sw_run = True
            self.sw_t0 = self.sim_t - self.sw_val
            self.btn_sw.config(text=T("Stop"))

    def sw_lap(self):
        if not self.sw_run:
            return
        v = max(0.0, self.sw_val + self.b.rng.normal(0, 0.12))
        self.laps.append(v)
        prev = self.laps[-2] if len(self.laps) > 1 else 0.0
        self.lst.insert("end", "%2d  %8.2f s  (+%6.2f)"
                        % (len(self.laps), v, v - prev))
        self.lst.see("end")

    def sw_reset(self):
        self.sw_run = False
        self.sw_val = 0.0
        self.laps.clear()
        self.lst.delete(0, "end")
        self.btn_sw.config(text=T("Start"))

    # ---------------- loop ----------------
    def _tick(self):
        t0 = time.perf_counter()
        dt = min(t0 - self._last, 0.4)
        self._last = t0
        n = max(1, int(dt * self.speed / 0.002))
        n = min(n, 4000)
        step = dt * self.speed / n
        for _ in range(n):
            self.b.step(step, self.L, self.var_mag.get(),
                        math.radians(self.th0), self.var_ma.get() / 1000.0,
                        self.var_ra.get() / 100.0)
        self.sim_t += dt * self.speed
        if self.sw_run:
            self.sw_val = self.sim_t - self.sw_t0
        self.sw_lines[0].config(text=T("%8.2f s") % self.sw_val)

        if not self.winfo_ismapped():
            self.after(150, self._tick)
            return

        th = self.b.theta
        ra = self.var_ra.get()
        rr = 3.2 + 1.1 * ra
        s, cth = math.sin(th), math.cos(th)
        self.bar.set_data([-rr * s, rr * s], [-rr * cth, rr * cth])
        self.tooth.set_data([0, 9.6 * math.sin(th + math.pi / 2)],
                            [0, 9.6 * math.cos(th + math.pi / 2)])
        if self.var_ma.get() > 0.02:
            self.pastes.set_data([-rr * s, rr * s], [-rr * cth, rr * cth])
            self.pastes.set_markersize(5 + 5 * self.var_ma.get() ** (1 / 3.))
        else:
            self.pastes.set_data([], [])

        if self.background is None:
            self.canvas.draw()
        else:
            self.canvas.restore_region(self.background)
            for art in (self.bar, self.tooth, self.pastes):
                self.axp.draw_artist(art)
            self.canvas.blit(self.fig.bbox)

        self.after(max(50, int(2200 * (time.perf_counter() - t0))), self._tick)


# ══════════════════════════════════════════════════════════════════
class App:
    def __init__(self, root):
        root.title(T("IPhO 2025 Q1 - Earth's magnetic field measurement "
                   "(virtual laboratory)"))
        bench = Bench()
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        nb.add(CoilTab(nb, bench), text=T("  Part A - coils (A.1 - A.4)  "))
        nb.add(MagnetTab(nb, bench), text=T("  Part A - free magnet (A.5)  "))
        nb.add(PodTab(nb, bench), text=T("  Part B - pod on the stand  "))


def main():
    root = tk.Tk()
    _setup_hangul_font(root)
    try:
        root.call("tk", "scaling", 1.15)
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
