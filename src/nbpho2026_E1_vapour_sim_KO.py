#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  Nordic-Baltic Physics Olympiad (NBPhO 2026), problem 5
  SATURATION PRESSURE OF WATER
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Apparatus after the problem sheet: a transparent tube (~1.5 m, inner
    diameter ~1.5 mm) with a Luer lock, a syringe, dodecane (D), water (W),
    a metal pin to close the tube, a measuring tape, masking tape, a waste
    container.  The channel from the plunger to the far end of the tube
    holds incompressible liquids and gas segments obeying pV = n at a
    common pressure (plus the hydrostatics of the dodecane when the tube is
    not level).  Water evaporates at its interface towards p_sat at a
    finite rate and condenses above it; a wall that water has touched
    boils off below p_sat; dodecane slowly gives up a little dissolved air.
    Only what can be seen is shown: the contents of the tube beside the
    measuring tape and the syringe with its scale.  p_sat is never shown.
    Every hidden value (room conditions on the board, p_sat, the bore,
    evaporation rate) is drawn afresh for each session.

    Run:   python3 nbpho2026_E1_vapour_sim_KO.py   [--seed=N]
"""
import math
import random
import sys
import time
import tkinter as tk
from tkinter import ttk

LANG = "KO"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "KO" else en


def U(a, b):
    return random.uniform(a, b)


RHO_D, G0 = 750.0, 9.81
SYR_A, SYR_TRAVEL, SYR_TIP = 113.1, 55.0, 25.0     # mm², mm, mm³
MEDIUM = {"air": "air", "D": "dod", "W": "water", "waste": "air"}


class Truth:
    def __init__(self):
        self.T = round(U(20.0, 25.0), 1)
        self.pair = round(U(99.0, 103.0), 1)
        self.psat = 0.61094 * math.exp(17.625 * self.T / (self.T + 243.04)) * U(0.99, 1.01)
        self.L = U(1490, 1520)
        self.A = math.pi * (U(1.45, 1.55) / 2) ** 2
        self.kev = U(45, 80)
        self.sol = U(3e-4, 7e-4)


TR = None


def seg(k, v=0.0, n=0.0):
    return {"k": k, "v": v, "na": n, "nv": 0.0, "p": None}


def gas(s):
    return s["k"] in ("air", "vap")


def nof(s):
    return s["na"] + s["nv"]


class Rig:
    def __init__(self):
        self.conn = False
        self.pin = False
        self.end = "air"
        self.tip = "air"
        self.lift = 0.0
        self.xp = 0.0
        self.joint = 0.0
        self.wet = 0.0
        self.p = None
        self.auto = 0.0
        self.t = 0.0
        self.reset_tube()
        self.reset_syr()

    def reset_tube(self):
        self.tube = [seg("air", n=TR.pair * TR.A * TR.L)]
        self.wet = 0.0
        self.pin = False
        self.end = "air"

    def reset_syr(self):
        self.xp = 0.0
        self.syr = [seg("air", n=TR.pair * self.syr_vol())]

    def syr_vol(self):
        return SYR_A * self.xp + SYR_TIP + (self.joint if self.conn else 0.0)

    def tube_vol(self):
        return TR.A * TR.L

    @staticmethod
    def vol(s, p=None):
        if not gas(s):
            return s["v"]
        return nof(s) / (s["p"] or p or TR.pair)

    @staticmethod
    def merge(lst):
        out = []
        for s in lst:
            if (gas(s) and nof(s) < 1e-6) or (not gas(s) and s["v"] < 1e-6):
                continue
            if out and out[-1]["k"] == s["k"]:
                if gas(s):
                    out[-1]["na"] += s["na"]; out[-1]["nv"] += s["nv"]
                else:
                    out[-1]["v"] += s["v"]
            else:
                out.append(dict(s))
        return out

    def split_back(self, lst):
        vs, acc, a, b = self.syr_vol(), 0.0, [], []
        for s in lst:
            v = self.vol(s, self.p)
            if acc + v <= vs + 1e-9:
                a.append(s)
            elif acc >= vs - 1e-9:
                b.append(s)
            else:
                f = (vs - acc) / v
                s1, s2 = dict(s), dict(s)
                if gas(s):
                    s1["na"], s1["nv"], s2["na"], s2["nv"] = s["na"] * f, s["nv"] * f, s["na"] * (1 - f), s["nv"] * (1 - f)
                else:
                    s1["v"], s2["v"] = s["v"] * f, s["v"] * (1 - f)
                a.append(s1); b.append(s2)
            acc += v
        self.syr, self.tube = (a or [seg("air")]), b

    def height(self, q):
        vs = self.syr_vol()
        return 0.0 if q <= vs else self.lift * min(1.0, (q - vs) / self.tube_vol())

    def solve(self, lst):
        vtot = self.syr_vol() + self.tube_vol()
        vg = vtot - sum(s["v"] for s in lst if not gas(s))
        if vg <= 0:
            return None

        def f(p):
            q = V = 0.0
            for s in lst:
                if gas(s):
                    pi = max(1e-3, p - RHO_D * G0 * self.height(q) / 1000)
                    s["p"] = pi; vi = nof(s) / pi; V += vi; q += vi
                else:
                    q += s["v"]
            return V
        lo, hi = 1e-3, 5000.0
        for _ in range(60):
            m = math.sqrt(lo * hi)
            if f(m) > vg:
                lo = m
            else:
                hi = m
        p = math.sqrt(lo * hi); f(p)
        return p

    def flow_at_end(self, lst, dv, medium):
        for s in lst:
            if gas(s):
                s["p"] = TR.pair
        if dv > 0:
            lst.append(seg("air", n=TR.pair * dv) if medium == "air" else seg(medium, v=dv))
            return
        rem = -dv
        while rem > 1e-9 and lst:
            s = lst[-1]; v = nof(s) / TR.pair if gas(s) else s["v"]
            if v <= rem:
                lst.pop(); rem -= v
            else:
                if gas(s):
                    f = (v - rem) / v; s["na"] *= f; s["nv"] *= f
                else:
                    s["v"] -= rem
                rem = 0

    def relax_open(self, lst, cap, medium, front):
        for s in lst:
            if gas(s):
                s["p"] = TR.pair
        vol = sum(nof(s) / TR.pair if gas(s) else s["v"] for s in lst)
        L = lst[::-1] if front else list(lst)
        self.flow_at_end(L, -(vol - cap), medium)
        return self.merge(L[::-1] if front else L)

    def track_wet(self):
        for s in self.tube:
            if s["k"] == "water" and s["v"] > 0.5:
                self.wet = min(1.0, self.wet + s["v"] / (TR.A * 200))

    def plunger(self, dx):
        x1 = max(0.0, min(SYR_TRAVEL, self.xp + dx)); dx = x1 - self.xp
        if abs(dx) < 1e-9:
            return
        dv = SYR_A * dx
        if self.conn:
            lst = self.syr + self.tube
            if self.pin:
                old = self.xp; self.xp = x1
                p = self.solve(lst)
                if p is None:
                    self.xp = old; return
                self.p = p; self.split_back(lst); return
            self.xp = x1; self.flow_at_end(lst, dv, MEDIUM[self.end]); self.split_back(self.merge(lst)); self.track_wet(); return
        self.xp = x1; lst = list(self.syr); self.flow_at_end(lst, dv, MEDIUM[self.tip]); self.syr = self.merge(lst)

    def connect(self):
        self.joint = U(0.3, 3.0); self.syr.append(seg("air", n=TR.pair * self.joint)); self.conn = True; self.tip = "air"

    def disconnect(self):
        if not self.conn:
            return
        lst = self.syr + self.tube
        if self.pin:
            self.p = self.solve(lst)
        self.split_back(lst); self.conn = False; self.joint = 0.0
        self.syr = self.relax_open(self.syr, self.syr_vol(), "air", False) or [seg("air")]
        self.tube = self.relax_open(self.tube, self.tube_vol(), "air", True)
        if not self.pin:
            self.tube = self.relax_open(self.tube, self.tube_vol(), MEDIUM[self.end], False)
        self.p = None

    def set_pin(self, on):
        if on and not self.pin:
            if self.end != "air":
                return False
            if not self.conn:
                self.tube = self.relax_open(self.tube, self.tube_vol(), "air", False)
            self.pin = True
        elif not on and self.pin:
            self.pin = False
            if self.conn:
                self.split_back(self.relax_open(self.syr + self.tube, self.syr_vol() + self.tube_vol(), MEDIUM[self.end], False))
            else:
                self.tube = self.relax_open(self.tube, self.tube_vol(), MEDIUM[self.end], False)
            self.track_wet(); self.p = None
        return True

    def knock(self):
        g = [s for s in self.syr if gas(s)]
        if not g:
            return
        liq = [s for s in self.syr if not gas(s)]
        tot = seg("air"); tot["na"] = sum(s["na"] for s in g); tot["nv"] = sum(s["nv"] for s in g); tot["p"] = g[0]["p"]
        self.syr = self.merge(liq + [tot])

    def step(self, dt):
        self.t += dt
        if self.auto:
            self.plunger(self.auto * dt)
        if not (self.conn and self.pin):
            self.p = None; return
        lst = self.syr + self.tube
        p = self.solve(lst)
        if p is None:
            return
        n = max(1, int(math.ceil(dt / 0.05))); h = dt / n
        for _ in range(n):
            g = None
            for i, s in enumerate(lst):
                if s["k"] == "water":
                    if i + 1 < len(lst) and gas(lst[i + 1]):
                        g = lst[i + 1]
                    elif i > 0 and gas(lst[i - 1]):
                        g = lst[i - 1]
                    else:
                        g = seg("vap"); g["nv"] = 1e-6; lst.insert(i + 1, g)
                    break
            if g is not None:
                g["nv"] = max(0.0, g["nv"] + TR.kev * (TR.psat - (g["p"] or p)) * h)
            if self.wet > 0:
                far = next((s for s in reversed(lst) if gas(s)), None)
                if far is not None and (far["p"] or p) < TR.psat:
                    far["nv"] += self.wet * 0.6 * TR.kev * (TR.psat - (far["p"] or p)) * h
            for i, s in enumerate(lst):
                if s["k"] != "dod":
                    continue
                s.setdefault("dis", s["v"] * TR.sol * TR.pair)
                nb = lst[i + 1] if i + 1 < len(lst) and gas(lst[i + 1]) else (lst[i - 1] if i > 0 and gas(lst[i - 1]) else None)
                if nb is None:
                    continue
                r = max(0.0, s["dis"] - s["v"] * TR.sol * (nb["p"] or p)) * h / 600
                s["dis"] -= r; nb["na"] += r
            p = self.solve(lst)
        self.p = p; self.split_back(self.merge(lst))

    def tube_layout(self):
        out, x = [], 0.0
        for s in self.tube:
            l = self.vol(s, self.p) / TR.A; out.append((s["k"], x, x + l)); x += l
        return out


COL = {"dod": "#e4c450", "water": "#5aa5e6", "air": "#eef6fa", "vap": "#eef6fa"}


class App:
    def __init__(self, root, seed=None):
        global TR
        if seed is not None:
            random.seed(seed)
        TR = Truth()
        self.R = Rig()
        self.root = root
        self.speed = 1
        self.marks = []
        self.view = [-20.0, 1560.0]
        self.last = time.time()
        root.title(T("NBPhO 2026 실험 — 물의 포화 증기압  ·  HaslaLab", "NBPhO 2026 Experiment — Saturation Pressure of Water  ·  HaslaLab"))
        root.geometry("1300x760")
        self.build()
        self.tick()

    def build(self):
        left = ttk.Frame(self.root, padding=8); left.pack(side="left", fill="y")
        right = ttk.Frame(self.root, padding=8); right.pack(side="left", fill="both", expand=True)
        tk.Label(left, text=T("감독관: T_room = %.1f °C, p_air = %.1f kPa", "Invigilator: T_room = %.1f °C, p_air = %.1f kPa") % (TR.T, TR.pair),
                 font=("Consolas", 12, "bold"), fg="#8fd6ff", bg="#101418").pack(fill="x", pady=4)
        self.conn_b = ttk.Button(left, text="", command=self.toggle_conn); self.conn_b.pack(fill="x", pady=2)
        self.pin_b = ttk.Button(left, text="", command=self.toggle_pin); self.pin_b.pack(fill="x", pady=2)
        for lab, var_name, opts in ((T("관의 먼 끝", "far end of the tube"), "end_v", ("air", "D", "W", "waste")),
                                    (T("주사기 끝 (연결 안 됐을 때)", "syringe tip (when apart)"), "tip_v", ("air", "D", "W", "waste"))):
            ttk.Label(left, text=lab).pack(anchor="w", pady=(8, 0))
            v = tk.StringVar(value="air"); setattr(self, var_name, v)
            fr = ttk.Frame(left); fr.pack(anchor="w")
            names = {"air": T("탁자 위", "on table"), "D": "D", "W": "W", "waste": T("폐액", "waste")}
            for o in opts:
                ttk.Radiobutton(fr, text=names[o], value=o, variable=v, command=self.on_where).pack(side="left")
        ttk.Label(left, text=T("주사기 피스톤 (ml)", "Syringe plunger (ml)")).pack(anchor="w", pady=(10, 0))
        fr = ttk.Frame(left); fr.pack(anchor="w")
        for ml in (-1, -0.1, -0.01, 0.01, 0.1, 1):
            ttk.Button(fr, text="%+g" % ml, width=6, command=lambda ml=ml: self.push(ml)).pack(side="left")
        self.slow_b = ttk.Button(left, text="", command=self.toggle_slow); self.slow_b.pack(fill="x", pady=2)
        ttk.Button(left, text=T("끝을 위로, 톡톡 쳐서 기포를 끝으로", "Tip up, tap the bubbles to the tip"), command=self.R.knock).pack(fill="x", pady=2)
        ttk.Label(left, text=T("관을 놓는 모양", "How the tube lies")).pack(anchor="w", pady=(10, 0))
        self.lift_v = tk.DoubleVar(value=0.0)
        for v, lab in ((0.0, T("수평", "flat")), (0.3, T("먼 끝 30 cm 들기", "far end up 30 cm")), (-0.3, T("주사기 쪽 30 cm 들기", "syringe end up 30 cm"))):
            ttk.Radiobutton(left, text=lab, value=v, variable=self.lift_v, command=lambda: setattr(self.R, "lift", self.lift_v.get())).pack(anchor="w")
        ttk.Button(left, text=T("예비 관으로 바꾸기", "Swap for the spare tube"), command=self.spare).pack(fill="x", pady=6)
        fr = ttk.Frame(left); fr.pack(anchor="w")
        ttk.Label(fr, text=T("시간 배속", "Speed")).pack(side="left")
        for s in (1, 5, 20):
            ttk.Button(fr, text="×%d" % s, width=4, command=lambda s=s: setattr(self, "speed", s)).pack(side="left")
        self.status = tk.Label(left, text="", fg="#b3261e", wraplength=330, justify="left"); self.status.pack(fill="x", pady=6)
        ttk.Label(left, text=T("관 그림: 휠 확대, 클릭 = 마스킹 테이프 표시, 우클릭 = 표시 떼기",
                               "Tube view: wheel zoom, click = masking-tape mark, right-click = remove mark"),
                  wraplength=330, foreground="#7a8794").pack(fill="x")
        self.cv = tk.Canvas(right, bg="#eceae4", highlightthickness=0); self.cv.pack(fill="both", expand=True)
        self.cv.bind("<MouseWheel>", self.wheel); self.cv.bind("<Button-4>", lambda e: self.wheel(e, 1)); self.cv.bind("<Button-5>", lambda e: self.wheel(e, -1))
        self.cv.bind("<Button-1>", self.mark); self.cv.bind("<Button-3>", self.unmark)
        self.cv.bind("<Double-Button-1>", lambda e: setattr(self, "view", [-20.0, 1560.0]))

    def say(self, s):
        self.status.config(text=s)

    def toggle_conn(self):
        if self.R.conn:
            self.R.disconnect(); self.say(T("주사기를 뺐습니다.", "Syringe taken off."))
        else:
            self.R.connect(); self.tip_v.set("air"); self.say(T("주사기를 관에 끼웠습니다.", "Syringe joined to the tube."))

    def toggle_pin(self):
        if not self.R.set_pin(not self.R.pin):
            self.say(T("끝을 액체에서 꺼낸 뒤에 막으세요.", "Lift the end out of the liquid first."))

    def on_where(self):
        self.R.end = self.end_v.get()
        if not self.R.conn:
            self.R.tip = self.tip_v.get()
        if self.R.end != "air":
            self.R.lift = 0.0; self.lift_v.set(0.0)

    def push(self, ml):
        self.R.auto = 0.0; self.R.plunger(ml * 1000 / SYR_A)
        if self.R.conn and self.R.pin:
            self.R.step(0.001)

    def toggle_slow(self):
        self.R.auto = 0.0 if self.R.auto else 0.01 * 1000 / SYR_A

    def spare(self):
        if getattr(self, "spare_used", False):
            self.say(T("예비 관이 없습니다.", "No spare tube left.")); return
        self.spare_used = True; self.R.disconnect(); self.R.reset_tube(); self.marks = []
        self.end_v.set("air"); self.say(T("예비 관으로 바꿨습니다.", "Swapped for the spare tube."))

    def X(self, mm):
        W = self.cv.winfo_width(); return 20 + (mm - self.view[0]) / (self.view[1] - self.view[0]) * (W - 40)

    def mm_at(self, x):
        W = self.cv.winfo_width(); return self.view[0] + (x - 20) / (W - 40) * (self.view[1] - self.view[0])

    def wheel(self, e, sign=None):
        s = sign if sign is not None else (1 if e.delta > 0 else -1)
        c = self.mm_at(e.x); f = (e.x - 20) / max(1, self.cv.winfo_width() - 40)
        span = max(20, min(1580, (self.view[1] - self.view[0]) * (1 / 1.3 if s > 0 else 1.3)))
        self.view = [c - f * span, c - f * span + span]

    def mark(self, e):
        if 60 < e.y < 200:
            m = self.mm_at(e.x)
            if 0 <= m <= TR.L:
                self.marks.append(m)

    def unmark(self, e):
        if self.marks:
            m = self.mm_at(e.x); self.marks.remove(min(self.marks, key=lambda v: abs(v - m)))

    def draw(self):
        c = self.cv; c.delete("all"); W = c.winfo_width(); X = self.X
        yc, hh = 120, 16
        c.create_rectangle(X(0), yc - hh, X(TR.L), yc + hh, fill="#e1eef5", outline="#7d8f9c")
        for k, a, b in self.R.tube_layout():
            c.create_rectangle(max(X(a), 0), yc - hh * 0.7, min(X(b), W), yc + hh * 0.7, fill=COL[k], outline="")
        c.create_text(max(4, X(0)), yc + hh + 14, anchor="w", text=T("주사기 쪽 끝", "syringe end"))
        end_txt = T("핀으로 막힘", "pinned") if self.R.pin else {"air": T("열림", "open"), "D": "D", "W": "W", "waste": T("폐액", "waste")}[self.R.end]
        c.create_text(min(W - 4, X(TR.L)), yc + hh + 14, anchor="e", text=T("먼 끝 · ", "far end · ") + end_txt)
        ty = yc + hh + 30
        if self.R.end == "air" and self.R.lift == 0:
            c.create_rectangle(X(-12), ty, X(1545), ty + 40, fill="#f2d13a", outline="#b49a20")
            pxmm = (W - 40) / (self.view[1] - self.view[0]); minor = 1 if pxmm > 6 else 5 if pxmm > 1.2 else 10
            for mm in range(0, 1541, minor):
                x = X(mm)
                if -2 < x < W + 2:
                    big = mm % 100 == 0
                    c.create_line(x, ty, x, ty + (22 if big else 16 if mm % 50 == 0 else 12 if mm % 10 == 0 else 6))
                    if big:
                        c.create_text(x + 2, ty + 31, anchor="w", text=str(mm // 10), font=("Arial", 10, "bold"))
        else:
            c.create_text(W / 2, ty + 20, text=T("줄자를 대려면 관을 탁자 위에 수평으로 펴세요", "Lay the tube flat on the table to put the tape beside it"))
        for m in self.marks:
            x = X(m); c.create_rectangle(x - 5, yc - hh - 14, x + 5, yc + hh + 4, fill="#efe2b4", outline="#b9ad86"); c.create_line(x, yc - hh - 12, x, yc + hh + 2, fill="#c0392b", width=2)
        # the syringe
        x0, ln, sy = W * 0.35, 380, 330
        mm2 = ln / (SYR_TRAVEL + 6); xt = x0 + ln; xf = xt - (self.R.xp + 1) * mm2
        vb = self.R.syr_vol() - SYR_TIP - (self.R.joint if self.R.conn else 0); q = 0.0
        for s in self.R.syr:
            v = self.R.vol(s, self.R.p); a = xf + min(1, q / max(vb, 1e-6)) * (xt - xf); q += v; b = xf + min(1, q / max(vb, 1e-6)) * (xt - xf)
            if b > a:
                c.create_rectangle(a, sy - 30, b, sy + 30, fill=COL[s["k"]], outline="")
        c.create_rectangle(x0, sy - 34, xt, sy + 34, outline="#6d7c88", width=2)
        c.create_rectangle(xt, sy - 9, xt + 26, sy + 9, outline="#6d7c88")
        for i in range(51):
            x = xt - (1 + i / 10 * 1000 / SYR_A) * mm2
            if x < x0:
                break
            c.create_line(x, sy - 34, x, sy - 34 + (24 if i % 10 == 0 else 16 if i % 5 == 0 else 9))
            if i % 5 == 0:
                c.create_text(x, sy - 44, text=("%g" % (i / 10)), font=("Arial", 10, "bold"))
        c.create_rectangle(xf - 8, sy - 32, xf, sy + 32, fill="#2a2c30"); c.create_line(xf - 8, sy, xf - 8 - ln - 40, sy, width=8, fill="#d9d9d4")
        c.create_text(xt + 26, sy + 52, anchor="e", text=(T("관에 연결됨", "joined to the tube") if self.R.conn else T("끝: ", "tip: ") + self.R.tip))
        if self.R.wet > 0:
            c.create_text(W / 2, 30, text=T("관 안쪽 벽에 물이 묻었습니다!", "Water reached the tube's inner wall!"), fill="#b3261e", font=("Arial", 12, "bold"))

    def tick(self):
        now = time.time(); dt = min(0.1, now - self.last); self.last = now
        rem = dt * self.speed
        while rem > 1e-9:
            h = min(0.1, rem); self.R.step(h); rem -= h
        self.conn_b.config(text=T("주사기 빼기", "Take the syringe off") if self.R.conn else T("주사기를 관에 끼우기", "Join the syringe to the tube"))
        self.pin_b.config(text=T("핀 뽑기", "Pull the pin out") if self.R.pin else T("핀으로 먼 끝 막기", "Close the far end with the pin"))
        self.slow_b.config(text=T("천천히 당기기 멈춤", "Stop the slow pull") if self.R.auto else T("천천히 당기기 (0.01 ml/s)", "Slow pull (0.01 ml/s)"))
        self.draw()
        self.root.after(50, self.tick)


def main():
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
    root = tk.Tk()
    App(root, seed)
    root.mainloop()


if __name__ == "__main__":
    main()
