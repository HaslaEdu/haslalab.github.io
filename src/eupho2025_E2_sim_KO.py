#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  9th European Physics Olympiad  (EuPhO 2025, Sofia, Bulgaria)
  Experimental Problem 2 :  HIDDEN PATTERN   (tasks a - d)
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rules
------------
* The foil carries sinusoids y = A sin(k(x - x0)) (k = 2 pi / Lambda),
  repeated every d vertically and printed as staircases of horizontal
  segments with vertical pitch s.  Where the beam crosses the foil the
  lines are a grating tilted by theta, tan(theta) = A k cos(k(x - x0)):
  the primary maxima lie on a line perpendicular to the lines,
  R_n = L tan(asin(n lambda / (d cos theta))), and the staircase edges,
  g = s / |tan theta| apart, give a weak horizontal secondary pattern.
* The laser diode's end cap sets where the beam is focused; the spots
  on the screen grow when it is out of focus.  Its aim is slightly off
  the goniometer's centre.
* Shown are only what the instruments show: the goniometer (1-mm radial
  circles, 1-degree lines) with the spots and pencil dots, the diagonal
  scale under the side of the foil's stand, and the measuring tape at the
  screen.  Lambda, d, A, s, x0 and the exact wavelength are randomised for
  every session and never displayed (--seed N repeats a session).

    Run:   python3 eupho2025_E2_sim_KO.py   [--seed N] [--lang ko|en]
"""

import math
import random
import sys
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


# --------------------------------------------------------------------------
#  The hidden truth of this session  (mm, um, nm)
# --------------------------------------------------------------------------
class Truth(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.r = r
        self.Lam = r.uniform(58, 64)
        self.d = r.uniform(57.5, 62.5)
        self.A = r.uniform(4.6, 5.4)
        self.s = r.uniform(8.5, 11.5)
        self.lam = r.uniform(650, 658)
        self.x0 = r.uniform(8, 40)
        self.off = (r.gauss(0, 1.2), r.gauss(0, 1.2))
        self.tilt = (r.gauss(0, 0.0015), r.gauss(0, 0.0015))


class Bench(object):
    LAS_TO_FOIL = 8.0          # cm

    def __init__(self, seed=None):
        self.t = Truth(seed)
        r = self.t.r
        self.las = False
        self.focus = r.uniform(22, 45)      # cm from the laser
        self.p = r.uniform(15, 65)          # stand edge on the diagonal scale, mm
        self.L = 55.0                       # foil to screen, cm
        self.marks = []

    def theta(self):
        k = 2 * math.pi / self.t.Lam
        return math.atan(self.t.A * k * math.cos(k * (self.p - self.t.x0)))

    def spot_r(self):
        D = self.L + self.LAS_TO_FOIL
        return 0.35 + 1.4 * abs(D - self.focus) / self.focus

    def spots(self):
        t, Lm = self.t, self.L * 10
        o = (t.off[0] + Lm * t.tilt[0], t.off[1] + Lm * t.tilt[1])
        out = [(o[0], o[1], 1.0)]
        th = self.theta()
        lam, dd = t.lam * 1e-6, t.d * 1e-3
        u = (-math.sin(th), math.cos(th))
        for n in range(1, 9):
            a = n * lam / (dd * math.cos(th))
            if a >= 0.5:
                break
            R = Lm * math.tan(math.asin(a))
            I = 0.62 * math.exp(-0.22 * n) * (1 + 0.2 * math.cos(1.7 * n))
            out.append((o[0] + u[0] * R, o[1] + u[1] * R, I))
            out.append((o[0] - u[0] * R, o[1] - u[1] * R, I))
        tt = abs(math.tan(th))
        for m in (1, 2):
            a = m * lam * tt / (t.s * 1e-3)
            if a >= 0.6:
                break
            X = Lm * math.tan(math.asin(a))
            I = 0.16 * math.exp(-0.7 * (m - 1))
            out.append((o[0] + X, o[1], I))
            out.append((o[0] - X, o[1], I))
        return out


def red(I):
    """a spot colour on white paper for intensity I"""
    q = math.sqrt(max(0.0, min(1.0, I)))
    g = int(235 - 215 * q)
    return "#%02x%02x%02x" % (255, g, g)


class App(tk.Tk):
    W, H = 900, 560

    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.b = Bench(seed)
        self.title(T("EuPhO 2025 실험 2 — 숨은 무늬 · HaslaLab", "EuPhO 2025 Experiment 2 — Hidden Pattern · HaslaLab"))
        self.geometry("1360x820")
        self.z = self.H / 236.0
        self.c = [0.0, 0.0]
        self.pan = None
        self.rows = 0
        self.msg = ""

        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=4)
        ttk.Label(top, text=T("EuPhO 2025 실험 2 — 숨은 무늬", "EuPhO 2025 Experiment 2 — Hidden Pattern"),
                  font=("Helvetica", 13, "bold")).pack(anchor="w")
        ttk.Label(top, wraplength=1320, text=T(
            "필름에는 진폭 A, 주기 Λ인 사인 곡선이 세로로 d씩 어긋나 겹쳐 있고, 각 곡선은 세로 간격 s인 계단입니다. "
            "λ = (654 ± 5) nm 레이저를 비추고 스크린의 각도기(1 mm 원, 1° 선)에서 회절 무늬를 읽으세요. "
            "필름 받침은 자 모서리를 따라 밀고 위치는 사선 눈금자로 0.1 mm까지 읽습니다. 계산은 대신 해주지 않습니다.",
            "The foil carries sinusoids of amplitude A and period Λ, shifted by d vertically; each is a staircase of pitch s. "
            "Shine the λ = (654 ± 5) nm laser through it and read the diffraction pattern on the goniometer (1-mm circles, "
            "1° lines) on the screen. Slide the foil's stand along the ruler and read its position to 0.1 mm on the diagonal "
            "scale. No calculation is done for you.")).pack(anchor="w")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=8, pady=4)
        nb = ttk.Notebook(body)
        nb.pack(side="left", anchor="n")
        self.cs = tk.Canvas(nb, width=self.W, height=self.H, bg="#e7d3ad", highlightthickness=0)
        self.cd = tk.Canvas(nb, width=self.W, height=self.H, bg="#e9e7e0", highlightthickness=0)
        self.ct = tk.Canvas(nb, width=self.W, height=self.H, bg="#2a2d33", highlightthickness=0)
        nb.add(self.cs, text=T(" 스크린 (각도기) ", " Screen (goniometer) "))
        nb.add(self.cd, text=T(" 사선 눈금자 ", " Diagonal scale "))
        nb.add(self.ct, text=T(" 위에서 본 배치 ", " Layout from above "))

        side = ttk.Frame(body)
        side.pack(side="left", fill="both", expand=True, padx=10)
        ttk.Label(side, text=T("레이저", "Laser"), font=("Helvetica", 11, "bold")).pack(anchor="w")
        row = ttk.Frame(side)
        row.pack(anchor="w")
        self.lb = ttk.Button(row, text="", command=self.toggle)
        self.lb.pack(side="left", padx=1)
        ttk.Button(row, text="⟲", width=4, command=lambda: self.refocus(1 / 1.08)).pack(side="left", padx=1)
        ttk.Button(row, text="⟳", width=4, command=lambda: self.refocus(1.08)).pack(side="left", padx=1)
        ttk.Label(row, text=T("끝 캡 돌리기 (초점)", "turn the end cap (focus)")).pack(side="left", padx=4)

        ttk.Label(side, text=T("필름 받침 밀기 (자 모서리를 따라)", "Slide the foil's stand (along the ruler)"),
                  font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(8, 0))
        row = ttk.Frame(side)
        row.pack(anchor="w")
        for dv, lab in ((-1, "−1 mm"), (-0.1, "−0.1"), (0.1, "+0.1"), (1, "+1 mm")):
            ttk.Button(row, text=lab, width=7, command=lambda dv=dv: self.slide(dv)).pack(side="left", padx=1)
        ttk.Label(side, text=T("스크린(상자) 옮기기", "Move the screen (the box)"),
                  font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(8, 0))
        row = ttk.Frame(side)
        row.pack(anchor="w")
        for dv, lab in ((-5, "−5 cm"), (-1, "−1"), (1, "+1"), (5, "+5 cm")):
            ttk.Button(row, text=lab, width=7, command=lambda dv=dv: self.move(dv)).pack(side="left", padx=1)

        ttk.Label(side, text=T("연필 표시", "Pencil marks"), font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(8, 0))
        row = ttk.Frame(side)
        row.pack(anchor="w")
        ttk.Button(row, text=T("마지막 표시 지우기", "Rub out the last mark"), command=self.unmark).pack(side="left", padx=1)
        ttk.Button(row, text=T("표시 모두 지우기", "Rub out all marks"), command=self.clear_marks).pack(side="left", padx=1)

        ttk.Label(side, text=T("실험 노트", "Notebook"), font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(8, 0))
        self.cfg = ttk.Entry(side, width=44)
        self.cfg.pack(anchor="w")
        row = ttk.Frame(side)
        row.pack(anchor="w")
        ttk.Button(row, text=T("적기", "Write"), command=self.note).pack(side="left", padx=1)
        ttk.Button(row, text=T("지우기", "Clear"), command=lambda: self.notes.delete("1.0", "end")).pack(side="left", padx=1)
        self.notes = tk.Text(side, height=10, width=44, font=("Courier", 10))
        self.notes.pack(anchor="w")
        self.status = ttk.Label(side, text="", foreground="#8a1b1b", wraplength=420)
        self.status.pack(anchor="w", pady=4)

        cs = self.cs
        cs.bind("<ButtonPress-1>", self.s_down)
        cs.bind("<B1-Motion>", self.s_move)
        cs.bind("<ButtonRelease-1>", self.s_up)
        cs.bind("<ButtonPress-3>", self.s_right)
        cs.bind("<MouseWheel>", lambda e: self.s_zoom(e, 1 if e.delta > 0 else -1))
        cs.bind("<Button-4>", lambda e: self.s_zoom(e, 1))
        cs.bind("<Button-5>", lambda e: self.s_zoom(e, -1))
        for c in (self.cd, self.ct):
            c.bind("<MouseWheel>", lambda e: self.slide(0.1 if e.delta > 0 else -0.1))
            c.bind("<Button-4>", lambda e: self.slide(0.1))
            c.bind("<Button-5>", lambda e: self.slide(-0.1))
        self.redraw()

    # -- the screen --
    def px(self, X, Y):
        return self.W / 2 + (X - self.c[0]) * self.z, self.H / 2 - (Y - self.c[1]) * self.z

    def mm(self, x, y):
        return (x - self.W / 2) / self.z + self.c[0], -(y - self.H / 2) / self.z + self.c[1]

    def draw_screen(self):
        cv, z, b = self.cs, self.z, self.b
        cv.delete("all")
        x0, y0 = self.px(-100, 100)
        x1, y1 = self.px(100, -100)
        cv.create_rectangle(x0, y0, x1, y1, fill="#fbfbf7", outline="")
        cx, cy = self.px(0, 0)
        step = 1 if z >= 3.2 else (5 if z >= 1.2 else 10)
        for r in range(step, 96, step):
            col = "#555" if r % 10 == 0 else ("#999" if r % 5 == 0 else "#cfcfcf")
            cv.create_oval(cx - r * z, cy - r * z, cx + r * z, cy + r * z, outline=col)
        for g in range(360):
            major, mid = g % 10 == 0, g % 5 == 0
            if not mid and z < 3.5:
                continue
            r0 = 10 if major else (30 if mid else 50)
            s, c = math.sin(math.radians(g)), math.cos(math.radians(g))
            p0, p1 = self.px(r0 * s, r0 * c), self.px(95 * s, 95 * c)
            cv.create_line(p0[0], p0[1], p1[0], p1[1], fill="#666" if major else "#c4c4c4")
            if major:
                q = self.px(98 * s, 98 * c)
                cv.create_text(q[0], q[1], text=str(g), font=("Helvetica", max(7, min(11, int(2.4 * z)))), fill="#222")
        for r in range(10, 91, 10):
            q = self.px(r + 1.2, -2.2)
            cv.create_text(q[0], q[1], text=str(r), anchor="w", font=("Helvetica", max(7, min(10, int(2 * z)))), fill="#444")
        if b.las:
            rr = b.spot_r()
            for X, Y, I in b.spots():
                p = self.px(X, Y)
                R = max(2.4, rr * z * (0.75 + 0.5 * math.sqrt(I)))
                cv.create_oval(p[0] - 2.2 * R, p[1] - 2.2 * R, p[0] + 2.2 * R, p[1] + 2.2 * R, fill=red(0.18 * I), outline="")
                cv.create_oval(p[0] - R, p[1] - R, p[0] + R, p[1] + R, fill=red(0.3 + 0.7 * I), outline="")
        for X, Y in b.marks:
            p = self.px(X, Y)
            r = max(1.5, 0.35 * z)
            cv.create_oval(p[0] - r, p[1] - r, p[0] + r, p[1] + r, fill="#4a4a4a", outline="")

    def s_down(self, e):
        self.pan = (e.x, e.y, self.c[:], False)

    def s_move(self, e):
        if not self.pan:
            return
        x, y, c, moved = self.pan
        if math.hypot(e.x - x, e.y - y) > 4:
            moved = True
        self.pan = (x, y, c, moved)
        self.c = [c[0] - (e.x - x) / self.z, c[1] + (e.y - y) / self.z]
        self.draw_screen()

    def s_up(self, e):
        if self.pan and not self.pan[3]:
            self.b.marks.append(self.mm(e.x, e.y))
            self.msg = T("연필로 점을 찍었습니다.", "Pencil dot made.")
        self.pan = None
        self.redraw()

    def s_right(self, e):
        m = self.mm(e.x, e.y)
        best, bd = -1, 12 / self.z
        for i, q in enumerate(self.b.marks):
            dd = math.hypot(q[0] - m[0], q[1] - m[1])
            if dd < bd:
                best, bd = i, dd
        if best >= 0:
            del self.b.marks[best]
            self.msg = T("점을 지웠습니다.", "Dot rubbed out.")
        self.redraw()

    def s_zoom(self, e, sgn):
        m = self.mm(e.x, e.y)
        self.z = max(0.8, min(40, self.z * (1.15 if sgn > 0 else 1 / 1.15)))
        q = self.mm(e.x, e.y)
        self.c = [self.c[0] + m[0] - q[0], self.c[1] + m[1] - q[1]]
        self.draw_screen()

    # -- the diagonal scale --
    def draw_scale(self):
        cv, b = self.cd, self.b
        cv.delete("all")
        k = self.W / 10.0
        x0 = self.W / 2 - b.p * k
        X = lambda v: x0 + v * k
        ya, yb = self.H * 0.16, self.H * 0.78
        ry = lambda r: yb - (yb - ya) * r / 10.0
        cv.create_rectangle(X(0) - 20, ya - 30, X(80) + 20, yb + 40, fill="#f7f6ef", outline="")
        for r in range(11):
            cv.create_line(max(0, X(0)), ry(r), min(self.W, X(80)), ry(r), fill="#333", width=2 if r % 5 == 0 else 1)
            cv.create_text(max(8, X(0) - 12), ry(r), text=str(r), font=("Helvetica", 9))
        for i in range(max(0, int(b.p) - 6), min(80, int(b.p) + 7) + 1):
            cv.create_line(X(i), ya, X(i), yb + (14 if i % 5 == 0 else 8), fill="#333", width=2 if i % 10 == 0 else 1)
            cv.create_text(X(i), yb + 26, text=str(i), font=("Helvetica", 11 if i % 5 == 0 else 9, "bold" if i % 5 == 0 else "normal"))
            if i < 80:
                cv.create_line(X(i), yb, X(i + 1), ya, fill="#444")
        cv.create_rectangle(0, yb + 52, self.W, self.H, fill="#d4e2ea", outline="#8aa")
        e = X(b.p)
        cv.create_rectangle(e, ya - 40, self.W, yb + 52, fill="#8b9198", outline="")
        cv.create_line(e, ya - 40, e, yb + 52, fill="#2a2d31", width=2)
        cv.create_text(e + 12, ya - 24, anchor="w", text=T("필름 받침", "foil stand"), font=("Helvetica", 11, "bold"))

    # -- the layout from above, with the tape --
    def draw_top(self):
        cv, b = self.ct, self.b
        cv.delete("all")
        k = (self.W - 40) / 122.0
        X = lambda x: 20 + x * k
        Y = lambda y: self.H * 0.55 + (y - 30) * k
        cv.create_rectangle(X(0), Y(0), X(122), Y(72), fill="#e9eaec", outline="")
        fx = 14.0
        face = fx + b.L
        ye = 31 + (b.p - 40) / 10.0
        cv.create_rectangle(X(fx - 6), Y(ye), X(fx + 0.3), Y(ye + 8), fill="#a3a9b0", outline="#555")
        cv.create_rectangle(X(fx + 0.3), Y(ye - 6), X(fx + 0.6), Y(ye + 3), fill="#cfcfbf", outline="")
        cv.create_rectangle(X(0.5), Y(29.4), X(6.3), Y(30.6), fill="#2b2e33", outline="")
        cv.create_rectangle(X(fx - 7.5), Y(18), X(fx - 4.5), Y(48), fill="#c8dce6", outline="")
        cv.create_rectangle(X(face), Y(10), X(face + 12), Y(50), fill="#c9a46a", outline="#7a5f33", width=2)
        cv.create_rectangle(X(fx), Y(18.4), X(face), Y(19.1), fill="#f4d641", outline="")
        if b.las:
            cv.create_line(X(6.3), Y(30), X(face), Y(30), fill="#ff3333", width=2)
        W, H = 360, 92
        bx, by = self.W - W - 14, 12
        cv.create_rectangle(bx, by, bx + W, by + H, fill="#15181d", outline="#555")
        cv.create_text(bx + 8, by + 12, anchor="w", text=T("줄자 (스크린 쪽 끝)", "measuring tape (screen end)"),
                       fill="#c9ced3", font=("Helvetica", 10, "bold"))
        cv.create_rectangle(bx + 4, by + 30, bx + W - 4, by + 70, fill="#f4d641", outline="")
        mmpx = W / 50.0
        c = b.L * 10
        fxp = bx + W / 2 - W * 0.1
        for v in range(int(c - 26), int(c + 27)):
            x = fxp + (v - c) * mmpx
            if x < bx + 4 or x > bx + W - 4:
                continue
            L0 = 18 if v % 10 == 0 else (12 if v % 5 == 0 else 7)
            cv.create_line(x, by + 30, x, by + 30 + L0, fill="#111", width=2 if v % 10 == 0 else 1)
            if v % 10 == 0:
                cv.create_text(x, by + 60, text=str(v // 10), font=("Helvetica", 10, "bold"))
        cv.create_rectangle(fxp, by + 22, bx + W - 4, by + H - 4, fill="#c9a46a", outline="")
        cv.create_line(fxp, by + 22, fxp, by + H - 4, fill="#7a5f33", width=2)

    def redraw(self):
        self.draw_screen()
        self.draw_scale()
        self.draw_top()
        b = self.b
        self.lb.config(text=T("레이저 끄기", "Laser off") if b.las else T("레이저 켜기", "Laser on"))
        st = []
        if b.las and b.spot_r() > 1.6:
            st.append(T("스크린 위 점이 퍼져 있습니다 — 끝 캡을 돌려 초점을 맞추세요.",
                        "The dots on the screen are spread out: turn the end cap to focus."))
        if b.L < 40:
            st.append(T("스크린이 너무 가깝습니다 — 멀수록 정밀합니다.", "The screen is close: the farther, the more precise."))
        if self.msg:
            st.append("• " + self.msg)
        self.status.config(text="\n".join(st))

    # -- hands --
    def toggle(self):
        self.b.las = not self.b.las
        self.redraw()

    def refocus(self, f):
        self.b.focus = max(8, min(300, self.b.focus * f))
        self.redraw()

    def slide(self, dmm):
        b = self.b
        np_ = b.p + dmm + b.t.r.gauss(0, 0.015)
        if np_ < 0 or np_ > 80:
            self.msg = T("받침이 눈금자 끝에 닿았습니다.", "The stand is at the end of the scale.")
        b.p = max(0.0, min(80.0, round(np_, 2)))
        self.redraw()

    def move(self, dcm):
        b = self.b
        nl = round(b.L + dcm, 1)
        if nl < 15 or nl > 94:
            self.msg = T("책상 끝입니다.", "That is the edge of the desk.")
        b.L = max(15.0, min(94.0, nl))
        self.redraw()

    def unmark(self):
        if self.b.marks:
            self.b.marks.pop()
        self.redraw()

    def clear_marks(self):
        self.b.marks = []
        self.redraw()

    def note(self):
        self.rows += 1
        self.notes.insert("end", "%d)  %s\n" % (self.rows, self.cfg.get().strip()))
        self.notes.see("end")


def main():
    global LANG
    seed = None
    args = sys.argv[1:]
    if "--seed" in args:
        seed = int(args[args.index("--seed") + 1])
    if "--lang" in args:
        LANG = args[args.index("--lang") + 1].lower()
    App(seed).mainloop()


if __name__ == "__main__":
    main()
