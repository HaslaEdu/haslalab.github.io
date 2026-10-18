#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  31st International Physics Olympiad  (IPhO 2000, Leicester, UK)
  Experimental Problem 2 :  THE MAGNETIC PUCK
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The puck (weight 5.84e-2 N) slides down a paper track at angle theta:
  m dv/dt = mg sin(theta) - mu mg cos(theta) - F(v), where F = 0 with
  the light face down and F = k v / (1 + v/v0) (eddy currents) with the
  blue face down.  It does not start below tan(theta) = mu_static.
* Two sensors 0.294 m apart flip a gate; while it is on, a current
  proportional to the battery charges a capacitor: 1 V <-> 0.213 s at
  9.0 V.  The capacitor leaks slowly and cannot pass the battery's
  voltage; the red button (held 10 s) empties it.  The battery runs
  down while the black button is held; below 8.4 V the sensors fail.
* mu, k and the battery are hidden and randomised.  Standard library
  only (tkinter).

    Run:   python3 ipho2000_E2_sim_KO.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line

G, W = 9.81, 5.84e-2
M = W / G
TLEN, S1, S2, PR = 80.0, 35.0, 64.4, 2.0
MODES = {"off": None, "V2": (1.999, 3), "V20": (19.99, 2)}


# --------------------------------------------------------------------------
#  Physics core
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.mu = r.uniform(0.22, 0.30)
        self.muS = self.mu + r.uniform(0.03, 0.06)
        self.k, self.v0 = r.uniform(0.032, 0.042), r.uniform(1.6, 2.4)
        self.vBat0, self.drain = r.uniform(9.25, 9.5), r.uniform(0.0006, 0.0010)
        self.leak, self.sens = r.uniform(700, 1100), r.uniform(0.3, 0.6)

    def mag(self, v, face):
        return 0.0 if face == "light" else self.k * v / (1 + v / self.v0)


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def box_art(col, w, h):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_rectangle(x - w * s, y - h * s, x + w * s, y + h * s, fill=col, outline="#555")
    return art


def art_track(cv, x, y, sc=1.0):
    s = sc
    cv.create_line(x - 60 * s, y - 30 * s, x + 60 * s, y + 30 * s, fill="#8a6a40", width=6)


def art_puck(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 16 * s, y - 6 * s, x + 16 * s, y + 6 * s, fill="#2a5d9f", outline="#555")
    cv.create_oval(x - 16 * s, y - 9 * s, x + 16 * s, y + 3 * s, fill="#f2efe6", outline="#888")


ART = {"track": art_track, "puck": art_puck, "timer": box_art("#3a4a5a", 30, 18), "dmm": box_art("#e3b72d", 18, 28)}
PARTS = [
    ("track", ("경사 트랙 (센서 둘)", "Sloping track (two sensors)"), []),
    ("puck",  ("자석 퍽", "Magnetic puck"), ["track"]),
    ("timer", ("타이머 상자 (9 V 전지)", "Timer box (9 V battery)"), ["track"]),
    ("dmm",   ("멀티미터", "Multimeter"), ["timer"]),
]
ZONES = {"track": (380, 260, 130, 70), "puck": (340, 240, 36, 24), "timer": (560, 420, 64, 40), "dmm": (220, 420, 40, 60)}
SCENE_TITLE = ("경사 트랙 · 퍽 · 타이머 상자 · 멀티미터", "Sloping track · puck · timer box · multimeter")
APP_TITLE = ("IPhO 2000 실험 2 — 자석 퍽", "IPhO 2000 Experiment 2 — The magnetic puck")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.th, self.s, self.v, self.moving = 28.0, 10.0, 0.0, False
        self.face = tk.StringVar(value="light")
        self.power, self.red = tk.BooleanVar(value=False), tk.BooleanVar(value=False)
        self.redT, self.led, self.vc, self.vBat = 0.0, random.random() < 0.5, random.uniform(0.5, 3), self.ph.vBat0
        self.mode, self.conn = tk.StringVar(value="off"), tk.StringVar(value="none")
        self.disp, self.disp_t, self.msg = "", 0.0, ""
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("멀티미터", "Multimeter"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.ml = tk.Label(row, text="", font=("Courier", 14, "bold"), bg="#9fae8f", fg="#1b1d20", width=10)
        self.ml.pack(side="left", padx=2)
        ttk.OptionMenu(row, self.mode, "off", *MODES.keys()).pack(side="left")
        for v, lab in (("none", T("분리", "off")), ("cap", T("축전기", "capacitor")), ("bat", T("전지", "battery"))):
            ttk.Radiobutton(row, text=lab, value=v, variable=self.conn).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("타이머", "Timer"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Checkbutton(row, text=T("검은 버튼 누르고 있기", "Hold the black button"), variable=self.power).pack(side="left")
        ttk.Checkbutton(row, text=T("빨간 버튼 누르고 있기", "Hold the red button"), variable=self.red).pack(side="left", padx=6)
        self.ll = tk.Label(f, text="●", font=("Helvetica", 16, "bold"), fg="#1d3a22")
        self.ll.pack(anchor="w")
        ttk.Button(f, text=T("새 전지", "New battery"), command=self.newbat).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("트랙 · 퍽", "Track · puck"))
        f.pack(fill="x", pady=2)
        stepper(f, T("경사각", "Angle"), [("−1°", lambda: self.ang(-1)), ("−0.1°", lambda: self.ang(-0.1)), ("+0.1°", lambda: self.ang(0.1)), ("+1°", lambda: self.ang(1))])
        stepper(f, T("퍽 위치", "Puck at"), [("−5", lambda: self.mv(-5)), ("−1", lambda: self.mv(-1)), ("−0.1", lambda: self.mv(-0.1)), ("+0.1", lambda: self.mv(0.1)), ("+1", lambda: self.mv(1)), ("+5", lambda: self.mv(5))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Radiobutton(row, text=T("밝은 면 아래", "light face down"), value="light", variable=self.face).pack(side="left")
        ttk.Radiobutton(row, text=T("파란 면 아래", "blue face down"), value="blue", variable=self.face).pack(side="left")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("놓기", "Let go"), command=self.release).pack(side="left")
        ttk.Button(row, text=T("위로 (10 cm)", "Back to 10 cm"), command=self.top).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        ttk.Button(f, text=T("지금 상태와 멀티미터 적기", "Write down the setting and the meter"), command=self.record).pack(anchor="w")
        self.sheet = DataSheet(f, [("a", T("각도", "angle"), 60), ("f", T("면", "face"), 60), ("s", T("출발", "start"), 60), ("m", T("멀티미터", "meter"), 90)], height=5)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=420)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("옆에서 본 트랙과 각도기", "The track from the side, with the inclinometer"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()
        self.start = 10.0

    def ang(self, d):
        if self.has("track") and not self.moving:
            self.th = max(10.0, min(50.0, round(self.th + d, 1)))

    def mv(self, d):
        if self.has("puck") and not self.moving:
            self.s = max(PR, min(TLEN - PR, round(self.s + d, 2)))

    def newbat(self):
        self.vBat = random.uniform(9.25, 9.5)

    def top(self):
        self.moving, self.v, self.s = False, 0.0, 10.0

    def release(self):
        if not self.has("puck") or self.moving:
            return
        if math.tan(math.radians(self.th)) <= self.ph.muS:
            self.msg = T("이 각도에서는 미끄러지지 않습니다.", "At this angle the puck does not slide.")
            return
        self.start, self.v, self.moving, self.msg = self.s, 0.0, True, ""

    def record(self):
        self.sheet.add(("%.1f°" % self.th, T("밝은", "light") if self.face.get() == "light" else T("파란", "blue"), "%.1f" % self.start, self.show()))

    def show(self):
        if not self.has("dmm"):
            return "—"
        if not MODES[self.mode.get()]:
            return "OFF"
        return (self.disp + " V") if self.disp and self.disp != "1" else self.disp

    def tick(self, dt):
        ph = self.ph
        on = self.power.get() and self.has("timer")
        if on:
            self.vBat = max(7.5, self.vBat - ph.drain * dt)
        h = dt
        while h > 0:
            q = min(0.002, h)
            h -= q
            if on and self.led:
                self.vc += q * (self.vBat / 9.0) / 0.213
            self.vc *= math.exp(-q / ph.leak)
            if self.moving:
                th = math.radians(self.th)
                a = G * math.sin(th) - (ph.mu * M * G * math.cos(th) + ph.mag(self.v, self.face.get())) / M
                sp = self.s
                self.v = max(0.0, self.v + a * q)
                self.s += self.v * q * 100
                ok = self.vBat >= 8.4 or random.random() < 0.6
                for S, state in ((S1, True), (S2, False)):
                    if on and ok and sp + PR < S + ph.sens <= self.s + PR:
                        self.led = state
                if self.s >= TLEN - PR:
                    self.s, self.v, self.moving = TLEN - PR, 0.0, False
        if self.red.get():
            self.redT += dt
            if self.redT > 2:
                self.vc *= math.exp(-dt / 1.5)
        else:
            self.redT = 0.0
        self.vc = min(self.vc, self.vBat - 0.6)
        self.disp_t -= dt
        if self.disp_t <= 0:
            self.disp_t = 0.3
            m = MODES[self.mode.get()]
            if not self.has("dmm") or not m or self.conn.get() == "none" or not self.has("timer"):
                self.disp = ""
            else:
                r = self.vc if self.conn.get() == "cap" else self.vBat
                self.disp = "1" if r > m[0] else "%.*f" % (m[1], max(0.0, r + (random.random() - 0.5) * 10 ** (-m[1]) * 0.8))
        w = []
        if self.msg:
            w.append(self.msg)
        if on and self.vBat < 8.4:
            w.append(T("전지가 8.4 V 아래입니다.", "The battery is below 8.4 V."))
        self.warn.config(text="\n".join(w))
        self.refresh()

    def refresh(self):
        self.ml.config(text=self.show())
        self.ll.config(fg="#2fd04f" if self.power.get() and self.led else "#1d3a22")
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        th = math.radians(self.th)
        k = min(680 / (TLEN * math.cos(th) + 10), 560 / (TLEN * math.sin(th) + 10))
        ox, oy = 720, 600
        Q = lambda s, h: (ox - ((TLEN - s) * math.cos(th) - h * math.sin(th)) * k, oy - ((TLEN - s) * math.sin(th) + h * math.cos(th)) * k)
        cv.create_line(20, oy + 4, 750, oy + 4, fill="#333")
        if not self.has("track"):
            return
        pts = [Q(0, 0), Q(TLEN, 0), Q(TLEN, -0.9), Q(0, -0.9)]
        cv.create_polygon(*[v for p in pts for v in p], fill="#e9e2cc", outline="#8a6a40")
        for c in range(0, int(TLEN) + 1):
            a, b = Q(c, 0), Q(c, 1.4 if c % 10 == 0 else (1.0 if c % 5 == 0 else 0.6))
            cv.create_line(a[0], a[1], b[0], b[1], fill="#1b1d20")
            if c % 10 == 0:
                q = Q(c, 2.6)
                cv.create_text(q[0], q[1], text=str(c), font=("Helvetica", 9, "bold"))
        for S in (S1, S2):
            a = Q(S, -1.6)
            cv.create_rectangle(a[0] - 4, a[1] - 4, a[0] + 4, a[1] + 4, fill="#1b1d20", outline="")
        if self.has("puck"):
            a, b, c, e = Q(self.s - PR, 0), Q(self.s + PR, 0), Q(self.s + PR, 0.9), Q(self.s - PR, 0.9)
            light = self.face.get() == "light"
            cv.create_polygon(a[0], a[1], b[0], b[1], c[0], c[1], e[0], e[1], fill="#f2efe6" if light else "#2a5d9f", outline="#333")
            q = Q(self.s, 4)
            cv.create_text(q[0], q[1], text=T("퍽 중심 %.1f cm", "puck centre %.1f cm") % self.s, font=("Helvetica", 9))
        R = 110
        cv.create_arc(ox - R, oy - R, ox + R, oy + R, start=90, extent=90, style="arc", outline="#666")
        for g in range(0, 91):
            a = math.pi + math.radians(g)
            L0 = 12 if g % 10 == 0 else (8 if g % 5 == 0 else 4)
            cv.create_line(ox + R * math.cos(a), oy + R * math.sin(a), ox + (R - L0) * math.cos(a), oy + (R - L0) * math.sin(a), fill="#333")
            if g % 10 == 0:
                cv.create_text(ox + (R - 22) * math.cos(a), oy + (R - 22) * math.sin(a), text=str(g), font=("Helvetica", 7))


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
