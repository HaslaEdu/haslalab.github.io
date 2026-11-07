# IPhO 2026 T2 — Cooking with sunlight?: official answers and marking scheme

**Task total: 10.0 points** (A1 1.5; B1 2.0 + B2 1.5 + B3 0.5; C1 0.5 + C2 2.0 + C3 1.0 + C4 1.0).

Sources: official marking scheme "PROBLEM T2 — 10 Points total" (`IPhO_2026_M2.pdf`) for the step points; official solution "SOLUTION T2 [10 pts]. Cooking with sunlight?" (`IPhO_2026_S2.pdf`) for the final answers. Step descriptions are copied from the scheme (spelling lightly corrected). The scheme labels part A1 simply as "A".

---

## T2-A1 [1.5 pts] — Multiple reflections

**Official final answer:**
$$x_N = R\sin\left(\frac{2N-1}{4N+2}\pi\right) = R\cos\left(\frac{\pi}{2N+1}\right)$$
(e.g. $x_1 = R\sin\frac{\pi}{6} = \frac R2$, $x_2 = R\sin\frac{3\pi}{10} = \frac{1+\sqrt5}{4}R \approx 0.8R$, $x_3 = R\sin\frac{5\pi}{14}\approx 0.9R$.)

Official reasoning (summary): the limiting ray for $N$ reflections leaves the mirror exactly through the edge point $(-R,0)$. Its path forms $N$ isosceles triangles with common sides and base angle $\theta_N$ (the angle of incidence), i.e. half of a regular $(2N+1)$-gon; summing angles, $(2N\theta_N+\pi) + (\frac\pi2+\theta_N) = (N+1)\pi$, so $\theta_N = \frac{2N-1}{4N+2}\pi$ and $x_N = R\sin\theta_N$.

| Step | Points |
|---|---|
| Correctly identifies critical conditions | 1.0 |
| Does algebra correctly (has correct expression in terms of $R$, $N$) | 0.5 |
| *Partial solution (instead of the 1.0 above, if the general critical condition is not found):* critical condition only for 1 reflection | 0.3 |
| *Partial:* critical condition only for 2 and 3 reflections | 0.6 |
| *Partial:* critical condition only for 2 and 3 and 4 reflections | 1.0 |

---

## T2-B1 [2.0 pts] — container radius

**Official final answer:** $\alpha = R$, $\beta = -\dfrac R2$, i.e. $a = R\sin\theta_{\max} - \dfrac R2\sin(2\theta_{\max})$.

Official reasoning (summary): in the limiting case the reflected ray from $B$ (incidence angle $\theta_{\max}$) is tangent to the container at $C$ and crosses the $y$ axis at $D$. Triangle $ODB$ is isosceles, $\angle ODB = \pi - 2\theta_{\max}$, $\overline{OD} = \frac{R}{2\cos\theta_{\max}}$; triangle $O_cDC$ is right-angled, so $a = \overline{O_cD}\sin(\pi-2\theta_{\max}) = \left(\frac{R}{2\cos\theta_{\max}} - \frac R2\right)\sin(2\theta_{\max})$.

| Step | Points |
|---|---|
| Correctly understand angles of reflection | 0.3 |
| Correctly understands relation to geometry of container center line | 0.5 |
| Correctly understands tangential condition | 0.2 |
| Use triangles in image to compute | 0.5 |
| Do trigonometric correctly | 0.5 |

---

## T2-B2 [1.5 pts] — power ratio

**Official final answer:**
$$\frac{P}{P_0} = \frac{1}{1-\cos\theta_{\max}}$$
(Accepted alternative in terms of $\alpha,\beta$ from the given expression: $\dfrac{P}{P_0} = \dfrac{R}{\alpha + 2\beta\cos\theta_{\max}}$.)

Official reasoning: $P_0 = 2Ial$ ($I$ = intensity, $l$ = cylinder length); with the mirror $P = 2I\,\overline{OA}\,l = 2IRl\sin\theta_{\max}$ (all rays with $|x| \le R\sin\theta_{\max}$ reach the container); divide and use B1.

| Step | Points |
|---|---|
| Correctly computes $P_0$ | 0.3 |
| Understands flux flow | 0.7 |
| Correctly computes $P$ | 0.3 |
| Expressed correctly in terms of required data | 0.2 |

---

## T2-B3 [0.5 pts] — numerical container radius

**Official final answer:** $a = 12\ \text{cm}$ ($\cos\theta_{\max} = 4/5$, $\sin\theta_{\max} = 3/5$, $a = (1\,\text{m})\frac35\left(1-\frac45\right)$).
(Accepted alternative parametrised in terms of $\alpha$ and $\beta$: $a = -\dfrac{R\sqrt{100\beta^2-(R-5\alpha)^2}}{50\beta}$.)

| Step | Points |
|---|---|
| Utilize previous result correctly to compute $\theta_{\max}$ | 0.3 |
| Calculate $a$ for specific case | 0.15 |
| Correct units | 0.05 |

---

## T2-C1 [0.5 pts] — reflected ray $A$

**Official final answer:**
$$m_A = \cot(2\theta), \qquad b_A = \frac{R}{2\cos\theta}$$
(equivalent: $m_A = \frac{1}{\tan 2\theta} = \frac{\cot\theta}{2} - \frac{\tan\theta}{2}$, $b_A = \frac R2\sec\theta$). The reflected ray makes angle $2\theta$ with the vertical; it meets the $y$ axis at $C$ with $\overline{OC} = b_A$, and the isosceles triangle $OBC$ gives $\cos\theta = R/(2b_A)$.

| Step | Points |
|---|---|
| Slope correct | 0.3 |
| Intercept correct | 0.2 |

---

## T2-C2 [2.0 pts] — reflected ray $B$ to first order

**Official final answer:**
$$m_B = \cot(2\theta) - 2\csc^2(2\theta)\,\Delta\theta, \qquad b_B = \frac R2\sec(\theta)\,\bigl(1+\tan(\theta)\,\Delta\theta\bigr)$$
(equivalent: $m_B = \frac12\csc^2(2\theta)\,(\sin 4\theta - 4\Delta\theta)$; $b_B = \frac{R}{2\cos\theta}(1+\tan\theta\,\Delta\theta)$.)

| Step | Points |
|---|---|
| Do second slope correctly with small increment in angle | 0.2 |
| Correctly expand slope to first order | 0.8 |
| Do second intercept correctly with small increment in angle | 0.2 |
| Correctly get height [intercept] to first order | 0.8 |

---

## T2-C3 [1.0 pts] — intersection point (caustic)

**Official final answer:**
$$X_c = R\sin^3\theta, \qquad Y_c = \frac R2\cos\theta\,\bigl(2-\cos 2\theta\bigr)$$
(equivalent: $Y_c = \frac R4(3\cos\theta - \cos 3\theta) = \frac R4(3\cos\theta - \cos^3\theta + 3\sin^2\theta\cos\theta)$). From $X_c = -\frac{b_A-b_B}{m_A-m_B}$, $Y_c = \frac{m_Ab_B - b_Am_B}{m_A-m_B}$.

| Step | Points |
|---|---|
| Setup problem correctly (equations of lines) | 0.2 |
| Solve linear algebra correctly | 0.8 |
| *Alternative solutions using calculus are also valid.* | |

---

## T2-C4 [1.0 pts] — cusp shape

**Official final answer:**
$$v = \frac34 R^{1/3}, \qquad u = \frac R2, \qquad p = 2,\ q = 3\ \ (p/q = 2/3)$$
i.e. $Y_c = \frac R2 + \frac{3R}{4}\left(\frac{X_c}{R}\right)^{2/3}$ (for $\theta\ll1$: $X_c \approx R\theta^3$, $Y_c \approx \frac R2 + \frac{3R}{4}\theta^2$). The cusp tip is at $y = R/2$.

| Step | Points |
|---|---|
| Notice that it is a small angle problem | 0.1 |
| Correctly expand to second order | 0.3 |
| Write angle in terms of $x_c$ | 0.2 |
| Identify $p/q$ correctly | 0.2 |
| Identify $u$ correctly | 0.1 |
| Identify $v$ correctly | 0.1 |
| *ALT for $u$:* focus point of mirror without expansions | 0.2 |
| *Scheme note:* "If not made explicit by student that it is small angle problem, it is implicit by focus and needs to be added." | |
