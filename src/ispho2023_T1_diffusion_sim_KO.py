#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISPhO 2023 Theoretical Problem 1 — "Polycrystal diffusion"
The organisers' A.exe, B.exe and C.exe with InteractiveBuffer, B.nb and
C.nb in one window.

A.exe  impurity atoms hop between the inter-nodes of a cubic lattice
       (a = 1); along each axis a jump happens at the rate 2D/a², with
       D = D0 sqrt(T) exp(-Eg/T) in arbitrary units.  The program returns
       the rms displacement and its error over the N particles.
B.exe  type-A kinetics: the front moves with the effective coefficient of
       the polycrystal, D_eff/D = 1 + alpha delta (D_gb/D - 1); it writes
       ln c against z².
C.exe  type-B kinetics: the boundaries carry the impurity ahead of the
       lattice front, ln c falls linearly in z^(6/5); it writes the
       average profile and the map around one boundary.
Eg, alpha, xi, eta, zeta and C are left for the user to find; Eg, D0,
alpha and C are drawn afresh for each session.

    python ispho2023_T1_diffusion_sim_KO.py
"""

import csv
import random
import tkinter as tk
from tkinter import ttk, filedialog

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

LANG = "KO"          # the EN edition differs only in this line

TXT = {
 "KO": dict(title="ISPhO 2023 T1 — 다결정 확산", A="A — A.exe", B="B — B.exe", C="C — C.exe", Buf="Buffer",
            lA=("t  시간 [1; 10]", "T  온도 [1; 10]", "N  반복 [100; 10000]"),
            lB=("t  시간 [2; 5]", "D_gb/D [2; 5]", "δ [0.005; 0.05]"),
            lC=("t  시간 [0.005; 0.2]", "D_gb/D [5; 50]", "δ [0.02; 0.2]"),
            run="실행", fit="직선 맞춤 구간 (z 축 비율)", add="Add point", dele="Remove last point", clr="Clear data",
            pfit="Plot fit", csv="CSV로 저장", bad="입력 범위를 벗어났습니다", slope="기울기", eta="예상 모의 시간 %.1f s",
            note="Eg, α, ξ, η, ζ, C 는 직접 찾으세요."),
 "EN": dict(title="ISPhO 2023 T1 — Polycrystal Diffusion", A="A — A.exe", B="B — B.exe", C="C — C.exe", Buf="Buffer",
            lA=("t  time [1; 10]", "T  temperature [1; 10]", "N  repetitions [100; 10000]"),
            lB=("t  time [2; 5]", "D_gb/D [2; 5]", "delta [0.005; 0.05]"),
            lC=("t  time [0.005; 0.2]", "D_gb/D [5; 50]", "delta [0.02; 0.2]"),
            run="run", fit="fit range (fraction of the axis)", add="Add point", dele="Remove last point", clr="Clear data",
            pfit="Plot fit", csv="save as CSV", bad="Input out of range", slope="slope", eta="expected simulation time %.1f s",
            note="Eg, alpha, xi, eta, zeta and C are yours to find."),
}[LANG]

RANGE = {"A": ((1, 10), (1, 10), (100, 10000)), "B": ((2, 5), (2, 5), (0.005, 0.05)), "C": ((0.005, 0.2), (5, 50), (0.02, 0.2))}
DEF = {"A": (10, 1, 1000), "B": (5, 5, 0.02), "C": (0.1, 25, 0.1)}


def U(a, b):
    return random.uniform(a, b)


class Truth:
    def __init__(self):
        self.Eg, self.D0, self.alpha = U(3.40, 3.80), 113 * U(0.95, 1.05), U(0.68, 0.82)
        self.C, self.xi, self.eta, self.zeta = 1.42 * U(0.96, 1.04), -0.39, -0.68, -0.44


TR = Truth()


def run_A(t, T, N):
    """Random walk between inter-nodes; exact hops for short walks, the normal limit for long ones."""
    D = TR.D0 * np.sqrt(T) * np.exp(-TR.Eg / T)
    n = np.random.poisson(6 * D * t, size=N)
    pos = np.zeros((N, 3))
    for i in range(N):
        if n[i] < 3000:
            ax = np.random.randint(0, 3, n[i]); sg = np.random.choice((-1, 1), n[i])
            for k in range(3):
                pos[i, k] = np.sum(sg[ax == k])
        else:
            pos[i] = np.round(np.random.normal(0, np.sqrt(n[i] / 3), 3))
    r2 = np.sum(pos ** 2, axis=1); R = np.sqrt(r2.mean())
    return pos, R, r2.std(ddof=1) / np.sqrt(N) / (2 * R)


def run_B(t, g, dl):
    Deff = 1 + TR.alpha * dl * (g - 1)
    z = np.abs(np.random.normal(0, np.sqrt(2 * Deff * t), 40000)); dz = 0.1
    h, e = np.histogram(z, bins=np.arange(0, z.max() + dz, dz))
    zc = (e[:-1] + e[1:]) / 2; ok = h >= 3
    return zc[ok] ** 2, np.log(h[ok] / (z.size * dz)), z[:1500]


def run_C(t, g, dl):
    k = TR.C * dl ** TR.xi * g ** TR.eta * t ** TR.zeta
    A0 = 1 / np.sqrt(np.pi * t); Agb = A0 * dl * np.sqrt(g) * 0.6; ell = 0.7 * np.sqrt(t)
    zmax = (np.log(Agb / 1e-6 * A0) / k) ** (5 / 6) * 0.9
    z = (np.arange(160) + 0.5) / 160 * zmax; y = np.linspace(-0.5, 0.5, 81)
    Z, Y = np.meshgrid(z, y, indexing="ij")
    c = A0 * np.exp(-Z ** 2 / (4 * t)) + Agb * np.exp(-k * Z ** 1.2) * np.exp(-np.abs(Y) / ell) / (2 * ell * (1 - np.exp(-0.5 / ell)))
    cnt = 6e6; m = c.mean(axis=1); n = m * cnt * zmax / 160 / A0; ok = n >= 4
    lc = np.log(m[ok] * (1 + np.random.normal(0, 1, ok.sum()) / np.sqrt(n[ok])))
    nn = c * 40 * cnt * zmax / 160 / 81 / A0
    cmap = np.where(nn >= 1, np.log(np.abs(c * (1 + np.random.normal(0, 1, c.shape) / np.sqrt(np.maximum(nn, 1))))), np.nan)
    return z[ok] ** 1.2, lc, cmap, zmax


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TXT["title"]); self.geometry("1220x780")
        self.res = {"A": None, "B": None, "C": None}; self.fitr = {"B": [0.0, 0.6], "C": [0.15, 0.85]}
        self.buf = []; self.kfit = None
        self._build(); self._redraw()

    def _build(self):
        left = ttk.Frame(self, padding=10); left.pack(side="left", fill="y")
        right = ttk.Frame(self, padding=10); right.pack(side="right", fill="both", expand=True)
        self.task = tk.StringVar(value="A")
        for k in ("A", "B", "C", "Buf"):
            ttk.Radiobutton(left, text=TXT[k], value=k, variable=self.task, command=self._switch).pack(anchor="w")
        self.lab, self.var = [], []
        for i in range(3):
            l = ttk.Label(left, text=""); l.pack(anchor="w", pady=(8, 0)); v = tk.DoubleVar(value=DEF["A"][i])
            ttk.Entry(left, textvariable=v).pack(fill="x"); self.lab.append(l); self.var.append(v)
        self.etal = ttk.Label(left, text="", foreground="#5b6b7c"); self.etal.pack(anchor="w")
        ttk.Button(left, text=TXT["run"], command=self._run).pack(fill="x", pady=6)
        self.resl = tk.Label(left, text="—", font=("Consolas", 13, "bold"), bg="#101418", fg="#8fd6ff"); self.resl.pack(fill="x")
        ttk.Label(left, text=TXT["fit"]).pack(anchor="w", pady=(10, 0))
        self.f1, self.f2 = tk.DoubleVar(value=0.0), tk.DoubleVar(value=0.6)
        for v in (self.f1, self.f2):
            ttk.Scale(left, from_=0, to=1, variable=v, command=lambda e: self._refit()).pack(fill="x")
        self.fitl = ttk.Label(left, text="—", font=("Consolas", 10)); self.fitl.pack(anchor="w")
        ttk.Separator(left).pack(fill="x", pady=8)
        ttk.Label(left, text="InteractiveBuffer  x, y").pack(anchor="w")
        fr = ttk.Frame(left); fr.pack(fill="x")
        self.bx, self.by = tk.StringVar(), tk.StringVar()
        ttk.Entry(fr, textvariable=self.bx, width=12).pack(side="left"); ttk.Entry(fr, textvariable=self.by, width=12).pack(side="left")
        for lab, cmd in ((TXT["add"], self._add), (TXT["dele"], self._del), (TXT["clr"], self._clr), (TXT["pfit"], self._bfit)):
            ttk.Button(left, text=lab, command=cmd).pack(fill="x", pady=1)
        self.bl = ttk.Label(left, text="—", font=("Consolas", 10)); self.bl.pack(anchor="w")
        ttk.Button(left, text=TXT["csv"], command=self._csv).pack(fill="x", pady=6)
        ttk.Label(left, text=TXT["note"], wraplength=260, foreground="#7a8794").pack(fill="x")
        self.fig = Figure(figsize=(8, 6.4), dpi=100)
        self.ax1 = self.fig.add_subplot(211); self.ax2 = self.fig.add_subplot(212)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right); self.canvas.get_tk_widget().pack(fill="both", expand=True)
        for v in self.var:
            v.trace_add("write", lambda *a: self._eta())
        self._switch()

    def _switch(self):
        k = self.task.get()
        if k in RANGE:
            for i in range(3):
                self.lab[i].config(text=TXT["l" + k][i]); self.var[i].set(DEF[k][i])
            if k in self.fitr:
                self.f1.set(self.fitr[k][0]); self.f2.set(self.fitr[k][1])
        self._refit()

    def _eta(self):
        try:
            t, T, N = (v.get() for v in self.var)
            e = N * 6 * TR.D0 * np.sqrt(T) * np.exp(-TR.Eg / T) * t * 4e-8 + 0.1 if self.task.get() == "A" else 0.5
            self.etal.config(text=TXT["eta"] % e)
        except (tk.TclError, ValueError):
            pass

    def _run(self):
        k = self.task.get()
        if k not in RANGE:
            return
        v = [x.get() for x in self.var]
        if not all(lo <= x <= hi for x, (lo, hi) in zip(v, RANGE[k])):
            self.resl.config(text=TXT["bad"]); return
        if k == "A":
            pos, R, sR = run_A(v[0], v[1], int(v[2])); self.res["A"] = (pos, R, sR)
            self.resl.config(text=f"Δr_sq = {R:.3f} ± {sR:.3f}")
        elif k == "B":
            self.res["B"] = run_B(*v) + (v,)
        else:
            self.res["C"] = run_C(*v) + (v,)
        self._refit()

    def _refit(self):
        k = self.task.get(); self.kfit = None
        if k in ("B", "C") and self.res[k]:
            self.fitr[k] = [self.f1.get(), self.f2.get()]
            x, y = self.res[k][0], self.res[k][1]; x0, x1 = self.f1.get() * x.max(), self.f2.get() * x.max()
            ok = (x >= x0) & (x <= x1)
            if ok.sum() >= 3:
                (b, a), cov = np.polyfit(x[ok], y[ok], 1, cov=True)
                self.kfit = (a, b, np.sqrt(cov[0, 0]), x0, x1)
                self.fitl.config(text=f"{TXT['slope']} k = {b:.5f} ± {np.sqrt(cov[0, 0]):.5f}")
        self._redraw()

    def _add(self):
        try:
            self.buf.append((float(self.bx.get()), float(self.by.get())))
        except ValueError:
            return
        self._bfit()

    def _del(self):
        if self.buf:
            self.buf.pop()
        self._bfit()

    def _clr(self):
        self.buf = []; self._bfit()

    def _bfit(self):
        if len(self.buf) >= 3:
            p = np.array(self.buf); (b, a), cov = np.polyfit(p[:, 0], p[:, 1], 1, cov=True)
            self.bl.config(text=f"b = {b:.6g} ± {np.sqrt(cov[0, 0]):.3g}\na = {a:.6g} ± {np.sqrt(cov[1, 1]):.3g}")
        elif len(self.buf) == 2:
            p = np.array(self.buf); b, a = np.polyfit(p[:, 0], p[:, 1], 1); self.bl.config(text=f"b = {b:.6g}\na = {a:.6g}")
        else:
            self.bl.config(text="—")
        self.task.set("Buf"); self._redraw()

    def _redraw(self):
        a1, a2 = self.ax1, self.ax2; a1.clear(); a2.clear(); a2.set_visible(True)
        k = self.task.get()
        if k == "A" and self.res["A"]:
            pos = self.res["A"][0]
            a1.plot(pos[:3000, 0], pos[:3000, 1], ".", ms=2); a1.set_xlabel("x, a"); a1.set_ylabel("y, a"); a1.set_aspect("equal", "datalim")
            a2.hist(np.sqrt(np.sum(pos ** 2, axis=1)), bins=40); a2.set_xlabel("r, a"); a2.set_ylabel("N")
        elif k in ("B", "C") and self.res[k]:
            x, y = self.res[k][0], self.res[k][1]
            a1.plot(x, y, ".", label="Bavg" if k == "B" else "Cavg"); a1.set_xlabel("z²" if k == "B" else "z^(6/5)"); a1.set_ylabel("ln c̄")
            if self.kfit:
                a, b, sb, x0, x1 = self.kfit; a1.plot([x0, x1], [a + b * x0, a + b * x1], label=f"k = {b:.4f}")
            a1.legend()
            if k == "B":
                z = self.res["B"][2]; a2.plot(np.random.uniform(0, 6, z.size), -z, ".", ms=2, color="#e02424")
                a2.set_xlabel("y, a"); a2.set_ylabel("−z, a")
            else:
                cmap, zmax = self.res["C"][2], self.res["C"][3]
                im = a2.imshow(cmap.T, aspect="auto", origin="lower", extent=(0, zmax ** 1.2, -0.5, 0.5))
                a2.set_xlabel("z^(6/5)"); a2.set_ylabel("y")
        elif k == "Buf" and self.buf:
            p = np.array(self.buf); a1.plot(p[:, 0], p[:, 1], "o")
            if len(p) >= 2:
                b, a = np.polyfit(p[:, 0], p[:, 1], 1); xs = np.array([p[:, 0].min(), p[:, 0].max()]); a1.plot(xs, a + b * xs)
            a2.set_visible(False)
        for ax in (a1, a2):
            ax.grid(True, alpha=0.4)
        self.fig.tight_layout(); self.canvas.draw_idle()

    def _csv(self):
        k = self.task.get()
        p = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=f"ISPhO2023_T1_{k}.csv")
        if not p:
            return
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if k == "A" and self.res["A"]:
                w.writerow(["x", "y", "z"]); w.writerows(self.res["A"][0].astype(int).tolist())
            elif k in ("B", "C") and self.res[k]:
                w.writerow(["z2" if k == "B" else "z6_5", "ln_c"])
                for a, b in zip(self.res[k][0], self.res[k][1]):
                    w.writerow([f"{a:.6f}", f"{b:.6f}"])
            elif self.buf:
                w.writerow(["x", "y"]); w.writerows(self.buf)


if __name__ == "__main__":
    App().mainloop()
