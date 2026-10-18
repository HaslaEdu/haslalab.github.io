#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  3rd Asian Physics Olympiad  (APhO 2002, Singapore)
  Experimental Problem, Part B :  FREQUENCY OF VIBRATION OF A TUNING FORK
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The loaded fork rings at f = 1/sqrt(A (m + B)) with hidden A and B; the
  unknown pair X is hidden too.  A clamp's lever left on adds its mass;
  unequal prongs make the fork die away at once.
* The stroboscope's flashes are simulated one by one: each catches the
  prongs where they are, and the eye keeps each image about 0.1 s, so
  y = (q/p) f shows q stationary images and a slightly wrong rate makes
  them drift.  Room light or the torch smear the prongs into a band.
* Hidden truths are randomised every session.
* Standard library only (tkinter).

    Run:   python3 apho2002_E2_sim_KO.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line


# --------------------------------------------------------------------------
#  Physics core  (g, s, Hz)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.A = r.uniform(5.2, 6.2) * 1e-6
        self.B = r.uniform(9.0, 12.0)
        self.X = r.uniform(11.0, 15.5)
        self.lever = r.uniform(1.1, 1.4)
        self.cal = r.uniform(-0.0015, 0.0015)
        self.tau = r.uniform(18, 26)
        self.masses = {"5 g": 5.0, "10 g": 10.0, "15 g": 15.0, "20 g": 20.0, "25 g": 25.0, "X": self.X, "31.6 g": 31.6}


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_fork(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 30 * s, y + 30 * s, x + 30 * s, y + 40 * s, fill="#3b4047", outline="")
    cv.create_rectangle(x - 3 * s, y, x + 3 * s, y + 30 * s, fill="#b9bfc4", outline="")
    for dx in (-12, 8):
        cv.create_rectangle(x + dx * s, y - 50 * s, x + (dx + 4) * s, y, fill="#c9ced3", outline="#888")
    cv.create_rectangle(x - 12 * s, y - 4 * s, x + 12 * s, y, fill="#c9ced3", outline="")


def art_strobe(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 40 * s, y - 26 * s, x + 40 * s, y + 26 * s, fill="#2b2e33", outline="#111")
    cv.create_oval(x - 48 * s, y - 14 * s, x - 24 * s, y + 10 * s, fill="#c9ced3", outline="")
    cv.create_rectangle(x - 10 * s, y - 16 * s, x + 30 * s, y - 2 * s, fill="#300d0d", outline="")


def art_masses(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 50 * s, y - 16 * s, x + 50 * s, y + 16 * s, fill="#caa06c", outline="#8a6a40")
    for i in range(6):
        cv.create_oval(x - 44 * s + i * 15 * s, y - 6 * s, x - 34 * s + i * 15 * s, y + 4 * s, fill="#c8a24c", outline="")


def art_torch(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 40 * s, y - 7 * s, x + 30 * s, y + 7 * s, fill="#1b1d20", outline="#555")
    cv.create_oval(x + 26 * s, y - 9 * s, x + 40 * s, y + 9 * s, fill="#fff4c8", outline="")


ART = {"fork": art_fork, "strobe": art_strobe, "masses": art_masses, "torch": art_torch}

PARTS = [
    ("fork",   ("[3] 소리굽쇠 (31.6 g씩 물림)", "[3] Tuning fork (31.6 g on each prong)"), []),
    ("strobe", ("[1] 스트로보스코프 (디지털)", "[1] Stroboscope (digital)"), []),
    ("masses", ("[4–6] 집게 2개, 미지 질량 X 쌍, 5–25 g 쌍", "[4-6] 2 clamps, the X pair, 5-25 g pairs"), []),
    ("torch",  ("[2] 작은 손전등", "[2] Mini torch"), []),
]
ZONES = {"fork": (300, 300, 80, 110), "strobe": (500, 290, 100, 60), "masses": (300, 440, 110, 40), "torch": (520, 430, 90, 30)}
SCENE_TITLE = ("실험대 — 소리굽쇠, 스트로보스코프, 질량", "The bench — tuning fork, stroboscope, masses")
APP_TITLE = ("APhO 2002 실험 2 — 소리굽쇠의 진동수", "APhO 2002 Experiment 2 — Frequency of a tuning fork")
MK = ["5 g", "10 g", "15 g", "20 g", "25 g", "X", "31.6 g"]


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.load = {"L": tk.StringVar(value="31.6 g"), "R": tk.StringVar(value="31.6 g")}
        self.lever = {"L": tk.BooleanVar(value=False), "R": tk.BooleanVar(value=False)}
        self.on = tk.BooleanVar(value=False)
        self.room = tk.BooleanVar(value=True)
        self.torch = tk.BooleanVar(value=False)
        self.fl = 65.0
        self.amp, self.phase, self.t, self.next = 0.0, 0.0, 0.0, 0.0
        self.flashes = []
        self.build()
        self.refresh()

    def m(self, s):
        v = self.load[s].get()
        return (self.ph.masses[v] + (self.ph.lever if self.lever[s].get() else 0.0)) if v in self.ph.masses else 0.0

    def f(self):
        return 1 / math.sqrt(self.ph.A * ((self.m("L") + self.m("R")) / 2 + self.ph.B))

    def tau(self):
        return 1.2 if abs(self.m("L") - self.m("R")) > 0.4 else self.ph.tau

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("스트로보스코프", "Stroboscope"))
        f.pack(fill="x", pady=2)
        self.dF = tk.Label(f, text="", font=("Courier", 20, "bold"), bg="#300d0d", fg="#ff5a3a", width=10)
        self.dF.pack(pady=2)
        ttk.Checkbutton(f, text=T("섬광 켜기", "Flash on"), variable=self.on).pack(anchor="w")
        stepper(f, "", [("−10", lambda: self.df(-10)), ("−1", lambda: self.df(-1)), ("−0.1", lambda: self.df(-0.1)), ("−.01", lambda: self.df(-0.01))])
        stepper(f, "", [("+.01", lambda: self.df(0.01)), ("+0.1", lambda: self.df(0.1)), ("+1", lambda: self.df(1)), ("+10", lambda: self.df(10))])
        f = ttk.LabelFrame(ctl, text=T("소리굽쇠 — P점에 물린 질량 (집게 포함)", "Tuning fork — the mass clamped at P (clamp included)"))
        f.pack(fill="x", pady=2)
        for s, lab in (("L", T("왼쪽 가지", "left prong")), ("R", T("오른쪽 가지", "right prong"))):
            row = ttk.Frame(f)
            row.pack(fill="x")
            ttk.Label(row, text=lab, width=10).pack(side="left")
            ttk.Combobox(row, values=[T("없음", "none")] + MK, textvariable=self.load[s], width=8, state="readonly").pack(side="left")
            ttk.Checkbutton(row, text=T("레버 달림", "lever on"), variable=self.lever[s]).pack(side="left", padx=4)
            self.load[s].trace_add("write", lambda *_, s=s: self.loaded(s))
        ttk.Button(f, text=T("고무망치로 치기", "Strike with the mallet"), command=self.strike).pack(fill="x", pady=2)
        f = ttk.LabelFrame(ctl, text=T("방의 빛", "Room light"))
        f.pack(fill="x", pady=2)
        ttk.Checkbutton(f, text=T("방 불 켜짐", "Room lights on"), variable=self.room).pack(side="left")
        ttk.Checkbutton(f, text=T("손전등", "Torch"), variable=self.torch).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.note = ttk.Entry(row, width=18)
        self.note.pack(side="left", padx=2)
        ttk.Button(row, text=T("섬광 진동수 적기", "Record the rate"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("f", T("섬광 (Hz)", "flash (Hz)"), 90), ("n", T("메모", "note"), 200)], height=8)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=360)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("섬광에 비친 두 가지의 끝", "The prong tips in the flashes"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=600, bg="#050608", highlightthickness=0)
        self.cv.pack()

    def df(self, d):
        self.fl = max(5.0, min(300.0, round(self.fl + d, 2)))

    def loaded(self, s):
        """a freshly clamped mass comes with its clamp's lever still on"""
        self.lever[s].set(self.load[s].get() in self.ph.masses)
        self.amp = 0.0

    def strike(self):
        if "fork" in self.app.placed:
            self.amp = 1.0

    def record(self):
        self.sheet.add(("%.1f" % (self.fl * (1 + self.ph.cal)) if self.on.get() else "—", self.note.get()))

    def tick(self, dt):
        f, t0 = self.f(), self.t
        if self.on.get() and "strobe" in self.app.placed:
            if self.next < t0 - 0.2:
                self.next = t0
            while self.next <= t0 + dt:
                ph = self.phase + 2 * math.pi * f * (self.next - t0)
                self.flashes.append((self.next, self.amp * math.sin(ph)))
                self.next += 1.0 / self.fl
        self.t += dt
        self.phase = (self.phase + 2 * math.pi * f * dt) % (2 * math.pi)
        self.amp *= math.exp(-dt / self.tau())
        self.flashes = [q for q in self.flashes if self.t - q[0] < 0.15]
        msgs = []
        if self.amp < 0.08 and "fork" in self.app.placed:
            msgs.append(T("소리굽쇠가 울리지 않습니다 — 치시오.", "The fork is silent: strike it."))
        if self.tau() < 5:
            msgs.append(T("두 가지의 질량이 다릅니다.", "The prongs carry different masses."))
        if self.lever["L"].get() or self.lever["R"].get():
            msgs.append(T("집게 레버가 붙어 있습니다.", "A clamp's lever is still on."))
        self.warn.config(text="\n".join(msgs))
        self.refresh()

    def refresh(self):
        self.dF.config(text=("%.1f Hz" % (self.fl * (1 + self.ph.cal))) if self.on.get() and "strobe" in self.app.placed else "— Hz")
        self.draw()

    def prongs(self, xL, xR, col):
        cv, px, cx, y0 = self.cv, 42.0, 380, 60
        for s, dx, side in ((-1, xL, "L"), (1, xR, "R")):
            x = cx + s * (0.8 + 0.275) * px + dx
            cv.create_rectangle(x - 0.275 * px, y0, x + 0.275 * px, y0 + 7 * px, fill=col, outline="")
            v = self.load[side].get()
            if v in self.ph.masses:
                r = (0.55 + math.sqrt(self.ph.masses[v]) * 0.12) * px
                x0 = x - 0.275 * px - 2 * r if s < 0 else x + 0.275 * px
                cv.create_rectangle(x0, y0 + 4.4 * px, x0 + 2 * r, y0 + 6.2 * px, fill=col, outline="")
            cv.create_line(x - 0.275 * px, y0 + 5.3 * px, x + 0.275 * px, y0 + 5.3 * px, fill="#111")

    def draw(self):
        cv = self.cv
        cv.delete("all")
        lit = 0.55 if self.room.get() else 0.15 if self.torch.get() else 0.0
        cv.config(bg="#4a4f57" if self.room.get() else "#050608")
        if "fork" not in self.app.placed:
            return
        A = 30.0
        if lit > 0:
            for i in range(8):
                x = self.amp * math.sin(i / 8.0 * 2 * math.pi) * A
                g = int(90 + 80 * lit)
                self.prongs(-x, x, "#%02x%02x%02x" % (g, g + 4, g + 8))
        if self.on.get() and "strobe" in self.app.placed:
            seen = []
            for tf, x in self.flashes:
                age = self.t - tf
                if age > 0.12 or any(abs(x - q) < 0.02 for q in seen):
                    continue
                seen.append(x)
                g = int(235 * (0.45 if self.room.get() else 1.0) * math.exp(-age / 0.08)) + 20
                self.prongs(-x * A, x * A, "#%02x%02x%02x" % (g, g, min(255, g + 6)))


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
