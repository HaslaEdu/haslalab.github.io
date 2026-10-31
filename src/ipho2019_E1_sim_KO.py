#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPhO 2019 (Israel) - Experimental Problem Q1
"Optical Measurements"  -  Virtual laboratory

Single file, standard library only (tkinter).

  * the cubicle is drawn at a FIXED scale of 16 px per cm and is scrolled,
    never zoomed: the 20.00 cm disk is 320 px across and its printed
    protractor (2 deg graduation, labelled every 10 deg) is read directly on
    the screen.  There is no magnifier and no zoom - the lengths are measured
    with the instruments that the exam provides: the 60 cm ruler, the 30 cm
    plastic ruler (item 8) and the 3 m measuring tape (item 7).
  * every item is drawn from the photographs of the official problem sheet
    (equipment figures of Q1-1, Q1-2 and Q1-3)
  * a general ray tracer: the nearest object along the ray is found among the
    disk, the grating, the prism, the black screen board, the opaque holder
    12B and the walls, so anything that stands in the beam really blocks it
  * a laser beam is invisible in air.  With the lights ON only the main
    transmitted beam and the N = 3 exit are barely visible, and the N = 4
    exit appears only at large incidence; the hall has to be darkened to
    follow the whole family of exits
  * the adhesive tape (item 6) has to be taken out of the tray before the
    disk board or the ruler can be taped down; an untaped item shivers

  The simulator NEVER computes a result.  Only printed graduations are shown.

Run:  python IPhO2019_Q1_Sim.py
"""

LANG = "KO"

import math
import random
import tkinter as tk
from tkinter import ttk

# ==========================================================================
S = {
    "title": ("IPhO 2019  Q1 - 광학 측정  가상 실험실",
              "IPhO 2019  Q1 - Optical Measurements  Virtual Lab"),
    "tab_lab": ("실험 부스", "Cubicle"),
    "tab_info": ("장비 목록", "Equipment"),
    "map": ("부스 전체 (클릭하면 그쪽으로 이동)",
            "cubicle overview - click to go there"),
    "level": ("레이저 높이", "laser level"),
    "low": ("3A 낮음 (A부: 원판)", "3A low (part A: disk)"),
    "high": ("3B 높음 (B·C부: 12B)", "3B high (parts B,C: 12B)"),
    "laser_on": ("레이저 3C ON", "laser 3C ON"),
    "dark": ("암실 (소등)", "darken the hall"),
    "tscale": ("시간", "clock"),
    "lit": ("실내등 ON — 소등까지 %s", "lights on - blackout in %s"),
    "blk": ("암실 — 점등까지 %s", "hall dark - lights back in %s"),
    "parch": ("양피지(11)를 원판에 대기", "parchment paper (11) on the disk"),
    "front": ("검은 스크린 - 정면도", "black screen - front view"),
    "front_hint": ("줄자의 노란 끝점을 끌어 눈금을 무늬에 대세요",
                   "drag the yellow ends of the tape onto the pattern"),
    "tray": ("장비", "equipment"),
    "put": ("배치", "place"),
    "take": ("회수", "remove"),
    "hint": ("· 장비를 끌어서 옮기고, 장비 위에서 휠을 돌리면 회전합니다\n"
             "· 바닥에서 휠 = 위아래 스크롤,  가운데/오른쪽 버튼 = 화면 이동\n"
             "· 12B 검은 원통 위에서 휠 = 격자·프리즘만 회전(회절각 조절),\n"
             "  나무판 12A 위에서 휠 = 받침 전체 회전\n"
             "· 자 안의 슬라이더를 끌면 레이저가 자를 따라 움직입니다\n"
             "· 슬라이더 위에서 휠 = 4C 미세 회전,  레이저 머리 클릭 = 3C\n"
             "· 접착 테이프(6)를 클릭해 손에 들고, 든 상태에서 장비의 아무 곳이나\n"
             "  클릭하면 그 자리에 테이프가 붙습니다 (다시 클릭하면 떼기,\n"
             "  빈 바닥 클릭 = 내려놓기).  1개 붙이면 그 점을 축으로만 미세하게\n"
             "  흔들리고, 2개 붙이면 완전히 고정됩니다.  테이프가 붙은 장비는\n"
             "  움직일 수 없고, 테이프를 클릭하면 뜯어집니다.  자에 붙인 테이프에\n"
             "  레이저의 빨간 받침이 닿으면 더 이상 가지 못합니다\n"
             "· 장비를 클릭해 선택(노란 점선)한 뒤 휠을 돌리면 회전합니다.\n"
             "  휠 = 2도,  Shift+휠 = 0.25도.  빈 바닥을 클릭하면 선택 해제되고\n"
             "  그때 휠은 화면 스크롤입니다\n"
             "· 장비를 부스 밖으로 끌어내거나 오른쪽 버튼으로 회수합니다\n"
             "· 공기 중 광선은 보이지 않습니다 — 스크린의 점과 원판 속 경로만",
             "· drag an item to move it, turn the wheel over it to rotate\n"
             "· wheel over the floor = scroll,  middle/right button = pan\n"
             "· wheel over the black cylinder 12B turns the grating / prism\n"
             "  only (this sets the diffraction angle); wheel over the wooden\n"
             "  piece 12A turns the whole mount\n"
             "· drag the slider inside the ruler to move the laser\n"
             "· wheel over the slider = bar 4C,  click the head = switch 3C\n"
             "· click the adhesive tape (6) to pick it up; with it in your hand\n"
             "  click anywhere on an item to stick a strip there (click it\n"
             "  again to peel it off, click the floor to put the roll down).\n"
             "  One strip pins that point, two fix the item completely; a taped\n"
             "  item cannot be moved, and the red base of the laser stops\n"
             "  against a strip stuck on the ruler\n"
             "· click an item to select it (yellow dashes), then the wheel\n"
             "  turns it: 2 deg per notch, 0.25 deg with Shift.  Click the\n"
             "  bare floor to deselect - then the wheel scrolls the view\n"
             "· drag an item out of the cubicle, or use the buttons, to remove\n"
             "· the beam is invisible in air - only spots and the path\n"
             "  inside the glass disk can be seen"),
    "nm": {"ruler": ("1+2+3  자·슬라이더·레이저", "1+2+3  ruler, slider, laser"),
           "tape6": ("6  접착 테이프", "6  adhesive tape"),
           "tape": ("7  줄자 3 m", "7  measuring tape 3 m"),
           "ruler8": ("8  자 30 cm", "8  ruler 30 cm"),
           "disk": ("10  원판 20.00 cm", "10  disk 20.00 cm"),
           "holder": ("12  12A + 12B", "12  12A + 12B"),
           "screen": ("검은 스크린판", "black screen board")},
    "items": (
        ["1. 자 60 cm", "2. 자 위를 움직이는 슬라이더",
         "3. 슬라이더에 장착된 다이오드 레이저 (3A 낮음 / 3B 높음, 3C 스위치)",
         "4. 4A·4B 나사, 4C 방향 조절 막대 (슬라이더 위에서 휠)",
         "5. 스크린 — 부스의 벽 및 검은 스크린판",
         "6. 접착 테이프 — 꺼낸 뒤 원판 네 귀퉁이·자 양끝을 클릭",
         "7. 유연한 줄자 3 m", "8. 자 30 cm", "9. 탁상 램프",
         "10. 지름 20.00 cm 투명 원판 (각도기 위에 고정, 나무 받침)",
         "11. 양피지 — 반투명 스크린", "12. 나무판 12A + 회전 홀더 12B",
         "12C. 회절격자   12D. 삼각 프리즘"],
        ["1. Ruler, 60 cm", "2. Slider moving along the ruler",
         "3. Diode laser on the slider (3A low / 3B high, switch 3C)",
         "4. Screws 4A, 4B and direction bar 4C (wheel over the slider)",
         "5. Screen - the cubicle walls and the black screen board",
         "6. Adhesive tape - take it out, then click the corners",
         "7. Flexible measuring tape, 3 m", "8. Ruler, 30 cm",
         "9. Table lamp",
         "10. Transparent disk, 20.00 cm dia, on a printed protractor",
         "11. Parchment paper - translucent screen",
         "12. Wooden piece 12A + rotating holder 12B",
         "12C. diffraction grating   12D. triangular prism"]),
}


def _(k):
    v = S[k]
    return v[0] if LANG == "KO" else v[1]


def nm(k):
    v = S["nm"][k]
    return v[0] if LANG == "KO" else v[1]


# ==========================================================================
#  palette sampled from the photographs of the problem sheet
# ==========================================================================
C_MAT = "#5f8b76"          # green table mat
C_MAT2 = "#547e6a"
C_MATD = "#16241d"         # the same mat with the lights off
C_MATD2 = "#121e18"
C_WALL = "#e9e2d2"
C_WALL_D = "#2a2a26"
C_WALL_E = "#c9c0ac"

C_ALU = "#d3d7da"          # ruler body
C_ALU_E = "#9aa1a6"
C_ALU_D = "#b7bcc0"        # laser bracket
C_RED = "#d8322a"          # red slider clamps
C_RED_D = "#8d1c16"
C_BATT = "#2a2c30"
C_BRASS = "#b8912e"
C_ROD4C = "#b8a14a"
C_WHITE = "#eeeeec"        # printed protractor board / 12A
C_WOOD = "#c9a878"
C_WOOD_E = "#958774"
C_PLY = "#a8916d"
C_DISK = "#e9eff1"
C_DISK_D = "#8fa9b0"
C_TICK = "#232323"
C_HOLD = "#1b1b1d"
C_HOLD2 = "#2c2e31"
C_GFRAME = "#23282a"
C_GGLASS = "#a8c4b4"
C_PRISM = "#dfeaee"
C_PARCH = "#ddd6c4"
C_ROLL = "#e6dfcc"
C_ROLL_C = "#c9a878"
C_ROLL_I = "#cfd8e0"
C_TAPE = "#f2f0e6"
C_TCASE = "#e8437f"
C_TBTN = "#f0d02a"
C_SCREEN = "#131313"
BEAM = "#ff5a3c"
BEAM2 = "#e01808"

SC = 12.0                  # px per cm  (fixed - there is no zoom)
ROOM_W = 272.0
ROOM_D = 208.0
SCREEN_W = 120.0
# a graduation closer than 2 px on the screen is not worth drawing
TSTEP = 1 if SC * 0.1 >= 2.0 else 5

# the hall is darkened on a schedule, as in the real cubicle (shortened
# here because this is an on-line session)
DARK_FROM = 180.0        # s, first blackout
DARK_LEN = 420.0         # s, how long it lasts
DARK_EVERY = 900.0       # s, and it comes back every

TRAY = ["ruler", "disk", "holder", "screen", "tape6", "tape", "ruler8"]


# ==========================================================================
def norm(v):
    m = math.hypot(v[0], v[1]) or 1.0
    return (v[0] / m, v[1] / m)


def dirv(a_deg):
    a = math.radians(a_deg)
    return (math.cos(a), -math.sin(a))


def refract(d, nvec, n1, n2):
    r = n1 / n2
    ci = -(d[0] * nvec[0] + d[1] * nvec[1])
    s2 = r * r * (1.0 - ci * ci)
    if s2 > 1.0:
        return None
    ct = math.sqrt(1.0 - s2)
    return norm((r * d[0] + (r * ci - ct) * nvec[0],
                 r * d[1] + (r * ci - ct) * nvec[1]))


def fresnel_s(ci, n1, n2):
    r = n1 / n2
    s2 = r * r * (1.0 - ci * ci)
    if s2 >= 1.0:
        return 1.0
    ct = math.sqrt(1.0 - s2)
    rs = (n1 * ci - n2 * ct) / (n1 * ci + n2 * ct)
    return rs * rs


def seg_hit(p, d, a, b):
    ex, ey = b[0] - a[0], b[1] - a[1]
    den = d[0] * ey - d[1] * ex
    if abs(den) < 1e-12:
        return None
    t = ((a[0] - p[0]) * ey - (a[1] - p[1]) * ex) / den
    u = ((a[0] - p[0]) * d[1] - (a[1] - p[1]) * d[0]) / den
    if t > 1e-6 and -1e-9 <= u <= 1 + 1e-9:
        return t
    return None


def circ_hit(p, d, c, R):
    ox, oy = p[0] - c[0], p[1] - c[1]
    b = ox * d[0] + oy * d[1]
    cc = ox * ox + oy * oy - R * R
    disc = b * b - cc
    if disc < 0:
        return []
    sd = math.sqrt(disc)
    return [t for t in (-b - sd, -b + sd) if t > 1e-6]


def grating_frame(d, a, b):
    gv = norm((b[0] - a[0], b[1] - a[1]))
    nv = (-gv[1], gv[0])
    if nv[0] * d[0] + nv[1] * d[1] < 0:
        nv = (-nv[0], -nv[1])
    sa = d[0] * gv[0] + d[1] * gv[1]
    if sa < 0:
        gv = (-gv[0], -gv[1])
        sa = -sa
    return nv, gv, sa


_MIX = {}


def mix(c0, c1, f):
    key = (c0, c1, int(max(0.0, min(1.0, f)) * 64))
    out = _MIX.get(key)
    if out is None:
        g = key[2] / 64.0
        a = [int(c0[i:i + 2], 16) for i in (1, 3, 5)]
        b = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
        out = "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * g)
                                      for i in range(3))
        _MIX[key] = out
    return out


def vis(I, dark):
    """how bright a spot / a scattered path looks.  0 = not visible."""
    if dark:
        if I < 1.0e-4:
            return 0.0
        return min(1.0, 1.90 * I ** 0.55)
    if I < 0.020:
        return 0.0                     # lost in the light of the hall
    return min(1.0, I ** 0.42 * 0.80)


# ==========================================================================
class Lab:
    """The optical bench.  Poses are (x, y, angle) in cm / degrees."""

    def __init__(self, seed=None):
        rng = random.Random(seed)
        self.rng = rng
        self.n_disk = rng.uniform(1.505, 1.524)
        self.n_prism = rng.uniform(1.6395, 1.6455)
        self.lam_over_d = rng.uniform(0.3955, 0.4045)
        self.grating_id = "#%d" % rng.randint(100, 999)
        e1 = rng.uniform(-0.35, 0.35)
        e2 = rng.uniform(-0.35, 0.35)
        self.prism_eps = [e1, e2, -(e1 + e2)]
        self.prot_zero = rng.uniform(-0.4, 0.4)

        self.obj = {
            "ruler": dict(on=False, pos=[136.0, 170.0], ang=0.0, tapes=[]),
            "disk": dict(on=False, pos=[136.0, 96.0], ang=270.0, tapes=[]),
            "holder": dict(on=False, pos=[150.0, 110.0], ang=0.0, tapes=[]),
            "screen": dict(on=False, pos=[136.0, 30.0], ang=0.0, tapes=[]),
            "ruler8": dict(on=False, pos=[60.0, 150.0], ang=0.0, tapes=[]),
            "tape6": dict(on=False, pos=[40.0, 60.0], ang=0.0, tapes=[]),
        }
        self.order = ["screen", "holder", "disk", "ruler8", "ruler",
                      "tape6"]
        self.tape_on = False
        self.tape_held = False
        self.tape_a = [50.0, 192.0]
        self.tape_b = [170.0, 192.0]
        self.ftape_a = [-40.0, 6.0]
        self.ftape_b = [40.0, 6.0]

        self.slider = 0.0
        self.laser_fine = 0.0
        self.hold_item = "grating"
        self.hold_rot = 0.0      # rotation of the upper part 12B
        self.sel = None          # the item the wheel will turn
        self.level = "low"
        self.laser_on = False
        self.parchment = False
        self.dark = False
        self.clock = 0.0             # s, session time

        self.t = 0.0
        self._ph = [rng.uniform(0, 6.3) for _ in range(9)]
        self._pc = {}
        self.segs = []
        self.spots = []
        self.shots = []
        self.hits = []

    # ------------------------------------------------------------------ #
    def raise_(self, key):
        if key in self.order:
            self.order.remove(key)
            self.order.append(key)

    def in_ruler8(self, x, y):
        """is the point covered by the transparent 30 cm ruler ?"""
        o = self.obj["ruler8"]
        if not o["on"]:
            return False
        if self.order.index("ruler8") < self.order.index("disk"):
            return False              # the ruler lies under the disk
        cx, cy, ang = self.pose("ruler8")
        u, v = dirv(ang), dirv(ang + 90.0)
        a = (x - cx) * u[0] + (y - cy) * u[1]
        b = (x - cx) * v[0] + (y - cy) * v[1]
        return abs(a) < 15.6 and abs(b) < 1.9

    LOCAL = {"ruler": (30.6, 3.0), "disk": (15.4, 15.4),
             "holder": (12.6, 8.6), "screen": (SCREEN_W / 2 + 1, 3.0),
             "ruler8": (15.6, 1.9)}
    # true outlines used for the "nothing may overlap" rule
    COLL = {"ruler": (30.4, 2.6), "disk": (15.2, 15.2),
            "holder": (12.5, 8.5), "screen": (SCREEN_W / 2, 0.9)}

    def local(self, key, x, y):
        cx, cy, ang = self.pose(key)
        u, v = dirv(ang), dirv(ang + 90.0)
        return ((x - cx) * u[0] + (y - cy) * u[1],
                (x - cx) * v[0] + (y - cy) * v[1])

    def inside(self, key, x, y):
        h = self.LOCAL.get(key)
        if h is None or not self.obj[key]["on"]:
            return False
        a, b = self.local(key, x, y)
        return abs(a) < h[0] and abs(b) < h[1]

    def wobbly(self):
        for k, o in self.obj.items():
            if o["on"] and k in self.LOCAL and len(o["tapes"]) < 2:
                return True
        return False

    def pose(self, key):
        c = self._pc.get(key)
        if c is not None:
            return c
        o = self.obj[key]
        x, y, a = o["pos"][0], o["pos"][1], o["ang"]
        n = len(o["tapes"])
        if o["on"] and n < 2 and key in self.LOCAL:
            t = self.t
            p = self._ph
            da = (0.26 * math.sin(0.23 * t + p[4]) +
                  0.09 * math.sin(0.71 * t + p[5]))
            if n == 0:
                x += (0.085 * math.sin(0.31 * t + p[0]) +
                      0.028 * math.sin(0.83 * t + p[1]))
                y += (0.080 * math.sin(0.27 * t + p[2]) +
                      0.026 * math.sin(0.97 * t + p[3]))
                a += da
            else:
                # one piece of tape pins that point: the item can only pivot
                ta, tb = o["tapes"][0]
                u, v = dirv(a), dirv(a + 90.0)
                fx = x + u[0] * ta + v[0] * tb
                fy = y + u[1] * ta + v[1] * tb
                a += 0.45 * da
                u, v = dirv(a), dirv(a + 90.0)
                x = fx - (u[0] * ta + v[0] * tb)
                y = fy - (u[1] * ta + v[1] * tb)
        self._pc[key] = (x, y, a)
        return x, y, a

    def light_phase(self):
        """(dark?, seconds until it changes)"""
        if self.clock < DARK_FROM:
            return False, DARK_FROM - self.clock
        p = (self.clock - DARK_FROM) % DARK_EVERY
        if p < DARK_LEN:
            return True, DARK_LEN - p
        return False, DARK_EVERY - p

    def slider_limits(self):
        """a piece of tape blocks the slider from moving past it"""
        lo, hi = -27.0, 27.0
        # the red clamps are 4.9 cm wide, the strip 1.6 cm
        for (ta, _tb) in self.obj["ruler"]["tapes"]:
            if ta < self.slider:
                lo = max(lo, ta + 6.5)
            else:
                hi = min(hi, ta - 6.5)
        return lo, hi

    # ------------------------------------------------------------------ #
    BARREL = 2.9                 # cm, pivot -> aperture of the holder

    def pivot(self):
        """the optical axis where it crosses the ruler (the slider mark)"""
        x, y, a = self.pose("ruler")
        u = dirv(a)
        return (x + u[0] * self.slider, y + u[1] * self.slider)

    def laser(self):
        """the aperture: the tip of the brass barrel"""
        p = self.pivot()
        d = self.beam_dir()
        return (p[0] + d[0] * self.BARREL, p[1] + d[1] * self.BARREL)

    def beam_dir(self):
        _x, _y, a = self.pose("ruler")
        return dirv(a + 90.0 + self.laser_fine)

    def disk_center(self):
        x, y, _a = self.pose("disk")
        return (x, y)

    def protractor(self, q):
        x, y, a = self.pose("disk")
        ang = math.degrees(math.atan2(-(q[1] - y), q[0] - x))
        return (ang - a - self.prot_zero) % 360.0

    def prism_poly(self):
        cx, cy, rot = self.pose("holder")
        rot += self.hold_rot
        R = 2.90
        A, _B, Cc = [60.0 + 2.0 * e for e in self.prism_eps]
        th = [0.0, 2.0 * Cc, 2.0 * Cc + 2.0 * A]
        return [(cx + R * math.cos(math.radians(rot + t)),
                 cy - R * math.sin(math.radians(rot + t))) for t in th]

    def grating_seg(self):
        cx, cy, rot = self.pose("holder")
        u = dirv(rot + self.hold_rot)
        return ((cx - 2.4 * u[0], cy - 2.4 * u[1]),
                (cx + 2.4 * u[0], cy + 2.4 * u[1]))

    def screen_seg(self):
        cx, cy, rot = self.pose("screen")
        u = dirv(rot)
        h = SCREEN_W / 2.0
        return ((cx - h * u[0], cy - h * u[1]),
                (cx + h * u[0], cy + h * u[1]))

    # ------------------------------------------------------------------ #
    #  general ray tracer
    # ------------------------------------------------------------------ #
    def active(self):
        if self.obj["disk"]["on"] and self.level == "low":
            return "disk"
        if self.obj["holder"]["on"] and self.level == "high":
            return self.hold_item
        return None

    def trace(self):
        self._pc.clear()          # never trace with a stale pose
        self.segs = []
        self.spots = []
        self.shots = []
        self.hits = []
        if not self.laser_on or not self.obj["ruler"]["on"]:
            return self.segs, self.spots, self.hits, self.shots
        self._air(self.laser(), self.beam_dir(), 1.0, 0)
        return self.segs, self.spots, self.hits, self.shots

    # ------------------------------------------------------------------ #
    def _air(self, p, d, I, depth):
        """propagate one ray through air until it meets something"""
        if I < 1.0e-6 or depth > 6:
            return
        act = self.active()
        best, kind, extra = 1e9, None, None

        if self.obj["screen"]["on"]:
            a, b = self.screen_seg()
            t = seg_hit(p, d, a, b)
            if t and t < best:
                best, kind, extra = t, "screen", (a, b)
        if act == "disk":
            ts = circ_hit(p, d, self.disk_center(), 10.0)
            if ts and min(ts) < best:
                best, kind, extra = min(ts), "disk", None
        if self.obj["holder"]["on"] and self.level == "low":
            # the black cylinder 12B is opaque for the low beam
            cx, cy, _a = self.pose("holder")
            ts = circ_hit(p, d, (cx, cy), 4.4)
            if ts and min(ts) < best:
                best, kind, extra = min(ts), "block", None
        if act == "grating":
            a, b = self.grating_seg()
            t = seg_hit(p, d, a, b)
            if t and t < best:
                best, kind, extra = t, "grating", None
        if act == "prism":
            pts = self.prism_poly()
            for i in range(3):
                t = seg_hit(p, d, pts[i], pts[(i + 1) % 3])
                if t and t < best:
                    best, kind, extra = t, "prism", None
        for a, b in (((0.0, 0.0), (ROOM_W, 0.0)),
                     ((0.0, 0.0), (0.0, ROOM_D)),
                     ((ROOM_W, 0.0), (ROOM_W, ROOM_D)),
                     ((0.0, ROOM_D), (ROOM_W, ROOM_D))):
            t = seg_hit(p, d, a, b)
            if t and t < best:
                best, kind, extra = t, "wall", None
        if kind is None:
            return
        q = (p[0] + d[0] * best, p[1] + d[1] * best)
        self.segs.append((p[0], p[1], q[0], q[1], I, "air"))

        if kind in ("wall", "screen"):
            if kind == "wall":
                self.spots.append((q[0], q[1], I))
            else:
                # seen edge-on from above: the pattern is only visible in
                # the front view of the board
                a, b = extra
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
                s = (q[0] - a[0]) * u[0] + (q[1] - a[1]) * u[1] - L / 2.0
                self.shots.append((s, I))
        elif kind == "block":
            pass
        elif kind == "disk":
            self._disk(q, d, I, depth)
        elif kind == "grating":
            self._grating(q, d, I, depth)
        elif kind == "prism":
            self._prism(q, d, I, depth)

    # ------------------------------------------------------------------ #
    def _disk(self, q, d, I0, depth):
        C = self.disk_center()
        R = 10.0
        n = self.n_disk
        nv = norm((q[0] - C[0], q[1] - C[1]))
        ci = -(d[0] * nv[0] + d[1] * nv[1])
        Rs = fresnel_s(ci, 1.0, n)
        di = refract(d, nv, 1.0, n)
        self.hits.append(q)
        self._air(q, norm((d[0] + 2 * ci * nv[0], d[1] + 2 * ci * nv[1])),
                  I0 * Rs, depth + 1)
        if di is None:
            return
        I = I0 * (1.0 - Rs)
        cur, cd = q, di
        for _k in range(12):
            tt = circ_hit(cur, cd, C, R)
            if not tt:
                break
            nxt = (cur[0] + cd[0] * max(tt), cur[1] + cd[1] * max(tt))
            self.segs.append((cur[0], cur[1], nxt[0], nxt[1], I, "glass"))
            self.hits.append(nxt)
            nout = norm((nxt[0] - C[0], nxt[1] - C[1]))
            nv2 = (-nout[0], -nout[1])
            ci2 = -(cd[0] * nv2[0] + cd[1] * nv2[1])
            Rs2 = fresnel_s(ci2, n, 1.0)
            do = refract(cd, nv2, n, 1.0)
            if do is not None:
                self._air(nxt, do, I * (1.0 - Rs2), depth + 1)
            cd = norm((cd[0] + 2 * ci2 * nv2[0], cd[1] + 2 * ci2 * nv2[1]))
            cur = nxt
            I *= Rs2
            if I < 1.0e-6:
                break

    # ------------------------------------------------------------------ #
    def _grating(self, q, d, I0, depth):
        a, b = self.grating_seg()
        nv, gv, sa = grating_frame(d, a, b)
        # the light really is seen inside the glass of the grating
        self.segs.append((q[0] - d[0] * 0.42, q[1] - d[1] * 0.42,
                          q[0] + d[0] * 0.06, q[1] + d[1] * 0.06,
                          I0, "glass"))
        for m in range(-6, 7):
            sd = m * self.lam_over_d - sa
            if abs(sd) > 1.0:
                continue
            cdv = math.sqrt(1.0 - sd * sd)
            eff = 0.40 if m == 0 else 0.26 / (1.0 + 0.7 * abs(m))
            o = norm((cdv * nv[0] - sd * gv[0], cdv * nv[1] - sd * gv[1]))
            self._air(q, o, I0 * eff, depth + 1)

    # ------------------------------------------------------------------ #
    def _prism(self, q, d, I0, depth):
        """a single clear pass: in through one face, out through another"""
        pts = self.prism_poly()
        faces = [(pts[i], pts[(i + 1) % 3]) for i in range(3)]
        n = self.n_prism

        def perp(pt, f):
            ax, ay = f[0]
            bx, by = f[1]
            ex, ey = bx - ax, by - ay
            L = math.hypot(ex, ey) or 1.0
            return abs((pt[0] - ax) * ey - (pt[1] - ay) * ex) / L

        def face_normal(f, dvec):
            fv = norm((f[1][0] - f[0][0], f[1][1] - f[0][1]))
            nv = (-fv[1], fv[0])
            if nv[0] * dvec[0] + nv[1] * dvec[1] > 0:
                nv = (-nv[0], -nv[1])
            return nv

        bf = min(faces, key=lambda f: perp(q, f))
        nv = face_normal(bf, d)
        ci = -(d[0] * nv[0] + d[1] * nv[1])
        Rs = fresnel_s(ci, 1.0, n)
        self._air(q, norm((d[0] + 2 * ci * nv[0], d[1] + 2 * ci * nv[1])),
                  I0 * Rs, depth + 1)
        cd = refract(d, nv, 1.0, n)
        if cd is None:
            return
        I = I0 * (1.0 - Rs)
        best, bf2 = 1e9, None
        for f in faces:
            t = seg_hit(q, cd, f[0], f[1])
            if t and t < best:
                best, bf2 = t, f
        if bf2 is None:
            return
        nxt = (q[0] + cd[0] * best, q[1] + cd[1] * best)
        self.segs.append((q[0], q[1], nxt[0], nxt[1], I, "glass"))
        nv2 = face_normal(bf2, cd)
        ci2 = -(cd[0] * nv2[0] + cd[1] * nv2[1])
        Rs2 = fresnel_s(ci2, n, 1.0)
        do = refract(cd, nv2, n, 1.0)
        if do is not None:
            self._air(nxt, do, I * (1.0 - Rs2), depth + 1)


# ==========================================================================
#  drawing
# ==========================================================================
class _Tag(object):
    """canvas proxy that stamps every new item with a tag"""

    __slots__ = ("cv", "tag")

    def __init__(self, cv, tag):
        self.cv = cv
        self.tag = tag

    def __getattr__(self, n):
        f = getattr(self.cv, n)
        if n.startswith("create_"):
            tag = self.tag

            def g(*a, **k):
                k.setdefault("tags", tag)
                return f(*a, **k)
            return g
        return f


class View:
    def __init__(self, lab):
        self.lab = lab

    # ------------------------------------------------------------------ #
    ITEM_FN = ("screen", "tape6", "ruler8", "ruler", "disk", "holder")

    def draw(self, cv, rect):
        cv.delete("all")
        self.draw_room(cv, rect)
        for k in self.lab.order:
            if self.lab.obj[k]["on"]:
                self.draw_item(cv, k, rect)
        if self.lab.tape_on:
            self.draw_tape(_Tag(cv, "mtape"), rect)
        self.draw_beams(cv)

    def sel_mark(self, cv, k, W):
        sel = self.lab.sel
        if sel != k and not (k == "holder" and sel == "holder12b"):
            return
        if sel == "holder12b":
            cx, cy, _a = self.lab.pose("holder")
            r = 4.8 * SC
            cv.create_oval(cx * SC - r, cy * SC - r, cx * SC + r,
                           cy * SC + r, outline="#ffd45e", width=2,
                           dash=(6, 4))
            return
        h = self.lab.LOCAL.get(k)
        if h is None:
            return
        self._poly(cv, [W(-h[0], -h[1]), W(h[0], -h[1]), W(h[0], h[1]),
                        W(-h[0], h[1])], fill="", outline="#ffd45e",
                   width=2, dash=(6, 4))

    def draw_item(self, cv, k, rect):
        t = _Tag(cv, k)
        if k == "screen":
            self.draw_screen(t)
        elif k == "tape6":
            self.draw_roll(t)
        elif k == "ruler8":
            self.draw_ruler8(t, rect)
        elif k == "ruler":
            self.draw_ruler(t, rect)
        elif k == "disk":
            self.draw_disk(t, rect)
        elif k == "holder":
            self.draw_holder(t)

    def draw_room(self, cv, rect):
        lab = self.lab
        dark = lab.dark
        f0 = C_MATD if dark else C_MAT
        f1 = C_MATD2 if dark else C_MAT2
        cv.create_rectangle(0, 0, ROOM_W * SC, ROOM_D * SC, fill=f0,
                            outline="", tags="room")
        i0 = max(0, int(rect[0] / 8.0) - 1)
        i1 = min(40, int(rect[2] / 8.0) + 2)
        for i in range(i0, i1):
            cv.create_line(i * 8.0 * SC, rect[1] * SC, i * 8.0 * SC,
                           rect[3] * SC, fill=f1, tags="room")
        t = 5 * SC
        wc = C_WALL_D if dark else C_WALL
        ec = "#3a3a34" if dark else C_WALL_E
        cv.create_rectangle(-t, -t, ROOM_W * SC + t, 0, fill=wc, outline=ec,
                            tags="room")
        cv.create_rectangle(-t, 0, 0, ROOM_D * SC, fill=wc, outline=ec,
                            tags="room")
        cv.create_rectangle(ROOM_W * SC, 0, ROOM_W * SC + t, ROOM_D * SC,
                            fill=wc, outline=ec, tags="room")

    def draw_beams(self, cv):
        lab = self.lab
        dark = lab.dark
        f0 = C_MATD if dark else C_MAT
        segs, spots, hits, _sh = lab.trace()
        gbase = C_DISK_D if dark else C_DISK
        for (ax, ay, bx, by, I, med) in segs:
            if med == "air":
                continue                      # invisible in air
            v0 = vis(I * 0.60, dark)
            if v0 <= 0.02:
                continue
            n = 12 if lab.obj["ruler8"]["on"] else 1
            ex, ey = (bx - ax) / n, (by - ay) / n
            L = math.hypot(bx - ax, by - ay) or 1.0
            px_, py_ = -(by - ay) / L, (bx - ax) / L
            for i in range(n):
                x0_, y0_ = ax + ex * i, ay + ey * i
                x1_, y1_ = ax + ex * (i + 1), ay + ey * (i + 1)
                under = (n > 1 and
                         lab.in_ruler8(0.5 * (x0_ + x1_), 0.5 * (y0_ + y1_)))
                v = v0 * 0.58 if under else v0
                if v <= 0.02:
                    continue
                sh = 0.16 if under else 0.0
                xa, ya = (x0_ + px_ * sh) * SC, (y0_ + py_ * sh) * SC
                xb, yb = (x1_ + px_ * sh) * SC, (y1_ + py_ * sh) * SC
                for wf, cf in ((3.6, 0.14), (2.1, 0.42)):
                    w = wf * v
                    if w < 1.2:
                        continue
                    cv.create_line(xa, ya, xb, yb,
                                   fill=mix(gbase, BEAM, min(1.0, v * cf)),
                                   width=w, capstyle="round", tags="beam")
                # the core is always drawn, at least one pixel wide
                cv.create_line(xa, ya, xb, yb, fill=mix(gbase, BEAM, v),
                               width=max(1.0, 1.3 * v), capstyle="round",
                               tags="beam")
        for (sx, sy, I) in spots:
            v = vis(I * (0.58 if lab.in_ruler8(sx, sy) else 1.0), dark)
            if v <= 0.02:
                continue
            for k, f in ((7.0, 0.14), (4.0, 0.40), (2.2, 0.80), (1.2, 1.0)):
                r = max(1.0, k * (0.45 + 0.95 * v))
                cv.create_oval(sx * SC - r, sy * SC - r, sx * SC + r,
                               sy * SC + r,
                               fill=mix(f0, BEAM, min(1.0, v * f)),
                               outline="", tags="beam")
        if lab.parchment and lab.obj["disk"]["on"]:
            for q in hits:
                cv.create_oval(q[0] * SC - 5, q[1] * SC - 5, q[0] * SC + 5,
                               q[1] * SC + 5, outline="#c07a5a", width=2,
                               tags="beam")

    # ------------------------------------------------------------------ #
    @staticmethod
    def _poly(cv, pts, **kw):
        return cv.create_polygon([c for p in pts for c in p], **kw)

    def tapes(self, cv, key, W):
        """the strips of adhesive tape stuck on an item"""
        for (ta, tb) in self.lab.obj[key]["tapes"]:
            self._poly(cv, [W(ta - 1.6, tb - 1.0), W(ta + 1.6, tb - 1.0),
                            W(ta + 1.6, tb + 1.0), W(ta - 1.6, tb + 1.0)],
                       fill="#f0e8d2", outline="#a99c7d", width=2)
            for d in (-0.5, 0.5):
                p1, p2 = W(ta - 1.3, tb + d), W(ta + 1.3, tb + d)
                cv.create_line(p1[0], p1[1], p2[0], p2[1], fill="#d8ceb2")

    # ------------------------------------------------------------------ #
    def draw_ruler(self, cv, rect):
        lab = self.lab
        x, y, ang = lab.pose("ruler")
        u, v = dirv(ang), dirv(ang + 90.0)

        def W(a, b):
            return ((x + u[0] * a + v[0] * b) * SC,
                    (y + u[1] * a + v[1] * b) * SC)

        self._poly(cv, [W(-30.4, -2.6), W(30.4, -2.6), W(30.4, 2.6),
                        W(-30.4, 2.6)], fill=C_ALU, outline=C_ALU_E)
        self._poly(cv, [W(-30.4, -2.6), W(30.4, -2.6), W(30.4, -2.0),
                        W(-30.4, -2.0)], fill="#f2f4f5", outline="")
        for i in range(0, 601, TSTEP):
            a = -30 + i * 0.1
            wx, wy = W(a, 0)
            if not (rect[0] * SC - 30 < wx < rect[2] * SC + 30 and
                    rect[1] * SC - 30 < wy < rect[3] * SC + 30):
                continue
            if i % 100 == 0:
                ln, col = 2.0, C_TICK
            elif i % 50 == 0:
                ln, col = 1.4, C_TICK
            else:
                ln, col = 0.85, "#555"
            p1, p2 = W(a, 2.6), W(a, 2.6 - ln)
            cv.create_line(p1[0], p1[1], p2[0], p2[1], fill=col)
            if i % 100 == 0:
                pt = W(a, -0.6)
                cv.create_text(pt[0], pt[1], text=str(i // 10), fill=C_TICK,
                               font=("", 9), angle=ang % 360)
        # ---- the laser, rebuilt from the photographs -------------------
        #  measured on the top-view photograph with the 12 mm diode module
        #  as the scale (150 px/cm):  L-shaped aluminium bracket 7.3 x 5.5,
        #  2 x AA battery holder 5.7 x 1.6, black diode module 2.27 long x
        #  1.20 dia, white printed clamp 2.13 long x 1.53 dia with a screw
        #  tab, brass bar 4C 0.47 dia.  The optical axis is 1.2 cm from the
        #  front edge of the bracket.
        s = lab.slider
        for cu in (-3.2, 3.2):               # the two red clamps
            self._poly(cv, [W(s + cu - 1.7, -3.0), W(s + cu + 1.7, -3.0),
                            W(s + cu + 1.7, 3.0), W(s + cu - 1.7, 3.0)],
                       fill=C_RED, outline=C_RED_D)
            q = W(s + cu, -1.7)
            cv.create_oval(q[0] - 0.85 * SC, q[1] - 0.5 * SC,
                           q[0] + 0.85 * SC, q[1] + 0.5 * SC,
                           fill="#f0e9e6", outline=C_RED_D)
            for r_ in range(2):
                for c_ in range(4):
                    q = W(s + cu - 1.05 + c_ * 0.7, 0.7 + r_ * 0.9)
                    cv.create_oval(q[0] - 1.3, q[1] - 1.3, q[0] + 1.3,
                                   q[1] + 1.3, fill="#9c211b", outline="")
        # clear acrylic plate screwed onto the two clamps: the metal head
        # turns on top of it about the brass pivot 4A
        self._poly(cv, [W(s - 4.9, -2.7), W(s + 4.9, -2.7), W(s + 4.9, 2.7),
                        W(s - 4.9, 2.7)], fill="", outline="#9fb0b6",
                   width=2)
        self._poly(cv, [W(s - 4.9, -2.7), W(s + 4.9, -2.7), W(s + 4.9, -2.4),
                        W(s - 4.9, -2.4)], fill="#f2f8fa", outline="")
        self._poly(cv, [W(s - 4.9, 2.4), W(s + 4.9, 2.4), W(s + 4.9, 2.7),
                        W(s - 4.9, 2.7)], fill="#dae4e8", outline="")
        for cu in (-4.1, 4.1):
            q = W(s + cu, 0.0)
            cv.create_oval(q[0] - 0.2 * SC, q[1] - 0.2 * SC,
                           q[0] + 0.2 * SC, q[1] + 0.2 * SC,
                           fill="#c9ced1", outline="#8b959a")
        # ---- the head : everything below turns with bar 4C -------------
        pv = lab.pivot()
        fu = lab.beam_dir()
        wv = (-fu[1], fu[0])

        def B(a, b):
            return ((pv[0] + fu[0] * a + wv[0] * b) * SC,
                    (pv[1] + fu[1] * a + wv[1] * b) * SC)

        # L-bracket : horizontal base plate seen from above
        self._poly(cv, [B(-4.5, -3.2), B(2.8, -3.2), B(2.8, 2.3),
                        B(-4.5, 2.3)], fill="#c3c8cc", outline="#7e8488")
        self._poly(cv, [B(-4.5, -3.2), B(2.8, -3.2), B(2.8, -2.4),
                        B(-4.5, -2.4)], fill="#dfe3e6", outline="")
        # the vertical plate, edge on, with the 2 x AA battery holder
        self._poly(cv, [B(-4.5, -3.2), B(-4.1, -3.2), B(-4.1, 2.3),
                        B(-4.5, 2.3)], fill="#9aa0a4", outline="#6e7478")
        self._poly(cv, [B(-4.1, -3.0), B(-2.5, -3.0), B(-2.5, 1.8),
                        B(-4.1, 1.8)], fill="#1a1a1c", outline="#000")
        for bb in (-2.2, 0.9):
            self._poly(cv, [B(-3.9, bb - 0.55), B(-2.7, bb - 0.55),
                            B(-2.7, bb + 0.55), B(-3.9, bb + 0.55)],
                       fill="#d8d4c8", outline="#8e8a80")
        # red / black leads looping to the diode
        cv.create_line(B(-2.6, -2.4)[0], B(-2.6, -2.4)[1],
                       B(-0.4, -2.9)[0], B(-0.4, -2.9)[1],
                       B(0.9, -1.2)[0], B(0.9, -1.2)[1], smooth=True,
                       fill="#c3312a", width=max(2, 0.16 * SC))
        cv.create_line(B(-2.6, -1.9)[0], B(-2.6, -1.9)[1],
                       B(-0.2, -2.4)[0], B(-0.2, -2.4)[1],
                       B(0.9, -0.9)[0], B(0.9, -0.9)[1], smooth=True,
                       fill="#1b1b1b", width=max(2, 0.16 * SC))
        # the brass pivot 4A : the metal head turns about it on the acrylic
        pq = B(0.0, 0.0)
        cv.create_oval(pq[0] - 0.95 * SC, pq[1] - 0.95 * SC,
                       pq[0] + 0.95 * SC, pq[1] + 0.95 * SC,
                       fill="#a98a2e", outline="#7d6320", width=2)
        # brass bar 4C, collinear with the diode, reaching out behind
        q0, q1 = B(-16.0, 0.0), B(-1.0, 0.0)
        cv.create_line(q0[0], q0[1], q1[0], q1[1], fill="#8a6a1e",
                       width=max(2, 0.47 * SC), capstyle="round")
        cv.create_line(q0[0], q0[1], q1[0], q1[1], fill=C_BRASS,
                       width=max(1, 0.30 * SC), capstyle="round")
        # black diode module
        d0, d1 = B(-1.0, 0.0), B(1.3, 0.0)
        cv.create_line(d0[0], d0[1], d1[0], d1[1], fill="#101010",
                       width=max(3, 1.20 * SC), capstyle="butt")
        cv.create_line(d0[0], d0[1], d1[0], d1[1], fill="#242424",
                       width=max(1, 0.45 * SC), capstyle="butt")
        # white printed clamp with its screw tab
        self._poly(cv, [B(1.3, -0.77), B(3.4, -0.77), B(3.4, 0.77),
                        B(1.3, 0.77)], fill="#f4f4f2", outline="#b6b6b0")
        self._poly(cv, [B(1.7, 0.77), B(2.5, 0.77), B(2.5, 1.5),
                        B(1.7, 1.5)], fill="#f4f4f2", outline="#b6b6b0")
        q = B(2.1, 1.15)
        cv.create_oval(q[0] - 0.22 * SC, q[1] - 0.22 * SC,
                       q[0] + 0.22 * SC, q[1] + 0.22 * SC, fill=C_BRASS,
                       outline="#7d6320")
        # brass thumb screw 4A on the base plate
        q = B(-1.2, -2.6)
        cv.create_oval(q[0] - 0.32 * SC, q[1] - 0.32 * SC,
                       q[0] + 0.32 * SC, q[1] + 0.32 * SC, fill=C_BRASS,
                       outline="#7d6320")
        # the aperture
        ap = B(lab.BARREL, 0.0)
        rap = max(2, 0.20 * SC)
        cv.create_oval(ap[0] - rap, ap[1] - rap, ap[0] + rap, ap[1] + rap,
                       fill=BEAM if lab.laser_on else "#3a3a3a",
                       outline="#6b1a10")
        # switch 3C
        sw = B(-3.6, 1.9)
        rsw = max(4, 0.34 * SC)
        cv.create_oval(sw[0] - rsw, sw[1] - rsw, sw[0] + rsw, sw[1] + rsw,
                       fill="#3a7d46" if lab.laser_on else "#5a5a5a",
                       outline="#141414", width=2)
        tx = B(-6.4, 2.6)
        cv.create_text(tx[0], tx[1], text="3C / " +
                       ("3A" if lab.level == "low" else "3B"),
                       fill="#dedede", font=("", 8))
        self.tapes(cv, "ruler", W)
        self.sel_mark(cv, "ruler", W)
        if lab.sel == "laser":
            pvq = lab.pivot()
            r = 5.6 * SC
            cv.create_oval(pvq[0] * SC - r, pvq[1] * SC - r,
                           pvq[0] * SC + r, pvq[1] * SC + r,
                           outline="#ffd45e", width=2, dash=(6, 4))

    # ------------------------------------------------------------------ #
    def draw_ruler8(self, cv, rect):
        lab = self.lab
        x, y, ang = lab.pose("ruler8")
        u, v = dirv(ang), dirv(ang + 90.0)

        def W(a, b):
            return ((x + u[0] * a + v[0] * b) * SC,
                    (y + u[1] * a + v[1] * b) * SC)

        # clear acrylic: only the edges are drawn, the body stays see-through
        self._poly(cv, [W(-15.6, -1.9), W(15.6, -1.9), W(15.6, 1.9),
                        W(-15.6, 1.9)], fill="", outline="#8fa3aa", width=2)
        self._poly(cv, [W(-15.6, -1.9), W(15.6, -1.9), W(15.6, -1.62),
                        W(-15.6, -1.62)], fill="#f2f8fa", outline="")
        self._poly(cv, [W(-15.6, 1.62), W(15.6, 1.62), W(15.6, 1.9),
                        W(-15.6, 1.9)], fill="#dae4e8", outline="")
        for i in range(0, 301, TSTEP):
            a = -15 + i * 0.1
            wx, wy = W(a, 0)
            if not (rect[0] * SC - 30 < wx < rect[2] * SC + 30 and
                    rect[1] * SC - 30 < wy < rect[3] * SC + 30):
                continue
            if i % 100 == 0:
                ln, col = 1.55, C_TICK
            elif i % 50 == 0:
                ln, col = 1.0, "#3d4448"
            else:
                ln, col = 0.5, "#93a0a5"
            p1, p2 = W(a, 1.9), W(a, 1.9 - ln)
            cv.create_line(p1[0], p1[1], p2[0], p2[1], fill=col)
            if i % 100 == 0:
                pt = W(a, -0.7)
                cv.create_text(pt[0], pt[1], text=str(i // 10), fill=C_TICK,
                               font=("", 8), angle=ang % 360)
        self.tapes(cv, "ruler8", W)
        self.sel_mark(cv, "ruler8", W)

    # ------------------------------------------------------------------ #
    def draw_disk(self, cv, rect=None):
        lab = self.lab
        cx, cy, ang = lab.pose("disk")
        u, v = dirv(ang), dirv(ang + 90.0)

        def W(a, b):
            return ((cx + u[0] * a + v[0] * b) * SC,
                    (cy + u[1] * a + v[1] * b) * SC)

        self._poly(cv, [W(-15.2, -15.2), W(15.2, -15.2), W(15.2, 15.2),
                        W(-15.2, 15.2)], fill=C_WOOD, outline=C_WOOD_E)
        self._poly(cv, [W(-14.2, -14.2), W(14.2, -14.2), W(14.2, 14.2),
                        W(-14.2, 14.2)], fill=C_PLY, outline=C_WOOD_E)
        self._poly(cv, [W(-13.0, -13.0), W(13.0, -13.0), W(13.0, 13.0),
                        W(-13.0, 13.0)], fill=C_WHITE, outline="#cfcdc4")
        Rt, Rl = 10.9, 11.9
        vis_ = rect is None or (rect[0] - 16 < cx < rect[2] + 16 and
                                rect[1] - 16 < cy < rect[3] + 16)
        for k in range(0, 180 if vis_ else 0):
            a = math.radians(2.0 * k + lab.prot_zero)
            ln = 0.55 if k % 5 else 1.05
            ca, sa_ = math.cos(a), math.sin(a)
            p1 = W((Rt - ln) * ca, -(Rt - ln) * sa_)
            p2 = W(Rt * ca, -Rt * sa_)
            cv.create_line(p1[0], p1[1], p2[0], p2[1], fill=C_TICK,
                           width=2 if k % 5 == 0 else 1)
            if k % 5 == 0:
                pl = W(Rl * ca, -Rl * sa_)
                cv.create_text(pl[0], pl[1], text=str(2 * k), fill=C_TICK,
                               font=("", 8))
        r = 10.0 * SC
        pc = (cx * SC, cy * SC)
        cv.create_oval(pc[0] - r, pc[1] - r, pc[0] + r, pc[1] + r,
                       fill=C_DISK_D if lab.dark else C_DISK,
                       outline="#9fc4cf", width=2)
        cv.create_oval(pc[0] - r + 7, pc[1] - r + 7, pc[0] + r - 7,
                       pc[1] + r - 7, outline="#f4fbfd")
        self.tapes(cv, "disk", W)
        self.sel_mark(cv, "disk", W)
        if lab.parchment:
            cv.create_oval(pc[0] - r - 9, pc[1] - r - 9, pc[0] + r + 9,
                           pc[1] + r + 9, outline=C_PARCH, width=5)

    # ------------------------------------------------------------------ #
    def draw_holder(self, cv):
        lab = self.lab
        cx, cy, rot = lab.pose("holder")
        u, v = dirv(rot), dirv(rot + 90.0)

        def W(a, b):
            return ((cx + u[0] * a + v[0] * b) * SC,
                    (cy + u[1] * a + v[1] * b) * SC)

        self._poly(cv, [W(-12.5, -8.5), W(12.5, -8.5), W(12.5, 8.5),
                        W(-12.5, 8.5)], fill=C_PLY, outline=C_WOOD_E)
        self._poly(cv, [W(-11.5, -7.6), W(11.5, -7.6), W(11.5, 7.6),
                        W(-11.5, 7.6)], fill=C_WHITE, outline="#cfcdc4")
        pc = (cx * SC, cy * SC)
        r = 4.4 * SC
        cv.create_oval(pc[0] - r, pc[1] - r, pc[0] + r, pc[1] + r,
                       fill=C_HOLD, outline="#000")
        r2 = 3.3 * SC
        cv.create_oval(pc[0] - r2, pc[1] - r2, pc[0] + r2, pc[1] + r2,
                       fill=C_HOLD2, outline="#3c3c3c")
        if lab.hold_item == "grating":
            a, b = lab.grating_seg()
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy) or 1
            nx, ny = -dy / L * 0.45, dx / L * 0.45
            self._poly(cv, [((a[0] + nx) * SC, (a[1] + ny) * SC),
                            ((b[0] + nx) * SC, (b[1] + ny) * SC),
                            ((b[0] - nx) * SC, (b[1] - ny) * SC),
                            ((a[0] - nx) * SC, (a[1] - ny) * SC)],
                       fill=C_GGLASS, outline=C_GFRAME, width=3)
        else:
            self._poly(cv, [(q[0] * SC, q[1] * SC)
                            for q in lab.prism_poly()],
                       fill=C_PRISM, outline="#7fa7b4", width=2)
        self.tapes(cv, "holder", W)
        self.sel_mark(cv, "holder", W)

    # ------------------------------------------------------------------ #
    def draw_screen(self, cv):
        lab = self.lab
        a, b = lab.screen_seg()
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L * 0.8, dx / L * 0.8
        self._poly(cv, [((a[0] + nx) * SC, (a[1] + ny) * SC),
                        ((b[0] + nx) * SC, (b[1] + ny) * SC),
                        ((b[0] - nx) * SC, (b[1] - ny) * SC),
                        ((a[0] - nx) * SC, (a[1] - ny) * SC)],
                   fill=C_SCREEN, outline="#3a3a3a")
        for f in (-0.42, 0.42):
            px = (a[0] + dx * (0.5 + f) - nx * 3.0) * SC
            py = (a[1] + dy * (0.5 + f) - ny * 3.0) * SC
            cv.create_oval(px - 9, py - 9, px + 9, py + 9, fill="#4a4a4a",
                           outline="#2a2a2a")

    # ------------------------------------------------------------------ #
    def draw_roll(self, cv):
        lab = self.lab
        cx, cy, _a = lab.pose("tape6")
        pc = (cx * SC, cy * SC)
        for r, col in ((4.0, C_ROLL), (3.2, C_ROLL_C), (2.0, C_ROLL_I)):
            rr = r * SC
            cv.create_oval(pc[0] - rr, pc[1] - rr, pc[0] + rr, pc[1] + rr,
                           fill=col, outline="#b3a98d")
        cv.create_arc(pc[0] - 4.0 * SC, pc[1] - 4.0 * SC, pc[0] + 4.0 * SC,
                      pc[1] + 4.0 * SC, start=20, extent=40, style="arc",
                      outline="#ffffff", width=3)
        if lab.tape_held:
            rr = 4.8 * SC
            cv.create_oval(pc[0] - rr, pc[1] - rr, pc[0] + rr, pc[1] + rr,
                           outline="#ffd45e", width=3, dash=(6, 4))

    # ------------------------------------------------------------------ #
    def draw_tape(self, cv, rect):
        lab = self.lab
        a, b = lab.tape_a, lab.tape_b
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 1:
            return
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        px, py = -uy, ux
        wA = 1.5
        self._poly(cv, [((a[0] + px * wA) * SC, (a[1] + py * wA) * SC),
                        ((b[0] + px * wA) * SC, (b[1] + py * wA) * SC),
                        ((b[0] - px * wA) * SC, (b[1] - py * wA) * SC),
                        ((a[0] - px * wA) * SC, (a[1] - py * wA) * SC)],
                   fill=C_TAPE, outline="#b5ae95")
        i = 0
        while i <= L * 10:
            x, y = a[0] + ux * i * 0.1, a[1] + uy * i * 0.1
            if not (rect[0] - 2 < x < rect[2] + 2 and
                    rect[1] - 2 < y < rect[3] + 2):
                i += TSTEP
                continue
            if i % 100 == 0:
                ln, col = 1.25, C_TICK
            elif i % 50 == 0:
                ln, col = 0.9, "#3d4448"
            else:
                ln, col = 0.45, "#9a9484"
            cv.create_line((x - px * wA) * SC, (y - py * wA) * SC,
                           (x - px * (wA - ln)) * SC,
                           (y - py * (wA - ln)) * SC, fill=col)
            if i % 100 == 0:
                cv.create_text((x + px * 0.35) * SC, (y + py * 0.35) * SC,
                               text=str(i // 10), fill=C_TICK, font=("", 8),
                               angle=-math.degrees(math.atan2(uy, ux)))
            i += TSTEP
        for q, big in ((a, True), (b, False)):
            qq = (q[0] * SC, q[1] * SC)
            if big:
                cv.create_oval(qq[0] - 22, qq[1] - 16, qq[0] + 22,
                               qq[1] + 16, fill=C_TCASE, outline="#a02757")
                cv.create_oval(qq[0] - 6, qq[1] - 6, qq[0] + 6, qq[1] + 6,
                               fill=C_TBTN, outline="#a08b12")
            else:
                cv.create_rectangle(qq[0] - 7, qq[1] - 7, qq[0] + 7,
                                    qq[1] + 7, fill="#e0b83a",
                                    outline="#8a6f18")


# ==========================================================================
class FrontView(tk.Toplevel):
    W, H = 900, 400
    PS = 7.0

    def __init__(self, master, lab):
        super().__init__(master)
        self.lab = lab
        self.title(_("front"))
        self.resizable(False, False)
        self.cv = tk.Canvas(self, width=self.W, height=self.H, bg="#070707",
                            highlightthickness=0)
        self.cv.pack()
        ttk.Label(self, text=_("front_hint")).pack(anchor="w", padx=6,
                                                   pady=2)
        self.drag = None
        self.cv.bind("<Button-1>", self.press)
        self.cv.bind("<B1-Motion>", self.move)
        self.cv.bind("<ButtonRelease-1>",
                     lambda e: setattr(self, "drag", None))
        self.tick()

    def cm(self, ex, ey):
        return ((ex - self.W / 2) / self.PS, (ey - self.H / 2) / self.PS)

    def px(self, x, y):
        return (self.W / 2 + x * self.PS, self.H / 2 + y * self.PS)

    def press(self, ev):
        x, y = self.cm(ev.x, ev.y)
        for k in ("ftape_a", "ftape_b"):
            q = getattr(self.lab, k)
            if math.hypot(x - q[0], y - q[1]) < 2.4:
                self.drag = k
                return

    def move(self, ev):
        if self.drag:
            setattr(self.lab, self.drag, list(self.cm(ev.x, ev.y)))
            self.draw()

    def tick(self):
        if not self.winfo_exists():
            return
        self.draw()
        self.after(140, self.tick)

    def draw(self):
        lab = self.lab
        cv = self.cv
        cv.delete("all")
        h2 = SCREEN_W / 2.0
        p0, p1 = self.px(-h2, -13.0), self.px(h2, 13.0)
        cv.create_rectangle(p0[0], p0[1], p1[0], p1[1], fill=C_SCREEN,
                            outline="#333")
        _s, _sp, _h, shots = lab.trace()
        rng = random.Random(4321)
        for (s, I) in shots:
            v = vis(I, lab.dark)
            if v <= 0.02:
                continue
            q = self.px(s, 0.0)
            for k, f in ((10.0, 0.10), (5.5, 0.28), (2.9, 0.72),
                         (1.4, 1.0)):
                r = k * (0.5 + 0.9 * v)
                cv.create_oval(q[0] - r, q[1] - r, q[0] + r, q[1] + r,
                               fill=mix("#131313", BEAM, min(1.0, v * f)),
                               outline="")
            for _i in range(int(34 * v)):
                a = rng.uniform(0, 6.283)
                rr_ = rng.uniform(0, 4.0 * (0.4 + v))
                sx = q[0] + rr_ * math.cos(a)
                sy = q[1] + rr_ * math.sin(a) * 0.85
                cv.create_oval(sx - 0.8, sy - 0.8, sx + 0.8, sy + 0.8,
                               fill=mix("#131313", BEAM2,
                                        rng.uniform(0.3, 1.0)), outline="")
        a, b = lab.ftape_a, lab.ftape_b
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L > 1:
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            px_, py_ = -uy, ux
            c = [self.px(a[0] + px_ * 1.4, a[1] + py_ * 1.4),
                 self.px(b[0] + px_ * 1.4, b[1] + py_ * 1.4),
                 self.px(b[0] - px_ * 1.4, b[1] - py_ * 1.4),
                 self.px(a[0] - px_ * 1.4, a[1] - py_ * 1.4)]
            cv.create_polygon([q for p in c for q in p], fill=C_TAPE,
                              outline="#b5ae95")
            i = 0
            while i <= L * 10:
                x, y = a[0] + ux * i * 0.1, a[1] + uy * i * 0.1
                ln = 1.3 if i % 100 == 0 else (0.95 if i % 50 == 0 else 0.55)
                q1 = self.px(x - px_ * 1.4, y - py_ * 1.4)
                q2 = self.px(x - px_ * (1.4 - ln), y - py_ * (1.4 - ln))
                cv.create_line(q1[0], q1[1], q2[0], q2[1], fill=C_TICK)
                if i % 100 == 0:
                    qt = self.px(x + px_ * 0.35, y + py_ * 0.35)
                    cv.create_text(qt[0], qt[1], text=str(i // 10),
                                   fill=C_TICK, font=("", 8),
                                   angle=-math.degrees(math.atan2(uy, ux)))
                i += 1
            for q in (a, b):
                qq = self.px(q[0], q[1])
                cv.create_oval(qq[0] - 5, qq[1] - 5, qq[0] + 5, qq[1] + 5,
                               fill="#e0b83a", outline="#8a6f18")


# ==========================================================================
class LabTab(ttk.Frame):
    VW, VH = 1440, 900
    MW = 340

    def __init__(self, master, lab, app):
        super().__init__(master)
        self.lab = lab
        self.app = app
        self.view = View(lab)
        self.front = None

        right = ttk.Frame(self, padding=6, width=self.MW + 24)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        left = ttk.Frame(self)
        left.pack(side="left", fill="both", expand=True)
        self.cv = tk.Canvas(left, width=self.VW, height=self.VH,
                            highlightthickness=0, bg=C_MAT,
                            scrollregion=(-5 * SC, -5 * SC,
                                          (ROOM_W + 5) * SC,
                                          (ROOM_D + 5) * SC))
        hb = ttk.Scrollbar(left, orient="horizontal", command=self.cv.xview)
        vb = ttk.Scrollbar(left, orient="vertical", command=self.cv.yview)
        self.cv.configure(xscrollcommand=hb.set, yscrollcommand=vb.set)
        self.cv.grid(row=0, column=0, sticky="nsew")
        vb.grid(row=0, column=1, sticky="ns")
        hb.grid(row=1, column=0, sticky="ew")
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        ttk.Label(right, text=_("tray"),
                  font=("", 9, "bold")).pack(anchor="w")
        self.btn = {}
        for k in TRAY:
            b = ttk.Button(right, text=nm(k), width=32,
                           command=lambda kk=k: self.toggle(kk))
            b.pack(anchor="w", pady=1)
            self.btn[k] = b

        self.lvl = tk.StringVar(value="low")
        ttk.Label(right, text=_("level")).pack(anchor="w", pady=(8, 0))
        ttk.Radiobutton(right, text=_("low"), value="low", variable=self.lvl,
                        command=self.sync).pack(anchor="w")
        ttk.Radiobutton(right, text=_("high"), value="high",
                        variable=self.lvl, command=self.sync).pack(anchor="w")
        self.on = tk.BooleanVar(value=False)
        ttk.Checkbutton(right, text=_("laser_on"), variable=self.on,
                        command=self.sync).pack(anchor="w", pady=(6, 0))
        self.lbl_dark = ttk.Label(right, text="")
        self.lbl_dark.pack(anchor="w", pady=(4, 0))
        row0 = ttk.Frame(right)
        row0.pack(anchor="w")
        ttk.Label(row0, text=_("tscale")).pack(side="left")
        self.ts = tk.IntVar(value=1)
        for lb, v in (("1x", 1), ("10x", 10)):
            ttk.Radiobutton(row0, text=lb, value=v,
                            variable=self.ts).pack(side="left")
        self.par = tk.BooleanVar(value=False)
        ttk.Checkbutton(right, text=_("parch"), variable=self.par,
                        command=self.sync).pack(anchor="w")
        self.itm = tk.StringVar(value="grating")
        row = ttk.Frame(right)
        row.pack(anchor="w", pady=(6, 0))
        ttk.Radiobutton(row, text="12C", value="grating", variable=self.itm,
                        command=self.sync).pack(side="left")
        ttk.Radiobutton(row, text="12D", value="prism", variable=self.itm,
                        command=self.sync).pack(side="left")
        box = ttk.Frame(right)
        box.pack(anchor="w", fill="both", expand=True, pady=(8, 0))
        hint = tk.Text(box, width=1, height=8, wrap="word", font=("", 8),
                       relief="flat", background="#f0f0f0",
                       highlightthickness=0)
        hsb = ttk.Scrollbar(box, orient="vertical", command=hint.yview)
        hint.configure(yscrollcommand=hsb.set)
        hint.pack(side="left", fill="both", expand=True)
        hsb.pack(side="right", fill="y")
        hint.insert("1.0", _("hint"))
        hint.configure(state="disabled")

        self.drag = None
        self.press_xy = None
        self.side = 0
        self._pending = False
        self._last = {}
        self.cv.bind("<Button-1>", self.b1)
        self.cv.bind("<B1-Motion>", self.m1)
        self.cv.bind("<ButtonRelease-1>", self.r1)
        self.cv.bind("<Double-Button-1>", self.dbl)
        for b in ("2", "3"):
            self.cv.bind("<Button-%s>" % b, self.pan_start)
            self.cv.bind("<B%s-Motion>" % b, self.pan_move)
        self.cv.bind("<Motion>", self.hover)
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.cv.bind(seq, self.wheel)
        self.cv.xview_moveto((136 - 31 + 5) / (ROOM_W + 10.0))
        self.cv.yview_moveto((96 - 22 + 5) / (ROOM_D + 10.0))
        self.redraw()

    # ------------------------------------------------------------------ #
    def sync(self):
        lab = self.lab
        lab.level = self.lvl.get()
        lab.laser_on = self.on.get()
        lab.parchment = self.par.get()
        lab.hold_item = self.itm.get()
        self.redraw()

    def toggle(self, k):
        lab = self.lab
        if k == "tape":
            lab.tape_on = not lab.tape_on
            if lab.tape_on:
                c = self.center()
                lab.tape_a = [c[0] - 60.0, c[1] + 14.0]
                lab.tape_b = [c[0] + 60.0, c[1] + 14.0]
        else:
            o = lab.obj[k]
            o["on"] = not o["on"]
            if o["on"]:
                c = self.center()
                o["pos"] = [c[0], c[1]]
                self.side = self.screen_side(k)
                self.avoid_screen(k)
                self.separate(k)
                self.side = 0
        self.redraw()

    def center(self):
        r = self.rect()
        return (0.5 * (r[0] + r[2]), 0.5 * (r[1] + r[3]))

    def rect(self):
        w = self.cv.winfo_width() or self.VW
        h = self.cv.winfo_height() or self.VH
        x0 = self.cv.canvasx(0) / SC
        y0 = self.cv.canvasy(0) / SC
        return (x0, y0, x0 + w / SC, y0 + h / SC)

    # ------------------------------------------------------------------ #
    def cm(self, ev):
        return (self.cv.canvasx(ev.x) / SC, self.cv.canvasy(ev.y) / SC)

    def pick(self, x, y):
        lab = self.lab
        for key in reversed(lab.order):
            if key not in lab.LOCAL or not lab.obj[key]["on"]:
                continue
            if not lab.obj[key]["tapes"]:
                continue
            a, b = lab.local(key, x, y)
            for i, t in enumerate(lab.obj[key]["tapes"]):
                if abs(t[0] - a) < 1.7 and abs(t[1] - b) < 1.1:
                    return "peel|%s|%d" % (key, i)
        if lab.tape_on:
            for k in ("tape_a", "tape_b"):
                q = getattr(lab, k)
                if math.hypot(x - q[0], y - q[1]) < 2.4:
                    return k
        if lab.obj["ruler"]["on"]:
            rx, ry, ang = lab.pose("ruler")
            u, v = dirv(ang), dirv(ang + 90.0)
            a = (x - rx) * u[0] + (y - ry) * u[1]
            b = (x - rx) * v[0] + (y - ry) * v[1]
            pv = lab.pivot()
            fu = lab.beam_dir()
            wv = (-fu[1], fu[0])
            tx, ty = x - pv[0], y - pv[1]
            pa = tx * fu[0] + ty * fu[1]
            pb = tx * wv[0] + ty * wv[1]
            if abs(pa + 3.6) < 0.7 and abs(pb - 1.9) < 0.7:
                return "switch"
            if (-16.4 < pa < lab.BARREL + 0.4 and abs(pb) < 1.0) or \
                    (-4.6 < pa < 2.9 and -3.3 < pb < 2.4):
                return "barrel"
            if abs(a - lab.slider) < 5.2 and abs(b) < 3.4:
                return "slider"
            if abs(a) < 30.6 and abs(b) < 2.8:
                return "ruler"
        if lab.obj["disk"]["on"]:
            cx, cy, ang = lab.pose("disk")
            u, v = dirv(ang), dirv(ang + 90.0)
            a = (x - cx) * u[0] + (y - cy) * u[1]
            b = (x - cx) * v[0] + (y - cy) * v[1]
            if abs(a) < 15.4 and abs(b) < 15.4:
                return "disk"
        if lab.obj["holder"]["on"]:
            cx, cy, ang = lab.pose("holder")
            u, v = dirv(ang), dirv(ang + 90.0)
            a = (x - cx) * u[0] + (y - cy) * u[1]
            b = (x - cx) * v[0] + (y - cy) * v[1]
            if math.hypot(a, b) < 4.6:
                return "holder12b"
            if abs(a) < 12.6 and abs(b) < 8.6:
                return "holder"
        if lab.obj["ruler8"]["on"]:
            cx, cy, ang = lab.pose("ruler8")
            u, v = dirv(ang), dirv(ang + 90.0)
            a = (x - cx) * u[0] + (y - cy) * u[1]
            b = (x - cx) * v[0] + (y - cy) * v[1]
            if abs(a) < 15.6 and abs(b) < 2.0:
                return "ruler8"
        if lab.obj["tape6"]["on"]:
            cx, cy, _a = lab.pose("tape6")
            if math.hypot(x - cx, y - cy) < 4.2:
                return "tape6"
        if lab.obj["screen"]["on"]:
            cx, cy, ang = lab.pose("screen")
            u, v = dirv(ang), dirv(ang + 90.0)
            a = (x - cx) * u[0] + (y - cy) * u[1]
            b = (x - cx) * v[0] + (y - cy) * v[1]
            if abs(a) < SCREEN_W / 2 + 1 and abs(b) < 3.0:
                return "screen"
        return None

    # ------------------------------------------------------------------ #
    def b1(self, ev):
        self.press_xy = (ev.x, ev.y)
        self.lab._pc.clear()
        x, y = self.cm(ev)
        if self.lab.tape_held and self.lab.obj["tape6"]["on"]:
            if self.stick_tape(x, y):
                return
        k = self.pick(x, y)
        if k is None:
            self.lab.sel = None
            self.redraw()
            if self.lab.tape_held:           # put the roll down here
                self.lab.tape_held = False
                self.lab.obj["tape6"]["pos"] = [x, y]
                self.redraw()
                return
            self.cv.scan_mark(ev.x, ev.y)
            self.drag = ("pan", 0, 0)
            return
        if k.startswith("peel|"):
            _p, key, i = k.split("|")
            self.lab.obj[key]["tapes"].pop(int(i))
            self.lab._pc.clear()
            self.redraw()
            return
        if k == "switch":
            self.on.set(not self.on.get())
            self.sync()
            return
        if k == "barrel":
            self.lab.sel = "laser"
            self.drag = ("slider", 0.0, 0.0)
            self.redraw()
            return
        if k == "tape6":
            self.lab.tape_held = not self.lab.tape_held
            if self.lab.tape_held:
                self.lab.obj["tape6"]["pos"] = [x, y]
            self.redraw()
            return
        if k in ("slider", "tape_a", "tape_b"):
            self.lab.sel = "laser" if k == "slider" else None
            if k == "slider":
                self.lab.raise_("ruler")
            self.drag = (k, 0.0, 0.0)
            self.redraw()
            return
        self.lab.sel = k
        if k == "holder12b":
            k = "holder"
        self.lab.raise_(k)
        if self.lab.obj[k]["tapes"]:
            if k == "screen":
                self.drag = ("screen", 1e9, 1e9)   # click-only, no moving
            self.redraw()
            return                       # taped down - peel it off first
        self.side = self.screen_side(k)
        cx, cy, _a = self.lab.pose(k)
        self.drag = (k, x - cx, y - cy)
        self.redraw()

    def m1(self, ev):
        if not self.drag:
            return
        self.lab._pc.clear()
        k, ox, oy = self.drag
        if k == "pan":
            self.cv.scan_dragto(ev.x, ev.y, gain=1)
            self.redraw()
            return
        x, y = self.cm(ev)
        lab = self.lab
        if k == "slider":
            rx, ry, ang = lab.pose("ruler")
            u = dirv(ang)
            lo, hi = lab.slider_limits()
            lab.slider = max(lo, min(hi,
                                     (x - rx) * u[0] + (y - ry) * u[1]))
        elif k in ("tape_a", "tape_b"):
            setattr(lab, k, [x, y])
        elif ox < 1e8:
            lab.obj[k]["pos"] = [x - ox, y - oy]
            self.avoid_screen(k)
            self.separate(k)
        self.redraw()

    def open_front(self):
        if self.front is None or not self.front.winfo_exists():
            self.front = FrontView(self, self.lab)
        else:
            self.front.deiconify()
            self.front.lift()
            self.front.focus_force()

    def dbl(self, ev):
        self.lab._pc.clear()
        x, y = self.cm(ev)
        if self.pick(x, y) == "screen" or self.lab.inside("screen", x, y):
            self.open_front()

    def stick_tape(self, x, y):
        """put a strip of tape where the roll is, or pull one off again"""
        lab = self.lab
        for key in reversed(lab.order):
            if key not in lab.LOCAL or not lab.obj[key]["on"]:
                continue
            if not lab.inside(key, x, y):
                continue
            a, b = lab.local(key, x, y)
            for t in lab.obj[key]["tapes"]:
                if abs(t[0] - a) < 1.9 and abs(t[1] - b) < 1.3:
                    lab.obj[key]["tapes"].remove(t)
                    lab._pc.clear()
                    self.redraw()
                    return True
            if key == "ruler" and abs(a - lab.slider) < 6.6:
                return True              # the slider is in the way
            o = lab.obj[key]
            if not o["tapes"]:
                # freeze the item exactly where it is, so it does not jump
                cx, cy, ang = lab.pose(key)
                o["pos"] = [cx, cy]
                o["ang"] = ang
                lab._pc.clear()
                a, b = lab.local(key, x, y)
            o["tapes"].append((a, b))
            lab._pc.clear()
            self.redraw()
            return True
        return False

    def screen_side(self, key):
        """which side of the black board the item is on ( +1 / -1 )"""
        lab = self.lab
        lab._pc.clear()
        if not lab.obj["screen"]["on"] or key not in lab.LOCAL:
            return 0
        sx, sy, ang = lab.pose("screen")
        v = dirv(ang + 90.0)
        px, py = lab.obj[key]["pos"]
        b = (px - sx) * v[0] + (py - sy) * v[1]
        return 1.0 if b >= 0 else -1.0

    NOCLASH = ("ruler", "disk", "holder", "screen")

    def separate(self, key):
        """true rectangle-against-rectangle test: items may touch, not overlap"""
        lab = self.lab
        lab._pc.clear()
        if key not in self.NOCLASH:
            return
        hA = lab.COLL[key]
        for other in list(lab.order):
            if other == key or other not in self.NOCLASH:
                continue
            if not lab.obj[other]["on"]:
                continue
            hB = lab.COLL[other]
            for _it in range(4):
                lab._pc.clear()
                ax_, ay_ = lab.obj[key]["pos"]
                aa = lab.obj[key]["ang"]
                bx_, by_, ba = lab.pose(other)
                ua, va = dirv(aa), dirv(aa + 90.0)
                ub, vb = dirv(ba), dirv(ba + 90.0)
                dx, dy = bx_ - ax_, by_ - ay_
                best = None
                for ax in (ua, va, ub, vb):
                    ra = (hA[0] * abs(ua[0] * ax[0] + ua[1] * ax[1]) +
                          hA[1] * abs(va[0] * ax[0] + va[1] * ax[1]))
                    rb = (hB[0] * abs(ub[0] * ax[0] + ub[1] * ax[1]) +
                          hB[1] * abs(vb[0] * ax[0] + vb[1] * ax[1]))
                    dist = dx * ax[0] + dy * ax[1]
                    pen = ra + rb + 0.35 - abs(dist)
                    if pen <= 0.0:
                        best = None
                        break
                    if best is None or pen < best[0]:
                        best = (pen, ax, 1.0 if dist >= 0 else -1.0)
                if best is None:
                    break
                pen, ax, sg = best
                lab.obj[key]["pos"] = [ax_ - ax[0] * pen * sg,
                                       ay_ - ax[1] * pen * sg]
            lab._pc.clear()

    def avoid_screen(self, key):
        """the black board is solid: an item cannot be pushed through it"""
        lab = self.lab
        lab._pc.clear()
        sgn = self.side
        if key == "screen" or not sgn or not lab.obj["screen"]["on"]:
            return
        h = lab.COLL.get(key)
        if h is None:
            return
        sx, sy, ang = lab.pose("screen")
        u, v = dirv(ang), dirv(ang + 90.0)
        th = math.radians(lab.obj[key]["ang"] - ang)
        c, sn = abs(math.cos(th)), abs(math.sin(th))
        ra = h[0] * c + h[1] * sn + 0.15
        rad = h[0] * sn + h[1] * c + 0.15 + lab.COLL["screen"][1]
        px, py = lab.obj[key]["pos"]
        a = (px - sx) * u[0] + (py - sy) * u[1]
        b = (px - sx) * v[0] + (py - sy) * v[1]
        if abs(a) > SCREEN_W / 2 + ra:
            return
        if b * sgn >= rad:
            return
        b = sgn * rad
        lab.obj[key]["pos"] = [sx + u[0] * a + v[0] * b,
                               sy + u[1] * a + v[1] * b]
        lab._pc.clear()

    def r1(self, ev):
        d = self.drag
        self.drag = None
        if d is None:
            return
        moved = (self.press_xy and
                 math.hypot(ev.x - self.press_xy[0],
                            ev.y - self.press_xy[1]) > 4)
        k = d[0]
        if k in self.lab.obj and moved:
            px, py = self.lab.obj[k]["pos"]
            if not (-6.0 < px < ROOM_W + 6.0 and -6.0 < py < ROOM_D + 6.0):
                self.lab.obj[k]["on"] = False
                if k == "tape6":
                    self.lab.tape_held = False
                self.redraw()
                return
        if k in ("tape_a", "tape_b") and moved:
            q = getattr(self.lab, k)
            if not (-6.0 < q[0] < ROOM_W + 6.0 and
                    -6.0 < q[1] < ROOM_D + 6.0):
                self.lab.tape_on = False
                self.redraw()
                return
        if d[0] == "screen" and not moved:
            self.open_front()

    def hover(self, ev):
        if self.lab.tape_held and not self.drag:
            self.lab.obj["tape6"]["pos"] = list(self.cm(ev))
            self.redraw()

    def pan_start(self, ev):
        self.cv.scan_mark(ev.x, ev.y)

    def pan_move(self, ev):
        self.cv.scan_dragto(ev.x, ev.y, gain=1)
        self.redraw()

    def wheel(self, ev):
        up = getattr(ev, "delta", 0) > 0 or getattr(ev, "num", 0) == 4
        step = 0.25 if (getattr(ev, "state", 0) & 0x0001) else 2.0
        lab = self.lab
        lab._pc.clear()
        k = lab.sel
        if k == "laser":
            lab.laser_fine += step if up else -step
        elif k == "holder12b":
            lab.hold_rot = (lab.hold_rot + (step if up else -step)) % 360.0
        elif k in ("ruler", "disk", "holder", "screen", "ruler8"):
            if len(lab.obj[k]["tapes"]) < 2:
                lab.obj[k]["ang"] = (lab.obj[k]["ang"] +
                                     (step if up else -step)) % 360.0
                lab._pc.clear()
                self.side = self.screen_side(k)
                self.avoid_screen(k)
                self.separate(k)
                self.side = 0
        else:
            self.cv.yview_scroll(-1 if up else 1, "units")
        self.redraw()

    # ------------------------------------------------------------------ #
    def tick(self, dt):
        lab = self.lab
        sc = self.ts.get()
        lab.t += dt * sc
        lab.clock += dt * sc
        lab._pc.clear()
        dark, left = lab.light_phase()
        txt = (_("blk") if dark else _("lit")) % ("%d:%02d" % (int(left) // 60,
                                                               int(left) % 60))
        self.lbl_dark.configure(text=txt)
        if dark != lab.dark:
            lab.dark = dark
            self.redraw()
            return
        if lab.wobbly():
            self.wobble_redraw()

    def wobble_redraw(self):
        """redraw only the items that actually move, plus the beams"""
        if self._pending:
            return
        lab = self.lab
        cv = self.cv
        rect = self.rect()
        moved = False
        for k in lab.order:
            o = lab.obj[k]
            if not (o["on"] and k in lab.LOCAL and len(o["tapes"]) < 2):
                continue
            p = lab.pose(k)
            q = self._last.get(k)
            if q is None or (abs(p[0] - q[0]) * SC > 0.4 or
                             abs(p[1] - q[1]) * SC > 0.4 or
                             abs(p[2] - q[2]) > 0.03):
                cv.delete(k)
                self.view.draw_item(cv, k, rect)
                self._last[k] = p
                moved = True
        if moved:
            cv.delete("beam")
            self.view.draw_beams(cv)
            for k in lab.order:
                cv.tag_raise(k)
            cv.tag_raise("mtape")
            cv.tag_raise("beam")

    def redraw(self):
        if self._pending:
            return
        self._pending = True
        self.after_idle(self._do_redraw)

    def _do_redraw(self):
        self._pending = False
        self.lab._pc.clear()
        self.view.draw(self.cv, self.rect())
        self._last = {k: self.lab.pose(k) for k in self.lab.order
                      if k in self.lab.LOCAL}
        for k in TRAY:
            on = (self.lab.tape_on if k == "tape"
                  else self.lab.obj[k]["on"])
            self.btn[k].configure(text=("- " if on else "+ ") + nm(k))

class App:
    def __init__(self, root):
        self.root = root
        root.title(_("title"))
        root.geometry("1820x1010")
        self.lab = Lab()
        self.tab = LabTab(root, self.lab, self)
        self.tab.pack(fill="both", expand=True)
        self.dt = 0.25
        self._tick()

    def _tick(self):
        if not self.root.winfo_exists():
            return
        try:
            self.tab.tick(self.dt)
        except Exception:
            pass
        self.root.after(int(self.dt * 1000), self._tick)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
