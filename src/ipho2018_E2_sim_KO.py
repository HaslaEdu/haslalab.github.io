#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPhO 2018 (Lisbon) - Experimental Problem 2
Viscoelasticity of a polymer thread

Virtual apparatus.  Nothing is computed for the student: the scale shows
grams, the stopwatch shows seconds, the rulers show millimetres.  Every
derived quantity (F, eps, beta, E0, E1, E2, tau1, tau2, tau3, d, D) has to
be worked out on paper.

Hidden true parameters are re-randomised every session.

The parts are taken out of the box one by one; nothing on screen tells
you where an item has to go.

Run:  python ipho2018_E2_sim_KO.py   (EN edition: ipho2018_E2_sim_EN.py)
"""
import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "KO"          # the EN edition differs only in this line
TR = {
    'IPhO 2018 Experimental Problem 2 - Viscoelasticity of a polymer thread': 'IPhO 2018 실험 2 - 고분자 실의 점탄성',
    '1. Assembly': '1. 조립',
    '2. Bench (Part A)': '2. 실험대 (Part A)',
    '3. Diffraction (Part B)': '3. 회절 (Part B)',
    '4. Short thread (Part C/E)': '4. 짧은 실 (Part C/E)',
    'Drag each item from the tray onto its ghosted position.': '쟁반의 부품을 흐리게 표시된 자리로 끌어다 놓으세요.',
    'Tray': '부품 쟁반',
    'Placed: ': '설치됨: ',
    'Assembly complete - go to the Bench tab.': '조립 완료 - 실험대 탭으로 이동하세요.',
    'Place ': '먼저 ',
    ' first.': ' 을(를) 설치하세요.',
    'Digital scale': '전자저울',
    'Stopwatch': '스톱워치',
    'Experiment': '실험',
    'Hang the thread on the upper support\n(starts the stopwatch at the same instant)': '실을 위쪽 지지대에 걸기\n(동시에 스톱워치가 시작됩니다)',
    'Time scale': '시간 배속',
    'Measuring tape / ruler': '줄자 / 자',
    'Measure thread between screw heads': '나사 머리 사이의 실 길이 재기',
    'The tape reads to the nearest millimetre. Remember to add 5 mm for each screw.': '줄자는 1 mm 까지 읽힙니다. 나사 하나당 5 mm 를 더해야 합니다.',
    'assemble first': '먼저 조립하세요',
    'switch the scale on first': '먼저 저울을 켜세요',
    'Thread hung - measurement running': '실 걸림 - 측정 진행 중',
    'between screw heads': '나사 머리 사이',
    'constant strain': '일정 변형률',
    'Elapsed': '경과',
    'time scale': '시간 배속',
    'Laser': '레이저',
    'Spring clamp ON/OFF': '집게로 레이저 ON/OFF',
    'Wavelength printed on the pointer: 650 +- 10 nm': '포인터에 인쇄된 파장: 650 +- 10 nm',
    'Optical path': '광 경로',
    'thread -> screen directly': '실 -> 스크린 직접',
    'fold once with mirror 1': '거울 1 로 한 번 접기',
    'fold twice with mirrors 1 + 2': '거울 1 + 2 로 두 번 접기',
    'Screen distance along the last leg': '마지막 구간의 스크린 거리',
    'Screen region shown': '화면에 보이는 스크린 폭',
    'Tape measure': '줄자',
    'Measure each leg of the optical path': '광 경로 각 구간 재기',
    'Drag on the screen with the mouse to lay the ruler between two minima. The ruler reads to 0.5 mm.': '스크린 위에서 마우스를 끌어 두 극소 사이에 자를 놓으세요. 자는 0.5 mm 까지 읽힙니다.',
    'switch the laser on': '레이저를 켜세요',
    'Hang the thread, place the screen, then switch the laser on.': '실을 걸고 스크린을 놓은 뒤 레이저를 켜세요.',
    'A4 screen': 'A4 스크린',
    'view width': '표시 폭',
    'Part C': 'Part C',
    'Measure the short thread (unstretched)': '짧은 실 길이 재기 (늘어나기 전)',
    'Transfer the mass-set and hang the short thread': '추 뭉치를 옮겨 짧은 실에 매달기',
    'Part E': 'Part E',
    'Measure the stretched short thread': '늘어난 짧은 실 길이 재기',
    'The thread must hang for at least 30 minutes before the strain is stationary. Use the time scale on the Bench tab.': '변형률이 정상 상태가 되려면 최소 30분은 매달아 두어야 합니다. 실험대 탭의 시간 배속을 쓰세요.',
    'finish Part A first': 'Part A 를 먼저 끝내세요',
    'not hung yet': '아직 매달지 않았습니다',
    'hanging for': '매단 시간',
    'Transfer the mass-set to the short thread.': '추 뭉치를 짧은 실로 옮기세요.',
    'Standing structure': '스탠드 구조물',
    'Mass-set': '추 뭉치',
    'Long TPU thread': '긴 TPU 실',
    'Laser pointer + support': '레이저 포인터 + 받침',
    'Plane mirror 1': '평면거울 1',
    'Plane mirror 2': '평면거울 2',
    'A4 paper screen': 'A4 종이 스크린',
    'ON/OFF': '전원',
    'TARE': '영점',
    'START/STOP': '시작/정지',
    'LAP': '랩',
    'RESET': '리셋',
    'Click each item in the box to take it out onto the bench.': '부품함의 항목을 눌러 실험대로 꺼내세요.',
    'Take the %s out first.': '먼저 %s 을(를) 꺼내세요.',
    '%d of %d items on the bench.': '%d / %d 개를 꺼냈습니다.',
    'Everything is on the bench. Go to the Bench tab.': '모두 실험대에 있습니다. 실험대 탭으로 이동하세요.',
}



import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _setup_hangul_font(root):
    """Point every named Tk font at a family that actually has Hangul."""
    import tkinter.font as _tkfont
    want = ("Malgun Gothic", "AppleGothic", "Apple SD Gothic Neo",
            "NanumGothic", "NanumBarunGothic", "Noto Sans CJK KR",
            "Noto Sans KR", "UnDotum", "Gulim", "Batang")
    have = set(_tkfont.families(root))
    fam = next((f for f in want if f in have), None)
    if not fam:
        return
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont",
                 "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont",
                 "TkIconFont", "TkTooltipFont"):
        try:
            _tkfont.nametofont(name, root).configure(family=fam)
        except Exception:
            pass


def T(s):
    return TR.get(s, s) if LANG != "EN" else s


# ==========================================================================
#  PHYSICS
# ==========================================================================
GRAV = 9.80                     # m/s^2, Lisbon (given in the problem)
LAMBDA_NM = 650.0               # laser wavelength, nominal


class Thread:
    """Generalised standard-linear-solid thread.

    Calibrated so that a student following the official extraction route
    (D.6 -> D.13) recovers the official answers:
        tau1 = 1546 s, E1 = 7.4e5    tau2 = 177 s, E2 = 4.5e5
        E0 = 1.31e7                  tau3 ~ 50 s
    """

    def __init__(self, rng):
        j = lambda s: 1.0 + rng.gauss(0.0, s)
        # --- generating parameters (hidden) -------------------------------
        self.F0 = 40.320 * j(0.012)          # gf
        self.F1 = 2.280 * j(0.05)
        self.T1 = 1546.0 * j(0.05)
        self.F2 = 1.390 * j(0.06)
        self.T2 = 177.0 * j(0.06)
        self.F3 = 2.309 * j(0.07)
        self.T3 = 23.6 * j(0.08)

        # --- geometry ------------------------------------------------------
        # the stretched length is fixed by the stand: upper support to the
        # scale platform.  Only the relaxed length varies from thread to
        # thread, so the strain varies -- and with it the force, since the
        # material moduli E_k are what is actually constant.
        self.l = 0.510 * j(0.002)            # m, stretched long thread
        self.l0 = 0.437 * j(0.004)           # m, unstretched long thread
        eps = (self.l - self.l0) / self.l0
        k = eps / 0.16705                    # F_k scale with the strain
        for a in ("F0", "F1", "F2", "F3"):
            setattr(self, a, getattr(self, a) * k)
        self.d_stretched = 0.480e-3 * j(0.012) * (0.16705 / eps) ** 0.25
        self.d_rest = 0.500e-3

        self.l0_short = 0.326 * j(0.008)
        # short thread under constant stress: eps' = sigma/E
        self.mass = 81.11e-3 * j(0.004)      # kg, mass-set
        self.tau_creep = 420.0 * j(0.1)      # s, creep towards stationary strain

    # ---- constant-strain relaxation (Part A / D) -------------------------
    def force_gf(self, t):
        """force pulled off the scale, in gram-force"""
        if t <= 0.0:
            return self.F0 + self.F1 + self.F2 + self.F3
        return (self.F0
                + self.F1 * math.exp(-t / self.T1)
                + self.F2 * math.exp(-t / self.T2)
                + self.F3 * math.exp(-t / self.T3))

    def scale_reading_g(self, t):
        """what the digital scale under the mass-set shows, in gram"""
        return self.mass * 1e3 - self.force_gf(t)

    # ---- constant-stress creep (Part C / E) ------------------------------
    def eps_short(self, t):
        """strain of the short thread, t seconds after it was hung"""
        E0 = self.beta() * self.F0
        sigma = self.mass * GRAV / self.area()
        eps_inf = sigma / E0 * 1.021          # the 2 % offset seen in the real data
        return eps_inf * (1.0 - math.exp(-t / self.tau_creep))

    def len_short(self, t):
        return self.l0_short * (1.0 + self.eps_short(t))

    # ---- helpers used only for internal validation -----------------------
    def strain(self):
        return (self.l - self.l0) / self.l0

    def area(self):
        return math.pi * (self.d_stretched / 2.0) ** 2

    def beta(self):
        return 1e-3 * GRAV / (self.strain() * self.area())


class Scale:
    """Digital balance, 0.01 g resolution, slow settling, small drift."""

    def __init__(self, rng):
        self.rng = rng
        self.tau = 0.45                       # s, mechanical settling
        self.noise = 0.0015                   # g rms
        self.drift = rng.gauss(0.0, 0.01)     # g, tare offset
        self.value = 0.0
        self.shown = 0.0
        self.on = False
        self.warm_t = 0.0

    def update(self, target, dt):
        if not self.on:
            return
        self.warm_t += dt
        a = 1.0 - math.exp(-dt / self.tau)
        self.value += (target - self.value) * a
        w = 0.0 if self.warm_t > 600 else 0.02 * math.exp(-self.warm_t / 240.0)
        self.shown = self.value + self.drift + w + self.rng.gauss(0.0, self.noise)

    def display(self):
        if not self.on:
            return ""
        return "%8.2f" % (round(self.shown * 100.0) / 100.0)


# ==========================================================================
#  APPLICATION
# ==========================================================================
PARTS = [
    ("stand", "Standing structure"),
    ("scale", "Digital scale"),
    ("massset", "Mass-set"),
    ("thread", "Long TPU thread"),
    ("laser", "Laser pointer + support"),
    ("mirror1", "Plane mirror 1"),
    ("mirror2", "Plane mirror 2"),
    ("screen", "A4 paper screen"),
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(T("IPhO 2018 Experimental Problem 2 - Viscoelasticity of a polymer thread"))
        self.geometry("1180x760")
        _setup_hangul_font(self)
        self.rng = random.Random()
        self.th = Thread(self.rng)
        self.scale = Scale(self.rng)

        self.t_exp = 0.0            # s, time since the thread was hung (-1 = not hung)
        self.hung = False
        self.t_short = None         # s, time since the short thread was hung
        self.speed = 1.0
        self.watch_t = 0.0
        self.watch_run = False
        self.laps = []
        self.placed = set()
        self.on_scale = False       # mass-set resting on the scale platform
        self.laser_on = False
        self.mirror_use = 0         # 0, 1 or 2 mirrors in the optical path
        self.D_extra = 0.0
        self.short_mounted = False

        self._build()
        self.after(50, self._tick)

    # ------------------------------------------------------------------
    def _build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.nb = nb

        self.tab_asm = tk.Frame(nb, bg="#f4f2ee")
        self.tab_bench = tk.Frame(nb, bg="#f4f2ee")
        self.tab_diff = tk.Frame(nb, bg="#f4f2ee")
        self.tab_short = tk.Frame(nb, bg="#f4f2ee")
        nb.add(self.tab_asm, text=T("1. Assembly"))
        nb.add(self.tab_bench, text=T("2. Bench (Part A)"))
        nb.add(self.tab_diff, text=T("3. Diffraction (Part B)"))
        nb.add(self.tab_short, text=T("4. Short thread (Part C/E)"))

        self._build_asm()
        self._build_bench()
        self._build_diff()
        self._build_short()

    # ---------------- assembly ----------------------------------------
    def _build_asm(self):
        f = self.tab_asm
        tk.Label(f, bg="#f4f2ee", font=("TkDefaultFont", 10),
                 text=T("Click each item in the box to take it out onto the bench.")
                 ).pack(anchor="w", padx=12, pady=8)
        box = tk.Frame(f, bg="#f4f2ee")
        box.pack(fill="both", expand=True, padx=16, pady=8)
        self.asm_btn = {}
        for i, (k, name) in enumerate(PARTS):
            b = tk.Button(box, text=T(name), width=34, anchor="w",
                          command=lambda k=k: self._take(k))
            b.grid(row=i, column=0, sticky="w", pady=3)
            self.asm_btn[k] = b
        self.asm_note = tk.Label(box, bg="#f4f2ee", fg="#4a443a", justify="left",
                                 wraplength=680, text="")
        self.asm_note.grid(row=len(PARTS), column=0, sticky="w", pady=14)
        self.draw_asm()

    def _take(self, k):
        need = {"massset": "scale", "thread": "stand"}.get(k)
        if need and need not in self.placed:
            self.asm_note.config(text=T("Take the %s out first.") % T(dict(PARTS)[need]))
            return
        self.placed.add(k)
        if k == "massset":
            self.on_scale = True
        self.draw_asm()

    def draw_asm(self):
        for k, name in PARTS:
            self.asm_btn[k].config(text=("[x] " if k in self.placed else "[ ] ") + T(name),
                                   relief="sunken" if k in self.placed else "raised")
        if len(self.placed) == len(PARTS):
            self.asm_note.config(text=T("Everything is on the bench. Go to the Bench tab."))
        else:
            self.asm_note.config(text=T("%d of %d items on the bench.")
                                 % (len(self.placed), len(PARTS)))

    # ---------------- bench -------------------------------------------
    def _build_bench(self):
        f = self.tab_bench
        left = tk.Frame(f, bg="#f4f2ee")
        left.pack(side="left", fill="both", expand=True)
        self.c_bench = tk.Canvas(left, bg="#fbfaf7", highlightthickness=0)
        self.c_bench.pack(fill="both", expand=True, padx=10, pady=10)

        r = tk.Frame(f, bg="#f4f2ee", width=330)
        r.pack(side="right", fill="y")
        r.pack_propagate(False)

        box = tk.LabelFrame(r, text=T("Digital scale"), bg="#f4f2ee", padx=8, pady=8)
        box.pack(fill="x", padx=10, pady=(12, 6))
        self.lbl_scale = tk.Label(box, text="", bg="#0e1a12", fg="#7dfda1",
                                  font=("Courier New", 26, "bold"), width=9, anchor="e")
        self.lbl_scale.pack(fill="x")
        tk.Label(box, text="g", bg="#f4f2ee").pack(anchor="e")
        bf = tk.Frame(box, bg="#f4f2ee"); bf.pack(fill="x", pady=4)
        tk.Button(bf, text=T("ON/OFF"), width=9, command=self._scale_toggle).pack(side="left")
        tk.Button(bf, text=T("TARE"), width=9, command=self._tare).pack(side="left", padx=4)

        box2 = tk.LabelFrame(r, text=T("Stopwatch"), bg="#f4f2ee", padx=8, pady=8)
        box2.pack(fill="x", padx=10, pady=6)
        self.lbl_watch = tk.Label(box2, text="0:00.00", bg="#141414", fg="#e8e8e8",
                                  font=("Courier New", 20, "bold"))
        self.lbl_watch.pack(fill="x")
        wf = tk.Frame(box2, bg="#f4f2ee"); wf.pack(fill="x", pady=4)
        tk.Button(wf, text=T("START/STOP"), command=self._watch_toggle).pack(side="left")
        tk.Button(wf, text=T("LAP"), command=self._lap).pack(side="left", padx=4)
        tk.Button(wf, text=T("RESET"), command=self._watch_reset).pack(side="left")
        self.lst_lap = tk.Listbox(box2, height=7, font=("Courier New", 9))
        self.lst_lap.pack(fill="x", pady=(4, 0))

        box3 = tk.LabelFrame(r, text=T("Experiment"), bg="#f4f2ee", padx=8, pady=8)
        box3.pack(fill="x", padx=10, pady=6)
        self.btn_hang = tk.Button(box3, wraplength=280, justify="left",
                                  text=T("Hang the thread on the upper support\n"
                                         "(starts the stopwatch at the same instant)"),
                                  command=self._hang)
        self.btn_hang.pack(fill="x")
        tk.Label(box3, text=T("Time scale"), bg="#f4f2ee").pack(anchor="w", pady=(8, 0))
        sf = tk.Frame(box3, bg="#f4f2ee"); sf.pack(fill="x")
        self.spd = tk.IntVar(value=1)
        for v in (1, 10, 60, 300):
            tk.Radiobutton(sf, text="x%d" % v, variable=self.spd, value=v,
                           bg="#f4f2ee").pack(side="left")

        box4 = tk.LabelFrame(r, text=T("Measuring tape / ruler"), bg="#f4f2ee",
                             padx=8, pady=8)
        box4.pack(fill="x", padx=10, pady=6)
        tk.Button(box4, text=T("Measure thread between screw heads"),
                  command=self._measure_len).pack(fill="x")
        self.lbl_len = tk.Label(box4, text="--", bg="#f4f2ee", font=("Courier New", 11))
        self.lbl_len.pack(anchor="w", pady=(4, 0))
        tk.Label(box4, wraplength=290, justify="left", fg="#6a6254", bg="#f4f2ee",
                 text=T("The tape reads to the nearest millimetre. Remember to add "
                        "5 mm for each screw.")).pack(anchor="w")

    def _scale_toggle(self):
        if "scale" not in self.placed:
            return
        self.scale.on = not self.scale.on
        self.scale.warm_t = 0.0

    def _tare(self):
        if self.scale.on:
            self.scale.drift -= self.scale.shown

    def _watch_toggle(self):
        self.watch_run = not self.watch_run

    def _watch_reset(self):
        if not self.watch_run:
            self.watch_t = 0.0
            self.laps = []
            self.lst_lap.delete(0, "end")

    def _lap(self):
        if not self.watch_run:
            return
        self.laps.append(self.watch_t)
        self.lst_lap.insert(0, "%2d  %s   %s" % (len(self.laps),
                                                 self._fmt(self.watch_t),
                                                 self.lbl_scale["text"].strip()))

    def _hang(self):
        if self.hung:
            return
        for k in ("stand", "scale", "massset", "thread"):
            if k not in self.placed:
                self.lbl_len.config(text=T("assemble first"))
                return
        if not self.scale.on:
            self.lbl_len.config(text=T("switch the scale on first"))
            return
        self.hung = True
        self.t_exp = 0.0
        self.watch_t = 0.0
        self.watch_run = True
        self.btn_hang.config(state="disabled",
                             text=T("Thread hung - measurement running"))

    def _measure_len(self):
        if not self.hung:
            v = self.th.l0
        else:
            v = self.th.l
        v = v - 0.010                       # the tape spans screw head to screw head
        r = round(v * 1000.0 + self.rng.gauss(0.0, 0.6))
        self.lbl_len.config(text="%.1f cm  (%s)" % (r / 10.0, T("between screw heads")))

    @staticmethod
    def _fmt(t):
        return "%d:%05.2f" % (int(t // 60), t % 60)

    def draw_bench(self):
        c = self.c_bench
        c.delete("all")
        w = c.winfo_width() or 800
        h = c.winfo_height() or 640
        cx = w * 0.46
        top, base = 70, h - 70
        c.create_rectangle(cx - 130, base, cx + 130, base + 14, fill="#8d8577", outline="")
        c.create_rectangle(cx - 96, top, cx - 80, base, fill="#a8a091", outline="")
        c.create_rectangle(cx - 96, top, cx + 40, top + 14, fill="#a8a091", outline="")
        # scale
        if "scale" in self.placed:
            c.create_rectangle(cx - 70, base - 44, cx + 70, base - 6, fill="#3c3c3c",
                               outline="#222")
            c.create_rectangle(cx - 58, base - 62, cx + 58, base - 44, fill="#6d6d6d",
                               outline="#222")
            c.create_rectangle(cx + 6, base - 38, cx + 62, base - 16, fill="#0e1a12",
                               outline="#111")
            c.create_text(cx + 34, base - 27, text=self.scale.display().strip(),
                          fill="#7dfda1", font=("Courier New", 10, "bold"))
        # thread + mass
        if "thread" in self.placed:
            if self.hung:
                ytop = top + 14
                ybot = base - 62
                c.create_line(cx - 20, ytop, cx - 20, ybot, fill="#2f2a24", width=3)
                c.create_oval(cx - 26, ytop - 8, cx - 14, ytop + 4, fill="#b9b1a1",
                              outline="#6a6254")
                c.create_rectangle(cx - 40, ybot, cx, ybot + 44, fill="#9c9689",
                                   outline="#4a443a")
                c.create_text(cx + 150, top + 40, anchor="w", fill="#6a6254",
                              text=T("constant strain"))
            else:
                c.create_line(cx - 20, base - 130, cx - 20, base - 62, fill="#2f2a24",
                              width=3)
                c.create_rectangle(cx - 40, base - 62, cx, base - 18, fill="#9c9689",
                                   outline="#4a443a")
        c.create_text(20, 20, anchor="nw", fill="#4a443a",
                      text=T("Elapsed") + ": " + (self._fmt(self.t_exp) if self.hung
                                                  else "--"))
        c.create_text(20, 40, anchor="nw", fill="#6a6254",
                      text=T("time scale") + " x%d" % self.spd.get())

    # ---------------- diffraction --------------------------------------
    def _build_diff(self):
        f = self.tab_diff
        self.c_diff = tk.Canvas(f, bg="#101014", highlightthickness=0)
        self.c_diff.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        r = tk.Frame(f, bg="#f4f2ee", width=320)
        r.pack(side="right", fill="y"); r.pack_propagate(False)

        b = tk.LabelFrame(r, text=T("Laser"), bg="#f4f2ee", padx=8, pady=8)
        b.pack(fill="x", padx=10, pady=12)
        tk.Button(b, text=T("Spring clamp ON/OFF"),
                  command=self._laser_toggle).pack(fill="x")
        tk.Label(b, wraplength=280, justify="left", fg="#6a6254", bg="#f4f2ee",
                 text=T("Wavelength printed on the pointer: 650 +- 10 nm")
                 ).pack(anchor="w", pady=(6, 0))

        b2 = tk.LabelFrame(r, text=T("Optical path"), bg="#f4f2ee", padx=8, pady=8)
        b2.pack(fill="x", padx=10, pady=6)
        self.mvar = tk.IntVar(value=0)
        for n, lab in ((0, T("thread -> screen directly")),
                       (1, T("fold once with mirror 1")),
                       (2, T("fold twice with mirrors 1 + 2"))):
            tk.Radiobutton(b2, text=lab, variable=self.mvar, value=n, bg="#f4f2ee",
                           command=self._set_mirrors, anchor="w",
                           justify="left").pack(fill="x")
        tk.Label(b2, text=T("Screen distance along the last leg"),
                 bg="#f4f2ee").pack(anchor="w", pady=(8, 0))
        self.sld_D = tk.Scale(b2, from_=20, to=120, orient="horizontal", bg="#f4f2ee",
                              showvalue=False, command=lambda e: self.draw_diff())
        self.sld_D.set(60)
        self.sld_D.pack(fill="x")
        tk.Label(b2, text=T("Screen region shown"), bg="#f4f2ee").pack(anchor="w",
                                                                      pady=(8, 0))
        zf = tk.Frame(b2, bg="#f4f2ee"); zf.pack(fill="x")
        self.zoom = tk.IntVar(value=7)
        for v in (28, 14, 7):
            tk.Radiobutton(zf, text="%d cm" % v, variable=self.zoom, value=v,
                           bg="#f4f2ee",
                           command=self.draw_diff).pack(side="left")

        b3 = tk.LabelFrame(r, text=T("Tape measure"), bg="#f4f2ee", padx=8, pady=8)
        b3.pack(fill="x", padx=10, pady=6)
        tk.Button(b3, text=T("Measure each leg of the optical path"),
                  command=self._measure_D).pack(fill="x")
        self.lbl_D = tk.Label(b3, text="--", bg="#f4f2ee", justify="left",
                              font=("Courier New", 10))
        self.lbl_D.pack(anchor="w", pady=(4, 0))
        tk.Label(r, wraplength=290, justify="left", fg="#6a6254", bg="#f4f2ee",
                 text=T("Drag on the screen with the mouse to lay the ruler between "
                        "two minima. The ruler reads to 0.5 mm.")
                 ).pack(anchor="w", padx=12, pady=8)
        self.lbl_x = tk.Label(r, text="", bg="#f4f2ee", font=("Courier New", 11))
        self.lbl_x.pack(anchor="w", padx=12)
        self.c_diff.bind("<Button-1>", self._ruler_press)
        self.c_diff.bind("<B1-Motion>", self._ruler_drag)
        self._rul = None

    def _laser_toggle(self):
        if "laser" not in self.placed or not self.hung:
            return
        self.laser_on = not self.laser_on
        self.draw_diff()

    def _set_mirrors(self):
        n = self.mvar.get()
        if n >= 1 and "mirror1" not in self.placed:
            self.mvar.set(self.mirror_use); return
        if n >= 2 and "mirror2" not in self.placed:
            self.mvar.set(self.mirror_use); return
        self.mirror_use = n
        self.draw_diff()

    def legs(self):
        """the physical legs of the optical path, in metres"""
        last = self.sld_D.get() / 100.0
        if self.mirror_use == 0:
            return [last]
        if self.mirror_use == 1:
            return [0.260, last]
        return [0.260, 0.360, last]

    def D_total(self):
        return sum(self.legs())

    def _measure_D(self):
        if not self.laser_on:
            self.lbl_D.config(text=T("switch the laser on"))
            return
        txt = []
        for i, g in enumerate(self.legs()):
            r = round(g * 100.0 + self.rng.gauss(0.0, 0.25), 1)
            txt.append("D%d = %5.1f cm" % (i + 1, r))
        self.lbl_D.config(text="\n".join(txt))

    def _pattern(self, wpx):
        """x positions (px) of the diffraction minima on the screen"""
        d = self.th.d_stretched
        D = self.D_total()
        lam = LAMBDA_NM * 1e-9
        dx = lam * D / d                     # metre between minima
        self.px_per_m = wpx / (self.zoom.get() / 100.0)
        return dx * self.px_per_m

    def draw_diff(self):
        c = self.c_diff
        c.delete("all")
        w = c.winfo_width() or 700
        h = c.winfo_height() or 640
        c.create_rectangle(0, 0, w, h, fill="#101014", outline="")
        if not (self.hung and self.laser_on and "screen" in self.placed):
            c.create_text(w / 2, h / 2, fill="#5a5a64",
                          text=T("Hang the thread, place the screen, then switch "
                                 "the laser on."))
            return
        sx0, sx1 = 40, w - 40
        sy0, sy1 = 60, h - 120
        c.create_rectangle(sx0, sy0, sx1, sy1, fill="#f2efe6", outline="#b9b1a1")
        cy = (sy0 + sy1) / 2
        step = self._pattern(sx1 - sx0)
        cx = (sx0 + sx1) / 2
        # single-slit / wire pattern: minima at n*step, maxima at (n+1/2)*step
        n = 0
        while n < 60:
            n += 1
            off = (n + 0.5) * step
            if off > (sx1 - sx0) / 2:
                break
            u = math.pi * (n + 0.5)
            inten = (math.sin(u) / u) ** 2
            g = int(255 * min(1.0, inten * 7.0))
            col = "#%02x%02x%02x" % (255, 40 + g // 3, 40 + g // 3)
            r = max(1.0, step * 0.34)
            hh = 6 + 16 * inten ** 0.25
            for sgn in (-1, 1):
                x = cx + sgn * off
                c.create_oval(x - r, cy - hh, x + r, cy + hh, fill=col, outline="")
        c.create_oval(cx - step * 0.95, cy - 26, cx + step * 0.95, cy + 26,
                      fill="#ff5252", outline="")
        c.create_oval(cx - step * 0.55, cy - 20, cx + step * 0.55, cy + 20,
                      fill="#ffd0d0", outline="")
        c.create_text(w / 2, sy1 + 26, fill="#9a9aa4",
                      text=T("A4 screen") + "  -  " + T("view width") +
                           " %.1f cm" % self.zoom.get())
        if self._rul:
            x0, x1 = self._rul
            yr = cy + 46
            c.create_line(x0, yr - 22, x0, yr + 8, fill="#1b4fa0", width=2)
            c.create_line(x1, yr - 22, x1, yr + 8, fill="#1b4fa0", width=2)
            c.create_line(x0, yr, x1, yr, fill="#1b4fa0", width=2)
            mm = abs(x1 - x0) / self.px_per_m * 1000.0
            mm = round(mm * 2.0) / 2.0
            self.lbl_x.config(text="%.1f mm" % mm)

    def _ruler_press(self, e):
        self._rul = [e.x, e.x]
        self.draw_diff()

    def _ruler_drag(self, e):
        if self._rul:
            self._rul[1] = e.x
            self.draw_diff()

    # ---------------- short thread -------------------------------------
    def _build_short(self):
        f = self.tab_short
        self.c_short = tk.Canvas(f, bg="#fbfaf7", highlightthickness=0)
        self.c_short.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        r = tk.Frame(f, bg="#f4f2ee", width=320)
        r.pack(side="right", fill="y"); r.pack_propagate(False)
        b = tk.LabelFrame(r, text=T("Part C"), bg="#f4f2ee", padx=8, pady=8)
        b.pack(fill="x", padx=10, pady=12)
        tk.Button(b, text=T("Measure the short thread (unstretched)"),
                  command=self._meas_short0).pack(fill="x")
        self.lbl_s0 = tk.Label(b, text="--", bg="#f4f2ee", font=("Courier New", 11))
        self.lbl_s0.pack(anchor="w", pady=4)
        tk.Button(b, text=T("Transfer the mass-set and hang the short thread"),
                  command=self._mount_short, wraplength=280).pack(fill="x", pady=(6, 0))
        self.lbl_wait = tk.Label(b, text="", bg="#f4f2ee", fg="#6a6254")
        self.lbl_wait.pack(anchor="w")
        b2 = tk.LabelFrame(r, text=T("Part E"), bg="#f4f2ee", padx=8, pady=8)
        b2.pack(fill="x", padx=10, pady=6)
        tk.Button(b2, text=T("Measure the stretched short thread"),
                  command=self._meas_short).pack(fill="x")
        self.lbl_s1 = tk.Label(b2, text="--", bg="#f4f2ee", font=("Courier New", 11))
        self.lbl_s1.pack(anchor="w", pady=4)
        tk.Label(r, wraplength=290, justify="left", fg="#6a6254", bg="#f4f2ee",
                 text=T("The thread must hang for at least 30 minutes before the "
                        "strain is stationary. Use the time scale on the Bench tab.")
                 ).pack(anchor="w", padx=12, pady=10)

    def _meas_short0(self):
        v = self.th.l0_short - 0.010
        r = round(v * 1000.0 + self.rng.gauss(0.0, 0.6))
        self.lbl_s0.config(text="%.1f cm  (%s)" % (r / 10.0, T("between screw heads")))

    def _mount_short(self):
        if not self.hung:
            self.lbl_wait.config(text=T("finish Part A first"))
            return
        if self.short_mounted:
            return
        self.short_mounted = True
        self.t_short = 0.0

    def _meas_short(self):
        if not self.short_mounted:
            self.lbl_s1.config(text=T("not hung yet"))
            return
        v = self.th.len_short(self.t_short) - 0.010
        r = round(v * 1000.0 + self.rng.gauss(0.0, 0.6))
        self.lbl_s1.config(text="%.1f cm  (%s)" % (r / 10.0, T("between screw heads")))

    def draw_short(self):
        c = self.c_short
        c.delete("all")
        w = c.winfo_width() or 700
        h = c.winfo_height() or 640
        cx, top, base = w * 0.5, 70, h - 90
        c.create_rectangle(cx - 130, base, cx + 130, base + 14, fill="#8d8577", outline="")
        c.create_rectangle(cx - 96, top, cx - 80, base, fill="#a8a091", outline="")
        c.create_rectangle(cx - 96, top, cx + 40, top + 14, fill="#a8a091", outline="")
        if self.short_mounted:
            frac = self.th.len_short(self.t_short) / 0.60
            ybot = top + 14 + frac * (base - top - 90)
            c.create_line(cx - 20, top + 14, cx - 20, ybot, fill="#2f2a24", width=3)
            c.create_rectangle(cx - 40, ybot, cx, ybot + 44, fill="#9c9689",
                               outline="#4a443a")
            c.create_text(20, 20, anchor="nw", fill="#4a443a",
                          text=T("hanging for") + ": " + self._fmt(self.t_short))
        else:
            c.create_text(w / 2, h / 2, fill="#8a8274",
                          text=T("Transfer the mass-set to the short thread."))

    # ---------------- main loop ----------------------------------------
    def _tick(self):
        dt = 0.05 * self.spd.get()
        if self.hung:
            self.t_exp += dt
            if self.watch_run:
                self.watch_t += dt
            if self.short_mounted:
                self.t_short += dt
        elif self.watch_run:
            self.watch_t += dt

        if self.on_scale and "scale" in self.placed:
            if self.hung and not self.short_mounted:
                target = self.th.scale_reading_g(self.t_exp)
            elif self.short_mounted:
                target = 0.0
            else:
                target = self.th.mass * 1e3
        else:
            target = 0.0
        self.scale.update(target, dt)

        self.lbl_scale.config(text=self.scale.display())
        self.lbl_watch.config(text=self._fmt(self.watch_t))
        cur = self.nb.index(self.nb.select())
        if cur == 0:
            pass
        elif cur == 1:
            self.draw_bench()
        elif cur == 2:
            self.draw_diff()
        else:
            self.draw_short()
        self.after(50, self._tick)


if __name__ == "__main__":
    App().mainloop()
