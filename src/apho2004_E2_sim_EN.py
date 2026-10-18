#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  5th Asian Physics Olympiad  (APhO 2004, Hanoi, Vietnam)
  Experimental Problem 2 :  BLACK BOX
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The box holds two stars of passive elements: Z1 (A-B), Z2 (A-C),
  Z3 (A-D) round the common A, and Z'1, Z'2, Z'3 the same round A'.
  Group 1 is one R, one C and one L (with its winding's resistance) in a
  random order; group 2 is C, R, R or L, C, R.  The draw is kept only if
  the joined box DD'A' (B, C, B', C', D' together) has one in-phase
  frequency f0 between 300 Hz and 30 kHz.  Rn = 5 kohm stands alone.
* Any wiring of the box, the function generator (50 ohm, sine / triangle
  / square as odd harmonics) and the double-beam scope (1 Mohm || 25 pF)
  is solved by complex nodal analysis, harmonic by harmonic.  The
  generator's and the scope's grounds are both earthed, so joined.
* The element types and values are hidden and randomised.
* Standard library only (tkinter).

    Run:   python3 apho2004_E2_sim_EN.py
"""

import cmath
import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line

TERMS = ["A", "B", "C", "D", "A'", "B'", "C'", "D'", "N1", "N2", "FG", "FGG", "CH1", "G1", "CH2", "G2"]
VDIV = [0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5]
TDIV = [1e-6, 2e-6, 5e-6, 1e-5, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4, 1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2, 0.1, 0.2, 0.5, 1]


def fmtV(v):
    return ("%g V" % v) if v >= 1 else ("%g mV" % (v * 1000))


def fmtT(t):
    return ("%g s" % t) if t >= 1 else ("%g ms" % (t * 1e3)) if t >= 1e-3 else ("%g µs" % round(t * 1e6))


def fmtF(f):
    return ("%.3f MHz" % (f / 1e6)) if f >= 1e6 else ("%.4g kHz" % (f / 1e3)) if f >= 1e3 else ("%.4g Hz" % f) if f >= 1 else ("%.3f Hz" % f)


# --------------------------------------------------------------------------
#  Physics core  (V, ohm, F, H, Hz)
# --------------------------------------------------------------------------
def Yel(z, w):
    if z[0] == "R":
        return 1.0 / z[1]
    if z[0] == "C":
        return 1j * w * z[1]
    return 1.0 / (z[2] + 1j * w * z[1])


class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        mkR = lambda: ("R", round(r.uniform(1.0, 4.7) * 100) * 10.0)
        mkC = lambda: ("C", r.uniform(10, 100) * 1e-9)
        mkL = lambda: ("L", r.uniform(20, 80) * 1e-3, r.uniform(25, 90))
        for _ in range(400):
            g1 = [mkR(), mkC(), mkL()]
            r.shuffle(g1)
            g2 = [mkR(), mkC(), mkR()] if r.random() < 0.5 else [mkL(), mkC(), mkR()]
            r.shuffle(g2)
            self.g1, self.g2 = g1, g2
            f0 = self.zero_cross()
            if f0 and 300 < f0 < 30000:
                self.f0 = f0
                break
        self.Rn = 5000 * r.uniform(0.995, 1.005)
        self.Rfg = 50.0
        self.gain = [r.uniform(0.97, 1.03), r.uniform(0.97, 1.03)]
        self.fcal = r.uniform(0.997, 1.003)

    def ratio(self, f):
        w = 2 * math.pi * f
        top = 1 / Yel(self.g1[2], w) + 1 / (Yel(self.g1[0], w) + Yel(self.g1[1], w))
        bot = 1 / (Yel(self.g2[0], w) + Yel(self.g2[1], w) + Yel(self.g2[2], w))
        return bot / (top + bot)

    def zero_cross(self):
        prev, n, f0 = None, 0, None
        for i in range(501):
            f = 10 ** (1 + i * 0.01)
            ph = cmath.phase(self.ratio(f))
            if prev is not None and (ph > 0) != (prev > 0) and abs(ph - prev) < 2:
                n += 1
                f0 = f
            prev = ph
        return f0 if n == 1 else None


def make_nets(leads):
    par = dict((t, t) for t in TERMS)

    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for a, b in leads:
        par[f(a)] = f(b)
    par[f("FGG")] = f("G1")          # both instruments are earthed through their plugs
    par[f("G2")] = f("G1")
    return f


def csolve(A, b):
    n = len(b)
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(A[r][i]))
        A[i], A[p] = A[p], A[i]
        b[i], b[p] = b[p], b[i]
        for r in range(i + 1, n):
            k = A[r][i] / A[i][i]
            for c in range(i, n):
                A[r][c] -= k * A[i][c]
            b[r] -= k * b[i]
    x = [0j] * n
    for i in range(n - 1, -1, -1):
        x[i] = (b[i] - sum(A[i][c] * x[c] for c in range(i + 1, n))) / A[i][i]
    return x


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_box(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 50 * s, y - 30 * s, x + 50 * s, y + 30 * s, fill="#1b1d20", outline="#444")
    for dx in (-25, 25):
        for px, py in ((0, -16), (-14, 0), (14, 0), (0, 16)):
            cv.create_oval(x + (dx + px - 3) * s, y + (py - 3) * s, x + (dx + px + 3) * s, y + (py + 3) * s, fill="#c9a64a", outline="")


def art_scope(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 45 * s, y - 35 * s, x + 45 * s, y + 35 * s, fill="#c9cbc4", outline="#777")
    cv.create_rectangle(x - 38 * s, y - 28 * s, x + 10 * s, y + 12 * s, fill="#0d1a12", outline="")
    cv.create_line(*[v for i in range(25) for v in (x - 38 * s + i * 2 * s, y - 8 * s - 10 * s * math.sin(i / 3.0))], fill="#7cf29a")


def art_fg(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 40 * s, y - 22 * s, x + 40 * s, y + 22 * s, fill="#2b6cb0", outline="#1b4c80")
    cv.create_rectangle(x - 34 * s, y - 14 * s, x + 4 * s, y + 0 * s, fill="#14200f", outline="")
    cv.create_oval(x + 14 * s, y - 10 * s, x + 30 * s, y + 6 * s, fill="#1f2226", outline="")


def art_leads(cv, x, y, sc=1.0):
    s = sc
    for c, r in (("#c0392b", 26), ("#1f2226", 20), ("#2b6cb0", 14)):
        cv.create_oval(x - r * s, y - r * 0.6 * s, x + r * s, y + r * 0.6 * s, outline=c, width=2)


ART = {"box": art_box, "scope": art_scope, "fg": art_fg, "leads": art_leads}
PARTS = [
    ("box",   ("[3] 블랙박스 (ABCD · A'B'C'D' · Rn)", "[3] Black box (ABCD · A'B'C'D' · Rn)"), []),
    ("scope", ("[1] 두 겹 빔 오실로스코프", "[1] Double-beam oscilloscope"), []),
    ("fg",    ("[2] 함수 발생기 0.02 Hz – 2 MHz", "[2] Function generator 0.02 Hz - 2 MHz"), []),
    ("leads", ("[4] 연결 도선", "[4] Leads"), []),
]
ZONES = {"box": (220, 330, 120, 70), "scope": (560, 220, 110, 90), "fg": (260, 190, 100, 60), "leads": (450, 400, 70, 40)}
SCENE_TITLE = ("블랙박스, 함수 발생기, 오실로스코프", "The black box, the function generator, the oscilloscope")
APP_TITLE = ("APhO 2004 실험 2 — 블랙박스", "APhO 2004 Experiment 2 — Black box")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.leads = []
        self.fgOn, self.scOn = tk.BooleanVar(value=False), tk.BooleanVar(value=False)
        self.wave = tk.StringVar(value="sine")
        self.freq, self.amp = 1000.0, 4.0
        self.vd, self.td, self.pos = [8, 8], 9, [0.0, 0.0]
        self.xy, self.trig = tk.BooleanVar(value=False), tk.IntVar(value=0)
        self.cache = (None, None)
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def phasors(self, fr):
        ph, f, w = self.ph, make_nets(self.leads), 2 * math.pi * fr
        gnd, el = f("G1"), []
        if self.has("box"):
            for (p, z) in (("B", ph.g1[0]), ("C", ph.g1[1]), ("D", ph.g1[2])):
                el.append((f(p), f("A"), Yel(z, w)))
            for (p, z) in (("B'", ph.g2[0]), ("C'", ph.g2[1]), ("D'", ph.g2[2])):
                el.append((f(p), f("A'"), Yel(z, w)))
            el.append((f("N1"), f("N2"), 1 / ph.Rn))
        if self.has("scope") and self.scOn.get():
            yin = 1e-6 + 1j * w * 25e-12
            el.append((f("CH1"), gnd, yin))
            el.append((f("CH2"), gnd, yin))
        src = f("FG") if self.has("fg") and self.fgOn.get() else None
        if src is not None:
            el.append((src, gnd, 1 / ph.Rfg))
        names = []
        for p, q, _ in el:
            for n in (p, q):
                if n != gnd and n not in names:
                    names.append(n)
        if not names:
            return 0j, 0j
        idx = dict((n, i) for i, n in enumerate(names))
        N = len(names)
        A = [[1e-12 + 0j if i == j else 0j for j in range(N)] for i in range(N)]
        b = [0j] * N
        for p, q, y in el:
            i, j = idx.get(p), idx.get(q)
            if i is not None:
                A[i][i] += y
            if j is not None:
                A[j][j] += y
            if i is not None and j is not None:
                A[i][j] -= y
                A[j][i] -= y
        if src is not None and src != gnd:
            b[idx[src]] += 1 / ph.Rfg
        x = csolve(A, b)
        V = lambda n: 0j if n == gnd else (x[idx[n]] if n in idx else 0j)
        return V(f("CH1")), V(f("CH2"))

    def harmonics(self):
        w = self.wave.get()
        if w == "sine":
            return [(1, 1.0)]
        H, M = [], 59 if w == "square" else 15
        for n in range(1, M + 1, 2):
            s = 1.0 if n == 1 else math.sin(math.pi * n / (M + 2)) / (math.pi * n / (M + 2))
            H.append((n, 4 / (math.pi * n) * s if w == "square" else 8 / (math.pi ** 2 * n * n) * (-1 if ((n - 1) // 2) % 2 else 1)))
        return H

    def waves(self):
        key = (tuple(self.leads), self.fgOn.get(), self.scOn.get(), self.wave.get(), self.freq, tuple(sorted(self.app.placed)))
        if self.cache[0] == key:
            return self.cache[1]
        fr = self.freq * self.ph.fcal
        H = []
        for n, a in self.harmonics():
            if n * fr < 2e7:
                v1, v2 = self.phasors(n * fr)
                H.append((n, a, v1, v2))
        self.cache = (key, H)
        return H

    def vAt(self, ch, t):
        w, s = 2 * math.pi * self.freq * self.ph.fcal, 0.0
        for n, a, v1, v2 in self.waves():
            v = v2 if ch else v1
            s += a * (v.real * math.sin(n * w * t) + v.imag * math.cos(n * w * t))
        return s * self.amp / 2 * self.ph.gain[ch]

    def traces(self, n):
        if not (self.has("scope") and self.scOn.get()):
            return None, None
        T = 1 / (self.freq * self.ph.fcal)
        vd = [VDIV[self.vd[0]], VDIV[self.vd[1]]]
        cl = lambda v: max(-0.15, min(8.15, v))
        if self.xy.get():
            return [(max(-0.1, min(10.1, 5 + self.pos[0] + self.vAt(0, i * T / n) / vd[0])), cl(4 + self.pos[1] + self.vAt(1, i * T / n) / vd[1])) for i in range(n + 1)], None
        win, t0, tc = 10 * TDIV[self.td], 0.0, self.trig.get()
        prev = self.vAt(tc, 0)
        for i in range(1, 241):
            t = i * T / 240
            v = self.vAt(tc, t)
            if prev < 0 <= v:
                t0 = t - v / (v - prev) * T / 240
                break
            prev = v
        out = []
        for ch in (0, 1):
            if win / T > n / 3.0:
                vs = [self.vAt(ch, i * T / 120) for i in range(120)]
                lo, hi = min(vs), max(vs)
                out.append([(i * 10.0 / n, cl(4 + self.pos[ch] + (lo if i % 2 else hi) / vd[ch])) for i in range(n + 1)])
            else:
                out.append([(i * 10.0 / n, cl(4 + self.pos[ch] + self.vAt(ch, t0 + i * win / n) / vd[ch])) for i in range(n + 1)])
        return out[0], out[1]

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("함수 발생기 (출력 저항 50 Ω)", "Function generator (50 ohm output)"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Checkbutton(row, text=T("켜기", "On"), variable=self.fgOn).pack(side="left")
        for w, lab in (("sine", T("사인", "sine")), ("triangle", T("삼각", "triangle")), ("square", T("사각", "square"))):
            ttk.Radiobutton(row, text=lab, value=w, variable=self.wave).pack(side="left")
        self.fl = ttk.Label(f, text="")
        self.fl.pack(anchor="w")
        stepper(f, T("주파수", "Frequency"), [("÷10", lambda: self.setf(0.1)), ("−10%", lambda: self.setf(1 / 1.1)), ("−1%", lambda: self.setf(1 / 1.01)),
                                             ("+1%", lambda: self.setf(1.01)), ("+10%", lambda: self.setf(1.1)), ("×10", lambda: self.setf(10))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.fin = ttk.Entry(row, width=10)
        self.fin.pack(side="left", padx=2)
        ttk.Button(row, text=T("Hz 맞추기", "Set Hz"), command=self.setf_entry).pack(side="left")
        stepper(f, T("진폭 Vpp", "Amplitude Vpp"), [("−1", lambda: self.seta(-1)), ("−0.1", lambda: self.seta(-0.1)), ("+0.1", lambda: self.seta(0.1)), ("+1", lambda: self.seta(1))])
        f = ttk.LabelFrame(ctl, text=T("오실로스코프", "Oscilloscope"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Checkbutton(row, text=T("켜기", "On"), variable=self.scOn).pack(side="left")
        ttk.Checkbutton(row, text="X–Y", variable=self.xy).pack(side="left")
        ttk.Radiobutton(row, text="TRIG CH1", value=0, variable=self.trig).pack(side="left")
        ttk.Radiobutton(row, text="TRIG CH2", value=1, variable=self.trig).pack(side="left")
        stepper(f, "CH1 V/div", [("◀", lambda: self.stepv(0, -1)), ("▶", lambda: self.stepv(0, 1)), ("▲", lambda: self.mvpos(0, 0.2)), ("▼", lambda: self.mvpos(0, -0.2))])
        stepper(f, "CH2 V/div", [("◀", lambda: self.stepv(1, -1)), ("▶", lambda: self.stepv(1, 1)), ("▲", lambda: self.mvpos(1, 0.2)), ("▼", lambda: self.mvpos(1, -0.2))])
        stepper(f, "TIME/DIV", [("◀", lambda: self.stept(-1)), ("▶", lambda: self.stept(1))])
        self.sl = ttk.Label(f, text="")
        self.sl.pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("배선 — 단자 두 개를 골라 잇기 (FGG·G1·G2는 모두 접지)", "Wiring — pick two terminals (FGG, G1, G2 are all earth)"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.ta, self.tb = ttk.Combobox(row, values=TERMS, width=5, state="readonly"), ttk.Combobox(row, values=TERMS, width=5, state="readonly")
        self.ta.pack(side="left", padx=2)
        self.tb.pack(side="left", padx=2)
        ttk.Button(row, text=T("잇기", "Join"), command=self.join).pack(side="left", padx=2)
        ttk.Button(row, text=T("고른 것 뽑기", "Unplug"), command=self.unplug).pack(side="left", padx=2)
        self.lb = tk.Listbox(f, height=5)
        self.lb.pack(fill="x")
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.note = ttk.Entry(row, width=22)
        self.note.pack(side="left", padx=2)
        ttk.Button(row, text=T("지금 설정 적기", "Record"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("f", T("주파수", "frequency"), 80), ("v", "V/div 1·2", 90), ("t", "TIME/DIV", 70), ("n", T("메모 (눈금 읽은 값)", "note (readings)"), 150)], height=4)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("블랙박스 뚜껑과 오실로스코프 화면 (10 × 8 칸)", "The box's lid and the scope's screen (10 x 8 div)"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    def setf(self, k):
        self.freq = max(0.02, min(2e6, float("%.4g" % (self.freq * k))))

    def setf_entry(self):
        try:
            v = float(self.fin.get())
        except ValueError:
            return
        if v > 0:
            self.freq = max(0.02, min(2e6, float("%.4g" % v)))

    def seta(self, d):
        self.amp = max(0.0, min(20.0, round(self.amp + d, 1)))

    def stepv(self, ch, d):
        self.vd[ch] = max(0, min(len(VDIV) - 1, self.vd[ch] + d))

    def mvpos(self, ch, d):
        self.pos[ch] = max(-4.0, min(4.0, self.pos[ch] + d))

    def stept(self, d):
        self.td = max(0, min(len(TDIV) - 1, self.td + d))

    def join(self):
        a, b = self.ta.get(), self.tb.get()
        if a and b and a != b and len(self.leads) < 14 and self.has("leads"):
            self.leads.append((a, b))
            self.lb.insert("end", "%s — %s" % (a, b))

    def unplug(self):
        sel = self.lb.curselection()
        if sel:
            del self.leads[sel[0]]
            self.lb.delete(sel[0])

    def record(self):
        self.sheet.add((fmtF(self.freq) if self.fgOn.get() else "—", fmtV(VDIV[self.vd[0]]) + " · " + fmtV(VDIV[self.vd[1]]), "X-Y" if self.xy.get() else fmtT(TDIV[self.td]), self.note.get()))

    def tick(self, dt):
        self.refresh()

    def refresh(self):
        self.fl.config(text=(fmtF(self.freq) + "   ·   %.1f Vpp" % self.amp) if self.fgOn.get() and self.has("fg") else "—")
        self.sl.config(text="CH1 %s/div   CH2 %s/div   %s" % (fmtV(VDIV[self.vd[0]]), fmtV(VDIV[self.vd[1]]), "X-Y" if self.xy.get() else fmtT(TDIV[self.td]) + "/div"))
        self.draw()

    LID = {"C": (130, 60), "B": (60, 130), "D": (200, 130), "A": (130, 200), "C'": (420, 60), "B'": (350, 130), "D'": (490, 130), "A'": (420, 200), "N1": (250, 230), "N2": (300, 230),
           "FG": (620, 70), "FGG": (680, 70), "CH1": (620, 160), "G1": (680, 160), "CH2": (620, 220), "G2": (680, 220)}

    def draw(self):
        cv = self.cv
        cv.delete("all")
        P = self.LID
        if self.has("box"):
            cv.create_rectangle(20, 20, 540, 270, fill="#1b1d20", outline="#444", width=2)
            cv.create_text(30, 32, text=T("BLACK BOX — 열지 마시오", "BLACK BOX — DO NOT OPEN"), anchor="w", fill="#868e96", font=("Helvetica", 9, "bold"))
            for g, pr in ((("A", "B", "C", "D"), ""), (("A'", "B'", "C'", "D'"), "'")):
                c = P[g[0]]
                m = (c[0], (P[g[1]][1] + c[1]) / 2.0)
                for i, k in enumerate(g[1:]):
                    q = P[k]
                    cv.create_line(c[0], c[1], m[0], m[1], q[0], q[1], fill="#9aa3ab", width=2)
                    zx, zy = (m[0] + q[0]) / 2.0, (m[1] + q[1]) / 2.0
                    cv.create_rectangle(zx - 12, zy - 7, zx + 12, zy + 7, fill="#2a2d33", outline="#9aa3ab")
                    cv.create_text(zx, zy, text="Z%s%d" % (pr, i + 1), fill="#e8eef2", font=("Helvetica", 7, "bold"))
            cv.create_line(P["N1"][0], P["N1"][1], P["N2"][0], P["N2"][1], fill="#c0392b", width=2)
            cv.create_text(275, 252, text="Rn = 5 kΩ", fill="#e8eef2", font=("Helvetica", 8))
        if self.has("fg"):
            cv.create_rectangle(590, 30, 730, 95, fill="#2b6cb0", outline="#1b4c80", width=2)
            cv.create_text(660, 42, text=fmtF(self.freq) if self.fgOn.get() else T("함수 발생기", "generator"), fill="#9cf06a" if self.fgOn.get() else "#e8eef2", font=("Courier", 10, "bold"))
        if self.has("scope"):
            cv.create_rectangle(590, 120, 730, 260, fill="#c9cbc4", outline="#777", width=2)
        own = lambda t: "fg" if t.startswith("FG") else "scope" if t[0] in "G" or t.startswith("CH") else "box" if t.startswith("FG") else "scope"
        for t, (x, y) in P.items():
            if not self.has(own(t)):
                continue
            col = "#c0392b" if t in ("FG", "CH1", "CH2", "N1", "N2") else "#1f2226" if t in ("FGG", "G1", "G2") else "#c9a64a"
            cv.create_oval(x - 8, y - 8, x + 8, y + 8, fill=col, outline="#111")
            cv.create_text(x, y - 15, text=t, font=("Helvetica", 8, "bold"), fill="#f2c14e" if own(t) == "box" and t[0] != "N" else "#111")
        cols = ["#c0392b", "#1f2226", "#2b6cb0", "#d9a21b", "#2f8f4e", "#8e44ad", "#16a085", "#7f8c8d"]
        for i, (a, b) in enumerate(self.leads):
            (x0, y0), (x1, y1) = P[a], P[b]
            cv.create_line(x0, y0, (x0 + x1) / 2, max(y0, y1) + 25 + 4 * i, x1, y1, smooth=True, fill=cols[i % len(cols)], width=3)
        # the scope's screen
        sx, sy, sw, sh = 140, 300, 450, 320
        cv.create_rectangle(sx - 6, sy - 6, sx + sw + 6, sy + sh + 6, fill="#2a2d33", outline="")
        cv.create_rectangle(sx, sy, sx + sw, sy + sh, fill="#0d1a12", outline="")
        for i in range(11):
            cv.create_line(sx + i * sw / 10.0, sy, sx + i * sw / 10.0, sy + sh, fill="#2c4a35")
        for j in range(9):
            cv.create_line(sx, sy + j * sh / 8.0, sx + sw, sy + j * sh / 8.0, fill="#2c4a35")
        for i in range(51):
            X = sx + i * sw / 50.0
            cv.create_line(X, sy + sh / 2 - 3, X, sy + sh / 2 + 3, fill="#2c4a35")
        for j in range(41):
            Y = sy + j * sh / 40.0
            cv.create_line(sx + sw / 2 - 3, Y, sx + sw / 2 + 3, Y, fill="#2c4a35")
        if not self.has("scope"):
            return
        t1, t2 = self.traces(400)
        for tr, col in ((t1, "#7cf29a"), (t2, "#79c7ff")):
            if tr:
                cv.create_line(*[c for u, v in tr for c in (sx + u / 10.0 * sw, sy + sh - v / 8.0 * sh)], fill=col, width=2)


def T(ko, en):
    return ko if LANG == "ko" else en


def rr(cv, x0, y0, x1, y1, r, **kw):
    """rounded rectangle on a Tk canvas"""
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


# --------------------------------------------------------------------------
#  Assembly tab: drag each part from the list onto its place, in order
# --------------------------------------------------------------------------
class AssemblyTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.placed = set()
        self.drag = None

        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Label(left, text=T("장치 목록", "Apparatus list"),
                  font=("Helvetica", 11, "bold")).pack(anchor="w")
        self.tray = tk.Canvas(left, width=215, height=640, bg="#f2f3f5",
                              highlightthickness=1,
                              highlightbackground="#c3c7cc")
        self.tray.pack()
        self.msg = ttk.Label(left, text="", wraplength=205,
                             foreground="#8a1b1b")
        self.msg.pack(anchor="w", pady=4)

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("조립 구역 — 준비 절차 순서대로 놓으시오",
                                "Assembly area — follow the preparation order"),
                  font=("Helvetica", 11, "bold")).pack(anchor="w")
        self.scene = tk.Canvas(right, width=760, height=640, bg="#e9ebee",
                               highlightthickness=1,
                               highlightbackground="#c3c7cc")
        self.scene.pack(fill="both", expand=True)

        self.tray.bind("<ButtonPress-1>", self.on_press)
        self.tray.bind("<B1-Motion>", self.on_move)
        self.tray.bind("<ButtonRelease-1>", self.on_release)
        self.redraw()

    def redraw(self):
        self.tray.delete("all")
        pitch = min(60, 620 // len(PARTS))     # every part fits in the list
        y, self.slots, self.half = 10 + pitch // 2, [], pitch // 2 - 2
        for key, lab, _ in PARTS:
            if key in self.placed:
                continue
            self.tray.create_rectangle(8, y - self.half, 205, y + self.half,
                                       fill="#ffffff", outline="#d3d7dc")
            ART[key](self.tray, 50, y, 0.5 * pitch / 60.0)
            self.tray.create_text(98, y, text=T(*lab), width=104,
                                  font=("Helvetica", 8), anchor="w")
            self.slots.append((key, y))
            y += pitch
        self.paint_scene()

    def paint_scene(self):
        cv = self.scene
        cv.delete("all")
        cv.create_text(380, 20, text=T(*SCENE_TITLE),
                       font=("Helvetica", 10, "bold"), fill="#4a5058")
        cv.create_rectangle(20, 470, 740, 500, fill="#d6d3c8", outline="")
        for key, (cx, cy, w, h) in ZONES.items():
            if key in self.placed:
                continue
            cv.create_rectangle(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2,
                                dash=(4, 3), outline="#b0b5bb")
        for key, _, _ in PARTS:
            if key in self.placed:
                cx, cy, w, h = ZONES[key]
                ART[key](cv, cx, cy, 1.0)
        if len(self.placed) == len(PARTS):
            cv.create_text(380, 610, fill="#14532d",
                           font=("Helvetica", 11, "bold"),
                           text=T("조립 완료 — '실험대' 탭으로 이동하시오.",
                                  "Assembly complete — go to the Bench tab."))

    def on_press(self, ev):
        self.drag = None
        for key, y in self.slots:
            if abs(ev.y - y) <= self.half:
                self.drag = key
                return

    def on_move(self, ev):
        if not self.drag:
            return
        x = self.tray.winfo_rootx() + ev.x - self.scene.winfo_rootx()
        y = self.tray.winfo_rooty() + ev.y - self.scene.winfo_rooty()
        self.paint_scene()
        ART[self.drag](self.scene, x, y, 0.9)

    def on_release(self, ev):
        if not self.drag:
            return
        key, self.drag = self.drag, None
        x = self.tray.winfo_rootx() + ev.x - self.scene.winfo_rootx()
        y = self.tray.winfo_rooty() + ev.y - self.scene.winfo_rooty()
        self.drop(key, x, y)

    def drop(self, key, x, y):
        cx, cy, w, h = ZONES[key]
        self.msg.config(text="")
        if not (abs(x - cx) < w / 2 + 28 and abs(y - cy) < h / 2 + 28):
            self.msg.config(text=T("그 위치에는 놓을 수 없습니다.",
                                   "That part does not belong there."))
            self.redraw()
            return False
        needs = dict((k, n) for k, _, n in PARTS)[key]
        miss = [n for n in needs if n not in self.placed]
        if miss:
            names = ", ".join(T(*dict((k, l) for k, l, _ in PARTS)[m])
                              for m in miss)
            self.msg.config(text=T("먼저 설치해야 합니다: ",
                                   "Install first: ") + names)
            self.redraw()
            return False
        self.placed.add(key)
        self.app.on_assembly_change(self.placed)
        self.redraw()
        return True


# --------------------------------------------------------------------------
#  Data sheet: what the student typed down, nothing more
# --------------------------------------------------------------------------
class DataSheet(ttk.Frame):
    def __init__(self, master, cols, height=12):
        ttk.Frame.__init__(self, master)
        self.cols = cols
        self.tv = ttk.Treeview(self, columns=[c[0] for c in cols],
                               show="headings", height=height)
        for key, head, wd in cols:
            self.tv.heading(key, text=head)
            self.tv.column(key, width=wd, anchor="center")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")

    def add(self, row):
        self.tv.insert("", "end", values=row)
        self.tv.yview_moveto(1.0)

    def del_last(self):
        kids = self.tv.get_children()
        if kids:
            self.tv.delete(kids[-1])

    def clear(self):
        for k in self.tv.get_children():
            self.tv.delete(k)

    def as_text(self):
        out = ["\t".join(c[1] for c in self.cols)]
        for k in self.tv.get_children():
            out.append("\t".join(str(v) for v in self.tv.item(k, "values")))
        return "\n".join(out)


def sheet_buttons(parent, sheet, app):
    row = ttk.Frame(parent)
    row.pack(fill="x", pady=2)
    ttk.Button(row, text=T("마지막 줄 삭제", "Delete last"),
               command=sheet.del_last).pack(side="left", padx=2)
    ttk.Button(row, text=T("모두 지우기", "Clear"),
               command=sheet.clear).pack(side="left", padx=2)

    def copy():
        app.clipboard_clear()
        app.clipboard_append(sheet.as_text())
    ttk.Button(row, text=T("표 복사", "Copy table"),
               command=copy).pack(side="left", padx=2)


def stepper(parent, label, cmds):
    """a row of buttons: label  [−1] [−0.1] … ; cmds = [(text, fn), …]"""
    row = ttk.Frame(parent)
    row.pack(fill="x", pady=1)
    ttk.Label(row, text=label, width=16).pack(side="left")
    for txt, fn in cmds:
        ttk.Button(row, text=txt, width=max(6, len(txt) + 1), command=fn).pack(side="left", padx=1)
    return row


class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.ph = Physics(seed)
        self.title(T(*APP_TITLE))
        self.geometry("1360x800")
        self.placed = set()
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_asm = AssemblyTab(nb, self)
        self.tab_bench = BenchTab(nb, self)
        nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.tab_bench, text=T(" 실험대 ", " Bench "))
        self.after(40, self.tick)

    def on_assembly_change(self, placed):
        self.placed = set(placed)
        self.tab_bench.refresh()

    def tick(self):
        self.tab_bench.tick(0.04)
        self.after(40, self.tick)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
