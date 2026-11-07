# APhO 2023 T1 — ISS Orbital Decay Dynamics: official answers and marking scheme

**Task total: 10.0 points** (A 2.0 + B 3.0 + C 1.0 + D 1.0 + E 2.0 + F 1.0).

Sources: official marking scheme "Theoretical Problem 1: ISS Orbital Decay Dynamics — Q1 - Marking scheme" (`APhO_2023_M1.pdf`) for the step points; official solution "ISS Orbital Decay Dynamics (Gurjav Ganbold)" (`APhO_2023_S1.pdf`) for the answers and tables. Step descriptions are copied from the scheme (spelling kept). Equation numbers (n) refer to the official solution. Notation: $z_h \doteq h/R_E$, $h_0 \doteq RT/(\mu g_0)$.

---

## A.1 [0.5 pt] — general barometric formula

**Official answer:**
$$dp_h \doteq p_{h+dh}-p_h = -g_h\,(M/V)\,dh,\qquad \frac{dp_h}{p_h} = -\frac{g_h\mu}{RT_h}\,dh,\qquad p_h = p_0\exp\!\left(-\frac{\mu}{R}\int_0^h dh\,\frac{g_h}{T_h}\right),$$
with $p_0$ the air pressure at $h=0$.

| Step | Points |
|---|---|
| Perturbation of air pressure correct | 0.1 |
| Differential formula is correct | 0.1 |
| Integral formula is correct (final answer) | 0.3 |

## A.2 [0.3 pt] — standard barometric formula, $h_0$

**Official answer:** $p_h^{sta} = p_0\exp\left(-\dfrac{h}{h_0}\right)$, $h_0 \doteq \dfrac{RT}{\mu g_0} = \dfrac{8.31\ \mathrm{J\,K^{-1}mol^{-1}}\cdot 425\ \mathrm K}{0.029\ \mathrm{kg\,mol^{-1}}\cdot 9.81\ \mathrm{m\,s^{-2}}} \approx 12400\ \mathrm m$.

| Step | Points |
|---|---|
| correct standard barometric formula | 0.1 |
| correct calculation of $h_0$ | 0.2 |

## A.3 [0.6 pt] — improved barometric formula

**Official answer:** with $g_h \simeq g_0(1-2z_h)$ and $\int_0^h dh\,g_h \simeq g_0 h(1-z_h)$,
$$p_h^{imp} = p_0\exp\left(-\frac{h(1-z_h)}{h_0}\right).$$

| Step | Points |
|---|---|
| Correct dependence of $g_h$ | 0.1 |
| correct integration | 0.2 |
| correct improved barometric formula | 0.3 |

## A.4 [0.4 pt] — ratio

**Official answer:**
$$\frac{p_h^{imp}}{p_h^{sta}} = \frac{\exp\left(-\frac{h(1-z_h)}{h_0}\right)}{\exp\left(-\frac{h}{h_0}\right)} = e^{\frac{h^2}{h_0R_E}} \approx 7.54\quad\text{for } h = 4.0\times10^5\ \mathrm m.$$
(The gas density rises by almost eight times when the weakening of gravity is taken into account.)

| Step | Points |
|---|---|
| correct analytic formula | 0.2 |
| correct numerical values | 0.2 |

## A.5 [0.2 pt] — density and concentration

**Official answer:**
$$\rho_h \doteq \frac{M}{V} = \rho_0\exp(-h(1-z_h)/h_0),\qquad n_h = N_A\frac{\rho_0}{\mu}\exp(-h(1-z_h)/h_0).$$

| Step | Points |
|---|---|
| Correct air density | 0.1 |
| Correct air concentration | 0.1 |

---

## B.1 [0.5 pt] — orbital velocity and period

**Official answer:** $g_h = \dfrac{v_h^2}{R_E(1+z_h)}$, $g_h \doteq \dfrac{g_0}{(1+z_h)^2}$, hence
$$v_h = \sqrt{\frac{g_0R_E}{1+z_h}},\qquad \tau_h \doteq 2\pi\frac{R_E+h}{v_h} = 2\pi\sqrt{\frac{R_E}{g_0}}\,(1+z_h)^{3/2}.$$

| Step | Points |
|---|---|
| Gravitation $g_h$ | 0.1 |
| Satellite velocity $v_h$ | 0.1 |
| Correct revolution period | 0.3 |

## B.2 [0.5 pt] — total energy

**Official answer:**
$$E_S = \frac{M_S v_h^2}{2} - M_S g_h R_E(1+z_h) = -\frac{M_S g_0 R_E}{2(1+z_h)}.$$

| Step | Points |
|---|---|
| Kinetic and potential energy | 0.2 |
| Total energy | 0.3 |

## B.3 [1.0 pt] — energy balance

**Official answer:** work of the drag $dA_{drag} = -F_{drag}\,v_h\,dt$; change of orbital energy $dE_S = +\dfrac{M_S g_0}{2(1+z_h)^2}\,dh$; $dE_S + dA_{drag} = 0$ gives
$$\frac{M_S g_0}{2(1+z_h)^2}\,dh = F_{drag}\cdot v_h\cdot dt.$$

| Step | Points |
|---|---|
| Negative work by air drag force | 0.3 |
| Perturbation of total energy | 0.2 |
| Correct conservation formula | 0.5 |

## B.4 [0.5 pt] — descent speed

**Official answer:**
$$u_h \doteq \frac{dh}{dt} = \frac{2F_{drag}}{M_S g_0}\,v_h(1+z_h)^2 = \frac{2F_{drag}}{M_S}\sqrt{\frac{R_E}{g_0}}\,(1+z_h)^{3/2}.$$

| Step | Points |
|---|---|
| Formula of the speed as $dh/dt$ | 0.1 |
| Correct formula for descent speed | 0.4 |

## B.5 [0.5 pt] — descent per revolution and total fall time

**Official answer:**
$$H_h \doteq u_h\tau_h = \frac{4\pi R_E}{M_S g_0}F_{drag}(h)\cdot(1+z_h)^3,\qquad T_h \doteq \int_0^{T_h}dt = \frac{M_S}{2}\sqrt{\frac{g_0}{R_E}}\int_0^h dh\,\frac{1}{F_{drag}(h)\cdot(1+z_h)^{3/2}}.$$

| Step | Points |
|---|---|
| Descent rate per a revolution | 0.1 |
| Total falling time written as an integral | 0.4 |

---

## C.1 [0.5 pt] — air drag

**Official answer:**
$$F_{air} = n_h m_{air}v_h^2 S = \frac{N_{air}m_{air}}{V}v_h^2 S = \rho_h v_h^2 S,$$
$$u_h^{air} = \frac{2\rho_0 S\sqrt{g_0R_E^3}}{M_S}(1+z_h)^{1/2}\exp(-h(1-z_h)/h_0),\qquad H_h^{air} \doteq u_h^{air}\tau_h = \frac{4\pi S R_E^2}{M_S}\rho_0(1+z_h)^2\exp(-h(1-z_h)/h_0).$$

| Step | Points |
|---|---|
| Air drag force | 0.3 |
| Air drag descending velocity | 0.1 |
| Air drag descent rate per a revolution | 0.1 |

## C.2 [0.5 pt] — fall time under air drag

**Official answer:**
$$T_h^{air} \simeq \frac{M_S}{2\rho_0 S\sqrt{g_0R_E^3}}\int_0^h dh\left(1-\frac{h}{2R_E}\right)e^{+h/h_0} \approx \frac{M_S h_0}{2\rho_0 S\sqrt{g_0R_E^3}}\left(1-\frac{h}{2R_E}\right)e^{+h/h_0},$$
using $h_0 \ll h \ll R_E$.

| Step | Points |
|---|---|
| Correct integral formula for the air descent rate | 0.1 |
| Use of approximations taking into account $h_0 \ll h \ll R_E$ | 0.1 |
| Correct total falling time in final integral form | 0.3 |

---

## D.1 [0.3 pt] — ion drag force

**Official answer:** average ion concentration taken as half the maximum (ionization negligible at night):
$$F_{ion} = \frac12\rho_{ion}\cdot S\cdot v_h^2,\qquad \rho_{ion} = \frac{\mu_{ion}}{N_A}\cdot n_{ion}.$$

| Step | Points |
|---|---|
| Drag force by oxygen ions | 0.2 |
| Density of ionized oxygen molecules | 0.1 |

## D.2 [0.7 pt] — ion descent speed and descent per revolution

**Official answer:**
$$u_h^{ion} = \rho_{ion}\cdot\frac{S\sqrt{g_0R_E^3}}{M_S}(1+z_h)^{1/2},\qquad H_h^{ion} \doteq u_h^{ion}\tau_h = \rho_{ion}\frac{2\pi S R_E^2}{M_S}\cdot(1+z_h)^2.$$

| Step | Points |
|---|---|
| Descent velocity due to atomic oxygen | 0.3 |
| Descent rate $H_h^{ion}$ | 0.4 |

---

## E.1 [0.6 pt] — induced current

**Official answer:** $dN = n_{ion}\cdot v_h\cdot S\cdot dt$, so
$$I_{ind} \approx e\frac{dN}{dt} = e\cdot S\cdot n_{ion}\cdot\sqrt{\frac{g_0R_E}{1+z_h}}.$$

| Step | Points |
|---|---|
| Number of electrons collected by the IS for time dt | 0.3 |
| Magnitude of the inducted electric current | 0.3 |

## E.2 [0.6 pt] — Ampere braking force

**Official answer:** the force is proportional to $[\vec v_h\times\vec B] = v_hB|\sin\phi|$. Averaging over a revolution (from the "north" point $\phi=\pi/2-\theta$ to the "south" point $\phi=\pi/2+\theta$):
$$\langle|\sin\phi|\rangle = \frac{1}{2\theta}\int_{\pi/2-\theta}^{\pi/2+\theta}d\phi\,|\sin\phi| = 0.93 \approx 1,$$
or with four equidistant sample points $\{\sin(\pi/2-\theta)+\sin(\pi/2)+\sin(\pi/2+\theta)+\sin(\pi/2)\}/4 = 0.89 \approx 1$; use $\langle|\sin\phi|\rangle \approx 1$. With $L\sim S^{1/2}$:
$$F_{ind} = B\cdot I_{ind}\cdot\langle|\sin\phi|\rangle\cdot L \approx B\cdot I_{ind}\cdot\sqrt S = e\cdot B\cdot S^{3/2}\cdot n_{ion}\cdot\sqrt{\frac{g_0R_E}{1+z_h}}.$$

| Step | Points |
|---|---|
| Averaged sine of the angle between magnetic field and ISS velocity | 0.2 |
| Formula of Ampere's force | 0.2 |
| Correct final answer | 0.2 |

## E.3 [0.8 pt] — magnetic descent speed and descent per revolution

**Official answer:**
$$u_h^{ind} \approx 2n_{ion}\frac{eBS^{3/2}R_E}{M_S}\cdot(1+z_h),\qquad H_h^{ind} \doteq u_h^{ind}\tau_h = \frac{4\pi\,e\,B\,(S\,R_E)^{3/2}}{M_S\sqrt{g_0}}\cdot(1+z_h)^{5/2}.$$
*(Grader note, not part of the official text: eq. (35) as printed omits the factor $n_{ion}$, which follows from $u_h^{ind}\tau_h$; i.e. $H_h^{ind} = n_{ion}\,\frac{4\pi eB(SR_E)^{3/2}}{M_S\sqrt{g_0}}(1+z_h)^{5/2}$. The official Table 2 values for $H_h^{ind}$ include $n_{ion} = 10^{13}\,m^{-3}$.)*

| Step | Points |
|---|---|
| Descent velocity due to Earth's magnetic field | 0.3 |
| Descent rate $H_h^{ind}$ | 0.5 |

---

## F.1 [0.4 pt] — Table 1

**Official answer** (official solution, Table 1: "Various deorbit velocities on the height h above the Earth surface, compared to the ISS-NASA data estimated for $n_{ion} = 10^{13}\,m^{-3}$. For $n_{ion} = 10^{12}\,m^{-3}$ the results for $u_{ion}$ and $u_{ind}$ will decrease in 10 times."):

| $h$ [km] | $T_h^{air}$ [day] | $u_{air}$ [m/day] | $u_{ion}$ [m/day] | $u_{ind}$ [m/day] | $\sum$ [m/day] | $w_{ISS}$ [m/day] (NASA data, for comparison; not on the answer sheet) |
|---|---|---|---|---|---|---|
| 350 | 316 | 184 | 14 | 28 | 226 | ~170 [in 2008] |
| 375 | 2360 | 30.9 | 14 | 29 | 73 | – |
| 400 | 17700 | 5.3 | 14 | 29 | 47 | ≤ 100 [in 2021] |
| 410 | 39500 | 2.6 | 14 | 29 | 45 | ≤ 70 [in 2022] |

| Step | Points |
|---|---|
| 0.02 each filled box (20 boxes) | 0.4 |

## F.2 [0.4 pt] — Table 2

**Official answer** (official solution, Table 2: "The descent rates for a revolution of the ISS around the Earth for $n_{ion} = 10^{13}\,m^{-3}$. For $n_{ion} = 10^{12}\,m^{-3}$ the results for $H_h^{ion}$ and $H_h^{ind}$ will decrease in 10 times."):

| $h$ [km] | $H_h^{air}$ [m] | $H_h^{ion}$ [m] | $H_h^{ind}$ [m] |
|---|---|---|---|
| 350 | 11.7 | 0.9 | 1.8 |
| 375 | 2.0 | 0.9 | 1.8 |
| 400 | 0.3 | 0.9 | 1.8 |
| 410 | 0.2 | 0.9 | 1.8 |

| Step | Points |
|---|---|
| Value $H_h^{air}$ at h=350km | 0.1 |
| Value $H_h^{air}$ at h=3750km *(sic; i.e. 375 km)* | 0.1 |
| Value $H_h^{air}$ at h=400km | 0.1 |
| Value $H_h^{air}$ at h=410km | 0.1 |

## F.3 [0.2 pt] — ranking

**Official answer:** for the ISS above 380 km the most significant factors of orbital decay are, in order: 1) the Ampere force arising from the motion of the conductive apparatus in the Earth's magnetic field; 2) collisions of the station with ionized atoms of oxygen; 3) the atmospheric drag caused by frequent collisions of neutral $O_2$ molecules.

| Step | Points |
|---|---|
| If answered: 1) Ampere 2) Oxygen ions 3) Air drag | 0.2 |

---

### Grader notes (not part of the official scheme)

- The marking scheme gives step points only; it lists no tolerance ranges for numerical values. The official tables are approximate: recomputing them from the official formulas with $T = 425$ K, $n_{ion} = 10^{13}\,m^{-3}$ and $\mu_{ion} = 0.032$ kg/mol gives values within about 10 % of the tabulated ones, apart from the entries rounded to one significant digit (e.g. $T_h^{air}$ ≈ 339, 2530, 18900, 42400 days; $u_{air}$ ≈ 172, 28.9, 4.9, 2.4 m/day; $u_{ion}$ ≈ 13 m/day; $u_{ind}$ ≈ 26 m/day; $H_h^{air}$ ≈ 10.9, 1.85, 0.32, 0.16 m).
- The statement does not give the molar mass used for the oxygen ions; the official numbers correspond to $0.032$ kg/mol (the solution's constants list gives $\mu = 0.032$ kg/mol "for $O_2$"). With $0.016$ kg/mol (atomic O) $u_{ion}$ and $H_h^{ion}$ are halved.
- The statement (Part D) quotes $n_{ion} \sim 10^{12}\,m^{-3}$, but the answer-sheet tables and the official tables use $n_{ion} = 10^{13}\,m^{-3}$; the official solution states that for $10^{12}$ the ion and magnetic columns decrease tenfold.
