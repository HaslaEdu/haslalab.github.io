# IPhO 2026 T1 — Three problems: official answers and marking scheme

**Task total: 10.0 points** (A1 3.0 + B1 1.0 + B2 2.5 + C1 2.5 + C2 1.0).

Sources: official marking scheme "Problem T1 — 10 Points total" (`IPhO_2026_M1.pdf`) for the step points; official solution "SOLUTION T1 [10 pts]. Three problems" (`IPhO_2026_S1.pdf`) for the final answers. Step descriptions are copied from the scheme (spelling kept). Where the scheme lists alternative solutions (SOLN1, SOLN2, ...), a student is marked along **one** of them (the one that gives the higher mark); points from different alternatives are not added.

---

## T1-A1 [3.0 pts] — Hydrostatic gate

**Official final answer:**
$$a = \frac{\rho_0}{\sqrt2(\rho-\rho_0)}\,\Delta h \;\xrightarrow{\ \rho = 3\rho_0\ }\; a = \frac{\Delta h}{2\sqrt2} = 0.50\ \text{m}$$

Official reasoning (summary): the effective area of the opening is $a\cdot(a/\sqrt2)$; the net horizontal force of the water is $\Delta F = \frac{a^2}{\sqrt2}\rho_0 g\Delta h$. Other forces: the block's weight $\rho g\,a^3$, the buoyant force $\rho_0 g\,a^3$, and the hinge force (no torque). At the critical $\Delta h$ the bottom edge of the opening exerts zero force on the block. Both arms are $a/(2\sqrt2)$ from $O$ (horizontal for the pressure force, vertical-line offset for the effective weight):
$$\frac{a^2}{\sqrt2}\rho_0 g\Delta h\left(\frac{a}{2\sqrt2}\right) = (\rho-\rho_0)a^3 g\left(\frac{a}{2\sqrt2}\right).$$

| Step (SOLN1) | Points |
|---|---|
| Forces correctly: Weight | 0.2 |
| Forces correctly: Buoyancy | 0.2 |
| Forces correctly: Pressure difference | 0.2 |
| Pressure force: P times area | 0.4 |
| Torques applied correctly (wrt to O and correct arms) | 0.6 |
| Understands critical vanishing condition | 0.5 |
| Correctly evaluates height (see note) | 0.7 |
| Units are used correctly | 0.2 |
| **Note:** if the height (value of $a$) is wrong numerically by a small algebra mistake only, award 0.3 instead of the 0.7 | (0.3) |

---

## T1-B1 [1.0 pts] — maximum separation, $\mu = 4$

**Official final answer:** $r_{\max} = \dfrac{1600}{9}\,a_0 \approx 177.8\,a_0$

Official reasoning (summary): $m v_0 (50a_0) = \mu\hbar$, $v_0 = \mu\hbar/(50 m a_0)$; total energy $E = \frac{ke^2}{a_0}\left(\frac{\mu^2}{50^2}-\frac1{100}\right)$, so for $\mu=4$, $E = -\frac{9ke^2}{2500a_0}$. At turning points $\vec v\perp\vec r$, $L = 2\mu\hbar = 8\hbar$, $E = 2\frac{L^2}{2mr^2}-\frac{ke^2}{r}$ (as written in the official solution), giving $\frac{9}{2500}r^2 - a_0 r + 64a_0^2 = 0$, $r = \frac{1250}{9}a_0\left(1\pm\frac{7}{25}\right)$; the plus sign gives $r_{\max}$. (Equivalent: semi-major axis $x = \frac{1250}{9}a_0$, $r_2 = 2x - 100a_0 = \frac{1600}{9}a_0$; or $\ell = 128a_0$, $\varepsilon = 7/25$, $r_{\max} = \ell/(1-\varepsilon)$.)

| Step | SOLN1 | SOLN2 | SOLN3 |
|---|---|---|---|
| Writes correct energy equation and calculates it | 0.3 | 0.3 | 0.3 |
| Writes condition for critical point correctly (SOLN1) / Notices that one is at one of the turning points (SOLN2, SOLN3) | 0.3 | 0.15 | 0.15 |
| Computes $a$ (in the hint equation we give them) (SOLN2) / Computes semi-major axis (SOLN3) | — | 0.15 | 0.15 |
| Chooses correct solution numerically | 0.2 | 0.2 | 0.2 |
| Units of $a_0$ correctly | 0.2 | 0.2 | 0.2 |
| **Total** | 1.0 | 1.0 | 1.0 |

---

## T1-B2 [2.5 pts] — asymptotic direction, $\mu = 15/2$

**Official final answer:** $\theta = 90^\circ - \theta' = -16.60^\circ$, where $\theta' = \arccos(-1/\varepsilon) = \arccos(-2/7) = 106.60^\circ$ is measured from the $y$ axis (the initial separation line). I.e. $\vec u_\infty$ makes an angle of **16.60°** with the initial line of motion of $e^+$, deflected "downward" (toward the side where $e^-$ initially was), as stated in the official solution ("the initial $e^+$ velocity is directed towards the positive $x$-axis, heading downward").

Official reasoning (summary): $E = +\frac{ke^2}{80a_0} > 0$; $r(\theta) = \ell/(1+\varepsilon\cos(\theta-\theta_0))$ with the initial position the closest approach ($\theta_0=0$); $r\to\infty$ when $1+\varepsilon\cos\theta' = 0$; $\varepsilon = \sqrt{1+\frac{45}{4}} = \frac72$.

| Step (SOLN 1) | Points |
|---|---|
| Numerically tabulates the energy and finds it positive | 0.8 |
| Computes eccentricity correctly (needs to be > 1) | 0.8 |
| Finds parameter $a$ correctly | 0.4 |
| Finds angle correctly (denominator vanishing) | 0.5 |

---

## T1-C1 [2.5 pts] — minimum photon frequency

**Official final answer:**
$$\omega_{\min} = \frac{3mc^2 - \sqrt{3mc^2\left(3mc^2 + 2\Delta U(\cos(2\theta)-2)\right)}}{\hbar\,(2-\cos(2\theta))}$$
(equivalently, from the centre-of-mass solution, $p_\gamma = \dfrac{3cm - \sqrt3\sqrt m\sqrt{3c^2m + 2\Delta U\cos(2\theta) - 4\Delta U}}{2\sin^2\theta + 1}$ with $\hbar\omega_{\min} = p_\gamma c$; note $2\sin^2\theta+1 = 3-2\cos^2\theta = 2-\cos 2\theta$). For $\theta \ge 90^\circ$ the official solution states the formula is the same as for $\theta = 90^\circ$.

*Grader note:* the official solution's second boxed form, $\omega_{\min} = 3mc^2\left[\dfrac{1-\sqrt{1-\frac{\Delta U}{3mc^2}(2\sin^2\theta+1)}}{(2\sin^2\theta+1)\hbar}\right]$, lacks a factor 2 inside the square root relative to the two forms above (it should read $1-\frac{2\Delta U}{3mc^2}(2\sin^2\theta+1)$); the forms above are the ones consistent with the official C2 expansion. Accept answers equivalent to the forms above.

Official reasoning (SOLN1): momentum $\hbar\frac{\omega}{c}\hat k = \vec p + \vec q$; energy $\hbar\omega = \Delta U + \frac{p^2}{4m} + \frac{q^2}{2m}$; quadratic in $p$: $p^2 - \frac{4\hbar\omega\cos\theta}{3c}p + \frac{2\hbar^2\omega^2}{3c^2} + \frac43 m(\Delta U - \hbar\omega) = 0$; reality (discriminant $\ge 0$) gives $(\cos 2\theta - 2)\hbar^2\omega^2 + 6mc^2\hbar\omega - 6\Delta U mc^2 = 0$ at the threshold; the smaller root is $\omega_{\min}$.

| Step | SOLN1: pure algebra | SOLN2: centre-of-mass approach |
|---|---|---|
| Momentum conservation correct | 0.2 | — |
| Energy conservation correct | 0.2 | — |
| Quadratic equation for $p$ | 0.4 | — |
| Reality condition (critical discriminant) | 0.8 | — |
| Center of mass velocity correct | — | 0.2 |
| Relation between outgoing relative velocities wrt CM | — | 0.2 |
| Energy conservation correct (inc. velocities wrt CM) | — | 0.2 |
| Find that velocity of O$_2$ relative to CM is fixed | — | 0.2 |
| Geometric setup done correctly (how velocity vectors add) | — | 0.2 |
| Understand critical condition (straight triangle reasoning) | — | 0.6 |
| Correctly write quadratic equation for $w$ [$\omega$] | 0.3 | 0.3 |
| Solve quadratic equation for $w$ | 0.2 | 0.2 |
| Get correct root and final form correct | 0.4 | 0.37 |
| Handle backscattering correctly ($\theta \ge 90^\circ$) | — | 0.03 |
| **Total** | 2.5 | 2.5 |

---

## T1-C2 [1.0 pts] — numerical value for $\theta = \pi/6$

**Official final answer:** $\hbar\omega_{\min} - \Delta U = \dfrac{2-\cos(2\theta)}{6mc^2}(\Delta U)^2 = 2.03\times10^{-11}\ \text{eV}$

(Up to second order in $\Delta U$: $\omega_{\min} = \frac{\Delta U}{\hbar} - \frac{(\cos(2\theta)-2)\Delta U^2}{6\hbar mc^2}$.)

| Step | Solution by Taylor series | Solution by direct substitution in C1 |
|---|---|---|
| Write Taylor expansion | 0.2 | — |
| Go to second order | 0.4 | — |
| Finds large cancellation numerically | — | 0.5 |
| Numerical value correct within 5% | 0.3 | 0.4 |
| Numerical value correct within 50% (only if not within 5%) | — | 0.2 |
| Units in final answer correct | 0.1 | 0.1 |
| **Total** | 1.0 | 1.0 |

---

*Remark:* the official solution's subsection header reads "T1-B [2.5 pts]"; the statement and the marking scheme give T1-B = 3.5 pts (B1 1.0 + B2 2.5), which is used here.
