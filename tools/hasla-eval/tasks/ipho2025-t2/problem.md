# IPhO 2025 — Theory Question T2 (Q2) [10 points]. Cox's Timepiece

*Text-only version of the official English statement (55th IPhO, France, 2025). Figures are described in words in "Figure description" blocks; everything else follows the official wording. Answer-sheet boilerplate is omitted.*

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

# Cox's Timepiece (10 points)

In 1765, British clockmaker James Cox invented a clock whose only source of energy is the fluctuations in atmospheric pressure. Cox's clock used two vessels containing mercury. Changes in atmospheric pressure caused mercury to move between the vessels, and the two vessels to move relative to each other. This movement acted as an energy source for the actual clock.

> **Figure description (Fig. 1. Artistic view of Cox's clock [1]).** A drawing of a tall ornate clock case in a museum gallery, with visitors; the clock dial is at the top and two glass vessels are visible inside the case. Decorative only.

We propose an analysis of this device. Throughout, we assume that

- the Earth's gravitational field $\vec g = -g\,\vec u_z$ is uniform with $g = 9.8\ \mathrm{m\cdot s^{-2}}$ and $\vec u_z$ a unit vector;
- all liquids are incompressible and their density is denoted $\rho$;
- no surface tension effects will be considered;
- the variations of atmospheric pressure with altitude are neglected;
- the surrounding temperature $T_{\rm a}$ is uniform and all transformations are isothermal.

## Part A - Pulling on a submerged tube

We first consider a bath of water that occupies the semi-infinite space $z\le0$. The air above it is at a pressure $P_{\rm a} = P_0$. A cylindrical vertical tube of length $H = 1$ m, cross-sectional area $S = 10\ \mathrm{cm^2}$ and mass $m = 0.5$ kg is dipped into the bath. The bottom end of the tube is open, and the top end of the tube is closed. We denote $h$ the altitude of the top of the tube and $z_\ell$ that of the water inside the tube. The thickness of the tube walls is neglected.

> **Figure description (Fig. 2. Sketch of the tube in different configurations).** Three panels, each with a vertical $z$ axis; the bath surface is at $z=0$ (liquid below, air above), $\vec g$ points down, and a pulling force $\vec F$ (upward arrow) acts on a hook at the closed top of the tube.
> **(a)** The tube is entirely submerged with its closed top exactly at the bath surface: $h = z_\ell = 0$; its length $H$ extends below the surface; it is full of liquid.
> **(b)** The tube has been lifted: its top is at altitude $h>0$ above the bath surface and the tube is still completely full of liquid up to its top: $h = z_\ell$. Its open bottom is still under the bath surface.
> **(c)** The tube is lifted further: the liquid column inside reaches only $z_\ell < h$; the space between $z_\ell$ and the closed top $h$ is empty of liquid (white; filled only by vapour).

We start from the situation where the tube in Fig. 2 contains no gas and its top is at the bath level: in other words, $h=0$ and $z_\ell=0$ (case a). The tube is then slowly lifted until its bottom end reaches the bath level. The pulling force exerted on the tube is denoted $\vec F = F\,\vec u_z$.

**A.1 (0.2 pt)** For the configuration shown in Fig. 2 (case b), express the pressure $P_{\rm w}$ in the water at the top of the tube. Also express the force $\vec F$ necessary to maintain the tube at this position. Expressions must be written in terms of $P_0$, $\rho$, $m$, $S$, $h$, $g$ and $\vec u_z$.

Three experiments are performed. In each, the tube is lifted from the initial state shown in Fig. 2(a) under the conditions specified in Table 1.

| Experiment | Liquid | $T_{\rm a}$ (°C) | $\rho$ (kg·m⁻³) | $P_{\rm sat}$ (Pa) |
|---|---|---|---|---|
| 1 | Water | 20 | $1.00\times10^3$ | $2.34\times10^3$ |
| 2 | Water | 80 | $0.97\times10^3$ | $47.4\times10^3$ |
| 3 | Water | 99 | $0.96\times10^3$ | $99.8\times10^3$ |

*Table 1. Experimental conditions and numerical values of physical quantities for each experiment ($P_{\rm sat}$ designates the saturated vapour pressure of the pure fluid).*

In each case, we study the evolution of the force $F$ that must be applied in order to maintain the tube in equilibrium at an altitude $h$, the external pressure being fixed at $P_{\rm a} = P_0 = 1.000\times10^5$ Pa. Two different behaviours are possible

> **Figure description (the two behaviours).** Two graphs of $F$ versus $h$, both starting at $F = F_0$ for $h = 0$.
> **Behaviour A:** $F$ increases linearly with $h$ over the whole range $0\le h\le H$, reaching its largest value $F_{\max}$ at $h = H$.
> **Behaviour B:** $F$ increases linearly from $F_0$ up to $F_{\max}$ at $h = h^\star$ (with $0<h^\star<H$), then stays constant at $F_{\max}$ (horizontal segment) from $h^\star$ to $H$.

**A.2 (0.8 pt)** For each experiment, complete the table in the answer sheet to indicate the expected behaviour and the numerical values for $F_{\max}$ and for $h^\star$ (when pertinent), where $F_{\max}$ and $h^\star$ are defined in the figures illustrating the two behaviours.

*(Answer-sheet table columns: Experiment | Behaviour (A or B?) | $h^\star$ (cm) | $F_{\max}$ (N), for experiments 1, 2, 3.)*

When we replace the water with liquid mercury (whose properties are given below), behaviour B is observed.

| Liquid | $T_{\rm a}$ (°C) | $\rho$ (kg·m⁻³) | $P_{\rm sat}$ (Pa) |
|---|---|---|---|
| Mercury | 20 | $13.5\times10^3$ | 0.163 |

**A.3 (0.3 pt)** Express the relative error, denoted $\varepsilon$, committed when we evaluate the maximal force $F_{\max}$ neglecting $P_{\rm sat}$ compared to $P_0$. Give the numerical value of $\varepsilon$.

## Part B - Two-part barometric tube

From now on, we work with mercury (density $\rho = 13.5\times10^3\ \mathrm{kg\cdot m^{-3}}$) at the ambient temperature $T_{\rm a} = 20$ °C and we take $P_{\rm sat} = 0$.

Let us consider a tube with a reservoir on top, modeled as two superposed cylinders of different dimensions, as shown in Fig. 3.

- the bottom part (still called the tube) has cross-sectional area $S_{\rm t}$ and height $H_{\rm t} = 80$ cm;
- the top part (called the bulb) has cross-sectional area $S_{\rm b} > S_{\rm t}$ and height $H_{\rm b} = 20$ cm.

This two-part tube is dipped into a semi-infinite liquid bath.

> **Figure description (Fig. 3. Sketch of the two-part barometric tube).** Vertical $z$ axis; bath surface at $z = 0$. A narrow vertical tube (height $H_{\rm t} = 80$ cm, open at its bottom, which is below the bath surface) is topped by a wider cylindrical bulb (height $H_{\rm b} = 20$ cm) closed at its top; a hook at the top of the bulb carries the upward force $\vec F$; $\vec g$ points down. The junction between tube and bulb is at altitude $h_{\rm t}$ (above the bath surface in the drawing). Mercury fills the tube and the lower part of the bulb up to the free surface at altitude $z_\ell$ (between $h_{\rm t}$ and $h_{\rm t}+H_{\rm b}$); above $z_\ell$ the bulb is empty (vacuum, $P_{\rm sat}=0$).

As in Part A, the system is prepared such that the tube contains no air. We identify the vertical position of the tube by the altitude $h_{\rm t}$ of the junction between the tube and the bulb. The height of the column of mercury is again denoted $z_\ell$. The force $\vec F$ that must be exerted to maintain the tube in equilibrium in the configuration shown in Fig. 3 can now be written as

$$\vec F = (m_{\rm tb} + m_{\rm add})\,g\,\vec u_z \tag{1}$$

where $m_{\rm tb}$ is the total mass of the two-part tube (when empty of mercury).

**B.1 (0.3 pt)** `[GRAPH/FIGURE-DEPENDENT]` On the answer sheet, color the area corresponding to the volume of liquid mercury that is responsible for the term $m_{\rm add}$ appearing in equation (1).

> *(The answer-sheet drawing reproduces Fig. 3: the two-part tube in the bath, junction above the bath surface, mercury up to $z_\ell$ inside the bulb. Text-only version: describe precisely which volume of mercury would be coloured, and give $m_{\rm add}$ as an expression.)*

The mass $m_{\rm add}$ depends both on the height $h_{\rm t}$ and the atmospheric pressure $P_{\rm a}$. For the next question, assume that the atmospheric pressure is fixed at $P_{\rm a} = P_0 = 1.000\times10^5$ Pa. Starting from the situation where the system is completely submerged, the tube is slowly lifted until its base is flush with the liquid bath.

**B.2 (1.4 pt)** `[GRAPH/FIGURE-DEPENDENT]` Sketch the evolution of the mass $m_{\rm add}$ as a function of $h_{\rm t}$ for $h_{\rm t}\in[-H_{\rm b}, H_{\rm t}]$. On the graph, provide the expression for the slopes of the different segments, as well as the $h_{\rm t}$ analytical value of any angular points, in terms of $P_0$, $\rho$, $g$, $S_{\rm b}$, $S_{\rm t}$, $H_{\rm b}$ and $H_{\rm t}$.

> *(Text-only version: describe the graph in words — number of straight segments, sign and expression of each slope, value of $m_{\rm add}$ at the start, and the $h_{\rm t}$ values of the angular points.)*

As the system is lifted while $P_{\rm a} = P_0 = 10^5$ Pa, we stop when the free surface of the liquid is in the middle of the bulb. The value of $h_{\rm t}$ is fixed and then we observe variations in the mass $m_{\rm add}$ due to variations in the atmospheric pressure described by

$$P_{\rm a}(t) = P_0 + P_1(t) \tag{2}$$

where $P_0$ designates the average value and $P_1$ is a perturbative term. We model $P_1$ by a periodic triangular function of amplitude $A = 5\times10^2$ Pa and period $\tau_1$ of 1 week.

> **Figure description (Fig. 4. Simplified model of the perturbative term $P_1(t)$).** A symmetric triangular wave between $-A$ and $+A$, with period $\tau_1$: $P_1(0) = 0$ and increasing linearly, $P_1 = +A$ at $t = \tau_1/4$, $P_1 = 0$ at $t=\tau_1/2$, $P_1 = -A$ at $t = 3\tau_1/4$, back to $0$ at $t = \tau_1$ (increasing), and so on; the plot shows about six periods.

**B.3 (0.3 pt)** Given that $S_{\rm t} = 5\ \mathrm{cm^2}$ and $S_{\rm b} = 200\ \mathrm{cm^2}$, express the amplitude $\Delta m_{\rm add}$ of the variations of the mass $m_{\rm add}$ over time, then give its numerical value. *Assume that the liquid surface always stays in the bulb.*

## Part C - Cox's timepiece

The real mechanism developed by Cox is complex (Fig. 5). We study a simplified version, depicted in Fig. 6, and described below

- a cylindrical bottom cistern containing a mercury bath;
- a two-part barometric tube identical to that studied in part B, which is still completely emptied of any air, is dipped into the bath;
- the cistern and the two-part tube are each suspended by a cable. Both cables (assumed to be inextensible and of negligible mass) pass through a system of ideal pullies and finish attached to either side of the same mass $M$, which can slide on a horizontal surface;
- the total volume of liquid mercury contained in the system is $V_\ell = 5$ L.

The height, cross-section and masses of each part are given in Table 2. The position of mass $M$ is referenced by the coordinate $x$ of its center of mass. We consider solid friction between the horizontal support and the mass $M$, without distinction between static and dynamic coefficients; the magnitude of this force when sliding occurs is denoted $F_{\rm s}$.

Two stops limit the displacement of the mass $M$ such that $-X\le x\le X$ (with $X>0$). Assume that the value of $X$ guarantees that

- the bottom of the two-part tube never touches the bottom of the cistern nor comes out of the liquid bath;
- the altitude $z_\ell$ of the mercury column is always in the upper bulb.

> **Figure description (Fig. 5. Real Cox's timepiece [2] (without mercury)).** Photograph of the actual clock in a tall glazed wooden case: dial at the top, a large glass bulb hanging above a long glass tube that dips into a glass vessel at the bottom. Decorative only.
>
> **Figure description (Fig. 6. Sketch of the system modeling the timepiece).** At the top, the mass $M$ rests on a horizontal (hatched) support and can slide along the horizontal $x$ axis (pointing to the right); a vertical pointer on $M$ moves between two stops at $x=-X$ and $x=+X$. Two cables leave $M$ horizontally:
> – the cable attached to the **left** side of $M$ runs left to a pulley, down to a second pulley, right to a pulley near the centre, then hangs vertically down and is attached (through a two-strand yoke) to the rim of the **cistern** (reference 1, containing the liquid-mercury bath);
> – the cable attached to the **right** side of $M$ runs right to a pulley, down to a second pulley, left to a pulley near the centre, then hangs vertically down to the hook on top of the **bulb** (reference 2′) of the two-part barometric tube, whose narrow tubular part (reference 2) dips into the mercury of the cistern.
> Consequently, a displacement of $M$ by $+\delta x$ (to the right) lowers the barometric tube by $\delta x$ and raises the cistern by $\delta x$; the tension of the tube cable pulls $M$ towards $+x$ and the tension of the cistern cable pulls $M$ towards $-x$. The bulb contains mercury up to a level inside the bulb, with vacuum above it.

| Reference | Name | Height | Cross section area | Empty mass |
|---|---|---|---|---|
| 1 | cistern | $H_{\rm c} = 30$ cm | $S_{\rm c} = 210\ \mathrm{cm^2}$ | $m_{\rm c}$ |
| 2 | tubular part of the barometric tube | $H_{\rm t} = 80$ cm | $S_{\rm t} = 5\ \mathrm{cm^2}$ | total mass of the barometric tube: $m_{\rm tb}$ |
| 2′ | bulb of the barometric tube | $H_{\rm b} = 20$ cm | $S_{\rm b} = 200\ \mathrm{cm^2}$ | (included in $m_{\rm tb}$) |

*Table 2. Dimensions and notations for the model system.*

The system evolves in contact with the atmosphere, whose pressure fluctuates as in Fig. 4 (still with amplitude $A = 5\times10^2$ Pa and period $\tau_1 = 1$ week). At the start $t=0$, the mass $M$ is at rest at $x=0$ and the tensions exerted by the two cables on either side of the mass $M$ are in balance while $P_1(0) = 0$. We define

$$\xi = \frac{S_{\rm b}+S_{\rm c}-S_{\rm t}}{S_{\rm b}S_{\rm c}}\,\frac{F_{\rm s}}{A} \simeq \frac{S_{\rm b}+S_{\rm c}}{S_{\rm b}S_{\rm c}}\,\frac{F_{\rm s}}{A} \tag{3}$$

where the last expression uses that $S_{\rm t}\ll S_{\rm b}, S_{\rm c}$ (which we will assume is valid until the end of the problem).

**C.1 (1 pt)** Determine the threshold $\xi^\star$ such that $M$ remains indefinitely at rest when $\xi>\xi^\star$.

For the next question only, suppose that the mass $M$ is temporarily blocked at $x = X$.

**C.2 (1 pt)** Give an expression for the total tension force $\vec T = T\,\vec u_x$ acting on the mass $M$ due to the tension in two cables at this position, when $P_1 = 0$, in terms of $\rho$, $g$, $X$ and pertinent cross-sections.

When $\xi<\xi^\star$, starting again from $x=0$ and $P_1 = 0$, two different behaviours can be observed for $t\ge0$. To distinguish them, we need to introduce another parameter

$$\lambda = \frac{2(S_{\rm b}-S_{\rm t})}{S_{\rm b}}\,\frac{\rho g X}{A} \simeq \frac{2\rho gX}{A} \tag{4}$$

**C.3 (2 pt)** `[GRAPH/FIGURE-DEPENDENT]` Complete the table in the answer sheet to indicate the condition under which each regime is obtained. Conditions must be expressed as inequalities on $\xi$ and/or $\lambda$. In addition, sketch the variations of $x(t)/X$ for $t\in[0, 3\tau_1]$ that are consistent with the variations of $P_1(t)/A$ already present. *Specification of remarkable points coordinates is not required.*

> *(Answer-sheet table: rows "Regime 1" and "Regime 2"; columns "Condition for observation" and "Graph of $x(t)/X$"; each graph box already shows $P_1(t)/A$ as a dashed triangular wave over $[0,3\tau_1]$ with ticks at $\tau_1$, $2\tau_1$, $3\tau_1$. Text-only version: give the two conditions and describe each graph of $x(t)/X$ in words — when the switches happen relative to the $P_1$ wave, their duration, and the levels.)*

In the real Cox's timepiece, energy provided by the mechanism is stored using a system of ratchets and used to raise a counterweight, like in a traditional clock. In the simplified model studied here, the energy recovered by the clock corresponds to the energy dissipated by the friction force exerted by the horizontal surface on the mass $M$. From now on, we assume that the system is dimensioned such that to work in the regime that allows the clock to recuperate energy. We also assume that the permanent regime is established. We denote $W$ the energy dissipated by the solid friction force during a period $\tau_1$, which can be expressed only in terms of $F_{\rm s}$ and $X$.

All else equal, $F_{\rm s}$ and $X$ can be adjusted to maximize the energy $W$; we denote $F_{\rm s}^\star$ and $X^\star$ their respective values in the optimal situation.

**C.4 (1 pt)** Considering $S_{\rm b}\simeq S_{\rm c}$ and $S_{\rm t}\ll S_{\rm b}$, determine the expressions for $F_{\rm s}^\star$ and $X^\star$ as functions of $\rho$, $g$, $S_{\rm c}$ and $A$. Express the corresponding maximum energy $W^\star$, then calculate its numerical value with $A = 5\times10^2$ Pa.

We denote $W_{\rm pr}^\star$ the work of atmospheric pressure forces received by the system in the optimal situation during a period $\tau_1$.

**C.5 (1.7 pt)** Express $W_{\rm pr}^\star$, then calculate the ratio $W^\star/W_{\rm pr}^\star$. *It could be useful to represent the evolution of the system in a $(P,V)$ diagram, where $V$ is the system's volume.*

Credits: [1]: Bruno Vacaro; [2]: Victoria and Albert Museum, London.
