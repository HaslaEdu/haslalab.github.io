#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  X Asian-Pacific Astronomy Olympiad  (APAO 2014, Irkutsk-Listvyanka)
  Observational round, cloudy sky, questions 9-10   (27 November 2014)
     9 Orion       10 Diurnal motion
  Virtual night sky
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The sky over the Baikal shore at Listvyanka (51°51' N, 104°53' E)
    on the evening of 27 November 2014 is covered by a closed cloud
    deck: no star shows.  The student points where Orion's Belt
    culminates and sweeps the hand along the diurnal path of a star
    through the zenith; nothing reacts to the answers.  Questions 11
    and 12 need the place itself and are left out.  No official
    solution was published: the solution and the self-check shown on
    request are HaslaLab's.

    Run:   python3 apao2014_O_sky_sim_KO.py
"""
import json
import math
import os
import time
import tkinter as tk
from tkinter import messagebox

APP_VERSION = "1.0"
LANG = "KO"          # the EN edition differs only in this line

DEG = math.pi / 180
SAVE = os.path.join(os.path.expanduser("~"), ".haslalab_apao2014_O.json")
# Listvyanka on the Baikal shore (UT+8), the evening of 27 November 2014, a closed cloud deck
LAT, LON, TZ, START = 51 + 51 / 60, 104 + 53 / 60, 8, 21.0
BELT_RA, BELT_DEC = 84.05, -1.20                 # Alnilam, the middle of Orion's Belt
ALT9 = 90 - LAT + BELT_DEC                       # where the belt culminates, due south
R10 = 90 - LAT                                   # polar distance of a star that reaches the zenith


def T(ko, en):
    return ko if LANG == "KO" else en


def norm360(a):
    return a % 360.0


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def unit(v):
    n = math.sqrt(dot(v, v))
    return [x / n for x in v]


def sep(a, b):
    return math.acos(max(-1.0, min(1.0, dot(unit(a), unit(b))))) / DEG


def altaz(h):
    return math.asin(max(-1.0, min(1.0, h[2]))) / DEG, norm360(math.atan2(h[0], h[1]) / DEG)


def hvec(alt, az):
    return [math.sin(az * DEG) * math.cos(alt * DEG), math.cos(az * DEG) * math.cos(alt * DEG), math.sin(alt * DEG)]


def refr(a):
    return 1.02 / math.tan((a + 10.3 / (a + 5.11)) * DEG) / 60 if a > -2 else 0.0


def hadec_to_hor(H, d):
    """hour angle and declination (degrees) -> unit vector in the local sky"""
    h, dd, p = H * DEG, d * DEG, LAT * DEG
    alt = math.asin(math.sin(p) * math.sin(dd) + math.cos(p) * math.cos(dd) * math.cos(h))
    az = math.atan2(-math.cos(dd) * math.sin(h), math.sin(dd) * math.cos(p) - math.cos(dd) * math.sin(p) * math.cos(h))
    return hvec(alt / DEG, az / DEG)


def hour_angle(h):
    alt, az = altaz(h)
    a, Z, p = alt * DEG, az * DEG, LAT * DEG
    return math.atan2(-math.sin(Z) * math.cos(a), math.sin(a) * math.cos(p) - math.cos(a) * math.sin(p) * math.cos(Z)) / DEG


def jd_ut(y, m, d, h):
    if m <= 2:
        y -= 1
        m += 12
    A = y // 100
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + 2 - A + A // 4 - 1524.5 + h / 24


def gmst_deg(J):
    T_ = (J - 2451545) / 36525
    return norm360(280.46061837 + 360.98564736629 * (J - 2451545) + 0.000387933 * T_ * T_)


def belt_transit():
    J = jd_ut(2014, 11, 27, 12 - TZ)
    for _ in range(3):
        lst = norm360(gmst_deg(J) + LON)
        J += ((BELT_RA - lst + 540) % 360 - 180) / 360.9856
    h = ((J + 0.5 + TZ / 24) % 1) * 24
    return "%d:%02d" % (int(h), int(round((h % 1) * 60)) % 60)


ZEN, POLE = [0.0, 0.0, 1.0], hvec(LAT, 0)
T9 = hvec(ALT9 + refr(ALT9), 180)
TRANSIT = belt_transit()


def judge10(pts):
    """how a swept path compares with the diurnal circle through the zenith"""
    if not pts or len(pts) < 3:
        return None
    err = sum(abs(sep(h, POLE) - R10) for h in pts) / len(pts)
    zen = min(sep(h, ZEN) for h in pts)
    span, prev = 0.0, hour_angle(pts[0])
    for h in pts[1:]:
        H = hour_angle(h)
        span += (H - prev + 540) % 360 - 180
        prev = H
    score = ((40 if err <= 3 else 25 if err <= 6 else 10 if err <= 10 else 0) + (20 if zen <= 4 else 10 if zen <= 8 else 0) + (20 if span > 20 else 0)
             + (20 if abs(span) >= 300 else 12 if abs(span) >= 180 else 5 if abs(span) >= 90 else 0))
    return err, zen, span, score


# the shore: the lake opens to the south-east and south, taiga hills stand behind the village
def _hills():
    s, L = 2014, []
    for _ in range(9):
        vals = []
        for _ in range(3):
            s = (s * 16807) % 2147483647
            vals.append(s / 2147483647)
        L.append((vals[0] * 360, 2 + vals[1] * 5, 6 + vals[2] * 14))
    return L


HILLS = _hills()


def skyline(az):
    az = norm360(az)
    if 105 < az < 235:
        return -0.2
    edge = min(abs((az - 105 + 540) % 360 - 180), abs((az - 235 + 540) % 360 - 180))
    ramp = min(1.0, edge / 14)
    h = 3.2 + 1.2 * math.sin(az * 0.05) + 0.4 * math.sin(az * 0.31)
    for a, ht, w in HILLS:
        d = abs((az - a + 540) % 360 - 180)
        h += ht * math.exp(-((d / w) ** 2))
    return h * ramp + 0.25 * math.sin(az * 2.7) * ramp


LIGHTS = [(250, 12), (262, 7), (95, 9), (80, 5), (170, 3), (150, 2)]
DOMES = [(300, 0.7, 10), (255, 0.5, 6), (90, 0.4, 6)]
HANDS = [("f1", T("손가락 1°", "Finger 1°"), 1), ("f3", T("세 손가락 5°", "3 fingers 5°"), 5), ("fist", T("주먹 10°", "Fist 10°"), 10), ("span", T("편 손 20°", "Spread 20°"), 20)]


def vnoise(x, y):
    def h(a, b):
        n = math.sin(a * 127.1 + b * 311.7) * 43758.5453
        return n - math.floor(n)
    X, Y = math.floor(x), math.floor(y)
    fx, fy = x - X, y - Y
    u, v = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    return h(X, Y) * (1 - u) * (1 - v) + h(X + 1, Y) * u * (1 - v) + h(X, Y + 1) * (1 - u) * v + h(X + 1, Y + 1) * u * v


def hexc(r, g, b):
    return "#%02x%02x%02x" % (int(max(0, min(255, r))), int(max(0, min(255, g))), int(max(0, min(255, b))))


QTEXT = T(
    "(9) 오리온. 오리온 벨트가 남중하는 하늘의 방향을 손으로 가리키세요(‘가리키기’로 한 번 클릭).\n\n"
    "(10) 일주 운동. 천정을 지날 수 있는 별의 일주 경로를 손으로 보여 주세요(‘손으로 그리기’로 별이 움직이는 방향대로 끌어서 그리기).\n\n"
    "하늘은 구름으로 덮여 있습니다. 별은 보이지 않으니 하늘의 좌표를 머릿속에 그려 손으로 보여 주세요. 전체 제한 시간 14분.\n\n"
    "시험의 11번(호숫가 불빛 사진)과 12번(망원경으로 건물 창문의 숫자 읽기)은 그 자리의 풍경과 시설이 있어야 하는 문제라 싣지 않았습니다.",
    "(9) Orion. By hand, point the direction to the sky where Orion's Belt culminates (one click with ‘Point’).\n\n"
    "(10) Diurnal motion. Show by your hand the diurnal way of a star that may pass through the zenith (drag with ‘Trace’, in the direction the star moves).\n\n"
    "The sky is overcast. No star shows, so picture the coordinates of the sky and show them with your hand. 14 minutes for all.\n\n"
    "Questions 11 (a photo of the lights on the embankment) and 12 (reading numbers in a window through a telescope) need the place itself and are left out.")


class App:
    def __init__(self, root):
        self.root = root
        root.title(T("APAO 2014 관측 라운드 — 흐린 하늘 (9–10번) · HaslaLab", "APAO 2014 observational round — cloudy sky (9–10) · HaslaLab"))
        root.configure(bg="#1c2027")
        root.geometry("1560x920")
        self.data = self.load()
        self.az, self.alt, self.fov = 150.0, 25.0, 110.0
        self.t0 = time.time()
        self.J0 = jd_ut(2014, 11, 27, START - TZ)
        self.tool, self.hand, self.mouse, self.drag, self.cur = "look", "fist", None, None, None
        self.solved, self.t_end = False, 0
        left = tk.Frame(root, bg="#22262d", width=360)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)
        right = tk.Frame(root, bg="#22262d", width=320)
        right.pack(side="right", fill="y", padx=(5, 10), pady=10)
        right.pack_propagate(False)
        mid = tk.Frame(root, bg="#1c2027")
        mid.pack(side="left", fill="both", expand=True, pady=10)
        q = tk.Text(left, wrap="word", bg="#12161b", fg="#d6dde2", relief="flat", font=("Malgun Gothic", 10), padx=10, pady=8)
        q.pack(fill="both", expand=True, padx=8, pady=8)
        q.tag_configure("h", foreground="#f2c14e", font=("Malgun Gothic", 11, "bold"))
        q.insert("end", T("(9–10) 흐린 하늘 — 2014년 11월 27일 밤, 바이칼 호숫가 리스트뱐카\n\n", "(9–10) Cloudy sky — the night of 27 Nov 2014, Listvyanka on Lake Baikal\n\n"), "h")
        q.insert("end", QTEXT)
        q.configure(state="disabled")
        bar = tk.Frame(mid, bg="#1c2027")
        bar.pack(fill="x", pady=(0, 4))
        self.tb = {}
        for k, lab in (("look", T("둘러보기", "Look")), ("point", T("가리키기", "Point")), ("trace", T("손으로 그리기", "Trace")), ("hand", T("손 재기", "Hand"))):
            b = tk.Button(bar, text=lab, command=lambda k=k: self.set_tool(k), bg="#2b2f36", fg="#e8eef2", relief="flat", font=("Segoe UI", 10, "bold"), padx=10)
            b.pack(side="left", padx=2)
            self.tb[k] = b
        self.hb = {}
        for k, lab, _ in HANDS:
            self.hb[k] = tk.Button(bar, text=lab, command=lambda k=k: self.set_hand(k), bg="#2b2f36", fg="#e8eef2", relief="flat", font=("Segoe UI", 9))
        self.clock = tk.Label(bar, text="", bg="#1c2027", fg="#f3d58a", font=("Consolas", 11, "bold"))
        self.clock.pack(side="right", padx=6)
        self.cv = tk.Canvas(mid, bg="#000", highlightthickness=0, cursor="fleur")
        self.cv.pack(fill="both", expand=True)
        tk.Label(mid, text=T("끌기: 둘러보기 / 휠: 시야 / 가리키기: 클릭 / 손으로 그리기: 별이 움직이는 방향대로 끌기 / 손 재기: 팔을 뻗은 손",
                             "Drag: look / wheel: field of view / Point: click / Trace: drag the way the star moves / Hand: your hand at arm's length"),
                 bg="#1c2027", fg="#9aa3ab", font=("Segoe UI", 8)).pack(anchor="w")
        ctl = tk.Frame(mid, bg="#1c2027")
        ctl.pack(fill="x", pady=(4, 0))
        tk.Button(ctl, text=T("시험 시작 (14분)", "Start (14 min)"), command=self.start, bg="#2b2f36", fg="#e8eef2", relief="flat").pack(side="left", padx=2)
        tk.Button(ctl, text=T("가리킨 것 지우기", "Clear pointing"), command=lambda: self.clear("pt"), bg="#2b2f36", fg="#e8eef2", relief="flat").pack(side="left", padx=2)
        tk.Button(ctl, text=T("그린 길 지우기", "Clear the path"), command=lambda: self.clear("tr"), bg="#2b2f36", fg="#e8eef2", relief="flat").pack(side="left", padx=2)
        self.timer = tk.Label(ctl, text="", bg="#1c2027", fg="#f3d58a", font=("Consolas", 11, "bold"))
        self.timer.pack(side="left", padx=8)
        self.info = tk.Label(mid, text="", bg="#1c2027", fg="#c3cbd2", justify="left", anchor="w", font=("Malgun Gothic", 9))
        self.info.pack(fill="x")
        cv = self.cv
        cv.bind("<Configure>", lambda e: self.redraw())
        cv.bind("<ButtonPress-1>", self.down)
        cv.bind("<B1-Motion>", self.move)
        cv.bind("<ButtonRelease-1>", self.up)
        cv.bind("<Motion>", self.hover)
        cv.bind("<MouseWheel>", lambda e: self.zoom(1 if e.delta < 0 else -1))
        cv.bind("<Button-4>", lambda e: self.zoom(-1))
        cv.bind("<Button-5>", lambda e: self.zoom(1))
        tk.Label(right, text=T("요약 답안지", "Summary answer sheet"), bg="#22262d", fg="#f2c14e", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        tk.Label(right, text=T("메모 (시험관에게 할 설명)", "Notes (what you would tell the examiner)"), bg="#22262d", fg="#c3cbd2", anchor="w").pack(fill="x", padx=10)
        self.note = tk.Text(right, height=5, wrap="word", bg="#14171c", fg="#e8eef2", insertbackground="#e8eef2", relief="flat")
        self.note.pack(fill="x", padx=10)
        self.note.insert("1.0", self.data.get("note", ""))
        self.note.bind("<KeyRelease>", lambda e: (self.data.__setitem__("note", self.note.get("1.0", "end-1c")), self.store()))
        tk.Button(right, text=T("해답 보기", "Show the solution"), command=self.show_sol, bg="#2b2f36", fg="#e8eef2", relief="flat").pack(fill="x", padx=10, pady=(14, 4))
        self.sol = tk.Label(right, text="", wraplength=295, justify="left", bg="#22262d", fg="#c3cbd2", font=("Malgun Gothic", 9))
        self.sol.pack(fill="x", padx=10)
        tk.Label(right, text=T("리스트뱐카(북위 51°51′, 동경 104°53′), 2014년 11월 27일 21:00(UT+8)의 하늘을 계산해 두고 구름으로 덮었습니다. 공식 해답이 공개되지 않아 해답과 점검 점수는 HaslaLab이 정했습니다. 답은 홈 폴더의 .haslalab_apao2014_O.json에 저장됩니다.",
                               "The sky over Listvyanka (51°51′ N, 104°53′ E) at 21:00 (UT+8) on 27 November 2014, covered with cloud. No official solution was published; the solution and the self-check scores are HaslaLab's. Answers are kept in .haslalab_apao2014_O.json in your home folder."),
                 wraplength=295, justify="left", bg="#22262d", fg="#9aa3ab", font=("Malgun Gothic", 8)).pack(side="bottom", fill="x", padx=10, pady=10)
        self.set_tool("look")
        self.sync()
        self.tick()

    # ---- storage
    def load(self):
        try:
            with open(SAVE, encoding="utf-8") as f:
                d = json.load(f)
            d.setdefault("pt", None)
            d.setdefault("tr", None)
            return d
        except (OSError, ValueError):
            return {"pt": None, "tr": None, "note": ""}

    def store(self):
        try:
            with open(SAVE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False)
        except OSError:
            pass

    # ---- time and tools
    def J(self):
        return self.J0 + (time.time() - self.t0) / 86400

    def start(self):
        self.t0 = time.time()
        self.t_end = time.time() + 14 * 60

    def tick(self):
        if self.t_end:
            s = max(0, int(self.t_end - time.time()))
            self.timer.configure(text=(T("남은 시간 ", "Time left ") + "%d:%02d" % (s // 60, s % 60)) if s else T("시간이 끝났습니다", "Time is up"), fg="#ff8a70" if s < 60 else "#f3d58a")
        h = ((self.J() + 0.5 + TZ / 24) % 1) * 24
        self.clock.configure(text=T("현지 시각 ", "local time ") + "%02d:%02d:%02d" % (int(h), int(h * 60) % 60, int(h * 3600) % 60))
        self.root.after(1000, self.tick)

    def set_tool(self, k):
        self.tool = k
        for kk, b in self.tb.items():
            b.configure(bg="#f2c14e" if kk == k else "#2b2f36", fg="#1c2027" if kk == k else "#e8eef2")
        for b in self.hb.values():
            if k == "hand":
                b.pack(side="left", padx=1)
            else:
                b.pack_forget()
        self.set_hand(self.hand)
        self.cv.configure(cursor={"look": "fleur", "point": "crosshair", "trace": "pencil", "hand": "none"}[k])

    def set_hand(self, k):
        self.hand = k
        for kk, b in self.hb.items():
            b.configure(bg="#f2c14e" if kk == k else "#2b2f36", fg="#1c2027" if kk == k else "#e8eef2")
        self.redraw()

    def zoom(self, d):
        self.fov = max(50.0, min(130.0, self.fov * (1.08 if d > 0 else 1 / 1.08)))
        self.redraw()

    def hover(self, e):
        self.mouse = (e.x, e.y)
        if self.tool == "hand":
            self.redraw()

    def down(self, e):
        if self.tool == "point":
            self.data["pt"] = self.unproj(e.x, e.y)
            self.store()
            self.sync()
            self.redraw()
        elif self.tool == "trace":
            self.cur = [self.unproj(e.x, e.y)]
        else:
            self.drag = (e.x, e.y, self.az, self.alt)

    def move(self, e):
        self.mouse = (e.x, e.y)
        if self.cur is not None:
            h = self.unproj(e.x, e.y)
            if dot(h, self.cur[-1]) < math.cos(0.8 * DEG):
                self.cur.append(h)
                self.redraw()
            return
        if not self.drag:
            return
        k = self.fov / max(100, self.cv.winfo_width())
        x0, y0, az0, alt0 = self.drag
        self.az = norm360(az0 - (e.x - x0) * k)
        self.alt = max(-5.0, min(90.0, alt0 + (e.y - y0) * k))
        self.redraw()

    def up(self, e):
        if self.cur is not None:
            if len(self.cur) > 2:
                self.data["tr"] = self.cur
                self.store()
                self.sync()
            self.cur = None
            self.redraw()
        self.drag = None

    def clear(self, k):
        self.data[k] = None
        self.store()
        self.sync()
        self.redraw()

    def sync(self):
        def aa(h):
            a, z = altaz(h)
            return T("방위각 %.0f°, 고도 %.0f°", "azimuth %.0f°, altitude %.0f°") % (z, a)
        s = T("9번 — 가리킨 곳: ", "Question 9 — pointed at: ") + (aa(self.data["pt"]) if self.data["pt"] else T("없음", "nothing"))
        s += T("     10번 — 그린 길: ", "     Question 10 — path: ") + (T("점 %d개", "%d points") % len(self.data["tr"]) if self.data["tr"] else T("없음", "none"))
        self.info.configure(text=s)

    def show_sol(self):
        if not messagebox.askyesno("APAO 2014", T("해답을 볼까요? 시험처럼 풀어 보려면 먼저 끝까지 풀어 보세요.", "Show the solution? To work it like the examination, finish first.")):
            return
        self.solved = True
        g = []
        if self.data["pt"]:
            d = sep(self.data["pt"], T9)
            g.append(T("9번: 정답에서 %.1f° 떨어짐 ", "Question 9: %.1f° from the answer ") % d + ("✓" if d <= 4 else "△" if d <= 8 else "✗"))
        j = judge10(self.data["tr"])
        if j:
            err, zen, span, sc = j
            g.append(T("10번: 원과의 평균 차 %.1f°, 천정에서 %.1f°, %s, 그린 범위 %.0f° → 자체 점검 %d/100", "Question 10: mean distance from the circle %.1f°, closest to the zenith %.1f°, %s, extent %.0f° → self-check %d/100")
                     % (err, zen, T("방향 맞음(서쪽으로)", "direction right (westwards)") if span > 20 else T("방향 틀림 또는 너무 짧음", "direction wrong or too short"), abs(span), sc))
        self.sol.configure(text=T(
            "공식 해답은 공개되지 않았습니다. HaslaLab 해답 — 하늘에 겹쳐 그려집니다.\n\n"
            "9.  정남(방위각 180°), 고도 ≈ %.0f° = 90° − φ + δ = 90° − 51.9° + (−1.2°). 벨트는 천구 적도 위에 있으므로 천구 적도가 자오선과 만나는 점입니다. 이날 실제 남중은 자정을 넘긴 현지 시각 %s쯤입니다.\n"
            "10. 적위 δ = φ = +51.9°인 별: 천구 북극(정북, 고도 51.9°)을 중심으로 각반지름 38.1°인 원. 위쪽 남중은 천정, 아래쪽 남중은 정북 고도 13.7°(지지 않는 주극성). 북쪽을 보면 시계 반대 방향, 천정에서는 동쪽에서 서쪽으로 지납니다.\n\n",
            "No official solution was published. HaslaLab's solution — drawn on the sky.\n\n"
            "9.  Due south (azimuth 180°), altitude ≈ %.0f° = 90° − φ + δ = 90° − 51.9° + (−1.2°): where the celestial equator crosses the meridian. That night it culminated after midnight, at about %s local time.\n"
            "10. A star of δ = φ = +51.9°: a circle of angular radius 38.1° around the north celestial pole (due north, altitude 51.9°). Upper culmination at the zenith, lower culmination 13.7° above the north point (it never sets). Facing north it turns anticlockwise, crossing the zenith from east to west.\n\n") % (ALT9, TRANSIT) + "\n".join(g))
        self.redraw()

    # ---- the view
    def basis(self):
        a, h = self.az * DEG, self.alt * DEG
        f = [math.sin(a) * math.cos(h), math.cos(a) * math.cos(h), math.sin(h)]
        r = [math.cos(a), -math.sin(a), 0.0]
        u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
        W = max(100, self.cv.winfo_width())
        return f, r, u, (W / 2) / (2 * math.tan(self.fov / 4 * DEG))

    def proj(self, x, B=None):
        f, r, u, s = B or self.B
        Z = dot(x, f)
        if Z < -0.3:
            return None
        k = 2 * s / (1 + Z)
        return self.W / 2 + dot(x, r) * k, self.H / 2 - dot(x, u) * k

    def unproj(self, px, py):
        f, r, u, s = self.basis()
        W, H = max(100, self.cv.winfo_width()), max(100, self.cv.winfo_height())
        X, Y = (px - W / 2) / s, -(py - H / 2) / s
        r2 = X * X + Y * Y
        d = 4 + r2
        a, b, c = 4 * X / d, 4 * Y / d, (4 - r2) / d
        return [a * r[i] + b * u[i] + c * f[i] for i in range(3)]

    def redraw(self):
        cv = self.cv
        cv.delete("all")
        self.W, self.H = max(100, cv.winfo_width()), max(100, cv.winfo_height())
        W, H = self.W, self.H
        self.B = self.basis()
        nx, ny = 56, 34                  # the cloud deck, lit from below by the village and Irkutsk
        for j in range(ny):
            for i in range(nx):
                x0, y0 = i * W / nx, j * H / ny
                v = self.unproj(x0 + W / nx / 2, y0 + H / ny / 2)
                alt, az = altaz(v)
                glow = 0.18
                for A, s, hs in DOMES:
                    d = abs((az - A + 540) % 360 - 180)
                    glow += 0.5 * s * math.exp(-max(0.3, alt) / (hs * 2.5)) * math.exp(-((d / 60) ** 2))
                r = 1 / max(0.12, math.sin(max(1, alt) * DEG))
                tex = 0.55 * vnoise(v[0] * r * 3, v[1] * r * 3) + 0.3 * vnoise(v[0] * r * 7, v[1] * r * 7) + 0.15 * vnoise(v[0] * r * 15, v[1] * r * 15)
                L = min(1.0, glow * (0.75 + 0.5 * tex))
                cv.create_rectangle(x0, y0, x0 + W / nx + 1, y0 + H / ny + 1, fill=hexc(14 + 70 * L, 13 + 58 * L, 16 + 50 * L), outline="")
        self.draw_ground()
        if self.solved:
            self.draw_key()
        if self.data["pt"]:
            p = self.proj(self.data["pt"])
            if p:
                cv.create_line(W / 2, H + 10, p[0], p[1], fill="#ff5a46", width=2)
                cv.create_oval(p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4, fill="#ff5a46", outline="")
                cv.create_text(p[0] + 8, p[1] - 8, text="9", fill="#ff5a46", anchor="w", font=("Segoe UI", 10, "bold"))
        for tr in [t for t in (self.data["tr"], self.cur) if t]:
            self.draw_path(tr, "#78dcff", "10")
        if self.tool == "hand" and self.mouse:
            self.draw_hand()

    def draw_path(self, pts, col, label, dash=None):
        cv = self.cv
        seg, acc, prev = [], 0.0, None
        for h in pts:
            p = self.proj(h)
            if p is None:
                if len(seg) >= 4:
                    cv.create_line(*seg, fill=col, width=2.5, dash=dash or "")
                seg, prev = [], None
                continue
            seg += [p[0], p[1]]
            if prev:
                l = math.hypot(p[0] - prev[0], p[1] - prev[1])
                acc += l
                if acc > 70 and l > 0.5:
                    acc = 0
                    cv.create_line(prev[0], prev[1], p[0], p[1], fill=col, width=2.5, arrow="last", arrowshape=(12, 14, 6))
            prev = p
        if len(seg) >= 4:
            cv.create_line(*seg, fill=col, width=2.5, dash=dash or "")
        p0 = self.proj(pts[0])
        if p0 and label:
            cv.create_text(p0[0] + 8, p0[1] - 8, text=label, fill=col, anchor="w", font=("Segoe UI", 10, "bold"))

    def draw_key(self):
        circle = [hadec_to_hor(H, LAT) for H in range(0, 361, 3)]
        self.draw_path(circle, "#ffd25a", "", dash=(7, 5))
        for h, t, c in ((T9, T("9: 오리온 벨트 남중 (정남, 고도 %.0f°)", "9: belt culminates (due south, altitude %.0f°)") % ALT9, "#ff8a70"),
                        (POLE, T("천구 북극 (고도 51.9°)", "north celestial pole (altitude 51.9°)"), "#9fd0ff"), (ZEN, T("천정", "zenith"), "#ffd25a"),
                        (hvec(LAT - R10, 0), T("10: 아래 남중 (정북, 고도 13.7°)", "10: lower culmination (due north, altitude 13.7°)"), "#ffd25a")):
            p = self.proj(h)
            if p:
                self.cv.create_oval(p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5, fill=c, outline="")
                self.cv.create_text(p[0] + 9, p[1] - 9, text=t, fill=c, anchor="w", font=("Segoe UI", 10, "bold"))

    def draw_ground(self):
        cv = self.cv
        W, H = self.W, self.H
        top = []
        for i in range(121):
            x = i * W / 120
            best, y = H * 2, -H
            while y < H * 2:
                a2, z2 = altaz(self.unproj(x, y))
                if a2 < skyline(z2):
                    best = y
                    break
                y += 6
            top.append((x, best))
        cv.create_polygon(*([0, H * 3] + [z for xy in top for z in xy] + [W, H * 3]), fill="#040507", outline="")
        for A, n in LIGHTS:
            p = self.proj(hvec(skyline(A) + 0.15, A))
            if p:
                for k in range(n):
                    dx = math.sin(A * 7 + k * 3.1) * 15
                    cv.create_rectangle(p[0] + dx, p[1] + 1 + k % 2, p[0] + dx + 1.5, p[1] + 2.5 + k % 2, fill="#ffc878" if k % 3 else "#f0f0ff", outline="")
        for i, n in enumerate(T(["북", "동", "남", "서"], ["N", "E", "S", "W"])):
            p = self.proj(hvec(skyline(i * 90) - 2.5, i * 90))
            if p and 0 < p[0] < W and p[1] < H + 20:
                cv.create_text(p[0], min(H - 8, p[1] + 14), text=n, fill="#c9a24a", font=("Segoe UI", 10, "bold"))

    def draw_hand(self):
        cv = self.cv
        x, y = self.mouse
        c = self.unproj(x, y)
        e = unit([c[1], -c[0], 0.0] if abs(c[2]) < 0.999 else [1, 0, 0])
        w = dict((k, a) for k, _, a in HANDS)[self.hand]
        q = self.proj([c[i] * math.cos(w * DEG) + e[i] * math.sin(w * DEG) for i in range(3)])
        s = (math.hypot(q[0] - x, q[1] - y) if q else w * self.B[3] * DEG) / w

        def R(x0, y0, ww, hh):
            cv.create_rectangle(x + x0 * s, y + y0 * s, x + (x0 + ww) * s, y + (y0 + hh) * s, fill="#0e0c0c", outline="#c9a24a")
        if self.hand == "f1":
            R(-0.5, -2.6, 1, 9)
        elif self.hand == "f3":
            for k in range(3):
                R(-2.5 + k * 1.67, -3.6 - (0.5 if k == 1 else 0), 1.6, 9)
            R(-2.6, 3, 5.4, 8)
        elif self.hand == "fist":
            R(-4.6, 1.5, 9.2, 7)
            R(-4.2, 7.5, 7.6, 7)
            for k in range(4):
                R(-5 + k * 2.5, -3.5 + (-0.3 if k in (1, 2) else 0.2), 2.5, 5.4)
            R(-5.2, 1.6, 7.4, 2.4)
        else:
            R(-4.5, -2, 13, 11)
            for k in range(4):
                R(-3.6 + k * 2.4, -10, 1.9, 9)
            R(-8.5, -4, 4.2, 2.2)
        lab = dict((k, l) for k, l, _ in HANDS)[self.hand]
        cv.create_text(x, y - {"span": 12, "f1": 4, "f3": 5, "fist": 5}[self.hand] * s - 10, text=lab, fill="#f2c14e", font=("Segoe UI", 9, "bold"))


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
