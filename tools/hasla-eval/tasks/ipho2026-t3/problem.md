# IPhO 2026 — Theoretical Question T3 [10 pts]. Chasing the absolute zero

*Text-only version of the official English statement (56th IPhO, Bucaramanga, Colombia, July 8, 2026). Figures are described in words in "Figure description" blocks; everything else follows the official wording. Note (as in the official statement): $R$ denotes the ideal gas constant in the constants table and in the ideal-gas column of the comparison table, but the torus mean radius elsewhere in this question.*

## Physical constants (from the official General Instructions)

Throughout the exam, always use the values of physical constants indicated here, unless otherwise noted. When performing numerical calculations, always indicate the units of the used quantities.

| Constant | Notation | Value | Units |
|---|---|---|---|
| Speed of light in vacuum | $c$ | $2.99792458\times10^{8}$ | $\mathrm{m\cdot s^{-1}}$ |
| Planck constant | $h$ | $4.135667696\ldots\times10^{-15}$ | $\mathrm{eV\cdot s}$ |
| Reduced Planck constant | $\hbar = h/2\pi$ | $6.582119569\ldots\times10^{-16}$ | $\mathrm{eV\cdot s}$ |
| Avogadro number | $N_A$ | $6.02214076\times10^{23}$ | $\mathrm{mol^{-1}}$ |
| Boltzmann constant | $k_B$ | $8.617333262\times10^{-5}$ | $\mathrm{eV\cdot K^{-1}}$ |
| Ideal gas constant | $R$ | $8.31446261815324$ | $\mathrm{kg\cdot m^2\cdot s^{-2}\cdot mol^{-1}\cdot K^{-1}}$ |
| Elementary charge | $e$ | $1.602176634\times10^{-19}$ | $\mathrm{A\cdot s}$ |
| Universal gravitational constant | $G$ | $6.67430(15)\times10^{-11}$ | $\mathrm{m^3\cdot kg^{-1}\cdot s^{-2}}$ |
| Stefan–Boltzmann constant | $\sigma$ | $5.670374419\times10^{-8}$ | $\mathrm{kg\cdot s^{-3}\cdot K^{-4}}$ |
| Vacuum permeability | $\mu_0$ | $1.25663706127(20)\times10^{-6}$ | $\mathrm{kg\cdot m\cdot A^{-2}\cdot s^{-2}}$ |
| Vacuum permittivity | $\varepsilon_0$ | $8.8541878188(14)\times10^{-12}$ | $\mathrm{A^2\cdot s^4\cdot kg^{-1}\cdot m^{-3}}$ |
| Mass of the electron | $m_e$ | $5.1099895069(16)\times10^{5}$ | $\mathrm{eV}/c^2$ |
| Mass of the proton | $m_p$ | $9.3827208943(29)\times10^{8}$ | $\mathrm{eV}/c^2$ |
| Atomic mass units | amu | $9.3149410372(29)\times10^{8}$ | $\mathrm{eV}/c^2$ |

---

A refrigeration cycle must be carried out by a system with characteristics appropriate for the temperatures to be achieved. One hundred years ago, in 1926, the chemist William Giauque and, independently, the physicist Peter Debye proposed paramagnetic salts as ideal systems for lowering temperatures far below 1 K. Indeed, beginning in the following decade, temperatures as low as 0.0044 K were achieved (Wander de Haas and Gerrit Wiersma, 1935, Leiden Cryogenic Laboratories). In this question, the paramagnetic Carnot refrigeration cycle is studied.

Consider a torus with mean radius $R$ and inner radius $r$ made of a homogeneous, isotropic paramagnetic material, around which an insulated conducting wire is wound, with its ends connected to an external voltage source (emf), as shown in figure 3a. The resistance of the wire is so low that energy losses due to the heating of the wire can be neglected. The winding is dense, with $N$ turns in total, and it is assumed that $r \ll R$, so that the fields $\vec H$ and $\vec B$ and the magnetization $\vec M$ have approximately constant magnitudes throughout the torus. Let $V$ and $A$ be the volume and the cross-section area of the torus. Hereinafter, the abbreviation Pm-T is used to refer to the paramagnetic torus.

> **Figure description (Fig. 3a).** A ring-shaped core (torus) densely wound with wire along its whole circumference (a toroidal coil). An arrow from the centre of the ring to the middle of the tube is labelled $R$ (mean radius); a double arrow across the tube is labelled $2r$ (tube diameter, so $r$ is the tube's radius). A small cut-away shows the grey paramagnetic core inside the winding. The two ends of the wire are connected to a battery symbol labelled $\mathscr{E}$ (the external emf).

In paramagnetic materials, $\vec M$ is parallel to $\vec H$ and the following relation holds:

$$\vec B = \mu_0\vec H + \mu_0\vec M.$$

**Energy transfer sign convention:** in this problem, Work ($W$) and Heat ($Q$) are considered positive when they flow into the system, and negative when they flow out.

## T3-A [1.0 pts]. Work in the Pm-T

*Hint: in magnetic materials, $\oint_C \vec H\cdot d\vec\ell = I_C$, where $I_C$ is the net free current passing through the area bounded by the closed curve $C$.*

**T3-A1 [0.2 pts].** Let $H$ be the magnitude of $\vec H$ in the torus. Write $H$ in terms of $N$, $A$, $V$ and the instantaneous electric current $I$ in the wire.

**T3-A2 [0.6 pts].** Let $dW_{emf}$ be the work that the external voltage source performs to change the magnitude of $\vec B$ by $dB$. Write $dW_{emf}$ in terms of $V$, $H$, and $dB$.

**T3-A3 [0.2 pts].** The total work done by the voltage source, $dW_{emf}$, can be divided in two parts: the work that would be performed to change the magnetic field if the toroid had a vacuum core, $dW_{vac}$, and the work done on the paramagnetic material itself, $dW$. Write $dW$ in terms of $\mu_0$, $H$, $V$ and $dM$.

## T3-B [3.0 pts]. Heat and temperature in the Pm-T

The following table compares two thermodynamic systems: the ideal gas and the Pm-T. Use this information and your answer to question T3-A3 to solve the following questions. This information will also be used in part C. If you did not find an answer for $dW$ in question T3-A3, you may use $dW = \alpha V\mu_0 H\,dM$ where $\alpha$ is a number. The volume $V$ of the paramagnetic torus is constant, so that there is no work due to pressure. Below, $T$ is the temperature in all instances.

| IDEAL GAS | PARAMAGNETIC TORUS |
|---|---|
| State functions: $P, V$ and temperature $T$ | State functions: $H, M$ and temperature $T$ |
| Constants: $R, \gamma$ and number of moles $n$ | Constants: $K, \lambda$ and number of moles $n$ |
| Equation of state: $PV = nRT$ | Equation of state: $TMV = nKH$ |
| Heat capacity at constant $V$: $C_V = nR/(\gamma-1)$ | Heat capacity at constant $M$: $C_M = n\lambda/T^2$ |
| Internal energy $U$ in any process satisfies $dU = C_V\,dT$ | Internal energy $U$ in any process satisfies $dU = C_M\,dT$ |

$K$ and $\lambda$ are constants given by the material in the torus. You may use the equations provided in the table directly without proving them.

**T3-B1 [1.5 pts].** If the magnitude of $\vec H$ changes from $H_i$ to $H_f$ at a constant temperature $T$, an energy $Q$ is transferred between the Pm-T and its environment. Write $Q$ in terms of $\mu_0$, $n$, $V$, $K$, $H_i$, $H_f$, and $T$.

**T3-B2 [1.5 pts].** If the magnitude of $\vec H$ changes adiabatically from $H_i$ to $H_f$, the temperature of the Pm-T changes from $T_i$ to $T_f$. Write $\Delta T = T_f - T_i$ in terms of $\mu_0$, $V$, $n$, $K$, $\lambda$, $H_i$, $H_f$, and $T_i$.

## T3-C [6.0 pts]. Carnot refrigerator of the Pm-T

The $H$ vs. $T$ diagram of the Carnot refrigeration cycle $1\to2\to3\to4\to1$ performed by the Pm-T is shown in figure 3b. In this cycle, let:

- $T_h$: temperature of the hot reservoir
- $T_c$: temperature of the cold reservoir
- $Q_h$: absolute value of the heat transferred to the hot reservoir
- $Q_c$: absolute value of the heat absorbed from the cold reservoir

> **Figure description (Fig. 3b).** Axes: $H$ vertical, $T$ horizontal (no numerical scale). The cycle has four vertices. Vertices 2 and 3 lie on the same vertical line at a lower temperature (left), with 2 above 3; vertices 1 and 4 lie on the same vertical line at a higher temperature (right), with 1 above 4. Vertex 1 has the largest $H$ of the cycle and vertex 3 the smallest; $H_2$ is between $H_4$ and $H_1$ in height on the drawing, $H_4$ is above $H_3$. Process $1\to2$: a curve going from the upper right (1) down and to the left to 2, concave downward (both $H$ and $T$ decrease). Process $2\to3$: vertical straight segment at the lower temperature, $H$ decreasing from 2 to 3. Process $3\to4$: a curve rising from 3 up and to the right to 4, concave downward (both $H$ and $T$ increase). Process $4\to1$: vertical straight segment at the higher temperature, $H$ increasing from 4 to 1. Dashed vertical lines drop from vertices 3 and 4 to the $T$ axis, marking the two temperatures of the vertical segments (unlabelled in the statement figure).

**T3-C1 [0.2 pts].** `[GRAPH/FIGURE-DEPENDENT]` Mark $T_h$ and $T_c$ on the $T$ axis of the $H$ vs. $T$ diagram. Also label the processes in which the transfers of $Q_h$ and $Q_c$ occur, respectively.
*(Text-only adaptation: state which of the two marked temperatures — that of the left vertical segment 2–3 or that of the right vertical segment 4–1 — is $T_h$ and which is $T_c$, and name the processes, e.g. "$x\to y$", in which $Q_h$ and $Q_c$ are transferred.)*

**T3-C2 [1.5 pts].** Let $M_1$, $M_2$, $M_3$, and $M_4$ be the magnitudes of $\vec M$ at the vertices of this cycle. Write $M_1$ in terms of $M_2$, $M_3$, and $M_4$.

**T3-C3 [0.8 pts].** Suppose that to cool 1.00 L of liquid helium initially at 1.00 K, we utilize a 2.0 moles Pm-T made of *potassium chromate*. For this material, $K = 1.87\times10^{-6}\ \text{K}\cdot\text{m}^3/\text{mol}$, its density is $2730\ \text{kg/m}^3$ and its molar mass is $0.19\ \text{kg/mol}$. The Pm-T performs a Carnot refrigeration cycle with $H_1 = 411624$ A/m, $H_2 = 311306$ A/m, $H_3 = 204618$ A/m and $H_4 = 240446$ A/m. After one operating cycle, calculate the final temperature of the liquid helium. Assume that for the liquid helium both the specific heat capacity $c = 100\ \text{J/(kg}\cdot\text{K)}$ and the density $\rho = 130\ \text{kg/m}^3$ remain constant.

**T3-C4 [2.0 pts].** In order to continuously lower the temperature of a body with constant heat capacity $C_c$, Carnot cycles are allowed to occur over time in such a way that the power $P$ transferred to the refrigerator remains constant. It is then assumed that the temperature $T_h$ of the hot reservoir remains constant and that in each operating cycle the temperature $T_c$ of the cooled body decreases by $dT_c$, satisfying the relation $dQ_c/dQ_h = T_c/T_h$. If at $t = 0$ we have $T_c = T_0$, determine the time $t$ that the Carnot refrigerator must operate for the cooled body to reach a temperature $T < T_0$. Express your answer in terms of $C_c$, $T_h$, $P$, $T_0$ and $T$.

**T3-C5 [1.5 pts].** The efficiency of a refrigerator is quantified by its *coefficient of performance* $\mathrm{COP} = Q_c/W$. Determine the overall COP of the refrigerator of question T3-C4 with all the cycles performed until time $t$. Write your answer in terms of $T_0$ and $T_h$ and $T$.
