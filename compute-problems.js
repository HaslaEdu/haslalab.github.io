/* HaslaLab computational physics problems. Each problem asks for a Python function; `grader` is Python
   that defines grade(ns) -> {"tests":[{name, ok, got, want, note}], "plot":{...}|None}. The grader checks
   physics (analytic solutions, conservation laws, reference integrations), not one exact algorithm.
   `area`/`subtopic`/`step` place the problem on the learning path (learn-path.js). */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.HL_COMPUTE_PROBLEMS=api;
})(typeof globalThis==='object'?globalThis:this,function(){
  'use strict';
  /* shared Python helpers, prepended to every grader */
  const COMMON=String.raw`
import math, json
def _rel(a,b):
    return abs(a-b)/max(abs(b),1e-300)
def _num(x):
    try:
        return float(x)
    except Exception:
        return None
def _test(name, ok, got=None, want=None, note=""):
    def f(v):
        if v is None: return None
        if isinstance(v, float): return float("%.6g" % v)
        return v
    return {"name": name, "ok": bool(ok), "got": f(got), "want": f(want), "note": note}
def _need(ns, name):
    if name not in ns or not callable(ns[name]):
        raise NameError("함수 %s 를 정의하세요 / define the function %s" % (name, name))
    return ns[name]
def _series(xs, ys, label, limit=600):
    xs=list(map(float,xs)); ys=list(map(float,ys))
    n=min(len(xs),len(ys))
    stride=max(1, n//limit)
    return {"x": xs[:n:stride], "y": ys[:n:stride], "label": label}
`;
  const P=[
    {id:'rc-discharge',area:'em',subtopic:'dc_circuits',step:4,
      title:{ko:'RC 회로의 방전',en:'Discharging an RC circuit'},
      statement:{ko:'전하 $Q_0$로 충전된 축전기(전기 용량 $C$)가 저항 $R$을 통해 방전합니다. 회로 방정식은 $\\dfrac{dQ}{dt}=-\\dfrac{Q}{RC}$입니다.\n\n시간 간격 `dt`로 시각 `T`까지 수치 적분해, 매 단계의 전하를 담은 리스트 `[Q(0), Q(dt), Q(2dt), …]`를 돌려주는 함수 `charge(Q0, R, C, dt, T)`를 작성하세요.\n\n채점: 마지막 값이 해석해 $Q_0e^{-T/RC}$와 상대 오차 $10^{-3}$ 안에서 같아야 합니다.',
        en:'A capacitor $C$ charged to $Q_0$ discharges through a resistor $R$: $\\dfrac{dQ}{dt}=-\\dfrac{Q}{RC}$.\n\nWrite `charge(Q0, R, C, dt, T)` that integrates with step `dt` up to time `T` and returns the list `[Q(0), Q(dt), Q(2dt), …]`.\n\nGrading: the last value must match $Q_0e^{-T/RC}$ within a relative error of $10^{-3}$.'},
      starter:'def charge(Q0, R, C, dt, T):\n    """매 단계의 전하 리스트를 돌려주세요."""\n    Q = Q0\n    out = [Q]\n    steps = round(T / dt)\n    for _ in range(steps):\n        # TODO: dQ/dt = -Q/(RC)\n        out.append(Q)\n    return out\n',
      grader:String.raw`
def grade(ns):
    f=_need(ns,"charge"); tests=[]; plot=None
    for (Q0,R,C,dt,T) in [(1.0,1.0,1.0,1e-4,1.0),(5e-6,2e3,1e-6,1e-6,5e-3),(2.0,10.0,0.5,1e-3,20.0)]:
        out=list(f(Q0,R,C,dt,T)); want=Q0*math.exp(-T/(R*C)); got=_num(out[-1]) if out else None
        n_ok=abs(len(out)-(round(T/dt)+1))<=1
        tests.append(_test("Q0=%g, RC=%g, T=%g"%(Q0,R*C,T), got is not None and n_ok and _rel(got,want)<1e-3, got, want, "" if n_ok else "리스트 길이가 단계 수+1이 아닙니다 / list length is not steps+1"))
        if plot is None and out:
            ts=[i*dt for i in range(len(out))]
            plot={"xlabel":"t","ylabel":"Q","series":[_series(ts,out,"numerical"),_series(ts,[Q0*math.exp(-t/(R*C)) for t in ts],"exact")]}
    return {"tests":tests,"plot":plot}
`},
    {id:'drag-projectile',area:'mechanics',subtopic:'kinematics',step:4,
      title:{ko:'공기 저항이 있는 포물선 운동',en:'Projectile with air drag'},
      statement:{ko:'질량 1인 공을 속력 `v0`, 각도 `angle_deg`로 던집니다. 중력 $g=9.8$과 속도에 비례하는 저항이 작용합니다: $\\vec a=-g\\hat y-k\\vec v$.\n\n공이 다시 $y=0$에 닿을 때까지 시간 간격 `dt`로 적분하고, `(xs, ys, R)`를 돌려주는 함수 `trajectory(v0, angle_deg, k, dt)`를 작성하세요. `R`은 수평 도달 거리입니다(마지막 두 점 사이를 선형 보간하면 정확해집니다).\n\n채점: 정밀하게 계산한 기준값과 상대 오차 0.5% 안.',
        en:'A unit-mass ball is thrown at speed `v0` and angle `angle_deg` under gravity $g=9.8$ and linear drag: $\\vec a=-g\\hat y-k\\vec v$.\n\nWrite `trajectory(v0, angle_deg, k, dt)` that integrates with step `dt` until the ball returns to $y=0$ and returns `(xs, ys, R)`, where `R` is the horizontal range (interpolate between the last two points).\n\nGrading: within 0.5% of a precise reference.'},
      starter:'import math\n\ndef trajectory(v0, angle_deg, k, dt):\n    g = 9.8\n    th = math.radians(angle_deg)\n    x, y = 0.0, 0.0\n    vx, vy = v0 * math.cos(th), v0 * math.sin(th)\n    xs, ys = [x], [y]\n    while True:\n        # TODO: 가속도를 구하고 위치와 속도를 갱신하세요\n        break\n    R = x\n    return xs, ys, R\n',
      grader:String.raw`
def _ref_range(v0,ang,k):
    g=9.8; th=math.radians(ang); s=[0.0,0.0,v0*math.cos(th),v0*math.sin(th)]; h=1e-4
    def d(s): return [s[2],s[3],-k*s[2],-g-k*s[3]]
    while True:
        k1=d(s); k2=d([s[i]+h/2*k1[i] for i in range(4)]); k3=d([s[i]+h/2*k2[i] for i in range(4)]); k4=d([s[i]+h*k3[i] for i in range(4)])
        n=[s[i]+h/6*(k1[i]+2*k2[i]+2*k3[i]+k4[i]) for i in range(4)]
        if n[1]<0 and n[3]<0:
            return s[0]+(n[0]-s[0])*s[1]/(s[1]-n[1])
        s=n
def grade(ns):
    f=_need(ns,"trajectory"); tests=[]; plot={"xlabel":"x","ylabel":"y","series":[]}
    for (v0,ang,k) in [(20.0,45.0,0.0),(20.0,45.0,0.3),(35.0,30.0,0.8),(10.0,70.0,1.5)]:
        xs,ys,R=f(v0,ang,k,1e-3); want=_ref_range(v0,ang,k); got=_num(R)
        tests.append(_test("v0=%g, %g°, k=%g"%(v0,ang,k), got is not None and _rel(got,want)<5e-3, got, want))
        if len(plot["series"])<2: plot["series"].append(_series(xs,ys,"k=%g"%k))
    return {"tests":tests,"plot":plot}
`},
    {id:'pendulum-period',area:'waves',subtopic:'shm',step:5,
      title:{ko:'큰 진폭 진자의 주기',en:'Period of a large-amplitude pendulum'},
      statement:{ko:'길이 `L`인 단진자를 각도 `theta0_deg`에서 가만히 놓습니다. 운동 방정식은 $\\ddot\\theta=-\\dfrac{g}{L}\\sin\\theta$입니다. 진폭이 크면 주기가 $2\\pi\\sqrt{L/g}$보다 길어집니다.\n\n수치 적분으로 주기를 구해 돌려주는 함수 `period(theta0_deg, L, g)`를 작성하세요. (힌트: $\\theta$가 처음으로 0을 지나는 시각이 주기의 1/4입니다.)\n\n채점: 타원 적분으로 구한 정확한 주기와 상대 오차 $10^{-4}$ 안. 진폭 170°까지 검사합니다.',
        en:'A pendulum of length `L` is released from rest at `theta0_deg`: $\\ddot\\theta=-\\dfrac{g}{L}\\sin\\theta$. At large amplitude the period exceeds $2\\pi\\sqrt{L/g}$.\n\nWrite `period(theta0_deg, L, g)` that finds the period numerically. (Hint: the first zero crossing of $\\theta$ is a quarter period.)\n\nGrading: within $10^{-4}$ of the exact period from the elliptic integral, up to 170°.'},
      starter:'import math\n\ndef period(theta0_deg, L, g):\n    th = math.radians(theta0_deg)\n    w = 0.0\n    t = 0.0\n    dt = 1e-4\n    # TODO: th가 0을 지날 때까지 적분하고 그 시각의 4배를 돌려주세요\n    return 2 * math.pi * math.sqrt(L / g)\n',
      grader:String.raw`
def _exact_period(th0,L,g):
    k=math.sin(math.radians(th0)/2); a,b=1.0,math.sqrt(1-k*k)
    for _ in range(40): a,b=(a+b)/2,math.sqrt(a*b)
    return 4*math.sqrt(L/g)*math.pi/(2*a)
def grade(ns):
    f=_need(ns,"period"); tests=[]; xs=[]; ys=[]; ex=[]
    for (th,L,g) in [(5.0,1.0,9.8),(60.0,1.0,9.8),(120.0,2.0,9.8),(170.0,0.5,9.8),(90.0,1.0,1.62)]:
        want=_exact_period(th,L,g); got=_num(f(th,L,g))
        tests.append(_test("θ0=%g°, L=%g, g=%g"%(th,L,g), got is not None and _rel(got,want)<1e-4, got, want))
    for th in range(5,176,10):
        T=_num(f(float(th),1.0,9.8)); xs.append(th); ys.append(T if T is not None else 0.0); ex.append(_exact_period(th,1.0,9.8))
    return {"tests":tests,"plot":{"xlabel":"θ0 (°)","ylabel":"T (s)","series":[_series(xs,ys,"yours"),_series(xs,ex,"exact")]}}
`},
    {id:'kepler-orbit',area:'mechanics',subtopic:'gravitation',step:6,
      title:{ko:'궤도와 에너지 보존',en:'An orbit that conserves energy'},
      statement:{ko:'$GM=1$인 중심 천체 주위의 궤도를 계산합니다: $\\ddot{\\vec r}=-\\vec r/|\\vec r|^3$. 처음 위치 $(r_0,0)$, 속도 $(0,v_0)$에서 시작해 시간 간격 `dt`로 `steps`단계 적분하고 `(xs, ys, vxs, vys)`를 돌려주는 함수 `orbit(r0, v0, dt, steps)`를 작성하세요.\n\n채점:\n1. 원 궤도($r_0=1, v_0=1$)는 한 주기($2\\pi$) 뒤 출발점으로 돌아와야 합니다(거리 $10^{-3}$ 안).\n2. 타원 궤도 20바퀴 동안 역학적 에너지의 상대 변화가 $10^{-4}$ 이하여야 합니다.\n\n오일러 방법으로는 2번을 통과할 수 없습니다. 속도 베를레나 RK4를 써 보세요.',
        en:'Integrate an orbit around a body with $GM=1$: $\\ddot{\\vec r}=-\\vec r/|\\vec r|^3$, starting at $(r_0,0)$ with velocity $(0,v_0)$. Write `orbit(r0, v0, dt, steps)` returning `(xs, ys, vxs, vys)`.\n\nGrading:\n1. The circular orbit ($r_0=1, v_0=1$) returns to its start after one period $2\\pi$ (within $10^{-3}$).\n2. Over 20 revolutions of an ellipse the relative energy change stays below $10^{-4}$.\n\nEuler’s method cannot pass test 2; try velocity Verlet or RK4.'},
      starter:'def orbit(r0, v0, dt, steps):\n    x, y, vx, vy = r0, 0.0, 0.0, v0\n    xs, ys, vxs, vys = [x], [y], [vx], [vy]\n    for _ in range(steps):\n        r3 = (x * x + y * y) ** 1.5\n        ax, ay = -x / r3, -y / r3\n        # 오일러 방법: 에너지가 보존되지 않습니다. 더 나은 방법으로 바꿔 보세요.\n        x, y = x + vx * dt, y + vy * dt\n        vx, vy = vx + ax * dt, vy + ay * dt\n        xs.append(x); ys.append(y); vxs.append(vx); vys.append(vy)\n    return xs, ys, vxs, vys\n',
      grader:String.raw`
def grade(ns):
    f=_need(ns,"orbit"); tests=[]
    dt=1e-3; n=round(2*math.pi/dt)
    xs,ys,vxs,vys=f(1.0,1.0,dt,n)
    # the last sample sits up to dt/2 off the exact period; allow for it
    d=math.hypot(_num(xs[-1])-1.0,_num(ys[-1])-0.0)
    tests.append(_test("원 궤도 한 바퀴 / one circular period", d<1e-3+dt, d, 0.0, "출발점까지 거리 / distance from start"))
    r0,v0=1.0,1.2; a=1/(2/r0-v0*v0); T=2*math.pi*a**1.5; dt=2e-3; n=round(20*T/dt)
    xs,ys,vxs,vys=f(r0,v0,dt,n)
    E=[0.5*(_num(vxs[i])**2+_num(vys[i])**2)-1/math.hypot(_num(xs[i]),_num(ys[i])) for i in range(0,len(xs),max(1,len(xs)//2000))]
    drift=max(abs(e-E[0]) for e in E)/abs(E[0])
    tests.append(_test("타원 20바퀴 에너지 / energy over 20 ellipses", drift<1e-4, drift, 1e-4, "최대 상대 변화 / max relative change"))
    tests.append(_test("반환 길이 / returned length", len(xs)==n+1, len(xs), n+1))
    return {"tests":tests,"plot":{"xlabel":"x","ylabel":"y","aspect":"equal","series":[_series(xs,ys,"orbit",1500)]}}
`},
    {id:'random-walk',area:'thermal',subtopic:'kinetic_theory',step:5,
      title:{ko:'무작위 걸음과 확산',en:'Random walks and diffusion'},
      statement:{ko:'2차원 격자 위에서 `n_walkers`명이 동시에 출발해, 매 단계 상하좌우 중 하나로 한 칸씩 무작위로 움직입니다.\n\n단계 $n=0,1,\\dots,$`n_steps`마다 평균 제곱 변위 $\\langle r^2\\rangle$를 담은 리스트를 돌려주는 함수 `msd(n_walkers, n_steps, seed)`를 작성하세요. 이론적으로 $\\langle r^2\\rangle=n$입니다.\n\n채점: 4000명, 400단계에서 마지막 값이 400과 6% 안이고, 기울기가 1에 가까워야 합니다. numpy를 써도 됩니다.',
        en:'`n_walkers` walkers start together on a 2-D lattice and each step one site up, down, left or right at random.\n\nWrite `msd(n_walkers, n_steps, seed)` returning the mean squared displacement $\\langle r^2\\rangle$ for $n=0,1,\\dots,$`n_steps`. Theory: $\\langle r^2\\rangle=n$.\n\nGrading: with 4000 walkers and 400 steps the last value is within 6% of 400 and the slope is close to 1. numpy is allowed.'},
      starter:'import random\n\ndef msd(n_walkers, n_steps, seed):\n    rng = random.Random(seed)\n    xs = [0] * n_walkers\n    ys = [0] * n_walkers\n    out = [0.0]\n    for _ in range(n_steps):\n        # TODO: 각 걸음꾼을 한 칸씩 움직이고 평균 r^2를 기록하세요\n        out.append(0.0)\n    return out\n',
      grader:String.raw`
def grade(ns):
    f=_need(ns,"msd"); tests=[]
    out=[_num(v) for v in f(4000,400,7)]
    tests.append(_test("반환 길이 / returned length", len(out)==401, len(out), 401))
    tests.append(_test("<r²>(0) = 0", out and abs(out[0])<1e-12, out[0] if out else None, 0.0))
    last=out[-1] if out else None
    tests.append(_test("<r²>(400) ≈ 400", last is not None and _rel(last,400.0)<0.06, last, 400.0))
    n=len(out); sx=sum(range(n)); sy=sum(out); sxx=sum(i*i for i in range(n)); sxy=sum(i*out[i] for i in range(n))
    slope=(n*sxy-sx*sy)/(n*sxx-sx*sx) if n>1 else None
    tests.append(_test("기울기 / slope ≈ 1", slope is not None and abs(slope-1)<0.06, slope, 1.0))
    return {"tests":tests,"plot":{"xlabel":"n","ylabel":"<r²>","series":[_series(range(n),out,"simulation"),_series(range(n),range(n),"theory")]}}
`},
    {id:'heat-rod',area:'thermal',subtopic:'heat_transfer',step:7,
      title:{ko:'막대의 열전도 (유한 차분)',en:'Heat flow in a rod (finite differences)'},
      statement:{ko:'길이 1인 막대의 온도 $u(x,t)$가 $\\partial_t u=\\alpha\\,\\partial_x^2u$를 따릅니다. 양 끝은 $u=0$으로 고정되어 있고 처음 온도는 $u(x,0)=\\sin\\pi x$입니다.\n\n격자점 $x_j=j/N$ $(j=0,\\dots,N)$ 위에서 시간 간격 `dt`로 `steps`단계 계산하고, 마지막 온도 리스트(길이 $N+1$)를 돌려주는 함수 `heat(N, alpha, dt, steps)`를 작성하세요.\n\n채점: 정확해 $e^{-\\alpha\\pi^2t}\\sin\\pi x$와 최대 오차 $2\\times10^{-3}$ 안. 안정 조건 $\\alpha\\,dt/\\Delta x^2\\le1/2$을 생각해 보세요.',
        en:'The temperature of a unit rod obeys $\\partial_t u=\\alpha\\,\\partial_x^2u$ with $u=0$ at both ends and $u(x,0)=\\sin\\pi x$.\n\nWrite `heat(N, alpha, dt, steps)` that advances the grid $x_j=j/N$ $(j=0,\\dots,N)$ by `steps` steps of `dt` and returns the final temperatures (length $N+1$).\n\nGrading: maximum error below $2\\times10^{-3}$ against $e^{-\\alpha\\pi^2t}\\sin\\pi x$. Mind the stability limit $\\alpha\\,dt/\\Delta x^2\\le1/2$.'},
      starter:'import math\n\ndef heat(N, alpha, dt, steps):\n    dx = 1.0 / N\n    u = [math.sin(math.pi * j * dx) for j in range(N + 1)]\n    for _ in range(steps):\n        # TODO: 명시적(FTCS) 갱신, 양 끝은 0\n        pass\n    return u\n',
      grader:String.raw`
def grade(ns):
    f=_need(ns,"heat"); tests=[]; plot=None
    for (N,alpha,dt,steps) in [(50,1.0,1e-4,500),(40,0.5,2e-4,1000),(100,0.1,1e-3,2000)]:
        u=[_num(v) for v in f(N,alpha,dt,steps)]; t=dt*steps
        exact=[math.exp(-alpha*math.pi**2*t)*math.sin(math.pi*j/N) for j in range(N+1)]
        ok_len=len(u)==N+1
        err=max(abs(u[j]-exact[j]) for j in range(N+1)) if ok_len else None
        tests.append(_test("N=%d, α=%g, t=%g"%(N,alpha,t), ok_len and err<2e-3, err, 2e-3, "최대 오차 / max error"))
        if plot is None and ok_len:
            xs=[j/N for j in range(N+1)]
            plot={"xlabel":"x","ylabel":"u","series":[_series(xs,u,"numerical"),_series(xs,exact,"exact")]}
    return {"tests":tests,"plot":plot}
`}
  ];
  return{VERSION:'compute-v1',COMMON,PROBLEMS:P,byId:id=>P.find(p=>p.id===id)||null};
});
