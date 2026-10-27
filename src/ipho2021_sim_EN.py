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

import json
import math
import random
import socket
import threading
import time
import tkinter as tk
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from tkinter import ttk, messagebox

APP_VERSION = "1.0"

# ----------------------------------------------------------------------------
#  i18n
# ----------------------------------------------------------------------------
LANG = "EN"          # the EN edition differs only in this line (switchable from the menu too)

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
            self.iH = self.iL = 0.0
        self.t += dt

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

    # ---------------- instrument readings ----------------------------------
    def sample(self):
        """what the board sends to the tablet"""
        if not self.powered or not self.data_cable:
            return None
        uL = self.led_state()[0]      # always fresh: no lag after a current step
        return {
            "t": self.t,
            "uC": _q(self.uC, LSB_UC, SIG_UC, self.rng),
            "uT": _q(self.ntc_voltage(), LSB_UT, SIG_UT, self.rng),
            "uL": _q(uL, LSB_UL, SIG_UL, self.rng),
            "duC": self._duC + self.rng.gauss(0.0, 0.6e-3),
            "duT": self._duT + self.rng.gauss(0.0, 3.0e-4),
            "duL": self._duL + self.rng.gauss(0.0, 5.0e-3),
            "iL": self.iL,
            "iH": self.iH,
        }


# ============================================================================
#                       FUNCTION EDITOR  (expression engine)
# ============================================================================
VARIABLES = ["uC", "uT", "uL", "duC", "duT", "duL", "iL", "iH", "t"]
_ALLOWED = {"sin": math.sin, "cos": math.cos, "tan": math.tan, "exp": math.exp,
            "asin": math.asin, "acos": math.acos, "atan": math.atan,
            "ln": math.log, "abs": abs, "sqrt": math.sqrt}
import re as _re
_SAFE = _re.compile(r"^[0-9A-Za-z_+\-*/^(). ,e]*$")


class Expr:
    """Compiled user function, exactly like the app's equation editor."""

    def __init__(self, text):
        self.text = text.strip()
        py = self.text.replace("^", "**")
        if not _SAFE.match(py):
            raise ValueError("bad characters")
        stripped = _re.sub(r"\d+\.?\d*(?:[eE][+-]?\d+)?", " ", py)
        names = set(_re.findall(r"[A-Za-z_][A-Za-z_0-9]*", stripped))
        for n in names:
            if n not in VARIABLES and n not in _ALLOWED:
                raise ValueError("unknown name: " + n)
        self.code = compile(py, "<fx>", "eval")

    def __call__(self, row):
        env = dict(_ALLOWED)
        env.update(row)
        try:
            v = eval(self.code, {"__builtins__": {}}, env)
            return float(v)
        except Exception:
            return float("nan")


# ============================================================================
#                              CHART WIDGET
# ============================================================================
PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
           "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]


class Chart(tk.Canvas):
    """Simple scatter/line chart with manual limits and tap-to-read, like the
    chart area (28) of the IPhO 2021 app."""

    def __init__(self, master, **kw):
        super().__init__(master, bg="#fdf3e6", highlightthickness=0, **kw)
        self.series = []            # list of (label, [(x,y)...], color)
        self.xlim = [None, None]
        self.ylim = [None, None]
        self.xlabel, self.ylabel = "t", "uC"
        self.marker = None
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Button-1>", self._tap)
        self._px = (0, 0, 1, 1)
        self._sx = self._sy = (0.0, 1.0)

    # ---------------------------------------------------------------
    def set_series(self, series):
        self.series = series
        self.redraw()

    def _bounds(self):
        xs = [p[0] for _, pts, _ in self.series for p in pts if p[0] == p[0]]
        ys = [p[1] for _, pts, _ in self.series for p in pts if p[1] == p[1]]
        x0 = self.xlim[0] if self.xlim[0] is not None else (min(xs) if xs else 0.0)
        x1 = self.xlim[1] if self.xlim[1] is not None else (max(xs) if xs else 1.0)
        y0 = self.ylim[0] if self.ylim[0] is not None else (min(ys) if ys else 0.0)
        y1 = self.ylim[1] if self.ylim[1] is not None else (max(ys) if ys else 1.0)
        if x1 - x0 < 1e-12:
            x0, x1 = x0 - 0.5, x1 + 0.5
        if y1 - y0 < 1e-12:
            y0, y1 = y0 - 0.5, y1 + 0.5
        if self.ylim[0] is None and self.ylim[1] is None:
            m = 0.05 * (y1 - y0)
            y0, y1 = y0 - m, y1 + m
        return x0, x1, y0, y1

    @staticmethod
    def _ticks(a, b, n=6):
        span = b - a
        if span <= 0:
            return [a]
        raw = span / n
        mag = 10 ** math.floor(math.log10(raw))
        for m in (1, 2, 2.5, 5, 10):
            if raw / mag <= m:
                stepv = m * mag
                break
        first = math.ceil(a / stepv) * stepv
        out, v = [], first
        while v <= b + 1e-9 * span:
            out.append(v)
            v += stepv
        return out

    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 40 or h < 40:
            return
        L, Rm, Tp, B = 58, 12, 12, 34
        self._px = (L, Tp, w - Rm, h - B)
        x0, x1, y0, y1 = self._bounds()
        self._sx, self._sy = (x0, x1), (y0, y1)
        self.create_rectangle(L, Tp, w - Rm, h - B, fill="white", outline="#888")

        for xv in self._ticks(x0, x1):
            px = L + (xv - x0) / (x1 - x0) * (w - Rm - L)
            self.create_line(px, Tp, px, h - B, fill="#e3e3e3")
            self.create_text(px, h - B + 12, text=_fmt(xv), font=("TkDefaultFont", 8))
        for yv in self._ticks(y0, y1):
            py = (h - B) - (yv - y0) / (y1 - y0) * (h - B - Tp)
            self.create_line(L, py, w - Rm, py, fill="#e3e3e3")
            self.create_text(L - 5, py, text=_fmt(yv), anchor="e", font=("TkDefaultFont", 8))
        self.create_text((L + w - Rm) / 2, h - 8, text=self.xlabel, font=("TkDefaultFont", 9, "bold"))
        self.create_text(12, (Tp + h - B) / 2, text=self.ylabel, angle=90,
                         font=("TkDefaultFont", 9, "bold"))

        for idx, (label, pts, color) in enumerate(self.series):
            prev = None
            for (xv, yv) in pts:
                if xv != xv or yv != yv:
                    prev = None
                    continue
                if not (x0 <= xv <= x1 and y0 <= yv <= y1):
                    prev = None
                    continue
                px = L + (xv - x0) / (x1 - x0) * (w - Rm - L)
                py = (h - B) - (yv - y0) / (y1 - y0) * (h - B - Tp)
                if prev:
                    self.create_line(prev[0], prev[1], px, py, fill=color)
                self.create_oval(px - 1.6, py - 1.6, px + 1.6, py + 1.6,
                                 fill=color, outline=color)
                prev = (px, py)
            self.create_text(w - Rm - 8, Tp + 12 + 13 * idx, text=label,
                             anchor="e", fill=color, font=("TkDefaultFont", 8))
        if self.marker:
            px, py, txt = self.marker
            self.create_oval(px - 4, py - 4, px + 4, py + 4, outline="#c00", width=2)
            self.create_text(px, py - 12, text=txt, fill="#c00",
                             font=("TkDefaultFont", 8, "bold"))

    def _tap(self, ev):
        L, Tp, R, B = self._px
        if not (L <= ev.x <= R and Tp <= ev.y <= B):
            return
        x0, x1 = self._sx
        y0, y1 = self._sy
        best, bd = None, 1e18
        for _, pts, _c in self.series:
            for (xv, yv) in pts:
                if xv != xv or yv != yv:
                    continue
                px = L + (xv - x0) / (x1 - x0) * (R - L)
                py = B - (yv - y0) / (y1 - y0) * (B - Tp)
                d = (px - ev.x) ** 2 + (py - ev.y) ** 2
                if d < bd:
                    bd, best = d, (px, py, xv, yv)
        if best and bd < 900:
            self.marker = (best[0], best[1], "%s ; %s" % (_fmt(best[2], 5), _fmt(best[3], 5)))
        else:
            xv = x0 + (ev.x - L) / (R - L) * (x1 - x0)
            yv = y0 + (B - ev.y) / (B - Tp) * (y1 - y0)
            self.marker = (ev.x, ev.y, "%s ; %s" % (_fmt(xv, 5), _fmt(yv, 5)))
        self.redraw()


def _fmt(v, sig=4):
    if v != v:
        return "NaN"
    if v == 0:
        return "0"
    a = abs(v)
    if a >= 1e5 or a < 1e-4:
        return "%.*e" % (sig - 1, v)
    return ("%.*g" % (sig, v))


# ============================================================================
#                         TABLET  (IPhO 2021 Experiments app)
# ============================================================================
LED_MIN, LED_MAX = 0.0, 50.0        # mA   (app: "0..50")
HEAT_MIN, HEAT_MAX = 0.0, 500.0     # mA   (app: "0..500")
PULSE_MIN, PULSE_MAX = 0.1, 25.5    # ms   (app: "0.1 to 25.5 (0 is constant current)")


class Tablet(tk.Toplevel):
    def __init__(self, master, sim):
        super().__init__(master)
        self.sim = sim
        self.board = sim.board
        self.title("IPhO 2021 Experiments  —  " + T("tablet"))
        self.configure(bg="#111111")
        self.geometry("1180x720")
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        # ---------------- app state
        self.connected = False
        self.await_reset_until = -1.0
        self.perm_asked = False
        self.measuring = False
        self.checking = False
        self.rows = []                 # last measurement
        self.saved = {}                # name -> rows
        self.plotted = set()
        self.functions = []            # list of Expr
        self.columns = ["t", "uC", "duC"]
        self.yaxis, self.xaxis = "uC", "t"
        self.settings = dict(lab="ANY LAB", timestep=140, off_led=True, off_heat=False,
                             sweep=False, smin=0.1, smax=50.0, sn=51,
                             sexp=False, spulse=False, spw=1.0, replot=5)
        self._next_sample = 0.0
        self._sweep_i = -1
        self._replot_ctr = 0
        self._build()

    # ------------------------------------------------------------------ UI
    def _build(self):
        top = tk.Frame(self, bg="#f6e0c8")
        top.pack(side="top", fill="x")

        self.v_meas = tk.BooleanVar(value=False)
        self.v_check = tk.BooleanVar(value=False)
        r1 = tk.Frame(top, bg="#f6e0c8")
        r1.pack(fill="x", padx=6, pady=(4, 0))
        tk.Checkbutton(r1, text=T("meas"), variable=self.v_meas, bg="#f6e0c8",
                       command=self.toggle_measure).pack(side="left")
        self.e_title = tk.Entry(r1, width=18)
        self.e_title.pack(side="left", padx=6)
        self.e_title.insert(0, "")
        tk.Button(r1, text="+", fg="green", width=2, command=self.save_meas).pack(side="left")
        tk.Button(r1, text="✖", fg="red", width=2, command=self.del_meas).pack(side="left")
        tk.Button(r1, text=T("tapmeas"), command=self.pick_saved).pack(side="left", padx=4)
        tk.Button(r1, text="⟳", command=self.replot).pack(side="left", padx=(12, 4))
        tk.Label(r1, text="X =", bg="#f6e0c8").pack(side="left")
        self.e_xmin = tk.Entry(r1, width=7); self.e_xmin.pack(side="left")
        tk.Label(r1, text="…", bg="#f6e0c8").pack(side="left")
        self.e_xmax = tk.Entry(r1, width=7); self.e_xmax.pack(side="left")
        tk.Label(r1, text="  Y =", bg="#f6e0c8").pack(side="left")
        self.e_ymin = tk.Entry(r1, width=7); self.e_ymin.pack(side="left")
        tk.Label(r1, text="…", bg="#f6e0c8").pack(side="left")
        self.e_ymax = tk.Entry(r1, width=7); self.e_ymax.pack(side="left")

        r2 = tk.Frame(top, bg="#f6e0c8")
        r2.pack(fill="x", padx=6, pady=2)
        tk.Checkbutton(r2, text=T("check"), variable=self.v_check, bg="#f6e0c8",
                       command=self.toggle_check).pack(side="left")
        tk.Button(r2, text="⚙", command=self.open_settings).pack(side="left", padx=3)
        tk.Button(r2, text="ⓘ", command=self.show_summary).pack(side="left")

        self.e_ih = tk.Entry(r2, width=7); self.e_ih.insert(0, "0")
        self.e_il = tk.Entry(r2, width=7); self.e_il.insert(0, "0")
        self.e_tl = tk.Entry(r2, width=7); self.e_tl.insert(0, "0")
        self.s_ih = tk.Scale(r2, from_=0, to=1000, orient="horizontal", showvalue=False,
                             length=150, bg="#f6e0c8", command=lambda v: self._slider("iH", v))
        self.s_il = tk.Scale(r2, from_=0, to=1000, orient="horizontal", showvalue=False,
                             length=150, bg="#f6e0c8", command=lambda v: self._slider("iL", v))
        self.s_tl = tk.Scale(r2, from_=0, to=255, orient="horizontal", showvalue=False,
                             length=110, bg="#f6e0c8", command=lambda v: self._slider("tL", v))
        for lab, e, s in (("iH=", self.e_ih, self.s_ih), ("iL=", self.e_il, self.s_il),
                          ("tL=", self.e_tl, self.s_tl)):
            tk.Label(r2, text="  " + lab, bg="#f6e0c8").pack(side="left")
            e.pack(side="left"); s.pack(side="left", padx=(2, 6))
            tk.Label(r2, text="mA" if lab != "tL=" else "ms", bg="#f6e0c8").pack(side="left")
        for e, key in ((self.e_ih, "iH"), (self.e_il, "iL"), (self.e_tl, "tL")):
            e.bind("<Return>", lambda ev, k=key: self._entry_apply(k))
            e.bind("<FocusOut>", lambda ev, k=key: self._entry_apply(k))

        r3 = tk.Frame(top, bg="#f6e0c8")
        r3.pack(fill="x", padx=6, pady=(0, 4))
        tk.Button(r3, text="✎ f(x)", command=self.open_funcs).pack(side="left")
        self.colbtn = []
        for i in range(3):
            b = tk.Button(r3, text="f(x)", width=10, command=lambda i=i: self.pick_column(i))
            b.pack(side="left", padx=3)
            self.colbtn.append(b)
        self.lbl_status = tk.Label(r3, text="", bg="#f6e0c8", fg="#b00")
        self.lbl_status.pack(side="left", padx=14)

        body = tk.Frame(self, bg="#111")
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg="#dfe3f3")
        left.pack(side="left", fill="both", expand=False)
        self.live = tk.Label(left, text="", bg="#dfe3f3", justify="left",
                             font=("TkFixedFont", 11), anchor="nw")
        self.live.pack(fill="x", padx=6, pady=4)
        self.tree = ttk.Treeview(left, columns=("a", "b", "c"), show="headings", height=26)
        for c in ("a", "b", "c"):
            self.tree.column(c, width=118, anchor="e")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)

        right = tk.Frame(body, bg="#f6e0c8")
        right.pack(side="left", fill="both", expand=True)
        self.b_y = tk.Button(right, text=self.yaxis, command=lambda: self.pick_axis("y"))
        self.b_y.pack(side="left", padx=2)
        bot = tk.Frame(right, bg="#f6e0c8")
        bot.pack(side="bottom", fill="x")
        tk.Button(bot, text="• " + T("tapmeas"), command=self.pick_saved).pack(side="left", padx=4)
        self.b_x = tk.Button(bot, text=self.xaxis, command=lambda: self.pick_axis("x"))
        self.b_x.pack(side="right", padx=6)
        self.chart = Chart(right)
        self.chart.pack(fill="both", expand=True, padx=4, pady=4)
        self._update_colbtn()

    # -------------------------------------------------------------- helpers
    def toast(self, msg):
        self.lbl_status.config(text=msg)
        self.after(4000, lambda: self.lbl_status.config(text=""))

    def var_list(self):
        return VARIABLES + [f.text for f in self.functions]

    def eval_var(self, name, row):
        if name in row:
            return row[name]
        for f in self.functions:
            if f.text == name:
                return f(row)
        return float("nan")

    def _slider(self, key, v):
        v = float(v)
        if key == "iH":
            val = HEAT_MAX * v / 1000.0
            self.e_ih.delete(0, "end"); self.e_ih.insert(0, "%.1f" % val)
            self.board.iH = val
        elif key == "iL":
            val = 0.0 if v <= 0 else LED_MAX * (v / 1000.0) ** 3
            self.e_il.delete(0, "end"); self.e_il.insert(0, "%.2f" % val)
            self.board.iL = val
        else:
            val = v / 10.0
            self.e_tl.delete(0, "end"); self.e_tl.insert(0, "%.1f" % val)
            self.board.tL = val

    def _entry_apply(self, key):
        e = {"iH": self.e_ih, "iL": self.e_il, "tL": self.e_tl}[key]
        txt = e.get().strip()
        try:
            val = 0.0 if txt == "" else float(txt)
        except ValueError:
            self.toast(T("badheat") if key == "iH" else
                       (T("badled") if key == "iL" else T("badpulse")))
            return
        if key == "iH":
            if not (HEAT_MIN <= val <= HEAT_MAX):
                self.toast(T("badheat")); return
            self.board.iH = val
            self.s_ih.set(int(1000 * val / HEAT_MAX))
        elif key == "iL":
            if not (LED_MIN <= val <= LED_MAX):
                self.toast(T("badled")); return
            self.board.iL = val
            self.s_il.set(int(1000 * (val / LED_MAX) ** (1 / 3.0)))
        else:
            if val != 0.0 and not (PULSE_MIN <= val <= PULSE_MAX):
                self.toast(T("badpulse")); return
            self.board.tL = val
            self.s_tl.set(int(val * 10))

    # -------------------------------------------------------------- USB flow
    def poll_link(self):
        b = self.board
        if not (b.powered and b.data_cable):
            if self.connected or self.perm_asked:
                self.connected = False
                self.perm_asked = False
                self.await_reset_until = -1.0
                self.measuring = False
                self.v_meas.set(False)
                self.toast(T("usb_no"))
            return
        if self.connected:
            return
        if not self.perm_asked:
            self.perm_asked = True
            if messagebox.askyesno("USB", T("usb_perm"), parent=self):
                self.await_reset_until = self.sim.now + 10.0
                self.toast(T("press_reset"))
            else:
                self.toast(T("usb_denied"))
                self.perm_asked = False
                self.board.data_cable = False
            return
        if self.await_reset_until > 0:
            if b.reset_pressed_at > self.await_reset_until - 10.0:
                self.connected = True
                self.await_reset_until = -1.0
                b.t = 0.0
                self.toast(T("usb_ok"))
            elif self.sim.now > self.await_reset_until:
                self.await_reset_until = -1.0
                self.perm_asked = False
                self.toast(T("plug_first"))

    # ---------------------------------------------------------- acquisition
    def tick(self, now):
        """called by the simulation loop; `now` is simulated time (s)"""
        self.poll_link()
        dt = self.settings["timestep"] / 1000.0
        if not self.connected:
            self.live.config(text=T("usb_no"))
            return
        if now < self._next_sample:
            return
        self._next_sample = now + dt
        self.board.timestep = dt

        if self.measuring and self.settings["sweep"]:
            self._sweep_step()

        s = self.board.sample()
        if s is None:
            return
        row = dict(s)
        self._prev_sample = row
        if self.checking:
            self.live.config(text=self._live_text(row))
        if self.measuring:
            if self.rows:
                row["t"] = row["t"]
            self.rows.append(row)
            self._append_tree(row)
            self._replot_ctr += 1
            if self._replot_ctr >= self.settings["replot"]:
                self._replot_ctr = 0
                self.replot()

    _prev_sample = None

    def _live_text(self, r):
        return ("uC = %+9.4f V     duC = %+10.4f V/s\n"
                "uT = %+9.4f V     duT = %+10.4f V/s\n"
                "uL = %+9.4f V     duL = %+10.4f V/s\n"
                "iL = %8.3f mA    iH  = %8.1f mA\n"
                " t = %8.2f s" %
                (r["uC"], r["duC"], r["uT"], r["duT"], r["uL"], r["duL"],
                 r["iL"], r["iH"], r["t"]))

    def _sweep_step(self):
        st = self.settings
        self._sweep_i += 1
        n = max(2, int(st["sn"]))
        if self._sweep_i >= n:
            self.toggle_measure(force_off=True)
            return
        f = self._sweep_i / (n - 1.0)
        if st["sexp"]:
            lo = max(st["smin"], 1e-3)
            i = lo * (st["smax"] / lo) ** f
        else:
            i = st["smin"] + (st["smax"] - st["smin"]) * f
        self.board.iL = i
        self.board.tL = st["spw"] if st["spulse"] else 0.0
        self.e_il.delete(0, "end"); self.e_il.insert(0, "%.2f" % i)

    def toggle_measure(self, force_off=False):
        if force_off:
            self.v_meas.set(False)
        if not self.connected:
            self.v_meas.set(False)
            self.toast(T("plug_first"))
            return
        if self.v_meas.get():
            self.measuring = True
            self.rows = []
            self._prev_sample = None
            self._sweep_i = -1
            self.board.t = 0.0
            for i in self.tree.get_children():
                self.tree.delete(i)
        else:
            self.measuring = False
            if self.settings["off_led"]:
                self.board.iL = 0.0
                self.e_il.delete(0, "end"); self.e_il.insert(0, "0")
                self.s_il.set(0)
            if self.settings["off_heat"]:
                self.board.iH = 0.0
                self.e_ih.delete(0, "end"); self.e_ih.insert(0, "0")
                self.s_ih.set(0)
            self.toast(T("allstopped"))
            self.replot()

    def toggle_check(self):
        self.checking = self.v_check.get()
        if not self.checking:
            self.live.config(text="")

    # ---------------------------------------------------------- table/chart
    def _update_colbtn(self):
        for i, b in enumerate(self.colbtn):
            b.config(text=self.columns[i])
            self.tree.heading("abc"[i], text=self.columns[i])

    def _append_tree(self, row):
        vals = [_fmt(self.eval_var(c, row), 6) for c in self.columns]
        self.tree.insert("", "end", values=vals)
        if len(self.tree.get_children()) > 4000:
            self.tree.delete(self.tree.get_children()[0])
        self.tree.yview_moveto(1.0)

    def _refill_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in self.rows[-4000:]:
            self._append_tree(r)

    def replot(self):
        series = []
        idx = 0
        sets = []
        if "Last measurement" in self.plotted or not self.plotted:
            sets.append((T("lastmeas"), self.rows))
        for nm in sorted(self.plotted):
            if nm in self.saved:
                sets.append((nm, self.saved[nm]))
        for nm, rows in sets:
            pts = [(self.eval_var(self.xaxis, r), self.eval_var(self.yaxis, r)) for r in rows]
            series.append((nm, pts, PALETTE[idx % len(PALETTE)]))
            idx += 1
        self.chart.xlabel, self.chart.ylabel = self.xaxis, self.yaxis
        self.chart.xlim = [_num(self.e_xmin.get()), _num(self.e_xmax.get())]
        self.chart.ylim = [_num(self.e_ymin.get()), _num(self.e_ymax.get())]
        self.chart.marker = None
        self.chart.set_series(series)

    # ------------------------------------------------------------- dialogs
    def _chooser(self, title, options, multi=False, preset=()):
        dlg = tk.Toplevel(self)
        dlg.title(title)
        dlg.transient(self)
        dlg.grab_set()
        res = {"v": None}
        vars_ = []
        frm = tk.Frame(dlg)
        frm.pack(padx=14, pady=8, fill="both", expand=True)
        tk.Label(frm, text=title, font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=4)
        sel = tk.StringVar(value=options[0] if options else "")
        for o in options:
            if multi:
                v = tk.BooleanVar(value=(o in preset))
                tk.Checkbutton(frm, text=o, variable=v, anchor="w").pack(fill="x")
                vars_.append((o, v))
            else:
                tk.Radiobutton(frm, text=o, variable=sel, value=o, anchor="w").pack(fill="x")
        bar = tk.Frame(dlg); bar.pack(fill="x", pady=6)

        def ok():
            res["v"] = [o for o, v in vars_ if v.get()] if multi else sel.get()
            dlg.destroy()
        tk.Button(bar, text=T("cancel"), command=dlg.destroy).pack(side="right", padx=6)
        tk.Button(bar, text=T("select"), command=ok).pack(side="right")
        self.wait_window(dlg)
        return res["v"]

    def pick_axis(self, which):
        opts = self.var_list()
        v = self._chooser(T("sel_y") if which == "y" else T("sel_x"), opts)
        if not v:
            return
        if which == "y":
            self.yaxis = v; self.b_y.config(text=v)
        else:
            self.xaxis = v; self.b_x.config(text=v)
        self.replot()

    def pick_column(self, i):
        v = self._chooser(T("sel_col"), self.var_list())
        if v:
            self.columns[i] = v
            self._update_colbtn()
            self._refill_tree()

    def pick_saved(self):
        opts = [T("lastmeas")] + sorted(self.saved)
        pre = set(self.plotted)
        if not self.plotted:
            pre.add(T("lastmeas"))
        v = self._chooser(T("tapmeas"), opts, multi=True, preset=pre)
        if v is None:
            return
        self.plotted = set(x if x != T("lastmeas") else "Last measurement" for x in v)
        self.replot()

    def save_meas(self):
        nm = self.e_title.get().strip()
        if not nm:
            self.toast(T("notitle")); return
        if nm in self.saved:
            self.toast(T("exists")); return
        if not self.rows:
            self.toast(T("nomeas")); return
        self.saved[nm] = list(self.rows)
        self.plotted.add(nm)
        self.toast(T("saved_n", nm, len(self.rows)))
        self.replot()

    def del_meas(self):
        nm = self.e_title.get().strip()
        if nm in self.saved:
            del self.saved[nm]
            self.plotted.discard(nm)
            self.toast(nm + " " + T("deleted"))
            self.replot()
        else:
            self.toast(T("nomeas"))

    def open_funcs(self):
        dlg = tk.Toplevel(self); dlg.title(T("funceditor")); dlg.grab_set()
        e = tk.Entry(dlg, width=52); e.pack(padx=10, pady=8)
        lb = tk.Listbox(dlg, width=52, height=8); lb.pack(padx=10)
        for f in self.functions:
            lb.insert("end", f.text)
        tk.Label(dlg, text="uC uT uL duC duT duL iL iH t | sin cos tan exp asin acos atan ln"
                 "  |  * / ^ + -", fg="#555").pack(padx=10, pady=4)

        def add():
            try:
                fx = Expr(e.get())
            except Exception as ex:
                messagebox.showerror(T("enterfunc"), str(ex), parent=dlg); return
            if fx.text and all(fx.text != g.text for g in self.functions):
                self.functions.append(fx)
                lb.insert("end", fx.text)

        def rm():
            s = lb.curselection()
            if s:
                txt = lb.get(s[0])
                self.functions = [g for g in self.functions if g.text != txt]
                lb.delete(s[0])
        bar = tk.Frame(dlg); bar.pack(pady=8)
        tk.Button(bar, text="+", fg="green", width=3, command=add).pack(side="left", padx=4)
        tk.Button(bar, text="✖", fg="red", width=3, command=rm).pack(side="left", padx=4)
        tk.Button(bar, text="OK", command=dlg.destroy).pack(side="left", padx=12)

    def show_summary(self):
        st = self.settings
        messagebox.showinfo("Current settings:",
                            "%s: %s\n%s: %d ms\n%s: %s\n%s: %s\n%s: %.3g…%.3g mA / %d steps\n"
                            "%s: %s   %s: %s (%.1f ms)" %
                            (T("showctrl"), st["lab"], T("timestep"), st["timestep"],
                             T("offled"), st["off_led"], T("offheat"), st["off_heat"],
                             T("sweep"), st["smin"], st["smax"], st["sn"],
                             T("sweepexp"), st["sexp"], T("sweeppulse"), st["spulse"], st["spw"]),
                            parent=self)

    def open_settings(self):
        if self.measuring:
            self.toast(T("duringmeas")); return
        st = self.settings
        dlg = tk.Toplevel(self); dlg.title(T("settings")); dlg.grab_set()
        dlg.configure(bg="#f6e0c8")
        f = tk.Frame(dlg, bg="#f6e0c8"); f.pack(padx=16, pady=10, fill="both")
        row = [0]

        def line(label, widget):
            tk.Label(f, text=label, bg="#f6e0c8", anchor="w").grid(row=row[0], column=0, sticky="w", pady=3)
            widget.grid(row=row[0], column=1, sticky="w", padx=8)
            row[0] += 1

        v_lab = tk.StringVar(value=st["lab"])
        line(T("showctrl"), ttk.Combobox(f, textvariable=v_lab, width=10,
                                         values=["LAB 1", "LAB 2", "ANY LAB"], state="readonly"))
        v_ts = tk.StringVar(value=str(st["timestep"]))
        line(T("timestep") + " (ms)", tk.Entry(f, textvariable=v_ts, width=10))
        v_ol = tk.BooleanVar(value=st["off_led"])
        line(T("offled"), tk.Checkbutton(f, variable=v_ol, bg="#f6e0c8"))
        v_oh = tk.BooleanVar(value=st["off_heat"])
        line(T("offheat"), tk.Checkbutton(f, variable=v_oh, bg="#f6e0c8"))
        v_sw = tk.BooleanVar(value=st["sweep"])
        line(T("sweep"), tk.Checkbutton(f, variable=v_sw, bg="#f6e0c8"))
        tk.Label(f, text=T("sweepset"), fg="#b04030", bg="#f6e0c8").grid(
            row=row[0], column=0, sticky="w", pady=(8, 2)); row[0] += 1
        v_mn = tk.StringVar(value=str(st["smin"])); line(T("sweepmin") + " (mA)", tk.Entry(f, textvariable=v_mn, width=10))
        v_mx = tk.StringVar(value=str(st["smax"])); line(T("sweepmax") + " (mA)", tk.Entry(f, textvariable=v_mx, width=10))
        v_n = tk.StringVar(value=str(st["sn"])); line(T("sweepn"), tk.Entry(f, textvariable=v_n, width=10))
        v_ex = tk.BooleanVar(value=st["sexp"]); line(T("sweepexp"), tk.Checkbutton(f, variable=v_ex, bg="#f6e0c8"))
        v_pu = tk.BooleanVar(value=st["spulse"]); line(T("sweeppulse"), tk.Checkbutton(f, variable=v_pu, bg="#f6e0c8"))
        v_pw = tk.StringVar(value=str(st["spw"])); line(T("pulsedur") + " (ms)", tk.Entry(f, textvariable=v_pw, width=10))

        def apply():
            try:
                st["lab"] = v_lab.get()
                st["timestep"] = max(20, min(500, int(float(v_ts.get()))))
                st["off_led"] = v_ol.get(); st["off_heat"] = v_oh.get()
                st["sweep"] = v_sw.get()
                st["smin"] = max(0.0, min(LED_MAX, float(v_mn.get())))
                st["smax"] = max(0.0, min(LED_MAX, float(v_mx.get())))
                st["sn"] = max(2, min(2000, int(float(v_n.get()))))
                st["sexp"] = v_ex.get(); st["spulse"] = v_pu.get()
                pw = float(v_pw.get())
                st["spw"] = 0.0 if pw == 0 else max(PULSE_MIN, min(PULSE_MAX, pw))
            except ValueError:
                messagebox.showerror(T("settings"), "Non-numeric (or badly formatted) value", parent=dlg)
                return
            dlg.destroy()
        tk.Button(dlg, text=T("apply"), command=apply).pack(pady=8)


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
            self.create_rectangle(x - 63, y - 39, x + 63, y + 39, fill="#f6e0c8", outline="",
                                  tags="tablet")
            self.create_text(x, y, text="IPhO 2021\nExperiments", font=("TkDefaultFont", 8),
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
                    self.board.reset_pressed_at = self.sim.now
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
        self.stream, self.ts, self.next, self.epoch = False, 0.140, 0.0, 0
        self.sweep, self.sweep_i, self.sweep_done = None, -1, False
        self.out, self.last_link, self.last_clock, self.last_reset = [], None, 0.0, None
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
                elif u.path == "/ipho2021_app_icon.svg":
                    self._send(200, APP_ICON, "image/svg+xml")
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
                        link.seen = time.time()
                self._send(200, "{}", "application/json")
        return H

    def alive(self):
        return time.time() - self.seen < 3.0

    def to_app(self, m):
        with self.lock:
            self.seq += 1
            self.outbox.append((self.seq, m))
            if len(self.outbox) > 3000:
                del self.outbox[:1000]

    def link_on(self):
        b = self.sim.board
        return bool(b.powered and b.data_cable and self.alive())

    def handle(self):
        with self.lock:
            msgs, self.inbox = self.inbox, []
        for m in msgs:
            self.from_app(m)

    def from_app(self, m):
        b, t = self.sim.board, m.get("type")
        if t == "hello":
            self.to_app({"type": "welcome", "lang": LANG.lower(), "state": {"iH": b.iH, "iL": b.iL, "tL": b.tL}})
            self.last_link = None
        elif t == "stream":
            self.stream = bool(m.get("on")) and self.link_on()
            if m.get("ts"):
                self.ts = max(0.02, min(0.5, float(m["ts"])))
                b.timestep = self.ts
            self.next = self.sim.now
        elif t == "zero":
            b.t = 0.0
            self.next = self.sim.now
            self.epoch = m.get("epoch", 0)
        elif t == "set" and b.powered:
            if isinstance(m.get("iH"), (int, float)):
                b.iH = max(0.0, min(500.0, float(m["iH"])))
            if isinstance(m.get("iL"), (int, float)):
                b.iL = max(0.0, min(50.0, float(m["iL"])))
            if isinstance(m.get("tL"), (int, float)):
                b.tL = float(m["tL"])
        elif t == "sweep":
            self.sweep, self.sweep_i = m.get("cfg"), -1

    def step(self, now):
        """the board firmware: one sample every time step while the app streams"""
        if not self.stream:
            return
        if not self.link_on():
            self.stream, self.sweep = False, None
            return
        if now < self.next:
            return
        b = self.sim.board
        self.next = now + self.ts
        b.timestep = self.ts
        if self.sweep:
            c = self.sweep
            n = max(2, int(c.get("n", 2)))
            self.sweep_i += 1
            if self.sweep_i >= n:
                self.sweep, self.sweep_done = None, True
                return
            f = self.sweep_i / (n - 1.0)
            lo = max(float(c.get("min", 0)), 1e-3)
            hi = float(c.get("max", 50))
            b.iL = lo * (hi / lo) ** f if c.get("exp") else float(c.get("min", 0)) + (hi - float(c.get("min", 0))) * f
            b.tL = float(c.get("pw") or 0.0)
        s = b.sample()
        if s:
            s = dict(s)
            s["tL"], s["ep"] = b.tL, self.epoch
            self.out.append(s)

    def flush(self, now):
        b = self.sim.board
        on = self.link_on()
        if on != self.last_link:
            self.last_link = on
            self.to_app({"type": "link", "on": on, "now": now})
        if self.last_reset is None:
            self.last_reset = b.reset_pressed_at
        if b.reset_pressed_at != self.last_reset:
            self.last_reset = b.reset_pressed_at
            self.to_app({"type": "reset", "at": b.reset_pressed_at})
        if self.out:
            self.to_app({"type": "samples", "list": self.out, "now": now})
            self.out = []
        if self.sweep_done:
            self.sweep_done = False
            self.to_app({"type": "sweepDone"})
        if time.time() - self.last_clock > 0.2:
            self.last_clock = time.time()
            self.to_app({"type": "clock", "now": now})


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
        keep = None
        if self.tablet:
            keep = (self.tablet.saved, self.tablet.functions, self.tablet.rows,
                    self.tablet.settings, self.tablet.connected)
            self.tablet.destroy()
            self.tablet = None
        self.bench.destroy()
        self._menu()
        self.root.title(T("title"))
        self.bench = Bench(self.root, self)
        self.bench.pack(side="top", fill="both", expand=True)
        if keep:
            self.show_tablet()
            (self.tablet.saved, self.tablet.functions, self.tablet.rows,
             self.tablet.settings, self.tablet.connected) = keep
            self.tablet.perm_asked = keep[4]

    def flash(self, txt):
        self.msg.config(text=txt)
        self.root.after(1500, lambda: self.msg.config(text=""))

    def reset_bench(self):
        self.board = Board()
        self.bench.destroy()
        self.bench = Bench(self.root, self)
        self.bench.pack(side="top", fill="both", expand=True)
        if self.tablet:
            self.tablet.board = self.board
            self.tablet.connected = False
            self.tablet.perm_asked = False

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
            self.tablet.withdraw()
        self.link.stream = False
        self.link.last_link = None
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
            self.tablet = Tablet(self.root, self)
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
            if remote:
                self.link.step(self.now + (k + 1) * dt)
        self.now += want
        if remote:
            self.link.flush(self.now)
            if self.remote_win is not None and self.remote_win.winfo_exists() and hasattr(self, "remote_status"):
                ok = self.link.alive()
                self.remote_status.config(text=T("remote_ok") if ok else T("remote_wait"), fg="#1e8449" if ok else "#9a6a00")
        elif self.tablet is not None and self.tablet.winfo_exists():
            self.tablet.tick(self.now)
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
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#c2662d">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="IPhO 2021">
<link rel="manifest" href="ipho2021_app.webmanifest">
<link rel="icon" href="ipho2021_app_icon.svg" type="image/svg+xml">
<title>IPhO 2021 Experiments · HaslaLab</title>
<meta name="description" content="The IPhO 2021 Experiments app for the HaslaLab virtual board: open it on your own tablet, phone or computer and connect it to the simulator.">
<style>
  *{box-sizing:border-box}
  [hidden]{display:none!important}
  html,body{margin:0;padding:0;height:100%}
  body{background:#0e0f11;color:#222;font:13px/1.35 -apple-system,'Segoe UI',Roboto,'Malgun Gothic',sans-serif}
  .abar{display:flex;align-items:center;gap:10px;background:#c2662d;color:#fff;padding:0 12px;height:40px;font-weight:600;font-size:15px}
  .abar .sub{margin-left:auto;font-weight:400;font-size:11.5px;opacity:.9}
  #tab{position:relative;background:#0e0f11;min-height:calc(100% - 40px)}
  .tbar{display:flex;flex-wrap:wrap;gap:5px;align-items:center;background:#f6e0c8;padding:4px 6px;border-bottom:1px solid #e2c8aa}
  .tbar label{display:flex;align-items:center;gap:3px;font-weight:600}
  .tbar input:not([type]),.tbar input[size]{background:#fff;border:1px solid #c9b294;border-radius:3px;padding:2px 4px;font:12px ui-monospace,Consolas,monospace;color:#111}
  .tbar input[type=range]{width:110px;accent-color:#c2662d}
  .tbar button,.mbox button{width:auto;margin:0;padding:3px 8px;background:#fff;color:#222;border:1px solid #c9b294;border-radius:4px;font-size:12px;cursor:pointer}
  .tbar button.ok,.mbox button.ok{color:#1e8449;font-weight:700}.tbar button.no{color:#c0392b;font-weight:700}
  .tbar select,.axisx select,.axisy select{background:#fff;border:1px solid #c9b294;border-radius:3px;font-size:12px;padding:1px 3px;color:#111}
  .toast{color:#b03020;font-weight:600;margin-left:8px}
  .tbody{display:flex;gap:4px;background:#111}
  .tleft{width:36%;background:#dfe3f3;display:flex;flex-direction:column;min-width:0}
  #tLive{margin:4px 6px;font:12px/1.45 ui-monospace,Consolas,monospace;min-height:16px;white-space:pre;overflow:auto}
  #tTable{flex:1;overflow:auto;max-height:300px;font:11.5px ui-monospace,Consolas,monospace;margin:0 4px 4px;background:#fff}
  #tTable table{border-collapse:collapse;width:100%}#tTable th{position:sticky;top:0;background:#c9cfe6;font-weight:600}
  #tTable td,#tTable th{padding:1px 5px;text-align:right;border-bottom:1px solid #eef}
  .tright{flex:1;background:#f6e0c8;display:flex;flex-direction:column;min-width:0;position:relative}
  #chart{width:100%;height:330px;display:block}
  .axisx{text-align:right;padding:2px 6px}.axisy{position:absolute;left:4px;top:4px;z-index:2}
  @media (max-width:700px){ .tbody{flex-direction:column} .tleft{width:100%} #tTable{max-height:180px} }
  .modal{position:fixed;inset:0;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;z-index:5}
  .mbox{background:#fbf4ea;color:#111;border-radius:8px;padding:14px 16px;min-width:280px;max-width:92%;max-height:88%;overflow:auto;box-shadow:0 6px 20px rgba(0,0,0,.4)}
  .mbox label{display:flex;align-items:center;gap:6px;margin:4px 0}.mbox input:not([type]){border:1px solid #c9b294;border-radius:3px;padding:3px 5px;margin:4px 0}
  .mrow{display:flex;gap:8px;justify-content:flex-end;margin-top:10px}.hintsm{font-size:11px;color:#666;margin:4px 0}
  .mbox .fx{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:2px 0;font:12px ui-monospace,Consolas,monospace}
  /* the Android system dialog for USB access */
  .sysd{background:#fff;color:#202124;border-radius:10px;padding:20px 22px 10px;width:330px;max-width:92%;box-shadow:0 10px 30px rgba(0,0,0,.45);font-family:Roboto,'Segoe UI','Malgun Gothic',sans-serif}
  .sysd p{margin:0 0 14px;font-size:15px;line-height:1.45}
  .sysd .mrow button{background:none;border:0;color:#1a73e8;font-weight:600;font-size:14px;padding:8px 10px;cursor:pointer;text-transform:uppercase}
  /* connecting to the board */
  #conn{position:fixed;inset:40px 0 0 0;background:#f6e0c8;display:flex;align-items:center;justify-content:center;z-index:8;padding:16px}
  .cbox{background:#fff;border:1px solid #e2c8aa;border-radius:12px;padding:20px 22px;max-width:440px;width:100%;box-shadow:0 8px 24px rgba(0,0,0,.12)}
  .cbox h2{margin:0 0 6px;font-size:17px;color:#7a3a12}
  .cbox p{margin:6px 0;color:#444;font-size:13px;line-height:1.55}
  .cbox input{font:600 22px ui-monospace,Consolas,monospace;letter-spacing:.25em;text-transform:uppercase;width:100%;padding:8px 10px;border:1px solid #c9b294;border-radius:6px;text-align:center;margin:8px 0}
  .cbox button{width:100%;padding:10px;border-radius:6px;border:0;background:#c2662d;color:#fff;font-weight:700;font-size:14px;cursor:pointer}
  .cbox .st{margin-top:10px;font-weight:600;color:#b03020;min-height:1.4em}
  .cbox .small{font-size:11.5px;color:#777}
</style>
</head>
<body>
<div class="abar"><span>IPhO 2021 Experiments</span><span class="sub" id="aSub"></span></div>

<div id="conn" hidden>
  <div class="cbox">
    <h2 id="cH"></h2>
    <p id="cP"></p>
    <input id="cCode" maxlength="6" autocomplete="off" spellcheck="false">
    <button id="cGo"></button>
    <div class="st" id="cSt"></div>
    <p class="small" id="cSmall"></p>
  </div>
</div>

<div id="tab">
  <div class="tbar">
    <label><input type="checkbox" id="tMeas"> <span id="l-meas"></span></label>
    <input id="tTitle" size="14">
    <button id="tSave" class="ok">+</button><button id="tDel" class="no">✖</button>
    <button id="tPick"></button>
    <button id="tReplot">⟳</button>
    <span>X =</span><input id="tXmin" size="5"><span>…</span><input id="tXmax" size="5">
    <span>Y =</span><input id="tYmin" size="5"><span>…</span><input id="tYmax" size="5">
  </div>
  <div class="tbar">
    <label><input type="checkbox" id="tCheck"> <span id="l-check"></span></label>
    <button id="tSet">⚙</button>
    <span>iH=</span><input id="tIH" size="6" value="0"><input type="range" id="sIH" min="0" max="1000" value="0"><span>mA</span>
    <span>iL=</span><input id="tIL" size="6" value="0"><input type="range" id="sIL" min="0" max="1000" value="0"><span>mA</span>
    <span>tL=</span><input id="tTL" size="5" value="0"><input type="range" id="sTL" min="0" max="255" value="0"><span>ms</span>
  </div>
  <div class="tbar">
    <button id="tFx">✎ f(x)</button>
    <select id="col0"></select><select id="col1"></select><select id="col2"></select>
    <span id="tToast" class="toast"></span>
  </div>
  <div class="tbody">
    <div class="tleft"><pre id="tLive"></pre><div id="tTable"></div></div>
    <div class="tright">
      <div class="axisy"><select id="tY"></select></div>
      <canvas id="chart"></canvas>
      <div class="axisx"><select id="tX"></select></div>
    </div>
  </div>
</div>
<div class="modal" id="mUsb" hidden><div class="sysd"><p id="l-perm"></p><div class="mrow"><button id="bDeny"></button><button id="bAllow"></button></div></div></div>
<div class="modal" id="mPick" hidden><div class="mbox"><b id="l-pick"></b><div id="pickList"></div><div class="mrow"><button id="pickCancel"></button><button id="pickOk"></button></div></div></div>
<div class="modal" id="mFx" hidden><div class="mbox"><b id="l-fx"></b><input id="fxIn" size="40"><div class="hintsm">uC uT uL duC duT duL iL iH t | sin cos tan exp asin acos atan ln | * / ^ + −</div><div id="fxList"></div><div class="mrow"><button id="fxAdd" class="ok">+</button><button id="fxOk">OK</button></div></div></div>
<div class="modal" id="mSet" hidden><div class="mbox" id="setBox"></div></div>

<script>
"use strict";
/* ══════════════════════════════════════════════════════════════
   THE IPhO 2021 EXPERIMENTS APP
   It talks to the HaslaLab measurement board over one of three links:
     embed  - inside the simulator's virtual tablet (postMessage)
     bc     - a window on the same computer (BroadcastChannel)
     peer   - another device: tablet, phone, computer (WebRTC via PeerJS)
   The board streams raw samples; the app records, tabulates and plots
   them.  Nothing is derived for the student.
   ══════════════════════════════════════════════════════════════ */
const Q=new URLSearchParams(location.search);
let lang=Q.get("lang")==="en"?"en":"ko";
const EMBED=Q.get("embed")==="1";
const A={
  ko:{meas:"Measure", check:"Check state", pick:"Tap for measurements", last:"Last measurement", usbNo:"No USB connected", perm:"IPhO 2021 Experiments 앱이 USB 장치(HaslaLab IPhO 2021 board)에 접근하도록 허용할까요?", allow:"허용", deny:"거부",
      pressReset:"10초 안에 보드의 RESET 버튼을 누르세요!", connected:"장치가 연결되었습니다.", plugFirst:"먼저 보드를 연결하고 전원을 켠 뒤 리셋하세요.", denied:"USB 접근이 허용되지 않았습니다",
      noTitle:"측정 이름이 입력되지 않았습니다!", exists:"같은 이름이 이미 있습니다!", noMeas:"해당 이름의 측정이 없습니다", saved:(n,k)=>'"'+n+'" 저장됨 ('+k+"개)", deleted:n=>n+" 삭제됨",
      during:"측정 중에는 할 수 없습니다.", badLed:"LED 전류 값이 잘못되었습니다!", badHeat:"히터 전류 값이 잘못되었습니다!", badPulse:"LED 펄스 폭 값이 잘못되었습니다!", stopped:"측정이 멈췄습니다.",
      cancel:"취소", select:"선택", fx:"함수 편집기", bad:"식을 읽을 수 없습니다", set:"설정", ts:"측정 시간 간격 (ms)", offLed:"측정 종료 시 LED 전류 끄기", offHeat:"측정 종료 시 히터 전류 끄기",
      sweep:"스윕 측정", smin:"스윕 최소 전류 (mA)", smax:"스윕 최대 전류 (mA)", sn:"스윕 단계 수", sexp:"전류를 지수적으로 증가", spulse:"펄스 전류 사용", spw:"펄스 폭 (ms)", apply:"적용",
      cH:"HaslaLab 보드에 연결", cP:"시뮬레이터(IPhO 2021 실험 페이지)의 '내 태블릿 · 컴퓨터' 화면에 나온 연결 코드 6자리를 입력하세요. QR 코드로 열었다면 코드가 이미 들어 있습니다.",
      cGo:"연결", cWait:"연결하는 중…", cFail:"보드를 찾지 못했습니다. 시뮬레이터 페이지가 열려 있고 코드가 맞는지 확인하세요.", cLost:"보드와의 연결이 끊겼습니다. 다시 연결하세요.",
      cSmall:"같은 컴퓨터의 다른 창은 곧바로, 다른 기기(태블릿 · 휴대폰)는 인터넷을 거쳐 직접 연결됩니다. 이 앱은 홈 화면에 추가해 설치할 수 있습니다.",
      subEmbed:"", subLink:k=>"보드 링크: "+k},
  en:{meas:"Measure", check:"Check state", pick:"Tap for measurements", last:"Last measurement", usbNo:"No USB connected", perm:"Allow the app IPhO 2021 Experiments to access the USB device (HaslaLab IPhO 2021 board)?", allow:"ALLOW", deny:"DENY",
      pressReset:"Please press RESET button on the board in 10 seconds!", connected:"Device connected.", plugFirst:"Please plug in, power on and reset the board first.", denied:"USB Permission not granted",
      noTitle:"No measurement title entered!", exists:"This name already exists!", noMeas:"No measurement with this title exists", saved:(n,k)=>'"'+n+'" saved ('+k+" pts)", deleted:n=>n+" deleted",
      during:"You don't want to do this during measurement.", badLed:"Bad value of LED current!", badHeat:"Bad heater current value!", badPulse:"Bad value of LED current pulse width entered!", stopped:"All running measurements stopped.",
      cancel:"CANCEL", select:"SELECT", fx:"Function Editor", bad:"Cannot read the expression", set:"Settings", ts:"Time step of measurement (ms)", offLed:"Turn off LED current when measurement is done.", offHeat:"Turn off heating current when measurement is done.",
      sweep:"Sweep measurement", smin:"Minimum sweep current (mA)", smax:"Maximum sweep current (mA)", sn:"Number of sweep steps", sexp:"Increase current exponentially", spulse:"Set pulsed current", spw:"Pulse duration (ms)", apply:"Apply",
      cH:"Connect to the HaslaLab board", cP:"Type the six-character code shown on the simulator's (IPhO 2021 experiment page) 'my tablet or computer' screen. If you opened this from the QR code, the code is already in.",
      cGo:"Connect", cWait:"Connecting…", cFail:"No board found. Check that the simulator page is open and the code is right.", cLost:"The link to the board was lost. Connect again.",
      cSmall:"A window on the same computer connects at once; another device (tablet, phone) connects directly over the internet. You can install this app by adding it to your home screen.",
      subEmbed:"", subLink:k=>"board link: "+k}
};
const $=id=>document.getElementById(id);
const a=()=>A[lang];

/* ---- the link to the board ------------------------------------------------- */
let send=()=>{}, linkKind="", boardSeen=false;
function onBoard(m){ if(!m||typeof m!=="object") return;
  switch(m.type){
    case "welcome": boardSeen=true; $("conn").hidden=true; if(m.lang&&!Q.get("lang")){ lang=m.lang; applyLang(); } if(m.state) showState(m.state); $("aSub").textContent=EMBED?"":a().subLink(linkKind); break;
    case "lang": lang=m.lang==="en"?"en":"ko"; applyLang(); break;
    case "link": link=!!m.on; if(typeof m.now==="number") simNow=m.now; pollLink(); break;
    case "clock": simNow=m.now; pollLink(); break;
    case "reset": lastReset=m.at; pollLink(); break;
    case "samples": simNow=m.now; for(const s of m.list) onSample(s); pollLink(); break;
    case "sweepDone": if(measuring) setMeasure(false); break;
    case "state": showState(m); break;
    case "bye": lost(); break;
  }
}
function lost(){ boardSeen=false; link=false; pollLink(); if(!EMBED){ $("conn").hidden=false; $("cSt").textContent=a().cLost; } }
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
  return new Promise(res=>{ const p=new Peer(); let done=false; const fail=()=>{ if(!done){ done=true; try{ p.destroy(); }catch(e){} res(false); } };
    p.on("error",fail); setTimeout(fail,15000);
    p.on("open",()=>{ const c=p.connect("haslalab-ipho2021-"+code,{reliable:true});
      c.on("open",()=>{ linkKind="peer"; send=m=>{ try{ c.send({hl21app:m}); }catch(e){} }; send({type:"hello"}); });
      c.on("data",d=>{ const m=d&&d.hl21board; if(!m) return; if(!done&&m.type==="welcome"){ done=true; res(true); } onBoard(m); });
      c.on("close",lost); c.on("error",fail); }); }); }
async function connect(){ const code=$("cCode").value.trim().toUpperCase(); if(code.length<4) return;
  $("cSt").textContent=a().cWait; $("cGo").disabled=true;
  const ok=(await tryBC(code))||(await tryPeer(code).catch(()=>false));
  $("cGo").disabled=false; if(!ok) $("cSt").textContent=a().cFail; else { $("cSt").textContent=""; history.replaceState(null,"","?code="+code+(Q.get("lang")?"&lang="+lang:"")); } }
$("cGo").onclick=connect; $("cCode").onkeydown=e=>{ if(e.key==="Enter") connect(); };

/* ---- the app proper (guide G1) ------------------------------------------------ */
const VARS=["uC","uT","uL","duC","duT","duL","iL","iH","t"], FUNCS={sin:Math.sin,cos:Math.cos,tan:Math.tan,exp:Math.exp,asin:Math.asin,acos:Math.acos,atan:Math.atan,ln:Math.log,abs:Math.abs,sqrt:Math.sqrt};
const PALETTE=["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"];
const LED_MAX=50, HEAT_MAX=500, PULSE_MIN=0.1, PULSE_MAX=25.5;
let link=false, simNow=0, lastReset=-1e9;
let connected=false, permAsked=false, awaitUntil=-1, denied=false, measuring=false, checking=false, linkWas=false;
let epoch=0, rows=[], saved={}, plotted=new Set(["__last"]), functions=[], columns=["t","uC","duC"], xaxis="t", yaxis="uC", replotCtr=0;
const settings={timestep:140, offLed:true, offHeat:false, sweep:false, smin:0.1, smax:50, sn:51, sexp:false, spulse:false, spw:1.0};
function compileExpr(txt){
  const t=txt.trim(); if(!t) throw new Error("empty");
  const js=t.replace(/\^/g,"**"); if(!/^[0-9A-Za-z_+\-*/(). ,e]*$/.test(js.replace(/\*\*/g,"*"))) throw new Error("bad characters");
  const names=(js.replace(/\d+\.?\d*(?:[eE][+-]?\d+)?/g," ").match(/[A-Za-z_][A-Za-z_0-9]*/g)||[]);
  for(const n of names) if(!VARS.includes(n)&&!(n in FUNCS)) throw new Error("unknown name: "+n);
  const f=new Function(...VARS,...Object.keys(FUNCS),"return ("+js+");");
  return {text:t, fn:r=>{ try{ const v=f(...VARS.map(k=>r[k]),...Object.values(FUNCS)); return typeof v==="number"?v:NaN; }catch(e){ return NaN; } }};
}
const varList=()=>[...VARS,...functions.map(f=>f.text)];
function evalVar(name,r){ if(name in r) return r[name]; const f=functions.find(g=>g.text===name); return f?f.fn(r):NaN; }
function fmt(v){ if(!isFinite(v)) return "NaN"; const x=Math.abs(v); if(x!==0&&(x<1e-3||x>=1e5)) return v.toExponential(4); return Number(v.toPrecision(6)).toString(); }
let toastT=null;
function toast(s){ $("tToast").textContent=s; clearTimeout(toastT); toastT=setTimeout(()=>{ $("tToast").textContent=""; },4000); }
function pollLink(){
  if(!link){ if(connected||permAsked||linkWas){ if(measuring) setMeasure(false,true); connected=false; permAsked=false; awaitUntil=-1; $("mUsb").hidden=true; send({type:"stream",on:false}); if(linkWas) toast(a().usbNo); }
    linkWas=false; denied=false; $("tLive").textContent=a().usbNo; return; }
  linkWas=true;
  if(connected||denied) return;
  if(!permAsked){ permAsked=true; $("mUsb").hidden=false; return; }
  if(awaitUntil>0){ if(lastReset>awaitUntil-10){ connected=true; awaitUntil=-1; send({type:"zero"}); send({type:"stream",on:true,ts:settings.timestep/1000}); toast(a().connected); $("tLive").textContent=""; }
    else if(simNow>awaitUntil){ awaitUntil=-1; permAsked=false; toast(a().plugFirst); } }
}
$("bAllow").onclick=()=>{ $("mUsb").hidden=true; awaitUntil=simNow+10; toast(a().pressReset); };
$("bDeny").onclick=()=>{ $("mUsb").hidden=true; denied=true; permAsked=false; toast(a().denied); };
function liveText(r){ const f=(v,w,p)=>((v>=0?"+":"")+v.toFixed(p)).padStart(w," ");
  return "uC ="+f(r.uC,10,4)+" V    duC ="+f(r.duC,11,4)+" V/s\nuT ="+f(r.uT,10,4)+" V    duT ="+f(r.duT,11,4)+" V/s\nuL ="+f(r.uL,10,4)+" V    duL ="+f(r.duL,11,4)+" V/s\niL ="+r.iL.toFixed(3).padStart(9," ")+" mA   iH  ="+r.iH.toFixed(1).padStart(8," ")+" mA\nt  ="+r.t.toFixed(3).padStart(10," ")+" s"; }
function onSample(s){ if(!connected) return; if(measuring&&s.ep!==epoch) return;
  if(checking) $("tLive").textContent=liveText(s);
  if(measuring){ rows.push(s); appendRow(s); if(settings.sweep){ $("tIL").value=s.iL.toFixed(2); $("sIL").value=Math.round(1000*Math.cbrt(s.iL/LED_MAX)); $("tTL").value=s.tL!==undefined?s.tL:$("tTL").value; }
    if(++replotCtr>=5){ replotCtr=0; replot(); } } }
function setMeasure(on,quiet){
  if(on&&!connected){ $("tMeas").checked=false; toast(a().plugFirst); return; }
  $("tMeas").checked=on;
  if(on){ measuring=true; rows=[]; refillTable(); epoch++; send({type:"zero",epoch});
    send({type:"sweep",cfg:settings.sweep?{min:settings.smin,max:settings.smax,n:settings.sn,exp:settings.sexp,pw:settings.spulse?settings.spw:0}:null}); }
  else { measuring=false; send({type:"sweep",cfg:null});
    if(settings.offLed) setDrive("iL",0,false); if(settings.offHeat) setDrive("iH",0,false);
    if(!quiet) toast(a().stopped); replot(); }
}
$("tMeas").onchange=e=>setMeasure(e.target.checked);
$("tCheck").onchange=e=>{ checking=e.target.checked; if(!checking) $("tLive").textContent=connected?"":a().usbNo; };
function setDrive(key,val,fromSlider){
  if(key==="iH"){ if(!(val>=0&&val<=HEAT_MAX)){ toast(a().badHeat); return; } send({type:"set",iH:val}); if(!fromSlider){ $("sIH").value=Math.round(1000*val/HEAT_MAX); $("tIH").value=String(val); } else $("tIH").value=val.toFixed(1); }
  if(key==="iL"){ if(!(val>=0&&val<=LED_MAX)){ toast(a().badLed); return; } send({type:"set",iL:val}); if(!fromSlider){ $("sIL").value=Math.round(1000*Math.cbrt(val/LED_MAX)); $("tIL").value=String(val); } else $("tIL").value=val.toFixed(2); }
  if(key==="tL"){ if(val!==0&&!(val>=PULSE_MIN&&val<=PULSE_MAX)){ toast(a().badPulse); return; } send({type:"set",tL:val}); if(!fromSlider){ $("sTL").value=Math.round(val*10); $("tTL").value=String(val); } else $("tTL").value=val.toFixed(1); }
}
function showState(s){ if(typeof s.iH==="number"){ $("tIH").value=String(s.iH); $("sIH").value=Math.round(1000*s.iH/HEAT_MAX); }
  if(typeof s.iL==="number"){ $("tIL").value=String(+s.iL.toFixed(3)); $("sIL").value=Math.round(1000*Math.cbrt(s.iL/LED_MAX)); }
  if(typeof s.tL==="number"){ $("tTL").value=String(s.tL); $("sTL").value=Math.round(s.tL*10); } }
for(const [k,inp,sl,f] of [["iH","tIH","sIH",v=>HEAT_MAX*v/1000],["iL","tIL","sIL",v=>v<=0?0:LED_MAX*Math.pow(v/1000,3)],["tL","tTL","sTL",v=>v/10]]){
  $(inp).onchange=()=>{ const t=$(inp).value.trim(); const v=t===""?0:Number(t); if(isNaN(v)){ toast(k==="iH"?a().badHeat:k==="iL"?a().badLed:a().badPulse); return; } setDrive(k,v,false); };
  $(sl).oninput=()=>setDrive(k,f(+$(sl).value),true); }
function fillSelects(){ const opts=varList();
  for(let i=0;i<3;i++){ const s=$("col"+i); s.innerHTML=opts.map(o=>"<option>"+o.replace(/</g,"&lt;")+"</option>").join(""); s.value=columns[i]; }
  for(const [id,v] of [["tX",xaxis],["tY",yaxis]]){ const s=$(id); s.innerHTML=opts.map(o=>"<option>"+o.replace(/</g,"&lt;")+"</option>").join(""); s.value=v; } }
for(let i=0;i<3;i++) $("col"+i).onchange=e=>{ columns[i]=e.target.value; refillTable(); };
$("tX").onchange=e=>{ xaxis=e.target.value; replot(); }; $("tY").onchange=e=>{ yaxis=e.target.value; replot(); };
for(const id of ["tXmin","tXmax","tYmin","tYmax"]) $(id).onchange=replot;
$("tReplot").onclick=replot;
function rowHtml(r){ return "<tr>"+columns.map(c=>"<td>"+fmt(evalVar(c,r))+"</td>").join("")+"</tr>"; }
function refillTable(){ const last=rows.slice(-300); $("tTable").innerHTML="<table><thead><tr>"+columns.map(c=>"<th>"+c.replace(/</g,"&lt;")+"</th>").join("")+"</tr></thead><tbody>"+last.map(rowHtml).join("")+"</tbody></table>"; const el=$("tTable"); el.scrollTop=el.scrollHeight; }
function appendRow(r){ const tb=$("tTable").querySelector("tbody"); if(!tb){ refillTable(); return; } tb.insertAdjacentHTML("beforeend",rowHtml(r)); if(tb.children.length>300) tb.removeChild(tb.firstChild); const el=$("tTable"); el.scrollTop=el.scrollHeight; }
$("tSave").onclick=()=>{ const nm=$("tTitle").value.trim(); if(!nm){ toast(a().noTitle); return; } if(saved[nm]){ toast(a().exists); return; } if(!rows.length){ toast(a().noMeas); return; }
  saved[nm]=rows.slice(); plotted.add(nm); toast(a().saved(nm,rows.length)); replot(); };
$("tDel").onclick=()=>{ const nm=$("tTitle").value.trim(); if(saved[nm]){ delete saved[nm]; plotted.delete(nm); toast(a().deleted(nm)); replot(); } else toast(a().noMeas); };
$("tPick").onclick=()=>{ const opts=["__last",...Object.keys(saved).sort()];
  $("pickList").innerHTML=opts.map(o=>'<label><input type="checkbox" value="'+o.replace(/"/g,"&quot;")+'"'+(plotted.has(o)?" checked":"")+"> "+(o==="__last"?a().last:o.replace(/</g,"&lt;"))+"</label>").join("");
  $("mPick").hidden=false; };
$("pickCancel").onclick=()=>{ $("mPick").hidden=true; };
$("pickOk").onclick=()=>{ plotted=new Set([...$("pickList").querySelectorAll("input:checked")].map(i=>i.value)); $("mPick").hidden=true; replot(); };
function renderFx(){ $("fxList").innerHTML=functions.map((f,i)=>'<div class="fx"><span>'+f.text.replace(/</g,"&lt;")+'</span><button data-i="'+i+'" class="no">✖</button></div>').join("");
  for(const b of $("fxList").querySelectorAll("button")) b.onclick=()=>{ functions.splice(+b.dataset.i,1); renderFx(); fillSelects(); }; }
$("tFx").onclick=()=>{ renderFx(); $("mFx").hidden=false; };
$("fxAdd").onclick=()=>{ try{ const f=compileExpr($("fxIn").value); if(!functions.some(g=>g.text===f.text)) functions.push(f); $("fxIn").value=""; renderFx(); fillSelects(); }catch(e){ toast(a().bad+": "+e.message); } };
$("fxOk").onclick=()=>{ $("mFx").hidden=true; };
$("tSet").onclick=()=>{ if(measuring){ toast(a().during); return; } const t=a(), s=settings;
  const chk=(id,v,l)=>'<label><input type="checkbox" id="'+id+'"'+(v?" checked":"")+"> "+l+"</label>", num=(id,v,l)=>'<label>'+l+' <input id="'+id+'" size="7" value="'+v+'"></label>';
  $("setBox").innerHTML="<b>"+t.set+"</b>"+num("sTs",s.timestep,t.ts)+chk("sOl",s.offLed,t.offLed)+chk("sOh",s.offHeat,t.offHeat)+chk("sSw",s.sweep,t.sweep)+num("sMn",s.smin,t.smin)+num("sMx",s.smax,t.smax)+num("sN",s.sn,t.sn)+chk("sEx",s.sexp,t.sexp)+chk("sPu",s.spulse,t.spulse)+num("sPw",s.spw,t.spw)+'<div class="mrow"><button id="sCancel">'+t.cancel+'</button><button id="sApply" class="ok">'+t.apply+"</button></div>";
  $("mSet").hidden=false;
  $("sCancel").onclick=()=>{ $("mSet").hidden=true; };
  $("sApply").onclick=()=>{ const n=id=>Number($(id).value); if([n("sTs"),n("sMn"),n("sMx"),n("sN"),n("sPw")].some(isNaN)){ toast("Non-numeric value"); return; }
    s.timestep=Math.max(20,Math.min(500,Math.round(n("sTs")))); s.offLed=$("sOl").checked; s.offHeat=$("sOh").checked; s.sweep=$("sSw").checked;
    s.smin=Math.max(0,Math.min(LED_MAX,n("sMn"))); s.smax=Math.max(0,Math.min(LED_MAX,n("sMx"))); s.sn=Math.max(2,Math.min(2000,Math.round(n("sN"))));
    s.sexp=$("sEx").checked; s.spulse=$("sPu").checked; const pw=n("sPw"); s.spw=pw===0?0:Math.max(PULSE_MIN,Math.min(PULSE_MAX,pw)); $("mSet").hidden=true;
    if(connected) send({type:"stream",on:true,ts:s.timestep/1000}); }; };
/* the chart */
const chartCv=$("chart"), chartCtx=chartCv.getContext("2d"); let CW=600, CH=330;
function sizeChart(){ const r=chartCv.getBoundingClientRect(), dpr=window.devicePixelRatio||1; CW=Math.max(200,r.width); CH=330; chartCv.width=Math.round(CW*dpr); chartCv.height=Math.round(CH*dpr); replot(); }
const numOr=(id)=>{ const v=$(id).value.trim(); return v===""||isNaN(+v)?null:+v; };
function niceTicks(lo,hi,n){ const span=hi-lo; if(!(span>0)) return [lo]; const st0=Math.pow(10,Math.floor(Math.log10(span/n))), st=[1,2,5,10].map(k=>k*st0).find(s=>span/s<=n)||st0*10; const out=[]; for(let v=Math.ceil(lo/st)*st;v<=hi+1e-9*span;v+=st) out.push(Math.abs(v)<st*1e-9?0:v); return out; }
function replot(){
  const dpr=window.devicePixelRatio||1, c=chartCtx; c.setTransform(dpr,0,0,dpr,0,0); c.fillStyle="#fffaf3"; c.fillRect(0,0,CW,CH);
  const sets=[]; if(plotted.has("__last")) sets.push([a().last,rows]); for(const nm of [...plotted].filter(x=>x!=="__last").sort()) if(saved[nm]) sets.push([nm,saved[nm]]);
  const series=sets.map(([nm,rs],i)=>[nm,rs.map(r=>[evalVar(xaxis,r),evalVar(yaxis,r)]).filter(p=>isFinite(p[0])&&isFinite(p[1])),PALETTE[i%PALETTE.length]]);
  let xs=[],ys=[]; for(const [,pts] of series) for(const [x,y] of pts){ xs.push(x); ys.push(y); }
  let x0=numOr("tXmin"), x1=numOr("tXmax"), y0=numOr("tYmin"), y1=numOr("tYmax");
  if(x0===null) x0=xs.length?Math.min(...xs):0; if(x1===null) x1=xs.length?Math.max(...xs):1; if(y0===null) y0=ys.length?Math.min(...ys):0; if(y1===null) y1=ys.length?Math.max(...ys):1;
  if(x1-x0<1e-12){ x0-=0.5; x1+=0.5; } if(y1-y0<1e-12){ const m=Math.abs(y0)*0.05||0.5; y0-=m; y1+=m; }
  const L=64, R=12, T0=10, Bm=30, X=x=>L+(x-x0)/(x1-x0)*(CW-L-R), Y=y=>CH-Bm-(y-y0)/(y1-y0)*(CH-Bm-T0);
  c.strokeStyle="#ddd"; c.lineWidth=1; c.font="11px ui-monospace,Consolas,monospace"; c.fillStyle="#444";
  for(const t of niceTicks(x0,x1,7)){ const x=X(t); c.beginPath(); c.moveTo(x,T0); c.lineTo(x,CH-Bm); c.stroke(); c.textAlign="center"; c.textBaseline="top"; c.fillText(fmt(t),x,CH-Bm+4); }
  for(const t of niceTicks(y0,y1,6)){ const y=Y(t); c.beginPath(); c.moveTo(L,y); c.lineTo(CW-R,y); c.stroke(); c.textAlign="right"; c.textBaseline="middle"; c.fillText(fmt(t),L-4,y); }
  c.strokeStyle="#666"; c.strokeRect(L,T0,CW-L-R,CH-Bm-T0);
  c.save(); c.beginPath(); c.rect(L,T0,CW-L-R,CH-Bm-T0); c.clip();
  for(const [,pts,col] of series){ c.fillStyle=col; for(const [x,y] of pts){ c.fillRect(X(x)-1.5,Y(y)-1.5,3,3); } }
  c.restore();
  let ly=T0+6; c.textAlign="left"; c.textBaseline="top"; c.font="11px -apple-system,'Segoe UI','Malgun Gothic',sans-serif";
  for(const [nm,,col] of series){ c.fillStyle=col; c.fillRect(CW-R-130,ly+3,8,8); c.fillStyle="#333"; c.fillText(nm,CW-R-118,ly); ly+=15; }
}
function applyLang(){ const t=a(); document.documentElement.lang=lang;
  $("l-meas").textContent=t.meas; $("l-check").textContent=t.check; $("tPick").textContent=t.pick; $("l-perm").textContent=t.perm; $("bAllow").textContent=t.allow; $("bDeny").textContent=t.deny;
  $("l-pick").textContent=t.pick; $("pickCancel").textContent=t.cancel; $("pickOk").textContent=t.select; $("l-fx").textContent=t.fx;
  $("cH").textContent=t.cH; $("cP").textContent=t.cP; $("cGo").textContent=t.cGo; $("cSmall").textContent=t.cSmall;
  if(!connected) $("tLive").textContent=t.usbNo; if(boardSeen&&!EMBED) $("aSub").textContent=t.subLink(linkKind);
  fillSelects(); replot(); }
addEventListener("resize",sizeChart);
if("ResizeObserver" in window) new ResizeObserver(()=>{ const r=chartCv.getBoundingClientRect(); if(r.width>0&&Math.abs(r.width-CW)>1) sizeChart(); }).observe(chartCv);
applyLang(); sizeChart();
/* the Python edition serves this page from the student's own computer; the app polls it */
function usePy(){ linkKind="py"; let since=0;
  send=m=>{ fetch("cmd",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(m)}).catch(()=>{}); };
  $("conn").hidden=true; send({type:"hello"});
  (async function poll(){ for(;;){ try{ const r=await fetch("poll?since="+since,{cache:"no-store"}); const j=await r.json(); if(j.seq<since) since=0; else since=j.seq; for(const m of j.msgs) onBoard(m); }
    catch(e){ if(boardSeen) lost(); } await new Promise(r=>setTimeout(r,120)); } })(); }
addEventListener("pagehide",()=>{ try{ send({type:"bye"}); }catch(e){} });
if(EMBED) useEmbed();
else if(Q.get("py")==="1") usePy();
else { $("conn").hidden=false; const code=(Q.get("code")||"").toUpperCase(); $("cCode").value=code; if(code) connect(); }
</script>
</body>
</html>
'''
APP_ICON = r'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96"><rect width="96" height="96" rx="20" fill="#c2662d"/><path d="M14 64 C30 64 34 26 50 26 S70 52 82 52" fill="none" stroke="#f6e0c8" stroke-width="6" stroke-linecap="round"/><text x="48" y="84" font-family="Arial,Helvetica,sans-serif" font-size="18" font-weight="700" fill="#fff" text-anchor="middle">2021</text></svg>'''
APP_MANIFEST = r'''{
  "name": "IPhO 2021 Experiments (HaslaLab)",
  "short_name": "IPhO 2021",
  "start_url": "/app?py=1",
  "scope": "./",
  "display": "standalone",
  "orientation": "landscape",
  "background_color": "#f6e0c8",
  "theme_color": "#c2662d",
  "icons": [{"src": "ipho2021_app_icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}]
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
