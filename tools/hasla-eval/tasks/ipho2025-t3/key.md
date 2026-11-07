# IPhO 2025 T3 — Champagne!: official answers and marking scheme

**Task total: 10.0 points** (A: 4.3 = 0.2+0.5+1.2+0.8+0.5+1.1; B: 3.3 = 1.1+1.1+1.1; C: 2.4 = 0.4+0.7+1.3).

Source: official solution with embedded marking scheme, "Q3 … English (Official)", `IPhO_2025_S3.pdf`. That file is a tracked-changes version (struck-through red = deleted, wavy-underlined blue = inserted); **the final (inserted) version is used here** — e.g. the widened tolerance ranges of A.4 and the re-weighted B.1 items. Step labels (A.2.1, …) and descriptions are copied from the scheme.

**Note on C.3:** the official C.3 step points (0.2+0.2+0.1+0.3+0.1+0.1+0.2+0.2) add up to **1.4 pt**, while the question is worth **1.3 pt** in the exam paper. They are reproduced unchanged; a grader should cap C.3 at 1.3 pt.

---

## A.1 [0.2 pt]

**Official answer:** Laplace's law: $P_{\rm b} = P_0 + \dfrac{2\sigma}{a}$.

| Step | Points |
|---|---|
| A.1. Laplace's law: $P_{\rm b} = P_0 + \frac{2\sigma}{a}$ | 0.2 |

## A.2 [0.5 pt]

**Official answer:** $a_{\rm c}$ is such that $c_\ell = c_{\rm b}$; $c_{\rm b} = k_{\rm H}P_{\rm b} = k_{\rm H}(P_0+\frac{2\sigma}{a})$, $c_0 = k_{\rm H}P_0$, so
$$a_{\rm c} = \frac{2\sigma}{P_0(c_\ell/c_0-1)} = 0.3\ \mu\mathrm m\quad(c_\ell = 4c_0).$$

| Step | Points |
|---|---|
| A.2.1. comparison (equality $c_{\rm b} = c_\ell$ or inequality $c_{\rm b}\le c_\ell$) | 0.1 |
| A.2.2. exact expression $a_{\rm c} = \frac{2\sigma}{P_0(c_\ell/c_0-1)}$ | 0.2 |
| A.2.3. numerical value $a_{\rm c} = 0.3\ \mu$m | 0.2 |

## A.3 [1.2 pt]

**Official answer:** $n_{\rm c} = \frac43\pi a^3\frac{P_0}{RT_0}$. Balance of CO$_2$: $\frac{\mathrm dn_{\rm c}}{\mathrm dt} = 4\pi a^2\frac{\mathrm da}{\mathrm dt}\frac{P_0}{RT} = j4\pi a^2\Rightarrow\frac{\mathrm da}{\mathrm dt} = j\frac{RT}{P_0}$.
- Model 1: $\frac{\mathrm da}{\mathrm dt} = \frac{DRT}{aP_0}(c_\ell-c_0)$, so $a^2 = a_0^2 + \frac{2DRT_0}{P_0}(c_\ell-c_0)\,t$.
- Model 2: $\frac{\mathrm da}{\mathrm dt} = \frac{KRT_0}{P_0}(c_\ell-c_0)$, so $a = a_0 + \frac{KRT_0}{P_0}(c_\ell-c_0)\,t$.

Experimental data: $\frac{\mathrm da}{\mathrm dt}$ is constant → **model 2**. Slope $\dot a\approx150/0.62\approx0.24\ \mathrm{mm\cdot s^{-1}}$; $K = 1.0\times10^{-4}\ \mathrm{m\cdot s^{-1}}$.

| Step | Points |
|---|---|
| A.3.1. $n_{\rm c} = \frac43\pi a^3\frac{P_0}{RT_0}$ | 0.1 |
| A.3.2. any equation that that can be interpreted as a particule balance | 0.1 |
| A.3.3. equation between $\dot a$ (or $\dot n_{\rm c}$) and $j$ | 0.2 |
| A.3.4. model 1 $a$ exact with $a_0$ present | 0.2 |
| A.3.5. model 2 $a$ exact with $a_0$ present | 0.2 |
| A.3.6. model 2 | 0.1 |
| A.3.7. value of the slope: total mark only if $\frac{\mathrm da}{\mathrm dt}$ is in range $[210-250]\ \mu\mathrm m\cdot s^{-1}$ | 0.1 |
| A.3.8. any value of $K$ in range $[0.9-1.1]\times10^{-4}\ \mathrm{m\cdot s^{-1}}$ | 0.2 |

## A.4 [0.8 pt]

**Official answer:** main forces: buoyancy $\frac43\pi a^3\rho_\ell g_0$, drag $6\pi\eta av$; weight negligible ($\frac{\rho_{\rm CO_2}}{\rho_\ell} = \frac{P_eM_{\rm CO_2}}{RT\rho_\ell}\approx10^{-3}$, $m_{\rm b}\ll m_\ell$). Balance $\frac43\pi a^3\rho_\ell g_0 = 6\pi\eta av$, so
$$v = \frac{2}{9\eta}a^2\rho_\ell g_0.$$
Time between two bubbles $\Delta t = 1/f_{\rm b}$. $\eta = \frac{2\rho_\ell g_0}{9}\times\frac{a^2}{v}$ for the penultimate bubble ($n-1$) with $a_{n-1}\approx0.19$ mm, $v(t_{n-1}) = \frac{z(t_n)-z(t_{n-2})}{2\times f_{\rm b}^{-1}} = 4.5\ \mathrm{cm\cdot s^{-1}}$:
$$\eta\approx2\times10^{-3}\ \mathrm{Pa\cdot s}.$$

| Step | Points |
|---|---|
| A.4.1. Expression of main forces (gravity force present or absent): fullmark | 0.1 |
| A.4.2. expression $v = \frac{2}{9\eta}a^2\rho_\ell g_0$ (full mark on this point with or without the gravity force) | 0.2 |
| A.4.3. taking account of the time during two positions $\Delta t = 1/f_{\rm b} = 5\times10^{-2}$ s | 0.1 |
| A.4.4. full mark for one coherent value of the radius measured on Fig.3. last bubble in $[0.20-0.30]$ mm; penultimate bubble: radius in $[0.16-0.24]$ mm; antepenultimate bubble: radius in $[0.14-0.22]$ mm | 0.1 |
| A.4.5. full mark for one coherent value of the velocity measured on Fig.3. last bubble $v\in[4.3, 4.8]\ \mathrm{cm\cdot s^{-1}}$; penultimate bubble $v\in[4.2, 4.6]\ \mathrm{cm\cdot s^{-1}}$; antepenultimate bubble $v\in[3.7-4.2]\ \mathrm{cm\cdot s^{-1}}$ | 0.1 |
| A.4.6. full mark for any value or $\eta$ in range $[1.0-4.0]\,10^{-3}$ Pa·s | 0.2 |

## A.5 [0.5 pt]

**Official answer:** $v = \frac{\mathrm dz}{\mathrm dt} = \frac{2\rho_\ell g_0}{9\eta}a^2$ and $\frac{\mathrm da}{\mathrm dt} = q_a$, so $\frac{\mathrm dz}{\mathrm da} = \frac{2\rho_\ell g_0}{9q_a\eta}a^2$; neglecting $a(z=0)$, $z = \frac{2\rho_\ell g_0}{27q_a\eta}a^3$, so
$$a_{H_\ell} = \left(\frac{27q_a\eta H_\ell}{2\rho_\ell g_0}\right)^{1/3} = 3.9\times10^{-4}\ \mathrm m\quad(\eta = 2.0\times10^{-3}\ \mathrm{Pa\cdot s}).$$

| Step | Points |
|---|---|
| A.5.1. $a_{H_\ell} = \left(\frac{27q_a\eta H_\ell}{2\rho_\ell g_0}\right)^{1/3}$ | 0.3 |
| A.5.2. full mark if $a_{H_\ell}\in[0.36-0.49]$ mm | 0.2 |

## A.6 [1.1 pt]

**Official answer:** bubbles reaching the surface per unit time: $N_{\rm b}f_{\rm b}$; volume of CO$_2$ released per unit time $\frac{\mathrm dV}{\mathrm dt} = \frac43\pi a_{H_\ell}^3N_{\rm b}f_{\rm b} = \frac{18\pi N_{\rm b}f_{\rm b}\eta H_\ell}{\rho_\ell g_0}q_a$ (using A.5), with $q_a = \frac{\mathrm da}{\mathrm dt} = \frac{RT_0}{P_0}K(c_\ell-c_0)$ (A.3). In the bubble $c_{\rm b}\approx c_0$; total number of CO$_2$ moles $n$ in $V_\ell$: $\frac{\mathrm dn}{\mathrm dt} = -\frac{P_0}{RT_0}\frac{\mathrm dV}{\mathrm dt} = -\frac{18\pi N_{\rm b}f_{\rm b}\eta KH_\ell}{\rho_\ell g_0}(c_\ell-c_0)$; with $c_\ell = n/V_\ell$:
$$\frac{\mathrm dc_\ell}{\mathrm dt} + \frac{18\pi N_{\rm b}f_{\rm b}\eta KH_\ell}{\rho_\ell g_0V_\ell}(c_\ell-c_0) = 0,\qquad \tau = \frac{\rho_\ell g_0V_\ell}{18\pi N_{\rm b}f_{\rm b}\eta KH_\ell}.$$

| Step | Points |
|---|---|
| A.6.1. Correct count of bubbles reaching the free surface by unit time: $N_{\rm b}f_{\rm b}$ | 0.1 |
| A.6.2. Balance at the free surface: $\frac{\mathrm dV}{\mathrm dt} = \frac43\pi a_{H_\ell}^3N_{\rm b}f_{\rm b}$ | 0.2 |
| A.6.3. Exact expression of $\frac{\mathrm dV}{\mathrm dt} = \frac{18\pi N_{\rm b}f_{\rm b}\eta H_\ell}{\rho_\ell g_0}q_a$ using A.5. | 0.1 |
| A.6.4. $q_a = \frac{\mathrm da}{\mathrm dt} = \frac{RT_0}{P_0}K(c_\ell-c_0)$ | 0.2 |
| A.6.5. First order linear differential equation $\frac{\mathrm dc_\ell}{\mathrm dt}+\frac{18\pi N_{\rm b}f_{\rm b}\eta KH_\ell}{\rho_\ell g_0V_\ell}(c_\ell-c_0) = 0$. If an homogeneous mistake has been made at a previous task, but the differential equation is first order and coherent, fullmark. | 0.3 |
| A.6.6. Exponential decay with characteristic time: $\tau = \frac{\rho_\ell g_0V_\ell}{18\pi N_{\rm b}f_{\rm b}\eta KH_\ell}$ full mark if the numerical coefficient is absent or different of $1/18\pi$ (reasonable solution) | 0.2 |

## B.1 [1.1 pt]

**Official answer:** system: the rim (perimeter $\ell = 2\pi r$) and the volume $\delta V = h\ell\,\mathrm dt = h2\pi rv_{\rm f}\mathrm dt$; kinetic energy gained $\mathrm dE_c = \frac12\rho_\ell\delta Vv_{\rm f}^2 = \frac12\rho_\ell h\ell v_{\rm f}\mathrm dt = \pi r\rho_\ell hv_{\rm f}\mathrm dt$ [sic, as printed; i.e. $\frac12\rho_\ell h\ell v_{\rm f}^3\mathrm dt$]. Surface energy $E_s = \sigma S$; $\delta E_s = -2\sigma\ell v_{\rm f}\mathrm dt = -4\sigma\pi rv_{\rm f}\mathrm dt$. Kinetic energy theorem with half the energy lost: $\mathrm dE_c + \delta E_s = \delta E_s/2$, so
$$v_{\rm f} = \sqrt{\frac{2\sigma}{\rho_\ell h}}.$$
If partial answer: $v_f = \sqrt{\sigma/\rho_\ell h}$ obtained only by dimensional analysis: 0.2 pt to the question.

| Step | Points |
|---|---|
| B.1.1. Any expression of kinetic energy | 0.1 |
| B.1.2. Variation of kinetic energy (differential or finite variation accepted) | 0.2 |
| B.1.3. Expression of a surface energy or a variation. | 0.1 |
| B.1.4. Exact expression of $\delta E_s$ | 0.3 |
| B.1.5. Kinetic energy balance (without sign mistake). If the candidate forget the energy loss, it is treated as a small mistake (-0.1pt) | 0.2 |
| B.1.6. exact expression of $v_f$ | 0.2 |

## B.2 [1.1 pt]

**Official answer:** $F_z = P(t)S - P_0S$; $V(t) = V_0 + Sz$; adiabatic reversible: $PV(t)^\gamma = P_0V_0^\gamma$, $P(t) = P_0\left(\frac{V_0}{V_0+Sz}\right)^\gamma = P_0\left(\frac{1}{1+Sz/V_0}\right)^\gamma\approx P_0\left(1-\gamma\frac{Sz}{V_0}\right)$; $F_z = -\gamma S^2P_0\frac{z}{V_0}$; $m_p\ddot z + \gamma S^2P_0\frac{z}{V_0} = 0$; $\omega_0^2 = S^2\frac{P_0\gamma}{m_pV_0}$:
$$f_0 = \frac1{2\pi}\sqrt{\frac{S^2P_0\gamma}{m_pV_0}}.$$

| Step | Points |
|---|---|
| B.2.1. Pressure force with $P_0$ | 0.1 |
| B.2.2. Expression of volume $V(t)$ | 0.1 |
| B.2.3. Expression of $P(t)$ with adiabatic reversible process for an ideal gas | 0.2 |
| B.2.4. Approximate pressure | 0.2 |
| B.2.5. Exact linearized pressure force | 0.1 |
| B.2.6. Law of motion | 0.1 |
| B.2.7. Harmonic oscillator, angular frequency | 0.2 |
| B.2.8. Expression of $f_0$ | 0.1 |

## B.3 [1.1 pt]

**Official answer:** maximal $f_0 = 40$ kHz is obtained for $r = r_c$. With $m = \frac{8r^3}{3}\rho_g$, $S = \pi r_c^2$, $V_0 = \frac43\pi a^3$:
$$f_0 = \frac1{2\pi}\sqrt{\frac{3r_c\pi^2P_0\gamma}{8\rho_gV_0}}\ \Rightarrow\ f_0 = \frac{1}{2\pi}\sqrt{\frac{\gamma P_0}{\rho_g}}\sqrt{\frac{3\sqrt3\pi}{16a}\sqrt{\frac{\rho_\ell g_0}{\sigma}}}\quad\text{or}\quad a = \frac{3\sqrt3}{64\pi}\frac{\gamma P_0}{\rho_gf_0^2}\sqrt{\frac{\rho_\ell g_0}{\sigma}},$$
$$a = 0.53\ \mathrm{mm}.$$
Then $r_c = \frac{2}{\sqrt3}a^2\sqrt{\frac{\rho_\ell g_0}{\sigma}}$ and $r_c = 0.15$ mm, so $v_f = \frac{r_c}{t_b} = 5.0\ \mathrm{m\cdot s^{-1}}$; $h = \frac{2\sigma}{\rho_\ell v_f^2} = \frac{3t_b^2}{2a^4}\sqrt{\frac{\sigma^3}{\rho_\ell^3g_0}}$:
$$h = 3.7\ \mu\mathrm m.$$

| Step | Points |
|---|---|
| B.3.1. Use of $r_c$ for $f_0$ | 0.1 |
| B.3.2. Exact expression of $f_0$ in terms of $a, \rho_g, \sigma, g_0, \rho_\ell, P_0$ or expression of $a$ | 0.3 |
| B.3.3. Exact numerical value between 0.5 mm and 0.6 mm | 0.2 |
| B.3.4. Relationship between $t_b$, $v_f$ and $r_c$ or $a$ | 0.2 |
| B.3.5. Expression of $h$ in terms of $\sigma,\rho_\ell$ and $v_f$ (or $a$ and $t_b$) | 0.1 |
| B.3.6. Numerical value $h = 3.7\ \mu$m | 0.2 |

## C.1 [0.4 pt]

**Official answer:** $n_T = n_V + n_L = n_V + k_H(T_0)P_iV_L$; $n_V = \frac{P_iV_G}{RT_0}$;
$$P_i = \frac{n_T}{V_Lk_H(T_0)+\frac{V_G}{RT_0}} = \frac{\frac{n_TRT_0}{V_G}}{1+RT_0k_H(T_0)\frac{V_L}{V_G}};\qquad P_i = 4.81\ \mathrm{bar}\ (6\,^\circ\mathrm C),\quad P_i = 7.76\ \mathrm{bar}\ (20\,^\circ\mathrm C).$$

| Step | Points |
|---|---|
| C.1.1. Conservation of CO$_2$ molecules | 0.1 |
| C.1.2. Litteral expression of $P_i$ | 0.1 |
| C.1.3. For $T_0 = 6$ °C: $P_i = 4.81$ bar | 0.1 |
| C.1.4. For $T_0 = 20$ °C: $P_i = 7.76$ bar | 0.1 |

## C.2 [0.7 pt]

**Official answer:** adiabatic reversible expansion from $P_i$ to $P_0$: $T_f = T_0\left(\frac{P_i}{P_0}\right)^{(1/\gamma)-1}$.
- $T_0 = 6$ °C: $P_i = 4.69$ bar, $T_f = 195.3\ \mathrm K = -77.8$ °C.
- $T_0 = 20$ °C: $P_i = 7.45$ bar, $T_f = 184.3\ \mathrm K = -88.8$ °C.

Comparison: $P_{\rm sat}^{\rm CO_2}(T_f, 6\,^\circ\mathrm C) = 1.07\ \mathrm{bar} > P_0$ → final CO$_2$ gaseous; $P_{\rm sat}^{\rm CO_2}(T_f, 20\,^\circ\mathrm C) = 0.41\ \mathrm{bar} < P_0$ → gaseous hypothesis inconsistent, phase transition (solid CO$_2$). (Equivalently $T_{\rm trans} = \frac{B}{A-\log_{10}(P_0/P_0)} - C = 194.4\ \mathrm K = -78.8$ °C; $195.3 > T_{\rm trans}$ at 6 °C, $184.3 < T_{\rm trans}$ at 20 °C.)
**True statements: 1 and 4.**

| Step | Points |
|---|---|
| C.2.1. Final pressure of the expansion. | 0.1 |
| C.2.2. Litteral expression of $T_f$. | 0.1 |
| C.2.3. For $T_0 = 6$ °C: $P_i = 4.69$ bar and $T_f = 195.3$ K; | 0.1 |
| C.2.4. For $T_0 = 20$ °C: $P_i = 7.45$ bar and $T_f = 184.3$ K; | 0.1 |
| C.2.5. Idea of comparison between $P_{\rm sat}$ and $P_0$ or evaluation of the transition temperature at $P_0$ and idea of comparison with $T_f$. | 0.1 |
| C.2.6. Numerical comparison. | 0.1 |
| C.2.7. True statements (all or nothing). | 0.1 |

## C.3 [1.3 pt] (official step points sum to 1.4 — see note at top)

**Official answer:** friction $\vec F = -\alpha\pi d(\ell_0 - z)\vec u_z$; initially it compensates the pressure force: $F = \pi\alpha d\ell_0 = \pi\frac{d^2}{4}(P_i-P_0)$, so $\alpha = (P_i-P_0)\frac{d}{4\ell_0}$; $\vec F = -(P_i-P_0)\pi d^2\frac{(\ell_0-z)}{4\ell_0}\vec u_z$; friction work $W_f = -\alpha\pi d\frac{\ell_0^2}{2} = -\frac{(P_i-P_0)\pi d^2}{8}\ell_0$.
Work of the internal gas (adiabatic): $\Delta U_g = \frac{n_VR}{\gamma-1}(T_f-T_0) = \frac{P_iV_G}{\gamma-1}\left(\frac{1}{\left(1+\frac{\pi d^2\ell_0}{4V_G}\right)^{\gamma-1}}-1\right)$, $W_{\rm CO_2\to cork} = -\Delta U_g = \frac{P_iV_G}{\gamma-1}\left(1-\frac{1}{\left(1+\frac{\pi d^2\ell_0}{4V_G}\right)^{(\gamma-1)}}\right)$ (or $\int_{V_G}^{V_F}P\,dV$ with $V_F = V_G+\frac{\pi d^2\ell_0}{4}$, $PV^\gamma = P_iV_G^\gamma$). External pressure work $W_e = -P_0\frac{\pi d^2}{4}\ell_0$. Energy balance: $E_c = -\Delta U_g + W_f + W_e$ (weight negligible). At $T_0 = 6$ °C: $P_i = 4.69$ bar, $W_f = -1.17$ J, $W_e = -0.64$ J, $\Delta U_g = -2.57$ J, $E_c = 0.76$ J;
$$H_c = \frac{E_c}{mg_0} = \frac{-\Delta U_g + W_f + W_e}{mg_0},\qquad H_c = 7.7\ \mathrm m.$$
(If $P_i$ is taken constant during the expansion, the work would be $P_i(\pi\ell_0d^2/4) = 3$ J instead of 2.56 J and $H_c = 12$ m — not negligible.)

| Step | Points |
|---|---|
| C.3.1. Correct expression of $\alpha$ (all or nothing). If $\alpha$ is not correct (contribution of $P_0$ forgotten for example), 0 point but the following items are evaluated with this uncorrect $\alpha$. | 0.2 |
| C.3.2. Expression of the friction work (all or nothing) | 0.2 |
| C.3.3. Consequences of the adiabatic reversible expansion (1st principle with $Q=0$ or $PV^\gamma = P_iV_G^\gamma$) | 0.1 |
| C.3.4. Exact expression of the work (all or nothing). *Partial points:* if $P$ is considered constant during the expansion, 0 point for C.3.4. but all points for the following items if coherent with the incorrect work expression. | 0.3 |
| C.3.5. Work due to external pressure correct. If this item is forgotten by the candidate, 0 point. | 0.1 |
| C.3.6. Correct $E_c$ with the 3 contributions (even if errors in the writing of the contributions). If the candidate has forgotten the contribution of the external pressure, 0 point. | 0.1 |
| C.3.7. Correct energy balance during the free flight or use of Newton's second law. | 0.2 |
| C.3.8. Correct numerical value of $H_c$. If the candidate has forgotten the contribution of the external pressure in C.3.5 but $H_c$ is coherent, fullmark. | 0.2 |
