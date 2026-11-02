/* IPhO 2025 Theory-Backup Q4 «Strongly correlated Fermi gases»: no official solution was published, so this is
 * HaslaLab's worked solution and marking scheme, laid out as the 2025 solutions are (the question box, the solution
 * in red, a marker scheme).  The points of each sub-item add up to the points printed in the paper. */
const { q, sol, ms } = require('../lib.cjs');

const T = {
  en: {
    title: 'Strongly correlated Fermi gases (10.0 points)',
    intro: '<p class="note">No official solution of this backup problem has been published. This worked solution and marking scheme were written by HaslaLab for grading practice; the problem text is the official English version.</p>',
    A: 'A. Thermodynamics of a non-interacting quantum gas', B: 'B. Thermodynamics of a trapped quantum gas',
  },
  ko: {
    title: '강상관 페르미 기체 (10.0점)',
    intro: '<p class="note">이 예비 문제의 공식 풀이는 공개되지 않았습니다. 아래 풀이와 채점 기준은 채점 연습을 위해 HaslaLab이 작성했으며, 문제 문장은 공식 영어판을 옮긴 것입니다.</p>',
    A: 'A. 상호작용이 없는 양자 기체의 열역학', B: 'B. 갇힌 양자 기체의 열역학',
  },
};

/* [label, points, question {en, ko}, solution {en, ko}, scheme [[en, ko, pts]…]] */
const ITEMS = [
  ['A.1', 0.5,
    { en: 'Express the kinetic energy $K_x$ of the particle as a function of $h$, $\\lambda$ and $m$.',
      ko: '입자의 운동 에너지 $K_x$를 $h$, $\\lambda$, $m$으로 나타내어라.' },
    { en: 'By de Broglie\'s relation the momentum is $p_x=\\hbar k_x=h/\\lambda$, so <span class="box">$K_x=\\dfrac{p_x^2}{2m}=\\dfrac{h^2}{2m\\lambda^2}$</span>.',
      ko: '드브로이 관계식에서 운동량은 $p_x=\\hbar k_x=h/\\lambda$이므로 <span class="box">$K_x=\\dfrac{p_x^2}{2m}=\\dfrac{h^2}{2m\\lambda^2}$</span>이다.' },
    [['de Broglie relation $p=h/\\lambda$', '드브로이 관계식 $p=h/\\lambda$', 0.2], ['$K_x=h^2/(2m\\lambda^2)$', '$K_x=h^2/(2m\\lambda^2)$', 0.3]]],
  ['A.2', 0.6,
    { en: 'Show that $k_x=k_1 n_x$, where $n_x$ is a strictly positive integer.', ko: '$n_x$가 양의 정수일 때 $k_x=k_1 n_x$임을 보여라.' },
    { en: '$\\psi(0)=A+B=0$ gives $B=-A$ and $\\psi(x)=2iA\\sin(k_x x)$. Then $\\psi(L)=0$ requires $\\sin(k_xL)=0$, i.e. $k_xL=n_x\\pi$. Since $k_x>0$ (and $n_x=0$ would give $\\psi\\equiv0$), $n_x\\ge1$: <span class="box">$k_x=n_x k_1,\\ k_1=\\pi/L$</span>.',
      ko: '$\\psi(0)=A+B=0$에서 $B=-A$이고 $\\psi(x)=2iA\\sin(k_x x)$이다. $\\psi(L)=0$이려면 $\\sin(k_xL)=0$, 즉 $k_xL=n_x\\pi$이다. $k_x>0$이고 $n_x=0$이면 $\\psi\\equiv0$이므로 $n_x\\ge1$: <span class="box">$k_x=n_x k_1,\\ k_1=\\pi/L$</span>.' },
    [['$\\psi(0)=0\\Rightarrow B=-A$ (standing wave $\\sin k_x x$)', '$\\psi(0)=0\\Rightarrow B=-A$ (정상파 $\\sin k_x x$)', 0.2],
     ['$\\psi(L)=0\\Rightarrow k_xL=n_x\\pi$ with $n_x\\ge1$', '$\\psi(L)=0\\Rightarrow k_xL=n_x\\pi$, $n_x\\ge1$', 0.3], ['$k_1=\\pi/L$', '$k_1=\\pi/L$', 0.1]]],
  ['A.3', 0.7,
    { en: 'Represent the quantum states in the $(k_x,k_y,k_z)$ phase space. Express with $L$ the volume $(\\Delta k)^3$ occupied by each state.',
      ko: '$(k_x,k_y,k_z)$ 위상 공간에 양자 상태를 나타내어라. 상태 하나가 차지하는 부피 $(\\Delta k)^3$를 $L$로 나타내어라.' },
    { en: 'The states are the points $\\vec k=\\frac{\\pi}{L}(n_x,n_y,n_z)$ with $n_i\\ge1$: a cubic lattice of spacing $\\pi/L$ filling the octant $k_x,k_y,k_z>0$. Each point owns one cell, <span class="box">$(\\Delta k)^3=(\\pi/L)^3=\\pi^3/V$</span>.',
      ko: '상태는 $n_i\\ge1$인 점 $\\vec k=\\frac{\\pi}{L}(n_x,n_y,n_z)$이다. 즉 $k_x,k_y,k_z>0$인 1/8 공간을 채우는 간격 $\\pi/L$의 입방 격자이다. 각 점이 칸 하나를 차지하므로 <span class="box">$(\\Delta k)^3=(\\pi/L)^3=\\pi^3/V$</span>이다.' },
    [['Cubic lattice in the octant $k_i>0$', '$k_i>0$인 1/8 공간의 입방 격자', 0.3], ['Spacing $\\pi/L$', '간격 $\\pi/L$', 0.2], ['$(\\Delta k)^3=(\\pi/L)^3$', '$(\\Delta k)^3=(\\pi/L)^3$', 0.2]]],
  ['A.4', 1.4,
    { en: 'Represent the states with energy lower than $\\mathcal E_F$ in $\\vec k$-space. Deduce the expression of $\\mathcal E_F$ with $N$.',
      ko: '에너지가 $\\mathcal E_F$보다 낮은 상태를 $\\vec k$ 공간에 나타내어라. $\\mathcal E_F$를 $N$으로 나타내어라.' },
    { en: 'Since $\\mathcal E=\\hbar^2k^2/2m$, the occupied states fill the part of the sphere $|\\vec k|<k_F$ in the octant. Their number is $\\frac18\\cdot\\frac{4\\pi k_F^3/3}{(\\pi/L)^3}=\\frac{Vk_F^3}{6\\pi^2}$; with two atoms per state $N=\\frac{Vk_F^3}{3\\pi^2}$, so $k_F=(3\\pi^2N/V)^{1/3}$ and <span class="box">$\\mathcal E_F=\\dfrac{\\hbar^2}{2m}\\left(\\dfrac{3\\pi^2N}{L^3}\\right)^{2/3}$</span>.',
      ko: '$\\mathcal E=\\hbar^2k^2/2m$이므로 채워진 상태는 1/8 공간 안에서 구 $|\\vec k|<k_F$를 채운다. 그 수는 $\\frac18\\cdot\\frac{4\\pi k_F^3/3}{(\\pi/L)^3}=\\frac{Vk_F^3}{6\\pi^2}$이고, 상태 하나에 원자 둘이므로 $N=\\frac{Vk_F^3}{3\\pi^2}$, $k_F=(3\\pi^2N/V)^{1/3}$, <span class="box">$\\mathcal E_F=\\dfrac{\\hbar^2}{2m}\\left(\\dfrac{3\\pi^2N}{L^3}\\right)^{2/3}$</span>이다.' },
    [['Occupied states: octant of the sphere of radius $k_F$', '채워진 상태: 반지름 $k_F$인 구의 1/8', 0.3], ['Number of states $Vk_F^3/(6\\pi^2)$', '상태 수 $Vk_F^3/(6\\pi^2)$', 0.4],
     ['Two atoms per state: $N=Vk_F^3/(3\\pi^2)$', '상태당 원자 2개: $N=Vk_F^3/(3\\pi^2)$', 0.3], ['$\\mathcal E_F=\\frac{\\hbar^2}{2m}(3\\pi^2N/V)^{2/3}$', '$\\mathcal E_F=\\frac{\\hbar^2}{2m}(3\\pi^2N/V)^{2/3}$', 0.4]]],
  ['A.5', 0.8,
    { en: 'Express the increase in energy $\\mathrm d\\mathcal E$ in the system as a function of $\\mathcal E_F(N)$. Show that $\\mathcal E(N)=\\kappa N\\mathcal E_F(N)$ for some number $\\kappa$.',
      ko: '계의 에너지 증가 $\\mathrm d\\mathcal E$를 $\\mathcal E_F(N)$으로 나타내어라. 어떤 수 $\\kappa$에 대해 $\\mathcal E(N)=\\kappa N\\mathcal E_F(N)$임을 보여라.' },
    { en: 'The added atoms go into the lowest free states, at energy $\\mathcal E_F$: <span class="box">$\\mathrm d\\mathcal E=\\mathcal E_F(N)\\,\\mathrm dN$</span>. With $\\mathcal E_F=CN^{2/3}$, $\\mathcal E=\\int_0^N CN\'^{2/3}\\mathrm dN\'=\\frac35CN^{5/3}$, so <span class="box">$\\mathcal E=\\frac35N\\mathcal E_F$, $\\kappa=3/5$</span>.',
      ko: '더한 원자는 비어 있는 가장 낮은 상태, 즉 에너지 $\\mathcal E_F$에 들어가므로 <span class="box">$\\mathrm d\\mathcal E=\\mathcal E_F(N)\\,\\mathrm dN$</span>이다. $\\mathcal E_F=CN^{2/3}$이므로 $\\mathcal E=\\int_0^N CN\'^{2/3}\\mathrm dN\'=\\frac35CN^{5/3}$, 곧 <span class="box">$\\mathcal E=\\frac35N\\mathcal E_F$, $\\kappa=3/5$</span>이다.' },
    [['$\\mathrm d\\mathcal E=\\mathcal E_F\\,\\mathrm dN$', '$\\mathrm d\\mathcal E=\\mathcal E_F\\,\\mathrm dN$', 0.3], ['Integration with $\\mathcal E_F\\propto N^{2/3}$', '$\\mathcal E_F\\propto N^{2/3}$로 적분', 0.3], ['$\\kappa=3/5$', '$\\kappa=3/5$', 0.2]]],
  ['A.6', 0.8,
    { en: 'Express the energy variation $\\mathrm d\\mathcal E$ for a change in volume $\\mathrm dV$. Deduce the expression of the pressure as a function of density $n=N/L^3$.',
      ko: '부피 변화 $\\mathrm dV$에 대한 에너지 변화 $\\mathrm d\\mathcal E$를 나타내어라. 압력을 밀도 $n=N/L^3$의 함수로 구하여라.' },
    { en: 'At fixed $N$ (and $T=0$) <span class="box">$\\mathrm d\\mathcal E=-P\\,\\mathrm dV$</span>. As $\\mathcal E\\propto V^{-2/3}$, $P=-\\partial\\mathcal E/\\partial V=\\frac{2\\mathcal E}{3V}=\\frac25n\\mathcal E_F$, i.e. <span class="box">$P=\\dfrac{(3\\pi^2)^{2/3}\\hbar^2}{5m}\\,n^{5/3}$</span>.',
      ko: '$N$이 일정할 때($T=0$) <span class="box">$\\mathrm d\\mathcal E=-P\\,\\mathrm dV$</span>이다. $\\mathcal E\\propto V^{-2/3}$이므로 $P=-\\partial\\mathcal E/\\partial V=\\frac{2\\mathcal E}{3V}=\\frac25n\\mathcal E_F$, 즉 <span class="box">$P=\\dfrac{(3\\pi^2)^{2/3}\\hbar^2}{5m}\\,n^{5/3}$</span>이다.' },
    [['$\\mathrm d\\mathcal E=-P\\,\\mathrm dV$', '$\\mathrm d\\mathcal E=-P\\,\\mathrm dV$', 0.2], ['$P=2\\mathcal E/(3V)=\\frac25n\\mathcal E_F$', '$P=2\\mathcal E/(3V)=\\frac25n\\mathcal E_F$', 0.3], ['$P\\propto n^{5/3}$ with the correct prefactor', '올바른 계수의 $P\\propto n^{5/3}$', 0.3]]],
  ['A.7', 0.4,
    { en: 'Give the value of $\\alpha$.', ko: '$\\alpha$의 값을 구하여라.' },
    { en: '$f$ depends on a dimensionless argument; $n$ has dimension $\\mathrm{L^{-3}}$ and $a$ a length, so $na^\\alpha$ is dimensionless only for <span class="box">$\\alpha=3$</span> (equivalently $1/(k_Fa)^3$).',
      ko: '$f$의 인자는 무차원이다. $n$의 차원은 $\\mathrm{L^{-3}}$, $a$는 길이이므로 $na^\\alpha$가 무차원이려면 <span class="box">$\\alpha=3$</span>이다($1/(k_Fa)^3$와 같은 뜻).' },
    [['Dimensionless argument $\\Rightarrow\\alpha=3$', '무차원 인자 $\\Rightarrow\\alpha=3$', 0.4]]],
  ['A.8', 0.6,
    { en: 'Show that, at the unitary limit, the properties of the interacting cloud are identical to those of a noninteracting system up to a rescaling of Planck\'s constant $\\hbar\\to\\xi^\\gamma\\hbar$. Give the value of $\\gamma$.',
      ko: '유니터리 극한에서 상호작용하는 구름의 성질이 플랑크 상수를 $\\hbar\\to\\xi^\\gamma\\hbar$로 바꾼 비상호작용 계와 같음을 보여라. $\\gamma$의 값을 구하여라.' },
    { en: 'At $a=\\infty$, $\\mathcal E=\\xi\\kappa N\\mathcal E_F$ and $\\mathcal E_F\\propto\\hbar^2$, so $\\xi\\hbar^2=(\\xi^{1/2}\\hbar)^2$: the energy (and hence $P=\\frac23\\mathcal E/V$ and every derived quantity) is that of the free gas with $\\hbar\\to\\xi^{1/2}\\hbar$. <span class="box">$\\gamma=1/2$</span>.',
      ko: '$a=\\infty$에서 $\\mathcal E=\\xi\\kappa N\\mathcal E_F$이고 $\\mathcal E_F\\propto\\hbar^2$이므로 $\\xi\\hbar^2=(\\xi^{1/2}\\hbar)^2$이다. 에너지(따라서 $P=\\frac23\\mathcal E/V$와 이로부터 얻는 모든 양)가 $\\hbar\\to\\xi^{1/2}\\hbar$로 바꾼 자유 기체와 같다. <span class="box">$\\gamma=1/2$</span>.' },
    [['$\\mathcal E=\\xi\\kappa N\\mathcal E_F$ with $\\mathcal E_F\\propto\\hbar^2$', '$\\mathcal E=\\xi\\kappa N\\mathcal E_F$, $\\mathcal E_F\\propto\\hbar^2$', 0.3], ['$\\gamma=1/2$', '$\\gamma=1/2$', 0.3]]],
  ['B.1', 1.5,
    { en: 'Write the total forces exerted on the atoms and show that the density is given by $n(\\vec r)=A\\left(\\mathcal E_F(0)-U(\\vec r)\\right)^{3/2}$, where $\\mathcal E_F(0)$ is the Fermi energy at the trap center. Give the expression of $A$.',
      ko: '원자에 작용하는 힘을 모두 쓰고 밀도가 $n(\\vec r)=A\\left(\\mathcal E_F(0)-U(\\vec r)\\right)^{3/2}$임을 보여라. 여기서 $\\mathcal E_F(0)$은 덫 중심의 페르미 에너지이다. $A$를 구하여라.' },
    { en: 'For the slab between $x$ and $x+\\mathrm dx$: pressure forces $\\Sigma[P(x)-P(x+\\mathrm dx)]$ and the trap force $-n\\Sigma\\,\\mathrm dx\\,U\'(x)$ balance, so $\\dfrac{\\mathrm dP}{\\mathrm dx}=-n\\dfrac{\\mathrm dU}{\\mathrm dx}$. From A.6, $P=\\frac25n\\mathcal E_F$ with $\\mathcal E_F\\propto n^{2/3}$ gives $\\mathrm dP=n\\,\\mathrm d\\mathcal E_F$. Hence $\\mathcal E_F(x)+U(x)=\\mathcal E_F(0)$ and, inverting $\\mathcal E_F=\\frac{\\hbar^2}{2m}(3\\pi^2n)^{2/3}$, <span class="box">$A=\\dfrac{(2m)^{3/2}}{3\\pi^2\\hbar^3}$</span>.',
      ko: '$x$와 $x+\\mathrm dx$ 사이의 얇은 판에서 압력에 의한 힘 $\\Sigma[P(x)-P(x+\\mathrm dx)]$과 덫의 힘 $-n\\Sigma\\,\\mathrm dx\\,U\'(x)$가 평형을 이루므로 $\\dfrac{\\mathrm dP}{\\mathrm dx}=-n\\dfrac{\\mathrm dU}{\\mathrm dx}$이다. A.6에서 $P=\\frac25n\\mathcal E_F$, $\\mathcal E_F\\propto n^{2/3}$이므로 $\\mathrm dP=n\\,\\mathrm d\\mathcal E_F$이다. 따라서 $\\mathcal E_F(x)+U(x)=\\mathcal E_F(0)$이고, $\\mathcal E_F=\\frac{\\hbar^2}{2m}(3\\pi^2n)^{2/3}$을 풀면 <span class="box">$A=\\dfrac{(2m)^{3/2}}{3\\pi^2\\hbar^3}$</span>이다.' },
    [['Force balance $\\mathrm dP/\\mathrm dx=-n\\,\\mathrm dU/\\mathrm dx$', '힘의 평형 $\\mathrm dP/\\mathrm dx=-n\\,\\mathrm dU/\\mathrm dx$', 0.5], ['$\\mathrm dP=n\\,\\mathrm d\\mathcal E_F$ (from A.6)', '$\\mathrm dP=n\\,\\mathrm d\\mathcal E_F$ (A.6에서)', 0.4],
     ['$\\mathcal E_F(\\vec r)+U(\\vec r)=\\mathcal E_F(0)$', '$\\mathcal E_F(\\vec r)+U(\\vec r)=\\mathcal E_F(0)$', 0.3], ['$A=(2m)^{3/2}/(3\\pi^2\\hbar^3)$', '$A=(2m)^{3/2}/(3\\pi^2\\hbar^3)$', 0.3]]],
  ['B.2', 0.7,
    { en: 'Find the equation defining the surface of the cloud. Give the expression of the radius $R_i$ of the cloud in the direction $i=x,y,z$ as a function of $\\mathcal E_F(0)$, $m$ and $\\omega_i$.',
      ko: '구름의 표면을 나타내는 식을 구하여라. $i=x,y,z$ 방향의 구름 반지름 $R_i$를 $\\mathcal E_F(0)$, $m$, $\\omega_i$로 나타내어라.' },
    { en: 'The density vanishes where $U(\\vec r)=\\mathcal E_F(0)$: the ellipsoid <span class="box">$\\sum_i x_i^2/R_i^2=1$</span> with <span class="box">$R_i=\\sqrt{2\\mathcal E_F(0)/(m\\omega_i^2)}$</span>.',
      ko: '$U(\\vec r)=\\mathcal E_F(0)$에서 밀도가 0이 된다. 표면은 타원체 <span class="box">$\\sum_i x_i^2/R_i^2=1$</span>이고 <span class="box">$R_i=\\sqrt{2\\mathcal E_F(0)/(m\\omega_i^2)}$</span>이다.' },
    [['Surface $U=\\mathcal E_F(0)$', '표면 $U=\\mathcal E_F(0)$', 0.2], ['Ellipsoid equation', '타원체 식', 0.2], ['$R_i=\\sqrt{2\\mathcal E_F(0)/m\\omega_i^2}$', '$R_i=\\sqrt{2\\mathcal E_F(0)/m\\omega_i^2}$', 0.3]]],
  ['B.3', 1.1,
    { en: 'Calculate the total atom number as a spatial integral by decomposing the cloud into infinitesimal shells of radius $r$ and thickness $\\mathrm dr$, and show that $\\mathcal E_F(0)=\\hbar\\bar\\omega(3N)^\\mu$. Give the value of $\\mu$.',
      ko: '구름을 반지름 $r$, 두께 $\\mathrm dr$인 얇은 껍질로 나누어 전체 원자 수를 적분으로 구하고, $\\mathcal E_F(0)=\\hbar\\bar\\omega(3N)^\\mu$임을 보여라. $\\mu$의 값을 구하여라.' },
    { en: 'In the isotropic trap $n(r)=A\\mathcal E_F(0)^{3/2}(1-r^2/R^2)^{3/2}$ with $R^2=2\\mathcal E_F(0)/(m\\bar\\omega^2)$. Then $N=\\int_0^R4\\pi r^2n\\,\\mathrm dr=4\\pi A\\mathcal E_F(0)^{3/2}R^3\\cdot\\frac{\\pi}{32}=\\dfrac{\\mathcal E_F(0)^3}{3(\\hbar\\bar\\omega)^3}$, so <span class="box">$\\mathcal E_F(0)=\\hbar\\bar\\omega(3N)^{1/3}$, $\\mu=1/3$</span>.',
      ko: '등방 덫에서 $n(r)=A\\mathcal E_F(0)^{3/2}(1-r^2/R^2)^{3/2}$, $R^2=2\\mathcal E_F(0)/(m\\bar\\omega^2)$이다. $N=\\int_0^R4\\pi r^2n\\,\\mathrm dr=4\\pi A\\mathcal E_F(0)^{3/2}R^3\\cdot\\frac{\\pi}{32}=\\dfrac{\\mathcal E_F(0)^3}{3(\\hbar\\bar\\omega)^3}$이므로 <span class="box">$\\mathcal E_F(0)=\\hbar\\bar\\omega(3N)^{1/3}$, $\\mu=1/3$</span>이다.' },
    [['$n(r)$ in the isotropic trap with $R^2=2\\mathcal E_F(0)/m\\bar\\omega^2$', '등방 덫의 $n(r)$, $R^2=2\\mathcal E_F(0)/m\\bar\\omega^2$', 0.3], ['Shell integral with the given value $\\pi/32$', '주어진 적분값 $\\pi/32$를 쓴 껍질 적분', 0.4], ['$\\mathcal E_F(0)=\\hbar\\bar\\omega(3N)^{1/3}$, $\\mu=1/3$', '$\\mathcal E_F(0)=\\hbar\\bar\\omega(3N)^{1/3}$, $\\mu=1/3$', 0.4]]],
  ['B.4', 0.9,
    { en: 'Express the ratio $\\dfrac{R(a=\\infty)}{R(a=0)}$ with $\\xi$ and deduce from the data of Fig. 2 an estimate of $\\xi$.',
      ko: '비 $\\dfrac{R(a=\\infty)}{R(a=0)}$를 $\\xi$로 나타내고, 그림 2의 자료로부터 $\\xi$를 어림하여라.' },
    { en: 'By A.8 the unitary gas is a free gas with $\\hbar\\to\\xi^{1/2}\\hbar$, so at equal $N$: $\\mathcal E_F(0)\\propto\\hbar$ (B.3) gives $\\mathcal E_F(0)\\to\\xi^{1/2}\\mathcal E_F(0)$, and $R\\propto\\mathcal E_F(0)^{1/2}$ (B.2) gives <span class="box">$\\dfrac{R(a=\\infty)}{R(a=0)}=\\xi^{1/4}$</span>. In Fig. 2 the profile at $8.45\\times10^{-2}$ T (closest to the resonance $8.32\\times10^{-2}$ T) reaches the baseline at about $\\pm0.11$, the non-interacting one at $10.2\\times10^{-2}$ T at about $\\pm0.14$: ratio $\\approx0.8$, so <span class="box">$\\xi\\approx0.8^4\\approx0.4$</span> (any value from 0.3 to 0.5 obtained this way is accepted; the measured value is $\\xi\\approx0.37$).',
      ko: 'A.8에서 유니터리 기체는 $\\hbar\\to\\xi^{1/2}\\hbar$로 바꾼 자유 기체이다. 같은 $N$에서 $\\mathcal E_F(0)\\propto\\hbar$(B.3)이므로 $\\mathcal E_F(0)\\to\\xi^{1/2}\\mathcal E_F(0)$이고, $R\\propto\\mathcal E_F(0)^{1/2}$(B.2)이므로 <span class="box">$\\dfrac{R(a=\\infty)}{R(a=0)}=\\xi^{1/4}$</span>이다. 그림 2에서 공명($8.32\\times10^{-2}$ T)에 가장 가까운 $8.45\\times10^{-2}$ T의 분포는 약 $\\pm0.11$에서, 상호작용이 없는 $10.2\\times10^{-2}$ T의 분포는 약 $\\pm0.14$에서 바닥선에 닿는다. 비 $\\approx0.8$이므로 <span class="box">$\\xi\\approx0.8^4\\approx0.4$</span>이다(이 방법으로 얻은 0.3–0.5의 값은 인정; 측정값은 $\\xi\\approx0.37$).' },
    [['$\\mathcal E_F(0)\\to\\xi^{1/2}\\mathcal E_F(0)$ at equal $N$', '같은 $N$에서 $\\mathcal E_F(0)\\to\\xi^{1/2}\\mathcal E_F(0)$', 0.2], ['$R(\\infty)/R(0)=\\xi^{1/4}$', '$R(\\infty)/R(0)=\\xi^{1/4}$', 0.3],
     ['Radii read from the profiles at $8.45$ and $10.2\\times10^{-2}$ T (ratio $\\approx0.8$)', '$8.45$와 $10.2\\times10^{-2}$ T 분포에서 반지름 읽기 (비 $\\approx0.8$)', 0.2], ['$\\xi$ between 0.3 and 0.5', '$\\xi$가 0.3–0.5', 0.2]]],
];

const total = ITEMS.reduce((n, it) => n + it[1], 0);
if (Math.abs(total - 10) > 1e-9) throw new Error('T4 points add up to ' + total);
for (const [label, pts, , , scheme] of ITEMS) {
  const s = scheme.reduce((n, r) => n + r[2], 0);
  if (Math.abs(s - pts) > 1e-9) throw new Error(`${label}: scheme ${s} ≠ ${pts}`);
}

function body(lang) {
  const t = T[lang], out = [`<h1>${t.title}</h1>`, t.intro];
  for (const [label, pts, qq, ss, scheme] of ITEMS) {
    if (label === 'A.1') out.push(`<h2>${t.A}</h2>`);
    if (label === 'B.1') out.push(`<h2>${t.B}</h2>`);
    out.push(q(label, qq[lang], `${pts.toFixed(1)}pt`), sol(ss[lang], lang),
      ms(scheme.map(([en, ko, p]) => [lang === 'ko' ? ko : en, p]), lang));
  }
  return out.join('\n');
}

module.exports = {
  docs: [
    { out: 'pdfx/ipho/IPhO_2025_T4S.pdf', style: 'ipho2025', kind: 'solution', lang: 'en', code: 'Q4', section: 'Theory-Backup · Solution',
      langLabel: 'English', html: body('en') },
    { out: 'pdfx/ipho/IPhO_2025_T4_S_KO.pdf', style: 'ipho2025', kind: 'solution', lang: 'ko', code: 'Q4', section: 'Theory-Backup · 풀이',
      langLabel: 'Korean (Korea (Republic of))', html: body('ko') },
  ],
  ITEMS,
};
