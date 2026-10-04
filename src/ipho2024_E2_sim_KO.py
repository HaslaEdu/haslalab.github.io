#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPhO 2024 (Isfahan, Iran) - Experimental Problem E2
"Diffraction from Phase Steps" (10 points) - virtual laboratory

The apparatus delivers nothing but what the real one delivers: the pattern
on the observation screen and the reading of the rotating protractor.  The
user counts the fringe shifts by eye.  Nothing is computed for the user: no
fringe indicator, no x = sqrt(n^2 - N^2 sin^2) - N cos, no theta^2, no u, w,
no fit, no thickness, no index, no score.  The graphs of A-2, B-3, C-3 and
D-4 are the user's work on paper; the only plot shown is the raw table
(m against the protractor reading).

Run:  python ipho2024_E2_sim_KO.py   (EN edition: ipho2024_E2_sim_EN.py)
Needs numpy and matplotlib (pip install numpy matplotlib).

--------------------------------------------------------------------------
PHYSICAL MODEL
  the pattern is computed, not replayed: the Fresnel field of a half plane
  carrying an extra phase phi,
        U(v) = e^{i phi} F(-inf..v) + F(v..+inf),   I = |U|^2,
  so it returns to its shape whenever phi advances by 2 pi;
  phi follows eq. (2) of the sheet with no small-angle approximation:
        phi = (2 pi h / lambda) ( sqrt(n^2 - N^2 sin^2 theta) - N cos theta )

CALIBRATION (official solution E2_S)
    A.4  h = 148.9 um          B.5  H = 1.061 mm
    C.5  N = 1.332             D.6  N = 1.337 / 1.332
  given: n(glass) = 1.51, N(air) = 1.00, lambda = 650 nm
  built-in truth  h = 148.9 um, N(liquid) = 1.3320,
                  H = 1.061 mm / 1.0234 = 1.0367 mm, so that the prescribed
                  small-angle expansion of B-2 (biased by 2.3 % over 0-20 deg)
                  returns the official 1.061 mm
  The protractor is read to 0.25 deg with a human judgement error; the
  slides and the liquid are redrawn (+-0.2 %) at every new session.
--------------------------------------------------------------------------
"""

import csv
import math

import numpy as np

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


LANG = "KO"          # the EN edition differs only in this line
TR = {
    "IPhO 2024 E2 - Diffraction from Phase Steps : Virtual Lab":
        "IPhO 2024 E2 - 위상 계단에 의한 회절 : 가상 실험실",
    "Setup": "장치",
    "holder on the protractor": "각도기 위의 홀더",
    "none": "없음",
    "S1 (thin slide)": "S1 (얇은 슬라이드)",
    "S2 (thick slide)": "S2 (두꺼운 슬라이드)",
    "liquid container": "액체 용기",
    "not in place": "치움",
    "in place, filled with the pink liquid": "제자리, 분홍 액체를 채움",
    "laser board": "레이저 보드",
    "laser on": "레이저 켜기",
    "current knob": "전류 손잡이",
    "Rotating protractor": "회전 각도기",
    "slow turn": "천천히 돌리기",
    "stop": "멈춤",
    "back to 0°": "0°로",
    "Your table": "기록표",
    "fringe shift seen: record": "줄무늬 이동을 봄: 기록",
    "undo": "되돌리기",
    "clear": "지우기",
    "no.": "번호",
    "θm (deg)": "θm (도)",
    "Export CSV": "CSV 내보내기",
    "New session": "새 장치",
    "observation screen": "관찰 스크린",
    "your snapshot": "내가 찍어 둔 모습",
    "snapshot of the screen": "스크린 찍어 두기",
    "raw table: m against the protractor reading": "기록표 그대로: m 대 각도기 눈금",
    "protractor reading (deg)": "각도기 눈금 (도)",
    "Save PNG": "PNG 저장",
    "laser off": "레이저 꺼짐",
    "no slide in the beam": "빔 앞에 슬라이드가 없음",
    "configuration": "구성",
    "points": "개",
    "Clear": "지우기",
    "Erase the table of this configuration?": "이 구성의 기록표를 지울까요?",
    "Restart with new slides and a new bottle of liquid?": "새 슬라이드와 새 액체로 다시 시작할까요?",
    "\n=== new slides / new bottle of liquid ===\n": "\n=== 새 슬라이드 / 새 액체 ===\n",
    "Rotate the protractor slowly and count how many times the pattern comes "
    "back to the shape it had at 0°.  Press RECORD at each return.\n":
        "각도기를 천천히 돌리며 무늬가 0° 때의 모양으로 몇 번 돌아오는지 세세요. "
        "돌아올 때마다 기록을 누릅니다.\n",
    "Put a holder on the protractor first.\n": "먼저 각도기에 홀더를 올리세요.\n",
    "Turn the laser on first.\n": "먼저 레이저를 켜세요.\n",
    "data exported": "데이터를 내보냈습니다",
    "graph saved": "그래프를 저장했습니다",
    "S1 in air": "S1, 공기 중",
    "S2 in air": "S2, 공기 중",
    "S2 in the liquid": "S2, 액체 속",
    "S1 in the liquid": "S1, 액체 속",
}


def T(s):
    return TR.get(s, s) if LANG != "EN" else s


def _setup_hangul_font(root):
    """Point every named Tk font, and matplotlib, at a family that has Hangul."""
    import tkinter.font as _tkfont
    want = ("Malgun Gothic", "AppleGothic", "Apple SD Gothic Neo",
            "NanumGothic", "NanumBarunGothic", "Noto Sans CJK KR",
            "Noto Sans KR", "UnDotum", "Gulim", "Batang")
    have = set(_tkfont.families(root))
    fam = next((f for f in want if f in have), None)
    if not fam:
        return
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont",
                 "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont",
                 "TkIconFont", "TkTooltipFont"):
        try:
            _tkfont.nametofont(name, root).configure(family=fam)
        except Exception:
            pass
    try:
        matplotlib.rcParams["font.family"] = [fam, "DejaVu Sans"]
        matplotlib.rcParams["axes.unicode_minus"] = False
    except Exception:
        pass


LAMBDA = 650e-9          # m
N_GLASS = 1.51
N_AIR = 1.00
H_THIN = 148.9e-6        # m   S1
H_THICK = 1.061e-3 / 1.0234   # m   S2
N_LIQUID = 1.3320
THETA_MAX = 80.0         # deg, the part of the scale used here

# configuration key -> label  (S1 or S2, in air or in the liquid)
CONFIGS = {("S1", False): "S1 in air", ("S2", False): "S2 in air",
           ("S2", True): "S2 in the liquid", ("S1", True): "S1 in the liquid"}


def _fresnel_tables(vmax=9.0, npts=24001):
    """Cumulative Fresnel integrals C(v), S(v) on a fine grid."""
    v = np.linspace(-vmax, vmax, npts)
    dv = v[1] - v[0]
    c = np.cos(0.5 * math.pi * v * v)
    s = np.sin(0.5 * math.pi * v * v)
    C = np.concatenate([[0.0], np.cumsum(0.5 * (c[1:] + c[:-1]) * dv)])
    S = np.concatenate([[0.0], np.cumsum(0.5 * (s[1:] + s[:-1]) * dv)])
    C -= C[0] + 0.5
    S -= S[0] + 0.5
    return v, C, S


_VG, _CG, _SG = _fresnel_tables()


def phase_step_intensity(phi, v):
    """|U|^2 for a half plane carrying an extra phase phi, at reduced coord v."""
    C = np.interp(v, _VG, _CG)
    S = np.interp(v, _VG, _SG)
    F1 = (C + 0.5) + 1j * (S + 0.5)
    F2 = (0.5 - C) + 1j * (0.5 - S)
    U = np.exp(1j * phi) * F1 + F2
    return (np.abs(U) ** 2) / 2.0


def phase(theta_rad, thick, N):
    return (2 * math.pi * thick / LAMBDA) * (
        math.sqrt(N_GLASS ** 2 - N ** 2 * math.sin(theta_rad) ** 2)
        - N * math.cos(theta_rad))


# ===========================================================================
#  GUI
# ===========================================================================
class App(tk.Tk):

    NV = 420
    NX = 220
    VMAX = 6.5

    def __init__(self):
        super().__init__()
        _setup_hangul_font(self)
        self.title(T("IPhO 2024 E2 - Diffraction from Phase Steps : Virtual Lab"))
        self.geometry("1400x880")
        self.minsize(1150, 760)

        self.rng = np.random.default_rng()
        self._new_hardware()

        self.holder = tk.StringVar(value="none")
        self.liquid = tk.BooleanVar(value=False)
        self.laser = tk.BooleanVar(value=False)
        self.theta = tk.DoubleVar(value=0.0)
        self.current = tk.DoubleVar(value=15.0)
        self.scanning = False
        self.snapshot = None

        self.data = {k: [] for k in CONFIGS}
        self.mcount = {k: 0 for k in CONFIGS}

        self._v = np.linspace(-self.VMAX, self.VMAX, self.NV)
        self._env_x = np.exp(-(np.linspace(-1, 1, self.NX) ** 2) / 0.42)
        self._env_v = np.exp(-(self._v / (self.VMAX * 0.78)) ** 2)

        self._build_ui()
        self._changed()
        self.after(60, self._tick)

    def _new_hardware(self):
        self.h_thin = H_THIN * (1 + self.rng.normal(0, 0.002))
        self.h_thick = H_THICK * (1 + self.rng.normal(0, 0.002))
        self.n_liquid = N_LIQUID * (1 + self.rng.normal(0, 0.0015))

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = ttk.Frame(self, padding=8)
        root.pack(fill="both", expand=True)
        left = ttk.Frame(root)
        left.pack(side="left", fill="y", padx=(0, 8))
        right = ttk.Frame(root)
        right.pack(side="left", fill="both", expand=True)

        box = ttk.LabelFrame(left, text=T("Setup"), padding=6)
        box.pack(fill="x")
        ttk.Label(box, text=T("holder on the protractor")).pack(anchor="w")
        for val, lab in (("none", "none"), ("S1", "S1 (thin slide)"), ("S2", "S2 (thick slide)")):
            ttk.Radiobutton(box, text=T(lab), value=val, variable=self.holder,
                            command=self._changed).pack(anchor="w", padx=10)
        ttk.Label(box, text=T("liquid container")).pack(anchor="w", pady=(4, 0))
        ttk.Radiobutton(box, text=T("not in place"), value=False, variable=self.liquid,
                        command=self._changed).pack(anchor="w", padx=10)
        ttk.Radiobutton(box, text=T("in place, filled with the pink liquid"), value=True,
                        variable=self.liquid, command=self._changed).pack(anchor="w", padx=10)
        ttk.Separator(box).pack(fill="x", pady=4)
        ttk.Label(box, text=T("laser board")).pack(anchor="w")
        ttk.Checkbutton(box, text=T("laser on"), variable=self.laser,
                        command=self._redraw_pattern).pack(anchor="w", padx=10)
        row = ttk.Frame(box)
        row.pack(fill="x", padx=10)
        ttk.Label(row, text=T("current knob")).pack(side="left")
        ttk.Scale(row, from_=4, to=25, variable=self.current,
                  command=lambda e: self._redraw_pattern()).pack(side="left", fill="x", expand=True)

        box = ttk.LabelFrame(left, text=T("Rotating protractor"), padding=6)
        box.pack(fill="x", pady=(8, 0))
        self.lbl_theta = ttk.Label(box, text="", font=("Consolas", 20, "bold"))
        self.lbl_theta.pack()
        self.sld = ttk.Scale(box, from_=0, to=THETA_MAX, variable=self.theta,
                             command=lambda e: self._redraw_pattern())
        self.sld.pack(fill="x", pady=4)
        row = ttk.Frame(box)
        row.pack()
        for txt, d in (("◀◀ -1°", -1.0), ("◀ -0.25°", -0.25),
                       ("+0.25° ▶", 0.25), ("+1° ▶▶", 1.0)):
            ttk.Button(row, text=txt, width=9,
                       command=lambda d=d: self._nudge(d)).pack(side="left", padx=1)
        row2 = ttk.Frame(box)
        row2.pack(pady=4)
        self.btn_scan = ttk.Button(row2, text=T("slow turn"), width=14, command=self._toggle_scan)
        self.btn_scan.pack(side="left", padx=2)
        ttk.Button(row2, text=T("back to 0°"), width=11,
                   command=lambda: (self.theta.set(0.0), self._redraw_pattern())
                   ).pack(side="left", padx=2)

        box = ttk.LabelFrame(left, text=T("Your table"), padding=6)
        box.pack(fill="both", expand=True, pady=(8, 0))
        self.lbl_cfg = ttk.Label(box, text="", font=("Consolas", 10))
        self.lbl_cfg.pack(anchor="w")
        r = ttk.Frame(box)
        r.pack(fill="x", pady=3)
        ttk.Button(r, text=T("fringe shift seen: record"), command=self._record).pack(side="left", padx=2)
        ttk.Button(r, text=T("undo"), width=9, command=self._undo).pack(side="left")
        ttk.Button(r, text=T("clear"), width=8, command=self._clear_cfg).pack(side="left", padx=2)
        cols = ("i", "m", "th")
        self.tree = ttk.Treeview(box, columns=cols, show="headings", height=14)
        for c, h, w in zip(cols, (T("no."), "m", T("θm (deg)")), (50, 50, 90)):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, pady=(6, 0))
        bar = ttk.Frame(left)
        bar.pack(fill="x", pady=4)
        ttk.Button(bar, text=T("Export CSV"), command=self._export).pack(side="left")
        ttk.Button(bar, text=T("New session"), command=self._new_session).pack(side="right")

        top = ttk.Frame(right)
        top.pack(fill="x")
        ttk.Button(top, text=T("snapshot of the screen"), command=self._snap).pack(side="left")
        self.fig1 = Figure(figsize=(7.4, 3.6), dpi=100)
        self.ax_now = self.fig1.add_subplot(121)
        self.ax_snap = self.fig1.add_subplot(122)
        self.cv1 = FigureCanvasTkAgg(self.fig1, master=right)
        self.cv1.get_tk_widget().pack(fill="x")

        top = ttk.Frame(right)
        top.pack(fill="x", pady=(6, 0))
        ttk.Label(top, text=T("raw table: m against the protractor reading")).pack(side="left")
        ttk.Button(top, text=T("Save PNG"), command=self._save_png).pack(side="right")
        self.fig2 = Figure(figsize=(7.4, 3.0), dpi=100)
        self.ax2 = self.fig2.add_subplot(111)
        self.cv2 = FigureCanvasTkAgg(self.fig2, master=right)
        self.cv2.get_tk_widget().pack(fill="x", pady=4)

        self.log = tk.Text(right, height=8, wrap="word", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)
        self._say(T("Rotate the protractor slowly and count how many times the pattern comes "
                    "back to the shape it had at 0°.  Press RECORD at each return.\n"))

    # ------------------------------------------------------------------
    def _say(self, s):
        self.log.insert("end", s)
        self.log.see("end")

    def _key(self):
        h = self.holder.get()
        return None if h == "none" else (h, bool(self.liquid.get()))

    def _cfg(self):
        k = self._key()
        if k is None:
            return None
        thick = self.h_thin if k[0] == "S1" else self.h_thick
        N = self.n_liquid if k[1] else N_AIR
        return thick, N

    def _reading(self):
        """The protractor scale, read to a quarter of a degree."""
        return round(self.theta.get() * 4) / 4.0

    def _changed(self):
        self.snapshot = None
        self._refresh_table()
        self._redraw_pattern()
        self._redraw_graph()

    def _nudge(self, d):
        self.theta.set(min(THETA_MAX, max(0.0, self.theta.get() + d)))
        self._redraw_pattern()

    def _toggle_scan(self):
        self.scanning = not self.scanning
        self.btn_scan.configure(text=T("stop") if self.scanning else T("slow turn"))

    def _tick(self):
        if self.scanning:
            t = self.theta.get() + 0.05
            if t >= THETA_MAX:
                t, self.scanning = THETA_MAX, False
                self.btn_scan.configure(text=T("slow turn"))
            self.theta.set(t)
            self._redraw_pattern()
        self.after(60, self._tick)

    # ------------------------------------------------------------------
    def _image(self, phi):
        if phi is None:
            I = np.full_like(self._v, 1.0)
        else:
            I = phase_step_intensity(phi, self._v)
        amp = min(1.0, self.current.get() / 15.0)
        I = I * self._env_v * amp
        M = I[:, None] * self._env_x[None, :]
        M = np.clip(M / 1.35, 0, 1)
        rgb = np.zeros(M.shape + (3,))
        rgb[..., 0] = np.clip(M * 1.35, 0, 1)
        rgb[..., 1] = np.clip(M ** 3.2 * 0.85, 0, 1)
        rgb[..., 2] = np.clip(M ** 1.9 * 0.80, 0, 1)
        return rgb

    def _current_image(self):
        if not self.laser.get():
            return np.zeros((self.NV, self.NX, 3)), T("laser off")
        c = self._cfg()
        if c is None:
            return self._image(None), T("no slide in the beam")
        phi = phase(math.radians(self.theta.get()), *c)
        return self._image(phi), ""

    def _redraw_pattern(self):
        self.lbl_theta.configure(text=f"{self._reading():6.2f}°")
        k = self._key()
        if k is None:
            self.lbl_cfg.configure(text="")
        else:
            self.lbl_cfg.configure(text=f"{T('configuration')}: {T(CONFIGS[k])}   "
                                        f"m = {self.mcount[k]}")
        img, note = self._current_image()
        self.ax_now.clear()
        self.ax_now.imshow(img, aspect="auto", origin="lower")
        self.ax_now.set_title(T("observation screen") + (f"  ({note})" if note else ""), fontsize=9)
        self.ax_now.set_xticks([]), self.ax_now.set_yticks([])
        self.ax_snap.clear()
        if self.snapshot is not None:
            self.ax_snap.imshow(self.snapshot[0], aspect="auto", origin="lower")
            self.ax_snap.set_title(f"{T('your snapshot')}  ({self.snapshot[1]:.2f}°)", fontsize=9)
        else:
            self.ax_snap.set_facecolor("#111")
            self.ax_snap.set_title(T("your snapshot"), fontsize=9)
        self.ax_snap.set_xticks([]), self.ax_snap.set_yticks([])
        self.fig1.tight_layout()
        self.cv1.draw_idle()

    def _snap(self):
        img, _ = self._current_image()
        self.snapshot = (img, self._reading())
        self._redraw_pattern()

    # ------------------------------------------------------------------
    def _record(self):
        k = self._key()
        if k is None:
            self._say(T("Put a holder on the protractor first.\n"))
            return
        if not self.laser.get():
            self._say(T("Turn the laser on first.\n"))
            return
        self.mcount[k] += 1
        th = self.theta.get() + self.rng.normal(0, 0.09)   # judgement error of the reading
        th = round(th * 4) / 4.0
        self.data[k].append((self.mcount[k], th))
        self._refresh_table()
        self._redraw_pattern()
        self._redraw_graph()

    def _undo(self):
        k = self._key()
        if k and self.data[k]:
            self.data[k].pop()
            self.mcount[k] = self.data[k][-1][0] if self.data[k] else 0
            self._refresh_table()
            self._redraw_pattern()
            self._redraw_graph()

    def _clear_cfg(self):
        k = self._key()
        if k and self.data[k] and messagebox.askyesno(T("Clear"), T("Erase the table of this configuration?")):
            self.data[k].clear()
            self.mcount[k] = 0
            self._refresh_table()
            self._redraw_pattern()
            self._redraw_graph()

    def _refresh_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        k = self._key()
        if k is None:
            return
        for i, (m, th) in enumerate(self.data[k], 1):
            self.tree.insert("", "end", values=(i, m, f"{th:.2f}"))
        kids = self.tree.get_children()
        if kids:
            self.tree.see(kids[-1])

    def _new_session(self):
        if not messagebox.askyesno(T("New session"), T("Restart with new slides and a new bottle of liquid?")):
            return
        self._new_hardware()
        for k in CONFIGS:
            self.data[k].clear()
            self.mcount[k] = 0
        self.theta.set(0.0)
        self._changed()
        self._say(T("\n=== new slides / new bottle of liquid ===\n"))

    def _redraw_graph(self):
        ax = self.ax2
        ax.clear()
        ax.grid(alpha=0.3)
        k = self._key()
        d = self.data[k] if k else []
        if d:
            ax.plot([t for _, t in d], [m for m, _ in d], "o", ms=4, color="#1f77b4")
        ax.set_xlabel(T("protractor reading (deg)"))
        ax.set_ylabel("m")
        if k:
            ax.set_title(f"{T(CONFIGS[k])}   ({len(d)} {T('points')})", fontsize=10)
        self.fig2.tight_layout()
        self.cv2.draw_idle()

    def _save_png(self):
        p = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if p:
            self.fig2.savefig(p, dpi=150)
            self._say(f"{T('graph saved')} -> {p}\n")

    def _export(self):
        p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not p:
            return
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["holder", "liquid", "no", "m", "theta_deg"])
            for (h, liq), rows in self.data.items():
                for i, (m, t) in enumerate(rows, 1):
                    w.writerow([h, int(liq), i, m, f"{t:.2f}"])
        self._say(f"{T('data exported')} -> {p}\n")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
