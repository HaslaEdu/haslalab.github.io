# IPhO 2025 — Theory Question T1 (Q1) [10 points]. Hydrogen and galaxies

*Text-only version of the official English statement (55th IPhO, France, 2025). Figures are described in words in "Figure description" blocks; numerical values quoted in those blocks were read off the official figures (approximate, as a careful reader of the printed figure would read them). Everything else follows the official wording. Answer-sheet boilerplate is omitted.*

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

# Hydrogen and galaxies (10 points)

This problem aims to study the peculiar physics of galaxies, such as their dynamics and structure. In particular, we explain how to measure the mass distribution of our galaxy from the inside. For this we will focus on hydrogen, its main constituent.

Throughout this problem we will only use $\hbar$, defined as $\hbar = h/2\pi$.

## Part A - Introduction

### Bohr model

We assume that the hydrogen atom consists of a non-relativistic electron, with mass $m_e$, orbiting a fixed proton. Throughout this part, we assume its motion is on a circular orbit.

**A.1 (0.2 pt)** Determine the electron's velocity $v$ in a circular orbit of radius $r$.

In the Bohr model, we assume the magnitude of the electron's angular momentum $L$ is quantized, $L = n\hbar$ where $n>0$ is an integer. We define $\alpha = \dfrac{e^2}{4\pi\varepsilon_0\hbar c} \approx 7.27\times10^{-3}$.

**A.2 (0.5 pt)** Show that the radius of each orbit is given by $r_n = n^2 r_1$, where $r_1$ is called the Bohr radius. Express $r_1$ in terms of $\alpha$, $m_e$, $c$ and $\hbar$ and calculate its numerical value with 3 digits. Express $v_1$, the velocity on the orbit of radius $r_1$, in terms of $\alpha$ and $c$.

**A.3 (0.5 pt)** Determine the electron's mechanical energy $E_n$ on an orbit of radius $r_n$ in terms of $e$, $\varepsilon_0$, $r_1$ and $n$. Determine $E_1$ in the ground state in terms of $\alpha$, $m_e$ and $c$. Compute its numerical value in eV.

### Hydrogen fine and hyperfine structures

The rare spontaneous inversion of the electron's spin causes a photon to be emitted on average once per 10 million years per hydrogen atom. This emission serves as a hydrogen tracer in the universe and is thus fundamental in astrophysics. We will study the transition responsible for this emission in two steps.

First, consider the interaction between the electron spin and the relative motion of the electron and the proton. Working in the electron's frame of reference, the proton orbits the electron at a distance $r_1$. This produces a magnetic field $\vec B_1$.

**A.4 (0.5 pt)** Determine the magnitude $B_1$ of $\vec B_1$ at the position of the electron in terms of $\mu_0$, $e$, $\alpha$, $c$ and $r_1$.

Second, the electron spin creates a magnetic moment $\vec{\mathcal M}_s$. Its magnitude is roughly $\mathcal M_s = \dfrac{e}{m_e}\hbar$. The *fine* (F) structure is related to the energy difference $\Delta E_{\rm F}$ between an electron with a magnetic moment $\vec{\mathcal M}_s$ parallel to $\vec B_1$ and that of an electron with $\vec{\mathcal M}_s$ anti-parallel to $\vec B_1$. Similarly, the *hyperfine* (HF) structure is related to the energy difference $\Delta E_{\rm HF}$, due to the interaction between parallel and anti-parallel magnetic moments of the electron and the proton. It is known to be approximately $\Delta E_{\rm HF} \simeq 3.72\,\dfrac{m_e}{m_p}\,\Delta E_{\rm F}$ where $m_p$ is the proton mass.

**A.5 (0.5 pt)** Express $\Delta E_{\rm F}$ as a function of $\alpha$ and $E_1$.
Express the wavelength $\lambda_{\rm HF}$ of a photon emitted during a transition between the two states of the hyperfine structure and give its numerical value with two digits.

## Part B - Rotation curves of galaxies

**Data**

- Kiloparsec: $1\ \mathrm{kpc} = 3.09\times10^{19}\ \mathrm{m}$
- Solar mass: $1\ \mathrm{M_\odot} = 1.99\times10^{30}\ \mathrm{kg}$

We consider a spherical galaxy centered around a fixed point $O$. At any point $P$, let $\rho=\rho(P)$ be the volumetric mass density and $\varphi=\varphi(P)$ the associated gravitational potential (i.e. potential energy per unit mass). Both $\rho$ and $\varphi$ depend only on $r = \left\|\overrightarrow{OP}\right\|$. The motion of a mass $m$ located at $P$, due to the field $\varphi$, is restricted to a plane containing $O$.

**B.1 (0.2 pt)** In the case of a circular orbit, determine the velocity $v_c$ of an object on a circular orbit passing through $P$ in terms of $r$ and $\dfrac{d\varphi}{dr}$.

Fig. 1(A) is a picture of the spiral galaxy NGC 6946 in the visible band (from the $0.8$ m Schulman Telescope at the Mount Lemmon Sky Center in Arizona). The little ellipses in Fig. 1(B) show experimental measurements of $v_c$ for this galaxy. The central region ($r<1$ kpc) is named the bulge. In this region, the mass distribution is roughly homogeneous. The red curve is a prediction for $v_c$ if the system were homogeneous in the bulge and keplerian ($\varphi(r) = -\beta/r$ with $\beta>0$) outside it, i.e. considering that the total mass of the galaxy is concentrated in the bulge.

> **Figure description (Fig. 1: NGC 6946 galaxy: Picture (A) and rotation curve (B)).**
> **(A)** A colour photograph of the face-on spiral galaxy NGC 6946 (bright yellowish core, bluish spiral arms, field stars). A double-headed scale arrow below the picture spanning the full width of the picture is labelled **18 kpc** (i.e. the visible galaxy fills a region about 18 kpc across, radius about 9 kpc).
> **(B)** Rotation curve: horizontal axis $r$ [kpc] from 0 to about 11.5 (ticks labelled 0, 5, 10); vertical axis $v_C$ [km/s] from 0 to 200 (labels 0, 50, 100, 150, 200; dashed grid lines at 50, 100, 150 km/s and at $r$ = 5, 10 kpc).
> *Black open ellipses (measurements, some with error bars):* about 100–115 km/s for $r\lesssim0.5$ kpc; a shallow dip around 95–105 km/s for $r\approx1$–2 kpc; then a steady rise: ≈125 km/s at 2.5 kpc, ≈135 km/s at 3 kpc, ≈148 km/s at 4 kpc, ≈158 km/s at 5 kpc, ≈165–170 km/s from 6 to 8 kpc; isolated points with error bars at $r\approx8.6$ kpc (≈172 km/s), 9.5 kpc (≈168 km/s), 10.3 kpc (≈166 km/s) and 11.3 kpc (≈166 km/s). The measured curve is thus flat at roughly 160–170 km/s beyond about 5 kpc.
> *Red curve (homogeneous bulge + keplerian model):* rises steeply from 0 at $r=0$ to a maximum of about 120 km/s at $r\approx0.6$ kpc, then decreases: ≈113 km/s at 0.8 kpc, ≈99 km/s at 1.0 kpc, ≈67 km/s at 1.5 kpc, ≈53 km/s at 2 kpc, ≈40 km/s at 3 kpc, ≈33 km/s at 4 kpc, ≈29 km/s at 5 kpc, ≈26 km/s at 6 kpc, ≈24 km/s at 7 kpc, ≈23 km/s at 8 kpc, ≈22 km/s at 9 kpc, ≈20–21 km/s at 10–11 kpc.

**B.2 (0.5 pt)** Deduce the mass $M_b$ of the bulge of NGC 6946 from the red rotation curve in Fig. 1(B), in solar mass units.

Comparing the keplerian model and the experimental data makes astronomers confident that part of the mass is invisible in the picture. They thus suppose that the galaxy's actual mass density is given by

$$\rho_m(r) = \frac{C_m}{r_m^2 + r^2} \tag{1}$$

where $C_m>0$ and $r_m>0$ are constants.

**B.3 (1.8 pt)** Show that the velocity profile $v_{c,m}(r)$, corresponding to the mass density in Eq. 1, can be written $v_{c,m}(r) = \sqrt{k_1 - \dfrac{k_2\cdot\arctan\left(\frac{r}{r_m}\right)}{r}}$. Express $k_1$ and $k_2$ in terms of $C_m$, $r_m$ and $G$.
(Hints: $\displaystyle\int_0^r \frac{x^2}{a^2+x^2}\,dx = r - a\arctan(r/a)$, and: $\arctan(x)\simeq x - x^3/3$ for $x\ll1$.)
Simplify $v_{c,m}(r)$ when $r\ll r_m$ and when $r\gg r_m$.
Show that if $r\gg r_m$, the mass $M_m(r)$ embedded in a sphere of radius $r$ with the mass density given by Eq. 1 simplifies and depends only on $C_m$ and $r$.
Estimate the mass of the galaxy NGC 6946 actually present in the picture in Fig. 1(A).

## Part C - Mass distribution in our galaxy

For a spiral galaxy, the model for Eq. 1 is modified and one usually considers the gravitational potential is given by $\varphi_G(r,z) = \varphi_0 \ln\left(\dfrac{r}{r_0}\right)\exp\left[-\left(\dfrac{z}{z_0}\right)^2\right]$, where $z$ is the distance to the galactic plane (defined by $z=0$), and $r<r_0$ is now the axial radius and $\varphi_0>0$ a constant to be determined. $r_0$ and $z_0$ are constant values.

**C.1 (0.5 pt)** Find the equation of motion on $z$ for the vertical motion of a point mass $m$ in such a potential, assuming $r$ is constant. Show that, if $r<r_0$, the galactic plane is a stable equilibrium state by giving the angular frequency $\omega_0$ of small oscillations around it.

From here on, we set $z=0$.

**C.2 (0.6 pt)** Identify the regime, either $r\gg r_m$ or $r\ll r_m$, in which the model of Eq. 1 recovers a potential of the form $\varphi_G(r,0)$ with a suitable definition of $\varphi_0$.
Under this condition $v_c(r)$ no longer depends on $r$. Express it in terms of $\varphi_0$.

Therefore, outside the bulge the velocity modulus $v_c$ does not depend on the distance to the galactic center. We will use this fact, as astronomers do, to measure the galaxy's mass distribution from the inside.

All galactic objects considered here for astronomical observations, such as stars or nebulae, are primarily composed of hydrogen. Outside the bulge, we assume that they rotate on circular orbits around the galactic center $C$. $S$ is the sun's position and $E$ that of a given galactic object emitting in the hydrogen spectrum. In the galactic plane, we consider a line of sight $SE$ corresponding to the orientation of an observation, on the unit vector $\hat u_v$ (see Fig. 2).

> **Figure description (Fig. 2: Geometry of the measurement).** View of the galactic plane. $C$ is the galactic centre (bottom left of the drawing). $S$ (top) lies on a black dotted circle centred on $C$ of radius $R_\odot$ (the dotted segment $SC$ is labelled $R_\odot$). A straight line of sight starts at $S$ and goes down and to the right, with unit vector $\hat u_v$ pointing away from $S$ (arrow at the far end, beyond $C$'s level). The angle at $S$ between $SC$ and the line of sight is $\ell$. The emitter $E$ lies on the line of sight, on a smaller red dotted circle centred on $C$ of radius $R<R_\odot$ (red dotted segment $CE$ labelled $R$); $E$ is the first (near) intersection of the line of sight with this circle. $T$ is the foot of the perpendicular dropped from $C$ onto the line of sight (right angle marked at $T$, so $CT\perp ST$); along the line, the order is $S$, $s$, $E$, $e$, $T$.
> Sun's velocity: the vector $\vec v_\odot$ is drawn from $S$ to a point $S_v$, perpendicular to $CS$ (right angle marked at $S$) and pointing to the right, i.e. towards the same side of $SC$ as the line of sight. $s$ is the foot of the perpendicular from $S_v$ onto the line of sight (right angle at $s$); the angle at $S_v$ between $S_vS$ and $S_vs$ is labelled $\alpha$.
> Emitter's velocity: the red vector $\vec v_E$ is drawn from $E$ to $E_v$, perpendicular to $CE$ (right angle marked at $E$) and also pointing to the right (same sense of rotation about $C$ as the sun). $e$ is the foot of the perpendicular from $E_v$ onto the line of sight (right angle at $e$); the angle at $E$ between the line of sight (direction $\hat u_v$) and $\vec v_E$ is labelled $\beta$.

Let $\ell$ be the galactic longitude, measuring the angle between $SC$ and the $SE$. The sun's velocity on its circular orbit of radius $R_\odot = 8.00$ kpc is denoted $\vec v_\odot$. A galactic object in $E$ orbits on another circle of radius $R$ at velocity $\vec v_E$. Using a Doppler effect on the previously studied 21 cm line, one can obtain the relative radial velocity $v_{rE/S}$ of the emitter $E$ with respect to the sun $S$: it is the projection of $\vec v_E - \vec v_\odot$ on the line of sight.

**C.3 (0.7 pt)** Determine $v_{rE/S}$ in terms of $\ell$, $R$, $R_\odot$ and $v_\odot$. Then, express $R$ in terms of $R_\odot$, $v_\odot$, $\ell$ and $v_{rE/S}$.

Using a radio telescope, we make observations in the plane of our galaxy toward a longitude $\ell = 30^\circ$. The frequency band used contains the 21 cm line, whose frequency is $f_0 = 1.42$ GHz. The results are reported in Fig. 3.

> **Figure description (Fig. 3: Electromagnetic signal as a function of the frequency shift, measured in the radio frequency band at $\ell = 30^\circ$ using EU-HOU RadioAstronomy).** Horizontal axis: $f-f_0$ [MHz] from $-0.1$ to $0.5$ (labels every 0.1 MHz, fine grid every 0.01 MHz). Vertical axis: Flux [arbitrary units] from 0 to 1200 (labels 0, 400, 800, 1200). A single red curve shows **three peaks**, whose maxima lie on grid points at $f-f_0 = 0.03$ MHz, $0.15$ MHz and $0.26$ MHz. Approximate flux values read on the curve:
>
> | $f-f_0$ (MHz) | −0.10 | −0.05 | −0.03 | 0.00 | 0.02 | **0.03** | 0.05 | 0.07 | 0.09 | 0.11 | 0.13 | 0.14 | **0.15** | 0.17 | 0.20 | 0.22 | 0.24 | 0.25 | **0.26** | 0.28 | 0.30 | 0.33 | 0.35 | 0.40 | 0.47 |
> |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
> | Flux | ≈10 | ≈55 | ≈260 | ≈430 | ≈600 | **≈660 (max)** | ≈550 | ≈300 | ≈200 (min) | ≈300 | ≈780 | ≈960 | **≈1100 (max)** | ≈930 | ≈760 | ≈680 | ≈560 (min) | ≈680 | **≈770 (max)** | ≈570 | ≈240 | ≈150 | ≈80 | ≈25 | ≈0 |

**C.4 (0.6 pt)** In our galaxy, $v_\odot = 220\ \mathrm{km\cdot s^{-1}}$. Determine the values of the relative radial velocity (with 3 significant digits) and the distance from the galactic center (with 2 significant digits) of the 3 sources observed in Fig. 3. Distances should be expressed as multiples of $R_\odot$.

**C.5 (0.6 pt)** `[GRAPH/FIGURE-DEPENDENT]` On the top view of our galaxy (in the answer box), indicate the positions of the sources observed in Fig. 3.
What could be deduced from repeated measurements changing $\ell$?

> **Figure description (answer box of C.5).** A polar grid (top view of the galactic plane) centred on the galactic centre $C$, with radial dashed lines every $15^\circ$ and dashed concentric circles every $R_\odot/8$ out to about $1.3R_\odot$; two concentric circles are drawn solid, at radii $R_\odot/2$ and $R_\odot$. The sun $S$ is marked on the solid circle of radius $R_\odot$ (upper right of $C$). Two red dash-dotted lines pass through $C$: the line $CS$ and the line through $C$ perpendicular to $CS$.
> *(Text-only version: describe in words/coordinates how the line of sight and the three sources are placed on this map, then answer the question.)*

## Part D - Tully-Fisher relation and MOND theory

The flat external velocity curve of NGC 6946 in Fig. 1 is a common property of spiral galaxies, as can be seen in Fig. 4 (left). Plotting the external constant velocity value $v_{c,\infty}$ as a function of the measured total mass $M_{\rm tot}$ of each galaxy gives an interesting correlation called the Tully-Fischer relation, see Fig. 4 (right).

> **Figure description (Fig. 4. Left: Rotation curves for typical spiral galaxies - Right: $\log_{10}(M_{\rm tot})$ as a function of $\log_{10}(v_{c,\infty})$ on linear scales. Colored dots correspond to different galaxies and different surveys. The green line is the Tully-Fischer relation which is in very good agreement with the best fit line of the data (in black).)**
> *Left:* six small panels of rotation curves $V$ (km/s) versus $R$ (kpc) for NGC 3621, NGC 5055, NGC 2903, NGC 3521, NGC 7321 and NGC 2841 (data points with a blue model curve). In every panel the velocity rises quickly near the centre and then stays essentially constant out to the last measured radius (20–50 kpc); this constant outer value is labelled $v_{c,\infty}$ (arrow on the first panel).
> *Right:* scatter plot, horizontal axis $\log_{10}(v_{c,\infty}/1\ \mathrm{km/s})$ from 1.5 to 2.9 (labels 1.6, 1.8, …, 2.8), vertical axis $\log_{10}(M_{\rm tot}/M_\odot)$ from about 7.8 to 12.7 (labels 8, 9, 10, 11, 12). Red dots run along a straight band from about (1.58, 8.1) to (2.45, 11.5); orange dots cluster at $\log_{10}v_{c,\infty}\approx2.05$–2.65, $\log_{10}M_{\rm tot}\approx10.9$–11.5; blue dots at $\log_{10}v_{c,\infty}\approx2.4$–2.75, $\log_{10}M_{\rm tot}\approx11.1$–11.8. The green straight line (Tully-Fischer relation, practically superposed on the black best-fit line) passes approximately through the points $(1.5,\ 7.8)$, $(1.6,\ 8.2)$, $(1.8,\ 8.9)$, $(2.0,\ 9.6)$, $(2.2,\ 10.4)$, $(2.4,\ 11.1)$, $(2.6,\ 11.9)$, $(2.8,\ 12.6)$.

**D.1 (0.4 pt)** Assuming that the radius $R$ of a galaxy doesn't depend on its mass, show that the model of Eq. 1 (part B) gives a relation of the form $M_{\rm tot} = \eta\, v_{c,\infty}^{\gamma}$ where $\gamma$ and $\eta$ should be specified.
Compare this expression to the Tully-Fischer relation by computing $\gamma_{TF}$.

In the extremely low acceleration regime, of the order of $a_0 = 10^{-10}\ \mathrm{m\cdot s^{-2}}$, the MOdified Newtonian Dynamics (MOND) theory suggests that one can modify Newton's second law using $\vec F = m\,\mu\!\left(\dfrac{a}{a_0}\right)\vec a$ where $a = \|\vec a\|$ is the modulus of the acceleration and the $\mu$ function is defined by $\mu(x) = \dfrac{x}{1+x}$.

**D.2 (0.2 pt)** Using data for NGC 6946 in Fig. 1, estimate, within Newton's theory, the modulus of the acceleration $a_m$ of a mass in the outer regions of NGC 6946.

**D.3 (0.8 pt)** Let $m$ be a mass on a circular orbit of radius $r$ with velocity $v_{c,\infty}$ in the gravity field of a fixed mass $M$.
Within the MOND theory, with $a\ll a_0$, determine the Tully-Fischer exponent.
Using data for NGC 6946 and/or Tully-Fischer law, calculate $a_0$ to show that MOND operates in the correct regime.

**D.4 (0.9 pt)** Considering relevant cases, determine $v_c(r)$ for all values of $r$ in the MOND theory in the case of a gravitational field due to a homogeneously distributed mass $M$ with radius $R_b$.
