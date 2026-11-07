# IPhO 2025 — Theory Question T3 (Q3) [10 points]. Champagne!

*Text-only version of the official English statement (55th IPhO, France, 2025). Figures are described in words in "Figure description" blocks; numerical values quoted in those blocks were read off the official figures (approximate). Everything else follows the official wording. Answer-sheet boilerplate is omitted.*

## General Data Sheet (from the official General Instructions)

Throughout the examination, always refer to the quantities indicated in the instructions, unless otherwise stated. In all cases, the units of all quantities used should be given.

| Constant | Notation | Value | Unit |
|---|---|---|---|
| Speed of light in vacuum | $c$ | $2.99792458\times10^{8}$ | $\mathrm{m\cdot s^{-1}}$ |
| Planck constant | $h$ | $6.62607015\times10^{-34}$ | $\mathrm{kg\cdot m^2\cdot s^{-1}}$ |
| Reduced Planck constant | $\hbar=\frac{h}{2\pi}$ | $1.054571818\times10^{-34}$ | $\mathrm{kg\cdot m^2\cdot s^{-1}}$ |
| Boltzmann constant | $k_B$ | $1.380649\times10^{-23}$ | $\mathrm{kg\cdot m^2\cdot s^{-2}\cdot K^{-1}}$ |
| Avogadro constant | $N_A$ | $6.02214076\times10^{23}$ | $\mathrm{mol^{-1}}$ |
| Molar gas constant | $R$ | $8.31446261815324$ | $\mathrm{kg\cdot m^2\cdot s^{-2}\cdot mol^{-1}\cdot K^{-1}}$ |
| Elementary charge | $e$ | $1.602176634\times10^{-19}$ | $\mathrm{A\cdot s}$ |
| Universal constant of gravitation | $G$ | $6.67430(15)\times10^{-11}$ | $\mathrm{m^3\cdot kg^{-1}\cdot s^{-2}}$ |
| Standard acceleration due to gravity | $g$ | $9.80665$ | $\mathrm{m\cdot s^{-2}}$ |
| Stefan Boltzmann constant | $\sigma$ | $5.670374419\times10^{-8}$ | $\mathrm{kg\cdot s^{-3}\cdot K^{-4}}$ |
| Vacuum permeability (magnetic constant) | $\mu_0$ | $1.25663706127(20)\times10^{-6}$ | $\mathrm{kg\cdot m\cdot A^{-2}\cdot s^{-2}}$ |
| Vacuum permittivity (electrical constant) | $\epsilon_0$ | $8.8541878188(14)\times10^{-12}$ | $\mathrm{A^2\cdot s^4\cdot kg^{-1}\cdot m^{-3}}$ |
| Rydberg constant | $R_\infty$ | $1.0973731568157(12)\times10^{7}$ | $\mathrm{m^{-1}}$ |
| Mass of the electron | $m_e$ | $9.1093837139(28)\times10^{-31}$ | $\mathrm{kg}$ |
| Mass of the proton | $m_p$ | $1.67262192595(52)\times10^{-27}$ | $\mathrm{kg}$ |
| Mass of the neutron | $m_n$ | $1.67492750056(85)\times10^{-27}$ | $\mathrm{kg}$ |
| Atomic mass constant | $m_u$ | $1.66053906892(52)\times10^{-27}$ | $\mathrm{kg}$ |
| Electronvolt | eV | $1.602176634\times10^{-19}$ | $\mathrm{kg\cdot m^2\cdot s^{-2}}$ |

---

# Champagne! (10 points)

**Warning:** Excessive alcohol consumption is harmful to health and drinking alcohol below legal age is prohibited.

Champagne is a French sparkling wine. Fermentation of sugars produces carbon dioxide (CO$_2$) in the bottle. The molar concentration of CO$_2$ in the liquid phase $c_\ell$ and the partial pressure $P_{\rm CO_2}$ in the gas phase are related by $c_\ell = k_{\rm H}P_{\rm CO_2}$, known as Henry's law and where $k_{\rm H}$ is called Henry's constant.

> **Figure description (Fig. 1. A glass filled with champagne.)** Photograph of a champagne flute full of sparkling wine with rising bubbles. Decorative only.

**Data**

- Surface tension of champagne $\sigma = 47\times10^{-3}\ \mathrm{J\cdot m^{-2}}$
- Density of the liquid $\rho_\ell = 1.0\times10^3\ \mathrm{kg\cdot m^{-3}}$
- Henry's constant at $T_0 = 20$ °C, $k_{\rm H}(20\,°\mathrm{C}) = 3.3\times10^{-4}\ \mathrm{mol\cdot m^{-3}\cdot Pa^{-1}}$
- Henry's constant at $T_0 = 6$ °C, $k_{\rm H}(6\,°\mathrm{C}) = 5.4\times10^{-4}\ \mathrm{mol\cdot m^{-3}\cdot Pa^{-1}}$
- Atmospheric pressure $P_0 = 1\ \mathrm{bar} = 1.0\times10^5$ Pa
- Gases are ideal with an adiabatic coefficient $\gamma = 1.3$

*(Editor's note: $\vec g_0$, used below, is the gravitational acceleration, pointing downward; no specific value is given in the statement — see the General Data Sheet.)*

## Part A. Nucleation, growth and rise of bubbles

Immediately after opening a bottle of champagne at temperature $T_0 = 20$ °C, we fill a glass. The pressure in the liquid is $P_0$ and its temperature stays constant at $T_0$. The concentration $c_\ell$ of dissolved CO$_2$ exceeds the equilibrium concentration and we study the nucleation of a CO$_2$ bubble. We note $a$ its radius and $P_{\rm b}$ its inner pressure.

**A.1 (0.2 pt)** Express the pressure $P_{\rm b}$ in terms of $P_0$, $a$ and $\sigma$.

In the liquid, the concentration of dissolved CO$_2$ depends on the distance to the bubble. At long distance we recover the value $c_\ell$ and we note $c_{\rm b}$ the concentration close to the bubble surface. According to Henry's law, $c_{\rm b} = k_{\rm H}P_{\rm b}$. We furthermore assume in all the problem that bubbles contain only CO$_2$.

Since $c_\ell\ne c_{\rm b}$, CO$_2$ molecules diffuse from areas of high to low concentration. We assume also that any molecule from the liquid phase reaching the bubble surface is transferred to the vapour.

**A.2 (0.5 pt)** Express the critical radius $a_{\rm c}$ above which a bubble is expected to grow in terms of $P_0$, $\sigma$, $c_\ell$ and $c_0$ where $c_0 = k_{\rm H}P_0$. Calculate numerically $a_{\rm c}$ for $c_\ell = 4c_0$.

In practice, bubbles mainly grow from pre-existing gas cavities. Consider then a bubble with initial radius $a_0\approx40\ \mu$m. The number of moles of CO$_2$ transferred at the bubble's surface per unit area and time is noted $j$. Two models are possible for $j$.

- model (1) $j = \dfrac{D}{a}(c_\ell - c_{\rm b})$ where $D$ is the diffusion coefficient of CO$_2$ in the liquid.
- model (2) $j = K(c_\ell - c_{\rm b})$ where $K$ is a constant here.

Experimentally, the bubble radius $a(t)$ is found to depend on time as shown in **Fig. 2**. Here $c_\ell\approx4c_0$, and since bubbles are large enough to be visible, the excess pressure due to surface tension can be neglected and $P_{\rm b}\approx P_0$.

**A.3 (1.2 pt)** Express the number of CO$_2$ moles in the bubble $n_{\rm c}$ in terms of $a$, $P_0$, $T_0$ and ideal gas constant $R$. Find $a(t)$ for both models. Indicate which model explains the experimental results in **Fig. 2**. Depending on your answer, calculate numerically $K$ or $D$.

> **Figure description (Fig. 2. Time evolution of CO$_2$ bubble radius in a glass of champagne (adapted from [1]).)** Horizontal axis $t$ (s) from 0 to about 0.98 (labels 0.0, 0.2, 0.4, 0.6, 0.8); vertical axis $a$ ($\mu$m) from about 5 to 305 (labels 50 to 300 in steps of 50). Eighteen data points (blue squares), each with a vertical error bar of about $\pm23\ \mu$m. Values read from the figure:
>
> | $t$ (s) | 0.00 | 0.054 | 0.112 | 0.166 | 0.222 | 0.279 | 0.335 | 0.391 | 0.448 | 0.502 | 0.560 | 0.616 | 0.671 | 0.728 | 0.783 | 0.840 | 0.894 | 0.950 |
> |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
> | $a$ ($\mu$m) | 38 | 49 | 71 | 85 | 99 | 112 | 120 | 127 | 141 | 156 | 169 | 177 | 189 | 210 | 224 | 248 | 254 | 269 |
>
> The points lie close to a straight line (no visible curvature).

Eventually bubbles detach from the bottom of the glass and continue to grow while rising. **Fig. 3** shows a train of bubbles. The bubbles of the train have the same initial radius and are emitted at a constant frequency $f_{\rm b} = 20$ Hz.

> **Figure description (Fig. 3. A train of bubbles. The photo is rotated horizontally for the page layout (adapted from [1]).)** A grey photograph, about 16.0 mm long and 1.5 mm high (scale bar "1 mm" drawn below it), of a single line of bubbles rising in champagne. The photo is rotated: the vertical upward direction $\vec u_z$ points to the **right** (the $z$ axis is drawn below the photo with its origin at the left edge of the photo), and $\vec g_0$ points to the **left**. Bubbles appear as dark rings, small and closely spaced at the left (bottom), larger and farther apart towards the right (top). Positions of the bubble centres along $z$, measured from the origin of the $z$ axis, and apparent outer diameters (measured from the image; the image is blurred, so diameters carry about $\pm0.03$ mm uncertainty, more for the smallest bubbles):
>
> | bubble (from the left) | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 (last, rightmost) |
> |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
> | centre $z$ (mm) | 0.20 | 0.39 | 0.68 | 1.03 | 1.52 | 2.16 | 2.92 | 3.85 | 4.94 | 6.22 | 7.71 | 9.38 | 11.26 | 13.38 | 15.68 |
> | diameter (mm) | ≈0.06 | ≈0.07 | ≈0.09 | ≈0.18 | ≈0.21 | 0.25 | 0.27 | 0.30 | 0.32 | 0.35 | 0.38 | 0.41 | 0.43 | 0.45 | 0.48 |
>
> (A faint, partly cut blob is also visible at the very left edge, $z\approx0.05$ mm.)

For the range of velocities studied here, the drag force $F$ on a bubble of radius $a$ moving at velocity $v$ in a liquid of dynamic viscosity $\eta$ is given by Stokes' law $F = 6\pi\eta av$. Measurements show that at any moment in time, the bubble can be assumed to be travelling at its terminal velocity.

**A.4 (0.8 pt)** Give the expression of the main forces exerted on a vertically rising bubble. Obtain the expression of $v(a)$. Give a numerical estimate of $\eta$ using $\rho_\ell$, $g_0$ and quantities measured on **Fig. 3**.

The quasi-stationary growth of bubbles with rate $q_a = \dfrac{\mathrm da}{\mathrm dt}$ still applies during bubble rise.

**A.5 (0.5 pt)** Express the radius $a_{H_\ell}$ of a bubble reaching the free surface in terms of height travelled $H_\ell$, growth rate $q_a = \frac{\mathrm da}{\mathrm dt}$, and any constants you may need. Assume $a_{H_\ell}\gg a_0$ and $q_a$ constant, and give the numerical value of $a_{H_\ell}$ with $H_\ell = 10$ cm and $q_a$ corresponding to **Fig. 2**.

There are $N_{\rm b}$ nucleation sites of bubbles. Assume that the bubbles are nucleated at a constant frequency $f_{\rm b}$ at the bottom of a glass of champagne (height $H_\ell$ for a volume $V_\ell$), with $a_0$ still negligible. Neglect diffusion of CO$_2$ at the free surface.

**A.6 (1.1 pt)** Write the differential equation for $c_\ell(t)$. Obtain from this equation the characteristic time $\tau$ for the decay of the concentration of dissolved CO$_2$ in the liquid.

## Part B. Acoustic emission of a bursting bubble

Small bubbles are nearly spherical as they reach the free surface. Once the liquid film separating the bubble from the air thins out sufficiently, a circular hole of radius $r$ forms in the film and, driven by surface tension, opens very quickly (**Fig. 4.** left). The hole opens at constant speed $v_{\rm f}$ (**Fig. 4.** right). The film outside the rim remains still, with constant thickness $h$.

> **Figure description (Fig. 4).** *(Left)* Four cross-section sketches of a bubble at the free surface. $(\alpha)$ Bubble at the surface: a spherical cavity of radius $a$ (region (3), CO$_2$ at pressure $P_{\rm b}$) just below the flat free surface of the liquid (region (1)); above is air (region (2)) at pressure $P_0$; the top of the bubble is capped by a thin liquid film slightly bulging above the free surface; point $A$ is the top of the cap, and $r_c$ is the horizontal radius of the cap (circle where the film meets the free surface). $(\beta)$ and $(\gamma)$ retraction of the liquid film: the film has a hole centred on $A$ of radius $r(t)$; the edge of the film is a thickened rim (dark blue) moving outward with velocity $\vec v_{\rm f}$; the film thickness is $h$. $(\delta)$ bubble collapse: the cap has disappeared, leaving an open cavity in the surface.
> *(Right)* Retraction of the liquid film at time $t$. Top: sketch of the pierced film seen from above: a circular hole of radius $r(t)$ centred on $A$, surrounded by an annular rim (dark), surrounded by the still film; a dotted annulus of width $v_{\rm f}\,\mathrm dt$ just outside the rim is the film liquid collected during $\mathrm dt$. Bottom: cross-section: the rim is a roughly circular bulge of radius $R_{\rm m}$ at distance $r(t)$ from the axis through $A$, moving outward with velocity $\vec v_{\rm f}$; outside it the flat film of thickness $h$; the strip of length $v_{\rm f}\,\mathrm dt$ of film adjacent to the rim is accumulated into the rim during $\mathrm dt$ (dotted).

Due to dissipative processes, only half of the difference of the surface energy between $t$ and $t+\mathrm dt$ of the rim and the accumulated liquid is transformed into kinetic energy. We further assume that the variation of the surface of the rim is negligible compared to that of the film.

**B.1 (1.1 pt)** Express $v_{\rm f}$ in terms of $\rho_\ell$, $\sigma$ and $h$.

When the film bursts, it releases internal pressure and emits a sound. We model this acoustic emission by a Helmholtz resonator: a cavity open to the atmosphere at $P_0$ through a bottleneck aperture of area $S$ (**Fig. 5.** left). In the neck, a mass $m_{\rm p}$ makes small amplitude position oscillations due to the pressure forces it experiences as the gas in the cavity expands or compresses adiabatically. The gravity force on $m_{\rm p}$ is negligible compared to pressure forces. Let $V_0$ be the volume of gas under the mass $m_{\rm p}$ for $P = P_0$ as $z = 0$.

> **Figure description (Fig. 5).** *(Left)* A Helmholtz resonator: a spherical cavity containing gas at pressure $P(t)$, with a narrow vertical neck of cross-section $S$ on top; a small piston (plug) of mass $m_{\rm P}$ sits in the neck; its position is measured by $z$ along a vertical axis, with $z = 0$ the equilibrium position; outside, above the neck, the pressure is $P_0$. *(Right)* A bubble as an oscillator: a spherical bubble of radius $a$ just below the free surface, with a circular aperture of diameter $2r$ at its top opening to the air.

**B.2 (1.1 pt)** Express the frequency of oscillation $f_0$ of $m_{\rm p}$. Hint: for $\varepsilon\ll1$, $(1+\varepsilon)^\alpha\approx1+\alpha\varepsilon$.

The Helmholtz model may be used for a bubble of radius $a$. $V_0$ is the volume of the closed bubble. From litterature, the mass of the equivalent of the piston is $m_p = 8\rho_g r^3/3$ where $r$ is the radius of the circular aperture and $\rho_g = 1.8\ \mathrm{kg\cdot m^{-3}}$ is the density of the gas (**Fig. 5**. right). During the bursting process, $r$ goes from 0 to $r_{\rm c}$, given by $r_{\rm c} = \dfrac{2}{\sqrt3}a^2\sqrt{\dfrac{\rho_\ell g_0}{\sigma}}$. At the same time, the frequency of emitted sound increases until a maximum value of 40 kHz and the bursting time is $t_b = 3\times10^{-2}$ ms.

**B.3 (1.1 pt)** Find the radius $a$ and the thickness $h$ of the champagne film separating the bubble from the atmosphere.

## Part C. Popping champagne

In a bottle, the total quantity of CO$_2$ is $n_{\rm T} = 0.2$ mol, either dissolved in the volume $V_{\rm L} = 750$ mL of liquid champagne, or as a gas in the volume $V_{\rm G} = 25$ mL under the cork (**Fig. 6.** left). $V_{\rm G}$ contains only CO$_2$. The equilibrium between both CO$_2$ phases follows Henry's Law. We suppose that the fast gaseous CO$_2$ expansion when the bottle is opened, is adiabatic and reversible. Ambient temperature $T_0$ and pressure $P_0 = 1$ bar are constant.

> **Figure description (Fig. 6).** *(Left)* Traditional bottleneck (enlarged from a sketch of a champagne bottle): from top to bottom, (1) surrounding air at $P_0$; (2) the cork stopper, whose cylindrical part of diameter $d$ and length $\ell_0$ is stuck inside the neck (a mushroom-shaped head sits above the neck); (3) the headspace containing CO$_2$ gas at pressure $P_{\rm i}$ in volume $V_{\rm G}$; (4) the liquid champagne of volume $V_{\rm L}$ with dissolved CO$_2$ at concentration $c_\ell = k_{\rm H}P_{\rm i}$. *(Right)* Two photographs of a bottle neck just after the cork leaves, at two different temperatures: in the first, a bluish fog/plume emerges from the neck; in the second, a grey-white fog cloud surrounds the neck. (Which temperature corresponds to which photo is not indicated.)

**C.1 (0.4 pt)** Give the numerical value of the pressure $P_{\rm i}$ of gaseous CO$_2$ in the bottle for $T_0 = 6$ °C and $T_0 = 20$ °C.

Another step of champagne production (not described here) leads to the following values of $P_i$ that we will use for the next questions: $P_{\rm i} = 4.69$ bar at $T_0 = 6$ °C and $P_{\rm i} = 7.45$ bar at $T_0 = 20$ °C.

During bottle opening, two different phenomena can be observed, depending on $T_0$ (Fig. 6. right).

- either a blue fog appears, due to the formation of solid CO$_2$ crystals (but water condensation is inhibited);
- or a grey-white fog appears, due to water vapor condensation in the air surrounding the bottleneck. In this latter case, there is no formation of CO$_2$ solid crystals.

The saturated vapor pressure $P_{\rm sat}^{\rm CO_2}$ for the CO$_2$ solid/gas transition follows: $\log_{10}\left(\dfrac{P_{\rm sat}^{\rm CO_2}}{P_0}\right) = A - \dfrac{B}{T+C}$ with $T$ in K, $A = 6.81$, $B = 1.30\times10^3$ K and $C = -3.49$ K.

**C.2 (0.7 pt)** Give the numerical value $T_{\rm f}$ of the CO$_2$ gas at the end of the expansion, after opening a bottle, if $T_0 = 6$ °C and if $T_0 = 20$ °C, if no phase transition occured.
Choose which statements are true (several statements possible):
1. At $T_0 = 6$ °C a grey-white fog appears while opening the bottle.
2. At $T_0 = 6$ °C a blue fog appears while opening the bottle.
3. At $T_0 = 20$ °C a grey-white fog appears while opening the bottle.
4. At $T_0 = 20$ °C a blue fog appears while opening the bottle.

During bottle opening, the cork stopper pops out. We now determine the maximum height $H_{\rm c}$ it reaches. Assume that the friction force $F$ due to the bottleneck on the cork stopper is $F = \alpha A$ where $A$ is the area of contact and $\alpha$ is a constant to determine. Initially, the pressure force slightly overcomes the friction force. The cork's mass is $m = 10$ g, its diameter $d = 1.8$ cm and the length of the cylindrical part initially stuck in the bottleneck is $\ell_0 = 2.5$ cm. Once the cork has left the bottleneck, you can neglect the net pressure force.

**C.3 (1.3 pt)** Give the numerical value of $H_{\rm c}$ if the external temperature is $T_0 = 6$ °C.

[1] Liger-Belair et al, Am. J. Enol. Vitic., Vol. 50, No. 3 (1999).
[2] Liger-Belair et al., Sc. Reports 7, 10938 (2017).
