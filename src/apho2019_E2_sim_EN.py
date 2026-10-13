#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  20th Asian Physics Olympiad  (APhO 2019, Adelaide, Australia)
  Experimental Problem E2 :  WAVE PULSES IN A MAGNETICALLY ACTIVE FLUID
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Apparatus rebuilt from the photographs of the problem sheet: glass dish
    of ferrofluid on a wooden base tilted by nylon bolts, lamp, camera
    (25 frames per second), transparent graticule strip, small magnets and
    the large N42 magnet.
    Pulse fronts come from the eikonal equation |grad T| = 1/v with
    v = kappa sqrt(d), solved once per configuration (refraction, diffraction
    and wall reflections follow automatically).  Speeds, depths, kappa,
    tan(theta) and times in seconds are never computed or shown -- only the
    frame number, the rulers and the graticule.
    All hidden true parameters are randomised for every session.

    Run:   python3 apho2019_E2_sim_KO.py
"""

# --------------------------------------------------------------------------
# language
# --------------------------------------------------------------------------
LANG = "en"          # the KO edition differs only in this line

import math
import random
import tkinter as tk
from tkinter import ttk

# =========================================================================
#  0. 물리 상수 / 장비 제원
# =========================================================================
#  v(d) = kappa * sqrt(d)   —  문제지 식 (1)
#  아래 KAP_MM 은 mm 단위 전용 :  v[mm/s] = KAP_MM * sqrt(d[mm])
#  SI 로는 kappa = KAP_MM / sqrt(1000) * (1/1000) * 1000 = KAP_MM/31.623 m^0.5/s
KAP_MM = 130.0                 # -> kappa = 4.111 m^0.5/s
KAP_SI = KAP_MM / math.sqrt(1000.0) / math.sqrt(1000.0) * math.sqrt(1000.0)

DISH_L = 173.0                 # 접시 안쪽 길이 (x 방향) [mm]
DISH_W = 120.0                 # 접시 안쪽 폭   (y 방향) [mm]
DISH_WALL = 4.0                # 유리 벽 두께 [mm]

FPS = 25                       # 카메라 프레임률 (부록 A)

C_METAL = "#b9bec4"
C_METAL_D = "#7f858c"
C_METAL_L = "#e6e9ec"
C_PLASTIC = "#eceae4"
C_PLASTIC_D = "#c4c0b6"
C_WOOD = "#d9b378"
C_WOOD_D = "#a8823f"
C_FF = "#141418"
C_FF_HL = "#4a4a56"
C_GLASS = "#dfe8ee"
C_GHOST = "#9aa4ad"
C_LAMP = "#f7f3d8"
C_NYLON = "#f2f0e6"
C_NYLON_D = "#c9c5b4"


# =========================================================================
#  1. 은닉 참값 — 세션마다 무작위 (학생은 절대 볼 수 없다)
# =========================================================================
class Apparatus2:
    def __init__(self, seed=None):
        rng = random.Random(seed)
        self.rng = rng

        # --- 유체 -------------------------------------------------------
        self.kap = KAP_MM * rng.uniform(0.96, 1.04)      # mm^0.5 / s
        self.d0 = 4.0 * rng.uniform(0.92, 1.08)          # 수평일 때 깊이 [mm]

        # --- 접시 -------------------------------------------------------
        self.Lx = DISH_L * rng.uniform(0.99, 1.01)
        self.Ly = DISH_W * rng.uniform(0.99, 1.01)

        # --- 나무 받침대 ------------------------------------------------
        self.base_len = 195.0 * rng.uniform(0.98, 1.02)  # 힌지변 ↔ 볼트 [mm]
        self.bolt_pitch = 1.25 * rng.uniform(0.99, 1.01)  # 나일론 볼트 [mm/회전]

        # --- 투명 격자 스트립 -------------------------------------------
        self.grid = 12.91 * rng.uniform(0.97, 1.03)      # 한 칸 [mm]

        # --- 자석 위 융기 -----------------------------------------------
        self.lump_h = 5.0 * rng.uniform(0.88, 1.12)      # 융기 높이 [mm]
        self.lump_r = 16.0 * rng.uniform(0.92, 1.08)     # 융기 반경 [mm]
        self.dip_h = 0.30 * rng.uniform(0.8, 1.2)        # 융기 둘레의 얕아짐

        # --- 촬영 ------------------------------------------------------
        self.fps = FPS
        # 손으로 미는 순간의 무작위성 (펄스 진폭·발생 시각 흔들림)
        self.push_jitter = 0.0

    # ------------------------------------------------------------------
    def reroll_push(self):
        """손으로 밀 때마다 조금씩 다른 펄스가 만들어진다."""
        r = self.rng
        self.push_jitter = r.uniform(-0.010, 0.010)      # [s]
        return r.uniform(0.75, 1.25)                      # 진폭 배율

    # ------------------------------------------------------------------
    def tilt(self, turns):
        """볼트 회전수 -> tan(theta).  (학생은 자로 높이를 재서 알아낸다)"""
        return turns * self.bolt_pitch / self.base_len

    def water_line(self, tan_th):
        """기울였을 때 유체가 시작되는 y 좌표 [mm] (깊이 0 인 곳).
           음수이면 접시 전체가 젖어 있다는 뜻."""
        if tan_th < 1e-9:
            return -1e9
        V = self.Lx * self.Ly * self.d0
        Ywet = math.sqrt(2.0 * V / (self.Lx * tan_th))
        if Ywet >= self.Ly:                    # 전면이 젖어 있다
            return self.Ly / 2.0 - self.d0 / tan_th
        return self.Ly - Ywet

    def depth(self, y, tan_th):
        y0 = self.water_line(tan_th)
        if tan_th < 1e-9:
            return self.d0
        return max(0.0, (y - y0) * tan_th)

    def lump(self, x, y, mags):
        """자석 위 융기 (초가우시안 : 평평한 꼭대기 + 짧은 자락).
           유체가 융기로 끌려 올라가므로 둘레는 오히려 얕아진다(부피 보존)."""
        add = 0.0
        for (mx, my) in mags:
            r = math.hypot(x - mx, y - my) / self.lump_r
            if r < 3.0:
                add += self.lump_h * math.exp(-(r ** 4))
                add -= self.dip_h * math.exp(-((r - 1.65) / 0.55) ** 2)
        return add


# =========================================================================
#  2. 파면 계산  —  아이코날 방정식  |grad T| = 1 / v(x, y)
# =========================================================================
#   * 굴절(깊이에 따른 속도 변화)과 회절(장애물 뒤로 돌아 들어감)이 저절로 나온다
#   * 먼 쪽 벽의 반사는 x 방향으로 접은(거울) 영역을 함께 풀어서 얻는다
#   * 프레임마다 다시 풀지 않는다. 배치가 바뀔 때 한 번만 푼다.
INF = 1e18


class WaveField:
    def __init__(self, ap, tan_th, mags, src, h=2.5):
        """src : ("plane",) 또는 ("point", x, y)"""
        self.ap = ap
        self.h = h
        self.nx = int(2.0 * ap.Lx / h) + 1      # 거울 영역까지
        self.ny = int(ap.Ly / h) + 1
        self.build_speed(tan_th, mags)
        self.solve(src)

    # ------------------------------------------------------------ 속도장
    def build_speed(self, tan_th, mags):
        ap, h = self.ap, self.h
        nx, ny = self.nx, self.ny
        Lx = ap.Lx
        self.slow = []                       # 1/v  [s/mm]
        self.dep = []
        for j in range(ny):
            y = j * h
            rows = []
            deps = []
            base = ap.depth(y, tan_th)
            for i in range(nx):
                x = i * h
                xr = x if x <= Lx else 2.0 * Lx - x     # 거울
                d = base + ap.lump(xr, y, mags)
                deps.append(d)
                if d < 0.12:
                    rows.append(INF)                    # 마른 바닥
                else:
                    rows.append(1.0 / (ap.kap * math.sqrt(d)))
            self.slow.append(rows)
            self.dep.append(deps)

    # -------------------------------------------------------- 고속 스위핑
    def solve(self, src):
        nx, ny, h = self.nx, self.ny, self.h
        T = [[INF] * nx for _ in range(ny)]
        if src[0] in ("plane", "plane2"):
            iw = [0] if src[0] == "plane" else [0, int(round(self.ap.Lx / h))]
            for j in range(ny):
                for i in iw:
                    if i < nx and self.slow[j][i] < INF:
                        T[j][i] = 0.0
        else:
            sx, sy = src[1], src[2]
            i0 = min(nx - 1, max(0, int(round(sx / h))))
            j0 = min(ny - 1, max(0, int(round(sy / h))))
            T[j0][i0] = 0.0
            for dj in (-1, 0, 1):
                for di in (-1, 0, 1):
                    j, i = j0 + dj, i0 + di
                    if 0 <= j < ny and 0 <= i < nx and self.slow[j][i] < INF:
                        T[j][i] = math.hypot(di, dj) * h * self.slow[j][i]

        rng_i = range(nx)
        rng_ir = range(nx - 1, -1, -1)
        rng_j = range(ny)
        rng_jr = range(ny - 1, -1, -1)
        sweeps = ((rng_j, rng_i), (rng_j, rng_ir),
                  (rng_jr, rng_i), (rng_jr, rng_ir))
        for _ in range(2):
            for js, iss in sweeps:
                for j in js:
                    Tj = T[j]
                    sj = self.slow[j]
                    Tup = T[j - 1] if j > 0 else None
                    Tdn = T[j + 1] if j < ny - 1 else None
                    for i in iss:
                        f = sj[i]
                        if f >= INF:
                            continue
                        a = INF
                        if i > 0:
                            a = Tj[i - 1]
                        if i < nx - 1 and Tj[i + 1] < a:
                            a = Tj[i + 1]
                        b = INF
                        if Tup is not None:
                            b = Tup[i]
                        if Tdn is not None and Tdn[i] < b:
                            b = Tdn[i]
                        if a >= INF and b >= INF:
                            continue
                        fh = f * h
                        if abs(a - b) >= fh or a >= INF or b >= INF:
                            cand = min(a, b) + fh
                        else:
                            s = a + b
                            dd = 2.0 * fh * fh - (a - b) ** 2
                            cand = 0.5 * (s + math.sqrt(dd))
                        if cand < Tj[i]:
                            Tj[i] = cand
        self.T = T

    # ------------------------------------------------ 마칭 스퀘어 등고선
    def front(self, t):
        """T = t 인 등고선을 선분 목록 [(x0,y0,x1,y1), ...] 으로.
           거울 영역(x > Lx)의 점은 반사파로서 되접어 돌려준다."""
        T, h = self.T, self.h
        nx, ny = self.nx, self.ny
        Lx = self.ap.Lx
        segs = []
        for j in range(ny - 1):
            r0, r1 = T[j], T[j + 1]
            for i in range(nx - 1):
                a, b = r0[i], r0[i + 1]
                c, d = r1[i + 1], r1[i]
                mx = a
                mn = a
                for v in (b, c, d):
                    if v > mx:
                        mx = v
                    if v < mn:
                        mn = v
                if mn > t or mx < t or mx >= INF:
                    continue
                x0, y0 = i * h, j * h
                pts = []
                # 아래변
                if (a - t) * (b - t) < 0:
                    pts.append((x0 + h * (t - a) / (b - a), y0))
                # 오른변
                if (b - t) * (c - t) < 0:
                    pts.append((x0 + h, y0 + h * (t - b) / (c - b)))
                # 윗변
                if (d - t) * (c - t) < 0:
                    pts.append((x0 + h * (t - d) / (c - d), y0 + h))
                # 왼변
                if (a - t) * (d - t) < 0:
                    pts.append((x0, y0 + h * (t - a) / (d - a)))
                if len(pts) >= 2:
                    (px, py), (qx, qy) = pts[0], pts[1]
                    if px > Lx:
                        px = 2 * Lx - px
                    if qx > Lx:
                        qx = 2 * Lx - qx
                    segs.append((px, py, qx, qy))
        return segs

    def arrival(self, x, y):
        i = min(self.nx - 1, max(0, int(round(x / self.h))))
        j = min(self.ny - 1, max(0, int(round(y / self.h))))
        return self.T[j][i]

    def depth_at(self, x, y):
        i = min(self.nx - 1, max(0, int(round(x / self.h))))
        j = min(self.ny - 1, max(0, int(round(y / self.h))))
        return self.dep[j][i]


# =========================================================================
#  3. 다국어 문자열
# =========================================================================
S_KO = {
    "lampoff": "(램프 꺼짐)",
    "title": "APhO 2019 실험 2 — 자기 활성 유체의 파동 펄스 (가상 실험실)",
    "t_asm": "1. 장비 배치·조립",
    "t_ab": "2. 평면 펄스 (Part A · B)",
    "t_cd": "3. 자석과 파동 (Part C · D)",
    "t_info": "장비 목록 · 주의사항",
    "tray": "부품 상자 — 끌어다 놓으세요",
    "reset": "전부 분해",
    "auto": "자동 조립",
    "need": "먼저 필요한 부품",
    "done": "조립 완료 — 다음 탭으로 이동하세요.",
    "cam": "카메라 (위에서)",
    "side": "옆에서 본 모습",
    "push": "접시를 손으로 탁 밀기",
    "pushbase": "받침대째 밀기",
    "pullmag": "큰 자석을 빠르게 치우기",
    "setmag": "큰 N42 자석을 가장자리에 대기",
    "magready": "큰 자석 대기 중 — 치우면 펄스가 생깁니다",
    "rec": "촬영본",
    "live": "실시간 (정지 상태)",
    "frame": "프레임",
    "first": "◀◀ 처음",
    "prev": "◀ 이전",
    "next": "다음 ▶",
    "play": "재생 ▶",
    "stop": "정지",
    "bolts": "나일론 볼트 (기울기)",
    "up": "▲ 올림",
    "dn": "▼ 내림",
    "turn1": "1 회전",
    "turn4": "1/4 회전",
    "turns": "돌린 회전",
    "zero": "회전수 영점",
    "level": "수평으로 되돌리기",
    "tools": "자 / 투명 그리드 스트립",
    "showrul": "자 표시",
    "vert": "세로",
    "showgrid": "그리드 스트립 표시",
    "gridmove": "그리드 이동",
    "smag": "채널의 작은 N52 자석",
    "n0": "없음", "n1": "1 개", "n2": "2 개",
    "movl": "◀ 왼쪽", "movr": "오른쪽 ▶",
    "gap": "두 자석 간격",
    "wider": "넓게", "narrower": "좁게",
    "lamp": "램프",
    "on": "켬",
    "note_ab": ("접시를 밀어 평면 펄스를 만들고 촬영한 뒤, 프레임을 한 장씩\n"
                "넘기며 그리드 위에서 펄스가 간 거리를 직접 재세요.\n"
                "볼트를 돌려 기울이면 깊이가 y 에 따라 변합니다."),
    "note_cd": ("작은 자석을 채널에 넣고 접시를 덮은 뒤, 큰 자석을 가장자리에\n"
                "댔다가 빠르게 치워 펄스를 만드세요. 세 가지 구동 방식을 모두\n"
                "관찰하고 파면이 어떻게 달라지는지 보세요."),
    "hint_frame": "프레임 사이 간격은 카메라 사양표를 보세요.",
    "dry": "이 부분은 유체가 없습니다 (바닥이 드러남)",
    "eq": "장비 목록",
    "safety": "주의사항",
    "notshown": "이 시뮬레이터가 보여주지 않는 것",
}
S_EN = {
    "lampoff": "(lamp off)",
    "title": "APhO 2019 Experiment 2 — Wave pulses in a magnetically "
             "active fluid (virtual lab)",
    "t_asm": "1. Set up the apparatus",
    "t_ab": "2. Plane pulses (Part A · B)",
    "t_cd": "3. Waves and magnets (Part C · D)",
    "t_info": "Equipment · Safety",
    "tray": "Parts tray — drag them onto the bench",
    "reset": "Disassemble all",
    "auto": "Auto assemble",
    "need": "First place",
    "done": "Assembly complete — go to the next tab.",
    "cam": "Camera (from above)",
    "side": "Side view",
    "push": "Push the dish sharply",
    "pushbase": "Slide the wooden base",
    "pullmag": "Withdraw the large magnet rapidly",
    "setmag": "Hold the large N42 magnet at the edge",
    "magready": "Large magnet in place — withdraw it to launch a pulse",
    "rec": "Recording",
    "live": "Live (fluid at rest)",
    "frame": "Frame",
    "first": "◀◀ First",
    "prev": "◀ Prev",
    "next": "Next ▶",
    "play": "Play ▶",
    "stop": "Stop",
    "bolts": "Nylon bolts (tilt)",
    "up": "▲ Raise",
    "dn": "▼ Lower",
    "turn1": "1 turn",
    "turn4": "1/4 turn",
    "turns": "turns made",
    "zero": "Zero the counter",
    "level": "Back to level",
    "tools": "Ruler / transparent grid strip",
    "showrul": "Show ruler",
    "vert": "vertical",
    "showgrid": "Show grid strip",
    "gridmove": "Move grid",
    "smag": "Small N52 magnets in the channel",
    "n0": "none", "n1": "1", "n2": "2",
    "movl": "◀ left", "movr": "right ▶",
    "gap": "Gap between the two magnets",
    "wider": "wider", "narrower": "narrower",
    "lamp": "Lamp",
    "on": "on",
    "note_ab": ("Push the dish to launch a plane pulse, record it, then step\n"
                "frame by frame and measure how far the pulse has travelled\n"
                "on the grid. Turning the bolts tilts the dish so that the\n"
                "depth varies with y."),
    "note_cd": ("Put a small magnet in the channel, place the dish over it,\n"
                "then hold the large magnet at the edge and withdraw it\n"
                "rapidly. Try all three ways of driving the pulse."),
    "hint_frame": "The interval between frames is in the camera specification.",
    "dry": "no fluid here (bare glass)",
    "eq": "Equipment",
    "safety": "Safety",
    "notshown": "What this simulator does NOT show you",
}
S = S_KO if LANG == "ko" else S_EN

PARTS_KO = [
    ("나무 받침대 W (턱 + 자석 채널, 모서리에 볼트 구멍)", "base"),
    ("유리접시 (뚜껑 밀봉, 페로플루이드 F)", "dish"),
    ("차광 후드 겸 받침대", "shroud"),
    ("건전지 램프", "lamp"),
    ("카메라 (동영상 25 fps)", "cam"),
    ("투명 그리드 스트립", "grid"),
    ("나일론 볼트 2개 + 나무 스페이서", "bolts"),
    ("N52 자석 14.2 x 3.2 mm  (2개)", "smag"),
    ("N42 자석 20.0 x 5.0 mm  (1개)", "bmag"),
    ("자 (30 cm), 블루택, 알루미늄 포일", "misc"),
]
PARTS_EN = [
    ("Wooden base W (barrier + magnet channel, bolt holes)", "base"),
    ("Glass dish (sealed lid, ferrofluid F)", "dish"),
    ("Light shroud and stand", "shroud"),
    ("Battery lamp", "lamp"),
    ("Camera (video, 25 fps)", "cam"),
    ("Transparent grid strips", "grid"),
    ("2 nylon bolts + wooden spacers", "bolts"),
    ("N52 magnet 14.2 x 3.2 mm  (2 off)", "smag"),
    ("N42 magnet 20.0 x 5.0 mm  (1 off)", "bmag"),
    ("30 cm ruler, blu-tack, aluminium foil", "misc"),
]
PARTS = PARTS_KO if LANG == "ko" else PARTS_EN

SAFETY_KO = [
    "유리접시의 뚜껑은 어떤 경우에도 열지 않습니다. 페로플루이드는 피부·옷에 "
    "묻으면 지워지지 않고 유해합니다.",
    "자석끼리 부딪히면 깨집니다. 깨진 자석은 위험하며 교체해 주지 않습니다.",
    "강한 자석은 카메라·시계·신용카드에서 멀리 두세요.",
    "자석을 다룰 때는 손가락이 끼지 않도록 항상 옆으로 밀어서 떼어냅니다.",
]
SAFETY_EN = [
    "Never remove the lid of the glass dish. Ferrofluid stains permanently "
    "and is harmful on skin or clothing.",
    "If the magnets collide they will break. Broken magnets are dangerous "
    "and will not be replaced.",
    "Keep the strong magnets away from cameras, watches and cards.",
    "Always separate magnets by sliding them sideways, never by pulling "
    "them apart.",
]
SAFETY = SAFETY_KO if LANG == "ko" else SAFETY_EN

NOTSHOWN_KO = """  이 시뮬레이터는 실제 실험대에서 볼 수 있는 것만 보여줍니다.

  화면에 없는 것 :
    · 펄스의 속도 v, 유체 깊이 d, 비례상수 kappa
    · 기울기 tan(theta), 깊이 함수 d(y)
    · 프레임 사이의 시간(초), 거리(mm 또는 cm) 의 수치
    · 그래프, 회귀직선, 채점표

  학생이 직접 하는 것 :
    · 자로 접시·받침대·볼트 높이를 재고 기울기를 구한다
    · 투명 그리드 스트립을 대고 한 칸의 크기를 자로 교정한다
    · 프레임 번호를 세어 시간을 얻는다 (카메라 사양표 참조)
    · 파면의 (x, y) 를 읽어 x^2 대 y 그래프를 직접 그린다
"""
NOTSHOWN_EN = """  This simulator shows only what you could see on a real bench.

  NOT on the screen :
    · pulse speed v, fluid depth d, the constant kappa
    · the tilt tan(theta) or the depth function d(y)
    · the time between frames, or any distance as a number
    · graphs, fitted lines, marking schemes

  What YOU have to do :
    · measure the dish, the base and the bolt height with the ruler
    · lay the transparent grid strip down and calibrate one square
    · count frame numbers to get the time (see the camera specification)
    · read off (x, y) on the wave front and plot x^2 against y yourself
"""
NOTSHOWN = NOTSHOWN_KO if LANG == "ko" else NOTSHOWN_EN


# =========================================================================
#  4. 부품 그림 (2D) — 문제지 사진의 배치를 그대로 따른다
# =========================================================================
def draw_base(cv, x, y, s=1.0, ghost=False, tag="p"):
    """나무 받침대. y = 윗면.  턱(barrier)은 뒤쪽, 채널은 가운데."""
    W, H = 250 * s, 18 * s
    if ghost:
        cv.create_rectangle(x - W / 2, y, x + W / 2, y + H, outline=C_GHOST,
                            dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - W / 2, y, x + W / 2, y + H, fill=C_WOOD,
                        outline=C_WOOD_D, width=2, tags=tag)
    for i in range(5):
        cv.create_line(x - W / 2 + 14 + i * 48, y + 3,
                       x - W / 2 + 24 + i * 48, y + H - 3,
                       fill=C_WOOD_D, tags=tag)
    # 뒤쪽 턱
    cv.create_rectangle(x + W / 2 - 7 * s, y - 9 * s, x + W / 2, y,
                        fill=C_WOOD, outline=C_WOOD_D, width=2, tags=tag)
    # 볼트 구멍
    for dx in (-W / 2 + 10 * s, W / 2 - 16 * s):
        cv.create_oval(x + dx - 3, y + 2, x + dx + 3, y + 8,
                       fill="#8d6a2f", outline="", tags=tag)


def draw_dish_side(cv, x, y, s=1.0, ghost=False, tag="p", fill_frac=0.35):
    """유리접시 옆면. y = 바닥 밑면."""
    W, H = 190 * s, 30 * s
    if ghost:
        cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, outline=C_GHOST,
                            dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, fill=C_GLASS,
                        outline="#93a9b7", width=2, tags=tag)
    cv.create_rectangle(x - W / 2 + 3, y - 6 * s, x + W / 2 - 3, y - 3 * s,
                        fill="#c9d8e2", outline="", tags=tag)
    h = (H - 9 * s) * fill_frac
    cv.create_rectangle(x - W / 2 + 3, y - 6 * s - h, x + W / 2 - 3, y - 6 * s,
                        fill=C_FF, outline="", tags=tag)
    cv.create_rectangle(x - W / 2, y - H, x + W / 2, y - H + 4 * s,
                        fill="#eef4f8", outline="#93a9b7", tags=tag)


def draw_shroud(cv, x, y, s=1.0, ghost=False, tag="p"):
    """차광 후드 겸 받침대 (다리 두 개 + 윗판)."""
    W, H = 210 * s, 120 * s
    if ghost:
        cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, outline=C_GHOST,
                            dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - W / 2, y - H, x - W / 2 + 20 * s, y,
                        fill=C_PLASTIC, outline=C_PLASTIC_D, width=2, tags=tag)
    cv.create_rectangle(x + W / 2 - 20 * s, y - H, x + W / 2, y,
                        fill=C_PLASTIC, outline=C_PLASTIC_D, width=2, tags=tag)
    cv.create_rectangle(x - W / 2 - 6 * s, y - H - 12 * s, x + W / 2 + 6 * s,
                        y - H, fill=C_PLASTIC, outline=C_PLASTIC_D, width=2,
                        tags=tag)
    cv.create_oval(x - 14 * s, y - H - 9 * s, x + 14 * s, y - H - 3 * s,
                   fill="#d5d2c8", outline=C_PLASTIC_D, tags=tag)


def draw_lamp(cv, x, y, s=1.0, ghost=False, tag="p", on=True):
    W, H = 44 * s, 24 * s
    if ghost:
        cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, outline=C_GHOST,
                            dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, fill=C_PLASTIC,
                        outline=C_PLASTIC_D, width=2, tags=tag)
    cv.create_rectangle(x - W / 2 + 5, y, x + W / 2 - 5, y + 7 * s,
                        fill=C_LAMP if on else "#d8d6cc",
                        outline=C_PLASTIC_D, tags=tag)


def draw_camera(cv, x, y, s=1.0, ghost=False, tag="p"):
    W, H = 56 * s, 34 * s
    if ghost:
        cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, outline=C_GHOST,
                            dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, fill="#3b3f45",
                        outline="#23262a", width=2, tags=tag)
    cv.create_oval(x - 9 * s, y - 4 * s, x + 9 * s, y + 8 * s,
                   fill="#1b1e22", outline="#5c626a", width=2, tags=tag)
    cv.create_oval(x - 4 * s, y + 0 * s, x + 2 * s, y + 5 * s,
                   fill="#39434d", outline="", tags=tag)
    cv.create_rectangle(x + 10 * s, y - H - 5 * s, x + 22 * s, y - H,
                        fill="#4a5057", outline="#23262a", tags=tag)


def draw_gridstrip(cv, x, y, s=1.0, ghost=False, tag="p"):
    W, H = 120 * s, 16 * s
    if ghost:
        cv.create_rectangle(x - W / 2, y - H / 2, x + W / 2, y + H / 2,
                            outline=C_GHOST, dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - W / 2, y - H / 2, x + W / 2, y + H / 2,
                        fill="#eaf3f8", outline="#8fb0c2", tags=tag)
    n = 14
    for i in range(n + 1):
        xx = x - W / 2 + i * W / n
        cv.create_line(xx, y - H / 2, xx, y + H / 2, fill="#7ea6bc", tags=tag)
    cv.create_line(x - W / 2, y, x + W / 2, y, fill="#7ea6bc", tags=tag)


def draw_bolt(cv, x, y, s=1.0, ghost=False, tag="p"):
    """나일론 볼트 (머리가 아래)."""
    if ghost:
        cv.create_rectangle(x - 6 * s, y - 26 * s, x + 6 * s, y,
                            outline=C_GHOST, dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - 4 * s, y - 26 * s, x + 4 * s, y - 6 * s,
                        fill=C_NYLON, outline=C_NYLON_D, width=2, tags=tag)
    for i in range(7):
        yy = y - 25 * s + i * 2.8 * s
        cv.create_line(x - 4 * s, yy, x + 4 * s, yy - 1.4 * s,
                       fill=C_NYLON_D, tags=tag)
    cv.create_polygon(x - 9 * s, y - 6 * s, x + 9 * s, y - 6 * s,
                      x + 7 * s, y, x - 7 * s, y,
                      fill=C_NYLON, outline=C_NYLON_D, width=2, tags=tag)


def draw_smag(cv, x, y, s=1.0, ghost=False, tag="p"):
    if ghost:
        cv.create_rectangle(x - 12 * s, y - 5 * s, x + 12 * s, y,
                            outline=C_GHOST, dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - 12 * s, y - 5 * s, x + 12 * s, y, fill=C_METAL,
                        outline=C_METAL_D, width=2, tags=tag)
    cv.create_line(x - 12 * s, y - 4 * s, x + 12 * s, y - 4 * s,
                   fill=C_METAL_L, tags=tag)


def draw_bmag(cv, x, y, s=1.0, ghost=False, tag="p"):
    if ghost:
        cv.create_rectangle(x - 17 * s, y - 8 * s, x + 17 * s, y,
                            outline=C_GHOST, dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - 17 * s, y - 8 * s, x + 17 * s, y, fill=C_METAL,
                        outline=C_METAL_D, width=2, tags=tag)
    cv.create_line(x - 17 * s, y - 6.5 * s, x + 17 * s, y - 6.5 * s,
                   fill=C_METAL_L, tags=tag)


def draw_misc(cv, x, y, s=1.0, ghost=False, tag="p"):
    if ghost:
        cv.create_rectangle(x - 40 * s, y - 10 * s, x + 40 * s, y + 10 * s,
                            outline=C_GHOST, dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - 40 * s, y - 5 * s, x + 20 * s, y + 3 * s,
                        fill="#e8f4fb", outline="#7fa8c0", tags=tag)
    for i in range(13):
        xx = x - 39 * s + i * 4.6 * s
        cv.create_line(xx, y - 5 * s, xx, y - 1 * s, fill="#2a6383", tags=tag)
    cv.create_oval(x + 24 * s, y - 8 * s, x + 40 * s, y + 4 * s,
                   fill="#c9c3ae", outline="#a9a48f", tags=tag)


ICON = {"base": draw_base, "dish": draw_dish_side, "shroud": draw_shroud,
        "lamp": draw_lamp, "cam": draw_camera, "grid": draw_gridstrip,
        "bolts": draw_bolt, "smag": draw_smag, "bmag": draw_bmag,
        "misc": draw_misc}


# =========================================================================
#  5. 공용 위젯 : 실물 자 / 투명 그리드 스트립
# =========================================================================
class Ruler:
    """투명 30 cm 자. 눈금은 그림으로만 존재하고 수치는 표시하지 않는다."""

    def __init__(self, canvas, k, span_mm=140.0, x=40, y=40, vertical=True):
        self.cv = canvas
        self.k = k
        self.span = span_mm
        self.x, self.y = x, y
        self.vertical = vertical
        self.visible = False

    def bbox(self):
        L = self.span * self.k
        W = 34
        if self.vertical:
            return (self.x, self.y, self.x + W, self.y + L)
        return (self.x, self.y, self.x + L, self.y + W)

    def hit(self, px, py):
        x0, y0, x1, y1 = self.bbox()
        return self.visible and x0 <= px <= x1 and y0 <= py <= y1

    def draw(self, tag="ruler"):
        if not self.visible:
            return
        cv, k = self.cv, self.k
        x0, y0, x1, y1 = self.bbox()
        cv.create_rectangle(x0, y0, x1, y1, fill="#e8f4fb", outline="#7fa8c0",
                            width=1, stipple="gray50", tags=tag)
        for i in range(int(self.span) + 1):
            d = i * k
            if i % 10 == 0:
                ln, col = 22, "#0d2a3a"
            elif i % 5 == 0:
                ln, col = 15, "#16455e"
            else:
                ln, col = 9, "#2a6383"
            if self.vertical:
                cv.create_line(x0, y0 + d, x0 + ln, y0 + d, fill=col, tags=tag)
                if i % 10 == 0:
                    cv.create_text(x0 + 27, y0 + d, text=str(i // 10),
                                   font=("TkDefaultFont", 7), fill="#0d2a3a",
                                   tags=tag)
            else:
                cv.create_line(x0 + d, y0, x0 + d, y0 + ln, fill=col, tags=tag)
                if i % 10 == 0:
                    cv.create_text(x0 + d, y0 + 27, text=str(i // 10),
                                   font=("TkDefaultFont", 7), fill="#0d2a3a",
                                   tags=tag)
        cv.create_text(x0 + 17 if self.vertical else (x0 + x1) / 2,
                       y1 - 6 if self.vertical else y1 - 8,
                       text="cm", font=("TkDefaultFont", 7), fill="#0d2a3a",
                       tags=tag)


class Graticule:
    """투명 그리드 스트립. 한 칸의 실제 크기는 화면에 표시되지 않는다."""

    def __init__(self, canvas, k, pitch_mm, x=30, y=30, nx=13, ny=9):
        self.cv = canvas
        self.k = k
        self.pitch = pitch_mm
        self.x, self.y = x, y
        self.nx, self.ny = nx, ny
        self.visible = False

    def bbox(self):
        w = self.nx * self.pitch * self.k
        h = self.ny * self.pitch * self.k
        return (self.x, self.y, self.x + w, self.y + h)

    def hit(self, px, py):
        x0, y0, x1, y1 = self.bbox()
        return self.visible and x0 <= px <= x1 and y0 <= py <= y1

    def draw(self, tag="grat"):
        if not self.visible:
            return
        cv = self.cv
        p = self.pitch * self.k
        x0, y0, x1, y1 = self.bbox()
        cv.create_rectangle(x0, y0, x1, y1, outline="#63d0e8", width=2,
                            tags=tag)
        for i in range(self.nx + 1):
            xx = x0 + i * p
            cv.create_line(xx, y0, xx, y1, tags=tag, width=2,
                           fill="#63d0e8" if i % 5 == 0 else "#3fa8bf")
        for j in range(self.ny + 1):
            yy = y0 + j * p
            cv.create_line(x0, yy, x1, yy, tags=tag, width=2,
                           fill="#63d0e8" if j % 5 == 0 else "#3fa8bf")


# =========================================================================
#  6. 조립 탭 : 슬롯 정의  (slot key, 화면 x, y, 선행 슬롯)
# =========================================================================
DESK_Y = 470
SLOTS = [
    ("base",   600, 452, []),
    ("bolts",  505, 490, ["base"]),
    ("smag",   645, 450, ["base"]),
    ("dish",   600, 452, ["base"]),
    ("shroud", 600, 452, ["base", "dish"]),
    ("lamp",   556, 352, ["shroud"]),
    ("cam",    600, 320, ["shroud"]),
    ("grid",   600, 424, ["dish"]),
    ("bmag",   520, 448, ["dish"]),
    ("misc",   350, 486, []),
]
ZORDER = ["base", "bolts", "smag", "dish", "grid", "bmag", "shroud",
          "lamp", "cam", "misc"]
SLOT_LABEL_KO = {
    "base": "나무 받침대 (턱이 뒤쪽으로)",
    "bolts": "나일론 볼트 (모서리 구멍)",
    "smag": "작은 자석 (채널 안)",
    "dish": "유리접시 — 긴 변을 턱에 붙여서",
    "shroud": "차광 후드 겸 받침대",
    "lamp": "건전지 램프 (후드 안쪽)",
    "cam": "카메라 (후드 윗판 구멍 위)",
    "grid": "투명 그리드 스트립 (뚜껑 위)",
    "bmag": "큰 N42 자석 (접시 옆에 대기)",
    "misc": "자 · 블루택 · 포일",
}
SLOT_LABEL_EN = {
    "base": "Wooden base (barrier at the back)",
    "bolts": "Nylon bolts (corner holes)",
    "smag": "Small magnet (in the channel)",
    "dish": "Glass dish — long side against the barrier",
    "shroud": "Light shroud and stand",
    "lamp": "Battery lamp (inside the shroud)",
    "cam": "Camera (over the hole in the top plate)",
    "grid": "Transparent grid strip (on the lid)",
    "bmag": "Large N42 magnet (parked beside the dish)",
    "misc": "Ruler · blu-tack · foil",
}
SLOT_LABEL = SLOT_LABEL_KO if LANG == "ko" else SLOT_LABEL_EN
NEEDED = {"base", "dish", "shroud", "lamp", "cam"}


# =========================================================================
#  7. 본체
# =========================================================================
class App(tk.Tk):
    NFR = 30                      # 한 번 촬영에 남는 프레임 수

    def __init__(self):
        super().__init__()
        self.title(S["title"])
        self.geometry("1290x860")
        self.ap = Apparatus2()

        self.placed = set()
        self.drag_item = None

        self.turns = 0.0           # 볼트를 돌린 회전 (표시용 카운터)
        self.turn_ref = 0.0
        self.tilt_turns = 0.0      # 실제 기울기를 만드는 회전
        self.nsmag = 0
        self.smag_x = 60.0
        self.smag_gap = 34.0
        self.bmag_ready = False
        self.lamp_on = True

        self.wf = None
        self.rec = False
        self.frame = 0
        self.playing = False
        self.amp = 1.0
        self.jit = 0.0
        self.msg = ""

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_asm = ttk.Frame(nb)
        self.tab_ab = ttk.Frame(nb)
        self.tab_cd = ttk.Frame(nb)
        self.tab_info = ttk.Frame(nb)
        nb.add(self.tab_asm, text=S["t_asm"])
        nb.add(self.tab_ab, text=S["t_ab"])
        nb.add(self.tab_cd, text=S["t_cd"])
        nb.add(self.tab_info, text=S["t_info"])
        self.nb = nb

        self.build_asm()
        self.build_ab()
        self.build_cd()
        self.build_info()
        self.draw_asm()
        self.redraw()
        self.after(80, self._tick)

    # =============================================== 1) 조립 탭 =========
    def build_asm(self):
        top = ttk.Frame(self.tab_asm)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Button(top, text=S["auto"], command=self.auto_asm).pack(side="left")
        ttk.Button(top, text=S["reset"],
                   command=self.reset_asm).pack(side="left", padx=8)
        self.lb_asm = ttk.Label(top, text="", foreground="#177a3d")
        self.lb_asm.pack(side="left", padx=16)

        body = ttk.Frame(self.tab_asm)
        body.pack(fill="both", expand=True, padx=8, pady=4)
        self.cv_asm = tk.Canvas(body, width=1080, height=630, bg="#fbfaf7",
                                highlightthickness=1,
                                highlightbackground="#d5d2cb")
        self.cv_asm.pack(side="left")
        self.cv_asm.bind("<ButtonPress-1>", self._asm_press)
        self.cv_asm.bind("<B1-Motion>", self._asm_move)
        self.cv_asm.bind("<ButtonRelease-1>", self._asm_release)

    def _tray_box(self, i):
        return (14, 74 + i * 55, 250, 122 + i * 55)

    def draw_asm(self):
        cv = self.cv_asm
        cv.delete("all")
        cv.create_rectangle(6, 20, 258, 74 + len(PARTS) * 55 - 4,
                            fill="#eef1ea", outline="#c8cfc0")
        cv.create_text(132, 44, text=S["tray"], font=("TkDefaultFont", 10, "bold"))
        for i, (name, key) in enumerate(PARTS):
            x0, y0, x1, y1 = self._tray_box(i)
            done = key in self.placed
            cv.create_rectangle(x0, y0, x1, y1,
                                fill="#dbe5d3" if done else "#f7f9f4",
                                outline="#b6c2ab")
            ICON[key](cv, x0 + 42, y0 + 34, 0.20)
            cv.create_text(x0 + 78, (y0 + y1) / 2, anchor="w", width=150,
                           text=("✔ " if done else "") + name,
                           font=("TkDefaultFont", 8))
        cv.create_rectangle(272, 20, 1074, 616, fill="#fdfcfa",
                            outline="#e0ddd6")
        cv.create_line(292, DESK_Y + 22, 1056, DESK_Y + 22, fill="#c8bfa8",
                       width=3)
        for key in ZORDER:
            for k, x, y, need in SLOTS:
                if k != key:
                    continue
                if k in self.placed:
                    ICON[k](cv, x, y, self._scale(k))
                    if k == "bolts":
                        ICON[k](cv, x + 190, y, self._scale(k))
                else:
                    ICON[k](cv, x, y, self._scale(k), ghost=True)
                    cv.create_text(x, y + 16, text=SLOT_LABEL[k],
                                   font=("TkDefaultFont", 7), fill="#8d949b")
        self.lb_asm.config(text=S["done"] if self.assembled() else "")

    @staticmethod
    def _scale(key):
        return {"dish": 0.85, "grid": 0.8, "bolts": 1.0}.get(key, 1.0)

    def assembled(self):
        return NEEDED <= self.placed

    def auto_asm(self):
        for k, x, y, need in SLOTS:
            self.placed.add(k)
        self.draw_asm()

    def reset_asm(self):
        self.placed.clear()
        self.draw_asm()

    def _asm_press(self, e):
        if e.x > 258:
            return
        for i, (name, key) in enumerate(PARTS):
            x0, y0, x1, y1 = self._tray_box(i)
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                self.drag_item = key
                return

    def _asm_move(self, e):
        if self.drag_item is None:
            return
        self.cv_asm.delete("carry")
        self.cv_asm.create_oval(e.x - 18, e.y - 18, e.x + 18, e.y + 18,
                                outline="#3b7ea8", width=2, dash=(3, 2),
                                tags="carry")
        ICON[self.drag_item](self.cv_asm, e.x, e.y + 8, 0.3, tag="carry")

    def _asm_release(self, e):
        key = self.drag_item
        self.drag_item = None
        self.cv_asm.delete("carry")
        if key is None:
            return
        for k, x, y, need in SLOTS:
            if k != key:
                continue
            if math.hypot(e.x - x, e.y - y) < 130:
                miss = [n for n in need if n not in self.placed]
                if miss:
                    self.lb_asm.config(
                        text=S["need"] + " : " +
                        ", ".join(SLOT_LABEL[n] for n in miss),
                        foreground="#a8341f")
                    self.after(2600, lambda: self.lb_asm.config(
                        foreground="#177a3d"))
                    return
                self.placed.add(k)
        self.draw_asm()

    # =============================================== 2) 평면 펄스 탭 ====
    KS = 1.75          # 옆면도 px/mm
    KC = 3.30          # 카메라 화면 px/mm
    CX0, CY0 = 26, 22  # 카메라 화면 원점(접시 안쪽 좌상단)

    def cx(self, x_mm):
        return self.CX0 + self.KC * x_mm

    def cy(self, y_mm):
        return self.CY0 + self.KC * y_mm

    def build_ab(self):
        f = self.tab_ab
        left = ttk.Frame(f)
        left.pack(side="left", padx=6, pady=6, anchor="n")
        ttk.Label(left, text=S["side"],
                  font=("TkDefaultFont", 9, "bold")).pack(anchor="w")
        self.cv_side = tk.Canvas(left, width=430, height=252, bg="#fbfaf7",
                                 highlightthickness=1,
                                 highlightbackground="#d5d2cb")
        self.cv_side.pack()
        self.rul_s = Ruler(self.cv_side, self.KS, 90.0, 312, 20, True)
        self.cv_side.bind("<ButtonPress-1>", self._rs_press)
        self.cv_side.bind("<B1-Motion>", self._rs_move)
        ttk.Label(left, text=S["note_ab"], justify="left",
                  font=("TkDefaultFont", 8)).pack(anchor="w", pady=6)

        g = ttk.LabelFrame(left, text=S["bolts"])
        g.pack(fill="x", pady=4)
        r1 = ttk.Frame(g)
        r1.pack(fill="x", pady=2)
        ttk.Button(r1, text=S["up"] + "  " + S["turn1"],
                   command=lambda: self.turn(+1.0)).pack(side="left", padx=2)
        ttk.Button(r1, text=S["up"] + "  " + S["turn4"],
                   command=lambda: self.turn(+0.25)).pack(side="left", padx=2)
        r2 = ttk.Frame(g)
        r2.pack(fill="x", pady=2)
        ttk.Button(r2, text=S["dn"] + "  " + S["turn1"],
                   command=lambda: self.turn(-1.0)).pack(side="left", padx=2)
        ttk.Button(r2, text=S["dn"] + "  " + S["turn4"],
                   command=lambda: self.turn(-0.25)).pack(side="left", padx=2)
        r3 = ttk.Frame(g)
        r3.pack(fill="x", pady=2)
        self.lb_turn = ttk.Label(r3, text="", font=("TkDefaultFont", 9, "bold"))
        self.lb_turn.pack(side="left", padx=4)
        ttk.Button(r3, text=S["zero"],
                   command=self.zero_turn).pack(side="left", padx=6)
        ttk.Button(r3, text=S["level"],
                   command=self.make_level).pack(side="left")

        right = ttk.Frame(f)
        right.pack(side="left", padx=4, pady=6, fill="both", expand=True,
                   anchor="n")
        self.cv_cam = tk.Canvas(right, width=620, height=440, bg="#0a0a0c",
                                highlightthickness=1,
                                highlightbackground="#3a3a40")
        self.cv_cam.pack(side="top")
        self.rul_c = Ruler(self.cv_cam, self.KC, 120.0, 40, 40, False)
        self.grat = Graticule(self.cv_cam, self.KC, self.ap.grid, 30, 30)
        self.cv_cam.bind("<ButtonPress-1>", self._cam_press)
        self.cv_cam.bind("<B1-Motion>", self._cam_move)

        self.pan_ab = ttk.Frame(right)
        self.pan_ab.pack(side="top", fill="x", pady=4)
        ttk.Button(self.pan_ab, text=S["push"],
                   command=lambda: self.shoot("plane")).pack(side="left")
        self.build_play(self.pan_ab)

        pan2 = ttk.Frame(right)
        pan2.pack(side="top", fill="x")
        self.build_tools(pan2)

    def build_play(self, parent):
        g = ttk.Frame(parent)
        g.pack(side="left", padx=10)
        ttk.Button(g, text=S["first"], width=7,
                   command=lambda: self.goframe(0)).pack(side="left")
        ttk.Button(g, text=S["prev"], width=7,
                   command=lambda: self.step(-1)).pack(side="left")
        self.lb_frame = ttk.Label(g, text="", width=14, anchor="center",
                                  font=("TkDefaultFont", 10, "bold"))
        self.lb_frame.pack(side="left", padx=4)
        ttk.Button(g, text=S["next"], width=7,
                   command=lambda: self.step(+1)).pack(side="left")
        self.bt_play = ttk.Button(g, text=S["play"], width=7,
                                  command=self.toggle_play)
        self.bt_play.pack(side="left", padx=6)

    def build_tools(self, parent):
        g = ttk.LabelFrame(parent, text=S["tools"])
        g.pack(side="left", fill="x", padx=2)
        self.v_rul = tk.BooleanVar(value=False)
        self.v_rulv = tk.BooleanVar(value=False)
        self.v_grat = tk.BooleanVar(value=False)
        self.v_lamp = tk.BooleanVar(value=True)
        ttk.Checkbutton(g, text=S["showrul"], variable=self.v_rul,
                        command=self.redraw).pack(side="left", padx=4)
        ttk.Checkbutton(g, text=S["vert"], variable=self.v_rulv,
                        command=self.redraw).pack(side="left")
        ttk.Checkbutton(g, text=S["showgrid"], variable=self.v_grat,
                        command=self.redraw).pack(side="left", padx=8)
        ttk.Checkbutton(g, text=S["lamp"] + " " + S["on"], variable=self.v_lamp,
                        command=self.redraw).pack(side="left", padx=8)

    # ------------------------------------------------------- 볼트 조작
    def turn(self, dt):
        self.turns += dt
        self.tilt_turns = max(0.0, self.tilt_turns + dt)
        self.invalidate()
        self.redraw()

    def zero_turn(self):
        self.turns = 0.0
        self.redraw()

    def make_level(self):
        self.turns = 0.0
        self.tilt_turns = 0.0
        self.invalidate()
        self.redraw()

    def tan_th(self):
        return self.ap.tilt(self.tilt_turns)

    # =============================================== 3) 자석 탭 =========
    def build_cd(self):
        f = self.tab_cd
        left = ttk.Frame(f)
        left.pack(side="left", padx=6, pady=6, anchor="n")
        ttk.Label(left, text=S["note_cd"], justify="left",
                  font=("TkDefaultFont", 8)).pack(anchor="w")

        g = ttk.LabelFrame(left, text=S["smag"])
        g.pack(fill="x", pady=6)
        self.v_ns = tk.IntVar(value=0)
        for n, key in ((0, "n0"), (1, "n1"), (2, "n2")):
            ttk.Radiobutton(g, text=S[key], value=n, variable=self.v_ns,
                            command=self.set_nsmag).pack(anchor="w")
        r = ttk.Frame(g)
        r.pack(fill="x", pady=3)
        ttk.Button(r, text=S["movl"], width=8,
                   command=lambda: self.move_smag(-4)).pack(side="left")
        ttk.Button(r, text=S["movr"], width=8,
                   command=lambda: self.move_smag(+4)).pack(side="left")
        r = ttk.Frame(g)
        r.pack(fill="x", pady=3)
        ttk.Label(r, text=S["gap"]).pack(side="left")
        ttk.Button(r, text=S["narrower"], width=7,
                   command=lambda: self.set_gap(-3)).pack(side="left", padx=2)
        ttk.Button(r, text=S["wider"], width=7,
                   command=lambda: self.set_gap(+3)).pack(side="left")

        g2 = ttk.LabelFrame(left, text="구동" if LANG == "ko" else "Driving")
        g2.pack(fill="x", pady=6)
        ttk.Button(g2, text=S["push"],
                   command=lambda: self.shoot("plane")).pack(fill="x", pady=2)
        ttk.Button(g2, text=S["pushbase"],
                   command=lambda: self.shoot("plane2")).pack(fill="x", pady=2)
        self.bt_setmag = ttk.Button(g2, text=S["setmag"], command=self.set_bmag)
        self.bt_setmag.pack(fill="x", pady=2)
        self.bt_pull = ttk.Button(g2, text=S["pullmag"],
                                  command=lambda: self.shoot("point"))
        self.bt_pull.pack(fill="x", pady=2)
        self.lb_cd = ttk.Label(left, text="", foreground="#1d4f7a",
                               font=("TkDefaultFont", 8))
        self.lb_cd.pack(anchor="w")

        right = ttk.Frame(f)
        right.pack(side="left", padx=4, pady=6, fill="both", expand=True,
                   anchor="n")
        self.cv_cam2 = tk.Canvas(right, width=620, height=440, bg="#0a0a0c",
                                 highlightthickness=1,
                                 highlightbackground="#3a3a40")
        self.cv_cam2.pack(side="top")
        self.rul_c2 = Ruler(self.cv_cam2, self.KC, 120.0, 40, 40, False)
        self.grat2 = Graticule(self.cv_cam2, self.KC, self.ap.grid, 30, 30)
        self.cv_cam2.bind("<ButtonPress-1>", self._cam2_press)
        self.cv_cam2.bind("<B1-Motion>", self._cam2_move)

        pan = ttk.Frame(right)
        pan.pack(side="top", fill="x", pady=4)
        g = ttk.Frame(pan)
        g.pack(side="left")
        ttk.Button(g, text=S["first"], width=7,
                   command=lambda: self.goframe(0)).pack(side="left")
        ttk.Button(g, text=S["prev"], width=7,
                   command=lambda: self.step(-1)).pack(side="left")
        self.lb_frame2 = ttk.Label(g, text="", width=14, anchor="center",
                                   font=("TkDefaultFont", 10, "bold"))
        self.lb_frame2.pack(side="left", padx=4)
        ttk.Button(g, text=S["next"], width=7,
                   command=lambda: self.step(+1)).pack(side="left")
        self.bt_play2 = ttk.Button(g, text=S["play"], width=7,
                                   command=self.toggle_play)
        self.bt_play2.pack(side="left", padx=6)

        g2 = ttk.LabelFrame(pan, text=S["tools"])
        g2.pack(side="left", padx=8)
        ttk.Checkbutton(g2, text=S["showrul"], variable=self.v_rul,
                        command=self.redraw).pack(side="left", padx=4)
        ttk.Checkbutton(g2, text=S["showgrid"], variable=self.v_grat,
                        command=self.redraw).pack(side="left", padx=4)

    def set_nsmag(self):
        self.nsmag = self.v_ns.get()
        self.invalidate()
        self.redraw()

    def move_smag(self, d):
        self.smag_x = min(self.ap.Lx - 26, max(26.0, self.smag_x + d))
        self.invalidate()
        self.redraw()

    def set_gap(self, d):
        self.smag_gap = min(80.0, max(26.0, self.smag_gap + d))
        self.invalidate()
        self.redraw()

    def set_bmag(self):
        self.bmag_ready = True
        self.lb_cd.config(text=S["magready"])
        self.redraw()

    def mags(self):
        if self.nsmag == 0:
            return []
        yc = self.ap.Ly / 2.0
        if self.nsmag == 1:
            return [(self.smag_x, yc)]
        return [(self.smag_x, yc - self.smag_gap / 2.0),
                (self.smag_x, yc + self.smag_gap / 2.0)]

    # =============================================== 촬영 / 재생 ========
    def invalidate(self):
        self.wf = None
        self.rec = False
        self.frame = 0
        self.playing = False

    def shoot(self, kind):
        if not self.assembled():
            self.lb_asm.config(text=S["need"])
            self.nb.select(self.tab_asm)
            return
        if kind == "point":
            if not self.bmag_ready:
                self.lb_cd.config(text=S["setmag"])
                return
            self.bmag_ready = False
            self.lb_cd.config(text="")
            src = ("point", 7.0, self.ap.Ly / 2.0)
        elif kind == "plane2":
            src = ("plane2",)
        else:
            src = ("plane",)
        self.amp = self.ap.reroll_push()
        self.jit = self.ap.push_jitter
        self.wf = WaveField(self.ap, self.tan_th(), self.mags(), src)
        self.rec = True
        self.frame = 0
        self.playing = False
        self.redraw()

    def goframe(self, n):
        self.frame = max(0, min(self.NFR, n))
        self.redraw()

    def step(self, d):
        if not self.rec:
            return
        self.goframe(self.frame + d)

    def toggle_play(self):
        self.playing = not self.playing and self.rec

    def _tick(self):
        if self.playing and self.rec:
            if self.frame >= self.NFR:
                self.playing = False
            else:
                self.frame += 1
                self.redraw()
            self.after(220, self._tick)
        else:
            self.after(120, self._tick)

    def cur_t(self):
        return self.frame / float(self.ap.fps) + self.jit

    # =============================================== 그리기 =============
    def redraw(self):
        self.draw_side()
        for cv, rul, gr, lb in ((self.cv_cam, self.rul_c, self.grat,
                                 self.lb_frame),
                                (self.cv_cam2, self.rul_c2, self.grat2,
                                 self.lb_frame2)):
            self.draw_cam(cv, rul, gr)
            lb.config(text=("%s %d" % (S["frame"], self.frame)) if self.rec
                      else S["live"])
        q = self.turns
        sgn = "" if q >= 0 else "-"
        a = abs(q)
        whole = int(a)
        frac = a - whole
        fs = {0.0: "", 0.25: " ¼", 0.5: " ½", 0.75: " ¾"}.get(round(frac, 2),
                                                              "")
        self.lb_turn.config(text="%s : %s%d%s" % (S["turns"], sgn, whole, fs))
        self.bt_play.config(text=S["stop"] if self.playing else S["play"])
        self.bt_play2.config(text=S["stop"] if self.playing else S["play"])

    # -------------------------------------------------------- 옆면도
    def draw_side(self):
        cv = self.cv_side
        cv.delete("all")
        k = self.KS
        ap = self.ap
        x0, ybase = 40, 214
        L = ap.base_len
        h = self.tilt_turns * ap.bolt_pitch      # 들어올린 높이 [mm]
        cv.create_line(10, ybase + 22, 420, ybase + 22, fill="#c8bfa8", width=3)
        # 나무 받침대 (왼쪽이 볼트, 오른쪽이 힌지)
        ax, ay = x0, ybase - h * k
        bx, by = x0 + L * k, ybase
        th = 14 * k * 0.6
        cv.create_polygon(ax, ay, bx, by, bx, by + th, ax, ay + th,
                          fill=C_WOOD, outline=C_WOOD_D, width=2)
        # 나일론 볼트
        cv.create_rectangle(ax + 4, ay + th, ax + 14, ybase + 22,
                            fill=C_NYLON, outline=C_NYLON_D, width=2)
        for i in range(max(1, int((ybase + 22 - ay - th) / 6))):
            yy = ay + th + 4 + i * 6
            cv.create_line(ax + 4, yy, ax + 14, yy - 3, fill=C_NYLON_D)
        cv.create_polygon(bx - 12, by + th, bx + 2, by + th, bx + 2, ybase + 22,
                          bx - 12, ybase + 22, fill="#b9a179", outline=C_WOOD_D)
        # 유리접시 (받침대 위, 같은 기울기)
        ux = (bx - ax) / max(1e-6, math.hypot(bx - ax, by - ay))
        uy = (by - ay) / max(1e-6, math.hypot(bx - ax, by - ay))
        px, py = -uy, ux
        d0x = ax + ux * 12
        d0y = ay + uy * 12
        dl = ap.Ly * k
        hh = 30 * k * 0.6
        cv.create_polygon(d0x, d0y, d0x + ux * dl, d0y + uy * dl,
                          d0x + ux * dl - px * hh, d0y + uy * dl - py * hh,
                          d0x - px * hh, d0y - py * hh,
                          fill=C_GLASS, outline="#93a9b7", width=2)
        # 유체 쐐기 (수평면!)
        tan = self.tan_th()
        y0 = ap.water_line(tan)
        pts = []
        n = 24
        for i in range(n + 1):
            yy = ap.Ly * i / n
            d = ap.depth(yy, tan)
            bxp = d0x + ux * yy * k
            byp = d0y + uy * yy * k
            pts.append((bxp - px * 2.5 * k, byp - py * 2.5 * k))
        top = []
        for i in range(n + 1):
            yy = ap.Ly * i / n
            d = ap.depth(yy, tan)
            bxp = d0x + ux * yy * k
            byp = d0y + uy * yy * k
            top.append((bxp - px * (2.5 + d) * k, byp - py * (2.5 + d) * k))
        poly = []
        for p in pts:
            poly += [p[0], p[1]]
        for p in reversed(top):
            poly += [p[0], p[1]]
        cv.create_polygon(poly, fill=C_FF, outline="")
        cv.create_text(ax + 6, ay - 16, text="y = 0", anchor="w",
                       font=("TkDefaultFont", 8), fill="#5a6068")
        cv.create_text(bx - 6, by - 44, text="y", anchor="e",
                       font=("TkDefaultFont", 8), fill="#5a6068")
        if tan > 1e-9 and y0 > 0:
            wx = d0x + ux * y0 * k
            wy = d0y + uy * y0 * k
            cv.create_text(min(418, wx + 8), wy - 30, text=S["dry"],
                           anchor="w", font=("TkDefaultFont", 7),
                           fill="#8d949b")
        self.rul_s.visible = self.v_rul.get()
        self.rul_s.vertical = self.v_rulv.get()
        self.rul_s.draw()

    def _rs_press(self, e):
        self._rs = (e.x, e.y) if self.rul_s.hit(e.x, e.y) else None

    def _rs_move(self, e):
        if getattr(self, "_rs", None) is None:
            return
        self.rul_s.x += e.x - self._rs[0]
        self.rul_s.y += e.y - self._rs[1]
        self._rs = (e.x, e.y)
        self.draw_side()

    # -------------------------------------------------------- 카메라 화면
    def draw_cam(self, cv, rul, gr):
        cv.delete("all")
        ap = self.ap
        k = self.KC
        tan = self.tan_th()
        x0, y0 = self.cx(0), self.cy(0)
        x1, y1 = self.cx(ap.Lx), self.cy(ap.Ly)
        # 유리 벽
        w = DISH_WALL * k
        cv.create_rectangle(x0 - w, y0 - w, x1 + w, y1 + w, fill="#20262b",
                            outline="#4c565e", width=2)
        cv.create_rectangle(x0, y0, x1, y1, fill="#0b0b0e", outline="")
        if not self.v_lamp.get():
            cv.create_text((x0 + x1) / 2, (y0 + y1) / 2,
                           text=S["lampoff"], fill="#2b2b31")
            return
        # 깊이에 따른 바닥 밝기 (얕을수록 유리가 비쳐 조금 밝다)
        yw = ap.water_line(tan)
        nb = 34
        for i in range(nb):
            ya = ap.Ly * i / nb
            yb = ap.Ly * (i + 1) / nb
            d = ap.depth((ya + yb) / 2.0, tan)
            if d < 0.12:
                col = "#39424a"
            else:
                f = max(0.0, min(1.0, d / 6.0))
                g = int(26 - 14 * f)
                col = "#%02x%02x%02x" % (g, g, g + 3)
            cv.create_rectangle(x0, self.cy(ya), x1, self.cy(yb) + 1,
                                fill=col, outline="")
        if tan > 1e-9 and 0 < yw < ap.Ly:
            cv.create_line(x0, self.cy(yw), x1, self.cy(yw), fill="#5a6a76",
                           width=1, dash=(4, 3))
        # 램프 반사 (윗변 근처의 부드러운 띠)
        for i in range(6):
            cv.create_rectangle(x0, y0 + i * 3, x1, y0 + i * 3 + 3,
                                fill="#%02x%02x%02x" % (52 - i * 7, 52 - i * 7,
                                                        58 - i * 7),
                                outline="")
        # 자석 위 융기
        for (mx, my) in self.mags():
            r = ap.lump_r * 1.15
            cv.create_oval(self.cx(mx - r), self.cy(my - r),
                           self.cx(mx + r), self.cy(my + r),
                           outline="#3d444b", width=2)
            r2 = ap.lump_r * 0.72
            cv.create_oval(self.cx(mx - r2), self.cy(my - r2),
                           self.cx(mx + r2), self.cy(my + r2),
                           fill="#1a1c20", outline="#586169", width=2)
            cv.create_oval(self.cx(mx - r2 * 0.42), self.cy(my - r2 * 0.5),
                           self.cx(mx + r2 * 0.05), self.cy(my - r2 * 0.05),
                           fill="#767f88", outline="")
        # 큰 자석 대기 표시
        if self.bmag_ready:
            cv.create_rectangle(x0 - w - 26, self.cy(ap.Ly / 2 - 10),
                                x0 - w - 4, self.cy(ap.Ly / 2 + 10),
                                fill=C_METAL, outline=C_METAL_D, width=2)
            cv.create_text(x0 - w - 15, self.cy(ap.Ly / 2) - 22, text="M",
                           fill="#9aa4ad", font=("TkDefaultFont", 8, "bold"))
        # 파면
        if self.rec and self.wf is not None:
            t = self.cur_t()
            dt = 1.0 / ap.fps
            layers = ((t + 0.34 * dt, "#2f4652", 1),
                      (t, "#cfe9f5", 3),
                      (t - 0.42 * dt, "#7fa9bd", 2),
                      (t - 0.95 * dt, "#48697a", 1),
                      (t - 1.55 * dt, "#31474f", 1))
            for tt, col, wd in layers:
                if tt <= 0:
                    continue
                for (px, py, qx, qy) in self.wf.front(tt):
                    cv.create_line(self.cx(px), self.cy(py),
                                   self.cx(qx), self.cy(qy),
                                   fill=col, width=wd, capstyle="round")
        rul.visible = self.v_rul.get()
        rul.vertical = self.v_rulv.get() if rul is self.rul_c else False
        rul.draw()
        gr.visible = self.v_grat.get()
        gr.pitch = ap.grid
        gr.draw()

    def _cam_press(self, e):
        self._cd = None
        if self.grat.hit(e.x, e.y) and self.v_grat.get():
            self._cd = ("g", e.x, e.y)
        elif self.rul_c.hit(e.x, e.y):
            self._cd = ("r", e.x, e.y)

    def _cam_move(self, e):
        if self._cd is None:
            return
        kind, px, py = self._cd
        obj = self.grat if kind == "g" else self.rul_c
        obj.x += e.x - px
        obj.y += e.y - py
        self._cd = (kind, e.x, e.y)
        self.draw_cam(self.cv_cam, self.rul_c, self.grat)

    def _cam2_press(self, e):
        self._cd2 = None
        if self.grat2.hit(e.x, e.y) and self.v_grat.get():
            self._cd2 = ("g", e.x, e.y)
        elif self.rul_c2.hit(e.x, e.y):
            self._cd2 = ("r", e.x, e.y)

    def _cam2_move(self, e):
        if getattr(self, "_cd2", None) is None:
            return
        kind, px, py = self._cd2
        obj = self.grat2 if kind == "g" else self.rul_c2
        obj.x += e.x - px
        obj.y += e.y - py
        self._cd2 = (kind, e.x, e.y)
        self.draw_cam(self.cv_cam2, self.rul_c2, self.grat2)

    # =============================================== 4) 장비 탭 =========
    def build_info(self):
        f = self.tab_info
        txt = tk.Text(f, wrap="word", font=("TkDefaultFont", 9),
                      bg="#fdfcfa", relief="flat")
        txt.pack(fill="both", expand=True, padx=14, pady=10)
        txt.insert("end", S["eq"] + "\n", "h")
        for name, key in PARTS:
            txt.insert("end", "   ·  " + name + "\n")
        txt.insert("end", "\n" + ("카메라 사양" if LANG == "ko"
                                  else "Camera specification") + "\n", "h")
        txt.insert("end",
                   ("   동영상 : 25 프레임/초,  프레임 단위 재생 가능\n"
                    "   접시 안쪽 : 긴 변 x, 짧은 변 y\n" if LANG == "ko" else
                    "   Video : 25 frames per second, frame-by-frame playback\n"
                    "   Dish interior : long side x, short side y\n"))
        txt.insert("end", "\n" + S["safety"] + "\n", "h")
        for s in SAFETY:
            txt.insert("end", "   ⚠  " + s + "\n")
        txt.insert("end", "\n" + S["notshown"] + "\n", "h")
        txt.insert("end", NOTSHOWN)
        txt.tag_config("h", font=("TkDefaultFont", 10, "bold"),
                       foreground="#1d4f7a")
        txt.config(state="disabled")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
