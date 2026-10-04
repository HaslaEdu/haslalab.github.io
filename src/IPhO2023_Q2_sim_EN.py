#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPhO 2023 (Tokyo) Q2 - Thickness Measurements Using Birefringence
=================================================================
Single file, standard library only (tkinter).

    Tab 1  Bench (side view)  - the parts of Figs. 4 and 5 lie in the tray.
                                Put them wherever you want.  Nothing is
                                enforced, nothing is suggested: if the
                                LED, the slit, L1, the grating, P1, Q, P2,
                                L2 and PD are not where they belong, no
                                light reaches the detector.  Slide a mount
                                along a rail to change a distance, drag it
                                up or down to change the height of its post.
    Tab 2  Stage (top view)   - the rotation stage, the two guide rails and
                                the P2 mount are dials: grab them with the
                                mouse and turn them (wheel = fine step).

The scale assembly (17) is what it is in the real experiment: a screen
with mm graph paper.  Stand it anywhere in the beam and it shows the beam
spot - its height above the rail and its diameter - which is how
procedures [4], [8], [9] and [11] are actually carried out.  It also
blocks the light downstream, exactly like the real one.

Only physical readouts exist: the printed scale of the rotation stage
with its 6(d) readout device, the dial of the P2 mount, the mm grid of
the scale assembly and the DMM.  lambda, I_Total, I_Norm, dn and L are
never displayed, and nothing tells the student whether the alignment is
good: the DMM, the spot on the screen and the light sent back into the
slit are the only witnesses.

Run:  python IPhO2023_Q2_sim_KO.py   (EN edition: IPhO2023_Q2_sim_EN.py)

Hidden and randomised per session: the mechanical error of alpha, the
theta_Stage offset, the quartz thickness L, the blue LED peak and FWHM,
the detector gain, the stray-light offsets and the initial post heights.

White-LED throughput: least-squares fit of the official B.1 I_Total data
(rms 8 mV) - blue 383.8 mV @ 458.2 nm FWHM 26.8 nm, phosphor 172.5 mV @
540.3 nm, sigma 54.8 nm (blue side) / 94.2 nm (red side).
"""

import math
import random
import sys

LANG = "EN"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "KO" else en


def _setup_hangul_font(root):
    """Point every named Tk font at a family that has Hangul."""
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


try:
    import tkinter as tk
    from tkinter import ttk, filedialog
    HAS_TK = True
except Exception:
    HAS_TK = False

GRATING_D = 1.00e-6      # m, groove period of G
F1 = 100.0               # mm, focal length of L1
F2 = 80.0                # mm, focal length of L2
H_PD = 62.0              # mm, height of the PD aperture above the rail
H_LED = 62.0             # mm, height of the LED emission centre
PD_ACC = 8.0             # mm, height acceptance of the detector

# geometry of the side view (1 px = 1 mm along the rails)
RAIL_Y = 430             # y of the rail surface
PXMM = 1.30              # px per mm of height
SR_X0, SR_X1 = 120, 470  # short rail
LR_X0, LR_X1 = 470, 940  # long rail
JUNCTION = 470           # the "virtual through-hole" / stage axle


# =====================================================================
#  1.  PHYSICS ENGINE
# =====================================================================
def quartz_dn(lam_um):
    """dn = n_e - n_o of quartz; fit of Table 1 (|error| < 2e-6, 400-700 nm)."""
    return 8.699e-3 + 1.378e-4 / (lam_um * lam_um)


class Biref:
    #  key -> mount it belongs to when correctly installed
    NOMINAL_H = {"led": H_LED, "L1": 62.0, "P1": 62.0, "quartz": 62.0,
                 "P2": 62.0, "L2": 62.0, "PD": H_PD, "screen": 0.0}

    def __init__(self, seed=None):
        r = random.Random(seed)
        self.r = r
        # ---- hidden truth --------------------------------------------
        self.dalpha = r.gauss(0.0, 0.55)          # mechanical error of alpha
        self.stage_off = r.choice([-1.0, -0.5, 0.0, 0.5, 1.0])
        self.L = r.uniform(399.0, 410.0) * 1e-6   # 407 um nominal
        self.lam_blue = r.uniform(455.0, 461.0)
        self.fwhm_blue = r.uniform(23.0, 29.0)
        self.gain = r.uniform(0.92, 1.08)
        self.phi_p1 = float(r.randrange(0, 360))  # P1 direction on the P2 dial
        self.off_par = r.uniform(0.007, 0.013)
        self.off_per = r.uniform(0.003, 0.007)

        # ---- what is on the table -------------------------------------
        #   key -> dict(mount=..., x=px, h=mm)
        self.obj = {}
        self.slit_on_led = False
        self.slit_off = r.uniform(-6.0, 6.0)      # mm, slit position on the LED
        self.led_on = False
        self.grating_on_stage = False

        # ---- angles (top view) ----------------------------------------
        self.short_rail = r.choice([-2.0, -1.5, 2.5, 3.0])
        self.long_rail = 180.0 + self.short_rail + r.choice([-3.0, 2.0, 4.5])
        self.stage = 0.0
        self.phi = 0.0

        # ---- accessories ----------------------------------------------
        self.black_card = False
        self.white_card = False
        self.shield_box = False
        self.cylinder_on = False
        self.quartz_in = True

        # initial post heights of the two lenses are wrong on purpose
        self.h_init = {"L1": round(r.uniform(48.0, 78.0) * 2) / 2,
                       "L2": round(r.uniform(48.0, 78.0) * 2) / 2}

    # ---------------- placement helpers ----------------
    def put(self, key, mount, x, h=None):
        self.obj[key] = dict(mount=mount, x=float(x),
                             h=float(self.NOMINAL_H.get(key, 62.0)
                                     if h is None else h))
        if key == "stage":
            self.obj[key]["x"] = JUNCTION

    def drop(self, key):
        self.obj.pop(key, None)
        if key == "led":
            self.slit_on_led = False
            self.led_on = False
        if key == "stage":
            self.grating_on_stage = False

    def on(self, key, *mounts):
        o = self.obj.get(key)
        return bool(o) and (not mounts or o["mount"] in mounts)

    def x(self, key):
        o = self.obj.get(key)
        return o["x"] if o else None

    def h(self, key):
        o = self.obj.get(key)
        return o["h"] if o else None

    # ---------------- geometry of the beam ----------------
    @property
    def h_slit(self):
        """Height of the beam centre at the slit exit [mm]."""
        return H_LED + self.slit_off

    def chain_ok(self):
        """True when a light path LED -> slit -> L1 -> G -> ... -> PD exists."""
        if not (self.led_on and self.slit_on_led):
            return False
        if not (self.on("led", "srail") and self.on("L1", "srail")):
            return False
        if not ("srail" in self.obj and "lrail" in self.obj):
            return False
        if not (self.on("stage", "junction") and self.grating_on_stage):
            return False
        if not (self.on("L2", "lrail") and self.on("PD", "lrail")):
            return False
        if self.x("L1") <= self.x("led") or self.x("PD") <= self.x("L2"):
            return False
        return True

    def pol_ok(self):
        """P1 before the sample, P2 behind it (Malus analyser)."""
        if not (self.on("P1", "lrail") and self.on("P2", "lrail")):
            return False
        if self.x("P2") <= self.x("P1"):
            return False
        return True

    def quartz_active(self):
        """The quartz is in the beam AND between the two polarizers."""
        if not (self.on("quartz", "lrail") and self.quartz_in):
            return False
        if not self.pol_ok():
            return False
        return self.x("P1") < self.x("quartz") < self.x("P2")

    def d_slit_l1(self):
        return self.x("L1") - self.x("led") if self.on("L1", "srail") and \
            self.on("led", "srail") else None

    def d_l2_pd(self):
        return self.x("PD") - self.x("L2") if self.on("L2", "lrail") and \
            self.on("PD", "lrail") else None

    def divergence(self):
        """Residual divergence of the beam after L1 (0 when collimated)."""
        d = self.d_slit_l1()
        if d is None:
            return 0.0
        return (d - F1) / F1

    def beam_at(self, x_px):
        """
        (height above the rail [mm], diameter [mm], relative brightness)
        of the beam at the position x_px, or None if there is no beam there.
        """
        if not (self.led_on and self.slit_on_led and self.on("led", "srail")):
            return None
        x_led = self.x("led")
        if x_px < x_led:
            return None
        bright = math.exp(-(self.slit_off / 5.0) ** 2)
        # --- before L1: light diverging out of the slit -------------------
        if not self.on("L1", "srail") or x_px < self.x("L1"):
            d = x_px - x_led
            return self.h_slit, 3.0 + 0.10 * d, bright
        h1, x1 = self.h("L1"), self.x("L1")
        dir1 = (h1 - self.h_slit) / F1
        u = self.divergence()
        # --- after L1 (and before L2) -------------------------------------
        if not self.on("L2", "lrail") or x_px < self.x("L2"):
            d = x_px - x1
            return h1 + d * dir1, 6.0 + abs(0.12 * u) * d, bright
        x2, h2 = self.x("L2"), self.h("L2")
        d1 = x2 - x1
        hL2 = h1 + d1 * dir1
        w2 = 6.0 + abs(0.12 * u) * d1
        dir2 = dir1 - (hL2 - h2) / F2
        best = F2 * (1.0 + 1.1 * u)              # focal distance behind L2
        d = x_px - x2
        w = max(0.4, w2 * abs(1.0 - d / best)) if best > 1 else w2
        return hL2 + d * dir2, w, bright

    def screen_blocks(self):
        """The scale assembly standing in the beam blocks it."""
        sc = self.obj.get("screen")
        if not sc or sc["mount"] == "tray":
            return False
        if not self.on("led", "srail") or not self.on("PD", "lrail"):
            return False
        return self.x("led") < sc["x"] < self.x("PD")

    def spot_at_pd(self):
        """(height error [mm], spot diameter [mm]) at the detector."""
        if not self.chain_ok():
            return None
        h, w, _ = self.beam_at(self.x("PD"))
        return h - H_PD, w

    def alignment(self):
        """Overall optical throughput 0..1."""
        if not self.chain_ok() or self.screen_blocks():
            return 0.0
        dh, w = self.spot_at_pd()
        f = math.exp(-(dh / PD_ACC) ** 2)             # beam height at PD
        f *= math.exp(-((w - 0.4) / 3.0) ** 2)        # focusing
        f *= math.exp(-(self.slit_off / 5.0) ** 2)    # slit position [4]
        if "P1" not in self.obj or not self.on("P1", "lrail"):
            f *= 2.0        # the fitted spectrum contains both polarizers
        return f

    # ---------------- spectra ----------------
    @property
    def alpha_true(self):
        return 180.0 + self.short_rail - self.long_rail + self.dalpha

    @property
    def theta(self):
        return self.stage_off - self.stage

    def lam_nm(self):
        a = math.radians(self.alpha_true)
        th = math.radians(self.theta)
        return 2.0 * GRATING_D * math.sin(a / 2.0) * \
            math.cos(a / 2.0 - th) * 1e9

    def spectrum(self, lam):
        if lam <= 395.0 or lam >= 760.0:
            return 0.0
        s = self.fwhm_blue / (2.0 * math.sqrt(2.0 * math.log(2.0)))
        blue = 0.3838 * math.exp(-0.5 * ((lam - self.lam_blue) / s) ** 2)
        c, sl, sr = 540.26, 54.82, 94.21
        w = sl if lam < c else sr
        phos = 0.1725 * math.exp(-((lam - c) / w) ** 2)
        return self.gain * (blue + phos)

    def i_norm(self, lam):
        if not self.quartz_active():
            return 0.0
        gam = 2.0 * math.pi * quartz_dn(lam * 1e-3) * self.L / (lam * 1e-9)
        return math.sin(gam / 2.0) ** 2

    def components(self):
        """(I_parallel, I_perpendicular) [V] in front of P2."""
        if self.black_card or not self.chain_ok():
            return 0.0, 0.0
        tot = self.spectrum(self.lam_nm()) * self.alignment()
        f = self.i_norm(self.lam_nm())
        return tot * (1.0 - f), tot * f

    def offsets(self):
        k = 1.0
        if self.shield_box:
            k *= 0.35
        if self.cylinder_on:
            k *= 0.6
        return self.off_par * k, self.off_per * k

    def dmm_v(self):
        """DC voltage on the DMM [V], 1 mV resolution; None if not wired."""
        if "dmm" not in self.obj or not self.on("PD", "lrail"):
            return None
        ipar, iper = self.components()
        opar, oper = self.offsets()
        if self.pol_ok():
            d = math.radians(self.phi - self.phi_p1)
            w = math.sin(d) ** 2
            v = ipar * math.cos(d) ** 2 + iper * w + opar * (1 - w) + oper * w
        elif self.on("P2", "lrail"):        # analyser without polarizer
            v = 0.5 * (ipar + iper) + opar
        else:
            v = ipar + iper + opar
        v += self.r.gauss(0.0, 5e-4)
        return max(round(v, 3), 0.0)

    def retro(self):
        """Light reflected by G back into the slit (0..1) - procedure [13]."""
        if not (self.led_on and self.slit_on_led and self.grating_on_stage
                and self.on("stage", "junction") and self.on("led", "srail")):
            return 0.0
        return math.exp(-(self.theta / 0.7) ** 2)

    def missing(self):
        need = [("srail", T("짧은 레일", "short rail")),
                ("lrail", T("긴 레일", "long rail")),
                ("stage", T("회전 스테이지", "rotation stage")),
                ("led", "LED"), ("L1", "L1"), ("L2", "L2"),
                ("PD", "PD"), ("dmm", "DMM")]
        out = [n for k, n in need if k not in self.obj]
        if not self.slit_on_led:
            out.append(T("슬릿", "slit"))
        if not self.led_on:
            out.append(T("건전지", "batteries"))
        if not self.grating_on_stage:
            out.append(T("회절격자", "grating"))
        return out

    def truth(self):
        return dict(alpha=self.alpha_true, stage_off=self.stage_off,
                    L=self.L, lam_blue=self.lam_blue, fwhm=self.fwhm_blue,
                    phi_p1=self.phi_p1, slit_off=self.slit_off)


# =====================================================================
#  2.  APPARATUS DRAWINGS  (traced from the photographs of Figs. 3-5)
# =====================================================================
MDF = "#cdae82"
MDF_D = "#a98a5f"
MDF_L = "#e0c79f"
PCB = "#2f8f4e"
PCB_D = "#1d6636"
STEEL = "#c3c7cb"
STEEL_D = "#8d939a"
WHITE_P = "#f2f1ee"
GREY_W = "#4c4f55"
ACRYL = "#dfe9ef"
TABLE = "#ece7dd"
DARK = "#1d2126"


def yof(h_mm):
    """canvas y of a height h above the rail"""
    return RAIL_Y - 10 - h_mm * PXMM


def foot(c, x, ytop, w=46, tag=()):
    c.create_rectangle(x - w / 2, ytop, x + w / 2, RAIL_Y - 10, fill=MDF,
                       outline=MDF_D, tags=tag)
    c.create_rectangle(x - 6, RAIL_Y - 19, x + 6, RAIL_Y - 10, fill=TABLE,
                       outline=MDF_D, tags=tag)


def d_led(c, x, tag=(), slit=False, slit_off=0.0, on=False):
    y = yof(H_LED)
    foot(c, x, RAIL_Y - 32, 46, tag)
    c.create_rectangle(x - 7, y + 10, x + 7, RAIL_Y - 32, fill=MDF,
                       outline=MDF_D, tags=tag)
    c.create_polygon(x - 26, y + 30, x + 26, y + 30, x + 30, y - 30,
                     x - 22, y - 30, fill=PCB, outline=PCB_D, tags=tag)
    for dx in (-14, 12):
        c.create_rectangle(x + dx, y + 8, x + dx + 9, y + 18, fill="#173d22",
                           outline="", tags=tag)
    c.create_oval(x - 9, y - 9, x + 9, y + 9,
                  fill="#fdfdf5" if on else "#e6e6dc", outline="#c9c9bd",
                  tags=tag)
    if on:
        c.create_oval(x - 15, y - 15, x + 15, y + 15, outline="#fff8c8",
                      tags=tag)
    if slit:
        ys = yof(H_LED + slit_off)
        c.create_rectangle(x - 2, ys - 26, x + 32, ys + 26, fill="#242424",
                           outline="#3a3a3a", tags=tag)
        c.create_line(x + 15, ys - 12, x + 15, ys + 12, fill="#f7f7e0",
                      tags=tag)


def d_lens(c, x, h, tag=(), label=None):
    y = yof(h)
    foot(c, x, RAIL_Y - 30, 48, tag)
    c.create_rectangle(x - 5, y + 18, x + 5, RAIL_Y - 30, fill=STEEL,
                       outline=STEEL_D, tags=tag)
    c.create_oval(x - 16, RAIL_Y - 32, x - 4, RAIL_Y - 20, fill=WHITE_P,
                  outline="#cfcfcf", tags=tag)
    c.create_rectangle(x - 30, y - 28, x + 30, y + 28, fill=MDF,
                       outline=MDF_D, tags=tag)
    c.create_oval(x - 21, y - 21, x + 21, y + 21, fill=ACRYL,
                  outline="#a9b6bd", tags=tag)
    c.create_arc(x - 21, y - 21, x + 21, y + 21, start=40, extent=90,
                 style="arc", outline="#ffffff", tags=tag)
    if label:
        c.create_text(x, y - 38, text=label, font=("", 9, "bold"),
                      fill="#2c3e50", tags=tag)


def d_frame_plate(c, x, h, tag=(), label=None, window=24):
    y = yof(h)
    foot(c, x, RAIL_Y - 40, 46, tag)
    c.create_rectangle(x - 11, y + 22, x + 11, RAIL_Y - 40, fill=MDF,
                       outline=MDF_D, tags=tag)
    c.create_rectangle(x - 30, y - 23, x + 30, y + 23, fill=WHITE_P,
                       outline="#d2d0cb", tags=tag)
    hw = window / 2.0
    c.create_rectangle(x - hw, y - hw, x + hw, y + hw, fill=GREY_W,
                       outline="#2f3237", tags=tag)
    if label:
        c.create_text(x, y - 34, text=label, font=("", 9, "bold"),
                      fill="#2c3e50", tags=tag)


def d_p2(c, x, h, tag=(), phi=0.0):
    y = yof(h)
    foot(c, x, RAIL_Y - 26, 52, tag)
    c.create_polygon(x - 26, RAIL_Y - 26, x + 26, RAIL_Y - 26, x + 18,
                     RAIL_Y - 48, x - 18, RAIL_Y - 48, fill="#2b2f34",
                     outline="#15181b", tags=tag)
    r = 34
    c.create_oval(x - r, y - r, x + r, y + r, fill="#e9ecef",
                  outline=STEEL_D, tags=tag)
    for a in range(0, 360, 10):
        rad = math.radians(a)
        ln = 7 if a % 30 == 0 else 3
        c.create_line(x + (r - ln) * math.cos(rad), y + (r - ln) * math.sin(rad),
                      x + r * math.cos(rad), y + r * math.sin(rad),
                      fill="#6b7075", tags=tag)
    c.create_oval(x - 21, y - 13, x + 21, y + 13, fill=WHITE_P,
                  outline="#cfcfcf", tags=tag)
    c.create_oval(x - 12, y - 12, x + 12, y + 12, fill="#7c7f83",
                  outline="#5b5e62", tags=tag)
    rad = math.radians(phi - 90.0)
    c.create_line(x, y, x + (r - 3) * math.cos(rad), y + (r - 3) * math.sin(rad),
                  fill="#c0392b", width=2, tags=tag)
    c.create_text(x, y - r - 10, text="P2", font=("", 9, "bold"),
                  fill="#2c3e50", tags=tag)


def d_pd(c, x, tag=(), cylinder=False):
    y = yof(H_PD)
    c.create_rectangle(x - 34, RAIL_Y - 32, x + 40, RAIL_Y - 10, fill=MDF,
                       outline=MDF_D, tags=tag)
    c.create_rectangle(x - 28, y + 6, x - 20, RAIL_Y - 32, fill=MDF,
                       outline=MDF_D, tags=tag)
    c.create_rectangle(x + 4, y - 2, x + 12, RAIL_Y - 32, fill=MDF,
                       outline=MDF_D, tags=tag)
    c.create_rectangle(x + 12, y - 22, x + 34, y + 22, fill=PCB,
                       outline=PCB_D, tags=tag)
    c.create_rectangle(x + 18, y - 10, x + 28, y, fill="#173d22", outline="",
                       tags=tag)
    c.create_line(x + 34, y + 10, x + 58, y + 38, fill="#c0392b", width=2,
                  tags=tag)
    c.create_line(x + 34, y + 16, x + 60, y + 50, fill="#1c1c1c", width=2,
                  tags=tag)
    if cylinder:
        c.create_rectangle(x - 40, y - 8, x + 12, y + 6, fill="#232323",
                           outline="#3a3a3a", tags=tag)
        c.create_oval(x - 44, y - 8, x - 36, y + 6, fill="#151515",
                      outline="#3a3a3a", tags=tag)
    c.create_text(x + 24, y - 32, text="PD", font=("", 9, "bold"),
                  fill="#2c3e50", tags=tag)


def d_dmm(c, x, y, s=1.0, tag=(), reading=None):
    c.create_rectangle(x, y, x + 96 * s, y + 150 * s, fill="#c0392b",
                       outline="#7b241c", width=2, tags=tag)
    c.create_rectangle(x + 10 * s, y + 10 * s, x + 86 * s, y + 44 * s,
                       fill="#cfe3cf", outline="#4d5b4d", tags=tag)
    c.create_text(x + 82 * s, y + 30 * s, anchor="e",
                  font=("Consolas", max(8, int(13 * s)), "bold"),
                  fill="#1c2833",
                  text="- - -" if reading is None else f"{reading:.3f}",
                  tags=tag)
    c.create_rectangle(x + 12 * s, y + 50 * s, x + 42 * s, y + 60 * s,
                       fill="#e67e22", outline="", tags=tag)
    c.create_rectangle(x + 52 * s, y + 50 * s, x + 84 * s, y + 60 * s,
                       fill="#2980b9", outline="", tags=tag)
    c.create_oval(x + 20 * s, y + 70 * s, x + 76 * s, y + 126 * s,
                  fill="#1c1c1c", outline="#111", tags=tag)
    c.create_oval(x + 40 * s, y + 90 * s, x + 56 * s, y + 106 * s,
                  fill="#3d3d3d", outline="", tags=tag)


def d_rail(c, x0, x1, y, tag=()):
    c.create_rectangle(x0, y - 10, x1, y, fill=MDF_L, outline=MDF_D, tags=tag)
    c.create_line(x0, y - 10, x1, y - 10, fill="#f0e0c2", tags=tag)


def d_stage_side(c, x, tag=(), grating=False):
    y = RAIL_Y - 10
    c.create_oval(x - 84, y - 8, x + 84, y + 10, fill=ACRYL,
                  outline="#b8c6cd", tags=tag)
    c.create_oval(x - 74, y - 22, x + 74, y + 2, fill=MDF_L, outline=MDF_D,
                  tags=tag)
    c.create_rectangle(x - 26, y - 34, x + 26, y - 14, fill=STEEL,
                       outline=STEEL_D, tags=tag)
    c.create_oval(x - 18, y - 32, x + 18, y - 16, fill="#dfe3e6",
                  outline=STEEL_D, tags=tag)
    c.create_rectangle(x - 7, y - 66, x + 7, y - 30, fill="#eef4f7",
                       outline="#c3ced4", tags=tag)
    if grating:
        c.create_rectangle(x - 26, y - 120, x + 26, y - 66, fill="#9aa1a6",
                           outline="#6f767b", tags=tag)
        c.create_rectangle(x - 18, y - 112, x + 18, y - 80, fill="#3b4046",
                           outline="#22262a", tags=tag)
        c.create_text(x, y - 132, text="G", font=("", 9, "bold"),
                      fill="#2c3e50", tags=tag)


def d_stage_top(c, cx, cy, r, stage_deg, tag=()):
    c.create_oval(cx - r - 10, cy - r - 10, cx + r + 10, cy + r + 10,
                  fill=ACRYL, outline="#b8c6cd", tags=tag)
    c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=MDF_L, outline=MDF_D,
                  tags=tag)
    c.create_oval(cx - r + 26, cy - r + 26, cx + r - 26, cy + r - 26,
                  fill=MDF, outline=MDF_D, tags=tag)
    for a in range(0, 360, 2):
        rad = math.radians(a + 90 - stage_deg)
        ln = 12 if a % 10 == 0 else (8 if a % 10 == 5 else 4)
        c.create_line(cx + (r - ln) * math.cos(rad),
                      cy + (r - ln) * math.sin(rad),
                      cx + (r - 1) * math.cos(rad),
                      cy + (r - 1) * math.sin(rad), fill="#6b5b3e", tags=tag)
        if a % 30 == 0:
            c.create_text(cx + (r - 20) * math.cos(rad),
                          cy + (r - 20) * math.sin(rad), text=str(a),
                          font=("", 6), fill="#5b4a30", tags=tag)
    c.create_rectangle(cx - 22, cy - 22, cx + 22, cy + 22, fill=STEEL,
                       outline=STEEL_D, tags=tag)
    c.create_oval(cx - 17, cy - 17, cx + 17, cy + 17, fill="#e3e7ea",
                  outline=STEEL_D, tags=tag)
    c.create_oval(cx - 9, cy - 9, cx + 9, cy + 9, fill="#c8cdd1",
                  outline=STEEL_D, tags=tag)
    c.create_rectangle(cx - 9, cy + r - 2, cx + 9, cy + r + 13, fill=STEEL,
                       outline=STEEL_D, tags=tag)
    for i in range(-3, 4):
        c.create_line(cx + i * 2.5, cy + r - 2, cx + i * 2.5, cy + r + 6,
                      fill="#4b4f54", tags=tag)
    c.create_line(cx, cy + r - 12, cx, cy + r + 13, fill="#c0392b", width=2,
                  tags=tag)


def d_screen(c, x, tag=(), spot=None):
    """17: the scale assembly - mm graph paper on its cardboard stand."""
    top = yof(105)
    c.create_polygon(x - 46, RAIL_Y - 10, x + 46, RAIL_Y - 10, x + 34, top,
                     x - 34, top, fill="#c9a97e", outline=MDF_D, tags=tag)
    gx0, gy0, gx1, gy1 = x - 28, yof(100), x + 28, yof(20)
    c.create_rectangle(gx0, gy0, gx1, gy1, fill="#f6f6f0", outline="#b9b9ae",
                       tags=tag)
    step = 5 * PXMM
    n = 0
    yy = gy1
    while yy > gy0:
        c.create_line(gx0, yy, gx1, yy,
                      fill="#93b7d8" if n % 2 == 0 else "#cfe0ee", tags=tag)
        if n % 2 == 0:
            c.create_text(gx0 - 4, yy, anchor="e", text=str(20 + n * 5),
                          font=("", 6), fill="#7f8c8d", tags=tag)
        yy -= step
        n += 1
    xx = gx0 + step
    while xx < gx1:
        c.create_line(xx, gy0, xx, gy1, fill="#cfe0ee", tags=tag)
        xx += step
    if spot:
        h, w, b = spot
        if 18 <= h <= 102:
            yc = yof(h)
            rr = max(1.5, w * PXMM / 2.0)
            col = "#f6e58d" if b > 0.6 else "#efe0a0"
            c.create_oval(x - rr * 1.2, yc - rr, x + rr * 1.2, yc + rr,
                          fill=col, outline="#e8c95a", tags=tag)
    c.create_text(x, top - 10, text=T("눈금자 조립체", "scale assembly"),
                  font=("", 8), fill="#6b7075", tags=tag)


def d_battery(c, x, y, tag=()):
    for i in range(2):
        c.create_oval(x - 20 + 22 * i, y - 11, x - 2 + 22 * i, y + 11,
                      fill="#d7d9dc", outline="#9aa0a6", tags=tag)
        c.create_arc(x - 20 + 22 * i, y - 11, x - 2 + 22 * i, y + 11,
                     start=200, extent=140, fill="#c0392b", outline="",
                     tags=tag)


def d_anti_slip(c, x0, x1, y, tag=()):
    c.create_rectangle(x0, y, x1, y + 10, fill="#3c3f43", outline="#2a2d30",
                       tags=tag)
    for x in range(int(x0) + 4, int(x1), 7):
        c.create_line(x, y + 2, x + 4, y + 9, fill="#585c61", tags=tag)


# =====================================================================
#  3.  BENCH TAB  (side view, free placement)
# =====================================================================
TRAY = [("srail", T("짧은 가이드 레일 (15)", "short guide rail (15)")),
        ("lrail", T("긴 가이드 레일 (16)", "long guide rail (16)")),
        ("stage", T("회전 스테이지 (6c)", "rotation stage (6c)")),
        ("grating", T("회절격자 (6a)", "grating (6a)")),
        ("battery", T("건전지 (2)", "batteries (2)")),
        ("led", T("백색 LED (1)", "white LED (1)")),
        ("slit", T("슬릿 (3)", "slit (3)")),
        ("L1", T("렌즈 (5)", "lens (5)")),
        ("L2", T("렌즈 (5)", "lens (5)")),
        ("P1", T("편광자 (7)", "polarizer (7)")),
        ("quartz", T("수정판 (8)", "quartz (8)")),
        ("P2", T("편광자+회전마운트 (9)", "polarizer on mount (9)")),
        ("PD", T("광검출기 (12,11)", "photodetector (12,11)")),
        ("cylinder", T("차광 실린더 (10)", "shield cylinder (10)")),
        ("dmm", T("DMM (14)", "DMM (14)")),
        ("screen", T("눈금자 조립체 (17)", "scale assembly (17)"))]


class BenchTab:
    def __init__(self, master, app):
        self.app = app
        self.sim = app.sim
        self.drag = None          # [key, dx, dy]
        self.msg = ""
        self.frame = ttk.Frame(master)
        bar = ttk.Frame(self.frame, padding=(8, 4))
        bar.pack(fill="x")
        self.lbl = ttk.Label(bar, text="", font=("", 10))
        self.lbl.pack(side="left")
        self.v_white = tk.BooleanVar(value=False)
        self.v_black = tk.BooleanVar(value=False)
        self.v_box = tk.BooleanVar(value=False)
        self.v_q = tk.BooleanVar(value=True)
        for txt, var in ((T("백색 카드 (18)", "white card (18)"), self.v_white),
                         (T("흑색 카드 (19)", "black card (19)"), self.v_black),
                         (T("차광 상자 (22)", "shield box (22)"), self.v_box),
                         (T("수정판 삽입", "quartz in"), self.v_q)):
            ttk.Checkbutton(bar, text=txt, variable=var,
                            command=self.upd).pack(side="right", padx=4)
        self.c = tk.Canvas(self.frame, width=1000, height=620, bg=TABLE,
                           highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        self.c.bind("<ButtonPress-1>", self.press)
        self.c.bind("<B1-Motion>", self.motion)
        self.c.bind("<ButtonRelease-1>", self.release)
        self.draw()

    # ------------------------------------------------------------------
    def upd(self):
        s = self.sim
        s.white_card = self.v_white.get()
        s.black_card = self.v_black.get()
        s.shield_box = self.v_box.get()
        s.quartz_in = self.v_q.get()
        self.draw()

    def tray_slots(self):
        out, x = [], 52
        for key, name in TRAY:
            if key in self.sim.obj or (key == "slit" and self.sim.slit_on_led) \
                    or (key == "battery" and self.sim.led_on) \
                    or (key == "grating" and self.sim.grating_on_stage) \
                    or (key == "cylinder" and self.sim.cylinder_on):
                continue
            out.append((key, name, x, 578))
            x += 62
        return out

    def hit_placed(self, ex, ey):
        """Which installed object is under the cursor?"""
        s = self.sim
        best = None
        for key, o in s.obj.items():
            if key in ("srail", "lrail"):
                continue
            x = o["x"]
            if abs(ex - x) < 34 and ey < RAIL_Y + 6:
                best = key
        if s.slit_on_led and "led" in s.obj and \
                abs(ex - (s.obj["led"]["x"] + 16)) < 18:
            best = "slit"
        return best

    # ------------------------------------------------------------------
    def press(self, e):
        for key, name, x, y in self.tray_slots():
            if abs(e.x - x) < 30 and abs(e.y - y) < 30:
                self.drag = [key, 0, 0, True]
                return
        k = self.hit_placed(e.x, e.y)
        if k:
            self.drag = [k, 0, 0, False]

    def motion(self, e):
        if not self.drag:
            return
        self.drag[1], self.drag[2] = e.x, e.y
        key = self.drag[0]
        s = self.sim
        # live move of an installed mount
        if not self.drag[3] and key in s.obj and e.y < RAIL_Y + 10:
            o = s.obj[key]
            if o["mount"] in ("srail", "lrail"):
                lo, hi = (SR_X0 + 20, SR_X1 - 20) if o["mount"] == "srail" \
                    else (LR_X0 + 20, LR_X1 - 20)
                o["x"] = max(lo, min(hi, e.x))
                if key in ("L1", "L2"):
                    o["h"] = max(35.0, min(95.0,
                                           round((RAIL_Y - 10 - e.y) / PXMM * 2) / 2))
        if not self.drag[3] and key == "slit" and s.slit_on_led:
            s.slit_off = max(-8.0, min(8.0, round(
                ((RAIL_Y - 10 - e.y) / PXMM - H_LED) * 2) / 2))
        self.draw()

    def release(self, e):
        if not self.drag:
            return
        key, _, _, from_tray = self.drag
        self.drag = None
        s = self.sim
        if e.y > 540:                                  # back into the tray
            if key in s.obj:
                s.drop(key)
            elif key == "slit":
                s.slit_on_led = False
            elif key == "battery":
                s.led_on = False
            elif key == "grating":
                s.grating_on_stage = False
            elif key == "cylinder":
                s.cylinder_on = False
            self.draw()
            return
        if not from_tray:
            self.draw()
            return
        self.install(key, e.x, e.y)
        self.draw()

    def install(self, key, x, y):
        """Free placement - nothing is enforced, the physics decides."""
        s = self.sim
        near_rail = y > RAIL_Y - 150
        if key == "srail":
            s.put("srail", "table", (SR_X0 + SR_X1) / 2)
            return
        if key == "lrail":
            # only forms the virtual hole when its end meets the short rail
            s.put("lrail", "table", (LR_X0 + LR_X1) / 2)
            return
        if key == "stage":
            ok = ("srail" in s.obj and "lrail" in s.obj
                  and abs(x - JUNCTION) < 70)
            s.put("stage", "junction" if ok else "table",
                  JUNCTION if ok else x)
            return
        if key == "grating":
            if s.on("stage", "junction") and abs(x - JUNCTION) < 70:
                s.grating_on_stage = True
            else:
                self.msg = T("스테이지 축 위에 붙여야 합니다.",
                             "it must be taped onto the stage axle.")
            return
        if key == "battery":
            if s.on("led") and abs(x - s.x("led")) < 60:
                s.led_on = True
            else:
                self.msg = T("LED 모듈에 넣어야 합니다.",
                             "the batteries go into the LED module.")
            return
        if key == "slit":
            if s.on("led") and abs(x - s.x("led")) < 60:
                s.slit_on_led = True
                s.slit_off = max(-8.0, min(8.0, round(
                    ((RAIL_Y - 10 - y) / PXMM - H_LED) * 2) / 2))
            else:
                self.msg = T("LED 모듈 앞면에 나사로 고정합니다.",
                             "the slit is screwed onto the LED module.")
            return
        if key == "cylinder":
            if s.on("PD") and abs(x - s.x("PD")) < 70:
                s.cylinder_on = True
            else:
                self.msg = T("PD 마운트에 끼웁니다.",
                             "it goes on the PD mount.")
            return
        if key == "dmm":
            s.put("dmm", "table", max(120, min(880, x)))
            return
        if key == "screen":
            s.put("screen", "table", max(60, min(940, x)))
            return
        # optical mounts: LED, L1, L2, P1, Q, P2, PD
        mount = "table"
        if near_rail and "srail" in s.obj and SR_X0 + 10 < x < SR_X1 - 10:
            mount = "srail"
        elif near_rail and "lrail" in s.obj and LR_X0 + 10 < x < LR_X1 - 10:
            mount = "lrail"
        h = None
        if key in ("L1", "L2"):
            h = s.h_init[key]
        s.put(key, mount, x, h)

    # ------------------------------------------------------------------
    def draw(self):
        c = self.c
        s = self.sim
        c.delete("all")
        c.create_rectangle(0, 0, 1000, 620, fill=TABLE, outline="")
        c.create_rectangle(0, RAIL_Y, 1000, 620, fill="#f6f3ec", outline="")
        c.create_line(0, RAIL_Y, 1000, RAIL_Y, fill="#d5cfc4")

        d_anti_slip(c, 110, 460, RAIL_Y)
        d_anti_slip(c, 500, 900, RAIL_Y)
        if "srail" in s.obj:
            d_rail(c, SR_X0, SR_X1, RAIL_Y)
        if "lrail" in s.obj:
            d_rail(c, LR_X0, LR_X1, RAIL_Y - 4)
        if "stage" in s.obj:
            d_stage_side(c, s.x("stage"), grating=s.grating_on_stage)

        # ---- the beam -----------------------------------------------
        if s.led_on and s.slit_on_led and s.on("led"):
            xs = int(s.x("led")) + 16
            xe = int(s.x("PD")) if s.on("PD") else 940
            if s.screen_blocks():
                xe = int(s.obj["screen"]["x"])
            prev = None
            x = xs
            while x <= xe:
                b = s.beam_at(x)
                if b:
                    h, w, br = b
                    y = yof(h)
                    hw = max(1.0, w * PXMM / 2.0)
                    if prev:
                        c.create_polygon(prev[0], prev[1] - prev[2],
                                         x, y - hw, x, y + hw,
                                         prev[0], prev[1] + prev[2],
                                         fill="#f7f0c0", outline="", stipple="gray50")
                    prev = (x, y, hw)
                x += 8

        # ---- the mounts ----------------------------------------------
        for key in ("led", "L1", "P1", "quartz", "P2", "L2", "PD"):
            if key not in s.obj:
                continue
            o = s.obj[key]
            x, h = o["x"], o["h"]
            if key == "led":
                d_led(c, x, slit=s.slit_on_led, slit_off=s.slit_off,
                      on=s.led_on)
            elif key in ("L1", "L2"):
                d_lens(c, x, h, label=key)
            elif key == "P1":
                d_frame_plate(c, x, h, label="P1", window=26)
            elif key == "quartz":
                d_frame_plate(c, x, h, label="Q", window=14)
            elif key == "P2":
                d_p2(c, x, h, phi=s.phi)
            elif key == "PD":
                d_pd(c, x, cylinder=s.cylinder_on)
            if o["mount"] == "table":
                c.create_text(x, RAIL_Y + 14, text=T("(레일 위가 아님)",
                                                     "(not on a rail)"),
                              font=("", 7), fill="#c0392b")
        if "screen" in s.obj:
            x = s.obj["screen"]["x"]
            spot = s.beam_at(x) if (s.led_on and s.slit_on_led) else None
            d_screen(c, x, spot=spot)
        if "dmm" in s.obj:
            d_dmm(c, s.x("dmm") - 48, RAIL_Y + 40, 0.72, reading=s.dmm_v())

        # ---- white card at the detector -------------------------------
        if s.white_card and s.chain_ok():
            dh, w = s.spot_at_pd()
            x, y = 880, 110
            c.create_rectangle(x - 60, y - 60, x + 60, y + 60, fill="#f4f4ee",
                               outline="#b9b9ae")
            rr = max(1.5, w * 2.2)
            c.create_oval(x - rr * 1.2, y - dh * 1.6 - rr,
                          x + rr * 1.2, y - dh * 1.6 + rr, fill="#f6e58d",
                          outline="#e8c95a")
            c.create_text(x, y - 70, text=T("백색 카드 (PD 위치)",
                                            "white card (at PD)"),
                          font=("", 8), fill="#6b7075")

        # ---- tray ------------------------------------------------------
        c.create_rectangle(0, 540, 1000, 620, fill="#e2ddd2", outline="")
        c.create_text(14, 548, anchor="w", font=("", 9, "bold"),
                      fill="#6b7075",
                      text=T("부품 트레이 — 끌어다 원하는 곳에 놓으세요 "
                             "(트레이로 되돌려 놓으면 회수)",
                             "parts tray - drag anything anywhere "
                             "(drop it back here to remove it)"))
        for key, name, x, y in self.tray_slots():
            if self.drag and self.drag[0] == key:
                continue
            self.icon(key, x, y)
        if self.drag:
            key = self.drag[0]
            self.icon(key, self.drag[1], self.drag[2])

        txt = ""
        if s.screen_blocks():
            txt = T("눈금자 조립체가 빔을 가로막고 있습니다.",
                    "the scale assembly is blocking the beam.")
        self.lbl.config(text=self.msg or txt)
        self.msg = ""

    def icon(self, key, x, y):
        c = self.c
        if key in ("srail", "lrail"):
            w = 20 if key == "srail" else 28
            c.create_rectangle(x - w, y - 5, x + w, y + 3, fill=MDF_L,
                               outline=MDF_D)
        elif key == "stage":
            c.create_oval(x - 22, y - 12, x + 22, y + 12, fill=MDF_L,
                          outline=MDF_D)
            c.create_oval(x - 7, y - 5, x + 7, y + 5, fill=STEEL,
                          outline=STEEL_D)
        elif key == "grating":
            c.create_rectangle(x - 15, y - 15, x + 15, y + 13, fill="#9aa1a6",
                               outline="#6f767b")
            c.create_rectangle(x - 10, y - 10, x + 10, y + 8, fill="#3b4046",
                               outline="#22262a")
        elif key == "battery":
            d_battery(c, x + 10, y)
        elif key == "led":
            c.create_polygon(x - 14, y + 12, x + 14, y + 12, x + 16, y - 14,
                             x - 12, y - 14, fill=PCB, outline=PCB_D)
            c.create_oval(x - 6, y - 8, x + 6, y + 4, fill="#f2f2ea",
                          outline="#c9c9bd")
        elif key == "slit":
            c.create_rectangle(x - 16, y - 16, x + 16, y + 16, fill="#242424",
                               outline="#3a3a3a")
            c.create_line(x, y - 8, x, y + 8, fill="#f7f7e0")
        elif key in ("L1", "L2"):
            c.create_rectangle(x - 18, y - 15, x + 18, y + 15, fill=MDF,
                               outline=MDF_D)
            c.create_oval(x - 12, y - 12, x + 12, y + 12, fill=ACRYL,
                          outline="#a9b6bd")
        elif key in ("P1", "quartz"):
            c.create_rectangle(x - 18, y - 13, x + 18, y + 13, fill=WHITE_P,
                               outline="#d2d0cb")
            w = 10 if key == "P1" else 5
            c.create_rectangle(x - w, y - w, x + w, y + w, fill=GREY_W,
                               outline="#2f3237")
        elif key == "P2":
            c.create_oval(x - 17, y - 17, x + 17, y + 15, fill="#e9ecef",
                          outline=STEEL_D)
            c.create_oval(x - 8, y - 8, x + 8, y + 6, fill="#7c7f83",
                          outline="#5b5e62")
        elif key == "PD":
            c.create_rectangle(x - 4, y - 16, x + 14, y + 4, fill=PCB,
                               outline=PCB_D)
            c.create_rectangle(x - 18, y + 4, x + 18, y + 14, fill=MDF,
                               outline=MDF_D)
        elif key == "cylinder":
            c.create_rectangle(x - 20, y - 6, x + 16, y + 6, fill="#232323",
                               outline="#3a3a3a")
            c.create_oval(x - 24, y - 6, x - 16, y + 6, fill="#151515",
                          outline="#3a3a3a")
        elif key == "dmm":
            c.create_rectangle(x - 12, y - 20, x + 12, y + 16, fill="#c0392b",
                               outline="#7b241c")
            c.create_rectangle(x - 8, y - 16, x + 8, y - 6, fill="#cfe3cf",
                               outline="#4d5b4d")
        elif key == "screen":
            c.create_polygon(x - 18, y + 16, x + 18, y + 16, x + 13, y - 18,
                             x - 13, y - 18, fill="#c9a97e", outline=MDF_D)
            c.create_rectangle(x - 10, y - 14, x + 10, y + 10, fill="#f6f6f0",
                               outline="#b9b9ae")


# =====================================================================
#  4.  STAGE TAB  (top view - everything is a dial)
# =====================================================================
class StageTab:
    CX, CY, R = 330, 250, 96
    P2X, P2Y, P2R = 600, 524, 58

    def __init__(self, master, app):
        self.app = app
        self.sim = app.sim
        self.rows = []
        self.grab = None
        self.frame = ttk.Frame(master)
        right = ttk.Frame(self.frame, padding=8)
        right.pack(side="right", fill="y")
        self.c = tk.Canvas(self.frame, width=760, height=700, bg=DARK,
                           highlightthickness=0)
        self.c.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text=T("측정 노트", "measurement notebook"),
                  font=("", 10, "bold")).pack(anchor="w")
        ttk.Button(right, text=T("현재 값 기록", "record"),
                   command=self.record).pack(fill="x", pady=2)
        ttk.Button(right, text=T("CSV 저장", "export CSV"),
                   command=self.export).pack(fill="x")
        self.tv = ttk.Treeview(right, columns=("a", "b", "c"),
                               show="headings", height=22)
        for cc, t in (("a", T("θ_Stage", "theta_Stage")), ("b", "φ"),
                      ("c", "DMM /V")):
            self.tv.heading(cc, text=t)
            self.tv.column(cc, width=76, anchor="center")
        self.tv.pack(fill="both", expand=True, pady=6)
        for ev, fn in (("<ButtonPress-1>", self.press),
                       ("<B1-Motion>", self.motion),
                       ("<ButtonRelease-1>", self.release),
                       ("<MouseWheel>", self.wheel)):
            self.c.bind(ev, fn)
        self.c.bind("<Button-4>", lambda e: self.wheel(e, +1))
        self.c.bind("<Button-5>", lambda e: self.wheel(e, -1))
        self.draw()

    # ---------------- interaction ----------------
    def ang(self, e, cx, cy):
        return (math.degrees(math.atan2(e.x - cx, -(e.y - cy)))) % 360

    def press(self, e):
        s = self.sim
        d2 = (e.x - self.P2X) ** 2 + (e.y - self.P2Y) ** 2
        if d2 < (self.P2R + 8) ** 2 and s.on("P2"):
            self.grab = ("phi", self.ang(e, self.P2X, self.P2Y) - s.phi)
            return
        dx, dy = e.x - self.CX, e.y - self.CY
        rr = math.hypot(dx, dy)
        a = self.ang(e, self.CX, self.CY)
        if rr > self.R and rr < 280:
            # grab the rail whose centre line is nearest to the pointer
            best, bd = None, 1e9
            for key, val in (("srail", s.short_rail), ("lrail", s.long_rail)):
                if key not in s.obj:
                    continue
                dang = abs(((a - val + 180) % 360) - 180)
                dist = rr * math.sin(math.radians(min(dang, 90)))
                if dang < 90 and dist < bd:
                    best, bd = (key, val), dist
            if best and bd < 20:
                self.grab = (best[0], a - best[1])
                return
        if rr <= self.R and "stage" in s.obj:
            self.grab = ("stage", a - s.stage)

    def motion(self, e):
        if not self.grab:
            return
        what, off = self.grab
        s = self.sim
        if what == "phi":
            s.phi = round(self.ang(e, self.P2X, self.P2Y) - off) % 360
        else:
            a = self.ang(e, self.CX, self.CY) - off
            if what == "stage":
                v = ((a + 180) % 360) - 180
                s.stage = max(-40.0, min(40.0, round(v * 2) / 2))
            elif what == "srail":
                v = ((a + 180) % 360) - 180
                s.short_rail = max(-12.0, min(12.0, round(v * 2) / 2))
            else:
                s.long_rail = max(140.0, min(220.0, round(a % 360 * 2) / 2))
        self.draw()

    def release(self, _):
        self.grab = None

    def wheel(self, e, direction=None):
        d = direction if direction is not None else (1 if e.delta > 0 else -1)
        s = self.sim
        if (e.x - self.P2X) ** 2 + (e.y - self.P2Y) ** 2 < (self.P2R + 8) ** 2:
            if s.on("P2"):
                s.phi = (s.phi + d) % 360
        elif (e.x - self.CX) ** 2 + (e.y - self.CY) ** 2 < self.R ** 2:
            if "stage" in s.obj:
                s.stage = max(-40.0, min(40.0, s.stage + 0.5 * d))
        else:
            a = self.ang(e, self.CX, self.CY)
            if abs(((a - s.long_rail + 180) % 360) - 180) < 25:
                s.long_rail = max(140.0, min(220.0, s.long_rail + 0.5 * d))
            elif abs(((a - s.short_rail + 180) % 360) - 180) < 25:
                s.short_rail = max(-12.0, min(12.0, s.short_rail + 0.5 * d))
        self.draw()

    # ---------------- notebook ----------------
    def record(self):
        s = self.sim
        v = s.dmm_v()
        if v is None:
            return
        self.rows.append((s.stage, s.phi, v))
        self.tv.insert("", "end", values=(f"{s.stage:+.1f}", f"{s.phi:.0f}",
                                          f"{v:.3f}"))
        self.tv.yview_moveto(1.0)

    def export(self):
        if not self.rows:
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv",
                                         initialfile="ipho2023_Q2_notebook.csv")
        if not p:
            return
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("theta_Stage/deg,phi/deg,DMM/V\n")
            for a, b, cv in self.rows:
                fh.write(f"{a:+.1f},{b:.0f},{cv:.3f}\n")

    # ---------------- drawing ----------------
    @staticmethod
    def lam_colour(lam):
        if lam < 380 or lam > 760:
            return "#101010"
        if lam < 440:
            r, g, b = -(lam - 440) / 60.0, 0.0, 1.0
        elif lam < 490:
            r, g, b = 0.0, (lam - 440) / 50.0, 1.0
        elif lam < 510:
            r, g, b = 0.0, 1.0, -(lam - 510) / 20.0
        elif lam < 580:
            r, g, b = (lam - 510) / 70.0, 1.0, 0.0
        elif lam < 645:
            r, g, b = 1.0, -(lam - 645) / 65.0, 0.0
        else:
            r, g, b = 1.0, 0.0, 0.0
        f = 1.0
        if lam < 420:
            f = 0.3 + 0.7 * (lam - 380) / 40.0
        elif lam > 700:
            f = 0.3 + 0.7 * (760 - lam) / 60.0
        return "#%02x%02x%02x" % tuple(min(255, int(255 * (v * f) ** 0.8))
                                       for v in (r, g, b))

    def draw(self):
        c = self.c
        s = self.sim
        cx, cy, R = self.CX, self.CY, self.R
        c.delete("all")
        c.create_text(360, 16, font=("", 9), fill="#95a5a6", text=T(
            "스테이지·레일·P2를 마우스로 돌리세요 (휠 = 미세 조정)",
            "turn the stage, the rails and P2 with the mouse "
            "(wheel = fine step)"))

        def on_rail(ang, dist):
            rad = math.radians(ang - 90)
            return cx + dist * math.cos(rad), cy + dist * math.sin(rad)

        for key, ang, dist in (("srail", s.short_rail, 215),
                               ("lrail", s.long_rail, 235)):
            if key not in s.obj:
                continue
            x2, y2 = on_rail(ang, dist)
            c.create_line(cx, cy, x2, y2, fill=MDF_L, width=9)
            xm, ym = on_rail(ang, dist + 16)
            c.create_text(xm, ym, font=("", 8), fill="#7f8c8d",
                          text=T("짧은 레일", "short rail") if key == "srail"
                          else T("긴 레일", "long rail"))
        if s.led_on and s.slit_on_led and s.grating_on_stage:
            xa, ya = on_rail(s.short_rail, 190)
            c.create_line(xa, ya, cx, cy, fill="#fffdf0", width=4)
            if "lrail" in s.obj:
                xb, yb = on_rail(s.long_rail, 215)
                c.create_line(cx, cy, xb, yb,
                              fill=self.lam_colour(s.lam_nm()), width=4)
        for key, rail in (("led", "srail"), ("L1", "srail"), ("P1", "lrail"),
                          ("quartz", "lrail"), ("P2", "lrail"),
                          ("L2", "lrail"), ("PD", "lrail")):
            if not s.on(key, rail):
                continue
            base = SR_X0 if rail == "srail" else LR_X0
            dist = 60 + (s.x(key) - base) * 0.42
            ang = s.short_rail if rail == "srail" else s.long_rail
            x, y = on_rail(ang, dist)
            c.create_rectangle(x - 7, y - 7, x + 7, y + 7, fill=WHITE_P,
                               outline="#7f8c8d")
            c.create_text(x + 15, y - 12, text=key.upper().replace("QUARTZ", "Q"),
                          font=("", 7, "bold"), fill="#dfe6e9")

        if "stage" in s.obj:
            d_stage_top(c, cx, cy, R, s.stage)
            if s.grating_on_stage:
                rad = math.radians(-s.stage - 90)
                c.create_line(cx - 32 * math.sin(rad), cy + 32 * math.cos(rad),
                              cx + 32 * math.sin(rad), cy - 32 * math.cos(rad),
                              fill="#3b4046", width=6)
        else:
            c.create_oval(cx - R, cy - R, cx + R, cy + R, outline="#4d5b66",
                          dash=(4, 4))
            c.create_text(cx, cy, text=T("회전 스테이지 없음",
                                         "no rotation stage"),
                          fill="#7f8c8d", font=("", 9))

        # ---- readouts ----------------------------------------------------
        c.create_rectangle(20, 400, 740, 690, fill="#12161a", outline="#3d444d")
        y = 432
        c.create_text(44, y, anchor="w", font=("Consolas", 13), fill="#dfe6e9",
                      text=(T("스테이지 눈금  θ_Stage = %+.1f°",
                              "stage readout  theta_Stage = %+.1f deg") % s.stage)
                      if "stage" in s.obj else
                      T("회전 스테이지 미설치", "rotation stage not installed"))
        y += 26
        c.create_text(44, y, anchor="w", font=("Consolas", 11), fill="#95a5a6",
                      text=T("짧은 레일 %.1f°    긴 레일 %.1f°",
                             "short rail %.1f deg    long rail %.1f deg")
                      % (s.short_rail, s.long_rail))
        y += 30
        c.create_text(44, y, anchor="w", font=("", 10), fill="#95a5a6",
                      text=T("슬릿으로 되돌아오는 반사광",
                             "light reflected back into the slit"))
        c.create_rectangle(280, y - 9, 450, y + 9, outline="#4d5b66")
        c.create_rectangle(280, y - 9, 280 + 170 * s.retro(), y + 9,
                           fill="#f1c40f", outline="")
        # P2 dial
        if s.on("P2"):
            px, py, pr = self.P2X, self.P2Y, self.P2R
            c.create_oval(px - pr, py - pr, px + pr, py + pr, fill="#e9ecef",
                          outline=STEEL_D, width=2)
            for a in range(0, 360, 5):
                rad = math.radians(a - 90)
                ln = 9 if a % 30 == 0 else 4
                c.create_line(px + (pr - ln) * math.cos(rad),
                              py + (pr - ln) * math.sin(rad),
                              px + pr * math.cos(rad), py + pr * math.sin(rad),
                              fill="#6b7075")
                if a % 30 == 0:
                    c.create_text(px + (pr - 18) * math.cos(rad),
                                  py + (pr - 18) * math.sin(rad), text=str(a),
                                  font=("", 6), fill="#5b6068")
            c.create_oval(px - 20, py - 20, px + 20, py + 20, fill="#7c7f83",
                          outline="#5b5e62")
            rad = math.radians(s.phi - 90)
            c.create_line(px, py, px + (pr - 4) * math.cos(rad),
                          py + (pr - 4) * math.sin(rad), fill="#c0392b",
                          width=3)
            c.create_text(px, py + pr + 14, font=("Consolas", 12),
                          fill="#dfe6e9", text="P2  φ = %.0f°" % s.phi)
        else:
            c.create_text(self.P2X, self.P2Y, text=T("P2 미설치",
                                                     "P2 not installed"),
                          fill="#7f8c8d", font=("", 10))
        v = s.dmm_v()
        d_dmm(c, 44, 528, 1.0, reading=v)
        c.create_text(92, 518, text="DMM  DCV", font=("", 9), fill="#95a5a6")
        # no verdict on the alignment: the DMM, the screen and the light
        # sent back into the slit are what tell the student how it is going
        if s.screen_blocks():
            c.create_text(160, 546, anchor="w", font=("", 9), fill="#95a5a6",
                          text=T("눈금자 조립체가 빔 안에 서 있습니다",
                                 "the scale assembly stands in the beam"))


# =====================================================================
#  5.  APP
# =====================================================================
class App:
    def __init__(self, root, seed=None):
        self.root = root
        root.title(T("IPhO 2023 Q2 복굴절 두께 측정 - 가상 실험실",
                     "IPhO 2023 Q2 Birefringence - Virtual Lab"))
        self.sim = Biref(seed)
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        self.bench = BenchTab(nb, self)
        self.stage = StageTab(nb, self)
        nb.add(self.bench.frame, text=T("1. 실험대 (옆에서 본 모습)",
                                        "1. Bench (side view)"))
        nb.add(self.stage.frame, text=T("2. 회전 스테이지 (위에서 본 모습)",
                                        "2. Stage (top view)"))
        nb.bind("<<NotebookTabChanged>>", self._sync)
        self.nb = nb

    def _sync(self, _=None):
        try:
            if self.nb.index(self.nb.select()) == 0:
                self.bench.draw()
            else:
                self.stage.draw()
        except Exception:
            pass


def main():
    if not HAS_TK:
        print("tkinter is required")
        return 1
    root = tk.Tk()
    _setup_hangul_font(root)
    root.geometry("1180x800")
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
