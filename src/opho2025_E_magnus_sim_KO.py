#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OPhO 2025 Invitational, Part II — Experimental question "Ball Knowledge"
A football kicked on an unknown planet, filmed by a camera of fixed frame rate.

Like the organisers' magnus.exe it asks for v0, theta0, omega0 and a file name and writes the
camera's points as "x,y" lines to two decimals, the format the organisers' plotting notebook
reads.  Same model as the HaslaLab browser version:
    F_drag = -1/2 rho Cd A v^2 v_hat,   F_Magnus = K r omega x v,   d omega/dt = -B omega v
with v the velocity relative to the air.  The wind, rho, g, the frame rate, K and B are hidden;
no official solution was published, so the hidden values were chosen by HaslaLab.

    python opho2025_E_magnus_sim.py
"""

import math, os, random
import tkinter as tk
from tkinter import ttk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
matplotlib.rcParams["font.family"] = ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

LANG = "KO"

TXT = {
 "KO": dict(title="OPhO 2025 실험 — 공 감각 (magnus)", v0="초기 속력 v₀ (m/s)", th="발사각 θ₀ (°)",
            w0="초기 각속도 ω₀ (rad/s)", fn="출력 파일 이름", run="시뮬레이션 실행", hold="이전 궤적 함께 그리기",
            bad="입력값이 범위를 벗어났습니다.",
            help="v₀ ∈ [5, 40] m/s, θ₀ > 0, ω₀ ∈ [−400, 400] rad/s\n(양수 = 아랫회전). 파일은 이 프로그램이 있는 폴더에 저장됩니다."),
 "EN": dict(title="OPhO 2025 Experimental — Ball Knowledge (magnus)", v0="initial speed v0 (m/s)", th="launch angle theta0 (deg)",
            w0="initial angular velocity omega0 (rad/s)", fn="output file name", run="run the simulation",
            hold="keep earlier trajectories", bad="An input is out of range.",
            help="v0 in [5, 40] m/s, theta0 > 0, omega0 in [-400, 400] rad/s\n(positive = underspin). Files are saved next to this program."),
}[LANG]

P = dict(vw=-2.6, rho=1.62, g=7.35, rc=24, K=0.0062, B=0.0115)        # the planet, hidden
R, M, CD = 0.11, 0.43, 0.47
A = math.pi * R * R


def deriv(s):
    ux, uy = s[2] - P["vw"], s[3]; u = math.hypot(ux, uy)
    kd = 0.5 * P["rho"] * CD * A * u / M; km = P["K"] * R * s[4] / M
    return [s[2], s[3], -kd * ux - km * uy, -kd * uy + km * ux - P["g"], -P["B"] * s[4] * u]


def fly(v0, th, w0):
    v0 += random.gauss(0, 0.5); th += random.gauss(0, 0.5); w0 += random.gauss(0, 1.0)
    s = [0, 0, v0 * math.cos(math.radians(th)), v0 * math.sin(math.radians(th)), w0]
    t, h, frame = 0.0, 1e-4, 1 / P["rc"]; out = [(0.0, 0.0)]; nxt = frame
    while t < 60:
        k1 = deriv(s); k2 = deriv([v + h / 2 * k for v, k in zip(s, k1)])
        k3 = deriv([v + h / 2 * k for v, k in zip(s, k2)]); k4 = deriv([v + h * k for v, k in zip(s, k3)])
        prev = s
        s = [v + h / 6 * (a + 2 * b + 2 * c + d) for v, a, b, c, d in zip(s, k1, k2, k3, k4)]; t += h
        if s[1] < 0:                                    # the landing point closes the file, as in the official example
            f = prev[1] / (prev[1] - s[1]); out.append((prev[0] + f * (s[0] - prev[0]), 0.0))
            break
        if t >= nxt - 1e-12:
            out.append((s[0] + random.gauss(0, 0.004), s[1] + random.gauss(0, 0.004))); nxt += frame
    return out


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TXT["title"]); self.geometry("1180x760"); self.traces = []
        left = ttk.Frame(self, padding=10); left.pack(side="left", fill="y")
        right = ttk.Frame(self, padding=6); right.pack(side="right", fill="both", expand=True)
        self.v = {}
        for k, val in (("v0", "20"), ("th", "35"), ("w0", "0"), ("fn", "output.txt")):
            ttk.Label(left, text=TXT[k]).pack(anchor="w")
            self.v[k] = tk.StringVar(value=val); ttk.Entry(left, textvariable=self.v[k], width=22).pack(anchor="w", pady=(0, 4))
        ttk.Button(left, text=TXT["run"], command=self.run).pack(fill="x", pady=4)
        self.hold = tk.BooleanVar(value=True); ttk.Checkbutton(left, text=TXT["hold"], variable=self.hold).pack(anchor="w")
        ttk.Label(left, text=TXT["help"], wraplength=230, foreground="#555").pack(anchor="w", pady=8)
        self.term = tk.Text(right, height=10, bg="#0c0c0c", fg="#d7d7d7", font=("Consolas", 10)); self.term.pack(fill="x")
        self.fig = Figure(figsize=(9, 4.6), dpi=100); self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right); self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.say("magnus_sim  —  loading ... ok"); self.draw()

    def say(self, s):
        self.term.insert("end", s + "\n"); self.term.see("end")

    def run(self):
        try:
            v0, th, w0 = float(self.v["v0"].get()), float(self.v["th"].get()), float(self.v["w0"].get())
        except ValueError:
            self.say(TXT["bad"]); return
        fn = self.v["fn"].get().strip() or "output.txt"
        for q, a in zip(("Initial speed v0 (m/s): ", "Launch angle theta0 (deg): ",
                         "Initial angular velocity omega0 (rad/s): ", "Output file name: "), (v0, th, w0, fn)):
            self.say(q + str(a))
        if not (5 <= v0 <= 40 and 0 < th < 90 and -400 <= w0 <= 400):
            self.say(TXT["bad"]); return
        pts = fly(v0, th, w0)
        path = os.path.abspath(fn)
        with open(path, "w") as f:
            f.write("x,y\n"); f.writelines(f"{x:.2f},{y:.2f}\n" for x, y in pts)
        self.say(f"Output saved to: {path}  ({len(pts)} points)")
        self.say("Would you like to run the simulation again? (y/n): y")
        if not self.hold.get():
            self.traces = []
        self.traces = (self.traces + [(f"{fn} (v0={v0}, th={th}, w0={w0})", pts)])[-6:]
        self.draw()

    def draw(self):
        ax = self.ax; ax.clear()
        for name, pts in self.traces:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], ".", ms=4, label=name)
        ax.set_aspect("equal", adjustable="datalim"); ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)"); ax.grid(alpha=.3)
        if self.traces:
            ax.legend(fontsize=8, loc="upper right")
        self.fig.tight_layout(); self.canvas.draw_idle()


if __name__ == "__main__":
    App().mainloop()
