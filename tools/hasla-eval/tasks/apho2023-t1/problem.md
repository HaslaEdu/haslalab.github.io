# APhO 2023 — Theoretical Problem 1: ISS Orbital Decay Dynamics [10.0 points]

*Text-only version of the official English statement (23rd APhO, Mongolia 2023, "English (Official)"). Figures are described in words in "Figure description" blocks; everything else follows the official wording (including its spelling). Tables 1 and 2 referred to in F.1 and F.2 are printed only on the official Answer Sheet; the English answer sheet could not be obtained, so their layout is reproduced here from the official Korean answer sheet (translated).*

## Introduction

> **Figure 1 description.** "The International Space Station orbiting above the Earth." A photograph of the ISS (truss with several pairs of large rectangular solar-panel wings) above the Earth's limb. Illustrative only; it contains no data.

The ISS is currently maintained in a nearly circular orbit with a minimum mean altitude of $370\,km$ and a maximum of $460\,km$, in the center of the thermosphere, at an inclination of $\theta = 51.6^\circ$ (degrees) to Earth's equator. The trajectory of the spacecraft is similar to a spiral with a slowly changing distance from the station to the Earth's surface, and during one cycle of revolution the change in altitude is inconsiderable.

The ISS mass is $M_S = 4.5\times10^{5}\,kg$ and overall length is $L_S = 109\,m$. Huge solar panels with a width of $W_S = 73\,m$ provide the ISS with electrical energy [NASA Official Report (2023].

Including all batteries and other parts, the effective cross area (section) of the station is approximately $S \approx 2.5\times10^{3}\ \mathrm{m}^2$ [European Space Agency, SDC6-23].

The ISS orbital decay is caused by one or more mechanisms which absorb energy from the orbital motion, the essential ones being:

- atmospheric drag at orbital altitude is caused by frequent collisions of gas molecules with the satellite,
- the Ampere force arising from the motion of the conductive apparatus in the Earth's magnetic field,
- the interaction with the atomic oxygen ions.

"... In May 2008, the altitude was 350 kilometers, the ISS lost $4.5\,km$ and was re-boosted by the Progess-60 supply ship by $5.5\,km$. Again, the ISS continued to lose altitude by $5.5\,km$ ..." [https://mod.jsc.nasa.gov]

> **Figure 2 description.** "The altitude of ISS ($km$) over the years." Line plot, horizontal axis years 1998–2019 (ticks every 2 years, 1998 … 2018), vertical axis altitude 300–440 km (gridlines every 20 km). The curve is a noisy band a few km wide. It starts near 400 km in 1998–1999, falls to about 330–350 km around 2000 (lowest spike ≈ 325 km), returns to about 380–400 km in 2001–2003, then declines slowly to a minimum of about 320–340 km around 2007–2008, stays around 340–360 km from 2008 to mid-2011, jumps up in 2011–2012 to about 390–430 km, stays around 410–420 km in 2012–2015, and around 400–410 km from 2015 to 2019. Context only.

> **Figure 3 description.** "The ISS mean height ($km$) in 2022-2023." Line plot titled "ISS - mean height in km", horizontal axis months May 2022 to May 2023, vertical axis 415–420 km (gridlines every 0.5 km). The curve is a sawtooth: the height decreases gradually and almost linearly by roughly 1–2.5 km over 2–6 weeks, then jumps up abruptly (re-boosts) by a similar amount. Over the whole year the height stays between about 415.4 km and 419.7 km (highest values in February–March 2023). Context only.

". . . The ISS loses up to $330\,ft$ ( $100\,m$) of altitude each day . . . " [NASA Control Data (2021)]. In 2023 the ISS flies at altitudes of 410 km, with an orbital decay about $70\,m$ every day ( $\sim 2\,km$ per month), and during magnetic storms the daily descent reaches $300\,m$. The ISS accomplishes the de-orbit maneuvers by using the propulsion capabilities of the ISS and its visiting vehicles [International Space Station Transition Report (2022)].

> **Figure 4 description.** "ISS model with the cross sections from different aspect angles ($dm^2$). The CROC provides $2481\,m^2$ cross section." Scatter plot of coloured dots: horizontal axis "Azimuth [deg]" from $-180$ to $180$, vertical axis "Elevation [deg]" from $-90$ to $90$; colour bar from 50000 $dm^2$ (dark blue) to 450000 $dm^2$ (dark red), i.e. from $500\,m^2$ to $4500\,m^2$. The cross section depends mainly on elevation and is roughly symmetric about elevation 0: near elevation $0^\circ$ (edge-on views) the dots are blue (≈ 50000–150000 $dm^2$); at elevations $\pm 20^\circ$ to $\pm 30^\circ$ cyan/green (≈ 200000–300000 $dm^2$); at $\pm 40^\circ$ to $\pm 50^\circ$ yellow/orange (≈ 300000–380000 $dm^2$); at $\pm 60^\circ$ to $\pm 80^\circ$ red (≈ 400000–450000 $dm^2$). Context only.

## Denotations and Physical constants

| Quantity | Symbol | Value |
|---|---|---|
| Universal gas constant | $R$ | $8.31\ J\cdot K^{-1}\cdot mol^{-1}$ |
| Avogadro's number | $N_A$ | $6.022\cdot10^{23}\ mol^{-1}$ |
| The molar mass of gas (for air) | $\mu$ | $0.029\ kg\cdot mol^{-1}$ |
| Mass of the Earth | $M_E$ | $5.97\cdot10^{24}\ kg$ |
| Radius of the Earth | $R_E$ | $6.38\cdot10^{6}\ m$ |
| Gravitational universal constant | $G$ | $6.67\cdot10^{-11}\ m^3\cdot s^{-2}\cdot kg^{-1}$ |
| Density of air at Earth's surface | $\rho_0$ | $1.29\ kg/m^3$ |
| Gravitational acceleration at Earth's surface | $g_0$ | $9.81\ m\cdot s^{-2}$ |
| Average magnitude of Earth's magnetic field | $B$ | $5.0\cdot10^{-5}\ T$ |
| The electron absolute charge | $e$ | $1.60\cdot10^{-19}\ C$ |

## Part A: Modified barometric formula [2.0 points]

The pressure of atmospheric air, composed mainly of neutral $O_2$ and $N_2$ molecules, can be found by using the Clapeyron-Mendeleev law (the ideal gas law): $pV = \frac{M}{\mu}RT$. where $p, V, T, M$ and $\mu$ are the pressure, volume, temperature, mass and molar mass of a portion of air, $R$ is the ideal gas universal constant.

There are two equations for computing air pressure as a function of height. The first equation is applicable to the standard model of the **troposphere** ($h < 100\,km$) in which the temperature is assumed to vary with altitude at a lapse rate.

The second equation belongs to the standard model of the **thermosphere** ($h > 250\,km$) in which the temperature is assumed not to change considerably with altitude and is applicable to ISS.

We may assume that all pressure is hydrostatic and isotropic (i.e., it acts with equal magnitude in all directions).

**A.1 [0.5 pt]** Derive the general integral expression for the air pressure $p_h$ at ISS altitude $h$. This equation is called the general barometric formula. Hint: the temperature and gravitation may depend on $h$.

*Remark 1.* The temperature of Earth's thermosphere at altitude $300-600\,km$ does not change considerably and reaches averagely about $800-900\,K$ on the solar side [NASA data]. Therefore, one may put $T_h = T = const$ by investigating the ISS orbital flight. Particularly, since the spacecraft spends almost half of its flight time in the shadow side of the Earth, where the temperature drops sharply, we may take the value of $T = 425\,K$ as the average temperature at these altitudes. This temperature is also in agreement with the air density value $\rho_h \sim 10^{-12}\,kg/\mathrm{m}^3$ [MSISE-90 Model of Earth's Upper Atmosphere] at $h = 400\,km$.

> **Figure 5 description.** "The Earth's thermosphere." Artistic diagram of the atmosphere above a curved Earth surface with layers labelled (from the ground up) Troposphere, Stratosphere, Mesosphere, Thermosphere. The Sun is drawn at the top. On the left, an altitude scale (0–600 km) with a "Temperature (K)" axis (ticks 400, 800, 1200) shows two temperature profiles labelled "Solar Min" (yellow) and "Solar Max" (red): both have a minimum near 100 km, rise steeply between about 100 and 250–300 km, and are nearly constant above about 300 km, at roughly 800 K (Solar Min) and roughly 1100–1200 K (Solar Max). In the middle, vertical bands show how deep solar radiation penetrates: X-Rays, Extreme UV 10–120 nm, Far UV 120–200 nm, Middle UV 200–300 nm, Near UV 300–400 nm, Visible and IR; wavy arrows, one labelled "IR Cooling", leave towards space. On the right, an altitude scale (0–600 km) with a "Density ($\log_{10}$ cm$^{-3}$)" axis (ticks 0, 4, 8, 12, 16, 20) shows the number-density profiles of $O_2$, $N_2$ and $O$ and an electron-density profile $e^-$ with ionospheric layers labelled D, E, F. Qualitative context only.

**A.2 [0.3 pt]** Write down the air pressure (the standard barometric formula) $p_h^{sta}$, when the temperature and gravitation $g_h$ do not depend on $h$. Calculate the parameter $h_0 = \frac{RT}{\mu g_0}$ for $T = 425\,K$.

**A.3 [0.6 pt]** Write down the air pressure (the improved barometric formula) $p_h^{imp}$ when the temperature is constant but the gravitation depends on $h$. Hint: Use the leading-order correction only, with accuracy $O(z_h^2)$. Hereby, the flight altitude $h$ above the Earth's surface is significantly smaller than the Earth's radius: $z_h \doteq h/R_E \ll 1$.

**A.4 [0.4 pt]** Write down the ratio of the 'standard' and 'improved' versions of the barometric formula $p_h^{imp}/p_h^{sta}$. Estimate it for $h = 4.0\times10^{5}\,m$. Further use the 'improved' version.

**A.5 [0.2 pt]** Write down the air density $\rho_h$ and the concentration of neutral air molecules $n_h$ at height $h$, with accuracy $O(z_h^2)$.

## Part B: Orbital deceleration and station descent rate [3.0 points]

Let us consider the problem of determining the rate of orbital decay of a satellite with mass $M_S$ that experiences constant friction force $\vec F_{drag}$ acting on it. We assume that the decrease in altitude $dh$ is much less than the flight altitude $h$ itself ($dh \ll h$).

**B.1 [0.5 pt]** Write down the satellite velocity $v_h$ and revolution period $\tau_h$ on a stable orbit of altitude $h$.

**B.2 [0.5 pt]** Write down the total energy $E_S$ of a satellite moving along a circular orbit with radius $R_E + h$.

**B.3 [1.0 pt]** The total decelerating force exerted on a satellite of constant mass is given by some external braking force $\vec F_{drag}$. As a result, the ISS slows down and its altitude decreases by a height $dh$ for a small time interval, $dt$. Write down the equation for the total enery balance of the ISS and surrounding system, given a value of $F_{drag}$.

**B.4 [0.5 pt]** Define the rate of descent (de-orbiting ) speed $u_h$ of the satellite. Hint: The de-orbiting speed depends on the friction force, and on the altitude of the satellite, and on the mass of the satellite.

**B.5 [0.5 pt]** Write down the amount of decent $H_h$ for a revolution around the Earth and the total time $T_h$ for which the satellite will fall from the altitude $h$ to the earth's surface due to the friction.
Hint: Take into account relations $h_0 \ll h \ll R_E$.

## Part C: Atmospheric drag [1.0 points]

The speed of the satellite $v$ is many times greater than the average velocities (hundreds m/s) of the thermal motion of atmospheric molecules at a height $h \approx 300-400\,km$, so we can assume that the molecules were at rest before the collision with the ISS. To roughly estimate the drag force, we assume that after the collision the molecules acquire the same speed as the satellite.

**C.1 [0.5 pt]** Write down the air drag force $F_{air}$, the de-orbiting descending velocity $u_h^{air}$ and the descent rate $H_h^{air}$.

**C.2 [0.5 pt]** Define the total time $T_h^{air}$ for which the satellite will fall from the altitude $h$ to the earth's surface due to air drag effect. Hint: Take into account relations $h_0 \ll h \ll R_E$.

## Part D: Drag by atomic oxygen ion [1.0 points]

In the thermosphere, under the influence of ultraviolet and X-ray solar radiation and cosmic radiation, air ionization occurs (''polar lights''). Unlike $O_2$, $N_2$ does not undergo strong dissociation under the action of solar radiation, therefore, in general, there is much less atomic nitrogen $N$ in the Earth's upper atmosphere than atomic oxygen. At altitudes above $250\,km$, atomic oxygen $O$ predominates. Layers containing electrons and ions of oxygen atoms appear on the day side of the atmosphere. In this case, the concentration of atomic oxygen ions reaches $n_{ion} \sim 10^{12}\,m^{-3}$

**D.1 [0.3 pt]** Write down the decelerating force $F_{ion}$, averaged during a 24-hour, associated with the mechanical collisions of these particles. Take into account the strong decrease in ionized layers are negligible during the night. Express the density of ionized oxygen molecules $\rho_{ion}$.

**D.2 [0.7 pt]** Define the speed of fall of the satellite $u_h^{ion}$ due to deceleration by ions of atomic oxygen. Write down the descent rate $H_h^{ion}$ for a revolution caused by the ionization effect. Hint: Take into account relations $h_0 \ll h \ll R_E$ .

## Part E: Drag by the Earth's magnetic field [2.0 points]

We consider the influence on the motion of the satellite of the Earth's magnetic field, the value of which near the Earth's surface is equal to $(3.5-6.5)\cdot10^{-5}\,T$ with an average value of $B = 5\cdot10^{-5}\,T$.

When a satellite moves at high speed in a magnetic field, an inducted electric current (electromotive force (EMF) ) occurs in the current-conducting elements of the satellite's structure. This electromotive force causes a redistribution of electric charges in the current-conducting elements of the satellite structure. An electric field appears around the satellite, which affects the movement electrically charged particles in the environment. Electrons are attracted to those parts of the satellite that have a positive potential (relative to the middle part of the satellite), and positively charged ions are attracted to those parts of the satellite that have a negative potential. Electrons and ions that hit the surface of the satellite structures are combined into neutral oxygen atoms, while the electrons 'travel' in the satellite's conductive structures, creating an electric current. The satellite, moving in space, 'collects' electrons and ions from the surrounding space and collides with them. For a rough estimate of the magnitude of the current that can flow through the conductive structures of the satellite, we will assume that the collection occurs only from an area equal to the cross-sectional area $S$ of the satellite, and all ions and electrons participate in the creation of this current.

**E.1 [0.6 pt]** Evaluate approximately the magnitude of the induced electric current $I_{ind}$ .

**E.2 [0.6 pt]** Determine an approximate expression for the induced 'braking' Ampere force $F_{ind}$ in the direction opposite to the direction of the satellite's motion.
Let $\phi$ be the angle between the Earth magnetic field $\vec B$along the longitude lines. To simplify, you may approximate the length of the satellite $L$ as the square root of the satellite area $S$. Additionally, instead of computing the average of $\sin(\phi)$, you may approximate it with $\sin(\pi/2-\theta)$. You may use a discrete number of sample points to compute an average value.

**E.3 [0.8 pt]** Write down the descent speed $u_{ind}$ of the satellite due to Earth's magnetic field. Write down the descent rate $H_h^{ind}$ for a revolution caused by the magnetic drag effect.
Hint: Take into account relations $h \ll R_E$.

## Part F: Numerical results and conclusion [1.0 points]

**F.1 [0.4 pt]** Calculate and fill Table 1 in the Answer Sheet.

**F.2 [0.4 pt]** Calculate and fill Table 2 in the Answer Sheet.

**F.3 [0.2 pt]** Rank these three orbital slowing processes in order of how strong an impact they have on ISS orbital altitudes higher than $380\,km$.
For the International Space Station, orbiting at an altitude above $380\,km$, write down the most significant factors contributing to orbital decay.

### Answer-sheet tables (layout from the official answer sheet; Korean version, translated)

**Table 1** (F.1). Deorbit velocities as a function of the height $h$ above the Earth's surface ($n_{ion} = 10^{13}\,\mathrm{m^{-3}}$). Fill all 20 empty cells.

| $h$ [km] | $T_h^{air}$ [day] | $u_{air}$ [m/day] | $u_{ion}$ [m/day] | $u_{ind}$ [m/day] | $\sum$ [m/day] |
|---|---|---|---|---|---|
| 350 | | | | | |
| 375 | | | | | |
| 400 | | | | | |
| 410 | | | | | |

**Table 2** (F.2). Descent rates for one revolution around the Earth ($n_{ion} = 10^{13}\,\mathrm{m^{-3}}$).

| $h$ [km] | $H_h^{air}$ [m] | $H_h^{ion}$ [m] | $H_h^{ind}$ [m] |
|---|---|---|---|
| 350 | | | |
| 375 | | | |
| 400 | | | |
| 410 | | | |

*(Note: the answer-sheet tables specify $n_{ion} = 10^{13}\,m^{-3}$, while Part D of the statement quotes $n_{ion} \sim 10^{12}\,m^{-3}$; both are reproduced as in the official documents.)*
