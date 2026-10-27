#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  4th Gulf Physics Olympiad  (GPhO 2022, Dammam, Saudi Arabia)
  Experimental Problem E1 :  CYLINDER IN CYLINDER
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The apparatus of the problem sheet: a transparent cylinder (outer
    part n_o, a central core n_c as wide as the magnet) with a disc
    magnet in its middle and foil caps; a digital caliper, a 30 cm
    ruler, graph paper, a marker, two safety pins on cardboard, a cup
    of water, doubled rubber threads with tape, a magnetoresistive
    sensor fed by a battery holder and a multimeter.
    Only what the student would see is shown: the caliper's display
    where you put its jaws, the cylinder seen through its own
    refraction, the ruler's marks, the meter's digits.  No volume,
    density, refractive index or dipole moment is computed for you.
    The hidden values are randomised each session; --seed N repeats it.

    Run:   python3 gpho2022_E1_cylinder_sim_EN.py   [--seed N]
"""
import math
import random
import time
import sys
import tkinter as tk

APP_VERSION = "1.0"
LANG = "EN"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "KO" else en


SEED = None
for i, a in enumerate(sys.argv):
    if a == "--seed" and i + 1 < len(sys.argv):
        SEED = int(sys.argv[i + 1])
RNG = random.Random(SEED)


def gauss():
    return RNG.gauss(0.0, 1.0)


# ==============================================================================
#  1.  참값 (학생에게 보이지 않음) — 공식 해설에 맞춤 (mm)
# ==============================================================================
R = 12.6 * (1 + 0.004 * gauss())
HC = 30.45 + 0.08 * gauss()
RM = 6.0 * (1 + 0.012 * gauss())
HM = 9.5 + 0.12 * gauss()
NO = 1.54 + 0.008 * gauss()
NC = NO + 0.062 + 0.006 * gauss()
ZM = HC / 2 + 0.25 * gauss()
RHO_G = 1280 * (1 + 0.025 * gauss())
VM = math.pi * RM ** 2 * HM * 1e-9
VOL = math.pi * R ** 2 * HC * 1e-9
MASS = 7500 * VM + RHO_G * (VOL - VM)
RHO_W, G, MU0 = 1000.0, 9.81, 4e-7 * math.pi
L0_TH, K_TH = 135 * (1 + 0.02 * gauss()), 0.461 * (1 + 0.05 * gauss())
J_MAG = 1.30e6 * (1 + 0.04 * gauss())
E_BAT = 3.15 + 0.035 * gauss()
V0 = [-0.8 + 0.5 * gauss()]
BE = (23e-6 * (1 + 0.15 * gauss()), -25e-6 * (1 + 0.1 * gauss()))
D_, d_ = 2 * R, 2 * RM
L_STAR = D_ + 1 / (NO / (NC * d_ / (NC - NO) - D_) + (NO - 1) / D_)
F_CYL = L_STAR / 4
BG_DIST = 100.0
DESK_HALF, CYL_X = 380.0, -150.0
DIAL = ["OFF", "DCV 200m", "DCV 2", "DCV 20", "DCV 200", "DCA 200m", "DCA 10", "Ω 200", "Ω 2k", "Ω 20k"]


def RW(th):
    return R * (1 + 0.0035 * math.sin(2 * th + 0.7) + 0.0015 * math.sin(3 * th + 2.1))


def HW(th):
    return HC + 0.05 * math.sin(th + 1.3)


def tau(lam):
    return (1 - 1 / lam) * (1 - 0.2664 * lam + 0.1191 * lam * lam)


def _ref(d, n, n1, n2):
    c = -(d[0] * n[0] + d[1] * n[1])
    k = n1 / n2
    s = 1 - k * k * (1 - c * c)
    if s < 0:
        return None
    t = k * c - math.sqrt(s)
    return (k * d[0] + t * n[0], k * d[1] + t * n[1])


def _hit(p, d, rad):
    b = p[0] * d[0] + p[1] * d[1]
    cc = p[0] ** 2 + p[1] ** 2 - rad * rad
    disc = b * b - cc
    if disc < 0:
        return None
    return (-b - math.sqrt(disc), -b + math.sqrt(disc))


def trace_ray(y, mag_row):
    """a ray parallel to the view at offset y (mm): (blocked by magnet?, offset on the paper, angle where it leaves)"""
    if abs(y) >= R:
        return False, y, None
    p = (-math.sqrt(R * R - y * y), y)
    d = _ref((1.0, 0.0), (p[0] / R, p[1] / R), 1, NO)
    if d is None:
        return True, 0, None
    hc = _hit(p, d, RM)
    if hc and hc[0] > 1e-9:
        if mag_row:
            return True, 0, None
        p = (p[0] + d[0] * hc[0], p[1] + d[1] * hc[0])
        d = _ref(d, (p[0] / RM, p[1] / RM), NO, NC)
        h2 = _hit(p, d, RM)
        p = (p[0] + d[0] * h2[1], p[1] + d[1] * h2[1])
        d = _ref(d, (-p[0] / RM, -p[1] / RM), NC, NO)
        if d is None:
            return True, 0, None
    ho = _hit(p, d, R)
    p = (p[0] + d[0] * ho[1], p[1] + d[1] * ho[1])
    th = math.atan2(p[1], p[0])
    d = _ref(d, (-p[0] / R, -p[1] / R), NO, 1)
    if d is None:
        return True, 0, th
    return False, p[1] + d[1] / d[0] * (R + BG_DIST - p[0]), th


def mag_field(px, py):
    r = math.hypot(px, py)
    if r < R:
        return 0.0, 0.0
    a, hh, m0J = RM * 1e-3, HM * 1e-3 / 2, MU0 * J_MAG

    def on_axis(z):
        z1, z2 = z - hh, z + hh
        return m0J / 2 * (z2 / math.hypot(z2, a) - z1 / math.hypot(z1, a))
    c, s = px / r, py / r
    Ba = on_axis(r * 1e-3)
    Br, Bt = Ba * c, Ba * s / 2
    return Br * c - Bt * s, Br * s + Bt * c


class State(object):
    def __init__(self):
        self.rot = 0.0
        self.dots = []                       # (phi, z)
        self.cal = {"x": -30.0, "y": 5.0, "open": 40.0, "dir": "h", "mode": "around"}
        self.calT = {"x": -30.0, "y": -16.0, "open": 60.0, "dir": "h", "mode": "around"}
        self.pa, self.pb, self.eye = -45.0, 45.0, 0.0
        self.rulP = [-82.0, -28.0]
        self.hand, self.l, self.v, self.hang, self.cup = 420.0, L0_TH, 0.0, True, False
        self.rulT = [40.0, 0.0]
        self.sx, self.sy, self.sdir, self.near = 150.0, 0.0, 0, False
        self.rulS = [-134.0, -22.0]
        self.meter = None
        self.dial = 0
        self.marker = False


S = State()
CUP_W, CUP_H, CUP_LEVEL = 80.0, 95.0, 72.0
SDIR = [(1, 0), (0, 1), (-1, 0), (0, -1)]


def seat(cal, k, lo, hi):
    a = -lo
    if k == "y":
        if 0 < cal["y"] < hi:
            cal["y"] = 0.0
        if cal["y"] <= 0 and cal["y"] + cal["open"] < hi:
            cal["y"] = min(0.0, hi - cal["open"])
            cal["open"] = max(cal["open"], hi - cal["y"])
        return
    if a < cal["x"] < hi:
        cal["x"] = a
    if cal["x"] <= a and cal["x"] + cal["open"] < hi:
        cal["x"] = min(a, hi - cal["open"])
        cal["open"] = max(cal["open"], hi - cal["x"])


def cal_contact(cal, view):
    if cal["mode"] != "around":
        return
    if view == "look" and cal["dir"] == "h":
        if cal["y"] > 0 and cal["y"] - 22 < HC:
            seat(cal, "x", RW(S.rot - math.pi / 2), RW(S.rot + math.pi / 2))
    elif view == "look":
        if cal["x"] < R and cal["x"] + 22 > -R:
            seat(cal, "y", 0, HW(S.rot))
    else:
        L = Rr = 0.0
        anyp = False
        for i in range(180):
            a = i / 180.0 * 2 * math.pi
            rr = RW(a)
            x, y = rr * math.cos(a), rr * math.sin(a)
            if cal["y"] - 22 < y < cal["y"]:
                anyp = True
                L, Rr = max(L, -x), max(Rr, x)
        if anyp:
            seat(cal, "x", L, Rr)


def sub_vol(bottom, top, level):
    wet = max(0.0, min(top, level) - bottom)
    return math.pi * R * R * wet * 1e-9


def step_thread(dt):
    if not S.hang:
        S.l, S.v = L0_TH, 0.0
        return
    n = int(math.ceil(dt / 0.001))
    h = dt / n
    for _ in range(n):
        top = S.hand - S.l
        lam = S.l / L0_TH
        F = K_TH * max(0.0, tau(lam)) if lam > 1 else 0.0
        Fb = RHO_W * G * sub_vol(top - HC, top, CUP_LEVEL) if S.cup else 0.0
        a = G - (F + Fb) / MASS - 6 * S.v
        S.v += a * h
        S.l += S.v * h * 1000
        if S.l < 20:
            S.l, S.v = 20.0, 0.0
    if S.cup and S.hand - S.l - HC < 4:
        S.hand += 4 - (S.hand - S.l - HC)


def sensor_B():
    bx, by = mag_field(S.sx - CYL_X, S.sy)
    bx += BE[0] + 20e-6 * (1 if S.sx > 0 else -1) * math.exp(-(DESK_HALF - abs(S.sx)) / 60)
    by += BE[1]
    return bx, by


def sensor_mV():
    B = sensor_B()
    u = SDIR[S.sdir]
    return V0[0] + (B[0] * u[0] + B[1] * u[1]) / 1e-5 * E_BAT / 3


def meter_reading():
    r = DIAL[S.dial]
    if r == "OFF":
        return ""
    if S.meter == "holder":
        V = E_BAT
    elif S.meter == "sensor":
        V = (sensor_mV() + 0.06 * gauss()) / 1000
    else:
        V = 0.00003 * gauss()

    def fmt(x, full, dec):
        return ("-1" if x < 0 else "1") if abs(x) >= full else "%.*f" % (dec, x)
    if r == "DCV 200m":
        return fmt(V * 1000, 199.95, 1)
    if r == "DCV 2":
        return fmt(V, 1.9995, 3)
    if r == "DCV 20":
        return fmt(V, 19.995, 2)
    if r == "DCV 200":
        return fmt(V, 199.95, 1)
    if r.startswith("DCA"):
        return "1" if S.meter == "holder" else "0.0"
    return "1"


def image_of_B():
    inv = 1 / F_CYL - 1 / S.pb
    return 1e6 if abs(inv) < 1e-6 else 1 / inv


# ==============================================================================
#  2.  화면
# ==============================================================================
BG, PANEL, PANEL2 = "#1c2027", "#22262d", "#2b2f36"
FG, FG_DIM, ACC = "#e8eef2", "#9aa3ab", "#f2c14e"


class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title(T("GPhO 2022 실험 시뮬레이터 — E1 원통 속의 원통", "GPhO 2022 Experiment Simulator — E1 Cylinder in cylinder") + "   v" + APP_VERSION)
        self.geometry("1480x920")
        self.configure(bg=BG)
        self.msg = ("", 0)
        self.disp = ""
        self.last_read = 0
        self.tab = "look"
        self.zoom = {}
        self.drag = None
        self.img = None
        self.img_key = None
        self._build()
        cal_contact(S.cal, "look")
        self._last = time.time()
        self.after(30, self._tick)

    def say(self, m):
        self.msg = (m, time.time())

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x")
        tk.Label(top, text="GPhO 2022  ·  " + T("E1 원통 속의 원통 (20점)", "E1 Cylinder in cylinder (20 pts)"), bg=BG, fg=ACC,
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=14, pady=6)
        self.tabs = {}
        for k, t in (("look", T("원통 너머 (A, C1)", "through it (A, C1)")), ("top", T("위에서 (A3)", "from above (A3)")), ("pins", T("핀 (C2)", "pins (C2)")),
                     ("thread", T("고무줄 (B)", "rubber (B)")), ("sensor", T("센서 (D)", "sensor (D)"))):
            b = tk.Button(top, text=t, command=lambda k=k: self.set_tab(k), bg=PANEL2, fg=FG, relief="flat", bd=0, padx=10, pady=4, font=("Segoe UI", 10))
            b.pack(side="left", padx=3)
            self.tabs[k] = b
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        self.cap = tk.Label(left, anchor="w", justify="left", bg=BG, fg=FG_DIM, font=("Segoe UI", 9), wraplength=1100)
        self.cap.pack(fill="x")
        self.cv = tk.Canvas(left, bg="#2e3238", highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        right = tk.Frame(body, bg=PANEL, width=310)
        right.pack(side="left", fill="y", padx=(8, 0))
        right.pack_propagate(False)
        self.bs = dict(bg=PANEL2, fg=FG, activebackground="#343941", activeforeground=FG, relief="flat", bd=0, padx=8, pady=5, font=("Segoe UI", 10))

        def H(t):
            tk.Label(right, text=t, bg=PANEL, fg=ACC, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        H(T("조작", "Controls"))
        self.ctl = tk.Frame(right, bg=PANEL)
        self.ctl.pack(fill="x")
        H(T("멀티미터", "Multimeter"))
        self.lcd = tk.Label(right, text="", bg="#b9bfb3", fg="#1b1e1c", font=("Consolas", 26, "bold"), width=8, anchor="e")
        self.lcd.pack(padx=10, pady=2)
        row = tk.Frame(right, bg=PANEL)
        row.pack(fill="x", padx=10)
        tk.Button(row, text="◀", command=lambda: self.turn(-1), **self.bs).pack(side="left")
        self.dl = tk.Label(row, text="", bg=PANEL, fg=FG, font=("Segoe UI", 10, "bold"), width=12)
        self.dl.pack(side="left", expand=True)
        tk.Button(row, text="▶", command=lambda: self.turn(1), **self.bs).pack(side="left")
        self.b_w = tk.Button(right, command=self.t_wires, **self.bs)
        self.b_w.pack(fill="x", padx=10, pady=(4, 1))
        H(T("안내", "Notes"))
        tk.Label(right, justify="left", wraplength=288, bg=PANEL, fg=FG_DIM, font=("Segoe UI", 8), text=T(
            "• ρw = 1000 kg/m³, ρm = 7500 kg/m³, μ0 = 4π×10⁻⁷ H/m.\n• 고무줄: 장력 ∝ τ = (1 − λ⁻¹)(1 − 0.2664λ + 0.1191λ²), λ = l/l0.\n• 핀: (1/(L−D) − (n_o−1)/D)(n_c d/(n_c−n_o) − D) = n_o.\n• 센서: E = 3 V일 때 1 mV ↔ 10 µT; 읽음은 E에 비례.\n• 센서를 자석 면에 너무 가까이 대지 마세요 — 오프셋이 바뀝니다; 책상 가장자리 아래에 쇠막대가 있습니다.",
            "• ρw = 1000 kg/m³, ρm = 7500 kg/m³, μ0 = 4π×10⁻⁷ H/m.\n• Rubber: tension ∝ τ = (1 − λ⁻¹)(1 − 0.2664λ + 0.1191λ²), λ = l/l0.\n• Pins: (1/(L−D) − (n_o−1)/D)(n_c d/(n_c−n_o) − D) = n_o.\n• Sensor: with E = 3 V, 1 mV ↔ 10 µT; the reading is proportional to E.\n• Keep the sensor off the magnet's face or its offset shifts; the desk has iron bars under its edges.")).pack(anchor="w", padx=10)
        self.status = tk.Label(right, justify="left", wraplength=288, bg="#12161b", fg=ACC, font=("Segoe UI", 9), anchor="nw", padx=8, pady=8)
        self.status.pack(fill="both", expand=True, padx=10, pady=10)
        self.cv.bind("<Button-1>", self.down)
        self.cv.bind("<Shift-Button-1>", lambda e: self.down(e, True))
        self.cv.bind("<B1-Motion>", self.move)
        self.cv.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag", None))
        self.cv.bind("<MouseWheel>", self.wheel)
        self.cv.bind("<Button-4>", lambda e: self.wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self.wheel(e, -1))
        self.set_tab("look")

    def set_tab(self, k):
        self.tab = k
        for kk, b in self.tabs.items():
            b.config(bg=ACC if kk == k else PANEL2, fg="#1c2027" if kk == k else FG)
        for w in self.ctl.winfo_children():
            w.destroy()
        self.dyn = []

        def B(fn, txt):
            b = tk.Button(self.ctl, command=fn, **self.bs)
            b.pack(fill="x", padx=10, pady=1)
            self.dyn.append((b, txt))
        if k == "look":
            B(self.t_dir, lambda: T("캘리퍼: 가로", "Caliper: horizontal") if S.cal["dir"] == "h" else T("캘리퍼: 세로", "Caliper: vertical"))
            B(lambda: self.t_mode(S.cal, "look"), lambda: T("턱: 물체를 물기", "Jaws: closing on the object") if S.cal["mode"] == "around" else T("턱: 앞에 대기", "Jaws: held in front"))
            B(self.t_marker, lambda: T("마커: 들고 있음 (클릭 = 앞면, Shift-클릭 = 뒷면)", "Marker: in hand (click = near side, Shift-click = far side)") if S.marker else T("마커 집기", "Pick up the marker"))
            B(self.t_wipe, lambda: T("점 지우기", "Wipe the dots off"))
            self.cap.config(text=T("멀리서 본 원통, 10 cm 뒤에 모눈종이 — 캘리퍼 몸체나 턱 끌기 · 원통 위 휠: 돌리기 · 다른 곳 휠: 확대, 끌기: 이동",
                                   "the cylinder from far away, graph paper 10 cm behind — drag the caliper's body or jaw · wheel over the cylinder: turn it · wheel elsewhere: zoom, drag: pan"))
        elif k == "top":
            B(lambda: self.t_mode(S.calT, "top"), lambda: T("턱: 물체를 물기", "Jaws: closing on the object") if S.calT["mode"] == "around" else T("턱: 앞에 대기", "Jaws: held in front"))
            B(self.t_wipe, lambda: T("점 지우기", "Wipe the dots off"))
            self.cap.config(text=T("위에서 본 원통 (호일 뚜껑) — 옆면의 점이 가장자리에 보입니다 · 캘리퍼 끌기 · 원통 위 휠: 돌리기",
                                   "the cylinder from above (foil cap) — the side-wall dots show at the rim · drag the caliper · wheel over the cylinder: turn it"))
        elif k == "pins":
            self.cap.config(text=T("왼쪽: 위에서 본 판지 — 핀을 선을 따라 끌기, 자 끌기 · 오른쪽: 핀 A 뒤의 눈 — 좌우로 끌어 머리 움직이기",
                                   "left: the cardboard from above — drag a pin along the line, drag the ruler · right: your eye behind pin A — drag sideways to move your head"))
        elif k == "thread":
            B(self.t_hang, lambda: T("원통 매달림", "Cylinder hanging") if S.hang else T("고무줄만 (원통 뗌)", "Thread alone (cylinder off)"))
            B(self.t_cup, lambda: T("물컵: 원통 아래", "Cup: under the cylinder") if S.cup else T("물컵: 책상 위", "Cup: on the desk"))
            self.cap.config(text=T("두 겹 고무줄 — 위 끝(손)을 위아래로 끌기 · 자 끌기 · 휠: 확대", "the doubled rubber thread — drag its upper end (your hand) · drag the ruler · wheel: zoom"))
        else:
            B(self.t_sdir, lambda: T("센서 화살표 ", "Sensor arrow ") + ["→ +x", "↑ +y", "← −x", "↓ −y"][S.sdir])
            self.cap.config(text=T("위에서 본 책상 — 원통의 축이 x를 따라 누움 · 센서를 붙인 캘리퍼 상자 끌기, 자 끌기 · 휠: 확대",
                                   "the desk from above — the cylinder lies with its axis along x · drag the caliper box carrying the sensor, drag the ruler · wheel: zoom"))

    def turn(self, d):
        S.dial = (S.dial + d) % len(DIAL)
        self.last_read = 0

    def t_wires(self):
        S.meter = {None: "holder", "holder": "sensor", "sensor": None}[S.meter]

    def t_dir(self):
        if S.cal["dir"] == "h":
            S.cal.update({"dir": "v", "x": -40.0, "y": -10.0, "open": 45.0})
        else:
            S.cal.update({"dir": "h", "x": -30.0, "y": 5.0, "open": 40.0})

    def t_mode(self, cal, v):
        cal["mode"] = "front" if cal["mode"] == "around" else "around"
        cal_contact(cal, v)

    def t_marker(self):
        S.marker = not S.marker

    def t_wipe(self):
        S.dots = []

    def t_hang(self):
        S.hang = not S.hang
        S.v = 0.0

    def t_cup(self):
        S.cup = not S.cup

    def t_sdir(self):
        S.sdir = (S.sdir + 1) % 4

    # ---- maps ---- #
    def vmap(self, v=None):
        v = v or self.tab
        W, H = max(600, self.cv.winfo_width()), max(400, self.cv.winfo_height())
        if v == "look":
            k, ox, oy = min(W / 100.0, (H - 40) / 62.0), W / 2, H - 30 - 8 * min(W / 100.0, (H - 40) / 62.0)
        elif v == "top":
            k, ox, oy = min(W / 120.0, (H - 40) / 80.0), W / 2, H / 2
        elif v == "thread":
            k, ox, oy = (H - 40) / 490.0, W * 0.45, H - 20
        elif v == "sensor":
            k, ox, oy = min((W - 40) / 800.0, (H - 40) / 420.0), W / 2, H / 2
        else:
            k, ox, oy = min((W / 2 - 40) / 180.0, (H - 80) / 120.0), W / 4, H / 2
        z = self.zoom.get(v, [1.0, 0.0, 0.0])
        k, ox, oy = k * z[0], ox + z[1], oy + z[2]
        return k, (lambda x, y: (ox + x * k, oy - y * k)), (lambda sx, sy: ((sx - ox) / k, (oy - sy) / k))

    # ---- drawing helpers ---- #
    def paper(self, W, H):
        c = self.cv
        k, P, M = self.vmap()
        c.create_rectangle(0, 0, W, H, fill="#f6f2e9", outline="")
        u0, v1 = M(0, 0)
        u1, v0 = M(W, H)
        step = 1 if k >= 3 else 5
        for u in range(int(math.floor(u0)), int(u1) + 1):
            if u % step:
                continue
            x = P(u, 0)[0]
            c.create_line(x, 0, x, H, fill="#d6965f" if u % 10 == 0 else "#e4b68c" if u % 5 == 0 else "#eed4ba")
        for v in range(int(math.floor(v0)), int(v1) + 1):
            if v % step:
                continue
            y = P(0, v)[1]
            c.create_line(0, y, W, y, fill="#d6965f" if v % 10 == 0 else "#e4b68c" if v % 5 == 0 else "#eed4ba")

    def caliper(self, cal):
        c = self.cv
        k, Pm, M = self.vmap()
        v = cal["dir"] == "v"
        f, o = (cal["y"] if v else cal["x"]), cal["open"]

        def P(a, b):
            return Pm(cal["x"] - b, a) if v else Pm(a, cal["y"] + b)

        def rect(a0, a1, b0, b1, fill, tag=None):
            p, q = P(a0, b0), P(a1, b1)
            c.create_rectangle(min(p[0], q[0]), min(p[1], q[1]), max(p[0], q[0]), max(p[1], q[1]), fill=fill, outline="", tags=tag)
            return p, q
        rect(f - 8, f + 160, 0, 5, "#c9ced3", "calBody")
        for mm in range(0, 161):
            p, q = P(f + mm, 5), P(f + mm, 3.8 if mm % 10 else 2.8)
            c.create_line(p[0], p[1], q[0], q[1], fill="#3a3f45")
        rect(f - 8, f, -22, 5, "#b9bec3", "calBody")
        rect(f - 1.2, f, -22, 0, "#dfe3e6")
        rect(f + o, f + o + 8, -22, 5, "#b9bec3", "calJaw")
        rect(f + o, f + o + 1.2, -22, 0, "#dfe3e6", "calJaw")
        rect(f + o, f + o + 48, 5, 19, "#2a2d31", "calJaw")
        p, q = rect(f + o + 6, f + o + 34, 8, 16, "#b9bfb3", "calJaw")
        c.create_text((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, text="%.2f" % o, fill="#1b1e1c", font=("Consolas", max(9, int(5.4 * k)), "bold"),
                      angle=90 if v else 0, tags="calJaw")

    def ruler(self, Rp, vertical):
        c = self.cv
        k, Pm, M = self.vmap()

        def P(a, b):
            return Pm(Rp[0] + b, Rp[1] + a) if vertical else Pm(Rp[0] + a, Rp[1] - b)
        p, q = P(-4, 0), P(304, 25)
        c.create_rectangle(min(p[0], q[0]), min(p[1], q[1]), max(p[0], q[0]), max(p[1], q[1]), fill="#f0f2ec", outline="#9aa3ab", tags="ruler")
        for mm in range(0, 301):
            if k < 1.6 and mm % 5:
                continue
            ln = 7 if mm % 10 == 0 else 5 if mm % 5 == 0 else 3.2
            a, b = P(mm, 0), P(mm, ln)
            c.create_line(a[0], a[1], b[0], b[1], fill="#1a1a1a", tags="ruler")
            if mm % 10 == 0 and (k > 1.2 or mm % 50 == 0):
                t = P(mm, 11)
                c.create_text(t[0], t[1], text=str(mm // 10), fill="#1a1a1a", font=("Arial", max(7, int(2.6 * k)), "bold"), tags="ruler")

    # ---- the views ---- #
    def look_image(self, k):
        key = (round(k, 3), round(S.rot, 4), len(S.dots))
        if key == self.img_key:
            return self.img
        self.img_key = key
        w, hh = int(math.ceil(2 * R * k)) + 2, int(math.ceil(HC * k)) + 2
        back = [(math.pi - (ph + S.rot), z) for ph, z in S.dots if math.cos(ph + S.rot) < 0.05]
        cols = []
        for px in range(w):
            y = (px + 0.5) / k - R
            cols.append((y, trace_ray(y, False), trace_ray(y, True)))
        rows = []
        for py in range(hh):
            z = HC - (py + 0.5) / k
            in_mag = abs(z - ZM) < HM / 2
            row = []
            for y, t0, t1 in cols:
                if abs(y) > R:
                    row.append("#2e3238")
                    continue
                tr_ = t1 if in_mag else t0
                if z > HC - 0.35 or z < 0.35:
                    col = (196, 200, 205)
                elif tr_[0]:
                    s = math.sqrt(max(0.0, 1 - (y / (NO * RM)) ** 2))
                    col = (96 + 70 * s, 100 + 70 * s, 108 + 70 * s)
                else:
                    col = [246, 242, 233]
                    for wv in (tr_[1], z):
                        dd = abs(wv - round(wv)) * k
                        n = round(wv)
                        if dd < 0.7:
                            cc = (214, 150, 96) if n % 10 == 0 else (228, 182, 140) if n % 5 == 0 else (238, 212, 186)
                            col = list(cc)
                    col = [col[0] * 0.9, col[1] * 0.95, col[2] * 0.97]
                    for a, dz in back:
                        if abs(z - dz) < 0.5 and tr_[2] is not None:
                            da = math.atan2(math.sin(tr_[2] - a), math.cos(tr_[2] - a))
                            if abs(da) * R < 0.5:
                                col = [x * 0.25 for x in col]
                e = abs(y) / R
                dark = 1 - 0.55 * ((e - 0.88) / 0.12) ** 2 if e > 0.88 else 1
                row.append("#%02x%02x%02x" % tuple(int(max(0, min(255, x * dark))) for x in col))
            rows.append("{" + " ".join(row) + "}")
        self.img = tk.PhotoImage(width=w, height=hh)
        self.img.put(" ".join(rows))
        return self.img

    def draw_look(self, W, H):
        c = self.cv
        k, P, M = self.vmap()
        self.paper(W, H)
        img = self.look_image(k)
        p = P(-R, HC)
        c.create_image(p[0], p[1], image=img, anchor="nw", tags="cyl")
        for ph, z in S.dots:
            th = ph + S.rot
            if math.cos(th) <= 0:
                continue
            q = P(R * math.sin(th), z)
            r = max(1.5, 0.45 * k)
            c.create_oval(q[0] - r, q[1] - r, q[0] + r, q[1] + r, fill="#14161e", outline="")
        self.caliper(S.cal)

    def draw_top(self, W, H):
        c = self.cv
        k, P, M = self.vmap()
        self.paper(W, H)
        pts = []
        for i in range(120):
            a = i / 120.0 * 2 * math.pi
            rr = RW(a)
            pts.extend(P(rr * math.cos(a), rr * math.sin(a)))
        c.create_polygon(*pts, fill="#c4c8cd", outline="#7d838a", tags="cyl")
        c0 = P(0, 0)
        sq = []
        for (u, v) in ((-6, -6), (6, -6), (6, 6), (-6, 6)):
            x = u * math.cos(S.rot) - v * math.sin(S.rot)
            y = u * math.sin(S.rot) + v * math.cos(S.rot)
            sq.extend(P(x, y))
        c.create_polygon(*sq, fill="#f7f6f0", outline="")
        for ph, z in S.dots:
            th = ph + S.rot
            rr = RW(th)
            q = P(rr * math.sin(th), -rr * math.cos(th))
            r = max(1.5, 0.5 * k)
            c.create_oval(q[0] - r, q[1] - r, q[0] + r, q[1] + r, fill="#14161e", outline="")
        e = P(0, -40)
        c.create_text(e[0], e[1], text=T("▲ 원통 너머 보기의 눈 방향", "▲ where you look through it from"), fill="#596069")
        self.caliper(S.calT)

    def draw_pins(self, W, H):
        c = self.cv
        k, P, M = self.vmap()
        a, b = P(-85, 55), P(85, -55)
        c.create_rectangle(a[0], a[1], b[0], b[1], fill="#c9a878", outline="")
        s0, s1 = P(-85, 0), P(85, 0)
        c.create_line(s0[0], s0[1], s1[0], s1[1], fill="#6e5a3c", dash=(6, 4))
        c0 = P(0, 0)
        c.create_oval(c0[0] - R * k, c0[1] - R * k, c0[0] + R * k, c0[1] + R * k, fill="#c8ccd1", outline="#7d838a")
        for tag, x, col, lab in (("pinA", S.pa, "#c8262b", "A"), ("pinB", S.pb, "#2b62c4", "B")):
            q = P(x, 0)
            c.create_oval(q[0] - 1.6 * k, q[1] - 1.6 * k, q[0] + 1.6 * k, q[1] + 1.6 * k, fill=col, outline="", tags=tag)
            c.create_text(q[0], q[1] - 2.6 * k, text=lab, fill="#eee", font=("Segoe UI", 9, "bold"))
        self.ruler(S.rulP, False)
        X0, Wv = W / 2 + 10, W / 2 - 20
        cx, base, Kv, e = X0 + Wv / 2, H * 0.78, Wv / 50.0, S.eye
        c.create_rectangle(X0, 20, X0 + Wv, H - 20, fill="#dfe3e6", outline="", tags="eye")
        c.create_rectangle(X0, base, X0 + Wv, H - 20, fill="#c9a878", outline="", tags="eye")
        EYE_D = 250.0
        sA, sI = -S.pa, image_of_B()
        Dc, DI, DB = EYE_D + sA, EYE_D + sA - sI, EYE_D + sA + S.pb

        def sx(X, Dd):
            return cx + Kv * (X - e) * EYE_D / Dd

        def sy(Y, Dd):
            return base - Kv * Y * EYE_D / Dd
        l, r, topc = sx(-R, Dc), sx(R, Dc), sy(HC, Dc)
        mt, mb = sy(ZM + HM / 2, Dc), sy(ZM - HM / 2, Dc)
        c.create_rectangle(l, topc, r, base, fill="#c7dbe4", outline="", tags="eye")
        c.create_rectangle(sx(-NO * RM, Dc), mt, sx(NO * RM, Dc), mb, fill="#7e848b", outline="", tags="eye")
        xi = sx(0, DI)
        wI = max(1.0, 0.7 * abs(sI / S.pb) * Kv * EYE_D / abs(DI))
        yt = max(topc, sy(35, DB))
        if l < xi < r:
            c.create_rectangle(xi - wI / 2, yt, xi + wI / 2, mt, fill="#2b62c4", outline="", tags="eye")
            c.create_rectangle(xi - wI / 2, mb, xi + wI / 2, base, fill="#2b62c4", outline="", tags="eye")
        xa, ya = sx(0, EYE_D), sy(35, EYE_D)
        c.create_rectangle(xa - 0.35 * Kv, ya, xa + 0.35 * Kv, base, fill="#555b62", outline="", tags="eye")
        c.create_oval(xa - 1.6 * Kv, ya - 1.6 * Kv, xa + 1.6 * Kv, ya + 1.6 * Kv, fill="#c8262b", outline="", tags="eye")
        c.create_text(X0 + 8, 34, anchor="w", text=T("머리 위치: ", "head: ") + "%+.1f mm" % e, fill="#33373d")

    def draw_thread(self, W, H):
        c = self.cv
        k, P, M = self.vmap()
        d0 = P(0, 0)
        c.create_rectangle(0, d0[1], W, H, fill="#4a4e55", outline="")
        topv = S.hand - S.l
        if S.cup:
            a, b = P(-CUP_W / 2, CUP_H), P(CUP_W / 2, 0)
            wl = P(0, CUP_LEVEL)[1]
            c.create_rectangle(a[0], wl, b[0], b[1], fill="#5f86a8", outline="")
        hp = P(0, S.hand)
        c.create_oval(hp[0] - 10, hp[1] - 22, hp[0] + 22, hp[1], fill="#d6a98a", outline="", tags="hand")
        endY = topv if S.hang else S.hand - L0_TH
        for dx in (-0.8, 0.8):
            a, b = P(dx, S.hand), P(dx, endY)
            c.create_line(a[0], a[1], b[0], b[1], fill="#111")
        for yy in (S.hand - 2, endY + 2):
            t = P(-3, yy)
            c.create_rectangle(t[0], t[1], t[0] + 6 * k, t[1] + 3 * k, fill="#f4f1e4", outline="")
        if S.hang:
            p, q = P(-R, topv), P(R, topv - HC)
            c.create_rectangle(p[0], p[1], q[0], q[1], fill="#cde2ec", outline="#c4c8cd")
            m1, m2 = P(-RM, topv - (HC - ZM) + HM / 2), P(RM, topv - (HC - ZM) - HM / 2)
            c.create_rectangle(m1[0], m1[1], m2[0], m2[1], fill="#858b92", outline="")
        if S.cup:
            a, b = P(-CUP_W / 2, CUP_H), P(CUP_W / 2, 0)
            wl = P(0, CUP_LEVEL)[1]
            c.create_line(a[0], wl, b[0], wl, fill="#a0c8eb")
            c.create_line(a[0], a[1], a[0], b[1], b[0], b[1], b[0], a[1], fill="#dcebf5", width=2)
        self.ruler(S.rulT, True)

    def draw_sensor(self, W, H):
        c = self.cv
        k, P, M = self.vmap()
        a, b = P(-DESK_HALF, 400), P(DESK_HALF, -400)
        c.create_rectangle(a[0], a[1], b[0], b[1], fill="#b99b74", outline="")
        p, q = P(CYL_X - HC / 2, R), P(CYL_X + HC / 2, -R)
        c.create_rectangle(p[0], p[1], q[0], q[1], fill="#cde2ec", outline="#c4c8cd")
        m1, m2 = P(CYL_X - HM / 2, RM), P(CYL_X + HM / 2, -RM)
        c.create_rectangle(m1[0], m1[1], m2[0], m2[1], fill="#858b92", outline="")
        self.ruler(S.rulS, False)
        b0, b1 = P(S.sx + 3, 25), P(S.sx + 173, -25)
        c.create_rectangle(b0[0], b0[1], b1[0], b1[1], fill="#e1e4e7", outline="#8a9096", tags="sensor")
        s0, s1 = P(S.sx - 3, 2.2), P(S.sx + 3, -2.2)
        c.create_rectangle(s0[0], s0[1], s1[0], s1[1], fill="#18191b", outline="", tags="sensor")
        for i, col in enumerate(("#2b62c4", "#1d1d1f", "#e3b21a", "#c8262b")):
            w0, w1 = P(S.sx + 3, (i - 1.5) * 1.1), P(S.sx + 400, (i - 1.5) * 1.1 + 30)
            c.create_line(w0[0], w0[1], w1[0], w1[1], fill=col, width=2)
        u = SDIR[S.sdir]
        a0, a1 = P(S.sx + 8 - u[0] * 8, 40 - u[1] * 8), P(S.sx + 8 + u[0] * 8, 40 + u[1] * 8)
        c.create_line(a0[0], a0[1], a1[0], a1[1], fill="#111", width=3, arrow="last")
        x0 = P(DESK_HALF - 30, 360)
        c.create_text(x0[0], x0[1], text="x →", fill="#3a2d1e", font=("Segoe UI", 11, "bold"))

    # ---- mouse ---- #
    def tag_at(self, e):
        for it in reversed(self.cv.find_overlapping(e.x, e.y, e.x, e.y)):
            for t in self.cv.gettags(it):
                if t in ("calBody", "calJaw", "ruler", "pinA", "pinB", "hand", "sensor", "eye", "cyl"):
                    return t
        return None

    def down(self, e, shift=False):
        k, P, M = self.vmap()
        t = self.tag_at(e)
        w = M(e.x, e.y)
        if self.tab == "look" and S.marker and t == "cyl":
            y, z = w
            if abs(y) < R and 0.4 < z < HC - 0.4:
                if not shift:
                    S.dots.append((math.asin(y / R) - S.rot, z))
                else:
                    tr_ = trace_ray(y, abs(z - ZM) < HM / 2)
                    if not tr_[0] and tr_[2] is not None:
                        S.dots.append((math.pi - tr_[2] - S.rot, z))
            return
        cal = S.calT if self.tab == "top" else S.cal
        rul = {"pins": S.rulP, "thread": S.rulT, "sensor": S.rulS}.get(self.tab)
        self.drag = (t or "pan", w, e.x, e.y, dict(cal), list(rul) if rul else None, (S.pa, S.pb, S.hand, S.sx, S.sy, S.eye), list(self.zoom.get(self.tab, [1.0, 0.0, 0.0])))

    def move(self, e):
        if not self.drag:
            return
        t, w0, x0, y0, c0, r0, s0, z0 = self.drag
        k, P, M = self.vmap()
        w = M(e.x, e.y)
        d = (w[0] - w0[0], w[1] - w0[1])
        if t in ("calBody", "calJaw") and self.tab in ("look", "top"):
            cal = S.calT if self.tab == "top" else S.cal
            if t == "calBody":
                cal["x"], cal["y"] = c0["x"] + d[0], c0["y"] + d[1]
            else:
                cal["open"] = max(0.0, min(150.0, c0["open"] + (d[1] if cal["dir"] == "v" else d[0])))
            cal_contact(cal, self.tab)
        elif t == "ruler" and r0:
            rul = {"pins": S.rulP, "thread": S.rulT, "sensor": S.rulS}[self.tab]
            rul[0], rul[1] = r0[0] + d[0], r0[1] + d[1]
        elif t == "pinA":
            S.pa = min(-R - 3, max(-84.0, s0[0] + d[0]))
        elif t == "pinB":
            S.pb = max(R + 3, min(84.0, s0[1] + d[0]))
        elif t == "hand":
            S.hand = max(150.0, min(470.0, s0[2] + d[1]))
        elif t == "sensor":
            S.sx = max(-DESK_HALF + 20, min(DESK_HALF - 10, s0[3] + d[0]))
            S.sy = max(-380.0, min(380.0, s0[4] + d[1]))
        elif t == "eye":
            S.eye = max(-15.0, min(15.0, s0[5] + (e.x - x0) / 12.0))
        else:
            self.zoom[self.tab] = [z0[0], z0[1] + e.x - x0, z0[2] + e.y - y0]

    def wheel(self, e, d=None):
        if d is None:
            d = 1 if e.delta > 0 else -1
        t = self.tag_at(e)
        if self.tab in ("look", "top") and t == "cyl":
            S.rot += d * 3 * math.pi / 180
            cal_contact(S.calT if self.tab == "top" else S.cal, self.tab)
            return
        z = self.zoom.get(self.tab, [1.0, 0.0, 0.0])
        f = 1.15 if d > 0 else 1 / 1.15
        nz = max(0.5, min(12.0, z[0] * f))
        r = nz / z[0]
        k, P, M = self.vmap()
        ox, oy = P(0, 0)
        ox0, oy0 = ox - z[1], oy - z[2]
        self.zoom[self.tab] = [nz, (e.x - ox0) - (e.x - ox0 - z[1]) * r, (e.y - oy0) - (e.y - oy0 - z[2]) * r]

    def _tick(self):
        now = time.time()
        dt = min(0.05, now - self._last)
        self._last = now
        step_thread(dt)
        B = sensor_B()
        mag = math.hypot(B[0], B[1])
        if mag > 6e-3 and not S.near:
            S.near = True
            V0[0] += (-1 if RNG.random() < 0.5 else 1) * (1.5 + 2 * RNG.random())
            self.say(T("센서가 자석에 너무 가까이 갔습니다: 오프셋이 바뀌었습니다", "the sensor came too close to the magnet: its offset has shifted"))
        if mag < 3e-3:
            S.near = False
        if now - self.last_read > 0.333:
            self.last_read = now
            self.disp = meter_reading()
        try:
            W, H = max(600, self.cv.winfo_width()), max(400, self.cv.winfo_height())
            self.cv.delete("all")
            {"look": self.draw_look, "top": self.draw_top, "pins": self.draw_pins, "thread": self.draw_thread, "sensor": self.draw_sensor}[self.tab](W, H)
        except tk.TclError:
            return
        self.lcd.config(text=self.disp)
        self.dl.config(text=DIAL[S.dial])
        for b, txt in self.dyn:
            b.config(text=txt())
        self.b_w.config(text={None: T("전선: 연결 안 됨", "Wires: free"), "holder": T("전선: 건전지 홀더 단자에", "Wires: on the battery holder's leads"),
                              "sensor": T("전선: 센서의 노랑·빨강 선에", "Wires: on the sensor's yellow and red wires")}[S.meter])
        w = []
        if self.msg[0] and now - self.msg[1] < 5:
            w.append(self.msg[0])
        self.status.config(text="\n\n".join(w))
        self.after(30, self._tick)


if __name__ == "__main__":
    App().mainloop()
