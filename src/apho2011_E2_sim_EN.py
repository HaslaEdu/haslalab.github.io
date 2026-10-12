#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APhO 2011 (12th Asian Physics Olympiad, Israel) - Experimental Question 2
"An Optical Black Box"

HaslaLab virtual laboratory simulator.
- Standard library only (tkinter).
- The student sees only what the real bench shows: patterns on millimetre
  paper, the view through the sample, a tape measure and a ruler.
  No angle, index or spacing is ever displayed.
- Hidden true parameters are randomised every session.
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


DEG = math.pi / 180.0
LAM_LASER_NOM = 652e-9        # given on the problem sheet, +-2 nm


# ----------------------------------------------------------------------------
#  colour : wavelength (nm) -> 8-bit RGB   (Bruton's approximation)
# ----------------------------------------------------------------------------
def wl_rgb(nm):
    if nm < 380 or nm > 780:
        return (0.0, 0.0, 0.0)
    if nm < 440:
        r, g, b = -(nm - 440.0) / 60.0, 0.0, 1.0
    elif nm < 490:
        r, g, b = 0.0, (nm - 440.0) / 50.0, 1.0
    elif nm < 510:
        r, g, b = 0.0, 1.0, -(nm - 510.0) / 20.0
    elif nm < 580:
        r, g, b = (nm - 510.0) / 70.0, 1.0, 0.0
    elif nm < 645:
        r, g, b = 1.0, -(nm - 645.0) / 65.0, 0.0
    else:
        r, g, b = 1.0, 0.0, 0.0
    if nm > 700:
        f = 0.3 + 0.7 * (780.0 - nm) / 80.0
    elif nm < 420:
        f = 0.3 + 0.7 * (nm - 380.0) / 40.0
    else:
        f = 1.0
    return (r * f, g * f, b * f)


def hexcol(r, g, b):
    cl = lambda v: max(0, min(255, int(round(255.0 * v))))
    return "#%02x%02x%02x" % (cl(r), cl(g), cl(b))


# ----------------------------------------------------------------------------
#  the sample : a transparent film with 90-degree saw teeth
# ----------------------------------------------------------------------------
class Sample(object):
    """Structure (A) of figure 5: symmetric teeth, apex angle phi, period d.
    Each slanted face together with the flat back face forms a prism of
    opening angle  x = (pi - phi) / 2."""

    def __init__(self, rng):
        self.phi = math.pi / 2.0                      # apex angle (by design)
        self.x_prism = (math.pi - self.phi) / 2.0      # 45 degrees
        self.d = 50.2e-6 * rng.uniform(0.96, 1.05)     # tooth period
        self.cauchy_a = 1.562056 + rng.uniform(-0.006, 0.006)
        self.cauchy_b = 6.778e-15 * rng.uniform(0.96, 1.04)   # [m^2]
        self.height = 0.5 * self.d * math.tan(self.x_prism)   # tooth height
        # the far blue end of the white LED spectrum (subjective!)
        self.lam_violet = rng.uniform(396e-9, 410e-9)
        self.frame_mm = 50.0
        self.aperture_mm = 24.0

    def n(self, lam):
        return self.cauchy_a + self.cauchy_b / (lam * lam)

    # ---- geometric deviation of one prism ------------------------------
    def deviation(self, i1, lam):
        """Deviation of a ray hitting the slanted face at incidence i1."""
        n = self.n(lam)
        s = math.sin(i1) / n
        if abs(s) > 1.0:
            return None
        r1 = math.asin(s)
        r2 = self.x_prism - r1
        s2 = n * math.sin(r2)
        if abs(s2) > 1.0:
            return None                      # total internal reflection
        return i1 + math.asin(s2) - self.x_prism

    def delta0(self, lam):
        """Perpendicular illumination of the toothed side (i1 = x_prism)."""
        return self.deviation(self.x_prism, lam)

    def delta_min(self, lam):
        n = self.n(lam)
        s = n * math.sin(self.x_prism / 2.0)
        if abs(s) > 1.0:
            return None
        return 2.0 * math.asin(s) - self.x_prism

    def i1_of_min(self, lam):
        return math.asin(self.n(lam) * math.sin(self.x_prism / 2.0))

    # ---- index from the measured angles (part g) ------------------------
    @staticmethod
    def n_from_delta0(delta0, phi):
        x = (math.pi - phi) / 2.0
        return math.sqrt(math.sin(x) ** 2 +
                         (math.cos(x) + math.sin(delta0) / math.sin(x)) ** 2)

    @staticmethod
    def n_from_delta_min(dmin, phi):
        x = (math.pi - phi) / 2.0
        return math.sin((x + dmin) / 2.0) / math.sin(x / 2.0)

    # ---- diffraction ----------------------------------------------------
    def sin_theta(self, m, lam, psi=0.0):
        """Grating equation; a rotation psi foreshortens the period."""
        d_eff = self.d * math.cos(psi)
        s = m * lam / d_eff
        return s if abs(s) <= 1.0 else None

    def fringe_visibility(self, m, psi, lam):
        """Peaks and valleys of the profile are laterally d/2 apart and
        vertically h apart -> their interference dims every other order."""
        n = self.n(lam)
        dphi = 2.0 * math.pi * (n - 1.0) * self.height / lam
        dphi += 2.0 * math.pi * self.height * math.tan(psi) / lam
        return 0.5 * (1.0 + math.cos(math.pi * m + dphi))


# ----------------------------------------------------------------------------
#  the bench : where every object sits (millimetres, desk coordinates)
# ----------------------------------------------------------------------------
class Apparatus(object):
    DESK_W = 1120.0
    DESK_H = 1000.0

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1 << 30)
        self.seed = seed
        self.rng = random.Random(seed)
        rng = self.rng
        self.sample = Sample(rng)
        self.lam_laser = LAM_LASER_NOM + rng.uniform(-2e-9, 2e-9)

        # placed objects : None until the student puts them on the desk
        self.placed = set()
        self.src = [180.0, 500.0]          # light-source stand
        self.holder = [560.0, 500.0]       # sample holder + stand
        self.screen = [900.0, 500.0]       # centre of the screen
        self.screen_horiz = False          # False: screen plane along y
        self.bench = [560.0, 830.0]        # centre of the wooden bench
        self.bench_horiz = True            # True: rail along x
        self.stake = 0.0                   # stake offset along the rail [mm]
        self.marks = []                    # marks made on the bench [mm]

        self.mounted = None                # "flashlight" / "laser" / None
        self.source_on = False
        self.lamp_on = True                # desk lamp
        self.sample_in_holder = False
        self.flip = 0                      # 0: toothed side faces the source
        self.psi = 0.0                     # fine rotation of the sample [rad]
        self.screen_w = 600.0
        self.screen_hole = 8.0             # diameter of the hole [mm]
        self.bench_len = 1000.0
        # small unavoidable imperfections
        self.laser_slope = rng.uniform(-0.004, 0.004)
        self.read_bias = rng.uniform(-0.4, 0.4)      # mm, tape measure bias

    # ------------------------------------------------------------------
    def axis(self):
        """Unit vector from the light source to the sample."""
        dx = self.holder[0] - self.src[0]
        dy = self.holder[1] - self.src[1]
        L = math.hypot(dx, dy)
        if L < 1e-6:
            return (1.0, 0.0), 0.0
        return (dx / L, dy / L), L

    def source_at_hole(self):
        """Is the light source sitting in the hole of the screen?"""
        if "screen" not in self.placed:
            return False
        return self.dist_point_screen(self.src) < 25.0 and \
            self.lateral_on_screen(self.src) < 0.6 * self.screen_hole + 6.0

    def dist_point_screen(self, p):
        if self.screen_horiz:
            return abs(p[1] - self.screen[1])
        return abs(p[0] - self.screen[0])

    def lateral_on_screen(self, p):
        """Distance from the hole, measured in the plane of the screen."""
        if self.screen_horiz:
            return abs(p[0] - self.screen[0])
        return abs(p[1] - self.screen[1])

    def screen_distance(self):
        """Perpendicular distance sample -> screen plane [mm]."""
        return self.dist_point_screen(self.holder)

    def bench_distance(self):
        """Perpendicular distance sample -> the rail of the bench [mm]."""
        if self.bench_horiz:
            return abs(self.holder[1] - self.bench[1])
        return abs(self.holder[0] - self.bench[0])

    def stake_xy(self):
        if self.bench_horiz:
            return [self.bench[0] + self.stake, self.bench[1]]
        return [self.bench[0], self.bench[1] + self.stake]

    def stake_angle(self):
        """Angle of the stake as seen from the sample, measured from the
        sample -> source direction (positive = to one side)."""
        (ux, uy), _ = self.axis()
        sx, sy = self.stake_xy()
        vx, vy = sx - self.holder[0], sy - self.holder[1]
        # component along the outgoing optical axis and perpendicular to it
        along = -(vx * ux + vy * uy)      # towards the light source
        perp = -vx * uy + vy * ux
        if along < 20.0:
            return None                   # the stake is behind the sample
        return math.atan2(perp, along)

    def alignment_quality(self):
        """0 = perfect, 1 = hopeless : lateral offset of the sample from the
        axis of the source, and of the stake from the plane of the bench."""
        (ux, uy), L = self.axis()
        if L < 60.0:
            return 1.0
        # the bench should be perpendicular to the line of sight
        if self.bench_horiz:
            cross = abs(ux)
        else:
            cross = abs(uy)
        return min(1.0, abs(1.0 - cross) * 4.0)


# ----------------------------------------------------------------------------
#  observation model : what the eye and the screen actually show
# ----------------------------------------------------------------------------
LAMS = [(384 + 8 * i) * 1e-9 for i in range(41)]         # 384 ... 704 nm


def led_weight(lam, lam_violet=402e-9):
    """Relative spectral power of the white LED (blue pump + phosphor).
    The violet roll-off is what makes "the far blue end of the spectrum"
    a subjective judgement for the student."""
    nm = lam * 1e9
    cut = lam_violet * 1e9 + 25.0
    blue = 1.00 * math.exp(-((nm - 452.0) / 17.0) ** 2)
    phos = 0.85 * math.exp(-((nm - 565.0) / 62.0) ** 2)
    w = blue + phos
    if nm < cut:
        w *= math.exp(-((cut - nm) / 13.0) ** 2)
    if nm > 690.0:
        w *= math.exp(-((nm - 690.0) / 22.0) ** 2)
    return w


class Optics(object):
    def __init__(self, app):
        self.app = app

    # ---------------- feature list ---------------------------------------
    def features(self, kind, lam, mono=False):
        """[(angle [rad], amplitude, tag)] for one wavelength.
        Angles are measured from the sample towards the light source."""
        a = self.app
        s = a.sample
        out = []
        d_eff = s.d * math.cos(a.psi)
        if kind == "trans":
            # the flattened peaks/valleys transmit undeviated light in both
            # orientations; the slanted faces only work from the toothed side
            out.append((0.0, 0.45, "direct"))
            bands = []
            if a.flip == 0:
                for sgn in (+1, -1):
                    dv = s.deviation(s.x_prism - sgn * a.psi, lam)
                    if dv is not None:
                        bands.append(sgn * dv)
                        if not mono:
                            out.append((sgn * dv, 7.0, "band"))
            amp_o = 0.30
            # with monochromatic light the bright patch is itself made of
            # interference fringes, narrowed by the diffraction pattern of a
            # single slanted face (width of the order of the spacing d)
            wband = 3.0 * lam / d_eff
            m = 1
            while True:
                sv = m * lam / d_eff
                if sv >= 0.62:
                    break
                th = math.asin(sv)
                env = math.exp(-(sv / 0.34) ** 2)
                vis = s.fringe_visibility(m, a.psi, lam)
                for sg in (+1, -1):
                    amp = amp_o * env
                    if mono:
                        for bd in bands:
                            amp += 7.0 * math.exp(-((sg * sv -
                                                     math.sin(bd)) / wband) ** 2)
                    out.append((sg * th, amp * vis, "order"))
                m += 1
            if mono:
                for bd in bands:
                    out.append((bd, 1.6, "band"))
        else:                                    # reflection
            strong = 4.2 if a.flip == 1 else 0.42
            out.append((0.0, strong, "band"))
            m = 1
            while True:
                sv = m * lam / d_eff
                if sv >= 0.30:
                    break
                th = math.asin(sv)
                env = math.exp(-(sv / 0.075) ** 2)
                for sg in (+1, -1):
                    out.append((sg * th, strong * env *
                                s.fringe_visibility(m, a.psi, lam), "order"))
                m += 1
        return out

    # ---------------- generic accumulator --------------------------------
    def columns(self, kind, npx, ang0, ang1, sigma, mono=None, gain=1.0):
        """Render one horizontal strip: returns three float lists (r,g,b)."""
        R = [0.0] * npx
        G = [0.0] * npx
        B = [0.0] * npx
        dang = (ang1 - ang0) / float(npx - 1)
        lams = [mono] if mono else LAMS
        for lam in lams:
            w = 1.0 if mono else led_weight(lam, self.app.sample.lam_violet)
            if w < 1e-3:
                continue
            cr, cg, cb = wl_rgb(lam * 1e9)
            for (ang, amp, tag) in self.features(kind, lam, mono is not None):
                if amp <= 1e-4:
                    continue
                sg = sigma(tag, ang) if callable(sigma) else sigma
                if sg <= 0:
                    continue
                c = (ang - ang0) / dang
                half = int(3.2 * sg / abs(dang)) + 1
                i0 = max(0, int(c) - half)
                i1 = min(npx - 1, int(c) + half)
                k = amp * w * gain
                for i in range(i0, i1 + 1):
                    da = (ang0 + i * dang) - ang
                    v = k * math.exp(-0.5 * (da / sg) ** 2)
                    R[i] += v * cr
                    G[i] += v * cg
                    B[i] += v * cb
        return R, G, B

    # ---------------- the view through the sample ------------------------
    def eye_columns(self, npx, ang0, ang1):
        a = self.app
        (_, L) = a.axis()[0], a.axis()[1]
        src_ang = math.atan2(2.0, max(L, 30.0))       # LED die ~2 mm across
        sig = lambda tag, ang: max(src_ang, 0.004)
        R, G, B = self.columns("trans", npx, ang0, ang1, sig, gain=1.0)
        return R, G, B

    # ---------------- accumulator in screen coordinates -------------------
    def columns_x(self, kind, npx, x0, x1, y, sig_mm, mono=None, gain=1.0):
        """Render a strip of the screen: columns are linear in x [mm]."""
        R = [0.0] * npx
        G = [0.0] * npx
        B = [0.0] * npx
        dx = (x1 - x0) / float(npx - 1)
        lams = [mono] if mono else LAMS
        for lam in lams:
            w = 1.0 if mono else led_weight(lam, self.app.sample.lam_violet)
            if w < 1e-3:
                continue
            cr, cg, cb = wl_rgb(lam * 1e9)
            for (ang, amp, tag) in self.features(kind, lam, mono is not None):
                if amp <= 1e-4 or abs(ang) > 80.0 * DEG:
                    continue
                xf = y * math.tan(ang)
                sg = sig_mm(tag) if callable(sig_mm) else sig_mm
                if sg <= 0:
                    continue
                c = (xf - x0) / dx
                half = int(3.2 * sg / abs(dx)) + 1
                i0 = max(0, int(c) - half)
                i1 = min(npx - 1, int(c) + half)
                k = amp * w * gain
                for i in range(i0, i1 + 1):
                    dd = (x0 + i * dx) - xf
                    v = k * math.exp(-0.5 * (dd / sg) ** 2)
                    R[i] += v * cr
                    G[i] += v * cg
                    B[i] += v * cb
        return R, G, B

    # ---------------- the pattern on the screen --------------------------
    def screen_columns(self, npx, x0_mm, x1_mm, mode):
        """mode: 'trans-white', 'refl-white', 'trans-laser', 'refl-laser'.
        x0_mm, x1_mm are measured from the centre of the pattern."""
        a = self.app
        y = max(a.screen_distance(), 20.0)
        if mode.endswith("laser"):
            path = y if mode.startswith("trans") else 2.0 * y
            beam = 1.2 + 0.0025 * path
            kind = "trans" if mode.startswith("trans") else "refl"
            return self.columns_x(kind, npx, x0_mm, x1_mm, y,
                                  lambda tag: beam / 2.5,
                                  mono=a.lam_laser, gain=1.6)
        if mode.startswith("trans"):
            # the whole aperture of the sample is deflected -> heavy smear
            ap = 0.5 * a.sample.aperture_mm
            return self.columns_x("trans", npx, x0_mm, x1_mm, y,
                                  lambda tag: ap, gain=1.0)
        # white-light reflection: the smear vanishes when the lamp sits in the
        # hole of the screen, because the doubly reflected ray is antiparallel
        off = abs(a.dist_point_screen(a.src))
        spread = 0.5 * a.sample.aperture_mm * off / max(y, 1.0)
        return self.columns_x("refl", npx, x0_mm, x1_mm, y,
                              lambda tag: max(spread, 0.6), gain=1.0)


# ============================================================================
#                                   GUI
# ============================================================================
TOP_PX = 0.55        # top-view canvas pixels per millimetre
SCR_PX = 1.80        # screen: pixels per millimetre
BEN_PX = 1.08        # bench close-up: pixels per millimetre (1000 mm rail)
EYE_N = 1080         # columns of the "view through the sample"
REF_EYE = 40.0       # fixed "exposure" of the eye view
REF_SCR_WHITE = 60.0
REF_SCR_LASER = 1.5
EYE_A = 45.0 * DEG   # half field of the eye view
BG = "#e8e4d9"
DESK = "#5f7d6e"
PAPER = "#f4f2e6"

PARTS = [
    ("stand", T("광원용 스탠드", "stand for the light source")),
    ("flashlight", T("백색 LED 손전등", "white LED flashlight")),
    ("laser", T("적색 레이저 포인터", "red laser pointer")),
    ("holder", T("시료 홀더 + 스탠드", "sample holder + stand")),
    ("sample", T("시료(슬라이드 프레임)", "the sample (slide frame)")),
    ("screen", T("흰 스크린(모눈종이, 구멍)", "white screen (mm paper, hole)")),
    ("bench", T("나무 벤치 + 막대", "wooden bench + stake")),
    ("tape", T("줄자", "tape measure")),
    ("ruler", T("자", "ruler")),
    ("lamp", T("탁상 램프", "desk lamp")),
]


def q(v, step):
    return round(v / step) * step


class Sim(object):
    def __init__(self, root, seed=None):
        self.root = root
        self.app = Apparatus(seed)
        self.opt = Optics(self.app)
        root.title("HaslaLab \u2014 APhO 2011 E2 : " +
                   T("광학 \u201c블랙박스\u201d", "An Optical Black Box"))
        root.configure(bg=BG)
        self.drag = None
        self.dragobj = None
        self.tape_pts = []
        self.scr_pts = []
        self.bench_pts = []
        self.tape_txt = tk.StringVar(value="")
        self.scr_txt = tk.StringVar(value="")
        self.bench_txt = tk.StringVar(value="")
        self.status = tk.StringVar(
            value=T("부품 상자에서 장비를 끌어다 책상에 배치하십시오.",
                    "Drag the equipment from the parts box onto the desk."))
        self._cache = None
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        self.t_asm = tk.Frame(nb, bg=BG)
        self.t_ben = tk.Frame(nb, bg=BG)
        nb.add(self.t_asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.t_ben, text=T(" 실험대 ", " Bench "))
        self._build_asm()
        self._build_bench()
        self.redraw()

    # ================================================================
    #  assembly / layout tab
    # ================================================================
    def _build_asm(self):
        bar = tk.Frame(self.t_asm, bg=BG)
        bar.pack(fill="x", padx=6, pady=3)
        tk.Button(bar, text=T("스크린 90\u00b0 회전", "rotate screen 90\u00b0"),
                  command=self.rot_screen).pack(side="left")
        tk.Button(bar, text=T("벤치 90\u00b0 회전", "rotate bench 90\u00b0"),
                  command=self.rot_bench).pack(side="left", padx=4)
        tk.Label(bar, text=T("  왼쪽 끌기: 장비 이동   오른쪽 클릭: 줄자 측정",
                             "  left-drag: move   right-click: tape measure"),
                 bg=BG, font=("TkDefaultFont", 8)).pack(side="left")
        tk.Label(bar, textvariable=self.tape_txt, bg=BG, fg="#8a1c1c",
                 font=("TkDefaultFont", 10, "bold")).pack(side="right")
        tk.Label(self.t_asm, textvariable=self.status, bg=BG,
                 anchor="w").pack(fill="x", padx=8)
        body = tk.Frame(self.t_asm, bg=BG)
        body.pack(fill="both", expand=True)
        box = tk.Frame(body, bg="#cfd8cf")
        box.pack(side="left", fill="y", padx=6, pady=4)
        self.cbox = tk.Canvas(box, width=170, height=560, bg="#cfd8cf",
                              highlightthickness=0)
        self.cbox.pack()
        self.cbox.bind("<ButtonPress-1>", self.box_press)
        self.cbox.bind("<B1-Motion>", self.box_motion)
        self.cbox.bind("<ButtonRelease-1>", self.box_release)
        self.ct = tk.Canvas(body, width=int(Apparatus.DESK_W * TOP_PX) + 4,
                            height=int(Apparatus.DESK_H * TOP_PX) + 4,
                            bg=DESK, highlightthickness=0)
        self.ct.pack(side="left", padx=4, pady=4)
        self.ct.bind("<ButtonPress-1>", self.top_press)
        self.ct.bind("<B1-Motion>", self.top_motion)
        self.ct.bind("<ButtonRelease-1>", self.top_release)
        self.ct.bind("<Button-3>", self.top_tape)

    def mm2px(self, p):
        return (p[0] * TOP_PX + 2, p[1] * TOP_PX + 2)

    def px2mm(self, x, y):
        return [(x - 2) / TOP_PX, (y - 2) / TOP_PX]

    def draw_box(self):
        c = self.cbox
        c.delete("all")
        c.create_text(85, 12, text=T("부품 상자", "parts box"),
                      font=("TkDefaultFont", 9, "bold"))
        self.boxes = []
        y = 26
        a = self.app
        for key, label in PARTS:
            done = key in a.placed or (key == "sample" and a.sample_in_holder) \
                or (key in ("flashlight", "laser") and a.mounted == key)
            rr = c.create_rectangle(8, y, 162, y + 48,
                                    fill="#9fae9f" if done else "#f3f6f3",
                                    outline="#7d8a7d")
            c.create_text(85, y + 16, text=label, width=148,
                          font=("TkDefaultFont", 8))
            c.create_text(85, y + 38,
                          text=T("(배치됨)", "(placed)") if done
                          else T("끌어다 놓기", "drag me"),
                          font=("TkDefaultFont", 7), fill="#555")
            self.boxes.append((key, 8, y, 162, y + 48))
            y += 53

    def draw_top(self):
        c = self.ct
        c.delete("all")
        a = self.app
        W = Apparatus.DESK_W * TOP_PX
        H = Apparatus.DESK_H * TOP_PX
        c.create_rectangle(2, 2, W + 2, H + 2, fill=DESK, outline="#3f5a4d")
        for x in range(0, int(Apparatus.DESK_W) + 1, 100):
            c.create_line(x * TOP_PX + 2, 2, x * TOP_PX + 2, H + 2,
                          fill="#55705f")
        for y in range(0, int(Apparatus.DESK_H) + 1, 100):
            c.create_line(2, y * TOP_PX + 2, W + 2, y * TOP_PX + 2,
                          fill="#55705f")
        c.create_text(64, 12, text=T("책상 위 (위에서 본 그림, 100 mm 격자)",
                                     "desk, seen from above (100 mm grid)"),
                      fill="#cfe0d6", font=("TkDefaultFont", 8))
        if a.lamp_on and "lamp" in a.placed:
            c.create_oval(W - 90, 8, W - 20, 78, fill="#f7f0c0",
                          outline="#c9bd6a")
            c.create_text(W - 55, 43, text=T("램프 ON", "lamp ON"),
                          font=("TkDefaultFont", 7))
        elif "lamp" in a.placed:
            c.create_oval(W - 90, 8, W - 20, 78, fill="#6d7d72",
                          outline="#4b5a50")
            c.create_text(W - 55, 43, text=T("램프 OFF", "lamp OFF"),
                          font=("TkDefaultFont", 7), fill="#ddd")
        # ---- screen -------------------------------------------------
        if "screen" in a.placed:
            sx, sy = self.mm2px(a.screen)
            half = 0.5 * a.screen_w * TOP_PX
            if a.screen_horiz:
                c.create_rectangle(sx - half, sy - 4, sx + half, sy + 4,
                                   fill=PAPER, outline="#8f8b78")
                c.create_oval(sx - 3, sy - 5, sx + 3, sy + 5, fill="#333",
                              outline="")
            else:
                c.create_rectangle(sx - 4, sy - half, sx + 4, sy + half,
                                   fill=PAPER, outline="#8f8b78")
                c.create_oval(sx - 5, sy - 3, sx + 5, sy + 3, fill="#333",
                              outline="")
            c.create_text(sx, sy - half - 10 if not a.screen_horiz else sy - 14,
                          text=T("스크린(구멍)", "screen (hole)"), fill="#eee",
                          font=("TkDefaultFont", 7))
        # ---- bench + stake ------------------------------------------
        if "bench" in a.placed:
            bx, by = self.mm2px(a.bench)
            half = 0.5 * a.bench_len * TOP_PX
            if a.bench_horiz:
                c.create_rectangle(bx - half, by - 8, bx + half, by + 8,
                                   fill="#c8a86a", outline="#8a6f3c")
            else:
                c.create_rectangle(bx - 8, by - half, bx + 8, by + half,
                                   fill="#c8a86a", outline="#8a6f3c")
            for mk in a.marks:
                if a.bench_horiz:
                    mx, my = bx + mk * TOP_PX, by
                    c.create_line(mx, my - 8, mx, my + 8, fill="#b02")
                else:
                    mx, my = bx, by + mk * TOP_PX
                    c.create_line(mx - 8, my, mx + 8, my, fill="#b02")
            stx, sty = self.mm2px(a.stake_xy())
            c.create_oval(stx - 4, sty - 4, stx + 4, sty + 4, fill="#6b4a1e",
                          outline="#2f200c")
            c.create_text(bx, by - 16, text=T("벤치 + 막대", "bench + stake"),
                          fill="#eee", font=("TkDefaultFont", 7))
        # ---- light source -------------------------------------------
        (ux, uy), L = a.axis()
        if "stand" in a.placed:
            px, py = self.mm2px(a.src)
            c.create_oval(px - 19, py - 19, px + 19, py + 19, fill="#1b1b1b",
                          outline="#000")
            if a.mounted:
                col = "#c9c9c9" if a.mounted == "flashlight" else "#8a8a8a"
                c.create_line(px, py, px + 40 * ux, py + 40 * uy, width=9,
                              fill=col)
                if a.mounted == "laser":
                    c.create_line(px + 30 * ux, py + 30 * uy, px + 44 * ux,
                                  py + 44 * uy, width=9, fill="#111")
                if a.source_on:
                    c.create_oval(px + 40 * ux - 5, py + 40 * uy - 5,
                                  px + 40 * ux + 5, py + 40 * uy + 5,
                                  fill="#fff" if a.mounted == "flashlight"
                                  else "#f33", outline="")
            c.create_text(px, py + 28, text=T("광원", "source"), fill="#eee",
                          font=("TkDefaultFont", 7))
        # ---- sample holder ------------------------------------------
        if "holder" in a.placed:
            px, py = self.mm2px(a.holder)
            c.create_oval(px - 19, py - 19, px + 19, py + 19, fill="#1b1b1b",
                          outline="#000")
            if a.sample_in_holder:
                nx, ny = ux * math.cos(a.psi) - uy * math.sin(a.psi), \
                    ux * math.sin(a.psi) + uy * math.cos(a.psi)
                tx, ty = -ny, nx
                hf = 0.5 * a.sample.frame_mm * TOP_PX
                c.create_line(px - hf * tx, py - hf * ty, px + hf * tx,
                              py + hf * ty, width=6, fill="#e9e9e9")
                c.create_line(px - 3 * tx - 8 * nx, py - 3 * ty - 8 * ny,
                              px + 3 * tx - 8 * nx, py + 3 * ty - 8 * ny,
                              width=2, fill="#1b4fd0")
                c.create_text(px, py - 26,
                              text=T("톱니면", "toothed") if a.flip == 0
                              else T("평면", "flat"), fill="#ffe",
                              font=("TkDefaultFont", 7))
            c.create_text(px, py + 28, text=T("시료", "sample"), fill="#eee",
                          font=("TkDefaultFont", 7))
        if "stand" in a.placed and "holder" in a.placed:
            p1 = self.mm2px(a.src)
            p2 = self.mm2px(a.holder)
            c.create_line(p1[0], p1[1], p2[0], p2[1], fill="#d8e6dd",
                          dash=(3, 4))
        for (px, py) in self.tape_pts:
            c.create_line(px - 7, py, px + 7, py, fill="#ff3", width=2)
            c.create_line(px, py - 7, px, py + 7, fill="#ff3", width=2)
        if len(self.tape_pts) == 2:
            c.create_line(self.tape_pts[0][0], self.tape_pts[0][1],
                          self.tape_pts[1][0], self.tape_pts[1][1],
                          fill="#ff3", width=1)
        if self.drag:
            x, y, key = self.drag
            c.create_rectangle(x - 44, y - 14, x + 44, y + 14,
                               fill="#fffbe0", outline="#b8a800")
            c.create_text(x, y, text=dict(PARTS)[key], width=84,
                          font=("TkDefaultFont", 7))

    # ---------------- box / desk interaction -------------------------
    def box_press(self, e):
        for (k, x0, y0, x1, y1) in getattr(self, "boxes", []):
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                self.drag = (0, 0, k)
                self.status.set(T("%s \u2014 책상 위 원하는 곳에 놓으십시오.",
                                  "%s - drop it where you want it.")
                                % dict(PARTS)[k])
                return

    def box_motion(self, e):
        pass

    def box_release(self, e):
        pass

    def top_press(self, e):
        a = self.app
        if self.drag:
            return
        for key, pos in (("stand", a.src), ("holder", a.holder),
                         ("screen", a.screen), ("bench", a.bench)):
            if key not in a.placed:
                continue
            px, py = self.mm2px(pos)
            if math.hypot(e.x - px, e.y - py) < 22:
                self.dragobj = key
                return
        if "bench" in a.placed:
            sx, sy = self.mm2px(a.stake_xy())
            if math.hypot(e.x - sx, e.y - sy) < 10:
                self.dragobj = "stake"

    def top_motion(self, e):
        a = self.app
        if self.drag:
            self.drag = (e.x, e.y, self.drag[2])
            self.redraw()
            return
        if not self.dragobj:
            return
        p = self.px2mm(e.x, e.y)
        p[0] = max(20.0, min(Apparatus.DESK_W - 20.0, p[0]))
        p[1] = max(20.0, min(Apparatus.DESK_H - 20.0, p[1]))
        if self.dragobj == "stand":
            a.src = p
        elif self.dragobj == "holder":
            a.holder = p
        elif self.dragobj == "screen":
            a.screen = p
        elif self.dragobj == "bench":
            a.bench = p
        elif self.dragobj == "stake":
            off = (p[0] - a.bench[0]) if a.bench_horiz else (p[1] - a.bench[1])
            a.stake = max(-0.5 * a.bench_len, min(0.5 * a.bench_len, off))
        self.invalidate()
        self.redraw()

    def top_release(self, e):
        if self.dragobj:
            self.dragobj = None
            return
        if not self.drag:
            return
        key = self.drag[2]
        self.drag = None
        self.place(key, e.x, e.y)
        self.invalidate()
        self.redraw()

    def place(self, key, ex, ey):
        a = self.app
        p = self.px2mm(ex, ey)
        if key in ("flashlight", "laser"):
            if "stand" not in a.placed:
                self.status.set(T("먼저 광원용 스탠드를 배치하십시오.",
                                  "Place the stand for the light source first."))
                return
            sx, sy = self.mm2px(a.src)
            if math.hypot(ex - sx, ey - sy) > 34:
                self.status.set(T("광원은 스탠드에 장착해야 합니다. 스탠드 위에 놓으십시오.",
                                  "The source must be mounted on the stand."))
                return
            a.mounted = key
            a.placed.add(key)
            a.placed.discard("laser" if key == "flashlight" else "flashlight")
            a.source_on = False
            self.status.set(T("%s 를 스탠드에 장착했습니다.",
                              "%s mounted on the stand.") % dict(PARTS)[key])
            return
        if key == "sample":
            if "holder" not in a.placed:
                self.status.set(T("먼저 시료 홀더와 스탠드를 배치하십시오.",
                                  "Place the sample holder and stand first."))
                return
            hx, hy = self.mm2px(a.holder)
            if math.hypot(ex - hx, ey - hy) > 34:
                self.status.set(
                    T("시료는 홀더에서 빼지 마십시오 \u2014 슬라이드 프레임은 홀더에 끼워야 합니다.",
                      "Do not remove the slide frame from its holder."))
                return
            a.sample_in_holder = True
            a.placed.add("sample")
            a.psi = self.app.rng.uniform(-3.0, 3.0) * DEG
            self.status.set(T("시료를 홀더에 끼웠습니다.",
                              "The sample sits in its holder."))
            return
        if key in ("tape", "ruler", "lamp"):
            a.placed.add(key)
            self.status.set(T("%s 준비 완료.", "%s ready.") % dict(PARTS)[key])
            return
        a.placed.add(key)
        if key == "stand":
            a.src = p
        elif key == "holder":
            a.holder = p
        elif key == "screen":
            a.screen = p
        elif key == "bench":
            a.bench = p
            a.stake = 0.0
            a.marks = []
        self.status.set(T("배치 완료: ", "placed: ") + dict(PARTS)[key])

    def rot_screen(self):
        self.app.screen_horiz = not self.app.screen_horiz
        self.invalidate()
        self.redraw()

    def rot_bench(self):
        self.app.bench_horiz = not self.app.bench_horiz
        self.app.stake = 0.0
        self.app.marks = []
        self.invalidate()
        self.redraw()

    def top_tape(self, e):
        a = self.app
        if "tape" not in a.placed:
            self.status.set(T("줄자를 먼저 꺼내십시오.", "Take out the tape measure."))
            return
        pt = (e.x, e.y)
        for pos in (a.src, a.holder, a.screen, a.bench, a.stake_xy()):
            px, py = self.mm2px(pos)
            if math.hypot(e.x - px, e.y - py) < 16:
                pt = (px, py)
                break
        self.tape_pts.append(pt)
        if len(self.tape_pts) > 2:
            self.tape_pts = [pt]
        if len(self.tape_pts) == 2:
            (x1, y1), (x2, y2) = self.tape_pts
            mm = math.hypot(x2 - x1, y2 - y1) / TOP_PX + a.read_bias
            self.tape_txt.set(T("줄자: %.0f mm", "tape: %.0f mm") % q(mm, 1.0))
        else:
            self.tape_txt.set(T("두 번째 점을 오른쪽 클릭",
                                "right-click the second point"))
        self.redraw()

    # ================================================================
    #  bench tab
    # ================================================================
    def _build_bench(self):
        a = self.app
        top = tk.Frame(self.t_ben, bg=BG)
        top.pack(fill="x", padx=6, pady=3)
        self.src_btn = tk.Button(top, text=T("광원 켜기", "source ON"),
                                 command=self.toggle_source)
        self.src_btn.pack(side="left")
        self.lamp_btn = tk.Button(top, text=T("탁상 램프", "desk lamp"),
                                  command=self.toggle_lamp)
        self.lamp_btn.pack(side="left", padx=4)
        tk.Button(top, text=T("시료 앞뒤 뒤집기", "turn the sample around"),
                  command=self.flip).pack(side="left", padx=4)
        tk.Label(top, text=T("  홀더 손잡이로 회전:", "  rotate with the handle:"),
                 bg=BG).pack(side="left")
        for txt, d in (("\u25c0\u25c0", -1.0), ("\u25c0", -0.2),
                       ("\u25b6", 0.2), ("\u25b6\u25b6", 1.0)):
            tk.Button(top, text=txt, width=3,
                      command=lambda d=d: self.rotate(d)).pack(side="left")
        tk.Label(top, textvariable=self.status, bg=BG,
                 font=("TkDefaultFont", 8)).pack(side="left", padx=8)

        tk.Label(self.t_ben, text=T("시료를 통해 본 모습 (시야 \u00b145\u00b0)",
                                    "the view through the sample (field \u00b145\u00b0)"),
                 bg=BG, anchor="w").pack(fill="x", padx=8)
        self.ce = tk.Canvas(self.t_ben, width=EYE_N, height=132, bg="#000",
                            highlightthickness=0)
        self.ce.pack(padx=6)

        row = tk.Frame(self.t_ben, bg=BG)
        row.pack(fill="x", padx=8)
        tk.Label(row, text=T("스크린 (모눈종이) \u2014 왼쪽 클릭 두 번으로 거리 측정",
                             "screen (mm paper) - click two points to measure"),
                 bg=BG).pack(side="left")
        tk.Label(row, textvariable=self.scr_txt, bg=BG, fg="#8a1c1c",
                 font=("TkDefaultFont", 10, "bold")).pack(side="right")
        self.cs = tk.Canvas(self.t_ben, width=EYE_N, height=196, bg=PAPER,
                            highlightthickness=0)
        self.cs.pack(padx=6)
        self.cs.bind("<Button-1>", self.screen_click)

        row2 = tk.Frame(self.t_ben, bg=BG)
        row2.pack(fill="x", padx=8)
        tk.Label(row2, text=T("벤치 근접도 \u2014 왼쪽 끌기: 막대 이동, 오른쪽 클릭: 자로 측정",
                              "bench close-up - left-drag the stake, right-click "
                              "to use the ruler"), bg=BG).pack(side="left")
        tk.Button(row2, text=T("벤치에 표시", "mark the bench"),
                  command=self.mark).pack(side="left", padx=6)
        tk.Button(row2, text=T("표시 지우기", "clear marks"),
                  command=self.clear_marks).pack(side="left")
        tk.Label(row2, textvariable=self.bench_txt, bg=BG, fg="#8a1c1c",
                 font=("TkDefaultFont", 10, "bold")).pack(side="right")
        self.cbn = tk.Canvas(self.t_ben, width=EYE_N, height=76,
                             bg="#c8a86a", highlightthickness=0)
        self.cbn.pack(padx=6)
        self.cbn.bind("<B1-Motion>", self.bench_drag)
        self.cbn.bind("<Button-1>", self.bench_drag)
        self.cbn.bind("<Button-3>", self.bench_measure)

        bot = tk.Frame(self.t_ben, bg=BG)
        bot.pack(fill="both", expand=True, padx=8, pady=4)
        tk.Button(bot, text=T("측정값 기록", "record the readings"),
                  command=self.record).pack(side="left", anchor="n")
        self.log = tk.Text(bot, height=6, font=("Courier", 8))
        self.log.pack(side="left", fill="both", expand=True, padx=6)

    # ---------------- controls ---------------------------------------
    def toggle_source(self):
        a = self.app
        if not a.mounted:
            self.status.set(T("스탠드에 광원이 장착되어 있지 않습니다.",
                              "No source is mounted on the stand."))
            return
        a.source_on = not a.source_on
        self.src_btn.configure(text=T("광원 끄기", "source OFF") if a.source_on
                               else T("광원 켜기", "source ON"))
        if a.source_on and a.mounted == "laser":
            self.status.set(T("경고: 레이저를 직접 또는 시료를 통해 보지 마십시오. "
                              "스크린을 사용하십시오.",
                              "WARNING: never look into the laser or through the "
                              "sample - use the screen."))
        self.invalidate()
        self.redraw()

    def toggle_lamp(self):
        if "lamp" not in self.app.placed:
            return
        self.app.lamp_on = not self.app.lamp_on
        self.invalidate()
        self.redraw()

    def flip(self):
        if not self.app.sample_in_holder:
            return
        self.app.flip = 1 - self.app.flip
        self.app.psi = -self.app.psi
        self.invalidate()
        self.redraw()

    def rotate(self, deg):
        if not self.app.sample_in_holder:
            return
        self.app.psi += deg * DEG
        self.invalidate()
        self.redraw()

    def mark(self):
        a = self.app
        if "bench" in a.placed:
            a.marks.append(a.stake)
            if len(a.marks) > 6:
                a.marks.pop(0)
            self.redraw()

    def clear_marks(self):
        self.app.marks = []
        self.redraw()

    def record(self):
        parts = [self.tape_txt.get(), self.scr_txt.get(), self.bench_txt.get()]
        line = " | ".join(p for p in parts if p)
        if line:
            self.log.insert("end", line + "\n")
            self.log.see("end")

    def invalidate(self):
        self._cache = None

    # ---------------- screen geometry --------------------------------
    def screen_mode(self):
        a = self.app
        if "screen" not in a.placed or not a.sample_in_holder:
            return None
        if not a.mounted or not a.source_on:
            return None
        nx, ny = (0.0, 1.0) if a.screen_horiz else (1.0, 0.0)
        d_scr = (a.screen[0] - a.holder[0]) * nx + (a.screen[1] - a.holder[1]) * ny
        d_src = (a.src[0] - a.holder[0]) * nx + (a.src[1] - a.holder[1]) * ny
        if abs(d_scr) < 30.0:
            return None
        kind = "refl" if d_scr * d_src > 0 else "trans"
        return kind + ("-laser" if a.mounted == "laser" else "-white")

    def screen_center(self):
        """Lateral coordinate (mm, relative to the screen centre) where the
        optical axis meets the plane of the screen."""
        a = self.app
        (ux, uy), L = a.axis()
        if L < 30.0:
            return None
        if a.screen_horiz:
            if abs(uy) < 0.15:
                return None
            t = (a.screen[1] - a.src[1]) / uy
            return (a.src[0] + t * ux) - a.screen[0]
        if abs(ux) < 0.15:
            return None
        t = (a.screen[0] - a.src[0]) / ux
        return (a.src[1] + t * uy) - a.screen[1]

    # ---------------- renders ---------------------------------------
    def render(self):
        if self._cache is not None:
            return self._cache
        a = self.app
        eye = None
        if a.sample_in_holder and a.mounted == "flashlight" and a.source_on:
            eye = self.opt.eye_columns(EYE_N, -EYE_A, EYE_A)
        scr = None
        mode = self.screen_mode()
        xc = self.screen_center()
        if mode and xc is not None:
            half = 0.5 * a.screen_w
            scr = (self.opt.screen_columns(EYE_N, -half - xc, half - xc, mode),
                   xc, mode)
        self._cache = (eye, scr)
        return self._cache

    def draw_eye(self):
        c = self.ce
        c.delete("all")
        a = self.app
        eye, _ = self.render()
        H = 132
        if eye is None:
            msg = T("(시료를 통해 볼 수 없습니다)", "(nothing to see through the sample)")
            if a.mounted == "laser" and a.source_on:
                msg = T("레이저는 시료를 통해 보지 마십시오! 스크린을 사용하십시오.",
                        "Never look at the laser through the sample - use the screen.")
            c.create_text(EYE_N / 2, H / 2, text=msg, fill="#d33",
                          font=("TkDefaultFont", 10))
            return
        R, G, B = eye
        lamp = a.lamp_on and "lamp" in a.placed
        amb = 0.075 if lamp else 0.012
        for i in range(EYE_N):
            r, g, b = [min(1.0, (v / REF_EYE) ** 0.5)
                       for v in (R[i], G[i], B[i])]
            if max(r, g, b) < amb:
                continue
            c.create_line(i, 26, i, 106, fill=hexcol(r, g, b))
        # the blue mark on the centre of the sample frame
        c.create_line(EYE_N / 2, 14, EYE_N / 2, 118, fill="#3a6ee8")
        # the stake, seen through the sample
        ang = a.stake_angle()
        if ang is not None and "bench" in a.placed:
            i = (ang + EYE_A) / (2 * EYE_A) * (EYE_N - 1)
            y = max(a.bench_distance(), 30.0)
            w = max(2.0, 6.0 / y / (2 * EYE_A) * (EYE_N - 1))
            if -w < i < EYE_N + w:
                c.create_rectangle(i - w / 2, 20, i + w / 2, 112,
                                   fill="#3a2a14", outline="#6b4a1e")
                c.create_line(i, 20, i, 112, fill="#8a6a3a")

    def draw_screen(self):
        c = self.cs
        c.delete("all")
        a = self.app
        _, scr = self.render()
        H = 196
        half = 0.5 * a.screen_w
        lamp = a.lamp_on and "lamp" in a.placed
        if lamp:
            paper, g1, g2, g3 = (0.95, 0.94, 0.89), "#e9e5d5", "#d8d2bd", "#b9b19a"
        else:
            paper, g1, g2, g3 = (0.20, 0.20, 0.18), "#33332e", "#3d3d37", "#4a4a42"
        c.configure(bg=hexcol(*paper))
        for xmm in range(int(-half), int(half) + 1):
            x = (xmm + half) * (EYE_N / a.screen_w)
            if xmm % 50 == 0:
                c.create_line(x, 0, x, H, fill=g3)
            elif xmm % 10 == 0:
                c.create_line(x, 0, x, H, fill=g2)
            elif xmm % 2 == 0:
                c.create_line(x, 0, x, H, fill=g1)
        for ymm in range(0, int(H / SCR_PX), 10):
            y = ymm * SCR_PX
            c.create_line(0, y, EYE_N, y, fill=g2)
        hole = half * (EYE_N / a.screen_w)
        hr = 0.5 * a.screen_hole * SCR_PX
        c.create_oval(hole - hr, H / 2 - hr, hole + hr, H / 2 + hr,
                      fill="#101010", outline="#555")
        if scr is None:
            c.create_text(EYE_N / 2, 16,
                          text=T("(스크린에 무늬가 없습니다)",
                                 "(no pattern on the screen)"),
                          fill="#888" if lamp else "#666")
            return
        (R, G, B), xc, mode = scr
        ref = REF_SCR_LASER if mode.endswith("laser") else REF_SCR_WHITE
        thr = 0.16 if lamp else 0.035
        for i in range(EYE_N):
            r, g, b = [min(1.0, (v / ref) ** 0.5) for v in (R[i], G[i], B[i])]
            if max(r, g, b) < thr:
                continue
            col = hexcol(min(1.0, paper[0] + r), min(1.0, paper[1] + g),
                         min(1.0, paper[2] + b))
            c.create_line(i, H / 2 - 34, i, H / 2 + 34, fill=col)
        for (px, py) in self.scr_pts:
            c.create_line(px - 8, py, px + 8, py, fill="#b02", width=2)
            c.create_line(px, py - 8, px, py + 8, fill="#b02", width=2)

    def draw_bench(self):
        c = self.cbn
        c.delete("all")
        a = self.app
        if "bench" not in a.placed:
            c.create_text(EYE_N / 2, 38, text=T("(벤치가 없습니다)", "(no bench)"),
                          fill="#5a4520")
            return
        span = EYE_N / BEN_PX
        for xmm in range(int(-span / 2), int(span / 2) + 1, 10):
            x = (xmm + span / 2) * BEN_PX
            c.create_line(x, 52, x, 62 if xmm % 50 else 68, fill="#7a5f30")
        c.create_rectangle(0, 16, EYE_N, 52, fill="#c8a86a", outline="#8a6f3c")
        for mk in a.marks:
            x = (mk + span / 2) * BEN_PX
            c.create_line(x, 16, x, 52, fill="#b02", width=2)
        x = (a.stake + span / 2) * BEN_PX
        c.create_rectangle(x - 6, 4, x + 6, 44, fill="#6b4a1e",
                           outline="#2f200c")
        c.create_line(x, 4, x, 44, fill="#c9a86a")
        for (px, py) in self.bench_pts:
            c.create_line(px, 0, px, 76, fill="#0a5", width=1)
            c.create_line(px - 6, py, px + 6, py, fill="#0a5", width=2)

    # ---------------- measurement clicks -----------------------------
    def screen_click(self, e):
        self.scr_pts.append((e.x, e.y))
        if len(self.scr_pts) > 2:
            self.scr_pts = [(e.x, e.y)]
        if len(self.scr_pts) == 2:
            dx = abs(self.scr_pts[1][0] - self.scr_pts[0][0])
            mm = dx / (EYE_N / self.app.screen_w)
            self.scr_txt.set(T("스크린 거리: %.1f mm", "on the screen: %.1f mm")
                             % q(mm, 0.5))
        else:
            self.scr_txt.set(T("두 번째 점을 클릭", "click the second point"))
        self.draw_screen()

    def bench_drag(self, e):
        a = self.app
        if "bench" not in a.placed:
            return
        span = EYE_N / BEN_PX
        off = e.x / BEN_PX - span / 2
        a.stake = max(-0.5 * a.bench_len, min(0.5 * a.bench_len, off))
        self.invalidate()
        self.redraw()

    def bench_measure(self, e):
        if "ruler" not in self.app.placed:
            self.status.set(T("자를 먼저 꺼내십시오.", "Take out the ruler first."))
            return
        pt = (e.x, e.y)
        span = EYE_N / BEN_PX
        for mk in self.app.marks:
            x = (mk + span / 2) * BEN_PX
            if abs(e.x - x) < 8:
                pt = (x, e.y)
                break
        self.bench_pts.append(pt)
        if len(self.bench_pts) > 2:
            self.bench_pts = [pt]
        if len(self.bench_pts) == 2:
            mm = abs(self.bench_pts[1][0] - self.bench_pts[0][0]) / BEN_PX
            self.bench_txt.set(T("벤치 위 거리: %.1f mm", "on the bench: %.1f mm")
                               % q(mm, 0.5))
        else:
            self.bench_txt.set(T("두 번째 점을 오른쪽 클릭",
                                 "right-click the second point"))
        self.draw_bench()

    # ---------------- global redraw ----------------------------------
    def redraw(self):
        self.draw_box()
        self.draw_top()
        self.draw_eye()
        self.draw_screen()
        self.draw_bench()


def main():
    import sys
    global LANG
    seed = None
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--seed" and i + 1 < len(args):
            seed = int(args[i + 1])
        if a == "--lang" and i + 1 < len(args):
            LANG = args[i + 1]
    root = tk.Tk()
    Sim(root, seed)
    root.mainloop()


if __name__ == "__main__":
    main()
