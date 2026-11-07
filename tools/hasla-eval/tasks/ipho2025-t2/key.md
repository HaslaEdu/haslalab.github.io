# IPhO 2025 T2 — Cox's Timepiece: official answers and marking scheme

**Task total: 10.0 points** (A: 1.3 = 0.2+0.8+0.3; B: 2.0 = 0.3+1.4+0.3; C: 6.7 = 1+1+2+1+1.7).

Source: official solution with embedded marking scheme, "Q2 … English (Official)", `IPhO_2025_S2.pdf` (each part: SOLUTION, then "MARKING SCHEME" table). Step descriptions are copied from the scheme; "*all or nothing*" annotations are official. Boxed/displayed results of the official solution are given as final answers.

---

## A.1 [0.2 pt]

**Official answer:** hydrostatics: $P_{\rm w} = P_{\rm a} - \rho gh = P_0 - \rho gh$. Equilibrium: $\vec 0 = m\vec g + (P_{\rm w}-P_0)S\,\vec u_z + \vec F$, so
$$\vec F = -(m+\rho Sh)\,\vec g = (m+\rho Sh)\,g\,\vec u_z.$$

| Step | Points |
|---|---|
| Expression of $P_{\rm w}$ (as a function of $P_{\rm a}$ or $P_0$) | 0.1 |
| Expression of $\vec F$ | 0.1 |

## A.2 [0.8 pt]

**Official answer:** $h^\star$ is the threshold at which saturated vapour appears: $P_{\rm w} = P_0 - \rho gh^\star = P_{\rm sat}(T_{\rm a})$, so $h^\star = \frac{P_0 - P_{\rm sat}(T_{\rm a})}{\rho g}$. If $h^\star > H$: behaviour A, otherwise B. With $F = (m+\rho Sh)g$: $F_{\max} = (m+\rho SH)g$ for A, $(m+\rho Sh^\star)g$ for B.

| Experiment | Behaviour | $h^\star$ (cm) | $F_{\max}$ (N) |
|---|---|---|---|
| 1 | A | — | 14.7 |
| 2 | A | — | 14.4 |
| 3 | B | 2.1 | 5.1 |

| Step | Points |
|---|---|
| All behaviours are correct (*all or nothing*): A/A/B | 0.2 |
| Experiment 1: Numerical value of $F_{\max}$ in $[14.6, 15]$ (N) | 0.1 |
| Experiment 2: Numerical value of $F_{\max}$ in $[14, 14.5]$ (N) | 0.1 |
| Experiment 3: Numerical value of $h^\star$ in $[2, 2.2]$ (cm) (0.1 pt if only literal expression is correct) | 0.2 |
| Experiment 3: Numerical value of $F_{\max}$ in $[5, 5.2]$ (N) (0.1 pt if only literal expression is correct) | 0.2 |

## A.3 [0.3 pt]

**Official answer:** behaviour B: $F_{\max} = mg + (P_0 - P_{\rm sat})S \simeq mg + P_0S$, so
$$\varepsilon = \frac{P_{\rm sat}}{P_0 + mg/S}\simeq1.6\times10^{-6}.$$

| Step | Points |
|---|---|
| Literal expression of $\varepsilon$ (with or without $P_{\rm sat}$ in denominator) | 0.2 |
| Numerical value of $\varepsilon$ in $[1, 2]\times10^{-6}$ | 0.1 |

## B.1 [0.3 pt] — [GRAPH/FIGURE-DEPENDENT]

**Official answer:** by the reasoning of part A, $m_{\rm add}$ corresponds to the liquid mass in the two-part tube which is **above the outside surface of the liquid bath** (from $z = 0$ up to $z_\ell$: the part of the narrow tube above the bath level plus the mercury in the bulb up to $z_\ell$).

| Step | Points |
|---|---|
| Coloring of the correct area (0.1 pt only if a correct expression of $m_{\rm add}$ is provided but the colored area is incorrect) | 0.3 |

*Grader note for text-only answers:* a precise verbal description of that volume is the equivalent of the coloured area.

## B.2 [1.4 pt] — [GRAPH/FIGURE-DEPENDENT]

**Official answer:** vapour (vacuum) appears when the column reaches $z_\ell^\star = \frac{P_0-P_{\rm sat}}{\rho g} = \frac{P_0}{\rho g} = 76$ cm. Graph of $m_{\rm add}(h_{\rm t})$, four straight pieces:
1. from $h_{\rm t} = -H_{\rm b}$ ($m_{\rm add}=0$) to $h_{\rm t} = 0$: slope $\rho S_{\rm b}$;
2. from $0$ to $z_\ell^\star - H_{\rm b}$ ($=56$ cm): slope $\rho S_{\rm t}$ (positive, smaller);
3. from $z_\ell^\star - H_{\rm b}$ to $z_\ell^\star$ ($=76$ cm): slope $-\rho(S_{\rm b}-S_{\rm t})$;
4. from $z_\ell^\star$ to $H_{\rm t}$: slope $0$.

Angular points at $h_{\rm t} = 0$, $\ z_\ell^\star - H_{\rm b} = \frac{P_0}{\rho g}-H_{\rm b}$, $\ z_\ell^\star = \frac{P_0}{\rho g}$.

| Step | Points |
|---|---|
| Qualitative aspect: Graph with 4 straight pieces (0.1pt only if there are 3 pieces; 0 else) | 0.2 |
| Qualitative aspect: For the 1st & 2nd pieces, the slopes are positive *and* the slope of 2nd piece is less than that of 1st (*all or nothing*) | 0.2 |
| Qualitative aspect: The 3rd piece has a negative slope | 0.2 |
| Qualitative aspect: The 4th piece has a null slope | 0.2 |
| Expressions of the two first slopes (*all or nothing*) | 0.1 |
| Expression of the negative slope | 0.2 |
| $h_{\rm t}$ analytical values of the 3 intermediate angular points (0.1pt per value) | 0.3 |

## B.3 [0.3 pt]

**Official answer:** $z_\ell(t) = \frac{P_{\rm a}(t)}{\rho g} = \frac{P_0}{\rho g}+\frac{P_1(t)}{\rho g} = \underbrace{h_{\rm t}+\frac{H_{\rm b}}2}_{z_{\ell,0}} + \frac{P_1(t)}{\rho g}$;
$m_{\rm add}(t) = \rho[S_{\rm t}h_{\rm t} + S_{\rm b}(z_\ell(t)-h_{\rm t})] = \rho[S_{\rm t}h_{\rm t}+S_{\rm b}(z_{\ell,0}-h_{\rm t})] + \frac{S_{\rm b}P_1(t)}{g}$, so
$$\Delta m_{\rm add} = \frac{S_{\rm b}A}{g}\simeq1\ \mathrm{kg}.$$

| Step | Points |
|---|---|
| Literal expression of $\Delta m_{\rm add}$ | 0.2 |
| Numerical value *with unit*, in $[1\ \mathrm{kg}, 1.1\ \mathrm{kg}]$ | 0.1 |

## C.1 [1 pt]

**Official answer:** with $M$ at rest at $x=0$, cable tensions are $[F_0 + m_{1,\rm tb}g]\vec u_x$ (right cable, tube) and $-[F_0+m_{1,\rm c}g]\vec u_x$ (left cable, cistern), with $m_{1,\rm tb} = -m_{1,\rm c}$ (mass conservation). Friction needed: $\vec R_{\rm t} = 2m_{1,\rm c}g\,\vec u_x$, $m_{1,\rm c} = \rho S_{\rm c}\delta_{\rm c}$. Hydrostatics $\delta_{\rm b}-\delta_{\rm c} = \frac{P_1}{\rho g}$; volume conservation $S_{\rm b}\delta_{\rm b} = -[S_{\rm c}-S_{\rm t}]\delta_{\rm c}\simeq -S_{\rm c}\delta_{\rm c}$. Hence $\delta_{\rm c} = -\frac{S_{\rm b}}{S_{\rm b}+S_{\rm c}-S_{\rm t}}\frac{P_1}{\rho g}$ and
$$\vec R_{\rm t} = -\frac{2S_{\rm b}S_{\rm c}}{S_{\rm b}+S_{\rm c}-S_{\rm t}}P_1\vec u_x\simeq-\frac{2S_{\rm b}S_{\rm c}}{S_{\rm b}+S_{\rm c}}P_1\vec u_x.$$
Maximum at $P_1 = \pm A$; Coulomb: $M$ stays at rest iff $\frac{2S_{\rm b}S_{\rm c}}{S_{\rm b}+S_{\rm c}-S_{\rm t}}A < F_{\rm s}$, i.e. $2 < \xi$:
$$\xi^\star = 2.$$

| Step | Points |
|---|---|
| Introduction of geometric parameters to locate the positions of the fluid surfaces in each vessel | 0.1 |
| Expression of mass or volume variation of fluid in at least one of the vessels, in terms of those geometric parameters (with or without using $S_{\rm t}\ll S_{\rm b},S_{\rm c}$) | 0.1 |
| Physical law: Conservation of the total mass/volume | 0.2 |
| Physical law: Expression of barometric difference of heights between the two surfaces | 0.2 |
| Physical law: Expression of the friction force at equilibrium (with or without using $S_{\rm t}\ll S_{\rm b},S_{\rm c}$) | 0.1 |
| Physical law: Use of Coulomb's law in sticky situation | 0.1 |
| Conclusion: Obtaining $\xi^\star$ | 0.2 |

## C.2 [1 pt]

**Official answer:** at fixed $P_0$, the height difference $\Delta z_{\ell,0} = P_0/\rho g$ is the same at $x=0$ and $x=X$, so $\delta_{\rm b} = \delta_{\rm c}$. Volume conservation: $(S_{\rm c}-S_{\rm t})\delta_{\rm c} - (S_{\rm c}+S_{\rm t})X + S_{\rm b}(\delta_{\rm b}+X) = 0$, i.e. $S_{\rm b}\delta_{\rm b} + (S_{\rm c}-S_{\rm t})\delta_{\rm c} = (S_{\rm c}-S_{\rm b}+S_{\rm t})X$, giving $\delta_{\rm b}=\delta_{\rm c} = \frac{S_{\rm c}-S_{\rm b}+S_{\rm t}}{S_{\rm b}+S_{\rm c}-S_{\rm t}}X$, and $m_{1,\rm c} = \rho S_{\rm c}(\delta_{\rm c}-X) = -\rho\frac{2S_{\rm c}(S_{\rm b}-S_{\rm t})}{S_{\rm c}+S_{\rm b}-S_{\rm t}}X\simeq-\frac{2S_{\rm b}S_{\rm c}}{S_{\rm b}+S_{\rm c}}\rho X$, $m_{1,\rm tb} = -m_{1,\rm c}$. Then $\vec T = (m_{1,\rm tb}-m_{1,\rm c})g\,\vec u_x = -2m_{1,\rm c}g\,\vec u_x$:
$$\vec T = \frac{4S_{\rm c}(S_{\rm b}-S_{\rm t})}{S_{\rm b}+S_{\rm c}-S_{\rm t}}\rho gX\,\vec u_x\simeq\frac{4S_{\rm b}S_{\rm c}}{S_{\rm b}+S_{\rm c}}\rho gX\,\vec u_x.$$

| Step | Points |
|---|---|
| Introduction of geometric parameters to locate the positions of the fluid surfaces in each vessel | 0.1 |
| Expressions of mass or volume variations of fluid in one of the vessels in terms of $X$ and those geometric parameters (with or without using $S_{\rm t}\ll S_{\rm b},S_{\rm c}$) | 0.3 |
| Physical law: Conservation of the total mass/volume | 0.2 |
| Physical law: Expression of barometric difference of heights between the two surfaces | 0.2 |
| Expression of the total tension force $\vec T$ (with or without using $S_{\rm t}\ll S_{\rm b},S_{\rm c}$) | 0.2 |

## C.3 [2 pt] — [GRAPH/FIGURE-DEPENDENT]

**Official answer:** for $\xi<\xi^\star$, $M$ starts to move right at some instant and is accelerated until blocked at $x = X$ (switch time negligible compared with $\tau_1$). Once at $x=X$: hydrostatics $\delta_{\rm b}-\delta_{\rm c} = \frac{P_1}{\rho g}$, volume $S_{\rm b}\delta_{\rm b}+(S_{\rm c}-S_{\rm t})\delta_{\rm c} = (S_{\rm c}-S_{\rm b}+S_{\rm t})X$, giving
$$\vec T = -2m_{1,\rm c}g\,\vec u_x = \left[\frac{4S_{\rm c}(S_{\rm b}-S_{\rm t})}{S_{\rm b}+S_{\rm c}-S_{\rm t}}\rho gX + \frac{2S_{\rm b}S_{\rm c}}{S_{\rm b}+S_{\rm c}-S_{\rm t}}P_1\right]\vec u_x.$$
$M$ stays at $x=X$ while $\vec T\cdot\vec u_x > -F_{\rm s}$; always satisfied if $\frac{4S_{\rm c}(S_{\rm b}-S_{\rm t})}{S_{\rm b}+S_{\rm c}-S_{\rm t}}\rho gX - \frac{2S_{\rm b}S_{\rm c}}{S_{\rm b}+S_{\rm c}-S_{\rm t}}A > -F_s$.
- **Regime 1: $\xi + 2\lambda > 2$** — once at $x=X$, $M$ stays indefinitely at rest. Graph: $x/X = 0$ until a single fast switch to $x/X = 1$ during the first rise of $P_1$ (before $t=\tau_1/4$), then $x/X = 1$ for all later times.
- **Regime 2: $\xi + 2\lambda < 2$** — once at $x = X$, $M$ periodically sweeps between the two stops. Graph: rectangular wave between $+1$ and $-1$ with period $\tau_1$ and 50% duty cycle in steady state; first switch $0\to1$ during the first quarter period; switches to $-1$ during each decrease of $P_1$ and back to $+1$ during each increase; the first step at $x = X$ lasts longer than the others.

| Step | Points |
|---|---|
| Expression for $\vec T$ in the general case, containing both $P_1$ and $X$ terms. | 0.2 |
| At least one inequality is correct (without considering strict or large) | 0.2 |
| Both inequalities are correct (without considering strict or large) | 0.1 |
| Global appearance of *both* graphs: one seems to show an aperiodic behaviour, the other a periodic behaviour (*all or nothing*) | 0.2 |
| Global appearance: each graph is in accordance with the correct sign of obtained inequality (focus on symbols > / <, without considering if the inequality is strict or large) | 0.2 |
| Either graph 1 or 2 shows: A first switch from $x=0$ to $x=X$ that begins somewhere in the interval $t\in\left(0,\frac{\tau_1}{4}\right]$ | 0.2 |
| Either graph 1 or 2 shows: The switch is instantaneous | 0.2 |
| Graph in aperiodic regime: $x = X$ for all times after the first switch | 0.1 |
| Graph in periodic regime: the behaviour is periodic with period $\tau_1$ (except for the first switch) | 0.1 |
| Graph in periodic regime: the positive and negative parts of the graph are similar | 0.2 |
| Graph in periodic regime: $x(t)/X$ is described by a rectangular function, of magnitude 1 and duty cycle 50% in steady state | 0.2 |
| Graph in periodic regime: the first step at $x=X$ last longer than others | 0.1 |

*Grader note for text-only answers:* graph items can be awarded only for an unambiguous verbal description of the corresponding feature.

## C.4 [1 pt]

**Official answer:** one motion to the left and one to the right per period, total length $4X$: $W = 4F_{\rm S}X$. Constraint $\xi+2\lambda\le2$, i.e. $\frac{2\rho gX}{A}+\frac{F_{\rm s}}{S_{\rm c}A}\le1$. Optimum on the limit $F_{\rm S} = S_{\rm c}(A-2\rho gX)$, $W = 4XS_{\rm c}(A-2\rho gX)$, maximal for
$$X^\star = \frac{A}{4\rho g},\qquad F_{\rm s}^\star = \frac{AS_{\rm c}}{2},\qquad W^\star = \frac{A^2S_{\rm c}}{2\rho g}\simeq20\ \mathrm{mJ}.$$

| Step | Points |
|---|---|
| Starting point: $W = 4F_{\rm s}X$ | 0.2 |
| Optimization: $\xi+2\lambda = 2$ or equivalent $F_{\rm s} = S_{\rm c}(A-2gX)$ [sic, as printed; $= S_{\rm c}(A-2\rho gX)$] | 0.3 |
| Expression of $X^\star$ | 0.1 |
| Expression of $F_{\rm s}^\star$ | 0.1 |
| Expression of $W^\star$ | 0.2 |
| Numerical value for $W^\star$ *with unit*: in $[19\ \mathrm{mJ}, 21\ \mathrm{mJ}]$ | 0.1 |

## C.5 [1.7 pt]

**Official answer:** $V(t) = V_0 + V_1(t)$ with $V_1 = m_{1,\rm c}/\rho$ (change of the liquid volume in the cistern); with $S_{\rm b}\simeq S_{\rm c}$, $S_{\rm t}$ neglected:
$$V_1(t) = -S_{\rm c}\left[x(t)+\frac{P_1(t)}{2\rho g}\right] = -S_{\rm c}X\left[\frac{x(t)}{X}+\frac1\lambda\frac{P_1(t)}{A}\right].$$
$W_{\rm pr} = \oint_{\rm 1\,period}-P_{\rm a}\,dV = -\oint_{\rm 1\,period}P_1\,dV_1$ = area of the cycle in the $(P_1,V_1)$ diagram. In the optimal case $M$ switches between $x = \pm X^\star$ when $P_1 = \pm A$; cycle of 2 iso-$x$ and 2 iso-$P$ transformations through the states

| State | $P_1$ | $x$ | $V_1$ |
|---|---|---|---|
| 1 | $A$ | $X^\star$ | $-3S_{\rm c}X^\star$ |
| 2 | $-A$ | $X^\star$ | $S_{\rm c}X^\star$ |
| 3 | $-A$ | $-X^\star$ | $3S_{\rm c}X^\star$ |
| 4 | $A$ | $-X^\star$ | $-S_{\rm c}X^\star$ |

(parallelogram 1→2→3→4→1, base $2S_{\rm c}X^\star$, height $2A$):
$$W_{\rm pr}^\star = 4S_{\rm c}X^\star A = \frac{S_{\rm c}A^2}{\rho g},\qquad \frac{W^\star}{W_{\rm pr}^\star} = \frac12.$$

| Step | Points |
|---|---|
| Physical analysis: In the optimal case, the mass $M$ switches between the two positions $x=\pm X$ when $P_1 = \pm A$ | 0.1 |
| Physical analysis: During a period, the system describes a cycle formed of 2 iso-$x$ and 2 iso-$P$ transformations (sketch of cycle, or a table or any other pertinent description) | 0.2 |
| Physical analysis: Correct sequence of the successive states and/or direction of the cycle using $x$ and $P$ | 0.2 |
| General expression of the volume of the system in an $(P,x)$ state: $V = -S_{\rm c}\left[x+\frac{P_1}{2\rho g}\right]+\mathrm{Cste}$ | 0.3 |
| Expressions of the volume in the 4 states of the cycle: $-3S_{\rm c}X^\star\to S_{\rm c}X^\star\to3S_{\rm c}X^\star\to-S_{\rm c}X^\star$ (*all or nothing*) | 0.2 |
| Method used to calculate the work of atmospheric pressure forces: $W_{\rm pr} = -\oint_{\rm 1\,period}P_{\rm a}\,dV$ (explicit integral or area of the cycle in $(P,V)$ diagram or other pertinent method) | 0.2 |
| Obtaining $W_{\rm pr}^\star = 4S_{\rm c}X^\star A = \frac{S_{\rm c}A^2}{\rho g}$ | 0.2 |
| Final result: $\frac{W^\star}{W_{\rm pr}^\star} = \frac12$ | 0.3 |
