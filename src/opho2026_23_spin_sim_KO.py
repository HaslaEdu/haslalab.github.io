#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OPhO 2026 #23 — Spinny Spin Spin (Simulation Lab)
A virtual sensor: 100 000 electron spins on a rod (xi from -1 to 1) in Bz = B0 + B1 xi + b,
thermalised, turned 90 degrees about y at t = 0, then left to precess.  The sensor returns the
total magnetisation Mx, My in units of mu_B, with noise, only for 100 ns <= t <= 10000 ns.

Same model as the HaslaLab browser version; g, B0 and B1 are hidden (the official solution's values).

    python opho2026_23_spin_sim.py
"""

import math, csv
import tkinter as tk
from tkinter import ttk, filedialog

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
matplotlib.rcParams["font.family"] = ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

LANG = "KO"

TXT = {
 "KO": dict(title="OPhO 2026 #23 — 스핀, 스핀, 스핀", b="바이어스 b (T)", t0="측정 시작 (ns)", t1="측정 끝 (ns)",
            dt="간격 (ns)", run="펄스를 주고 측정", csv="CSV로 저장", hold="이전 측정 유지", showM="|M| 함께 그리기",
            help="|b| ≤ 0.01 T. t < 100 ns와 t > 10000 ns는 기록되지 않습니다.\n측정값에는 잡음이 있습니다."),
 "EN": dict(title="OPhO 2026 #23 — Spinny Spin Spin", b="bias b (T)", t0="record from (ns)", t1="record to (ns)",
            dt="step (ns)", run="pulse and measure", csv="save as CSV", hold="keep earlier runs", showM="also plot |M|",
            help="|b| <= 0.01 T. Nothing is recorded before 100 ns or after 10000 ns.\nEvery reading is noisy."),
}[LANG]

G, B0, B1, N, TK, SIG = 1.83, 5.27e-3, 73e-6, 100000, 1.0, 12.0     # hidden truth
MUB, HBAR, KB = 9.2740100783e-24, 1.054571817e-34, 1.380649e-23


def measure(b, t0, t1, dt, K=400):
    Bc = B0 + b
    M0 = N * (G / 2) * math.tanh(G * MUB * abs(Bc) / (2 * KB * TK)) * (1 if Bc >= 0 else -1)
    t = np.arange(max(100, t0), min(10000, t1) + 1e-9, dt)
    xi = -1 + (np.arange(K) + 0.5) * 2 / K
    w = np.outer(t * 1e-9, G * MUB * (Bc + B1 * xi) / HBAR)
    mx = M0 * np.cos(w).mean(axis=1) + SIG * np.random.randn(len(t))
    my = M0 * np.sin(w).mean(axis=1) + SIG * np.random.randn(len(t))
    return t, mx, my


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TXT["title"]); self.geometry("1180x700"); self.runs = []
        left = ttk.Frame(self, padding=10); left.pack(side="left", fill="y")
        right = ttk.Frame(self, padding=6); right.pack(side="right", fill="both", expand=True)
        self.v = {}
        for k, val in (("b", "0.010"), ("t0", "100"), ("t1", "400"), ("dt", "1")):
            f = ttk.Frame(left); f.pack(fill="x", pady=2)
            ttk.Label(f, text=TXT[k]).pack(side="left")
            self.v[k] = tk.StringVar(value=val); ttk.Entry(f, textvariable=self.v[k], width=9).pack(side="right")
        ttk.Button(left, text=TXT["run"], command=self.run).pack(fill="x", pady=4)
        ttk.Button(left, text=TXT["csv"], command=self.save).pack(fill="x")
        self.hold = tk.BooleanVar(); self.showM = tk.BooleanVar(value=True)
        ttk.Checkbutton(left, text=TXT["hold"], variable=self.hold).pack(anchor="w", pady=2)
        ttk.Checkbutton(left, text=TXT["showM"], variable=self.showM, command=self.draw).pack(anchor="w")
        ttk.Label(left, text=TXT["help"], wraplength=220, foreground="#555").pack(anchor="w", pady=8)
        self.fig = Figure(figsize=(9, 5), dpi=100); self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right); self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.draw()

    def run(self):
        try:
            b, t0, t1, dt = (float(self.v[k].get()) for k in ("b", "t0", "t1", "dt"))
        except ValueError:
            return
        b = max(-0.01, min(0.01, b)); self.v["b"].set(str(b))
        dt = max(dt, (min(10000, t1) - max(100, t0)) / 20000, 1e-3)
        if not self.hold.get():
            self.runs = []
        self.runs = (self.runs + [(b,) + measure(b, t0, t1, dt)])[-3:]
        self.draw()

    def draw(self):
        ax = self.ax; ax.clear()
        for b, t, mx, my in self.runs:
            ax.plot(t, mx, lw=0.8, label=f"Mx  b={b} T"); ax.plot(t, my, lw=0.8, label=f"My  b={b} T")
            if self.showM.get():
                ax.plot(t, np.hypot(mx, my), color="#333", lw=1)
        ax.set_xlabel("t (ns)"); ax.set_ylabel("M (μ_B)"); ax.grid(alpha=.3)
        if self.runs:
            ax.legend(loc="upper right", fontsize=8)
        self.fig.tight_layout(); self.canvas.draw_idle()

    def save(self):
        if not self.runs:
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if p:
            b, t, mx, my = self.runs[-1]
            with open(p, "w", newline="") as f:
                w = csv.writer(f); w.writerow(["t_ns", "Mx_muB", "My_muB"])
                w.writerows(zip(t, mx, my))


if __name__ == "__main__":
    App().mainloop()
