#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPhO 2025 (France) Experimental Problem Q2
"Sand craters and dunes"

Virtual laboratory.

The apparatus delivers nothing but what the real one delivers: the sight of
the crater in the sand, the tape measure, the millimetre ruler, the wooden
track and the chronometer.  Nothing is computed for the user: no energy, no
exponent, no fit, no log-log plot, no mu_eff, no score.  D and L are read off
a drawn ruler and written down by hand, and the times are taken by clicking
the chronometer, so the reaction error is the user's own.

────────────────────────────────────────────────────────────────────────
HOW THE REAL EXPERIMENT RUNS  (problem sheet)

 PART A - impact craters
  A.1  fill the bowl, level the surface with the edge of the ruler, drop ball
       #3 from h = 50 cm and measure the crater diameter D.  Repeat 5 times,
       mixing the sand with the spoon after every impact - if you do not, the
       sand compacts and the craters get smaller.
  A.2  h_max is where the drag reaches 10 % of the weight; above it the ball
       arrives slower than sqrt(2gh) and the crater is too small.
  A.3  cover a wide energy range: the small ball from ~10 cm, the big one up
       to 2 m; two drops per setting.
  A.4  the log-log plot of D against E = mgh, and the choice between the
       exponents 0, 1/3 and 1/4, are done on paper.

 PART B - rolling and bogging
  B.2  raise one end of the 1 m rail with the clamp and read the height on
       the vertical rod: sin(theta) = height / rail length.  Release ball #4
       from l = 50 cm and time the run with the chronometer.  Do it 5 times.
  B.3  repeat for at least 8 values of l.
  B.6  fill the wooden track with sand, scrape it flat, release from l =
       50 cm and read the stopping distance L on the millimetre ruler.
  B.7  repeat for at least 8 values of l.  Stir, refill and scrape before
       every run, otherwise the sand hardens and the ball leaves the track.

────────────────────────────────────────────────────────────────────────
PHYSICAL MODEL

  fall       quadratic drag, v^2 = v_t^2 [1 - exp(-2gh/v_t^2)],
             v_t^2 = 8 m g/(pi d^2 rho_0 Cx), Cx = 1
  crater     D = c E^(1/4) with E = m v^2/2, c such that
             D = 6.92 (m[g] h[cm])^0.25 mm without drag
  rail       x(t) = (5/14) g sin(theta) t^2                        (B.1)
  sand       point mass, dv/dt = -mu g, so L = (5/7) sin(theta) l / mu   (B.5)

CALIBRATION against the official Marking Scheme & Solution
  built-in truth   D = 6.92 (m h)^0.25 mm,  mu = 0.50
  a correct measurement then returns
      D(ball #3, 50 cm) = 24 +- 1 mm       (A.1  accepts 22 - 26 mm)
      h_max             = 0.9 / 2 / 4 / 7 m                        (A.2)
      exponent          = 1/4                                      (A.4)
      t50 at 5 deg      = 1.3 s            (B.2  accepts 1.2 - 1.4 s)
      g                 = 9 +- 1 m/s2      (B.4  accepts 6 - 14)
      L50               = 6.2 +- 0.4 cm    (B.6  accepts 5.5 - 7.5 cm)
      L ~ l             -> solid friction  (B.7)
      mu_eff            = 0.70             (B.8  accepts 0.6 - 1.0,
                          with the simplified relation L = sin(th)/mu * l)

ERROR MODEL (re-drawn at every new kit)
  crater law +-1.5 %, grain-scale scatter 4.5 %, irregular rim ~2 %,
  sand compaction -5 % per impact without mixing (floor 82 %),
  friction +-4 %, stopping scatter 6 %, hardening +5 % per run without
  re-preparing the track, rail angle read on a 1 mm scale
────────────────────────────────────────────────────────────────────────

Run:  python ipho2025_E2_sim_KO.py   (EN edition: ipho2025_E2_sim_EN.py)
Needs numpy and matplotlib (pip install numpy matplotlib).
"""

import math
import time
import tkinter as tk
from tkinter import ttk, filedialog

import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Circle, Polygon, Wedge
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


LANG = "EN"          # the KO edition differs only in this line
TR = {
    '0.00 s': '0.00 s',
    'Steel balls (d)': '강철 공 (d)',
    '%s   d = %.1f mm   m = %s g': '%s   d = %.1f mm   m = %s g',
    'Drag the ball up or down the tape measure (e) and read the drop height on its scale.': '공을 줄자 (e)를 따라 위아래로 끌고, 줄자 눈금에서 낙하 높이를 읽으세요.',
    'release the ball': '공 놓기',
    'mix the sand with the spoon (n) and level it with the ruler (o)': '숟가락 (n)으로 모래를 섞고 자 (o)로 고르기',
    'Note book': '기록장',
    'D read on the ruler (mm)': '자에서 읽은 D (mm)',
    'write down': '적기',
    'erase': '지우기',
    'new page': '새 쪽',
    'export the page as CSV': '이 쪽을 CSV로 내보내기',
    'bowl (b), stand (f) and tape measure (e)': '그릇 (b), 스탠드 (f), 줄자 (e)',
    'bowl filled with sand, surface levelled': '모래를 채우고 표면을 고른 그릇',
    'tape measure (cm)': '줄자 (cm)',
    'ball %s': '공 %s',
    'held by hand': '손으로 듦',
    'the sand seen from above, with the ruler (o) laid across': '위에서 본 모래, 자 (o)를 가로질러 놓음',
    'ruler (o), millimetre scale': '자 (o), 밀리미터 눈금',
    '%d impact(s) since the sand was mixed': '모래를 섞은 뒤 %d번 충돌',
    ' - it is getting compacted': ' - 모래가 다져지고 있습니다',
    'Rail (h) and track (j)': '레일 (h)와 트랙 (j)',
    'Drag the clamp (f2) up the rod and read the height of the raised end on the rod scale; the rail is 1.00 m long.  Drag the ball along the rail and read l on the tape stuck to it.': '클램프 (f2)를 기둥을 따라 끌어 올리고 기둥 눈금에서 들린 끝의 높이를 읽으세요. 레일 길이는 1.00 m 입니다.  공을 레일을 따라 끌고, 레일에 붙인 줄자에서 l 을 읽으세요.',
    'sand in the wooden track': '나무 트랙에 모래 채움',
    'stir, refill and scrape the track': '트랙을 섞고, 다시 채우고, 긁어 고르기',
    'RELEASE the ball': '공 놓기',
    'Chronometer (k)': '스톱워치 (k)',
    'Start': '시작',
    'Lap': '랩',
    'Reset': '리셋',
    'Stop': '정지',
    't (s)': 't (s)',
    'L (cm)': 'L (cm)',
    'rail (h) on the stand (f) and wooden track (j) - side view (cm)': '스탠드 (f)에 건 레일 (h)과 나무 트랙 (j) - 옆모습 (cm)',
    'rise of the raised end,\nread on the rod scale': '들린 끝의 높이,\n기둥 눈금으로 읽기',
    'ruler along the track (cm)': '트랙을 따라 놓은 자 (cm)',
    'close-up of the sand track (millimetre scale)': '모래 트랙 확대 (밀리미터 눈금)',
    '%d run(s) since the track was prepared': '트랙을 고른 뒤 %d번 굴림',
    ' - the sand is hardening': ' - 모래가 단단해지고 있습니다',
    'the ball left the end of the track - re-prepare the sand, this run is not usable': '공이 트랙 끝을 넘어갔습니다 - 모래를 다시 준비하세요. 이 측정은 쓸 수 없습니다',
    'IPhO 2025 Q2 - Sand craters and dunes (virtual laboratory)': 'IPhO 2025 Q2 - 모래 크레이터와 사구 (가상 실험실)',
    '  A - impact craters  ': '  A - 충돌 크레이터  ',
    '  B - rail and sand track  ': '  B - 레일과 모래 트랙  ',
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

G = 9.81
RHO_A = 7.8e3
RHO_0 = 1.2
CX = 1.0

BALLS = [("#1", 0.0020, 0.033e-3),
         ("#2", 0.0050, 0.51e-3),
         ("#3", 0.0090, 3.0e-3),
         ("#4", 0.0160, 17.0e-3)]

RAIL_LEN = 1.00          # m
TRACK_LEN = 0.45         # m, usable length of the wooden track
ROD_H = 0.36             # m, vertical rod of the stand


def h_max(d):
    return 0.1 * (2.0 / 3.0) * (RHO_A / RHO_0) / CX * d


class Bench:
    """One kit of sand, balls, rail and track."""

    def __init__(self, seed=None):
        rng = np.random.default_rng(seed)
        self.rng = rng
        # D = c E^(1/4)  <->  6.92 (m[g] h[cm])^0.25 mm
        self.c = 0.0695 * (1 + rng.normal(0, 0.015))
        self.scatter = 0.045
        self.bowl_shots = 0
        self.mu = float(rng.normal(0.500, 0.020))
        self.L_scatter = 0.06
        self.track_shots = 0
        self.rim = rng.normal(0, 1.0, 5)          # shape of the last crater
        self.last_D = None

    # ---------------- part A ----------------
    def impact_v2(self, d, m, h):
        vt2 = 8 * m * G / (math.pi * d * d * RHO_0 * CX)
        return vt2 * (1 - math.exp(-2 * G * h / vt2))

    def compaction(self):
        return max(0.82, 1.0 - 0.05 * self.bowl_shots)

    def drop(self, d, m, h):
        E = 0.5 * m * self.impact_v2(d, m, h)
        D = self.c * E ** 0.25 * self.compaction()
        D *= (1 + self.rng.normal(0, self.scatter))
        self.bowl_shots += 1
        self.rim = self.rng.normal(0, 1.0, 5)
        self.last_D = D
        return D

    def mix(self):
        self.bowl_shots = 0
        self.last_D = None

    # ---------------- part B ----------------
    def track_mu(self):
        return self.mu * max(0.80, 1.0 - 0.05 * self.track_shots)

    def stop_distance(self, ell, theta):
        L = (5.0 / 7.0) * math.sin(theta) / self.track_mu() * ell
        L *= (1 + self.rng.normal(0, self.L_scatter))
        self.track_shots += 1
        return L

    def prepare(self):
        self.track_shots = 0


# ══════════════════════════════════════════════════════════════════
def lcd(parent, width=12, size=19, fg="#8fd6ff"):
    box = tk.Frame(parent, bg="#101418", bd=2, relief="sunken")
    l = tk.Label(box, text=T("0.00 s"), font=("Consolas", size, "bold"),
                 fg=fg, bg="#101418", anchor="e", width=width)
    l.pack(fill="x", padx=8, pady=6)
    return box, l


def scale(ax, x0, x1, y, step, label_every, tick, below=True, origin=0.0,
          color="#3a3a3a", fontsize=7, unit=1.0):
    k0 = int(math.ceil((x0 - origin) / step - 1e-9))
    k1 = int(math.floor((x1 - origin) / step + 1e-9))
    for k in range(k0, k1 + 1):
        x = origin + k * step
        big = (k % label_every == 0)
        mid = (k % max(label_every // 2, 1) == 0)
        h = tick * (1.0 if big else (0.60 if mid else 0.36))
        ax.plot([x, x], [y, y - h if below else y + h], color=color,
                lw=0.9 if big else 0.5, zorder=7)
        if big:
            ax.text(x, y - h - tick * 0.3 if below else y + h + tick * 0.3,
                    "%g" % (k * step * unit), ha="center",
                    va="top" if below else "bottom", fontsize=fontsize,
                    color=color, zorder=7)
    ax.plot([x0, x1], [y, y], color=color, lw=1.0, zorder=7)


def vscale(ax, y0, y1, x, step, label_every, tick, origin=0.0,
           color="#3a3a3a", fontsize=7):
    k0 = int(math.ceil((y0 - origin) / step - 1e-9))
    k1 = int(math.floor((y1 - origin) / step + 1e-9))
    for k in range(k0, k1 + 1):
        y = origin + k * step
        big = (k % label_every == 0)
        mid = (k % max(label_every // 2, 1) == 0)
        w = tick * (1.0 if big else (0.60 if mid else 0.36))
        ax.plot([x, x + w], [y, y], color=color, lw=0.9 if big else 0.5,
                zorder=7)
        if big:
            ax.text(x + w + tick * 0.3, y, "%g" % (k * step), va="center",
                    ha="left", fontsize=fontsize, color=color, zorder=7)
    ax.plot([x, x], [y0, y1], color=color, lw=1.0, zorder=7)


# ══════════════════════════════════════════════════════════════════
#  TAB 1 : impact craters
# ══════════════════════════════════════════════════════════════════
class CraterTab(ttk.Frame):
    def __init__(self, master, bench):
        super().__init__(master, padding=7)
        self.b = bench
        self.ball = 2
        self.h = 0.50                 # m, release height above the sand
        self.drag = False
        self.rng_tex = np.random.default_rng(11)
        self.sand_tex = self.rng_tex.uniform(0, 1, (300, 2))

        self._controls()
        self._figure()
        self.redraw()

    # ---------------- controls ----------------
    def _controls(self):
        c = ttk.Frame(self)
        c.grid(row=0, column=0, sticky="ns")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        r = 0
        ttk.Label(c, text=T("Steel balls (d)"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        self.var_ball = tk.IntVar(value=2)
        for k, (lab, d, m) in enumerate(BALLS):
            ttk.Radiobutton(c, text=T("%s   d = %.1f mm   m = %s g") % (lab, d * 1e3,
                               ("%.3f" % (m * 1e3)).rstrip("0").rstrip(".")),
                            value=k, variable=self.var_ball,
                            command=self.set_ball).grid(row=r, column=0,
                                                        sticky="w")
            r += 1
        ttk.Label(c, wraplength=255, foreground="#555",
                  text=T("Drag the ball up or down the tape measure (e) and "
                        "read the drop height on its scale.")
                  ).grid(row=r, column=0, sticky="w", pady=(6, 4))
        r += 1
        ttk.Button(c, text=T("release the ball"),
                   command=self.drop).grid(row=r, column=0, sticky="ew",
                                           pady=(2, 2))
        r += 1
        ttk.Button(c, text=T("mix the sand with the spoon (n) and level it "
                           "with the ruler (o)"),
                   command=self.mix).grid(row=r, column=0, sticky="ew")
        r += 1
        self.lbl_sand = ttk.Label(c, text="", foreground="#a33", wraplength=255)
        self.lbl_sand.grid(row=r, column=0, sticky="w", pady=(4, 0))
        r += 1

        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=7)
        r += 1
        ttk.Label(c, text=T("Note book"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        row = ttk.Frame(c)
        row.grid(row=r, column=0, sticky="w", pady=(3, 2))
        ttk.Label(row, text=T("D read on the ruler (mm)")).pack(side="left")
        self.var_D = tk.StringVar()
        e = ttk.Entry(row, textvariable=self.var_D, width=7)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda *_: self.record())
        r += 1
        row = ttk.Frame(c)
        row.grid(row=r, column=0, sticky="ew", pady=(2, 2))
        ttk.Button(row, text=T("write down"), command=self.record).pack(side="left")
        ttk.Button(row, text=T("erase"), command=self.erase).pack(side="left",
                                                               padx=4)
        ttk.Button(row, text=T("new page"), command=self.clear).pack(side="left")
        r += 1
        self.rows = []
        self.tree = ttk.Treeview(c, columns=("b", "m", "h", "D"),
                                 show="headings", height=11)
        for k, t, w in (("b", "ball", 46), ("m", "m (g)", 62),
                        ("h", "h (cm)", 62), ("D", "D (mm)", 66)):
            self.tree.heading(k, text=t)
            self.tree.column(k, width=w, anchor="e")
        self.tree.grid(row=r, column=0, sticky="ew", pady=3)
        r += 1
        ttk.Button(c, text=T("export the page as CSV"),
                   command=self.export).grid(row=r, column=0, sticky="ew")

    # ---------------- figure ----------------
    def _figure(self):
        self.fig = Figure(figsize=(8.6, 7.6), dpi=96)
        gs = self.fig.add_gridspec(1, 2, width_ratios=[1.0, 1.25], wspace=0.14)
        self.axs = self.fig.add_subplot(gs[0])
        self.axc = self.fig.add_subplot(gs[1])
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew")
        self.canvas.mpl_connect("button_press_event", self._press)
        self.canvas.mpl_connect("motion_notify_event", self._motion)
        self.canvas.mpl_connect("button_release_event", self._release)

    # ---------------- drawing ----------------
    def redraw(self):
        lab, d, m = BALLS[self.ball]
        hcm = self.h * 100.0

        # ══════ set-up, side view (cm) ══════
        a = self.axs
        a.clear()
        a.set_title(T("bowl (b), stand (f) and tape measure (e)"), fontsize=10)
        # plastic box
        a.add_patch(Rectangle((-16, -2), 32, 9, facecolor="#cfd4d9",
                              edgecolor="#8d949b", lw=1.0, alpha=0.55, zorder=1))
        # bowl with sand
        th = np.linspace(math.pi, 2 * math.pi, 90)
        a.fill(12 * np.cos(th), 7 + 7.6 * np.sin(th), facecolor="#f7f7f2",
               edgecolor="#b8bdc2", lw=1.4, zorder=2)
        a.fill(11 * np.cos(th), 7 + 6.9 * np.sin(th), facecolor="#e7cf93",
               edgecolor="none", zorder=3)
        a.plot([-11, 11], [7, 7], "-", color="#c9ab68", lw=1.4, zorder=4)
        a.text(0, -6.4, T("bowl filled with sand, surface levelled"),
               ha="center", fontsize=8, color="#8a7648")
        # stand
        a.add_patch(Rectangle((-24, -2.6), 12, 2.6, facecolor="#d8b98a",
                              edgecolor="#8a7048", lw=1.0, zorder=1))
        a.add_patch(Rectangle((-19, 0), 1.4, 62, facecolor="#a8adb3",
                              edgecolor="#5c6166", lw=0.8, zorder=2))
        yb = 7 + hcm
        if yb <= 61.0:
            # the clamp on the rod holds the horizontal rod with the ball
            a.add_patch(Rectangle((-19.6, yb - 1.2), 4.0, 2.4,
                                  facecolor="#3a3f45", edgecolor="#22262a",
                                  zorder=5))
            a.plot([-15.6, -0.6], [yb, yb], "-", color="#8d949b", lw=2.2,
                   zorder=5)
        else:
            # above the top of the rod the ball is held by hand
            a.text(-1.4, yb - 7.0, T("held by hand"), fontsize=8, ha="right",
                   color="#7a5a3a")
        # tape measure, zero on the sand surface, long enough for 2 m drops
        top = max(105.0, hcm + 15.0)
        vscale(a, 7, 7 + top, 3.0, 1.0, 10, 1.8, origin=7.0)
        a.text(9.0, 7 + top + 7, T("tape measure (cm)"), fontsize=7.5,
               color="#555", ha="center")
        # the ball, held at the end of the rod
        a.add_patch(Circle((-0.6, yb), max(d * 100 / 2, 0.42),
                           facecolor="#4a4f55", edgecolor="#1d2124", zorder=6))
        a.plot([-0.6, 3.0], [yb, yb], ":", color="#c00", lw=1.0, zorder=6)
        a.plot([-0.6, -0.6], [7, yb], ":", color="#aaa", lw=0.8, zorder=4)
        a.text(-2.0, yb + 3.0, T("ball %s") % lab, fontsize=8, ha="right")
        a.set_xlim(-27, 26)
        a.set_ylim(-8, max(128.0, 7 + top + 16))
        a.set_aspect("equal")
        a.set_xticks([])
        a.set_yticks([])
        for sp in a.spines.values():
            sp.set_visible(False)

        # ══════ crater seen from above, with the ruler (mm) ══════
        c = self.axc
        c.clear()
        c.set_title(T("the sand seen from above, with the ruler (o) laid across"),
                    fontsize=10)
        c.add_patch(Circle((0, 0), 52, facecolor="#e7cf93",
                           edgecolor="#c9ab68", lw=1.4, zorder=1))
        c.add_patch(Circle((0, 0), 52, facecolor="none",
                           edgecolor="#c9ab68", lw=1.0, zorder=5))
        pts = self.sand_tex
        xx = (pts[:, 0] * 104 - 52)
        yy = (pts[:, 1] * 104 - 52)
        keep = xx ** 2 + yy ** 2 < 50 ** 2
        c.plot(xx[keep], yy[keep], ".", color="#d3b77a", ms=1.4, alpha=0.5,
               zorder=2)

        if self.b.last_D is not None:
            R = self.b.last_D * 1000 / 2.0        # mm
            t = np.linspace(0, 2 * np.pi, 400)
            rr = R * (1 + 0.020 * np.sin(3 * t + self.b.rim[0])
                      + 0.014 * np.sin(5 * t + self.b.rim[1])
                      + 0.010 * np.sin(7 * t + self.b.rim[2]))
            c.fill(rr * np.cos(t), rr * np.sin(t), facecolor="#c9a967",
                   edgecolor="#a8873f", lw=1.6, zorder=3)
            c.fill(0.62 * rr * np.cos(t), 0.62 * rr * np.sin(t),
                   facecolor="#b2914f", edgecolor="none", zorder=4)
            c.fill(1.06 * rr * np.cos(t) + 1.5, 1.06 * rr * np.sin(t) - 1.5,
                   facecolor="none", edgecolor="#dcc389", lw=2.0, zorder=2)

        # the ruler, laid across the crater: its graduated edge is the
        # diameter line, so the rim crosses it at both ends of D
        c.add_patch(Rectangle((-40, 0.2), 80, 13, facecolor="#f6f4e8",
                              edgecolor="#8a8578", lw=1.0, alpha=0.94, zorder=6))
        scale(c, -37, 37, 0.7, 1, 10, 4.4, below=False, origin=-36)
        c.text(0, 15.6, T("ruler (o), millimetre scale"), ha="center",
               fontsize=7.5, color="#555")
        c.set_xlim(-42, 42)
        c.set_ylim(-40, 20)
        c.set_aspect("equal")
        c.set_xticks([])
        c.set_yticks([])
        for sp in c.spines.values():
            sp.set_visible(False)

        n = self.b.bowl_shots
        if n == 0:
            self.lbl_sand.config(text="")
        else:
            self.lbl_sand.config(
                text=T("%d impact(s) since the sand was mixed") % n
                + ("" if n < 2 else T(" - it is getting compacted")))
        self.canvas.draw_idle()

    # ---------------- interaction ----------------
    def _press(self, ev):
        if ev.inaxes is self.axs and ev.ydata is not None:
            if abs(ev.ydata - (7 + self.h * 100)) < 8 and ev.xdata < 6:
                self.drag = True

    def _motion(self, ev):
        if self.drag and ev.inaxes is self.axs and ev.ydata is not None:
            self.h = float(np.clip(round(ev.ydata - 7), 5, 200)) / 100.0
            self.redraw()

    def _release(self, ev):
        self.drag = False

    def set_ball(self):
        self.ball = self.var_ball.get()
        self.redraw()

    def drop(self):
        lab, d, m = BALLS[self.ball]
        self.b.drop(d, m, self.h)
        self.var_D.set("")
        self.redraw()

    def mix(self):
        self.b.mix()
        self.redraw()

    def record(self):
        try:
            D = float(self.var_D.get())
        except ValueError:
            return
        lab, d, m = BALLS[self.ball]
        row = (lab, ("%.3f" % (m * 1e3)).rstrip("0").rstrip("."),
               "%.0f" % (self.h * 100), "%.1f" % D)
        self.rows.append(row)
        self.tree.insert("", "end", values=row)
        self.var_D.set("")

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
                                         initialfile="Q2_craters.csv")
        if not p:
            return
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("ball,m_g,h_cm,D_mm\n")
            for row in self.rows:
                fh.write(",".join(row) + "\n")


# ══════════════════════════════════════════════════════════════════
#  TAB 2 : the rail and the sand track
# ══════════════════════════════════════════════════════════════════
class RailTab(ttk.Frame):
    def __init__(self, master, bench):
        super().__init__(master, padding=7)
        self.b = bench
        self.rise = 0.087           # m, height of the raised end of the rail
        self.ell = 0.50             # m, distance travelled on the rail
        self.state = "idle"         # idle | rolling | sanding | stopped
        self.t_run = 0.0
        self.x_rail = 0.0
        self.x_sand = 0.0
        self.L_final = None
        self.v_entry = 0.0
        self.sand_on = True
        self.drag = None
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
        ttk.Label(c, text=T("Rail (h) and track (j)"),
                  font=("", 10, "bold")).grid(row=r, column=0, sticky="w")
        r += 1
        ttk.Label(c, wraplength=255, foreground="#555",
                  text=T("Drag the clamp (f2) up the rod and read the height of "
                        "the raised end on the rod scale; the rail is 1.00 m "
                        "long.  Drag the ball along the rail and read l on the "
                        "tape stuck to it.")
                  ).grid(row=r, column=0, sticky="w", pady=(2, 5))
        r += 1
        self.var_sand = tk.BooleanVar(value=True)
        ttk.Checkbutton(c, text=T("sand in the wooden track"),
                        variable=self.var_sand,
                        command=self.toggle_sand).grid(row=r, column=0,
                                                       sticky="w")
        r += 1
        ttk.Button(c, text=T("stir, refill and scrape the track"),
                   command=self.prepare).grid(row=r, column=0, sticky="ew",
                                              pady=(3, 2))
        r += 1
        self.lbl_track = ttk.Label(c, text="", foreground="#a33",
                                   wraplength=255)
        self.lbl_track.grid(row=r, column=0, sticky="w")
        r += 1
        ttk.Button(c, text=T("RELEASE the ball"),
                   command=self.release).grid(row=r, column=0, sticky="ew",
                                              pady=(5, 2))
        r += 1

        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=6)
        r += 1
        ttk.Label(c, text=T("Chronometer (k)"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        box, self.lbl_sw = lcd(c)
        box.grid(row=r, column=0, sticky="ew", pady=(3, 2))
        r += 1
        row = ttk.Frame(c)
        row.grid(row=r, column=0, sticky="ew")
        self.btn_sw = ttk.Button(row, text=T("Start"), width=7,
                                 command=self.sw_toggle)
        self.btn_sw.pack(side="left")
        ttk.Button(row, text=T("Lap"), width=6,
                   command=self.sw_lap).pack(side="left", padx=3)
        ttk.Button(row, text=T("Reset"), width=7,
                   command=self.sw_reset).pack(side="left")
        r += 1
        self.lst = tk.Listbox(c, height=5, font=("Consolas", 9))
        self.lst.grid(row=r, column=0, sticky="ew", pady=4)
        r += 1

        ttk.Separator(c).grid(row=r, column=0, sticky="ew", pady=6)
        r += 1
        ttk.Label(c, text=T("Note book"), font=("", 10, "bold")).grid(
            row=r, column=0, sticky="w")
        r += 1
        row = ttk.Frame(c)
        row.grid(row=r, column=0, sticky="w", pady=(3, 2))
        ttk.Label(row, text=T("t (s)")).pack(side="left")
        self.var_t = tk.StringVar()
        ttk.Entry(row, textvariable=self.var_t, width=7).pack(side="left",
                                                              padx=(3, 8))
        ttk.Label(row, text=T("L (cm)")).pack(side="left")
        self.var_L = tk.StringVar()
        ttk.Entry(row, textvariable=self.var_L, width=7).pack(side="left",
                                                              padx=3)
        r += 1
        row = ttk.Frame(c)
        row.grid(row=r, column=0, sticky="ew", pady=(2, 2))
        ttk.Button(row, text=T("write down"), command=self.record).pack(side="left")
        ttk.Button(row, text=T("erase"), command=self.erase).pack(side="left",
                                                               padx=4)
        ttk.Button(row, text=T("new page"), command=self.clear).pack(side="left")
        r += 1
        self.rows = []
        self.tree = ttk.Treeview(c, columns=("r", "l", "t", "L"),
                                 show="headings", height=9)
        for k, t, w in (("r", "rise (cm)", 66), ("l", "l (cm)", 58),
                        ("t", "t (s)", 58), ("L", "L (cm)", 58)):
            self.tree.heading(k, text=t)
            self.tree.column(k, width=w, anchor="e")
        self.tree.grid(row=r, column=0, sticky="ew", pady=3)
        r += 1
        ttk.Button(c, text=T("export the page as CSV"),
                   command=self.export).grid(row=r, column=0, sticky="ew")

    # ---------------- figure ----------------
    def _figure(self):
        self.fig = Figure(figsize=(8.6, 7.6), dpi=96)
        gs = self.fig.add_gridspec(2, 1, height_ratios=[1.35, 1.0], hspace=0.22)
        self.axr = self.fig.add_subplot(gs[0])
        self.axz = self.fig.add_subplot(gs[1])
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew")
        self.canvas.mpl_connect("button_press_event", self._press)
        self.canvas.mpl_connect("motion_notify_event", self._motion)
        self.canvas.mpl_connect("button_release_event", self._release)
        self.background = None
        self.canvas.mpl_connect("draw_event", self._on_draw)

    def _on_draw(self, ev):
        self.background = self.canvas.copy_from_bbox(self.fig.bbox)

    # ---------------- geometry (cm) ----------------
    @property
    def theta(self):
        return math.asin(min(self.rise / RAIL_LEN, 0.5))

    # ---------------- drawing ----------------
    def redraw(self):
        a = self.axr
        a.clear()
        a.set_title(T("rail (h) on the stand (f) and wooden track (j) - "
                    "side view (cm)"), fontsize=10)
        c_, s_ = math.cos(self.theta), math.sin(self.theta)
        x_top, y_top = 100.0 - 100.0 * c_, 100.0 * s_       # raised end
        # table
        a.add_patch(Rectangle((-16, -4), 190, 4, facecolor="#d8b98a",
                              edgecolor="#8a7048", lw=1.0, zorder=1))
        # stand with its vertical rod and the clamp
        a.add_patch(Rectangle((x_top - 9, 0), 18, 1.6, facecolor="#d8b98a",
                              edgecolor="#8a7048", zorder=2))
        a.add_patch(Rectangle((x_top - 0.7, 1.6), 1.4, ROD_H * 100,
                              facecolor="#a8adb3", edgecolor="#5c6166",
                              lw=0.8, zorder=2))
        vscale(a, 1.6, 1.6 + ROD_H * 100, x_top - 6.0, 1.0, 10, -2.6,
               origin=1.6)
        a.add_patch(Rectangle((x_top - 2.4, y_top - 1.4), 4.8, 2.8,
                              facecolor="#3a3f45", edgecolor="#22262a",
                              zorder=6))
        a.annotate("", xy=(x_top + 5.0, y_top), xytext=(x_top + 5.0, 1.6),
                   zorder=6,
                   arrowprops=dict(arrowstyle="<|-|>", color="#2a8f5a", lw=1.2))
        a.text(x_top + 5.0, y_top + 6.0,
               T("rise of the raised end,\nread on the rod scale"),
               color="#2a8f5a", fontsize=8, ha="center", va="bottom")
        # the rail itself
        a.plot([x_top, 100.0], [y_top, 0.0], "-", color="#b9bfc6", lw=5,
               solid_capstyle="round", zorder=4)
        a.plot([x_top, 100.0], [y_top, 0.0], "-", color="#8d949b", lw=1.0,
               zorder=5)
        # tape stuck along the rail, zero at the lower end
        n = 21
        for k in range(n):
            s = k * 5.0
            big = (k % 4 == 0)
            px, py = 100.0 - s * c_, s * s_
            a.plot([px, px + 2.4 * s_], [py, py + 2.4 * c_], color="#3a3a3a",
                   lw=0.9 if big else 0.5, zorder=6)
            if big:
                a.text(px + 4.6 * s_, py + 4.6 * c_, T("%d") % s, fontsize=7,
                       ha="center", va="center", color="#3a3a3a", zorder=6)
        # wooden track with the sand
        a.add_patch(Rectangle((100, -1.0), TRACK_LEN * 100 + 4, 3.4,
                              facecolor="#e2caa0", edgecolor="#a8865a",
                              lw=1.0, zorder=3))
        if self.var_sand.get():
            a.add_patch(Rectangle((100.5, -0.4), TRACK_LEN * 100 + 3, 2.4,
                                  facecolor="#e7cf93", edgecolor="none",
                                  zorder=4))
        # ruler along the track, zero at the end of the rail
        scale(a, 100, 100 + TRACK_LEN * 100, -4.6, 1.0, 10, 3.0, origin=100.0)
        a.text(100 + TRACK_LEN * 50, -12.5, T("ruler along the track (cm)"),
               ha="center", fontsize=7.5, color="#555")
        # the ball
        bx, by = self.ball_xy()
        (self.ball_art,) = a.plot([bx], [by], "o", color="#4a4f55",
                                  markeredgecolor="#1d2124", ms=9,
                                  zorder=8, animated=True)
        a.set_xlim(-18, 176)
        a.set_ylim(-17, 56)
        a.set_aspect("equal")
        a.set_xticks([])
        a.set_yticks([])
        for sp in a.spines.values():
            sp.set_visible(False)

        # ---------------- close-up of the track ----------------
        z = self.axz
        z.clear()
        z.set_title(T("close-up of the sand track (millimetre scale)"),
                    fontsize=10)
        z.add_patch(Rectangle((-2, -1.2), TRACK_LEN * 100 + 6, 4.2,
                              facecolor="#e2caa0", edgecolor="#a8865a",
                              lw=1.0, zorder=1))
        if self.var_sand.get():
            z.add_patch(Rectangle((-1.5, -0.6), TRACK_LEN * 100 + 5, 3.0,
                                  facecolor="#f0dcaa", edgecolor="none",
                                  zorder=2))
        scale(z, 0, TRACK_LEN * 100, -1.8, 0.1, 10, 1.5, origin=0.0)
        (self.ball_art2,) = z.plot([0], [0.9], "o", color="#4a4f55",
                                   markeredgecolor="#1d2124", ms=13,
                                   zorder=6, animated=True)
        (self.trail,) = z.plot([], [], "-", color="#c2a05e", lw=9,
                               alpha=0.9, zorder=3, animated=True)
        z.set_xlim(-4, TRACK_LEN * 100 + 6)
        z.set_ylim(-8.5, 6.5)
        z.set_aspect("equal")
        z.set_xticks([])
        z.set_yticks([])
        for sp in z.spines.values():
            sp.set_visible(False)

        n = self.b.track_shots
        self.lbl_track.config(
            text="" if n == 0 else
            T("%d run(s) since the track was prepared") % n
            + ("" if n < 2 else T(" - the sand is hardening")))
        self.background = None
        self.canvas.draw_idle()

    # ---------------- ball position ----------------
    def ball_xy(self):
        c_, s_ = math.cos(self.theta), math.sin(self.theta)
        if self.state in ("idle", "rolling"):
            s = (self.ell * 100 - self.x_rail * 100) if self.state == "rolling" \
                else self.ell * 100
            s = max(s, 0.0)
            return 100.0 - s * c_, s * s_ + 0.9
        return 100.0 + self.x_sand * 100, 0.9

    # ---------------- interaction ----------------
    def _press(self, ev):
        if ev.inaxes is not self.axr or ev.xdata is None:
            return
        c_, s_ = math.cos(self.theta), math.sin(self.theta)
        x_top, y_top = 100.0 - 100.0 * c_, 100.0 * s_
        if abs(ev.xdata - x_top) < 8 and abs(ev.ydata - y_top) < 10:
            self.drag = "clamp"
            return
        bx, by = self.ball_xy()
        if abs(ev.xdata - bx) < 7 and abs(ev.ydata - by) < 7:
            self.drag = "ball"

    def _motion(self, ev):
        if self.drag is None or ev.inaxes is not self.axr or ev.xdata is None:
            return
        if self.drag == "clamp":
            self.rise = float(np.clip(round(ev.ydata - 1.6), 2,
                                      ROD_H * 100 - 2)) / 100.0
            self.state = "idle"
        else:
            c_ = math.cos(self.theta)
            s = float(np.clip(round((100.0 - ev.xdata) / max(c_, 1e-6)),
                              5, 100))
            self.ell = s / 100.0
            self.state = "idle"
        self.redraw()

    def _release(self, ev):
        self.drag = None

    # ---------------- actions ----------------
    def toggle_sand(self):
        self.state = "idle"
        self.redraw()

    def prepare(self):
        self.b.prepare()
        self.state = "idle"
        self.L_final = None
        self.redraw()

    def release(self):
        self.state = "rolling"
        self.t_run = 0.0
        self.x_rail = 0.0
        self.x_sand = 0.0
        self.L_final = None

    def sw_toggle(self):
        if self.sw_run:
            self.sw_run = False
            self.btn_sw.config(text=T("Start"))
        else:
            self.sw_run = True
            self.sw_t0 = time.perf_counter() - self.sw_val
            self.btn_sw.config(text=T("Stop"))

    def sw_lap(self):
        if not self.sw_run:
            return
        self.laps.append(self.sw_val)
        prev = self.laps[-2] if len(self.laps) > 1 else 0.0
        self.lst.insert("end", "%2d  %7.2f s  (+%5.2f)"
                        % (len(self.laps), self.sw_val, self.sw_val - prev))
        self.lst.see("end")

    def sw_reset(self):
        self.sw_run = False
        self.sw_val = 0.0
        self.laps.clear()
        self.lst.delete(0, "end")
        self.btn_sw.config(text=T("Start"))

    def record(self):
        t = self.var_t.get().strip() or "-"
        L = self.var_L.get().strip() or "-"
        row = ("%.0f" % (self.rise * 100), "%.0f" % (self.ell * 100), t, L)
        self.rows.append(row)
        self.tree.insert("", "end", values=row)
        self.var_t.set("")
        self.var_L.set("")

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
                                         initialfile="Q2_rail.csv")
        if not p:
            return
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("rise_cm,l_cm,t_s,L_cm\n")
            for row in self.rows:
                fh.write(",".join(row) + "\n")

    # ---------------- loop ----------------
    def _tick(self):
        t0 = time.perf_counter()
        dt = min(t0 - self._last, 0.10)
        self._last = t0
        if self.sw_run:
            self.sw_val = t0 - self.sw_t0
        self.lbl_sw.config(text=T("%.2f s") % self.sw_val)

        if self.state == "rolling":
            acc = (5.0 / 14.0) * G * math.sin(self.theta)
            self.t_run += dt
            self.x_rail = acc * self.t_run ** 2
            if self.x_rail >= self.ell:
                self.x_rail = self.ell
                self.v_entry = math.sqrt(max(2 * acc * self.ell, 0.0))
                if self.var_sand.get():
                    self.L_final = self.b.stop_distance(self.ell, self.theta)
                    self.state = "sanding"
                    self.t_sand = 0.0
                else:
                    self.state = "stopped"
                    self.x_sand = 0.0
        elif self.state == "sanding":
            # constant deceleration over the measured stopping distance
            self.t_sand += dt
            v0 = self.v_entry
            a_dec = v0 * v0 / (2 * max(self.L_final, 1e-4))
            x = v0 * self.t_sand - 0.5 * a_dec * self.t_sand ** 2
            if x >= self.L_final or self.t_sand > v0 / max(a_dec, 1e-6):
                self.x_sand = self.L_final
                self.state = "stopped"
                if self.L_final > TRACK_LEN:
                    self.x_sand = TRACK_LEN
                    self.lbl_track.config(
                        text=T("the ball left the end of the track - "
                             "re-prepare the sand, this run is not usable"))
            else:
                self.x_sand = x

        if not self.winfo_ismapped():
            self.after(60, self._tick)
            return

        bx, by = self.ball_xy()
        self.ball_art.set_data([bx], [by])
        xs = min(self.x_sand * 100, TRACK_LEN * 100)
        self.ball_art2.set_data([xs], [0.9])
        if self.state in ("sanding", "stopped") and self.x_sand > 0:
            self.trail.set_data([0, xs], [0.6, 0.6])
        else:
            self.trail.set_data([], [])

        if self.background is None:
            self.canvas.draw()
        else:
            self.canvas.restore_region(self.background)
            self.axr.draw_artist(self.ball_art)
            self.axz.draw_artist(self.trail)
            self.axz.draw_artist(self.ball_art2)
            self.canvas.blit(self.fig.bbox)

        self.after(max(20, int(1200 * (time.perf_counter() - t0))), self._tick)


# ══════════════════════════════════════════════════════════════════
class App:
    def __init__(self, root):
        root.title(T("IPhO 2025 Q2 - Sand craters and dunes "
                   "(virtual laboratory)"))
        bench = Bench()
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        nb.add(CraterTab(nb, bench), text=T("  A - impact craters  "))
        nb.add(RailTab(nb, bench), text=T("  B - rail and sand track  "))


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
