#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  46th International Physics Olympiad  (IPhO 2015, Mumbai, India)
  Experimental Problem E-I :  DIFFRACTION DUE TO HELICAL STRUCTURE
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The simulator shows ONLY what the real instruments show -- the X-shaped
    pattern on the pattern marking sheet, the pencil marks, the digital caliper
    and the measuring tape.  The wire thickness, the pitch, the helix radius,
    the angles and the separations are NEVER computed or displayed.
    All hidden true parameters are randomised for every session.
"""

import math
import random
import tkinter as tk
from tkinter import ttk, messagebox

# --------------------------------------------------------------------------
# i18n
# --------------------------------------------------------------------------
LANG = "ko"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


LAM = 635e-6          # laser wavelength in mm  (635 nm)

# --------------------------------------------------------------------------
# Hidden physics
# --------------------------------------------------------------------------


class E1Physics:
    """Hidden true parameters of the two samples and of the optical bench."""

    def __init__(self, seed=None):
        r = random.Random(seed)
        self.seed = seed

        # ---- Sample I : helical spring -----------------------------------
        self.a1 = r.uniform(0.142, 0.160)        # wire thickness      [mm]
        self.P = r.uniform(0.86, 0.96)           # pitch               [mm]
        self.R = r.uniform(0.70, 0.80)           # helix radius        [mm]
        self.alpha1 = math.atan(self.P / (2.0 * math.pi * self.R))
        self.d1 = self.P * math.cos(self.alpha1)  # projected spacing  [mm]

        # ---- Sample II : printed double-helix-like pattern ---------------
        self.a2 = r.uniform(0.045, 0.053)        # line thickness      [mm]
        self.s2 = r.uniform(0.235, 0.262)        # separation of helices
        self.d2 = r.uniform(0.95, 1.05)          # perpendicular pitch
        self.alpha2 = math.radians(r.uniform(9.7, 10.9))

        # ---- Bench geometry (mm) -----------------------------------------
        #  far configuration :  sample -> left mirror -> right mirror -> screen
        self.leg1 = r.uniform(780.0, 830.0)
        self.leg2 = r.uniform(1080.0, 1130.0)
        self.leg3 = r.uniform(840.0, 900.0)
        self.D_far = self.leg1 + self.leg2 + self.leg3
        #  near configuration (Fig. 6) : sample -> screen, direct
        self.D_near = r.uniform(775.0, 815.0)

        # ---- initial mis-alignment ---------------------------------------
        self.base_dx = r.uniform(-55.0, 55.0)    # mm on the screen
        self.base_dy = r.uniform(-55.0, 55.0)
        self.base_tilt = r.uniform(-12.0, 12.0)  # screen tilt, degrees
        self.focus_opt = r.uniform(-0.35, 0.35)  # best lens-cap setting

        # measurement noise
        self.pencil_sigma = 0.10                 # mm, pencil mark scatter
        self.caliper_sigma = 0.008               # mm
        self.tape_sigma = 1.2                    # mm

    # -------- projected-object geometry used by the diffraction model ----
    def object_params(self, kind):
        """Return (a, spacings, alpha) of the projected wire set."""
        if kind == "I":
            return self.a1, (self.d1, None), self.alpha1
        return self.a2, (self.d2, self.s2), self.alpha2


# --------------------------------------------------------------------------
# Diffraction model
# --------------------------------------------------------------------------


def _sinc2(x):
    if abs(x) < 1e-9:
        return 1.0
    s = math.sin(x) / x
    return s * s


def arm_profile_value(u, D, kind, phys, N):
    """Intensity along one arm of the X pattern (normalised to 1 at u = 0).

    u : distance from the centre of the pattern measured along the arm  [mm]
    D : sample-screen distance                                          [mm]
    N : number of illuminated turns (wires per set)
    """
    a, (d, s), _ = phys.object_params(kind)
    beta = math.pi * a * u / (LAM * D)
    env = _sinc2(beta)

    delta = math.pi * d * u / (LAM * D)
    sd = math.sin(delta)
    if abs(sd) < 1e-12:
        struct = float(N * N)
    else:
        struct = (math.sin(N * delta) / sd) ** 2
    val = env * struct / float(N * N)

    if s is not None:                       # double helix : extra pair term
        val *= math.cos(math.pi * s * u / (LAM * D)) ** 2
    return val


class ArmField:
    """Pre-tabulated 1-D profiles used by the renderer (fast pixel lookup)."""

    UMAX = 230.0
    USTEP = 0.02
    VMAX = 26.0
    VSTEP = 0.04

    def __init__(self, rig):
        p = rig.p
        self.kind = rig.sample
        self.D = rig.D()
        self.N = rig.illuminated_turns()
        _, _, self.alpha = p.object_params(self.kind)

        n = int(self.UMAX / self.USTEP)
        self.n = n
        prof = [0.0] * (2 * n + 1)
        for i in range(-n, n + 1):
            prof[i + n] = arm_profile_value(i * self.USTEP, self.D,
                                            self.kind, p, self.N)

        blur = rig.blur_mm()
        w = int(blur / self.USTEP)
        if w >= 1:
            pre = [0.0] * (len(prof) + 1)
            acc = 0.0
            for i, v in enumerate(prof):
                acc += v
                pre[i + 1] = acc
            sm = [0.0] * len(prof)
            L = len(prof)
            for i in range(L):
                lo = max(0, i - w)
                hi = min(L, i + w + 1)
                sm[i] = (pre[hi] - pre[lo]) / (hi - lo)
            prof = sm
        self.F = prof

        sig = rig.sigma_v()
        self.sigma = sig
        m = int(self.VMAX / self.VSTEP)
        self.m = m
        self.G = [math.exp(-(((i * self.VSTEP) ** 2) / (2.0 * sig * sig)))
                  for i in range(-m, m + 1)]

    def f(self, u):
        t = (u + self.UMAX) / self.USTEP
        i = int(t)
        if i < 0 or i >= 2 * self.n:
            return 0.0
        a = t - i
        return self.F[i] * (1.0 - a) + self.F[i + 1] * a

    def g(self, v):
        t = (v + self.VMAX) / self.VSTEP
        i = int(t)
        if i < 0 or i >= 2 * self.m:
            return 0.0
        a = t - i
        return self.G[i] * (1.0 - a) + self.G[i + 1] * a

    def value(self, X, Y):
        """X, Y measured from the centre of the pattern, in mm."""
        sa = math.sin(self.alpha)
        ca = math.cos(self.alpha)
        u1 = -X * sa + Y * ca
        v1 = X * ca + Y * sa
        u2 = X * sa + Y * ca
        v2 = X * ca - Y * sa
        return self.f(u1) * self.g(v1) + self.f(u2) * self.g(v2)


# --------------------------------------------------------------------------
# Apparatus / assembly
# --------------------------------------------------------------------------

PARTS = [
    # key,      no,  ko,                        en,                            slot
    ("psu",     "3", "DC 안정화 전원공급장치",   "DC regulated power supply",    "table_psu"),
    ("goggles", "18", "레이저 보안경",           "Laser safety goggles",         "wear"),
    ("laser",   "2", "레이저 광원 + 마운트",     "Laser source with mount",      "rail_laser"),
    ("holder",  "4", "시료 홀더",               "Sample holder with base",      "rail_holder"),
    ("refL",    "5", "왼쪽 반사경",             "Left reflector",               "rail_refL"),
    ("refR",    "6", "오른쪽 반사경",           "Right reflector",              "rail_refR"),
    ("screen",  "7", "스크린 + 마운트",         "Screen with mount",            "rail_screen"),
    ("clips",   "11", "플라스틱 클립",           "Plastic clips",                "screen_clip"),
    ("sheet",   "17", "패턴 마킹 시트",          "Pattern marking sheet",        "screen_sheet"),
    ("mirror",  "8", "평면 거울 (정렬용)",       "Plane mirror (alignment)",     "screen_mirror"),
    ("caliper", "14", "디지털 캘리퍼 + 마운트",  "Digital caliper with mount",   "table_tools"),
    ("tape",    "16", "줄자 (1.5 m)",           "Measuring tape (1.5 m)",       "table_tools"),
    ("pencil",  "13", "샤프 펜슬",               "Mechanical pencil",            "table_tools"),
    ("scale",   "15", "플라스틱 자 (30 cm)",     "Plastic scale (30 cm)",        "table_tools"),
    ("sticker", "12", "원형 검정 스티커",        "Circular black stickers",      "table_tools"),
    ("flash",   "19", "손전등",                  "Battery operated flashlight",  "table_tools"),
    ("sample1", "9", "시료 I (나선 스프링)",     "Sample I (helical spring)",    "holder_slot"),
    ("sample2", "10", "시료 II (이중나선 패턴)", "Sample II (double-helix)",     "holder_slot"),
]

PART_BY_KEY = {p[0]: p for p in PARTS}

# prerequisites : part -> set of parts that must already be installed
PREREQ = {
    "laser": {"psu"},
    "clips": {"screen"},
    "sheet": {"screen", "clips"},
    "mirror": {"screen", "clips"},
    "sample1": {"holder"},
    "sample2": {"holder"},
}

SLOT_LABELS = {
    "table_psu":     ("작업대 - 전원부", "Bench - power"),
    "wear":          ("착용", "Wear"),
    "rail_laser":    ("플랫폼 - 레이저 자리", "Platform - laser seat"),
    "rail_holder":   ("플랫폼 - 시료 자리", "Platform - sample seat"),
    "rail_refL":     ("플랫폼 - 좌측 반사경 자리", "Platform - left mirror seat"),
    "rail_refR":     ("플랫폼 - 우측 반사경 자리", "Platform - right mirror seat"),
    "rail_screen":   ("플랫폼 - 스크린 자리", "Platform - screen seat"),
    "screen_clip":   ("스크린 - 클립", "Screen - clips"),
    "screen_sheet":  ("스크린 - 시트", "Screen - sheet"),
    "screen_mirror": ("스크린 - 거울", "Screen - mirror"),
    "table_tools":   ("작업대 - 공구", "Bench - tools"),
    "holder_slot":   ("시료 홀더", "Sample holder"),
}

BENCH_REQUIRED = ["psu", "goggles", "laser", "holder", "refL", "refR",
                  "screen", "clips", "sheet", "caliper", "tape", "pencil"]


class Mark:
    __slots__ = ("x", "y", "idx")

    def __init__(self, x, y, idx):
        self.x = x
        self.y = y
        self.idx = idx


class Sheet:
    def __init__(self, label):
        self.label = label
        self.marks = []
        self.stickers = []

    def add_mark(self, x, y):
        m = Mark(x, y, len(self.marks) + 1)
        self.marks.append(m)
        return m


class E1Rig:
    """Complete state of the E-I optical bench.  Usable without a GUI."""

    SHEET_W = 90.0      # marking box, mm
    SHEET_H = 300.0

    def __init__(self, phys):
        self.p = phys
        self.rng = random.Random((phys.seed or 0) * 7919 + 13)
        self.installed = set()
        self.log = []

        self.laser_on = False
        self.intensity = "high"        # high / low
        self.room_light = True
        self.sample = None             # 'I' | 'II' | None
        self.screen_pos = "far"        # 'far' | 'near'

        # adjustment knobs
        self.knob_lx = 0.0             # laser lateral   (-10 .. 10)
        self.knob_ly = 0.0             # laser height
        self.knob_tL = 0.0             # left  mirror tilt (-10 .. 10)
        self.knob_tR = 0.0             # right mirror tilt
        self.knob_tilt = 0.0           # screen tilt knob, degrees (-15 .. 15)
        self.knob_focus = 0.0          # lens cap (-1 .. 1)
        self.spot_h = 3.0              # illuminated height on sample, mm

        self.sheets = []
        self.cur_sheet = -1

    # ---------------- assembly ------------------------------------------
    def can_install(self, key):
        if key in self.installed:
            return False, T("이미 설치되어 있습니다.", "Already installed.")
        need = PREREQ.get(key, set())
        missing = need - self.installed
        if missing:
            names = ", ".join(T(PART_BY_KEY[k][2], PART_BY_KEY[k][3])
                              for k in sorted(missing))
            return False, T("먼저 설치해야 합니다: ", "Install first: ") + names
        if key in ("sample1", "sample2"):
            other = "sample2" if key == "sample1" else "sample1"
            if other in self.installed:
                return False, T("시료 홀더에는 시료를 하나만 장착할 수 있습니다.",
                                "Only one sample fits in the holder.")
        if key == "mirror" and "sheet" in self.installed:
            return False, T("시트가 이미 스크린에 고정되어 있습니다. "
                            "정렬용 거울을 먼저 사용하십시오.",
                            "The sheet is already clipped on. Use the "
                            "alignment mirror first.")
        return True, ""

    def install(self, key, slot=None):
        part = PART_BY_KEY.get(key)
        if part is None:
            return False, T("알 수 없는 부품입니다.", "Unknown part.")
        if slot is not None and slot != part[4]:
            return False, T("이 부품의 자리가 아닙니다.",
                            "This is not the seat for that part.")
        ok, msg = self.can_install(key)
        if not ok:
            return False, msg
        self.installed.add(key)
        if key == "sample1":
            self.sample = "I"
        elif key == "sample2":
            self.sample = "II"
        if key == "sheet" and not self.sheets:
            self.new_sheet()
        self.log.append("install:" + key)
        return True, T("설치 완료", "Installed")

    def remove(self, key):
        if key not in self.installed:
            return False, T("설치되어 있지 않습니다.", "Not installed.")
        if key in ("screen", "clips") and "sheet" in self.installed:
            return False, T("시트를 먼저 떼어내십시오.", "Remove the sheet first.")
        self.installed.discard(key)
        if key == "sample1" and self.sample == "I":
            self.sample = None
        if key == "sample2" and self.sample == "II":
            self.sample = None
        self.log.append("remove:" + key)
        return True, T("분리 완료", "Removed")

    def bench_ready(self):
        missing = [k for k in BENCH_REQUIRED if k not in self.installed]
        return (len(missing) == 0), missing

    # ---------------- optics --------------------------------------------
    def D(self):
        return self.p.D_far if self.screen_pos == "far" else self.p.D_near

    def tilt_deg(self):
        return self.p.base_tilt + self.knob_tilt

    def offsets(self):
        """Position of the centre of the pattern on the sheet, in mm."""
        p = self.p
        ox = p.base_dx + 7.0 * self.knob_lx
        oy = p.base_dy + 7.0 * self.knob_ly
        if self.screen_pos == "far":
            ox += 13.0 * self.knob_tR
            oy += 13.0 * self.knob_tL
        else:
            ox += 0.0
        return ox, oy

    def retro_offset(self):
        """Offset of the beam returning from the plane mirror, in mm.

        Horizontal : lateral aim of the beam on the screen.
        Vertical   : twice the screen tilt times the optical path.
        """
        ox, _ = self.offsets()
        return (0.40 * ox,
                2.0 * math.tan(math.radians(self.tilt_deg())) * self.D())

    def illuminated_turns(self):
        """Number of turns / periods illuminated by the beam."""
        pitch = self.p.P if self.sample == "I" else self.p.d2
        n = int(self.spot_h / pitch)
        return max(1, min(8, n))

    def blur_mm(self):
        e = abs(self.knob_focus - self.p.focus_opt)
        return 0.05 + 3.0 * e * e * (self.D() / 1000.0)

    def sigma_v(self):
        e = abs(self.knob_focus - self.p.focus_opt)
        return 0.0006 * self.D() * (1.0 + 3.0 * e)

    def pattern_status(self):
        """(visible, message)."""
        if not self.laser_on:
            return False, T("레이저가 꺼져 있습니다.", "The laser is off.")
        if "sheet" not in self.installed:
            return False, T("스크린에 패턴 마킹 시트가 없습니다.",
                            "No pattern marking sheet on the screen.")
        if "mirror" in self.installed:
            return False, T("정렬용 평면 거울이 스크린을 가리고 있습니다.",
                            "The alignment mirror covers the screen.")
        if self.sample is None:
            return False, T("시료 홀더가 비어 있습니다 (직진 빔만 보입니다).",
                            "The sample holder is empty (undiffracted beam only).")
        ox, oy = self.offsets()
        if abs(ox) > self.SHEET_W / 2 + 25 or abs(oy) > self.SHEET_H / 2 + 25:
            return False, T("빔이 시트를 벗어났습니다.",
                            "The beam misses the sheet.")
        return True, ""

    def field(self):
        return ArmField(self)

    # ---------------- sheets & marking ----------------------------------
    def new_sheet(self):
        self.sheets.append(Sheet("P-%d" % (len(self.sheets) + 1)))
        self.cur_sheet = len(self.sheets) - 1
        return self.sheets[-1]

    def sheet(self):
        if 0 <= self.cur_sheet < len(self.sheets):
            return self.sheets[self.cur_sheet]
        return None

    def mark(self, x, y):
        """Place a pencil mark.  A small random scatter models the pencil."""
        sh = self.sheet()
        if sh is None:
            return None, T("시트가 없습니다.", "No sheet.")
        if "pencil" not in self.installed:
            return None, T("샤프 펜슬이 없습니다.", "No pencil available.")
        if abs(x) > self.SHEET_W / 2 or abs(y) > self.SHEET_H / 2:
            return None, T("마킹 박스 밖입니다.", "Outside the marking box.")
        s = self.p.pencil_sigma
        m = sh.add_mark(x + self.rng.gauss(0, s), y + self.rng.gauss(0, s))
        return m, ""

    def add_sticker(self, x, y):
        sh = self.sheet()
        if sh is None or "sticker" not in self.installed:
            return False
        sh.stickers.append((x, y, 4.0))
        return True

    # ---------------- instruments ---------------------------------------
    def caliper(self, i, j):
        """Digital caliper reading between two marks of the current sheet."""
        if "caliper" not in self.installed:
            return None, T("디지털 캘리퍼가 없습니다.", "No digital caliper.")
        sh = self.sheet()
        if sh is None:
            return None, T("시트가 없습니다.", "No sheet.")
        n = len(sh.marks)
        if not (1 <= i <= n and 1 <= j <= n) or i == j:
            return None, T("마크 번호가 올바르지 않습니다.", "Invalid mark numbers.")
        a, b = sh.marks[i - 1], sh.marks[j - 1]
        d = math.hypot(a.x - b.x, a.y - b.y)
        d += self.rng.gauss(0, self.p.caliper_sigma)
        return round(d, 2), ""

    TAPE_POINTS = ["sample", "refL", "refR", "screen_far", "screen_near"]

    def tape(self, p1, p2):
        """Measuring tape between two points of the bench, in mm."""
        if "tape" not in self.installed:
            return None, T("줄자가 없습니다.", "No measuring tape.")
        p = self.p
        seg = {
            ("sample", "refL"): p.leg1,
            ("refL", "refR"): p.leg2,
            ("refR", "screen_far"): p.leg3,
            ("sample", "screen_near"): p.D_near,
        }
        key = (p1, p2) if (p1, p2) in seg else (p2, p1)
        if key not in seg:
            return None, T("줄자로 직접 잴 수 없는 구간입니다 (광선 경로가 아님).",
                           "That span is not along the beam path.")
        v = seg[key] + self.rng.gauss(0, p.tape_sigma)
        return round(v), ""


# --------------------------------------------------------------------------
# Pattern renderer
# --------------------------------------------------------------------------


def make_palette(base):
    pal = []
    for v in range(256):
        r = min(255, base + v)
        g = min(255, base + int(max(0, v - 170) * 1.5))
        b = min(255, base + int(max(0, v - 200) * 2.0))
        pal.append("#%02x%02x%02x" % (r, g, b))
    return pal


_TONE = [int(255.0 * ((i / 1023.0) ** 0.35)) for i in range(1024)]
TABLE_COLOR = "#242424"


class PatternCanvas(tk.Canvas):
    """Shows the pattern-marking sheet clipped to the screen."""

    BASE_PPM = 2.0

    def __init__(self, master, rig, on_status, **kw):
        tk.Canvas.__init__(self, master, bg="#101010", highlightthickness=0, **kw)
        self.rig = rig
        self.on_status = on_status
        self.zoom = 1.0
        self.vx = 0.0            # view centre, sheet mm
        self.vy = 0.0
        self.mode = "mark"       # mark | sticker | pan
        self.img = None
        self._drag = None
        self.bind("<Button-1>", self._click)
        self.bind("<B1-Motion>", self._drag_move)
        self.bind("<ButtonRelease-1>", self._drag_end)
        self.bind("<Configure>", lambda e: self.redraw())

    # ---- coordinate helpers
    def ppm(self):
        return self.BASE_PPM * self.zoom

    def to_sheet(self, px, py):
        w = self.winfo_width()
        h = self.winfo_height()
        p = self.ppm()
        return (self.vx + (px - w / 2.0) / p, self.vy + (py - h / 2.0) / p)

    def to_px(self, x, y):
        w = self.winfo_width()
        h = self.winfo_height()
        p = self.ppm()
        return (w / 2.0 + (x - self.vx) * p, h / 2.0 + (y - self.vy) * p)

    # ---- interaction
    def _click(self, ev):
        if self.mode == "pan":
            self._drag = (ev.x, ev.y, self.vx, self.vy)
            return
        x, y = self.to_sheet(ev.x, ev.y)
        if self.mode == "mark":
            m, msg = self.rig.mark(x, y)
            if m is None:
                self.on_status(msg)
            else:
                self.on_status(T("마크 #%d 표시", "Mark #%d placed") % m.idx)
        elif self.mode == "sticker":
            if not self.rig.add_sticker(x, y):
                self.on_status(T("검정 스티커가 없습니다.", "No black stickers."))
        self.redraw()

    def _drag_move(self, ev):
        if self._drag is None:
            return
        x0, y0, vx, vy = self._drag
        p = self.ppm()
        self.vx = vx - (ev.x - x0) / p
        self.vy = vy - (ev.y - y0) / p
        self.redraw()

    def _drag_end(self, ev):
        self._drag = None

    # ---- rendering
    def redraw(self):
        self.delete("all")
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        rig = self.rig
        ok, msg = rig.pattern_status()
        base = 96 if rig.room_light else 14
        pal = make_palette(base)
        ppm = self.ppm()
        dx = 1.0 / ppm
        x0 = self.vx - (w / 2.0) / ppm
        y0 = self.vy - (h / 2.0) / ppm

        HW = rig.SHEET_W / 2.0
        HH = rig.SHEET_H / 2.0
        paper = pal[0]

        if not ok:
            rows = []
            for py in range(h):
                Ys = y0 + py * dx
                if abs(Ys) > HH:
                    rows.append("{" + " ".join([TABLE_COLOR] * w) + "}")
                    continue
                row = []
                for px in range(w):
                    Xs = x0 + px * dx
                    row.append(paper if abs(Xs) <= HW else TABLE_COLOR)
                rows.append("{" + " ".join(row) + "}")
            self.img = tk.PhotoImage(width=w, height=h)
            self.img.put(" ".join(rows))
            self.create_image(0, 0, image=self.img, anchor="nw")
            self.create_text(w / 2, 24, text=msg, fill="#ffcc55",
                             font=("TkDefaultFont", 10))
            self._overlay()
            return

        field = rig.field()
        ox, oy = rig.offsets()
        ct = math.cos(math.radians(rig.tilt_deg()))
        sa = math.sin(field.alpha)
        ca = math.cos(field.alpha)
        amp = 1.0 if rig.intensity == "high" else 0.42
        inv = amp / 0.95
        lim = min(field.VMAX, 4.2 * field.sigma)
        F, G = field.F, field.G
        UM, US, nF = field.UMAX, field.USTEP, 2 * field.n
        VM, VS, nG = field.VMAX, field.VSTEP, 2 * field.m
        tone = _TONE
        p0 = pal[0]
        tbl = TABLE_COLOR

        rows = []
        for py in range(h):
            Ys = y0 + py * dx
            if abs(Ys) > HH:
                rows.append("{" + " ".join([tbl] * w) + "}")
                continue
            Y = (Ys - oy) * ct
            row = [p0] * w
            for px in range(w):
                if abs(x0 + px * dx) > HW:
                    row[px] = tbl
            # only the two narrow streaks carry light
            for sgn in (1.0, -1.0):
                # v = (Xs-ox)*ca + sgn*Y*sa  ;  |v| <= lim
                xa = (-lim - sgn * Y * sa) / ca + ox
                xb = (lim - sgn * Y * sa) / ca + ox
                if xa > xb:
                    xa, xb = xb, xa
                ia = max(0, int((xa - x0) / dx))
                ib = min(w - 1, int((xb - x0) / dx) + 1)
                if ia > ib:
                    continue
                X = x0 + ia * dx - ox
                u = -sgn * X * sa + Y * ca
                v = X * ca + sgn * Y * sa
                du = -sgn * dx * sa
                dv = dx * ca
                for px in range(ia, ib + 1):
                    if abs(x0 + px * dx) <= HW:
                        tu = (u + UM) / US
                        iu = int(tu)
                        if 0 <= iu < nF:
                            au = tu - iu
                            fv = F[iu] * (1.0 - au) + F[iu + 1] * au
                            if fv > 1e-7:
                                tv = (v + VM) / VS
                                iv = int(tv)
                                if 0 <= iv < nG:
                                    av = tv - iv
                                    gv = G[iv] * (1.0 - av) + G[iv + 1] * av
                                    I = fv * gv
                                    if I > 0.0:
                                        t = I * inv
                                        if t > 1.0:
                                            t = 1.0
                                        c = pal[tone[int(t * 1023)]]
                                        if c != p0:
                                            # brighter of the two streaks
                                            row[px] = c
                    u += du
                    v += dv
            rows.append("{" + " ".join(row) + "}")

        self.img = tk.PhotoImage(width=w, height=h)
        self.img.put(" ".join(rows))
        self.create_image(0, 0, image=self.img, anchor="nw")
        self._overlay()

    def _overlay(self):
        rig = self.rig
        sh = rig.sheet()
        # marking box border
        x1, y1 = self.to_px(-rig.SHEET_W / 2, -rig.SHEET_H / 2)
        x2, y2 = self.to_px(rig.SHEET_W / 2, rig.SHEET_H / 2)
        self.create_rectangle(x1, y1, x2, y2, outline="#5599ff", dash=(4, 3))
        if sh is None:
            return
        for (cx, cy, r) in sh.stickers:
            px, py = self.to_px(cx, cy)
            rr = r * self.ppm()
            self.create_oval(px - rr, py - rr, px + rr, py + rr,
                             fill="#000000", outline="#333333")
        for m in sh.marks:
            px, py = self.to_px(m.x, m.y)
            self.create_line(px - 5, py, px + 5, py, fill="#39ff88")
            self.create_line(px, py - 5, px, py + 5, fill="#39ff88")
            self.create_text(px + 11, py - 8, text=str(m.idx), fill="#39ff88",
                             font=("TkDefaultFont", 7), anchor="w")


# --------------------------------------------------------------------------
# Assembly tab
# --------------------------------------------------------------------------

SLOT_BOXES = {
    "table_psu":     (300, 40, 430, 84),
    "wear":          (450, 40, 560, 84),
    "table_tools":   (580, 40, 880, 84),
    "rail_refL":     (300, 150, 342, 330),
    "rail_screen":   (360, 165, 440, 315),
    "rail_holder":   (660, 205, 748, 250),
    "holder_slot":   (660, 258, 748, 300),
    "rail_laser":    (766, 205, 858, 250),
    "rail_refR":     (876, 150, 918, 330),
    "screen_clip":   (360, 322, 440, 352),
    "screen_sheet":  (360, 358, 440, 388),
    "screen_mirror": (360, 394, 440, 424),
}


class AssemblyTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.rig = app.rig
        self.drag = None

        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=4)
        ttk.Label(top, text=T("부품을 끌어서 알맞은 자리에 놓으십시오. "
                              "설치 순서가 맞아야 합니다.",
                              "Drag each part onto its seat. "
                              "The order of installation matters."),
                  font=("TkDefaultFont", 10, "bold")).pack(side="left")

        self.cv = tk.Canvas(self, width=940, height=620, bg="#f2efe6",
                            highlightthickness=0)
        self.cv.pack(fill="both", expand=True, padx=6, pady=4)
        self.status = ttk.Label(self, text="", foreground="#a03000")
        self.status.pack(fill="x", padx=8, pady=(0, 6))

        self.cv.bind("<Button-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_move)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Button-3>", self.on_right)
        self.redraw()

    # ------------------------------------------------------------------
    def redraw(self):
        cv = self.cv
        cv.delete("all")
        cv.create_rectangle(272, 120, 936, 470, fill="#d9c39a",
                            outline="#a98d5b", width=2)
        cv.create_text(604, 132, text=T("나무 플랫폼 [1] (윗면 도면)",
                                        "Wooden platform [1] (top view)"),
                       font=("TkDefaultFont", 9, "italic"), fill="#6b5628")
        for y in (196, 340):
            cv.create_rectangle(300, y, 918, y + 12, fill="#3a3a3a",
                                outline="#222222")
        cv.create_text(604, 452, text=T("가이드 레일", "guiding rails"),
                       font=("TkDefaultFont", 8), fill="#6b5628")

        for slot, (x1, y1, x2, y2) in SLOT_BOXES.items():
            occupied = [k for k in self.rig.installed
                        if PART_BY_KEY[k][4] == slot]
            fill = "#bfe8c0" if occupied else "#ffffff"
            cv.create_rectangle(x1, y1, x2, y2, outline="#7a7a7a",
                                dash=() if occupied else (3, 3), fill=fill)
            lab = T(*SLOT_LABELS[slot])
            cv.create_text((x1 + x2) / 2, y1 - 8, text=lab,
                           font=("TkDefaultFont", 7), fill="#555555")
            if occupied:
                names = "\n".join("[%s] %s" % (PART_BY_KEY[k][1],
                                               T(PART_BY_KEY[k][2],
                                                 PART_BY_KEY[k][3]))
                                  for k in occupied)
                cv.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=names,
                               font=("TkDefaultFont", 7), width=x2 - x1 - 6)

        # parts palette
        cv.create_text(130, 24, text=T("부품 목록", "Apparatus"),
                       font=("TkDefaultFont", 10, "bold"))
        y = 42
        self.palette = {}
        for key, no, ko, en, slot in PARTS:
            done = key in self.rig.installed
            col = "#cfcfcf" if done else "#ffffff"
            r = cv.create_rectangle(14, y, 258, y + 30, fill=col,
                                    outline="#999999")
            t = cv.create_text(20, y + 15, anchor="w",
                               text="[%s] %s" % (no, T(ko, en)),
                               font=("TkDefaultFont", 8))
            self.palette[key] = (r, t, y)
            y += 32

        ok, missing = self.rig.bench_ready()
        msg = (T("실험대 사용 준비 완료.", "Bench ready.") if ok else
               T("실험대 사용에 더 필요한 부품: ", "Still required for the bench: ")
               + ", ".join("[%s]" % PART_BY_KEY[k][1] for k in missing))
        cv.create_text(604, 494, text=msg, font=("TkDefaultFont", 9,
                                                 "bold" if ok else "normal"),
                       fill="#116611" if ok else "#a03000")
        cv.create_text(604, 516,
                       text=T("우클릭: 설치된 부품 분리",
                              "Right click on a seat: remove the part"),
                       font=("TkDefaultFont", 8), fill="#666666")

    # ------------------------------------------------------------------
    def part_at(self, x, y):
        for key, (r, t, y0) in self.palette.items():
            if 14 <= x <= 258 and y0 <= y <= y0 + 30:
                return key
        return None

    def slot_at(self, x, y):
        for slot, (x1, y1, x2, y2) in SLOT_BOXES.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                return slot
        return None

    def on_press(self, ev):
        key = self.part_at(ev.x, ev.y)
        if key is None or key in self.rig.installed:
            return
        self.drag = key
        self.ghost = self.cv.create_rectangle(
            ev.x - 60, ev.y - 12, ev.x + 60, ev.y + 12,
            fill="#ffe9a8", outline="#cc9900")
        self.ghost_t = self.cv.create_text(
            ev.x, ev.y, text=T(PART_BY_KEY[key][2], PART_BY_KEY[key][3]),
            font=("TkDefaultFont", 8))

    def on_move(self, ev):
        if self.drag is None:
            return
        self.cv.coords(self.ghost, ev.x - 60, ev.y - 12, ev.x + 60, ev.y + 12)
        self.cv.coords(self.ghost_t, ev.x, ev.y)

    def on_release(self, ev):
        if self.drag is None:
            return
        key = self.drag
        self.drag = None
        slot = self.slot_at(ev.x, ev.y)
        if slot is None:
            self.status.config(text=T("부품을 놓을 자리가 아닙니다.",
                                      "That is not a seat."))
            self.redraw()
            return
        ok, msg = self.rig.install(key, slot)
        self.status.config(text=msg,
                           foreground="#116611" if ok else "#a03000")
        self.redraw()
        self.app.refresh_bench()

    def on_right(self, ev):
        slot = self.slot_at(ev.x, ev.y)
        if slot is None:
            return
        for k in list(self.rig.installed):
            if PART_BY_KEY[k][4] == slot:
                ok, msg = self.rig.remove(k)
                self.status.config(text=msg,
                                   foreground="#116611" if ok else "#a03000")
                break
        self.redraw()
        self.app.refresh_bench()


# --------------------------------------------------------------------------
# Bench tab
# --------------------------------------------------------------------------


class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.rig = app.rig
        self._job = None

        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=4, pady=4)
        mid = ttk.Frame(self)
        mid.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        right = ttk.Frame(self)
        right.pack(side="left", fill="y", padx=4, pady=4)

        self._build_left(left)
        self._build_mid(mid)
        self._build_right(right)
        self.refresh()

    # ------------------------------------------------------------------
    def _slider(self, parent, label, lo, hi, res, attr, row):
        ttk.Label(parent, text=label, font=("TkDefaultFont", 8)).grid(
            row=row, column=0, sticky="w")
        v = tk.DoubleVar(value=getattr(self.rig, attr))

        def cb(_=None, a=attr, var=v):
            setattr(self.rig, a, float(var.get()))
            self.schedule()
        s = tk.Scale(parent, from_=lo, to=hi, resolution=res,
                     orient="horizontal", variable=v, command=cb,
                     length=190, showvalue=False, font=("TkDefaultFont", 7))
        s.grid(row=row + 1, column=0, sticky="ew", pady=(0, 2))
        return v

    def _build_left(self, f):
        box = ttk.LabelFrame(f, text=T("광원 / 조명", "Source / lighting"))
        box.pack(fill="x", pady=3)
        self.btn_laser = ttk.Button(box, text="", command=self.toggle_laser)
        self.btn_laser.pack(fill="x", padx=4, pady=3)
        self.v_int = tk.StringVar(value=self.rig.intensity)
        r = ttk.Frame(box)
        r.pack(fill="x", padx=4)
        ttk.Label(r, text=T("강도", "Intensity"),
                  font=("TkDefaultFont", 8)).pack(side="left")
        for val, lab in (("high", "High"), ("low", "Low")):
            ttk.Radiobutton(r, text=lab, value=val, variable=self.v_int,
                            command=self.set_int).pack(side="left")
        self.v_room = tk.BooleanVar(value=self.rig.room_light)
        ttk.Checkbutton(box, text=T("큐비클 조명 켜기", "Cubicle light on"),
                        variable=self.v_room,
                        command=self.set_room).pack(anchor="w", padx=4, pady=2)

        box2 = ttk.LabelFrame(f, text=T("정렬 조절", "Alignment adjustments"))
        box2.pack(fill="x", pady=3)
        box2.columnconfigure(0, weight=1)
        self._slider(box2, T("레이저 마운트 수평 (X)", "Laser mount lateral (X)"),
                     -10, 10, 0.05, "knob_lx", 0)
        self._slider(box2, T("레이저 마운트 수직 (Y)", "Laser mount height (Y)"),
                     -10, 10, 0.05, "knob_ly", 2)
        self._slider(box2, T("좌측 반사경 기울기", "Left reflector tilt"),
                     -10, 10, 0.05, "knob_tL", 4)
        self._slider(box2, T("우측 반사경 기울기", "Right reflector tilt"),
                     -10, 10, 0.05, "knob_tR", 6)
        self._slider(box2, T("스크린 볼 조인트 (기울기)", "Screen ball joint (tilt)"),
                     -15, 15, 0.1, "knob_tilt", 8)

        box3 = ttk.LabelFrame(f, text=T("레이저 빔", "Laser beam"))
        box3.pack(fill="x", pady=3)
        box3.columnconfigure(0, weight=1)
        self._slider(box3, T("렌즈캡 회전 (초점)", "Lens cap (focus)"),
                     -1.0, 1.0, 0.01, "knob_focus", 0)
        self._slider(box3, T("레이저 몸통 회전 (빔 타원 방향)",
                             "Laser body rotation (beam ellipse)"),
                     1.0, 6.0, 0.05, "spot_h", 2)

        box4 = ttk.LabelFrame(f, text=T("스크린 위치", "Screen position"))
        box4.pack(fill="x", pady=3)
        self.v_pos = tk.StringVar(value=self.rig.screen_pos)
        ttk.Radiobutton(box4, text=T("Fig.2 위치 (반사경 경유)",
                                     "Fig. 2 position (via reflectors)"),
                        value="far", variable=self.v_pos,
                        command=self.set_pos).pack(anchor="w", padx=4)
        ttk.Radiobutton(box4, text=T("Fig.6 대체 위치 (직접)",
                                     "Fig. 6 alternate position (direct)"),
                        value="near", variable=self.v_pos,
                        command=self.set_pos).pack(anchor="w", padx=4)

    def _build_mid(self, f):
        bar = ttk.Frame(f)
        bar.pack(fill="x")
        self.v_mode = tk.StringVar(value="mark")
        for val, ko, en in (("mark", "연필 마킹", "Pencil mark"),
                            ("sticker", "검정 스티커", "Black sticker"),
                            ("pan", "화면 이동", "Pan")):
            ttk.Radiobutton(bar, text=T(ko, en), value=val,
                            variable=self.v_mode,
                            command=self.set_mode).pack(side="left")
        ttk.Label(bar, text=T("  확대", "  Zoom")).pack(side="left")
        self.v_zoom = tk.DoubleVar(value=1.0)
        tk.Scale(bar, from_=1.0, to=8.0, resolution=0.25, orient="horizontal",
                 variable=self.v_zoom, command=self.set_zoom, length=130,
                 showvalue=True, font=("TkDefaultFont", 7)).pack(side="left")
        ttk.Button(bar, text=T("중앙", "Centre"),
                   command=self.centre).pack(side="left", padx=3)

        self.cv = PatternCanvas(f, self.rig, self.set_status,
                                width=400, height=600)
        self.cv.pack(fill="both", expand=True, pady=3)

        sb = ttk.Frame(f)
        sb.pack(fill="x")
        ttk.Label(sb, text=T("시트", "Sheet")).pack(side="left")
        self.cb_sheet = ttk.Combobox(sb, width=8, state="readonly")
        self.cb_sheet.pack(side="left", padx=3)
        self.cb_sheet.bind("<<ComboboxSelected>>", self.sel_sheet)
        ttk.Button(sb, text=T("새 시트", "New sheet"),
                   command=self.new_sheet).pack(side="left", padx=3)
        ttk.Button(sb, text=T("마지막 마크 삭제", "Undo mark"),
                   command=self.undo_mark).pack(side="left", padx=3)
        self.lbl_status = ttk.Label(f, text="", foreground="#0055aa")
        self.lbl_status.pack(fill="x")

    def _build_right(self, f):
        b1 = ttk.LabelFrame(f, text=T("시료 확대 관찰 [19]",
                                      "Sample under flashlight [19]"))
        b1.pack(fill="x", pady=3)
        self.mag = tk.Canvas(b1, width=260, height=210, bg="#101010",
                             highlightthickness=0)
        self.mag.pack(padx=4, pady=4)

        b2 = ttk.LabelFrame(f, text=T("정렬 확인 (평면 거울 [8])",
                                      "Alignment check (plane mirror [8])"))
        b2.pack(fill="x", pady=3)
        self.retro = tk.Canvas(b2, width=170, height=170, bg="#101010",
                               highlightthickness=0)
        self.retro.pack(padx=4, pady=4)
        self.lbl_retro = ttk.Label(b2, text="", font=("TkDefaultFont", 8))
        self.lbl_retro.pack()

        b3 = ttk.LabelFrame(f, text=T("디지털 캘리퍼 [14]",
                                      "Digital caliper [14]"))
        b3.pack(fill="x", pady=3)
        r = ttk.Frame(b3)
        r.pack(padx=4, pady=2)
        ttk.Label(r, text=T("마크", "Mark")).pack(side="left")
        self.sp_i = tk.Spinbox(r, from_=1, to=999, width=4)
        self.sp_i.pack(side="left", padx=2)
        ttk.Label(r, text="-").pack(side="left")
        self.sp_j = tk.Spinbox(r, from_=1, to=999, width=4)
        self.sp_j.pack(side="left", padx=2)
        ttk.Button(r, text=T("측정", "Read"),
                   command=self.do_caliper).pack(side="left", padx=4)
        self.lbl_cal = tk.Label(b3, text="----.-- mm", bg="#101a10",
                                fg="#66ff99", font=("Courier", 16, "bold"),
                                width=14)
        self.lbl_cal.pack(padx=4, pady=3)

        b4 = ttk.LabelFrame(f, text=T("줄자 [16]", "Measuring tape [16]"))
        b4.pack(fill="x", pady=3)
        names = {"sample": T("시료", "sample"),
                 "refL": T("좌측 반사경", "left reflector"),
                 "refR": T("우측 반사경", "right reflector"),
                 "screen_far": T("스크린(Fig.2)", "screen (Fig.2)"),
                 "screen_near": T("스크린(Fig.6)", "screen (Fig.6)")}
        self._tape_names = names
        r = ttk.Frame(b4)
        r.pack(padx=4, pady=2)
        self.cb_p1 = ttk.Combobox(r, width=13, state="readonly",
                                  values=[names[k] for k in E1Rig.TAPE_POINTS])
        self.cb_p1.current(0)
        self.cb_p1.pack(side="left")
        self.cb_p2 = ttk.Combobox(r, width=13, state="readonly",
                                  values=[names[k] for k in E1Rig.TAPE_POINTS])
        self.cb_p2.current(1)
        self.cb_p2.pack(side="left", padx=2)
        ttk.Button(b4, text=T("측정", "Read"),
                   command=self.do_tape).pack(pady=2)
        self.lbl_tape = tk.Label(b4, text="---- mm", bg="#101a10",
                                 fg="#66ff99", font=("Courier", 14, "bold"),
                                 width=16)
        self.lbl_tape.pack(padx=4, pady=3)

        b5 = ttk.LabelFrame(f, text=T("측정 기록", "Reading log"))
        b5.pack(fill="both", expand=True, pady=3)
        self.txt = tk.Text(b5, width=34, height=10, font=("Courier", 8))
        self.txt.pack(fill="both", expand=True, padx=4, pady=4)

    # ------------------------------------------------------------------
    def set_status(self, s):
        self.lbl_status.config(text=s)

    def schedule(self):
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(140, self._do_redraw)

    def _do_redraw(self):
        self._job = None
        self.cv.redraw()
        self.draw_mag()
        self.draw_retro()

    def refresh(self):
        ok, missing = self.rig.bench_ready()
        self.btn_laser.config(
            text=T("레이저 끄기", "Laser OFF") if self.rig.laser_on
            else T("레이저 켜기", "Laser ON"))
        self.cb_sheet["values"] = [s.label for s in self.rig.sheets]
        if self.rig.sheets:
            self.cb_sheet.current(self.rig.cur_sheet)
        self.schedule()

    # ---- control callbacks
    def toggle_laser(self):
        if not self.rig.laser_on:
            if "goggles" not in self.rig.installed:
                messagebox.showwarning(
                    T("안전", "Safety"),
                    T("레이저 보안경 [18]을 먼저 착용하십시오.",
                      "Put on the laser safety goggles [18] first."))
                return
            if "psu" not in self.rig.installed or "laser" not in self.rig.installed:
                messagebox.showwarning(T("연결", "Connection"),
                                       T("레이저와 전원공급장치가 필요합니다.",
                                         "Laser and power supply are required."))
                return
        self.rig.laser_on = not self.rig.laser_on
        self.refresh()

    def set_int(self):
        self.rig.intensity = self.v_int.get()
        self.schedule()

    def set_room(self):
        self.rig.room_light = bool(self.v_room.get())
        self.schedule()

    def set_pos(self):
        self.rig.screen_pos = self.v_pos.get()
        self.schedule()

    def set_mode(self):
        self.cv.mode = self.v_mode.get()

    def set_zoom(self, _=None):
        self.cv.zoom = float(self.v_zoom.get())
        self.schedule()

    def centre(self):
        self.cv.vx = 0.0
        self.cv.vy = 0.0
        self.schedule()

    def new_sheet(self):
        if "sheet" not in self.rig.installed:
            self.set_status(T("스크린에 시트를 먼저 고정하십시오.",
                              "Clip a sheet on the screen first."))
            return
        self.rig.new_sheet()
        self.refresh()

    def sel_sheet(self, _=None):
        self.rig.cur_sheet = self.cb_sheet.current()
        self.schedule()

    def undo_mark(self):
        sh = self.rig.sheet()
        if sh and sh.marks:
            sh.marks.pop()
            self.schedule()

    # ---- instruments
    def logline(self, s):
        self.txt.insert("end", s + "\n")
        self.txt.see("end")

    def do_caliper(self):
        try:
            i = int(self.sp_i.get())
            j = int(self.sp_j.get())
        except ValueError:
            return
        v, msg = self.rig.caliper(i, j)
        if v is None:
            self.lbl_cal.config(text="-- Err --")
            self.set_status(msg)
            return
        self.lbl_cal.config(text="%8.2f mm" % v)
        sh = self.rig.sheet()
        self.logline("%-5s #%d-#%d : %8.2f mm" % (sh.label, i, j, v))

    def do_tape(self):
        k1 = E1Rig.TAPE_POINTS[self.cb_p1.current()]
        k2 = E1Rig.TAPE_POINTS[self.cb_p2.current()]
        v, msg = self.rig.tape(k1, k2)
        if v is None:
            self.lbl_tape.config(text="-- Err --")
            self.set_status(msg)
            return
        self.lbl_tape.config(text="%8d mm" % v)
        self.logline("tape %s-%s : %6d mm" %
                     (self._tape_names[k1][:6], self._tape_names[k2][:6], v))

    # ---- auxiliary views
    def draw_mag(self):
        c = self.mag
        c.delete("all")
        rig = self.rig
        if rig.sample is None:
            c.create_text(130, 105, text=T("시료 없음", "no sample"),
                          fill="#888888")
            return
        p = rig.p
        S = 34.0                       # px per mm
        cx, cy = 130, 105
        if rig.sample == "I":
            pitch, alpha, halfw = p.P, p.alpha1, 0.5 * 2 * p.R * 1.15
            col = "#c8c8c8"
        else:
            pitch, alpha, halfw = p.d2, p.alpha2, 1.6
            col = "#7fb0ff"
        n = int(120 / (pitch * S)) + 2
        for k in range(-n, n + 1):
            y0 = cy + k * pitch * S
            dx = halfw * S * 1.6
            dy = dx * math.tan(alpha)
            c.create_line(cx - dx, y0 + dy, cx + dx, y0 - dy, fill=col)
            c.create_line(cx - dx, y0 - dy, cx + dx, y0 + dy, fill="#8b8b8b")
        if rig.laser_on:
            hh = rig.spot_h * S / 2.0
            ww = 1.1 * S
            c.create_oval(cx - ww, cy - hh, cx + ww, cy + hh,
                          outline="#ff4030", width=2)
            c.create_oval(cx - ww * 0.9, cy - hh * 0.9, cx + ww * 0.9,
                          cy + hh * 0.9, outline="#ff8070")
        c.create_text(130, 200, text=T("(붉은 타원 = 조명 영역)",
                                       "(red ellipse = illuminated area)"),
                      fill="#777777", font=("TkDefaultFont", 7))

    def draw_retro(self):
        c = self.retro
        c.delete("all")
        for r in (20, 40, 60, 80):
            c.create_oval(85 - r, 85 - r, 85 + r, 85 + r, outline="#334433")
        c.create_line(85, 5, 85, 165, fill="#334433")
        c.create_line(5, 85, 165, 85, fill="#334433")
        rig = self.rig
        if "mirror" not in rig.installed or not rig.laser_on:
            self.lbl_retro.config(
                text=T("스크린에 평면 거울을 부착하고 레이저를 켜십시오.",
                       "Clip the plane mirror on and switch the laser on."))
            return
        rx, ry = rig.retro_offset()
        px = 85 + 80 * math.tanh(rx / 40.0)
        py = 85 + 80 * math.tanh(ry / 40.0)
        c.create_oval(px - 4, py - 4, px + 4, py + 4, fill="#ff3020",
                      outline="")
        self.lbl_retro.config(
            text=T("빔이 레이저로 되돌아오도록 맞추십시오.",
                   "Adjust until the beam retraces to the laser."))


# --------------------------------------------------------------------------
# Application
# --------------------------------------------------------------------------


class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.seed = seed if seed is not None else random.randrange(1, 10 ** 6)
        self.phys = E1Physics(self.seed)
        self.rig = E1Rig(self.phys)
        self.title("IPhO 2015 E-I")
        self.geometry("1360x760")
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()
        self.title(T("IPhO 2015 E-I  나선 구조에 의한 회절  |  HaslaLab",
                     "IPhO 2015 E-I  Diffraction due to Helical Structure"
                     "  |  HaslaLab"))
        m = tk.Menu(self)
        fm = tk.Menu(m, tearoff=0)
        fm.add_command(label=T("새 세션 (매개변수 재추첨)",
                               "New session (re-randomise)"),
                       command=self.new_session)
        fm.add_separator()
        fm.add_command(label=T("종료", "Quit"), command=self.destroy)
        m.add_cascade(label=T("파일", "File"), menu=fm)
        lm = tk.Menu(m, tearoff=0)
        lm.add_command(label="한국어", command=lambda: self.set_lang("ko"))
        lm.add_command(label="English", command=lambda: self.set_lang("en"))
        m.add_cascade(label=T("언어", "Language"), menu=lm)
        self.config(menu=m)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_a = AssemblyTab(nb, self)
        self.tab_b = BenchTab(nb, self)
        nb.add(self.tab_a, text=T(" 1. 조립 ", " 1. Assembly "))
        nb.add(self.tab_b, text=T(" 2. 실험대 ", " 2. Bench "))
        self.nb = nb

    def refresh_bench(self):
        if hasattr(self, "tab_b"):
            self.tab_b.refresh()

    def set_lang(self, lang):
        global LANG
        LANG = lang
        self._build()

    def new_session(self):
        self.seed = random.randrange(1, 10 ** 6)
        self.phys = E1Physics(self.seed)
        self.rig = E1Rig(self.phys)
        self._build()


def main():
    import sys
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
        elif a.startswith("--lang="):
            globals()["LANG"] = a.split("=", 1)[1]
    App(seed).mainloop()


if __name__ == "__main__":
    main()
