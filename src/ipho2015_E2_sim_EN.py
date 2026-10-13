#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  46th International Physics Olympiad  (IPhO 2015, Mumbai, India)
  Experimental Problem E-II :  DIFFRACTION DUE TO SURFACE TENSION WAVES ON WATER
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Only instrument readings are shown: the light meter (lux), the digital
    multimeter (V), the vernier caliper (mm), the tape (cm) and the position
    scales.  No wavelength, wave number, surface tension, viscosity or angle
    is ever computed or displayed for the student.
    All hidden true parameters are randomised for every session.
"""

import math
import random
import tkinter as tk
from tkinter import ttk, messagebox

LANG = "en"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "ko" else en


LAM = 635e-9          # laser wavelength [m]
RHO = 1000.0          # water density   [kg/m^3]


# --------------------------------------------------------------------------
# Bessel functions of the first kind (integer order), power series
# --------------------------------------------------------------------------

_FACT = [1.0]
for _i in range(1, 40):
    _FACT.append(_FACT[-1] * _i)


def besselJ(m, x):
    if x < 0:
        return besselJ(m, -x) * (1 if m % 2 == 0 else -1)
    h = 0.5 * x
    s = 0.0
    for i in range(0, 32):
        t = ((-1.0) ** i) / (_FACT[i] * _FACT[i + m]) * h ** (2 * i + m)
        s += t
        if abs(t) < 1e-18 and i > m:
            break
    return s


# --------------------------------------------------------------------------
# Hidden physics
# --------------------------------------------------------------------------


class E2Physics:
    """True, hidden state of the water sample and of the optical bench."""

    def __init__(self, seed=None):
        r = random.Random(seed)
        self.seed = seed

        self.sigma = r.uniform(0.0570, 0.0625)     # surface tension  [N/m]
        self.eta = r.uniform(0.00088, 0.00099)     # viscosity      [Pa s]
        self.theta = math.radians(r.uniform(3.70, 4.35))   # glancing angle
        self.q = 3                                 # exponent in eq. (2)

        # geometry [m]
        self.l2 = r.uniform(0.050, 0.061)          # incidence point -> edge
        self.c1 = r.uniform(0.760, 0.812)          # edge -> track origin
        self.y_base = r.uniform(0.0020, 0.0060)    # caliper reading offset
        self.x_mark = r.uniform(-0.9, 0.9)         # tray/scale zero offset [cm]

        # vibrator coupling :  h0 = A * Vrms**0.4
        self.A = r.uniform(4.30e-6, 4.95e-6)

        # optics
        self.gain = r.uniform(1420.0, 1560.0)      # lux at the specular spot
        self.spot = r.uniform(0.24e-3, 0.29e-3)    # effective spot sigma [m]
        self.dark = r.uniform(0.0, 0.6)            # stray light [lux]

        # tolerances of the instruments
        self.cal_res = 0.01                        # mm
        self.tape_res = 0.1                        # cm
        self.dmm_gain = r.uniform(0.995, 1.005)    # d.m.m. calibration
        self.lux_noise = 0.004                     # relative, r.m.s.

    # ---- derived, hidden --------------------------------------------------
    def k_of_f(self, f):
        """Wave number of the surface tension wave of frequency f."""
        return (4.0 * math.pi ** 2 * f * f * RHO / self.sigma) ** (1.0 / 3.0)

    def delta_of_f(self, f):
        """Attenuation constant, eq. (5)."""
        return 8.0 * math.pi * self.eta * f / (3.0 * self.sigma)

    def lambda_c(self):
        return 2.0 * math.pi * math.sqrt(self.sigma / (RHO * 9.81))


# --------------------------------------------------------------------------
# Apparatus / assembly
# --------------------------------------------------------------------------

PARTS = [
    ("platform", "6",  "나무 플랫폼",              "Wooden platform",            "floor_platform"),
    ("psu",      "8",  "DC 안정화 전원공급장치",   "DC regulated power supply",  "table_psu"),
    ("tablet",   "3",  "태블릿 (사인파 발생기)",   "Tablet (sine generator)",    "table_tablet"),
    ("ctrlbox",  "5",  "바이브레이터 컨트롤 박스", "Vibrator control box",       "table_ctrl"),
    ("dmm",      "4",  "디지털 멀티미터",          "Digital multimeter",         "table_dmm"),
    ("meter",    "1",  "조도계",                   "Light meter",                "table_meter"),
    ("track",    "7",  "광센서 이동 트랙",         "Track for the light sensor", "plat_track"),
    ("tray",     "12", "물 트레이",                "Water tray",                 "plat_tray"),
    ("vib",      "11", "바이브레이터 조립체",      "Vibrator assembly",          "plat_vib"),
    ("laser2",   "15", "레이저 광원 2 (635 nm)",   "Laser source 2 (635 nm)",    "plat_laser"),
    ("scale10",  "10", "눈금자 + 위치 표시자",     "Scale with position marker", "plat_scale"),
    ("base",     "2b", "스크린 베이스",            "Screen base",                "track_base"),
    ("sensor",   "2",  "광센서 + 버니어 캘리퍼",   "Light sensor on caliper",    "base_sensor"),
    ("cover",    "13", "플라스틱 커버",            "Plastic cover",              "plat_cover"),
    ("cyl",      "17", "500 ml 메스실린더",        "500 ml measuring cylinder",  "table_tools"),
    ("water",    "16", "실험용 물 시료 (500 ml)",  "Water sample (500 ml)",      "tray_water"),
    ("tape",     "9a", "줄자 / 플라스틱 자",       "Measuring tape / scale",     "table_tools"),
    ("hexkey",   "9b", "육각 렌치",                "Hex key",                    "table_tools"),
]
PART_BY_KEY = {p[0]: p for p in PARTS}

PREREQ = {
    "track": {"platform"},
    "tray": {"platform"},
    "vib": {"platform"},
    "laser2": {"platform"},
    "scale10": {"platform"},
    "cover": {"tray", "vib", "laser2"},
    "base": {"track"},
    "sensor": {"base", "hexkey"},
    "water": {"tray", "cyl"},
}

# cable / connector list :  key -> (from, to, prerequisites)
CABLES = [
    ("audio",  "[36] \u2192 [22]", "오디오 핀 \u2192 태블릿",
     "audio pin \u2192 tablet", {"tablet", "ctrlbox"}),
    ("vibpin", "[38] \u2192 [34]", "바이브레이터 케이블 \u2192 컨트롤 박스",
     "vibrator cable \u2192 control box", {"vib", "ctrlbox"}),
    ("dmmwire", "[41] \u2194 [32]", "멀티미터 \u2194 컨트롤 박스",
     "multimeter \u2194 control box", {"dmm", "ctrlbox"}),
    ("usb",    "[35] \u2192 [44]", "USB \u2192 전원공급장치",
     "USB \u2192 power supply", {"ctrlbox", "psu"}),
    ("laser",  "[42] \u2192 [45]", "레이저 2 커넥터 \u2192 전원공급장치",
     "laser 2 connector \u2192 power supply", {"laser2", "psu"}),
    ("sensorw", "\u2192 [1]", "광센서 \u2192 조도계",
     "light sensor \u2192 light meter", {"sensor", "meter"}),
]
CABLE_BY_KEY = {c[0]: c for c in CABLES}

SLOT_LABELS = {
    "floor_platform": ("작업대 - 플랫폼", "Bench - platform"),
    "table_psu": ("작업대 - 전원", "Bench - power"),
    "table_tablet": ("작업대 - 태블릿", "Bench - tablet"),
    "table_ctrl": ("작업대 - 컨트롤 박스", "Bench - control box"),
    "table_dmm": ("작업대 - 멀티미터", "Bench - multimeter"),
    "table_meter": ("작업대 - 조도계", "Bench - light meter"),
    "plat_track": ("플랫폼 - 트랙", "Platform - track"),
    "plat_tray": ("플랫폼 - 트레이", "Platform - tray"),
    "plat_vib": ("플랫폼 - 바이브레이터", "Platform - vibrator"),
    "plat_laser": ("플랫폼 - 레이저 2", "Platform - laser 2"),
    "plat_scale": ("플랫폼 - 눈금자", "Platform - scale"),
    "plat_cover": ("플랫폼 - 커버", "Platform - cover"),
    "track_base": ("트랙 - 스크린 베이스", "Track - screen base"),
    "base_sensor": ("베이스 - 광센서", "Base - light sensor"),
    "tray_water": ("트레이 - 물", "Tray - water"),
    "table_tools": ("작업대 - 공구", "Bench - tools"),
}

BENCH_REQUIRED = ["platform", "psu", "tablet", "ctrlbox", "dmm", "meter",
                  "track", "tray", "vib", "laser2", "scale10", "base",
                  "sensor", "cover", "water", "tape", "hexkey", "cyl"]
BENCH_CABLES = ["audio", "vibpin", "dmmwire", "usb", "laser", "sensorw"]


class E2Rig:
    """State of the E-II bench.  Fully usable without a GUI."""

    def __init__(self, phys):
        self.p = phys
        self.rng = random.Random((phys.seed or 0) * 5081 + 7)
        self.installed = set()
        self.cables = set()

        # sources
        self.laser_on = False
        self.laser_high = True
        self.gen_on = False
        self.freq = 100.0                  # Hz
        self.amp = 0.0                     # 0 .. 1 slider
        self.knob = 1.0                    # control-box gain knob 0 .. 1

        # multimeter
        self.dmm_ac = True
        self.dmm_range = "2V"              # 200mV / 2V / 20V

        # light meter
        self.meter_on = False
        self.meter_range = "A"             # A / B / C

        # mechanics
        self.track_x = 10.0                # track scale reading   [cm]
        self.cal_y = 5.0                   # caliper reading       [mm]
        self.vib_mark = 8.0                # vibrator marker       [cm]
        self.cover_down = True
        self.water_ml = 0

    # ------------------------------------------------------------ assembly
    def can_install(self, key):
        if key in self.installed:
            return False, T("이미 설치되어 있습니다.", "Already installed.")
        missing = PREREQ.get(key, set()) - self.installed
        if missing:
            names = ", ".join(T(PART_BY_KEY[k][2], PART_BY_KEY[k][3])
                              for k in sorted(missing))
            return False, T("먼저 설치해야 합니다: ", "Install first: ") + names
        return True, ""

    def install(self, key, slot=None):
        part = PART_BY_KEY.get(key)
        if part is None:
            return False, T("알 수 없는 부품입니다.", "Unknown part.")
        if slot is not None and slot != part[4]:
            return False, T("이 부품의 자리가 아닙니다.",
                            "This is not the seat for that part.")
        ok, msg = self.can_install(key)
        if not ok:
            return False, msg
        self.installed.add(key)
        if key == "water":
            self.water_ml = 500
        return True, T("설치 완료", "Installed")

    def connect(self, key):
        c = CABLE_BY_KEY.get(key)
        if c is None:
            return False, T("알 수 없는 케이블입니다.", "Unknown cable.")
        if key in self.cables:
            return False, T("이미 연결되어 있습니다.", "Already connected.")
        missing = c[4] - self.installed
        if missing:
            names = ", ".join(T(PART_BY_KEY[k][2], PART_BY_KEY[k][3])
                              for k in sorted(missing))
            return False, T("먼저 설치해야 합니다: ", "Install first: ") + names
        self.cables.add(key)
        return True, T("연결 완료", "Connected")

    def bench_ready(self):
        m = [k for k in BENCH_REQUIRED if k not in self.installed]
        m += [k for k in BENCH_CABLES if k not in self.cables]
        return len(m) == 0, m

    # ----------------------------------------------------------- electrical
    def vrms(self):
        """True r.m.s. voltage across the vibrator [V]."""
        if not (self.gen_on and "audio" in self.cables
                and "vibpin" in self.cables and "usb" in self.cables):
            return 0.0
        return 2.0 * self.amp * self.knob

    def dmm_reading(self):
        """String shown by the digital multimeter."""
        if "dmm" not in self.installed:
            return None
        if "dmmwire" not in self.cables:
            return "  0.000"
        v = self.vrms()
        if not self.dmm_ac:
            return "  0.000"          # a pure a.c. signal reads ~0 on d.c.
        v *= self.p.dmm_gain * (1.0 + self.rng.gauss(0.0, 2e-4))
        full = {"200mV": 0.2, "2V": 2.0, "20V": 20.0}[self.dmm_range]
        if v > full:
            return "   O L "
        if self.dmm_range == "200mV":
            return "%7.1f" % (v * 1000.0)      # mV, 0.1 mV resolution
        if self.dmm_range == "2V":
            return "%7.3f" % v                 # 3 1/2 digits: 1 mV resolution
        return "%7.2f" % v

    # ------------------------------------------------------------- geometry
    def l1_m(self):
        """Aperture -> outer edge of the tray [m]."""
        return self.p.c1 + self.track_x * 0.01

    def L_m(self):
        return self.l1_m() + self.p.l2

    def spot_center_mm(self):
        """Caliper reading at which the specular spot is centred [mm]."""
        return (self.p.y_base + math.tan(self.p.theta)
                * self.track_x * 0.01) * 1000.0

    def x1_m(self):
        """Separation of consecutive diffraction orders on the sensor [m]."""
        f = self.freq
        k = self.p.k_of_f(f)
        sg = k * LAM / (2.0 * math.pi * math.sin(self.p.theta))
        return self.L_m() * sg

    def wave_amplitude(self):
        """Wave amplitude at the point of incidence [m]."""
        v = self.vrms()
        if v <= 0 or self.water_ml < 500:
            return 0.0
        s = max(0.0, (self.vib_mark + self.p.x_mark) * 0.01)
        h0 = self.p.A * v ** 0.4
        return h0 * math.exp(-self.p.delta_of_f(self.freq) * s)

    def phase_depth(self):
        return 4.0 * math.pi * self.wave_amplitude() * \
            math.sin(self.p.theta) / LAM

    # ---------------------------------------------------------- light meter
    _ord_cache = {}

    def orders(self):
        """[(order, relative intensity)] of the diffraction pattern."""
        d = self.phase_depth()
        key = round(d, 7)
        hit = E2Rig._ord_cache.get(key)
        if hit is not None:
            return hit
        out = []
        for m in range(-4, 5):
            j = besselJ(abs(m), d)
            out.append((m, j * j))
        if len(E2Rig._ord_cache) > 20000:
            E2Rig._ord_cache.clear()
        E2Rig._ord_cache[key] = out
        return out

    def illuminance(self, y_mm=None):
        """True illuminance at the sensor aperture [lux]."""
        if not self.laser_on or "laser" not in self.cables:
            return 0.0
        if self.water_ml < 500:
            return 0.0
        y = self.cal_y if y_mm is None else y_mm
        g = self.p.gain * (1.0 if self.laser_high else 0.42)
        c = self.spot_center_mm()
        x1 = self.x1_m() * 1000.0
        sig = self.p.spot * 1000.0
        tot = 0.0
        for m, w in self.orders():
            if w < 1e-9:
                continue
            dy = y - (c + m * x1)
            if abs(dy) > 6.0 * sig:
                continue
            tot += w * math.exp(-dy * dy / (2.0 * sig * sig))
        amb = 0.0 if self.cover_down else 2.0
        lux = g * tot + self.p.dark + amb
        return lux * (1.0 + self.rng.gauss(0.0, self.p.lux_noise))

    def meter_reading(self):
        """String shown by the light meter."""
        if "meter" not in self.installed or "sensorw" not in self.cables:
            return None
        if not self.meter_on:
            return "       "
        lux = self.illuminance()
        step = {"A": 1.0, "B": 10.0, "C": 100.0}[self.meter_range]
        top = {"A": 1999.0, "B": 19990.0, "C": 50000.0}[self.meter_range]
        if lux > top:
            return "   1   "
        return "%7d" % (int(lux / step + 0.5) * int(step))

    # ------------------------------------------------------------- the tape
    def tape(self, what):
        """Measuring tape / plastic scale readings, in cm."""
        if "tape" not in self.installed:
            return None, T("줄자가 없습니다.", "No measuring tape.")
        if what == "l1":
            v = self.l1_m() * 100.0
        elif what == "l2":
            v = self.p.l2 * 100.0
        else:
            return None, T("측정할 수 없습니다.", "Cannot be measured.")
        v += self.rng.gauss(0.0, 0.05)
        return round(v, 1), ""


# --------------------------------------------------------------------------
# Top view geometry of the assembly tab
# --------------------------------------------------------------------------

SLOT_BOXES = {
    "table_psu":      (32,  58, 136, 140),
    "table_tablet":  (148,  58, 260, 140),
    "table_ctrl":    (272,  58, 380, 140),
    "table_dmm":     (392,  58, 484, 140),
    "table_meter":   (496,  58, 592, 140),
    "table_tools":    (32, 152, 312, 224),
    "floor_platform": (22, 240, 672, 574),
    "plat_laser":     (38, 466, 122, 546),
    "plat_tray":      (38, 300, 262, 452),
    "plat_vib":       (42, 246, 142, 296),
    "plat_scale":    (152, 246, 262, 296),
    "tray_water":     (54, 330, 246, 436),
    "plat_track":    (290, 300, 664, 384),
    "track_base":    (408, 306, 498, 378),
    "base_sensor":   (420, 326, 486, 372),
    "plat_cover":    (292, 466, 408, 546),
}

C_BG = "#101418"
C_TABLE = "#1b2229"
C_SLOT = "#232c35"
C_SLOT_OK = "#2f4a38"
C_EDGE = "#3d4a57"
C_TXT = "#c9d6e2"
C_ACC = "#e0552b"
CONTAINERS = {"platform", "tray", "track", "base"}


class AssemblyTab(ttk.Frame):
    """Drag the parts from the palette onto their seat on the bench."""

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.rig = app.rig

        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Label(left, text=T("부품 목록", "Parts list"),
                  font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.pal = tk.Canvas(left, width=196, height=430, bg=C_BG,
                             highlightthickness=1, highlightbackground=C_EDGE)
        self.pal.pack(pady=(4, 6))

        ttk.Label(left, text=T("케이블 / 커넥터", "Cables / connectors"),
                  font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.cab = ttk.Frame(left)
        self.cab.pack(fill="x", pady=4)
        self.cab_btn = {}
        for c in CABLES:
            b = ttk.Button(self.cab, text=T(c[2], c[3]) + "  " + c[1],
                           width=34,
                           command=lambda k=c[0]: self.do_cable(k))
            b.pack(anchor="w", pady=1)
            self.cab_btn[c[0]] = b

        self.cv = tk.Canvas(self, bg=C_BG, highlightthickness=0)
        self.cv.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=6)

        self.msg = tk.StringVar(value=T("나무 플랫폼부터 설치하십시오.",
                                        "Start with the wooden platform."))
        ttk.Label(left, textvariable=self.msg, foreground="#e8b04b",
                  wraplength=196, justify="left").pack(anchor="w", pady=(6, 0))

        self.drag = None
        self.pal.bind("<ButtonPress-1>", self.on_press)
        self.pal.bind("<B1-Motion>", self.on_move)
        self.pal.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<B1-Motion>", self.on_move)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.redraw()

    # ------------------------------------------------------------------ ui
    def pal_items(self):
        out, y = [], 8
        for p in PARTS:
            if p[0] in self.rig.installed:
                continue
            out.append((p, 6, y, 190, y + 30))
            y += 34
        return out

    def redraw(self):
        self.pal.delete("all")
        items = self.pal_items()
        if not items:
            self.pal.create_text(98, 30, fill="#5d6b79", width=180,
                                 justify="center",
                                 text=T("모든 부품을 설치했습니다.",
                                        "All parts installed."))
        for p, x1, y1, x2, y2 in items:
            self.pal.create_rectangle(x1, y1, x2, y2, fill=C_SLOT,
                                      outline=C_EDGE, tags=("it", p[0]))
            self.pal.create_text(x1 + 8, (y1 + y2) / 2, anchor="w",
                                 fill=C_ACC, text="[%s]" % p[1],
                                 font=("TkDefaultFont", 8), tags=("it", p[0]))
            self.pal.create_text(x1 + 44, (y1 + y2) / 2, anchor="w",
                                 fill=C_TXT, text=T(p[2], p[3]),
                                 font=("TkDefaultFont", 8), tags=("it", p[0]))
        self.draw_scene()
        for c in CABLES:
            done = c[0] in self.rig.cables
            self.cab_btn[c[0]].configure(
                text=("\u2713 " if done else "") + T(c[2], c[3]) + "  " + c[1],
                state="disabled" if done else "normal")
        self.app.refresh_bench()

    def draw_scene(self):
        cv = self.cv
        cv.delete("all")
        cv.create_rectangle(20, 44, 682, 232, fill=C_TABLE, outline=C_EDGE)
        cv.create_text(24, 38, anchor="w", fill="#7f8c9b",
                       text=T("실험 테이블", "Instrument table"),
                       font=("TkDefaultFont", 8))
        ins = self.rig.installed
        for slot, (x1, y1, x2, y2) in SLOT_BOXES.items():
            occ = [p for p in PARTS if p[4] == slot and p[0] in ins]
            if slot == "floor_platform":
                col = "#3a2f22" if occ else C_SLOT
                cv.create_rectangle(x1, y1, x2, y2, fill=col,
                                    outline="#6b5335" if occ else C_EDGE,
                                    width=2)
                continue
            if slot in ("tray_water", "base_sensor") and not occ:
                cv.create_rectangle(x1, y1, x2, y2, outline="#33404c",
                                    dash=(2, 3))
                continue
            cv.create_rectangle(x1, y1, x2, y2,
                                fill=C_SLOT_OK if occ else C_SLOT,
                                outline="#4f7f5f" if occ else C_EDGE)
            if not occ:
                cv.create_text((x1 + x2) / 2, (y1 + y2) / 2, fill="#5d6b79",
                               width=x2 - x1 - 6, justify="center",
                               text=T(*SLOT_LABELS[slot]),
                               font=("TkDefaultFont", 7))
        self.draw_parts()

    def draw_parts(self):
        cv = self.cv
        ins = self.rig.installed
        for p in PARTS:
            if p[0] not in ins:
                continue
            x1, y1, x2, y2 = SLOT_BOXES[p[4]]
            if p[4] == "table_tools":
                idx = [q[0] for q in PARTS if q[4] == "table_tools"
                       and q[0] in ins].index(p[0])
                y1 = y1 + 4 + idx * 22
                y2 = y1 + 20
                x2 = x1 + 268
            if p[0] in CONTAINERS:
                cv.create_rectangle(x1 + 3, y1 + 3, x2 - 3, y2 - 3,
                                    outline="#6f8ea3", width=2,
                                    tags=("part", p[0]))
                ly = y2 - 11 if p[0] == "platform" else y1 + 11
                cv.create_text(x1 + 8, ly, anchor="w", fill="#a8c2d6",
                               text="[%s] %s" % (p[1], T(p[2], p[3])),
                               font=("TkDefaultFont", 7),
                               tags=("part", p[0]))
            else:
                cv.create_rectangle(x1 + 3, y1 + 3, x2 - 3, y2 - 3,
                                    fill="#31424f", outline="#6f8ea3",
                                    tags=("part", p[0]))
                cv.create_text((x1 + x2) / 2, (y1 + y2) / 2, fill="#dcecf7",
                               width=x2 - x1 - 10, justify="center",
                               text="[%s] %s" % (p[1], T(p[2], p[3])),
                               font=("TkDefaultFont", 7),
                               tags=("part", p[0]))
        # beam sketch, only once everything optical is present
        if {"laser2", "tray", "water", "track", "base", "sensor"} <= ins:
            lx = (SLOT_BOXES["plat_laser"][0] + SLOT_BOXES["plat_laser"][2]) / 2
            wx1, wy1, wx2, wy2 = SLOT_BOXES["tray_water"]
            sx = (SLOT_BOXES["base_sensor"][0]
                  + SLOT_BOXES["base_sensor"][2]) / 2
            sy = SLOT_BOXES["base_sensor"][3] - 8
            cv.create_line(lx, SLOT_BOXES["plat_laser"][1],
                           (wx1 + wx2) / 2, wy2 - 6, fill="#ff5a4a", width=2)
            cv.create_line((wx1 + wx2) / 2, wy2 - 6, sx, sy, fill="#ff5a4a",
                           width=2, arrow="last", dash=(7, 4))
        cv.tag_bind("part", "<Button-3>", self.on_remove)

    # -------------------------------------------------------------- events
    def on_press(self, e):
        it = self.pal.find_withtag("current")
        if not it:
            return
        tags = self.pal.gettags(it[0])
        key = [t for t in tags if t in PART_BY_KEY]
        if not key:
            return
        self.drag = key[0]
        p = PART_BY_KEY[self.drag]
        self.ghost = tk.Toplevel(self)
        self.ghost.overrideredirect(True)
        self.ghost.attributes("-topmost", True)
        tk.Label(self.ghost, text=T(p[2], p[3]), bg="#e0552b", fg="white",
                 font=("TkDefaultFont", 8), padx=6, pady=2).pack()
        self.on_move(e)

    def on_move(self, e):
        if not self.drag:
            return
        self.ghost.geometry("+%d+%d" % (e.widget.winfo_rootx() + e.x + 12,
                                        e.widget.winfo_rooty() + e.y + 12))

    def on_release(self, e):
        if not self.drag:
            return
        key = self.drag
        self.drag = None
        self.ghost.destroy()
        if e.widget is not self.cv:
            x = e.widget.winfo_rootx() + e.x - self.cv.winfo_rootx()
            y = e.widget.winfo_rooty() + e.y - self.cv.winfo_rooty()
        else:
            x, y = e.x, e.y
        slot = None
        best = None
        for s, (x1, y1, x2, y2) in SLOT_BOXES.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                a = (x2 - x1) * (y2 - y1)
                if best is None or a < best:
                    best, slot = a, s
        if slot is None:
            self.msg.set(T("작업 영역 위에 놓으십시오.",
                           "Drop the part on the workspace."))
            return
        ok, m = self.rig.install(key, slot)
        self.msg.set(m if ok else "\u26a0 " + m)
        self.redraw()

    def on_remove(self, e):
        it = self.cv.find_withtag("current")
        if not it:
            return
        tags = self.cv.gettags(it[0])
        key = [t for t in tags if t in PART_BY_KEY]
        if not key:
            return
        k = key[0]
        dep = [q for q, req in PREREQ.items()
               if k in req and q in self.rig.installed]
        if dep:
            self.msg.set("\u26a0 " + T("먼저 분리해야 합니다: ",
                                       "Remove first: ")
                         + ", ".join(T(PART_BY_KEY[d][2], PART_BY_KEY[d][3])
                                     for d in dep))
            return
        for c in CABLES:
            if k in c[4] and c[0] in self.rig.cables:
                self.rig.cables.discard(c[0])
        self.rig.installed.discard(k)
        if k == "water":
            self.rig.water_ml = 0
        self.msg.set(T("분리했습니다.", "Removed."))
        self.redraw()

    def do_cable(self, key):
        ok, m = self.rig.connect(key)
        self.msg.set(m if ok else "\u26a0 " + m)
        self.redraw()


LCD_BG = "#0d1a12"
LCD_FG = "#7dfcb0"


def lcd(master, width=9):
    e = tk.Label(master, text="", bg=LCD_BG, fg=LCD_FG, width=width,
                 font=("Courier", 15, "bold"), anchor="e", padx=6, pady=3,
                 relief="sunken", bd=2)
    return e


class BenchTab(ttk.Frame):
    """The working bench: sources, instruments and the sensor plane."""

    VIEW_MM = 9.0          # half height of the sensor-plane view [mm]

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.rig = app.rig

        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)

        col = ttk.Frame(outer)
        col.pack(side="left", fill="y", padx=6, pady=6)

        # ---------------- laser + generator
        f1 = ttk.LabelFrame(col, text=T("광원 / 신호원",
                                        "Light source / generator"))
        f1.pack(fill="x", pady=3)
        self.v_laser = tk.BooleanVar(value=False)
        ttk.Checkbutton(f1, text=T("레이저 2 ON [15]", "Laser 2 ON [15]"),
                        variable=self.v_laser,
                        command=self.apply).grid(row=0, column=0, columnspan=2,
                                                 sticky="w", padx=4)
        self.v_hi = tk.StringVar(value="high")
        ttk.Radiobutton(f1, text=T("고출력", "high"), value="high",
                        variable=self.v_hi, command=self.apply
                        ).grid(row=1, column=0, sticky="w", padx=12)
        ttk.Radiobutton(f1, text=T("저출력", "low"), value="low",
                        variable=self.v_hi, command=self.apply
                        ).grid(row=1, column=1, sticky="w")
        self.v_gen = tk.BooleanVar(value=False)
        ttk.Checkbutton(f1, text=T("사인파 출력 ON [3]",
                                   "sine output ON [3]"),
                        variable=self.v_gen,
                        command=self.apply).grid(row=2, column=0, columnspan=2,
                                                 sticky="w", padx=4, pady=(6, 0))
        ttk.Label(f1, text=T("주파수 [Hz]", "frequency [Hz]")
                  ).grid(row=3, column=0, sticky="w", padx=12)
        self.e_freq = ttk.Entry(f1, width=8)
        self.e_freq.insert(0, "100")
        self.e_freq.grid(row=3, column=1, sticky="w")
        self.e_freq.bind("<Return>", lambda e: self.apply())
        ttk.Label(f1, text=T("진폭 슬라이더", "amplitude slider")
                  ).grid(row=4, column=0, columnspan=2, sticky="w", padx=12)
        self.v_amp = tk.DoubleVar(value=0.0)
        ttk.Scale(f1, from_=0.0, to=1.0, variable=self.v_amp, length=200,
                  command=lambda e: self.apply()
                  ).grid(row=5, column=0, columnspan=2, padx=12)
        ttk.Label(f1, text=T("컨트롤 박스 노브 [5]", "control-box knob [5]")
                  ).grid(row=6, column=0, columnspan=2, sticky="w", padx=12)
        self.v_knob = tk.DoubleVar(value=1.0)
        ttk.Scale(f1, from_=0.05, to=1.0, variable=self.v_knob, length=200,
                  command=lambda e: self.apply()
                  ).grid(row=7, column=0, columnspan=2, padx=12, pady=(0, 4))

        # ---------------- multimeter
        f2 = ttk.LabelFrame(col, text=T("디지털 멀티미터 [4]",
                                        "Digital multimeter [4]"))
        f2.pack(fill="x", pady=3)
        self.d_dmm = lcd(f2)
        self.d_dmm.grid(row=0, column=0, rowspan=3, padx=6, pady=4)
        self.v_ac = tk.StringVar(value="AC")
        ttk.Radiobutton(f2, text="AC V", value="AC", variable=self.v_ac,
                        command=self.apply).grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(f2, text="DC V", value="DC", variable=self.v_ac,
                        command=self.apply).grid(row=1, column=1, sticky="w")
        self.v_rng = tk.StringVar(value="2V")
        rb = ttk.Frame(f2)
        rb.grid(row=2, column=1, sticky="w")
        for r in ("200mV", "2V", "20V"):
            ttk.Radiobutton(rb, text=r, value=r, variable=self.v_rng,
                            command=self.apply).pack(side="left")

        # ---------------- light meter
        f3 = ttk.LabelFrame(col, text=T("조도계 [1]", "Light meter [1]"))
        f3.pack(fill="x", pady=3)
        self.d_lux = lcd(f3)
        self.d_lux.grid(row=0, column=0, rowspan=2, padx=6, pady=4)
        self.v_meter = tk.BooleanVar(value=False)
        ttk.Checkbutton(f3, text="ON", variable=self.v_meter,
                        command=self.apply).grid(row=0, column=1, sticky="w")
        self.v_mrng = tk.StringVar(value="A")
        mb = ttk.Frame(f3)
        mb.grid(row=1, column=1, sticky="w")
        for r, lab in (("A", "A x1"), ("B", "B x10"), ("C", "C x100")):
            ttk.Radiobutton(mb, text=lab, value=r, variable=self.v_mrng,
                            command=self.apply).pack(side="left")

        # ---------------- mechanics
        f4 = ttk.LabelFrame(col, text=T("기구부", "Mechanics"))
        f4.pack(fill="x", pady=3)
        ttk.Label(f4, text=T("트랙 위치 [7]  (cm)", "track position [7]  (cm)")
                  ).grid(row=0, column=0, sticky="w", padx=4)
        self.e_track = ttk.Entry(f4, width=8)
        self.e_track.insert(0, "10.0")
        self.e_track.grid(row=0, column=1)
        self.e_track.bind("<Return>", lambda e: self.apply())
        ttk.Label(f4, text=T("바이브레이터 눈금 [10] (cm)",
                             "vibrator marker [10] (cm)")
                  ).grid(row=1, column=0, sticky="w", padx=4)
        self.e_vib = ttk.Entry(f4, width=8)
        self.e_vib.insert(0, "8.0")
        self.e_vib.grid(row=1, column=1)
        self.e_vib.bind("<Return>", lambda e: self.apply())
        ttk.Label(f4, text=T("캘리퍼 [2] (mm)", "caliper [2] (mm)")
                  ).grid(row=2, column=0, sticky="w", padx=4)
        self.d_cal = lcd(f4, width=8)
        self.d_cal.grid(row=2, column=1, padx=4, pady=3)
        bb = ttk.Frame(f4)
        bb.grid(row=3, column=0, columnspan=2, pady=2)
        for lab, dv in (("\u25c0\u25c0", -1.0), ("\u25c0", -0.1),
                        ("\u25c0", -0.01), ("\u25b6", 0.01),
                        ("\u25b6", 0.1), ("\u25b6\u25b6", 1.0)):
            ttk.Button(bb, text=lab, width=3,
                       command=lambda d=dv: self.nudge(d)).pack(side="left")
        self.e_cal = ttk.Entry(f4, width=8)
        self.e_cal.insert(0, "5.00")
        self.e_cal.grid(row=4, column=1, pady=(0, 4))
        self.e_cal.bind("<Return>", lambda e: self.apply())
        ttk.Label(f4, text=T("캘리퍼 값 입력", "set caliper")
                  ).grid(row=4, column=0, sticky="w", padx=4)
        self.v_cov = tk.BooleanVar(value=True)
        ttk.Checkbutton(f4, text=T("플라스틱 커버 덮음 [13]",
                                   "plastic cover in place [13]"),
                        variable=self.v_cov, command=self.apply
                        ).grid(row=5, column=0, columnspan=2, sticky="w",
                               padx=4, pady=(0, 4))

        # ---------------- tape
        f5 = ttk.LabelFrame(col, text=T("줄자 [9]", "Measuring tape [9]"))
        f5.pack(fill="x", pady=3)
        ttk.Button(f5, text=T("l\u2081 측정 (조리개 \u2192 트레이 끝)",
                              "measure l\u2081 (aperture \u2192 tray edge)"),
                   command=lambda: self.do_tape("l1")).pack(fill="x", padx=4,
                                                            pady=2)
        ttk.Button(f5, text=T("l\u2082 측정 (트레이 끝 \u2192 입사점)",
                              "measure l\u2082 (tray edge \u2192 incidence)"),
                   command=lambda: self.do_tape("l2")).pack(fill="x", padx=4,
                                                            pady=(0, 2))
        self.lbl_tape = ttk.Label(f5, text="--- cm",
                                  font=("Courier", 11, "bold"))
        self.lbl_tape.pack(anchor="e", padx=6, pady=(0, 4))

        # ---------------- right column : view + log
        right = ttk.Frame(outer)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.status = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.status,
                  foreground="#e8b04b").pack(anchor="w")
        self.cv = tk.Canvas(right, bg="#07090c", highlightthickness=1,
                            highlightbackground=C_EDGE, height=470)
        self.cv.pack(fill="both", expand=True, pady=4)

        lg = ttk.Frame(right)
        lg.pack(fill="x")
        ttk.Button(lg, text=T("현재 값 기록", "record current readings"),
                   command=self.log_now).pack(side="left")
        ttk.Button(lg, text=T("기록 지우기", "clear log"),
                   command=lambda: self.txt.delete("1.0", "end")
                   ).pack(side="left", padx=4)
        self.txt = tk.Text(right, height=8, bg="#0d1116", fg="#b9c8d6",
                           font=("Courier", 9))
        self.txt.pack(fill="x", pady=4)

        self.refresh()

    # ------------------------------------------------------------ helpers
    def nudge(self, d):
        self.rig.cal_y = max(0.0, min(60.0, self.rig.cal_y + d))
        self.e_cal.delete(0, "end")
        self.e_cal.insert(0, "%.2f" % self.rig.cal_y)
        self.refresh()

    def _f(self, entry, lo, hi, cur):
        try:
            v = float(entry.get())
        except ValueError:
            return cur
        return max(lo, min(hi, v))

    def apply(self):
        r = self.rig
        r.laser_on = self.v_laser.get()
        r.laser_high = (self.v_hi.get() == "high")
        r.gen_on = self.v_gen.get()
        r.freq = self._f(self.e_freq, 20.0, 400.0, r.freq)
        r.amp = self.v_amp.get()
        r.knob = self.v_knob.get()
        r.dmm_ac = (self.v_ac.get() == "AC")
        r.dmm_range = self.v_rng.get()
        r.meter_on = self.v_meter.get()
        r.meter_range = self.v_mrng.get()
        r.track_x = self._f(self.e_track, 0.0, 60.0, r.track_x)
        r.vib_mark = self._f(self.e_vib, 0.0, 30.0, r.vib_mark)
        r.cal_y = self._f(self.e_cal, 0.0, 60.0, r.cal_y)
        r.cover_down = self.v_cov.get()
        self.refresh()

    def do_tape(self, what):
        v, m = self.rig.tape(what)
        if v is None:
            self.status.set("\u26a0 " + m)
            return
        self.lbl_tape.configure(text="%s = %.1f cm" % (what, v))

    def log_now(self):
        r = self.rig
        self.txt.insert("end",
                        "f=%6.1f Hz  s=%5.2f cm  X=%5.2f cm  y=%6.2f mm"
                        "   V=%s   E=%s\n"
                        % (r.freq, r.vib_mark, r.track_x, r.cal_y,
                           (r.dmm_reading() or "----").strip(),
                           (r.meter_reading() or "----").strip()))
        self.txt.see("end")

    # ------------------------------------------------------------ display
    def refresh(self):
        r = self.rig
        ok, missing = r.bench_ready()
        d = r.dmm_reading()
        self.d_dmm.configure(text="-------" if d is None else d)
        m = r.meter_reading()
        self.d_lux.configure(text="-------" if m is None else m)
        self.d_cal.configure(
            text="  --.--" if "sensor" not in r.installed
            else "%7.2f" % (round(r.cal_y / 0.01) * 0.01))
        if not ok:
            self.status.set(T("조립이 끝나지 않았습니다: ",
                              "Assembly incomplete: ")
                            + ", ".join(
                                T(PART_BY_KEY[k][2], PART_BY_KEY[k][3])
                                if k in PART_BY_KEY
                                else CABLE_BY_KEY[k][1] for k in missing[:4])
                            + (" ..." if len(missing) > 4 else ""))
        else:
            self.status.set("")
        self.draw_view()

    def draw_view(self):
        cv = self.cv
        cv.delete("all")
        w = max(cv.winfo_width(), 480)
        h = max(cv.winfo_height(), 440)
        r = self.rig

        # ---- upper part : side view of tray, laser and track
        cv.create_text(10, 8, anchor="nw", fill="#7f8c9b",
                       text=T("측면도", "Side view"),
                       font=("TkDefaultFont", 8))
        y0 = 96
        cv.create_line(30, y0, w - 30, y0, fill="#31404d")
        if "water" in r.installed and r.water_ml >= 500:
            cv.create_rectangle(40, y0 - 12, 200, y0, fill="#123245",
                                outline="#2a6a8c")
            if r.vrms() > 0:
                for i in range(0, 160, 6):
                    a = 4.0 * math.exp(-0.012 * i)
                    cv.create_line(40 + i, y0 - 12 - a, 46 + i, y0 - 12 + a,
                                   fill="#4fb6e0")
        cv.create_rectangle(40, y0, 200, y0 + 16, fill="#22303a",
                            outline="#43596b")
        cv.create_text(120, y0 + 8, fill="#8fa2b3", text=T("트레이 [12]",
                                                           "tray [12]"),
                       font=("TkDefaultFont", 7))
        if "vib" in r.installed:
            xv = 40 + min(158, r.vib_mark * 5.2)
            cv.create_line(xv, y0 - 40, xv, y0 - 12, fill="#c9d6e2", width=3)
            cv.create_text(xv, y0 - 46, fill="#8fa2b3",
                           text=T("바이브레이터", "vibrator"),
                           font=("TkDefaultFont", 7))
        if "laser2" in r.installed and r.laser_on and "laser" in r.cables:
            cv.create_line(24, y0 - 34, 120, y0 - 12, fill="#ff5a4a", width=2)
            cv.create_line(120, y0 - 12, w - 60, y0 - 44, fill="#ff5a4a",
                           width=2, dash=(6, 3))
        if "sensor" in r.installed:
            xs = w - 58
            cv.create_rectangle(xs, y0 - 60, xs + 22, y0 + 6, fill="#22303a",
                                outline="#43596b")
            cv.create_text(xs + 11, y0 + 18, fill="#8fa2b3",
                           text=T("광센서", "sensor"),
                           font=("TkDefaultFont", 7))

        # ---- lower part : the sensor plane, as seen from the beam
        top = 150
        bot = h - 14
        cv.create_text(10, top - 18, anchor="nw", fill="#7f8c9b",
                       text=T("센서면 (조리개 주변에서 보이는 모습)",
                              "Sensor plane (view around the aperture)"),
                       font=("TkDefaultFont", 8))
        cx = w / 2
        cv.create_rectangle(cx - 130, top, cx + 130, bot, fill="#0b0e12",
                            outline="#2b3642")
        ok, _ = r.bench_ready()
        if not (r.laser_on and "laser" in r.cables and r.water_ml >= 500):
            cv.create_text(cx, (top + bot) / 2, fill="#43505d",
                           text=T("(어두움)", "(dark)"))
            return
        span = 2.0 * self.VIEW_MM
        pxmm = (bot - top) / span
        y_lo = r.cal_y - self.VIEW_MM
        c = r.spot_center_mm()
        x1 = r.x1_m() * 1000.0
        sig = max(0.12, self.rig.p.spot * 1000.0)
        for m, wgt in r.orders():
            if wgt < 2e-4:
                continue
            ym = c + m * x1
            if not (y_lo <= ym <= y_lo + span):
                continue
            py = bot - (ym - y_lo) * pxmm
            for lev in range(6, 0, -1):
                a = lev / 6.0
                rr = sig * pxmm * a * 3.0
                inten = wgt * math.exp(-4.2 * a * a)
                inten *= (1.0 if r.laser_high else 0.42)
                t = min(1.0, (inten * 3.0) ** 0.45)
                if t < 0.03:
                    continue
                col = "#%02x%02x%02x" % (int(48 + 207 * t),
                                         int(12 + 150 * t ** 3.2),
                                         int(10 + 130 * t ** 3.6))
                cv.create_oval(cx - rr, py - rr, cx + rr, py + rr,
                               fill=col, outline="")
        # the aperture of the light sensor
        py = bot - (r.cal_y - y_lo) * pxmm
        cv.create_oval(cx - 11, py - 11, cx + 11, py + 11,
                       outline="#9fb3c4", width=2)
        cv.create_line(cx + 11, py, cx + 40, py, fill="#9fb3c4")
        cv.create_text(cx + 44, py, anchor="w", fill="#7f8c9b",
                       text=T("조리개", "aperture"),
                       font=("TkDefaultFont", 7))


# --------------------------------------------------------------------------
# Application
# --------------------------------------------------------------------------

HELP_KO = u"""IPhO 2015  실험문제 E-II
물 표면의 표면장력파에 의한 회절

[조립 탭]
 부품 목록에서 부품을 끌어다 알맞은 자리에 놓으십시오.
 순서가 맞아야 설치됩니다 (플랫폼 -> 트랙/트레이/바이브레이터/레이저 ->
 스크린 베이스 -> 광센서, 물은 메스실린더로 500 ml 만 넣습니다).
 케이블 6 개를 모두 연결해야 실험대가 동작합니다.

[실험대 탭]
 - 레이저 2 를 켜고 물 표면에서 스치듯 반사시킵니다.
 - 태블릿에서 사인파를 내보내면 바이브레이터가 물 표면에 파동을 만듭니다.
 - 멀티미터는 바이브레이터 양단 전압을, 조도계는 조리개를 통과한 빛의
   조도를 읽습니다.  캘리퍼를 돌려 광센서를 세로로 움직이면서 회절 반점의
   위치를 조도 최댓값으로 찾습니다.
 - 줄자로 l1, l2 를 재고, 트랙 눈금으로 X 를, 바이브레이터 눈금으로
   입사점까지의 거리 s 를 읽습니다.

이 시뮬레이터는 실제 계기가 보여주는 값만 표시합니다.
파장, 파수, 표면장력, 점성계수는 스스로 구해야 합니다.
숨은 참값은 세션마다 다시 무작위로 정해집니다."""

HELP_EN = u"""IPhO 2015  Experimental problem E-II
Diffraction due to surface tension waves on water

[Assembly tab]
 Drag the parts from the list onto their seats.  The order is enforced
 (platform -> track / tray / vibrator / laser -> screen base -> light
 sensor; the water is poured with the 500 ml measuring cylinder).
 All six cables must be connected before the bench will work.

[Bench tab]
 - Switch laser 2 on; it grazes the water surface and is reflected.
 - The tablet drives the vibrator, which excites surface waves.
 - The multimeter reads the voltage across the vibrator, the light meter
   reads the illuminance through the aperture.  Turn the caliper to move
   the sensor vertically and locate the diffraction spots by maximising
   the illuminance.
 - Measure l1 and l2 with the tape, X on the track scale and the distance
   s of the point of incidence on the vibrator scale.

Only the readings of the real instruments are displayed.  Wavelength,
wave number, surface tension and viscosity have to be worked out by you.
The hidden true values are re-randomised for every session."""


class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.seed = seed
        self.title("HaslaLab  |  IPhO 2015 E-II  " +
                   T("표면장력파에 의한 회절",
                     "Diffraction by surface tension waves"))
        self.geometry("1330x790")
        self.configure(bg=C_BG)
        try:
            ttk.Style(self).theme_use("clam")
        except tk.TclError:
            pass
        self._build_menu()
        self._new_rig()
        self._build()

    def _new_rig(self):
        self.phys = E2Physics(self.seed)
        self.rig = E2Rig(self.phys)

    def _build_menu(self):
        m = tk.Menu(self)
        fm = tk.Menu(m, tearoff=0)
        fm.add_command(label=T("새 세션", "New session"),
                       command=self.new_session)
        fm.add_separator()
        fm.add_command(label=T("종료", "Quit"), command=self.destroy)
        m.add_cascade(label=T("파일", "File"), menu=fm)
        lm = tk.Menu(m, tearoff=0)
        lm.add_command(label="한국어", command=lambda: self.set_lang("ko"))
        lm.add_command(label="English", command=lambda: self.set_lang("en"))
        m.add_cascade(label=T("언어", "Language"), menu=lm)
        hm = tk.Menu(m, tearoff=0)
        hm.add_command(label=T("사용법", "How to use"), command=self.help)
        m.add_cascade(label=T("도움말", "Help"), menu=hm)
        self.config(menu=m)

    def _build(self):
        self.tab_b = None
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.tab_a = AssemblyTab(self.nb, self)
        self.tab_b = BenchTab(self.nb, self)
        self.nb.add(self.tab_a, text=T("1. 장치 조립", "1. Assembly"))
        self.nb.add(self.tab_b, text=T("2. 실험대", "2. Bench"))

    def refresh_bench(self):
        if getattr(self, "tab_b", None) is not None:
            self.tab_b.refresh()

    def help(self):
        messagebox.showinfo(T("사용법", "How to use"),
                            HELP_KO if LANG == "ko" else HELP_EN)

    def set_lang(self, lang):
        global LANG
        if lang == LANG:
            return
        LANG = lang
        ins, cab = set(self.rig.installed), set(self.rig.cables)
        state = dict(laser_on=self.rig.laser_on, gen_on=self.rig.gen_on,
                     freq=self.rig.freq, amp=self.rig.amp, knob=self.rig.knob,
                     track_x=self.rig.track_x, cal_y=self.rig.cal_y,
                     vib_mark=self.rig.vib_mark, water_ml=self.rig.water_ml,
                     meter_on=self.rig.meter_on)
        self.nb.destroy()
        self._build_menu()
        self.title("HaslaLab  |  IPhO 2015 E-II  " +
                   T("표면장력파에 의한 회절",
                     "Diffraction by surface tension waves"))
        self._build()
        self.rig.installed, self.rig.cables = ins, cab
        for k, v in state.items():
            setattr(self.rig, k, v)
        self.tab_a.redraw()
        self.tab_b.refresh()

    def new_session(self):
        self._new_rig()
        self.nb.destroy()
        self._build()


def main():
    global LANG
    import sys
    seed = None
    for a in sys.argv[1:]:
        if a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])
        elif a.startswith("--lang="):
            LANG = a.split("=", 1)[1]
    App(seed).mainloop()


if __name__ == "__main__":
    main()
