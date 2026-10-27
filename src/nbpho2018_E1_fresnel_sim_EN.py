#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  Nordic-Baltic Physics Olympiad 2018  (Tallinn, Estonia)
  Problem 4 :  FRESNEL PRISM
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
  Single file, Tkinter, Python standard library only.

Design rule (non-negotiable):
    The tools of the problem: a sheet of Fresnel prism (a transparent
    sheet whose surface is a sawtooth of pitch d and facet angle alpha,
    n = 1.47), a sheet with coloured stripes, a cardboard screen, a
    ruler, a measuring tape, a stand and a green laser (532 nm).
    For the laser the sheet is a blazed grating: a long row of spots on
    the screen, the brightest where the facets refract the beam.  Seen
    through, it is a prism of small angle: a stripe moves by h tan(beta),
    and the magenta (630 nm) and cyan (495 nm) stripes move by different
    amounts because n falls with the wavelength.
    Only what the student would see is shown.  The values are randomised
    each session; --seed N repeats a session.

    Run:   python3 nbpho2018_E1_fresnel_sim_KO.py   [--seed N]
"""
import math
import random
import sys
import tkinter as tk

APP_VERSION = "1.0"
LANG = "EN"          # the EN edition differs only in this line


def T(ko, en):
    return ko if LANG == "KO" else en


SEED = None
for i, a in enumerate(sys.argv):
    if a == "--seed" and i + 1 < len(sys.argv):
        SEED = int(sys.argv[i + 1])
RNG = random.Random(SEED)


def gauss():
    return RNG.gauss(0.0, 1.0)


# ==============================================================================
#  1.  시트 (학생에게 보이지 않음)
# ==============================================================================
P_D = 0.300e-3 * (1 + 0.05 * gauss())        # 피치 (m)
P_ALPHA = 0.25 * (1 + 0.04 * gauss())        # 프리즘 각 (rad)
P_N0 = 1.47                                  # 532 nm에서의 굴절률
P_DNDL = -5.5e-5 * (1 + 0.08 * gauss())      # dn/dλ (1/nm)
LAM0, LAM_M, LAM_C = 532, 630, 495


def n_of(lam):
    return P_N0 + P_DNDL * (lam - LAM0)


def beta_of(lam):
    """평평한 면으로 수직으로 들어가 톱니 면으로 나오는 빛의 꺾임각"""
    return math.asin(min(0.999, n_of(lam) * math.sin(P_ALPHA))) - P_ALPHA


TAPE0 = -58.0                                # 줄자의 0 (cm, 실험대 x)
HOLD_X = -45.5 + 0.3 * gauss()               # 프리즘 홀더 위치 (cm)
R0 = 32 + 4 * RNG.random()                   # 프리즘 없이 빔이 스크린 자에 닿는 곳 (mm)
BX1 = 74.0


class State(object):
    def __init__(self):
        self.mode = "laser"       # laser | look
        self.laser = False
        self.prism_in = True
        self.flip = False
        self.scr_x = 40.0         # 스크린 위치 (cm)
        self.h = 22.0             # 종이에서 프리즘까지 (cm)
        self.sheet_u = 0.0        # 종이를 민 거리 (mm)


S = State()


def spots():
    """스크린 위의 빛: 블레이즈 회절격자의 차수들, 톱니가 굴절시키는 방향이 가장 밝다"""
    if not S.laser:
        return []
    if not S.prism_in or S.mode != "laser":
        return [(R0, 1.0)]
    L = (S.scr_x - HOLD_X) / 100
    lam = LAM0 * 1e-9
    sgn = -1 if S.flip else 1
    sb = math.sin(beta_of(LAM0))
    mB = int(round(sb * P_D / lam))
    out = []
    for m in range(mB - 160, mB + 161):
        s = m * lam / P_D
        if abs(s) >= 0.95:
            continue
        u = math.pi * P_D / lam * (s - sb)
        env = 1.0 if abs(u) < 1e-9 else (math.sin(u) / u) ** 2
        I = 0.9 * env + 0.05 * math.exp(-((m - mB) / 30.0) ** 2) + 0.012 * math.exp(-(m / 18.0) ** 2)
        if I < 0.0025:
            continue
        out.append((R0 + sgn * L * math.tan(math.asin(s)) * 1000, I))
    return out


# 줄무늬 종이 (mm): A 흰 선 8 mm 간격, B 청록·자홍 쌍 (중심 간격 0.5 … 1.5 mm)
STRIPES = []
for _i in range(17):
    STRIPES.append(dict(x=-140 + 8 * _i, w=0.45, kind="white", lab=_i))
_x = 20.0
for _g in (0.5, 0.7, 0.9, 1.1, 1.3, 1.5):
    STRIPES += [dict(x=_x, w=0.35, kind="cyan"), dict(x=_x + _g, w=0.35, kind="mag", gap=_g)]
    _x += 11
    STRIPES += [dict(x=_x, w=0.35, kind="mag"), dict(x=_x + _g, w=0.35, kind="cyan", gap=_g)]
    _x += 13
INK = {"white": [(460, (70, 90, 255), 0.8), (532, (60, 255, 80), 1.0), (610, (255, 80, 40), 0.9)],
       "cyan": [(495, (0, 235, 205), 1.0), (455, (40, 80, 255), 0.35)], "mag": [(630, (255, 40, 60), 1.0), (450, (90, 60, 255), 0.4)]}
SHEET_W, SHEET_D = 297.0, 210.0


def shift_mm(lam):
    return (-1 if S.flip else 1) * S.h * 10 * math.tan(beta_of(lam))


# ==============================================================================
#  2.  화면
# ==============================================================================
BG, PANEL, PANEL2 = "#1c2027", "#22262d", "#2b2f36"
FG, FG_DIM, ACC = "#e8eef2", "#9aa3ab", "#f2c14e"
VIEWS = [("bench", T("실험대 (위에서)", "bench, from above")), ("screen", T("스크린", "the screen")),
         ("look", T("프리즘으로 보기", "looking through the prism")), ("side", T("프리즘 높이 (옆에서)", "prism height, from the side"))]
HELP = {"bench": T("스크린을 줄자를 따라 끌기 · 휠: 스크린 1 cm (Shift: 1 mm) · 줄자에서 프리즘 홀더와 스크린의 위치를 읽기",
                   "drag the screen along the tape · wheel: screen by 1 cm (Shift: 1 mm) · read the holder and the screen on the tape"),
        "screen": T("판지 스크린과 밀리미터 자 — 휠: 확대, 끌기: 이동", "the cardboard screen and its millimetre ruler — wheel to zoom, drag to pan"),
        "look": T("위에서 본 줄무늬 종이, 왼쪽 부분 위에 프리즘 — 휠: 확대, 끌기: 종이 밀기", "the striped sheet from above, the prism over its left part — wheel to zoom, drag to slide the sheet"),
        "side": T("옆에서 본 스탠드 — 클램프를 위아래로 끌기, 높이는 미터자로 — 휠: 확대", "the stand from the side — drag the clamp up or down, read the height on the metre stick — wheel to zoom")}


def mix(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in rgb)


class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title(T("NBPhO 2018 실험 시뮬레이터 — 문제 4 프레넬 프리즘", "NBPhO 2018 Experiment Simulator — Problem 4 Fresnel prism") + "   v" + APP_VERSION)
        self.geometry("1480x860")
        self.configure(bg=BG)
        self.view = "bench"
        self.vz = {v: [1.0, 0.0, 0.0] for v, _ in VIEWS}
        self.drag = None
        self._build()
        self.after(30, self._tick)

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x")
        tk.Label(top, text="NBPhO 2018  ·  " + T("문제 4 프레넬 프리즘 (12점)", "Problem 4 Fresnel prism (12 pts)"), bg=BG, fg=ACC,
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=14, pady=6)
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        tabs = tk.Frame(left, bg=BG)
        tabs.pack(fill="x")
        self.tabb = {}
        for v, lab in VIEWS:
            b = tk.Button(tabs, text=lab, relief="flat", bd=0, padx=10, pady=4, font=("Segoe UI", 10), command=lambda v=v: self.show(v))
            b.pack(side="left", padx=(0, 4))
            self.tabb[v] = b
        self.help = tk.Label(left, anchor="w", bg=BG, fg=FG_DIM, font=("Segoe UI", 9))
        self.help.pack(fill="x")
        self.cv = tk.Canvas(left, bg="#2e3238", highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        right = tk.Frame(body, bg=PANEL, width=300)
        right.pack(side="left", fill="y", padx=(8, 0))
        right.pack_propagate(False)
        self.bs = dict(bg=PANEL2, fg=FG, activebackground="#343941", activeforeground=FG, relief="flat", bd=0, padx=8, pady=5, font=("Segoe UI", 10))

        def H(t):
            tk.Label(right, text=t, bg=PANEL, fg=ACC, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        H(T("배치", "Arrangement"))
        self.b_ml = tk.Button(right, text=T("프리즘: 레이저 쪽 홀더에", "Prism: in the laser stand"), command=lambda: setattr(S, "mode", "laser"), **self.bs)
        self.b_ml.pack(fill="x", padx=10, pady=1)
        self.b_mk = tk.Button(right, text=T("프리즘: 줄무늬 종이 위에", "Prism: held over the striped sheet"), command=lambda: setattr(S, "mode", "look"), **self.bs)
        self.b_mk.pack(fill="x", padx=10, pady=1)
        H(T("조작", "Controls"))
        self.b_las = tk.Button(right, command=lambda: setattr(S, "laser", not S.laser), **self.bs)
        self.b_las.pack(fill="x", padx=10, pady=1)
        self.b_pin = tk.Button(right, command=lambda: setattr(S, "prism_in", not S.prism_in) if S.mode == "laser" else None, **self.bs)
        self.b_pin.pack(fill="x", padx=10, pady=1)
        tk.Button(right, text=T("프리즘 시트 180° 돌리기", "Turn the prism sheet over (180°)"), command=lambda: setattr(S, "flip", not S.flip), **self.bs).pack(fill="x", padx=10, pady=1)
        H(T("안내", "Notes"))
        tk.Label(right, justify="left", wraplength=265, bg=PANEL, fg=FG_DIM, font=("Segoe UI", 8), text=T(
            "• 주의! 레이저의 직접광이나 반사광을 절대 들여다보지 마세요.\n• 줄자는 실험대 앞 가장자리를 따라 깔려 있습니다.\n• 자홍 줄무늬가 흩뜨리는 빛의 세기 최대는 630 nm, 청록 줄무늬는 495 nm입니다.\n• 가시광선 범위에서 n(λ)는 파장의 일차 함수입니다.",
            "• NB! Never look into the direct or reflected laser light.\n• The tape runs along the front edge of the bench.\n• The intensity maximum of the light scattered by the magenta stripes is at 630 nm, by the cyan stripes at 495 nm.\n• In the visible range n(λ) is a linear function of the wavelength.")).pack(anchor="w", padx=10)
        self.cv.bind("<ButtonPress-1>", self.press)
        self.cv.bind("<B1-Motion>", self.motion)
        self.cv.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag", None))
        self.cv.bind("<MouseWheel>", lambda e: self.wheel(e, 1 if e.delta > 0 else -1))
        self.cv.bind("<Button-4>", lambda e: self.wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self.wheel(e, -1))
        self.show("bench")

    def show(self, v):
        self.view = v
        for k, b in self.tabb.items():
            b.config(bg=ACC if k == v else PANEL2, fg="#1c2027" if k == v else FG)
        self.help.config(text=HELP[v])

    # ---- 좌표 -------------------------------------------------------------
    def vmap(self):
        W, H = self.cv.winfo_width(), self.cv.winfo_height()
        z, px, py = self.vz[self.view]
        v = self.view
        if v == "screen":
            k, ox, oy = W / 345.0, W / 2 - 150 * W / 345.0, H * 0.42
        elif v == "look":
            k = W / 135.0
            ox, oy = W / 2, 26 + SHEET_D / 2 * k
        elif v == "side":
            k = (H - 40) / 66.0
            ox, oy = W * 0.55, H - 22
        else:
            k = (W - 40) / 150.0
            ox, oy = W / 2 - 2 * k, H / 2
        return k * z, ox + px, oy + py

    def S_(self, x, y):
        k, ox, oy = self.vmap()
        return ox + x * k, oy - y * k

    def M_(self, sx, sy):
        k, ox, oy = self.vmap()
        return (sx - ox) / k, (oy - sy) / k

    def press(self, e):
        w = self.M_(e.x, e.y)
        z = self.vz[self.view]
        self.drag = dict(p=(e.x, e.y), w=w, h=S.h, u=S.sheet_u, scr=S.scr_x, px=z[1], py=z[2], what=None)
        if self.view == "bench" and abs(w[0] - S.scr_x) < 3 and -8 < w[1] < 30:
            self.drag["what"] = "screen"
        if self.view == "side" and S.mode == "look" and 7 < w[0] < 11 and abs(w[1] - S.h) < 2.5:
            self.drag["what"] = "clamp"

    def motion(self, e):
        d = self.drag
        if not d:
            return
        w = self.M_(e.x, e.y)
        z = self.vz[self.view]
        if d["what"] == "screen":
            S.scr_x = max(HOLD_X + 12, min(BX1 - 2, d["scr"] + w[0] - d["w"][0]))
        elif d["what"] == "clamp":
            S.h = max(2.0, min(58.0, d["h"] + (w[1] - d["w"][1])))
        elif self.view == "look":
            S.sheet_u = max(-150, min(150, d["u"] - (w[0] - d["w"][0])))
            z[2] = d["py"] + e.y - d["p"][1]
        else:
            z[1] = d["px"] + e.x - d["p"][0]
            z[2] = d["py"] + e.y - d["p"][1]

    def wheel(self, e, s):
        if self.view == "bench":
            S.scr_x = max(HOLD_X + 12, min(BX1 - 2, S.scr_x + s * (0.1 if (e.state & 1) else 1)))
            return
        z = self.vz[self.view]
        k, ox, oy = self.vmap()
        f = 1.15 if s > 0 else 1 / 1.15
        nz = max(0.5, min(40, z[0] * f))
        r = nz / z[0]
        ox0, oy0 = ox - z[1], oy - z[2]
        z[1] = (e.x - ox0) - (e.x - ox0 - z[1]) * r
        z[2] = (e.y - oy0) - (e.y - oy0 - z[2]) * r
        z[0] = nz

    # ---- 그리기 -------------------------------------------------------------
    def rect(self, x0, y0, x1, y1, **kw):
        a, b = self.S_(x0, y0), self.S_(x1, y1)
        return self.cv.create_rectangle(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]), **kw)

    def draw_bench(self):
        c = self.cv
        k = self.vmap()[0]
        self.rect(-70, 26, BX1, -24, fill="#3a3d42", outline="")
        self.rect(TAPE0, -24, BX1, -21.4, fill="#f2cf2e", outline="")
        for mm in range(0, int((BX1 - TAPE0) * 10) + 1):
            if k < 12 and mm % 10:
                continue
            x = self.S_(TAPE0 + mm / 10.0, 0)[0]
            y0 = self.S_(0, -21.4)[1]
            L = 0.5 if mm % 10 == 0 else (0.35 if mm % 5 == 0 else 0.2)
            c.create_line(x, y0, x, y0 + L * k, fill="#1b1b1b")
            if mm % 100 == 0 or (mm % 10 == 0 and k > 9):
                c.create_text(x, self.S_(0, -23.2)[1], text=str(mm // 10), fill="#c8262b" if mm % 100 == 0 else "#1b1b1b", font=("Segoe UI", 8, "bold"))
        self.rect(TAPE0 - 6, -25, TAPE0, -20, fill="#c8262b", outline="")
        self.rect(-66, -1.6, -55, 1.6, fill="#2b2d31", outline="")
        c.create_oval(*self.S_(-63.5, 0.4), *self.S_(-62.5, -0.4), fill="#45d46a" if S.laser else "#8f2f28", outline="")
        sx = HOLD_X - 1
        self.rect(sx - 14.85, 2.5, sx + 14.85, 23.5, fill="#0e0f12", outline="#555")
        self.rect(HOLD_X - 3.5, -4, HOLD_X + 8.5, -12, fill="#2a2c30", outline="")
        c.create_oval(*self.S_(HOLD_X + 1.9, -7.4), *self.S_(HOLD_X + 3.1, -8.6), fill="#b9bec4", outline="")
        if S.mode == "laser" and S.prism_in:
            self.rect(HOLD_X - 0.2, -5, HOLD_X + 0.2, 5, fill="#aad7f0", outline="")
        elif S.mode == "look":
            self.rect(HOLD_X - 9, 8, HOLD_X + 1, 18, fill="", outline="#9cc7de", width=2)
        else:
            self.rect(HOLD_X + 4, -3, HOLD_X + 14, 7, fill="", outline="#9cc7de")
        z0 = -0.1 * R0 - 1.5          # 스크린 판지의 한쪽 끝 (자의 0이 z0 + 1.5)
        self.rect(S.scr_x, -z0, S.scr_x + 0.6, -z0 - 34, fill="#b48a5a", outline="")
        if S.laser:
            sp = spots()
            if S.mode == "laser" and S.prism_in:
                c.create_line(*self.S_(-55, 0), *self.S_(HOLD_X, 0), fill="#5aff5a")
                for x, I in sp:
                    if I > 0.25:
                        c.create_line(*self.S_(HOLD_X, 0), *self.S_(S.scr_x, -(x - R0) / 10.0), fill="#5aff5a")
            else:
                c.create_line(*self.S_(-55, 0), *self.S_(S.scr_x, 0), fill="#5aff5a")
        c.create_text(*self.S_(-60, 8), text=T("레이저", "laser"), fill=FG_DIM)
        c.create_text(*self.S_(S.scr_x, 22), text=T("스크린", "screen"), fill=FG_DIM)

    def draw_screen(self):
        c = self.cv
        W, H = c.winfo_width(), c.winfo_height()
        k = self.vmap()[0]
        c.create_rectangle(0, 0, W, H, fill="#121316", outline="")
        self.rect(-15, 150, 325, -90, fill="#8f6c45" if S.laser else "#76593a", outline="")
        self.rect(-6, -4.5, 306, -20.5, fill="#f4f1e6", outline="")
        for mm in range(0, 301):
            if k < 1.6 and mm % 5:
                continue
            x = self.S_(mm, 0)[0]
            if x < -20 or x > W + 20:
                continue
            L = 5.2 if mm % 10 == 0 else (3.6 if mm % 5 == 0 else 2.2)
            c.create_line(x, self.S_(0, -4.5)[1], x, self.S_(0, -4.5 - L)[1], fill="#1e1e1e")
            if mm % 10 == 0 and (k > 2.2 or mm % 50 == 0):
                c.create_text(x, self.S_(0, -13)[1], text=str(mm // 10), fill="#1e1e1e", font=("Segoe UI", 8))
        for x, I in spots():
            sx, sy = self.S_(x, 0)
            if sx < -30 or sx > W + 30:
                continue
            R = (0.3 + 0.35 * math.sqrt(I)) * k + 0.9
            g = min(1.0, 0.25 + 1.5 * I)
            c.create_oval(sx - R * 1.6, sy - R * 1.6, sx + R * 1.6, sy + R * 1.6, fill=mix((143 * (1 - g * 0.5), 108 + 147 * g, 69 * (1 - g))), outline="")
            c.create_oval(sx - R * 0.7, sy - R * 0.7, sx + R * 0.7, sy + R * 0.7, fill=mix((143 + 100 * g, 108 + 147 * g, 69 + 160 * g)), outline="")

    def draw_look(self):
        c = self.cv
        W, H = c.winfo_width(), c.winfo_height()
        k = self.vmap()[0]
        c.create_rectangle(0, 0, W, H, fill="#3a3d42", outline="")
        off = S.sheet_u
        self.rect(-SHEET_W / 2 - off, SHEET_D / 2, SHEET_W / 2 - off, -SHEET_D / 2, fill="#0e0f12", outline="")
        top, bot = self.S_(0, SHEET_D / 2 - 14)[1], self.S_(0, -SHEET_D / 2 + 14)[1]
        edge = self.S_(0, 0)[0]
        over = S.mode == "look"
        # 겹치는 빛은 더한다: 화면 열 단위로 색을 모은다
        cols = {}

        def band(X, w, rgb, wt, under):
            x0, x1 = self.S_(X - w / 2, 0)[0], self.S_(X + w / 2, 0)[0]
            l, r = min(x0, x1), max(x0, x1)
            if under:
                r = min(r, edge)
            elif over:
                l = max(l, edge)
            if r <= l:
                return
            frac = min(1.0, (r - l) / 1.2)
            for px in range(int(math.floor(l)), int(math.ceil(max(r, l + 1)))):
                a = cols.setdefault(px, [0.0, 0.0, 0.0])
                for i in range(3):
                    a[i] += rgb[i] * wt * frac
        for s in STRIPES:
            X = s["x"] - off
            for lam, rgb, wt in INK[s["kind"]]:
                band(X, s["w"], rgb, wt, False)
                if over:
                    band(X + shift_mm(lam), s["w"], rgb, wt * 0.92, True)
        for px, a in cols.items():
            if -2 < px < W + 2:
                c.create_line(px, top, px, bot, fill=mix((14 + a[0], 15 + a[1], 18 + a[2])))
        if over:
            c.create_line(edge, 0, edge, H, fill="#d2ebfa", width=2)
            c.create_rectangle(0, 0, edge, H, outline="", fill="#a0cde6", stipple="gray12")
        else:
            c.create_text(12, 20, anchor="w", text=T("프리즘이 레이저 홀더에 있습니다 — 먼저 줄무늬 종이 위로 옮기세요", "the prism is in the laser holder — move it over the striped sheet first"), fill="#e8b45a")
        for s in STRIPES:
            X = s["x"] - off
            if s["kind"] == "white" and s["lab"] % 4 == 0:
                x, y = self.S_(X, SHEET_D / 2 - 7)
                if not over or x > edge:
                    c.create_text(x, y, text=str(s["lab"]), fill="#c4c8cc")
            if s.get("gap"):
                x, y = self.S_(X, -SHEET_D / 2 + 5)
                if not over or x > edge:
                    c.create_text(x, y, text="%.1f" % s["gap"], fill="#c4c8cc")

    def draw_side(self):
        c = self.cv
        W, H = c.winfo_width(), c.winfo_height()
        k = self.vmap()[0]
        c.create_rectangle(0, 0, W, H, fill="#2a3038", outline="")
        self.rect(-40, 0, 40, -3, fill="#3a3d42", outline="")
        self.rect(-28, 0.1, 2, 0, fill="#0e0f12", outline="")
        self.rect(3, 0.9, 15, 0, fill="#2a2c30", outline="")
        self.rect(8.4, 60, 9.6, 0.9, fill="#b9bec4", outline="")
        self.rect(16, 62, 19, 0, fill="#e8dcae", outline="")
        x0 = self.S_(16, 0)[0]
        for mm in range(0, 621):
            if k < 12 and mm % 5:
                continue
            if k < 5 and mm % 10:
                continue
            y = self.S_(0, mm / 10.0)[1]
            if y < -10 or y > H + 10:
                continue
            L = 1.2 if mm % 10 == 0 else (0.75 if mm % 5 == 0 else 0.45)
            c.create_line(x0, y, x0 + L * k, y, fill="#202020")
            if mm % 10 == 0 and (k > 6 or mm % 50 == 0):
                c.create_text(x0 + 1.4 * k, y, anchor="w", text=str(mm // 10), fill="#202020", font=("Segoe UI", 8))
        if S.mode != "look":
            c.create_text(12, 20, anchor="w", text=T("프리즘이 레이저 홀더에 있습니다 — 먼저 줄무늬 종이 위로 옮기세요", "the prism is in the laser holder — move it over the striped sheet first"), fill="#e8b45a")
            return
        h = S.h
        self.rect(7.6, h + 1.2, 10.4, h - 1.2, fill="#3a3c40", outline="")
        self.rect(-9.5, h + 0.5, 8, h + 0.1, fill="#9aa0a6", outline="")
        self.rect(-19, h + 0.06, -9, h, fill="#aad7f0", outline="#aad7f0")
        a, b = self.S_(-9, h), self.S_(16, h)
        c.create_line(a[0], a[1], b[0], b[1], fill="#aad7f0", dash=(4, 4))

    def _tick(self):
        try:
            self.cv.delete("all")
            {"bench": self.draw_bench, "screen": self.draw_screen, "look": self.draw_look, "side": self.draw_side}[self.view]()
            self.b_las.config(text=T("레이저: 켜짐", "Laser: ON") if S.laser else T("레이저: 꺼짐", "Laser: OFF"), bg=ACC if S.laser else PANEL2, fg="#1c2027" if S.laser else FG)
            self.b_pin.config(text=T("프리즘 시트: 빔 안", "Prism sheet: in the beam") if S.prism_in else T("프리즘 시트: 빔 밖", "Prism sheet: out of the beam"),
                              state="normal" if S.mode == "laser" else "disabled")
            self.b_ml.config(bg=ACC if S.mode == "laser" else PANEL2, fg="#1c2027" if S.mode == "laser" else FG)
            self.b_mk.config(bg=ACC if S.mode == "look" else PANEL2, fg="#1c2027" if S.mode == "look" else FG)
        except tk.TclError:
            return
        self.after(80, self._tick)


if __name__ == "__main__":
    App().mainloop()
