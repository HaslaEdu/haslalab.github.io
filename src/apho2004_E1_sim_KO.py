#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  5th Asian Physics Olympiad  (APhO 2004, Hanoi, Vietnam)
  Experimental Problem 1 :  HALL EFFECT AND MAGNETORESISTIVITY
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* The Hall sensor: current terminals P, Q (resistance Rin); voltage
  terminals M, N, with a misalignment so that U_MN = roff*I even without
  a field, plus the Hall voltage alpha*I*B_perp; the M-N resistance grows
  with the field as R0(1 + c|B|^k).
* The disc magnet stands on the protractor round the needle: on its axis
  B(y) = (B0/2)[(y+t)/sqrt((y+t)^2+R^2) - y/sqrt(y^2+R^2)], and the part
  perpendicular to the sensor's plate goes as sin(phi - phi0).
* The toroid (N turns, mean radius 25 mm, gap 3 mm, core mu) gives
  B = mu0*N*I/((2 pi r - d)/mu + d) in its gap.
* Any wiring of the sensor, the two batteries (one with a 10 kohm
  variable resistor), the coil and three multimeters is solved by nodal
  analysis; the 200 mA range blows its 0.2 A fuse.
* alpha, roff, R0, c, k, phi0, N and mu are hidden and randomised.
* Standard library only (tkinter).

    Run:   python3 apho2004_E1_sim_KO.py
"""

import math
import random
import tkinter as tk
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line

TERMS = ["M", "N", "P", "Q", "B1+", "B1-", "B2+", "B2-", "L1", "L2", "D1V", "D1A", "D1C", "D2V", "D2A", "D2C", "D3V", "D3A", "D3C"]
# range: (jack, input resistance, full scale, unit, factor, test current)
MODES = {"off": None, "mv": ("V", 1e7, 199.99, "mV", 1e3, 0), "v": ("V", 1e7, 19.999, "V", 1.0, 0), "ohm": ("V", 1e7, 1999.9, "ohm", 1.0, 5e-4),
         "ma": ("V", 1.0, 199.99, "mA", 1e3, 0), "a20": ("A", 0.01, 19.999, "A", 1.0, 0)}
MU0 = 4 * math.pi * 1e-7
RMAG, TMAG, RHO, GAP = 0.014, 0.004, 0.025, 0.003


# --------------------------------------------------------------------------
#  Physics core  (SI)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.alpha = r.uniform(400, 800)
        self.roff = r.uniform(-1.3, 1.3)
        self.R0, self.Rin = r.uniform(330, 370), r.uniform(330, 380)
        self.k = r.uniform(1.72, 1.95)
        self.c = r.uniform(0.012, 0.022) / 0.035 ** self.k
        self.phi0 = r.uniform(0, 360)
        self.B0 = r.choice((0.30, 0.35, 0.40))
        self.N = r.randint(80, 120)
        self.mu = r.uniform(250, 700)
        self.rCoil = r.uniform(0.18, 0.26)
        self.e1, self.e2, self.r1, self.r2 = r.uniform(1.52, 1.58), r.uniform(1.52, 1.60), r.uniform(0.4, 0.8), r.uniform(0.15, 0.22)
        self.drain = r.uniform(0.004, 0.008)

    def Baxis(self, y):
        return self.B0 / 2 * ((y + TMAG) / math.hypot(y + TMAG, RMAG) - y / math.hypot(y, RMAG))

    def Bgap(self, I):
        return MU0 * self.N * I / ((2 * math.pi * RHO - GAP) / self.mu + GAP)


def make_nets(leads):
    par = dict((t, t) for t in TERMS)

    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for a, b in leads:
        par[f(a)] = f(b)
    return f


def rsolve(A, b):
    n = len(b)
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(A[r][i]))
        A[i], A[p] = A[p], A[i]
        b[i], b[p] = b[p], b[i]
        for r in range(i + 1, n):
            k = A[r][i] / A[i][i]
            for c in range(i, n):
                A[r][c] -= k * A[i][c]
            b[r] -= k * b[i]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (b[i] - sum(A[i][c] * x[c] for c in range(i + 1, n))) / A[i][i]
    return x


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def art_sheet(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 50 * s, y - 34 * s, x + 50 * s, y + 34 * s, fill="#fbfbf8", outline="#999")
    cv.create_rectangle(x - 4 * s, y - 4 * s, x + 30 * s, y + 4 * s, fill="#d6e4ea", outline="#8fa7b4")
    cv.create_oval(x - 2 * s, y - 2 * s, x + 2 * s, y + 2 * s, fill="#c0392b", outline="")


def art_sensor(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 14 * s, y - 10 * s, x + 14 * s, y + 8 * s, fill="#2f6b3a", outline="#1b3a20")
    cv.create_rectangle(x - 4 * s, y - 5 * s, x + 4 * s, y + 1 * s, fill="#111", outline="")
    for i, c in enumerate(("#111", "#d9c21b", "#c0392b", "#2f8f4e")):
        cv.create_line(x - 9 * s + i * 6 * s, y + 8 * s, x - 9 * s + i * 6 * s, y + 22 * s, fill=c, width=2)


def art_prot(cv, x, y, sc=1.0):
    s = sc
    cv.create_arc(x - 40 * s, y - 40 * s, x + 40 * s, y + 40 * s, start=0, extent=180, fill="#dbe7ec", outline="#7f9fb0")


def art_magnet(cv, x, y, sc=1.0):
    s = sc
    cv.create_oval(x - 16 * s, y - 16 * s, x + 16 * s, y + 16 * s, fill="#5a5f66", outline="#333")
    cv.create_oval(x - 5 * s, y - 5 * s, x + 5 * s, y + 5 * s, fill="#7a7f86", outline="")


def art_toroid(cv, x, y, sc=1.0):
    s = sc
    cv.create_arc(x - 24 * s, y - 24 * s, x + 24 * s, y + 24 * s, start=15, extent=330, style="arc", outline="#b0442a", width=max(2, int(9 * s)))


def art_batt(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 40 * s, y - 22 * s, x + 40 * s, y + 22 * s, fill="#1b1d20", outline="#444")
    cv.create_rectangle(x - 34 * s, y - 14 * s, x - 6 * s, y + 4 * s, fill="#b03a2a", outline="")
    cv.create_rectangle(x + 6 * s, y - 14 * s, x + 34 * s, y + 4 * s, fill="#b03a2a", outline="")
    cv.create_oval(x - 26 * s, y + 6 * s, x - 14 * s, y + 18 * s, fill="#e8eef2", outline="")


def art_dmm(cv, x, y, sc=1.0):
    s = sc
    cv.create_rectangle(x - 24 * s, y - 38 * s, x + 24 * s, y + 38 * s, fill="#c0392b", outline="#555")
    cv.create_rectangle(x - 17 * s, y - 31 * s, x + 17 * s, y - 14 * s, fill="#9fae8f", outline="")
    cv.create_oval(x - 11 * s, y - 6 * s, x + 11 * s, y + 16 * s, fill="#1b1d20", outline="")


def art_leads(cv, x, y, sc=1.0):
    s = sc
    for c, r in (("#c0392b", 26), ("#1f2226", 20), ("#2b6cb0", 14)):
        cv.create_oval(x - r * s, y - r * 0.6 * s, x + r * s, y + r * 0.6 * s, outline=c, width=2)


ART = {"sheet": art_sheet, "sensor": art_sensor, "prot": art_prot, "magnet": art_magnet, "toroid": art_toroid, "batt": art_batt,
       "dmm1": art_dmm, "dmm2": art_dmm, "dmm3": art_dmm, "leads": art_leads}

PARTS = [
    ("sheet",  ("[1] 바늘 달린 받침 종이 (mm 자)", "[1] Base sheet with needle (mm rule)"), []),
    ("prot",   ("[2] 각도기", "[2] Protractor"), ["sheet"]),
    ("sensor", ("[3] 홀 센서 (M N P Q)", "[3] Hall sensor (M N P Q)"), ["sheet"]),
    ("magnet", ("[4] 원판 자석", "[4] Disc magnet"), ["prot"]),
    ("toroid", ("[5] 토로이드 코일 (틈 있음)", "[5] Toroidal coil (with gap)"), []),
    ("batt",   ("[6] 건전지 상자 (1: 10 kΩ, 2: 코일)", "[6] Battery box (1: 10 kohm, 2: coil)"), []),
    ("dmm1",   ("[7] 멀티미터 1", "[7] Multimeter 1"), []),
    ("dmm2",   ("[7] 멀티미터 2", "[7] Multimeter 2"), []),
    ("dmm3",   ("[7] 멀티미터 3", "[7] Multimeter 3"), []),
    ("leads",  ("[8] 연결 도선", "[8] Leads"), []),
]
ZONES = {
    "sheet": (250, 170, 110, 75), "prot": (250, 140, 90, 45), "sensor": (250, 185, 35, 35), "magnet": (300, 120, 35, 35), "toroid": (480, 170, 55, 55),
    "batt": (180, 380, 90, 50), "dmm1": (330, 380, 55, 85), "dmm2": (430, 380, 55, 85), "dmm3": (530, 380, 55, 85), "leads": (650, 380, 70, 40),
}
SCENE_TITLE = ("받침 종이 위의 센서·각도기·자석, 옆에는 토로이드 코일과 계기", "Sensor, protractor and magnet on the sheet; the coil and the meters beside")
APP_TITLE = ("APhO 2004 실험 1 — 홀 효과와 자기저항", "APhO 2004 Experiment 1 — Hall effect and magnetoresistivity")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.leads = []
        self.where = tk.StringVar(value="needle")     # the sensor: on the needle, or in the coil's gap
        self.y, self.phi = 2.0, 90.0                   # the magnet: distance from the needle (cm), protractor reading (deg)
        self.pot = 5.0                                 # battery 1's resistor, kohm
        self.mode = [tk.StringVar(value="off") for _ in range(3)]
        self.fuse = [True, True, True]
        self.e2, self.Ts = 1.0, 0.0
        self.disp, self.disp_t = [0.0, 0.0, 0.0], 0.0
        self.drag = False
        self.build()
        self.refresh()

    def has(self, k):
        return k in self.app.placed

    def Bperp(self, Icoil):
        ph = self.ph
        if self.where.get() == "gap":
            return ph.Bgap(Icoil) if self.has("toroid") else 0.0
        if not (self.has("magnet") and self.has("prot")):
            return 0.0
        return ph.Baxis(self.y / 100) * math.sin(math.radians(self.phi - ph.phi0))

    def solve(self):
        ph, f, base = self.ph, make_nets(self.leads), []
        if self.has("batt"):
            r = ph.r1 + self.pot * 1000
            base.append((f("B1-"), f("B1+"), 1 / r, ph.e1 / r))
            base.append((f("B2-"), f("B2+"), 1 / ph.r2, ph.e2 * self.e2 / ph.r2))
        if self.has("toroid"):
            base.append((f("L1"), f("L2"), 1 / ph.rCoil, 0.0))
        for i in range(3):
            m = MODES[self.mode[i].get()]
            if not self.has("dmm%d" % (i + 1)) or not m or (m[3] == "mA" and not self.fuse[i]):
                continue
            base.append((f("D%dC" % (i + 1)), f("D%d%s" % (i + 1, m[0])), 1 / m[1], m[5]))
        sens = self.has("sensor")
        alpha = ph.alpha * (1 - 0.002 * self.Ts)
        Ipq = Icoil = 0.0
        gnd = f("B1-")
        V = lambda n: 0.0
        for _ in range(4):
            el = list(base)
            if sens:
                B = self.Bperp(Icoil)
                Rmn = ph.R0 * (1 + ph.c * abs(B) ** ph.k)
                emf = alpha * Ipq * B + ph.roff * Ipq
                el.append((f("P"), f("Q"), 1 / ph.Rin, 0.0))
                el.append((f("N"), f("M"), 1 / Rmn, emf / Rmn))
            names = []
            for p, q, _, _ in el:
                for n in (p, q):
                    if n != gnd and n not in names:
                        names.append(n)
            idx = dict((n, i) for i, n in enumerate(names))
            N = len(names)
            A = [[1e-9 if i == j else 0.0 for j in range(N)] for i in range(N)]
            b = [0.0] * N
            for p, q, g, I in el:
                i, j = idx.get(p), idx.get(q)
                if i is not None:
                    A[i][i] += g
                    b[i] -= I
                if j is not None:
                    A[j][j] += g
                    b[j] += I
                if i is not None and j is not None:
                    A[i][j] -= g
                    A[j][i] -= g
            x = rsolve(A, b) if N else []
            V = (lambda x, idx: (lambda n: 0.0 if n == gnd else (x[idx[n]] if n in idx else 0.0)))(x, idx)
            Ipq = (V(f("P")) - V(f("Q"))) / ph.Rin if sens else 0.0
            Icoil = (V(f("L1")) - V(f("L2"))) / ph.rCoil if self.has("toroid") else 0.0
        return V, f, Ipq, Icoil

    def raw(self, i):
        m = MODES[self.mode[i].get()]
        if not self.has("dmm%d" % (i + 1)) or not m:
            return None
        if m[3] == "mA" and not self.fuse[i]:
            return 0.0
        V, f, _, _ = self.solve()
        v = V(f("D%d%s" % (i + 1, m[0]))) - V(f("D%dC" % (i + 1)))
        if m[5]:
            return v / m[5]
        return v / m[1] * m[4] if m[1] < 1e6 else v * m[4]

    def show(self, i):
        m = MODES[self.mode[i].get()]
        if not self.has("dmm%d" % (i + 1)) or not m:
            return "—"
        v = self.disp[i]
        if abs(v) > m[2]:
            return "1"
        dg = 3 if m[2] < 20 else 2 if m[2] < 200 else 1
        return ("%." + str(dg) + "f") % v + " " + m[3]

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("멀티미터", "Multimeters"))
        f.pack(fill="x", pady=2)
        self.lbl = []
        for i in range(3):
            row = ttk.Frame(f)
            row.pack(fill="x")
            l = tk.Label(row, text="", font=("Courier", 14, "bold"), bg="#9fae8f", fg="#1b1d20", width=11)
            l.pack(side="left", pady=1)
            self.lbl.append(l)
            for md, lab in (("off", "OFF"), ("mv", "200mV"), ("v", "20V"), ("ohm", "2kΩ"), ("ma", "200mA"), ("a20", "20A")):
                ttk.Radiobutton(row, text=lab, value=md, variable=self.mode[i]).pack(side="left")
        ttk.Button(f, text=T("끊어진 퓨즈 갈기", "Replace a blown fuse"), command=self.new_fuse).pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("센서 · 자석", "Sensor · magnet"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Radiobutton(row, text=T("센서를 바늘에", "Sensor on the needle"), value="needle", variable=self.where).pack(side="left")
        ttk.Radiobutton(row, text=T("센서를 코일 틈에", "Sensor in the coil's gap"), value="gap", variable=self.where).pack(side="left")
        stepper(f, T("자석 거리 y", "Magnet distance y"), [("−5 mm", lambda: self.mv(-0.5)), ("−1 mm", lambda: self.mv(-0.1)), ("+1 mm", lambda: self.mv(0.1)), ("+5 mm", lambda: self.mv(0.5))])
        stepper(f, T("자석 각도", "Magnet angle"), [("−10°", lambda: self.rot(-10)), ("−1°", lambda: self.rot(-1)), ("−0.5°", lambda: self.rot(-0.5)), ("+0.5°", lambda: self.rot(0.5)), ("+1°", lambda: self.rot(1)), ("+10°", lambda: self.rot(10))])
        self.magl = ttk.Label(f, text="")
        self.magl.pack(anchor="w")
        f = ttk.LabelFrame(ctl, text=T("가변저항 (건전지 1, 0–10 kΩ)", "Variable resistor (battery 1, 0-10 kohm)"))
        f.pack(fill="x", pady=2)
        self.potl = ttk.Label(f, text="")
        self.potl.pack(anchor="w")
        stepper(f, "", [("−1", lambda: self.turn(-1)), ("−0.1", lambda: self.turn(-0.1)), ("−0.01", lambda: self.turn(-0.01)), ("+0.01", lambda: self.turn(0.01)), ("+0.1", lambda: self.turn(0.1)), ("+1", lambda: self.turn(1))])
        f = ttk.LabelFrame(ctl, text=T("배선 — 단자 두 개를 골라 잇기", "Wiring — pick two terminals and join them"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.ta, self.tb = ttk.Combobox(row, values=TERMS, width=5, state="readonly"), ttk.Combobox(row, values=TERMS, width=5, state="readonly")
        self.ta.pack(side="left", padx=2)
        self.tb.pack(side="left", padx=2)
        ttk.Button(row, text=T("잇기", "Join"), command=self.join).pack(side="left", padx=2)
        ttk.Button(row, text=T("고른 것 뽑기", "Unplug"), command=self.unplug).pack(side="left", padx=2)
        self.lb = tk.Listbox(f, height=5)
        self.lb.pack(fill="x")
        f = ttk.LabelFrame(ctl, text=T("기록", "Record"))
        f.pack(fill="both", expand=True, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.note = ttk.Entry(row, width=16)
        self.note.pack(side="left", padx=2)
        ttk.Button(row, text=T("지금 값 적기", "Record"), command=self.record).pack(side="left", padx=2)
        self.sheet = DataSheet(f, [("a", "M1", 80), ("b", "M2", 80), ("c", "M3", 80), ("n", T("메모", "note"), 100)], height=4)
        self.sheet.pack(fill="both", expand=True)
        sheet_buttons(f, self.sheet, self.app)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=380)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("각도기(위에서 · 자석을 끌어 옮기기), 코일, 회로", "Protractor (from above · drag the magnet), coil, circuit"), font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, width=760, height=640, bg="#e9e7e0", highlightthickness=0)
        self.cv.pack()
        self.cv.bind("<Button-1>", self.press)
        self.cv.bind("<B1-Motion>", self.motion)
        self.cv.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag", False))

    CX, CY, Z = 240, 300, 22.0

    def press(self, e):
        q = math.radians(self.phi)
        mx, my = self.CX + self.y * self.Z * math.cos(q), self.CY - self.y * self.Z * math.sin(q)
        self.drag = self.has("magnet") and math.hypot(e.x - mx, e.y - my) < 30

    def motion(self, e):
        if not self.drag:
            return
        x, y = (e.x - self.CX) / self.Z, (self.CY - e.y) / self.Z
        self.phi = round(max(0.0, min(180.0, math.degrees(math.atan2(max(0.0, y), x)))) * 2) / 2
        self.y = round(max(0.5, min(6.0, math.hypot(x, y))) * 20) / 20

    def mv(self, d):
        self.y = max(0.5, min(6.0, round(self.y + d, 2)))

    def rot(self, d):
        self.phi = max(0.0, min(180.0, round(self.phi + d, 1)))

    def turn(self, d):
        self.pot = max(0.0, min(10.0, round(self.pot + d, 2)))

    def new_fuse(self):
        for i in range(3):
            if not self.fuse[i]:
                self.fuse[i] = True
                return

    def join(self):
        a, b = self.ta.get(), self.tb.get()
        if a and b and a != b and len(self.leads) < 14 and self.has("leads"):
            self.leads.append((a, b))
            self.lb.insert("end", "%s — %s" % (a, b))

    def unplug(self):
        sel = self.lb.curselection()
        if sel:
            del self.leads[sel[0]]
            self.lb.delete(sel[0])

    def record(self):
        self.sheet.add((self.show(0), self.show(1), self.show(2), self.note.get()))

    def tick(self, dt):
        V, f, _, Ic = self.solve()
        Ic = abs(Ic)
        self.e2 += -self.ph.drain * dt * Ic / 3.5 if Ic > 0.5 else (1 - self.e2) * dt / 200
        self.e2 = max(0.6, self.e2)
        self.Ts += (Ic * Ic * self.ph.rCoil * (0.9 if self.where.get() == "gap" else 0.2) - self.Ts * 0.05) * dt
        for i in range(3):
            m = MODES[self.mode[i].get()]
            if m and m[3] == "mA" and self.fuse[i] and self.has("dmm%d" % (i + 1)):
                if abs(V(f("D%dV" % (i + 1))) - V(f("D%dC" % (i + 1)))) / m[1] > 0.2:
                    self.fuse[i] = False
        self.disp_t -= dt
        if self.disp_t <= 0:
            self.disp_t = 0.4
            for i in range(3):
                r = self.raw(i)
                if r is not None:
                    m = MODES[self.mode[i].get()]
                    self.disp[i] = r + (random.random() - 0.5) * 1.2 * (0.001 if m[2] < 20 else 0.01 if m[2] < 200 else 0.1)
        msgs = []
        for i in range(3):
            if not self.fuse[i]:
                msgs.append(T("멀티미터 %d의 퓨즈가 끊어졌습니다 (200mA 범위는 0.2 A까지)" % (i + 1), "Multimeter %d's fuse has blown (the 200mA range takes 0.2 A)" % (i + 1)))
            if self.show(i) == "1":
                msgs.append(T("멀티미터 %d: 범위 초과" % (i + 1), "Multimeter %d: over range" % (i + 1)))
        if self.Ts > 3:
            msgs.append(T("코일 전류로 센서가 데워지고 있습니다", "The coil current is warming the sensor"))
        if self.e2 < 0.9:
            msgs.append(T("건전지 2가 약해지고 있습니다 (쉬게 두면 돌아옵니다)", "Battery 2 is running down (rest it and it recovers)"))
        self.warn.config(text="\n".join(msgs))
        self.refresh()

    def refresh(self):
        for i in range(3):
            self.lbl[i].config(text=self.show(i))
        self.potl.config(text="%.2f kΩ" % self.pot)
        self.magl.config(text=T("자석: y = %.2f cm, %.1f°   ·   자석에 적힌 B₀ = %.2f T", "Magnet: y = %.2f cm, %.1f°   ·   printed B0 = %.2f T") % (self.y, self.phi, self.ph.B0))
        self.draw()

    TP = {"M": (60, 470), "N": (100, 470), "P": (140, 470), "Q": (180, 470), "B1+": (250, 478), "B1-": (290, 478), "B2+": (340, 478), "B2-": (380, 478),
          "L1": (560, 300), "L2": (600, 300)}
    for _i, _x in ((1, 90), (2, 330), (3, 570)):
        TP["D%dC" % _i], TP["D%dA" % _i], TP["D%dV" % _i] = (_x, 610), (_x + 50, 610), (_x + 100, 610)

    def draw(self):
        cv, Z, CX, CY = self.cv, self.Z, self.CX, self.CY
        cv.delete("all")
        if self.has("sheet"):
            cv.create_rectangle(CX - 190, CY - 200, CX + 190, CY + 40, fill="#fbfbf8", outline="#bbb")
            if self.has("prot"):
                R = 9 * Z
                cv.create_arc(CX - R, CY - R, CX + R, CY + R, start=0, extent=180, fill="#dbe7ec", outline="#7f9fb0")
                for dg in range(0, 181):
                    a = math.radians(dg)
                    ln = 10 if dg % 10 == 0 else 6 if dg % 5 == 0 else 3
                    cv.create_line(CX + R * math.cos(a), CY - R * math.sin(a), CX + (R - ln) * math.cos(a), CY - (R - ln) * math.sin(a), fill="#334")
                    if dg % 10 == 0:
                        cv.create_text(CX + (R - 22) * math.cos(a), CY - (R - 22) * math.sin(a), text=str(dg), font=("Helvetica", 7), fill="#223")
            q = math.radians(self.phi if self.has("magnet") else 0)
            u, n = (math.cos(q), -math.sin(q)), (math.sin(q), math.cos(q))
            pt = lambda a, b: (CX + (u[0] * a + n[0] * b) * Z, CY + (u[1] * a + n[1] * b) * Z)
            cv.create_polygon(*(pt(-0.8, -1) + pt(6.4, -1) + pt(6.4, 1) + pt(-0.8, 1)), fill="#d6e4ea", outline="#8fa7b4")
            for mm in range(61):
                ln = 0.6 if mm % 10 == 0 else 0.4 if mm % 5 == 0 else 0.25
                cv.create_line(*(pt(mm / 10.0, 1) + pt(mm / 10.0, 1 - ln)), fill="#223")
                if mm % 10 == 0:
                    cv.create_text(*pt(mm / 10.0, 0.2), text=str(mm // 10), font=("Helvetica", 7))
            if self.has("sensor") and self.where.get() == "needle":
                cv.create_rectangle(CX - 0.9 * Z, CY - 0.6 * Z, CX + 0.9 * Z, CY + 0.6 * Z, fill="#2f6b3a", outline="")
                cv.create_rectangle(CX - 0.3 * Z, CY - 0.25 * Z, CX + 0.3 * Z, CY + 0.25 * Z, fill="#111", outline="")
            cv.create_oval(CX - 3, CY - 3, CX + 3, CY + 3, fill="#c0392b", outline="")
            if self.has("magnet") and self.has("prot"):
                c = pt(self.y + 0.2, 0)
                cv.create_polygon(*(pt(self.y, -1.4) + pt(self.y + 0.4, -1.4) + pt(self.y + 0.4, 1.4) + pt(self.y, 1.4)), fill="#5a5f66", outline="#222")
                cv.create_line(CX, CY, c[0], c[1], dash=(3, 3), fill="#888")
        if self.has("toroid"):
            cx, cy, R = 580, 170, 85
            ga = 0.12
            cv.create_arc(cx - R, cy - R, cx + R, cy + R, start=math.degrees(ga), extent=360 - 2 * math.degrees(ga), style="arc", outline="#6b7177", width=22)
            a0, a1 = ga + 0.12, 2 * math.pi - ga - 0.12
            for i in range(self.ph.N):
                a = a0 + (a1 - a0) * (i + 0.5) / self.ph.N
                cv.create_line(cx + (R - 15) * math.cos(a), cy - (R - 15) * math.sin(a), cx + (R + 15) * math.cos(a), cy - (R + 15) * math.sin(a), fill="#b0442a" if i % 2 else "#c25a3c", width=2)
            if self.has("sensor") and self.where.get() == "gap":
                cv.create_rectangle(cx + R - 13, cy - 13, cx + R + 13, cy + 13, fill="#2f6b3a", outline="")
            cv.create_text(cx, cy, text=T("감은 수를 세시오", "count the turns"), fill="#555", font=("Helvetica", 9))
        boxes = (("sensor", 40, 430, 200, 490, "#2f6b3a", T("홀 센서", "Hall sensor")), ("batt", 230, 430, 400, 500, "#1b1d20", "1 (10 kΩ)      2"),
                 ("dmm1", 70, 520, 210, 630, "#c0392b", "M1"), ("dmm2", 310, 520, 450, 630, "#c0392b", "M2"), ("dmm3", 550, 520, 690, 630, "#c0392b", "M3"))
        for k, x0, y0, x1, y1, col, lab in boxes:
            if self.has(k):
                cv.create_rectangle(x0, y0, x1, y1, fill=col, outline="#555", width=2)
                cv.create_text((x0 + x1) / 2, y0 + 12, text=lab, fill="#fff", font=("Helvetica", 9, "bold"))
        own = lambda t: "sensor" if t in "MNPQ" else "batt" if t[0] == "B" else "toroid" if t[0] == "L" else "dmm" + t[1]
        for t, (x, y) in self.TP.items():
            if not self.has(own(t)):
                continue
            col = "#c0392b" if t.endswith("+") or t.endswith("V") or t.endswith("A") else "#1f2226" if t.endswith("-") or t.endswith("C") else "#c9a64a"
            cv.create_oval(x - 8, y - 8, x + 8, y + 8, fill=col, outline="#111")
            cv.create_text(x, y - 15, text=t, font=("Helvetica", 8, "bold"))
        cols = ["#c0392b", "#1f2226", "#2b6cb0", "#d9a21b", "#2f8f4e", "#8e44ad", "#16a085", "#7f8c8d"]
        for i, (a, b) in enumerate(self.leads):
            (x0, y0), (x1, y1) = self.TP[a], self.TP[b]
            cv.create_line(x0, y0, (x0 + x1) / 2, max(y0, y1) + 25 + 4 * i, x1, y1, smooth=True, fill=cols[i % len(cols)], width=3)


def T(ko, en):
    return ko if LANG == "ko" else en


def rr(cv, x0, y0, x1, y1, r, **kw):
    """rounded rectangle on a Tk canvas"""
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


# --------------------------------------------------------------------------
#  Assembly tab: drag each part from the list onto its place, in order
# --------------------------------------------------------------------------
class AssemblyTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.placed = set()
        self.drag = None

        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Label(left, text=T("장치 목록", "Apparatus list"),
                  font=("Helvetica", 11, "bold")).pack(anchor="w")
        self.tray = tk.Canvas(left, width=215, height=640, bg="#f2f3f5",
                              highlightthickness=1,
                              highlightbackground="#c3c7cc")
        self.tray.pack()
        self.msg = ttk.Label(left, text="", wraplength=205,
                             foreground="#8a1b1b")
        self.msg.pack(anchor="w", pady=4)

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("조립 구역 — 준비 절차 순서대로 놓으시오",
                                "Assembly area — follow the preparation order"),
                  font=("Helvetica", 11, "bold")).pack(anchor="w")
        self.scene = tk.Canvas(right, width=760, height=640, bg="#e9ebee",
                               highlightthickness=1,
                               highlightbackground="#c3c7cc")
        self.scene.pack(fill="both", expand=True)

        self.tray.bind("<ButtonPress-1>", self.on_press)
        self.tray.bind("<B1-Motion>", self.on_move)
        self.tray.bind("<ButtonRelease-1>", self.on_release)
        self.redraw()

    def redraw(self):
        self.tray.delete("all")
        pitch = min(60, 620 // len(PARTS))     # every part fits in the list
        y, self.slots, self.half = 10 + pitch // 2, [], pitch // 2 - 2
        for key, lab, _ in PARTS:
            if key in self.placed:
                continue
            self.tray.create_rectangle(8, y - self.half, 205, y + self.half,
                                       fill="#ffffff", outline="#d3d7dc")
            ART[key](self.tray, 50, y, 0.5 * pitch / 60.0)
            self.tray.create_text(98, y, text=T(*lab), width=104,
                                  font=("Helvetica", 8), anchor="w")
            self.slots.append((key, y))
            y += pitch
        self.paint_scene()

    def paint_scene(self):
        cv = self.scene
        cv.delete("all")
        cv.create_text(380, 20, text=T(*SCENE_TITLE),
                       font=("Helvetica", 10, "bold"), fill="#4a5058")
        cv.create_rectangle(20, 470, 740, 500, fill="#d6d3c8", outline="")
        for key, (cx, cy, w, h) in ZONES.items():
            if key in self.placed:
                continue
            cv.create_rectangle(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2,
                                dash=(4, 3), outline="#b0b5bb")
        for key, _, _ in PARTS:
            if key in self.placed:
                cx, cy, w, h = ZONES[key]
                ART[key](cv, cx, cy, 1.0)
        if len(self.placed) == len(PARTS):
            cv.create_text(380, 610, fill="#14532d",
                           font=("Helvetica", 11, "bold"),
                           text=T("조립 완료 — '실험대' 탭으로 이동하시오.",
                                  "Assembly complete — go to the Bench tab."))

    def on_press(self, ev):
        self.drag = None
        for key, y in self.slots:
            if abs(ev.y - y) <= self.half:
                self.drag = key
                return

    def on_move(self, ev):
        if not self.drag:
            return
        x = self.tray.winfo_rootx() + ev.x - self.scene.winfo_rootx()
        y = self.tray.winfo_rooty() + ev.y - self.scene.winfo_rooty()
        self.paint_scene()
        ART[self.drag](self.scene, x, y, 0.9)

    def on_release(self, ev):
        if not self.drag:
            return
        key, self.drag = self.drag, None
        x = self.tray.winfo_rootx() + ev.x - self.scene.winfo_rootx()
        y = self.tray.winfo_rooty() + ev.y - self.scene.winfo_rooty()
        self.drop(key, x, y)

    def drop(self, key, x, y):
        cx, cy, w, h = ZONES[key]
        self.msg.config(text="")
        if not (abs(x - cx) < w / 2 + 28 and abs(y - cy) < h / 2 + 28):
            self.msg.config(text=T("그 위치에는 놓을 수 없습니다.",
                                   "That part does not belong there."))
            self.redraw()
            return False
        needs = dict((k, n) for k, _, n in PARTS)[key]
        miss = [n for n in needs if n not in self.placed]
        if miss:
            names = ", ".join(T(*dict((k, l) for k, l, _ in PARTS)[m])
                              for m in miss)
            self.msg.config(text=T("먼저 설치해야 합니다: ",
                                   "Install first: ") + names)
            self.redraw()
            return False
        self.placed.add(key)
        self.app.on_assembly_change(self.placed)
        self.redraw()
        return True


# --------------------------------------------------------------------------
#  Data sheet: what the student typed down, nothing more
# --------------------------------------------------------------------------
class DataSheet(ttk.Frame):
    def __init__(self, master, cols, height=12):
        ttk.Frame.__init__(self, master)
        self.cols = cols
        self.tv = ttk.Treeview(self, columns=[c[0] for c in cols],
                               show="headings", height=height)
        for key, head, wd in cols:
            self.tv.heading(key, text=head)
            self.tv.column(key, width=wd, anchor="center")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")

    def add(self, row):
        self.tv.insert("", "end", values=row)
        self.tv.yview_moveto(1.0)

    def del_last(self):
        kids = self.tv.get_children()
        if kids:
            self.tv.delete(kids[-1])

    def clear(self):
        for k in self.tv.get_children():
            self.tv.delete(k)

    def as_text(self):
        out = ["\t".join(c[1] for c in self.cols)]
        for k in self.tv.get_children():
            out.append("\t".join(str(v) for v in self.tv.item(k, "values")))
        return "\n".join(out)


def sheet_buttons(parent, sheet, app):
    row = ttk.Frame(parent)
    row.pack(fill="x", pady=2)
    ttk.Button(row, text=T("마지막 줄 삭제", "Delete last"),
               command=sheet.del_last).pack(side="left", padx=2)
    ttk.Button(row, text=T("모두 지우기", "Clear"),
               command=sheet.clear).pack(side="left", padx=2)

    def copy():
        app.clipboard_clear()
        app.clipboard_append(sheet.as_text())
    ttk.Button(row, text=T("표 복사", "Copy table"),
               command=copy).pack(side="left", padx=2)


def stepper(parent, label, cmds):
    """a row of buttons: label  [−1] [−0.1] … ; cmds = [(text, fn), …]"""
    row = ttk.Frame(parent)
    row.pack(fill="x", pady=1)
    ttk.Label(row, text=label, width=16).pack(side="left")
    for txt, fn in cmds:
        ttk.Button(row, text=txt, width=max(6, len(txt) + 1), command=fn).pack(side="left", padx=1)
    return row


class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.ph = Physics(seed)
        self.title(T(*APP_TITLE))
        self.geometry("1360x800")
        self.placed = set()
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_asm = AssemblyTab(nb, self)
        self.tab_bench = BenchTab(nb, self)
        nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.tab_bench, text=T(" 실험대 ", " Bench "))
        self.after(40, self.tick)

    def on_assembly_change(self, placed):
        self.placed = set(placed)
        self.tab_bench.refresh()

    def tick(self):
        self.tab_bench.tick(0.04)
        self.after(40, self.tick)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
