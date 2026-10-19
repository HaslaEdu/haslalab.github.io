#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  6th European Physics Olympiad  (EuPhO 2022, Ljubljana, Slovenia)
  Experimental Problem E :  PHYSICS OF ILLUMINATION
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Apparatus rebuilt from the photographs of the problem sheet: the
    work mat with its angle and distance grid, the light stand with the
    incandescent and LED modules, the TENMA bench supply, the light
    meter with its red, green and blue filters, the black and white
    plastic plates, the infrared thermometer and the protractor.
    Task 1 colour and temperature, Task 2 luminous efficacy, Task 3
    radiative heating.  Only what a real instrument shows is displayed:
    the supply's current and voltage, the light meter, the infrared
    thermometer, the grid on the mat.  No temperature, flux, efficacy or
    heat transfer coefficient is ever computed.
    Every hidden true parameter is randomised for each session.

    Run:   python3 eupho2022_E1_sim_KO.py   [--seed N] [--lang ko|en]
"""
import math
import random
import sys
import time
import tkinter as tk
from tkinter import ttk, font as tkfont

VERSION = "1.0"
APP_ID = "eupho2022_e"

# --------------------------------------------------------------------------
# bilingual wrapper
# --------------------------------------------------------------------------
LANG = "KO"          # the EN edition differs only in this line


def T(ko, en):          # retained for API compatibility
    return ko if LANG == "KO" else en


# --------------------------------------------------------------------------
# physical constants
# --------------------------------------------------------------------------
H_PLANCK = 6.62607015e-34
C_LIGHT = 2.99792458e8
K_BOLTZ = 1.380649e-23

KELVIN0 = 273.15

# --------------------------------------------------------------------------
# Combined spectral response of (tungsten black body) x (colour filter) x
# (light meter photopic response), expressed as the fraction of the
# *unfiltered* illuminance that passes each filter, tabulated versus filament
# temperature.  Derived from a Planck / photopic model whose filter passbands
# were calibrated against the reference illuminance table supplied with the
# problem (Table 1).  Values are dimensionless fractions in [0,1].
# --------------------------------------------------------------------------
_RHO_T0=900
_RHO_DT=20
_RHO_R=(0.59826,0.589617,0.581149,0.572861,0.564755,0.556833,0.549094,0.541539,0.534165,0.526972,0.519956,0.513116,0.506447,0.499947,0.493612,0.487438,0.481422,0.47556,0.469847,0.46428,0.458854,0.453567,0.448414,0.443391,0.438495,0.433721,0.429066,0.424527,0.420101,0.415783,0.411571,0.407461,0.40345,0.399536,0.395715,0.391985,0.388342,0.384785,0.38131,0.377916,0.374599,0.371357,0.368189,0.365092,0.362063,0.359102,0.356205,0.353371,0.350599,0.347886,0.34523,0.342631,0.340086,0.337594,0.335154,0.332763,0.330421,0.328127,0.325878,0.323674,0.321513,0.319395,0.317318,0.315281,0.313283,0.311323,0.3094,0.307512,0.30566,0.303842,0.302058,0.300306,0.298585,0.296895,0.295236,0.293606,0.292004,0.29043,0.288883,0.287363,0.285869,0.2844,0.282956,0.281536,0.28014,0.278766,0.277415,0.276086,0.274779,0.273492,0.272226,0.27098,0.269753,0.268546,0.267357,0.266187,0.265034,0.2639,0.262782,0.261681,0.260596)
_RHO_G=(0.00344452,0.00416951,0.00500357,0.00595603,0.00703623,0.00825341,0.00961671,0.0111351,0.0128172,0.0146715,0.0167062,0.0189289,0.0213472,0.0239678,0.0267975,0.0298423,0.0331078,0.0365993,0.0403215,0.0442786,0.0484744,0.0529123,0.057595,0.0625252,0.0677047,0.0731351,0.0788177,0.0847531,0.0909417,0.0973837,0.104079,0.111026,0.118224,0.125673,0.133371,0.141315,0.149503,0.157935,0.166606,0.175515,0.184658,0.194032,0.203635,0.213462,0.223511,0.232414,0.239047,0.243829,0.247205,0.249624,0.251508,0.25325,0.255204,0.257624,0.260462,0.263606,0.266956,0.270415,0.273896,0.277316,0.280596,0.283666,0.286457,0.28891,0.290987,0.292722,0.294166,0.295367,0.29637,0.297382,0.299253,0.302871,0.30772,0.312018,0.315143,0.317631,0.319879,0.322105,0.324504,0.327327,0.331063,0.336248,0.343413,0.351782,0.360213,0.368705,0.377256,0.385864,0.394528,0.403246,0.412016,0.420837,0.429708,0.438626,0.447591,0.4566,0.465652,0.474746,0.483881,0.493054,0.502265)
_RHO_B=(4.98016e-08,9.31682e-08,1.69623e-07,3.01053e-07,5.21705e-07,8.8402e-07,1.46668e-06,2.38548e-06,3.80788e-06,5.97192e-06,9.21066e-06,1.39833e-05,2.09138e-05,3.08392e-05,4.48681e-05,6.44514e-05,9.14668e-05,0.000128318,0.000178053,0.000244496,0.000332408,0.000447655,0.000597418,0.000790406,0.00103711,0.00135009,0.00174424,0.00223717,0.0028495,0.00360529,0.00453245,0.00566314,0.00703427,0.00868796,0.0106721,0.0130407,0.0158549,0.0191829,0.023101,0.0276941,0.0330564,0.0392917,0.0465144,0.05485,0.0644355,0.0738904,0.0815342,0.0873056,0.091402,0.0941849,0.0960937,0.0975842,0.0990959,0.100963,0.103188,0.105698,0.108426,0.111304,0.114268,0.117254,0.120199,0.123041,0.12572,0.128177,0.130371,0.132313,0.13403,0.135547,0.136889,0.138157,0.139744,0.142073,0.144955,0.147643,0.149811,0.151575,0.153065,0.154409,0.155725,0.157214,0.159414,0.162937,0.168412,0.175168,0.182079,0.189147,0.196372,0.203754,0.211291,0.218986,0.226836,0.234843,0.243005,0.251323,0.259795,0.268423,0.277204,0.286139,0.295227,0.304468,0.313861)


def rho_filter(idx, Tk):
    """Fraction of the unfiltered illuminance transmitted by filter idx
    (0=red, 1=green, 2=blue) for a black body of temperature Tk [K]."""
    tab = (_RHO_R, _RHO_G, _RHO_B)[idx]
    x = (Tk - _RHO_T0) / float(_RHO_DT)
    if x <= 0:
        return tab[0]
    n = len(tab) - 1
    if x >= n:
        return tab[n]
    i = int(x)
    f = x - i
    return tab[i] * (1.0 - f) + tab[i + 1] * f


# --------------------------------------------------------------------------
# hidden per-session apparatus parameters
# --------------------------------------------------------------------------
class Truth(object):
    """Hidden true parameters of this particular set of apparatus.

    Nothing in this object is ever displayed by the program.
    """

    def __init__(self, seed):
        self.seed = int(seed)
        r = random.Random(self.seed ^ 0x45755068)
        self.rng = r

        # ---- incandescent lamp -------------------------------------------
        # filament temperature law  T = K_T * P**(1/4)  (Stefan-Boltzmann),
        # regularised at low power by the ambient term.
        self.K_T = r.uniform(1205.0, 1235.0)          # K W^-1/4
        self.P_at_12V = r.uniform(19.6, 21.4)          # W reached at 12.00 V
        self.T_ref = self.K_T * self.P_at_12V ** 0.25
        self.R_ref = 144.0 / self.P_at_12V             # ohm at T_ref
        self.R_exp = r.uniform(1.16, 1.24)             # tungsten rho ~ T^1.2
        self.bulb_Vmax = 12.0
        self.bulb_burn_V = r.uniform(13.6, 15.2)       # destroyed above this

        # ---- LED ----------------------------------------------------------
        self.led_nVt = r.uniform(0.086, 0.096)         # V
        self.led_Rs = r.uniform(0.80, 1.05)            # ohm
        self.led_Vmax = 3.0
        self.led_Imax = 0.400
        self.led_burn_V = r.uniform(3.35, 3.70)
        self.led_burn_I = r.uniform(0.46, 0.55)
        # I_s chosen so that V(I_max) = 3.00 V
        self.led_Is = self.led_Imax * math.exp(
            -(3.00 - self.led_Imax * self.led_Rs) / self.led_nVt)

        # ---- luminous output ---------------------------------------------
        # bulb : Phi = m * P * ln(1+exp(k1*P - k0))
        self.w_k1 = 1.189 * r.uniform(0.996, 1.004)
        self.w_k0 = 4.632 * r.uniform(0.996, 1.004)
        self.w_scale = r.uniform(0.975, 1.025)
        # LED : Phi = m * (a1*P - a2*P^2)
        self.l_a1 = 259.56 * r.uniform(0.98, 1.02)
        self.l_a2 = 23.78 * r.uniform(0.95, 1.05)
        self.l_scale = r.uniform(0.97, 1.03)

        # ---- angular distribution ----------------------------------------
        self.C_W = r.uniform(9.80, 10.22)
        self.C_L = r.uniform(2.86, 3.14)
        self.wp_s, self.wp_n = 0.50, 3.50
        self.lp_s, self.lp_n = 0.50, 2.60
        self.wp_th = _solve_half_angle(self.wp_s, self.wp_n, self.C_W, True)
        self.lp_th = _solve_half_angle(self.lp_s, self.lp_n, self.C_L, False)
        # small angular misalignment of the modules in their holder
        self.w_axis_off = math.radians(r.uniform(-3.0, 3.0))
        self.l_axis_off = math.radians(r.uniform(-3.0, 3.0))
        # finite source size (near field breakdown of the inverse square law)
        self.w_size = r.uniform(0.010, 0.014)          # m
        self.l_size = r.uniform(0.003, 0.006)          # m

        # ---- environment --------------------------------------------------
        self.T0 = r.uniform(21.0, 25.5)                # deg C, effective
        self.background_lx = r.uniform(0.4, 3.2)       # stray room light
        self.ir_offset = r.uniform(-4.0, 4.0)          # constant systematic
        self.ir_noise = r.uniform(0.10, 0.20)
        self.meter_cal = r.uniform(0.968, 1.032)       # meter calibration
        self.meter_noise = r.uniform(0.0025, 0.0050)
        self.psu_i_offset = r.uniform(0.0032, 0.0048)  # ammeter under-reads
        self.psu_v_noise = 0.0025
        self.psu_i_noise = 0.00035

        # ---- plates -------------------------------------------------------
        self.h_black = r.uniform(10.6, 12.9)           # W m^-2 K^-1
        self.lam_black = r.uniform(0.0655, 0.0765)     # W m^-1 K^-1
        self.plate_d = 0.0030                          # m
        self.albedo = r.uniform(0.665, 0.735)
        self.h_conv_nl = r.uniform(0.0006, 0.0013)     # weak nonlinearity /K
        self.plate_rho_c = r.uniform(1.55e6, 1.95e6)   # J m^-3 K^-1

        # filters : the same standard filter set used for the reference table,
        # only a fraction of a percent of unit-to-unit spread.
        self.filt_gain = [r.uniform(0.997, 1.003) for _ in range(3)]

    # ------------------------------------------------------------------
    def bulb_temperature(self, P):
        """Filament temperature [K] for true electrical power P [W]."""
        Tamb = self.T0 + KELVIN0
        return (Tamb ** 4 + (self.K_T ** 4) * max(P, 0.0)) ** 0.25

    def bulb_resistance(self, Tk):
        return self.R_ref * (Tk / self.T_ref) ** self.R_exp

    def bulb_flux(self, P):
        """Luminous flux [lm] of the incandescent lamp at true power P [W]."""
        if P <= 0.0:
            return 0.0
        x = self.w_k1 * P - self.w_k0
        if x > 60.0:
            eta = x
        else:
            eta = math.log1p(math.exp(x))
        return self.w_scale * P * eta

    def led_flux(self, P):
        if P <= 0.0:
            return 0.0
        return max(0.0, self.l_scale * (self.l_a1 * P - self.l_a2 * P * P))

    def led_voltage(self, I):
        if I <= 0.0:
            return 0.0
        return self.led_nVt * math.log(1.0 + I / self.led_Is) + I * self.led_Rs

    # ------------------------------------------------------------------
    def profile(self, source, theta):
        """Relative luminous intensity E(theta)/E(0)."""
        th = abs(theta)
        if th >= math.pi / 2:
            return 0.0
        if source == "bulb":
            s, n, t0 = self.wp_s, self.wp_n, self.wp_th
        else:
            s, n, t0 = self.lp_s, self.lp_n, self.lp_th
        c = math.cos(th)
        if c <= 0.0:
            return 0.0
        return (c ** s) * math.exp(-math.log(2.0) * (th / t0) ** n)

    def C_factor(self, source):
        return self.C_W if source == "bulb" else self.C_L

    def source_size(self, source):
        return self.w_size if source == "bulb" else self.l_size


def _profile_fn(s, n, th):
    def g(t):
        c = math.cos(t)
        if c <= 0.0:
            return 0.0
        return (c ** s) * math.exp(-math.log(2.0) * (t / th) ** n)
    return g


def _integrate(f, a, b, n=1200):
    h = (b - a) / n
    tot = 0.5 * (f(a) + f(b))
    for i in range(1, n):
        tot += f(a + i * h)
    return tot * h


def _C_of(s, n, th, is_bulb):
    g = _profile_fn(s, n, th)
    if is_bulb:
        return 4.0 * math.pi * _integrate(lambda t: g(t) * math.cos(t),
                                          0.0, math.pi / 2)
    return 2.0 * math.pi * _integrate(lambda t: g(t) * math.sin(t),
                                      0.0, math.pi / 2)


def _solve_half_angle(s, n, target, is_bulb):
    lo, hi = 0.15, 3.0
    for _ in range(70):
        mid = 0.5 * (lo + hi)
        if _C_of(s, n, mid, is_bulb) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)

# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------
def _norm_angle(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


def _seg_cross(p, q, a, b):
    """True if segment p-q crosses segment a-b."""
    def cr(o, u, v):
        return (u[0] - o[0]) * (v[1] - o[1]) - (u[1] - o[1]) * (v[0] - o[0])
    d1 = cr(a, b, p)
    d2 = cr(a, b, q)
    d3 = cr(p, q, a)
    d4 = cr(p, q, b)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


# --------------------------------------------------------------------------
# apparatus items placed on the bench
# --------------------------------------------------------------------------
class Item(object):
    def __init__(self, kind, x=0.0, y=0.0, heading=0.0):
        self.kind = kind
        self.x = x
        self.y = y
        self.heading = heading      # rad, direction the item faces


PART_LIST = [
    # id, needs (list of part ids), unique
    ("mat", []),
    ("stand", ["mat"]),
    ("weight", ["stand"]),
    ("module_bulb", ["stand"]),
    ("module_led", ["stand"]),
    ("toothpick", ["stand"]),
    ("psu", ["mat"]),
    ("wires", ["psu", "stand"]),
    ("meter", ["mat"]),
    ("meter_stand", ["meter"]),
    ("plate_black", ["mat"]),
    ("plate_white", ["mat"]),
    ("ir", ["mat"]),
    ("filter_r", ["meter"]),
    ("filter_g", ["meter"]),
    ("filter_b", ["meter"]),
    ("protractor", ["mat"]),
]
PART_NEEDS = dict(PART_LIST)


def part_name(pid):
    return {
        "mat": T('작업 매트 (E)', 'Work mat (E)'),
        "stand": T('조명 거치대 (C)', 'Light stand (C)'),
        "weight": T('안정용 추 (C)', 'Weight (C)'),
        "module_bulb": T('백열전구 모듈 (C)', 'Incandescent bulb module (C)'),
        "module_led": T('LED 모듈 (C)', 'LED module (C)'),
        "toothpick": T('이쑤시개 (C)', 'Toothpicks (C)'),
        "psu": T('전원 공급기 (H)', 'Power supply (H)'),
        "wires": T('전선 (빨강/검정)', 'Wires (red/black)'),
        "meter": T('조도계 (B)', 'Light meter (B)'),
        "meter_stand": T('조도계 받침대 (B)', 'Light meter stand (B)'),
        "plate_black": T('검정 플라스틱 판 (A)', 'Black plastic plate (A)'),
        "plate_white": T('흰색 플라스틱 판 (A)', 'White plastic plate (A)'),
        "ir": T('적외선 온도계 (D)', 'Infrared thermometer (D)'),
        "filter_r": T('빨강 필터 (G)', 'Red filter (G)'),
        "filter_g": T('초록 필터 (G)', 'Green filter (G)'),
        "filter_b": T('파랑 필터 (G)', 'Blue filter (G)'),
        "protractor": T('각도기 (F)', 'Protractor (F)'),
    }[pid]


# --------------------------------------------------------------------------
# the rig : complete state of the experiment
# --------------------------------------------------------------------------
class Rig(object):

    PLATE_RADIUS = 0.025          # m (disc)
    PLATE_THICK = 0.0030          # m

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1, 10 ** 9)
        self.seed = int(seed)
        self.truth = Truth(self.seed)
        self.rng = random.Random(self.seed ^ 0x5F3759DF)

        self.placed = set()
        self.items = {}
        self.log = []

        # --- power supply -------------------------------------------------
        self.psu_on = False
        self.v_limit = 30.00
        self.i_limit = 0.000
        self.v_true = 0.0
        self.i_true = 0.0
        self.mode = "CV"
        self._v_shown = 0.0
        self._i_shown = 0.0

        # --- light meter --------------------------------------------------
        self.meter_on = False
        self.meter_hold = False
        self.meter_unit = "lx"
        self.meter_held_value = 0.0
        self.meter_last_touch = 0.0
        self.meter_filter = None          # None | 0 | 1 | 2

        # --- infrared thermometer -----------------------------------------
        self.ir_target = None             # ('plate_black','front') etc.
        self.ir_reading = None

        # --- consumables --------------------------------------------------
        self.spare_bulb = 2
        self.spare_led = 2
        self.bulb_dead = False
        self.led_dead = False
        self.filter_burnt = [False, False, False]

        # --- thermal state --------------------------------------------------
        self.tf = {"plate_black": self.truth.T0, "plate_white": self.truth.T0}
        self.tb = {"plate_black": self.truth.T0, "plate_white": self.truth.T0}

        self.sim_time = 0.0
        self.speed = 10.0

    # ==================================================================
    # assembly
    # ==================================================================
    def can_place(self, pid):
        if pid in self.placed:
            return False, T('이미 배치되어 있다.', 'Already placed.')
        if pid == "module_bulb" and "module_led" in self.placed:
            return False, T('거치대에는 광원 모듈을 하나만 끼울 수 있다.', 'Only one light module fits the stand.')
        if pid == "module_led" and "module_bulb" in self.placed:
            return False, T('거치대에는 광원 모듈을 하나만 끼울 수 있다.', 'Only one light module fits the stand.')
        if pid.startswith("filter_"):
            others = [p for p in ("filter_r", "filter_g", "filter_b")
                      if p in self.placed]
            if others:
                return False, T('조도계 위에는 필터를 하나만 올릴 수 있다.', 'Only one filter fits on the light meter.')
        for need in PART_NEEDS[pid]:
            if need not in self.placed:
                return False, T('먼저 %s 을(를) 배치해야 한다.', 'Place the %s first.') % part_name(need)
        if pid == "wires":
            if not ("module_bulb" in self.placed or "module_led" in self.placed):
                return False, T('먼저 광원 모듈을 거치대에 끼워야 한다.', 'Put a light module in the stand first.')
        return True, ""

    def place(self, pid, x=None, y=None, heading=None):
        ok, why = self.can_place(pid)
        if not ok:
            return False, why
        defaults = {
            "mat": (0.0, 0.0, 0.0),
            "stand": (0.0, 0.0, 0.0),
            "psu": (0.355, 0.235, 0.0),
            "meter": (0.15, 0.0, math.pi),
            "plate_black": (0.115, -0.150, math.pi),
            "plate_white": (0.150, -0.235, math.pi),
            "ir": (-0.055, -0.255, 0.0),
            "protractor": (-0.055, 0.215, 0.0),
        }
        if pid in defaults:
            dx, dy, dh = defaults[pid]
            self.items[pid] = Item(pid,
                                   dx if x is None else x,
                                   dy if y is None else y,
                                   dh if heading is None else heading)
        self.placed.add(pid)
        if pid == "wires":
            self._hot_plug_check()
        return True, ""

    def remove(self, pid):
        if pid not in self.placed:
            return False
        for other, needs in PART_LIST:
            if other in self.placed and pid in needs:
                self.remove(other)
        self.placed.discard(pid)
        self.items.pop(pid, None)
        if pid.startswith("filter_"):
            self.meter_filter = None
        return True

    def assembly_complete(self):
        need = ("mat", "stand", "psu", "wires")
        if not all(p in self.placed for p in need):
            return False
        if not ("module_bulb" in self.placed or "module_led" in self.placed):
            return False
        if not ("meter" in self.placed or "ir" in self.placed):
            return False
        return True

    def missing_for_bench(self):
        miss = []
        for p in ("mat", "stand", "psu", "wires"):
            if p not in self.placed:
                miss.append(part_name(p))
        if not ("module_bulb" in self.placed or "module_led" in self.placed):
            miss.append(T('광원 모듈', 'light module'))
        if not ("meter" in self.placed or "ir" in self.placed):
            miss.append(T('계측기(조도계 또는 적외선 온도계)', 'an instrument (light meter or infrared thermometer)'))
        return miss

    # ==================================================================
    # source
    # ==================================================================
    def source(self):
        if "module_bulb" in self.placed:
            return "bulb"
        if "module_led" in self.placed:
            return "led"
        return None

    def source_dead(self):
        s = self.source()
        if s == "bulb":
            return self.bulb_dead
        if s == "led":
            return self.led_dead
        return False

    def replace_source(self):
        s = self.source()
        if s == "bulb" and self.bulb_dead and self.spare_bulb > 0:
            self.spare_bulb -= 1
            self.bulb_dead = False
            return True
        if s == "led" and self.led_dead and self.spare_led > 0:
            self.spare_led -= 1
            self.led_dead = False
            return True
        return False

    def _hot_plug_check(self):
        """Connecting the leads while the supply is live can destroy the lamp."""
        if not self.psu_on:
            return
        s = self.source()
        if s is None:
            return
        vmax = self.truth.bulb_burn_V if s == "bulb" else self.truth.led_burn_V
        if self.v_limit > vmax and self.i_limit > 0.02:
            self._kill_source()

    def _kill_source(self):
        s = self.source()
        if s == "bulb":
            self.bulb_dead = True
        elif s == "led":
            self.led_dead = True

    # ==================================================================
    # electrical solution
    # ==================================================================
    def _solve_bulb(self, vlim, ilim):
        tr = self.truth

        def v_of_i(I):
            if I <= 0:
                return 0.0
            V = max(I * tr.bulb_resistance(tr.T0 + KELVIN0), 1e-6)
            for _ in range(60):
                Tk = tr.bulb_temperature(V * I)
                Vn = I * tr.bulb_resistance(Tk)
                if abs(Vn - V) < 1e-9:
                    V = Vn
                    break
                V = 0.5 * (V + Vn)
            return V

        if ilim <= 0.0:
            return 0.0, 0.0, "CC"
        if v_of_i(ilim) <= vlim:
            return v_of_i(ilim), ilim, "CC"
        lo, hi = 0.0, ilim
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if v_of_i(mid) < vlim:
                lo = mid
            else:
                hi = mid
        I = 0.5 * (lo + hi)
        return v_of_i(I), I, "CV"

    def _solve_led(self, vlim, ilim):
        tr = self.truth
        if ilim <= 0.0:
            return 0.0, 0.0, "CC"
        if tr.led_voltage(ilim) <= vlim:
            return tr.led_voltage(ilim), ilim, "CC"
        lo, hi = 0.0, ilim
        for _ in range(90):
            mid = 0.5 * (lo + hi)
            if tr.led_voltage(mid) < vlim:
                lo = mid
            else:
                hi = mid
        I = 0.5 * (lo + hi)
        return tr.led_voltage(I), I, "CV"

    def _update_electrical(self):
        s = self.source()
        connected = ("wires" in self.placed) and (s is not None) \
            and (not self.source_dead()) and self.psu_on
        if not connected:
            self.v_true = self.v_limit if self.psu_on else 0.0
            self.i_true = 0.0
            self.mode = "CV" if self.psu_on else "CV"
            return
        if s == "bulb":
            v, i, m = self._solve_bulb(self.v_limit, self.i_limit)
            if v > self.truth.bulb_burn_V:
                self._kill_source()
                self.v_true, self.i_true, self.mode = self.v_limit, 0.0, "CV"
                return
        else:
            v, i, m = self._solve_led(self.v_limit, self.i_limit)
            if v > self.truth.led_burn_V or i > self.truth.led_burn_I:
                self._kill_source()
                self.v_true, self.i_true, self.mode = self.v_limit, 0.0, "CV"
                return
        self.v_true, self.i_true, self.mode = v, i, m

    def power(self):
        """True electrical power dissipated in the lamp [W]."""
        return self.v_true * self.i_true

    def flux(self):
        s = self.source()
        if s is None or self.source_dead():
            return 0.0
        P = self.power()
        return self.truth.bulb_flux(P) if s == "bulb" else self.truth.led_flux(P)

    # ==================================================================
    # optics
    # ==================================================================
    def _source_pos(self):
        it = self.items.get("stand")
        if it is None:
            return None
        return (it.x, it.y, it.heading)

    def _axis_offset(self):
        s = self.source()
        return self.truth.w_axis_off if s == "bulb" else self.truth.l_axis_off

    def _shadowed(self, px, py):
        sx, sy, _ = self._source_pos()
        for pid in ("plate_black", "plate_white"):
            it = self.items.get(pid)
            if it is None:
                continue
            n = it.heading
            tx, ty = -math.sin(n), math.cos(n)
            a = (it.x + tx * self.PLATE_RADIUS, it.y + ty * self.PLATE_RADIUS)
            b = (it.x - tx * self.PLATE_RADIUS, it.y - ty * self.PLATE_RADIUS)
            if _seg_cross((sx, sy), (px, py), a, b):
                return True
        return False

    def illuminance_at(self, px, py, facing):
        """Illuminance [lx] on a sensor at (px,py) whose normal points along
        `facing`, including the room background."""
        bg = self.truth.background_lx
        sp = self._source_pos()
        s = self.source()
        if sp is None or s is None or self.source_dead():
            return bg
        sx, sy, sh = sp
        dx, dy = px - sx, py - sy
        r2 = dx * dx + dy * dy
        r = math.sqrt(r2)
        if r < 1e-4:
            return bg
        phi = self.flux()
        if phi <= 0.0:
            return bg
        ang_to = math.atan2(dy, dx)
        th_src = _norm_angle(ang_to - sh - self._axis_offset())
        g = self.truth.profile(s, th_src)
        th_in = _norm_angle(math.atan2(-dy, -dx) - facing)
        ci = math.cos(th_in)
        if ci <= 0.0:
            return bg
        if self._shadowed(px, py):
            return bg
        a = self.truth.source_size(s)
        I_axis = phi / self.truth.C_factor(s)
        return bg + I_axis * g * ci / (r2 + a * a)

    def irradiance_on_plate(self, pid):
        """On-axis irradiance [W/m^2] at the centre of the plate front face,
        assuming the lamp converts all electrical power into radiation."""
        it = self.items.get(pid)
        sp = self._source_pos()
        s = self.source()
        if it is None or sp is None or s is None or self.source_dead():
            return 0.0
        P = self.power()
        if P <= 0.0:
            return 0.0
        sx, sy, sh = sp
        dx, dy = it.x - sx, it.y - sy
        r2 = dx * dx + dy * dy
        if r2 < 1e-8:
            return 0.0
        ang_to = math.atan2(dy, dx)
        g = self.truth.profile(s, _norm_angle(ang_to - sh - self._axis_offset()))
        ci = math.cos(_norm_angle(math.atan2(-dy, -dx) - it.heading))
        if ci <= 0.0:
            return 0.0
        a = self.truth.source_size(s)
        return P * g * ci / (self.truth.C_factor(s) * (r2 + a * a))

    # ==================================================================
    # thermal integration
    # ==================================================================
    def _thermal_step(self, dt):
        tr = self.truth
        cap = tr.plate_rho_c * self.PLATE_THICK * 0.5     # J m^-2 K^-1 per node
        for pid in ("plate_black", "plate_white"):
            if pid not in self.placed:
                self.tf[pid] = tr.T0
                self.tb[pid] = tr.T0
                continue
            alb = 0.0 if pid == "plate_black" else tr.albedo
            j = self.irradiance_on_plate(pid) * (1.0 - alb)
            TF, TB = self.tf[pid], self.tb[pid]
            n = max(1, int(dt / 2.0) + 1)
            hstep = dt / n
            k = tr.lam_black / self.PLATE_THICK
            for _ in range(n):
                hF = tr.h_black * (1.0 + tr.h_conv_nl * max(TF - tr.T0, 0.0))
                hB = tr.h_black * (1.0 + tr.h_conv_nl * max(TB - tr.T0, 0.0))
                dF = (j - hF * (TF - tr.T0) - k * (TF - TB)) / cap
                dB = (-hB * (TB - tr.T0) + k * (TF - TB)) / cap
                TF += dF * hstep
                TB += dB * hstep
            self.tf[pid], self.tb[pid] = TF, TB

    # ==================================================================
    # time
    # ==================================================================
    def advance(self, dt_sim):
        if dt_sim <= 0:
            return
        self._update_electrical()
        remaining = dt_sim
        while remaining > 0:
            step = min(remaining, 30.0)
            self._thermal_step(step)
            self.sim_time += step
            remaining -= step
        if self.meter_on and (self.sim_time - self.meter_last_touch) > 360.0:
            self.meter_on = False

    # ==================================================================
    # instrument front panels  (display strings only)
    # ==================================================================
    def psu_set_voltage_limit(self, v):
        self.v_limit = max(0.0, min(30.0, round(v, 2)))
        self._update_electrical()

    def psu_set_current_limit(self, i):
        self.i_limit = max(0.0, min(3.0, round(i, 3)))
        self._update_electrical()

    def psu_set_output(self, on):
        was = self.psu_on
        self.psu_on = bool(on)
        if self.psu_on and not was:
            self._hot_plug_check()
        self._update_electrical()

    def psu_display(self):
        """Returns (current_string, voltage_string, indicator)."""
        if not self.psu_on:
            return ("     ", "     ", "OFF")
        self._update_electrical()
        vn = self.v_true + self.rng.gauss(0.0, self.truth.psu_v_noise)
        ino = max(0.0, self.i_true - self.truth.psu_i_offset) \
            + self.rng.gauss(0.0, self.truth.psu_i_noise)
        ino = max(0.0, ino)
        self._v_shown = vn
        self._i_shown = ino
        return ("%05.3f" % min(ino, 9.999), "%05.2f" % min(vn, 99.99), self.mode)

    def meter_press_power(self):
        self.meter_on = not self.meter_on
        self.meter_last_touch = self.sim_time
        self.meter_hold = False

    def meter_press_hold(self):
        if not self.meter_on:
            return
        self.meter_last_touch = self.sim_time
        if self.meter_hold:
            self.meter_hold = False
        else:
            self.meter_held_value = self._meter_raw()
            self.meter_hold = True

    def meter_press_units(self):
        if not self.meter_on:
            return
        self.meter_last_touch = self.sim_time
        self.meter_unit = "fc" if self.meter_unit == "lx" else "lx"

    def set_meter_filter(self, which):
        """which: None | 0 | 1 | 2  (must correspond to a placed filter)."""
        self.meter_filter = which

    def _meter_raw(self):
        it = self.items.get("meter")
        if it is None:
            return 0.0
        e = self.illuminance_at(it.x, it.y, it.heading)
        f = self.meter_filter
        if f is not None:
            if self.filter_burnt[f]:
                return 0.0
            s = self.source()
            if s == "bulb" and not self.source_dead() and self.power() > 0:
                Tk = self.truth.bulb_temperature(self.power())
                frac = rho_filter(f, Tk) * self.truth.filt_gain[f]
            else:
                frac = (0.055, 0.245, 0.335)[f] * self.truth.filt_gain[f]
            bg = self.truth.background_lx
            e = bg * (0.35, 0.30, 0.25)[f] + (e - bg) * frac
        e *= self.truth.meter_cal
        e *= (1.0 + self.rng.gauss(0.0, self.truth.meter_noise))
        return max(0.0, e)

    @staticmethod
    def _quantise(v):
        if v < 200.0:
            return round(v, 1), "%.1f"
        if v < 2000.0:
            return round(v), "%.0f"
        if v < 20000.0:
            return round(v / 10.0) * 10.0, "%.0f"
        return round(v / 100.0) * 100.0, "%.0f"

    def meter_display(self):
        if not self.meter_on:
            return ""
        v = self.meter_held_value if self.meter_hold else self._meter_raw()
        if self.meter_unit == "fc":
            v = v / 10.7639
        if v >= 200000.0:
            return "OL"
        q, fmt = self._quantise(v)
        return fmt % q

    def meter_unit_text(self):
        return self.meter_unit

    # --- infrared thermometer -----------------------------------------
    def ir_aim(self, target):
        """target: None, ('plate_black','front'|'back'), ('ambient',) ..."""
        self.ir_target = target

    def ir_trigger(self):
        tr = self.truth
        t = self.ir_target
        if t is None:
            self.ir_reading = None
            return
        kind = t[0]
        if kind in ("plate_black", "plate_white"):
            if kind not in self.placed:
                self.ir_reading = None
                return
            temp = self.tf[kind] if t[1] == "front" else self.tb[kind]
        elif kind == "ambient":
            temp = tr.T0 + self.rng.gauss(0.0, 0.25)
        elif kind == "lamp":
            s = self.source()
            if s is None or self.source_dead() or self.power() <= 0:
                temp = tr.T0
            else:
                temp = min(495.0, tr.T0 + 6.0 + 11.0 * self.power())
        else:
            temp = tr.T0
        temp = temp + tr.ir_offset + self.rng.gauss(0.0, tr.ir_noise)
        self.ir_reading = temp

    def ir_display(self):
        if self.ir_reading is None:
            return "---.-"
        v = self.ir_reading
        if v > 500.0:
            return "HI"
        if v < -50.0:
            return "LO"
        return "%.1f" % v

    # ==================================================================
    # placement helpers (bench)
    # ==================================================================
    def move_item(self, pid, x, y):
        it = self.items.get(pid)
        if it is None:
            return
        it.x, it.y = x, y

    def rotate_item(self, pid, dtheta):
        it = self.items.get(pid)
        if it is None:
            return
        it.heading = _norm_angle(it.heading + dtheta)

    def aim_at_source(self, pid):
        it = self.items.get(pid)
        sp = self._source_pos()
        if it is None or sp is None:
            return
        it.heading = math.atan2(sp[1] - it.y, sp[0] - it.x)

    def polar_of(self, pid):
        """Distance [m] and bearing [deg] of an item read off the printed mat.

        The mat carries a 1 cm / 5 cm distance grid and a 2 deg / 10 deg angular
        grid centred on the lamp; this returns what a careful reader obtains.
        """
        it = self.items.get(pid)
        sp = self._source_pos()
        if it is None or sp is None:
            return None
        dx, dy = it.x - sp[0], it.y - sp[1]
        r = math.hypot(dx, dy)
        ang = math.degrees(_norm_angle(math.atan2(dy, dx) - sp[2]))
        return round(r, 3), round(ang, 0)

    def set_polar(self, pid, r, ang_deg):
        sp = self._source_pos()
        it = self.items.get(pid)
        if it is None or sp is None:
            return
        a = sp[2] + math.radians(ang_deg)
        it.x = sp[0] + r * math.cos(a)
        it.y = sp[1] + r * math.sin(a)
        self.aim_at_source(pid)

    def check_filter_heat(self):
        """Filters left close to a hot lamp are destroyed."""
        it = self.items.get("meter")
        sp = self._source_pos()
        if it is None or sp is None or self.meter_filter is None:
            return False
        if self.source() != "bulb" or self.power() < 6.0:
            return False
        r = math.hypot(it.x - sp[0], it.y - sp[1])
        if r < 0.035:
            self.filter_burnt[self.meter_filter] = True
            return True
        return False

# --------------------------------------------------------------------------
# drawing helpers  (all apparatus is drawn from the photograph of the
# EuPhO-2022 equipment set, seen from above unless stated otherwise)
# --------------------------------------------------------------------------
COL_MAT = "#f2ece1"
COL_MAT_EDGE = "#cdc3b2"
COL_GRID = "#c9bda9"
COL_GRID_FINE = "#e0d7c8"
COL_WOOD = "#d9b382"
COL_WOOD_D = "#b08a56"
COL_BRASS = "#c9a227"
COL_METAL = "#b9bec4"
COL_DARK = "#2b2b2b"
COL_PSU_BODY = "#d8d2c4"
COL_PSU_FACE = "#b9ad8f"
COL_LCD = "#0a1c3c"
COL_LCD_TXT = "#7fd0ff"
COL_MLCD = "#b9c8a8"
COL_SEL = "#e2574c"


def _rot(px, py, ang):
    c, s = math.cos(ang), math.sin(ang)
    return px * c - py * s, px * s + py * c


class Painter(object):
    """Draws the bench scene on a canvas with a world->screen transform."""

    def __init__(self, canvas):
        self.cv = canvas
        self.scale = 820.0        # px per metre
        self.ox = 0.155           # world coord at screen centre
        self.oy = 0.010

    # -- transform -----------------------------------------------------
    def w2s(self, x, y):
        w = self.cv.winfo_width() or 800
        h = self.cv.winfo_height() or 600
        return (w * 0.5 + (x - self.ox) * self.scale,
                h * 0.5 - (y - self.oy) * self.scale)

    def s2w(self, sx, sy):
        w = self.cv.winfo_width() or 800
        h = self.cv.winfo_height() or 600
        return (self.ox + (sx - w * 0.5) / self.scale,
                self.oy - (sy - h * 0.5) / self.scale)

    def poly(self, pts, **kw):
        flat = []
        for (x, y) in pts:
            sx, sy = self.w2s(x, y)
            flat += [sx, sy]
        return self.cv.create_polygon(*flat, **kw)

    def line(self, x1, y1, x2, y2, **kw):
        a = self.w2s(x1, y1)
        b = self.w2s(x2, y2)
        return self.cv.create_line(a[0], a[1], b[0], b[1], **kw)

    def circle(self, x, y, r, **kw):
        a = self.w2s(x - r, y + r)
        b = self.w2s(x + r, y - r)
        return self.cv.create_oval(a[0], a[1], b[0], b[1], **kw)

    def arc(self, x, y, r, a0, a1, **kw):
        p = self.w2s(x - r, y + r)
        q = self.w2s(x + r, y - r)
        return self.cv.create_arc(p[0], p[1], q[0], q[1],
                                  start=a0, extent=a1 - a0, **kw)

    def text(self, x, y, s, **kw):
        sx, sy = self.w2s(x, y)
        return self.cv.create_text(sx, sy, text=s, **kw)

    def local(self, it, pts):
        out = []
        for (px, py) in pts:
            rx, ry = _rot(px, py, it.heading)
            out.append((it.x + rx, it.y + ry))
        return out

    # -- items ---------------------------------------------------------
    def draw_mat(self):
        x0, x1, y0, y1 = -0.11, 0.47, -0.33, 0.33
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                  fill=COL_MAT, outline=COL_MAT_EDGE, tags="mat")
        fine = self.scale > 1400
        step = 0.01
        if fine:
            v = math.ceil(x0 / step) * step
            while v < x1:
                self.line(v, y0, v, y1, fill=COL_GRID_FINE, tags="mat")
                v += step
            v = math.ceil(y0 / step) * step
            while v < y1:
                self.line(x0, v, x1, v, fill=COL_GRID_FINE, tags="mat")
                v += step
        for v in (-0.10, -0.05, 0.0, 0.05, 0.10, 0.15, 0.20, 0.25,
                  0.30, 0.35, 0.40, 0.45):
            if x0 <= v <= x1:
                self.line(v, y0, v, y1, fill=COL_GRID, tags="mat")
        for v in (-0.30, -0.25, -0.20, -0.15, -0.10, -0.05, 0.0, 0.05,
                  0.10, 0.15, 0.20, 0.25, 0.30):
            self.line(x0, v, x1, v, fill=COL_GRID, tags="mat")
        # polar grid centred on the mat origin
        rr = 0.01
        while rr <= 0.32 + 1e-9:
            major = abs(rr * 100 - round(rr * 100 / 5) * 5) < 1e-6
            if major or fine:
                self.arc(0, 0, rr, -80, 80,
                         style="arc",
                         outline=COL_GRID if major else COL_GRID_FINE,
                         tags="mat")
            rr += 0.01
        a = -80
        while a <= 80:
            major = (a % 10 == 0)
            if major or fine:
                ar = math.radians(a)
                self.line(0.012 * math.cos(ar), 0.012 * math.sin(ar),
                          0.325 * math.cos(ar), 0.325 * math.sin(ar),
                          fill=COL_GRID if major else COL_GRID_FINE, tags="mat")
            a += 2
        if self.scale > 700:
            for rr in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30):
                self.text(rr * math.cos(math.radians(6)),
                          rr * math.sin(math.radians(6)),
                          "%d cm" % int(rr * 100),
                          fill="#9c8f79", font=("TkDefaultFont", 7), tags="mat")
            for a in (-60, -30, 0, 30, 60):
                ar = math.radians(a)
                self.text(0.335 * math.cos(ar), 0.335 * math.sin(ar),
                          u"%d\u00b0" % a, fill="#9c8f79",
                          font=("TkDefaultFont", 7), tags="mat")

    def draw_stand(self, it, source, dead, lit):
        tag = "item:stand"
        self.circle(it.x, it.y, 0.045, fill=COL_WOOD, outline=COL_WOOD_D,
                    tags=tag)
        self.circle(it.x, it.y, 0.040, fill="", outline=COL_WOOD_D, tags=tag)
        self.poly(self.local(it, [(-0.012, -0.016), (0.012, -0.016),
                                  (0.012, 0.016), (-0.012, 0.016)]),
                  fill=COL_WOOD, outline=COL_WOOD_D, tags=tag)
        if source == "bulb":
            self.poly(self.local(it, [(0.008, -0.026), (0.030, -0.026),
                                      (0.030, 0.026), (0.008, 0.026)]),
                      fill="#efe6d2", outline=COL_WOOD_D, tags=tag)
            for sgn in (-1, 1):
                self.poly(self.local(it, [(0.014, sgn * 0.018),
                                          (0.026, sgn * 0.018),
                                          (0.026, sgn * 0.026),
                                          (0.014, sgn * 0.026)]),
                          fill=COL_BRASS, outline="#8a6f18", tags=tag)
            glass = "#fff2b0" if lit else ("#7a7a7a" if dead else "#dfe4e8")
            self.poly(self.local(it, [(0.0155, -0.017), (0.0245, -0.017),
                                      (0.0245, 0.017), (0.0155, 0.017)]),
                      fill=glass, outline="#8d949a", tags=tag)
            self.line(*(self.local(it, [(0.020, -0.013)])[0] +
                        self.local(it, [(0.020, 0.013)])[0]),
                      fill="#c08a2a" if not lit else "#fff8d0",
                      width=2, tags=tag)
        elif source == "led":
            self.poly(self.local(it, [(0.008, -0.022), (0.026, -0.022),
                                      (0.026, 0.022), (0.008, 0.022)]),
                      fill="#f4f4f0", outline="#9aa0a6", tags=tag)
            self.poly(self.local(it, [(0.012, -0.010), (0.020, -0.010),
                                      (0.020, 0.010), (0.012, 0.010)]),
                      fill="#2c3138", outline="#12151a", tags=tag)
            c = "#fdfde8" if lit else ("#6b6b6b" if dead else "#c8ccd0")
            p = self.local(it, [(0.023, 0.0)])[0]
            self.circle(p[0], p[1], 0.005, fill=c, outline="#8d949a", tags=tag)
        if lit:
            p = self.local(it, [(0.024, 0.0)])[0]
            for rr, col in ((0.030, "#f6e6b4"), (0.022, "#fbeeb8"),
                            (0.014, "#fff6cc")):
                self.circle(p[0], p[1], rr, outline=col, fill="",
                            width=2, tags=tag)

    def draw_meter(self, it, filt):
        tag = "item:meter"
        self.poly(self.local(it, [(-0.030, -0.026), (0.020, -0.026),
                                  (0.020, 0.026), (-0.030, 0.026)]),
                  fill="#e9ecef", outline="#8d949a", tags=tag)
        self.poly(self.local(it, [(-0.026, -0.018), (-0.004, -0.018),
                                  (-0.004, 0.018), (-0.026, 0.018)]),
                  fill=COL_MLCD, outline="#7c8a6c", tags=tag)
        self.poly(self.local(it, [(-0.034, -0.030), (-0.028, -0.030),
                                  (-0.028, 0.030), (-0.034, 0.030)]),
                  fill=COL_WOOD, outline=COL_WOOD_D, tags=tag)
        p = self.local(it, [(0.026, 0.0)])[0]
        self.circle(p[0], p[1], 0.0085, fill="#3a4148", outline="#20262c",
                    tags=tag)
        cols = {0: "#d8433a", 1: "#3aa050", 2: "#3f68c8"}
        self.circle(p[0], p[1], 0.0060,
                    fill=cols.get(filt, "#f2f4f6"), outline="#20262c",
                    tags=tag)

    def draw_plate(self, it, white, tsel):
        tag = "item:" + it.kind
        n = it.heading
        tx, ty = -math.sin(n), math.cos(n)
        R = Rig.PLATE_RADIUS
        fx, fy = math.cos(n) * 0.0016, math.sin(n) * 0.0016
        face = "#f0f0ee" if white else "#232323"
        self.poly([(it.x + tx * R + fx, it.y + ty * R + fy),
                   (it.x - tx * R + fx, it.y - ty * R + fy),
                   (it.x - tx * R - fx, it.y - ty * R - fy),
                   (it.x + tx * R - fx, it.y + ty * R - fy)],
                  fill=face, outline="#5a5a5a", tags=tag)
        self.line(it.x + tx * R + fx * 2.2, it.y + ty * R + fy * 2.2,
                  it.x - tx * R + fx * 2.2, it.y - ty * R + fy * 2.2,
                  fill="#8a8a8a", width=1, tags=tag)
        self.poly([(it.x + tx * 0.020 - fx * 6, it.y + ty * 0.020 - fy * 6),
                   (it.x - tx * 0.020 - fx * 6, it.y - ty * 0.020 - fy * 6),
                   (it.x - tx * 0.014 - fx * 12, it.y - ty * 0.014 - fy * 12),
                   (it.x + tx * 0.014 - fx * 12, it.y + ty * 0.014 - fy * 12)],
                  fill=COL_WOOD, outline=COL_WOOD_D, tags=tag)
        if tsel:
            side = 1.0 if tsel == "front" else -1.0
            self.line(it.x + tx * R + fx * side * 5,
                      it.y + ty * R + fy * side * 5,
                      it.x - tx * R + fx * side * 5,
                      it.y - ty * R + fy * side * 5,
                      fill=COL_SEL, width=3, tags=tag)

    def draw_psu(self, it):
        tag = "item:psu"
        self.poly(self.local(it, [(-0.075, -0.055), (0.075, -0.055),
                                  (0.075, 0.055), (-0.075, 0.055)]),
                  fill=COL_PSU_BODY, outline="#8f8878", tags=tag)
        self.poly(self.local(it, [(-0.075, 0.020), (0.075, 0.020),
                                  (0.075, 0.055), (-0.075, 0.055)]),
                  fill=COL_PSU_FACE, outline="#8f8878", tags=tag)
        for dx in (-0.035, 0.035):
            p = self.local(it, [(dx, -0.010)])[0]
            self.circle(p[0], p[1], 0.013, fill="#e8e4d8", outline="#8f8878",
                        tags=tag)
        for dx, c in ((-0.030, "#3a6fd8"), (0.005, "#c8332a"),
                      (0.030, "#2b2b2b"), (0.055, "#2f9e4f")):
            p = self.local(it, [(dx, -0.040)])[0]
            self.circle(p[0], p[1], 0.007, fill=c, outline="#55503f", tags=tag)
        p = self.local(it, [(0.0, 0.038)])[0]
        self.cv.create_text(*self.w2s(p[0], p[1]), text="TENMA",
                            fill="#4a4535", font=("TkDefaultFont", 7, "bold"),
                            tags=tag)

    def draw_ir(self, it):
        tag = "item:ir"
        self.poly(self.local(it, [(-0.020, -0.022), (0.055, -0.012),
                                  (0.055, 0.012), (-0.020, 0.022)]),
                  fill="#e6e8ea", outline="#8d949a", tags=tag)
        self.poly(self.local(it, [(-0.030, -0.030), (-0.010, -0.024),
                                  (-0.010, 0.024), (-0.030, 0.030)]),
                  fill="#2f3338", outline="#1a1d21", tags=tag)
        p = self.local(it, [(0.056, 0.0)])[0]
        self.circle(p[0], p[1], 0.006, fill="#3a4148", outline="#20262c",
                    tags=tag)

    def draw_protractor(self, it):
        tag = "item:protractor"
        self.arc(it.x, it.y, 0.055, math.degrees(it.heading),
                 math.degrees(it.heading) + 180, style="chord",
                 outline="#7fa8c8", fill="", width=1, tags=tag)
        for a in range(0, 181, 10):
            ar = it.heading + math.radians(a)
            self.line(it.x + 0.048 * math.cos(ar), it.y + 0.048 * math.sin(ar),
                      it.x + 0.055 * math.cos(ar), it.y + 0.055 * math.sin(ar),
                      fill="#7fa8c8", tags=tag)
        self.line(it.x - 0.055 * math.cos(it.heading),
                  it.y - 0.055 * math.sin(it.heading),
                  it.x + 0.055 * math.cos(it.heading),
                  it.y + 0.055 * math.sin(it.heading),
                  fill="#7fa8c8", tags=tag)

    def draw_weight(self, it):
        self.circle(it.x, it.y, 0.012, fill=COL_METAL, outline="#7e858c",
                    tags="item:weight")


# --------------------------------------------------------------------------
# small pictorial icons used by the assembly tab
# --------------------------------------------------------------------------
def draw_icon(cv, pid, cx, cy, s=1.0, tags=""):
    """Miniature line drawing of a part, centred on (cx, cy)."""
    def rect(x0, y0, x1, y1, **kw):
        cv.create_rectangle(cx + x0 * s, cy + y0 * s, cx + x1 * s,
                            cy + y1 * s, tags=tags, **kw)

    def oval(x0, y0, x1, y1, **kw):
        cv.create_oval(cx + x0 * s, cy + y0 * s, cx + x1 * s, cy + y1 * s,
                       tags=tags, **kw)

    def line(x0, y0, x1, y1, **kw):
        cv.create_line(cx + x0 * s, cy + y0 * s, cx + x1 * s, cy + y1 * s,
                       tags=tags, **kw)

    if pid == "mat":
        rect(-16, -11, 16, 11, fill=COL_MAT, outline=COL_MAT_EDGE)
        for k in (-8, 0, 8):
            line(k, -11, k, 11, fill=COL_GRID)
            line(-16, k * 0.7, 16, k * 0.7, fill=COL_GRID)
        cv.create_arc(cx - 26 * s, cy - 10 * s, cx + 6 * s, cy + 22 * s,
                      start=20, extent=60, style="arc", outline="#b09a76",
                      tags=tags)
    elif pid == "stand":
        oval(-14, 4, 14, 12, fill=COL_WOOD, outline=COL_WOOD_D)
        rect(-3, -12, 3, 6, fill=COL_WOOD, outline=COL_WOOD_D)
    elif pid == "weight":
        rect(-6, -8, 6, 8, fill=COL_METAL, outline="#7e858c")
        rect(-6, -8, 6, -4, fill="#8f979e", outline="#7e858c")
    elif pid == "module_bulb":
        rect(-11, -6, 11, 9, fill="#efe6d2", outline=COL_WOOD_D)
        rect(-4, -6, 4, -2, fill=COL_BRASS, outline="#8a6f18")
        oval(-6, -16, 6, -3, fill="#dfe4e8", outline="#8d949a")
        line(0, -13, 0, -6, fill="#c08a2a", width=2)
    elif pid == "module_led":
        rect(-10, -4, 10, 10, fill="#f4f4f0", outline="#9aa0a6")
        rect(-5, -4, 5, 4, fill="#2c3138", outline="#12151a")
        oval(-4, -12, 4, -4, fill="#e8ecef", outline="#8d949a")
    elif pid == "toothpick":
        for k in (-5, 0, 5):
            line(k - 3, -11, k + 3, 11, fill="#c9a86a", width=2)
    elif pid == "psu":
        rect(-16, -11, 16, 11, fill=COL_PSU_BODY, outline="#8f8878")
        rect(-13, -8, -1, -1, fill=COL_LCD, outline="")
        rect(1, -8, 13, -1, fill=COL_LCD, outline="")
        oval(-11, 2, -3, 10, fill="#e8e4d8", outline="#8f8878")
        oval(3, 2, 11, 10, fill="#e8e4d8", outline="#8f8878")
    elif pid == "wires":
        cv.create_line(cx - 15 * s, cy + 8 * s, cx - 4 * s, cy - 8 * s,
                       cx + 6 * s, cy + 6 * s, cx + 15 * s, cy - 6 * s,
                       fill="#c8332a", width=2, smooth=True, tags=tags)
        cv.create_line(cx - 15 * s, cy + 11 * s, cx - 4 * s, cy - 4 * s,
                       cx + 6 * s, cy + 9 * s, cx + 15 * s, cy - 2 * s,
                       fill="#2b2b2b", width=2, smooth=True, tags=tags)
    elif pid == "meter":
        rect(-9, -6, 9, 13, fill="#e9ecef", outline="#8d949a")
        rect(-6, -3, 6, 5, fill=COL_MLCD, outline="#7c8a6c")
        oval(-5, -16, 5, -6, fill="#3a4148", outline="#20262c")
        oval(-3, -14, 3, -8, fill="#f2f4f6", outline="#20262c")
    elif pid == "meter_stand":
        rect(-13, 2, 13, 8, fill=COL_WOOD, outline=COL_WOOD_D)
        rect(-4, -8, 4, 2, fill=COL_WOOD, outline=COL_WOOD_D)
    elif pid in ("plate_black", "plate_white"):
        oval(-11, -14, 11, 8, fill="#f0f0ee" if pid.endswith("white")
             else "#232323", outline="#5a5a5a")
        rect(-1, 6, 1, 14, fill=COL_WOOD, outline=COL_WOOD_D)
        oval(-9, 12, 9, 16, fill=COL_WOOD, outline=COL_WOOD_D)
    elif pid == "ir":
        cv.create_polygon(cx - 14 * s, cy - 6 * s, cx + 8 * s, cy - 8 * s,
                          cx + 14 * s, cy - 4 * s, cx + 14 * s, cy + 2 * s,
                          cx - 6 * s, cy + 4 * s, cx - 8 * s, cy + 14 * s,
                          cx - 14 * s, cy + 14 * s,
                          fill="#e6e8ea", outline="#8d949a", tags=tags)
        oval(12, -4, 17, 2, fill="#3a4148", outline="#20262c")
    elif pid.startswith("filter_"):
        col = {"r": "#d8433a", "g": "#3aa050", "b": "#3f68c8"}[pid[-1]]
        cv.create_polygon(cx - 12 * s, cy - 10 * s, cx + 12 * s, cy - 12 * s,
                          cx + 12 * s, cy + 10 * s, cx - 12 * s, cy + 12 * s,
                          fill=col, outline="#555555", tags=tags)
    elif pid == "protractor":
        cv.create_arc(cx - 15 * s, cy - 8 * s, cx + 15 * s, cy + 22 * s,
                      start=0, extent=180, style="chord", outline="#7fa8c8",
                      fill="#eef4f9", tags=tags)
        for a in range(0, 181, 30):
            import math as _m
            ar = _m.radians(a)
            line(13 * _m.cos(ar), 7 - 13 * _m.sin(ar),
                 15 * _m.cos(ar), 7 - 15 * _m.sin(ar), fill="#7fa8c8")

# --------------------------------------------------------------------------
# assembly tab
# --------------------------------------------------------------------------
BOX_ORDER = ["mat", "stand", "weight", "module_bulb", "module_led",
             "toothpick", "psu", "wires", "meter", "meter_stand",
             "plate_black", "plate_white", "ir",
             "filter_r", "filter_g", "filter_b", "protractor"]


class AssemblyTab(ttk.Frame):

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.rig = app.rig
        self.drag = None

        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Label(left, text=T('부품 상자', 'Parts box'),
                  font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        ttk.Label(left, wraplength=250, foreground="#555",
                  text=T('부품을 오른쪽 작업 공간으로 끌어다 놓아 조립한다.\n배치된 부품을 오른쪽 클릭하면 상자로 되돌아온다.', 'Drag the parts onto the work area on the right.\nRight-click a placed part to put it back in the box.')).pack(anchor="w", pady=(0, 6))
        self.box = tk.Canvas(left, width=290, height=620, bg="#f7f7f5",
                             highlightthickness=1,
                             highlightbackground="#cccccc")
        self.box.pack(fill="y", expand=True)

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T('작업 공간', 'Work area'),
                  font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, bg="#eef0f2", highlightthickness=1,
                            highlightbackground="#cccccc")
        self.cv.pack(fill="both", expand=True)
        self.status = ttk.Label(right, text="", foreground="#a03030",
                                wraplength=760)
        self.status.pack(anchor="w", pady=4)

        self.box.bind("<Button-1>", self.on_box_press)
        self.cv.bind("<ButtonRelease-1>", self.on_drop)
        self.cv.bind("<B1-Motion>", self.on_motion)
        self.cv.bind("<Button-3>", self.on_right)
        self.cv.bind("<Configure>", lambda e: self.redraw())
        self.bind_all("<Motion>", self._track, add="+")
        self.redraw()

    # ------------------------------------------------------------------
    def _track(self, ev):
        if self.drag is None:
            return
        try:
            x = ev.x_root - self.cv.winfo_rootx()
            y = ev.y_root - self.cv.winfo_rooty()
        except Exception:
            return
        self.cv.delete("ghost")
        if 0 <= x <= self.cv.winfo_width() and 0 <= y <= self.cv.winfo_height():
            self.cv.create_rectangle(x - 46, y - 13, x + 46, y + 13,
                                     fill="#ffffff", outline="#7799bb",
                                     tags="ghost")
            self.cv.create_text(x, y, text=part_name(self.drag),
                                font=("TkDefaultFont", 7), tags="ghost")

    def on_box_press(self, ev):
        idx = int(ev.y // 46)
        avail = [p for p in BOX_ORDER if p not in self.rig.placed]
        if 0 <= idx < len(avail):
            self.drag = avail[idx]
            self.status.config(text="")

    def on_motion(self, ev):
        self._track(ev)

    def on_drop(self, ev):
        if self.drag is None:
            return
        pid = self.drag
        self.drag = None
        self.cv.delete("ghost")
        ok, why = self.rig.place(pid)
        self.status.config(text="" if ok else why)
        self.app.refresh_all()

    def on_right(self, ev):
        hit = self._hit(ev.x, ev.y)
        if hit:
            self.rig.remove(hit)
            self.status.config(text="")
            self.app.refresh_all()

    def _slots(self):
        """screen rectangles of the placed parts in the workspace"""
        w = max(self.cv.winfo_width(), 200)
        cols = max(2, min(4, w // 220))
        out = {}
        placed = [p for p in BOX_ORDER if p in self.rig.placed]
        for i, pid in enumerate(placed):
            r, c = divmod(i, cols)
            x0 = 18 + c * 210
            y0 = 18 + r * 86
            out[pid] = (x0, y0, x0 + 194, y0 + 74)
        return out

    def _hit(self, x, y):
        for pid, (a, b, c, d) in self._slots().items():
            if a <= x <= c and b <= y <= d:
                return pid
        return None

    # ------------------------------------------------------------------
    def redraw(self):
        self.box.delete("all")
        avail = [p for p in BOX_ORDER if p not in self.rig.placed]
        for i, pid in enumerate(avail):
            y = i * 46
            self.box.create_rectangle(6, y + 4, 284, y + 44,
                                      fill="#ffffff", outline="#c8ccd0")
            draw_icon(self.box, pid, 30, y + 24, 0.62)
            self.box.create_text(58, y + 24, anchor="w", text=part_name(pid),
                                 font=("TkDefaultFont", 9))
        if not avail:
            self.box.create_text(130, 20, text=T('모든 부품 사용 중', 'All parts in use'),
                                 fill="#888888")

        self.cv.delete("all")
        for pid, (a, b, c, d) in self._slots().items():
            self.cv.create_rectangle(a, b, c, d, fill="#ffffff",
                                     outline="#9fb4c8", width=2)
            draw_icon(self.cv, pid, a + 30, (b + d) / 2, 0.78)
            self.cv.create_text((a + c) / 2 + 20, b + 22, text=part_name(pid),
                                font=("TkDefaultFont", 9, "bold"),
                                width=c - a - 66)
            sub = self._subtitle(pid)
            if sub:
                self.cv.create_text((a + c) / 2 + 20, b + 52, text=sub,
                                    font=("TkDefaultFont", 8),
                                    fill="#5a6570", width=c - a - 66)
        if not self.rig.placed:
            self.cv.create_text(self.cv.winfo_width() // 2 or 300, 200,
                                text=T('부품 상자에서 부품을 끌어와 실험 장치를 조립하라.', 'Drag parts from the box to assemble the apparatus.'),
                                fill="#8a939c")
        miss = self.rig.missing_for_bench()
        if miss:
            self.status.config(
                foreground="#a06030",
                text=T('실험대를 사용하려면 아직 필요함: ', 'Still needed for the bench: ')
                     + ", ".join(miss))
        else:
            self.status.config(foreground="#2f7a3f",
                               text=T("조립 완료 - '실험대' 탭으로 이동하라.", "Assembly complete: go to the 'Bench' tab."))

    def _subtitle(self, pid):
        r = self.rig
        if pid == "psu":
            return T('전압 제한 %.2f V / 전류 제한 %.3f A', 'voltage limit %.2f V / current limit %.3f A') % (r.v_limit, r.i_limit)
        if pid == "module_bulb":
            if r.bulb_dead:
                return T('타버림 - 예비 %d개', 'burnt out - %d spare(s)') % r.spare_bulb
            return T('최대 12 V', '12 V max')
        if pid == "module_led":
            if r.led_dead:
                return T('타버림 - 예비 %d개', 'burnt out - %d spare(s)') % r.spare_led
            return T('최대 3.0 V / 400 mA', '3.0 V / 400 mA max')
        if pid == "wires":
            return T('검정=음극, 빨강=양극', 'black = negative, red = positive')
        if pid.startswith("filter_"):
            i = "rgb".index(pid[-1])
            if r.filter_burnt[i]:
                return T('열로 손상됨', 'damaged by heat')
            return T('조도계 센서 위에 덮는다', 'goes over the light meter sensor')
        return ""

# --------------------------------------------------------------------------
# bench tab
# --------------------------------------------------------------------------
MOVABLE = ("stand", "meter", "plate_black", "plate_white", "psu", "ir",
           "protractor")
HIT_R = {"stand": 0.047, "meter": 0.036, "plate_black": 0.028,
         "plate_white": 0.028, "psu": 0.080, "ir": 0.040,
         "protractor": 0.056}

V_W = (10.0, 1.0, 0.1, 0.01)
I_W = (1.0, 0.1, 0.01, 0.001)


class BenchTab(ttk.Frame):

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.rig = app.rig

        self.pan = None
        self.dragging = None
        self.v_sel = None
        self.i_sel = None
        self.edit_until = 0.0

        wrap = ttk.Frame(self)
        wrap.pack(fill="both", expand=True)

        wrap.columnconfigure(0, weight=1)
        wrap.columnconfigure(1, weight=0, minsize=332)
        wrap.rowconfigure(0, weight=1)
        self.cv = tk.Canvas(wrap, bg="#3f4448", highlightthickness=0)
        self.cv.grid(row=0, column=0, sticky="nsew")
        self.p = Painter(self.cv)

        side = ttk.Frame(wrap, width=332)
        side.grid(row=0, column=1, sticky="ns")
        side.grid_propagate(False)
        self._build_side(side)

        self.cv.bind("<Button-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_drag)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<MouseWheel>", self.on_wheel)
        self.cv.bind("<Button-4>", lambda e: self.on_wheel(e, 120))
        self.cv.bind("<Button-5>", lambda e: self.on_wheel(e, -120))
        self.cv.bind("<Shift-MouseWheel>", lambda e: self.on_wheel(e, None, True))
        self.cv.bind("<Configure>", lambda e: self.redraw_scene())

        self.hint = self.cv.create_text(10, 10, anchor="nw", fill="#c8ced4",
                                        font=("TkDefaultFont", 8), text="")

    # ==================================================================
    def _build_side(self, side):
        nb = ttk.Frame(side)
        nb.pack(fill="both", expand=True, padx=6, pady=6)

        ttk.Label(nb, text=T('전원 공급기 (H)', 'Power supply (H)'),
                  font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.psu_cv = tk.Canvas(nb, width=312, height=186, bg="#e9e6dc",
                                highlightthickness=1,
                                highlightbackground="#b0aa9a")
        self.psu_cv.pack(pady=(2, 8))
        self.psu_cv.bind("<Button-1>", self.on_psu_click)
        self.psu_cv.bind("<MouseWheel>", self.on_psu_wheel)
        self.psu_cv.bind("<Button-4>", lambda e: self.on_psu_wheel(e, 120))
        self.psu_cv.bind("<Button-5>", lambda e: self.on_psu_wheel(e, -120))
        self.psu_cv.bind("<Shift-MouseWheel>",
                         lambda e: self.on_psu_wheel(e, None, True))

        ttk.Label(nb, text=T('조도계 (B)', 'Light meter (B)'),
                  font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.mtr_cv = tk.Canvas(nb, width=312, height=132, bg="#eceef0",
                                highlightthickness=1,
                                highlightbackground="#b0b5ba")
        self.mtr_cv.pack(pady=(2, 2))
        self.mtr_cv.bind("<Button-1>", self.on_meter_click)
        fr = ttk.Frame(nb)
        fr.pack(fill="x", pady=(0, 8))
        ttk.Label(fr, text=T('센서 위 필터:', 'Filter on the sensor:')).pack(
            side="left")
        self.filt_var = tk.StringVar(value="none")
        for key, lab in (("none", T('없음', 'none')), ("r", T('빨강', 'red')),
                         ("g", T('초록', 'green')), ("b", T('파랑', 'blue'))):
            ttk.Radiobutton(fr, text=lab, value=key, variable=self.filt_var,
                            command=self.on_filter).pack(side="left")

        ttk.Label(nb, text=T('적외선 온도계 (D)', 'Infrared thermometer (D)'),
                  font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.ir_cv = tk.Canvas(nb, width=312, height=104, bg="#eceef0",
                               highlightthickness=1,
                               highlightbackground="#b0b5ba")
        self.ir_cv.pack(pady=(2, 2))
        self.ir_cv.bind("<Button-1>", self.on_ir_click)
        self.ir_lab = ttk.Label(nb, text="", foreground="#556",
                                wraplength=300)
        self.ir_lab.pack(anchor="w", pady=(0, 8))

        box = ttk.LabelFrame(nb, text=T('실험 진행', 'Running the experiment'))
        box.pack(fill="x")
        r1 = ttk.Frame(box)
        r1.pack(fill="x", pady=2)
        self.clock_lab = ttk.Label(r1, text="", font=("TkDefaultFont", 9))
        self.clock_lab.pack(side="left")
        ttk.Label(r1, text=T('  배속:', '  speed:')).pack(side="left")
        self.speed_var = tk.StringVar(value="10")
        cb = ttk.Combobox(r1, textvariable=self.speed_var, width=5,
                          state="readonly",
                          values=("1", "5", "10", "30", "60", "180"))
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", self.on_speed)
        r2 = ttk.Frame(box)
        r2.pack(fill="x", pady=2)
        self.spare_lab = ttk.Label(r2, text="")
        self.spare_lab.pack(side="left")
        ttk.Button(r2, text=T('광원 교체', 'Replace light source'),
                   command=self.on_replace).pack(side="right")
        self.warn = ttk.Label(box, text="", foreground="#b03030",
                              wraplength=300)
        self.warn.pack(anchor="w")

    # ==================================================================
    # scene interaction
    # ==================================================================
    def _hit(self, sx, sy):
        wx, wy = self.p.s2w(sx, sy)
        best, bd = None, 1e9
        for pid in MOVABLE:
            it = self.rig.items.get(pid)
            if it is None:
                continue
            d = math.hypot(wx - it.x, wy - it.y)
            if d < HIT_R[pid] and d < bd:
                best, bd = pid, d
        return best, wx, wy

    def on_press(self, ev):
        pid, wx, wy = self._hit(ev.x, ev.y)
        if pid is None:
            self.pan = (ev.x, ev.y, self.p.ox, self.p.oy)
            self.rig.ir_aim(("ambient",))
        else:
            it = self.rig.items[pid]
            self.dragging = (pid, wx - it.x, wy - it.y)
            if pid in ("plate_black", "plate_white"):
                n = it.heading
                side = (wx - it.x) * math.cos(n) + (wy - it.y) * math.sin(n)
                self.rig.ir_aim((pid, "front" if side >= 0 else "back"))
            elif pid == "stand":
                self.rig.ir_aim(("lamp",))
            else:
                self.rig.ir_aim(("ambient",))
        self.app.refresh_panels()
        self.redraw_scene()

    def on_drag(self, ev):
        if self.dragging:
            pid, ox, oy = self.dragging
            wx, wy = self.p.s2w(ev.x, ev.y)
            self.rig.move_item(pid, wx - ox, wy - oy)
            if pid in ("meter", "plate_black", "plate_white"):
                self.rig.aim_at_source(pid)
            self.redraw_scene()
        elif self.pan:
            x0, y0, ox, oy = self.pan
            self.p.ox = ox - (ev.x - x0) / self.p.scale
            self.p.oy = oy + (ev.y - y0) / self.p.scale
            self.redraw_scene()

    def on_release(self, ev):
        self.dragging = None
        self.pan = None

    def on_wheel(self, ev, delta=None, fine=False):
        d = delta if delta is not None else ev.delta
        pid, wx, wy = self._hit(ev.x, ev.y)
        if pid is not None:
            step = math.radians(0.5 if fine else 2.0)
            self.rig.rotate_item(pid, step if d > 0 else -step)
        else:
            f = 1.12 if d > 0 else 1 / 1.12
            ns = max(300.0, min(6000.0, self.p.scale * f))
            wx0, wy0 = self.p.s2w(ev.x, ev.y)
            self.p.scale = ns
            wx1, wy1 = self.p.s2w(ev.x, ev.y)
            self.p.ox += wx0 - wx1
            self.p.oy += wy0 - wy1
        self.redraw_scene()

    # ==================================================================
    # panels
    # ==================================================================
    def on_speed(self, *_):
        try:
            self.rig.speed = float(self.speed_var.get())
        except ValueError:
            pass

    def on_replace(self):
        if self.rig.replace_source():
            self.warn.config(text=T('새 광원으로 교체했다.', 'New light source fitted.'))
        else:
            self.warn.config(text=T('교체할 필요가 없거나 예비 광원이 없다.', 'Nothing to replace, or no spares left.'))
        self.app.refresh_all()

    def on_filter(self):
        v = self.filt_var.get()
        if v == "none":
            self.rig.set_meter_filter(None)
            return
        pid = "filter_" + v
        if pid not in self.rig.placed:
            self.filt_var.set("none")
            self.rig.set_meter_filter(None)
            self.warn.config(text=T('그 필터를 아직 조립하지 않았다.', 'That filter has not been placed yet.'))
            return
        self.rig.set_meter_filter("rgb".index(v))

    # --- power supply --------------------------------------------------
    def on_psu_click(self, ev):
        x, y = ev.x, ev.y
        if 24 <= x <= 86 and 108 <= y <= 170:            # current knob
            self.i_sel = 0 if self.i_sel is None else (self.i_sel + 1) % 4
            self.v_sel = None
            self.edit_until = time.time() + 4.0
        elif 134 <= x <= 196 and 108 <= y <= 170:        # voltage knob
            self.v_sel = 0 if self.v_sel is None else (self.v_sel + 1) % 4
            self.i_sel = None
            self.edit_until = time.time() + 4.0
        elif 228 <= x <= 294 and 118 <= y <= 160:        # output button
            self.rig.psu_set_output(not self.rig.psu_on)
        self.app.refresh_panels()

    def on_psu_wheel(self, ev, delta=None, fine=False):
        d = delta if delta is not None else ev.delta
        s = 1 if d > 0 else -1
        if self.i_sel is not None:
            self.rig.psu_set_current_limit(
                self.rig.i_limit + s * I_W[self.i_sel])
            self.edit_until = time.time() + 4.0
        elif self.v_sel is not None:
            self.rig.psu_set_voltage_limit(
                self.rig.v_limit + s * V_W[self.v_sel])
            self.edit_until = time.time() + 4.0
        self.app.refresh_panels()

    def draw_psu(self):
        c = self.psu_cv
        c.delete("all")
        c.create_rectangle(6, 8, 306, 100, fill="#a99e80", outline="#7d745c")
        c.create_rectangle(14, 22, 132, 86, fill=COL_LCD, outline="#04101f")
        c.create_rectangle(180, 22, 298, 86, fill=COL_LCD, outline="#04101f")
        c.create_text(20, 16, text="A", fill="#4a4535", anchor="w",
                      font=("TkDefaultFont", 8, "bold"))
        c.create_text(186, 16, text="V", fill="#4a4535", anchor="w",
                      font=("TkDefaultFont", 8, "bold"))
        istr, vstr, mode = self.rig.psu_display()
        editing = time.time() < self.edit_until
        if editing and self.i_sel is not None:
            istr = "%05.3f" % self.rig.i_limit
        if editing and self.v_sel is not None:
            vstr = "%05.2f" % self.rig.v_limit
        f = ("Courier", 22, "bold")
        c.create_text(73, 54, text=istr, fill=COL_LCD_TXT, font=f)
        c.create_text(239, 54, text=vstr, fill=COL_LCD_TXT, font=f)
        if editing and self.i_sel is not None:
            c.create_rectangle(40 + self.i_sel * 16, 74,
                               52 + self.i_sel * 16, 77,
                               fill="#ff9b3d", outline="")
        if editing and self.v_sel is not None:
            c.create_rectangle(206 + self.v_sel * 16, 74,
                               218 + self.v_sel * 16, 77,
                               fill="#ff9b3d", outline="")
        on = self.rig.psu_on
        c.create_oval(146, 28, 154, 36,
                      fill="#e04b3a" if (on and mode == "CC") else "#5c554a",
                      outline="")
        c.create_text(157, 32, text="CC", anchor="w", fill="#4a4535",
                      font=("TkDefaultFont", 7))
        c.create_oval(146, 46, 154, 54,
                      fill="#e04b3a" if (on and mode == "CV") else "#5c554a",
                      outline="")
        c.create_text(157, 50, text="CV", anchor="w", fill="#4a4535",
                      font=("TkDefaultFont", 7))
        for x0, lab in ((24, "CURRENT"), (134, "VOLTAGE")):
            c.create_oval(x0, 108, x0 + 62, 170, fill="#ded8c8",
                          outline="#8f8878", width=2)
            c.create_line(x0 + 31, 139, x0 + 31, 116, fill="#8f8878", width=3)
            c.create_text(x0 + 31, 178, text=lab, font=("TkDefaultFont", 7))
        if self.i_sel is not None and editing:
            c.create_oval(22, 106, 88, 172, outline="#ff9b3d", width=2)
        if self.v_sel is not None and editing:
            c.create_oval(132, 106, 198, 172, outline="#ff9b3d", width=2)
        c.create_oval(228, 118, 294, 160,
                      fill="#3a6fd8" if on else "#8f96a0", outline="#2a4f9a",
                      width=2)
        c.create_text(261, 139, text=T('출력', 'Output'), fill="white",
                      font=("TkDefaultFont", 9, "bold"))
        c.create_text(255, 178, text=T('설정: %.2f V / %.3f A', 'set: %.2f V / %.3f A')
                      % (self.rig.v_limit, self.rig.i_limit),
                      font=("TkDefaultFont", 7), fill="#555")

    # --- light meter ---------------------------------------------------
    def on_meter_click(self, ev):
        x, y = ev.x, ev.y
        if 14 <= x <= 84 and 96 <= y <= 124:
            self.rig.meter_press_power()
        elif 104 <= x <= 174 and 96 <= y <= 124:
            self.rig.meter_press_hold()
        elif 194 <= x <= 264 and 96 <= y <= 124:
            self.rig.meter_press_units()
        self.app.refresh_panels()

    def draw_meter(self):
        c = self.mtr_cv
        c.delete("all")
        c.create_rectangle(6, 8, 306, 88, fill="#dfe3e6", outline="#a9b0b6")
        c.create_rectangle(14, 16, 298, 80, fill=COL_MLCD, outline="#7c8a6c")
        txt = self.rig.meter_display()
        c.create_text(238, 48, text=txt, anchor="e", fill="#1d2b18",
                      font=("Courier", 26, "bold"))
        if self.rig.meter_on:
            c.create_text(290, 52, text=self.rig.meter_unit_text(), anchor="e",
                          fill="#1d2b18", font=("Courier", 13, "bold"))
            if self.rig.meter_hold:
                c.create_text(26, 26, text="HOLD", anchor="w", fill="#1d2b18",
                              font=("Courier", 9, "bold"))
        for x0, lab in ((14, T('전원', 'Power')), (104, "HOLD"),
                        (194, T('단위', 'Units'))):
            c.create_rectangle(x0, 96, x0 + 70, 124, fill="#f3f5f6",
                               outline="#9aa2a8")
            c.create_text(x0 + 35, 110, text=lab, font=("TkDefaultFont", 8))

    # --- infrared thermometer ------------------------------------------
    def on_ir_click(self, ev):
        if 200 <= ev.x <= 298 and 30 <= ev.y <= 74:
            self.rig.ir_trigger()
        self.app.refresh_panels()

    def draw_ir(self):
        c = self.ir_cv
        c.delete("all")
        c.create_rectangle(6, 8, 190, 96, fill="#dfe3e6", outline="#a9b0b6")
        c.create_rectangle(14, 18, 182, 70, fill=COL_MLCD, outline="#7c8a6c")
        c.create_text(172, 44, text=self.rig.ir_display(), anchor="e",
                      fill="#1d2b18", font=("Courier", 22, "bold"))
        c.create_text(172, 64, text=u"\u00b0C", anchor="e", fill="#1d2b18",
                      font=("Courier", 10, "bold"))
        c.create_rectangle(200, 30, 298, 74, fill="#c8503f", outline="#8f3428")
        c.create_text(249, 52, text=T('방아쇠', 'Trigger'), fill="white",
                      font=("TkDefaultFont", 9, "bold"))

    def aim_text(self):
        t = self.rig.ir_target
        if t is None:
            return T('조준: 없음 (장면에서 대상을 클릭하라)', 'Aim: none (click a target in the scene)')
        if t[0] == "ambient":
            return T('조준: 주변 (작업 매트 / 벽)', 'Aim: surroundings (mat / wall)')
        if t[0] == "lamp":
            return T('조준: 광원', 'Aim: light source')
        nm = T('검정 판', 'black plate') if t[0] == "plate_black" \
            else T('흰색 판', 'white plate')
        sd = T('앞면', 'front') if t[1] == "front" else T('뒷면', 'back')
        return T('조준: %s %s', 'Aim: %s %s') % (nm, sd)

    # ==================================================================
    def redraw_scene(self):
        cv = self.cv
        cv.delete("all")
        r = self.rig
        if "mat" in r.placed:
            self.p.draw_mat()
        for pid in ("psu", "protractor", "ir"):
            it = r.items.get(pid)
            if it is None:
                continue
            if pid == "psu":
                self.p.draw_psu(it)
            elif pid == "protractor":
                self.p.draw_protractor(it)
            else:
                self.p.draw_ir(it)
        for pid in ("plate_black", "plate_white"):
            it = r.items.get(pid)
            if it is None:
                continue
            sel = None
            if r.ir_target and r.ir_target[0] == pid:
                sel = r.ir_target[1]
            self.p.draw_plate(it, pid.endswith("white"), sel)
        it = r.items.get("stand")
        if it is not None:
            lit = (r.power() > 0.02) and not r.source_dead()
            self.p.draw_stand(it, r.source(), r.source_dead(), lit)
            if "weight" in r.placed:
                self.p.draw_weight(Item("weight", it.x - 0.055, it.y - 0.055))
        it = r.items.get("meter")
        if it is not None:
            self.p.draw_meter(it, r.meter_filter)
        if "wires" in r.placed and "psu" in r.items and "stand" in r.items:
            a, b = r.items["psu"], r.items["stand"]
            for off, col in ((0.006, "#c8332a"), (-0.006, "#2b2b2b")):
                self.p.line(a.x + 0.03, a.y - 0.04 + off, b.x - 0.03,
                            b.y + off, fill=col, width=2, smooth=True)
        # readouts taken from the printed grid
        rows = [pid for pid in ("meter", "plate_black", "plate_white")
                if r.polar_of(pid) is not None]
        if rows:
            cv.create_rectangle(6, 6, 340, 16 + 18 * len(rows),
                                fill="#2b3033", outline="#565c60")
        y = 10
        for pid, lab in (("meter", T('조도계', 'light meter')),
                         ("plate_black", T('검정 판', 'black plate')),
                         ("plate_white", T('흰색 판', 'white plate'))):
            pol = r.polar_of(pid)
            if pol is None:
                continue
            cv.create_text(10, y, anchor="nw", fill="#dfe5ea",
                           font=("TkDefaultFont", 9),
                           text=T('%s: 격자 눈금 r = %.1f cm,  각 = %d°', '%s: grid reading r = %.1f cm,  angle = %d°')
                           % (lab, pol[0] * 100.0, int(pol[1])))
            y += 18
        hh = cv.winfo_height() or 600
        cv.create_rectangle(6, hh - 46, 640, hh - 6, fill="#2b3033",
                            outline="#565c60")
        cv.create_text(12, hh - 40, anchor="nw", fill="#9aa5ad",
                       font=("TkDefaultFont", 8), width=620,
                       text=T('빈 곳 휠=확대/축소, 빈 곳 드래그=이동, 물체 위 휠=회전(Shift=미세), 물체 클릭=적외선 조준', 'Wheel on empty space = zoom, drag empty space = pan, wheel on an object = rotate (Shift = fine), click an object = aim the IR thermometer'))

    def refresh(self):
        self.draw_psu()
        self.draw_meter()
        self.draw_ir()
        self.ir_lab.config(text=self.aim_text())
        m, s = divmod(int(self.rig.sim_time), 60)
        self.clock_lab.config(
            text=T('경과 시간 %02d:%02d', 'Elapsed %02d:%02d') % (m, s))
        self.spare_lab.config(
            text=T('예비: 전구 %d, LED %d', 'Spares: bulb %d, LED %d')
            % (self.rig.spare_bulb, self.rig.spare_led))
        msgs = []
        if self.rig.source_dead():
            msgs.append(T('광원이 타버렸다.', 'The light source has burnt out.'))
        if self.rig.check_filter_heat():
            msgs.append(T('필터가 열로 손상되었다.', 'A filter was damaged by heat.'))
        if self.rig.psu_on and self.rig.i_limit <= 0:
            msgs.append(T('전류 제한이 0이다.', 'The current limit is zero.'))
        if msgs:
            self.warn.config(text="  ".join(msgs))
        elif self.warn.cget("text") and self.rig.sim_time % 30 < 1:
            self.warn.config(text="")


# --------------------------------------------------------------------------
# application
# --------------------------------------------------------------------------
class App(tk.Tk):

    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.title(T('EuPhO 2022 실험 E - 조명의 물리  |  HaslaLab', 'EuPhO 2022 Experiment E - Physics of Illumination  |  HaslaLab'))
        self.geometry("1400x880")
        self.minsize(1080, 700)
        self.rig = Rig(seed)

        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Label(top, text=T('EuPhO 2022  실험 문제 E : 조명의 물리', 'EuPhO 2022  Experimental problem E : Physics of Illumination'),
                  font=("TkDefaultFont", 13, "bold")).pack(side="left")
        ttk.Label(top, text=T('  세션 번호 %d', '  session %d')
                  % self.rig.seed,
                  foreground="#667").pack(side="left")
        ttk.Button(top, text=T('새 세션', 'New session'),
                   command=self.new_session).pack(side="right")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.tab_asm = AssemblyTab(self.nb, self)
        self.tab_bench = BenchTab(self.nb, self)
        self.nb.add(self.tab_asm, text=T('  조립  ', '  Assembly  '))
        self.nb.add(self.tab_bench, text=T('  실험대  ', '  Bench  '))
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab)

        self._last = time.time()
        self.after(60, self.tick)

    def new_session(self):
        seed = random.randrange(1, 10 ** 9)
        self.destroy()
        App(seed).mainloop()

    def on_tab(self, *_):
        if self.nb.index("current") == 1 and not self.rig.assembly_complete():
            self.nb.select(0)
            self.tab_asm.status.config(
                foreground="#a03030",
                text=T('아직 실험대를 사용할 수 없다: ', 'The bench cannot be used yet: ')
                     + ", ".join(self.rig.missing_for_bench()))
        else:
            self.refresh_all()

    def refresh_panels(self):
        self.tab_bench.refresh()

    def refresh_all(self):
        self.tab_asm.redraw()
        self.tab_bench.refresh()
        self.tab_bench.redraw_scene()

    def tick(self):
        now = time.time()
        dt = min(now - self._last, 0.5)
        self._last = now
        if self.nb.index("current") == 1:
            self.rig.advance(dt * self.rig.speed)
            self.tab_bench.refresh()
            self.tab_bench.redraw_scene()
        self.after(120, self.tick)


def main():
    seed = None
    args = sys.argv[1:]
    global LANG
    for i, a in enumerate(args):
        if a in ("--seed", "-s") and i + 1 < len(args):
            seed = int(args[i + 1])
        if a == "--lang" and i + 1 < len(args):
            LANG = "EN" if args[i + 1].lower().startswith("e") else "KO"
    App(seed).mainloop()


if __name__ == "__main__":
    main()
