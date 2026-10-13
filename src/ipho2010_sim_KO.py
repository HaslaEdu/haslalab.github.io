#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  41st International Physics Olympiad  (IPhO 2010, Zagreb, Croatia)
  Experimental Problem 1 :  ELASTICITY OF SHEETS
  Experimental Problem 2 :  FORCES BETWEEN MAGNETS
  Virtual laboratory simulator  (both problems share one press and scale)
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    Only quantities that a real instrument would show are displayed: the
    balance display, the turn graduation on the press screw and the ruler.
    No forces, radii, bending rigidities, fitted slopes or hints are shown.
    All hidden true parameters (Young moduli, magnetisations, geometry,
    instrument offsets) are drawn from a per-session random generator.
    
    Physics is a forward model, never replayed data:
      - Problem 1: the exact planar elastica of a closed inextensible ring
        squeezed between two rigid plates (flat contact + free arc).
      - Problem 2: the magnetic surface-charge (Gilbert) model of a uniformly
        magnetised rod and ring, via the Hankel/Bessel form of the kernel.
"""

import math
import os
import random
import sys

# --------------------------------------------------------------------------
#  language
# --------------------------------------------------------------------------
LANG = "ko"          # the EN edition differs only in this line
for _a in sys.argv[1:]:
    if _a in ("--en", "--lang=en"):
        LANG = "en"
    elif _a in ("--ko", "--lang=ko"):
        LANG = "ko"


def T(ko, en):
    """Bilingual string helper."""
    return ko if LANG == "ko" else en


APP_TITLE = T(u"IPhO 2010 실험 I·II 가상실험실 — HaslaLab",
              u"IPhO 2010 Experiments I & II Virtual Lab — HaslaLab")

# =========================================================================
#  1.  numerical helpers
# =========================================================================


def gauss_legendre(n):
    """Gauss-Legendre nodes/weights on [-1, 1]."""
    xs, ws = [], []
    for i in range(1, n + 1):
        x = math.cos(math.pi * (i - 0.25) / (n + 0.5))
        dp = 1.0
        for _ in range(100):
            p0, p1 = 1.0, x
            for k in range(2, n + 1):
                p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
            dp = n * (x * p1 - p0) / (x * x - 1.0)
            dx = -p1 / dp
            x += dx
            if abs(dx) < 1e-15:
                break
        xs.append(x)
        ws.append(2.0 / ((1.0 - x * x) * dp * dp))
    return xs, ws


_G8X, _G8W = gauss_legendre(8)
_G6X, _G6W = gauss_legendre(6)


def quad8(f, a, b):
    h, m = 0.5 * (b - a), 0.5 * (b + a)
    return h * sum(w * f(m + h * x) for x, w in zip(_G8X, _G8W))


def quad_panels(f, a, b, npan):
    """composite 8-point Gauss on npan equal panels"""
    s = 0.0
    step = (b - a) / npan
    for i in range(npan):
        s += quad8(f, a + i * step, a + (i + 1) * step)
    return s


def bessj1(x):
    """Bessel function J1 (Numerical-Recipes rational approximation)."""
    ax = abs(x)
    if ax < 8.0:
        y = x * x
        p = x * (72362614232.0 + y * (-7895059235.0 + y * (242396853.1 + y * (
            -2972611.439 + y * (15704.48260 + y * (-30.16036606))))))
        q = (144725228442.0 + y * (2300535178.0 + y * (18583304.74 + y * (
            99447.43394 + y * (376.9991397 + y)))))
        return p / q
    z = 8.0 / ax
    y = z * z
    xx = ax - 2.356194491
    p = 1.0 + y * (0.183105e-2 + y * (-0.3516396496e-4 + y * (
        0.2457520174e-5 + y * (-0.240337019e-6))))
    q = 0.04687499995 + y * (-0.2002690873e-3 + y * (0.8449199096e-5 + y * (
        -0.88228987e-6 + y * 0.105787412e-6)))
    ans = math.sqrt(0.636619772 / ax) * (math.cos(xx) * p - z * math.sin(xx) * q)
    return ans if x > 0.0 else -ans


G_ACC = 9.81            # m/s^2, the value printed in the problem sheet
MU0 = 4.0e-7 * math.pi

# =========================================================================
#  2.  Problem 1 physics -- elastica of a ring pressed between two plates
# =========================================================================
#
#  A closed inextensible rod (the rolled foil, cross-section perimeter
#  2*pi*Rc, bending stiffness B = kappa * l) is squeezed between two rigid
#  parallel plates a distance h apart.
#
#  Along a free arc no distributed load acts, hence the internal force N is
#  constant; the symmetry condition k'=0 at the equator forces N_x = 0, so
#  N = (0, f) with f = F/2 (F = total press force).  The first integral of
#  the elastica equation B*k' = -N_y*cos(theta) reads
#
#        (B/2) k^2 = f * sin(phi) + (B/2) k0^2 ,      phi = -theta
#
#  with k0 the curvature where the arc leaves the plate.  Two regimes:
#
#   (a) h <= h_thr : a straight strip of the foil lies flat on each plate,
#       so k0 = 0 (curvature is continuous at the edge of contact) and
#            h/2 = sqrt(B/2f) * I1 ,  I1 = int_0^{pi/2} sqrt(sin phi) dphi
#       giving the closed form   F = 4 I1^2 B / h^2 .
#       The contact strip disappears when the quarter arc length
#            s = sqrt(B/2f) * I0 ,  I0 = int_0^{pi/2} dphi/sqrt(sin phi)
#       equals pi*Rc/2, i.e. at  h_thr = (pi/2)(I1/I0) 2 Rc = 1.4355 Rc,
#       i.e.  R0/Rc = 0.7177  --  the limit of the "stadium" approximation.
#
#   (b) h > h_thr : the ring touches each plate at a single line, k0 > 0,
#       and (f, k0) follow from arc length = pi*Rc/2 and drop = h/2.
#
#  The stadium approximation of the problem sheet gives F = 2 pi B / h^2,
#  which is 1/0.91389 times larger than the exact result -- see README.
# -------------------------------------------------------------------------
_U_MAX = math.sqrt(math.pi / 2.0)
I0_EL = quad_panels(lambda u: 2.0 * u / math.sqrt(math.sin(u * u)), 0.0, _U_MAX, 8)
I1_EL = quad_panels(lambda u: 2.0 * u * math.sin(u * u) / math.sqrt(math.sin(u * u)),
                    0.0, _U_MAX, 8)
H_THR = math.pi * I1_EL / I0_EL          # h_thr / Rc  = 1.43554
R0_RC_THR = 0.5 * H_THR                  # 0.71777
F_CONTACT = 4.0 * I1_EL * I1_EL          # F h^2 / B   = 5.74216
STADIUM_RATIO = F_CONTACT / (2.0 * math.pi)   # 0.91389


def _arc_int(f, k0):
    """(quarter arc length, vertical drop) for B = 1."""
    c = 2.0 * f
    k2 = k0 * k0

    def gl(u):
        return 2.0 * u / math.sqrt(c * math.sin(u * u) + k2)

    def gd(u):
        s = math.sin(u * u)
        return 2.0 * u * s / math.sqrt(c * s + k2)

    return quad_panels(gl, 0.0, _U_MAX, 6), quad_panels(gd, 0.0, _U_MAX, 6)


def elastica_force_hat(hh):
    """dimensionless press force  F Rc^2 / B  for plate gap hh = h/Rc."""
    if hh <= 0.0:
        return float("inf")
    if hh >= 2.0:
        return 0.0
    if hh <= H_THR:
        return F_CONTACT / (hh * hh)
    f = 0.5 * F_CONTACT / (hh * hh)
    k0 = 2.0 / hh
    for _ in range(60):
        L, D = _arc_int(f, k0)
        r1, r2 = L - 0.5 * math.pi, D - 0.5 * hh
        if abs(r1) < 1e-12 and abs(r2) < 1e-12:
            break
        df, dk = f * 1e-6 + 1e-13, k0 * 1e-6 + 1e-13
        L1, D1 = _arc_int(f + df, k0)
        L2, D2 = _arc_int(f, k0 + dk)
        a11, a21 = (L1 - L) / df, (D1 - D) / df
        a12, a22 = (L2 - L) / dk, (D2 - D) / dk
        det = a11 * a22 - a12 * a21
        if det == 0.0:
            break
        sf = -(r1 * a22 - a12 * r2) / det
        sk = -(a11 * r2 - r1 * a21) / det
        lam = 1.0
        while (f + lam * sf <= 1e-12 or k0 + lam * sk <= 0.0) and lam > 1e-8:
            lam *= 0.5
        f += lam * sf
        k0 += lam * sk
    return 2.0 * f


def elastica_outline(hh, nseg=44):
    """Closed cross-section outline (list of (x, y) in units of Rc) of the
    squeezed foil ring for plate gap hh = h/Rc.  Used only for drawing."""
    if hh >= 2.0:
        return [(math.cos(2 * math.pi * i / 72.0), math.sin(2 * math.pi * i / 72.0))
                for i in range(72)]
    if hh <= H_THR:
        f = 2.0 * I1_EL * I1_EL / (hh * hh)
        k0 = 0.0
        sf = I0_EL / math.sqrt(2.0 * f)
    else:
        F = elastica_force_hat(hh)
        f = 0.5 * F
        k0 = 2.0 / hh
        for _ in range(60):
            L, D = _arc_int(f, k0)
            r1, r2 = L - 0.5 * math.pi, D - 0.5 * hh
            if abs(r1) < 1e-12 and abs(r2) < 1e-12:
                break
            df, dk = f * 1e-6 + 1e-13, k0 * 1e-6 + 1e-13
            L1, D1 = _arc_int(f + df, k0)
            L2, D2 = _arc_int(f, k0 + dk)
            a11, a21 = (L1 - L) / df, (D1 - D) / df
            a12, a22 = (L2 - L) / dk, (D2 - D) / dk
            det = a11 * a22 - a12 * a21
            if det == 0.0:
                break
            sf = -(r1 * a22 - a12 * r2) / det
            sk = -(a11 * r2 - r1 * a21) / det
            lam = 1.0
            while (f + lam * sf <= 1e-12 or k0 + lam * sk <= 0.0) and lam > 1e-8:
                lam *= 0.5
            f += lam * sf
            k0 += lam * sk
        sf = 0.5 * math.pi
    c = max(0.0, 0.5 * math.pi - sf)
    # integrate the quarter arc in the variable u (phi = u^2)
    pts = [(c, 0.5 * hh)]
    x, y = c, 0.5 * hh
    du = _U_MAX / nseg
    for i in range(nseg):
        u0 = i * du
        # midpoint rule in u on each sub-step (smooth, adequate for drawing)
        for sub in (0.25, 0.75):
            u = u0 + du * sub
            phi = u * u
            dsdu = 2.0 * u / math.sqrt(2.0 * f * math.sin(phi) + k0 * k0)
            x += math.cos(phi) * dsdu * du * 0.5
            y -= math.sin(phi) * dsdu * du * 0.5
        pts.append((x, y))
    right = pts
    out = [p for p in right]
    out += [(p[0], -p[1]) for p in reversed(right[:-1])]
    out += [(-p[0], -p[1]) for p in right[1:]]
    out += [(-p[0], p[1]) for p in reversed(right[:-1])]
    return out


# =========================================================================
#  3.  Problem 2 physics -- rod magnet / ring magnet axial force
# =========================================================================
#
#  Uniformly magnetised bodies are replaced by their magnetic surface
#  charges (sigma = M.n).  For two coaxial charged discs / annuli a distance
#  d apart the axial repulsion is a single Hankel integral
#
#     K(d) = pi mu0 sigma1 sigma2 Int_0^inf k S1(k) S2(k) e^{-k d} dk ,
#     S_disc(k) = a J1(k a)/k ,
#     S_annulus(k) = [Ro J1(k Ro) - Ri J1(k Ri)]/k .
#
#  Because  Int_0^inf J1(kA)J1(kB)/k dk = B/(2A)  for B <= A, K(0) = 0
#  whenever the rod fits inside the hole, so the force stays continuous.
# -------------------------------------------------------------------------
class MagnetModel(object):
    def __init__(self, a, L, Ri, Ro, t, M_rod, M_ring,
                 kfine=20.0, npan=140, kmax=3000.0, nlog=80,
                 dmax=130.0, dstep=0.05):
        self.a, self.L, self.Ri, self.Ro, self.t = a, L, Ri, Ro, t
        self.M_rod, self.M_ring = M_rod, M_ring
        edges = [kfine * i / npan for i in range(npan + 1)]
        r = (kmax / kfine) ** (1.0 / nlog)
        e = kfine
        for _ in range(nlog):
            e *= r
            edges.append(e)
        ks, ws = [], []
        for i in range(len(edges) - 1):
            aa, bb = edges[i], edges[i + 1]
            hm, mm = 0.5 * (bb - aa), 0.5 * (bb + aa)
            for x, w in zip(_G6X, _G6W):
                ks.append(mm + hm * x)
                ws.append(w * hm)
        C = math.pi * MU0 * M_rod * M_ring * 1e-6      # mm^2 -> m^2
        self._k = ks
        self._w = []
        for k, w in zip(ks, ws):
            s1 = a * bessj1(k * a) / k
            s2 = (Ro * bessj1(k * Ro) - Ri * bessj1(k * Ri)) / k
            self._w.append(C * w * k * s1 * s2)
        self.dstep = dstep
        n = int(dmax / dstep) + 1
        tab = []
        for i in range(n):
            d = i * dstep
            s = 0.0
            for k, w in zip(ks, self._w):
                e = -k * d
                if e > -50.0:
                    s += w * math.exp(e)
            tab.append(s)
        self._tab = tab
        self.dmax = (n - 1) * dstep

    def K(self, d):
        d = abs(d)
        if d >= self.dmax:
            return 0.0
        x = d / self.dstep
        i = int(x)
        fr = x - i
        tb = self._tab
        if i == 0 or i >= len(tb) - 2:
            return tb[i] * (1.0 - fr) + tb[i + 1] * fr
        p0, p1, p2, p3 = tb[i - 1], tb[i], tb[i + 1], tb[i + 2]
        m1 = 0.5 * (p2 - p0)
        m2 = 0.5 * (p3 - p1)
        return (p1 + m1 * fr + (3.0 * (p2 - p1) - 2.0 * m1 - m2) * fr * fr
                + (2.0 * (p1 - p2) + m1 + m2) * fr ** 3)

    def force(self, z, orient=1):
        """Axial magnetic force on the rod magnet [N].  z [mm] is the
        rod-centre coordinate measured from the ring centre, positive into
        the cylinder.  orient = +1 parallel moments, -1 antiparallel."""
        L2, t2 = 0.5 * self.L, 0.5 * self.t
        tot = 0.0
        for zi, si in ((z + L2, 1.0), (z - L2, -1.0)):
            for zj, sj in ((t2, 1.0), (-t2, -1.0)):
                d = zi - zj
                if d != 0.0:
                    tot += si * sj * (1.0 if d > 0.0 else -1.0) * self.K(d)
        return orient * tot

    def equilibria(self, orient=1, zmin=-90.0, zmax=90.0, dz=0.05):
        """list of (z, stable?) -- used by the verification harness only."""
        out = []
        n = int((zmax - zmin) / dz)
        zp = zmin
        fp = self.force(zp, orient)
        for i in range(1, n + 1):
            zc = zmin + i * dz
            fc = self.force(zc, orient)
            if (fp < 0.0) != (fc < 0.0) and fp != fc:
                z0 = zp + dz * (-fp / (fc - fp))
                if not out or abs(z0 - out[-1][0]) > 0.5:
                    out.append((z0, fc < fp))
            zp, fp = zc, fc
        return out


# =========================================================================
#  4.  hidden truth  (randomised once per session)
# =========================================================================
#  Nothing in this class is ever displayed to the user.
# -------------------------------------------------------------------------
class Truth(object):
    def __init__(self, seed=None):
        if seed is None:
            seed = random.randrange(1, 10 ** 9)
        self.seed = int(seed)
        rng = random.Random(self.seed)
        self.rng = rng
        u = rng.uniform

        # ---- transparency foils ------------------------------------------
        # printed on the problem sheet: 210 x 297 mm, 200 um (blue),
        # 150 um (colourless).  The real sheets deviate slightly.
        self.foil_sheet = (210.0, 297.0)
        self.d_nom = {"blue": 200e-6, "clear": 150e-6}
        self.d_true = {"blue": 200e-6 * (1.0 + u(-0.006, 0.006)),
                       "clear": 150e-6 * (1.0 + u(-0.006, 0.006))}
        #  hidden Young moduli.  A student who analyses the data with the
        #  stadium approximation of the problem sheet recovers
        #  0.91389 * Y_true  (see the elastica discussion above), i.e.
        #  2.0 GPa and 2.5 GPa for the central values below.
        self.Y_true = {"blue": 2.188e9 * (1.0 + u(-0.045, 0.045)),
                       "clear": 2.735e9 * (1.0 + u(-0.045, 0.045))}
        self.nu = 1.0 / 3.0
        self.kappa_true = {}
        for k in ("blue", "clear"):
            d = self.d_true[k]
            self.kappa_true[k] = self.Y_true[k] * d ** 3 / (12.0 * (1.0 - self.nu ** 2))

        # ---- press / balance ---------------------------------------------
        self.pitch = 2.0 * (1.0 + u(-0.0012, 0.0012))     # mm per turn (true)
        self.backlash = u(0.05, 0.11)                     # mm
        self.compliance = u(0.8e-3, 2.0e-3)               # mm per N (frame)
        self.scale_offset = u(-0.6, 0.6)                  # g
        self.scale_noise = u(0.25, 0.45)                  # g rms
        self.scale_gain = 1.0 + u(-0.0015, 0.0015)
        self.scale_cap = 5000.0
        self.eye = u(0.18, 0.30)                          # ruler reading error, mm

        # ---- magnets ------------------------------------------------------
        self.rod_a = 2.5 * (1.0 + u(-0.02, 0.02))         # radius  [mm]
        self.rod_L = 30.0 * (1.0 + u(-0.025, 0.025))      # length  [mm]
        self.ring_Ri = 3.0 * (1.0 + u(-0.03, 0.03))
        self.ring_Ro = 11.0 * (1.0 + u(-0.035, 0.035))
        self.ring_t = 5.0 * (1.0 + u(-0.05, 0.05))
        self.M_rod = 1.00e6 * (1.0 + u(-0.04, 0.04))      # A/m  (Br ~ 1.26 T)
        self.M_ring = 1.00e6 * (1.0 + u(-0.04, 0.04))
        self.rho_mag = 7.5e-3 * (1.0 + u(-0.02, 0.02))    # g/mm^3
        self.rod_mass = (math.pi * self.rod_a ** 2 * self.rod_L) * self.rho_mag
        self.mu_hole = u(0.10, 0.20)                      # rod/hole friction
        self.magnet = MagnetModel(self.rod_a, self.rod_L, self.ring_Ri,
                                  self.ring_Ro, self.ring_t,
                                  self.M_rod, self.M_ring)

        # ---- masses of the accessories [g] --------------------------------
        self.m_wplate = u(118.0, 132.0)
        self.m_tube = u(46.0, 54.0)
        self.m_stone = u(1150.0, 1290.0)


# =========================================================================
#  5.  apparatus geometry (mm, side view; y = 0 at the balance pan surface)
# =========================================================================
BASE_TOP = -48.0            # top face of the press base board
BASE_W, BASE_TH = 330.0, 18.0
POST_X = 150.0
POST_H = 300.0
PLATE_W, PLATE_TH = 270.0, 18.0
PLATE_Y_MAX = 200.0         # plate underside, screw fully retracted
PLATE_Y_MIN = 2.0
SCREW_X = 96.0
ALROD_X = -58.0
ALROD_LEN = 60.0
ALROD_D = 6.0
WPLATE_X, WPLATE_W, WPLATE_TH = -40.0, 150.0, 12.0
TUBE_X = ALROD_X
TUBE_H = 100.0
TUBE_OD = 25.0
TUBE_HOLE_D = 6.0
RING_FROM_END = 15.0        # ring centre, distance from the "ring end" face
PAN_D = 180.0
STONE_W, STONE_H = 92.0, 62.0


# =========================================================================
#  6.  Rig -- the apparatus.  This is the only public API: the GUI and the
#      verification harness both drive the experiment through it and read
#      instruments through *_display() / measure().
# =========================================================================
class Rig(object):

    PARTS = ("press", "scale", "wplate", "stone", "tube", "rodmag", "ruler", "stick")

    def __init__(self, seed=None):
        self.truth = Truth(seed)
        self.rng = random.Random(self.truth.seed ^ 0x5eed)
        self.log = []
        # ---- assembly -----------------------------------------------------
        self.placed = set()
        self.plate_flipped = False        # False: Al rod up (Exp.1) / True: down
        self.cylinders = {}               # id -> dict(kind, l, Rc, B, creased)
        self._cyl_n = 0
        self.foil_stock = {"blue": [], "clear": []}
        self.cut_sheets = {}
        self._sheet_n = 0
        self.on_pan = None                # None | 'wplate' | 'tube'
        self.cyl_on_plate = None          # cylinder id
        # ---- press --------------------------------------------------------
        self.turns = 0.0                  # signed screw revolutions (down +)
        self.counter_zero = 0.0
        self._last_dir = 0
        self._lash = 0.0
        # ---- balance ------------------------------------------------------
        self.scale_on = True
        self.tare = 0.0
        self.tare_off = 0.0
        self.unit_oz = False
        self._last_reading = 0.0
        # ---- magnets ------------------------------------------------------
        self.tube_orient = "upright"      # 'upright' | 'inverted' | 'horizontal'
        self.rod_where = "box"            # 'box' | 'tube' | 'hand'
        self.rod_orient = 1               # +1 parallel, -1 antiparallel
        self.rod_z = 0.0
        self.rod_contact = False
        self.msg = ""

    # -------------------------------------------------- small helpers
    def _note(self, s):
        self.msg = s
        self.log.append(s)

    def has(self, p):
        return p in self.placed

    # ================================================== assembly
    def place(self, part):
        t = self.truth
        if part in self.placed:
            return False, T(u"이미 설치되어 있습니다.", u"Already in place.")
        if part == "press":
            self.placed.add(part)
            return True, T(u"프레스를 작업대에 놓았습니다.",
                           u"The press is on the bench.")
        if part in ("ruler", "stick"):
            self.placed.add(part)
            return True, T(u"도구를 집었습니다.", u"Tool in hand.")
        if not self.has("press"):
            return False, T(u"먼저 프레스를 놓아야 합니다.",
                            u"Place the press first.")
        if part == "scale":
            self.placed.add(part)
            return True, T(u"저울을 프레스 안에 넣었습니다.",
                           u"The balance is inside the press.")
        if part == "stone":
            self.placed.add(part)
            return True, T(u"돌덩이를 윗판 위에 올렸습니다.",
                           u"The stone block sits on the upper plate.")
        if not self.has("scale"):
            return False, T(u"먼저 저울을 놓아야 합니다.", u"Place the balance first.")
        if part == "wplate":
            if self.on_pan == "tube":
                return False, T(u"저울 위에 투명 원통이 있습니다.",
                                u"The transparent cylinder occupies the pan.")
            self.placed.add(part)
            self.on_pan = "wplate"
            return True, T(u"나무판을 저울 위에 놓았습니다.",
                           u"The wooden plate is on the pan.")
        if part == "tube":
            if self.on_pan == "wplate":
                return False, T(u"저울 위에 나무판이 있습니다.",
                                u"The wooden plate occupies the pan.")
            self.placed.add(part)
            self.on_pan = "tube"
            return True, T(u"링자석이 든 투명 원통을 저울 위에 세웠습니다.",
                           u"The transparent cylinder stands on the pan.")
        if part == "rodmag":
            if not self.has("tube"):
                return False, T(u"막대자석을 넣을 투명 원통이 없습니다.",
                                u"No transparent cylinder to insert the rod into.")
            return self.insert_rod()
        return False, T(u"알 수 없는 부품입니다.", u"Unknown part.")

    def remove(self, part):
        if part not in self.placed:
            return False, T(u"설치되어 있지 않습니다.", u"Not in place.")
        if part == "wplate" and self.cyl_on_plate is not None:
            return False, T(u"필름 원통을 먼저 치우세요.",
                            u"Take the foil cylinder off first.")
        if part == "tube" and self.rod_where == "tube":
            return False, T(u"막대자석을 먼저 빼내세요.",
                            u"Remove the rod magnet first.")
        if part == "press" and (self.has("scale") or self.has("stone")):
            return False, T(u"저울과 돌덩이를 먼저 치우세요.",
                            u"Remove the balance and the stone first.")
        if part == "scale" and self.on_pan:
            return False, T(u"저울 위의 물체를 먼저 치우세요.",
                            u"Clear the balance pan first.")
        self.placed.discard(part)
        if part in ("wplate", "tube"):
            self.on_pan = None
        return True, T(u"치웠습니다.", u"Removed.")

    def flip_plate(self):
        if not self.has("press"):
            return False, T(u"프레스가 없습니다.", u"No press.")
        self.plate_flipped = not self.plate_flipped
        return True, (T(u"윗판을 뒤집어 알루미늄 봉이 아래를 향합니다. (실험 2)",
                        u"Upper plate inverted: the aluminium rod points down. (Exp. 2)")
                      if self.plate_flipped else
                      T(u"윗판을 원래대로 두어 알루미늄 봉이 위를 향합니다. (실험 1)",
                        u"Upper plate upright: the aluminium rod points up. (Exp. 1)"))

    # ------------------------------------------------ foil workshop
    def cut_sheet(self, kind, w, h):
        """scissors: produce a sheet of w x h mm out of an A4 transparency."""
        W, H = self.truth.foil_sheet
        w = max(20.0, min(W, round(w, 1)))
        h = max(20.0, min(H, round(h, 1)))
        self._sheet_n += 1
        sid = "%s%d" % (kind, self._sheet_n)
        self.cut_sheets[sid] = (kind, w, h)
        return sid, (w, h)

    def roll_foil(self, kind="blue", axis="short", overlap=5.0, sheet=None):
        """Roll a transparency into a cylinder.
        axis='short' : the cylinder axis is parallel to the *short* (210 mm)
                       edge, i.e. the 297 mm edge is rolled up  (l = 210 mm).
        axis='long'  : axis parallel to the long (297 mm) edge   (l = 297 mm).
        """
        if sheet is not None and sheet in self.cut_sheets:
            kind, W, H = self.cut_sheets[sheet]
        else:
            W, H = self.truth.foil_sheet
        overlap = max(0.0, min(40.0, overlap))
        if axis == "short":
            l, circ = W, H - overlap          # l = 210, rolled edge = 297
        else:
            l, circ = H, W - overlap          # l = 297, rolled edge = 210
        if circ < 40.0:
            return None, T(u"둘레가 너무 짧습니다.", u"Circumference too small.")
        Rc = circ / (2.0 * math.pi) + self.rng.uniform(-0.18, 0.18)
        t = self.truth
        seam = 1.0 + self.rng.uniform(-0.022, 0.022)      # tape / overlap seam
        self._cyl_n += 1
        cid = "cyl%d" % self._cyl_n
        self.cylinders[cid] = dict(
            kind=kind, l=l, circ=circ, overlap=overlap, Rc=Rc,
            B=t.kappa_true[kind] * (l * 1e-3) * seam,     # N m^2
            creased=False,
            mass=1.40e-3 * l * circ * (t.d_true[kind] * 1e3))   # g (PET foil)
        return cid, T(u"필름을 말아 원통을 만들었습니다.",
                      u"The foil has been rolled into a cylinder.")

    def put_cylinder(self, cid):
        if cid not in self.cylinders:
            return False, T(u"그런 원통이 없습니다.", u"No such cylinder.")
        if self.on_pan != "wplate":
            return False, T(u"먼저 저울 위에 나무판을 놓으세요.",
                            u"Put the wooden plate on the pan first.")
        self.cyl_on_plate = cid
        return True, T(u"원통을 나무판 위에 올렸습니다.",
                       u"The cylinder lies on the wooden plate.")

    def take_cylinder(self):
        self.cyl_on_plate = None
        return True, T(u"원통을 치웠습니다.", u"Cylinder removed.")

    # ------------------------------------------------ rod magnet
    def insert_rod(self, orient=None):
        if not self.has("tube"):
            return False, T(u"투명 원통이 없습니다.", u"No transparent cylinder.")
        if orient is not None:
            self.rod_orient = 1 if orient > 0 else -1
        if self.plate_flipped and self.has("press") \
                and self.tube_orient != "horizontal":
            need = TUBE_H + self.truth.rod_L + 2.0
            if self._plate_y_raw() - ALROD_LEN < need:
                return False, T(u"알루미늄 봉이 방해합니다. 나비너트를 되돌려 "
                                u"윗판을 올리거나 원통을 눕힌 뒤 넣으세요.",
                                u"The aluminium rod is in the way: raise the "
                                u"upper plate, or lay the cylinder down first.")
        self.placed.add("rodmag")
        self.rod_where = "tube"
        # dropped in through the far opening
        self.rod_z = self._z_entry()
        self.relax()
        return True, T(u"막대자석을 구멍에 넣었습니다.",
                       u"The rod magnet is inside the hole.")

    def remove_rod(self):
        if self.rod_where != "tube":
            return False, T(u"원통 안에 막대자석이 없습니다.",
                            u"The rod magnet is not in the cylinder.")
        if not self.has("stick"):
            return False, T(u"막대자석을 밀어낼 나무 막대가 필요합니다.",
                            u"You need the wooden stick to push it out.")
        self.rod_where = "hand"
        self.rod_contact = False
        return True, T(u"나무 막대로 막대자석을 빼냈습니다.",
                       u"The rod magnet has been pushed out with the stick.")

    def flip_rod(self):
        if self.rod_where == "tube":
            return False, T(u"먼저 막대자석을 원통에서 빼내세요.",
                            u"Take the rod magnet out of the cylinder first.")
        self.rod_orient = -self.rod_orient
        return True, T(u"막대자석의 방향을 뒤집었습니다.",
                       u"The rod magnet has been turned around.")

    def set_tube_orientation(self, mode):
        if mode not in ("upright", "inverted", "horizontal"):
            return False, "?"
        if mode != "horizontal" and self.tube_orient == "horizontal" \
                and not self.has("scale"):
            return False, T(u"저울이 없습니다.", u"No balance.")
        self.tube_orient = mode
        if mode == "horizontal":
            self.rod_contact = False
        self.relax()
        return True, {"upright": T(u"원통을 링자석 쪽이 위로 오게 세웠습니다.",
                                   u"Cylinder standing, ring end up."),
                      "inverted": T(u"원통을 링자석 쪽이 아래로 오게 세웠습니다.",
                                    u"Cylinder standing, ring end down."),
                      "horizontal": T(u"원통을 작업대에 눕혔습니다. (z축 수평)",
                                      u"Cylinder lying on the bench (z horizontal).")
                      }[mode]

    # ================================================== press kinematics
    def plate_y(self):
        """height of the upper-plate underside above the balance pan [mm]"""
        t = self.truth
        y = PLATE_Y_MAX - t.pitch * self.turns + self._lash
        y += t.compliance * self.press_force()
        return max(PLATE_Y_MIN, min(PLATE_Y_MAX + 4.0, y))

    def _plate_y_raw(self):
        t = self.truth
        return PLATE_Y_MAX - t.pitch * self.turns + self._lash

    def turn_nut(self, degrees):
        """turn the wing nut; positive = plate moves down (2 mm per 360 deg)"""
        if not self.has("press"):
            return False, T(u"프레스가 없습니다.", u"No press.")
        d = 1 if degrees > 0 else (-1 if degrees < 0 else 0)
        if d and self._last_dir and d != self._last_dir:
            # play in the thread: the first motion after a reversal is lost
            self._lash += self.truth.backlash if d > 0 else -self.truth.backlash
        if d:
            self._last_dir = d
        self.turns += degrees / 360.0
        ymin = PLATE_Y_MIN
        if self.on_pan == "tube" and self.tube_orient != "horizontal":
            ymin = TUBE_H + 1.5
        elif self.on_pan == "wplate":
            ymin = WPLATE_TH + 2.0
        hard = False
        tmax = (PLATE_Y_MAX - ymin) / self.truth.pitch
        if self.turns > tmax:
            self.turns = tmax
            hard = True
        self.turns = max(-6.0, self.turns)
        self.relax()
        if hard:
            return True, T(u"윗판이 아래 물체에 닿아 더 내려가지 않습니다.",
                           u"The upper plate is already against the object below.")
        return True, ""

    def zero_counter(self):
        self.counter_zero = self.turns
        return True, T(u"회전 카운터를 0으로 맞췄습니다.",
                       u"Rotation counter set to zero.")

    def counter_display(self):
        if not self.has("press"):
            return "---"
        x = self.turns - self.counter_zero
        s = -1 if x < 0 else 1
        ax = abs(x)
        n = int(ax)
        deg = (ax - n) * 360.0
        return u"%s%d %s %5.1f\u00b0" % ("-" if s < 0 else "", n,
                                         T(u"회전", u"turn"), deg)

    # ================================================== forces
    def foil_gap(self):
        """clear gap between the plate underside and the wooden plate top."""
        return self._plate_y_raw() - WPLATE_TH

    def foil_force(self):
        """press force on the rolled foil [N] (0 if not touching)."""
        cid = self.cyl_on_plate
        if cid is None or self.on_pan != "wplate" or self.plate_flipped:
            return 0.0
        c = self.cylinders[cid]
        Rc, B = c["Rc"], c["B"]
        if c["creased"]:
            B *= 0.86
        # solve h with frame compliance:  h = h_raw + compliance * F
        h = self.foil_gap()
        for _ in range(24):
            hh = max(1e-3, h) / Rc
            if hh >= 2.0:
                F = 0.0
            else:
                F = elastica_force_hat(hh) * B / ((Rc * 1e-3) ** 2)
            hn = self.foil_gap() + self.truth.compliance * F
            if abs(hn - h) < 1e-7:
                h = hn
                break
            h = hn
        hh = max(1e-3, h) / Rc
        if hh >= 2.0:
            return 0.0
        F = elastica_force_hat(hh) * B / ((Rc * 1e-3) ** 2)
        if 0.5 * hh < 0.12 and not c["creased"]:
            c["creased"] = True
            self._note(T(u"필름이 심하게 눌려 영구적으로 접혔습니다! 다시 말아야 합니다.",
                         u"The foil has been creased permanently! Roll a new one."))
        return F

    # ---- magnet geometry ------------------------------------------------
    def ring_height(self):
        """height of the ring-magnet centre above the pan [mm]"""
        if self.tube_orient == "upright":
            return TUBE_H - RING_FROM_END
        if self.tube_orient == "inverted":
            return RING_FROM_END
        return 0.5 * TUBE_OD

    def z_sign(self):
        """d(height)/dz : -1 when +z points down, +1 when it points up"""
        return -1.0 if self.tube_orient == "upright" else 1.0

    def rod_height(self):
        return self.ring_height() + self.z_sign() * self.rod_z

    def _z_entry(self):
        """where a dropped rod magnet starts (far opening of the hole)"""
        L2 = 0.5 * self.truth.rod_L
        if self.tube_orient == "inverted":
            return TUBE_H - RING_FROM_END - L2 + 1.0
        return -RING_FROM_END - L2 + 3.5

    def z_limits(self):
        """travel limits of the rod-magnet centre inside the hole"""
        L2 = 0.5 * self.truth.rod_L
        deep = TUBE_H - RING_FROM_END - L2       # far end of the hole
        out = -RING_FROM_END - L2 + 3.0          # about to leave the hole
        if self.tube_orient == "inverted":
            # the ring end rests on the pan: the rod cannot pass it
            out = L2 - RING_FROM_END
        return out, deep

    def grav_z(self):
        """component of the rod weight along +z [N]"""
        if self.tube_orient == "horizontal":
            return 0.0
        m = self.truth.rod_mass * 1e-3
        return -self.z_sign() * m * G_ACC

    def press_z_bound(self):
        """(bound, kind) imposed by the aluminium rod, or (None, None)"""
        if not (self.plate_flipped and self.has("press") and
                self.rod_where == "tube" and self.tube_orient != "horizontal"):
            return None, None
        tip = self._plate_y_raw() - ALROD_LEN
        L2 = 0.5 * self.truth.rod_L
        zb = self.z_sign() * (tip - L2 - self.ring_height())
        if self.tube_orient == "upright":
            return zb, "lower"      # the rod cannot rise above the tip
        return zb, "upper"

    def net_force(self, z):
        """magnetic + gravity force on the rod magnet along +z [N]"""
        return self.truth.magnet.force(z, self.rod_orient) + self.grav_z()

    def relax(self):
        """Quasi-static settling of the rod magnet.

        The rod is heavily damped inside the hole, so it simply drifts along
        the sign of the net force until either (a) the net force changes sign
        -- a stable equilibrium, located by bisection -- or (b) it runs into
        a mechanical stop (the aluminium rod of the press, the pan, or the
        far opening of the hole, in which case it leaves the cylinder).
        """
        if self.rod_where != "tube":
            self.rod_contact = False
            return
        zlo, zhi = self.z_limits()
        zb, kind = self.press_z_bound()
        lo, hi = zlo, zhi
        if zb is not None:
            if kind == "lower":
                lo = max(lo, zb)
            else:
                hi = min(hi, zb)
        if hi < lo:
            hi = lo
        z = max(lo, min(hi, self.rod_z))
        fstick = self.truth.mu_hole * self.truth.rod_mass * 1e-3 * G_ACC \
            if self.tube_orient == "horizontal" else 0.0015
        F = self.net_force(z)
        pinned = None                      # "lo" / "hi" / None
        if abs(F) > fstick:
            sgn = 1.0 if F > 0.0 else -1.0
            h = 0.04
            while True:
                zn = z + sgn * h
                if zn <= lo:
                    z, pinned = lo, "lo"
                    break
                if zn >= hi:
                    z, pinned = hi, "hi"
                    break
                Fn = self.net_force(zn)
                if Fn * sgn <= 0.0:        # crossed a stable equilibrium
                    a, b = z, zn
                    for _ in range(60):
                        m = 0.5 * (a + b)
                        if self.net_force(m) * sgn > 0.0:
                            a = m
                        else:
                            b = m
                    z = 0.5 * (a + b)
                    break
                z, F = zn, Fn
        self.rod_z = max(lo, min(hi, z))
        # ---- is the rod held against the aluminium rod of the press?
        self.rod_contact = False
        if zb is not None:
            if kind == "lower" and pinned == "lo" and abs(self.rod_z - zb) < 1e-6:
                self.rod_contact = True
            if kind == "upper" and pinned == "hi" and abs(self.rod_z - zb) < 1e-6:
                self.rod_contact = True
        if self.rod_contact:
            return
        # ---- did it leave the cylinder through an opening?
        out_lo = abs(self.rod_z - zlo) < 1e-6 and pinned == "lo" \
            and self.tube_orient != "inverted"
        out_hi = abs(self.rod_z - zhi) < 1e-6 and pinned == "hi" \
            and self.tube_orient == "horizontal"
        if out_lo or out_hi:
            self.rod_where = "hand"
            self._note(T(u"막대자석이 구멍에서 튀어나왔습니다.",
                         u"The rod magnet has shot out of the hole."))

    def press_force(self):
        """downward force applied by the press to whatever is below [N]"""
        if not self.has("press"):
            return 0.0
        if not self.plate_flipped:
            return self.foil_force()
        if self.rod_where == "tube" and self.rod_contact:
            F = self.truth.magnet.force(self.rod_z, self.rod_orient)
            m = self.truth.rod_mass * 1e-3 * G_ACC
            if self.tube_orient == "upright":
                return max(0.0, -m - F)
            return max(0.0, F - m)
        return 0.0

    # ================================================== balance
    def pan_load(self):
        """total load on the pan [g] before taring"""
        if not self.has("scale"):
            return 0.0
        t = self.truth
        m = 0.0
        if self.on_pan == "wplate":
            m += t.m_wplate
            if self.cyl_on_plate is not None:
                m += self.cylinders[self.cyl_on_plate]["mass"]
        elif self.on_pan == "tube" and self.tube_orient != "horizontal":
            m += t.m_tube
            if self.rod_where == "tube":
                m += t.rod_mass
        m += self.press_force() / G_ACC * 1000.0
        return m

    def scale_tare(self):
        if not self.scale_on:
            return False, T(u"저울이 꺼져 있습니다.", u"The balance is off.")
        self.tare = self.pan_load()
        self.tare_off = self.truth.scale_offset      # the display is zeroed
        return True, T(u"영점(TARA)을 잡았습니다.", u"Tared.")

    def scale_power(self):
        self.scale_on = not self.scale_on
        if self.scale_on:
            self.tare = self.pan_load()
            self.tare_off = self.truth.scale_offset
        return True, ""

    def scale_toggle_unit(self):
        self.unit_oz = not self.unit_oz
        return True, ""

    def scale_value(self):
        """the number the balance shows [g], quantised, or None if overload"""
        if not self.scale_on or not self.has("scale"):
            return None
        t = self.truth
        gross = self.pan_load()
        if gross > t.scale_cap:
            return "OL"
        v = (gross - self.tare) * t.scale_gain + t.scale_offset - self.tare_off
        v += self.rng.gauss(0.0, t.scale_noise)
        return math.floor(v + 0.5)

    def scale_display(self):
        if not self.has("scale"):
            return T(u"(저울 없음)", u"(no balance)")
        if not self.scale_on:
            return ""
        v = self.scale_value()
        if v == "OL":
            return "O-Ld"
        if self.unit_oz:
            return "%.2f oz" % (v * 0.03527396)
        return "%d g" % int(v)

    # ================================================== ruler
    def _eye(self, x, q=0.5):
        e = self.rng.gauss(0.0, self.truth.eye)
        return round((x + e) / q) * q

    def measure(self, what, cid=None):
        """read a length off the millimetre ruler (eye precision ~0.5 mm)."""
        if not self.has("ruler"):
            return None, T(u"자를 먼저 집으세요.", u"Pick up the ruler first.")
        if what == "gap":
            if self.on_pan != "wplate":
                return None, T(u"저울 위에 나무판이 없습니다.",
                               u"No wooden plate on the pan.")
            v = self._eye(self.foil_gap() + self.truth.compliance * self.foil_force())
            return v, T(u"윗판–나무판 간격", u"plate/board separation") + ": %.1f mm" % v
        if what == "cyl":
            cid = cid or self.cyl_on_plate
            if cid is None:
                return None, T(u"원통이 없습니다.", u"No cylinder.")
            v = self._eye(2.0 * self.cylinders[cid]["Rc"])
            return v, T(u"원통 지름", u"cylinder diameter") + ": %.1f mm" % v
        if what == "rod_z":
            if self.rod_where != "tube":
                return None, T(u"막대자석이 원통 안에 없습니다.",
                               u"The rod magnet is not in the cylinder.")
            v = self._eye(self.rod_z)
            return v, T(u"막대자석 중심 – 링자석 중심", u"rod centre to ring centre") \
                + ": %+.1f mm" % v
        if what == "rod_len":
            v = self._eye(self.truth.rod_L)
            return v, T(u"막대자석 길이", u"rod magnet length") + ": %.1f mm" % v
        if what == "ring":
            v = self._eye(2.0 * self.truth.ring_Ro)
            w = self._eye(self.truth.ring_t)
            return v, T(u"링자석 바깥지름/두께", u"ring outer dia./thickness") \
                + ": %.1f / %.1f mm" % (v, w)
        if what == "tube":
            v = self._eye(TUBE_OD)
            h = self._eye(TUBE_H)
            return v, T(u"투명 원통 지름/높이", u"cylinder dia./height") \
                + ": %.1f / %.1f mm" % (v, h)
        return None, "?"

    # ================================================== stick (task 1)
    def push_rod(self, dz):
        """Push the rod magnet along the axis with the wooden stick, then let go.

        If the rod is not yet in the hole it is first offered at the opening,
        so that a single push can force it past a repulsive barrier -- exactly
        what one does with the wooden stick.
        """
        if self.rod_where != "tube":
            if not self.has("tube"):
                return False, T(u"투명 원통이 없습니다.", u"No transparent cylinder.")
            if not self.has("stick"):
                return False, T(u"나무 막대가 필요합니다.",
                                u"You need the wooden stick.")
            ok, msg = self.insert_rod()
            if not ok:
                return False, msg
            if self.rod_where != "tube":         # it was pushed straight out
                self.rod_where = "tube"
            self.rod_z = self._z_entry()
        if not self.has("stick") and self.tube_orient == "horizontal":
            return False, T(u"나무 막대가 필요합니다.", u"You need the wooden stick.")
        zlo, zhi = self.z_limits()
        self.rod_z = max(zlo, min(zhi, self.rod_z + dz))
        self.relax()
        return True, ""

    def state(self):
        """compact machine-readable state (verification harness)."""
        return dict(placed=sorted(self.placed), flipped=self.plate_flipped,
                    on_pan=self.on_pan, cyl=self.cyl_on_plate,
                    turns=self.turns, counter=self.counter_display(),
                    scale=self.scale_display(), rod=self.rod_where,
                    orient=self.rod_orient, z=self.rod_z,
                    contact=self.rod_contact, tube=self.tube_orient)

# =========================================================================
#  7.  GUI  --  two tabs only:  "조립 / Assembly"  and  "실험대 / Bench".
#      Nothing is displayed that a real experimenter could not see:
#      the balance LCD, the revolution counter engraved on the screw,
#      and the millimetre ruler.  No derived quantity, no hint, no answer.
# =========================================================================
import tkinter as tk
from tkinter import ttk

COL = {
    "bg": "#1d2128", "panel": "#262b34", "ink": "#e9edf2", "dim": "#98a1ad",
    "ply": "#c9a370", "plydk": "#a07c4c", "plyed": "#8a6a3f",
    "post": "#2c2f35", "postlt": "#3a3f47",
    "metal": "#b8bfc7", "metaldk": "#79818b", "alrod": "#d7dbe0",
    "stone": "#918d87", "stonedk": "#6f6b66",
    "scale": "#cfd4da", "scaledk": "#9aa1a9",
    "lcd": "#b8d8a8", "lcdink": "#1f2a19", "btn": "#2f6fbf",
    "tube": "#d3ecf5", "tubeed": "#8ab6c6",
    "magN": "#c34b3e", "magS": "#3f6ac6", "magbody": "#6d737b",
    "foilblue": "#3f78cf", "foilclear": "#c9d3de",
    "ruler": "#efe0ab", "rulerink": "#4a4130",
    "ghost": "#6fd0a0", "warn": "#ffcf6b", "ok": "#8fe0a8",
}

SEG = ("Consolas", 22, "bold")


def _rr(cv, x0, y0, x1, y1, r=4, **kw):
    """rounded rectangle as a polygon (screen coordinates)"""
    r = max(0.0, min(r, abs(x1 - x0) * 0.5, abs(y1 - y0) * 0.5))
    p = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
         x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(p, smooth=True, **kw)


# -------------------------------------------------------------------------
#  the side-view scene, shared by both tabs
# -------------------------------------------------------------------------
class Scene(object):

    HX0 = -158.0          # left end of the cylinder when it lies down

    def __init__(self, canvas, rig, ppm=2.3):
        self.cv = canvas
        self.rig = rig
        self.ppm = ppm                 # pixels per millimetre
        self.ox, self.oy = 480.0, 560.0
        self.zones = []                # (name, x0, y0, x1, y1) screen, topmost last
        self.left_margin = 0.0
        self.user_moved = False

    def fit(self, left=0.0):
        """frame the whole apparatus in the canvas"""
        w = int(self.cv.winfo_width() or 900)
        h = int(self.cv.winfo_height() or 600)
        x0, x1 = -195.0, 200.0
        y0, y1 = -85.0, 300.0
        m = 16.0
        self.ppm = max(0.6, min((w - left - 2 * m) / (x1 - x0),
                                (h - 2 * m) / (y1 - y0)))
        self.ox = left + (w - left) / 2.0 - 0.5 * (x0 + x1) * self.ppm
        self.oy = h - m + y0 * self.ppm

    # ---- transforms
    def sx(self, x):
        return self.ox + x * self.ppm

    def sy(self, y):
        return self.oy - y * self.ppm

    def wx(self, sx):
        return (sx - self.ox) / self.ppm

    def wy(self, sy):
        return (self.oy - sy) / self.ppm

    def box(self, x0, y0, x1, y1, **kw):
        return self.cv.create_rectangle(self.sx(x0), self.sy(y1),
                                        self.sx(x1), self.sy(y0), **kw)

    def poly(self, pts, **kw):
        f = []
        for x, y in pts:
            f.append(self.sx(x))
            f.append(self.sy(y))
        return self.cv.create_polygon(f, **kw)

    def zone(self, name, x0, y0, x1, y1):
        self.zones.append((name, self.sx(x0), self.sy(y1),
                           self.sx(x1), self.sy(y0)))

    def hit(self, sx, sy):
        for name, x0, y0, x1, y1 in reversed(self.zones):
            if x0 <= sx <= x1 and y0 <= sy <= y1:
                return name
        return None

    # =====================================================================
    def draw(self):
        cv, R = self.cv, self.rig
        cv.delete("all")
        self.zones = []
        w = int(cv.winfo_width() or 900)
        h = int(cv.winfo_height() or 600)
        cv.create_rectangle(0, 0, w, h, fill=COL["bg"], outline="")
        # bench top
        cv.create_rectangle(0, self.sy(BASE_TOP - 18.0), w, h,
                            fill="#171a20", outline="")
        cv.create_line(0, self.sy(BASE_TOP - 18.0), w, self.sy(BASE_TOP - 18.0),
                       fill="#0f1216", width=2)
        if R.has("press"):
            self._press_frame()
        if R.has("scale"):
            self._balance()
        if R.on_pan == "wplate":
            self._wplate()
            if R.cyl_on_plate is not None:
                self._foil()
        if R.on_pan == "tube" and R.tube_orient != "horizontal":
            self._tube_vertical()
        if R.has("tube") and R.tube_orient == "horizontal":
            self._tube_horizontal()
        if R.has("press"):
            self._plate_and_screw()
        if R.has("ruler"):
            self._ruler()
        if R.has("stick"):
            self._stick()
        if R.rod_where == "hand":
            self._rod_in_hand()
        self._scalebar()

    # ---------------------------------------------------------------- press
    def _press_frame(self):
        # base board with rubber feet
        self.box(-BASE_W / 2, BASE_TOP - BASE_TH, BASE_W / 2, BASE_TOP,
                 fill=COL["ply"], outline=COL["plyed"])
        self.box(-BASE_W / 2, BASE_TOP - 2.0, BASE_W / 2, BASE_TOP,
                 fill=COL["plydk"], outline="")
        for fx in (-120.0, 120.0):
            self.box(fx - 14, BASE_TOP - BASE_TH - 7, fx + 14, BASE_TOP - BASE_TH,
                     fill="#26282c", outline="")
        # two black L posts + top cross-bar
        for px in (-POST_X, POST_X):
            self.box(px - 9, BASE_TOP, px + 9, BASE_TOP + POST_H,
                     fill=COL["post"], outline=COL["postlt"])
            self.box(px - 9, BASE_TOP, px + 9, BASE_TOP + 4,
                     fill=COL["postlt"], outline="")
        ytop = BASE_TOP + POST_H
        self.box(-POST_X - 9, ytop, POST_X + 9, ytop + 16,
                 fill=COL["post"], outline=COL["postlt"])
        self.zone("press", -BASE_W / 2, BASE_TOP - BASE_TH, -POST_X + 9, ytop + 16)
        self.zone("press", POST_X - 9, BASE_TOP, POST_X + 9, ytop + 16)

    def _plate_and_screw(self):
        R = self.rig
        y = R.plate_y()
        # upper wooden plate
        self.box(-PLATE_W / 2, y, PLATE_W / 2, y + PLATE_TH,
                 fill=COL["ply"], outline=COL["plyed"])
        self.box(-PLATE_W / 2, y, PLATE_W / 2, y + 2.2,
                 fill=COL["plydk"], outline="")
        self.zone("plate", -PLATE_W / 2, y, PLATE_W / 2, y + PLATE_TH)
        # aluminium rod
        if R.plate_flipped:
            self.box(ALROD_X - ALROD_D / 2, y - ALROD_LEN,
                     ALROD_X + ALROD_D / 2, y,
                     fill=COL["alrod"], outline=COL["metaldk"])
        else:
            self.box(ALROD_X - ALROD_D / 2, y + PLATE_TH,
                     ALROD_X + ALROD_D / 2, y + PLATE_TH + ALROD_LEN,
                     fill=COL["alrod"], outline=COL["metaldk"])
        # granite block
        if R.has("stone"):
            sy0 = y + PLATE_TH
            self.box(-STONE_W / 2 + 20, sy0, STONE_W / 2 + 20, sy0 + STONE_H,
                     fill=COL["stone"], outline=COL["stonedk"])
            self.box(-STONE_W / 2 + 20, sy0 + STONE_H - 4,
                     STONE_W / 2 + 20, sy0 + STONE_H, fill="#a5a19b", outline="")
            self.zone("stone", -STONE_W / 2 + 20, sy0, STONE_W / 2 + 20,
                      sy0 + STONE_H)
        # threaded rod from the cross-bar down to the plate
        ytop = BASE_TOP + POST_H
        self.box(SCREW_X - 5, y + PLATE_TH, SCREW_X + 5, ytop + 16,
                 fill=COL["metal"], outline=COL["metaldk"])
        yy = y + PLATE_TH + 2.0
        while yy < ytop + 14:
            self.cv.create_line(self.sx(SCREW_X - 5), self.sy(yy),
                                self.sx(SCREW_X + 5), self.sy(yy + 1.6),
                                fill=COL["metaldk"])
            yy += 3.0
        self._nut(ytop + 16)

    def _nut(self, ybase):
        """wing nut on top of the cross-bar; its wings show the rotation"""
        R = self.rig
        ang = (R.turns * 360.0) % 360.0
        c = math.cos(math.radians(ang))
        s = math.sin(math.radians(ang))
        x0, y0 = SCREW_X, ybase + 7.0
        self.box(x0 - 9, ybase, x0 + 9, ybase + 13,
                 fill=COL["metal"], outline=COL["metaldk"])
        for sg in (1, -1):
            wx = sg * 22.0 * c
            self.poly([(x0 + sg * 6, y0 - 5), (x0 + wx, y0 - 9 - 3 * s),
                       (x0 + wx, y0 + 9 - 3 * s), (x0 + sg * 6, y0 + 5)],
                      fill=COL["metal"] if c * sg >= 0 else COL["metaldk"],
                      outline=COL["metaldk"])
        self.zone("nut", x0 - 26, ybase - 2, x0 + 26, ybase + 18)

    # -------------------------------------------------------------- balance
    def _balance(self):
        R = self.rig
        self.box(-58, BASE_TOP, 58, -6, fill=COL["scale"], outline=COL["scaledk"])
        self.box(-58, BASE_TOP, 58, BASE_TOP + 3, fill=COL["scaledk"], outline="")
        # pan
        self.box(-PAN_D / 2, -6, PAN_D / 2, 0,
                 fill=COL["scale"], outline=COL["scaledk"])
        self.box(-PAN_D / 2, -1.6, PAN_D / 2, 0, fill="#e6eaee", outline="")
        # LCD on the front face
        self.box(10, -40, 54, -18, fill=COL["lcdink"], outline="#5a6a52")
        self.box(11.5, -38.5, 52.5, -19.5, fill=COL["lcd"], outline="")
        txt = R.scale_display() if R.scale_on else ""
        self.cv.create_text(self.sx(32), self.sy(-29), text=txt,
                            fill=COL["lcdink"],
                            font=("Consolas", max(6, int(9 * self.ppm / 2.3)),
                                  "bold"))
        # three buttons
        for bx, name in ((-14, "btn_unit"), (-30, "btn_tare"), (-46, "btn_pw")):
            self.cv.create_oval(self.sx(bx - 5), self.sy(-24),
                                self.sx(bx + 5), self.sy(-34),
                                fill=COL["btn"], outline="#1c4a86")
            self.zone(name, bx - 6, -35, bx + 6, -23)
        self.zone("scale", -58, BASE_TOP, 58, -6)
        self.zone("scale", -PAN_D / 2, -6, PAN_D / 2, 0)

    # ------------------------------------------------------- wooden plate
    def _wplate(self):
        self.box(WPLATE_X - WPLATE_W / 2, 0, WPLATE_X + WPLATE_W / 2, WPLATE_TH,
                 fill=COL["ply"], outline=COL["plyed"])
        self.box(WPLATE_X - WPLATE_W / 2, WPLATE_TH - 2, WPLATE_X + WPLATE_W / 2,
                 WPLATE_TH, fill=COL["plydk"], outline="")
        self.zone("wplate", WPLATE_X - WPLATE_W / 2, 0,
                  WPLATE_X + WPLATE_W / 2, WPLATE_TH)

    # ------------------------------------------------------ rolled foil
    def _foil(self):
        R = self.rig
        c = R.cylinders[R.cyl_on_plate]
        Rc = c["Rc"]
        h = R.foil_gap() + R.truth.compliance * R.foil_force()
        hh = max(1e-3, h) / Rc
        pts = elastica_outline(min(hh, 2.0))
        yc = WPLATE_TH + (Rc if hh >= 2.0 else 0.5 * min(h, 2.0 * Rc))
        col = COL["foilblue"] if c["kind"] == "blue" else COL["foilclear"]
        out = [(WPLATE_X + px * Rc, yc + py * Rc) for px, py in pts]
        self.poly(out, fill="", outline=col, width=max(1, int(0.9 * self.ppm)))
        inn = [(WPLATE_X + px * (Rc - 0.9), yc + py * (Rc - 0.9)) for px, py in pts]
        self.poly(inn, fill="", outline=col, width=1)
        if c["creased"]:
            self.cv.create_text(self.sx(WPLATE_X), self.sy(yc),
                                text=T(u"주름", u"creased"), fill=COL["warn"],
                                font=("Helvetica", 9))
        self.zone("foil", WPLATE_X - Rc, WPLATE_TH, WPLATE_X + Rc, yc + Rc)

    # ---------------------------------------------------- magnet cylinder
    def _mag_block(self, x0, y0, x1, y1, npos):
        """draw a magnet with the N half towards +npos (a unit vector tuple)"""
        nx, ny = npos
        xm, ym = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if abs(ny) > abs(nx):
            a = (x0, ym, x1, y1) if ny > 0 else (x0, y0, x1, ym)
            b = (x0, y0, x1, ym) if ny > 0 else (x0, ym, x1, y1)
        else:
            a = (xm, y0, x1, y1) if nx > 0 else (x0, y0, xm, y1)
            b = (x0, y0, xm, y1) if nx > 0 else (xm, y0, x1, y1)
        self.box(a[0], a[1], a[2], a[3], fill=COL["magN"], outline="")
        self.box(b[0], b[1], b[2], b[3], fill=COL["magS"], outline="")
        self.box(x0, y0, x1, y1, fill="", outline="#20242b")

    def _tube_body_vertical(self):
        x0, x1 = TUBE_X - TUBE_OD / 2, TUBE_X + TUBE_OD / 2
        self.box(x0, 0, x1, TUBE_H, fill=COL["tube"], outline=COL["tubeed"])
        self.box(x0, 0, x0 + 2.0, TUBE_H, fill="#eaf7fb", outline="")
        for hx in (-TUBE_HOLE_D / 2, TUBE_HOLE_D / 2):
            self.cv.create_line(self.sx(TUBE_X + hx), self.sy(0),
                                self.sx(TUBE_X + hx), self.sy(TUBE_H),
                                fill=COL["tubeed"], dash=(3, 2))
        self.zone("tube", x0, 0, x1, TUBE_H)

    def _tube_vertical(self):
        R = self.rig
        self._tube_body_vertical()
        t = R.truth
        yr = R.ring_height()
        zs = R.z_sign()                 # +1 : +z points up
        ny = (0.0, 1.0) if zs > 0 else (0.0, -1.0)
        # ring magnet embedded in the wall
        for sg in (-1, 1):
            x0 = TUBE_X + sg * t.ring_Ri
            x1 = TUBE_X + sg * t.ring_Ro
            self._mag_block(min(x0, x1), yr - t.ring_t / 2,
                            max(x0, x1), yr + t.ring_t / 2, ny)
        # rod magnet
        if R.rod_where == "tube":
            yc = R.rod_height()
            a, L = t.rod_a, t.rod_L
            nr = ny if R.rod_orient > 0 else (0.0, -ny[1])
            self._mag_block(TUBE_X - a, yc - L / 2, TUBE_X + a, yc + L / 2, nr)
            self.zone("rodmag", TUBE_X - a, yc - L / 2, TUBE_X + a, yc + L / 2)

    def _tube_horizontal(self):
        R = self.rig
        t = R.truth
        yb = BASE_TOP
        yc = yb + TUBE_OD / 2
        x0 = self.HX0
        x1 = x0 + TUBE_H
        self.box(x0, yb, x1, yb + TUBE_OD, fill=COL["tube"], outline=COL["tubeed"])
        for hy in (-TUBE_HOLE_D / 2, TUBE_HOLE_D / 2):
            self.cv.create_line(self.sx(x0), self.sy(yc + hy),
                                self.sx(x1), self.sy(yc + hy),
                                fill=COL["tubeed"], dash=(3, 2))
        self.zone("tube", x0, yb, x1, yb + TUBE_OD)
        xr = x0 + RING_FROM_END          # +z points to +x
        for sg in (-1, 1):
            y0 = yc + sg * t.ring_Ri
            y1 = yc + sg * t.ring_Ro
            self._mag_block(xr - t.ring_t / 2, min(y0, y1),
                            xr + t.ring_t / 2, max(y0, y1), (1.0, 0.0))
        if R.rod_where == "tube":
            xc = xr + R.rod_z
            a, L = t.rod_a, t.rod_L
            n = (1.0, 0.0) if R.rod_orient > 0 else (-1.0, 0.0)
            self._mag_block(xc - L / 2, yc - a, xc + L / 2, yc + a, n)
            self.zone("rodmag", xc - L / 2, yc - a, xc + L / 2, yc + a)

    def _rod_in_hand(self):
        R = self.rig
        t = R.truth
        x, y = 128.0, BASE_TOP + 8.0
        self._mag_block(x - t.rod_L / 2, y - t.rod_a, x + t.rod_L / 2,
                        y + t.rod_a, (1.0, 0.0) if R.rod_orient > 0
                        else (-1.0, 0.0))
        self.zone("rodmag", x - t.rod_L / 2, y - t.rod_a,
                  x + t.rod_L / 2, y + t.rod_a)

    # ------------------------------------------------------------- tools
    def _ruler(self):
        x = 106.0
        y0, y1 = -8.0, 212.0
        self.box(x, y0, x + 17, y1, fill=COL["ruler"], outline="#b8a878")
        n = int(y0)
        while n <= y1:
            if n % 10 == 0:
                ln, wd = 11.0, 1
            elif n % 5 == 0:
                ln, wd = 7.0, 1
            else:
                ln, wd = 4.0, 1
            self.cv.create_line(self.sx(x), self.sy(n),
                                self.sx(x + ln), self.sy(n),
                                fill=COL["rulerink"], width=wd)
            if n % 20 == 0 and self.ppm > 1.6:
                self.cv.create_text(self.sx(x + 13.5), self.sy(n),
                                    text="%d" % n, fill=COL["rulerink"],
                                    font=("Helvetica", max(5, int(3.3 * self.ppm))))
            n += 1
        self.zone("ruler", x, y0, x + 17, y1)

    def _stick(self):
        y0 = BASE_TOP - BASE_TH - 7.0
        self.box(-150, y0, -90, y0 + 6, fill="#d9b98a", outline="#a98a5f")
        self.zone("stick", -150, y0, -90, y0 + 6)

    def _scalebar(self):
        """20 mm scale bar, bottom right"""
        cv = self.cv
        w = int(cv.winfo_width() or 900)
        h = int(cv.winfo_height() or 600)
        L = 20.0 * self.ppm
        x1, y1 = w - 24, h - 18
        cv.create_line(x1 - L, y1, x1, y1, fill=COL["dim"], width=2)
        cv.create_line(x1 - L, y1 - 4, x1 - L, y1 + 4, fill=COL["dim"])
        cv.create_line(x1, y1 - 4, x1, y1 + 4, fill=COL["dim"])
        cv.create_text(x1 - L / 2, y1 - 10, text="20 mm", fill=COL["dim"],
                       font=("Helvetica", 8))


# -------------------------------------------------------------------------
#  parts palette (left strip of the assembly canvas)
# -------------------------------------------------------------------------
PART_LABEL = {
    "press": T(u"프레스 (나사 프레스)", u"screw press"),
    "scale": T(u"전자저울 5000 g", u"electronic balance"),
    "wplate": T(u"나무판", u"wooden board"),
    "stone": T(u"돌덩이", u"stone block"),
    "tube": T(u"투명 원통 (링자석)", u"transparent cylinder"),
    "rodmag": T(u"막대자석", u"rod magnet"),
    "ruler": T(u"자 300 mm", u"ruler"),
    "stick": T(u"나무 막대", u"wooden stick"),
}


class Palette(object):
    W = 196
    ITEM_H = 62

    def __init__(self, canvas, rig):
        self.cv = canvas
        self.rig = rig
        self.slots = []          # (part, x0, y0, x1, y1)

    def draw(self):
        cv = self.cv
        h = int(cv.winfo_height() or 600)
        cv.create_rectangle(0, 0, self.W, h, fill=COL["panel"], outline="")
        cv.create_line(self.W, 0, self.W, h, fill="#3a4150")
        cv.create_text(self.W / 2, 18, text=T(u"부품 상자", u"parts box"),
                       fill=COL["ink"], font=("Helvetica", 11, "bold"))
        cv.create_text(self.W / 2, 36,
                       text=T(u"끌어다 놓기 / 우클릭 회수",
                              u"drag to place / right-click to remove"),
                       fill=COL["dim"], font=("Helvetica", 8))
        self.slots = []
        y = 52
        for p in Rig.PARTS:
            self._item(p, y)
            y += self.ITEM_H
        return y

    def _item(self, part, y):
        cv = self.cv
        used = self.rig.has(part)
        x0, y0, x1, y1 = 8, y, self.W - 8, y + self.ITEM_H - 8
        _rr(cv, x0, y0, x1, y1, 6,
            fill="#20242b" if used else "#2f3542",
            outline="#3f4756")
        self._icon(part, x0 + 30, (y0 + y1) / 2, dim=used)
        cv.create_text(x0 + 58, (y0 + y1) / 2 - 7, anchor="w",
                       text=PART_LABEL[part],
                       fill=COL["dim"] if used else COL["ink"],
                       font=("Helvetica", 9, "bold"), width=x1 - x0 - 62)
        if used:
            cv.create_text(x0 + 58, (y0 + y1) / 2 + 10, anchor="w",
                           text=T(u"설치됨", u"in place"), fill=COL["ok"],
                           font=("Helvetica", 8))
        if not used:
            self.slots.append((part, x0, y0, x1, y1))

    def hit(self, x, y):
        for part, x0, y0, x1, y1 in self.slots:
            if x0 <= x <= x1 and y0 <= y <= y1:
                return part
        return None

    # small vector icons, drawn in screen pixels
    def _icon(self, part, cx, cy, dim=False, cv=None, sc=1.0):
        cv = cv or self.cv
        a = "#555c68" if dim else None

        def c(key):
            return a or COL[key]
        if part == "press":
            cv.create_rectangle(cx - 15 * sc, cy + 10 * sc, cx + 15 * sc,
                                cy + 14 * sc, fill=c("ply"), outline="")
            for px in (-13, 13):
                cv.create_rectangle(cx + px * sc - 2 * sc, cy - 14 * sc,
                                    cx + px * sc + 2 * sc, cy + 10 * sc,
                                    fill=c("post"), outline="")
            cv.create_rectangle(cx - 15 * sc, cy - 18 * sc, cx + 15 * sc,
                                cy - 14 * sc, fill=c("post"), outline="")
            cv.create_rectangle(cx - 12 * sc, cy - 2 * sc, cx + 12 * sc,
                                cy + 3 * sc, fill=c("ply"), outline="")
            cv.create_line(cx, cy - 14 * sc, cx, cy - 2 * sc, fill=c("metal"),
                           width=2)
        elif part == "scale":
            cv.create_rectangle(cx - 13 * sc, cy - 2 * sc, cx + 13 * sc,
                                cy + 10 * sc, fill=c("scale"), outline="")
            cv.create_rectangle(cx - 16 * sc, cy - 6 * sc, cx + 16 * sc,
                                cy - 2 * sc, fill=c("scale"), outline="")
            cv.create_rectangle(cx + 2 * sc, cy + 1 * sc, cx + 12 * sc,
                                cy + 6 * sc, fill=c("lcd"), outline="")
        elif part == "wplate":
            cv.create_rectangle(cx - 16 * sc, cy - 3 * sc, cx + 16 * sc,
                                cy + 4 * sc, fill=c("ply"), outline=c("plyed"))
        elif part == "stone":
            cv.create_polygon(cx - 13 * sc, cy + 8 * sc, cx - 11 * sc,
                              cy - 7 * sc, cx + 12 * sc, cy - 9 * sc,
                              cx + 14 * sc, cy + 7 * sc,
                              fill=c("stone"), outline=c("stonedk"))
        elif part == "tube":
            cv.create_rectangle(cx - 6 * sc, cy - 16 * sc, cx + 6 * sc,
                                cy + 14 * sc, fill=c("tube"), outline=c("tubeed"))
            cv.create_rectangle(cx - 6 * sc, cy - 12 * sc, cx - 2 * sc,
                                cy - 6 * sc, fill=c("magbody"), outline="")
            cv.create_rectangle(cx + 2 * sc, cy - 12 * sc, cx + 6 * sc,
                                cy - 6 * sc, fill=c("magbody"), outline="")
        elif part == "rodmag":
            cv.create_rectangle(cx - 4 * sc, cy - 14 * sc, cx + 4 * sc,
                                cy, fill=c("magN"), outline="")
            cv.create_rectangle(cx - 4 * sc, cy, cx + 4 * sc, cy + 14 * sc,
                                fill=c("magS"), outline="")
        elif part == "ruler":
            cv.create_rectangle(cx - 5 * sc, cy - 16 * sc, cx + 5 * sc,
                                cy + 16 * sc, fill=c("ruler"), outline="#b8a878")
            for k in range(-14, 15, 4):
                cv.create_line(cx - 5 * sc, cy + k * sc, cx - 1 * sc,
                               cy + k * sc, fill=c("rulerink"))
        elif part == "stick":
            cv.create_rectangle(cx - 3 * sc, cy - 16 * sc, cx + 3 * sc,
                                cy + 16 * sc, fill="#d9b98a", outline="#a98a5f")


# -------------------------------------------------------------------------
#  application
# -------------------------------------------------------------------------
class App(object):

    def __init__(self, root, seed=None):
        self.root = root
        self.rig = Rig(seed)
        root.title(T(u"IPhO 2010 크로아티아 – 실험 1 & 2 가상실험실  [HaslaLab]",
                     u"IPhO 2010 Croatia – Experiments 1 & 2 virtual lab  [HaslaLab]"))
        root.configure(bg=COL["bg"])
        root.minsize(1120, 760)
        root.geometry("1320x880")
        self._style()
        self.status = tk.StringVar(value=T(
            u"부품 상자에서 장비를 끌어다 놓아 실험을 조립하세요.",
            u"Drag the equipment out of the parts box to build the experiment."))
        top = tk.Frame(root, bg=COL["bg"])
        top.pack(fill="x", padx=10, pady=(8, 0))
        tk.Label(top, text=T(u"IPhO 2010 · 실험 1 (얇은 판의 굽힘) · 실험 2 (자석)",
                             u"IPhO 2010 · Exp. 1 (bending of a sheet) · Exp. 2 (magnets)"),
                 bg=COL["bg"], fg=COL["ink"],
                 font=("Helvetica", 12, "bold")).pack(side="left")
        tk.Label(top, text=T(u"세션 번호", u"session") + ": %d" % self.rig.truth.seed,
                 bg=COL["bg"], fg=COL["dim"],
                 font=("Consolas", 10)).pack(side="right")
        self.nb = ttk.Notebook(root)
        self.nb.pack(fill="both", expand=True, padx=10, pady=8)
        self.tab_asm = tk.Frame(self.nb, bg=COL["bg"])
        self.tab_bench = tk.Frame(self.nb, bg=COL["bg"])
        self.nb.add(self.tab_asm, text=T(u"  조립  ", u"  Assembly  "))
        self.nb.add(self.tab_bench, text=T(u"  실험대  ", u"  Bench  "))
        tk.Label(root, textvariable=self.status, bg=COL["panel"], fg=COL["ink"],
                 anchor="w", font=("Helvetica", 10), padx=8, pady=4
                 ).pack(fill="x", side="bottom")
        self._build_assembly()
        self._build_bench()
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.refresh())
        self.refresh()

    def _style(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TNotebook", background=COL["bg"], borderwidth=0)
        st.configure("TNotebook.Tab", background=COL["panel"],
                     foreground=COL["ink"], padding=(14, 7),
                     font=("Helvetica", 10, "bold"))
        st.map("TNotebook.Tab", background=[("selected", "#3b4454")])
        st.configure("TCombobox", fieldbackground="#2f3542", background="#2f3542")

    # ============================================================ assembly
    def _build_assembly(self):
        f = self.tab_asm
        self.acv = tk.Canvas(f, bg=COL["bg"], highlightthickness=0)
        self.acv.pack(side="left", fill="both", expand=True)
        self.pal = Palette(self.acv, self.rig)
        self.ascene = Scene(self.acv, self.rig, ppm=1.55)
        self.ascene.ox, self.ascene.oy = 640.0, 500.0
        self._drag = None
        self.acv.bind("<Configure>", self._a_config)
        self.acv.bind("<ButtonPress-1>", self._a_press)
        self.acv.bind("<B1-Motion>", self._a_motion)
        self.acv.bind("<ButtonRelease-1>", self._a_release)
        self.acv.bind("<Button-3>", self._a_right)
        self.acv.bind("<MouseWheel>", self._a_wheel)
        self.acv.bind("<Button-4>", lambda e: self._a_wheel(e, 120))
        self.acv.bind("<Button-5>", lambda e: self._a_wheel(e, -120))
        side = tk.Frame(f, bg=COL["panel"], width=330)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)
        self._foil_workshop(side)

    def _hdr(self, parent, txt):
        tk.Label(parent, text=txt, bg=COL["panel"], fg=COL["ink"], anchor="w",
                 font=("Helvetica", 10, "bold")).pack(fill="x", padx=10,
                                                      pady=(9, 2))

    def _foil_workshop(self, side):
        self._hdr(side, T(u"필름 작업대 (실험 1)", u"Foil workbench (Exp. 1)"))
        tk.Label(side, text=T(u"OHP 필름 210 × 297 mm\n파랑 200 µm · 무색 150 µm",
                              u"transparency 210 x 297 mm\nblue 200 um · colourless 150 um"),
                 bg=COL["panel"], fg=COL["dim"], justify="left", anchor="w",
                 font=("Helvetica", 8)).pack(fill="x", padx=10)
        self.v_kind = tk.StringVar(value="blue")
        row = tk.Frame(side, bg=COL["panel"])
        row.pack(fill="x", padx=10, pady=3)
        for val, lab in (("blue", T(u"파랑", u"blue")),
                         ("clear", T(u"무색", u"clear"))):
            tk.Radiobutton(row, text=lab, variable=self.v_kind, value=val,
                           bg=COL["panel"], fg=COL["ink"], selectcolor="#1b1f26",
                           activebackground=COL["panel"],
                           activeforeground=COL["ink"],
                           font=("Helvetica", 9)).pack(side="left")
        # cutting
        row = tk.Frame(side, bg=COL["panel"])
        row.pack(fill="x", padx=10, pady=2)
        tk.Label(row, text=T(u"가위 재단  가로", u"cut  w"), bg=COL["panel"],
                 fg=COL["dim"], font=("Helvetica", 9)).pack(side="left")
        self.v_cw = tk.StringVar(value="210")
        self.v_ch = tk.StringVar(value="297")
        tk.Entry(row, textvariable=self.v_cw, width=5, bg="#1b1f26",
                 fg=COL["ink"], insertbackground=COL["ink"]).pack(side="left", padx=2)
        tk.Label(row, text=u"×", bg=COL["panel"], fg=COL["dim"]).pack(side="left")
        tk.Entry(row, textvariable=self.v_ch, width=5, bg="#1b1f26",
                 fg=COL["ink"], insertbackground=COL["ink"]).pack(side="left", padx=2)
        tk.Button(row, text=T(u"재단", u"cut"), command=self._cut,
                  bg="#3b4454", fg=COL["ink"], relief="flat",
                  font=("Helvetica", 9)).pack(side="left", padx=4)
        # rolling
        row = tk.Frame(side, bg=COL["panel"])
        row.pack(fill="x", padx=10, pady=(8, 2))
        tk.Label(row, text=T(u"원통 축 방향", u"cylinder axis"), bg=COL["panel"],
                 fg=COL["dim"], font=("Helvetica", 9)).pack(side="left")
        self.v_axis = tk.StringVar(value="short")
        cb = ttk.Combobox(row, textvariable=self.v_axis, width=16, state="readonly",
                          values=(T(u"짧은 변(210) ∥ 축", u"short edge (210) || axis"),
                                  T(u"긴 변(297) ∥ 축", u"long edge (297) || axis")))
        cb.current(0)
        cb.pack(side="left", padx=4)
        self.cb_axis = cb
        row = tk.Frame(side, bg=COL["panel"])
        row.pack(fill="x", padx=10, pady=2)
        tk.Label(row, text=T(u"겹침 [mm]", u"overlap [mm]"), bg=COL["panel"],
                 fg=COL["dim"], font=("Helvetica", 9)).pack(side="left")
        self.v_ov = tk.StringVar(value="5")
        tk.Entry(row, textvariable=self.v_ov, width=5, bg="#1b1f26",
                 fg=COL["ink"], insertbackground=COL["ink"]).pack(side="left", padx=4)
        tk.Button(row, text=T(u"말아서 원통 만들기", u"roll it up"),
                  command=self._roll, bg="#3b4454", fg=COL["ink"], relief="flat",
                  font=("Helvetica", 9)).pack(side="left", padx=4)
        self._hdr(side, T(u"만든 원통", u"cylinders made"))
        self.lb_cyl = tk.Listbox(side, height=5, bg="#1b1f26", fg=COL["ink"],
                                 selectbackground="#3b4454", highlightthickness=0,
                                 font=("Consolas", 9))
        self.lb_cyl.pack(fill="x", padx=10)
        row = tk.Frame(side, bg=COL["panel"])
        row.pack(fill="x", padx=10, pady=4)
        tk.Button(row, text=T(u"나무판 위에 올리기", u"put on the board"),
                  command=self._put_cyl, bg="#3b4454", fg=COL["ink"],
                  relief="flat", font=("Helvetica", 9)).pack(side="left")
        tk.Button(row, text=T(u"치우기", u"take off"), command=self._take_cyl,
                  bg="#3b4454", fg=COL["ink"], relief="flat",
                  font=("Helvetica", 9)).pack(side="left", padx=4)
        self._hdr(side, T(u"프레스 윗판", u"upper plate of the press"))
        tk.Button(side, text=T(u"윗판 뒤집기 (알루미늄 봉 방향)",
                               u"turn the plate over (aluminium rod)"),
                  command=self._flip_plate, bg="#3b4454", fg=COL["ink"],
                  relief="flat", font=("Helvetica", 9)).pack(fill="x", padx=10)
        self.lb_plate = tk.Label(side, text="", bg=COL["panel"], fg=COL["dim"],
                                 anchor="w", justify="left",
                                 font=("Helvetica", 8), wraplength=300)
        self.lb_plate.pack(fill="x", padx=10, pady=(2, 0))
        self._hdr(side, T(u"투명 원통 놓는 방향 (실험 2)",
                          u"orientation of the cylinder (Exp. 2)"))
        self.v_orient = tk.StringVar(value="upright")
        for val, lab in (("upright", T(u"세움 – 링자석 위",
                                       u"standing, ring end up")),
                         ("inverted", T(u"세움 – 링자석 아래",
                                        u"standing, ring end down")),
                         ("horizontal", T(u"작업대에 눕힘",
                                          u"lying on the bench"))):
            tk.Radiobutton(side, text=lab, variable=self.v_orient,
                           value=val, command=self._set_orient, bg=COL["panel"],
                           fg=COL["ink"], selectcolor="#1b1f26",
                           activebackground=COL["panel"],
                           activeforeground=COL["ink"], anchor="w",
                           font=("Helvetica", 9)).pack(fill="x", padx=10)

    # ---- assembly callbacks
    def _cut(self):
        try:
            w = float(self.v_cw.get())
            h = float(self.v_ch.get())
        except ValueError:
            self.say(T(u"숫자를 입력하세요.", u"Enter numbers."))
            return
        sid, wh = self.rig.cut_sheet(self.v_kind.get(), w, h)
        self.say(T(u"필름을 %.1f × %.1f mm로 잘랐습니다. (%s)",
                   u"Sheet cut to %.1f x %.1f mm. (%s)") % (wh[0], wh[1], sid))
        self._last_sheet = sid
        self.refresh()

    def _roll(self):
        try:
            ov = float(self.v_ov.get())
        except ValueError:
            ov = 5.0
        axis = "short" if self.cb_axis.current() == 0 else "long"
        sid = getattr(self, "_last_sheet", None)
        cid, msg = self.rig.roll_foil(self.v_kind.get(), axis, ov, sid)
        self._last_sheet = None
        if cid is None:
            self.say(msg)
        else:
            c = self.rig.cylinders[cid]
            self.say(msg + "  (%s: l=%.0f mm, %s=%.0f mm)"
                     % (cid, c["l"], T(u"둘레", u"circumference"), c["circ"]))
        self.refresh()

    def _sel_cyl(self):
        i = self.lb_cyl.curselection()
        if not i:
            return None
        return self._cyl_ids[i[0]]

    def _put_cyl(self):
        cid = self._sel_cyl()
        if cid is None:
            self.say(T(u"목록에서 원통을 고르세요.", u"Select a cylinder first."))
            return
        self.say(self.rig.put_cylinder(cid)[1])
        self.refresh()

    def _take_cyl(self):
        self.say(self.rig.take_cylinder()[1])
        self.refresh()

    def _flip_plate(self):
        self.say(self.rig.flip_plate()[1])
        self.refresh()

    def _set_orient(self):
        ok, msg = self.rig.set_tube_orientation(self.v_orient.get())
        if not ok:
            self.v_orient.set(self.rig.tube_orient)
        self.say(msg)
        self.refresh()

    # ---- assembly mouse
    def _a_config(self, e):
        if not self.ascene.user_moved:
            self.ascene.fit(Palette.W)
        self.refresh()

    def _a_press(self, e):
        p = self.pal.hit(e.x, e.y)
        if p:
            self._drag = p
            return
        self._pan0 = (e.x, e.y, self.ascene.ox, self.ascene.oy)

    def _a_motion(self, e):
        if self._drag:
            self.refresh()
            self.acv.create_text(e.x + 12, e.y, anchor="w",
                                 text=PART_LABEL[self._drag],
                                 fill=COL["ghost"], font=("Helvetica", 10, "bold"))
            self.pal._icon(self._drag, e.x - 8, e.y, cv=self.acv, sc=0.8)
            return
        if getattr(self, "_pan0", None):
            x0, y0, ox, oy = self._pan0
            self.ascene.ox = ox + (e.x - x0)
            self.ascene.oy = oy + (e.y - y0)
            self.ascene.user_moved = True
            self.refresh()

    def _a_release(self, e):
        if not self._drag:
            self._pan0 = None
            return
        part = self._drag
        self._drag = None
        if e.x <= Palette.W:
            self.refresh()
            return
        ok, msg = self.rig.place(part)
        self.say(msg)
        if ok and part == "tube":
            self.v_orient.set(self.rig.tube_orient)
        self.refresh()

    def _a_right(self, e):
        if e.x <= Palette.W:
            return
        name = self.ascene.hit(e.x, e.y)
        if name in ("press", "scale", "wplate", "stone", "tube", "ruler", "stick"):
            self.say(self.rig.remove(name)[1])
        elif name == "rodmag":
            self.say(self.rig.remove_rod()[1] if self.rig.rod_where == "tube"
                     else T(u"막대자석은 상자에 있습니다.",
                            u"The rod magnet is in the box."))
        elif name == "foil":
            self.say(self.rig.take_cylinder()[1])
        self.refresh()

    def _a_wheel(self, e, d=None):
        d = e.delta if d is None else d
        self.ascene.ppm *= 1.12 if d > 0 else 1 / 1.12
        self.ascene.ppm = max(0.7, min(6.0, self.ascene.ppm))
        self.ascene.user_moved = True
        self.refresh()

    # =============================================================== bench
    def _build_bench(self):
        f = self.tab_bench
        self.bcv = tk.Canvas(f, bg=COL["bg"], highlightthickness=0)
        self.bcv.pack(side="left", fill="both", expand=True)
        self.bscene = Scene(self.bcv, self.rig, ppm=2.4)
        self.bcv.bind("<Configure>", self._b_config)
        self.bcv.bind("<ButtonPress-1>", self._b_press)
        self.bcv.bind("<B1-Motion>", self._b_motion)
        self.bcv.bind("<ButtonRelease-1>", self._b_release)
        self.bcv.bind("<Button-3>", self._b_right)
        self.bcv.bind("<MouseWheel>", self._b_wheel)
        self.bcv.bind("<Button-4>", lambda e: self._b_wheel(e, 120))
        self.bcv.bind("<Button-5>", lambda e: self._b_wheel(e, -120))
        self.bcv.bind("<Shift-MouseWheel>", lambda e: self._b_wheel(e, fine=True))
        side = tk.Frame(f, bg=COL["panel"], width=350)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)
        # ---- balance
        self._hdr(side, T(u"전자저울", u"electronic balance"))
        box = tk.Frame(side, bg="#1b1f26")
        box.pack(fill="x", padx=10)
        self.lcd = tk.Label(box, text="", bg=COL["lcd"], fg=COL["lcdink"],
                            font=SEG, anchor="e", padx=10, pady=4)
        self.lcd.pack(fill="x", padx=6, pady=6)
        row = tk.Frame(side, bg=COL["panel"])
        row.pack(fill="x", padx=10, pady=3)
        for txt, cmd in ((u"UNIT", self._unit), (u"Z / T", self._tare),
                         (u"ON / OFF", self._power)):
            tk.Button(row, text=txt, command=cmd, bg=COL["btn"], fg="white",
                      relief="flat", font=("Helvetica", 9, "bold"),
                      padx=6).pack(side="left", padx=3)
        # ---- press
        self._hdr(side, T(u"나사 프레스 (나비너트)", u"screw press (wing nut)"))
        self.lb_cnt = tk.Label(side, text="", bg="#1b1f26", fg="#f0d78a",
                               font=("Consolas", 13), anchor="e", padx=8, pady=3)
        self.lb_cnt.pack(fill="x", padx=10)
        g = tk.Frame(side, bg=COL["panel"])
        g.pack(fill="x", padx=10, pady=3)
        for txt, deg in ((u"−10", -3600), (u"−1", -360), (u"−45°", -45),
                         (u"+45°", 45), (u"+1", 360), (u"+10", 3600)):
            tk.Button(g, text=txt, command=lambda d=deg: self._nut(d),
                      bg="#3b4454", fg=COL["ink"], relief="flat", width=4,
                      font=("Helvetica", 9)).pack(side="left", padx=2)
        tk.Button(side, text=T(u"회전 카운터 0으로", u"zero the revolution counter"),
                  command=self._zero, bg="#3b4454", fg=COL["ink"], relief="flat",
                  font=("Helvetica", 9)).pack(fill="x", padx=10, pady=2)
        tk.Button(side, text=T(u"전체 보기 (화면 맞춤)", u"fit the view"),
                  command=self._fit, bg="#3b4454", fg=COL["ink"], relief="flat",
                  font=("Helvetica", 9)).pack(fill="x", padx=10, pady=2)
        tk.Label(side, text=T(u"너트 위에서 휠을 돌리면 ±45°, Shift+휠은 ±5°",
                              u"wheel over the nut: +-45 deg, Shift+wheel: +-5 deg"),
                 bg=COL["panel"], fg=COL["dim"], anchor="w",
                 font=("Helvetica", 8), wraplength=320).pack(fill="x", padx=10)
        # ---- ruler
        self._hdr(side, T(u"자로 재기", u"read the ruler"))
        self.v_meas = tk.StringVar()
        self.cb_meas = ttk.Combobox(side, textvariable=self.v_meas, width=30,
                                    state="readonly", values=(
                                        T(u"윗판–나무판 간격", u"plate/board gap"),
                                        T(u"필름 원통 지름", u"foil cylinder diameter"),
                                        T(u"막대자석 위치 z", u"rod magnet position z"),
                                        T(u"막대자석 길이", u"rod magnet length"),
                                        T(u"링자석 바깥지름/두께", u"ring dia./thickness"),
                                        T(u"투명 원통 지름/높이", u"cylinder dia./height")))
        self.cb_meas.current(0)
        self.cb_meas.pack(fill="x", padx=10, pady=2)
        tk.Button(side, text=T(u"읽기", u"read"), command=self._read,
                  bg="#3b4454", fg=COL["ink"], relief="flat",
                  font=("Helvetica", 9)).pack(fill="x", padx=10)
        # ---- rod magnet
        self._hdr(side, T(u"막대자석 / 나무 막대", u"rod magnet / wooden stick"))
        g = tk.Frame(side, bg=COL["panel"])
        g.pack(fill="x", padx=10)
        tk.Button(g, text=T(u"넣기", u"insert"), command=self._insert,
                  bg="#3b4454", fg=COL["ink"], relief="flat", width=7,
                  font=("Helvetica", 9)).pack(side="left", padx=2)
        tk.Button(g, text=T(u"빼기", u"take out"), command=self._pull,
                  bg="#3b4454", fg=COL["ink"], relief="flat", width=7,
                  font=("Helvetica", 9)).pack(side="left", padx=2)
        tk.Button(g, text=T(u"뒤집기", u"flip"), command=self._fliprod,
                  bg="#3b4454", fg=COL["ink"], relief="flat", width=7,
                  font=("Helvetica", 9)).pack(side="left", padx=2)
        g = tk.Frame(side, bg=COL["panel"])
        g.pack(fill="x", padx=10, pady=3)
        tk.Label(g, text=T(u"막대로 밀기 [mm]", u"push [mm]"), bg=COL["panel"],
                 fg=COL["dim"], font=("Helvetica", 9)).pack(side="left")
        for txt, dz in ((u"−20", -20.0), (u"−5", -5.0), (u"−1", -1.0),
                        (u"+1", 1.0), (u"+5", 5.0), (u"+20", 20.0)):
            tk.Button(g, text=txt, command=lambda d=dz: self._push(d),
                      bg="#3b4454", fg=COL["ink"], relief="flat", width=3,
                      font=("Helvetica", 9)).pack(side="left", padx=1)
        self.lb_rod = tk.Label(side, text="", bg=COL["panel"], fg=COL["dim"],
                               anchor="w", justify="left", font=("Helvetica", 8),
                               wraplength=320)
        self.lb_rod.pack(fill="x", padx=10)
        # ---- log
        self._hdr(side, T(u"기록", u"log"))
        self.txt = tk.Text(side, height=11, bg="#1b1f26", fg=COL["ink"],
                           highlightthickness=0, font=("Consolas", 9), wrap="word")
        self.txt.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.txt.configure(state="disabled")

    # ---- bench callbacks
    def _fit(self):
        self.bscene.user_moved = False
        self.bscene.fit()
        self.refresh()

    def _unit(self):
        self.rig.scale_toggle_unit()
        self.refresh()

    def _tare(self):
        self.say(self.rig.scale_tare()[1])
        self.refresh()

    def _power(self):
        self.rig.scale_power()
        self.refresh()

    def _nut(self, deg):
        ok, msg = self.rig.turn_nut(deg)
        if msg:
            self.say(msg)
        self.refresh()

    def _zero(self):
        self.say(self.rig.zero_counter()[1])
        self.refresh()

    def _read(self):
        what = ("gap", "cyl", "rod_z", "rod_len", "ring", "tube")[
            self.cb_meas.current()]
        v, msg = self.rig.measure(what)
        self.log(msg)
        self.say(msg)
        self.refresh()

    def _insert(self):
        self.say(self.rig.insert_rod()[1])
        self.refresh()

    def _pull(self):
        self.say(self.rig.remove_rod()[1])
        self.refresh()

    def _fliprod(self):
        self.say(self.rig.flip_rod()[1])
        self.refresh()

    def _push(self, dz):
        ok, msg = self.rig.push_rod(dz)
        if msg:
            self.say(msg)
        self.refresh()

    def _b_config(self, e):
        if not self.bscene.user_moved:
            self.bscene.fit()
        self.refresh()

    def _b_press(self, e):
        name = self.bscene.hit(e.x, e.y)
        if name == "btn_unit":
            self._unit()
            return
        if name == "btn_tare":
            self._tare()
            return
        if name == "btn_pw":
            self._power()
            return
        if name == "nut":
            self._nutdrag = (e.y, self.rig.turns)
            return
        if name == "rodmag" and self.rig.rod_where in ("tube", "hand"):
            self._roddrag = (e.x, e.y, self.rig.rod_z)
            return
        self._bpan0 = (e.x, e.y, self.bscene.ox, self.bscene.oy)

    def _b_motion(self, e):
        if getattr(self, "_nutdrag", None):
            y0, t0 = self._nutdrag
            self.rig.turns = t0
            self.rig._last_dir = 0
            self.rig.turn_nut((e.y - y0) * 4.0 - (self.rig.turns - t0) * 360.0)
            self.refresh()
            return
        if getattr(self, "_roddrag", None):
            x0, y0, z0 = self._roddrag
            if self.rig.tube_orient == "horizontal":
                d = (e.x - x0) / self.bscene.ppm
            else:
                d = -(e.y - y0) / self.bscene.ppm * self.rig.z_sign()
            self.rig.rod_z = z0
            self.rig.push_rod(d)
            self.refresh()
            return
        if getattr(self, "_bpan0", None):
            x0, y0, ox, oy = self._bpan0
            self.bscene.ox = ox + (e.x - x0)
            self.bscene.oy = oy + (e.y - y0)
            self.bscene.user_moved = True
            self.refresh()

    def _b_release(self, e):
        self._nutdrag = None
        self._roddrag = None
        self._bpan0 = None

    def _b_right(self, e):
        self._a_right(e)

    def _b_wheel(self, e, d=None, fine=False):
        d = e.delta if d is None else d
        if self.bscene.hit(e.x, e.y) == "nut":
            self._nut((5.0 if fine else 45.0) * (1 if d > 0 else -1))
            return
        self.bscene.ppm *= 1.12 if d > 0 else 1 / 1.12
        self.bscene.ppm = max(0.9, min(14.0, self.bscene.ppm))
        self.bscene.user_moved = True
        self.refresh()

    # =============================================================== common
    def say(self, msg):
        if msg:
            self.status.set(msg)

    def log(self, msg):
        if not msg:
            return
        self.txt.configure(state="normal")
        self.txt.insert("end", msg + "\n")
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def refresh(self):
        R = self.rig
        # assembly tab
        self.acv.delete("all")
        self.ascene.draw()
        self.pal.draw()
        self._cyl_ids = sorted(R.cylinders.keys())
        sel = self.lb_cyl.curselection()
        self.lb_cyl.delete(0, "end")
        for cid in self._cyl_ids:
            c = R.cylinders[cid]
            self.lb_cyl.insert("end", "%s %-5s l=%3.0f  %s%s"
                               % (cid, T(u"파랑", u"blue") if c["kind"] == "blue"
                                  else T(u"무색", u"clear"), c["l"],
                                  T(u"둘레", u"circ") + "=%.0f" % c["circ"],
                                  "  *" if cid == R.cyl_on_plate else ""))
        if sel:
            try:
                self.lb_cyl.selection_set(sel[0])
            except tk.TclError:
                pass
        self.lb_plate.configure(
            text=T(u"현재: 알루미늄 봉이 아래를 향합니다 (실험 2 배치)",
                   u"now: aluminium rod points down (Exp. 2)") if R.plate_flipped
            else T(u"현재: 알루미늄 봉이 위를 향합니다 (실험 1 배치)",
                   u"now: aluminium rod points up (Exp. 1)"))
        self.v_orient.set(R.tube_orient)
        # bench tab
        self.bcv.delete("all")
        self.bscene.draw()
        self.lcd.configure(text=R.scale_display() or " ")
        self.lb_cnt.configure(text=T(u"회전", u"turns") + ": " +
                              R.counter_display())
        if R.rod_where == "tube":
            s = T(u"막대자석: 원통 안", u"rod magnet: inside the cylinder")
            if R.rod_contact:
                s += " · " + T(u"알루미늄 봉에 닿아 있음",
                               u"pressed against the aluminium rod")
        elif R.rod_where == "hand":
            s = T(u"막대자석: 손에 있음", u"rod magnet: in your hand")
        else:
            s = T(u"막대자석: 상자 안", u"rod magnet: in the box")
        s += "  |  " + (T(u"극 방향 평행 (↑↑)", u"poles parallel")
                        if R.rod_orient > 0
                        else T(u"극 방향 반평행 (↑↓)", u"poles antiparallel"))
        self.lb_rod.configure(text=s)
        if R.msg:
            self.log(R.msg)
            R.msg = ""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    seed = None
    for i, a in enumerate(argv):
        if a == "--seed" and i + 1 < len(argv):
            try:
                seed = int(argv[i + 1])
            except ValueError:
                pass
    root = tk.Tk()
    app = App(root, seed)
    if "--shot" in argv:
        out = argv[argv.index("--shot") + 1]
        root.update()
        root.update_idletasks()

        def grab(tab, path):
            app.nb.select(tab)
            root.update()
            root.update_idletasks()
            root.after(120)
            import subprocess
            subprocess.call(["import", "-window", str(root.winfo_id()), path])
        grab(0, out + "_asm.png")
        grab(1, out + "_bench.png")
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
