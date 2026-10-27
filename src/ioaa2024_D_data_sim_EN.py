#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  International Olympiad on Astronomy and Astrophysics 2024  (Vassouras)
  Data Analysis Examination
     D1  Photometric Comparison of Surveys
     D2  The Shapley Hypothesis
  Virtual examination desk
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    What a data-analysis round puts on the table and nothing more: the
    examination's tables (in the worksheet), semi-log graph paper with
    three decades for Graph 1, millimetre paper for Graph 2 and the
    histograms, a scientific calculator and a worksheet.  The student
    chooses the axis scales, plots the values they worked out (with error
    bars) and rules lines by hand: nothing is fitted, matched or sorted.
    The official answers, and a check of the typed answers against the
    official accepted ranges, are shown only on request.

    Run:   python3 ioaa2024_D_data_sim_EN.py
"""
import ast
import json
import math
import os
import re
import tkinter as tk
from tkinter import messagebox

APP_VERSION = "1.0"
LANG = "EN"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "KO" else en


SAVE = os.path.join(os.path.expanduser("~"), ".haslalab_ioaa2024_D.json")

# ======================================================================
#   THE PROBLEMS
# ======================================================================
T1 = [(1, 0.047255, 0.000406, 21.7649, 0.0120), (2, 0.064741, 0.021568, 21.1111, 0.0067), (3, 0.064911, 0.026395, 21.3931, 0.0084), (4, 0.098343, 0.054871, 21.3934, 0.0088),
      (5, 0.022256, 0.039129, 21.9933, 0.0157), (6, 0.006188, 0.066928, 21.5490, 0.0088), (7, 0.083945, 0.074259, 21.9395, 0.0126), (8, 0.076715, 0.079496, 21.4808, 0.0089),
      (9, 0.057422, 0.076006, 21.8897, 0.0127), (10, 0.024412, 0.087688, 21.8341, 0.0126), (11, 0.044723, 0.091782, 21.8868, 0.0172), (12, 0.071089, 0.091053, 21.4390, 0.0098)]
T2 = [(1, 0.006167, 0.066874, 21.9020, 0.0576), (2, 0.018660, 0.007450, 21.8039, 0.0529), (3, 0.047853, 0.061487, 21.3007, 0.0418), (4, 0.050870, 0.015659, 21.1678, 0.0388),
      (5, 0.051270, 0.020812, 21.2524, 0.0401), (6, 0.057414, 0.075999, 21.8884, 0.0578), (7, 0.064745, 0.021583, 21.3634, 0.0422), (8, 0.064910, 0.026419, 21.6428, 0.0488),
      (9, 0.071102, 0.091058, 21.9259, 0.0751), (10, 0.074946, 0.002792, 21.3258, 0.0410), (11, 0.076709, 0.079474, 21.5303, 0.0476), (12, 0.092635, 0.077395, 21.6995, 0.0513),
      (13, 0.098343, 0.054854, 21.6542, 0.0499), (14, 0.099332, 0.093711, 21.8802, 0.0577)]
GC = [("NGC 6522", 1.025, -3.926, 14.3), ("NGC 6401", 3.450, 3.980, 14.4), ("NGC 6342", 4.898, 9.725, 14.5), ("NGC 6553", 5.253, -3.029, 13.6), ("NGC 6440", 7.729, 3.801, 14.6),
      ("Ter 12", 8.358, -2.101, 13.6), ("VVV-CL160", 10.151, 0.302, 14.2), ("2MASS-GC01", 10.471, 0.100, 12.6), ("NGC 6517", 19.225, 6.762, 14.8), ("NGC 6402", 21.324, 14.804, 14.8),
      ("NGC 6712", 25.354, -4.318, 14.3), ("NGC 6426", 28.087, 16.234, 16.6), ("NGC 5466", 42.150, 73.592, 16.0), ("NGC 7089", 53.371, -35.770, 15.3), ("NGC 288", 151.285, -89.380, 14.8),
      ("NGC 2298", 245.629, -16.006, 15.0), ("NGC 4590", 299.626, 36.051, 15.1), ("NGC 4372", 300.993, -9.884, 13.8), ("NGC 362", 301.533, -46.247, 14.7), ("BH 140", 303.171, -4.307, 13.4),
      ("NGC 5927", 326.604, 4.860, 14.6), ("Patchick 126", 340.381, -3.826, 14.5), ("NGC 5897", 342.946, 30.294, 15.5), ("NGC 6380", 350.182, -3.422, 14.9), ("Djor 1", 356.675, -2.484, 15.0)]
MATCH = {3: 8, 9: 6, 4: 13, 6: 1, 12: 9, 2: 7, 8: 11}      # ID1 -> ID2, official solution
STAR = lambda r: [str(r[0]), "%.6f" % r[1], "%.6f" % r[2], "%.4f" % r[3], "%.4f" % r[4]]

TASKS = [
    {"id": "D1", "marks": 75, "name": T("서베이 간 측광 비교", "Photometric Comparison of Surveys"),
     "text": T(
         "SDSS(2.5 m, 미국 아파치 포인트, 2000년대)와 DES(4 m, 칠레 세로 톨롤로, 2013–2019)는 적도 지역 ‘스트라이프 82’를 함께 관측했습니다. "
         "파일 이름이 뒤섞여 두 표가 어느 서베이 것인지 모릅니다. 두 서베이는 검출기 응답, 노출 시간, 관측지 조건이 같다고 가정합니다. "
         "표 1(12개)과 표 2(14개)의 ID, RA, Dec(°), m_g, err m_g는 계산표에 있습니다.\n\n"
         "(a) [5] 표 1과 표 2는 각각 어느 서베이(SDSS 또는 DES)의 것인가?\n\n"
         "(b) [35] 그래프 1(반로그)에 x축 m_g(선형), y축 err m_g(로그)로 두 자료를 그리고, 각 자료의 기울기 A와 y절편 B를 어림하라 "
         "(log₁₀ err m_g = A·m_g + B). 오차는 구하지 않아도 된다.\n\n"
         "(c) [5] S/N ≈ 1/err m_g일 때 (b)의 맞춤으로 m_g = 21.5에서 각 서베이의 S/N.\n\n"
         "(d) [15] 서로 1″ 안에 있는 천체는 같은 천체다. 공통 천체를 찾아 ID₁–ID₂ 짝의 표를 만들어라.\n\n"
         "(e) [15] (d)의 짝으로 그래프 2(밀리미터)에 x축 표 1, y축 표 2의 m_g를 그리고, 두 방향 모두 2·err m_g(2σ) 오차 막대를 그려라. "
         "두 서베이 사이 측광 보정에 알맞은 별을 표 1의 ID로 써라.",
         "SDSS (2.5 m, Apache Point, USA, 2000s) and DES (4 m, Cerro Tololo, Chile, 2013–2019) both covered the equatorial region Stripe 82. "
         "The file names were scrambled, so you cannot tell which table belongs to which survey. Assume the surveys are equivalent in detector response, "
         "exposure times and site characteristics. ID, RA, Dec (°), m_g and err m_g of Table 1 (12 objects) and Table 2 (14) are in the worksheet.\n\n"
         "(a) [5] Which survey (SDSS or DES) is Table 1 and which is Table 2?\n\n"
         "(b) [35] On Graph 1 (semi-log) plot m_g on the x-axis (linear) and err m_g on the y-axis (logarithmic) and estimate the slope A and intercept B "
         "for each dataset (log₁₀ err m_g = A·m_g + B). No uncertainties are needed.\n\n"
         "(c) [5] With S/N ≈ 1/err m_g, use the fits from (b) to find the S/N of each survey at m_g = 21.5.\n\n"
         "(d) [15] Objects within 1″ of each other are the same object. Identify the objects in common and write a table of matching IDs, ID₁ and ID₂.\n\n"
         "(e) [15] Using the matches from (d), plot m_g of Table 1 (x) against Table 2 (y) on Graph 2 (millimetre) with error bars of 2·err m_g (2σ) "
         "in both directions. Identify the stars suitable for photometric calibration between the surveys (IDs from Table 1)."),
     "sheets": ["g1", "g2"],
     "table": [[T("표 1 ID₁", "Table 1 ID₁"), "RA (°)", "Dec (°)", "m_g", "err m_g", "", ""]] + [STAR(r) for r in T1] + [[]]
              + [[T("표 2 ID₂", "Table 2 ID₂"), "RA (°)", "Dec (°)", "m_g", "err m_g"]] + [STAR(r) for r in T2] + [[]]
              + [["ID₁", "ID₂", "m_g,1", "err₁", "m_g,2", "err₂", "Δ (″)"]],
     "fields": [T("(a) 표 1은", "(a) Table 1 is"), "(b) A SDSS", "(b) B SDSS", "(b) A DES", "(b) B DES", "(c) S/N SDSS", "(c) S/N DES",
                T("(d) 짝 3-8, …", "(d) pairs 3-8, …"), T("(e) 보정용 별", "(e) calibration")],
     "check": {"(b) A SDSS": (0.2502, 0.3058), "(b) B SDSS": (-8.0419, -6.5797), "(b) A DES": (0.3657, 0.4470), "(b) B DES": (-11.2977, -10.2217),
               "(c) S/N SDSS": (19.8, 24.2), "(c) S/N DES": (95.4, 116.6)},
     "key": T("(a) 표 1 = DES, 표 2 = SDSS. 어두운 별일수록 오차가 큰데 표 2의 오차가 훨씬 크므로 작은 망원경(2.5 m)의 SDSS.\n"
              "(b) SDSS: A = 0.2780 (0.2502–0.3058), B = −7.3108 (−8.0419 – −6.5797);  DES: A = 0.4063 (0.3657–0.4470), B = −10.7597 (−11.2977 – −10.2217)\n"
              "(c) SDSS err = 0.0464 → S/N ≈ 22 (19.8–24.2);  DES err = 0.0095 → S/N ≈ 106 (95.4–116.6)\n"
              "(d) 3–8, 9–6, 4–13, 6–1, 12–9, 2–7, 8–11 (ID₁–ID₂, 떨어진 거리 0.04″–0.21″)\n"
              "(e) x = y 선에 가장 가까운 별: 영점 차이 없이 보정하면 8, 9;  영점 차이를 두고 보정하면 2, 3, 4, 6",
              "(a) Table 1 = DES, Table 2 = SDSS. Fainter stars have larger errors, and Table 2's are far larger, so it is the smaller (2.5 m) SDSS.\n"
              "(b) SDSS: A = 0.2780 (0.2502–0.3058), B = −7.3108 (−8.0419 – −6.5797);  DES: A = 0.4063 (0.3657–0.4470), B = −10.7597 (−11.2977 – −10.2217)\n"
              "(c) SDSS err = 0.0464 → S/N ≈ 22 (19.8–24.2);  DES err = 0.0095 → S/N ≈ 106 (95.4–116.6)\n"
              "(d) 3–8, 9–6, 4–13, 6–1, 12–9, 2–7, 8–11 (ID₁–ID₂, separations 0.04″–0.21″)\n"
              "(e) Stars closest to a one-to-one line: with zero offset 8 and 9;  with a non-zero offset 2, 3, 4 and 6")},
    {"id": "D2", "marks": 75, "name": T("섀플리 가설", "The Shapley Hypothesis"),
     "text": T(
         "약 100년 전 섀플리는 구상 성단이 은하 중심 둘레에 대칭으로 퍼져 있다고 보고 태양에서 은하 중심까지의 거리를 구했다. "
         "구상 성단 25개의 은하 경도 l, 은하 위도 b, 소광을 보정한 거리 지수 DM은 계산표에 있다.\n\n"
         "(a) [25] 각 성단의 태양으로부터의 거리(pc)와 직교 좌표 (x, y, z). x축은 은하 중심 쪽, y축은 은하 회전 방향, 오른손 좌표계.\n\n"
         "(b) [15] 태양에서 구상 성단 분포의 중심까지 거리 D와 그 불확도 δD.\n\n"
         "(c) [30] x, y, z 분포마다 구간 다섯 개짜리 히스토그램(자료를 정렬해 같은 폭 구간 다섯 개)을 그리고 사분위수 Q₁, Q₂, Q₃를 실선으로 표시하라.\n\n"
         "(d) [5] 대칭 인자 Φ = |Q₁ + Q₃ − 2Q₂| / (Q₃ − Q₁)를 세 분포에 대해 구하고 분류하라(Φ ≤ 0.1 대칭, ≤ 0.2 준대칭, > 0.2 비대칭). "
         "섀플리 가설을 따르면 T, 아니면 F.",
         "About 100 years ago Shapley took the globular clusters to be spread symmetrically about the Galactic centre and found the Sun's distance from it. "
         "The Galactic longitude l, latitude b and extinction-corrected distance modulus DM of 25 globular clusters are in the worksheet.\n\n"
         "(a) [25] The distance (pc) of each cluster from the Sun and its Cartesian coordinates (x, y, z): x towards the Galactic centre, y in the direction "
         "of Galactic rotation, a right-handed system.\n\n"
         "(b) [15] The distance D from the Sun to the centre of the distribution, and its uncertainty δD.\n\n"
         "(c) [30] For each of x, y and z make a histogram with five bins (sort the data, five bins of equal width) and mark the quartiles Q₁, Q₂, Q₃ with solid lines.\n\n"
         "(d) [5] Find the symmetry factor Φ = |Q₁ + Q₃ − 2Q₂| / (Q₃ − Q₁) for the three distributions and classify them (Φ ≤ 0.1 symmetrical, ≤ 0.2 "
         "quasi-symmetrical, > 0.2 asymmetrical). T if they follow Shapley's hypothesis, F if not."),
     "sheets": ["h"],
     "table": [["Name", "l (°)", "b (°)", "DM", "d (pc)", "x (pc)", "y (pc)", "z (pc)"]] + [[r[0], "%.3f" % r[1], "%.3f" % r[2], "%.1f" % r[3]] for r in GC],
     "fields": ["(b) D (pc)", "(b) δD (pc)", "(d) Φx", "(d) Φy", "(d) Φz", "(d) T/F"],
     "check": {"(b) D (pc)": (5600, 6800), "(b) δD (pc)": (650, 1000), "(d) Φx": (0.39, 0.47), "(d) Φy": (0.38, 0.46), "(d) Φz": (0.53, 0.65), "(d) T/F": ("F",)},
     "key": T("(a) d = 10^((DM+5)/5) pc, x = d cos l cos b, y = d sin l cos b, z = d sin b.  예: NGC 6522 d = 7244 pc, (7226, 129, −496);  NGC 6426 d = 20893 pc, (17698, 9444, 5841)\n"
              "(b) x̄ = 6164.1, ȳ = −321.3, z̄ = 434.3 pc;  σ = 4057.7, 4196.4, 4682.6 pc;  σ/√N = 811.5, 839.3, 936.5 pc  →  D = √(x̄² + ȳ² + z̄²) = 6188 pc, δD = 812 pc "
              "(✓ 범위 ±10%·±20%는 HaslaLab이 둔 것)\n"
              "(c) 사분위수 x: 3287.7, 6809.9, 8218.8 pc;  y: −3591.5, 455.4, 2100.7 pc;  z: −557.7, −192.4, 1207.8 pc\n"
              "(d) Φx = 0.429, Φy = 0.422, Φz = 0.588 — 셋 다 비대칭이므로 F",
              "(a) d = 10^((DM+5)/5) pc, x = d cos l cos b, y = d sin l cos b, z = d sin b.  E.g. NGC 6522 d = 7244 pc, (7226, 129, −496);  NGC 6426 d = 20893 pc, (17698, 9444, 5841)\n"
              "(b) x̄ = 6164.1, ȳ = −321.3, z̄ = 434.3 pc;  σ = 4057.7, 4196.4, 4682.6 pc;  σ/√N = 811.5, 839.3, 936.5 pc  →  D = √(x̄² + ȳ² + z̄²) = 6188 pc, δD = 812 pc "
              "(the ✓ ranges, ±10% and ±20%, are HaslaLab's)\n"
              "(c) Quartiles x: 3287.7, 6809.9, 8218.8 pc;  y: −3591.5, 455.4, 2100.7 pc;  z: −557.7, −192.4, 1207.8 pc\n"
              "(d) Φx = 0.429, Φy = 0.422, Φz = 0.588 — all asymmetrical, so F")},
]
SHEETS = {
    "g1": {"paper": (180, 240), "logy": 3, "name": T("그래프 1 (반로그)", "Graph 1 (semi-log)")},
    "g2": {"paper": (180, 200), "name": T("그래프 2 (밀리미터)", "Graph 2 (millimetre)")},
    "h": {"paper": (180, 250), "name": T("D2 (c) 히스토그램", "D2 (c) histograms")},
}
PX = 4          # paper pixels per mm (native)
TOOLS = [("pen", "∿"), ("line", "／"), ("dot", "•"), ("circle", "○"), ("cross", "×"), ("plus", "+"), ("text", T("글자", "Text")), ("erase", T("지우개", "Eraser"))]


def num(s):
    try:
        return float(str(s).replace(",", ".").replace("−", "-"))
    except ValueError:
        return None


def fmt(v):
    if not math.isfinite(v):
        return "—"
    a = abs(v)
    return "%.4e" % v if a and (a < 1e-3 or a >= 1e5) else ("%.6g" % v)


# ======================================================================
#   CALCULATOR  (a small expression evaluator, no eval)
# ======================================================================
class Calc:
    def __init__(self):
        self.deg = True
        self.ans = 0.0

    def run(self, src):
        s = src.replace("×", "*").replace("÷", "/").replace("−", "-").replace("^", "**").replace("π", "pi")
        node = ast.parse(s, mode="eval")
        v = self.ev(node.body)
        self.ans = v
        return v

    def ev(self, n):
        d = self.deg
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.Name):
            return {"pi": math.pi, "e": math.e, "Ans": self.ans}[n.id]
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            v = self.ev(n.operand)
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.BinOp):
            a, b = self.ev(n.left), self.ev(n.right)
            ops = {ast.Add: lambda: a + b, ast.Sub: lambda: a - b, ast.Mult: lambda: a * b, ast.Div: lambda: a / b, ast.Pow: lambda: a ** b}
            return ops[type(n.op)]()
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and len(n.args) == 1:
            x = self.ev(n.args[0])
            r = (lambda t: t * math.pi / 180) if d else (lambda t: t)
            f = (lambda t: t * 180 / math.pi) if d else (lambda t: t)
            fn = {"sin": lambda: math.sin(r(x)), "cos": lambda: math.cos(r(x)), "tan": lambda: math.tan(r(x)), "asin": lambda: f(math.asin(x)),
                  "acos": lambda: f(math.acos(x)), "atan": lambda: f(math.atan(x)), "sqrt": lambda: math.sqrt(x), "ln": lambda: math.log(x),
                  "log": lambda: math.log10(x), "exp": lambda: math.exp(x), "abs": lambda: abs(x)}
            return fn[n.func.id]()
        raise ValueError


# ======================================================================
#   THE DESK
# ======================================================================
class App:
    def __init__(self, root):
        self.root = root
        root.title(T("IOAA 2024 자료 분석 시험 — D1 서베이 측광 비교 · D2 섀플리 가설 · HaslaLab", "IOAA 2024 data analysis — D1 Photometric comparison · D2 Shapley hypothesis · HaslaLab"))
        root.configure(bg="#1c2027")
        root.geometry("1560x940")
        self.data = self.load()
        self.task = TASKS[0]
        self.sheet = "g1"
        self.tool = "pen"
        self.col = "#111111"
        self.drag = None
        self.undo = []
        self.imgs = {}
        self.calc = Calc()
        left = tk.Frame(root, bg="#22262d", width=400)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)
        right = tk.Frame(root, bg="#22262d", width=320)
        right.pack(side="right", fill="y", padx=(5, 10), pady=10)
        right.pack_propagate(False)
        mid = tk.Frame(root, bg="#1c2027")
        mid.pack(side="left", fill="both", expand=True, pady=10)
        tb = tk.Frame(left, bg="#22262d")
        tb.pack(fill="x", padx=8, pady=8)
        self.tbtn = {}
        for t in TASKS:
            b = tk.Button(tb, text=t["id"], command=lambda t=t: self.set_task(t), bg="#2b2f36", fg="#e8eef2", relief="flat", font=("Segoe UI", 10, "bold"), padx=10)
            b.pack(side="left", padx=2)
            self.tbtn[t["id"]] = b
        tk.Button(tb, text=T("계산표", "Worksheet"), command=self.worksheet, bg="#2b2f36", fg="#e8eef2", relief="flat").pack(side="right")
        self.qtext = tk.Text(left, wrap="word", bg="#12161b", fg="#d6dde2", relief="flat", font=("Malgun Gothic", 10), padx=10, pady=8)
        self.qtext.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.qtext.tag_configure("h", foreground="#f2c14e", font=("Malgun Gothic", 11, "bold"))
        self.sbar = tk.Frame(mid, bg="#1c2027")
        self.sbar.pack(fill="x")
        bar = tk.Frame(mid, bg="#1c2027")
        bar.pack(fill="x", pady=3)
        self.toolbtn = {}
        for k, lab in TOOLS:
            b = tk.Button(bar, text=lab, width=3 if len(lab) < 3 else 5, command=lambda k=k: self.set_tool(k), bg="#2b2f36", fg="#e8eef2", relief="flat")
            b.pack(side="left", padx=1)
            self.toolbtn[k] = b
        for c in ("#111111", "#c62828", "#1f4fd1"):
            tk.Button(bar, bg=c, activebackground=c, width=2, relief="flat", command=lambda c=c: setattr(self, "col", c)).pack(side="left", padx=1)
        tk.Button(bar, text="↶", command=self.do_undo, bg="#2b2f36", fg="#e8eef2", relief="flat").pack(side="left", padx=4)
        tk.Button(bar, text=T("모두 지우기", "Clear"), command=self.clear, bg="#2b2f36", fg="#e8eef2", relief="flat").pack(side="left")
        self.cv = tk.Canvas(mid, bg="#6b6257", highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.rd = tk.Label(mid, text="", bg="#1c2027", fg="#f3d58a", font=("Consolas", 10), anchor="w")
        self.rd.pack(fill="x")
        self.form = tk.Frame(mid, bg="#12161b")
        self.form.pack(fill="x", pady=(4, 0))
        self.cv.bind("<Configure>", lambda e: self.redraw())
        self.cv.bind("<ButtonPress-1>", self.down)
        self.cv.bind("<B1-Motion>", self.move)
        self.cv.bind("<ButtonRelease-1>", self.up)
        self.cv.bind("<Motion>", self.hover)
        root.bind("<Control-z>", lambda e: self.do_undo())
        # calculator
        tk.Label(right, text=T("공학용 계산기", "Scientific calculator"), bg="#22262d", fg="#f2c14e", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        self.cres = tk.Label(right, text="0", bg="#c9d4c0", fg="#111", font=("Consolas", 15, "bold"), anchor="e", padx=8, pady=6)
        self.cres.pack(fill="x", padx=10)
        self.chist = tk.Label(right, text="", bg="#22262d", fg="#9aa3ab", font=("Consolas", 9), anchor="w")
        self.chist.pack(fill="x", padx=10)
        ce = tk.Entry(right, bg="#0f1216", fg="#e8eef2", insertbackground="#e8eef2", font=("Consolas", 12), relief="flat")
        ce.pack(fill="x", padx=10, pady=3)
        ce.bind("<Return>", lambda e: self.calc_run(ce))
        row = tk.Frame(right, bg="#22262d")
        row.pack(fill="x", padx=10)
        self.degb = tk.Button(row, text="DEG", command=self.toggle_deg, bg="#2b2f36", fg="#e8eef2", relief="flat")
        self.degb.pack(side="left")
        tk.Label(row, text="sin cos tan asin acos atan sqrt ln log exp ^ pi Ans", bg="#22262d", fg="#9aa3ab", font=("Consolas", 8)).pack(side="left", padx=4)
        tk.Label(right, text=T("요약 답안지", "Summary answer sheet"), bg="#22262d", fg="#f2c14e", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(12, 2))
        self.ans = tk.Frame(right, bg="#22262d")
        self.ans.pack(fill="x", padx=10)
        tk.Button(right, text=T("공식 해답 보기", "Show the official solution"), command=self.show_sol, bg="#2b2f36", fg="#e8eef2", relief="flat").pack(fill="x", padx=10, pady=8)
        self.sol = tk.Label(right, text="", wraplength=290, justify="left", bg="#22262d", fg="#c3cbd2", font=("Malgun Gothic", 9))
        self.sol.pack(fill="x", padx=10)
        self.set_task(TASKS[0])

    # ---- storage
    def load(self):
        try:
            with open(SAVE, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            d = {}
        for k in ("marks", "axes", "answers", "tables"):
            d.setdefault(k, {})
        return d

    def store(self):
        try:
            with open(SAVE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False)
        except OSError:
            pass

    def marks(self):
        return self.data["marks"].setdefault(self.sheet, [])

    # ---- panels
    def set_task(self, t):
        self.task = t
        for k, b in self.tbtn.items():
            b.configure(bg="#f2c14e" if k == t["id"] else "#2b2f36", fg="#1c2027" if k == t["id"] else "#e8eef2")
        q = self.qtext
        q.configure(state="normal")
        q.delete("1.0", "end")
        q.insert("end", "(%s) %s  [%d %s]\n\n" % (t["id"], t["name"], t["marks"], T("점", "marks")), "h")
        q.insert("end", t["text"])
        q.configure(state="disabled")
        for w in self.sbar.winfo_children():
            w.destroy()
        for s in t["sheets"]:
            tk.Button(self.sbar, text=SHEETS[s]["name"], command=lambda s=s: self.set_sheet(s), bg="#2b2f36", fg="#e8eef2", relief="flat").pack(side="left", padx=2)
        for w in self.ans.winfo_children():
            w.destroy()
        A = self.data["answers"]
        for f in t["fields"]:
            r = tk.Frame(self.ans, bg="#22262d")
            r.pack(fill="x", pady=1)
            tk.Label(r, text=f, bg="#22262d", fg="#c3cbd2", width=18, anchor="w").pack(side="left")
            v = tk.StringVar(value=A.get(f, ""))
            v.trace_add("write", lambda *a, f=f, v=v: (A.__setitem__(f, v.get()), self.store()))
            tk.Entry(r, textvariable=v, bg="#14171c", fg="#e8eef2", insertbackground="#e8eef2", relief="flat", width=14).pack(side="right")
        self.sol.configure(text="")
        self.set_sheet(t["sheets"][0])

    def show_sol(self):
        if messagebox.askyesno("IOAA 2024", T("해답을 볼까요? 시험처럼 풀어 보려면 먼저 끝까지 풀어 보세요.", "Show the solution? To work it like the examination, finish first.")):
            self.sol.configure(text=self.task["key"] + self.grade())

    def grade(self):
        A, out = self.data["answers"], []
        for f, rng in self.task.get("check", {}).items():
            v = A.get(f, "").strip()
            if not v:
                continue
            if isinstance(rng[0], str):
                ok = v.upper() == rng[0]
            else:
                x = num(v)
                ok = x is not None and rng[0] <= x <= rng[1]
            out.append("%s  %s  %s" % (f, v, "✓" if ok else "✗"))
        t = self.task["id"]
        if t == "D1":
            v = A.get(self.task["fields"][0], "").strip().upper()
            if v:
                out.insert(0, "%s  %s  %s" % (self.task["fields"][0], v, "✓" if v == "DES" else "✗"))
            pairs = [(int(m[0]), int(m[1])) for m in re.findall(r"(\d+)\s*[-–:=→,/]\s*(\d+)", A.get(self.task["fields"][7], ""))]
            if pairs:
                ok = sum(MATCH.get(p) == q for p, q in pairs)
                out.append(T("(d) 짝: 맞음 %d / 7, 틀림 %d", "(d) pairs: %d of 7 right, %d wrong") % (ok, len(pairs) - ok))
            ids = {int(m) for m in re.findall(r"\d+", A.get(self.task["fields"][8], ""))}
            if ids:
                out.append("(e) " + ", ".join(map(str, sorted(ids))) + ("  ✓ " + T("(영점 차이 없는 보정)", "(zero offset)") if ids == {8, 9} else
                           "  ✓ " + T("(영점 차이 있는 보정)", "(non-zero offset)") if ids == {2, 3, 4, 6} else "  ✗"))
        return ("\n\n" + T("내 답", "Your answers") + "\n" + "\n".join(out)) if out else ""

    def set_sheet(self, s):
        self.sheet = s
        self.undo = []
        for w in self.sbar.winfo_children():
            on = w.cget("text") == SHEETS[s]["name"]
            w.configure(bg="#f2c14e" if on else "#2b2f36", fg="#1c2027" if on else "#e8eef2")
        self.build_form()
        self.redraw()

    def set_tool(self, k):
        self.tool = k
        for kk, b in self.toolbtn.items():
            b.configure(bg="#f2c14e" if kk == k else "#2b2f36", fg="#1c2027" if kk == k else "#e8eef2")

    # ---- the axes and plotting forms of a graph-paper sheet
    def build_form(self):
        for w in self.form.winfo_children():
            w.destroy()
        S = SHEETS[self.sheet]
        if "paper" not in S:
            tk.Label(self.form, text=T("시험지 그래프입니다. 곡선과 읽은 자리를 연필로 표시하세요.", "The examination's graph: draw your curve and mark your readings in pencil."), bg="#12161b", fg="#9aa3ab").pack(anchor="w", padx=6, pady=4)
            return
        ax = self.data["axes"].get(self.sheet) or {"ox": 20, "oy": 0 if S.get("logy") else 20, "x0": 0, "dx": 1, "y0": 0.001 if S.get("logy") else 0, "dy": 1, "xl": "", "yl": ""}
        r1 = tk.Frame(self.form, bg="#12161b")
        r1.pack(fill="x", padx=6, pady=3)
        tk.Label(r1, text=T("축:", "Axes:"), bg="#12161b", fg="#f2c14e").pack(side="left")
        self.axv = {}
        for k, lab in (("ox", T("원점 x mm", "origin x mm")), ("oy", T("원점 y mm", "origin y mm")), ("x0", T("원점 x값", "x at origin")), ("dx", T("x/cm", "x per cm")),
                       ("y0", T("원점 y값", "y at origin")), ("dy", T("y/cm", "y per cm")), ("xl", T("x 이름", "x label")), ("yl", T("y 이름", "y label"))):
            if k == "y0":
                r1 = tk.Frame(self.form, bg="#12161b")
                r1.pack(fill="x", padx=6, pady=3)
                if S.get("logy"):
                    lab = T("맨 아래 선의 y값", "y at the bottom line")
            if k == "dy" and S.get("logy"):
                tk.Label(r1, text=T("y: 로그 %d단 (단마다 ×10)", "y: log, %d decades (×10 each)") % S["logy"], bg="#12161b", fg="#9aa3ab").pack(side="left", padx=(6, 1))
                self.axv[k] = tk.StringVar(value="1")
                continue
            tk.Label(r1, text=lab, bg="#12161b", fg="#9aa3ab").pack(side="left", padx=(6, 1))
            v = tk.StringVar(value=str(ax[k]))
            tk.Entry(r1, textvariable=v, width=7, bg="#1a1e24", fg="#e8eef2", insertbackground="#e8eef2", relief="flat").pack(side="left")
            self.axv[k] = v
        tk.Button(r1, text=T("축 그리기", "Draw axes"), command=self.set_axes, bg="#2b2f36", fg="#e8eef2", relief="flat").pack(side="left", padx=6)
        r2 = tk.Frame(self.form, bg="#12161b")
        r2.pack(fill="x", padx=6, pady=3)
        tk.Label(r2, text=T("점 찍기:", "Plot:"), bg="#12161b", fg="#f2c14e").pack(side="left")
        self.pv = {}
        for k in ("x", "y", "±x", "±y"):
            tk.Label(r2, text=k, bg="#12161b", fg="#9aa3ab").pack(side="left", padx=(6, 1))
            v = tk.StringVar()
            e = tk.Entry(r2, textvariable=v, width=9, bg="#1a1e24", fg="#e8eef2", insertbackground="#e8eef2", relief="flat")
            e.pack(side="left")
            e.bind("<Return>", lambda ev: self.plot())
            self.pv[k] = v
        tk.Button(r2, text=T("찍기", "Plot"), command=self.plot, bg="#2b2f36", fg="#e8eef2", relief="flat").pack(side="left", padx=6)
        self.pmsg = tk.Label(r2, text="", bg="#12161b", fg="#f0a79f")
        self.pmsg.pack(side="left")

    def set_axes(self):
        try:
            a = {k: float(self.axv[k].get().replace(",", ".")) for k in ("ox", "oy", "x0", "dx", "y0", "dy")}
            if not a["dx"] or not a["dy"] or (SHEETS[self.sheet].get("logy") and a["y0"] <= 0):
                raise ValueError
        except ValueError:
            return
        a["xl"], a["yl"] = self.axv["xl"].get(), self.axv["yl"].get()
        self.data["axes"][self.sheet] = a
        self.store()
        self.redraw()

    def ym_of(self, ax, y):
        S = SHEETS[self.sheet]
        if S.get("logy"):
            return math.log10(y / ax["y0"]) * S["paper"][1] / S["logy"] if y > 0 else -1e9
        return ax["oy"] + (y - ax["y0"]) / ax["dy"] * 10

    def y_at(self, ax, ym):
        S = SHEETS[self.sheet]
        if S.get("logy"):
            return ax["y0"] * 10 ** (ym * S["logy"] / S["paper"][1])
        return ax["y0"] + (ym - ax["oy"]) / 10 * ax["dy"]

    def plot(self):
        ax = self.data["axes"].get(self.sheet)
        if not ax:
            self.pmsg.configure(text=T("먼저 축을 그리세요.", "Draw the axes first."))
            return
        try:
            x, y = float(self.pv["x"].get().replace(",", ".")), float(self.pv["y"].get().replace(",", "."))
        except ValueError:
            self.pmsg.configure(text=T("숫자를 넣으세요.", "Type numbers."))
            return
        wm, hm = SHEETS[self.sheet]["paper"]
        xm, ym = ax["ox"] + (x - ax["x0"]) / ax["dx"] * 10, self.ym_of(ax, y)
        if not (0 <= xm <= wm and 0 <= ym <= hm):
            self.pmsg.configure(text=T("그 점은 종이 밖입니다.", "That point is off the paper."))
            return
        u, v = xm * PX, (hm - ym) * PX
        self.push()
        self.marks().append({"t": "circle", "x": u, "y": v, "r": 7, "c": self.col})
        for key, horiz in (("±x", True), ("±y", False)):
            try:
                s = float(self.pv[key].get().replace(",", "."))
            except ValueError:
                continue
            if horiz:
                d = s / ax["dx"] * 10 * PX
                pts = [[u - d, v], [u + d, v]]
            else:
                lo, hi = self.ym_of(ax, y - abs(s)), self.ym_of(ax, y + abs(s))
                pts = [[u, (hm - max(lo, 0)) * PX], [u, (hm - min(hi, hm)) * PX]]
            self.marks().append({"t": "line", "pts": pts, "c": self.col})
        self.store()
        self.pmsg.configure(text="")
        for k in self.pv:
            self.pv[k].set("")
        self.redraw()

    # ---- calculator
    def calc_run(self, e):
        src = e.get().strip()
        if not src:
            return
        try:
            v = self.calc.run(src)
            self.cres.configure(text=fmt(v))
            self.chist.configure(text=src + " =")
            e.delete(0, "end")
        except Exception:
            self.cres.configure(text=T("식 오류", "error"))

    def toggle_deg(self):
        self.calc.deg = not self.calc.deg
        self.degb.configure(text="DEG" if self.calc.deg else "RAD")

    # ---- worksheet
    def worksheet(self):
        t = self.task
        tab = self.data["tables"].setdefault(t["id"], {"rows": [list(r) + [""] * (len(t["table"][0]) - len(r)) for r in t["table"]] + [[""] * len(t["table"][0]) for _ in range(4)]})
        w = tk.Toplevel(self.root)
        w.title(T("계산표 — ", "Worksheet — ") + t["id"])
        w.configure(bg="#fbfaf6")
        box = tk.Frame(w, bg="#fbfaf6")
        box.pack(fill="both", expand=True, padx=6, pady=6)

        def build():
            for c in box.winfo_children():
                c.destroy()
            for i, row in enumerate(tab["rows"]):
                for j in range(len(row)):
                    v = tk.StringVar(value=row[j])

                    def setv(*a, i=i, j=j, v=v):
                        tab["rows"][i][j] = v.get()
                        self.store()
                    v.trace_add("write", setv)
                    tk.Entry(box, textvariable=v, width=12, font=("Consolas", 10, "bold" if i == 0 else "normal"),
                             bg="#ece6d6" if i == 0 else "#fffdf6", relief="solid", bd=1).grid(row=i, column=j, sticky="nsew")
        build()

        def add():
            tab["rows"].append([""] * len(tab["rows"][0]))
            self.store()
            build()
        tk.Button(w, text=T("줄 추가", "Add row"), command=add).pack(side="left", padx=6, pady=4)

    # ---- drawing
    def geom(self):
        S = SHEETS[self.sheet]
        W, H = self.size()
        cw, ch = max(100, self.cv.winfo_width()), max(100, self.cv.winfo_height())
        k = min((cw - 16) / W, (ch - 16) / H)
        if "img" in S:
            k = 1 / max(1, math.ceil(1 / k - 1e-9))      # the figure is shown at its own size or an exact fraction of it
        return k, (cw - W * k) / 2, (ch - H * k) / 2

    def size(self):
        S = SHEETS[self.sheet]
        if "paper" in S:
            return S["paper"][0] * PX, S["paper"][1] * PX
        return S["w"], S["h"]

    def to_map(self, e):
        k, ox, oy = self.geom()
        return [(e.x - ox) / k, (e.y - oy) / k]

    def redraw(self):
        cv = self.cv
        cv.delete("all")
        S = SHEETS[self.sheet]
        W, H = self.size()
        k, ox, oy = self.geom()
        X = lambda u: ox + u * k
        Y = lambda v: oy + v * k
        if "paper" in S:
            wm, hm = S["paper"]
            cv.create_rectangle(X(0), Y(0), X(W), Y(H), fill="#fffdf8", outline="")
            for i in range(wm + 1):
                if k * PX < 2.2 and i % 5:
                    continue
                c = "#e2834a" if i % 10 == 0 else "#efb08a" if i % 5 == 0 else "#f8d9c4"
                cv.create_line(X(i * PX), Y(0), X(i * PX), Y(H), fill=c)
            if S.get("logy"):
                dec = hm / S["logy"]
                for d in range(S["logy"]):
                    for n in [10 + i for i in range(10)] + [20 + 2 * i for i in range(15)] + [50 + 5 * i for i in range(10)] + ([100] if d == S["logy"] - 1 else []):
                        if k * PX < 2.2 and n % 10:
                            continue
                        c = "#e2834a" if n in (10, 100) else "#efb08a" if n % 10 == 0 else "#f8d9c4"
                        yy = (d + math.log10(n / 10)) * dec
                        cv.create_line(X(0), Y(H - yy * PX), X(W), Y(H - yy * PX), fill=c)
            else:
                for j in range(hm + 1):
                    if k * PX < 2.2 and j % 5:
                        continue
                    c = "#e2834a" if j % 10 == 0 else "#efb08a" if j % 5 == 0 else "#f8d9c4"
                    cv.create_line(X(0), Y(H - j * PX), X(W), Y(H - j * PX), fill=c)
            cv.create_text(X(W) - 6, Y(0) + 4, text=S["name"], anchor="ne", fill="#b85a2a", font=("Arial", 10, "bold"))
            ax = self.data["axes"].get(self.sheet)
            if ax:
                X0, Y0 = X(ax["ox"] * PX), Y((hm - ax["oy"]) * PX)
                cv.create_line(X(0), Y0, X(W), Y0, fill="#1b1b1b", width=2, arrow="last")
                cv.create_line(X0, Y(H), X0, Y(0), fill="#1b1b1b", width=2, arrow="last")
                for n in range(-40, 41):
                    xm = ax["ox"] + 10 * n
                    if 2 <= xm <= wm - 6:
                        x = X(xm * PX)
                        cv.create_line(x, Y0 - 3, x, Y0 + 3)
                        cv.create_text(x, Y0 + 5, text=fmt(ax["x0"] + n * ax["dx"]), anchor="n", font=("Arial", 8))
                    if S.get("logy"):
                        continue
                    ym = ax["oy"] + 10 * n
                    if n and 2 <= ym <= hm - 6:
                        y = Y((hm - ym) * PX)
                        cv.create_line(X0 - 3, y, X0 + 3, y)
                        cv.create_text(X0 - 5, y, text=fmt(ax["y0"] + n * ax["dy"]), anchor="e", font=("Arial", 8))
                if S.get("logy"):
                    for d in range(S["logy"] + 1):
                        for m in (1, 2, 5):
                            ym = (d + math.log10(m)) * hm / S["logy"]
                            if ym <= hm - 4:
                                y = Y((hm - ym) * PX)
                                cv.create_line(X0 - 3, y, X0 + 3, y)
                                cv.create_text(X0 - 5, y, text=fmt(ax["y0"] * m * 10 ** d), anchor="e", font=("Arial", 8))
                cv.create_text(X(W) - 8, Y0 - 8, text=ax.get("xl", ""), anchor="se", font=("Arial", 10, "bold"))
                cv.create_text(X0 + 8, Y(0) + 6, text=ax.get("yl", ""), anchor="nw", font=("Arial", 10, "bold"))
        for it in self.marks() + ([self.drag["it"]] if self.drag else []):
            self.mark(it, X, Y, k)

    def mark(self, it, X, Y, k):
        cv = self.cv
        c = it.get("c", "#111")
        s = 11 * k
        t = it["t"]
        if "pts" in it:
            flat = [z for u, v in it["pts"] for z in (X(u), Y(v))]
            if len(flat) >= 4:
                cv.create_line(*flat, fill=c, width=max(1.2, s * 0.12), capstyle="round", joinstyle="round")
            return
        x, y = X(it["x"]), Y(it["y"])
        w = max(1.2, s * 0.12)
        if t == "circle":
            r = it.get("r", 8) * k
            cv.create_oval(x - r, y - r, x + r, y + r, outline=c, width=w)
        elif t == "dot":
            cv.create_oval(x - s * 0.3, y - s * 0.3, x + s * 0.3, y + s * 0.3, fill=c, outline=c)
        elif t == "cross":
            cv.create_line(x - s * 0.6, y - s * 0.6, x + s * 0.6, y + s * 0.6, fill=c, width=w)
            cv.create_line(x + s * 0.6, y - s * 0.6, x - s * 0.6, y + s * 0.6, fill=c, width=w)
        elif t == "plus":
            cv.create_line(x - s * 0.7, y, x + s * 0.7, y, fill=c, width=w)
            cv.create_line(x, y - s * 0.7, x, y + s * 0.7, fill=c, width=w)
        elif t == "text":
            cv.create_text(x, y, text=it["str"], fill=c, anchor="w", font=("Segoe UI", max(7, int(s)), "bold"))

    def hover(self, e):
        S = SHEETS[self.sheet]
        if "paper" not in S:
            self.rd.configure(text="")
            return
        u, v = self.to_map(e)
        wm, hm = S["paper"]
        xm, ym = u / PX, hm - v / PX
        s = T("종이 위치", "on the paper") + "  %.1f mm, %.1f mm" % (xm, ym)
        ax = self.data["axes"].get(self.sheet)
        if ax:
            s += "     " + T("축 눈금으로", "on your axes") + "  x = %s, y = %s" % (fmt(ax["x0"] + (xm - ax["ox"]) / 10 * ax["dx"]), fmt(self.y_at(ax, ym)))
        self.rd.configure(text=s)

    def push(self):
        self.undo.append(json.dumps(self.marks()))

    def down(self, e):
        p = self.to_map(e)
        if self.tool == "erase":
            best, bi = 1e9, -1
            for i, it in enumerate(self.marks()):
                d = min(math.hypot(p[0] - u, p[1] - v) for u, v in it["pts"]) if "pts" in it else math.hypot(p[0] - it["x"], p[1] - it["y"])
                if d < best:
                    best, bi = d, i
            if bi >= 0 and best < 18:
                self.push()
                del self.marks()[bi]
                self.store()
                self.redraw()
            return
        if self.tool == "text":
            w = tk.Toplevel(self.root)
            v = tk.StringVar()
            en = tk.Entry(w, textvariable=v, font=("Segoe UI", 12))
            en.pack(padx=10, pady=10)
            en.focus_set()

            def ok(_=None):
                s = v.get().strip()
                w.destroy()
                if s:
                    self.push()
                    self.marks().append({"t": "text", "x": p[0], "y": p[1], "str": s, "c": self.col})
                    self.store()
                    self.redraw()
            en.bind("<Return>", ok)
            return
        if self.tool in ("pen", "line"):
            self.drag = {"it": {"t": self.tool, "pts": [p, list(p)], "c": self.col}}
            return
        self.push()
        self.marks().append({"t": self.tool, "x": p[0], "y": p[1], "c": self.col, "r": 8})
        self.store()
        self.redraw()

    def move(self, e):
        if not self.drag:
            return
        p = self.to_map(e)
        it = self.drag["it"]
        if it["t"] == "line":
            it["pts"][1] = p
        else:
            it["pts"].append(p)
        self.redraw()

    def up(self, e):
        if not self.drag:
            return
        it = self.drag["it"]
        self.drag = None
        self.push()
        self.marks().append(it)
        self.store()
        self.redraw()

    def do_undo(self):
        if self.undo:
            self.data["marks"][self.sheet] = json.loads(self.undo.pop())
            self.store()
            self.redraw()

    def clear(self):
        if self.marks() and messagebox.askyesno("IOAA 2024", T("이 종이에 그린 것을 모두 지울까요?", "Erase everything drawn on this sheet?")):
            self.push()
            self.data["marks"][self.sheet] = []
            self.store()
            self.redraw()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
