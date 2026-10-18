#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  35th International Physics Olympiad  (IPhO 2004, Pohang, Korea)
  Experimental Problem :  MECHANICAL "BLACK BOX"
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* A ball (r = 11 mm) between two springs in a black tube.  Part A: the
  tube balances where its centre of mass lies, l_cm = m l / (M + m).
* Part B: the falling weight spins the tube on the rotation stage; the
  ball holds by static friction until m w^2 l exceeds it, then slides
  (with the weaker sliding friction) towards the end cap, the spring
  stretching as m w^2 x = k (x - l) + f.  Energy conservation (friction
  losses ignored, as the problem allows) gives the weight's speed after
  falling h; the photogate times the weight's length d through its beam.
* Part C: hung by pins at either end, the ball sags by mg/k; the periods
  follow the physical-pendulum formula.
* m, M, k1, k2, the frictions and the stage's inertia are hidden.
* Standard library only (tkinter).

    Run:   python3 ipho2004_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line

G = 9.8


# --------------------------------------------------------------------------
#  Physics core
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.r_ = r
        self.m, self.M = r.uniform(0.056, 0.068), r.uniform(0.076, 0.082)
        self.L, self.dl, self.r = 0.400 + r.uniform(-0.0006, 0.0006), 0.005, 0.011
        self.k, asym = r.uniform(7.6, 9.4), r.uniform(0.20, 0.32)
        self.k2 = self.k * (1 + asym) / 2
        self.k1 = self.k - self.k2
        self.Istage, self.R = r.uniform(0.50e-3, 0.62e-3), r.uniform(0.01945, 0.01965)
        self.mo, self.d = r.uniform(0.1000, 0.1010), r.uniform(0.0260, 0.0264)
        self.fs, self.fk = r.uniform(0.23, 0.29), r.uniform(0.035, 0.06)
        self.l = (self.k2 - self.k1) / self.k * self.xend()
        self.Itube = self.M * self.L ** 2 / 12 * r.uniform(1.02, 1.08)
        self.Io = self.M * self.L ** 2 / 3 * r.uniform(1.0, 1.08)
        self.lcm = self.m * self.l / (self.m + self.M)

    def xend(self):
        return self.L / 2 - self.dl - self.r

    def rot_energy(self, w, x):
        I = self.Istage + self.Itube + self.m * (x * x + 0.4 * self.r ** 2)
        return 0.5 * (self.mo * self.R ** 2 + I) * w * w + 0.5 * self.k * (x - self.l) ** 2

    def slide_x(self, w, x0):
        den = self.k - self.m * w * w
        if den <= 0:
            return self.xend()
        return max(x0, min(self.xend(), (self.k * self.l - self.fk) / den))

    def speed_after(self, h, x0, fs):
        E = self.mo * G * h
        ws = math.sqrt(fs / (self.m * x0))
        if E <= self.rot_energy(ws, x0):
            I = self.Istage + self.Itube + self.m * (x0 * x0 + 0.4 * self.r ** 2)
            return math.sqrt(max(0.0, 2 * (E - 0.5 * self.k * (x0 - self.l) ** 2) / (self.mo * self.R ** 2 + I))) * self.R
        if E <= self.rot_energy(ws, self.slide_x(ws, x0)):
            return ws * self.R
        a, b = ws, 60.0
        for _ in range(60):
            w = (a + b) / 2
            if self.rot_energy(w, self.slide_x(w, x0)) < E:
                a = w
            else:
                b = w
        return (a + b) / 2 * self.R

    def gate_time(self, h1, beam):
        """the weight, its top at h1 at rest, falls; the time its length takes to pass the beam (s)"""
        x0 = self.l + self.r_.uniform(-0.0006, 0.0006)
        fs = self.fs * self.r_.uniform(0.97, 1.03)
        h, t, dt, enter = 0.0, 0.0, 0.0005, None
        while True:
            v = max(0.004, self.speed_after(max(h, 1e-5), x0, fs))
            h += v * dt
            t += dt
            top = h1 - h
            if enter is None and top - self.d <= beam:
                enter = t - min(1.0, (beam - (top - self.d)) / (v * dt)) * dt
            if enter is not None and top <= beam:
                return t - min(1.0, (beam - top) / (v * dt)) * dt - enter
            if top - self.d < 0.02:
                return None

    def period(self, end):
        arm_l = self.l if end == 1 else -self.l
        dlx = min(self.xend() - arm_l, self.m * G / self.k)
        arm = self.L / 2 + arm_l + dlx
        tq = self.M * G * self.L / 2 + self.m * G * arm
        I = self.Io + self.m * (arm * arm + 0.4 * self.r ** 2)
        return 2 * math.pi * math.sqrt(I / tq)


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def box_art(col, w, h):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_rectangle(x - w * s, y - h * s, x + w * s, y + h * s, fill=col, outline="#555")
    return art


ART = {"stage": box_art("#6b7178", 24, 16), "mbb": box_art("#16181b", 60, 6), "weight": box_art("#c9a43b", 6, 12), "stand": box_art("#b7bdc3", 6, 60),
       "gate": box_art("#1f2226", 14, 10), "timer": box_art("#2b6cb0", 24, 16), "usup": box_art("#9aa1a8", 18, 6), "balance": box_art("#e9ecef", 26, 18),
       "ruler": box_art("#d6e4ec", 60, 5), "caliper": box_art("#c9ced3", 30, 6)}
PARTS = [
    ("stage",   ("[E·F] 회전대", "[E·F] Rotation stage"), []),
    ("mbb",     ("[D] 역학 블랙박스", "[D] Mechanical black box"), []),
    ("stand",   ("[O] 자 달린 스탠드 (도르래 G)", "[O] Stand with ruler (pulleys G)"), []),
    ("weight",  ("[M] 실 달린 추", "[M] Weight with string"), ["stage", "stand"]),
    ("gate",    ("[B] 광문", "[B] Photogate"), ["stand"]),
    ("timer",   ("[A] 광문 타이머", "[A] Photogate timer"), []),
    ("usup",    ("[P·Q] U자 받침 (핀 H)", "[P·Q] U-support (pins H)"), []),
    ("balance", ("[N] 전자저울", "[N] Electronic balance"), []),
    ("ruler",   ("자 0.50 m", "Ruler 0.50 m"), []),
    ("caliper", ("버니어 캘리퍼", "Vernier calipers"), []),
]
ZONES = {"stage": (140, 200, 56, 40), "mbb": (140, 120, 130, 20), "stand": (380, 230, 20, 140), "weight": (420, 180, 20, 30), "gate": (420, 300, 34, 24),
         "timer": (560, 300, 56, 40), "usup": (560, 120, 44, 20), "balance": (600, 420, 60, 44), "ruler": (180, 420, 130, 14), "caliper": (380, 420, 70, 14)}
SCENE_TITLE = ("회전대 · 블랙박스 · 스탠드 · 광문 · 저울", "Rotation stage · black box · stand · photogate · balance")
APP_TITLE = ("IPhO 2004 실험 — 역학 블랙박스", "IPhO 2004 Experiment — Mechanical black box")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.edge = 0.20
        self.h1, self.beam = 0.40, 0.25
        self.end = tk.IntVar(value=1)
        self.tmode = tk.StringVar(value="gate")
        self.show_t = ""
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("광문 타이머 · 저울 · 캘리퍼", "Timer · balance · calipers"))
        f.pack(fill="x", pady=2)
        self.lbl = tk.Label(f, text="", font=("Courier", 18, "bold"), bg="#0d0e10", fg="#ff5a3c", width=14)
        self.lbl.pack(anchor="w", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Radiobutton(row, text="GATE", value="gate", variable=self.tmode).pack(side="left")
        ttk.Radiobutton(row, text="PERIOD", value="period", variable=self.tmode).pack(side="left")
        self.bal = ttk.Label(f, text="", font=("Courier", 11))
        self.bal.pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("A부: 받침 위 균형", "Part A: balancing on the support"))
        f.pack(fill="x", pady=2)
        stepper(f, T("받침 위치", "Support place"), [("−1 mm", lambda: self.mv(-0.001)), ("−0.1", lambda: self.mv(-0.0001)), ("+0.1", lambda: self.mv(0.0001)), ("+1 mm", lambda: self.mv(0.001))])
        self.tip = ttk.Label(f, text="", font=("Helvetica", 11, "bold"))
        self.tip.pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("B부: 추 떨어뜨리기", "Part B: drop the weight"))
        f.pack(fill="x", pady=2)
        stepper(f, "h1", [("−1 cm", lambda: self.hh("h1", -0.01)), ("−1 mm", lambda: self.hh("h1", -0.001)), ("+1 mm", lambda: self.hh("h1", 0.001)), ("+1 cm", lambda: self.hh("h1", 0.01))])
        stepper(f, T("광문", "Gate"), [("−1 cm", lambda: self.hh("beam", -0.01)), ("−1 mm", lambda: self.hh("beam", -0.001)), ("+1 mm", lambda: self.hh("beam", 0.001)), ("+1 cm", lambda: self.hh("beam", 0.01))])
        ttk.Button(f, text=T("추 놓기", "Release"), command=self.release).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("C부: 진자", "Part C: pendulum"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Radiobutton(row, text=T("끝 1로 매달기", "Hang by end 1"), value=1, variable=self.end).pack(side="left")
        ttk.Radiobutton(row, text=T("끝 2로 매달기", "Hang by end 2"), value=2, variable=self.end).pack(side="left")
        ttk.Button(row, text=T("흔들어 주기 재기", "Swing and time"), command=self.swing).pack(side="left", padx=6)
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("메모", "Note")).pack(side="left")
        self.en = ttk.Entry(row, width=14)
        self.en.pack(side="left", padx=2)
        ttk.Button(row, text=T("적기", "Write"), command=self.record).pack(side="left")
        self.sheet = DataSheet(f, [("n", T("메모", "note"), 140), ("t", T("타이머", "timer"), 110)], height=5)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=400)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("받침 위의 관과 자 · 스탠드의 자", "The tube on its support with the ruler · the stand's ruler"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    def mv(self, d):
        self.edge = max(0.05, min(self.ph.L - 0.05, round(self.edge + d, 5)))

    def hh(self, which, d):
        v = getattr(self, which) + d
        setattr(self, which, max(0.03, min(0.74, round(v, 4))))

    def release(self):
        if not (self.has("stage") and self.has("mbb") and self.has("weight") and self.has("stand")):
            self.warn.config(text=T("회전대·블랙박스·추·스탠드가 필요합니다.", "Needs the stage, black box, weight and stand."))
            return
        if not (self.has("gate") and self.has("timer")) or self.tmode.get() != "gate":
            return
        dt = self.ph.gate_time(self.h1, self.beam)
        self.show_t = "—" if dt is None else "%.1f ms" % (dt * 1000 + random.uniform(-0.04, 0.04))
        self.h1 = max(self.ph.d + 0.02, self.h1)

    def swing(self):
        if not (self.has("usup") and self.has("mbb") and self.has("gate") and self.has("timer")) or self.tmode.get() != "period":
            self.warn.config(text=T("U자 받침·블랙박스·광문·타이머(PERIOD)가 필요합니다.", "Needs the U-support, black box, photogate and timer on PERIOD."))
            return
        amp = random.uniform(0.035, 0.06)
        self.show_t = "%.4f s" % (self.ph.period(self.end.get()) * (1 + amp * amp / 16) + random.uniform(-0.0003, 0.0003))

    def record(self):
        self.sheet.add((self.en.get(), self.show_t))

    def tick(self, dt):
        self.refresh()

    def refresh(self):
        ph = self.ph
        self.lbl.config(text=self.show_t if self.has("timer") else "—")
        parts = []
        if self.has("balance"):
            parts.append(T("저울: MBB %.1f g · 추 %.1f g", "balance: MBB %.1f g · weight %.1f g") % ((ph.M + ph.m) * 1000, ph.mo * 1000))
        if self.has("caliper"):
            parts.append(T("캘리퍼: 2R = %.2f mm · d = %.2f mm", "calipers: 2R = %.2f mm · d = %.2f mm") % (round(2 * ph.R * 1000 * 20) / 20, round(ph.d * 1000 * 20) / 20))
        if self.has("ruler"):
            parts.append(T("자: L = %.1f cm", "ruler: L = %.1f cm") % (round(ph.L * 1000) / 10))
        self.bal.config(text="\n".join(parts))
        c = self.edge - ph.L / 2
        e = ph.lcm - c
        s = 0 if abs(e) < 0.00025 else (1 if e > 0 else -1)
        self.tip.config(text=[T("끝 1 쪽이 내려감", "end 1 goes down"), T("수평 — 균형", "level — balanced"), T("끝 2 쪽이 내려감", "end 2 goes down")][s + 1])
        self.draw(s)

    def draw(self, s):
        cv, ph = self.cv, self.ph
        cv.delete("all")
        if self.has("mbb") and self.has("usup"):
            k, x0, y0 = 16.0, 40, 140
            ex = x0 + self.edge * 100 * k
            a = s * 0.05
            cv.create_polygon(ex, y0 + 18, ex - 14, y0 + 60, ex + 14, y0 + 60, fill="#9aa1a8", outline="#555")
            ca, sa = math.cos(a), math.sin(a)
            p = lambda u, v: (ex + u * ca - v * sa, y0 + u * sa + v * ca)
            L0, L1 = -self.edge * 100 * k, (ph.L - self.edge) * 100 * k
            cv.create_polygon(*p(L0, -16), *p(L1, -16), *p(L1, 16), *p(L0, 16), fill="#16181b")
            cv.create_text(*p(L0 + 14, 0), text="1", fill="#e8eef2")
            cv.create_text(*p(L1 - 14, 0), text="2", fill="#e8eef2")
            if self.has("ruler"):
                for mm in range(0, 401, 5):
                    X = x0 + mm / 10.0 * k
                    cv.create_line(X, y0 + 64, X, y0 + 64 + (14 if mm % 50 == 0 else 7), fill="#111")
                    if mm % 50 == 0:
                        cv.create_text(X, y0 + 88, text=str(mm // 10), font=("Helvetica", 8))
        # the stand's ruler near the weight and the beam
        for col, (center, lab) in enumerate(((self.h1, T("추 윗면 h1", "weight top h1")), (self.beam, T("광문 빛줄기", "photogate beam")))):
            x0, w, cy, k = 60 + col * 360, 320, 470, 55.0
            cv.create_rectangle(x0, 320, x0 + w, 620, fill="#fbfaf4", outline="#888")
            cv.create_text(x0 + w / 2, 334, text=lab, font=("Helvetica", 9, "bold"))
            for mm in range(int((center - 0.03) * 1000), int((center + 0.03) * 1000) + 1):
                y = cy - (mm / 1000.0 - center) * 100 * k
                if 345 < y < 615:
                    L0 = 30 if mm % 10 == 0 else (20 if mm % 5 == 0 else 10)
                    cv.create_line(x0 + 90, y, x0 + 90 + L0, y, fill="#222")
                    if mm % 10 == 0:
                        cv.create_text(x0 + 140, y, text=str(mm // 10), font=("Helvetica", 9, "bold"))
            cv.create_line(x0 + 60, cy, x0 + w - 20, cy, fill="#c0392b", width=2)


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
