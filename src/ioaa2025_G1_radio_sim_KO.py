#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  International Olympiad on Astronomy and Astrophysics 2025  (Mumbai)
  Group Competition G01 :  UNCOVERING GALACTIC DARK MATTER
                           USING A RADIO TELESCOPE
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The tools of the problem: a horn radio telescope (aperture 56.5 cm x
    41.5 cm) on an alt-azimuth mount, its azimuth read on a protractor
    (1 deg) and its altitude on a digital inclinometer (0.01 deg), and a
    laptop running the "Radio Astronomy Suite": Tab 1 quick look, Tab 2
    pointing and velocity correction, Tab 3 data acquisition (60 s),
    Tab 4 calibration on the ground and the sky, Tab 5 HI line analysis.
    The sky is computed, not stored: the site is the venue fitted to the
    official pointing table (19.10 N, 72.85 E, IST = UTC+5:30) and the
    clock starts at 20:50:00 IST on 24 July 2025 and runs in real time.
    Every spectrum is the 21-cm line of a model Milky Way seen through
    the horn's beam, Doppler shifted by the Earth's rotation and orbit and
    the Sun's motion, with continuum, ground spill-over, a receiver with
    its own bandpass and noise temperature, radiometer noise and the
    mobile tower the write-up warns about.  Only what the students see is
    shown; --seed N repeats a session.

    Run:   python3 ioaa2025_G1_radio_sim_KO.py   [--seed N]
"""
import math
import random
import sys
import time
import tkinter as tk
from tkinter import ttk, filedialog

APP_VERSION = "1.0"
LANG = "KO"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "KO" else en


SEED = None
if "--seed" in sys.argv:
    try:
        SEED = int(sys.argv[sys.argv.index("--seed") + 1])
    except (IndexError, ValueError):
        SEED = None
RNG = random.Random(SEED)
D2R = math.pi / 180

# ======================================================================
#   TIME AND THE SKY
# ======================================================================
SITE_LAT, SITE_LON, TZ = 19.10, 72.85, 5.5


def _jd0():
    y, m, d, H = 2025, 7, 24, 20 + 50 / 60 - TZ
    if m <= 2:
        y -= 1
        m += 12
    A = y // 100
    B = 2 - A + A // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5 + H / 24


JD0 = _jd0()


class Clock:
    def __init__(self):
        self.t0 = time.time()
        self.extra = 0.0

    def t(self):
        return time.time() - self.t0 + self.extra


CLOCK = Clock()


def jd_now():
    return JD0 + CLOCK.t() / 86400


def ist(t):
    s = int(t) + 20 * 3600 + 50 * 60
    return "%02d:%02d:%02d" % ((s // 3600) % 24, (s // 60) % 60, s % 60)


def gmst(J):
    Tc = (J - 2451545) / 36525
    return (280.46061837 + 360.98564736629 * (J - 2451545) + 0.000387933 * Tc * Tc) % 360


MG = [[-0.0548755604, 0.4941094279, -0.8676661490],
      [-0.8734370902, -0.4448296300, -0.1980763734],
      [-0.4838350155, 0.7469822445, 0.4559837762]]


def mul(M, v):
    return [sum(M[i][k] * v[k] for k in range(3)) for i in range(3)]


def mulT(M, v):
    return [sum(M[k][i] * v[k] for k in range(3)) for i in range(3)]


def sph(lon, lat):
    return [math.cos(lat * D2R) * math.cos(lon * D2R), math.cos(lat * D2R) * math.sin(lon * D2R), math.sin(lat * D2R)]


def unsph(v):
    return (math.atan2(v[1], v[0]) / D2R) % 360, math.asin(max(-1.0, min(1.0, v[2]))) / D2R


def prec_mat(J):
    Tc = (J - 2451545) / 36525
    a = D2R / 3600
    z = (2306.2181 * Tc + 1.09468 * Tc * Tc) * a
    ze = (2306.2181 * Tc + 0.30188 * Tc * Tc) * a
    th = (2004.3109 * Tc - 0.42665 * Tc * Tc) * a
    cz, sz, ce, se, ct, st = math.cos(z), math.sin(z), math.cos(ze), math.sin(ze), math.cos(th), math.sin(th)
    return [[cz * ct * ce - sz * se, -cz * ct * se - sz * ce, -cz * st],
            [sz * ct * ce + cz * se, -sz * ct * se + cz * ce, -sz * st],
            [st * ce, -st * se, ct]]


def gal2hor(l, b, J):
    ra, dec = unsph(mul(prec_mat(J), mul(MG, sph(l, b))))
    H = (gmst(J) + SITE_LON - ra) * D2R
    d, p = dec * D2R, SITE_LAT * D2R
    alt = math.asin(math.sin(p) * math.sin(d) + math.cos(p) * math.cos(d) * math.cos(H))
    az = math.atan2(-math.cos(d) * math.sin(H), math.sin(d) * math.cos(p) - math.cos(d) * math.sin(p) * math.cos(H))
    return alt / D2R, (az / D2R) % 360


def hor2gal(alt, az, J):
    p, a, A = SITE_LAT * D2R, alt * D2R, az * D2R
    d = math.asin(math.sin(p) * math.sin(a) + math.cos(p) * math.cos(a) * math.cos(A))
    H = math.atan2(-math.sin(A) * math.cos(a), math.sin(a) * math.cos(p) - math.cos(a) * math.sin(p) * math.cos(A))
    ra = gmst(J) + SITE_LON - H / D2R
    return unsph(mulT(MG, mulT(prec_mat(J), sph(ra, d / D2R))))


def earth_vel(J):
    def pos(J):
        n = J - 2451545
        L = 280.460 + 0.9856474 * n
        g = (357.528 + 0.9856003 * n) * D2R
        lam = (L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g) + 180) * D2R
        R = 1.00014 - 0.01671 * math.cos(g) - 0.00014 * math.cos(2 * g)
        e = 23.439 * D2R
        return [R * math.cos(lam), R * math.sin(lam) * math.cos(e), R * math.sin(lam) * math.sin(e)]
    a, b = pos(J + 0.01), pos(J - 0.01)
    k = 1.495978707e8 / 86400 / 0.02
    return [(a[i] - b[i]) * k for i in range(3)]


SUN_APEX = sph(270.96, 29.99)


def vcorr(l, b, J):
    """v_LSR = v_obs(Earth) + v_corr"""
    n = mul(MG, sph(l, b))
    ve = earth_vel(J)
    lst = (gmst(J) + SITE_LON) * D2R
    vr = 0.4651 * math.cos(SITE_LAT * D2R)
    V = [ve[0] - vr * math.sin(lst) + 20 * SUN_APEX[0], ve[1] + vr * math.cos(lst) + 20 * SUN_APEX[1], ve[2] + 20 * SUN_APEX[2]]
    return -(n[0] * V[0] + n[1] * V[1] + n[2] * V[2])


# ======================================================================
#   THE MODEL GALAXY
# ======================================================================
R0, V0, TS, SIG = 8.5, 220.0, 120.0, 4.5


def vrot(R):
    return 232.3 * (1 - math.exp(-R / 2.9))


def n_hi(R, z, x, y):
    if R > 22:
        return 0.0
    th = math.atan2(y, x)
    inner = (R / 3) ** 3 if R < 3 else 1.0
    outer = math.exp(-max(0.0, R - 13) / 3)
    arm = 1 + 0.55 * math.cos(2 * (th - math.log(R + 0.1) / math.tan(13 * D2R)))
    h = 0.11 * math.exp((R - 8.5) / 8)
    return 0.62 * inner * outer * arm * 0.12 / h * math.exp(-z * z / (2 * h * h))


VG0, VGN = -200.0, 401
KERN = [math.exp(-0.5 * (i / SIG) ** 2) / (SIG * math.sqrt(2 * math.pi)) for i in range(-24, 25)]


def hi_line(l, b):
    tau = [0.0] * VGN
    cl, sl, cb, sb = math.cos(l * D2R), math.sin(l * D2R), math.cos(b * D2R), math.sin(b * D2R)
    ds, kpc = 0.05, 3.086e21
    s = ds / 2
    while s < 30:
        dp, z = s * cb, s * sb + 0.015
        if abs(z) > 3:
            break
        x, y = R0 - dp * cl, dp * sl
        R = math.hypot(x, y)
        n = n_hi(R, z, x, y)
        if n >= 1e-5:
            v = vrot(R) * (R0 / R) * sl * cb - V0 * sl * cb
            N = n * ds * kpc / (1.823e18 * TS)
            ci = int(round(v - VG0))
            for k in range(-24, 25):
                j = ci + k
                if 0 <= j < VGN:
                    tau[j] += N * KERN[k + 24]
        s += ds
    return [TS * (1 - math.exp(-t)) for t in tau]


def cont_t(l, b):
    L = (l + 180) % 360 - 180
    return 3.3 + 1.2 * math.exp(-abs(b) / 15) + 9 * math.exp(-b * b / 8) * math.exp(-abs(L) / 35)


# ======================================================================
#   THE TELESCOPE AND THE RECEIVER
# ======================================================================
HORN_A, HORN_B, HPBW_A, HPBW_B = 56.5, 41.5, 21.4, 29.2
FC, NB, DF = 1420.0, 512, 0.004
F0, C_KMS = 1420.40575, 299792.458
FREQ = [FC - NB * DF / 2 + (i + 0.5) * DF for i in range(NB)]
_ph, _ph2 = RNG.random() * 6, RNG.random() * 6
GAIN, TRECV = [], []
for _f in FREQ:
    _x = _f - FC
    _roll = 1 / (1 + math.exp((abs(_x) - 0.93) / 0.025))
    GAIN.append(2.4e-3 * (0.86 + 0.10 * math.cos(2 * math.pi * _x / 1.37 + _ph) + 0.04 * math.cos(2 * math.pi * _x / 0.31 + _ph2)) * (0.15 + 0.85 * _roll))
    TRECV.append(107 + 5 * _x + 2.5 * math.sin(2 * math.pi * _x / 1.9 + _ph2) + 25 * (1 - _roll))


class Telescope:
    def __init__(self):
        self.az, self.alt = 180.0, 60.0
        self.az_err, self.alt_err = 0.3 * RNG.gauss(0, 1), 0.05 * RNG.gauss(0, 1)


TEL = Telescope()


def offset_dir(alt, az, x, y):
    a, A = alt * D2R, az * D2R
    f = [math.sin(A) * math.cos(a), math.cos(A) * math.cos(a), math.sin(a)]
    r = [math.cos(A), -math.sin(A), 0.0]
    u = [-math.sin(A) * math.sin(a), -math.cos(A) * math.sin(a), math.cos(a)]
    tx, ty = math.tan(x * D2R), math.tan(y * D2R)
    v = [f[i] + tx * r[i] + ty * u[i] for i in range(3)]
    n = math.sqrt(sum(c * c for c in v))
    e = [c / n for c in v]
    return math.asin(e[2]) / D2R, (math.atan2(e[0], e[1]) / D2R) % 360


BEAM = []
_sa, _sb = HPBW_A / 2.355, HPBW_B / 2.355
for _i in range(-3, 4):
    for _j in range(-3, 4):
        _x, _y = _i * _sa * 0.75, _j * _sb * 0.75
        BEAM.append([_x, _y, math.exp(-0.5 * ((_x / _sa) ** 2 + (_y / _sb) ** 2))])
_W = sum(b[2] for b in BEAM)
for _b in BEAM:
    _b[2] /= _W


def tower_hit(alt, az):
    return min(1.0, (40 - alt) / 15) if alt < 40 and (az < 40 or az > 240) else 0.0


RFI_LINES = [(1419.384, 9, 0.010), (1420.912, 14, 0.006), (1420.536, 4, 0.014)]
_ant_cache = {"key": None, "T": None}


def antenna_t(alt, az, J):
    key = (round(alt, 1), round(az, 1), int(round(J * 1440)))
    if key == _ant_cache["key"]:
        return _ant_cache["T"]
    line = [0.0] * VGN
    cont = ground = 0.0
    for x, y, w in BEAM:
        sa, sz = offset_dir(alt, az, x, y)
        if sa < 0:
            ground += w
            continue
        l, b = hor2gal(sa, sz, J)
        cont += w * (cont_t(l, b) + 2.2 / max(0.15, math.sin(sa * D2R)) * 0.6)
        H = hi_line(l, b)
        for i in range(VGN):
            line[i] += w * H[i]
    l0, b0 = hor2gal(alt, az, J)
    vc = vcorr(l0, b0, J)
    Ta = []
    rfi = tower_hit(alt, az)
    for f in FREQ:
        vl = C_KMS * (F0 - f) / F0 + vc
        c = vl - VG0
        k = int(math.floor(c))
        hv = line[k] * (k + 1 - c) + line[k + 1] * (c - k) if 0 <= k < VGN - 1 else 0.0
        t = cont + hv + ground * 290 + 9.0
        if rfi > 0:
            t += 18 * rfi + sum(A * 8 * rfi * math.exp(-0.5 * ((f - f1) / w) ** 2) for f1, A, w in RFI_LINES)
        Ta.append(t)
    _ant_cache["key"], _ant_cache["T"] = key, Ta
    return Ta


def integrate(t):
    Ta = antenna_t(TEL.alt + TEL.alt_err, TEL.az + TEL.az_err, jd_now())
    P = []
    for i in range(NB):
        Tsys = Ta[i] + TRECV[i]
        s = Tsys / math.sqrt(DF * 1e6 * t)
        P.append(GAIN[i] * (Tsys + s * RNG.gauss(0, 1)) * (1.6 if i == NB // 2 else 1.0))
    return P


def poly_fit(x, y, use, deg):
    n = deg + 1
    A = [[0.0] * n for _ in range(n)]
    bb = [0.0] * n
    xm, xs = (x[0] + x[-1]) / 2, (x[-1] - x[0]) / 2
    for i in range(len(x)):
        if not use(i):
            continue
        t = (x[i] - xm) / xs
        p = [t ** k for k in range(n)]
        for r in range(n):
            bb[r] += p[r] * y[i]
            for c in range(n):
                A[r][c] += p[r] * p[c]
    for c in range(n):
        pv = max(range(c, n), key=lambda r: abs(A[r][c]))
        A[c], A[pv] = A[pv], A[c]
        bb[c], bb[pv] = bb[pv], bb[c]
        for r in range(n):
            if r != c:
                f = A[r][c] / A[c][c]
                for k in range(c, n):
                    A[r][k] -= f * A[c][k]
                bb[r] -= f * bb[c]
    co = [bb[i] / A[i][i] for i in range(n)]
    return [sum(co[k] * ((xx - xm) / xs) ** k for k in range(n)) for xx in x]


# ======================================================================
#   A PLOT ON A CANVAS
# ======================================================================
class Plot:
    def __init__(self, master, w, h, xl, yl, cross=False, on_click=None):
        self.c = tk.Canvas(master, width=w, height=h, bg="white", highlightthickness=1, highlightbackground="#cfd6de")
        self.w, self.h, self.xl, self.yl = w, h, xl, yl
        self.series, self.mask, self.mark = [], None, None
        self.zoom = None
        self.on_click = on_click
        self.xr = self.yr = None
        if cross:
            self.c.bind("<Motion>", self._cross)
            self.c.bind("<MouseWheel>", self._wheel)
            self.c.bind("<Button-4>", lambda e: self._wheel(e, 1))
            self.c.bind("<Button-5>", lambda e: self._wheel(e, -1))
        if on_click:
            self.c.bind("<Button-1>", self._click)

    def X(self, x):
        return 60 + (x - self.xr[0]) / (self.xr[1] - self.xr[0]) * (self.w - 75)

    def Y(self, y):
        return self.h - 36 - (y - self.yr[0]) / (self.yr[1] - self.yr[0]) * (self.h - 50)

    def inv(self, px, py):
        return (self.xr[0] + (px - 60) / (self.w - 75) * (self.xr[1] - self.xr[0]),
                self.yr[0] + (self.h - 36 - py) / (self.h - 50) * (self.yr[1] - self.yr[0]))

    def draw(self):
        c = self.c
        c.delete("all")
        pts = [(x, y) for s in self.series for x, y in zip(s["x"], s["y"]) if y == y]
        if not pts:
            return
        xa, xb = (self.zoom if self.zoom else (min(p[0] for p in pts), max(p[0] for p in pts)))
        ys = [p[1] for p in pts if xa <= p[0] <= xb] or [0, 1]
        ya, yb = min(ys), max(ys)
        pad = (yb - ya) * 0.06 or 1
        self.xr, self.yr = (xa, xb), (ya - pad, yb + pad)
        x0, x1, y0, y1 = 60, self.w - 15, 14, self.h - 36
        c.create_rectangle(x0, y0, x1, y1, outline="#55606b")

        def nice(a, b, n):
            r = (b - a) / n
            p = 10 ** math.floor(math.log10(r))
            m = r / p
            return (1 if m < 1.5 else 2 if m < 3.5 else 5 if m < 7.5 else 10) * p
        sx, sy = nice(*self.xr, 6), nice(*self.yr, 5)
        x = math.ceil(self.xr[0] / sx) * sx
        while x <= self.xr[1]:
            c.create_line(self.X(x), y0, self.X(x), y1, fill="#e6eaee")
            c.create_text(self.X(x), y1 + 10, text=("%.2f" % x if sx < 0.1 else "%.1f" % x), font=("Arial", 8), fill="#55606b")
            x += sx
        y = math.ceil(self.yr[0] / sy) * sy
        while y <= self.yr[1]:
            c.create_line(x0, self.Y(y), x1, self.Y(y), fill="#e6eaee")
            c.create_text(x0 - 4, self.Y(y), text=("%.3g" % y), anchor="e", font=("Arial", 8), fill="#55606b")
            y += sy
        c.create_text((x0 + x1) / 2, self.h - 8, text=self.xl, font=("Arial", 9), fill="#55606b")
        c.create_text(12, (y0 + y1) / 2, text=self.yl, angle=90, font=("Arial", 9), fill="#55606b")
        if self.mask:
            a, b = sorted(self.mask)
            c.create_rectangle(self.X(a), y0, self.X(b), y1, fill="#d0d0d0", outline="")
        elif self.mark is not None:
            c.create_line(self.X(self.mark), y0, self.X(self.mark), y1, fill="#888", dash=(3, 3))
        for s in self.series:
            seg = []
            for xx, yy in zip(s["x"], s["y"]):
                if yy != yy or not (self.xr[0] <= xx <= self.xr[1]):
                    if len(seg) > 3:
                        c.create_line(*seg, fill=s["col"], width=s.get("lw", 1), dash=s.get("dash"))
                    seg = []
                    continue
                seg += [self.X(xx), self.Y(yy)]
            if len(seg) > 3:
                c.create_line(*seg, fill=s["col"], width=s.get("lw", 1), dash=s.get("dash"))

    def _cross(self, e):
        if not self.xr:
            return
        self.c.delete("cross")
        if 60 <= e.x <= self.w - 15 and 14 <= e.y <= self.h - 36:
            f, t = self.inv(e.x, e.y)
            self.c.create_line(e.x, 14, e.x, self.h - 36, fill="#c83232", tags="cross")
            self.c.create_line(60, e.y, self.w - 15, e.y, fill="#c83232", tags="cross")
            self.c.create_text(66, 24, anchor="w", text="f = %.4f MHz   T = %.2f K" % (f, t), fill="#b3372f", font=("Consolas", 10), tags="cross")

    def _wheel(self, e, d=None):
        if not self.xr:
            return
        d = d if d is not None else (1 if e.delta > 0 else -1)
        xm = self.inv(e.x, e.y)[0]
        f = 0.8 if d > 0 else 1.25
        self.zoom = (xm - (xm - self.xr[0]) * f, xm + (self.xr[1] - xm) * f)
        self.draw()

    def _click(self, e):
        if self.xr:
            self.on_click(self.inv(e.x, e.y)[0])


# ======================================================================
#   THE APPLICATION
# ======================================================================
class App:
    def __init__(self, root):
        self.root = root
        root.title(T("IOAA 2025 그룹 경기 — 전파망원경으로 찾는 암흑물질 · HaslaLab", "IOAA 2025 Group Competition — Dark matter with a radio telescope · HaslaLab"))
        root.configure(bg="#1c2027")
        self.files, self.quick, self.rec, self.cal, self.cin = {}, None, None, None, {}
        self.tape_ang, self.tape = 0, [-36.0, -26.0, 20.0]
        left = tk.Frame(root, bg="#1c2027")
        left.pack(side="left", fill="y", padx=8, pady=8)
        self.clk = tk.Label(left, font=("Consolas", 22, "bold"), bg="#12161b", fg="#e8eef2", width=12)
        self.clk.pack(pady=(0, 6))
        tk.Label(left, text=T("방위각 각도기 (끌기 / 휠)", "Azimuth protractor (drag / wheel)"), bg="#1c2027", fg="#f2c14e").pack()
        self.dial = tk.Canvas(left, width=300, height=300, bg="#6e5236", highlightthickness=0)
        self.dial.pack()
        self.dial.bind("<B1-Motion>", self._dial_drag)
        self.dial.bind("<Button-1>", self._dial_drag)
        for ev, d in (("<MouseWheel>", None), ("<Button-4>", 1), ("<Button-5>", -1)):
            self.dial.bind(ev, lambda e, d=d: self._wheel_az(e, d))
        tk.Label(left, text=T("디지털 경사계 (위아래 끌기 / 휠)", "Digital inclinometer (drag up/down / wheel)"), bg="#1c2027", fg="#f2c14e").pack(pady=(8, 0))
        self.incl = tk.Canvas(left, width=300, height=150, bg="#0e1522", highlightthickness=0)
        self.incl.pack()
        self.incl.bind("<Button-1>", lambda e: setattr(self, "_iy", (e.y, TEL.alt)))
        self.incl.bind("<B1-Motion>", self._incl_drag)
        for ev, d in (("<MouseWheel>", None), ("<Button-4>", 1), ("<Button-5>", -1)):
            self.incl.bind(ev, lambda e, d=d: self._wheel_alt(e, d))
        tk.Label(left, text=T("혼 입구와 줄자 (고리 / 몸통 끌기)", "Horn mouth and tape (drag hook / case)"), bg="#1c2027", fg="#f2c14e").pack(pady=(8, 0))
        self.mouth = tk.Canvas(left, width=300, height=230, bg="#0e1522", highlightthickness=0)
        self.mouth.pack()
        self.mouth.bind("<Button-1>", self._tape_down)
        self.mouth.bind("<B1-Motion>", self._tape_drag)
        tk.Button(left, text=T("줄자 돌리기", "Turn the tape"), command=self._turn).pack(fill="x", pady=3)
        self.warn = tk.Label(left, text="", bg="#1c2027", fg="#f0a79f", wraplength=300, justify="left")
        self.warn.pack(fill="x")
        right = tk.Frame(root, bg="#e9edf2")
        right.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)
        tk.Label(right, text="Radio Astronomy Suite", bg="#2c3e50", fg="white", anchor="w").pack(fill="x")
        self.nb = ttk.Notebook(right)
        self.nb.pack(fill="both", expand=True)
        self._tabs()
        self.folder = tk.Label(right, text="", bg="#2c3e50", fg="#cfd6de", anchor="w")
        self.folder.pack(fill="x")
        self.tick()

    # ---- the instruments --------------------------------------------------
    def _dial_drag(self, e):
        TEL.az = (math.degrees(math.atan2(e.x - 150, 150 - e.y))) % 360

    def _wheel_az(self, e, d):
        d = d if d is not None else (1 if e.delta > 0 else -1)
        TEL.az = (TEL.az + 0.2 * d) % 360

    def _incl_drag(self, e):
        y0, a0 = getattr(self, "_iy", (e.y, TEL.alt))
        TEL.alt = max(-90.0, min(90.0, a0 - (e.y - y0) * 0.1))

    def _wheel_alt(self, e, d):
        d = d if d is not None else (1 if e.delta > 0 else -1)
        TEL.alt = max(-90.0, min(90.0, TEL.alt + 0.05 * d))

    def _turn(self):
        self.tape_ang = 0 if self.tape_ang else 90

    def _tape_xy(self, s):
        k, x0, y0 = 4.4, self.tape[0], self.tape[1]
        a = self.tape_ang * D2R
        return 150 + (x0 + math.cos(a) * s) * k, 115 - (y0 + math.sin(a) * s) * k

    def _tape_down(self, e):
        hx, hy = self._tape_xy(0)
        cx, cy = self._tape_xy(self.tape[2] + 3.5)
        self._grab = ("hook" if math.hypot(e.x - hx, e.y - hy) < 12 else "case" if math.hypot(e.x - cx, e.y - cy) < 18 else None, e.x, e.y, list(self.tape))

    def _tape_drag(self, e):
        g = getattr(self, "_grab", None)
        if not g or not g[0]:
            return
        dx, dy = (e.x - g[1]) / 4.4, -(e.y - g[2]) / 4.4
        if g[0] == "hook":
            self.tape[0], self.tape[1] = g[3][0] + dx, g[3][1] + dy
        else:
            a = self.tape_ang * D2R
            self.tape[2] = max(3.0, min(70.0, g[3][2] + dx * math.cos(a) + dy * math.sin(a)))

    def draw_instruments(self):
        c = self.dial
        c.delete("all")
        R, k = 135, 135 / 27
        c.create_oval(150 - R, 150 - R, 150 + R, 150 + R, fill="#f3f0e4")
        for d in range(360):
            t = d * D2R
            L = 2.6 if d % 10 == 0 else 1.8 if d % 5 == 0 else 1.1
            c.create_line(150 + (R - 2) * math.sin(t), 150 - (R - 2) * math.cos(t), 150 + (R - 2 - L * k) * math.sin(t), 150 - (R - 2 - L * k) * math.cos(t), fill="#1d1d1d")
            if d % 10 == 0:
                c.create_text(150 + (R - 22) * math.sin(t), 150 - (R - 22) * math.cos(t), text=str(d), font=("Arial", 7, "bold"), angle=-d)
        c.create_oval(150 - 19 * k, 150 - 19 * k, 150 + 19 * k, 150 + 19 * k, fill="#2b2e33", outline="#454a51")
        c.create_polygon(146, 8, 154, 8, 150, 15, fill="#b22222")
        a = TEL.az * D2R
        c.create_line(150 + 19 * k * math.sin(a), 150 - 19 * k * math.cos(a), 150 + (R - 2) * math.sin(a), 150 - (R - 2) * math.cos(a), fill="#c62828", width=4)
        c.create_line(150 + 19 * k * math.sin(a), 150 - 19 * k * math.cos(a), 150 + (R - 2) * math.sin(a), 150 - (R - 2) * math.cos(a), fill="#111", width=1)
        c = self.incl
        c.delete("all")
        c.create_rectangle(80, 20, 290, 130, fill="#f2c14e", outline="#9a7a1d", width=2)
        c.create_rectangle(92, 32, 278, 104, fill="#b9c7a3")
        c.create_text(270, 68, anchor="e", text="%.2f°" % TEL.alt, font=("Consolas", 26, "bold"), fill="#1b2014")
        c.create_text(185, 117, text="DIGITAL LEVEL · ANGLE", font=("Arial", 8, "bold"), fill="#3b3214")
        t = TEL.alt * D2R
        c.create_line(40 - 30 * math.cos(t), 80 + 30 * math.sin(t), 40 + 30 * math.cos(t), 80 - 30 * math.sin(t), fill="#c3c8cd", width=6)
        c = self.mouth
        c.delete("all")
        k = 4.4
        c.create_rectangle(150 - 28.85 * k, 115 - 21.35 * k, 150 + 28.85 * k, 115 + 21.35 * k, fill="#d9dde1", outline="")
        c.create_rectangle(150 - 28.25 * k, 115 - 20.75 * k, 150 + 28.25 * k, 115 + 20.75 * k, fill="#59606a", outline="")
        c.create_rectangle(150 - 8.25 * k, 115 - 4.15 * k, 150 + 8.25 * k, 115 + 4.15 * k, fill="#23272d", outline="")
        x0, y0 = self._tape_xy(0)
        x1, y1 = self._tape_xy(self.tape[2])
        c.create_line(x0, y0, x1, y1, fill="#f2cf2e", width=9)
        a = self.tape_ang * D2R
        for mm in range(int(self.tape[2] * 10) + 1):
            if mm % 5:
                continue
            px, py = self._tape_xy(mm / 10)
            L = 4 if mm % 10 else 7
            nx, ny = -math.sin(a), -math.cos(a)
            c.create_line(px, py, px + nx * L, py + ny * L, fill="#1b1b1b")
            if mm % 50 == 0 and mm:
                c.create_text(px - nx * 3, py - ny * 3, text=str(mm // 10), font=("Arial", 6), fill="#1b1b1b")
        cx, cy = self._tape_xy(self.tape[2] + 3.5)
        c.create_rectangle(cx - 14, cy - 14, cx + 14, cy + 14, fill="#c62828", outline="")

    # ---- the suite ----------------------------------------------------------
    def _tabs(self):
        self.pg = []
        names = ["1 · Quick Look", T("2 · 지향과 속도 보정", "2 · Pointing & velocity correction"), T("3 · 데이터 수집", "3 · Data acquisition"),
                 T("4 · 보정", "4 · Calibration"), T("5 · HI 선 분석", "5 · HI line analysis"), "HI Line Temperature"]
        for n in names:
            f = tk.Frame(self.nb, bg="white")
            self.nb.add(f, text=n)
            self.pg.append(f)
        fq = T("진동수 (MHz)", "Frequency (MHz)")
        p = self.pg[0]
        tk.Label(p, text=T("망원경을 하늘로, 그다음 땅으로 돌려 신호 크기가 바뀌는지 보세요. 데이터는 저장되지 않습니다.",
                           "Point the telescope at the sky, then at the ground, and watch the signal change. Nothing is saved."), bg="white").pack(anchor="w")
        b = tk.Frame(p, bg="white")
        b.pack(anchor="w")
        tk.Button(b, text=T("시작 (60 s)", "Start (60 s)"), command=lambda: setattr(self, "quick", [CLOCK.t(), -1])).pack(side="left")
        tk.Button(b, text=T("멈춤", "Stop"), command=lambda: setattr(self, "quick", None)).pack(side="left")
        self.qT = tk.Label(b, text="", bg="white")
        self.qT.pack(side="left")
        self.pq = Plot(p, 760, 330, fq, T("상대 출력", "Relative power"))
        self.pq.c.pack()
        p = self.pg[1]
        r = tk.Frame(p, bg="white")
        r.pack(anchor="w", pady=4)
        tk.Label(r, text=T("은경 ℓ (°)", "Galactic longitude ℓ (°)"), bg="white").pack(side="left")
        self.el = tk.Entry(r, width=8)
        self.el.insert(0, "30")
        self.el.pack(side="left")
        tk.Label(r, text=T("  은위 b (°)", "  Galactic latitude b (°)"), bg="white").pack(side="left")
        self.eb = tk.Entry(r, width=8)
        self.eb.insert(0, "0")
        self.eb.pack(side="left")
        tk.Button(r, text=T("계산", "Calculate"), command=self._calc).pack(side="left", padx=6)
        self.pt = tk.Label(p, text="", bg="white", justify="left", font=("Consolas", 11))
        self.pt.pack(anchor="w", padx=6)
        p = self.pg[2]
        b = tk.Frame(p, bg="white")
        b.pack(anchor="w")
        tk.Button(b, text="Record Data", command=self._rec).pack(side="left")
        tk.Button(b, text="Stop Recording", command=self._stoprec).pack(side="left")
        tk.Button(b, text="Clear Plot", command=self._clearrec).pack(side="left")
        self.rT = tk.Label(b, text="", bg="white")
        self.rT.pack(side="left", padx=6)
        self.pr = Plot(p, 760, 330, fq, T("상대 출력", "Relative power"))
        self.pr.c.pack()
        self.sv = tk.Frame(p, bg="white")
        self.sv.pack(anchor="w")
        p = self.pg[3]
        b = tk.Frame(p, bg="white")
        b.pack(anchor="w")
        self.cg, self.cs = tk.StringVar(), tk.StringVar()
        tk.Button(b, text="Load ground", command=lambda: self._load_cal("g")).pack(side="left")
        self.og = ttk.Combobox(b, textvariable=self.cg, width=12, state="readonly")
        self.og.pack(side="left")
        tk.Button(b, text="Load sky", command=lambda: self._load_cal("s")).pack(side="left")
        self.os = ttk.Combobox(b, textvariable=self.cs, width=12, state="readonly")
        self.os.pack(side="left")
        tk.Button(b, text="Calibrate gain and obtain T_recv", command=self._calib).pack(side="left", padx=4)
        tk.Label(p, text=T("오른쪽 그림에서 섞여 든 HI 선의 양쪽을 차례로 클릭해 가릴 구간을 정하세요.",
                           "On the right-hand plot click on either side of the contaminating HI line to mask it."), bg="white").pack(anchor="w")
        b2 = tk.Frame(p, bg="white")
        b2.pack()
        self.pc1 = Plot(b2, 380, 300, fq, T("상대 출력", "Relative power"))
        self.pc1.c.pack(side="left")
        self.pc2 = Plot(b2, 380, 300, fq, "T_recv (K)", on_click=self._mask_click)
        self.pc2.c.pack(side="left")
        self.cT = tk.Label(p, text="", bg="white")
        self.cT.pack(anchor="w")
        p = self.pg[4]
        b = tk.Frame(p, bg="white")
        b.pack(anchor="w")
        self.ls = tk.StringVar()
        self.ol = ttk.Combobox(b, textvariable=self.ls, width=14, state="readonly")
        self.ol.pack(side="left")
        tk.Button(b, text=T("불러오기", "Load"), command=self._load_line).pack(side="left")
        tk.Button(b, text="Line temperature profile", command=self._line).pack(side="left")
        tk.Button(b, text=T("CSV 내보내기", "Export CSV"), command=self._export).pack(side="left", padx=8)
        self.lT = tk.Label(b, text="", bg="white", fg="#b3372f")
        self.lT.pack(side="left")
        self.pl = Plot(p, 760, 330, fq, T("상대 출력", "Relative power"))
        self.pl.c.pack()
        p = self.pg[5]
        self.hT = tk.Label(p, text=T("(5번 탭에서 파일을 불러오고 Line temperature profile을 누르세요)", "(load a file in Tab 5 and press Line temperature profile)"), bg="white")
        self.hT.pack(anchor="w")
        self.ph = Plot(p, 760, 360, fq, T("온도 (K)", "Temperature (K)"), cross=True)
        self.ph.c.pack()
        tk.Button(p, text=T("확대 초기화 (휠: 확대)", "Reset zoom (wheel: zoom)"), command=lambda: (setattr(self.ph, "zoom", None), self.ph.draw())).pack(anchor="w")

    def _calc(self):
        try:
            l, b = float(self.el.get()), float(self.eb.get())
        except ValueError:
            return
        J = jd_now()
        alt, az = gal2hor(l, b, J)
        self.pt.config(text="%s  2025-07-24\n%s  %s IST\nℓ, b  %.2f°, %.2f°\n%s  %.2f°\n%s  %.2f°\nv_corr  %.3f km/s" % (
            T("날짜", "Date"), T("시각", "Time"), ist(CLOCK.t()), l, b, T("고도", "Altitude"), alt, T("방위각", "Azimuth"), az, vcorr(l, b, J)))

    def _rec(self):
        if self.rec and self.rec["run"]:
            return
        self.rec = {"run": True, "t0": CLOCK.t(), "n": 0, "acc": [0.0] * NB, "last": int(CLOCK.t())}
        for w in self.sv.winfo_children():
            w.destroy()

    def _stoprec(self):
        self.rec = None
        self.pr.series = []
        self.pr.draw()
        self.rT.config(text="")

    def _clearrec(self):
        if self.rec and self.rec["run"]:
            return
        self._stoprec()

    def _save_dialog(self):
        tk.Label(self.sv, text=T("다른 이름으로 저장 — 파일 이름:", "Save as — file name:"), bg="white").pack(side="left")
        e = tk.Entry(self.sv, width=16)
        e.pack(side="left")
        e.focus_set()

        def go(*_):
            n = e.get().strip()
            if not n:
                return
            if not n.lower().endswith(".csv"):
                n += ".csv"
            self.files[n] = self.rec["done"]
            self.rec = None
            for w in self.sv.winfo_children():
                w.destroy()
            tk.Label(self.sv, text=n + T(" — 저장됨", " — saved"), bg="white").pack()
            self._refresh_files()
        e.bind("<Return>", go)
        tk.Button(self.sv, text=T("저장", "Save"), command=go).pack(side="left")

    def _refresh_files(self):
        names = list(self.files)
        for cb in (self.og, self.os, self.ol):
            cb["values"] = names
        if "ground.csv" in names:
            self.cg.set("ground.csv")
        if "sky.csv" in names:
            self.cs.set("sky.csv")
        self.folder.config(text="📁 G07: " + (", ".join(names) if names else T("폴더가 비어 있습니다", "the folder is empty")))

    def _load_cal(self, which):
        n = self.cg.get() if which == "g" else self.cs.get()
        if n in self.files:
            self.cin[which] = n
            self.cin.pop("Tr", None)
            self.cin.pop("mask", None)
            self.cal = None
            self._draw_cal()

    def _calib(self):
        if "g" not in self.cin or "s" not in self.cin:
            return
        G, S = self.files[self.cin["g"]]["P"], self.files[self.cin["s"]]["P"]
        self.cin["gain"] = [(g - s) / 295.0 for g, s in zip(G, S)]
        self.cin["Tr"] = [s / gn - 5 for s, gn in zip(S, self.cin["gain"])]
        self.cin.pop("mask", None)
        self.cin["A"] = None
        self.cal = None
        self._draw_cal()

    def _mask_click(self, f):
        if "Tr" not in self.cin:
            return
        if self.cin.get("A") is None or self.cin.get("mask"):
            self.cin["A"], self.cin["mask"], self.cal = f, None, None
        else:
            self.cin["mask"] = (self.cin["A"], f)
            self.cin["A"] = None
            lo, hi = sorted(self.cin["mask"])
            Trf = poly_fit(FREQ, self.cin["Tr"], lambda i: abs(FREQ[i] - FC) < 0.9 and not (lo <= FREQ[i] <= hi) and i != NB // 2, 8)
            self.cal = {"gain": self.cin["gain"], "Trf": Trf}
        self._draw_cal()

    def _draw_cal(self):
        self.pc1.series = []
        if "g" in self.cin:
            self.pc1.series.append({"x": FREQ, "y": self.files[self.cin["g"]]["P"], "col": "#8c564b"})
        if "s" in self.cin:
            self.pc1.series.append({"x": FREQ, "y": self.files[self.cin["s"]]["P"], "col": "#1f77b4"})
        self.pc2.series, self.pc2.mask, self.pc2.mark = [], self.cin.get("mask"), self.cin.get("A")
        if "Tr" in self.cin:
            self.pc2.series.append({"x": FREQ, "y": [v if abs(f - FC) < 0.97 else float("nan") for f, v in zip(FREQ, self.cin["Tr"])], "col": "#1f77b4"})
        if self.cal:
            self.pc2.series.append({"x": FREQ, "y": [v if abs(f - FC) < 0.93 else float("nan") for f, v in zip(FREQ, self.cal["Trf"])], "col": "#2ca02c", "dash": (6, 4), "lw": 2})
            mid = sorted(self.cal["Trf"][100:412])[156]
            self.cT.config(text=T("보정 완료", "calibration done") + " — T_recv ≈ %.1f K (median), T_sys = T_recv + 5 K ≈ %.1f K" % (mid, mid + 5))
        else:
            self.cT.config(text="")
        self.pc1.draw()
        self.pc2.draw()

    def _load_line(self):
        n = self.ls.get()
        if n in self.files:
            self.loaded = n
            self.pl.series = [{"x": FREQ, "y": self.files[n]["P"], "col": "#1f77b4"}]
            self.pl.draw()
            self.lT.config(text="")

    def _line(self):
        if not getattr(self, "loaded", None):
            return
        if not self.cal:
            self.lT.config(text=T("먼저 4번 탭에서 보정하세요.", "Calibrate in Tab 4 first."))
            return
        P, K = self.files[self.loaded]["P"], self.cal
        Tl = [p / K["gain"][i] - K["Trf"][i] - 5 if abs(FREQ[i] - FC) <= 0.93 else float("nan") for i, p in enumerate(P)]
        self.ph.series = [{"x": FREQ, "y": Tl, "col": "#1f77b4"}, {"x": [FREQ[0], FREQ[-1]], "y": [0, 0], "col": "#888", "dash": (4, 4)}]
        self.ph.zoom = None
        self.hT.config(text=self.loaded + " — HI Line Temperature")
        self.nb.select(5)
        self.root.after(50, self.ph.draw)

    def _export(self):
        n = getattr(self, "loaded", None)
        if not n:
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=n)
        if path:
            F = self.files[n]
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("# Radio Astronomy Suite — %s, recorded 2025-07-24 %s IST, 60 s\nfreq_MHz,relative_power\n" % (n, ist(F["t"])))
                for f, p in zip(FREQ, F["P"]):
                    fh.write("%.4f,%.6e\n" % (f, p))

    # ---- the clock ---------------------------------------------------------
    def tick(self):
        now = CLOCK.t()
        self.clk.config(text=ist(now))
        self.draw_instruments()
        self.warn.config(text=T("기지국 방향(고도 40° 아래, 방위각 0°–40° 또는 240°–360°)을 겨누고 있습니다", "The horn points towards the mobile tower (below 40°, azimuth 0°–40° or 240°–360°).") if tower_hit(TEL.alt, TEL.az) > 0 else "")
        if self.quick:
            s = int(now - self.quick[0])
            if s != self.quick[1]:
                self.quick[1] = s
                self.pq.series = [{"x": FREQ, "y": integrate(1), "col": "#1f77b4"}]
                self.pq.draw()
                self.qT.config(text="%d s" % max(0, 60 - s))
            if s >= 60:
                self.quick = None
        R = self.rec
        if R and R["run"]:
            while R["last"] < int(now) and R["n"] < 60:
                R["last"] += 1
                P = integrate(1)
                R["acc"] = [a + p for a, p in zip(R["acc"], P)]
                R["n"] += 1
            self.pr.series = [{"x": FREQ, "y": [a / max(1, R["n"]) for a in R["acc"]], "col": "#1f77b4"}]
            self.pr.draw()
            self.rT.config(text=T("적분 중 ", "integrating ") + "%d / 60 s" % R["n"])
            if R["n"] >= 60:
                R["run"] = False
                R["done"] = {"P": [a / 60 for a in R["acc"]], "t": R["t0"] + 30}
                self._save_dialog()
        self.root.after(250, self.tick)


def main():
    root = tk.Tk()
    root.geometry("1200x960")
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
