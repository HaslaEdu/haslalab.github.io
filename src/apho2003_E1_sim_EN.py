#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  4th Asian Physics Olympiad  (APhO 2003, Bangkok, Thailand)
  Experimental Problem 1 :  DETERMINATION OF CAPACITANCE
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* A 50 Hz step-down isolation transformer drives the capacitor C into
  terminal D; terminal E is the transformer's other end.  The resistors
  RA, RB, RC (680, 1500, 3300 ohm as marked, each truly within 5 %) are
  joined between D and E with leads in any series/parallel combination.
* The board is solved as a complex nodal network every reading (winding
  resistance, the meter's 10 Mohm, the leads as given), so any wiring
  works, including wrong ones.
* The digital multimeter shows only what a 3 1/2-digit meter would on
  the chosen range; C, the emf and the true resistances are hidden.
* Hidden truths are randomised every session.
* Standard library only (tkinter).

    Run:   python3 apho2003_E1_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line

TERMS = ["D", "E", "A1", "A2", "B1", "B2", "C1", "C2", "V", "COM"]
RANGES = [("off", "OFF", None), ("a2", "V~ 2", 2.0), ("a20", "V~ 20", 20.0), ("a200", "V~ 200", 200.0), ("a750", "V~ 750", 750.0),
          ("d20", "V⎓ 20", 20.0), ("o2k", "Ω 2k", 2000.0)]


# --------------------------------------------------------------------------
#  Physics core  (V, ohm, F, Hz)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.r = r
        self.C = r.uniform(1.70, 2.30) * 1e-6        # the capacitor: the hidden answer
        self.emf = r.uniform(24.2, 26.4)             # open-circuit secondary, V rms
        self.Rs = r.uniform(8, 22)                   # winding resistance
        self.f = 50 * r.uniform(0.998, 1.002)
        self.R = {"A": 680 * r.uniform(0.96, 1.04), "B": 1500 * r.uniform(0.96, 1.04), "C": 3300 * r.uniform(0.96, 1.04)}
        self.gain = r.uniform(0.996, 1.004)          # the meter's ac calibration
        self.wander = r.uniform(0.0015, 0.0035)
        self.mains = 1.0

    def step(self, dt):
        self.mains += (1 - self.mains) * dt / 40 + self.wander / 60 * math.sqrt(dt) * (random.random() - 0.5) * 2.4


def make_nets(leads):
    par = dict((t, t) for t in TERMS)

    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for a, b in leads:
        par[f(a)] = f(b)
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
        s = b[i] - sum(A[i][c] * x[c] for c in range(i + 1, n))
        x[i] = s / A[i][i]
    return x


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_board(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 100 * s, y - 45 * s, x + 100 * s, y + 45 * s, fill="#caa06c", outline="#8a6a40")
    cv.create_rectangle(x - 90 * s, y - 35 * s, x - 55 * s, y, fill="#4a4d52", outline="")
    cv.create_oval(x - 45 * s, y - 38 * s, x - 15 * s, y - 22 * s, fill="#9aa3ab", outline="#6b7177")
    cv.create_oval(x - 2 * s, y - 12 * s, x + 8 * s, y - 2 * s, fill="#c0392b", outline="")
    cv.create_oval(x - 2 * s, y + 22 * s, x + 8 * s, y + 32 * s, fill="#1f2226", outline="")
    for i in range(3):
        cv.create_rectangle(x + (40 + 20 * i) * s, y - 22 * s, x + (46 + 20 * i) * s, y + 22 * s, fill="#d9c9a0", outline="#9a8a60")


def art_dmm(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 26 * s, y - 45 * s, x + 26 * s, y + 45 * s, fill="#e3b72d", outline="#8a6d12")
    cv.create_rectangle(x - 18 * s, y - 36 * s, x + 18 * s, y - 18 * s, fill="#9fae8f", outline="")
    cv.create_oval(x - 12 * s, y - 6 * s, x + 12 * s, y + 18 * s, fill="#1b1d20", outline="")
    cv.create_oval(x - 14 * s, y + 28 * s, x - 6 * s, y + 36 * s, fill="#111", outline="")
    cv.create_oval(x + 6 * s, y + 28 * s, x + 14 * s, y + 36 * s, fill="#c0392b", outline="")


def art_leads(cv, x, y, sc=1.0):
    s = sc
    for c, r in (("#c0392b", 26), ("#1f2226", 20), ("#2b6cb0", 14)):
        cv.create_oval(x - r * s, y - r * 0.6 * s, x + r * s, y + r * 0.6 * s, outline=c, width=2)


ART = {"board": art_board, "dmm": art_dmm, "leads": art_leads}

PARTS = [
    ("board", ("[1–3] 실험 판 (축전기, 저항 3개, 강압 변압기)", "[1–3] Board (capacitor, 3 resistors, transformer)"), []),
    ("dmm",   ("[4] 디지털 전압계", "[4] Digital voltmeter"), []),
    ("leads", ("[5] 연결 도선", "[5] Connectors"), ["board"]),
]
ZONES = {
    "board": (300, 300, 220, 110),
    "dmm":   (580, 300, 70, 110),
    "leads": (420, 430, 70, 40),
}
SCENE_TITLE = ("실험대 — 실험 판, 전압계, 연결 도선", "The bench — board, voltmeter and connectors")
APP_TITLE = ("APhO 2003 실험 1 — 축전기의 전기 용량", "APhO 2003 Experiment 1 — Determination of capacitance")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    TP = {"D": (430, 250), "E": (430, 470), "C1": (560, 200), "C2": (560, 470), "B1": (640, 200), "B2": (640, 470),
          "A1": (720, 200), "A2": (720, 470), "COM": (760, 600), "V": (840, 600)}

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.leads = []
        self.power = tk.BooleanVar(value=False)
        self.rng = tk.StringVar(value="off")
        self.disp, self.disp_t = 0.0, 0.0
        self.build()
        self.refresh()

    def ok(self):
        return {"board", "dmm", "leads"} <= self.app.placed

    def solve(self):
        ph, f = self.ph, make_nets(self.leads)
        w, gnd = 2 * math.pi * ph.f, f("E")
        el = [("S", f("D"), complex(0, w * ph.C))]
        for k in "ABC":
            el.append((f(k + "1"), f(k + "2"), complex(1 / ph.R[k], 0)))
        if self.rng.get() != "off":
            el.append((f("V"), f("COM"), complex(1e-7, w * 100e-12)))
        names = []
        for p, q, _ in el:
            for n in (p, q):
                if n != gnd and n not in names:
                    names.append(n)
        idx = dict((n, i) for i, n in enumerate(names))
        N = len(names)
        A = [[complex(1e-12, 0)] * N for _ in range(N)]
        for i in range(N):
            A[i][i] = complex(1e-9, 0)
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
        e = ph.emf * ph.mains if self.power.get() else 0.0
        A[idx["S"]][idx["S"]] += 1 / ph.Rs
        b[idx["S"]] += e / ph.Rs
        x = csolve(A, b)
        V = lambda n: 0j if n == gnd else x[idx[n]] if n in idx else 0j
        return V, f

    def raw(self):
        if not self.ok() or self.rng.get() == "off":
            return None
        V, f = self.solve()
        v = abs(V(f("V")) - V(f("COM")))
        k = self.rng.get()
        if k[0] == "a":
            return v * self.ph.gain
        if k[0] == "d":
            return 0.0
        return float("nan")

    def show(self):
        r = self.raw()
        if r is None:
            return ""
        k = self.rng.get()
        R = dict((a, c) for a, _, c in RANGES)[k]
        if k[0] == "o":
            return "1" if random.random() < 0.5 else "%.3f" % (random.random() * 1.999)
        v = self.disp
        if v > R * 0.9995 and R != 750:
            return "1   "
        return ("%.3f" if R == 2 else "%.2f" if R == 20 else "%.1f" if R == 200 else "%.0f") % v

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("디지털 멀티미터", "Digital multimeter"))
        f.pack(fill="x", pady=2)
        self.dV = tk.Label(f, text="", font=("Courier", 22, "bold"), bg="#9fae8f", fg="#1b1d20", width=10)
        self.dV.pack(pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for i, (k, lab, _) in enumerate(RANGES):
            ttk.Radiobutton(row, text=lab, value=k, variable=self.rng, command=self.range_changed).grid(row=i // 4, column=i % 4, sticky="w", padx=2)
        ttk.Label(f, text=T("교류 전압(V~) 범위만 쓰시오. '1'만 보이면 범위 초과.", "Use the ac (V~) ranges only. A lone '1' means over range."),
                  foreground="#555", wraplength=320).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("변압기", "Transformer"))
        f.pack(fill="x", pady=2)
        ttk.Checkbutton(f, text=T("POWER (220 V → 약 24 V, 50 Hz)", "POWER (220 V → about 24 V, 50 Hz)"), variable=self.power).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("배선 — 단자 두 개를 골라 잇기", "Wiring — pick two terminals and join them"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.ta, self.tb = ttk.Combobox(row, values=TERMS, width=6, state="readonly"), ttk.Combobox(row, values=TERMS, width=6, state="readonly")
        self.ta.pack(side="left", padx=2)
        self.tb.pack(side="left", padx=2)
        ttk.Button(row, text=T("잇기", "Join"), command=self.join).pack(side="left", padx=2)
        self.lb = tk.Listbox(f, height=7)
        self.lb.pack(fill="x")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("고른 도선 뽑기", "Unplug selected"), command=self.unplug).pack(side="left", padx=2)
        ttk.Button(row, text=T("모두 뽑기", "Unplug all"), command=self.unplug_all).pack(side="left", padx=2)
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("연결", "Circuit")).pack(side="left")
        self.cent = ttk.Entry(row, width=12)
        self.cent.pack(side="left", padx=2)
        ttk.Button(row, text=T("지금 읽은 값 적기", "Record the reading"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("c", T("연결", "circuit"), 120), ("r", T("범위", "range"), 70), ("V", "V (V)", 90)], height=7)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("실험 판 (위에서 본 모습)", "The board, seen from above"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=900, height=660, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    def range_changed(self):
        self.disp_t = 0.0

    def join(self):
        a, b = self.ta.get(), self.tb.get()
        if a and b and a != b and len(self.leads) < 10 and self.ok():
            self.leads.append((a, b))
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
        lab = dict((a, b) for a, b, _ in RANGES)[self.rng.get()]
        self.sheet.add((self.cent.get() or "?", lab, self.show().replace("1   ", "OL") or "—"))

    def tick(self, dt):
        self.ph.step(dt)
        self.disp_t -= dt
        if self.disp_t <= 0:
            self.disp_t = 0.4
            r = self.raw()
            if r is not None and r == r:
                R = dict((a, c) for a, _, c in RANGES)[self.rng.get()]
                lsd = 0.001 if R == 2 else 0.01 if R == 20 else 0.1 if R == 200 else 1.0
                self.disp = max(0.0, r + (random.random() - 0.5) * 1.6 * lsd)
        self.refresh()

    def refresh(self):
        self.dV.config(text=self.show())
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        if "board" not in self.app.placed:
            cv.create_text(450, 330, text=T("조립 탭에서 실험 판을 놓으시오", "Place the board in the Assembly tab"), fill="#69717a")
            return
        cv.create_rectangle(60, 140, 800, 530, fill="#caa06c", outline="#8a6a40", width=2)
        cv.create_rectangle(90, 170, 220, 280, fill="#4a4d52", outline="#2a2d33")
        cv.create_text(155, 225, text="220V / 24V", fill="#e8eef2", font=("Helvetica", 10, "bold"))
        cv.create_oval(270, 175, 370, 225, fill="#9aa3ab", outline="#6b7177")
        cv.create_text(320, 200, text="C", font=("Helvetica", 14, "bold"))
        cv.create_line(220, 200, 270, 200, 370, 200, 430, 200, 430, 250, fill="#3b2f22", width=3)
        cv.create_line(220, 260, 250, 260, 250, 470, 430, 470, fill="#3b2f22", width=3)
        cv.create_rectangle(110, 380, 170, 420, fill="#c0392b" if self.power.get() else "#7a2a22", outline="#1f2226", width=3)
        cv.create_text(140, 440, text="POWER", font=("Helvetica", 9, "bold"))
        for k in "CBA":
            x = self.TP[k + "1"][0]
            cv.create_line(x, 200, x, 470, fill="#9aa0a6", width=2)
            cv.create_rectangle(x - 10, 290, x + 10, 380, fill="#d9c9a0", outline="#9a8a60")
            cv.create_text(x, 505, text="R" + k, font=("Helvetica", 11, "bold"))
        cv.create_text(640, 160, text="RA 680 Ω · RB 1500 Ω · RC 3300 Ω (±5 %)", font=("Helvetica", 9))
        cv.create_text(405, 250, text="D", font=("Helvetica", 13, "bold"))
        cv.create_text(405, 470, text="E", font=("Helvetica", 13, "bold"))
        if "dmm" in self.app.placed:
            cv.create_rectangle(730, 545, 870, 650, fill="#e3b72d", outline="#8a6d12", width=2)
            cv.create_text(800, 565, text=T("멀티미터 단자", "meter jacks"), font=("Helvetica", 9, "bold"))
        for t, (x, y) in self.TP.items():
            if t in ("V", "COM") and "dmm" not in self.app.placed:
                continue
            col = "#c0392b" if t in ("D", "V") else "#1f2226" if t in ("E", "COM") else "#d4b25a"
            cv.create_oval(x - 9, y - 9, x + 9, y + 9, fill=col, outline="#111")
            if t in ("V", "COM"):
                cv.create_text(x, y + 20, text=t, font=("Helvetica", 9, "bold"))
            elif t[0] in "ABC":
                cv.create_text(x + 18, y, text=t, font=("Helvetica", 8))
        cols = ["#c0392b", "#1f2226", "#2b6cb0", "#d9a21b", "#2f8f4e", "#8e44ad"]
        for i, (a, b) in enumerate(self.leads):
            (x0, y0), (x1, y1) = self.TP[a], self.TP[b]
            mx, my = (x0 + x1) / 2, max(y0, y1) + 30 + 4 * i
            cv.create_line(x0, y0, mx, my, x1, y1, smooth=True, fill=cols[i % len(cols)], width=3)


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
