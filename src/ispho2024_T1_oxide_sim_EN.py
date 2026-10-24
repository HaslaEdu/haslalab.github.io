#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISPhO 2024 Theoretical Problem 1 — "Thermal oxidation"
The organisers' programs in one window: A.py, B1.py, B2.py, gen_data, B.py,
B7.py and B8.py.

Ellipsometry of a film d on a substrate, the sheet's three-layer formula

    r = (A + B e^{2 i k2x d}) / (AB + e^{2 i k2x d}),
    s: A = (k2x + k3x)/(k2x - k3x),  B = (k1x + k2x)/(k1x - k2x)
    p: the same with kappa_ix = k_ix / eps_i
    tan Psi e^{i Delta} = r_p / r_s

Part A without dispersion (eps_Si = 17.2 - 0.430i, eps_SiO2 = 2.13); part B
with the dispersion of Si (Green 2008) and SiO2 (Malitson).
The furnace grows the oxide by Deal-Grove plus a fast initial term that dies
away within a few nanometres, which is why the model is fitted from 25 nm.
Every hidden constant (the two samples, B, B/A, their activation energies)
is drawn afresh for each session; theta_opt, Phi, d, B, B/A, dEa and dEb are
left for the user to find.

    python ispho2024_T1_oxide_sim_KO.py
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

LANG = "EN"          # the EN edition differs only in this line

TXT = {
 "KO": dict(title="ISPhO 2024 T1 — 열산화", A="A7 — A.py", B12="B1 · B2", B3="B3 · B7", B8="B8 — B8.py",
            runA="A.py 실행", runB12="근사 곡선 그리기", gen="gen_data 실행", stop="중단", proc="B.py 실행",
            b7="B7.py 실행", toB8="B8_in.txt 에 한 줄 추가", runB8="B8.py 실행", csv="CSV로 저장",
            err="error (deg)", thin="Final layer is too thin to approximate", noexp="그 이름의 gen_data 결과가 없습니다 (FileNotFoundError)",
            bad="입력 범위를 벗어났습니다", slope="기울기", idle="입력을 정하고 실행하세요.",
            note="θopt, Φ, d, B, B/A, ΔEa, ΔEb 는 직접 찾으세요."),
 "EN": dict(title="ISPhO 2024 T1 — Thermal Oxidation", A="A7 — A.py", B12="B1 · B2", B3="B3 · B7", B8="B8 — B8.py",
            runA="run A.py", runB12="draw the approximation", gen="run gen_data", stop="interrupt", proc="run B.py",
            b7="run B7.py", toB8="append to B8_in.txt", runB8="run B8.py", csv="save as CSV",
            err="error (deg)", thin="Final layer is too thin to approximate", noexp="No gen_data result under that name (FileNotFoundError)",
            bad="Input out of range", slope="slope", idle="Set the input and run.",
            note="theta_opt, Phi, d, B, B/A, dEa and dEb are yours to find."),
}[LANG]

LAM = np.arange(400, 801, 4.0)
SI = np.array([[400, 5.570, 0.387], [425, 5.000, 0.230], [450, 4.674, 0.135], [475, 4.460, 0.093], [500, 4.298, 0.073],
               [525, 4.180, 0.056], [550, 4.077, 0.041], [575, 4.000, 0.031], [600, 3.939, 0.025], [650, 3.844, 0.016],
               [700, 3.776, 0.0108], [750, 3.728, 0.0076], [800, 3.688, 0.0055]])
N_SI = np.interp(LAM, SI[:, 0], SI[:, 1]) - 1j * np.interp(LAM, SI[:, 0], SI[:, 2])
EPS_SI = N_SI ** 2
X2 = (LAM / 1000) ** 2
EPS_OX = 1 + 0.6961663 * X2 / (X2 - 0.0684043 ** 2) + 0.4079426 * X2 / (X2 - 0.1162414 ** 2) + 0.8974794 * X2 / (X2 - 9.896161 ** 2)
SIG_P, SIG_D = 0.15, 0.80
KB = 8.617e-5


def psi_delta(th_deg, d, disp):
    """Psi, Delta (degrees) over LAM for angle th_deg and film thickness d (nm)."""
    th = np.radians(th_deg)
    e1 = 1.0 + 0j
    e2 = EPS_OX + 0j if disp else 2.13 + 0j
    e3 = EPS_SI if disp else (17.2 - 0.43j) * np.ones_like(LAM)
    w = 2 * np.pi / LAM
    s2 = np.sin(th) ** 2
    k1 = np.sqrt(e1) * np.cos(th) * w
    k2 = np.sqrt(e2 - e1 * s2) * w
    k3 = np.sqrt(e3 - e1 * s2) * w
    E = np.exp(2j * k2 * d)

    def r(a1, a2, a3):
        A = (a2 + a3) / (a2 - a3)
        B = (a1 + a2) / (a1 - a2)
        return (A + B * E) / (A * B + E)
    q = r(k1 / e1, k2 / e2, k3 / e3) / r(k1, k2, k3)
    return np.degrees(np.arctan(np.abs(q))), np.degrees(np.angle(-q))


def wrap(x):
    return (x + 180) % 360 - 180


def U(a, b):
    return random.uniform(a, b)


class Truth:
    def __init__(self):
        self.b1 = (U(66, 75), U(52, 85))
        self.b2 = (U(52, 62), U(205, 245))
        self.B0, self.Ea = U(150, 172), U(1.30, 1.45)
        self.BA0, self.Eb = U(0.95, 1.12), U(1.90, 2.10)
        self.K0, self.Lm, self.dn = U(3, 4), U(5, 6), U(1.0, 1.8)

    def B(self, T):
        return self.B0 * np.exp(-self.Ea / KB * (1 / (T + 273.15) - 1 / 1273.15))

    def BA(self, T):
        return self.BA0 * np.exp(-self.Eb / KB * (1 / (T + 273.15) - 1 / 1273.15))

    def grow(self, T, dt, d):
        B, A, K = self.B(T), self.B(T) / self.BA(T), self.K0 * self.BA(T) / self.BA0
        f = lambda x: B / (2 * x + A) + K * np.exp(-x / self.Lm)
        k1 = f(d); k2 = f(d + dt / 2 * k1); k3 = f(d + dt / 2 * k2); k4 = f(d + dt * k3)
        return d + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)


TR = Truth()


def noisy(PD):
    P, D = PD
    return P + np.random.normal(0, SIG_P, P.size), wrap(D + np.random.normal(0, SIG_D, D.size))


DATA = {"B1": noisy(psi_delta(*TR.b1, True)), "B2": noisy(psi_delta(*TR.b2, True))}


def fit_d(phi, data):
    """B.py: the thickness that best explains one spectrum, and its statistical error."""
    def chi(d):
        P, D = psi_delta(phi, d, True)
        return np.sum(((data[0] - P) / SIG_P) ** 2 + (wrap(data[1] - D) / SIG_D) ** 2)
    grid = np.arange(0, 301, 1.0)
    best = grid[np.argmin([chi(d) for d in grid])]
    a, b = max(0.0, best - 1), best + 1
    for _ in range(40):
        m1, m2 = a + (b - a) * 0.382, a + (b - a) * 0.618
        if chi(m1) < chi(m2):
            b = m2
        else:
            a = m1
    dm, h = (a + b) / 2, 0.05
    c = (chi(dm + h) - 2 * chi(dm) + chi(max(0, dm - h))) / h ** 2
    red = chi(dm) / (2 * LAM.size - 1)
    return dm, np.sqrt(2 * max(red, 1) / max(c, 1e-9))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TXT["title"]); self.geometry("1240x800")
        self.res_A = self.res_B12 = self.b7res = self.b8res = None
        self.exps, self.cur, self.gen = {}, None, None
        self._build(); self._redraw()

    # ---------------- layout ----------------
    def _build(self):
        left = ttk.Frame(self, padding=10); left.pack(side="left", fill="y")
        right = ttk.Frame(self, padding=10); right.pack(side="right", fill="both", expand=True)
        nb = ttk.Notebook(left, width=330); nb.pack(fill="both", expand=True)
        nb.bind("<<NotebookTabChanged>>", lambda e: self._redraw())
        self.nb = nb
        fA, fB, fC, fD = (ttk.Frame(nb, padding=6) for _ in range(4))
        for f, k in ((fA, "A"), (fB, "B12"), (fC, "B3"), (fD, "B8")):
            nb.add(f, text=TXT[k])

        ttk.Label(fA, text="A_in.txt  (Name  θ1  d)").pack(anchor="w")
        self.ainA = tk.Text(fA, height=8, width=36, font=("Consolas", 10)); self.ainA.pack(fill="x")
        self.ainA.insert("1.0", "Name\tθ1\td\nex1\t50\t40\nex2\t30\t100\n")
        ttk.Button(fA, text=TXT["runA"], command=self._runA).pack(fill="x", pady=6)

        self.samp = tk.StringVar(value="B1")
        fr = ttk.Frame(fB); fr.pack(fill="x")
        for k in ("B1", "B2"):
            ttk.Radiobutton(fr, text=k + ".txt", value=k, variable=self.samp, command=self._redraw).pack(side="left")
        self.phi = tk.DoubleVar(value=60); self.dd = tk.DoubleVar(value=50)
        for lab, var in (("Φ, °", self.phi), ("d, nm", self.dd)):
            ttk.Label(fB, text=lab).pack(anchor="w", pady=(8, 0))
            ttk.Entry(fB, textvariable=var).pack(fill="x")
        ttk.Button(fB, text=TXT["runB12"], command=self._runB12).pack(fill="x", pady=6)
        self.errl = tk.Label(fB, text=TXT["err"] + ": —", font=("Consolas", 16, "bold"), bg="#101418", fg="#8fd6ff")
        self.errl.pack(fill="x")

        ttk.Label(fC, text="B_in.txt  (Name  Phi  T  t)").pack(anchor="w")
        self.ainB = tk.Text(fC, height=3, width=36, font=("Consolas", 10)); self.ainB.pack(fill="x")
        self.ainB.insert("1.0", "Name\tPhi\tT\tt\ntest\t50\t1000\t40\n")
        for lab, cmd in ((TXT["gen"], self._gen), (TXT["stop"], self._stop), (TXT["proc"], self._proc),
                         (TXT["b7"], self._b7), (TXT["toB8"], self._toB8)):
            ttk.Button(fC, text=lab, command=cmd).pack(fill="x", pady=2)
        self.prog = ttk.Progressbar(fC, maximum=1.0); self.prog.pack(fill="x", pady=4)
        self.b7l = ttk.Label(fC, text="—", font=("Consolas", 10), justify="left"); self.b7l.pack(anchor="w")

        ttk.Label(fD, text="B8_in.txt  (T  B  dB  B/A  d(B/A))").pack(anchor="w")
        self.ainB8 = tk.Text(fD, height=9, width=36, font=("Consolas", 10)); self.ainB8.pack(fill="x")
        self.ainB8.insert("1.0", "T\tB\tdB\tB/A\td(B/A)\n")
        ttk.Button(fD, text=TXT["runB8"], command=self._runB8).pack(fill="x", pady=6)
        self.b8l = ttk.Label(fD, text="—", font=("Consolas", 10), justify="left"); self.b8l.pack(anchor="w")

        self.status = ttk.Label(left, text=TXT["idle"], wraplength=320, foreground="#b3261e"); self.status.pack(fill="x", pady=6)
        ttk.Button(left, text=TXT["csv"], command=self._csv).pack(fill="x")
        ttk.Label(left, text=TXT["note"], wraplength=320, foreground="#7a8794").pack(fill="x", pady=8)

        self.fig = Figure(figsize=(8.2, 6.6), dpi=100)
        self.ax1 = self.fig.add_subplot(211); self.ax2 = self.fig.add_subplot(212)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def task(self):
        return ["A", "B12", "B3", "B8"][self.nb.index(self.nb.select())]

    @staticmethod
    def rows(text):
        return [p for p in (ln.split() for ln in text.splitlines()) if p and p[0].lower() not in ("name", "t")]

    def say(self, s):
        self.status.config(text=s)

    # ---------------- programs ----------------
    def _runA(self):
        out = []
        for r in self.rows(self.ainA.get("1.0", "end")):
            try:
                th, d = float(r[1]), float(r[2])
            except (IndexError, ValueError):
                continue
            if not (20 <= th <= 80 and 0 <= d <= 250):
                self.say(TXT["bad"] + ": " + " ".join(r)); return
            out.append((r[0], th, d, psi_delta(th, d, False)))
        self.res_A = out; self._redraw()

    def _runB12(self):
        phi, d = self.phi.get(), self.dd.get()
        if not (20 <= phi <= 80 and 0 <= d <= 250):
            self.say(TXT["bad"]); return
        P, D = psi_delta(phi, d, True); dat = DATA[self.samp.get()]
        err = np.sqrt(np.mean(np.concatenate([(dat[0] - P) ** 2, wrap(dat[1] - D) ** 2])))
        self.res_B12 = (self.samp.get(), P, D); self.errl.config(text=f"{TXT['err']}: {err:.3f}"); self._redraw()

    def readB(self):
        r = [x for x in self.rows(self.ainB.get("1.0", "end")) if len(x) >= 4]
        if not r:
            return None
        try:
            o = dict(name=r[0][0], phi=float(r[0][1]), T=float(r[0][2]), tmax=float(r[0][3]))
        except ValueError:
            return None
        if not (20 <= o["phi"] <= 80 and 800 <= o["T"] <= 1200 and 0 < o["tmax"] <= 200):
            return None
        return o

    def _gen(self):
        o = self.readB()
        if not o:
            self.say(TXT["bad"]); return
        if self.gen:
            return
        o.update(frames=[], res=None, d=TR.dn, t=0)
        self.exps[o["name"]] = o; self.cur = o["name"]; self.gen = o
        self.after(10, self._gen_step)

    def _gen_step(self):
        o = self.gen
        if not o:
            return
        for _ in range(20):
            o["d"] = TR.grow(o["T"], 0.1, o["d"])
        o["t"] += 2
        o["frames"].append((o["t"], noisy(psi_delta(o["phi"] + np.random.normal(0, 0.12), o["d"], True))))
        n = int(o["tmax"] // 2)
        self.prog.config(value=len(o["frames"]) / n); self.say(f"gen_data: {len(o['frames'])} / {n}"); self._redraw()
        if len(o["frames"]) >= n:
            self.gen = None
        else:
            self.after(60, self._gen_step)

    def _stop(self):
        self.gen = None

    def _proc(self):
        o = self.readB(); ex = o and self.exps.get(o["name"])
        if not ex or not ex["frames"]:
            self.say(TXT["noexp"]); return
        self.cur = o["name"]; ex["res"] = []
        for i, (t, s) in enumerate(ex["frames"]):
            d, e = fit_d(ex["phi"], s); ex["res"].append((t, d, e))
            self.prog.config(value=(i + 1) / len(ex["frames"])); self.update_idletasks()
        self.say("B.py: res"); self._redraw()

    def _b7(self):
        o = self.readB(); ex = o and self.exps.get(o["name"])
        if not ex or not ex["res"]:
            self.say(TXT["noexp"]); return
        p = np.array([r for r in ex["res"] if r[1] >= 25])
        if len(p) < 4:
            self.b7l.config(text=TXT["thin"]); self.b7res = None; return
        t, d = p[:, 0], p[:, 1]
        M = np.vstack([d * d, d, np.ones_like(d)]).T
        c, *_ = np.linalg.lstsq(M, t, rcond=None)
        s2 = np.sum((t - M @ c) ** 2) / max(1, len(t) - 3)
        cov = s2 * np.linalg.inv(M.T @ M)
        B, BA = 1 / c[0], 1 / c[1]
        sB, sBA = np.sqrt(cov[0, 0]) / c[0] ** 2, np.sqrt(cov[1, 1]) / c[1] ** 2
        self.b7res = (ex["T"], B, sB, BA, sBA)
        self.b7l.config(text=f"T = {ex['T']:.0f} °C\nB = {B:.1f} ± {sB:.1f} nm²/min\nB/A = {BA:.3f} ± {sBA:.3f} nm/min")
        self._redraw()

    def _toB8(self):
        if self.b7res:
            T, B, sB, BA, sBA = self.b7res
            self.ainB8.insert("end", f"{T:.0f}\t{B:.1f}\t{sB:.1f}\t{BA:.3f}\t{sBA:.3f}\n")

    def _runB8(self):
        R = []
        for r in self.rows(self.ainB8.get("1.0", "end")):
            try:
                v = [float(x) for x in r[:5]]
            except ValueError:
                continue
            if len(v) == 5 and v[1] > 0 and v[3] > 0:
                R.append(v)
        if len(R) < 2:
            return
        R = np.array(R); x = 1 / (R[:, 0] + 273.15)
        out = {}
        for key, y, e in (("B", np.log(R[:, 1]), R[:, 2] / R[:, 1]), ("BA", np.log(R[:, 3]), R[:, 4] / R[:, 3])):
            w = 1 / np.maximum(e, 1e-6) ** 2
            if len(x) > 2:
                (b, a), cov = np.polyfit(x, y, 1, w=np.sqrt(w), cov="unscaled")
            else:
                (b, a), cov = np.polyfit(x, y, 1), np.zeros((2, 2))
            out[key] = (x, y, e, a, b, np.sqrt(cov[0, 0]))
        self.b8res = out
        self.b8l.config(text=f"ln B: {TXT['slope']} = {out['B'][4]:.0f} ± {out['B'][5]:.0f} K\n"
                             f"ln(B/A): {TXT['slope']} = {out['BA'][4]:.0f} ± {out['BA'][5]:.0f} K")
        self._redraw()

    # ---------------- drawing ----------------
    def _redraw(self):
        a1, a2 = self.ax1, self.ax2
        a1.clear(); a2.clear()
        k = self.task()
        if k == "A":
            for name, th, d, (P, D) in self.res_A or []:
                a1.plot(LAM, P, label=f"{name}: {th:g}°, {d:g} nm"); a2.plot(LAM, D, label=f"{name}")
            a1.set_ylabel("Ψ, deg"); a2.set_ylabel("Δ, deg"); a2.set_xlabel("λ, nm")
        elif k == "B12":
            dat = DATA[self.samp.get()]
            a1.plot(LAM, dat[0], ".", label="data"); a2.plot(LAM, dat[1], ".", label="data")
            if self.res_B12 and self.res_B12[0] == self.samp.get():
                a1.plot(LAM, self.res_B12[1], label="fit"); a2.plot(LAM, self.res_B12[2], label="fit")
            a1.set_ylabel("Ψ, deg"); a2.set_ylabel("Δ, deg"); a2.set_xlabel("λ, nm")
        elif k == "B3":
            ex = self.exps.get(self.cur)
            if ex and ex["res"]:
                r = np.array(ex["res"]); a1.errorbar(r[:, 0], r[:, 1], yerr=r[:, 2], fmt=".", label=ex["name"])
            if ex and ex["frames"]:
                t, (P, D) = ex["frames"][-1]
                a2.plot(LAM, P, ".", label="Ψ"); a2.plot(LAM, D, ".", label="Δ")
                a2.set_title(f"{ex['name']} · Φ = {ex['phi']:g}° · T = {ex['T']:g} °C · t = {t} min")
            a1.set_xlabel("t, min"); a1.set_ylabel("d, nm"); a2.set_xlabel("λ, nm"); a2.set_ylabel("deg")
        else:
            if self.b8res:
                for ax, key, lab in ((a1, "B", "ln(B·min/nm²)"), (a2, "BA", "ln(B/A·min/nm)")):
                    x, y, e, a, b, sb = self.b8res[key]
                    ax.errorbar(x, y, yerr=e, fmt="o"); xs = np.array([x.min(), x.max()])
                    ax.plot(xs, a + b * xs, label=f"{TXT['slope']} {b:.0f} ± {sb:.0f} K"); ax.set_ylabel(lab)
            a2.set_xlabel("1/T, 1/K")
        for ax in (a1, a2):
            ax.grid(True, alpha=0.4)
            if ax.get_legend_handles_labels()[0]:
                ax.legend(fontsize=8)
        self.fig.tight_layout(); self.canvas.draw_idle()

    def _csv(self):
        p = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=f"ISPhO2024_T1_{self.task()}.csv")
        if not p:
            return
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); k = self.task()
            if k == "A" and self.res_A:
                w.writerow(["lambda_nm"] + [s for r in self.res_A for s in (r[0] + "_Psi", r[0] + "_Delta")])
                for i, l in enumerate(LAM):
                    w.writerow([l] + [f"{v:.5f}" for r in self.res_A for v in (r[3][0][i], r[3][1][i])])
            elif k == "B12":
                dat = DATA[self.samp.get()]; w.writerow(["lambda_nm", "Psi_deg", "Delta_deg"])
                for i, l in enumerate(LAM):
                    w.writerow([l, f"{dat[0][i]:.3f}", f"{dat[1][i]:.3f}"])
            elif k == "B3" and self.exps.get(self.cur, {}).get("res"):
                w.writerow(["t_min", "d_nm", "dd_nm"])
                for t, d, e in self.exps[self.cur]["res"]:
                    w.writerow([t, f"{d:.2f}", f"{e:.2f}"])


if __name__ == "__main__":
    App().mainloop()
