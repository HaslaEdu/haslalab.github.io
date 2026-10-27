#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  Nordic-Baltic Physics Olympiad 2018  (Tallinn, Estonia)
  Problem 9 :  BLACK BOX
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The tools of the problem: a black box with three wires - white, blue
    and black - holding a battery, a capacitor, and an inductor in series
    with a diode, joined in a star; a multimeter (10 MOhm as a voltmeter,
    a new reading every 0.4 s) and a stopwatch.  The diode is ideal, the
    battery and the capacitor have no internal resistance, the inductor
    has a considerable one.
    The box is solved in time: the capacitor keeps its charge, the
    inductor its current, and a contact that opens on that current with
    nowhere else to go makes a spark.  Only what the student would see is
    shown: the meter's digits, the stopwatch and the spark.  The values
    are randomised each session; --seed N repeats a session.

    Run:   python3 nbpho2018_E2_blackbox_sim_KO.py   [--seed N]
"""
import math
import random
import time
import sys
import tkinter as tk

APP_VERSION = "1.0"
LANG = "KO"          # the EN edition differs only in this line


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
#  1.  상자 속 (학생에게 보이지 않음) — 공식 해설에 맞춤: 회로 B
# ==============================================================================
BOX_E = 9.5 * (1 + 0.02 * gauss())          # 전지 기전력 (V)
BOX_RL = 100 * (1 + 0.05 * gauss())         # 인덕터 저항 (Ω)
BOX_C = 1.0e-6 * (1 + 0.06 * gauss())       # 전기용량 (F)
BOX_L = 0.100 * (1 + 0.06 * gauss())        # 인덕턴스 (H)

DIAL = ["OFF", "400mV", "4V", "40V", "400V", "40mA", "400mA", "10A", "400Ω", "4kΩ", "40kΩ", "400kΩ"]
# kind, full scale, decimals, display multiplier, accuracy, ohmmeter test current
RANGE = {"400mV": ("V", 0.4, 1, 1000, 0.006, 0), "4V": ("V", 4, 3, 1, 0.006, 0), "40V": ("V", 40, 2, 1, 0.006, 0), "400V": ("V", 400, 1, 1, 0.006, 0),
         "40mA": ("A", 0.04, 2, 1000, 0.01, 0), "400mA": ("A", 0.4, 1, 1000, 0.01, 0), "10A": ("A10", 10, 2, 1, 0.015, 0),
         "400Ω": ("R", 400, 1, 1, 0.01, 1e-3), "4kΩ": ("R", 4000, 3, 1e-3, 0.01, 1e-4), "40kΩ": ("R", 40000, 2, 1e-3, 0.01, 1e-5), "400kΩ": ("R", 400000, 1, 1e-3, 0.01, 1e-6)}
CAL = {r: (max(-0.8, min(0.8, 0.35 * gauss())) * v[4], max(-2, min(2, int(round(gauss()))))) for r, v in RANGE.items()}
R_V, R_MA, R_10A, R_LEAD = 10e6, 1.0, 0.01, 0.02
TERMS = ["W", "U", "K", "X10A", "XmA", "XCOM", "XV"]
INNER = ["cen", "lm", "ld"]


class State(object):
    def __init__(self):
        self.wires = []           # (a, b)
        self.held = None
        self.dial = 0
        self.fuse = False
        self.burnt = False
        self.vc = 0.0             # V(white) - V(centre)
        self.il = 0.0             # 인덕터 전류
        self.don = False          # 다이오드가 통하는지
        self.fast = 0.0           # 이 시각까지는 잘게 나눠 푼다
        self.t = 0.0
        self.sw_run = False
        self.sw_t0 = 0.0
        self.sw_acc = 0.0
        self.spark = None         # (단자, 시각)


S = State()


def elements():
    E = [(a, b, "R", R_LEAD) for a, b in S.wires]
    E += [("cen", "K", "V", BOX_E, 1e-3), ("W", "cen", "C", BOX_C), ("cen", "lm", "R", BOX_RL), ("lm", "ld", "L", BOX_L), ("ld", "U", "D", 0)]
    R = RANGE.get(DIAL[S.dial])
    if not S.burnt:
        E.append(("X10A", "XCOM", "R", R_10A))
        if not S.fuse:
            E.append(("XmA", "XCOM", "R", R_MA))
        if R and R[0] == "V":
            E.append(("XV", "XCOM", "R", R_V))
        if R and R[0] == "R":
            E += [("XCOM", "XV", "I", R[5]), ("XV", "XCOM", "R", 100 / R[5])]
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


def solve_step(h, don):
    """후진 오일러 한 걸음: 축전기·인덕터는 동반 전원, 다이오드는 닫힌/열린 접점"""
    nodes = [t for t in TERMS + INNER if t != "K"]
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
    for e in elements():
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
        elif k == "C":
            g = v / h
            st(a, b, g)
            inj(a, g * S.vc)
            inj(b, -g * S.vc)
        elif k == "L":
            st(a, b, h / v)
            inj(a, -S.il)
            inj(b, S.il)
        elif k == "D":
            st(a, b, 1 / 0.02 if don else 1e-10)
    for i in range(N):
        G[i][i] += 1e-12
    V = gauss_solve(G, I)
    return lambda t: 0.0 if t == "K" else V[idx[t]]


SOL = [lambda t: 0.0]


def advance(h):
    don = S.don
    s = None
    for _ in range(4):
        s = solve_step(h, don)
        il = S.il + h / BOX_L * (s("lm") - s("ld"))
        want = il > 0 if don else (s("ld") - s("U")) > 1e-6
        if want == don:
            break
        don = want
    S.don = don
    S.il = max(0.0, S.il + h / BOX_L * (s("lm") - s("ld"))) if don else 0.0
    S.vc = s("W") - s("cen")
    SOL[0] = s


def topology_changed(where, app):
    """접점이 열렸는데 인덕터 전류가 갈 곳이 없으면 불꽃이 튀고 전류가 사라진다"""
    if S.il > 2e-3:
        keep = (S.vc, S.il, S.don)
        s = solve_step(1e-6, S.don)
        vmax = max(abs(s(t)) for t in TERMS + INNER)
        S.vc, S.il, S.don = keep
        if vmax > 300:
            S.il, S.don = 0.0, False
            if where:
                S.spark = (where, time.time())
            app.say(T("접점에서 작은 불꽃이 튀었습니다", "a small spark jumped at the contact"))
    S.fast = S.t + 0.06


def step(dt):
    if S.burnt:
        return
    left = dt
    while left > 1e-12:
        fast = S.t < S.fast
        h = min(4e-5, left) if fast else min(left, 0.004)
        advance(h)
        S.t += h
        left -= h


def meter_reading():
    d = DIAL[S.dial]
    if d == "OFF" or S.burnt:
        return ""
    k, full, dec, mul, acc, it = RANGE[d]
    g, o = CAL[d]
    s = SOL[0]
    if k == "V":
        x = (s("XV") - s("XCOM")) * mul
    elif k == "A":
        x = 0.0 if S.fuse else (s("XmA") - s("XCOM")) / R_MA * mul
    elif k == "A10":
        x = (s("X10A") - s("XCOM")) / R_10A
    else:
        v = s("XV") - s("XCOM")
        if v > 2.9:
            return "OL"
        x = v / it * mul
    x = x * (1 + g) + (o + 0.5 * gauss()) * 10 ** (-dec)
    if abs(x) * 10 ** dec > 3999.4:
        return "-OL" if x < 0 else "OL"
    return "%.*f" % (dec, x)


# ==============================================================================
#  2.  화면
# ==============================================================================
BG, PANEL, PANEL2 = "#1c2027", "#22262d", "#2b2f36"
FG, FG_DIM, ACC = "#e8eef2", "#9aa3ab", "#f2c14e"
POS = {"W": (560, 200), "U": (600, 330), "K": (560, 460), "X10A": (900, 560), "XmA": (950, 560), "XCOM": (1000, 560), "XV": (1050, 560)}
WIRE = {"W": ("#efefe8", T("흰색", "white")), "U": ("#2b62c4", T("파란색", "blue")), "K": ("#18181a", T("검은색", "black"))}
LCOL = ["#c8262b", "#1d1d1f", "#2f8a3e", "#e3b21a", "#8a4fc0", "#d35400", "#16a085"]


class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title(T("NBPhO 2018 실험 시뮬레이터 — 문제 9 블랙박스", "NBPhO 2018 Experiment Simulator — Problem 9 Black box") + "   v" + APP_VERSION)
        self.geometry("1480x860")
        self.configure(bg=BG)
        self.msg = ("", 0)
        self.disp = ""
        self.last_read = 0
        self.last_t = time.time()
        self.mouse = (0, 0)
        self._build()
        self.after(30, self._tick)

    def say(self, m):
        self.msg = (m, time.time())

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x")
        tk.Label(top, text="NBPhO 2018  ·  " + T("문제 9 블랙박스", "Problem 9 Black box"), bg=BG, fg=ACC,
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=14, pady=6)
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, anchor="w", bg=BG, fg=FG_DIM, font=("Segoe UI", 9), text=T(
            "상자와 멀티미터 — 단자 두 개를 차례로 클릭해 도선 연결(전선 끝에는 악어 집게) · 우클릭: 그 단자의 도선 떼기",
            "the box and the meter — click two terminals in turn to run a lead (crocodile clips on the wire ends) · R-click a terminal: take its leads off")).pack(fill="x")
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
        H(T("스톱워치", "Stopwatch"))
        self.sw = tk.Label(right, text="00:00.00", bg="#aeb8a6", fg="#1a1d1a", font=("Consolas", 22, "bold"), width=9)
        self.sw.pack(padx=10, pady=2)
        row = tk.Frame(right, bg=PANEL)
        row.pack(fill="x", padx=10)
        tk.Button(row, text=T("시작 / 멈춤", "Start / stop"), command=self.sw_toggle, **bs).pack(side="left", expand=True, fill="x")
        tk.Button(row, text=T("0으로", "Reset"), command=self.sw_reset, **bs).pack(side="left", expand=True, fill="x")
        tk.Button(right, text=T("도선 모두 떼기", "Take off all leads"), command=self.clear, **bs).pack(fill="x", padx=10, pady=(8, 1))
        H(T("안내", "Notes"))
        tk.Label(right, justify="left", wraplength=265, bg=PANEL, fg=FG_DIM, font=("Segoe UI", 8), text=T(
            "• 다이오드는 이상적입니다: 한쪽으로는 완전히 통하고 반대쪽으로는 전혀 통하지 않습니다.\n• 전지와 축전기의 내부 저항은 무시하고, 인덕터에는 상당한 내부 저항이 있습니다.\n• 전압계일 때 멀티미터의 저항은 10 MΩ이고 0.4초마다 새 값을 보여 줍니다.\n• 전류가 흐르는 중에 집게를 떼면 접점을 잘 보세요.",
            "• The diode is ideal: it conducts one way and not at all the other.\n• The battery and the capacitor have no internal resistance; the inductor has a considerable one.\n• As a voltmeter the meter is 10 MΩ and shows a new reading every 0.4 s.\n• Take a clip off a wire while a current is flowing and watch the contact.")).pack(anchor="w", padx=10)
        self.status = tk.Label(right, justify="left", wraplength=265, bg="#12161b", fg=ACC, font=("Segoe UI", 9), anchor="nw", padx=8, pady=8)
        self.status.pack(fill="both", expand=True, padx=10, pady=10)
        self.cv.bind("<Button-1>", self.down)
        self.cv.bind("<Button-3>", self.right_click)
        self.cv.bind("<Motion>", lambda e: setattr(self, "mouse", (e.x, e.y)))

    def turn(self, d):
        S.dial = (S.dial + d) % len(DIAL)
        self.last_read = 0
        topology_changed(None, self)

    def sw_time(self):
        return S.sw_acc + (time.time() - S.sw_t0 if S.sw_run else 0)

    def sw_toggle(self):
        if S.sw_run:
            S.sw_acc += time.time() - S.sw_t0
            S.sw_run = False
        else:
            S.sw_t0 = time.time()
            S.sw_run = True

    def sw_reset(self):
        if not S.sw_run:
            S.sw_acc = 0.0

    def clear(self):
        had = S.wires[:]
        S.wires = []
        S.held = None
        if had:
            a, b = had[0]
            topology_changed(a if a in WIRE else b, self)

    def term_at(self, x, y):
        for t, (px, py) in POS.items():
            if abs(x - px) < 16 and abs(y - py) < 16:
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
        topology_changed(None, self)

    def right_click(self, e):
        t = self.term_at(e.x, e.y)
        if S.held:
            S.held = None
        elif t:
            had = [w for w in S.wires if t in w]
            S.wires = [w for w in S.wires if t not in w]
            if had:
                a, b = had[0]
                topology_changed(t if t in WIRE else (a if a in WIRE else b), self)

    def draw(self):
        c = self.cv
        c.delete("all")
        c.create_rectangle(170, 210, 430, 450, fill="#1d1e20", outline="#2c2d30", width=3)
        c.create_rectangle(215, 300, 385, 360, fill="#e9e6dc", outline="")
        c.create_text(300, 320, text="BLACK BOX", fill="#1b1b1b", font=("Arial", 16, "bold"))
        c.create_text(300, 343, text="NBPhO 2018", fill="#1b1b1b", font=("Arial", 10))
        for t, (x, y) in (("W", POS["W"]), ("U", POS["U"]), ("K", POS["K"])):
            col, name = WIRE[t]
            y0 = {"W": 290, "U": 330, "K": 370}[t]
            c.create_line(430, y0, 490, y0, (x - 40 + 490) / 2, y, x - 20, y, smooth=True, fill=col, width=7)
            c.create_line(x - 20, y, x + 14, y, fill="#c98a4a", width=3)
            c.create_text(x + 30, y, anchor="w", text=name, fill=FG_DIM, font=("Segoe UI", 10))
        c.create_rectangle(860, 300, 1090, 600, fill="#e8b417" if not S.burnt else "#5a4a2a", outline="")
        c.create_rectangle(880, 320, 1070, 380, fill="#b9bfb3", outline="")
        c.create_text(1060, 350, anchor="e", text=self.disp, fill="#1b1e1c", font=("Consolas", 24, "bold"))
        c.create_text(975, 420, text=DIAL[S.dial], fill="#1b1e1c", font=("Segoe UI", 12, "bold"))
        c.create_text(975, 470, text="10 MΩ", fill="#1b1e1c", font=("Segoe UI", 9))
        for t, lab in (("X10A", "10A"), ("XmA", "mA"), ("XCOM", "COM"), ("XV", "VΩ")):
            x, y = POS[t]
            c.create_text(x, y - 24, text=lab, fill="#1b1e1c", font=("Segoe UI", 9, "bold"))
        for t, (x, y) in POS.items():
            if t[0] == "X":
                col = "#1d1d1f" if t == "XCOM" else "#c8262b"
                c.create_oval(x - 9, y - 9, x + 9, y + 9, fill=col, outline="#f2c14e" if S.held == t else "#555", width=2 if S.held == t else 1)
            else:
                c.create_oval(x - 7, y - 7, x + 7, y + 7, fill="", outline="#f2c14e" if S.held == t else "#5b6168", width=2 if S.held == t else 1)
        for i, (a, b) in enumerate(S.wires):
            (x1, y1), (x2, y2) = POS[a], POS[b]
            mx, my = (x1 + x2) / 2 + 30, max(y1, y2) + 50 + 12 * (i % 4)
            col = LCOL[i % len(LCOL)]
            c.create_line(x1, y1, mx, my, x2, y2, smooth=True, fill=col, width=3)
            for (x, y) in ((x1, y1), (x2, y2)):
                c.create_rectangle(x - 5, y - 4, x + 5, y + 4, fill="#c9ced3", outline=col, width=2)
        if S.held:
            x1, y1 = POS[S.held]
            c.create_line(x1, y1, self.mouse[0], self.mouse[1], fill="#ff8a2a", width=2, dash=(4, 3))
        if S.spark and time.time() - S.spark[1] < 0.25:
            x, y = POS[S.spark[0]]
            for k in range(9):
                a = k * 2.4 + time.time() * 40
                r = 22 * (1 - (time.time() - S.spark[1]) / 0.25)
                c.create_line(x, y, x + r * math.cos(a), y + r * math.sin(a), fill="#fff6c8" if k % 2 else "#9fd4ff", width=2)

    def _tick(self):
        now = time.time()
        dt = min(0.08, now - self.last_t)
        self.last_t = now
        step(dt)
        s = SOL[0]
        if not S.burnt:
            imA = 0 if S.fuse else abs(s("XmA") - s("XCOM")) / R_MA
            i10 = abs(s("X10A") - s("XCOM")) / R_10A
            if imA > 0.45:
                S.fuse = True
                self.say(T("멀티미터의 퓨즈가 끊어졌습니다", "the meter's fuse has blown"))
                topology_changed(None, self)
            if i10 > 12:
                S.burnt = True
                self.say(T("멀티미터가 타 버렸습니다", "the meter has burnt out"))
        if now - self.last_read > 0.4:
            self.last_read = now
            self.disp = meter_reading()
        try:
            self.draw()
        except tk.TclError:
            return
        self.lcd.config(text=self.disp)
        self.dl.config(text=DIAL[S.dial])
        t = self.sw_time()
        self.sw.config(text="%02d:%05.2f" % (int(t // 60), t - 60 * int(t // 60)))
        w = []
        if self.msg[0] and now - self.msg[1] < 5:
            w.append(self.msg[0])
        if S.held:
            w.append(T("도선을 들고 있음: 다른 단자 클릭 (우클릭: 내려놓기)", "a lead in hand: click another terminal (R-click: put it away)"))
        self.status.config(text="\n\n".join(w))
        self.after(50, self._tick)


if __name__ == "__main__":
    App().mainloop()
