#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
13th Asian Physics Olympiad (New Delhi, India, 2012)
Experimental Competition -- Question 1 : FRICTION
Virtual laboratory simulator.

HaslaLab / HaslaEdu.

Design rules obeyed by this file
--------------------------------
*  The simulator only ever shows what a real instrument / a real pair of eyes
   would show:  the masses printed on the weights, the mass printed on the pan,
   and the *visual appearance* of the cord next to the ruled acrylic plate.
   No physical quantity (mu, theta in radians, thresholds, ...) is computed or
   displayed for the student.
*  All hidden true parameters are re-randomised for every session (seed).
*  Standard library only.
"""

import math
import random
import sys
import tkinter as tk
from tkinter import ttk

LANG = "en"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


# ----------------------------------------------------------------------------
#  apparatus constants (taken from the printed apparatus list of the paper)
# ----------------------------------------------------------------------------
WEIGHT_SET = [500.0, 200.0, 200.0, 100.0, 50.0, 20.0, 20.0, 10.0, 5.0, 2.0, 2.0, 1.0]
SLOT_MASS = 100.0          # each slotted weight of the hanger
N_SLOTS = 8                # total 800.0 g
THETA_MIN = math.pi        # cord over two parallel pipes, clear of the post
THETA_STEP = math.pi / 2   # one quarter turn round the central vertical post
MAX_WRAPS = 15             # -> theta up to 17*pi/2

# ----------------------------------------------------------------------------
#  apparatus geometry (bench coordinates, mm-ish; x right, y into the scene,
#  z up).  Reconstructed from Fig.2(a), Fig.2(i) and Fig.3 of the question
#  paper: a square wooden platform on four white plastic legs, a central
#  vertical steel pipe and four horizontal steel pipes in a pin-wheel square
#  around it.  The left and right pipes overhang the front edge so that the
#  load and the pan can hang freely.
# ----------------------------------------------------------------------------
PIPE_R = 14.0
POST_R = 17.0
Z_HI = 118.0                       # the two pipes running front-to-back
Z_LO = 84.0                        # the two pipes running left-to-right
Z_CORD = Z_HI + PIPE_R             # the cord rides on top of them
Y_CORD = -96.0                     # the cord crosses in front of the platform
X_LOAD = 90.0 - PIPE_R             # outer side of the left pipe
X_EFF = 210.0 + PIPE_R             # outer side of the right pipe
PLAT = 300.0

#  name       axis  fixed   from     to     height
PIPES = [("LEFT",  "y",  90.0, -116.0, 300.0, Z_HI),
         ("RIGHT", "y", 210.0, -116.0, 300.0, Z_HI),
         ("FRONT", "x",  90.0,  -28.0, 328.0, Z_LO),
         ("BACK",  "x", 210.0,  -28.0, 328.0, Z_LO)]
STUBS = [(90.0, 30.0, Z_HI), (90.0, 258.0, Z_HI),
         (210.0, 30.0, Z_HI), (210.0, 258.0, Z_HI),
         (26.0, 90.0, Z_LO), (274.0, 90.0, Z_LO),
         (26.0, 210.0, Z_LO), (274.0, 210.0, Z_LO)]

# anchors of the drop zones of the assembly tab, in bench coordinates
ZONE_ANCHOR = {
    "table":  ((90.0, -246.0, -96.0), 148, 28),
    "plate":  ((70.0, -132.0, 92.0), 48, 40),
    "mag":    ((26.0, -206.0, 72.0), 44, 36),
    "pipes":  ((150.0, -96.0, 146.0), 68, 26),
    "load":   ((X_LOAD, -96.0, 4.0), 38, 42),
    "effort": ((X_EFF, -96.0, 2.0), 40, 42),
}


# ============================================================================
#  PHYSICS  (forward model -- capstan / Euler-Eytelwein equation)
# ============================================================================
class Model(object):
    """Hidden state of the bench.  Everything here is invisible to the student."""

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1, 10 ** 9)
        self.seed = int(seed)
        r = random.Random(self.seed)
        self._r = r

        # true coefficients of friction of the two cords against the steel pipes
        self.mu = {"dial": round(r.uniform(0.098, 0.116), 5),
                   "pink": round(r.uniform(0.138, 0.156), 5)}
        # the body of unknown mass and the pan (M_pan is printed on the pan)
        self.M_u = round(r.uniform(105.0, 135.0), 1)
        self.M_pan = round(r.uniform(27.0, 30.5), 1)

        # visual detectability of the creep of the cord: outside band_out the
        # motion is unmistakable, inside band_in nothing can be seen at all.
        self.band_out = r.uniform(0.010, 0.014)
        self.band_in = self.band_out * r.uniform(0.30, 0.45)

        # contamination of the pipe surface (greasy fingers)
        self.grease = 0.0
        self._offsets = {}

    # ---- reference mode (used by the verification harness) -----------------
    def force_reference(self):
        """Pin the hidden parameters onto the values of the official solution."""
        self.mu = {"dial": 0.10600, "pink": 0.14560}
        self.M_u = 119.4
        self.M_pan = 28.6
        self.band_out = 0.012
        self.band_in = 0.0042
        self.grease = 0.0
        self._offsets = {}

    # ---- surface scatter ---------------------------------------------------
    def _surface(self, key):
        if key not in self._offsets:
            self._offsets[key] = self._r.gauss(0.0, 0.0025)
        return self._offsets[key]

    def mu_eff(self, cord, key):
        m = self.mu[cord] * (1.0 - self.grease)
        return m * (1.0 + self._surface((cord, key)))

    # ---- the single observable of the experiment --------------------------
    def observe(self, cord, M_w, M_p, theta, magnifier=True):
        """
        What the eye sees at the ruled acrylic plate.

        Returns one of
            'down'       : the load descends, cord clearly slips
            'creep_down' : motion too slow to be certain
            'static'     : nothing moves
            'creep_up'   : motion too slow to be certain
            'up'         : the load rises, cord clearly slips the other way
        """
        if cord is None or M_w is None or M_w <= 0.0 or theta <= 0.0:
            return "invalid"
        key = (round(M_w, 3), round(theta, 5))
        mu = self.mu_eff(cord, key)
        lo = M_w * math.exp(-mu * theta)          # verge of the load moving down
        hi = M_w * math.exp(+mu * theta)          # verge of the load moving up
        f = 1.0 if magnifier else 4.0
        bo, bi = self.band_out * f, self.band_in * f
        if M_p < lo * (1.0 - bo):
            return "down"
        if M_p < lo * (1.0 - bi):
            return "creep_down"
        if M_p > hi * (1.0 + bo):
            return "up"
        if M_p > hi * (1.0 + bi):
            return "creep_up"
        return "static"

    def slip_rate(self, cord, M_w, M_p, theta, magnifier=True):
        """Dimensionless visual speed of the cord, only used for the animation."""
        st = self.observe(cord, M_w, M_p, theta, magnifier)
        if st in ("invalid", "static"):
            return 0.0
        key = (round(M_w, 3), round(theta, 5))
        mu = self.mu_eff(cord, key)
        lo = M_w * math.exp(-mu * theta)
        hi = M_w * math.exp(+mu * theta)
        if st in ("down", "creep_down"):
            x = max(0.0, (lo - M_p) / max(lo, 1e-9))
        else:
            x = max(0.0, (M_p - hi) / max(hi, 1e-9))
        v = 26.0 * math.sqrt(x)
        if st in ("creep_down", "creep_up"):
            v = min(v, 0.9)
        return -v if st in ("down", "creep_down") else v


# ============================================================================
#  small drawing helpers  (isometric apparatus)
# ============================================================================
def proj(x, y, z, ox, oy, s=1.0):
    return (ox + (x - 0.62 * y) * s, oy - (z + 0.55 * y) * s)


def shade(hexcol, f):
    hexcol = hexcol.lstrip("#")
    r, g, b = (int(hexcol[i:i + 2], 16) for i in (0, 2, 4))
    r = max(0, min(255, int(r * f)))
    g = max(0, min(255, int(g * f)))
    b = max(0, min(255, int(b * f)))
    return "#%02x%02x%02x" % (r, g, b)


def ellipse_cap(cv, p, dirv, rad, fill, outline, squash=0.36, tags=()):
    """Ellipse standing perpendicular to the projected axis direction dirv."""
    dx, dy = dirv
    L = math.hypot(dx, dy) or 1.0
    dx, dy = dx / L, dy / L
    nx, ny = -dy, dx
    pts = []
    for i in range(20):
        a = 2.0 * math.pi * i / 20.0
        pts += [p[0] + nx * rad * math.cos(a) + dx * rad * squash * math.sin(a),
                p[1] + ny * rad * math.cos(a) + dy * rad * squash * math.sin(a)]
    cv.create_polygon(pts, fill=fill, outline=outline, tags=tags)


def cylinder(cv, p0, p1, rad, base="#b9bec6", cap=True, tags=()):
    """Draw a cylinder whose projected axis runs from p0 to p1."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    bands = [(-1.00, -0.34, 0.74), (-0.34, 0.22, 1.10), (0.22, 0.62, 0.92),
             (0.62, 1.00, 0.66)]
    for a, b, f in bands:
        pts = [p0[0] + nx * rad * a, p0[1] + ny * rad * a,
               p1[0] + nx * rad * a, p1[1] + ny * rad * a,
               p1[0] + nx * rad * b, p1[1] + ny * rad * b,
               p0[0] + nx * rad * b, p0[1] + ny * rad * b]
        cv.create_polygon(pts, fill=shade(base, f), outline="", tags=tags)
    if cap:
        ellipse_cap(cv, p1, (dx, dy), rad, shade(base, 1.16), shade(base, 0.55),
                    tags=tags)


def quad(cv, a, b, c, d, fill, outline="", tags=()):
    cv.create_polygon([a[0], a[1], b[0], b[1], c[0], c[1], d[0], d[1]],
                      fill=fill, outline=outline, tags=tags)


# ============================================================================
#  bench state
# ============================================================================
class Bench(object):
    def __init__(self):
        self.installed = set()          # part keys
        self.cord = None                # 'dial' | 'pink'
        self.load = None                # 'hanger' | 'unknown'
        self.slots = N_SLOTS            # slotted weights left on the hanger
        self.pan = [False] * len(WEIGHT_SET)
        self.wraps = 0

    # --- derived ---
    def M_w(self, model):
        if self.load == "hanger":
            return self.slots * SLOT_MASS
        if self.load == "unknown":
            return model.M_u
        return None

    def added(self):
        return sum(w for w, on in zip(WEIGHT_SET, self.pan) if on)

    def M_p(self, model):
        return model.M_pan + self.added()

    def theta(self):
        return THETA_MIN + self.wraps * THETA_STEP

    def ready(self):
        return ("platform" in self.installed and self.cord is not None
                and self.load is not None and "pan" in self.installed
                and "weightbox" in self.installed)

    def can_see(self):
        return "acrylic" in self.installed

    def magnified(self):
        return "magnifier" in self.installed


# ============================================================================
#  part catalogue for the assembly tab
# ============================================================================
def parts_catalogue():
    return [
        dict(key="platform", zone="table",
             name=T("강철 파이프 조립대", "Steel pipe assembly"),
             note=T("중앙의 수직 파이프와 네 개의 수평 파이프, 나무 받침대",
                    "Central vertical pipe + four horizontal pipes on a wooden platform")),
        dict(key="acrylic", zone="plate",
             name=T("아크릴 눈금판", "Ruled acrylic sheet"),
             note=T("1.5 mm 간격 선. 수평 파이프 앞에 장착",
                    "Lines 1.5 mm apart, mounted in front of a horizontal pipe")),
        dict(key="magnifier", zone="mag",
             name=T("확대경 (손전등)", "Magnifying glass with torch"),
             note=T("눈금판을 확대해서 본다. 스위치 ON/OFF",
                    "Magnifies the ruled plate; blue slide switch ON/OFF")),
        dict(key="weightbox", zone="table",
             name=T("분동 상자", "Weight box"),
             note=T("500, 200x2, 100, 50, 20x2, 10, 5, 2x2, 1 g",
                    "500, 200x2, 100, 50, 20x2, 10, 5, 2x2, 1 g")),
        dict(key="cord_dial", zone="pipes",
             name=T("다이얼 코드 (흰색·청색 표시)", "Dial cord (white, blue marks)"),
             note=T("파이프 위로 걸친다 (Part 1)", "Passed over the pipes (Part 1)")),
        dict(key="cord_pink", zone="pipes",
             name=T("핑크 코드", "Pink cord"),
             note=T("파이프 위로 걸친다 (Part 2)", "Passed over the pipes (Part 2)")),
        dict(key="hanger", zone="load",
             name=T("슬롯 추 걸이 (100 g x 8)", "Slotted weight hanger (100 g x 8)"),
             note=T("하중 쪽 끝에 매단다", "Hung from the load end of the cord")),
        dict(key="unknown", zone="load",
             name=T("미지 질량 M_u", "Body of unknown mass M_u"),
             note=T("하중 쪽 끝에 매단다", "Hung from the load end of the cord")),
        dict(key="pan", zone="effort",
             name=T("플라스틱 접시", "Plastic pan"),
             note=T("가한 힘 쪽 끝에 매단다. 접시 옆면에 질량이 적혀 있다",
                    "Hung from the effort end; its mass is written on its side")),
        dict(key="cloth", zone="table",
             name=T("청소용 천", "Cleaning cloth"),
             note=T("파이프 표면을 닦는다", "For wiping the pipe surfaces")),
    ]


ASM_OX, ASM_OY, ASM_S = 652.0, 400.0, 0.70
BEN_OX, BEN_OY, BEN_S = 366.0, 402.0, 0.80


def zones_for(ox, oy, s):
    """Screen rectangles of the drop zones, derived from the same projection
    that draws the apparatus, so they always sit on the right part."""
    out = {}
    for k, ((x, y, z), hw, hh) in ZONE_ANCHOR.items():
        px, py = proj(x, y, z, ox, oy, s)
        out[k] = (px - hw * s, py - hh * s, px + hw * s, py + hh * s)
    return out


ZONE_LABEL = {
    "table":  T("작업대", "Work table"),
    "plate":  T("파이프 앞면", "Front of pipe"),
    "mag":    T("관찰 위치", "Viewing position"),
    "pipes":  T("파이프 위", "Over the pipes"),
    "load":   T("하중 쪽 끝", "Load end"),
    "effort": T("가한 힘 쪽 끝", "Effort end"),
}


# ============================================================================
#  assembly tab
# ============================================================================
class AssemblyTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.parts = parts_catalogue()
        self.drag = None

        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 2))
        ttk.Label(top, font=("TkDefaultFont", 10, "bold"),
                  text=T("부품을 왼쪽 목록에서 끌어다 장치의 알맞은 위치에 놓으세요. "
                         "부품을 오른쪽 클릭하면 제거됩니다.",
                         "Drag a part from the tray onto the correct place of the "
                         "apparatus.  Right-click an installed part to remove it.")
                  ).pack(anchor="w")

        self.cv = tk.Canvas(self, width=1180, height=600, bg="#f2efe6",
                            highlightthickness=0)
        self.cv.pack(padx=8, pady=4)
        self.msg = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.msg, foreground="#8a2b12").pack(anchor="w", padx=12)

        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_move)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Button-3>", self.on_right)
        self.redraw()

    # ---------------- tray ----------------
    def tray_slots(self):
        out = []
        y = 46
        for p in self.parts:
            out.append((p, 12, y, 300, y + 44))
            y += 50
        return out

    def redraw(self):
        cv, b = self.cv, self.app.bench
        cv.delete("all")
        cv.create_text(156, 24, text=T("부품 목록", "Parts tray"),
                       font=("TkDefaultFont", 11, "bold"))
        for p, x0, y0, x1, y1 in self.tray_slots():
            done = p["key"] in b.installed
            cv.create_rectangle(x0, y0, x1, y1,
                                fill="#dfe6d6" if done else "#ffffff",
                                outline="#9aa39a")
            self.part_icon(cv, p["key"], x0 + 22, (y0 + y1) / 2)
            cv.create_text(x0 + 46, y0 + 15, anchor="w", text=p["name"],
                           font=("TkDefaultFont", 9, "bold"),
                           fill="#4b6b3a" if done else "#222222", tags=("tray",))
            cv.create_text(x0 + 46, y0 + 31, anchor="w", text=p["note"],
                           font=("TkDefaultFont", 7), fill="#666666")
            if done:
                cv.create_text(x1 - 12, y0 + 22, text="OK",
                               font=("TkDefaultFont", 8, "bold"), fill="#3f7a2a")
        cv.create_line(312, 10, 312, 590, fill="#c9c2b0")
        draw_apparatus(cv, self.app.model, b, ox=ASM_OX, oy=ASM_OY, s=ASM_S)
        if self.drag is not None:
            self.draw_ghost()
        self.msg.set("")

    def draw_zones(self):
        for key, (x0, y0, x1, y1) in zones_for(ASM_OX, ASM_OY, ASM_S).items():
            self.cv.create_rectangle(x0, y0, x1, y1, dash=(4, 3),
                                     outline="#2f6fb0", tags=("zone",))
            self.cv.create_text((x0 + x1) / 2, y0 + 9, text=ZONE_LABEL[key],
                                fill="#2f6fb0", font=("TkDefaultFont", 8),
                                tags=("zone",))

    def part_icon(self, cv, key, cx, cy, sc=1.0):
        s = 15 * sc
        if key == "platform":
            cv.create_polygon(cx - s, cy + s * .3, cx + s, cy + s * .3,
                              cx + s * .7, cy - s * .2, cx - s * 1.3, cy - s * .2,
                              fill="#c79a63", outline="#8a6636")
            cylinder(cv, (cx - s, cy - s * .5), (cx + s * .6, cy - s * .5), s * .3)
        elif key == "acrylic":
            cv.create_rectangle(cx - s * .7, cy - s, cx + s * .7, cy + s,
                                fill="#dff0f5", outline="#7fa8b5")
            for i in range(5):
                cv.create_line(cx - s * .6, cy - s + 4 + i * 5.5,
                               cx + s * .6, cy - s + 4 + i * 5.5, fill="#5f8b99")
        elif key == "magnifier":
            cv.create_oval(cx - s * .8, cy - s * .8, cx + s * .5, cy + s * .5,
                           fill="#eef4f7", outline="#777777", width=2)
            cv.create_line(cx + s * .4, cy + s * .4, cx + s, cy + s, width=4, fill="#cccccc")
        elif key == "weightbox":
            cv.create_rectangle(cx - s, cy - s * .7, cx + s, cy + s * .8,
                                fill="#e8e2d4", outline="#8d8878")
            for i in range(3):
                cv.create_oval(cx - s * .8 + i * s * .7, cy - s * .4,
                               cx - s * .3 + i * s * .7, cy + s * .2,
                               fill="#c9a227", outline="#8a6d10")
        elif key == "cord_dial":
            cv.create_oval(cx - s, cy - s * .7, cx + s, cy + s * .7,
                           outline="#dddddd", width=4)
            cv.create_oval(cx - s * .5, cy - s * .35, cx + s * .5, cy + s * .35,
                           outline="#3f6fd0", width=2)
        elif key == "cord_pink":
            cv.create_oval(cx - s, cy - s * .7, cx + s, cy + s * .7,
                           outline="#ef9fc0", width=5)
        elif key == "hanger":
            cv.create_arc(cx - s * .4, cy - s, cx + s * .4, cy - s * .3,
                          start=0, extent=180, style="arc", width=3, outline="#c9a227")
            for i in range(4):
                cv.create_rectangle(cx - s * .6, cy - s * .3 + i * s * .35,
                                    cx + s * .6, cy - s * .05 + i * s * .35,
                                    fill="#c9a227", outline="#8a6d10")
        elif key == "unknown":
            cv.create_arc(cx - s * .35, cy - s, cx + s * .35, cy - s * .35,
                          start=0, extent=180, style="arc", width=3, outline="#c9a227")
            cv.create_rectangle(cx - s * .55, cy - s * .35, cx + s * .55, cy + s * .8,
                                fill="#d4af37", outline="#8a6d10")
        elif key == "pan":
            cv.create_line(cx - s * .8, cy - s * .8, cx, cy - s * .1, fill="#999999")
            cv.create_line(cx + s * .8, cy - s * .8, cx, cy - s * .1, fill="#999999")
            cv.create_polygon(cx - s * .9, cy - s * .1, cx + s * .9, cy - s * .1,
                              cx + s * .6, cy + s * .7, cx - s * .6, cy + s * .7,
                              fill="#e9f2f6", outline="#8fa8b2")
        elif key == "cloth":
            cv.create_polygon(cx - s, cy + s * .5, cx - s * .6, cy - s * .6,
                              cx + s, cy - s * .4, cx + s * .5, cy + s * .6,
                              fill="#cfe0c8", outline="#7f9877")

    # ---------------- drag & drop ----------------
    def on_press(self, ev):
        for p, x0, y0, x1, y1 in self.tray_slots():
            if x0 <= ev.x <= x1 and y0 <= ev.y <= y1:
                if p["key"] in self.app.bench.installed:
                    self.msg.set(T("이미 설치되어 있습니다.", "Already installed."))
                    return
                self.drag = dict(part=p, x=ev.x, y=ev.y)
                self.redraw()
                self.draw_zones()
                return

    def on_move(self, ev):
        if self.drag is None:
            return
        self.drag["x"], self.drag["y"] = ev.x, ev.y
        self.cv.delete("ghost")
        self.draw_ghost()

    def draw_ghost(self):
        d = self.drag
        self.cv.create_oval(d["x"] - 20, d["y"] - 20, d["x"] + 20, d["y"] + 20,
                            fill="#ffffff", outline="#2f6fb0", width=2, tags=("ghost",))
        self.part_icon(self.cv, d["part"]["key"], d["x"], d["y"], 1.0)
        self.cv.itemconfig("ghost", tags=("ghost",))

    def on_release(self, ev):
        if self.drag is None:
            return
        part = self.drag["part"]
        self.drag = None
        zone = None
        best = None
        for key, (x0, y0, x1, y1) in zones_for(ASM_OX, ASM_OY, ASM_S).items():
            if x0 <= ev.x <= x1 and y0 <= ev.y <= y1:
                d = (ev.x - 0.5 * (x0 + x1)) ** 2 + (ev.y - 0.5 * (y0 + y1)) ** 2
                if best is None or d < best:
                    best, zone = d, key
        self.redraw()
        if zone is None:
            self.msg.set(T("놓을 위치가 아닙니다.", "Not a valid place to put that."))
            return
        if zone != part["zone"]:
            self.msg.set(T("%s 는 그 위치에 설치할 수 없습니다.",
                           "%s cannot be installed there.") % part["name"])
            return
        ok, why = self.app.install(part["key"])
        self.redraw()
        if not ok:
            self.msg.set(why)
        else:
            self.msg.set(T("%s 설치 완료.", "%s installed.") % part["name"])

    def on_right(self, ev):
        hit, best = None, None
        for key, (x0, y0, x1, y1) in zones_for(ASM_OX, ASM_OY, ASM_S).items():
            if x0 <= ev.x <= x1 and y0 <= ev.y <= y1:
                d = (ev.x - 0.5 * (x0 + x1)) ** 2 + (ev.y - 0.5 * (y0 + y1)) ** 2
                if best is None or d < best:
                    best, hit = d, key
        if hit is None:
            return
        b = self.app.bench
        cands = [p["key"] for p in self.parts
                 if p["zone"] == hit and p["key"] in b.installed]
        if not cands:
            return
        ok, why = self.app.remove(cands[-1])
        self.redraw()
        self.msg.set(why)


# ============================================================================
#  apparatus rendering (shared by both tabs)
# ============================================================================
def _pipe_pts(axis, fixed, t0, t1, zz):
    if axis == "y":
        return (fixed, t0, zz), (fixed, t1, zz)
    return (t0, fixed, zz), (t1, fixed, zz)


def draw_apparatus(cv, model, b, ox, oy, s=1.0):
    """Isometric rendering with a painter's-algorithm depth sort on y."""
    P = lambda x, y, z: proj(x, y, z, ox, oy, s)
    have = b.installed
    items = []                                    # (depth, callable)

    def add(depth, fn):
        items.append((depth, fn))

    # ---------------- table top (always) ----------------
    quad(cv, P(-230, -262, -96), P(400, -262, -96), P(400, 372, -96),
         P(-230, 372, -96), "#e3d9c3", "#c2b598")

    if "platform" not in have:
        px, py = P(120, 40, 40)
        cv.create_text(px, py, text=T("조립대를 작업대 위에 놓으세요",
                                      "Put the pipe assembly on the work table"),
                       fill="#9a9a9a", font=("TkDefaultFont", 11))
        return

    # ---------------- legs, then platform slab ----------------
    for lx, ly in ((26, 26), (274, 26), (26, 274), (274, 274)):
        cylinder(cv, P(lx, ly, -92), P(lx, ly, -14), 11 * s, base="#f2f2f0")
    quad(cv, P(0, 0, -16), P(PLAT, 0, -16), P(PLAT, 0, 0), P(0, 0, 0),
         "#a87f4c", "#7d5c33")
    quad(cv, P(PLAT, 0, -16), P(PLAT, PLAT, -16), P(PLAT, PLAT, 0), P(PLAT, 0, 0),
         "#96703f", "#7d5c33")
    quad(cv, P(0, 0, 0), P(PLAT, 0, 0), P(PLAT, PLAT, 0), P(0, PLAT, 0),
         "#c79a63", "#8a6636")
    for i in range(1, 7):                                  # wood grain
        cv.create_line(P(0, i * 42, 0)[0], P(0, i * 42, 0)[1],
                       P(PLAT, i * 42, 0)[0], P(PLAT, i * 42, 0)[1],
                       fill="#bd8f57")

    # ---------------- central vertical post ----------------
    def post():
        cylinder(cv, P(150, 150, 0), P(150, 150, 212), POST_R * s,
                 base="#c6cbd3", cap=False)
        q = P(150, 150, 212)
        ellipse_cap(cv, q, (0, -1), POST_R * s, "#dfe3e9", "#8e949c", squash=0.55)
        ellipse_cap(cv, q, (0, -1), POST_R * 0.6 * s, "#9aa0a8", "#7d838b",
                    squash=0.55)
    add(150.5, post)

    # ---------------- four horizontal pipes (segmented for depth sort) -------
    for kind, axis, fixed, t0, t1, zz in PIPES:
        n = 18
        for i in range(n):
            u0 = t0 + (t1 - t0) * i / n
            u1 = t0 + (t1 - t0) * (i + 1) / n
            p0, p1 = _pipe_pts(axis, fixed, u0, u1, zz)
            add(0.5 * (p0[1] + p1[1]) + 0.02 * zz,
                lambda p0=p0, p1=p1: cylinder(cv, P(*p0), P(*p1), PIPE_R * s,
                                              base="#b9bec6", cap=False))
        for end, other in ((t0, t1), (t1, t0)):
            pe, po = _pipe_pts(axis, fixed, end, other, zz)
            def capfn(pe=pe, po=po):
                q, r = P(*pe), P(*po)
                ellipse_cap(cv, q, (q[0] - r[0], q[1] - r[1]), PIPE_R * s,
                            "#d6dae0", "#7d838b")
                ellipse_cap(cv, q, (q[0] - r[0], q[1] - r[1]), PIPE_R * 0.6 * s,
                            "#8b9199", "#6d727a")
            add(pe[1] - 0.3 + 0.02 * zz, capfn)

    # ---------------- stubs carrying the pipes ----------------
    for x, y, zz in STUBS:
        add(y - 0.6, lambda x=x, y=y, zz=zz: cylinder(
            cv, P(x, y, 0), P(x, y, zz - PIPE_R * 0.5), 7 * s, base="#a9aeb5"))

    # ---------------- ruled acrylic plate, in front of the left pipe ---------
    if "acrylic" in have:
        def plate():
            a = P(26, -76, 38)
            bb = P(114, -76, 38)
            c = P(114, -76, 146)
            d = P(26, -76, 146)
            cv.create_polygon([a[0], a[1], bb[0], bb[1], c[0], c[1], d[0], d[1]],
                              fill="#cfe8f0", outline="#5f8b99", stipple="gray50")
            n = 26
            for i in range(n + 1):
                t = i / float(n)
                p = (a[0] + (d[0] - a[0]) * t, a[1] + (d[1] - a[1]) * t)
                cv.create_line(p[0], p[1], p[0] + (bb[0] - a[0]), p[1] + (bb[1] - a[1]),
                               fill="#6f9dab")
            tx, ty = P(70, -76, 158)
            cv.create_text(tx, ty, text=T("1.5 mm 간격", "1.5 mm apart"),
                           font=("TkDefaultFont", 7), fill="#4b7280")
        add(-76.0, plate)

    # ---------------- magnifying glass with torch ----------------
    if "magnifier" in have:
        def mag():
            cx, cy = P(-70, -206, 66)
            r = 30 * s
            cv.create_line(cx + r * 0.6, cy + r * 0.6, cx + r * 1.5, cy + r * 1.7,
                           width=6, fill="#d6d6d6")
            cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#eef7fb",
                           outline="#8b8b8b", width=3)
            cv.create_arc(cx - r * 0.78, cy - r * 0.78, cx + r * 0.78, cy + r * 0.78,
                          start=40, extent=70, style="arc", outline="#ffffff", width=3)
            cv.create_rectangle(cx + r * 0.95, cy + r * 1.05, cx + r * 1.3,
                                cy + r * 1.45, fill="#2f6fb0", outline="#1d4a7a")
        add(-212.0, mag)

    # ---------------- weight box and cloth on the table ----------------
    if "weightbox" in have:
        def wbox():
            a = P(-190, -238, -96)
            quad(cv, a, (a[0] + 150 * s, a[1]), (a[0] + 178 * s, a[1] - 40 * s),
                 (a[0] + 28 * s, a[1] - 40 * s), "#e8e2d4", "#8d8878")
            for i in range(6):
                cv.create_oval(a[0] + (16 + i * 22) * s, a[1] - 31 * s,
                               a[0] + (34 + i * 22) * s, a[1] - 17 * s,
                               fill="#c9a227", outline="#8a6d10")
            cv.create_text(a[0] + 80 * s, a[1] + 13 * s,
                           text=T("분동 상자", "weight box"),
                           font=("TkDefaultFont", 8), fill="#5f5a4c")
        add(-238.0, wbox)
    if "cloth" in have:
        def cloth():
            a = P(300, -238, -96)
            cv.create_polygon(a[0], a[1], a[0] + 44 * s, a[1] - 18 * s,
                              a[0] + 82 * s, a[1] + 2 * s, a[0] + 38 * s, a[1] + 20 * s,
                              fill="#cfe0c8", outline="#7f9877")
        add(-239.0, cloth)

    # ---------------- the cord ----------------
    if b.cord is not None:
        ccol = "#f6f6f4" if b.cord == "dial" else "#f08bb4"
        cout = "#9aa0a6" if b.cord == "dial" else "#c25d8c"
        pts = [(X_LOAD, Y_CORD, 30.0), (X_LOAD, Y_CORD, Z_CORD),
               (90.0, Y_CORD, Z_CORD)]
        if b.wraps == 0:
            pts.append((210.0, Y_CORD, Z_CORD))
        else:
            n = b.wraps
            steps = max(10, n * 5)
            z0, z1 = 152.0, 152.0 + min(48.0, 4.0 * n)
            pts.append((108.0, 118.0, 152.0))
            for i in range(steps + 1):
                t = i / float(steps)
                ang = math.pi * 1.05 - t * (n * math.pi / 2.0)
                pts.append((150 + (POST_R + 3) * math.cos(ang),
                            150 + (POST_R + 3) * math.sin(ang),
                            z0 + (z1 - z0) * t))
            pts.append((194.0, 118.0, 152.0))
        pts += [(210.0, Y_CORD, Z_CORD), (X_EFF, Y_CORD, Z_CORD),
                (X_EFF, Y_CORD, 44.0)]

        for i in range(len(pts) - 1):
            p0, p1 = pts[i], pts[i + 1]
            depth = 0.5 * (p0[1] + p1[1]) - 0.6
            def seg(p0=p0, p1=p1):
                q0, q1 = P(*p0), P(*p1)
                cv.create_line(q0[0], q0[1], q1[0], q1[1], width=5 * s,
                               fill=cout, capstyle="round")
                cv.create_line(q0[0], q0[1], q1[0], q1[1], width=3 * s,
                               fill=ccol, capstyle="round")
                if b.cord == "dial":
                    L = math.hypot(q1[0] - q0[0], q1[1] - q0[1])
                    k = int(L // (20 * s))
                    for j in range(k):
                        t = (j + 0.5) / max(k, 1)
                        cv.create_line(q0[0] + (q1[0] - q0[0]) * t,
                                       q0[1] + (q1[1] - q0[1]) * t,
                                       q0[0] + (q1[0] - q0[0]) * (t + 0.05),
                                       q0[1] + (q1[1] - q0[1]) * (t + 0.05),
                                       width=4 * s, fill="#3f6fd0")
            add(depth, seg)

        # ---------------- load ----------------
        if b.load == "hanger":
            def hanger():
                x, y = P(X_LOAD, Y_CORD, 30.0)
                cv.create_arc(x - 9 * s, y - 18 * s, x + 9 * s, y - 2 * s,
                              start=0, extent=180, style="arc", width=3,
                              outline="#c9a227")
                for i in range(b.slots):
                    yy = y + i * 10 * s
                    cv.create_oval(x - 23 * s, yy - 6 * s, x + 23 * s, yy + 7 * s,
                                   fill="#d4af37", outline="#8a6d10")
                cv.create_text(x, y + (b.slots * 10 + 17) * s,
                               text="%d x 100.0 g" % b.slots,
                               font=("TkDefaultFont", 8), fill="#5b4a10")
            add(Y_CORD - 1.0, hanger)
        elif b.load == "unknown":
            def unk():
                x, y = P(X_LOAD, Y_CORD, 30.0)
                cv.create_arc(x - 8 * s, y - 18 * s, x + 8 * s, y - 2 * s,
                              start=0, extent=180, style="arc", width=3,
                              outline="#c9a227")
                cv.create_polygon(x - 16 * s, y, x + 16 * s, y, x + 13 * s,
                                  y + 42 * s, x - 13 * s, y + 42 * s,
                                  fill="#d4af37", outline="#8a6d10")
                cv.create_oval(x - 16 * s, y - 5 * s, x + 16 * s, y + 6 * s,
                               fill="#e2c356", outline="#8a6d10")
                cv.create_text(x, y + 56 * s, text=T("M_u", "M_u"),
                               font=("TkDefaultFont", 8, "bold"), fill="#5b4a10")
            add(Y_CORD - 1.0, unk)

        # ---------------- pan ----------------
        if "pan" in b.installed:
            def pan():
                x, y = P(X_EFF, Y_CORD, 44.0)
                cv.create_line(x, y - 4 * s, x - 26 * s, y + 26 * s, fill="#9aa0a6")
                cv.create_line(x, y - 4 * s, x + 26 * s, y + 26 * s, fill="#9aa0a6")
                k = sum(1 for on in b.pan if on)
                for i in range(k):
                    cv.create_oval(x - 20 * s + (i % 4) * 10 * s,
                                   y + 14 * s - (i // 4) * 7 * s,
                                   x - 9 * s + (i % 4) * 10 * s,
                                   y + 23 * s - (i // 4) * 7 * s,
                                   fill="#c9a227", outline="#8a6d10")
                cv.create_polygon(x - 32 * s, y + 26 * s, x + 32 * s, y + 26 * s,
                                  x + 24 * s, y + 56 * s, x - 24 * s, y + 56 * s,
                                  fill="#e9f2f6", outline="#8fa8b2")
                cv.create_oval(x - 32 * s, y + 20 * s, x + 32 * s, y + 32 * s,
                               fill="#dcebf1", outline="#8fa8b2")
                cv.create_text(x, y + 44 * s, text="M_pan = %.1f g" % model.M_pan,
                               font=("TkDefaultFont", 7), fill="#37505a")
            add(Y_CORD - 2.0, pan)

    items.sort(key=lambda e: -e[0])
    for _, fn in items:
        fn()


# ============================================================================
#  bench tab
# ============================================================================
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.anim = None
        self.phase = 0.0
        self.running = False

        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=(8, 4), pady=8)
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)

        # ---------------- controls ----------------
        self.status = tk.StringVar()
        ttk.Label(left, textvariable=self.status, foreground="#8a2b12",
                  wraplength=300, justify="left").pack(anchor="w", pady=(0, 6))

        f0 = ttk.LabelFrame(left, text=T("장치", "Apparatus"))
        f0.pack(fill="x", pady=3)
        self.lab_setup = tk.StringVar()
        ttk.Label(f0, textvariable=self.lab_setup, justify="left",
                  wraplength=300).pack(anchor="w", padx=6, pady=4)

        f1 = ttk.LabelFrame(left, text=T("하중 (슬롯 추 걸이)", "Load (slotted hanger)"))
        f1.pack(fill="x", pady=3)
        row = ttk.Frame(f1)
        row.pack(padx=6, pady=4)
        ttk.Button(row, text="-100 g", width=8,
                   command=lambda: self.slot(-1)).pack(side="left")
        self.lab_load = tk.StringVar()
        ttk.Label(row, textvariable=self.lab_load, width=16,
                  anchor="center").pack(side="left")
        ttk.Button(row, text="+100 g", width=8,
                   command=lambda: self.slot(+1)).pack(side="left")

        f2 = ttk.LabelFrame(left, text=T("중앙 기둥에 코드 감기",
                                         "Winding the cord round the post"))
        f2.pack(fill="x", pady=3)
        row = ttk.Frame(f2)
        row.pack(padx=6, pady=4)
        ttk.Button(row, text=T("풀기 1/4바퀴", "unwind 1/4 turn"), width=14,
                   command=lambda: self.wrap(-1)).pack(side="left")
        self.lab_wrap = tk.StringVar()
        ttk.Label(row, textvariable=self.lab_wrap, width=13,
                  anchor="center").pack(side="left")
        ttk.Button(row, text=T("감기 1/4바퀴", "wind 1/4 turn"), width=14,
                   command=lambda: self.wrap(+1)).pack(side="left")

        f3 = ttk.LabelFrame(left, text=T("분동 상자 -> 접시", "Weight box -> pan"))
        f3.pack(fill="x", pady=3)
        grid = ttk.Frame(f3)
        grid.pack(padx=6, pady=4)
        self.wbtn = []
        for i, w in enumerate(WEIGHT_SET):
            v = tk.IntVar(value=0)
            cb = ttk.Checkbutton(grid, text="%.0f g" % w, variable=v,
                                 command=lambda i=i: self.toggle(i))
            cb.grid(row=i // 3, column=i % 3, sticky="w", padx=2, pady=1)
            self.wbtn.append(v)
        self.lab_pan = tk.StringVar()
        ttk.Label(f3, textvariable=self.lab_pan,
                  font=("TkDefaultFont", 10, "bold")).pack(anchor="w", padx=6, pady=(0, 4))
        ttk.Button(f3, text=T("접시 비우기", "empty the pan"),
                   command=self.clear_pan).pack(anchor="w", padx=6, pady=(0, 5))

        f4 = ttk.LabelFrame(left, text=T("관찰", "Observation"))
        f4.pack(fill="x", pady=3)
        self.obs = tk.Canvas(f4, width=300, height=170, bg="#20262b",
                             highlightthickness=0)
        self.obs.pack(padx=6, pady=5)
        row = ttk.Frame(f4)
        row.pack(pady=(0, 6))
        ttk.Button(row, text=T("놓고 관찰", "release & watch"),
                   command=self.start_obs).pack(side="left", padx=3)
        ttk.Button(row, text=T("정지", "stop"),
                   command=self.stop_obs).pack(side="left", padx=3)

        f5 = ttk.Frame(left)
        f5.pack(fill="x", pady=4)
        ttk.Button(f5, text=T("파이프 표면 만지기", "touch the pipe surface"),
                   command=self.touch).pack(side="left", padx=2)
        ttk.Button(f5, text=T("천으로 닦기", "wipe with cloth"),
                   command=self.wipe).pack(side="left", padx=2)

        # ---------------- apparatus view ----------------
        self.cv = tk.Canvas(right, width=820, height=640, bg="#f2efe6",
                            highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.refresh()

    # ------------- actions -------------
    def slot(self, d):
        b = self.app.bench
        if b.load != "hanger":
            self.status.set(T("슬롯 추 걸이가 하중으로 걸려 있지 않습니다.",
                              "The slotted hanger is not hung as the load."))
            return
        b.slots = max(1, min(N_SLOTS, b.slots + d))
        self.stop_obs()
        self.refresh()

    def wrap(self, d):
        b = self.app.bench
        if b.cord is None:
            self.status.set(T("먼저 코드를 걸어야 합니다.", "Install a cord first."))
            return
        b.wraps = max(0, min(MAX_WRAPS, b.wraps + d))
        self.stop_obs()
        self.refresh()

    def toggle(self, i):
        b = self.app.bench
        if "weightbox" not in b.installed or "pan" not in b.installed:
            self.wbtn[i].set(0)
            self.status.set(T("분동 상자와 접시가 필요합니다.",
                              "You need the weight box and the pan."))
            return
        b.pan[i] = bool(self.wbtn[i].get())
        self.stop_obs()
        self.refresh()

    def clear_pan(self):
        for v in self.wbtn:
            v.set(0)
        self.app.bench.pan = [False] * len(WEIGHT_SET)
        self.stop_obs()
        self.refresh()

    def touch(self):
        self.app.model.grease = min(0.10, self.app.model.grease + 0.05)
        self.app.model._offsets.clear()
        self.status.set(T("파이프 표면을 손으로 만졌습니다.",
                          "You touched the pipe surface with your fingers."))
        self.stop_obs()
        self.refresh()

    def wipe(self):
        if "cloth" not in self.app.bench.installed:
            self.status.set(T("청소용 천이 작업대에 없습니다.",
                              "The cleaning cloth is not on the table."))
            return
        self.app.model.grease = 0.0
        self.app.model._offsets.clear()
        self.status.set(T("파이프와 코드를 닦았습니다.",
                          "Pipes and cord wiped clean."))
        self.stop_obs()
        self.refresh()

    # ------------- observation animation -------------
    def start_obs(self):
        b = self.app.bench
        if not b.ready():
            self.status.set(T("장치가 완전히 조립되지 않았습니다. 조립 탭을 확인하세요.",
                              "The set-up is incomplete -- check the Assembly tab."))
            return
        if not b.can_see():
            self.status.set(T("아크릴 눈금판이 없으면 코드의 움직임을 판단할 수 없습니다.",
                              "Without the ruled acrylic plate the motion of the "
                              "cord cannot be judged."))
            return
        self.stop_obs()
        self.running = True
        self.phase = 0.0
        self.t = 0
        self._tick()

    def stop_obs(self):
        self.running = False
        if self.anim is not None:
            try:
                self.after_cancel(self.anim)
            except Exception:
                pass
            self.anim = None

    def _tick(self):
        if not self.running:
            return
        b, m = self.app.bench, self.app.model
        v = m.slip_rate(b.cord, b.M_w(m), b.M_p(m), b.theta(), b.magnified())
        self.phase += v * 0.06
        self.t += 1
        self.draw_obs()
        if self.t > 380:
            self.running = False
            return
        self.anim = self.after(40, self._tick)

    def draw_obs(self):
        cv = self.obs
        b, m = self.app.bench, self.app.model
        cv.delete("all")
        W, H = 300, 170
        if not b.can_see() or b.cord is None:
            cv.create_text(W / 2, H / 2, fill="#8a949c",
                           text=T("관찰할 수 없음", "nothing to observe"))
            return
        mag = b.magnified()
        # ruled acrylic plate (lines 1.5 mm apart)
        pitch = 26.0 if mag else 7.0
        cv.create_rectangle(8, 8, W - 8, H - 8, fill="#0f2a33", outline="#3d6b78")
        n = int((H - 16) / pitch) + 2
        for i in range(n):
            y = 8 + i * pitch
            cv.create_line(10, y, W - 10, y, fill="#69a7b8" if mag else "#3f6d7a")
        if mag:
            cv.create_text(W - 44, 20, text=T("확대경", "magnified"),
                           fill="#8fd0e0", font=("TkDefaultFont", 7))
            cv.create_oval(2, 2, W - 2, H - 2, outline="#dddddd", width=3)
        else:
            cv.create_text(W - 52, 20, text=T("맨눈", "naked eye"),
                           fill="#7f9aa4", font=("TkDefaultFont", 7))
        # the cord in front of the plate
        cw = 16 if mag else 7
        x0 = W / 2 - cw / 2
        col = "#f4f4f2" if b.cord == "dial" else "#f08bb4"
        cv.create_rectangle(x0, 8, x0 + cw, H - 8, fill=col, outline="")
        if b.cord == "dial":
            markpitch = 62.0 if mag else 19.0
            off = (self.phase * (2.4 if mag else 0.8)) % markpitch
            k = int((H - 16) / markpitch) + 3
            for i in range(-1, k):
                y = 8 + off + i * markpitch
                if 8 < y < H - 8:
                    cv.create_rectangle(x0, y, x0 + cw, min(H - 8, y + (13 if mag else 5)),
                                        fill="#3f6fd0", outline="")
        else:
            markpitch = 48.0 if mag else 15.0
            off = (self.phase * (2.4 if mag else 0.8)) % markpitch
            k = int((H - 16) / markpitch) + 3
            for i in range(-1, k):
                y = 8 + off + i * markpitch
                if 8 < y < H - 8:
                    cv.create_rectangle(x0 + 2, y, x0 + cw - 2,
                                        min(H - 8, y + (7 if mag else 3)),
                                        fill="#c25d8c", outline="")

    # ------------- refresh -------------
    def refresh(self):
        b, m = self.app.bench, self.app.model
        cordname = {None: T("없음", "none"),
                    "dial": T("다이얼 코드", "dial cord"),
                    "pink": T("핑크 코드", "pink cord")}[b.cord]
        loadname = {None: T("없음", "none"),
                    "hanger": T("슬롯 추 걸이", "slotted hanger"),
                    "unknown": T("미지 질량 M_u", "unknown mass M_u")}[b.load]
        txt = [T("코드: ", "cord: ") + cordname,
               T("하중: ", "load: ") + loadname,
               T("접시: ", "pan: ") + (T("설치", "installed") if "pan" in b.installed
                                       else T("없음", "none")),
               T("눈금판: ", "ruled plate: ") + (T("설치", "installed") if b.can_see()
                                                 else T("없음", "none")),
               T("확대경: ", "magnifier: ") + (T("설치", "installed") if b.magnified()
                                               else T("없음", "none"))]
        self.lab_setup.set("\n".join(txt))
        if b.load == "hanger":
            self.lab_load.set("%.1f g" % (b.slots * SLOT_MASS))
        elif b.load == "unknown":
            self.lab_load.set(T("미지", "unknown"))
        else:
            self.lab_load.set("-")
        self.lab_wrap.set(T("%d/4 바퀴", "%d/4 turn") % b.wraps)
        on = [WEIGHT_SET[i] for i, v in enumerate(b.pan) if v]
        self.lab_pan.set(T("접시에 올린 분동: ", "weights in the pan: ") +
                         (" + ".join("%g g" % w for w in on) if on else T("없음", "none")))
        self.cv.delete("all")
        draw_apparatus(self.cv, m, b, ox=BEN_OX, oy=BEN_OY, s=BEN_S)
        if not b.ready():
            self.cv.create_text(410, 24, fill="#8a2b12",
                                font=("TkDefaultFont", 10, "bold"),
                                text=T("조립 탭에서 장치를 완성하세요.",
                                       "Complete the set-up in the Assembly tab."))
        self.draw_obs()


# ============================================================================
#  application
# ============================================================================
class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.title(T("APhO 2012 실험 1 - 마찰 (HaslaLab)",
                     "APhO 2012 Experiment 1 - Friction (HaslaLab)"))
        self.model = Model(seed)
        self.bench = Bench()
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.tab_asm = AssemblyTab(self.nb, self)
        self.tab_bench = BenchTab(self.nb, self)
        self.nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        self.nb.add(self.tab_bench, text=T(" 실험대 ", " Bench "))
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.sync())
        bar = ttk.Frame(self)
        bar.pack(fill="x")
        ttk.Label(bar, text="APhO 2012 - Q1 FRICTION      seed = %d" % self.model.seed,
                  font=("TkDefaultFont", 8), foreground="#777777").pack(side="right",
                                                                       padx=8, pady=2)

    def sync(self):
        self.tab_asm.redraw()
        self.tab_bench.refresh()

    # ---- installation rules -------------------------------------------------
    def install(self, key):
        b = self.bench
        if key in b.installed:
            return False, T("이미 설치되어 있습니다.", "Already installed.")
        if key in ("acrylic", "magnifier") and "platform" not in b.installed:
            return False, T("먼저 조립대를 놓으세요.", "Put the pipe assembly down first.")
        if key in ("cord_dial", "cord_pink"):
            if "platform" not in b.installed:
                return False, T("먼저 조립대를 놓으세요.",
                                "Put the pipe assembly down first.")
            other = "cord_pink" if key == "cord_dial" else "cord_dial"
            if other in b.installed:
                return False, T("다른 코드가 이미 걸려 있습니다. 먼저 제거하세요.",
                                "The other cord is already in place -- remove it first.")
            b.installed.add(key)
            b.cord = "dial" if key == "cord_dial" else "pink"
            b.wraps = 0
            return True, ""
        if key in ("hanger", "unknown"):
            if b.cord is None:
                return False, T("먼저 코드를 파이프 위로 걸치세요.",
                                "Pass a cord over the pipes first.")
            other = "unknown" if key == "hanger" else "hanger"
            if other in b.installed:
                return False, T("하중이 이미 매달려 있습니다. 먼저 제거하세요.",
                                "A load is already hanging -- remove it first.")
            b.installed.add(key)
            b.load = "hanger" if key == "hanger" else "unknown"
            b.slots = N_SLOTS
            return True, ""
        if key == "pan":
            if b.cord is None:
                return False, T("먼저 코드를 파이프 위로 걸치세요.",
                                "Pass a cord over the pipes first.")
        b.installed.add(key)
        return True, ""

    def remove(self, key):
        b = self.bench
        if key not in b.installed:
            return False, ""
        if key == "platform":
            b.installed.clear()
            b.cord = None
            b.load = None
            b.pan = [False] * len(WEIGHT_SET)
            b.wraps = 0
            for v in self.tab_bench.wbtn:
                v.set(0)
            return True, T("조립대를 치웠습니다 (모든 부품 해체).",
                           "Assembly removed (everything dismantled).")
        if key in ("cord_dial", "cord_pink"):
            if b.load is not None or "pan" in b.installed:
                return False, T("하중과 접시를 먼저 떼어내세요.",
                                "Detach the load and the pan first.")
            b.installed.discard(key)
            b.cord = None
            b.wraps = 0
            return True, T("코드를 걷었습니다.", "Cord removed.")
        b.installed.discard(key)
        if key in ("hanger", "unknown"):
            b.load = None
        return True, T("부품을 제거했습니다.", "Part removed.")


def main():
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
    app = App(seed)
    app.mainloop()


if __name__ == "__main__":
    main()
