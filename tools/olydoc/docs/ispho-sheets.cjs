/* ISPhO answer sheets and working sheets that the olympiad did not publish (2023–2025), and the working sheets of 2026.
 *
 *     node tools/olydoc/build.cjs tools/olydoc/docs/ispho-sheets.cjs && python3 -I tools/olydoc/ispho_sheets.py
 *
 * 2023–2025 are set as the official 2026 answer sheets are (style «ispho»: «Theory»/«Experiment», the logo, «A1-1»,
 * the language, a 2 pt rule; a box per question with its label, points «(0.2pt)» — in Korean too, as the official IPhO
 * 2025 Korean sheets — and what is to be written in it).  The
 * questions, their points and what each asks for are read from the official papers and solutions; where a question
 * hands its result over as a file (the 2024–2025 experiments were sat on a computer), the sheet gives the table or the
 * graph paper to write it on.  A working sheet is the answer sheet's head with «W» for «A» and one empty frame, the
 * size of the frames on page 7 of the 2026 theory sheets.  Every page carries the scanner's four corner squares
 * (stamp.py).  ISPhO 2024 T2 and T3 published no points: their boxes carry the label only.
 * tools/olydoc/ispho_sheets.py then joins each year's theory sheets into the whole paper's (TA, T_W) and finishes 2026. */
const L = (en, ko) => ({ en, ko: ko ?? en });
const v = m => ({ v: m });
const pair = (a, b) => ({ pair: [a, b] });
const fv = m => ({ fv: m });
const EQ = { txt: L('Equation:', '식:') };
const sp = h => ({ space: h });
const plot = h => ({ plot: h || 150 });
const plots = (caps, h) => ({ plots: caps, h: h || 140 });
const tbl = (cols, rows) => ({ table: { cols, rows } });
const txt = (en, ko) => ({ txt: L(en, ko) });
const LOW = L('Low-current mode:', '저전류 모드:'), HIGH = L('High-current mode:', '고전류 모드:');
const VV = (n, unit) => tbl(['$V_1$ (\u2003\u2003)', '$V_2$ (\u2003\u2003)'], n);
const IU = [txt('$I=$', '$I=$'), txt('$U=$', '$U=$')];

/* ─────────────────────────── ISPhO 2025 ─────────────────────────── */
const Y2025 = [
  { q: 1, kind: 'T', title: L('Ferromagnetic domain wall dynamics', '강자성 도메인벽 동역학'), parts: [
    { t: L('Part A. Single magnetic moment', 'Part A. 단일 자기 모멘트'), pts: 2.0, items: [
      ['A.1', 0.3, sp(34)],
      ['A.2', 0.9, v('m_z(t)=')],
      ['A.3', 0.8, v('\\Omega=')]] },
    { t: L('Part B. Static domain wall', 'Part B. 정적 도메인벽'), pts: 3.5, items: [
      ['B.1', 0.5, fv('B_{\\rm ex}='), fv('B_{\\rm an}='), fv('\\omega=')],
      ['B.2', 1.0, pair('\\alpha=', 'T='), v('d=')],
      ['B.3', 1.5, tbl(['$\\beta$', '$d$'], 6)],
      ['B.4', 0.5, v('c=')]] },
    { t: L('Part C. Domain wall motion in external field', 'Part C. 외부 자기장 속 도메인벽 운동'), pts: 4.5, items: [
      ['C.1', 0.2, txt('Direction (to the right / to the left):', '방향 (오른쪽 / 왼쪽):')],
      ['C.2', 2.0, tbl(['$b$', '$v$', '$\\varphi$'], 8)],
      ['C.3', 0.4, plot(170), v('dv/db=')],
      ['C.4', 0.6, plot(170), pair('v_c=', 'b_{\\rm cr}=')],
      ['C.5', 0.3, pair('v_c=', 'B_{\\rm cr}=')],
      ['C.6', 1.0, tbl(['$t$', '$x$'], 8), plot(170)]] }] },
  { q: 2, kind: 'T', title: L('Vibrational structure of polyynes', '폴리인의 진동 구조'), parts: [
    { t: L('Part A. An infinite chain of carbon atoms', 'Part A. 무한한 탄소 원자 사슬'), pts: 6.5, items: [
      ['A.1', 0.8, v('E='), sp(12)],
      ['A.2', 0.8, v('m\\ddot u_n='), v('m\\ddot v_n=')],
      ['A.3', 0.9, pair('a=', 'b='), pair('c=', 'd=')],
      ['A.4', 1.0, v('\\omega_1/\\omega_0='), v('\\omega_2/\\omega_0=')],
      ['A.5', 1.0, v('\\omega_1/\\omega_0\\approx'), v('\\omega_2/\\omega_0\\approx')],
      ['A.6', 1.0, v('\\omega_1/\\omega_0\\approx'), v('\\omega_2/\\omega_0\\approx')],
      ['A.7', 1.0, plots(['$\\alpha=0.5,\\ \\beta=0.1$', '$\\alpha=0.5,\\ \\beta=3.0$'], 150)]] },
    { t: L('Part B. Spectroscopy of polyynes', 'Part B. 폴리인의 분광학'), pts: 3.5, items: [
      ['B.1', 0.8, EQ, sp(30)],
      ['B.2', 0.7, v('q_l=')],
      ['B.3', 2.0, txt('Single bond:', '단일 결합:'), txt('Triple bond:', '삼중 결합:')]] }] },
  { q: 3, kind: 'T', title: L('Single-electron transistor', '단전자 트랜지스터'), parts: [
    { t: L('Part A. Tunneling effect', 'Part A. 터널 효과'), pts: 3.0, items: [
      ['A.1', 0.1, pair('W=', '\\Delta W=')],
      ['A.2', 0.3, pair('q_g=', 'q_j=')],
      ['A.3', 0.3, v('\\Delta E=')],
      ['A.4', 0.5, pair('A=', 'Q=')],
      ['A.5', 0.5, v('I_t='), txt('Condition on $n$:', '$n$에 대한 조건:')],
      ['A.6', 0.3, v('I=')],
      ['A.7', 1.0, plot(190)]] },
    { t: L('Part B. Single-electron transistor', 'Part B. 단전자 트랜지스터'), pts: 4.5, items: [
      ['B.1', 0.2, v('\\varphi=')],
      ['B.2', 1.0, v('A=')],
      ['B.3', 1.0, v('Q=')],
      ['B.4', 0.3, txt('Condition:', '조건:')],
      ['B.5', 1.5, txt('Conditions:', '조건:'), sp(24), plot(190)],
      ['B.6', 0.5, v('I(V_g,V)=')]] },
    { t: L('Part C. Tunneling at finite temperature', 'Part C. 유한 온도에서의 터널링'), pts: 2.5, items: [
      ['C.1', 0.5, pair('C_1=C_2=', 'C_g=')],
      ['C.2', 0.3, v('dp(n)/dt=')],
      ['C.3', 0.5, v('p(n+1)=')],
      ['C.4', 0.3, sp(34)],
      ['C.5', 0.5, pair('p(0)=', 'p(1)=')],
      ['C.6', 0.4, v('I=')]] }] },
  { q: 1, kind: 'E', title: L('LED Color', 'LED의 색'), parts: [
    { t: L('Part A. Calibration', 'Part A. 보정'), pts: 0.6, items: [
      ['A.1', 0.3, txt('Spectra saved: R.csv\u2003G.csv\u2003B.csv', '저장한 스펙트럼: R.csv\u2003G.csv\u2003B.csv')],
      ['A.2', 0.1, tbl([L('Colour', '색'), '$N$'], [L('Red', '빨강'), L('Green', '초록'), L('Blue', '파랑')])],
      ['A.3', 0.2, pair('\\text{slope}=', '\\text{shift}=')]] },
    { t: L('Part B. LED in air', 'Part B. 공기 중의 LED'), pts: 5.3, items: [
      ['B.1', 0.1, tbl([L('Range, V', '측정 범위, V'), '$R_V$'], ['600', '200', '20', '2', '200m'])],
      ['B.2', 0.1, pair('R_0=', 'U_{100\\,{\\rm mA}}=')],
      ['B.3', 0.3, txt('Circuit:', '회로도:'), sp(110)],
      ['B.4', 0.6, VV(10)],
      ['B.5', 0.1, { diode: true }],
      ['B.6', 0.3, txt('Circuit:', '회로도:'), sp(110)],
      ['B.7', 0.9, VV(15)],
      ['B.8', 0.4, { txt: LOW }, ...IU, { txt: HIGH }, ...IU],
      ['B.9', 0.2, plot(190)],
      ['B.10', 0.1, v('\\eta_0k_BT_0/e=')],
      ['B.11', 0.3, v('\\eta_{\\rm room}=')],
      ['B.12', 0.8, tbl(['$I$, mA', '$\\lambda$, nm'], 7)],
      ['B.13', 0.8, txt('Time series saved:', '저장한 시계열:'), sp(12)],
      ['B.14', 0.3, tbl(['$t$, s', '$\\lambda$, nm'], 10), plot(170)]] },
    { t: L('Part C. LED in water', 'Part C. 물속의 LED'), pts: 3.5, items: [
      ['C.1', 0.9, VV(15)],
      ['C.2', 0.2, ...IU],
      ['C.3', 0.5, plot(190)],
      ['C.4', 0.8, tbl(['$I$, mA', '$\\lambda$, nm'], 7)],
      ['C.5', 0.8, txt('Time series saved:', '저장한 시계열:'), sp(12)],
      ['C.6', 0.3, tbl(['$t$, s', '$\\lambda$, nm'], 10)]] },
    { t: L('Part D. LED in liquid nitrogen', 'Part D. 액체 질소 속의 LED'), pts: 6.1, items: [
      ['D.1', 0.1, txt('Spectrum saved:', '저장한 스펙트럼:')],
      ['D.2', 0.6, VV(10)],
      ['D.3', 0.9, VV(15)],
      ['D.4', 0.2, { txt: LOW }, ...IU, { txt: HIGH }, ...IU],
      ['D.5', 0.2, plot(190)],
      ['D.6', 0.3, v('\\eta_{\\rm N_2}=')],
      ['D.7', 1.0, tbl(['$I$, mA', L('Spectrum file', '스펙트럼 파일')], 7)],
      ['D.8', 0.5, tbl(['$I$, mA', '$\\lambda$, nm'], 7)],
      ['D.9', 1.0, plot(200)],
      ['D.10', 0.6, pair('\\lambda_{\\rm N_2}=', '\\lambda_{\\rm room}=')],
      ['D.11', 0.7, pair('E_0=', '\\alpha=')]] },
    { t: L('Part E. Calculation of calorimetric parameters', 'Part E. 열량 측정 매개변수 계산'), pts: 3.1, items: [
      ['E.1', 0.5, fv('\\chi=')],
      ['E.2', 0.5, v('\\varkappa_{\\rm air}/\\varkappa_{\\rm water}=')],
      ['E.3', 0.3, v('T(t)=')],
      ['E.4', 1.0, tbl([L('$t$, s (air)', '$t$, s (공기)'), '$T$', L('$t$, s (water)', '$t$, s (물)'), '$T$'], 10)],
      ['E.5', 0.5, plots([L('Air', '공기'), L('Water', '물')], 150)],
      ['E.6', 0.3, v('C_{\\rm air}/C_{\\rm water}=')]] },
    { t: L('Part F. Temperature dependence of saturation current', 'Part F. 포화 전류의 온도 의존성'), pts: 1.4, items: [
      ['F.1', 0.6, tbl(['$T$', '$\\ln(I_0/{\\rm mA})$'], 7), plot(160)],
      ['F.2', 0.6, tbl(['$T$', '$\\ln(I_0/{\\rm mA})$'], 7), plot(160)],
      ['F.3', 0.2, txt('Factor:', '배수:')]] }] },
];

/* ─────────────────────────── ISPhO 2024 ─────────────────────────── */
const Y2024 = [
  { q: 1, kind: 'T', title: L('Thermal oxidation', '열 산화'), parts: [
    { t: L('Part A. Theoretical principles of ellipsometry', 'Part A. 엘립소미트리의 이론적 원리'), pts: 4.5, items: [
      ['A.1', 0.2, sp(34)],
      ['A.2', 0.4, v('k_{1x}='), v('k_{2x}='), v('k_{3x}=')],
      ['A.3', 0.6, EQ, sp(40)],
      ['A.4', 0.6, v('r_s='), pair('A=', 'B=')],
      ['A.5', 0.6, EQ, sp(40)],
      ['A.6', 0.6, v('r_p='), pair('A=', 'B=')],
      ['A.7', 1.5, v('\\theta_{\\rm opt}=')]] },
    { t: L('Part B. Kinetics of oxidation', 'Part B. 산화의 동역학'), pts: 5.5, items: [
      ['B.1', 0.7, pair('\\Phi=', 'd=')],
      ['B.2', 0.7, pair('\\Phi=', 'd=')],
      ['B.3', 0.3, tbl(['$t$, min', '$d$, nm'], 8)],
      ['B.4', 0.3, v('v=')],
      ['B.5', 0.5, v('C_0='), v('C_i=')],
      ['B.6', 0.5, EQ, sp(14), pair('A=', 'B='), v('\\tau=')],
      ['B.7', 1.0, tbl(['$T$', '$B$', '$B/A$'], 5)],
      ['B.8', 1.5, pair('\\Delta E_b=', '\\Delta E_a='), plots([L('$B$', '$B$'), L('$B/A$', '$B/A$')], 150)]] }] },
  { q: 2, kind: 'T', title: L('Memristors and NVRAM', '멤리스터와 NVRAM'), parts: [
    { t: L('Part A. Memristor', 'Part A. 멤리스터'), items: [
      ['A.1', null, v('\\dfrac{dx}{dt}=')],
      ['A.2', null, v('x_{0,\\min}=')],
      ['A.3', null, v('\\tau=')],
      ['A.4', null, v('Q=')]] },
    { t: L('Part B. Memristor hysteresis', 'Part B. 멤리스터 히스테리시스'), items: [
      ['B.1', null, v('x(t)='), v('\\Delta I(\\varphi)=')],
      ['B.2', null, v('s=')],
      ['B.3', null, pair('\\alpha=', '\\xi=')]] },
    { t: L('Part C. ReRAM energy efficiency', 'Part C. ReRAM 에너지 효율'), items: [
      ['C.1', null, v('\\tau=')],
      ['C.2', null, v('Q=')]] },
    { t: L('Part D. Segnetoelectrics and FeRAM', 'Part D. 강유전체와 FeRAM'), items: [
      ['D.1', null, pair('E_{\\rm cr}=', 'P_{\\rm cr}=')],
      ['D.2', null, v('P_{\\rm after}=')],
      ['D.3', null, v('Q=')],
      ['D.4', null, fv('Q_{1\\,{\\rm TiB}}=')]] }] },
  { q: 3, kind: 'T', title: L('Hydraulic jump', '도수 현상'), parts: [
    { t: L('Part A. Flow without energy loss', 'Part A. 에너지 손실 없는 흐름'), items: [
      ['A.1', null, v('E=')],
      ['A.2', null, v('d_c=')],
      ['A.3', null, pair('v_c=', '{\\rm Fr}_c=')],
      ['A.4', null, EQ, sp(26)],
      ['A.5', null, pair('\\Delta v/v_1=', '\\Delta d/d_1=')],
      ['A.6', null, txt('Velocity increases for:', '속도가 증가하는 경우:'), txt('Velocity decreases for:', '속도가 감소하는 경우:')]] },
    { t: L('Part B. Theory of hydraulic jumping', 'Part B. 도수 현상의 이론'), items: [
      ['B.1', null, v('F=')],
      ['B.2', null, EQ, sp(26)],
      ['B.3', null, v('d_2/d_1=')],
      ['B.4', null, v('\\Delta E=')],
      ['B.5', null, txt('A jump is possible for:', '도수가 가능한 경우:')]] },
    { t: L('Part C. Hydraulic jump in the sink', 'Part C. 싱크대에서의 도수 현상'), items: [
      ['C.1', null, fv('v=')],
      ['C.2', null, v('d(r)='), v('d(r_c)=')],
      ['C.3', null, pair('{\\rm Fr}=', 'd_2/d_1=')]] }] },
  { q: 1, kind: 'E', title: L('Absorption spectroscopy and chemical kinetics', '흡수 분광법과 화학 반응 속도론'), parts: [
    { t: L('Part A. Calibration', 'Part A. 보정'), pts: 1.7, items: [
      ['A.1', 0.1, txt('Spectrum saved: LED-CON.csv', '저장한 스펙트럼: LED-CON.csv')],
      ['A.2', 0.1, txt('Background saved: dark-A.csv', '저장한 배경: dark-A.csv')],
      ['A.3', 0.3, txt('Spectra saved: R-0.csv\u2003G-0.csv\u2003B-0.csv', '저장한 스펙트럼: R-0.csv\u2003G-0.csv\u2003B-0.csv')],
      ['A.4', 0.8, tbl([L('LED', 'LED'), '$\\lambda_{\\max}$, nm', '$N$'], [L('Red', '빨강'), L('Green', '초록'), L('Blue', '파랑')]), pair('a=', 'b=')],
      ['A.5', 0.4, v('\\lambda_{\\max}=')]] },
    { t: L('Part B. Beer–Lambert law', 'Part B. 비어–람베르트 법칙'), pts: 5.0, items: [
      ['B.1', 1.0, v('V_d=')],
      ['B.2', 0.2, txt('Spectra saved: src-B.csv\u2003dark-B.csv', '저장한 스펙트럼: src-B.csv\u2003dark-B.csv')],
      ['B.3', 0.4, txt('Wavelength range:', '파장 범위:')],
      ['B.4', 1.0, tbl([L('Drops', '방울 수'), L('File', '파일')], 10)],
      ['B.5', 0.4, v('\\beta(\\lambda)=')],
      ['B.6', 0.4, v('I_\\lambda=')],
      ['B.7', 1.4, tbl(['$\\lambda$, nm', '$\\sigma(\\lambda)$'], 10), plot(170)],
      ['B.8', 0.2, v('\\lambda_{\\max}=')]] },
    { t: L('Part C. Phenolphthalein', 'Part C. 페놀프탈레인'), pts: 6.7, items: [
      ['C.1', 0.1, v('J=')],
      ['C.2', 0.3, EQ],
      ['C.3', 0.3, EQ],
      ['C.4', 0.2, tbl([L('Cuvette', '큐벳'), L('NaOH, ml', 'NaOH, ml'), L('NaCl, ml', 'NaCl, ml'), L('Water, ml', '물, ml'), '$c$, mol/l'], 5)],
      ['C.5', 1.5, txt('Measurements done for all five solutions:', '다섯 용액 모두 측정:'), sp(12)],
      ['C.6', 0.3, v('\\lambda_{\\max,{\\rm In}}=')],
      ['C.7', 1.5, plot(200)],
      ['C.8', 2.0, plot(200)],
      ['C.9', 0.5, v('p=')]] },
    { t: L('Part D. Chemical traffic light', 'Part D. 화학 신호등'), pts: 6.6, items: [
      ['D.1', 0.4, tbl([L('Colour', '색'), L('Order', '번호'), '$t$, s'], [L('Green / cyan', '초록/청록'), L('Yellow', '노랑'), L('Red / orange', '빨강/주황'), L('Violet', '보라')])],
      ['D.2', 1.0, txt('Spectra saved: src-D.csv\u2003dark-D.csv\u2003time series', '저장한 스펙트럼: src-D.csv\u2003dark-D.csv\u2003시계열')],
      ['D.3', 1.2, plots(['$\\beta_1(\\lambda),\\ \\beta_2(\\lambda)$', '$\\beta_3(\\lambda),\\ \\beta_4(\\lambda)$'], 150)],
      ['D.4', 1.0, txt('Number of states:', '상태의 수:')],
      ['D.5', 3.0, plot(220)]] }] },
];

/* ─────────────────────────── ISPhO 2023 ─────────────────────────── */
const Y2023 = [
  { q: 1, kind: 'T', title: L('Polycrystal diffusion', '다결정 확산'), parts: [
    { t: L('Part A. Temperature dependence of the diffusion coefficient', 'Part A. 확산 계수의 온도 의존성'), pts: 2.6, items: [
      ['A1', 0.2, v('v='), v('D(T)\\propto')],
      ['A2', 0.4, v('\\Delta r_{\\rm sq}=')],
      ['A3', 2.0, tbl(['$T$', '$t$', '$N$', '$\\Delta r_{\\rm sq}$', '$D$'], 8), v('E_g='), txt('Accuracy:', '정확도:')]] },
    { t: L('Part B. Effective diffusion coefficient', 'Part B. 유효 확산 계수'), pts: 2.4, items: [
      ['B1', 0.4, v('\\alpha=')],
      ['B2', 2.0, tbl(['$t$', '$D_{gb}/D$', '$\\delta$', '$\\alpha$'], 6), v('\\alpha=')]] },
    { t: L('Part C. Type B kinetics', 'Part C. B형 운동학'), pts: 5, items: [
      ['C1', 0.4, sp(30)],
      ['C2', 4.0, tbl(['$t$', '$D_{gb}/D$', '$\\delta$', '$\\ln\\bar c$'], 8), pair('\\xi=', '\\eta='), v('\\zeta=')],
      ['C3', 0.6, v('C=')]] }] },
  { q: 2, kind: 'T', title: L('Muon anomalous magnetic moment', '뮤온의 비정상 자기 모멘트'), parts: [
    { t: L('Part A. Dynamics in magnetic field', 'Part A. 자기장 속에서의 동역학'), pts: 4.5, items: [
      ['A1', 1.0, fv('\\Delta v=')],
      ['A2', 0.5, fv('E_k=')],
      ['A3', 1.0, fv('R='), fv('T=')],
      ['A4', 0.8, fv('N=')],
      ['A5', 0.7, v('d\\vec s/dt=')],
      ['A6', 0.5, v('\\omega_z=')]] },
    { t: L('Part B. Thomas precession', 'Part B. 토머스 세차'), pts: 3.5, items: [
      ['B1', 0.5, pair('v_{Cx}=', 'v_{Cy}=')],
      ['B2', 0.7, pair("v''_{x''}=", "v''_{y''}=")],
      ['B3', 0.6, sp(30)],
      ['B4', 1.0, v('\\omega=')],
      ['B5', 0.7, v('\\omega_{T,z}=')]] },
    { t: L('Part C. Magnetic moment precession', 'Part C. 자기 모멘트의 세차'), pts: 2, items: [
      ['C1', 0.7, v('\\omega_s=')],
      ['C2', 0.5, v('\\omega_a=')],
      ['C3', 0.8, fv('a_\\mu=')]] }] },
  { q: 3, kind: 'T', title: L('Frequency measurements with ring resonators', '링 공진기를 이용한 주파수 측정'), parts: [
    { t: L('Part A. Field profile in fiber optics', 'Part A. 광섬유에서의 장 분포'), pts: 2.5, items: [
      ['A1', 0.3, pair('C_1=', 'C_2=')],
      ['A2', 0.5, pair('k_{\\rm in}=', 'k_{\\rm out}=')],
      ['A3', 0.3, sp(30)],
      ['A4', 0.3, v('B=')],
      ['A5', 0.3, sp(30)],
      ['A6', 0.3, sp(30)],
      ['A7', 0.3, EQ],
      ['A8', 0.2, EQ]] },
    { t: L('Part B. Fiber resonator transmittance', 'Part B. 광섬유 공진기 투과율'), pts: 3.0, items: [
      ['B1', 0.2, EQ],
      ['B2', 0.3, v('B_{\\rm in}(t)=')],
      ['B3', 0.3, v('B_{\\rm in}(t)=')],
      ['B4', 0.5, v('B_{\\rm in}(t)=')],
      ['B5', 0.5, v('N_2=')],
      ['B6', 0.6, plot(160)],
      ['B7', 0.6, v('Q=')]] },
    { t: L('Part C. Calibration of the Mach-Zehnder Interferometer', 'Part C. 마흐‑젠더 간섭계의 보정'), pts: 2.0, items: [
      ['C1', 0.5, plot(150)],
      ['C2', 1.0, plot(150)],
      ['C3', 0.5, v('\\Delta\\omega_{\\rm MZI}/\\omega_{\\rm MZI}=')]] },
    { t: L('Part D. Cubic nonlinearity and solitons', 'Part D. 3차 비선형성과 솔리톤'), pts: 2.5, items: [
      ['D1', 0.1, v('v_g=')],
      ['D2', 0.6, sp(40)],
      ['D3', 0.5, pair('D_1=', 'D_2=')],
      ['D4', 0.3, txt('Condition on $D_2$:', '$D_2$에 대한 조건:')],
      ['D5', 0.6, plot(150)],
      ['D6', 0.2, v('\\Delta\\omega=')],
      ['D7', 0.2, v('\\tau_s=')]] }] },
];

/* ─────────────────────────── rendering ─────────────────────────── */
const tr = (x, lang) => typeof x === 'object' && x ? x[lang] : x;
const fmt = p => (Math.round(p * 10) / 10).toFixed(1);
/* the points of a question in «pt» in Korean too, as the official IPhO 2025 Korean answer sheets have them */
const PTW = { en: p => ` (${fmt(p)}pt)`, ko: p => ` (${fmt(p)}pt)` };
const PART = { en: p => ` (${p} points)`, ko: p => ` (${p}점)` };
const FORM = { en: ['(Formula)', '(Value)'], ko: ['(식)', '(값)'] };

/* graph paper as the IPhO 2025 theory answer sheets have it: a light millimetre-style grid (5 mm cells, every fifth line
   darker) with the two axes drawn in, arrows on their ends; the candidate writes the quantities and the scale */
function graph(h, cap) {
  const C = 18.8976, M = C * 5;                                   /* 5 mm and 25 mm in CSS px */
  const oy = (Math.floor(h * 4 / 3 / C) - 1) * C;                 /* the x axis on the grid line one cell above the bottom */
  return `<div class="gp" style="height:${h}pt">${cap ? `<i>${cap}</i>` : ''}<svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
    <defs><pattern id="gpm" width="${C}" height="${C}" patternUnits="userSpaceOnUse"><path d="M ${C} 0 L 0 0 0 ${C}" fill="none" stroke="#c9c9c9" stroke-width="0.5"/></pattern>
      <pattern id="gpM" width="${M}" height="${M}" patternUnits="userSpaceOnUse"><rect width="${M}" height="${M}" fill="url(#gpm)"/><path d="M ${M} 0 L 0 0 0 ${M}" fill="none" stroke="#9a9a9a" stroke-width="0.8"/></pattern>
      <marker id="gpa" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#000"/></marker></defs>
    <rect width="100%" height="100%" fill="url(#gpM)"/>
    <line x1="${2 * C}" y1="${oy}" x2="98%" y2="${oy}" stroke="#000" stroke-width="1.1" marker-end="url(#gpa)"/>
    <line x1="${2 * C}" y1="${oy + C * 0.6}" x2="${2 * C}" y2="${C * 0.4}" stroke="#000" stroke-width="1.1" marker-end="url(#gpa)"/></svg></div>`;
}
/* the heights the items ask for are those of the first sheets, which came out flat; the graph paper of the official
   sheets (IPhO 2025 T2 B.2, ISPhO 2026 E1) is about half as tall as it is wide, or square: half as tall again */
const GH = h => Math.round(h * 1.5);
function rows(prompts, lang) {
  return prompts.map(p => {
    if (p.v) return `<div class="r">$${p.v}$</div>`;
    if (p.pair) return `<div class="r two"><span>$${p.pair[0]}$</span><span>$${p.pair[1]}$</span></div>`;
    if (p.fv) return `<div class="r two"><span>${FORM[lang][0]} $${p.fv}$</span><span>${FORM[lang][1]} $${p.fv}$</span></div>`;
    if (p.txt) return `<div class="r">${tr(p.txt, lang)}</div>`;
    if (p.space) return `<div style="height:${p.space}pt"></div>`;
    if (p.plot) return `<div class="pl">${lang === 'ko' ? '그래프:' : 'Plot:'}</div>${graph(GH(p.plot))}`;
    if (p.plots) return `<div class="pl">${lang === 'ko' ? '그래프:' : 'Plot:'}</div><div class="pls">${p.plots.map(c => graph(GH(p.h), tr(c, lang))).join('')}</div>`;
    if (p.table) {
      const { cols, rows: n } = p.table, labels = Array.isArray(n) ? n : null, count = labels ? labels.length : n;
      return `<table class="at" style="width:${Math.min(100, cols.length * 22)}%"><tr>${cols.map(c => `<th>${tr(c, lang)}</th>`).join('')}</tr>${Array.from({ length: count }, (_, i) =>
        `<tr>${cols.map((c, j) => `<td>${j === 0 && labels ? tr(labels[i], lang) : ''}</td>`).join('')}</tr>`).join('')}</table>`;
    }
    if (p.diode) {
      const d = flip => `<svg width="150" height="34" viewBox="0 0 150 34"><text x="2" y="21" font-size="12">+</text><circle cx="16" cy="17" r="3" fill="none" stroke="#000"/><line x1="19" y1="17" x2="58" y2="17" stroke="#000"/>
        <g transform="${flip ? 'translate(150,0) scale(-1,1)' : ''}"><polygon points="58,6 58,28 80,17" fill="none" stroke="#000"/><line x1="80" y1="6" x2="80" y2="28" stroke="#000"/></g>
        <line x1="80" y1="17" x2="128" y2="17" stroke="#000"/><line x1="58" y1="17" x2="92" y2="17" stroke="#000" stroke-opacity="0"/><circle cx="131" cy="17" r="3" fill="none" stroke="#000"/><text x="138" y="21" font-size="12">−</text></svg>`;
      const lab = lang === 'ko' ? ['(1)', '(2)', '올바른 극성: (1) / (2)'] : ['(1)', '(2)', 'Correct polarity: (1) / (2)'];
      return `<div class="r two"><span>${lab[0]} ${d(false)}</span><span>${lab[1]} ${d(true)}</span></div><div class="r">${lab[2]}</div>`;
    }
    throw new Error('unknown prompt ' + JSON.stringify(p));
  }).join('');
}

function answerSheet(P, lang, style) {
  const out = [];
  out.push(`<h1>${tr(P.title, lang)}</h1>`);
  for (const part of P.parts) {
    out.push(`<h2>${tr(part.t, lang)}${part.pts != null ? PART[lang](fmt(part.pts)) : ''}</h2>`);
    for (const [label, pts, ...prompts] of part.items) {
        out.push(`<div class="bx"><div class="lb"><b>${label}</b>${pts != null ? PTW[lang](pts) : ''}</div>${rows(prompts, lang)}</div>`);
    }
  }
  return out.join('\n');
}

const workingSheet = n => Array.from({ length: n }, (_, i) => `<div class="ws"${i < n - 1 ? ' style="break-after:page"' : ''}></div>`).join('');

const CSS = `
h1{font:700 15.94pt/1.2 'HL Sans','HL Sans KR',sans-serif;color:#0000b3;margin:-1.2pt 0 7pt}
h2{font:700 10.96pt/1.3 'HL Sans','HL Sans KR',sans-serif;color:#0000b3;margin:12pt 0 0;break-after:avoid}
h1+h2{margin-top:0}
.bx{border:0.4pt solid #000;margin-top:6.4pt;padding:5.4pt 9.4pt 9.2pt;break-inside:avoid;line-height:12pt}
.lb{line-height:13.6pt}.lb b{font-weight:700}
.r{min-height:23.9pt;display:flex;align-items:flex-end}.r.two>span{flex:1}.r svg{vertical-align:middle}
.pl{line-height:12pt}
.pls{display:flex;gap:9pt;margin-top:4pt}.pls>.gp{flex:1}
.gp{position:relative;border:0.4pt solid #888;margin-top:3pt;break-inside:avoid}.gp svg{display:block}.gp i{position:absolute;left:10%;top:2pt;font-style:normal;font-size:8.5pt;background:#fff;padding:0 2pt}
table.at{border-collapse:collapse;margin:7pt auto 0;font-size:10pt;table-layout:fixed}table.at th,table.at td{border:0.4pt solid #000;height:19pt;padding:0 5pt;text-align:center;font-weight:400}table.at th{background:#f2f2f2}
.ws{border:0.4pt solid #000;height:615.4pt;margin-top:6.4pt}
.katex{font-size:1em}`;

const LANG = { en: 'English', ko: 'Korean (Korea (Republic of))' };
const docs = [];
const name = (y, P, kind, lang) => {
  const k = P.kind === 'E' ? `E${P.q}` : `T${P.q}`;
  const tail = kind === 'answer' ? (P.kind === 'E' ? '_AS' : 'A') : (P.kind === 'E' ? '_WS' : 'W');
  const dir = P.kind === 'E' ? 'sim/sheets' : 'pdfx/ispho';
  if (P.kind === 'E') return `${dir}/ISPhO_${y}_${k}${tail}${lang === 'ko' ? '_KO' : ''}.pdf`;
  return `${dir}/ISPhO_${y}_${k}${lang === 'ko' ? (kind === 'answer' ? '_A_KO' : '_W_KO') : tail}.pdf`;
};
for (const [y, problems, style] of [[2025, Y2025, 'ispho'], [2024, Y2024, 'ispho'], [2023, Y2023, 'ispho']]) {
  for (const P of problems) for (const lang of ['en', 'ko']) {
    const section = P.kind === 'E' ? 'Experiment' : 'Theory';
    docs.push({ out: name(y, P, 'answer', lang), style, kind: 'answer', lang, code: `A${P.q}`, section, langLabel: LANG[lang],
      css: CSS, html: answerSheet(P, lang, style) });
  }
}
/* working sheets: 2023–2026, theory (each problem) and experiment */
const WS = { 2023: [['T', 1], ['T', 2], ['T', 3]], 2026: [['T', 1], ['T', 2], ['T', 3], ['E', 1]], 2025: [['T', 1], ['T', 2], ['T', 3], ['E', 1]], 2024: [['T', 1], ['T', 2], ['T', 3], ['E', 1]] };
for (const [y, list] of Object.entries(WS)) for (const [kind, q] of list) for (const lang of ['en', 'ko'])
  docs.push({ out: name(y, { kind, q }, 'working', lang), style: 'ispho', kind: 'working', lang, code: `W${q}`,
    section: kind === 'E' ? 'Experiment' : 'Theory', langLabel: LANG[lang], css: CSS, html: workingSheet(kind === 'E' ? 4 : 3) });

module.exports = { docs, Y2025, Y2024, Y2023 };
