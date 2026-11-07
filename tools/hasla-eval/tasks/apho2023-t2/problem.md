# APhO 2023 — Theoretical Problem 2: A ball on a turntable [10.0 points]

*Text-only version of the official English statement (23rd APhO, Mongolia 2023, "English (Official)"). Figures are described in words in "Figure description" blocks; everything else follows the official wording (including its spelling and the misprints marked [sic]).*

## Preamble

Notations and conventions: The length of a vector $\vec A$ is simply denoted as $A \equiv |\vec A|$. It's $x, y, z$ components are denoted by $A_x$, $A_y$, $A_z$, respectively. The time derivative of a quantity is denoted by the dot over the quantity: $\dot{\vec A} \equiv d\vec A/dt$, $\dot A \equiv dA/dt$. The unit vector along the direction of vector $\vec A$ is denoted as $\hat A$. The unit vectors along the Cartesian coordinates are, therefore, $\hat x$, $\hat y$ and $\hat z$. The definitions of scalar and vector products are:

$$(\vec A\cdot\vec B) = (\vec B\cdot\vec A) = A_xB_x + A_yB_y + A_zB_z = AB\cos\theta$$

$$(\vec A\times\vec B) = -(\vec B\times\vec A) = (A_yB_z - A_zB_y)\hat x + (A_zB_x - A_xB_z)\hat y + (A_xB_x - A_yB_x)\hat z \quad\text{[sic: the } \hat z \text{ component should read } (A_xB_y - A_yB_x)\text{]}$$

$$|\vec A\times\vec B| = AB\sin\theta,$$

where $\theta$ is the angle between $\vec A$ and $\vec B$. You may need the following properties of vectors and their multiplications. Triple product rules for vectors:

$$(\vec A\times\vec B)\times\vec C = (\vec A\cdot\vec C)\vec B - (\vec B\cdot\vec C)\vec A,$$
$$(\vec A\times\vec B)\cdot\vec C = (\vec B\times\vec C)\cdot\vec A = (\vec C\times\vec A)\cdot\vec B.$$

The vector products are very useful in describing many relations in physics. For example:

$$\vec v = \vec\omega\times\vec r,\qquad \vec F_{Lorentz} = Q\vec v\times\vec B,$$

and, often, saves time combining three equations for vector components into a single equation.

## The statement

> **Figure 1 description.** "Ball rolling on the turntable without slipping." Perspective view of a large horizontal circular turntable (a flat disk). A vertical axis labelled $\hat z$ (pointing up) passes through the centre of the disk. A curved arrow around the axis, labelled $\Omega$, shows the turntable rotating counter-clockwise when seen from above (i.e. its angular velocity is $\Omega\hat z$ with $\Omega > 0$ in the drawing). A grey ball of radius $r$ (radius drawn from the centre of the ball to its surface) rests on the disk away from the axis. The vector $\vec R$ is drawn horizontally from the rotation axis (at the height of the ball's centre) to the ball's centre; a dashed line on the disk joins the foot of the axis to the ball's contact point (the projection of $\vec R$ onto the disk).

A ball of mass $m$ and radius $r$ is rolling on a horizontal turntable without slipping (see Figure 1). Its mass density has a spherical symmetry, i.e. only depends on the distance from its center. The moment of inertia of the ball is $I$ . In part B and C, where the turntable can rotate freely, the moment of inertia of the turntable is denoted as $I_d$. The purpose of the problem is to analyze the motion and trajectory of the ball with respect to the laboratory frame. Throughout the problem, assume the turntable is large enough so that the ball does not fall off. The following notations are used:

- $\Omega$ - the magnitude of the turntable angular velocity,
- $\vec\omega$ - the spinning angular velocity of the ball with respect to its spinning axis,
- $\vec R$ - the horizontal position of the ball center with respect to the rotation axis of the turn table,
- $\vec v$ - the velocity of the ball at $\vec R$ with respect to the laboratory frame.

Assume that the initial position $\vec R_0 \equiv \vec R(0)$ and velocity $\vec v_0 \equiv \vec v(0)$ of the ball, the angular velocity of the turn table $\Omega_0 \equiv \Omega(0)$ are known. For the initial vector quantities $\vec R_0 \equiv \vec R(0)$ and $\vec v_0 \equiv \vec v(0)$, assume that their directions are known. In addition, whenever you need to express a vector quantity, you may use $\hat z$ in your expression. Also, if asked to write your expression in terms of the known quantity you may use any or all of $m$, $r$, $I$ and $I_d$. Unless otherwise stated, keep $I$ as general. The following notations are recommended:

$$\alpha = \frac{I}{I+mr^2},\qquad \delta = \frac{I_d}{mr^2},$$

You may write the final answers as vector expressions involving cross product (vector product), dot product (scalar product) and unit vectors in axis directions.

## Part A: Ball on turntable with constant angular velocity [1.5 points]

First we start with the simplest case wherein the turntable angular velocity with respect to vertical axis $\hat z$ is constant, therefore $\Omega = \Omega_0$.

**A.1 [0.1 pt]** Express the ball's velocity $\vec v$ in terms of $\Omega$, $\vec\omega$, $r$ and $\vec R$ from a kinematic constraint.

**A.2 [0.2 pt]** Using Newton's equation and torque equation with respect to its center, find the acceleration of the ball $\vec a \equiv \dot{\vec v}$ in terms of $\Omega$, $\vec v$, $r$, $m$ and $I$.

**A.3 [0.2 pt]** Find the velocity $\vec v$ in terms of $\Omega$, $\vec R$, $\vec v_0$, $\vec R_0$, $r$, $m$ and $I$.

**A.4 [0.5 pt]** Write an explicit solution for the trajectory of the ball given the initial conditions $\vec v_0$ and $\vec R_0$.

**A.5 [0.5 pt]** Assume this time that the ball has a uniform mass density, i.e. $I = 2mr^2/5$. Trajectory you have found is a circle and it's radius is $R_t$. Choose its magnitude to be the same as $R_0$. How long does it take for the ball to approach the initial spot on the table (the position on the turntable at $t=0$) with the closest distance?

## Part B: Ball on freely rotating turntable [4.0 points]

In this part, the turntable can rotate freely without any friction around $z$ -axis. Therefore its free rotation is hindered only by the ball's friction.

**B.1 [0.2 pt]** Find the velocity $\vec v$ and acceleration $\dot{\vec v}$ of the ball in terms of $\Omega$ , $\vec R$, $\Omega_0$, $\vec R_0$, $\dot\Omega$, $r$, $m$ and $I$.

**B.2 [0.6 pt]** Find the magnitude of the angular acceleration of the turntable $\dot\Omega$ in terms of $\Omega, \Omega_0, \vec R, \vec R_0, \vec v_0, r, m, I$ and $I_d$. You may use the constants $\alpha$ and $\delta$ defined in the beginning of the problem.

**B.3 [0.6 pt]** Find the magnitude of the angular velocity of the turntable $\Omega$ as a function of $R$ only. Use this constants in your expression: $\Omega_0, R_0, r, m, I, I_d$.

**B.4 [0.1 pt]** From the result of B.3, for a given $\Omega_0$, $R_0$, find the maximum possible $\Omega$ .

**B.5 [2.5 pt]** Write down the vertical component the angular momentum $\hat zM_z$ of the whole system. Subtract any constant term and rename the remaining part as $\hat zL$ .
In part B.1 you found the velocity of the ball $\vec v$, which can be written as the sum of a part that depends on the position of the ball $\vec R$ and a constant vector. Let us call this constant vector $\vec c$ . Choose the direction of $x$-axis along this vector and $y$-axis along $\hat z\times\vec c$ . In this frame of reference, find $\Omega$ in terms of $L, \vec R, \vec c, \hat z, R^2, r, m, I$ and $I_d$ . Combining this with the result of B.3, write down an equation only containing $R^2$ and $y$ variables and $L, r, m, I, c$ and $I_d$. Here $c$ is the magnitude of $\vec c$. Substituting $R^2 = x^2 + y^2$ , write down an expression containing only $x$ and $y$ variables and describing a curve. From this, list all possible types of trajectories.

## Part C: Ball on turntable in magnetic field [4.5 points]

In this part, we consider a density profile so that $I = mr^2/10$ . This can be realized, for example, if the ball is filled up to half of its radius with uniform density and the remaining part has a negligible mass. In addition, on its outer surface, the ball has a uniform charge density $Q/(4\pi r^2)$ , where $Q$ is the total surface charge. The whole setup is in a uniform magnetic field $\vec B$ that is in $\hat z$ direction. The turntable rotates with constant $\Omega$ like in Part A.

> **Figure 2 description.** "Ball rolling on the turntable in a constant magnetic field $\vec B$." The same drawing as Figure 1 (turntable, vertical axis $\hat z$, rotation arrow $\Omega$ counter-clockwise seen from above, ball of radius $r$, vector $\vec R$ from the axis to the ball's centre), with an additional vertical arrow labelled $\vec B$ pointing up (along $+\hat z$) drawn to the left of the axis.

**C.1 [0.5 pt]** Write down Newton's equation and the torque $\vec\tau_s$ equation for the ball. Find expression for the torque due to the spinning of the ball around its axis in terms of $Q, r, \vec\omega$ and $\vec B$ .

**C.2 [0.5 pt]** Using the results of C.1, find expression for the linear acceleration of the ball with respect to the laboratory frame in terms of $Q, r, \vec\omega$ and $\vec B$ .

**C.3 [1.0 pt]** We assume all quantities of unit lenght are measured by meter, all angular velocities have unit of $1$ Hertz, and all quantities of time have the unit of $1$ second. The equation for the linear acceleration you found in part C.2 is a second order differential equation for $\vec R$ of the following form:

$$\frac{d^2\vec R}{dt^2} - \gamma\frac{d\vec R}{dt}\times\hat z + \beta\vec R = 0.$$

Write down $\gamma$ and $\beta$ constants in terms of $Q, r, B, I, m, \Omega$. Make the following transformation to a polar coordinates for the components of $\vec R$ :

$$x(t) = \rho(t)\cos(\eta(t)),\qquad y(t) = \rho(t)\sin(\eta(t))$$

so that the new equations do not have the first time derivative term. Here the polar angle $\eta(t)$ is a function of time. Find the form of this function.
Express the coefficient $\beta'$ of $\rho(t)$ in the new equation in terms of $\gamma$ and $\beta$ .
Write down the conditions for different types of behavior of $\rho(t)$ with respect to time: harmonic, exponential etc.

**C.4 [0.9 pt]** Consider the following initial conditions for the solution found in part C.3:

$$x(0) = 1\,m,\quad y = 0\,m,\quad v_x(0) = \dot x|_{t=0} = 1\,m/s,\quad v_y(0) = \dot y|_{t=0} = -1\,m/s.$$

From these conditions, find $\beta$ and $\gamma$. Using them find the corresponding $\Omega$.
Sketch the trajectory. Is the charge of the surface negative or positive? For the negative write $-$ and for the positive write $+$ on your answer sheet.

*[Text version: describe the sketched trajectory in words (shape, sense of motion, how its size changes).]*

**C.5 [1.6 pt]** Consider the solution you have found in part C.4. If you identified it correctly your solution should have a rotating $\vec R(t)$. Find the expressions for the total and per rotation changes in energy for $N \gg 1$ number of rotations. Here you may ignore the terms small compared to $N$. In this part assume the mass and the radius of the ball are $m = 1\,kg$ and $r = 1\,m$ so that $I = 1/11\,kg\cdot m^2$.
