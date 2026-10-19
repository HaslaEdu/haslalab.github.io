#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  2nd European Physics Olympiad  (EuPhO 2018, Dolgoprudny, Russia)
  Experimental Problem :  POROUS MEMBRANE  (anodic aluminium oxide)
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

    A  Diffusion      ->  the characteristic time tau
    B  Interference   ->  the membrane thickness h
    C  Birefringence  ->  dn = |ne - no|  ->  the porosity p
    D  Coda           ->  the channel diameter d

Design rule (non-negotiable):
    Apparatus after the problem sheet: the airproof vessel behind the
    membrane window with its two clamped tubes and lid, the NDIR CO2
    sensor with its power bank, two fans with a battery block, and the
    optical bench with the 660 nm laser, two polarisers, the rotary table
    holding the membrane, the swing arm with the photodiode and the
    microammeter.  CO2 leaves the vessel by Knudsen diffusion through the
    pores; the film reflects as a partially coherent etalon and retards
    the two eigenwaves exactly.
    Only what a real instrument shows is displayed: the sensor's LCD and
    its record memory, the scales of the table, the arm and the
    polarisers, and the microammeter.  No fit or derived value is ever
    computed.  The sample is randomised for each session; --reference
    gives the sample that reproduces the official answers.

    Run:   python3 eupho2018_E1_sim_EN.py   [--seed N] [--reference]
"""
import math
import random
import time
import bisect

# ----------------------------------------------------------------------------
#  Language: the KO and EN editions differ only in the LANG line.
# ----------------------------------------------------------------------------
LANG = "EN"          # the KO edition differs only in this line


def T(ko, en):
    return ko if LANG == "KO" else en


APP_TITLE = T("EuPhO 2018 실험 — 다공성 막", "EuPhO 2018 Experiment — Porous Membrane")

# ----------------------------------------------------------------------------
#  Physical constants
# ----------------------------------------------------------------------------
R_GAS = 8.314462618           # J/(mol K)
M_CO2 = 44.0e-3               # kg/mol
LAMBDA = 660e-9               # m, laser wavelength
N_ORD = 1.50                  # ordinary index of the membrane (given)
D_WINDOW = 13.0e-3            # m, membrane window diameter (given)
D_CO2_AIR = 1.60e-5           # m^2/s, free diffusion of CO2 in air (external film)

S0_WINDOW = math.pi / 4.0 * D_WINDOW ** 2      # 1.327e-4 m^2


def mean_speed(T_kelvin, M=M_CO2):
    """Maxwell mean molecular speed  <v> = sqrt(8RT/pi M).

    Kinetic theory of Knudsen (free-molecular) diffusion uses the MEAN speed,
    D_K = (1/3) <v> d.  The EuPhO problem sheet calls v the 'root-mean-square'
    speed, but the official solution evaluates sqrt(8RT/pi mu) = 376 m/s, i.e.
    the mean speed.  See README, erratum A-1.  We follow kinetic theory.
    """
    return math.sqrt(8.0 * R_GAS * T_kelvin / (math.pi * M))


def rms_speed(T_kelvin, M=M_CO2):
    return math.sqrt(3.0 * R_GAS * T_kelvin / M)


# ----------------------------------------------------------------------------
#  dn(p) --- the calibration curve printed on the problem sheet.
#  Digitised from the EuPhO 2018 problem sheet plot (0 <= p <= 0.50).
#  This *is* the ground truth of the sample family: the porosity of every
#  simulated membrane is mapped to its birefringence through this same curve,
#  so a student reading the printed plot recovers a self-consistent p.
# ----------------------------------------------------------------------------
_DN_P = [0.000, 0.025, 0.050, 0.075, 0.100, 0.125, 0.150, 0.175, 0.200,
         0.225, 0.250, 0.275, 0.300, 0.325, 0.350, 0.375, 0.400, 0.425,
         0.450, 0.475, 0.500]
_DN_V = [0.0000, 0.0080, 0.0157, 0.0228, 0.0295, 0.0357, 0.0415, 0.0472,
         0.0530, 0.0585, 0.0637, 0.0682, 0.0722, 0.0762, 0.0800, 0.0832,
         0.0857, 0.0878, 0.0895, 0.0909, 0.0920]


def _fritsch_carlson(xs, ys):
    """Monotone cubic Hermite tangents (Fritsch-Carlson)."""
    n = len(xs)
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [0.0] * n
    m[0] = d[0]
    m[-1] = d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            m[i] = (d[i - 1] + d[i]) / 2.0
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
            continue
        a, b = m[i] / d[i], m[i + 1] / d[i]
        s = a * a + b * b
        if s > 9.0:
            t = 3.0 / math.sqrt(s)
            m[i] = t * a * d[i]
            m[i + 1] = t * b * d[i]
    return m


_DN_M = _fritsch_carlson(_DN_P, _DN_V)


def dn_of_p(p):
    """Birefringence dn = |ne - no| of an AAO membrane of porosity p."""
    p = max(_DN_P[0], min(_DN_P[-1], p))
    i = bisect.bisect_right(_DN_P, p) - 1
    i = max(0, min(len(_DN_P) - 2, i))
    x0, x1 = _DN_P[i], _DN_P[i + 1]
    y0, y1 = _DN_V[i], _DN_V[i + 1]
    m0, m1 = _DN_M[i], _DN_M[i + 1]
    hh = x1 - x0
    t = (p - x0) / hh
    t2, t3 = t * t, t * t * t
    return ((2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * hh * m0 +
            (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * hh * m1)


def p_of_dn(dn):
    """Inverse of dn(p) -- exactly what a student does by reading the plot."""
    lo, hi = 0.0, 0.50
    if dn <= 0:
        return 0.0
    if dn >= _DN_V[-1]:
        return 0.50
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if dn_of_p(mid) < dn:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ----------------------------------------------------------------------------
#  Hidden truth --- randomised per session with a seeded RNG.
# ----------------------------------------------------------------------------
class Truth:
    """Everything the student is supposed to find out.  Never exposed."""

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1, 10 ** 9)
        self.seed = int(seed)
        rng = random.Random(self.seed)
        self.rng = rng

        # --- reference sample reproduces the official EuPhO 2018 answers ----
        if self.seed == 20180001:
            self.h = 74.60e-6
            self.p = 0.1405
            self.d = 5.689e-9
            self.T = 295.0
            self.L_vessel = 5.00e-2
            self.D_vessel = 7.40e-2
            self.c_amb = 0.0500
        else:
            self.h = rng.uniform(48.0, 108.0) * 1e-6            # m
            self.p = rng.uniform(0.085, 0.235)                  # -
            self.d = rng.uniform(4.2, 9.2) * 1e-9               # m
            self.T = rng.uniform(290.5, 299.5)                  # K
            self.L_vessel = rng.uniform(4.4, 5.8) * 1e-2        # m
            self.D_vessel = rng.uniform(6.8, 8.0) * 1e-2        # m
            self.c_amb = rng.uniform(0.042, 0.060)              # %

        self.dn = dn_of_p(self.p)
        self.n_e = N_ORD + self.dn        # pores along the normal -> ne > no
        self.n_o = N_ORD

        self.V = math.pi * self.D_vessel ** 2 / 4.0 * self.L_vessel
        self.S0 = S0_WINDOW
        self.v_mean = mean_speed(self.T)
        self.D_kn = self.v_mean * self.d / 3.0
        # membrane-limited time constant
        self.tau_mem = self.V * self.h / (self.p * self.S0 * self.D_kn)

        # external stagnant film thickness when the outside fan is off
        self.bl_off = rng.uniform(10.5, 13.5) * 1e-3            # m
        self.bl_on = rng.uniform(0.05, 0.20) * 1e-3             # m
        if self.seed == 20180001:
            self.bl_off = 12.0e-3
            self.bl_on = 0.0

        # --- optical bench imperfections --------------------------------
        self.table_zero = rng.uniform(-14.0, 14.0)     # deg, rotary-table offset
        self.arm_zero = rng.uniform(-1.2, 1.2)         # deg, detector arm offset
        self.pol_zero = [rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0)]
        # face A = barrier-layer side (good fringe contrast), face B = rough
        self.vis_face = [rng.uniform(0.62, 0.86), rng.uniform(0.10, 0.26)]
        self.scatter = rng.uniform(0.030, 0.075)       # diffuse haze fraction
        self.laser_uA = rng.uniform(148.0, 176.0)      # full-beam photocurrent
        self.dark_uA = rng.uniform(0.18, 0.42)
        self.room_uA = rng.uniform(0.05, 0.35)
        self.laser_drift = rng.uniform(0.004, 0.011)

        # --- sensor -------------------------------------------------------
        self.sensor_gain = rng.uniform(0.985, 1.015)
        self.sensor_off = rng.uniform(-0.004, 0.004)   # %
        self.sensor_noise = rng.uniform(0.0016, 0.0032)
        self.sensor_tau = rng.uniform(14.0, 24.0)      # s, NDIR response time
        self.warmup = rng.uniform(135.0, 195.0)        # s self-calibration
        self.mix_tau_on = rng.uniform(2.5, 5.0)        # s, fan on
        self.mix_tau_off = rng.uniform(85.0, 150.0)    # s, fan off

    # --- convenience -----------------------------------------------------
    def tau_total(self, fan_out):
        """Time constant including the external boundary-layer resistance."""
        bl = self.bl_on if fan_out else self.bl_off
        r_mem = self.h / (self.p * self.S0 * self.D_kn)
        r_ext = bl / (self.S0 * D_CO2_AIR)
        return self.V * (r_mem + r_ext)


# ----------------------------------------------------------------------------
#  Part A --- the airproof vessel
# ----------------------------------------------------------------------------
class DiffusionCell:
    """Well-mixed vessel behind an AAO membrane window.

    State variables
      c_bulk   bulk CO2 fraction in the vessel   [%]
      c_local  fraction in the gas actually seen by the sensor head [%]
      c_read   low-pass filtered value the NDIR detector reports    [%]
    """

    LEAK_OPEN = 1.0 / 18.0      # 1/s per open tube (huge compared with membrane)

    def __init__(self, truth):
        self.tr = truth
        self.c_bulk = truth.c_amb
        self.c_local = truth.c_amb
        self.c_read = truth.c_amb
        self.clamp = [True, True]        # True = closed
        self.lid_on = True
        self.fan_in = False
        self.fan_out = False
        self.batt_in = False             # last cell inserted in the fan block
        self.t = 0.0

    # ---- actions --------------------------------------------------------
    def exhale(self, strength=1.0):
        """Breathe into the vessel through a tube.  Exhaled air is ~4 % CO2."""
        if self.clamp[0] and self.clamp[1] and self.lid_on:
            return False                 # nowhere for the air to go
        frac = max(0.05, min(1.0, strength))
        c_breath = 4.0
        self.c_bulk = self.c_bulk * (1 - frac) + c_breath * frac
        self.c_local = self.c_bulk
        return True

    def purge_suck(self):
        """Suck through one tube while the other admits room air (fastest)."""
        if self.clamp[0] and self.clamp[1]:
            return False
        self.c_bulk = self.tr.c_amb + (self.c_bulk - self.tr.c_amb) * 0.06
        self.c_local = self.c_bulk
        return True

    def purge_fan(self):
        """Lid off + fan blowing room air through the vessel."""
        if self.lid_on or not (self.fan_in or self.fan_out):
            return False
        self.c_bulk = self.tr.c_amb + (self.c_bulk - self.tr.c_amb) * 0.22
        self.c_local = self.c_bulk
        return True

    # ---- dynamics -------------------------------------------------------
    def rate_constant(self):
        """1/s  --  membrane + external film + open tubes."""
        tr = self.tr
        k = 0.0
        if self.lid_on:
            k += 1.0 / tr.tau_total(self.fan_out and self.batt_in)
        else:
            k += 1.0 / 45.0              # lid removed: wide open aperture
        n_open = (0 if self.clamp[0] else 1) + (0 if self.clamp[1] else 1)
        if n_open == 1:
            k += self.LEAK_OPEN * 0.06   # one open tube -- slow chimney exchange
        elif n_open == 2:
            k += self.LEAK_OPEN
        return k

    def step(self, dt):
        tr = self.tr
        if dt <= 0:
            return
        n = max(1, int(dt / 2.0) + 1)
        sub = dt / n
        fan_ok = self.fan_in and self.batt_in
        mix_tau = tr.mix_tau_on if fan_ok else tr.mix_tau_off
        for _ in range(n):
            k = self.rate_constant()
            self.c_bulk += -k * (self.c_bulk - tr.c_amb) * sub
            # the sensor sits away from the window; without stirring it lags
            self.c_local += (self.c_bulk - self.c_local) * (1 - math.exp(-sub / mix_tau))
            self.c_read += (self.c_local - self.c_read) * (1 - math.exp(-sub / tr.sensor_tau))
            self.t += sub


# ----------------------------------------------------------------------------
#  The CO2 sensor unit (display + button state machine)
# ----------------------------------------------------------------------------
class CO2Sensor:
    LIMIT = 0.500                # % -- upper working limit
    MEM = 200
    PERIOD = 20.0                # s between records

    def __init__(self, truth, cell):
        self.tr = truth
        self.cell = cell
        self.powered = False
        self.t_on = 0.0
        self.ready = False
        self.mode = "R"          # "R" recording, "D" record browsing
        self.timer = 0.0
        self.records = []        # list of (t_stamp, value_string_float)
        self.next_rec = 0.0
        self.cursor = 0
        self._noise_seed = random.Random(truth.seed ^ 0x5EED)

    # ---- power ----------------------------------------------------------
    def plug_usb(self, on):
        if on and not self.powered:
            self.powered = True
            self.t_on = 0.0
            self.ready = False
            self.mode = "R"
            self.timer = 0.0
            self.records = []
            self.next_rec = 0.0
            self.cursor = 0
        elif not on and self.powered:
            self.powered = False
            self.ready = False
            self.records = []      # "if you turn the sensor off, all data is lost"
            self.timer = 0.0

    # ---- buttons --------------------------------------------------------
    def press_select(self):
        if not (self.powered and self.ready):
            return
        self.mode = "D" if self.mode == "R" else "R"
        if self.mode == "D":
            self.cursor = max(0, len(self.records) - 1)

    def press_rst(self):
        if not (self.powered and self.ready):
            return
        self.records = []
        self.timer = 0.0
        self.next_rec = 0.0
        self.cursor = 0

    def press_up(self):
        if self.mode == "D" and self.records:
            self.cursor = min(len(self.records) - 1, self.cursor + 1)

    def press_down(self):
        if self.mode == "D" and self.records:
            self.cursor = max(0, self.cursor - 1)

    # ---- physics --------------------------------------------------------
    def raw_reading(self):
        tr = self.tr
        val = self.cell.c_read * tr.sensor_gain + tr.sensor_off
        val += self._noise_seed.gauss(0.0, tr.sensor_noise)
        return val

    def step(self, dt):
        if not self.powered:
            return
        self.t_on += dt
        if not self.ready:
            if self.t_on >= self.tr.warmup:
                self.ready = True
                self.timer = 0.0
                self.next_rec = 0.0
            else:
                return
        self.timer += dt
        if self.mode == "R":
            while self.timer >= self.next_rec:
                v = self.raw_reading()
                self.records.append((self.next_rec, v))
                if len(self.records) > self.MEM:
                    self.records.pop(0)
                self.next_rec += self.PERIOD
            if self.records:
                self.cursor = len(self.records) - 1
        else:
            # timer keeps running but no records are added
            while self.timer >= self.next_rec:
                self.next_rec += self.PERIOD

    # ---- what the LCD shows --------------------------------------------
    def display(self):
        """Returns (line1, line2, line3) exactly as printed on the LCD."""
        if not self.powered:
            return ("", "", "")
        if not self.ready:
            dots = "." * (1 + int(self.t_on / 1.0) % 4)
            return ("CAL" + dots, "", "")
        if self.mode == "R":
            v = self.raw_reading()
            top = "  OL  " if v > self.LIMIT else ("%.3f %%" % v)
            return ("R  %s" % self._fmt_t(self.timer),
                    "CO2 %s" % top,
                    "n=%d" % len(self.records))
        else:
            if not self.records:
                return ("D  %s" % self._fmt_t(self.timer), "-- EMPTY --", "n=0")
            ts, v = self.records[self.cursor]
            top = "  OL  " if v > self.LIMIT else ("%.3f %%" % v)
            return ("D  %s" % self._fmt_t(self.timer),
                    "CO2 %s" % top,
                    "#%03d t=%s" % (self.cursor + 1, self._fmt_t(ts)))

    @staticmethod
    def _fmt_t(t):
        t = int(t)
        return "%d:%02d:%02d" % (t // 3600, (t // 60) % 60, t % 60)


# ----------------------------------------------------------------------------
#  Parts B & C --- the optical bench
# ----------------------------------------------------------------------------
class Optics:
    """Forward optical model of the membrane on the rotary table.

    Geometry (top view):
        laser -> [polariser 1] -> membrane on rotary table -> [polariser 2]
        detector either straight through (psi = 0) or on the swing arm.
    alpha  = angle of incidence, from the true membrane normal
    psi    = scattering angle of the detector arm from the forward direction
             (specular reflection sits at psi = 180 - 2 alpha)
    """

    ACCEPT_DEG = 1.15            # half-acceptance of the photodiode can

    def __init__(self, truth):
        self.tr = truth
        self.rng = random.Random(truth.seed ^ 0xBEEF)
        self.t = 0.0

    # ---- basic optics ---------------------------------------------------
    def beta_ord(self, alpha):
        s = math.sin(alpha) / self.tr.n_o
        s = max(-1.0, min(1.0, s))
        return math.asin(s)

    def film_phase(self, alpha):
        """round-trip phase of the ordinary wave inside the film."""
        s2 = math.sin(alpha) ** 2
        return 4.0 * math.pi * self.tr.h * math.sqrt(self.tr.n_o ** 2 - s2) / LAMBDA

    def r_s(self, alpha):
        """s-polarised amplitude reflection at one air/film interface."""
        n = self.tr.n_o
        ca = math.cos(alpha)
        cb = math.sqrt(max(1e-12, n * n - math.sin(alpha) ** 2)) / n
        return (ca - n * cb) / (ca + n * cb)

    def r_p(self, alpha):
        n = self.tr.n_o
        ca = math.cos(alpha)
        cb = math.sqrt(max(1e-12, n * n - math.sin(alpha) ** 2)) / n
        return (n * ca - cb) / (n * ca + cb)

    def reflectance(self, alpha, face, s_frac=1.0):
        """Airy reflectance of the free-standing film, partially coherent."""
        phi = self.film_phase(alpha)
        vis = self.tr.vis_face[face]
        out = 0.0
        for r, w in ((self.r_s(alpha), s_frac), (self.r_p(alpha), 1.0 - s_frac)):
            if w <= 0:
                continue
            r2 = r * r
            coh = 2 * r2 * (1 - vis * math.cos(phi)) / (1 - 2 * r2 * vis * math.cos(phi) + r2 * r2)
            out += w * coh
        return out

    def retardation(self, alpha):
        """Exact  delta = h (n1 cos b1 - n2 cos b2)  for the two eigenwaves.

        With  n1 = no  and  1/n2^2 = cos^2(b2)/no^2 + sin^2(b2)/ne^2  and
        Snell  sin(alpha) = n1 sin b1 = n2 sin b2, this collapses to

            delta = h [ sqrt(no^2 - s^2) - sqrt(no^2 - s^2 no^2/ne^2) ],  s=sin a

        The first-order expansion of this is the familiar
            delta ~= h dn sin^2(beta)/cos(beta)
        used in the official solution; the two differ by ~4 % at dn/no ~ 0.025.
        """
        tr = self.tr
        s2 = math.sin(alpha) ** 2
        t1 = math.sqrt(max(0.0, tr.n_o ** 2 - s2))
        t2 = math.sqrt(max(0.0, tr.n_o ** 2 - s2 * tr.n_o ** 2 / tr.n_e ** 2))
        return abs(tr.h * (t1 - t2))

    def transmittance(self, alpha, pol1_in, pol2_in, a1_deg, a2_deg):
        """Fraction of the incident laser power reaching the photodiode.

        The laser itself is linearly polarised; polariser axes are given in
        degrees from the plane of incidence (= the rotary-table plane).
        """
        tr = self.tr
        # ---- Fresnel transmission of the two surfaces (unpolarised avg.) --
        Ts = 1.0 - self.r_s(alpha) ** 2
        Tp = 1.0 - self.r_p(alpha) ** 2
        # ---- angle of the polarisation reaching the film -----------------
        if pol1_in:
            a_in = math.radians(a1_deg)
            p_loss = 0.42                    # sheet polariser transmission
        else:
            a_in = math.radians(90.0)        # bare laser: s-polarised
            p_loss = 1.0
        # amplitudes of eigenwave 1 (s, perpendicular) and 2 (p, parallel)
        A1 = math.sin(a_in)
        A2 = math.cos(a_in)
        d = self.retardation(alpha)
        dphi = 2.0 * math.pi * d / LAMBDA
        if pol2_in:
            a_out = math.radians(a2_deg)
            re = A1 * math.sin(a_out) + A2 * math.cos(a_out) * math.cos(dphi)
            im = A2 * math.cos(a_out) * math.sin(dphi)
            amp2 = re * re + im * im
            p_loss *= 0.42
        else:
            amp2 = A1 * A1 + A2 * A2         # no analyser -> no interference
        # weight the Fresnel factors by the eigen-amplitudes
        w1 = A1 * A1
        w2 = A2 * A2
        wsum = max(1e-9, w1 + w2)
        Tfr = (w1 * Ts * Ts + w2 * Tp * Tp) / wsum
        # etalon ripple of the same film (survives, but is weak in transmission)
        rs2 = self.r_s(alpha) ** 2
        ripple = 1.0 + 2.0 * rs2 * tr.vis_face[0] * math.cos(self.film_phase(alpha))
        haze = math.exp(-tr.scatter / max(0.20, math.cos(self.beta_ord(alpha))))
        return max(0.0, amp2 * Tfr * ripple * haze * p_loss)

    # ---- the photodiode -------------------------------------------------
    def photocurrent(self, alpha_deg, psi_deg, mount, pol1_in, pol2_in,
                     a1_deg, a2_deg, face, laser_on, beam_blocked=False):
        """microamps into the (virtually shorted) photodiode."""
        tr = self.tr
        base = tr.dark_uA + tr.room_uA
        if not laser_on or beam_blocked:
            return base + self.rng.gauss(0.0, 0.012)
        alpha = math.radians(abs(alpha_deg))
        if alpha >= math.radians(88.0):
            return base + self.rng.gauss(0.0, 0.012)
        P = tr.laser_uA * (1.0 + tr.laser_drift * math.sin(self.t / 41.0))

        if mount == "rail":
            psi_target = 0.0
            sig = P * self.transmittance(alpha, pol1_in, pol2_in, a1_deg, a2_deg)
            # the transmitted beam is refracted-then-restored: stays on axis
        else:
            # the analyser sits behind the sample on the rail, so a beam that
            # leaves towards the swing arm never passes through it
            psi_target = 180.0 - 2.0 * abs(alpha_deg)
            frac = 0.42 if pol1_in else 1.0
            sig = P * frac * self.reflectance(alpha, face,
                                              s_frac=self._s_fraction(pol1_in, a1_deg))
        dpsi = psi_deg - psi_target
        acc = math.exp(-(dpsi / self.ACCEPT_DEG) ** 2 * 0.7)
        if abs(dpsi) > 4.5 * self.ACCEPT_DEG:
            acc = 0.0
        halo = tr.scatter * 0.045 * P * math.exp(-(dpsi / 26.0) ** 2)
        val = sig * acc + halo + base
        return val + self.rng.gauss(0.0, 0.010 + 0.0016 * math.sqrt(max(0.0, val)))

    @staticmethod
    def _s_fraction(pol1_in, a1_deg):
        if not pol1_in:
            return 1.0
        return math.sin(math.radians(a1_deg)) ** 2


# ----------------------------------------------------------------------------
#  Multimeter
# ----------------------------------------------------------------------------
class Multimeter:
    #  name, full scale (uA), display unit, resolution (uA), decimals
    RANGES = [("200 \u00b5A", 200.0, "\u00b5A", 0.01, 2),
              ("2 mA", 2000.0, "mA", 1.0, 3),
              ("20 mA", 20000.0, "mA", 10.0, 2)]

    def __init__(self):
        self.range_i = 0
        self.on = True
        self.connected = False

    def read(self, uA):
        if not self.on:
            return ""
        name, full, unit, res, dec = self.RANGES[self.range_i]
        if not self.connected:
            uA = 0.0
        if uA > full:
            return "OL"
        q = round(uA / res) * res
        if unit == "mA":
            q /= 1000.0
        return ("%%.%df" % dec) % q

    def unit(self):
        return self.RANGES[self.range_i][2]


# ----------------------------------------------------------------------------
#  Rig --- the single public API.  The GUI and the verification harness both
#  talk to the apparatus only through this object.
# ----------------------------------------------------------------------------
class Rig:
    def __init__(self, seed=None):
        self.truth = Truth(seed)
        self.cell = DiffusionCell(self.truth)
        self.sensor = CO2Sensor(self.truth, self.cell)
        self.optics = Optics(self.truth)
        self.dmm = Multimeter()

        # --- assembly state ------------------------------------------------
        self.built = set()          # ids of installed components
        self.usb_plugged = False
        self.batt_inserted = False

        # --- optical bench state ------------------------------------------
        self.table_deg = 0.0        # what the rotary-table scale reads
        self.arm_deg = 0.0          # what the swing-arm scale reads
        self.det_mount = "rail"     # "rail" | "arm"
        self.pol1_deg = 45.0        # scale reading of polariser 1
        self.pol2_deg = 45.0
        self.laser_on = False
        self.face = 0               # which side of the membrane faces the laser
        self.beam_block = False
        self.fan_in_on = False
        self.fan_out_on = False

        self.sim_time = 0.0
        self.time_scale = 1.0

    # ---------------- assembly ----------------------------------------
    def install(self, key):
        self.built.add(key)
        self._sync()

    def remove(self, key):
        self.built.discard(key)
        self._sync()

    def has(self, key):
        return key in self.built

    def _sync(self):
        self.cell.fan_in = self.has("fan_in") and self.fan_in_on
        self.cell.fan_out = self.has("fan_out") and self.fan_out_on
        self.cell.batt_in = self.batt_inserted
        self.dmm.connected = self.has("dmm") and self.has("pd") and self.has("wires")
        if not (self.has("sensor") and self.has("powerbank") and self.usb_plugged):
            self.sensor.plug_usb(False)

    def set_usb(self, on):
        self.usb_plugged = bool(on)
        if on and self.has("sensor") and self.has("powerbank"):
            self.sensor.plug_usb(True)
        else:
            self.sensor.plug_usb(False)

    def set_battery(self, on):
        self.batt_inserted = bool(on)
        self.cell.batt_in = self.batt_inserted

    # ---------------- part A ------------------------------------------
    def set_clamp(self, i, closed):
        self.cell.clamp[i] = bool(closed)

    def set_lid(self, on):
        self.cell.lid_on = bool(on)

    def set_fan(self, which, on):
        if which == "fan_in":
            self.fan_in_on = bool(on)
        else:
            self.fan_out_on = bool(on)
        self._sync()

    def exhale(self, strength=1.0):
        return self.cell.exhale(strength)

    def purge_suck(self):
        return self.cell.purge_suck()

    def purge_fan(self):
        return self.cell.purge_fan()

    # ---------------- part B / C ---------------------------------------
    def true_alpha(self):
        """Angle of incidence actually realised (deg).  Hidden zero offset."""
        return self.table_deg - self.truth.table_zero

    def true_psi(self):
        return self.arm_deg - self.truth.arm_zero

    def current_uA(self):
        if not (self.has("bench") and self.has("laser") and self.has("stage")
                and self.has("pd")):
            return self.truth.dark_uA + self.truth.room_uA
        return self.optics.photocurrent(
            self.true_alpha(), self.true_psi(), self.det_mount,
            self.has("pol1"), self.has("pol2"),
            self.pol1_deg - self.truth.pol_zero[0],
            self.pol2_deg - self.truth.pol_zero[1],
            self.face, self.laser_on, self.beam_block)

    def dmm_text(self):
        return self.dmm.read(self.current_uA())

    # ---------------- clock --------------------------------------------
    SLICE = 4.0                 # s of simulated time per integration slice

    def advance(self, dt_real):
        dt = dt_real * self.time_scale
        if dt <= 0:
            return
        self.sim_time += dt
        self.optics.t += dt
        n = max(1, int(math.ceil(dt / self.SLICE)))
        n = min(n, 4000)
        sub = dt / n
        for _ in range(n):
            self.cell.step(sub)
            self.sensor.step(sub)

    # ---------------- rulers (what a ruler would show) -----------------
    def measure_vessel(self):
        """Inner length and diameter as read off a mm ruler."""
        L = round(self.truth.L_vessel * 1000.0 * 2) / 2.0     # to 0.5 mm
        D = round(self.truth.D_vessel * 1000.0 * 2) / 2.0
        return L, D            # mm

# ============================================================================
#  SECTION 2 --- equipment artwork
#  Every shape is reconstructed from the EuPhO 2018 problem sheet figure and
#  from the photographs in the official solution.
# ============================================================================

import tkinter as tk
from tkinter import ttk, font as tkfont

# --- palette ---------------------------------------------------------------
BG_LAB = "#1b1f24"
BG_TABLE = "#2c3138"
CL_ALU = "#b9c0c8"
CL_ALU_D = "#7d858e"
CL_ALU_L = "#e2e7ec"
CL_ACRYL = "#8fb6c9"
CL_BLACK = "#22262b"
CL_BLACK_L = "#3a4048"
CL_PCB = "#1f6b3a"
CL_RED = "#e8402a"
CL_LCD = "#9fd66a"
CL_LCD_D = "#2b3a1c"
CL_TXT = "#e8ecf1"
CL_DIM = "#8d959e"
CL_GOLD = "#d7b26a"
CL_MEMB = "#cfd8de"


def _lerp_hex(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def beam_colour(frac):
    """Red laser spot colour for a relative intensity 0..1."""
    f = max(0.0, min(1.0, frac))
    f = f ** 0.45
    return _lerp_hex("#3a0d09", "#ff6a55", f)


# ---------------------------------------------------------------------------
#  small helpers
# ---------------------------------------------------------------------------
def rrect(cv, x0, y0, x1, y1, r, **kw):
    r = min(r, abs(x1 - x0) / 2, abs(y1 - y0) / 2)
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, splinesteps=8, **kw)


def hatch(cv, x0, y0, x1, y1, step, colour, tags=()):
    x = x0
    while x < x1 + (y1 - y0):
        a = (max(x0, x - (y1 - y0)), min(y1, y0 + (x - x0)))
        b = (min(x1, x), max(y0, y1 - (x1 - x)))
        cv.create_line(a[0], a[1], b[0], b[1], fill=colour, tags=tags)
        x += step


# ---------------------------------------------------------------------------
#  A-station artwork (side elevation)
# ---------------------------------------------------------------------------
def art_vessel(cv, x, y, s, tag, lid=True, clamp=(True, True),
               have_tubes=False, have_sensor=False, have_fan=False,
               fan_ang=0.0, membrane=True):
    """Airproof cylindrical vessel, side elevation.  (x,y) = centre of body."""
    w, hgt = 150 * s, 118 * s
    x0, x1 = x - w / 2, x + w / 2
    y0, y1 = y - hgt / 2, y + hgt / 2

    # --- glass body ------------------------------------------------------
    cv.create_rectangle(x0, y0, x1, y1, fill="#3b4a52", outline="", tags=tag)
    for i in range(7):
        t = i / 6.0
        cv.create_line(x0 + w * t, y0, x0 + w * t, y1,
                       fill=_lerp_hex("#46585f", "#6d8993", 1 - abs(t - 0.32) * 2),
                       width=max(1, int(w / 7)), tags=tag)
    cv.create_rectangle(x0, y0, x1, y1, outline=CL_ACRYL, width=max(1, int(1.6 * s)),
                        tags=tag)
    # highlight
    cv.create_line(x0 + w * 0.18, y0 + 6 * s, x0 + w * 0.18, y1 - 6 * s,
                   fill="#cfe6ef", width=max(1, int(2.2 * s)), tags=tag)

    # --- bottom flange ---------------------------------------------------
    cv.create_rectangle(x0 - 7 * s, y1, x1 + 7 * s, y1 + 9 * s,
                        fill=CL_ALU, outline=CL_ALU_D, tags=tag)

    # --- top flange / lid ------------------------------------------------
    ly = y0 - 12 * s
    if lid:
        cv.create_rectangle(x0 - 9 * s, ly, x1 + 9 * s, y0 + 2 * s,
                            fill=CL_ALU, outline=CL_ALU_D, tags=tag)
        cv.create_rectangle(x0 - 9 * s, ly, x1 + 9 * s, ly + 3.5 * s,
                            fill=CL_ALU_L, outline="", tags=tag)
        # four clamp screws
        for k in range(4):
            sx = x0 + w * (0.08 + 0.28 * k)
            cv.create_oval(sx - 3.2 * s, ly + 2 * s, sx + 3.2 * s, ly + 8.4 * s,
                           fill=CL_ALU_D, outline="#5c646c", tags=tag)
        # --- membrane window (d_w = 13 mm) -------------------------------
        if membrane:
            mw = 26 * s
            cv.create_rectangle(x - mw / 2, ly - 3.2 * s, x + mw / 2, ly + 0.5 * s,
                                fill=CL_MEMB, outline="#8e9aa2", tags=tag)
            cv.create_line(x + mw / 2, ly - 1.5 * s, x + mw / 2 + 34 * s, ly - 16 * s,
                           fill="#6a727a", tags=tag)
            cv.create_text(x + mw / 2 + 36 * s, ly - 18 * s, anchor="w",
                           text=T("막 창  d_w = 13 mm", "membrane window  d_w = 13 mm"),
                           fill="#9fb0bc", font=("TkDefaultFont", max(6, int(7.5 * s))),
                           tags=tag)
    else:
        cv.create_rectangle(x0 - 9 * s, ly - 26 * s, x1 + 9 * s, ly - 26 * s + 14 * s,
                            fill=CL_ALU, outline=CL_ALU_D, tags=tag)
        cv.create_text(x, ly - 34 * s, text=T("뚜껑 열림", "lid off"),
                       fill="#e0a24a", font=("TkDefaultFont", max(6, int(8 * s))),
                       tags=tag)

    # --- two connecting tubes with clamps -------------------------------
    if have_tubes:
        for i, side in enumerate((-1, 1)):
            bx = x + side * (w / 2)
            by = y - hgt * 0.28 + i * hgt * 0.16
            ex = bx + side * 62 * s
            cv.create_line(bx, by, bx + side * 22 * s, by,
                           ex, by + 16 * s, fill="#c8ccd0",
                           width=max(2, int(5 * s)), smooth=True, tags=tag)
            cx = bx + side * 40 * s
            cy = by + 6 * s
            col = "#d8493a" if clamp[i] else "#4a5158"
            cv.create_rectangle(cx - 5 * s, cy - 7 * s, cx + 5 * s, cy + 7 * s,
                                fill=col, outline="#20242a", tags=tag)
            cv.create_text(cx, cy + 15 * s,
                           text=(T("잠금", "shut") if clamp[i] else T("열림", "open")),
                           fill=col if clamp[i] else CL_DIM,
                           font=("TkDefaultFont", max(6, int(7 * s))), tags=tag)

    # --- CO2 sensor board inside ----------------------------------------
    if have_sensor:
        bx, by = x - w * 0.24, y + hgt * 0.22
        rrect(cv, bx - 24 * s, by - 11 * s, bx + 24 * s, by + 11 * s, 3 * s,
              fill=CL_PCB, outline="#0d3d21", tags=tag)
        cv.create_rectangle(bx - 16 * s, by - 7 * s, bx + 2 * s, by + 7 * s,
                            fill="#12151a", outline="#3a4048", tags=tag)
        cv.create_oval(bx + 8 * s, by - 5 * s, bx + 18 * s, by + 5 * s,
                       fill="#c9ccd1", outline="#7d858e", tags=tag)
        cv.create_text(bx, by + 18 * s, text="CO2", fill=CL_DIM,
                       font=("TkDefaultFont", max(6, int(7 * s))), tags=tag)
        # USB lead out of the sealed port
        cv.create_line(bx - 24 * s, by, x0 - 26 * s, by, x0 - 40 * s, by + 26 * s,
                       fill="#e6e6e6", width=max(1, int(2.4 * s)), smooth=True, tags=tag)

    # --- internal fan mounted under the window --------------------------
    if have_fan:
        art_fan(cv, x + w * 0.20, y - hgt * 0.22, 20 * s, fan_ang, tag)


def art_fan(cv, x, y, r, ang, tag, frame=True, colour=CL_BLACK):
    if frame:
        rrect(cv, x - r, y - r, x + r, y + r, r * 0.22,
              fill=colour, outline="#12151a", tags=tag)
        for dx in (-1, 1):
            for dy in (-1, 1):
                cv.create_oval(x + dx * r * 0.74 - r * 0.09, y + dy * r * 0.74 - r * 0.09,
                               x + dx * r * 0.74 + r * 0.09, y + dy * r * 0.74 + r * 0.09,
                               fill="#0e1114", outline="", tags=tag)
    cv.create_oval(x - r * 0.86, y - r * 0.86, x + r * 0.86, y + r * 0.86,
                   fill="#171a1e", outline="#4a5158", tags=tag)
    for k in range(7):
        a = math.radians(ang + k * 360.0 / 7)
        a2 = a + 0.60
        cv.create_polygon(
            x + r * 0.13 * math.cos(a), y + r * 0.13 * math.sin(a),
            x + r * 0.82 * math.cos(a - 0.16), y + r * 0.82 * math.sin(a - 0.16),
            x + r * 0.80 * math.cos(a2), y + r * 0.80 * math.sin(a2),
            x + r * 0.15 * math.cos(a2 + 0.10), y + r * 0.15 * math.sin(a2 + 0.10),
            fill="#39404a", outline="#525a64", tags=tag)
    cv.create_oval(x - r * 0.20, y - r * 0.20, x + r * 0.20, y + r * 0.20,
                   fill="#8a929b", outline="#5c646c", tags=tag)


def art_battery_block(cv, x, y, s, tag, inserted):
    w, h = 46 * s, 22 * s
    rrect(cv, x - w / 2, y - h / 2, x + w / 2, y + h / 2, 3 * s,
          fill="#2b3138", outline="#4a5158", tags=tag)
    for k in range(3):
        cx = x - w / 2 + 8 * s + k * 12 * s
        cv.create_rectangle(cx - 4 * s, y - 7 * s, cx + 4 * s, y + 7 * s,
                            fill="#1a1d22" if (k == 2 and not inserted) else "#3f6f3a",
                            outline="#555c64", tags=tag)
    cv.create_text(x, y + h / 2 + 8 * s,
                   text=T("배터리", "cells") if inserted else T("배터리 1개 빠짐", "1 cell missing"),
                   fill=CL_DIM if inserted else "#e0a24a",
                   font=("TkDefaultFont", max(6, int(7 * s))), tags=tag)


def art_powerbank(cv, x, y, s, tag, usb=False):
    w, h = 56 * s, 26 * s
    rrect(cv, x - w / 2, y - h / 2, x + w / 2, y + h / 2, 4 * s,
          fill="#414951", outline="#666e77", tags=tag)
    for k in range(4):
        cv.create_rectangle(x - w / 2 + 6 * s + k * 6 * s, y + 5 * s,
                            x - w / 2 + 9 * s + k * 6 * s, y + 8 * s,
                            fill="#6fd36f" if usb else "#2a2f35", outline="", tags=tag)
    cv.create_rectangle(x + w / 2 - 12 * s, y - 5 * s, x + w / 2 - 2 * s, y + 1 * s,
                        fill="#20252b", outline="#7d858e", tags=tag)
    cv.create_text(x, y + h / 2 + 9 * s, text=T("보조배터리", "power bank"),
                   fill=CL_DIM, font=("TkDefaultFont", max(6, int(7 * s))), tags=tag)


def art_gluepads(cv, x, y, s, tag):
    for k in range(3):
        cv.create_rectangle(x - 16 * s + k * 12 * s, y - 8 * s,
                            x - 6 * s + k * 12 * s, y + 8 * s,
                            fill="#e9e2c9", outline="#b8b096", tags=tag)


# ---------------------------------------------------------------------------
#  Optical bench artwork (plan view)
# ---------------------------------------------------------------------------
def art_rail(cv, x0, x1, y, s, tag):
    hgt = 26 * s
    cv.create_rectangle(x0, y - hgt, x1, y + hgt, fill="#5d666f",
                        outline="#3a4048", tags=tag)
    for yy in (-hgt * 0.55, hgt * 0.55):
        cv.create_line(x0, y + yy, x1, y + yy, fill="#7e878f", tags=tag)
    n = int((x1 - x0) / (20 * s))
    for k in range(n + 1):
        xx = x0 + k * 20 * s
        big = (k % 5 == 0)
        cv.create_line(xx, y - hgt, xx, y - hgt + (9 if big else 5) * s,
                       fill="#c9ced4" if big else "#98a0a8", tags=tag)
        if big:
            cv.create_text(xx, y - hgt + 15 * s, text="%d" % (k * 2),
                           fill="#98a0a8",
                           font=("TkDefaultFont", max(5, int(6 * s))), tags=tag)


def art_post(cv, x, y, s, tag, w=13):
    cv.create_rectangle(x - w * s, y - 6 * s, x + w * s, y + 6 * s,
                        fill="#4c545c", outline="#2f353b", tags=tag)


def art_laser(cv, x, y, s, tag, on):
    L, w = 54 * s, 15 * s
    cv.create_rectangle(x - L, y - w, x + L * 0.35, y + w,
                        fill="#3c4249", outline="#6a727a", tags=tag)
    cv.create_rectangle(x + L * 0.35, y - w * 0.55, x + L * 0.62, y + w * 0.55,
                        fill="#20252b", outline="#6a727a", tags=tag)
    cv.create_oval(x + L * 0.55, y - w * 0.35, x + L * 0.70, y + w * 0.35,
                   fill=CL_RED if on else "#5a2620", outline="", tags=tag)
    cv.create_oval(x - L * 0.75, y - 3 * s, x - L * 0.60, y + 3 * s,
                   fill="#6fd36f" if on else "#2a2f35", outline="", tags=tag)
    cv.create_text(x - L * 0.15, y, text="660 nm", fill="#c9ced4",
                   font=("TkDefaultFont", max(5, int(7 * s))), tags=tag)


def art_polarizer(cv, x, y, s, tag, ang_deg, label):
    r = 26 * s
    cv.create_rectangle(x - 7 * s, y - r, x + 7 * s, y + r,
                        fill="#39404a", outline="#6a727a", tags=tag)
    cv.create_line(x - 7 * s, y - r, x + 7 * s, y - r, fill="#8d959e", tags=tag)
    # the polariser axis line printed on the frame (45 deg to the frame edge)
    a = math.radians(ang_deg)
    dy = r * 0.78 * math.cos(a)
    dz = 7 * s * math.sin(a)
    cv.create_line(x - dz, y - dy, x + dz, y + dy, fill="#e6c46a",
                   width=max(1, int(2 * s)), tags=tag)
    cv.create_text(x, y + r + 9 * s, text="%s %.0f\u00b0" % (label, ang_deg),
                   fill=CL_DIM, font=("TkDefaultFont", max(5, int(7 * s))), tags=tag)


def art_rotary_table(cv, x, y, R, tag, table_deg, face, s):
    """Graduated rotary table seen from above, with the membrane at its centre."""
    cv.create_oval(x - R, y - R, x + R, y + R, fill="#3f474f",
                   outline="#22262b", width=max(1, int(2 * s)), tags=tag)
    # --- graduated annulus, rotates with the table --------------------
    cv.create_oval(x - R * 0.97, y - R * 0.97, x + R * 0.97, y + R * 0.97,
                   fill="#59626b", outline="#7d858e", tags=tag)
    for k in range(180):
        a = math.radians(k * 2 - table_deg)
        big = (k % 5 == 0)
        r0 = R * (0.80 if big else 0.87)
        cv.create_line(x + r0 * math.cos(a), y - r0 * math.sin(a),
                       x + R * 0.96 * math.cos(a), y - R * 0.96 * math.sin(a),
                       fill="#e3e8ee" if big else "#a8b0b8",
                       width=(max(1, int(1.4 * s)) if big else 1), tags=tag)
    for k in range(12):
        a = math.radians(k * 30 - table_deg)
        rr = R * 0.70
        cv.create_text(x + rr * math.cos(a), y - rr * math.sin(a),
                       text="%d" % (k * 30), fill="#f0f4f8",
                       font=("TkDefaultFont", max(6, int(8.5 * s)), "bold"), tags=tag)
    # --- clear inner disc ---------------------------------------------
    cv.create_oval(x - R * 0.56, y - R * 0.56, x + R * 0.56, y + R * 0.56,
                   fill="#2d333a", outline="#7d858e", tags=tag)
    # --- fixed index mark on the bench --------------------------------
    cv.create_polygon(x, y - R - 1 * s, x - 5 * s, y - R - 14 * s,
                      x + 5 * s, y - R - 14 * s, fill="#e8c05a",
                      outline="#8a6f21", tags=tag)
    cv.create_text(x, y - R - 22 * s, text=T("지표", "index"), fill="#e8c05a",
                   font=("TkDefaultFont", max(5, int(7 * s))), tags=tag)
    # --- the membrane, edge-on in its holder --------------------------
    a = math.radians(table_deg)
    hl = R * 0.50
    dx, dy = hl * math.sin(a), hl * math.cos(a)
    cv.create_line(x - dx * 1.12, y - dy * 1.12, x + dx * 1.12, y + dy * 1.12,
                   fill="#6e7780",
                   width=max(3, int(7 * s)), tags=tag)
    cv.create_line(x - dx, y - dy, x + dx, y + dy,
                   fill=CL_MEMB, width=max(2, int(3.4 * s)), tags=tag)
    # barrier-layer face marked with a dot
    nx, ny = math.cos(a), -math.sin(a)
    sgn = 1 if face == 0 else -1
    cv.create_oval(x + sgn * nx * 7 * s - 3.0 * s, y + sgn * ny * 7 * s - 3.0 * s,
                   x + sgn * nx * 7 * s + 3.0 * s, y + sgn * ny * 7 * s + 3.0 * s,
                   fill="#e8c05a", outline="", tags=tag)
    cv.create_oval(x - 3 * s, y - 3 * s, x + 3 * s, y + 3 * s,
                   fill="#12151a", outline="#8d959e", tags=tag)


def art_arm(cv, x, y, R, arm_deg, s, tag, has_pd):
    a = math.radians(arm_deg)
    ex, ey = x + R * math.cos(a), y - R * math.sin(a)
    cv.create_line(x, y, ex, ey, fill="#6a727a" if has_pd else "#464e56",
                   width=max(2, int((7 if has_pd else 4) * s)), tags=tag)
    cv.create_oval(x - 8 * s, y - 8 * s, x + 8 * s, y + 8 * s,
                   fill="#39404a", outline="#8d959e", tags=tag)
    # arm scale
    cv.create_arc(x - R * 1.14, y - R * 1.14, x + R * 1.14, y + R * 1.14,
                  start=0, extent=180, style="arc", outline="#4a5158", tags=tag)
    for k in range(0, 181, 10):
        aa = math.radians(k)
        cv.create_line(x + R * 1.10 * math.cos(aa), y - R * 1.10 * math.sin(aa),
                       x + R * 1.17 * math.cos(aa), y - R * 1.17 * math.sin(aa),
                       fill="#98a0a8", tags=tag)
        if k % 30 == 0:
            cv.create_text(x + R * 1.26 * math.cos(aa), y - R * 1.26 * math.sin(aa),
                           text="%d" % k, fill="#98a0a8",
                           font=("TkDefaultFont", max(5, int(6.5 * s))), tags=tag)
    if has_pd:
        art_photodiode(cv, ex, ey, s, tag, math.degrees(a) + 180.0)
    return ex, ey


def art_photodiode(cv, x, y, s, tag, face_deg):
    a = math.radians(face_deg)
    L = 17 * s
    ca, sa = math.cos(a), -math.sin(a)
    px, py = -sa, ca
    cv.create_polygon(
        x + ca * L + px * 12 * s, y + sa * L + py * 12 * s,
        x + ca * L - px * 12 * s, y + sa * L - py * 12 * s,
        x - ca * L - px * 12 * s, y - sa * L - py * 12 * s,
        x - ca * L + px * 12 * s, y - sa * L + py * 12 * s,
        fill="#2b3138", outline="#8d959e", tags=tag)
    cv.create_oval(x + ca * L * 0.92 - 7 * s, y + sa * L * 0.92 - 7 * s,
                   x + ca * L * 0.92 + 7 * s, y + sa * L * 0.92 + 7 * s,
                   fill="#1b3a5c", outline="#5f7fa0", tags=tag)
    for sgn in (-1, 1):
        cv.create_line(x - ca * L, y - sa * L,
                       x - ca * L * 2.2 + px * sgn * 9 * s,
                       y - sa * L * 2.2 + py * sgn * 9 * s,
                       fill="#d8493a" if sgn < 0 else "#2a2f35",
                       width=max(1, int(2 * s)), tags=tag)


def art_screen(cv, x, y, s, tag, spot=None):
    w, h = 10 * s, 40 * s
    cv.create_rectangle(x - w, y - h, x + w, y + h, fill="#e9e9e4",
                        outline="#9aa0a6", tags=tag)
    if spot:
        f, off = spot
        col = beam_colour(f)
        r = 4 * s + 3 * s * f
        cv.create_oval(x - r, y + off - r, x + r, y + off + r,
                       fill=col, outline="", tags=tag)


def art_multimeter(cv, x, y, s, tag, text, unit, on):
    w, h = 62 * s, 96 * s
    rrect(cv, x - w, y - h, x + w, y + h, 8 * s, fill="#c8501f",
          outline="#7d3111", tags=tag)
    rrect(cv, x - w * 0.82, y - h * 0.90, x + w * 0.82, y - h * 0.40, 4 * s,
          fill=CL_LCD if on else "#5d6b4d", outline="#3d4a33", tags=tag)
    cv.create_text(x + w * 0.62, y - h * 0.64, text=text if on else "", anchor="e",
                   fill="#1b2412", font=("Courier", max(8, int(15 * s)), "bold"), tags=tag)
    cv.create_text(x - w * 0.66, y - h * 0.50, text=unit if on else "", anchor="w",
                   fill="#1b2412", font=("Courier", max(6, int(9 * s))), tags=tag)
    cv.create_oval(x - w * 0.5, y - h * 0.28, x + w * 0.5, y + h * 0.42,
                   fill="#2b3138", outline="#12151a", tags=tag)


def art_ruler(cv, x, y, s, tag, length=120):
    L = length * s
    cv.create_rectangle(x - L / 2, y - 9 * s, x + L / 2, y + 9 * s,
                        fill="#e8dfa8", outline="#a89b57", tags=tag)
    n = int(length / 5)
    for k in range(n + 1):
        xx = x - L / 2 + k * 5 * s
        big = (k % 2 == 0)
        cv.create_line(xx, y - 9 * s, xx, y - 9 * s + (7 if big else 4) * s,
                       fill="#5c5326", tags=tag)


# ---------------------------------------------------------------------------
#  Parts-box icons --- one dispatcher for every component
# ---------------------------------------------------------------------------
def draw_icon(cv, key, x, y, s, tag):
    if key == "vessel":
        art_vessel(cv, x, y + 4 * s, s * 0.46, tag, membrane=True)
    elif key == "tubes":
        for i, dy in enumerate((-9 * s, 11 * s)):
            cv.create_line(x - 30 * s, y + dy, x - 6 * s, y + dy, x + 26 * s, y + dy + 12 * s,
                           fill="#c8ccd0", width=max(2, int(4 * s)), smooth=True, tags=tag)
            cv.create_rectangle(x + 2 * s - 5 * s, y + dy + 4 * s - 7 * s,
                                x + 2 * s + 5 * s, y + dy + 4 * s + 7 * s,
                                fill="#d8493a", outline="#20242a", tags=tag)
    elif key == "sensor":
        rrect(cv, x - 30 * s, y - 15 * s, x + 30 * s, y + 15 * s, 4 * s,
              fill=CL_PCB, outline="#0d3d21", tags=tag)
        cv.create_rectangle(x - 22 * s, y - 9 * s, x + 2 * s, y + 9 * s,
                            fill="#12151a", outline="#3a4048", tags=tag)
        cv.create_oval(x + 8 * s, y - 7 * s, x + 22 * s, y + 7 * s,
                       fill="#c9ccd1", outline="#7d858e", tags=tag)
    elif key == "powerbank":
        art_powerbank(cv, x, y, s, tag)
    elif key in ("fan_in", "fan_out"):
        art_fan(cv, x - 6 * s, y, 22 * s, 0, tag)
        art_battery_block(cv, x + 34 * s, y, s * 0.8, tag, True)
    elif key == "pads":
        art_gluepads(cv, x, y, s, tag)
    elif key == "bench":
        art_rail(cv, x - 46 * s, x + 46 * s, y, s * 0.9, tag)
    elif key == "laser":
        art_laser(cv, x, y, s * 0.9, tag, False)
    elif key in ("pol1", "pol2"):
        art_polarizer(cv, x, y, s * 0.9, tag, 45.0, T("편광판", "pol"))
    elif key == "stage":
        art_rotary_table(cv, x, y, 34 * s, tag, 0.0, 0, s * 0.75)
    elif key == "pd":
        art_photodiode(cv, x, y, s * 1.0, tag, 180.0)
    elif key == "dmm":
        art_multimeter(cv, x, y, s * 0.42, tag, "0.00", "uA", True)
    elif key == "wires":
        for sgn, col in ((-1, "#d8493a"), (1, "#2a2f35")):
            cv.create_line(x - 34 * s, y + sgn * 8 * s, x - 6 * s, y + sgn * 14 * s,
                           x + 30 * s, y + sgn * 6 * s, fill=col,
                           width=max(2, int(3 * s)), smooth=True, tags=tag)
        for sgn in (-1, 1):
            cv.create_rectangle(x + 26 * s, y + sgn * 6 * s - 4 * s,
                                x + 36 * s, y + sgn * 6 * s + 4 * s,
                                fill="#b9c0c8", outline="#5c646c", tags=tag)
    elif key == "screen":
        cv.create_rectangle(x - 24 * s, y - 16 * s, x + 24 * s, y + 16 * s,
                            fill="#e9e9e4", outline="#9aa0a6", tags=tag)
    elif key == "rulers":
        art_ruler(cv, x, y - 8 * s, s * 0.75, tag)
        art_ruler(cv, x, y + 10 * s, s * 0.75, tag)

# ============================================================================
#  SECTION 3 --- Assembly tab
# ============================================================================

#  key, ko, en, station, slot index, prerequisites
PARTS = [
    ("vessel",    "기밀 용기 (막 창)",     "airproof vessel (membrane window)", "A", 0, []),
    ("tubes",     "연결관 2개 + 클램프",   "2 connecting tubes + clamps",       "A", 1, ["vessel"]),
    ("sensor",    "CO\u2082 농도 센서",     "CO2 concentration sensor",          "A", 2, ["vessel"]),
    ("powerbank", "보조배터리",            "power bank",                        "A", 3, []),
    ("fan_in",    "내부 팬 + 배터리 블록", "inner fan + battery block",         "A", 4, ["vessel"]),
    ("fan_out",   "외부 팬 + 배터리 블록", "outer fan + battery block",         "A", 5, ["vessel"]),
    ("pads",      "접착 패드",             "glue pads",                         "A", 6, []),
    ("bench",     "광학 벤치 (레일)",      "optical bench (rail)",              "O", 0, []),
    ("laser",     "레이저 \u03bb=660 nm",  "laser, lambda = 660 nm",            "O", 1, ["bench"]),
    ("pol1",      "편광판 1 (편광자)",     "polariser 1",           "O", 2, ["bench", "laser"]),
    ("stage",     "회전대 + 막 지지대",    "rotary table + membrane support",   "O", 3, ["bench"]),
    ("pol2",      "편광판 2 (검광자)",     "polariser 2 (analyser)",            "O", 4, ["bench", "stage"]),
    ("pd",        "광다이오드",            "photodiode",                        "O", 5, ["bench"]),
    ("dmm",       "멀티미터",              "multimeter",                        "O", 6, []),
    ("wires",     "전선 + 클립",           "wires + clips",                     "O", 7, ["pd", "dmm"]),
    ("screen",    "흰 종이 (스크린)",      "white paper (screen)",              "O", 8, ["bench"]),
    ("rulers",    "자 2개",                "2 rulers",                          "O", 9, []),
]
PART_BY_KEY = {p[0]: p for p in PARTS}


def part_name(key):
    p = PART_BY_KEY[key]
    return T(p[1], p[2])


class AssemblyTab(ttk.Frame):
    BOX_W = 268
    ICON_H = 74

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.rig = app.rig
        self.drag = None
        self.msg = ""
        self.msg_t = 0.0
        self.box_scroll = 0.0

        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 2))
        ttk.Label(top, text=T("① 부품 상자에서 부품을 끌어 실험대의 빈 자리에 놓으시오. "
                              "오른쪽 클릭 = 부품 상자로 되돌리기.",
                              "1. Drag a part from the box onto an empty seat on the bench. "
                              "Right-click returns it to the box.")).pack(side="left")
        self.btn_all = ttk.Button(top, text=T("전체 조립", "assemble all"),
                                  command=self.assemble_all)
        self.btn_all.pack(side="right")
        ttk.Button(top, text=T("전체 해체", "strip all"),
                   command=self.strip_all).pack(side="right", padx=6)

        self.cv = tk.Canvas(self, bg=BG_LAB, highlightthickness=0)
        self.cv.pack(fill="both", expand=True, padx=8, pady=8)
        self.cv.bind("<Configure>", lambda e: self.redraw())
        self.cv.bind("<Button-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_move)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Button-3>", self.on_right)
        self.cv.bind("<MouseWheel>", self.on_wheel)
        self.cv.bind("<Button-4>", lambda e: self.on_wheel(e, 120))
        self.cv.bind("<Button-5>", lambda e: self.on_wheel(e, -120))

        self.slots = {}          # (station, index) -> (cx, cy, w, h)
        self.box_rects = {}      # key -> (x0,y0,x1,y1)

    # ------------------------------------------------------------------
    def note(self, s):
        self.msg = s
        self.msg_t = time.time()

    def missing(self, key):
        return [k for k in PART_BY_KEY[key][5] if not self.rig.has(k)]

    def try_install(self, key, station, index):
        p = PART_BY_KEY[key]
        if station != p[3] or index != p[4]:
            self.note(T("이 자리에는 '%s'가 들어가지 않는다.", "'%s' does not fit that seat.")
                      % part_name(key))
            return False
        miss = self.missing(key)
        if miss:
            self.note(T("먼저 %s 을(를) 설치해야 한다.", "Install %s first.")
                      % ", ".join(part_name(k) for k in miss))
            return False
        self.rig.install(key)
        self.note(T("%s 설치 완료.", "%s installed.") % part_name(key))
        return True

    def try_remove(self, key):
        dependants = [k for k, p in PART_BY_KEY.items()
                      if key in p[5] and self.rig.has(k)]
        if dependants:
            self.note(T("%s 이(가) 여기에 얹혀 있다. 먼저 치우시오.",
                        "%s rests on it -- remove that first.")
                      % ", ".join(part_name(k) for k in dependants))
            return
        self.rig.remove(key)
        if key == "fan_in":
            self.rig.set_fan("fan_in", False)
        if key == "fan_out":
            self.rig.set_fan("fan_out", False)
        if key in ("sensor", "powerbank"):
            self.rig.set_usb(False)
        self.note(T("%s 을(를) 상자에 넣었다.", "%s put back in the box.") % part_name(key))

    def assemble_all(self):
        for _ in range(4):
            for k, _ko, _en, st, ix, _pr in PARTS:
                if not self.rig.has(k) and not self.missing(k):
                    self.rig.install(k)
        self.note(T("모든 부품을 설치했다.", "All parts installed."))
        self.redraw()

    def strip_all(self):
        for k, *_ in reversed(PARTS):
            self.rig.remove(k)
        self.rig.set_usb(False)
        self.rig.set_fan("fan_in", False)
        self.rig.set_fan("fan_out", False)
        self.note(T("실험대를 비웠다.", "Bench cleared."))
        self.redraw()

    # ------------------------------------------------------------------
    def on_press(self, e):
        for key, (x0, y0, x1, y1) in self.box_rects.items():
            if x0 <= e.x <= x1 and y0 <= e.y <= y1 and not self.rig.has(key):
                self.drag = [key, e.x, e.y]
                self.redraw()
                return
        # picking an already-seated part starts a drag too
        hit = self.slot_at(e.x, e.y)
        if hit:
            st, ix = hit
            for k, _ko, _en, s2, i2, _pr in PARTS:
                if s2 == st and i2 == ix and self.rig.has(k):
                    self.drag = [k, e.x, e.y]
                    return

    def on_move(self, e):
        if self.drag:
            self.drag[1], self.drag[2] = e.x, e.y
            self.redraw()

    def on_release(self, e):
        if not self.drag:
            return
        key = self.drag[0]
        self.drag = None
        hit = self.slot_at(e.x, e.y)
        if hit:
            self.try_install(key, hit[0], hit[1])
        else:
            for x0, y0, x1, y1 in [self.box_area]:
                if x0 <= e.x <= x1 and y0 <= e.y <= y1 and self.rig.has(key):
                    self.try_remove(key)
        self.redraw()

    def on_right(self, e):
        hit = self.slot_at(e.x, e.y)
        if hit:
            st, ix = hit
            for k, _ko, _en, s2, i2, _pr in PARTS:
                if s2 == st and i2 == ix and self.rig.has(k):
                    self.try_remove(k)
                    self.redraw()
                    return

    def on_wheel(self, e, delta=None):
        d = delta if delta is not None else e.delta
        if e.x > self.BOX_W:
            return
        span = len(PARTS) * self.ICON_H + 46 - max(1, self.cv.winfo_height())
        self.box_scroll = max(0.0, min(max(0.0, span),
                                       self.box_scroll - (1 if d > 0 else -1) * 46))
        self.redraw()

    def slot_at(self, x, y):
        for (st, ix), (cx, cy, w, h) in self.slots.items():
            if abs(x - cx) <= w / 2 and abs(y - cy) <= h / 2:
                return (st, ix)
        return None

    # ------------------------------------------------------------------
    def redraw(self):
        cv = self.cv
        cv.delete("all")
        W = max(600, cv.winfo_width())
        H = max(420, cv.winfo_height())

        # ---- parts box --------------------------------------------------
        bw = self.BOX_W
        self.box_area = (0, 0, bw, H)
        cv.create_rectangle(0, 0, bw, H, fill="#23282e", outline="#3a4048")
        self.box_rects = {}
        span = len(PARTS) * self.ICON_H + 46 - H
        self.box_scroll = max(0.0, min(max(0.0, span), self.box_scroll))
        y = 34 - self.box_scroll
        for key, ko, en, st, ix, pr in PARTS:
            x0, y0, x1, y1 = 8, y, bw - 8, y + self.ICON_H - 6
            if y1 < 26 or y0 > H:
                y += self.ICON_H
                continue
            placed = self.rig.has(key)
            blocked = bool(self.missing(key))
            cv.create_rectangle(x0, y0, x1, y1,
                                fill="#1b1f24" if placed else "#2d333a",
                                outline="#4a5158" if not blocked else "#5a4a2a")
            if not placed:
                self.box_rects[key] = (x0, y0, x1, y1)
                draw_icon(cv, key, x0 + 46, (y0 + y1) / 2, 0.62, "box")
            else:
                cv.create_text(x0 + 46, (y0 + y1) / 2, text="\u2714",
                               fill="#5fbf6a", font=("TkDefaultFont", 20))
            cv.create_text(x0 + 92, (y0 + y1) / 2 - 8, text=T(ko, en), anchor="w",
                           fill=CL_DIM if placed else CL_TXT,
                           font=("TkDefaultFont", 9))
            if not placed and blocked:
                cv.create_text(x0 + 92, (y0 + y1) / 2 + 9, anchor="w",
                               text=T("선행: ", "needs: ") +
                                    ", ".join(part_name(k) for k in self.missing(key)),
                               fill="#c79a4a", font=("TkDefaultFont", 7))
            y += self.ICON_H
        cv.create_rectangle(0, 0, bw, 26, fill="#23282e", outline="")
        cv.create_line(0, 26, bw, 26, fill="#3a4048")
        cv.create_text(bw / 2, 14, text=T("부품 상자  (휠로 넘김)", "parts box  (wheel to scroll)"),
                       fill=CL_TXT, font=("TkDefaultFont", 11, "bold"))
        if span > 0:
            fh = max(24.0, (H - 30) * (H / float(H + span)))
            fy = 28 + (H - 32 - fh) * (self.box_scroll / span)
            cv.create_rectangle(bw - 6, fy, bw - 2, fy + fh, fill="#5a636c", outline="")

        # ---- two stations ----------------------------------------------
        self.slots = {}
        gx0 = bw + 16
        gw = W - gx0 - 16
        ah = (H - 40) * 0.46
        self._station(cv, gx0, 14, gw, ah, "A",
                      T("A. 확산 실험대", "A. diffusion station"), 7)
        self._station(cv, gx0, 26 + ah, gw, H - 40 - ah, "O",
                      T("B / C. 광학 벤치", "B / C. optical bench"), 10)

        # ---- drag ghost --------------------------------------------------
        if self.drag:
            key, mx, my = self.drag
            draw_icon(cv, key, mx, my, 0.62, "ghost")
            cv.create_text(mx, my + 30, text=part_name(key), fill=CL_TXT,
                           font=("TkDefaultFont", 8))

        # ---- message ------------------------------------------------------
        if self.msg and time.time() - self.msg_t < 6.0:
            cv.create_text(gx0 + gw / 2, H - 12, text=self.msg, fill="#e8c05a",
                           font=("TkDefaultFont", 10))

    def _station(self, cv, x, y, w, h, station, title, n):
        cv.create_rectangle(x, y, x + w, y + h, fill=BG_TABLE, outline="#454d55")
        cv.create_text(x + 12, y + 14, text=title, anchor="w", fill=CL_TXT,
                       font=("TkDefaultFont", 11, "bold"))
        cols = min(n, max(3, int(w // 150)))
        rows = (n + cols - 1) // cols
        cw = w / cols
        chh = (h - 30) / rows
        for i in range(n):
            r, c = divmod(i, cols)
            cx = x + cw * (c + 0.5)
            cy = y + 30 + chh * (r + 0.5)
            self.slots[(station, i)] = (cx, cy, cw - 10, chh - 8)
            key = None
            for k, _ko, _en, st, ix, _pr in PARTS:
                if st == station and ix == i:
                    key = k
            filled = key and self.rig.has(key)
            cv.create_rectangle(cx - cw / 2 + 5, cy - chh / 2 + 4,
                                cx + cw / 2 - 5, cy + chh / 2 - 4,
                                fill="#242a30" if filled else "#20252a",
                                outline="#5f6a74" if filled else "#3d444b",
                                dash=() if filled else (3, 3))
            if filled:
                draw_icon(cv, key, cx, cy - 6, min(0.9, chh / 105), "st")
                cv.create_text(cx, cy + chh / 2 - 14, text=part_name(key),
                               fill=CL_DIM, font=("TkDefaultFont", 8))
            else:
                cv.create_text(cx, cy, text=T("빈 자리 %d", "seat %d") % (i + 1),
                               fill="#4d555d", font=("TkDefaultFont", 9))

# ============================================================================
#  SECTION 4 --- Bench tab
# ============================================================================

#  world layout (arbitrary units, 1 unit ~ 1 px at zoom 1)
WX_LASER = 400.0
WX_POL1 = 520.0
WX_TABLE = 700.0
WX_POL2 = 862.0
WX_PD = 1000.0
WX_SCREEN = 1082.0
W_RAIL_Y = 0.0
TABLE_R = 92.0
ARM_R = 214.0


class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.rig = app.rig
        self.zoom = 0.62
        self.ox, self.oy = 0.0, 0.0
        self._fit_done = False
        self._pan = None
        self.fan_phase = 0.0
        self.sensor_btns = {}
        self.msg, self.msg_t = "", 0.0
        self._dmm_txt = "0.00"

        # ---------------- canvas ----------------------------------------
        self.cv = tk.Canvas(self, bg=BG_LAB, highlightthickness=0)
        self.cv.pack(fill="both", expand=True, side="top")
        self.cv.bind("<Configure>", lambda e: self.fit())
        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_drag)
        self.cv.bind("<ButtonRelease-1>", lambda e: setattr(self, "_pan", None))
        self.cv.bind("<MouseWheel>", self.on_wheel)
        self.cv.bind("<Button-4>", lambda e: self.on_wheel(e, 120))
        self.cv.bind("<Button-5>", lambda e: self.on_wheel(e, -120))

        # ---------------- control strip ---------------------------------
        bar = ttk.Frame(self)
        bar.pack(fill="x", side="bottom", padx=6, pady=6)
        for c in range(5):
            bar.columnconfigure(c, weight=1)
        self._build_sensor(bar, 0)
        self._build_vessel(bar, 1)
        self._build_dmm(bar, 2)
        self._build_optics(bar, 3)
        self._build_clock(bar, 4)

    # ==================================================================
    #  control panels
    # ==================================================================
    def _build_sensor(self, bar, col):
        f = ttk.LabelFrame(bar, text=T("CO\u2082 농도 센서", "CO2 sensor"))
        f.grid(row=0, column=col, sticky="nsew", padx=3)
        self.scv = tk.Canvas(f, width=272, height=196, bg="#1b1f24",
                             highlightthickness=0)
        self.scv.pack(padx=4, pady=4)
        self.scv.bind("<Button-1>", self.on_sensor_click)
        self.usb_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text=T("USB로 보조배터리에 연결", "USB to power bank"),
                        variable=self.usb_var, command=self.toggle_usb).pack(anchor="w",
                                                                            padx=6, pady=(0, 4))

    def _build_vessel(self, bar, col):
        f = ttk.LabelFrame(bar, text=T("A. 용기 조작", "A. vessel"))
        f.grid(row=0, column=col, sticky="nsew", padx=3)
        self.v_clamp = [tk.BooleanVar(value=True), tk.BooleanVar(value=True)]
        for i in range(2):
            ttk.Checkbutton(f, text=T("연결관 %d 클램프 잠금", "clamp tube %d") % (i + 1),
                            variable=self.v_clamp[i],
                            command=lambda i=i: self.rig.set_clamp(i, self.v_clamp[i].get())
                            ).pack(anchor="w", padx=6)
        self.v_lid = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text=T("뚜껑 닫음", "lid on"), variable=self.v_lid,
                        command=lambda: self.rig.set_lid(self.v_lid.get())
                        ).pack(anchor="w", padx=6)
        self.v_batt = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text=T("마지막 배터리 끼움", "insert last cell"),
                        variable=self.v_batt,
                        command=lambda: self.rig.set_battery(self.v_batt.get())
                        ).pack(anchor="w", padx=6)
        self.v_fi = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text=T("내부 팬 ON", "inner fan ON"), variable=self.v_fi,
                        command=lambda: self.rig.set_fan("fan_in", self.v_fi.get())
                        ).pack(anchor="w", padx=6)
        self.v_fo = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text=T("외부 팬 ON", "outer fan ON"), variable=self.v_fo,
                        command=lambda: self.rig.set_fan("fan_out", self.v_fo.get())
                        ).pack(anchor="w", padx=6)
        ttk.Separator(f).pack(fill="x", pady=3)
        ttk.Button(f, text=T("숨을 불어넣기", "exhale into vessel"),
                   command=self.do_exhale).pack(fill="x", padx=6, pady=1)
        ttk.Button(f, text=T("한쪽 관으로 빨아내기", "suck air out"),
                   command=self.do_suck).pack(fill="x", padx=6, pady=1)
        ttk.Button(f, text=T("뚜껑 열고 팬으로 환기", "lid off + fan purge"),
                   command=self.do_purge).pack(fill="x", padx=6, pady=1)
        ttk.Button(f, text=T("자로 용기 재기", "measure vessel with ruler"),
                   command=self.do_ruler).pack(fill="x", padx=6, pady=(6, 4))

    def _build_dmm(self, bar, col):
        f = ttk.LabelFrame(bar, text=T("멀티미터 (단락 전류)", "multimeter (short-circuit current)"))
        f.grid(row=0, column=col, sticky="nsew", padx=3)
        self.mcv = tk.Canvas(f, width=196, height=150, bg="#1b1f24",
                             highlightthickness=0)
        self.mcv.pack(padx=4, pady=4)
        self.rng = tk.IntVar(value=0)
        for i, rr in enumerate(Multimeter.RANGES):
            nm = rr[0]
            ttk.Radiobutton(f, text=nm, value=i, variable=self.rng,
                            command=lambda: setattr(self.rig.dmm, "range_i", self.rng.get())
                            ).pack(anchor="w", padx=6)

    def _build_optics(self, bar, col):
        f = ttk.LabelFrame(bar, text=T("B / C. 광학 벤치", "B / C. optical bench"))
        f.grid(row=0, column=col, sticky="nsew", padx=3)
        self.o_laser = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text=T("레이저 ON", "laser ON"), variable=self.o_laser,
                        command=lambda: setattr(self.rig, "laser_on", self.o_laser.get())
                        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=6)

        self.e_table = self._angle_row(f, 1, T("회전대 눈금", "table scale"),
                                       lambda v: setattr(self.rig, "table_deg", v),
                                       lambda: self.rig.table_deg)
        self.e_arm = self._angle_row(f, 2, T("검출기 팔", "detector arm"),
                                     lambda v: setattr(self.rig, "arm_deg", v),
                                     lambda: self.rig.arm_deg)
        self.e_p1 = self._angle_row(f, 3, T("편광판 1", "polariser 1"),
                                    lambda v: setattr(self.rig, "pol1_deg", v),
                                    lambda: self.rig.pol1_deg)
        self.e_p2 = self._angle_row(f, 4, T("편광판 2", "polariser 2"),
                                    lambda v: setattr(self.rig, "pol2_deg", v),
                                    lambda: self.rig.pol2_deg)

        self.o_mount = tk.StringVar(value="rail")
        mf = ttk.Frame(f)
        mf.grid(row=5, column=0, columnspan=3, sticky="w", padx=6, pady=(4, 0))
        ttk.Label(mf, text=T("광다이오드 위치:", "photodiode:")).pack(side="left")
        ttk.Radiobutton(mf, text=T("레일(투과)", "rail (transmit)"), value="rail",
                        variable=self.o_mount, command=self.set_mount).pack(side="left")
        ttk.Radiobutton(mf, text=T("팔(반사)", "arm (reflect)"), value="arm",
                        variable=self.o_mount, command=self.set_mount).pack(side="left")
        bf = ttk.Frame(f)
        bf.grid(row=6, column=0, columnspan=3, sticky="we", padx=6, pady=(4, 4))
        ttk.Button(bf, text=T("막 뒤집기", "flip membrane"),
                   command=self.flip_face).pack(side="left", expand=True, fill="x")
        self.o_block = tk.BooleanVar(value=False)
        ttk.Checkbutton(bf, text=T("빔 차단", "block beam"), variable=self.o_block,
                        command=lambda: setattr(self.rig, "beam_block", self.o_block.get())
                        ).pack(side="left", padx=4)
        ttk.Button(f, text=T("\u0394n(p) 그래프 (문제지 제공)", "dn(p) plot (given)"),
                   command=self.app.show_chart).grid(row=7, column=0, columnspan=3,
                                                     sticky="we", padx=6, pady=(0, 4))

    def _angle_row(self, f, row, label, setter, getter):
        ttk.Label(f, text=label).grid(row=row, column=0, sticky="w", padx=(6, 2))
        var = tk.StringVar(value="%.2f" % getter())
        ent = ttk.Entry(f, textvariable=var, width=9, justify="right")
        ent.grid(row=row, column=1, sticky="w")

        def commit(*_a):
            try:
                setter(float(var.get()))
            except ValueError:
                pass
            var.set("%.2f" % getter())
            self.redraw()

        def bump(d):
            setter(getter() + d)
            var.set("%.2f" % getter())
            self.redraw()

        ent.bind("<Return>", commit)
        ent.bind("<FocusOut>", commit)
        ent.bind("<MouseWheel>",
                 lambda e: bump((0.05 if e.state & 0x0001 else 1.0) *
                                (1 if e.delta > 0 else -1)))
        ent.bind("<Button-4>", lambda e: bump(0.05 if e.state & 0x0001 else 1.0))
        ent.bind("<Button-5>", lambda e: bump(-(0.05 if e.state & 0x0001 else 1.0)))
        bb = ttk.Frame(f)
        bb.grid(row=row, column=2, sticky="w")
        for txt, d in (("\u25c0\u25c0", -1.0), ("\u25c0", -0.05),
                       ("\u25b6", 0.05), ("\u25b6\u25b6", 1.0)):
            ttk.Button(bb, text=txt, width=3,
                       command=lambda d=d: bump(d)).pack(side="left")
        return var

    def _build_clock(self, bar, col):
        f = ttk.LabelFrame(bar, text=T("시간", "clock"))
        f.grid(row=0, column=col, sticky="nsew", padx=3)
        self.ts = tk.DoubleVar(value=1.0)
        for v, lab in ((1.0, "\u00d71"), (10.0, "\u00d710"), (60.0, "\u00d760"),
                       (200.0, "\u00d7200"), (600.0, "\u00d7600")):
            ttk.Radiobutton(f, text=T("시간 배속 ", "time ") + lab, value=v,
                            variable=self.ts,
                            command=lambda: setattr(self.rig, "time_scale", self.ts.get())
                            ).pack(anchor="w", padx=6)
        self.lbl_clock = ttk.Label(f, text="", font=("Courier", 10))
        self.lbl_clock.pack(anchor="w", padx=6, pady=(6, 2))
        self.lbl_msg = ttk.Label(f, text="", wraplength=190, foreground="#c79a4a")
        self.lbl_msg.pack(anchor="w", padx=6)
        ttk.Label(f, text=T("휠: 확대/축소 · 회전대 위에서는 각도\n"
                            "Shift+휠: 미세 조정 · 드래그: 이동",
                            "wheel: zoom, or angle over the table\n"
                            "shift+wheel: fine  ·  drag: pan"),
                  font=("TkDefaultFont", 7), foreground=CL_DIM).pack(anchor="w",
                                                                     padx=6, pady=(8, 2))

    # ==================================================================
    #  actions
    # ==================================================================
    def note(self, s):
        self.msg, self.msg_t = s, time.time()

    def toggle_usb(self):
        if self.usb_var.get() and not (self.rig.has("sensor") and self.rig.has("powerbank")):
            self.usb_var.set(False)
            self.note(T("센서와 보조배터리를 먼저 설치하시오.",
                        "Install the sensor and the power bank first."))
            return
        self.rig.set_usb(self.usb_var.get())

    def do_exhale(self):
        if not self.rig.has("vessel"):
            return self.note(T("용기가 없다.", "No vessel."))
        if not self.rig.has("tubes") and self.rig.cell.lid_on:
            return self.note(T("연결관이 없어 불어넣을 수 없다.", "No tube to blow through."))
        if self.rig.exhale(0.9):
            self.note(T("용기 안으로 숨을 불어넣었다. (날숨의 CO\u2082는 약 4 %)",
                        "Exhaled into the vessel (breath is ~4 % CO2)."))
        else:
            self.note(T("클램프가 둘 다 잠겨 있어 공기가 들어가지 않는다.",
                        "Both clamps are shut -- the air has nowhere to go."))

    def do_suck(self):
        if self.rig.purge_suck():
            self.note(T("한쪽 관으로 빨아내고 다른 관으로 실내 공기가 들어왔다.",
                        "Sucked out through one tube, room air entered the other."))
        else:
            self.note(T("먼저 클램프를 열어야 한다.", "Open a clamp first."))

    def do_purge(self):
        if self.rig.purge_fan():
            self.note(T("뚜껑을 열고 팬으로 실내 공기를 불어 넣었다.",
                        "Lid off, fan blew room air through."))
        else:
            self.note(T("뚜껑을 열고 팬을 켜야 한다.", "Take the lid off and switch a fan on."))

    def do_ruler(self):
        if not (self.rig.has("vessel") and self.rig.has("rulers")):
            return self.note(T("용기와 자가 있어야 한다.", "Vessel and rulers needed."))
        L, D = self.rig.measure_vessel()
        self.note(T("자 눈금: 안쪽 길이 %.1f mm, 안지름 %.1f mm",
                    "ruler: inner length %.1f mm, inner diameter %.1f mm") % (L, D))

    def set_mount(self):
        self.rig.det_mount = self.o_mount.get()
        self.redraw()

    def flip_face(self):
        if not self.rig.has("stage"):
            return self.note(T("회전대가 없다.", "No rotary table."))
        self.rig.face = 1 - self.rig.face
        self.note(T("막을 지지대에서 빼내 앞뒤를 바꾸어 끼웠다. (현재 %s면)",
                    "Membrane taken out and turned round (face %s).")
                  % ("A" if self.rig.face == 0 else "B"))

    # ---- CO2 sensor keypad -------------------------------------------
    def on_sensor_click(self, e):
        for name, (x0, y0, x1, y1) in self.sensor_btns.items():
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                s = self.rig.sensor
                if name == "select":
                    s.press_select()
                elif name == "rst":
                    s.press_rst()
                elif name == "up":
                    s.press_up()
                elif name == "down":
                    s.press_down()
                else:
                    self.note(T("LEFT / RIGHT 버튼은 쓰지 않는다.",
                                "LEFT and RIGHT are not used."))
                return

    # ---- canvas navigation -------------------------------------------
    def fit(self):
        if self._fit_done:
            return
        w = self.cv.winfo_width()
        if w < 50:
            return
        self.zoom = max(0.28, min(0.9, w / 1560.0))
        self.ox = w / 2 - 470 * self.zoom
        self.oy = self.cv.winfo_height() / 2
        self._fit_done = True

    def w2s(self, x, y):
        return self.ox + x * self.zoom, self.oy + y * self.zoom

    def s2w(self, x, y):
        return (x - self.ox) / self.zoom, (y - self.oy) / self.zoom

    def on_press(self, e):
        self._pan = (e.x, e.y, self.ox, self.oy)

    def on_drag(self, e):
        if self._pan:
            x0, y0, ox, oy = self._pan
            self.ox = ox + (e.x - x0)
            self.oy = oy + (e.y - y0)

    def on_wheel(self, e, delta=None):
        d = delta if delta is not None else e.delta
        fine = bool(e.state & 0x0001)
        wx, wy = self.s2w(e.x, e.y)
        if self.rig.has("stage"):
            r = math.hypot(wx - WX_TABLE, wy - W_RAIL_Y)
            if r <= TABLE_R:
                self.rig.table_deg += (0.05 if fine else 1.0) * (1 if d > 0 else -1)
                self.e_table.set("%.2f" % self.rig.table_deg)
                return
            if ARM_R * 0.90 <= r <= ARM_R * 1.35:
                self.rig.arm_deg += (0.05 if fine else 1.0) * (1 if d > 0 else -1)
                self.e_arm.set("%.2f" % self.rig.arm_deg)
                return
        k = 1.12 if d > 0 else 1 / 1.12
        nz = max(0.18, min(3.4, self.zoom * k))
        k = nz / self.zoom
        self.zoom = nz
        self.ox = e.x - (e.x - self.ox) * k
        self.oy = e.y - (e.y - self.oy) * k

    # ==================================================================
    #  per-frame update
    # ==================================================================
    def tick(self, dt_real):
        self._dmm_txt = self.rig.dmm_text()
        if self.rig.cell.fan_in or self.rig.cell.fan_out:
            self.fan_phase = (self.fan_phase + 900 * dt_real) % 360
        self.redraw()
        self.draw_sensor()
        self.draw_dmm()
        t = self.rig.sim_time
        self.lbl_clock.config(text=T("경과 %d:%02d:%02d", "elapsed %d:%02d:%02d")
                              % (int(t) // 3600, (int(t) // 60) % 60, int(t) % 60))
        self.lbl_msg.config(text=self.msg if time.time() - self.msg_t < 8 else "")

    # ---- instrument faces --------------------------------------------
    def draw_sensor(self):
        cv = self.scv
        cv.delete("all")
        W, H = 272, 196
        rrect(cv, 8, 6, W - 8, H - 6, 10, fill="#2f353c", outline="#585f68")
        s = self.rig.sensor
        on = s.powered
        rrect(cv, 22, 18, W - 22, 86, 5,
              fill=CL_LCD if on else "#4c5744", outline="#2f3a26")
        l1, l2, l3 = s.display()
        if on:
            cv.create_text(30, 32, text=l1, anchor="w", fill="#1b2412",
                           font=("Courier", 10, "bold"))
            cv.create_text(30, 56, text=l2, anchor="w", fill="#1b2412",
                           font=("Courier", 15, "bold"))
            cv.create_text(30, 76, text=l3, anchor="w", fill="#1b2412",
                           font=("Courier", 9))
        self.sensor_btns = {}
        defs = [("select", "SELECT", 26, 100, 78, 30),
                ("rst", "RST", 112, 100, 52, 30),
                ("left", "LEFT", 174, 100, 52, 30),
                ("up", "UP", 62, 138, 52, 30),
                ("down", "DOWN", 122, 138, 60, 30),
                ("right", "RIGHT", 190, 138, 56, 30)]
        for name, lab, x, y, w, h in defs:
            rrect(cv, x, y, x + w, y + h, 5, fill="#454d56", outline="#6e7680")
            cv.create_text(x + w / 2, y + h / 2, text=lab, fill="#dfe4ea",
                           font=("TkDefaultFont", 8, "bold"))
            self.sensor_btns[name] = (x, y, x + w, y + h)
        cv.create_oval(W - 34, 176, W - 26, 184,
                       fill="#6fd36f" if on else "#3a3f45", outline="")

    def draw_dmm(self):
        cv = self.mcv
        cv.delete("all")
        art_multimeter(cv, 98, 76, 0.72, "m", self._dmm_txt,
                       self.rig.dmm.unit(), True)
        if not self.rig.dmm.connected:
            cv.create_text(98, 142, text=T("전선 미연결", "not wired"),
                           fill="#c79a4a", font=("TkDefaultFont", 8))

    # ==================================================================
    #  bench canvas
    # ==================================================================
    def redraw(self):
        cv = self.cv
        cv.delete("all")
        z = self.zoom
        self.fit()

        cv.create_text(12, 14, anchor="w", fill=CL_DIM,
                       font=("TkDefaultFont", 9),
                       text=T("A. 확산 실험대 (측면도)          B / C. 광학 벤치 (평면도)",
                              "A. diffusion station (elevation)     B / C. optical bench (plan)"))

        # ------------------------------------------------ station A ----
        if self.rig.has("vessel"):
            x, y = self.w2s(0, 0)
            art_vessel(cv, x, y, z * 1.55, "A",
                       lid=self.rig.cell.lid_on,
                       clamp=tuple(self.rig.cell.clamp),
                       have_tubes=self.rig.has("tubes"),
                       have_sensor=self.rig.has("sensor"),
                       have_fan=self.rig.has("fan_in"),
                       fan_ang=self.fan_phase if self.rig.cell.fan_in else 0.0)
            if self.rig.has("fan_out"):
                fx, fy = self.w2s(0, -170)
                art_fan(cv, fx, fy, 34 * z, self.fan_phase if self.rig.cell.fan_out else 0.0,
                        "A")
                if self.rig.cell.fan_out:
                    for k in range(-2, 3):
                        ax, ay = self.w2s(k * 16, -128)
                        cv.create_line(ax, ay, ax, ay + 34 * z, fill="#5f7f95",
                                       arrow="last", width=max(1, int(1.6 * z)))
                cv.create_text(fx, fy - 46 * z,
                               text=T("외부 팬", "outer fan"), fill=CL_DIM,
                               font=("TkDefaultFont", max(6, int(9 * z))))
            if self.rig.has("fan_in") or self.rig.has("fan_out"):
                bx, by = self.w2s(178, 96)
                art_battery_block(cv, bx, by, z * 1.5, "A", self.rig.batt_inserted)
            if self.rig.has("powerbank"):
                px, py = self.w2s(-232, 132)
                art_powerbank(cv, px, py, z * 1.5, "A", usb=self.rig.usb_plugged)
            if self.rig.has("pads"):
                gx, gy = self.w2s(182, 152)
                art_gluepads(cv, gx, gy, z * 1.4, "A")
            if self.rig.has("rulers"):
                rx, ry = self.w2s(-150, 190)
                art_ruler(cv, rx, ry, z * 1.4, "A")
        else:
            x, y = self.w2s(0, 0)
            cv.create_text(x, y, text=T("(확산 실험대가 비어 있다)", "(diffusion station empty)"),
                           fill="#4d555d", font=("TkDefaultFont", 11))

        # ------------------------------------------------ optical ------
        if not self.rig.has("bench"):
            x, y = self.w2s(WX_TABLE, 0)
            cv.create_text(x, y, text=T("(광학 벤치가 비어 있다)", "(optical bench empty)"),
                           fill="#4d555d", font=("TkDefaultFont", 11))
            return

        alpha = self.rig.true_alpha()
        psi_spec = 180.0 - 2.0 * abs(alpha)
        psi_draw = psi_spec if alpha >= 0 else -psi_spec
        laser_on = self.rig.laser_on and self.rig.has("laser") and not self.rig.beam_block
        tx, ty = self.w2s(WX_TABLE, W_RAIL_Y)

        # --- 1. the rail, behind everything -------------------------
        rx0, ry = self.w2s(WX_LASER - 110, W_RAIL_Y)
        rx1, _ = self.w2s(WX_SCREEN + 70, 0)
        art_rail(cv, rx0, rx1, ry, z * 1.35, "O")

        # --- 2. the swing arm and its scale -------------------------
        has_pd_arm = self.rig.has("pd") and self.rig.det_mount == "arm"
        if self.rig.has("stage"):
            art_arm(cv, tx, ty, ARM_R * z, self.rig.arm_deg, z * 1.30, "O", False)

        # --- 3. the beams -------------------------------------------
        tfr = 0.0
        if laser_on and self.rig.has("stage"):
            aa = math.radians(min(87.0, abs(alpha)))
            fr = self.rig.optics.reflectance(aa, self.rig.face)
            tfr = self.rig.optics.transmittance(
                aa, self.rig.has("pol1"), self.rig.has("pol2"),
                self.rig.pol1_deg - self.rig.truth.pol_zero[0],
                self.rig.pol2_deg - self.rig.truth.pol_zero[1])
        if laser_on:
            bx, by = self.w2s(WX_LASER + 42, W_RAIL_Y)
            cv.create_line(bx, by, tx, ty, fill=beam_colour(0.95),
                           width=max(1, int(2.4 * z)))
        if laser_on and self.rig.has("stage"):
            ar = math.radians(psi_draw)
            for k in (-11, -6, 6, 11):
                ah = math.radians(psi_draw + k)
                cv.create_line(tx, ty, tx + ARM_R * 0.85 * z * math.cos(ah),
                               ty - ARM_R * 0.85 * z * math.sin(ah),
                               fill=beam_colour(0.05), width=1)
            cv.create_line(tx, ty,
                           tx + ARM_R * 1.30 * z * math.cos(ar),
                           ty - ARM_R * 1.30 * z * math.sin(ar),
                           fill=beam_colour(fr / 0.10), width=max(1, int(2.0 * z)))
            sx, sy = self.w2s(WX_SCREEN + 44, W_RAIL_Y)
            cv.create_line(tx, ty, sx, sy, fill=beam_colour(tfr),
                           width=max(1, int(2.0 * z)))

        # --- 4. the components sitting on the rail ------------------
        if self.rig.has("laser"):
            lx, ly = self.w2s(WX_LASER, W_RAIL_Y)
            art_laser(cv, lx, ly, z * 1.40, "O", self.rig.laser_on)
        if self.rig.has("pol1"):
            x, y = self.w2s(WX_POL1, W_RAIL_Y)
            art_polarizer(cv, x, y, z * 1.40, "O", self.rig.pol1_deg, "P1")
        if self.rig.has("stage"):
            art_rotary_table(cv, tx, ty, TABLE_R * z, "O",
                             self.rig.table_deg, self.rig.face, z * 1.30)
            if has_pd_arm:
                a = math.radians(self.rig.arm_deg)
                ex, ey = tx + ARM_R * z * math.cos(a), ty - ARM_R * z * math.sin(a)
                cv.create_line(tx, ty, ex, ey, fill="#6a727a",
                               width=max(3, int(9 * z)))
                art_photodiode(cv, ex, ey, z * 1.45, "O", self.rig.arm_deg + 180.0)
        if self.rig.has("pol2"):
            x, y = self.w2s(WX_POL2, W_RAIL_Y)
            art_polarizer(cv, x, y, z * 1.40, "O", self.rig.pol2_deg, "P2")
        if self.rig.has("pd") and self.rig.det_mount == "rail":
            x, y = self.w2s(WX_PD, W_RAIL_Y)
            art_photodiode(cv, x, y, z * 1.45, "O", 180.0)
        if self.rig.has("screen"):
            x, y = self.w2s(WX_SCREEN, W_RAIL_Y)
            spot = (min(1.0, tfr), 0.0) if (laser_on and self.rig.has("stage")) else None
            art_screen(cv, x, y, z * 1.45, "O", spot)

        # --- 5. the multimeter, on the table in front of the rail ---
        if self.rig.has("dmm"):
            x, y = self.w2s(WX_LASER - 20, W_RAIL_Y + 268)
            art_multimeter(cv, x, y, z * 1.15, "O",
                           self._dmm_txt, self.rig.dmm.unit(), True)
            if self.rig.has("wires") and self.rig.has("pd"):
                if self.rig.det_mount == "arm":
                    a = math.radians(self.rig.arm_deg)
                    ex = tx + ARM_R * z * math.cos(a)
                    ey = ty - ARM_R * z * math.sin(a)
                else:
                    ex, ey = self.w2s(WX_PD, W_RAIL_Y)
                mid = self.w2s(WX_TABLE, W_RAIL_Y + 320)
                for sgn, col in ((-1, "#d8493a"), (1, "#2a2f35")):
                    cv.create_line(x + sgn * 11 * z, y + 74 * z,
                                   mid[0], mid[1] + sgn * 8 * z,
                                   ex + sgn * 6 * z, ey + 14 * z,
                                   fill=col, width=max(1, int(1.7 * z)), smooth=True)

# ============================================================================
#  SECTION 5 --- application shell
# ============================================================================

class ChartWindow(tk.Toplevel):
    """The dn(p) calibration plot printed on the EuPhO 2018 problem sheet."""

    def __init__(self, master):
        tk.Toplevel.__init__(self, master)
        self.title(T("\u0394n(p) — 문제지 제공 그래프", "dn(p) — plot given in the problem"))
        self.configure(bg="white")
        self.cv = tk.Canvas(self, width=760, height=540, bg="white",
                            highlightthickness=0)
        self.cv.pack(padx=8, pady=8)
        self.readout = tk.Label(self, bg="white", fg="#333",
                                text=T("그래프 위에서 마우스를 움직이면 눈금을 읽을 수 있다.",
                                       "Move the pointer over the plot to read the scales."))
        self.readout.pack(pady=(0, 8))
        self.cv.bind("<Motion>", self.on_motion)
        self.draw()

    L, Rr, Tt, B = 78, 726, 26, 478

    def px(self, p):
        return self.L + (self.Rr - self.L) * (p / 0.50)

    def py(self, dn):
        return self.B - (self.B - self.Tt) * (dn / 0.10)

    def draw(self):
        cv = self.cv
        cv.delete("all")
        for k in range(51):
            x = self.px(k * 0.01)
            cv.create_line(x, self.Tt, x, self.B,
                           fill="#dcdcdc" if k % 5 else "#9a9a9a")
        for k in range(51):
            y = self.py(k * 0.002)
            cv.create_line(self.L, y, self.Rr, y,
                           fill="#dcdcdc" if k % 5 else "#9a9a9a")
        cv.create_rectangle(self.L, self.Tt, self.Rr, self.B, outline="black", width=2)
        for k in range(11):
            p = k * 0.05
            cv.create_text(self.px(p), self.B + 16, text="%.2f" % p,
                           fill="black", font=("TkDefaultFont", 9))
            dn = k * 0.01
            cv.create_text(self.L - 12, self.py(dn), text="%.2f" % dn, anchor="e",
                           fill="black", font=("TkDefaultFont", 9))
        cv.create_text(self.L + 22, self.Tt + 20, text="\u0394n", fill="black",
                       font=("Times", 20, "italic"))
        cv.create_text((self.L + self.Rr) / 2, self.B + 42, text="p", fill="black",
                       font=("Times", 20, "italic"))
        pts = []
        for i in range(501):
            p = i * 0.001
            pts += [self.px(p), self.py(dn_of_p(p))]
        cv.create_line(*pts, fill="black", width=2, smooth=True)

    def on_motion(self, e):
        if not (self.L <= e.x <= self.Rr and self.Tt <= e.y <= self.B):
            return
        p = (e.x - self.L) / (self.Rr - self.L) * 0.50
        dn = (self.B - e.y) / (self.B - self.Tt) * 0.10
        self.readout.config(text="p = %.3f      \u0394n = %.4f" % (p, dn))


class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.title(APP_TITLE + "   —   HaslaLab")
        self.geometry("1500x920")
        self.minsize(1180, 760)
        self.configure(bg=BG_LAB)
        try:
            ttk.Style(self).theme_use("clam")
        except tk.TclError:
            pass
        self._style()

        self.rig = Rig(seed)
        self.chart = None

        head = ttk.Frame(self)
        head.pack(fill="x", padx=10, pady=(8, 0))
        ttk.Label(head, text=T("EuPhO 2018 실험 — 다공성 막 (양극산화 알루미늄 산화물)",
                               "EuPhO 2018 Experiment — porous anodic aluminium oxide"),
                  font=("TkDefaultFont", 13, "bold")).pack(side="left")
        ttk.Label(head, text=T("시료 번호 %d", "sample no. %d") % (self.rig.truth.seed % 100000),
                  foreground=CL_DIM).pack(side="right")
        ttk.Button(head, text=T("새 시료", "new sample"),
                   command=self.new_sample).pack(side="right", padx=8)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.tab_a = AssemblyTab(self.nb, self)
        self.tab_b = BenchTab(self.nb, self)
        self.nb.add(self.tab_a, text=T("  조립  ", "  assembly  "))
        self.nb.add(self.tab_b, text=T("  실험대  ", "  bench  "))

        self._last = time.time()
        self.after(33, self.loop)

    def _style(self):
        st = ttk.Style(self)
        st.configure(".", background=BG_LAB, foreground=CL_TXT)
        st.configure("TFrame", background=BG_LAB)
        st.configure("TLabel", background=BG_LAB, foreground=CL_TXT)
        st.configure("TLabelframe", background=BG_LAB, bordercolor="#454d55")
        st.configure("TLabelframe.Label", background=BG_LAB, foreground="#c3cad2")
        st.configure("TCheckbutton", background=BG_LAB, foreground=CL_TXT)
        st.configure("TRadiobutton", background=BG_LAB, foreground=CL_TXT)
        st.configure("TButton", background="#39404a", foreground=CL_TXT)
        st.map("TButton", background=[("active", "#4a525c")])
        st.configure("TNotebook", background=BG_LAB)
        st.configure("TNotebook.Tab", background="#2c3138", foreground=CL_TXT)
        st.map("TNotebook.Tab", background=[("selected", "#454d55")])
        st.configure("TEntry", fieldbackground="#2c3138", foreground=CL_TXT)

    def show_chart(self):
        if self.chart is not None and self.chart.winfo_exists():
            self.chart.lift()
            return
        self.chart = ChartWindow(self)

    def new_sample(self):
        seed = random.randrange(1, 10 ** 9)
        self.rig = Rig(seed)
        self.tab_a.rig = self.rig
        self.tab_b.rig = self.rig
        self.tab_b.usb_var.set(False)
        self.tab_b.v_batt.set(False)
        self.tab_b.v_fi.set(False)
        self.tab_b.v_fo.set(False)
        self.tab_b.v_lid.set(True)
        self.tab_b.o_laser.set(False)
        for i in range(2):
            self.tab_b.v_clamp[i].set(True)
        self.tab_a.note(T("새 시료를 받았다. 처음부터 조립하시오.",
                          "A new sample has arrived. Assemble from scratch."))
        self.tab_a.redraw()
        self.title(APP_TITLE + "   —   HaslaLab")

    def loop(self):
        now = time.time()
        dt = min(0.25, now - self._last)
        self._last = now
        try:
            self.rig.advance(dt)
            if self.nb.index(self.nb.select()) == 1:
                self.tab_b.tick(dt)
        except Exception:
            import traceback
            traceback.print_exc()
        self.after(33, self.loop)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=APP_TITLE)
    ap.add_argument("--seed", type=int, default=None,
                    help="fix the hidden sample parameters")
    ap.add_argument("--reference", action="store_true",
                    help="use the sample that reproduces the official answers")
    a = ap.parse_args()
    seed = 20180001 if a.reference else a.seed
    App(seed).mainloop()


if __name__ == "__main__":
    main()
