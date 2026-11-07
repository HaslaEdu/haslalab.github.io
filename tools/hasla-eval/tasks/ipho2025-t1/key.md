# IPhO 2025 T1 — Hydrogen and galaxies: official answers and marking scheme

**Task total: 10.0 points** (A: 2.2 = 0.2+0.5+0.5+0.5+0.5; B: 2.5 = 0.2+0.5+1.8; C: 3.0 = 0.5+0.6+0.7+0.6+0.6; D: 2.3 = 0.4+0.2+0.8+0.9).

Source: official solution with embedded marking scheme, "Q1 … English (Official)", `IPhO_2025_S1.pdf` (each part: SOLUTION, then "Marking Scheme" table with step labels and points). Step descriptions are copied from the scheme; boxed results of the official solution are given as the final answers. Values read from figures carry the tolerances stated in the scheme.

---

## A.1 [0.2 pt]

**Official answer:** Newton's second law on $\vec u_r$: $-m_e\frac{v^2}{r} = -\frac{e^2}{4\pi\varepsilon_0 r^2}$, hence
$$v = \sqrt{\frac{e^2}{4\pi\varepsilon_0 m_e r}}$$

| Step | Points |
|---|---|
| A.1.1 : Using Newton's second law | 0.1 |
| A.1.2 : Expression of the velocity | 0.1 |

## A.2 [0.5 pt]

**Official answer:** $L = m_e r_n v_n = n\hbar$ and $v_n = \sqrt{\frac{e^2}{4\pi\epsilon_0 m_e r_n}} = \sqrt{\frac{\alpha\hbar c}{m_e r_n}}$ give
$$r_n = \frac{\hbar n^2}{\alpha m_e c},\qquad r_1 = \frac{\hbar}{\alpha m_e c} = 5.31\times10^{-11}\ \mathrm{m},\qquad v_1 = \frac{e^2}{4\pi\varepsilon_0\hbar} = \alpha c.$$

| Step | Points |
|---|---|
| A.2.1 : Expression of $r_n$ | 0.1 |
| A.2.2 : Expression of $r_1$ | 0.1 |
| A.2.3 : Numerical value for $r_1$ | 0.1 |
| A.2.4 : Expression of $v_1$ | 0.2 |

## A.3 [0.5 pt]

**Official answer:** $E_n = \frac12 m_e v_n^2 - \frac{e^2}{4\pi\varepsilon_0 r_n} = -\frac{e^2}{8\pi\varepsilon_0 r_n}$, hence
$$E_n = -\frac{e^2}{8\pi\varepsilon_0 n^2 r_1},\qquad E_1 = -\frac{e^2}{8\pi\varepsilon_0 r_1} = -\frac12\alpha^2 m_e c^2 = -2.17\times10^{-18}\ \mathrm{J} = -13.6\ \mathrm{eV}.$$

| Step | Points |
|---|---|
| A.3.1 : Expression for $E_n$ | 0.2 |
| A.3.2 : Expression for $E_1$ with $\alpha$ | 0.2 |
| A.3.3 : Numerical value for $E_1$ | 0.1 |

## A.4 [0.5 pt]

**Official answer:** period $T = \frac{2\pi r_1}{v_1}$; current $i = \frac{e}{T} = \frac{e v_1}{2\pi r_1} = \frac{e\alpha c}{2\pi r_1}$; loop field $B = \frac{\mu_0 i}{2R}$, so
$$B_1 = \frac{\mu_0 e\alpha c}{4\pi r_1^2}.$$

| Step | Points |
|---|---|
| A.4.1 : Expression for the period | 0.1 |
| A.4.2 : Expression for the current | 0.2 |
| A.4.3 : General expression for $B$ | 0.1 |
| A.4.4 : Inject $i$ into $B$ | 0.1 |

## A.5 [0.5 pt]

**Official answer:** $E_p = -\vec{\mathcal M}_s\cdot\vec B_1$; $\Delta E_{\rm F} = 2\mathcal M_s B_1 = 2\frac{e}{m_e}\hbar B_1 = 2\frac{e}{m_e}\hbar\frac{\mu_0 e\alpha c}{4\pi r_1^2}$, which writes
$$\Delta E_{\rm F} = -4\alpha^2 E_1,\qquad \Delta E_{\rm HF} = -3.72\frac{m_e}{m_p}4\alpha^2E_1,$$
$$\lambda_{\rm HF} = -\frac{hc}{3.72\,\frac{m_e}{m_p}\,4\alpha^2 E_1} = 21\ \mathrm{cm}.$$

| Step | Points |
|---|---|
| A.5.1 : Expression for the potential energy | 0.1 |
| A.5.2 : Expression for $\Delta E_{\rm F}$ | 0.1 |
| A.5.3 : Expression for $\Delta E_{\rm HF}$ in term of $\alpha$ | 0.1 |
| A.5.4 : Expression for $\lambda_{\rm HF}$ | 0.1 |
| A.5.5 : Numerical value for $\lambda_{\rm HF}$ | 0.1 |

## B.1 [0.2 pt]

**Official answer:** $\vec F = -\nabla(m\varphi) = -m\frac{d\varphi}{dr}\vec u_r$; Newton's second law for a circular orbit: $m\frac{v_c^2}{r} = m\frac{d\varphi}{dr}$, hence
$$v_c = \sqrt{r\frac{d\varphi}{dr}}.$$

| Step | Points |
|---|---|
| B.1.1 : Using Newton's second law | 0.1 |
| B.1.2 : Expression for the velocity. | 0.1 |

## B.2 [0.5 pt]

**Official answer:** Gauss: $g(r) = GM_{\rm int}(r)/r^2$; for $r>r_b$, $M_{\rm int} = M_b$, $\vec g(r>r_b) = -\frac{GM_b}{r^2}\vec u_r$, $v_c(r>r_b) = \sqrt{GM_b/r}$, so $M_b = v_c^2R/G$. Reading $v_c = 20\ \mathrm{km\cdot s^{-1}}$ at $R = 10$ kpc on the red curve:
$$M_b = \frac{v_c^2R}{G}\simeq\frac{4\cdot10^8\times3\cdot10^{20}}{6.7\cdot10^{-11}}\simeq1.8\cdot10^{39}\ \mathrm{kg},\qquad M_b\simeq9\cdot10^{8}\ M_\odot.$$

| Step | Points |
|---|---|
| B.2.1 : $g(r) = GM_{\rm int}(r)/r^2$ via Gauss's theorem or another method resulting in an equivalent result. | 0.1 |
| B.2.2 : Expression for $\vec g(r>r_b)$ | 0.1 |
| B.2.3 : Expression for $M_b$ | 0.1 |
| B.2.4 : Taking the right value of $v_c$ in the figure | 0.1 |
| B.2.5 : Numerical value for $M_b$ with a tolerance of ±25% | 0.1 |

## B.3 [1.8 pt]

**Official answer:** $g(r) = GM_{\rm int}(r)/r^2$ with $M_{\rm int} = \int_0^r 4\pi x^2\rho(x)dx = 4\pi C_m\left[r - r_m\arctan\left(\frac{r}{r_m}\right)\right]$, so
$$g_m(r) = -\frac{4\pi C_mG\left[r - r_m\arctan\left(\frac{r}{r_m}\right)\right]}{r^2},\qquad v_{c,m} = \sqrt{r g_m(r)} = \sqrt{\frac{4\pi C_mG\left[r - r_m\arctan\left(\frac{r}{r_m}\right)\right]}{r}}$$
[editor's note: as printed; the magnitude of $g_m$ is meant under the root], hence
$$k_1 = 4\pi C_mG,\qquad k_2 = 4\pi C_mG\,r_m.$$
- $r\ll r_m$ (third-order Taylor expansion of arctan): $v_{c,m}\simeq\sqrt{\dfrac{4\pi C_mGr^2}{3r_m^2}}$
- $r\gg r_m$: $\arctan(r/r_m)\simeq\pi/2$ and $v_{c,m}\simeq\sqrt{4\pi C_mG}$.

Reading $v_c\simeq160\ \mathrm{km\cdot s^{-1}}$ for the constant value: $C_m = \frac{v_c^2}{4\pi G}\simeq\frac{(1.6\cdot10^5)^2}{4\pi\times6.67\cdot10^{-11}}\simeq3\cdot10^{19}\ \mathrm{kg\cdot m^{-1}}$. $M_{\rm int}\simeq4\pi C_m r$ if $r\gg r_m$. With the radius in the picture $R = 9\ \mathrm{kpc} = 2.27\times10^{20}$ m (sic, as printed in the official solution):
$$M_{\rm in\ the\ figure}\simeq4\pi C_mR\simeq10^{41}\ \mathrm{kg}\simeq10^{11}\ M_\odot$$
(more than ten times the visible mass: dark matter).

| Step | Points |
|---|---|
| B.3.1 : $g(r) = GM_{\rm int}(r)/r^2$ via Gauss' Theorem or another method resulting in an equivalent result. | 0.2 |
| B.3.2 : Interior mass | 0.3 |
| B.3.3. : Expression for $g(r)$ | 0.1 |
| B.3.4 : Using Newton's second law | 0.1 |
| B.3.5 : Expression for $k_1$ | 0.1 |
| B.3.6 : Expression for $k_2$ | 0.1 |
| B.3.7 : Simplification for $v_c$ in the case $r\ll r_m$ | 0.2 |
| B.3.8 : Simplification for $v_c$ in the case $r\gg r_m$ | 0.2 |
| B.3.9 : Value of $C_m$ | 0.2 |
| B.3.10 : Expression for $M_m$ in the case $r\gg r_m$ | 0.2 |
| B.3.11 : Mass in the figure (good if nearest power of ten) | 0.1 |

## C.1 [0.5 pt]

**Official answer:** $m\vec a = \vec F = -m\nabla\varphi$, projected on $\vec u_z$: $m\ddot z = -m\frac{\partial\varphi}{\partial z}$, so
$$\ddot z = \frac{2z}{z_0^2}\varphi_0\ln\left(\frac{r}{r_0}\right)\exp\left[-\left(\frac{z}{z_0}\right)^2\right].$$
Near $z=0$: $\ddot z\simeq\frac{2z}{z_0^2}\varphi_0\ln\left(\frac{r}{r_0}\right)$. For $r<r_0$ the ln is negative: $\ddot z\simeq-\omega_0^2z$ with
$$\omega_0 = \sqrt{\frac{2\varphi_0}{z_0^2}\left|\ln\left(\frac{r}{r_0}\right)\right|}$$
— stable oscillation about $z=0$.

| Step | Points |
|---|---|
| C.1.1 : Newton's second law, or equivalent method | 0.1 |
| C.1.2 : Projection on the z axis | 0.1 |
| C.1.3 : Equation of motion | 0.1 |
| C.1.4 : Equation near the galactic plane | 0.1 |
| C.1.5 : Expression for $\omega_0$ | 0.1 |

## C.2 [0.6 pt]

**Official answer:** regime $r\gg r_m$: $g_m(r)\simeq-\frac{4\pi C_mG}{r}$, $\varphi(r) = +4\pi C_mG\ln(r) + \mathrm{cst}$, i.e. $\varphi_G(r,z=0) = \varphi_0\ln\left(\frac{r}{r_0}\right)$ with
$$\varphi_0 = +4\pi C_mG,\qquad v_c = \sqrt{rg_m(r)} = \sqrt{4\pi C_mG} = \sqrt{\varphi_0}.$$

| Step | Points |
|---|---|
| C2.1 : Condition for simplication $r\gg r_m$ | 0.1 |
| C2.2 : Expression for $\varphi(r)$ | 0.2 |
| C2.3 : Identification of $\varphi_0$ | 0.1 |
| C2.4 : Newton's second law | 0.1 |
| C2.5 : Expression for $v_c$ | 0.1 |

## C.3 [0.7 pt]

**Official answer:** $\overrightarrow{Ss} = v_\odot\sin(\alpha)\,\vec u_v$ and $\overrightarrow{Ee} = v_E\cos(\beta)\,\vec u_v$; $\alpha = \ell$ (since $\vec v_\odot\perp CS$); $CT = R_\odot\sin(\ell) = R\sin(\frac\pi2-\beta)$, so $\cos(\beta) = \frac{R_\odot}{R}\sin(\ell)$. With $v_E = v_\odot$ and $\vec v_{rE/S} = \overrightarrow{Ee}-\overrightarrow{Ss}$:
$$v_{rE/S} = v_\odot\left(\frac{R_\odot}{R}-1\right)\sin(\ell),\qquad R = \frac{R_\odot}{1+\dfrac{v_{rE/S}}{v_\odot\sin(\ell)}}.$$

| Step | Points |
|---|---|
| C3.1 : Expression for $\overrightarrow{Ss}$ | 0.1 |
| C3.2 : Expression for $\overrightarrow{Ee}$ | 0.1 |
| C3.3 : $\alpha = \ell$ | 0.1 |
| C3.4 : Expression for $\cos(\beta)$ | 0.1 |
| C3.5 : Expression for $v_{r,E/S}$ | 0.2 |
| C3.6 : Expression for $R$ | 0.1 |

## C.4 [0.6 pt]

**Official answer:** peaks at $\Delta f_1 = 0.03$ MHz, $\Delta f_2 = 0.15$ MHz, $\Delta f_3 = 0.26$ MHz; $v_{r,i} = c\,\Delta f_i/f_0$ with $f_0 = 1420$ MHz:
- $v_{r,1} = 6.33\ \mathrm{km\cdot s^{-1}}$, $v_{r,2} = 31.7\ \mathrm{km\cdot s^{-1}}$, $v_{r,3} = 54.9\ \mathrm{km\cdot s^{-1}}$

(tolerance because candidates could use $c = 3.00\times10^8$ m/s instead of the 9 digits of the formulary). With $R_i = \dfrac{R_\odot}{1+\dfrac{v_{r,i}}{v_\odot\sin\ell}}$ and $\ell = 30^\circ$:
- $R_1 = 0.95R_\odot$, $R_2 = 0.78R_\odot$, $R_3 = 0.67R_\odot$

| Step | Points |
|---|---|
| C4.1 : Doppler formula for $v_r$ | 0.1 |
| C4.2 : Getting the 3 numerical values for $\Delta f$ | 0.2 |
| C4.3 : Numerical values of the 3 velocities (± 0.01 km·s⁻¹) | 0.2 |
| C4.4 : Numerical values of the 3 distances (± 0.01 $R_\odot$) | 0.1 |

## C.5 [0.6 pt] — [GRAPH/FIGURE-DEPENDENT]

**Official answer:** the line of sight from $S$ at $\ell = 30^\circ$ from $SC$ can be obtained geometrically (using the 15° grid; since $\sin30^\circ = 0.5$ the line of sight passes through $S$ and is tangent to the circle of radius $CS/2$). Drawing the circles of radii $R_1$, $R_2$, $R_3$ around $C$, each meets the line of sight at 2 points (near and far); the official answer plots the nearest intersection for each source (three points on the line of sight, at distances $0.95R_\odot$, $0.78R_\odot$, $0.67R_\odot$ from $C$). The far intersections are much further away and hence likely less intense; astronomers could also use the variation in the radio signal when slowly varying the longitude to determine the right position.
**Deduction:** a continuous variation of $\ell$ in $[0,2\pi]$ makes hydrogen sources appear in the galaxy; as the galaxy is essentially composed of hydrogen, one can trace its mass distribution, i.e. the spiral structure.

| Step | Points |
|---|---|
| C5.1 : Getting the right line of sight | 0.1 |
| C5.2 : Drawing for the 3 circles | 0.2 |
| C5.3 : Drawing for the 3 points | 0.2 |
| C5.4 : Deduction | 0.1 |

*Grader note for text-only answers:* C5.1–C5.3 (0.5 pt) can only be awarded if the answer describes the construction/positions unambiguously (line of sight at 30° from $SC$ tangent to the circle of radius $R_\odot/2$; points on it at $R_1,R_2,R_3$ from $C$, near intersections).

## D.1 [0.4 pt]

**Official answer:** $v_{c,\infty}^2 = 4\pi C_mG$ and $M_{\rm tot}\simeq4\pi C_mR$, so $C_m = \frac{M_{\rm tot}}{4\pi R}$ and $v_{c,\infty}^2 = 4\pi\frac{M_{\rm tot}}{4\pi R}G$:
$$M_{\rm tot} = \eta v_{c,\infty}^{\gamma}\ \text{with}\ \gamma = 2,\ \eta = R/G;\qquad \gamma_{TF}\simeq\frac{12-9}{2.6-1.8} = 3.75$$
— the dark matter model of part B cannot reproduce this law.

| Step | Points |
|---|---|
| D1.1 : Recall for $v_{c,\infty}$ | 0.1 |
| D1.2 : Expression for $\eta$ | 0.1 |
| D1.3 : Expression for $\gamma$ | 0.1 |
| D1.4 : Numerical value for $\gamma_{TF}$ (correct if it is between 3.5 and 4) | 0.1 |

## D.2 [0.2 pt]

**Official answer:** $a_m\simeq v_c^2/R$; with $v_c = 160\ \mathrm{km\cdot s^{-1}}$ for $R>5$ kpc, at the smallest distance:
$$a_m = \frac{(1.6\cdot10^5)^2}{5.3\cdot10^{19}}\simeq1.5\times10^{-10}\ \mathrm{m\cdot s^{-2}}$$
(maximal acceleration in the outer regions; MOND regime).

| Step | Points |
|---|---|
| D2.1 : Expression for $a_m$ | 0.1 |
| D2.2 : Numerical value for $a_m$ (good nearest power of ten) | 0.1 |

## D.3 [0.8 pt]

**Official answer:** for $x = a/a_0\ll1$, $\mu\simeq x$ and $\vec F = m\frac{a}{a_0}\vec a$. Radial component: $G\frac{M}{r^2}m = m\frac{a^2}{a_0}$ with $a = v_{c,\infty}^2/r$: $G\frac{M}{r^2} = \frac{v_{c,\infty}^4}{r^2a_0}$, so
$$v_{c,\infty} = (a_0GM)^{1/4},\quad M = \frac{1}{a_0G}v_{c,\infty}^4,\quad \gamma_{\rm MOND} = 4$$
(in accordance with Tully-Fischer). For NGC 6946: $v_{c,\infty} = 160\ \mathrm{km\cdot s^{-1}}$, $\log_{10}\left(\frac{v_{c,\infty}}{1\ \mathrm{km\cdot s^{-1}}}\right) = 2.2$, Tully-Fischer gives $\log(M_{\rm tot}/M_\odot) = 10.5$, $M_{\rm tot} = 2\cdot10^{40.5}$ kg;
$$a_0 = \frac{v_{c,\infty}^4}{GM_{\rm tot}} = 1.5\times10^{-10}\ \mathrm{m\cdot s^{-2}}.$$

| Step | Points |
|---|---|
| D3.1 : Considering the hypothesis $a\ll a_0$ | 0.1 |
| D3.2 : Newton's second law | 0.1 |
| D3.3 : Expression for $v_{c,\infty}$ | 0.1 |
| D3.4 : Numerical value for $\gamma_{MOND}$ | 0.1 |
| D3.5 : Numerical value for $\log_{10}(v_{c,\infty}/1\ \mathrm{km/s})$ | 0.1 |
| D3.6 : Numerical value for $\log_{10}(M)$ | 0.1 |
| D3.7 : Expression for $a_0$ | 0.1 |
| D3.8 : Numerical value for $a_0$ (good if nearest power of ten) | 0.1 |

## D.4 [0.9 pt]

**Official answer:** modified second law with the full $\mu$: $\mathcal G(r)m = -m\dfrac{\frac{v_f^2}{a_0r}}{1+\frac{v_f^2}{a_0r}}\dfrac{v_f^2}{r}$ (notation $v_f$ = $v_c$ as printed), with the field of the homogeneous ball (Gauss):
$$\mathcal G(r) = \begin{cases}-GM/r^2 & \text{if } r>R_b\\ -GMr/R_b^3 & \text{if } r\le R_b\end{cases}$$
Outside ($r>R_b$): $v_c^4 - \frac{GM}{r}v_c^2 - a_0GM = 0$, positive root
$$v_c(r) = \sqrt{\frac{GM}{2r}\left(1+\sqrt{1+\frac{4a_0r^2}{GM}}\right)}\quad(r>R_b);$$
when $r\to\infty$, $v_c$ is asymptotically constant and $M\to\frac{v_{c,\infty}^4}{a_0G}$ (Tully-Fisher).
Inside ($r\le R_b$): $v_c^4 - \frac{GM}{r}\left(\frac{r}{R_b}\right)^3v_c^2 - a_0GM\left(\frac{r}{R_b}\right)^3 = 0$, positive solution
$$v_c(r) = \sqrt{\frac{GM}{2r}\left(\frac{r}{R_b}\right)^3\left[1+\sqrt{1+\frac{4a_0r^2}{GM}\left(\frac{R_b}{r}\right)^3}\right]}\quad(r\le R_b);$$
when $r\to0$, $v_c\to0$.

| Step | Points |
|---|---|
| D4.1 : Modified second law | 0.1 |
| D4.2 : Gravitational field in the case $r>R_b$ | 0.1 |
| D4.3 : Gravitational field in the case $r<R_b$ | 0.1 |
| D4.4 : Bi-quadratic equation in the case $r>R_b$ | 0.1 |
| D4.5 : Expression for $v_c$ in the case $r>R_b$ | 0.1 |
| D4.6 : Behaviour in the limit $r\to\infty$ | 0.1 |
| D4.7 : Bi-quadractic equation for $r<R_b$ | 0.1 |
| D4.8 : Expression for $v_c$ when $r<R_b$ | 0.1 |
| D4.9 : Behaviour when $r\to0$ | 0.1 |
