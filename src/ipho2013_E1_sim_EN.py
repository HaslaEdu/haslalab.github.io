#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  44th International Physics Olympiad  (IPhO 2013, Copenhagen, Denmark)
  Experimental Problem E1 :  SPEED OF LIGHT
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The simulator shows ONLY what the real instruments show -- the display of
    the laser distance meter and the tape measure.  Refractive indices, speeds
    and angles that the student has to derive are never computed or shown.
    The apparatus is rebuilt in 2D from the photographs of the problem sheet
    and is assembled by hand in the Assembly tab.
    All hidden true parameters are randomised for every session.

    Run:   python3 ipho2013_E1_sim_KO.py   [--seed=N]
"""

import math
import random
import sys
import tkinter as tk
from tkinter import ttk, messagebox

# --------------------------------------------------------------------------
# language
# --------------------------------------------------------------------------
LANG = "en"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


C_LIGHT = 2.998e8          # 문제지 데이터시트 값
N_ACRYLIC = 1.491


# ==========================================================================
#  물리 엔진
# ==========================================================================
class E1Physics:
    """레이저 거리계(Bosch PLR) 전방 모델.

    디스플레이 표시값        y = ½ c t + k
    광섬유                  ½ c t = ½ n_co x
    기울어진 빔 (공기)       ½ c t = z/cosθ₁
    광학 용기 (깊이 x 물)    ½ c t = (z - t_bot)/cosθ₁ + α x,
                            α = n_w/cosθ₂ - 1/cosθ₁ ,  sinθ₁ = n_w sinθ₂
    """

    LDM_MIN = 0.05          # 시차 때문에 5 cm 미만 측정 불가
    LDM_MAX = 25.0
    BODY_LEN = 0.105        # 기기 길이 (뒷면 기준 <-> 앞면 기준 차이)

    def __init__(self, seed=None):
        self.seed = seed if seed is not None else random.randrange(1, 10 ** 9)
        r = random.Random(self.seed)
        self.rng = r

        # ---- 숨은 참값 (세션마다 무작위) -------------------------------
        self.H = 0.907 + r.uniform(-0.008, 0.010)          # 테이블 높이 [m]
        self.k_rear = 0.1014 + r.uniform(-0.0015, 0.0015)  # 뒷면 기준 오프셋
        self.k_front = self.k_rear - self.BODY_LEN
        self.n_co = 1.542 + r.uniform(-0.010, 0.010)       # 코어 유효(군)굴절률
        self.theta1 = math.radians(19.30 + r.uniform(-0.45, 0.45))
        self.n_w = 1.3317 + r.uniform(-0.0012, 0.0012)     # 635 nm, 실온
        self.z_lens = 0.1988 + r.uniform(-0.004, 0.004)    # 렌즈 높이(테이블 기준)

        # ---- 고정 기하 -------------------------------------------------
        self.v_inner_h = 0.100      # 광학 용기 내부 높이
        self.v_bottom = 0.003       # 바닥판 두께
        self.v_inner_w = 0.060      # 내부 폭

        # ---- 소모품 ----------------------------------------------------
        self.cable_len = 1.000 + r.uniform(-0.004, 0.004)  # 남은 광섬유 [m]
        self.cable_cuts = 0

        # ---- 기기 상태 -------------------------------------------------
        self.power = False
        self.ref_rear = True
        self.cont = False
        self.overheat = 0.0

        # ---- 실험대 상태 -----------------------------------------------
        self.water_x = 0.0          # 실제 수심 [m]
        self.box_s = 0.42           # 렌즈 -> 테이블 모서리 수평거리 [m]

    # ------------------------------------------------------------------
    def alpha(self):
        s1 = math.sin(self.theta1)
        c1 = math.cos(self.theta1)
        c2 = math.sqrt(1.0 - (s1 / self.n_w) ** 2)
        return self.n_w / c2 - 1.0 / c1

    def _k(self):
        return self.k_rear if self.ref_rear else self.k_front

    def _display(self, half_ct, sigma=0.0008):
        """½ct 를 받아 디스플레이 표시값(1 mm 분해능)을 돌려준다."""
        y = half_ct + self._k() + self.rng.gauss(0.0, sigma)
        if y < self.LDM_MIN or y > self.LDM_MAX:
            return None
        return round(y, 3)

    # ---- 각 측정 모드 --------------------------------------------------
    def read_floor_from_table(self):
        """1.1 : 뒷면을 테이블 윗면에 대고 바닥을 조준."""
        return self._display(self.H - self.k_rear, 0.0008)

    def read_fiber(self, x=None):
        """1.2 : 길이 x 의 광섬유가 송신부-수신부를 잇는다."""
        if x is None:
            x = self.cable_len
        return self._display(0.5 * self.n_co * x, 0.0040)

    def tilt_dot_on_table(self):
        """빔이 테이블 위에 떨어지는가?  (상자 수평 위치로 결정)"""
        reach = self.z_lens * math.tan(self.theta1)
        return self.box_s > reach

    def read_tilt(self):
        """1.3 : y₁(테이블 점) 또는 y₂(바닥 점)."""
        if self.tilt_dot_on_table():
            half = self.z_lens / math.cos(self.theta1)
        else:
            half = (self.z_lens + self.H) / math.cos(self.theta1)
        return self._display(half, 0.0008)

    def read_vessel(self, x=None):
        """1.4 : 깊이 x 의 물이 든 광학 용기 바닥까지."""
        if x is None:
            x = self.water_x
        base = (self.z_lens - self.v_bottom) / math.cos(self.theta1)
        return self._display(base + self.alpha() * x, 0.00035)

    # ---- 도구 ----------------------------------------------------------
    def tape_measure_cable(self):
        """줄자로 광섬유 길이 측정 (1 mm 눈금)."""
        return round(self.cable_len + self.rng.gauss(0.0, 0.0006), 3)

    def tape_read_water(self):
        """용기에 붙인 줄자로 수심 읽기 (1 mm 눈금)."""
        return round(self.water_x + self.rng.gauss(0.0, 0.0004), 3)

    def cut_cable(self, target_m):
        """가위로 자르기 (되돌릴 수 없음)."""
        if target_m >= self.cable_len - 0.004:
            return False, T("현재 케이블보다 짧게만 자를 수 있다.",
                            "You can only cut it shorter than it is now.")
        if target_m < 0.030:
            return False, T("너무 짧다. 30 mm 미만은 다룰 수 없다.",
                            "Too short. Below 30 mm it cannot be handled.")
        self.cable_len = target_m + self.rng.gauss(0.0, 0.0015)
        self.cable_cuts += 1
        return True, None

    def add_water(self, dx):
        self.water_x = max(0.0, min(self.v_inner_h - 0.002,
                                    self.water_x + dx + self.rng.gauss(0, 0.00025)))


# ==========================================================================
#  2D 장비 그리기 (문제지 사진 기반 재구성)
# ==========================================================================
GREEN = "#1f6b4a"
GREEN_D = "#14503a"
BLACKB = "#1a1a1a"
GREY = "#8f8f8f"
SILVER = "#c6c8cb"
LCD = "#b9c9a8"
WATER = "#9dc9e8"
ACRYL = "#dceaf2"


def rr(cv, x0, y0, x1, y1, rad, **kw):
    """둥근 사각형."""
    pts = [x0 + rad, y0, x1 - rad, y0, x1, y0, x1, y0 + rad, x1, y1 - rad,
           x1, y1, x1 - rad, y1, x0 + rad, y1, x0, y1, x0, y1 - rad,
           x0, y0 + rad, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


def draw_ldm(cv, x, y, tag, s=1.0, text="", show_cont=False, rear=True):
    """Bosch PLR 형태의 레이저 거리계 (정면 뷰)."""
    w, h = 46 * s, 104 * s
    x0, y0 = x - w / 2, y - h / 2
    rr(cv, x0, y0, x0 + w, y0 + h, 7 * s, fill=GREEN, outline=GREEN_D,
       width=2, tags=tag)
    # 앞머리(검은 부분)
    rr(cv, x0 + 2 * s, y0 + 2 * s, x0 + w - 2 * s, y0 + 24 * s, 5 * s,
       fill=BLACKB, outline="", tags=tag)
    cv.create_text(x, y0 + 13 * s, text="BOSCH", fill="#dddddd",
                   font=("Helvetica", int(6 * s), "bold"), tags=tag)
    # LCD
    cv.create_rectangle(x0 + 5 * s, y0 + 27 * s, x0 + w - 5 * s, y0 + 55 * s,
                        fill=LCD, outline="#556", tags=tag)
    cv.create_text(x0 + w - 8 * s, y0 + 32 * s,
                   text=("|" if rear else "|"), anchor="e",
                   fill="#333", font=("Helvetica", int(5 * s)), tags=tag)
    cv.create_text(x0 + 8 * s, y0 + 32 * s, text=("CONT" if show_cont else ""),
                   anchor="w", fill="#333", font=("Helvetica", int(5 * s)),
                   tags=tag)
    if text:
        cv.create_text(x, y0 + 44 * s, text=text, fill="#111",
                       font=("Courier", int(11 * s), "bold"), tags=tag)
    # 키패드
    rr(cv, x0 + 6 * s, y0 + 60 * s, x0 + w - 6 * s, y0 + 70 * s, 4 * s,
       fill="#d23a2a", outline="#8d2418", tags=tag)
    for i in range(3):
        for j in range(2):
            cv.create_oval(x0 + (10 + j * 16) * s, y0 + (74 + i * 8) * s,
                           x0 + (20 + j * 16) * s, y0 + (80 + i * 8) * s,
                           fill="#2b2b2b", outline="", tags=tag)


def draw_ldm_side(cv, x, y, tag, s=1.0, tilt_deg=0.0):
    """옆에서 본 LDM (기울여 놓을 때)."""
    w, h = 30 * s, 96 * s
    th = math.radians(tilt_deg)
    ct, st = math.cos(th), math.sin(th)

    def P(u, v):
        return (x + u * ct - v * st, y + u * st + v * ct)

    corners = [P(-w / 2, -h / 2), P(w / 2, -h / 2), P(w / 2, h / 2), P(-w / 2, h / 2)]
    pts = []
    for c in corners:
        pts.extend(c)
    cv.create_polygon(pts, fill=GREEN, outline=GREEN_D, width=2, tags=tag)
    nose = [P(-w / 2, -h / 2), P(w / 2, -h / 2), P(w / 2, -h / 2 + 22 * s),
            P(-w / 2, -h / 2 + 22 * s)]
    p2 = []
    for c in nose:
        p2.extend(c)
    cv.create_polygon(p2, fill=BLACKB, outline="", tags=tag)


def draw_fiber(cv, x, y, tag, s=1.0, length=70):
    cv.create_line(x - length * s / 2, y, x - 10 * s, y - 16 * s,
                   x + 10 * s, y + 16 * s, x + length * s / 2, y,
                   smooth=True, width=int(4 * s), fill="#111", tags=tag,
                   capstyle="round")
    cv.create_line(x - length * s / 2, y, x - length * s / 2 + 6 * s, y - 1,
                   width=int(4 * s), fill="#f2f2c0", tags=tag)


def draw_felt(cv, x, y, tag, s=1.0):
    cv.create_oval(x - 13 * s, y - 13 * s, x + 13 * s, y + 13 * s,
                   fill="#141414", outline="#3a3a3a", width=2, tags=tag)
    cv.create_oval(x - 3 * s, y - 3 * s, x + 3 * s, y + 3 * s,
                   fill="#6a6a6a", outline="", tags=tag)


def draw_tape(cv, x, y, tag, s=1.0):
    cv.create_oval(x - 26 * s, y - 26 * s, x + 26 * s, y + 26 * s,
                   fill="#f2f2ee", outline="#b9b9b0", width=2, tags=tag)
    cv.create_oval(x - 11 * s, y - 11 * s, x + 11 * s, y + 11 * s,
                   fill="#ffffff", outline="#b9b9b0", width=2, tags=tag)
    cv.create_text(x, y + 17 * s, text="IKEA", font=("Helvetica", int(7 * s), "bold"),
                   fill="#555", tags=tag)


def draw_scissors(cv, x, y, tag, s=1.0):
    cv.create_line(x - 18 * s, y - 12 * s, x + 16 * s, y + 10 * s,
                   width=int(3 * s), fill="#9aa0a6", tags=tag)
    cv.create_line(x - 18 * s, y + 12 * s, x + 16 * s, y - 10 * s,
                   width=int(3 * s), fill="#9aa0a6", tags=tag)
    cv.create_oval(x - 26 * s, y - 20 * s, x - 12 * s, y - 6 * s,
                   outline="#1e9ad6", width=int(3 * s), tags=tag)
    cv.create_oval(x - 26 * s, y + 6 * s, x - 12 * s, y + 20 * s,
                   outline="#1e9ad6", width=int(3 * s), tags=tag)


def draw_roll_tape(cv, x, y, tag, s=1.0):
    cv.create_oval(x - 20 * s, y - 20 * s, x + 20 * s, y + 20 * s,
                   fill="#f4efb8", outline="#cfc98d", width=2, tags=tag)
    cv.create_oval(x - 8 * s, y - 8 * s, x + 8 * s, y + 8 * s,
                   fill="#ffffff", outline="#cfc98d", tags=tag)


def draw_angle_iron(cv, x, y, tag, s=1.0, pads=False):
    """ㄴ 자 앵글 철물 (측면)."""
    cv.create_polygon(x - 28 * s, y - 30 * s, x - 16 * s, y - 30 * s,
                      x - 16 * s, y + 18 * s, x + 30 * s, y + 18 * s,
                      x + 30 * s, y + 30 * s, x - 28 * s, y + 30 * s,
                      fill=SILVER, outline="#8e9296", width=2, tags=tag)
    for dx, dy in ((-22, -18), (-22, 2), (8, 24), (22, 24)):
        cv.create_oval(x + (dx - 3) * s, y + (dy - 3) * s,
                       x + (dx + 3) * s, y + (dy + 3) * s,
                       fill="#9aa0a6", outline="", tags=tag)
    if pads:
        cv.create_rectangle(x - 15 * s, y - 26 * s, x - 9 * s, y - 6 * s,
                            fill="#efefef", outline="#c8c8c8", tags=tag)
        cv.create_rectangle(x - 15 * s, y - 2 * s, x - 9 * s, y + 16 * s,
                            fill="#efefef", outline="#c8c8c8", tags=tag)


def draw_foam(cv, x, y, tag, s=1.0):
    cv.create_rectangle(x - 8 * s, y - 20 * s, x + 8 * s, y + 20 * s,
                        fill="#f4f4f4", outline="#c9c9c9", width=2, tags=tag)


def draw_magnet(cv, x, y, tag, s=1.0):
    cv.create_rectangle(x - 8 * s, y - 8 * s, x + 8 * s, y + 8 * s,
                        fill="#7a7f85", outline="#4a4d50", width=2, tags=tag)


def draw_box(cv, x, y, tag, s=1.0):
    """검은 상자 (측면, 윗면이 약 4° 기울어져 있음)."""
    w, h = 150 * s, 78 * s
    cv.create_polygon(x - w / 2, y + h / 2, x + w / 2, y + h / 2,
                      x + w / 2, y - h / 2 + 10 * s, x - w / 2, y - h / 2,
                      fill="#141414", outline="#000", width=2, tags=tag)
    cv.create_text(x, y + 6 * s, text="IPhO 2013", fill="#5a5a5a",
                   font=("Helvetica", int(8 * s), "bold"), tags=tag)


def draw_vessel(cv, x, y, tag, s=1.0, fill_frac=0.0, tape=False):
    """광학 용기 (측면). y 는 바닥 기준선."""
    w, h = 54 * s, 82 * s
    cv.create_rectangle(x - w / 2, y - h, x + w / 2, y, fill=ACRYL,
                        outline="#8fb4c6", width=2, tags=tag)
    if fill_frac > 0:
        wh = h * min(1.0, fill_frac)
        cv.create_rectangle(x - w / 2 + 3, y - wh, x + w / 2 - 3, y - 3,
                            fill=WATER, outline="", tags=tag)
        cv.create_line(x - w / 2 + 3, y - wh, x + w / 2 - 3, y - wh,
                       fill="#3f7fa8", width=2, tags=tag)
    if tape:
        cv.create_rectangle(x + w / 2, y - h, x + w / 2 + 9 * s, y,
                            fill="#fbfbf6", outline="#bdbdb4", tags=tag)
        n = 10
        for i in range(n + 1):
            yy = y - h * i / n
            cv.create_line(x + w / 2, yy, x + w / 2 + (7 if i % 2 == 0 else 4) * s,
                           yy, fill="#666", tags=tag)


# ==========================================================================
#  조립 탭
# ==========================================================================
PARTS = [
    ("LDM", T("A 레이저 거리계", "A Laser distance meter"), draw_ldm),
    ("FIBER", T("B 광섬유 케이블", "B Fiber optic cable"), draw_fiber),
    ("FELT", T("C 검은 펠트 패드", "C Black felt pad"), draw_felt),
    ("TAPEM", T("D 줄자", "D Measuring tape"), draw_tape),
    ("TAPE", T("E 테이프", "E Tape"), draw_roll_tape),
    ("SCIS", T("F 가위", "F Scissors"), draw_scissors),
    ("ANGLE", T("C' 앵글 철물", "C' Angle iron"), draw_angle_iron),
    ("FOAM", T("D' 폼 패드", "D' Foam pads"), draw_foam),
    ("MAG", T("B' 자석", "B' Magnet"), draw_magnet),
    ("VESSEL", T("A' 광학 용기", "A' Optical vessel"), draw_vessel),
]

ZONES = [
    dict(key="Z_TABLE", part="LDM", x=250, y=470,
         label=T("테이블 모서리 (실험 1.1)", "Table edge (task 1.1)")),
    dict(key="Z_LENS", part="FELT", x=250, y=120,
         label=T("수신부 렌즈", "Receiver lens")),
    dict(key="Z_HOLE", part="FIBER", x=400, y=120,
         label=T("펠트 패드 구멍", "Hole in felt pad")),
    dict(key="Z_PADS", part="FOAM", x=250, y=290,
         label=T("앵글 철물 · 폼 패드", "Angle iron · foam pads")),
    dict(key="Z_ANGLDM", part="LDM", x=400, y=290,
         label=T("앵글 철물 · LDM 안착", "Angle iron · seat the LDM")),
    dict(key="Z_MAG", part="MAG", x=580, y=430,
         label=T("상자 내부 · 자석", "Inside the box · magnet")),
    dict(key="Z_BOXANG", part="ANGLE", x=580, y=290,
         label=T("상자 윗면 · 앵글 철물", "Box top · angle iron")),
    dict(key="Z_VESSEL", part="VESSEL", x=740, y=470,
         label=T("빔 경로 · 광학 용기", "Beam path · optical vessel")),
    dict(key="Z_VTAPE", part="TAPEM", x=740, y=340,
         label=T("광학 용기 · 줄자 부착", "Optical vessel · attach tape")),
]


class AssemblyE1(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.state = {z["key"]: None for z in ZONES}   # zone -> part key
        self.where = {}                                # part -> zone key

        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 2))
        ttk.Label(top, text=T("장비를 끌어다 올바른 위치에 조립하시오. "
                              "설치된 부품은 오른쪽 버튼으로 분리한다.",
                              "Drag the equipment into the correct places. "
                              "Right-click an installed part to remove it."),
                  font=("Helvetica", 10)).pack(side="left")

        self.cv = tk.Canvas(self, width=980, height=560, bg="#f7f7f4",
                            highlightthickness=0)
        self.cv.pack(fill="both", expand=True, padx=8, pady=6)

        self.msg = ttk.Label(self, text="", foreground="#a33")
        self.msg.pack(fill="x", padx=10, pady=(0, 6))

        self.drag = None
        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_move)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Button-3>", self.on_right)
        self.redraw()

    # ---------------------------------------------------------------
    def tray_pos(self, i):
        return 70, 60 + i * 52

    def redraw(self):
        cv = self.cv
        cv.delete("all")
        cv.create_rectangle(8, 8, 140, 552, fill="#ececE6", outline="#cfcfc8")
        cv.create_text(74, 24, text=T("부품함", "Parts tray"),
                       font=("Helvetica", 10, "bold"))
        cv.create_rectangle(150, 8, 972, 552, fill="#fbfbf8", outline="#dedad2")
        cv.create_text(560, 24, text=T("작업대", "Workbench"),
                       font=("Helvetica", 10, "bold"), fill="#555")

        # 고정 배경물 : 검은 상자 + 테이블
        draw_box(cv, 580, 400, "bg", 1.0)
        cv.create_line(160, 520, 960, 520, fill="#a58b62", width=6)
        cv.create_text(200, 508, text=T("테이블 윗면", "table top"),
                       fill="#8a6f4a", font=("Helvetica", 8), anchor="w")

        # 존
        for z in ZONES:
            occ = self.state[z["key"]]
            col = "#2f7d4f" if occ else "#b7b2a8"
            cv.create_rectangle(z["x"] - 52, z["y"] - 40, z["x"] + 52, z["y"] + 40,
                                dash=(4, 3), outline=col, width=2)
            cv.create_text(z["x"], z["y"] + 52, text=z["label"], fill="#666",
                           font=("Helvetica", 8))

        # 부품
        for i, (key, label, fn) in enumerate(PARTS):
            zk = self.where.get(key)
            if zk:
                z = [q for q in ZONES if q["key"] == zk][0]
                x, y = z["x"], z["y"]
                sc = 0.85
            else:
                x, y = self.tray_pos(i)
                sc = 0.55
            self._draw_part(key, fn, x, y, sc)
            if not zk:
                cv.create_text(x + 46, y, text=label, anchor="w",
                               font=("Helvetica", 8), fill="#333", tags="lbl")

        self._status()

    def _draw_part(self, key, fn, x, y, sc):
        tag = "P_" + key
        if key == "ANGLE":
            fn(self.cv, x, y, tag, sc, pads=(self.state["Z_PADS"] == "FOAM"))
        elif key == "VESSEL":
            fn(self.cv, x, y + 30 * sc, tag, sc, 0.0,
               tape=(self.state["Z_VTAPE"] == "TAPEM"))
        elif key == "LDM":
            fn(self.cv, x, y, tag, sc, "")
        else:
            fn(self.cv, x, y, tag, sc)

    # ---------------------------------------------------------------
    def _status(self):
        st = []
        if self.state["Z_LENS"] and self.state["Z_HOLE"]:
            st.append(T("설정: 1.2 광섬유", "Setup: 1.2 fiber"))
        if self.state["Z_BOXANG"] and self.state["Z_ANGLDM"]:
            st.append(T("설정: 1.3 기울어진 LDM", "Setup: 1.3 tilted LDM"))
            if self.state["Z_VESSEL"]:
                st.append(T("설정: 1.4 광학 용기", "Setup: 1.4 optical vessel"))
        if self.state["Z_TABLE"]:
            st.append(T("설정: 1.1 높이 측정", "Setup: 1.1 height"))
        self.cv.create_text(560, 540, text="   |   ".join(st) if st else
                            T("(아직 완성된 설정 없음)", "(no complete setup yet)"),
                            fill="#2f7d4f", font=("Helvetica", 9, "bold"))

    def say(self, m, err=True):
        self.msg.config(text=m, foreground="#a33" if err else "#2f7d4f")

    # ---------------------------------------------------------------
    def on_press(self, e):
        items = self.cv.find_overlapping(e.x - 2, e.y - 2, e.x + 2, e.y + 2)
        for it in reversed(items):
            for t in self.cv.gettags(it):
                if t.startswith("P_"):
                    key = t[2:]
                    self.drag = dict(key=key, tag=t, x=e.x, y=e.y)
                    self.cv.tag_raise(t)
                    return

    def on_move(self, e):
        if not self.drag:
            return
        self.cv.move(self.drag["tag"], e.x - self.drag["x"], e.y - self.drag["y"])
        self.drag["x"], self.drag["y"] = e.x, e.y

    def on_release(self, e):
        if not self.drag:
            return
        key = self.drag["key"]
        self.drag = None
        target = None
        for z in ZONES:
            if abs(e.x - z["x"]) < 55 and abs(e.y - z["y"]) < 44:
                target = z
                break
        if target is None:
            if self.where.get(key):
                self.where.pop(key)
                for k, v in list(self.state.items()):
                    if v == key:
                        self.state[k] = None
                self.say(T("부품을 부품함으로 되돌렸다.",
                           "Part returned to the tray."), False)
            self.redraw()
            return
        ok, why = self.check(key, target)
        if not ok:
            self.say(why)
            self.redraw()
            return
        # 이전 위치 비우기
        old = self.where.get(key)
        if old:
            self.state[old] = None
        self.state[target["key"]] = key
        self.where[key] = target["key"]
        self.say(T("설치 완료: ", "Installed: ") + target["label"], False)
        self.redraw()
        self.app.sync()

    def on_right(self, e):
        for z in ZONES:
            if abs(e.x - z["x"]) < 55 and abs(e.y - z["y"]) < 44 and self.state[z["key"]]:
                key = self.state[z["key"]]
                # 종속 부품이 있으면 거부
                dep = {"Z_LENS": "Z_HOLE", "Z_PADS": "Z_ANGLDM",
                       "Z_ANGLDM": "Z_BOXANG", "Z_MAG": "Z_BOXANG",
                       "Z_VESSEL": "Z_VTAPE"}
                d = dep.get(z["key"])
                if d and self.state[d]:
                    self.say(T("먼저 그 위에 설치된 부품을 분리해야 한다.",
                               "Remove the part mounted on top of it first."))
                    return
                self.state[z["key"]] = None
                self.where.pop(key, None)
                self.say(T("분리했다.", "Removed."), False)
                self.redraw()
                self.app.sync()
                return

    def check(self, part, zone):
        if zone["part"] != part:
            return False, T("이 자리에 들어갈 부품이 아니다: ",
                            "That part does not belong here: ") + zone["label"]
        if self.state[zone["key"]] not in (None, part):
            return False, T("이미 다른 부품이 설치되어 있다.",
                            "Another part is already installed there.")
        k = zone["key"]
        if k == "Z_HOLE" and self.state["Z_LENS"] != "FELT":
            return False, T("먼저 수신부 렌즈에 펠트 패드를 붙여야 한다.",
                            "Attach the felt pad to the receiver lens first.")
        if k == "Z_ANGLDM":
            if self.state["Z_PADS"] != "FOAM":
                return False, T("먼저 앵글 철물에 폼 패드 두 개를 붙여야 한다.",
                                "Stick the two foam pads on the angle iron first.")
            if self.state["Z_LENS"] == "FELT":
                return False, T("렌즈에서 검은 펠트 패드를 먼저 제거하라.",
                                "Remove the black felt pad from the lens first.")
        if k == "Z_LENS" and self.state["Z_ANGLDM"] == "LDM":
            return False, T("LDM 이 앵글 철물에 장착된 상태에서는 붙일 수 없다.",
                            "Cannot attach it while the LDM sits on the angle iron.")
        if k == "Z_BOXANG":
            if self.state["Z_MAG"] != "MAG":
                return False, T("상자 안쪽 아래에 자석을 먼저 넣어야 한다.",
                                "Put the magnet inside the box first.")
            if self.state["Z_ANGLDM"] != "LDM":
                return False, T("앵글 철물 위에 LDM 을 먼저 올려야 한다.",
                                "Seat the LDM on the angle iron first.")
        if k == "Z_VESSEL" and self.state["Z_BOXANG"] != "ANGLE":
            return False, T("기울어진 LDM 설정이 먼저 완성되어야 한다.",
                            "The tilted-LDM setup must be complete first.")
        if k == "Z_VTAPE" and self.state["Z_VESSEL"] != "VESSEL":
            return False, T("광학 용기를 먼저 배치하라.",
                            "Place the optical vessel first.")
        if k == "Z_TABLE" and self.state["Z_ANGLDM"] == "LDM":
            return False, T("LDM 이 앵글 철물에 올려져 있다.",
                            "The LDM is sitting on the angle iron.")
        return True, None

    # 벤치가 참조하는 모드 --------------------------------------------
    def mode(self):
        s = self.state
        if s["Z_LENS"] == "FELT" and s["Z_HOLE"] == "FIBER":
            return "fiber"
        if s["Z_BOXANG"] == "ANGLE" and s["Z_ANGLDM"] == "LDM":
            return "vessel" if s["Z_VESSEL"] == "VESSEL" else "tilt"
        if s["Z_TABLE"] == "LDM":
            return "free"
        return "none"


# ==========================================================================
#  실험대 탭
# ==========================================================================
class BenchE1(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.p = app.phys
        self.last = None

        left = ttk.Frame(self)
        left.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.cv = tk.Canvas(left, width=640, height=560, bg="#f4f5f2",
                            highlightthickness=0)
        self.cv.pack(fill="both", expand=True)

        right = ttk.Frame(self, width=340)
        right.pack(side="right", fill="y", padx=6, pady=6)
        right.pack_propagate(False)

        # --- LDM 조작 ---------------------------------------------------
        f = ttk.LabelFrame(right, text=T("레이저 거리계", "Laser distance meter"))
        f.pack(fill="x", pady=4)
        self.disp = tk.Label(f, text="- - -", bg=LCD, fg="#111",
                             font=("Courier", 22, "bold"), width=10, anchor="e",
                             relief="sunken", bd=2)
        self.disp.pack(fill="x", padx=6, pady=6)
        self.ind = ttk.Label(f, text="", font=("Helvetica", 8))
        self.ind.pack(fill="x", padx=6)
        b = ttk.Frame(f)
        b.pack(fill="x", padx=6, pady=6)
        ttk.Button(b, text=T("A 전원", "A power"), width=10,
                   command=self.power).grid(row=0, column=0, padx=2, pady=2)
        ttk.Button(b, text=T("B 기준면", "B ref."), width=10,
                   command=self.refsw).grid(row=0, column=1, padx=2, pady=2)
        ttk.Button(b, text=T("D 측정", "D measure"), width=10,
                   command=self.measure).grid(row=1, column=0, padx=2, pady=2)
        ttk.Button(b, text=T("E 연속", "E cont."), width=10,
                   command=self.contsw).grid(row=1, column=1, padx=2, pady=2)

        # --- 조준 / 설정 -------------------------------------------------
        self.f_aim = ttk.LabelFrame(right, text=T("배치", "Placement"))
        self.f_aim.pack(fill="x", pady=4)
        self.aim_body = ttk.Frame(self.f_aim)
        self.aim_body.pack(fill="x", padx=6, pady=6)

        # --- 도구 -------------------------------------------------------
        f2 = ttk.LabelFrame(right, text=T("도구", "Tools"))
        f2.pack(fill="x", pady=4)
        row = ttk.Frame(f2)
        row.pack(fill="x", padx=6, pady=4)
        ttk.Label(row, text=T("자를 길이 [mm]", "cut to [mm]")).pack(side="left")
        self.cutvar = tk.StringVar(value="900")
        ttk.Entry(row, textvariable=self.cutvar, width=7).pack(side="left", padx=4)
        ttk.Button(row, text=T("F 가위로 자르기", "F cut"),
                   command=self.cut).pack(side="left")
        ttk.Button(f2, text=T("D 줄자로 케이블 길이 측정",
                              "D measure cable with tape"),
                   command=self.tape_cable).pack(fill="x", padx=6, pady=3)

        # --- 기록 -------------------------------------------------------
        f3 = ttk.LabelFrame(right, text=T("측정 기록", "Measurement log"))
        f3.pack(fill="both", expand=True, pady=4)
        self.log = tk.Text(f3, height=12, width=40, font=("Courier", 9))
        self.log.pack(fill="both", expand=True, padx=4, pady=4)
        ttk.Button(f3, text=T("기록 지우기", "clear"),
                   command=lambda: self.log.delete("1.0", "end")).pack(pady=2)

        self.build_aim()
        self.draw()

    # ------------------------------------------------------------------
    def logline(self, s):
        self.log.insert("end", s + "\n")
        self.log.see("end")

    def power(self):
        self.p.power = not self.p.power
        if not self.p.power:
            self.last = None
            self.p.ref_rear = True
            self.p.cont = False
        self.refresh()

    def refsw(self):
        if not self.p.power:
            return
        self.p.ref_rear = not self.p.ref_rear
        self.refresh()

    def contsw(self):
        if not self.p.power:
            return
        self.p.cont = not self.p.cont
        self.refresh()
        if self.p.cont:
            self.tick()

    def tick(self):
        if self.p.cont and self.p.power:
            self.measure(silent=True)
            self.after(900, self.tick)

    def measure(self, silent=False):
        if not self.p.power:
            self.disp.config(text="- - -")
            return
        m = self.app.asm.mode()
        if m == "none":
            self.last = None
            self.disp.config(text="Err")
            if not silent:
                self.logline(T("[조립 미완성]", "[setup incomplete]"))
            return
        if m == "fiber":
            v = self.p.read_fiber()
        elif m == "free":
            v = self.p.read_floor_from_table()
        elif m == "tilt":
            v = self.p.read_tilt()
        else:
            v = self.p.read_vessel()
        self.last = v
        self.refresh()
        if not silent:
            tagm = {"fiber": T("광섬유", "fiber"), "free": T("높이", "height"),
                    "tilt": T("기울임", "tilt"), "vessel": T("용기", "vessel")}[m]
            extra = ""
            if m == "vessel":
                extra = "  x=%.3f m" % self.p.tape_read_water()
            if m == "tilt":
                extra = "  (%s)" % (T("테이블 점", "dot on table")
                                    if self.p.tilt_dot_on_table()
                                    else T("바닥 점", "dot on floor"))
            self.logline("%-7s y = %s m%s" % (tagm,
                         ("%.3f" % v) if v is not None else "Err", extra))

    def cut(self):
        try:
            mm = float(self.cutvar.get())
        except ValueError:
            messagebox.showerror("", T("숫자를 입력하라.", "Enter a number."))
            return
        if not messagebox.askyesno(
                T("경고", "Warning"),
                T("광섬유 케이블을 자르기 전에 매우 신중하게 생각할 것.\n"
                  "더 이상의 케이블은 받을 수 없다!!\n\n%d mm 로 자르겠는가?" % mm,
                  "Think very carefully before cutting the fiber optic cable.\n"
                  "You cannot get more cable!!\n\nCut to %d mm?" % mm)):
            return
        ok, why = self.p.cut_cable(mm / 1000.0)
        if not ok:
            messagebox.showwarning("", why)
            return
        self.logline(T("[가위] 케이블을 잘랐다 (%d 회째)",
                       "[scissors] cable cut (#%d)") % self.p.cable_cuts)
        self.draw()

    def tape_cable(self):
        v = self.p.tape_measure_cable()
        self.logline(T("[줄자] 케이블 길이 x = %.3f m",
                       "[tape] cable length x = %.3f m") % v)

    # ------------------------------------------------------------------
    def build_aim(self):
        for w in self.aim_body.winfo_children():
            w.destroy()
        m = self.app.asm.mode()
        if m == "tilt" or m == "vessel":
            ttk.Label(self.aim_body,
                      text=T("상자 수평 위치 (렌즈→테이블 모서리) [cm]",
                             "box position (lens→table edge) [cm]")).pack(anchor="w")
            self.sv = tk.DoubleVar(value=self.p.box_s * 100)
            s = ttk.Scale(self.aim_body, from_=2, to=60, variable=self.sv,
                          command=self.on_slide)
            s.pack(fill="x")
        if m == "vessel":
            r = ttk.Frame(self.aim_body)
            r.pack(fill="x", pady=6)
            ttk.Button(r, text=T("물 +5 mm", "water +5 mm"), width=12,
                       command=lambda: self.water(+0.005)).grid(row=0, column=0, padx=2)
            ttk.Button(r, text=T("물 +1 mm", "water +1 mm"), width=12,
                       command=lambda: self.water(+0.001)).grid(row=0, column=1, padx=2)
            ttk.Button(r, text=T("피펫 -5 mm", "pipette -5 mm"), width=12,
                       command=lambda: self.water(-0.005)).grid(row=1, column=0, padx=2)
            ttk.Button(r, text=T("모두 비움", "empty"), width=12,
                       command=self.empty).grid(row=1, column=1, padx=2)
            self.wl = ttk.Label(self.aim_body, text="", font=("Courier", 10))
            self.wl.pack(anchor="w", pady=2)
        if m == "free":
            ttk.Label(self.aim_body,
                      text=T("LDM 뒷면을 테이블 윗면에 대고\n바닥을 조준한 상태",
                             "LDM rear face on the table top,\naimed at the floor")
                      ).pack(anchor="w")
        if m == "fiber":
            ttk.Label(self.aim_body,
                      text=T("케이블 한쪽 끝은 펠트 패드 구멍에,\n"
                             "다른 끝은 송신부 유리에 대고 있음",
                             "One end in the felt-pad hole,\n"
                             "the other against the transmitter")
                      ).pack(anchor="w")
        if m == "none":
            ttk.Label(self.aim_body, foreground="#a33",
                      text=T("조립 탭에서 설정을 완성하시오.",
                             "Complete a setup in the Assembly tab.")).pack(anchor="w")

    def on_slide(self, _=None):
        self.p.box_s = self.sv.get() / 100.0
        self.draw()
        if self.p.cont:
            self.measure(silent=True)

    def water(self, dx):
        self.p.add_water(dx)
        self.refresh()

    def empty(self):
        self.p.water_x = 0.0
        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self):
        p = self.p
        if not p.power:
            self.disp.config(text="- - -")
        elif self.last is None:
            self.disp.config(text="")
        else:
            self.disp.config(text="%.3f" % self.last)
        ind = []
        ind.append(T("기준: 뒷면", "ref: rear") if p.ref_rear
                   else T("기준: 앞면", "ref: front"))
        if p.cont:
            ind.append(T("연속 측정", "continuous"))
        self.ind.config(text="   ".join(ind))
        if hasattr(self, "wl") and self.wl.winfo_exists():
            self.wl.config(text=T("용기 줄자 눈금  ", "tape on vessel  ")
                           + "%.3f m" % p.tape_read_water())
        self.draw()

    # ------------------------------------------------------------------
    def draw(self):
        cv = self.cv
        cv.delete("all")
        m = self.app.asm.mode()
        p = self.p
        W, H = 640, 560
        floor_y = 500
        table_y = 300
        cv.create_rectangle(0, 0, W, H, fill="#f4f5f2", outline="")
        # 바닥 / 테이블
        cv.create_rectangle(0, floor_y, W, H, fill="#e6ded2", outline="#c9bda9")
        cv.create_rectangle(60, table_y, 600, table_y + 10, fill="#a58b62",
                            outline="#7d6746")
        cv.create_rectangle(90, table_y + 10, 110, floor_y, fill="#8f7550", outline="")
        cv.create_rectangle(560, table_y + 10, 580, floor_y, fill="#8f7550", outline="")
        cv.create_text(70, table_y - 8, text=T("테이블 윗면", "table top"),
                       anchor="w", fill="#7d6746", font=("Helvetica", 8))
        cv.create_text(10, floor_y - 8, text=T("바닥", "floor"), anchor="w",
                       fill="#8a7d6a", font=("Helvetica", 8))

        if m == "none":
            cv.create_text(W / 2, 180, text=T("조립되지 않음",
                                              "nothing assembled"),
                           fill="#999", font=("Helvetica", 14))
            return

        if m == "free":
            draw_ldm_side(cv, 520, table_y - 48, "ldm", 1.0, 0)
            cv.create_line(520, table_y + 6, 520, floor_y, fill="#e03030",
                           width=2, dash=(6, 3))
            cv.create_oval(514, floor_y - 5, 526, floor_y + 5, fill="#ff5050",
                           outline="")
            cv.create_text(534, (table_y + floor_y) / 2, text="H", anchor="w",
                           fill="#444", font=("Helvetica", 12, "italic"))
            return

        if m == "fiber":
            draw_ldm(cv, 300, 180, "ldm", 1.6, "")
            draw_felt(cv, 282, 118, "felt", 1.3)
            cv.create_line(282, 118, 250, 250, 380, 250, 322, 122,
                           smooth=True, width=5, fill="#111", capstyle="round")
            cv.create_text(320, 300,
                           text=T("케이블 길이 x = 줄자로 측정",
                                  "cable length x : use the tape"),
                           fill="#666", font=("Helvetica", 9))
            return

        # tilt / vessel : 상자 + 앵글 + LDM
        bx = 300
        draw_box(cv, bx, table_y - 44, "box", 0.95)
        draw_angle_iron(cv, bx + 8, table_y - 100, "ang", 0.8, pads=True)
        draw_ldm_side(cv, bx + 22, table_y - 148, "ldm", 0.95,
                      tilt_deg=math.degrees(p.theta1))
        lens_x = bx + 22 + 40 * math.sin(p.theta1)
        lens_y = table_y - 148 - 40 * math.cos(p.theta1) + 18
        # 픽셀 스케일: 테이블~바닥 실제 H(m) -> (floor_y-table_y) px
        scale = (floor_y - table_y) / p.H
        z_px = p.z_lens * scale
        lens_y = table_y - z_px
        cv.create_oval(lens_x - 3, lens_y - 3, lens_x + 3, lens_y + 3,
                       fill="#c00", outline="")

        edge_x = 600
        s_px = p.box_s * scale
        # 빔
        tan = math.tan(p.theta1)
        dot_dx = z_px * tan
        if p.box_s > p.z_lens * tan:
            # 테이블 위
            dx = dot_dx
            dot = (lens_x + dx, table_y)
        else:
            dx = (z_px + (floor_y - table_y)) * tan
            dot = (lens_x + dx, floor_y)
        cv.create_line(lens_x, lens_y, dot[0], dot[1], fill="#e03030", width=2)
        cv.create_oval(dot[0] - 5, dot[1] - 4, dot[0] + 5, dot[1] + 4,
                       fill="#ff4040", outline="")
        # 모서리 표시
        cv.create_line(lens_x, lens_y - 14, lens_x, table_y - z_px - 14,
                       fill="#888")
        cv.create_line(lens_x, table_y - 4, lens_x + s_px, table_y - 4,
                       fill="#4477aa", dash=(3, 2))

        if m == "vessel":
            vx = lens_x + dot_dx
            frac = p.water_x / 0.100
            draw_vessel(cv, vx, table_y, "ves", 1.0, frac, tape=True)
            cv.create_text(vx, table_y + 18,
                           text=T("광학 용기", "optical vessel"),
                           fill="#666", font=("Helvetica", 8))


# ==========================================================================
class App(tk.Tk):
    def __init__(self, seed=None):
        super().__init__()
        self.title("IPhO 2013  E1 — " + T("빛의 속력", "Speed of light"))
        self.geometry("1010x660")
        self.phys = E1Physics(seed)
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.asm = AssemblyE1(nb, self)
        self.bench = BenchE1(nb, self)
        nb.add(self.asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.bench, text=T(" 실험대 ", " Bench "))
        self.nb = nb
        nb.bind("<<NotebookTabChanged>>", lambda e: self.sync())

    def sync(self):
        try:
            self.bench.build_aim()
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
