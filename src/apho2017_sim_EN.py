#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  18th Asian Physics Olympiad  (APhO 2017, Yakutsk, Russia)
  Experimental Problem :  PHOTONIC CRYSTAL
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The simulator shows ONLY what the real apparatus shows -- the rainbow
    strip of the diffraction grating seen through the sample, the two
    protractors and the multimeter reading of the photodiode current.
    Periods, refractive indices, porosities, the orders m and the
    structures of the samples are never computed or displayed.
    All hidden true parameters are randomised for every session.

    Physics: the transmittance minimums of each sample follow the
    Bragg-Snell law 2 D sqrt(n^2 - sin^2 theta) = m lambda; the layer
    indices come from the porosities (n^2 = p n_pore^2 + (1-p) n_AAO^2,
    dry or with water in the pores); the depth of the m-th minimum of
    samples Y and Z follows the reflectances I_m/I_0 of their structures
    (appendix of the problem); the two faces add Fresnel losses.

    Run:   python3 apho2017_sim_KO.py   [--seed=N]
"""

import math
import random
import sys
import tkinter as tk
from tkinter import ttk

# --------------------------------------------------------------------------
# language
# --------------------------------------------------------------------------
LANG = "en"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


DEG = math.pi / 180.0
H_GRATING = 1000.0                  # grating period [nm]
N_WATER = 1.33
LASER_NM = {"red": 659.0, "green": 530.0, "blue": 400.0}
STRUCT = {"n-6": [1, 1, 1, 2, 6, 48, 48, 6, 2, 1, 1, 1, 100, 1, 1, 1, 2, 6, 48, 48],
          "hi5-5": [1, 0, 1, 0, 2, 1, 3, 6, 36, 1, 32, 10, 1, 2, 0, 1, 0, 6, 28, 25]}


# ==========================================================================
#  1.  the samples (hidden truth)
# ==========================================================================
class Truth:
    def __init__(self, seed=None):
        self.seed = seed if seed is not None else random.randrange(1, 10 ** 9)
        r = random.Random(self.seed)
        self.rng = r
        self.nA = 1.72 * r.uniform(0.995, 1.005)          # aluminium oxide
        self.p1 = 0.22 * r.uniform(0.93, 1.07)            # porosities of the two layers
        self.p2 = 0.41 * r.uniform(0.95, 1.05)
        self.Dx = 227.0 * r.uniform(0.97, 1.03)           # periods [nm]
        self.Dy = 1105.0 * r.uniform(0.99, 1.01)
        self.Dz = 1802.0 * r.uniform(0.985, 1.015)
        self.zeroR = r.uniform(-0.6, 0.6)                 # protractor zero errors [deg]
        self.zeroL = r.uniform(-0.5, 0.5)
        self.laser_off = r.uniform(-2.2, 2.2)             # laser holder alignment [deg]
        self.I = {"red": 290 * r.uniform(0.9, 1.1), "green": 185 * r.uniform(0.9, 1.1),
                  "blue": 1350 * r.uniform(0.9, 1.1)}   # photocurrent without sample [uA]
        self.dark = r.uniform(0.2, 0.6)
        self.warm = r.uniform(0.10, 0.18)
        self.Gx = r.uniform(2.0, 2.6)
        self.Gyz = r.uniform(7.0, 9.0)

    def layer_n(self, p, wet):
        npore2 = N_WATER ** 2 if wet else 1.0
        return math.sqrt(p * npore2 + (1 - p) * self.nA ** 2)

    def sample_n(self, wet):
        n1, n2 = self.layer_n(self.p1, wet), self.layer_n(self.p2, wet)
        return (n1 + n2) / 2.0, n1 - n2

    def optics(self, s, wet):
        n0, dn0 = self.sample_n(False)
        n1, dn1 = self.sample_n(True)
        n, dn = n0 + (n1 - n0) * wet, dn0 + (dn1 - dn0) * wet
        if s == "X":
            return n, dn, self.Dx, [(1, 100)]
        tab = STRUCT["n-6" if s == "Y" else "hi5-5"]
        return n, dn, (self.Dy if s == "Y" else self.Dz), [(i + 1, v) for i, v in enumerate(tab)]

    def transmit(self, s, lam, th, wet):
        if not s:
            return 1.0
        n, dn, D, dips = self.optics(s, wet)
        c = math.sqrt(n * n - math.sin(th) ** 2)
        scale = (dn / self.sample_n(False)[1]) ** 2
        ci, ct = math.cos(th), c / n
        rs = ((ci - n * ct) / (ci + n * ct)) ** 2
        rp = ((n * ci - ct) / (n * ci + ct)) ** 2
        Tt = ((1 - rs) ** 2 + (1 - rp) ** 2) / 2 * (0.92 - 0.30 * math.exp(-(lam - 380) / 55))
        w0 = 2 / math.pi * abs(dn) / n
        for m, I in dips:
            if I <= 0:
                continue
            lm = 2 * D * c / m
            if lm < 330 or lm > 900:
                continue
            if s == "X":
                t, w = 1 / (1 + self.Gx * scale), w0
            else:
                t, w = 1 / (1 + self.Gyz * scale * (I / 100.0) ** 1.3), max(0.006, w0 * math.sqrt(I / 100.0) * 0.9)
            sg = w * lm / 2.355
            Tt *= 1 - (1 - t) * math.exp(-0.5 * ((lam - lm) / sg) ** 2)
        return Tt


def lam_rgb(l):
    r = g = b = 0.0
    if l < 440:
        r, b = -(l - 440) / 60.0, 1.0
    elif l < 490:
        g, b = (l - 440) / 50.0, 1.0
    elif l < 510:
        g, b = 1.0, -(l - 510) / 20.0
    elif l < 580:
        r, g = (l - 510) / 70.0, 1.0
    elif l < 645:
        r, g = 1.0, -(l - 645) / 65.0
    else:
        r = 1.0
    f = 0.3 + 0.7 * (l - 380) / 40 if l < 420 else (0.3 + 0.7 * (780 - l) / 80 if l > 700 else 1.0)
    return [max(0.0, min(1.0, v * max(0.0, f))) for v in (r, g, b)]


# ==========================================================================
#  2.  the apparatus
# ==========================================================================
PARTS = [("bench", "주 광학 벤치·각도기 [6]", "main optical bench [6]"),
         ("psu", "직류 어댑터 [8]", "DC adapter [8]"),
         ("arm", "회절격자 팔 [2]", "diffraction arm [2]"),
         ("lholder", "레이저 홀더 [3]", "laser holder [3]"),
         ("sholder", "시료 홀더 [5]", "sample holder [5]"),
         ("pd", "포토다이오드 [4]", "photodiode [4]"),
         ("mm", "멀티미터 [17]", "multimeter [17]"),
         ("samples", "광결정 시료 접시 [13]", "dish with samples [13]"),
         ("wetkit", "주사기·물·커버슬립·핀셋", "syringe, water, coverslip, tweezers")]


class Rig:
    def __init__(self, seed=None):
        self.t = Truth(seed)
        self.placed = set()
        self.left = None            # "arm" | "lholder"
        self.laser = None
        self.lamp = False
        self.lock = False
        self.laser_t0 = 0.0
        self.phiL = 38.0            # reading of the left protractor
        self.phi_laser = 0.0
        self.thR = 0.0              # reading of the right protractor
        self.lens = 0.5             # 0.5: lamp in the focal point
        self.sample = None
        self.wet = 0.0
        self.cover = False
        self.mm_mode = "OFF"
        self.clock = 0.0

    def place(self, pid):
        if pid in ("arm", "lholder"):
            if "bench" not in self.placed:
                return T("먼저 주 광학 벤치를 놓아야 한다.", "put the main bench down first.")
            if self.left:
                return T("왼쪽 구멍이 이미 차 있다.", "the left hole is taken.")
            self.left = pid
        if pid in ("sholder", "pd") and "bench" not in self.placed:
            return T("먼저 주 광학 벤치를 놓아야 한다.", "put the main bench down first.")
        self.placed.add(pid)
        return None

    def remove(self, pid):
        self.placed.discard(pid)
        if pid == self.left:
            self.left, self.lamp, self.lock, self.laser = None, False, False, None
        if pid == "sholder":
            self.sample, self.cover, self.wet = None, False, 0.0

    def lamp_lit(self):
        return self.left == "arm" and self.lamp and "psu" in self.placed

    def laser_lit(self):
        return self.left == "lholder" and self.laser and self.lock and "psu" in self.placed

    def theta(self):
        return (self.thR - self.t.zeroR) * DEG

    def step(self, dt):
        self.clock += dt
        if self.cover:
            self.wet = min(1.0, self.wet + dt / 4.0)
        elif self.wet > 0:
            self.wet = max(0.0, self.wet - dt / 40.0)

    def current(self):
        if "pd" not in self.placed or "mm" not in self.placed:
            return None
        t, I = self.t, self.t.dark
        if self.laser_lit():
            age = self.clock - self.laser_t0
            warm = 1 - t.warm * math.exp(-age / 70.0) + 0.004 * math.sin(age * 0.7)
            align = math.exp(-((self.phi_laser - t.laser_off) / 0.9) ** 2)
            tr = 1.0
            if self.sample and "sholder" in self.placed:
                tr = t.transmit(self.sample, LASER_NM[self.laser], self.theta(), self.wet) * (0.93 if self.cover else 1.0)
            I += t.I[self.laser] * warm * align * tr
        if self.lamp_lit():
            I += 0.8
        return I * (1 + t.rng.gauss(0, 0.003)) + t.rng.gauss(0, 0.15)

    def mm_text(self):
        I = self.current()
        if self.mm_mode == "OFF":
            return ""
        if I is None:
            return "0.0"
        if self.mm_mode == "200 uA":
            return "1" if abs(I) > 199.9 else "%.1f" % I
        if self.mm_mode == "2000 uA":
            return "1" if abs(I) > 1999 else "%.0f" % I
        return "1" if abs(I / 1000) > 19.99 else "%.2f" % (I / 1000)


# ==========================================================================
#  3.  the window
# ==========================================================================
COL_BG, COL_PANEL, COL_TXT, COL_ACC = "#1c2027", "#22262d", "#e8eef2", "#f2c14e"


class App(tk.Tk):
    def __init__(self, seed=None):
        super().__init__()
        self.rig = Rig(seed)
        self.title("APhO 2017 — " + T("광결정", "Photonic crystal"))
        self.configure(bg=COL_BG)
        self.geometry("1320x820")
        self.status = tk.StringVar(value=T("부품을 실험대에 놓으십시오.", "put the parts on the bench."))
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=6, pady=6)
        self.nb = nb
        f1, f2 = ttk.Frame(nb), ttk.Frame(nb)
        nb.add(f1, text=T(" 조립 ", " Assembly "))
        nb.add(f2, text=T(" 실험대 ", " Bench "))
        self._build_asm(f1)
        self._build_bench(f2)
        tk.Label(self, textvariable=self.status, bg=COL_BG, fg="#b9c6cf", anchor="w").pack(fill="x", padx=8)
        self._last = None
        self.after(100, self._tick)

    # ----------------------------------------------------------- assembly
    def _build_asm(self, root):
        box = tk.Frame(root, bg=COL_PANEL)
        box.pack(side="left", fill="y", padx=8, pady=8)
        tk.Label(box, text=T("부품 상자", "parts box"), bg=COL_PANEL, fg=COL_ACC,
                 font=("TkDefaultFont", 11, "bold")).pack(pady=6)
        self.part_btn = {}
        for pid, ko, en in PARTS:
            row = tk.Frame(box, bg=COL_PANEL)
            row.pack(fill="x", padx=6, pady=2)
            tk.Label(row, text=T(ko, en), bg=COL_PANEL, fg=COL_TXT, width=28, anchor="w").pack(side="left")
            b = ttk.Button(row, text=T("놓기", "place"), width=8, command=lambda p=pid: self.toggle_part(p))
            b.pack(side="right")
            self.part_btn[pid] = b
        self.cv_asm = tk.Canvas(root, bg="#d6d3c8", highlightthickness=0)
        self.cv_asm.pack(side="left", fill="both", expand=True, padx=8, pady=8)

    def toggle_part(self, pid):
        r = self.rig
        if pid in r.placed:
            r.remove(pid)
            self.status.set(T("부품함에 넣었다.", "put back."))
        else:
            err = r.place(pid)
            self.status.set(err or T("놓았다.", "placed."))
        self.refresh()

    # -------------------------------------------------------------- bench
    def _build_bench(self, root):
        left = tk.Frame(root, bg=COL_BG)
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, text=T("들여다보기: 시료 너머의 회절격자 창 (가운데 눈금)",
                              "looking through the sample at the grating window (middle mark)"),
                 bg=COL_BG, fg="#9aa3ab").pack(anchor="w", padx=6)
        self.cv_eye = tk.Canvas(left, height=200, bg="#08090b", highlightthickness=0)
        self.cv_eye.pack(fill="x", padx=6, pady=4)
        tk.Label(left, text=T("각도기 (왼쪽 원판 · 오른쪽 원판)", "protractors (left disk · right disk)"),
                 bg=COL_BG, fg="#9aa3ab").pack(anchor="w", padx=6)
        self.cv_prot = tk.Canvas(left, height=300, bg="#15181d", highlightthickness=0)
        self.cv_prot.pack(fill="both", expand=True, padx=6, pady=4)

        p = tk.Frame(root, bg=COL_PANEL, width=380)
        p.pack(side="right", fill="y", padx=6, pady=6)
        p.pack_propagate(False)
        lf = ttk.LabelFrame(p, text=T(" 원판 돌리기 ", " turn the disks "))
        lf.pack(fill="x", padx=6, pady=4)
        for row, (lab, fn) in enumerate(((T("왼쪽", "left"), self.turnL), (T("오른쪽", "right"), self.turnR))):
            tk.Label(lf, text=lab, width=6).grid(row=row, column=0)
            for j, s in enumerate((-1, -0.5, -0.1, 0.1, 0.5, 1)):
                ttk.Button(lf, text="%+g°" % s, width=5, command=lambda f=fn, s=s: f(s)).grid(row=row, column=j + 1, padx=1, pady=2)
        lf2 = ttk.LabelFrame(p, text=T(" 광원 ", " light "))
        lf2.pack(fill="x", padx=6, pady=4)
        self.lamp_btn = ttk.Button(lf2, command=self.toggle_lamp)
        self.lamp_btn.pack(fill="x", padx=4, pady=2)
        r = tk.Frame(lf2)
        r.pack(fill="x")
        for c, ko, en in (("red", "빨강 659", "red 659"), ("green", "초록 530", "green 530"), ("blue", "파랑 400", "blue 400")):
            ttk.Button(r, text=T(ko, en), command=lambda c=c: self.set_laser(c)).pack(side="left", expand=True, fill="x", padx=1)
        self.lock_btn = ttk.Button(lf2, command=self.toggle_lock)
        self.lock_btn.pack(fill="x", padx=4, pady=2)
        tk.Label(lf2, text=T("렌즈 F 위치", "lens F position")).pack(anchor="w", padx=4)
        self.lens_var = tk.DoubleVar(value=0.5)
        ttk.Scale(lf2, from_=0, to=1, variable=self.lens_var, command=lambda e: self.refresh()).pack(fill="x", padx=4, pady=2)
        lf3 = ttk.LabelFrame(p, text=T(" 시료 ", " sample "))
        lf3.pack(fill="x", padx=6, pady=4)
        r = tk.Frame(lf3)
        r.pack(fill="x")
        for s in ("X", "Y", "Z", None):
            ttk.Button(r, text=s or T("빼기", "out"), command=lambda s=s: self.set_sample(s)).pack(side="left", expand=True, fill="x", padx=1)
        self.wet_btn = ttk.Button(lf3, command=self.toggle_wet)
        self.wet_btn.pack(fill="x", padx=4, pady=2)
        self.sample_lab = tk.Label(lf3, text="", anchor="w")
        self.sample_lab.pack(fill="x", padx=4)
        lf4 = ttk.LabelFrame(p, text=T(" 멀티미터 (직류 전류) ", " multimeter (DC current) "))
        lf4.pack(fill="x", padx=6, pady=4)
        self.mm_var = tk.StringVar(value="OFF")
        cb = ttk.Combobox(lf4, state="readonly", values=("OFF", "200 uA", "2000 uA", "20 mA"), textvariable=self.mm_var, width=10)
        cb.pack(padx=4, pady=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        self.mm_lab = tk.Label(lf4, text="", bg="#a9b896", fg="#111", font=("Courier", 20, "bold"), width=10, anchor="e")
        self.mm_lab.pack(padx=4, pady=4)
        lf5 = ttk.LabelFrame(p, text=T(" 실험 노트 ", " notebook "))
        lf5.pack(fill="both", expand=True, padx=6, pady=4)
        ttk.Button(lf5, text=T("각도·전류 적기", "write down angles & current"), command=self.note).pack(fill="x", padx=4)
        self.notes = tk.Text(lf5, height=8, bg="#12161b", fg=COL_TXT, font=("Courier", 9))
        self.notes.pack(fill="both", expand=True, padx=4, pady=4)

    # ----------------------------------------------------------- actions
    def turnL(self, s):
        r = self.rig
        if r.left == "arm":
            r.phiL = max(-85, min(85, round(r.phiL + s, 2)))
        elif r.left == "lholder":
            r.phi_laser = max(-85, min(85, round(r.phi_laser + s, 2)))
        self.refresh()

    def turnR(self, s):
        if "sholder" in self.rig.placed:
            self.rig.thR = max(-85, min(85, round(self.rig.thR + s, 2)))
        self.refresh()

    def toggle_lamp(self):
        r = self.rig
        if r.left != "arm" or "psu" not in r.placed:
            self.status.set(T("회절격자 팔과 직류 어댑터가 필요하다.", "the diffraction arm and the adapter are needed."))
            return
        r.lamp = not r.lamp
        self.refresh()

    def set_laser(self, c):
        r = self.rig
        if r.left != "lholder":
            self.status.set(T("레이저 홀더가 왼쪽 구멍에 있어야 한다.", "the laser holder must be in the left hole."))
            return
        swap = (r.laser, c) in (("red", "blue"), ("blue", "red"))
        r.laser = c
        if not swap:
            r.lock = False
        r.laser_t0 = r.clock
        self.status.set(T("레이저를 홀더에 고정했다.", "laser fixed on the holder."))
        self.refresh()

    def toggle_lock(self):
        r = self.rig
        if not (r.left == "lholder" and r.laser and "psu" in r.placed):
            self.status.set(T("홀더·레이저·어댑터가 필요하다.", "holder, laser and adapter are needed."))
            return
        r.lock = not r.lock
        if r.lock:
            r.laser_t0 = r.clock
        self.refresh()

    def set_sample(self, s):
        r = self.rig
        if s and not ("samples" in r.placed and "sholder" in r.placed):
            self.status.set(T("시료 접시와 시료 홀더가 필요하다.", "the sample dish and the holder are needed."))
            return
        r.sample, r.cover, r.wet = s, False, 0.0
        self.refresh()

    def toggle_wet(self):
        r = self.rig
        if not r.sample:
            return
        if r.cover:
            r.cover = False
        elif "wetkit" in r.placed:
            r.cover = True
        else:
            self.status.set(T("주사기·물·커버슬립·핀셋이 필요하다.", "syringe, water, coverslip and tweezers are needed."))
        self.refresh()

    def note(self):
        r = self.rig
        L = ("phi=%.1f" % r.phiL) if r.left == "arm" else ("laser " + (r.laser or "-")) if r.left == "lholder" else ""
        self.notes.insert("end", "%s%s  %s  theta=%.1f  I=%s\n" % (r.sample or "-", "(wet)" if r.cover else "", L, r.thR,
                                                                   r.mm_text() or "-"))
        self.notes.see("end")

    # ------------------------------------------------------------ drawing
    def _tick(self):
        if not self.winfo_exists():
            return
        self.rig.step(0.3)
        self.refresh(light=True)
        self.after(300, self._tick)

    def refresh(self, light=False):
        r = self.rig
        r.lens = self.lens_var.get()
        r.mm_mode = self.mm_var.get()
        for pid, b in self.part_btn.items():
            b.configure(text=T("치우기", "remove") if pid in r.placed else T("놓기", "place"))
        self.lamp_btn.configure(text=T("램프 끄기", "lamp off") if r.lamp else T("램프 켜기", "lamp on"))
        self.lock_btn.configure(text=T("버튼 잠금 풀기", "release button lock") if r.lock else T("버튼 잠금 돌리기 (레이저 켜기)", "turn button lock (laser on)"))
        self.wet_btn.configure(text=T("커버슬립 떼고 말리기", "lift coverslip, let dry") if r.cover else T("물 + 커버슬립", "water + coverslip"))
        self.sample_lab.configure(text=(T("홀더: 시료 ", "holder: sample ") + r.sample) if r.sample else T("홀더 비어 있음", "holder empty"))
        self.mm_lab.configure(text=r.mm_text())
        self.draw_eye()
        self.draw_prot()
        if not light:
            self.draw_asm()

    def draw_asm(self):
        c = self.cv_asm
        c.delete("all")
        r = self.rig
        w = c.winfo_width() or 800
        if "bench" in r.placed:
            c.create_rectangle(80, 220, w - 80, 260, fill="#5a6168", outline="#1e2226", width=2)
            for x in (220, w - 300):
                c.create_oval(x - 40, 200, x + 40, 280, fill="#d9dde2", outline="#555")
            if r.left == "arm":
                c.create_line(220, 240, 40, 120, width=8, fill="#4a4f55")
                c.create_oval(28, 108, 52, 132, fill="#fff2b0" if r.lamp_lit() else "#8a8478")
            if r.left == "lholder":
                c.create_rectangle(170, 232, 270, 248, fill="#3a3e44")
            if "sholder" in r.placed:
                c.create_rectangle(w - 304, 215, w - 296, 265, fill={"X": "#d23b3b", "Y": "#2f9a4a", "Z": "#2f5fd0"}.get(r.sample, "#3a3e44"))
            if "pd" in r.placed:
                c.create_rectangle(w - 150, 225, w - 130, 255, fill="#2b2f35")
        c.create_text(20, 20, anchor="nw", text=T("위에서 본 실험대", "the bench from above"), fill="#555")

    def draw_eye(self):
        c = self.cv_eye
        c.delete("all")
        r = self.rig
        w = c.winfo_width() or 700
        h = 200
        x0, x1 = 60, w - 60
        c.create_rectangle(x0 - 8, 30, x1 + 8, 170, outline="#3a3e44", width=3)
        if not r.lamp_lit():
            c.create_text(w / 2, 100, text=T("(램프 꺼짐 또는 회절격자 팔 없음)", "(lamp off or no diffraction arm)"), fill="#5a626c")
            return
        phi = (r.phiL - r.t.zeroL) * DEG
        half = (1.1 + 9 * abs(r.lens - 0.5) / 0.5) * DEG
        smp = r.sample if "sholder" in r.placed else None
        th = r.theta()
        n = 180
        dx = (x1 - x0) / n
        for i in range(n):
            x = -1 + 2 * (i + 0.5) / n
            lam = H_GRATING * math.sin(phi + x * half)
            if 380 <= lam <= 780:
                rgb = lam_rgb(lam)
                f = min(1.0, 0.35 + 0.65 * (lam - 380) / 250)
                if smp:
                    f *= 0.02 if abs(th) > 78 * DEG else r.t.transmit(smp, lam, th, r.wet) * (0.93 if r.cover else 1)
                col = "#%02x%02x%02x" % tuple(int(255 * v * f) for v in rgb)
            else:
                col = "#08090b"
            c.create_rectangle(x0 + i * dx, 80, x0 + (i + 1) * dx + 1, 120, fill=col, outline="")
        c.create_line(w / 2, 40, w / 2, 75, fill="#cfd6dc", width=2)
        c.create_line(w / 2, 125, w / 2, 160, fill="#cfd6dc", width=2)

    def draw_prot(self):
        c = self.cv_prot
        c.delete("all")
        r = self.rig
        w = c.winfo_width() or 700
        R = min(w * 0.2, 130)
        for k, cx in (("L", w * 0.27), ("R", w * 0.73)):
            cy = 40 + R + 10
            val = None
            if k == "L":
                val = r.phiL if r.left == "arm" else (r.phi_laser if r.left == "lholder" else None)
            elif "sholder" in r.placed:
                val = r.thR
            if val is None:
                c.create_text(cx, cy - R / 2, text=T("(비어 있음)", "(empty)"), fill="#69717a")
                continue
            c.create_arc(cx - R, cy - R, cx + R, cy + R, start=0, extent=180, fill="#e6e9ec", outline="#6d7277")
            for a in range(-90, 91):
                t = (a - 90) * DEG
                L = R * (0.12 if a % 10 == 0 else 0.08 if a % 5 == 0 else 0.045)
                c.create_line(cx + math.cos(t) * R, cy + math.sin(t) * R, cx + math.cos(t) * (R - L), cy + math.sin(t) * (R - L), fill="#222")
                if a % 10 == 0:
                    c.create_text(cx + math.cos(t) * (R - L - 12), cy + math.sin(t) * (R - L - 12), text=str(abs(a)), fill="#222", font=("TkDefaultFont", 8))
            t = (val - 90) * DEG
            c.create_polygon(cx + math.cos(t) * (R - 2), cy + math.sin(t) * (R - 2),
                             cx + math.cos(t - 0.035) * R * 0.66, cy + math.sin(t - 0.035) * R * 0.66,
                             cx + math.cos(t + 0.035) * R * 0.66, cy + math.sin(t + 0.035) * R * 0.66, fill=COL_ACC)
            c.create_text(cx, cy + 20, text=T("왼쪽 원판", "left disk") if k == "L" else T("오른쪽 원판", "right disk"), fill="#cfd6dc")

    def destroy(self):
        try:
            for aid in self.tk.call("after", "info"):
                try:
                    self.after_cancel(aid)
                except Exception:
                    pass
        except Exception:
            pass
        tk.Tk.destroy(self)


def main():
    global LANG
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
        if a == "--en":
            LANG = "en"
    App(seed).mainloop()


if __name__ == "__main__":
    main()
