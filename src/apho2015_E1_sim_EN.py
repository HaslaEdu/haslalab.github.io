#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  16th Asian Physics Olympiad  (APhO 2015, Hangzhou - China)
  Experimental Problem :  THE PIEZOELECTRIC EFFECT AND ITS APPLICATIONS
  가상 실험실 시뮬레이터 / Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------

설계 원칙
  * 계기가 실제로 표시하는 것만 보여준다. 물리량은 계산해 주지 않는다.
  * 버니어 캘리퍼스/줄자는 눈금을 그려서 학생이 직접 읽는다.
  * 숨은 참값은 세션마다 무작위화된다.
  * 표준 라이브러리(tkinter 포함)만 사용한다.
"""

import math
import random
import tkinter as tk
from tkinter import ttk

VERSION = "1.0"
LANG = "en"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


# =====================================================================
#  물리 엔진 (순방향 모델)
# =====================================================================

EPS0 = 8.85e-12          # 문제지에 주어진 진공 유전율
RSER = 10.0              # 전류계 션트 + 리드선 저항 (Ω)
DMM_FC = 45.0e3          # DMM 교류 대역폭 (Hz)


def dmm_ac_gain(f):
    """DMM 은 1 kHz 이상에서 정확도가 보장되지 않고 40 kHz 부근에서 응답이 떨어진다."""
    x = f / DMM_FC
    return 1.0 / math.sqrt(1.0 + x ** 4)


class Plate:
    """PZT 판 1장의 숨은 참값."""

    def __init__(self, rng, idx, t_room):
        self.idx = idx
        self.l0 = rng.uniform(44.94, 45.08)     # mm
        self.w0 = rng.uniform(6.96, 7.08)       # mm
        self.t0 = rng.uniform(0.965, 1.035)     # mm
        # 6개 측정 지점에서의 미세한 비균일성 (mm)
        self.dl = [rng.gauss(0.0, 0.011) for _ in range(6)]
        self.dw = [rng.gauss(0.0, 0.017) for _ in range(6)]
        self.dt = [rng.gauss(0.0, 0.011) for _ in range(6)]
        self.rho = rng.uniform(7.06e3, 7.36e3)  # kg/m^3
        vol = self.l0 * self.w0 * self.t0 * 1e-9
        self.mass_g = self.rho * vol * 1e3
        # 상온 비유전율: 판의 정전용량이 실제 시료(약 18 nF)와 같은 범위에
        # 들도록 기하 인자에 맞춰 뽑는다.
        geom = EPS0 * (self.l0 * 1e-3) * (self.w0 * 1e-3) / (self.t0 * 1e-3)
        lo = max(6.15e3, 17.75e-9 / geom)
        hi = min(6.75e3, 18.85e-9 / geom)
        if lo > hi:
            lo = hi = 0.5 * (lo + hi)
        self.eps_room = rng.uniform(lo, hi)
        self.Tc = rng.uniform(166.0, 178.0)     # °C
        self.t_room = t_room
        self.Kcw = self.eps_room * (self.Tc - t_room)   # eps_r = Kcw/(Tc-T)
        self.Y = rng.uniform(5.20e10, 5.85e10)  # Pa
        self.d31 = rng.uniform(4.30e-10, 4.58e-10)      # m/V
        self.Qm = rng.uniform(45.0, 65.0)
        self.tand = rng.uniform(0.006, 0.012)
        self.temp = t_room                      # 현재 판 온도 (°C)
        self.mass_noise = [rng.gauss(0.0, 0.004) for _ in range(6)]
        self.cap_noise = [rng.gauss(0.0, 0.0012) for _ in range(8)]
        self._nc = 0

    # ---- 치수 / 질량 ----
    def dim_true(self, kind, pos):
        pos %= 6
        if kind == "l":
            return self.l0 + self.dl[pos]
        if kind == "w":
            return self.w0 + self.dw[pos]
        return self.t0 + self.dt[pos]

    def mass_reading(self, pos=0):
        return self.mass_g + self.mass_noise[pos % 6]

    # ---- 유전 ----
    def eps_r(self, temp=None):
        tp = self.temp if temp is None else temp
        tp = min(tp, self.Tc - 8.0)
        return self.Kcw / (self.Tc - tp)

    def cap_F(self, temp=None):
        l, w, t = self.l0 * 1e-3, self.w0 * 1e-3, self.t0 * 1e-3
        return EPS0 * self.eps_r(temp) * l * w / t

    def cap_reading_nF(self, rng, temp=None):
        c = self.cap_F(temp) * 1e9
        self._nc += 1
        return c * (1.0 + rng.gauss(0.0, 0.0007)) + rng.gauss(0.0, 0.006)

    # ---- 등가회로 ----
    def circuit(self, temp=None):
        """(C0, C1, L1, R1, fr, fa) 반환.

        k^2 = d31^2 Y / (eps0 epsT),  C1/C0 = (8/pi^2) k^2/(1-k^2)
        fr  = u/(2l),  u = sqrt(Y/rho)
        이 관계는 문제지의 d 공식과 정확히 등가이다.
        """
        eps = self.eps_r(temp)
        l, w, t = self.l0 * 1e-3, self.w0 * 1e-3, self.t0 * 1e-3
        cfree = EPS0 * eps * l * w / t
        k2 = self.d31 ** 2 * self.Y / (EPS0 * eps)
        r = (8.0 / math.pi ** 2) * k2 / (1.0 - k2)
        c0 = cfree / (1.0 + r)
        c1 = cfree - c0
        u = math.sqrt(self.Y / self.rho)
        fr = u / (2.0 * l)
        l1 = 1.0 / (c1 * (2.0 * math.pi * fr) ** 2)
        r1 = 2.0 * math.pi * fr * l1 / self.Qm
        return c0, c1, l1, r1, fr, fr * math.sqrt(1.0 + r)

    def current_A(self, f, vrms, clip="M", temp=None):
        """그림 9 회로의 교류 전류 (A)."""
        if f <= 0:
            return 0.0
        c0, c1, l1, r1, fr, fa = self.circuit(temp)
        damp, dfr = 1.0, 1.0
        if clip == "Q":
            damp, dfr = 9.0, 1.006
        elif clip in ("L", "R"):
            damp, dfr = 26.0, 1.014
        if dfr != 1.0:
            l1 = l1 / dfr ** 2          # 클램핑에 의한 공진 이동
        w = 2.0 * math.pi * f
        zm = complex(r1 * damp, w * l1 - 1.0 / (w * c1))
        adm = complex(w * c0 * self.tand, w * c0) + 1.0 / zm
        z = 1.0 / adm
        return vrms / abs(complex(RSER, 0.0) + z) * dmm_ac_gain(f)


class Rod:
    """알루미늄 막대 (D: 결함 없음 / E: 깊은 절단부 있음).

    공진 주파수는 이상적인 n·u/(2L) 에서 약간 벗어난다 (불완전한 자유 경계
    조건, 변환기의 질량 부하, 막대의 미세한 불균일성).
    """

    JIT = 60.0        # 봉우리 위치의 무작위 편차 (Hz)

    def __init__(self, rng, flawed=False, ref=None):
        self.L = rng.uniform(0.4988, 0.5012)         # m
        if ref is None:
            self.uL = rng.uniform(4960.0, 5110.0)    # 종파 m/s
            self.uT = rng.uniform(2880.0, 3020.0)    # 횡파 m/s
        else:                                        # 같은 알루미늄 재질
            self.uL = ref.uL * rng.uniform(0.997, 1.003)
            self.uT = ref.uT * rng.uniform(0.997, 1.003)
        self.flaw = rng.uniform(0.286, 0.318) if flawed else None
        self.tape_noise = [rng.gauss(0.0, 0.035) for _ in range(8)]   # cm
        self.fT = self._series(rng, self.uT / (2 * self.L), 16)
        self.fL = self._series(rng, self.uL / (2 * self.L), 9)
        self.fF = self._series(rng, self.uL / (2 * self.flaw), 6) if flawed else []

    def _series(self, rng, f0, nmax):
        out = []
        for n in range(1, nmax + 1):
            f = n * f0 + rng.gauss(0.0, self.JIT)
            if 1500.0 < f < 42000.0:
                out.append((f, rng.uniform(320.0, 720.0)))
        return out

    def tape_reading_cm(self, i):
        return self.L * 100.0 + self.tape_noise[i % 8]


def _env(f):
    """PZT 변환기/센서의 광대역 응답 포락선 (32 kHz 부근에서 최대)."""
    f0, q = 32500.0, 1.15
    x = f / f0
    return 1.0 / math.sqrt((1.0 - x * x) ** 2 + (x / q) ** 2)


def _add(rng, table, base, out):
    for f, q in table:
        out.append((f, base * _env(f) * rng.uniform(0.55, 1.55), q))


def build_modes(rng, rod, setup):
    """setup: 'D1'(횡파 배치) / 'D2'(종파 배치) / 'E'(결함 막대)"""
    m = []
    if setup == "D1":
        _add(rng, rod.fT, 620.0, m)
        _add(rng, rod.fL, 26.0, m)
    elif setup == "D2":
        _add(rng, rod.fL, 900.0, m)
        _add(rng, rod.fT, 300.0, m)
    else:
        _add(rng, rod.fF, 900.0, m)
        _add(rng, rod.fL, 380.0, m)
        _add(rng, rod.fT, 150.0, m)
    # 설비 불완전성에 의한 무관한 봉우리
    added, guard = 0, 0
    while added < 3 and guard < 400:
        guard += 1
        f = rng.uniform(4500.0, 41500.0)
        if all(abs(f - x[0]) > 380.0 for x in m):
            m.append((f, 55.0 * _env(f) * rng.uniform(0.6, 1.4),
                      rng.uniform(400.0, 900.0)))
            added += 1
    m.sort(key=lambda x: x[0])
    return m


class Session:
    """한 세션의 모든 숨은 참값."""

    def __init__(self, seed=None):
        self.seed = seed if seed is not None else random.randrange(1, 10 ** 9)
        rng = random.Random(self.seed)
        self.rng = random.Random(self.seed ^ 0x5EED)
        self.t_room = rng.uniform(20.5, 24.0)
        self.plates = [Plate(rng, i, self.t_room) for i in range(5)]
        self.rod = Rod(rng, False)
        self.rod_flaw = Rod(rng, True, ref=self.rod)
        self.modes = {
            "D1": build_modes(rng, self.rod, "D1"),
            "D2": build_modes(rng, self.rod, "D2"),
            "E": build_modes(rng, self.rod_flaw, "E"),
        }

    def sensor_uA(self, f, setup, vrms=3.0, contact=1.0, noise=True):
        """센서 PZT 판이 검출하는 전류 (µA)."""
        if f <= 0:
            return 0.0
        z = 0j
        for fn, a, q in self.modes[setup]:
            z += a / complex(1.0, 2.0 * q * (f - fn) / fn)
        val = abs(z) * (vrms / 3.0) * contact
        val += 0.9 + 6.0e-5 * f * (vrms / 3.0)
        val *= dmm_ac_gain(f)
        if noise:
            val *= 1.0 + self.rng.gauss(0.0, 0.006)
            val += self.rng.gauss(0.0, 0.25)
        return max(val, 0.0)


# =====================================================================
#  공용 그리기 도구
# =====================================================================

FONT = {}


def init_fonts(root):
    import tkinter.font as tkfont
    fams = set(tkfont.families(root))
    base = None
    for cand in ("맑은 고딕", "Malgun Gothic", "NanumGothic", "Noto Sans CJK KR",
                 "AppleGothic", "DejaVu Sans"):
        if cand in fams:
            base = cand
            break
    base = base or "TkDefaultFont"
    mono = None
    for cand in ("Consolas", "DejaVu Sans Mono", "Courier New"):
        if cand in fams:
            mono = cand
            break
    mono = mono or "TkFixedFont"
    FONT.update({
        "s": (base, 8), "n": (base, 9), "b": (base, 9, "bold"),
        "m": (base, 11), "mb": (base, 11, "bold"), "l": (base, 14, "bold"),
        "lcd": (mono, 20, "bold"), "lcd2": (mono, 14, "bold"),
        "lcd3": (mono, 11), "tiny": (base, 7),
    })


def rrect(c, x1, y1, x2, y2, r=6, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


# --- 개별 장비 2D 그래픽 (문제지 사진/그림을 참조하여 재구성) ---

def d_pzt(c, x, y, s=1.0, t=(), idx=None):
    L, W, D = 92 * s, 15 * s, 9 * s
    c.create_polygon(x - L / 2, y, x - L / 2 + D, y - D, x + L / 2 + D, y - D,
                     x + L / 2, y, fill="#b9bcc0", outline="#6f7378", tags=t)
    c.create_rectangle(x - L / 2, y, x + L / 2, y + W, fill="#9aa0a6",
                       outline="#5f6368", tags=t)
    c.create_rectangle(x - L / 2, y + W - 4 * s, x + L / 2, y + W,
                       fill="#e8d84a", outline="#b9a92c", tags=t)
    c.create_polygon(x + L / 2, y, x + L / 2 + D, y - D, x + L / 2 + D,
                     y - D + W, x + L / 2, y + W, fill="#e8d84a",
                     outline="#b9a92c", tags=t)
    if idx:
        c.create_text(x, y + W / 2 + 1, text=str(idx), font=FONT["b"],
                      fill="#22262a", tags=t)


def d_dmm(c, x, y, s=1.0, t=()):
    w, h = 96 * s, 150 * s
    rrect(c, x - w / 2, y - h / 2, x + w / 2, y + h / 2, 10 * s,
          fill="#f2c21a", outline="#7a6300", tags=t)
    rrect(c, x - w / 2 + 6 * s, y - h / 2 + 5 * s, x + w / 2 - 6 * s,
          y + h / 2 - 6 * s, 7 * s, fill="#3f4448", outline="#23272a", tags=t)
    c.create_rectangle(x - w / 2 + 12 * s, y - h / 2 + 12 * s, x + w / 2 - 12 * s,
                       y - h / 2 + 48 * s, fill="#c9d6c0", outline="#5b6b56", tags=t)
    c.create_oval(x - 26 * s, y - 18 * s, x + 26 * s, y + 34 * s,
                  fill="#5a6066", outline="#2a2e31", tags=t)
    c.create_oval(x - 8 * s, y - 0 * s, x + 8 * s, y + 16 * s, fill="#2a2e31", tags=t)
    for dx, col in ((-26, "#d02020"), (0, "#111111"), (26, "#d02020")):
        c.create_oval(x + dx * s - 6 * s, y + h / 2 - 22 * s, x + dx * s + 6 * s,
                      y + h / 2 - 10 * s, fill=col, outline="#000000", tags=t)


def d_siggen(c, x, y, s=1.0, t=()):
    w, h = 150 * s, 78 * s
    rrect(c, x - w / 2, y - h / 2, x + w / 2, y + h / 2, 6 * s,
          fill="#e9edf1", outline="#8b9198", tags=t)
    c.create_rectangle(x - w / 2 + 26 * s, y - h / 2 + 10 * s, x - w / 2 + 86 * s,
                       y - h / 2 + 38 * s, fill="#2f6fb0", outline="#1b4470", tags=t)
    for i, dx in enumerate((96, 116, 136)):
        c.create_oval(x - w / 2 + dx * s - 8 * s, y - h / 2 + 12 * s,
                      x - w / 2 + dx * s + 8 * s, y - h / 2 + 28 * s,
                      fill="#cfd4d9" if i < 2 else "#4a8fd6", outline="#6b7176", tags=t)
    c.create_rectangle(x - w / 2 + 8 * s, y - 8 * s, x - w / 2 + 18 * s,
                       y + 8 * s, fill="#d03a2a", outline="#7a1f14", tags=t)
    for dx in (96, 116, 136):
        c.create_oval(x - w / 2 + dx * s - 6 * s, y + 6 * s,
                      x - w / 2 + dx * s + 6 * s, y + 18 * s,
                      fill="#c9a227", outline="#6f5a12", tags=t)
    c.create_rectangle(x - w / 2 + 24 * s, y + 8 * s, x + w / 2 - 24 * s,
                       y + h / 2, fill="#dfe4e9", outline="#9aa0a6", tags=t)


def d_scale(c, x, y, s=1.0, t=()):
    w, h = 92 * s, 62 * s
    rrect(c, x - w / 2, y - h / 2, x + w / 2, y + h / 2, 6 * s,
          fill="#d7dbe0", outline="#8b9198", tags=t)
    c.create_rectangle(x - w / 2 + 6 * s, y - h / 2 + 5 * s, x + w / 2 - 6 * s,
                       y + 2 * s, fill="#b98b7a", outline="#7a5a4d", tags=t)
    c.create_rectangle(x - w / 2 + 10 * s, y + 6 * s, x + w / 2 - 10 * s,
                       y + h / 2 - 12 * s, fill="#7f8a7c", outline="#4d5549", tags=t)
    for i in range(4):
        c.create_oval(x - w / 2 + (10 + i * 20) * s, y + h / 2 - 10 * s,
                      x - w / 2 + (22 + i * 20) * s, y + h / 2 - 2 * s,
                      fill="#eceff2", outline="#8b9198", tags=t)


def d_caliper(c, x, y, s=1.0, t=()):
    w = 150 * s
    c.create_rectangle(x - w / 2, y - 5 * s, x + w / 2, y + 5 * s,
                       fill="#c8ccd0", outline="#6f7378", tags=t)
    c.create_polygon(x - w / 2, y - 5 * s, x - w / 2, y - 26 * s,
                     x - w / 2 + 9 * s, y - 5 * s, fill="#c8ccd0",
                     outline="#6f7378", tags=t)
    c.create_polygon(x - w / 2, y + 5 * s, x - w / 2, y + 22 * s,
                     x - w / 2 + 9 * s, y + 5 * s, fill="#c8ccd0",
                     outline="#6f7378", tags=t)
    xv = x - w / 2 + 52 * s
    c.create_rectangle(xv, y - 24 * s, xv + 34 * s, y + 20 * s,
                       fill="#dfe3e7", outline="#6f7378", tags=t)
    c.create_polygon(xv, y - 5 * s, xv, y - 26 * s, xv - 9 * s, y - 5 * s,
                     fill="#c8ccd0", outline="#6f7378", tags=t)
    c.create_polygon(xv, y + 5 * s, xv, y + 22 * s, xv - 9 * s, y + 5 * s,
                     fill="#c8ccd0", outline="#6f7378", tags=t)
    for i in range(14):
        c.create_line(x - w / 2 + (90 + i * 4) * s, y - 5 * s,
                      x - w / 2 + (90 + i * 4) * s, y - 1 * s, fill="#5f6368", tags=t)


def d_kelvin(c, x, y, s=1.0, t=()):
    c.create_polygon(x - 30 * s, y - 10 * s, x + 6 * s, y - 4 * s, x + 6 * s,
                     y + 2 * s, x - 30 * s, y - 2 * s, fill="#b0b5ba",
                     outline="#5f6368", tags=t)
    c.create_polygon(x - 30 * s, y + 10 * s, x + 6 * s, y + 4 * s, x + 6 * s,
                     y - 2 * s, x - 30 * s, y + 2 * s, fill="#8e939a",
                     outline="#5f6368", tags=t)
    rrect(c, x + 4 * s, y - 12 * s, x + 26 * s, y + 12 * s, 4 * s,
          fill="#d8443a", outline="#7a1f14", tags=t)
    c.create_line(x + 26 * s, y - 6 * s, x + 46 * s, y - 12 * s, fill="#cc2b1f",
                  width=2, tags=t)
    c.create_line(x + 26 * s, y + 6 * s, x + 46 * s, y + 12 * s, fill="#1a1a1a",
                  width=2, tags=t)


def d_cable(c, x, y, s=1.0, t=(), col="#cc2b1f"):
    c.create_line(x - 40 * s, y - 8 * s, x - 10 * s, y - 2 * s, x + 14 * s,
                  y - 10 * s, smooth=True, fill=col, width=3, tags=t)
    c.create_line(x - 40 * s, y + 10 * s, x - 6 * s, y + 4 * s, x + 14 * s,
                  y + 12 * s, smooth=True, fill="#1a1a1a", width=3, tags=t)
    for dy, cc in ((-10, col), (12, "#1a1a1a")):
        c.create_polygon(x + 14 * s, y + dy * s - 4 * s, x + 30 * s, y + dy * s - 2 * s,
                         x + 30 * s, y + dy * s + 4 * s, x + 14 * s, y + dy * s + 5 * s,
                         fill=cc, outline="#333333", tags=t)
    for dy in (-8, 8):
        c.create_rectangle(x - 46 * s, y + dy * s - 3 * s, x - 38 * s,
                           y + dy * s + 3 * s, fill="#c9a227", outline="#6f5a12", tags=t)


def d_bath(c, x, y, s=1.0, t=()):
    w, h = 110 * s, 84 * s
    rrect(c, x - w / 2, y - h / 2, x + w / 2, y + h / 2, 8 * s,
          fill="#eceff2", outline="#8b9198", tags=t)
    c.create_oval(x - 40 * s, y - h / 2 - 6 * s, x + 40 * s, y - h / 2 + 24 * s,
                  fill="#9aa0a6", outline="#5f6368", tags=t)
    c.create_oval(x - 32 * s, y - h / 2 - 1 * s, x + 32 * s, y - h / 2 + 19 * s,
                  fill="#5b6b7a", outline="#3c4855", tags=t)
    c.create_rectangle(x - 26 * s, y - 6 * s, x + 26 * s, y + 12 * s,
                       fill="#2a2020", outline="#111111", tags=t)
    c.create_text(x, y + 3 * s, text="88.8", fill="#ff3b30", font=FONT["lcd3"], tags=t)
    for dx in (-20, 0, 20):
        c.create_oval(x + dx * s - 7 * s, y + 20 * s, x + dx * s + 7 * s,
                      y + 34 * s, fill="#d8443a" if dx < 0 else "#3f7fd8",
                      outline="#555555", tags=t)


def d_rod(c, x, y, s=1.0, t=()):
    c.create_rectangle(x - 90 * s, y - 9 * s, x + 90 * s, y + 9 * s,
                       fill="#c2c6ca", outline="#787d82", tags=t)
    c.create_rectangle(x - 90 * s, y - 9 * s, x + 90 * s, y - 4 * s,
                       fill="#dde1e5", outline="", tags=t)


def d_clearbox(c, x, y, s=1.0, t=()):
    rrect(c, x - 96 * s, y - 26 * s, x + 96 * s, y + 26 * s, 5 * s,
          fill="#e6f0f4", outline="#7f9aa6", tags=t)
    c.create_rectangle(x - 88 * s, y - 10 * s, x + 88 * s, y + 10 * s,
                       fill="#d5e4ea", outline="#96b0bb", tags=t)


def d_blackbox(c, x, y, s=1.0, t=()):
    rrect(c, x - 96 * s, y - 26 * s, x + 96 * s, y + 26 * s, 5 * s,
          fill="#2f3236", outline="#15171a", tags=t)
    c.create_rectangle(x - 88 * s, y - 10 * s, x + 88 * s, y + 10 * s,
                       fill="#3b3f44", outline="#1d1f22", tags=t)


def d_eraser(c, x, y, s=1.0, t=()):
    rrect(c, x - 26 * s, y - 16 * s, x + 26 * s, y + 16 * s, 5 * s,
          fill="#e8a33d", outline="#9c6a17", tags=t)
    c.create_line(x - 26 * s, y - 6 * s, x + 26 * s, y - 6 * s, fill="#c98a2c", tags=t)


def d_spring(c, x, y, s=1.0, t=()):
    pts = []
    for i in range(19):
        pts += [x - 34 * s + i * 3.8 * s, y + (10 * s if i % 2 else -10 * s)]
    c.create_line(pts, fill="#9aa0a6", width=3, tags=t)


def d_bag(c, x, y, s=1.0, t=()):
    c.create_polygon(x - 26 * s, y - 24 * s, x + 26 * s, y - 24 * s, x + 22 * s,
                     y + 26 * s, x - 22 * s, y + 26 * s, fill="#dfeef5",
                     outline="#8fb6c6", tags=t)
    c.create_line(x - 26 * s, y - 20 * s, x + 26 * s, y - 20 * s,
                  fill="#8fb6c6", tags=t)


def d_pebble(c, x, y, s=1.0, t=()):
    c.create_oval(x - 18 * s, y - 12 * s, x + 18 * s, y + 12 * s,
                  fill="#a89f92", outline="#6d665c", tags=t)


def d_tongs(c, x, y, s=1.0, t=()):
    c.create_line(x - 26 * s, y - 12 * s, x + 6 * s, y - 3 * s, x + 26 * s,
                  y - 8 * s, smooth=True, fill="#dfe3e7", width=4, tags=t)
    c.create_line(x - 26 * s, y + 12 * s, x + 6 * s, y + 3 * s, x + 26 * s,
                  y + 8 * s, smooth=True, fill="#c8ccd0", width=4, tags=t)


def d_tape(c, x, y, s=1.0, t=()):
    rrect(c, x - 24 * s, y - 20 * s, x + 24 * s, y + 20 * s, 8 * s,
          fill="#e8c93d", outline="#9c8617", tags=t)
    c.create_oval(x - 12 * s, y - 10 * s, x + 12 * s, y + 12 * s,
                  fill="#3f4448", outline="#22262a", tags=t)
    c.create_rectangle(x + 20 * s, y + 4 * s, x + 44 * s, y + 12 * s,
                       fill="#f0f2f4", outline="#8b9198", tags=t)


def d_bottle(c, x, y, s=1.0, t=()):
    c.create_rectangle(x - 14 * s, y - 20 * s, x + 14 * s, y + 30 * s,
                       fill="#dfeef5", outline="#8fb6c6", tags=t)
    c.create_rectangle(x - 6 * s, y - 32 * s, x + 6 * s, y - 20 * s,
                       fill="#dfeef5", outline="#8fb6c6", tags=t)
    c.create_rectangle(x - 8 * s, y - 38 * s, x + 8 * s, y - 30 * s,
                       fill="#d8443a", outline="#7a1f14", tags=t)


def d_towel(c, x, y, s=1.0, t=()):
    rrect(c, x - 26 * s, y - 18 * s, x + 26 * s, y + 18 * s, 4 * s,
          fill="#e6dcc8", outline="#a8977a", tags=t)


def d_earplug(c, x, y, s=1.0, t=()):
    c.create_oval(x - 20 * s, y - 8 * s, x - 2 * s, y + 8 * s, fill="#f0e04a",
                  outline="#a89a17", tags=t)
    c.create_oval(x + 2 * s, y - 8 * s, x + 20 * s, y + 8 * s, fill="#f0e04a",
                  outline="#a89a17", tags=t)


ITEMS = {
    "siggen":  (T("신호발생기", "Signal generator"), d_siggen, 0.62),
    "dmm":     (T("디지털 멀티미터", "DMM"), d_dmm, 0.42),
    "caliper": (T("버니어 캘리퍼스", "Vernier caliper"), d_caliper, 0.52),
    "scale":   (T("전자 저울", "Electronic scale"), d_scale, 0.62),
    "kelvin":  (T("캘빈 클립", "Kelvin clip"), d_kelvin, 0.8),
    "cable1":  (T("악어클립 케이블 1", "Croc. cable 1"), d_cable, 0.8),
    "cable2":  (T("악어클립 케이블 2", "Croc. cable 2"), d_cable, 0.8),
    "bath":    (T("항온수조", "Water bath"), d_bath, 0.5),
    "bag":     (T("비닐봉지", "Plastic bag"), d_bag, 0.7),
    "towel":   (T("종이 타월", "Paper towel"), d_towel, 0.7),
    "tongs":   (T("플라스틱 집게", "Plastic tongs"), d_tongs, 0.8),
    "pebble":  (T("조약돌", "Pebble"), d_pebble, 0.9),
    "rod":     (T("알루미늄 막대", "Aluminium rod"), d_rod, 0.5),
    "tape":    (T("강철 줄자", "Steel tape"), d_tape, 0.7),
    "spring":  (T("스프링", "Spring"), d_spring, 0.8),
    "eraser":  (T("지우개", "Rubber eraser"), d_eraser, 0.8),
    "clearbox": (T("투명 플라스틱 상자", "Clear box"), d_clearbox, 0.45),
    "blackbox": (T("검은색 플라스틱 상자", "Black box"), d_blackbox, 0.45),
    "earplug": (T("귀마개", "Earplugs"), d_earplug, 0.9),
    "bottle":  (T("1.5 L 생수", "1.5 L water"), d_bottle, 0.6),
}
for _i in range(1, 6):
    ITEMS["pzt%d" % _i] = (T("PZT 판 #%d" % _i, "PZT plate #%d" % _i),
                           (lambda n: (lambda c, x, y, s=1.0, t=():
                                       d_pzt(c, x, y, s, t, n)))(_i), 0.62)


# =====================================================================
#  조립(Assembly) 탭
# =====================================================================

SETUP_NAMES = [
    ("A",  T("실험 A — 기본 측정", "Experiment A — Basic measurements")),
    ("B",  T("실험 B — 공진법 (압전 계수)", "Experiment B — Resonant method")),
    ("C",  T("실험 C — 큐리 온도", "Experiment C — Curie temperature")),
    ("D1", T("실험 D — 횡파 배치 (그림 11)", "Experiment D — transverse setup")),
    ("D2", T("실험 D — 종파 배치 (그림 13)", "Experiment D — longitudinal setup")),
    ("E",  T("실험 E — 결함 막대 (그림 14)", "Experiment E — flaw location")),
]

PZT_ANY = ["pzt1", "pzt2", "pzt3", "pzt4", "pzt5"]
CAB_ANY = ["cable1", "cable2"]

# (key, col, row, accepts, need, caption)
SLOTS = {
    "A": [
        ("caliper", 0, 0, ["caliper"], [], T("버니어 캘리퍼스", "Vernier caliper")),
        ("scale", 0, 1, ["scale"], [], T("전자 저울", "Electronic scale")),
        ("plate", 0, 2, PZT_ANY, [], T("측정할 PZT 판 (A·B·C 동일 판)",
                                       "PZT plate under test (same for A,B,C)")),
        ("dmm", 1, 0, ["dmm"], [], T("디지털 멀티미터", "Digital multimeter")),
        ("kelvin", 1, 1, ["kelvin"], ["dmm"], T("캘빈 클립 → DMM 단자",
                                                "Kelvin clip → DMM terminals")),
    ],
    "B": [
        ("siggen", 0, 0, ["siggen"], [], T("신호발생기", "Signal generator")),
        ("dmm", 0, 1, ["dmm"], [], T("디지털 멀티미터", "Digital multimeter")),
        ("plate", 0, 2, PZT_ANY, [], T("PZT 판", "PZT plate")),
        ("clipL", 1, 0, ["kelvin"], ["plate"], T("클립: 판의 왼쪽 끝",
                                                 "Clip at left end")),
        ("clipM", 1, 1, ["kelvin"], ["plate"], T("클립: 판의 중간점",
                                                 "Clip at midpoint")),
        ("clipR", 1, 2, ["kelvin"], ["plate"], T("클립: 판의 오른쪽 끝",
                                                 "Clip at right end")),
        ("cabg", 2, 0, CAB_ANY, ["siggen", "clip*"],
         T("케이블: 신호발생기 → 클립", "Cable: generator → clip")),
        ("cabd", 2, 1, CAB_ANY, ["dmm", "clip*"],
         T("케이블: 클립 → DMM", "Cable: clip → DMM")),
    ],
    "C": [
        ("bath", 0, 0, ["bath"], [], T("항온수조", "Thermostat water bath")),
        ("water", 0, 1, ["bottle"], ["bath"], T("수조에 생수 붓기 (약 절반)",
                                                "Fill bath with water")),
        ("submerge", 0, 2, ["pebble"], ["water", "tongs"],
         T("봉지를 물에 담그고 조약돌로 가라앉히기", "Submerge bag with pebble")),
        ("bag", 1, 0, ["bag"], [], T("비닐봉지", "Plastic bag")),
        ("pbag", 1, 1, PZT_ANY, ["bag"], T("PZT 판을 봉지 안에", "PZT plate into bag")),
        ("cabc", 1, 2, CAB_ANY, ["pbag", "dmm"],
         T("악어클립 케이블: 판 ↔ DMM", "Croc. cable: plate ↔ DMM")),
        ("tongs", 1, 3, ["tongs"], ["cabc"], T("집게로 케이블과 봉지를 함께 집기",
                                               "Clamp cable and bag with tongs")),
        ("dmm", 2, 0, ["dmm"], [], T("디지털 멀티미터", "Digital multimeter")),
    ],
    "D1": [
        ("box", 0, 0, ["clearbox"], [], T("투명 플라스틱 상자", "Clear plastic box")),
        ("rod", 0, 1, ["rod"], ["box"], T("알루미늄 막대를 긴 홈에", "Rod into the groove")),
        ("spring", 0, 2, ["spring"], ["rod"], T("반대쪽 끝에 스프링", "Spring at far end")),
        ("eraser", 0, 3, ["eraser"], ["pztt", "pzts"],
         T("지우개로 두 판을 눌러 붙이기", "Press plates with eraser")),
        ("pztt", 1, 0, PZT_ANY, ["rod"], T("변환기 판 — 막대 끝의 옆면",
                                           "Transducer — side face at rod end")),
        ("pzts", 1, 1, PZT_ANY, ["rod"], T("센서 판 — 막대 끝의 옆면",
                                           "Sensor — side face at rod end")),
        ("cabg", 1, 2, CAB_ANY, ["pztt", "siggen"], T("케이블: 신호발생기 → 변환기",
                                                      "Cable: generator → transducer")),
        ("cabd", 1, 3, CAB_ANY, ["pzts", "dmm"], T("케이블: 센서 → DMM",
                                                   "Cable: sensor → DMM")),
        ("siggen", 2, 0, ["siggen"], [], T("신호발생기", "Signal generator")),
        ("dmm", 2, 1, ["dmm"], [], T("디지털 멀티미터", "Digital multimeter")),
    ],
    "D2": [
        ("box", 0, 0, ["clearbox"], [], T("투명 플라스틱 상자", "Clear plastic box")),
        ("rod", 0, 1, ["rod"], ["box"], T("알루미늄 막대를 긴 홈에", "Rod into the groove")),
        ("spring", 0, 2, ["spring"], ["rod"], T("반대쪽 끝에 스프링", "Spring at far end")),
        ("eraser", 0, 3, ["eraser"], ["pztt", "pzts"],
         T("지우개를 완충재로 두 판을 밀착", "Eraser as cushion behind plates")),
        ("pztt", 1, 0, PZT_ANY, ["box"], T("변환기 판 — 상자 끝의 가는 슬롯",
                                           "Transducer — thin slot at box end")),
        ("pzts", 1, 1, PZT_ANY, ["box"], T("센서 판 — 상자 끝의 가는 슬롯",
                                           "Sensor — thin slot at box end")),
        ("cabg", 1, 2, CAB_ANY, ["pztt", "siggen"], T("케이블: 신호발생기 → 변환기",
                                                      "Cable: generator → transducer")),
        ("cabd", 1, 3, CAB_ANY, ["pzts", "dmm"], T("케이블: 센서 → DMM",
                                                   "Cable: sensor → DMM")),
        ("siggen", 2, 0, ["siggen"], [], T("신호발생기", "Signal generator")),
        ("dmm", 2, 1, ["dmm"], [], T("디지털 멀티미터", "Digital multimeter")),
    ],
    "E": [
        ("box", 0, 0, ["blackbox"], [], T("검은색 상자 (막대 내장)",
                                          "Black box (rod inside)")),
        ("eraser", 0, 1, ["eraser"], ["pztt", "pzts"],
         T("지우개를 완충재로 두 판을 밀착", "Eraser as cushion behind plates")),
        ("pztt", 1, 0, PZT_ANY, ["box"], T("변환기 판 — 막대 끝면",
                                           "Transducer — rod end face")),
        ("pzts", 1, 1, PZT_ANY, ["box"], T("센서 판 — 막대 끝면", "Sensor — rod end face")),
        ("cabg", 1, 2, CAB_ANY, ["pztt", "siggen"], T("케이블: 신호발생기 → 변환기",
                                                      "Cable: generator → transducer")),
        ("cabd", 1, 3, CAB_ANY, ["pzts", "dmm"], T("케이블: 센서 → DMM",
                                                   "Cable: sensor → DMM")),
        ("siggen", 2, 0, ["siggen"], [], T("신호발생기", "Signal generator")),
        ("dmm", 2, 1, ["dmm"], [], T("디지털 멀티미터", "Digital multimeter")),
    ],
}

TRAY_ORDER = ["siggen", "dmm", "pzt1", "pzt2", "pzt3", "pzt4", "pzt5", "caliper",
              "scale", "kelvin", "cable1", "cable2", "bath", "bag", "towel",
              "tongs", "pebble", "rod", "tape", "spring", "eraser", "clearbox",
              "blackbox", "earplug", "bottle"]

COLX = [268, 574, 880]
COLW = 292
ROWY = [58, 168, 278, 388]
ROWH = 100


class AssemblyTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.canvas = tk.Canvas(self, width=1180, height=720, bg="#20242a",
                                highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.drag = None
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.on_right)
        self.msg = ""
        self.redraw()

    # -------- 상태 --------
    @property
    def placed(self):
        return self.app.placed[self.app.setup]

    def slots(self):
        return SLOTS[self.app.setup]

    def item_used(self, item):
        return item in self.placed.values()

    def need_ok(self, need):
        for n in need:
            if n.endswith("*"):
                if not any(k.startswith(n[:-1]) for k in self.placed):
                    return False
            elif n not in self.placed:
                return False
        return True

    # -------- 그리기 --------
    def redraw(self):
        c = self.canvas
        c.delete("all")
        c.create_text(16, 16, anchor="nw", font=FONT["l"], fill="#e9edf1",
                      text=T("장비 배치 및 조립", "Apparatus assembly"))
        c.create_text(16, 38, anchor="nw", font=FONT["n"], fill="#9aa4ad",
                      text=T("왼쪽 목록에서 장비를 끌어다 놓으십시오. 오른쪽 클릭으로 제거합니다.",
                             "Drag equipment from the tray. Right-click to remove."))
        # 트레이
        c.create_rectangle(10, 56, 250, 700, fill="#171a1e", outline="#333a41")
        for i, it in enumerate(TRAY_ORDER):
            x, y = 20 + (i % 2) * 115, 64 + (i // 2) * 50
            used = self.item_used(it)
            c.create_rectangle(x, y, x + 108, y + 44,
                               fill="#2b3037" if not used else "#23262a",
                               outline="#3d444c",
                               tags=("tray", "tray:" + it))
            name, drawer, sc = ITEMS[it]
            try:
                drawer(c, x + 54, y + 16, sc * 0.42, ("tray", "tray:" + it))
            except Exception:
                pass
            c.create_text(x + 54, y + 36, text=name, font=FONT["tiny"],
                          fill="#9aa4ad" if not used else "#565c63",
                          tags=("tray", "tray:" + it))
        # 슬롯
        for key, col, row, acc, need, cap in self.slots():
            x, y = COLX[col], ROWY[row]
            filled = key in self.placed
            ready = self.need_ok(need)
            fill = "#243027" if filled else ("#262b31" if ready else "#1d2024")
            out = "#4f8f5a" if filled else ("#4a525b" if ready else "#31363c")
            c.create_rectangle(x, y, x + COLW, y + ROWH, fill=fill, outline=out,
                               dash=() if filled else (4, 3),
                               tags=("slot", "slot:" + key))
            c.create_text(x + 8, y + 8, anchor="nw", text=cap, font=FONT["n"],
                          fill="#dfe4e9" if (ready or filled) else "#5b6168",
                          width=COLW - 16, tags=("slot", "slot:" + key))
            if filled:
                it = self.placed[key]
                name, drawer, sc = ITEMS[it]
                try:
                    drawer(c, x + COLW - 60, y + ROWH - 34, sc * 0.55,
                           ("slot", "slot:" + key))
                except Exception:
                    pass
                c.create_text(x + 8, y + ROWH - 14, anchor="w", text="✔ " + name,
                              font=FONT["s"], fill="#8fd39a",
                              tags=("slot", "slot:" + key))
            elif not ready:
                c.create_text(x + 8, y + ROWH - 14, anchor="w",
                              text=T("선행 조립 필요", "prerequisite missing"),
                              font=FONT["s"], fill="#7a5a3a",
                              tags=("slot", "slot:" + key))
        # 미리보기
        c.create_rectangle(268, 500, 1172, 700, fill="#171a1e", outline="#333a41")
        c.create_text(276, 506, anchor="nw", font=FONT["s"], fill="#7d868e",
                      text=T("조립 상태", "assembled state"))
        self.preview(c, 268, 500, 904, 200)
        if self.msg:
            c.create_text(268, 712, anchor="w", text=self.msg, font=FONT["n"],
                          fill="#e8b04a")

    # -------- 조립 상태 미리보기 --------
    def preview(self, c, x0, y0, w, h):
        s = self.app.setup
        cx, cy = x0 + w / 2, y0 + h / 2 + 10
        P = self.placed
        if s == "A":
            if "caliper" in P:
                d_caliper(c, x0 + 150, cy, 0.9)
            if "scale" in P:
                d_scale(c, x0 + 360, cy, 0.9)
            if "dmm" in P:
                d_dmm(c, x0 + 560, cy, 0.55)
            if "kelvin" in P:
                d_kelvin(c, x0 + 700, cy, 1.0)
            if "plate" in P:
                d_pzt(c, x0 + 810, cy, 0.9, idx=int(P["plate"][-1]))
        elif s == "B":
            if "siggen" in P:
                d_siggen(c, x0 + 110, cy, 0.85)
            if "dmm" in P:
                d_dmm(c, x0 + 780, cy, 0.62)
            if "plate" in P:
                d_pzt(c, cx, cy + 6, 1.5, idx=int(P["plate"][-1]))
            for k, dx in (("clipL", -120), ("clipM", 0), ("clipR", 120)):
                if k in P:
                    d_kelvin(c, cx + dx - 30, cy - 26, 0.9)
            if "cabg" in P:
                c.create_line(x0 + 190, cy + 10, cx - 60, cy - 30, fill="#cc2b1f",
                              width=3, smooth=True)
            if "cabd" in P:
                c.create_line(cx + 60, cy - 30, x0 + 730, cy, fill="#cc2b1f",
                              width=3, smooth=True)
        elif s == "C":
            if "bath" in P:
                d_bath(c, x0 + 130, cy, 1.0)
            if "water" in P:
                c.create_oval(x0 + 90, cy - 48, x0 + 170, cy - 28, fill="#4a86b8",
                              outline="#2c5c86")
            if "dmm" in P:
                d_dmm(c, x0 + 800, cy, 0.62)
            if "bag" in P:
                bx = x0 + 130 if "submerge" in P else x0 + 430
                by = cy - 30 if "submerge" in P else cy
                d_bag(c, bx, by, 0.8)
                if "pbag" in P:
                    d_pzt(c, bx, by, 0.5, idx=int(P["pbag"][-1]))
                if "submerge" in P:
                    d_pebble(c, bx + 6, by + 16, 0.6)
                if "tongs" in P:
                    d_tongs(c, bx, by - 26, 0.6)
                if "cabc" in P:
                    c.create_line(bx + 10, by - 20, x0 + 640, cy - 10,
                                  x0 + 760, cy, fill="#cc2b1f", width=3, smooth=True)
        else:
            boxy = cy
            if "box" in P:
                (d_blackbox if s == "E" else d_clearbox)(c, cx - 60, boxy, 1.6)
            if "rod" in P or s == "E":
                if "rod" in P or ("box" in P and s == "E"):
                    d_rod(c, cx - 70, boxy, 1.5)
            if "spring" in P:
                d_spring(c, cx - 210, boxy, 0.7)
            side = (s == "D1")
            for k, dy in (("pztt", -22), ("pzts", 22)):
                if k in P:
                    if side:
                        d_pzt(c, cx + 100, boxy + dy - 10, 0.55,
                              idx=int(P[k][-1]))
                    else:
                        d_pzt(c, cx + 120, boxy + dy - 4, 0.55, idx=int(P[k][-1]))
            if "eraser" in P:
                d_eraser(c, cx + 190, boxy, 1.0)
            if "siggen" in P:
                d_siggen(c, x0 + 810, y0 + 55, 0.55)
            if "dmm" in P:
                d_dmm(c, x0 + 830, y0 + 145, 0.42)
            if "cabg" in P:
                c.create_line(cx + 150, boxy - 30, x0 + 770, y0 + 62,
                              fill="#cc2b1f", width=2, smooth=True)
            if "cabd" in P:
                c.create_line(cx + 150, boxy + 24, x0 + 800, y0 + 140,
                              fill="#cc2b1f", width=2, smooth=True)

    # -------- 드래그 --------
    def _tag_of(self, ev, pref):
        for t in self.canvas.gettags(self.canvas.find_closest(
                self.canvas.canvasx(ev.x), self.canvas.canvasy(ev.y))):
            if t.startswith(pref):
                return t[len(pref):]
        return None

    def on_press(self, ev):
        it = self._tag_of(ev, "tray:")
        if it and not self.item_used(it):
            self.drag = it
            self.msg = ""

    def on_move(self, ev):
        if not self.drag:
            return
        self.canvas.delete("ghost")
        name, drawer, sc = ITEMS[self.drag]
        try:
            drawer(self.canvas, ev.x, ev.y, sc * 0.55, ("ghost",))
        except Exception:
            pass

    def on_release(self, ev):
        if not self.drag:
            return
        item, self.drag = self.drag, None
        self.canvas.delete("ghost")
        target = None
        for key, col, row, acc, need, cap in self.slots():
            x, y = COLX[col], ROWY[row]
            if x <= ev.x <= x + COLW and y <= ev.y <= y + ROWH:
                target = (key, acc, need, cap)
                break
        if target is None:
            self.redraw()
            return
        key, acc, need, cap = target
        if key in self.placed:
            self.msg = T("이미 조립된 자리입니다.", "Slot already occupied.")
        elif item not in acc:
            if item == "kelvin" and self.app.setup == "C":
                self.msg = T("캘빈 클립은 가열 시 ABS 플라스틱이 물러지므로 사용하지 않습니다.",
                             "Do not use the Kelvin clip in hot water (ABS softens).")
            else:
                self.msg = T("이 자리에 맞지 않는 장비입니다.", "This item does not fit here.")
        elif not self.need_ok(need):
            self.msg = T("먼저 선행 조립을 완료하십시오.", "Complete the prerequisite first.")
        else:
            self.placed[key] = item
            self.msg = ""
            self.app.on_assembly_change()
        self.redraw()

    def on_right(self, ev):
        for key, col, row, acc, need, cap in self.slots():
            x, y = COLX[col], ROWY[row]
            if x <= ev.x <= x + COLW and y <= ev.y <= y + ROWH and key in self.placed:
                # 이 슬롯에 의존하는 슬롯도 함께 제거
                changed = True
                del self.placed[key]
                while changed:
                    changed = False
                    for k2, c2, r2, a2, n2, cp2 in self.slots():
                        if k2 in self.placed and not self.need_ok(n2):
                            del self.placed[k2]
                            changed = True
                self.msg = ""
                self.app.on_assembly_change()
                self.redraw()
                return


# =====================================================================
#  실험대(Bench) 탭
# =====================================================================

SCALE_UNITS = [("g", 1.0, 2), ("gn", 15.4324, 1), ("oz", 0.0352740, 3),
               ("ozt", 0.0321507, 3), ("dwt", 0.643015, 2), ("ct", 5.0, 2),
               ("tl", 0.0264554, 3)]

DMM_FUNCS = ["OFF", "V", "mV", "OHM", "CAP", "uA", "mA", "A"]
DMM_LABEL = {"OFF": "OFF", "V": "V", "mV": "mV", "OHM": "Ω", "CAP": "⊣⊢",
             "uA": "µA", "mA": "mA", "A": "A"}


class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.canvas = tk.Canvas(self, width=1180, height=720, bg="#2b2f34",
                                highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.wids = []
        self.dyn = {}
        self._rep = None
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "_pan0", None))
        self._pan0 = None
        self.build()

    # ---------------- 공통 위젯 ----------------
    def btn(self, x, y, text, cmd, w=6, bg="#d9dde1", fg="#1c1f22", font=None,
            repeat=False):
        b = tk.Button(self.canvas, text=text, font=font or FONT["s"], bg=bg,
                      fg=fg, width=w, relief="raised", bd=2,
                      activebackground="#f0f2f4", padx=1, pady=0)
        if repeat:
            b.bind("<ButtonPress-1>", lambda e, f=cmd: self.start_rep(f))
            b.bind("<ButtonRelease-1>", lambda e: self.stop_rep())
        else:
            b.configure(command=cmd)
        wid = self.canvas.create_window(x, y, window=b, anchor="nw")
        self.wids.append((b, wid))
        return b

    def start_rep(self, fn):
        self.stop_rep()
        self._delay = 260

        def step():
            fn()
            self._delay = max(28, int(self._delay * 0.72))
            self._rep = self.after(self._delay, step)
        fn()
        self._rep = self.after(self._delay, step)

    def stop_rep(self):
        if self._rep:
            self.after_cancel(self._rep)
            self._rep = None

    def clear(self):
        self.stop_rep()
        for b, wid in self.wids:
            self.canvas.delete(wid)
            b.destroy()
        self.wids = []
        self.dyn = {}
        self.canvas.delete("all")

    # ---------------- 구성 ----------------
    def build(self):
        self.clear()
        s = self.app.setup
        c = self.canvas
        c.create_text(14, 12, anchor="nw", font=FONT["l"], fill="#e9edf1",
                      text=dict(SETUP_NAMES)[s])
        self.dyn["clock"] = c.create_text(1166, 16, anchor="ne", font=FONT["n"],
                                          fill="#8f989f", text="")
        if s == "A":
            self.panel_caliper(14, 44)
            self.panel_scale(14, 470)
            self.panel_dmm(830, 300)
            self.panel_sample(430, 470)
        elif s == "B":
            self.panel_siggen(14, 44)
            self.panel_dmm(830, 44)
            self.panel_schematic(14, 320)
        elif s == "C":
            self.panel_bath(14, 44)
            self.panel_dmm(830, 44)
            self.panel_schematic(14, 380)
        else:
            self.panel_siggen(14, 44)
            self.panel_dmm(830, 44)
            self.panel_schematic(14, 320)
        self.refresh()

    # ---------------- 버니어 캘리퍼스 ----------------
    def panel_caliper(self, x, y):
        c = self.canvas
        W, H = 800, 410
        rrect(c, x, y, x + W, y + H, 8, fill="#343a40", outline="#4d555d")
        c.create_text(x + 12, y + 10, anchor="nw", font=FONT["mb"], fill="#e9edf1",
                      text=T("버니어 캘리퍼스", "Vernier caliper"))
        if "caliper" not in self.app.placed["A"]:
            c.create_text(x + W / 2, y + H / 2, font=FONT["m"], fill="#8f989f",
                          text=T("조립 탭에서 캘리퍼스를 배치하십시오.",
                                 "Place the caliper in the Assembly tab."))
            return
        # 전체 모습
        c.create_rectangle(x + 12, y + 34, x + W - 12, y + 104, fill="#22262a",
                           outline="#4d555d")
        self.dyn["cal_full"] = (x + 12, y + 34, W - 24, 70)
        # 확대창
        c.create_rectangle(x + 12, y + 112, x + W - 12, y + 292, fill="#f4f6f7",
                           outline="#4d555d")
        self.dyn["cal_zoom"] = (x + 14, y + 114, W - 28, 176)
        # 조작
        yy = y + 300
        c.create_text(x + 14, yy, anchor="nw", font=FONT["n"], fill="#cfd5da",
                      text=T("측정 대상", "Quantity"))
        for i, (k, lb) in enumerate((("l", T("길이 l", "length l")),
                                     ("w", T("너비 w", "width w")),
                                     ("t", T("두께 t", "thickness t")))):
            self.btn(x + 90 + i * 78, yy - 4, lb, lambda kk=k: self.set_cal("k", kk), 8)
        c.create_text(x + 14, yy + 34, anchor="nw", font=FONT["n"], fill="#cfd5da",
                      text=T("측정 지점", "Position"))
        for i in range(6):
            self.btn(x + 90 + i * 44, yy + 30, str(i + 1),
                     lambda ii=i: self.set_cal("p", ii), 3)
        self.btn(x + 14, yy + 66, T("판을 물기", "clamp plate"),
                 lambda: self.set_cal("s", 1), 12)
        self.btn(x + 130, yy + 66, T("턱 닫기(0점)", "close jaws"),
                 lambda: self.set_cal("s", 0), 12)
        self.btn(x + 250, yy + 66, T("턱 열기", "open jaws"),
                 lambda: self.set_cal("s", 2), 10)
        c.create_text(x + 380, yy + 40, anchor="nw", font=FONT["n"], fill="#cfd5da",
                      text=T("확대창 이동", "pan zoom window"))
        for i, (lb, dv) in enumerate((("◀◀", -5.0), ("◀", -1.0), ("▶", 1.0),
                                      ("▶▶", 5.0))):
            self.btn(x + 380 + i * 56, yy + 62, lb,
                     lambda d=dv: self.pan_cal(d), 4, repeat=True)
        self.dyn["cal_txt"] = c.create_text(x + 600, yy + 34, anchor="nw",
                                            font=FONT["n"], fill="#9aa4ad", text="")

    def set_cal(self, what, val):
        if what == "k":
            self.app.cal["k"] = val
        elif what == "p":
            self.app.cal["p"] = val
        else:
            self.app.cal["state"] = val
            if val == 1:
                self.app.cal["pan"] = max(0.0, self.cal_reading() - 3.0)
            elif val == 0:
                self.app.cal["pan"] = 0.0
        self.refresh()

    def pan_cal(self, d):
        self.app.cal["pan"] = min(140.0, max(-2.0, self.app.cal["pan"] + d))
        self.refresh()

    def cal_reading(self):
        st = self.app.cal["state"]
        if st == 0:
            return 0.0
        if st == 2:
            return 62.0
        pl = self.app.plate_of("A")
        if pl is None:
            return 0.0
        return pl.dim_true(self.app.cal["k"], self.app.cal["p"])

    def draw_caliper_scales(self):
        c = self.canvas
        if "cal_zoom" not in self.dyn:
            return
        c.delete("calg")
        rd = self.cal_reading()
        # 전체 모습
        fx, fy, fw, fh = self.dyn["cal_full"]
        ppm_f = (fw - 40) / 160.0
        c.create_rectangle(fx + 10, fy + 30, fx + 10 + 160 * ppm_f, fy + 44,
                           fill="#c8ccd0", outline="#6f7378", tags="calg")
        for mm in range(0, 161, 10):
            c.create_line(fx + 10 + mm * ppm_f, fy + 30, fx + 10 + mm * ppm_f,
                          fy + 36, fill="#5f6368", tags="calg")
        xv = fx + 10 + rd * ppm_f
        c.create_rectangle(xv, fy + 20, xv + 49 * ppm_f, fy + 32, fill="#dfe3e7",
                           outline="#6f7378", tags="calg")
        c.create_polygon(fx + 10, fy + 44, fx + 10, fy + 62, fx + 16, fy + 44,
                         fill="#c8ccd0", outline="#6f7378", tags="calg")
        c.create_polygon(xv, fy + 44, xv, fy + 62, xv - 6, fy + 44,
                         fill="#c8ccd0", outline="#6f7378", tags="calg")
        if self.app.cal["state"] == 1:
            c.create_rectangle(fx + 10, fy + 48, xv, fy + 56, fill="#9aa0a6",
                               outline="#5f6368", tags="calg")
        # 확대창
        zx, zy, zw, zh = self.dyn["cal_zoom"]
        pan = self.app.cal["pan"]
        ppm = 40.0
        c.create_rectangle(zx, zy, zx + zw, zy + zh, fill="#eef1f3", outline="",
                           tags="calg")
        base = zy + zh * 0.52
        c.create_rectangle(zx, zy + 8, zx + zw, base, fill="#dfe3e7",
                           outline="#9aa0a6", tags="calg")
        c.create_rectangle(zx, base, zx + zw, zy + zh - 6, fill="#cfd4d9",
                           outline="#9aa0a6", tags="calg")
        mm0 = int(math.floor(pan)) - 1
        mm1 = int(math.ceil(pan + zw / ppm)) + 1
        for mm in range(mm0, mm1 + 1):
            xx = zx + (mm - pan) * ppm
            if xx < zx - 2 or xx > zx + zw + 2:
                continue
            ln = 40 if mm % 10 == 0 else (26 if mm % 5 == 0 else 16)
            c.create_line(xx, base, xx, base - ln, fill="#2b2f34", tags="calg")
            if mm % 10 == 0:
                c.create_text(xx, base - ln - 10, text=str(mm // 10),
                              font=FONT["n"], fill="#2b2f34", tags="calg")
        rd_v = rd
        for j in range(51):
            pos = rd_v + j * 0.98
            xx = zx + (pos - pan) * ppm
            if xx < zx - 2 or xx > zx + zw + 2:
                continue
            ln = 30 if j % 5 == 0 else 16
            c.create_line(xx, base, xx, base + ln, fill="#2b2f34", tags="calg")
            if j % 5 == 0:
                c.create_text(xx, base + ln + 9, text=str(j // 5), font=FONT["n"],
                              fill="#2b2f34", tags="calg")
        c.create_line(zx, base, zx + zw, base, fill="#7a8288", tags="calg")
        c.itemconfigure(self.dyn["cal_txt"], text=T(
            "확대창 위치: %.0f–%.0f mm\n(주척 위 = mm, 부척 아래 = 0.02 mm 단위)",
            "window: %.0f–%.0f mm\n(main scale above, vernier below)") %
            (pan, pan + zw / ppm))

    # ---------------- 전자 저울 ----------------
    def panel_scale(self, x, y):
        c = self.canvas
        rrect(c, x, y, x + 400, y + 230, 8, fill="#343a40", outline="#4d555d")
        c.create_text(x + 12, y + 10, anchor="nw", font=FONT["mb"], fill="#e9edf1",
                      text=T("전자 저울", "Electronic scale"))
        if "scale" not in self.app.placed["A"]:
            c.create_text(x + 200, y + 120, font=FONT["m"], fill="#8f989f",
                          text=T("조립 탭에서 저울을 배치하십시오.",
                                 "Place the scale in the Assembly tab."))
            return
        rrect(c, x + 30, y + 40, x + 250, y + 160, 8, fill="#d7dbe0",
              outline="#8b9198")
        c.create_rectangle(x + 44, y + 50, x + 236, y + 92, fill="#b98b7a",
                           outline="#7a5a4d")
        c.create_rectangle(x + 50, y + 100, x + 230, y + 138, fill="#7f8a7c",
                           outline="#4d5549")
        self.dyn["scale_lcd"] = c.create_text(x + 224, y + 120, anchor="e",
                                              font=FONT["lcd2"], fill="#22261f",
                                              text="")
        self.btn(x + 270, y + 46, "ON/OFF", lambda: self.app.toggle_scale(), 8)
        self.btn(x + 270, y + 76, "MODE", lambda: self.app.scale_mode(), 8)
        self.btn(x + 270, y + 106, "TARE", lambda: self.app.scale_tare(), 8)
        self.btn(x + 270, y + 150, T("판 올리기/내리기", "put/remove plate"),
                 lambda: self.app.scale_put(), 16)
        self.dyn["scale_note"] = c.create_text(x + 30, y + 180, anchor="nw",
                                               font=FONT["s"], fill="#9aa4ad", text="")

    # ---------------- 시료(판) ----------------
    def panel_sample(self, x, y):
        c = self.canvas
        rrect(c, x, y, x + 400, y + 230, 8, fill="#343a40", outline="#4d555d")
        c.create_text(x + 12, y + 10, anchor="nw", font=FONT["mb"], fill="#e9edf1",
                      text=T("시료 / 정전용량 측정", "Sample / capacitance"))
        P = self.app.placed["A"]
        if "plate" not in P:
            c.create_text(x + 200, y + 120, font=FONT["m"], fill="#8f989f",
                          text=T("조립 탭에서 PZT 판을 선택하십시오.",
                                 "Select a PZT plate in the Assembly tab."))
            return
        d_pzt(c, x + 180, y + 70, 1.9, idx=int(P["plate"][-1]))
        if "kelvin" in P:
            d_kelvin(c, x + 120, y + 60, 1.1)
        self.dyn["sample_note"] = c.create_text(x + 20, y + 140, anchor="nw",
                                                font=FONT["s"], fill="#9aa4ad",
                                                width=360, text="")

    # ---------------- DMM ----------------
    def panel_dmm(self, x, y):
        c = self.canvas
        W, H = 336, 400
        rrect(c, x, y, x + W, y + H, 10, fill="#f2c21a", outline="#7a6300")
        rrect(c, x + 10, y + 10, x + W - 10, y + H - 12, 8, fill="#3f4448",
              outline="#23272a")
        c.create_text(x + W / 2, y + 24, font=FONT["b"], fill="#e9edf1",
                      text="DIGITAL MULTIMETER")
        P = self.app.placed[self.app.setup]
        if "dmm" not in P:
            c.create_text(x + W / 2, y + H / 2, font=FONT["m"], fill="#c9cfd4",
                          text=T("조립 탭에서 DMM을 배치하십시오.",
                                 "Place the DMM in the Assembly tab."))
            return
        c.create_rectangle(x + 26, y + 36, x + W - 26, y + 110, fill="#c9d6c0",
                           outline="#5b6b56")
        self.dyn["dmm_lcd"] = c.create_text(x + W - 40, y + 82, anchor="e",
                                            font=FONT["lcd"], fill="#1d2320", text="")
        self.dyn["dmm_unit"] = c.create_text(x + W - 34, y + 100, anchor="e",
                                             font=FONT["s"], fill="#1d2320", text="")
        self.dyn["dmm_ac"] = c.create_text(x + 36, y + 48, anchor="w",
                                           font=FONT["s"], fill="#1d2320", text="")
        # 회전 스위치
        cx, cy, R = x + W / 2, y + 210, 56
        c.create_oval(cx - R, cy - R, cx + R, cy + R, fill="#5a6066", outline="#2a2e31")
        c.create_oval(cx - 14, cy - 14, cx + 14, cy + 14, fill="#2a2e31")
        for i, f in enumerate(DMM_FUNCS):
            a = -math.pi / 2 + i * 2 * math.pi / len(DMM_FUNCS)
            lx, ly = cx + (R + 22) * math.cos(a), cy + (R + 22) * math.sin(a)
            c.create_text(lx, ly, text=DMM_LABEL[f], font=FONT["b"],
                          fill="#f0f2f4", tags=("dial", "dial:" + f))
        self.dyn["dmm_dial"] = (cx, cy, R)
        self.dyn["dial_ptr"] = c.create_line(cx, cy, cx, cy - R + 6, width=5,
                                             fill="#f2c21a")
        self.btn(x + 24, y + 176, "YELLOW", lambda: self.app.dmm_yellow(), 8,
                 bg="#f2c21a")
        # 단자
        ty = y + H - 60
        for i, (nm, key) in enumerate((("µA/mA", "uA"), ("A", "A"), ("COM", "COM"),
                                       ("VΩ⊣⊢", "V"))):
            tx = x + 34 + i * 72
            c.create_oval(tx - 12, ty - 12, tx + 12, ty + 12,
                          fill="#d02020" if key != "COM" else "#111111",
                          outline="#000000", tags=("term", "term:" + key))
            c.create_text(tx, ty + 22, text=nm, font=FONT["s"], fill="#e9edf1",
                          tags=("term", "term:" + key))
        self.dyn["dmm_lead"] = c.create_oval(0, 0, 0, 0, outline="#4ad06a", width=3)
        self.dyn["dmm_termxy"] = {k: (x + 34 + i * 72, ty) for i, (nm, k) in
                                  enumerate((("µA/mA", "uA"), ("A", "A"),
                                             ("COM", "COM"), ("VΩ⊣⊢", "V")))}

    # ---------------- 신호발생기 ----------------
    def panel_siggen(self, x, y):
        c = self.canvas
        W, H = 800, 258
        rrect(c, x, y, x + W, y + H, 8, fill="#e9edf1", outline="#8b9198")
        c.create_text(x + 16, y + 12, anchor="nw", font=FONT["mb"], fill="#2b2f34",
                      text="DDS Signal Generator")
        P = self.app.placed[self.app.setup]
        if "siggen" not in P:
            c.create_text(x + W / 2, y + H / 2, font=FONT["m"], fill="#6f7378",
                          text=T("조립 탭에서 신호발생기를 배치하십시오.",
                                 "Place the generator in the Assembly tab."))
            return
        c.create_rectangle(x + 130, y + 40, x + 470, y + 130, fill="#2f6fb0",
                           outline="#1b4470")
        self.dyn["sg_lcd"] = c.create_text(x + 452, y + 78, anchor="e",
                                           font=FONT["lcd"], fill="#dff0ff", text="")
        self.dyn["sg_cur"] = c.create_text(x + 452, y + 96, anchor="e",
                                           font=FONT["lcd"], fill="#8fd0ff", text="")
        self.dyn["sg_wave"] = c.create_text(x + 146, y + 112, anchor="w",
                                            font=FONT["s"], fill="#dff0ff", text="")
        self.btn(x + 20, y + 44, T("전원", "POWER"), lambda: self.app.sg_power(), 8,
                 bg="#d03a2a", fg="#ffffff")
        c.create_text(x + 24, y + 84, anchor="nw", font=FONT["s"], fill="#2b2f34",
                      text=T("커서", "cursor"))
        self.btn(x + 20, y + 100, "◄", lambda: self.app.sg_cursor(-1), 3)
        self.btn(x + 70, y + 100, "►", lambda: self.app.sg_cursor(1), 3)
        c.create_text(x + 500, y + 40, anchor="nw", font=FONT["n"], fill="#2b2f34",
                      text="Adjust")
        self.btn(x + 500, y + 58, "▲", lambda: self.app.sg_adjust(1), 4, repeat=True)
        self.btn(x + 500, y + 88, "▼", lambda: self.app.sg_adjust(-1), 4, repeat=True)
        c.create_text(x + 580, y + 40, anchor="nw", font=FONT["n"], fill="#2b2f34",
                      text="Amplitude")
        self.btn(x + 580, y + 58, "▲", lambda: self.app.sg_amp(1), 4, repeat=True)
        self.btn(x + 580, y + 88, "▼", lambda: self.app.sg_amp(-1), 4, repeat=True)
        c.create_text(x + 665, y + 40, anchor="nw", font=FONT["n"], fill="#2b2f34",
                      text="DC offset")
        self.btn(x + 665, y + 58, "▲", lambda: self.app.sg_dc(1), 4, repeat=True)
        self.btn(x + 665, y + 88, "▼", lambda: self.app.sg_dc(-1), 4, repeat=True)
        c.create_rectangle(x + 130, y + 150, x + 470, y + 240, fill="#dfe4e9",
                           outline="#9aa0a6")
        self.dyn["sg_scope"] = (x + 130, y + 150, 340, 90)
        for i, nm in enumerate(("EXT.IN", "TTL", "OUT")):
            c.create_oval(x + 520 + i * 70, y + 160, x + 552 + i * 70, y + 192,
                          fill="#c9a227", outline="#6f5a12")
            c.create_text(x + 536 + i * 70, y + 200, text=nm, font=FONT["s"],
                          fill="#2b2f34")
        c.create_text(x + 24, y + 150, anchor="nw", font=FONT["s"], fill="#6f7378",
                      width=100,
                      text=T("커서 자리 = 조정 단위", "cursor digit = step"))

    # ---------------- 항온수조 ----------------
    def panel_bath(self, x, y):
        c = self.canvas
        W, H = 800, 320
        rrect(c, x, y, x + W, y + H, 8, fill="#eceff2", outline="#8b9198")
        c.create_text(x + 16, y + 12, anchor="nw", font=FONT["mb"], fill="#2b2f34",
                      text=T("항온수조", "Thermostat water bath"))
        P = self.app.placed["C"]
        if "bath" not in P:
            c.create_text(x + W / 2, y + H / 2, font=FONT["m"], fill="#6f7378",
                          text=T("조립 탭에서 수조를 배치하십시오.",
                                 "Place the bath in the Assembly tab."))
            return
        c.create_rectangle(x + 40, y + 60, x + 300, y + 250, fill="#dfe3e7",
                           outline="#8b9198")
        c.create_rectangle(x + 60, y + 80, x + 280, y + 230, fill="#b7c4cc",
                           outline="#7f8a92")
        self.dyn["bath_water"] = c.create_rectangle(x + 62, y + 150, x + 278,
                                                    y + 228, fill="#5aa0cf",
                                                    outline="", state="hidden")
        self.dyn["bath_bag"] = (x + 170, y + 190)
        c.create_rectangle(x + 340, y + 70, x + 470, y + 120, fill="#2a2020",
                           outline="#111111")
        self.dyn["bath_lcd"] = c.create_text(x + 460, y + 95, anchor="e",
                                             font=FONT["lcd"], fill="#ff3b30", text="")
        for i, nm in enumerate(("Set", "Heat", "Keep")):
            c.create_oval(x + 350 + i * 44, y + 132, x + 362 + i * 44, y + 144,
                          fill="#3a3030", outline="#555555",
                          tags="ind:" + nm.lower())
            c.create_text(x + 356 + i * 44, y + 154, text=nm, font=FONT["s"],
                          fill="#2b2f34")
        self.btn(x + 344, y + 170, "Set", lambda: self.app.bath_set(), 6)
        self.btn(x + 400, y + 170, "▲", lambda: self.app.bath_inc(1), 4, repeat=True)
        self.btn(x + 448, y + 170, "▼", lambda: self.app.bath_inc(-1), 4, repeat=True)
        self.btn(x + 344, y + 206, T("전원", "POWER"), lambda: self.app.bath_power(),
                 8, bg="#d03a2a", fg="#ffffff")
        self.dyn["bath_note"] = c.create_text(x + 520, y + 60, anchor="nw",
                                              font=FONT["s"], fill="#4d555d",
                                              width=260, text="")

    # ---------------- 배치 도해 ----------------
    def panel_schematic(self, x, y):
        c = self.canvas
        W, H = 800, 380 if self.app.setup in ("B",) else 320
        rrect(c, x, y, x + W, y + H, 8, fill="#343a40", outline="#4d555d")
        c.create_text(x + 12, y + 8, anchor="nw", font=FONT["mb"], fill="#e9edf1",
                      text=T("실험 배치", "Experimental arrangement"))
        self.dyn["schem"] = (x, y + 30, W, H - 30)

    def draw_schematic(self):
        if "schem" not in self.dyn:
            return
        c = self.canvas
        c.delete("schg")
        x, y, W, H = self.dyn["schem"]
        s = self.app.setup
        P = self.app.placed[s]
        cx, cy = x + W / 2, y + H / 2
        if s == "B":
            if "plate" in P:
                d_pzt(c, cx, cy, 2.4, ("schg",), idx=int(P["plate"][-1]))
            for k, dx in (("clipL", -100), ("clipM", 0), ("clipR", 100)):
                if k in P:
                    d_kelvin(c, cx + dx - 40, cy - 30, 1.4, ("schg",))
            if "siggen" in P:
                c.create_oval(x + 60, cy - 30, x + 120, cy + 30, outline="#cfd5da",
                              width=2, tags="schg")
                c.create_text(x + 90, cy, text="∿", font=FONT["l"], fill="#cfd5da",
                              tags="schg")
            if "dmm" in P:
                c.create_oval(x + W - 130, cy - 90, x + W - 70, cy - 30,
                              outline="#cfd5da", width=2, tags="schg")
                c.create_text(x + W - 100, cy - 60, text="A", font=FONT["l"],
                              fill="#cfd5da", tags="schg")
            if "cabg" in P:
                c.create_line(x + 90, cy + 30, x + 90, cy + 90, cx - 60, cy + 90,
                              cx - 60, cy + 10, fill="#cc2b1f", width=3, tags="schg")
            if "cabd" in P:
                c.create_line(cx - 40, cy - 32, cx - 40, cy - 60, x - 100 + W, cy - 60,
                              fill="#cc2b1f", width=3, tags="schg")
                c.create_line(x + W - 100, cy - 30, x + W - 100, cy + 90,
                              x + 90, cy + 90, fill="#1a1a1a", width=3, tags="schg")
            st = self.app.plate_state_text()
            c.create_text(x + 12, y + H - 18, anchor="w", font=FONT["s"],
                          fill="#9aa4ad", text=st, tags="schg")
        elif s == "C":
            if "bag" in P:
                bx, by = (x + 200, y + 150) if "submerge" in P else (x + 420, y + 120)
                d_bag(c, bx, by, 1.6, ("schg",))
                if "pbag" in P:
                    d_pzt(c, bx, by, 1.0, ("schg",), idx=int(P["pbag"][-1]))
                if "tongs" in P:
                    d_tongs(c, bx, by - 46, 1.2, ("schg",))
                if "submerge" in P:
                    d_pebble(c, bx + 10, by + 30, 1.0, ("schg",))
                if "cabc" in P and "dmm" in P:
                    c.create_line(bx + 20, by - 40, x + W - 120, y + 60,
                                  fill="#cc2b1f", width=3, smooth=True, tags="schg")
            c.create_text(x + 12, y + H - 18, anchor="w", font=FONT["s"],
                          fill="#9aa4ad", text=self.app.plate_state_text(),
                          tags="schg")
        else:
            self._schem_rod(c, x, y, W, H, s, P)

    def _schem_rod(self, c, x, y, W, H, s, P):
        """그림 11 / 13 / 14 배치도 (위에서 본 모습)."""
        cy = y + H / 2
        x0, x1 = x + 70, x + 470          # 막대 좌우 끝
        longi = (s != "D1")
        if "box" in P:
            col = ("#2f3236", "#15171a") if s == "E" else ("#e6f0f4", "#7f9aa6")
            rrect(c, x + 40, cy - 62, x + 600, cy + 62, 6, fill=col[0],
                  outline=col[1], tags="schg")
            c.create_rectangle(x + 52, cy - 26, x + 588, cy + 26,
                               fill="#d5e4ea" if s != "E" else "#3b3f44",
                               outline="#96b0bb" if s != "E" else "#1d1f22",
                               tags="schg")
        rod_ok = ("rod" in P) or (s == "E" and "box" in P)
        if rod_ok:
            if s == "E":
                c.create_rectangle(x0, cy - 16, x1, cy + 16, fill="#3f4348",
                                   outline="#2a2d31", tags="schg")
                c.create_rectangle(x1 - 60, cy - 16, x1 + 40, cy + 16,
                                   fill="#c2c6ca", outline="#787d82", tags="schg")
                x1 = x1 + 40
            else:
                c.create_rectangle(x0, cy - 16, x1, cy + 16, fill="#c2c6ca",
                                   outline="#787d82", tags="schg")
                c.create_rectangle(x0, cy - 16, x1, cy - 9, fill="#dde1e5",
                                   outline="", tags="schg")
            c.create_text((x0 + x1) / 2, cy, text=T("알루미늄 막대", "Aluminium rod"),
                          font=FONT["s"], fill="#3a3f44" if s != "E" else "#c2c6ca",
                          tags="schg")
        if "spring" in P and rod_ok:
            pts = []
            for i in range(17):
                pts += [x + 54 + i * 2.4, cy + (11 if i % 2 else -11)]
            c.create_line(pts, fill="#9aa0a6", width=3, tags="schg")
        # PZT 판
        px = x1 + 6
        lab_col = "#c9cfd4" if s == "E" else "#31363c"
        for k, dy, lab in (("pztt", -1, T("변환기", "transducer")),
                           ("pzts", 1, T("센서", "sensor"))):
            if k not in P:
                continue
            if longi:   # 그림 13 : 판의 길이 방향이 막대와 나란 (압축 → 종파)
                yy = cy + dy * 9
                c.create_rectangle(px, yy - 6, px + 92, yy + 6, fill="#e8d84a",
                                   outline="#b9a92c", tags="schg")
                c.create_text(px + 46, yy, text=str(P[k][-1]), font=FONT["s"],
                              fill="#4a4415", tags="schg")
                c.create_text(px + 56, cy + dy * 44, text=lab, font=FONT["s"],
                              fill=lab_col, anchor="w", tags="schg")
                c.create_line(px + 46, yy + dy * 6, px + 46, cy + dy * 60,
                              fill="#cc2b1f" if dy < 0 else "#1a1a1a", width=2,
                              tags="schg")
            else:       # 그림 11 : 판의 길이 방향이 막대에 수직 (마찰 → 횡파)
                xx = x1 + 14
                y2 = cy + dy * 12
                y3 = cy + dy * 74
                c.create_rectangle(xx - 6, min(y2, y3), xx + 6, max(y2, y3),
                                   fill="#e8d84a", outline="#b9a92c", tags="schg")
                c.create_text(xx, (y2 + y3) / 2, text=str(P[k][-1]),
                              font=FONT["s"], fill="#4a4415", angle=90, tags="schg")
                c.create_text(xx, y3 + dy * 12, text=lab, font=FONT["s"],
                              fill=lab_col, tags="schg")
                c.create_line(xx, y3, xx + 40, y3, fill="#cc2b1f" if dy < 0
                              else "#1a1a1a", width=2, tags="schg")
        if "eraser" in P and ("pztt" in P or "pzts" in P):
            ex = (px + 100) if longi else (x1 + 40)
            rrect(c, ex, cy - 40, ex + 46, cy + 40, 5, fill="#e8a33d",
                  outline="#9c6a17", tags="schg")
            c.create_text(ex + 23, cy, text=T("지우개", "eraser"), font=FONT["s"],
                          fill="#6b4a10", angle=90, tags="schg")
        # 계기 기호
        gx, gy = x + W - 96, y + 34
        ax, ay = x + W - 96, y + H - 40
        if "siggen" in P:
            c.create_oval(gx - 22, gy - 22, gx + 22, gy + 22, outline="#cfd5da",
                          width=2, tags="schg")
            c.create_text(gx, gy, text="∿", font=FONT["l"], fill="#cfd5da",
                          tags="schg")
        if "dmm" in P:
            c.create_oval(ax - 22, ay - 22, ax + 22, ay + 22, outline="#cfd5da",
                          width=2, tags="schg")
            c.create_text(ax, ay, text="A", font=FONT["l"], fill="#cfd5da",
                          tags="schg")
        if "cabg" in P and "pztt" in P:
            sx = (px + 46) if longi else (x1 + 54)
            sy = cy - (60 if longi else 74)
            c.create_line(sx, sy, sx, gy, gx - 22, gy, fill="#cc2b1f", width=2,
                          tags="schg")
        if "cabd" in P and "pzts" in P:
            sx = (px + 46) if longi else (x1 + 54)
            sy = cy + (60 if longi else 74)
            c.create_line(sx, sy, sx, ay, ax - 22, ay, fill="#cc2b1f", width=2,
                          tags="schg")
        # 파동 방향 표시 (문제지 그림과 동일)
        if rod_ok:
            c.create_line(x0 + 30, cy - 44, x0 + 130, cy - 44, arrow="both",
                          fill="#5e9ec9", width=3, tags="schg")
            c.create_text(x0 + 80, cy - 56, text=T("전파 방향", "propagation"),
                          font=FONT["s"], fill="#5e9ec9", tags="schg")
            if longi:
                c.create_line(x0 + 30, cy + 44, x0 + 130, cy + 44, arrow="both",
                              fill="#5e9ec9", width=3, tags="schg")
            else:
                c.create_line(x0 + 80, cy + 26, x0 + 80, cy + 62, arrow="both",
                              fill="#5e9ec9", width=3, tags="schg")
            c.create_text(x0 + 80, cy + 74, text=T("진동 방향", "vibration"),
                          font=FONT["s"], fill="#5e9ec9", tags="schg")

    # ---------------- 클릭 처리 ----------------
    def on_click(self, ev):
        it = self.canvas.find_closest(ev.x, ev.y)
        tags = self.canvas.gettags(it)
        for t in tags:
            if t.startswith("dial:"):
                self.app.dmm.update(func=t[5:])
                self.refresh()
                return
            if t.startswith("term:"):
                k = t[5:]
                if k != "COM":
                    self.app.dmm["lead"] = k
                    self.refresh()
                return
        if "cal_zoom" in self.dyn:
            zx, zy, zw, zh = self.dyn["cal_zoom"]
            if zx <= ev.x <= zx + zw and zy <= ev.y <= zy + zh:
                self._pan0 = (ev.x, self.app.cal["pan"])

    def on_drag(self, ev):
        if self._pan0:
            x0, p0 = self._pan0
            self.app.cal["pan"] = min(140.0, max(-2.0, p0 - (ev.x - x0) / 40.0))
            self.refresh()

    # ---------------- 표시 갱신 ----------------
    def refresh(self):
        app = self.app
        c = self.canvas
        if "clock" in self.dyn:
            t = int(app.sim_t)
            c.itemconfigure(self.dyn["clock"],
                            text=T("경과 %02d:%02d:%02d", "elapsed %02d:%02d:%02d")
                            % (t // 3600, t // 60 % 60, t % 60))
        if "cal_zoom" in self.dyn:
            self.draw_caliper_scales()
        if "scale_lcd" in self.dyn:
            c.itemconfigure(self.dyn["scale_lcd"], text=app.scale_text())
            c.itemconfigure(self.dyn["scale_note"], text=app.scale_note())
        if "sample_note" in self.dyn:
            c.itemconfigure(self.dyn["sample_note"], text=app.sample_note())
        if "dmm_lcd" in self.dyn:
            v, u, ac = app.dmm_text()
            c.itemconfigure(self.dyn["dmm_lcd"], text=v)
            c.itemconfigure(self.dyn["dmm_unit"], text=u)
            c.itemconfigure(self.dyn["dmm_ac"], text=ac)
            cx, cy, R = self.dyn["dmm_dial"]
            a = -math.pi / 2 + DMM_FUNCS.index(app.dmm["func"]) * 2 * math.pi / 8
            c.coords(self.dyn["dial_ptr"], cx, cy, cx + (R - 8) * math.cos(a),
                     cy + (R - 8) * math.sin(a))
            tx, ty = self.dyn["dmm_termxy"][app.dmm["lead"]]
            c.coords(self.dyn["dmm_lead"], tx - 17, ty - 17, tx + 17, ty + 17)
        if "sg_lcd" in self.dyn:
            c.itemconfigure(self.dyn["sg_lcd"], text=app.sg_text())
            c.itemconfigure(self.dyn["sg_cur"], text=app.sg_cursor_text())
            c.itemconfigure(self.dyn["sg_wave"], text=app.sg_wave_text())
            self.draw_scope()
        if "bath_lcd" in self.dyn:
            c.itemconfigure(self.dyn["bath_lcd"], text=app.bath_text())
            c.itemconfigure(self.dyn["bath_note"], text=app.bath_note())
            c.itemconfigure(self.dyn["bath_water"],
                            state="normal" if "water" in app.placed["C"] else "hidden")
            for nm, on in (("set", app.bath["setmode"]), ("heat", app.bath["heating"]),
                           ("keep", app.bath["on"] and not app.bath["heating"])):
                c.itemconfigure("ind:" + nm,
                                fill="#ff3b30" if on else "#3a3030")
        self.draw_schematic()

    def draw_scope(self):
        """실제 기기의 표시 패널처럼 파형 종류만 나타낸다 (진폭 정보 없음)."""
        if "sg_scope" not in self.dyn:
            return
        c = self.canvas
        c.delete("scope")
        x, y, w, h = self.dyn["sg_scope"]
        if not self.app.sg["on"]:
            return
        pts = []
        for i in range(w):
            pts += [x + i, y + h / 2 - math.sin(i / w * 4 * math.pi) * (h / 2 - 16)]
        c.create_line(pts, fill="#1b4470", width=2, tags="scope")
        c.create_text(x + 8, y + 8, anchor="nw", text="WAVEFORM: SINE",
                      font=FONT["s"], fill="#4d555d", tags="scope")



# =====================================================================
#  응용 프로그램
# =====================================================================

SIM_SPEED = 25.0          # 1 실제초 = 25 모의초
VMAX_SG = 4.6             # 신호발생기 출력 한계 (V, 순간값)


class App(tk.Tk):
    def __init__(self, seed=None):
        super().__init__()
        self.title("APhO 2015 — %s" % T("압전 효과와 그 응용 (가상 실험)",
                                        "Piezoelectric Effect (virtual lab)"))
        self.geometry("1196x812")
        self.resizable(False, False)
        init_fonts(self)
        self.session = Session(seed)
        self.setup = "A"
        self.placed = {k: {} for k, _ in SETUP_NAMES}
        self.cal = {"k": "l", "p": 0, "state": 2, "pan": 0.0}
        self.scale = {"on": False, "unit": 0, "tare": 0.0, "plate": False}
        self.dmm = {"func": "OFF", "lead": "V", "ac": True}
        self.sg = {"on": False, "f": 1000.0, "cur": 2, "amp": 1.15, "dc": 0.35}
        self.bath = {"on": False, "sp": 40.0, "tw": self.session.t_room,
                     "setmode": False, "heating": False}
        self.sim_t = 0.0
        self._build_ui()
        self._after_id = self.after(100, self.tick)

    # ---------------- UI ----------------
    def _build_ui(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=6, pady=4)
        ttk.Label(bar, text=T("실험 선택:", "Experiment:")).pack(side="left")
        self.cb = ttk.Combobox(bar, state="readonly", width=42,
                               values=[n for _, n in SETUP_NAMES])
        self.cb.current(0)
        self.cb.pack(side="left", padx=6)
        self.cb.bind("<<ComboboxSelected>>", self.on_setup)
        ttk.Label(bar, text="  seed = %d" % self.session.seed,
                  foreground="#666666").pack(side="left", padx=10)
        ttk.Button(bar, text=T("새 세션", "New session"),
                   command=self.new_session).pack(side="right")
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.asm = AssemblyTab(self.nb, self)
        self.bench = BenchTab(self.nb, self)
        self.nb.add(self.asm, text=T(" 조립 ", " Assembly "))
        self.nb.add(self.bench, text=T(" 실험대 ", " Bench "))

    def on_setup(self, *_):
        self.setup = SETUP_NAMES[self.cb.current()][0]
        self.asm.msg = ""
        self.asm.redraw()
        self.bench.build()

    def new_session(self):
        self.session = Session()
        for k in self.placed:
            self.placed[k].clear()
        self.bath["tw"] = self.session.t_room
        self.sim_t = 0.0
        self.title("APhO 2015 — seed %d" % self.session.seed)
        self.asm.redraw()
        self.bench.build()

    def on_assembly_change(self):
        self.bench.build()

    # ---------------- 시간 진행 ----------------
    def step_physics(self, dt):
        self.sim_t += dt
        b, P = self.bath, self.placed["C"]
        has_water = "water" in P
        if b["on"] and has_water:
            if b["tw"] < b["sp"] - 0.15:
                b["heating"] = True
                b["tw"] += 0.0215 * dt
            else:
                b["heating"] = False
        else:
            b["heating"] = False
        b["tw"] -= 0.00010 * (b["tw"] - self.session.t_room) * dt
        cpl = self.plate_of("C")
        for pl in self.session.plates:
            if cpl is pl and "submerge" in P and has_water:
                tgt, tau = b["tw"], 45.0
            else:
                tgt, tau = self.session.t_room, 300.0
            pl.temp += (tgt - pl.temp) * (1.0 - math.exp(-dt / tau))

    def tick(self):
        self.step_physics(0.1 * SIM_SPEED)
        try:
            self.bench.refresh()
        except Exception:
            pass
        self._after_id = self.after(100, self.tick)

    def destroy(self):
        try:
            if getattr(self, "_after_id", None):
                self.after_cancel(self._after_id)
        except Exception:
            pass
        super().destroy()

    # ---------------- 상태 조회 ----------------
    def plate_of(self, setup):
        P = self.placed[setup]
        key = {"A": "plate", "B": "plate", "C": "pbag"}.get(setup)
        if key and key in P:
            return self.session.plates[int(P[key][-1]) - 1]
        return None

    def plate_state_text(self):
        s = self.setup
        P = self.placed[s]
        if s == "B":
            pl = self.plate_of("B")
            if pl is None:
                return ""
            pos = T("중간점", "midpoint") if "clipM" in P else (
                T("왼쪽 끝", "left end") if "clipL" in P else
                (T("오른쪽 끝", "right end") if "clipR" in P else T("없음", "none")))
            return T("PZT 판 #%d, 캘빈 클립 위치: %s",
                     "PZT plate #%d, clip at %s") % (pl.idx + 1, pos)
        if s == "C":
            pl = self.plate_of("C")
            if pl is None:
                return ""
            return T("PZT 판 #%d (봉지 속)", "PZT plate #%d (in the bag)") % (pl.idx + 1)
        return ""

    # ---------------- 저울 ----------------
    def toggle_scale(self):
        self.scale["on"] = not self.scale["on"]
        if self.scale["on"]:
            self.scale["tare"] = 0.0
        self.bench.refresh()

    def scale_mode(self):
        if self.scale["on"]:
            self.scale["unit"] = (self.scale["unit"] + 1) % len(SCALE_UNITS)
        self.bench.refresh()

    def scale_tare(self):
        if self.scale["on"]:
            self.scale["tare"] = self._scale_raw()
        self.bench.refresh()

    def scale_put(self):
        self.scale["plate"] = not self.scale["plate"]
        self._wcnt = getattr(self, "_wcnt", -1) + 1
        self.bench.refresh()

    def _scale_raw(self):
        pl = self.plate_of("A")
        if self.scale["plate"] and pl is not None:
            return pl.mass_reading(getattr(self, "_wcnt", 0))
        return 0.0

    def scale_text(self):
        if not self.scale["on"]:
            return ""
        u, k, dec = SCALE_UNITS[self.scale["unit"]]
        v = (self._scale_raw() - self.scale["tare"]) * k
        return ("%%.%df %%s" % dec) % (v, u)

    def scale_note(self):
        if "plate" not in self.placed["A"]:
            return ""
        return T("PZT 판이 저울 위에 있습니다.", "PZT plate is on the pan.") \
            if self.scale["plate"] else T("저울 접시가 비어 있습니다.", "Pan empty.")

    def sample_note(self):
        P = self.placed["A"]
        t = []
        if "kelvin" in P:
            t.append(T("캘빈 클립이 DMM에 연결되어 판을 물고 있습니다.",
                       "Kelvin clip connects the plate to the DMM."))
        pl = self.plate_of("A")
        return "\n".join(t)

    # ---------------- DMM ----------------
    def dmm_yellow(self):
        self.dmm["ac"] = not self.dmm["ac"]
        self.bench.refresh()

    def _fmt(self, v, ranges):
        for lim, dec, unit in ranges:
            if abs(v) < lim:
                return ("%%.%df" % dec) % v, unit
        return "OL", ranges[-1][2]

    def dmm_text(self):
        f, lead, ac = self.dmm["func"], self.dmm["lead"], self.dmm["ac"]
        s, P = self.setup, self.placed[self.setup]
        if f == "OFF" or "dmm" not in P:
            return "", "", ""
        acs = "AC" if ac else "DC"
        rng = self.session.rng
        if f == "CAP":
            if lead != "V":
                return "OL", "nF", ""
            pl, ok = None, False
            if s == "A":
                pl, ok = self.plate_of("A"), ("kelvin" in P and "plate" in P)
            elif s == "B":
                pl = self.plate_of("B")
                ok = ("cabd" in P and "cabg" in P and not self.sg["on"])
            elif s == "C":
                pl, ok = self.plate_of("C"), ("cabc" in P)
            if not ok or pl is None:
                return "OL", "nF", ""
            c = pl.cap_reading_nF(rng, temp=pl.temp)
            if c < 40:
                return "%.2f" % c, "nF", ""
            if c < 400:
                return "%.1f" % c, "nF", ""
            return "%.4f" % (c / 1000.0), "µF", ""
        if f in ("V", "mV"):
            if lead != "V":
                return "0.000", f, acs
            v = 0.0
            if s == "B" and self.sg["on"] and "cabg" in P and "cabd" in P:
                v = self.sg_rms() * dmm_ac_gain(self.sg["f"]) if ac else self.sg["dc"]
            elif s in ("D1", "D2", "E") and self.sg["on"] and "cabg" in P:
                v = self.sg_rms() * dmm_ac_gain(self.sg["f"]) if ac else self.sg["dc"]
            v += rng.gauss(0.0, 0.0004)
            if f == "mV":
                v *= 1000.0
                return (("%.1f" % v) if abs(v) < 600 else "OL"), "mV", acs
            return "%.3f" % v, "V", acs
        if f in ("uA", "mA", "A"):
            if (f in ("uA", "mA") and lead != "uA") or (f == "A" and lead != "A"):
                return "0.00", DMM_LABEL[f], acs
            i_a = self.circuit_current()          # 암페어
            if not ac:
                i_a = 0.0
            i_a += rng.gauss(0.0, 2e-8)
            if f == "uA":
                v = i_a * 1e6
                return self._fmt(v, ((400, 1, "µA"), (4000, 0, "µA")))[0], "µA", acs
            if f == "mA":
                v = i_a * 1e3
                return self._fmt(v, ((40, 2, "mA"), (400, 1, "mA")))[0], "mA", acs
            return "%.3f" % i_a, "A", acs
        if f == "OHM":
            return "OL", "Ω", ""
        return "", "", ""

    # ---------------- 신호발생기 ----------------
    def sg_power(self):
        self.sg["on"] = not self.sg["on"]
        self.bench.refresh()

    def sg_cursor(self, d):
        self.sg["cur"] = max(0, min(4, self.sg["cur"] + d))
        self.bench.refresh()

    def sg_adjust(self, d):
        step = [10000.0, 1000.0, 100.0, 10.0, 1.0][self.sg["cur"]]
        self.sg["f"] = max(1.0, min(99999.0, self.sg["f"] + d * step))
        self.bench.refresh()

    def sg_amp(self, d):
        self.sg["amp"] = max(0.0, min(3.6, self.sg["amp"] + d * 0.05))
        self.bench.refresh()

    def sg_dc(self, d):
        self.sg["dc"] = max(-1.5, min(1.5, self.sg["dc"] + d * 0.05))
        self.bench.refresh()

    def sg_rms(self):
        """출력의 교류 실효값 (클리핑 반영)."""
        if not self.sg["on"]:
            return 0.0
        pk = self.sg["amp"] * math.sqrt(2.0)
        off = self.sg["dc"]
        n, acc, mean = 256, 0.0, 0.0
        vs = []
        for i in range(n):
            v = off + pk * math.sin(2 * math.pi * i / n)
            v = max(-VMAX_SG, min(VMAX_SG, v))
            vs.append(v)
            mean += v
        mean /= n
        for v in vs:
            acc += (v - mean) ** 2
        return math.sqrt(acc / n)

    def sg_text(self):
        if not self.sg["on"]:
            return ""
        return "%06.3f kHz" % (self.sg["f"] / 1000.0)

    def sg_cursor_text(self):
        if not self.sg["on"]:
            return ""
        pos = [0, 1, 3, 4, 5][self.sg["cur"]]
        return "".join("‾" if i == pos else " " for i in range(6)) + "    "

    def sg_wave_text(self):
        return "SINE" if self.sg["on"] else ""

    # ---------------- 항온수조 ----------------
    def bath_power(self):
        self.bath["on"] = not self.bath["on"]
        self.bath["setmode"] = False
        self.bench.refresh()

    def bath_set(self):
        if self.bath["on"]:
            self.bath["setmode"] = not self.bath["setmode"]
        self.bench.refresh()

    def bath_inc(self, d):
        if self.bath["on"] and self.bath["setmode"]:
            self.bath["sp"] = max(25.0, min(90.0, self.bath["sp"] + d))
        self.bench.refresh()

    def bath_text(self):
        if not self.bath["on"]:
            return ""
        if "water" not in self.placed["C"]:
            return "---"
        v = self.bath["sp"] if self.bath["setmode"] else self.bath["tw"]
        return "%.1f" % v

    def bath_note(self):
        P = self.placed["C"]
        t = []
        if self.bath["on"] and "water" not in P:
            t.append(T("경고: 가열부가 물로 덮여 있지 않아 가열이 차단되었습니다.",
                       "Warning: heater not covered by water — heating disabled."))
        if "submerge" in P:
            t.append(T("비닐봉지가 물속에 잠겨 있습니다.", "Bag is submerged."))
        t.append(self.plate_state_text())
        return "\n".join(x for x in t if x)

    # ---------------- 회로 전류 ----------------
    def circuit_current(self):
        s, P = self.setup, self.placed[self.setup]
        if not self.sg["on"]:
            return 0.0
        v = self.sg_rms()
        f = self.sg["f"]
        if s == "B":
            need = ("siggen", "dmm", "plate", "cabg", "cabd")
            if not all(k in P for k in need):
                return 0.0
            clip = "M" if "clipM" in P else ("L" if "clipL" in P else
                                             ("R" if "clipR" in P else None))
            if clip is None:
                return 0.0
            pl = self.plate_of("B")
            return pl.current_A(f, v, clip, temp=pl.temp)
        if s in ("D1", "D2", "E"):
            need = ["box", "pztt", "pzts", "cabg", "cabd", "siggen", "dmm", "eraser"]
            if s in ("D1", "D2"):
                need.append("rod")
            if not all(k in P for k in need):
                return 0.0
            cf = 1.0 if ("spring" in P or s == "E") else 0.45
            return self.session.sensor_uA(f, s, vrms=v, contact=cf) * 1e-6
        return 0.0


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
