# -*- coding: utf-8 -*-
"""
APhO 2025  Experimental Problem 1  —  Physics of Induction Cooking
유도가열 조리기의 물리 · 실험 시뮬레이터

HaslaLab / HaslaEdu
표준 라이브러리(tkinter)만 사용합니다. 외부 패키지 필요 없음.

설계 원칙: 장비가 실제로 주는 것만 준다.
  회귀·기울기·유도된 물리량·채점 기능은 제공하지 않습니다.
"""
import math, cmath, random, time
import tkinter as tk
from tkinter import ttk, font as tkfont

LANG = "KO"          # the EN edition differs only in this line

# =============================================================================
# 1. 물리 엔진
# =============================================================================
MU0 = 4.0e-7 * math.pi
SB = 5.670e-8
T_AMB = 303.5                       # 주위 온도 [K]  (R_NTC0 = 7.86 kΩ)


class Mat:
    def __init__(self, key, sigma, mur, t, alpha, n, ko, en, c1, c2):
        self.key, self.sigma, self.mur, self.t = key, sigma, mur, t
        self.alpha, self.n, self.ko, self.en = alpha, n, ko, en
        self.c1, self.c2 = c1, c2

    @property
    def name(self):
        return self.ko if LANG == "KO" else self.en


# alpha: 판을 우회하는 누설 결합 비율. 자성체(SS410)는 자속이 판 안으로 끌려들어가
#        측면으로 빠져나오므로 크다 → 표피 깊이 측정이 무너진다(공식 해설의 "극단적 표피 깊이").
MAT = {
    "AL":    Mat("AL",    3.70e7, 1,   0.73e-3, 0.005, 5, "알루미늄", "Aluminium", "#d5d9dd", "#9aa1a8"),
    "CU":    Mat("CU",    5.88e7, 1,   0.71e-3, 0.005, 5, "구리", "Copper", "#d98a55", "#a1512a"),
    "SS304": Mat("SS304", 1.39e6, 1,   0.72e-3, 0.005, 4, "스테인리스 304", "Stainless 304", "#c3c8cc", "#7e858c"),
    "SS410": Mat("SS410", 1.70e6, 700, 0.76e-3, 0.55,  4, "스테인리스 410", "Stainless 410", "#cfd6da", "#89939b"),
}


class Pan:
    def __init__(self, key, rho, c, t, e, rload40, ko, en):
        self.key, self.rho, self.c, self.t = key, rho, c, t
        self.e, self.rload40, self.ko, self.en = e, rload40, ko, en
        self.side = 0.02

    @property
    def name(self):
        return self.ko if LANG == "KO" else self.en

    @property
    def area(self):
        return 2 * self.side * self.side          # 양면 복사

    @property
    def mass(self):
        return self.rho * self.side * self.side * self.t


PAN = {
    "AL":    Pan("AL",    2700, 900, 0.73e-3, 0.65, 0.0546, "알루미늄 팬", "Aluminium pan"),
    "SS410": Pan("SS410", 7700, 460, 0.76e-3, 0.80, 0.1377, "SS410 팬", "SS410 pan"),
}

COIL_L, COIL_RL, COIL_M = 47.2e-6, 0.47, 5.79e-6       # Wurth 760308101303
R1_OHM, RCAB, RSCOPE = 1.0, 0.0225, 1.0e6              # 케이블 4개 → R_C = 0.09 Ω
FG_EMAX, FG_RS, FG_ILIM = 32.0, 2.0, 4.0               # 진폭(peak) 최대, 출력 임피던스, 앰프 전류 제한
NTC_R0, NTC_T0, NTC_B = 10000.0, 298.0, 3950.0

CAPS = {                                               # key: (C, ESR, 표기, 필름 여부)
    "C470N":  (470e-9,  0.010, "470 nF",  True),
    "C470U":  (470e-6,  0.030, "470 µF",  False),
    "C1000U": (1000e-6, 0.030, "1000 µF", False),
    "C2200U": (2200e-6, 0.030, "2200 µF", False),
}
CAP_ORDER = ["C470N", "C470U", "C1000U", "C2200U"]

TERMS = ["FGP", "FGN", "R1A", "R1B", "CBA", "CBB", "C1A", "C1B", "C2A", "C2B", "NTCA", "NTCB"]
TIDX = {t: i for i, t in enumerate(TERMS)}


def skin_depth(key, f):
    m = MAT[key]
    return 1.0 / math.sqrt(math.pi * m.sigma * m.mur * MU0 * max(f, 1e-9))


def shielding(stack, f):
    """금속판 더미를 통과한 2차 코일 결합 감쇠 (0~1)."""
    if not stack:
        return 1.0
    d_fringe = 6.0e-3 * (1000.0 / max(f, 1.0)) ** 0.15
    s = sf = 0.0
    alpha = 0.0
    for k in stack:
        m = MAT[k]
        s += m.t / skin_depth(k, f)
        sf += m.t / d_fringe
        alpha = max(alpha, m.alpha)
    return (1 - alpha) * math.exp(-s) + alpha * math.exp(-sf)


def rntc(T):
    return NTC_R0 * math.exp(NTC_B * (1.0 / T - 1.0 / NTC_T0))


def t_from_r(R):
    return 1.0 / (math.log(R / NTC_R0) / NTC_B + 1.0 / NTC_T0)


def rload(pan_key, f):
    return PAN[pan_key].rload40 * math.sqrt(max(f, 1.0) / 40000.0)


def csolve(A, b):
    """복소 선형계 Ax=b (부분 피벗 가우스 소거)."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for k in range(n):
        piv, best = k, abs(M[k][k])
        for i in range(k + 1, n):
            if abs(M[i][k]) > best:
                best, piv = abs(M[i][k]), i
        if best < 1e-300:
            return None
        if piv != k:
            M[k], M[piv] = M[piv], M[k]
        d = M[k][k]
        for j in range(k, n + 1):
            M[k][j] /= d
        for i in range(n):
            if i == k:
                continue
            fct = M[i][k]
            if fct == 0:
                continue
            for j in range(k, n + 1):
                M[i][j] -= fct * M[k][j]
    return [M[i][n] for i in range(n)]


class Solution:
    __slots__ = ("V", "I1", "I2", "IFG")

    def __init__(self, V, I1, I2, IFG):
        self.V, self.I1, self.I2, self.IFG = V, I1, I2, IFG

    def amp(self, t1, t2):
        if not t1 or not t2:
            return 0.0
        return abs(self.V[t1] - self.V[t2])


def analyze(st, f):
    """복소 MNA. st 는 dict: cables, cap, stack, pan, panT, E, scope, dmm, dmmMode."""
    N, gnd = len(TERMS), TIDX["FGN"]
    w = 2 * math.pi * f
    nmap, c = [0] * N, 0
    for i in range(N):
        if i == gnd:
            nmap[i] = -1
        else:
            nmap[i] = c
            c += 1
    nb = 3
    size = (N - 1) + nb
    A = [[0j] * size for _ in range(size)]
    b = [0j] * size

    def at(i, j, v):
        if i >= 0 and j >= 0:
            A[i][j] += v

    def stampY(na, nbb, Y):
        a, bb = nmap[na], nmap[nbb]
        at(a, a, Y); at(bb, bb, Y); at(a, bb, -Y); at(bb, a, -Y)

    def stampR(na, nbb, R):
        if R > 0:
            stampY(na, nbb, 1.0 / R)

    for i in range(N):                      # 수치 안정화 누설 1 nS
        if i != gnd:
            at(nmap[i], nmap[i], 1e-9 + 0j)

    for ca, cb in st["cables"]:
        if ca in TIDX and cb in TIDX:
            stampR(TIDX[ca], TIDX[cb], RCAB)
    stampR(TIDX["R1A"], TIDX["R1B"], R1_OHM)
    if st.get("cap"):
        C, esr, _, _ = CAPS[st["cap"]]
        Z = complex(esr, -1.0 / (w * C))
        stampY(TIDX["CBA"], TIDX["CBB"], 1.0 / Z)
    if st.get("pan"):
        stampR(TIDX["NTCA"], TIDX["NTCB"], rntc(st.get("panT", T_AMB)))
    sc = st.get("scope")
    if sc and sc[0] and sc[1]:
        stampR(TIDX[sc[0]], TIDX[sc[1]], RSCOPE)
    dm = st.get("dmm")
    if dm and st.get("dmmMode") == "V" and dm[0] and dm[1]:
        stampR(TIDX[dm[0]], TIDX[dm[1]], 1e7)

    rex = 0.0
    if st.get("pan"):
        rex += rload(st["pan"], f)
    if st.get("stack"):
        rex += 0.02 * math.sqrt(max(f, 1.0) / 40000.0) * len(st["stack"])
    Meff = COIL_M * shielding(st.get("stack") or [], f)

    bFG, bL1, bL2 = (N - 1), (N - 1) + 1, (N - 1) + 2
    at(nmap[TIDX["FGP"]], bFG, 1); at(nmap[TIDX["FGN"]], bFG, -1)
    at(bFG, nmap[TIDX["FGP"]], 1); at(bFG, nmap[TIDX["FGN"]], -1)
    at(bFG, bFG, -FG_RS)
    b[bFG] = complex(st.get("E", 0.0), 0)

    Zc = complex(COIL_RL + rex, w * COIL_L)
    Zm = complex(0, w * Meff)
    for br, p, m, other in ((bL1, "C1A", "C1B", bL2), (bL2, "C2A", "C2B", bL1)):
        ip, im = TIDX[p], TIDX[m]
        at(nmap[ip], br, 1); at(nmap[im], br, -1)
        at(br, nmap[ip], 1); at(br, nmap[im], -1)
        at(br, br, -Zc); at(br, other, -Zm)

    x = csolve(A, b)
    if x is None:
        return None
    ifg = abs(x[bFG])
    if ifg > FG_ILIM:                       # 증폭기 전류 제한 (회로가 선형이므로 비례 축소)
        s2 = FG_ILIM / ifg
        x = [v * s2 for v in x]
    V = {t: (0j if TIDX[t] == gnd else x[nmap[TIDX[t]]]) for t in TERMS}
    return Solution(V, x[bL1], x[bL2], x[bFG])


def measure_r(st, ta, tb):
    """멀티미터 Ω 모드: 전원 끄고 축전기 개방, 코일은 R_L 만."""
    if not ta or not tb or ta == tb:
        return float("inf")
    N = len(TERMS)
    G = [[0.0] * N for _ in range(N)]

    def add(a, bb, g):
        G[a][a] += g; G[bb][bb] += g; G[a][bb] -= g; G[bb][a] -= g

    for ca, cb in st["cables"]:
        if ca in TIDX and cb in TIDX:
            add(TIDX[ca], TIDX[cb], 1.0 / RCAB)
    add(TIDX["R1A"], TIDX["R1B"], 1.0 / R1_OHM)
    add(TIDX["C1A"], TIDX["C1B"], 1.0 / COIL_RL)
    add(TIDX["C2A"], TIDX["C2B"], 1.0 / COIL_RL)
    if st.get("pan"):
        add(TIDX["NTCA"], TIDX["NTCB"], 1.0 / rntc(st.get("panT", T_AMB)))
    add(TIDX["FGP"], TIDX["FGN"], 1.0 / FG_RS)
    for i in range(N):
        G[i][i] += 1e-12
    ref, src = TIDX[tb], TIDX[ta]
    keep = [i for i in range(N) if i != ref]
    M = [[complex(G[i][j], 0) for j in keep] for i in keep]
    rhs = [complex(1.0 if i == src else 0.0, 0) for i in keep]
    x = csolve(M, rhs)
    if x is None:
        return float("inf")
    R = x[keep.index(src)].real
    return float("inf") if R > 1e7 else R


def live_terms(st):
    """Terminals that carry the generator's signal: everything wired to the
    generator, plus both coils once either is in that net (they are coupled
    through M).  The pan's NTC is on its own and stays readable."""
    par = {t: t for t in TERMS}

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    def join(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            par[ra] = rb

    for a, b in st["cables"]:
        if a in par and b in par:
            join(a, b)
    join("R1A", "R1B"); join("FGP", "FGN")
    join("C1A", "C1B"); join("C2A", "C2B")
    if st.get("cap"):
        join("CBA", "CBB")
    g = find("FGP")
    if find("C1A") == g or find("C2A") == g:
        join("C1A", "C2A")
        g = find("FGP")
    return {t for t in TERMS if find(t) == g}


def thermal_step(pan_key, T, Irms, f, dt, uncovered):
    p = PAN[pan_key]
    Pin = Irms * Irms * rload(pan_key, f)
    Ploss = p.e * p.area * SB * (T ** 4 - T_AMB ** 4)
    if uncovered:
        Ploss += 8.0 * p.area * (T - T_AMB)        # 자연대류 h ≈ 8 W/m²K
    return T + (Pin - Ploss) * dt / (p.mass * p.c)


# =============================================================================
# 2. 문자열
# =============================================================================
_S = {
    "KO": dict(
        title="APhO 2025 · 실험 1 — 유도가열 조리기의 물리",
        lab="실험대", task="문제", note="기록지", help="사용법", speed="시간 배속",
        cable="케이블 연결", pp="프로브 +", pn="프로브 −", dp="DMM +", dn="DMM −", erase="지우기",
        h_cable="단자를 두 번 눌러 케이블을 연결합니다.", h_probe="스코프 프로브를 놓을 단자를 누르세요.",
        h_dmm="멀티미터 리드를 놓을 단자를 누르세요.", h_erase="케이블을 눌러 제거합니다.",
        t_cap="축전기", t_plate="금속판", t_pan="조리 팬", t_misc="설치",
        slotclear="슬롯 비우기", cover="차폐 덮개", coveron="닫힘", coveroff="열림",
        fg="함수 발생기", fgout="출력", on="ON", off="OFF",
        scope="디지털 오실로스코프 ZOYI ZT-702S", sw="스톱워치",
        startstop="시작 / 정지", lap="랩", reset="초기화",
        rec="현재 값 기록", csv="CSV 저장", clearnote="기록 삭제", recwhat="항목 이름",
        unclip="프로브 해제", undmm="DMM 해제",
        ovr="코일이 뜨거워지고 있습니다 — 전류를 줄이세요 (2 A-peak 이하로)",
        nocap="축전기 없이 코일을 구동하면 코일이 뜨거워집니다",
        dmmfreq="AC 전압 모드는 40 Hz–1 kHz 에서만 유효",
        dmmlive="신호가 걸린 회로입니다 — 발생기 출력을 끄고 재세요",
        coil1="코일 #1", coil2="코일 #2", slotempty="슬롯 비어 있음", probeoff="프로브 미연결",
        plate="판", exagg="판 두께는 보기 좋게 과장되어 있습니다",
        pinterm="핀 단자", capins="축전기를 꽂으세요", powres="전력 저항 R₁",
        capbox="블랙박스 · 축전기 홀더", logged="기록했습니다", saved="저장했습니다",
        cols=("#", "시각", "항목", "값", "주파수", "조건"),
        fgtip="노브를 위아래로 끌어 조절합니다. 발생기에는 주파수 표시가 없습니다 — 스코프로 읽으세요.",
        wave="이 실험에서는 정현파만 사용합니다", maxcable="케이블은 8개까지 있습니다",
    ),
    "EN": dict(
        title="APhO 2025 · Experiment 1 — Physics of Induction Cooking",
        lab="Bench", task="Tasks", note="Log", help="How to use", speed="Time ×",
        cable="Cable", pp="Probe +", pn="Probe −", dp="DMM +", dn="DMM −", erase="Remove",
        h_cable="Click two terminals to run a cable between them.",
        h_probe="Click the terminal to clip the scope probe onto.",
        h_dmm="Click the terminal to clip the multimeter lead onto.",
        h_erase="Click a cable to remove it.",
        t_cap="Capacitors", t_plate="Metal plates", t_pan="Cooking pans", t_misc="Setup",
        slotclear="Empty the slot", cover="Shield lid", coveron="closed", coveroff="open",
        fg="Function generator", fgout="OUTPUT", on="ON", off="OFF",
        scope="Digital oscilloscope ZOYI ZT-702S", sw="Stopwatch",
        startstop="Start / Stop", lap="Lap", reset="Reset",
        rec="Log this reading", csv="Save CSV", clearnote="Clear log", recwhat="Item name",
        unclip="Unclip probes", undmm="Unclip DMM",
        ovr="The coil is warming up: turn the current down (keep it under 2 A-peak)",
        nocap="Driving the coil without a capacitor makes it very hot",
        dmmfreq="AC volts mode is valid only from 40 Hz to 1 kHz",
        dmmlive="That circuit is live: switch the generator output off first",
        coil1="coil #1", coil2="coil #2", slotempty="slot empty", probeoff="no probe",
        plate="plate", exagg="Plate thickness is drawn exaggerated",
        pinterm="pin terminals", capins="insert a capacitor", powres="POWER RESISTOR R₁",
        capbox="BLACK BOX · CAPACITOR HOLDER", logged="Logged", saved="Saved",
        cols=("#", "Time", "Item", "Value", "Frequency", "Conditions"),
        fgtip="Drag a knob up or down. The generator has no frequency display — read it on the scope.",
        wave="Use the sine waveform for every part of this experiment",
        maxcable="Only eight cables are supplied",
    ),
}


def S(k):
    return _S[LANG][k]


TASK_TEXT = {"KO": """실험 1 — 유도 코일의 특성 (4.5점)
  노란 저항 R₁(1 Ω), 코일 #1, 축전기로 직렬 RLC 회로를 구성합니다.
  부하 임피던스가 변하면 발생기 출력 전압도 함께 변합니다.

  1.1 (0.4) 회로를 그리고 각 부분을 표시하세요. 케이블 저항 R_C 는 무시할 수 없습니다 — 옴미터로 측정.
  1.2 (1.2) C = 470 nF, 2200 µF 의 공진 주파수를 구하고 공진 곡선을 그려 L 을 결정하세요.
  1.3 (0.5) 축전기 하나의 공진 자료만으로는 L 이 부정확합니다. L 과 R_L 을 함께 뽑을 선형 모형을 세우세요.
  1.4 (1.4) C = 470 µF, 1000 µF 로도 측정하고 네 자료 전부를 새 모형으로 분석하세요.
  1.5 (1.0) 네 축전기 각각의 L, R_L 을 구하고 평균을 내세요.

실험 2 — 상호 유도와 표피 깊이 (8.1점)     구동 회로는 C = 1000 µF 직렬 RLC.

  2.1 (0.4) 상호 인덕턴스 측정 배치를 그리세요.
  2.2 (1.0) 1차·2차 코일의 역할을 바꿔 두 번 측정하고 각각 그래프를 그리세요.
  2.3 (0.4) 각 배치의 상호 인덕턴스 M 을 구하세요.
  2.4 (5.5) 두 코일 사이에 금속판을 넣어 금속별 주파수 지수 n 을 구하세요(정수로 반올림).
            표피 깊이가 극단적이라 좋은 자료가 나오지 않는 금속 하나를 찾아 2.5–2.6 에서 제외하세요.
  2.5 (0.2) 차원 해석으로 전도도 지수 m 을 구하세요.
  2.6 (0.6) 자료가 좋은 세 금속의 전도도 σ 를 구하세요.

  주어진 식:  B(z) = B₀ e^(−z/δ) cos(ωt − z/δ + φ),   δ = √(σᵐ fⁿ / πµ),   µ = µ_r µ₀

실험 3 — "조리": 비열과 유효 부하저항 (7.4점)
  C = 1000 µF, f ≈ 40 kHz, 코일 전류는 2 A-peak 이하. 복사 외의 열손실은 없다고 봅니다.

  3.1 (0.2) 유도 조리기의 작동 원리를 그림으로 나타내세요.
  3.2 (0.5) 금속 팬의 비열 c 를 구할 물리 모형을 세우세요.
  3.3 (1.5) 알루미늄 팬의 비열을 측정하세요 (코일 #2 로 가열).
  3.4 (1.5) SS410 팬에 대해 반복하세요.
  3.5 (1.6) Al 팬의 R_LOAD 모형을 세우고 측정하세요. 전력을 넣고 약 30 초 뒤부터 측정하세요.
  3.6 (1.5) SS410 팬에 대해 반복하세요.
  3.7 (0.1) 어느 쪽이 조리용으로 더 낫습니까?  (a) 알루미늄  (b) SS410
  3.8 (0.1) 그 선택에서 가장 지배적인 물리량은?
            (a) 전기전도도 (b) 자기투자율 (c) 밀도 (d) 비열 (e) 열전도도
  3.9 (0.4) 두 팬의 유도 가열 효율 η 를 계산하세요.

  P_RAD = e A σ_S T⁴,   R_NTC = R₀ exp[B(1/T − 1/T₀)],  R₀ = 10 kΩ, T₀ = 298 K, B = 3950 K
  σ_S = 5.670×10⁻⁸ W m⁻² K⁻⁴,  µ₀ = 4π×10⁻⁷ H/m
  ρ_Al = 2700, ρ_SS410 = 7700 kg/m³,  e_Al = 0.65, e_SS410 = 0.8

  치수 — 팬 2×2 cm (Al 0.73 mm, SS410 0.76 mm)
        판 2.7×4.6 cm (Al 0.73, Cu 0.71, SS304 0.72, SS410 0.76 mm)
        SS410 은 µ_r = 700, 나머지는 µ_r = 1
""", "EN": """Experiment 1 — Characterising the induction coil (4.5 pt)
  Build a series RLC circuit from the yellow resistor R₁ (1 Ω), coil #1 and a capacitor.
  The generator output voltage changes as the load impedance changes.

  1.1 (0.4) Sketch the circuit and label every part. Cable resistance R_C is not negligible — measure it.
  1.2 (1.2) Find the resonance frequency for C = 470 nF and 2200 µF, plot the curve, determine L.
  1.3 (0.5) One capacitor alone gives an inaccurate L. Develop a linear model yielding both L and R_L.
  1.4 (1.4) Repeat for C = 470 µF and 1000 µF, then analyse all four data sets with the new model.
  1.5 (1.0) Determine L and R_L for all four capacitors and average them.

Experiment 2 — Mutual induction and skin depth (8.1 pt)   Drive with C = 1000 µF series RLC.

  2.1 (0.4) Sketch the setup for measuring the mutual inductance.
  2.2 (1.0) Measure twice, swapping the roles of the coils, and plot both.
  2.3 (0.4) Determine M for each configuration.
  2.4 (5.5) Insert metal plates between the coils and determine n for each metal (nearest integer).
            Identify the one metal whose skin depth is so extreme it must be dropped from 2.5–2.6.
  2.5 (0.2) Deduce the conductivity power factor m by dimensional analysis.
  2.6 (0.6) Determine σ for the three metals that gave good data.

  Given:  B(z) = B₀ e^(−z/δ) cos(ωt − z/δ + φ),   δ = √(σᵐ fⁿ / πµ),   µ = µ_r µ₀

Experiment 3 — "Cooking": specific heat and effective load resistance (7.4 pt)
  C = 1000 µF, f ≈ 40 kHz, keep the coil current below 2 A-peak. Radiation is the only heat loss.

  3.1 (0.2) Draw how the induction cooker works.
  3.2 (0.5) Develop a physical model for the specific heat c of the pans.
  3.3 (1.5) Measure the specific heat of the aluminium pan, heating it with coil #2.
  3.4 (1.5) Repeat for the SS410 pan.
  3.5 (1.6) Model and measure R_LOAD for the Al pan, reading from about 30 s after power is applied.
  3.6 (1.5) Repeat for the SS410 pan.
  3.7 (0.1) Which works better as a cooking pan?  (a) aluminium  (b) SS410
  3.8 (0.1) Which parameter dominates that choice?
            (a) conductivity (b) magnetic permeability (c) density (d) specific heat (e) thermal cond.
  3.9 (0.4) Calculate the induction cooking efficiency η for both pans.

  P_RAD = e A σ_S T⁴,   R_NTC = R₀ exp[B(1/T − 1/T₀)],  R₀ = 10 kΩ, T₀ = 298 K, B = 3950 K
  σ_S = 5.670×10⁻⁸ W m⁻² K⁻⁴,  µ₀ = 4π×10⁻⁷ H/m
  ρ_Al = 2700, ρ_SS410 = 7700 kg/m³,  e_Al = 0.65, e_SS410 = 0.8

  Dimensions — pans 2×2 cm (Al 0.73 mm, SS410 0.76 mm)
               plates 2.7×4.6 cm (Al 0.73, Cu 0.71, SS304 0.72, SS410 0.76 mm)
               SS410 has µ_r = 700, the rest µ_r = 1
"""}

HELP_TEXT = {"KO": """실험대 사용법

배선     위쪽 [케이블 연결] 을 켜고 단자를 두 번 누르면 그 사이에 케이블이 연결됩니다.
         직렬 RLC 는 발생기 출력 → 축전기 → 코일 핀 → R₁ → 발생기 반대 단자로 한 바퀴 잇습니다.
         케이블은 8개까지, [지우기] 로 케이블을 눌러 뺍니다.

프로브   [프로브 +] / [프로브 −] 로 스코프 프로브 두 끝을 원하는 단자에 겁니다.
         스코프는 두 단자 사이 전압만 보여 줍니다. 전류는 R₁ 양단 전압을 재서 직접 나누세요.

주파수   발생기에는 주파수 표시가 없습니다. RANGE 로 대역을 고르고 COARSE·FINE 노브를 끌어
         맞춘 뒤 스코프 화면의 F 값을 읽으세요. 노브는 위아래로 끌거나 휠을 굴려 조절합니다.

멀티미터 MODE 로 DMM 으로 바꾸면 저항(Ω)과 AC 전압을 잽니다. 발생기에 연결된 회로의 저항은
         출력을 끈 상태에서만 잴 수 있고(팬의 NTC 는 따로 떨어져 있어 가열 중에도 잴 수 있습니다),
         AC 전압은 실제 장비와 같이 40 Hz–1 kHz 에서만 동작합니다.

판과 팬  왼쪽에서 금속판을 누르면 두 코일 사이 슬롯에 한 장씩 쌓입니다(단면도).
         팬을 고르면 슬롯에 뒤집어 고정되고 NTC 배선 두 가닥이 오른쪽으로 나옵니다.
         팬 온도는 그 NTC 저항을 재서 알아냅니다.

시간     가열·냉각은 실제로 수 분 걸립니다. 위쪽 시간 배속으로 빠르게 돌릴 수 있고
         스톱워치도 같은 시계를 씁니다.

기록지   [현재 값 기록] 은 지금 계기에 떠 있는 값을 종이에 옮겨 적는 것과 같습니다.
         회귀·기울기·유도량 계산은 제공하지 않습니다. 분석은 직접 하세요.


물리 모형 메모 (공식 해설 v3.0 기준 보정)

  코일 L = 47.2 µH, R_L = 0.47 Ω, M = 5.79 µH
  R₁ = 1 Ω, 케이블 1개 22.5 mΩ (회로에 4개 → R_C = 0.09 Ω), 전해 축전기 ESR 30 mΩ
  발생기 출력 임피던스 2 Ω, 앰프 전류 제한 4 A-peak
  δ = 1/√(πσµf),  σ = 3.70e7 / 5.88e7 / 1.39e6 / 1.70e6 S/m (Al, Cu, SS304, SS410)
  차폐  V₂ ∝ (1−α)e^(−Σt/δ) + α e^(−Σt/δ_f),  누설 α = 비자성 0.005, SS410 0.55
        자성체는 자속이 판 안으로 끌려들어가 측면으로 빠져나오므로 표피 깊이 측정이 무너집니다.
  열    mc dT/dt = I²R_LOAD − eAσ_S(T⁴−T₀⁴),  A = 2×(2 cm)², 주위 303.5 K
        덮개를 열면 자연대류(h ≈ 8 W m⁻²K⁻¹)가 더해져 결과가 틀어집니다.
  R_LOAD(40 kHz) = 54.6 mΩ (Al) / 137.7 mΩ (SS410), √f 비례
  판독 잡음 0.4 %, 유효숫자 4자리, 화면 눈금의 0.25 % 오프셋
""", "EN": """Using the bench

Wiring     With [Cable] active, click two terminals and a cable runs between them.
           For the series RLC loop: generator output → capacitor → coil pins → R₁ → other terminal.
           Eight cables are supplied; [Remove] takes one out again.

Probes     Clip the two scope probe ends onto any terminals with [Probe +] / [Probe −].
           The scope shows only the voltage between them. For current, measure across R₁.

Frequency  The generator has no frequency display. Pick a band with RANGE, drag COARSE and FINE,
           then read F on the scope. Drag knobs vertically or use the wheel.

Multimeter MODE switches to DMM for resistance and AC volts. Anything wired to the generator reads
           only with the output off (the pan's NTC is separate and reads while heating); AC volts works
           from 40 Hz to 1 kHz just like the real instrument.

Plates     Clicking a metal drops one plate into the slot between the coils (cross-section view).
and pans   Choosing a pan clamps it in the slot upside down with NTC leads running out to the right;
           read its resistance to get the pan temperature.

Time       Heating and cooling really take minutes. The time multiplier speeds the whole bench up,
           stopwatch included.

Log        "Log this reading" copies what the instrument shows right now, the way you would write it
           on paper. No fitting, no slopes, no derived quantities: the analysis is yours.


Model notes (calibrated against the official solution v3.0)

  Coil L = 47.2 µH, R_L = 0.47 Ω, M = 5.79 µH
  R₁ = 1 Ω, 22.5 mΩ per cable (four in the loop → R_C = 0.09 Ω), 30 mΩ ESR on electrolytics
  Generator output impedance 2 Ω, amplifier current limit 4 A-peak
  δ = 1/√(πσµf),  σ = 3.70e7 / 5.88e7 / 1.39e6 / 1.70e6 S/m (Al, Cu, SS304, SS410)
  Shielding  V₂ ∝ (1−α)e^(−Σt/δ) + α e^(−Σt/δ_f), leakage α = 0.005 non-magnetic, 0.55 for SS410
  Heat       mc dT/dt = I²R_LOAD − eAσ_S(T⁴−T₀⁴), A = 2×(2 cm)², ambient 303.5 K
             Opening the lid adds convection (h ≈ 8 W m⁻²K⁻¹) and spoils the result.
  R_LOAD(40 kHz) = 54.6 mΩ (Al) / 137.7 mΩ (SS410), scaling as √f
  Readout noise 0.4 %, four significant figures, plus 0.25 % of full scale
"""}


# =============================================================================
# 3. 화면 상수 · 배치
# =============================================================================
BW, BH = 1020, 580
BG, BENCH, PANEL = "#101315", "#1b1f23", "#1e2226"
LINE, INK, DIM, FAINT = "#2b3137", "#e8eaec", "#8d969e", "#5b646c"
AMBER, PHOS, RED, CYAN = "#f0a23c", "#7dfab0", "#c8372d", "#4ec9e8"

BOXES = {"fg": (28, 34, 264, 158), "cbox": (28, 196, 264, 328),
         "r1": (28, 366, 264, 498), "stage": (330, 24, 1000, 544)}

# (id, x, y, kind 'b'anana/'p'in, color 'r'ed/'k'black, label)
TERM_DEF = [("FGP", 232, 72, "b", "r", "FG +"), ("FGN", 232, 116, "b", "k", "FG −"),
            ("CBA", 74, 300, "b", "r", "C 1"), ("CBB", 218, 300, "b", "k", "C 2"),
            ("R1A", 74, 470, "b", "r", "R1 1"), ("R1B", 218, 470, "b", "k", "R1 2"),
            ("C1A", 356, 252, "p", "r", "L1 a"), ("C1B", 356, 292, "p", "k", "L1 b"),
            ("C2A", 356, 440, "p", "r", "L2 a"), ("C2B", 356, 480, "p", "k", "L2 b"),
            ("NTCA", 966, 300, "p", "r", "NTC"), ("NTCB", 966, 340, "p", "k", "NTC")]
TPOS = {t[0]: (t[1], t[2]) for t in TERM_DEF}
SLOT_X, SLOT_Y0, SLOT_X2 = 402, 412, 928
ANCH_SCOPE, ANCH_DMM = (994, 46), (994, 544)
VDIV = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10]
TDIV = [1e-6, 2e-6, 5e-6, 1e-5, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4,
        1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2]
FRANGE = [(20, 200), (200, 2000), (2000, 20000), (20000, 100000)]
KNOBS = [("amp", 48, 92, 21, "AMPLITUDE", False), ("range", 116, 92, 18, "FREQ RANGE", False),
         ("coarse", 178, 58, 15, "COARSE", False), ("fine", 178, 110, 15, "FINE", True),
         ("wave", 238, 92, 18, "WAVEFORM", False)]
CCOL = ["#c94b3c", "#2b3238", "#c94b3c", "#2b3238", "#3f7ec4", "#7a8189"]


def pick_font(cands, size, weight="normal"):
    fams = set(tkfont.families())
    for f in cands:
        if f in fams:
            return (f, size, weight)
    return ("TkDefaultFont", size, weight)


def bez2(a, b, k):
    """케이블용 2차 베지에 표본점."""
    ax, ay = TPOS[a]; bx, by = TPOS[b]
    mx, my = (ax + bx) / 2, max(ay, by) + 34 + (k % 3) * 12
    out = []
    for i in range(17):
        t = i / 16.0; u = 1 - t
        out += [u * u * ax + 2 * u * t * mx + t * t * bx,
                u * u * ay + 2 * u * t * my + t * t * by]
    return out


def bez3(p0, p1, p2, p3):
    out = []
    for i in range(15):
        t = i / 14.0; u = 1 - t
        out += [u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]]
    return out


def sig3(x):
    if x == 0 or not math.isfinite(x):
        return 0.0
    d = 10 ** (math.floor(math.log10(abs(x))) - 3)
    return round(x / d) * d


def fmt_v(v):
    if v >= 1:      return "%.3f V" % v
    if v >= 1e-3:   return ("%.1f mV" if v >= 0.1 else "%.2f mV") % (v * 1000)
    return "%.0f µV" % (v * 1e6)


def fmt_f(f):
    if not f:       return "- - -"
    if f >= 1000:   return ("%.2f kHz" if f >= 10000 else "%.3f kHz") % (f / 1000.0)
    return "%.1f Hz" % f


def fmt_r(R):
    if R == -1:                 return "- - -"
    if not math.isfinite(R):    return "O.L"
    if R >= 1000:               return "%.3f kΩ" % (R / 1000.0)
    return "%.3f Ω" % R


def fmt_t(x):
    if x >= 1e-3:   return ("%.0f ms" if x >= 1e-2 else "%.1f ms") % (x * 1e3)
    return ("%.0f µs" if x >= 1e-5 else "%.1f µs") % (x * 1e6)


# =============================================================================
# 4. 애플리케이션
# =============================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(S("title"))
        self.configure(bg=BG)
        self.geometry("1400x880")
        self.minsize(1080, 700)
        self.f_ui = pick_font(["Malgun Gothic", "Noto Sans CJK KR", "NanumGothic", "DejaVu Sans"], 9)
        self.f_ui2 = pick_font(["Malgun Gothic", "Noto Sans CJK KR", "NanumGothic", "DejaVu Sans"], 10, "bold")
        self.f_mono = pick_font(["Consolas", "DejaVu Sans Mono", "Courier New"], 8)
        self.f_mono2 = pick_font(["Consolas", "DejaVu Sans Mono", "Courier New"], 10, "bold")
        self.f_big = pick_font(["Consolas", "DejaVu Sans Mono", "Courier New"], 22, "bold")

        # ---- 상태 ----
        self.cables = []            # [(a,b)]
        self.cap = None
        self.stack = []
        self.pan = None
        self.panT = T_AMB
        self.covered = True
        self.fg = {"amp": 25.0, "range": 2, "coarse": 50.0, "fine": 50.0, "on": False}
        self.sp = self.sn = self.dp = self.dn = None
        self.mode, self.dmm_fn, self.probe_x = "SCOPE", "R", 1
        self.hold, self.held = False, None
        self.vi, self.ti = 7, 5
        self.tool, self.pending = "cable", None
        self.sw_t, self.sw_run, self.laps = 0.0, False, []
        self.speed = 20
        self.notes, self.nno = [], 0
        self.disp = {"v": 0.0, "f": 0.0, "r": 0.0, "clip": False, "off": True, "t": 0.0}
        self.sol = None
        self.drag = None
        self.msg, self.msg_until = "", 0.0

        self._build()
        self.solve()
        self.draw_bench(); self.draw_fg(); self.draw_scope()
        self.last = time.time()
        self.after(60, self.tick)

    # ---------------- 상태 → 물리 ----------------
    def freq(self):
        lo, hi = FRANGE[self.fg["range"]]
        f = lo * (hi / lo) ** (self.fg["coarse"] / 100.0)
        return f * (1 + 0.03 * (self.fg["fine"] - 50) / 50.0)

    def emf(self):
        return FG_EMAX * self.fg["amp"] / 100.0 if self.fg["on"] else 0.0

    def pstate(self):
        return {"cables": list(self.cables), "cap": self.cap, "stack": self.stack,
                "pan": self.pan, "panT": self.panT, "E": self.emf(),
                "scope": (self.sp, self.sn) if self.mode == "SCOPE" else None,
                "dmm": (self.dp, self.dn) if (self.mode == "DMM" and self.dmm_fn == "V") else None,
                "dmmMode": self.dmm_fn}

    def solve(self):
        self.sol = analyze(self.pstate(), self.freq())
        return self.sol

    def term_live(self, tid):
        return bool(self.pan) if tid in ("NTCA", "NTCB") else True

    def flash(self, m):
        self.msg, self.msg_until = m, time.time() + 2.5

    # =====================================================================
    # 4.1 위젯 구성
    # =====================================================================
    def _build(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("TNotebook", background=BG, borderwidth=0)
        st.configure("TNotebook.Tab", background="#22272b", foreground=DIM,
                     padding=(14, 6), font=self.f_ui)
        st.map("TNotebook.Tab", background=[("selected", "#2f363c")], foreground=[("selected", INK)])
        st.configure("Treeview", background="#15181b", fieldbackground="#15181b",
                     foreground=INK, borderwidth=0, font=self.f_mono, rowheight=20)
        st.configure("Treeview.Heading", background="#22272b", foreground=DIM, font=self.f_ui)

        # ---- 머리말 ----
        head = tk.Frame(self, bg="#22272b", height=40)
        head.pack(fill="x"); head.pack_propagate(False)
        tk.Label(head, text=S("title"), bg="#22272b", fg=INK, font=self.f_ui2).pack(side="left", padx=12)
        tk.Label(head, text="HaslaLab", bg="#22272b", fg=FAINT, font=self.f_ui).pack(side="left")
        tk.Label(head, text=S("speed"), bg="#22272b", fg=DIM, font=self.f_ui).pack(side="left", padx=(24, 4))
        self.spd = ttk.Combobox(head, width=5, state="readonly", font=self.f_ui,
                                values=["1×", "5×", "20×", "60×"])
        self.spd.set("20×"); self.spd.pack(side="left")
        self.spd.bind("<<ComboboxSelected>>",
                      lambda e: setattr(self, "speed", int(self.spd.get().rstrip("×"))))

        nb = ttk.Notebook(self); nb.pack(fill="both", expand=True, padx=6, pady=6)
        lab = tk.Frame(nb, bg=BG); nb.add(lab, text=S("lab"))
        t_task = tk.Frame(nb, bg=BG); nb.add(t_task, text=S("task"))
        self.tab_note = tk.Frame(nb, bg=BG); nb.add(self.tab_note, text=S("note"))
        t_help = tk.Frame(nb, bg=BG); nb.add(t_help, text=S("help"))
        for frame, txt in ((t_task, TASK_TEXT[LANG]), (t_help, HELP_TEXT[LANG])):
            box = tk.Text(frame, bg="#15181b", fg="#c3cad0", bd=0, wrap="none",
                          font=pick_font(["Consolas", "DejaVu Sans Mono"], 10), padx=16, pady=12)
            sb = tk.Scrollbar(frame, command=box.yview, bg=PANEL)
            box.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y"); box.pack(fill="both", expand=True)
            box.insert("1.0", txt); box.configure(state="disabled")

        # ---- 실험대 ----
        tray = tk.Frame(lab, bg=PANEL, width=212); tray.pack(side="left", fill="y")
        tray.pack_propagate(False)
        self.tray = tray
        rack = tk.Frame(lab, bg=PANEL, width=352); rack.pack(side="right", fill="y")
        rack.pack_propagate(False)
        mid = tk.Frame(lab, bg=BG); mid.pack(side="left", fill="both", expand=True)

        tools = tk.Frame(mid, bg=BG); tools.pack(fill="x", pady=(4, 4))
        self.toolbtn = {}
        for key, lb in (("cable", S("cable")), ("probeP", S("pp")), ("probeN", S("pn")),
                        ("dmmP", S("dp")), ("dmmN", S("dn")), ("erase", S("erase"))):
            b = tk.Button(tools, text=lb, font=self.f_ui, bd=0, padx=9, pady=3,
                          bg="#22272b", fg=DIM, activebackground="#2f363c",
                          command=lambda k=key: self.set_tool(k))
            b.pack(side="left", padx=2); self.toolbtn[key] = b
        self.hint = tk.Label(tools, text=S("h_cable"), bg=BG, fg=FAINT, font=self.f_ui)
        self.hint.pack(side="left", padx=10)
        self.logbtn = tk.Button(tools, text=S("rec"), font=self.f_ui, bd=0, padx=9, pady=3,
                                bg="#2f363c", fg=INK, activebackground="#3a4249",
                                command=self.log_current)
        self.logbtn.pack(side="right", padx=(4, 8))
        self.noteName = tk.Entry(tools, bg="#0e1214", fg=INK, insertbackground=INK,
                                 bd=0, font=self.f_ui, width=22)
        self.noteName.pack(side="right", ipady=3)
        tk.Label(tools, text=S("recwhat"), bg=BG, fg=FAINT,
                 font=self.f_ui).pack(side="right", padx=(0, 6))

        self.b = tk.Canvas(mid, width=BW, height=BH, bg=BENCH, highlightthickness=0)
        self.b.pack(fill="both", expand=True, padx=4, pady=2)
        self.bscale, self.box, self.boy = 1.0, 0.0, 0.0
        self.b.bind("<Configure>", lambda e: self.draw_bench())
        self.b.bind("<Button-1>", self.on_bench_click)
        self.warn = tk.Label(mid, text="", bg=BG, fg="#f0a79f", font=self.f_ui, anchor="w")
        self.warn.pack(fill="x", padx=8)

        self._build_tray()
        self._build_rack(rack)
        self._build_note()
        self.set_tool("cable")

    def _sect(self, parent, title):
        tk.Label(parent, text=title, bg=PANEL, fg=FAINT, font=self.f_ui,
                 anchor="w").pack(fill="x", padx=8, pady=(6, 2))

    def _build_tray(self):
        for w in self.tray.winfo_children():
            w.destroy()
        self._sect(self.tray, S("t_cap"))
        for k in CAP_ORDER:
            C, esr, nm, film = CAPS[k]
            self._part(self.tray, nm, "#8a5228" if film else "#2f4f9e",
                       lambda kk=k: self.set_cap(kk), on=(self.cap == k))
        self._sect(self.tray, S("t_plate"))
        for k, m in MAT.items():
            used = self.stack.count(k)
            self._part(self.tray, m.name, m.c1, lambda kk=k: self.add_plate(kk),
                       cnt="%d / %d" % (m.n - used, m.n),
                       dis=(used >= m.n or self.pan is not None or len(self.stack) >= 6))
        self._sect(self.tray, S("t_pan"))
        for k, p in PAN.items():
            self._part(self.tray, p.name, MAT[k].c1, lambda kk=k: self.set_pan(kk),
                       on=(self.pan == k), dis=(len(self.stack) > 0 and self.pan != k))
        self._sect(self.tray, S("t_misc"))
        self._part(self.tray, S("slotclear"), None, self.clear_slot)
        self._part(self.tray, "%s · %s" % (S("cover"), S("coveron") if self.covered else S("coveroff")),
                   None, self.toggle_cover, on=self.covered)

    def _part(self, parent, text, sw, cmd, on=False, dis=False, cnt=None):
        f = tk.Frame(parent, bg="#33291a" if on else "#252b30",
                     highlightbackground=AMBER if on else LINE, highlightthickness=1)
        f.pack(fill="x", padx=8, pady=2)
        if sw:
            tk.Frame(f, bg=sw, width=14, height=14).pack(side="left", padx=6, pady=5)
        lb = tk.Label(f, text=text, bg=f["bg"], fg=FAINT if dis else INK,
                      font=self.f_ui, anchor="w")
        lb.pack(side="left", padx=(4 if sw else 8), pady=4)
        if cnt:
            tk.Label(f, text=cnt, bg=f["bg"], fg=FAINT, font=self.f_mono).pack(side="right", padx=6)
        if not dis:
            for w in (f, lb):
                w.bind("<Button-1>", lambda e, c=cmd: c())

    def _rowbtn(self, parent, text, cmd, on=False):
        b = tk.Button(parent, text=text, font=self.f_ui, bd=0, padx=7, pady=2,
                      bg="#3a4249" if on else "#242a2f", fg=INK if on else DIM,
                      activebackground="#39414a", command=cmd)
        b.pack(side="left", padx=2, pady=2)
        return b

    def _build_rack(self, rack):
        self.rack = rack
        # 함수 발생기
        self._sect(rack, S("fg"))
        self.fgc = tk.Canvas(rack, width=336, height=160, bg="#0e1113", highlightthickness=0)
        self.fgc.pack(padx=8)
        self.fgc.bind("<Button-1>", self.fg_down)
        self.fgc.bind("<B1-Motion>", self.fg_move)
        self.fgc.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag", None))
        self.fgc.bind("<MouseWheel>", self.fg_wheel)
        self.fgc.bind("<Button-4>", lambda e: self.fg_wheel(e, 1))
        self.fgc.bind("<Button-5>", lambda e: self.fg_wheel(e, -1))
        r = tk.Frame(rack, bg=PANEL); r.pack(fill="x", padx=8)
        self.btn_out = self._rowbtn(r, "", self.toggle_out)
        self._rowbtn(r, "RANGE ▶", self.next_range)
        self._rowbtn(r, "AMP −", lambda: self.bump("amp", -2))
        self._rowbtn(r, "AMP +", lambda: self.bump("amp", +2))
        rb = tk.Frame(rack, bg=PANEL); rb.pack(fill="x", padx=8)
        for lb, key in (("COARSE", "coarse"), ("FINE", "fine")):
            self._rowbtn(rb, lb + " −", lambda k=key: self.bump(k, -2))
            self._rowbtn(rb, lb + " +", lambda k=key: self.bump(k, +2))
        tk.Label(rack, text=S("fgtip"), bg=PANEL, fg=FAINT, font=self.f_ui,
                 wraplength=340, justify="left").pack(fill="x", padx=8, pady=(2, 0))

        # 오실로스코프
        self._sect(rack, S("scope"))
        self.osc = tk.Canvas(rack, width=336, height=248, bg="#0e1113", highlightthickness=0)
        self.osc.pack(padx=8)
        r2 = tk.Frame(rack, bg=PANEL); r2.pack(fill="x", padx=8)
        self.btn_mode = self._rowbtn(r2, "", self.toggle_mode, on=True)
        self._rowbtn(r2, "AUTO", self.auto_set)
        self.btn_hold = self._rowbtn(r2, "HOLD", self.toggle_hold)
        self.btn_px = self._rowbtn(r2, "", self.toggle_px)
        r3 = tk.Frame(rack, bg=PANEL); r3.pack(fill="x", padx=8)
        self._rowbtn(r3, "V/div ▲", lambda: self.bump_scale("v", 1))
        self._rowbtn(r3, "V/div ▼", lambda: self.bump_scale("v", -1))
        self._rowbtn(r3, "T/div ◀", lambda: self.bump_scale("t", -1))
        self._rowbtn(r3, "T/div ▶", lambda: self.bump_scale("t", 1))
        r4 = tk.Frame(rack, bg=PANEL); r4.pack(fill="x", padx=8)
        self.btn_acv = self._rowbtn(r4, "AC V", lambda: self.set_dmm("V"))
        self.btn_ohm = self._rowbtn(r4, "Ω", lambda: self.set_dmm("R"))
        self._rowbtn(r4, S("unclip"), self.unclip_probe)
        self._rowbtn(r4, S("undmm"), self.unclip_dmm)

        # 스톱워치 · 기록
        self._sect(rack, S("sw"))
        self.swlbl = tk.Label(rack, text="00:00.0", bg="#0a1a12", fg=PHOS, font=self.f_big)
        self.swlbl.pack(fill="x", padx=8)
        r5 = tk.Frame(rack, bg=PANEL); r5.pack(fill="x", padx=8)
        self._rowbtn(r5, S("startstop"), self.sw_toggle)
        self._rowbtn(r5, S("lap"), self.sw_lap)
        self._rowbtn(r5, S("reset"), self.sw_reset)
        self.lapl = tk.Label(rack, text="", bg=PANEL, fg=FAINT, font=self.f_mono, justify="left", anchor="w")
        self.lapl.pack(fill="x", padx=8)
        self.refresh_buttons()

    def _build_note(self):
        f = self.tab_note
        bar = tk.Frame(f, bg=BG); bar.pack(fill="x", pady=4)
        self._rowbtn(bar, S("csv"), self.save_csv)
        self._rowbtn(bar, S("clearnote"), self.clear_notes)
        cols = ("n", "t", "w", "v", "f", "c")
        self.tree = ttk.Treeview(f, columns=cols, show="headings", height=26)
        for cid, txt, wdt in zip(cols, S("cols"), (44, 70, 150, 130, 100, 460)):
            self.tree.heading(cid, text=txt); self.tree.column(cid, width=wdt, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=6, pady=4)

    def refresh_buttons(self):
        self.btn_out.configure(text="%s %s" % (S("fgout"), S("on") if self.fg["on"] else S("off")),
                               bg="#4a2320" if self.fg["on"] else "#242a2f",
                               fg="#f0a79f" if self.fg["on"] else DIM)
        self.btn_mode.configure(text="MODE: " + self.mode)
        self.btn_hold.configure(bg="#3a4249" if self.hold else "#242a2f")
        self.btn_px.configure(text="PROBE " + ("10X" if self.probe_x == 10 else "1X"),
                              bg="#3a4249" if self.probe_x == 10 else "#242a2f")
        for b, act in ((self.btn_acv, self.dmm_fn == "V"), (self.btn_ohm, self.dmm_fn == "R")):
            b.configure(bg="#3a4249" if (act and self.mode == "DMM") else "#242a2f")

    # =====================================================================
    # 4.2 실험대 그리기
    # =====================================================================
    def _t(self, c, x, y, s, fill=DIM, size=8, anchor="w", bold=False):
        c.create_text(x, y, text=s, fill=fill, anchor=anchor,
                      font=pick_font(["Consolas", "DejaVu Sans Mono"], size, "bold" if bold else "normal"))

    def _screw(self, c, x, y, r=3):
        c.create_oval(x - r, y - r, x + r, y + r, fill="#3a4046", outline="")
        c.create_line(x - r * .6, y, x + r * .6, y, fill="#14171a")

    def draw_bench(self):
        c = self.b
        c.delete("all")
        for x in range(0, BW, 26):
            c.create_line(x, 0, x, BH, fill="#1e2327")
        for y in range(0, BH, 26):
            c.create_line(0, y, BW, y, fill="#1e2327")
        self._d_fg(c); self._d_cap(c); self._d_r1(c)
        self._d_stage(c); self._d_cables(c); self._d_terms(c)
        w, h = c.winfo_width(), c.winfo_height()
        if w > 10 and h > 10:                       # 창 크기에 맞춰 축척·중앙 정렬
            sc = min(w / float(BW), h / float(BH), 1.0)
            self.bscale = sc
            if abs(sc - 1.0) > 0.005:
                c.scale("all", 0, 0, sc, sc)
            self.box, self.boy = (w - BW * sc) / 2.0, (h - BH * sc) / 2.0
            c.move("all", self.box, self.boy)

    def _d_fg(self, c):
        x0, y0, x1, y1 = BOXES["fg"]
        c.create_rectangle(x0 + 5, y0 + 8, x1 + 5, y1 + 8, fill="#0b0d0f", outline="")
        c.create_rectangle(x0, y0, x1, y1, fill="#23282d", outline="#000")
        c.create_rectangle(x0 + 12, y0 + 22, x1 - 12, y1 - 22, fill="#e9e6e0", outline="#b9b4ab")
        self._t(c, x0 + 20, y0 + 34, "FUNCTION GENERATOR", "#5c6167", 8)
        vals = [self.fg["amp"], self.fg["range"] * 33, self.fg["coarse"], self.fg["fine"]]
        for i, v in enumerate(vals):
            x, y = x0 + 34 + i * 40, y0 + 66
            c.create_oval(x - 11, y - 11, x + 11, y + 11, fill="#454b51", outline="")
            c.create_oval(x - 7, y - 7, x + 7, y + 7, fill="#20252a", outline="")
            a = -math.pi * .75 + v / 100.0 * math.pi * 1.5
            c.create_line(x, y, x + math.cos(a) * 9, y + math.sin(a) * 9, fill="#cfd3d6", width=2)
        c.create_oval(x0 + 20, y0 + 48, x0 + 28, y0 + 56,
                      fill="#ff5a4a" if self.fg["on"] else "#4a2320", outline="")
        for sx, sy in ((x0 + 9, y0 + 9), (x1 - 9, y0 + 9), (x0 + 9, y1 - 9), (x1 - 9, y1 - 9)):
            self._screw(c, sx, sy)

    def _d_cap(self, c):
        x0, y0, x1, y1 = BOXES["cbox"]
        c.create_rectangle(x0 + 5, y0 + 8, x1 + 5, y1 + 8, fill="#0b0d0f", outline="")
        c.create_rectangle(x0, y0, x1, y1, fill="#1c2024", outline="#000")
        self._t(c, x0 + 14, y0 + 18, S("capbox"), "#6e767d", 8)
        c.create_rectangle(x0 + 40, y0 + 32, x1 - 40, y0 + 84, fill="#0b0d0f", outline="")
        mx, my = (x0 + x1) / 2, y0 + 58
        if self.cap:
            _, _, nm, film = CAPS[self.cap]
            if film:
                c.create_rectangle(mx - 17, my - 17, mx + 17, my + 13, fill="#7a4a26", outline="#5d3719")
                self._t(c, mx, my + 2, "470n", "#f2dfc9", 8, "center")
            else:
                c.create_rectangle(mx - 15, my - 20, mx + 15, my + 16, fill="#2c4b8f", outline="#1a2f5c")
                c.create_rectangle(mx - 15, my - 16, mx - 7, my + 16, fill="#8fa8d8", outline="")
                self._t(c, mx + 4, my - 2, nm.replace(" ", ""), "#dbe6ff", 7, "center")
            for dx, tx in ((-10, 74), (10, 218)):
                c.create_line(mx + dx, my + 16, mx + dx, y0 + 84, fill="#9aa3ab", width=2)
                c.create_line(mx + dx, y0 + 84, tx, y0 + 96, fill="#9aa3ab", width=2)
        else:
            self._t(c, mx, my, S("capins"), "#4a5158", 9, "center")
        self._screw(c, x0 + 10, y1 - 10); self._screw(c, x1 - 10, y1 - 10)

    def _d_r1(self, c):
        x0, y0, x1, y1 = BOXES["r1"]
        c.create_rectangle(x0 + 5, y0 + 8, x1 + 5, y1 + 8, fill="#0b0d0f", outline="")
        c.create_rectangle(x0, y0, x1, y1, fill="#1c2024", outline="#000")
        rx, ry, rw, rh = x0 + 34, y0 + 40, (x1 - x0) - 68, 30
        c.create_rectangle(rx, ry, rx + rw, ry + rh, fill="#e0bd35", outline="#7d6210")
        c.create_rectangle(rx + 3, ry + 4, rx + rw - 3, ry + 8, fill="#f6e69a", outline="")
        self._t(c, rx + rw / 2, ry + rh / 2 + 1, "1 Ω  100 W", "#4a3a06", 9, "center", True)
        c.create_rectangle(rx - 8, ry + 8, rx + 2, ry + 22, fill="#8b8f93", outline="")
        c.create_rectangle(rx + rw - 2, ry + 8, rx + rw + 8, ry + 22, fill="#8b8f93", outline="")
        c.create_line(rx - 4, ry + 22, 74, y0 + 96, fill="#9aa3ab", width=2)
        c.create_line(rx + rw + 4, ry + 22, 218, y0 + 96, fill="#9aa3ab", width=2)
        self._t(c, x0 + 14, y0 + 18, S("powres"), "#6e767d", 8)
        self._screw(c, x0 + 10, y1 - 10); self._screw(c, x1 - 10, y1 - 10)

    def _d_stage(self, c):
        X0, X1 = 380, 950
        c.create_rectangle(350, 505, 980, 529, fill="#b8bcc0", outline="#8f9498")
        for (yy0, yy1, cy) in ((415, 505, 440), (230, 320, 272)):
            c.create_rectangle(X0, yy0, X1, yy1, fill="#22272c", outline="#000")
            c.create_rectangle(430, cy, 900, cy + 22, fill="#c8372d", outline="#8e1f16")
            c.create_rectangle(433, cy + 3, 897, cy + 7, fill="#e06a5e", outline="")
            for x in range(436, 898, 13):
                c.create_line(x, cy + 1, x, cy + 21, fill="#8e1f16")
        self._t(c, 905, 451, S("coil2"), "#9aa3ab", 8)
        self._t(c, 905, 283, S("coil1"), "#9aa3ab", 8)
        for x in (430, 860):
            c.create_rectangle(x, 208, x + 60, 232, fill="#4b5157", outline="#000")
            self._screw(c, x + 12, 220, 4); self._screw(c, x + 48, 220, 4)
        c.create_rectangle(X0, 320, X0 + 22, 415, fill="#1b1f22", outline="")
        c.create_rectangle(X1 - 22, 320, X1, 415, fill="#1b1f22", outline="")
        c.create_rectangle(SLOT_X, 320, SLOT_X2, 412, fill="#07090a", outline="")
        if self.pan:
            p, m = PAN[self.pan], MAT[self.pan]
            y, h, xa, xb = 356, 18, 560, 770
            col = m.c1                           # a warm pan looks like a cold one
            c.create_rectangle(xa, y, xb, y + h, fill=col, outline="#0b0d0f")
            self._t(c, (xa + xb) / 2, y + h / 2, p.name, "#20242a", 9, "center", True)
            c.create_oval(xb - 23, y - 9, xb - 13, y + 1, fill="#101316", outline="")
            c.create_line(*bez3((xb - 18, y - 4), (860, 340), (920, 300), (964, 300)),
                          fill="#cf4a3d", width=2, smooth=True)
            c.create_line(*bez3((xb - 18, y - 4), (870, 360), (920, 340), (964, 340)),
                          fill="#2a2f34", width=2, smooth=True)
            self._t(c, xb - 18, y - 16, "NTC", "#cf4a3d", 8, "center")
        elif self.stack:
            y = SLOT_Y0
            for k in self.stack:
                m = MAT[k]; y -= 13
                c.create_rectangle(470, y, 870, y + 11, fill=m.c1, outline="#0b0d0f")
                self._t(c, 878, y + 6, m.name, "#6f787f", 8)
            self._t(c, 410, 330, "%d × %s · %s" % (len(self.stack), S("plate"), S("exagg")), "#454d54", 8)
        else:
            self._t(c, (SLOT_X + SLOT_X2) / 2, 366, S("slotempty"), "#3e454b", 9, "center")
        if self.covered:
            c.create_rectangle(366, 180, 966, 204, fill="#191d21", outline="#3a4147")
            self._t(c, 666, 192, "%s — %s" % (S("cover"), S("coveron")), "#6e767d", 8, "center")
        else:
            self._t(c, 666, 192, "%s — %s" % (S("cover"), S("coveroff")), "#7a4a3a", 8, "center")
        for y in (252, 292, 440, 480):
            c.create_line(X0, y, 360, y, fill="#7d858c", width=3)
        self._t(c, 386, 245, S("pinterm"), "#5b646c", 8)

    def _d_cables(self, c):
        for i, (a, b) in enumerate(self.cables):
            pts = bez2(a, b, i)
            c.create_line(*pts, fill="#0b0d0f", width=7, smooth=True, capstyle="round")
            c.create_line(*pts, fill=CCOL[i % len(CCOL)], width=5, smooth=True, capstyle="round")
        def lead(frm, to, col):
            if not to:
                return
            bx, by = TPOS[to]
            c.create_line(*bez3(frm, (frm[0] - 90, frm[1]), (bx + 110, by - 60), (bx, by)),
                          fill="#0b0d0f", width=5, smooth=True)
            c.create_line(*bez3(frm, (frm[0] - 90, frm[1]), (bx + 110, by - 60), (bx, by)),
                          fill=col, width=2, smooth=True)
        lead(ANCH_SCOPE, self.sp, "#e8c33a")
        lead((ANCH_SCOPE[0], ANCH_SCOPE[1] + 22), self.sn, "#2d3339")
        lead(ANCH_DMM, self.dp, "#d24b3d")
        lead((ANCH_DMM[0], ANCH_DMM[1] - 22), self.dn, "#2d3339")
        for (px, py), nm in ((ANCH_SCOPE, "SCOPE"), (ANCH_DMM, "DMM")):
            c.create_rectangle(px - 6, py - 26, px + 16, py + 26, fill="#22272b", outline="#3a4147")
            self._t(c, px + 5, py, nm, "#6e767d", 7, "center")

    def _d_terms(self, c):
        used = set()
        for a, b in self.cables:
            used.add(a); used.add(b)
        for t in (self.sp, self.sn, self.dp, self.dn):
            if t:
                used.add(t)
        for tid, x, y, kind, col, lab in TERM_DEF:
            live = self.term_live(tid)
            fill = ("#b0392c" if col == "r" else "#31373d") if live else "#22262a"
            if kind == "b":
                c.create_oval(x - 11, y - 11, x + 11, y + 11, fill="#0d0f11", outline="")
                c.create_oval(x - 9, y - 9, x + 9, y + 9, fill=fill, outline="")
                c.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#07090a", outline="")
            else:
                c.create_rectangle(x - 8, y - 6, x + 8, y + 6, fill=fill, outline="")
                c.create_rectangle(x - 2, y - 9, x + 2, y + 9, fill="#c9ced2", outline="")
            if tid in used:
                c.create_oval(x - 14, y - 14, x + 14, y + 14, outline="#e8c33a")
            if self.pending == tid:
                c.create_oval(x - 17, y - 17, x + 17, y + 17, outline=PHOS, width=2)
            self._t(c, x, y + 20, lab, "#69727a" if live else "#3a4147", 7, "center")

    # =====================================================================
    # 4.3 계측기 그리기
    # =====================================================================
    def _knob(self, c, kx, ky, r, val, lab, below, sub=""):
        a = -math.pi * .75 + val * math.pi * 1.5
        c.create_oval(kx - r, ky - r, kx + r, ky + r, fill="#4a5157", outline="#2b3137")
        c.create_oval(kx - r * .62, ky - r * .62, kx + r * .62, ky + r * .62, fill="#20252a", outline="")
        c.create_line(kx + math.cos(a) * r * .3, ky + math.sin(a) * r * .3,
                      kx + math.cos(a) * (r - 2), ky + math.sin(a) * (r - 2),
                      fill="#e6eaed", width=2, capstyle="round")
        for i in range(9):
            t = -math.pi * .75 + i / 8.0 * math.pi * 1.5
            c.create_line(kx + math.cos(t) * (r + 3), ky + math.sin(t) * (r + 3),
                          kx + math.cos(t) * (r + 6), ky + math.sin(t) * (r + 6), fill="#8d9298")
        self._t(c, kx, ky + (r + 12 if below else -r - 13), lab, "#4c5258", 7, "center")
        if sub:
            self._t(c, kx, ky + r + 13, sub, "#2a2f34", 8, "center", True)

    def draw_fg(self):
        c = self.fgc
        c.delete("all")
        c.create_rectangle(6, 6, 330, 154, fill="#2b3137", outline="#0e1113")
        c.create_rectangle(14, 14, 322, 146, fill="#e9e6e0", outline="#b9b4ab")
        self._t(c, 22, 28, "FUNCTION GENERATOR", "#5c6167", 8)
        c.create_oval(295, 21, 305, 31, fill="#ff5a4a" if self.fg["on"] else "#5a3733", outline="")
        lo, hi = FRANGE[self.fg["range"]]
        rl = ("%g–%g kHz" % (lo / 1000.0, hi / 1000.0)) if hi >= 1000 else ("%d–%d Hz" % (lo, hi))
        for key, kx, ky, r, lab, below in KNOBS:
            if key == "range":
                self._knob(c, kx, ky, r, (self.fg["range"] + .5) / 4.0, lab, below, rl)
            elif key == "wave":
                self._knob(c, kx, ky, r, 1 / 6.0, lab, below, "SINE")
            elif key == "amp":
                self._knob(c, kx, ky, r, self.fg["amp"] / 100.0, lab, below, "%d %%" % self.fg["amp"])
            else:
                self._knob(c, kx, ky, r, self.fg[key] / 100.0, lab, below)
        for cy, col in ((74, "#b0392c"), (114, "#31373d")):
            c.create_oval(289, cy - 11, 311, cy + 11, fill="#0d0f11", outline="")
            c.create_oval(291, cy - 9, 309, cy + 9, fill=col, outline="")
        self._t(c, 300, 136, "OUTPUT", "#5c6167", 7, "center")

    SCRX, SCRY, SCRW, SCRH = 26, 22, 284, 168

    def scope_signal(self):
        f = self.freq()
        if not self.sp or not self.sn or not self.term_live(self.sp) or not self.term_live(self.sn):
            return {"off": True, "amp": 0.0, "f": 0.0}
        a = self.sol.amp(self.sp, self.sn) if (self.sol and self.fg["on"]) else 0.0
        return {"off": False, "amp": a * self.probe_x, "f": f}

    def refresh_disp(self, force=False):
        now = time.time()
        if not force and now - self.disp["t"] < 0.24:
            return
        self.disp["t"] = now
        s = self.scope_signal()
        vd = VDIV[self.vi]
        v, clip = s["amp"], s["amp"] > 4 * vd
        if clip:
            v = 4 * vd
        v = sig3(v * (1 + 0.004 * random.gauss(0, 1)) + 0.0025 * vd * random.gauss(0, 1))
        self.disp.update(v=max(0.0, v), clip=clip, off=s["off"],
                         f=(s["f"] * (1 + 0.0015 * random.gauss(0, 1))) if s["amp"] > 0.04 * vd else 0.0)
        if self.mode == "DMM" and self.dmm_fn == "R":
            live = live_terms(self.pstate()) if self.fg["on"] else set()
            if self.dp in live or self.dn in live:
                self.disp["r"] = -1
            elif not self.dp or not self.dn or not self.term_live(self.dp) or not self.term_live(self.dn):
                self.disp["r"] = float("inf")
            else:
                R = measure_r(self.pstate(), self.dp, self.dn)
                self.disp["r"] = (max(0.0, sig3(R * (1 + 0.002 * random.gauss(0, 1))
                                                + 0.004 * random.gauss(0, 1)))
                                  if math.isfinite(R) else float("inf"))

    def dmm_acv(self):
        f = self.freq()
        if not self.dp or not self.dn or not self.term_live(self.dp) or not self.term_live(self.dn) \
                or not self.fg["on"]:
            return "0.000 V", ""
        if f < 40 or f > 1000:
            return "- - -", S("dmmfreq")
        r = analyze(self.pstate(), f)
        return "%.4f V" % (r.amp(self.dp, self.dn) / math.sqrt(2)), ""

    def draw_scope(self):
        c = self.osc
        c.delete("all")
        X, Y, W, H = self.SCRX, self.SCRY, self.SCRW, self.SCRH
        c.create_rectangle(2, 2, 334, 246, fill="#b9382c", outline="")
        c.create_rectangle(12, 6, 324, 242, fill="#22272c", outline="#0e1113")
        c.create_rectangle(4, 60, 16, 180, fill="#8e1f16", outline="")
        c.create_rectangle(320, 60, 332, 180, fill="#8e1f16", outline="")
        self._t(c, 26, 14, "ZOYI  ZT-702S   DIGITAL OSCILLOSCOPE", "#dfe3e6", 7, "w", True)
        c.create_rectangle(X - 3, Y - 3, X + W + 3, Y + H + 3, fill="#05070a", outline="")
        self.refresh_disp()

        if self.mode == "DMM":
            c.create_rectangle(X, Y, X + W, Y + H, fill="#0a1a12", outline="")
            self._t(c, X + 10, Y + 16, "RESISTANCE" if self.dmm_fn == "R" else "AC VOLTAGE", "#5d7d6d", 8)
            if self.dmm_fn == "R":
                big, warn = fmt_r(self.disp["r"]), (S("dmmlive") if self.disp["r"] == -1 else "")
            else:
                big, warn = self.dmm_acv()
            c.create_text(X + W / 2, Y + 72, text=big, fill=PHOS, anchor="center",
                          font=pick_font(["Consolas", "DejaVu Sans Mono"], 20, "bold"))
            self._t(c, X + W / 2, Y + 112, warn, "#d78a6a", 8, "center")
            self._t(c, X + W / 2, Y + 148, "MULTIMETER  ·  %s ↔ %s" % (self.dp or "—", self.dn or "—"),
                    "#4d6b5c", 8, "center")
        else:
            c.create_rectangle(X, Y, X + W, Y + H, fill="#04120c", outline="")
            dx, dy = W / 10.0, H / 8.0
            for i in range(1, 10):
                c.create_line(X + i * dx, Y, X + i * dx, Y + H, fill="#1a3a2a")
            for i in range(1, 8):
                c.create_line(X, Y + i * dy, X + W, Y + i * dy, fill="#1a3a2a")
            c.create_line(X, Y + H / 2, X + W, Y + H / 2, fill="#2c5f45")
            c.create_line(X + W / 2, Y, X + W / 2, Y + H, fill="#2c5f45")
            s = self.held if (self.hold and self.held) else self.scope_signal()
            vd, td, cy = VDIV[self.vi], TDIV[self.ti], Y + H / 2
            A, per = s["amp"] / vd * dy, td * 10
            pts = []
            for i in range(0, int(W) + 1, 2):
                t = (i / W) * per
                v = (math.sin(2 * math.pi * s["f"] * t) * A) if s["amp"] else 0.0
                v += (random.random() - .5) * (0.6 if s["off"] else 1.1)
                yy = min(max(cy - v, Y + 1), Y + H - 1)
                pts += [X + i, yy]
            c.create_line(*pts, fill=PHOS, width=1)
            c.create_rectangle(X, Y, X + W, Y + 13, fill="#02100a", outline="")
            c.create_rectangle(X, Y + H - 15, X + W, Y + H, fill="#02100a", outline="")
            self._t(c, X + 5, Y + 7, "%s  AC   %s/div   %s/div" % (
                "10X" if self.probe_x == 10 else "1X",
                ("%g V" % vd) if vd >= 1 else ("%g mV" % (vd * 1000)), fmt_t(td)), "#9fe8c4", 8)
            if self.hold:
                self._t(c, X + W - 5, Y + 7, "HOLD", AMBER, 8, "e")
            self._t(c, X + 5, Y + H - 7, "Vmax %s%s" % (">" if self.disp["clip"] else "", fmt_v(self.disp["v"])),
                    "#ff8b6a" if self.disp["clip"] else PHOS, 9, "w", True)
            self._t(c, X + 118, Y + H - 7, "Vpp %s" % fmt_v(self.disp["v"] * 2), PHOS, 9, "w", True)
            self._t(c, X + 202, Y + H - 7, "F %s" % fmt_f(self.disp["f"]), PHOS, 9, "w", True)
            if self.disp["off"]:
                self._t(c, X + W / 2, Y + 26, S("probeoff"), "#5d7d6d", 8, "center")
        yk = Y + H + 12
        for i, s2 in enumerate(("F1", "F2", "F3", "F4")):
            c.create_rectangle(30 + i * 46, yk, 68 + i * 46, yk + 15, fill="#3a4147", outline="")
            self._t(c, 49 + i * 46, yk + 8, s2, "#aab2b8", 7, "center")
        c.create_rectangle(222, yk, 262, yk + 15, fill="#b9382c", outline="")
        self._t(c, 242, yk + 8, "MODE", "#ffffff", 7, "center")
        c.create_rectangle(268, yk, 308, yk + 15, fill="#3a4147", outline="")
        self._t(c, 288, yk + 8, "HOLD", "#aab2b8", 7, "center")
        c.create_rectangle(30, yk + 22, 306, yk + 42, fill="#2b3035", outline="")
        self._t(c, 168, yk + 32, "▲ ▼ ◀ ▶   MENU   AUTO   10A  mA  COM  VΩ", "#6e767d", 7, "center")

    # =====================================================================
    # 4.4 조작
    # =====================================================================
    def set_tool(self, k):
        self.tool, self.pending = k, None
        for key, b in self.toolbtn.items():
            on = (key == k)
            b.configure(bg=AMBER if on else "#22272b", fg="#161616" if on else DIM)
        self.hint.configure(text=S("h_cable") if k == "cable" else
                            S("h_erase") if k == "erase" else
                            S("h_probe") if k.startswith("probe") else S("h_dmm"))
        self.draw_bench()

    def hit_term(self, x, y):
        best, bd = None, 18
        for tid, tx, ty, _, _, _ in TERM_DEF:
            if not self.term_live(tid):
                continue
            d = math.hypot(tx - x, ty - y)
            if d < bd:
                bd, best = d, tid
        return best

    def hit_cable(self, x, y):
        for i, (a, b) in enumerate(self.cables):
            p = bez2(a, b, i)
            for j in range(0, len(p), 2):
                if math.hypot(p[j] - x, p[j + 1] - y) < 9:
                    return i
        return -1

    def on_bench_click(self, e):
        ex = (e.x - self.box) / self.bscale
        ey = (e.y - self.boy) / self.bscale
        t = self.hit_term(ex, ey)
        if self.tool == "erase":
            i = self.hit_cable(ex, ey)
            if i >= 0:
                self.cables.pop(i)
            elif t:
                self.cables = [c for c in self.cables if t not in c]
                for a in ("sp", "sn", "dp", "dn"):
                    if getattr(self, a) == t:
                        setattr(self, a, None)
        elif self.tool == "cable":
            if not t:
                self.pending = None
            elif not self.pending:
                self.pending = t
            elif self.pending == t:
                self.pending = None
            else:
                pair = (self.pending, t)
                if not any(set(c) == set(pair) for c in self.cables):
                    if len(self.cables) >= 8:
                        self.flash(S("maxcable"))
                    else:
                        self.cables.append(pair)
                self.pending = None
        elif t:
            a = {"probeP": "sp", "probeN": "sn", "dmmP": "dp", "dmmN": "dn"}[self.tool]
            setattr(self, a, None if getattr(self, a) == t else t)
        self.solve(); self.draw_bench()

    def set_cap(self, k):
        self.cap = None if self.cap == k else k
        self._build_tray(); self.solve(); self.draw_bench()

    def add_plate(self, k):
        self.stack.append(k)
        self._build_tray(); self.solve(); self.draw_bench()

    def set_pan(self, k):
        self.pan = None if self.pan == k else k
        self.panT = T_AMB
        if self.pan:
            self.stack = []
        self._build_tray(); self.solve(); self.draw_bench()

    def clear_slot(self):
        self.stack, self.pan = [], None
        self._build_tray(); self.solve(); self.draw_bench()

    def toggle_cover(self):
        self.covered = not self.covered
        self._build_tray(); self.draw_bench()

    def toggle_out(self):
        self.fg["on"] = not self.fg["on"]
        self.refresh_buttons(); self.solve(); self.draw_bench(); self.draw_fg()

    def bump(self, key, d):
        self.fg[key] = max(0.0, min(100.0, self.fg[key] + d))
        self.draw_fg(); self.draw_bench()

    def next_range(self):
        self.fg["range"] = (self.fg["range"] + 1) % 4
        self.draw_fg(); self.draw_bench()

    def toggle_mode(self):
        self.mode = "DMM" if self.mode == "SCOPE" else "SCOPE"
        self.refresh_buttons(); self.refresh_disp(True)

    def toggle_hold(self):
        self.hold = not self.hold
        self.held = self.scope_signal() if self.hold else None
        self.refresh_buttons()

    def toggle_px(self):
        self.probe_x = 10 if self.probe_x == 1 else 1
        self.refresh_buttons(); self.refresh_disp(True)

    def bump_scale(self, which, d):
        if which == "v":
            self.vi = max(0, min(len(VDIV) - 1, self.vi + d))
        else:
            self.ti = max(0, min(len(TDIV) - 1, self.ti + d))
        self.refresh_disp(True)

    def set_dmm(self, fn):
        self.dmm_fn = fn
        self.mode = "DMM"
        self.refresh_buttons(); self.refresh_disp(True)

    def unclip_probe(self):
        self.sp = self.sn = None
        self.solve(); self.draw_bench()

    def unclip_dmm(self):
        self.dp = self.dn = None
        self.solve(); self.draw_bench()

    def auto_set(self):
        s = self.scope_signal()
        if s["amp"] > 0:
            self.vi = len(VDIV) - 1
            for i, v in enumerate(VDIV):
                if s["amp"] / v <= 3.2:
                    self.vi = i; break
            self.ti = len(TDIV) - 1
            for i, t in enumerate(TDIV):
                if t * 10 >= 3.0 / s["f"]:
                    self.ti = i; break
        self.refresh_disp(True)

    def fg_pos(self, e):
        return e.x, e.y

    def fg_down(self, e):
        for key, kx, ky, r, lab, below in KNOBS:
            if math.hypot(kx - e.x, ky - e.y) < r + 4:
                if key == "range":
                    self.next_range()
                elif key == "wave":
                    self.flash(S("wave"))
                else:
                    self.drag = (key, e.y, self.fg[key])
                return

    def fg_move(self, e):
        if not self.drag:
            return
        key, y0, v0 = self.drag
        self.fg[key] = max(0.0, min(100.0, v0 + (y0 - e.y) * 0.45))
        self.draw_fg(); self.draw_bench()

    def fg_wheel(self, e, direction=None):
        d = direction if direction is not None else (1 if e.delta > 0 else -1)
        for key, kx, ky, r, lab, below in KNOBS:
            if math.hypot(kx - e.x, ky - e.y) < r + 4 and key not in ("range", "wave"):
                self.fg[key] = max(0.0, min(100.0, self.fg[key] + d))
                self.draw_fg(); self.draw_bench()
                return

    # ---- 스톱워치 · 기록 ----
    def sw_toggle(self):
        self.sw_run = not self.sw_run

    def sw_lap(self):
        self.laps = ([self.sw_t] + self.laps)[:6]
        self.lapl.configure(text="\n".join("L%d  %.1f s" % (len(self.laps) - i, t)
                                           for i, t in enumerate(self.laps)))

    def sw_reset(self):
        self.sw_t, self.laps = 0.0, []
        self.lapl.configure(text="")

    def setup_text(self):
        p = []
        if self.cap:
            p.append("C=" + CAPS[self.cap][2])
        if self.stack:
            p.append("N=%d×%s" % (len(self.stack), MAT[self.stack[0]].key))
        if self.pan:
            p.append(PAN[self.pan].key + " pan")
        p.append("probe %s/%s" % (self.sp or "—", self.sn or "—"))
        if not self.covered:
            p.append("lid open")
        return ", ".join(p)

    def log_current(self):
        nm = self.noteName.get().strip() or (
            ("R" if self.dmm_fn == "R" else "V(AC)") if self.mode == "DMM" else "Vmax")
        if self.mode == "DMM":
            val = fmt_r(self.disp["r"]) if self.dmm_fn == "R" else self.dmm_acv()[0]
            fr = fmt_f(self.freq()) if self.fg["on"] else "—"
        else:
            val = fmt_v(self.disp["v"]) + (" (clip)" if self.disp["clip"] else "")
            fr = fmt_f(self.disp["f"])
        self.nno += 1
        row = (self.nno, "%.1f" % self.sw_t, nm, val, fr, self.setup_text())
        self.notes.append(row)
        self.tree.insert("", 0, values=row)
        self.flash("%s · %s = %s" % (S("logged"), nm, val))

    def clear_notes(self):
        self.notes = []
        for i in self.tree.get_children():
            self.tree.delete(i)

    def save_csv(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")],
                                            initialfile="apho2025_Q1_log.csv")
        if not path:
            return
        with open(path, "w", encoding="utf-8-sig") as fh:
            fh.write("no,time_s,item,value,frequency,conditions\n")
            for r in self.notes:
                fh.write("%d,%s,%s,%s,%s,\"%s\"\n" % r)
        self.flash("%s · %s" % (S("saved"), path))

    # =====================================================================
    # 4.5 루프
    # =====================================================================
    def tick(self):
        now = time.time()
        dt = min(0.25, now - self.last) * self.speed
        self.last = now
        self.solve()
        if self.pan:
            Irms = (abs(self.sol.I1) + abs(self.sol.I2)) / math.sqrt(2) if self.sol else 0.0
            n = max(1, int(math.ceil(dt / 0.5)))
            for _ in range(n):
                self.panT = thermal_step(self.pan, self.panT, Irms, self.freq(), dt / n, not self.covered)
        if self.sw_run:
            self.sw_t += dt
        self.swlbl.configure(text="%02d:%04.1f" % (int(self.sw_t // 60), self.sw_t % 60))
        Ipk = (abs(self.sol.I1) + abs(self.sol.I2)) if self.sol else 0.0
        msg = ""
        if self.fg["on"] and not self.cap and Ipk > 0.05:
            msg = S("nocap")
        elif Ipk > 2.0:
            msg = S("ovr")            # the coil warms up; the current itself is for you to measure
        if now < self.msg_until:
            self.warn.configure(text=self.msg, fg=PHOS)
        else:
            self.warn.configure(text=msg, fg="#f0a79f")
        self.draw_scope()
        self.after(120, self.tick)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
