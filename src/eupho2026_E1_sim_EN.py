#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  10th European Physics Olympiad  (EuPhO 2026, Gothenburg, Sweden)
  Experimental Problem :  ACOUSTIC LEVITATION   (tasks E1 - E8)
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Apparatus rebuilt from the photographs of the problem sheet: the
    levitator module on its frame with the red LED, the capture unit,
    the electrical box with its LED and Mode X switches, the power
    supply and banana cables, the screen, the transparent ruler, the
    green LEDs and the single transducer, tweezers, beads, liquids,
    syringes and a stopwatch.
    Only what a real instrument shows is displayed: the supply's
    voltage, the stopwatch, the ruler's marks and the shadows on the
    screen.  No magnification, node spacing, diameter, density,
    surface tension or refractive index is ever computed.
    The hidden values (node spacing, the Mode X detuning, the white
    beads' density, liquid I and III) are randomised for each session;
    --seed 2026 keeps the values of the official solution.

    Run:   python3 eupho2026_E1_sim_EN.py   [--seed N] [--lang ko|en]
"""
import math
import random
import time
import os
import sys
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_VERSION = "1.0"
LANG = "EN"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "KO" else en


# ==============================================================================
#  1.  물리 상수 / 참값  (학생에게는 절대 노출되지 않음)
# ==============================================================================
G = 9.81
V_SOUND = 340.0                 # m/s  (문제지 제공값)

# --- 음장 ---------------------------------------------------------------------
# 실제 트랜스듀서는 40 kHz (lam = 8.5 mm) 이지만, 두 반구 배열이 만드는
# 파면이 평면파가 아니어서 z축 위 마디 간격은 5.06 mm 로 넓어진다.
# 학생이 측정하는 것은 이 5.06 mm 이므로 f_meas ~ 33.6 kHz 가 된다. (공식 해설과 동일)
D_NODE = 5.06                   # mm, 인접 마디(=인접 배) 간격
LAM_E = 2.0 * D_NODE            # mm, 유효 파장
K2 = 2.0 * (2.0 * math.pi / LAM_E)   # 2k  [1/mm]
N_NODE_MIN, N_NODE_MAX = -3, 3       # z = n * D_NODE
Z_ARRAY_TOP = 19.0              # mm, 위쪽 배열 하면
Z_ARRAY_BOT = -19.0             # mm, 아래쪽 배열 상면
F_TRUE = 40000.0                # Hz (Överkurs)

# --- Mode X -------------------------------------------------------------------
DF_MODEX = -0.67                # Hz   (부호 음수 : 마디가 +z 로 이동)
U_RISE = D_NODE * abs(DF_MODEX)  # mm/s = 3.390
MODEX_STEP = LAM_E / 64.0       # mm, 위상 스텝 (짧은 '점프')

# --- 고체 비드 ----------------------------------------------------------------
DZ_FALL = 0.50                  # mm, 마디로부터 이 변위를 넘으면 낙하(불안정)
S_FALL = math.sin(K2 * DZ_FALL)  # = 0.58174
U_DROP_GLASS = 11.08            # V, 지름 2.0 mm 유리 비드의 낙하전압
RHO_GLASS = 2500.0
RHO_PP = 950.0                  # ★ 미지 흰색 비드(O)의 참값
RHO_STYRO = 25.0
D_BEAD = 2.00                   # mm
D_STYRO = 2.60                  # mm

# --- 액적 ---------------------------------------------------------------------
K_G = 0.0245                    # V^2 m^3/kg — 중력을 떠받치는 데 쓰이는 U^2 몫
CHI_C = 7795.0                  # 폭발 임계  chi = (U^2 - K_G rho) D / sigma
XI_A = 0.060                    # 형상식 절편
XI_B = 1.30e-4                  # 형상식 기울기

LIQUIDS = {
    'I':   dict(label='I',   rho=786.0,  sig=0.0218, nref=1.377,
                g_hi=9.0e-9,  g_lo=5.2e-10, color='#dfe9f5', tint='#c9d8ec'),
    'II':  dict(label='II',  rho=998.0,  sig=0.0730, nref=1.333,
                g_hi=1.1e-9,  g_lo=1.0e-10, color='#e2eef6', tint='#cfe0ee'),
    'III': dict(label='III', rho=1000.0, sig=0.0700, nref=1.333,
                g_hi=1.2e-9,  g_lo=1.1e-10, color='#f3cccc', tint='#e0a8a8'),
}

# --- 광학 ---------------------------------------------------------------------
LED_INSET = 5.0                 # mm, LED 발광점은 앞면보다 5 mm 안쪽에 있다
LED_EMIT_SIZE = 0.045           # mm, 발광면 크기 -> 반영(penumbra) 흐림
RUL_ENGRAVE = 0.12              # mm, 아크릴 자에 새겨진 눈금선의 두께
SCREEN_W = 260.0                # mm, 스크린 폭
SCREEN_H = 260.0                # mm, 스크린 높이

MAX_VOLT = 20.0


# ==============================================================================
#  2.  물리 함수
# ==============================================================================
def bead_drop_voltage(rho):
    """지름과 무관 : U_min ∝ sqrt(rho)"""
    return U_DROP_GLASS * math.sqrt(rho / RHO_GLASS)


def bead_offset(rho, U):
    """마디 아래로 내려간 거리 [mm]. 낙하하면 None."""
    if U <= 0:
        return None
    s = S_FALL * (bead_drop_voltage(rho) / U) ** 2
    if s > S_FALL * 1.0000001:
        return None
    s = min(s, 1.0)
    return math.asin(s) / K2


def drop_min_voltage(D, rho):
    """액적의 낙하(최소) 전압 [V]  — D [mm]"""
    return (1.7 * D + 4.6) * math.sqrt(rho / 998.0)


def drop_offset(D, rho, U):
    if U <= 0:
        return None
    s = S_FALL * (drop_min_voltage(D, rho) / U) ** 2
    if s > S_FALL * 1.0000001:
        return None
    return math.asin(min(s, 1.0)) / K2


def chi_param(U, D, liq):
    """형상 변수 chi = (U^2 - K_G rho) D / sigma"""
    return (U * U - K_G * liq['rho']) * D / liq['sig']


def aspect_ratio(U, D, liq):
    """xi = a/c  (a: 수평 반축, c: 연직 반축)"""
    return 1.0 + XI_A + XI_B * max(0.0, chi_param(U, D, liq))


def explode_voltage(D, liq):
    return math.sqrt(K_G * liq['rho'] + CHI_C * liq['sig'] / D)


def xi_line(liq):
    """수평선(E7)이 보이는 종횡비 :  n = xi^2/(xi^2-1)"""
    n = liq['nref']
    return math.sqrt(n / (n - 1.0))


def gamma_evap(D, liq):
    """증발상수 gamma(D) [m^2/s] — D >~ 1.1 mm 에서 상수, 그 아래에서 급감"""
    s = 1.0 / (1.0 + math.exp(-(D - 1.05) / 0.09))
    return liq['g_lo'] + (liq['g_hi'] - liq['g_lo']) * s


def semi_axes(D, xi):
    """등가지름 D, 종횡비 xi 인 회전타원체의 (a, c) [mm]"""
    c = (D / 2.0) / (xi ** (2.0 / 3.0))
    a = xi * c
    return a, c


def pressure_env(z):
    """z 위치의 음압 진폭 (0~1). 마디(=부양 위치)에서 0, 배에서 1."""
    axial = abs(math.sin(math.pi * z / D_NODE))
    env = math.exp(-(z / 26.0) ** 2)          # 배열 중심에서 멀어지면 약해짐
    return axial * env


def magnification(a_face_mm, b_mm):
    """a_face : 레비테이터 축 ~ LED 앞면 거리, b : 축 ~ 스크린 거리"""
    a = a_face_mm + LED_INSET
    return (a + b_mm) / a


# ==============================================================================
#  3.  색 / 그리기 유틸
# ==============================================================================
BG = "#12161c"
PANEL = "#1b2129"
PANEL2 = "#232b35"
FG = "#dfe6ee"
FG_DIM = "#8b98a8"
ACC = "#f0a500"
ACC2 = "#4da3ff"
OK = "#57c785"
BAD = "#e2544a"
METAL = "#8f9aa6"
METAL_D = "#5c656f"
METAL_L = "#c3ccd6"
DARK = "#2a2f36"


def mix(c1, c2, t):
    def h2r(c):
        c = c.lstrip('#')
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    r1, g1, b1 = h2r(c1)
    r2, g2, b2 = h2r(c2)
    return "#%02x%02x%02x" % (int(r1 + (r2 - r1) * t),
                              int(g1 + (g2 - g1) * t),
                              int(b1 + (b2 - b1) * t))


def shade(c, t):
    """t>0 밝게, t<0 어둡게"""
    return mix(c, "#ffffff" if t > 0 else "#000000", abs(t))


# ==============================================================================
#  4.  실험 대상 물체
# ==============================================================================
class Item(object):
    """레비테이터 안의 물체 하나 (비드 또는 액적)."""

    _uid = 0

    def __init__(self, kind, node, liquid=None, D=None, rng=None):
        Item._uid += 1
        self.uid = Item._uid
        self.kind = kind                    # 'styro' | 'pp' | 'glass' | 'drop'
        self.node = node                    # 마디 번호
        self.liq = LIQUIDS[liquid] if liquid else None
        self.liq_key = liquid
        r = rng or random
        # 개체차 (실제 비드/액적의 편차)
        self.var = 1.0 + r.gauss(0.0, 0.012)
        self.jit_phase = r.uniform(0, 6.283)
        self.jit_w = r.uniform(1.6, 3.2)
        self.jit_amp = r.uniform(0.010, 0.030)   # mm, 공기 난류에 의한 흔들림
        self.jit_x = r.uniform(0.020, 0.055)
        self.falling = False
        self.vz = 0.0
        self.z = 0.0
        self.x = 0.0
        self.dead = False
        self.exploded_at = -1e9
        if kind == 'styro':
            self.rho, self.D0 = RHO_STYRO, D_STYRO
        elif kind == 'pp':
            self.rho, self.D0 = RHO_PP, D_BEAD
        elif kind == 'glass':
            self.rho, self.D0 = RHO_GLASS, D_BEAD
        else:
            self.rho, self.D0 = self.liq['rho'], D
        self.D = self.D0 * (self.var if kind == 'drop' else 1.0)
        self.Dsq = (self.D * 1e-3) ** 2

    # ---- 물리 ----------------------------------------------------------------
    def is_drop(self):
        return self.kind == 'drop'

    def u_min(self, ):
        if self.is_drop():
            return drop_min_voltage(self.D, self.rho) * self.var
        return bead_drop_voltage(self.rho) * self.var

    def u_exp(self):
        if not self.is_drop():
            return 1e9
        return explode_voltage(self.D, self.liq) * self.var

    def offset(self, U):
        """마디 아래로의 변위 [mm]"""
        if self.is_drop():
            s = S_FALL * (self.u_min() / U) ** 2 if U > 0 else 9
        else:
            s = S_FALL * (self.u_min() / U) ** 2 if U > 0 else 9
        if s > S_FALL * 1.0000001:
            return None
        return math.asin(min(s, 1.0)) / K2

    def xi(self, U):
        if not self.is_drop():
            return 1.0
        return aspect_ratio(U, self.D, self.liq)

    def axes(self, U):
        """(a, c) 반축 [mm]"""
        if not self.is_drop():
            return self.D / 2.0, self.D / 2.0
        return semi_axes(self.D, self.xi(U))

    def line_visible(self, U, align_err):
        """E7 : 수평선이 보이는가"""
        if not self.is_drop():
            return False
        xl = xi_line(self.liq)
        x = self.xi(U)
        if abs(x - xl) > 0.048:
            return False
        if abs(align_err) > 1.6:            # LED 정렬 오차 [mm]
            return False
        return True


# ==============================================================================
#  5.  벤치(세계) 모델
# ==============================================================================
class World(object):
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.reset_all()

    # --------------------------------------------------------------------- #
    def reset_all(self):
        self.t = 0.0                 # 시뮬레이션 시각 [s]
        self.speed = 1.0
        # 조립 상태
        self.asm = dict(levitator=False, net=False, powercord=False,
                        cab_gp=False, cab_gm=False, screen=False,
                        capture=False)
        self.shorted = False
        self.damage = []             # E8 벌점 기록
        # 전원 / 스위치
        self.out_on = False
        self.U = 8.0
        self.modeX = False
        self.red_led = True
        # 기하
        self.a_face = 15.0           # mm, 축~LED 앞면
        self.b_screen = 680.0        # mm, 축~스크린
        self.led_dy = 0.0            # mm, LED 연직 정렬 오차
        self.led_tilt = 0.0          # deg
        # 물체
        self.items = []
        self.node_off = 0.0          # Mode X 에 의한 마디 이동 [mm]
        self._modex_acc = 0.0
        # 스톱워치
        self.sw_run = False
        self.sw_t = 0.0
        self.sw_laps = []
        # E1 프로브
        self.probe_z = 0.0
        self.probe_cfg = 'none'
        self.probe_led_blown = 0
        # 스크린 위 작도
        self.marks = []              # (x_mm, y_mm, label)
        self.lines = []              # (x1,y1,x2,y2)
        self.ruler_place = 'screen'  # 'screen' | 'levitator' | 'away'
        self.ruler_x = 40.0
        self.ruler_y = 0.0
        self.ruler_ang = 90.0
        self.log = []                # 사용자 수기 기록

    # --------------------------------------------------------------------- #
    def powered(self):
        return (self.asm['levitator'] and self.asm['powercord'] and
                self.asm['cab_gp'] and self.asm['cab_gm'] and
                self.out_on and not self.shorted)

    def U_eff(self):
        return self.U if self.powered() else 0.0

    def M(self):
        return magnification(self.a_face, self.b_screen)

    def node_z(self, n):
        return n * D_NODE + self.node_off

    # --------------------------------------------------------------------- #
    def add_item(self, kind, node, liquid=None, D=None):
        if not self.powered():
            return None, T("전원이 켜져 있지 않습니다.", "The levitator is not powered.")
        if len(self.items) >= 9:
            return None, T("물체가 너무 많습니다.", "Too many objects in the trap.")
        it = Item(kind, node, liquid, D, self.rng)
        if self.U_eff() < it.u_min():
            return None, T("전압이 낮아 부양되지 않고 떨어집니다.",
                           "Voltage too low - the object falls immediately.")
        if it.is_drop() and self.U_eff() > it.u_exp():
            return None, T("전압이 너무 높아 액적이 즉시 터졌습니다.",
                           "Voltage too high - the droplet burst immediately.")
        for o in self.items:
            if (not o.dead) and o.node == node:
                return None, T("그 마디에는 이미 물체가 있습니다.",
                               "That node is already occupied.")
        it.z = self.node_z(node)
        self.items.append(it)
        return it, None

    def clear_items(self):
        self.items = []

    def remove_item(self, uid):
        self.items = [o for o in self.items if o.uid != uid]

    # --------------------------------------------------------------------- #
    def step(self, dt_real):
        dt = dt_real * self.speed
        self.t += dt
        if self.sw_run:
            self.sw_t += dt

        U = self.U_eff()

        # --- Mode X : 마디가 위로 이동 ---------------------------------------
        if self.modeX and U > 0:
            self._modex_acc += U_RISE * dt
            while self._modex_acc >= MODEX_STEP:
                self._modex_acc -= MODEX_STEP
                self.node_off += MODEX_STEP
            # 마디 무늬는 D_NODE 만큼 이동하면 자기 자신과 같아진다.
            # 따라서 오프셋을 감고, 물체는 한 마디 위로 옮겨 탄다.
            while self.node_off >= D_NODE:
                self.node_off -= D_NODE
                for it in self.items:
                    if not it.dead and not it.falling:
                        it.node += 1

        # --- 물체 ------------------------------------------------------------
        for it in self.items:
            if it.dead:
                continue
            if it.falling:
                it.vz -= G * 1000.0 * dt
                it.z += it.vz * dt
                if it.z < Z_ARRAY_BOT - 6.0:
                    it.dead = True
                continue

            # 증발
            if it.is_drop():
                g = gamma_evap(it.D, it.liq)
                it.Dsq -= g * dt
                if it.Dsq <= (0.28e-3) ** 2:
                    it.dead = True
                    continue
                it.D = math.sqrt(it.Dsq) * 1e3

            # 폭발
            if it.is_drop() and U > it.u_exp():
                self._explode(it)
                continue

            # 낙하
            off = it.offset(U)
            if off is None:
                it.falling = True
                it.vz = 0.0
                continue

            znode = self.node_z(it.node)
            if znode > Z_ARRAY_TOP - 1.0:
                # 위쪽 배열에 도달 -> 트랩에서 이탈
                it.falling = True
                it.vz = 0.0
                continue
            jit = it.jit_amp * math.sin(it.jit_w * self.t + it.jit_phase)
            it.z = znode - off + jit
            it.x = it.jit_x * math.sin(0.61 * it.jit_w * self.t + 1.7 * it.jit_phase)

    def _explode(self, it):
        it.exploded_at = self.t
        if self.rng.random() < 0.62 and it.D > 1.0:
            it.D *= self.rng.uniform(0.66, 0.78)
            it.Dsq = (it.D * 1e-3) ** 2
            it.var = 1.0 + self.rng.gauss(0.0, 0.012)
            # 폭발 후에도 전압이 너무 높으면 계속 터진다
            if self.U_eff() > it.u_exp():
                it.dead = True
        else:
            it.dead = True

    # --------------------------------------------------------------------- #
    def alive(self):
        return [o for o in self.items if not o.dead]

    def line_active(self):
        U = self.U_eff()
        for o in self.alive():
            if (not o.falling) and o.line_visible(U, self.led_dy):
                return o
        return None

    # --- E1 프로브 ---------------------------------------------------------- #
    PROBE_GAIN = {'anti': 1.00, 'same': 0.16, 'one': 0.15,
                  'one_hand': 0.45, 'none': 0.0, 'blown': 0.0}

    def probe_brightness(self):
        if not self.powered():
            return 0.0
        g = self.PROBE_GAIN.get(self.probe_cfg, 0.0)
        if g <= 0:
            return 0.0
        p = pressure_env(self.probe_z)
        drive = p * (self.U / 17.0) * 1.55
        v = (drive - 0.30) * g / 0.70          # LED 문턱전압 효과
        if self.modeX:
            # 마디가 이동하므로 고정된 점에서 밝기가 |df| 로 점멸한다
            ph = math.pi * (self.probe_z - self.node_off) / D_NODE
            p2 = abs(math.sin(ph)) * math.exp(-(self.probe_z / 26.0) ** 2)
            drive = p2 * (self.U / 17.0) * 1.55
            v = (drive - 0.30) * g / 0.70
        return max(0.0, min(1.0, v))


# ==============================================================================
#  6.  장비 그리기 유틸
# ==============================================================================
def rrect(cv, x1, y1, x2, y2, r=6, **kw):
    r = min(r, abs(x2 - x1) / 2.0, abs(y2 - y1) / 2.0)
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def vgrad(cv, x1, y1, x2, y2, c1, c2, steps=18, tags=()):
    h = (y2 - y1) / float(steps)
    for i in range(steps):
        cv.create_rectangle(x1, y1 + i * h, x2, y1 + (i + 1) * h + 1,
                            fill=mix(c1, c2, i / float(steps - 1)),
                            outline="", tags=tags)


def draw_transducer_face(cv, cx, cy, rx, ry, tags=(), lit=0.0):
    """트랜스듀서(초음파 소자) 정면 : 동심원 + 나선 무늬"""
    body = shade("#2a2d31", 0.05 + 0.5 * lit)
    cv.create_oval(cx - rx, cy - ry, cx + rx, cy + ry,
                   fill="#4a4f55", outline="#22262a", tags=tags)
    cv.create_oval(cx - rx * .86, cy - ry * .86, cx + rx * .86, cy + ry * .86,
                   fill=body, outline="#1b1e21", tags=tags)
    for k in range(3):
        f = .66 - .18 * k
        cv.create_oval(cx - rx * f, cy - ry * f, cx + rx * f, cy + ry * f,
                       outline=shade("#7f868d", 0.1 * k), tags=tags)
    cv.create_oval(cx - rx * .16, cy - ry * .16, cx + rx * .16, cy + ry * .16,
                   fill="#9aa2aa", outline="", tags=tags)


def draw_levitator(cv, cx, cy, sc, world, tags="lev", show_net=True,
                   show_led=True):
    """레비테이터 모듈 측면도.  sc = px/mm, cy = z0 화면 y좌표"""
    def Y(z):
        return cy - z * sc

    def X(x):
        return cx + x * sc

    R = 31.0                       # mm, 배열 반경
    # ---- 지지 기둥 4개 ----
    for xx in (-27.5, 27.5):
        cv.create_rectangle(X(xx) - 2.6 * sc, Y(34), X(xx) + 2.6 * sc, Y(-34),
                            fill="#6d757e", outline="#4a5158", tags=tags)
        cv.create_rectangle(X(xx) - 2.6 * sc, Y(34), X(xx) - 0.9 * sc, Y(-34),
                            fill="#8d959d", outline="", tags=tags)
    # ---- 위/아래 원판 ----
    for z0, z1 in ((30.5, 35.0), (-35.0, -30.5)):
        cv.create_polygon(X(-R - 4), Y(z0), X(R + 4), Y(z0),
                          X(R + 2), Y(z1), X(-R - 2), Y(z1),
                          fill="#6b7278", outline="#41474c", tags=tags)
    # 위 원판 상면 하이라이트
    cv.create_line(X(-R - 4), Y(35.0), X(R + 4), Y(35.0),
                   fill="#a8b0b8", width=2, tags=tags)
    # 볼트
    for xx in (-20, 20):
        cv.create_oval(X(xx) - 2.2 * sc, Y(36.6), X(xx) + 2.2 * sc, Y(33.6),
                       fill="#98a1a9", outline="#5d656c", tags=tags)

    # ---- 아래 배열 (오목 그릇, 위를 향함) ----
    bowl_b = [(-R, -30.5), (-R * .93, -24.0), (-R * .55, -20.2),
              (0, -19.0), (R * .55, -20.2), (R * .93, -24.0), (R, -30.5)]
    cv.create_polygon([c for p in bowl_b for c in (X(p[0]), Y(p[1]))],
                      fill="#2f3338", outline="#1c1f22", smooth=True, tags=tags)
    # ---- 위 배열 (오목 그릇, 아래를 향함) ----
    bowl_t = [(-R, 30.5), (-R * .93, 24.0), (-R * .55, 20.2),
              (0, 19.0), (R * .55, 20.2), (R * .93, 24.0), (R, 30.5)]
    cv.create_polygon([c for p in bowl_t for c in (X(p[0]), Y(p[1]))],
                      fill="#2f3338", outline="#1c1f22", smooth=True, tags=tags)

    on = world.powered()
    lit = 0.0 if not on else min(1.0, world.U / 17.0)
    # 트랜스듀서들
    for xx, zz in ((-24, -25.6), (-14.5, -21.4), (-4.5, -19.4),
                   (5.5, -19.6), (15.5, -21.8), (24.5, -26.0)):
        draw_transducer_face(cv, X(xx), Y(zz), 4.4 * sc, 2.0 * sc, tags, lit)
    for xx, zz in ((-24, 25.6), (-14.5, 21.4), (-4.5, 19.4),
                   (5.5, 19.6), (15.5, 21.8), (24.5, 26.0)):
        draw_transducer_face(cv, X(xx), Y(zz), 4.4 * sc, 2.0 * sc, tags, lit)

    # ---- 상/하 단자 레일 (단락 주의) ----
    for z in (33.0, -33.0):
        cv.create_line(X(-R - 2), Y(z), X(R + 2), Y(z),
                       fill="#c9a227", width=max(1, int(0.9 * sc)), tags=tags)

    # ---- 금속망 ----
    if show_net and world.asm['net']:
        for i in range(9):
            xx = -20 + i * 5.0
            cv.create_line(X(xx), Y(-29.4), X(xx), Y(-31.6),
                           fill="#b9c1c9", tags=tags)
        cv.create_line(X(-21), Y(-30.5), X(21), Y(-30.5),
                       fill="#cfd6dd", width=max(1, int(0.6 * sc)), tags=tags)

    # ---- 빨간 LED 모듈 (측면, 왼쪽에서 비춤) ----
    if show_led:
        ax = -(world.a_face)
        ay = world.led_dy
        cv.create_rectangle(X(ax - 12), Y(ay + 3.2), X(ax), Y(ay - 3.2),
                            fill="#3a4048", outline="#22262b", tags=tags)
        col = "#ff2b2b" if (on and world.red_led) else "#5a2020"
        cv.create_oval(X(ax) - 1.9 * sc, Y(ay + 1.9), X(ax) + 1.9 * sc,
                       Y(ay - 1.9), fill=col, outline="#7d1414", tags=tags)
        if on and world.red_led:
            cv.create_oval(X(ax) - 3.4 * sc, Y(ay + 3.4), X(ax) + 3.4 * sc,
                           Y(ay - 3.4), outline="#ff6a6a", tags=tags)
    return X, Y


def draw_rail(cv, x1, x2, y, tags="rail"):
    """알루미늄 프로파일 레일 (측면)"""
    cv.create_rectangle(x1, y, x2, y + 14, fill="#9aa3ac", outline="#6a727a",
                        tags=tags)
    cv.create_rectangle(x1, y + 4, x2, y + 10, fill="#7d858d", outline="",
                        tags=tags)
    for x in range(int(x1) + 10, int(x2), 24):
        cv.create_line(x, y + 1, x, y + 13, fill="#8e969e", tags=tags)


# ------------------------------------------------------------------------------
#  투명 자 (K) : 300 mm, mm 눈금
# ------------------------------------------------------------------------------
def draw_ruler(cv, px_per_mm, x_mm, y_mm, ang_deg, to_px, tags="ruler",
               length=300.0, width=30.0):
    """중심(x_mm,y_mm), 각도 ang_deg 인 투명 자를 그린다.
       to_px(xmm,ymm) -> (px,py)"""
    a = math.radians(ang_deg)
    ca, sa = math.cos(a), math.sin(a)

    def P(u, v):
        return to_px(x_mm + u * ca - v * sa, y_mm + u * sa + v * ca)

    hl, hw = length / 2.0, width / 2.0
    corners = [P(-hl, -hw), P(hl, -hw), P(hl, hw), P(-hl, hw)]
    cv.create_polygon([c for p in corners for c in p],
                      fill="#8ec8e8", outline="#cfe9f7", stipple="gray25",
                      tags=tags)
    cv.create_polygon([c for p in corners for c in p],
                      fill="", outline="#dff0fb", tags=tags)
    for i in range(0, int(length) + 1):
        u = -hl + i
        if i % 10 == 0:
            ln, col = 10.0, "#eaf6ff"
        elif i % 5 == 0:
            ln, col = 6.5, "#d8ecfa"
        else:
            ln, col = 3.6, "#c6e2f4"
        p1 = P(u, -hw)
        p2 = P(u, -hw + ln)
        cv.create_line(p1[0], p1[1], p2[0], p2[1], fill=col, tags=tags)
        if i % 10 == 0 and i > 0:
            q = P(u, -hw + 16)
            cv.create_text(q[0], q[1], text=str(i // 10), fill="#eaf6ff",
                           font=("Consolas", 7), angle=-ang_deg, tags=tags)
    p = P(-hl + 6, hw - 7)
    cv.create_text(p[0], p[1], text="EuPhO", fill="#bfe0f3",
                   font=("Segoe UI", 7, "bold"), angle=-ang_deg, tags=tags)


# ------------------------------------------------------------------------------
#  그림자 투영 (스크린)
# ------------------------------------------------------------------------------
def project_items(world):
    """스크린에 맺히는 그림자 목록을 계산한다.
       반환 : [(y_mm, a_mm, c_mm, kind, item, blur_mm)]   y는 스크린 좌표(위 +)"""
    M = world.M()
    U = world.U_eff()
    a_led = world.a_face + LED_INSET
    blur = LED_EMIT_SIZE * (world.b_screen / a_led)
    out = []
    for it in world.alive():
        a, c = it.axes(U)
        y = (it.z - world.led_dy) * M
        out.append((y, a * M, c * M, it.kind, it, blur))
    return out


def project_ruler_shadow(world):
    """자(K)를 레비테이터 중심에 세웠을 때, mm 눈금의 그림자 y좌표 목록"""
    M = world.M()
    res = []
    # 자의 중심을 z=0 근처에 두고, -60 ~ +60 mm 범위
    for i in range(-70, 71):
        z = i * 1.0 + world.ruler_y
        y = (z - world.led_dy) * M
        if abs(y) > SCREEN_H * 0.75:
            continue
        res.append((y, i))
    return res


# ==============================================================================
#  7.  애플리케이션
# ==============================================================================
EQUIP = [
    ("A", T("초록색 LED 2개", "Two green LEDs"),
     T("전원공급기(G)에 연결하지 말 것", "Do not connect to the power supply (G)")),
    ("B", T("개별 트랜스듀서", "Individual transducer"),
     T("압전 소자 — 수신기로 사용 가능", "Piezo element — usable as a receiver")),
    ("C", T("레비테이터 모듈 + 빨간 LED", "Levitator module + red LED"),
     T("빨간 LED는 점광원으로 취급", "The red LED is a point source")),
    ("D", T("낙하물 수집 유닛", "Capture unit"), ""),
    ("E", T("육각 렌치 2개", "2 hex keys"), T("정렬용", "For alignment")),
    ("F", T("전기 박스 (LED / Mode X)", "Electrical enclosure (LED / Mode X)"), ""),
    ("G", T("전원공급기", "Power supply"), T("0 – 20 V", "0 – 20 V")),
    ("H", T("바나나 케이블", "Banana cables"), ""),
    ("I", T("스크린", "Screen"), ""),
    ("J", T("테이프", "Tape"), ""),
    ("K", T("투명 자 (300 mm)", "Transparent ruler (300 mm)"), ""),
    ("L", T("금속망", "Metal net"), T("젖으면 말릴 것", "Dry it if it gets wet")),
    ("M", T("핀셋", "Tweezers"), ""),
    ("N", T("파란 스티로폼 비드 15개", "15 blue styrofoam beads"), ""),
    ("O", T("흰색 구형 비드 (미지 재질, ⌀2.0 mm)",
            "White spherical beads (unknown, ⌀2.0 mm)"), ""),
    ("P", T("유리 비드 (⌀2.0 mm, 2500 kg/m³)",
            "Glass beads (⌀2.0 mm, 2500 kg/m³)"), ""),
    ("Q", T("미지 액체 I · II · III", "Unknown liquids I, II, III"), ""),
    ("R", T("주사기 3개", "3 syringes"), ""),
    ("S", T("무딘 바늘 3개", "3 blunt needles"), ""),
    ("T", T("빨래집게 2개", "2 clothes pegs"), ""),
    ("U", T("스톱워치", "Stop watch"), ""),
    ("V", T("램프", "Lamp"), ""),
    ("W", T("전원 코드", "Power cord"), ""),
    ("X", T("종이 (망 건조용)", "Paper (to dry the net)"), ""),
]


def sprite(cv, code, x, y, s=1.0):
    """장비 아이콘 (x,y = 좌상단, 62x46 기준)"""
    def R(a, b, c, d, **k):
        cv.create_rectangle(x + a * s, y + b * s, x + c * s, y + d * s, **k)

    def O(a, b, c, d, **k):
        cv.create_oval(x + a * s, y + b * s, x + c * s, y + d * s, **k)

    def L(a, b, c, d, **k):
        cv.create_line(x + a * s, y + b * s, x + c * s, y + d * s, **k)

    if code == "A":
        for dx, col in ((6, "#41d16b"), (26, "#41d16b")):
            O(dx, 6, dx + 14, 22, fill=col, outline="#1d7a3a")
            R(dx + 4, 20, dx + 6, 40, fill="#c8ccd0", outline="")
            R(dx + 9, 20, dx + 11, 40, fill="#c8ccd0", outline="")
    elif code == "B":
        draw_transducer_face(cv, x + 22 * s, y + 16 * s, 15 * s, 11 * s)
        L(18, 26, 14, 44, fill="#c8ccd0")
        L(26, 26, 30, 44, fill="#c8ccd0")
    elif code == "C":
        R(6, 34, 56, 40, fill="#8f9aa6", outline="#5c656f")
        R(14, 10, 46, 14, fill="#5b636b", outline="#3c4248")
        R(14, 26, 46, 30, fill="#5b636b", outline="#3c4248")
        for dx in (18, 27, 36):
            draw_transducer_face(cv, x + (dx + 4) * s, y + 24 * s, 4 * s, 2.6 * s)
            draw_transducer_face(cv, x + (dx + 4) * s, y + 16 * s, 4 * s, 2.6 * s)
        O(4, 17, 12, 23, fill="#ff3030", outline="#8a1515")
    elif code == "D":
        R(10, 16, 52, 40, fill="#3d444c", outline="#252a30")
        R(10, 16, 52, 20, fill="#59626b", outline="")
    elif code == "E":
        L(12, 34, 12, 12, fill="#6c757e", width=4)
        L(12, 12, 26, 12, fill="#6c757e", width=4)
        L(36, 36, 36, 16, fill="#6c757e", width=4)
        L(36, 16, 50, 16, fill="#6c757e", width=4)
    elif code == "F":
        R(6, 8, 56, 40, fill="#e7e3da", outline="#a9a49a")
        O(14, 18, 24, 28, fill="#3a4048", outline="#20242a")
        O(36, 18, 46, 28, fill="#c0392b", outline="#7d2318")
        cv.create_text(x + 31 * s, y + 13 * s, text="EuPhO", fill="#8a8478",
                       font=("Segoe UI", int(5 * s), "bold"))
    elif code == "G":
        R(6, 6, 56, 42, fill="#ded9cf", outline="#a7a196")
        R(12, 12, 50, 24, fill="#2b2f33", outline="#15181b")
        cv.create_text(x + 31 * s, y + 18 * s, text="12.0", fill="#ff5a3c",
                       font=("Consolas", int(8 * s), "bold"))
        O(14, 30, 22, 38, fill="#b9c0c7", outline="#7d848b")
        O(40, 30, 48, 38, fill="#b9c0c7", outline="#7d848b")
    elif code == "H":
        cv.create_line(x + 6 * s, y + 34 * s, x + 24 * s, y + 12 * s,
                       x + 40 * s, y + 34 * s, x + 56 * s, y + 14 * s,
                       fill="#c0392b", width=3, smooth=True)
        cv.create_line(x + 6 * s, y + 40 * s, x + 24 * s, y + 20 * s,
                       x + 40 * s, y + 40 * s, x + 56 * s, y + 22 * s,
                       fill="#222", width=3, smooth=True)
    elif code == "I":
        cv.create_polygon(x + 10 * s, y + 8 * s, x + 54 * s, y + 12 * s,
                          x + 50 * s, y + 42 * s, x + 6 * s, y + 38 * s,
                          fill="#cfe6f2", outline="#9dc2d6", stipple="gray50")
    elif code == "J":
        O(16, 12, 46, 36, fill="#f2f2f2", outline="#b9b9b9")
        O(26, 20, 36, 28, fill=PANEL, outline="#b9b9b9")
    elif code == "K":
        R(4, 18, 58, 30, fill="#bfe0f3", outline="#8fc4de", stipple="gray50")
        for i in range(4, 58, 3):
            L(i, 18, i, 23, fill="#7fb3cd")
    elif code == "L":
        for i in range(8, 56, 6):
            L(i, 12, i, 36, fill="#b9c1c9")
        for j in range(12, 37, 6):
            L(8, j, 54, j, fill="#b9c1c9")
    elif code == "M":
        cv.create_polygon(x + 10 * s, y + 8 * s, x + 30 * s, y + 38 * s,
                          x + 26 * s, y + 40 * s, x + 6 * s, y + 10 * s,
                          fill="#31363c", outline="#1b1f23")
        cv.create_polygon(x + 52 * s, y + 8 * s, x + 32 * s, y + 38 * s,
                          x + 36 * s, y + 40 * s, x + 56 * s, y + 10 * s,
                          fill="#31363c", outline="#1b1f23")
    elif code in ("N", "O", "P"):
        cols = {"N": "#5aa9e6", "O": "#f2f2f0", "P": "#dcecf5"}
        R(8, 8, 54, 40, fill="#e9edf1", outline="#b6bec6", stipple="gray50")
        for i, (dx, dy) in enumerate(((16, 16), (28, 22), (38, 15),
                                      (22, 30), (36, 30), (44, 24))):
            O(dx, dy, dx + 8, dy + 8, fill=cols[code], outline="#8d97a1")
    elif code == "Q":
        for i, col in enumerate(("#5aa9e6", "#8fd3c7", "#e2544a")):
            cv.create_polygon(x + (8 + i * 18) * s, y + 10 * s,
                              x + (22 + i * 18) * s, y + 10 * s,
                              x + (18 + i * 18) * s, y + 40 * s,
                              x + (12 + i * 18) * s, y + 40 * s,
                              fill=col, outline="#5b6068")
    elif code == "R":
        R(8, 18, 44, 28, fill="#e8f1f6", outline="#a9b6c0")
        R(44, 21, 56, 25, fill="#b9c1c9", outline="#8d959d")
        L(8, 23, 2, 23, fill="#8d959d", width=3)
    elif code == "S":
        for dy in (12, 22, 32):
            R(10, dy, 20, dy + 6, fill="#7fc48a", outline="#4d8a58")
            L(20, dy + 3, 52, dy + 3, fill="#c8ccd0", width=2)
    elif code == "T":
        for dx in (10, 34):
            R(dx, 10, dx + 16, 38, fill="#d8c39a", outline="#a08a5f")
            L(dx + 4, 10, dx + 4, 38, fill="#a08a5f")
    elif code == "U":
        O(12, 6, 50, 44, fill="#2b2f33", outline="#15181b")
        O(17, 11, 45, 39, fill="#cfd6dd", outline="#9aa2aa")
        cv.create_text(x + 31 * s, y + 25 * s, text="0:00", fill="#22262a",
                       font=("Consolas", int(7 * s), "bold"))
    elif code == "V":
        O(10, 10, 52, 34, fill="#f4f4f2", outline="#c2c2be")
        L(31, 34, 31, 44, fill="#8d959d", width=3)
    elif code == "W":
        cv.create_line(x + 6 * s, y + 12 * s, x + 30 * s, y + 34 * s,
                       x + 56 * s, y + 14 * s, fill="#222", width=4, smooth=True)
        R(2, 8, 14, 18, fill="#333", outline="#111")
    elif code == "X":
        cv.create_polygon(x + 14 * s, y + 8 * s, x + 48 * s, y + 8 * s,
                          x + 48 * s, y + 40 * s, x + 14 * s, y + 40 * s,
                          fill="#f6f6f2", outline="#c8c8c0")


class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title(T("EuPhO 2026 실험 시뮬레이터 — 음향 부양",
                     "EuPhO 2026 Experiment Simulator — Acoustic Levitation")
                   + "   v" + APP_VERSION)
        self.geometry("1520x930")
        self.minsize(1240, 780)
        self.configure(bg=BG)
        self.world = World()
        self._style()
        self._build()
        self._last = time.time()
        self.after(40, self._tick)

    # ------------------------------------------------------------------ #
    def _style(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure(".", background=PANEL, foreground=FG,
                     fieldbackground=PANEL2, font=("Segoe UI", 9))
        st.configure("TNotebook", background=BG, borderwidth=0)
        st.configure("TNotebook.Tab", background=PANEL, foreground=FG_DIM,
                     padding=(16, 8), font=("Segoe UI", 10, "bold"))
        st.map("TNotebook.Tab", background=[("selected", PANEL2)],
               foreground=[("selected", ACC)])
        st.configure("TFrame", background=PANEL)
        st.configure("Card.TFrame", background=PANEL2, relief="flat")
        st.configure("TLabel", background=PANEL, foreground=FG)
        st.configure("Dim.TLabel", background=PANEL, foreground=FG_DIM)
        st.configure("H.TLabel", background=PANEL, foreground=ACC,
                     font=("Segoe UI", 12, "bold"))
        st.configure("TButton", background=PANEL2, foreground=FG,
                     borderwidth=1, focusthickness=0, padding=(8, 4))
        st.map("TButton", background=[("active", "#313a45")])
        st.configure("TCheckbutton", background=PANEL, foreground=FG)
        st.configure("TRadiobutton", background=PANEL, foreground=FG)
        st.configure("TCombobox", fieldbackground=PANEL2, background=PANEL2)
        st.configure("Horizontal.TScale", background=PANEL)
        st.configure("Treeview", background="#191f26", fieldbackground="#191f26",
                     foreground=FG, rowheight=21)
        st.configure("Treeview.Heading", background=PANEL2, foreground=ACC)

    # ------------------------------------------------------------------ #
    def _build(self):
        top = tk.Frame(self, bg=BG, height=40)
        top.pack(fill="x", side="top")
        tk.Label(top, text="EuPhO 2026  ·  " +
                 T("음향 부양 (20점)", "Acoustic levitation (20 pts)"),
                 bg=BG, fg=ACC, font=("Segoe UI", 13, "bold")).pack(
                     side="left", padx=14, pady=6)
        self.status = tk.Label(top, text="", bg=BG, fg=FG_DIM,
                               font=("Segoe UI", 9))
        self.status.pack(side="right", padx=14)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tab_over = ttk.Frame(self.nb)
        self.tab_asm = ttk.Frame(self.nb)
        self.tab_e1 = ttk.Frame(self.nb)
        self.tab_bench = ttk.Frame(self.nb)
        self.tab_log = ttk.Frame(self.nb)
        self.nb.add(self.tab_over, text=T(" 과제 · 장비 ", " Tasks · Equipment "))
        self.nb.add(self.tab_asm, text=T(" 1. 조립 ", " 1. Assembly "))
        self.nb.add(self.tab_e1, text=T(" 2. E1 음장 탐침 ", " 2. E1 Field probe "))
        self.nb.add(self.tab_bench, text=T(" 3. 레비테이터 벤치 ", " 3. Levitator bench "))
        self.nb.add(self.tab_log, text=T(" 4. 기록 ", " 4. Notebook "))
        self._build_over()
        self._build_asm()
        self._build_e1()
        self._build_bench()
        self._build_log()

    # ------------------------------------------------------------------ #
    def _build_over(self):
        f = self.tab_over
        left = ttk.Frame(f)
        left.pack(side="left", fill="both", expand=False, padx=10, pady=10)
        txt = tk.Text(left, width=62, bg="#161b22", fg=FG, bd=0,
                      font=("Segoe UI", 9), wrap="word", padx=12, pady=10)
        txt.pack(fill="both", expand=True)
        txt.insert("end", T("과제 개요\n", "Task overview\n"), "h")
        for tag, body in [
            ("E1  " + T("음장 탐침 (1.0)", "Probing the acoustic field (1.0)"),
             T("초록 LED(A)와 트랜스듀서(B)로 국소 음향세기에 따라 빛나는 도구를 만들고,"
               " z축 중앙에서 인접한 두 배(antinode) 사이 거리를 어림한다.",
               "Build a tool from the green LEDs (A) and transducer (B) that lights up "
               "according to the local acoustic intensity; estimate the distance between "
               "two adjacent antinodes on the z axis.")),
            ("E2  " + T("레비테이터 성질 (4.0)", "Levitator properties (4.0)"),
             T("a) 트랜스듀서 주파수를 가능한 정밀하게 결정 (v ≈ 340 m/s).\n"
               "b) Mode X 를 I 로 바꾸어 달라진 거동을 기술하고 Δf 와 그 부호를 결정.",
               "a) Determine the transducer frequency as precisely as possible (v ≈ 340 m/s).\n"
               "b) Switch Mode X to I, describe the changed behaviour, determine Δf and its sign.")),
            ("E3  " + T("고체 비드 밀도 (3.0)", "Density of solid beads (3.0)"),
             T("미지 비드(O)의 밀도를 결정한다. 유리 비드(P) 2500 kg/m³, 두 비드는 크기가 같다.\n"
               "힌트 : F = −f(R)P²Δz,  P ∝ U",
               "Determine the density of the unknown beads (O). Glass beads (P): 2500 kg/m³, "
               "same size.\nHint: F = −f(R)P²Δz, P ∝ U")),
            ("E4  " + T("증발 (3.0)", "Evaporation (3.0)"),
             T("액체 I 만 사용. 전압 고정. d(D²)/dt = −γ 에서 γ [m²/s] 를 D ≳ 1.5 mm 에서 결정.\n"
               "b) 완전 증발 시간을 과대/과소평가하게 되는가?",
               "Liquid I only, constant voltage. Determine γ [m²/s] from d(D²)/dt = −γ for "
               "D ≳ 1.5 mm.\nb) Would you over- or underestimate the total evaporation time?")),
            ("E5  " + T("표면장력 (2.5)", "Surface tension (2.5)"),
             T("a) I 과 II 중 어느 쪽 표면장력이 낮은가.\n"
               "b) σ_II = 0.073 N/m 을 이용해 σ_I 결정. 형상은 V 와 P²/σ 에만 의존.",
               "a) Which of I and II has the lower surface tension?\n"
               "b) Determine σ_I given σ_II = 0.073 N/m. The shape depends only on V and P²/σ.")),
            ("E6  " + T("폭발 (4.0)", "Explosion (4.0)"),
             T("액체 II 만 사용.  U_max = √(α/D + β) 의 α [V²·mm], β [V²] 결정.\n"
               "b) 부양 가능한 최대 지름 추정.",
               "Liquid II only. Determine α [V²·mm] and β [V²] in U_max = √(α/D + β).\n"
               "b) Estimate the maximum diameter that can be levitated.")),
            ("E7  " + T("신비한 선 (2.5)", "Mysterious line (2.5)"),
             T("액체 III 만 사용. 액적이 납작해지면 빨간 LED 빛이 스크린에 날카로운 수평선을 만든다.\n"
               "광선 경로를 그리고 굴절률 n 을 추정.",
               "Liquid III only. When the droplet is flat, the red LED light forms a sharp "
               "horizontal line on the screen. Sketch the ray propagation and estimate n.")),
            ("E8  " + T("장비 손상 벌점 (−0.5)", "Damage penalty (−0.5)"), ""),
        ]:
            txt.insert("end", "\n" + tag + "\n", "t")
            if body:
                txt.insert("end", body + "\n", "b")
        txt.insert("end", "\n" + T(
            "⚠ 경고 : 레비테이터 상·하 단자를 단락시키지 마시오. "
            "액체를 전자부품과 트랜스듀서에 흘리지 마시오. "
            "LED 를 전원공급기(G)에 직접 연결하지 마시오.",
            "⚠ Warning: do not short-circuit the top and bottom levitator rails. "
            "Do not spill liquids on the electronics/transducers. "
            "Do not connect the LEDs to the power supply (G).") + "\n", "w")
        txt.tag_config("h", foreground=ACC, font=("Segoe UI", 13, "bold"))
        txt.tag_config("t", foreground=ACC2, font=("Segoe UI", 10, "bold"))
        txt.tag_config("b", foreground=FG)
        txt.tag_config("w", foreground=BAD, font=("Segoe UI", 9, "bold"))
        txt.config(state="disabled")

        right = ttk.Frame(f)
        right.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)
        ttk.Label(right, text=T("장비 목록 (Fig. 1)", "Equipment (Fig. 1)"),
                  style="H.TLabel").pack(anchor="w", pady=(0, 6))
        cv = tk.Canvas(right, bg="#e9eaec", highlightthickness=0)
        cv.pack(fill="both", expand=True)
        self.cv_equip = cv
        cv.bind("<Configure>", lambda e: self._draw_equip())

    def _draw_equip(self):
        cv = self.cv_equip
        cv.delete("all")
        W = max(cv.winfo_width(), 200)
        cols = max(3, W // 190)
        for i, (code, name, note) in enumerate(EQUIP):
            r, c = divmod(i, cols)
            x = 10 + c * (W - 20) / cols
            y = 10 + r * 92
            w = (W - 20) / cols - 8
            cv.create_rectangle(x, y, x + w, y + 84, fill="#f7f8f9",
                                outline="#c9ccd0")
            sprite(cv, code, x + 8, y + 10, 0.95)
            cv.create_text(x + 78, y + 14, text=code, anchor="w",
                           fill="#1b2129", font=("Segoe UI", 11, "bold"))
            cv.create_text(x + 78, y + 34, text=name, anchor="w", width=w - 86,
                           fill="#2c3540", font=("Segoe UI", 8))
            if note:
                cv.create_text(x + 78, y + 66, text=note, anchor="w",
                               width=w - 86, fill="#7a838d",
                               font=("Segoe UI", 7))
        cv.config(scrollregion=cv.bbox("all"))


# ==============================================================================
#  8.  조립 탭
# ==============================================================================
TRAY = [
    ("C", "levitator", T("레비테이터 모듈", "Levitator module")),
    ("L", "net", T("금속망", "Metal net")),
    ("D", "capture", T("낙하물 수집 유닛", "Capture unit")),
    ("W", "powercord", T("전원 코드", "Power cord")),
    ("H+", "cab_gp", T("바나나 케이블 (빨강)", "Banana cable (red)")),
    ("H-", "cab_gm", T("바나나 케이블 (검정)", "Banana cable (black)")),
    ("I", "screen", T("스크린", "Screen")),
    ("H!", "spare", T("여분 바나나 케이블", "Spare banana cable")),
]


class AsmMixin(object):
    def _build_asm(self):
        f = self.tab_asm
        bar = ttk.Frame(f)
        bar.pack(fill="x", padx=10, pady=(8, 0))
        ttk.Label(bar, text=T("부품을 왼쪽 트레이에서 끌어다 알맞은 자리에 놓으십시오.",
                              "Drag the parts from the tray onto their mounting points."),
                  style="H.TLabel").pack(side="left")
        ttk.Button(bar, text=T("초기화", "Reset"),
                   command=self._asm_reset).pack(side="right")
        self.asm_msg = ttk.Label(f, text="", style="Dim.TLabel")
        self.asm_msg.pack(anchor="w", padx=12, pady=2)
        cv = tk.Canvas(f, bg="#20262e", highlightthickness=0)
        cv.pack(fill="both", expand=True, padx=10, pady=8)
        self.cv_asm = cv
        self._drag = None
        cv.bind("<Configure>", lambda e: self._draw_asm())
        cv.bind("<ButtonPress-1>", self._asm_press)
        cv.bind("<B1-Motion>", self._asm_move)
        cv.bind("<ButtonRelease-1>", self._asm_release)

    # ------------------------------------------------------------------ #
    def _asm_reset(self):
        for k in self.world.asm:
            self.world.asm[k] = False
        self.world.shorted = False
        self.world.out_on = False
        self.world.clear_items()
        self.asm_msg.config(text="")
        self._draw_asm()

    def _asm_targets(self):
        return {
            'levitator': (530, 250, 700, 520),
            'net':       (560, 470, 670, 512),
            'capture':   (556, 520, 664, 566),
            'powercord': (30, 300, 90, 470),
            'cab_gp':    (150, 430, 290, 470),
            'cab_gm':    (150, 470, 290, 508),
            'screen':    (930, 250, 1075, 520),
            'short':     (532, 236, 700, 262),
        }

    # ------------------------------------------------------------------ #
    def _draw_asm(self):
        cv = self.cv_asm
        w = self.world
        cv.delete("all")
        W = max(cv.winfo_width(), 400)
        H = max(cv.winfo_height(), 300)
        # 테이블
        cv.create_rectangle(0, 0, W, H, fill="#20262e", outline="")
        cv.create_rectangle(0, 555, W, H, fill="#39424d", outline="")
        cv.create_line(0, 555, W, 555, fill="#5a6572", width=2)

        # ---------- 트레이 ----------
        cv.create_rectangle(8, 8, 168, 548, fill="#171c23", outline="#2f3945")
        cv.create_text(88, 22, text=T("부품 트레이", "Parts tray"), fill=ACC,
                       font=("Segoe UI", 10, "bold"))
        self._tray_hit = []
        y = 40
        for code, key, name in TRAY:
            placed = (key != 'spare') and w.asm.get(key, False)
            box = cv.create_rectangle(16, y, 160, y + 58,
                                      fill="#232b35" if not placed else "#1d2a22",
                                      outline=OK if placed else "#3a4552")
            sprite(cv, code.rstrip('+-!'), 22, y + 6, 0.62)
            cv.create_text(66, y + 16, text=name, anchor="w", width=90,
                           fill=FG if not placed else OK,
                           font=("Segoe UI", 8, "bold"))
            if placed:
                cv.create_text(66, y + 42, text=T("✓ 설치됨", "✓ installed"),
                               anchor="w", fill=OK, font=("Segoe UI", 8))
            elif key == 'spare':
                cv.create_text(66, y + 42, text=T("(예비)", "(spare)"),
                               anchor="w", fill=FG_DIM, font=("Segoe UI", 8))
            self._tray_hit.append((16, y, 160, y + 58, code, key))
            y += 62

        # ---------- 목표 영역 ----------
        tg = self._asm_targets()
        for key, (x1, y1, x2, y2) in tg.items():
            if key == 'short':
                continue
            if not w.asm.get(key, False):
                cv.create_rectangle(x1, y1, x2, y2, dash=(5, 4),
                                    outline="#4c5a6b")
                cv.create_text((x1 + x2) / 2, (y1 + y2) / 2,
                               text=T("여기", "here"), fill="#4c5a6b",
                               font=("Segoe UI", 8))

        # ---------- 전원공급기 G ----------
        rrect(cv, 90, 300, 300, 520, 6, fill="#ded9cf", outline="#a7a196")
        cv.create_rectangle(110, 320, 280, 372, fill="#22262a", outline="#0f1214")
        cv.create_text(195, 346, text="%4.1f V" % (w.U if w.out_on else 0.0),
                       fill="#ff5a3c", font=("Consolas", 20, "bold"))
        cv.create_text(195, 388, text="POWER SUPPLY  0–20 V", fill="#6d685e",
                       font=("Segoe UI", 8))
        cv.create_oval(150, 430, 178, 458, fill="#c0392b", outline="#7d2318")
        cv.create_oval(150, 470, 178, 498, fill="#222", outline="#000")
        cv.create_text(196, 444, text="+", anchor="w", fill="#6d685e",
                       font=("Segoe UI", 10, "bold"))
        cv.create_text(196, 484, text="−", anchor="w", fill="#6d685e",
                       font=("Segoe UI", 10, "bold"))
        if w.asm['powercord']:
            cv.create_line(90, 400, 46, 430, 30, 520, fill="#1a1a1a", width=5,
                           smooth=True)

        # ---------- 전기 박스 F ----------
        rrect(cv, 330, 400, 500, 520, 5, fill="#e7e3da", outline="#a9a49a")
        cv.create_text(415, 414, text="EuPhO 2026", fill="#8a8478",
                       font=("Segoe UI", 8, "bold"))
        cv.create_oval(358, 432, 384, 458, fill="#3a4048", outline="#20242a")
        cv.create_text(371, 468, text="LED", fill="#6d685e",
                       font=("Segoe UI", 7))
        cv.create_oval(444, 432, 470, 458, fill="#c0392b", outline="#7d2318")
        cv.create_text(457, 468, text="MODE X", fill="#6d685e",
                       font=("Segoe UI", 7))
        cv.create_oval(340, 486, 356, 502, fill="#c0392b", outline="#7d2318")
        cv.create_oval(340, 506, 356, 522, fill="#222", outline="#000")
        if w.asm['cab_gp']:
            cv.create_line(164, 444, 250, 420, 348, 494, fill="#c0392b",
                           width=5, smooth=True)
        if w.asm['cab_gm']:
            cv.create_line(164, 484, 250, 470, 348, 514, fill="#111",
                           width=5, smooth=True)
        # F -> 레비테이터 (내장 케이블)
        if w.asm['levitator']:
            cv.create_line(500, 470, 540, 452, 556, 300, fill="#d8a51a",
                           width=3, smooth=True)
            cv.create_line(500, 480, 545, 470, 560, 500, fill="#d8a51a",
                           width=3, smooth=True)

        # ---------- 레일 ----------
        draw_rail(cv, 470, 1090, 528)

        # ---------- 레비테이터 ----------
        if w.asm['levitator']:
            cv.create_rectangle(596, 470, 626, 530, fill="#7d858d",
                                outline="#565e66")
            draw_levitator(cv, 613, 372, 2.35, w, show_led=True)
        # ---------- 수집 유닛 ----------
        if w.asm['capture']:
            rrect(cv, 556, 520, 664, 556, 4, fill="#3d444c", outline="#252a30")
            cv.create_rectangle(556, 520, 664, 528, fill="#59626b", outline="")
        # ---------- 스크린 ----------
        if w.asm['screen']:
            cv.create_polygon(940, 258, 1068, 268, 1060, 520, 932, 512,
                              fill="#cfe6f2", outline="#9dc2d6", stipple="gray50")
            cv.create_line(996, 520, 996, 552, fill="#8d959d", width=4)

        # ---------- 단락 경고 ----------
        if w.shorted:
            cv.create_line(540, 250, 700, 250, fill=BAD, width=5)
            cv.create_text(616, 226, text=T("단락! 트랜스듀서 정지",
                                            "SHORT CIRCUIT — transducers dead"),
                           fill=BAD, font=("Segoe UI", 11, "bold"))

        # ---------- 상태 ----------
        need = [k for k in ('levitator', 'powercord', 'cab_gp', 'cab_gm', 'net')
                if not w.asm[k]]
        if w.shorted:
            s, col = T("단락으로 장비가 손상되었습니다. 초기화하십시오.",
                       "Damaged by a short circuit. Reset the setup."), BAD
        elif need:
            s, col = T("남은 필수 조립: ", "Still required: ") + ", ".join(need), ACC
        else:
            s, col = T("조립 완료 — '레비테이터 벤치' 탭으로 이동하십시오.",
                       "Assembly complete — go to the 'Levitator bench' tab."), OK
        cv.create_text(W - 16, 20, text=s, anchor="e", fill=col,
                       font=("Segoe UI", 10, "bold"))
        cv.create_text(W - 16, 44, anchor="e", fill=FG_DIM,
                       font=("Segoe UI", 8),
                       text=T("⚠ 여분 케이블을 레비테이터 상·하 단자에 걸면 단락됩니다.",
                              "⚠ Bridging the top/bottom levitator rails short-circuits it."))

        if self._drag:
            code, key, mx, my = self._drag
            sprite(cv, code.rstrip('+-!'), mx - 31, my - 23, 1.0)
            cv.create_rectangle(mx - 33, my - 25, mx + 33, my + 25,
                                outline=ACC, dash=(3, 3))

    # ------------------------------------------------------------------ #
    def _asm_press(self, e):
        for (x1, y1, x2, y2, code, key) in getattr(self, "_tray_hit", []):
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                if key != 'spare' and self.world.asm.get(key, False):
                    return
                self._drag = [code, key, e.x, e.y]
                self._draw_asm()
                return

    def _asm_move(self, e):
        if self._drag:
            self._drag[2], self._drag[3] = e.x, e.y
            self._draw_asm()

    def _asm_release(self, e):
        if not self._drag:
            return
        code, key, mx, my = self._drag
        self._drag = None
        w = self.world
        tg = self._asm_targets()
        hit = None
        for k, (x1, y1, x2, y2) in tg.items():
            if x1 <= mx <= x2 and y1 <= my <= y2:
                hit = k
                break
        msg = ""
        if hit is None:
            msg = T("빈 곳입니다.", "Nothing there.")
        elif key == 'spare':
            if hit == 'short':
                w.shorted = True
                w.out_on = False
                w.damage.append(T("레비테이터 단락 (E8-4)",
                                  "Levitator short-circuited (E8-4)"))
                msg = T("⚠ 상·하 단자를 단락시켰습니다! (E8 벌점)",
                        "⚠ You shorted the top and bottom rails! (E8 penalty)")
            else:
                msg = T("여분 케이블은 여기에 쓰지 않습니다.",
                        "The spare cable is not needed there.")
        elif hit == key:
            if key in ('cab_gp', 'cab_gm') and not w.asm['powercord']:
                msg = T("먼저 전원 코드를 연결하십시오.",
                        "Connect the power cord first.")
            elif key == 'net' and not w.asm['levitator']:
                msg = T("먼저 레비테이터를 장착하십시오.",
                        "Mount the levitator module first.")
            else:
                w.asm[key] = True
                msg = T("설치되었습니다.", "Installed.")
        elif hit == 'short':
            msg = T("그 자리는 단자 레일입니다.", "Those are the terminal rails.")
        else:
            msg = T("자리가 맞지 않습니다.", "Wrong mounting point.")
        self.asm_msg.config(text=msg)
        self._draw_asm()
        self._refresh_bench_controls()


# ==============================================================================
#  9.  E1 : 음장 탐침 탭
# ==============================================================================
PALETTE = [
    ('led_f', T("초록 LED (정방향)", "Green LED (forward)")),
    ('led_r', T("초록 LED (역방향)", "Green LED (reversed)")),
    ('hand', T("손으로 두 단자 잡기", "Touch both leads by hand")),
    ('psu', T("전원공급기 G 에 연결", "Connect to power supply G")),
]


class E1Mixin(object):
    def _build_e1(self):
        f = self.tab_e1
        self.e1_slot = [None, None]
        self.e1_ruler0 = random.uniform(-14.0, 14.0)   # 자의 임의 영점 [mm]
        self._e1_drag = None

        left = ttk.Frame(f)
        left.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=8)
        ttk.Label(left, text=T("a) 회로 구성", "a) Circuit"),
                  style="H.TLabel").pack(anchor="w")
        ttk.Label(left, style="Dim.TLabel", wraplength=520, text=T(
            "트랜스듀서는 가해지는 기계적 압력에 따라 전하가 변하는 축전기입니다. "
            "부품을 두 가지 분기 자리에 끌어다 놓아 회로를 완성하십시오.",
            "A transducer is a capacitor whose charge depends on the applied mechanical "
            "pressure. Drag components onto the two branch slots to build your tool.")
                  ).pack(anchor="w", pady=(0, 4))
        cv = tk.Canvas(left, bg="#f3f4f6", height=360, highlightthickness=0)
        cv.pack(fill="both", expand=True)
        self.cv_e1c = cv
        cv.bind("<Configure>", lambda e: self._draw_e1c())
        cv.bind("<ButtonPress-1>", self._e1_press)
        cv.bind("<B1-Motion>", self._e1_move)
        cv.bind("<ButtonRelease-1>", self._e1_release)
        self.e1_msg = ttk.Label(left, text="", style="Dim.TLabel")
        self.e1_msg.pack(anchor="w", pady=3)

        right = ttk.Frame(f)
        right.pack(side="left", fill="both", expand=True, padx=(5, 10), pady=8)
        ttk.Label(right, text=T("b) z축을 따라 탐침 이동",
                                "b) Move the probe along z"),
                  style="H.TLabel").pack(anchor="w")
        bar = ttk.Frame(right)
        bar.pack(fill="x", pady=3)
        ttk.Label(bar, text=T("탐침을 마우스로 위아래로 끌거나 ↑↓ 키를 쓰십시오.",
                              "Drag the probe up/down, or use the ↑ ↓ keys."),
                  style="Dim.TLabel").pack(side="left")
        cv2 = tk.Canvas(right, bg="#14181e", highlightthickness=0)
        cv2.pack(fill="both", expand=True)
        self.cv_e1p = cv2
        cv2.bind("<Configure>", lambda e: self._draw_e1p())
        cv2.bind("<B1-Motion>", self._e1_probe_drag)
        cv2.bind("<Button-1>", self._e1_probe_drag)
        cv2.bind("<Up>", lambda e: self._e1_nudge(+0.2))
        cv2.bind("<Down>", lambda e: self._e1_nudge(-0.2))
        cv2.bind("<Enter>", lambda e: cv2.focus_set())

    # ------------------------------------------------------------------ #
    def _e1_nudge(self, d):
        self.world.probe_z = max(-30.0, min(30.0, self.world.probe_z + d))
        self._draw_e1p()

    def _e1_probe_drag(self, e):
        cv = self.cv_e1p
        H = max(cv.winfo_height(), 200)
        sc = self._e1_sc()
        cy = H * 0.5
        z = (cy - e.y) / sc
        self.world.probe_z = max(-30.0, min(30.0, z))
        self._draw_e1p()

    def _e1_sc(self):
        cv = self.cv_e1p
        H = max(cv.winfo_height(), 200)
        return max(3.0, min(9.0, (H - 60) / 78.0))

    # ------------------------------------------------------------------ #
    def _e1_cfg(self):
        s = sorted([x for x in self.e1_slot if x])
        if self.world.probe_led_blown >= 2:
            return 'blown'
        if 'psu' in s:
            return 'blown'
        leds = [x for x in s if x.startswith('led')]
        if not leds:
            return 'none'
        if len(leds) == 2:
            return 'anti' if self.e1_slot[0] != self.e1_slot[1] else 'same'
        if 'hand' in s:
            return 'one_hand'
        return 'one'

    def _draw_e1c(self):
        cv = self.cv_e1c
        cv.delete("all")
        W = max(cv.winfo_width(), 420)
        cv.create_rectangle(0, 0, W, 400, fill="#f3f4f6", outline="")
        # 팔레트
        cv.create_text(12, 14, text=T("부품", "Components"), anchor="w",
                       fill="#39424d", font=("Segoe UI", 9, "bold"))
        self._e1_hit = []
        for i, (key, name) in enumerate(PALETTE):
            x = 12 + i * 118
            cv.create_rectangle(x, 26, x + 110, 92, fill="#ffffff",
                                outline="#c9ccd0")
            self._pal_icon(cv, key, x + 55, 50)
            cv.create_text(x + 55, 80, text=name, width=104, fill="#39424d",
                           font=("Segoe UI", 7))
            self._e1_hit.append((x, 26, x + 110, 92, key))

        # 회로
        ox, oy = 60, 150
        cv.create_text(ox - 40, oy + 55, text="T", fill="#1b2129",
                       font=("Segoe UI", 12, "bold"))
        cv.create_oval(ox - 62, oy + 33, ox - 18, oy + 77, outline="#1b2129",
                       width=2)
        cv.create_line(ox - 18, oy + 55, ox + 20, oy + 55, fill="#1b2129",
                       width=2)
        cv.create_line(ox + 20, oy - 10, ox + 20, oy + 120, fill="#1b2129",
                       width=2)
        cv.create_line(ox + 20, oy - 10, ox + 300, oy - 10, fill="#1b2129",
                       width=2)
        cv.create_line(ox + 20, oy + 120, ox + 300, oy + 120, fill="#1b2129",
                       width=2)
        cv.create_line(ox + 300, oy - 10, ox + 300, oy + 120, fill="#1b2129",
                       width=2)
        self._e1_slotbox = []
        for i in range(2):
            sy = oy + 10 + i * 66
            x1, x2 = ox + 110, ox + 210
            cv.create_line(ox + 20, sy + 12, x1, sy + 12, fill="#1b2129", width=2)
            cv.create_line(x2, sy + 12, ox + 300, sy + 12, fill="#1b2129", width=2)
            k = self.e1_slot[i]
            if k is None:
                cv.create_rectangle(x1, sy - 12, x2, sy + 36, dash=(4, 3),
                                    outline="#9aa4ae")
                cv.create_text((x1 + x2) / 2, sy + 12,
                               text=T("분기 %d" % (i + 1), "branch %d" % (i + 1)),
                               fill="#9aa4ae", font=("Segoe UI", 8))
            else:
                self._pal_icon(cv, k, (x1 + x2) / 2, sy + 12,
                               lit=(self.world.probe_brightness()
                                    if k.startswith('led') else 0.0))
            self._e1_slotbox.append((x1, sy - 12, x2, sy + 36, i))

        cfg = self._e1_cfg()
        self.world.probe_cfg = cfg
        names = {'anti': T("역병렬 LED 2개 — 가장 밝음",
                           "Two antiparallel LEDs — brightest"),
                 'same': T("같은 방향 LED 2개 — 어둡다",
                           "Two LEDs, same direction — dim"),
                 'one': T("LED 1개 — 어둡다 (반파만 기여)",
                          "Single LED — dim (only one half-cycle)"),
                 'one_hand': T("LED 1개 + 손 — 중간 밝기",
                               "Single LED + hand — moderate"),
                 'none': T("회로 미완성", "Circuit incomplete"),
                 'blown': T("LED 가 파손되었습니다 (E8 벌점)",
                            "The LED is destroyed (E8 penalty)")}
        cv.create_text(12, 330, anchor="w", text=names[cfg],
                       fill="#c0392b" if cfg in ('blown',) else "#39424d",
                       font=("Segoe UI", 9, "bold"))
        if self._e1_drag:
            k, mx, my = self._e1_drag
            self._pal_icon(cv, k, mx, my)

    def _pal_icon(self, cv, key, cx, cy, lit=0.0):
        if key.startswith('led'):
            d = 1 if key == 'led_f' else -1
            col = mix("#1d6b34", "#7dff9a", min(1.0, lit))
            pts = [cx - 9 * d, cy - 9, cx - 9 * d, cy + 9, cx + 9 * d, cy]
            cv.create_polygon(pts, fill=col, outline="#144a24")
            cv.create_line(cx + 9 * d, cy - 10, cx + 9 * d, cy + 10,
                           fill="#144a24", width=2)
            for a in (0, 1):
                cv.create_line(cx + 3, cy - 12 - a * 5, cx + 11, cy - 18 - a * 5,
                               fill="#2a8a45", arrow="last")
        elif key == 'hand':
            cv.create_oval(cx - 12, cy - 10, cx + 12, cy + 12, fill="#f0c9a8",
                           outline="#b08a6a")
            for i in range(4):
                cv.create_line(cx - 9 + i * 6, cy - 10, cx - 9 + i * 6, cy - 20,
                               fill="#f0c9a8", width=4)
        elif key == 'psu':
            cv.create_rectangle(cx - 16, cy - 11, cx + 16, cy + 11,
                                fill="#ded9cf", outline="#a7a196")
            cv.create_text(cx, cy, text="G", fill="#c0392b",
                           font=("Segoe UI", 10, "bold"))

    def _e1_press(self, e):
        for (x1, y1, x2, y2, k) in getattr(self, "_e1_hit", []):
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                self._e1_drag = [k, e.x, e.y]
                self._draw_e1c()
                return
        for (x1, y1, x2, y2, i) in getattr(self, "_e1_slotbox", []):
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                self.e1_slot[i] = None
                self._draw_e1c()
                return

    def _e1_move(self, e):
        if self._e1_drag:
            self._e1_drag[1], self._e1_drag[2] = e.x, e.y
            self._draw_e1c()

    def _e1_release(self, e):
        if not self._e1_drag:
            return
        k = self._e1_drag[0]
        self._e1_drag = None
        for (x1, y1, x2, y2, i) in getattr(self, "_e1_slotbox", []):
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                if k == 'psu':
                    self.world.probe_led_blown = 2
                    self.world.damage.append(
                        T("LED 소손 (E8-2)", "LED blown (E8-2)"))
                    self.e1_msg.config(text=T(
                        "LED 를 전원공급기에 연결해 태웠습니다. (경고를 어김 — E8 벌점)",
                        "You connected the LED to the power supply and blew it "
                        "(warning violated — E8 penalty)."))
                    self.e1_slot[i] = 'psu'
                else:
                    self.e1_slot[i] = k
                break
        self._draw_e1c()

    # ------------------------------------------------------------------ #
    def _draw_e1p(self):
        cv = self.cv_e1p
        w = self.world
        cv.delete("all")
        W = max(cv.winfo_width(), 320)
        H = max(cv.winfo_height(), 260)
        sc = self._e1_sc()
        cx, cy = W * 0.46, H * 0.5
        if not w.powered():
            cv.create_text(W / 2, 24, text=T(
                "레비테이터에 전원이 없습니다 (조립·전원 확인).",
                "The levitator is not powered (check assembly / supply)."),
                fill=BAD, font=("Segoe UI", 10, "bold"))
        draw_levitator(cv, cx, cy, sc, w, show_led=False)

        # --- 세로 자 (임의 영점) ---
        rx = cx + 46 * sc
        cv.create_rectangle(rx - 16, cy - 34 * sc, rx + 16, cy + 34 * sc,
                            fill="#8ec8e8", outline="#cfe9f7", stipple="gray25")
        z = -34.0
        while z <= 34.0:
            val = z + self.e1_ruler0
            k = round(val * 1.0)
            if abs(val - k) < 0.02:
                ln = 13 if k % 10 == 0 else (8 if k % 5 == 0 else 5)
                cv.create_line(rx - 16, cy - z * sc, rx - 16 + ln, cy - z * sc,
                               fill="#eaf6ff")
                if k % 10 == 0:
                    cv.create_text(rx + 6, cy - z * sc, text=str(int(k // 10)),
                                   fill="#eaf6ff", font=("Consolas", 8))
            z += 0.5

        # --- 탐침 트랜스듀서 ---
        pz = w.probe_z
        py = cy - pz * sc
        px = cx - 40 * sc
        cv.create_line(px, py, cx - 14 * sc, py, fill="#b9c1c9", width=3)
        draw_transducer_face(cv, cx - 20 * sc, py, 5.0 * sc, 3.2 * sc)
        cv.create_rectangle(px - 74, py - 22, px, py + 22, fill="#2b333d",
                            outline="#47525f")
        b = w.probe_brightness()
        for i, dx in enumerate((-46, -20)):
            col = mix("#1d3a24", "#7dff9a", b)
            cv.create_oval(px + dx - 10, py - 10, px + dx + 10, py + 10,
                           fill=col, outline="#144a24")
            if b > 0.05:
                cv.create_oval(px + dx - 10 - 12 * b, py - 10 - 12 * b,
                               px + dx + 10 + 12 * b, py + 10 + 12 * b,
                               outline=mix("#1d3a24", "#7dff9a", b * 0.6))
        cv.create_text(px - 37, py + 34, text=T("탐침 (B + A)", "probe (B + A)"),
                       fill=FG_DIM, font=("Segoe UI", 8))
        cv.create_text(W / 2, H - 14, fill=FG_DIM, font=("Segoe UI", 8),
                       text=T("자의 영점은 임의입니다 — 눈금 차이만 읽으십시오.",
                              "The ruler zero is arbitrary — read differences only."))


# ==============================================================================
# 10.  레비테이터 벤치 탭
# ==============================================================================
NODE_LABEL = [T("맨 아래", "lowest"), "", "", T("중앙", "centre"), "", "",
              T("맨 위", "highest")]


class BenchMixin(object):
    def _build_bench(self):
        f = self.tab_bench
        self.scr_tool = tk.StringVar(value='ruler')
        self.scr_pan = 0.0
        self._scr_drag = None
        self.mark_seq = 0

        # ---------------- 좌측 제어 패널 ----------------
        pl = tk.Frame(f, bg=PANEL, width=336)
        pl.pack(side="left", fill="y", padx=(8, 4), pady=8)
        pl.pack_propagate(False)
        self._bench_panel(pl)

        # ---------------- 중앙 : 레비테이터 ----------------
        mid = tk.Frame(f, bg=PANEL, width=326)
        mid.pack(side="left", fill="y", padx=4, pady=8)
        mid.pack_propagate(False)
        tk.Label(mid, text=T("레비테이터 (실물 크기 관찰)",
                             "Levitator (direct view)"),
                 bg=PANEL, fg=ACC, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.cv_lev = tk.Canvas(mid, bg="#14181e", highlightthickness=0)
        self.cv_lev.pack(fill="both", expand=True, pady=4)
        self.cv_lev.bind("<Configure>", lambda e: self._draw_lev())

        # ---------------- 우측 : 스크린 ----------------
        rt = tk.Frame(f, bg=PANEL)
        rt.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)
        tb = tk.Frame(rt, bg=PANEL)
        tb.pack(fill="x")
        tk.Label(tb, text=T("스크린 (I)", "Screen (I)"), bg=PANEL, fg=ACC,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        for key, lab in (('ruler', T("자 이동", "move ruler")),
                         ('mark', T("표시", "mark")),
                         ('normal', T("법선 작도", "normal line")),
                         ('line', T("자유선", "free line"))):
            ttk.Radiobutton(tb, text=lab, value=key, variable=self.scr_tool
                            ).pack(side="left", padx=3)
        ttk.Button(tb, text=T("작도 지우기", "clear drawing"),
                   command=self._scr_clear).pack(side="right")
        tk.Label(tb, text=T("  (휠: 자 회전)", "  (wheel: rotate ruler)"),
                 bg=PANEL, fg=FG_DIM, font=("Segoe UI", 8)).pack(side="right")
        self.cv_scr = tk.Canvas(rt, bg="#0a0407", highlightthickness=0)
        self.cv_scr.pack(fill="both", expand=True, pady=4)
        self.cv_scr.bind("<Configure>", lambda e: self._draw_scr())
        self.cv_scr.bind("<ButtonPress-1>", self._scr_press)
        self.cv_scr.bind("<B1-Motion>", self._scr_move)
        self.cv_scr.bind("<ButtonRelease-1>", lambda e: setattr(self, "_scr_drag", None))
        self.cv_scr.bind("<MouseWheel>", self._scr_wheel)
        self.cv_scr.bind("<Button-4>", lambda e: self._scr_wheel_d(+1))
        self.cv_scr.bind("<Button-5>", lambda e: self._scr_wheel_d(-1))

        pan = tk.Frame(rt, bg=PANEL)
        pan.pack(fill="x")
        tk.Label(pan, text=T("스크린 상하 위치", "screen height"), bg=PANEL,
                 fg=FG_DIM, font=("Segoe UI", 8)).pack(side="left")
        self.sc_pan = tk.Scale(pan, from_=-420, to=420, orient="horizontal",
                               bg=PANEL, fg=FG_DIM, troughcolor="#151a20",
                               highlightthickness=0, showvalue=False, length=280,
                               command=lambda v: self._set_pan(float(v)))
        self.sc_pan.set(0)
        self.sc_pan.pack(side="left", padx=6)

    def _set_pan(self, v):
        self.scr_pan = v
        self._draw_scr()

    # ------------------------------------------------------------------ #
    def _sec(self, parent, title):
        lf = tk.LabelFrame(parent, text=title, bg=PANEL, fg=ACC,
                           font=("Segoe UI", 9, "bold"), bd=1,
                           relief="groove", labelanchor="nw")
        lf.pack(fill="x", pady=4)
        return lf

    def _bench_panel(self, p):
        w = self.world
        # ---- 전원공급기 ----
        g = self._sec(p, T("전원공급기 G", "Power supply G"))
        self.lbl_volt = tk.Label(g, text="0.0 V", bg="#22262a", fg="#ff5a3c",
                                 font=("Consolas", 22, "bold"), width=9)
        self.lbl_volt.pack(pady=4)
        r1 = tk.Frame(g, bg=PANEL)
        r1.pack()
        for d, lab in ((-1.0, "−1.0"), (-0.1, "−0.1"), (+0.1, "+0.1"),
                       (+1.0, "+1.0")):
            ttk.Button(r1, text=lab, width=5,
                       command=lambda dd=d: self._dV(dd)).pack(side="left", padx=1)
        self.sc_volt = tk.Scale(g, from_=0, to=MAX_VOLT, resolution=0.1,
                                orient="horizontal", bg=PANEL, fg=FG,
                                troughcolor="#151a20", highlightthickness=0,
                                showvalue=False, length=300,
                                command=self._setV)
        self.sc_volt.set(w.U)
        self.sc_volt.pack(pady=2)
        self.btn_out = ttk.Button(g, text=T("출력 ON", "OUTPUT ON"),
                                  command=self._toggle_out)
        self.btn_out.pack(pady=3)

        # ---- 전기 박스 ----
        b = self._sec(p, T("전기 박스 F", "Electrical box F"))
        r = tk.Frame(b, bg=PANEL)
        r.pack(fill="x", pady=2)
        self.var_led = tk.BooleanVar(value=True)
        ttk.Checkbutton(r, text=T("빨간 LED", "red LED"), variable=self.var_led,
                        command=self._set_led).pack(side="left", padx=6)
        self.var_mx = tk.StringVar(value='O')
        ttk.Radiobutton(r, text="Mode X : O", value='O', variable=self.var_mx,
                        command=self._set_mx).pack(side="left")
        ttk.Radiobutton(r, text="I", value='I', variable=self.var_mx,
                        command=self._set_mx).pack(side="left")

        # ---- 광학 ----
        o = self._sec(p, T("광학 배치", "Optical layout"))
        self._spin(o, T("LED 앞면 ~ 레비테이터 축 [mm]",
                        "LED front face → axis [mm]"), 8, 90, 1.0,
                   'a_face', w.a_face)
        self._spin(o, T("레비테이터 축 ~ 스크린 [mm]", "axis → screen [mm]"),
                   80, 900, 10.0, 'b_screen', w.b_screen)
        self._spin(o, T("LED 연직 정렬 (나사 2) [mm]",
                        "LED vertical alignment (screw 2) [mm]"),
                   -6, 6, 0.2, 'led_dy', w.led_dy)

        # ---- 자 ----
        k = self._sec(p, T("투명 자 K", "Transparent ruler K"))
        self.var_ruler = tk.StringVar(value='screen')
        for val, lab in (('screen', T("스크린에 댐", "against the screen")),
                         ('levitator', T("레비테이터 중심에 세움",
                                         "upright at levitator centre")),
                         ('away', T("치움", "put away"))):
            ttk.Radiobutton(k, text=lab, value=val, variable=self.var_ruler,
                            command=self._set_ruler).pack(anchor="w", padx=6)

        # ---- 물체 ----
        s = self._sec(p, T("고체 비드 (핀셋 M)", "Solid beads (tweezers M)"))
        self.var_bead = tk.StringVar(value='styro')
        rb = tk.Frame(s, bg=PANEL)
        rb.pack(fill="x")
        for val, lab in (('styro', T("N 스티로폼", "N styrofoam")),
                         ('pp', T("O 흰색", "O white")),
                         ('glass', T("P 유리", "P glass"))):
            ttk.Radiobutton(rb, text=lab, value=val, variable=self.var_bead
                            ).pack(side="left")
        self.sc_h = tk.Scale(s, from_=17, to=-17, resolution=0.5,
                             orient="horizontal", bg=PANEL, fg=FG_DIM,
                             troughcolor="#151a20", highlightthickness=0,
                             showvalue=False, length=300,
                             label=T("핀셋 높이", "tweezer height"))
        self.sc_h.set(0)
        self.sc_h.pack()
        rb2 = tk.Frame(s, bg=PANEL)
        rb2.pack(fill="x", pady=2)
        ttk.Button(rb2, text=T("비드 넣기", "place bead"),
                   command=self._add_bead).pack(side="left", padx=3)
        ttk.Button(rb2, text=T("여러 개 넣기", "place several"),
                   command=self._add_many).pack(side="left", padx=3)

        # ---- 액체 ----
        q = self._sec(p, T("액체 (주사기 R + 바늘 S)",
                           "Liquids (syringes R + needles S)"))
        self.var_liq = tk.StringVar(value='I')
        rq = tk.Frame(q, bg=PANEL)
        rq.pack(fill="x")
        for val in ('I', 'II', 'III'):
            ttk.Radiobutton(rq, text=T("액체 ", "liquid ") + val, value=val,
                            variable=self.var_liq).pack(side="left")
        self.sc_syr = tk.Scale(q, from_=0, to=100, resolution=1,
                               orient="horizontal", bg=PANEL, fg=FG_DIM,
                               troughcolor="#151a20", highlightthickness=0,
                               showvalue=False, length=300,
                               label=T("주사기 밀기 (임의 눈금)",
                                       "syringe push (arbitrary scale)"))
        self.sc_syr.set(45)
        self.sc_syr.pack()
        rq2 = tk.Frame(q, bg=PANEL)
        rq2.pack(fill="x", pady=2)
        ttk.Button(rq2, text=T("액적 주입", "inject droplet"),
                   command=self._add_drop).pack(side="left", padx=3)
        ttk.Button(rq2, text=T("모두 제거", "remove all"),
                   command=self._clear_items).pack(side="left", padx=3)

        # ---- 스톱워치 / 시간 ----
        t = self._sec(p, T("스톱워치 U · 시간", "Stopwatch U · time"))
        self.lbl_sw = tk.Label(t, text="0:00.00", bg="#22262a", fg="#cfd6dd",
                               font=("Consolas", 17, "bold"), width=11)
        self.lbl_sw.pack(pady=3)
        rt = tk.Frame(t, bg=PANEL)
        rt.pack()
        ttk.Button(rt, text=T("시작/정지", "start/stop"), width=9,
                   command=self._sw_toggle).pack(side="left", padx=2)
        ttk.Button(rt, text="LAP", width=5, command=self._sw_lap).pack(side="left", padx=2)
        ttk.Button(rt, text=T("리셋", "reset"), width=6,
                   command=self._sw_reset).pack(side="left", padx=2)
        rt2 = tk.Frame(t, bg=PANEL)
        rt2.pack(pady=2)
        tk.Label(rt2, text=T("배속", "speed"), bg=PANEL, fg=FG_DIM,
                 font=("Segoe UI", 8)).pack(side="left")
        self.var_sp = tk.StringVar(value='1')
        for v in ('1', '2', '5', '20'):
            ttk.Radiobutton(rt2, text=v + "×", value=v, variable=self.var_sp,
                            command=self._set_speed).pack(side="left")
        self.lbl_laps = tk.Label(t, text="", bg=PANEL, fg=FG_DIM, justify="left",
                                 font=("Consolas", 8), anchor="w")
        self.lbl_laps.pack(fill="x", padx=6)

        self.bench_msg = tk.Label(p, text="", bg=PANEL, fg=ACC,
                                  font=("Segoe UI", 8), wraplength=320,
                                  justify="left")
        self.bench_msg.pack(fill="x", pady=4)

    def _spin(self, parent, label, lo, hi, step, attr, init):
        fr = tk.Frame(parent, bg=PANEL)
        fr.pack(fill="x", pady=1)
        tk.Label(fr, text=label, bg=PANEL, fg=FG_DIM, font=("Segoe UI", 8),
                 anchor="w", width=30, wraplength=210, justify="left"
                 ).pack(side="left")
        var = tk.StringVar(value=("%.1f" % init))

        def apply(*_):
            try:
                v = float(var.get())
            except ValueError:
                return
            v = max(lo, min(hi, v))
            var.set("%.1f" % v)
            setattr(self.world, attr, v)
            self._draw_lev()
            self._draw_scr()
        sp = tk.Spinbox(fr, from_=lo, to=hi, increment=step, width=7,
                        textvariable=var, command=apply, bg="#151a20", fg=FG,
                        insertbackground=FG, buttonbackground=PANEL2,
                        font=("Consolas", 10))
        sp.pack(side="right", padx=4)
        sp.bind("<Return>", apply)
        sp.bind("<FocusOut>", apply)

    # ------------------------------------------------------------------ #
    def _refresh_bench_controls(self):
        try:
            self._draw_lev()
            self._draw_scr()
        except Exception:
            pass

    def _dV(self, d):
        self.world.U = max(0.0, min(MAX_VOLT, round(self.world.U + d, 2)))
        self.sc_volt.set(self.world.U)

    def _setV(self, v):
        self.world.U = float(v)

    def _sync_volt(self):
        """슬라이더를 항상 기준으로 삼는다 (Tk 버전에 따라 set() 이 command 를
        호출하지 않는 경우가 있어 매 틱마다 재동기화한다)."""
        try:
            u = float(self.sc_volt.get())
        except Exception:
            return
        if abs(u - self.world.U) > 1e-9:
            self.world.U = u

    def _toggle_out(self):
        w = self.world
        if w.shorted:
            self._msg(T("단락으로 손상되었습니다. 조립 탭에서 초기화하십시오.",
                        "Damaged by a short. Reset in the assembly tab."))
            return
        need = [k for k in ('levitator', 'powercord', 'cab_gp', 'cab_gm')
                if not w.asm[k]]
        if need and not w.out_on:
            self._msg(T("조립이 끝나지 않았습니다: ", "Assembly incomplete: ")
                      + ", ".join(need))
            return
        if not w.asm['net'] and not w.out_on:
            self._msg(T("금속망(L)을 먼저 놓으십시오.",
                        "Place the metal net (L) first."))
            return
        w.out_on = not w.out_on
        self.btn_out.config(text=T("출력 OFF", "OUTPUT OFF") if w.out_on
                            else T("출력 ON", "OUTPUT ON"))

    def _set_led(self):
        self.world.red_led = self.var_led.get()

    def _set_mx(self):
        self.world.modeX = (self.var_mx.get() == 'I')

    def _set_ruler(self):
        self.world.ruler_place = self.var_ruler.get()
        self._draw_scr()

    def _set_speed(self):
        self.world.speed = float(self.var_sp.get())

    def _msg(self, s):
        self.bench_msg.config(text=s)

    # ---- 스톱워치 ----
    def _sw_toggle(self):
        self.world.sw_run = not self.world.sw_run

    def _sw_lap(self):
        w = self.world
        w.sw_laps.append(w.sw_t)
        if len(w.sw_laps) > 8:
            w.sw_laps = w.sw_laps[-8:]

    def _sw_reset(self):
        self.world.sw_t = 0.0
        self.world.sw_run = False
        self.world.sw_laps = []

    # ---- 물체 ----
    def _nearest_node(self, h):
        best, bd = 0, 1e9
        occupied = set(o.node for o in self.world.alive())
        for n in range(N_NODE_MIN, N_NODE_MAX + 1):
            d = abs(self.world.node_z(n) - h)
            if d < bd and n not in occupied:
                best, bd = n, d
        return best

    def _add_bead(self):
        n = self._nearest_node(float(self.sc_h.get()))
        it, err = self.world.add_item(self.var_bead.get(), n)
        self._msg(err or T("비드를 넣었습니다.", "Bead placed."))
        self._draw_lev()
        self._draw_scr()

    def _add_many(self):
        cnt = 0
        for _ in range(7):
            occupied = set(o.node for o in self.world.alive())
            free = [n for n in range(N_NODE_MIN, N_NODE_MAX + 1)
                    if n not in occupied]
            if not free:
                break
            it, err = self.world.add_item(self.var_bead.get(), free[0])
            if it is None:
                self._msg(err)
                break
            cnt += 1
        self._msg(T("비드 %d개를 넣었습니다." % cnt, "%d beads placed." % cnt))
        self._draw_lev()
        self._draw_scr()

    def _add_drop(self):
        p = float(self.sc_syr.get())
        D = 1.05 + (p / 100.0) ** 1.25 * 3.7
        D *= (1.0 + self.world.rng.gauss(0.0, 0.055))
        D = max(0.6, min(5.6, D))
        n = self._nearest_node(float(self.sc_h.get()))
        it, err = self.world.add_item('drop', n, liquid=self.var_liq.get(), D=D)
        self._msg(err or T("액적을 주입했습니다.", "Droplet injected."))
        self._draw_lev()
        self._draw_scr()

    def _clear_items(self):
        self.world.clear_items()
        self._draw_lev()
        self._draw_scr()

    def _scr_clear(self):
        self.world.marks = []
        self.world.lines = []
        self.mark_seq = 0
        self._draw_scr()


# ------------------------------------------------------------------------------
#  10-b.  레비테이터 직시도 / 스크린 투영도
# ------------------------------------------------------------------------------
class ViewMixin(object):

    # ---------------- 레비테이터 ----------------
    def _draw_lev(self):
        cv = self.cv_lev
        w = self.world
        cv.delete("all")
        W = max(cv.winfo_width(), 200)
        H = max(cv.winfo_height(), 260)
        sc = max(3.0, min(9.0, (H - 40) / 82.0))
        cx, cy = W * 0.52, H * 0.5
        draw_levitator(cv, cx, cy, sc, w)
        U = w.U_eff()
        for it in w.alive():
            y = cy - it.z * sc
            x = cx + it.x * sc
            a, c = it.axes(U)
            if it.kind == 'styro':
                col, oc = "#5aa9e6", "#2c6f9f"
            elif it.kind == 'pp':
                col, oc = "#f4f4f2", "#b0b4b8"
            elif it.kind == 'glass':
                col, oc = "#dcecf5", "#9fc0d2"
            else:
                col, oc = it.liq['color'], it.liq['tint']
            cv.create_oval(x - a * sc, y - c * sc, x + a * sc, y + c * sc,
                           fill=col, outline=oc)
            if it.kind == 'drop':
                cv.create_oval(x - a * sc * .45, y - c * sc * .6,
                               x - a * sc * .05, y - c * sc * .15,
                               fill="#ffffff", outline="")
        if not w.powered():
            cv.create_text(W / 2, 16, text=T("전원 없음", "no power"),
                           fill=BAD, font=("Segoe UI", 9, "bold"))
        elif w.modeX:
            cv.create_text(W / 2, 16, text="MODE X : I", fill=ACC,
                           font=("Segoe UI", 9, "bold"))
        cv.create_text(W / 2, H - 12, fill=FG_DIM, font=("Segoe UI", 8),
                       text=T("육안 관찰 — 확대되지 않음",
                              "naked-eye view — not magnified"))

    # ---------------- 스크린 ----------------
    def _scr_geom(self):
        cv = self.cv_scr
        W = max(cv.winfo_width(), 300)
        H = max(cv.winfo_height(), 300)
        spx = (H - 12) / SCREEN_H
        return W, H, spx, W / 2.0, H / 2.0

    def _to_px(self, xmm, ymm):
        W, H, spx, cx, cy = self._scr_geom()
        return (cx + xmm * spx, cy - (ymm - self.scr_pan) * spx)

    def _to_mm(self, px, py):
        W, H, spx, cx, cy = self._scr_geom()
        return ((px - cx) / spx, (cy - py) / spx + self.scr_pan)

    def _draw_scr(self):
        cv = self.cv_scr
        w = self.world
        cv.delete("all")
        W, H, spx, cx, cy = self._scr_geom()
        on = w.powered() and w.red_led
        # --- 배경 : 빨간 LED 조명 ---
        if on:
            cx0, cy0 = self._to_px(0.0, 0.0)
            for i in range(16, 0, -1):
                r = i * max(W, H) / 13.0
                cv.create_oval(cx0 - r, cy0 - r * 0.92, cx0 + r, cy0 + r * 0.92,
                               fill=mix("#3d070c", "#e0203a", (1 - i / 16.0) ** 1.5),
                               outline="")
        else:
            cv.create_rectangle(0, 0, W, H, fill="#0a0407", outline="")

        # --- 레비테이터 중심에 세운 자의 그림자 ---
        if on and w.ruler_place == 'levitator':
            # 아크릴 자는 투명하므로 몸통은 그림자를 만들지 않는다.
            # 새겨진 눈금선만 그림자가 지며, 그 간격이 곧 배율 M 이다.
            # 자의 0 모서리를 레비테이터 축(x = 0)에 맞추고 눈금은 +x 로 뻗는다.
            M = w.M()
            wid = max(1, int(RUL_ENGRAVE * M * spx))
            i0 = int((w.led_dy - (H / 2.0) / (spx * M) - 2.0))
            i1 = int((w.led_dy + (H / 2.0) / (spx * M) + 2.0))
            for i in range(i0, i1 + 1):
                y = (i * 1.0 - w.led_dy) * M
                px0, py = self._to_px(0.0, y)
                if py < -wid or py > H + wid:
                    continue
                ln = 7.0 if i % 10 == 0 else (5.0 if i % 5 == 0 else 3.0)
                px1, _ = self._to_px(ln * M, y)
                cv.create_line(px0, py, px1, py, fill="#150206", width=wid)

        # --- 물체 그림자 ---
        U = w.U_eff()
        M = w.M()
        for it in w.alive():
            a, c = it.axes(U)
            A = a * M * spx
            C = c * M * spx
            y = (it.z - w.led_dy) * M
            px, py = self._to_px(it.x * M, y)
            if py < -200 or py > H + 200:
                continue
            blur = LED_EMIT_SIZE * (w.b_screen / (w.a_face + LED_INSET)) * spx
            for k in (3, 2, 1):
                t = k / 3.0
                cv.create_oval(px - A - blur * t, py - C - blur * t,
                               px + A + blur * t, py + C + blur * t,
                               fill=mix("#0d0206", "#5a0a12", t * 0.75),
                               outline="")
            cv.create_oval(px - A, py - C, px + A, py + C,
                           fill="#080205", outline="")
            if it.kind == 'drop' and on:
                cv.create_oval(px - A * .55, py - C * .55, px + A * .55,
                               py + C * .55, outline="#1a0409")

        # --- E7 : 수평선 ---
        it = w.line_active()
        if it is not None and on:
            a, c = it.axes(U)
            A = a * M * spx
            y = (it.z - w.led_dy) * M
            px, py = self._to_px(it.x * M, y)
            cv.create_line(0, py, W, py, fill="#ff9aa2", width=1)
            cv.create_line(px - A * 1.25, py, px + A * 1.25, py,
                           fill="#ffd9dd", width=2)

        # --- 사용자 작도 ---
        for (x1, y1, x2, y2) in w.lines:
            p1 = self._to_px(x1, y1)
            p2 = self._to_px(x2, y2)
            cv.create_line(p1[0], p1[1], p2[0], p2[1], fill="#ffe08a", width=1)
        for (mx, my, lab) in w.marks:
            p = self._to_px(mx, my)
            cv.create_line(p[0] - 7, p[1], p[0] + 7, p[1], fill="#7dff9a")
            cv.create_line(p[0], p[1] - 7, p[0], p[1] + 7, fill="#7dff9a")
            cv.create_text(p[0] + 11, p[1] - 9, text=lab, anchor="w",
                           fill="#7dff9a", font=("Segoe UI", 8, "bold"))

        # --- 자 ---
        if w.ruler_place == 'screen':
            draw_ruler(cv, spx, w.ruler_x, w.ruler_y, w.ruler_ang, self._to_px)

        cv.create_text(8, H - 10, anchor="w", fill="#8a6b70",
                       font=("Segoe UI", 8),
                       text=T("스크린 (그림자 투영)", "screen (shadow projection)"))

    # ---------------- 스크린 마우스 ----------------
    def _scr_press(self, e):
        w = self.world
        tool = self.scr_tool.get()
        xmm, ymm = self._to_mm(e.x, e.y)
        if tool == 'ruler':
            if w.ruler_place == 'screen':
                self._scr_drag = ('ruler', xmm - w.ruler_x, ymm - w.ruler_y)
            return
        if tool == 'mark':
            lab = chr(ord('A') + self.mark_seq % 26)
            self.mark_seq += 1
            w.marks.append((xmm, ymm, lab))
        elif tool == 'line':
            self._scr_drag = ('line', xmm, ymm)
            w.lines.append((xmm, ymm, xmm, ymm))
        elif tool == 'normal':
            self._make_normal(xmm, ymm)
        self._draw_scr()

    def _scr_move(self, e):
        if not self._scr_drag:
            return
        w = self.world
        xmm, ymm = self._to_mm(e.x, e.y)
        if self._scr_drag[0] == 'ruler':
            w.ruler_x = xmm - self._scr_drag[1]
            w.ruler_y = ymm - self._scr_drag[2]
        elif self._scr_drag[0] == 'line' and w.lines:
            x0, y0 = self._scr_drag[1], self._scr_drag[2]
            w.lines[-1] = (x0, y0, xmm, ymm)
        self._draw_scr()

    def _scr_wheel(self, e):
        self._scr_wheel_d(1 if e.delta > 0 else -1)

    def _scr_wheel_d(self, d):
        self.world.ruler_ang = (self.world.ruler_ang + d * 2.0) % 360.0
        self._draw_scr()

    def _make_normal(self, xmm, ymm):
        """클릭 위치에서 가장 가까운 액적 윤곽점의 법선을 작도한다."""
        w = self.world
        U = w.U_eff()
        M = w.M()
        best = None
        for it in w.alive():
            a, c = it.axes(U)
            A, C = a * M, c * M
            y0 = (it.z - w.led_dy) * M
            x0 = it.x * M
            for i in range(720):
                th = i * math.pi / 360.0
                px = x0 + A * math.cos(th)
                py = y0 + C * math.sin(th)
                d = (px - xmm) ** 2 + (py - ymm) ** 2
                if best is None or d < best[0]:
                    nx = math.cos(th) / A
                    ny = math.sin(th) / C
                    nn = math.hypot(nx, ny)
                    best = (d, px, py, nx / nn, ny / nn, A)
        if best is None:
            self._msg(T("액적을 찾지 못했습니다.", "No droplet found."))
            return
        _, px, py, nx, ny, A = best
        L = 2.6 * A
        w.lines.append((px - nx * L, py - ny * L, px + nx * L * 0.15,
                        py + ny * L * 0.15))


# ==============================================================================
# 11.  기록 탭
# ==============================================================================
LOG_COLS = [T("과제", "task"), T("항목", "quantity"), T("값", "value"),
            T("단위", "unit"), T("메모", "note")]


class LogMixin(object):
    def _build_log(self):
        f = self.tab_log
        top = ttk.Frame(f)
        top.pack(fill="x", padx=10, pady=8)
        ttk.Label(top, text=T("실험 노트 (직접 읽은 값만 적으십시오)",
                              "Lab notebook (record only what you read yourself)"),
                  style="H.TLabel").pack(side="left")
        ttk.Button(top, text=T("CSV 저장", "Export CSV"),
                   command=self._log_csv).pack(side="right", padx=3)
        ttk.Button(top, text=T("선택 삭제", "Delete selected"),
                   command=self._log_del).pack(side="right", padx=3)
        ttk.Button(top, text=T("계기값 스냅샷", "Snapshot instruments"),
                   command=self._log_snap).pack(side="right", padx=3)

        ent = ttk.Frame(f)
        ent.pack(fill="x", padx=10)
        self.log_vars = []
        for i, c in enumerate(LOG_COLS):
            ttk.Label(ent, text=c, style="Dim.TLabel").grid(row=0, column=i,
                                                            sticky="w")
            v = tk.StringVar()
            e = tk.Entry(ent, textvariable=v, bg="#151a20", fg=FG,
                         insertbackground=FG, width=(10 if i < 2 else
                                                     (12 if i < 4 else 40)))
            e.grid(row=1, column=i, padx=3, pady=3, sticky="we")
            e.bind("<Return>", lambda ev: self._log_add())
            self.log_vars.append(v)
        ttk.Button(ent, text=T("추가", "Add"), command=self._log_add
                   ).grid(row=1, column=len(LOG_COLS), padx=6)

        self.tv = ttk.Treeview(f, columns=[str(i) for i in range(5)],
                               show="headings", height=22)
        for i, c in enumerate(LOG_COLS):
            self.tv.heading(str(i), text=c)
            self.tv.column(str(i), width=(90 if i < 2 else
                                          (110 if i < 4 else 420)),
                           anchor="w")
        self.tv.pack(fill="both", expand=True, padx=10, pady=8)

        ttk.Label(f, style="Dim.TLabel", wraplength=1200, text=T(
            "이 시뮬레이터는 어떤 물리량도 대신 계산하지 않습니다. "
            "배율, 마디 간격, 지름, 밀도, 표면장력, 굴절률, 기울기 등은 "
            "직접 자·스톱워치·전압계 눈금을 읽고 종이에서 계산하십시오.",
            "This simulator never computes a physical quantity for you. "
            "Magnification, node spacing, diameters, densities, surface tension, "
            "refractive index and fitted slopes must all be obtained from your own "
            "ruler / stopwatch / voltmeter readings and worked out on paper.")
                  ).pack(anchor="w", padx=12, pady=(0, 8))

    def _log_add(self):
        row = [v.get().strip() for v in self.log_vars]
        if not any(row):
            return
        self.world.log.append(row)
        self.tv.insert("", "end", values=row)
        for v in self.log_vars[1:4]:
            v.set("")

    def _log_del(self):
        for iid in self.tv.selection():
            idx = self.tv.index(iid)
            if 0 <= idx < len(self.world.log):
                del self.world.log[idx]
            self.tv.delete(iid)

    def _log_snap(self):
        w = self.world
        row = ["", T("계기 스냅샷", "instrument snapshot"),
               "%.1f" % (w.U if w.out_on else 0.0), "V",
               T("스톱워치 %s · LED앞면 %.1f mm · 스크린 %.0f mm · ModeX %s",
                 "stopwatch %s · LED face %.1f mm · screen %.0f mm · ModeX %s")
               % (self._fmt_sw(w.sw_t), w.a_face, w.b_screen,
                  "I" if w.modeX else "O")]
        self.world.log.append(row)
        self.tv.insert("", "end", values=row)

    def _log_csv(self):
        p = filedialog.asksaveasfilename(defaultextension=".csv",
                                         filetypes=[("CSV", "*.csv")])
        if not p:
            return
        with open(p, "w", newline="", encoding="utf-8-sig") as fp:
            wcsv = csv.writer(fp)
            wcsv.writerow(LOG_COLS)
            wcsv.writerows(self.world.log)
        messagebox.showinfo(T("저장", "Saved"), p)

    @staticmethod
    def _fmt_sw(t):
        m = int(t // 60)
        s = t - 60 * m
        return "%d:%05.2f" % (m, s)


# ==============================================================================
# 12.  메인 루프
# ==============================================================================
class MainMixin(object):
    def _tick(self):
        now = time.time()
        dt = min(0.2, now - self._last)
        self._last = now
        w = self.world
        self._sync_volt()
        w.step(dt)

        self.lbl_volt.config(text="%4.1f V" % (w.U if w.out_on else 0.0))
        self.lbl_sw.config(text=self._fmt_sw(w.sw_t))
        if w.sw_laps:
            self.lbl_laps.config(text="\n".join(
                "%d: %s" % (i + 1, self._fmt_sw(t))
                for i, t in enumerate(w.sw_laps)))
        else:
            self.lbl_laps.config(text="")

        tab = self.nb.index(self.nb.select())
        if tab == 2:
            self._draw_e1c()
            self._draw_e1p()
        elif tab == 3:
            self._draw_lev()
            self._draw_scr()

        n_alive = len(w.alive())
        st = []
        st.append(T("전원 ", "power ") + ("ON" if w.powered() else "OFF"))
        st.append(T("물체 %d개", "%d object(s)") % n_alive)
        if w.modeX:
            st.append("MODE X")
        if w.damage:
            st.append(T("손상 %d건 (E8)", "%d damage event(s) (E8)")
                      % len(w.damage))
        self.status.config(text="   ·   ".join(st))
        self.after(40, self._tick)


class Simulator(App, AsmMixin, E1Mixin, BenchMixin, ViewMixin, LogMixin,
                MainMixin):
    pass


def _randomise(seed):
    """Draw this session's hidden values (the official ones for --seed 2026)."""
    global D_NODE, LAM_E, K2, DF_MODEX, U_RISE, MODEX_STEP, S_FALL, RHO_PP, U_DROP_GLASS
    if seed == 2026:
        return
    r = random.Random(seed)
    D_NODE = r.uniform(4.95, 5.15)
    LAM_E = 2.0 * D_NODE
    K2 = 2.0 * (2.0 * math.pi / LAM_E)
    DF_MODEX = -r.uniform(0.58, 0.76)
    U_RISE = D_NODE * abs(DF_MODEX)
    MODEX_STEP = LAM_E / 64.0
    S_FALL = math.sin(K2 * DZ_FALL)
    RHO_PP = r.uniform(850.0, 1100.0)
    U_DROP_GLASS = r.uniform(10.7, 11.4)
    LIQUIDS['I']['sig'] = r.uniform(0.021, 0.026)
    LIQUIDS['I']['g_hi'] = r.uniform(7.5e-9, 10.5e-9)
    LIQUIDS['III']['nref'] = r.uniform(1.33, 1.42)


def main():
    global LANG
    seed = None
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--seed" and i + 1 < len(args):
            seed = int(args[i + 1])
        if a == "--lang" and i + 1 < len(args):
            LANG = "EN" if args[i + 1].lower().startswith("e") else "KO"
    _randomise(seed if seed is not None else random.randrange(1, 10 ** 9))
    app = Simulator()
    app.mainloop()


if __name__ == "__main__":
    main()
