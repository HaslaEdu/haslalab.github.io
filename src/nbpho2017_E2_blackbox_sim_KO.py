#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  Nordic-Baltic Physics Olympiad 2017  (NBPhO 2017)
  Problem 10 (experimental) :  BLACK BOX   (Jaan Kalda, Siim Ainsaar)
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* Three leads come out of the box: A (white), B (black), C (blue).
  Inside is the official solution's circuit A, a star around an inner
  node X: A goes to X through the battery E (+ towards A) in series
  with R2, B through R1, C through the capacitor C.  The organisers
  found E = 1.57 V on the voltmeter, R2 = E/I = 51 kohm, R1 = 200 kohm
  and C = 330 uF from the half-time of the current; E is set so that a
  >10 Mohm voltmeter across R1 + R2 reads those 1.57 V.  (Option B of
  the solution, the battery on the black side, looks the same from
  outside.)
* One 6000-count multimeter (uA 103.2 ohm, mA 4.2 ohm, V more than
  10 Mohm).  On Ohm it puts 0.6 V behind a reference resistor across
  the jacks and works the resistance out ratiometrically, so a battery
  or a capacitor in the loop makes it read nonsense, as a real one does.
  On AUTO it hunts for its range and answers about every 1.5 s; RANGE
  holds the present range (0.4 s per reading) and steps it up.
* Wires join any two terminals; joining two of the box's leads shorts
  them.  A stopwatch; time can run x4 to save waiting.
* Hidden truths (E, R1, R2, C, the capacitor's charge at the start) are
  randomised every session around the official values.
* Standard library only (tkinter).

    Run:   python3 nbpho2017_E2_blackbox_sim_KO.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line

TERMS = ["W", "K", "U", "V", "C"]
FUNCS = [("off", "OFF"), ("V", "V⎓"), ("R", "Ω"), ("uA", "µA⎓"), ("mA", "mA⎓")]
RIN = {"V": 1.2e7, "uA": 103.2, "mA": 4.2}
RNG = {"V": [0.6, 6.0, 60.0], "R": [600.0, 6e3, 60e3, 600e3, 6e6, 60e6],
       "uA": [600e-6, 6000e-6], "mA": [60e-3, 600e-3]}
UNITS = {"V": ["mV", "V", "V"], "R": ["Ω", "kΩ", "kΩ", "kΩ", "MΩ", "MΩ"],
         "uA": ["µA", "µA"], "mA": ["mA", "mA"]}
OHM_VOC = 0.6        # the ohmmeter's source, behind a reference of half the range
MAXLEADS = 5


def T(ko, en):
    return ko if LANG == "ko" else en


# --------------------------------------------------------------------------
#  Physics core  (V, ohm, F, s)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.E = r.uniform(1.596, 1.610)
        self.R1 = r.uniform(195e3, 205e3)
        self.R2 = r.uniform(49.5e3, 52.5e3)
        self.C = r.uniform(315e-6, 345e-6)
        self.gain = r.uniform(0.997, 1.003)
        self.Vc = self.E * r.uniform(0.15, 0.85)


def make_nets(leads):
    par = dict((t, t) for t in TERMS + ["X"])

    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for a, b in leads:
        par[f(a)] = f(b)
    return f


def lsolve(A, b):
    n = len(b)
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(A[r][i]))
        A[i], A[p] = A[p], A[i]
        b[i], b[p] = b[p], b[i]
        for r in range(i + 1, n):
            k = A[r][i] / A[i][i]
            if k:
                for c in range(i, n):
                    A[r][c] -= k * A[i][c]
                b[r] -= k * b[i]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = b[i] - sum(A[i][c] * x[c] for c in range(i + 1, n))
        x[i] = s / A[i][i]
    return x


def solve(ph, placed, leads, fn, ri=0, h=1e-9):
    """node voltages, the capacitor as its backward-Euler companion over a
    step h (a tiny h makes it a voltage source); returns V(net), f(term)"""
    f = make_nets(leads)
    gnd = f("X") if "box" in placed else f("C")
    G, Is = [], []
    if "box" in placed:
        x, w, k, u, gc = f("X"), f("W"), f("K"), f("U"), ph.C / h
        G.append((w, x, 1 / ph.R2))
        Is.append((x, w, ph.E / ph.R2))          # E (+ towards A) in series with R2
        G.append((k, x, 1 / ph.R1))
        G.append((u, x, gc))
        Is.append((x, u, gc * ph.Vc))            # C, Vc = V(C lead) - V(X)
    if "dmm" in placed and fn != "off":
        if fn == "R":
            rr = RNG["R"][ri] / 2
            G.append((f("V"), f("C"), 1 / rr))
            Is.append((f("C"), f("V"), OHM_VOC / rr))
        else:
            G.append((f("V"), f("C"), 1 / RIN[fn]))
    names = []
    for e in G + Is:
        for nn in e[:2]:
            if nn != gnd and nn not in names:
                names.append(nn)
    idx = dict((nn, i) for i, nn in enumerate(names))
    N = len(names)
    A = [[0.0] * N for _ in range(N)]
    b = [0.0] * N
    for i in range(N):
        A[i][i] = 1e-12
    for p, q, g in G:
        i, j = idx.get(p), idx.get(q)
        if i is not None:
            A[i][i] += g
        if j is not None:
            A[j][j] += g
        if i is not None and j is not None:
            A[i][j] -= g
            A[j][i] -= g
    for p, q, I in Is:
        i, j = idx.get(p), idx.get(q)
        if i is not None:
            b[i] -= I
        if j is not None:
            b[j] += I
    x = lsolve(A, b) if N else []

    def V(nn):
        return 0.0 if nn == gnd or nn not in idx else x[idx[nn]]
    return V, f


def fmt_sw(t):
    t = round(t, 2)
    m = int(t // 60)
    return "%02d:%05.2f" % (m, t - 60 * m)


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_box(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 46 * s, y - 32 * s, x + 46 * s, y + 32 * s, fill="#1d1f23", outline="#000")
    cv.create_text(x, y - 14 * s, text="BLACK BOX", fill="#e9e5da", font=("Helvetica", max(6, int(9 * s)), "bold"))
    for dx, col in ((-28, "#eceff1"), (0, "#1b1d20"), (28, "#2a62c9")):
        cv.create_oval(x + (dx - 8) * s, y + 2 * s, x + (dx + 8) * s, y + 18 * s, fill=col, outline="#888")


def art_dmm(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 26 * s, y - 45 * s, x + 26 * s, y + 45 * s, fill="#e8622a", outline="#5a2a12")
    cv.create_rectangle(x - 18 * s, y - 36 * s, x + 18 * s, y - 18 * s, fill="#9fae8f", outline="")
    cv.create_oval(x - 12 * s, y - 6 * s, x + 12 * s, y + 18 * s, fill="#1b1d20", outline="")
    cv.create_oval(x - 4 * s, y + 28 * s, x + 4 * s, y + 36 * s, fill="#c0392b", outline="")
    cv.create_oval(x + 10 * s, y + 28 * s, x + 18 * s, y + 36 * s, fill="#111", outline="")


def art_watch(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 26 * s, y - 32 * s, x + 26 * s, y + 32 * s, fill="#2b2e33", outline="#000")
    cv.create_rectangle(x - 20 * s, y - 24 * s, x + 20 * s, y - 4 * s, fill="#9fae8f", outline="")
    cv.create_oval(x - 16 * s, y + 8 * s, x - 4 * s, y + 20 * s, fill="#c0392b", outline="")
    cv.create_oval(x + 4 * s, y + 8 * s, x + 16 * s, y + 20 * s, fill="#e8eef2", outline="")


def art_leads(cv, x, y, sc=1.0):
    s = sc
    for c, r in (("#c0392b", 26), ("#1f2226", 20), ("#2f8f4e", 14)):
        cv.create_oval(x - r * s, y - r * 0.6 * s, x + r * s, y + r * 0.6 * s, outline=c, width=2)


ART = {"box": art_box, "dmm": art_dmm, "watch": art_watch, "leads": art_leads}
PARTS = [
    ("box",   ("블랙박스 (단자 3개)", "Black box (3 terminals)"), []),
    ("dmm",   ("멀티미터", "Multimeter"), []),
    ("watch", ("스톱워치", "Stopwatch"), []),
    ("leads", ("도선", "Wires"), []),
]
ZONES = {
    "box":   (170, 290, 130, 90),
    "dmm":   (380, 290, 70, 110),
    "watch": (540, 280, 70, 80),
    "leads": (380, 420, 70, 40),
}
SCENE_TITLE = ("실험대 — 블랙박스, 멀티미터, 스톱워치, 도선", "The bench — black box, multimeter, stopwatch, wires")
APP_TITLE = ("NBPhO 2017 실험 (문제 10) — 블랙박스", "NBPhO 2017 Experiment (Problem 10) — Black box")
TNAME = {"W": ("상자 A (흰색)", "box A (white)"), "K": ("상자 B (검은색)", "box B (black)"), "U": ("상자 C (파란색)", "box C (blue)"),
         "V": ("멀티 VΩµAmA", "meter VΩµAmA"), "C": ("멀티 COM", "meter COM")}
PCOL = {"W": ("#eceff1", "A"), "K": ("#1b1d20", "B"), "U": ("#2a62c9", "C")}


def tn(t):
    return T(*TNAME[t])


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    TP = {"W": (90, 420), "K": (170, 420), "U": (250, 420), "V": (610, 560), "C": (660, 560)}

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.leads = []
        self.fn = tk.StringVar(value="off")
        self.hold, self.ri, self.disp, self.disp_t, self.busy = False, 0, None, 0.0, 0.0
        self.sw_run, self.sw_t, self.speed = False, 0.0, 1
        self.points = []
        self.build()
        self.refresh()

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("멀티미터", "Multimeter"))
        f.pack(fill="x", pady=2)
        self.dM = tk.Label(f, text="", font=("Courier", 18, "bold"), bg="#9fae8f", fg="#1b1d20", width=16)
        self.dM.pack(pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for k, lb in FUNCS:
            ttk.Radiobutton(row, text=lb, value=k, variable=self.fn, command=self.fn_changed).pack(side="left", padx=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("RANGE (고정·올림)", "RANGE (hold · step up)"), command=self.range_btn).pack(side="left", padx=2)
        ttk.Button(row, text="AUTO", command=self.auto_btn).pack(side="left", padx=2)
        ttk.Label(f, text=T("6000 카운트. AUTO에서는 약 1.5초마다, 범위를 고정하면 0.4초마다 표시가 바뀝니다. 내부 저항: µA 103.2 Ω, mA 4.2 Ω, V 10 MΩ 이상. Ω은 약 0.6 V를 걸어 전류로 셈하므로 전지나 축전기가 있으면 엉뚱한 값입니다.",
                            "6000 counts. On AUTO the display changes about every 1.5 s, with the range held every 0.4 s. Inner resistance: µA 103.2 Ω, mA 4.2 Ω, V more than 10 MΩ. Ω puts about 0.6 V across and works from the current, so a battery or a capacitor makes it read nonsense."),
                  foreground="#555", wraplength=330).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("스톱워치", "Stopwatch"))
        f.pack(fill="x", pady=2)
        self.dS = tk.Label(f, text="", font=("Courier", 18, "bold"), bg="#9fae8f", fg="#1b1d20", width=12)
        self.dS.pack(pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.bSS = ttk.Button(row, text="", command=self.sw_start)
        self.bSS.pack(side="left", padx=2)
        ttk.Button(row, text=T("0으로", "Reset"), command=self.sw_reset).pack(side="left", padx=2)
        ttk.Label(row, text=T("  시간 배속", "  Time ×")).pack(side="left")
        self.spd = tk.IntVar(value=1)
        for s in (1, 4):
            ttk.Radiobutton(row, text="×%d" % s, value=s, variable=self.spd).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("배선 — 단자 두 개를 골라 잇기 (상자의 두 단자를 이으면 그 사이 단락)", "Wiring — pick two terminals (two of the box's own: a short)"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        names = [tn(t) for t in TERMS]
        self.ta, self.tb = ttk.Combobox(row, values=names, width=13, state="readonly"), ttk.Combobox(row, values=names, width=13, state="readonly")
        self.ta.pack(side="left", padx=2)
        self.tb.pack(side="left", padx=2)
        ttk.Button(row, text=T("잇기", "Join"), command=self.join).pack(side="left", padx=2)
        self.lb = tk.Listbox(f, height=4)
        self.lb.pack(fill="x")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("고른 도선 뽑기", "Unplug selected"), command=self.unplug).pack(side="left", padx=2)
        ttk.Button(row, text=T("모두 뽑기", "Unplug all"), command=self.unplug_all).pack(side="left", padx=2)
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("메모", "Memo")).pack(side="left")
        self.cent = ttk.Entry(row, width=14)
        self.cent.pack(side="left", padx=2)
        ttk.Button(row, text=T("지금 값 적기", "Record now"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("c", T("메모", "memo"), 110), ("t", T("스톱워치", "stopwatch"), 90), ("a", "DMM", 110)], height=8)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("배선 (위에서 본 모습)", "Wiring, from above"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=900, height=660, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    # ---- the meter
    def fn_changed(self):
        if "dmm" not in self.app.placed:
            self.fn.set("off")
            return
        self.hold, self.ri, self.disp, self.disp_t = False, 0, None, 0.0
        self.busy = 0.8 if self.fn.get() != "off" else 0.0

    def range_btn(self):
        k = self.fn.get()
        if k == "off":
            return
        if not self.hold:
            self.hold = True
        else:
            self.ri = (self.ri + 1) % len(RNG[k])
        self.disp_t = 0.0

    def auto_btn(self):
        self.hold = False
        self.disp_t = 0.0

    def raw(self):
        k = self.fn.get()
        if "dmm" not in self.app.placed or k == "off":
            return None
        V, f = solve(self.ph, self.app.placed, self.leads, k, self.ri)
        v = (V(f("V")) - V(f("C"))) * self.ph.gain
        if k == "R":
            rr = RNG["R"][self.ri] / 2
            return float("inf") if v >= OHM_VOC * 0.9999 else rr * v / (OHM_VOC - v)
        return v if k == "V" else v / RIN[k]

    def show(self):
        k = self.fn.get()
        if "dmm" not in self.app.placed or k == "off":
            return ""
        if self.busy > 0:
            return "----"
        v = self.disp
        if v is None:
            return ""
        R = RNG[k][self.ri]
        if math.isinf(v) or abs(v) >= R * 0.99995:
            return "OL"
        if k == "V":
            return "%.1f" % (v * 1e3) if self.ri == 0 else "%.3f" % v if self.ri == 1 else "%.2f" % v
        if k == "R":
            return ["%.1f" % v, "%.3f" % (v / 1e3), "%.2f" % (v / 1e3), "%.1f" % (v / 1e3), "%.3f" % (v / 1e6), "%.2f" % (v / 1e6)][self.ri]
        if k == "uA":
            return "%.1f" % (v * 1e6) if self.ri == 0 else "%.0f" % (v * 1e6)
        return "%.2f" % (v * 1e3) if self.ri == 0 else "%.1f" % (v * 1e3)

    def unit(self):
        k = self.fn.get()
        return "" if k == "off" else UNITS[k][self.ri]

    def text_of(self):
        s = self.show()
        if not s or s == "----":
            return "—"
        return s if s == "OL" else s + " " + self.unit()

    # ---- stopwatch, wires, record
    def sw_start(self):
        if "watch" in self.app.placed:
            self.sw_run = not self.sw_run

    def sw_reset(self):
        self.sw_run, self.sw_t = False, 0.0

    def join(self):
        names = [tn(t) for t in TERMS]
        a, b = self.ta.get(), self.tb.get()
        if a in names and b in names and a != b and len(self.leads) < MAXLEADS and "leads" in self.app.placed:
            ta, tb = TERMS[names.index(a)], TERMS[names.index(b)]
            self.leads.append((ta, tb))
            self.lb.insert("end", "%s — %s" % (a, b))

    def unplug(self):
        sel = self.lb.curselection()
        if sel:
            i = sel[0]
            del self.leads[i]
            self.lb.delete(i)

    def unplug_all(self):
        self.leads = []
        self.lb.delete(0, "end")

    def record(self):
        memo = self.cent.get() or ""
        tt = fmt_sw(self.sw_t) if "watch" in self.app.placed else "—"
        self.sheet.add((memo or "—", tt, self.text_of()))
        s = self.show()
        if "watch" in self.app.placed and s and s not in ("----", "OL"):
            u = self.unit()
            v = float(s) * (1000.0 if u in ("V", "mA", "MΩ") else 1e-3 if u == "Ω" else 1.0)
            k = self.fn.get()
            self.points.append((self.sw_t, v, (memo or "—") + (" (mV)" if k == "V" else " (kΩ)" if k == "R" else " (µA)")))
            self.app.tab_graph.draw()

    # ---- time
    def tick(self, dt):
        dt *= self.spd.get()
        if self.sw_run:
            self.sw_t += dt
        if "box" in self.app.placed:
            n = max(1, int(math.ceil(dt / 0.05)))
            h = dt / n
            for _ in range(n):
                V, f = solve(self.ph, self.app.placed, self.leads, self.fn.get(), self.ri, h)
                self.ph.Vc = V(f("U")) - V(f("X"))
        k = self.fn.get()
        if "dmm" in self.app.placed and k != "off":
            self.busy -= dt / self.spd.get()
            self.disp_t -= dt / self.spd.get()
            if self.disp_t <= 0:
                r = self.raw()
                R = RNG[k]
                hunting = False
                if not self.hold:
                    kk = next((i for i, c in enumerate(R) if abs(r) < c * 0.9999), len(R) - 1)
                    hunting = kk != self.ri
                    if hunting:                      # it changes range first, and shows nothing meanwhile
                        self.ri, self.busy, self.disp_t = kk, 0.7, 0.7
                    else:
                        self.disp_t = 1.4
                else:
                    self.disp_t = 0.4
                if not hunting:
                    self.disp = r + (random.random() - 0.5) * 1.2 * R[self.ri] / 6000
        else:
            self.disp = None
        self.refresh()

    def refresh(self):
        self.dM.config(text=(self.text_of() + ("  MANU" if self.hold else "  AUTO")) if "dmm" in self.app.placed and self.fn.get() != "off" else "")
        self.dS.config(text=fmt_sw(self.sw_t) if "watch" in self.app.placed else "—")
        self.bSS.config(text=T("멈춤", "Stop") if self.sw_run else T("시작", "Start"))
        self.draw()

    def draw(self):
        cv, pl = self.cv, self.app.placed
        cv.delete("all")
        if "box" in pl:
            cv.create_rectangle(40, 260, 300, 500, fill="#1d1f23", outline="#000", width=2)
            cv.create_rectangle(70, 280, 270, 340, fill="#e9e5da", outline="")
            cv.create_text(170, 300, text="BLACK BOX  № 7", font=("Helvetica", 13, "bold"))
            cv.create_text(170, 325, text=T("열지 마시오", "DO NOT OPEN"), fill="#7a2a22", font=("Helvetica", 9))
            for t in ("W", "K", "U"):
                x, y = self.TP[t]
                cv.create_oval(x - 24, y - 24, x + 24, y + 24, fill=PCOL[t][0], outline="#000", width=2)
                cv.create_oval(x - 8, y - 8, x + 8, y + 8, fill="#c9cdd2", outline="#555")
                cv.create_text(x, y + 46, text=PCOL[t][1], fill="#e8eef2", font=("Helvetica", 18, "bold"))
        else:
            cv.create_text(170, 380, text=T("블랙박스를 놓으시오", "Place the black box"), fill="#69717a")
        x0 = 560
        if "dmm" in pl:
            cv.create_rectangle(x0, 160, x0 + 140, 600, fill="#e8622a", outline="#5a2a12", width=2)
            cv.create_rectangle(x0 + 10, 170, x0 + 130, 590, fill="#2a2d33", outline="")
            cv.create_text(x0 + 70, 185, text="DMM 6000", fill="#e8eef2", font=("Helvetica", 10, "bold"))
            cv.create_rectangle(x0 + 16, 200, x0 + 124, 265, fill="#9fae8f", outline="")
            cv.create_text(x0 + 118, 228, text=self.show(), font=("Courier", 20, "bold"), anchor="e")
            cv.create_text(x0 + 118, 255, text=self.unit() if self.show() not in ("", "----", "OL") else "", font=("Helvetica", 9, "bold"), anchor="e")
            cv.create_text(x0 + 22, 210, text=("MANU" if self.hold else "AUTO") if self.fn.get() != "off" else "", font=("Helvetica", 8, "bold"), anchor="w")
            cv.create_oval(x0 + 40, 360, x0 + 100, 420, fill="#1b1d20", outline="#000")
            cv.create_text(x0 + 70, 440, text=dict(FUNCS)[self.fn.get()], fill="#ffcf3a", font=("Helvetica", 11, "bold"))
            cv.create_text(x0 + 17, 540, text="10A", fill="#e8eef2", font=("Helvetica", 8))
            cv.create_text(x0 + 52, 540, text="VΩµAmA", fill="#e8eef2", font=("Helvetica", 8))
            cv.create_text(x0 + 100, 540, text="COM", fill="#e8eef2", font=("Helvetica", 8))
            cv.create_oval(x0 + 10, 553, x0 + 24, 567, fill="#c0392b", outline="#111")
        else:
            cv.create_text(x0 + 70, 380, text=T("멀티미터를 놓으시오", "Place the multimeter"), fill="#69717a")
        if "watch" in pl:
            cv.create_rectangle(740, 200, 880, 360, fill="#2b2e33", outline="#000", width=2)
            cv.create_rectangle(752, 220, 868, 270, fill="#9fae8f", outline="")
            cv.create_text(810, 245, text=fmt_sw(self.sw_t), font=("Courier", 16, "bold"))
            cv.create_oval(765, 295, 795, 325, fill="#c0392b", outline="")
            cv.create_oval(825, 295, 855, 325, fill="#e8eef2", outline="")
        for t, (x, y) in self.TP.items():
            here = ("box" in pl) if t in ("W", "K", "U") else ("dmm" in pl)
            if here and t in ("V", "C"):
                cv.create_oval(x - 9, y - 9, x + 9, y + 9, fill="#c0392b" if t == "V" else "#1f2226", outline="#111", width=2)
        cols = ["#c0392b", "#1f2226", "#2f8f4e", "#8e44ad", "#d35400"]
        for i, (a, b) in enumerate(self.leads):
            (xa, ya), (xb, yb) = self.TP[a], self.TP[b]
            mx, my = (xa + xb) / 2, max(ya, yb) + 50 + 8 * i
            cv.create_line(xa, ya, mx, my, xb, yb, smooth=True, fill=cols[i % len(cols)], width=3)


# --------------------------------------------------------------------------
#  Graph paper tab: (stopwatch time, reading), coloured by memo
# --------------------------------------------------------------------------
class GraphTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        ttk.Label(self, text=T("모눈종이 — 스톱워치가 있을 때 기록한 (스톱워치 시각, 멀티미터 값)이 점으로 찍힙니다. 전압은 mV, 전류는 µA, 저항은 kΩ (메모가 같으면 같은 색).",
                               "Graph paper — each record with the stopwatch on the bench is plotted as (stopwatch time, reading): volts in mV, currents in µA, resistances in kΩ (same memo, same colour)."),
                  font=("Helvetica", 10, "bold")).pack(anchor="w", padx=6, pady=4)
        row = ttk.Frame(self)
        row.pack(anchor="w", padx=6)
        ttk.Button(row, text=T("점 모두 지우기", "Clear the points"), command=self.clear).pack(side="left")
        self.cv = tk.Canvas(self, width=1100, height=640, bg="#fbfaf4", highlightthickness=0)
        self.cv.pack(padx=6, pady=6)

    def clear(self):
        self.app.tab_bench.points = []
        self.draw()

    def draw(self):
        cv, P = self.cv, self.app.tab_bench.points
        cv.delete("all")
        L, R, Tp, B = 70, 1070, 30, 590

        def nice(v):
            e = 10 ** math.floor(math.log10(v))
            m = v / e
            return (1 if m <= 1 else 2 if m <= 2 else 5 if m <= 5 else 10) * e
        x0, x1, y0, y1 = 0.0, 10.0, 0.0, 1.0
        for v, i, _ in P:
            x0, x1, y0, y1 = min(x0, v), max(x1, v), min(y0, i), max(y1, i)
        xs, ys = nice((x1 - x0) / 10), nice((y1 - y0) / 8)
        x0, x1 = math.floor(x0 / xs) * xs, math.ceil(x1 / xs) * xs
        y0, y1 = math.floor(y0 / ys) * ys, math.ceil(y1 / ys) * ys
        X = lambda v: L + (v - x0) / (x1 - x0) * (R - L)
        Y = lambda v: B - (v - y0) / (y1 - y0) * (B - Tp)
        nx, ny = int(round((x1 - x0) / xs)) * 10, int(round((y1 - y0) / ys)) * 10
        for k in range(nx + 1):
            c = "#d6783c" if k % 10 == 0 else "#ebb995" if k % 5 == 0 else "#f6dcc8"
            cv.create_line(X(x0 + k * xs / 10), Tp, X(x0 + k * xs / 10), B, fill=c)
        for k in range(ny + 1):
            c = "#d6783c" if k % 10 == 0 else "#ebb995" if k % 5 == 0 else "#f6dcc8"
            cv.create_line(L, Y(y0 + k * ys / 10), R, Y(y0 + k * ys / 10), fill=c)
        cv.create_line(X(0), Tp, X(0), B, fill="#222", width=2)
        cv.create_line(L, Y(0), R, Y(0), fill="#222", width=2)
        for k in range(int(round((x1 - x0) / xs)) + 1):
            v = x0 + k * xs
            cv.create_text(X(v), B + 12, text=("%g" % round(v, 6)), font=("Helvetica", 9))
        for k in range(int(round((y1 - y0) / ys)) + 1):
            v = y0 + k * ys
            cv.create_text(L - 6, Y(v), text=("%g" % round(v, 6)), anchor="e", font=("Helvetica", 9))
        cv.create_text(R, B + 28, text=T("t (s, 스톱워치)", "t (s, stopwatch)"), anchor="e", font=("Helvetica", 11, "bold"))
        cv.create_text(L + 4, Tp + 10, text=T("멀티미터 (mV, µA 또는 kΩ)", "meter (mV, µA or kΩ)"), anchor="w", font=("Helvetica", 11, "bold"))
        tags = []
        for _, _, g in P:
            if g not in tags:
                tags.append(g)
        cols = ["#1a4fb4", "#c0392b", "#2f8f4e", "#8e44ad", "#d35400", "#16a085"]
        for k, g in enumerate(tags):
            if len(tags) < 2 and not g:
                break
            y = Tp + 14 + 16 * k
            cv.create_text(R - 150, y, text="×  " + (g or "—"), anchor="w", fill=cols[k % 6], font=("Helvetica", 10, "bold"))
        for v, i, g in P:
            x, y, c = X(v), Y(i), cols[tags.index(g) % 6]
            cv.create_line(x - 4, y - 4, x + 4, y + 4, fill=c, width=2)
            cv.create_line(x - 4, y + 4, x + 4, y - 4, fill=c, width=2)
        if not P:
            cv.create_text(570, 320, text=T("아직 찍힌 점이 없습니다", "No points yet"), fill="#888", font=("Helvetica", 12))



# --------------------------------------------------------------------------
#  Assembly tab: drag each part from the list onto its place
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
        ttk.Label(right, text=T("조립 구역 — 장치를 끌어다 제자리에 놓으시오",
                                "Assembly area — drag each item to its place"),
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
        pitch = min(60, 620 // len(PARTS))
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
        self.placed.add(key)
        self.app.on_assembly_change(self.placed)
        self.redraw()
        return True


# --------------------------------------------------------------------------
#  Data sheet: what the student wrote down, nothing more
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
    ttk.Label(row, text=label, width=8).pack(side="left")
    for txt, fn in cmds:
        ttk.Button(row, text=txt, width=max(5, len(txt) + 1), command=fn).pack(side="left", padx=1)
    return row


class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.ph = Physics(seed)
        self.title(T(*APP_TITLE))
        self.geometry("1360x860")
        self.placed = set()
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_asm = AssemblyTab(nb, self)
        self.tab_bench = BenchTab(nb, self)
        self.tab_graph = GraphTab(nb, self)
        nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.tab_bench, text=T(" 실험대 ", " Bench "))
        nb.add(self.tab_graph, text=T(" 모눈종이 ", " Graph paper "))
        self.tab_graph.draw()
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
