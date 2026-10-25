#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OPhO 2026 #22 — Einstein Ring
A virtual camera looking down (z) on a transparent unit sphere doped with fluorescent dye.

Same model as the HaslaLab browser version:
    UV enters through the hemispherical indent at the top and is bent by
        theta0 = asin(b') - asin(b'/n_u)          (b' uniform over the indent's disc)
    only photons with sin(theta0) > 1/n_u stay trapped; their absorption points have
        P(r) = g(r) / (2 pi r^2 sin(theta))       (official solution)
    the brightness at image radius b integrates P along the refracted ray traced back
    from the camera; the indent size eps cuts off the 1/sin(theta) divergence on the axis.

The sphere of the problem has n_b = 1.900, n_u = 1.45; it is hidden on the first tab.

    python opho2026_22_ring_sim.py
"""

import math, random
import tkinter as tk
from tkinter import ttk

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
matplotlib.rcParams["font.family"] = ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

LANG = "EN"

TXT = {
 "KO": dict(title="OPhO 2026 #22 — 아인슈타인 고리", tabs=("카메라 (문제의 구)", "탐색 (n 직접 설정)"),
            nb="n_b (파란빛)", nu="n_u (자외선)", expo="노출 (상대)", shoot="사진 찍기", rnd="다른 구로 바꾸기",
            hidden="이 구의 n_b, n_u는 숨겨져 있습니다.\n고리의 안쪽·바깥쪽 반지름에서 구하세요.",
            prof="방위각 평균 밝기 I(b)", read="사진 위를 움직이면 b와 밝기가 나옵니다. 클릭하면 b를 기록합니다.",
            picked="기록한 b: ", clear="기록 지우기"),
 "EN": dict(title="OPhO 2026 #22 — Einstein Ring", tabs=("Camera (the problem's sphere)", "Explore (set n yourself)"),
            nb="n_b (blue)", nu="n_u (UV)", expo="exposure (rel.)", shoot="take the picture", rnd="swap for another sphere",
            hidden="This sphere's n_b and n_u are hidden;\nfind them from the inner and outer radii of the ring.",
            prof="azimuthally averaged brightness I(b)", read="Move over the picture to read b and the brightness; click to record b.",
            picked="recorded b: ", clear="clear the records"),
}[LANG]

EPS, NR = 1e-6, 600


def g_table(nu):
    """radial density of the trapped UV absorption points"""
    g = np.zeros(NR); dr = 1.0 / NR; NB = 6000
    for i in range(NB):
        bp = (i + 0.5) / NB; w = 2 * bp / NB
        th0 = math.asin(bp) - math.asin(bp / nu); s0 = math.sin(th0)
        if s0 <= 1 / nu:
            continue
        c0 = math.cos(th0)
        k = np.arange(int(s0 / dr), NR)
        ra = np.maximum(k * dr, s0); rb = (k + 1) * dr
        g[k] += w * (np.sqrt(rb * rb - s0 * s0) - np.sqrt(ra * ra - s0 * s0)) / c0 / dr
    return g


def chord(b, nb):
    z1 = math.sqrt(1 - b * b); e = 1 / nb; k = 1 - e * e * (1 - z1 * z1)
    f = e * z1 - math.sqrt(k)
    d = (f * b, -e + f * z1)
    return (b, z1), d, -2 * (b * d[0] + z1 * d[1])


def profile(nb, nu, N=420):
    g = g_table(nu); I = np.zeros(N)
    for i in range(N):
        b = (i + 0.5) / N
        if b >= 0.999:
            continue
        p, d, L = chord(b, nb); M = 1200; dl = L / M
        t = np.arange(M) * dl
        ua = p[0] + d[0] * t; ub = ua + d[0] * dl; um = ua + d[0] * dl / 2
        zm = p[1] + d[1] * (t + dl / 2); r = np.hypot(um, zm)
        k = np.minimum(NR - 1, (r * NR).astype(int)); gk = g[k]
        A = np.abs(ua); B = np.abs(ub); a = np.maximum(A, EPS); bb = np.maximum(B, EPS)
        same = np.abs(bb - a) < 1e-12
        J = np.where(same, dl / a, dl * np.log(bb / a) / np.where(same, 1, bb - a))
        cross = ua * ub < 0
        Jc = dl / np.abs(ub - ua + 1e-30) * (np.log(a / EPS) + np.log(bb / EPS) + 2)
        J = np.where(cross, Jc, J)
        I[i] = np.sum(np.where((gk > 0) & (r > 1e-6), gk / np.maximum(r, 1e-6) * J, 0))
    return I


def axis_cross(b, nb):
    return 1 / (math.sqrt(nb * nb - b * b) - math.sqrt(1 - b * b))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TXT["title"]); self.geometry("1180x720")
        self.hid = (1.900, 1.45); self.ref = None; self.pins = []; self.prof = None
        left = ttk.Frame(self, padding=10); left.pack(side="left", fill="y")
        right = ttk.Frame(self, padding=6); right.pack(side="right", fill="both", expand=True)
        self.tab = tk.IntVar(value=0)
        for i, t in enumerate(TXT["tabs"]):
            ttk.Radiobutton(left, text=t, variable=self.tab, value=i, command=self.shoot).pack(anchor="w")
        self.lab = ttk.Label(left, text=TXT["hidden"], wraplength=220, foreground="#555"); self.lab.pack(pady=6, anchor="w")
        self.vnb = self._field(left, TXT["nb"], "1.9"); self.vnu = self._field(left, TXT["nu"], "1.45")
        self.vex = self._field(left, TXT["expo"], "1.0")
        ttk.Button(left, text=TXT["shoot"], command=self.shoot).pack(fill="x", pady=4)
        ttk.Button(left, text=TXT["rnd"], command=self.random_sphere).pack(fill="x")
        ttk.Label(left, text=TXT["read"], wraplength=220, foreground="#555").pack(pady=8, anchor="w")
        self.readout = ttk.Label(left, text="—", font=("Consolas", 10)); self.readout.pack(anchor="w")
        self.pinlab = ttk.Label(left, text="", wraplength=220, font=("Consolas", 9)); self.pinlab.pack(anchor="w", pady=4)
        ttk.Button(left, text=TXT["clear"], command=self.clear).pack(fill="x")
        self.fig = Figure(figsize=(10, 5.4), dpi=100)
        self.ax = self.fig.add_subplot(1, 2, 1); self.ap = self.fig.add_subplot(1, 2, 2)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right); self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.canvas.mpl_connect("motion_notify_event", self.on_move)
        self.canvas.mpl_connect("button_press_event", self.on_click)
        self.shoot()

    def _field(self, parent, label, val):
        f = ttk.Frame(parent); f.pack(fill="x", pady=2)
        ttk.Label(f, text=label).pack(side="left")
        v = tk.StringVar(value=val); ttk.Entry(f, textvariable=v, width=8).pack(side="right")
        return v

    def params(self):
        if self.tab.get() == 0:
            return self.hid
        return (min(3, max(1.01, float(self.vnb.get()))), min(3, max(1.01, float(self.vnu.get()))))

    def random_sphere(self):
        for _ in range(200):
            nb = 1.5 + 0.45 * random.random(); nu = 1.43 + 0.3 * random.random()
            if axis_cross(0.02, nb) > 1 and axis_cross(0.995, nb) < 1 / nu + 0.02 and nu > math.sqrt(2) + 0.01:
                self.hid = (nb, nu); break
        self.tab.set(0); self.clear(); self.shoot()

    def shoot(self):
        nb, nu = self.params()
        self.lab.configure(text=TXT["hidden"] if self.tab.get() == 0 else "")
        I = profile(nb, nu)
        if self.ref is None:
            Ir = profile(1.9, 1.45); band = np.sort(Ir[int(0.65 * len(Ir)):int(0.95 * len(Ir))])
            self.ref = band[len(band) // 2] / 0.75
        W = 400; y, x = np.mgrid[0:W, 0:W] + 0.5; R = W * 0.42
        b = np.hypot(x - W / 2, y - W / 2) / R
        v = np.where(b < 1, np.interp(b, (np.arange(len(I)) + 0.5) / len(I), I) / self.ref * float(self.vex.get()), 0)
        v = v * (1 + 0.12 * np.random.randn(W, W)) + 0.025 * np.abs(np.random.randn(W, W))
        v = np.clip(v, 0, 1.2); q = np.clip(v, 0, 1) ** 1.6
        rgb = np.dstack([0.16 * q, 0.47 * q, q])
        bins = np.arange(0, 1.41, 0.01); idx = np.digitize(b.ravel(), bins) - 1
        prof = np.bincount(idx[idx < len(bins) - 1], weights=v.ravel()[idx < len(bins) - 1], minlength=len(bins) - 1)
        cnt = np.bincount(idx[idx < len(bins) - 1], minlength=len(bins) - 1)
        self.prof = (bins[:-1] + 0.005, prof / np.maximum(cnt, 1))
        self.ax.clear(); self.ax.imshow(rgb, extent=(-W / 2 / R, W / 2 / R, -W / 2 / R, W / 2 / R))
        t = np.linspace(0, 2 * np.pi, 300); self.ax.plot(np.cos(t), np.sin(t), "r-", lw=1); self.ax.plot([0], [0], "r+")
        for pb in self.pins:
            self.ax.plot(pb * np.cos(t), pb * np.sin(t), "--", color="#fc0", lw=0.8)
        self.ax.set_xticks([]); self.ax.set_yticks([])
        self.ap.clear(); self.ap.plot(*self.prof, color="#1f77b4"); self.ap.set_xlim(0, 1.3)
        for pb in self.pins:
            self.ap.axvline(pb, color="#e8a400", ls="--", lw=0.8)
        self.ap.set_xlabel("b"); self.ap.set_title(TXT["prof"], fontsize=10); self.ap.grid(alpha=.3)
        self.fig.tight_layout(); self.canvas.draw_idle()

    def on_move(self, ev):
        if ev.inaxes is self.ax and ev.xdata is not None and self.prof:
            b = math.hypot(ev.xdata, ev.ydata); j = min(len(self.prof[1]) - 1, int(b * 100))
            self.readout.configure(text=f"b = {b:.3f}   I ≈ {self.prof[1][j]:.3f}")

    def on_click(self, ev):
        if ev.inaxes is self.ax and ev.xdata is not None:
            self.pins.append(round(math.hypot(ev.xdata, ev.ydata), 3))
            self.pinlab.configure(text=TXT["picked"] + ", ".join(f"{p:.3f}" for p in self.pins)); self.shoot()

    def clear(self):
        self.pins = []; self.pinlab.configure(text="")


if __name__ == "__main__":
    App().mainloop()
