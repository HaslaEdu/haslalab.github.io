---
title_ko: 운동학: 등가속도 운동
title_en: "Kinematics: constant acceleration"
unit: mechanics/kinematics
level: 3
order: 1
summary: Derive the four equations that give position and velocity in time when the acceleration is constant, then use them on a ball thrown upward.
---

## Position, velocity and acceleration

We describe a body moving along a straight line by its position as a function of time, $x(t)$. First choose which direction is $+$. That choice fixes the sign of the position, the velocity and the acceleration.

Velocity is how fast the position changes, and acceleration is how fast the velocity changes.

$$ v = \frac{dx}{dt}, \qquad a = \frac{dv}{dt} $$ {#def}

If you have not met derivatives yet, read them as changes over a very short time $\Delta t$: $v \approx \Delta x / \Delta t$ and $a \approx \Delta v / \Delta t$.

:::remark
Speed is the size of the velocity. A ball thrown upward has zero velocity at the top, but its acceleration is not zero there. The velocity is still changing at that instant.
:::

## The four equations of constant acceleration

This chapter covers only the case where the acceleration $a$ does not change with time. At $t = 0$ the position is $x_0$ and the velocity is $v_0$.

With constant acceleration the velocity changes at a constant rate.

$$ v = v_0 + a t $$ {#v-t}

The position changes by the area under the velocity-time graph. In [@vt-graph] that area is a trapezoid of width $t$ with heights $v_0$ and $v$.

![Velocity-time graph. The slope is the acceleration $a$, and the shaded area is the displacement $x - x_0$.](fig/kinematics-vt-graph.svg){#vt-graph}

The area of the trapezoid gives the next equation at once.

$$ x - x_0 = \frac{v_0 + v}{2}\, t $$ {#avg}

Putting $v$ from [@v-t] into [@avg] gives position against time.

$$ x = x_0 + v_0 t + \frac{1}{2} a t^2 $$ {#x-t}

:::derivation [@x-t] with calculus
Since the acceleration is constant, integrate $dv/dt = a$ from $0$ to $t$.

$$ v(t) - v_0 = \int_0^t a \, dt' = a t $$

Then integrate $dx/dt = v_0 + a t$.

$$ \begin{aligned} x(t) - x_0 &= \int_0^t (v_0 + a t')\, dt' \\ &= v_0 t + \frac{1}{2} a t^2 \end{aligned} $$

This is the same result as the area of the graph, because an integral is a way of computing that area.
:::

Many problems do not give the time. Solve [@v-t] for $t = (v - v_0)/a$ and put it into [@avg]; the time drops out.

$$ v^2 = v_0^2 + 2a\,(x - x_0) $$ {#v-x}

:::derivation Removing the time to get [@v-x]
$$ \begin{aligned} x - x_0 &= \frac{v_0 + v}{2} \cdot \frac{v - v_0}{a} \\ &= \frac{v^2 - v_0^2}{2a} \end{aligned} $$

Multiply both sides by $2a$ to get [@v-x]. Dividing by $a$ assumed $a \neq 0$, but when $a = 0$ we have $v = v_0$, so [@v-x] still holds.
:::

:::result
With constant acceleration

- $v = v_0 + a t$
- $x - x_0 = v_0 t + \frac{1}{2} a t^2$
- $v^2 = v_0^2 + 2a(x - x_0)$
- $x - x_0 = \frac{1}{2}(v_0 + v)\, t$

Of the five quantities $x - x_0$, $v_0$, $v$, $a$ and $t$, any three give the other two. Pick the equation that leaves out the quantity the problem does not mention.
:::

:::why Why is the average velocity $(v_0 + v)/2$?
The average velocity is the displacement divided by the time taken. With constant acceleration the $v$-$t$ graph is a straight line, so the body is slower than average in the first half of the time by exactly as much as it is faster in the second half. The mean of the two end velocities is then the average velocity. If the acceleration changes, the graph bends and the formula fails. A car that accelerates hard at the start and then cruises at a steady speed has an average velocity larger than $(v_0 + v)/2$.
:::

## Vertical motion

Near the Earth's surface, with air resistance neglected, every body falls with the same acceleration whatever its mass. Its size is written $g \approx 9.8\ \mathrm{m/s^2}$.

Taking up as $+$, $a = -g$, and with the height written $y$, [@x-t] becomes

$$ y = y_0 + v_0 t - \frac{1}{2} g t^2 $$ {#free}

:::remark
You may take down as $+$ instead. Then $a = +g$ and an upward throw has a negative velocity. Either way, keep the same direction for the whole problem.
:::

:::example A ball thrown up from a cliff
A ball is thrown straight up at $15\ \mathrm{m/s}$ from the edge of a cliff $20\ \mathrm{m}$ high, and lands on the ground below. Take $g = 9.8\ \mathrm{m/s^2}$ and ignore air resistance.

**(a) Greatest height above the ground.** At the top $v = 0$, so [@v-x] gives $0 = v_0^2 - 2g\,\Delta y$.

$$ \Delta y = \frac{v_0^2}{2g} = \frac{15^2}{2 \times 9.8} \approx 11.5\ \mathrm{m} $$

Measured from the ground that is $20 + 11.5 = 31.5\ \mathrm{m}$.

**(b) Speed on reaching the ground.** The displacement from the start to the ground is $y - y_0 = -20\ \mathrm{m}$. From [@v-x],

$$ \begin{aligned} v^2 &= 15^2 + 2 \times 9.8 \times 20 = 617 \\ |v| &\approx 24.8\ \mathrm{m/s} \end{aligned} $$

pointing down. We found the speed without knowing the time.

**(c) Time of flight.** Put $v = -24.8\ \mathrm{m/s}$ into [@v-t].

$$ t = \frac{v_0 - v}{g} = \frac{15 + 24.8}{9.8} \approx 4.1\ \mathrm{s} $$

Putting $y = 0$ and $y_0 = 20\ \mathrm{m}$ into [@free] gives the quadratic $4.9 t^2 - 15 t - 20 = 0$, whose positive root is the same. The negative root is a time before the throw, so we drop it.
:::

## Try it yourself

:::try A train starting from rest
A train starts from rest with constant acceleration and covers $100\ \mathrm{m}$ in the first $10\ \mathrm{s}$.

1. Find its acceleration.
2. How many seconds does it take to cover the next $100\ \mathrm{m}$?

:::solution
1. With $v_0 = 0$, [@x-t] gives $100 = \frac{1}{2} a (10)^2$, so $a = 2\ \mathrm{m/s^2}$.
2. The time to reach $200\ \mathrm{m}$ from the start is given by $200 = \frac{1}{2} \times 2 \times t^2$, so $t = \sqrt{200} \approx 14.1\ \mathrm{s}$. The next $100\ \mathrm{m}$ takes $14.1 - 10 = 4.1\ \mathrm{s}$, much less than the first $100\ \mathrm{m}$ because the train is now faster.
:::
:::

:::try Distances in equal time intervals
A body starts from rest with constant acceleration. Cut its motion into equal time intervals $\tau$. Show that the distances covered in the first, second and third intervals are in the ratio $1 : 3 : 5$. (Find the distance in the $n$-th interval too.)

:::solution
From [@x-t] with $x_0 = 0$ and $v_0 = 0$, the distance covered by time $n\tau$ is $\frac{1}{2} a (n\tau)^2$. In the $n$-th interval the body covers

$$ \begin{aligned} &\frac{1}{2} a \tau^2 \left[ n^2 - (n-1)^2 \right] \\ &= \frac{1}{2} a \tau^2 (2n - 1) \end{aligned} $$

so for $n = 1, 2, 3$ the ratio is $1 : 3 : 5$, and in general the odd numbers in turn. Galileo found this rule with balls rolling down a slope.
:::
:::
