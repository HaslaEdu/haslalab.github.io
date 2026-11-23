---
title_ko: 에너지 보존
title_en: Conservation of energy
unit: mechanics/energy
level: 3
order: 1
summary: Start from the work-energy theorem, define potential energy, and write energy conservation with and without friction.
---

## Work and kinetic energy

When a force $F$ moves a body a distance $\Delta x$ along the force, the work done by the force is $W = F\,\Delta x$. If the force changes with position, add it up over short pieces.

$$ W = \int_{x_0}^{x} F\, dx $$ {#work}

Work has a sign. A force opposite to the motion does negative work. A force perpendicular to the motion does no work.

Call $W_{\text{net}}$ the work done by the resultant of all the forces on the body. It equals the change in the kinetic energy $K = \frac{1}{2} m v^2$.

$$ W_{\text{net}} = \frac{1}{2} m v^2 - \frac{1}{2} m v_0^2 = \Delta K $$ {#wk}

:::derivation The work-energy theorem
Put Newton's second law $F = m\,dv/dt$ into [@work] and use $dx = v\,dt$.

$$ \begin{aligned} W &= \int m \frac{dv}{dt}\, dx = \int m \frac{dv}{dt}\, v\, dt \\ &= \int_{v_0}^{v} m v\, dv = \frac{1}{2} m v^2 - \frac{1}{2} m v_0^2 \end{aligned} $$

Here $F$ is the resultant force. The work of one force alone does not tell you the change in kinetic energy.
:::

## Conservative forces and potential energy

A force whose work depends only on the starting and finishing positions, like gravity or a spring, is called **conservative**. For a conservative force we can define a potential energy $U$: the work done by the force is the decrease in $U$.

$$ W_{\text{cons}} = -\Delta U $$ {#wu}

With up as $+$, gravity is $-mg$, so while the height changes from $y_0$ to $y$ it does work $-mg(y - y_0)$. The spring force $-kx$ does work $-\frac{1}{2}k(x^2 - x_0^2)$, from [@work]. So

$$ U_{\text{grav}} = m g y, \qquad U_{\text{spring}} = \frac{1}{2} k x^2 $$ {#u}

where the spring's $x$ is how far it is stretched or compressed.

:::remark
You may put the zero of potential energy wherever you like. Whether $y = 0$ is the floor or the desk top, only the difference $\Delta U$ enters the equations, so the answer is the same.
:::

:::why Why does the work of gravity not depend on the path?
Cut the path into very short pieces. On each piece gravity does (gravity) $\times$ (vertical distance moved on that piece). Sideways motion is perpendicular to gravity and gets no work. Adding all the pieces leaves only $-mg\,\Delta y$, whether the path is curved or straight. Friction is different. On every piece it points against the motion, so between the same two points a longer route collects more negative work. That is why friction has no potential energy.
:::

## Conservation of mechanical energy

If only conservative forces do work, [@wk] and [@wu] give $\Delta K = -\Delta U$. The sum of kinetic and potential energy, the mechanical energy $E = K + U$, stays the same.

$$ \frac{1}{2} m v_0^2 + U_0 = \frac{1}{2} m v^2 + U $$ {#cons}

If a non-conservative force such as friction does work $W_{\text{nc}}$, the mechanical energy changes by that amount.

$$ \Delta K + \Delta U = W_{\text{nc}} $$ {#nc}

For kinetic friction of size $\mu N$ over a sliding distance $d$, $W_{\text{nc}} = -\mu N d$. The mechanical energy lost becomes heat in the body and the floor. The total energy is still conserved.

:::result
- If only conservative forces do work, $K + U$ is constant.
- If other forces do work, $\Delta(K + U) = W_{\text{nc}}$.
- These equations look only at the start and the end. You can find a speed without knowing how the forces changed in between or what shape the path had.
:::

:::example A slide and a rough floor
As in [@track], a body starts from rest at height $h = 1.8\ \mathrm{m}$, slides down a frictionless curved track, then slides along a level floor with coefficient of kinetic friction $\mu = 0.3$ until it stops. Take $g = 9.8\ \mathrm{m/s^2}$.

![A body comes down a frictionless curve from height $h$, then slides a distance $d$ on a rough floor and stops.](fig/energy-track.svg){#track}

**(a) Speed at the bottom of the curve.** On the curve the normal force is perpendicular to the motion and does no work, so only gravity does work. With the floor at $y = 0$, [@cons] gives

$$ \begin{aligned} m g h &= \frac{1}{2} m v^2 \\ v &= \sqrt{2 g h} \\ &= \sqrt{2 \times 9.8 \times 1.8} \approx 5.9\ \mathrm{m/s} \end{aligned} $$

We never used the shape of the curve.

**(b) Sliding distance on the floor.** On the floor $N = mg$, so friction does work $-\mu m g d$. Apply [@nc] from the start until the body stops: $\Delta K = 0$ and $\Delta U = -mgh$, so

$$ \begin{aligned} -m g h &= -\mu m g d \\ d &= \frac{h}{\mu} = \frac{1.8}{0.3} = 6.0\ \mathrm{m} \end{aligned} $$

Neither the mass nor $g$ is left in the answer.
:::

## Try it yourself

:::try The lowest point of a pendulum
A bob on a string of length $L = 1.0\ \mathrm{m}$ is released from rest with the string at $60^\circ$ to the vertical.

1. Find the speed of the bob at the lowest point.
2. At that point, how many times the bob's weight is the tension in the string?

:::solution
1. The tension is always perpendicular to the motion and does no work, so [@cons] applies. The bob falls a height $L(1 - \cos 60^\circ) = 0.5\ \mathrm{m}$, so $v = \sqrt{2 \times 9.8 \times 0.5} = \sqrt{9.8} \approx 3.1\ \mathrm{m/s}$.
2. At the lowest point the bob moves on a circle of radius $L$, so $T - mg = m v^2 / L$. With $v^2 = 2 g L (1 - \cos 60^\circ) = g L$ this gives $T = mg + mg = 2mg$, twice the weight. Released from an angle $\theta$, in general $T = mg(3 - 2\cos\theta)$.
:::
:::

:::try A block launched by a spring
A spring with $k = 500\ \mathrm{N/m}$ is compressed by $0.10\ \mathrm{m}$ with a $0.20\ \mathrm{kg}$ block against it, then released. The block crosses a frictionless level surface and slides up a frictionless ramp.

1. Find the block's speed as it leaves the spring.
2. How far above its starting level does it rise on the ramp?

:::solution
1. The spring stores $\frac{1}{2} k x^2 = \frac{1}{2} \times 500 \times 0.10^2 = 2.5\ \mathrm{J}$. All of it becomes kinetic energy, so $\frac{1}{2}(0.20) v^2 = 2.5$ and $v = 5.0\ \mathrm{m/s}$.
2. At the highest point the speed is $0$, so $m g h = 2.5\ \mathrm{J}$ and $h = 2.5 / (0.20 \times 9.8) \approx 1.3\ \mathrm{m}$. The slope of the ramp does not change the answer.
:::
:::
