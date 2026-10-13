#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  20th Asian Physics Olympiad  (APhO 2019, Adelaide, Australia)
  Experimental Problem E1 :  STATIC RESPONSE OF A MAGNETICALLY ACTIVE FLUID
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Apparatus rebuilt from the photographs of the problem sheet: ferrofluid
    bottle, glass dish, N42 / N52 magnets on a threaded rod, lamp, camera,
    ruler and transparent graticule.
    Only what the student would see is shown -- the fluid surface, the spikes,
    the lamp image on the camera and the rulers.  Density difference, surface
    tension, curvature radius and thresholds are never computed or shown.
    All hidden true parameters are randomised for every session.

    Run:   python3 apho2019_E1_sim_KO.py
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
#  0. 물리 상수 / 장비 제원   (문제지 Q1-2, Q1-3 에서)
# =========================================================================
MU0 = 4.0e-7 * math.pi
G = 9.81
CHI = 2.64                 # 문제지가 준 자화율
RHO_FF = 1.21e3            # 페로플루이드 밀도 [kg/m^3]

#   key : (반지름 a[mm], 두께 l[mm], 잔류자속밀도 Br[T], 표시명)
MAGNETS = {
    "N52": (7.10, 3.20, 1.40, "N52  14.2 x 3.2 mm"),
    "N42": (10.00, 5.00, 1.30, "N42  20.0 x 5.0 mm"),
    # 작은 자석 + 큰 자석을 붙여 쌓은 것 (Part D.1)
    "STACK": (10.00, 8.20, 1.34, "N52 + N42 stack"),
}

GRID_MM = 1.0              # 투명 그리드 스트립 : 1 mm 눈금


# ------------------------------------------------------------------ 자기장
def _F(u, a):
    return u / math.sqrt(u * u + a * a)


def _dF(u, a):
    return a * a / (u * u + a * a) ** 1.5


def _d2F(u, a):
    return -3.0 * a * a * u / (u * u + a * a) ** 2.5


def Bz(z, mag):
    """문제지 식 (1). z, 자석치수는 [m] 단위."""
    a, l, Br = mag[0], mag[1], mag[2]
    if z <= 1e-6:
        z = 1e-6
    return 0.5 * Br * (_F(z + l, a) - _F(z, a))


def dBz(z, mag):
    a, l, Br = mag[0], mag[1], mag[2]
    if z <= 1e-6:
        z = 1e-6
    return 0.5 * Br * (_dF(z + l, a) - _dF(z, a))


def d2Bz(z, mag):
    a, l, Br = mag[0], mag[1], mag[2]
    if z <= 1e-6:
        z = 1e-6
    return 0.5 * Br * (_d2F(z + l, a) - _d2F(z, a))


def mag_si(key):
    """MAGNETS 항목을 SI 로."""
    a, l, Br, _ = MAGNETS[key]
    return (a * 1e-3, l * 1e-3, Br)


# =========================================================================
#  1. 은닉 참값 — 세션마다 무작위 (학생은 절대 볼 수 없다)
# =========================================================================
class Apparatus:
    def __init__(self, seed=None):
        rng = random.Random(seed)
        self.rng = rng

        # --- 유체 -------------------------------------------------------
        # 병 안 : 페로플루이드 / 투명유체 밀도차
        self.drho = 15.0 * rng.uniform(0.93, 1.07)          # [kg/m^3]
        # 병 안 계면장력 -> lambda ~ 6 mm 가 되도록
        lam_b = 6.0e-3 * rng.uniform(0.93, 1.07)            # [m]
        self.sigma_c = G * self.drho * lam_b ** 2 / (4 * math.pi ** 2)
        self.lam_b = 2 * math.pi * math.sqrt(self.sigma_c / (G * self.drho))
        # 접시 : 페로플루이드 / 공기 계면장력 -> lambda ~ 8.75 mm
        self.sigma_a = 2.30e-2 * rng.uniform(0.93, 1.07)
        self.lam_a = 2 * math.pi * math.sqrt(self.sigma_a / (G * RHO_FF))

        # 초상자성체 포화자화 (문제지는 chi 를 상수로 주지만 실제로는 포화한다)
        self.Ms = 15500.0 * rng.uniform(0.95, 1.05)          # [A/m]

        # --- 기구 치수 [mm] ---------------------------------------------
        self.pitch = 0.800 * rng.uniform(0.995, 1.005)       # 나사 피치
        self.dish_base = 8.0 * rng.uniform(0.97, 1.03)       # 접시 바닥 유리 두께
        self.depth = 4.0 * rng.uniform(0.95, 1.05)           # 접시 속 유체 깊이
        self.offset = self.dish_base + self.depth            # 받침대 윗면 -> 유체면
        self.lamp_h = 34.0 * rng.uniform(0.965, 1.035)         # 유체면 -> 램프 (물체거리)
        self.lamp_len = 20.0 * rng.uniform(0.97, 1.03)       # 램프 발광부 길이 [mm]
        self.blur = 2.2                                      # 상 번짐 하한 [mm]

        # --- 병 : 스파이크 시작 문턱 ------------------------------------
        zc = 22.0e-3 * rng.uniform(0.94, 1.06)
        self.B_thr_bottle = Bz(zc, mag_si("N52"))
        self.z_crit_bottle = zc * 1e3                        # [mm] (검증용)

        # --- 접시 : 스파이크 개수 문턱 (STACK 기준, 경험값) --------------
        self.B1_spike = 0.0288 * rng.uniform(0.95, 1.05)     # 1번째 스파이크
        self.spike_ratio = 1.129 * rng.uniform(0.99, 1.01)   # 등비
        self.hyst = 1.25 * rng.uniform(0.94, 1.06)           # 소멸/생성 문턱 비
        self.N_MAX = 12

        # --- 융기(lump) 높이 : E2 와 공유하는 값 ------------------------
        self.lump_h = 5.0 * rng.uniform(0.9, 1.1)

    # ------------------------------------------------------- 자화(포화)
    def Mmag(self, H):
        """랑주뱅 자화 곡선. 저자기장에서 M -> chi*H (문제지와 일치)."""
        x = 3.0 * CHI * H / self.Ms
        if x < 1e-4:
            return CHI * H
        if x > 60.0:
            return self.Ms
        return self.Ms * (1.0 / math.tanh(x) - 1.0 / x)

    # ------------------------------------------------ Part A : 부양 평형
    def z_balance(self, key):
        """자기력 = 순 부력 이 되는 자석면-유체 거리 [mm]."""
        a, l, Br = mag_si(key)
        K = 3.0 * CHI * Br ** 2 * a ** 4 * l ** 2 / (8.0 * MU0)
        return (K / (self.drho * G)) ** (1.0 / 7.0) * 1e3

    def lift_force_ratio(self, z_mm, key):
        """(자기력)/(순 부력).  1 보다 크면 뜬다.

        Part A 는 문제지가 명시적으로 허용한 쌍극자 근사(식 3)를 그대로 쓴다.
        (식 1+2 의 완전한 장을 쓰면 같은 z 에서 힘이 약 1/1.57 이 되어
         공식 해설의 drho = 15 kg/m^3 과 어긋난다 — README 참조)"""
        z = max(z_mm, 0.05) * 1e-3
        a, l, Br = mag_si(key)
        K = 3.0 * CHI * Br ** 2 * a ** 4 * l ** 2 / (8.0 * MU0)
        return K / z ** 7 / (self.drho * G)

    # ------------------------------------------- Part C : 표면 곡률반지름
    def R_curv(self, z_mm, key):
        """유체면 중심의 유효 곡률반지름 [mm].
           자유표면 :  rho g h = u(B),  u' = M(H)/2
           1/R = |M(H0) * gamma| / (2 B0 rho g),  gamma = B'^2/2 - B B''"""
        z = max(z_mm, 0.05) * 1e-3
        m = mag_si(key)
        b, b1, b2 = Bz(z, m), dBz(z, m), d2Bz(z, m)
        gam = abs(0.5 * b1 * b1 - b * b2)
        if gam < 1e-30:
            return 1e9
        Mv = self.Mmag(b / MU0)
        R = 2.0 * b * RHO_FF * G / (Mv * gam)
        return R * 1e3

    def image_len(self, z_mm, key):
        """카메라에 보이는 반사 광원상의 길이 [mm]  (구면거울 M = R/(R+2l))."""
        R = self.R_curv(z_mm, key)
        M = R / (R + 2.0 * self.lamp_h)
        L = self.lamp_len * M
        # 광원 크기·초점흐림 때문에 아무리 작아도 이 이하로는 안 보인다
        return math.sqrt(L * L + self.blur * self.blur)

    # ------------------------------------------- Part D : 스파이크 개수
    def spike_thresholds(self, n):
        up = self.B1_spike * self.spike_ratio ** (n - 1)
        return up, up / self.hyst


# =========================================================================
#  2. 다국어 문자열
# =========================================================================
S_KO = {
    "title": "APhO 2019 실험 1 — 자기 활성 유체의 정적 응답 (가상 실험실)",
    "t_asm": "1. 장비 배치·조립",
    "t_bottle": "2. 병 실험 (Part A · B)",
    "t_dish": "3. 접시 실험 (Part C · D)",
    "t_info": "장비 목록 · 주의사항",
    "setup": "실험 구성",
    "set_ab": "A·B  유리병",
    "set_cd": "C·D  유리접시",
    "tray": "부품 상자 — 끌어다 놓으세요",
    "reset": "전부 분해",
    "auto": "자동 조립",
    "need": "먼저 필요한 부품",
    "done": "조립 완료 — 다음 탭으로 이동하세요.",
    "wrong": "여기에는 놓을 수 없습니다.",
    "notyet": "먼저 놓아야 할 부품이 있습니다.",
    "magnet": "자석",
    "carrier": "자석 캐리어 (나사봉)",
    "up": "▲ 올림", "dn": "▼ 내림",
    "fine": "미세 (1/4 회전)", "coarse": "거칠게 (5 회전)",
    "turns": "돌린 회전수",
    "zero": "회전수 영점",
    "ruler": "자 (30 cm)",
    "show": "표시",
    "vert": "세로", "horz": "가로",
    "grid": "투명 그리드 스트립",
    "zoom": "확대경",
    "lamp": "램프",
    "on": "켬", "off": "끔",
    "view": "화면",
    "v_side": "옆에서 보기", "v_cam": "카메라 (위에서)",
    "v_thread": "나사봉 확대 (C.1)",
    "hint_ab": "자석을 천천히 내려서 페로플루이드가 떠오르는 순간을 찾으세요.\n"
               "자를 끌어다 자석면과 유체 사이 거리를 읽습니다.",
    "hint_cd": "나사봉을 돌려 자석을 올리고 내리면서, 카메라에 비친\n"
               "램프 반사상의 길이를 그리드로 읽으세요.",
    "blob_up": "페로플루이드가 떠올랐습니다",
    "blob_dn": "페로플루이드가 가라앉았습니다",
    "spikes": "스파이크",
    "stuck": "⚠ 자석을 10초 이상 유체에 바짝 붙였습니다 — 잔류자화로 거동이 달라집니다",
    "release": "유체 흔들어 풀기",
    "flush": "자석 윗면이 받침대 윗면과 나란합니다",
    "wheel": "(캔버스에서 휠을 굴려도 됩니다)",
    "nocalc": "이 시뮬레이터는 어떤 물리량도 대신 계산하지 않습니다.",
    "mm": "mm",
    "stack_note": "작은 자석 + 큰 자석 (겹쳐 쌓음)",
    "no_dish": "접시 구성이 조립되지 않았습니다.",
    "no_bottle": "병 구성이 조립되지 않았습니다.",
    "goto": "[1. 장비 배치·조립] 탭에서 먼저 조립하세요.",
}
S_EN = {
    "title": "APhO 2019 Experiment 1 — Static response of a magnetically "
             "active fluid (Virtual Laboratory)",
    "t_asm": "1. Set-up & assembly",
    "t_bottle": "2. Bottle experiment (Part A · B)",
    "t_dish": "3. Dish experiment (Part C · D)",
    "t_info": "Equipment list · Safety",
    "setup": "Configuration",
    "set_ab": "A·B  glass bottle",
    "set_cd": "C·D  glass dish",
    "tray": "Parts tray — drag onto the bench",
    "reset": "Disassemble all",
    "auto": "Auto-assemble",
    "need": "Required first",
    "done": "Assembly complete — move to the next tab.",
    "wrong": "That does not go here.",
    "notyet": "Another part must be placed first.",
    "magnet": "Magnet",
    "carrier": "Magnet carrier (threaded rod)",
    "up": "▲ raise", "dn": "▼ lower",
    "fine": "fine (1/4 turn)", "coarse": "coarse (5 turns)",
    "turns": "turns made",
    "zero": "zero the counter",
    "ruler": "Ruler (30 cm)",
    "show": "show",
    "vert": "vertical", "horz": "horizontal",
    "grid": "Transparent grid strip",
    "zoom": "Magnifier",
    "lamp": "Lamp",
    "on": "on", "off": "off",
    "view": "View",
    "v_side": "side view", "v_cam": "camera (from above)",
    "v_thread": "threaded rod close-up (C.1)",
    "hint_ab": "Lower the magnet slowly and find the moment the ferrofluid "
               "lifts.\nDrag the ruler to read the gap between the magnet "
               "face and the fluid.",
    "hint_cd": "Turn the threaded rod to raise/lower the magnet and read the "
               "length\nof the reflected lamp image on the grid.",
    "blob_up": "the ferrofluid has lifted",
    "blob_dn": "the ferrofluid has settled",
    "spikes": "spikes",
    "stuck": "⚠ magnet held against the fluid for over 10 s — residual "
             "magnetisation changes the behaviour",
    "release": "shake the fluid free",
    "flush": "magnet top face is level with the top of the stand",
    "wheel": "(the mouse wheel over the canvas works too)",
    "nocalc": "This simulator never computes a physical quantity for you.",
    "mm": "mm",
    "stack_note": "small magnet + large magnet (stacked)",
    "no_dish": "The dish configuration is not assembled.",
    "no_bottle": "The bottle configuration is not assembled.",
    "goto": "Assemble it first in the [1. Set-up & assembly] tab.",
}
S = S_KO if LANG == "ko" else S_EN

# 부품 목록 (문제지 Equipment List 번호 그대로)
PARTS_KO = {
    1: "유리병 (페로플루이드+투명유체)",
    2: "유리접시 (뚜껑 밀봉, 페로플루이드)",
    3: "차광 후드 겸 받침대",
    4: "알루미늄 관 + 자석 캐리어",
    5: "나무 받침판 (수평 조절 볼트)",
    6: "카메라 (메모리카드 포함)",
    7: "N52 자석  14.2 x 3.2 mm  (2개)",
    8: "N42 자석  20.0 x 5.0 mm  (1개)",
    9: "500 mm 나사봉 (램프 기둥)",
    10: "와셔 + 나비너트",
    11: "건전지 램프 (나사 구멍)",
    12: "알루미늄 포일",
    13: "블루택",
    14: "초록 쐐기",
    15: "투명 30 cm 자",
    16: "투명 그리드 스트립 (4개)",
    17: "나무 스페이서 (2개)",
    18: "종이 줄자",
}
PARTS_EN = {
    1: "Small glass bottle (ferrofluid under clear medium)",
    2: "Glass dish with sealed lid (ferrofluid)",
    3: "Combination light shroud and stand",
    4: "Tube with adjustable magnet carrier",
    5: "Adjustable wooden base (nylon levelling bolts)",
    6: "Camera with memory card",
    7: "2 x N52 magnet, 14.2 x 3.2 mm",
    8: "1 x N42 magnet, 20.0 x 5.0 mm",
    9: "500 mm threaded rod (lamp pole)",
    10: "Washer and wing nut",
    11: "Battery-powered lamp (threaded hole)",
    12: "Aluminium foil",
    13: "Blutack",
    14: "Green wedge",
    15: "Transparent 30 cm ruler",
    16: "4 x transparent grid strips",
    17: "2 x wooden spacers",
    18: "Paper tape measure",
}
PARTS = PARTS_KO if LANG == "ko" else PARTS_EN

SAFETY_KO = """\
안전 및 주의 (문제지 Q1-3)

• 고자력 자석입니다. 서로 붙게 두면 손가락이 끼거나 자석이 깨질 수 있습니다.
  깨진 자석은 교체되지 않습니다. 보관할 때는 충분히 떨어뜨려 두세요.
• 작은 유리병과 유리접시의 뚜껑은 어떤 이유로도 열 수 없습니다.
• 접시 옆면에 페로플루이드가 묻으면 안이 보이지 않으니 불필요하게 기울이지 마세요.
• 자석을 페로플루이드에 10초 이상 바짝 대고 있으면 잔류자화와 주위 유체와의
  상호작용 때문에 유체 거동이 달라집니다. 실험은 계속할 수 있으나 관찰이 어려워집니다.
• 램프는 건전지식입니다. 필요하면 여분 건전지 1세트를 요청할 수 있습니다.

이 시뮬레이터가 보여주는 것 / 보여주지 않는 것

  보여줌 : 실제 눈금(자·줄자·그리드), 직접 센 나사 회전수, 관찰 화면.
  안 보여줌 : z, R, 배율 M, 표면장력, 밀도차, 지수 n, 그래프, 채점.
  ─ 모든 판독·계산·오차평가는 여러분 몫입니다.
"""
SAFETY_EN = """\
Safety and important notes (problem sheet Q1-3)

• These are high strength magnets. If allowed to attract each other they may
  pinch fingers or shatter. Broken magnets will not be replaced. Store them
  well apart.
• The small glass bottle and the sealed glass dish must NEVER be opened.
• If the sides of the dish get coated with ferrofluid they become opaque, so
  do not tip the dish unnecessarily.
• Holding a magnet close against the ferrofluid for more than about ten
  seconds changes its behaviour through residual magnetisation.
• The lamp is battery operated; one spare set of batteries may be requested.

What this simulator does and does not show

  Shown     : real scales (ruler, tape, grid), the turns you counted yourself,
              and the observed view.
  Not shown : z, R, magnification M, surface tension, density difference, the
              exponent n, any graph, any score.
  - every reading, calculation and uncertainty estimate is yours to make.
"""
SAFETY = SAFETY_KO if LANG == "ko" else SAFETY_EN


# =========================================================================
#  3. 부품 그리기 (문제지 사진을 본떠 2D 로 재현)
# =========================================================================
C_METAL = "#b9bec4"
C_METAL_D = "#7f858c"
C_METAL_L = "#e6e9ec"
C_PLASTIC = "#eceae4"
C_PLASTIC_D = "#c4c0b6"
C_WOOD = "#d9b378"
C_WOOD_D = "#a8823f"
C_FF = "#141418"
C_FF_HL = "#4a4a56"
C_GREEN = "#1f8f4a"
C_GREEN_D = "#146634"
C_GLASS = "#dfe8ee"
C_GHOST = "#9aa4ad"
C_LAMP = "#f7f3d8"


def _poly(cv, pts, **kw):
    return cv.create_polygon(pts, **kw)


def draw_stand(cv, x, y, s=1.0, ghost=False, tag="p"):
    """차광 후드 겸 받침대 (사진: 흰 플라스틱 스툴 모양, 윗면에 구멍들)."""
    o = dict(outline=C_GHOST, fill="", dash=(4, 3), width=2, tags=tag) if ghost \
        else dict(outline=C_PLASTIC_D, fill=C_PLASTIC, width=2, tags=tag)
    W, H, T = 300 * s, 130 * s, 26 * s
    # 윗면 (약간의 원근)
    _poly(cv, [x - W / 2, y, x + W / 2, y,
               x + W / 2 - 22 * s, y - T, x - W / 2 + 22 * s, y - T], **o)
    # 몸통 (사다리꼴 다리)
    _poly(cv, [x - W / 2, y, x + W / 2, y, x + W / 2 + 10 * s, y + H,
               x + W / 2 - 34 * s, y + H, x + W / 2 - 34 * s, y + 30 * s,
               x - W / 2 + 34 * s, y + 30 * s, x - W / 2 + 34 * s, y + H,
               x - W / 2 - 10 * s, y + H], **o)
    if not ghost:
        # 윗면 환기 구멍
        for r in range(2):
            for c in range(7):
                cx = x - 78 * s + c * 26 * s
                cy = y - 8 * s - r * 11 * s
                rr = 5.5 * s
                cv.create_oval(cx - rr, cy - rr * 0.55, cx + rr,
                               cy + rr * 0.55, fill="#4a4a4a",
                               outline="", tags=tag)
        # 가운데 큰 구멍
        cv.create_oval(x - 13 * s, y - 17 * s, x + 13 * s, y - 6 * s,
                       fill="#3a3a3a", outline=C_PLASTIC_D, tags=tag)
        # 옆면 관 통과 구멍
        cv.create_oval(x - W / 2 - 4 * s, y + 44 * s, x - W / 2 + 10 * s,
                       y + 58 * s, fill="#3a3a3a", outline="", tags=tag)
    return tag


def draw_tube(cv, x, y, s=1.0, ghost=False, tag="p"):
    """알루미늄 관 (가로)."""
    L, D = 330 * s, 17 * s
    if ghost:
        cv.create_rectangle(x - L / 2, y - D / 2, x + L / 2, y + D / 2,
                            outline=C_GHOST, dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - L / 2, y - D / 2, x + L / 2, y + D / 2,
                        fill=C_METAL, outline=C_METAL_D, tags=tag)
    cv.create_line(x - L / 2, y - D / 4, x + L / 2, y - D / 4,
                   fill=C_METAL_L, width=max(1, int(2 * s)), tags=tag)
    cv.create_oval(x + L / 2 - 5 * s, y - D / 2, x + L / 2 + 5 * s, y + D / 2,
                   fill=C_METAL_L, outline=C_METAL_D, tags=tag)


def draw_rod(cv, x, y0, y1, s=1.0, ghost=False, tag="p", pitch_px=5.0):
    """나사봉 : 지그재그 나사산."""
    w = 5.0 * s
    if ghost:
        cv.create_rectangle(x - w, y0, x + w, y1, outline=C_GHOST,
                            dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - w, y0, x + w, y1, fill=C_METAL,
                        outline=C_METAL_D, tags=tag)
    yy = y0
    while yy < y1:
        cv.create_line(x - w, yy, x + w, yy + pitch_px * 0.55,
                       fill=C_METAL_D, tags=tag)
        yy += pitch_px
    cv.create_line(x - w * 0.35, y0, x - w * 0.35, y1, fill=C_METAL_L, tags=tag)


def draw_magnet(cv, x, y, dia_mm, th_mm, ppm, tag="p", ghost=False,
                stack=False):
    """자석 (옆에서 본 원기둥). y = 아랫면."""
    w = dia_mm * ppm / 2.0
    h = th_mm * ppm
    if ghost:
        cv.create_rectangle(x - w, y - h, x + w, y, outline=C_GHOST,
                            dash=(4, 3), width=2, tags=tag)
        return
    if stack:
        h1 = h * 3.2 / 8.2
        cv.create_rectangle(x - w * 0.71, y - h, x + w * 0.71, y - h + h1,
                            fill=C_METAL_L, outline=C_METAL_D, tags=tag)
        cv.create_rectangle(x - w, y - h + h1, x + w, y,
                            fill=C_METAL, outline=C_METAL_D, tags=tag)
    else:
        cv.create_rectangle(x - w, y - h, x + w, y, fill=C_METAL,
                            outline=C_METAL_D, width=1, tags=tag)
        cv.create_line(x - w, y - h * 0.72, x + w, y - h * 0.72,
                       fill=C_METAL_L, tags=tag)


def draw_wedge(cv, x, y, s=1.0, ghost=False, tag="p"):
    """초록 쐐기 (두꺼운 쪽이 왼쪽)."""
    W, H = 120 * s, 44 * s
    pts = [x - W / 2, y, x + W / 2, y, x + W / 2, y - 8 * s, x - W / 2, y - H]
    if ghost:
        _poly(cv, pts, outline=C_GHOST, fill="", dash=(4, 3), width=2, tags=tag)
        return
    _poly(cv, pts, outline=C_GREEN_D, fill=C_GREEN, width=2, tags=tag)
    _poly(cv, [x - W / 2, y - H, x + W / 2, y - 8 * s, x + W / 2 + 16 * s,
               y - 13 * s, x - W / 2 + 16 * s, y - H - 5 * s],
          outline=C_GREEN_D, fill="#2aa85c", tags=tag)


def draw_bottle(cv, x, y, s=1.0, ghost=False, tag="p"):
    """작은 유리병 (옆으로 눕힘). y = 병 아래 바깥면, x = 중심."""
    L, D = 150 * s, 62 * s
    if ghost:
        cv.create_rectangle(x - L / 2, y - D, x + L / 2, y, outline=C_GHOST,
                            dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - L / 2, y - D, x + L / 2 - 34 * s, y,
                        fill=C_GLASS, outline="#9db4c2", width=2, tags=tag)
    cv.create_rectangle(x + L / 2 - 34 * s, y - D * 0.72, x + L / 2 - 16 * s,
                        y - D * 0.28, fill=C_GLASS, outline="#9db4c2",
                        width=2, tags=tag)
    cv.create_rectangle(x + L / 2 - 16 * s, y - D * 0.76, x + L / 2,
                        y - D * 0.24, fill="#f2f2f0", outline="#b9b9b4",
                        width=2, tags=tag)   # 흰 뚜껑
    cv.create_oval(x - L / 2 - 6 * s, y - D, x - L / 2 + 6 * s, y,
                   fill="#eef4f8", outline="#9db4c2", tags=tag)


def draw_dish(cv, x, y, s=1.0, ghost=False, tag="p"):
    """유리접시 + 밀봉 뚜껑 (옆에서)."""
    W, H = 210 * s, 52 * s
    if ghost:
        cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, outline=C_GHOST,
                            dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, fill=C_GLASS,
                        outline="#93a7b4", width=2, tags=tag)
    cv.create_rectangle(x - W / 2, y - 11 * s, x + W / 2, y, fill="#c9d6de",
                        outline="#93a7b4", tags=tag)      # 두꺼운 바닥
    cv.create_rectangle(x - W / 2 + 3 * s, y - 20 * s, x + W / 2 - 3 * s,
                        y - 11 * s, fill=C_FF, outline="", tags=tag)
    cv.create_rectangle(x - W / 2 - 6 * s, y - H - 9 * s, x + W / 2 + 6 * s,
                        y - H, fill="#d3d8dc", outline="#9aa2a8",
                        width=2, tags=tag)                # 뚜껑
    for i in range(4):
        cv.create_line(x - W / 2 + 12 * s + i * 50 * s, y - H - 9 * s,
                       x - W / 2 + 12 * s + i * 50 * s, y - H,
                       fill="#b0b6bb", tags=tag)


def draw_lamp(cv, x, y, s=1.0, ghost=False, tag="p", on=True):
    W, H = 44 * s, 34 * s
    if ghost:
        cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, outline=C_GHOST,
                            dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, fill="#f4f4f2",
                        outline="#bdbdb8", width=2, tags=tag)
    cv.create_rectangle(x - W * 0.32, y - H * 0.72, x + W * 0.32, y - H * 0.42,
                        fill=("#f5e64a" if on else "#cfcf9a"),
                        outline="#c9bb3a", tags=tag)
    cv.create_oval(x - 4 * s, y - H * 0.28, x + 4 * s, y - H * 0.10,
                   fill="#8c8c88", outline="", tags=tag)


def draw_camera(cv, x, y, s=1.0, ghost=False, tag="p"):
    W, H = 62 * s, 34 * s
    if ghost:
        cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, outline=C_GHOST,
                            dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, fill="#2b2b2e",
                        outline="#141416", width=2, tags=tag)
    cv.create_oval(x - 11 * s, y - H * 0.75, x + 11 * s, y - H * 0.15,
                   fill="#4a4a52", outline="#8f8f96", tags=tag)
    cv.create_rectangle(x + W / 2 - 16 * s, y - H - 4 * s, x + W / 2 - 6 * s,
                        y - H, fill="#8f2222", outline="", tags=tag)


def draw_wingnut(cv, x, y, s=1.0, ghost=False, tag="p"):
    if ghost:
        cv.create_rectangle(x - 22 * s, y - 14 * s, x + 22 * s, y + 6 * s,
                            outline=C_GHOST, dash=(4, 3), width=2, tags=tag)
        return
    cv.create_oval(x - 20 * s, y - 4 * s, x + 20 * s, y + 5 * s,
                   fill=C_METAL_L, outline=C_METAL_D, tags=tag)   # 와셔
    cv.create_rectangle(x - 7 * s, y - 13 * s, x + 7 * s, y - 2 * s,
                        fill=C_METAL, outline=C_METAL_D, tags=tag)
    for sg in (-1, 1):
        _poly(cv, [x + sg * 6 * s, y - 12 * s, x + sg * 20 * s, y - 16 * s,
                   x + sg * 20 * s, y - 6 * s, x + sg * 6 * s, y - 4 * s],
              fill=C_METAL, outline=C_METAL_D, tags=tag)


def draw_gridstrip(cv, x, y, s=1.0, ghost=False, tag="p"):
    W, H = 150 * s, 26 * s
    if ghost:
        cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, outline=C_GHOST,
                            dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, fill="#f2f7fa",
                        outline="#9fb0bb", tags=tag)
    n = 15
    for i in range(n + 1):
        xx = x - W / 2 + i * W / n
        cv.create_line(xx, y - H, xx, y, fill="#7f97a5", tags=tag)
    for i in range(3):
        yy = y - H + i * H / 2
        cv.create_line(x - W / 2, yy, x + W / 2, yy, fill="#7f97a5", tags=tag)


def draw_woodbase(cv, x, y, s=1.0, ghost=False, tag="p"):
    W, H = 250 * s, 16 * s
    if ghost:
        cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, outline=C_GHOST,
                            dash=(4, 3), width=2, tags=tag)
        return
    cv.create_rectangle(x - W / 2, y - H, x + W / 2, y, fill=C_WOOD,
                        outline=C_WOOD_D, width=2, tags=tag)
    for i in range(5):
        cv.create_line(x - W / 2 + 12 + i * 48, y - H + 2,
                       x - W / 2 + 20 + i * 48, y - 2, fill=C_WOOD_D, tags=tag)


ICON = {
    "stand": draw_stand, "tube": draw_tube, "wedge": draw_wedge,
    "bottle": draw_bottle, "dish": draw_dish, "lamp": draw_lamp,
    "camera": draw_camera, "wingnut": draw_wingnut, "grid": draw_gridstrip,
    "base": draw_woodbase,
}


# =========================================================================
#  4. 공용 위젯 : 실물 자 (드래그해서 눈금을 직접 읽는다)
# =========================================================================
class Ruler:
    """투명 30 cm 자의 일부. 눈금은 그림으로만 존재하고 수치는 표시하지 않는다."""

    def __init__(self, canvas, k, span_mm=130.0, x=60, y=60, vertical=True):
        self.cv = canvas
        self.k = k                       # px per mm
        self.span = span_mm
        self.x, self.y = x, y
        self.vertical = vertical
        self.visible = False
        self.drag = None

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
        n = int(self.span)
        for i in range(n + 1):
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
        cv.create_text((x0 + x1) / 2 if not self.vertical else x0 + 17,
                       y1 - 8 if not self.vertical else y1 - 6,
                       text="cm", font=("TkDefaultFont", 7), fill="#0d2a3a",
                       tags=tag)


def grid_overlay(cv, x0, y0, x1, y1, k, tag="grid", phase=(0.0, 0.0)):
    """투명 그리드 스트립 : 1 mm 격자, 10 mm 마다 굵게."""
    cv.create_rectangle(x0, y0, x1, y1, fill="#f0f7fb", outline="#8fb0c2",
                        stipple="gray25", tags=tag)
    i = 0
    xx = x0 + phase[0] * k
    while xx <= x1:
        w = 2 if i % 10 == 0 else 1
        col = "#41708a" if i % 10 == 0 else "#9ab8c8"
        cv.create_line(xx, y0, xx, y1, fill=col, width=w, tags=tag)
        xx += k
        i += 1
    i = 0
    yy = y0 + phase[1] * k
    while yy <= y1:
        w = 2 if i % 10 == 0 else 1
        col = "#41708a" if i % 10 == 0 else "#9ab8c8"
        cv.create_line(x0, yy, x1, yy, fill=col, width=w, tags=tag)
        yy += k
        i += 1


def hex_positions(n, lam):
    """최근접 간격이 lam 인 육방 격자에서 중심에 가까운 순으로 n 개."""
    pts = []
    for i in range(-4, 5):
        for j in range(-4, 5):
            x = lam * (i + 0.5 * j)
            y = lam * (math.sqrt(3) / 2.0) * j
            pts.append((math.hypot(x, y), x, y))
    pts.sort()
    return [(x, y) for _, x, y in pts[:n]]


# =========================================================================
#  5. 조립 탭 : 슬롯 정의
# =========================================================================
#   (slot key, 부품 id, 화면 x, y, 선행 슬롯들)
SETUP_AB = [
    ("stand", 3, 690, 300, []),
    ("tube", 4, 690, 351, ["stand"]),
    ("rodA", 9, 690, 334, ["tube"]),
    ("magA", 8, 690, 366, ["rodA"]),
    ("wedge", 14, 700, 430, []),
    ("bottle", 1, 676, 424, ["wedge"]),
]
SETUP_CD = [
    ("stand", 3, 690, 300, []),
    ("tube", 4, 690, 430, ["stand"]),
    ("rodC", 9, 690, 386, ["tube"]),
    ("magC", 7, 690, 332, ["rodC"]),
    ("dish", 2, 690, 300, ["stand"]),
    ("pole", 9, 866, 300, ["stand"]),
    ("wnut", 10, 866, 300, ["pole"]),
    ("lamp", 11, 782, 208, ["pole"]),
    ("grid", 16, 690, 246, ["dish"]),
]
SLOT_LABEL_KO = {
    "stand": "차광 후드 겸 받침대", "tube": "알루미늄 관 (옆 구멍에 끼움)",
    "rodA": "나사봉 — 평평한 면이 아래로", "magA": "N42 큰 자석",
    "wedge": "초록 쐐기", "bottle": "유리병 (쐐기 두꺼운 쪽에 옆으로)",
    "rodC": "나사봉 — 위를 향하게", "magC": "N52 작은 자석",
    "dish": "유리접시 (가운데 구멍 위)", "pole": "500 mm 나사봉 (램프 기둥)",
    "wnut": "와셔 + 나비너트", "lamp": "램프 (기둥에 끼움)",
    "grid": "투명 그리드 스트립 (뚜껑 위)",
}
SLOT_LABEL_EN = {
    "stand": "light shroud and stand", "tube": "aluminium tube (side hole)",
    "rodA": "threaded rod - flat face down", "magA": "N42 large magnet",
    "wedge": "green wedge", "bottle": "glass bottle (sideways on the wedge)",
    "rodC": "threaded rod - pointing up", "magC": "N52 small magnet",
    "dish": "glass dish (over the centre hole)", "pole": "500 mm threaded rod",
    "wnut": "washer + wing nut", "lamp": "lamp (threaded on the pole)",
    "grid": "transparent grid strip (on the lid)",
}
SLOT_LABEL = SLOT_LABEL_KO if LANG == "ko" else SLOT_LABEL_EN


# =========================================================================
#  6. 메인 애플리케이션
# =========================================================================
BENCH_BG = "#f5f2ea"
PANEL_BG = "#eceff1"

ZORDER = ["stand", "tube", "dish", "pole", "wnut", "rodA", "rodC",
          "magA", "magC", "wedge", "bottle", "lamp", "grid"]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(S["title"])
        self.geometry("1290x860")
        self.minsize(1120, 700)
        self.ap = Apparatus()

        # ---- 실험 상태 ------------------------------------------------
        self.setup = tk.StringVar(value="AB")
        self.placed = {"AB": set(), "CD": set()}
        self.drag_item = None
        self.drag_xy = (0, 0)

        # 병 실험
        self.magA_key = tk.StringVar(value="N42")
        self.mag_y = 150.0          # 자석 아랫면 높이 [mm] (책상 기준)
        self.blob_up = False
        self.blob_anim = 0.0        # 0 = 바닥, 1 = 위
        self.contact_t = 0.0

        # 접시 실험
        self.magC_key = tk.StringVar(value="N52")
        self.drop = 18.0            # 자석 윗면이 받침대 윗면보다 아래인 깊이 [mm]
        self.turns = 0.0            # 학생이 센 회전수
        self.nspike = 0
        self.lamp_on = tk.BooleanVar(value=True)
        self.dish_view = tk.StringVar(value="cam")

        self._build()
        self.after(60, self._tick)

    # =====================================================================
    def _build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.nb = nb
        self.f_asm = ttk.Frame(nb)
        self.f_bot = ttk.Frame(nb)
        self.f_dis = ttk.Frame(nb)
        self.f_inf = ttk.Frame(nb)
        nb.add(self.f_asm, text=S["t_asm"])
        nb.add(self.f_bot, text=S["t_bottle"])
        nb.add(self.f_dis, text=S["t_dish"])
        nb.add(self.f_inf, text=S["t_info"])
        self._build_asm()
        self._build_bottle()
        self._build_dish()
        self._build_info()

    # ==================================================== 1) 조립 탭 =====
    def _build_asm(self):
        f = self.f_asm
        top = ttk.Frame(f)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text=S["setup"] + " :").pack(side="left")
        for v, t in (("AB", S["set_ab"]), ("CD", S["set_cd"])):
            ttk.Radiobutton(top, text=t, value=v, variable=self.setup,
                            command=self.draw_asm).pack(side="left", padx=6)
        ttk.Button(top, text=S["auto"], command=self._auto).pack(side="left",
                                                                 padx=14)
        ttk.Button(top, text=S["reset"], command=self._reset_asm).pack(
            side="left")
        self.lb_asm = ttk.Label(top, text="", foreground="#0b6")
        self.lb_asm.pack(side="left", padx=16)

        self.cv_asm = tk.Canvas(f, width=1100, height=640, bg=BENCH_BG,
                                highlightthickness=0)
        self.cv_asm.pack(fill="both", expand=True, padx=8, pady=4)
        self.cv_asm.bind("<Button-1>", self._asm_press)
        self.cv_asm.bind("<B1-Motion>", self._asm_move)
        self.cv_asm.bind("<ButtonRelease-1>", self._asm_release)
        self.draw_asm()

    def _slots(self):
        return SETUP_AB if self.setup.get() == "AB" else SETUP_CD

    def _tray_items(self):
        seen, out = set(), []
        for key, pid, *_ in self._slots():
            if pid not in seen:
                seen.add(pid)
                out.append(pid)
        return out

    def _tray_box(self, i):
        return (14, 74 + i * 68, 246, 74 + i * 68 + 60)

    def draw_asm(self):
        cv = self.cv_asm
        cv.delete("all")
        st = self.setup.get()
        placed = self.placed[st]
        # ---- 부품 상자 ------------------------------------------------
        cv.create_rectangle(6, 6, 252, 634, fill="#e4e7ea", outline="#b8bfc5")
        cv.create_text(129, 34, text=S["tray"], font=("TkDefaultFont", 10, "bold"),
                       fill="#2c3b45", width=230)
        need_ids = {}
        for key, pid, x, y, need in self._slots():
            if key not in placed:
                need_ids.setdefault(pid, 0)
                need_ids[pid] += 1
        for i, pid in enumerate(self._tray_items()):
            x0, y0, x1, y1 = self._tray_box(i)
            done = pid not in need_ids
            cv.create_rectangle(x0, y0, x1, y1,
                                fill=("#d3ded3" if done else "#f7f8f9"),
                                outline="#a9b2b9", tags=("tray", f"tray{i}"))
            self._icon(cv, pid, x0 + 34, y0 + 32)
            cv.create_text(x0 + 66, y0 + 30, anchor="w", width=160,
                           text=("✔ " if done else "") + PARTS[pid],
                           font=("TkDefaultFont", 8),
                           fill=("#4d7a52" if done else "#22303a"))
        # ---- 실험대 --------------------------------------------------
        cv.create_rectangle(258, 6, 1094, 634, fill="#fbfaf6", outline="#c9cdd1")
        cv.create_line(280, 430, 1080, 430, fill="#c0b9a8", width=3)
        # 유령(빈 슬롯)
        for key, pid, x, y, need in self._slots():
            if key in placed:
                continue
            ready = all(n in placed for n in need)
            self._draw_slot(cv, key, x, y, ghost=True)
            cv.create_text(x, y + 26, text=SLOT_LABEL[key],
                           font=("TkDefaultFont", 8),
                           fill=("#7d8890" if ready else "#c0c6cb"))
        # 놓인 부품
        for key in ZORDER:
            for k2, pid, x, y, need in self._slots():
                if k2 == key and key in placed:
                    self._draw_slot(cv, key, x, y, ghost=False)
        if len(placed) == len(self._slots()):
            self.lb_asm.config(text=S["done"], foreground="#0a7a3d")
        else:
            self.lb_asm.config(text="")

    def _icon(self, cv, pid, x, y):
        s = 0.20
        if pid == 3:
            draw_stand(cv, x, y - 4, s)
        elif pid == 4:
            draw_tube(cv, x, y, s * 1.3)
        elif pid == 9:
            draw_rod(cv, x, y - 22, y + 22, 1.0, pitch_px=4)
        elif pid == 8:
            draw_magnet(cv, x, y + 8, 20, 5, 1.6)
        elif pid == 7:
            draw_magnet(cv, x, y + 8, 14.2, 3.2, 1.6)
        elif pid == 14:
            draw_wedge(cv, x, y + 12, 0.42)
        elif pid == 1:
            draw_bottle(cv, x, y + 14, 0.30)
        elif pid == 2:
            draw_dish(cv, x, y + 14, 0.28)
        elif pid == 11:
            draw_lamp(cv, x, y + 14, 0.55)
        elif pid == 10:
            draw_wingnut(cv, x, y + 4, 0.62)
        elif pid == 16:
            draw_gridstrip(cv, x, y + 10, 0.30)
        else:
            cv.create_rectangle(x - 14, y - 10, x + 14, y + 10,
                                fill="#cfd6db", outline="#9aa3aa")

    def _draw_slot(self, cv, key, x, y, ghost):
        if key == "stand":
            draw_stand(cv, x, y, 1.0, ghost)
        elif key == "tube":
            draw_tube(cv, x, y, 1.0, ghost)
        elif key == "rodA":
            draw_rod(cv, x, y - 48, y + 32, 1.0, ghost, pitch_px=6)
        elif key == "rodC":
            draw_rod(cv, x, y - 56, y + 46, 1.0, ghost, pitch_px=6)
        elif key == "magA":
            draw_magnet(cv, x, y, 20, 5, 3.0, ghost=ghost)
        elif key == "magC":
            draw_magnet(cv, x, y, 14.2, 3.2, 3.0, ghost=ghost)
        elif key == "wedge":
            draw_wedge(cv, x, y, 1.0, ghost)
        elif key == "bottle":
            draw_bottle(cv, x, y, 0.75, ghost)
        elif key == "dish":
            draw_dish(cv, x, y, 0.92, ghost)
        elif key == "pole":
            draw_rod(cv, x, y - 160, y, 1.0, ghost, pitch_px=6)
        elif key == "wnut":
            draw_wingnut(cv, x, y, 1.0, ghost)
        elif key == "lamp":
            col = "#c8ced2" if ghost else "#8f979c"
            cv.create_line(x + 34, y, 866, y, width=5, fill=col)
            cv.create_line(866, y - 10, 866, y + 10, width=7, fill=col)
            draw_lamp(cv, x, y, 1.0, ghost, on=True)
        elif key == "grid":
            draw_gridstrip(cv, x, y, 0.8, ghost)

    def _asm_press(self, e):
        if e.x > 252:
            return
        for i, pid in enumerate(self._tray_items()):
            x0, y0, x1, y1 = self._tray_box(i)
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                self.drag_item = pid
                self.drag_xy = (e.x, e.y)
                return

    def _asm_move(self, e):
        if self.drag_item is None:
            return
        self.cv_asm.delete("carry")
        self.cv_asm.create_oval(e.x - 16, e.y - 16, e.x + 16, e.y + 16,
                                outline="#3b7ea8", width=2, dash=(3, 2),
                                tags="carry")
        self._icon(self.cv_asm, self.drag_item, e.x, e.y)
        self.cv_asm.addtag_withtag("carry", "current")

    def _asm_release(self, e):
        pid = self.drag_item
        self.drag_item = None
        self.cv_asm.delete("carry")
        if pid is None:
            self.draw_asm()
            return
        st = self.setup.get()
        placed = self.placed[st]
        best, bd = None, 1e9
        for key, p, x, y, need in self._slots():
            if p != pid or key in placed:
                continue
            d = math.hypot(e.x - x, e.y - y)
            if d < bd:
                best, bd = (key, need), d
        if best and bd < 110:
            key, need = best
            if all(n in placed for n in need):
                placed.add(key)
            else:
                self.lb_asm.config(text=S["notyet"], foreground="#b3541e")
                self.draw_asm()
                return
        self.draw_asm()

    def _auto(self):
        st = self.setup.get()
        self.placed[st] = set(k for k, *_ in self._slots())
        self.draw_asm()

    def _reset_asm(self):
        self.placed[self.setup.get()] = set()
        self.draw_asm()

    def ready(self, st):
        return len(self.placed[st]) == len(SETUP_AB if st == "AB" else SETUP_CD)

    # ================================================ 2) 병 실험 탭 =====
    KB = 3.0          # px per mm
    PY0 = 610         # 책상면
    PX0 = 40

    def bx(self, x_mm):
        return self.PX0 + self.KB * x_mm

    def by(self, y_mm):
        return self.PY0 - self.KB * y_mm

    def _build_bottle(self):
        f = self.f_bot
        left = ttk.Frame(f)
        left.pack(side="left", fill="both", expand=True)
        self.cv_bot = tk.Canvas(left, width=700, height=640, bg="#f7f5ef",
                                highlightthickness=0)
        self.cv_bot.pack(side="top", padx=6, pady=6)
        self.cv_mag = tk.Canvas(left, width=700, height=150, bg="#20262b",
                                highlightthickness=0)
        self.cv_mag.pack(side="top", padx=6)

        p = ttk.Frame(f, padding=8)
        p.pack(side="left", fill="y")
        ttk.Label(p, text=S["hint_ab"], foreground="#3a4a55",
                  font=("TkDefaultFont", 8)).pack(anchor="w", pady=(0, 8))

        g = ttk.LabelFrame(p, text=S["magnet"], padding=6)
        g.pack(fill="x", pady=4)
        for v in ("N42", "N52"):
            ttk.Radiobutton(g, text=MAGNETS[v][3], value=v,
                            variable=self.magA_key,
                            command=self.draw_bottle_view).pack(anchor="w")

        g = ttk.LabelFrame(p, text=S["carrier"], padding=6)
        g.pack(fill="x", pady=4)
        for txt, d in ((S["up"] + "  " + S["coarse"], +4.0),
                       (S["up"] + "  " + S["fine"], +0.4),
                       (S["dn"] + "  " + S["fine"], -0.4),
                       (S["dn"] + "  " + S["coarse"], -4.0)):
            ttk.Button(g, text=txt, width=22,
                       command=lambda d=d: self._move_mag(d)).pack(pady=1)
        ttk.Label(g, text=S["wheel"], font=("TkDefaultFont", 8),
                  foreground="#667").pack(pady=(4, 0))

        g = ttk.LabelFrame(p, text=S["ruler"] + " / " + S["grid"], padding=6)
        g.pack(fill="x", pady=4)
        self.v_rul_b = tk.BooleanVar(value=True)
        self.v_rulv_b = tk.BooleanVar(value=True)
        ttk.Checkbutton(g, text=S["show"], variable=self.v_rul_b,
                        command=self.draw_bottle_view).pack(anchor="w")
        ttk.Checkbutton(g, text=S["vert"], variable=self.v_rulv_b,
                        command=self._rulv_b).pack(anchor="w")
        ttk.Label(g, text=S["zoom"] + " : " + ("아래 창" if LANG == "ko"
                                               else "panel below"),
                  font=("TkDefaultFont", 8)).pack(anchor="w", pady=(4, 0))

        self.lb_bot = ttk.Label(p, text="", font=("TkDefaultFont", 9, "bold"),
                                foreground="#1d4f7a", wraplength=210)
        self.lb_bot.pack(anchor="w", pady=10)
        self.lb_warn = ttk.Label(p, text="", foreground="#a3421c",
                                 wraplength=210, font=("TkDefaultFont", 8))
        self.lb_warn.pack(anchor="w")
        ttk.Button(p, text=S["release"], command=self._release_fluid).pack(
            anchor="w", pady=6)

        self.rul_b = Ruler(self.cv_bot, self.KB, 120, 500, 120, True)
        self.rul_b.visible = True
        cv = self.cv_bot
        cv.bind("<Button-1>", self._bot_press)
        cv.bind("<B1-Motion>", self._bot_drag)
        cv.bind("<ButtonRelease-1>", lambda e: setattr(self, "_rdrag", None))
        cv.bind("<MouseWheel>", lambda e: self._move_mag(
            0.4 if e.delta > 0 else -0.4))
        cv.bind("<Button-4>", lambda e: self._move_mag(0.4))
        cv.bind("<Button-5>", lambda e: self._move_mag(-0.4))
        self._rdrag = None
        self.draw_bottle_view()

    def _rulv_b(self):
        self.rul_b.vertical = self.v_rulv_b.get()
        self.draw_bottle_view()

    def _bot_press(self, e):
        self.rul_b.visible = self.v_rul_b.get()
        if self.rul_b.hit(e.x, e.y):
            self._rdrag = (e.x - self.rul_b.x, e.y - self.rul_b.y)

    def _bot_drag(self, e):
        if self._rdrag:
            self.rul_b.x = e.x - self._rdrag[0]
            self.rul_b.y = e.y - self._rdrag[1]
            self.draw_bottle_view()

    def _move_mag(self, d):
        self.mag_y = min(168.0, max(59.0, self.mag_y + d))
        self.draw_bottle_view()

    def _release_fluid(self):
        self.contact_t = 0.0
        self.draw_bottle_view()

    # -------------------------------------------------- 병 실험 물리
    BLOB_TOP_LO = 37.0     # 바닥에 있을 때 유체 윗면 [mm]
    BLOB_TOP_HI = 55.0     # 떠올랐을 때 유체 윗면 [mm]

    def blob_top(self):
        return self.BLOB_TOP_LO + (self.BLOB_TOP_HI - self.BLOB_TOP_LO) \
            * self.blob_anim

    def _bottle_update(self):
        key = self.magA_key.get()
        gap_lo = self.mag_y - self.BLOB_TOP_LO
        gap_hi = self.mag_y - self.BLOB_TOP_HI
        if not self.blob_up:
            if self.ap.lift_force_ratio(gap_lo, key) > 1.0:
                self.blob_up = True
        else:
            if self.ap.lift_force_ratio(gap_hi, key) < 1.0:
                self.blob_up = False
        tgt = 1.0 if self.blob_up else 0.0
        self.blob_anim += (tgt - self.blob_anim) * 0.34
        if abs(self.blob_anim - tgt) < 0.01:
            self.blob_anim = tgt
        gap = self.mag_y - self.blob_top()
        b = Bz(max(gap, 0.2) * 1e-3, mag_si(key))
        self.cur_gap = gap
        self.cur_B = b
        thr = self.ap.B_thr_bottle
        self.spike_amp = 0.0 if b <= thr else min(1.0, (b / thr - 1.0) * 2.2)
        if gap < 12.0:
            self.contact_t += 0.06
        else:
            self.contact_t = max(0.0, self.contact_t - 0.02)

    # -------------------------------------------------- 병 실험 그리기
    def draw_bottle_view(self):
        cv = self.cv_bot
        cv.delete("all")
        if not self.ready("AB"):
            cv.create_text(350, 300, text=S["no_bottle"] + "\n" + S["goto"],
                           font=("TkDefaultFont", 12), fill="#8a6a3a")
            self.cv_mag.delete("all")
            return
        self._bottle_update()
        bx, by, k = self.bx, self.by, self.KB
        # --- 후드/받침대 ------------------------------------------------
        cv.create_rectangle(bx(-10), by(203), bx(230), by(196),
                            fill=C_PLASTIC, outline=C_PLASTIC_D)
        for xm in (2, 214):
            cv.create_rectangle(bx(xm), by(196), bx(xm + 14), by(0),
                                fill=C_PLASTIC, outline=C_PLASTIC_D)
        cv.create_line(bx(-10), by(0), bx(232), by(0), fill="#b9b0a0", width=3)
        # --- 알루미늄 관 -----------------------------------------------
        cv.create_rectangle(bx(16), by(180), bx(214), by(163),
                            fill=C_METAL, outline=C_METAL_D)
        cv.create_line(bx(16), by(176), bx(214), by(176), fill=C_METAL_L,
                       width=2)
        # --- 나사봉 + 자석 ---------------------------------------------
        key = self.magA_key.get()
        dia, th = MAGNETS[key][0] * 2, MAGNETS[key][1]
        draw_rod(cv, bx(110), by(165), by(self.mag_y + th), 1.0,
                 pitch_px=max(3.0, k * self.ap.pitch))
        draw_magnet(cv, bx(110), by(self.mag_y), dia, th, k)
        cv.create_text(bx(110) - 46, by(self.mag_y) - 6, anchor="e",
                       text=MAGNETS[key][3], font=("TkDefaultFont", 8),
                       fill="#55606a")
        # --- 쐐기 + 병 --------------------------------------------------
        cv.create_polygon(bx(60), by(0), bx(180), by(0), bx(180), by(5),
                          bx(60), by(26), fill=C_GREEN, outline=C_GREEN_D,
                          width=2)
        cv.create_oval(bx(86), by(28), bx(104), by(21), fill="#c9c3ae",
                       outline="#a9a48f")
        self._draw_bottle_body(cv)
        # --- 자 ---------------------------------------------------------
        self.rul_b.visible = self.v_rul_b.get()
        self.rul_b.draw()
        # --- 상태 --------------------------------------------------------
        txt = S["blob_up"] if self.blob_up else S["blob_dn"]
        if self.spike_amp > 0.02:
            txt += "  /  " + S["spikes"]
        self.lb_bot.config(text=txt)
        self.lb_warn.config(text=S["stuck"] if self.contact_t > 10 else "")
        self._draw_magnifier()

    def _draw_bottle_body(self, cv):
        bx, by = self.bx, self.by
        x0, x1 = bx(79), bx(141)
        cv.create_rectangle(x0, by(57), x1 - 22, by(25), fill=C_GLASS,
                            outline="#93a9b7", width=2)
        cv.create_oval(x0 - 10, by(57), x0 + 10, by(25), fill="#eaf2f7",
                       outline="#93a9b7", width=2)
        cv.create_rectangle(x1 - 22, by(50), x1 - 8, by(32), fill=C_GLASS,
                            outline="#93a9b7", width=2)
        cv.create_rectangle(x1 - 8, by(52), x1 + 8, by(30), fill="#f3f3f1",
                            outline="#b7b7b2", width=2)
        cv.create_text((x0 + x1) / 2, by(50), text="20 mL",
                       font=("TkDefaultFont", 7), fill="#7f95a3")
        self._draw_blob(cv, self.bx, self.by, self.KB, spikes=True)

    def _draw_blob(self, cv, fx, fy, k, spikes=False, tag="blob"):
        """페로플루이드 덩어리. 윗면에 정상장 불안정 스파이크."""
        top = self.blob_top()
        cy = top - 5.0
        rx, ry = 13.0, 5.2
        pts = []
        N = 64
        lam = self.ap.lam_b * 1e3
        amp = self.spike_amp * min(2.6, 0.35 * lam)
        for i in range(N + 1):
            th = math.pi * 2 * i / N
            x = math.cos(th) * rx
            y = math.sin(th) * ry
            if spikes and amp > 0.02 and y > 0:
                w = math.cos(math.pi * 2 * x / lam + 0.7)
                y += amp * max(0.0, w) ** 1.6 * (1 - (x / rx) ** 2)
            pts += [fx(110 + x), fy(cy + y)]
        cv.create_polygon(pts, fill=C_FF, outline="#2c2c34", smooth=True,
                          tags=tag)
        cv.create_oval(fx(110 - 6), fy(cy + ry * 0.2), fx(110 - 1),
                       fy(cy - ry * 0.5), fill=C_FF_HL, outline="", tags=tag)
        # 작은 분리 방울 (문제지 A.1 각주)
        cv.create_oval(fx(126), fy(48), fx(131), fy(45), fill=C_FF,
                       outline="", tags=tag)

    def _draw_magnifier(self):
        """확대경 : 그리드 스트립을 대고 스파이크 간격을 잰다."""
        cv = self.cv_mag
        cv.delete("all")
        k2 = 10.0
        # 확대할 영역(왼쪽 위) [mm] — 유체 윗면을 따라간다
        x_lo = 110.0 - 35.0
        y_hi = self.blob_top() + 3.5

        def fx(x):
            return (x - x_lo) * k2

        def fy(y):
            return (y_hi - y) * k2
        grid_overlay(cv, 0, 0, 700, 150, k2, phase=(0.3, 0.4))
        self._draw_blob(cv, fx, fy, k2, spikes=True, tag="m")
        cv.create_text(660, 12, text=S["grid"] + " (1 mm)", fill="#cfe0ea",
                       font=("TkDefaultFont", 8))

    # ============================================== 3) 접시 실험 탭 =====
    KD = 4.0          # 옆면도 px/mm
    PYS = 330         # 받침대 윗면
    PXS = 40
    KC = 6.0          # 위에서 본 화면 px/mm

    def dx(self, x_mm):
        return self.PXS + self.KD * x_mm

    def dy(self, y_mm):
        return self.PYS - self.KD * y_mm

    def _build_dish(self):
        f = self.f_dis
        left = ttk.Frame(f)
        left.pack(side="left", fill="both", expand=True)
        self.cv_side = tk.Canvas(left, width=600, height=520, bg="#f7f5ef",
                                 highlightthickness=0)
        self.cv_side.pack(side="top", padx=6, pady=6)

        mid = ttk.Frame(f)
        mid.pack(side="left", fill="both")
        ttk.Label(mid, text=S["v_cam"], font=("TkDefaultFont", 9, "bold")
                  ).pack(anchor="w", padx=6)
        self.cv_cam = tk.Canvas(mid, width=560, height=470, bg="#101215",
                                highlightthickness=0)
        self.cv_cam.pack(side="top", padx=6, pady=(0, 6))

        p = ttk.Frame(f, padding=8)
        p.pack(side="left", fill="y")
        ttk.Label(p, text=S["hint_cd"], foreground="#3a4a55",
                  font=("TkDefaultFont", 8)).pack(anchor="w", pady=(0, 8))

        g = ttk.LabelFrame(p, text=S["view"], padding=6)
        g.pack(fill="x", pady=4)
        for v, t in (("side", S["v_side"]), ("thread", S["v_thread"])):
            ttk.Radiobutton(g, text=t, value=v, variable=self.dish_view,
                            command=self.draw_dish_view).pack(anchor="w")

        g = ttk.LabelFrame(p, text=S["magnet"], padding=6)
        g.pack(fill="x", pady=4)
        for v in ("N52", "STACK"):
            ttk.Radiobutton(g, text=MAGNETS[v][3], value=v,
                            variable=self.magC_key,
                            command=self._mag_changed).pack(anchor="w")

        g = ttk.LabelFrame(p, text=S["carrier"], padding=6)
        g.pack(fill="x", pady=4)
        row = ttk.Frame(g)
        row.pack()
        for txt, d in (("▲ 5", 5.0), ("▲ 1", 1.0), ("▲ ¼", 0.25)):
            ttk.Button(row, text=txt, width=5,
                       command=lambda d=d: self._turn(-d)).pack(side="left")
        row = ttk.Frame(g)
        row.pack()
        for txt, d in (("▼ 5", 5.0), ("▼ 1", 1.0), ("▼ ¼", 0.25)):
            ttk.Button(row, text=txt, width=5,
                       command=lambda d=d: self._turn(+d)).pack(side="left")
        self.lb_turn = ttk.Label(g, text="", font=("TkDefaultFont", 11, "bold"),
                                 foreground="#1d4f7a")
        self.lb_turn.pack(pady=4)
        ttk.Button(g, text=S["zero"], command=self._zero_turns).pack()
        self.lb_flush = ttk.Label(g, text="", foreground="#0a7a3d",
                                  wraplength=200, font=("TkDefaultFont", 8))
        self.lb_flush.pack(pady=(4, 0))

        g = ttk.LabelFrame(p, text=S["lamp"], padding=6)
        g.pack(fill="x", pady=4)
        ttk.Checkbutton(g, text=S["on"], variable=self.lamp_on,
                        command=self.draw_dish_view).pack(anchor="w")

        g = ttk.LabelFrame(p, text=S["ruler"], padding=6)
        g.pack(fill="x", pady=4)
        self.v_rul_d = tk.BooleanVar(value=True)
        self.v_rulv_d = tk.BooleanVar(value=True)
        ttk.Checkbutton(g, text=S["show"], variable=self.v_rul_d,
                        command=self.draw_dish_view).pack(anchor="w")
        ttk.Checkbutton(g, text=S["vert"], variable=self.v_rulv_d,
                        command=self._rulv_d).pack(anchor="w")

        self.lb_dish = ttk.Label(p, text="", font=("TkDefaultFont", 9, "bold"),
                                 foreground="#1d4f7a", wraplength=210)
        self.lb_dish.pack(anchor="w", pady=10)

        self.rul_d = Ruler(self.cv_side, self.KD, 90, 470, 60, True)
        cv = self.cv_side
        cv.bind("<Button-1>", self._dish_press)
        cv.bind("<B1-Motion>", self._dish_drag)
        cv.bind("<ButtonRelease-1>", lambda e: setattr(self, "_rdrag2", None))
        for c in (self.cv_side, self.cv_cam):
            c.bind("<MouseWheel>", lambda e: self._turn(
                -0.25 if e.delta > 0 else 0.25))
            c.bind("<Button-4>", lambda e: self._turn(-0.25))
            c.bind("<Button-5>", lambda e: self._turn(0.25))
        self._rdrag2 = None
        self._spike_jit = [(self.ap.rng.uniform(-.35, .35),
                            self.ap.rng.uniform(-.35, .35)) for _ in range(24)]
        self.draw_dish_view()

    def _rulv_d(self):
        self.rul_d.vertical = self.v_rulv_d.get()
        self.draw_dish_view()

    def _dish_press(self, e):
        self.rul_d.visible = self.v_rul_d.get()
        if self.rul_d.hit(e.x, e.y):
            self._rdrag2 = (e.x - self.rul_d.x, e.y - self.rul_d.y)

    def _dish_drag(self, e):
        if self._rdrag2:
            self.rul_d.x = e.x - self._rdrag2[0]
            self.rul_d.y = e.y - self._rdrag2[1]
            self.draw_dish_view()

    def _mag_changed(self):
        self.nspike = 0
        self.draw_dish_view()

    def _turn(self, dturn):
        """+ 는 자석을 내리는 방향(유체에서 멀어짐)."""
        new = self.drop + dturn * self.ap.pitch
        new = min(34.0, max(0.0, new))
        real = (new - self.drop) / self.ap.pitch
        self.drop = new
        self.turns += real
        self.draw_dish_view()

    def _zero_turns(self):
        self.turns = 0.0
        self.draw_dish_view()

    # ------------------------------------------------ 접시 실험 물리
    def _dish_update(self):
        key = self.magC_key.get()
        z = self.ap.offset + self.drop           # 자석면 - 유체면 [mm]
        self.z_dish = z
        b = Bz(z * 1e-3, mag_si(key))
        # 스파이크 개수 (이력현상 포함)
        n = self.nspike
        while n < self.ap.N_MAX and b >= self.ap.spike_thresholds(n + 1)[0]:
            n += 1
        while n > 0 and b < self.ap.spike_thresholds(n)[1]:
            n -= 1
        self.nspike = n
        self.img_len = self.ap.image_len(z, key)

    # ------------------------------------------------ 접시 실험 그리기
    def draw_dish_view(self):
        if not self.ready("CD"):
            self.cv_side.delete("all")
            self.cv_cam.delete("all")
            self.cv_side.create_text(300, 250,
                                     text=S["no_dish"] + "\n" + S["goto"],
                                     font=("TkDefaultFont", 12),
                                     fill="#8a6a3a")
            return
        self._dish_update()
        self.lb_turn.config(text=f"{S['turns']} : {self.turns:+.2f}")
        self.lb_flush.config(text=S["flush"] if self.drop < 0.2 else "")
        if self.dish_view.get() == "thread":
            self._draw_thread()
        else:
            self._draw_side()
        self._draw_cam()
        t = ""
        if self.nspike:
            t = f"{S['spikes']} : {self.nspike}"
        self.lb_dish.config(text=t)

    def _draw_side(self):
        cv = self.cv_side
        cv.delete("all")
        dx, dy, k = self.dx, self.dy, self.KD
        key = self.magC_key.get()
        dia, th = MAGNETS[key][0] * 2, MAGNETS[key][1]
        # 받침대 윗판
        cv.create_rectangle(dx(-6), dy(0), dx(56), dy(-7), fill=C_PLASTIC,
                            outline=C_PLASTIC_D, width=2)
        cv.create_rectangle(dx(74), dy(0), dx(136), dy(-7), fill=C_PLASTIC,
                            outline=C_PLASTIC_D, width=2)
        cv.create_rectangle(dx(-6), dy(-7), dx(2), dy(-46), fill=C_PLASTIC,
                            outline=C_PLASTIC_D)
        cv.create_rectangle(dx(128), dy(-7), dx(136), dy(-46), fill=C_PLASTIC,
                            outline=C_PLASTIC_D)
        cv.create_text(dx(20), dy(-4), text="stand", font=("TkDefaultFont", 7),
                       fill="#8b939a")
        # 자석 캐리어 (나사봉 + 자석)
        draw_rod(cv, dx(65), dy(-self.drop - th), dy(-40), 1.0,
                 pitch_px=k * self.ap.pitch)
        draw_magnet(cv, dx(65), dy(-self.drop - th), dia, th, k,
                    stack=(key == "STACK"))
        # 알루미늄 관
        cv.create_rectangle(dx(4), dy(-40), dx(126), dy(-45), fill=C_METAL,
                            outline=C_METAL_D)
        # 유리접시 (단면)
        ap = self.ap
        b, d = ap.dish_base, ap.depth
        cv.create_rectangle(dx(2), dy(0), dx(128), dy(b), fill="#c9d6de",
                            outline="#8fa4b0", width=2)
        cv.create_rectangle(dx(2), dy(b), dx(128), dy(b + d), fill=C_FF,
                            outline="#8fa4b0")
        cv.create_rectangle(dx(2), dy(b + d), dx(6), dy(30), fill=C_GLASS,
                            outline="#8fa4b0")
        cv.create_rectangle(dx(124), dy(b + d), dx(128), dy(30), fill=C_GLASS,
                            outline="#8fa4b0")
        cv.create_rectangle(dx(-1), dy(30), dx(131), dy(33), fill="#d5dade",
                            outline="#9aa2a8", width=2)
        # 유체 융기(자석 위)
        self._draw_bump_side(cv)
        # 램프
        lh = b + d + ap.lamp_h
        on = self.lamp_on.get()
        cv.create_rectangle(dx(55), dy(lh), dx(75), dy(lh + 4),
                            fill=("#f7ef9a" if on else "#d9d9c8"),
                            outline="#b8ac48")
        cv.create_rectangle(dx(52), dy(lh + 4), dx(78), dy(lh + 12),
                            fill="#f2f2ef", outline="#bcbcb6", width=2)
        cv.create_line(dx(78), dy(lh + 8), dx(120), dy(lh + 8), fill="#9aa2a8",
                       width=3)
        draw_rod(cv, dx(120), dy(lh + 40), dy(0), 1.0, pitch_px=6)
        draw_wingnut(cv, dx(120), dy(0), 0.8)
        if on:
            for i in range(3):
                cv.create_line(dx(65), dy(lh), dx(50 + i * 15), dy(b + d),
                               fill="#e9d76a", dash=(3, 3))
        cv.create_text(dx(65), dy(lh + 18), text="lamp",
                       font=("TkDefaultFont", 7), fill="#8b939a")
        self.rul_d.visible = self.v_rul_d.get()
        self.rul_d.draw()

    def _draw_bump_side(self, cv):
        """자석 위로 솟은 유체 표면 (옆에서). 스파이크가 생기면 뾰족해진다."""
        dx, dy = self.dx, self.dy
        ap = self.ap
        surf = ap.dish_base + ap.depth
        R = ap.R_curv(self.z_dish, self.magC_key.get())
        # 중심 융기 높이 (표시용 : 곡률과 폭에서)
        halfw = min(28.0, max(6.0, self.z_dish * 0.75))
        h0 = min(ap.depth * 1.6, halfw * halfw / (2 * max(R, 1.0)))
        pts = []
        for i in range(61):
            x = 65 - halfw + 2 * halfw * i / 60.0
            u = (x - 65) / halfw
            y = surf + h0 * math.exp(-3.0 * u * u)
            pts += [dx(x), dy(y)]
        if self.nspike:
            lam = ap.lam_a * 1e3
            pts = []
            for i in range(121):
                x = 65 - halfw + 2 * halfw * i / 120.0
                u = (x - 65) / halfw
                env = math.exp(-3.0 * u * u)
                sp = max(0.0, math.cos(2 * math.pi * (x - 65) / lam))
                y = surf + h0 * env + ap.depth * 1.5 * env * sp ** 2
                pts += [dx(x), dy(y)]
        pts = [dx(37), dy(surf)] + pts + [dx(93), dy(surf)]
        cv.create_polygon(pts, fill=C_FF, outline="#2c2c34", smooth=True)

    def _draw_thread(self):
        """C.1 : 나사봉 확대 — 나사산을 직접 세고 자로 길이를 잰다."""
        cv = self.cv_side
        cv.delete("all")
        k = 16.0
        x0, y0 = 26, 250
        span = 34.0
        cv.create_rectangle(x0, y0 - 26, x0 + span * k, y0 + 26,
                            fill=C_METAL, outline=C_METAL_D, width=2)
        p = self.ap.pitch
        n = 0
        xx = 0.0
        while xx <= span:
            cv.create_line(x0 + xx * k, y0 - 26, x0 + (xx + p * 0.55) * k,
                           y0 + 26, fill=C_METAL_D, width=2)
            cv.create_line(x0 + xx * k, y0 + 26, x0 + (xx + p * 0.55) * k,
                           y0 - 26, fill="#cfd4d9")
            xx += p
            n += 1
        cv.create_rectangle(x0, y0 - 26, x0 + span * k, y0 - 20,
                            fill="#d8dce0", outline="")
        # 자 (고정, 실물 눈금)
        ry = y0 + 60
        cv.create_rectangle(x0, ry, x0 + span * k, ry + 46, fill="#e8f4fb",
                            outline="#7fa8c0")
        for i in range(int(span) + 1):
            xx = x0 + i * k
            if i % 10 == 0:
                ln, col = 30, "#0d2a3a"
            elif i % 5 == 0:
                ln, col = 20, "#16455e"
            else:
                ln, col = 12, "#2a6383"
            cv.create_line(xx, ry, xx, ry + ln, fill=col)
            if i % 10 == 0:
                cv.create_text(xx, ry + 38, text=str(i // 10),
                               font=("TkDefaultFont", 8), fill="#0d2a3a")
        cv.create_text(x0 + span * k / 2, ry + 62,
                       text=("자 눈금 : cm    (나사산을 직접 세어 피치를 구하세요)"
                             if LANG == "ko" else
                             "ruler scale: cm  (count the threads yourself)"),
                       font=("TkDefaultFont", 9), fill="#33424c")
        cv.create_text(300, 60, width=540, justify="center",
                       text=("C.1 — 나사봉 확대 사진.\n"
                             "나사산 개수와 그 구간의 길이를 재어 1회전당 z 변화를 구하세요."
                             if LANG == "ko" else
                             "C.1 - close-up of the threaded rod.\n"
                             "Count the threads over a measured length to get "
                             "the change in z per turn."),
                       font=("TkDefaultFont", 10), fill="#33424c")

    def _draw_cam(self):
        cv = self.cv_cam
        cv.delete("all")
        k = self.KC
        cx, cy = 280, 235
        ap = self.ap
        # 접시 안쪽 (페로플루이드 표면)
        cv.create_rectangle(cx - 46 * k, cy - 36 * k, cx + 46 * k,
                            cy + 36 * k, fill="#17181c", outline="#3a4048",
                            width=2)
        # 융기 영역의 어두운 원
        rr = min(30.0, max(6.0, self.z_dish * 0.75)) * k
        cv.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, outline="#2a2d33")
        if self.nspike:
            self._draw_spikes_top(cv, cx, cy, k)
        elif self.lamp_on.get():
            L = self.img_len
            a = L * k / 2.0
            bb = L * 0.26 * k / 2.0
            for i, col in ((2.1, "#4a4632"), (1.5, "#8d8544"),
                           (1.15, "#d8cd63"), (1.0, "#fdf7c8")):
                cv.create_oval(cx - a * i, cy - bb * i, cx + a * i,
                               cy + bb * i, fill=col, outline="")
        # 그리드 스트립 (위에 얹힌 투명 눈금)
        grid_overlay(cv, 20, 300, 540, 452, k, phase=(0.4, 0.2))
        gy = 376
        if self.nspike:
            self._draw_spikes_top(cv, 280, gy, k, flat=True)
        elif self.lamp_on.get():
            L = self.img_len
            a = L * k / 2.0
            bb = L * 0.26 * k / 2.0
            for i, col in ((1.5, "#b8a94e"), (1.15, "#e6da7a"),
                           (1.0, "#fffbe0")):
                cv.create_oval(280 - a * i, gy - bb * i, 280 + a * i,
                               gy + bb * i, fill=col, outline="")
        cv.create_text(280, 288, text=S["grid"] + "  (1 mm)", fill="#9fb6c4",
                       font=("TkDefaultFont", 8))

    def _draw_spikes_top(self, cv, cx, cy, k, flat=False):
        lam = self.ap.lam_a * 1e3
        pos = hex_positions(self.nspike, lam)
        for i, (px, py) in enumerate(pos):
            jx, jy = self._spike_jit[i % len(self._spike_jit)]
            x = cx + (px + jx * 0.25) * k
            y = cy + (py + jy * 0.25) * k
            r = 0.30 * lam * k
            cv.create_oval(x - r, y - r, x + r, y + r, fill="#26262e",
                           outline="#0a0a0c")
            cv.create_oval(x - r * 0.45, y - r * 0.45, x + r * 0.15,
                           y + r * 0.15, fill="#8b8b9a", outline="")
            if not flat:
                cv.create_oval(x - r * 0.18, y - r * 0.18, x + r * 0.18,
                               y + r * 0.18, fill="#e6e6f2", outline="")

    # ================================================ 4) 안내 탭 =========
    def _build_info(self):
        f = self.f_inf
        box = ttk.Frame(f, padding=10)
        box.pack(fill="both", expand=True)
        left = tk.Text(box, width=56, height=34, wrap="word",
                       font=("TkDefaultFont", 9), bg="#fbfaf7",
                       relief="flat")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        lines = [("장비 목록 (문제지 Q1-2)" if LANG == "ko"
                  else "Equipment list (problem sheet Q1-2)"), ""]
        for i in sorted(PARTS):
            lines.append(f"{i:2d}.  {PARTS[i]}")
        left.insert("1.0", "\n".join(lines))
        left.config(state="disabled")

        right = tk.Text(box, width=64, height=34, wrap="word",
                        font=("TkDefaultFont", 9), bg="#fbfaf7", relief="flat")
        right.pack(side="left", fill="both", expand=True)
        right.insert("1.0", SAFETY)
        right.config(state="disabled")

    # ================================================ 애니메이션 ========
    def _tick(self):
        try:
            if self.nb.index(self.nb.select()) == 1 and self.ready("AB"):
                if self.blob_anim not in (0.0, 1.0) or self.contact_t > 0:
                    self.draw_bottle_view()
        except Exception:
            pass
        self.after(80, self._tick)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
