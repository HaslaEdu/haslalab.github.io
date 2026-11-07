# APhO 2023 T2 — A ball on a turntable: official answers and marking scheme

**Task total: 10.0 points** (A 1.5 + B 4.0 + C 4.5).

Sources: official marking scheme "Theoretical Problem 2: Ball on turntable — Q2 – Marking Scheme" (`APhO_2023_M2.pdf`) for the step points; official solution "A ball on a turntable (Enkhbat Tsedenbaljir)" (`APhO_2023_S2.pdf`) for the answers. Step descriptions are copied from the scheme (spelling kept). Equation numbers (n) refer to the official solution. Note: the problem text reproduced at the start of the official solution carries an older point split (e.g. B.5 3.1, C.4 1.5); the point values used here are those of the official statement and marking scheme, which agree with each other. Notation: $\alpha = I/(I+mr^2)$, $\delta = I_d/(mr^2)$.

---

## A.1 [0.1 pt]

**Official answer:** velocity of the ball relative to the turntable from non-slipping, $\vec v_b = \vec\omega\times(r\hat z)$, hence
$$\vec v = \Omega\hat z\times\vec R + \vec v_b = \Omega\hat z\times\vec R + \vec\omega\times\hat z\,r.$$

| Step | Points |
|---|---|
| Kinematic constraint from non-slipping condition | 0.1 |

## A.2 [0.2 pt]

**Official answer:** $\vec F = m\dot{\vec v}$, $\vec\tau = (-r\hat z)\times\vec F = I\,d\vec\omega/dt$; differentiating the constraint, $\dot{\vec v} = \Omega\hat z\times\vec v + \frac{d\vec\omega}{dt}\times(r\hat z) = \Omega\hat z\times\vec v - \frac{mr^2}{I}(\hat z\times\dot{\vec v})\times\hat z = \Omega\hat z\times\vec v - \frac{mr^2}{I}\dot{\vec v}$, so
$$\dot{\vec v} = \frac{\Omega}{1+mr^2/I}\,\hat z\times\vec v.$$

| Step | Points |
|---|---|
| Time derivative of the constraint equation | 0.1 |
| Expression for the linear acceleration of the ball | 0.1 |

## A.3 [0.2 pt]

**Official answer:** the motion is circular with angular velocity of the centre $\frac{\Omega}{1+mr^2/I}$; integrating,
$$\vec v - \vec v_0 = \frac{\Omega}{1+mr^2/I}\hat z\times(\vec R-\vec R_0),\qquad \vec v = \frac{\Omega}{1+mr^2/I}\hat z\times(\vec R-\vec R_0) + \vec v_0.$$

| Step | Points |
|---|---|
| Time integral of the acceleration with initial values | 0.1 |
| Velocity formula in terms of initial values | 0.1 |

## A.4 [0.5 pt]

**Official answer:** a circle with centre and radius
$$\vec R_c = \vec R_0 + \frac{1+mr^2/I}{\Omega}\hat z\times\vec v_0,\qquad R_t = |\vec R_0-\vec R_c| = \frac{1+mr^2/I}{\Omega}|\hat z\times\vec v| = \frac{1+mr^2/I}{\Omega}v_0,$$
traversed with angular velocity $\Omega/(1+mr^2/I)$ (i.e. $|\vec R(t)-\vec R_c| = R_t$).

| Step | Points |
|---|---|
| Identification of trajectory radius | 0.2 |
| Identification of the center of the trajectory | 0.3 |

## A.5 [0.5 pt]

**Official answer:** for $I = 2mr^2/5$ the angular velocity of the ball's centre is $\omega_c = \frac27\Omega$, and the time to return to the initial point on the turntable is in general
$$t = \frac{14\pi}{\Omega}.$$
Special case (as stated, $R_t = R_0$): the spot on the turntable can cross the ball's path before the turntable makes a full turn; equating the chord distances $2R_0\sin\left(\frac{\omega_ct}{2}\right) = 2R_t\sin\left(\frac{2\pi-\Omega t}{2}\right)$ gives
$$t = \frac{2\pi}{\omega_c+\Omega} = \frac{14\pi}{9\Omega}.$$

| Step | Points |
|---|---|
| Calculate the return time on the same spot in general | 0.2 |
| Calculate the return time on the same spot for spectial case | 0.3 |

---

## B.1 [0.2 pt]

**Official answer:** integrating the torque equation, $\vec\omega\times\hat z = \vec\omega_0\times\hat z - \frac{mr}{I}(\vec v-\vec v_0)$; with the non-slipping condition and $\vec v_0 = \Omega_0\hat z\times\vec R_0 + \vec\omega(0)\times\hat zr$:
$$\vec v = \frac{I}{I+mr^2}\hat z\times\left(\Omega\vec R - \Omega_0\vec R_0\right) + \vec v_0,\qquad \dot{\vec v} = \frac{I}{I+mr^2}\hat z\times\left(\dot\Omega(t)\vec R + \Omega\vec v\right).$$

| Step | Points |
|---|---|
| Velocity formula | 0.1 |
| Acceleration | 0.1 |

## B.2 [0.6 pt]

**Official answer:** torque equation of the turntable $I_d\dot\Omega\hat z = -m\vec R\times\dot{\vec v}$, giving $I_d\dot\Omega = -\frac{mI}{I+mr^2}\left(\dot\Omega R^2 + \Omega(\vec v\cdot\vec R)\right)$ with $\vec v\cdot\vec R = \left(\vec v_0 - \frac{I}{I+mr^2}\Omega_0\hat z\times\vec R_0\right)\cdot\vec R$; hence
$$\left(I_d + \frac{mI}{I+mr^2}R^2\right)\dot\Omega = -\frac{mI}{I+mr^2}\Omega\left(\vec v_0 - \frac{I}{I+mr^2}\Omega_0\hat z\times\vec R_0\right)\cdot\vec R,$$
$$\dot\Omega = -\frac{\alpha\Omega/r^2\,(\vec c\cdot\vec R)}{\delta + \alpha R^2/r^2},\qquad \vec c \equiv \vec v_0 - \alpha\Omega_0\hat z\times\vec R_0.$$

| Step | Points |
|---|---|
| Angular acceleration of the turntable with the ball's velocity dependency and coordinates | 0.3 |
| Angular acceleration of the turntable with the ball's coordinates dependency | 0.3 |

## B.3 [0.6 pt]

**Official answer:** $\vec v = \alpha\Omega\hat z\times\vec R + \vec c$, so $\vec v\cdot\vec R = \frac12\frac{d(\vec R\cdot\vec R)}{dt} = \vec R\cdot\vec c$; then $\frac{1}{\Omega}\frac{d\Omega}{dt} = -\frac12\frac{1}{\delta+\alpha R^2/r^2}\frac{d(\alpha R^2/r^2)}{dt}$, which integrates to
$$\Omega^2 = \Omega_0^2\,\frac{\delta + \alpha R_0^2/r^2}{\delta + \alpha R^2/r^2}.$$

| Step | Points |
|---|---|
| Find scalar product of coordinate and velocity | 0.3 |
| Integrate and obtain table's angular velocity depending on magnitude of position only | 0.3 |

## B.4 [0.1 pt]

**Official answer:** maximum when $R = 0$ (the ball crosses the centre of the turntable):
$$\Omega_{max} = \Omega_0\sqrt{1 + \frac{\alpha R_0^2}{\delta r^2}}.$$

| Step | Points |
|---|---|
| Maximum table's angular velocity | 0.1 |

## B.5 [2.5 pt]

**Official answer:**
$$M_z\hat z = I_d\Omega\hat z + m\vec R\times\vec v + I\omega_z\hat z;$$
$\omega_z$ is constant (no torque along $\hat z$ on the ball), so the conserved remainder is
$$L\hat z = I_d\Omega\hat z + m\vec R\times\vec v = I_d\Omega_0\hat z + m\vec R_0\times\vec v_0.$$
With $\vec R\times\vec v = -\alpha\Omega R^2\hat z + \vec R\times\vec c$ *(sign as printed in the official solution; the next line uses $+\alpha\Omega mR^2$)*: $L\hat z = I_d\Omega\hat z + \alpha\Omega mR^2\hat z + m\vec R\times\vec c$,
$$\Omega = \frac{L - m\hat z\cdot(\vec R\times\vec c)}{I_d + \alpha mR^2};\qquad x\text{ along }\hat c,\ y\text{ along }\hat z\times\hat c:\quad \Omega = \frac{L/mr^2 + cy/r^2}{\delta + \alpha R^2/r^2}.$$
Combining with B.3:
$$\Omega_0^2\,\frac{\delta+\alpha R_0^2/r^2}{\delta+\alpha R^2/r^2} = \left(\frac{L/mr^2 + cy/r^2}{\delta+\alpha R^2/r^2}\right)^2,\qquad \Omega_0^2\left(\delta + \alpha R_0^2/r^2\right)\left(\delta+\alpha R^2/r^2\right) = \left(L/mr^2 + cy/r^2\right)^2,$$
a conic section. With $k \equiv \Omega_0^2(\delta r^2 + \alpha R_0^2)$, $\lambda \equiv L/m$, the official solution writes
$$k\alpha\left(\delta r^2 + \alpha(x^2+y^2)\right) - \left(\lambda^2 + 2\lambda cy + c^2y^2\right) = 0,\qquad k\alpha^2x^2 + (k\alpha^2 - c^2)y^2 - 2\lambda cy = \lambda^2 - k\alpha\delta r^2.$$
Since $k\alpha^2 > 0$ the trajectory type is set by the sign of $k\alpha^2 - c^2$: **ellipse** if $k\alpha^2 > c^2$; **parabola** if $k\alpha^2 = c^2$; **hyperbola** if $k\alpha^2 < c^2$.

*(Grader note, not official: multiplying the previous equation by $r^4$ gives $k(\delta r^2 + \alpha(x^2+y^2)) = (\lambda + cy)^2$, i.e. without the extra factor $\alpha$ printed in the official eq. (65); the curve is then $k\alpha x^2 + (k\alpha - c^2)y^2 - 2\lambda cy = \lambda^2 - k\delta r^2$, and the criterion reads ellipse/parabola/hyperbola for $k\alpha \gtrless c^2$. The list of possible trajectories — ellipse (circle as special case), parabola, hyperbola — is the same.)*

| Step | Points |
|---|---|
| Calculate table's angular velocity using conservation of angular momentum | 0.5 |
| Calculate table's angular velocity in the given coordinates | 0.5 |
| Find the equation for the curve | 0.9 |
| List the possible trajectories | 0.6 |

*(In the English scheme the first description wraps onto a second line, so the four marks 0.5, 0.5, 0.9, 0.6 are visually offset from the descriptions; the assignment above is the one given explicitly, line by line, in the official Korean translation of the scheme (`APhO_2023_T2_M_KO.pdf`). Sum = 2.5.)*

---

## C.1 [0.5 pt]

**Official answer:**
$$m\dot{\vec v} = \vec F_f + Q\vec v\times\vec B,\qquad I\dot{\vec\omega} = -r\hat z\times\vec F_f + \vec\tau_s,$$
where the torque due to the spinning of the charged sphere (surface density $\rho = Q/4\pi r^2$) is
$$\vec\tau_s = \int d\cos\theta\,d\phi\,\rho\,\vec r\times\left((\vec\omega\times\vec r)\times\vec B\right) = \rho Br^4\,\vec\omega\times\hat z\int_{-1}^{1}d\cos\theta\,\cos^2\theta\int_0^{2\pi}d\phi = \frac{Qr^2}{3}\vec\omega\times\vec B.$$

| Step | Points |
|---|---|
| Newton's equation | 0.2 |
| Spinning torque due to magnetic field | 0.3 |

## C.2 [0.5 pt]

**Official answer:** with $\vec v = \Omega\hat z\times\vec R + \vec\omega\times\hat zr$, $\dot{\vec v} = \Omega\hat z\times\vec v + \dot{\vec\omega}\times\hat zr$ (so $\dot{\vec\omega}r = \Omega\vec v - \dot{\vec v}\times\hat z$):
$$I\dot{\vec\omega} = -r\hat z\times\left(m\dot{\vec v} - Q\vec v\times\vec B\right) + \frac{Qr^2}{3}\vec\omega\times\vec B,$$
$$\left(I+mr^2\right)\dot{\vec v} = \left(\frac{4Qr^2B}{3} - I\Omega\right)\vec v\times\hat z - \frac{Qr^2B}{3}\Omega\vec R,$$
i.e. $\dfrac{d^2\vec R}{dt^2} - \gamma\dfrac{d\vec R}{dt}\times\hat z + \beta\vec R = 0$.

| Step | Points |
|---|---|
| Acceleration formula including spinning of the ball | 0.2 |
| Acceleration formula and 2nd order diff equation | 0.3 |

## C.3 [1.0 pt]

**Official answer:**
$$\beta \equiv \frac{Qr^2B}{3(I+mr^2)},\qquad \gamma \equiv \frac{4Qr^2B - 3I\Omega}{3(I+mr^2)} = \frac{4\beta}{\Omega} - \alpha\Omega.$$
*(Grader note, not official: from the official eq. (84) the coefficient of $\vec R$ is $\beta = \frac{Qr^2B\,\Omega}{3(I+mr^2)}$; with this $\beta$ the official relation $\gamma = 4\beta/\Omega - \alpha\Omega$ and the C.4 result for $\Omega$ hold. Eq. (86) as printed omits the factor $\Omega$.)*
Components (unitless): $\ddot x - \gamma\dot y + \beta x = 0$, $\ddot y + \gamma\dot x + \beta y = 0$. Substituting $x = \rho\cos\eta$, $y = \rho\sin\eta$:
$$\ddot\rho + (\beta - \gamma\dot\eta - \dot\eta^2)\rho = 0,\qquad \dot\rho(\gamma + 2\dot\eta) = 0,$$
$$\eta = -\frac{\gamma}{2}t + \phi,\qquad \beta' \equiv \beta - \gamma\dot\eta - \dot\eta^2 = \beta + \frac{\gamma^2}{4}.$$
For $\ddot\rho + \beta'\rho = 0$: $\beta' > 0$ harmonic oscillation; $\beta' < 0$ exponential run away; $\beta' = 0$ (linear in time; examined in C.4).

| Step | Points |
|---|---|
| Transformation to polar system removing the first time | 0.5 |
| Identification of angle function and beta' | 0.3 |
| Classification of time behavior of rho(t) | 0.2 |

## C.4 [0.9 pt]

**Official answer:** the case $\beta' = 0$, $\beta = -\gamma^2/4$, $\ddot\rho = 0$, $\rho = A + Dt$. From the initial conditions:
$$A = 1,\quad D = 1,\quad \gamma = 2,\quad \beta = -1;\qquad x(t) = (1+t)\cos t,\quad y(t) = -(1+t)\sin t,\quad R^2 = (1+t)^2.$$
From the definitions of $\beta$ and $\gamma$ (with $\alpha = 1/11$):
$$\Omega = -11 \pm \sqrt{77}.$$
Trajectory: an Archimedean-type spiral $\rho = 1 + t$ starting at $(1,0)$ and winding outward **clockwise** (seen from $+\hat z$), one turn per $2\pi$ s, the distance from the axis growing by $2\pi$ m per turn (the official sketch shows this spiral with about three turns, reaching $|x|,|y| \approx 15$–$20$).
Charge sign (official): "Since the both solutions for $\Omega < 0$ and $B > 0$ ($\vec B$ is in $\hat z$ direction), from $\beta < 0$ we see that $Q < 0$" — answer **$-$**.
*(Grader note, not official: with $\beta = Qr^2B\Omega/(3(I+mr^2))$ as implied by eq. (84), $\beta < 0$ with $\Omega < 0$, $B > 0$ would give $Q > 0$; the official answer "$-$" follows from eq. (86), which omits $\Omega$. The official scheme awards 0.1 for "Identify the charge sign".)*

| Step | Points |
|---|---|
| Identification of the curve from the initial condition | 0.5 |
| Find angular velocity of the table | 0.3 |
| Identify the charge sign | 0.1 |

## C.5 [1.6 pt]

**Official answer:** $\vec R$ makes one revolution every $t = 2\pi$; after $N \gg 1$ rotations $R^2 = (1+t)^2 \approx t^2$, $R \approx t$, $\Delta R = \Delta t = 2\pi$ per rotation.
Linear motion: $\vec v\cdot\dot{\vec v} = -\beta\vec v\cdot\vec R \Rightarrow v^2 - v_0^2 = -\beta(R^2 - R_0^2) = t^2$;
$$\Delta K = \frac{v^2 - v_0^2}{2} = \left(\frac{R^2 - R_0^2}{2}\right) = \frac{t^2}{2},\qquad \Delta K_N = \frac{v_{N+1}^2 - v_N^2}{2} = \Delta\left(\frac{R^2}{2}\right) = t\Delta t = 4\pi^2N.$$
Spinning: from non-slipping $\omega^2 = v^2 + \Omega^2R^2 + 2\Omega\vec v\cdot(\hat z\times\vec R)$; for large $N$, $\vec v\cdot(\hat z\times\vec R) = -vR$ and with $\Omega < 0$ this term is $|\Omega|vR$:
$$K_s = \frac{I\omega^2}{2} = \frac{I(v^2 + \Omega^2R^2 + 2|\Omega|vR)}{2},\qquad \Delta K_s = \frac{I\left((v^2 - v_0^2) + \Omega^2(R^2 - R_0^2) + 2|\Omega|(vR - v_0R_0)\right)}{2}.$$
Totals (official):
$$\Delta E = \frac{I(\omega^2 - \omega_0^2)}{2} + \Delta K \simeq \frac{I(v^2 + \Omega^2R^2 + 2|\Omega|vR)}{2} + \frac{t^2}{2} = \frac{t^2}{2}\left(\frac{(1+|\Omega|)^2}{11} + 1\right),$$
$$\Delta E_N = \frac{I(\omega_N^2 - \omega_{N-1}^2)}{2} + \Delta K_N = 4\pi N\left(\frac{(1+|\Omega|)^2}{11} + 1\right),\qquad |\Omega| = |11 \pm \sqrt{77}|.$$
*(Grader note, not official: the official per-rotation linear term is $4\pi^2N$ (eq. 108) while the final eq. (115) prints the prefactor $4\pi N$; $\Delta(t^2/2) = t\,\Delta t$ with $t \approx 2\pi N$, $\Delta t = 2\pi$ gives $4\pi^2N$. Also, the statement says $I = 1/11$ kg·m² although $I = mr^2/10 = 1/10$ for $m = r = 1$; the factor $1/11$ in the official result is used as given.)*

| Step | Points |
|---|---|
| Calculation of the total kinetic energy change from linear motion | 0.4 |
| Calculation of the kinetic energy change from linear motion per revolution | 0.4 |
| Calculation of the total kinetic energy change from spinning | 0.3 |
| Calculation of the kinetic energy change from spinning per revolution | 0.3 |
| Total energy change | 0.2 |
