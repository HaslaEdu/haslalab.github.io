#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  1st Gulf Physics Olympiad  (GPhO 2016, Riyadh, Saudi Arabia)
  Experimental Problem E1 :  ROLLING CYLINDER
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The apparatus of the problem sheet: a wooden board with holes at one
    end, two sticks put through them, two clamps on the sticks holding
    the board's end up, a measuring tape, a stopwatch (go / stop /
    clear), a pencil and a sealed cylindrical bottle (M = 50 g) with an
    unknown amount of an unknown viscous liquid.
    Only what the student would see is shown: the bottle rolling, the
    tape's marks, the pencil marks, the stopwatch.  No angle, speed or
    force is computed for you.  The hidden values (the liquid's
    resistance F = k v + F0, the critical slopes, the liquid's mass) are
    randomised for each session; --seed N repeats a session.

    Run:   python3 gpho2016_E1_rolling_sim_EN.py   [--seed N]
"""
import math
import random
import time
import sys
import tkinter as tk

APP_VERSION = "1.0"
LANG = "EN"          # the KO edition differs only in this line


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
G, M = 9.81, 0.050
D2R = math.pi / 180
TRUE = {
    "F0": 0.0166 * (1 + 0.05 * gauss()),       # N
    "k": 0.390 * (1 + 0.06 * gauss()),         # N s/m
    "ml": 0.0125 + 0.0010 * gauss(),           # kg
    "a1": (6.2 + 0.3 * gauss()) * D2R,
    "T0": 22 + 0.5 * gauss(), "visc": 0.035,
}
TRUE["Fsat"] = TRUE["ml"] * G
TRUE["a2"] = math.asin(TRUE["ml"] / M)

# 기하 (cm)
L, TH, SH, R, STICK_H = 68.0, 0.8, 65.5, 1.5, 36.0


class State(object):
    def __init__(self):
        self.clamps = [4.0, 4.0]          # 클램프 윗면의 높이 (cm)
        self.where = "tray"               # tray / board / desk / hand
        self.s = 0.0
        self.v = 0.0
        self.rolled = 0.0
        self.phi = 0.0
        self.x = -10.0
        self.vdesk = 0.0
        self.Tb = TRUE["T0"]
        self.marks = []
        self.t = 0.0
        self.sw_run = False
        self.sw_t0 = 0.0
        self.sw_acc = 0.0
        self.speed = 1


S = State()


def hc():
    return min(max(S.clamps), SH * 0.6)


def alpha():
    return math.asin(hc() / SH)


def top_at(s):
    a = alpha()
    return (math.cos(a) * s - math.sin(a) * TH, math.sin(a) * s + math.cos(a) * TH)


def bottle_c():
    if S.where == "board":
        a = alpha()
        p = top_at(S.s)
        return (p[0] - math.sin(a) * R, p[1] + math.cos(a) * R)
    return (S.x, R)


def k_eff():
    a = alpha()
    k = TRUE["k"] * math.exp(-TRUE["visc"] * (S.Tb - TRUE["T0"]))
    if a > TRUE["a1"]:
        beta = 0.4 + 2.2 * min(1.0, (a - TRUE["a1"]) / (TRUE["a2"] - TRUE["a1"]))
        k /= 1 + beta * S.rolled / 100.0
    return k


def physics(dt):
    if S.where == "hand":
        S.Tb += (34 - S.Tb) * (1 - math.exp(-dt / 60))
    else:
        S.Tb += (TRUE["T0"] - S.Tb) * (1 - math.exp(-dt / 400))
    if S.where == "board":
        a = alpha()
        F = M * G * math.sin(a)
        m = M * 1.6
        k = k_eff()
        F0 = TRUE["F0"] * math.exp(-0.5 * TRUE["visc"] * (S.Tb - TRUE["T0"]))
        if S.v <= 0 and F <= F0:
            S.v = 0.0
            return
        v = (S.v + dt * (F - F0) / m) / (1 + dt * k / m)
        if F0 + k * v > TRUE["Fsat"]:
            v = S.v + dt * (F - TRUE["Fsat"]) / m
        S.v = max(0.0, v)
        marg = (F - F0) / F0
        mod = max(0.0, min(0.9, 1 - marg / 0.25))
        ve = S.v * (1 + mod * math.sin(S.phi))
        ds = ve * 100 * dt
        S.s -= ds
        S.rolled += ds
        S.phi += ds / R
        if S.s < 0.4:
            S.where = "desk"
            S.x = top_at(0)[0] - 1.2
            S.vdesk = S.v * 100
    elif S.where == "desk" and S.vdesk > 0:
        ds = S.vdesk * dt
        S.x -= ds
        S.phi += ds / R
        S.vdesk = max(0.0, S.vdesk - 30 * dt)
        if S.x < -40:
            S.x, S.vdesk = -40.0, 0.0


# ==============================================================================
#  2.  화면
# ==============================================================================
BG, PANEL, PANEL2 = "#1c2027", "#22262d", "#2b2f36"
FG, FG_DIM, ACC, BAD = "#e8eef2", "#9aa3ab", "#f2c14e", "#f0a79f"


class Tape(object):
    def __init__(self):
        self.on = False
        self.x, self.y, self.ang = -1.0, 0.0, math.pi / 2

    def local(self, wx, wy):
        c, s = math.cos(self.ang), math.sin(self.ang)
        dx, dy = wx - self.x, wy - self.y
        return dx * c + dy * s, -dx * s + dy * c

    def contains(self, wx, wy):
        u, v = self.local(wx, wy)
        return -0.5 <= u <= 101 and -1.4 <= v <= 0.1


class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title(T("GPhO 2016 실험 시뮬레이터 — E1 구르는 원통", "GPhO 2016 Experiment Simulator — E1 Rolling cylinder") + "   v" + APP_VERSION)
        self.geometry("1440x860")
        self.configure(bg=BG)
        self.sx = 14.0
        self.ox = 120.0
        self.oy = 620.0
        self.tape = Tape()
        self.tool = None                # None / "pencil"
        self.drag = None
        self.rd = (0, 0, True)
        self._build()
        self._last = time.time()
        self.after(20, self._tick)

    def W2P(self, x, y):
        return (self.ox + x * self.sx, self.oy - y * self.sx)

    def P2W(self, px, py):
        return ((px - self.ox) / self.sx, (self.oy - py) / self.sx)

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x")
        tk.Label(top, text="GPhO 2016  ·  " + T("E1 구르는 원통 (7점)", "E1 Rolling cylinder (7 pts)"), bg=BG, fg=ACC,
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=14, pady=6)
        tk.Label(top, text=T("높이·길이는 줄자로, 시간은 스톱워치로 직접 재세요", "read heights and lengths off the tape and times off the stopwatch yourself"),
                 bg=BG, fg=FG_DIM, font=("Segoe UI", 9)).pack(side="left")
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, anchor="w", bg=BG, fg=FG_DIM, font=("Segoe UI", 9), text=T(
            "판 정면 — 휠: 확대 · 우클릭 끌기: 이동 · 클램프: 위아래로 끌기, 휠 1 mm (Shift 0.1 mm) · 줄자: 끌기, 줄자 위 휠: 기울이기 · 병: 집어서 판에 놓기",
            "board, front — wheel: zoom · right-drag: pan · clamp: drag up/down, wheel 1 mm (Shift 0.1 mm) · tape: drag, wheel over it: tilt · bottle: pick it up and set it on the board")).pack(fill="x")
        self.cv = tk.Canvas(left, bg="#20252c", highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        right = tk.Frame(body, bg=PANEL, width=300)
        right.pack(side="left", fill="y", padx=(8, 0))
        right.pack_propagate(False)
        bs = dict(bg=PANEL2, fg=FG, activebackground="#343941", activeforeground=FG, relief="flat", bd=0, padx=8, pady=6, font=("Segoe UI", 10))

        def H(t):
            tk.Label(right, text=t, bg=PANEL, fg=ACC, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(12, 4))
        H(T("스톱워치", "Stopwatch"))
        self.sw = tk.Label(right, text="0:00.00", bg="#12161b", fg=FG, font=("Consolas", 24, "bold"))
        self.sw.pack(fill="x", padx=10)
        row = tk.Frame(right, bg=PANEL)
        row.pack(fill="x", padx=10, pady=4)
        for txt, fn in (("go", self.sw_go), ("stop", self.sw_stop), ("clear", self.sw_clear)):
            tk.Button(row, text=txt, command=fn, **bs).pack(side="left", expand=True, fill="x", padx=2)
        H(T("부품", "Parts"))
        self.b_bottle = tk.Button(right, text="", command=self.take_bottle, **bs)
        self.b_bottle.pack(fill="x", padx=10, pady=2)
        self.b_pencil = tk.Button(right, text="", command=self.take_pencil, **bs)
        self.b_pencil.pack(fill="x", padx=10, pady=2)
        tk.Button(right, text=T("줄자 놓기 / 치우기", "Tape out / away"), command=self.toggle_tape, **bs).pack(fill="x", padx=10, pady=2)
        H(T("시간 배속", "Time"))
        row = tk.Frame(right, bg=PANEL)
        row.pack(fill="x", padx=10)
        self.sp_btn = []
        for s in (1, 2, 5, 10):
            b = tk.Button(row, text="%d×" % s, command=lambda s=s: self.set_speed(s), **bs)
            b.pack(side="left", expand=True, fill="x", padx=2)
            self.sp_btn.append((s, b))
        H(T("안내", "Notes"))
        tk.Label(right, justify="left", wraplength=278, bg=PANEL, fg=FG_DIM, font=("Segoe UI", 9), text=T(
            "• M = 50 g (병과 액체), g = 9.81 m/s².\n• 병을 열지 마세요.\n• 액체의 성질은 온도에 따라 달라집니다. 병을 쥐는 시간을 최소로 하세요.\n• 판의 위쪽 끝은 더 높은 클램프에 얹힙니다.\n• 연필: 판을 클릭해 표시, 표시를 우클릭하면 지웁니다.",
            "• M = 50 g (bottle and liquid), g = 9.81 m/s².\n• Do not open the bottle.\n• The liquid's properties depend on temperature: hold the bottle as briefly as you can.\n• The board's upper end rests on the higher clamp.\n• Pencil: click the board to mark it; R-click a mark to rub it out.")).pack(anchor="w", padx=10)
        self.status = tk.Label(right, justify="left", wraplength=278, bg="#12161b", fg=ACC, font=("Segoe UI", 9), anchor="nw", padx=8, pady=8)
        self.status.pack(fill="both", expand=True, padx=10, pady=10)
        cv = self.cv
        cv.bind("<Motion>", self.on_move)
        cv.bind("<Button-1>", self.on_down)
        cv.bind("<B1-Motion>", self.on_drag)
        cv.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag", None))
        cv.bind("<Button-3>", lambda e: setattr(self, "rd", (e.x, e.y, False)))
        cv.bind("<B3-Motion>", self.on_rdrag)
        cv.bind("<ButtonRelease-3>", self.on_rup)
        cv.bind("<MouseWheel>", self.on_wheel)
        cv.bind("<Button-4>", lambda e: self.on_wheel(e, 1))
        cv.bind("<Button-5>", lambda e: self.on_wheel(e, -1))
        self.mouse = (0, 0)
        self.set_speed(1)

    # ---- stopwatch / parts ---- #
    def sw_time(self):
        return S.sw_acc + (S.t - S.sw_t0 if S.sw_run else 0)

    def sw_go(self):
        if not S.sw_run:
            S.sw_run, S.sw_t0 = True, S.t

    def sw_stop(self):
        if S.sw_run:
            S.sw_acc += S.t - S.sw_t0
            S.sw_run = False

    def sw_clear(self):
        if not S.sw_run:
            S.sw_acc = 0.0

    def set_speed(self, s):
        S.speed = s
        for v, b in self.sp_btn:
            b.config(bg=ACC if v == s else PANEL2, fg="#1c2027" if v == s else FG)

    def take_bottle(self):
        S.where = "tray" if S.where == "hand" else "hand"
        self.tool = None

    def take_pencil(self):
        self.tool = None if self.tool == "pencil" else "pencil"
        if S.where == "hand":
            S.where = "tray"

    def toggle_tape(self):
        self.tape.on = not self.tape.on
        self.tape.x, self.tape.y, self.tape.ang = -1.0, 0.0, math.pi / 2

    # ---- drawing ---- #
    def draw(self):
        cv = self.cv
        cv.delete("all")
        W, Hh = cv.winfo_width(), cv.winfo_height()
        P = self.W2P
        y0 = P(0, 0)[1]
        cv.create_rectangle(-10, y0, W + 10, Hh + 10, fill="#3a3d42", outline="")
        a = alpha()
        ux, uy, nx, ny = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
        xs = ux * SH
        # sticks and clamps
        for i in range(2):
            p, q = P(xs - 0.48, STICK_H), P(xs + 0.48, 0)
            cv.create_rectangle(p[0], p[1], q[0], q[1], fill="#d9c39b", outline="#b8a27a")
        for i in range(2):
            h = S.clamps[i]
            p, q = P(xs - 1.3 - 0.2 * i, h), P(xs + 1.3 + 0.2 * i, h - 1.8)
            cv.create_rectangle(p[0], p[1], q[0], q[1], fill="#2d6fb8" if i == 0 else "#2a63a4", outline="#1d4f88", tags="clamp%d" % i)
        # board
        pts = [(0, 0), (ux * L, uy * L), (ux * L + nx * TH, uy * L + ny * TH), (nx * TH, ny * TH)]
        cv.create_polygon(*[c for p in pts for c in P(*p)], fill="#c79d63", outline="#9b7444", tags="board")
        for s in S.marks:
            p, q = P(ux * s, uy * s), P(ux * s + nx * TH, uy * s + ny * TH)
            cv.create_line(p[0], p[1], q[0], q[1], fill="#2a2a2d", width=1.4)
        # bottle
        if S.where in ("board", "desk", "hand"):
            if S.where == "hand":
                c = self.P2W(*self.mouse)
            else:
                c = bottle_c()
            p = P(*c)
            r = R * self.sx
            cv.create_oval(p[0] - r, p[1] - r, p[0] + r, p[1] + r, fill="#dfe6ea", outline="#7e8b93", width=2, tags="bottle")
            Fdr = M * G * math.sin(a) if S.where == "board" else 0
            dl = math.asin(min(1.0, Fdr / (TRUE["ml"] * G))) if (S.v > 0 or Fdr > TRUE["F0"]) else 0.0
            fill = TRUE["ml"] / 0.0125 * 0.55
            arc = [P(c[0] + (R - 0.12) * math.sin(dl - fill + 2 * fill * k / 12), c[1] - (R - 0.12) * math.cos(dl - fill + 2 * fill * k / 12)) for k in range(13)]
            cv.create_polygon(*[v for q in arc for v in q], fill="#964612", outline="", tags="bottle")
            for d in (0, math.pi):
                q = P(c[0] + R * 0.95 * math.sin(-S.phi + d), c[1] - R * 0.95 * math.cos(-S.phi + d))
                cv.create_oval(q[0] - 3, q[1] - 3, q[0] + 3, q[1] + 3, fill="#2a5aa8", outline="", tags="bottle")
        # tape
        if self.tape.on:
            tp = self.tape
            c, s = math.cos(tp.ang), math.sin(tp.ang)

            def Q(u, v):
                return P(tp.x + u * c - v * s, tp.y + u * s + v * c)
            poly = [Q(0, 0), Q(100, 0), Q(100, -1.3), Q(0, -1.3)]
            cv.create_polygon(*[v for q in poly for v in q], fill="#f3cd2f", outline="#a8891c")
            step = 1 if self.sx * 0.1 >= 3 else 5 if self.sx * 0.5 >= 3 else 10
            for mm in range(0, 1001, step):
                u = mm / 10.0
                p1 = Q(u, 0)
                if not (-40 < p1[0] < W + 40 and -40 < p1[1] < Hh + 40):
                    continue
                ln = 0.55 if mm % 10 == 0 else 0.38 if mm % 5 == 0 else 0.25
                p2 = Q(u, -ln)
                cv.create_line(p1[0], p1[1], p2[0], p2[1], fill="#151515")
                if mm % 10 == 0 and self.sx > 6:
                    q = Q(u + 0.08, -0.95)
                    cv.create_text(q[0], q[1], text=str(mm // 10), anchor="w", angle=-math.degrees(tp.ang),
                                   fill="#c4161c" if mm % 100 == 0 else "#151515", font=("Arial", max(6, int(self.sx * 0.4)), "bold"))
        if self.tool == "pencil":
            x, y = self.mouse
            cv.create_line(x, y, x + 14, y - 30, fill="#f2c230", width=5)
            cv.create_line(x, y, x + 3, y - 6, fill="#333", width=2)

    # ---- mouse ---- #
    def tags_at(self, x, y):
        out = set()
        for it in self.cv.find_overlapping(x - 3, y - 3, x + 3, y + 3):
            out.update(self.cv.gettags(it))
        return out

    def board_s(self, px, py):
        a = alpha()
        wx, wy = self.P2W(px, py)
        return max(0.0, min(L, wx * math.cos(a) + wy * math.sin(a)))

    def on_move(self, e):
        self.mouse = (e.x, e.y)

    def on_down(self, e):
        self.mouse = (e.x, e.y)
        tags = self.tags_at(e.x, e.y)
        wx, wy = self.P2W(e.x, e.y)
        if S.where == "hand":
            if "board" in tags or "bottle" in tags:
                S.where, S.s, S.v, S.rolled = "board", max(R, min(L - R - 0.4, self.board_s(e.x, e.y))), 0.0, 0.0
            elif wy < 0.5 or wy < 3:
                S.where, S.x, S.vdesk = "desk", wx, 0.0
            return
        if self.tool == "pencil":
            if "board" in tags:
                S.marks.append(self.board_s(e.x, e.y))
            return
        if self.tape.on and self.tape.contains(wx, wy):
            self.drag = ("tape", wx - self.tape.x, wy - self.tape.y)
            return
        for i in range(2):
            if "clamp%d" % i in tags:
                self.drag = ("clamp", i, e.y, S.clamps[i])
                return
        if "bottle" in tags:
            S.where = "hand"

    def on_drag(self, e):
        self.mouse = (e.x, e.y)
        if not self.drag:
            return
        if self.drag[0] == "tape":
            wx, wy = self.P2W(e.x, e.y)
            self.tape.x, self.tape.y = wx - self.drag[1], wy - self.drag[2]
        else:
            _, i, y0, h0 = self.drag
            S.clamps[i] = max(1.8, min(STICK_H - 3, h0 + (y0 - e.y) / self.sx))

    def on_rdrag(self, e):
        x, y, _ = self.rd
        if abs(e.x - x) + abs(e.y - y) > 3:
            self.ox += e.x - x
            self.oy += e.y - y
            self.rd = (e.x, e.y, True)

    def on_rup(self, e):
        if self.rd[2]:
            return
        tags = self.tags_at(e.x, e.y)
        if "board" in tags and S.marks:
            s = self.board_s(e.x, e.y)
            j = min(range(len(S.marks)), key=lambda k: abs(S.marks[k] - s))
            if abs(S.marks[j] - s) * self.sx < 8:
                S.marks.pop(j)
                return
        if self.tool:
            self.tool = None
        elif S.where == "hand" or "bottle" in tags:
            S.where = "tray"

    def on_wheel(self, e, d=None):
        s = d if d is not None else (1 if e.delta > 0 else -1)
        tags = self.tags_at(e.x, e.y)
        wx, wy = self.P2W(e.x, e.y)
        for i in range(2):
            if "clamp%d" % i in tags:
                S.clamps[i] = max(1.8, min(STICK_H - 3, S.clamps[i] + s * (0.01 if e.state & 1 else 0.1)))
                return
        if self.tape.on and self.tape.contains(wx, wy):
            self.tape.ang += s * math.radians(0.1 if e.state & 1 else 0.5)
            return
        f = 1.15 if s > 0 else 1 / 1.15
        ns = max(4.0, min(300.0, self.sx * f))
        self.ox = e.x - (e.x - self.ox) * ns / self.sx
        self.oy = e.y - (e.y - self.oy) * ns / self.sx
        self.sx = ns

    def _tick(self):
        now = time.time()
        dt = min(0.1, now - self._last) * S.speed
        self._last = now
        S.t += dt
        n = max(1, int(math.ceil(dt / 0.005)))
        for _ in range(n):
            physics(dt / n)
        try:
            self.draw()
        except tk.TclError:
            return
        t = self.sw_time()
        m = int(t // 60)
        self.sw.config(text="%d:%05.2f" % (m, t - 60 * m))
        self.b_bottle.config(text=T("병: 손에 듦 (부품함에 넣기)", "Bottle: in hand (put it away)") if S.where == "hand" else T("병 집기", "Pick up the bottle"))
        self.b_pencil.config(text=T("연필 내려놓기", "Put the pencil down") if self.tool == "pencil" else T("연필 집기", "Pick up the pencil"))
        w = []
        if abs(S.clamps[0] - S.clamps[1]) > 0.15:
            w.append(T("두 클램프 높이가 다릅니다: 판이 높은 쪽에 얹혀 흔들립니다", "the clamps are not level: the board rests on the higher one and rocks"))
        if S.Tb > TRUE["T0"] + 3:
            w.append(T("병을 오래 쥐어 액체가 따뜻해졌습니다", "the bottle has been held long enough to warm the liquid"))
        if S.where == "hand":
            w.append(T("병을 들고 있음: 판이나 책상을 클릭해 내려놓기", "bottle in hand: click the board or the desk to set it down"))
        self.status.config(text="\n\n".join(w))
        self.after(20, self._tick)


if __name__ == "__main__":
    App().mainloop()
