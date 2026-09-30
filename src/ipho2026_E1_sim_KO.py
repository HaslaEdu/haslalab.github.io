# -*- coding: utf-8 -*-
# IPhO 2026 experimental exam -- virtual laboratory
# KO and EN editions differ only in the LANG line below.
"""
IPhO 2026 (56th, Bucaramanga) -- VIRTUAL LABORATORY
===================================================
"Ideal Gas, Vapor Pressure and Heat Conduction"  [20 pts / 5 h]

This is a hands-on bench, not a problem solver.  Nothing is filled, measured,
tabulated, fitted or plotted for you.  You operate the real hardware:

  * turn the POWER on at the rear of the electronic module
  * open / close valves A, B, C, D and E by clicking their handles
  * drag the ends of hose A and hose C into the containers
  * run the pump to fill / drain / recirculate the outer cylinder
  * drag a syringe to a bottle, pull its plunger to load liquid,
    plug it into hose D and push the plunger to feed the inner cylinder
  * switch the heater on and read the four sensors and the stopwatch
  * read the liquid heights h and H off the centimetre scale, by eye

The only numbers the apparatus will ever show you are the ones a real
instrument shows: INT./ATM. pressure, INT./EXT. temperature and the timer.

Requires: Python 3.8+  (tkinter only -- no third-party packages)
"""

# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
#  LANGUAGE.  build_editions.py freezes this into the KO / EN editions.
# --------------------------------------------------------------------------
LANG = "KO"          # the EN edition differs only in this line


def T(ko, en):
    """Bilingual string.  Instrument silkscreen stays English on purpose."""
    return ko if LANG == "KO" else en


TR = T          # the name the call sites use: several physics routines have a
                # local temperature called T, which would shadow the helper


import math
import random
import time

# ==========================================================================
#  CONSTANTS / GEOMETRY  (problem sheet, Fig. 17)
# ==========================================================================
NA      = 6.022e23
C0      = 4.184e3
RHO0    = 1000.0
M_W     = 18.02e-3
M_AIR   = 28.96e-3
R_GAS   = 8.314
T0K     = 273.15
RHO_AIR = 1.12
RHO_PG  = 1036.0
G_ACC   = 9.81
# surface tension [N/m] and contact angle on acrylic
GAMMA_W20, DGAMMA_W = 0.0728, -1.5e-4      # water, per K about 20 C
GAMMA_PG = 0.0360                          # propylene glycol
THETA_W, THETA_PG = math.radians(70.0), math.radians(30.0)

D_IC_IN  = 33.7e-3
WALL     = 3.4e-3
D_OC_OUT = 74.8e-3
R1       = D_IC_IN / 2.0
R2       = R1 + WALL
R_OC_IN  = D_OC_OUT / 2.0 - WALL

A_IC = math.pi * R1 ** 2                       # 8.92 cm^2
A_OC = math.pi * (R_OC_IN ** 2 - R2 ** 2)      # 23.4 cm^2
L_IC = 0.140                                   # 14.0 cm of usable IC scale
L_OC = 0.180                                   # 18.0 cm of usable OC scale

P_ATM = 95.2e3
T_AMB = 24.0

LAMBDA_ACRYLIC = 0.250
R_ENV_OC = 2.35
R_ENV_IC = 150.0
HEATER_POWER = 200.0

P_GAIN, P_OFFSET = 1.0190, -1.4407e3           # decalibrated pressure sensor
CC_SLOPE, CC_CONST = 4700.0, 16.7875           # ln(Pv[kPa]) = C - S/T


# --- vapour pressure: pre-computed table + linear interpolation ----------
_PV_T0, _PV_DT, _PV_N = 250.0, 0.05, 3400
_PV = [1.0e3 * math.exp(CC_CONST - CC_SLOPE / (_PV_T0 + i * _PV_DT))
       for i in range(_PV_N + 1)]


def pv_water(T):
    """Saturated vapour pressure of water [Pa] (LUT, ~8x faster than exp)."""
    u = (T - _PV_T0) * 20.0                      # 1 / _PV_DT
    i = int(u)
    if i < 0:
        return _PV[0]
    if i >= _PV_N:
        return 1.0e3 * math.exp(CC_CONST - CC_SLOPE / T)
    f = u - i
    a = _PV[i]
    return a + (_PV[i + 1] - a) * f


# ==========================================================================
#  BENCH OBJECTS
# ==========================================================================
class Container(object):
    """A bottle / jug / tub sitting on the bench."""

    def __init__(self, key, label, vol, T, kind, cap):
        self.key = key
        self.label = label
        self.vol = float(vol)        # mL
        self.T = float(T)            # degC
        self.kind = kind             # 'water' | 'pg' | 'waste'
        self.cap = float(cap)        # mL

    def take(self, mL):
        mL = min(mL, self.vol)
        self.vol -= mL
        return mL

    def give(self, mL, T, kind):
        if self.vol < 1e-9:
            self.kind = kind
        elif kind != self.kind and self.kind != 'waste':
            self.kind = 'mixed'
        tot = self.vol + mL
        if tot > 0:
            self.T = (self.T * self.vol + T * mL) / tot
        self.vol = min(self.cap, tot)


class Syringe(object):
    """100 mL syringe (Fig. 7).  Plunger position = held volume."""

    def __init__(self, key, label):
        self.key = key
        self.label = label
        self.cap = 100.0
        self.vol = 0.0               # mL of liquid inside the barrel
        self.plunger = 0.0           # mL swept volume the plunger allows
        self.kind = None             # 'water' | 'pg'
        self.T = 24.0
        self.has_plunger = True
        self.attached = None         # None | 'D' | container key
        self.x, self.y = 0.0, 0.0    # bench position (px, set by the GUI)


class Lab(object):
    """The complete apparatus.  step(dt) advances the physics."""

    # ------------------------------------------------------------------
    def __init__(self, seed=None):
        # ----每 session the apparatus is a different individual ---------
        if seed is None:
            seed = random.randrange(1, 999999)
        self.seed = seed
        g = random.Random(seed)
        self.rng = random.Random(seed * 7919 + 13)

        # hidden physical truths (never shown, never printed)
        self.lam = g.uniform(0.235, 0.265)          # W/(m K), acrylic
        self.cc_s = g.uniform(4600.0, 4800.0)       # Qv / R   [K]
        pv339 = g.uniform(17.6, 19.6)               # kPa at 339 K
        self.cc_c = math.log(pv339) + self.cc_s / 339.0
        self._pv_tab = [1.0e3 * math.exp(self.cc_c - self.cc_s /
                                         (_PV_T0 + i * _PV_DT))
                        for i in range(_PV_N + 1)]
        self.P_atm0 = g.uniform(94.4e3, 96.0e3)
        self.P_atm = self.P_atm0
        self._drift = 0.0
        self.T_amb = g.uniform(22.0, 26.0)
        self.P_heat = g.uniform(180.0, 220.0)
        self.Renv_oc = g.uniform(2.05, 2.75)
        self.Renv_ic = g.uniform(100.0, 200.0)
        # true bore of this particular pair of cylinders (Fig. 17 +/- 0.1 mm)
        self.r1 = R1 + g.uniform(-1e-4, 1e-4)
        self.r2 = R2 + g.uniform(-1e-4, 1e-4)
        self.A_ic = math.pi * self.r1 ** 2
        self.A_oc = math.pi * ((R_OC_IN + g.uniform(-1e-4, 1e-4)) ** 2
                               - self.r2 ** 2)
        # sensor calibration (the sheet warns they may be decalibrated)
        self.p_gain = g.uniform(1.004, 1.034)
        self.p_off = g.uniform(-3.0e3, 0.5e3)
        self.ti_gain = g.uniform(0.9965, 1.0035)
        self.ti_off = g.uniform(-0.4, 0.4)
        self.te_gain = g.uniform(0.9965, 1.0035)
        self.te_off = g.uniform(-0.4, 0.4)
        self.tau_probe = g.uniform(5.0, 9.0)        # s, thermal lag
        self.tau_press = 1.2

        self.t = 0.0
        self.power = False
        self.pump = False
        self.heater = False
        self.heater_hot = False       # 65 C cut-out latched (indicator red)
        self.timer = 0.0
        self.timer_run = False
        self.graph_mode = False

        self.valve = {k: False for k in "ABCDE"}

        # outer cylinder
        self.h_oc = 0.0
        self.T_oc = self.T_amb
        self.strat = 0.0

        # inner cylinder
        self.ic_kind = None           # None | 'water' | 'pg' | 'mixed'
        self.h_ic = 0.0
        self.T_ic = self.T_amb
        self.n_air = self.P_atm * self.A_ic * L_IC / (R_GAS * (self.T_amb + T0K))

        # hoses
        self.hoseA_in = None          # container key the free end is dipped in
        self.hoseC_in = None
        self.clip = {'A': False, 'C': False}   # Fig. 14 clips
        self.hconn = {'A': True, 'C': True, 'D': True}   # push-fit, Fig. 16
        self.primed = False           # pump primed (purged with valve B)
        self._purging = False
        self._slip = 0.0

        self.containers = {
            'pg':    Container('pg', 'PG 100 mL', 100.0,
                                self.T_amb, 'pg', 120.0),
            'cold':  Container('cold', TR('찬물', 'cold water'), 500.0, g.uniform(3.0, 7.0),
                                'water', 600.0),
            'room':  Container('room', TR('상온수', 'room-temp. water'), 1500.0,
                                self.T_amb, 'water', 1500.0),
            'pour':  Container('pour', TR('비커', 'pouring jug'), 0.0,
                                self.T_amb, 'water', 1200.0),
            'jug':   Container('jug', TR('폐수통', 'waste jug'), 0.0,
                                self.T_amb, 'waste', 3000.0),
        }
        self.syr = {'w': Syringe('w', TR('물 주사기', 'water syringe')),
                    'p': Syringe('p', TR('PG 주사기', 'PG syringe'))}

        self.s_tint = self.T_ic
        self.s_text = self.T_oc
        self.s_press = self.P_atm
        self.msg = ""
        self.msg_t = -99.0

    # ------------------------------------------------------------- helpers
    def say(self, s):
        self.msg, self.msg_t = s, self.t

    def pv(self, T):
        """This apparatus's own saturated vapour pressure curve [Pa]."""
        u = (T - _PV_T0) * 20.0
        i = int(u)
        if i < 0:
            return self._pv_tab[0]
        if i >= _PV_N:
            return 1.0e3 * math.exp(self.cc_c - self.cc_s / T)
        a = self._pv_tab[i]
        return a + (self._pv_tab[i + 1] - a) * (u - i)

    # ---------------------------------------------------------- meniscus
    def meniscus(self):
        """Wall rise and volume of the meniscus in the IC.

        The bore (33.7 mm) is far wider than the capillary length, so the
        surface is flat in the middle and only curves up in a ring of order
        lambda_c at the wall:  rise = lambda_c * sqrt(2 (1 - sin theta)).
        Returns (rise [m], ring width [m], volume [m^3]).
        """
        if self.ic_kind is None or self.h_ic <= 1e-6:
            return 0.0, 0.0, 0.0
        if self.ic_kind == 'pg':
            g, rho, th = GAMMA_PG, RHO_PG, THETA_PG
        else:
            g = max(0.02, GAMMA_W20 + DGAMMA_W * (self.T_ic - 20.0))
            rho, th = RHO0, THETA_W
            if self.ic_kind == 'mixed':
                g *= 0.75
        lam = math.sqrt(g / (rho * G_ACC))          # capillary length
        rise = lam * math.sqrt(max(0.0, 2.0 * (1.0 - math.sin(th))))
        width = 1.6 * lam
        # the wetting ring, a roughly triangular section around the wall
        vol = math.pi * (self.r1 ** 2 - max(0.0, self.r1 - width) ** 2) \
            * rise * 0.5
        return rise, width, vol

    @property
    def v_men(self):
        return self.meniscus()[2]

    @property
    def H(self):
        """Air column above the flat part of the surface (what you read)."""
        return max(0.0, L_IC - self.h_ic)

    @property
    def V_air(self):
        """The meniscus eats into the gas space above the flat level."""
        return max(1e-9, self.A_ic * self.H - self.v_men)

    @property
    def R_wall(self):
        h = max(min(self.h_ic, self.h_oc), 0.005)
        return math.log(self.r2 / self.r1) / (2.0 * math.pi * self.lam * h)

    @property
    def open_column(self):
        """Syringe barrel with the plunger removed, plugged into hose D."""
        s = self.syr['w']
        if s.has_plunger:
            return False
        if s.attached == 'Dh':
            return True
        return s.attached == 'D' and self.valve['D'] and self.hconn['D']

    def ic_vented(self):
        """Is the confined air open to the atmosphere anywhere?"""
        if self.valve['E']:
            return True
        free = [s for s in self.syr.values() if s.attached in ('D', 'Dh')]
        if not self.hconn['D']:
            # the hose is off the board: the IC line is a bare open tube
            return not any(s.attached == 'Dh' for s in free)
        if self.valve['D']:
            return not any(s.attached == 'D' for s in free)
        return False

    def reseal(self):
        """Recompute the trapped amount of dry air whenever the IC is open."""
        T = self.T_ic + T0K
        p = self.P_atm - (self.pv(T) if self.ic_kind in ('water', 'mixed')
                          else 0.0)
        self.n_air = p * self.V_air / (R_GAS * T)

    # ------------------------------------------------------------ readouts
    def true_pressure(self):
        T = self.T_ic + T0K
        if self.ic_vented() and not self.open_column:
            return self.P_atm
        p = self.n_air * R_GAS * T / max(self.V_air, 1e-9)
        if self.ic_kind in ('water', 'mixed'):
            p += self.pv(T)
        return p

    def r_pint(self):
        if not self.power:
            return None
        p = (self.p_gain * self.s_press + self.p_off
             + self.rng.gauss(0, 40))
        return round(p / 1000.0, 1)

    def r_patm(self):
        if not self.power:
            return None
        return round(self.P_atm / 1000.0 + self.rng.gauss(0, 0.03), 1)

    def r_tint(self):
        if not self.power:
            return None
        return round(self.ti_gain * self.s_tint + self.ti_off
                     + self.rng.gauss(0, 0.05), 1)

    def r_text(self):
        if not self.power:
            return None
        return round(self.te_gain * self.s_text + self.te_off
                     + self.rng.gauss(0, 0.05), 1)

    # ------------------------------------------------------------- actions
    def press_power(self):
        self.power = not self.power
        if not self.power:
            self.heater = self.pump = False
        self.say(TR('전원 ', 'Power ') + (TR('켜짐', 'on') if self.power
                                        else TR('꺼짐', 'off')))

    def press_button(self, n):
        if not self.power:
            self.say(TR('전자 모듈에 전원이 들어와 있지 않습니다.', 'The electronic module has no power.'))
            return
        if n == 1:
            self.timer_run = not self.timer_run
        elif n == 2:
            self.timer = 0.0
        elif n == 3:
            self.graph_mode = not self.graph_mode
            self.say(TR('그래프 화면은 이 실험에서 쓰지 않습니다.', 'Graph display is not used in the experiments.'))
        elif n == 4:
            if self.h_oc < 0.04:
                self.say(TR('! 히터가 물에 완전히 잠겨 있어야 합니다.', '! The heater must be fully under water.'))
                return
            if self.heater_hot and not self.heater:
                self.say(TR('! 표시등이 아직 빨간색입니다 - 60 C 아래로 내려갈 때까지 기다리세요.', '! The indicator is still red - wait until it drops below 60 C.'))
                return
            self.heater = not self.heater

    def press_pump(self):
        if not self.power:
            self.say(TR('전자 모듈에 전원이 들어와 있지 않습니다.', 'The electronic module has no power.'))
            return
        self.pump = not self.pump

    def toggle_valve(self, v):
        self.valve[v] = not self.valve[v]
        if v == 'B':
            if self.valve['B'] and self.pump:
                self._purging = True          # purge stroke started
            elif not self.valve['B'] and self._purging:
                self._purging = False
                self.primed = True
                self.say(TR('펌프 공기빼기 완료 - 이제 물을 제대로 끌어올립니다.', 'Pump primed - it now draws water properly.'))
        if v in "DE" and not self.ic_vented():
            self.reseal()

    def toggle_hose(self, k):
        """Push the hoop and pull the hose out, or push it fully in."""
        self.hconn[k] = not self.hconn[k]
        if self.hconn[k]:
            self.say(TR('호스 %s를 포트에 꽂았습니다', 'Hose %s pushed into its port') % k)
        else:
            self.say(TR('호스 %s를 포트에서 빼냈습니다', 'Hose %s pulled out of its port') % k)

    def toggle_clip(self, k):
        self.clip[k] = not self.clip[k]
        self.say(TR('호스 %s %s', 'Hose %s %s') % (
            k, TR('클립으로 고정됨', 'clipped') if self.clip[k]
            else TR('고정 해제', 'unclipped')))

    def pour(self, src, dst, mL=150.0):
        """Tip one container into another (Fig. 12 pouring container)."""
        a, b = self.containers[src], self.containers[dst]
        got = a.take(min(mL, max(0.0, b.cap - b.vol)))
        if got <= 0:
            self.say(TR('! 따를 것이 없습니다.', '! Nothing to pour.'))
            return
        b.give(got, a.T, a.kind)
        self.say(TR('%.0f mL 따름  %s -> %s', 'Poured %.0f mL  %s -> %s') % (got, a.label, b.label))

    # ---------------------------------------------------- syringe handling
    def syringe_pull(self, key, dmL):
        """Pull (dmL>0) or push (dmL<0) the plunger by dmL millilitres."""
        s = self.syr[key]
        if not s.has_plunger:
            self.say(TR('피스톤이 제거된 상태입니다.', 'The plunger is out.'))
            return
        new = min(s.cap, max(0.0, s.plunger + dmL))
        d = new - s.plunger
        if abs(d) < 1e-9:
            return
        s.plunger = new

        # --- nozzle dipped in a container -----------------------------
        if s.attached in self.containers:
            c = self.containers[s.attached]
            if d > 0:                                   # draw liquid up
                got = c.take(d)
                if got > 0:
                    if s.kind and s.kind != c.kind:
                        s.kind = 'mixed'
                        self.say(TR('! 주사기 안에서 두 액체가 섞였습니다.', '! The two liquids have mixed in the syringe.'))
                    else:
                        s.kind = c.kind
                    s.T = c.T
                    s.vol += got
            else:                                        # expel back
                give = min(s.vol, -d)
                if give > 0:
                    c.give(give, s.T, s.kind or 'water')
                    s.vol -= give
            return

        # --- plugged into hose D --------------------------------------
        if s.attached == 'Dh':                 # straight onto hose D
            if not self.valve['E']:
                self.say(TR('! 밸브 E를 여세요.', '! Open valve E.'))
                s.plunger -= d
                return
            if d < 0:
                give = min(s.vol, -d, (L_IC - self.h_ic) * self.A_ic * 1e6)
                if give > 0:
                    self._add_to_ic(give, s.kind, s.T)
                    s.vol -= give
            else:
                take = min(d, self.h_ic * self.A_ic * 1e6)
                if take > 0:
                    self.h_ic -= take * 1e-6 / self.A_ic
                    s.kind = self.ic_kind if not s.kind else s.kind
                    s.vol += take
                    if self.h_ic < 1e-4:
                        self.h_ic, self.ic_kind = 0.0, None
                    self.reseal()
            return

        if s.attached == 'D':
            if not self.hconn['D']:
                self.say(TR('! 호스 D가 포트에서 빠져 있습니다.', '! Hose D is out of its port.'))
                s.plunger -= d
                return
            if not self.valve['D']:
                self.say(TR('! 밸브 D가 닫혀 있습니다.', '! Valve D is closed.'))
                s.plunger -= d
                return
            if not self.valve['E']:
                self.say(TR('! 밸브 E도 여세요. 공기가 빠져나갈 수 없습니다.', '! Open valve E too: the air has nowhere to go.'))
                s.plunger -= d
                return
            if d < 0:                                   # push into the IC
                give = min(s.vol, -d, (L_IC - self.h_ic) * self.A_ic * 1e6)
                if give <= 0:
                    return
                self._add_to_ic(give, s.kind, s.T)
                s.vol -= give
            else:                                       # withdraw from the IC
                take = min(d, self.h_ic * self.A_ic * 1e6)
                if take <= 0:
                    return
                self.h_ic -= take * 1e-6 / self.A_ic
                if s.kind and self.ic_kind and s.kind != self.ic_kind:
                    s.kind = 'mixed'
                else:
                    s.kind = self.ic_kind
                s.vol += take
                if self.h_ic < 1e-4:
                    self.h_ic, self.ic_kind = 0.0, None
                self.reseal()
            return

        # --- free in the air ------------------------------------------
        if d < 0 and s.vol > 0:
            spill = min(s.vol, -d)
            s.vol -= spill
            self.say(TR('! 액체 %.0f mL를 실험대에 흘렸습니다.', '! Spilt %.0f mL on the bench.') % spill)

    def _add_to_ic(self, mL, kind, T):
        if kind is None:
            return
        first = self.h_ic <= 1e-6
        if self.ic_kind and kind != self.ic_kind:
            self.ic_kind = 'mixed'
            self.say(TR('! PG와 물은 섞입니다 - IC 내용물이 혼합물이 되었습니다. 비우고 세척하세요.', '! PG and water mix - the IC now holds a mixture. Empty and rinse it.'))
        else:
            self.ic_kind = kind
        m_old = RHO0 * self.A_ic * self.h_ic * 1000.0
        m_new = mL * 1e-3
        if m_old + m_new > 0:
            self.T_ic = (self.T_ic * m_old + T * m_new) / (m_old + m_new)
        dv = mL * 1e-6
        if first:
            dv -= self.v_men          # forming the meniscus swallows a little
        self.h_ic = min(L_IC - 0.002, self.h_ic + max(0.0, dv) / self.A_ic)
        self.reseal()

    def remove_plunger(self, key):
        s = self.syr[key]
        if s.has_plunger:
            if s.attached is None:
                self.say(TR('! 주사기를 먼저 연결하세요.', '! Connect the syringe first.'))
                return
            s.has_plunger = False
            self.say(TR('피스톤 제거 - 실린더가 대기에 열렸습니다.', 'Plunger removed - the barrel is open to the air.'))
        else:
            s.has_plunger = True
            s.plunger = s.vol
            self.say(TR('피스톤을 다시 끼웠습니다.', 'Plunger put back.'))

    # ----------------------------------------------------------- time step
    def step(self, dt):
        self.t += dt
        # first-order thermal lag of the two probes, pneumatic lag of the
        # pressure line, and a slow drift of the local atmosphere
        f = 1.0 - math.exp(-dt / self.tau_probe)
        self.s_tint += (self.T_ic - self.s_tint) * f
        self.s_text += (self.T_oc + self.strat - self.s_text) * f
        self.s_press += (self.true_pressure() - self.s_press) * \
            (1.0 - math.exp(-dt / self.tau_press))
        self._drift += (-self._drift * dt / 900.0 +
                        self.rng.gauss(0.0, 6.0) * math.sqrt(dt))
        self.P_atm = self.P_atm0 + self._drift
        if self.timer_run:
            self.timer += dt

        # ---------------- pump -------------------------------------
        rate = 22.0 * dt * (1.0 if self.primed else 0.05)    # mL per step
        if self.pump and self.power:
            fill = self.valve['A'] and not self.valve['B'] and not self.valve['C']
            drain = self.valve['C'] and self.valve['B'] and not self.valve['A']
            recirc = self.valve['B'] and not self.valve['A'] and not self.valve['C']
            # an unsecured hose works its way out of the container (Fig. 14)
            for k, key in (('A', 'hoseA_in'), ('C', 'hoseC_in')):
                if getattr(self, key) and not self.clip[k]:
                    self._slip += dt
                    if self._slip > 40.0:
                        self._slip = 0.0
                        setattr(self, key, None)
                        self.say(TR('! 호스 %s가 용기에서 빠졌습니다 - 클립으로 고정하세요.', '! Hose %s slipped out of the container - clip it.') % k)
            if fill and self.hconn['A'] and not self.hoseA_in:
                self.say(TR('! 호스 A가 어느 용기에도 들어 있지 않습니다.', '! Hose A is not in any container.'))
            elif drain and self.hconn['C'] and not self.hoseC_in:
                self.say(TR('! 호스 C가 어느 용기에도 들어 있지 않습니다.', '! Hose C is not in any container.'))
            elif self.valve['A'] and self.valve['C']:
                self.say(TR('! 밸브 A와 C가 동시에 열려 있습니다.', '! Valves A and C are both open.'))
            if fill and not self.hconn['A']:
                self.say(TR('! 호스 A가 포트에서 빠져 있습니다.', '! Hose A is out of its port.'))
            elif drain and not self.hconn['C']:
                self.say(TR('! 호스 C가 포트에서 빠져 있습니다.', '! Hose C is out of its port.'))
            if fill and self.hoseA_in and self.hconn['A']:
                c = self.containers[self.hoseA_in]
                if self.h_oc >= L_OC - 1e-4:
                    self.say(TR('! OC가 가득 찼습니다 - 물이 넘치고 있습니다.', '! The OC is full - water is overflowing.'))
                got = c.take(min(rate, max(0.0, (L_OC - self.h_oc) * self.A_oc * 1e6)))
                if got > 0:
                    m_old = RHO0 * self.A_oc * self.h_oc
                    m_new = got * 1e-6 * RHO0
                    self.T_oc = (self.T_oc * m_old + c.T * m_new) / max(
                        m_old + m_new, 1e-9)
                    self.h_oc += got * 1e-6 / self.A_oc
                    self.strat *= 0.5
                    if self.h_oc > 0.170:
                        self.say(TR('! 수위를 실린더 덮개보다 최소 1 cm 아래로 유지하세요.', '! Keep the level at least 1 cm below the cover.'))
            elif drain and self.hoseC_in and self.hconn['C']:
                out = min(rate, self.h_oc * self.A_oc * 1e6)
                if out > 0:
                    self.containers[self.hoseC_in].give(out, self.T_oc, 'water')
                    self.h_oc -= out * 1e-6 / self.A_oc

        # ---------------- heater -----------------------------------
        Q = 0.0
        if self.heater and self.power and self.h_oc > 0.04:
            if self.T_oc >= 65.0:
                self.heater = False
                self.heater_hot = True
            else:
                Q = self.P_heat
        elif self.heater and self.h_oc <= 0.04:
            self.heater = False
            self.say(TR('! 히터가 꺼졌습니다: 물에 잠겨 있지 않습니다.', '! Heater off: it is not under water.'))
        if self.heater_hot and self.T_oc < 60.0:
            self.heater_hot = False

        # ---------------- stratification ---------------------------
        recirc = (self.pump and self.power and self.valve['B']
                  and not self.valve['A'] and not self.valve['C'])
        if recirc:
            self.strat *= math.exp(-dt / 8.0)
        else:
            tgt = 2.5 if Q > 0 else 0.0
            self.strat += (tgt - self.strat) * (1.0 - math.exp(-dt / 90.0))

        # ---------------- thermal network --------------------------
        C_ic = C0 * RHO0 * self.A_ic * self.h_ic + 1005.0 * RHO_AIR * self.V_air
        C_oc = C0 * RHO0 * self.A_oc * self.h_oc + 40.0
        C_ic = max(C_ic, 2.0)
        C_oc = max(C_oc, 40.0)

        if self.h_oc > 0.005 and self.h_ic > 0.005:
            q = (self.T_oc - self.T_ic) / self.R_wall
        else:
            q = (self.T_oc - self.T_ic) / 60.0
        self.T_ic += (q - (self.T_ic - self.T_amb) / self.Renv_ic) / C_ic * dt
        self.T_oc += (Q - q - (self.T_oc - self.T_amb) / self.Renv_oc) / C_oc * dt

        # ---------------- open water column (Part B) ---------------
        if self.open_column and self.ic_kind in ('water', 'mixed'):
            s = self.syr['w']
            T = self.T_ic + T0K
            p_dry = max(self.P_atm - self.pv(T), 1.0)
            H_new = self.n_air * R_GAS * T / (self.A_ic * p_dry)
            H_new = min(max(H_new, 0.004), L_IC - 0.002)
            dV = self.A_ic * (H_new - self.H) * 1e6     # mL pushed out of IC
            if dV > 0:
                dV = min(dV, s.cap - s.vol)
                if s.vol >= s.cap - 1e-6:
                    self.say(TR('! 주사기 실린더가 넘치고 있습니다.', '! The syringe barrel is overflowing.'))
            else:
                dV = -min(-dV, s.vol)
                if s.vol <= 1e-6:
                    self.say(TR('! 주사기 실린더가 비었습니다 - IC로 공기가 빨려 들어갑니다.', '! The syringe barrel is empty - air is drawn into the IC.'))
                    self.reseal()
            s.vol += dV
            self.h_ic = L_IC - (self.H + dV * 1e-6 / self.A_ic)



# ==========================================================================
#  THE BENCH  --  layout is recomputed for whatever window size you give it
# ==========================================================================
import math
import sys
import tkinter as tk


from tkinter import font as tkfont

ELEV = 0.20                       # sin(camera elevation) -> ellipse squash
BENCH = "#0d1015"
STEEL = "#9aa7b4"
ACRYL = "#8095a8"
INK = "#dfe7ee"
DIM = "#7f8a95"


def _lerp(c1, c2, f):
    f = 0.0 if f < 0 else (1.0 if f > 1 else f)
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * f)
                                   for i in range(3))


def _ramp(i):
    f = i / 63.0
    return (_lerp("#12507f", "#2f8fc4", f / 0.62) if f < 0.62
            else _lerp("#2f8fc4", "#63c3e2", (f - 0.62) / 0.38))


_WRAMP = [_ramp(i) for i in range(64)]
_WTOP = [_lerp(c, "#ffffff", 0.42) for c in _WRAMP]
_WDARK = [_lerp(c, "#02121e", 0.30) for c in _WRAMP]


def wi(T):
    i = int((T - 5.0) * (63.0 / 62.0))
    return 0 if i < 0 else (63 if i > 63 else i)


def pick_font():
    """First Hangul-capable family that exists, else Consolas."""
    try:
        fams = set(tkfont.families())
    except Exception:
        fams = set()
    for f in (["맑은 고딕", "Malgun Gothic", "NanumGothicCoding",
               "NanumGothic", "AppleGothic", "Noto Sans CJK KR",
               "D2Coding"] if LANG == "KO" else []):
        if f in fams:
            return f
    return "Consolas"

class Bench(object):

    # ==================================================================
    def __init__(self, session=None):
        if session is None:
            for i, a in enumerate(sys.argv):
                if a == "--session" and i + 1 < len(sys.argv):
                    session = int(sys.argv[i + 1])
        self.lab = Lab(seed=session)
        self.speed = 1.0
        self.running = True
        self.drag = None
        self.last = time.time()
        self.acc = 0.0
        self.frame = 0
        self.D, self.C = {}, {}
        self.coff = {}
        self._imgs = []
        self._resize_job = None
        self._size = (0, 0)

        self.root = tk.Tk()
        self.root.title(TR('IPhO 2026 -- 실험 시험 | 가상 실험실', 'IPhO 2026 -- experimental exam | virtual laboratory'))
        self.root.configure(bg=BENCH)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry("%dx%d+0+0" % (sw, sh - 60))
        try:
            self.root.state("zoomed")
        except tk.TclError:
            pass
        self.cv = tk.Canvas(self.root, bg=BENCH, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)

        self.cv.bind("<Button-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_move)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Configure>", self.on_resize)
        self.cv.bind("<MouseWheel>", self.on_wheel)          # Windows / macOS
        self.cv.bind("<Button-4>", lambda e: self.on_wheel(e, +1))   # X11
        self.cv.bind("<Button-5>", lambda e: self.on_wheel(e, -1))
        self.root.bind("<space>", lambda e: self.toggle_run())
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<F11>", self.toggle_full)
        self.full = False
        self.tick()

    def toggle_full(self, _e=None):
        self.full = not self.full
        self.root.attributes("-fullscreen", self.full)

    # ------------------------------------------------------------ resize
    def on_resize(self, e):
        if (e.width, e.height) == self._size or e.width < 300:
            return
        self._size = (e.width, e.height)
        if self._resize_job:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(120, self.rebuild)

    def rebuild(self):
        self._resize_job = None
        w, h = self._size
        self.cv.delete("all")
        self.D, self.C = {}, {}
        self._imgs = []
        self.frame = 0                      # force a full panel update
        self.layout(w, h)
        self.build()
        self.refresh()

    # =============================================================== layout
    #  Fixed 1920 x 1010 design.  At that size every photograph is blitted
    #  1:1, so the panels are pixel-identical to the figures of the sheet.
    #  Smaller windows scale the whole bench uniformly.
    def layout(self, W, H):
        k = min(W / 1920.0, H / 1010.0)
        self.k = k
        ox = (W - 1920.0 * k) / 2.0
        oy = (H - 1010.0 * k) / 2.0
        self.k, self.m = k, 14 * k

        def P(x, y, w, h):
            return (ox + x * k, oy + y * k, ox + (x + w) * k, oy + (y + h) * k)
        self.P = P

        def F(sz, b=False, mono=False):
            return tkfont.Font(family="Consolas" if mono else fam,
                               size=max(6, int(sz * k)),
                               weight="bold" if b else "normal")
        fam = pick_font()
        self.f_s, self.f_m = F(8), F(10)
        self.f_b, self.f_lcd = F(13, True), F(19, True, mono=True)

        # ---- left column : the chamber ---------------------------------
        self.PXCM = 29.0 * k
        self.CX = ox + 209 * k
        self.YB = oy + 810 * k
        self.YTOP = self.YB - 18.0 * self.PXCM

        def mm(v):
            return v * self.PXCM / 10.0
        self.mm = mm
        self.W_OC_O = mm(74.8 / 2.0)
        self.W_OC_I = mm(74.8 / 2.0 - 3.4)
        self.W_IC_O = mm(33.7 / 2.0 + 3.4)
        self.W_IC_I = mm(33.7 / 2.0)
        self.R_STUD = self.W_OC_O + 5 * k
        self.X_STUD_F = self.W_OC_O * 0.69
        self.X_STUD_R = self.W_OC_O * 0.45
        self.DY_STUD = self.R_STUD * 0.866 * ELEV
        self.FLANGE_W, self.FLANGE_H = self.W_OC_O + 15 * k, 17 * k
        self.COVER_W, self.COVER_H = self.W_OC_O + 2 * k, 15 * k
        self.BASE_W, self.BASE_H = self.W_OC_O + 30 * k, 26 * k
        self.X_HEAT = -(self.W_IC_O + self.W_OC_I) / 2.0 - 8 * k
        self.X_PROBE = (self.W_IC_O + self.W_OC_I) / 2.0 + 4 * k

        # ---- centre column : Fig. 3 over Fig. 6 -------------------------
        self.MOD = P(420, 26, 560, 386)
        self.BOARD = P(420, 440, 560, 470)

        # ---- right column 1 : Fig. 5, Fig. 4, Fig. 8, containers --------
        self.SIDE = P(996, 30, 470, 170)
        self.REAR = P(996, 226, 330, 156)
        self.PUMPP = P(1276, 410, 190, 230)
        self.CONT = {}
        for i, (key, w, h) in enumerate((('pg', 54, 132), ('cold', 62, 156),
                                         ('room', 70, 168), ('pour', 84, 140),
                                         ('jug', 96, 104))):
            x = 1000 + i * 86
            self.CONT[key] = P(x, 908 - h, w, h)

        # ---- right column 2 : notation, Fig. 17, syringes ---------------
        self.NOTE = P(1466, 26, 440, 116)
        self.CARD17 = P(1466, 152, 440, 176)
        self.SH = 240 * k
        self.SW = self.SH * 0.20
        self.SYR_HOME = {'w': (ox + 1560 * k, oy + 430 * k),
                         'p': (ox + 1760 * k, oy + 430 * k)}
        for key, (x, y) in self.SYR_HOME.items():
            sy = self.lab.syr[key]
            if getattr(sy, 'placed', None) != 'D':
                sy.x, sy.y = x, y

        # ---- ports are re-derived from the Fig. 6 photograph in panels()
        self.VALVE_XY = {v: (0, 0) for v in "ABCD"}
        self.HOSE_PORT = {'A': (0, 0), 'C': (0, 0)}
        self.SYR_PORT = (0, 0)
        self.VY1 = self.BOARD[1] + 0.20 * (self.BOARD[3] - self.BOARD[1])
        self.VY2 = self.BOARD[1] + 0.50 * (self.BOARD[3] - self.BOARD[1])
        self.W, self.H = W, H
        self.OX, self.OY = ox, oy
        self.FOOT = oy + 936 * k
        # hose ends follow the container they were put in
        for key, cont in (('A', self.lab.hoseA_in), ('C', self.lab.hoseC_in)):
            if cont:
                a, b_, d, e = self.CONT[cont]
                self.hose[key] = [(a + d) / 2.0, b_ + (e - b_) * 0.3]
            else:
                self.hose[key] = [ox + (700 + (0 if key == 'A' else 60)) * k,
                                  oy + 940 * k]

    def cm2y(self, cm):
        return self.YB - cm * self.PXCM

    def ell(self, xc, r, y, **kw):
        return self.cv.create_oval(xc - r, y - r * ELEV, xc + r,
                                   y + r * ELEV, **kw)

    # ================================================================ build
    def build(self):
        self.apparatus_back()
        self.dyn_liquids()
        self.apparatus_front()
        self.panels()
        self.dyn_rest()
        self.cv.tag_raise("scale")
        self.cv.tag_raise("top")

    # ----------------------------------------------------------- apparatus
    def apparatus_back(self):
        c, k = self.cv, self.k
        CX, YB = self.CX, self.YB
        self.ell(CX, self.BASE_W, YB, fill="#385063", outline="#93aabb")
        c.create_rectangle(CX - self.BASE_W, YB, CX + self.BASE_W,
                           YB + self.BASE_H, fill="#22303c", outline="")
        c.create_arc(CX - self.BASE_W, YB + self.BASE_H - self.BASE_W * ELEV,
                     CX + self.BASE_W, YB + self.BASE_H + self.BASE_W * ELEV,
                     start=180, extent=180, style="arc", outline="#93aabb",
                     width=2)
        for sg in (-1, 1):
            c.create_line(CX + sg * self.BASE_W, YB, CX + sg * self.BASE_W,
                          YB + self.BASE_H, fill="#93aabb", width=2)
        # four straight acrylic legs with a chamfered tip (Fig. 2)
        for th in (35.0, 145.0, 215.0, 325.0):
            lx = CX + self.BASE_W * 0.78 * math.cos(math.radians(th))
            ly = (YB + self.BASE_H +
                  self.BASE_W * 0.78 * math.sin(math.radians(th)) * ELEV)
            back = math.sin(math.radians(th)) > 0
            col = "#22303c" if back else "#2b3d4d"
            edge = "#7c93a6" if back else "#b6cadb"
            hgt = 104 * k
            c.create_polygon(lx - 10 * k, ly, lx + 10 * k, ly,
                             lx + 10 * k, ly + hgt - 14 * k,
                             lx + 4 * k, ly + hgt,
                             lx - 10 * k, ly + hgt, fill=col, outline=edge)
            c.create_line(lx - 6 * k, ly + 6 * k, lx - 6 * k, ly + hgt - 8 * k,
                          fill=edge)
        # heater cable leaving the underside
        c.create_line(CX + 6 * k, YB + self.BASE_H, CX + 14 * k,
                      YB + self.BASE_H + 70 * k, CX - 6 * k,
                      YB + self.BASE_H + 132 * k, smooth=True, fill="#15181c",
                      width=6)
        for th, rr in ((0, self.R_STUD), (180, self.R_STUD),
                       (60, self.X_STUD_R), (120, self.X_STUD_R),
                       (240, self.X_STUD_F), (300, self.X_STUD_F)):
            sgn = 1 if math.cos(math.radians(th)) >= 0 else -1
            nx = CX + sgn * rr
            ny = YB - self.R_STUD * math.sin(math.radians(th)) * ELEV
            c.create_rectangle(nx - 12 * k, ny - 4 * k, nx + 12 * k,
                               ny + 2 * k, fill="#b3bdc5", outline="#5d666f")
            c.create_rectangle(nx - 10 * k, ny - 13 * k, nx + 10 * k,
                               ny - 4 * k, fill="#96a1aa", outline="#5d666f")
        c.create_rectangle(CX - self.W_OC_O, self.YTOP, CX + self.W_OC_O, YB,
                           outline="", fill="#0f161d")
        self.ell(CX, self.W_OC_I, YB, outline="#33424f", fill="#0d141a")
        for sg in (-1, 1):
            self.stud(CX + sg * self.X_STUD_R, self.YTOP - 74 * k +
                      self.DY_STUD, YB + self.BASE_H + 6 * k + self.DY_STUD,
                      False)

    def apparatus_front(self):
        c, k = self.cv, self.k
        CX, YB, YT = self.CX, self.YB, self.YTOP
        for sg in (-1, 1):
            for i in range(5):
                f0 = self.W_OC_I + (self.W_OC_O - self.W_OC_I) * i / 5.0
                f1 = self.W_OC_I + (self.W_OC_O - self.W_OC_I) * (i + 1) / 5.0
                c.create_rectangle(CX + sg * f0, YT, CX + sg * f1, YB,
                                   outline="", fill=_lerp("#1d2a35", "#8ea6b8",
                                                          (i + 1) / 5.0))
            for i in range(4):
                f0 = self.W_IC_I + (self.W_IC_O - self.W_IC_I) * i / 4.0
                f1 = self.W_IC_I + (self.W_IC_O - self.W_IC_I) * (i + 1) / 4.0
                c.create_rectangle(CX + sg * f0, YT + 4, CX + sg * f1, YB,
                                   outline="", fill=_lerp("#1d2a35", "#8ea6b8",
                                                          (i + 1) / 4.0))
        px = CX + self.X_PROBE
        c.create_rectangle(px - 7 * k, self.cm2y(11.0), px + 7 * k, YB,
                           fill="#8b959e", outline="#c3ccd4")
        c.create_rectangle(px - 8 * k, self.cm2y(11.0) - 34 * k, px + 8 * k,
                           self.cm2y(11.0), fill="#15181c", outline="#3a4148")
        c.create_line(px, self.cm2y(11.0) - 34 * k, px + 10 * k, YT - 20 * k,
                      smooth=True, fill="#15181c", width=3)
        for sg in (-1, 1):
            self.stud(CX + sg * self.X_STUD_F, YT - 74 * k - self.DY_STUD,
                      YB + self.BASE_H + 6 * k - self.DY_STUD, True)
            self.stud(CX + sg * self.R_STUD, YT - 74 * k,
                      YB + self.BASE_H + 6 * k, True)
        for r in (self.W_OC_O, self.W_OC_I, self.W_IC_O, self.W_IC_I):
            c.create_arc(CX - r, YT - r * ELEV, CX + r, YT + r * ELEV,
                         start=180, extent=180, style="arc", outline="#b6c8d6")
            c.create_arc(CX - r, YT - r * ELEV, CX + r, YT + r * ELEV,
                         start=0, extent=180, style="arc", outline="#4a5a68")
            c.create_arc(CX - r, YB - r * ELEV, CX + r, YB + r * ELEV,
                         start=180, extent=180, style="arc", outline="#7f93a6")
        # ---- Fig. 2 head: black gasket, two clear discs with a gap,
        #      hex nuts + washers between them, chrome dome nuts on top ----
        c.create_arc(CX - self.W_OC_O, YT - 4 * k - self.W_OC_O * ELEV,
                     CX + self.W_OC_O, YT - 4 * k + self.W_OC_O * ELEV,
                     start=180, extent=180, style="arc", outline="#0c0f12",
                     width=7)
        fy = YT - self.FLANGE_H
        self.plate(CX, self.FLANGE_W, fy, self.FLANGE_H)
        cy = fy - 22 * k                      # visible gap between the discs
        self.plate(CX, self.COVER_W, cy - self.COVER_H, self.COVER_H)
        self.CY_COVER = cy - self.COVER_H
        for th, rr in ((0, self.R_STUD), (180, self.R_STUD),
                       (60, self.X_STUD_R), (120, self.X_STUD_R),
                       (240, self.X_STUD_F), (300, self.X_STUD_F)):
            sgn = 1 if math.cos(math.radians(th)) >= 0 else -1
            nx = CX + sgn * rr
            dy = -self.R_STUD * math.sin(math.radians(th)) * ELEV
            # hex nut + washer sitting on the lower flange, inside the gap
            c.create_rectangle(nx - 10 * k, fy + dy - 12 * k, nx + 10 * k,
                               fy + dy - 3 * k, fill="#96a1aa",
                               outline="#5d666f")
            c.create_rectangle(nx - 12 * k, fy + dy - 3 * k, nx + 12 * k,
                               fy + dy + 1 * k, fill="#b3bdc5",
                               outline="#5d666f")
            # chrome dome (acorn) nut on top of the cover plate
            ty = cy - self.COVER_H + dy
            c.create_rectangle(nx - 11 * k, ty - 3 * k, nx + 11 * k,
                               ty + 8 * k, fill="#8b959e", outline="#c3ccd4")
            c.create_arc(nx - 11 * k, ty - 21 * k, nx + 11 * k, ty + 5 * k,
                         start=0, extent=180, fill="#b7c2cb",
                         outline="#e6eef4")
            c.create_arc(nx - 6 * k, ty - 17 * k, nx + 2 * k, ty - 1 * k,
                         start=30, extent=110, style="arc", outline="#f2f7fb")
        # central push-fit fitting: chrome body + blue collet + the two hoses
        ty = cy - self.COVER_H
        c.create_rectangle(CX - 9 * k, ty - 26 * k, CX + 9 * k, ty,
                           fill="#aab4bc", outline="#dfe8ef")
        c.create_oval(CX - 13 * k, ty - 34 * k, CX + 13 * k, ty - 22 * k,
                      fill="#2f7fbf", outline="#8fc6e8")
        c.create_line(CX, ty - 30 * k, CX - 34 * k, ty - 62 * k,
                      CX - 96 * k, ty - 58 * k, smooth=True, fill="#54b6e8",
                      width=7)
        c.create_rectangle(CX + 16 * k, ty - 20 * k, CX + 28 * k, ty,
                           fill="#8b959e", outline="#c3ccd4")
        c.create_line(CX + 22 * k, ty - 20 * k, CX + 58 * k, ty - 52 * k,
                      CX + 128 * k, ty - 44 * k, smooth=True, fill="#15181c",
                      width=6)
        c.create_line(CX + 34 * k, ty + 2 * k, CX + 76 * k, ty - 34 * k,
                      CX + 132 * k, ty - 24 * k, smooth=True, fill="#15181c",
                      width=5)
        for cmv in range(0, 15):
            y = self.cm2y(cmv)
            c.create_line(CX - self.W_IC_I, y, CX - self.W_IC_I + 13 * k, y,
                          fill="#eaf4fc", tags="scale")
            c.create_line(CX + self.W_IC_I, y, CX + self.W_IC_I - 13 * k, y,
                          fill="#eaf4fc", tags="scale")
            c.create_text(CX - self.W_IC_I + 17 * k, y, anchor="w",
                          text="%d" % cmv, fill="#eaf4fc", font=self.f_s,
                          tags="scale")
            for j in range(1, 10):
                yy = y - j * self.PXCM / 10.0
                if yy > self.cm2y(14.2):
                    d = (8 if j == 5 else 5) * k
                    c.create_line(CX - self.W_IC_I, yy,
                                  CX - self.W_IC_I + d, yy, fill="#9fb6c8",
                                  tags="scale")
                    c.create_line(CX + self.W_IC_I, yy,
                                  CX + self.W_IC_I - d, yy, fill="#9fb6c8",
                                  tags="scale")
        c.create_text(CX - self.W_IC_I + 17 * k, self.cm2y(-0.5), anchor="w",
                      text="cm", fill="#eaf4fc", font=self.f_s, tags="scale")
        for cmv in range(0, 19):
            y = self.cm2y(cmv)
            c.create_line(CX + self.W_OC_O, y,
                          CX + self.W_OC_O - (10 if cmv % 5 == 0 else 6) * k,
                          y, fill="#7f97ab", tags="scale")
            if cmv % 5 == 0:
                c.create_text(CX + self.W_OC_O + 7 * k, y, anchor="w",
                              text="%d" % cmv, fill="#7f97ab", font=self.f_s,
                              tags="scale")
        c.create_text(CX + self.FLANGE_W + 10 * k, cy + 6 * k, anchor="w",
                      text="Fig. 2", fill=DIM, font=self.f_s)
        c.create_text(CX - self.W_OC_O - 10 * k, self.cm2y(17.4), anchor="e",
                      text="OC", fill=DIM, font=self.f_s)
        c.create_text(CX - self.W_IC_I - 8 * k, self.cm2y(13.4), anchor="e",
                      text="IC", fill=DIM, font=self.f_s)

    def ballvalve(self, cx, cy, rw, rh, tag):
        """Black plastic ball valve: chunky body, cross-head boss, shading."""
        c, k = self.cv, self.k
        c.create_rectangle(cx - rw, cy - rh, cx + rw, cy + rh, fill="#1b1e22",
                           outline="#727b83", width=2, tags=tag)
        c.create_rectangle(cx - rw, cy - rh, cx + rw, cy - rh * 0.62,
                           fill="#2c3238", outline="", tags=tag)
        c.create_rectangle(cx - rw, cy + rh * 0.66, cx + rw, cy + rh,
                           fill="#101215", outline="", tags=tag)
        c.create_oval(cx - rw * .46, cy - rh * .44, cx + rw * .46,
                      cy + rh * .44, fill="#262b31", outline="#5a636b",
                      tags=tag)
        c.create_line(cx - rw * .22, cy, cx + rw * .22, cy, fill="#8b959e",
                      tags=tag)
        c.create_line(cx, cy - rh * .22, cx, cy + rh * .22, fill="#8b959e",
                      tags=tag)

    def pushfit(self, x, y, side):
        """Chrome knurled push-fit body with a blue collet (Fig. 16)."""
        c, k = self.cv, self.k
        c.create_rectangle(x - 13 * k, y - 8 * k, x + 13 * k, y + 8 * k,
                           fill="#c3ccd4", outline="#eef3f7")
        for i in range(-3, 4):
            c.create_line(x + i * 4 * k, y - 8 * k, x + i * 4 * k, y + 8 * k,
                          fill="#8b959e")
        c.create_oval(x + side * 10 * k - 5 * k, y - 9 * k,
                      x + side * 10 * k + 5 * k, y + 9 * k, fill="#2f7fbf",
                      outline="#8fc6e8")

    def tee(self, x, y):
        c, k = self.cv, self.k
        c.create_rectangle(x - 16 * k, y - 9 * k, x + 16 * k, y + 9 * k,
                           fill="#17191c", outline="#3a4148")
        c.create_rectangle(x - 8 * k, y - 22 * k, x + 8 * k, y - 6 * k,
                           fill="#17191c", outline="#3a4148")
        c.create_oval(x - 8 * k, y - 26 * k, x + 8 * k, y - 16 * k,
                      fill="#2f7fbf", outline="#8fc6e8")

    # fractional positions of the live parts, measured on the photographs
    HOT = {'fig3': {'screen': (0.040, 0.030, 0.960, 0.590),
                    'btn': [(0.185, 0.740), (0.353, 0.740),
                            (0.520, 0.740), (0.688, 0.740)],
                    'btnw': 0.125, 'btnh': 0.130},
           'fig4': {'power': (0.590, 0.288, 0.136, 0.269)},
           'fig8': {'pump': (0.257, 0.434, 0.198, 0.153),
                    'out': (0.255, 0.660), 'in': (0.255, 0.870)},
           'fig6': {'A': (0.119, 0.187), 'B': (0.754, 0.203),
                    'C': (0.127, 0.494), 'D': (0.754, 0.769),
                    'hoseA': (0.010, 0.200), 'hoseC': (0.010, 0.505),
                    'hoseD': (0.960, 0.780)}}

    def panel(self, key, x0, y0, x1, y1):
        """Draw one instrument panel as 2D vector art inside the rect.
        The live parts sit at the fractions listed in HOT, which were
        measured off the photographs of the question sheet."""
        box = (x0, y0, x1 - x0, y1 - y0)
        getattr(self, "draw_" + key)(box)
        return box

    def hot(self, box, fx, fy):
        px, py, pw, ph = box
        return px + fx * pw, py + fy * ph

    # ------------------------------------------------ Fig. 3 : module
    def draw_fig3(self, box):
        c, k = self.cv, self.k
        x, y, w, h = box
        c.create_rectangle(x, y, x + w, y + h, fill="#15171a",
                           outline="#33383d", width=2)
        f = self.HOT['fig3']['screen']
        sx0, sy0 = x + f[0] * w, y + f[1] * h
        sx1, sy1 = x + f[2] * w, y + f[3] * h
        c.create_rectangle(sx0 - 4 * k, sy0 - 4 * k, sx1 + 4 * k,
                           sy1 + 4 * k, fill="#c9d2d9", outline="#eef3f7")
        c.create_rectangle(sx0, sy0, sx1, sy1, fill="#04090d",
                           outline="#63d3e8", width=2)
        c.create_text(x + 0.03 * w, y + h - 12 * k, anchor="w",
                      text=TR('전자 모듈', 'electronic module'), fill="#3a4148",
                      font=self.f_s)
        H = self.HOT['fig3']
        for i, (n, t) in enumerate((("1", "Start\nStop"), ("2", "Reset"),
                                    ("3", "Graphics"), ("4", "Heat"))):
            bx = x + H['btn'][i][0] * w
            by = y + H['btn'][i][1] * h
            bw, bh = H['btnw'] * w / 2.0, H['btnh'] * h / 2.0
            for dx, dy, col in ((3 * k, 3 * k, "#0d3b4c"), (0, 0, "#27c3f1")):
                c.create_oval(bx - bw + dx, by - bh + dy, bx - bw + 22 * k + dx,
                              by + bh + dy, fill=col, outline="")
                c.create_oval(bx + bw - 22 * k + dx, by - bh + dy, bx + bw + dx,
                              by + bh + dy, fill=col, outline="")
                c.create_rectangle(bx - bw + 11 * k + dx, by - bh + dy,
                                   bx + bw - 11 * k + dx, by + bh + dy,
                                   fill=col, outline="")
            c.create_text(bx, by, text=n, fill="#eaf6ff", font=self.f_lcd,
                          tags="btn%s" % n)
            c.create_rectangle(bx - bw, by - bh, bx + bw, by + bh, fill="",
                               outline="", tags="btn%s" % n)
            c.create_text(bx, by + bh + 22 * k, text=t, fill="#4ad07a",
                          font=self.f_m, justify="center")

    # ------------------------------------------------ Fig. 4 : rear
    def draw_fig4(self, box):
        c, k = self.cv, self.k
        x, y, w, h = box
        c.create_rectangle(x, y, x + w, y + h, fill="#111316",
                           outline="#2f353b", width=2)
        ix, iy = x + 0.22 * w, y + 0.30 * h
        c.create_rectangle(ix - 0.13 * w, iy - 0.20 * h, ix + 0.13 * w,
                           iy + 0.20 * h, fill="#1c2024", outline="#59616a",
                           width=2)
        c.create_polygon(ix - 0.11 * w, iy + 0.16 * h, ix + 0.11 * w,
                         iy + 0.16 * h, ix + 0.07 * w, iy + 0.19 * h,
                         ix - 0.07 * w, iy + 0.19 * h, fill="#0d1013",
                         outline="#59616a")
        for dx in (-0.045, 0.045):
            c.create_oval(ix + dx * w - 6 * k, iy - 6 * k, ix + dx * w + 6 * k,
                          iy + 6 * k, fill="#07090b", outline="#6b747c")
        for dx in (-0.115, 0.115):
            c.create_oval(ix + dx * w - 5 * k, iy - 0.17 * h,
                          ix + dx * w + 5 * k, iy - 0.17 * h + 10 * k,
                          fill="#95a0a8", outline="#cdd6dd")
        self.rocker(x + self.HOT['fig4']['power'][0] * w,
                    y + self.HOT['fig4']['power'][1] * h,
                    self.HOT['fig4']['power'][2] * w / 1.4, "power")
        c.create_text(ix, y + 0.80 * h, text="SOURCE AC", fill="#e8edf1",
                      font=self.f_m)
        c.create_text(x + self.HOT['fig4']['power'][0] * w, y + 0.80 * h,
                      text="POWER", fill="#e8edf1", font=self.f_m)

    # ------------------------------------------------ Fig. 5 : side face
    def draw_fig5(self, box):
        """Right-hand face of the module: two aviation connectors on the
        left, the heater connector and the pressure push-fit on the right,
        their labels stacked above / beside them as in the photograph."""
        c, k = self.cv, self.k
        x, y, w, h = box
        c.create_rectangle(x, y, x + w, y + h, fill="#0a0c0e",
                           outline="#2a3036", width=2)
        c.create_line(x + 4 * k, y + h - 8 * k, x + w - 4 * k, y + h - 8 * k,
                      fill="#5a3d2a", width=6)          # wooden bench edge
        for t1, t2, fx in (("External", "Temp.", 0.155),
                           ("Internal", "Temp.", 0.375)):
            px = x + fx * w
            c.create_text(px, y + 0.15 * h, text=t1, fill="#eef3f7",
                          font=self.f_m)
            c.create_text(px, y + 0.33 * h, text=t2, fill="#eef3f7",
                          font=self.f_m)
            cy = y + 0.56 * h
            rw = 0.050 * w
            ey = 0.30 * rw                      # ellipse squash
            # upper knurled nut
            c.create_rectangle(px - rw, cy - 0.08 * h, px + rw, cy,
                               fill="#8d8778", outline="")
            for i in range(-6, 7):
                c.create_line(px + i * rw / 6.5, cy - 0.08 * h,
                              px + i * rw / 6.5, cy, fill="#5f5a4e")
            c.create_oval(px - rw, cy - 0.08 * h - ey, px + rw,
                          cy - 0.08 * h + ey, fill="#b8b1a0",
                          outline="#ede7d6")
            c.create_line(px - rw, cy - 0.08 * h, px - rw, cy, fill="#ede7d6")
            c.create_line(px + rw, cy - 0.08 * h, px + rw, cy, fill="#ede7d6")
            # lower collar
            c.create_rectangle(px - rw * .78, cy, px + rw * .78,
                               cy + 0.09 * h, fill="#7e786b", outline="")
            c.create_oval(px - rw * .78, cy + 0.09 * h - ey * .8,
                          px + rw * .78, cy + 0.09 * h + ey * .8,
                          fill="#6d685c", outline="#c9c2ae")
            for sg in (-1, 1):
                c.create_line(px + sg * rw * .78, cy, px + sg * rw * .78,
                              cy + 0.09 * h, fill="#c9c2ae")
            # black cable leaving downwards
            c.create_line(px, cy + 0.11 * h, px - 0.035 * w, y + 0.92 * h,
                          px + 0.03 * w, y + h - 14 * k, smooth=True,
                          fill="#0d0f11", width=7)
        c.create_text(x + 0.62 * w, y + 0.15 * h, anchor="w", text="Water",
                      fill="#eef3f7", font=self.f_m)
        c.create_text(x + 0.62 * w, y + 0.33 * h, anchor="w", text="Heater",
                      fill="#eef3f7", font=self.f_m)
        c.create_text(x + 0.62 * w, y + 0.62 * h, anchor="w", text="Internal",
                      fill="#eef3f7", font=self.f_m)
        c.create_text(x + 0.62 * w, y + 0.80 * h, anchor="w",
                      text="pressure", fill="#eef3f7", font=self.f_m)
        px, cy = x + 0.885 * w, y + 0.30 * h
        rw, rh = 0.045 * w, 0.13 * h
        c.create_oval(px - rw, cy - rh, px + rw, cy + rh, fill="#a8853c",
                      outline="#e9cb86", width=2)
        for a2 in range(0, 360, 20):
            rr = math.radians(a2)
            c.create_line(px + rw * .76 * math.cos(rr),
                          cy + rh * .76 * math.sin(rr),
                          px + rw * math.cos(rr), cy + rh * math.sin(rr),
                          fill="#6e5320")
        c.create_oval(px - rw * .5, cy - rh * .5, px + rw * .5, cy + rh * .5,
                      fill="#7d6430", outline="#e9cb86")
        for dx in (-0.55, -0.15):
            c.create_line(px + dx * rw, cy + rh * .9,
                          px + dx * rw - 0.055 * w, y + 0.74 * h,
                          px + dx * rw - 0.075 * w, y + h - 12 * k,
                          smooth=True, fill="#efe9dc", width=4)
        cy = y + 0.72 * h
        c.create_rectangle(px - rw * 1.1, cy - 9 * k, px + rw * .2, cy + 9 * k,
                           fill="#c3ccd4", outline="#eef3f7")
        c.create_oval(px - rw * .1, cy - 11 * k, px + rw * .9, cy + 11 * k,
                      fill="#2f7fbf", outline="#8fc6e8")
        c.create_line(px + rw * .7, cy, x + w - 10 * k, cy - 0.10 * h,
                      x + w - 2 * k, y + h - 20 * k, smooth=True,
                      fill="#54b6e8", width=7)

    # ------------------------------------------------ Fig. 8 : pump
    def draw_fig8(self, box):
        c, k = self.cv, self.k
        x, y, w, h = box
        c.create_rectangle(x, y, x + w, y + h, fill="#0d0f11",
                           outline="#2a3036", width=2)
        c.create_text(x + 0.14 * w, y + 0.13 * h, anchor="w", text="PUMP",
                      fill="#eef3f7", font=self.f_b)
        f = self.HOT['fig8']['pump']
        self.rocker(x + f[0] * w, y + f[1] * h, f[2] * w / 1.4, "pump")
        for key, t in (('out', "OUT"), ('in', "IN")):
            fx, fy = self.HOT['fig8'][key]
            px, py = x + fx * w, y + fy * h
            r = 0.115 * w
            c.create_oval(px - r, py - r, px + r, py + r, fill="#0b0d0f",
                          outline="#3a4148")
            c.create_oval(px - r * .82, py - r * .82, px + r * .82,
                          py + r * .82, fill="#2f7fbf", outline="#8fc6e8",
                          width=3)
            c.create_oval(px - r * .34, py - r * .34, px + r * .34,
                          py + r * .34, fill="#08131c", outline="")
            c.create_text(px + r + 10 * k, py, anchor="w", text=t,
                          fill="#eef3f7", font=self.f_m)

    def rocker(self, cx, cy, r, tag):
        """Round illuminated rocker switch (Fig. 4 / Fig. 8)."""
        c, k = self.cv, self.k
        c.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#0f1215",
                      outline="#3a4148", width=2, tags=tag)
        c.create_oval(cx - r * .74, cy - r * .74, cx + r * .74, cy + r * .74,
                      fill="#c9261b", outline="#7a2a1e", width=2, tags=tag)
        c.create_oval(cx - r * .40, cy - r * .17, cx - r * .10, cy + r * .13,
                      outline="#f7ece5", width=2, tags=tag)
        c.create_line(cx + r * .10, cy, cx + r * .42, cy, fill="#f7ece5",
                      width=2, tags=tag)

    # ------------------------------------------------ Fig. 6 : board
    def draw_fig6(self, box):
        c, k = self.cv, self.k
        x, y, w, h = box
        c.create_rectangle(x, y, x + w, y + h, fill="#6b4a2c",
                           outline="#3d2713", width=2)
        px0, py0 = x + 0.022 * w, y + 0.028 * h
        px1, py1 = x + w - 0.022 * w, y + h - 0.028 * h
        c.create_rectangle(px0, py0, px1, py1, fill="#131518", outline="#000")
        c.create_rectangle(px0 + 9 * k, py0 + 9 * k, px1 - 9 * k, py1 - 9 * k,
                           outline="#c9d2d9")
        H = self.HOT['fig6']
        V = {key: (x + H[key][0] * w, y + H[key][1] * h) for key in "ABCD"}
        y1r, y2r = V['A'][1], V['C'][1]
        c.create_line(px0, y1r, px1, y1r, fill="#3aa0e0", width=8)
        c.create_line(px0, y2r, px1, y2r, fill="#e2721f", width=8)
        t1x, t2x = x + 0.40 * w, x + 0.47 * w
        c.create_line(t1x, y - 0.02 * h, t1x, y1r, t2x, y2r, smooth=True,
                      fill="#e2721f", width=8)
        # the syringe line: a clear hose comes up from under the board into
        # an elbow, runs right through valve D and leaves the right edge
        ex, ey = x + 0.380 * w, V['D'][1]
        c.create_line(ex, ey, ex, py1 + 6 * k, fill="#d8dde1", width=8)
        c.create_line(ex, ey, px1, ey, fill="#d8dde1", width=8)
        c.create_rectangle(ex - 15 * k, ey - 15 * k, ex + 15 * k, ey + 15 * k,
                           fill="#17191c", outline="#4a5158", width=2)
        c.create_oval(ex - 11 * k, ey + 12 * k, ex + 11 * k, ey + 28 * k,
                      fill="#2f7fbf", outline="#8fc6e8")
        c.create_oval(ex + 12 * k, ey - 11 * k, ex + 28 * k, ey + 11 * k,
                      fill="#2f7fbf", outline="#8fc6e8")
        for tx in (t1x, t2x):
            self.tee(tx, y1r if tx == t1x else y2r)
        for name, (fx, fy), anc in (('IN H2O   A',
                                     (0.055, 0.075), "w"),
                                    ('Water purge  B',
                                     (0.60, 0.075), "w"),
                                    ('OUT H2O  C',
                                     (0.055, 0.390), "w"),
                                    ("Outer cylinder", (0.97, 0.325), "e"),
                                    ("Outer cylinder", (0.97, 0.590), "e"),
                                    ("D", (0.70, 0.665), "w"),
                                    ("Syringe connection", (0.40, 0.94), "w")):
            c.create_text(x + fx * w, y + fy * h, anchor=anc, text=name,
                          fill="#d6dde3", font=self.f_m)
        for fx, fy, d in ((0.30, 0.105, 1), (0.30, 0.375, -1),
                          (0.90, 0.235, 1), (0.90, 0.505, 1),
                          (0.27, 0.660, -1), (0.27, 0.715, 1),
                          (0.90, 0.700, 1)):
            ax, ay = x + fx * w, y + fy * h
            c.create_line(ax - 15 * k * d, ay, ax + 15 * k * d, ay,
                          arrow="last", fill="#9aa5ad", width=2)
        for key in "ABCD":
            vx, vy = V[key]
            self.pushfit(vx - 0.072 * w, vy, -1)
            self.pushfit(vx + 0.072 * w, vy, 1)
            self.ballvalve(vx, vy, 0.058 * w, 0.062 * h, "valve%s" % key)

    def plate(self, xc, w, ytop, h):
        """A clear acrylic disc seen at 11 deg: rim, side wall, top face."""
        c = self.cv
        c.create_rectangle(xc - w, ytop, xc + w, ytop + h, fill="#31465a",
                           outline="")
        for sg in (-1, 1):
            c.create_line(xc + sg * w, ytop, xc + sg * w, ytop + h,
                          fill="#cfe0ee", width=2)
        c.create_arc(xc - w, ytop + h - w * ELEV, xc + w, ytop + h + w * ELEV,
                     start=180, extent=180, style="arc", outline="#cfe0ee",
                     width=2)
        self.ell(xc, w, ytop, fill="#4e6c83", outline="#dceaf5")
        c.create_arc(xc - w * .82, ytop - w * .82 * ELEV, xc + w * .82,
                     ytop + w * .82 * ELEV, start=200, extent=70,
                     style="arc", outline="#a9c8dd")

    def stud(self, x, y0, y1, bright):
        c, k = self.cv, self.k
        col = "#c3ced8" if bright else "#5d6771"
        dk = "#6d7883" if bright else "#39424b"
        w = (9 if bright else 8) * k
        c.create_line(x, y0, x, y1, fill=col, width=w)
        c.create_line(x - w * .30, y0, x - w * .30, y1, fill=dk,
                      width=max(1, int(w * .34)))
        step = max(5.0, 7 * k)
        for i in range(int((y1 - y0) / step)):
            yy = y0 + i * step
            c.create_line(x - w * .48, yy + step * .45, x + w * .48, yy,
                          fill=dk)
        for yy in (y0 + 9 * k, y1 - 9 * k):
            c.create_polygon(x - w * 1.15, yy - 8 * k, x + w * 1.15,
                             yy - 8 * k, x + w * 1.45, yy, x + w * 1.15,
                             yy + 8 * k, x - w * 1.15, yy + 8 * k,
                             x - w * 1.45, yy, fill=col, outline=dk)

    # -------------------------------------------------------------- panels
    def panels(self):
        c, k = self.cv, self.k
        c.create_text(self.OX + 18 * k, self.OY + 18 * k, anchor="w",
                      text=TR('IPhO 2026  --  이상 기체, 증기압, 열전도   [20점 | 5.0시간]', 'IPhO 2026  --  Ideal Gas, Vapor Pressure and Heat Conduction   [20 pts | 5.0 h]'),
                      fill="#4c8fd6", font=self.f_b)

        # ---- Fig. 18 / Fig. 15 card --------------------------------------
        x0, y0, x1, y1 = self.NOTE
        c.create_rectangle(x0, y0, x1, y1, fill="#101215", outline="#3a4148")
        c.create_text(x0 + 10 * k, y0 + 13 * k, anchor="w",
                      text=TR('Fig. 18 기호        Fig. 15 밸브 위치', 'Fig. 18 notation        Fig. 15 valve positions'),
                      fill="#3a4148", font=self.f_s)
        bx, by0, by1 = x0 + 36 * k, y0 + 30 * k, y1 - 16 * k
        c.create_rectangle(bx, by0, bx + 46 * k, by1, outline=ACRYL)
        c.create_rectangle(bx + 1, by0 + (by1 - by0) * .55, bx + 45 * k,
                           by1 - 1, fill="#2f8fc4", outline="")
        c.create_line(bx + 58 * k, by0, bx + 58 * k, by0 + (by1 - by0) * .55,
                      arrow="both", fill=INK)
        c.create_text(bx + 68 * k, by0 + (by1 - by0) * .27, text="H", fill=INK,
                      font=self.f_m)
        c.create_line(bx + 58 * k, by0 + (by1 - by0) * .55, bx + 58 * k, by1,
                      arrow="both", fill=INK)
        c.create_text(bx + 68 * k, by0 + (by1 - by0) * .78, text="h", fill=INK,
                      font=self.f_m)
        for i, (t, op) in enumerate(((TR('I  열림', 'I  open'), True),
                                     (TR('II  닫힘', 'II  closed'), False))):
            vx, vy = x1 - 118 * k, y0 + 50 * k + i * 52 * k
            self.valve_art(vx, vy, op)
            c.create_text(vx + 50 * k, vy, anchor="w", text=t, fill=DIM,
                          font=self.f_s)

        # ---- electronic module (Fig. 3) : the photograph itself --------
        x0, y0, x1, y1 = self.MOD
        box = self.BOX3 = self.panel('fig3', x0, y0, x1, y1)
        H = self.HOT['fig3']
        sx0, sy0 = self.hot(box, H['screen'][0], H['screen'][1])
        sx1, sy1 = self.hot(box, H['screen'][2], H['screen'][3])
        self.SCR = (sx0, sy0, sx1, sy1)

        # ---- side connector panel of the module (Fig. 5) --------------
        x0, y0, x1, y1 = self.SIDE
        self.panel('fig5', x0, y0, x1, y1)
        # the three leads run from the head of the assembly to this panel
        for i, (dx, col) in enumerate(((26, "#111417"), (46, "#111417"),
                                       (66, "#54b6e8"))):
            c.create_line(self.CX + dx * k, self.CY_COVER - 22 * k,
                          self.CX + self.W_OC_O + (30 + i * 12) * k,
                          self.YTOP + 40 * k,
                          x0 - (26 - i * 8) * k, y0 + (26 + i * 22) * k,
                          x0 + 8 * k, y0 + (40 + i * 26) * k,
                          smooth=True, fill=col, width=5)

        # ---- rear panel (Fig. 4) and pump (Fig. 8) ---------------------
        x0, y0, x1, y1 = self.REAR
        self.BOX4 = self.panel('fig4', x0, y0, x1, y1)
        x0, y0, x1, y1 = self.PUMPP
        self.BOX8 = self.panel('fig8', x0, y0, x1, y1)

        # ---- hydraulic module (Fig. 6) ---------------------------------
        x0, y0, x1, y1 = self.BOARD
        self.BOX6 = self.panel('fig6', x0, y0, x1, y1)
        H = self.HOT['fig6']
        for key in "ABCD":
            self.VALVE_XY[key] = self.hot(self.BOX6, *H[key])
        self.HOSE_PORT['A'] = self.hot(self.BOX6, *H['hoseA'])
        self.HOSE_PORT['C'] = self.hot(self.BOX6, *H['hoseC'])
        self.SYR_PORT = self.hot(self.BOX6, *H['hoseD'])
        self.HOSE_D_END = (self.SYR_PORT[0] + 22 * k,
                           self.SYR_PORT[1] - 26 * k)
        for key, (vx, vy) in self.VALVE_XY.items():
            c.create_oval(vx - 26 * k, vy - 26 * k, vx + 26 * k, vy + 26 * k,
                          outline="", fill="", tags="valve%s" % key)
        # sockets the syringe has to be pushed fully into
        for tx, ty in (self.SYR_PORT, self.HOSE_D_END):
            c.create_oval(tx - 20 * k, ty - 20 * k, tx + 20 * k, ty + 20 * k,
                          outline="#4a5760", dash=(3, 3), tags="top")
            c.create_oval(tx - 6 * k, ty - 6 * k, tx + 6 * k, ty + 6 * k,
                          fill="#05080b", outline="#8fa6b8", tags="top")

        # ---- containers ------------------------------------------------------
        names = {'pg': 'PG\n100 mL',
                 'cold': TR('찬물\n500 mL', 'cold water\n500 mL'),
                 'room': TR('상온수', 'room-temp.\nwater'),
                 'pour': TR('비커', 'pouring\njug'),
                 'jug': TR('폐수통', 'waste jug')}
        for key, (a, b_, d, e) in self.CONT.items():
            nk = 0 if key in ('pour', 'jug') else (e - b_) * 0.16
            # invisible grab area: same colour as the bench, so the whole
            # vessel can be picked up even when it is empty
            c.create_rectangle(a, b_, d, e, fill=BENCH, outline="",
                               tags=("cont_%s" % key,))
            if key in ('jug', 'pour'):
                c.create_rectangle(a, b_, d, e, outline=STEEL, width=2,
                                   tags=("top", "cont_%s" % key))
                if key == 'pour':
                    c.create_arc(d - 10 * k, b_ + 18 * k, d + 26 * k,
                                 e - 18 * k, start=270, extent=180,
                                 style="arc", outline=STEEL, width=3,
                                 tags="top")
            else:
                c.create_rectangle(a, b_ + nk, d, e, outline=STEEL, width=2,
                                   tags=("top", "cont_%s" % key))
                c.create_rectangle(a + (d - a) * .32, b_, d - (d - a) * .32,
                                   b_ + nk, outline=STEEL, width=2,
                                   tags=("top", "cont_%s" % key))
            c.create_text((a + d) / 2, b_ - 16 * k, text=names[key], fill=DIM,
                          font=self.f_s, justify="center")

        # ---- Fig. 17 card -----------------------------------------------------
        rx, ry, rx1, ry1 = self.CARD17
        c.create_rectangle(rx, ry, rx1, ry1, fill="#101215", outline="#3a4148")
        c.create_text(rx + 10 * k, ry + 13 * k, anchor="w",
                      text=TR('Fig. 17  단면', 'Fig. 17  cross-section'),
                      fill="#3a4148", font=self.f_s)
        ccx, ccy = rx + (ry1 - ry) * 0.52, (ry + ry1) / 2 + 6 * k
        rr = (ry1 - ry) * 0.36
        for f in (1.0, 0.91, 0.545, 0.455):
            c.create_oval(ccx - rr * f, ccy - rr * f, ccx + rr * f,
                          ccy + rr * f, outline=ACRYL)
        for i, t in enumerate((TR('바깥지름   74.8 +/- 0.1 mm', 'outer diameter  74.8 +/- 0.1 mm'),
                               TR('안지름     33.7 +/- 0.1 mm', 'inner diameter  33.7 +/- 0.1 mm'),
                               TR('벽 두께     3.4 +/- 0.1 mm', 'wall             3.4 +/- 0.1 mm'),
                               TR('벽 두께     3.4 +/- 0.1 mm', 'wall             3.4 +/- 0.1 mm'))):
            c.create_text(ccx + rr + 22 * k, ccy - rr * 0.7 + i * 24 * k,
                          anchor="w", text=t, fill="#9fb0bf", font=self.f_s)

        # ---- footer -----------------------------------------------------------
        fy = self.FOOT
        c.create_text(self.OX + 1906 * k, fy + 4 * k, anchor="e",
                      fill="#39424b", font=self.f_s,
                      text=TR('세션 %06d', 'session %06d') % self.lab.seed)
        c.create_text(self.OX + 18 * k, fy + 54 * k, anchor="w",
                      fill="#4d5760",
                      font=self.f_s,
                      text=TR('밸브 손잡이를 클릭하면 돌아갑니다  |  호스 A / 호스 C의 끝을 용기로 끌어다 놓고 다시 클릭해 클립 고정  |  주사기를 병으로 끌어다 피스톤을 당긴 뒤 호스 D에 연결  |  용기를 다른 용기 위로 끌면 따라집니다  |  space = 일시정지   F11 = 전체화면',
                             'click a valve handle to turn it  |  drag the end of hose A / hose C into a container, click it again to clip  |  drag a syringe to a bottle, pull the plunger, then plug it into hose D  |  drag a container onto another to pour  |  space = pause   F11 = full screen'))
        bw2, bh2 = 56 * k, 26 * k
        x = self.OX + 1660 * k
        for sp in (1, 10, 60, 300):
            c.create_rectangle(x, fy + 8 * k, x + bw2, fy + 8 * k + bh2,
                               fill="#1c232b", outline="#3a4148",
                               tags="spd%d" % sp)
            c.create_text(x + bw2 / 2, fy + 8 * k + bh2 / 2, text="x%d" % sp,
                          fill=INK, font=self.f_s, tags="spd%d" % sp)
            x += bw2 + 6 * k
        px = self.OX + 1580 * k
        c.create_rectangle(px, fy + 8 * k, px + 58 * k, fy + 8 * k + bh2,
                           fill="#1c232b", outline="#3a4148", tags="runpause")
        self.D['runtxt'] = c.create_text(px + 29 * k, fy + 8 * k + bh2 / 2,
                                         text="||", fill=INK, font=self.f_m,
                                         tags="runpause")

    def valve_art(self, vx, vy, is_open):
        c, k = self.cv, self.k
        c.create_rectangle(vx - 22 * k, vy - 9 * k, vx + 22 * k, vy + 9 * k,
                           fill="#c6ced6", outline="#8b959e")
        c.create_oval(vx - 13 * k, vy - 13 * k, vx + 13 * k, vy + 13 * k,
                      fill="#7d868f", outline="#aeb7bf")
        if is_open:
            c.create_rectangle(vx - 4 * k, vy - 34 * k, vx + 4 * k,
                               vy - 10 * k, fill="#4ad07a", outline="#2b7a4a")
        else:
            c.create_rectangle(vx + 10 * k, vy - 4 * k, vx + 34 * k,
                               vy + 4 * k, fill="#d95c4a", outline="#8a3227")

    # ============================================== dynamic items (once)
    def dyn_liquids(self):
        c, D, k = self.cv, self.D, self.k
        z = (0, 0, 0, 0)
        for sg in (-1, 1):
            for j in range(3):
                D['ocw%d_%d' % (sg, j)] = c.create_rectangle(
                    *z, outline="", fill="#1d6fa8")
        D['ocs'] = c.create_oval(*z, outline="", fill="#3a8fc8")
        D['ocm'] = c.create_oval(*z, outline="", fill="#0f161d")
        D['icw'] = c.create_rectangle(*z, outline="", fill="#1d6fa8")
        D['icr'] = c.create_oval(*z, outline="", fill="#3a8fc8")   # wall ring
        D['ics'] = c.create_oval(*z, outline="#eef6ff", fill="#3a8fc8")
        hx = self.CX + self.X_HEAT
        D['heat'] = [
            c.create_rectangle(hx - 9 * k, self.cm2y(9.0), hx + 9 * k,
                               self.YB, fill="#8b959e", outline="#c3ccd4"),
            c.create_rectangle(hx - 9 * k, self.cm2y(9.0) - 9 * k, hx + 9 * k,
                               self.cm2y(9.0), fill="#c9a227",
                               outline="#e3c964")]

    def dyn_rest(self):
        c, D, k = self.cv, self.D, self.k
        z = (0, 0, 0, 0)
        ex = self.CX - self.W_OC_O - 26 * k
        ey = self.YTOP - self.FLANGE_H - 14 * k
        self.EXY = (ex, ey)
        c.create_line(self.CX - self.FLANGE_W + 6 * k,
                      self.YTOP - self.FLANGE_H - 4 * k, ex + 16 * k,
                      ey - 26 * k, ex + 4 * k, ey - 14 * k, smooth=True,
                      fill="#15181c", width=6, tags="top")
        c.create_rectangle(ex - 15 * k, ey - 14 * k, ex + 15 * k, ey + 16 * k,
                           fill="#15181c", outline="#4a5259",
                           tags=("valveE", "top"))
        c.create_oval(ex - 9 * k, ey - 3 * k, ex + 9 * k, ey + 15 * k,
                      fill="#22282e", outline="#4a5259", tags=("valveE", "top"))
        c.create_rectangle(ex - 6 * k, ey + 16 * k, ex + 6 * k, ey + 28 * k,
                           fill="#8b959e", outline="#c3ccd4", tags="top")
        D['vE'] = c.create_line(ex, ey + 4 * k, ex, ey - 24 * k,
                                fill="#d95c4a", width=7,
                                tags=("valveE", "top"))
        c.create_text(ex - 20 * k, ey - 22 * k, anchor="e", text="E",
                      fill=INK, font=self.f_m, tags="top")
        for key, (vx, vy) in self.VALVE_XY.items():
            D['vh' + key] = c.create_rectangle(
                vx - 26 * k, vy - 8 * k, vx + 26 * k, vy + 8 * k,
                fill="#33383d", outline="#e0776a", width=3,
                tags="valve%s" % key)
            D['vt' + key] = c.create_text(vx, vy + 42 * k, text="II",
                                          fill="#d95c4a", font=self.f_m,
                                          tags="valve%s" % key)
        for key in ('A', 'C', 'D'):
            if key == 'D':
                px, py = self.SYR_PORT
            else:
                px, py = self.HOSE_PORT[key]
            D['pf' + key] = c.create_oval(px - 7 * k, py - 11 * k,
                                          px + 7 * k, py + 11 * k,
                                          fill="#2f7fbf", outline="#8fc6e8",
                                          width=2,
                                          tags=("port%s" % key, "top"))
        for key, col in (('A', "#3aa0e0"), ('C', "#e2721f")):
            D['hl' + key] = c.create_line(0, 0, 0, 0, 0, 0, smooth=True,
                                          fill=col, width=5, tags="top")
            D['he' + key] = c.create_oval(*z, fill="#c9d4de",
                                          outline="#6f7c88",
                                          tags=("hose%s" % key, "top"))
            D['hc' + key] = c.create_polygon(0, 0, 0, 0, 0, 0, 0, 0,
                                             fill="#3a4148", outline="#8fa6b8",
                                             tags=("clip%s" % key, "top"))
            D['ht' + key] = c.create_text(0, 0, text="hose %s" % key, fill=DIM,
                                          font=self.f_s, tags="top")
        for key in self.CONT:
            D['ct' + key] = c.create_rectangle(*z, outline="", fill="#1d6fa8")
        for key in ('w', 'p'):
            D['sb' + key] = c.create_rectangle(*z, fill="#0f151b",
                                               outline="#b9c6d2", width=2,
                                               tags=("syr_%s" % key, "top"))
            D['sg' + key] = [c.create_line(0, 0, 0, 0, fill="#93a3b2",
                                           tags="top") for _ in range(11)]
            D['sq' + key] = c.create_rectangle(*z, outline="", fill="#1d6fa8",
                                               tags="top")
            D['sn' + key] = c.create_polygon(0, 0, 0, 0, 0, 0, 0, 0,
                                             fill="#4f9ad0", outline="#8fc0e6",
                                             tags=("syr_%s" % key, "top"))
            D['sp' + key] = c.create_rectangle(*z, fill="#5b6772",
                                               outline="#98a5b1",
                                               tags=("plg_%s" % key, "top"))
            D['sr' + key] = c.create_line(0, 0, 0, 0, fill="#98a5b1", width=6,
                                          tags=("plg_%s" % key, "top"))
            D['sh' + key] = c.create_rectangle(*z, fill="#98a5b1",
                                               outline="#c4ced8",
                                               tags=("plg_%s" % key, "top"))
            D['sl' + key] = c.create_text(0, 0, text=self.lab.syr[key].label,
                                          fill=DIM, font=self.f_s, tags="top")
            D['sB' + key] = c.create_rectangle(
                *z, fill="#1c232b", outline="#3a4148",
                tags=("plgtoggle_%s" % key, "top"))
            D['sT' + key] = c.create_text(0, 0, text=TR('제거', 'remove'),
                                          fill=INK,
                                          font=self.f_s,
                                          tags=("plgtoggle_%s" % key, "top"))
        # ---- everything printed on the screen is dynamic: dark when off ---
        sx0, sy0, sx1, sy1 = self.SCR
        st0 = "normal" if self.lab.power else "hidden"
        c.create_rectangle(sx0, sy0, sx1, sy1, fill="#04090d", outline="")
        scr = []
        scr.append(c.create_rectangle(sx0 + 14 * k, sy0 + 22 * k,
                                      sx0 + 24 * k, sy0 + 96 * k,
                                      fill="#3a2f14", outline="#7a6a2e", state=st0))
        scr.append(c.create_rectangle(sx0 + 15 * k, sy0 + 60 * k,
                                      sx0 + 23 * k, sy0 + 95 * k,
                                      fill="#e0a712", outline="", state=st0))
        scr.append(c.create_oval(sx0 + 10 * k, sy0 + 90 * k, sx0 + 28 * k,
                                 sy0 + 108 * k, fill="#e0a712",
                                 outline="#7a6a2e", state=st0))
        band = sy1 - (sy1 - sy0) * 0.30
        scr.append(c.create_rectangle(sx0 + 6 * k, band, sx1 - 6 * k,
                                      sy1 - 6 * k, fill="#12293a", outline="", state=st0))
        cw = (sx1 - sx0)
        for i, (name, col, cc, rr) in enumerate(
                (("INT. PRESSURE", "#4ad07a", 0, 0),
                 ("ATM. PRESSURE", "#4ad07a", 1, 0),
                 ("INT. TEMPERATURE", "#e8a33d", 0, 1),
                 ("EXT. TEMPERATURE", "#e8a33d", 1, 1))):
            px = sx0 + cw * (0.10 + cc * 0.45)
            py = sy0 + 26 * k + rr * (band - sy0 - 26 * k) * 0.52
            scr.append(c.create_oval(px - 13 * k, py - 4 * k, px - 5 * k,
                                     py + 4 * k, fill=col, outline="", state=st0))
            scr.append(c.create_text(px, py, anchor="w", text=name,
                                     fill="#8fd6e8", font=self.f_s, state=st0))
            D['lcd%d' % i] = c.create_text(px, py + 28 * k, anchor="w",
                                           text="", fill="#eaf6ff",
                                           font=self.f_lcd)
            scr.append(c.create_text(px + cw * 0.235, py + 32 * k, anchor="w",
                                     text="kPa" if rr == 0 else "C",
                                     fill="#8fd6e8", font=self.f_s, state=st0))
        D['tmr'] = c.create_text(sx0 + 22 * k, (band + sy1) / 2 - 3 * k,
                                 anchor="w", text="", fill="#eaf6ff",
                                 font=self.f_lcd)
        D['ind'] = c.create_rectangle(sx1 - 44 * k, (band + sy1) / 2 - 13 * k,
                                      sx1 - 20 * k, (band + sy1) / 2 + 11 * k,
                                      fill="#1b2b33", outline="#3a5560")
        D['scr'] = scr
        fx, fy, fw, fh = self.HOT['fig4']['power']
        rcx, rcy = self.hot(self.BOX4, fx, fy)
        rr = fw * self.BOX4[2] / 1.4
        D['pw'] = c.create_oval(rcx - rr * .74, rcy - rr * .74,
                                rcx + rr * .74, rcy + rr * .74,
                                fill="#5a1d16", outline="#7a2a1e", width=2,
                                tags="power")
        fx, fy, fw, fh = self.HOT['fig8']['pump']
        pcx, pcy = self.hot(self.BOX8, fx, fy)
        pr = fw * self.BOX8[2] / 1.4
        D['pu'] = c.create_oval(pcx - pr * .74, pcy - pr * .74,
                                pcx + pr * .74, pcy + pr * .74,
                                fill="#5a1d16", outline="#7a2a1e", width=2,
                                tags="pump")
        D['st'] = c.create_text(self.OX + 18 * k, self.FOOT + 14 * k,
                                anchor="w",
                                text="", fill="#8fa2b3", font=self.f_m)
        D['ms'] = c.create_text(self.OX + 18 * k, self.FOOT + 34 * k,
                                anchor="w",
                                text="", fill="#6fa8dc", font=self.f_m)

    # ---------------------------------------------------- cached Tk ops
    def co(self, key, *a):
        if self.C.get('c' + key) != a:
            self.C['c' + key] = a
            self.cv.coords(self.D[key], *a)

    def cf(self, key, **kw):
        v = tuple(sorted(kw.items()))
        if self.C.get('f' + key) != v:
            self.C['f' + key] = v
            self.cv.itemconfigure(self.D[key], **kw)

    # ================================================== per-frame update
    def refresh(self):
        if not self.D:
            return
        L, D, c, k = self.lab, self.D, self.cv, self.k
        CX, YB = self.CX, self.YB
        self.frame += 1

        if L.h_oc > 0.001:
            y = self.cm2y(L.h_oc * 100)
            i = wi(L.T_oc + L.strat)
            for sg in (-1, 1):
                a, b = sorted((CX + sg * self.W_IC_O, CX + sg * self.W_OC_I))
                for j, sh in enumerate((_WDARK[i], _WRAMP[i], _WDARK[i])):
                    p0 = a + (b - a) * j / 3.0
                    p1 = a + (b - a) * (j + 1) / 3.0
                    self.co('ocw%d_%d' % (sg, j), p0, y, p1, YB)
                    self.cf('ocw%d_%d' % (sg, j), fill=sh, state="normal")
            self.co('ocs', CX - self.W_OC_I, y - self.W_OC_I * ELEV,
                    CX + self.W_OC_I, y + self.W_OC_I * ELEV)
            self.co('ocm', CX - self.W_IC_O, y - self.W_IC_O * ELEV,
                    CX + self.W_IC_O, y + self.W_IC_O * ELEV)
            self.cf('ocs', fill=_WTOP[i], state="normal")
            self.cf('ocm', state="normal")
        else:
            for key in ['ocs', 'ocm'] + ['ocw%d_%d' % (sg, j)
                                         for sg in (-1, 1) for j in range(3)]:
                self.cf(key, state="hidden")
        if L.h_ic > 0.001:
            y = self.cm2y(L.h_ic * 100)
            if L.ic_kind == 'pg':
                body, top = "#b3a862", "#dfd68f"
            elif L.ic_kind == 'mixed':
                body, top = "#8fa06a", "#b6c58e"
            else:
                i = wi(L.T_ic)
                body, top = _WDARK[i], _WTOP[i]
            # the meniscus: the liquid climbs the wall in a narrow ring,
            # the middle stays flat -- that flat part is what you read
            rise, width, _ = L.meniscus()
            rp = rise * 100.0 * self.PXCM          # m -> cm -> px
            wp = min(self.W_IC_I * 0.8, width * 100.0 * self.PXCM)
            yw = y - rp
            self.co('icw', CX - self.W_IC_I, yw, CX + self.W_IC_I, YB)
            self.co('icr', CX - self.W_IC_I, yw - self.W_IC_I * ELEV,
                    CX + self.W_IC_I, yw + self.W_IC_I * ELEV)
            ri = max(2.0, self.W_IC_I - wp)
            self.co('ics', CX - ri, y - ri * ELEV, CX + ri, y + ri * ELEV)
            self.cf('icw', fill=body, state="normal")
            self.cf('icr', fill=_lerp(top, "#ffffff", 0.25), state="normal")
            self.cf('ics', fill=top, state="normal")
        else:
            for key in ('icw', 'icr', 'ics'):
                self.cf(key, state="hidden")

        hc = "#e0603f" if L.heater else "#8b959e"
        if self.C.get('hc') != hc:
            self.C['hc'] = hc
            c.itemconfigure(D['heat'][0], fill=hc)

        ex, ey = self.EXY
        if L.valve['E']:
            self.co('vE', ex, ey + 1, ex + 24 * k, ey + 1)
            self.cf('vE', fill="#4ad07a")
        else:
            self.co('vE', ex, ey + 1, ex, ey - 24 * k)
            self.cf('vE', fill="#d95c4a")
        for key, (vx, vy) in self.VALVE_XY.items():
            if L.valve[key]:
                self.co('vh' + key, vx - 8 * k, vy - 26 * k, vx + 8 * k,
                        vy + 26 * k)
                self.cf('vh' + key, fill="#33383d", outline="#6de08f")
                self.co('vt' + key, vx, vy + 42 * k)
                self.cf('vt' + key, text="I", fill="#4ad07a")
            else:
                self.co('vh' + key, vx - 26 * k, vy - 8 * k, vx + 26 * k,
                        vy + 8 * k)
                self.cf('vh' + key, fill="#33383d", outline="#e0776a")
                self.co('vt' + key, vx, vy + 32 * k)
                self.cf('vt' + key, text="II", fill="#d95c4a")

        for key in ('A', 'C', 'D'):
            conn = L.hconn[key]
            self.cf('pf' + key, fill="#2f7fbf" if conn else "#5c6a74",
                    outline="#8fc6e8" if conn else "#8a949c")
            if key == 'D':
                continue
            px, py = self.HOSE_PORT[key]
            if not conn:
                px, py = px - 26 * k, py + 34 * k       # hose lying loose
            hx, hy = self.hose[key]
            sag = min(max(py, hy) + 70 * k, self.OY + 1000 * k)
            self.co('hl' + key, px, py, (px + hx) / 2, sag, hx, hy)
            self.co('he' + key, hx - 8 * k, hy - 8 * k, hx + 8 * k,
                    hy + 8 * k)
            self.co('ht' + key, hx, hy - 16 * k)
            if L.clip[key]:
                self.co('hc' + key, hx - 13 * k, hy - 3 * k, hx + 13 * k,
                        hy - 3 * k, hx + 10 * k, hy + 14 * k, hx - 10 * k,
                        hy + 14 * k)
                self.cf('hc' + key, state="normal")
            else:
                self.cf('hc' + key, state="hidden")

        for key, (a, b_, d, e) in self.CONT.items():
            ct = L.containers[key]
            f = ct.vol / ct.cap
            if f < 0.005:
                self.cf('ct' + key, state="hidden")
                continue
            nk = 0 if key in ('pour', 'jug') else (e - b_) * 0.16
            top = b_ + nk + (e - b_ - nk) * (1 - min(1.0, f))
            ox, oy = self.coff.get(key, (0.0, 0.0))
            self.co('ct' + key, a + 2 + ox, top + oy, d - 2 + ox, e - 2 + oy)
            col = ("#c8bd72" if ct.kind == 'pg' else
                   "#5d6b78" if ct.kind == 'waste' else
                   "#9fb07a" if ct.kind == 'mixed' else _WRAMP[wi(ct.T)])
            self.cf('ct' + key, fill=col, state="normal")

        SW, SH = self.SW, self.SH
        for key in ('w', 'p'):
            s = L.syr[key]
            sig = (round(s.x, 1), round(s.y, 1), round(s.vol, 1),
                   round(s.plunger, 1), s.kind, s.has_plunger, int(s.T))
            if self.C.get('syr' + key) == sig:
                continue
            self.C['syr' + key] = sig
            x, yv = s.x, s.y
            self.co('sb' + key, x, yv, x + SW, yv + SH)
            if self.C.get('sgy' + key) != (x, yv):
                self.C['sgy' + key] = (x, yv)
                for i, it in enumerate(D['sg' + key]):
                    yy = yv + SH - SH * i / 10.0
                    c.coords(it, x + SW, yy,
                             x + SW - (11 if i % 5 == 0 else 7) * k, yy)
            if s.vol > 0.2:
                col = ("#c8bd72" if s.kind == 'pg' else
                       "#9fb07a" if s.kind == 'mixed' else _WRAMP[wi(s.T)])
                top = yv + SH - SH * min(1.0, s.vol / s.cap)
                self.co('sq' + key, x + 2, top, x + SW - 2, yv + SH - 2)
                self.cf('sq' + key, fill=col, state="normal")
            else:
                self.cf('sq' + key, state="hidden")
            self.co('sn' + key, x + SW / 2 - 7 * k, yv + SH, x + SW / 2 +
                    7 * k, yv + SH, x + SW / 2 + 3 * k, yv + SH + 20 * k,
                    x + SW / 2 - 3 * k, yv + SH + 20 * k)
            if s.has_plunger:
                py = yv + SH - SH * min(1.0, s.plunger / s.cap)
                self.co('sp' + key, x + 2, py - 9 * k, x + SW - 2, py)
                self.co('sr' + key, x + SW / 2, py - 9 * k, x + SW / 2,
                        yv - 50 * k)
                self.co('sh' + key, x - 11 * k, yv - 62 * k, x + SW + 11 * k,
                        yv - 50 * k)
                for t in ('sp', 'sr', 'sh'):
                    self.cf(t + key, state="normal")
            else:
                for t in ('sp', 'sr', 'sh'):
                    self.cf(t + key, state="hidden")
            self.co('sl' + key, x + SW / 2, yv - 72 * k)
            self.co('sB' + key, x - 12 * k, yv + SH + 28 * k, x + SW + 12 * k,
                    yv + SH + 50 * k)
            self.co('sT' + key, x + SW / 2, yv + SH + 39 * k)
            self.cf('sT' + key, text=TR('장착', 'refit')
                    if not s.has_plunger else TR('제거', 'remove'))

        if self.frame % 6 == 1:
            st = "normal" if L.power else "hidden"
            if self.C.get('scr') != st:
                self.C['scr'] = st
                for it in D['scr']:
                    c.itemconfigure(it, state=st)
                c.itemconfigure(D['ind'], state=st)
            if L.power:
                for i, v in enumerate((L.r_pint(), L.r_patm(), L.r_tint(),
                                       L.r_text())):
                    self.cf('lcd%d' % i, text="%.1f" % v)
                mn, s2 = divmod(L.timer, 60)
                self.cf('tmr', text="TIMER: %02d:%04.1f" % (mn, s2))
            else:
                for i in range(4):
                    self.cf('lcd%d' % i, text="")
                self.cf('tmr', text="")
            self.cf('pw', fill="#c9261b" if L.power else "#5a1d16")
            self.cf('pu', fill="#c9261b" if L.pump else "#5a1d16")
            self.cf('st', text=TR('경과 %02d:%02d:%02d   배속 x%d   %s', 'elapsed %02d:%02d:%02d   speed x%d   %s') % (
                L.t // 3600, (L.t % 3600) // 60, L.t % 60, int(self.speed),
                "" if self.running else TR('[일시정지]', '[paused]')))
            fresh = L.msg and (L.t - L.msg_t) < 12 * max(1, self.speed / 4)
            self.cf('ms', text=L.msg if fresh else "",
                    fill="#e0a04a" if L.msg.startswith("!") else "#6fa8dc")
        if not L.power:
            ic = "#1b2b33"
        elif L.heater:
            ic = "#d94a34" if int(L.t * 2) % 2 else "#4ad07a"
        elif L.heater_hot:
            ic = "#d94a34"
        else:
            ic = "#1b2b33"
        self.cf('ind', fill=ic)

    # ====================================================== interaction
    @property
    def hose(self):
        if not hasattr(self, '_hose'):
            self._hose = {'A': [0.0, 0.0], 'C': [0.0, 0.0]}
        return self._hose

    def hose_home(self):
        x0, y0, x1, y1 = self.BOARD
        self.hose['A'] = [x0 - 40 * self.k, y1 + 40 * self.k]
        self.hose['C'] = [x0 - 40 * self.k, y1 + 90 * self.k]

    def hit(self, x, y):
        for it in reversed(self.cv.find_overlapping(x - 3, y - 3,
                                                    x + 3, y + 3)):
            for t in self.cv.gettags(it):
                if t not in ("current", "top", "scale"):
                    return t
        return None

    def on_press(self, e):
        L = self.lab
        t = self.hit(e.x, e.y)
        if t is None:
            return
        if t.startswith("btn"):
            L.press_button(int(t[3]))
        elif t == "power":
            L.press_power()
        elif t == "pump":
            L.press_pump()
        elif t.startswith("port"):
            L.toggle_hose(t[4])
        elif t.startswith("clip"):
            L.toggle_clip(t[4])
        elif t.startswith("valve"):
            L.toggle_valve(t[5])
        elif t.startswith("spd"):
            self.speed = float(t[3:])
        elif t == "runpause":
            self.toggle_run()
        elif t.startswith("plgtoggle_"):
            L.remove_plunger(t[10])
        elif t.startswith("plg_"):
            self.drag = ("plunger", t[4], e.y)
        elif t.startswith("syr_"):
            key = t[4:]
            self.drag = ("syringe", key,
                         (e.x - L.syr[key].x, e.y - L.syr[key].y))
        elif t.startswith("hose"):
            self.drag = ("hose", t[4], (e.x, e.y))
        elif t.startswith("cont_"):
            key = t[5:]
            self.coff[key] = (0.0, 0.0)
            self.drag = ("cont", key, (e.x, e.y))

    def on_wheel(self, e, direction=None):
        """Roll the wheel over a syringe to move its plunger, 1 mL a notch
        (hold Shift for 5 mL)."""
        t = self.hit(e.x, e.y)
        if not t:
            return
        if direction is None:
            direction = 1 if getattr(e, "delta", 0) > 0 else -1
        shift = bool(getattr(e, "state", 0) & 0x0001)
        if t.startswith("syr_") or t.startswith("plg"):
            key = t.split("_")[1]
            self.lab.syringe_pull(key, direction * (5.0 if shift else 1.0))
        elif t.startswith("valve"):
            v = t[5]
            if self.lab.valve[v] != (direction > 0):
                self.lab.toggle_valve(v)
        elif t.startswith("spd") or t == "runpause":
            sp = [1.0, 10.0, 60.0, 300.0]
            i = sp.index(self.speed) if self.speed in sp else 0
            self.speed = sp[max(0, min(len(sp) - 1, i + direction))]
        elif t.startswith("cont_"):
            self.lab.pour(t[5:], 'jug' if direction < 0 else t[5:], 40.0) \
                if direction < 0 else None
        self.refresh()

    def on_move(self, e):
        if not self.drag:
            return
        kind, key, ref = self.drag
        if kind == "hose":
            self.hose[key][0], self.hose[key][1] = e.x, e.y
        elif kind == "syringe":
            s = self.lab.syr[key]
            s.x, s.y = e.x - ref[0], e.y - ref[1]
        elif kind == "plunger":
            d = (ref - e.y) * (100.0 / self.SH)
            if abs(d) >= 0.5:
                self.lab.syringe_pull(key, d)
                self.drag = (kind, key, e.y)
        elif kind == "cont":
            ox, oy = self.coff.get(key, (0.0, 0.0))
            dx, dy = e.x - ref[0], e.y - ref[1]
            self.cv.move("cont_%s" % key, dx - ox, dy - oy)
            self.coff[key] = (dx, dy)
        self.refresh()

    def on_release(self, e):
        if not self.drag:
            return
        kind, key, ref = self.drag
        self.drag = None
        if kind == "syringe":
            self.snap(key)
        elif kind == "hose":
            hx, hy = self.hose[key]
            if ref and abs(e.x - ref[0]) < 5 and abs(e.y - ref[1]) < 5:
                inside = (self.lab.hoseA_in if key == 'A'
                          else self.lab.hoseC_in)
                if inside:
                    self.lab.toggle_clip(key)
                else:
                    self.lab.say(TR('! 호스를 먼저 용기에 넣으세요.', '! Put the hose in a container first.'))
                return
            found = None
            for ck, (a, b_, d, f) in self.CONT.items():
                if a - 6 <= hx <= d + 6 and b_ - 6 <= hy <= f + 6:
                    found = ck
            if key == 'A':
                self.lab.hoseA_in = found
            else:
                self.lab.hoseC_in = found
            self.lab.clip[key] = False
            self.lab.say(TR('호스 %s -> %s%s', 'Hose %s -> %s%s') % (
                key, self.lab.containers[found].label if found else TR('실험대', 'bench'),
                TR('  (호스 끝을 다시 클릭하면 클립으로 고정)', '  (click the hose end again to clip it)')
                if found else ""))
        elif kind == "cont":
            dx, dy = self.coff.get(key, (0.0, 0.0))
            tgt = None
            for ck, (a, b_, d, f) in self.CONT.items():
                if ck != key and a <= e.x <= d and b_ <= e.y <= f:
                    tgt = ck
            self.cv.move("cont_%s" % key, -dx, -dy)     # put it back down
            self.coff[key] = (0.0, 0.0)
            self.refresh()
            if tgt:
                self.lab.pour(key, tgt)

    def snap(self, key):
        L = self.lab
        s = L.syr[key]
        k = self.k
        nx, ny = s.x + self.SW / 2, s.y + self.SH + 20 * k
        hx, hy = self.HOSE_D_END
        if math.hypot(nx - hx, ny - hy) < 20 * k:
            s.attached = 'Dh'
            s.placed = 'D'
            s.x, s.y = hx - self.SW / 2, hy - self.SH - 20 * k
            L.say(TR('주사기를 호스 D에 직접 연결했습니다 (밸브 D 우회)', 'Syringe plugged straight into hose D (valve D bypassed)'))
            return
        d_port = math.hypot(nx - self.SYR_PORT[0], ny - self.SYR_PORT[1])
        d_hose = math.hypot(nx - hx, ny - hy)
        if d_port < 20 * k:
            s.attached = 'D'
            s.placed = 'D'
            s.x = self.SYR_PORT[0] - self.SW / 2
            s.y = self.SYR_PORT[1] - self.SH - 20 * self.k
            L.say(TR('주사기를 호스 D에 연결했습니다', 'Syringe connected to hose D'))
            return
        s.placed = None
        if min(d_port, d_hose) < 70 * k:
            L.say(TR('! 주사기가 포트에 완전히 꽂히지 않았습니다 - 노즐을 구멍에 맞추세요.', '! The syringe is not fully home - line the nozzle up with the socket.'))
            s.attached = None
            return
        for ck, (a, b_, d, ee) in self.CONT.items():
            if a - 12 <= nx <= d + 12 and b_ - 12 <= ny <= ee + 12:
                s.attached = ck
                L.say(TR('%s 노즐을 %s에 담갔습니다', '%s nozzle dipped in the %s') % (s.label,
                                                  L.containers[ck].label))
                return
        s.attached = None

    def toggle_run(self):
        self.running = not self.running
        if 'runtxt' in self.D:
            self.cv.itemconfigure(self.D['runtxt'],
                                  text="||" if self.running else ">")

    # ============================================================== loop
    def tick(self):
        now = time.time()
        real = now - self.last
        self.last = now
        if real > 0.25:
            real = 0.25
        if self.running:
            self.acc += real * self.speed
            step = self.lab.step
            budget = time.time() + 0.020
            while self.acc > 0.0:
                dt = 1.0 if self.acc > 1.0 else self.acc
                step(dt)
                self.acc -= dt
                if time.time() > budget:
                    self.acc = 0.0
                    break
        self.refresh()
        self.root.after(33, self.tick)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    Bench().run()
