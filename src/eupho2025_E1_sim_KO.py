#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  9th European Physics Olympiad  (EuPhO 2025, Sofia, Bulgaria)
  Experimental Problem 1 :  DEEP LEARNING   (tasks 1 - 6)
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rules
------------
* The box holds a voltage source +V (with a small internal resistance),
  the "neuron" y = A*sigma(w1*x1 + w2*x2 + b) behind an output resistor
  R_out, and two potentiometers.  A1-A2 is the whole track R_P, the
  slider is joined to A3 through the load resistor R_L (B the same,
  within tolerances).  The tracks are not perfectly linear.
* X1 and X2 load the circuit with 1 MOhm each.  A floating input wanders
  at random, so the output does as well.
* The multimeter is a real one: 10 MOhm on the voltage ranges, a 1 Ohm
  shunt on the mA range, a 1 mA test current on the Ohm ranges (so it
  reads nonsense in a live circuit), a last digit that flickers, and an
  overload "1".  A probe pushed into a terminal that already carries two
  banana plugs slips now and then unless the alligator clip holds it.
* Only the meter's display, the wiring and the knob positions are shown.
  R_P, R_L, A, w1, w2, b and R_out are never displayed; they are
  randomised for every session (--seed N repeats a session).

    Run:   python3 eupho2025_E1_sim_KO.py   [--seed N] [--lang ko|en]
"""

import math
import random
import sys
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


def sig(z):
    if z < -60:
        return 0.0
    return 1.0 / (1.0 + math.exp(-z))


TERMS = ["GND1", "GND2", "+V", "X1", "X2", "Y", "A1", "A2", "A3", "B1", "B2", "B3", "T"]
DIAL = ["OFF", "V20", "V2", "OHM20k", "OHM2k", "mA200"]
DIAL_LABEL = {"OFF": "OFF", "V20": "V= 20", "V2": "V= 2", "OHM20k": "Ω 20k",
              "OHM2k": "Ω 2k", "mA200": "mA 200"}
UNIT = {"V20": "V", "V2": "V", "mA200": "mA", "OHM2k": "Ω", "OHM20k": "kΩ"}


# --------------------------------------------------------------------------
#  The hidden truth of this session  (V, Ohm)
# --------------------------------------------------------------------------
class Truth(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.r = r
        self.A = r.uniform(2.65, 2.85)
        self.w1 = r.choice((-1, 1)) * r.uniform(0.45, 0.80)
        self.w2 = r.choice((-1, 1)) * r.uniform(0.75, 1.10)
        self.b = r.uniform(0.6, 1.9) * (-1 if r.random() < 0.2 else 1)
        self.Rout = r.uniform(255, 315)
        self.Vs = r.uniform(3.20, 3.30)
        self.Rs = r.uniform(10, 16)
        self.Rin = 1.0e6
        rp = r.uniform(960, 1060)
        rl = r.uniform(212, 232)
        self.RP = {"A": rp, "B": rp * (1 + r.gauss(0, 0.01))}
        self.RL = {"A": rl, "B": rl * (1 + r.gauss(0, 0.01))}
        self.taper = {"A": r.uniform(0.04, 0.08), "B": r.uniform(0.04, 0.08)}
        self.gain = 1 + r.gauss(0, 0.002)


def gsolve(G, I):
    n = len(I)
    M = [G[i][:] + [I[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-30:
            M[c][c] += 1e-18
            p = c
        M[c], M[p] = M[p], M[c]
        pv = M[c][c]
        for r in range(n):
            if r == c:
                continue
            f = M[r][c] / pv
            if f:
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] for i in range(n)]


# --------------------------------------------------------------------------
#  The bench: wires, probes, knobs, and the circuit they make
# --------------------------------------------------------------------------
class Bench(object):
    def __init__(self, seed=None):
        self.t = Truth(seed)
        r = self.t.r
        self.knob = {"A": r.uniform(0.2, 0.8), "B": r.uniform(0.2, 0.8)}
        self.wires = []
        self.probe = {"com": None, "v": None}
        self.dial = "OFF"
        self.clip = False
        self.drift = {"X1": r.uniform(0, 3), "X2": r.uniform(0, 3)}

    def frac(self, k):
        th = self.knob[k]
        return min(1.0, max(0.0, th + self.t.taper[k] * math.sin(2 * math.pi * th)))

    def groups(self):
        par = dict((t, t) for t in TERMS)

        def f(x):
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x

        def un(a, b):
            ra, rb = f(a), f(b)
            if ra != rb:
                par[ra] = rb
        un("GND1", "GND2")
        for a, b in self.wires:
            un(a, b)
        return f

    def meter_on(self):
        return self.dial != "OFF" and self.probe["com"] and self.probe["v"]

    def solve(self, dial=None):
        """node voltages with the meter on its probes; returns the meter's reading (SI) or None"""
        dial = dial or self.dial
        t, f = self.t, self.groups()
        roots = sorted(set(f(x) for x in TERMS))
        idx = dict((r, i) for i, r in enumerate(roots))
        N = len(roots) + 3
        WA, WB, YI = len(roots), len(roots) + 1, len(roots) + 2
        n = lambda k: idx[f(k)]
        g0 = n("GND1")
        on = dial != "OFF" and self.probe["com"] and self.probe["v"]
        pc, pv = (n(self.probe["com"]), n(self.probe["v"])) if on else (-1, -1)

        def floating(k):
            if any(k in w for w in self.wires):
                return False
            return not (on and k in (self.probe["com"], self.probe["v"]))

        def run(y):
            G = [[0.0] * N for _ in range(N)]
            I = [0.0] * N

            def sg(a, b, g):
                G[a][a] += g
                G[b][b] += g
                G[a][b] -= g
                G[b][a] -= g
            for i in range(N):
                G[i][i] += 1e-12
            G[g0][g0] += 1e6
            sg(n("+V"), g0, 1 / t.Rs)
            I[n("+V")] += t.Vs / t.Rs
            for k, W in (("A", WA), ("B", WB)):
                fr = self.frac(k)
                sg(n(k + "1"), W, 1 / (fr * t.RP[k] + 0.3))
                sg(W, n(k + "2"), 1 / ((1 - fr) * t.RP[k] + 0.3))
                sg(W, n(k + "3"), 1 / t.RL[k])
            sg(n("X1"), g0, 1 / t.Rin)
            sg(n("X2"), g0, 1 / t.Rin)
            sg(YI, n("Y"), 1 / t.Rout)
            sg(YI, g0, 1e3)
            I[YI] += y * 1e3
            if on:
                if dial.startswith("V"):
                    sg(pc, pv, 1e-7)
                elif dial.startswith("mA"):
                    sg(pc, pv, 1.0)
                else:
                    I[pv] += 1e-3
                    I[pc] -= 1e-3
            return gsolve(G, I)

        y, v = t.A / 2, None
        for _ in range(40):
            v = run(y)
            x1 = self.drift["X1"] if floating("X1") else v[n("X1")]
            x2 = self.drift["X2"] if floating("X2") else v[n("X2")]
            yn = t.A * sig(t.w1 * x1 + t.w2 * x2 + t.b)
            if abs(yn - y) < 1e-7:
                y = yn
                break
            y = 0.5 * y + 0.5 * yn
        if not on:
            return None
        dv = v[pv] - v[pc]
        if dial.startswith("V"):
            return dv
        if dial.startswith("mA"):
            return dv / 1.0
        return dv / 1e-3

    def display(self):
        if self.dial == "OFF":
            return ""
        r = self.solve()
        if r is None:
            return "1   ." if self.dial.startswith("OHM") else "0.00"
        g = self.t.r.gauss
        r *= self.t.gain
        d = self.dial
        if d == "V20":
            q = r + g(0, 0.004)
            return "1   ." if abs(q) > 19.99 else "%.2f" % q
        if d == "V2":
            q = r + g(0, 0.0006)
            return "1   ." if abs(q) > 1.999 else "%.3f" % q
        if d == "mA200":
            q = r * 1000 + g(0, 0.06)
            return "1   ." if abs(q) > 199.9 else "%.1f" % q
        if d == "OHM2k":
            return "1   ." if (r < 0 or r > 1999) else "%d" % round(r + g(0, 0.6))
        if d == "OHM20k":
            return "1   ." if (r < 0 or r > 19990) else "%.2f" % (r / 1000 + g(0, 0.002))
        return ""

    def unstable(self):
        if self.clip:
            return False
        for w in ("com", "v"):
            k = self.probe[w]
            if k and sum(1 for x in self.wires if k in x) >= 2:
                return True
        return False

    def shorted(self):
        f = self.groups()
        return f("+V") == f("GND1")

    def live_ohm(self):
        if not self.dial.startswith("OHM") or not self.meter_on():
            return False
        r = self.solve("V20")
        return r is not None and abs(r) > 2e-3

    def step(self, dt):
        for k in ("X1", "X2"):
            self.drift[k] = min(3.3, max(0.0, self.drift[k] + self.t.r.gauss(0, 0.9) * math.sqrt(dt)))


# --------------------------------------------------------------------------
#  The lid of the box, seen from above
# --------------------------------------------------------------------------
TPOS = {"GND1": (-11.5, -5.5), "+V": (-7.5, -5.5), "X1": (-3.5, -5.5), "X2": (0.5, -5.5),
        "Y": (4.5, -5.5), "GND2": (8.5, -5.5), "T": (12, -5.5),
        "A1": (-10, 6.5), "A2": (-7, 6.5), "A3": (-4, 6.5), "B1": (4, 6.5), "B2": (7, 6.5), "B3": (10, 6.5)}
KPOS = {"A": (-7, 1.8), "B": (7, 1.8)}
WCOL = ["#c0392b", "#1b1d20", "#2f6fd0", "#e8c22a", "#2e9e57", "#8e44ad", "#e67e22", "#7f8c8d"]


def tcol(k):
    if k.startswith("GND"):
        return "#1b1d20"
    if k == "+V":
        return "#d0352b"
    if k.startswith("X"):
        return "#e8c22a"
    if k == "Y":
        return "#2f6fd0"
    if k == "T":
        return "#7a7f86"
    return "#ecece8"


class App(tk.Tk):
    W, H = 900, 560

    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.b = Bench(seed)
        self.title(T("EuPhO 2025 실험 1 — 딥러닝 · HaslaLab", "EuPhO 2025 Experiment 1 — Deep Learning · HaslaLab"))
        self.geometry("1360x820")
        self.sel = None          # a terminal waiting for the other end of a wire
        self.psel = None         # a probe in hand
        self.kdrag = None
        self.rows = 0
        self.k = 25.0
        self.cx, self.cy = 384, 290

        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=4)
        ttk.Label(top, text=T("EuPhO 2025 실험 1 — 딥러닝 (전자 뉴런)",
                              "EuPhO 2025 Experiment 1 — Deep Learning (an electronic neuron)"),
                  font=("Helvetica", 13, "bold")).pack(anchor="w")
        ttk.Label(top, wraplength=1320, text=T(
            "단자를 클릭하고 다른 단자를 클릭하면 바나나 전선이 이어집니다(겹쳐 꽂기 가능). 전선 가운데나 단자를 오른쪽 클릭하면 뺍니다. "
            "손잡이는 끌거나 휠로 돌립니다. 오른쪽의 탐침(검정 COM, 빨강 V)을 클릭한 뒤 단자를 클릭하면 탐침을 댑니다. "
            "y = Aσ(w₁x₁ + w₂x₂ + b), 출력 Y에는 직렬 저항 R_out. 계산은 대신 해주지 않습니다.",
            "Click a terminal and then another to join them with a banana wire (plugs can be stacked). Right-click the middle of "
            "a wire or a terminal to unplug. Drag a knob or use the wheel to turn it. Click a probe on the right (black COM, red V) "
            "and then a terminal to touch it there. y = Aσ(w₁x₁ + w₂x₂ + b), with R_out in series with Y. No calculation is done for you.")
        ).pack(anchor="w")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=8, pady=4)
        self.cv = tk.Canvas(body, width=self.W, height=self.H, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack(side="left", anchor="n")
        side = ttk.Frame(body)
        side.pack(side="left", fill="both", expand=True, padx=10)

        ttk.Label(side, text=T("멀티미터", "Multimeter"), font=("Helvetica", 11, "bold")).pack(anchor="w")
        self.lcd = tk.Label(side, text="", font=("Courier", 30, "bold"), bg="#b9c4a3", fg="#1b1d20",
                            width=11, anchor="e", relief="sunken")
        self.lcd.pack(anchor="w", pady=2)
        dl = ttk.Frame(side)
        dl.pack(anchor="w")
        self.dialvar = tk.StringVar(value="OFF")
        for i, k in enumerate(DIAL):
            ttk.Radiobutton(dl, text=DIAL_LABEL[k], value=k, variable=self.dialvar,
                            command=self.set_dial).grid(row=i // 3, column=i % 3, sticky="w", padx=4)
        self.prl = ttk.Label(side, text="")
        self.prl.pack(anchor="w", pady=2)
        self.clipvar = tk.BooleanVar(value=False)
        ttk.Checkbutton(side, text=T("악어 집게로 탐침 고정", "Hold the probe with the alligator clip"),
                        variable=self.clipvar, command=self.set_clip).pack(anchor="w")

        for k in ("A", "B"):
            row = ttk.Frame(side)
            row.pack(anchor="w", pady=2)
            lab = ttk.Label(row, text="", width=16)
            lab.pack(side="left")
            setattr(self, "kl" + k, lab)
            for dv in (-10, -1, 1, 10):
                ttk.Button(row, text=("%+d°" % dv), width=5,
                           command=lambda k=k, dv=dv: self.turn(k, dv)).pack(side="left", padx=1)

        ttk.Label(side, text=T("전선", "Wires"), font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(8, 0))
        self.wl = tk.Text(side, height=7, width=40, font=("Courier", 10))
        self.wl.pack(anchor="w")
        row = ttk.Frame(side)
        row.pack(anchor="w")
        ttk.Button(row, text=T("마지막 전선 빼기", "Unplug the last wire"), command=self.undo).pack(side="left", padx=1)
        ttk.Button(row, text=T("전선 모두 빼기", "Unplug all wires"), command=self.clear).pack(side="left", padx=1)

        ttk.Label(side, text=T("실험 노트", "Notebook"), font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(8, 0))
        self.cfg = ttk.Entry(side, width=44)
        self.cfg.pack(anchor="w")
        row = ttk.Frame(side)
        row.pack(anchor="w")
        ttk.Button(row, text=T("적기", "Write"), command=self.note).pack(side="left", padx=1)
        ttk.Button(row, text=T("지우기", "Clear"), command=lambda: self.notes.delete("1.0", "end")).pack(side="left", padx=1)
        self.notes = tk.Text(side, height=9, width=44, font=("Courier", 10))
        self.notes.pack(anchor="w")
        self.status = ttk.Label(side, text="", foreground="#8a1b1b", wraplength=420)
        self.status.pack(anchor="w", pady=4)
        self.msg = ""

        self.cv.bind("<ButtonPress-1>", self.on_down)
        self.cv.bind("<B1-Motion>", self.on_move)
        self.cv.bind("<ButtonRelease-1>", lambda e: setattr(self, "kdrag", None))
        self.cv.bind("<ButtonPress-3>", self.on_right)
        self.cv.bind("<MouseWheel>", self.on_wheel)
        self.cv.bind("<Button-4>", lambda e: self.on_wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self.on_wheel(e, -1))
        self.bind("<Escape>", lambda e: self.drop_sel())
        self.redraw()
        self.after(400, self.tick)

    # -- geometry --
    def X(self, u):
        return self.cx + u * self.k

    def Y(self, v):
        return self.cy + v * self.k

    def tpx(self, n):
        u, v = TPOS[n]
        return self.X(u), self.Y(v)

    def wire_mid(self, i):
        a, b = self.b.wires[i]
        (xa, ya), (xb, yb) = self.tpx(a), self.tpx(b)
        dx, dy = xb - xa, yb - ya
        L = math.hypot(dx, dy) or 1
        bend = 0.16 * L + 8 + 10 * (i % 3)
        mx, my = (xa + xb) / 2, (ya + yb) / 2
        c1 = (mx - dy / L * bend, my + dx / L * bend)
        c2 = (mx + dy / L * bend, my - dx / L * bend)
        far = lambda q: math.hypot(q[0] - self.cx, (q[1] - self.cy) * 1.6)
        return c1 if far(c1) >= far(c2) else c2

    PROBES = {"com": (800, 150), "v": (800, 300)}

    # -- drawing --
    def redraw(self):
        cv, b, k = self.cv, self.b, self.k
        cv.delete("all")
        cv.create_rectangle(self.X(-14), self.Y(-9), self.X(14), self.Y(9), fill="#a4aab1", outline="#6f757c", width=2)
        cv.create_text(self.X(0), self.Y(1.2), text="NEURON", font=("Helvetica", 18, "bold"), fill="#1b1d20")
        cv.create_text(self.X(0), self.Y(2.6), text="EuPhO 2025", font=("Helvetica", 11, "bold"), fill="#33373c")
        for kk, (u, v) in KPOS.items():
            cx, cy, R = self.X(u), self.Y(v), 1.6 * k
            for i in range(31):
                a = math.radians(-150 + 10 * i - 90)
                r2 = R * (1.30 if i % 5 else 1.42)
                cv.create_line(cx + 1.18 * R * math.cos(a), cy + 1.18 * R * math.sin(a),
                               cx + r2 * math.cos(a), cy + r2 * math.sin(a), fill="#333")
                if i % 5 == 0:
                    cv.create_text(cx + 1.65 * R * math.cos(a), cy + 1.65 * R * math.sin(a), text=str(i * 10),
                                   font=("Helvetica", 8), fill="#333")
            cv.create_oval(cx - R, cy - R, cx + R, cy + R, fill="#2a2c30", outline="#111", width=2)
            a = math.radians(-150 + 300 * b.knob[kk] - 90)
            cv.create_line(cx, cy, cx + 0.92 * R * math.cos(a), cy + 0.92 * R * math.sin(a), fill="#f2f2f0", width=4)
            cv.create_text(cx - 2.3 * R, cy - 1.3 * R, text=kk, font=("Helvetica", 20, "bold"))
        for n in TERMS:
            x, y = self.tpx(n)
            r = 0.62 * k
            cv.create_oval(x - r, y - r, x + r, y + r, fill=tcol(n), outline="#000", width=1.5)
            cv.create_oval(x - r * 0.38, y - r * 0.38, x + r * 0.38, y + r * 0.38, fill="#111", outline="")
        for i, (a, c) in enumerate(b.wires):
            (xa, ya), (xb, yb), (mx, my) = self.tpx(a), self.tpx(c), self.wire_mid(i)
            col = WCOL[i % len(WCOL)]
            qx, qy = 2 * mx - (xa + xb) / 2, 2 * my - (ya + yb) / 2
            pts = []
            for s in range(17):
                t = s / 16.0
                pts += [(1 - t) ** 2 * xa + 2 * t * (1 - t) * qx + t * t * xb, (1 - t) ** 2 * ya + 2 * t * (1 - t) * qy + t * t * yb]
            cv.create_line(*pts, fill=col, width=5, capstyle="round")
            for x, y in ((xa, ya), (xb, yb)):
                cv.create_oval(x - 0.3 * k, y - 0.3 * k, x + 0.3 * k, y + 0.3 * k, fill=col, outline="#000")
            cv.create_oval(mx - 3, my - 3, mx + 3, my + 3, fill=col, outline="#fff")
        for n in TERMS:
            x, y = self.tpx(n)
            if self.sel == n:
                cv.create_oval(x - 22, y - 22, x + 22, y + 22, outline="#ff7a2a", width=3)
            cv.create_text(x, y + 0.62 * k + 12, text=n, font=("Helvetica", 10, "bold"))
        # the probes
        cv.create_rectangle(752, 60, 860, 500, fill="#d8d6cf", outline="#9a978e")
        cv.create_text(806, 80, text=T("탐침", "Probes"), font=("Helvetica", 11, "bold"))
        for w, col, lab in (("com", "#1b1d20", "COM"), ("v", "#c0392b", "V Ω mA")):
            px, py = self.PROBES[w]
            cv.create_rectangle(px - 34, py - 9, px + 34, py + 9, fill=col,
                                outline="#ff7a2a" if self.psel == w else "#000", width=3 if self.psel == w else 1)
            cv.create_text(px, py + 26, text=lab, font=("Helvetica", 10, "bold"))
            at = b.probe[w]
            cv.create_text(px, py + 44, text=("→ " + at) if at else T("(떼어 놓음)", "(free)"),
                           fill="#1a5" if at else "#777", font=("Helvetica", 10))
            if at:
                x, y = self.tpx(at)
                sgn = -1 if w == "com" else 1
                cv.create_line(x, y, x + sgn * 18, y - 30, fill=col, width=3, dash=(6, 4))
                cv.create_oval(x - 5, y - 5, x + 5, y + 5, fill=col, outline="#fff")
        if b.unstable():
            cv.create_text(806, 480, text=T("접촉 불안정", "unstable contact"), fill="#b3261e", font=("Helvetica", 10, "bold"))

    def refresh_panel(self):
        b = self.b
        self.prl.config(text="COM → %s · V → %s" % (b.probe["com"] or "—", b.probe["v"] or "—"))
        self.klA.config(text=T("A 손잡이 · ", "Knob A · ") + "%.0f°" % (300 * b.knob["A"]))
        self.klB.config(text=T("B 손잡이 · ", "Knob B · ") + "%.0f°" % (300 * b.knob["B"]))
        txt = "\n".join("%d. %s — %s" % (i + 1, a, c) for i, (a, c) in enumerate(b.wires)) or T("(전선 없음)", "(no wires)")
        self.wl.delete("1.0", "end")
        self.wl.insert("1.0", txt)
        st = []
        if b.shorted():
            st.append(T("+V와 GND가 전선으로 바로 이어져 있습니다!", "+V is wired straight to GND!"))
        if b.live_ohm():
            st.append(T("전류가 흐르는 회로에서 저항을 재고 있습니다 — 값을 믿을 수 없습니다.",
                        "You are measuring resistance in a live circuit: the value cannot be trusted."))
        if b.dial == "mA200":
            r = b.solve()
            if r is not None and abs(r) > 0.2:
                st.append(T("전류 범위로 전압원을 재면 퓨즈가 끊어질 수 있습니다.",
                            "Measuring a source on the current range may blow the fuse."))
        if self.msg:
            st.append("• " + self.msg)
        self.status.config(text="\n".join(st))

    def tick(self):
        b = self.b
        b.step(0.4)
        if b.dial == "OFF":
            s = "OFF"
        else:
            if b.unstable() and b.t.r.random() < 0.35:
                keep = b.probe["v"]
                b.probe["v"] = None
                s = b.display()
                b.probe["v"] = keep
            else:
                s = b.display()
            s = s + " " + UNIT.get(b.dial, "")
        self.lcd.config(text=s)
        self.refresh_panel()
        self.after(400, self.tick)

    # -- hands --
    def term_at(self, x, y):
        for n in TERMS:
            tx, ty = self.tpx(n)
            if math.hypot(x - tx, y - ty) < 0.62 * self.k + 5:
                return n
        return None

    def probe_at(self, x, y):
        for w, (px, py) in self.PROBES.items():
            if abs(x - px) < 40 and abs(y - py) < 20:
                return w
        return None

    def knob_at(self, x, y):
        for kk, (u, v) in KPOS.items():
            if math.hypot(x - self.X(u), y - self.Y(v)) < 1.6 * self.k:
                return kk
        return None

    def knob_ang(self, kk, x, y):
        u, v = KPOS[kk]
        return math.degrees(math.atan2(x - self.X(u), -(y - self.Y(v))))

    def on_down(self, e):
        b = self.b
        kk = self.knob_at(e.x, e.y)
        if kk:
            self.kdrag = (kk, self.knob_ang(kk, e.x, e.y))
            return
        w = self.probe_at(e.x, e.y)
        if w:
            self.sel = None
            self.psel = None if self.psel == w else w
            self.msg = T("%s 탐침을 들었습니다 — 댈 단자를 클릭하세요." % ("COM" if w == "com" else "V"),
                         "Holding the %s probe: click the terminal to touch." % ("COM" if w == "com" else "V")) if self.psel else ""
            self.redraw()
            return
        n = self.term_at(e.x, e.y)
        if not n:
            self.drop_sel()
            return
        if self.psel:
            b.probe[self.psel] = n
            self.msg = T("탐침을 %s에 댔습니다." % n, "Probe on %s." % n)
            self.psel = None
        elif not self.sel:
            self.sel = n
            self.msg = T("%s — 이을 단자를 클릭하세요." % n, "%s: click the terminal to join it to." % n)
        else:
            a, self.sel = self.sel, None
            if a == n:
                self.msg = T("같은 단자입니다.", "That is the same terminal.")
            else:
                b.wires.append((a, n))
                self.msg = T("%s — %s 전선을 이었습니다." % (a, n), "%s — %s joined." % (a, n))
        self.redraw()

    def on_move(self, e):
        if not self.kdrag:
            return
        kk, a0 = self.kdrag
        a = self.knob_ang(kk, e.x, e.y)
        da = a - a0
        if da > 180:
            da -= 360
        if da < -180:
            da += 360
        self.kdrag = (kk, a)
        self.turn(kk, da)

    def on_right(self, e):
        b = self.b
        self.drop_sel()
        w = self.probe_at(e.x, e.y)
        if w:
            b.probe[w] = None
            self.msg = T("탐침을 뗐습니다.", "Probe lifted.")
            self.redraw()
            return
        best, bd = -1, 16
        for i in range(len(b.wires)):
            mx, my = self.wire_mid(i)
            d = math.hypot(mx - e.x, my - e.y)
            if d < bd:
                best, bd = i, d
        if best >= 0:
            del b.wires[best]
            self.msg = T("전선을 뺐습니다.", "Wire unplugged.")
        else:
            n = self.term_at(e.x, e.y)
            if n:
                for w in ("v", "com"):
                    if b.probe[w] == n:
                        b.probe[w] = None
                        self.msg = T("탐침을 뗐습니다.", "Probe lifted.")
                        self.redraw()
                        return
                for i in range(len(b.wires) - 1, -1, -1):
                    if n in b.wires[i]:
                        del b.wires[i]
                        self.msg = T("전선을 뺐습니다.", "Wire unplugged.")
                        break
        self.redraw()

    def on_wheel(self, e, sgn=None):
        kk = self.knob_at(e.x, e.y)
        if not kk:
            return
        if sgn is None:
            sgn = 1 if e.delta > 0 else -1
        self.turn(kk, sgn)

    def drop_sel(self):
        self.sel = None
        self.psel = None
        self.redraw()

    def turn(self, kk, deg):
        self.b.knob[kk] = min(1.0, max(0.0, self.b.knob[kk] + deg / 300.0))
        self.redraw()
        self.refresh_panel()

    def set_dial(self):
        self.b.dial = self.dialvar.get()

    def set_clip(self):
        self.b.clip = self.clipvar.get()
        self.redraw()

    def undo(self):
        if self.b.wires:
            self.b.wires.pop()
        self.redraw()

    def clear(self):
        self.b.wires = []
        self.redraw()

    def note(self):
        self.rows += 1
        self.notes.insert("end", "%d)  %s\n" % (self.rows, self.cfg.get().strip()))
        self.notes.see("end")


def main():
    global LANG
    seed = None
    args = sys.argv[1:]
    if "--seed" in args:
        seed = int(args[args.index("--seed") + 1])
    if "--lang" in args:
        LANG = args[args.index("--lang") + 1].lower()
    App(seed).mainloop()


if __name__ == "__main__":
    main()
