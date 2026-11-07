# IPhO 2026 — Theoretical Question T2 [10 pts]. Cooking with sunlight?

*Text-only version of the official English statement (56th IPhO, Bucaramanga, Colombia, July 8, 2026). Figures are described in words in "Figure description" blocks; everything else follows the official wording.*

## Physical constants (from the official General Instructions)

Throughout the exam, always use the values of physical constants indicated here, unless otherwise noted. When performing numerical calculations, always indicate the units of the used quantities.

| Constant | Notation | Value | Units |
|---|---|---|---|
| Speed of light in vacuum | $c$ | $2.99792458\times10^{8}$ | $\mathrm{m\cdot s^{-1}}$ |
| Planck constant | $h$ | $4.135667696\ldots\times10^{-15}$ | $\mathrm{eV\cdot s}$ |
| Reduced Planck constant | $\hbar = h/2\pi$ | $6.582119569\ldots\times10^{-16}$ | $\mathrm{eV\cdot s}$ |
| Avogadro number | $N_A$ | $6.02214076\times10^{23}$ | $\mathrm{mol^{-1}}$ |
| Boltzmann constant | $k_B$ | $8.617333262\times10^{-5}$ | $\mathrm{eV\cdot K^{-1}}$ |
| Ideal gas constant | $R$ | $8.31446261815324$ | $\mathrm{kg\cdot m^2\cdot s^{-2}\cdot mol^{-1}\cdot K^{-1}}$ |
| Elementary charge | $e$ | $1.602176634\times10^{-19}$ | $\mathrm{A\cdot s}$ |
| Universal gravitational constant | $G$ | $6.67430(15)\times10^{-11}$ | $\mathrm{m^3\cdot kg^{-1}\cdot s^{-2}}$ |
| Stefan–Boltzmann constant | $\sigma$ | $5.670374419\times10^{-8}$ | $\mathrm{kg\cdot s^{-3}\cdot K^{-4}}$ |
| Vacuum permeability | $\mu_0$ | $1.25663706127(20)\times10^{-6}$ | $\mathrm{kg\cdot m\cdot A^{-2}\cdot s^{-2}}$ |
| Vacuum permittivity | $\varepsilon_0$ | $8.8541878188(14)\times10^{-12}$ | $\mathrm{A^2\cdot s^4\cdot kg^{-1}\cdot m^{-3}}$ |
| Mass of the electron | $m_e$ | $5.1099895069(16)\times10^{5}$ | $\mathrm{eV}/c^2$ |
| Mass of the proton | $m_p$ | $9.3827208943(29)\times10^{8}$ | $\mathrm{eV}/c^2$ |
| Atomic mass units | amu | $9.3149410372(29)\times10^{8}$ | $\mathrm{eV}/c^2$ |

---

The redistribution of luminous flux into regions of high and low intensity due to reflection or refraction can lead to the formation of *caustics:* curves formed by the intersection of infinitesimally close light rays. As an example, Figure 2a shows the caustic formed by rays incident paraxially on a half-cylindrical mirror. Figure 2b shows a photograph of the caustic formed by the reflection of light on the bottom part of a coffee cup. The brightest and central point of the caustic is called the *cusp*; at this point, the light intensity is maximal.

> **Figure description (Fig. 2a).** A semicircular mirror (arc opening downward) illuminated from below by many parallel vertical rays. The reflected rays form a bright envelope curve inside the semicircle: two symmetric arches that start at the two ends of the semicircle, rise toward the mirror, and meet at a sharp downward-pointing cusp on the symmetry axis. (Illustration only.)
>
> **Figure description (Fig. 2b).** Photograph, seen from above, of a coffee cup with liquid; a bright caustic curve with a cusp is visible on the liquid surface. (Illustration only.)

Caustics have a variety of applications in science, ranging from high-precision optics and quantum optics to astrophysics. In this question, you will study the caustic formation by light reflection on a half-cylinder mirror of radius $R$, as shown in figure 2c. You will also investigate other aspects of this mirror, such as its application in *solar cookers*.

Throughout the problem, assume that the incident rays come from a distant external light source and are parallel to the mirror's optical axis. By symmetry, it is sufficient to study reflection in one plane. Figure 2d shows such a plane, the mirror, and the coordinate system used throughout the problem.

> **Figure description (Fig. 2c).** Perspective drawing of a half-cylinder (half-pipe) mirror whose inner, reflecting surface has diameter $2R$ (radius $R$). The dashed optical axis lies in the symmetry plane. Light rays (orange arrows) enter the half-cylinder parallel to the optical axis, reflect on the inner surface (sometimes more than once) and leave.
>
> **Figure description (Fig. 2d) — coordinate system used throughout.** Cross-section perpendicular to the cylinder axis. The $x$ axis is horizontal (pointing right) and passes through the two ends of the mirror at $x=-R$ and $x=R$; the origin $O$ is the centre of the circle (on the cylinder axis). The $y$ axis points up and is the optical (symmetry) axis. The mirror is the upper semicircle $x^2+y^2=R^2$, $y\ge 0$, reflecting on its inner (concave) side. Incident rays travel vertically upward (in the $+y$ direction), coming from below the $x$ axis; a ray is labelled by its $x$-coordinate (its distance from the optical axis), with $-R<x<R$.

## T2-A [1.5 pts]. Multiple reflections

Figure 2e shows the relationship between the $x$-coordinate of an incident ray and the number $N$ of reflections it undergoes, up to $N=3$. As $x$ varies over the interval $(-R,R)$, the variable $N$ varies over all natural numbers greater than or equal to 1. The maximum distance from the optical axis that allows an incident ray to be reflected by the mirror at most $N$ times is denoted $x_N$.

> **Figure description (Fig. 2e).** Step-function graph of $N$ (vertical axis) versus $x$ (horizontal axis), symmetric about $x=0$, with marks $-x_3<-x_2<-x_1<0<x_1<x_2<x_3$ on the $x$ axis. $N=1$ on $[-x_1, x_1]$ (closed dots at both ends); $N=2$ on $x_1<|x|\le x_2$ (open dot at $\pm x_1$, closed dot at $\pm x_2$); $N=3$ on $x_2<|x|\le x_3$ (open dot at $\pm x_2$, closed dot at $\pm x_3$).

**T2-A1 [1.5 pts].** Find the general expression for $x_N$ in the infinite sequence $x_1, x_2, x_3, \ldots$ that limits the coordinates of the rays with at most $N$ reflections. Express your answer in terms of $R$ and $N$.

## T2-B [4.0 pts]. Solar Cooker

Consider a system consisting of a half-hollow-cylinder mirror and a cylindrical container. The cylinder is fully absorbing: any ray of light hitting it will be absorbed. The mirror radius is $R$. The container radius $a$. The axes of the mirror and the container are parallel. The center of the container is $R/2$ from the mirror on the system's symmetry plane, as shown in figure 2f. The mirror harnesses solar radiation to heat food inside the container. Assume that the sunlight is of constant and uniform intensity (power per unit area), and that the light rays are parallel to the optical axis of the mirror. Furthermore, assume that $a$ is such that any ray that is absorbed by the cylinder reflects from the mirror at most once. Let $\theta_{\max}$ be the maximum angle of incidence on the mirror (measured with respect to the normal drawn at the point of incidence) of any reflected ray striking the container.

> **Figure description (Fig. 2f).** Perspective drawing of a trough-shaped half-cylinder mirror of width $2R$ (opening upward, toward the sun), standing on legs, with a long cylindrical container of radius $a$ lying inside it, parallel to the mirror's axis. The container's axis lies in the symmetry plane, and the arrow labelled $R/2$ goes from the container's axis straight to the bottom of the mirror. Since the mirror radius is $R$, the container's axis is therefore halfway between the mirror's axis and the mirror's lowest point. In the coordinates of Fig. 2d (mirror drawn opening downward, light travelling in $+y$) the container's axis is at $(0, R/2)$.

**T2-B1 [2.0 pts].** The container radius is $a = \alpha\sin(\theta_{max}) + \beta\sin(2\theta_{max})$. Write $\alpha$ and $\beta$ in terms of $R$.

If you do not find $\alpha$ and $\beta$, use the expression given for the rest of the problem.

**T2-B2 [1.5 pts].** Let $P_0$ be the power that would be received by the cyllinder if the mirror was not present. Write $P/P_0$, the ratio of the actual received power $P$ to $P_0$, in terms of $\theta_{\max}$.

**T2-B3 [0.5 pts].** If $R = 1.0$ m, write the value of $a$ such that $P = 5P_0$. Give your answer in cm.

## T2-C [4.5 pts]. Caustics and Cusp

**T2-C1 [0.5 pts].** Consider a ray $A$ that strikes the mirror at an angle $\theta$, as shown in Figure 2g. Upon reflection, the equation corresponding to this ray in the coordinate system defined in Figure 2g. is $y = m_A x + b_A$. Write $m_A$ and $b_A$ in terms of $\theta$ and $R$

Hint: the expected form of $m_A = K_1\cot(K_2\theta)$ and $b_A = R\dfrac{K_3}{\cos(K_4\theta)}$, with $K_i$ numerical constants.

> **Figure description (Fig. 2g).** Same coordinate system as Fig. 2d (mirror = upper semicircle of radius $R$ centred at the origin, ends at $x=\pm R$). Ray $A$ travels vertically upward at some $x>0$ and hits the mirror at a point $P$ in the first quadrant. A dashed line joins the origin to $P$ (the radius, i.e. the normal at $P$); $\theta$ is the angle at $P$ between the incident vertical ray and this radius (the angle of incidence), so $P = (R\sin\theta, R\cos\theta)$. The reflected ray leaves $P$ going down and to the left, crosses the positive $y$ axis, and continues down-left past the $x$ axis near $x=-R$; this reflected line is labelled $y = m_A x + b_A$.

**T2-C2 [2.0 pts].** Now consider a ray $B$, parallel to $A$, that strikes the surface at an angle $\theta + \Delta\theta$, with $\Delta\theta \ll \theta$. Upon reflection, the equation corresponding to this ray is $y = m_B x + b_B$. Write $m_B$ and $b_B$ in terms of $\theta$, $\Delta\theta$, and $R$, approximating to first order in $\Delta\theta$.

**T2-C3 [1.0 pts].** Find the coordinates of the point of intersection $(X_c, Y_c)$ between the reflected rays of $A$ and $B$. Write your answer in terms of $R$ and $\theta$.

**T2-C4 [1.0 pts].** For $\theta \ll 1$, we have $Y_c = v|X_c|^{p/q} + u$. Write $v$ and $u$ in terms of $R$ and find the values of the integers $p$ and $q$ (equivalently, give the rational number $p/q$).
