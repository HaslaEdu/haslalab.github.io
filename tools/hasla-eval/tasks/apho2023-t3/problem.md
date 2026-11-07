# APhO 2023 — Theoretical Problem 3: Cavitation [10.0 points]

*Text-only version of the official English statement (23rd APhO, Mongolia 2023, "English (Official)"). Figures are described in words in "Figure description" blocks; everything else follows the official wording (including its spelling).*

## Introduction

Cavitation is the phenomenon of vapour bubbles or ``cavities'' occurring in a liquid medium due to *drop in pressure*. This is in contrast to boiling, where vapour bubbles are created due to *rise in temperature*. Since the vapour bubbles collapse and generate shock waves as well as supersonic jets when the dropped pressure is restored, cavitation is a constant source of damage and even of catastrophe in hydraulic machines, ships, and more generally in any device involving liquid flow. On the other hand, it has found many positive applications, for example in chemical industry, cleaning, and in treatment of kidney stones.

> **Figure 1 description.** "(a) Cavitating propeller (b) Cavitation damage (Source: Wikimedia Commons)". Two photographs: (a) a ship propeller in a water tunnel with white helical vapour trails streaming from its blade tips; (b) a metal impeller whose blade edges are pitted and eroded. Illustrative only.

It is understood that cavitation generally grow out of microscopic bubbles, called *nuclei*, that preexisted in the liquid. These micro-bubbles are a few microns in size and contain both vapour and non-condensable gas (the latter is just air when ordinary water is under consideration). If the pressure in the liquid becomes sufficiently low, the nuclei grow into a macroscopic size, initiating cavitation. Liquid purified of such nuclei can even withstand negative pressure without cavitating. One usually compares this with solid under tension, which does not rupture easily if there are no preexisting pockets or cracks in it.

In this problem, we will be concerned with various idealized scenarios related to cavitation. As is often the case, we can glean some nontrivial information from simple dimensional analysis. However, we will need differential equations embodying fundamental laws such as Newton's second law of motion and Fick's law of diffusion, if we want to conduct a more precise study.

One of the first things we want to know is the so called *critical (or threshold) pressure*, that is the minimum value of the water pressure so that the nuclei remain microscopic without growing into macroscopic bubbles. The critical pressure is roughly equal to the vapour pressure at the given temperature, but the exact value is slightly lower due to surface tension and the air content of the nucleus.

> **Figure 2 description.** "(a) Cavitation (down arrow) and boiling (right arrow) on a phase diagram (b) Typical bubble (see Table 1 for notations)".
> (a) Phase diagram of water with pressure $p$ on the vertical axis and temperature $T$ on the horizontal axis (no numbers). A blue vapour-pressure (liquid–vapour coexistence) curve starts near the origin and rises with increasing slope to a black dot (critical point) at the upper right; a black dot on it near the lower left is the triple point, from which a steep, almost vertical blue melting curve goes up (leaning slightly to lower $T$ as $p$ increases). An open circle marks a state in the liquid region (above the vapour-pressure curve, to the right of the melting curve). From it a green arrow points straight down (pressure lowered at constant $T$) and crosses the vapour-pressure curve: cavitation. A red arrow points horizontally to the right (temperature raised at constant $p$) and crosses the same curve: boiling.
> (b) A spherical bubble of radius $R$ (arrow from its centre to its wall) in water; the inside is labelled $p_v+q$ and the surrounding water is labelled $p_\infty$.

If the external pressure suddenly drops below the critical pressure of a nucleus, then the nucleus starts expanding and the expansion rate quickly reaches a stable value. In practice, after the bubble becomes macroscopic in size, the pressure is typically restored to its original value, and the bubble starts collapsing. We will model this situation by considering a macroscopic bubble in equilibrium, whose external pressure is then suddenly risen. The collapsing bubble will rebound after reaching a minimum size if the bubble had air in it. On the other hand, a pure vapour bubble would completely dissolve, with the shrinkage rate growing unboundedly as the radius of the bubble reaches zero. In reality, towards the end of the collapse, the bubble would lose its spherical shape, and the compressibility of water would become important. However, unless a particular question explicitly asserts otherwise, we will neglect those effects here.

Another interesting question is what happens when sound wave is transmitted through water containing bubbles. It turns out that not only the bubbles pulsate following the pressure oscillations, but also the sound wave induces translational motions of the bubbles. These effects can be used to manipulate bubbles with the help of acoustic waves. For example, in acoustic cavitation, high intensity ultrasound is employed to generate cavitation or cause collapse of bubbles.

Finally, there is a sort of paradox regarding the existence of nuclei in the first place. The theory predicts that unless water is saturated with dissolved air, diffusion of air from any nucleus into water through the gas-water interface must induce a complete dissolution of the nucleus in a matter of seconds. However, in reality, micron sized nuclei exist in water and it is in fact extremely difficult to get rid of them. We will consider one of a few potential resolutions of this paradox, namely the suggestion that small crevices in solid walls or in solid particles carried by water are responsible for acting as micro-pockets of air and vapour.

## Potentially useful information

### Vapour pressure

Let us say we have a closed jar containing water and air. If the air is too dry, then its humidity will increase due to evaporation of water. If the air is too wet, then its humidity will decrease due to condensation. It turns out that in equilibrium, the partial pressure $p_v = p_v(T)$ of vapour in air is a function of temperature.

> **Figure 3 description.** "(a) Closed jar containing air and water in equilibrium (b) Diffusion flux through the surface S is proportional to the concentration gradient across S".
> (a) A closed rectangular jar: the upper part is gas, labelled $p_v+q$; the lower part is water, labelled $u = Hq$.
> (b) A flat surface element (drawn as a parallelogram) labelled $S$, pierced perpendicularly by a coordinate axis labelled $x$ (arrow pointing to the right).

Now if a bubble changes its volume in an instant, then the humidity inside the bubble will lose its equilibrium with the surrounding water, and a new equilibrium must be reached either by condensation or evaporation. In reality this process is so rapid that we can justifiably assume that equilibrium is maintained at all times. Moreover, the heat lost or gained by the surrounding water during this process is negligible, so that the temperature remains constant. To conclude, we assume that the partial pressure of vapour contained in a bubble remains equal to $p_v$ at all times.

### Henry's law

While the concept of vapour pressure gives us a good handle on the vapour content of a bubble, Henry law offers at least a partial handle on the air content. Thinking of a closed jar containing water and air, it says that in equilibrium, the concentration of dissolved air in water is proportional to the partial pressure of air above the water:

$$u = Hq$$

where, $u$ is the concentration of air in water, $H$ is the so called Henry's constant, and $q$ is the partial pressure of air adjacent to water. As before, we will assume that equilibrium of air content in the sense of Henry's law is maintained at least in the immediate vicinity of the bubble at all times, and that this maintenance does not cause any temperature change.

### Fick's law

To complement Henry's law, we need to know how dissolved air in water moves from places with high concentration to places with low concentration. This is where Fick's law enters, which states that the diffusion flux across an area element $S$ is proportional to how fast the concentration changes along the direction perpendicular to $S$, see Figure 3:

$$J = \kappa\frac{\partial u}{\partial x}$$

Here $J$ is the diffusion flux, that is the amount of air moving across the surface per unit area per unit time, $\kappa$ is the diffusivity coefficient, and we have assumed that the $x$ coordinate axis is perpendicular to $S$. When $u$ is a function of $x$ and possibly other variables, the notation $\frac{\partial u}{\partial x}$ means that we have taken the derivative of $u$ with respect to the variable $x$, while holding all other variables constant.

### Diffusion equation

If you need to find a function $w = w(x,t)$ in the first quadrant $Q = \{(x,t) : x > 0,\ t > 0\}$ satisfying $\frac{\partial w}{\partial t} = \frac{\partial^2 w}{\partial x^2}$ in $Q$, and
$$\begin{cases} w(x,0) = f(x) & \text{for } x > 0,\\ w(0,t) = 0 & \text{for } t > 0,\end{cases}$$
then the solution is given by
$$w(x,t) = \frac{1}{\sqrt{4\pi t}}\int_0^\infty\left(e^{-(x-y)^2/(4t)} - e^{-(x+y)^2/(4t)}\right)f(y)\,dy.$$

### Gaussian type integrals

The following integrals may come in handy.
$$\int_0^\infty e^{-bx^2}dx = \frac{\sqrt\pi}{2\sqrt b},\qquad \int_0^\infty x^2e^{-bx^2}dx = \frac{\sqrt\pi}{4b\sqrt b}\qquad (b > 0).$$

### Notations and typical values of parameters.

In Table 1, we list the notations used in the statement of the problem, and the typical values of some important constants.

**Table 1**

| symbol | assigned meaning | typical value |
|---|---|---|
| $\rho$ | water density | $997$ kg/m³ |
| $p_\infty$ | water pressure far from a bubble | $101$ kPa |
| $p_v$ | vapour pressure | $2340$ Pa |
| $\sigma$ | surface tension | $72.8\cdot10^{-3}$ N/m |
| $R$ | bubble radius | |
| $R_0$ | initial radius of a bubble | $10^{-5}$ m |
| $\delta$ | density of air | $1.29$ kg/m³ |
| $q$ | partial pressure of air in a bubble | |
| $q_0$ | initial value of $q$ | |
| $\gamma$ | adiabatic exponent of air | $1.4$ |
| $u$ | concentration of dissolved air in water | |
| $\kappa$ | diffusivity coefficient for air in water | $2\cdot10^{-9}$ m²/s |
| $H$ | Henry's constant for air in water | $0.24\cdot10^{-6}$ s²/m² |
| $t$ | time | |
| $f_0$ | natural/resonant frequency | |

### Assumptions

*Unless otherwise specified*, throughout this problem we assume the following.

- Water is incompressible, inviscid, and homogeneous.
- Water fills the entire space.
- Pressure variation due to gravity is negligible.
- No spatial or temporal variation in temperature.
- There is a single bubble.
- The bubble remains spherical and without translatory motion.
- No migration of air between the bubble cavity and the surrounding water.
- Air is an ideal gas.

## Part A: Preliminary analysis [1.5 points]

These are warm-up questions to get the initial feel of the phenomenon.

**A.1 [0.5 pt]** By performing a simple dimensional analysis, estimate the collapse time $T$ of a pure vapour bubble, in terms of bubble's initial radius $R_0$, water density $\rho$, water pressure $p_\infty$, and the vapour pressure $p_v$. Evaluate the formula with the numerical constant implicit in the formula equal to 1, when $R_0 = 1$ mm and the quantities $\rho$, $p_\infty$, and $p_v$ take their typical values from previous Notation Table . Assume no surface tension: $\sigma = 0$.

**A.2 [1.0 pt]** Suppose that a nucleus consisting of air and vapour, with radius $R_0 = 10^{-5}$ m, is in equilibrium when the external pressure $p_\infty = 101$ kPa. Find the partial pressure $q_0$ of air in the bubble. Now suppose that the external pressure $p_\infty$ was gradually decreased, and that the air inside the bubble follows an isothermal process. Find the critical pressure $p_c$, defined by the condition that if $p_\infty < p_c$ the bubble size grows without bound. The quantities $p_v$ and $\sigma$ take their typical values from the above Notation Table.

## Part B: Main dynamics [6.0 points]

Now we will study the detailed dynamics of a spherical bubble consisting of a mixture of air and vapour. Please assume that there is no air migration through the bubble wall, and hence that the whole dynamics is governed by pressure only. Note however that as we have mentioned, there will be evaporation and condensation of water vapour at the bubble wall, that maintains the vapour pressure $p_v$ within the bubble.

**B.1 [1.5 pt]** Suppose that a single spherical bubble resides within water that fills space uniformly, and that the bubble may evolve in size without distorting its spherical shape, due to changes, e.g., in the external pressure $p_\infty$ . Derive an equation that relates the bubble radius $R(t)$ and its time derivatives $R'(t)$ and $R''(t)$ , surface tension $\sigma$ , water density $\rho$ , the pressure far from the bubble $p_\infty$ , and the pressure inside the bubble $p$. Then split the pressure $p$ into two terms, by assuming that the bubble has both vapour (with partial pressure $p_v$) and air in it, and that the air follows an adiabatic process with exponent $\gamma$. To give a reference point, the partial air pressure must be $q_0$ when the bubble size equals $R_0$. Assume that evaporation, condensation, or transfer of air between the bubble cavity and the surrounding water has no effect on the water volume.

**B.2 [1.0 pt]** A water tank under the external pressure $p_\infty^- = 101$ kPa, containing a nucleus of radius $R_0 = 10^{-5}$ m initially in equilibrium, was exposed to vacuum, so that the system suddenly has $p_\infty = 0$ . Estimate the terminal (asymptotic) value of the growth speed $R'$ , as well as the time it reaches this terminal value.

**B.3 [1.0 pt]** A water tank under the external pressure $p_\infty^- = 1.600$ kPa, containing a gas bubble of radius $R_0 = 10^{-5}$ m initially in equilibrium, was suddenly exposed to the atmospheric pressure $p_\infty = 101$ kPa . Estimate the minimum radius of the bubble before it rebounds.

**B.4 [0.5 pt]** If there is no gas other than water vapour present in a bubble, the bubble completely collapses in finite time. Determine the characteristic exponent $\alpha$ in
$$R(t) \sim (T-t)^\alpha,$$
where $T$ is the collapse time.

**B.5 [1.0 pt]** Based on the equation derived in B3, find the natural frequency of the spherical oscillation of a bubble of radius $R_0 = 0.1$ mm.

**B.6 [1.0 pt]** Suppose that the bubble described in the previous part is subjected to a standing sound wave along the $x$-axis, whose pressure field is given by
$$p(x,t) = p_0 + A\sin\left(\frac{2\pi f}{c}(x+a)\right)\sin(2\pi ft),$$
where $f$ is the frequency, and $c$ is the speed of sound. The parameters $p_0$, $A$ and $a$ are constants, whose meanings may readily be deduced from the equation. Find the average force exerted upon the bubble. The bubble is situated at the origin of the $xyz$ coordinate system, and its size is much smaller than the wavelength of the sound.

## Part C: Dissolution of nuclei through diffusion [2.5 points]

In this final section, complementary to Part B, we focus on the effect of diffusion across the bubble wall.

**C.1 [2.0 pt]** Suppose that a nucleus consisting of air and vapour, with radius $R_0 = 10^{-5}$ m , is placed in water-air solution, in which the dissolved air is in equilibrium with the atmospheric pressure above the water. The partial pressure of air in the bubble is $q = 1.70\cdot10^5$ Pa, and the vapour pressure can be neglected. Estimate the time required for the bubble to be completely resorbed into water.
The quantities $p_\infty, \kappa, \delta$ and $\sigma$ take their typical values from Table 1. Assume that the region surrounding the bubble in which air diffusion takes place immediately gets much larger than the bubble itself.

**C.2 [0.5 pt]** Consider a conical crevice in the wall of a water container, with an aperture angle $\alpha$, see the following Figure. A small amount of air and vapour reside within the cone. Write down the condition of mechanical and diffusive equilibrium. Determine when the pocket of air stays in the crevice without disappearing. The contact angle of water on the surface is $\theta$.

> **Figure description ("Conical Crevice").** Cross-section through the axis of the cone. The two thick dark lines are the solid walls of the crevice; they meet at the apex on the left and open towards the right (towards the water container). The angle between the two walls at the apex is marked $\alpha$ (the full aperture angle). The region next to the apex (light grey) is the gas pocket (air and vapour); the region further right, towards the opening (darker grey), is water. The gas–water interface (meniscus) is a circular arc spanning from the upper wall to the lower wall; it bulges towards the apex, i.e. it is convex towards the gas and its centre of curvature lies on the water side. At the lower contact point (marked with a dot) a short straight line is drawn tangent to the meniscus, pointing up-left into the gas, and an arc marks the contact angle $\theta$, measured inside the water between the wall (the part of the wall running from the contact point towards the opening) and that tangent; in the drawing $\theta$ is obtuse (roughly $150^\circ$–$160^\circ$) and $\alpha$ is roughly $40^\circ$.
