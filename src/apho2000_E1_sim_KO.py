#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  1st Asian Physics Olympiad  (APhO 2000, Karawaci, Indonesia)
  Experimental Problem 1 :  DETERMINATION OF THE DENSITY OF OIL
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* A round-bottomed glass test tube floats upright in a vessel of water.
  Water (or oil) is added with an eye dropper; the tube sinks deeper so
  that l_z = C + D l_c, with D = rho_c S_c / (rho_w S_z).  The rubber band
  marks the reference point A.  Too little liquid and the tube leans;
  too much and water comes over the rim and it sinks.
* Water and oil do not mix: both in the tube at once spoils the reading;
  an emptied tube keeps a film until dried with tissue.
* The student reads the band, the liquid surface inside and the water
  surface outside on a ruler (a magnifier helps); the tube's dimensions,
  its mass and the oil density are hidden.
* Hidden truths are randomised every session.
* Standard library only (tkinter).

    Run:   python3 apho2000_E1_sim_KO.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line


def hemi(r):
    return 2.0 / 3.0 * math.pi * r ** 3


def vol_to(r, h):
    """volume of a round-bottomed tube of radius r filled to height h above its lowest point"""
    if h <= 0:
        return 0.0
    if h <= r:
        return math.pi * h * h * (r - h / 3.0)
    return hemi(r) + math.pi * r * r * (h - r)


def h_of(r, V):
    if V <= 0:
        return 0.0
    if V >= hemi(r):
        return r + (V - hemi(r)) / (math.pi * r * r)
    a, b = 0.0, r
    for _ in range(40):
        m = (a + b) / 2
        if vol_to(r, m) < V:
            a = m
        else:
            b = m
    return (a + b) / 2


# --------------------------------------------------------------------------
#  Physics core  (g, cm)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.rho = r.uniform(0.80, 0.90)          # the oil: the hidden answer
        self.ri = r.uniform(0.70, 0.78)           # bore radius
        self.wall = r.uniform(0.065, 0.090)
        self.Lt = 15.0 * r.uniform(0.99, 1.01)
        self.rhoG, self.rhoW = 2.45, 0.9975
        self.Rv, self.Hv = 4.0, 21.0
        self.Vv = r.uniform(830, 870)             # water in the vessel
        self.ro = self.ri + self.wall
        self.M = self.rhoG * ((hemi(self.ro) - hemi(self.ri)) + math.pi * (self.ro ** 2 - self.ri ** 2) * (self.Lt - self.ro))
        self.Vw, self.Vo = 0.0, 0.0               # water and oil in the tube
        self.sunk = False

    def vin(self):
        return vol_to(self.ri, self.Lt - self.wall)

    def mass(self):
        return self.M + self.rhoW * self.Vw + self.rho * self.Vo

    def state(self, floating):
        """levels in the vessel's frame (z = 0 on its floor)"""
        A = math.pi * self.Rv ** 2
        if not floating:
            return {"Dv": self.Vv / A, "zb": None}
        if self.sunk:
            glass = vol_to(self.ro, self.Lt) - self.vin()
            return {"Dv": (self.Vv + glass) / A, "zb": 0.0, "sunk": True, "up": False}
        disp = self.mass() / self.rhoW
        h = h_of(self.ro, disp)
        Dv = (self.Vv + disp) / A
        zb = Dv - h
        up = self.rhoW * self.Vw + self.rho * self.Vo >= 2.2
        return {"Dv": Dv, "zb": zb, "zin": zb + self.wall + h_of(self.ri, self.Vw + self.Vo),
                "zww": zb + self.wall + h_of(self.ri, self.Vw), "up": up, "sunk": False}

    def check_sink(self):
        if self.sunk:
            return False
        if self.mass() / self.rhoW > vol_to(self.ro, self.Lt):
            room = self.vin() - self.Vw - self.Vo
            self.Vw += room
            self.Vv -= room
            self.sunk = True
            return True
        return False


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_vessel(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 34 * s, y - 60 * s, x + 34 * s, y + 60 * s, outline="#8fa7b4", width=2)
    cv.create_rectangle(x - 32 * s, y - 20 * s, x + 32 * s, y + 58 * s, fill="#a9cce3", outline="")


def art_tube(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 6 * s, y - 50 * s, x + 6 * s, y + 44 * s, outline="#8fa7b4", width=2)
    cv.create_oval(x - 6 * s, y + 38 * s, x + 6 * s, y + 50 * s, outline="#8fa7b4", width=2)


def art_rack(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 50 * s, y - 8 * s, x + 50 * s, y + 2 * s, fill="#caa06c", outline="#8a6a40")
    cv.create_rectangle(x - 50 * s, y + 22 * s, x + 50 * s, y + 30 * s, fill="#b98d5a", outline="#8a6a40")


def art_bottle(cv, x, y, sc=1.0, col="#a9cce3", cap="#2b6cb0"):
    s = sc
    cv.create_rectangle(x - 18 * s, y - 34 * s, x + 18 * s, y + 40 * s, fill="#eef3f6", outline="#8fa7b4")
    cv.create_rectangle(x - 16 * s, y - 6 * s, x + 16 * s, y + 38 * s, fill=col, outline="")
    cv.create_rectangle(x - 7 * s, y - 46 * s, x + 7 * s, y - 34 * s, fill=cap, outline="")


def art_water(cv, x, y, sc=1.0):
    art_bottle(cv, x, y, sc)


def art_oil(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 24 * s, y - 20 * s, x + 24 * s, y + 20 * s, fill="#f2f3f5", outline="#8fa7b4")
    cv.create_rectangle(x - 22 * s, y - 2 * s, x + 22 * s, y + 18 * s, fill="#d6b23c", outline="")


def art_dropper(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 40 * s, y - 3 * s, x + 14 * s, y + 3 * s, outline="#8fa7b4")
    cv.create_oval(x + 12 * s, y - 8 * s, x + 34 * s, y + 8 * s, fill="#c0392b", outline="")


def art_waste(cv, x, y, sc=1.0):
    art_bottle(cv, x, y, sc, col="#c9c49a", cap="#eef3f6")


def art_band(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 14 * s, y - 8 * s, x + 14 * s, y + 8 * s, outline="#c0392b", width=3)


def art_ruler(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 60 * s, y - 7 * s, x + 60 * s, y + 7 * s, fill="#e1edf2", outline="#8fa7b4")
    for i in range(13):
        cv.create_line(x - 58 * s + i * 9.6 * s, y - 7 * s, x - 58 * s + i * 9.6 * s, y - (1 if i % 5 else -1) * s, fill="#333")


def art_tissue(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 30 * s, y - 14 * s, x + 30 * s, y + 18 * s, fill="#7fb3d5", outline="#4f83a5")
    cv.create_rectangle(x - 10 * s, y - 24 * s, x + 10 * s, y - 12 * s, fill="#fbfbf8", outline="")


ART = {"vessel": art_vessel, "tube": art_tube, "rack": art_rack, "water": art_water, "oil": art_oil,
       "dropper": art_dropper, "waste": art_waste, "band": art_band, "ruler": art_ruler, "tissue": art_tissue}

PARTS = [
    ("vessel",  ("[2] 그릇 (물)", "[2] Vessel (water)"), []),
    ("rack",    ("시험관 꽂이", "Test-tube rack"), []),
    ("tube",    ("[1] 시험관", "[1] Test tube"), ["rack"]),
    ("band",    ("[7] 고무줄 (기준 표시)", "[7] Rubber band (level mark)"), ["tube"]),
    ("water",   ("[8] 증류수 (1.00 g/cm³)", "[8] Distilled water (1.00 g/cm³)"), []),
    ("oil",     ("[9] 기름 (플라스틱 컵)", "[9] Oil (plastic cup)"), []),
    ("dropper", ("[4] 스포이트", "[4] Eye dropper"), []),
    ("waste",   ("버림통", "Waste jar"), []),
    ("ruler",   ("[3] 자", "[3] Ruler"), []),
    ("tissue",  ("[6] 휴지", "[6] Drying cloth / tissue"), []),
]
ZONES = {
    "vessel":  (200, 320, 80, 130), "rack": (380, 400, 110, 50), "tube": (360, 330, 30, 110), "band": (360, 270, 40, 26),
    "water":   (520, 330, 50, 100), "oil": (600, 420, 60, 50), "dropper": (520, 200, 90, 30), "waste": (660, 330, 50, 100),
    "ruler":   (230, 450, 130, 20), "tissue": (660, 200, 70, 50),
}
SCENE_TITLE = ("실험대 — 물그릇, 시험관, 스포이트, 액체", "The bench — vessel, test tube, dropper, liquids")
APP_TITLE = ("APhO 2000 실험 1 — 기름의 밀도", "APhO 2000 Experiment 1 — Determination of the density of oil")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.where = tk.StringVar(value="rack")
        self.drop = [None, 0.0]                  # the dropper's liquid and volume
        self.band = 12.0                         # the band's height on the tube, from its bottom
        self.bob = 0.0
        self.rul = 0.0                           # the ruler's zero, cm above the vessel's floor
        self.mag = 10.0                          # the magnifier's centre height, cm
        self.t = 0.0
        self.build()
        self.refresh()

    def ok(self):
        return {"vessel", "tube", "dropper"} <= self.app.placed

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("시험관", "Test tube"))
        f.pack(fill="x", pady=2)
        ttk.Radiobutton(f, text=T("꽂이에 세우기", "Stand in the rack"), value="rack", variable=self.where, command=self.moved).pack(anchor="w")
        ttk.Radiobutton(f, text=T("물그릇에 띄우기", "Float in the vessel"), value="vessel", variable=self.where, command=self.moved).pack(anchor="w")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("버림통에 비우기", "Empty into the waste"), command=self.empty).pack(side="left", padx=2)
        ttk.Button(row, text=T("휴지로 말리기", "Dry with tissue"), command=self.dry).pack(side="left", padx=2)
        self.tube_lbl = ttk.Label(f, text="")
        self.tube_lbl.pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("스포이트 (한 번에 약 1 cm³)", "Eye dropper (about 1 cm³ a bulbful)"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("물 빨아올리기", "Draw water"), command=lambda: self.fill("water")).pack(side="left", padx=2)
        ttk.Button(row, text=T("기름 빨아올리기", "Draw oil"), command=lambda: self.fill("oil")).pack(side="left", padx=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("다 짜넣기", "Squeeze all"), command=lambda: self.squeeze(True)).pack(side="left", padx=2)
        ttk.Button(row, text=T("한 방울", "One drop"), command=lambda: self.squeeze(False)).pack(side="left", padx=2)
        ttk.Button(row, text=T("빨아내기", "Suck back"), command=self.suck).pack(side="left", padx=2)
        ttk.Button(row, text=T("버림통에", "To waste"), command=self.squirt).pack(side="left", padx=2)
        self.drop_lbl = ttk.Label(f, text="")
        self.drop_lbl.pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("고무줄 · 자 · 돋보기", "Band · ruler · magnifier"))
        f.pack(fill="x", pady=2)
        stepper(f, T("고무줄", "Band"), [("▲1cm", lambda: self.mv_band(1)), ("▲1mm", lambda: self.mv_band(0.1)), ("▼1mm", lambda: self.mv_band(-0.1)), ("▼1cm", lambda: self.mv_band(-1))])
        stepper(f, T("자", "Ruler"), [("▲1cm", lambda: self.mv_rul(1)), ("▲1mm", lambda: self.mv_rul(0.1)), ("▼1mm", lambda: self.mv_rul(-0.1)), ("▼1cm", lambda: self.mv_rul(-1))])
        ttk.Label(f, text=T("옆 그림을 클릭하면 그 높이를 돋보기로 봅니다.", "Click the side view to look at that height through the magnifier."), foreground="#555", wraplength=320).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("기록 (자에서 읽은 눈금, cm)", "Record (ruler readings, cm)"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.ents = []
        for lab in (T("고무줄", "band"), T("안쪽", "inside"), T("바깥", "outside")):
            ttk.Label(row, text=lab).pack(side="left")
            e = ttk.Entry(row, width=6)
            e.pack(side="left", padx=2)
            self.ents.append(e)
        ttk.Button(f, text=T("적기", "Record"), command=self.record).pack(fill="x")
        self.sheet = DataSheet(f, [("q", T("액체", "liquid"), 60), ("a", T("고무줄", "band"), 70), ("i", T("안쪽", "inside"), 70), ("o", T("바깥", "outside"), 70)], height=7)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=330)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        c1 = ttk.Frame(right)
        c1.pack(side="left")
        ttk.Label(c1, text=T("옆에서 본 물그릇", "The vessel from the side"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.side = tk.Canvas(c1, width=360, height=640, bg="#f4f2ec", highlightthickness=0)
        self.side.pack()
        self.side.bind("<Button-1>", self.pick_mag)
        c2 = ttk.Frame(right)
        c2.pack(side="left", padx=6)
        ttk.Label(c2, text=T("돋보기 (×6)", "Magnifier (×6)"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.magc = tk.Canvas(c2, width=430, height=640, bg="#f4f2ec", highlightthickness=0)
        self.magc.pack()

    # ---- the hands ------------------------------------------------------
    def floating(self):
        return self.where.get() == "vessel" and "vessel" in self.app.placed and "tube" in self.app.placed

    def moved(self):
        self.bob = 1.0
        if self.floating():
            self.ph.check_sink()

    def fill(self, liq):
        if "dropper" not in self.app.placed or ("water" if liq == "water" else "oil") not in self.app.placed:
            return
        if self.drop[1] > 0.01 and self.drop[0] != liq:
            self.warn.config(text=T("스포이트에 다른 액체가 남아 있습니다 — 버림통에 짜세요.", "Another liquid is left in the dropper: squirt it into the waste."))
            return
        self.drop = [liq, 1.0]

    def squeeze(self, all_):
        ph = self.ph
        if not self.ok() or self.drop[1] < 0.01 or ph.sunk:
            return
        v = self.drop[1] if all_ else min(self.drop[1], 0.05 * random.uniform(0.9, 1.1))
        if ph.Vw + ph.Vo + v > ph.vin() - 0.3:
            return
        if self.drop[0] == "water":
            ph.Vw += v
        else:
            ph.Vo += v
        self.drop[1] -= v
        if self.drop[1] < 0.01:
            self.drop = [None, 0.0]
        self.bob = 1.0
        if self.floating():
            ph.check_sink()

    def suck(self):
        ph = self.ph
        if not self.ok() or self.drop[1] > 0.01 or ph.sunk:
            return
        liq = "oil" if ph.Vo > 0.05 else "water"
        have = ph.Vo if liq == "oil" else ph.Vw
        if have < 0.05:
            return
        v = min(1.0, have)
        if liq == "oil":
            ph.Vo -= v
        else:
            ph.Vw -= v
        self.drop = [liq, v]
        self.bob = 1.0

    def squirt(self):
        self.drop = [None, 0.0]

    def empty(self):
        ph = self.ph
        ph.Vw = random.uniform(0.06, 0.12) if ph.Vw > 0.03 else ph.Vw
        ph.Vo = random.uniform(0.05, 0.09) if ph.Vo > 0.03 else ph.Vo
        ph.sunk = False
        self.where.set("rack")

    def dry(self):
        if "tissue" not in self.app.placed or self.ph.Vw + self.ph.Vo > 0.2:
            return
        self.ph.Vw = self.ph.Vo = 0.0

    def mv_band(self, d):
        self.band = max(2.0, min(self.ph.Lt - 0.5, round(self.band + d, 1)))

    def mv_rul(self, d):
        self.rul = round(self.rul + d, 1)

    def pick_mag(self, ev):
        self.mag = (600 - ev.y) / 26.0

    def record(self):
        ph = self.ph
        q = T("물", "water") if ph.Vw > 0.15 and ph.Vo < 0.15 else T("기름", "oil") if ph.Vo > 0.15 and ph.Vw < 0.15 else T("섞임", "mixed")
        self.sheet.add([q] + [e.get() or "?" for e in self.ents])

    # ---- loop -------------------------------------------------------------
    def tick(self, dt):
        self.t += dt
        self.bob = max(0.0, self.bob - dt * 1.5)
        self.refresh()

    def refresh(self):
        ph = self.ph
        self.tube_lbl.config(text=T("안: ", "inside: ") + (T("물+기름", "water+oil") if ph.Vw > 0.02 and ph.Vo > 0.02 else T("물", "water") if ph.Vw > 0.02 else T("기름", "oil") if ph.Vo > 0.02 else T("비었음", "empty"))
                             + (T(" · 가라앉음!", " · SUNK!") if ph.sunk else ""))
        self.drop_lbl.config(text=T("스포이트: ", "Dropper: ") + ((T("물", "water") if self.drop[0] == "water" else T("기름", "oil")) if self.drop[1] > 0.01 else T("비었음", "empty")))
        msgs = []
        if ph.Vw > 0.15 and ph.Vo > 0.15:
            msgs.append(T("시험관에 물과 기름이 함께 있습니다 — 비우고 말리시오.", "Water and oil together in the tube: empty and dry it."))
        st = ph.state(self.floating())
        if self.floating() and not st.get("up", True) and not ph.sunk:
            msgs.append(T("액체가 너무 적어 시험관이 기울어 떠 있습니다.", "Too little liquid: the tube floats leaning."))
        if ph.sunk:
            msgs.append(T("시험관이 가라앉았습니다 — 비우시오.", "The tube has sunk: empty it."))
        if self.bob > 0.2:
            msgs.append(T("시험관이 출렁입니다 — 기다리시오.", "The tube is bobbing: wait."))
        self.warn.config(text="\n".join(msgs))
        self.draw(self.side, 26.0, 600.0, 180.0, 0.0, False)
        self.draw(self.magc, 156.0, 320.0 + self.mag * 156.0, 215.0, 0.0, True)

    def draw(self, cv, z, Y0, X0, _, fine):
        """the vessel from the side at z px/cm, floor at y = Y0, axis at x = X0"""
        cv.delete("all")
        ph = self.ph
        X = lambda x: X0 + x * z
        Y = lambda h: Y0 - h * z
        if "vessel" not in self.app.placed:
            return
        st = ph.state(self.floating())
        R = ph.Rv
        wob = 0.05 * self.bob * math.sin(self.t * 9)
        cv.create_rectangle(X(-R), Y(st["Dv"]), X(R), Y(0), fill="#cfe0ec", outline="")
        cv.create_line(X(-R), Y(st["Dv"]), X(R), Y(st["Dv"]), fill="#285078", width=2 if fine else 1)
        if self.floating() and st["zb"] is not None:
            tilt = 0.0 if st.get("up") else (math.asin(min(0.95, (2 * R - 2 * ph.ro - 0.25) / ph.Lt)) if st.get("sunk") else 0.42)
            x0 = 0.0 if tilt == 0 else -R + ph.ro + (0.15 if st.get("sunk") else 0.6)
            zb = st["zb"] + (wob if tilt == 0 else 0.0)
            c, s = math.cos(tilt), math.sin(tilt)
            P = lambda u, v: [X(x0 + u * c + v * s), Y(zb + v * c - u * s)]
            hw, ht = h_of(ph.ri, ph.Vw), h_of(ph.ri, ph.Vw + ph.Vo)
            for lo, hi, col in ((0.0, hw, "#8ab4dc"), (hw, ht, "#d6b23c")):
                if hi - lo < 0.01:
                    continue
                pts = []
                xa = lambda yy: ph.ri if yy >= ph.ri else math.sqrt(max(0.0, ph.ri ** 2 - (ph.ri - yy) ** 2))
                for i in range(25):
                    yy = hi - (hi - lo) * i / 24.0
                    pts += P(-xa(yy), yy + ph.wall)
                for i in range(25):
                    yy = lo + (hi - lo) * i / 24.0
                    pts += P(xa(yy), yy + ph.wall)
                cv.create_polygon(pts, fill=col, outline="#555")
            out = []
            for i in range(17):
                q = math.pi + i / 16.0 * math.pi
                out += P(ph.ro * math.cos(q), ph.ro + ph.ro * math.sin(q))
            cv.create_line(P(-ph.ro, ph.Lt) + out + P(ph.ro, ph.Lt), fill="#5a6e78", width=2 if fine else 1)
            if "band" in self.app.placed:
                cv.create_polygon(P(-ph.ro - 0.05, self.band - 0.12) + P(ph.ro + 0.05, self.band - 0.12) + P(ph.ro + 0.05, self.band + 0.12) + P(-ph.ro - 0.05, self.band + 0.12), fill="#c0392b", outline="")
        cv.create_rectangle(X(-R - 0.25), Y(ph.Hv), X(-R), Y(-0.5), fill="#c8d8e0", outline="#6e8c9b")
        cv.create_rectangle(X(R), Y(ph.Hv), X(R + 0.25), Y(-0.5), fill="#c8d8e0", outline="#6e8c9b")
        cv.create_rectangle(X(-R - 0.25), Y(0), X(R + 0.25), Y(-0.5), fill="#c8d8e0", outline="#6e8c9b")
        if "ruler" in self.app.placed:
            xr = X(ph.ro + 0.12) if fine else X(R + 0.4)    # in the magnifier the ruler is held right against the tube
            cv.create_rectangle(xr, Y(self.rul - 0.5), xr + 3.2 * z, Y(self.rul + 30.5), fill="#e1edf2", outline="#8fa7b4")
            for mm in range(0, 301):
                yy = Y(self.rul + mm / 10.0)
                if yy < -5 or yy > 645:
                    continue
                if not fine and mm % 5:
                    continue
                ln = (0.9 if mm % 10 == 0 else 0.6 if mm % 5 == 0 else 0.35) * (26.0 if fine else z)
                cv.create_line(xr, yy, xr + ln, yy, fill="#222")
                if mm % 10 == 0:
                    cv.create_text(xr + ln + 10, yy, text=str(mm // 10), font=("Helvetica", 10 if fine else 7))
        if not fine:
            cv.create_rectangle(0, Y(self.mag + 2.05), 360, Y(self.mag - 2.05), outline="#f2c14e", width=2)


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
