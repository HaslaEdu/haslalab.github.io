#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPhO 2021 (Lithuania) - Experimental Examination Simulator
==========================================================
Experiment 1 : Non-ideal capacitors      (Q1, 10 points)
Experiment 2 : Light Emitting Diodes     (Q2, 10 points)

The whole examination shares ONE measurement / sample board and ONE Android
tablet running the "IPhO 2021 Experiments" app, therefore both experiments are
simulated inside a single apparatus, exactly like in the real examination.

Design rule (HaslaLab):
    The simulator NEVER computes or displays a derived physical quantity for
    the student.  Only what the real instruments show is displayed:
    raw voltages (uC, uT, uL), their time derivatives as produced by the board
    firmware (duC, duT, duL), currents (iL, iH), time (t), the room
    thermometer and the board ID.  Capacitance, temperature, thermal
    resistance, dU/dT ... must be obtained by the student.

Author: HaslaLab   |   stdlib + tkinter only

Run:  python ipho2021_sim_KO.py   (EN edition: ipho2021_sim_EN.py)
"""

import base64
import binascii
import json
import math
import os
import random
import socket
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from tkinter import ttk, messagebox

APP_VERSION = "1.0"

# ----------------------------------------------------------------------------
#  i18n
# ----------------------------------------------------------------------------
LANG = "KO"          # the EN edition differs only in this line (switchable from the menu too)

TR = {
    "title":        ("IPhO 2021 Lithuania — Experimental Examination", "IPhO 2021 리투아니아 — 실험 시험"),
    "bench":        ("Laboratory bench", "실험대"),
    "tray":         ("Equipment list (tap an item to put it on the bench)",
                     "장비 목록 (항목을 누르면 실험대에 올려집니다)"),
    "menu_lang":    ("Language", "언어"),
    "menu_speed":   ("Time", "시간"),
    "menu_help":    ("Tasks", "문제"),
    "menu_view":    ("View", "보기"),
    "speed_x":      ("Simulation speed ×%s", "시뮬레이션 속도 ×%s"),
    "open_tablet":  ("Open tablet", "태블릿 열기"),
    "open_tasks":   ("Problem sheet", "문제지"),
    "reset_bench":  ("Reset bench", "실험대 초기화"),
    "board_id":     ("Board ID", "보드 ID"),
    "thermometer":  ("Thermometer (examination hall)", "온도계 (시험장)"),
    "no_power":     ("Board is not powered", "보드에 전원이 없습니다"),
    "powered":      ("Board powered", "보드 전원 켜짐"),
    "usb_no":       ("No USB connected", "USB가 연결되지 않음"),
    "usb_ok":       ("Device connected.", "장치가 연결되었습니다."),
    "usb_perm":     ("Allow the app to access the USB device?", "앱이 USB 장치에 접근하도록 허용할까요?"),
    "usb_allow":    ("ALLOW", "허용"),
    "usb_deny":     ("DENY", "거부"),
    "usb_denied":   ("USB Permission not granted", "USB 접근이 허용되지 않았습니다"),
    "saved_n":      ('"%s" saved (%d pts)', '"%s" 저장됨 (%d개)'),
    "press_reset":  ("Please press RESET button on the board in 10 seconds!",
                     "10초 안에 보드의 RESET 버튼을 누르세요!"),
    "plug_first":   ("Please plug in, power on and reset the board first.",
                     "먼저 보드를 연결하고 전원을 켠 뒤 리셋하세요."),
    "w1_label":     ("W1  (100 MΩ)", "W1  (100 MΩ)"),
    "w2_label":     ("W2  (0 Ω)", "W2  (0 Ω)"),
    "insul":        ("Heat insulating material", "단열재"),
    "charger":      ("USB power source", "USB 전원 공급기"),
    "datacable":    ("Board–tablet cable", "보드–태블릿 케이블"),
    "tablet":       ("Tablet", "태블릿"),
    "start_title":  ("Before the experiment — the IPhO 2021 Experiments app", "실험을 시작하기 전에 — IPhO 2021 Experiments 앱"),
    "start_text":   ("In the real examination the app came installed on the Android tablet that connects to the board.\n"
                     "Choose where it runs: on the virtual tablet (a window of this program), or on your own tablet, "
                     "phone or computer - this program serves the app over your Wi-Fi and the device's browser links to the board.\n"
                     "You can switch later from the menu (View).",
                     "실제 시험에서는 보드에 연결하는 안드로이드 태블릿에 이 앱이 미리 설치되어 있었습니다.\n"
                     "앱을 어디서 쓸지 고르세요: 가상 태블릿(이 프로그램의 창)이나, 내 태블릿 · 휴대폰 · 컴퓨터입니다. "
                     "내 기기를 고르면 이 프로그램이 와이파이로 앱을 내보내고, 기기의 브라우저가 보드와 연결됩니다.\n"
                     "나중에 메뉴(보기)에서 바꿀 수 있습니다."),
    "use_virtual":  ("Use the virtual tablet", "가상 태블릿 사용"),
    "use_remote":   ("Use the app on my tablet or computer", "내 태블릿 · 컴퓨터에서 앱 사용"),
    "menu_link":    ("How the app connects…", "앱 연결 방식…"),
    "remote_title": ("The app on my tablet or computer", "내 태블릿 · 컴퓨터의 앱"),
    "remote_text":  ("Open one of these addresses in the browser of a tablet, phone or computer on the same Wi-Fi "
                     "(on this computer, the second one). Then put '6 Tablet' and '5 cable' on the bench; the app asks for "
                     "USB access - allow it and press RESET on the board. If the device cannot reach it, allow this "
                     "program through the firewall.",
                     "같은 와이파이에 있는 태블릿 · 휴대폰 · 컴퓨터의 브라우저에서 아래 주소 중 하나를 여세요 "
                     "(이 컴퓨터라면 두 번째 주소). 그다음 실험대에 '6 태블릿'과 '5 케이블'을 놓으면 앱이 USB 접근 허용을 묻습니다. "
                     "허용한 뒤 보드의 RESET을 누르세요. 기기에서 열리지 않으면 방화벽에서 이 프로그램을 허용하세요."),
    "open_browser": ("Open in this computer's browser", "이 컴퓨터의 브라우저에서 열기"),
    "remote_wait":  ("Waiting for the app…", "앱의 연결을 기다리는 중…"),
    "remote_ok":    ("The app is connected.", "앱이 연결되었습니다."),
    "remote_fail":  ("Could not open a port for the app (8021-8040 are busy).", "앱에 쓸 포트를 열지 못했습니다 (8021-8040 사용 중)."),
    "remove":       ("put back to the tray", "트레이로 되돌리기"),
    "short":        ("SHORT CIRCUIT between two voltage sources — disconnect the wire!",
                     "두 전압원 사이가 단락되었습니다 — 배선을 분리하세요!"),
    "meas":         ("Measure", "측정"),
    "check":        ("Check state", "상태 확인"),
    "mtitle":       ("Measurement title", "측정 이름"),
    "settings":     ("Settings", "설정"),
    "funceditor":   ("Function Editor", "함수 편집기"),
    "lastmeas":     ("Last measurement", "마지막 측정"),
    "tapmeas":      ("Tap for measurements", "측정 선택"),
    "sel_y":        ("Select Y axis", "Y축 선택"),
    "sel_x":        ("Select X axis", "X축 선택"),
    "sel_col":      ("Select column", "열 선택"),
    "cancel":       ("CANCEL", "취소"),
    "select":       ("SELECT", "선택"),
    "apply":        ("Apply", "적용"),
    "notitle":      ("No measurement title entered!", "측정 이름이 입력되지 않았습니다!"),
    "exists":       ("This name already exists!", "같은 이름이 이미 있습니다!"),
    "nomeas":       ("No measurement with this title exists", "해당 이름의 측정이 없습니다"),
    "duringmeas":   ("You don't want to do this during measurement.", "측정 중에는 할 수 없습니다."),
    "badled":       ("Bad value of LED current!", "LED 전류 값이 잘못되었습니다!"),
    "badheat":      ("Bad heater current value!", "히터 전류 값이 잘못되었습니다!"),
    "badpulse":     ("Bad value of LED current pulse width entered!", "LED 펄스 폭 값이 잘못되었습니다!"),
    "deleted":      ("deleted", "삭제됨"),
    "nothing_sel":  ("Nothing to select from!", "선택할 항목이 없습니다!"),
    "enterfunc":    ("Enter function", "함수 입력"),
    "showctrl":     ("Show controls for", "컨트롤 표시 대상"),
    "timestep":     ("Time step of measurement", "측정 시간 간격"),
    "offled":       ("Turn off LED current when measurement is done.", "측정 종료 시 LED 전류 끄기"),
    "offheat":      ("Turn off heating current when measurement is done.", "측정 종료 시 히터 전류 끄기"),
    "sweep":        ("Sweep measurement", "스윕 측정"),
    "sweepdesc":    ("This setting will enable measuring I-V curve, by increasing current and "
                     "measuring resulting voltage automatically in sweep mode.",
                     "전류를 증가시키며 전압을 자동으로 측정하여 I-V 곡선을 얻습니다."),
    "sweepset":     ("Sweep measurement settings", "스윕 측정 설정"),
    "sweepmin":     ("Minimum sweep measurement current", "스윕 최소 전류"),
    "sweepmax":     ("Maximum sweep measurement current", "스윕 최대 전류"),
    "sweepn":       ("Number of steps of sweep measurement", "스윕 단계 수"),
    "sweepexp":     ("Increase current exponentially", "전류를 지수적으로 증가"),
    "sweeppulse":   ("Set pulsed current", "펄스 전류 사용"),
    "pulsedur":     ("Current pulse duration", "전류 펄스 지속시간"),
    "allstopped":   ("All running measurements stopped. Tap again to start measurement.",
                     "실행 중이던 측정이 중지되었습니다. 다시 눌러 측정을 시작하세요."),
    "tasks_hdr":    ("Problem sheet (official IPhO 2021 text)", "문제지 (IPhO 2021 공식 문항)"),
    "roomT":        ("Room temperature", "실온"),
    "t_charger":    ("USB power", "USB 전원"),
    "t_cable":      ("Board–tablet cable", "보드–태블릿 선"),
    "t_insul":      ("Insulation", "단열재"),
    "t_therm":      ("Thermometer", "온도계"),
}


def T(key, *a):
    s = TR[key][0 if LANG == "EN" else 1]
    return s % a if a else s


# ============================================================================
#                              PHYSICS ENGINE
# ============================================================================
# All parameters below describe the *hardware*.  Nothing here is ever shown to
# the student; the GUI only exposes the instrument readings.

K_B = 1.380649e-23
Q_E = 1.602176634e-19

# ---- thermostat / PCB -------------------------------------------------------
R_HEAT = 3.90          # Ohm       heater resistor on the PCB
RTH_PCB_INS = 78.0     # K/W       PCB -> ambient, insulating pad installed
RTH_PCB_OPEN = 55.0    # K/W       PCB -> ambient, pad removed
C_TH_PCB = 1.50        # J/K       heat capacity of the thermostat block

# ---- NTC thermistor --------------------------------------------------------
NTC_B = 3500.0         # K   (given in G1)
NTC_R0_NOM = 0.03435   # Ohm (nominal; each board differs by a few %)
R3 = 2260.0            # Ohm
U_SUP = 3.3            # V

# ---- LED -------------------------------------------------------------------
LED_M = 0.06497294     # V     n*kT/q at the reference temperature
LED_IS = 1.7679150e-15  # A     saturation current
LED_RS = 4.70832       # Ohm   series resistance
LED_TREF = 22.0        # degC  reference temperature of the U(I) fit
# dU/dT [mV/K] anchored on the official A.2 table (least-squares slope of the
# four temperatures at each current); piecewise linear in ln(I), clamped.
LED_S_ANCHOR = ((0.003, -1.563), (0.010, -1.722), (0.020, -1.790), (0.040, -2.010))
RTH_LED = 400.0        # K/W   junction -> PCB thermal resistance

# ---- capacitors ------------------------------------------------------------
C1_NOM = 0.1000e-6     # F    class-1 ceramic: independent of U and T
C2_A = 19.33e-6        # Curie-Weiss numerator (F*K)
C2_TC = -17.8          # degC
C2_W0 = 2.19           # V  at 29 degC
C2_WT = 0.025          # V/K
C2_P = 2.66
C2_FLOOR = 0.060e-6    # F
# dielectric absorption (Debye) branches of C2: (fraction, tau[s])
C2_BRANCH = ((0.060, 0.030), (0.050, 0.250), (0.040, 1.50), (0.030, 12.0))
R_LEAK = 30.0e9        # Ohm  capacitor leakage at low voltage
R_INSUL_WET = 20.0e9   # Ohm  damp insulating pad shunting the capacitor node
I_VOLTMETER = 20e-12   # A    voltmeter input (bias) current

R_W1 = 100e6           # Ohm  jumper wire W1
R_W2 = 0.0             # Ohm  jumper wire W2

# ---- measurement front end -------------------------------------------------
LSB_UC, SIG_UC = 0.25e-3, 0.20e-3
LSB_UT, SIG_UT = 0.10e-3, 0.10e-3
LSB_UL, SIG_UL = 0.10e-3, 0.15e-3

SOURCES = {"P9A": 9.0, "P9B": 9.0, "N9A": -9.0, "N9B": -9.0,
           "GNDA": 0.0, "GNDB": 0.0}
IN_SOCKETS = ("INA", "INB")


def led_dUdT(i):
    """temperature coefficient of the forward voltage [V/K] at current i [A]"""
    xs = [math.log(a) for a, _ in LED_S_ANCHOR]
    ys = [b for _, b in LED_S_ANCHOR]
    x = math.log(max(i, 1e-9))
    if x <= xs[0]:
        k = (ys[1] - ys[0]) / (xs[1] - xs[0])
        y = ys[0] + k * (x - xs[0])
    elif x >= xs[-1]:
        k = (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
        y = ys[-1] + k * (x - xs[-1])
    else:
        for j in range(len(xs) - 1):
            if xs[j] <= x <= xs[j + 1]:
                f = (x - xs[j]) / (xs[j + 1] - xs[j])
                y = ys[j] + f * (ys[j + 1] - ys[j])
                break
    return max(-2.2, min(-1.0, y)) * 1e-3


def _q(x, lsb, sigma, rng):
    """ADC: gaussian noise + quantisation."""
    return round((x + rng.gauss(0.0, sigma)) / lsb) * lsb


# ============================================================================
#        THE BOARD'S STM32 AS THE APP SEES IT  (UsbProtocol / Converter)
# ============================================================================
#  The examination app (com.smm.ipholab.ipho.smm.ipho2020, version 1.01) talks
#  to the board's STM32 over USB serial (115200 8N1).  Every request is
#  answered by a 30-byte frame:
#     [6:8] uT  16 bit over 0..3.3 V      [8:10]  uL 16 bit over 0..3.3 V
#     [10:13] uC 24 bit over -10.05..+10.05 V
#     [13:15] heater DAC code             [15:17] LED current (12 bit + 1 mA range bit)
#     [17:19] heater current ADC          [19:23] ADC clock, 10 ms ticks
#     [25] error code                     [26:30] CRC32
#  The board (Board.frame) builds these frames and the app decodes them
#  exactly as Converter.java does.  Board.firmware is what runs the app's
#  measurement thread at 140 ms of board time.
def led_code(A):
    if A <= 0.001:
        mx, bit = 0.001, 0
    else:
        mx, bit = 0.05, 0x80
    A = max(0.0, min(mx, A))
    c = int(4095 * (A / mx))
    return [c & 255, ((c >> 8) & 255) | bit]


def led_amps(b0, b1):
    return ((b0 | ((b1 & 0x7F) << 8)) / 4095.0) * (0.05 if b1 & 0x80 else 0.001)


def _put(b, o, v, n):
    v = int(v)
    for i in range(n):
        b[o + i] = (v >> (8 * i)) & 255


def _ci(v, a, b):
    return max(a, min(b, int(round(v))))


def _u16(b, o):
    return b[o] | (b[o + 1] << 8)


def _u24(b, o):
    return b[o] | (b[o + 1] << 8) | (b[o + 2] << 16)


def _u32(b, o):
    return b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24)


def _conv(raw, i0, i1, d0, d1):
    return d0 + (raw - i0) / float(i1 - i0) * (d1 - d0)


class Board:
    """Measurement and sample board (item 1 of the equipment list)."""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        r = self.rng
        # per-board scatter
        self.room_T = round(r.uniform(21.0, 26.0), 1)          # degC
        self.board_id = "%06d" % r.randrange(100000, 999999)
        self.ntc_R0 = NTC_R0_NOM * (1.0 + r.uniform(-0.02, 0.02))
        self.c1 = C1_NOM * (1.0 + r.uniform(-0.006, 0.006))
        self.c2_scale = 1.0 + r.uniform(-0.02, 0.02)
        self.led_dU = r.uniform(-0.0015, 0.0015)               # LED unit spread

        # --- assembly state
        self.powered = False        # USB charger plugged
        self.data_cable = False     # 6-pin cable to the tablet
        self.insulation = True      # insulating pad on the thermostat
        self.sw1 = "C1"             # "C1" | "MID" | "C2"
        self.wires = {"W1": [None, None], "W2": [None, None]}  # socket names
        self.short_circuit = False
        self.reset_pressed_at = -1e9

        # --- driven quantities (set by the app)
        self.iH = 0.0               # mA
        self.iL = 0.0               # mA
        self.tL = 0.0               # ms (0 -> DC)
        self.heat_code = 4095       # heater DAC code as last written by the app
        self.clock = 0.0            # s since the STM32 started (ADC clock)

        # --- dynamic state
        self.t = 0.0
        self.T_pcb = self.room_T
        self.uC = 0.0
        self.vb = [0.0] * len(C2_BRANCH)
        self._duC = self._duT = self._duL = 0.0
        self._uT_prev = self._uL_prev = None
        self._uL_now = 0.0

    # ---------------- wiring helpers ---------------------------------------
    def wire_paths(self):
        """[(R, V_source)] for every wire that joins an IN socket to a source"""
        out = []
        self.short_circuit = False
        for name, (a, b) in self.wires.items():
            R = R_W1 if name == "W1" else R_W2
            if a in SOURCES and b in SOURCES and SOURCES[a] != SOURCES[b] and R == 0.0:
                self.short_circuit = True
            for x, y in ((a, b), (b, a)):
                if x in IN_SOCKETS and y in SOURCES:
                    out.append((R, SOURCES[y]))
        return out

    # ---------------- capacitance model ------------------------------------
    def c2_total(self, u, Tc):
        """differential capacitance of C2 at terminal voltage u, temp Tc"""
        w = C2_W0 + C2_WT * (Tc - 29.0)
        hi = C2_A / (Tc - C2_TC)
        return self.c2_scale * (hi / (1.0 + (abs(u) / w) ** C2_P) + C2_FLOOR)

    C2_FBR = sum(f for f, _ in C2_BRANCH)

    def cap_value(self, u, Tc):
        """capacitance seen instantaneously at the terminal (geometric part;
        the dielectric-absorption branches are treated separately)"""
        if self.sw1 == "C1":
            return self.c1
        if self.sw1 == "C2":
            return (1.0 - self.C2_FBR) * self.c2_total(u, Tc)
        return 1e-12                      # middle position: nothing connected

    # ---------------- LED model --------------------------------------------
    def led_voltage(self, i_mA, Tj):
        """forward voltage [V] of the LED at current i_mA and junction temp Tj"""
        if i_mA <= 1e-6:
            return 0.0
        i = i_mA * 1e-3
        u0 = LED_M * math.log1p(i / LED_IS) + LED_RS * i + self.led_dU
        return u0 + led_dUdT(i) * (Tj - LED_TREF)

    def led_state(self):
        """-> (uL, Tj, P_electrical_mean)"""
        if self.iL <= 1e-6 or not self.powered:
            return 0.0, self.T_pcb, 0.0
        if self.tL > 0.0:                       # pulsed: no self heating
            u = self.led_voltage(self.iL, self.T_pcb)
            duty = min(1.0, self.tL * 1e-3 / max(self.timestep, 1e-3))
            return u, self.T_pcb, u * self.iL * 1e-3 * duty
        Tj = self.T_pcb                          # DC: solve self-heating
        for _ in range(4):
            u = self.led_voltage(self.iL, Tj)
            Tj = self.T_pcb + RTH_LED * u * self.iL * 1e-3
        u = self.led_voltage(self.iL, Tj)
        return u, Tj, u * self.iL * 1e-3

    # ---------------- NTC ---------------------------------------------------
    def ntc_voltage(self):
        R = self.ntc_R0 * math.exp(NTC_B / (self.T_pcb + 273.15))
        return U_SUP * R / (R + R3)

    # ---------------- integration ------------------------------------------
    timestep = 0.140            # measurement time step (s), set by the app

    def step(self, dt):
        """advance the hardware by dt seconds (dt <= 5 ms recommended)"""
        if not self.powered:
            self.iH = self.iL = self.tL = 0.0
            self.heat_code, self.clock = 4095, 0.0
        self.t += dt
        if self.powered:
            self.clock += dt

        # ---- thermal ------------------------------------------------------
        p_heat = (self.iH * 1e-3) ** 2 * R_HEAT
        uL_now, _tj, p_led = self.led_state()
        self._uL_now = uL_now
        rth = RTH_PCB_INS if self.insulation else RTH_PCB_OPEN
        dT = (p_heat + p_led - (self.T_pcb - self.room_T) / rth) / C_TH_PCB
        self.T_pcb += dT * dt

        # ---- capacitor node ----------------------------------------------
        C = self.cap_value(self.uC, self.T_pcb)
        clamp = None
        i_ext = 0.0
        for R, V in self.wire_paths():
            if R <= 0.0:
                clamp = V
            else:
                i_ext += (V - self.uC) / R
        # leakage of the capacitor + voltmeter bias + damp insulation
        u = self.uC
        i_ext -= u / R_LEAK * (1.0 + 0.5 * (u / 9.0) ** 2)
        i_ext -= math.copysign(I_VOLTMETER, u) if abs(u) > 1e-3 else 0.0
        if self.insulation:
            i_ext -= u / R_INSUL_WET

        # dielectric absorption branches (only C2 has them)
        if self.sw1 == "C2":
            for k, (f, tau) in enumerate(C2_BRANCH):
                Cb = f * self.c2_total(self.vb[k], self.T_pcb)
                ib = (self.uC - self.vb[k]) * Cb / tau
                i_ext -= ib
                self.vb[k] += ib / Cb * dt
        else:
            for k in range(len(self.vb)):
                self.vb[k] += (self.uC - self.vb[k]) * dt / 0.05

        uT_before, uL_before = self._uT_prev, self._uL_prev
        if clamp is not None:
            self.uC = clamp
            self._duC = 0.0
        else:
            self._duC = i_ext / C
            self.uC += self._duC * dt
            self.uC = max(-12.0, min(12.0, self.uC))
        uT_now = self.ntc_voltage()
        self._duT = (uT_now - uT_before) / dt if uT_before is not None else 0.0
        self._duL = (uL_now - uL_before) / dt if uL_before is not None else 0.0
        self._uT_prev, self._uL_prev = uT_now, uL_now

    # ---------------- STM32 firmware (what the app talks to) ----------------
    def heat_from_app(self, A):
        """Converter.heaterCurrentToDacCode: v = A/2.2 + 0.139 on a 0..0.5 V DAC"""
        v = max(0.0, min(0.5, A / 2.2 + 0.139 if A > 0 else 0.0))
        self.heat_code = 4095 + int(-4095 * (v / 0.5))
        v2 = (4095 - self.heat_code) / 4095.0 * 0.5
        self.iH = min(500.0, (v2 - 0.139) * 2.2 * 1000.0) if v2 > 0.139 else 0.0

    def led_from_app(self, A, pw):
        b = led_code(A)
        self.iL = led_amps(b[0], b[1]) * 1000.0
        self.tL = pw if pw > 0 else 0.0

    def firmware_reset(self):
        self.iH = self.iL = self.tL = 0.0
        self.heat_code, self.clock = 4095, 0.0
        self.reset_pressed_at = self.t

    def frame(self, code, nr):
        """one 30-byte answer of UsbProtocol (code 1 = status, 4 = LED command)"""
        g = self.rng.gauss
        b = bytearray(30)
        b[0], b[1], b[2], b[3] = 27, 30, code, nr & 255
        uL = self.led_state()[0]
        _put(b, 6, _ci((self.ntc_voltage() + 60e-6 * g(0, 1)) / 3.3 * 65535, 0, 65535), 2)
        _put(b, 8, _ci((uL + (100e-6 * g(0, 1) if uL > 0 else 0.0)) / 3.3 * 65535, 0, 65535), 2)
        _put(b, 10, _ci((self.uC + 50e-6 * g(0, 1) + 10.05) / (10.04998 + 10.05) * 16777200, 0, 16777215), 3)
        _put(b, 13, self.heat_code, 2)
        lb = led_code(self.iL / 1000.0)
        b[15], b[16] = lb[0], lb[1]
        _put(b, 17, _ci(self.iH * (1 + 0.002 * g(0, 1)) / 3300.0 * 65535, 0, 65535), 2)
        _put(b, 19, int(self.clock * 100), 4)
        b[25] = 0
        _put(b, 26, binascii.crc32(bytes(b[:26])) & 0xFFFFFFFF, 4)
        return bytes(b)


class Firmware:
    """The board end of the link: requests from the app in, frames out."""

    def __init__(self, sim):
        self.sim = sim
        self.run = None
        self.next = 0.0
        self.out = []
        self.usb = False
        self.reset_until = 0.0
        self.nr = 0
        self.sink = None            # where messages to the app go

    def device_here(self):
        s = self.sim
        if s.mode == "virtual":
            return s.tablet is not None and s.tablet.app_running
        if s.mode == "remote":
            return s.link.alive()
        return False

    def link_on(self):
        b = self.sim.board
        return bool(b.powered and b.data_cable and self.device_here())

    def send(self, m):
        if self.sink:
            self.sink(m)

    def handle(self, m):
        b, t = self.sim.board, m.get("type")
        if t == "hello":
            self.send({"type": "welcome", "lang": LANG.lower(), "attached": self.usb})
        elif t == "bye":
            self.run = None
        elif t == "run":
            if not m.get("on") or not self.link_on():
                self.run = None
                return
            ts = max(0.03, min(1.0, float(m.get("ts") or 0.14)))
            b.timestep = ts
            sw = m.get("sweep")
            self.run = {"ts": ts, "sweep": list(sw) if isinstance(sw, list) else None, "si": 0,
                        "prev": b.iL / 1000.0, "pw": float(m.get("pw") or 0.0)}
            self.next = self.sim.now + 0.5
            if self.run["sweep"] is None and isinstance(m.get("led"), (int, float)) and b.powered:
                b.led_from_app(float(m["led"]), float(m.get("pw") or 0.0))
        elif t == "led":
            if b.powered and self.usb:
                b.led_from_app(float(m.get("A") or 0.0), float(m.get("pw") or 0.0))
        elif t == "heat":
            if b.powered and self.usb:
                b.heat_from_app(float(m.get("A") or 0.0))

    def step(self, now):
        R = self.run
        if R is None:
            return
        if not self.link_on() or not self.usb:
            self.run = None
            return
        if now < self.next:
            return
        self.next += R["ts"]
        if self.next < now:
            self.next = now + R["ts"]
        b = self.sim.board
        if R["sweep"] is not None:
            if R["si"] >= len(R["sweep"]):
                self.run = None
                self.out.append("@done")
                return
            d7 = R["sweep"][R["si"]]
            cross = (d7 > 0.001 and R["prev"] <= 0.001) or (d7 <= 0.001 and R["prev"] > 0.001)
            b.led_from_app(d7, R["pw"])
            R["prev"] = d7
            if cross:                     # the app ignores this answer and asks again
                return
            R["si"] += 1
            self.out.append(b.frame(4, self.nr))
        else:
            self.out.append(b.frame(1, self.nr))
        self.nr += 1

    def reset(self):
        self.sim.board.firmware_reset()
        self.run = None
        if self.usb:
            self.usb = False
            self.send({"type": "detach"})
        self.reset_until = time.time() + 0.9

    def flush(self):
        on = self.link_on() and time.time() >= self.reset_until
        if on != self.usb:
            self.usb = on
            if not on:
                self.run = None
            self.send({"type": "attach" if on else "detach"})
        if self.out:
            fr = [x for x in self.out if x != "@done"]
            if fr:
                self.send({"type": "frames", "list": fr})
            if len(fr) != len(self.out):
                self.send({"type": "done"})
            self.out = []


# ============================================================================
#            THE APP'S OWN CODE  (Calc, exp4j, Measurement, Database)
# ============================================================================
VARS = ["uC", "uT", "uL", "duC", "duT", "duL", "iL", "iH", "t"]
LAST = "Last measurement"


def jE(v, d):
    if v != v:
        return "NaN"
    if v in (float("inf"), float("-inf")):
        return "Infinity" if v > 0 else "-Infinity"
    return ("%." + str(d) + "e") % v


def jF(v, d):
    if v != v:
        return "NaN"
    if v in (float("inf"), float("-inf")):
        return "Infinity" if v > 0 else "-Infinity"
    return ("%." + str(d) + "f") % v


def jD(v):
    """Java's Double.toString"""
    if v != v:
        return "NaN"
    if v == 0:
        return "0.0"
    a = abs(v)
    if 1e-3 <= a < 1e7:
        s = repr(float(v))
        if "e" in s:
            s = ("%.12f" % v).rstrip("0")
        if "." not in s:
            s += ".0"
        if s.endswith("."):
            s += "0"
        return s
    m, e = ("%r" % float(v)).split("e") if "e" in repr(float(v)) else (repr(float(v)), "0")
    if "e" not in repr(float(v)):
        m, e = ("%e" % v).split("e")
        m = m.rstrip("0")
    if "." not in m:
        m += ".0"
    if m.endswith("."):
        m += "0"
    return m + "E" + str(int(e))


def jround(x):
    return math.floor(x + 0.5)


def round_digits(d, i):
    return jround(d * 10.0 ** i) / 10.0 ** i


def prec_digits(d):
    for lim, n in ((10, 0), (1, 1), (0.1, 2), (0.01, 3), (0.001, 4), (1e-4, 5), (1e-5, 6)):
        if d > lim:
            return n
    return 7


def nf(v, minf):
    """NumberFormat.getNumberInstance(Locale.US) with minimum fraction digits"""
    if v != v or v in (float("inf"), float("-inf")):
        return str(v)
    maxf = max(3, minf)
    s = "{:,.{}f}".format(v, maxf)
    if maxf > minf:
        ip, fp = s.split(".")
        fp = fp.rstrip("0")
        if len(fp) < minf:
            fp += "0" * (minf - len(fp))
        s = ip + ("." + fp if fp else "")
    return s


def round_to_led(A):
    b = led_code(A)
    return led_amps(b[0], b[1])


def get_sweep_array(d, d2, n, geo, rnd):
    a = [0.0] * n
    a[0] = d
    a[n - 1] = d2
    if geo:
        if d == 0:
            a[1] = 1e-5
            p = (d2 / a[1]) ** (1.0 / (n - 2))
            i2 = 1
        else:
            p = (d2 / d) ** (1.0 / (n - 1))
            i2 = 0
        for i in range(i2 + 1, n - 1):
            a[i] = a[i - 1] * p
    else:
        for i in range(1, n - 1):
            a[i] = (i * (d2 - d)) / (n - 1) + d
    if rnd:
        a = [round_to_led(x) for x in a]
    return a


def _d3(y, t, i):
    d = t[i + 1] - t[i]
    d2 = t[i] - t[i - 1]
    return ((y[i + 1] - y[i]) * d2 * d2 + (y[i] - y[i - 1]) * d * d) / (d2 * d * (d2 + d))


def _dlive(y, t, i, edge):
    try:
        if edge == 0:
            return _d3(y, t, i)
        if edge == 1:
            return (y[i] - y[i - 1]) / (t[i] - t[i - 1])
        return (y[i + 1] - y[i]) / (t[i + 1] - t[i])
    except ZeroDivisionError:
        return float("nan")


def get_var_names(s):
    out = []
    for v in VARS:
        i = s.find(v)
        while i != -1:
            if i == 0 or s[i - 1] != "d":
                out.append(v)
                i = -1
            else:
                i = s.find(v, i + 1)
    return out


def _cot(x):
    return 1.0 / math.tan(x)


def _sgn(x):
    return (x > 0) - (x < 0)


EXP4J_FN = {"sin": math.sin, "cos": math.cos, "tan": math.tan, "cot": _cot, "ln": math.log, "log1p": math.log1p,
            "abs": abs, "acos": math.acos, "asin": math.asin, "atan": math.atan, "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3.0), x),
            "ceil": math.ceil, "floor": math.floor, "sinh": math.sinh, "sqrt": math.sqrt, "tanh": math.tanh,
            "cosh": math.cosh, "exp": math.exp, "expm1": math.expm1, "log10": math.log10, "log2": math.log2, "signum": _sgn}
EXP4J_CONST = {"pi": math.pi, "π": math.pi, "e": math.e, "φ": 1.61803398874}


class _DivZero(Exception):
    pass


def _div(a, b):
    if b == 0:
        raise _DivZero()
    return a / b


def _mod(a, b):
    if b == 0:
        raise _DivZero()
    return math.fmod(a, b)


EXP4J_OPS = {"+": (500, True, lambda a, b: a + b), "-": (500, True, lambda a, b: a - b),
             "*": (1000, True, lambda a, b: a * b), "/": (1000, True, _div), "%": (1000, True, _mod),
             "^": (10000, False, lambda a, b: math.pow(a, b))}
_NUM_RE = None


def exp4j_compile(src, variables):
    """exp4j's tokenizer and shunting-yard (implicit multiplication, unary minus)"""
    import re
    global _NUM_RE
    if _NUM_RE is None:
        _NUM_RE = re.compile(r"^(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")
    names = set(variables) | set(EXP4J_CONST)
    toks = []
    i = 0

    def implicit():
        if toks and toks[-1][0] in ("num", "var", ")"):
            toks.append(("op", "*", 2))
    while i < len(src):
        c = src[i]
        if c in " \t":
            i += 1
            continue
        if c.isdigit() or c == ".":
            j, last_e = i, False
            while j < len(src) and (src[j].isdigit() or src[j] in ".eE" or (last_e and src[j] in "+-")):
                last_e = src[j] in "eE"
                j += 1
            s = src[i:j]
            if not _NUM_RE.match(s):
                raise ValueError("bad number")
            implicit()
            toks.append(("num", float(s)))
            i = j
            continue
        if c.isalpha() or c == "_" or ord(c) > 127:
            j = i
            while j < len(src) and (src[j].isalnum() or src[j] in "_." or ord(src[j]) > 127):
                j += 1
            best, bl = None, 0
            for L in range(1, j - i + 1):
                nm = src[i:i + L]
                if nm in names:
                    best, bl = ("var", nm), L
                elif nm in EXP4J_FN:
                    best, bl = ("fn", nm), L
            if best is None:
                raise ValueError("unknown function or variable")
            implicit()
            toks.append(best)
            i += bl
            continue
        if c == "(":
            implicit()
            toks.append(("(",))
            i += 1
            continue
        if c == ")":
            toks.append((")",))
            i += 1
            continue
        if c == ",":
            toks.append((",",))
            i += 1
            continue
        if c in "+-*/^%":
            l = toks[-1] if toks else None
            unary = c in "+-" and (l is None or l[0] in ("op", "(", ","))
            toks.append(("op", "neg" if c == "-" else "pos", 1) if unary else ("op", c, 2))
            i += 1
            continue
        raise ValueError("bad character")
    out, st = [], []

    def prec(t):
        return 5000 if t[2] == 1 else EXP4J_OPS[t[1]][0]

    def left(t):
        return False if t[2] == 1 else EXP4J_OPS[t[1]][1]
    for t in toks:
        k = t[0]
        if k in ("num", "var"):
            out.append(t)
        elif k == "fn":
            st.append(t)
        elif k == ",":
            while st and st[-1][0] != "(":
                out.append(st.pop())
        elif k == "op":
            while st and st[-1][0] == "op":
                o2 = st[-1]
                if t[2] == 1 and o2[2] == 2:
                    break
                if (left(t) and prec(t) <= prec(o2)) or prec(t) < prec(o2):
                    out.append(st.pop())
                else:
                    break
            st.append(t)
        elif k == "(":
            st.append(t)
        elif k == ")":
            while st and st[-1][0] != "(":
                out.append(st.pop())
            if not st:
                raise ValueError("mismatched parentheses")
            st.pop()
            if st and st[-1][0] == "fn":
                out.append(st.pop())
    while st:
        t = st.pop()
        if t[0] == "(":
            raise ValueError("mismatched parentheses")
        out.append(t)
    depth = 0
    for t in out:
        if t[0] in ("num", "var"):
            depth += 1
        elif t[0] == "fn":
            if depth < 1:
                raise ValueError("invalid")
        else:
            if depth < t[2]:
                raise ValueError("invalid")
            depth -= t[2] - 1
    if depth != 1:
        raise ValueError("invalid")

    def run(env):
        s = []
        for t in out:
            k = t[0]
            if k == "num":
                s.append(t[1])
            elif k == "var":
                s.append(env.get(t[1], EXP4J_CONST.get(t[1], 0.0)))
            elif k == "fn":
                try:
                    s.append(float(EXP4J_FN[t[1]](s.pop())))
                except (ValueError, OverflowError):
                    s.append(float("nan"))
            elif t[2] == 1:
                a = s.pop()
                s.append(-a if t[1] == "neg" else a)
            else:
                bb = s.pop()
                a = s.pop()
                try:
                    s.append(EXP4J_OPS[t[1]][2](a, bb))
                except (ValueError, OverflowError):
                    s.append(float("nan"))
        return s[0]
    return run


def exp4j_valid(src):
    try:
        exp4j_compile(src, get_var_names(src))
        return True
    except Exception:
        return False


class Calc:
    def __init__(self, s, m):
        self.s = s
        self.vars = get_var_names(s)
        try:
            self.f = exp4j_compile(s, self.vars)
        except Exception:
            self.f = None
        self.arr = [m.part(v) for v in self.vars]

    def at(self, i):
        if self.f is None:
            return float("nan")
        env = {}
        for v, a in zip(self.vars, self.arr):
            env[v] = a[i] if i < len(a) else 0.0
        try:
            return float(self.f(env))
        except _DivZero:
            return 1e12
        except Exception:
            return float("nan")


class AppDB:
    """Database.java: titles, equations, measurements (17 bytes per sample) and preferences"""

    def __init__(self):
        self.path = os.path.join(os.path.expanduser("~"), ".haslalab", "ipho2021_app.json")
        self.d = {"titles": [], "eq": [], "m": {}, "prefs": {}}
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                o = json.load(fh)
            if isinstance(o, dict) and "titles" in o:
                self.d.update(o)
        except Exception:
            pass

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self.d, fh)
        except Exception:
            pass

    def clear(self):
        self.d = {"titles": [], "eq": [], "m": {}, "prefs": {}}
        self.save()

    # PreferenceWrapper
    def pstr(self, k, d):
        return str(self.d["prefs"][k]) if k in self.d["prefs"] else d

    def pint(self, k, d):
        s = self.pstr(k, "")
        try:
            return int(s)
        except ValueError:
            return d

    def pdbl(self, k, d):
        s = self.pstr(k, "")
        try:
            return float(s)
        except ValueError:
            return d

    def pbool(self, k, d):
        return bool(self.d["prefs"][k]) if k in self.d["prefs"] else d

    def pset(self, k, v):
        self.d["prefs"][k] = v
        self.save()


class Measurement:
    def __init__(self, name="NEW"):
        self.name = name
        self.exprs, self.calcs, self.evals = [], [], []
        self.reset()

    def reset(self):
        for v in VARS:
            setattr(self, v, [])
        self.dump = []
        self.n = self.nc = 0
        self.start = -1
        self.loaded = False
        self.st = [0, 0, 0]          # last timestamp, last interval, counter-reset correction

    def add_expr(self, s):
        if s is None or s in self.exprs or s in VARS:
            return False
        self.exprs.append(s)
        self.calcs.append(Calc(s, self))
        self.evals.append([])
        return True

    def part(self, s):
        if s in VARS:
            return getattr(self, s)
        if s in self.exprs:
            return self.evals[self.exprs.index(s)]
        return None

    def setup_axes(self, x, y):
        self.add_expr(x)
        self.add_expr(y)
        self.xr, self.yr = self.part(x), self.part(y)

    def start_measurement(self):
        self.start = -1
        self.n = self.nc = 0
        self.dump = []
        for v in VARS:                 # in place: the chart keeps references to these
            del getattr(self, v)[:]
        for e in self.evals:
            del e[:]

    def stop_measurement(self):
        self.upd()
        self.start = -1
        self.st = [0, 0, 0]

    @staticmethod
    def _set(arr, i, v):
        if i < len(arr):
            arr[i] = v
        else:
            arr.append(v)

    def add(self, b):
        if b[25] != 0:
            return False
        if not self.loaded:
            self.dump.append(bytes(b[6:23]))
        ts = _u32(b, 19) * 10
        S = self.st
        if ts == S[0]:
            return False
        if ts < S[0]:
            S[2] = (S[0] + S[1]) - ts
        if self.start == -1:
            self.start = ts
        i = self.n
        st = self._set
        st(self.t, i, ((ts - self.start) + S[2]) / 1000.0)
        st(self.uC, i, _conv(_u24(b, 10), 0, 16777200, -10.05, 10.04998))
        st(self.uL, i, _conv(_u16(b, 8), 0, 65535, 0.0, 3.3))
        st(self.uT, i, _conv(_u16(b, 6), 0, 65535, 0.0, 3.3))
        st(self.iH, i, round_digits(_conv(_u16(b, 17), 0, 65535, 0.0, 3.3) * 1000.0, -1))
        st(self.iL, i, led_amps(b[15], b[16]) * 1000.0)
        if S[0] != 0:
            S[1] = ts - S[0]
        S[0] = ts
        self.n += 1
        return True

    def push(self, b, led_set):
        b = bytearray(b)
        lb = led_code(led_set)
        b[15], b[16] = lb[0], lb[1]
        if self.add(b):
            self.upd()

    def upd(self):
        n = self.n
        if n < 2:
            return
        c = self.nc
        if c == n:
            return
        edge = -1 if c == 0 else (0 if c < n - 1 else 1)
        self._set(self.duC, c, _dlive(self.uC, self.t, c, edge))
        self._set(self.duT, c, _dlive(self.uT, self.t, c, edge))
        self._set(self.duL, c, _dlive(self.uL, self.t, c, edge))
        for k, cl in enumerate(self.calcs):
            self._set(self.evals[k], c, cl.at(c))
        self.nc += 1

    def calc_all(self):
        self.nc = 0
        for _ in range(self.n):
            self.upd()

    def last(self, arr):
        if self.nc == 0 or arr is None or self.nc - 1 >= len(arr):
            return float("nan")
        return arr[self.nc - 1]

    def save(self, db, title=None):
        name = title or self.name
        self.name = name
        if name not in db.d["titles"]:
            db.d["titles"].append(name)
        raw = b"".join(self.dump[:self.n])
        db.d["m"][name] = {"p": "\n".join([name, "0.1", str(self.n), str(self.start)]),
                           "d": base64.b64encode(raw).decode("ascii")}
        db.save()

    @staticmethod
    def load(db, name):
        m = Measurement(name)
        m.loaded = True
        rec = db.d["m"].get(name)
        if not rec:
            return m
        p = rec["p"].split("\n")
        m.name = p[0]
        total = int(p[2]) if p[2].lstrip("-").isdigit() else 0
        m.start = int(p[3]) if p[3].lstrip("-").isdigit() else -1
        d = base64.b64decode(rec["d"])
        fr = bytearray(30)
        for i in range(total):
            fr[6:23] = d[i * 17:i * 17 + 17]
            fr[25] = 0
            m.add(fr)
        return m


def filter_lab(lst, lab):
    a = list(lst)
    rm = {"LAB 1": ("uL", "duL", "iL"), "LAB 2": ("uC", "duC")}.get(lab, ())
    for x in rm:
        if x in a:
            a.remove(x)
    return a


# ============================================================================
#      THE EXAMINATION TABLET  (8-inch 1280 x 800, Android 9) AND ITS APP
# ============================================================================
SAND, DSAND, TABLE_BG, ACC = "#ccaaaa", "#998888", "#ddccbb", "#ee6655"
DIM = "#514444"
COLORS = ["#444444", "#ff0000", "#00ff00", "#0000ff", "#000000", "#00ffff", "#ff00ff"]
PREFS = [
    dict(k="lab", t="Show controls for", type="list", d="ANY LAB", items=["LAB 1", "LAB 2", "ANY LAB"]),
    dict(k="time_step_of_measurement_ms", t="Time step of measurement", type="num", d="140", mn=30, unit="ms"),
    dict(k="turn_off_LED_on_measurement_end", t="Turn off LED current when measurement is done.", type="sw", d=True),
    dict(k="turn_off_heating_on_measurement_end", t="Turn off heating current when measurement is done.", type="sw", d=False),
    dict(k="sweep_measurement", t="Sweep measurement", s="This setting will enable measuring I-V curve, by increasing current and measuring resulting voltage automatically in sweep mode.", type="sw", d=False, dep="lab"),
    dict(cat="Sweep measurement settings"),
    dict(k="min_sweep_led_current_mA", t="Minimum sweep measurement current", type="num", d="0.1", mn=0, mx=49.5, unit="mA", incat=True),
    dict(k="max_sweep_led_current_mA", t="Maximum sweep measurement current", type="num", d="50", mn=0.5, mx=50, unit="mA", incat=True),
    dict(k="sweep_measurement_points_number", t="Number of steps of sweep measurement", type="num", isint=True, d="51", mn=3, mx=500, incat=True),
    dict(k="sweep_geometric_current_increase", t="Increase current exponentially", type="sw", d=False, incat=True),
    dict(k="pulsed_current", t="Set pulsed current", type="sw", d=False, incat=True),
    dict(k="led_current_pulse_durations_ms", t="Current pulse duration", type="num", d=None, mn=0.1, mx=25.5, unit="ms", incat=True, dep2="pulsed_current"),
    dict(cat="Performance settings"),
    dict(k="replot_each_n_timesteps", t="Replot every … measurement timesteps", type="num", isint=True, d="5", mn=1)]
EQ_KEYS = [("sin", 18, 20, 74, 42), ("cos", 101, 20, 74, 42), ("tan", 184, 20, 74, 42), ("exp", 267, 20, 74, 42), ("()", 420, 20, 50, 42),
           ("asin", 18, 73, 74, 42), ("acos", 101, 73, 74, 42), ("atan", 184, 73, 74, 42), ("ln", 267, 73, 74, 42), ("del", 361, 73, 50, 42), ("bsp", 420, 73, 50, 42),
           ("uC", 18, 272, 69, 42), ("uL", 95, 272, 69, 42), ("uT", 172, 272, 69, 42),
           ("duC", 18, 323, 69, 42), ("duL", 95, 323, 69, 42), ("duT", 172, 323, 69, 42),
           ("iL", 95, 374, 69, 42), ("iH", 172, 374, 69, 42), ("t", 251, 374, 69, 42),
           ("1", 359, 262, 41, 42), ("2", 407, 262, 41, 42), ("3", 455, 262, 41, 42), ("e", 503, 262, 41, 42),
           ("4", 359, 313, 41, 42), ("5", 407, 313, 41, 42), ("6", 455, 313, 41, 42), (".", 503, 313, 41, 42),
           ("7", 359, 364, 41, 42), ("8", 407, 364, 41, 42), ("9", 455, 364, 41, 42), ("0", 503, 364, 41, 42),
           ("+", 359, 420, 41, 42), ("-", 407, 420, 41, 42), ("*", 455, 420, 41, 42), ("/", 503, 420, 41, 42), ("^", 551, 420, 41, 42)]
EQ_FN = ("sin", "cos", "tan", "exp", "asin", "acos", "atan", "ln")


class Tablet(tk.Toplevel):
    """The examination tablet with the IPhO app (MainActivity, SettingsActivity,
    EquationEditorActivity), drawn in dp at the tablet's 960 x 600 dp."""

    def __init__(self, master, sim):
        super().__init__(master)
        self.sim = sim
        self.title("IPhO  —  " + T("tablet") + " (8\" 1280×800, Android 9)")
        self.configure(bg="#000")
        self.protocol("WM_DELETE_WINDOW", self.home)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.S = max(0.7, min(1.25, (sw - 60) / 960.0, (sh - 110) / 600.0))
        self.Sp = max(0.5, min(1.0, (sh - 110) / 960.0))
        fam = "Helvetica"
        try:
            import tkinter.font as tkf
            fams = set(tkf.families(self))
            for f in ("Roboto", "Segoe UI", "Noto Sans", "DejaVu Sans", "Helvetica", "Arial"):
                if f in fams:
                    fam = f
                    break
        except Exception:
            pass
        self.fam = fam
        self.db = AppDB()
        self.app_running = False
        self.act = "main"
        self.st = dict(connected=False, auto=False, prog=False, sweep=False, skip=0, last_reset=-1e9, heat=0.0,
                       led=0.0, pw=0.0, last_led=0.0, usb_default=False, attached=False, last_back=0.0,
                       thread=None, no_usb_shown=False)
        self.meas = Measurement()
        self.toasts, self.toast_busy = [], False
        self.dlg = None
        self._build_all()
        self.launch()

    # ------------------------------------------------------------ geometry
    def px(self, v):
        return int(round(v * self.Sc))

    def font(self, sp, bold=False):
        return (self.fam, -max(6, int(round(sp * self.Sc))), "bold" if bold else "normal")

    def _geom(self, portrait):
        if portrait:
            self.Sc = self.Sp
            w, h = int(600 * self.Sc), int(912 * self.Sc)
        else:
            self.Sc = self.S
            w, h = int(960 * self.Sc), int(552 * self.Sc)
        self.geometry("%dx%d" % (w, h + int(48 * self.Sc)))
        return w, h

    def _build_all(self):
        for ch in list(self.winfo_children()):
            ch.destroy()
        portrait = self.act == "eq"
        w, h = self._geom(portrait)
        self.app = tk.Frame(self, bg=SAND, width=w, height=h)
        self.app.place(x=0, y=0, width=w, height=h)
        nav = tk.Canvas(self, bg="#000", highlightthickness=0, width=w, height=self.px(48))
        nav.place(x=0, y=h, width=w, height=self.px(48))
        cy, s = self.px(24), self.Sc
        for i, (kind, fn) in enumerate((("back", self.back), ("home", self.home), ("rec", self.home))):
            cx = int(w * (0.29 + 0.21 * i)) if not portrait else int(w * (0.22 + 0.28 * i))
            if kind == "back":
                tg = nav.create_polygon(cx + 7 * s, cy - 8 * s, cx + 7 * s, cy + 8 * s, cx - 7 * s, cy, fill="#fff")
            elif kind == "home":
                tg = nav.create_oval(cx - 8 * s, cy - 8 * s, cx + 8 * s, cy + 8 * s, fill="#fff", outline="")
            else:
                tg = nav.create_rectangle(cx - 7 * s, cy - 7 * s, cx + 7 * s, cy + 7 * s, fill="#fff", outline="")
            hit = nav.create_rectangle(cx - 24 * s, 0, cx + 24 * s, 48 * s, outline="", fill="")
            for it in (tg, hit):
                nav.tag_bind(it, "<Button-1>", lambda e, f=fn: f())
        self.toast_lbl = None
        if self.act == "main":
            self._build_main()
        elif self.act == "set":
            self._build_settings()
        else:
            self._build_editor()

    # ------------------------------------------------------------ widgets
    def W_label(self, parent, x, y, text, sp=14, fg="#222", bg=SAND):
        l = tk.Label(parent, text=text, font=self.font(sp), fg=fg, bg=bg, bd=0, padx=0, pady=0)
        l.place(x=self.px(x), y=self.px(y))
        return l

    def W_sub(self, x, y, a, b):
        """iH= with a subscript, as Utils.setSupSubScript draws it"""
        c = tk.Canvas(self.app, width=self.px(26), height=self.px(22), bg=SAND, highlightthickness=0)
        c.place(x=self.px(x), y=self.px(y))
        c.create_text(self.px(1), self.px(13), text=a, anchor="w", font=self.font(14))
        c.create_text(self.px(6), self.px(17), text=b, anchor="w", font=self.font(9))
        c.create_text(self.px(14), self.px(13), text="=", anchor="w", font=self.font(14))
        return c

    def W_button(self, parent, x, y, w, h, text, cmd, sp=16, caps=False):
        l = tk.Label(parent, text=text.upper() if caps else text, font=self.font(14 if caps else sp, caps),
                     bg=DSAND, fg="#222", bd=0, cursor="hand2")
        l.place(x=self.px(x), y=self.px(y), width=self.px(w), height=self.px(h))
        l.bind("<Button-1>", lambda e: cmd())
        return l

    def W_icon(self, parent, x, y, kind, cmd, size=40, bg=DSAND):
        c = tk.Canvas(parent, width=self.px(size), height=self.px(size), bg=bg, highlightthickness=0, cursor="hand2")
        c.place(x=self.px(x), y=self.px(y))
        k, m = self.Sc * size / 40.0, self.px(size) / 2.0

        def P(pts):
            return [m + (p - 20) * k for p in pts]
        if kind == "add":
            c.create_polygon(*P([17, 8, 23, 8, 23, 17, 32, 17, 32, 23, 23, 23, 23, 32, 17, 32, 17, 23, 8, 23, 8, 17, 17, 17]), fill="#86c440")
        elif kind == "del":
            c.create_line(*P([11, 11, 29, 29]), fill="#e8175d", width=max(2, 5 * k))
            c.create_line(*P([29, 11, 11, 29]), fill="#e8175d", width=max(2, 5 * k))
        elif kind == "replot":
            c.create_arc(*P([10, 10, 30, 30]), start=30, extent=150, style="arc", outline="#cfcfcf", width=max(1, 2.5 * k))
            c.create_arc(*P([10, 10, 30, 30]), start=210, extent=150, style="arc", outline="#cfcfcf", width=max(1, 2.5 * k))
        elif kind == "set":
            c.create_line(*P([12, 28, 24, 16]), fill="#5f5f5f", width=max(2, 3 * k))
            c.create_oval(*P([22, 9, 31, 18]), outline="#5f5f5f", width=max(1, 2 * k))
        elif kind == "info":
            c.create_oval(*P([9, 9, 31, 31]), outline="#5f5f5f", width=max(1, 2 * k))
            c.create_text(m, m, text="i", font=self.font(15 * size / 40.0, True), fill="#5f5f5f")
        elif kind == "edit":
            c.create_line(*P([12, 28, 27, 13]), fill="#f5f5f5", width=max(2, 3 * k))
        c.bind("<Button-1>", lambda e: cmd())
        return c

    def W_entry(self, parent, x, y, w, hint, sp=12, bg=SAND):
        f = tk.Frame(parent, bg=bg)
        f.place(x=self.px(x), y=self.px(y), width=self.px(w), height=self.px(30))
        e = tk.Entry(f, font=self.font(sp), relief="flat", bd=0, bg=bg, highlightthickness=0, fg="#222", insertbackground="#222")
        e.place(x=0, y=self.px(6), width=self.px(w), height=self.px(sp * 1.5))
        line = tk.Frame(f, bg="#666")
        line.place(x=0, y=self.px(27), width=self.px(w), height=1)
        e._hint, e._line, e._ph = hint, line, False

        def show_hint(*_):
            if not e.get() and e.focus_get() is not e:
                e._ph = True
                e.insert(0, hint)
                e.config(fg="#8f7676")

        def focus_in(_):
            if e._ph:
                e.delete(0, "end")
                e.config(fg="#222")
                e._ph = False
            line.config(bg=ACC)
            line.place_configure(height=2)

        def focus_out(_):
            line.config(bg="#666")
            line.place_configure(height=1)
            show_hint()
        e.bind("<FocusIn>", focus_in)
        e.bind("<FocusOut>", focus_out)
        show_hint()
        return e

    @staticmethod
    def val(e):
        return "" if getattr(e, "_ph", False) else e.get()

    def setval(self, e, s):
        if getattr(e, "_ph", False):
            e.delete(0, "end")
            e.config(fg="#222")
            e._ph = False
        e.delete(0, "end")
        e.insert(0, s)
        if s == "" and e.focus_get() is not e:
            e._ph = True
            e.insert(0, e._hint)
            e.config(fg="#8f7676")

    def W_switch(self, parent, x, y, text, cmd, sp=16, bg=SAND):
        c = tk.Canvas(parent, bg=bg, highlightthickness=0, cursor="hand2")
        tw = len(text) * sp * 0.52
        c.place(x=self.px(x), y=self.px(y), width=self.px(tw + 52), height=self.px(32))
        c._on = False
        c._tw = tw

        def draw():
            c.delete("all")
            k = self.Sc
            if text:
                c.create_text(0, self.px(16), text=text, anchor="w", font=self.font(sp))
            x0 = (tw + 9) * k
            c.create_rectangle(x0, 9 * k, x0 + 36 * k, 23 * k, fill="#f2a093" if c._on else "#8d7a7a", outline="")
            cx = x0 + (29 if c._on else 7) * k
            c.create_oval(cx - 10 * k, 6 * k, cx + 10 * k, 26 * k, fill=ACC if c._on else "#ececec", outline="#9a8a8a")
        c.draw = draw
        c.bind("<Button-1>", lambda e: cmd())
        draw()
        return c

    def W_seek(self, x, y, w, on_change, on_start=None, on_stop=None):
        c = tk.Canvas(self.app, bg=SAND, highlightthickness=0, cursor="hand2")
        c.place(x=self.px(x), y=self.px(y), width=self.px(w), height=self.px(32))
        c._p, c._off = 0, False

        def draw():
            c.delete("all")
            k = self.Sc
            x0, x1 = 16 * k, (w - 16) * k
            xx = x0 + (x1 - x0) * c._p / 100.0
            c.create_line(x0, 16 * k, x1, 16 * k, fill="#b39a9a" if not c._off else "#c4b0b0", width=max(1, 2 * k))
            c.create_line(x0, 16 * k, xx, 16 * k, fill=ACC if not c._off else "#dcb4ad", width=max(1, 2 * k))
            c.create_oval(xx - 6 * k, 10 * k, xx + 6 * k, 22 * k, fill=ACC if not c._off else "#dcb4ad", outline="")

        def setp(p, user):
            p = max(0, min(100, int(round(p))))
            ch = p != c._p
            c._p = p
            draw()
            if ch and user:
                on_change(p)

        def pos(e):
            return (e.x / self.Sc - 16) / (w - 32) * 100.0

        def press(e):
            if c._off:
                return
            if on_start:
                on_start()
            setp(pos(e), True)

        def release(e):
            if c._off:
                return
            if on_stop:
                on_stop()
        c.bind("<ButtonPress-1>", press)
        c.bind("<B1-Motion>", lambda e: None if c._off else setp(pos(e), True))
        c.bind("<ButtonRelease-1>", release)
        c.setp, c.draw = setp, draw
        draw()
        return c

    # ------------------------------------------------------------ toasts
    def toast(self, s, long=False, big=False):
        self.toasts.append((s, long, big))
        if not self.toast_busy:
            self._next_toast()

    def _next_toast(self):
        if not self.toasts:
            self.toast_busy = False
            return
        self.toast_busy = True
        s, long, big = self.toasts.pop(0)
        try:
            l = tk.Label(self, text=s, bg="#323232", fg="#fff", font=self.font(32 if big else 14), padx=self.px(18), pady=self.px(10),
                         justify="center", wraplength=self.px(700))
            l.place(relx=0.5, rely=1.0, y=-self.px(118), anchor="s")
            l.lift()
        except tk.TclError:
            l = None
        self.after(3500 if long else 2000, lambda: (l and l.destroy(), self._next_toast()))

    # ------------------------------------------------------------ dialogs
    def dialog(self, title=None, items=None, multi=False, selected=(), on_select=None, on_cancel=None,
               msg=None, entry=None, check=None, ok="Select", cancel="Cancel", small=False):
        self.close_dialog()
        ov = tk.Frame(self, bg=DIM)
        ov.place(x=0, y=0, relwidth=1, relheight=1)
        self.dlg = ov
        bw = self.px(520 if small else 644)
        box = tk.Frame(ov, bg="#fff")
        box.place(relx=0.5, rely=0.5, anchor="center", width=bw, height=None if small else self.px(516))
        sel = [x for x in selected if items and x in items]
        if items and not multi and not sel:
            sel = [items[0]]
        if title:
            tk.Label(box, text=title, bg="#fff", font=self.font(20, True), anchor="w").pack(fill="x", padx=self.px(24), pady=(self.px(20), 0))
        if msg:
            tk.Label(box, text=msg, bg="#fff", fg="#666", font=self.font(16), anchor="w", justify="left",
                     wraplength=bw - self.px(48)).pack(fill="x", padx=self.px(24), pady=(self.px(14), 0))
        ent = None
        if entry is not None:
            ent = tk.Entry(box, font=self.font(18), relief="flat", bg="#fff", highlightthickness=2, highlightcolor=ACC, highlightbackground=ACC)
            ent.insert(0, entry)
            ent.pack(fill="x", padx=self.px(24), pady=(self.px(12), 0))
            ent.focus_set()
        chk = {"v": False}
        if check:
            cb = tk.Label(box, text="☐  " + check, bg="#fff", font=self.font(14), anchor="w", cursor="hand2")
            cb.pack(fill="x", padx=self.px(24), pady=(self.px(14), 0))

            def tog(_):
                chk["v"] = not chk["v"]
                cb.config(text=("☑  " if chk["v"] else "☐  ") + check)
            cb.bind("<Button-1>", tog)
        rows = []
        if items:
            holder = tk.Frame(box, bg="#fff")
            holder.pack(fill="both", expand=True, pady=self.px(6))
            cv = tk.Canvas(holder, bg="#fff", highlightthickness=0)
            sb = tk.Scrollbar(holder, orient="vertical", command=cv.yview)
            inner = tk.Frame(cv, bg="#fff")
            cv.create_window(0, 0, window=inner, anchor="nw")
            cv.configure(yscrollcommand=sb.set)
            cv.pack(side="left", fill="both", expand=True)
            if len(items) > 7:
                sb.pack(side="right", fill="y")

            def redraw():
                for (it, lb) in rows:
                    on = it in sel
                    mark = ("☑" if on else "☐") if multi else ("◉" if on else "○")
                    lb.config(text=mark + "    " + it, fg="#222")
            for it in items:
                lb = tk.Label(inner, text=it, bg="#fff", font=self.font(16), anchor="w", cursor="hand2", height=1)
                lb.pack(fill="x", padx=self.px(24), pady=self.px(10))

                def click(_, it=it):
                    if multi:
                        if it in sel:
                            sel.remove(it)
                        else:
                            sel.append(it)
                    else:
                        del sel[:]
                        sel.append(it)
                    redraw()
                lb.bind("<Button-1>", click)
                rows.append((it, lb))
            redraw()
            inner.update_idletasks()
            cv.configure(scrollregion=cv.bbox("all"), width=bw - self.px(20))
        bar = tk.Frame(box, bg="#fff")
        bar.pack(fill="x", side="bottom", pady=self.px(8))

        def do_ok(_=None):
            self.close_dialog()
            if on_select:
                if items is not None:
                    on_select([x for x in items if x in sel])
                else:
                    on_select(ent.get() if ent else None, chk["v"])

        def do_cancel(_=None):
            self.close_dialog()
            if on_cancel:
                on_cancel()
        for txt, f in ((ok, do_ok), (cancel, do_cancel)):
            b = tk.Label(bar, text=txt.upper(), bg="#fff", fg=ACC, font=self.font(14, True), cursor="hand2", padx=self.px(8), pady=self.px(8))
            b.pack(side="right", padx=self.px(4))
            b.bind("<Button-1>", f)
        if ent:
            ent.bind("<Return>", do_ok)
        ov.bind("<Button-1>", lambda e: do_cancel() if e.widget is ov else None)

    def close_dialog(self):
        if self.dlg is not None:
            try:
                self.dlg.destroy()
            except tk.TclError:
                pass
            self.dlg = None

    # ------------------------------------------------------------ MainActivity
    def _build_main(self):
        a = self.app
        self.sw_meas = self.W_switch(a, 8, 13, "Measure", self.on_measure)
        self.sw_check = self.W_switch(a, 8, 61, "Check state", self.on_check)
        self.e_title = self.W_entry(a, 126, 13, 100, "Measurement title")
        self.e_title.bind("<KeyRelease>", lambda e: None)
        self.W_icon(a, 234, 8, "add", self.on_add)
        self.W_icon(a, 282, 8, "del", self.on_del)
        self.W_button(a, 330, 6, 128, 40, "✎ measurements", self.on_meas_list)
        self.W_icon(a, 8, 101, "set", self.open_settings)
        self.W_icon(a, 56, 101, "info", self.on_info)
        self.W_button(a, 8, 149, 88, 40, "✎ f(x)", self.open_editor)
        self.lb_ih = self.W_sub(153, 69, "i", "H")
        self.e_ih = self.W_entry(a, 180, 63, 54, "0..500")
        self.W_label(a, 236, 70, "mA")
        self.sb_ih = self.W_seek(266, 64, 214, self.on_ih_seek, lambda: self._flag("ch_heat", True), lambda: self._flag("ch_heat", False))
        self.lb_il = self.W_sub(153, 106, "i", "L")
        self.e_il = self.W_entry(a, 180, 100, 54, "0..50")
        self.un_il = self.W_label(a, 236, 107, "mA")
        self.sb_il = self.W_seek(266, 101, 214, self.on_il_seek, lambda: self._flag("ch_led", True), self._il_stop)
        self.lb_tl = self.W_sub(153, 143, "t", "L")
        self.e_tl = self.W_entry(a, 180, 137, 54, "0.1..25.5")
        self.un_tl = self.W_label(a, 236, 144, "ms")
        self.sb_tl = self.W_seek(266, 138, 214, self.on_tl_seek, lambda: self._flag("ch_pw", True), self._tl_stop)
        self.bt_apply = self.W_button(a, 270, 96, 92, 40, "Apply", self.on_apply, caps=True)
        self.bt_cancel = self.W_button(a, 374, 96, 100, 40, "Cancel", self.on_cancel_heat, caps=True)
        self.bt_apply.place_forget()
        self.bt_cancel.place_forget()
        self.ch_heat = self.ch_led = self.ch_pw = False
        self.last_heat = (0, "0")
        self.e_ih.bind("<KeyRelease>", lambda e: self.show_apply())
        self.e_il.bind("<KeyRelease>", lambda e: self.update_led())
        self.e_tl.bind("<KeyRelease>", lambda e: self.update_led())
        # the table
        tf = tk.Frame(a, bg=TABLE_BG)
        tf.place(x=0, y=self.px(192), width=self.px(480), height=self.px(360))
        self.tcv = tk.Canvas(tf, bg=TABLE_BG, highlightthickness=0)
        tsb = tk.Scrollbar(tf, orient="vertical", command=self.tcv.yview)
        self.tcv.configure(yscrollcommand=lambda a1, a2: (tsb.set(a1, a2), self._tbl_scrolled(a1, a2)))
        tsb.pack(side="right", fill="y")
        self.tcv.pack(side="left", fill="both", expand=True)
        self.tcv.bind("<MouseWheel>", lambda e: self.tcv.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), "units"))
        self.tcv.bind("<Button-4>", lambda e: self.tcv.yview_scroll(-1, "units"))
        self.tcv.bind("<Button-5>", lambda e: self.tcv.yview_scroll(1, "units"))
        self.hb = []
        for i in range(3):
            b = tk.Label(self.tcv, text="f(x)", font=self.font(16), bg=DSAND, fg="#222", cursor="hand2")
            self.tcv.create_window(self.px(8 + 96 * i), 0, window=b, anchor="nw", width=self.px(88), height=self.px(40), tags="c%d" % i)
            b.bind("<Button-1>", lambda e, b=b: self.on_header(b))
            self.hb.append(b)
        self.tbl = dict(exprs=[], src=None, parts=[], filled=0, live=False, last_scroll=0.0)
        self.tbl_font = tkfont.Font(self, font=self.font(18))
        self.tbl_cw = [self.px(88)] * 3      # an HTML-like table: columns widen to their content
        # chart and its limits
        self.W_icon(a, 488, 10, "replot", lambda: self.safe_replot(True))
        self.W_label(a, 536, 24, "X =")
        self.e_xmin = self.W_entry(a, 568, 17, 60, "")
        self.W_label(a, 636, 24, "...")
        self.e_xmax = self.W_entry(a, 656, 17, 60, "")
        self.W_label(a, 740, 24, "Y = ")
        self.e_ymin = self.W_entry(a, 776, 17, 60, "")
        self.W_label(a, 844, 24, "...")
        self.e_ymax = self.W_entry(a, 864, 17, 60, "")
        self.cv = tk.Canvas(a, bg=SAND, highlightthickness=0)
        self.cv.place(x=self.px(488), y=self.px(60), width=self.px(464), height=self.px(484))
        self.cv.bind("<ButtonPress-1>", self._c_press)
        self.cv.bind("<B1-Motion>", self._c_move)
        self.cv.bind("<ButtonRelease-1>", self._c_release)
        self.cv.bind("<MouseWheel>", lambda e: self._c_zoom(e, e.delta > 0))
        self.cv.bind("<Button-4>", lambda e: self._c_zoom(e, True))
        self.cv.bind("<Button-5>", lambda e: self._c_zoom(e, False))
        if not hasattr(self, "chart"):
            self.chart = dict(series=[], mark=None, r=[None] * 4, xs="t", ys="uC", sel=[], last=[0.0] * 4,
                              rep=5, npts=0, prec=[2, 2], maps=[], xas=None, yas=None)
        self.restore_main()
        self.on_resume()

    def restore_main(self):
        st = self.st
        self.sw_meas._on = st["prog"]
        self.sw_meas.draw()
        self.sw_check._on = st["auto"]
        self.sw_check.draw()
        for e, k in ((self.e_ih, "ih_txt"), (self.e_il, "il_txt"), (self.e_tl, "tl_txt"), (self.e_title, "title_txt"),
                     (self.e_xmin, "x0"), (self.e_xmax, "x1"), (self.e_ymin, "y0"), (self.e_ymax, "y1")):
            v = getattr(self, "_keep", {}).get(k, "")
            if v:
                self.setval(e, v)
        kp = getattr(self, "_keep", {})
        for sb, k in ((self.sb_ih, "ih_p"), (self.sb_il, "il_p"), (self.sb_tl, "tl_p")):
            sb.setp(kp.get(k, 0), False)
        for i, b in enumerate(self.hb):
            b.config(text=kp.get("hb", ["f(x)"] * 3)[i])
        self.tbl["exprs"] = kp.get("exprs", [])
        self.red(self.lb_ih, st["heat"] != 0)
        self.red(self.lb_il, st["led"] != 0)
        if self.tbl_src_keep is not None:
            self.table_fill(self.tbl_src_keep)

    tbl_src_keep = None

    def keep_main(self):
        try:
            self._keep = dict(ih_txt=self.val(self.e_ih), il_txt=self.val(self.e_il), tl_txt=self.val(self.e_tl),
                              title_txt=self.val(self.e_title), x0=self.val(self.e_xmin), x1=self.val(self.e_xmax),
                              y0=self.val(self.e_ymin), y1=self.val(self.e_ymax), ih_p=self.sb_ih._p, il_p=self.sb_il._p,
                              tl_p=self.sb_tl._p, hb=[b.cget("text") for b in self.hb], exprs=list(self.tbl["exprs"]))
            self.tbl_src_keep = self.tbl["src"]
        except (tk.TclError, AttributeError):
            pass

    def red(self, w, on):
        w.config(bg="#ff0000" if on else SAND)

    def _flag(self, k, v):
        setattr(self, k, v)

    def lab(self):
        return self.db.pstr("lab", "ANY LAB")

    # ------------------------------------------------------------ launcher / lifecycle
    def launch(self):
        self.app_running = True
        self.sim.firmware.sink = self.on_board
        self.send({"type": "hello"})

    def send(self, m):
        if self.sim.mode == "virtual":
            self.sim.firmware.handle(m)

    def home(self):
        self.ask_to_stop()
        self.withdraw()

    def back(self):
        if self.dlg is not None:
            self.close_dialog()
            return
        if self.act != "main":
            self.go("main")
            return
        if time.time() - self.st["last_back"] > 4.0:
            self.toast('Press "back" again to close this app', True)
            self.st["last_back"] = time.time()
        else:
            self.ask_to_stop()
            self.send({"type": "bye"})
            self.app_running = False
            self.st.update(connected=False, attached=False, no_usb_shown=False)
            self.withdraw()

    def go(self, act):
        if self.act == "main":
            self.keep_main()
        self.act = act
        self.close_dialog()
        self._build_all()

    # ------------------------------------------------------------ USB
    def on_board(self, m):
        t = m.get("type")
        if t == "welcome":
            self.usb_attach(bool(m.get("attached")))
        elif t == "attach":
            self.usb_attach(True)
        elif t == "detach":
            self.usb_detach()
        elif t == "frames":
            for f in m.get("list", []):
                self.on_frame(f)
        elif t == "done":
            if self.st["prog"] and self.st["sweep"]:
                self.st["prog"] = False
                self.stop_thread()

    def usb_attach(self, on):
        st = self.st
        if not on:
            if st["attached"]:
                self.usb_detach()
            elif not st["no_usb_shown"]:
                st["no_usb_shown"] = True
                self.toast("No USB connected")
            return
        if st["attached"]:
            return
        st["attached"] = True
        if st["usb_default"]:
            self.granted()
        else:
            self.deiconify()
            self.dialog(msg="Allow IPhO to access STM32 Virtual ComPort?", check="Use by default for this USB device",
                        ok="OK", cancel="Cancel", small=True, on_select=lambda v, d: (st.update(usb_default=st["usb_default"] or d), self.granted()),
                        on_cancel=lambda: (self.toast("USB Permission not granted"), st.update(connected=False)))

    def granted(self):
        st = self.st
        if not st["attached"]:
            return
        if time.time() - st["last_reset"] < 10.0:
            self.toast("Device connected.")
            st["connected"] = True
        else:
            self.toast("Please press RESET button on the board in 10 seconds!", True, True)
        st["last_reset"] = time.time()

    def usb_detach(self):
        st = self.st
        if not st["attached"]:
            return
        st["attached"] = False
        self.toast("USB disconnected")
        st["connected"] = False
        self.ask_to_stop()

    # ------------------------------------------------------------ measurement thread
    def start_thread(self):
        st, ch = self.st, self.chart
        sweep_on = st["sweep"] and not st["auto"]
        z2 = not st["auto"]
        if not st["auto"] and st["prog"]:
            self.chart_reset()
        st["thread"] = {"z2": z2, "sweep": sweep_on}
        self.meas.setup_axes(ch["xs"], ch["ys"])
        self.table_bind(self.meas)
        ch["series"].append({"name": self.meas.name, "x": [], "y": [], "col": "#0000ff"})
        ch["maps"].append({"m": self.meas, "s": ch["series"][-1], "n": 0})
        self.meas.start_measurement()
        if st["prog"] and st["sweep"]:
            ch["rep"] = 1
        pw = self.db.pdbl("led_current_pulse_durations_ms", 0.0) if self.db.pbool("pulsed_current", False) else 0.0
        sweep = None
        if sweep_on:
            sweep = get_sweep_array(self.db.pdbl("min_sweep_led_current_mA", 1.0) * 0.001, self.db.pdbl("max_sweep_led_current_mA", 1.0) * 0.001,
                                    self.db.pint("sweep_measurement_points_number", 50), self.db.pbool("sweep_geometric_current_increase", False), True)
        self.send({"type": "run", "on": True, "ts": self.db.pint("interval_between_measurements_ms", 140) / 1000.0,
                   "sweep": sweep, "pw": pw if sweep_on else st["pw"], "led": st["led"]})
        st["skip"] = 0

    def on_frame(self, b):
        st = self.st
        if len(b) != 30:
            return
        if st["skip"] > 0:
            st["skip"] -= 1
            return
        if not (st["prog"] or st["auto"]) or not st["thread"]:
            return
        if b[2] == 4 and st["thread"]["sweep"]:
            st["led"] = led_amps(b[15], b[16])
        self.meas.push(b, st["led"])
        if self.act == "main":
            self.table_live()
        if st["prog"]:
            self.chart_update_mapped()

    def stop_thread(self):
        st = self.st
        th = st["thread"]
        if not th:
            return
        st["thread"] = None
        self.send({"type": "run", "on": False})
        self.meas.stop_measurement()
        if th["z2"]:
            self.meas.save(self.db, LAST)
            self.chart_update_mapped(True)
            self.chart["sel"] = [LAST]
            if self.act == "main":
                self.table_fill(self.meas)
        self.ask_to_stop(True)
        if self.db.pbool("turn_off_LED_on_measurement_end", False) and st["led"] != 0:
            st["led"] = st["pw"] = 0.0
            self.send({"type": "led", "A": 0.0, "pw": 0.0})
            if self.act == "main":
                self.setval(self.e_il, "0")
                self.sb_il.setp(0, False)
                self.sb_tl.setp(0, False)
                self.red(self.lb_il, False)
            st["last_led"] = 0.0
            self.toast("LED current off")
        if self.db.pbool("turn_off_heating_on_measurement_end", False) and st["heat"] != 0:
            st["heat"] = 0.0
            self.send({"type": "heat", "A": 0.0})
            if self.act == "main":
                self.setval(self.e_ih, "0")
                self.sb_ih.setp(0, False)
                self.red(self.lb_ih, False)
            self.toast("Heating current off")

    def ask_to_stop(self, from_thread=False):
        st = self.st
        was = st["prog"] or st["auto"]
        st["auto"] = st["prog"] = False
        if self.act == "main":
            try:
                self.sw_meas._on = False
                self.sw_meas.draw()
                self.sw_check._on = False
                self.sw_check.draw()
            except (tk.TclError, AttributeError):
                pass
        if was and not from_thread:
            self.stop_thread()

    def on_measure(self):
        st = self.st
        if self.dlg is not None:
            return
        want = not self.sw_meas._on
        if not st["connected"]:
            self.toast("Please plug in, power on and reset the board first.")
            return
        if st["auto"]:
            st["auto"] = st["prog"] = False
            self.sw_check._on = False
            self.sw_check.draw()
            self.stop_thread()
            self.toast("All running measurements stopped. Tap again to start measurement.", True, True)
            return
        self.sw_meas._on = want
        self.sw_meas.draw()
        st["prog"] = want
        if want:
            self.chart["sel"] = []
            self.start_thread()
        else:
            self.stop_thread()

    def on_check(self):
        st = self.st
        if self.dlg is not None:
            return
        want = not self.sw_check._on
        if not st["connected"]:
            self.toast("Please plug in, power on and reset the board first.")
            return
        if st["prog"]:
            self.toast("You don't want to do this during measurement.")
            return
        self.sw_check._on = want
        self.sw_check.draw()
        st["auto"] = want
        if want:
            self.start_thread()
        else:
            self.stop_thread()

    def during(self):
        if self.st["prog"] or self.st["auto"]:
            self.toast("You don't want to do this during measurement.")
            return True
        return False

    def on_add(self):
        if self.st["prog"]:
            self.toast("You don't want to do this during measurement.")
            return
        nm = self.val(self.e_title)
        if nm == "":
            self.toast("No measurement title entered!")
            return
        if nm not in self.db.d["titles"]:
            self.meas.save(self.db, nm)
            self.toast("saved  " + nm)
        else:
            self.toast("This name already exists!")

    def on_del(self):
        if self.st["prog"]:
            self.toast("You don't want to do this during measurement.")
            return
        nm = self.val(self.e_title)
        if nm == "":
            self.toast("No measurement title entered!")
            return
        if nm not in self.db.d["titles"]:
            self.toast("No measurement with this title exists")
            return
        self.db.d["titles"].remove(nm)
        self.db.save()
        if nm in self.chart["sel"]:
            self.chart["sel"].remove(nm)
            self.plot_selected(True)
        if self.tbl["src"] is not None and self.tbl["src"].name == nm:
            self.table_clear()
            self.tbl["src"] = None
        self.toast("deleted " + nm)
        self.setval(self.e_title, "")

    def on_meas_list(self):
        if self.during():
            return
        lst = list(self.db.d["titles"])
        if not lst:
            self.toast("Nothing to select from!", True)
            return

        def pick(a):
            self.setval(self.e_title, a[0])
            self.table_fill(Measurement.load(self.db, a[0]))
        self.dialog(title="Select measurement to edit", items=lst, on_select=pick, on_cancel=lambda: self.toast("Changes cancelled."))

    def on_info(self):
        l = self.lab()
        s = l + ";\ntimestep = %d ms;\n" % self.db.pint("interval_between_measurements_ms", 140)
        if l == "LAB 2" and self.db.pbool("sweep_measurement", True):
            s += "sweep measurement;\nnumber of points = %d;\n" % self.db.pint("sweep_measurement_points_number", -1)
            if self.db.pbool("pulsed_current", False):
                s += "current pulse duration = %s ms ;\n" % jF(self.db.pdbl("led_current_pulse_durations_ms", -1.0), 1)
        self.toast(s, True)

    # heater and LED
    def show_apply(self):
        self.bt_apply.place(x=self.px(270), y=self.px(96), width=self.px(92), height=self.px(40))
        self.bt_cancel.place(x=self.px(374), y=self.px(96), width=self.px(100), height=self.px(40))
        self.bt_apply.lift()
        self.bt_cancel.lift()

    def on_ih_seek(self, p):
        self.setval(self.e_ih, jF(500.0 * p / 100.0, 0))
        self.show_apply()

    def on_il_seek(self, p):
        d = LED_PROG[p] * 1000.0
        self.setval(self.e_il, jF(d, prec_digits(d) if d > 0 else 0))

    def _il_stop(self):
        self.ch_led = False
        self.update_led()

    def on_tl_seek(self, p):
        self.setval(self.e_tl, jF(25.5 * p / 100.0, 1))

    def _tl_stop(self):
        self.ch_pw = False
        self.update_led()

    def on_apply(self):
        self.last_heat = (self.sb_ih._p, self.val(self.e_ih))
        self.update_heat()
        self.bt_apply.place_forget()
        self.bt_cancel.place_forget()

    def on_cancel_heat(self):
        self.sb_ih.setp(self.last_heat[0], False)
        self.setval(self.e_ih, self.last_heat[1])
        self.bt_apply.place_forget()
        self.bt_cancel.place_forget()

    @staticmethod
    def _num(s, d):
        if s == "":
            return d
        try:
            return float(s.strip().rstrip("dDfF"))
        except ValueError:
            return float("nan")

    def update_heat(self):
        if self.ch_heat:
            return
        s = self.val(self.e_ih) or "0"
        v = self._num(s, 0.0)
        if v != v:
            self.toast("Bad heater current value!")
            return
        if v < 0:
            self.toast("Can't be < 0.")
            return
        if v > 500:
            self.toast("Too big value.")
            return
        st = self.st
        st["skip"] = 1 if (st["prog"] or st["auto"]) else 0
        st["heat"] = v / 1000.0
        self.send({"type": "heat", "A": v / 1000.0})
        if v == 0:
            self.red(self.lb_ih, False)
            self.toast("Turned off heating.")
        else:
            self.red(self.lb_ih, True)

    def update_led(self):
        if self.ch_led or self.ch_pw:
            return
        v = self._num(self.val(self.e_il), 0.0)
        pw = self._num(self.val(self.e_tl), 0.0)
        if v != v:
            self.toast("Bad value of LED current!")
            return
        if pw != pw:
            self.toast("Bad value of LED current pulse width entered!")
            return
        if v < 0 or pw < 0:
            self.toast("Can't be < 0.")
            return
        if v > 50 or pw > 25.5:
            self.toast("Too big value.")
            return
        st = self.st
        st["led"], st["pw"] = v * 0.001, pw
        self.send({"type": "led", "A": st["led"], "pw": pw})
        if v == 0:
            self.red(self.lb_il, False)
            if st["last_led"] != 0:
                self.toast("LED current off")
        else:
            self.red(self.lb_il, True)
        st["last_led"] = v

    def on_resume(self):
        st = self.st
        st["sweep"] = self.db.pbool("sweep_measurement", False)
        for e in (self.e_il, self.e_tl):
            e.config(state="disabled" if st["sweep"] else "normal")
        for sb in (self.sb_il, self.sb_tl):
            sb._off = st["sweep"]
            sb.draw()
        ch = self.chart
        ok = lambda x: x in VARS or x in self.db.d["eq"]
        if not ok(ch["xs"]) or not ok(ch["ys"]):
            if not ok(ch["xs"]):
                ch["xs"] = "t"
            if not ok(ch["ys"]):
                ch["ys"] = "uC"
            self.safe_replot(False)
        else:
            self.chart_draw()
        lab1 = self.lab() == "LAB 1"
        for w, (x, y) in ((self.lb_il, (153, 106)), (self.lb_tl, (153, 143)), (self.un_il, (236, 107)), (self.un_tl, (236, 144))):
            if lab1:
                w.place_forget()
            else:
                w.place(x=self.px(x), y=self.px(y))
        for w, (x, y, ww) in ((self.e_il.master, (180, 100, 54)), (self.e_tl.master, (180, 137, 54)), (self.sb_il, (266, 101, 214)), (self.sb_tl, (266, 138, 214))):
            if lab1:
                w.place_forget()
            else:
                w.place(x=self.px(x), y=self.px(y), width=self.px(ww), height=self.px(30 if ww == 54 else 32))

    # ------------------------------------------------------------ TableHandler
    def table_exprs(self):
        if not self.tbl["exprs"]:
            self.tbl["exprs"] = ["t", "uC", "uT"]
            for i, b in enumerate(self.hb):
                if i < 3:
                    b.config(text=self.tbl["exprs"][i])
        return self.tbl["exprs"]

    def table_clear(self):
        self.tcv.delete("row")
        for k in range(3):
            self.tcv.coords("c%d" % k, self.px(8 + 96 * k), 0)
        self.tbl_cw = [self.px(88)] * 3
        self.tbl["live"] = False
        self.tcv.configure(scrollregion=(0, 0, self.px(470), self.px(44)))

    def _fmt(self, e, v):
        return jF(v, 3) if e == "t" else jE(v, 3)

    def _row_y(self, i):
        return self.px(44 + 23.4 * i)

    def _draw_row(self, i, vals):
        cw = self.tbl_cw
        for k, s in enumerate(vals):
            w = self.tbl_font.measure(s)
            if w > cw[k]:
                for j in range(k + 1, 3):
                    self.tcv.move("c%d" % j, w - cw[k], 0)
                cw[k] = w
            x = self.px(8) + sum(cw[j] + self.px(8) for j in range(k))
            self.tcv.create_text(x, self._row_y(i), text=s, anchor="nw", font=self.tbl_font, fill="#222", tags=("row", "c%d" % k))

    def table_bind(self, m):
        if self.act != "main":
            return
        self.table_clear()
        self.tbl["parts"] = []
        self.tbl["src"] = m
        for e in self.table_exprs():
            m.add_expr(e)
            self.tbl["parts"].append(m.part(e))
        self.tbl["live"] = True

    def table_live(self):
        if not self.tbl["live"]:
            return
        m = self.tbl["src"]
        self.tcv.delete("row")
        self._draw_row(0, [self._fmt(e, m.last(self.tbl["parts"][i])) for i, e in enumerate(self.tbl["exprs"])])

    def table_fill(self, m):
        self.tbl["filled"] = 0
        self.tbl["src"] = m
        for e in self.table_exprs():
            m.add_expr(e)
        m.calc_all()
        self.table_clear()
        self.tbl["parts"] = []
        for i, e in enumerate(self.tbl["exprs"]):
            self.hb[i].config(text=e)
            self.tbl["parts"].append(m.part(e))
        self.table_refill()

    def table_refill(self):
        m = self.tbl["src"]
        if m is None:
            return
        n = min(m.nc, self.tbl["filled"] + 300)
        if self.tbl["filled"] < n:
            self.toast("Loading more data...")
        for i in range(self.tbl["filled"], n):
            self._draw_row(i, [self._fmt(e, self.tbl["parts"][k][i] if i < len(self.tbl["parts"][k]) else float("nan"))
                               for k, e in enumerate(self.tbl["exprs"])])
        self.tbl["filled"] = n
        self.tcv.configure(scrollregion=(0, 0, self.px(470), self._row_y(n) + self.px(6)))

    def _tbl_scrolled(self, a1, a2):
        if float(a2) >= 0.999 and time.time() - self.tbl["last_scroll"] > 0.1 and not self.tbl["live"]:
            self.tbl["last_scroll"] = time.time()
            if self.tbl["src"] is not None and self.tbl["filled"] < self.tbl["src"].nc:
                self.after(10, self.table_refill)

    def on_header(self, b):
        if self.during():
            return
        axes = filter_lab(VARS + self.db.d["eq"], self.lab())

        def pick(a):
            b.config(text=a[0])
            ex = [h.cget("text") for h in self.hb if h.cget("text") != "f(x)"]
            self.tbl["exprs"] = ex
            for i, h in enumerate(self.hb):
                h.config(text=ex[i] if i < len(ex) else "f(x)")
            if self.tbl["src"] is not None:
                self.table_fill(self.tbl["src"])
        self.dialog(title="Select equations to monitor", items=axes, selected=[b.cget("text")], on_select=pick,
                    on_cancel=lambda: self.toast("Changes cancelled."))

    # ------------------------------------------------------------ ChartHandler (achartengine scatter chart)
    K = 4.0 / 3.0

    def chart_reset(self):
        ch = self.chart
        ch.update(series=[], mark=None, r=[None] * 4, npts=0, prec=[2, 2], maps=[])
        ch["rep"] = self.db.pint("replot_each_n_timesteps", 5)
        if not ch["sel"]:
            self.put_point(0, 0, "Tap for measurements")
        self.chart_draw()

    def put_point(self, x, y, label=None):
        if label is None:
            label = "x,y: " + (jE(x, 3) if abs(x) < 0.1 else jF(x, 3)) + ", " + (jF(y, 3) if abs(y) >= 0.1 else jE(y, 3))
        self.chart["mark"] = {"name": label, "x": [x], "y": [y], "col": "#0000ff", "mark": True}

    def add_pt(self, s, x, y):
        if x != x or y != y:
            self.toast("NaN in data!")
            return
        if abs(x) >= 1e12 or abs(y) >= 1e12:
            self.toast("Overflow in data!(?)")
            return
        s["x"].append(x)
        s["y"].append(y)

    def chart_update_mapped(self, final=False):
        ch = self.chart
        for mp in ch["maps"]:
            m = mp["m"]
            for i in range(mp["n"], m.nc):
                self.add_pt(mp["s"], m.xr[i], m.yr[i])
                ch["npts"] += 1
                if ch["npts"] % max(1, ch["rep"]) == 0 and self.act == "main":
                    self._want_draw = True
            mp["n"] = m.nc
        if final and self.act == "main":
            self.chart_draw()

    _want_draw = False

    def tick_draw(self):
        if self._want_draw and self.act == "main":
            self._want_draw = False
            self.chart_draw()

    def all_series(self):
        ch = self.chart
        return ch["series"] + ([ch["mark"]] if ch["mark"] else [])

    def data_range(self):
        a = [float("inf"), float("-inf"), float("inf"), float("-inf")]
        for s in self.all_series():
            if s["x"]:
                a[0] = min(a[0], min(s["x"]))
                a[1] = max(a[1], max(s["x"]))
                a[2] = min(a[2], min(s["y"]))
                a[3] = max(a[3], max(s["y"]))
        return a

    def axis_limits(self):
        d, r = self.data_range(), self.chart["r"]
        big = 1.7976931348623157e308
        A = [r[0] if r[0] is not None else big, r[1] if r[1] is not None else -big,
             r[2] if r[2] is not None else big, r[3] if r[3] is not None else -big]
        return [min(A[0], d[0]), max(A[1], d[1]), min(A[2], d[2]), max(A[3], d[3])]

    def view(self):
        d, r = self.data_range(), self.chart["r"]
        v = [r[i] if r[i] is not None else d[i] for i in range(4)]
        if not (math.isfinite(v[0]) and math.isfinite(v[1])):
            v[0] = v[1] = 0.0
        if not (math.isfinite(v[2]) and math.isfinite(v[3])):
            v[2] = v[3] = 0.0
        return v

    def user_limits(self):
        out = []
        for e in (self.e_xmin, self.e_xmax, self.e_ymin, self.e_ymax):
            try:
                out.append(float(self.val(e)))
            except ValueError:
                out.append(float("nan"))
        return out

    def set_user_limits(self, a):
        dx, dy = a[1] - a[0], a[3] - a[2]
        for e, v, d in ((self.e_xmin, a[0], dx), (self.e_xmax, a[1], dx), (self.e_ymin, a[2], dy), (self.e_ymax, a[3], dy)):
            self.setval(e, jD(round_digits(v, prec_digits(d))))

    def plot_selected(self, user):
        ch = self.chart
        xa, ya = ch["xs"], ch["ys"]
        ch.update(series=[], mark=None, r=[None] * 4, npts=0, prec=[2, 2], maps=[])
        for nm in ch["sel"]:
            m = Measurement.load(self.db, nm)
            m.setup_axes(xa, ya)
            m.calc_all()
            s = {"name": m.name, "x": [], "y": [], "col": "#0000ff"}
            for i in range(m.n):
                self.add_pt(s, m.xr[i] if i < len(m.xr) else float("nan"), m.yr[i] if i < len(m.yr) else float("nan"))
            ch["series"].append(s)
        for i, s in enumerate(ch["series"]):
            s["col"] = COLORS[i % len(COLORS)]
        if user:
            lim = self.user_limits()
        else:
            lim = self.axis_limits()
            self.set_user_limits(lim)
            ch["last"] = list(lim)
        for i in range(4):
            if lim[i] == lim[i]:
                ch["r"][i] = lim[i]
        if not ch["sel"]:
            self.put_point(0, 0, "Tap for measurements")
        self.chart_draw()

    def safe_replot(self, user):
        if self.st["prog"]:
            self.toast("You don't want to do this during measurement.")
            return
        if self.chart["sel"] or not user:
            self.plot_selected(user)

    @staticmethod
    def labels(a, b, n):
        if abs(a - b) < 1.0000000116860974e-7:
            return [a]
        lo, hi = min(a, b), max(a, b)
        d = (hi - lo) / n
        f = math.floor(math.log10(d))
        p = d * 10.0 ** -f
        p = 10 if p > 5 else 5 if p > 2 else 2 if p > 1 else p
        stp = p * 10.0 ** f
        s0, s1 = math.ceil(lo / stp) * stp, math.floor(hi / stp) * stp
        k = int((s1 - s0) / stp) + 1
        return [round(s0 + i * stp, 5) for i in range(k)]

    def chart_draw(self):
        if self.act != "main":
            return
        c, ch, K = self.cv, self.chart, self.K
        c.delete("all")
        W, H = 464 * K, 484 * K
        f = self.px(464) / W
        L, Tp, R, B = 50, 50, W - 20, H - 70
        self.cbox = (L, Tp, R, B, W, H, f)

        def P(x, y):
            return x * f, y * f
        mc = "#b59896"
        for (x0, y0, x1, y1) in ((0, B, W, H), (0, 0, W, Tp), (0, 0, L, H), (R, 0, W, H)):
            c.create_rectangle(*P(x0, y0), *P(x1, y1), fill=mc, outline="")
        for (x0, y0, x1, y1) in ((0, 0, L, Tp), (R, 0, W, Tp), (0, B, L, H), (R, B, W, H)):
            c.create_rectangle(*P(x0, y0), *P(x1, y1), fill="#a48886", outline="")
        v = self.view()
        self.cview = v
        sx, sy = v[1] - v[0], v[3] - v[2]

        def X(x):
            return L + (x - v[0]) / sx * (R - L) if sx else L

        def Y(y):
            return B - (y - v[2]) / sy * (B - Tp) if sy else B
        self.cX, self.cY = X, Y
        lf = (self.fam, -max(6, int(14 * f)))
        for t in self.labels(v[0], v[1], 8):
            x = X(t)
            if L - 0.5 <= x <= R + 0.5:
                c.create_line(*P(x, Tp), *P(x, B), fill="#0000ff", width=1)
                c.create_text(*P(x, B + 14 * 4 / 3.0), text=nf(t, ch["prec"][0]), fill="#0000ff", font=lf, anchor="s")
        for t in self.labels(v[2], v[3], 8):
            y = Y(t)
            if Tp - 0.5 <= y <= B + 0.5:
                c.create_line(*P(L, y), *P(R, y), fill="#0000ff", width=1)
                c.create_text(*P(L, y), text=nf(t, ch["prec"][1]), fill="#0000ff", font=lf, anchor="s")
        c.create_line(*P(L, Tp), *P(L, B), *P(R, B), fill="#cccccc")
        tf = (self.fam, -max(8, int(32 * f)))
        c.create_text(*P(L + (R - L) / 2, B + 14 * 4 / 3.0 + 32), text=ch["xs"], fill="#0000ff", font=tf, anchor="s")
        c.create_text(*P(32, Tp + (B - Tp) / 2), text=ch["ys"], fill="#0000ff", font=tf, angle=90, anchor="s")
        for s in self.all_series():
            col = s["col"]
            n = len(s["x"])
            step = max(1, n // 4000)
            for i in range(0, n, step):
                px_, py_ = X(s["x"][i]), Y(s["y"][i])
                if not (L <= px_ <= R and Tp <= py_ <= B):
                    continue
                qx, qy = P(px_, py_)
                if s.get("mark"):
                    r = 4 * f
                    c.create_line(qx - r, qy - r, qx + r, qy + r, fill=col, width=2)
                    c.create_line(qx + r, qy - r, qx - r, qy + r, fill=col, width=2)
                else:
                    r = max(1.0, 1.6 * f)
                    c.create_oval(qx - r, qy - r, qx + r, qy + r, outline=col)
        gf = (self.fam, -max(6, int(16 * f)))
        lx, ly = L + 10, B + 34
        for s in self.all_series():
            w = len(s["name"]) * 8.5 + 30
            if lx + w > R and lx > L + 10:
                lx, ly = L + 10, ly + 20
            qx, qy = P(lx + 5, ly - 5)
            if s.get("mark"):
                r = 4 * f
                c.create_line(qx - r, qy - r, qx + r, qy + r, fill=s["col"], width=2)
                c.create_line(qx + r, qy - r, qx - r, qy + r, fill=s["col"], width=2)
            else:
                c.create_oval(qx - 2 * f, qy - 2 * f, qx + 2 * f, qy + 2 * f, outline=s["col"])
            c.create_text(*P(lx + 15, ly), text=s["name"], fill=s["col"], font=gf, anchor="sw")
            lx += w

    def _cp(self, e):
        f = self.cbox[6]
        return e.x / f, e.y / f

    def _c_press(self, e):
        self._g = {"start": self._cp(e), "moved": False, "v0": self.view()}

    def _c_move(self, e):
        g = getattr(self, "_g", None)
        if not g:
            return
        p = self._cp(e)
        if math.hypot(p[0] - g["start"][0], p[1] - g["start"][1]) > 8:
            g["moved"] = True
        if not g["moved"]:
            return
        L, Tp, R, B = self.cbox[:4]
        v = g["v0"]
        dx = (p[0] - g["start"][0]) / (R - L) * (v[1] - v[0])
        dy = (p[1] - g["start"][1]) / (B - Tp) * (v[3] - v[2])
        self.chart["r"] = [v[0] - dx, v[1] - dx, v[2] + dy, v[3] + dy]
        self.chart_draw()

    def _c_release(self, e):
        g = getattr(self, "_g", None)
        self._g = None
        if g and not g["moved"]:
            self.chart_click(*g["start"])

    def _real(self, px_, py_):
        L, Tp, R, B = self.cbox[:4]
        v = self.cview
        return [v[0] + (px_ - L) / (R - L) * (v[1] - v[0]), v[2] + (B - py_) / (B - Tp) * (v[3] - v[2])]

    def _c_zoom(self, e, zin):
        v = self.view()
        m = self._real(*self._cp(e))
        k = 1 / 1.25 if zin else 1.25
        self.chart["r"] = [m[0] - (m[0] - v[0]) * k, m[0] + (v[1] - m[0]) * k, m[1] - (m[1] - v[2]) * k, m[1] + (v[3] - m[1]) * k]
        self.chart_draw()

    def chart_click(self, px_, py_):
        ch = self.chart
        if self.st["prog"]:
            return
        a = self.axis_limits()
        z = [0.0] * 4
        changed = True
        if ch["last"] == z and a != z:
            ch["last"] = a
            changed = False
        elif a == ch["last"]:
            changed = False
        else:
            ch["last"] = a
        if changed:
            l = ch["last"]
            ch["prec"] = [prec_digits(l[1] - l[0]), prec_digits(l[3] - l[2])]
            self.chart_draw()
            self.set_user_limits(self.axis_limits())
            return
        for s in self.all_series():
            for i in range(len(s["x"])):
                if abs(self.cX(s["x"][i]) - px_) <= 10 and abs(self.cY(s["y"][i]) - py_) <= 10:
                    self.toast("%s=%s\n%s=%s" % (ch["xs"], jE(s["x"][i], 4), ch["ys"], jE(s["y"][i], 4)))
                    self.put_point(s["x"][i], s["y"][i])
                    self.chart_draw()
                    return
        W, H = self.cbox[4], self.cbox[5]
        bot = 0 + 70 + 32
        if px_ < 50 and 50 < py_ < H - bot:
            area = "Y"
        elif px_ >= (W - 50) / 2 and py_ > H - bot:
            area = "X"
        elif 50 <= px_ < W / 2 and py_ > H - bot:
            area = "LIST"
        else:
            area = "PLOT"
        if area in ("X", "Y"):
            lst = filter_lab(VARS + self.db.d["eq"], self.lab())

            def pick(s):
                ch["xs" if area == "X" else "ys"] = s[0]
                self.safe_replot(False)
            self.dialog(title="Select %s axis" % area, items=lst, selected=[ch["xs"] if area == "X" else ch["ys"]],
                        on_select=pick, on_cancel=lambda: self.toast("Changes cancelled."))
            return
        if area != "LIST" and ch["r"][1] is not None and ch["sel"]:
            self.put_point(*self._real(px_, py_))
            self.chart_draw()
            return
        lst = list(self.db.d["titles"])
        if not lst:
            self.toast("Nothing to select from!", True)
            return

        def pick2(s):
            ch["sel"] = list(s)
            self.safe_replot(False)
            if len(s) == 1:
                self.table_fill(Measurement.load(self.db, s[0]))
        self.dialog(items=lst, multi=area == "LIST", selected=list(ch["sel"]), on_select=pick2,
                    on_cancel=lambda: self.toast("Changes cancelled."))

    # ------------------------------------------------------------ SettingsActivity
    def open_settings(self):
        if self.st["prog"]:
            self.toast("You don't want to do this during measurement.")
            return
        for p in PREFS:
            if "k" in p and p["k"] not in self.db.d["prefs"] and p["d"] is not None:
                self.db.d["prefs"][p["k"]] = p["d"]
        self.db.save()
        self.go("set")

    def _build_settings(self):
        a = self.app
        cv = tk.Canvas(a, bg=SAND, highlightthickness=0)
        sb = tk.Scrollbar(a, orient="vertical", command=cv.yview)
        inner = tk.Frame(cv, bg=SAND)
        cv.create_window(0, 0, window=inner, anchor="nw", width=self.px(944))
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        cv.bind_all("<MouseWheel>", lambda e: cv.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), "units"))
        self._set_inner, self._set_cv = inner, cv
        self.render_settings()

    def render_settings(self):
        inner = self._set_inner
        for ch_ in inner.winfo_children():
            ch_.destroy()
        db = self.db
        l = db.pstr("lab", "ANY LAB")
        if l == "LAB 1" and db.d["prefs"].get("sweep_measurement"):
            db.pset("sweep_measurement", False)
        sweep_on = db.pbool("sweep_measurement", False)
        for p in PREFS:
            if "cat" in p:
                tk.Frame(inner, bg="#b39494", height=1).pack(fill="x", pady=(self.px(8), 0))
                tk.Label(inner, text=p["cat"], bg=SAND, fg=ACC, font=self.font(14, True), anchor="w").pack(fill="x", padx=(self.px(72), 0), pady=(self.px(16), self.px(4)))
                continue
            en = not (p.get("dep") == "lab" and l == "LAB 1") and not (p.get("incat") and not sweep_on) and not (p.get("dep2") and not db.pbool(p["dep2"], False))
            row = tk.Frame(inner, bg=SAND, cursor="hand2" if en else "")
            row.pack(fill="x", padx=(self.px(72), self.px(16)), pady=self.px(14))
            fg1, fg2 = ("#222", "#6d5858") if en else ("#a08a8a", "#b09a9a")
            txt = tk.Frame(row, bg=SAND)
            txt.pack(side="left", fill="x", expand=True)
            tk.Label(txt, text=p["t"], bg=SAND, fg=fg1, font=self.font(16), anchor="w").pack(fill="x")
            sm = None
            if p["type"] == "list":
                sm = l
            elif p["type"] == "num":
                v = db.d["prefs"].get(p["k"], p["d"])
                sm = ("null" if v is None else str(v)) + (" " + p["unit"] if p.get("unit") else "")
            elif p.get("s"):
                sm = p["s"]
            if sm is not None:
                tk.Label(txt, text=sm, bg=SAND, fg=fg2, font=self.font(14), anchor="w", justify="left", wraplength=self.px(760)).pack(fill="x")
            if p["type"] == "sw":
                on = db.pbool(p["k"], p["d"])
                swc = tk.Canvas(row, width=self.px(40), height=self.px(24), bg=SAND, highlightthickness=0)
                swc.pack(side="right")
                k = self.Sc
                swc.create_rectangle(3 * k, 6 * k, 37 * k, 18 * k, fill=("#f2a093" if on else "#8d7a7a") if en else "#bba5a5", outline="")
                cx = (28 if on else 12) * k
                swc.create_oval(cx - 10 * k, 2 * k, cx + 10 * k, 22 * k, fill=(ACC if on else "#ececec") if en else "#ddd", outline="")
                if en:
                    swc.bind("<Button-1>", lambda e, p=p: self.pref_click(p))
            if en:
                for w in [row, txt] + list(txt.winfo_children()):
                    w.bind("<Button-1>", lambda e, p=p: self.pref_click(p))
        inner.update_idletasks()
        self._set_cv.configure(scrollregion=self._set_cv.bbox("all"))

    def pref_click(self, p):
        db = self.db
        if p["type"] == "sw":
            db.pset(p["k"], not db.pbool(p["k"], p["d"]))
            self.render_settings()
            return
        if p["type"] == "list":
            self.dialog(title=p["t"], items=p["items"], selected=[db.pstr(p["k"], p["d"])], small=True,
                        on_select=lambda a: (db.pset(p["k"], a[0]), self.render_settings()))
            return
        u = " " + p["unit"] if p.get("unit") else ""

        def fmt(x):
            return str(int(x)) if float(x).is_integer() else str(x)
        rng = ""
        if p.get("mn") is not None and p.get("mx") is not None:
            rng = "From %s to %s%s" % (fmt(p["mn"]), fmt(p["mx"]), u)
        elif p.get("mn") is not None:
            rng = "Min %s%s" % (fmt(p["mn"]), u)
        cur = db.d["prefs"].get(p["k"], p["d"] if p["d"] is not None else "")

        def ok(v, _chk):
            v = str(v)
            if p["d"] is not None and (v == "" or self._num(v, float("nan")) == float(p["d"])):
                db.pset(p["k"], p["d"] if v == "" else v)
                self.render_settings()
                return
            x = self._num(v, float("nan")) if v.strip() else float("nan")
            err = None
            if x != x or (p.get("isint") and not float(x).is_integer()):
                err = "Non-numeric (or badly formatted) value %s !" % v
            elif p.get("mn") is not None and x < p["mn"]:
                err = "%s less than minimum value %s !" % (v, fmt(p["mn"]))
            elif p.get("mx") is not None and x > p["mx"]:
                err = "%s greater than maximum value %s !" % (v, fmt(p["mx"]))
            if err:
                self.toast(err, True)
                return
            db.pset(p["k"], v)
            self.render_settings()
        self.dialog(title=p["t"], msg=rng, entry=str(cur), ok="OK", cancel="Cancel", small=True, on_select=ok)

    # ------------------------------------------------------------ EquationEditorActivity (portrait)
    def open_editor(self):
        if self.during():
            return
        self.go("eq")

    def _build_editor(self):
        a = self.app
        for (s, x, y, w, h) in EQ_KEYS:
            l = tk.Label(a, text=s, bg=DSAND, fg="#222", font=self.font(30), anchor="w", padx=self.px(2), cursor="hand2")
            l.place(x=self.px(x), y=self.px(y), width=self.px(w), height=self.px(h))
            l.bind("<Button-1>", lambda e, s=s: self.eq_key(s))
        self.W_icon(a, 18, 132, "add", self.eq_add, size=70)
        self.W_icon(a, 99, 132, "del", self.eq_del, size=70)
        self.W_icon(a, 179, 132, "edit", self.eq_sel, size=70)
        self.eq = tk.Entry(a, font=self.font(24), relief="flat", bg=SAND, highlightthickness=0, fg="#222", insertbackground="#222")
        self.eq.place(x=self.px(16), y=self.px(220), width=self.px(568), height=self.px(34))
        self.eq_line = tk.Frame(a, bg=ACC)
        self.eq_line.place(x=self.px(16), y=self.px(256), width=self.px(568), height=2)
        self.eq.focus_set()

    def eq_ins(self, s):
        p = self.eq.index("insert")
        self.eq.insert(p, s)
        self.eq.icursor(p + len(s))

    def eq_key(self, s):
        e = self.eq
        if s in EQ_FN:
            self.eq_ins(s)
            self.eq_ins("()")
            e.icursor(e.index("insert") - 1)
        elif s == "()":
            self.eq_ins("()")
            e.icursor(e.index("insert") - 1)
        elif s == "del":
            p = e.index("insert")
            if p < len(e.get()):
                e.delete(p)
        elif s == "bsp":
            p = e.index("insert")
            if p > 0:
                e.delete(p - 1)
        else:
            self.eq_ins(s)
        e.focus_set()

    def eq_add(self):
        s = self.eq.get().strip()
        if s == "":
            self.toast("Empty equation.")
            return
        if not exp4j_valid(s):
            self.toast("Equation is invalid!")
            self.eq_line.config(bg="#d50000")
            return
        self.eq_line.config(bg=ACC)
        self.db.d["eq"].append(s)
        self.db.save()
        self.toast("Saved equation " + s)

    def eq_del(self):
        s = self.eq.get()
        if s not in self.db.d["eq"]:
            self.toast("No such equation to remove.")
            return
        self.db.d["eq"].remove(s)
        self.db.save()
        self.eq.delete(0, "end")

    def eq_sel(self):
        lst = list(self.db.d["eq"])
        cur = self.eq.get()
        if cur not in lst:
            if not lst:
                self.toast("No equation created!")
                return
            cur = lst[0]
        self.dialog(items=lst, selected=[cur], on_select=lambda a: (self.eq.delete(0, "end"), self.eq.insert(0, a[0])),
                    on_cancel=lambda: self.toast("Selection cancelled."))


LED_PROG = get_sweep_array(0.0, 0.05, 101, True, True)


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


# ============================================================================
#                                  BENCH
# ============================================================================
SOCKET_XY = {}          # filled by Bench._layout
PORT_USB = (168, 52)
PORT_DATA = (352, 52)
RESET_XY = (512, 62)
SW1_XY = (470, 176)
LED_XY = (206, 279)
NTC_XY = (240, 279)
CAP_XY = (168, 279)


class Bench(tk.Canvas):
    """Laboratory bench: board, jumper wires, charger, cable, insulation."""

    W, H = 1010, 600

    def __init__(self, master, sim):
        super().__init__(master, width=self.W, height=self.H, bg="#c9c3b6",
                         highlightthickness=0)
        self.sim = sim
        self.board = sim.board
        self._layout()
        self.parts = {
            "charger": dict(on=False, pos=(700, 470), label=T("charger")),
            "cable":   dict(on=False, pos=(700, 530), label=T("datacable")),
            "insul":   dict(on=True,  pos=(0, 0),     label=T("insul")),
            "therm":   dict(on=False, pos=(880, 120), label=T("thermometer")),
            "tablet":  dict(on=False, pos=(760, 220), label=T("tablet")),
        }
        self.wires = {"W1": dict(on=False, p=[(660, 380), (760, 380)]),
                      "W2": dict(on=False, p=[(660, 420), (760, 420)])}
        self.drag = None
        self.bind("<Button-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_move)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.refresh()

    # ------------------------------------------------------------------
    def _layout(self):
        names = [("N9A", "-9V"), ("N9B", "-9V"), ("GNDA", "GND"), ("GNDB", "GND"),
                 ("P9A", "+9V"), ("P9B", "+9V"), ("INA", "IN"), ("INB", "IN")]
        for i, (n, lab) in enumerate(names):
            SOCKET_XY[n] = (556, 96 + 26 * i, lab)

    # ------------------------------------------------------------------ draw
    def refresh(self):
        self.delete("all")
        b = self.board
        # ---------------- PCB
        self.create_rectangle(40, 40, 600, 330, fill="#1f6b3a", outline="#12401f", width=3)
        self.create_rectangle(46, 46, 594, 324, outline="#2f8b4a")
        for x in range(60, 590, 34):          # copper traces (decoration)
            self.create_line(x, 60, x, 200, fill="#2a7d45")
        # power module
        self.create_rectangle(60, 70, 130, 130, fill="#123", outline="#345")
        self.create_oval(66, 76, 108, 118, fill="#1a1a2a", outline="#889")
        self.create_text(87, 97, text="1000\n6.3", fill="#dde", font=("TkDefaultFont", 6))
        self.create_rectangle(190, 70, 300, 120, fill="#0d1a2a", outline="#345")
        self.create_text(245, 95, text="MCU", fill="#8ab", font=("TkDefaultFont", 8))
        # ports
        self.create_rectangle(PORT_USB[0] - 22, 40, PORT_USB[0] + 22, 62,
                              fill="#b0b0b8", outline="#666")
        self.create_text(PORT_USB[0], 72, text="USB (j)", fill="#dfe", font=("TkDefaultFont", 7))
        self.create_rectangle(PORT_DATA[0] - 26, 40, PORT_DATA[0] + 26, 62,
                              fill="#e8e8e0", outline="#666")
        self.create_text(PORT_DATA[0], 72, text="6-PIN (k)", fill="#dfe", font=("TkDefaultFont", 7))
        # reset
        self.create_oval(RESET_XY[0] - 12, RESET_XY[1] - 12, RESET_XY[0] + 12, RESET_XY[1] + 12,
                         fill="#333", outline="#999", width=2, tags="reset")
        self.create_text(RESET_XY[0], RESET_XY[1] + 22, text="RESET (i)", fill="#dfe",
                         font=("TkDefaultFont", 7))
        # power LED
        self.create_oval(96, 140, 106, 150, fill="#3f6" if b.powered else "#252",
                         outline="#062")
        self.create_text(150, 145, text=T("powered") if b.powered else T("no_power"),
                         fill="#dfe", font=("TkDefaultFont", 7), anchor="w")

        # ---------------- terminal strip
        self.create_rectangle(536, 80, 596, 300, fill="#0e4a29", outline="#0a3a20")
        for n, (x, y, lab) in SOCKET_XY.items():
            free = self._socket_free(n)
            self.create_oval(x - 8, y - 8, x + 8, y + 8,
                             fill="#d8b24a" if free else "#f2e2a0", outline="#7a5a10", width=2)
            self.create_text(x + 12, y, text=lab, anchor="w", fill="#eafbea",
                             font=("TkDefaultFont", 8, "bold"))
        # SW1
        sx, sy = SW1_XY
        self.create_rectangle(sx - 14, sy - 40, sx + 14, sy + 40, fill="#222", outline="#888")
        pos = {"C1": -26, "MID": 0, "C2": 26}[b.sw1]
        self.create_rectangle(sx - 10, sy + pos - 10, sx + 10, sy + pos + 10,
                              fill="#ddd", outline="#333", tags="sw1")
        self.create_text(sx, sy - 52, text="C1", fill="#dfe", font=("TkDefaultFont", 8, "bold"))
        self.create_text(sx, sy + 52, text="C2", fill="#dfe", font=("TkDefaultFont", 8, "bold"))
        self.create_text(sx + 26, sy, text="SW1", fill="#dfe", angle=90, font=("TkDefaultFont", 7))

        # ---------------- thermostat block
        self.create_rectangle(60, 228, 320, 322, fill="#2b2b2b", outline="#111")   # foam
        self.create_text(190, 236, text="Thermostat (PCB)", fill="#bbb", font=("TkDefaultFont", 7))
        for x in (80, 300):                       # nylon screws
            self.create_oval(x - 11, 246, x + 11, 268, fill="#f2f2ee", outline="#bbb")
            self.create_line(x - 6, 257, x + 6, 257, fill="#999")
        # components under the pad
        self.create_rectangle(CAP_XY[0] - 22, CAP_XY[1] - 14, CAP_XY[0] + 22, CAP_XY[1] + 14,
                              fill="#8a5a20", outline="#5a3a10")
        self.create_text(CAP_XY[0], CAP_XY[1], text="C1 C2", fill="#fff", font=("TkDefaultFont", 6))
        self.create_rectangle(NTC_XY[0] - 12, NTC_XY[1] - 10, NTC_XY[0] + 12, NTC_XY[1] + 10,
                              fill="#111", outline="#666")
        self.create_text(NTC_XY[0], NTC_XY[1], text="NTC", fill="#ddd", font=("TkDefaultFont", 6))
        uL, _, _ = b.led_state()
        glow = min(1.0, b.iL / 30.0) if b.powered else 0.0
        if b.tL > 0:
            glow *= 0.35
        self.create_oval(LED_XY[0] - 9, LED_XY[1] - 9, LED_XY[0] + 9, LED_XY[1] + 9,
                         fill="#c8c8c8", outline="#777")
        if glow > 0.02:
            rr = 10 + 16 * glow
            col = "#ff%02x%02x" % (int(60 + 120 * glow), int(40 + 40 * glow))
            self.create_oval(LED_XY[0] - rr, LED_XY[1] - rr, LED_XY[0] + rr, LED_XY[1] + rr,
                             fill=col, outline="")
            self.create_oval(LED_XY[0] - 6, LED_XY[1] - 6, LED_XY[0] + 6, LED_XY[1] + 6,
                             fill="#fff6d0", outline="")
        # heater resistor
        self.create_rectangle(110, 296, 150, 310, fill="#d8d8d8", outline="#666")
        self.create_text(130, 303, text="Rheat", font=("TkDefaultFont", 6))
        if self.parts["insul"]["on"]:
            self.create_rectangle(100, 244, 282, 312, fill="#fbfbf7", outline="#ddd")
            self.create_text(191, 278, text=T("insul"), fill="#999", font=("TkDefaultFont", 7))
            self.create_rectangle(70, 240, 312, 248, fill="#e8f0f8", outline="#b8c8d8")  # plate
            if glow > 0.02:                      # light shining through the pad
                rr = 12 + 14 * glow
                pale = "#ff%02x%02x" % (int(190 - 40 * glow), int(170 - 40 * glow))
                self.create_oval(LED_XY[0] - rr, LED_XY[1] - rr, LED_XY[0] + rr,
                                 LED_XY[1] + rr, fill=pale, outline="")
        # board ID
        self.create_rectangle(430, 250, 520, 310, fill="#f4f4ee", outline="#999")
        self.create_text(475, 262, text=T("board_id"), font=("TkDefaultFont", 7))
        self.create_text(475, 280, text=b.board_id, font=("TkFixedFont", 11, "bold"))
        for i in range(6):
            for j in range(6):
                if (i * 7 + j * 3 + int(b.board_id[i % 6])) % 3 == 0:
                    self.create_rectangle(440 + j * 5, 288 + i * 3, 444 + j * 5, 290 + i * 3,
                                          fill="#111", outline="")

        # ---------------- parts on the bench
        self._draw_parts()
        self._draw_wires()

        # ---------------- tray
        self.create_rectangle(0, 560, self.W, self.H, fill="#a89f8f", outline="")
        self.create_text(8, 570, text=T("tray"), anchor="w", font=("TkDefaultFont", 8, "bold"))
        x = 10
        for key, lab in (("charger", "2 " + T("t_charger")), ("cable", "5 " + T("t_cable")),
                         ("insul", "4 " + T("t_insul")), ("therm", "7 " + T("t_therm")),
                         ("tablet", "6 " + T("tablet")), ("W1", "3 W1 (100 MΩ)"),
                         ("W2", "3 W2 (0 Ω)")):
            st = self.parts[key]["on"] if key in self.parts else self.wires[key]["on"]
            self.create_rectangle(x, 580, x + 130, 600, fill="#7d7466" if st else "#efe9dd",
                                  outline="#555", tags=("tray:" + key,))
            self.create_text(x + 65, 590, text=lab, font=("TkDefaultFont", 8),
                             fill="#ddd" if st else "#111", tags=("tray:" + key,))
            x += 134

        if self.board.short_circuit:
            self.create_text(self.W / 2, 350, text=T("short"), fill="#c00",
                             font=("TkDefaultFont", 11, "bold"))
        self.create_text(8, 344, anchor="w", font=("TkDefaultFont", 8), fill="#333",
                         text="t = %.1f s   (×%g)" % (self.sim.now, self.sim.speed))

    def _draw_parts(self):
        p = self.parts
        if p["charger"]["on"]:
            x, y = p["charger"]["pos"]
            self.create_rectangle(x - 26, y - 18, x + 26, y + 18, fill="#222", outline="#000")
            self.create_text(x, y, text="5V", fill="#fff", font=("TkDefaultFont", 8))
            self._cable(x - 26, y, PORT_USB[0], PORT_USB[1] + 4, "#333")
        if p["cable"]["on"]:
            x, y = p["cable"]["pos"]
            self.create_rectangle(x - 20, y - 12, x + 20, y + 12, fill="#888", outline="#555")
            self.create_text(x, y, text="6-pin", font=("TkDefaultFont", 7))
            self._cable(x - 20, y, PORT_DATA[0], PORT_DATA[1] + 4, "#777")
            if p["tablet"]["on"]:
                tx, ty = p["tablet"]["pos"]
                self._cable(x + 20, y, tx, ty + 60, "#777")
        if p["tablet"]["on"]:
            x, y = p["tablet"]["pos"]
            self.create_rectangle(x - 70, y - 46, x + 70, y + 46, fill="#111", outline="#000",
                                  width=3, tags="tablet")
            self.create_rectangle(x - 63, y - 39, x + 63, y + 39, fill="#ccaaaa", outline="",
                                  tags="tablet")
            self.create_text(x, y, text="IPhO", font=("TkDefaultFont", 9, "bold"), fill="#3f51b5",
                             tags="tablet")
        if p["therm"]["on"]:
            x, y = p["therm"]["pos"]
            self.create_rectangle(x - 16, y - 54, x + 16, y + 54, fill="#fff", outline="#666")
            self.create_text(x, y - 20, text="%.1f" % self.board.room_T,
                             font=("TkDefaultFont", 11, "bold"))
            self.create_text(x, y, text="°C", font=("TkDefaultFont", 9))
            self.create_text(x, y + 34, text=T("roomT"), font=("TkDefaultFont", 6), width=30)

    def _cable(self, x0, y0, x1, y1, col):
        mx, my = (x0 + x1) / 2, max(y0, y1) + 40
        self.create_line(x0, y0, mx, my, x1, y1, smooth=True, width=3, fill=col)

    def _draw_wires(self):
        for name, w in self.wires.items():
            if not w["on"]:
                continue
            (x0, y0), (x1, y1) = w["p"]
            dx, dy = x1 - x0, y1 - y0
            L = max(1e-6, math.hypot(dx, dy))
            # sag perpendicular to the wire, always away from the terminal strip
            ox, oy = -dy / L, dx / L
            if ox * (0.5 * (x0 + x1) - 300) > 0:
                ox, oy = -ox, -oy
            bulge = min(110.0, 26.0 + 0.45 * L)
            mx, my = (x0 + x1) / 2 + ox * bulge, (y0 + y1) / 2 + oy * bulge
            self.create_line(x0, y0, mx, my, x1, y1, smooth=True, width=4, fill="#2a6fd6")
            if name == "W1":
                self.create_rectangle(mx - 16, my - 7, mx + 16, my + 7, fill="#e8e0c0",
                                      outline="#444")
                self.create_text(mx, my, text="100 MΩ", font=("TkDefaultFont", 6))
            else:
                self.create_text(mx, my - 12, text="W2 (0 Ω)", font=("TkDefaultFont", 7))
            for i, (x, y) in enumerate(w["p"]):
                self.create_oval(x - 7, y - 7, x + 7, y + 7, fill="#c0c0c8", outline="#333",
                                 width=2, tags=("wire:%s:%d" % (name, i),))

    def _socket_free(self, n):
        for w in self.board.wires.values():
            if n in w:
                return False
        return True

    # ------------------------------------------------------------- mouse
    def on_press(self, ev):
        for it in self.find_overlapping(ev.x - 3, ev.y - 3, ev.x + 3, ev.y + 3):
            for tg in self.gettags(it):
                if tg.startswith("tray:"):
                    self.toggle_part(tg[5:]); return
                if tg.startswith("wire:"):
                    _, nm, i = tg.split(":")
                    self.drag = ("wire", nm, int(i)); return
                if tg == "sw1":
                    b = self.board
                    b.sw1 = {"C1": "MID", "MID": "C2", "C2": "C1"}[b.sw1]
                    b.vb = [b.uC] * len(b.vb) if b.sw1 != "C2" else b.vb
                    self.refresh(); return
                if tg == "reset":
                    self.sim.firmware.reset()
                    self.sim.flash("RESET")
                    return
                if tg == "tablet":
                    self.sim.show_tablet(); return
        # dragging placed parts
        for key in ("charger", "cable", "tablet", "therm"):
            p = self.parts[key]
            if p["on"] and abs(ev.x - p["pos"][0]) < 40 and abs(ev.y - p["pos"][1]) < 50:
                self.drag = ("part", key, 0); return
        # insulating pad: click to take it off
        if self.parts["insul"]["on"] and 100 < ev.x < 282 and 240 < ev.y < 312:
            self.toggle_part("insul")

    def on_move(self, ev):
        if not self.drag:
            return
        kind, nm, i = self.drag
        x, y = max(6, min(self.W - 6, ev.x)), max(6, min(556, ev.y))
        if kind == "wire":
            self.wires[nm]["p"][i] = (x, y)
        else:
            self.parts[nm]["pos"] = (x, y)
        self.refresh()

    def on_release(self, ev):
        if self.drag and self.drag[0] == "wire":
            nm, i = self.drag[1], self.drag[2]
            x, y = self.wires[nm]["p"][i]
            best, bd = None, 22
            for n, (sx, sy, _l) in SOCKET_XY.items():
                d = math.hypot(sx - x, sy - y)
                if d < bd and (self._socket_free(n) or self.board.wires[nm][i] == n):
                    bd, best = d, n
            self.board.wires[nm][i] = best
            if best:
                self.wires[nm]["p"][i] = SOCKET_XY[best][:2]
        self.drag = None
        self.refresh()

    def toggle_part(self, key):
        if key in self.wires:
            w = self.wires[key]
            w["on"] = not w["on"]
            if not w["on"]:
                self.board.wires[key] = [None, None]
                w["p"] = [(660, 380 if key == "W1" else 420), (760, 380 if key == "W1" else 420)]
        else:
            p = self.parts[key]
            p["on"] = not p["on"]
            if key == "charger":
                self.board.powered = p["on"]
                if not p["on"]:
                    self.board.iH = self.board.iL = 0.0
            elif key == "cable":
                self.board.data_cable = p["on"] and self.parts["tablet"]["on"]
            elif key == "tablet":
                self.board.data_cable = p["on"] and self.parts["cable"]["on"]
                if p["on"]:
                    self.sim.show_tablet()
            elif key == "insul":
                self.board.insulation = p["on"]
        self.refresh()


# ============================================================================
#                            PROBLEM SHEET
# ============================================================================
TASKS_EN = """IPhO 2021 (Lithuania) — Experimental examination (5 h, 2×10 points)

EQUIPMENT (G1)
 1 Measurement and sample board: +9 V / -9 V sources (2 terminals each), 2 ground
   terminals, 2 capacitor (IN) terminals, capacitor selection switch S1 (C1 / C2),
   voltmeter with low input current, thermostat with heater and temperature sensor,
   sample capacitors C1 and C2, LED with constant current source and voltmeter,
   RESET button, USB power port, 6-PIN data port.
 2 USB power source.   3 Jumper wires W1 (100 MOhm resistor R1 inside) and W2 (0 Ohm).
 4 Heat insulating material.   5 Board-tablet cable.   6 Tablet with the app.
 7 Thermometer (in the examination hall).

 NTC thermistor:  R(T) = R0 * exp(B/T),  B = 3500 K,  R3 = 2.26 kOhm, supply 3.3 V,
 voltmeter reads the thermistor voltage uT (divider 3.3 V - R3 - R(T) - GND).

EXPERIMENT 1 — Non-ideal capacitors (10 pt)
 C(U) = dq/dU = I(U)/(dU/dt);   charging through R1 from a source Uf:
 C(U) = (Uf - U(t))/R1 / (dU/dt)
 Caution: when measuring at positive voltages charge the capacitor from 9 V down to
 -9 V, at negative voltages from -9 V towards 9 V; keep it at the starting voltage
 for at least 10 s before the measurement.
 A.1 (2.3) Measure and graph C1(U) and C2(U) from -7 V to 7 V; write C1, C2 at
     0 V, 3 V, 6 V, the formula used, Board ID and room temperature.
 A.2 (0.5) Find U_max change where (dC/(C dU)) is fastest; which capacitor, which voltage.
 A.3 (1.2) Charges q1 and q2 of C1 and C2 at 6 V.
 B.1 (1.0) Find the NTC thermistor constant R0.
 C.1 (1.3) C1(U), C2(U) from -7 V to 7 V at 40, 65 and 85 C.
 C.2 (0.5) Graph C1(T) and C2(T) at 0 V and 6 V up to 85 C.
 C.3 (1.2) Ratio C(85 C)/C(40 C) for both capacitors at 0 V and 6 V.
 D.1 (1.0) Main source of error for measuring C1(9 V)?  Write the measurement steps.
 D.2 (1.0) Main source of error for measuring C2(9 V)?  Write the measurement steps.
     (1 = leakage current, 2 = polarization of the dielectric.  Remove the insulating
      material when doing leakage measurements.)

EXPERIMENT 2 — Light Emitting Diodes (10 pt)
 T(U) = 3500 / (9.9 - ln(1/U - 0.3))   [K], U = thermistor voltage.
 dT/P = (Tj - Tpcb)/P.   Pulsed drive (1 ms, >=100 ms apart) => Tj = Tpcb.
 A.1 (2.5) Graph I_LED_pulsed(U_LED_pulsed, T) from 3 to 50 mA at room temperature
     and at 40, 60, 80 C (all curves on one graph).
 A.2 (1.0) Table of U_LED_pulsed at 3, 10, 20, 40 mA for those four temperatures.
 A.3 (1.5) Graph U(I,T) and find dU(I)/dT at 3, 10, 20 and 40 mA.
 B.1 (1.5) Graph I_LED_continuous(U_LED_continuous) from 3 to 50 mA, heater off;
     write U_continuous, Tpcb and dU = U_pulsed - U_continuous at 3, 10, 20, 40 mA.
 B.2 (0.5) dI/dU (reciprocal dynamic resistance) at 3, 10, 20 and 40 mA.
 B.3 (1.5) Graph dT(P) and find the thermal resistance dT/P.
 C.1 (1.5) With U kept at U(20 mA) of B.1, estimate the LED current at Tpcb = 0 C and 40 C.
"""

TASKS_KO = """IPhO 2021 (리투아니아) — 실험 시험 (5시간, 2×10점)

장비 (G1)
 1 측정·시료 보드: +9 V / -9 V 전원(각 2단자), 접지 2단자, 커패시터(IN) 2단자,
   커패시터 선택 스위치 S1 (C1 / C2), 입력전류가 작은 전압계, 히터와 온도센서를
   가진 항온조, 시료 커패시터 C1·C2, 정전류원과 전압계에 연결된 LED,
   RESET 버튼, USB 전원 포트, 6핀 데이터 포트.
 2 USB 전원.  3 점퍼선 W1(내부에 100 MΩ 저항 R1)과 W2(0 Ω).
 4 단열재.  5 보드–태블릿 케이블.  6 앱이 설치된 태블릿.  7 온도계(시험장).

 NTC 서미스터:  R(T) = R0·exp(B/T),  B = 3500 K,  R3 = 2.26 kΩ, 전원 3.3 V.

실험 1 — 비이상적 커패시터 (10점)
 C(U) = dq/dU = I(U)/(dU/dt),  R1을 통해 전원 Uf로 충전할 때
 C(U) = (Uf - U(t))/R1 / (dU/dt)
 주의: 양의 전압 구간은 9 V → -9 V로 방전하며, 음의 전압 구간은 -9 V → 9 V로
 충전하며 측정한다. 측정 전 시작 전압에서 최소 10초 유지할 것.
 A.1 (2.3) -7 V ~ 7 V에서 C1(U), C2(U) 측정·작도. 0 V, 3 V, 6 V에서의 값,
     사용한 식, 보드 ID, 실온을 기입.
 A.2 (0.5) (dC/(C·dU))가 최대인 전압 U_max change 와 해당 커패시터.
 A.3 (1.2) 6 V에서 C1, C2의 전하량 q1, q2.
 B.1 (1.0) NTC 상수 R0.
 C.1 (1.3) 40, 65, 85 °C에서 C1(U), C2(U).
 C.2 (0.5) 0 V와 6 V에서 C1(T), C2(T).
 C.3 (1.2) 0 V와 6 V에서 C(85 °C)/C(40 °C).
 D.1 (1.0) C1(9 V) 측정의 주된 오차 원인과 측정 절차.
 D.2 (1.0) C2(9 V) 측정의 주된 오차 원인과 측정 절차.
     (1 = 누설전류, 2 = 유전체 분극. 누설 측정 시 단열재를 제거할 것.)

실험 2 — 발광 다이오드 (10점)
 T(U) = 3500 / (9.9 - ln(1/U - 0.3)) [K].  ΔT/P = (Tj - Tpcb)/P.
 펄스 구동(1 ms, 100 ms 이상 간격) ⇒ Tj = Tpcb.
 A.1 (2.5) 실온, 40, 60, 80 °C에서 3~50 mA의 I(U) 곡선 (한 그래프에).
 A.2 (1.0) 3, 10, 20, 40 mA에서의 U_pulsed 표.
 A.3 (1.5) 3, 10, 20, 40 mA에서 dU(I)/dT.
 B.1 (1.5) 히터를 끈 상태에서 연속 구동 I(U) 곡선, U_continuous, Tpcb,
     ΔU = U_pulsed - U_continuous.
 B.2 (0.5) 3, 10, 20, 40 mA에서 dI/dU.
 B.3 (1.5) ΔT(P) 그래프와 열저항 ΔT/P.
 C.1 (1.5) B.1의 U(20 mA)로 전압을 고정했을 때 Tpcb = 0 °C, 40 °C에서의 전류.
"""


# ============================================================================
#                                  APP
# ============================================================================
# ============================================================================
#   THE APP ON YOUR OWN DEVICE
#   A tiny web server on this computer hands out the IPhO 2021 Experiments
#   app (the same page as the web edition) to any browser on the same
#   network; the page polls the board here for samples and posts its
#   commands back.  The board firmware below mirrors the web edition.
# ============================================================================
def _lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


class RemoteLink:
    def __init__(self, sim):
        self.sim = sim
        self.lock = threading.Lock()
        self.inbox, self.outbox, self.seq, self.seen = [], [], 0, 0.0
        self.server, self.port = None, None

    def start(self):
        if self.server:
            return True
        for port in range(8021, 8041):
            try:
                self.server = ThreadingHTTPServer(("0.0.0.0", port), self._handler())
                self.port = port
                break
            except OSError:
                continue
        if not self.server:
            return False
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return True

    def urls(self):
        q = "/app?py=1&lang=" + LANG.lower()
        return ["http://%s:%d%s" % (_lan_ip(), self.port, q), "http://localhost:%d%s" % (self.port, q)]

    def _handler(self):
        link = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, body, ctype):
                b = body.encode("utf-8") if isinstance(body, str) else body
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def do_GET(self):
                u = urlparse(self.path)
                if u.path == "/":
                    self.send_response(302)
                    self.send_header("Location", "/app?py=1&lang=" + LANG.lower())
                    self.end_headers()
                elif u.path in ("/app", "/ipho2021_app.html"):
                    self._send(200, APP_HTML, "text/html; charset=utf-8")
                elif u.path == "/ipho2021_app_icon.png":
                    self._send(200, base64.b64decode(APP_ICON), "image/png")
                elif u.path == "/ipho2021_app.webmanifest":
                    self._send(200, APP_MANIFEST, "application/manifest+json")
                elif u.path == "/poll":
                    try:
                        since = int(parse_qs(u.query).get("since", ["0"])[0])
                    except ValueError:
                        since = 0
                    with link.lock:
                        link.seen = time.time()
                        msgs = [m for (n, m) in link.outbox if n > since]
                        seq = link.seq
                    self._send(200, json.dumps({"seq": seq, "msgs": msgs}), "application/json")
                else:
                    self._send(404, "not found", "text/plain")

            def do_POST(self):
                if urlparse(self.path).path != "/cmd":
                    self._send(404, "", "text/plain")
                    return
                n = int(self.headers.get("Content-Length", "0") or 0)
                try:
                    m = json.loads(self.rfile.read(n).decode("utf-8"))
                except ValueError:
                    m = None
                if isinstance(m, dict):
                    with link.lock:
                        link.inbox.append(m)
                        if m.get("type") != "bye":
                            link.seen = time.time()
                self._send(200, "{}", "application/json")
        return H

    def alive(self):
        return time.time() - self.seen < 3.0

    def to_app(self, m):
        if m.get("type") == "frames":          # bytes on the wire -> base64 like the web edition
            m = {"type": "frames", "list": [base64.b64encode(f).decode("ascii") for f in m["list"]]}
        with self.lock:
            self.seq += 1
            self.outbox.append((self.seq, m))
            if len(self.outbox) > 3000:
                del self.outbox[:1000]

    def handle(self):
        with self.lock:
            msgs, self.inbox = self.inbox, []
        for m in msgs:
            if m.get("type") == "bye":
                self.seen = 0.0
            self.sim.firmware.handle(m)


class Sim:
    TICK_MS = 25
    MAX_DT = 0.010

    def __init__(self, root):
        self.root = root
        self.board = Board()
        self.now = 0.0
        self.speed = 1.0
        self.tablet = None
        self.mode = None            # "virtual" | "remote"
        self.link = RemoteLink(self)
        self.firmware = Firmware(self)
        self.remote_win = None
        root.title(T("title"))
        self._menu()
        self.bench = Bench(root, self)
        self.bench.pack(side="top", fill="both", expand=True)
        self.msg = tk.Label(root, text="", anchor="w", fg="#036")
        self.msg.pack(fill="x")
        self._last_real = time.perf_counter()
        self._acc = 0.0
        self.loop()
        root.after(300, self.ask_mode)

    # ------------------------------------------------------------------
    def _menu(self):
        m = tk.Menu(self.root)
        v = tk.Menu(m, tearoff=0)
        v.add_command(label=T("open_tablet"), command=self.show_tablet)
        v.add_command(label=T("menu_link"), command=self.ask_mode)
        v.add_command(label=T("open_tasks"), command=self.show_tasks)
        v.add_separator()
        v.add_command(label=T("reset_bench"), command=self.reset_bench)
        m.add_cascade(label=T("menu_view"), menu=v)
        s = tk.Menu(m, tearoff=0)
        for sp in (1, 2, 5, 10, 30):
            s.add_command(label=T("speed_x", sp), command=lambda sp=sp: self.set_speed(sp))
        m.add_cascade(label=T("menu_speed"), menu=s)
        lg = tk.Menu(m, tearoff=0)
        lg.add_command(label="English", command=lambda: self.set_lang("EN"))
        lg.add_command(label="한국어", command=lambda: self.set_lang("KO"))
        m.add_cascade(label=T("menu_lang"), menu=lg)
        self.root.config(menu=m)

    def set_speed(self, s):
        self.speed = s
        self.bench.refresh()

    def set_lang(self, lg):
        global LANG
        if LANG == lg:
            return
        LANG = lg
        self.bench.destroy()
        self._menu()
        self.root.title(T("title"))
        self.bench = Bench(self.root, self)
        self.bench.pack(side="top", fill="both", expand=True)

    def flash(self, txt):
        self.msg.config(text=txt)
        self.root.after(1500, lambda: self.msg.config(text=""))

    def reset_bench(self):
        self.board = Board()
        self.bench.destroy()
        self.bench = Bench(self.root, self)
        self.bench.pack(side="top", fill="both", expand=True)
        self.firmware.run = None

    def ask_mode(self):
        w = tk.Toplevel(self.root)
        w.title(T("start_title"))
        w.transient(self.root)
        w.configure(padx=18, pady=14)
        tk.Label(w, text=T("start_title"), font=("TkDefaultFont", 12, "bold"), anchor="w").pack(fill="x")
        tk.Label(w, text=T("start_text"), justify="left", wraplength=520, anchor="w").pack(fill="x", pady=(6, 12))
        row = tk.Frame(w)
        row.pack(fill="x")
        tk.Button(row, text=T("use_virtual"), width=28,
                  command=lambda: (w.destroy(), self.set_mode("virtual"))).pack(side="left", padx=(0, 8))
        tk.Button(row, text=T("use_remote"), width=32,
                  command=lambda: (w.destroy(), self.set_mode("remote"))).pack(side="left")
        w.grab_set()

    def set_mode(self, mode):
        self.mode = mode
        if mode == "virtual":
            if self.remote_win is not None and self.remote_win.winfo_exists():
                self.remote_win.withdraw()
            self.show_tablet()
            return
        if self.tablet is not None and self.tablet.winfo_exists():
            self.tablet.ask_to_stop()
            self.tablet.app_running = False
            self.tablet.withdraw()
        self.firmware.run = None
        self.firmware.usb = False
        self.firmware.sink = self.link.to_app
        self.show_remote()

    def show_remote(self):
        if self.remote_win is not None and self.remote_win.winfo_exists():
            self.remote_win.deiconify()
            self.remote_win.lift()
            return
        w = self.remote_win = tk.Toplevel(self.root)
        w.title(T("remote_title"))
        w.configure(padx=16, pady=12)
        if not self.link.start():
            tk.Label(w, text=T("remote_fail"), fg="#b03020").pack()
            return
        tk.Label(w, text=T("remote_text"), justify="left", wraplength=520, anchor="w").pack(fill="x")
        for u in self.link.urls():
            e = tk.Entry(w, width=58, font=("TkFixedFont", 11))
            e.insert(0, u)
            e.configure(state="readonly")
            e.pack(fill="x", pady=3)
        tk.Button(w, text=T("open_browser"), command=lambda: webbrowser.open(self.link.urls()[1])).pack(anchor="w", pady=(6, 4))
        self.remote_status = tk.Label(w, text=T("remote_wait"), fg="#9a6a00", font=("TkDefaultFont", 10, "bold"))
        self.remote_status.pack(anchor="w")

    def show_tablet(self):
        if self.mode == "remote":
            self.show_remote()
            return
        if self.tablet is None or not self.tablet.winfo_exists():
            self.firmware.usb = False
            self.tablet = Tablet(self.root, self)
        elif not self.tablet.app_running:      # launched again from the home screen
            self.firmware.usb = False
            self.tablet.launch()
        self.tablet.deiconify()
        self.tablet.lift()

    def show_tasks(self):
        w = tk.Toplevel(self.root)
        w.title(T("tasks_hdr"))
        t = tk.Text(w, width=96, height=42, wrap="word", font=("TkFixedFont", 9))
        t.pack(fill="both", expand=True)
        t.insert("1.0", TASKS_EN if LANG == "EN" else TASKS_KO)
        t.config(state="disabled")

    # ------------------------------------------------------------------
    def loop(self):
        real = time.perf_counter()
        dtr = min(0.25, real - self._last_real)
        self._last_real = real
        want = dtr * self.speed
        n = max(1, int(math.ceil(want / self.MAX_DT)))
        n = min(n, 400)
        dt = want / n
        remote = self.mode == "remote" and self.link.server is not None
        if remote:
            self.link.handle()
        for k in range(n):
            self.board.step(dt)
            self.firmware.step(self.now + (k + 1) * dt)
        self.now += want
        self.firmware.flush()
        if remote:
            if self.remote_win is not None and self.remote_win.winfo_exists() and hasattr(self, "remote_status"):
                ok = self.link.alive()
                self.remote_status.config(text=T("remote_ok") if ok else T("remote_wait"), fg="#1e8449" if ok else "#9a6a00")
        elif self.tablet is not None and self.tablet.winfo_exists():
            self.tablet.tick_draw()
        self._acc += dtr
        if self._acc > 0.15:
            self._acc = 0.0
            self.bench.refresh()
        self.root.after(self.TICK_MS, self.loop)


def _setup_hangul_font(root):
    """Point every named Tk font at a family that has Hangul."""
    import tkinter.font as _tkfont
    want = ("Malgun Gothic", "AppleGothic", "Apple SD Gothic Neo",
            "NanumGothic", "NanumBarunGothic", "Noto Sans CJK KR",
            "Noto Sans KR", "UnDotum", "Gulim", "Batang")
    have = set(_tkfont.families(root))
    fam = next((f for f in want if f in have), None)
    if not fam:
        return
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont",
                 "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont",
                 "TkIconFont", "TkTooltipFont"):
        try:
            _tkfont.nametofont(name, root).configure(family=fam)
        except Exception:
            pass


# The IPhO 2021 Experiments app page served to your own device (same as sim/ipho2021_app.html of the web edition)
APP_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<meta name="theme-color" content="#000000">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="IPhO">
<link rel="manifest" href="ipho2021_app.webmanifest">
<link rel="icon" href="ipho2021_app_icon.png" type="image/png">
<link rel="apple-touch-icon" href="ipho2021_app_icon.png">
<title>IPhO · IPhO 2021 Experiments · HaslaLab</title>
<meta name="description" content="The IPhO 2021 Experiments app (com.smm.ipholab, version 1.01) rebuilt for the HaslaLab virtual measurement board: open it on your own tablet, phone or computer and connect it to the simulator.">
<style>
  *{box-sizing:border-box}
  [hidden]{display:none!important}
  html,body{margin:0;padding:0;height:100%;overflow:hidden;background:#000}
  body{font-family:Roboto,"Noto Sans","Segoe UI","Helvetica Neue",Arial,"Malgun Gothic",sans-serif;-webkit-tap-highlight-color:transparent;user-select:none;-webkit-user-select:none;touch-action:manipulation}
  input{user-select:text;-webkit-user-select:text}
  /* the tablet's screen in dp: the app is laid out exactly as its XML layouts, then scaled */
  #scr{position:absolute;left:0;top:0;transform-origin:0 0;overflow:hidden;background:#ccaaaa;color:rgba(0,0,0,.87)}
  .act{position:absolute;left:0;top:0;background:#ccaaaa;overflow:hidden}
  #nav{position:absolute;left:0;bottom:0;width:100%;height:48px;background:#000;display:flex;justify-content:space-around;align-items:center}
  #nav span{width:48px;height:48px;display:flex;align-items:center;justify-content:center;cursor:pointer}
  /* widgets (Material, API 28) */
  .sw{position:absolute;display:flex;align-items:center;font-size:16px;cursor:pointer;height:45px}
  .sw i{position:relative;display:inline-block;width:36px;height:14px;border-radius:7px;background:rgba(0,0,0,.38);margin-left:9px}
  .sw i:after{content:"";position:absolute;left:-3px;top:-3px;width:20px;height:20px;border-radius:50%;background:#ececec;box-shadow:0 1px 3px rgba(0,0,0,.45);transition:left .12s}
  .sw.on i{background:rgba(238,102,85,.5)}.sw.on i:after{left:19px;background:#ee6655}
  .et{position:absolute;border:0;border-bottom:1px solid rgba(0,0,0,.45);background:transparent;font:inherit;font-size:12px;color:rgba(0,0,0,.87);padding:6px 0 5px;outline:none;border-radius:0}
  .et:focus{border-bottom:2px solid #ee6655;padding-bottom:4px}
  .et::placeholder{color:rgba(0,0,0,.38)}
  .et:disabled{color:rgba(0,0,0,.38);border-bottom-style:dotted}
  .btn{position:absolute;background:#998888;border:0;margin:0;padding:0 16px;font:inherit;font-size:16px;color:rgba(0,0,0,.87);min-width:88px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:flex;align-items:center;justify-content:center}
  .btn.caps{z-index:2;box-shadow:0 2px 2px rgba(0,0,0,.24);text-transform:uppercase;font-weight:500;font-size:14px;letter-spacing:.03em}
  .btn:active,.ib:active,.key:active{filter:brightness(.88)}
  .ib{position:absolute;width:40px;height:40px;background:#998888;display:flex;align-items:center;justify-content:center;cursor:pointer}
  .lbl{position:absolute;font-size:14px;color:rgba(0,0,0,.87);white-space:nowrap}
  .sb{position:absolute;height:32px;cursor:pointer;touch-action:none}
  .sb .tr{position:absolute;left:16px;right:16px;top:15px;height:2px;background:rgba(0,0,0,.26)}
  .sb .pr{position:absolute;left:16px;top:15px;height:2px;background:#ee6655}
  .sb .th{position:absolute;top:10px;width:12px;height:12px;margin-left:-6px;border-radius:50%;background:#ee6655}
  .sb.off{opacity:.38;pointer-events:none}
  /* table */
  #tbl{position:absolute;left:0;top:192px;width:480px;height:360px;background:#ddccbb;overflow-y:scroll;overflow-x:hidden}
  #tbl table{border-collapse:separate;border-spacing:0;margin:0 8px}
  #tbl td{font-size:18px;padding:0;white-space:nowrap;vertical-align:top;line-height:1.3}
  #tbl td{padding-right:8px}#tbl td:last-child{padding-right:0}
  #tbl .hb{position:static;height:40px}
  /* chart */
  #chart{position:absolute;left:488px;top:60px;width:464px;height:484px;touch-action:none}
  /* toast */
  #toasts{position:absolute;left:0;right:0;bottom:72px;display:flex;justify-content:center;pointer-events:none;z-index:40}
  .toast{background:rgba(50,50,50,.92);color:#fff;font-size:14px;line-height:1.35;padding:12px 18px;border-radius:24px;max-width:80%;text-align:center;white-space:pre-line;box-shadow:0 2px 6px rgba(0,0,0,.3)}
  .toast.big{font-size:32px;border-radius:30px;padding:16px 26px}
  /* dialogs (AppCompat AlertDialog) */
  .dim{position:absolute;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:30}
  .dlg{background:#fff;border-radius:2px;box-shadow:0 11px 15px rgba(0,0,0,.2),0 24px 38px rgba(0,0,0,.14);display:flex;flex-direction:column;color:rgba(0,0,0,.87)}
  .dlg h3{margin:0;padding:24px 24px 0;font-size:20px;font-weight:500}
  .dlg .msg{padding:16px 24px 0;font-size:16px;color:rgba(0,0,0,.6)}
  .dlg .lst{flex:1;overflow-y:auto;padding:8px 0}
  .dlg .it{display:flex;align-items:center;min-height:48px;padding:0 24px;font-size:16px;cursor:pointer;gap:32px}
  .dlg .rad{width:20px;height:20px;border-radius:50%;border:2px solid rgba(0,0,0,.54);flex:none;position:relative}
  .dlg .it.on .rad{border-color:#ee6655}.dlg .it.on .rad:after{content:"";position:absolute;inset:3px;border-radius:50%;background:#ee6655}
  .dlg .chk{width:18px;height:18px;border-radius:2px;border:2px solid rgba(0,0,0,.54);flex:none;display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;font-weight:700}
  .dlg .it.on .chk{background:#ee6655;border-color:#ee6655}
  .dlg .bar{display:flex;justify-content:flex-end;gap:8px;padding:8px 16px 8px}
  .dlg .bar span{color:#ee6655;font-size:14px;font-weight:500;text-transform:uppercase;letter-spacing:.04em;padding:10px 8px;cursor:pointer}
  .dlg .bar span.off{opacity:.38}
  .dlg input{margin:12px 24px 0;font:inherit;font-size:18px;border:0;border-bottom:2px solid #ee6655;outline:none;padding:4px 0;background:transparent}
  .dlg .cbx{display:flex;align-items:center;gap:16px;padding:16px 24px 0;font-size:14px;cursor:pointer}
  /* settings (PreferenceFragmentCompat) */
  #actSet{overflow-y:auto}
  .pref{position:relative;padding:16px 16px 16px 72px;min-height:72px;cursor:pointer;display:flex;align-items:center}
  .pref .tx{flex:1}.pref b{display:block;font-weight:400;font-size:16px;color:rgba(0,0,0,.87)}.pref small{display:block;font-size:14px;color:rgba(0,0,0,.54);margin-top:2px}
  .pref.off{cursor:default}.pref.off b,.pref.off small{color:rgba(0,0,0,.38)}
  .pref .sw{position:static;height:auto;margin-left:16px}.pref .sw i{margin:0}
  .pref.off .sw{opacity:.38}
  .pcat{padding:16px 16px 0 72px;font-size:14px;font-weight:500;color:#ee6655;border-top:1px solid rgba(0,0,0,.12);margin-top:8px;height:40px}
  /* function editor (portrait) */
  .key{position:absolute;background:#998888;font-size:30px;line-height:1;display:flex;align-items:center;cursor:pointer;padding:0 2px;color:rgba(0,0,0,.87)}
  #eqTxt{position:absolute;left:16px;top:214px;width:568px;font-size:24px;padding:8px 0 6px;border:0;border-bottom:2px solid #ee6655;background:transparent;outline:none;color:rgba(0,0,0,.87);font-family:inherit}
  #eqTxt.bad{border-bottom-color:#d50000}
  /* the pairing screen (HaslaLab, not part of the original app) */
  #conn{position:fixed;inset:0;background:#2b2f36;display:flex;align-items:center;justify-content:center;z-index:60;padding:16px;font-family:-apple-system,"Segoe UI",Roboto,"Malgun Gothic",sans-serif;overflow:auto}
  .cbox{background:#fff;border-radius:12px;padding:22px 24px;max-width:460px;width:100%;box-shadow:0 8px 24px rgba(0,0,0,.25);user-select:text}
  .cbox .hd{display:flex;align-items:center;gap:12px;margin-bottom:6px}.cbox .hd img{width:48px;height:48px}
  .cbox h2{margin:0;font-size:18px;color:#222}.cbox h2 small{display:block;font-size:12px;color:#777;font-weight:400}
  .cbox p{margin:8px 0;color:#444;font-size:13.5px;line-height:1.55}
  .cbox input{font:600 24px ui-monospace,Consolas,monospace;letter-spacing:.25em;text-transform:uppercase;width:100%;padding:8px 10px;border:1px solid #bbb;border-radius:6px;text-align:center;margin:8px 0}
  .cbox button{width:100%;padding:11px;border-radius:6px;border:0;background:#ee6655;color:#fff;font-weight:700;font-size:15px;cursor:pointer}
  .cbox button:disabled{opacity:.6}
  .cbox .st{margin-top:10px;font-weight:600;color:#b03020;min-height:1.4em;font-size:13.5px}
  .cbox .small{font-size:12px;color:#777}
  .cbox .lg{float:right;font-size:12px}.cbox .lg a{color:#ee6655;cursor:pointer;margin-left:6px;text-decoration:none}
  #closed{position:fixed;inset:0;background:#111;color:#ccc;display:flex;flex-direction:column;gap:16px;align-items:center;justify-content:center;z-index:55;font-size:15px}
  #closed img{width:72px}#closed button{padding:10px 22px;border-radius:6px;border:0;background:#ee6655;color:#fff;font-size:14px;cursor:pointer}
</style>
</head>
<body>
<div id="scr">
  <!-- ═════════════ MainActivity (activity_main.xml, landscape 960 × 552 dp) ═════════════ -->
  <div class="act" id="actMain" style="width:960px;height:552px">
    <div class="sw" id="swMeas" style="left:8px;top:8px">Measure<i></i></div>
    <input class="et" id="etTitle" placeholder="Measurement title" style="left:126px;top:13px;width:100px" maxlength="60" spellcheck="false" autocomplete="off">
    <div class="ib" id="ibAdd" style="left:234px;top:8px" title="+"><svg width="28" height="28" viewBox="0 0 28 28"><path d="M11.5 4h5v7.5H24v5h-7.5V24h-5v-7.5H4v-5h7.5z" fill="#86c440"/></svg></div>
    <div class="ib" id="ibDel" style="left:282px;top:8px" title="✖"><svg width="26" height="26" viewBox="0 0 26 26"><path d="M5 8.5 8.5 5 13 9.5 17.5 5 21 8.5 16.5 13 21 17.5 17.5 21 13 16.5 8.5 21 5 17.5 9.5 13z" fill="#e8175d"/></svg></div>
    <div class="btn" id="btMeas" style="left:330px;top:6px;height:40px;width:128px;padding:0 10px">✎ measurements</div>
    <div class="sw" id="swCheck" style="left:8px;top:61px;height:32px">Check state<i></i></div>
    <div class="ib" id="ibSet" style="left:8px;top:101px" title="settings"><svg width="30" height="30" viewBox="0 0 30 30"><path d="M21.6 4.4a6 6 0 0 0-7.4 7.6L4.6 21.6a2 2 0 0 0 0 2.8l1 1a2 2 0 0 0 2.8 0l9.6-9.6a6 6 0 0 0 7.6-7.4l-3.7 3.7-3.2-.9-.9-3.2z" fill="none" stroke="#5f5f5f" stroke-width="1.6" stroke-linejoin="round"/></svg></div>
    <div class="ib" id="ibInfo" style="left:56px;top:101px" title="info"><svg width="28" height="28" viewBox="0 0 28 28"><circle cx="14" cy="14" r="10.5" fill="none" stroke="#5f5f5f" stroke-width="1.6"/><circle cx="14" cy="9" r="1.6" fill="#5f5f5f"/><path d="M12.6 12.5h2.8v8h-2.8z" fill="#5f5f5f"/></svg></div>
    <div class="ib" id="ibCopy" style="left:104px;top:101px;background:#3f51b5" hidden title="copy"><svg width="22" height="22" viewBox="0 0 24 24"><path d="M16 1H4a2 2 0 0 0-2 2v14h2V3h12zm3 4H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 16H8V7h11z" fill="#fff"/></svg></div>
    <div class="btn" id="btFx" style="left:8px;top:149px;height:40px">✎ f(x)</div>
    <span class="lbl" id="lbIH" style="left:154px;top:69px;height:22px;line-height:22px;padding:0 1px">i<sub>H</sub>=</span>
    <input class="et" id="etIH" placeholder="0..500" inputmode="decimal" style="left:180px;top:63px;width:54px">
    <span class="lbl" style="left:236px;top:69px;line-height:22px">mA</span>
    <div class="sb" id="sbIH" style="left:266px;top:64px;width:214px"></div>
    <div class="btn caps" id="btApply" style="left:270px;top:96px;height:40px" hidden>Apply</div>
    <div class="btn caps" id="btCancel" style="left:374px;top:96px;height:40px" hidden>Cancel</div>
    <span class="lbl" id="lbIL" style="left:154px;top:106px;height:22px;line-height:22px;padding:0 1px">i<sub>L</sub>=</span>
    <input class="et" id="etIL" placeholder="0..50" inputmode="decimal" style="left:180px;top:100px;width:54px">
    <span class="lbl" id="unIL" style="left:236px;top:106px;line-height:22px">mA</span>
    <div class="sb" id="sbIL" style="left:266px;top:101px;width:214px"></div>
    <span class="lbl" id="lbTL" style="left:154px;top:143px;height:22px;line-height:22px;padding:0 1px">t<sub>L</sub>=</span>
    <input class="et" id="etTL" placeholder="0.1..25.5" inputmode="decimal" style="left:180px;top:137px;width:54px">
    <span class="lbl" id="unTL" style="left:236px;top:143px;line-height:22px">ms</span>
    <div class="sb" id="sbTL" style="left:266px;top:138px;width:214px"></div>
    <div id="tbl"><table><tbody id="tb"><tr id="thr"><td class="h"><div class="btn hb" data-h="0">f(x)</div></td><td class="h"><div class="btn hb" data-h="1">f(x)</div></td><td class="h"><div class="btn hb" data-h="2">f(x)</div></td></tr></tbody></table></div>
    <div class="ib" id="ibReplot" style="left:488px;top:10px" title="replot"><svg width="28" height="28" viewBox="0 0 24 24"><path d="M12 4V1L8 5l4 4V6a6 6 0 0 1 5.65 8.03l1.47 1.47A8 8 0 0 0 12 4zm0 14a6 6 0 0 1-5.65-8.03L4.88 8.5A8 8 0 0 0 12 20v3l4-4-4-4z" fill="#cfcfcf"/></svg></div>
    <span class="lbl" style="left:536px;top:24px">X =</span><input class="et" id="etXmin" inputmode="decimal" style="left:568px;top:17px;width:60px">
    <span class="lbl" style="left:636px;top:24px">...</span><input class="et" id="etXmax" inputmode="decimal" style="left:656px;top:17px;width:60px">
    <span class="lbl" style="left:740px;top:24px">Y = </span><input class="et" id="etYmin" inputmode="decimal" style="left:776px;top:17px;width:60px">
    <span class="lbl" style="left:844px;top:24px">...</span><input class="et" id="etYmax" inputmode="decimal" style="left:864px;top:17px;width:60px">
    <canvas id="chart"></canvas>
  </div>
  <!-- ═════════════ SettingsActivity (preferences.xml) ═════════════ -->
  <div class="act" id="actSet" style="width:960px;height:552px" hidden></div>
  <!-- ═════════════ EquationEditorActivity (activity_equation_editor.xml, portrait 600 × 912 dp) ═════════════ -->
  <div class="act" id="actEq" style="width:600px;height:912px" hidden>
    <div id="eqKeys"></div>
    <div class="ib" id="eqAdd" style="left:18px;top:132px;width:70px;height:70px"><svg width="34" height="34" viewBox="0 0 28 28"><path d="M11.5 4h5v7.5H24v5h-7.5V24h-5v-7.5H4v-5h7.5z" fill="#86c440"/></svg></div>
    <div class="ib" id="eqDel" style="left:99px;top:132px;width:70px;height:70px"><svg width="32" height="32" viewBox="0 0 26 26"><path d="M5 8.5 8.5 5 13 9.5 17.5 5 21 8.5 16.5 13 21 17.5 17.5 21 13 16.5 8.5 21 5 17.5 9.5 13z" fill="#e8175d"/></svg></div>
    <div class="ib" id="eqSel" style="left:179px;top:132px;width:70px;height:70px"><svg width="32" height="32" viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75z" fill="none" stroke="#f5f5f5" stroke-width="1.4"/></svg></div>
    <input id="eqTxt" placeholder="Enter function" spellcheck="false" autocomplete="off" autocapitalize="off">
  </div>
  <div id="toasts"></div>
  <div id="dlgs"></div>
  <div id="nav" hidden>
    <span id="navBack"><svg width="20" height="20" viewBox="0 0 20 20"><path d="M15 3v14L4 10z" fill="#fff"/></svg></span>
    <span id="navHome"><svg width="18" height="18" viewBox="0 0 18 18"><circle cx="9" cy="9" r="7.5" fill="#fff"/></svg></span>
    <span id="navRec"><svg width="16" height="16" viewBox="0 0 16 16"><rect x="1" y="1" width="14" height="14" rx="1.5" fill="#fff"/></svg></span>
  </div>
</div>

<div id="conn" hidden>
  <div class="cbox">
    <div class="lg"><a id="lgKo">한국어</a><a id="lgEn">English</a></div>
    <div class="hd"><img src="ipho2021_app_icon.png" alt=""><h2>IPhO<small>IPhO 2021 Experiments · com.smm.ipholab 1.01</small></h2></div>
    <p id="cP"></p>
    <input id="cCode" maxlength="6" autocomplete="off" spellcheck="false">
    <button id="cGo"></button>
    <div class="st" id="cSt"></div>
    <p class="small" id="cSmall"></p>
  </div>
</div>
<div id="closed" hidden><img src="ipho2021_app_icon.png" alt=""><span id="clTxt"></span><button id="clOpen">IPhO</button></div>

<script>
"use strict";
/* ══════════════════════════════════════════════════════════════════════════
   IPhO 2021 EXPERIMENTS  —  the examination tablet's app, rebuilt for HaslaLab

   The original is the Android package com.smm.ipholab.ipho.smm.ipho2020,
   versionName 1.01 (minSdk 26, targetSdk 28), written for IPhO 2021 by its
   organisers.  This page follows its decompiled code (MainActivity,
   Measurement, Calc, Converter, UsbProtocol, ChartHandler, TableHandler,
   EquationEditorActivity, preferences.xml, activity_main.xml ...):
     - the board answers every request with a 30-byte frame (STM32, USB
       serial 115200 8N1, CRC32): uT, uL 16 bit over 0..3.3 V, uC 24 bit over
       -10.05..+10.05 V, heater DAC/ADC, LED current with its 1 mA range bit,
       and the ADC clock in 10 ms ticks; the app converts them exactly as
       Converter.java does;
     - duC, duT, duL are worked out by the app (two-point while measuring,
       three-point when a stored measurement is loaded), as Calc.java does;
     - functions are parsed like exp4j (implicit multiplication, ln, log10,
       pi, e ...), a division by zero gives 1e12;
     - the measurement thread asks every 140 ms (the "Time step" setting is
       shown but the code reads another key, so it never changes it);
     - the sweep sets LED currents from Calc.getSweepArray, skipping the
       answer that follows a change of the 1 mA range;
     - measurements are stored raw (17 bytes per sample) and replayed.
   Only the link differs: instead of a USB cable it talks to the HaslaLab
   board over postMessage (the virtual tablet), BroadcastChannel (a window
   on the same computer), WebRTC/PeerJS (your own tablet, phone or
   computer) or HTTP (the Python edition).
   ══════════════════════════════════════════════════════════════════════════ */
const Q=new URLSearchParams(location.search);
const EMBED=Q.get("embed")==="1", PY=Q.get("py")==="1";
let lang=(Q.get("lang")||((navigator.language||"").startsWith("ko")?"ko":"en"))==="ko"?"ko":"en";
const $=id=>document.getElementById(id);

/* ── Java formatting ───────────────────────────────────────────────────── */
function jE(v,d){ if(Number.isNaN(v)) return "NaN"; if(!isFinite(v)) return v>0?"Infinity":"-Infinity";
  const m=v.toExponential(d).match(/^(-?[\d.]+)e([+-])(\d+)$/); return m[1]+"e"+m[2]+(m[3].length<2?"0":"")+m[3]; }
function jF(v,d){ if(Number.isNaN(v)) return "NaN"; if(!isFinite(v)) return v>0?"Infinity":"-Infinity"; return v.toFixed(d); }
function jD(v){ if(Number.isNaN(v)) return "NaN"; if(!isFinite(v)) return v>0?"Infinity":"-Infinity"; if(v===0) return "0.0";
  const a=Math.abs(v); if(a>=1e-3&&a<1e7){ let s=String(v); if(/e/.test(s)) s=v.toFixed(12).replace(/0+$/,""); if(!s.includes(".")) s+=".0"; if(s.endsWith(".")) s+="0"; return s; }
  let [m,e]=v.toExponential().split("e"); if(!m.includes(".")) m+=".0"; return m+"E"+(+e); }
const jRound=x=>Math.floor(x+0.5);
const roundToDigits=(d,i)=>jRound(d*Math.pow(10,i))/Math.pow(10,i);
function precDigits(d){ return d>10?0:d>1?1:d>0.1?2:d>0.01?3:d>0.001?4:d>1e-4?5:d>1e-5?6:7; }
/* NumberFormat.getNumberInstance(Locale.US) with a minimum number of fraction digits */
function nf(v,minF){ const maxF=Math.max(3,minF); if(!isFinite(v)) return String(v);
  return v.toLocaleString("en-US",{minimumFractionDigits:minF,maximumFractionDigits:maxF}); }

/* ── Converter.java and the frame the board sends ──────────────────────── */
const u16=(b,o)=>b[o]|(b[o+1]<<8), u24=(b,o)=>b[o]|(b[o+1]<<8)|(b[o+2]<<16), u32=(b,o)=>(b[o]|(b[o+1]<<8)|(b[o+2]<<16))+b[o+3]*16777216;
const conv=(raw,i0,i1,d0,d1)=>d0+(raw-i0)/(i1-i0)*(d1-d0);
function ledBytes(A){ let max,bit; if(A<=0.001){ max=0.001; bit=0; } else { max=0.05; bit=0x80; }
  if(A>max) A=max; if(A<0) A=0; const code=Math.trunc(4095*(A/max)); return [code&255,((code>>>8)&255)|bit]; }
function ledAmps(b0,b1){ return ((b0|((b1&0x7f)<<8))/4095)*((b1&0x80)?0.05:0.001); }
const roundToLed=A=>{ const b=ledBytes(A); return ledAmps(b[0],b[1]); };
function b64dec(s){ const t=atob(s), b=new Uint8Array(t.length); for(let i=0;i<t.length;i++) b[i]=t.charCodeAt(i); return b; }
function b64enc(b){ let s=""; for(let i=0;i<b.length;i+=8192) s+=String.fromCharCode.apply(null,b.subarray(i,i+8192)); return btoa(s); }

/* ── Calc.java ─────────────────────────────────────────────────────────── */
const VARS=["uC","uT","uL","duC","duT","duL","iL","iH","t"];
function getSweepArray(d,d2,n,geo,round){ const a=new Array(n).fill(0); a[0]=d; a[n-1]=d2;
  if(geo){ let p,i2; if(d===0){ a[1]=1e-5; p=Math.pow(d2/a[1],1/(n-2)); i2=1; } else { p=Math.pow(d2/d,1/(n-1)); i2=0; }
    for(let i=i2+1;i<n-1;i++) a[i]=a[i-1]*p; }
  else for(let i=1;i<n-1;i++) a[i]=(i*(d2-d))/(n-1)+d;
  if(round) for(let i=0;i<n;i++) a[i]=roundToLed(a[i]); return a; }
function d3(y,t,i){ const d=t[i+1]-t[i], d2=t[i]-t[i-1]; return ((y[i+1]-y[i])*d2*d2+(y[i]-y[i-1])*d*d)/(d2*d*(d2+d)); }
function dLive(y,t,i,edge){ if(edge===0) return d3(y,t,i); if(edge===1) return (y[i]-y[i-1])/(t[i]-t[i-1]); return (y[i+1]-y[i])/(t[i+1]-t[i]); }
function getVarNames(s){ const out=[]; for(const v of VARS){ let i=s.indexOf(v); while(i!==-1){ if(i===0||s.charAt(i-1)!=="d"){ out.push(v); i=-1; } else i=s.indexOf(v,i+1); } } return out; }
const unitOf=s=>s==="t"?"s":(s.indexOf("u")===0&&s.length===2)?"V":(s.indexOf("i")===0&&s.length===2)?"mA":(s.indexOf("d")===0&&s.length===3)?unitOf(s.substring(1))+"/s":"?";

/* ── exp4j (the expression parser the app uses) ────────────────────────── */
const FN={sin:Math.sin,cos:Math.cos,tan:Math.tan,cot:x=>1/Math.tan(x),ln:Math.log,log1p:Math.log1p,abs:Math.abs,acos:Math.acos,asin:Math.asin,atan:Math.atan,cbrt:Math.cbrt,ceil:Math.ceil,floor:Math.floor,
  sinh:Math.sinh,sqrt:Math.sqrt,tanh:Math.tanh,cosh:Math.cosh,exp:Math.exp,expm1:Math.expm1,log10:Math.log10,log2:Math.log2,signum:Math.sign};
const CONST={pi:Math.PI,"π":Math.PI,e:Math.E,"φ":1.61803398874};
const OPS={"+":[500,true,(a,b)=>a+b],"-":[500,true,(a,b)=>a-b],"*":[1000,true,(a,b)=>a*b],
  "/":[1000,true,(a,b)=>{ if(b===0) throw new RangeError("Division by zero!"); return a/b; }],
  "%":[1000,true,(a,b)=>{ if(b===0) throw new RangeError("Division by zero!"); return a%b; }],"^":[10000,false,Math.pow]};
function compile(src,vars){
  const names=new Set([...vars,...Object.keys(CONST)]), toks=[]; let i=0;
  const last=()=>toks[toks.length-1], implicit=()=>{ const l=last(); if(l&&(l.k==="num"||l.k==="var"||l.k===")")) toks.push({k:"op",v:"*",n:2}); };
  while(i<src.length){ const c=src[i];
    if(c===" "||c==="\t"){ i++; continue; }
    if(/[0-9.]/.test(c)){ let j=i, lastE=false; while(j<src.length&&(/[0-9.eE]/.test(src[j])||(lastE&&(src[j]==="-"||src[j]==="+")))){ lastE=src[j]==="e"||src[j]==="E"; j++; }
      const s=src.slice(i,j); if(!/^(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(s)) throw new Error("bad number"); implicit(); toks.push({k:"num",v:parseFloat(s)}); i=j; continue; }
    if(/[A-Za-z_\u0080-￿]/.test(c)){ let j=i; while(j<src.length&&/[A-Za-z0-9_.\u0080-￿]/.test(src[j])) j++;
      let best=null, bl=0; for(let L=1;L<=j-i;L++){ const nm=src.substr(i,L); if(names.has(nm)){ best={k:"var",v:nm}; bl=L; } else if(FN[nm]){ best={k:"fn",v:nm}; bl=L; } }
      if(!best) throw new Error("unknown function or variable"); implicit(); toks.push(best); i+=bl; continue; }
    if(c==="("){ implicit(); toks.push({k:"("}); i++; continue; }
    if(c===")"){ toks.push({k:")"}); i++; continue; }
    if(c===","){ toks.push({k:","}); i++; continue; }
    if("+-*/^%".includes(c)){ const l=last(); const unary=(c==="-"||c==="+")&&(!l||l.k==="op"||l.k==="("||l.k===",");
      toks.push(unary?{k:"op",v:c==="-"?"neg":"pos",n:1}:{k:"op",v:c,n:2}); i++; continue; }
    throw new Error("bad character");
  }
  const out=[], st=[];
  const prec=t=>t.n===1?5000:OPS[t.v][0], left=t=>t.n===1?false:OPS[t.v][1];
  for(const t of toks){
    if(t.k==="num"||t.k==="var") out.push(t);
    else if(t.k==="fn") st.push(t);
    else if(t.k===","){ while(st.length&&st[st.length-1].k!=="(") out.push(st.pop()); }
    else if(t.k==="op"){ while(st.length&&st[st.length-1].k==="op"){ const o2=st[st.length-1]; if(t.n===1&&o2.n===2) break;
        if((left(t)&&prec(t)<=prec(o2))||prec(t)<prec(o2)) out.push(st.pop()); else break; } st.push(t); }
    else if(t.k==="(") st.push(t);
    else if(t.k===")"){ while(st.length&&st[st.length-1].k!=="(") out.push(st.pop()); if(!st.length) throw new Error("mismatched parentheses"); st.pop(); if(st.length&&st[st.length-1].k==="fn") out.push(st.pop()); }
  }
  while(st.length){ const t=st.pop(); if(t.k==="(") throw new Error("mismatched parentheses"); out.push(t); }
  let depth=0; for(const t of out){ if(t.k==="num"||t.k==="var") depth++; else if(t.k==="fn"){ if(depth<1) throw new Error("invalid"); } else if(t.k==="op"){ if(depth<t.n) throw new Error("invalid"); depth-=t.n-1; } }
  if(depth!==1) throw new Error("invalid");
  return env=>{ const s=[]; for(const t of out){
      if(t.k==="num") s.push(t.v); else if(t.k==="var") s.push(t.v in env?env[t.v]:CONST[t.v]);
      else if(t.k==="fn") s.push(FN[t.v](s.pop()));
      else if(t.n===1){ const a=s.pop(); s.push(t.v==="neg"?-a:a); } else { const b=s.pop(), a=s.pop(); s.push(OPS[t.v][2](a,b)); } }
    return s[0]; };
}
function isValid(src){ try{ compile(src,getVarNames(src)); return true; }catch(e){ return false; } }
class Calc{ constructor(s,m){ this.s=s; this.vars=getVarNames(s); try{ this.f=compile(s,this.vars); }catch(e){ this.f=null; } this.arr=this.vars.map(v=>m.part(v)); }
  at(i){ if(!this.f) return NaN; const env={}; this.vars.forEach((v,k)=>{ const x=this.arr[k][i]; env[v]=x===undefined?0:x; });
    try{ return this.f(env); }catch(e){ return 1e12; } } }

/* ── Database.java (the tablet's storage) ──────────────────────────────── */
const KEY="haslalab.ipho2021.app.v1";
let DB={titles:[],eq:[],m:{},prefs:{}};
try{ const s=localStorage.getItem(KEY); if(s){ const o=JSON.parse(s); if(o&&o.titles) DB=Object.assign(DB,o); } }catch(e){}
function dbSave(){ try{ localStorage.setItem(KEY,JSON.stringify(DB)); }catch(e){} }
const P={ str:(k,d)=>k in DB.prefs?String(DB.prefs[k]):d, int(k,d){ const v=parseInt(P.str(k,""),10); return /^-?\d+$/.test(P.str(k,""))?v:d; },
  dbl(k,d){ const s=P.str(k,""); const v=Number(s); return s.trim()!==""&&!isNaN(v)?v:d; }, bool:(k,d)=>k in DB.prefs?!!DB.prefs[k]:d, set(k,v){ DB.prefs[k]=v; dbSave(); } };

/* ── Measurement.java ──────────────────────────────────────────────────── */
const LAST="Last measurement";
class Measurement{
  constructor(name){ this.name=name||"NEW"; this.exprs=[]; this.calcs=[]; this.evals=[]; this.maps=[]; this.reset(); }
  reset(){ for(const v of VARS) this[v]=[]; this.dump=[]; this.n=0; this.nc=0; this.start=-1; this.loaded=false; this.st={lastTs:0,lastInt:0,cr:0}; this.res=0.1; }
  addExpr(s){ if(s==null||this.exprs.includes(s)||VARS.includes(s)) return false; this.exprs.push(s); this.calcs.push(new Calc(s,this)); this.evals.push([]); return true; }
  part(s){ if(VARS.includes(s)) return this[s]; const i=this.exprs.indexOf(s); return i<0?null:this.evals[i]; }
  setupAxes(x,y){ this.addExpr(x); this.addExpr(y); this.xr=this.part(x); this.yr=this.part(y); }
  startMeasurement(){ this.start=-1; this.n=0; this.nc=0; this.dump=[]; }
  stopMeasurement(){ this.upd(); this.start=-1; this.st={lastTs:0,lastInt:0,cr:0}; }
  add(b){ if(b[25]!==0) return false;
    if(!this.loaded) this.dump.push(b.slice(6,23));
    const ts=u32(b,19)*10, S=this.st; if(ts===S.lastTs) return false;
    if(ts<S.lastTs) S.cr=(S.lastTs+S.lastInt)-ts;
    if(this.start===-1) this.start=ts;
    const i=this.n; this.t[i]=((ts-this.start)+S.cr)/1000;
    this.uC[i]=conv(u24(b,10),0,16777200,-10.05,10.04998); this.uL[i]=conv(u16(b,8),0,65535,0,3.3); this.uT[i]=conv(u16(b,6),0,65535,0,3.3);
    this.iH[i]=roundToDigits(conv(u16(b,17),0,65535,0,3.3)*1000,-1); this.iL[i]=ledAmps(b[15],b[16])*1000;
    if(S.lastTs!==0) S.lastInt=ts-S.lastTs; S.lastTs=ts; this.n++; return true; }
  push(b,ledSet){ const lb=ledBytes(ledSet); b[15]=lb[0]; b[16]=lb[1]; if(this.add(b)) this.upd(); }
  upd(){ const n=this.n; if(n<2) return; const c=this.nc; if(c===n) return; const edge=c===0?-1:(c<n-1?0:1);
    this.duC[c]=dLive(this.uC,this.t,c,edge); this.duT[c]=dLive(this.uT,this.t,c,edge); this.duL[c]=dLive(this.uL,this.t,c,edge);
    for(let k=0;k<this.calcs.length;k++) this.evals[k][c]=this.calcs[k].at(c); this.nc++; }
  calcAll(){ this.nc=0; for(let i=0;i<this.n;i++) this.upd(); }
  last(arr){ return this.nc===0||!arr?NaN:arr[this.nc-1]; }
  save(title){ const name=title||this.name; this.name=name; if(!DB.titles.includes(name)) DB.titles.push(name);
    const bytes=new Uint8Array(this.n*17); for(let i=0;i<this.n&&i<this.dump.length;i++) bytes.set(this.dump[i],i*17);
    DB.m[name]={p:[name,"0.1",this.n,this.start].join("\n"),d:b64enc(bytes)}; dbSave(); }
  static load(name){ const m=new Measurement(name), rec=DB.m[name]; m.loaded=true; if(!rec) return m;
    const p=rec.p.split("\n"); m.name=p[0]; const total=parseInt(p[2],10)||0; m.start=parseInt(p[3],10); const d=b64dec(rec.d), fr=new Uint8Array(30);
    for(let i=0;i<total;i++){ fr.set(d.subarray(i*17,i*17+17),6); fr[25]=0; m.add(fr); } return m; }
}

/* ── the app state (MainActivity.AppState) ─────────────────────────────── */
const S={boardConnected:false, autoRefresh:false, inProgress:false, sweep:false, skip:0, lastReset:-1, heatSet:0, ledSet:0, pwSet:0, lastLedMA:0, usbDefault:false, attached:false, lastBack:0, thread:null};
let meas=new Measurement();
const lab=()=>P.str("lab","ANY LAB");
function filterLab(list,l){ const a=list.slice(); const rm=x=>{ const i=a.indexOf(x); if(i>=0) a.splice(i,1); };
  if(l==="LAB 1"){ rm("uL"); rm("duL"); rm("iL"); } else if(l==="LAB 2"){ rm("uC"); rm("duC"); } return a; }

/* ── toasts and dialogs ────────────────────────────────────────────────── */
const toastQ=[]; let toastBusy=false;
function toast(s,long,big){ toastQ.push([s,long,big]); if(!toastBusy) nextToast(); }
function nextToast(){ const it=toastQ.shift(); if(!it){ toastBusy=false; return; } toastBusy=true;
  const el=document.createElement("div"); el.className="toast"+(it[2]?" big":""); el.textContent=it[0]; $("toasts").appendChild(el);
  setTimeout(()=>{ el.remove(); nextToast(); }, it[1]?3500:2000); }
function dialog(o){ /* o: {title, items, multi, selected[], onSelect(list), onCancel, msg, input, ok, cancel} */
  const dim=document.createElement("div"); dim.className="dim"; const box=document.createElement("div"); box.className="dlg";
  box.style.cssText=o.small?"width:520px;max-height:440px":"width:644px;height:516px";
  let sel=(o.selected||[]).filter(x=>o.items&&o.items.includes(x)); if(o.items&&!o.multi&&!sel.length&&o.items.length) sel=[o.items[0]];
  let html=(o.title?"<h3></h3>":"")+(o.msg?'<div class="msg"></div>':"")+(o.input!==undefined?"<input>":"")+(o.check?'<div class="cbx"><span class="chk"></span><span></span></div>':"")+(o.items?'<div class="lst"></div>':'<div style="flex:1"></div>')+'<div class="bar"><span class="c"></span><span class="o"></span></div>';
  box.innerHTML=html; if(o.title) box.querySelector("h3").textContent=o.title; if(o.msg) box.querySelector(".msg").textContent=o.msg;
  const inp=box.querySelector("input"); if(inp){ inp.value=o.input; inp.inputMode="decimal"; }
  if(o.check){ const c=box.querySelector(".cbx"); c.lastChild.textContent=o.check; c.onclick=()=>{ c.classList.toggle("on"); c.firstChild.textContent=c.classList.contains("on")?"✓":""; c.firstChild.style.cssText=c.classList.contains("on")?"background:#ee6655;border-color:#ee6655":""; }; }
  if(o.items){ const L=box.querySelector(".lst");
    const draw=()=>{ L.innerHTML=""; o.items.forEach(s=>{ const r=document.createElement("div"); r.className="it"+(sel.includes(s)?" on":""); r.innerHTML=(o.multi?'<span class="chk">'+(sel.includes(s)?"✓":"")+"</span>":'<span class="rad"></span>')+"<span></span>"; r.lastChild.textContent=s;
      r.onclick=()=>{ if(o.multi){ if(sel.includes(s)) sel=sel.filter(x=>x!==s); else sel.push(s); } else sel=[s]; draw(); }; L.appendChild(r); }); };
    draw(); }
  const close=()=>dim.remove();
  const bc=box.querySelector(".c"), bo=box.querySelector(".o"); bc.textContent=o.cancel||"Cancel"; bo.textContent=o.ok||"Select";
  bc.onclick=()=>{ close(); o.onCancel&&o.onCancel(); };
  bo.onclick=()=>{ close(); if(o.items) o.onSelect&&o.onSelect(o.items.filter(x=>sel.includes(x))); else o.onSelect&&o.onSelect(inp?inp.value:null,box.querySelector(".cbx.on")!==null); };
  dim.onclick=e=>{ if(e.target===dim){ close(); o.onCancel&&o.onCancel(); } };
  dim.appendChild(box); $("dlgs").appendChild(dim); if(inp){ inp.focus(); inp.select(); } return {close};
}
const dlgOpen=()=>$("dlgs").children.length>0;

/* ── the link to the board ─────────────────────────────────────────────── */
let send=()=>{}, linkKind="", boardSeen=false;
function onBoard(m){ if(!m||typeof m!=="object") return;
  switch(m.type){
    case "welcome": boardSeen=true; $("conn").hidden=true; if(m.lang&&!Q.get("lang")){ lang=m.lang==="ko"?"ko":"en"; } usbAttach(!!m.attached); break;
    case "lang": lang=m.lang==="ko"?"ko":"en"; connText(); break;
    case "attach": usbAttach(true); break;
    case "detach": usbDetach(); break;
    case "frames": if(Array.isArray(m.list)) for(const f of m.list) onFrame(b64dec(f)); break;
    case "done": if(S.inProgress&&S.sweep) S.inProgress=false, stopThread(); break;
    case "os": osCmd(m.cmd); break;
    case "bye": lost(); break;
  }
}
/* UsbService + MainActivity.mUsbReceiver */
function usbAttach(on){ if(!on){ if(S.attached) usbDetach(); else if(!S.noUsbShown){ S.noUsbShown=true; toast("No USB connected"); } return; }
  if(S.attached) return; S.attached=true;
  if(S.usbDefault) granted(); else usbPermission(); }
function usbPermission(){ dialog({small:true, msg:"Allow IPhO to access STM32 Virtual ComPort?", check:"Use by default for this USB device", cancel:"Cancel", ok:"OK",
  onSelect:(_v,def)=>{ if(def) S.usbDefault=true; granted(); }, onCancel:()=>{ toast("USB Permission not granted"); S.boardConnected=false; } }); }
function granted(){ if(!S.attached) return;
  if(Date.now()-S.lastReset<10000){ toast("Device connected."); S.boardConnected=true; }
  else toast("Please press RESET button on the board in 10 seconds!",true,true);
  S.lastReset=Date.now(); }
function usbDetach(){ if(!S.attached) return; S.attached=false; toast("USB disconnected"); S.boardConnected=false; askToStop(); }
function lost(){ boardSeen=false; if(S.attached) usbDetach(); if(!EMBED&&!PY){ $("conn").hidden=false; $("cSt").textContent=T().cLost; } }

/* ── the measurement thread (MainActivity.MeasurementThread) ───────────── */
function startThread(){ const sweepOn=S.sweep&&!S.autoRefresh; const z2=!S.autoRefresh;
  if(!S.autoRefresh&&S.inProgress){ chart.reset(); if(S.sweep) setSwitch("swMeas",true); }
  S.thread={z2, sweep:sweepOn};
  chart.setDefaultAxes(S.sweep); meas.setupAxes(chart.xSel(),chart.ySel()); table.bind(meas);
  chart.mapMeasurement(meas); meas.startMeasurement();
  if(S.inProgress&&S.sweep) chart.repaintPeriod=1;
  const pw=P.bool("pulsed_current",false)?P.dbl("led_current_pulse_durations_ms",0):0;
  send({type:"run",on:true,ts:P.int("interval_between_measurements_ms",140)/1000,
        sweep:sweepOn?getSweepCurrentArray():null, pw:sweepOn?pw:S.pwSet, led:S.ledSet});
  S.skip=0; }
function getSweepCurrentArray(){ return getSweepArray(P.dbl("min_sweep_led_current_mA",1)*0.001,P.dbl("max_sweep_led_current_mA",1)*0.001,P.int("sweep_measurement_points_number",50),P.bool("sweep_geometric_current_increase",false),true); }
function onFrame(b){ if(b.length!==30) return;
  if(S.skip>0){ S.skip--; return; }
  if(!(S.inProgress||S.autoRefresh)||!S.thread) return;
  if(b[2]===4&&S.thread.sweep) S.ledSet=ledAmps(b[15],b[16]);
  meas.push(b,S.ledSet); table.updateLive();
  if(S.inProgress) chart.updateMapped(); }
function stopThread(){ const th=S.thread; if(!th) return; S.thread=null; send({type:"run",on:false});
  meas.stopMeasurement();
  if(th.z2){ meas.save(LAST); chart.updateMapped(true); chart.sel=[LAST]; table.fill(meas); }
  askToStop(true);
  if(P.bool("turn_off_LED_on_measurement_end",false)&&S.ledSet!==0){ S.ledSet=0; S.pwSet=0; send({type:"led",A:0,pw:0}); $("etIL").value="0"; sbSet("sbIL",0); sbSet("sbTL",0); toast("LED current off"); lbRed("lbIL",false); S.lastLedMA=0; }
  if(P.bool("turn_off_heating_on_measurement_end",false)&&S.heatSet!==0){ S.heatSet=0; send({type:"heat",A:0}); $("etIH").value="0"; sbSet("sbIH",0); toast("Heating current off"); lbRed("lbIH",false); }
}
function askToStop(fromThread){ const was=S.inProgress||S.autoRefresh; S.autoRefresh=false; S.inProgress=false; setSwitch("swMeas",false); setSwitch("swCheck",false);
  if(was&&!fromThread) stopThread(); }

/* ── the main window ───────────────────────────────────────────────────── */
function setSwitch(id,on){ $(id).classList.toggle("on",!!on); }
const isOn=id=>$(id).classList.contains("on");
function lbRed(id,on){ $(id).style.background=on?"#ff0000":"transparent"; }
$("swMeas").onclick=()=>{ if(dlgOpen()) return; const want=!isOn("swMeas");
  if(!S.boardConnected){ toast("Please plug in, power on and reset the board first."); setSwitch("swMeas",false); return; }
  if(S.autoRefresh){ setSwitch("swCheck",false); setSwitch("swMeas",false); S.autoRefresh=false; S.inProgress=false; stopThread(); toast("All running measurements stopped. Tap again to start measurement.",true,true); return; }
  setSwitch("swMeas",want); S.inProgress=want;
  if(want){ chart.sel=[]; startThread(); } else stopThread(); };
$("swCheck").onclick=()=>{ if(dlgOpen()) return; const want=!isOn("swCheck");
  if(!S.boardConnected){ toast("Please plug in, power on and reset the board first."); setSwitch("swCheck",false); return; }
  if(S.inProgress){ toast("You don't want to do this during measurement."); if(want) setSwitch("swCheck",false); return; }
  setSwitch("swCheck",want); S.autoRefresh=want; if(want) startThread(); else stopThread(); };
$("ibAdd").onclick=()=>{ if(S.inProgress){ toast("You don't want to do this during measurement."); return; }
  const nm=$("etTitle").value; if(nm===""){ toast("No measurement title entered!"); return; }
  if(!DB.titles.includes(nm)){ meas.save(nm); toast("saved  "+nm); } else toast("This name already exists!"); };
$("ibDel").onclick=()=>{ if(S.inProgress){ toast("You don't want to do this during measurement."); return; }
  const nm=$("etTitle").value; if(nm===""){ toast("No measurement title entered!"); return; }
  if(!DB.titles.includes(nm)){ toast("No measurement with this title exists"); return; }
  DB.titles=DB.titles.filter(x=>x!==nm); dbSave(); chart.removeMeasurement(nm); table.removeMeasurement(nm); toast("deleted "+nm); $("etTitle").value=""; };
$("btMeas").onclick=()=>{ if(S.inProgress||S.autoRefresh){ toast("You don't want to do this during measurement."); return; }
  const list=DB.titles.slice(); if(!list.length){ toast("Nothing to select from!",true); return; }
  const cur=$("btMeas").textContent; dialog({title:"Select measurement to edit", items:list, selected:list.includes(cur)?[cur]:[],
    onSelect:a=>{ const nm=a[0]; $("etTitle").value=nm; table.fill(Measurement.load(nm)); }, onCancel:()=>toast("Changes cancelled.") }); };
$("ibReplot").onclick=()=>safeReplot(true);
$("ibInfo").onclick=()=>{ const l=lab(); let s=l+";\n"+"timestep = "+P.int("interval_between_measurements_ms",140)+" ms;\n";
  if(l==="LAB 2"&&P.bool("sweep_measurement",true)){ s+="sweep measurement;\n"+"number of points = "+P.int("sweep_measurement_points_number",-1)+";\n";
    if(P.bool("pulsed_current",false)) s+="current pulse duration = "+jF(P.dbl("led_current_pulse_durations_ms",-1),1)+" ms ;\n"; }
  toast(s,true); };
$("etTitle").oninput=()=>{ if($("etTitle").value==="ForSupportOnly!") $("ibCopy").hidden=false; };
$("ibCopy").onclick=()=>{ const s=table.toString(); if(s===""){ toast("No data in table!"); return; }
  const f=new File([s],"tmp.tsv",{type:"text/plain"}); if(navigator.canShare&&navigator.canShare({files:[f]})) navigator.share({files:[f],title:table.src?table.src.name:""}).catch(()=>{});
  else { const a=document.createElement("a"); a.href=URL.createObjectURL(f); a.download=(table.src?table.src.name:"measurement")+".tsv"; a.click(); setTimeout(()=>URL.revokeObjectURL(a.href),3000); } };
$("ibSet").onclick=()=>{ if(S.inProgress){ toast("You don't want to do this during measurement."); return; } openSettings(); };
$("btFx").onclick=()=>{ if(S.inProgress||S.autoRefresh){ toast("You don't want to do this during measurement."); return; } openEditor(); };

/* seekbars */
const SB={};
function makeSB(id,onChange,onStart,onStop){ const el=$(id); el.innerHTML='<div class="tr"></div><div class="pr"></div><div class="th"></div>'; SB[id]={p:0,onChange};
  const set=(p,user)=>{ p=Math.max(0,Math.min(100,Math.round(p))); const ch=p!==SB[id].p; SB[id].p=p; draw(); if(ch&&user) onChange(p); };
  const draw=()=>{ const w=el.clientWidth||parseFloat(el.style.width), x=16+(w-32)*SB[id].p/100; el.querySelector(".pr").style.width=(x-16)+"px"; el.querySelector(".th").style.left=x+"px"; };
  SB[id].set=set; SB[id].draw=draw;
  const pos=e=>{ const p=scrPt(e), o=offIn(el); return (p[0]-o[0]-16)/((el.offsetWidth||200)-32)*100; };
  el.addEventListener("pointerdown",e=>{ if(el.classList.contains("off")) return; el.setPointerCapture(e.pointerId); onStart&&onStart(); set(pos(e),true);
    const mv=ev=>set(pos(ev),true), up=()=>{ el.removeEventListener("pointermove",mv); el.removeEventListener("pointerup",up); el.removeEventListener("pointercancel",up); onStop&&onStop(); };
    el.addEventListener("pointermove",mv); el.addEventListener("pointerup",up); el.addEventListener("pointercancel",up); });
  draw(); }
function sbSet(id,p){ SB[id].set(p,false); }
const LED_PROG=getSweepArray(0,0.05,101,true,true);
let chHeat=false, chLed=false, chPw=false, lastHeatProg=0, lastHeatTxt="0";
makeSB("sbIH",p=>{ $("etIH").value=jF(500*p/100,0); showApply(); },()=>{ chHeat=true; },()=>{ chHeat=false; });
makeSB("sbIL",p=>{ const d=LED_PROG[p]*1000; $("etIL").value=jF(d,d>0?precDigits(d):0); },()=>{ chLed=true; },()=>{ chLed=false; updateLed(); });
makeSB("sbTL",p=>{ $("etTL").value=jF(25.5*p/100,1); },()=>{ chPw=true; },()=>{ chPw=false; updateLed(); });
function showApply(){ $("btApply").hidden=false; $("btCancel").hidden=false; }
$("etIH").oninput=showApply; $("etIL").oninput=()=>updateLed(); $("etTL").oninput=()=>updateLed();
$("btApply").onclick=()=>{ lastHeatProg=SB.sbIH.p; lastHeatTxt=$("etIH").value; updateHeat(); $("btApply").hidden=true; $("btCancel").hidden=true; };
$("btCancel").onclick=()=>{ sbSet("sbIH",lastHeatProg); $("etIH").value=lastHeatTxt; $("btApply").hidden=true; $("btCancel").hidden=true; };
function getD(el,d){ const s=el.value; if(s==="") return d; const v=Number(s); return /^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?[dDfF]?\s*$/.test(s)&&!isNaN(v)?v:NaN; }
function updateHeat(){ if(chHeat) return; const s=$("etIH").value!==""?$("etIH").value:"0"; const v=getD({value:s},0);
  if(Number.isNaN(v)){ toast("Bad heater current value!"); return; } if(v<0){ toast("Can't be < 0."); return; } if(v>500){ toast("Too big value."); return; }
  S.skip=S.inProgress||S.autoRefresh?1:0; S.heatSet=v/1000; send({type:"heat",A:v/1000});
  if(v===0){ lbRed("lbIH",false); toast("Turned off heating."); } else lbRed("lbIH",true); }
function updateLed(){ if(chLed||chPw) return; const v=getD($("etIL"),0), pw=getD($("etTL"),0);
  if(Number.isNaN(v)){ toast("Bad value of LED current!"); return; } if(Number.isNaN(pw)){ toast("Bad value of LED current pulse width entered!"); return; }
  if(v<0){ toast("Can't be < 0."); return; } if(v>50){ toast("Too big value."); return; } if(pw<0){ toast("Can't be < 0."); return; } if(pw>25.5){ toast("Too big value."); return; }
  S.ledSet=v*0.001; S.pwSet=pw; send({type:"led",A:S.ledSet,pw});
  if(v===0){ lbRed("lbIL",false); if(S.lastLedMA!==0) toast("LED current off"); } else lbRed("lbIL",true); S.lastLedMA=v; }

/* ── TableHandler.java ─────────────────────────────────────────────────── */
const table={exprs:[], defaults:["t","uC","uT"], src:null, parts:[], filled:0, live:null,
  hb:()=>[...document.querySelectorAll("#thr .hb")],
  getExprs(){ if(!this.exprs.length){ this.exprs=this.defaults.slice(); this.hb().forEach((b,i)=>{ if(i<this.exprs.length) b.textContent=this.exprs[i]; }); } return this.exprs; },
  clear(){ const tb=$("tb"); while(tb.children.length>1) tb.removeChild(tb.lastChild); this.live=null; },
  fmt(e,v){ return e==="t"?jF(v,3):jE(v,3); },
  bind(m){ this.clear(); this.parts=[]; this.src=m; const tr=document.createElement("tr"); this.getExprs().forEach(e=>{ m.addExpr(e); this.parts.push(m.part(e)); tr.appendChild(document.createElement("td")); }); $("tb").appendChild(tr); this.live=tr; },
  updateLive(){ if(!this.live) return; this.getExprs().forEach((e,i)=>{ const td=this.live.children[i]; if(td) td.textContent=this.fmt(e,this.src.last(this.parts[i])); }); },
  fill(m){ this.filled=0; this.src=m; this.getExprs().forEach(e=>m.addExpr(e)); m.calcAll(); this.clear(); this.parts=[];
    this.exprs.forEach((e,i)=>{ this.hb()[i].textContent=e; this.parts.push(m.part(e)); }); this.refill(); },
  refill(){ const m=this.src; if(!m) return; let n=m.nc; if(n>=this.filled+300) n=this.filled+300; if(this.filled<n) toast("Loading more data...");
    const frag=document.createDocumentFragment(); for(let i=this.filled;i<n;i++){ const tr=document.createElement("tr"); this.exprs.forEach((e,k)=>{ const td=document.createElement("td"); td.textContent=this.fmt(e,this.parts[k][i]); tr.appendChild(td); }); frag.appendChild(tr); }
    $("tb").appendChild(frag); this.filled=n; },
  changeColumns(){ this.exprs=[]; this.hb().forEach(b=>{ if(b.textContent!=="f(x)") this.exprs.push(b.textContent); });
    this.hb().forEach((b,i)=>b.textContent=i<this.exprs.length?this.exprs[i]:"f(x)"); if(this.src) this.fill(this.src); },
  removeMeasurement(nm){ if(this.src&&this.src.name===nm){ this.clear(); this.src=null; } },
  toString(){ const m=this.src; if(!m) return ""; let s=this.getExprs().join("\t")+"\n"; for(let i=0;i<m.nc;i++) s+=this.exprs.map((e,k)=>this.fmt(e,this.parts[k][i])).join("\t")+"\n"; return s; } };
let lastScroll=0;
$("tbl").addEventListener("scroll",()=>{ const el=$("tbl"); if(el.scrollTop+el.clientHeight<el.scrollHeight-2) return; const now=Date.now(); if(now-lastScroll>100){ table.refill(); lastScroll=now; } });
table.hb().forEach(b=>b.onclick=()=>{ if(S.inProgress||S.autoRefresh){ toast("You don't want to do this during measurement."); return; }
  const axes=filterLab(VARS.concat(DB.eq),lab()); dialog({title:"Select equations to monitor", items:axes, selected:[b.textContent],
    onSelect:a=>{ b.textContent=a[0]; table.changeColumns(); }, onCancel:()=>toast("Changes cancelled.") }); });

/* ── ChartHandler.java + achartengine (scatter chart) ──────────────────── */
const COLORS=["#444444","#ff0000","#00ff00","#0000ff","#000000","#00ffff","#ff00ff"];
const cvs=$("chart"), K=4/3;             /* achartengine works in device pixels: 1 dp = 4/3 px on this tablet (tvdpi) */
const PW=464*K, PH=484*K, MG={t:50,l:50,b:0,r:20}, LEG=70;
const chart={series:[], mark:null, r:{minX:null,maxX:null,minY:null,maxY:null}, xs:"t", ys:"uC", xAxisStr:null, yAxisStr:null, sel:[], lastLim:[0,0,0,0], repaintPeriod:5, nPts:0, prec:[2,2], maps:[],
  xSel(){ return this.xs; }, ySel(){ return this.ys; },
  setDefaultAxes(sw){ if(this.xAxisStr==null||this.yAxisStr==null){ if(sw){ this.xAxisStr=this.xAxisStr||"uL"; this.yAxisStr=this.yAxisStr||"iL"; } else { this.xAxisStr=this.xAxisStr||"t"; this.yAxisStr=this.yAxisStr||"uC"; } } },
  init(){ this.series=[]; this.r={minX:null,maxX:null,minY:null,maxY:null}; this.nPts=0; this.prec=[2,2]; this.maps=[]; this.refresh(); },
  reset(){ this.mark=null; this.init(); },
  refresh(){ this.repaintPeriod=P.int("replot_each_n_timesteps",5); if(!this.sel.length) this.putPoint(0,0,"Tap for measurements"); this.draw(); },
  addSeries(name,xs,ys,n,col){ const s={name,x:[],y:[],col:col||"#0000ff"}; for(let i=0;i<n;i++) this.addPt(s,xs[i],ys[i]); this.series.push(s); return s; },
  addPt(s,x,y){ if(Number.isNaN(x)||Number.isNaN(y)){ toast("NaN in data!"); return; } if(Math.abs(x)>=1e12||Math.abs(y)>=1e12){ toast("Overflow in data!(?)"); return; } s.x.push(x); s.y.push(y); },
  putPoint(x,y,label){ this.mark={name:label||("x,y: "+(Math.abs(x)<0.1?jE(x,3):jF(x,3))+", "+(Math.abs(y)>=0.1?jF(y,3):jE(y,3))),x:[x],y:[y],col:"#0000ff",isMark:true}; },
  mapMeasurement(m){ const s={name:m.name,x:[],y:[],col:"#0000ff"}; this.series.push(s); this.maps.push({m,s,xa:m.xr,ya:m.yr,n:0}); },
  updateMapped(all){ for(const mp of this.maps){ const tot=mp.m.nc; for(let i=mp.n;i<tot;i++){ this.addPt(mp.s,mp.xa[i],mp.ya[i]); this.nPts++; if(this.nPts%this.repaintPeriod===0) this.draw(); } mp.n=tot; } if(all) this.draw(); },
  all(){ return this.mark?this.series.concat([this.mark]):this.series; },
  dataRange(){ let a=[Infinity,-Infinity,Infinity,-Infinity]; for(const s of this.all()) for(let i=0;i<s.x.length;i++){ a[0]=Math.min(a[0],s.x[i]); a[1]=Math.max(a[1],s.x[i]); a[2]=Math.min(a[2],s.y[i]); a[3]=Math.max(a[3],s.y[i]); } return a; },
  getAxisLimits(){ const d=this.dataRange(), r=this.r; const A=[r.minX!=null?r.minX:Number.MAX_VALUE,r.maxX!=null?r.maxX:-Number.MAX_VALUE,r.minY!=null?r.minY:Number.MAX_VALUE,r.maxY!=null?r.maxY:-Number.MAX_VALUE];
    return [Math.min(A[0],d[0]),Math.max(A[1],d[1]),Math.min(A[2],d[2]),Math.max(A[3],d[3])]; },
  view(){ const d=this.dataRange(), r=this.r; let v=[r.minX!=null?r.minX:d[0],r.maxX!=null?r.maxX:d[1],r.minY!=null?r.minY:d[2],r.maxY!=null?r.maxY:d[3]];
    if(!isFinite(v[0])||!isFinite(v[1])){ v[0]=0; v[1]=0; } if(!isFinite(v[2])||!isFinite(v[3])){ v[2]=0; v[3]=0; } return v; },
  setXYLimits(a){ if(!Number.isNaN(a[0])) this.r.minX=a[0]; if(!Number.isNaN(a[1])) this.r.maxX=a[1]; if(!Number.isNaN(a[2])) this.r.minY=a[2]; if(!Number.isNaN(a[3])) this.r.maxY=a[3]; },
  plotSelected(user){ const xa=this.xs, ya=this.ys; this.reset(); this.series=[];
    for(const nm of this.sel){ const m=Measurement.load(nm); m.setupAxes(xa,ya); m.calcAll(); const s=this.addSeries(m.name,m.xr,m.yr,m.n); }
    this.series.forEach((s,i)=>s.col=COLORS[i%COLORS.length]); this.mark=null;
    let lim; if(user) lim=userLimits(); else { lim=this.getAxisLimits(); setUserLimits(lim); this.lastLim=lim.slice(); }
    this.setXYLimits(lim); if(!this.sel.length) this.putPoint(0,0,"Tap for measurements"); this.draw(); },
  removeMeasurement(nm){ if(this.sel.includes(nm)){ this.sel=this.sel.filter(x=>x!==nm); this.plotSelected(true); } },
  /* drawing, as XYChart/ScatterChart do it */
  draw(){ const dpr=window.devicePixelRatio||1, sc=SCALE*dpr, W=PW, H=PH; cvs.width=Math.round(464*sc); cvs.height=Math.round(484*sc);
    const c=cvs.getContext("2d"); c.setTransform(cvs.width/W,0,0,cvs.height/H,0,0); c.clearRect(0,0,W,H);
    const L=MG.l, T=MG.t, R=W-MG.r, B=H-MG.b-LEG; this.box={L,T,R,B,W,H};
    c.fillStyle="rgba(90,80,70,0.196)"; c.fillRect(0,B,W,H-B); c.fillRect(0,0,W,T); c.fillRect(0,0,L,H); c.fillRect(R,0,W-R,H);
    const v=this.view(); this.v=v; const sx=v[1]-v[0], sy=v[3]-v[2];
    const X=x=>sx?L+(x-v[0])/sx*(R-L):L, Y=y=>sy?B-(y-v[2])/sy*(B-T):B; this.X=X; this.Y=Y;
    c.font="14px Roboto,Arial,sans-serif"; c.fillStyle="#0000ff"; c.strokeStyle="#0000ff"; c.lineWidth=0.5; c.textAlign="center";
    const xl=labels(v[0],v[1],8), yl=labels(v[2],v[3],8);
    for(const t of xl){ const x=X(t); if(x<L-0.5||x>R+0.5) continue; c.beginPath(); c.moveTo(x,T); c.lineTo(x,B); c.stroke(); c.fillText(nf(t,this.prec[0]),x,B+14*4/3); }
    for(const t of yl){ const y=Y(t); if(y<T-0.5||y>B+0.5) continue; c.beginPath(); c.moveTo(L,y); c.lineTo(R,y); c.stroke(); c.fillText(nf(t,this.prec[1]),L,y); }
    c.strokeStyle="#cccccc"; c.lineWidth=1; c.beginPath(); c.moveTo(L,T); c.lineTo(L,B); c.lineTo(R,B); c.stroke();
    c.font="32px Roboto,Arial,sans-serif"; c.fillStyle="#0000ff"; c.fillText(this.xs,L+(R-L)/2,B+14*4/3+32);
    c.save(); c.translate(32,T+(B-T)/2); c.rotate(-Math.PI/2); c.fillText(this.ys,0,0); c.restore();
    c.save(); c.beginPath(); c.rect(L,T,R-L,B-T); c.clip();
    for(const s of this.all()){ c.strokeStyle=s.col; if(s.isMark){ c.lineWidth=3; for(let i=0;i<s.x.length;i++) xMark(c,X(s.x[i]),Y(s.y[i]),4); continue; }
      c.lineWidth=2; c.beginPath(); for(let i=0;i<s.x.length;i++){ const px=X(s.x[i]), py=Y(s.y[i]); c.moveTo(px+1,py); c.arc(px,py,1,0,6.2832); } c.stroke(); }
    c.restore();
    /* the legend */
    c.font="16px Roboto,Arial,sans-serif"; c.textAlign="left"; let lx=L+10, ly=B+34;
    for(const s of this.all()){ const w=c.measureText(s.name).width+30; if(lx+w>R&&lx>L+10){ lx=L+10; ly+=20; }
      c.strokeStyle=s.col; c.fillStyle=s.col; if(s.isMark){ c.lineWidth=3; xMark(c,lx+5,ly-5,4); } else { c.lineWidth=2; c.beginPath(); c.arc(lx+5,ly-5,2,0,6.2832); c.stroke(); }
      c.fillText(s.name,lx+15,ly); lx+=w; } },
  pick(px,py){ for(const s of this.all()) for(let i=0;i<s.x.length;i++){ if(Math.abs(this.X(s.x[i])-px)<=10&&Math.abs(this.Y(s.y[i])-py)<=10) return [s.x[i],s.y[i]]; } return null; },
  area(px,py){ const W=this.box.W, H=this.box.H, top=MG.t, left=MG.l, bot=MG.b+LEG+32;
    if(px<left&&py>top&&py<H-bot) return "Y"; if(px>=(W-left)/2&&py>H-bot) return "X"; if(px>=left&&px<W/2&&py>H-bot) return "LIST"; return py<top?"TITLE":"PLOT"; },
  toReal(px,py){ const v=this.v, b=this.box; return [v[0]+(px-b.L)/(b.R-b.L)*(v[1]-v[0]), v[2]+(b.B-py)/(b.B-b.T)*(v[3]-v[2])]; }
};
function xMark(c,x,y,s){ c.beginPath(); c.moveTo(x-s,y-s); c.lineTo(x+s,y+s); c.moveTo(x+s,y-s); c.lineTo(x-s,y+s); c.stroke(); }
function labels(a,b,n){ if(Math.abs(a-b)<1.0000000116860974e-7) return [a]; let lo=Math.min(a,b), hi=Math.max(a,b);
  const ru=d=>{ const f=Math.floor(Math.log10(d)); let p=d*Math.pow(10,-f); p=p>5?10:p>2?5:p>1?2:p; return p*Math.pow(10,f); };
  const st=ru((hi-lo)/n), s0=Math.ceil(lo/st)*st, s1=Math.floor(hi/st)*st, k=Math.trunc((s1-s0)/st)+1, out=[];
  for(let i=0;i<k;i++) out.push(Number((s0+i*st).toFixed(5))); return out; }
function userLimits(){ return ["etXmin","etXmax","etYmin","etYmax"].map(id=>{ const s=$(id).value; const v=Number(s); return s.trim()===""||isNaN(v)?NaN:v; }); }
function setUserLimits(a){ const dx=a[1]-a[0], dy=a[3]-a[2]; $("etXmin").value=jD(roundToDigits(a[0],precDigits(dx))); $("etXmax").value=jD(roundToDigits(a[1],precDigits(dx)));
  $("etYmin").value=jD(roundToDigits(a[2],precDigits(dy))); $("etYmax").value=jD(roundToDigits(a[3],precDigits(dy))); }
function safeReplot(user){ chart.setDefaultAxes(S.sweep); if(S.inProgress){ toast("You don't want to do this during measurement."); return; }
  if(chart.sel.length>0||!user) chart.plotSelected(user); }
function axisChanged(){ const a=chart.getAxisLimits(), z=[0,0,0,0], eq=(p,q)=>p.every((x,i)=>x===q[i]);
  if(eq(chart.lastLim,z)&&!eq(a,z)){ chart.lastLim=a; return false; } if(eq(a,chart.lastLim)) return false; chart.lastLim=a; return true; }
/* pan, zoom and taps on the chart (GraphicalView / TouchHandler) */
let gest=null;
const cpos=e=>{ const p=scrPt(e), o=offIn(cvs); return [(p[0]-o[0])/464*PW,(p[1]-o[1])/484*PH]; };
const ptrs=new Map();
cvs.addEventListener("pointerdown",e=>{ cvs.setPointerCapture(e.pointerId); ptrs.set(e.pointerId,cpos(e)); if(ptrs.size===1) gest={start:cpos(e),last:cpos(e),moved:false,v0:chart.view()}; else if(ptrs.size===2){ const [a,b]=[...ptrs.values()]; gest={pinch:Math.hypot(a[0]-b[0],a[1]-b[1]),v0:chart.view(),mid:[(a[0]+b[0])/2,(a[1]+b[1])/2],moved:true}; } });
cvs.addEventListener("pointermove",e=>{ if(!ptrs.has(e.pointerId)||!gest) return; ptrs.set(e.pointerId,cpos(e)); const v=gest.v0;
  if(gest.pinch&&ptrs.size===2){ const [a,b]=[...ptrs.values()], d=Math.hypot(a[0]-b[0],a[1]-b[1]), f=gest.pinch/Math.max(1,d), m=chart.toReal(gest.mid[0],gest.mid[1]);
    chart.r={minX:m[0]-(m[0]-v[0])*f,maxX:m[0]+(v[1]-m[0])*f,minY:m[1]-(m[1]-v[2])*f,maxY:m[1]+(v[3]-m[1])*f}; chart.draw(); return; }
  const p=cpos(e); if(Math.hypot(p[0]-gest.start[0],p[1]-gest.start[1])>8) gest.moved=true; if(!gest.moved) return;
  const b=chart.box, dx=(p[0]-gest.start[0])/(b.R-b.L)*(v[1]-v[0]), dy=(p[1]-gest.start[1])/(b.B-b.T)*(v[3]-v[2]);
  chart.r={minX:v[0]-dx,maxX:v[1]-dx,minY:v[2]+dy,maxY:v[3]+dy}; chart.draw(); });
const endPtr=e=>{ if(!ptrs.has(e.pointerId)) return; ptrs.delete(e.pointerId); if(ptrs.size) return; const g=gest; gest=null; if(g&&!g.moved&&e.type==="pointerup") chartClick(g.start[0],g.start[1]); };
cvs.addEventListener("pointerup",endPtr); cvs.addEventListener("pointercancel",endPtr);
cvs.addEventListener("wheel",e=>{ e.preventDefault(); const v=chart.view(), p=cpos(e), m=chart.toReal(p[0],p[1]), f=e.deltaY<0?1/1.25:1.25;
  chart.r={minX:m[0]-(m[0]-v[0])*f,maxX:m[0]+(v[1]-m[0])*f,minY:m[1]-(m[1]-v[2])*f,maxY:m[1]+(v[3]-m[1])*f}; chart.draw(); },{passive:false});
function chartClick(px,py){ if(S.inProgress) return;
  if(axisChanged()){ const l=chart.lastLim; chart.prec=[precDigits(l[1]-l[0]),precDigits(l[3]-l[2])]; chart.draw(); setUserLimits(chart.getAxisLimits()); return; }
  const hit=chart.pick(px,py); if(hit){ toast(chart.xs+"="+jE(hit[0],4)+"\n"+chart.ys+"="+jE(hit[1],4)); chart.putPoint(hit[0],hit[1]); chart.draw(); return; }
  const a=chart.area(px,py);
  if(a==="X"||a==="Y"){ const list=filterLab(VARS.concat(DB.eq),lab()); if(!list.length){ toast("Nothing to select from!",true); return; }
    dialog({title:"Select "+a+" axis", items:list, selected:[a==="X"?chart.xs:chart.ys], onSelect:s=>{ if(a==="X") chart.xs=s[0]; else chart.ys=s[0]; safeReplot(false); }, onCancel:()=>toast("Changes cancelled.") }); return; }
  if(a!=="LIST"&&chart.r.maxX!=null&&chart.sel.length){ const p=chart.toReal(px,py); chart.putPoint(p[0],p[1]); chart.draw(); return; }
  const list=DB.titles.slice(); if(!list.length){ toast("Nothing to select from!",true); return; }
  dialog({items:list, multi:a==="LIST", selected:chart.sel.slice(), onSelect:s=>{ chart.sel=s.slice(); safeReplot(false); if(s.length===1) table.fill(Measurement.load(s[0])); }, onCancel:()=>toast("Changes cancelled.") }); }

/* ── SettingsActivity (preferences.xml) ────────────────────────────────── */
const PREFS=[
  {k:"lab", t:"Show controls for", type:"list", def:"ANY LAB", items:["LAB 1","LAB 2","ANY LAB"]},
  {k:"time_step_of_measurement_ms", t:"Time step of measurement", type:"num", def:"140", min:30, unit:"ms"},
  {k:"turn_off_LED_on_measurement_end", t:"Turn off LED current when measurement is done.", type:"sw", def:true},
  {k:"turn_off_heating_on_measurement_end", t:"Turn off heating current when measurement is done.", type:"sw", def:false},
  {k:"sweep_measurement", t:"Sweep measurement", s:"This setting will enable measuring I-V curve, by increasing current and measuring resulting voltage automatically in sweep mode.", type:"sw", def:false, dep:"lab"},
  {cat:"Sweep measurement settings", dep:"sweep_measurement"},
  {k:"min_sweep_led_current_mA", t:"Minimum sweep measurement current", type:"num", def:"0.1", min:0, max:49.5, unit:"mA", inCat:true},
  {k:"max_sweep_led_current_mA", t:"Maximum sweep measurement current", type:"num", def:"50", min:0.5, max:50, unit:"mA", inCat:true},
  {k:"sweep_measurement_points_number", t:"Number of steps of sweep measurement", type:"num", int:true, def:"51", min:3, max:500, inCat:true},
  {k:"sweep_geometric_current_increase", t:"Increase current exponentially", type:"sw", def:false, inCat:true},
  {k:"pulsed_current", t:"Set pulsed current", type:"sw", def:false, inCat:true},
  {k:"led_current_pulse_durations_ms", t:"Current pulse duration", type:"num", def:null, min:0.1, max:25.5, unit:"ms", inCat:true, dep2:"pulsed_current"},
  {cat:"Performance settings"},
  {k:"replot_each_n_timesteps", t:"Replot every … measurement timesteps", type:"num", int:true, def:"5", min:1}];
const fmtN=s=>{ const v=Number(s); return Number.isInteger(v)?String(v):String(v); };
function renderSettings(){ const el=$("actSet"); el.innerHTML=""; const l=P.str("lab","ANY LAB"); if(l==="LAB 1"&&DB.prefs.sweep_measurement) P.set("sweep_measurement",false);
  const sweepOn=P.bool("sweep_measurement",false);
  for(const p of PREFS){
    if(p.cat){ const c=document.createElement("div"); c.className="pcat"; c.textContent=p.cat; el.appendChild(c); continue; }
    const enabled=!(p.dep==="lab"&&l==="LAB 1")&&!(p.inCat&&!sweepOn)&&!(p.dep2&&!P.bool(p.dep2,false));
    const r=document.createElement("div"); r.className="pref"+(enabled?"":" off"); const tx=document.createElement("div"); tx.className="tx"; const b=document.createElement("b"); b.textContent=p.t; tx.appendChild(b);
    let sum=null; if(p.type==="list") sum=l; else if(p.type==="num"){ const v=p.k in DB.prefs?DB.prefs[p.k]:p.def; sum=(v==null?"null":String(v))+(p.unit?" "+p.unit:""); } else if(p.s) sum=p.s;
    if(sum!==null){ const s=document.createElement("small"); s.textContent=sum; tx.appendChild(s); } r.appendChild(tx);
    if(p.type==="sw"){ const s=document.createElement("span"); s.className="sw"+(P.bool(p.k,p.def)?" on":""); s.innerHTML="<i></i>"; r.appendChild(s); }
    if(enabled) r.onclick=()=>prefClick(p); el.appendChild(r); } }
function prefClick(p){ if(p.type==="sw"){ P.set(p.k,!P.bool(p.k,p.def)); renderSettings(); return; }
  if(p.type==="list"){ dialog({title:p.t, items:p.items, selected:[P.str(p.k,p.def)], small:true, onSelect:a=>{ P.set(p.k,a[0]); renderSettings(); } }); return; }
  const unitF=p.unit?" "+p.unit:""; let range=""; if(p.min!=null&&p.max!=null) range="From "+fmtN(p.min)+" to "+fmtN(p.max)+unitF; else if(p.min!=null) range="Min "+fmtN(p.min)+unitF; else if(p.max!=null) range="Max "+fmtN(p.max)+unitF;
  const cur=p.k in DB.prefs?DB.prefs[p.k]:(p.def==null?"":p.def);
  dialog({title:p.t, msg:range, input:String(cur), small:true, cancel:"Cancel", ok:"OK", onSelect:v=>{ v=String(v);
    let x=v===""&&p.def!=null?Number(p.def):Number(v); if(v.trim()===""&&p.def==null) x=NaN;
    if(p.def!=null&&(v===""||x===Number(p.def))){ P.set(p.k,v===""?p.def:v); renderSettings(); return; }
    let err=null; if(Number.isNaN(x)||(p.int&&!Number.isInteger(x))) err="Non-numeric (or badly formatted) value "+v+" !";
    else if(p.min!=null&&x<p.min) err=v+" less than minimum value "+fmtN(p.min)+" !"; else if(p.max!=null&&x>p.max) err=v+" greater than maximum value "+fmtN(p.max)+" !";
    if(err){ toast(err,true); return; } P.set(p.k,v); renderSettings(); } }); }
function openSettings(){ for(const p of PREFS) if(p.k&&!(p.k in DB.prefs)&&p.def!==null) DB.prefs[p.k]=p.def; dbSave(); renderSettings(); go("set"); }

/* ── EquationEditorActivity (portrait) ─────────────────────────────────── */
const KEYS=[ /* [text, left, top, width, height] in dp, from the editor's screen */
  ["sin",18,20,74,42],["cos",101,20,74,42],["tan",184,20,74,42],["exp",267,20,74,42],["()",420,20,50,42],
  ["asin",18,73,74,42],["acos",101,73,74,42],["atan",184,73,74,42],["ln",267,73,74,42],["del",361,73,50,42],["bsp",420,73,50,42],
  ["uC",18,272,69,42],["uL",95,272,69,42],["uT",172,272,69,42],
  ["duC",18,323,69,42],["duL",95,323,69,42],["duT",172,323,69,42],
  ["iL",95,374,69,42],["iH",172,374,69,42],["t",251,374,69,42],
  ["1",359,262,41,42],["2",407,262,41,42],["3",455,262,41,42],["e",503,262,41,42],
  ["4",359,313,41,42],["5",407,313,41,42],["6",455,313,41,42],[".",503,313,41,42],
  ["7",359,364,41,42],["8",407,364,41,42],["9",455,364,41,42],["0",503,364,41,42],
  ["+",359,420,41,42],["-",407,420,41,42],["*",455,420,41,42],["/",503,420,41,42],["^",551,420,41,42]];
const FNKEYS=["sin","cos","tan","exp","asin","acos","atan","ln"];
$("eqKeys").innerHTML=KEYS.map(([s,x,y,w,h])=>'<div class="key" data-k="'+s+'" style="left:'+x+'px;top:'+y+'px;width:'+w+'px;height:'+h+'px">'+s+"</div>").join("");
const eq=$("eqTxt");
function eqIns(s){ const p=eq.selectionStart||0; eq.value=eq.value.slice(0,p)+s+eq.value.slice(p); eq.setSelectionRange(p+s.length,p+s.length); }
function eqCur(d){ const p=Math.max(0,Math.min(eq.value.length,(eq.selectionStart||0)+d)); eq.setSelectionRange(p,p); }
for(const k of document.querySelectorAll("#eqKeys .key")) k.addEventListener("pointerdown",e=>{ e.preventDefault(); const s=k.dataset.k;
  if(FNKEYS.includes(s)){ eqIns(s); eqIns("()"); eqCur(-1); }
  else if(s==="()"){ eqIns("()"); eqCur(-1); }
  else if(s==="del"){ const p=eq.selectionStart||0; if(p<eq.value.length){ eq.value=eq.value.slice(0,p)+eq.value.slice(p+1); eq.setSelectionRange(p,p); } }
  else if(s==="bsp"){ const p=eq.selectionStart||0; if(p>0){ eq.value=eq.value.slice(0,p-1)+eq.value.slice(p); eq.setSelectionRange(p-1,p-1); } }
  else eqIns(s);
  eq.focus(); });
$("eqAdd").onclick=()=>{ const s=eq.value.trim(); if(s===""){ toast("Empty equation."); return; }
  if(!isValid(s)){ toast("Equation is invalid!"); eq.classList.add("bad"); return; } eq.classList.remove("bad"); DB.eq.push(s); dbSave(); toast("Saved equation "+s); };
$("eqDel").onclick=()=>{ const s=eq.value; if(!DB.eq.includes(s)){ toast("No such equation to remove."); return; } DB.eq.splice(DB.eq.indexOf(s),1); dbSave(); eq.value=""; };
$("eqSel").onclick=()=>{ const list=DB.eq.slice(); let cur=eq.value; if(!list.includes(cur)){ if(!list.length) toast("No equation created!"); else cur=list[0]; }
  if(!list.length) return; dialog({items:list, selected:[cur], onSelect:a=>{ eq.value=a[0]; }, onCancel:()=>toast("Selection cancelled.") }); };
function openEditor(){ go("eq"); }

/* ── activities, the Back button and the screen ────────────────────────── */
let act="main";
function go(a){ act=a; $("actMain").hidden=a!=="main"; $("actSet").hidden=a!=="set"; $("actEq").hidden=a!=="eq";
  if(EMBED) parent.postMessage({hl21app:{type:"orient",portrait:a==="eq"}},"*");
  if(a!=="main"&&!EMBED) history.pushState({a},""); fit(); if(a==="main") onResume(); }
function onResume(){ S.sweep=P.bool("sweep_measurement",false); const off=S.sweep;
  for(const id of ["etIL","etTL"]) $(id).disabled=off; $("sbIL").classList.toggle("off",off); $("sbTL").classList.toggle("off",off);
  const axOk=x=>VARS.includes(x)||DB.eq.includes(x); if(!axOk(chart.xs)||!axOk(chart.ys)){ if(!axOk(chart.xs)) chart.xs="t"; if(!axOk(chart.ys)) chart.ys="uC"; safeReplot(false); } else chart.draw();
  const l1=lab()==="LAB 1"; for(const id of ["lbIL","lbTL","etIL","etTL","unIL","unTL","sbIL","sbTL"]) $(id).hidden=l1; }
function back(){ if(dlgOpen()){ const d=$("dlgs").lastChild; d.remove(); return; }
  if(act!=="main"){ go("main"); return; }
  if(Date.now()-S.lastBack>4000){ toast('Press "back" again to close this app',true); S.lastBack=Date.now(); }
  else exitApp(); }
function exitApp(){ askToStop(); send({type:"bye"}); if(EMBED){ parent.postMessage({hl21app:{type:"exit"}},"*"); return; }
  $("closed").hidden=false; $("clTxt").textContent=lang==="ko"?"앱을 닫았습니다.":"The app was closed."; }
$("clOpen").onclick=()=>location.reload();
function osCmd(c){ if(c==="back") back(); else if(c==="pause"){ askToStop(); } }
addEventListener("popstate",()=>{ if(act!=="main") { act="main"; go("main"); } });
addEventListener("keydown",e=>{ if(e.key==="Escape") back(); });
$("navBack").onclick=back;
let SCALE=1, XF={rot:false,tx:0,ty:0};
/* a pointer position in the screen's dp, whether or not the screen is turned (Android landscape lock on a phone held upright) */
function scrPt(e){ return XF.rot?[(XF.ty-e.clientY)/SCALE,(e.clientX-XF.tx)/SCALE]:[(e.clientX-XF.tx)/SCALE,(e.clientY-XF.ty)/SCALE]; }
function offIn(el){ let x=0,y=0; while(el&&el.id!=="scr"){ x+=el.offsetLeft; y+=el.offsetTop; el=el.offsetParent; } return [x,y]; }
function fit(){ const des=act==="eq"?[600,912]:[960,552], nav=EMBED?0:48, W=des[0], H=des[1]+nav, vw=innerWidth, vh=innerHeight;
  const scr=$("scr"); scr.style.width=W+"px"; scr.style.height=H+"px"; $("nav").hidden=EMBED;
  const coarse=matchMedia("(pointer:coarse)").matches, rot=!EMBED&&coarse&&((vw<vh)!==(W<H));
  if(rot){ SCALE=Math.min(vh/W,vw/H); XF={rot:true,tx:(vw-H*SCALE)/2,ty:(vh+W*SCALE)/2}; scr.style.transform="translate("+XF.tx+"px,"+XF.ty+"px) rotate(-90deg) scale("+SCALE+")"; }
  else { SCALE=Math.min(vw/W,vh/H); XF={rot:false,tx:(vw-W*SCALE)/2,ty:(vh-H*SCALE)/2}; scr.style.transform="translate("+XF.tx+"px,"+XF.ty+"px) scale("+SCALE+")"; }
  for(const k in SB) SB[k].draw(); if(act==="main") chart.draw(); }
addEventListener("resize",fit);

/* ── pairing with the board (HaslaLab) ─────────────────────────────────── */
const TX={ko:{cP:"시뮬레이터(IPhO 2021 실험 페이지)에서 '내 기기 연결'을 고르면 나오는 6자리 코드를 입력하세요. QR 코드로 열었다면 이미 들어 있습니다.",
    cGo:"보드에 연결", cWait:"연결하는 중…", cFail:"보드를 찾지 못했습니다. 시뮬레이터 페이지가 열려 있고 코드가 맞는지 확인하세요.", cLost:"보드와의 연결이 끊겼습니다. 다시 연결하세요.",
    cSmall:"같은 컴퓨터의 다른 창은 곧바로, 다른 기기(태블릿 · 휴대폰)는 인터넷을 거쳐 직접(WebRTC) 연결됩니다. 연결되면 실제 시험 태블릿처럼 USB 접근 허용 → 보드 RESET 순서로 연결을 마칩니다. 앱은 원본처럼 영어입니다."},
  en:{cP:"Type the six-character code the simulator (IPhO 2021 experiment page) shows under 'link my own device'. If you opened this from the QR code, it is already in.",
    cGo:"Connect to the board", cWait:"Connecting…", cFail:"No board found. Check that the simulator page is open and the code is right.", cLost:"The link to the board was lost. Connect again.",
    cSmall:"A window on the same computer connects at once; another device (tablet, phone) connects directly over the internet (WebRTC). Once linked, finish as on the examination tablet: allow USB access, then press RESET on the board."}};
const T=()=>TX[lang];
function connText(){ $("cP").textContent=T().cP; $("cGo").textContent=T().cGo; $("cSmall").textContent=T().cSmall; $("cCode").placeholder="ABC123"; }
$("lgKo").onclick=()=>{ lang="ko"; connText(); }; $("lgEn").onclick=()=>{ lang="en"; connText(); };
function useEmbed(){ linkKind="embed"; send=m=>parent.postMessage({hl21app:m},"*");
  addEventListener("message",e=>{ if(e.source===parent&&e.data&&e.data.hl21board) onBoard(e.data.hl21board); });
  send({type:"hello"}); }
function tryBC(code){ return new Promise(res=>{ if(!("BroadcastChannel" in window)) return res(false);
  const bc=new BroadcastChannel("haslalab-ipho2021-"+code); let ok=false;
  bc.onmessage=e=>{ const m=e.data&&e.data.hl21board; if(!m) return; if(!ok&&m.type==="welcome"){ ok=true; linkKind="bc"; send=x=>bc.postMessage({hl21app:x}); res(true); } onBoard(m); };
  bc.postMessage({hl21app:{type:"hello"}}); setTimeout(()=>{ if(!ok){ bc.close(); res(false); } },900); }); }
function loadPeer(){ return new Promise((res,rej)=>{ if(window.Peer) return res(); const s=document.createElement("script");
  s.src="https://cdn.jsdelivr.net/npm/peerjs@1.5.4/dist/peerjs.min.js"; s.onload=()=>res(); s.onerror=rej; document.head.appendChild(s); }); }
async function tryPeer(code){ await loadPeer();
  const pq=Q.get("peer")||"", opt=pq?{host:pq.split(":")[0],port:+(pq.split(":")[1]||443),path:"/",secure:!/^(localhost|127\.|10\.|192\.168\.)/.test(pq)}:{};
  return new Promise(res=>{ const p=new Peer(opt); let done=false; const fail=()=>{ if(!done){ done=true; try{ p.destroy(); }catch(e){} res(false); } };
    p.on("error",fail); setTimeout(fail,20000);
    p.on("open",()=>{ const c=p.connect("haslalab-ipho2021-"+code,{reliable:true});
      c.on("open",()=>{ linkKind="peer"; send=m=>{ try{ c.send({hl21app:m}); }catch(e){} }; send({type:"hello"}); });
      c.on("data",d=>{ const m=d&&d.hl21board; if(!m) return; if(!done&&m.type==="welcome"){ done=true; res(true); } onBoard(m); });
      c.on("close",lost); c.on("error",fail); }); }); }
async function connect(){ const code=$("cCode").value.trim().toUpperCase(); if(code.length<4) return;
  $("cSt").textContent=T().cWait; $("cGo").disabled=true;
  const ok=(await tryBC(code))||(await tryPeer(code).catch(()=>false));
  $("cGo").disabled=false; if(!ok) $("cSt").textContent=T().cFail; else { $("cSt").textContent=""; history.replaceState(null,"","?code="+code+(Q.get("lang")?"&lang="+lang:"")+(Q.get("peer")?"&peer="+encodeURIComponent(Q.get("peer")):"")); } }
$("cGo").onclick=connect; $("cCode").onkeydown=e=>{ if(e.key==="Enter") connect(); };
function usePy(){ linkKind="py"; let since=0;
  send=m=>{ fetch("cmd",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(m)}).catch(()=>{}); };
  send({type:"hello"});
  (async function poll(){ for(;;){ try{ const r=await fetch("poll?since="+since,{cache:"no-store"}); const j=await r.json(); if(j.seq<since) since=0; else since=j.seq; for(const m of j.msgs) onBoard(m); }
    catch(e){ if(boardSeen) lost(); } await new Promise(r=>setTimeout(r,100)); } })(); }
addEventListener("pagehide",()=>{ try{ send({type:"bye"}); }catch(e){} });
document.addEventListener("visibilitychange",()=>{ if(document.hidden&&!EMBED) askToStop(); });

/* start: MainActivity.onCreate + onResume */
connText(); fit(); chart.init(); onResume();
if(EMBED) useEmbed();
else if(PY) usePy();
else { $("conn").hidden=false; const code=(Q.get("code")||"").toUpperCase(); $("cCode").value=code; if(code) connect(); }
</script>
</body>
</html>
'''
# the app's launcher icon (res/mipmap-xxxhdpi/ic_launcher.png of the APK), base64
APP_ICON = '''
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
'''
APP_MANIFEST = r'''{
  "name": "IPhO",
  "short_name": "IPhO",
  "start_url": "/app?py=1",
  "scope": "./",
  "display": "fullscreen",
  "orientation": "landscape",
  "background_color": "#ccaaaa",
  "theme_color": "#3f51b5",
  "icons": [{"src": "ipho2021_app_icon.png", "sizes": "192x192", "type": "image/png", "purpose": "any"}]
}
'''


def main():
    global LANG
    root = tk.Tk()
    _setup_hangul_font(root)
    root.geometry("1030x700")
    Sim(root)
    root.mainloop()


if __name__ == "__main__":
    main()
