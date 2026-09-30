#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 APhO 2024  (24th Asian Physics Olympiad, Malaysia)  Experimental Problem
 "Gyroscope"  —  가상 실험실 시뮬레이터
=============================================================================
 설계 원칙 :  실제 장비가 주는 것만 준다.
   * 분석 도구, 회귀 그래프, 유도된 물리량, 채점 탭  --  없음
   * 학생이 보는 것 : 자이로스코프 본체, 전원 어댑터 표시창, 스톱워치,
                      각도기(1도 눈금), 자(mm 눈금)
   * 회전수(rpm)는 어디에도 표시되지 않는다. 문제지 Table 1 만이 단서다.

 의존성 : 파이썬 표준 라이브러리(tkinter) 뿐.  numpy / matplotlib 불필요.
=============================================================================
"""
LANG = "EN"          # the KO edition differs only in this line

import math
import random
import tkinter as tk
from tkinter import ttk

# =========================================================================
#  0.  물리 상수 / 장비 제원   (문제지 + 공식 채점표에서 역산)
# =========================================================================
G = 9.81

# --- DC 모터 -------------------------------------------------------------
# 문제지 Table 1(무부하 특성)의 선형 적합 :  rpm = 2074.99 V - 143.66
NOLOAD_SLOPE = 2074.99          # rpm / V
NOLOAD_INTCP = -143.66          # rpm
K_EMF = 4.602099e-3             # 역기전력 상수 [V*s/rad]  = 1/(slope*2pi/60)
R_ARM_COIL = 2.0                # 전기자 저항 [ohm]  (기동 시정수 결정)

# 공기 저항 토크 모형 :  (V - K*w) = (C0 + C1*t) * w^n
#   -> 공식 채점표 B.1 / D.1 의 18개 측정점을 오차 3.4 % 이내로 재현
DRAG_N = 2.590
DRAG_C0 = 7.856826e-08          # 원판 면(面) 항력  ~ R^5
DRAG_C1 = 2.085102e-04          # 원판 테두리 항력 ~ t * R^4
R_REF = 0.100                   # 적합 기준 반지름 [m]

MOTOR_BURN_VOLT = 6.0           # 이 이상 지속 -> 모터 소손
MOTOR_BURN_TIME = 12.0          # [s]
OVERHEAT_TIME = 600.0           # 연속 10분 -> 과열 경고

# --- 질량 [kg] (문제지 "Mass of components") -----------------------------
M_MOTOR = 0.094                 # DC 모터 + 케이스
DISKS = {
    #  key      : (질량, 반지름, 두께, 표시명)
    "20_2": (0.065, 0.100, 0.002, "20 cm × 2 mm"),
    "20_3": (0.089, 0.100, 0.003, "20 cm × 3 mm"),
    "20_4": (0.131, 0.100, 0.004, "20 cm × 4 mm"),
    "26_4": (0.231, 0.130, 0.004, "26 cm × 4 mm"),
}
M_BOLT = 0.0018                 # 스테인리스 볼트+너트 1세트 [kg]

# --- 기구 치수 [m] -------------------------------------------------------
TUBE_L = 0.53                   # 알루미늄 튜브 유효 길이(양 끝 장착점 사이)
PIVOT_Z = 0.30                  # 베어링(피벗) 높이
BASE_R = 0.115                  # 레토르트 스탠드 발 삼각형 반지름
PHI_STOP = math.radians(22.0)   # 튜브가 홀더에 닿는 한계각
TAU_BEARING = 1.2e-3            # 베어링 정지 마찰 토크 [N*m]
ZETA_NUT = 0.16                 # 장동 감쇠비
DAMP_PSI = 0.25
L3_MIN = 0.020                  # 이 이상이면 자이로(세차) 영역 [kg*m^2/s]
LEVEL_SENS = 3.0                # 받침 경사 -> 세차율 변조 감도
JITTER_SIGMA = 0.010            # 항력 계수의 상대 요동 (측정 재현성)
# 팔이 실제로 자리잡는 기울기  phi_eq = SAG0 + SAG_K*|tau|  (SAG_MAX 에서 포화)
SAG0 = math.radians(14.0)
SAG_K = math.radians(175.0)     # [rad/(N*m)]
SAG_MAX = math.radians(20.0)
KNOB_STEP = 5.0e-5              # 별 노브 1클릭 = 0.05 mm
KNOB_RANGE = 3.0e-3             # ±3 mm

# =========================================================================
#  1.  다국어 문자열
# =========================================================================
S_KO = {
    "title": "APhO 2024 실험 — 자이로스코프 가상 실험실",
    "tab_asm": "1. 조립",
    "tab_bench": "2. 실험대",
    "tab_g": "3. 자가균형 (Part G)",
    "tab_info": "장비 제원",
    "tray": "부품 상자  (끌어다 놓으세요)",
    "hint": "안내",
    "assembled": "조립 완료 — [2. 실험대] 탭으로 이동하세요.",
    "next": "다음 부품",
    "reset": "전부 분해",
    "power": "조절식 전원 어댑터",
    "onoff": "전원",
    "volt": "전압",
    "warn6": "⚠ 6 V 초과 — 모터가 탑니다",
    "burnt": "✖ 모터 소손 — 분해 후 재조립 필요",
    "overheat": "⚠ 10분 이상 연속 구동 — 모터를 쉬게 하세요",
    "sw": "스톱워치",
    "start": "시작", "stop": "정지", "lap": "랩", "rs": "초기화",
    "gonio": "각도기",
    "gonio_read": "판독",
    "ruler": "자",
    "armlen": "디스크 ↔ 중심 거리",
    "lock": "별 노브 (튜브 고정)",
    "locked": "잠김", "unlocked": "풀림",
    "level": "받침 수평 조절",
    "knob": "노브",
    "bolts_cw": "볼트+너트 (26 cm 균형추판)",
    "bolts_sd": "볼트+너트 (20 cm 회전판)",
    "sets": "세트",
    "impulse": "카운터웨이트 순간 누르기",
    "lift": "팔 들어올렸다 놓기",
    "trail": "잔상 표시",
    "speed": "시간 배속",
    "view": "시점",
    "disk": "회전 원판",
    "cw": "26 cm 균형추판",
    "nocw": "없음",
    "spin_note": "회전 중 — 원판에 손대지 마세요",
    "g_build": "구성 (아래 → 위)",
    "g_run": "시동", "g_stop": "정지",
    "g_stable": "직립 유지",
    "g_fall": "쓰러짐",
    "g_note": "지지점은 최하단 부품의 중심축입니다.",
}
S_EN = {
    "title": "APhO 2024 Experiment — Gyroscope Virtual Laboratory",
    "tab_asm": "1. Assembly",
    "tab_bench": "2. Bench",
    "tab_g": "3. Self-balancing (Part G)",
    "tab_info": "Specifications",
    "tray": "Parts tray  (drag onto the setup)",
    "hint": "Hint",
    "assembled": "Assembly complete — go to the [2. Bench] tab.",
    "next": "Next part",
    "reset": "Disassemble all",
    "power": "Adjustable power adapter",
    "onoff": "Power",
    "volt": "Voltage",
    "warn6": "⚠ above 6 V — the motor will burn",
    "burnt": "✖ Motor burnt out — disassemble and rebuild",
    "overheat": "⚠ running over 10 min — let the motor rest",
    "sw": "Stopwatch",
    "start": "START", "stop": "STOP", "lap": "LAP", "rs": "RESET",
    "gonio": "Goniometer",
    "gonio_read": "reading",
    "ruler": "Ruler",
    "armlen": "disk ↔ centre distance",
    "lock": "Star knob (tube lock)",
    "locked": "locked", "unlocked": "released",
    "level": "Base levelling",
    "knob": "knob",
    "bolts_cw": "Bolts+nuts (26 cm counterweight disk)",
    "bolts_sd": "Bolts+nuts (20 cm spinning disk)",
    "sets": "sets",
    "impulse": "Press the counterweight briefly",
    "lift": "Lift the arm and release",
    "trail": "Show trail",
    "speed": "Time scale",
    "view": "View",
    "disk": "Spinning disk",
    "cw": "26 cm counterweight disk",
    "nocw": "none",
    "spin_note": "Spinning — do not touch the disk",
    "g_build": "Stack (bottom → top)",
    "g_run": "RUN", "g_stop": "STOP",
    "g_stable": "stays upright",
    "g_fall": "topples",
    "g_note": "The support point is the axis of the lowest component.",
}
S = S_KO if LANG == "KO" else S_EN


def T(k):
    return S.get(k, k)


# 부품 정의 (조립 순서)
PARTS_KO = [
    ("mat", "정전기 방지 매트", None),
    ("stand", "A형 레토르트 스탠드", "mat"),
    ("knobs", "별 노브 ×3 + 핸드 노브", "stand"),
    ("pole", "자이로스코프 수직 스탠드", "knobs"),
    ("tube", "알루미늄 튜브", "pole"),
    ("motor", "DC 모터 + 케이스", "tube"),
    ("coupler", "모터 샤프트 커플러", "motor"),
    ("disk", "20 cm 회전 원판 (M3 볼트)", "coupler"),
    ("adapter", "조절식 전원 어댑터", "pole"),
    ("cw", "26 cm 균형추판 + 와셔 ×2 + M6", "tube"),
]
PARTS_EN = [
    ("mat", "Antistatic mat", None),
    ("stand", "A-shape retort stand", "mat"),
    ("knobs", "3 × star knob + hand knob", "stand"),
    ("pole", "Gyroscope main vertical stand", "knobs"),
    ("tube", "Aluminium tube", "pole"),
    ("motor", "DC motor with case", "tube"),
    ("coupler", "Motor shaft coupler", "motor"),
    ("disk", "20 cm spinning disk (M3 bolts)", "coupler"),
    ("adapter", "Adjustable power adapter", "pole"),
    ("cw", "26 cm counterweight disk + 2 washers + M6", "tube"),
]
PARTS = PARTS_KO if LANG == "KO" else PARTS_EN
REQUIRED = {"mat", "stand", "knobs", "pole", "tube", "motor", "coupler", "disk", "adapter"}


# =========================================================================
#  2.  물리 엔진
# =========================================================================
class Kit:
    """자이로스코프 실험 장치의 상태와 운동을 담는다."""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.reset_all()

    # ---------------- 조립 / 초기화 ----------------
    def reset_all(self):
        self.installed = set()
        self.disk_key = "20_3"
        self.n_bolt_cw = 0
        self.n_bolt_sd = 0
        self.r_m = 0.15            # 원판 중심 ↔ 피벗 거리 [m]
        self.tube_locked = True
        # 받침 다리 초기 높이(제작 공차) — 세션마다 다르다
        self.knob = [self.rng.uniform(-1.2e-3, 1.2e-3) for _ in range(3)]
        self.volt = 0.0
        self.power_on = False
        self.motor_burnt = False
        self.over_volt_t = 0.0
        self.run_t = 0.0
        self.jit = 1.0             # 마찰/공기밀도 요동 (측정 재현성)
        self.reset_motion()
        self.t = 0.0

    def reset_motion(self):
        self.w_s = 0.0             # 원판 자전 각속도 [rad/s]
        self.psi = 0.0             # 세차 방위각 [rad]
        self.dpsi = 0.0
        self.phi = 0.0             # 모터쪽 끝의 앙각 [rad] (아래로 = 음수)
        self.dphi = 0.0
        self.spin_ang = 0.0
        self.trail = []

    def ready(self):
        return REQUIRED <= self.installed

    # ---------------- 기하 / 질량 ----------------
    def disk(self):
        return DISKS[self.disk_key]

    @property
    def r_c(self):
        return TUBE_L - self.r_m

    def m_head(self):
        """모터쪽 끝(모터+원판+회전판에 박은 볼트) 질량"""
        m = M_MOTOR if "motor" in self.installed else 0.0
        if "disk" in self.installed:
            m += self.disk()[0] + self.n_bolt_sd * M_BOLT
        return m

    def m_cw(self):
        if "cw" not in self.installed:
            return 0.0
        return DISKS["26_4"][0] + self.n_bolt_cw * M_BOLT

    def imbalance(self):
        """축에 대한 질량모멘트 Q [kg*m].  + 이면 모터쪽이 무겁다."""
        return self.m_head() * self.r_m - self.m_cw() * self.r_c

    def I3(self):
        """회전 원판의 자전축 관성모멘트 (얇은 원판 I = 1/2 M R^2)"""
        if "disk" not in self.installed:
            return 0.0
        m, R, _, _ = self.disk()
        return 0.5 * m * R * R + self.n_bolt_sd * M_BOLT * R * R

    def I1(self):
        """피벗에 대한 가로 관성모멘트"""
        m, R, _, _ = self.disk() if "disk" in self.installed else (0, 0, 0, "")
        I = self.m_head() * self.r_m ** 2 + self.m_cw() * self.r_c ** 2
        if "disk" in self.installed:
            I += 0.25 * m * R * R
        if "cw" in self.installed:
            I += 0.25 * DISKS["26_4"][0] * DISKS["26_4"][1] ** 2
        return max(I, 1e-6)

    # ---------------- 받침 수평 ----------------
    def tilt(self):
        """(기울기 크기 alpha [rad], 내리막 방위각 [rad])"""
        h = self.knob
        pts = []
        for i in range(3):
            a = math.radians(90 + 120 * i)
            pts.append((BASE_R * math.cos(a), BASE_R * math.sin(a), h[i]))
        (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = pts
        ux, uy, uz = x2 - x1, y2 - y1, z2 - z1
        vx, vy, vz = x3 - x1, y3 - y1, z3 - z1
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        n = math.sqrt(nx * nx + ny * ny + nz * nz)
        if n == 0 or nz == 0:
            return 0.0, 0.0
        nx, ny, nz = nx / n, ny / n, nz / n
        if nz < 0:
            nx, ny, nz = -nx, -ny, -nz
        alpha = math.acos(max(-1.0, min(1.0, nz)))
        az = math.atan2(-ny, -nx)          # 내리막 방향
        return alpha, az

    # ---------------- 모터 ----------------
    def drag_coef(self):
        if "disk" not in self.installed:
            return 0.0, 0.0
        _, R, t, _ = self.disk()
        c0 = DRAG_C0 * (R / R_REF) ** 5
        c1 = DRAG_C1 * (R / R_REF) ** 4
        return c0, c1 * t

    def steady_ws(self, V=None):
        """정상 상태 자전 각속도 (검증/참고용, 이분법)"""
        if V is None:
            V = self.volt if self.power_on else 0.0
        c0, c1 = self.drag_coef()
        cc = c0 + c1
        if cc <= 0 or V <= 0:
            return 0.0
        lo, hi = 0.0, V / K_EMF
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if (V - K_EMF * mid) - cc * mid ** DRAG_N > 0:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def noload_rpm(self, V):
        return max(0.0, NOLOAD_SLOPE * V + NOLOAD_INTCP)

    # ---------------- 시간 적분 ----------------
    def step(self, dt):
        self.t += dt
        if not self.ready():
            return

        V = self.volt if (self.power_on and not self.motor_burnt) else 0.0

        # 베어링 마찰·공기 밀도의 느린 요동 (Ornstein-Uhlenbeck)
        lam = math.exp(-dt / 6.0)
        self.jit = 1.0 + (self.jit - 1.0) * lam + \
            self.rng.gauss(0.0, JITTER_SIGMA) * math.sqrt(max(0.0, 1 - lam * lam))

        # 과전압 / 과열
        if self.power_on and self.volt > MOTOR_BURN_VOLT:
            self.over_volt_t += dt
            if self.over_volt_t > MOTOR_BURN_TIME:
                self.motor_burnt = True
        else:
            self.over_volt_t = max(0.0, self.over_volt_t - dt * 0.5)
        self.run_t = self.run_t + dt if (self.power_on and V > 0) else max(0.0, self.run_t - dt)

        # --- 자전 ---
        I3 = self.I3()
        if I3 > 0:
            c0, c1 = self.drag_coef()
            drag = (c0 + c1) * self.jit * self.w_s ** DRAG_N
            tq = (K_EMF / R_ARM_COIL) * ((V - K_EMF * self.w_s) - drag)
            tq -= 4.0e-4 * (1.0 if self.w_s > 0.5 else self.w_s / 0.5)   # 베어링 마찰
            self.w_s = max(0.0, self.w_s + tq / I3 * dt)
        self.spin_ang = (self.spin_ang + self.w_s * dt) % (2 * math.pi)

        # --- 팔의 운동 ---
        #   빠른 팽이의 선형화 방정식을 정상해(세차) + 장동 진동자로 분해해서 푼다.
        #     ψ̇ = τ /(I₃ω₃)  −  ω_n (φ − φ_eq)      ω_n = I₃ω₃/I₁
        #     φ̈ = −ω_n²(φ − φ_eq) − 2ζω_n φ̇
        #   φ_eq 는 팔이 실제로 자리잡는 기울기 : 베어링 유격 + 튜브 처짐으로
        #   불균형 토크가 커질수록 커지고, 홀더에 닿기 직전(20°)에서 포화한다.
        Q = self.imbalance()
        I1 = self.I1()
        L3 = I3 * self.w_s
        alpha, az = self.tilt()

        # 받침이 기울어져 있으면 세차 토크가 방위각에 따라 변조된다
        # 중력 토크와 각운동량의 수평 성분이 둘 다 cos(phi) 로 줄어 서로 상쇄되므로
        # 세차율은 기울기 phi 에 무관하다 :  psi_dot = Q*g /(I3*w_s)
        mod = 1.0 + LEVEL_SENS * math.sin(alpha) * math.cos(self.psi - az)
        tau_g = Q * G * mod

        sag = min(SAG_MAX, SAG0 + SAG_K * abs(Q * G))
        phi_eq = -math.copysign(sag, Q) if abs(Q) > 1e-9 else 0.0

        if L3 > L3_MIN:
            w_n = L3 / I1
            self.dphi += (-w_n * w_n * (self.phi - phi_eq)
                          - 2 * ZETA_NUT * w_n * self.dphi) * dt
            self.phi += self.dphi * dt
            self.dpsi = tau_g / L3 - w_n * (self.phi - phi_eq)
            self.psi = (self.psi + self.dpsi * dt) % (2 * math.pi)
        else:
            # 정지/저속 : 팔은 처짐 위치로 가라앉고, 방위는 받침 경사에 대한 진자
            self.dphi += (-25.0 * (self.phi - phi_eq) - 7.0 * self.dphi) * dt
            self.phi += self.dphi * dt
            tau_lvl = -G * math.sin(alpha) * Q * math.cos(self.phi) * math.sin(self.psi - az)
            if abs(tau_lvl) < TAU_BEARING and abs(self.dpsi) < 2e-3:
                tau_lvl, self.dpsi = 0.0, 0.0
            elif abs(self.dpsi) > 1e-4:
                tau_lvl -= math.copysign(TAU_BEARING, self.dpsi)
            self.dpsi += (tau_lvl / I1 - DAMP_PSI * self.dpsi) * dt
            self.psi = (self.psi + self.dpsi * dt) % (2 * math.pi)

        # 튜브가 홀더에 닿는 기계적 한계
        if self.phi < -PHI_STOP:
            self.phi, self.dphi = -PHI_STOP, 0.0
        if self.phi > PHI_STOP:
            self.phi, self.dphi = PHI_STOP, 0.0

        # 잔상
        self.trail.append((self.t, self.psi, self.phi))
        while self.trail and self.t - self.trail[0][0] > 2.5:
            self.trail.pop(0)

    # ---------------- 학생이 가하는 자극 ----------------
    def impulse(self, mag=1.0):
        """카운터웨이트를 툭 눌렀다 놓는다 -> 장동 여기"""
        self.dphi += 0.55 * mag
        self.trail.clear()

    def lift_release(self, up=True):
        self.phi += math.radians(6.0) * (1 if up else -1)
        self.dphi = 0.0
        self.trail.clear()

    def turn_arm(self, dpsi_deg):
        self.psi = (self.psi + math.radians(dpsi_deg)) % (2 * math.pi)
        self.dpsi = 0.0

    # ---------------- 측정 장비 ----------------
    def goniometer(self):
        """각도기 판독 : 1도 단위 + 판독 오차"""
        a = math.degrees(abs(self.phi))
        a += self.rng.gauss(0.0, 0.6)
        return max(0, int(round(a)))

    def ruler_cm(self):
        return round(self.r_m * 100.0, 1)

    # ---------------- 방향 벡터 ----------------
    def axis(self):
        c, s = math.cos(self.phi), math.sin(self.phi)
        return (math.cos(self.psi) * c, math.sin(self.psi) * c, s)


# =========================================================================
#  3.  아주 작은 3D 렌더러 (Tk Canvas 위, 직교 투영 + 화가 알고리즘)
# =========================================================================
class Scene:
    def __init__(self):
        self.az = math.radians(38)
        self.el = math.radians(16)
        self.scale = 900.0
        self.cx, self.cy = 460, 330
        self.items = []

    def dirs(self):
        ca, sa = math.cos(self.az), math.sin(self.az)
        ce, se = math.cos(self.el), math.sin(self.el)
        right = (-sa, ca, 0.0)
        up = (-ca * se, -sa * se, ce)
        fwd = (ca * ce, sa * ce, se)
        return right, up, fwd

    def prj(self, p):
        r, u, _ = self.dirs()
        x = (p[0] * r[0] + p[1] * r[1] + p[2] * r[2]) * self.scale + self.cx
        y = -(p[0] * u[0] + p[1] * u[1] + p[2] * u[2]) * self.scale + self.cy
        return x, y

    def depth(self, p):
        """카메라 방향 성분. 값이 작을수록 멀다 -> 먼저 그린다."""
        _, _, f = self.dirs()
        return (p[0] * f[0] + p[1] * f[1] + p[2] * f[2])

    # --- 도형 추가 ---
    def poly(self, pts3, fill, outline="", width=1, dash=None):
        d = sum(self.depth(p) for p in pts3) / len(pts3)
        flat = []
        for p in pts3:
            flat.extend(self.prj(p))
        self.items.append((d, "poly", flat, fill, outline, width, dash))

    def line(self, a, b, fill, width=2, dash=None):
        d = (self.depth(a) + self.depth(b)) / 2
        x1, y1 = self.prj(a)
        x2, y2 = self.prj(b)
        self.items.append((d, "line", [x1, y1, x2, y2], fill, "", width, dash))

    def dot(self, p, r, fill):
        d = self.depth(p)
        x, y = self.prj(p)
        self.items.append((d, "oval", [x - r, y - r, x + r, y + r], fill, "", 1, None))

    def text(self, p, s, fill="#333", size=9, anchor="center"):
        d = self.depth(p) + 1e6      # 항상 맨 위
        x, y = self.prj(p)
        self.items.append((d, "text", [x, y, s, size, anchor], fill, "", 1, None))

    # --- 조합 도형 ---
    @staticmethod
    def _basis(n):
        n = _norm(n)
        a = (0, 0, 1) if abs(n[2]) < 0.9 else (1, 0, 0)
        u = _norm(_cross(n, a))
        v = _cross(n, u)
        return u, v

    def disk3(self, c, n, R, fill, outline="#5a5a5a", seg=48, width=1):
        u, v = self._basis(n)
        pts = [(c[0] + R * (math.cos(t) * u[0] + math.sin(t) * v[0]),
                c[1] + R * (math.cos(t) * u[1] + math.sin(t) * v[1]),
                c[2] + R * (math.cos(t) * u[2] + math.sin(t) * v[2]))
               for t in [2 * math.pi * i / seg for i in range(seg)]]
        self.poly(pts, fill, outline, width)
        return pts

    def cyl(self, a, b, R, fill, outline="#555", seg=14):
        n = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        u, v = self._basis(n)
        ring = []
        for i in range(seg):
            t = 2 * math.pi * i / seg
            o = (R * (math.cos(t) * u[0] + math.sin(t) * v[0]),
                 R * (math.cos(t) * u[1] + math.sin(t) * v[1]),
                 R * (math.cos(t) * u[2] + math.sin(t) * v[2]))
            ring.append(o)
        for i in range(seg):
            o1, o2 = ring[i], ring[(i + 1) % seg]
            quad = [(a[0] + o1[0], a[1] + o1[1], a[2] + o1[2]),
                    (a[0] + o2[0], a[1] + o2[1], a[2] + o2[2]),
                    (b[0] + o2[0], b[1] + o2[1], b[2] + o2[2]),
                    (b[0] + o1[0], b[1] + o1[1], b[2] + o1[2])]
            sh = _shade(fill, 0.62 + 0.38 * (i / seg))
            self.poly(quad, sh, "", 1)
        self.disk3(b, n, R, _shade(fill, 1.05), outline, seg)

    def box(self, c, n, w, h, d, fill):
        """n 방향 길이 d, 나머지 w×h 인 직육면체"""
        u, v = self._basis(n)
        n = _norm(n)
        corners = []
        for sd in (-d / 2, d / 2):
            for sw, sh_ in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
                corners.append((c[0] + n[0] * sd + u[0] * sw + v[0] * sh_,
                                c[1] + n[1] * sd + u[1] * sw + v[1] * sh_,
                                c[2] + n[2] * sd + u[2] * sw + v[2] * sh_))
        faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
                 (2, 3, 7, 6), (1, 2, 6, 5), (0, 3, 7, 4)]
        for k, f in enumerate(faces):
            self.poly([corners[i] for i in f], _shade(fill, 0.72 + 0.09 * k), "#2b2b2b", 1)

    def render(self, cv):
        cv.delete("scene")
        for it in sorted(self.items, key=lambda z: z[0]):
            d, kind, geo, fill, outline, width, dash = it
            if kind == "poly":
                cv.create_polygon(*geo, fill=fill, outline=outline, width=width,
                                  dash=dash, tags="scene")
            elif kind == "line":
                cv.create_line(*geo, fill=fill, width=width, dash=dash,
                               capstyle="round", tags="scene")
            elif kind == "oval":
                cv.create_oval(*geo, fill=fill, outline="", tags="scene")
            elif kind == "text":
                x, y, s, size, anchor = geo
                cv.create_text(x, y, text=s, fill=fill, anchor=anchor,
                               font=("Segoe UI", size), tags="scene")
        self.items = []


def _norm(v):
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _shade(hexcol, f):
    hexcol = hexcol.lstrip("#")
    r, g, b = (int(hexcol[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (max(0, min(255, int(c * f))) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


# =========================================================================
#  4.  장치 그리기
# =========================================================================
COL_MAT = "#1f7a72"
COL_STAND = "#20232a"
COL_ALU = "#c9ccd1"
COL_ACRYL = "#dfe9ef"
COL_MOTOR = "#2c2f36"


def draw_kit(sc, kit, ghost=None, show_gonio=False, trail=False):
    """ghost : 아직 설치되지 않은 다음 부품의 key (점선으로 표시)"""
    ins = kit.installed
    alpha, az = kit.tilt()
    # 받침 기울기를 전체 장치에 적용
    ca, sa = math.cos(alpha), math.sin(alpha)

    def W(p):
        """스탠드 좌표 -> 세계 좌표 (받침 경사 반영, 소각)"""
        x, y, z = p
        dx = -sa * math.cos(az) * z
        dy = -sa * math.sin(az) * z
        return (x + dx, y + dy, z * ca)

    # --- 매트 ---
    if "mat" in ins or ghost == "mat":
        g = ghost == "mat"
        pts = [(-0.20, -0.16, 0.0), (0.20, -0.16, 0.0), (0.20, 0.16, 0.0), (-0.20, 0.16, 0.0)]
        sc.poly(pts, "" if g else COL_MAT, "#8899a0" if g else "#155f59", 2,
                (5, 4) if g else None)

    # --- 레토르트 스탠드 (A형 삼각 받침) ---
    if "stand" in ins or ghost == "stand":
        g = ghost == "stand"
        f = []
        for i in range(3):
            a = math.radians(90 + 120 * i)
            f.append((BASE_R * math.cos(a), BASE_R * math.sin(a), 0.010))
        hub = (0, 0, 0.016)
        for p in f:
            if g:
                sc.line((p[0], p[1], 0.006), hub, "#8899a0", 3, (4, 3))
            else:
                # 두꺼운 주철 다리 (단면 사각)
                sc.box(((p[0] + hub[0]) / 2, (p[1] + hub[1]) / 2, (p[2] + hub[2]) / 2),
                       (p[0] - hub[0], p[1] - hub[1], p[2] - hub[2]),
                       0.020, 0.024, BASE_R, COL_STAND)
        if not g:
            sc.cyl((0, 0, 0.006), (0, 0, 0.034), 0.021, "#33373f")
            sc.disk3((0, 0, 0.034), (0, 0, 1), 0.021, "#41464f", "#1b1e23")

    # --- 별 노브 3개 ---
    if "knobs" in ins or ghost == "knobs":
        g = ghost == "knobs"
        for i in range(3):
            a = math.radians(90 + 120 * i)
            p = (BASE_R * math.cos(a), BASE_R * math.sin(a), 0.0)
            hgt = 0.012 + (kit.knob[i] if "knobs" in ins else 0.0) * 6
            if g:
                sc.dot((p[0], p[1], 0.008), 5, "#8899a0")
            else:
                sc.cyl((p[0], p[1], 0.0), (p[0], p[1], max(0.004, hgt)), 0.016, "#3a3f47")
                sc.disk3((p[0], p[1], max(0.004, hgt)), (0, 0, 1), 0.017, "#4a505a", "#22262c")

    # --- 수직 스탠드 ---
    if "pole" in ins or ghost == "pole":
        g = ghost == "pole"
        a, b = W((0, 0, 0.02)), W((0, 0, PIVOT_Z))
        if g:
            sc.line(a, b, "#8899a0", 3, (5, 4))
        else:
            sc.cyl(a, b, 0.0085, "#b9bfc6", seg=16)
            sc.box(W((0, 0, PIVOT_Z)), (0, 0, 1), 0.052, 0.052, 0.046, "#23262c")

    if not ("pole" in ins):
        return

    piv = W((0, 0, PIVOT_Z))
    u = kit.axis()
    ur = (u[0], u[1], u[2])

    def P(s):
        return (piv[0] + ur[0] * s, piv[1] + ur[1] * s, piv[2] + ur[2] * s)

    # --- 알루미늄 튜브 ---
    if "tube" in ins or ghost == "tube":
        g = ghost == "tube"
        a, b = P(-kit.r_c), P(kit.r_m - 0.035)
        if g:
            sc.line(a, b, "#8899a0", 3, (5, 4))
        else:
            sc.cyl(a, b, 0.004, COL_ALU, seg=12)

    if "tube" not in ins:
        return

    # --- DC 모터 + 케이스 ---
    if "motor" in ins or ghost == "motor":
        g = ghost == "motor"
        c = P(kit.r_m - 0.030)
        if g:
            sc.dot(c, 8, "#8899a0")
        else:
            sc.box(c, ur, 0.038, 0.042, 0.055, COL_MOTOR)
            sc.cyl(P(kit.r_m - 0.004), P(kit.r_m + 0.006), 0.0025, "#9aa0a8")

    # --- 커플러 ---
    if "coupler" in ins or ghost == "coupler":
        g = ghost == "coupler"
        if g:
            sc.dot(P(kit.r_m), 6, "#8899a0")
        else:
            sc.cyl(P(kit.r_m - 0.004), P(kit.r_m + 0.006), 0.009, "#c8a24a")

    # --- 회전 원판 ---
    if "disk" in ins or ghost == "disk":
        g = ghost == "disk"
        m, R, th, _ = kit.disk()
        c = P(kit.r_m)
        if g:
            sc.disk3(c, ur, R, "", "#8899a0")
        else:
            back = P(kit.r_m - th / 2)
            front = P(kit.r_m + th / 2)
            sc.cyl(back, front, R, COL_ACRYL, seg=44)
            # 회전 표시 : 느릴 때만 눈에 보인다
            if kit.w_s < 28.0:
                uu, vv = Scene._basis(ur)
                for k in range(3):
                    t = kit.spin_ang + 2 * math.pi * k / 3
                    e = (front[0] + R * 0.88 * (math.cos(t) * uu[0] + math.sin(t) * vv[0]),
                         front[1] + R * 0.88 * (math.cos(t) * uu[1] + math.sin(t) * vv[1]),
                         front[2] + R * 0.88 * (math.cos(t) * uu[2] + math.sin(t) * vv[2]))
                    sc.line(front, e, "#7d8b94", 2)
            elif kit.w_s > 1.0:
                sc.disk3(P(kit.r_m + th / 2 + 1e-4), ur, R * 0.55, "#eef4f8", "#cbd6de")
            # 볼트 구멍 + 회전판에 박은 볼트
            uu, vv = Scene._basis(ur)
            for k in range(12):
                t = 2 * math.pi * k / 12
                e = (front[0] + R * 0.90 * (math.cos(t) * uu[0] + math.sin(t) * vv[0]),
                     front[1] + R * 0.90 * (math.cos(t) * uu[1] + math.sin(t) * vv[1]),
                     front[2] + R * 0.90 * (math.cos(t) * uu[2] + math.sin(t) * vv[2]))
                filled = k < kit.n_bolt_sd
                sc.dot(e, 3 if filled else 2, "#3a3f47" if filled else "#b9c4cc")

    # --- 26 cm 균형추판 ---
    if "cw" in ins or ghost == "cw":
        g = ghost == "cw"
        Rc = DISKS["26_4"][1]
        c = P(-kit.r_c)
        if g:
            sc.disk3(c, ur, Rc, "", "#8899a0")
        else:
            sc.cyl(P(-kit.r_c - 0.002), P(-kit.r_c + 0.002), Rc, COL_ACRYL, seg=48)
            uu, vv = Scene._basis(ur)
            for k in range(12):
                t = 2 * math.pi * k / 12
                e = (c[0] + Rc * 0.90 * (math.cos(t) * uu[0] + math.sin(t) * vv[0]) + ur[0] * 0.003,
                     c[1] + Rc * 0.90 * (math.cos(t) * uu[1] + math.sin(t) * vv[1]) + ur[1] * 0.003,
                     c[2] + Rc * 0.90 * (math.cos(t) * uu[2] + math.sin(t) * vv[2]) + ur[2] * 0.003)
                filled = k < kit.n_bolt_cw
                sc.dot(e, 4 if filled else 2, "#2b2f35" if filled else "#b9c4cc")

    # --- 조절식 전원 어댑터 (ZY-009) + 전원선 ---
    if "adapter" in ins or ghost == "adapter":
        gh = ghost == "adapter"
        body = [(0.15, -0.235, 0.001), (0.32, -0.235, 0.001),
                (0.32, -0.145, 0.001), (0.15, -0.145, 0.001)]
        sc.poly(body, "" if gh else "#0e1013", "#8899a0" if gh else "#000", 2,
                (5, 4) if gh else None)
        if not gh:
            sc.poly([(0.262, -0.212, 0.004), (0.306, -0.212, 0.004),
                     (0.306, -0.183, 0.004), (0.262, -0.183, 0.004)], "#2a0808", "#000", 1)
            sc.text((0.284, -0.198, 0.006), f"{kit.volt:.1f}", "#ff3b30", 10)
            sc.dot((0.226, -0.196, 0.004), 7, "#c8a24a")
            sc.text((0.19, -0.163, 0.004), "ADAPTER POWER", "#b9c4cc", 7)
            sc.line(W((0, 0, 0.055)), (0.20, -0.150, 0.004), "#c0392b", 2)
            sc.line(W((0, 0, 0.042)), (0.215, -0.150, 0.004), "#111", 2)

    # --- 잔상 ---
    if trail and kit.trail:
        pts = []
        for (tt, ps, ph) in kit.trail[::2]:
            uu = (math.cos(ps) * math.cos(ph), math.sin(ps) * math.cos(ph), math.sin(ph))
            pts.append((piv[0] + uu[0] * kit.r_m, piv[1] + uu[1] * kit.r_m, piv[2] + uu[2] * kit.r_m))
        for i in range(len(pts) - 1):
            sc.line(pts[i], pts[i + 1], "#e08a3c", 2)


# =========================================================================
#  5.  GUI
# =========================================================================
FONT = ("Segoe UI", 10)
FONT_B = ("Segoe UI", 10, "bold")
FONT_S = ("Segoe UI", 9)
FONT_LCD = ("Consolas", 22, "bold")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(T("title"))
        self.geometry("1420x900")
        self.configure(bg="#f2f4f6")
        self.kit = Kit()
        self.scene = Scene()
        self.time_scale = 1.0

        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TNotebook.Tab", font=FONT_B, padding=(16, 8))

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.page_asm = AssemblyPage(self.nb, self)
        self.page_bench = BenchPage(self.nb, self)
        self.page_g = SelfBalancePage(self.nb, self)
        self.page_info = InfoPage(self.nb, self)
        self.nb.add(self.page_asm, text=T("tab_asm"))
        self.nb.add(self.page_bench, text=T("tab_bench"))
        self.nb.add(self.page_g, text=T("tab_g"))
        self.nb.add(self.page_info, text=T("tab_info"))

        self._last = None
        self.after(16, self._tick)

    def _tick(self):
        import time
        now = time.perf_counter()
        if self._last is None:
            self._last = now
        raw = min(0.05, now - self._last)
        self._last = now
        dt = raw * self.time_scale
        sub = max(1, int(dt / 0.004) + 1)
        for _ in range(sub):
            self.kit.step(dt / sub)
        self.page_bench.on_tick(dt)
        self.page_g.on_tick(raw)
        cur = self.nb.index(self.nb.select())
        if cur == 0:
            self.page_asm.redraw()
        elif cur == 1:
            self.page_bench.redraw()
        elif cur == 2:
            self.page_g.redraw()
        self.after(16, self._tick)


# -------------------------------------------------------------------------
class AssemblyPage(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.kit = app.kit
        self.scene = Scene()
        self.scene.cx, self.scene.cy, self.scene.scale = 520, 340, 780
        self.drag = None

        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=(6, 10), pady=6)
        ttk.Label(left, text=T("tray"), font=FONT_B).pack(anchor="w", pady=(0, 6))
        self.cards = {}
        for key, name, req in PARTS:
            f = tk.Frame(left, bg="#ffffff", bd=1, relief="solid",
                         highlightthickness=0, width=290, height=44)
            f.pack(fill="x", pady=3)
            f.pack_propagate(False)
            lb = tk.Label(f, text=name, bg="#ffffff", font=FONT, anchor="w", padx=10)
            lb.pack(fill="both", expand=True)
            for w in (f, lb):
                w.bind("<ButtonPress-1>", lambda e, k=key: self._pick(k))
            self.cards[key] = (f, lb)

        ttk.Label(left, text="  ").pack()
        self.thick_var = tk.StringVar(value="20_3")
        box = ttk.LabelFrame(left, text=T("disk"))
        box.pack(fill="x", pady=6)
        for k in ("20_2", "20_3", "20_4"):
            ttk.Radiobutton(box, text=DISKS[k][3], value=k, variable=self.thick_var,
                            command=self._set_disk).pack(anchor="w", padx=8, pady=1)

        ttk.Button(left, text=T("reset"), command=self._reset).pack(fill="x", pady=(10, 2))
        self.msg = tk.Label(left, text="", bg="#f2f4f6", fg="#1b5e20",
                            font=FONT_B, wraplength=290, justify="left")
        self.msg.pack(fill="x", pady=6)
        self.hint = tk.Label(left, text="", bg="#f2f4f6", fg="#555",
                             font=FONT_S, wraplength=290, justify="left")
        self.hint.pack(fill="x")

        self.cv = tk.Canvas(self, bg="#fbfcfd", highlightthickness=1,
                            highlightbackground="#cfd6dc")
        self.cv.pack(side="left", fill="both", expand=True, pady=6, padx=(0, 6))
        self.cv.bind("<B1-Motion>", self._motion)
        self.cv.bind("<ButtonRelease-1>", self._release)
        self.cv.bind("<Button-3>", self._rot_start)
        self.cv.bind("<B3-Motion>", self._rot)

    # ---- 부품 잡기 / 놓기 ----
    def _pick(self, key):
        if key in self.kit.installed:
            return
        self.drag = key
        self.cards[key][0].config(bg="#fff3cd")
        self.cards[key][1].config(bg="#fff3cd")

    def _motion(self, e):
        if not self.drag:
            return
        self.cv.delete("drag")
        self.cv.create_oval(e.x - 16, e.y - 16, e.x + 16, e.y + 16,
                            outline="#e08a3c", width=2, tags="drag")

    def _release(self, e):
        self.cv.delete("drag")
        if not self.drag:
            return
        key = self.drag
        self.drag = None
        self.cards[key][0].config(bg="#ffffff")
        self.cards[key][1].config(bg="#ffffff")
        req = dict((k, r) for k, _, r in PARTS)[key]
        if req and req not in self.kit.installed:
            self._say(("먼저 설치해야 할 부품이 있습니다." if LANG == "KO"
                       else "A prerequisite part is missing."), err=True)
            return
        tgt = self._slot_xy(key)
        if tgt is None:
            return
        if (e.x - tgt[0]) ** 2 + (e.y - tgt[1]) ** 2 > 95 ** 2:
            self._say(("장착 위치가 아닙니다 — 점선 표시 위에 놓으세요."
                       if LANG == "KO" else "Not the mounting point — drop it on the dashed ghost."),
                      err=True)
            return
        self.kit.installed.add(key)
        if key == "disk":
            self.kit.disk_key = self.thick_var.get()
        self.kit.reset_motion()
        self._say("")

    def _balance_rm(self):
        mh = self.kit.m_head()
        mc = DISKS["26_4"][0]
        return TUBE_L * mc / (mh + mc) if (mh + mc) else 0.15

    def _set_disk(self):
        if "disk" in self.kit.installed:
            self.kit.disk_key = self.thick_var.get()
            self.kit.reset_motion()

    def _reset(self):
        self.kit.reset_all()
        self._say("")

    def _say(self, s, err=False):
        self.msg.config(text=s, fg="#b71c1c" if err else "#1b5e20")

    # ---- 다음 설치할 부품의 화면 좌표 ----
    def _next_ghost(self):
        for key, _, req in PARTS:
            if key in self.kit.installed:
                continue
            if req is None or req in self.kit.installed:
                return key
        return None

    def _slot_xy(self, key):
        sc = self.scene
        piv = (0, 0, PIVOT_Z)
        u = self.kit.axis()
        pos = {
            "mat": (0, 0, 0.0),
            "stand": (0, 0, 0.02),
            "knobs": (BASE_R * math.cos(math.radians(90)), BASE_R * math.sin(math.radians(90)), 0.01),
            "pole": (0, 0, PIVOT_Z * 0.55),
            "tube": piv,
            "motor": (u[0] * (self.kit.r_m - 0.03), u[1] * (self.kit.r_m - 0.03), PIVOT_Z + u[2] * (self.kit.r_m - 0.03)),
            "coupler": (u[0] * self.kit.r_m, u[1] * self.kit.r_m, PIVOT_Z + u[2] * self.kit.r_m),
            "disk": (u[0] * self.kit.r_m, u[1] * self.kit.r_m, PIVOT_Z + u[2] * self.kit.r_m),
            "cw": (-u[0] * self.kit.r_c, -u[1] * self.kit.r_c, PIVOT_Z - u[2] * self.kit.r_c),
            "adapter": (0.24, -0.12, 0.02),
        }
        p = pos.get(key)
        return sc.prj(p) if p else None

    # ---- 시점 회전 ----
    def _rot_start(self, e):
        self._rp = (e.x, e.y)

    def _rot(self, e):
        dx = e.x - self._rp[0]
        dy = e.y - self._rp[1]
        self._rp = (e.x, e.y)
        self.scene.az -= dx * 0.008
        self.scene.el = max(-0.2, min(1.2, self.scene.el + dy * 0.006))

    # ---- 그리기 ----
    def redraw(self):
        sc = self.scene
        g = self._next_ghost()
        w = self.cv.winfo_width() or 900
        h = self.cv.winfo_height() or 700
        sc.cx, sc.cy = w * 0.52, h * 0.62
        sc.scale = min(w, h * 1.4) * 0.85
        draw_kit(sc, self.kit, ghost=g)
        sc.render(self.cv)
        self.cv.delete("hud")
        if g:
            x, y = self._slot_xy(g) or (0, 0)
            self.cv.create_oval(x - 26, y - 26, x + 26, y + 26, outline="#e08a3c",
                                width=2, dash=(4, 3), tags="hud")
            nm = dict((k, n) for k, n, _ in PARTS)[g]
            self.cv.create_text(x, y - 36, text="▼ " + nm, fill="#c2680f",
                                font=FONT_B, tags="hud")
            self.hint.config(text=T("next") + " : " + nm)
        else:
            self.hint.config(text="")
        if self.kit.ready():
            self._say(T("assembled"))
        for key, _, _ in PARTS:
            done = key in self.kit.installed
            self.cards[key][1].config(fg="#9aa3ab" if done else "#111",
                                      text=("✔ " if done else "") +
                                      dict((k, n) for k, n, _ in PARTS)[key])


# -------------------------------------------------------------------------
class BenchPage(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.kit = app.kit
        self.scene = Scene()
        self.sw_run = False
        self.sw_t = 0.0
        self.laps = []
        self._rp = (0, 0)

        self.cv = tk.Canvas(self, bg="#fbfcfd", highlightthickness=1,
                            highlightbackground="#cfd6dc")
        self.cv.pack(side="left", fill="both", expand=True, pady=6, padx=6)
        self.cv.bind("<Button-1>", self._rot_start)
        self.cv.bind("<B1-Motion>", self._rot)

        pan = ttk.Frame(self)
        pan.pack(side="right", fill="y", padx=(0, 6), pady=6)
        self._build_panel(pan)

    # ---------------- 오른쪽 패널 ----------------
    def _build_panel(self, pan):
        # --- 전원 어댑터 ---
        f = ttk.LabelFrame(pan, text=T("power"))
        f.pack(fill="x", pady=4)
        self.lcd = tk.Label(f, text="0.0", bg="#150708", fg="#ff3b30",
                            font=FONT_LCD, width=7, anchor="e", padx=8)
        self.lcd.pack(fill="x", padx=8, pady=(8, 2))
        self.volt_var = tk.DoubleVar(value=0.0)
        s = ttk.Scale(f, from_=0.0, to=12.0, variable=self.volt_var,
                      command=lambda e: self._set_volt())
        s.pack(fill="x", padx=8)
        row = ttk.Frame(f); row.pack(fill="x", padx=8, pady=4)
        for d in (-1.0, -0.4, -0.1, 0.1, 0.4, 1.0):
            ttk.Button(row, text=f"{d:+.1f}", width=4,
                       command=lambda d=d: self._bump(d)).pack(side="left", padx=1)
        self.pw_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text=T("onoff"), variable=self.pw_var,
                        command=self._set_power).pack(anchor="w", padx=8, pady=(0, 4))
        self.warn = tk.Label(f, text="", fg="#b71c1c", bg="#f0f0f0",
                             font=FONT_S, wraplength=280, justify="left")
        self.warn.pack(fill="x", padx=8, pady=(0, 6))

        # --- 스톱워치 ---
        f2 = ttk.LabelFrame(pan, text=T("sw"))
        f2.pack(fill="x", pady=4)
        self.sw_lbl = tk.Label(f2, text="00:00.00", bg="#0d1113", fg="#7CFC98",
                               font=("Consolas", 20, "bold"), anchor="e", padx=8)
        self.sw_lbl.pack(fill="x", padx=8, pady=(8, 2))
        r = ttk.Frame(f2); r.pack(fill="x", padx=8, pady=4)
        ttk.Button(r, text=T("start"), width=7, command=self._sw_start).pack(side="left", padx=2)
        ttk.Button(r, text=T("stop"), width=7, command=self._sw_stop).pack(side="left", padx=2)
        ttk.Button(r, text=T("lap"), width=7, command=self._sw_lap).pack(side="left", padx=2)
        ttk.Button(r, text=T("rs"), width=7, command=self._sw_reset).pack(side="left", padx=2)
        self.lap_box = tk.Listbox(f2, height=5, font=("Consolas", 9))
        self.lap_box.pack(fill="x", padx=8, pady=(2, 8))

        # --- 팔 / 원판 ---
        f3 = ttk.LabelFrame(pan, text=T("lock"))
        f3.pack(fill="x", pady=4)
        self.lock_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(f3, text=T("locked"), variable=self.lock_var,
                        command=self._set_lock).pack(anchor="w", padx=8, pady=2)
        self.arm_var = tk.DoubleVar(value=15.0)
        self.arm_scale = ttk.Scale(f3, from_=8.0, to=40.0, variable=self.arm_var,
                                   command=lambda e: self._set_arm())
        self.arm_scale.pack(fill="x", padx=8)
        self.arm_lbl = tk.Label(f3, text="", font=FONT_B)
        self.arm_lbl.pack(anchor="w", padx=8, pady=(0, 6))

        f4 = ttk.LabelFrame(pan, text=T("disk"))
        f4.pack(fill="x", pady=4)
        self.dk_var = tk.StringVar(value=self.kit.disk_key)
        for k in ("20_2", "20_3", "20_4"):
            ttk.Radiobutton(f4, text=DISKS[k][3], value=k, variable=self.dk_var,
                            command=self._set_disk).pack(anchor="w", padx=8)

        # --- 볼트 ---
        f5 = ttk.LabelFrame(pan, text=T("bolts_cw"))
        f5.pack(fill="x", pady=4)
        self.cwb = tk.Label(f5, text="0 " + T("sets"), font=FONT_B)
        self.cwb.pack(side="left", padx=10, pady=4)
        ttk.Button(f5, text="−", width=3, command=lambda: self._bolt("cw", -1)).pack(side="right", padx=4)
        ttk.Button(f5, text="+", width=3, command=lambda: self._bolt("cw", +1)).pack(side="right")

        f6 = ttk.LabelFrame(pan, text=T("bolts_sd"))
        f6.pack(fill="x", pady=4)
        self.sdb = tk.Label(f6, text="0 " + T("sets"), font=FONT_B)
        self.sdb.pack(side="left", padx=10, pady=4)
        ttk.Button(f6, text="−", width=3, command=lambda: self._bolt("sd", -1)).pack(side="right", padx=4)
        ttk.Button(f6, text="+", width=3, command=lambda: self._bolt("sd", +1)).pack(side="right")

        # --- 수평 조절 ---
        f7 = ttk.LabelFrame(pan, text=T("level"))
        f7.pack(fill="x", pady=4)
        for i in range(3):
            r = ttk.Frame(f7); r.pack(fill="x", padx=8, pady=1)
            ttk.Label(r, text=f"{T('knob')} {i+1}", width=8).pack(side="left")
            ttk.Button(r, text="▲", width=3, command=lambda i=i: self._knob(i, +1)).pack(side="left")
            ttk.Button(r, text="▼", width=3, command=lambda i=i: self._knob(i, -1)).pack(side="left")
            ttk.Button(r, text="▲▲", width=4, command=lambda i=i: self._knob(i, +10)).pack(side="left")
            ttk.Button(r, text="▼▼", width=4, command=lambda i=i: self._knob(i, -10)).pack(side="left")
        r = ttk.Frame(f7); r.pack(fill="x", padx=8, pady=(4, 6))
        ttk.Button(r, text="↺ 90°", width=8, command=lambda: self.kit.turn_arm(90)).pack(side="left", padx=2)
        ttk.Button(r, text="↻ 180°", width=8, command=lambda: self.kit.turn_arm(180)).pack(side="left", padx=2)

        # --- 자극 / 표시 ---
        f8 = ttk.LabelFrame(pan, text="Part F")
        f8.pack(fill="x", pady=4)
        ttk.Button(f8, text=T("impulse"), command=lambda: self.kit.impulse()).pack(fill="x", padx=8, pady=2)
        r = ttk.Frame(f8); r.pack(fill="x", padx=8, pady=(0, 6))
        ttk.Button(r, text=T("lift") + " ↑", command=lambda: self.kit.lift_release(True)).pack(side="left", expand=True, fill="x", padx=1)
        ttk.Button(r, text=T("lift") + " ↓", command=lambda: self.kit.lift_release(False)).pack(side="left", expand=True, fill="x", padx=1)

        f9 = ttk.Frame(pan); f9.pack(fill="x", pady=6)
        self.gonio_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f9, text=T("gonio"), variable=self.gonio_var).pack(side="left")
        self.trail_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f9, text=T("trail"), variable=self.trail_var).pack(side="left", padx=8)
        self.gonio_lbl = tk.Label(f9, text="", font=FONT_B, fg="#0b5394")
        self.gonio_lbl.pack(side="right")

        f10 = ttk.Frame(pan); f10.pack(fill="x", pady=2)
        ttk.Label(f10, text=T("speed")).pack(side="left")
        self.sp_var = tk.StringVar(value="1")
        for v in ("1", "2", "5", "10", "20"):
            ttk.Radiobutton(f10, text=v + "×", value=v, variable=self.sp_var,
                            command=self._set_speed).pack(side="left")

    # ---------------- 조작 ----------------
    def _set_volt(self):
        self.kit.volt = round(self.volt_var.get(), 1)

    def _bump(self, d):
        self.volt_var.set(max(0.0, min(12.0, round(self.volt_var.get() + d, 1))))
        self._set_volt()

    def _set_power(self):
        self.kit.power_on = self.pw_var.get()

    def _set_lock(self):
        self.kit.tube_locked = self.lock_var.get()

    def _set_arm(self):
        if self.kit.tube_locked:
            self.arm_var.set(self.kit.r_m * 100)
            return
        v = max(8.0, min(TUBE_L * 100 - 12.0, self.arm_var.get()))
        self.kit.r_m = v / 100.0

    def _set_disk(self):
        self.kit.disk_key = self.dk_var.get()
        self.kit.reset_motion()

    def _bolt(self, which, d):
        if self.kit.power_on and self.kit.w_s > 5:
            return
        if which == "cw":
            if "cw" not in self.kit.installed:
                return
            self.kit.n_bolt_cw = max(0, min(12, self.kit.n_bolt_cw + d))
        else:
            self.kit.n_bolt_sd = max(0, min(12, self.kit.n_bolt_sd + d))

    def _knob(self, i, n):
        self.kit.knob[i] = max(-KNOB_RANGE, min(KNOB_RANGE,
                                                self.kit.knob[i] + n * KNOB_STEP))

    def _set_speed(self):
        self.app.time_scale = float(self.sp_var.get())

    # ---- 스톱워치 ----
    def _sw_start(self):
        self.sw_run = True

    def _sw_stop(self):
        self.sw_run = False

    def _sw_lap(self):
        if self.sw_run:
            self.laps.append(self.sw_t)
            self.lap_box.insert("end", f"{len(self.laps):2d}  {self._fmt(self.sw_t)}")
            self.lap_box.see("end")

    def _sw_reset(self):
        self.sw_run = False
        self.sw_t = 0.0
        self.laps = []
        self.lap_box.delete(0, "end")

    @staticmethod
    def _fmt(t):
        return f"{int(t)//60:02d}:{t%60:05.2f}"

    # ---- 매 프레임 ----
    def on_tick(self, dt):
        if self.sw_run:
            self.sw_t += dt

    def _rot_start(self, e):
        self._rp = (e.x, e.y)

    def _rot(self, e):
        dx, dy = e.x - self._rp[0], e.y - self._rp[1]
        self._rp = (e.x, e.y)
        self.scene.az -= dx * 0.008
        self.scene.el = max(-0.15, min(1.2, self.scene.el + dy * 0.006))

    # ---- 그리기 ----
    def redraw(self):
        k = self.kit
        sc = self.scene
        w = self.cv.winfo_width() or 900
        h = self.cv.winfo_height() or 700
        sc.cx, sc.cy = w * 0.5, h * 0.66
        sc.scale = min(w, h * 1.35) * 0.82
        draw_kit(sc, k, trail=self.trail_var.get())
        sc.render(self.cv)

        self.cv.delete("hud")
        if not k.ready():
            self.cv.create_text(w / 2, h / 2, font=("Segoe UI", 15),
                                fill="#b71c1c", tags="hud",
                                text=("장치가 조립되지 않았습니다 — [1. 조립] 탭으로 가세요."
                                      if LANG == "KO" else
                                      "The apparatus is not assembled — go to the [1. Assembly] tab."))
        # 각도기
        if self.gonio_var.get() and k.ready():
            self._draw_gonio(w, h)
        self.gonio_lbl.config(text="")

        # 표시값
        self.lcd.config(text=f"{k.volt:4.1f}")
        self.sw_lbl.config(text=self._fmt(self.sw_t))
        self.arm_lbl.config(text=f"{T('ruler')} : {k.ruler_cm():.1f} cm   "
                                f"({T('armlen')})")
        self.arm_var.set(k.r_m * 100)
        self.cwb.config(text=f"{k.n_bolt_cw} " + T("sets"))
        self.sdb.config(text=f"{k.n_bolt_sd} " + T("sets"))
        msg = []
        if k.motor_burnt:
            msg.append(T("burnt"))
        elif k.power_on and k.volt > MOTOR_BURN_VOLT:
            msg.append(T("warn6"))
        if k.run_t > OVERHEAT_TIME:
            msg.append(T("overheat"))
        a, _ = k.tilt()
        msg.append(("받침 기울기 지시계 없음 — 팔의 거동으로 판단하세요."
                    if LANG == "KO" else
                    "No spirit level provided — judge from the behaviour of the arm."))
        self.warn.config(text="\n".join(msg))

    def _draw_gonio(self, w, h):
        """The goniometer held against the tube, drawn square-on in a corner:
        1-degree ticks and the tube edge.  Read it yourself."""
        k = self.kit
        cx, cy, R = w - 190, 190, 150
        cv = self.cv
        cv.create_rectangle(cx - 20, cy - R - 26, cx + R + 26, cy + R + 26,
                            fill="#fbfbf6", outline="#9bb7d4", tags="hud")
        cv.create_arc(cx - R, cy - R, cx + R, cy + R, start=-45, extent=90,
                      style="arc", outline="#0b5394", width=2, tags="hud")
        for dg in range(-45, 46):
            a = math.radians(dg)
            r0 = R - (16 if dg % 10 == 0 else 10 if dg % 5 == 0 else 5)
            cv.create_line(cx + r0 * math.cos(a), cy - r0 * math.sin(a),
                           cx + R * math.cos(a), cy - R * math.sin(a),
                           fill="#0b5394", tags="hud")
            if dg % 10 == 0:
                cv.create_text(cx + (R - 30) * math.cos(a), cy - (R - 30) * math.sin(a),
                               text=str(abs(dg)), font=FONT_S, fill="#0b5394", tags="hud")
        cv.create_line(cx, cy, cx + R, cy, fill="#9bb7d4", dash=(4, 3), tags="hud")
        a = k.phi                       # true elevation of the motor end
        cv.create_line(cx, cy, cx + (R + 12) * math.cos(a), cy - (R + 12) * math.sin(a),
                       fill="#c0392b", width=2, tags="hud")
        cv.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill="#333", tags="hud")
        cv.create_text(cx + 4, cy + R + 12, anchor="w", text=T("gonio"),
                       font=FONT_S, fill="#555", tags="hud")


# -------------------------------------------------------------------------
class SelfBalancePage(ttk.Frame):
    """Part G : 부품을 쌓아 자가균형 장치를 만들고 직립 여부를 본다."""

    STACK_KO = [("motor", "DC 모터 (정지)"), ("cw", "26 cm 원판 (정지)"),
                ("disk", "20 cm 회전 원판 (회전)")]
    STACK_EN = [("motor", "DC motor (static)"), ("cw", "26 cm disk (static)"),
                ("disk", "20 cm disk (spinning)")]

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.stack = []           # 아래->위 (key, z_bottom)
        self.disk_key = "20_2"
        self.volt = 5.0
        self.running = False
        self.w = 0.0
        self.theta = math.radians(4.0)
        self.dtheta = 0.0
        self.phi_prec = 0.0
        self.time = 0.0
        self.scene = Scene()

        pan = ttk.Frame(self); pan.pack(side="right", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(pan, text=T("g_build")); f.pack(fill="x")
        self.list = tk.Listbox(f, height=6, font=FONT)
        self.list.pack(fill="x", padx=8, pady=6)
        opts = self.STACK_KO if LANG == "KO" else self.STACK_EN
        for key, name in opts:
            ttk.Button(f, text="+ " + name, command=lambda k=key: self._add(k)).pack(fill="x", padx=8, pady=1)
        ttk.Button(f, text="↺", command=self._clear).pack(fill="x", padx=8, pady=(6, 8))

        f2 = ttk.LabelFrame(pan, text=T("disk")); f2.pack(fill="x", pady=6)
        self.dk = tk.StringVar(value="20_2")
        for k in ("20_2", "20_3", "20_4"):
            ttk.Radiobutton(f2, text=DISKS[k][3], value=k, variable=self.dk).pack(anchor="w", padx=8)

        f3 = ttk.LabelFrame(pan, text=T("volt")); f3.pack(fill="x", pady=6)
        self.vv = tk.DoubleVar(value=5.0)
        ttk.Scale(f3, from_=0, to=6, variable=self.vv).pack(fill="x", padx=8, pady=6)
        self.vl = tk.Label(f3, text="5.0 V", font=FONT_B); self.vl.pack(pady=(0, 6))

        ttk.Button(pan, text=T("g_run"), command=self._run).pack(fill="x", pady=(8, 2))
        ttk.Button(pan, text=T("g_stop"), command=self._stop).pack(fill="x")
        self.res = tk.Label(pan, text="", font=FONT_B, wraplength=260, justify="left")
        self.res.pack(fill="x", pady=10)
        tk.Label(pan, text=T("g_note"), font=FONT_S, fg="#666",
                 wraplength=260, justify="left").pack(fill="x")

        self.cv = tk.Canvas(self, bg="#fbfcfd", highlightthickness=1,
                            highlightbackground="#cfd6dc")
        self.cv.pack(side="left", fill="both", expand=True, padx=6, pady=6)

    def _add(self, k):
        if k in [s for s in self.stack]:
            return
        self.stack.append(k)
        self._refresh()

    def _clear(self):
        self.stack = []
        self.running = False
        self.res.config(text="")
        self._refresh()

    def _refresh(self):
        self.list.delete(0, "end")
        names = dict(self.STACK_KO if LANG == "KO" else self.STACK_EN)
        for i, k in enumerate(self.stack[::-1]):
            self.list.insert("end", f"{len(self.stack)-i}. {names[k]}")

    # --- 물리 : '잠자는 팽이' 판정 ---
    def _props(self):
        z = 0.0
        M = 0.0
        Ms = 0.0
        I1 = 0.0
        I3 = 0.0
        for k in self.stack:
            if k == "motor":
                m, hh, R = M_MOTOR, 0.055, 0.022
                I1 += m * (hh * hh / 12 + (z + hh / 2) ** 2)
            elif k == "cw":
                m, hh, R = DISKS["26_4"][0], 0.004, DISKS["26_4"][1]
                I1 += m * (0.25 * R * R + (z + hh / 2) ** 2)
            else:
                m, R, hh, _ = DISKS[self.dk.get()]
                I1 += m * (0.25 * R * R + (z + hh / 2) ** 2)
                I3 = 0.5 * m * R * R
            M += m
            Ms += m * (z + hh / 2)
            z += hh
        l = Ms / M if M else 0.0
        return M, l, max(I1, 1e-6), I3

    def _run(self):
        if not self.stack or "disk" not in self.stack:
            self.res.config(text=("회전 원판이 없습니다." if LANG == "KO"
                                  else "No spinning disk in the stack."), fg="#b71c1c")
            return
        self.running = True
        self.theta = math.radians(4.0)
        self.dtheta = 0.0
        self.time = 0.0
        self.w = 0.0

    def _stop(self):
        self.running = False

    def on_tick(self, dt):
        self.vl.config(text=f"{self.vv.get():4.1f} V")
        if not self.running:
            return
        self.time += dt
        M, l, I1, I3 = self._props()
        m, R, th, _ = DISKS[self.dk.get()]
        c0 = DRAG_C0 * (R / R_REF) ** 5
        c1 = DRAG_C1 * (R / R_REF) ** 4 * th
        V = self.vv.get()
        drag = (c0 + c1) * self.w ** DRAG_N
        tq = (K_EMF / R_ARM_COIL) * ((V - K_EMF * self.w) - drag)
        self.w = max(0.0, self.w + tq / max(I3, 1e-6) * dt)
        L3 = I3 * self.w
        crit = L3 * L3 - 4 * I1 * M * G * l
        if crit > 0:          # 잠자는 팽이 : 세차 + 감쇠로 직립
            wn = L3 / I1
            self.dtheta += (-wn * wn * 0.25 * self.theta) * dt
            self.dtheta *= math.exp(-1.2 * dt)
            self.theta = max(0.0, self.theta + self.dtheta * dt)
            self.phi_prec += (M * G * l / max(L3, 1e-6)) * dt
        else:
            self.dtheta += (M * G * l * math.sin(self.theta) / I1) * dt
            self.theta += self.dtheta * dt
            self.phi_prec += (M * G * l / max(L3, 1e-3)) * dt * 0.2
            if self.theta > math.radians(75):
                self.theta = math.radians(75)
                self.dtheta = 0.0

    def redraw(self):
        sc = self.scene
        w = self.cv.winfo_width() or 800
        h = self.cv.winfo_height() or 700
        sc.cx, sc.cy = w * 0.5, h * 0.72
        sc.scale = min(w, h * 1.3) * 1.6
        sc.az = math.radians(35); sc.el = math.radians(14)
        # 바닥
        sc.poly([(-0.12, -0.12, 0), (0.12, -0.12, 0), (0.12, 0.12, 0), (-0.12, 0.12, 0)],
                COL_MAT, "#155f59", 2)
        th, ph = self.theta, self.phi_prec
        n = (math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th))
        z = 0.0
        for k in self.stack:
            if k == "motor":
                hh = 0.055
                c = (n[0] * (z + hh / 2), n[1] * (z + hh / 2), n[2] * (z + hh / 2))
                sc.box(c, n, 0.038, 0.042, hh, COL_MOTOR)
            elif k == "cw":
                hh = 0.004
                a = (n[0] * z, n[1] * z, n[2] * z)
                b = (n[0] * (z + hh), n[1] * (z + hh), n[2] * (z + hh))
                sc.cyl(a, b, DISKS["26_4"][1], COL_ACRYL)
            else:
                m, R, hh, _ = DISKS[self.dk.get()]
                a = (n[0] * z, n[1] * z, n[2] * z)
                b = (n[0] * (z + hh), n[1] * (z + hh), n[2] * (z + hh))
                sc.cyl(a, b, R, COL_ACRYL)
            z += hh
        sc.render(self.cv)


# -------------------------------------------------------------------------
class InfoPage(ttk.Frame):
    TXT_KO = """APhO 2024  실험 문제 — 자이로스코프

[ 제공 장비 ]
  · 자이로스코프 수직 스탠드 ×1        · 조절식 전원 어댑터 ×1 (ZY-009)
  · DC 모터 + 케이스 + 커플러 ×1        · 각도기(goniometer) ×1
  · 20 cm 회전 원판 두께 2 / 3 / 4 mm    · 스톱워치 ×1
  · 26 cm 균형추 원판 ×1                · 정전기 방지 매트, 알루미늄 튜브, 레토르트 스탠드
  · 볼트·너트, 육각렌치, 드라이버, 케이블타이, 양면테이프, 자

[ 부품 질량 ]
  20 cm × 2 mm  →  65 ± 1 g       20 cm × 3 mm  →  89 ± 1 g
  20 cm × 4 mm  → 131 ± 1 g       26 cm × 4 mm  → 231 ± 1 g
  DC 모터(케이스 포함) → 94 g      알루미늄 튜브 질량은 무시한다.

[ Table 1 — DC 모터 무부하 특성 ]  (참고용, 재현 대상 아님)
   3.7 V  176 mA   7 200 rpm      7.4 V  230 mA  15 600 rpm
   4.8 V  185 mA   9 700 rpm      9.6 V  245 mA  19 800 rpm
   6.0 V  205 mA  12 600 rpm     12.0 V  298 mA  24 500 rpm

[ 주의사항 ]
  1) 전원을 켜기 전 노브를 OFF 로. 구동 전압은 6 V 이하. 초과 시 모터가 탄다.
  2) 10 분 이상 연속 구동 금지.
  3) 회전 중인 원판에 손대지 말 것.
  4) 알루미늄 튜브가 홀더에 닿지 않도록 할 것.

[ 이 시뮬레이터에 대하여 ]
  · 회전수(rpm)는 어디에도 표시되지 않는다. 실제 시험장과 같다.
  · 세차 주기·각도·길이는 스톱워치·각도기·자로 직접 재야 한다.
  · 분석·회귀·채점 기능은 의도적으로 넣지 않았다.
  · 마우스 좌 드래그(실험대) / 우 드래그(조립) 로 시점을 돌릴 수 있다.
  · 시간 배속을 쓰면 스톱워치도 같은 시간축으로 흐른다 (결과는 동일).
"""
    TXT_EN = """APhO 2024  Experimental Problem — Gyroscope

[ Equipment provided ]
  · Gyroscope main vertical stand ×1     · Adjustable power adapter ×1 (ZY-009)
  · DC motor + case + coupler ×1         · Goniometer ×1
  · 20 cm spinning disk, 2 / 3 / 4 mm    · Stopwatch ×1
  · 26 cm counterweight disk ×1          · Antistatic mat, aluminium tube, retort stand
  · Bolts & nuts, Allen keys, screwdriver, cable ties, double-sided tape, ruler

[ Mass of components ]
  20 cm × 2 mm  ->  65 ± 1 g       20 cm × 3 mm  ->  89 ± 1 g
  20 cm × 4 mm  -> 131 ± 1 g       26 cm × 4 mm  -> 231 ± 1 g
  DC motor with casing -> 94 g     The mass of the aluminium tube is neglected.

[ Table 1 — DC motor no-load characteristic ]  (reference only, not for replication)
   3.7 V  176 mA   7 200 rpm      7.4 V  230 mA  15 600 rpm
   4.8 V  185 mA   9 700 rpm      9.6 V  245 mA  19 800 rpm
   6.0 V  205 mA  12 600 rpm     12.0 V  298 mA  24 500 rpm

[ Precautions ]
  1) Knob OFF before switching on. Keep the driving voltage below 6 V, or the motor burns.
  2) Do not run continuously for more than 10 minutes.
  3) Never touch the spinning disk.
  4) Keep the aluminium tube clear of the holder.

[ About this simulator ]
  · The rotor speed (rpm) is never displayed, exactly as in the real exam hall.
  · Precession period, angle and length must be measured with the stopwatch,
    goniometer and ruler yourself.
  · Analysis, fitting and marking features are deliberately absent.
  · Drag with the left mouse button (bench) / right button (assembly) to orbit the view.
  · With time acceleration the stopwatch runs on the same clock, so results are unchanged.
"""

    def __init__(self, master, app):
        super().__init__(master)
        t = tk.Text(self, wrap="word", font=("Consolas", 10), bg="#ffffff",
                    relief="flat", padx=18, pady=14)
        t.pack(fill="both", expand=True, padx=8, pady=8)
        t.insert("1.0", self.TXT_KO if LANG == "KO" else self.TXT_EN)
        t.config(state="disabled")


# =========================================================================
if __name__ == "__main__":
    App().mainloop()
