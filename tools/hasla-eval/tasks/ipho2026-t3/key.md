# IPhO 2026 T3 — Chasing the absolute zero: official answers and marking scheme

**Task total: 10.0 points** (A: 0.2 + 0.6 + 0.2; B: 1.5 + 1.5; C: 0.2 + 1.5 + 0.8 + 2.0 + 1.5).

Sources: official marking scheme "PROBLEM T3 — 10 Points total" (`IPhO_2026_M3.pdf`) for the step points; official solution "SOLUTION T3 [10 pts]" (`IPhO_2026_S3.pdf`) for the final answers. Step descriptions are copied from the scheme (spelling lightly corrected).

---

## T3-A1 [0.2 pts]

**Official final answer:** $H = \dfrac{NIA}{V}$ (from $H\cdot 2\pi R = NI$, multiplying and dividing by $A = \pi r^2$, with $V = 2\pi R\,A$).

| Step | Points |
|---|---|
| Correctly uses Ampère circuital law | 0.1 |
| Writes correctly in terms of required variables | 0.1 |

## T3-A2 [0.6 pts]

**Official final answer:** $dW_{emf} = V H\,dB$ (from $\mathscr E + \mathscr E_{ind} \approx 0$, $dW_{emf} = \mathscr E\,dq = I\,d\Phi_B$, $\Phi_B = NAB$, so $dW_{emf} = NIA\,dB = VH\,dB$).

| Step | Points |
|---|---|
| Recognize EMF are opposite (no resistance) | 0.2 |
| Correctly uses Faraday law | 0.3 |
| Correct expression for work | 0.1 |
| *ALT:* if student knows answer already ($HdB$) | 0.6 |

## T3-A3 [0.2 pts]

**Official final answer:** $dW = \mu_0 V H\,dM$ (from $dB = \mu_0 dH + \mu_0 dM$: $dW_{emf} = \mu_0VH\,dH + \mu_0VH\,dM$).

| Step | Points |
|---|---|
| Differentiate relation | 0.1 |
| Substitute and get correct answer | 0.1 |

---

## T3-B1 [1.5 pts] — isothermal heat

**Official final answer:**
$$Q = -\mu_0\frac{nK}{T}\,\frac{H_f^2 - H_i^2}{2}$$

Official reasoning: $dU = dW + dQ = \mu_0VH\,dM + C\,dT$; $dU = C_M dT$, so $U$ depends only on $T$; isothermal $\Rightarrow dQ = -dW = -\mu_0 VH\,dM$; from the equation of state at constant $T$, $TV\,dM = nK\,dH$, so $dQ = -\mu_0\frac{nK}{T}H\,dH$; integrate from $H_i$ to $H_f$.

| Step | Points |
|---|---|
| Correctly states energy conservation with heat | 0.3 |
| Recognize that at constant $M$ the internal energy depends only on $T$ | 0.3 |
| Correctly understand isothermal relation between heat and magnetization | 0.3 |
| Relate heat to change in $H$ | 0.2 |
| Correctly get $Q$ | 0.4 |

## T3-B2 [1.5 pts] — adiabatic temperature change

**Official final answer:**
$$\Delta T = T_f - T_i = T_i\left(\sqrt{\frac{\lambda + \mu_0 K H_f^2}{\lambda + \mu_0 K H_i^2}} - 1\right)$$

Official reasoning: adiabatic $\Rightarrow dU = dW$: $\frac{n\lambda}{T^2}dT = \mu_0VH\,dM = \mu_0 V\frac{TMV}{nK}dM$; separate: $\frac{n\lambda}{T^3}dT = \mu_0\frac{V^2}{nK}M\,dM$; integrate: $\frac{n\lambda}{2}\left(\frac1{T_i^2}-\frac1{T_f^2}\right) = \mu_0\frac{V^2}{nK}\frac{M_f^2 - M_i^2}{2}$; with $M = nKH/(TV)$: $\frac{\lambda}{T_i^2} - \frac{\lambda}{T_f^2} = \mu_0 K\left(\frac{H_f^2}{T_f^2} - \frac{H_i^2}{T_i^2}\right)$, so $\frac{T_f^2}{T_i^2} = \frac{\lambda + \mu_0KH_f^2}{\lambda+\mu_0KH_i^2}$.

| Step | Points |
|---|---|
| Correctly understand adiabatic process (no heat exchange) | 0.5 |
| Correctly get differential relation between $dT$ and $dM$ | 0.3 |
| Separate variables correctly | 0.1 |
| Integrate correctly | 0.3 |
| Algebra done correctly | 0.3 |

---

## T3-C1 [0.2 pts] — `[GRAPH/FIGURE-DEPENDENT]` labels on the H–T diagram

**Official answer (from the solution's figure):** $T_c$ ($T_L$ in the solution figure) is the temperature of the left vertical segment $2\to3$; $T_h$ ($T_H$) is the temperature of the right vertical segment $4\to1$. $Q_c$ is absorbed (arrow into the cycle) during the isothermal process $2\to3$ at $T_c$; $Q_h$ is released (arrow out of the cycle) during the isothermal process $4\to1$ at $T_h$. (In the text-only version this can be answered in words.)

| Step | Points |
|---|---|
| Correctly label temperatures on graph | 0.1 |
| Specify heat flow portions in diagram | 0.1 |

## T3-C2 [1.5 pts]

**Official final answer:**
$$M_1 = \sqrt{M_2^2 - M_3^2 + M_4^2}$$

Official reasoning: Carnot $Q_c/Q_h = T_c/T_h$; $Q_c = Q_{2\to3} = \mu_0\frac{nK}{T_c}\frac{H_2^2 - H_3^2}{2}$, $Q_h = -Q_{4\to1} = \mu_0\frac{nK}{T_h}\frac{H_1^2 - H_4^2}{2}$ with $T_c = T_2 = T_3$, $T_h = T_4 = T_1$; hence $\frac{H_2^2 - H_3^2}{T_c^2} = \frac{H_1^2 - H_4^2}{T_h^2}$; with $M = nKH/(TV)$: $M_2^2 - M_3^2 = M_1^2 - M_4^2$.

| Step | Points |
|---|---|
| Correctly use conservation of energy (from previous work) to find heat with correct sign (0.2 each) | 0.4 |
| Identify correctly the temperatures of the vertices (0.1 each) | 0.4 |
| Use Carnot's relation to set up algebra | 0.3 |
| Simplify using equation of state | 0.3 |
| Get to correct final expression | 0.1 |

## T3-C3 [0.8 pts] — liquid helium after one cycle

**Official final answer:** $T_f = 0.99008\ \text{K}$ (i.e. $|\Delta T| = 9.92\times10^{-3}$ K).

Official reasoning: $Q_c = \mu_0\frac{nK}{T_c}\frac{H_2^2 - H_3^2}{2} = 1.29\times10^{-1}$ J (with $T_c = 1.00$ K); $|\Delta T|_{\text{helium}} = \dfrac{1.29\times10^{-1}\ \text{J}}{130\ \text{kg m}^{-3}\times10^{-3}\ \text{m}^3\times10^2\ \text{J kg}^{-1}\text{K}^{-1}} = \frac{1.29}{1.30}\times10^{-2}\ \text{K} = 9.92\times10^{-3}$ K; $T_f = 1.00\ \text{K} - 0.00992\ \text{K} = 0.99008$ K.

*Grader note (not part of the official text):* carrying unrounded values ($Q_c = 0.12935$ J) gives $|\Delta T| = 9.95\times10^{-3}$ K and $T_f = 0.99005$ K; both are inside the scheme's ±0.001 K tolerance.

| Step | Points |
|---|---|
| Equate change of energy of gas [helium] to heat | 0.1 |
| Use density and volume to calculate mass | 0.1 |
| Use heat relation to material refrigerator | 0.2 |
| Correctly calculate with physical parameters | 0.15 |
| Give numerical value of final temperature which is within 0.001 | 0.2 |
| Units correct | 0.05 |

## T3-C4 [2.0 pts] — cooling time at constant power

**Official final answer:**
$$t = \frac{C_cT_h}{P}\left(\ln\frac{T_0}{T} - \frac{T_0 - T}{T_h}\right)$$

Official reasoning: $dQ_c/dQ_h = T_c/T_h$ and $dQ_h = dW + dQ_c$, so $\frac{dW + dQ_c}{dQ_c} = -\frac{P\,dt}{C_c\,dT_c} + 1 = \frac{T_h}{T_c}$ with $dW = P\,dt$, $dQ_c = -C_c\,dT_c$; separate: $dt = -\frac{C_cT_h}{P}\left(\frac{dT_c}{T_c} - \frac{dT_c}{T_h}\right)$; integrate from $T_0$ to $T$.

| Step | Points |
|---|---|
| Write Carnot's equation in differential form (because non-linear) | 0.4 |
| Relation of power to work | 0.3 |
| Relate $dQ$ to $dT$ in magnetic material (sign is important) | 0.4 |
| Separate variables | 0.3 |
| Integrate with limits correctly | 0.3 |
| Final expression with logs | 0.3 |

## T3-C5 [1.5 pts] — overall COP

**Official final answer:**
$$\mathrm{COP} = \frac{Q_c}{W} = \left(\frac{T_h}{T_0 - T}\ln\frac{T_0}{T} - 1\right)^{-1}$$
(from $W = Pt = C_cT_h\ln\frac{T_0}{T} - Q_c$ and $Q_c = C_c(T_0 - T)$).

| Step | Points |
|---|---|
| Relate total work with power and time | 0.2 |
| Relate total heat with the temperature change for helium [the cooled body] | 0.2 |
| Replace in the formula for time of previous part | 0.6 |
| Use definition of COP properly | 0.3 |
| Get correct final expression | 0.2 |
