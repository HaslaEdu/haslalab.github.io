#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  Nordic-Baltic Physics Olympiad 2021  (NBPhO 2021)
  Problem 4 (experimental) :  STRETCHING GLOVES
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* Bands are cut from latex gloves at the width you choose (by hand, so a
  little off) and lie on graph paper, where their width and the two
  marks you draw can be read against the 1 mm grid.
* Latex keeps its volume: a band of initial width d0 and thickness a0
  under a force F carries the nominal stress s = F/(d0 a0), and takes the
  strain e with s(1 + e) = G(l - l^-2)(1 + c(l - 1)^q), fitted to the
  official solution's table.  Bands joined end to end carry the same
  force, so a chain of different widths spreads its strain over them.
* Each band breaks near the session's breaking strain; one in a few has a
  nick and breaks early, and a wide band joined flat tears at its knot.
* The chain's first band is fixed near the table's left end; the pulled
  end can walk up to 3.5 m away.  A 1 m measuring tape slides along the
  chain to read the marks.  Nothing is computed for you.
* Standard library only (tkinter).

    Run:   python3 nbpho2021_E1_gloves_sim_EN.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the EN edition differs only in this line

TXT = {
 "en": dict(
  title="NBPhO 2021 — Stretching Gloves (virtual lab)",
  cut="1. Cut a band", glove="glove", width="width (mm)", length="length (mm)", cutb="Cut with the scissors",
  mark="2. Draw the marks", band="band", l0="mark spacing (mm)", markb="Draw two lines", toss="Discard",
  chain="3. Join into a chain", roll="Roll it and join", flat="Join it flat", unchain="Take the chain apart",
  pull="4. Pull", slow="Pull slowly", stop="Stop", release="Let go",
  paper="Bands on the graph paper", tape="The chain on the measuring tape",
  help="wheel: zoom · drag: move · drag the yellow tape to slide it · double-click: first scale",
  left=lambda i, l: f"glove {i+1} (about {l} mm of width left)",
  stripopt=lambda s: f"#{s['n']} glove {s['g']+1}, about {s['w']} mm × {s['L']} mm" + (" · rolled" if s["rolled"] else "") + (" · in chain" if s["in"] else ""),
  none="(no bands)", empty="chain: empty", head="chain (fixed → pulled): ",
  m=dict(badnum="Check the numbers.", badw="Choose a width of 2–90 mm.", badl="Choose a length of 40–170 mm.", noroom="That glove has not that much width left.",
         cut="Band #{} cut.", pick="Choose a band first.", badl0="The marks must lie inside the last 8 mm at each end.", marked="Marks drawn on band #{}.",
         remark="It is marked already.", rolled="A rolled band is hard to mark.", inchain="That band is in the chain.", chained="Band #{} joined.",
         tossed="Band #{} thrown away.", unchained="Chain taken apart.", nochain="There is no chain.", far="You cannot walk further away (3.5 m).",
         snap="Snap! Band #{} broke and the chain came apart.", released="Let go; the chain is slack again.", slack="slack", taut="taut")),
 "ko": dict(
  title="NBPhO 2021 — 고무장갑 늘이기 (가상 실험실)",
  cut="1. 띠 자르기", glove="장갑", width="폭 (mm)", length="길이 (mm)", cutb="가위로 자르기",
  mark="2. 표시선 긋기", band="띠", l0="선 간격 (mm)", markb="두 줄 긋기", toss="버리기",
  chain="3. 사슬로 잇기", roll="말아서 잇기", flat="펴진 채로 잇기", unchain="사슬 풀기",
  pull="4. 당기기", slow="천천히 당기기", stop="멈추기", release="놓기",
  paper="모눈종이 위 띠", tape="줄자 위 사슬",
  help="휠: 확대 · 끌기: 이동 · 노란 줄자를 끌면 미끄러집니다 · 더블클릭: 처음 배율",
  left=lambda i, l: f"장갑 {i+1} (남은 폭 약 {l} mm)",
  stripopt=lambda s: f"#{s['n']} 장갑 {s['g']+1}, 약 {s['w']} mm × {s['L']} mm" + (" · 말림" if s["rolled"] else "") + (" · 사슬" if s["in"] else ""),
  none="(띠 없음)", empty="사슬: 비어 있음", head="사슬 (고정 → 당김): ",
  m=dict(badnum="숫자를 확인하세요.", badw="폭은 2–90 mm로 정하세요.", badl="길이는 40–170 mm로 정하세요.", noroom="이 장갑에는 그만한 폭이 남아 있지 않습니다.",
         cut="띠 #{}을(를) 잘랐습니다.", pick="띠를 먼저 고르세요.", badl0="선은 양 끝 8 mm 안쪽에 있어야 합니다.", marked="띠 #{}에 표시선을 그었습니다.",
         remark="이미 표시선이 있습니다.", rolled="말아 놓은 띠에는 선을 긋기 어렵습니다.", inchain="그 띠는 사슬에 있습니다.", chained="띠 #{}을(를) 이었습니다.",
         tossed="띠 #{}을(를) 버렸습니다.", unchained="사슬을 풀었습니다.", nochain="사슬이 없습니다.", far="더 멀리 갈 수 없습니다 (3.5 m).",
         snap="딱! 띠 #{}이(가) 끊어져 사슬이 풀렸습니다.", released="손을 놓았습니다. 사슬이 느슨해졌습니다.", slack="느슨함", taut="팽팽함")),
}[LANG]

# ── the hidden truth of this session (mm, MPa) ──────────────────────────
G, C, Q = 0.010912, 1.1095e-5, 6.6
UNIT = random.uniform(27, 32)
EM = random.uniform(5.2, 5.8)
A0 = [random.uniform(0.135, 0.15) for _ in range(6)]
X0 = random.uniform(18, 26)
END, JOINT, REACH = 8.0, 10.0, 3500.0


def s_nom(lam):
    return G * (lam - 1 / lam ** 2) * (1 + C * max(lam - 1, 0) ** Q) * UNIT


def eps_of(s):
    if s <= 0:
        return 0.0
    lo, hi = 0.0, 12.0
    for _ in range(60):
        m = (lo + hi) / 2
        if s_nom(1 + m) < s:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


class Lab:
    def __init__(self):
        self.left = [190.0] * 6
        self.strips, self.chain = [], []
        self.xe, self.paper_y, self.n = None, 12.0, 0
        self.tape_off = 0.0

    def strip(self, n):
        return next((s for s in self.strips if s["n"] == n), None)

    def cut(self, g, w, L):
        if not (2 <= w <= 90):
            return "badw"
        if not (40 <= L <= 170):
            return "badl"
        if self.left[g] < w + 1:
            return "noroom"
        self.left[g] -= w + 1
        self.n += 1
        d0 = max(1.2, w + random.gauss(0, 0.35))
        nick = random.random() < 0.15
        s = dict(n=self.n, g=g, w=round(w, 1), L=round(L), d0=d0, a0=A0[g] * (1 + random.gauss(0, 0.012)),
                 eb=EM * (1 + random.gauss(0, 0.022)) * (random.uniform(0.55, 0.9) if nick else 1),
                 marks=None, rolled=False, broken=False, px=10, py=self.paper_y,
                 ph=(random.uniform(0, 6), random.uniform(0, 6)))
        s["in"] = False
        self.paper_y += math.ceil(d0) + 8
        self.strips.append(s)
        return ("cut", s["n"])

    def natural_end(self):
        S = [self.strip(n) for n in self.chain]
        return X0 + sum(s["L"] - 2 * END for s in S) + (len(S) - 1) * JOINT

    def state(self):
        if not self.chain or self.xe is None:
            return None
        S = [self.strip(n) for n in self.chain]
        A = [s["L"] - 2 * END for s in S]
        span = self.xe - X0 - (len(S) - 1) * JOINT
        eps = [0.0] * len(S)
        F = 0.0
        if span > sum(A) + 1e-9:
            k = [s["d0"] * s["a0"] for s in S]
            def length(F):
                return sum(a * (1 + eps_of(F / ki)) for a, ki in zip(A, k))
            lo, hi = 0.0, s_nom(13) * max(k)
            for _ in range(50):
                m = (lo + hi) / 2
                if length(m) < span:
                    lo = m
                else:
                    hi = m
            F = (lo + hi) / 2
            eps = [eps_of(F / ki) for ki in k]
        seg, x = [], X0
        for s, a, e in zip(S, A, eps):
            seg.append(dict(s=s, x0=x, x1=x + a * (1 + e), eps=e))
            x += a * (1 + e) + JOINT
        return dict(F=F, seg=seg, taut=F > 0)

    def pull(self, dx):
        if not self.chain:
            return "nochain"
        x = self.xe + dx
        msg = None
        if x > REACH:
            x, msg = REACH, "far"
        self.xe = max(self.natural_end(), x)
        st = self.state()
        if st and st["taut"]:
            for g in st["seg"]:
                if g["eps"] > g["s"]["ebeff"]:
                    g["s"]["broken"] = True
                    for n in self.chain:
                        self.strip(n)["in"] = False
                    self.chain, self.xe = [], None
                    return ("snap", g["s"]["n"])
        return msg


def on_tape(g, u):
    s = g["s"]
    return g["x0"] + (max(END, min(s["L"] - END, u)) - END) * (1 + g["eps"])


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TXT["title"])
        self.geometry("1320x820")
        self.lab = Lab()
        self.view = {"paper": [1.0, 0.0, 0.0], "tape": [1.0, 0.0, 0.0]}
        self.tab = tk.StringVar(value="paper")
        self.slow = False
        side = ttk.Frame(self, padding=8)
        side.pack(side="right", fill="y")
        main = ttk.Frame(self, padding=6)
        main.pack(side="left", fill="both", expand=True)
        bar = ttk.Frame(main)
        bar.pack(fill="x")
        for k in ("paper", "tape"):
            ttk.Radiobutton(bar, text=TXT[k], value=k, variable=self.tab, command=self.draw).pack(side="left", padx=4)
        self.cv = tk.Canvas(main, bg="#fbfaf2", highlightthickness=0)
        self.cv.pack(fill="both", expand=True, pady=4)
        ttk.Label(main, text=TXT["help"], foreground="#555").pack(anchor="w")

        def head(t):
            ttk.Label(side, text=t, font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(10, 2))

        head(TXT["cut"])
        self.glove = ttk.Combobox(side, state="readonly", width=34)
        self.glove.pack(anchor="w")
        self.w = self.entry(side, TXT["width"], "10")
        self.L = self.entry(side, TXT["length"], "140")
        ttk.Button(side, text=TXT["cutb"], command=self.do_cut).pack(fill="x")
        head(TXT["mark"])
        self.sel = ttk.Combobox(side, state="readonly", width=34)
        self.sel.pack(anchor="w")
        self.l0 = self.entry(side, TXT["l0"], "80")
        r = ttk.Frame(side); r.pack(fill="x")
        ttk.Button(r, text=TXT["markb"], command=self.do_mark).pack(side="left", expand=True, fill="x")
        ttk.Button(r, text=TXT["toss"], command=self.do_toss).pack(side="left", expand=True, fill="x")
        head(TXT["chain"])
        r = ttk.Frame(side); r.pack(fill="x")
        ttk.Button(r, text=TXT["roll"], command=lambda: self.do_join(True)).pack(side="left", expand=True, fill="x")
        ttk.Button(r, text=TXT["flat"], command=lambda: self.do_join(False)).pack(side="left", expand=True, fill="x")
        ttk.Button(side, text=TXT["unchain"], command=self.do_unchain).pack(fill="x")
        self.chainlbl = ttk.Label(side, text="", wraplength=300)
        self.chainlbl.pack(anchor="w", pady=2)
        head(TXT["pull"])
        r = ttk.Frame(side); r.pack(fill="x")
        for lab, dx in (("◀10", -10), ("◀1", -1), ("1▶", 1), ("10▶", 10), ("100▶", 100)):
            ttk.Button(r, text=lab, width=5, command=lambda d=dx: self.do_pull(d)).pack(side="left")
        r = ttk.Frame(side); r.pack(fill="x")
        self.slowb = ttk.Button(r, text=TXT["slow"], command=self.toggle_slow)
        self.slowb.pack(side="left", expand=True, fill="x")
        ttk.Button(r, text=TXT["release"], command=self.do_release).pack(side="left", expand=True, fill="x")
        self.msg = ttk.Label(side, text="", foreground="#a0522d", wraplength=300)
        self.msg.pack(anchor="w", pady=10)
        self.cv.bind("<Configure>", lambda e: self.draw())
        self.cv.bind("<MouseWheel>", self.wheel)
        self.cv.bind("<Button-4>", lambda e: self.wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self.wheel(e, -1))
        self.cv.bind("<ButtonPress-1>", self.press)
        self.cv.bind("<B1-Motion>", self.motion)
        self.cv.bind("<Double-Button-1>", self.reset)
        self.refresh()
        self.after(100, self.tick)

    def entry(self, parent, label, val):
        f = ttk.Frame(parent); f.pack(fill="x")
        ttk.Label(f, text=label, width=18).pack(side="left")
        e = ttk.Entry(f, width=10); e.insert(0, val); e.pack(side="left")
        return e

    def say(self, r):
        if not r:
            return
        key, arg = (r if isinstance(r, tuple) else (r, None))
        t = TXT["m"][key]
        self.msg.config(text=t.format(arg) if arg is not None else t)

    def num(self, e):
        try:
            return float(e.get())
        except ValueError:
            return None

    def chosen(self):
        try:
            return int(self.sel.get().split()[0][1:])
        except (ValueError, IndexError):
            return None

    def do_cut(self):
        w, L = self.num(self.w), self.num(self.L)
        if w is None or L is None:
            return self.say("badnum")
        try:
            g = int(self.glove.get().split()[1]) - 1
        except (ValueError, IndexError):
            return self.say("noroom")
        self.say(self.lab.cut(g, w, L))
        self.tab.set("paper"); self.refresh()

    def do_mark(self):
        s = self.lab.strip(self.chosen())
        if not s:
            return self.say("pick")
        if s["in"]:
            return self.say("inchain")
        if s["rolled"]:
            return self.say("rolled")
        if s["marks"]:
            return self.say("remark")
        l0 = self.num(self.l0)
        if l0 is None or l0 < 5:
            return self.say("badnum")
        if l0 > s["L"] - 2 * END - 2:
            return self.say("badl0")
        m1 = (s["L"] - l0) / 2 + random.gauss(0, 0.3)
        s["marks"] = [m1, m1 + l0 + random.gauss(0, 0.3)]
        self.say(("marked", s["n"])); self.refresh()

    def do_toss(self):
        s = self.lab.strip(self.chosen())
        if not s:
            return self.say("pick")
        if s["in"]:
            return self.say("inchain")
        s["broken"] = True
        self.say(("tossed", s["n"])); self.refresh()

    def do_join(self, rolled):
        s = self.lab.strip(self.chosen())
        if not s:
            return self.say("pick")
        if s["in"]:
            return self.say("inchain")
        if rolled:
            s["rolled"] = True
        s["in"] = True
        s["ebeff"] = s["eb"] * (random.uniform(0.72, 0.85) if (not s["rolled"] and s["d0"] > 5) else 1)
        self.lab.chain.append(s["n"])
        self.lab.xe = self.lab.natural_end()
        self.say(("chained", s["n"])); self.tab.set("tape"); self.refresh()

    def do_unchain(self):
        if not self.lab.chain:
            return self.say("nochain")
        for n in self.lab.chain:
            self.lab.strip(n)["in"] = False
        self.lab.chain, self.lab.xe, self.slow = [], None, False
        self.say("unchained"); self.refresh()

    def do_pull(self, dx):
        self.say(self.lab.pull(dx)); self.refresh()

    def do_release(self):
        if not self.lab.chain:
            return self.say("nochain")
        self.lab.xe = self.lab.natural_end(); self.slow = False
        self.say("released"); self.refresh()

    def toggle_slow(self):
        self.slow = not self.slow and bool(self.lab.chain)
        self.slowb.config(text=TXT["stop"] if self.slow else TXT["slow"])

    def tick(self):
        if self.slow and self.lab.chain:
            self.say(self.lab.pull(1)); self.refresh()
        elif self.slow:
            self.toggle_slow()
        self.after(100, self.tick)

    def refresh(self):
        try:
            g0 = int(self.glove.get().split()[1]) - 1
        except (ValueError, IndexError):
            g0 = 0
        opts = [(i, TXT["left"](i, int(l))) for i, l in enumerate(self.lab.left) if l >= 3]
        self.glove["values"] = [o[1] for o in opts]
        keep = [o[1] for o in opts if o[0] == g0]
        if keep:
            self.glove.set(keep[0])
        elif opts:
            self.glove.current(0)
        live = [s for s in self.lab.strips if not s["broken"]]
        cur = self.sel.get()
        self.sel["values"] = [TXT["stripopt"](s) for s in live] or [TXT["none"]]
        vals = list(self.sel["values"])
        keep = [v for v in vals if cur and v.split()[0] == cur.split()[0]]
        self.sel.set(keep[0] if keep else vals[-1])
        self.chainlbl.config(text=(TXT["head"] + " — ".join(f"#{n}" + ("(R)" if self.lab.strip(n)["rolled"] else "") for n in self.lab.chain)) if self.lab.chain else TXT["empty"])
        self.draw()

    # ── the two views ──────────────────────────────────────────────────
    def scale(self):
        W, H = self.cv.winfo_width(), self.cv.winfo_height()
        z, cx, cy = self.view[self.tab.get()]
        base = min(W / 200, H / 110) if self.tab.get() == "paper" else W / 1000
        return base * z, cx, cy, W, H

    def draw(self):
        c = self.cv
        c.delete("all")
        if self.tab.get() == "paper":
            self.draw_paper()
        else:
            self.draw_tape()

    def draw_paper(self):
        c = self.cv
        s, cx, cy, W, H = self.scale()
        c.configure(bg="#fbfaf2")
        ox, oy = W / 2 - (100 + cx) * s, H / 2 - (55 + cy) * s
        X, Y = (lambda u: ox + u * s), (lambda v: oy + v * s)
        for u in range(int(-ox / s) - 1, int((W - ox) / s) + 2):
            c.create_line(X(u), 0, X(u), H, fill="#e09a70" if u % 10 == 0 else "#f0c8b0" if u % 5 == 0 else "#f8e4d8")
        for v in range(int(-oy / s) - 1, int((H - oy) / s) + 2):
            c.create_line(0, Y(v), W, Y(v), fill="#e09a70" if v % 10 == 0 else "#f0c8b0" if v % 5 == 0 else "#f8e4d8")
        for st in self.lab.strips:
            if st["in"] or st["broken"]:
                continue
            e = lambda u, k: 0.12 * math.sin(u / 7 + st["ph"][k]) + 0.07 * math.sin(u / 2.3 + 2 * st["ph"][k])
            if st["rolled"]:
                r = max(1.2, math.sqrt(st["d0"] * st["a0"]) * 0.9)
                c.create_rectangle(X(st["px"]), Y(st["py"] + st["d0"] / 2 - r / 2), X(st["px"] + st["L"]), Y(st["py"] + st["d0"] / 2 + r / 2), fill="#e8d6b8", outline="#78644a")
            else:
                pts = []
                for u in range(0, st["L"] + 1):
                    pts += [X(st["px"] + u), Y(st["py"] + e(u, 0))]
                for u in range(st["L"], -1, -1):
                    pts += [X(st["px"] + u), Y(st["py"] + st["d0"] + e(u, 1))]
                c.create_polygon(pts, fill="#efe2c8", outline="#8c7350", stipple="gray50")
            if st["marks"]:
                for m in st["marks"]:
                    c.create_line(X(st["px"] + m), Y(st["py"] - 0.2), X(st["px"] + m), Y(st["py"] + st["d0"] + 0.2), fill="#1b1d20", width=max(1, s * 0.45))
            c.create_text(X(st["px"]) - 4, Y(st["py"] + st["d0"] / 2), text=f"#{st['n']}", anchor="e", fill="#5a3a1a")

    def draw_tape(self):
        c = self.cv
        s, cx, cy, W, H = self.scale()
        c.configure(bg="#d6d3c8")
        ox, yT = W / 2 - (490 + cx) * s, H * 0.62 - cy * s
        X = lambda r: ox + r * s
        o = self.lab.tape_off
        c.create_rectangle(X(1000), 0, W, H, fill="#b9b4a6", outline="")
        c.create_rectangle(X(o - 5), yT - 9.5 * s, X(o + 960), yT + 9.5 * s, fill="#f2d23c", outline="#a08a1c")
        c.create_rectangle(X(o - 75), yT - 25 * s, X(o - 5), yT + 25 * s, fill="#2b2e33", outline="")
        step = 1 if s >= 3 else 2 if s >= 1.2 else 5 if s >= 0.5 else 10
        for mm in range(0, 961, step):
            x = X(o + mm)
            if x < -2 or x > W + 2:
                continue
            Lm = 9 if mm % 100 == 0 else 6 if mm % 10 == 0 else 4.2 if mm % 5 == 0 else 2.8
            c.create_line(x, yT - 9.5 * s, x, yT - 9.5 * s + Lm * s, fill="#1b1d20")
            if mm % 10 == 0 and (s > 0.9 or mm % 50 == 0):
                c.create_text(x + 1, yT + 3.5 * s, text=str(mm // 10), fill="#c0261c" if mm % 100 == 0 else "#1b1d20")
        st = self.lab.state()
        if not st:
            return
        Yc = yT - 14 * s
        for g in st["seg"]:
            b, lam = g["s"], 1 + g["eps"]
            a1, a2 = X(g["x0"] - END * 0.7), X(g["x1"] + END * 0.7)
            hw = (max(0.8, math.sqrt(b["d0"] * b["a0"] / lam) * 0.9) if b["rolled"] else b["d0"] / math.sqrt(lam)) * s / 2
            c.create_rectangle(a1, Yc - hw, a2, Yc + hw, fill="#ecdcc0", outline="#8c7350")
            if b["marks"]:
                for m in b["marks"]:
                    xm = X(on_tape(g, m))
                    hh = max(4 * s, hw + s)
                    c.create_line(xm, Yc - hh, xm, Yc + hh, fill="#1b1d20", width=max(1, s * 0.45))
            c.create_text((a1 + a2) / 2, Yc - hw - 10, text=f"#{b['n']}", fill="#5a3a1a")
        for i in range(len(st["seg"]) - 1):
            c.create_rectangle(X(st["seg"][i]["x1"]), Yc - 4 * s, X(st["seg"][i + 1]["x0"]), Yc + 4 * s, fill="#dce4e8", outline="#8a9096")
        xh = X(self.lab.xe)
        c.create_oval(xh, Yc - 7 * s, xh + 20 * s, Yc + 7 * s, fill="#d9a98a", outline="#9a6a4a")
        c.create_text(W - 10, 14, text=TXT["m"]["taut" if st["taut"] else "slack"], anchor="e", fill="#2a6a2a" if st["taut"] else "#69717a")

    # ── zoom, pan, slide the tape ──────────────────────────────────────
    def wheel(self, e, sign=None):
        v = self.view[self.tab.get()]
        up = (sign or (1 if e.delta > 0 else -1)) > 0
        lo, hi = (1, 14) if self.tab.get() == "paper" else (0.25, 60)
        v[0] = max(lo, min(hi, v[0] * (1.2 if up else 1 / 1.2)))
        self.draw()

    def press(self, e):
        s, cx, cy, W, H = self.scale()
        on_tape_band = self.tab.get() == "tape" and abs(e.y - (H * 0.62 - cy * s)) < max(8, 9.5 * s)
        self.drag = ("tape", e.x, self.lab.tape_off) if on_tape_band else ("pan", e.x, e.y, cx, cy)

    def motion(self, e):
        s = self.scale()[0]
        v = self.view[self.tab.get()]
        if self.drag[0] == "tape":
            self.lab.tape_off = max(-50, min(REACH, self.drag[2] + (e.x - self.drag[1]) / s))
        else:
            v[1] = self.drag[3] - (e.x - self.drag[1]) / s
            v[2] = self.drag[4] - (e.y - self.drag[2]) / s
        self.draw()

    def reset(self, e):
        self.view[self.tab.get()] = [1.0, 0.0, 0.0]
        self.draw()


if __name__ == "__main__":
    App().mainloop()
