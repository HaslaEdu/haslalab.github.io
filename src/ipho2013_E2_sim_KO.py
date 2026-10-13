#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  44th International Physics Olympiad  (IPhO 2013, Copenhagen, Denmark)
  Experimental Problem E2 :  SOLAR CELLS
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Only what the real instruments show is displayed: the two multimeters,
    the slot numbers of the box, the dial of the variable resistor and the
    water height read on the tape.  Photocurrents, diode parameters, optimal
    loads and refractive indices are never computed or shown.  Any wiring
    is solved as a real nonlinear circuit (nodal analysis, Newton-Raphson).
    All hidden true parameters are randomised for every session.

    Run:   python3 ipho2013_E2_sim_KO.py   [--seed=N]
"""

import math
import random
import sys
import tkinter as tk
from tkinter import ttk, messagebox

# --------------------------------------------------------------------------
# language
# --------------------------------------------------------------------------
LANG = "ko"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


E_CHG = 1.602e-19
K_B = 1.381e-23
N_ACRYLIC = 1.491


# ==========================================================================
#  비선형 회로 해석 (절점 해석 + Newton-Raphson)
# ==========================================================================
class Circuit:
    """단위: 전류 mA, 전압 V, 컨덕턴스 mA/V."""

    def __init__(self):
        self.terminals = set()
        self.wires = []
        self.elems = []          # dict

    def add_terminal(self, name):
        self.terminals.add(name)

    def wire(self, a, b):
        self.wires.append((a, b))

    def add_resistor(self, a, b, ohm, tag=None):
        self.terminals.update((a, b))
        self.elems.append(dict(t="R", a=a, b=b, G=1000.0 / max(ohm, 1e-6), tag=tag,
                               R=ohm))

    def add_cell(self, a, b, iph, i0, beta, tag=None):
        """a = + 단자."""
        self.terminals.update((a, b))
        self.elems.append(dict(t="C", a=a, b=b, iph=iph, i0=i0, beta=beta, tag=tag))

    # ------------------------------------------------------------------
    def solve(self):
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        for t in self.terminals:
            find(t)
        for a, b in self.wires:
            if a in self.terminals and b in self.terminals:
                union(a, b)
        roots = sorted({find(t) for t in self.terminals})
        idx = {r: i for i, r in enumerate(roots)}
        N = len(roots)
        if N == 0:
            return {}, {}

        def nd(t):
            return idx[find(t)]

        v = [0.0] * N
        GMIN = 1e-9
        for _ in range(300):
            F = [0.0] * N
            J = [[0.0] * N for _ in range(N)]
            for e in self.elems:
                p, q = nd(e["a"]), nd(e["b"])
                if e["t"] == "R":
                    g = e["G"]
                    i = g * (v[p] - v[q])
                    F[p] += i
                    F[q] -= i
                    J[p][p] += g
                    J[p][q] -= g
                    J[q][q] += g
                    J[q][p] -= g
                else:
                    V = v[p] - v[q]
                    arg = min(e["beta"] * V, 80.0)
                    ex = math.exp(arg)
                    iout = e["iph"] - e["i0"] * (ex - 1.0)
                    g = e["i0"] * e["beta"] * ex
                    F[p] += -iout
                    F[q] += iout
                    J[p][p] += g
                    J[p][q] -= g
                    J[q][q] += g
                    J[q][p] -= g
            for i in range(N):
                F[i] += GMIN * v[i]
                J[i][i] += GMIN
            # 기준 절점 0
            n = N - 1
            if n == 0:
                break
            A = [[J[i + 1][j + 1] for j in range(n)] + [-F[i + 1]] for i in range(n)]
            dv = _gauss(A, n)
            if dv is None:
                break
            mx = 0.0
            for i in range(n):
                d = max(-0.08, min(0.08, dv[i]))
                v[i + 1] += d
                mx = max(mx, abs(d))
            if mx < 1e-11:
                break
        volt = {t: v[nd(t)] for t in self.terminals}
        cur = {}
        for e in self.elems:
            if e.get("tag"):
                p, q = nd(e["a"]), nd(e["b"])
                if e["t"] == "R":
                    cur[e["tag"]] = e["G"] * (v[p] - v[q])
                else:
                    V = v[p] - v[q]
                    arg = min(e["beta"] * V, 80.0)
                    cur[e["tag"]] = e["iph"] - e["i0"] * (math.exp(arg) - 1.0)
        return volt, cur


def _gauss(A, n):
    for c in range(n):
        piv, pv = c, abs(A[c][c])
        for r in range(c + 1, n):
            if abs(A[r][c]) > pv:
                piv, pv = r, abs(A[r][c])
        if pv < 1e-18:
            return None
        A[c], A[piv] = A[piv], A[c]
        d = A[c][c]
        for j in range(c, n + 1):
            A[c][j] /= d
        for r in range(n):
            if r != c and A[r][c] != 0.0:
                f = A[r][c]
                for j in range(c, n + 1):
                    A[r][j] -= f * A[c][j]
    return [A[i][n] for i in range(n)]


# ==========================================================================
#  물리 엔진
# ==========================================================================
class E2Physics:
    SLOT_PITCH = 5.5        # mm
    SLOT_OFFSET = -7.5      # r[mm] = 5.5*(slot_cell - slot_lamp) - 7.5
    N_SLOTS = 21

    def __init__(self, seed=None):
        self.seed = seed if seed is not None else random.randrange(1, 10 ** 9)
        r = random.Random(self.seed)
        self.rng = r

        # ---- 조명 -------------------------------------------------------
        self.a = 35.0 * (1 + r.uniform(-0.03, 0.03))        # 유효 원판 반지름 mm
        self.S_open = 95.2 * (1 + r.uniform(-0.04, 0.04))   # 구멍판 없을 때 [mA]
        self.f_ap = 0.0704 * (1 + r.uniform(-0.03, 0.03))   # 원형 구멍판 투과
        self.f_off = 0.9672 * (1 + r.uniform(-0.01, 0.01))  # 2개용 거치대 off-axis

        # ---- 태양 전지 --------------------------------------------------
        T0 = 300.0
        self.Tk = T0
        beta0 = E_CHG / (K_B * T0)
        self.eta_A = 1.850 * (1 + r.uniform(-0.03, 0.03))
        self.eta_B = 1.850 * (1 + r.uniform(-0.03, 0.03))
        self.beta_A = beta0 / self.eta_A
        self.beta_B = beta0 / self.eta_B
        self.I0_A = 4.5e-4 * (1 + r.uniform(-0.12, 0.12))   # mA
        self.I0_B = 8.7e-4 * (1 + r.uniform(-0.12, 0.12))   # mA
        self.resp_A = 1.0
        self.resp_B = 0.9915 * (1 + r.uniform(-0.004, 0.004))
        self.leak_A = 0.0225 * (1 + r.uniform(-0.15, 0.15))
        self.leak_B = 0.0508 * (1 + r.uniform(-0.15, 0.15))

        # ---- 광학 용기 (큰 큐벳) ----------------------------------------
        self.n_w = 1.3317 + r.uniform(-0.0012, 0.0012)
        self.b_w = 26.0                 # 물 두께 (빔 방향)
        self.t_wall = 2.5
        self.gap = 3.0
        self.z_ax = 46.5                # 광축 높이 (용기 내부 바닥 기준)
        self.v_top = 78.0               # 내부 높이
        self.RL = 18.0                  # LED 원판 반지름
        self.rho = 4.0                  # 구멍판 반지름
        self.d_ap = 7.0                 # 구멍판+거치대 유효 깊이 (각도 수용한계)
        self._vcache = {}

        # ---- 가변 저항 --------------------------------------------------
        self.R_min = 0.30
        self.R_max = 100.0

    # ------------------------------------------------------------------
    def slot_r(self, slot_lamp, slot_cell):
        return max(2.0, self.SLOT_PITCH * (slot_cell - slot_lamp) + self.SLOT_OFFSET)

    def G(self, r):
        return 1.0 / (1.0 + (r * r) / (self.a * self.a))

    def vignette(self, r):
        """근거리(수 mm~20 mm)에서 구멍판 두께에 의한 비네팅.
        공식 해답의 slot 3,4 편차를 재현한다."""
        return 1.0 - 0.25 * math.exp(-(r / 12.0) ** 2)

    def accept(self, tan_th):
        """깊이 d_ap, 반지름 rho 인 구멍을 기울기 tan_th 로 지나갈 때
        살아남는 단면 비율 (두 원의 겹침 넓이)."""
        u = self.d_ap * abs(tan_th)
        if u >= 2.0 * self.rho:
            return 0.0
        x = u / (2.0 * self.rho)
        return (2.0 / math.pi) * (math.acos(x) - x * math.sqrt(max(0.0, 1.0 - x * x)))

    # ------------------------------------------------------------------
    def vessel_mult(self, r, h):
        """용기(+수위 h[mm])가 있을 때 / 없을 때 광전류 비."""
        key = (round(r, 1), round(h, 1))
        if key in self._vcache:
            return self._vcache[key]
        b, t, gap = self.b_w, self.t_wall, self.gap
        xf = r - gap - t - b
        xb = r - gap - t
        if xf < 3.0:
            self._vcache[key] = None
            return None
        nw, nac = self.n_w, N_ACRYLIC
        Rac = ((nac - 1.0) / (nac + 1.0)) ** 2
        Racw = ((nac - nw) / (nac + nw)) ** 2
        T_dry = (1 - Rac) ** 4
        T_wet = (1 - Rac) ** 2 * (1 - Racw) ** 2
        r_dry = r - 2 * t * (1 - 1 / nac)
        r_wet = r_dry - b * (1 - 1 / nw)
        fL, fB = xf / r, xb / r
        zax, RL, rho = self.z_ax, self.RL, self.rho
        # 수면(아래에서)에서 전반사가 일어나기 위한 공기 중 기울기 한계.
        # 수직 벽면에서 한 번 굴절되므로  sin a_air < sqrt(n²-1) 이 조건이 된다.
        n2 = nw * nw
        m_max = math.sqrt((n2 - 1.0) / (2.0 - n2)) if n2 < 2.0 else 1e9
        NL, NA = 41, 9
        wet = dry = tir = 0.0
        totw = 0.0
        for i in range(NL):
            dL = -RL + 2 * RL * i / (NL - 1)
            zL = zax + dL
            for j in range(NA):
                dA = -rho + 2 * rho * j / (NA - 1)
                zA = zax + dA
                w = self._led_weight((zA - zL) / r)
                totw += w
                z1 = zL + (zA - zL) * fL
                z2 = zL + (zA - zL) * fB
                lo, hi = (z1, z2) if z1 < z2 else (z2, z1)
                if h >= hi:
                    wet += w
                elif h <= lo:
                    dry += w
                # else: 수면을 가로지르는 광선 -> 스침각 굴절으로 소실
                den = 2 * h - zA - zL
                if zL < h < self.v_top and abs(den) > 1e-9:
                    s = (h - zL) / den
                    if fL <= s <= fB and abs(den / r) < m_max:
                        tir += self._led_weight(den / r)
        g0 = self.G(r)
        val = ((wet / totw) * T_wet * self.G(r_wet)
               + (dry / totw) * T_dry * self.G(r_dry)
               + (tir / totw) * T_wet * self.G(r_wet)) / g0
        self._vcache[key] = val
        return val

    def _led_weight(self, m):
        """광선 한 가닥이 구멍을 통과해 전지에 닿는 상대 세기.  m = tan a.

        램버시안 방출 cos a  ×  구멍판 사입사 cos a  ×  1/L²  =  (r/L)^4,
        여기에 두께 d_ap 인 구멍의 각도 수용률을 곱한다.
        """
        c2 = 1.0 / (1.0 + m * m)            # cos² a
        return c2 * c2 * self.accept(m)

    # ------------------------------------------------------------------
    def photocurrent(self, cell, st):
        """st : 벤치 상태 dict."""
        if not st["lamp_on"]:
            return 0.0
        r = self.slot_r(st["slot_lamp"], st["slot_holder"])
        base = self.S_open * self.G(r) * self.vignette(r)
        if st["aperture"]:
            base *= self.f_ap
        if st["holder"] == "dual":
            base *= self.f_off
        if st["vessel"]:
            m = self.vessel_mult(r, st["water_h"])
            if m is None:
                return 0.0
            base *= m
        base *= self.resp_A if cell == "A" else self.resp_B
        if st["shield"] == cell:
            base *= self.leak_A if cell == "A" else self.leak_B
        return base


# ==========================================================================
#  멀티미터
# ==========================================================================
DMM_MODES = [
    ("OFF", None, 0.0),
    ("A 200 uA", "I", 0.2),
    ("A 2 mA", "I", 2.0),
    ("A 20 mA", "I", 20.0),
    ("A 200 mA", "I", 200.0),
    ("V 200 mV", "V", 0.2),
    ("V 2 V", "V", 2.0),
    ("V 20 V", "V", 20.0),
]


def dmm_resistance(mode):
    name, kind, fs = mode
    if kind == "I":
        return 0.2 / (fs / 1000.0)      # 최대 200 mV 부담전압
    if kind == "V":
        return 1.0e7
    return None


def dmm_format(value, mode, rng):
    name, kind, fs = mode
    if kind is None:
        return ""
    res = fs / 2000.0
    val = value + rng.gauss(0.0, res * 0.35)
    if abs(val) > fs * 1.0999:
        return "1"
    q = round(val / res) * res
    dec = max(0, int(round(-math.log10(res)))) if res < 1 else 0
    return ("%." + str(dec) + "f") % q


# ==========================================================================
#  2D 장비 그리기
# ==========================================================================
BOXC = "#151515"
CELLC = "#20242b"
YEL = "#f2d14a"


def draw_cell(cv, x, y, tag, s=1.0, letter="A", shielded=False):
    w, h = 34 * s, 44 * s
    cv.create_rectangle(x - w / 2, y - h / 2, x + w / 2, y + h / 2,
                        fill=CELLC, outline="#3a3f47", width=2, tags=tag)
    for i in range(6):
        cv.create_line(x - w / 2 + 3, y - h / 2 + 5 + i * 6 * s,
                       x + w / 2 - 3, y - h / 2 + 5 + i * 6 * s,
                       fill="#454b55", tags=tag)
    cv.create_text(x, y + h / 2 + 8 * s, text=letter,
                   font=("Helvetica", int(9 * s), "bold"), tags=tag)
    if shielded:
        cv.create_rectangle(x - w / 2 - 3, y - h / 2 - 3, x + w / 2 + 3,
                            y + h / 2 + 3, fill="#0b0b0b", outline="#000",
                            stipple="gray50", tags=tag)


def draw_lamp(cv, x, y, tag, s=1.0, on=True):
    cv.create_polygon(x - 18 * s, y, x + 4 * s, y - 26 * s, x + 4 * s, y + 26 * s,
                      fill="#4a7fb5", outline="#2d5580", width=2, tags=tag)
    for i in range(7):
        cv.create_oval(x + 2 * s, y - 24 * s + i * 8 * s,
                       x + 10 * s, y - 16 * s + i * 8 * s,
                       fill=(YEL if on else "#9a9a9a"), outline="#8a7a20", tags=tag)


def draw_holder(cv, x, y, tag, s=1.0, dual=False):
    if dual:
        cv.create_polygon(x - 10 * s, y - 44 * s, x + 10 * s, y - 44 * s,
                          x + 10 * s, y + 44 * s, x - 10 * s, y + 44 * s,
                          fill="#22262c", outline="#3c414a", width=2, tags=tag)
    else:
        cv.create_polygon(x - 10 * s, y - 26 * s, x + 10 * s, y - 26 * s,
                          x + 10 * s, y + 26 * s, x - 10 * s, y + 26 * s,
                          fill="#22262c", outline="#3c414a", width=2, tags=tag)


def draw_aperture(cv, x, y, tag, s=1.0):
    cv.create_rectangle(x - 5 * s, y - 34 * s, x + 5 * s, y + 34 * s,
                        fill="#101010", outline="#333", width=2, tags=tag)
    cv.create_oval(x - 4 * s, y - 4 * s, x + 4 * s, y + 4 * s,
                   fill="#f5f5f5", outline="", tags=tag)


def draw_shield(cv, x, y, tag, s=1.0):
    cv.create_rectangle(x - 6 * s, y - 34 * s, x + 6 * s, y + 34 * s,
                        fill="#0d0d0d", outline="#2a2a2a", width=2, tags=tag)


def draw_resistor(cv, x, y, tag, s=1.0):
    cv.create_oval(x - 14 * s, y - 14 * s, x + 14 * s, y + 14 * s,
                   fill="#b9bcc0", outline="#7d8084", width=2, tags=tag)
    cv.create_rectangle(x + 12 * s, y - 4 * s, x + 44 * s, y + 4 * s,
                        fill="#a0a4a8", outline="#7d8084", tags=tag)


def draw_dmm(cv, x, y, tag, s=1.0, text="", mode=""):
    w, h = 74 * s, 128 * s
    cv.create_rectangle(x - w / 2, y - h / 2, x + w / 2, y + h / 2,
                        fill="#f0a81e", outline="#b57c10", width=3, tags=tag)
    cv.create_rectangle(x - w / 2 + 6, y - h / 2 + 6, x + w / 2 - 6, y + h / 2 - 6,
                        fill="#2b2b2b", outline="#111", tags=tag)
    cv.create_rectangle(x - w / 2 + 12, y - h / 2 + 12, x + w / 2 - 12,
                        y - h / 2 + 42, fill="#9fb08c", outline="#556", tags=tag)
    cv.create_text(x, y - h / 2 + 27, text=text, font=("Courier", int(12 * s), "bold"),
                   fill="#111", tags=tag)
    cv.create_oval(x - 22 * s, y - 16 * s, x + 22 * s, y + 28 * s,
                   fill="#1a1a1a", outline="#555", width=2, tags=tag)
    cv.create_text(x, y + 6 * s, text=mode, fill="#ddd",
                   font=("Helvetica", int(6 * s)), tags=tag)
    cv.create_text(x, y + h / 2 - 14, text="2286", fill="#ddd",
                   font=("Helvetica", int(8 * s), "bold"), tags=tag)


def draw_box_top(cv, x, y, tag, s=1.0):
    cv.create_rectangle(x - 150 * s, y - 80 * s, x + 150 * s, y + 80 * s,
                        fill=BOXC, outline="#000", width=2, tags=tag)


def draw_cuvette(cv, x, y, tag, s=1.0, frac=0.0):
    cv.create_rectangle(x - 13 * s, y - 40 * s, x + 13 * s, y + 40 * s,
                        fill="#dceaf2", outline="#8fb4c6", width=2, tags=tag)
    if frac > 0:
        cv.create_rectangle(x - 11 * s, y + 40 * s - 78 * s * frac,
                            x + 11 * s, y + 38 * s, fill="#9dc9e8",
                            outline="", tags=tag)


def draw_psu(cv, x, y, tag, s=1.0):
    cv.create_rectangle(x - 16 * s, y - 12 * s, x + 16 * s, y + 12 * s,
                        fill="#1c1c1c", outline="#444", width=2, tags=tag)
    cv.create_line(x + 16 * s, y, x + 34 * s, y, fill="#111", width=int(2 * s),
                   tags=tag)


def draw_lid(cv, x, y, tag, s=1.0):
    cv.create_rectangle(x - 40 * s, y - 22 * s, x + 40 * s, y + 22 * s,
                        fill="#111", outline="#333", width=2, tags=tag)


def draw_wireset(cv, x, y, tag, s=1.0):
    for i, c in enumerate(("#c33", "#3a3", "#33c", "#cc3")):
        cv.create_line(x - 22 * s, y - 12 * s + i * 8 * s, x + 22 * s,
                       y - 6 * s + i * 8 * s, fill=c, width=int(2.5 * s),
                       smooth=True, tags=tag)


# ==========================================================================
#  조립 탭
# ==========================================================================
E2_PARTS = [
    ("CELLA", T("A 태양 전지 A", "A Solar cell A"), lambda c, x, y, t, s: draw_cell(c, x, y, t, s, "A")),
    ("CELLB", T("B 태양 전지 B", "B Solar cell B"), lambda c, x, y, t, s: draw_cell(c, x, y, t, s, "B")),
    ("LAMP", T("D LED 광원", "D LED light source"), lambda c, x, y, t, s: draw_lamp(c, x, y, t, s)),
    ("PSU", T("E 전원 공급 장치", "E power supply"), draw_psu),
    ("RES", T("F 가변 저항기", "F variable resistor"), draw_resistor),
    ("HSIN", T("G 단일 거치대", "G single holder"), lambda c, x, y, t, s: draw_holder(c, x, y, t, s, False)),
    ("APER", T("H 원형 구멍판", "H circular aperture"), draw_aperture),
    ("HDUA", T("I 2개용 거치대", "I double holder"), lambda c, x, y, t, s: draw_holder(c, x, y, t, s, True)),
    ("SHLD", T("J 차폐판", "J shielding plate"), draw_shield),
    ("DMM1", T("K 멀티미터 1", "K multimeter 1"), lambda c, x, y, t, s: draw_dmm(c, x, y, t, s)),
    ("DMM2", T("L 멀티미터 2", "L multimeter 2"), lambda c, x, y, t, s: draw_dmm(c, x, y, t, s)),
    ("WIRE", T("M 악어클립 도선", "M clip leads"), draw_wireset),
    ("CUV", T("N 광학 용기", "N optical vessel"), lambda c, x, y, t, s: draw_cuvette(c, x, y, t, s)),
    ("LID", T("V 상자 뚜껑", "V box lid"), draw_lid),
]

E2_ZONES = [
    dict(key="Z_RES", part="RES", x=300, y=470, label=T("상자 측면 · 가변 저항기", "Box side · variable resistor")),
    dict(key="Z_LAMP", part="LAMP", x=250, y=110, label=T("U자형 거치대 · 광원", "U-holder · light source")),
    dict(key="Z_PSU", part="PSU", x=390, y=110, label=T("광원 · 전원 공급 장치", "Light source · power supply")),
    dict(key="Z_HSIN", part="HSIN", x=250, y=240, label=T("상자 슬롯 · 단일 거치대", "Box slot · single holder")),
    dict(key="Z_HDUA", part="HDUA", x=390, y=240, label=T("상자 슬롯 · 2개용 거치대", "Box slot · double holder")),
    dict(key="Z_CA", part="CELLA", x=530, y=240, label=T("거치대 · 전지 A", "Holder · cell A")),
    dict(key="Z_CB", part="CELLB", x=660, y=240, label=T("2개용 거치대 · 전지 B", "Double holder · cell B")),
    dict(key="Z_APER", part="APER", x=530, y=350, label=T("전지 바로 앞 · 구멍판", "In front of cell · aperture")),
    dict(key="Z_CUV", part="CUV", x=660, y=350, label=T("구멍판 앞 · 광학 용기", "Before aperture · vessel")),
    dict(key="Z_D1", part="DMM1", x=810, y=130, label=T("멀티미터 1 배치", "Place multimeter 1")),
    dict(key="Z_D2", part="DMM2", x=810, y=290, label=T("멀티미터 2 배치", "Place multimeter 2")),
    dict(key="Z_WIRE", part="WIRE", x=810, y=430, label=T("도선 꺼내기", "Take out leads")),
    dict(key="Z_LID", part="LID", x=465, y=478, label=T("상자 뚜껑 덮기(선택)", "Box lid (optional)")),
]


class AssemblyE2(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.state = {z["key"]: None for z in E2_ZONES}
        self.where = {}
        ttk.Label(self, text=T("장비를 끌어다 조립하시오. 오른쪽 버튼으로 분리.",
                               "Drag equipment into place. Right-click to remove."),
                  font=("Helvetica", 10)).pack(anchor="w", padx=10, pady=(8, 2))
        self.cv = tk.Canvas(self, width=980, height=560, bg="#f7f7f4",
                            highlightthickness=0)
        self.cv.pack(fill="both", expand=True, padx=8, pady=4)
        self.msg = ttk.Label(self, text="", foreground="#a33")
        self.msg.pack(fill="x", padx=10, pady=(0, 6))
        self.drag = None
        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_move)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Button-3>", self.on_right)
        self.redraw()

    def tray_pos(self, i):
        return 66, 54 + i * 36

    def redraw(self):
        cv = self.cv
        cv.delete("all")
        cv.create_rectangle(6, 6, 130, 554, fill="#ececE6", outline="#cfcfc8")
        cv.create_text(68, 22, text=T("부품함", "Parts tray"),
                       font=("Helvetica", 10, "bold"))
        cv.create_rectangle(140, 6, 974, 554, fill="#fbfbf8", outline="#dedad2")
        draw_box_top(cv, 430, 260, "bg", 1.0)
        cv.create_text(430, 348, text=T("상자 (윗면에서 본 그림)", "the box (top view)"),
                       fill="#777", font=("Helvetica", 8))
        for z in E2_ZONES:
            occ = self.state[z["key"]]
            cv.create_rectangle(z["x"] - 48, z["y"] - 34, z["x"] + 48, z["y"] + 34,
                                dash=(4, 3), width=2,
                                outline="#2f7d4f" if occ else "#b7b2a8")
            cv.create_text(z["x"], z["y"] + 44, text=z["label"], fill="#666",
                           font=("Helvetica", 8))
        for i, (key, label, fn) in enumerate(E2_PARTS):
            zk = self.where.get(key)
            if zk:
                z = [q for q in E2_ZONES if q["key"] == zk][0]
                x, y, sc = z["x"], z["y"], 0.8
            else:
                x, y = self.tray_pos(i)
                sc = 0.38
            fn(cv, x, y, "P_" + key, sc)
            if not zk:
                cv.create_text(x + 30, y, text=label, anchor="w",
                               font=("Helvetica", 7), fill="#333")
        cv.create_text(560, 542, text=self.status(), fill="#2f7d4f",
                       font=("Helvetica", 9, "bold"))

    def status(self):
        s = self.state
        out = []
        if s["Z_LAMP"] and s["Z_PSU"]:
            out.append(T("광원 준비", "light source ready"))
        if s["Z_HSIN"] and s["Z_CA"]:
            out.append(T("단일 전지 배치", "single-cell layout"))
        if s["Z_HDUA"] and s["Z_CA"] and s["Z_CB"]:
            out.append(T("2전지 배치", "two-cell layout"))
        if s["Z_D1"] and s["Z_D2"] and s["Z_WIRE"]:
            out.append(T("계측기 준비", "meters ready"))
        return "   |   ".join(out) if out else T("(조립 진행 중)", "(assembling)")

    def say(self, m, err=True):
        self.msg.config(text=m, foreground="#a33" if err else "#2f7d4f")

    # ---------------- drag and drop --------------------------------
    def on_press(self, e):
        for it in reversed(self.cv.find_overlapping(e.x - 2, e.y - 2, e.x + 2, e.y + 2)):
            for t in self.cv.gettags(it):
                if t.startswith("P_"):
                    self.drag = dict(key=t[2:], tag=t, x=e.x, y=e.y)
                    self.cv.tag_raise(t)
                    return

    def on_move(self, e):
        if self.drag:
            self.cv.move(self.drag["tag"], e.x - self.drag["x"], e.y - self.drag["y"])
            self.drag["x"], self.drag["y"] = e.x, e.y

    def on_release(self, e):
        if not self.drag:
            return
        key = self.drag["key"]
        self.drag = None
        tgt = None
        for z in E2_ZONES:
            if abs(e.x - z["x"]) < 52 and abs(e.y - z["y"]) < 38:
                tgt = z
                break
        if tgt is None:
            if self.where.get(key):
                zk = self.where.pop(key)
                self.state[zk] = None
                self.say(T("부품함으로 되돌렸다.", "Returned to tray."), False)
            self.redraw()
            self.app.sync()
            return
        ok, why = self.check(key, tgt)
        if not ok:
            self.say(why)
            self.redraw()
            return
        old = self.where.get(key)
        if old:
            self.state[old] = None
        self.state[tgt["key"]] = key
        self.where[key] = tgt["key"]
        self.say(T("설치: ", "Installed: ") + tgt["label"], False)
        self.redraw()
        self.app.sync()

    def on_right(self, e):
        for z in E2_ZONES:
            if abs(e.x - z["x"]) < 52 and abs(e.y - z["y"]) < 38 and self.state[z["key"]]:
                dep = {"Z_LAMP": "Z_PSU", "Z_HSIN": "Z_CA", "Z_HDUA": "Z_CB",
                       "Z_APER": "Z_CUV"}
                d = dep.get(z["key"])
                if d and self.state[d]:
                    self.say(T("그 위/앞의 부품을 먼저 분리하라.",
                               "Remove the dependent part first."))
                    return
                if z["key"] == "Z_HDUA" and self.state["Z_CA"] and \
                        self.holder_kind() == "dual":
                    self.say(T("그 위/앞의 부품을 먼저 분리하라.",
                               "Remove the dependent part first."))
                    return
                k = self.state[z["key"]]
                self.state[z["key"]] = None
                self.where.pop(k, None)
                self.say(T("분리했다.", "Removed."), False)
                self.redraw()
                self.app.sync()
                return

    def holder_kind(self):
        if self.state["Z_HDUA"]:
            return "dual"
        if self.state["Z_HSIN"]:
            return "single"
        return None

    def check(self, part, zone):
        if zone["part"] != part:
            return False, T("이 자리에 들어갈 부품이 아니다: ",
                            "Wrong place for this part: ") + zone["label"]
        if self.state[zone["key"]] not in (None, part):
            return False, T("이미 다른 부품이 있다.", "Already occupied.")
        s, k = self.state, zone["key"]
        if k == "Z_PSU" and not s["Z_LAMP"]:
            return False, T("먼저 광원을 U자형 거치대에 장착하라.",
                            "Mount the light source in the U-holder first.")
        if k in ("Z_HSIN", "Z_HDUA"):
            other = "Z_HDUA" if k == "Z_HSIN" else "Z_HSIN"
            if s[other]:
                return False, T("두 거치대를 동시에 쓸 수 없다. 먼저 분리하라.",
                                "Only one holder at a time — remove the other.")
        if k == "Z_CA" and not (s["Z_HSIN"] or s["Z_HDUA"]):
            return False, T("먼저 거치대를 상자에 장착하라.",
                            "Mount a holder in the box first.")
        if k == "Z_CB" and not s["Z_HDUA"]:
            return False, T("전지 B 는 2개용 거치대에만 넣을 수 있다.",
                            "Cell B needs the double holder.")
        if k == "Z_APER" and not s["Z_CA"]:
            return False, T("전지를 먼저 거치대에 넣어야 한다.",
                            "Put a solar cell into the holder first.")
        if k == "Z_CUV" and not s["Z_APER"]:
            return False, T("원형 구멍판을 먼저 배치하라.",
                            "Place the circular aperture first.")
        return True, None


# ==========================================================================
#  실험대 탭
# ==========================================================================
TERMINALS = {
    "A+": (150, 60, "A +"), "A-": (150, 108, "A −"),
    "B+": (150, 196, "B +"), "B-": (150, 244, "B −"),
    "R1": (330, 60, "R 1"), "R2": (330, 130, "R 2"),
    "M1I": (500, 60, "IN"), "M1C": (500, 108, "COM"),
    "M2I": (500, 196, "IN"), "M2C": (500, 244, "COM"),
}


class BenchE2(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.p = app.phys
        self.wires = []
        self.sel = None
        self.st = dict(slot_lamp=0, slot_holder=10, aperture=False, holder=None,
                       shield="none", vessel=False, water_h=0.0, lamp_on=False,
                       R=20.0)
        self.mode1 = DMM_MODES[0]
        self.mode2 = DMM_MODES[0]

        left = ttk.Frame(self)
        left.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.cv = tk.Canvas(left, width=620, height=250, bg="#f2f4f0",
                            highlightthickness=0)
        self.cv.pack(fill="x")
        ttk.Label(left, text=T("배선판 — 단자를 두 번 눌러 연결, 도선 오른쪽 버튼으로 제거",
                               "Wiring board — click two terminals to connect, "
                               "right-click a lead to remove"),
                  font=("Helvetica", 8)).pack(anchor="w")
        self.wcv = tk.Canvas(left, width=620, height=300, bg="#fbfbf6",
                             highlightthickness=0)
        self.wcv.pack(fill="both", expand=True, pady=4)
        self.wcv.bind("<Button-1>", self.on_wire_click)
        self.wcv.bind("<Button-3>", self.on_wire_right)

        right = ttk.Frame(self, width=370)
        right.pack(side="right", fill="y", padx=6, pady=6)
        right.pack_propagate(False)

        f0 = ttk.LabelFrame(right, text=T("광원 / 배치", "Light source / layout"))
        f0.pack(fill="x", pady=3)
        self.lampbtn = ttk.Button(f0, text=T("광원 켜기 (12 V)", "lamp ON (12 V)"),
                                  command=self.toggle_lamp)
        self.lampbtn.pack(fill="x", padx=6, pady=4)
        g = ttk.Frame(f0)
        g.pack(fill="x", padx=6, pady=2)
        ttk.Label(g, text=T("광원 슬롯", "lamp slot")).grid(row=0, column=0, sticky="w")
        self.sl_lamp = tk.IntVar(value=0)
        ttk.Spinbox(g, from_=0, to=20, width=5, textvariable=self.sl_lamp,
                    command=self.refresh).grid(row=0, column=1, padx=4)
        ttk.Label(g, text=T("거치대 슬롯", "holder slot")).grid(row=1, column=0, sticky="w")
        self.sl_cell = tk.IntVar(value=10)
        ttk.Spinbox(g, from_=0, to=20, width=5, textvariable=self.sl_cell,
                    command=self.refresh).grid(row=1, column=1, padx=4)
        ttk.Label(g, text=T("차폐판", "shielding plate")).grid(row=2, column=0, sticky="w")
        self.shv = tk.StringVar(value="none")
        cb = ttk.Combobox(g, width=7, state="readonly", textvariable=self.shv,
                          values=("none", "A", "B"))
        cb.grid(row=2, column=1, padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        f1 = ttk.LabelFrame(right, text=T("가변 저항기", "Variable resistor"))
        f1.pack(fill="x", pady=3)
        self.rv = tk.DoubleVar(value=50.0)
        ttk.Scale(f1, from_=0, to=100, variable=self.rv,
                  command=lambda e: self.refresh()).pack(fill="x", padx=8, pady=6)
        self.rlab = ttk.Label(f1, text="")
        self.rlab.pack(anchor="w", padx=8)

        f2 = ttk.LabelFrame(right, text=T("멀티미터", "Multimeters"))
        f2.pack(fill="x", pady=3)
        self.d1 = tk.StringVar(value=DMM_MODES[0][0])
        self.d2 = tk.StringVar(value=DMM_MODES[0][0])
        for i, (var, name) in enumerate(((self.d1, T("멀티미터 1", "meter 1")),
                                         (self.d2, T("멀티미터 2", "meter 2")))):
            row = ttk.Frame(f2)
            row.pack(fill="x", padx=6, pady=3)
            ttk.Label(row, text=name, width=11).pack(side="left")
            c = ttk.Combobox(row, width=12, state="readonly", textvariable=var,
                             values=[m[0] for m in DMM_MODES])
            c.pack(side="left")
            c.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        self.dl1 = tk.Label(f2, text="", bg="#9fb08c", font=("Courier", 15, "bold"),
                            width=14, anchor="e", relief="sunken", bd=2)
        self.dl1.pack(fill="x", padx=8, pady=2)
        self.dl2 = tk.Label(f2, text="", bg="#9fb08c", font=("Courier", 15, "bold"),
                            width=14, anchor="e", relief="sunken", bd=2)
        self.dl2.pack(fill="x", padx=8, pady=2)

        f3 = ttk.LabelFrame(right, text=T("광학 용기의 물", "Water in the vessel"))
        f3.pack(fill="x", pady=3)
        self.wv = tk.DoubleVar(value=0.0)
        ttk.Scale(f3, from_=0, to=76, variable=self.wv,
                  command=lambda e: self.refresh()).pack(fill="x", padx=8, pady=4)
        self.wlab = ttk.Label(f3, text="")
        self.wlab.pack(anchor="w", padx=8, pady=(0, 4))

        f4 = ttk.LabelFrame(right, text=T("측정 기록", "Measurement log"))
        f4.pack(fill="both", expand=True, pady=3)
        self.log = tk.Text(f4, height=8, width=44, font=("Courier", 9))
        self.log.pack(fill="both", expand=True, padx=4, pady=4)
        bb = ttk.Frame(f4)
        bb.pack(fill="x")
        ttk.Button(bb, text=T("현재 값 기록", "record"), command=self.record).pack(
            side="left", padx=4, pady=2)
        ttk.Button(bb, text=T("지우기", "clear"),
                   command=lambda: self.log.delete("1.0", "end")).pack(side="left")

        self.refresh()

    # ------------------------------------------------------------------
    def toggle_lamp(self):
        s = self.app.asm.state
        if not (s["Z_LAMP"] and s["Z_PSU"]):
            messagebox.showwarning("", T("광원과 전원 공급 장치를 먼저 조립하라.",
                                         "Assemble the lamp and power supply first."))
            return
        self.st["lamp_on"] = not self.st["lamp_on"]
        self.refresh()

    def collect_state(self):
        a = self.app.asm.state
        self.st["slot_lamp"] = self.sl_lamp.get()
        self.st["slot_holder"] = self.sl_cell.get()
        self.st["aperture"] = bool(a["Z_APER"])
        self.st["holder"] = self.app.asm.holder_kind()
        self.st["shield"] = self.shv.get()
        self.st["vessel"] = bool(a["Z_CUV"])
        self.st["water_h"] = float(self.wv.get())
        self.st["R"] = self.p.R_min + (self.p.R_max - self.p.R_min) * \
            (self.rv.get() / 100.0) ** 1.6
        if not (a["Z_LAMP"] and a["Z_PSU"]):
            self.st["lamp_on"] = False
        return self.st

    # ------------------------------------------------------------------
    def build_circuit(self):
        a = self.app.asm.state
        st = self.collect_state()
        c = Circuit()
        for t in TERMINALS:
            c.add_terminal(t)
        if a["Z_CA"]:
            iph = self.p.photocurrent("A", st)
            c.add_cell("A+", "A-", iph, self.p.I0_A, self.p.beta_A, tag="cellA")
        if a["Z_CB"]:
            iph = self.p.photocurrent("B", st)
            c.add_cell("B+", "B-", iph, self.p.I0_B, self.p.beta_B, tag="cellB")
        if a["Z_RES"]:
            c.add_resistor("R1", "R2", st["R"], tag="R")
        m1 = [m for m in DMM_MODES if m[0] == self.d1.get()][0]
        m2 = [m for m in DMM_MODES if m[0] == self.d2.get()][0]
        self.mode1, self.mode2 = m1, m2
        if a["Z_D1"] and m1[1]:
            c.add_resistor("M1I", "M1C", dmm_resistance(m1), tag="m1")
        if a["Z_D2"] and m2[1]:
            c.add_resistor("M2I", "M2C", dmm_resistance(m2), tag="m2")
        for w in self.wires:
            c.wire(*w)
        return c, m1, m2

    def readings(self):
        a = self.app.asm.state
        if not a["Z_WIRE"]:
            return "", "", None
        c, m1, m2 = self.build_circuit()
        volt, cur = c.solve()
        out = []
        for tag, mode, present in (("m1", m1, a["Z_D1"]), ("m2", m2, a["Z_D2"])):
            if not present or mode[1] is None:
                out.append("")
                continue
            if mode[1] == "I":
                val = cur.get(tag, 0.0)
            else:
                ia = "M1I" if tag == "m1" else "M2I"
                ic = "M1C" if tag == "m1" else "M2C"
                val = volt.get(ia, 0.0) - volt.get(ic, 0.0)
            out.append(dmm_format(val, mode, self.p.rng))
        return out[0], out[1], (volt, cur)

    # ------------------------------------------------------------------
    def refresh(self):
        st = self.collect_state()
        self.rlab.config(text=T("저항 눈금", "dial") + "  %5.1f %%" % self.rv.get())
        self.wlab.config(text=T("용기 물높이 h", "water height h")
                         + "  %.0f mm" % st["water_h"])
        self.lampbtn.config(text=(T("광원 끄기", "lamp OFF") if st["lamp_on"]
                                  else T("광원 켜기 (12 V)", "lamp ON (12 V)")))
        r1, r2, _ = self.readings()
        self.dl1.config(text=r1 if r1 else ("" if self.d1.get() == "OFF" else "----"))
        self.dl2.config(text=r2 if r2 else ("" if self.d2.get() == "OFF" else "----"))
        self.draw_scene()
        self.draw_wiring()

    def record(self):
        r1, r2, _ = self.readings()
        st = self.st
        self.log.insert("end", "slot(L=%2d,C=%2d) %s  h=%2.0f  M1=%-9s M2=%-9s\n"
                        % (st["slot_lamp"], st["slot_holder"],
                           ("ap" if st["aperture"] else "--"),
                           st["water_h"], r1 or "-", r2 or "-"))
        self.log.see("end")

    # ------------------------------------------------------------------
    def draw_scene(self):
        cv = self.cv
        cv.delete("all")
        a = self.app.asm.state
        st = self.st
        cv.create_rectangle(20, 30, 600, 220, fill=BOXC, outline="#000", width=2)
        cv.create_text(310, 16, text=T("상자 내부 (윗면에서 본 그림)",
                                       "inside the box (top view)"),
                       fill="#555", font=("Helvetica", 8))
        x0, dx = 45, 26.5
        for i in range(21):
            x = x0 + i * dx
            cv.create_line(x, 40, x, 210, fill="#2c2c2c")
            if i % 5 == 0:
                cv.create_text(x, 216, text=str(i), fill="#888",
                               font=("Helvetica", 7))
        if a["Z_LAMP"]:
            draw_lamp(cv, x0 + st["slot_lamp"] * dx, 125, "lamp", 0.9,
                      on=st["lamp_on"])
        hx = x0 + st["slot_holder"] * dx
        kind = self.app.asm.holder_kind()
        if kind:
            draw_holder(cv, hx, 125, "hold", 0.9, dual=(kind == "dual"))
        if a["Z_CA"]:
            yy = 125 if kind == "single" else 160
            draw_cell(cv, hx, yy, "cA", 0.75, "A", shielded=(st["shield"] == "A"))
        if a["Z_CB"]:
            draw_cell(cv, hx, 90, "cB", 0.75, "B", shielded=(st["shield"] == "B"))
        if a["Z_APER"]:
            draw_aperture(cv, hx - 14, 125, "ap", 0.8)
        if a["Z_CUV"]:
            draw_cuvette(cv, hx - 40, 125, "cuv", 0.9,
                         frac=st["water_h"] / 78.0)
        if a["Z_RES"]:
            draw_resistor(cv, 578, 125, "res", 0.8)
        if st["lamp_on"] and a["Z_LAMP"]:
            lx = x0 + st["slot_lamp"] * dx
            for yy in (95, 125, 155):
                cv.create_line(lx + 10, yy, hx - 18, 125, fill="#f6e08a",
                               width=1, dash=(3, 3))

    def draw_wiring(self):
        cv = self.wcv
        cv.delete("all")
        a = self.app.asm.state
        if not a["Z_WIRE"]:
            cv.create_text(310, 150, text=T("도선을 부품함에서 꺼내시오.",
                                            "Take the clip leads out first."),
                           fill="#a33", font=("Helvetica", 11))
            return
        # 소자 상자
        def blk(x0, y0, x1, y1, label, present):
            cv.create_rectangle(x0, y0, x1, y1,
                                fill="#ffffff" if present else "#eeeeea",
                                outline="#999", width=2)
            cv.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=label,
                           font=("Helvetica", 10, "bold"),
                           fill="#222" if present else "#aaa")
        blk(60, 40, 140, 128, "A", bool(a["Z_CA"]))
        blk(60, 176, 140, 264, "B", bool(a["Z_CB"]))
        blk(300, 44, 360, 146, "R", bool(a["Z_RES"]))
        blk(520, 40, 600, 128, "M1", bool(a["Z_D1"]))
        blk(520, 176, 600, 264, "M2", bool(a["Z_D2"]))
        for w in self.wires:
            (x1, y1, _), (x2, y2, _) = TERMINALS[w[0]], TERMINALS[w[1]]
            cv.create_line(x1, y1, (x1 + x2) / 2, min(y1, y2) - 22, x2, y2,
                           smooth=True, width=3, fill="#c0392b",
                           tags=("W", "W%d" % self.wires.index(w)))
        for name, (x, y, lab) in TERMINALS.items():
            col = "#2f7d4f" if self.sel == name else "#333"
            cv.create_oval(x - 7, y - 7, x + 7, y + 7, fill="#d8d8d0",
                           outline=col, width=3, tags=("TERM", "T_" + name))
            cv.create_text(x - 12, y, text=lab, anchor="e",
                           font=("Helvetica", 8))

    def on_wire_click(self, e):
        if not self.app.asm.state["Z_WIRE"]:
            return
        hit = None
        for name, (x, y, lab) in TERMINALS.items():
            if (e.x - x) ** 2 + (e.y - y) ** 2 < 130:
                hit = name
                break
        if hit is None:
            self.sel = None
        elif self.sel is None:
            self.sel = hit
        elif self.sel == hit:
            self.sel = None
        else:
            pair = (self.sel, hit)
            if pair not in self.wires and (hit, self.sel) not in self.wires:
                self.wires.append(pair)
            self.sel = None
        self.refresh()

    def on_wire_right(self, e):
        for i, w in enumerate(list(self.wires)):
            (x1, y1, _), (x2, y2, _) = TERMINALS[w[0]], TERMINALS[w[1]]
            for t in (0.25, 0.5, 0.75):
                mx = x1 + (x2 - x1) * t
                my = min(y1, y2) - 22 + (abs(y1 - y2)) * abs(t - 0.5)
                if (e.x - mx) ** 2 + (e.y - my) ** 2 < 400:
                    self.wires.pop(i)
                    self.refresh()
                    return
        # 근처 아무 도선
        for i, w in enumerate(list(self.wires)):
            (x1, y1, _), (x2, y2, _) = TERMINALS[w[0]], TERMINALS[w[1]]
            if min(x1, x2) - 20 < e.x < max(x1, x2) + 20 and \
               min(y1, y2) - 40 < e.y < max(y1, y2) + 20:
                self.wires.pop(i)
                self.refresh()
                return


# ==========================================================================
class App(tk.Tk):
    def __init__(self, seed=None):
        super().__init__()
        self.title("IPhO 2013  E2 — " + T("태양 전지", "Solar cells"))
        self.geometry("1010x700")
        self.phys = E2Physics(seed)
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.asm = AssemblyE2(nb, self)
        self.bench = BenchE2(nb, self)
        nb.add(self.asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.bench, text=T(" 실험대 ", " Bench "))
        nb.bind("<<NotebookTabChanged>>", lambda e: self.sync())

    def sync(self):
        try:
            self.bench.refresh()
        except Exception:
            pass


def main():
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
        if a == "--en":
            globals()["LANG"] = "en"
    App(seed).mainloop()


if __name__ == "__main__":
    main()
