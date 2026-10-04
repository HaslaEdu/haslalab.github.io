#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPhO 2023 (Tokyo) Q1 - Mass Measurement : virtual laboratory
=============================================================
Single file, standard library only (tkinter).  Same design rules as the
IPhO 2017 / APhO 2022-2026 simulators of this suite:

  * every part of Fig. 1 is taken out of the parts box and put to use; no
    mounting point is outlined in advance and no order is imposed beyond what
    the real parts allow (bands before the oscillator, riser before mirror...)
  * the bench shows ONLY what a real instrument shows
        - the height z is read by eye on the mm scale through the mirror
        - the amplitude A is read as the blur band on the same scale
        - currents, voltages and frequencies are read on the DMM
    no slope, no BL, no mass, no wavelength - nothing is computed for you
  * the true parameters are randomised per session and hidden

Run:  python IPhO2023_Q1_sim_KO.py   (EN edition: IPhO2023_Q1_sim_EN.py)

Official marking scheme targets (A1-1 ... A1-12):
    a = -0.51 +- 0.03 mm      b = 0.106 +- 0.005 A     c = 0.049 V/mm
    BL = 0.696 Vs/m           m = 7.5 g                k = 144 N/m
    M/k' = 9.88e-5 s^2        m/k' = 5.12e-5 s^2       M/m = 1.93
    M = 14.5 g                k' = 147 N/m
    F_AC = 0.0164 N (V'_AC = 0.157 V)                  M(D.3) = 14.9-15.1 g
"""

import math
import random
import sys

LANG = "EN"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "KO" else en


def _setup_hangul_font(root):
    """Point every named Tk font at a family that has Hangul."""
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
    import tkinter as tk
    from tkinter import ttk, messagebox
    HAS_TK = True
except Exception:                                    # headless verification
    HAS_TK = False

G0 = 9.80
DC_A_PER_V = 1.00
AC_A_PER_V = 0.106


# =====================================================================
#  1.  PHYSICS ENGINE  (no tkinter)
# =====================================================================
class Oscillator:
    """Driven mass-on-spring oscillator in the radial field of the magnets."""

    def __init__(self, seed=None):
        r = random.Random(seed)
        self.r = r
        self.M = r.uniform(14.1, 14.9) * 1e-3
        self.m = r.uniform(7.35, 7.65) * 1e-3
        self.k = r.uniform(138.0, 150.0)
        self.kp = self.k * r.uniform(1.010, 1.045)
        self.BL = r.uniform(0.680, 0.712)
        self.BpLp = self.BL * r.uniform(0.78, 0.95)
        self.df0 = r.uniform(0.26, 0.33)
        self.alpha = 4.0 * math.pi * self.M * self.df0
        self.z0_read = r.uniform(12.3, 13.2) * 1e-3      # scale reading, N=0
        self.z_e = self.z0_read + self.M * G0 / self.k
        self.gap0 = r.uniform(1.4, 6.6)                  # mm, magnet gap
        self.shim = 0                                    # shims under the support
        self.shim_mag = 0                                # shims under the magnet post
        self.lead_swapped = r.random() < 0.5             # M+/M- polarity

        # apparatus state
        self.N = 0
        self.ps_on = False
        self.mode = "DC"                                  # "DC" | "AC"
        self.m_out = None      # None | "DC" | "AC"   (M+/M- crimp wires)
        self.c_out = None      # None | "DC" | "AC"   (C+/C- crimp wires)
        self.v_dc = 0.0        # V at DCmon
        self.v_ac = 0.0        # V rms at ACmon
        self.f_coarse = 15.0
        self.f_fine = 0.0
        self.t = 0.0
        self.amp = 0.0
        self.phase = 0.0

    # ---------------- geometry / assembly ----------------
    @property
    def gap(self):
        """Distance lower magnet <-> oscillator bottom [mm] (needs 3..5)."""
        return self.gap0 + 0.8 * self.shim - 0.8 * self.shim_mag

    def gap_ok(self):
        return 3.0 <= self.gap <= 5.0

    # ---------------- electrical ----------------
    @property
    def freq(self):
        return max(0.5, self.f_coarse + self.f_fine)

    @property
    def m_tot(self):
        return self.M + self.N * self.m

    def i_dc(self):
        if not self.ps_on or self.mode != "DC":
            return 0.0
        sgn = -1.0 if self.lead_swapped else 1.0
        cur = DC_A_PER_V * self.v_dc
        return sgn * cur if self.m_out == "DC" else 0.0

    def i_ac_amp(self, coil):
        """AC current amplitude in 'main' or 'ctrl' coil [A]."""
        if not self.ps_on or self.mode != "AC":
            return 0.0
        out = self.m_out if coil == "main" else self.c_out
        if out != "AC":
            return 0.0
        return math.sqrt(2.0) * AC_A_PER_V * self.v_ac

    def force_amp(self):
        return (self.BL * self.i_ac_amp("main") +
                self.BpLp * self.i_ac_amp("ctrl"))

    # ---------------- mechanics ----------------
    def z_equilibrium(self):
        return (self.z_e - self.m_tot * G0 / self.k +
                self.BL * self.i_dc() / self.k)

    def f_res(self, N=None):
        N = self.N if N is None else N
        return math.sqrt(self.kp / (self.M + N * self.m)) / (2.0 * math.pi)

    def amp_steady(self):
        F = self.force_amp()
        if F <= 0.0:
            return 0.0
        w = 2.0 * math.pi * self.freq
        return F / math.hypot(self.kp - self.m_tot * w * w, self.alpha * w)

    def step(self, dt):
        target = self.amp_steady()
        tau = max(2.0 * self.m_tot / self.alpha, 1e-3)
        self.amp += (target - self.amp) * (1.0 - math.exp(-dt / tau))
        self.t += dt
        self.phase = (self.phase + 2.0 * math.pi * self.freq * dt) % (2 * math.pi)

    def z_now(self):
        return self.z_equilibrium() + self.amp * math.sin(self.phase)

    def emf_rms(self):
        """RMS emf induced in the MAIN coil (V' = V/sqrt2)."""
        w = 2.0 * math.pi * self.freq
        return w * self.amp * self.BL / math.sqrt(2.0)

    # ---------------- instrument models ----------------
    def dmm(self, mode, probe_hi, probe_lo):
        """
        Reading of the DMM.  mode: 'OFF'|'DCV'|'ACV'|'Hz'
        probes are terminal names; returns (text, value) - value is None
        when the reading is meaningless.
        """
        if mode == "OFF":
            return "", None
        pair = frozenset((probe_hi, probe_lo))
        if probe_hi is None or probe_lo is None or probe_hi == probe_lo:
            return ("0.000" if mode != "Hz" else "0.00"), 0.0

        def q(v, step, nd):
            v = round(v / step) * step
            return f"{v:.{nd}f}", v

        # --- monitor outputs of the power supply -------------------------
        if pair == frozenset(("DCmon", "DCGND")):
            v = abs(self.v_dc) if (self.ps_on and self.mode == "DC") else 0.0
            v += self.r.gauss(0.0, 2.5e-4)
            return q(max(v, 0.0), 1e-3, 3) if mode == "DCV" else ("0.000", 0.0)
        if pair == frozenset(("ACmon", "ACGND")):
            v = self.v_ac if (self.ps_on and self.mode == "AC") else 0.0
            if mode == "ACV":
                v += self.r.gauss(0.0, 2.5e-4)
                return q(max(v, 0.0), 1e-3, 3)
            return ("0.000", 0.0)
        if pair == frozenset(("Fmon", "ACGND")):
            if mode == "Hz":
                if not (self.ps_on and self.mode == "AC" and self.v_ac > 0.004):
                    return "0.00", 0.0
                f = self.freq + self.r.gauss(0.0, 6e-3)
                return q(f, 1e-2, 2)
            return ("0.000", 0.0)
        # --- binding posts -----------------------------------------------
        if pair == frozenset(("M+", "M-")):
            if mode == "ACV":
                if self.c_out == "AC" and self.m_out is None:
                    v = self.emf_rms() + self.r.gauss(0.0, 3e-4)
                    return q(max(v, 0.0), 1e-3, 3)
                if self.m_out == "AC":          # PS output itself
                    v = 1.06 * self.v_ac + self.r.gauss(0.0, 1e-3)
                    return q(max(v, 0.0), 1e-3, 3)
                return ("0.000", 0.0)
            if mode == "DCV":
                v = abs(self.i_dc()) * 1.9 + self.r.gauss(0.0, 5e-4)
                return q(max(v, 0.0), 1e-3, 3)
            return ("0.00", 0.0)
        if pair == frozenset(("C+", "C-")):
            if mode == "ACV" and self.c_out == "AC":
                v = 1.06 * self.v_ac + self.r.gauss(0.0, 1e-3)
                return q(max(v, 0.0), 1e-3, 3)
            return ("0.000", 0.0)
        return ("0.000" if mode != "Hz" else "0.00"), 0.0

    # --- readings used by the virtual student (verification only) -------
    def read_height_mm(self):
        return round(self.z_equilibrium() * 1e3 + self.r.gauss(0, 0.035), 1)

    def read_amp_mm(self):
        a = self.amp * 1e3
        if a < 0.05:
            return 0.0
        return max(round(a + self.r.gauss(0, 0.03), 1), 0.0)

    def truth(self):
        return dict(M=self.M, m=self.m, k=self.k, kp=self.kp, BL=self.BL,
                    df=self.df0, f0=self.f_res(0), gap=self.gap)


# =====================================================================
#  2.  drawing helpers
# =====================================================================
COL_BENCH = "#e9e5dc"
COL_WOOD = "#d9b98a"
COL_WOOD_D = "#b8946a"
COL_METAL = "#c9ccd1"
COL_METAL_D = "#8e949c"
COL_PCB = "#1f7a3f"
COL_DMM = "#c0392b"
COL_LCD = "#cfe3cf"


def rr(c, x0, y0, x1, y1, rad=6, **kw):
    """rounded rectangle"""
    pts = [x0 + rad, y0, x1 - rad, y0, x1, y0, x1, y0 + rad, x1, y1 - rad,
           x1, y1, x1 - rad, y1, x0 + rad, y1, x0, y1, x0, y1 - rad,
           x0, y0 + rad, x0, y0]
    return c.create_polygon(pts, smooth=True, **kw)


def draw_base(c, x, y, s=1.0, tag=()):
    """1. mounting base with magnet unit and 4 binding posts (Fig.1-1)."""
    f = lambda col: dict(fill=col, outline="#5b6068")
    c.create_polygon(x, y + 60 * s, x + 150 * s, y + 60 * s, x + 175 * s,
                     y + 40 * s, x + 25 * s, y + 40 * s,
                     fill=COL_METAL, outline=COL_METAL_D, tags=tag)
    c.create_rectangle(x, y + 60 * s, x + 150 * s, y + 76 * s,
                       **f(COL_METAL_D), tags=tag)
    # magnet unit (two discs on a post)
    mx, my = x + 96 * s, y + 34 * s
    c.create_rectangle(mx - 4 * s, my, mx + 4 * s, my + 16 * s,
                       **f(COL_METAL_D), tags=tag)
    c.create_oval(mx - 22 * s, my - 12 * s, mx + 22 * s, my + 2 * s,
                  **f("#7f8c8d"), tags=tag)
    c.create_oval(mx - 22 * s, my - 26 * s, mx + 22 * s, my - 12 * s,
                  **f("#95a5a6"), tags=tag)
    # binding posts M+ M- C+ C-
    for i, lb in enumerate(("M+", "M-", "C+", "C-")):
        px = x + (18 + 22 * i) * s
        c.create_rectangle(px - 6 * s, y + 22 * s, px + 6 * s, y + 60 * s,
                           **f(COL_METAL), tags=tag)
        c.create_rectangle(px - 7 * s, y + 14 * s, px + 7 * s, y + 24 * s,
                           **f("#2c3e50"), tags=tag)
        c.create_text(px, y + 68 * s, text=lb, font=("", int(7 * s)),
                      fill="#2c3e50", tags=tag)
    c.create_rectangle(x + 118 * s, y + 62 * s, x + 168 * s, y + 72 * s,
                       fill="#e67e22", outline="", tags=tag)
    c.create_text(x + 143 * s, y + 67 * s, text="WARNING",
                  font=("", int(5 * s)), fill="white", tags=tag)


def draw_support(c, x, y, s=1.0, bands=0, tag=()):
    """2. wooden support plate with the round opening + rubber bands."""
    c.create_rectangle(x, y, x + 110 * s, y + 100 * s, fill=COL_WOOD,
                       outline=COL_WOOD_D, tags=tag)
    c.create_oval(x + 25 * s, y + 22 * s, x + 85 * s, y + 82 * s,
                  fill=COL_BENCH, outline=COL_WOOD_D, tags=tag)
    for i in range(min(bands, 4)):
        if i < 2:
            xx = x + (36 + 22 * i) * s
            c.create_line(xx, y, xx, y + 100 * s, fill="#c98a3a", width=3,
                          tags=tag)
        else:
            yy = y + (36 + 22 * (i - 2)) * s
            c.create_line(x, yy, x + 110 * s, yy, fill="#c98a3a", width=3,
                          tags=tag)


def draw_oscillator(c, x, y, s=1.0, tag=(), marker=False):
    """5. cylindrical oscillator with main / control coil."""
    c.create_rectangle(x, y, x + 46 * s, y + 74 * s, fill="#f2f2ee",
                       outline="#b9b9b2", tags=tag)
    c.create_rectangle(x, y + 26 * s, x + 46 * s, y + 34 * s, fill="#3b3b3b",
                       outline="", tags=tag)      # control coil
    c.create_rectangle(x, y + 56 * s, x + 46 * s, y + 66 * s, fill="#1a1a1a",
                       outline="", tags=tag)      # main coil
    c.create_line(x + 46 * s, y + 30 * s, x + 70 * s, y + 16 * s,
                  fill="#c98a3a", width=2, smooth=True, tags=tag)
    c.create_line(x + 46 * s, y + 60 * s, x + 72 * s, y + 44 * s,
                  fill="#b35c1e", width=2, smooth=True, tags=tag)
    if marker:
        c.create_rectangle(x - 16 * s, y + 12 * s, x, y + 20 * s,
                           fill="#e8d94a", outline="#b6a92f", tags=tag)


def draw_ps(c, x, y, s=1.0, tag=()):
    """12. power supply board (green PCB, Fig.1-12)."""
    c.create_rectangle(x, y, x + 300 * s, y + 190 * s, fill=COL_PCB,
                       outline="#145c2e", width=2, tags=tag)
    for i in range(8):
        c.create_rectangle(x + (26 + 12 * i) * s, y + 44 * s,
                           x + (34 + 12 * i) * s, y + 76 * s,
                           fill="#d8d8d8", outline="#8a8a8a", tags=tag)
    for i in range(6):
        c.create_rectangle(x + (176 + 12 * i) * s, y + 44 * s,
                           x + (184 + 12 * i) * s, y + 76 * s,
                           fill="#d8d8d8", outline="#8a8a8a", tags=tag)
    c.create_rectangle(x + 150 * s, y + 96 * s, x + 178 * s, y + 120 * s,
                       fill="#111", outline="", tags=tag)
    c.create_rectangle(x + 214 * s, y + 152 * s, x + 292 * s, y + 172 * s,
                       fill="#f1c40f", outline="#b7950b", tags=tag)
    c.create_text(x + 253 * s, y + 162 * s, text="CAUTION",
                  font=("", int(7 * s), "bold"), fill="#7d6608", tags=tag)


def draw_dmm(c, x, y, s=1.0, tag=()):
    """17. digital multimeter."""
    rr(c, x, y, x + 96 * s, y + 168 * s, 10, fill=COL_DMM,
       outline="#7b241c", tags=tag)
    c.create_rectangle(x + 10 * s, y + 12 * s, x + 86 * s, y + 46 * s,
                       fill=COL_LCD, outline="#4d5b4d", tags=tag)
    c.create_oval(x + 22 * s, y + 74 * s, x + 74 * s, y + 126 * s,
                  fill="#2c2c2c", outline="#111", tags=tag)
    c.create_rectangle(x + 12 * s, y + 56 * s, x + 44 * s, y + 66 * s,
                       fill="#e67e22", outline="", tags=tag)
    c.create_rectangle(x + 52 * s, y + 56 * s, x + 84 * s, y + 66 * s,
                       fill="#2980b9", outline="", tags=tag)


def draw_weight(c, x, y, s=1.0, tag=()):
    c.create_oval(x, y, x + 26 * s, y + 26 * s, fill="#b7bcc2",
                  outline="#7f8890", width=2, tags=tag)
    c.create_oval(x + 8 * s, y + 8 * s, x + 18 * s, y + 18 * s,
                  fill=COL_BENCH, outline="#7f8890", tags=tag)


def draw_mirror(c, x, y, s=1.0, tag=()):
    c.create_polygon(x, y + 40 * s, x + 60 * s, y + 40 * s, x + 46 * s,
                     y, x + 14 * s, y, fill="#dfe6e9", outline="#95a5a6", tags=tag)


# =====================================================================
#  3.  ASSEMBLY TAB  (parts box + bench, no ghost outlines, free order)
# =====================================================================
class AssemblyTab:
    """Take each part of Fig. 1 out of the parts box and put it to use.

    Nothing is outlined in advance and no order is imposed: a part only
    refuses when the real one could not go there (an oscillator needs the
    four rubber bands, the mirror needs the riser block, ...)."""

    PARTS = [
        # key, label, count in the box
        ("support", T("2. 지지대", "2. support"), 1),
        ("band", T("6. 고무줄", "6. rubber band"), 6),
        ("osc", T("5. 원통 진동자", "5. cylindrical oscillator"), 1),
        ("screw", T("3. 나비나사 (지지대 고정)", "3. thumbscrews (fix the support)"), 1),
        ("shim", T("4. 심 → 지지대 아래 (간격 늘리기)", "4. shim -> under the support (wider gap)"), 6),
        ("shimmag", T("4. 심 → 자석 기둥 아래 (간격 줄이기)", "4. shim -> under the magnet post (narrower gap)"), 6),
        ("marker", T("7. 마커", "7. marker"), 2),
        ("riser", T("11. 라이저 블록", "11. riser block"), 1),
        ("mirror", T("10. 거울", "10. mirror"), 1),
        ("holder", T("13. 건전지 홀더", "13. battery holder"), 2),
        ("batt", T("14. 건전지", "14. battery"), 8),
        ("leads", T("코일 리드선 → 바인딩 포스트", "coil leads -> binding posts"), 1),
        ("ps", T("12. 전원공급장치 (PS)", "12. power supply (PS)"), 1),
        ("crimp", T("15. U자 압착 단자선", "15. U-shaped crimp terminal wires"), 1),
        ("clip", T("16. 악어클립 선", "16. alligator clip wires"), 1),
        ("dmm", T("17. 디지털 멀티미터", "17. digital multimeter"), 1),
        ("weights", T("8. 추 · 9. 핀셋", "8. weights · 9. tweezers"), 1),
    ]

    def __init__(self, master, app):
        self.app = app
        self.sim = app.sim
        self.n = {k: 0 for k, _, _ in self.PARTS}      # how many are out of the box
        self.fixed = False                              # support screwed onto the base
        self.frame = ttk.Frame(master)
        left = ttk.Frame(self.frame, padding=6)
        left.pack(side="left", fill="y")
        ttk.Label(left, text=T("부품함 - 클릭하면 꺼내서 씁니다",
                               "parts box - click to take a part out and use it"),
                  font=("", 10, "bold")).pack(anchor="w", pady=(0, 6))
        self.btn = {}
        for key, lab, cnt in self.PARTS:
            b = ttk.Button(left, text="", width=40, command=lambda k=key: self.take(k))
            b.pack(anchor="w", pady=1)
            self.btn[key] = b
        row = ttk.Frame(left)
        row.pack(anchor="w", pady=(8, 2))
        ttk.Button(row, text=T("심 하나 빼기", "remove a shim"),
                   command=self.unshim).pack(side="left")
        ttk.Button(row, text=T("자로 간격 재기", "measure the gap with a ruler"),
                   command=self.measure_gap).pack(side="left", padx=4)
        self.msg = ttk.Label(left, text="", wraplength=330, justify="left",
                             foreground="#2c3e50")
        self.msg.pack(anchor="w", pady=8)
        self.c = tk.Canvas(self.frame, width=820, height=560, bg=COL_BENCH,
                           highlightthickness=0)
        self.c.pack(side="left", fill="both", expand=True)
        self.redraw()

    # ------------------------------------------------------------------
    def say(self, s):
        self.msg.config(text=s)

    def take(self, k):
        s, n = self.sim, self.n
        cnt = dict((a, c) for a, _, c in self.PARTS)[k]
        if n[k] >= cnt:
            self.say(T("부품함에 더 없습니다.", "There are no more in the box."))
            return
        if k == "band":
            if not n["support"]:
                self.say(T("고무줄은 지지대에 감습니다 - 지지대를 먼저 꺼내세요.",
                           "The bands go round the support - take it out first."))
                return
            if self.fixed:
                self.say(T("지지대가 베이스에 고정되어 있어 감을 수 없습니다.",
                           "The support is screwed onto the base - it cannot be wrapped now."))
                return
            if n["band"] >= 4:
                self.say(T("격자 모양으로 감는 고무줄은 네 개입니다 (나머지는 예비).",
                           "Four bands make the grid; the others are spares."))
                return
        if k == "osc":
            if n["band"] < 4:
                self.say(T("진동자는 고무줄 네 개가 만든 네모 구멍에 끼웁니다.",
                           "The oscillator goes into the square opening of the four bands."))
                return
            if self.fixed:
                self.say(T("지지대를 고정하기 전에 끼우세요.",
                           "Put it in before the support is screwed down."))
                return
        if k == "screw":
            if not n["support"]:
                self.say(T("고정할 지지대가 없습니다.", "There is no support to fix."))
                return
            self.fixed = True
        if k in ("shim", "shimmag") and n["shim"] + n["shimmag"] >= 6:
            self.say(T("심은 여섯 개뿐입니다.", "There are only six shims."))
            return
        if k == "shimmag":
            if not n["support"]:
                self.say(T("자석 기둥을 돌려 빼려면 지지대를 먼저 베이스에서 떼어 놓으세요.",
                           "Take the support off the base before turning the magnet post out."))
                return
            s.shim_mag += 1
        if k == "shim":
            if not self.fixed:
                self.say(T("심은 지지대와 바인딩 포스트 사이에 넣습니다 - 지지대를 먼저 고정하세요.",
                           "Shims go between the binding posts and the support - fix the support first."))
                return
            s.shim += 1
        if k == "marker":
            if not n["osc"]:
                self.say(T("마커는 진동자의 작은 선반에 붙입니다.",
                           "The marker is glued to the little shelf of the oscillator."))
                return
            if n["marker"] >= 1:
                self.say(T("마커는 하나면 됩니다 (하나는 예비).", "One marker is enough (the other is a spare)."))
                return
        if k == "mirror" and not n["riser"]:
            self.say(T("거울은 라이저 블록 위에 세웁니다.", "The mirror stands on the riser block."))
            return
        if k == "batt" and n["batt"] >= 4 * n["holder"]:
            self.say(T("건전지를 넣을 홀더가 없습니다.", "There is no holder to put it in."))
            return
        if k == "leads":
            if not (self.fixed and n["osc"]):
                self.say(T("진동자의 리드선은 지지대를 고정한 뒤 바인딩 포스트의 아래쪽 틈에 끼웁니다.",
                           "The coil leads go into the lower gaps of the binding posts once the support is fixed."))
                return
        if k in ("crimp", "clip") and not n["ps"]:
            self.say(T("먼저 전원공급장치를 꺼내세요.", "Take the power supply out first."))
            return
        n[k] += 1
        self.say(self._done_text(k))
        if self.complete():
            self.app.on_assembled()
        self.redraw()

    def _done_text(self, k):
        return {
            "support": T("지지대를 베이스에서 떼어 실험대에 놓았습니다.", "Support off the base and on the bench."),
            "band": T("고무줄을 지지대에 감았습니다.", "Rubber band wrapped round the support."),
            "osc": T("진동자를 고무줄 사이에 끼우고 고리 여덟 개에 걸었습니다.",
                     "Oscillator in the bands, hung on the eight little hooks."),
            "screw": T("나비나사로 지지대를 대각선으로 고정했습니다.", "Support screwed diagonally onto the posts."),
            "shim": T("심을 지지대와 바인딩 포스트 사이에 하나 넣었습니다.", "One shim between the posts and the support."),
            "shimmag": T("자석 기둥을 돌려 빼고 그 아래에 심을 하나 넣었습니다.", "Magnet post turned out, one shim under it."),
            "marker": T("마커를 진동자의 선반에 붙였습니다.", "Marker glued to the shelf."),
            "riser": T("라이저 블록을 놓았습니다.", "Riser block put down."),
            "mirror": T("거울을 라이저 블록 위에 세웠습니다.", "Mirror set on the riser block."),
            "holder": T("건전지 홀더를 놓았습니다.", "Battery holder put down."),
            "batt": T("건전지를 넣었습니다.", "Battery put in."),
            "leads": T("주 코일(M)과 제어 코일(C)의 리드선을 바인딩 포스트에 끼웠습니다.",
                       "Main (M) and control (C) coil leads in the binding posts."),
            "ps": T("전원공급장치를 놓고 건전지 홀더를 CN1, CN2에 연결했습니다.",
                    "Power supply down, battery holders on CN1 and CN2."),
            "crimp": T("U자 단자선을 꺼냈습니다 (연결은 실험대에서).", "Crimp wires out (connect them on the bench)."),
            "clip": T("악어클립 선을 꺼냈습니다 (DMM 연결은 실험대에서).", "Alligator wires out (connect the DMM on the bench)."),
            "dmm": T("멀티미터를 꺼냈습니다.", "Multimeter out."),
            "weights": T("추와 핀셋을 꺼냈습니다.", "Weights and tweezers out."),
        }[k]

    def unshim(self):
        if self.sim.shim > 0:
            self.sim.shim -= 1
            self.n["shim"] -= 1
            self.say(T("심을 하나 뺐습니다.", "One shim taken out."))
        elif self.sim.shim_mag > 0:
            self.sim.shim_mag -= 1
            self.n["shimmag"] -= 1
            self.say(T("자석 기둥 아래의 심을 하나 뺐습니다.", "One shim taken out from under the magnet post."))
        self.redraw()
        if self.complete():
            self.app.on_assembled()

    def measure_gap(self):
        """What a ruler held next to the magnet shows - to the nearest half millimetre."""
        if not (self.fixed and self.n["osc"]):
            self.say(T("진동자를 단 지지대가 베이스에 고정되어야 잴 수 있습니다.",
                       "Fix the support with the oscillator on the base first."))
            return
        g = round((self.sim.gap + self.sim.r.gauss(0, 0.15)) * 2) / 2
        self.say(T("자로 재니 아래 자석 윗면과 진동자 아랫면 사이가 약 %.1f mm입니다.",
                   "The ruler shows about %.1f mm between the lower magnet and the oscillator.") % g)

    def complete(self):
        n = self.n
        return (self.fixed and n["band"] >= 4 and n["osc"] and n["marker"] and n["riser"]
                and n["mirror"] and n["holder"] >= 2 and n["batt"] >= 8 and n["leads"]
                and n["ps"] and n["crimp"] and n["clip"] and n["dmm"] and n["weights"]
                and self.sim.gap_ok())

    # ------------------------------------------------------------------
    def redraw(self):
        c, n = self.c, self.n
        c.delete("all")
        for key, lab, total in self.PARTS:
            left = total - n[key]
            self.btn[key].config(text=f"{lab}   ({T('남음', 'left')} {left})")
        draw_base(c, 330, 300, 1.2)
        if n["support"]:
            if self.fixed:
                draw_support(c, 320, 240, 1.0, bands=n["band"])
                if n["osc"]:
                    draw_oscillator(c, 368, 233, 1.0, marker=bool(n["marker"]))
                for i in range(self.sim.shim):
                    c.create_rectangle(338, 336 - 3 * i, 356, 339 - 3 * i, fill="#bfc4ca", outline="#7f868e")
            else:
                draw_support(c, 320, 60, 1.0, bands=n["band"])
                if n["osc"]:
                    draw_oscillator(c, 368, 53, 1.0, marker=bool(n["marker"]))
        if n["riser"]:
            c.create_rectangle(170, 330, 250, 360, fill=COL_WOOD, outline=COL_WOOD_D)
        if n["mirror"]:
            draw_mirror(c, 180, 292, 1.1)
        for i in range(n["holder"]):
            c.create_rectangle(600 + 52 * i, 60, 642 + 52 * i, 128, fill="#2c3e50", outline="#1b2631")
            for j in range(min(4, n["batt"] - 4 * i)):
                c.create_rectangle(604 + 52 * i, 66 + 15 * j, 638 + 52 * i, 77 + 15 * j,
                                   fill="#34495e", outline="#95a5a6")
        if n["ps"]:
            draw_ps(c, 560, 160, 0.75)
            for i in range(n["holder"]):
                c.create_line(621 + 52 * i, 128, 600 + 40 * i, 178, fill="#c0392b", width=2)
        if n["leads"]:
            c.create_line(387, 315, 352, 336, fill="#c98a3a", width=2)
            c.create_line(420, 315, 404, 336, fill="#b35c1e", width=2)
        if n["crimp"]:
            c.create_line(560, 430, 640, 430, fill="#7f8c8d", width=4)
            c.create_line(560, 442, 640, 442, fill="#7f8c8d", width=4)
        if n["clip"]:
            c.create_line(560, 470, 640, 462, fill="#c0392b", width=3)
            c.create_line(560, 482, 640, 474, fill="#2c3e50", width=3)
        if n["dmm"]:
            draw_dmm(c, 690, 360, 0.8)
        if n["weights"]:
            for i in range(5):
                draw_weight(c, 60 + 32 * i, 470, 1.0)
            c.create_line(60, 510, 150, 520, fill="#7f8c8d", width=3)
        if self.complete():
            c.create_text(410, 540, text=T("조립 완료 - 실험대 탭으로 가세요", "assembled - go to the bench tab"),
                          font=("", 11, "bold"), fill="#1e8449")


# =====================================================================
#  4.  BENCH TAB
# =====================================================================
class Knob:
    """A rotary knob drawn on a canvas; vertical drag or wheel changes it."""

    def __init__(self, canvas, x, y, r, label, lo, hi, value, cb, fmt=None):
        self.c, self.x, self.y, self.r = canvas, x, y, r
        self.label, self.lo, self.hi = label, lo, hi
        self.value, self.cb, self.fmt = value, cb, fmt
        self.items = []
        self.draw()

    def draw(self):
        c = self.c
        for i in self.items:
            c.delete(i)
        self.items = []
        frac = (self.value - self.lo) / (self.hi - self.lo)
        ang = math.radians(135 + 270 * frac)
        self.items.append(c.create_oval(self.x - self.r, self.y - self.r,
                                        self.x + self.r, self.y + self.r,
                                        fill="#2f3640", outline="#dcdde1",
                                        width=2))
        self.items.append(c.create_line(
            self.x, self.y, self.x + self.r * 0.82 * math.cos(ang),
            self.y + self.r * 0.82 * math.sin(ang), fill="#f5f6fa", width=3))
        self.items.append(c.create_text(self.x, self.y + self.r + 10,
                                        text=self.label, font=("", 8),
                                        fill="#dfe6e9"))

    def hit(self, ex, ey):
        return (ex - self.x) ** 2 + (ey - self.y) ** 2 <= (self.r + 6) ** 2

    def bump(self, d):
        span = self.hi - self.lo
        self.value = min(self.hi, max(self.lo, self.value + d * span))
        self.draw()
        self.cb(self.value)


class BenchTab:
    TERMS = {                       # terminal -> (x, y) on the bench canvas
        "DCmon": (214, 470), "DCGND": (262, 470),
        "ACmon": (58, 470), "ACGND": (106, 470), "Fmon": (154, 470),
        "M+": (720, 470), "M-": (752, 470), "C+": (784, 470), "C-": (816, 470),
    }

    def __init__(self, master, app):
        self.app = app
        self.sim = app.sim
        self.frame = ttk.Frame(master)
        bar = ttk.Frame(self.frame, padding=4)
        bar.pack(fill="x")
        self.lbl_state = ttk.Label(bar, text="", font=("", 9))
        self.lbl_state.pack(side="left")
        self.var_slow = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text=T("슬로모션(1/20)", "slow motion (1/20)"),
                        variable=self.var_slow).pack(side="right")
        self.c = tk.Canvas(self.frame, width=1160, height=690, bg="#20252b",
                           highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        self.knobs = []
        self.dmm_mode = "OFF"
        self.probe = {"hi": None, "lo": None}
        self.drag_probe = None
        self.weights_on = 0
        self.static_done = False
        self.ruler_drawn = False
        self.c.bind("<ButtonPress-1>", self.on_press)
        self.c.bind("<B1-Motion>", self.on_move)
        self.c.bind("<ButtonRelease-1>", self.on_release)
        self.c.bind("<MouseWheel>", self.on_wheel)
        self.c.bind("<Button-4>", lambda e: self.on_wheel(e, 1))
        self.c.bind("<Button-5>", lambda e: self.on_wheel(e, -1))
        self.build_static()

    # ---------------- static parts (knobs etc.) ----------------
    def build_static(self):
        c = self.c
        s = self.sim
        self.knobs = [
            Knob(c, 60, 560, 20, T("Coarse", "Coarse"), 5.0, 25.0,
                 s.f_coarse, self.set_fc),
            Knob(c, 118, 560, 20, T("Fine", "Fine"), -0.6, 0.6,
                 s.f_fine, self.set_ff),
            Knob(c, 186, 560, 20, "AC Vol.", 0.0, 0.40, s.v_ac, self.set_vac),
            Knob(c, 258, 560, 20, "DC Vol.", 0.0, 1.20, s.v_dc, self.set_vdc),
        ]
        self.static_done = True

    def set_fc(self, v):
        self.sim.f_coarse = v

    def set_ff(self, v):
        self.sim.f_fine = v

    def set_vac(self, v):
        self.sim.v_ac = v

    def set_vdc(self, v):
        self.sim.v_dc = v

    # ---------------- interaction ----------------
    def on_press(self, e):
        for k in self.knobs:
            if k.hit(e.x, e.y):
                self.drag_probe = ("knob", k, e.y)
                return
        # DMM rotary selector
        for i, m in enumerate(("OFF", "DCV", "ACV", "Hz")):
            bx, by = 980, 300 + 26 * i
            if abs(e.x - bx) < 40 and abs(e.y - by) < 12:
                self.dmm_mode = m
                return
        # probes
        for key in ("hi", "lo"):
            px, py = self.probe_xy(key)
            if (e.x - px) ** 2 + (e.y - py) ** 2 < 150:
                self.drag_probe = ("probe", key, None)
                return
        # PS switches
        if 30 <= e.x <= 90 and 620 <= e.y <= 646:
            self.sim.ps_on = not self.sim.ps_on
            return
        if 110 <= e.x <= 170 and 620 <= e.y <= 646:
            self.sim.mode = "AC" if self.sim.mode == "DC" else "DC"
            return
        # crimp-wire routing buttons (physically re-plugging the wires)
        for i, (lab, coil, out) in enumerate(
                ((T("M -> DC", "M -> DC"), "m", "DC"),
                 (T("M -> AC", "M -> AC"), "m", "AC"),
                 (T("M 분리", "M off"), "m", None),
                 (T("C -> AC", "C -> AC"), "c", "AC"),
                 (T("C 분리", "C off"), "c", None))):
            bx, by = 640 + 100 * (i % 3), 600 + 30 * (i // 3)
            if abs(e.x - bx) < 46 and abs(e.y - by) < 13:
                if coil == "m":
                    self.sim.m_out = out
                else:
                    self.sim.c_out = out
                return
        # weights
        if 900 <= e.x <= 1140 and 560 <= e.y <= 660:
            idx = (e.x - 900) // 40
            if 0 <= idx < 5:
                self.sim.N = int(idx) + 1 if self.sim.N != int(idx) + 1 else int(idx)
            return
        # polarity swap
        if 700 <= e.x <= 840 and 500 <= e.y <= 524:
            self.sim.lead_swapped = not self.sim.lead_swapped
            return

    def on_move(self, e):
        if not self.drag_probe:
            return
        kind = self.drag_probe[0]
        if kind == "knob":
            _, k, y0 = self.drag_probe
            k.bump((y0 - e.y) * 0.004)
            self.drag_probe = ("knob", k, e.y)
        else:
            self._probe_pos = (e.x, e.y)
            self.probe[self.drag_probe[1] + "_xy"] = (e.x, e.y)

    def on_release(self, e):
        if self.drag_probe and self.drag_probe[0] == "probe":
            key = self.drag_probe[1]
            best, bd = None, 1e9
            for name, (tx, ty) in self.TERMS.items():
                d = (e.x - tx) ** 2 + (e.y - ty) ** 2
                if d < bd:
                    best, bd = name, d
            self.probe[key] = best if bd < 900 else None
            self.probe.pop(key + "_xy", None)
        self.drag_probe = None

    def on_wheel(self, e, direction=None):
        d = direction if direction is not None else (1 if e.delta > 0 else -1)
        for k in self.knobs:
            if k.hit(e.x, e.y):
                k.bump(0.01 * d)
                return

    def probe_xy(self, key):
        if key + "_xy" in self.probe:
            return self.probe[key + "_xy"]
        t = self.probe.get(key)
        if t:
            return self.TERMS[t]
        return (1030, 470) if key == "hi" else (1070, 470)

    # ---------------- per-frame drawing ----------------
    def tick(self, dt):
        s = self.sim
        s.step(dt / (20.0 if self.var_slow.get() else 1.0)
               if self.var_slow.get() else dt)
        self.draw()

    def draw(self):
        c = self.c
        s = self.sim
        c.delete("dyn")
        if not self.static_done:
            return
        c.delete("bg")
        # --- bench background
        c.create_rectangle(0, 0, 1160, 690, fill="#20252b", outline="",
                           tags="bg")
        c.tag_lower("bg")
        # --- power supply board
        c.create_rectangle(20, 430, 300, 660, fill=COL_PCB, outline="#145c2e",
                           width=2, tags="dyn")
        c.create_text(160, 442, text="POWER SUPPLY", font=("", 9, "bold"),
                      fill="#d5f5e3", tags="dyn")
        for name in ("ACmon", "ACGND", "Fmon", "DCmon", "DCGND"):
            x, y = self.TERMS[name]
            c.create_oval(x - 7, y - 7, x + 7, y + 7, fill="#111",
                          outline="#bdc3c7", tags="dyn")
            c.create_text(x, y - 16, text=name, font=("", 7), fill="#d5f5e3",
                          tags="dyn")
        c.create_rectangle(30, 620, 90, 646,
                           fill="#27ae60" if s.ps_on else "#7f8c8d",
                           outline="#145c2e", tags="dyn")
        c.create_text(60, 633, text="ON" if s.ps_on else "OFF",
                      font=("", 9, "bold"), fill="white", tags="dyn")
        c.create_rectangle(110, 620, 170, 646, fill="#2980b9",
                           outline="#1b4f72", tags="dyn")
        c.create_text(140, 633, text=s.mode, font=("", 9, "bold"),
                      fill="white", tags="dyn")
        for k in self.knobs:
            k.draw()

        # --- oscillator + scale + mirror -------------------------------
        self.draw_oscillator_view()

        # --- binding posts ----------------------------------------------
        c.create_rectangle(690, 440, 850, 500, fill=COL_METAL,
                           outline=COL_METAL_D, tags="dyn")
        for name in ("M+", "M-", "C+", "C-"):
            x, y = self.TERMS[name]
            c.create_oval(x - 8, y - 8, x + 8, y + 8, fill="#2c3e50",
                          outline="#ecf0f1", tags="dyn")
            c.create_text(x, y + 18, text=name, font=("", 7), fill="#2c3e50",
                          tags="dyn")
        c.create_rectangle(700, 500, 840, 524, fill="#34495e", outline="",
                           tags="dyn")
        c.create_text(770, 512, text=T("M+/M- 극성 바꾸기", "swap M+/M- leads"),
                      font=("", 8), fill="#ecf0f1", tags="dyn")
        for i, (lab, coil, out) in enumerate(
                ((T("M → DC", "M -> DC"), "m", "DC"),
                 (T("M → AC", "M -> AC"), "m", "AC"),
                 (T("M 분리", "M off"), "m", None),
                 (T("C → AC", "C -> AC"), "c", "AC"),
                 (T("C 분리", "C off"), "c", None))):
            bx, by = 640 + 100 * (i % 3), 600 + 30 * (i // 3)
            cur = (s.m_out if coil == "m" else s.c_out) == out
            c.create_rectangle(bx - 46, by - 13, bx + 46, by + 13,
                               fill="#16a085" if cur else "#34495e",
                               outline="#1abc9c", tags="dyn")
            c.create_text(bx, by, text=lab, font=("", 8), fill="white",
                          tags="dyn")

        # --- DMM ---------------------------------------------------------
        c.create_rectangle(930, 230, 1110, 500, fill=COL_DMM,
                           outline="#7b241c", width=2, tags="dyn")
        c.create_rectangle(946, 246, 1094, 290, fill=COL_LCD,
                           outline="#4d5b4d", tags="dyn")
        txt, _ = s.dmm(self.dmm_mode, self.probe.get("hi"), self.probe.get("lo"))
        unit = {"DCV": "V", "ACV": "V", "Hz": "Hz", "OFF": ""}[self.dmm_mode]
        c.create_text(1086, 268, text=f"{txt} {unit}", anchor="e",
                      font=("Consolas", 17, "bold"), fill="#1c2833", tags="dyn")
        for i, m in enumerate(("OFF", "DCV", "ACV", "Hz")):
            bx, by = 980, 300 + 26 * i
            c.create_rectangle(bx - 40, by - 12, bx + 40, by + 12,
                               fill="#2c3e50" if self.dmm_mode == m else "#7f2b22",
                               outline="#ecf0f1", tags="dyn")
            c.create_text(bx, by, text=m, font=("", 9), fill="white",
                          tags="dyn")
        for key, col in (("hi", "#c0392b"), ("lo", "#2c3e50")):
            px, py = self.probe_xy(key)
            c.create_line(1050 if key == "hi" else 1070, 420, px, py,
                          fill=col, width=2, smooth=True, tags="dyn")
            c.create_oval(px - 5, py - 5, px + 5, py + 5, fill=col,
                          outline="#ecf0f1", tags="dyn")

        # --- weights tray -------------------------------------------------
        c.create_text(1020, 545, text=T("추 (부품 8) - 클릭해서 올리기/내리기",
                                        "weights (8) - click to add/remove"),
                      font=("", 8), fill="#dfe6e9", tags="dyn")
        for i in range(5):
            x = 900 + 40 * i
            on = i < s.N
            c.create_oval(x + 6, 590, x + 32, 616,
                          fill="#7f8c8d" if on else "#b7bcc2",
                          outline="#5d6d7e", width=2, tags="dyn")
            c.create_oval(x + 14, 598, x + 24, 608, fill="#20252b",
                          outline="#5d6d7e", tags="dyn")
        c.create_text(1020, 640, text=f"N = {s.N}", font=("", 11, "bold"),
                      fill="#f5f6fa", tags="dyn")

        self.lbl_state.config(text=T(
            "PS %s / %s   M단자: %s   C단자: %s   DMM: %s",
            "PS %s / %s   M posts: %s   C posts: %s   DMM: %s") % (
            "ON" if s.ps_on else "OFF", s.mode, s.m_out or "-",
            s.c_out or "-", self.dmm_mode))

    # ------------------------------------------------------------------
    def _ruler_ticks(self, x0, y0, h, mm2px, z_top):
        c = self.c
        n = int(z_top * 10)
        for i in range(n + 1):
            mm = z_top - i / 10.0
            y = y0 + (z_top - mm) * mm2px
            if y < y0 or y > y0 + h:
                continue
            t = round(mm * 10)
            if t % 10 == 0:
                c.create_line(x0, y, x0 + 30, y, fill="#2c3e50", width=2,
                              tags="ruler")
                c.create_text(x0 + 36, y, text=f"{mm:.0f}", anchor="w",
                              font=("", 9), fill="#2c3e50", tags="ruler")
            elif t % 5 == 0:
                c.create_line(x0, y, x0 + 20, y, fill="#2c3e50", tags="ruler")
            else:
                c.create_line(x0, y, x0 + 10, y, fill="#7f8c8d", tags="ruler")

    def draw_oscillator_view(self):
        """Ruler + marker + mirror image; the student reads z and A here."""
        c = self.c
        s = self.sim
        x0, y0 = 380, 60           # top-left of the scale view
        h = 330                     # px height of the ruler
        mm2px = 22.0                # zoom of the scale (0.1 mm readable)
        z_top = 16.0                # mm at the top of the ruler
        if not self.ruler_drawn:    # the ruler itself never moves
            self.ruler_drawn = True
            c.create_rectangle(x0 - 250, y0 - 30, x0 + 200, y0 + h + 40,
                               fill="#11151a", outline="#3d444d", tags="ruler")
            c.create_text(x0 - 25, y0 - 16, text=T(
                "거울을 통해 본 마커와 눈금자 (1 mm 눈금)",
                "marker and scale seen through the mirror (1 mm graduations)"),
                font=("", 9), fill="#95a5a6", tags="ruler")
            c.create_rectangle(x0, y0, x0 + 54, y0 + h, fill="#f0e6c8",
                               outline="#c8b98a", tags="ruler")
            self._ruler_ticks(x0, y0, h, mm2px, z_top)
            c.create_text(x0 + 150, y0 + h + 20, anchor="e", font=("", 8),
                          fill="#7f8c8d", tags="ruler",
                          text=T("눈금은 0.1 mm까지 눈대중으로 읽으세요",
                                 "estimate the reading to 0.1 mm by eye"))
        # marker: rest position + blur band of the oscillation
        zeq = s.z_equilibrium() * 1e3
        amp = s.amp * 1e3
        yc = y0 + (z_top - zeq) * mm2px
        bx0, bx1 = x0 - 78, x0 - 4        # the marker sticks out to the scale
        if amp > 0.05:
            if self.var_slow.get():
                yy = y0 + (z_top - s.z_now() * 1e3) * mm2px
                c.create_rectangle(bx0, yy - 3, bx1, yy + 3, fill="#e8d94a",
                                   outline="#b6a92f", tags="dyn")
            else:
                y1 = y0 + (z_top - (zeq + amp)) * mm2px
                y2 = y0 + (z_top - (zeq - amp)) * mm2px
                c.create_rectangle(bx0, y1, bx1, y2, fill="#e8d94a",
                                   outline="", stipple="gray25", tags="dyn")
                for yy in (y1, y2):
                    c.create_line(bx0, yy, bx1, yy, fill="#f7dc6f", width=2,
                                  tags="dyn")
        else:
            c.create_rectangle(bx0, yc - 3, bx1, yc + 3, fill="#e8d94a",
                               outline="#b6a92f", tags="dyn")
        # oscillator body, left of the marker
        c.create_rectangle(x0 - 216, yc - 46, x0 - 84, yc + 46,
                           fill="#f2f2ee", outline="#b9b9b2", tags="dyn")
        c.create_rectangle(x0 - 216, yc + 8, x0 - 84, yc + 20, fill="#3b3b3b",
                           outline="", tags="dyn")
        c.create_rectangle(x0 - 216, yc + 34, x0 - 84, yc + 46, fill="#1a1a1a",
                           outline="", tags="dyn")
        c.create_text(x0 - 150, yc - 60, text=T("진동자", "oscillator"),
                      font=("", 8), fill="#7f8c8d", tags="dyn")
        # magnet unit: fixed in space, the main coil rides between the discs
        ym = y0 + (z_top - s.z0_read * 1e3) * mm2px + 40
        c.create_rectangle(x0 - 236, ym - 26, x0 - 64, ym - 14,
                           fill="#8e949c", outline="#5d6d7e", tags="dyn")
        c.create_rectangle(x0 - 236, ym + 14, x0 - 64, ym + 26,
                           fill="#8e949c", outline="#5d6d7e", tags="dyn")
        c.create_text(x0 - 150, ym + 40, text=T("자석 유닛", "magnet unit"),
                      font=("", 8), fill="#7f8c8d", tags="dyn")


# =====================================================================
#  5.  APP
# =====================================================================
INFO = T("""[장비 목록 - 문제지 Fig. 1]
 1 마운팅 베이스(자석 유닛, M+/M-/C+/C- 바인딩 포스트)
 2 지지대   3 나비나사[2]   4 심(와셔)[6]   5 원통 진동자
 6 고무줄[6]   7 마커[2]   8 추[5]   9 핀셋   10 거울   11 라이저 블록
 12 전원공급장치(PS)  13 건전지 홀더[2]  14 건전지[8]
 15 U자 압착 단자선[2]  16 악어클립 선[2]  17 디지털 멀티미터(DMM)

[변환 계수]
 DC 모드: 정전류원, I = 1.00 A/V x V(DCmon-DC GND)
 AC 모드: 전압원,   I = 0.106 A/V x V(ACmon-AC GND), DMM ACV는 실효값
 주파수는 Fmon-AC GND에서 Hz 모드로 읽습니다.
 g = 9.80 m/s^2 을 사용하세요.

[측정 원칙]
 이 시뮬레이터는 계기가 보여주는 것만 보여줍니다.
 z와 A는 눈금자에서 직접 읽고, 기울기/BL/질량 등은 직접 계산하세요.

[주의] 코일과 자석은 뜨거워질 수 있습니다. 각 단계가 끝나면
 DC 출력을 최소로 내리세요.""",
"""[Parts - Fig. 1 of the problem sheet]
 1 mounting base (magnet unit, binding posts M+/M-/C+/C-)
 2 support   3 thumbscrews[2]   4 shims[6]   5 cylindrical oscillator
 6 rubber bands[6]  7 markers[2]  8 weights[5]  9 tweezers  10 mirror
 11 riser block  12 power supply (PS)  13 battery holders[2]
 14 batteries[8]  15 U-crimp terminal wires[2]  16 alligator wires[2]
 17 digital multimeter (DMM)

[Conversion factors]
 DC mode: constant-current source, I = 1.00 A/V x V(DCmon-DC GND)
 AC mode: voltage source, I = 0.106 A/V x V(ACmon-AC GND); ACV reads RMS
 read the frequency at Fmon-AC GND in Hz mode.  Use g = 9.80 m/s^2.

[Measurement policy]
 The simulator shows only what a real instrument shows.  Read z and A
 yourself on the scale; all slopes, BL and masses are yours to compute.

[Caution] Coils and magnets get hot.  Turn the DC output down to the
 minimum at the end of each step.""")


class App:
    def __init__(self, root, seed=None):
        self.root = root
        root.title(T("IPhO 2023 Q1 질량 측정 - 가상 실험실",
                     "IPhO 2023 Q1 Mass Measurement - Virtual Lab"))
        self.sim = Oscillator(seed)
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        self.asm = AssemblyTab(nb, self)
        self.bench = BenchTab(nb, self)
        info = ttk.Frame(nb)
        txt = tk.Text(info, font=("Consolas", 10), wrap="word")
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", INFO)
        txt.config(state="disabled")
        nb.add(self.asm.frame, text=T("1. 조립", "1. Assembly"))
        nb.add(self.bench.frame, text=T("2. 실험대", "2. Bench"))
        nb.add(info, text=T("3. 장비 안내", "3. Equipment"))
        self.nb = nb
        self.bench_enabled = False
        nb.tab(1, state="disabled")
        self.dt = 0.04
        self.tick()

    def on_assembled(self):
        if not self.bench_enabled:
            self.bench_enabled = True
            self.nb.tab(1, state="normal")
            messagebox.showinfo(
                T("조립 완료", "assembly complete"),
                T("실험대 탭이 열렸습니다.\n먼저 M+/M-를 DC 출력에 연결하고 "
                  "DC Vol을 올려 진동자가 위로 움직이는지 확인하세요.\n"
                  "아래로 움직이면 극성을 바꾸세요.",
                  "The bench tab is now open.\nFirst connect M+/M- to the DC "
                  "output and check that the oscillator moves UP.\n"
                  "If it moves down, swap the leads."))

    def tick(self):
        try:
            if self.nb.index(self.nb.select()) == 1:
                self.bench.tick(self.dt)
            else:
                self.sim.step(self.dt)
        except Exception:
            pass
        try:
            if self.root.winfo_exists():
                self.root.after(int(self.dt * 1000), self.tick)
        except Exception:
            pass


def main():
    if not HAS_TK:
        print("tkinter is required")
        return 1
    root = tk.Tk()
    _setup_hangul_font(root)
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
