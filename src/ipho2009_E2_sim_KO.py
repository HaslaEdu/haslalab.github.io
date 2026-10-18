#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  40th International Physics Olympiad  (IPhO 2009, Merida, Mexico)
  Experimental Problem 2 :  BIREFRINGENCE OF MICA
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The partially polarized laser light passes polarizer 1, the mica and
  polarizer 2 (each polarizer with its (+) or (-) axis vertical) into
  the photodetector, whose volts the multimeter shows.  Everything is
  done with Jones matrices: real polarizers leak a little, and the mica
  absorbs its two axes slightly differently, so the normalized IP, IO
  follow the problem's formulas only approximately - as on the day.
* The mica sits in a cylinder with 100 unnumbered lines; its axis 1 lies
  a fraction of a line away from one of them.
* L (written on the cylinder), |n1 - n2|, the axis offset, the laser's
  polarization and the detector's gain are hidden and randomised;
  |n1 - n2| is chosen so that the problem's 82 um rule holds.
* Standard library only (tkinter).

    Run:   python3 ipho2009_E2_sim_KO.py
"""

import cmath
import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line


# --------------------------------------------------------------------------
#  Physics core
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.lam = r.uniform(645, 672) * 1e-9
        self.L = round(r.uniform(58, 76) if r.random() < 0.5 else r.uniform(88, 108))
        self.dn = self.lam / (2 * 82e-6) * r.uniform(0.985, 1.015)
        self.th0 = r.uniform(-1.7, 1.7)
        self.t1, self.t2 = r.uniform(0.86, 0.90), r.uniform(0.80, 0.85)
        self.psiL, self.pol = r.uniform(0, 180), r.uniform(0.55, 0.8)
        self.tp, self.leak = 0.80, 0.0012
        self.k, self.bg = r.uniform(95, 108), r.uniform(0.25, 0.6)
        self.knob0 = r.uniform(-0.6, 0.6)
        self.rot0 = r.uniform(0, 360)
        self.dphi = 2 * math.pi * self.L * 1e-6 * self.dn / self.lam

    @staticmethod
    def rotate(e, ang, a, b):
        """apply amplitudes a (along ang) and b (across) to the Jones vector e"""
        c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        p, q = e[0] * c + e[1] * s, -e[0] * s + e[1] * c
        p, q = p * a, q * b
        return (p * c - q * s, p * s + q * c)

    def intensity(self, chain, pv, rot):
        q = math.radians(self.psiL)
        states = (((math.cos(q), math.sin(q)), self.pol), ((math.cos(q), math.sin(q)), (1 - self.pol) / 2), ((-math.sin(q), math.cos(q)), (1 - self.pol) / 2))
        I = 0.0
        for e0, w in states:
            e = (complex(e0[0]), complex(e0[1]))
            for k in chain:
                if k == "mica":
                    e = self.rotate(e, 90 + rot + self.th0, math.sqrt(self.t1), math.sqrt(self.t2) * cmath.exp(1j * self.dphi))
                else:
                    e = self.rotate(e, 90 if pv[k] == "+" else 0, math.sqrt(self.tp), math.sqrt(self.leak))
            I += w * (abs(e[0]) ** 2 + abs(e[1]) ** 2)
        return I


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def box_art(col, w, h):
    def art(cv, x, y, sc=1.0):
        s = sc
        cv.create_rectangle(x - w * s, y - h * s, x + w * s, y + h * s, fill=col, outline="#555")
    return art


def art_mica(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 22 * s, y - 22 * s, x + 22 * s, y + 22 * s, fill="#1b1d20", outline="")
    cv.create_oval(x - 13 * s, y - 13 * s, x + 13 * s, y + 13 * s, fill="#e6d7aa", outline="")


ART = {"laser": box_art("#2a2d33", 40, 8), "mirror": box_art("#c9d6de", 15, 15), "pol1": box_art("#4a4d55", 10, 22), "pol2": box_art("#4a4d55", 10, 22),
       "mica": art_mica, "det": box_art("#2a2d33", 16, 12), "dmm": box_art("#e3b72d", 24, 38), "stickers": box_art("#f4f4f0", 16, 10)}
PARTS = [
    ("laser",    ("[A] 다이오드 레이저", "[A] Diode laser"), []),
    ("mirror",   ("[B] 거울 (손잡이 2개)", "[B] Mirror (two knobs)"), []),
    ("pol1",     ("[J1] 편광판 1", "[J1] Polarizer 1"), []),
    ("mica",     ("[K] 운모판 (원통)", "[K] Mica plate (cylinder)"), []),
    ("pol2",     ("[J2] 편광판 2", "[J2] Polarizer 2"), []),
    ("det",      ("[L] 광검출기", "[L] Photodetector"), []),
    ("dmm",      ("[L] 멀티미터", "[L] Multimeter"), []),
    ("stickers", ("스티커", "Stickers"), []),
]
ZONES = {"laser": (150, 160, 90, 30), "mirror": (640, 160, 40, 40), "pol1": (560, 260, 30, 50), "mica": (480, 260, 50, 50), "pol2": (400, 260, 30, 50),
         "det": (300, 260, 40, 40), "dmm": (180, 380, 60, 90), "stickers": (560, 420, 40, 30)}
SCENE_TITLE = ("레이저 → 거울 → 편광판 → 운모 → 편광판 → 광검출기", "Laser → mirror → polarizer → mica → polarizer → photodetector")
APP_TITLE = ("IPhO 2009 실험 2 — 운모의 복굴절", "IPhO 2009 Experiment 2 — Birefringence of mica")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.laser = tk.BooleanVar(value=False)
        self.knob = 0.0
        self.pv = {"pol1": tk.StringVar(value="+"), "pol2": tk.StringVar(value="+")}
        self.use = {k: tk.BooleanVar(value=True) for k in ("pol1", "mica", "pol2")}
        self.rot = self.ph.rot0
        self.sticker = None
        self.rng = tk.StringVar(value="200m")
        self.disp, self.disp_t = 0.0, 0.0
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def on_det(self):
        return abs(self.ph.knob0 + self.knob) < 0.15

    def raw(self):
        if not (self.has("det") and self.has("dmm")) or self.rng.get() == "off":
            return None
        if not (self.laser.get() and self.has("laser") and self.has("mirror") and self.on_det()):
            return self.ph.bg
        chain = [k for k in ("pol1", "mica", "pol2") if self.has(k) and self.use[k].get()]
        pv = {k: v.get() for k, v in self.pv.items()}
        return self.ph.k * self.ph.intensity(chain, pv, self.rot) + self.ph.bg

    def show(self):
        if not self.has("dmm") or self.rng.get() == "off":
            return "—"
        full = 199.9 if self.rng.get() == "200m" else 1999
        v = self.disp
        if v > full:
            return "1"
        return ("%.1f" if full < 200 else "%.0f") % v + " mV"

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("멀티미터 (광검출기)", "Multimeter (photodetector)"))
        f.pack(fill="x", pady=2)
        self.lbl = tk.Label(f, text="", font=("Courier", 18, "bold"), bg="#9fae8f", fg="#1b1d20", width=12)
        self.lbl.pack(anchor="w", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        for md, lab in (("off", "OFF"), ("200m", "200 mV"), ("2000m", "2000 mV")):
            ttk.Radiobutton(row, text=lab, value=md, variable=self.rng).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("레이저 · 거울", "Laser · mirror"))
        f.pack(fill="x", pady=2)
        ttk.Checkbutton(f, text=T("레이저 켜기", "Laser on"), variable=self.laser).pack(anchor="w")
        stepper(f, T("거울 손잡이", "Mirror knob"), [("−0.5°", lambda: self.turn(-0.5)), ("−0.05°", lambda: self.turn(-0.05)), ("+0.05°", lambda: self.turn(0.05)), ("+0.5°", lambda: self.turn(0.5))])
        f = ttk.LabelFrame(ctl, text=T("빔 위의 부품 · 편광판 축", "Parts in the beam · polarizer axes"))
        f.pack(fill="x", pady=2)
        for k, lab in (("pol1", T("편광판 1", "Polarizer 1")), ("mica", T("운모", "Mica")), ("pol2", T("편광판 2", "Polarizer 2"))):
            row = ttk.Frame(f)
            row.pack(fill="x")
            ttk.Checkbutton(row, text=lab, variable=self.use[k]).pack(side="left")
            if k != "mica":
                ttk.Radiobutton(row, text=T("(+) 축 세로", "(+) vertical"), value="+", variable=self.pv[k]).pack(side="left")
                ttk.Radiobutton(row, text=T("(−) 축 세로", "(−) vertical"), value="-", variable=self.pv[k]).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("운모 원통 돌리기 · 스티커", "Turn the mica cylinder · sticker"))
        f.pack(fill="x", pady=2)
        stepper(f, "", [("−3.6°", lambda: self.spin(-3.6)), ("−0.9°", lambda: self.spin(-0.9)), ("−0.18°", lambda: self.spin(-0.18)),
                        ("+0.18°", lambda: self.spin(0.18)), ("+0.9°", lambda: self.spin(0.9)), ("+3.6°", lambda: self.spin(3.6))])
        ttk.Button(f, text=T("기준선 눈금에 스티커", "Sticker on the line at the index"), command=self.stick).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text=T("θ (눈금 칸)", "θ (lines)")).pack(side="left")
        self.eth = ttk.Entry(row, width=6)
        self.eth.pack(side="left", padx=2)
        ttk.Button(row, text="IP", command=lambda: self.record("IP")).pack(side="left")
        ttk.Button(row, text="IO", command=lambda: self.record("IO")).pack(side="left")
        self.sheet = DataSheet(f, [("t", T("θ (칸)", "θ (lines)"), 70), ("w", T("성분", "which"), 60), ("v", T("전압", "volts"), 90)], height=6)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=380)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("빔의 길 · 운모 원통의 눈금 (숫자 없음)", "The beam · the mica cylinder's scale (no numbers)"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()

    def turn(self, d):
        self.knob = round(self.knob + d, 3)

    def spin(self, d):
        self.rot = round(self.rot + d, 3)

    def stick(self):
        if self.has("stickers"):
            self.sticker = round(-self.rot / 3.6) * 3.6

    def record(self, which):
        self.sheet.add((self.eth.get(), which, self.show()))

    def tick(self, dt):
        self.disp_t -= dt
        if self.disp_t <= 0:
            self.disp_t = 0.5
            r = self.raw()
            if r is not None:
                self.disp = r * (1 + (random.random() - 0.5) * 0.004) + (random.random() - 0.5) * 0.12
        msg = ""
        if self.laser.get() and self.has("det") and not self.on_det():
            msg = T("빔이 광검출기에 닿지 않습니다 — 거울 손잡이를 맞추세요.", "The beam misses the photodetector: adjust the mirror's knob.")
        self.warn.config(text=msg)
        self.refresh()

    def refresh(self):
        self.lbl.config(text=self.show())
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        cv.create_rectangle(10, 10, 750, 200, fill="#c99a62", outline="")
        xs = {"pol1": 260, "mica": 380, "pol2": 500, "det": 640}
        y = 105
        if self.laser.get() and self.has("laser"):
            off = (self.ph.knob0 + self.knob) * 120
            cv.create_line(40, y, 700, y + off, fill="red", width=2)
        cv.create_rectangle(20, y - 10, 110, y + 10, fill="#2a2d33", outline="")
        for k, x in xs.items():
            if not self.has(k):
                continue
            if k == "det":
                cv.create_rectangle(x, y - 22, x + 40, y + 22, fill="#2a2d33", outline="")
                cv.create_oval(x - 3, y - 4, x + 5, y + 4, fill="#0d0e10", outline="#888")
            elif k == "mica":
                cv.create_rectangle(x - 18, y - 30, x + 18, y + 30, fill="#1b1d20" if self.use[k].get() else "#777", outline="")
                cv.create_text(x, y + 44, text="%d µm" % self.ph.L, font=("Helvetica", 9, "bold"))
            else:
                cv.create_rectangle(x - 4, y - 34, x + 4, y + 34, fill="#4a4d55" if self.use[k].get() else "#999", outline="")
                cv.create_text(x, y - 44, text="(%s)↕" % ("+" if self.pv[k].get() == "+" else "−"), font=("Helvetica", 10, "bold"))
        # the cylinder's side, unrolled round the index
        cx, y0, h, ppd = 380, 260, 160, 700 / 150.0
        cv.create_rectangle(30, y0, 730, y0 + h, fill="#1b1d20", outline="")
        for i in range(-60, 160):
            ang = (i * 3.6 + self.rot) % 360
            dd = (ang + 540) % 360 - 180
            if abs(dd) <= 75:
                X = cx + dd * ppd
                cv.create_line(X, y0 + h * 0.12, X, y0 + h * 0.55, fill="#e8eef2", width=2)
        if self.sticker is not None:
            dd = ((self.sticker + self.rot) % 360 + 540) % 360 - 180
            if abs(dd) <= 75:
                X = cx + dd * ppd
                cv.create_oval(X - 7, y0 + h * 0.72 - 7, X + 7, y0 + h * 0.72 + 7, fill="#c0392b", outline="")
        cv.create_polygon(cx, y0 - 2, cx - 8, y0 - 16, cx + 8, y0 - 16, fill="#f2c14e")
        cv.create_line(cx, y0 - 2, cx, y0 + h + 6, fill="#f2c14e")
        cv.create_text(cx, y0 - 26, text=T("기준선", "index"), font=("Helvetica", 9))
        cv.create_text(40, y0 + h - 12, anchor="w", text="%d µm" % self.ph.L, fill="#f2c14e", font=("Helvetica", 11, "bold"))


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
