-- HaslaLab v4: problems of the week, graded submissions, rankings (accounts shared with the community)

CREATE TABLE problems (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  week        TEXT NOT NULL,                     -- ISO week, '2026-W44'
  no          INTEGER NOT NULL DEFAULT 1,        -- order within the week
  kind        TEXT NOT NULL,                     -- 'short' (a number, checked exactly) | 'essay' (graded against a rubric)
  subject     TEXT NOT NULL DEFAULT 'physics',   -- physics | astro | chem | bio
  level       INTEGER NOT NULL DEFAULT 2,        -- 1 easy .. 5 olympiad-hard
  points      INTEGER NOT NULL DEFAULT 100,
  title_ko    TEXT NOT NULL,
  title_en    TEXT NOT NULL,
  body_ko     TEXT NOT NULL,                     -- HTML-free text; $...$ marks a formula
  body_en     TEXT NOT NULL,
  unit        TEXT,                              -- short answers: the unit shown next to the box
  answer      TEXT,                              -- private. short: {"value":..,"rel":..,"abs":..}
  rubric      TEXT,                              -- private. essay: [{"id","name","max","requirement","partial"}]
  model_ko    TEXT,                              -- private until the week closes: the worked solution
  model_en    TEXT,
  source      TEXT,
  opens_at    INTEGER NOT NULL,
  closes_at   INTEGER NOT NULL,
  created_at  INTEGER NOT NULL
);
CREATE INDEX problems_week ON problems(week, no);
CREATE INDEX problems_open ON problems(opens_at, closes_at);

CREATE TABLE submissions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  problem_id  INTEGER NOT NULL REFERENCES problems(id),
  user_id     INTEGER NOT NULL REFERENCES users(id),
  answer      TEXT NOT NULL,                     -- the number, or the text of the solution
  via_ocr     INTEGER NOT NULL DEFAULT 0,        -- the text came from a photo and was checked by the student
  status      TEXT NOT NULL,                     -- 'graded' | 'pending' (waits for an AI key or a person) | 'error'
  score       INTEGER,                           -- NULL until graded
  detail      TEXT,                              -- JSON: per-criterion scores, feedback, grader
  in_week     INTEGER NOT NULL DEFAULT 0,        -- sent while the problem's week was open
  created_at  INTEGER NOT NULL,
  graded_at   INTEGER
);
CREATE INDEX subs_user    ON submissions(user_id, problem_id, id DESC);
CREATE INDEX subs_problem ON submissions(problem_id, status, score DESC);
CREATE INDEX subs_pending ON submissions(status, id);

/* the first week: Monday 26 October 2026 00:00 KST to Monday 2 November 00:00 KST */
INSERT INTO problems(week,no,kind,subject,level,points,title_ko,title_en,body_ko,body_en,unit,answer,rubric,model_ko,model_en,source,opens_at,closes_at,created_at) VALUES
('2026-W44',1,'short','physics',2,100,
 '흔들리는 막대','The swinging rod',
 '길이 $L = 1.20$ m인 균일한 가는 막대의 한쪽 끝을 마찰 없는 수평축에 매달았습니다. 막대가 연직면 안에서 작은 진폭으로 흔들릴 때 주기 $T$는 몇 초입니까? $g = 9.81$ m/s²로 하고 유효숫자 세 자리로 답하세요.',
 'A thin uniform rod of length $L = 1.20$ m hangs from a frictionless horizontal axis through one end. What is the period $T$ of small oscillations in the vertical plane? Take $g = 9.81$ m/s² and give three significant figures.',
 's','{"value":1.7943,"rel":0.006}',NULL,
 '물리 진자의 주기는 $T = 2\pi\sqrt{I/(mgd)}$입니다. 끝을 축으로 한 막대의 관성 모멘트는 $I = mL^2/3$, 질량 중심까지 거리는 $d = L/2$이므로 $T = 2\pi\sqrt{2L/(3g)} = 2\pi\sqrt{2.40/29.43} = 1.79$ s입니다.',
 'For a physical pendulum $T = 2\pi\sqrt{I/(mgd)}$. About its end the rod has $I = mL^2/3$ and its centre of mass is at $d = L/2$, so $T = 2\pi\sqrt{2L/(3g)} = 2\pi\sqrt{2.40/29.43} = 1.79$ s.',
 'HaslaLab', 1792940400, 1793545200, 1792940400),
('2026-W44',2,'short','astro',2,100,
 '시차와 절대 등급','Parallax and absolute magnitude',
 '어떤 별의 연주 시차는 $0.0250″$이고 겉보기 등급은 $V = 8.20$입니다. 성간 소광을 무시할 때 이 별의 절대 등급 $M_V$를 소수 둘째 자리까지 구하세요.',
 'A star has an annual parallax of $0.0250″$ and an apparent magnitude $V = 8.20$. Ignoring interstellar extinction, find its absolute magnitude $M_V$ to two decimal places.',
 NULL,'{"value":5.19,"abs":0.02}',NULL,
 '거리는 $d = 1/p = 1/0.0250 = 40.0$ pc입니다. 거리 지수 $m - M = 5\log_{10}(d/10\ \mathrm{pc}) = 5\log_{10}4 = 3.01$이므로 $M_V = 8.20 - 3.01 = 5.19$입니다.',
 'The distance is $d = 1/p = 1/0.0250 = 40.0$ pc. The distance modulus is $m - M = 5\log_{10}(d/10\ \mathrm{pc}) = 5\log_{10}4 = 3.01$, so $M_V = 8.20 - 3.01 = 5.19$.',
 'HaslaLab', 1792940400, 1793545200, 1792940400),
('2026-W44',3,'essay','physics',3,100,
 '쓰러지지 않는 팽이','The top that does not fall',
 '빠르게 도는 팽이는 기울어진 채로 쓰러지지 않고 연직축 둘레를 천천히 돕니다(세차 운동). 질량 $m$인 팽이가 축 방향으로 크기 $L$인 스핀 각운동량을 가지고, 받침점에서 질량 중심까지의 거리가 $r$일 때, (가) 팽이가 쓰러지지 않고 세차하는 까닭을 돌림힘과 각운동량으로 설명하고, (나) 세차 각속도 $\Omega$를 유도하세요. (다) 어떤 근사를 썼는지, 그 근사가 언제 성립하는지 밝히세요.',
 'A fast-spinning top leans over yet does not fall; instead its axis slowly turns about the vertical (precession). A top of mass $m$ has spin angular momentum of magnitude $L$ along its axis, and its centre of mass is a distance $r$ from the pivot. (a) Explain with torque and angular momentum why it precesses instead of falling. (b) Derive the precession angular velocity $\Omega$. (c) State the approximation you used and when it holds.',
 NULL,NULL,
 '[{"id":"A","name":"돌림힘의 크기와 방향 / Torque, its size and direction","max":25,"requirement":"Gravity acting at the centre of mass gives a torque about the pivot of size m g r sin(theta), horizontal and perpendicular to the plane of the axis and the vertical.","partial":"Half credit for the size or the direction alone."},{"id":"B","name":"dL/dt = 돌림힘, 각운동량의 방향만 바뀜 / dL/dt = torque changes only the direction","max":25,"requirement":"Uses dL/dt = tau; since tau is perpendicular to L, L changes direction (sweeps horizontally) but not magnitude, so the axis turns instead of tipping.","partial":"Partial credit if dL/dt = tau is stated without explaining why the tilt stays the same."},{"id":"C","name":"세차 각속도 유도 / Derivation of Omega","max":30,"requirement":"Horizontal component L sin(theta) turns by dphi in dt with dL = L sin(theta) dphi = m g r sin(theta) dt, giving Omega = m g r / L (= m g r /(I omega)), independent of the tilt.","partial":"Up to 15 for the right idea with an algebra slip or a missing sin(theta) cancellation explained."},{"id":"D","name":"근사와 성립 조건 / The approximation and its validity","max":20,"requirement":"Fast-top (gyroscopic) approximation: the angular momentum of the precession itself is neglected, valid when the spin angular momentum is large, i.e. Omega much smaller than the spin rate (L much larger than I_perp Omega); mentions nutation or friction-free pivot as acceptable extras.","partial":"Half credit for naming the approximation without the condition."}]',
 '(가) 중력 $mg$가 질량 중심에 작용하므로 받침점에 대한 돌림힘은 $\tau = mgr\sin\theta$이고, 방향은 수평이며 팽이 축과 연직선이 이루는 면에 수직입니다. (나) $d\vec L/dt = \vec\tau$이고 $\vec\tau \perp \vec L$이므로 $\vec L$의 크기는 그대로이고 방향만 수평으로 돕니다. 축의 수평 성분 $L\sin\theta$가 $dt$ 동안 $d\varphi$만큼 돌면 $|d\vec L| = L\sin\theta\,d\varphi = mgr\sin\theta\,dt$이므로 $\Omega = d\varphi/dt = mgr/L = mgr/(I\omega)$로, 기울기와 무관합니다. (다) 세차 운동 자체의 각운동량을 무시한 빠른 팽이 근사이며, 스핀 각운동량이 충분히 커서 $\Omega$가 스핀 각속도보다 훨씬 작을 때 성립합니다. 그렇지 않으면 장동이 함께 나타납니다.',
 '(a) Gravity $mg$ acts at the centre of mass, so the torque about the pivot is $\tau = mgr\sin\theta$, horizontal and perpendicular to the plane of the axis and the vertical. (b) $d\vec L/dt = \vec\tau$ with $\vec\tau \perp \vec L$, so $\vec L$ keeps its size and only swings round horizontally. The horizontal part $L\sin\theta$ turns by $d\varphi$ in $dt$: $|d\vec L| = L\sin\theta\,d\varphi = mgr\sin\theta\,dt$, so $\Omega = d\varphi/dt = mgr/L = mgr/(I\omega)$, independent of the tilt. (c) This is the fast-top approximation: the angular momentum of the precession itself is neglected, valid when the spin angular momentum is large so that $\Omega$ is much smaller than the spin rate; otherwise nutation appears as well.',
 'HaslaLab', 1792940400, 1793545200, 1792940400);
