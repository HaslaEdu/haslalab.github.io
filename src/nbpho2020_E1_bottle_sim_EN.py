#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  Nordic-Baltic Physics Olympiad 2020  (online, hosted by Estonia)
  Problem 5 :  BOTTLE'S SOUND
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The tools of the problem: an empty 1-litre bottle, a 100 ml
    measuring cup, a jug of water and a smartphone running a tone
    detector and a spectrum analyser.  Blowing across the mouth sounds
    the bottle as a Helmholtz resonator; too gentle a breath gives only
    hiss, too strong a one may jump to the second harmonic.
    Only what the student would see is shown: the water against the
    cup's marks, the phone's readings.  The volume of water in the
    bottle is what you poured; it is not displayed.  The hidden values
    are randomised each session; --seed N repeats a session.

    Run:   python3 nbpho2020_E1_bottle_sim_EN.py   [--seed N]
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
#  1.  병과 공명 (학생에게 보이지 않음) — cm, ml
# ==============================================================================
B_R, B_BODY, B_SH, B_NR, B_NIN, B_NECK, B_WALL = 4.0, 17.6, 7.2, 1.25, 1.08, 2.4, 0.035
B_TOP = B_BODY + B_SH + B_NECK


def bot_r(y):
    if y < 0.6:
        return B_R * (0.9 + 0.1 * y / 0.6)
    if y <= B_BODY:
        return B_R
    if y <= B_BODY + B_SH:
        t = (y - B_BODY) / B_SH
        return B_NR + (B_R - B_NR) * (0.5 + 0.5 * math.cos(math.pi * t))
    return B_NR


def bot_rin(y):
    return B_NIN if y > B_BODY + B_SH else bot_r(y) - B_WALL


VOLT = [(0.0, 0.0)]
_v, _y = 0.0, 0.15
while _y <= B_TOP + 1e-9:
    _v += math.pi * bot_rin(_y) ** 2 * 0.01
    VOLT.append((_y, _v))
    _y += 0.01


def vol_below(y):
    if y <= 0.15:
        return 0.0
    i = max(0, min(len(VOLT) - 1, int(round((y - 0.15) / 0.01)) + 1))
    return VOLT[i][1]


def level_of(V):
    lo, hi = 0.15, B_TOP
    for _ in range(40):
        m = (lo + hi) / 2
        if vol_below(m) < V:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


V_BRIM, V_NECK = vol_below(B_TOP), vol_below(B_BODY + B_SH)
C_AIR = 343.6 * (1 + 0.002 * gauss())
V0 = V_NECK - 32 + 4 * gauss()
AREA = math.pi * (B_NIN * 1e-2) ** 2
_f0 = 144 * (1 + 0.015 * gauss())
L_EFF = AREA / (V0 * 1e-6) * (C_AIR / (2 * math.pi * _f0)) ** 2
CUP_R, CUP_H = 2.6, 6.2
BINW = 44100 / 8192.0
NB = int(2000 / BINW)


def helmholtz(V):
    cav = (V0 - V) * 1e-6
    if cav <= 6e-6:
        return None
    return C_AIR / (2 * math.pi) * math.sqrt(AREA / (L_EFF * cav))


class State(object):
    def __init__(self):
        self.t = 0.0
        self.V = 0.0
        self.cup = 0.0
        self.blowing = False
        self.strength = 0.5
        self.amp = 0.0
        self.over = 0.0
        self.filling = False
        self.app = "tone"
        self.hold = False
        self.cursor = 300.0
        self.fmax = 1000
        self.tone = None
        self.hist = []
        self.spec = [-95.0] * NB


S = State()


def regime():
    if S.strength < 0.22:
        return "hiss"
    if S.strength > 0.8:
        return "over"
    return "tone"


def step(dt):
    f = helmholtz(S.V)
    want = min(1.0, 0.4 + S.strength) if (S.blowing and f and regime() != "hiss") else 0.0
    S.amp += (want - S.amp) * min(1.0, dt * (6 if want > S.amp else 10))
    S.over = S.over + dt if (S.blowing and regime() == "over") else 0.0
    if S.filling:
        S.cup = min(118.0, S.cup + 28 * dt)


def sound_now():
    f = helmholtz(S.V)
    noise = (0.15 + 0.6 * S.strength) if S.blowing else 0.0
    if not f:
        return None, [], noise
    fb = f * (1 + 0.012 * (S.strength - 0.5))
    octave = regime() == "over" and S.over > 0.4 and math.sin(S.t * 3.1) > -0.2
    a = S.amp
    peaks = [(fb, 0.25 * a), (2 * fb, 0.9 * a), (3 * fb, 0.12 * a)] if octave else [(fb, a), (2 * fb, 0.06 * a), (3 * fb, 0.02 * a)]
    return fb, peaks, noise


def update_spectrum(dt):
    if S.hold:
        return
    f0, peaks, noise = sound_now()
    k = min(1.0, dt * 8)
    for i in range(1, NB):
        f = i * BINW
        p = 10 ** ((-92 + 4 * gauss()) / 10)
        if noise > 0:
            p += noise * noise * 2e-6 * (150 / max(f, 60)) ** 1.2 * (0.6 + 0.8 * RNG.random())
        for fp, a in peaks:
            d = (f - fp) / (1.3 * BINW)
            if abs(d) < 5:
                p += a * a * 4e-4 * math.exp(-d * d) * (0.85 + 0.3 * RNG.random())
        S.spec[i] += (10 * math.log10(p) - S.spec[i]) * k


def update_tone():
    f0, peaks, noise = sound_now()
    best, ba = None, 0.0
    for f, a in peaks:
        if a > ba:
            best, ba = f, a
    if best and ba > 0.3:
        S.tone = best * (1 + 0.0018 * gauss())
    elif noise > 0.05:
        S.tone = 250 + 1600 * RNG.random()
    if S.tone:
        S.hist.append(S.tone)
        S.hist = S.hist[-60:]


NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_of(f):
    n = int(round(12 * math.log(f / 440.0, 2))) + 57
    return NOTES[n % 12] + str(n // 12)


# ==============================================================================
#  2.  화면
# ==============================================================================
BG, PANEL, PANEL2 = "#1c2027", "#22262d", "#2b2f36"
FG, FG_DIM, ACC = "#e8eef2", "#9aa3ab", "#f2c14e"


class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title(T("NBPhO 2020 실험 시뮬레이터 — 문제 5 병의 소리", "NBPhO 2020 Experiment Simulator — Problem 5 Bottle's sound") + "   v" + APP_VERSION)
        self.geometry("1480x900")
        self.configure(bg=BG)
        self.msg = ("", 0)
        self.last_tone = 0
        self._build()
        self._last = time.time()
        self.after(30, self._tick)

    def say(self, m):
        self.msg = (m, time.time())

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x")
        tk.Label(top, text="NBPhO 2020  ·  " + T("문제 5 병의 소리 (8점)", "Problem 5 Bottle's sound (8 pts)"), bg=BG, fg=ACC,
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=14, pady=6)
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, anchor="w", bg=BG, fg=FG_DIM, font=("Segoe UI", 9), text=T(
            "탁자 — 병 입구를 누르고 있으면 불기 · 물병을 누르고 있으면 컵이 참 · 컵 클릭: 병에 붓기   |   휴대폰 — 아래 탭으로 음 검출기/스펙트럼, 스펙트럼을 끌어 커서 옮기기",
            "the table — hold the bottle's mouth to blow · hold the jug to fill the cup · click the cup to pour it into the bottle   |   the phone — tabs below switch tone/spectrum; drag on the spectrum to move the cursor")).pack(fill="x")
        row = tk.Frame(left, bg=BG)
        row.pack(fill="both", expand=True)
        self.cv = tk.Canvas(row, bg="#c8a87e", highlightthickness=0)
        self.cv.pack(side="left", fill="both", expand=True)
        self.ph = tk.Canvas(row, bg="#1d1f22", width=360, highlightthickness=0)
        self.ph.pack(side="left", fill="y", padx=(6, 0))
        right = tk.Frame(body, bg=PANEL, width=290)
        right.pack(side="left", fill="y", padx=(8, 0))
        right.pack_propagate(False)
        bs = dict(bg=PANEL2, fg=FG, activebackground="#343941", activeforeground=FG, relief="flat", bd=0, padx=8, pady=5, font=("Segoe UI", 10))

        def H(t):
            tk.Label(right, text=t, bg=PANEL, fg=ACC, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        H(T("불기", "Blowing"))
        self.b_blow = tk.Button(right, text=T("불기 (누르고 있기)", "Blow (hold)"), **bs)
        self.b_blow.pack(fill="x", padx=10, pady=1)
        self.b_blow.bind("<ButtonPress-1>", lambda e: setattr(S, "blowing", True))
        self.b_blow.bind("<ButtonRelease-1>", lambda e: setattr(S, "blowing", False))
        self.lb = tk.Label(right, text="", bg=PANEL, fg=FG_DIM, font=("Segoe UI", 9))
        self.lb.pack(anchor="w", padx=10)
        self.sc = tk.Scale(right, from_=0, to=100, orient="horizontal", showvalue=False, bg=PANEL, fg=FG, highlightthickness=0, troughcolor=PANEL2,
                           command=lambda v: setattr(S, "strength", float(v) / 100))
        self.sc.set(50)
        self.sc.pack(fill="x", padx=10)
        H(T("물", "Water"))
        self.b_fill = tk.Button(right, text=T("컵 채우기 (누르고 있기)", "Fill the cup (hold)"), **bs)
        self.b_fill.pack(fill="x", padx=10, pady=1)
        self.b_fill.bind("<ButtonPress-1>", lambda e: setattr(S, "filling", True))
        self.b_fill.bind("<ButtonRelease-1>", lambda e: setattr(S, "filling", False))
        tk.Button(right, text=T("병에 붓기", "Pour into the bottle"), command=self.pour, **bs).pack(fill="x", padx=10, pady=1)
        tk.Button(right, text=T("컵 비우기", "Empty the cup"), command=lambda: setattr(S, "cup", 0.0), **bs).pack(fill="x", padx=10, pady=1)
        tk.Button(right, text=T("병을 개수대에 비우기", "Empty the bottle into the sink"), command=lambda: setattr(S, "V", min(S.V, 1.5 + 2 * RNG.random())), **bs).pack(fill="x", padx=10, pady=1)
        H(T("안내", "Notes"))
        tk.Label(right, justify="left", wraplength=255, bg=PANEL, fg=FG_DIM, font=("Segoe UI", 8), text=T(
            "• 병의 축에 수직으로 입구를 가로질러 약하거나 적당히 세게 불면 소리가 납니다; 너무 약하면 쉭 소리뿐, 너무 세면 배음으로 넘어갈 수 있습니다.\n• 컵의 눈금 간격은 10 ml이며, 부을 때 물이 조금 컵에 남습니다.\n• 병 속 물의 양은 표시되지 않습니다: 부은 양을 기록하세요.",
            "• A gentle to moderately strong breath across the mouth makes it whistle; too weak gives only hiss, too strong may jump to a harmonic.\n• The cup's marks are 10 ml apart; a little water stays in the cup when you pour.\n• The water in the bottle is not displayed: keep count of what you pour.")).pack(anchor="w", padx=10)
        self.status = tk.Label(right, justify="left", wraplength=255, bg="#12161b", fg=ACC, font=("Segoe UI", 9), anchor="nw", padx=8, pady=8)
        self.status.pack(fill="both", expand=True, padx=10, pady=10)
        self.cv.bind("<ButtonPress-1>", self.c_down)
        self.cv.bind("<ButtonRelease-1>", self.c_up)
        self.ph.bind("<Button-1>", self.p_click)
        self.ph.bind("<B1-Motion>", lambda e: self.p_click(e, True))

    def pour(self):
        if S.cup < 0.5:
            return
        keep = min(S.cup, 0.8 + 0.6 * RNG.random())
        S.V += S.cup - keep
        S.cup = keep
        if S.V > V_BRIM:
            S.V = V_BRIM
            self.say(T("병이 가득 차서 물이 넘쳤습니다", "the bottle is full: the water ran over"))

    def geo(self):
        W, H = max(500, self.cv.winfo_width()), max(400, self.cv.winfo_height())
        k = min((H - 60) / 32.0, W / 50.0)
        return W, H, k, H - 40

    def c_down(self, e):
        W, H, k, by = self.geo()
        bx, cx, jx = W * 0.3, W * 0.55, W * 0.78
        if abs(e.x - bx) < B_R * k and by - B_TOP * k - 20 < e.y < by:
            S.blowing = True
        elif abs(e.x - jx) < 5.5 * k and e.y > by - 19 * k:
            S.filling = True
        elif abs(e.x - cx) < CUP_R * k + 6 and e.y > by - CUP_H * k - 6:
            self.pour()

    def c_up(self, e):
        S.blowing = False
        S.filling = False

    def p_click(self, e, drag=False):
        W, H = 360.0, max(400, self.ph.winfo_height())
        if e.y > H - 52 and not drag:
            S.app = "tone" if e.x < W / 2 else "spec"
            return
        if S.app == "spec":
            x0, w, y0, h = 44, W - 60, 80, H - 260
            if not drag and y0 + h + 60 < e.y < y0 + h + 96:
                if e.x > W - 100:
                    S.hold = not S.hold
                elif W - 196 < e.x < W - 108:
                    S.fmax = {2000: 1000, 1000: 500, 500: 2000}[S.fmax]
                    S.cursor = min(S.cursor, S.fmax)
                elif 16 < e.x < 50:
                    S.cursor = max(0.0, S.cursor - BINW)
                elif 56 < e.x < 90:
                    S.cursor = min(float(S.fmax), S.cursor + BINW)
                return
            if y0 < e.y < y0 + h:
                S.cursor = max(0.0, min(float(S.fmax), (e.x - x0) / w * S.fmax))

    def draw_table(self):
        c = self.cv
        c.delete("all")
        W, H, k, by = self.geo()
        c.create_rectangle(0, by, W, H, fill="#b08f66", outline="")
        bx = W * 0.3
        lv = level_of(S.V)
        ys = [i * 0.25 for i in range(int(B_TOP / 0.25) + 1)] + [B_TOP]
        if S.V > 0.5:
            wl = [bx - (bot_rin(y) - 0.02) * k for y in ys if y <= lv] + [bx - (bot_rin(lv) - 0.02) * k]
            wr = [bx + (bot_rin(y) - 0.02) * k for y in ys if y <= lv] + [bx + (bot_rin(lv) - 0.02) * k]
            yy = [by - y * k for y in ys if y <= lv] + [by - lv * k]
            pts = []
            for x, y in zip(wl, yy):
                pts += [x, y]
            for x, y in reversed(list(zip(wr, yy))):
                pts += [x, y]
            c.create_polygon(*pts, fill="#7aa9d4", outline="")
        L = []
        R_ = []
        for y in ys:
            L += [bx - bot_r(y) * k, by - y * k]
            R_ += [bx + bot_r(y) * k, by - y * k]
        c.create_line(*L, fill="#dfeaf0", width=2)
        c.create_line(*R_, fill="#dfeaf0", width=2)
        c.create_line(bx - bot_r(0) * k, by, bx + bot_r(0) * k, by, fill="#dfeaf0", width=2)
        if S.blowing:
            for i in range(4):
                s = (S.t * 2 + i / 4.0) % 1
                x = bx - 6 * k + 12 * k * s
                c.create_line(x - 0.6 * k, by - (B_TOP + 0.4) * k, x + 0.6 * k, by - (B_TOP + 0.4) * k, fill="#ffffff", width=2)
        cx = W * 0.55
        ri = (CUP_R - 0.1) * k
        if S.cup > 0.3:
            lvc = (0.25 + S.cup / (math.pi * (CUP_R - 0.1) ** 2)) * k
            c.create_rectangle(cx - ri, by - lvc, cx + ri, by - 0.25 * k, fill="#7aa9d4", outline="")
        c.create_line(cx - CUP_R * k, by - CUP_H * k, cx - CUP_R * k, by, cx + CUP_R * k, by, cx + CUP_R * k, by - CUP_H * k, fill="#e6edf1", width=2)
        for ml in range(10, 101, 10):
            y = by - (0.25 + ml / (math.pi * (CUP_R - 0.1) ** 2)) * k
            c.create_line(cx - 0.3 * k, y, cx + (0.5 if ml % 50 else 0.9) * k, y, fill="#c8262b", width=2)
            if ml % 20 == 0 or ml == 10 or k > 30:
                c.create_text(cx + 1.1 * k, y, text="%d" % ml, anchor="w", fill="#c8262b", font=("Arial", 8, "bold"))
        jx = W * 0.78
        c.create_rectangle(jx - 5.2 * k, by - 12 * k, jx + 5.2 * k, by, fill="#8ab4d9", outline="")
        c.create_line(jx - 5.2 * k, by - 18 * k, jx - 5.2 * k, by, jx + 5.2 * k, by, jx + 5.2 * k, by - 18 * k, fill="#e6edf1", width=2)
        if S.filling:
            c.create_line(jx - 5.2 * k, by - 17 * k, cx, by - CUP_H * k, fill="#8ab4d9", width=3)
        c.create_text(bx, by + 18, text=T("1리터 병", "1-litre bottle"), fill="#3a2d1e")
        c.create_text(cx, by + 18, text=T("계량컵", "measuring cup"), fill="#3a2d1e")
        c.create_text(jx, by + 18, text=T("물병", "jug"), fill="#3a2d1e")

    def draw_phone(self):
        g = self.ph
        g.delete("all")
        W, H = 360.0, max(400, self.ph.winfo_height())
        g.create_rectangle(0, 0, W, 58, fill="#26323a", outline="")
        g.create_text(14, 30, anchor="w", text="☰  " + ("Tone Detector" if S.app == "tone" else "Spectrum Analyzer"), fill=FG, font=("Arial", 13, "bold"))
        for i, (k, t) in enumerate((("tone", "Tone"), ("spec", "Spectrum"))):
            g.create_rectangle(i * W / 2, H - 52, (i + 1) * W / 2, H, fill="#3a7bd5" if S.app == k else "#20262c", outline="")
            g.create_text(i * W / 2 + W / 4, H - 26, text=t, fill=FG, font=("Arial", 12, "bold"))
        if S.app == "tone":
            f = S.tone
            g.create_text(W / 2, 110, text="Frequency", fill=FG_DIM, font=("Arial", 12))
            g.create_text(W / 2, 170, text="%.1f" % f if f else "—", fill="#7df08f", font=("Arial", 40, "bold"))
            g.create_text(W / 2, 215, text="Hz", fill=FG, font=("Arial", 14))
            g.create_text(W / 2, 270, text="Note", fill=FG_DIM, font=("Arial", 12))
            g.create_text(W / 2, 310, text=note_of(f) if f else "—", fill=FG, font=("Arial", 28, "bold"))
        else:
            FM, x0, y0, w, h = S.fmax, 44, 80, W - 60, H - 260

            def X(f):
                return x0 + f / FM * w

            def Y(d):
                return y0 + (-d - 20) / 80.0 * h
            for d in range(-20, -101, -20):
                g.create_line(x0, Y(d), x0 + w, Y(d), fill="#26323a")
                g.create_text(x0 - 4, Y(d), text=str(d), anchor="e", fill="#6b7680", font=("Arial", 8))
            f = 0
            while f <= FM:
                g.create_line(X(f), y0, X(f), y0 + h, fill="#26323a")
                if f % (FM // 4) == 0:
                    g.create_text(X(f), y0 + h + 14, text=str(int(f)), fill="#6b7680", font=("Arial", 8))
                f += FM // 8
            pts = []
            for i in range(1, NB):
                if i * BINW > FM:
                    break
                pts += [X(i * BINW), min(y0 + h, max(y0, Y(S.spec[i])))]
            if len(pts) > 3:
                g.create_line(*pts, fill="#5ab0ff")
            cxp = X(S.cursor)
            g.create_line(cxp, y0, cxp, y0 + h, fill=ACC)
            bi = max(1, min(NB - 1, int(round(S.cursor / BINW))))
            g.create_text(x0, y0 + h + 40, anchor="w", text="%.1f Hz   %.1f dB" % (bi * BINW, S.spec[bi]), fill=ACC, font=("Arial", 12, "bold"))
            yb = y0 + h + 60
            g.create_rectangle(16, yb, 50, yb + 34, fill="#26323a", outline="")
            g.create_text(33, yb + 17, text="◀", fill=FG)
            g.create_rectangle(56, yb, 90, yb + 34, fill="#26323a", outline="")
            g.create_text(73, yb + 17, text="▶", fill=FG)
            g.create_rectangle(W - 196, yb, W - 108, yb + 34, fill="#26323a", outline="")
            g.create_text(W - 152, yb + 17, text="0–%d Hz" % FM, fill=FG, font=("Arial", 10))
            g.create_rectangle(W - 100, yb, W - 16, yb + 34, fill="#c8262b" if S.hold else "#20262c", outline="")
            g.create_text(W - 58, yb + 17, text="Live" if S.hold else "Hold", fill=FG, font=("Arial", 11, "bold"))

    def _tick(self):
        now = time.time()
        dt = min(0.05, now - self._last)
        self._last = now
        S.t += dt
        step(dt)
        update_spectrum(dt)
        if now - self.last_tone > 0.15:
            self.last_tone = now
            update_tone()
        try:
            self.draw_table()
            self.draw_phone()
        except tk.TclError:
            return
        self.lb.config(text=T("숨의 세기: ", "breath: ") + "%d %%" % round(S.strength * 100))
        self.b_blow.config(bg=ACC if S.blowing else PANEL2, fg="#1c2027" if S.blowing else FG)
        w = []
        if self.msg[0] and now - self.msg[1] < 5:
            w.append(self.msg[0])
        if S.blowing and not helmholtz(S.V):
            w.append(T("물이 목까지 차서 병이 더 이상 울리지 않습니다", "the water is in the neck: the bottle no longer whistles"))
        self.status.config(text="\n\n".join(w))
        self.after(30, self._tick)


if __name__ == "__main__":
    App().mainloop()
