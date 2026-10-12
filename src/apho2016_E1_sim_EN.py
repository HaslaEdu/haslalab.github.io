# -*- coding: utf-8 -*-
"""
=======================================================================
  17th Asian Physics Olympiad  (APhO 2016, Hong Kong)
  Experimental Problem E1 :  REFLECTED OPTICAL DIFFRACTION PATTERNS FROM 1D STRUCTURES
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* Only what a real instrument / a real sheet of paper would show is displayed.
  No derived physical quantity (theta, a, b, phi*, ...) is ever printed by the UI.
* Screws are labelled by turn count, never by the angle they produce.
* Hidden true parameters are randomised every session.
* Standard library only (tkinter).
"""

import math
import random
import tkinter as tk
from tkinter import ttk, messagebox

LANG = "en"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


# --------------------------------------------------------------------------
#  Physics core
# --------------------------------------------------------------------------
class Physics(object):
    """Forward model of the APhO-2016 E1 apparatus."""

    D = 0.150            # observation board  <-  rotary-disk centre   [m]
    L0 = 0.120           # laser diode aperture <- rotary-disk centre  [m]
    LAM = 650e-9         # laser wavelength                            [m]
    SAMPLE_HALF = 0.0075  # sample is 1.5 cm x 1.5 cm

    def __init__(self, seed=None):
        rng = random.Random(seed)
        self.seed = seed
        # ---- hidden truths -------------------------------------------------
        self.h0 = rng.uniform(0.0520, 0.0580)      # zero-order mark height [m]
        self.theta = math.atan(self.h0 / self.D)   # nominal grazing angle
        self.a3 = rng.uniform(9.6e-6, 11.4e-6)     # sample 3 grating constant
        self.b5 = rng.uniform(20.5e-6, 23.5e-6)    # sample 5 pre-made spacing
        self.phi_star = math.radians(rng.uniform(18.0, 30.0))   # sample 4 tilt
        self.a_znse = rng.uniform(3.85e-10, 4.15e-10)           # ZnSe planes
        # RHEED (part G) conditions are fixed by the problem sheet
        self.V_gun = 13000.0
        self.D_rheed = 0.26

    # ---- electron wavelength (Eq. 6) ---------------------------------------
    @property
    def lam_e(self):
        V = self.V_gun
        return 12.247e-10 / math.sqrt(V * (1.0 + 1e-6 * V))

    @property
    def dx_rheed(self):
        return self.D_rheed * self.lam_e / self.a_znse

    # ---- beam --------------------------------------------------------------
    def beam_hit(self, yL, tau, xL, psi):
        """yL,xL in m ; tau,psi in rad.  Returns (H, dirvec) or None."""
        if tau <= 1e-4:
            return None
        d = (math.sin(psi) * math.cos(tau), -math.sin(tau),
             math.cos(psi) * math.cos(tau))
        s = yL / math.sin(tau)
        H = (xL + s * d[0], 0.0, -self.L0 + s * d[2])
        return H, d

    def on_sample(self, H):
        return (abs(H[0]) <= self.SAMPLE_HALF and
                abs(H[2]) <= self.SAMPLE_HALF)

    # ---- diffracted direction in the beam frame ----------------------------
    @staticmethod
    def u_vec(ctau, t, s, phi):
        """t = m*lam/a  (scratch / grating),  s = n*lam/b (pre-made grooves),
        phi = groove azimuth measured from the beam's horizontal projection."""
        ux = t * math.cos(phi) - s * math.sin(phi)
        uz = ctau - t * math.sin(phi) - s * math.cos(phi)
        if uz <= 1e-6:
            return None
        q = ux * ux + uz * uz
        if q >= 1.0:
            return None
        return (ux, math.sqrt(1.0 - q), uz)

    def to_board(self, H, psi, u):
        """beam-frame direction -> (X, Y) on the observation board [m]."""
        ux, uy, uz = u
        c, s = math.cos(psi), math.sin(psi)
        lx = ux * c + uz * s
        lz = -ux * s + uz * c
        if lz <= 1e-6:
            return None
        dz = self.D - H[2]
        if dz <= 0.0:
            return None
        return (H[0] + dz * lx / lz, dz * uy / lz)

    # ---- full pattern ------------------------------------------------------
    def pattern(self, sample, phi_disk_deg, yL, tau, xL, psi):
        """Returns list of items:
              ('dot', X, Y, bright)
              ('poly', [(X, Y, bright), ...])
        Coordinates in metres on the observation board."""
        hit = self.beam_hit(yL, tau, xL, psi)
        if hit is None:
            return []
        H, _ = hit
        if sample == 0 or not self.on_sample(H):
            return []
        ctau = math.cos(tau)
        phi = math.radians(phi_disk_deg) - psi
        if sample == 4:
            phi += self.phi_star
        out = []

        def push_dot(t, s, bright):
            u = self.u_vec(ctau, t, s, phi)
            if u is None:
                return
            p = self.to_board(H, psi, u)
            if p:
                out.append(('dot', p[0], p[1], bright))

        def arc(s, bright0, npts=1400):
            seg, prev_ok = [], False
            for i in range(npts + 1):
                t = -1.2 + 2.4 * i / npts
                u = self.u_vec(ctau, t, s, phi)
                ok = u is not None
                if ok:
                    p = self.to_board(H, psi, u)
                    ok = p is not None
                if ok:
                    b = bright0 * (0.45 + 0.55 * u[2]) * math.exp(-(t / 0.85) ** 2)
                    seg.append((p[0], p[1], b))
                    prev_ok = True
                elif prev_ok:
                    if len(seg) > 1:
                        out.append(('poly', seg))
                    seg, prev_ok = [], False
            if len(seg) > 1:
                out.append(('poly', seg))

        if sample == 1:                                   # plane mirror
            push_dot(0.0, 0.0, 1.0)
        elif sample in (2, 4):                            # non-uniform scratches
            arc(0.0, 1.0)
            push_dot(0.0, 0.0, 1.0)
        elif sample == 3:                                 # regular grating
            for m in range(-22, 23):
                b = math.exp(-(m / 9.0) ** 2)
                push_dot(m * self.LAM / self.a3, 0.0, 0.35 + 0.65 * b)
        elif sample == 5:                                 # cross structure
            for n in range(-9, 10):
                b0 = 0.30 + 0.70 * math.exp(-(n / 3.2) ** 2)
                arc(n * self.LAM / self.b5, b0)
            push_dot(0.0, 0.0, 1.0)
        return out


# --------------------------------------------------------------------------
#  small drawing helpers
# --------------------------------------------------------------------------
def rcol(b):
    b = max(0.0, min(1.0, b))
    r = int(95 + 160 * b)
    g = int(255 * max(0.0, b - 0.72) * 2.6)
    bl = int(255 * max(0.0, b - 0.86) * 3.4)
    return "#%02x%02x%02x" % (min(r, 255), min(g, 255), min(bl, 255))


def rr(cv, x0, y0, x1, y1, r, **kw):
    """rounded rectangle"""
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


# --------------------------------------------------------------------------
#  part artwork  (drawn from the photographs in the problem sheet)
# --------------------------------------------------------------------------
def art_platform(cv, x, y, sc=1.0, tag=""):
    """optical platform, perspective-free top view icon"""
    w, h = 150 * sc, 92 * sc
    cv.create_rectangle(x - w / 2, y - h / 2, x + w / 2, y + h / 2,
                        fill="#111417", outline="#3a4046", tags=tag)
    cv.create_rectangle(x - w / 2, y - h / 2, x - w / 2 + 8 * sc, y + h / 2,
                        fill="#c8ccd0", outline="#8b9096", tags=tag)
    cv.create_oval(x - 26 * sc, y - 26 * sc, x + 26 * sc, y + 26 * sc,
                   fill="#e8eef2", outline="#7c848c", tags=tag)
    cv.create_oval(x - 19 * sc, y - 19 * sc, x + 19 * sc, y + 19 * sc,
                   fill="#f6fbff", outline="#96a0a8", tags=tag)
    cv.create_rectangle(x + 46 * sc, y - 12 * sc, x + 66 * sc, y + 12 * sc,
                        fill="#9aa1a8", outline="#5c6167", tags=tag)


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
    cv.create_rectangle(x - 14 * sc, y - 6 * sc, x + 6 * sc, y + 6 * sc,
                        fill="#2a2d31", outline="", tags=tag)
    cv.create_line(x + 20 * sc, y, x + 34 * sc, y - 8 * sc,
                   width=2 * sc, fill="#a52121", tags=tag)
    cv.create_line(x + 20 * sc, y + 3 * sc, x + 34 * sc, y - 3 * sc,
                   width=2 * sc, fill="#101215", tags=tag)


def art_board(cv, x, y, sc=1.0, tag=""):
    w, h = 62 * sc, 84 * sc
    rr(cv, x - w / 2, y - h / 2, x + w / 2, y + h / 2, 5 * sc,
       fill="#0d0f11", outline="#3b4046", tags=tag)
    cv.create_rectangle(x - 14 * sc, y - h / 2 - 4 * sc, x + 14 * sc,
                        y - h / 2 + 8 * sc, fill="#b8bdc2",
                        outline="#6d7278", tags=tag)


def art_screws(cv, x, y, sc=1.0, tag=""):
    for k in (-1, 0, 1):
        cx = x + k * 13 * sc
        cv.create_oval(cx - 5 * sc, y - 5 * sc, cx + 5 * sc, y + 5 * sc,
                       fill="#2c2f33", outline="#6d7278", tags=tag)
        cv.create_line(cx - 3 * sc, y, cx + 3 * sc, y, fill="#9aa1a8", tags=tag)
        cv.create_rectangle(cx - 2 * sc, y + 5 * sc, cx + 2 * sc, y + 15 * sc,
                            fill="#8b9096", outline="", tags=tag)


def art_pinhole(cv, x, y, sc=1.0, tag=""):
    cv.create_oval(x - 17 * sc, y - 17 * sc, x + 17 * sc, y + 17 * sc,
                   fill="#232629", outline="#4b5055", tags=tag)
    cv.create_oval(x - 3 * sc, y - 3 * sc, x + 3 * sc, y + 3 * sc,
                   fill="#000000", outline="#6b7075", tags=tag)


def art_driver(cv, x, y, sc=1.0, tag=""):
    cv.create_rectangle(x - 26 * sc, y - 7 * sc, x - 2 * sc, y + 7 * sc,
                        fill="#f2c21a", outline="#8d7208", tags=tag)
    cv.create_rectangle(x - 22 * sc, y - 7 * sc, x - 16 * sc, y + 7 * sc,
                        fill="#26282b", outline="", tags=tag)
    cv.create_rectangle(x - 2 * sc, y - 2 * sc, x + 24 * sc, y + 2 * sc,
                        fill="#b9bfc5", outline="#7d8288", tags=tag)


def art_samplebox(cv, x, y, sc=1.0, tag=""):
    cv.create_rectangle(x - 26 * sc, y - 20 * sc, x + 26 * sc, y + 20 * sc,
                        fill="#101215", outline="#9aa1a8", width=2, tags=tag)
    cv.create_rectangle(x - 18 * sc, y - 6 * sc, x + 18 * sc, y + 6 * sc,
                        fill="#a51f1f", outline="", tags=tag)
    cv.create_text(x, y, text="Sample Box", fill="#ffffff",
                   font=("Helvetica", int(6 * sc)), tags=tag)


def art_sheet(cv, x, y, sc=1.0, tag="", grid=False):
    w, h = 44 * sc, 60 * sc
    cv.create_rectangle(x - w / 2, y - h / 2, x + w / 2, y + h / 2,
                        fill="#f6f7f2" if not grid else "#eef7ef",
                        outline="#9aa1a8", tags=tag)
    if grid:
        for i in range(1, 8):
            cv.create_line(x - w / 2, y - h / 2 + i * h / 8,
                           x + w / 2, y - h / 2 + i * h / 8,
                           fill="#a9d3b0", tags=tag)
            cv.create_line(x - w / 2 + i * w / 8, y - h / 2,
                           x - w / 2 + i * w / 8, y + h / 2,
                           fill="#a9d3b0", tags=tag)
    else:
        cv.create_line(x, y - h / 2 + 4, x, y + h / 2 - 4,
                       fill="#8d9298", tags=tag)
        cv.create_line(x - w / 2 + 4, y + h / 4, x + w / 2 - 4, y + h / 4,
                       fill="#8d9298", tags=tag)


def art_ruler(cv, x, y, sc=1.0, tag=""):
    cv.create_rectangle(x - 40 * sc, y - 7 * sc, x + 40 * sc, y + 7 * sc,
                        fill="#d7e9f6", outline="#7d9bb0", tags=tag)
    for i in range(-7, 8):
        cv.create_line(x + i * 5 * sc, y - 7 * sc, x + i * 5 * sc,
                       y - 1 * sc, fill="#3d566b", tags=tag)


def art_clips(cv, x, y, sc=1.0, tag=""):
    for k in (-1, 1):
        cx = x + k * 12 * sc
        cv.create_line(cx - 6 * sc, y - 8 * sc, cx + 6 * sc, y - 8 * sc,
                       cx + 6 * sc, y + 8 * sc, cx - 4 * sc, y + 8 * sc,
                       cx - 4 * sc, y - 4 * sc, width=2, fill="#9aa1a8",
                       tags=tag)


ART = {
    "platform": art_platform, "laser": art_laser, "battery": art_battery,
    "board": art_board, "screws": art_screws, "pinhole": art_pinhole,
    "driver": art_driver, "samplebox": art_samplebox, "ruler": art_ruler,
    "clips": art_clips,
}


# --------------------------------------------------------------------------
#  Assembly tab
# --------------------------------------------------------------------------
PARTS = [
    # key,        label(ko/en),                                needs
    ("platform",  ("[4] 광학 플랫폼", "[4] Optical platform"),  []),
    ("board",     ("[10] 관찰판", "[10] Observation board"),    ["platform"]),
    ("screws",    ("[7] 관찰판용 나사 3개", "[7] 3 screws"),     ["board"]),
    ("laser",     ("[2] 레이저 다이오드", "[2] Laser diode"),    ["platform"]),
    ("battery",   ("[3] 배터리 팩", "[3] Battery pack"),         ["laser"]),
    ("driver",    ("[9] 일자 드라이버", "[9] Flat-head driver"),  ["laser"]),
    ("pinhole",   ("[8] 핀홀", "[8] Pinhole"),                   ["driver"]),
    ("samplebox", ("[6] 시료 상자", "[6] Sample box"),           ["platform"]),
    ("clips",     ("[1] 종이 클립 4개", "[1] 4 paper clips"),     ["screws"]),
    ("ruler",     ("[13] 30 cm 자", "[13] 30 cm ruler"),          []),
]

ZONES = {
    "platform":  (300, 330, 190, 120),
    "board":     (300, 168, 90, 108),
    "screws":    (372, 168, 46, 108),
    "laser":     (470, 330, 82, 44),
    "battery":   (470, 424, 70, 40),
    "driver":    (150, 430, 70, 34),
    "pinhole":   (470, 286, 44, 40),
    "samplebox": (150, 200, 74, 54),
    "clips":     (232, 168, 44, 44),
    "ruler":     (150, 300, 92, 30),
}


class AssemblyTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.placed = set()
        self.drag = None

        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Label(left, text=T("장치 및 도구", "Apparatus & tools"),
                  font=("Helvetica", 11, "bold")).pack(anchor="w")
        self.tray = tk.Canvas(left, width=210, height=560, bg="#f2f3f5",
                              highlightthickness=1,
                              highlightbackground="#c3c7cc")
        self.tray.pack()
        self.msg = ttk.Label(left, text="", wraplength=200,
                             foreground="#8a1b1b")
        self.msg.pack(anchor="w", pady=4)

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("조립 구역 — 부품을 끌어다 놓으시오",
                                "Assembly area — drag the parts here"),
                  font=("Helvetica", 11, "bold")).pack(anchor="w")
        self.scene = tk.Canvas(right, width=620, height=560, bg="#e9ebee",
                               highlightthickness=1,
                               highlightbackground="#c3c7cc")
        self.scene.pack(fill="both", expand=True)

        self.tray.bind("<ButtonPress-1>", self.on_press)
        self.tray.bind("<B1-Motion>", self.on_move)
        self.tray.bind("<ButtonRelease-1>", self.on_release)

        self.redraw()

    # ----- painting --------------------------------------------------------
    def redraw(self):
        self.tray.delete("all")
        y = 46
        self.slots = []
        for key, lab, _ in PARTS:
            if key in self.placed:
                continue
            self.tray.create_rectangle(10, y - 32, 200, y + 32,
                                       fill="#ffffff", outline="#d3d7dc")
            ART[key](self.tray, 62, y, 0.62, tag="p_" + key)
            self.tray.create_text(120, y, text=T(*lab), width=150,
                                  font=("Helvetica", 8), anchor="w")
            self.slots.append((key, y))
            y += 70
        self.paint_scene()

    def paint_scene(self):
        cv = self.scene
        cv.delete("all")
        cv.create_text(310, 20, text=T("그림 9의 설치 구성",
                                       "Set-up of Figure 9"),
                       font=("Helvetica", 10, "bold"), fill="#4a5058")
        for key, (cx, cy, w, h) in ZONES.items():
            if key in self.placed:
                continue
            cv.create_rectangle(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2,
                                dash=(4, 3), outline="#b0b5bb")
        # placed items, in assembly order for correct overlap
        order = ["platform", "board", "screws", "clips", "samplebox",
                 "laser", "pinhole", "battery", "driver", "ruler"]
        for key in order:
            if key not in self.placed:
                continue
            cx, cy, w, h = ZONES[key]
            ART[key](cv, cx, cy, 1.0)
        if "platform" in self.placed:
            cv.create_text(300, 330 - 46, text="0",
                           font=("Helvetica", 8), fill="#dfe4e8")
        if len(self.placed) == len(PARTS):
            cv.create_text(310, 540, fill="#14532d",
                           font=("Helvetica", 11, "bold"),
                           text=T("조립 완료 — '실험대' 탭으로 이동하시오.",
                                  "Assembly complete — go to the Bench tab."))

    # ----- drag & drop -----------------------------------------------------
    def on_press(self, ev):
        for key, y in self.slots:
            if abs(ev.y - y) <= 32:
                self.drag = key
                self.ghost = self.scene.create_text(0, 0, text="")
                return
        self.drag = None

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
        key = self.drag
        self.drag = None
        x = self.tray.winfo_rootx() + ev.x - self.scene.winfo_rootx()
        y = self.tray.winfo_rooty() + ev.y - self.scene.winfo_rooty()
        cx, cy, w, h = ZONES[key]
        self.msg.config(text="")
        if not (abs(x - cx) < w / 2 + 26 and abs(y - cy) < h / 2 + 26):
            self.msg.config(text=T("그 위치에는 놓을 수 없습니다.",
                                   "That part does not belong there."))
            self.redraw()
            return
        needs = dict((k, n) for k, _, n in PARTS)[key]
        missing = [n for n in needs if n not in self.placed]
        if missing:
            names = ", ".join(T(*dict((k, l) for k, l, _ in PARTS)[m])
                              for m in missing)
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
    PPCM = 22.0                     # observation-board pixels per cm
    XMIN, XMAX = -11.0, 11.0        # cm
    YMIN, YMAX = -1.5, 24.0         # cm

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph

        # ---- state -------------------------------------------------------
        self.laser_on = tk.BooleanVar(value=False)
        self.turnA = tk.DoubleVar(value=38.0)     # laser height   (turns)
        self.turnB = tk.DoubleVar(value=26.0)     # laser tilt     (turns)
        self.turnC = tk.DoubleVar(value=25.0)     # lateral        (turns)
        self.turnD = tk.DoubleVar(value=25.0)     # yaw            (turns)
        self.aperture = tk.DoubleVar(value=2.6)   # beam spot dia [mm]
        self.pinhole_on = tk.BooleanVar(value=False)
        self.phi = tk.DoubleVar(value=0.0)        # rotary-disk reading [deg]
        self.sample = tk.IntVar(value=0)
        self.sheet = tk.StringVar(value="paper")
        self.markers = []

        self.build()
        self.refresh()

    # ---- geometry helpers -------------------------------------------------
    def yL(self):
        return self.turnA.get() * 1.0e-3                 # 1.0 mm / turn

    def tau(self):
        return math.radians(5.0 + self.turnB.get() * 0.5)

    def xL(self):
        return (self.turnC.get() - 25.0) * 0.4e-3

    def psi(self):
        return math.radians((self.turnD.get() - 25.0) * 0.2)

    def spot_mm(self):
        d = self.aperture.get()
        if self.pinhole_on.get() and "pinhole" in self.app.placed:
            d = min(d, 0.55)
        return d

    # ---- UI ---------------------------------------------------------------
    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        views = ttk.Frame(self)
        views.pack(side="left", fill="both", expand=True, padx=4, pady=6)

        def sec(txt):
            ttk.Label(ctl, text=txt, font=("Helvetica", 10, "bold")
                      ).pack(anchor="w", pady=(9, 2))

        sec(T("레이저 다이오드", "Laser diode"))
        ttk.Checkbutton(ctl, text=T("배터리 팩 스위치 ON",
                                    "Battery-pack switch ON"),
                        variable=self.laser_on,
                        command=self.refresh).pack(anchor="w")
        self.ap_row = ttk.Frame(ctl)
        self.ap_row.pack(anchor="w", fill="x")
        ttk.Label(self.ap_row, text=T("조리개 (드라이버)",
                                      "Aperture (driver)")).pack(anchor="w")
        ttk.Scale(self.ap_row, from_=0.4, to=4.0, variable=self.aperture,
                  orient="horizontal", length=190,
                  command=lambda e: self.refresh()).pack(anchor="w")
        ttk.Checkbutton(ctl, text=T("핀홀 부착", "Pinhole attached"),
                        variable=self.pinhole_on,
                        command=self.refresh).pack(anchor="w")

        sec(T("레이저 거치대 나사 (회전수)", "Laser holder screws (turns)"))
        self.mk_screw(ctl, "A", self.turnA, 0.0, 80.0, 0.1)
        self.mk_screw(ctl, "B", self.turnB, 0.0, 60.0, 0.02)
        self.mk_screw(ctl, "C", self.turnC, 0.0, 50.0, 0.1)
        self.mk_screw(ctl, "D", self.turnD, 0.0, 50.0, 0.05)

        sec(T("회전 원판", "Rotary disk"))
        row = ttk.Frame(ctl)
        row.pack(anchor="w")
        for d, txt in ((-30, "-30"), (-5, "-5"), (-1, "-1"),
                       (1, "+1"), (5, "+5"), (30, "+30")):
            ttk.Button(row, text=txt, width=4,
                       command=lambda dd=d: self.bump_phi(dd)).pack(side="left")
        self.phi_lbl = ttk.Label(ctl, text="", font=("Consolas", 11))
        self.phi_lbl.pack(anchor="w")

        sec(T("시료 상자", "Sample box"))
        row = ttk.Frame(ctl)
        row.pack(anchor="w")
        for i in range(1, 6):
            ttk.Button(row, text=str(i), width=3,
                       command=lambda k=i: self.load_sample(k)).pack(side="left")
        ttk.Button(row, text=T("비움", "empty"), width=6,
                   command=lambda: self.load_sample(0)).pack(side="left")
        self.smp_lbl = ttk.Label(ctl, text="", wraplength=210,
                                 foreground="#5a6068")
        self.smp_lbl.pack(anchor="w")

        sec(T("관찰판 부착물", "Attached to the board"))
        for v, txt in (("paper", T("종이 한 장", "plain paper")),
                       ("align", T("정렬 시트", "alignment sheet")),
                       ("graph", T("그래프 용지", "graph paper"))):
            ttk.Radiobutton(ctl, text=txt, value=v, variable=self.sheet,
                            command=self.refresh).pack(anchor="w")

        sec(T("기타", "Other"))
        ttk.Button(ctl, text=T("그림 16 (RHEED) 보기",
                               "Show Figure 16 (RHEED)"),
                   command=self.open_rheed).pack(anchor="w", fill="x")
        ttk.Button(ctl, text=T("표시 지우기", "Clear marks"),
                   command=self.clear_marks).pack(anchor="w", fill="x", pady=2)

        self.warn = ttk.Label(ctl, text="", wraplength=215,
                              foreground="#8a1b1b")
        self.warn.pack(anchor="w", pady=6)

        # ---- views -------------------------------------------------------
        top = ttk.Frame(views)
        top.pack(side="left", fill="y")
        ttk.Label(top, text=T("평면도 (플랫폼)", "Top view (platform)"),
                  font=("Helvetica", 9, "bold")).pack(anchor="w")
        self.cv_top = tk.Canvas(top, width=330, height=300, bg="#1a1d20",
                                highlightthickness=0)
        self.cv_top.pack()
        ttk.Label(top, text=T("시료 확대 / 측면도",
                              "Sample zoom / side view"),
                  font=("Helvetica", 9, "bold")).pack(anchor="w", pady=(6, 0))
        self.cv_side = tk.Canvas(top, width=330, height=250, bg="#f2f3f5",
                                 highlightthickness=0)
        self.cv_side.pack()

        bd = ttk.Frame(views)
        bd.pack(side="left", fill="both", expand=True, padx=(8, 0))
        ttk.Label(bd, text=T("관찰판", "Observation board"),
                  font=("Helvetica", 9, "bold")).pack(anchor="w")
        self.cv_board = tk.Canvas(bd, width=int((self.XMAX - self.XMIN) * self.PPCM),
                                  height=int((self.YMAX - self.YMIN) * self.PPCM),
                                  bg="#0b0c0d", highlightthickness=0)
        self.cv_board.pack()
        self.read = ttk.Label(bd, text="", font=("Consolas", 11))
        self.read.pack(anchor="w")
        self.cv_board.bind("<Motion>", self.on_board_motion)
        self.cv_board.bind("<Button-1>", self.on_board_click)

    def mk_screw(self, parent, name, var, lo, hi, step):
        row = ttk.Frame(parent)
        row.pack(anchor="w", fill="x")
        ttk.Label(row, text=T("나사 ", "screw ") + name, width=8).pack(side="left")
        ttk.Button(row, text="--", width=3,
                   command=lambda: self.bump(var, -10 * step, lo, hi)).pack(side="left")
        ttk.Button(row, text="-", width=2,
                   command=lambda: self.bump(var, -step, lo, hi)).pack(side="left")
        lbl = ttk.Label(row, text="", width=8, font=("Consolas", 10))
        lbl.pack(side="left")
        ttk.Button(row, text="+", width=2,
                   command=lambda: self.bump(var, step, lo, hi)).pack(side="left")
        ttk.Button(row, text="++", width=3,
                   command=lambda: self.bump(var, 10 * step, lo, hi)).pack(side="left")
        setattr(self, "lbl_" + name, lbl)

    def bump(self, var, d, lo, hi):
        var.set(max(lo, min(hi, round(var.get() + d, 4))))
        self.refresh()

    def bump_phi(self, d):
        self.phi.set((self.phi.get() + d) % 360)
        self.refresh()

    def load_sample(self, k):
        if "samplebox" not in self.app.placed:
            self.warn.config(text=T("시료 상자가 아직 없습니다.",
                                    "The sample box is not on the table yet."))
            return
        if abs(((self.phi.get() + 180) % 360) - 180) > 0.5:
            self.warn.config(text=T(
                "시료를 놓기 전에 회전 원판의 화살표가 0° 표시를 향하도록 하시오.",
                "Turn the rotary disk so its arrow points to the 0 deg mark "
                "before placing a sample."))
            return
        self.warn.config(text="")
        self.sample.set(k)
        self.refresh()

    def clear_marks(self):
        self.markers = []
        self.refresh()

    # ---- mapping ----------------------------------------------------------
    def bx(self, x_cm):
        return (x_cm - self.XMIN) * self.PPCM

    def by(self, y_cm):
        return (self.YMAX - y_cm) * self.PPCM

    def inv(self, px, py):
        return (px / self.PPCM + self.XMIN, self.YMAX - py / self.PPCM)

    # ---- events -----------------------------------------------------------
    def on_board_motion(self, ev):
        x, y = self.inv(ev.x, ev.y)
        self.read.config(text="x = %6.2f cm    y = %6.2f cm"
                              % (round(x * 20) / 20.0, round(y * 20) / 20.0))

    def on_board_click(self, ev):
        x, y = self.inv(ev.x, ev.y)
        self.markers.append((round(x * 20) / 20.0, round(y * 20) / 20.0))
        self.refresh()

    # ---- rendering --------------------------------------------------------
    def refresh(self):
        st_ap = "normal" if "driver" in self.app.placed else "disabled"
        for w in self.ap_row.winfo_children():
            try:
                w.configure(state=st_ap)
            except tk.TclError:
                pass
        for n, v in (("A", self.turnA), ("B", self.turnB),
                     ("C", self.turnC), ("D", self.turnD)):
            getattr(self, "lbl_" + n).config(text="%6.2f" % v.get())
        self.phi_lbl.config(text=T("각도 눈금 ", "angular scale ")
                            + "\u03d5 = %5.1f\u00b0" % self.phi.get())
        names = {0: T("없음", "none"),
                 1: T("1 : 평면 거울", "1 : plane mirror"),
                 2: T("2 : 비균일 긁힘 홈", "2 : non-uniform scratches"),
                 3: T("3 : 정규 격자", "3 : regular grating"),
                 4: T("4 : 기울어진 긁힘 홈", "4 : tilted scratches"),
                 5: T("5 : 긁힘 홈 + 미리 만들어진 홈",
                      "5 : scratches + pre-made grooves")}
        self.smp_lbl.config(text=T("장착된 시료: ", "mounted sample: ")
                            + names[self.sample.get()])
        self.draw_top()
        self.draw_side()
        self.draw_board()

    def beam_state(self):
        ph = self.ph
        hit = ph.beam_hit(self.yL(), self.tau(), self.xL(), self.psi())
        return hit

    def draw_top(self):
        cv = self.cv_top
        cv.delete("all")
        if "platform" not in self.app.placed:
            cv.create_text(165, 150, text=T("플랫폼 미설치", "no platform"),
                           fill="#6b7075")
            return
        cx, cy, R = 165.0, 165.0, 92.0
        cv.create_rectangle(14, 40, 316, 292, fill="#111417", outline="#33383d")
        # angular scale
        cv.create_oval(cx - R, cy - R, cx + R, cy + R,
                       fill="#e9eef2", outline="#7c848c")
        for a in range(0, 360, 5):
            rad = math.radians(a)
            l = 8 if a % 30 == 0 else 4
            # 0 deg toward the laser (-z, i.e. downward on screen)
            sx, sy = math.sin(rad), math.cos(rad)
            cv.create_line(cx + (R - l) * sx, cy + (R - l) * sy,
                           cx + R * sx, cy + R * sy, fill="#5b6167")
        for a in range(0, 360, 30):
            rad = math.radians(a)
            cv.create_text(cx + (R - 18) * math.sin(rad),
                           cy + (R - 18) * math.cos(rad),
                           text=str(a), font=("Helvetica", 7), fill="#3f454b")
        cv.create_oval(cx - 66, cy - 66, cx + 66, cy + 66,
                       fill="#f7fbff", outline="#9aa2aa")
        # disk arrow -> phi
        rad = math.radians(self.phi.get())
        cv.create_line(cx, cy, cx + 62 * math.sin(rad), cy + 62 * math.cos(rad),
                       fill="#b03030", width=2, arrow="last")
        # sample square (15 mm) at 3.4 px/mm
        s = 3.4
        half = 7.5 * s
        c, sn = math.cos(rad), math.sin(rad)
        pts = []
        for dx, dz in ((-half, -half), (half, -half), (half, half), (-half, half)):
            X = dx * c - dz * sn
            Z = dx * sn + dz * c
            pts += [cx + X, cy - Z]
        if self.sample.get():
            cv.create_polygon(pts, fill="#565b60", outline="#c9ced3")
        else:
            cv.create_polygon(pts, fill="", outline="#8b9096", dash=(3, 2))
        # laser holder at 0 deg side (bottom)
        cv.create_rectangle(cx - 16, cy + 118, cx + 16, cy + 140,
                            fill="#9aa1a8", outline="#5c6167")
        # angle bar + observation board at 180 deg side (top)
        cv.create_rectangle(cx - 96, cy - 128, cx + 96, cy - 120,
                            fill="#8b9096", outline="#5c6167")
        # beam
        hit = self.beam_state()
        if self.laser_on.get() and hit:
            H, d = hit
            x0 = cx + self.xL() * 1000 * s
            z0 = -self.ph.L0 * 1000 * s
            X = cx + H[0] * 1000 * s
            Z = H[2] * 1000 * s
            cv.create_line(x0, cy - z0, X, cy - Z, fill="#e33", width=1)
            if self.sample.get() and self.ph.on_sample(H):
                cv.create_line(X, cy - Z, X, cy - Z - 118,
                               fill="#f55", width=1, dash=(4, 3))
            cv.create_oval(X - 2, cy - Z - 2, X + 2, cy - Z + 2,
                           fill="#ff5555", outline="")

    def draw_side(self):
        cv = self.cv_side
        cv.delete("all")
        # ---- left: zoom of the sample seen from above -----------------------
        cv.create_rectangle(4, 4, 158, 158, fill="#15181b", outline="#33383d")
        cv.create_text(81, 14, text=T("시료 확대 (한 칸 1 mm)",
                                      "sample zoom (1 mm / division)"),
                       fill="#98a0a8", font=("Helvetica", 7))
        zx, zy, zs = 81.0, 88.0, 4.6            # px per mm
        for i in range(-15, 16):
            col = "#2c3136" if i % 5 else "#3d444a"
            cv.create_line(zx + i * zs, zy - 15 * zs, zx + i * zs, zy + 15 * zs,
                           fill=col)
            cv.create_line(zx - 15 * zs, zy + i * zs, zx + 15 * zs, zy + i * zs,
                           fill=col)
        rad = math.radians(self.phi.get())
        c, sn = math.cos(rad), math.sin(rad)
        pts = []
        for dx, dz in ((-7.5, -7.5), (7.5, -7.5), (7.5, 7.5), (-7.5, 7.5)):
            X = dx * c - dz * sn
            Z = dx * sn + dz * c
            pts += [zx + X * zs, zy - Z * zs]
        if self.sample.get():
            cv.create_polygon(pts, fill="#4b5055", outline="#d0d5da")
        else:
            cv.create_polygon(pts, fill="", outline="#6b7075", dash=(3, 2))
        hit = self.beam_state()
        if self.laser_on.get() and hit:
            H, _ = hit
            px, py = zx + H[0] * 1000 * zs, zy - H[2] * 1000 * zs
            r = max(1.6, self.spot_mm() * 0.5 * zs)
            cv.create_oval(px - r, py - r, px + r, py + r,
                           fill="#ff4d4d", outline="")
        # ---- right: side elevation ------------------------------------------
        ox, oy, sc = 236.0, 212.0, 0.40          # px per mm
        cv.create_rectangle(164, 4, 326, 246, fill="#f7f8fa", outline="#c9ced3")
        cv.create_text(245, 12, text=T("측면도", "side view"),
                       fill="#5a6068", font=("Helvetica", 7))
        cv.create_line(ox - 130 * sc, oy, ox + 170 * sc, oy,
                       fill="#8b9096")            # sample-surface plane / x-axis
        cv.create_rectangle(ox - 7.5 * sc, oy - 2, ox + 7.5 * sc, oy + 2,
                            fill="#4b5055", outline="")
        cv.create_line(ox + 150 * sc, oy + 10, ox + 150 * sc, oy - 255 * sc,
                       fill="#26292c", width=3)   # observation board
        if self.laser_on.get() and hit:
            H, d = hit
            lx = ox - self.ph.L0 * 1000 * sc
            ly = oy - self.yL() * 1000 * sc
            hx = ox + H[2] * 1000 * sc
            cv.create_rectangle(lx - 12, ly - 5, lx, ly + 5,
                                fill="#17191c", outline="")
            cv.create_line(lx, ly, hx, oy, fill="#e33")
            if self.sample.get() and self.ph.on_sample(H):
                u = self.ph.u_vec(math.cos(self.tau()), 0.0, 0.0, 0.0)
                p = self.ph.to_board(H, self.psi(), u)
                if p:
                    cv.create_line(hx, oy, ox + 150 * sc,
                                   oy - p[1] * 1000 * sc, fill="#f55")

    def draw_board(self):
        cv = self.cv_board
        cv.delete("all")
        W = int((self.XMAX - self.XMIN) * self.PPCM)
        Hh = int((self.YMAX - self.YMIN) * self.PPCM)
        if "board" not in self.app.placed or "screws" not in self.app.placed:
            cv.create_text(W / 2, Hh / 2, fill="#6b7075",
                           text=T("관찰판이 부착되지 않았습니다.",
                                  "observation board not mounted"))
            return
        sheet = self.sheet.get()
        if sheet == "graph":
            cv.create_rectangle(0, 0, W, Hh, fill="#f0f7f1", outline="")
            step = self.PPCM / 10.0
            i = 0
            x = self.bx(self.XMIN)
            while x <= W:
                cv.create_line(x, 0, x, Hh,
                               fill="#bfe0c5" if i % 10 else "#7fbf8c")
                x += step
                i += 1
            i = 0
            y = self.by(self.YMAX)
            while y <= Hh:
                cv.create_line(0, y, W, y,
                               fill="#bfe0c5" if i % 10 else "#7fbf8c")
                y += step
                i += 1
        else:
            cv.create_rectangle(0, 0, W, Hh, fill="#f7f7f3", outline="")
        # x-axis (top edge of the angle bar) and its origin
        cv.create_line(0, self.by(0), W, self.by(0), fill="#22262a", width=2)
        for i in range(int(self.XMIN), int(self.XMAX) + 1):
            cv.create_line(self.bx(i), self.by(0) - 5, self.bx(i),
                           self.by(0) + 5, fill="#22262a")
        cv.create_line(self.bx(0), 0, self.bx(0), Hh, fill="#9aa1a8")
        if sheet == "align":
            cv.create_oval(self.bx(0) - 4, self.by(self.ph.h0 * 100) - 4,
                           self.bx(0) + 4, self.by(self.ph.h0 * 100) + 4,
                           outline="#1b4d8a", width=2)
            cv.create_text(self.bx(0) + 62, self.by(self.ph.h0 * 100),
                           text=T("영차 점", "zero-order spot"),
                           fill="#1b4d8a", font=("Helvetica", 8))
        # ---- pattern -----------------------------------------------------
        if self.laser_on.get() and "laser" in self.app.placed \
                and "battery" in self.app.placed:
            items = self.ph.pattern(self.sample.get(), self.phi.get(),
                                    self.yL(), self.tau(),
                                    self.xL(), self.psi())
            r = max(1.8, self.spot_mm() * 0.5 * self.PPCM / 10.0 * 2.2)
            for it in items:
                if it[0] == 'dot':
                    _, X, Y, b = it
                    px, py = self.bx(X * 100), self.by(Y * 100)
                    if -20 < px < W + 20 and -20 < py < Hh + 20:
                        g = r * 2.1
                        cv.create_oval(px - g, py - g, px + g, py + g,
                                       fill=rcol(0.35 * b), outline="")
                        cv.create_oval(px - r, py - r, px + r, py + r,
                                       fill=rcol(min(1.0, 0.45 + 0.75 * b)),
                                       outline="")
                else:
                    pts = it[1]
                    for k in range(len(pts) - 1):
                        x1, y1, b1 = pts[k]
                        x2, y2, b2 = pts[k + 1]
                        p1 = (self.bx(x1 * 100), self.by(y1 * 100))
                        p2 = (self.bx(x2 * 100), self.by(y2 * 100))
                        if max(p1[1], p2[1]) < -30 or min(p1[1], p2[1]) > Hh + 30:
                            continue
                        if max(p1[0], p2[0]) < -30 or min(p1[0], p2[0]) > W + 30:
                            continue
                        bb = 0.5 * (b1 + b2)
                        cv.create_line(p1[0], p1[1], p2[0], p2[1],
                                       fill=rcol(0.28 * bb), capstyle="round",
                                       width=max(3, int(2.4 * r)))
                        cv.create_line(p1[0], p1[1], p2[0], p2[1],
                                       fill=rcol(min(1.0, 0.45 + 0.75 * bb)),
                                       capstyle="round",
                                       width=max(2, int(1.15 * r)))
        for (mx, my) in self.markers:
            px, py = self.bx(mx), self.by(my)
            cv.create_line(px - 6, py, px + 6, py, fill="#1560c0")
            cv.create_line(px, py - 6, px, py + 6, fill="#1560c0")

    # ---- Figure 16 ---------------------------------------------------------
    def open_rheed(self):
        w = tk.Toplevel(self)
        w.title(T("그림 16 : ZnSe의 RHEED 무늬",
                  "Figure 16 : RHEED pattern of ZnSe"))
        PP = 96.0                        # px per cm on the printed figure
        wide, high = 520, 330
        cv = tk.Canvas(w, width=wide, height=high, bg="#101010",
                       highlightthickness=0)
        cv.pack()
        x0 = wide / 2.0
        dx = self.ph.dx_rheed * 100.0 * PP
        cv.create_rectangle(30, 10, wide - 30, 210, fill="#050505", outline="")
        n = int((wide / 2 - 40) / dx) + 1
        for k in range(-n, n + 1):
            px = x0 + k * dx
            if not (32 < px < wide - 32):
                continue
            amp = math.exp(-(k / 5.0) ** 2)
            for j in range(6):
                g = int(230 * amp * math.exp(-(j / 2.4) ** 2))
                if g < 6:
                    continue
                col = "#%02x%02x%02x" % (g, g, g)
                for sgn in ((1,) if j == 0 else (1, -1)):
                    cv.create_line(px + sgn * j, 22, px + sgn * j, 205,
                                   fill=col)
        # ruler
        cv.create_rectangle(30, 222, wide - 30, 292, fill="#efe9dc",
                            outline="#b9b2a3")
        for k in range(0, int((wide - 60) / (PP / 10)) + 1):
            px = 34 + k * PP / 10.0
            if px > wide - 32:
                break
            L = 26 if k % 10 == 0 else (17 if k % 5 == 0 else 10)
            cv.create_line(px, 222, px, 222 + L, fill="#1b1b1b")
            if k % 10 == 0 and k > 0:
                cv.create_text(px, 262, text=str(k // 10),
                               font=("Helvetica", 16, "bold"), fill="#1b1b1b")
        lab = ttk.Label(w, text="", font=("Consolas", 11))
        lab.pack(anchor="w")

        def mv(ev):
            lab.config(text="%.2f cm" % ((ev.x - 34) / PP))
        cv.bind("<Motion>", mv)


# --------------------------------------------------------------------------
#  Application
# --------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.title(T("APhO 2016 실험 E1 — 1차원 구조로부터의 반사 광학 회절 무늬",
                     "APhO 2016 Experiment E1 — Reflected optical diffraction "
                     "patterns from 1D structures"))
        self.geometry("1330x760")
        self.ph = Physics(seed)
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
