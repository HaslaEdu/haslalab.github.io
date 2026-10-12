# -*- coding: utf-8 -*-
"""
=======================================================================
  17th Asian Physics Olympiad  (APhO 2016, Hong Kong)
  Experimental Problem E2 :  REFLECTION PHASE SHIFT OF METAL
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The bench shows only what the instruments show: the angular scale, the
  multimeter reading and the recorded numbers the student typed down.
  L, phi_s, the interference order and cos(theta) are never displayed.
* Screw positions are given as turn counts, never as the angle/offset produced.
* Hidden truths are randomised every session.
* Standard library only (tkinter).
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


# --------------------------------------------------------------------------
#  Physics core
# --------------------------------------------------------------------------
class Physics(object):
    LAM = 650e-9

    def __init__(self, seed=None):
        rng = random.Random(seed)
        self.seed = seed
        self.L = rng.uniform(3.40e-6, 4.60e-6)          # air-gap thickness
        self.phi_sn = rng.uniform(-0.85, -0.15)         # phi_s / 2pi
        self.phi_s = 2.0 * math.pi * self.phi_sn
        self.alpha = rng.uniform(0.50, 1.50)            # scale mis-alignment
        self.strip_v0 = rng.uniform(2.0, 6.0)           # upper Ti strip   [mm]
        self.strip_v1 = self.strip_v0 - 11.0            # lower Ti strip   [mm]
        self.p0 = rng.uniform(-1.6, 1.6)                # holder offset    [mm]
        self.q0 = rng.uniform(-1.6, 1.6)
        self.lat0 = rng.uniform(-2.0, 2.0)              # beam offset      [mm]
        self.sample_id = rng.randint(101, 399)
        self.nseed = rng.randint(0, 10 ** 6)

    # ---- true incidence angle from the scale reading ----------------------
    def theta_actual(self, theta_read_deg):
        return abs(theta_read_deg + self.alpha)

    # ---- ideal two-beam interference (Eq. 1) ------------------------------
    def raw_signal(self, theta_read_deg):
        th = math.radians(self.theta_actual(theta_read_deg))
        c = math.cos(th)
        k = 2.0 * math.pi / self.LAM
        V0 = 419.5 + 23.2 * (0.996 - c)
        A = 7.6 + 3.0 * (0.996 - c)
        return V0, A * math.cos(2.0 * k * self.L * c + self.phi_s)

    # ---- what the multimeter actually sees --------------------------------
    def voltage(self, theta_read, det_read, etalon_v, p, q, lat,
                spot_mm, laser_on):
        if not laser_on:
            return 0.4
        V0, mod = self.raw_signal(theta_read)
        th_a = math.radians(self.theta_actual(theta_read))
        # detector acceptance (flat top, then a smooth roll-off)
        d = abs(det_read - (2.0 * theta_read + self.alpha))
        if d <= 3.5:
            f_det = 1.0
        elif d >= 11.0:
            f_det = 0.0
        else:
            f_det = math.cos(math.pi / 2.0 * (d - 3.5) / 7.5) ** 2
        # beam must cross the centre of the rotary disk
        f_lat = math.exp(-((lat - self.lat0) / 1.7) ** 2)
        # the Ti strip must stay coaxial with the rotary disk
        walk = 2.0 * math.hypot(p - self.p0, q - self.q0) * math.sin(th_a)
        f_ax = math.exp(-(walk / 2.8) ** 2)
        # beam spot must be small compared with the Ti strip
        f_ap = 1.0 if spot_mm <= 1.2 else math.exp(-((spot_mm - 1.2) / 1.6) ** 2)
        # is the beam on one of the two Ti strips at all?
        w = max(math.exp(-((etalon_v - self.strip_v0) / 3.2) ** 4),
                math.exp(-((etalon_v - self.strip_v1) / 3.2) ** 4))
        sig = w * (V0 + mod) + (1.0 - w) * (0.24 * V0)
        v = sig * f_det * f_lat * f_ax * f_ap + 1.6
        # multimeter jitter, reproducible for a given setting
        h = (int(round(theta_read * 10)) * 7919 + self.nseed) & 0xFFFF
        v += ((h * 2654435761) % 1000 / 1000.0 - 0.5) * 0.8
        return v


# --------------------------------------------------------------------------
#  artwork
# --------------------------------------------------------------------------
def rr(cv, x0, y0, x1, y1, r, **kw):
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


def art_platform(cv, x, y, sc=1.0, tag=""):
    w, h = 150 * sc, 92 * sc
    cv.create_rectangle(x - w / 2, y - h / 2, x + w / 2, y + h / 2,
                        fill="#111417", outline="#3a4046", tags=tag)
    cv.create_rectangle(x - w / 2, y - h / 2, x - w / 2 + 8 * sc, y + h / 2,
                        fill="#c8ccd0", outline="#8b9096", tags=tag)
    cv.create_oval(x - 30 * sc, y - 30 * sc, x + 30 * sc, y + 30 * sc,
                   fill="#e8eef2", outline="#7c848c", tags=tag)
    cv.create_oval(x - 22 * sc, y - 22 * sc, x + 22 * sc, y + 22 * sc,
                   fill="#f6fbff", outline="#96a0a8", tags=tag)
    cv.create_rectangle(x + 48 * sc, y - 11 * sc, x + 66 * sc, y + 11 * sc,
                        fill="#9aa1a8", outline="#5c6167", tags=tag)
    cv.create_rectangle(x - 66 * sc, y - 9 * sc, x - 50 * sc, y + 9 * sc,
                        fill="#a52121", outline="#5c1010", tags=tag)


def art_laser(cv, x, y, sc=1.0, tag=""):
    cv.create_line(x - 34 * sc, y + 10 * sc, x - 6 * sc, y + 2 * sc,
                   smooth=True, width=3 * sc, fill="#101215", tags=tag)
    cv.create_rectangle(x - 8 * sc, y - 7 * sc, x + 26 * sc, y + 7 * sc,
                        fill="#17191c", outline="#44484d", tags=tag)
    cv.create_rectangle(x + 4 * sc, y - 7 * sc, x + 14 * sc, y + 7 * sc,
                        fill="#e0c23a", outline="#a08c22", tags=tag)
    cv.create_oval(x + 24 * sc, y - 4 * sc, x + 32 * sc, y + 4 * sc,
                   fill="#8c1616", outline="#511010", tags=tag)


def art_battery(cv, x, y, sc=1.0, tag=""):
    cv.create_rectangle(x - 20 * sc, y - 12 * sc, x + 20 * sc, y + 12 * sc,
                        fill="#15171a", outline="#42464b", tags=tag)
    for k in (-1, 1):
        cv.create_rectangle(x - 15 * sc, y + k * 5 * sc - 3 * sc,
                            x + 9 * sc, y + k * 5 * sc + 3 * sc,
                            fill="#b8912c", outline="#6d5518", tags=tag)
    cv.create_line(x + 20 * sc, y, x + 34 * sc, y - 8 * sc,
                   width=2 * sc, fill="#a52121", tags=tag)


def art_meter(cv, x, y, sc=1.0, tag=""):
    rr(cv, x - 22 * sc, y - 32 * sc, x + 22 * sc, y + 32 * sc, 5 * sc,
       fill="#a4231f", outline="#5e100e", tags=tag)
    cv.create_rectangle(x - 16 * sc, y - 26 * sc, x + 16 * sc, y - 8 * sc,
                        fill="#98a89a", outline="#3d4a3e", tags=tag)
    cv.create_oval(x - 13 * sc, y - 3 * sc, x + 13 * sc, y + 23 * sc,
                   fill="#1b1c1e", outline="#3d3f42", tags=tag)
    cv.create_line(x, y + 10 * sc, x, y - 1 * sc, fill="#e8e8e8",
                   width=2 * sc, tags=tag)


def art_leads(cv, x, y, sc=1.0, tag=""):
    cv.create_line(x - 30 * sc, y - 6 * sc, x - 4 * sc, y - 12 * sc,
                   x + 26 * sc, y - 4 * sc, smooth=True, width=2.4 * sc,
                   fill="#a52121", tags=tag)
    cv.create_line(x - 30 * sc, y + 8 * sc, x - 4 * sc, y + 14 * sc,
                   x + 26 * sc, y + 6 * sc, smooth=True, width=2.4 * sc,
                   fill="#101215", tags=tag)


def art_holder(cv, x, y, sc=1.0, tag=""):
    cv.create_polygon(x - 26 * sc, y + 14 * sc, x + 26 * sc, y + 14 * sc,
                      x + 20 * sc, y + 6 * sc, x - 32 * sc, y + 6 * sc,
                      fill="#dbe7ee", outline="#95a6b0", tags=tag)
    cv.create_rectangle(x - 24 * sc, y - 18 * sc, x + 18 * sc, y + 7 * sc,
                        fill="#e8f2f8", outline="#95a6b0", tags=tag)
    for k in (-1, 1):
        cv.create_line(x + k * 16 * sc - 4 * sc, y - 16 * sc,
                       x + k * 16 * sc + 4 * sc, y - 16 * sc,
                       x + k * 16 * sc + 4 * sc, y - 2 * sc,
                       width=2, fill="#3b4046", tags=tag)


def art_capscrews(cv, x, y, sc=1.0, tag=""):
    for k in (-1, 1):
        cv.create_oval(x + k * 12 * sc - 8 * sc, y - 8 * sc,
                       x + k * 12 * sc + 8 * sc, y + 8 * sc,
                       fill="#f4f5f7", outline="#a9aeb4", tags=tag)


def art_etalon(cv, x, y, sc=1.0, tag=""):
    cv.create_rectangle(x - 26 * sc, y - 20 * sc, x + 26 * sc, y + 20 * sc,
                        fill="#101215", outline="#9aa1a8", width=2, tags=tag)
    cv.create_rectangle(x - 15 * sc, y - 11 * sc, x + 15 * sc, y + 11 * sc,
                        fill="#cfe0ea", outline="#8fa3b0", tags=tag)
    cv.create_rectangle(x - 15 * sc, y - 5 * sc, x + 15 * sc, y + 1 * sc,
                        fill="#8d9296", outline="", tags=tag)


def art_driver(cv, x, y, sc=1.0, tag=""):
    cv.create_rectangle(x - 26 * sc, y - 7 * sc, x - 2 * sc, y + 7 * sc,
                        fill="#f2c21a", outline="#8d7208", tags=tag)
    cv.create_rectangle(x - 2 * sc, y - 2 * sc, x + 24 * sc, y + 2 * sc,
                        fill="#b9bfc5", outline="#7d8288", tags=tag)


def art_lamp(cv, x, y, sc=1.0, tag=""):
    cv.create_rectangle(x - 24 * sc, y + 10 * sc, x + 4 * sc, y + 18 * sc,
                        fill="#eceef1", outline="#a9aeb4", tags=tag)
    cv.create_line(x - 10 * sc, y + 10 * sc, x + 2 * sc, y - 6 * sc,
                   x + 18 * sc, y - 14 * sc, width=3 * sc, fill="#dfe3e8",
                   tags=tag)
    cv.create_rectangle(x + 8 * sc, y - 20 * sc, x + 30 * sc, y - 12 * sc,
                        fill="#ffffff", outline="#a9aeb4", tags=tag)


ART = {"platform": art_platform, "laser": art_laser, "battery": art_battery,
       "meter": art_meter, "leads": art_leads, "holder": art_holder,
       "capscrews": art_capscrews, "etalon": art_etalon,
       "driver": art_driver, "lamp": art_lamp}

PARTS = [
    ("platform",  ("[9] 광학 플랫폼", "[9] Optical platform"), []),
    ("laser",     ("[1] 레이저 다이오드", "[1] Laser diode"), ["platform"]),
    ("battery",   ("[2] 배터리 팩", "[2] Battery pack"), ["laser"]),
    ("meter",     ("[6] 디지털 멀티미터", "[6] Digital multimeter"), []),
    ("leads",     ("[5] 바나나 커넥터 전선", "[5] Banana leads"),
     ["meter", "platform"]),
    ("capscrews", ("[3] 흰색 마개 나사", "[3] White cap screws"), ["platform"]),
    ("holder",    ("[4] 시료 거치대 (클립 2개)", "[4] Sample holder (2 clips)"),
     ["capscrews"]),
    ("etalon",    ("[7] Ti 코팅 FP 에탈론", "[7] Ti-coated FP etalon"),
     ["holder"]),
    ("driver",    ("[8] 일자 드라이버", "[8] Flat-head driver"), ["laser"]),
    ("lamp",      ("[10] LED 램프", "[10] LED lamp"), []),
]

ZONES = {
    "platform":  (330, 330, 190, 120),
    "laser":     (500, 330, 82, 44),
    "battery":   (500, 420, 74, 40),
    "meter":     (120, 300, 60, 84),
    "leads":     (218, 300, 70, 40),
    "capscrews": (330, 330, 60, 30),
    "holder":    (330, 300, 70, 50),
    "etalon":    (330, 240, 62, 50),
    "driver":    (500, 500, 70, 34),
    "lamp":      (120, 150, 70, 50),
}


# --------------------------------------------------------------------------
#  Assembly tab
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
        self.tray = tk.Canvas(left, width=215, height=570, bg="#f2f3f5",
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
        self.scene = tk.Canvas(right, width=640, height=570, bg="#e9ebee",
                               highlightthickness=1,
                               highlightbackground="#c3c7cc")
        self.scene.pack(fill="both", expand=True)

        self.tray.bind("<ButtonPress-1>", self.on_press)
        self.tray.bind("<B1-Motion>", self.on_move)
        self.tray.bind("<ButtonRelease-1>", self.on_release)
        self.redraw()

    def redraw(self):
        self.tray.delete("all")
        y, self.slots = 44, []
        for key, lab, _ in PARTS:
            if key in self.placed:
                continue
            self.tray.create_rectangle(8, y - 30, 205, y + 30,
                                       fill="#ffffff", outline="#d3d7dc")
            ART[key](self.tray, 58, y, 0.58, tag="p_" + key)
            self.tray.create_text(112, y, text=T(*lab), width=150,
                                  font=("Helvetica", 8), anchor="w")
            self.slots.append((key, y))
            y += 66
        self.paint_scene()

    def paint_scene(self):
        cv = self.scene
        cv.delete("all")
        cv.create_text(320, 20, text=T("그림 13 ~ 15의 설치 구성",
                                       "Set-up of Figures 13 - 15"),
                       font=("Helvetica", 10, "bold"), fill="#4a5058")
        for key, (cx, cy, w, h) in ZONES.items():
            if key in self.placed:
                continue
            cv.create_rectangle(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2,
                                dash=(4, 3), outline="#b0b5bb")
        for key in ["platform", "capscrews", "holder", "etalon", "laser",
                    "battery", "meter", "leads", "driver", "lamp"]:
            if key in self.placed:
                cx, cy, w, h = ZONES[key]
                ART[key](cv, cx, cy, 1.0)
        if len(self.placed) == len(PARTS):
            cv.create_text(320, 548, fill="#14532d",
                           font=("Helvetica", 11, "bold"),
                           text=T("조립 완료 — '실험대' 탭으로 이동하시오.",
                                  "Assembly complete — go to the Bench tab."))

    def on_press(self, ev):
        self.drag = None
        for key, y in self.slots:
            if abs(ev.y - y) <= 30:
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
        cx, cy, w, h = ZONES[key]
        self.msg.config(text="")
        if not (abs(x - cx) < w / 2 + 28 and abs(y - cy) < h / 2 + 28):
            self.msg.config(text=T("그 위치에는 놓을 수 없습니다.",
                                   "That part does not belong there."))
            self.redraw()
            return
        needs = dict((k, n) for k, _, n in PARTS)[key]
        miss = [n for n in needs if n not in self.placed]
        if miss:
            names = ", ".join(T(*dict((k, l) for k, l, _ in PARTS)[m])
                              for m in miss)
            self.msg.config(text=T("먼저 설치해야 합니다: ",
                                   "Install first: ") + names)
            self.redraw()
            return
        self.placed.add(key)
        self.app.on_assembly_change(self.placed)
        self.redraw()


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    RANGES = [("OFF", None), ("200 mV", 0.2), ("2 V", 2.0), ("20 V", 20.0)]

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph

        self.laser_on = tk.BooleanVar(value=False)
        self.aperture = tk.DoubleVar(value=2.4)
        self.turnLat = tk.DoubleVar(value=25.0)     # laser lateral screw
        self.turnV = tk.DoubleVar(value=25.0)       # etalon vertical position
        self.turnP = tk.DoubleVar(value=25.0)       # holder cap screw 1
        self.turnQ = tk.DoubleVar(value=25.0)       # holder cap screw 2
        self.theta = tk.DoubleVar(value=0.0)        # rotary disk reading
        self.det = tk.DoubleVar(value=0.0)          # detector arm reading
        self.rng_i = tk.IntVar(value=0)
        self.rows = []

        self.build()
        self.refresh()

    # ---- mapped quantities (never shown to the student) -------------------
    def lat_mm(self):
        return (self.turnLat.get() - 25.0) * 0.25

    def etalon_v(self):
        return (self.turnV.get() - 25.0) * 0.5

    def p_mm(self):
        return (self.turnP.get() - 25.0) * 0.2

    def q_mm(self):
        return (self.turnQ.get() - 25.0) * 0.2

    def spot_mm(self):
        return self.aperture.get()

    def ready(self):
        need = {"platform", "laser", "battery", "meter", "leads",
                "capscrews", "holder", "etalon"}
        return need <= self.app.placed

    def volts(self):
        if not self.ready():
            return None
        return self.ph.voltage(self.theta.get(), self.det.get(),
                               self.etalon_v(), self.p_mm(), self.q_mm(),
                               self.lat_mm(), self.spot_mm(),
                               self.laser_on.get())

    # ---- UI ---------------------------------------------------------------
    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        mid = ttk.Frame(self)
        mid.pack(side="left", fill="both", expand=True, padx=4, pady=6)
        rgt = ttk.Frame(self)
        rgt.pack(side="left", fill="y", padx=6, pady=6)

        def sec(txt):
            ttk.Label(ctl, text=txt, font=("Helvetica", 10, "bold")
                      ).pack(anchor="w", pady=(9, 2))

        sec(T("레이저 다이오드", "Laser diode"))
        ttk.Checkbutton(ctl, text=T("배터리 팩 연결 / ON",
                                    "Battery pack connected / ON"),
                        variable=self.laser_on,
                        command=self.refresh).pack(anchor="w")
        self.ap_row = ttk.Frame(ctl)
        self.ap_row.pack(anchor="w", fill="x")
        ttk.Label(self.ap_row, text=T("조리개 (드라이버)",
                                      "Aperture (driver)")).pack(anchor="w")
        ttk.Scale(self.ap_row, from_=0.4, to=4.0, variable=self.aperture,
                  orient="horizontal", length=195,
                  command=lambda e: self.refresh()).pack(anchor="w")

        sec(T("정렬 나사 (회전수)", "Alignment screws (turns)"))
        self.mk_screw(ctl, T("레이저 가로", "laser lat."), self.turnLat,
                      0, 50, 0.1, "Lat")
        self.mk_screw(ctl, T("에탈론 높이", "etalon height"), self.turnV,
                      0, 50, 0.2, "V")
        self.mk_screw(ctl, T("마개 나사 P", "cap screw P"), self.turnP,
                      0, 50, 0.2, "P")
        self.mk_screw(ctl, T("마개 나사 Q", "cap screw Q"), self.turnQ,
                      0, 50, 0.2, "Q")

        sec(T("회전 원판 (시료 회전)", "Rotary disk (sample)"))
        row = ttk.Frame(ctl)
        row.pack(anchor="w")
        for d in (-5, -1, -0.5, 0.5, 1, 5):
            ttk.Button(row, text=("%+g" % d), width=4,
                       command=lambda dd=d: self.bump(self.theta, dd,
                                                      -85, 85)).pack(side="left")
        self.th_lbl = ttk.Label(ctl, text="", font=("Consolas", 12))
        self.th_lbl.pack(anchor="w")

        sec(T("광검출기 팔", "Photo-detector arm"))
        row = ttk.Frame(ctl)
        row.pack(anchor="w")
        for d in (-5, -1, -0.5, 0.5, 1, 5):
            ttk.Button(row, text=("%+g" % d), width=4,
                       command=lambda dd=d: self.bump(self.det, dd,
                                                      -175, 175)).pack(side="left")
        ttk.Button(ctl, text=T("검출기를 약 2\u03b8 위치로 옮김",
                               "move detector to about 2\u03b8"),
                   command=self.to_2theta).pack(anchor="w", fill="x", pady=2)
        self.det_lbl = ttk.Label(ctl, text="", font=("Consolas", 12))
        self.det_lbl.pack(anchor="w")

        sec(T("멀티미터 손잡이", "Multimeter knob"))
        for i, (name, _) in enumerate(self.RANGES):
            ttk.Radiobutton(ctl, text=("DCV  " + name) if i else name,
                            value=i, variable=self.rng_i,
                            command=self.refresh).pack(anchor="w")

        self.warn = ttk.Label(ctl, text="", wraplength=215,
                              foreground="#8a1b1b")
        self.warn.pack(anchor="w", pady=6)

        # ---------------- middle: top view + multimeter --------------------
        ttk.Label(mid, text=T("평면도 (광학 플랫폼)",
                              "Top view (optical platform)"),
                  font=("Helvetica", 9, "bold")).pack(anchor="w")
        self.cv_top = tk.Canvas(mid, width=430, height=372, bg="#15181b",
                                highlightthickness=0)
        self.cv_top.pack()
        ttk.Label(mid, text=T("에탈론 정면 (빔이 오는 쪽에서 본 모습)",
                              "Etalon seen from the beam side"),
                  font=("Helvetica", 9, "bold")).pack(anchor="w", pady=(6, 0))
        self.cv_front = tk.Canvas(mid, width=430, height=132, bg="#1b1e21",
                                  highlightthickness=0)
        self.cv_front.pack()
        ttk.Label(mid, text=T("디지털 멀티미터", "Digital multimeter"),
                  font=("Helvetica", 9, "bold")).pack(anchor="w", pady=(6, 0))
        self.cv_dmm = tk.Canvas(mid, width=430, height=118, bg="#8f1c19",
                                highlightthickness=0)
        self.cv_dmm.pack()

        # ---------------- right: notebook ---------------------------------
        ttk.Label(rgt, text=T("측정 기록", "Recorded readings"),
                  font=("Helvetica", 10, "bold")).pack(anchor="w")
        row = ttk.Frame(rgt)
        row.pack(anchor="w", pady=2)
        ttk.Button(row, text=T("기록", "record"), width=8,
                   command=self.record).pack(side="left")
        ttk.Button(row, text=T("기록 후 \u03b8 -0.5\u00b0", "record, \u03b8 -0.5\u00b0"),
                   command=lambda: self.record(-0.5)).pack(side="left")
        row2 = ttk.Frame(rgt)
        row2.pack(anchor="w", pady=2)
        ttk.Button(row2, text=T("마지막 삭제", "delete last"),
                   command=self.del_last).pack(side="left")
        ttk.Button(row2, text=T("전체 삭제", "clear all"),
                   command=self.clear).pack(side="left")
        ttk.Button(row2, text=T("텍스트로 보기", "as text"),
                   command=self.as_text).pack(side="left")
        self.lst = tk.Listbox(rgt, width=26, height=30,
                              font=("Consolas", 10))
        self.lst.pack(fill="y", expand=True)

    def mk_screw(self, parent, name, var, lo, hi, step, tag):
        row = ttk.Frame(parent)
        row.pack(anchor="w", fill="x")
        ttk.Label(row, text=name, width=12).pack(side="left")
        ttk.Button(row, text="-", width=2,
                   command=lambda: self.bump(var, -step, lo, hi)).pack(side="left")
        lbl = ttk.Label(row, text="", width=7, font=("Consolas", 10))
        lbl.pack(side="left")
        ttk.Button(row, text="+", width=2,
                   command=lambda: self.bump(var, step, lo, hi)).pack(side="left")
        setattr(self, "lbl_" + tag, lbl)

    def bump(self, var, d, lo, hi):
        var.set(max(lo, min(hi, round(var.get() + d, 4))))
        self.refresh()

    def to_2theta(self):
        self.det.set(round(2.0 * self.theta.get(), 2))
        self.refresh()

    # ---- notebook ---------------------------------------------------------
    def record(self, step=0.0):
        v = self.volts()
        if v is None or self.RANGES[self.rng_i.get()][1] is None:
            self.warn.config(text=T("멀티미터가 꺼져 있습니다.",
                                    "The multimeter knob is at OFF."))
            return
        txt = self.dmm_text()
        self.rows.append((self.theta.get(), txt))
        self.lst.insert("end", "%7.1f   %s" % (self.theta.get(), txt))
        self.lst.see("end")
        if step:
            self.bump(self.theta, step, -85, 85)
        else:
            self.refresh()

    def del_last(self):
        if self.rows:
            self.rows.pop()
            self.lst.delete("end")

    def clear(self):
        self.rows = []
        self.lst.delete(0, "end")

    def as_text(self):
        w = tk.Toplevel(self)
        w.title(T("측정 기록", "Recorded readings"))
        t = tk.Text(w, width=34, height=34, font=("Consolas", 10))
        t.pack(fill="both", expand=True)
        t.insert("1.0", T("theta(deg)   판독값\n", "theta(deg)   reading\n"))
        for th, v in self.rows:
            t.insert("end", "%8.1f   %s\n" % (th, v))

    # ---- multimeter -------------------------------------------------------
    def dmm_text(self):
        name, full = self.RANGES[self.rng_i.get()]
        if full is None:
            return ""
        v = self.volts()
        if v is None:
            return ""
        volt = v / 1000.0
        if volt > full:
            return " 1 ."
        if full == 0.2:
            return "%6.1f" % (volt * 1000.0)
        if full == 2.0:
            return "%6.3f" % volt
        return "%6.2f" % volt

    def draw_dmm(self):
        cv = self.cv_dmm
        cv.delete("all")
        cv.create_rectangle(4, 4, 426, 114, fill="#a4231f", outline="#5e100e")
        cv.create_rectangle(58, 16, 372, 102, fill="#9fb3a2", outline="#3d4a3e")
        name, full = self.RANGES[self.rng_i.get()]
        txt = self.dmm_text()
        cv.create_text(215, 56, text=txt, font=("Consolas", 38, "bold"),
                       fill="#14201a")
        unit = "" if full is None else ("mV" if full == 0.2 else "V")
        cv.create_text(347, 88, text=unit, font=("Helvetica", 15, "bold"),
                       fill="#14201a")
        cv.create_text(92, 88, text="DC" if full is not None else "",
                       font=("Helvetica", 12), fill="#14201a")
        cv.create_text(28, 58, text=name, font=("Helvetica", 9, "bold"),
                       fill="#ffffff", angle=90)

    # ---- top view ---------------------------------------------------------
    def draw_top(self):
        cv = self.cv_top
        cv.delete("all")
        if "platform" not in self.app.placed:
            cv.create_text(215, 200, text=T("플랫폼 미설치", "no platform"),
                           fill="#6b7075")
            return
        cx, cy, R = 215.0, 196.0, 122.0
        cv.create_rectangle(12, 36, 418, 362, fill="#111417", outline="#33383d")
        cv.create_oval(cx - R, cy - R, cx + R, cy + R,
                       fill="#e9eef2", outline="#7c848c")
        for a in range(0, 360, 5):
            rad = math.radians(a)
            l = 9 if a % 30 == 0 else 4
            sx, sy = math.sin(rad), math.cos(rad)
            cv.create_line(cx + (R - l) * sx, cy + (R - l) * sy,
                           cx + R * sx, cy + R * sy, fill="#5b6167")
        for a in range(0, 360, 30):
            rad = math.radians(a)
            cv.create_text(cx + (R - 20) * math.sin(rad),
                           cy + (R - 20) * math.cos(rad), text=str(a),
                           font=("Helvetica", 7), fill="#3f454b")
        cv.create_oval(cx - 92, cy - 92, cx + 92, cy + 92,
                       fill="#f7fbff", outline="#9aa2aa")
        # laser (0 deg side, bottom)  and its beam
        cv.create_rectangle(cx - 16, cy + 142, cx + 16, cy + 164,
                            fill="#9aa1a8", outline="#5c6167")
        lat = self.lat_mm() * 3.0
        beam_on = self.laser_on.get() and "laser" in self.app.placed \
            and "battery" in self.app.placed
        # sample holder + etalon
        th = self.theta.get()
        if "holder" in self.app.placed:
            rad = math.radians(th)
            c, s = math.cos(rad), math.sin(rad)
            pts = []
            for dx, dz in ((-46, -3), (46, -3), (46, 3), (-46, 3)):
                X = dx * c - dz * s
                Z = dx * s + dz * c
                pts += [cx + X, cy - Z]
            cv.create_polygon(pts, fill="#dbe7ee", outline="#8fa3b0")
            if "etalon" in self.app.placed:
                pts = []
                for dx, dz in ((-30, -1.5), (30, -1.5), (30, 1.5), (-30, 1.5)):
                    X = dx * c - dz * s
                    Z = dx * s + dz * c
                    pts += [cx + X, cy - Z]
                cv.create_polygon(pts, fill="#7f868c", outline="#c8ced3")
        # detector arm
        dd = math.radians(180.0 - self.det.get())
        dx_, dz_ = math.sin(dd), math.cos(dd)
        px, py = cx + (R - 8) * dx_, cy + (R - 8) * dz_
        cv.create_line(cx, cy, px, py, fill="#3a4046", width=3)
        cv.create_rectangle(px - 9, py - 9, px + 9, py + 9,
                            fill="#22262a", outline="#8b9096")
        cv.create_oval(px - 4, py - 4, px + 4, py + 4, fill="#101215",
                       outline="#6b7075")
        if beam_on:
            cv.create_line(cx + lat, cy + 164, cx + lat, cy,
                           fill="#e33", width=2)
            if "etalon" in self.app.placed and abs(lat) < 24:
                a_out = math.radians(180.0 - (2.0 * th + self.ph.alpha))
                ox, oz = math.sin(a_out), math.cos(a_out)
                cv.create_line(cx, cy, cx + (R - 8) * ox, cy + (R - 8) * oz,
                               fill="#f55", width=2)
            else:
                cv.create_line(cx + lat, cy, cx + lat, cy - (R - 8),
                               fill="#e33", width=2)
        cv.create_text(215, 22, fill="#98a0a8", font=("Helvetica", 8),
                       text=T("고정 각도 눈금 : 0\u00b0 쪽에 레이저, 180\u00b0 쪽이 기준",
                              "fixed angular scale: laser at 0 deg, 180 deg "
                              "opposite"))

    # ---- front view of the etalon -----------------------------------------
    def draw_front(self):
        cv = self.cv_front
        cv.delete("all")
        if "etalon" not in self.app.placed:
            cv.create_text(215, 65, text=T("에탈론 미장착", "no etalon"),
                           fill="#6b7075")
            return
        ph = self.ph
        beam_y, pxmm, hh = 65.0, 2.4, 36.0
        mid_v = 0.5 * (ph.strip_v0 + ph.strip_v1)
        body_c = beam_y - (self.etalon_v() - mid_v) * pxmm
        cv.create_rectangle(122, body_c - hh, 328, body_c + hh,
                            fill="#cfe0ea", outline="#8fa3b0")
        for v in (ph.strip_v0, ph.strip_v1):
            yc = beam_y - (self.etalon_v() - v) * pxmm
            cv.create_rectangle(122, yc - 7, 328, yc + 7,
                                fill="#8d9296", outline="#b6bcc1")
        cv.create_text(300, body_c - hh + 12, text="#%d" % ph.sample_id,
                       font=("Helvetica", 9, "bold"), fill="#2a3138")
        for cxp in (140, 310):                       # the two paper clips
            cv.create_line(cxp - 7, body_c - hh - 5, cxp + 7, body_c - hh - 5,
                           cxp + 7, body_c - hh + 16, cxp - 5,
                           body_c - hh + 16, width=2, fill="#3b4046")
        if self.laser_on.get() and "laser" in self.app.placed \
                and "battery" in self.app.placed:
            r = max(1.6, self.spot_mm() * 0.5 * pxmm)
            x = 225 + self.lat_mm() * pxmm
            cv.create_oval(x - r * 2.4, beam_y - r * 2.4, x + r * 2.4,
                           beam_y + r * 2.4, fill="#7a1414", outline="")
            cv.create_oval(x - r, beam_y - r, x + r, beam_y + r,
                           fill="#ff6060", outline="")
        cv.create_text(66, 65, text=T("Ti 띠 2개", "two Ti strips"),
                       fill="#98a0a8", font=("Helvetica", 8))

    # ---- refresh ----------------------------------------------------------
    def refresh(self):
        st_ap = "normal" if "driver" in self.app.placed else "disabled"
        for w in self.ap_row.winfo_children():
            try:
                w.configure(state=st_ap)
            except tk.TclError:
                pass
        for tag, var in (("Lat", self.turnLat), ("V", self.turnV),
                         ("P", self.turnP), ("Q", self.turnQ)):
            getattr(self, "lbl_" + tag).config(text="%5.1f" % var.get())
        self.th_lbl.config(text=T("각도 눈금  ", "angular scale  ")
                           + "\u03b8 = %+6.1f\u00b0" % self.theta.get())
        self.det_lbl.config(text=T("검출기 눈금 ", "detector scale ")
                            + "%+6.1f\u00b0" % self.det.get())
        if not self.ready():
            self.warn.config(text=T("장치 조립이 끝나지 않았습니다.",
                                    "The set-up is not complete yet."))
        else:
            self.warn.config(text="")
        self.draw_top()
        self.draw_front()
        self.draw_dmm()


# --------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.ph = Physics(seed)
        self.title(T("APhO 2016 실험 E2 — 금속의 반사 위상 변화   [시료 #%d]"
                     % self.ph.sample_id,
                     "APhO 2016 Experiment E2 — Reflection phase shift of a "
                     "metal   [sample #%d]" % self.ph.sample_id))
        self.geometry("1330x760")
        self.placed = set()
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_asm = AssemblyTab(nb, self)
        self.tab_bench = BenchTab(nb, self)
        nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.tab_bench, text=T(" 실험대 ", " Bench "))

    def on_assembly_change(self, placed):
        self.placed = set(placed)
        self.tab_bench.refresh()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
