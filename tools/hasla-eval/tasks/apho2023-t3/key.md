# APhO 2023 T3 — Cavitation: official answers and marking scheme

**Task total: 10.0 points** (A 1.5 + B 6.0 + C 2.5).

Sources: official marking scheme "Theoretical Problem 3: Cavitation — Q3 - Marking Scheme" (`APhO_2023_M3.pdf`) for the step points; official solution "Cavitation: a possible solution (Tsogtgerel Gantumur)" (`APhO_2023_S3.pdf`) for the answers. Step descriptions are copied from the scheme. Equation numbers (n) refer to the official solution. The solution itself warns: "The chosen units might be a bit different from the 'official' problem statement" (it uses e.g. $p_\infty = 100$ kPa, $1\,\mu$m $= 10^{-6}$ m, $\delta_0 = 1.2$ kg/m³). Several printed numerical values in the official solution do not follow from the statement's data; these are flagged in "Grader note" lines (not part of the official text).

---

## A.1 [0.5 pt] — collapse time by dimensional analysis

**Official answer:** the bubble would not collapse for $p_\infty \le p_v$, so $p_\infty - p_v$ enters; $[R_0] = \mathrm m$, $[\rho] = \mathrm{kg/m^3}$, $[p_\infty - p_v] = \mathrm{kg/(m\,s^2)}$; the only combination with dimension of time:
$$\tau \sim R_0\sqrt{\frac{\rho}{p_\infty - p_v}} \approx 0.1\ \mathrm s\ \text{(as printed)}.$$
*Grader note: with $R_0 = 1$ mm, $\rho = 997$ kg/m³, $p_\infty - p_v = 98.66$ kPa the formula gives $1.0\times10^{-4}$ s $= 0.1$ ms; the printed "0.1 s" appears to be a unit misprint.*

| Step | Points |
|---|---|
| Derivation of the formula | 0.4 |
| Numerical answer | 0.1 |

## A.2 [1.0 pt] — air partial pressure and critical pressure

**Official answer:** equilibrium $p_v + q = p_\infty + \dfrac{2\sigma}{R}$; at $R = R_0$:
$$q_0 = p_\infty - p_v + \frac{2\sigma}{R_0}\ \ (\approx 170\ \mathrm{kPa}\ \text{as printed}).$$
Isothermal law $q_0R_0^3 = qR^3$ gives $p_\infty = p_v + \dfrac{q_0R_0^3}{R^3} - \dfrac{2\sigma}{R}$; the critical pressure is the minimum of $p_\infty(R)$, at
$$R_c = R_0\sqrt{\frac{3q_0R_0}{2\sigma}}\ (\approx 60\ \mu\mathrm m),\qquad p_c = p_v - 2q_0\left(\frac{R_0}{R_c}\right)^3\ (\approx 700\ \mathrm{Pa}).$$
*Grader note: with the statement's data ($p_\infty = 101$ kPa, $p_v = 2340$ Pa, $\sigma = 72.8$ mN/m, $R_0 = 10\,\mu$m) one gets $2\sigma/R_0 = 14.56$ kPa, $q_0 \approx 113$ kPa, $R_c \approx 48\,\mu$m and $p_c \approx 330$ Pa. The printed $R_c \approx 60\,\mu$m and $p_c \approx 700$ Pa are consistent with the printed $q_0 \approx 170$ kPa.*

| Step | Points |
|---|---|
| Pressure equilibrium condition | 0.3 |
| Numerical answer for partial air pressure | 0.1 |
| Equilibrium condition with isothermal law | 0.1 |
| Formula for critical pressure | 0.4 |
| Numerical answer for critical pressure | 0.1 |

---

## B.1 [1.5 pt] — Rayleigh–Plesset equation

**Official answer:** with $u(t) = R'(t)$, incompressibility gives $v(r,t) = \dfrac{R^2u(t)}{r^2}$, so $\dfrac{\partial v}{\partial t} = \dfrac{2R}{r^2}u^2 + \dfrac{R^2}{r^2}u'$ and the radial acceleration is
$$a = \frac{\partial v}{\partial t} + \frac{\partial v}{\partial r}v = \frac{R^2}{r^2}u' + \frac{2R}{r^2}u^2 - \frac{2R^4}{r^5}u^2.$$
Newton's law $\rho a = -p'$; integrating from $r = R$ to $\infty$: $Ru' + \frac32u^2 = \dfrac{p(R) - p_\infty}{\rho}$. With $p = p(R) + \dfrac{2\sigma}{R}$ (pressure inside the bubble):
$$RR'' + \frac32(R')^2 + \frac{2\sigma}{\rho R} = \frac{p - p_\infty}{\rho},$$
and with $p = p_v + q = p_v + q_0\left(\dfrac{R_0}{R}\right)^{3\gamma}$:
$$\rho RR'' + \frac32\rho(R')^2 + \frac{2\sigma}{R} - \frac{q_0R_0^{3\gamma}}{R^{3\gamma}} = p_v - p_\infty.$$

| Step | Points |
|---|---|
| Incompressibility condition | 0.3 |
| Computation of radial acceleration | 0.5 |
| Taking into account Newton's second law | 0.3 |
| Final equation with p, where surface tension enters | 0.2 |
| Final equation with p split and adiabatic law taken into account | 0.2 |

## B.2 [1.0 pt] — terminal growth speed after exposure to vacuum

**Official answer:** setting $R'' = 0$, $R \to \infty$:
$$R'(\infty) = \sqrt{\frac{2(p_v - p_\infty)}{3\rho}} = \sqrt{\frac{2p_v}{3\rho}} \approx 1.24\ \mathrm{m/s};$$
initial acceleration $R''(0) = \dfrac{q_0 + p_v - 2\sigma/R_0}{\rho R_0} = \dfrac{p_\infty^-}{\rho R_0} \approx 10^7\ \mathrm{m/s^2}$; time to reach the terminal speed
$$t = \frac{R'(\infty)}{R''(0)} \approx 0.1\ \mu\mathrm s.$$

| Step | Points |
|---|---|
| Formula for terminal speed | 0.4 |
| Numerical answer for terminal speed | 0.1 |
| Formula for time or for initial acceleration | 0.4 |
| Numerical answer for time | 0.1 |

## B.3 [1.0 pt] — minimum radius on collapse

**Official answer:** multiplying the B.1 equation by $2R^2R'$ and integrating from $R(0) = R_0$, $R'(0) = 0$:
$$\rho R^3(R')^2 + 2\sigma(R^2 - R_0^2) + \frac{2q_0R_0^{3\gamma}(R^{3-3\gamma} - R_0^{3-3\gamma})}{3(\gamma-1)} = \frac23(p_v - p_\infty)(R^3 - R_0^3),$$
$$\rho(R')^2 = \frac{2(p_v - p_\infty)}{3} - \frac{2\sigma}{R} + \frac{2R_0^3}{R^3}\left(\frac{\sigma}{R_0} + \frac{p_\infty - p_v}{3} + \frac{q_0}{3(\gamma-1)} - \frac{q_0R_0^{3\gamma-3}}{3(\gamma-1)R^{3\gamma-3}}\right).$$
For $R \ll R_0$ this gives first $R' \sim -R^{-3/2}$, and the rebound radius satisfies
$$\left(\frac{R_0}{R}\right)^{3(\gamma-1)} = \frac{(\gamma-1)(p_\infty - p_v + 3\sigma/R_0)}{q_0} + 1.$$
With $q_0 = p_\infty^- - p_v + 2\sigma/R_0 \approx 10$ Pa (as printed), the rebound radius is
$$R \approx 0.4\ \mu\mathrm m\ \text{(as printed)}.$$
*Grader note: with the statement's data, $q_0 = 1600 - 2340 + 14560 \approx 1.38\times10^4$ Pa, and the official rebound formula then gives $R \approx 2.9\,\mu$m; with $q_0 = 10$ Pa it would give $R \approx 0.009\,\mu$m. The printed values ($q_0 \approx 10$ Pa, $R \approx 0.4\,\mu$m) cannot both be reproduced from the given data.*

| Step | Points |
|---|---|
| Formula for speed R' | 0.5 |
| Formula for rebound radius | 0.4 |
| Numerical answer for rebound radius | 0.1 |

## B.4 [0.5 pt] — collapse exponent

**Official answer:** from B.3, $R' \sim -R^{-3/2}$; with $R \sim (T-t)^\alpha$: $(T-t)^{\alpha-1} \sim -(T-t)^{-3\alpha/2}$, so
$$\alpha = \frac25.$$

| Step | Points |
|---|---|
| Writing down the asymptotic equation for R' | 0.2 |
| Substitution of the form into the equation | 0.2 |
| Numerical answer for alpha | 0.1 |

## B.5 [1.0 pt] — natural frequency

**Official answer:** with $R = R_0x$, $x = 1 + y$, linearizing: $\rho R_0^2y'' + \dfrac{2\sigma}{R_0}(1-y) - q_0(1 - 3\gamma y) = p_v - p_\infty$; with the equilibrium condition $\dfrac{2\sigma}{R_0} - q_0 = p_v - p_\infty$:
$$y'' + \frac{3\gamma q_0 - 2\sigma/R_0}{\rho R_0^2}\,y = 0.$$
Unstable if $3\gamma q_0 \le 2\sigma/R_0 = q_0 + p_v - p_\infty$, i.e. if $p_\infty \le p_v - (3\gamma-1)q_0$. Otherwise the bubble oscillates with
$$f_0 = \frac{1}{2\pi R_0}\sqrt{\frac{(3\gamma-1)q_0 + p_\infty - p_v}{\rho}} \approx 33\ \mathrm{kHz}\quad(R_0 = 0.1\ \mathrm{mm}).$$

| Step | Points |
|---|---|
| Writing down the linear second order equation | 0.4 |
| Recognition of the stability condition | 0.2 |
| Formula for the natural frequency | 0.3 |
| Numerical answer for the natural frequency | 0.1 |

## B.6 [1.0 pt] — average force in a standing wave

**Official answer:** small oscillations are driven by the pressure at the origin:
$$\rho R_0^2(y'' + 4\pi^2f_0^2y) = A\sin\left(\frac{2\pi f}{c}a\right)\sin(2\pi ft),\qquad y(t) = B\sin(2\pi ft),\quad B = \frac{A\sin(2\pi fa/c)}{4\pi^2\rho R_0^2(f_0^2 - f^2)}.$$
$R(t) = R_0 + R_0y(t)$, $V(t) = \frac{4\pi}{3}R(t)^3 \approx \frac{4\pi}{3}R_0^3[1 + 3y(t)]$; average force $F = -\left\langle V\dfrac{\partial p}{\partial x}\right\rangle$ with $\dfrac{\partial p}{\partial x} = \dfrac{2\pi fA}{c}\cos\left(\dfrac{2\pi f}{c}a\right)\sin(2\pi ft)$:
$$F = -\frac{fA^2R_0}{2\rho c(f_0^2 - f^2)}\sin\left(\frac{4\pi fa}{c}\right)$$
(directed along $x$).

| Step | Points |
|---|---|
| Writing down the forced oscillator equation | 0.2 |
| Solution of the equation | 0.3 |
| Computation of volume | 0.1 |
| Computation of pressure gradient | 0.1 |
| Final answer | 0.3 |

---

## C.1 [2.0 pt] — resorption time of a nucleus

**Official answer:** initial concentration in the bulk $u_i = Hp_\infty \approx 0.024$ kg/m³; near the bubble $u = Hq \approx 0.041$ kg/m³ ($u > u_i$: air diffuses away; the bubble shrinks, $2\sigma/R$ and $q$ grow, and the bubble is completely resorbed).
Mass balance in a shell $r \ldots r+\Delta r$: $\dfrac{dm}{dt} = 4\pi r^2\Delta r\dfrac{\partial u}{\partial t}$ and $\dfrac{dm}{dt} = 4\pi(r+\Delta r)^2J(r+\Delta r) - 4\pi r^2J(r) \approx 4\pi r^2\kappa\Delta r\dfrac{\partial^2u}{\partial r^2} + 8\pi r\kappa\Delta r\dfrac{\partial u}{\partial r}$, hence
$$\frac{\partial u}{\partial t} = \kappa\frac{\partial^2u}{\partial r^2} + \frac{2\kappa}{r}\frac{\partial u}{\partial r},\qquad \begin{cases}u(r,0) = u_i & r > R,\\ u(R,t) = Hq & t > 0\end{cases}$$
($R$ held constant). With $v = r(u - qH)$, $\tau = \kappa t$, $\xi = r - R$, $w(\xi,\tau) = v(R+\xi,\tau)$: $\partial_\tau w = \partial_\xi^2w$, $w(\xi,0) = (R+\xi)(u_i - qH)$, $w(0,\tau) = 0$, so
$$w(\xi,\tau) = \frac{u_i - qH}{\sqrt{4\pi\tau}}\int_0^\infty\left(e^{-(\xi-\eta)^2/(4\tau)} - e^{-(\xi+\eta)^2/(4\tau)}\right)(\eta + R)\,d\eta,$$
$$\left.\frac{\partial u}{\partial r}\right|_{r=R} = \frac1R\left.\frac{\partial w}{\partial\xi}\right|_{\xi=0} = (u_i - qH)\left(\frac1R + \frac{1}{\sqrt{\pi\kappa t}}\right).$$
The diffusion layer is much wider than the bubble, so
$$\frac{dm}{dt} = 4\pi R^2\kappa\left.\frac{\partial u}{\partial r}\right|_{r=R} \approx 4\pi\kappa R(u_i - qH).$$
Bubble mass $m = \frac{4\pi}{3}R^3\delta = \frac{4\pi}{3}R^3\cdot\frac{\delta_0q}{p_\infty}$ ($\delta_0 = 1.2$ kg/m³ at $p_\infty = 10^5$ Pa); with $q = p_\infty + \frac{2\sigma}{R}$ (vapour neglected), $m = \frac{4\pi}{3}R^3\left(\delta_0 + \frac{\varepsilon}{R}\right)$, $\varepsilon = \frac{2\sigma\delta_0}{p_\infty} \approx 1.73\cdot10^{-6}$ kg/m². Mass balance:
$$4\pi\kappa R\left(u_i - p_\infty H - \frac{2\sigma H}{R}\right) = 4\pi\delta_0R^2\frac{dR}{dt} + \frac{8\pi}{3}\varepsilon R\frac{dR}{dt};\quad u_i = p_\infty H \Rightarrow -2\sigma\kappa H\,dt = \delta_0R^2dR + \frac23\varepsilon R\,dR,$$
$$2\sigma\kappa Ht = \frac{\delta_0R_0^3}{3} + \frac{4\varepsilon R_0^2}{3}\ \text{(as printed)},\qquad t = \frac{(\delta_0R_0 + 4\varepsilon)R_0^2}{6\sigma\kappa H} \approx 9\ \mathrm s.$$
*Grader note: direct integration of the preceding line gives $\frac{\delta_0R_0^3}{3} + \frac{\varepsilon R_0^2}{3}$, i.e. $t = \frac{(\delta_0R_0 + \varepsilon)R_0^2}{6\sigma\kappa H}$; numerically the $\varepsilon$ term is a minor correction either way ($\delta_0R_0 = 1.2\times10^{-5}$ vs $\varepsilon \approx 1.7\times10^{-6}$ kg/m²: about 9.1 s with $4\varepsilon$, 6.6 s with $\varepsilon$; with $\delta = 1.29$ kg/m³ from Table 1, 9.7 s and 7.0 s). The official numerical answer is "≈ 9 s" — "the nucleus collapses in a matter of seconds".*

| Step | Points |
|---|---|
| Initial concentration of air in water | 0.1 |
| Initial concentration of air near bubble | 0.1 |
| Mass change rate in a shell in terms of concentration change rate | 0.1 |
| Mass change rate in a shell in terms of flux | 0.1 |
| Use of Fick's law | 0.1 |
| Diffusion equation in terms of r and t | 0.2 |
| Initial and boundary conditions | 0.2 |
| Reformulation and solution | 0.2 |
| Computing the air flux at the bubble wall | 0.2 |
| Simplification due to smallness of the bubble | 0.1 |
| Mass of the bubble in terms of pressure with ideal gas law taken into account | 0.2 |
| Mass balance | 0.1 |
| Final formula for resorption time | 0.2 |
| Numerical answer for resorption time | 0.1 |

## C.2 [0.5 pt] — gas pocket in a conical crevice

**Official answer:** equilibrium conditions
$$p_v + q = p_\infty \pm \frac{2\sigma}{R}\qquad\text{and}\qquad u = Hq.$$
The plus sign: water surface concave, surface tension squeezes the air out of the crevice through diffusion. Minus sign: water surface convex. If $q$ is initially large it decreases as the trapped air shrinks by diffusion, and a diffusive equilibrium is found when the water surface is convex. Thus the pocket of air does not disappear when the water surface is convex, meaning
$$\pi + \alpha < 2\theta.$$

| Step | Points |
|---|---|
| Condition of equilibrium | 0.2 |
| Final condition on angles | 0.3 |
