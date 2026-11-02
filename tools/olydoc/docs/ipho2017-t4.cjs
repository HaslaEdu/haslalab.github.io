/* IPhO 2017 (Yogyakarta) shortlist problem «Measuring the radius of a star» (pho.rs/p/3485, source Y23), typeset as
 * the 2017 theory paper (T4), answer sheet (AT4) and solutions/marking scheme.  The statement, solution and marking
 * scheme follow pho.rs's published version, translated to English and Korean; the figures are pho.rs's, with their
 * Russian words relabelled. */
const { q, fig } = require('../lib.cjs');

const SRC = 'pho.rs/p/3485';
const L = (en, ko) => ({ en, ko });

const FIG = {
  1: lang => fig('ipho2017-t4-fig1.jpg', lang === 'ko' ? '그림 1. 별에서 오는 빛의 경로.' : 'Fig. 1. Paths of the light rays coming from the star.', 78,
    [{ x: 38.6, y: 84.8, w: 8.5, h: 4.4, text: lang === 'ko' ? '스크린' : 'Screen' }]),
  2: lang => fig('ipho2017-t4-fig2.jpg', lang === 'ko' ? '그림 2. $yz$ 평면에서 각 $\\theta$로 진행하여 스크린의 점 $O$에 닿는 광선.' : 'Fig. 2. Rays travelling at an angle $\\theta$ in the $yz$ plane and reaching the screen at point $O$.', 74,
    [{ x: 35.2, y: 85.8, w: 8.6, h: 4.6, text: lang === 'ko' ? '스크린' : 'Screen' }]),
  3: lang => fig('ipho2017-t4-fig3.jpg', lang === 'ko' ? '그림 3.' : 'Fig. 3.', 62),
  4: lang => fig('ipho2017-t4-fig4.jpg', lang === 'ko' ? '그림 4. 왼쪽: 별과 관측자를 옆에서 본 모습; 오른쪽: 관측자가 본 별의 원반.' : 'Fig. 4. Left: side view of the star and the observer; right: the stellar disc seen by the observer.', 56,
    [{ x: 7.5, y: 0, w: 14.5, h: 4.2, text: lang === 'ko' ? '별' : 'Star' }, { x: 2, y: 95.6, w: 26, h: 4.4, text: lang === 'ko' ? '관측자' : 'Observer' }]),
};

/* the parts: intro (before the boxes) and items [label, points, question, answer-sheet prompts, solution, scheme] */
const PARTS = [
  { title: L('Part A. Rays parallel to the $z$ axis (1.6 points)', '파트 A. $z$축에 나란한 광선 (1.6점)'),
    intro: L('', ''),
    items: [
      ['A1', 0.2,
        L('Consider the case where rays 1 and 2 are parallel to the $z$ axis and mirror M3 is parallel to the $xy$ plane. Find the optical path difference $\\Delta_{12}$ between rays 1 and 2 if both reach the screen at point $O$.',
          '광선 1과 2가 $z$축에 나란하고 거울 M3이 $xy$ 평면에 나란한 경우를 생각하자. 두 광선이 모두 스크린의 점 $O$에 닿을 때 광선 1과 2의 광경로차 $\\Delta_{12}$를 구하여라.'),
        ['$\\Delta_{12}=$'],
        L('Along the horizontal stretches the paths differ by $L_1-L_2$; in addition ray 1 travels the distance $L_3$ twice. Hence $$\\Delta_{12}=L_1+2L_3-L_2.$$',
          '수평 구간에서 두 경로의 차는 $L_1-L_2$이고, 광선 1은 거리 $L_3$을 두 번 더 지난다. 따라서 $$\\Delta_{12}=L_1+2L_3-L_2.$$'),
        [[L('Answer $\\Delta_{12}=L_1+2L_3-L_2$. (If an extra term $\\lambda/2$ is written here, or a phase difference is computed instead of the path difference, A2 is marked consistently with this error.)',
            '답 $\\Delta_{12}=L_1+2L_3-L_2$. (여기서 $\\lambda/2$ 항을 더 썼거나 광경로차 대신 위상차를 구했으면, A2는 이 오류를 반영해 채점한다.)'), 0.2]]],
      ['A2', 1.4,
        L('Now mirror M3 is tilted by an angle $\\alpha$ from the $xy$ plane by a rotation about the $x$ axis (see Fig. 1). If ray 1′ reaches the screen at point $O$, find the optical path difference $\\Delta_{1\'2}$ between rays 1′ and 2. Show that to first order the path difference does not depend on $\\alpha$, and simplify your answer for $\\alpha\\ll1$.',
          '이제 거울 M3을 $x$축 둘레로 돌려 $xy$ 평면에서 각 $\\alpha$만큼 기울인다(그림 1). 광선 1′이 스크린의 점 $O$에 닿을 때 광선 1′과 2의 광경로차 $\\Delta_{1\'2}$를 구하여라. 1차 근사에서 경로차가 $\\alpha$에 무관함을 보이고, $\\alpha\\ll1$일 때 답을 간단히 하여라.'),
        ['$\\Delta_{1\'2}=$'],
        L('The paths of rays 1 and 1′ from M3 to $O$ form an isosceles triangle, and the changes of the horizontal and vertical stretches caused by the shifted point of incidence cancel. The only parameter that changes the path of the ray is the $z$ coordinate of its point on M3, which shortens the stretch from HM to M3; ray 2 is unchanged. Hence $$\\Delta_{1\'2}=\\Delta_{12}-2(L_3+L_4)\\sin^2\\alpha=L_1+2L_3-L_2-2(L_3+L_4)\\sin^2\\alpha\\approx L_1+2L_3-L_2-2(L_3+L_4)\\alpha^2.$$',
          '광선 1과 1′이 M3에서 $O$까지 가는 경로는 이등변 삼각형을 이루며, 입사점이 옮겨져 생기는 수평·수직 구간의 변화는 서로 상쇄된다. 경로를 바꾸는 것은 M3 위 입사점의 $z$ 좌표뿐이고, 이것이 HM에서 M3까지의 구간을 줄인다. 광선 2는 변하지 않는다. 따라서 $$\\Delta_{1\'2}=\\Delta_{12}-2(L_3+L_4)\\sin^2\\alpha=L_1+2L_3-L_2-2(L_3+L_4)\\sin^2\\alpha\\approx L_1+2L_3-L_2-2(L_3+L_4)\\alpha^2.$$'),
        [[L('Shown that the optical paths of rays 1 and 1′ from mirror M3 to the screen are equal.', '광선 1과 1′의 M3에서 스크린까지의 광경로가 같음을 보임.'), 0.5],
         [L('Shown that the optical path difference of rays 1 and 1′ from the beam splitter to M3 is $\\Delta_{11\'}=2(L_3+L_4)\\sin^2\\alpha$ (the small-angle limit was not stated, so only the exact result earns this).', '광선 1과 1′의 빔 분할기에서 M3까지의 광경로차 $\\Delta_{11\'}=2(L_3+L_4)\\sin^2\\alpha$를 보임(작은 각이 주어지지 않았으므로 정확한 결과만 인정).'), 0.5],
         [L('Answer $\\Delta_{1\'2}=L_1+2L_3-L_2-2(L_3+L_4)\\sin^2\\alpha\\approx L_1+2L_3-L_2-2(L_3+L_4)\\alpha^2$ (exact result required).', '답 $\\Delta_{1\'2}=L_1+2L_3-L_2-2(L_3+L_4)\\sin^2\\alpha\\approx L_1+2L_3-L_2-2(L_3+L_4)\\alpha^2$(정확한 결과 필요).'), 0.4]]],
    ] },
  { title: L('Part B. Rays at an angle $\\theta$ in the $yz$ plane (4.7 points)', '파트 B. $yz$ 평면에서 각 $\\theta$로 들어오는 광선 (4.7점)'),
    intro: L('<p>Now the rays enter the interferometer at an angle $\\theta\\ll1$ to the $z$ axis in the $yz$ plane, as shown below. As in A2, mirror M3 is tilted by $\\alpha$.</p><p><i>Note:</i> from here on, work to first order when computing optical paths, i.e. neglect terms containing $\\alpha^2$, $\\theta^2$, $\\alpha\\theta$ and so on.</p>' + FIG[2]('en'),
      '<p>이제 광선이 아래 그림처럼 $yz$ 평면에서 $z$축과 각 $\\theta\\ll1$를 이루며 간섭계에 들어온다. A2에서처럼 거울 M3은 $\\alpha$만큼 기울어져 있다.</p><p><i>참고:</i> 이제부터 광경로는 1차 근사로 계산하여라. 즉 $\\alpha^2$, $\\theta^2$, $\\alpha\\theta$ 등을 포함한 항은 무시한다.</p>' + FIG[2]('ko')),
    items: [
      ['B1', 0.8,
        L('Let rays 1 and 2 hit fixed points of mirrors M1 and M2 respectively. Show on the working sheets that, to first order, the optical paths of rays 1 and 2 from their points of reflection on M1 and M2 to the screen do not depend on the angles $\\theta$ and $\\alpha$.',
          '광선 1과 2가 각각 거울 M1과 M2의 정해진 점에 닿는다고 하자. 1차 근사에서 M1, M2의 반사점에서 스크린까지 광선 1과 2의 광경로가 각 $\\theta$와 $\\alpha$에 무관함을 풀이 용지에 보여라.'),
        ['(shown on the working sheets)'],
        L('The rays deviate from the horizontal and vertical directions only by small angles, so to first order these deviations do not change the path lengths. Because the beam splitter is at $\\pi/4$, a change of the horizontal stretch from M1 (M2) to the beam splitter is exactly compensated by the opposite change of the stretch from the beam splitter to the screen, for both rays.',
          '광선은 수평·수직 방향에서 작은 각만큼만 벗어나므로 1차 근사에서 이 벗어남은 경로 길이를 바꾸지 않는다. 빔 분할기가 $\\pi/4$로 놓여 있어서, 두 광선 모두 M1(M2)에서 빔 분할기까지의 수평 구간 변화가 빔 분할기에서 스크린까지의 구간의 반대 변화로 정확히 보상된다.'),
        [[L('Stated that, because the angles to the vertical and horizontal are small, they need not be taken into account in the first-order optical path.', '수직·수평과 이루는 각이 작아서 1차 광경로에서 고려할 필요가 없음을 언급.'), 0.2],
         [L('Used the $\\pi/4$ inclination of the beam splitter to show that the changes of the horizontal stretch from M1 (M2) to the beam splitter and of the stretch from the beam splitter to the screen cancel — for ray 1 and for ray 2 (0.3 each).', '빔 분할기가 $\\pi/4$로 기울어진 것을 이용해 M1(M2)에서 빔 분할기까지의 수평 구간 변화와 빔 분할기에서 스크린까지의 구간 변화가 상쇄됨을 보임 — 광선 1, 2 각각 0.3점.'), 0.6]]],
      ['B2', 0.8,
        L('Let the angles $\\alpha$ and $\\theta$ be fixed while the points of incidence of rays 1 and 2 on M1 and M2 may change. Show on the working sheets that the optical paths of rays 1 and 2 from the dashed line at $z_\\text{d}=L_3+L_4$ (its intersections with the paths of rays 1 and 2 before they hit M1 and M2) to the screen do not depend, to first order, on $\\theta$ and $\\alpha$.',
          '각 $\\alpha$와 $\\theta$는 고정하고 광선 1과 2가 M1, M2에 닿는 점은 바뀔 수 있다고 하자. $z_\\text{d}=L_3+L_4$인 점선(광선 1, 2가 M1, M2에 닿기 전 경로와 만나는 점)에서 스크린까지 광선 1과 2의 광경로가 1차 근사에서 $\\theta$와 $\\alpha$에 무관함을 풀이 용지에 보여라.'),
        ['(shown on the working sheets)'],
        L('Ray 1: its path from M3 to the screen is constant; when the point of incidence on M1 moves, the path from M1 to the beam splitter grows exactly as much as the sum of the paths from the dashed line to M1 and from the beam splitter to M3 shrinks. Ray 2: its path from M2 to the beam splitter is constant, and the sum of the paths from the dashed line to M2 and from the beam splitter to the screen is constant.',
          '광선 1: M3에서 스크린까지의 경로는 일정하다. M1 위 입사점이 움직이면 M1에서 빔 분할기까지의 경로가 늘어나는 만큼 점선에서 M1까지와 빔 분할기에서 M3까지의 경로 합이 줄어든다. 광선 2: M2에서 빔 분할기까지의 경로는 일정하고, 점선에서 M2까지와 빔 분할기에서 스크린까지의 경로 합도 일정하다.'),
        [[L('Ray 1: the optical path between M3 and the screen is constant.', '광선 1: M3과 스크린 사이 광경로가 일정함을 이용.'), 0.1],
         [L('Ray 1: as the point of incidence moves, the path from M1 to the beam splitter grows exactly as the sum of the paths from the dashed line to M1 and from the beam splitter to M3 shrinks.', '광선 1: 입사점이 움직일 때 M1에서 빔 분할기까지 경로가 늘어나는 만큼 점선에서 M1까지와 빔 분할기에서 M3까지 경로의 합이 줄어듦을 보임.'), 0.4],
         [L('Ray 2: the optical path from M2 to the beam splitter is constant.', '광선 2: M2에서 빔 분할기까지 광경로가 일정함을 이용.'), 0.1],
         [L('Ray 2: the sum of the paths from the dashed line to M2 and from the beam splitter to the screen is constant.', '광선 2: 점선에서 M2까지와 빔 분할기에서 스크린까지 경로의 합이 일정함을 보임.'), 0.2]]],
      ['B3', 1.0,
        L('If rays 1 and 2 reach the screen at point $O$, their phase difference can be written as $$\\delta_{12}=\\frac{2\\pi}{\\lambda}b\\theta+\\delta_O.$$ Express $b$ and $\\delta_O$ in terms of $\\lambda$, $L_1$, $L_2$, $L_3$, $L_4$.',
          '광선 1과 2가 스크린의 점 $O$에 닿으면 위상차를 $$\\delta_{12}=\\frac{2\\pi}{\\lambda}b\\theta+\\delta_O$$로 쓸 수 있다. $b$와 $\\delta_O$를 $\\lambda$, $L_1$, $L_2$, $L_3$, $L_4$로 나타내어라.'),
        ['$b=$', '$\\delta_O=$'],
        L('$\\delta_O$ is the phase difference at $\\theta=0$ (Part A). Besides the path difference, ray 1 has one more reflection and so an extra $\\pi$: $$\\delta_O=\\frac{2\\pi}{\\lambda}(L_1+2L_3-L_2)+\\pi.$$ By B1 and B2, a change of $\\theta$ changes the phase only through the paths up to the dashed line $z_\\text{d}=L_3+L_4$, which differ by $(L_1+L_2)\\theta$: $\\frac{2\\pi}{\\lambda}(L_1+L_2)\\theta=\\frac{2\\pi}{\\lambda}b\\theta$, so $$b=L_1+L_2.$$',
          '$\\delta_O$는 $\\theta=0$일 때의 위상차(파트 A)이다. 경로차 외에 광선 1은 반사를 한 번 더 하므로 $\\pi$가 더해진다: $$\\delta_O=\\frac{2\\pi}{\\lambda}(L_1+2L_3-L_2)+\\pi.$$ B1, B2에 따라 $\\theta$가 바뀌면 위상은 점선 $z_\\text{d}=L_3+L_4$까지의 경로를 통해서만 바뀌고, 그 차는 $(L_1+L_2)\\theta$이다: $\\frac{2\\pi}{\\lambda}(L_1+L_2)\\theta=\\frac{2\\pi}{\\lambda}b\\theta$, 따라서 $$b=L_1+L_2.$$'),
        [[L('Answer for $\\delta_O=\\frac{2\\pi}{\\lambda}(L_1+2L_3-L_2)+\\pi$.', '답 $\\delta_O=\\frac{2\\pi}{\\lambda}(L_1+2L_3-L_2)+\\pi$.'), 0.2],
         [L('Stated that the additional phase difference comes from the different optical paths of the rays up to the dashed line.', '추가 위상차가 점선까지의 광경로 차이에서 생김을 언급.'), 0.4],
         [L('Answer $b=L_1+L_2$.', '답 $b=L_1+L_2$.'), 0.4]]],
      ['B4', 0.6,
        L('If ray 1′ reflected by M1 and ray 2′ reflected by M2 reach the same point of the screen at coordinate $y$, their phase difference can be written as $$\\delta_{1\'2\'}=\\frac{2\\pi}{\\lambda}b\\theta+\\delta_y.$$ Show on the working sheets that $$\\delta_y=\\delta_O-\\frac{2\\pi}{\\lambda}\\cdot2\\alpha y.$$ <i>Note:</i> in all the following tasks you may use the statements of B1–B4 even if you have not proved them.',
          'M1에서 반사된 광선 1′과 M2에서 반사된 광선 2′이 스크린의 좌표 $y$인 같은 점에 닿으면 위상차를 $$\\delta_{1\'2\'}=\\frac{2\\pi}{\\lambda}b\\theta+\\delta_y$$로 쓸 수 있다. $$\\delta_y=\\delta_O-\\frac{2\\pi}{\\lambda}\\cdot2\\alpha y$$임을 풀이 용지에 보여라. <i>참고:</i> 이후 모든 문항에서 B1–B4의 내용은 증명하지 않았더라도 사용할 수 있다.'),
        ['(shown on the working sheets)'],
        L('Two rays 1 that reach points of the screen a distance $y$ apart were reflected from M3 at points also (for small $\\alpha$) $y$ apart. Their paths differ only through the $z$ coordinate of the point of reflection on M3, which shortens both the stretch from HM to M3 and that from M3 to the screen: $\\Delta L=-2\\alpha y$, so $\\delta_y=\\delta_O-\\frac{2\\pi}{\\lambda}\\cdot2\\alpha y$.',
          '스크린에서 거리 $y$만큼 떨어진 점에 닿는 두 광선 1은 ($\\alpha$가 작으므로) M3에서도 $y$만큼 떨어진 점에서 반사된다. 두 경로는 M3 반사점의 $z$ 좌표를 통해서만 달라지며, 이것이 HM에서 M3까지와 M3에서 스크린까지의 구간을 함께 줄인다: $\\Delta L=-2\\alpha y$, 따라서 $\\delta_y=\\delta_O-\\frac{2\\pi}{\\lambda}\\cdot2\\alpha y$.'),
        [[L('Stated that if the rays reach the screen at coordinate $y$, the point of incidence of ray 1 on M3 also shifts by $y$.', '광선이 스크린의 좌표 $y$에 닿으면 M3 위 광선 1의 입사점도 $y$만큼 옮겨짐을 언급.'), 0.3],
         [L('Shown that the optical path of ray 1 from the beam splitter to the screen decreases by $2\\alpha y$.', '빔 분할기에서 스크린까지 광선 1의 광경로가 $2\\alpha y$만큼 줄어듦을 보임.'), 0.3]]],
      ['B5', 0.6,
        L('An interference pattern thus appears on the screen. Find the distance $y_1$ from $O$ to the nearest interference maximum, and the distance $\\Delta y_m$ between two neighbouring maxima. Give numerical answers for $L_1=0.50$ m, $L_2=1.50$ m, $L_3=0.50$ m, $L_4=1.00$ m, $\\alpha=10^{-4}$, $\\theta=10^{-5}$, $\\lambda=500$ nm.',
          '이렇게 스크린에 간섭무늬가 생긴다. 점 $O$에서 가장 가까운 간섭 극대까지의 거리 $y_1$과 이웃한 두 극대 사이의 거리 $\\Delta y_m$을 구하여라. $L_1=0.50$ m, $L_2=1.50$ m, $L_3=0.50$ m, $L_4=1.00$ m, $\\alpha=10^{-4}$, $\\theta=10^{-5}$, $\\lambda=500$ nm일 때 수치로 답하여라.'),
        ['$y_1=$', '$\\Delta y_m=$'],
        L('With the numbers, $\\delta=81\\pi-800\\pi\\,y/(1\\ \\text{m})$. Maxima are at $\\delta=2\\pi n$; point $O$ is a minimum. Hence $$y_1=\\frac{\\lambda}{4\\alpha}=1.25\\ \\text{mm},\\qquad \\Delta y_m=\\frac{\\lambda}{2\\alpha}=2.5\\ \\text{mm}.$$',
          '수치를 넣으면 $\\delta=81\\pi-800\\pi\\,y/(1\\ \\text{m})$이다. 극대는 $\\delta=2\\pi n$에서 생기고 점 $O$는 극소이다. 따라서 $$y_1=\\frac{\\lambda}{4\\alpha}=1.25\\ \\text{mm},\\qquad \\Delta y_m=\\frac{\\lambda}{2\\alpha}=2.5\\ \\text{mm}.$$'),
        [[L('Answer $\\Delta y_m=2.5$ mm (expression and value, 0.1 each).', '답 $\\Delta y_m=2.5$ mm (식과 값 각 0.1점).'), 0.2],
         [L('Answer $y_1=1.25$ mm (marked even with the wrong sign).', '답 $y_1=1.25$ mm (부호가 틀려도 인정).'), 0.4]]],
      ['B6', 0.9,
        L('Find how the intensity $I(y)$ on the screen depends on $y$ if its maximum value is $I_0$, substituting the numerical values of the previous task. Take into account the effect of the beam splitter on the intensity of the transmitted light.',
          '스크린의 세기 $I(y)$의 최댓값이 $I_0$일 때 $I(y)$가 $y$에 어떻게 의존하는지 앞 문항의 수치를 넣어 구하여라. 빔 분할기가 투과하는 빛의 세기에 미치는 영향을 고려하여라.'),
        ['$I(y)=$'],
        L('Ray 1 meets the beam splitter twice (reflected, then transmitted), ray 2 once, so the field amplitude of ray 1 is $\\sqrt2$ times smaller and $I_1=I_2/2$. Then $I\\propto1+2+2\\sqrt2\\cos\\delta$ and $$I(y)=I_0\\,\\frac{3-2\\sqrt2\\cos\\left[80\\pi\\left(1-10\\,y/(1\\ \\text{m})\\right)\\right]}{3+2\\sqrt2}.$$',
          '광선 1은 빔 분할기를 두 번(반사 후 투과), 광선 2는 한 번 지나므로 광선 1의 전기장 진폭이 $\\sqrt2$배 작고 $I_1=I_2/2$이다. 따라서 $I\\propto1+2+2\\sqrt2\\cos\\delta$이고 $$I(y)=I_0\\,\\frac{3-2\\sqrt2\\cos\\left[80\\pi\\left(1-10\\,y/(1\\ \\text{m})\\right)\\right]}{3+2\\sqrt2}.$$'),
        [[L('Formula $I=I_1+I_2+2\\sqrt{I_1I_2}\\cos\\delta$.', '식 $I=I_1+I_2+2\\sqrt{I_1I_2}\\cos\\delta$.'), 0.2],
         [L('Taken into account that $I_1=I_2/2$.', '$I_1=I_2/2$를 고려함.'), 0.1],
         [L('Formula $I(y)=I_0\\,(3-2\\sqrt2\\cos\\delta(y))/(3+2\\sqrt2)$.', '식 $I(y)=I_0\\,(3-2\\sqrt2\\cos\\delta(y))/(3+2\\sqrt2)$.'), 0.3],
         [L('$\\delta(y)=\\pm80\\pi\\left(1-10\\,y/(1\\ \\text{m})\\right)$.', '$\\delta(y)=\\pm80\\pi\\left(1-10\\,y/(1\\ \\text{m})\\right)$.'), 0.3]]],
    ] },
  { title: L('Part C. Quite arbitrary rays (1.0 point)', '파트 C. 아주 임의의 광선 (1.0점)'),
    intro: L('<p>Now rays 1″ and 2″ enter the interferometer at an angle $\\theta_x\\ll1$ to the $yz$ plane and an angle $\\theta_y\\ll1$ to the $xz$ plane (see Fig. 3).</p>' + FIG[3]('en'),
      '<p>이제 광선 1″과 2″이 $yz$ 평면과 각 $\\theta_x\\ll1$, $xz$ 평면과 각 $\\theta_y\\ll1$를 이루며 간섭계에 들어온다(그림 3).</p>' + FIG[3]('ko')),
    items: [
      ['C1', 0.4,
        L('Express the wave vector $\\vec k$ of the incident rays in terms of $\\theta_x$, $\\theta_y$, the magnitude $k=2\\pi/\\lambda$ and the unit vectors of the axes.',
          '입사 광선의 파동 벡터 $\\vec k$를 $\\theta_x$, $\\theta_y$, 크기 $k=2\\pi/\\lambda$, 좌표축의 단위 벡터로 나타내어라.'),
        ['$\\vec k=$'],
        L('For small $\\theta_x$, $\\theta_y$: $k_z=-k$, $k_x=-k\\theta_x$, $k_y=-k\\theta_y$, i.e. $$\\vec k=-k\\left(\\theta_x\\hat x+\\theta_y\\hat y+\\hat z\\right).$$',
          '$\\theta_x$, $\\theta_y$가 작으므로 $k_z=-k$, $k_x=-k\\theta_x$, $k_y=-k\\theta_y$, 즉 $$\\vec k=-k\\left(\\theta_x\\hat x+\\theta_y\\hat y+\\hat z\\right).$$'),
        [[L('Taken into account that every projection is negative, $|k_i|=-k_i$.', '모든 성분이 음수임($|k_i|=-k_i$)을 고려함.'), 0.1],
         [L('Magnitudes of the projections $|k_x|=k\\theta_x$, $|k_y|=k\\theta_y$, $|k_z|=k$ (0.1 each).', '성분의 크기 $|k_x|=k\\theta_x$, $|k_y|=k\\theta_y$, $|k_z|=k$ (각 0.1점).'), 0.3]]],
      ['C2', 0.6,
        L('Let ray 1″ reflected by M1 and ray 2″ reflected by M2 reach the same point of the screen on the $y$ axis, a distance $y$ from $O$. Express the phase difference between rays 1″ and 2″ in terms of $\\lambda$, $L_1$, $L_2$, $L_3$, $L_4$, $\\theta_x$, $\\theta_y$, $\\alpha$, $y$.',
          'M1에서 반사된 광선 1″과 M2에서 반사된 광선 2″이 스크린의 $y$축 위, $O$에서 거리 $y$인 같은 점에 닿는다. 광선 1″과 2″의 위상차를 $\\lambda$, $L_1$, $L_2$, $L_3$, $L_4$, $\\theta_x$, $\\theta_y$, $\\alpha$, $y$로 나타내어라.'),
        ['$\\delta_{1\'\'2\'\'}=$'],
        L('The initial offset along $x$ of rays that meet at one point of the screen is of order $L_3\\theta_x$, so the path difference it causes is of order $\\theta_x^2$ and $\\theta_x$ drops out. As in Part B: $$\\delta_{1\'\'2\'\'}=\\frac{2\\pi}{\\lambda}\\left((L_1+L_2)\\theta_y+(L_1+2L_3-L_2)-2\\alpha y\\right)+\\pi.$$',
          '스크린의 한 점에서 만나는 광선들의 처음 $x$ 방향 어긋남은 $L_3\\theta_x$ 정도이므로 그로 인한 경로차는 $\\theta_x^2$ 정도이고 $\\theta_x$는 빠진다. 파트 B와 같이: $$\\delta_{1\'\'2\'\'}=\\frac{2\\pi}{\\lambda}\\left((L_1+L_2)\\theta_y+(L_1+2L_3-L_2)-2\\alpha y\\right)+\\pi.$$'),
        [[L('Shown that the phase difference does not depend on $\\theta_x$.', '위상차가 $\\theta_x$에 무관함을 보임.'), 0.3],
         [L('Answer $\\delta_{1\'\'2\'\'}=\\frac{2\\pi}{\\lambda}\\left(L_1+2L_3-L_2+(L_1+L_2)\\theta_y-2\\alpha y\\right)+\\pi$.', '답 $\\delta_{1\'\'2\'\'}=\\frac{2\\pi}{\\lambda}\\left(L_1+2L_3-L_2+(L_1+L_2)\\theta_y-2\\alpha y\\right)+\\pi$.'), 0.3]]],
    ] },
  { title: L('Part D. Measuring the radius (2.7 points)', '파트 D. 반지름 측정 (2.7점)'),
    intro: L('<p>Consider a star of angular radius $\\theta_R$, which we want to determine. For simplicity the star radiates as a uniform disc: the intensity of the light coming from a solid angle $\\mathrm d\\Omega=\\mathrm d\\theta_x\\mathrm d\\theta_y$ is $\\mathcal J\\mathrm d\\Omega$, with $\\mathcal J$ the same in every direction within the stellar disc. The interferometer (its $z$ axis) points exactly at the centre of the star. For $\\alpha>0$ an interference pattern is seen on the screen. Let $I_{y(\\min)}$ and $I_{y(\\max)}$ be the minimum and maximum intensities on the screen along the $y$ axis, and define the visibility $$V=\\frac{I_{y(\\max)}-I_{y(\\min)}}{I_{y(\\max)}+I_{y(\\min)}}.$$</p>' + FIG[4]('en'),
      '<p>각반지름 $\\theta_R$를 구하려는 별을 생각하자. 간단히 별은 균일한 원반처럼 빛을 낸다고 하자. 즉 입체각 $\\mathrm d\\Omega=\\mathrm d\\theta_x\\mathrm d\\theta_y$에서 오는 빛의 세기는 $\\mathcal J\\mathrm d\\Omega$이고, $\\mathcal J$는 별 원반 안의 모든 방향에서 같다. 간섭계($z$축)는 별의 중심을 정확히 향한다. $\\alpha>0$이면 스크린에 간섭무늬가 보인다. 스크린의 $y$축을 따라 최소·최대 세기를 $I_{y(\\min)}$, $I_{y(\\max)}$라 하고, 가시도를 $$V=\\frac{I_{y(\\max)}-I_{y(\\min)}}{I_{y(\\max)}+I_{y(\\min)}}$$로 정의한다.</p>' + FIG[4]('ko')),
    items: [
      ['D1', 1.8,
        L('Write $V$ as an integral over one variable. You need not carry out the integration. <i>Hint:</i> the integral of a function $f(\\theta_y)$ of $\\theta_y$ only over a disc of radius $\\theta_R$ can be written as $$I=\\int_{-\\theta_R}^{\\theta_R}\\mathrm d\\theta_y\\int_{-\\sqrt{\\theta_R^2-\\theta_y^2}}^{\\sqrt{\\theta_R^2-\\theta_y^2}}\\mathrm d\\theta_x\\,f(\\theta_y)=\\int_{-\\theta_R}^{\\theta_R}\\mathrm d\\theta_y\\cdot2\\sqrt{\\theta_R^2-\\theta_y^2}\\,f(\\theta_y).$$',
          '$V$를 한 변수에 대한 적분으로 써라. 적분을 실제로 계산할 필요는 없다. <i>힌트:</i> $\\theta_y$에만 의존하는 함수 $f(\\theta_y)$를 반지름 $\\theta_R$인 원반에서 적분하면 $$I=\\int_{-\\theta_R}^{\\theta_R}\\mathrm d\\theta_y\\int_{-\\sqrt{\\theta_R^2-\\theta_y^2}}^{\\sqrt{\\theta_R^2-\\theta_y^2}}\\mathrm d\\theta_x\\,f(\\theta_y)=\\int_{-\\theta_R}^{\\theta_R}\\mathrm d\\theta_y\\cdot2\\sqrt{\\theta_R^2-\\theta_y^2}\\,f(\\theta_y)$$로 쓸 수 있다.'),
        ['$V=$'],
        L('The parts of the star radiate independently, so their intensities add. With mirrors moved apart by $d$ (Part D below; $d=0$ here), a patch contributes $$\\mathrm dI=\\mathcal J\\,\\mathrm d\\theta_x\\mathrm d\\theta_y\\left(3-2\\sqrt2\\cos\\left(\\varphi_0-\\tfrac{4\\pi}{\\lambda}\\alpha y+\\tfrac{2\\pi}{\\lambda}(L_1+L_2+d)\\theta_y\\right)\\right),\\quad \\varphi_0=\\tfrac{2\\pi}{\\lambda}(L_1+2L_3-L_2).$$ Integrating over $\\theta_x$ with the hint, $I_{\\max,\\min}=\\int_{-\\theta_R}^{\\theta_R}\\mathcal J\\sqrt{\\theta_R^2-\\theta_y^2}\\left(3\\pm2\\sqrt2\\cos\\tfrac{2\\pi}{\\lambda}(L_1+L_2+d)\\theta_y\\right)\\mathrm d\\theta_y$ (twice, up to a common factor), so $$V=\\frac{2\\sqrt2\\int_{-\\theta_R}^{\\theta_R}\\sqrt{\\theta_R^2-\\theta_y^2}\\cos\\left(\\frac{2\\pi}{\\lambda}(L_1+L_2+d)\\theta_y\\right)\\mathrm d\\theta_y}{3\\int_{-\\theta_R}^{\\theta_R}\\sqrt{\\theta_R^2-\\theta_y^2}\\,\\mathrm d\\theta_y}.$$ With $w=\\theta_y/\\theta_R$ the denominator integral is $\\pi/2$; with $\\eta=\\frac{2\\pi}{\\lambda}(L_1+L_2+d)\\theta_R$ and the even integrand, $$V=\\frac{8\\sqrt2}{3\\pi}\\int_0^1\\sqrt{1-w^2}\\cos(\\eta w)\\,\\mathrm dw.$$',
          '별의 각 부분은 서로 독립적으로 빛을 내므로 세기가 더해진다. 거울을 $d$만큼 벌릴 때(아래 D2; 여기서는 $d=0$) 작은 조각의 기여는 $$\\mathrm dI=\\mathcal J\\,\\mathrm d\\theta_x\\mathrm d\\theta_y\\left(3-2\\sqrt2\\cos\\left(\\varphi_0-\\tfrac{4\\pi}{\\lambda}\\alpha y+\\tfrac{2\\pi}{\\lambda}(L_1+L_2+d)\\theta_y\\right)\\right),\\quad \\varphi_0=\\tfrac{2\\pi}{\\lambda}(L_1+2L_3-L_2)$$이다. 힌트대로 $\\theta_x$에 대해 적분하면 $I_{\\max,\\min}=\\int_{-\\theta_R}^{\\theta_R}\\mathcal J\\sqrt{\\theta_R^2-\\theta_y^2}\\left(3\\pm2\\sqrt2\\cos\\tfrac{2\\pi}{\\lambda}(L_1+L_2+d)\\theta_y\\right)\\mathrm d\\theta_y$(공통 인수 제외)이므로 $$V=\\frac{2\\sqrt2\\int_{-\\theta_R}^{\\theta_R}\\sqrt{\\theta_R^2-\\theta_y^2}\\cos\\left(\\frac{2\\pi}{\\lambda}(L_1+L_2+d)\\theta_y\\right)\\mathrm d\\theta_y}{3\\int_{-\\theta_R}^{\\theta_R}\\sqrt{\\theta_R^2-\\theta_y^2}\\,\\mathrm d\\theta_y}.$$ $w=\\theta_y/\\theta_R$로 두면 분모의 적분은 $\\pi/2$이고, $\\eta=\\frac{2\\pi}{\\lambda}(L_1+L_2+d)\\theta_R$와 피적분 함수가 짝함수임을 쓰면 $$V=\\frac{8\\sqrt2}{3\\pi}\\int_0^1\\sqrt{1-w^2}\\cos(\\eta w)\\,\\mathrm dw.$$'),
        [[L('Correct contribution $\\mathrm dI$ of a small patch of the star.', '별의 작은 조각에서 오는 세기 $\\mathrm dI$를 바르게 씀.'), 0.3],
         [L('Intensity at an arbitrary point as an integral over one variable.', '임의의 점의 세기를 한 변수 적분으로 나타냄.'), 0.3],
         [L('Correct $I_{\\max}$ and $I_{\\min}$ (0.3 each).', '$I_{\\max}$와 $I_{\\min}$을 바르게 구함 (각 0.3점).'), 0.6],
         [L('Formula for the visibility $V$ as a ratio of integrals.', '가시도 $V$를 적분의 비로 나타냄.'), 0.4],
         [L('Denominator evaluated and final answer $V=\\frac{8\\sqrt2}{3\\pi}\\int_0^1\\sqrt{1-w^2}\\cos(\\eta w)\\,\\mathrm dw$.', '분모를 계산하고 최종 답 $V=\\frac{8\\sqrt2}{3\\pi}\\int_0^1\\sqrt{1-w^2}\\cos(\\eta w)\\,\\mathrm dw$를 얻음.'), 0.2]]],
      ['D2', 0.9,
        L('The interferometer is used to observe Betelgeuse. If mirrors M1 and M2 are moved symmetrically away from the centre of HM (so that $L_1^*=L_1+d/2$ and $L_2^*=L_2+d/2$), the visibility $V$ vanishes at $d=0.97$ m, $3.12$ m, … (the other parameters as in B3; here $L_1$ and $L_2$ are not given numerically, $\\lambda=500$ nm). Find the angular radius $\\theta_R$ of Betelgeuse, and its radius $R$ if its distance is $h=6.079\\cdot10^{15}$ km.<br><i>Hint:</i> the first two zeros of $F_n=\\int_0^1(1-w^2)^n\\cos(\\eta w)\\,\\mathrm dw$ as a function of $\\eta$ are:<table class="ztab"><tr><th>$n$</th><th>$\\eta_1$</th><th>$\\eta_2$</th></tr><tr><td>0.5</td><td>3.832</td><td>7.016</td></tr><tr><td>0</td><td>4.493</td><td>7.725</td></tr><tr><td>1.5</td><td>5.136</td><td>8.417</td></tr></table>',
          '이 간섭계로 베텔게우스를 관측한다. 거울 M1과 M2를 HM의 중심에서 대칭으로 멀리 옮기면($L_1^*=L_1+d/2$, $L_2^*=L_2+d/2$) 가시도 $V$가 $d=0.97$ m, $3.12$ m, …에서 0이 된다(나머지는 B3과 같고, 여기서 $L_1$, $L_2$의 수치는 주어지지 않으며 $\\lambda=500$ nm). 베텔게우스의 각반지름 $\\theta_R$를 구하고, 거리가 $h=6.079\\cdot10^{15}$ km일 때 반지름 $R$을 구하여라.<br><i>힌트:</i> $\\eta$의 함수 $F_n=\\int_0^1(1-w^2)^n\\cos(\\eta w)\\,\\mathrm dw$의 처음 두 영점은 다음과 같다.<table class="ztab"><tr><th>$n$</th><th>$\\eta_1$</th><th>$\\eta_2$</th></tr><tr><td>0.5</td><td>3.832</td><td>7.016</td></tr><tr><td>0</td><td>4.493</td><td>7.725</td></tr><tr><td>1.5</td><td>5.136</td><td>8.417</td></tr></table>'),
        ['$\\theta_R=$', '$R=$'],
        L('The first zeros of the visibility are $\\eta_1$, $\\eta_2$ for $n=0.5$. Hence $\\eta_2-\\eta_1=\\frac{2\\pi}{\\lambda}(d_2-d_1)\\theta_R$, $$\\theta_R=\\frac{(\\eta_2-\\eta_1)\\lambda}{2\\pi(d_2-d_1)}=1.18\\cdot10^{-7},\\qquad R=\\theta_Rh=7.16\\cdot10^{8}\\ \\text{km}.$$',
          '가시도의 처음 영점은 $n=0.5$일 때의 $\\eta_1$, $\\eta_2$이다. 따라서 $\\eta_2-\\eta_1=\\frac{2\\pi}{\\lambda}(d_2-d_1)\\theta_R$, $$\\theta_R=\\frac{(\\eta_2-\\eta_1)\\lambda}{2\\pi(d_2-d_1)}=1.18\\cdot10^{-7},\\qquad R=\\theta_Rh=7.16\\cdot10^{8}\\ \\text{km}.$$'),
        [[L('Stated that the first zeros of the integral are $\\eta_1$, $\\eta_2$ for $n=0.5$.', '적분의 처음 영점이 $n=0.5$의 $\\eta_1$, $\\eta_2$임을 언급.'), 0.4],
         [L('Correct formula $\\theta_R=(\\eta_2-\\eta_1)\\lambda/(2\\pi(d_2-d_1))$.', '식 $\\theta_R=(\\eta_2-\\eta_1)\\lambda/(2\\pi(d_2-d_1))$.'), 0.3],
         [L('Correct value $\\theta_R=1.18\\cdot10^{-7}$.', '값 $\\theta_R=1.18\\cdot10^{-7}$.'), 0.1],
         [L('Correct radius $R=7.16\\cdot10^8$ km.', '반지름 $R=7.16\\cdot10^8$ km.'), 0.1]]],
    ] },
];

/* the points of every item and part add up as printed */
let total = 0;
for (const part of PARTS) for (const [label, pts, , , , scheme] of part.items) {
  const s = scheme.reduce((n, r) => n + r[1], 0);
  if (Math.abs(s - pts) > 1e-9) throw new Error(`IPhO 2017 T4 ${label}: scheme ${s} ≠ ${pts}`);
  total += pts;
}
if (Math.abs(total - 10) > 1e-9) throw new Error('IPhO 2017 T4 total ' + total);

const TITLE = L('Measuring the Radius of a Star (10 points)', '별의 반지름 측정 (10점)');
const INTRO = L(
  '<p>Measuring the radii of stars is difficult because of their huge distances. Inhomogeneities of the atmosphere blur the image and make it hard to determine their actual size. One possible method is to use an interferometer, proposed by Michelson and Pease in 1921 to measure the diameter of Betelgeuse. The figure below shows the interferometer used to measure the radius of a star.</p>',
  '<p>별의 반지름은 거리가 매우 멀어 재기 어렵다. 대기의 불균일성이 상을 흐리게 하여 실제 크기를 알아내기 어렵게 만든다. 한 가지 방법은 간섭계를 쓰는 것으로, 1921년 마이컬슨과 피스가 베텔게우스의 지름을 재기 위해 제안했다. 아래 그림은 별의 반지름을 재는 데 쓴 간섭계를 보여 준다.</p>');
const INTRO2 = L(
  '<p>Reflected by mirror M1, ray 1 reaches the beam splitter HM, which reflects 50% of the light intensity and transmits the other 50%. The reflected ray goes to mirror M3, is reflected, passes through HM and falls on the screen. Meanwhile ray 2 is reflected by mirror M2; reflected by HM, it also reaches the screen. Mirrors M1, M2 and M3 reflect all the light falling on them and add $\\pi$ radians to its phase. The wavelength of the light is $\\lambda$.</p>',
  '<p>거울 M1에서 반사된 광선 1은 빔 분할기 HM에 닿는데, HM은 빛의 세기의 50%를 반사하고 나머지 50%를 투과시킨다. 반사된 광선은 거울 M3으로 가서 반사된 뒤 HM을 지나 스크린에 떨어진다. 한편 광선 2는 거울 M2에서 반사되고, HM에서 반사되어 역시 스크린에 닿는다. 거울 M1, M2, M3은 받은 빛을 모두 반사하며 위상에 $\\pi$ 라디안을 더한다. 빛의 파장은 $\\lambda$이다.</p>');

const CSS = `.ztab{border-collapse:collapse;margin:2mm 0 0;font-size:9pt}.ztab td,.ztab th{border:0.25mm solid #555;padding:0.6mm 3mm;text-align:center}
h1{color:#000;font-size:12pt;text-align:left;margin-bottom:4mm}h2{color:#000;font-size:11pt}
.q{grid-template-columns:11mm 1fr 15mm;border:0.35mm solid #000;padding:0;gap:0}.q>div{padding:2mm 2.5mm}.q>.l{border-right:0.35mm solid #000}.q>.p{border-left:0.35mm solid #000;text-align:center}
.code{display:grid;grid-template-columns:40mm repeat(6,1fr);border:0.4mm double #000;margin:2mm 0 6mm}.code>div{border-right:0.35mm solid #000;height:12mm;display:flex;align-items:center;justify-content:center;font-weight:700}.code>div:last-child{border-right:0}
table.at{width:100%;border-collapse:collapse;margin:0 0 4mm}table.at th{border:0.35mm solid #000;padding:1.2mm;font-size:8.5pt}table.at td{border:0.35mm solid #000;vertical-align:top;padding:2mm}
table.at td.qn{width:21mm;text-align:center;font-size:9pt;vertical-align:middle}table.at td.mk{width:15mm}table.at tr{break-inside:avoid}
.ms17{width:100%;border-collapse:collapse;margin:0 0 5mm;break-inside:auto}.ms17 th{background:#eee;border:0.3mm solid #777;padding:1mm;font-weight:400}.ms17 td{border:0.3mm solid #777;padding:1.5mm 2.5mm;vertical-align:top}
.ms17 td.m{width:20mm;text-align:center;vertical-align:middle}.ms17 tr.tot td{background:#eee;text-align:right}.qh{font-size:11pt;margin:4mm 0 1.5mm}`;

function paper(lang) {
  const out = [`<h1>${TITLE[lang]}</h1>`, INTRO[lang], FIG[1](lang), INTRO2[lang]];
  for (const part of PARTS) {
    out.push(`<h2>${part.title[lang]}</h2>`, part.intro[lang]);
    for (const [label, pts, question] of part.items) out.push(q(label.replace(/^(\w)(\d)$/, '$1.$2'), question[lang], `${pts.toFixed(1)} pt.`));
  }
  return out.join('\n');
}

function answerSheet(lang) {
  const shown = lang === 'ko' ? '(풀이 용지에 보임)' : '(shown on the working sheets)';
  const out = [`<div class="code"><div>${lang === 'ko' ? '수험번호' : 'Student Code'}</div><div></div><div></div><div></div><div></div><div></div><div></div></div>`];
  for (const part of PARTS) {
    out.push(`<h3>${part.title[lang].replace(/\s*\([^)]*\)\s*$/, '')}</h3><table class="at"><tr><th>${lang === 'ko' ? '문항' : 'Question'}</th><th>${lang === 'ko' ? '답' : 'Answer'}</th><th>${lang === 'ko' ? '배점' : 'Marks'}</th></tr>`);
    for (const [label, pts, , prompts] of part.items) {
      const lines = prompts.map(p => p.startsWith('(') ? `<p style="color:#555">${shown}</p>` : `<p style="margin:0 0 ${Math.max(9, 20 - prompts.length * 5)}mm">${p}</p>`).join('');
      out.push(`<tr><td class="qn">${label.replace(/^(\w)(\d)$/, '$1.$2')}<br><br>(<b>${pts.toFixed(1)} pt.</b>)</td><td style="height:${prompts.length > 1 ? 42 : 30}mm">${lines}</td><td class="mk"></td></tr>`);
    }
    out.push('</table>');
  }
  return out.join('\n');
}

function solution(lang) {
  const out = [`<h1 style="margin-top:0">${TITLE[lang].replace(/\s*\(.*\)$/, '')}</h1>`];
  for (const part of PARTS) for (const [label, pts, , , sol, scheme] of part.items) {
    const lab = label.replace(/^(\w)(\d)$/, '$1.$2');
    out.push(`<div class="qh">${lang === 'ko' ? '문제' : 'Question'} ${lab}</div><table class="ms17"><tr><th>${lang === 'ko' ? '답' : 'Answer'}</th><th>${lang === 'ko' ? '배점' : 'Marks'}</th></tr>
      <tr><td colspan="2">${sol[lang]}</td></tr>
      ${scheme.map(([t, p]) => `<tr><td>${t[lang]}</td><td class="m">${p.toFixed(1)} pts</td></tr>`).join('')}
      <tr class="tot"><td>${lang === 'ko' ? '합계' : 'Total'}</td><td class="m">${pts.toFixed(1)} pts</td></tr></table>`);
  }
  return out.join('\n');
}

const base = { css: CSS, section: 'Theory-Backup' };   // a shortlist (backup) problem, headed as IPhO 2025's T4
module.exports = {
  docs: [
    { ...base, out: 'pdfx/ipho/IPhO_2017_T4_EN.pdf', style: 'ipho2017', kind: 'paper', lang: 'en', code: 'T4', langLabel: 'English', html: paper('en') },
    { ...base, out: 'pdfx/ipho/IPhO_2017_T4_KO.pdf', style: 'ipho2017', kind: 'paper', lang: 'ko', code: 'T4', langLabel: 'Korean (Korea (Republic of))', html: paper('ko') },
    { ...base, out: 'pdfx/ipho/IPhO_2017_T4A.pdf', style: 'ipho2017', kind: 'answer', lang: 'en', code: 'AT4', langLabel: 'English', html: answerSheet('en') },
    { ...base, out: 'pdfx/ipho/IPhO_2017_T4_A_KO.pdf', style: 'ipho2017', kind: 'answer', lang: 'ko', code: 'AT4', langLabel: 'Korean (Korea (Republic of))', html: answerSheet('ko') },
    { ...base, out: 'pdfx/ipho/IPhO_2017_T4S.pdf', style: 'ipho2017sol', kind: 'solution', lang: 'en', code: 'T4', langLabel: 'English', html: solution('en') },
    { ...base, out: 'pdfx/ipho/IPhO_2017_T4_S_KO.pdf', style: 'ipho2017sol', kind: 'solution', lang: 'ko', code: 'T4', langLabel: 'Korean (Korea (Republic of))', html: solution('ko') },
  ],
  PARTS,
};
