#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  Nordic-Baltic Physics Olympiad 2019  (Tallinn, Estonia)
  Problem 8 :  FOUR RESISTORS
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The tools of the problem: four almost identical resistors (slightly
    more than 4 kOhm) labelled A-D with the set number, a multimeter with
    a four-digit display whose first digit is only 0-3, a voltage source
    adjustable to 30 V, and wires.  The ohmmeter is good to 1 % + 4
    digits, the voltmeter to 0.6 % + 4 digits, and those errors stay the
    same within a range.  Do not use the ammeter function: a burnt meter
    is not replaced.
    Only what the student would see is shown: the meter's digits and the
    source's display.  The resistances are randomised each session;
    --seed N repeats a session.

    Run:   python3 nbpho2019_E1_resistors_sim_EN.py   [--seed N]
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
SET_NO = 1 + int(RNG.random() * 24)
R_BAR = 4670 * (1 + 0.004 * gauss())
_d = [x + 0.4 * gauss() for x in (4.0, -3.8, 1.4, -1.7)]
RNG.shuffle(_d)
_m = sum(_d) / 4
RES = [R_BAR + x - _m for x in _d]
NAMES = ["A", "B", "C", "D"]
DIAL = ["OFF", "400mV", "4V", "40V", "400V", "40mA", "400mA", "10A", "400Ω", "4kΩ", "40kΩ", "400kΩ"]
RANGE = {"400mV": ("V", 0.4, 1, 1000, 0.006), "4V": ("V", 4, 3, 1, 0.006), "40V": ("V", 40, 2, 1, 0.006), "400V": ("V", 400, 1, 1, 0.006),
         "40mA": ("A", 0.04, 2, 1000, 0.01), "400mA": ("A", 0.4, 1, 1000, 0.01), "10A": ("A10", 10, 2, 1, 0.015),
         "400Ω": ("R", 400, 1, 1, 0.01), "4kΩ": ("R", 4000, 3, 1e-3, 0.01), "40kΩ": ("R", 40000, 2, 1e-3, 0.01), "400kΩ": ("R", 400000, 1, 1e-3, 0.01)}
CAL = {r: (max(-0.8, min(0.8, 0.35 * gauss())) * v[4], max(-3, min(3, int(round(1.3 * gauss()))))) for r, v in RANGE.items()}
R_LEAD, R_SRC, R_MA, R_10A = 0.02, 0.05, 1.0, 0.01
SRC_GAIN = 1 + 0.004 * gauss()
TERMS = ["PSP", "PSN", "X10A", "XmA", "XCOM", "XV"] + [n + e for n in NAMES for e in "12"]


class State(object):
    def __init__(self):
        self.wires = []           # (a, b)
        self.held = None
        self.dial = 0
        self.src_on = False
        self.src_set = 10.0
        self.fuse = False
        self.burnt = False


S = State()


def elements():
    E = [(a, b, "R", R_LEAD) for a, b in S.wires]
    for i, n in enumerate(NAMES):
        E.append((n + "1", n + "2", "R", RES[i]))
    if S.src_on:
        E.append(("PSP", "PSN", "V", S.src_set * SRC_GAIN, R_SRC))
    k = RANGE.get(DIAL[S.dial], ("",))[0]
    if not S.burnt:
        E.append(("X10A", "XCOM", "R", R_10A))
        if not S.fuse:
            E.append(("XmA", "XCOM", "R", R_MA))
        if k == "V":
            E.append(("XV", "XCOM", "R", 10e6))
    return E


def gauss_solve(A, b):
    n = len(b)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        piv = M[c][c] or 1e-30
        for r in range(c + 1, n):
            k = M[r][c] / piv
            if k:
                for j in range(c, n + 1):
                    M[r][j] -= k * M[c][j]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (M[r][n] - sum(M[r][j] * x[j] for j in range(r + 1, n))) / (M[r][r] or 1e-30)
    return x


def solve(extra=None):
    E = elements() + ([extra] if extra else [])
    nodes = [t for t in TERMS if t != "PSN"]
    idx = {t: i for i, t in enumerate(nodes)}
    N = len(nodes)
    G = [[0.0] * N for _ in range(N)]
    I = [0.0] * N

    def st(a, b, g):
        ia, ib = idx.get(a), idx.get(b)
        if ia is not None:
            G[ia][ia] += g
        if ib is not None:
            G[ib][ib] += g
        if ia is not None and ib is not None:
            G[ia][ib] -= g
            G[ib][ia] -= g

    def inj(a, i):
        ia = idx.get(a)
        if ia is not None:
            I[ia] += i
    for e in E:
        a, b, k, v = e[0], e[1], e[2], e[3]
        if k == "R":
            st(a, b, 1 / v)
        elif k == "V":
            r = e[4]
            st(a, b, 1 / r)
            inj(a, v / r)
            inj(b, -v / r)
        elif k == "I":
            inj(a, -v)
            inj(b, v)
    for i in range(N):
        G[i][i] += 1e-12
    V = gauss_solve(G, I)
    return lambda t: 0.0 if t == "PSN" else V[idx[t]]


def meter_reading(sol):
    d = DIAL[S.dial]
    if d == "OFF" or S.burnt:
        return ""
    k, full, dec, mul, acc = RANGE[d]
    g, o = CAL[d]
    if k == "V":
        x = (sol("XV") - sol("XCOM")) * mul
    elif k == "A":
        x = 0.0 if S.fuse else (sol("XmA") - sol("XCOM")) / R_MA * mul
    elif k == "A10":
        x = (sol("X10A") - sol("XCOM")) / R_10A
    else:
        s = solve(("XCOM", "XV", "I", 1e-4))
        r = (s("XV") - s("XCOM")) / 1e-4
        if r > 1e9:
            return "OL"
        x = r * mul
    x = x * (1 + g) + (o + 0.6 * gauss()) * 10 ** (-dec)
    if abs(x) * 10 ** dec > 3999.4:
        return "-OL" if x < 0 else "OL"
    return "%.*f" % (dec, x)


# ==============================================================================
#  2.  화면
# ==============================================================================
BG, PANEL, PANEL2 = "#1c2027", "#22262d", "#2b2f36"
FG, FG_DIM, ACC = "#e8eef2", "#9aa3ab", "#f2c14e"
POS = {"PSP": (170, 470), "PSN": (230, 470), "X10A": (900, 520), "XmA": (950, 520), "XCOM": (1000, 520), "XV": (1050, 520)}
for _i, _n in enumerate(NAMES):
    POS[_n + "1"] = (450, 180 + 80 * _i)
    POS[_n + "2"] = (700, 180 + 80 * _i)
WCOL = ["#c8262b", "#1d1d1f", "#2f8a3e", "#2b62c4", "#e3b21a", "#ece9e2", "#8e44ad", "#d35400"]


class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title(T("NBPhO 2019 실험 시뮬레이터 — 문제 8 네 개의 저항", "NBPhO 2019 Experiment Simulator — Problem 8 Four resistors") + "   v" + APP_VERSION)
        self.geometry("1480x860")
        self.configure(bg=BG)
        self.msg = ("", 0)
        self.disp = ""
        self.last_read = 0
        self.mouse = (0, 0)
        self._build()
        self.after(30, self._tick)

    def say(self, m):
        self.msg = (m, time.time())

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x")
        tk.Label(top, text="NBPhO 2019  ·  " + T("문제 8 네 개의 저항 (10점)", "Problem 8 Four resistors (10 pts)"), bg=BG, fg=ACC,
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=14, pady=6)
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, anchor="w", bg=BG, fg=FG_DIM, font=("Segoe UI", 9), text=T(
            "회로 — 단자 두 개를 차례로 클릭해 전선 연결 · 우클릭: 그 단자의 전선 뽑기 · 멀티미터 단자에는 바나나 플러그 전선만",
            "the circuit — click two terminals in turn to run a wire · R-click a terminal: pull its wires · the meter's sockets take banana leads only")).pack(fill="x")
        self.cv = tk.Canvas(left, bg="#2e3238", highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        right = tk.Frame(body, bg=PANEL, width=300)
        right.pack(side="left", fill="y", padx=(8, 0))
        right.pack_propagate(False)
        bs = dict(bg=PANEL2, fg=FG, activebackground="#343941", activeforeground=FG, relief="flat", bd=0, padx=8, pady=5, font=("Segoe UI", 10))

        def H(t):
            tk.Label(right, text=t, bg=PANEL, fg=ACC, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        H(T("멀티미터 (3999)", "Multimeter (3999)"))
        self.lcd = tk.Label(right, text="", bg="#b9bfb3", fg="#1b1e1c", font=("Consolas", 26, "bold"), width=8, anchor="e")
        self.lcd.pack(padx=10, pady=2)
        row = tk.Frame(right, bg=PANEL)
        row.pack(fill="x", padx=10)
        tk.Button(row, text="◀", command=lambda: self.turn(-1), **bs).pack(side="left")
        self.dl = tk.Label(row, text="", bg=PANEL, fg=FG, font=("Segoe UI", 10, "bold"), width=12)
        self.dl.pack(side="left", expand=True)
        tk.Button(row, text="▶", command=lambda: self.turn(1), **bs).pack(side="left")
        H(T("전원 장치 (0–30 V)", "Voltage source (0–30 V)"))
        self.src_lbl = tk.Label(right, text="", bg="#101315", fg="#ff5a3a", font=("Consolas", 22, "bold"), width=8, anchor="e")
        self.src_lbl.pack(padx=10, pady=2)
        self.sc = tk.Scale(right, from_=0, to=300, orient="horizontal", showvalue=False, bg=PANEL, fg=FG, highlightthickness=0, troughcolor=PANEL2,
                           command=lambda v: setattr(S, "src_set", float(v) / 10))
        self.sc.set(100)
        self.sc.pack(fill="x", padx=10)
        self.b_src = tk.Button(right, command=self.t_src, **bs)
        self.b_src.pack(fill="x", padx=10, pady=1)
        tk.Button(right, text=T("전선 모두 뽑기", "Pull out all wires"), command=lambda: (S.wires.clear(), setattr(S, "held", None)), **bs).pack(fill="x", padx=10, pady=1)
        H(T("안내", "Notes"))
        tk.Label(right, justify="left", wraplength=265, bg=PANEL, fg=FG_DIM, font=("Segoe UI", 8), text=T(
            "• 멀티미터는 3999까지 표시합니다.\n• 저항계: ±(읽음의 1.0 % + 마지막 자리 4), 전압계: ±(0.6 % + 마지막 자리 4) — 한 범위 안에서는 같은 오차.\n• 전류계 기능을 쓰지 마세요: 태운 멀티미터는 바꿔 주지 않습니다.",
            "• The meter shows up to 3999.\n• Ohmmeter: ±(1.0 % of the reading + 4 last digits); voltmeter: ±(0.6 % + 4 last digits) — the same error within a range.\n• Do not use the ammeter function: a burnt meter is not replaced.")).pack(anchor="w", padx=10)
        self.status = tk.Label(right, justify="left", wraplength=265, bg="#12161b", fg=ACC, font=("Segoe UI", 9), anchor="nw", padx=8, pady=8)
        self.status.pack(fill="both", expand=True, padx=10, pady=10)
        self.cv.bind("<Button-1>", self.down)
        self.cv.bind("<Button-3>", self.right_click)
        self.cv.bind("<Motion>", lambda e: setattr(self, "mouse", (e.x, e.y)))

    def turn(self, d):
        S.dial = (S.dial + d) % len(DIAL)
        self.last_read = 0

    def t_src(self):
        S.src_on = not S.src_on

    def term_at(self, x, y):
        for t, (px, py) in POS.items():
            if abs(x - px) < 14 and abs(y - py) < 14:
                return t
        return None

    def down(self, e):
        t = self.term_at(e.x, e.y)
        if not t:
            S.held = None
            return
        if S.held is None:
            S.held = t
            return
        a = S.held
        if t == a:
            return
        if t[0] == "X" and a[0] == "X":
            self.say(T("멀티미터 단자끼리는 잇지 않습니다", "do not join two meter sockets"))
            return
        S.wires.append((a, t))
        S.held = None

    def right_click(self, e):
        t = self.term_at(e.x, e.y)
        if S.held:
            S.held = None
        elif t:
            S.wires = [w for w in S.wires if t not in w]

    def draw(self):
        c = self.cv
        c.delete("all")
        c.create_rectangle(400, 120, 760, 470, fill="#f3f1ea", outline="#bbbbbb")
        c.create_text(720, 455, text="Set %d" % SET_NO, fill="#222", font=("Arial", 11))
        bands = ["#d8c22a", "#6b2fa0", "#111111", "#7a4a22", "#7a4a22"]
        for i, n in enumerate(NAMES):
            y = 180 + 80 * i
            c.create_text(420, y - 22, text=n, fill="#222", font=("Arial", 14, "bold"))
            c.create_line(450, y, 700, y, fill="#9aa0a6", width=2)
            c.create_rectangle(545, y - 9, 605, y + 9, fill="#4f86c6", outline="")
            for j, col in enumerate(bands):
                x = 552 + j * 9 + (6 if j == 4 else 0)
                c.create_rectangle(x, y - 9, x + 4, y + 9, fill=col, outline="")
        c.create_rectangle(110, 360, 290, 500, fill="#d8dbd6", outline="")
        c.create_rectangle(125, 375, 275, 420, fill="#101315", outline="")
        c.create_text(265, 398, anchor="e", text=("%.1f V" % S.src_set) if S.src_on else "", fill="#ff5a3a", font=("Consolas", 20, "bold"))
        c.create_text(200, 440, text="DC 0–30 V", fill="#333")
        c.create_rectangle(860, 260, 1090, 560, fill="#e8b417" if not S.burnt else "#5a4a2a", outline="")
        c.create_rectangle(880, 280, 1070, 340, fill="#b9bfb3", outline="")
        c.create_text(1060, 310, anchor="e", text=self.disp, fill="#1b1e1c", font=("Consolas", 24, "bold"))
        c.create_text(975, 380, text=DIAL[S.dial], fill="#1b1e1c", font=("Segoe UI", 12, "bold"))
        for t, lab in (("X10A", "10A"), ("XmA", "mA"), ("XCOM", "COM"), ("XV", "VΩ")):
            x, y = POS[t]
            c.create_text(x, y - 24, text=lab, fill="#1b1e1c", font=("Segoe UI", 9, "bold"))
        for t, (x, y) in POS.items():
            col = "#c8262b" if t in ("PSP", "XV", "XmA", "X10A") else "#1d1d1f" if t in ("PSN", "XCOM") else "#c6ccd2"
            c.create_oval(x - 9, y - 9, x + 9, y + 9, fill=col, outline="#f2c14e" if S.held == t else "#555", width=2 if S.held == t else 1)
        for i, (a, b) in enumerate(S.wires):
            (x1, y1), (x2, y2) = POS[a], POS[b]
            mx, my = (x1 + x2) / 2, max(y1, y2) + 40 + 12 * (i % 4)
            c.create_line(x1, y1, mx, my, x2, y2, smooth=True, fill=WCOL[i % len(WCOL)], width=3)
        if S.held:
            x1, y1 = POS[S.held]
            c.create_line(x1, y1, self.mouse[0], self.mouse[1], fill="#ff8a2a", width=2, dash=(4, 3))

    def _tick(self):
        now = time.time()
        sol = solve()
        if not S.burnt:
            imA = 0 if S.fuse else abs(sol("XmA") - sol("XCOM")) / R_MA
            i10 = abs(sol("X10A") - sol("XCOM")) / R_10A
            if imA > 0.45:
                S.fuse = True
                self.say(T("멀티미터의 퓨즈가 끊어졌습니다", "the meter's fuse has blown"))
            if i10 > 12:
                S.burnt = True
                self.say(T("멀티미터가 타 버렸습니다 — 다른 멀티미터는 주지 않습니다", "the meter has burnt out — you will not be given another one"))
        if now - self.last_read > 0.4:
            self.last_read = now
            self.disp = meter_reading(sol)
        try:
            self.draw()
        except tk.TclError:
            return
        self.lcd.config(text=self.disp)
        self.dl.config(text=DIAL[S.dial])
        self.src_lbl.config(text=("%.1f V" % S.src_set) if S.src_on else "")
        self.b_src.config(text=T("전원: 켜짐", "Source: ON") if S.src_on else T("전원: 꺼짐", "Source: OFF"), bg=ACC if S.src_on else PANEL2, fg="#1c2027" if S.src_on else FG)
        w = []
        if self.msg[0] and now - self.msg[1] < 5:
            w.append(self.msg[0])
        if S.held:
            w.append(T("전선을 들고 있음: 다른 단자 클릭 (우클릭: 내려놓기)", "a wire in hand: click another terminal (R-click: put it away)"))
        self.status.config(text="\n\n".join(w))
        self.after(60, self._tick)


if __name__ == "__main__":
    App().mainloop()
