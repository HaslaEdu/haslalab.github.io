#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISPhO 2024 Theoretical Problem 1 — "Thermal oxidation"
A.py, B1.py, B2.py, gen_data, B.py, B7.py and B8.py as the tabs of one Tk
window, laid out like the organisers' FBG Writer of ISPhO 2026.

The organisers' programs were never published; these are rebuilt from the
input and output formats on the problem sheet and the results of the
solution.  Every label on the window stays in English, as the sheet quotes
them; the dialogs and the output line follow LANG.

Ellipsometry of a film d on a substrate, the sheet's three-layer formula

    r = (A + B e^{2 i k2x d}) / (AB + e^{2 i k2x d}),
    s: A = (k2x + k3x)/(k2x - k3x),  B = (k1x + k2x)/(k1x - k2x)
    p: the same with kappa_ix = k_ix / eps_i
    tan Psi e^{i Delta} = r_p / r_s

Part A without dispersion (eps_Si = 17.2 - 0.430i, eps_SiO2 = 2.13); part B
with the dispersion of Si (Green 2008) and SiO2 (Malitson).
The furnace grows the oxide by Deal-Grove plus a fast initial term that dies
away within a few nanometres, which is why the model is fitted from 25 nm.
Every hidden constant (the two samples, B, B/A, their activation energies)
is drawn afresh each time the window opens; theta_opt, Phi, d, B, B/A, dEa
and dEb are left for the user to find.

    python ispho2024_T1_oxide_sim_KO.py          (needs numpy and matplotlib)
"""

import csv
import random
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import numpy as np
from matplotlib import rcParams
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

LANG = "KO"          # the EN edition differs only in this line

MSG = {
 "EN": {
  "row": ("Input error", "Cannot read the line: {}\nEach line needs a name and numerical values."),
  "theta": ("Out of bounds", "θ1 must be between 20° and 80° ({})."),
  "d": ("Out of bounds", "d must be between 0 and 250 nm ({})."),
  "empty": ("Input error", "A_in.txt has no data lines."),
  "num": ("Input error", "Please ensure you have entered a numerical value. Also check decimal delimiter (0.0/0,0)."),
  "phi": ("Out of bounds", "Φ must be between 20° and 80°."),
  "brow": ("Input error", "B_in.txt needs one line: Name  Phi  T  t"),
  "T": ("Out of bounds", "The furnace works between 800 °C and 1200 °C."),
  "tmax": ("Out of bounds", "t must be between 0 and 200 min."),
  "noexp": ("FileNotFoundError", "No gen_data result named “{}”. Run gen_data first."),
  "noproc": ("FileNotFoundError", "No res for “{}”. Run B.py first."),
  "thin": ("B7.py", "Final layer is too thin to approximate"),
  "pos": ("Input error", "B and B/A must be positive: {}"),
  "b8need": ("Input error", "B8_in.txt needs at least two lines."),
  "nodata": ("Nothing to save", "Calculate and plot first."),
 },
 "KO": {
  "row": ("입력 오류", "이 줄을 읽을 수 없습니다: {}\n줄마다 이름과 숫자들이 있어야 합니다."),
  "theta": ("범위 밖", "θ1 은 20° 와 80° 사이여야 합니다 ({})."),
  "d": ("범위 밖", "d 는 0 과 250 nm 사이여야 합니다 ({})."),
  "empty": ("입력 오류", "A_in.txt 에 데이터 줄이 없습니다."),
  "num": ("입력 오류", "숫자를 입력했는지 확인하세요. 소수점 기호(0.0/0,0)도 확인하세요."),
  "phi": ("범위 밖", "Φ 는 20° 와 80° 사이여야 합니다."),
  "brow": ("입력 오류", "B_in.txt 에는 한 줄이 필요합니다: Name  Phi  T  t"),
  "T": ("범위 밖", "노의 온도는 800 °C 와 1200 °C 사이입니다."),
  "tmax": ("범위 밖", "t 는 0 과 200 min 사이여야 합니다."),
  "noexp": ("FileNotFoundError", "“{}” 이라는 gen_data 결과가 없습니다. 먼저 gen_data 를 실행하세요."),
  "noproc": ("FileNotFoundError", "“{}” 의 res 가 없습니다. 먼저 B.py 를 실행하세요."),
  "thin": ("B7.py", "Final layer is too thin to approximate"),
  "pos": ("입력 오류", "B 와 B/A 는 양수여야 합니다: {}"),
  "b8need": ("입력 오류", "B8_in.txt 에 두 줄 이상 필요합니다."),
  "nodata": ("저장할 데이터 없음", "먼저 계산하고 그리세요."),
 }}[LANG]

SAY = {
 "EN": dict(idle="Set the input and run.", A="A.py: {} curves", B12="{}.py: error = {} deg",
            gen="gen_data {}: measurement {} / {}", genDone="gen_data {}: {} measurements kept.", proc="B.py: {} / {}",
            procDone="B.py {}: d(t) saved to res.", b7="B7.py {}: fitted to {} points with d ≥ 25 nm.",
            added="Appended a line to B8_in.txt.", B8="B8.py: {} temperatures", saved="Saved as {}."),
 "KO": dict(idle="입력을 정하고 실행하세요.", A="A.py: 곡선 {} 개", B12="{}.py: error = {} deg",
            gen="gen_data {}: 측정 {} / {}", genDone="gen_data {}: 측정 {} 개를 남겼습니다.", proc="B.py: {} / {}",
            procDone="B.py {}: d(t) 를 res 에 저장했습니다.", b7="B7.py {}: d ≥ 25 nm 인 점 {} 개로 맞췄습니다.",
            added="B8_in.txt 에 한 줄 추가했습니다.", B8="B8.py: 온도 {} 개", saved="{} 로 저장했습니다."),
}[LANG]


def warn(key, *a):
    t, m = MSG[key]
    messagebox.showwarning(t, m.format(*a))


def error(key, *a):
    t, m = MSG[key]
    messagebox.showerror(t, m.format(*a))


LAM = np.arange(400, 801, 4.0)
SI = np.array([[400, 5.570, 0.387], [425, 5.000, 0.230], [450, 4.674, 0.135], [475, 4.460, 0.093], [500, 4.298, 0.073],
               [525, 4.180, 0.056], [550, 4.077, 0.041], [575, 4.000, 0.031], [600, 3.939, 0.025], [650, 3.844, 0.016],
               [700, 3.776, 0.0108], [750, 3.728, 0.0076], [800, 3.688, 0.0055]])
N_SI = np.interp(LAM, SI[:, 0], SI[:, 1]) - 1j * np.interp(LAM, SI[:, 0], SI[:, 2])
EPS_SI = N_SI ** 2
X2 = (LAM / 1000) ** 2
EPS_OX = 1 + 0.6961663 * X2 / (X2 - 0.0684043 ** 2) + 0.4079426 * X2 / (X2 - 0.1162414 ** 2) + 0.8974794 * X2 / (X2 - 9.896161 ** 2)
SIG_P, SIG_D = 0.15, 0.80
KB = 8.617e-5


def psi_delta(th_deg, d, disp):
    """Psi, Delta (degrees) over LAM for angle th_deg and film thickness d (nm)."""
    th = np.radians(th_deg)
    e1 = 1.0 + 0j
    e2 = EPS_OX + 0j if disp else 2.13 + 0j
    e3 = EPS_SI if disp else (17.2 - 0.43j) * np.ones_like(LAM)
    w = 2 * np.pi / LAM
    s2 = np.sin(th) ** 2
    k1 = np.sqrt(e1) * np.cos(th) * w
    k2 = np.sqrt(e2 - e1 * s2) * w
    k3 = np.sqrt(e3 - e1 * s2) * w
    E = np.exp(2j * k2 * d)

    def r(a1, a2, a3):
        A = (a2 + a3) / (a2 - a3)
        B = (a1 + a2) / (a1 - a2)
        return (A + B * E) / (A * B + E)
    q = r(k1 / e1, k2 / e2, k3 / e3) / r(k1, k2, k3)
    return np.degrees(np.arctan(np.abs(q))), np.degrees(np.angle(-q))


def wrap(x):
    return (x + 180) % 360 - 180


def U(a, b):
    return random.uniform(a, b)


class Truth:
    def __init__(self):
        self.b1 = (U(66, 75), U(52, 85))
        self.b2 = (U(52, 62), U(205, 245))
        self.B0, self.Ea = U(150, 172), U(1.30, 1.45)
        self.BA0, self.Eb = U(0.95, 1.12), U(1.90, 2.10)
        self.K0, self.Lm, self.dn = U(3, 4), U(5, 6), U(1.0, 1.8)

    def B(self, T):
        return self.B0 * np.exp(-self.Ea / KB * (1 / (T + 273.15) - 1 / 1273.15))

    def BA(self, T):
        return self.BA0 * np.exp(-self.Eb / KB * (1 / (T + 273.15) - 1 / 1273.15))

    def grow(self, T, dt, d):
        B, A, K = self.B(T), self.B(T) / self.BA(T), self.K0 * self.BA(T) / self.BA0
        f = lambda x: B / (2 * x + A) + K * np.exp(-x / self.Lm)
        k1 = f(d); k2 = f(d + dt / 2 * k1); k3 = f(d + dt / 2 * k2); k4 = f(d + dt * k3)
        return d + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)


TR = Truth()


def noisy(PD):
    P, D = PD
    return P + np.random.normal(0, SIG_P, P.size), wrap(D + np.random.normal(0, SIG_D, D.size))


DATA = {"B1": noisy(psi_delta(*TR.b1, True)), "B2": noisy(psi_delta(*TR.b2, True))}


def fit_d(phi, data):
    """B.py: the thickness that best explains one spectrum, and its statistical error."""
    def chi(d):
        P, D = psi_delta(phi, d, True)
        return np.sum(((data[0] - P) / SIG_P) ** 2 + (wrap(data[1] - D) / SIG_D) ** 2)
    grid = np.arange(0, 301, 1.0)
    best = grid[np.argmin([chi(d) for d in grid])]
    a, b = max(0.0, best - 1), best + 1
    for _ in range(40):
        m1, m2 = a + (b - a) * 0.382, a + (b - a) * 0.618
        if chi(m1) < chi(m2):
            b = m2
        else:
            a = m1
    dm, h = (a + b) / 2, 0.05
    c = (chi(dm + h) - 2 * chi(dm) + chi(max(0, dm - h))) / h ** 2
    red = chi(dm) / (2 * LAM.size - 1)
    return dm, np.sqrt(2 * max(red, 1) / max(c, 1e-9))


def rows_of(text):
    """The input files: header lines (Name ..., T ...) are skipped, fields split on white space."""
    return [p for p in (ln.split() for ln in text.splitlines()) if p and p[0].lower() not in ("name", "t")]


class OxidationApp(tk.Tk):
    def __init__(self):
        super().__init__()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        if screen_w >= 2560:
            base_font_size = 14
        elif screen_w >= 1920:
            base_font_size = 11
        else:
            base_font_size = 9
        rcParams.update({'font.size': base_font_size, 'axes.labelsize': base_font_size + 1,
                         'axes.titlesize': base_font_size + 2, 'xtick.labelsize': base_font_size,
                         'ytick.labelsize': base_font_size, 'legend.fontsize': base_font_size})
        rcParams.update({'axes.grid': True, 'axes.grid.which': 'both',
                         'xtick.minor.visible': True, 'ytick.minor.visible': True})
        width = max(1000, min(int(screen_w * 0.8), 1600))
        height = max(650, min(int(screen_h * 0.8), 900))
        self.geometry(f'{width}x{height}+{int((screen_w-width)/2)}+{int((screen_h-height)/2)}')
        self.title('Thermal Oxidation')
        self.exps, self.cur, self.gen, self.b7 = {}, None, None, None
        self.res_a = self.res_b12 = self.res_b8 = None
        self.setup_bottom_panel()
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        for key, label in (('a', 'Part A'), ('b12', 'Part B.1–B.2'), ('b3', 'Part B.3–B.7'), ('b8', 'Part B.8')):
            fr = ttk.Frame(self.notebook)
            setattr(self, 'tab_' + key, fr)
            self.notebook.add(fr, text=label)
            getattr(self, 'setup_tab_' + key)()
        self.notebook.bind('<<NotebookTabChanged>>', self.on_tab_change)
        self.say(SAY['idle'])

    # ---------------- frame ----------------
    def setup_bottom_panel(self):
        f = ttk.LabelFrame(self, text='Output', padding=10)
        f.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        self.lbl_out = ttk.Label(f, text=' ')
        self.lbl_out.pack(side=tk.LEFT, padx=(10, 2))
        ttk.Button(f, text='Save data as CSV', command=self.save_csv).pack(side=tk.RIGHT, padx=10)

    def say(self, s):
        self.lbl_out.config(text=s)

    def on_tab_change(self, event):
        i = self.notebook.index(self.notebook.select())
        if i == 1:
            self.plot_part_b12(False)
        elif i == 2:
            self.draw_b3()

    def _left(self, tab):
        col = ttk.Frame(tab)
        col.pack(side=tk.LEFT, fill=tk.Y)
        return col

    def _frame(self, col, title):
        f = ttk.LabelFrame(col, text=title, padding=15)
        f.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        return f

    def _text(self, f, value, rows):
        t = tk.Text(f, height=rows, width=34, font=('Consolas', 10), wrap=tk.NONE, tabs=('1.6c',))
        t.insert('1.0', value)
        t.pack(fill=tk.X)
        return t

    def _plot(self, tab, key, n):
        pf = ttk.Frame(tab)
        pf.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)
        fig = Figure(figsize=(6, 4), dpi=100)
        axes = [fig.add_subplot(n, 1, i + 1) for i in range(n)]
        cv = FigureCanvasTkAgg(fig, master=pf); cv.draw()
        tf = ttk.Frame(pf); tf.pack(side=tk.BOTTOM, fill=tk.X)
        tb = NavigationToolbar2Tk(cv, tf); tb.update()
        cv.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        setattr(self, 'fig_' + key, fig); setattr(self, 'axes_' + key, axes)
        setattr(self, 'canvas_' + key, cv); setattr(self, 'toolbar_' + key, tb)

    def _show(self, key):
        fig = getattr(self, 'fig_' + key)
        for ax in getattr(self, 'axes_' + key):
            ax.grid(True, linestyle='-', alpha=0.5)
            ax.grid(True, linestyle='--', which='minor', alpha=0.3)
            if ax.get_legend_handles_labels()[0]:
                ax.legend(loc='best')
        fig.tight_layout()
        getattr(self, 'canvas_' + key).draw(); getattr(self, 'toolbar_' + key).update()

    # ---------------- Part A — A.py ----------------
    def setup_tab_a(self):
        col = self._left(self.tab_a)
        f = self._frame(col, ' A_in.txt ')
        ttk.Label(f, text='Name    θ1 (°)    d (nm)').pack(anchor=tk.W)
        self.ain_a = self._text(f, 'Name\tθ1\td\nex1\t50\t40\nex2\t30\t100\n', 9)
        ttk.Button(f, text='Calculate and plot', command=self.plot_part_a).pack(fill=tk.X, pady=(12, 0))
        g = self._frame(col, ' Constants ')
        ttk.Label(g, text='ε(air) = 1.00\nε(Si) = 17.2 − 0.430i\nε(SiO2) = 2.13\n20° ≤ θ1 ≤ 80°,  0 ≤ d ≤ 250 nm',
                  justify=tk.LEFT).pack(anchor=tk.W)
        self._plot(self.tab_a, 'a', 2)
        self.plot_part_a()

    def plot_part_a(self):
        out = []
        for r in rows_of(self.ain_a.get('1.0', tk.END)):
            try:
                if len(r) < 3:
                    raise ValueError
                th, d = float(r[1]), float(r[2])
            except ValueError:
                error('row', ' '.join(r)); return
            if not 20 <= th <= 80:
                warn('theta', r[0]); return
            if not 0 <= d <= 250:
                warn('d', r[0]); return
            out.append((r[0], th, d, psi_delta(th, d, False)))
        if not out:
            warn('empty'); return
        self.res_a = out
        a1, a2 = self.axes_a
        a1.clear(); a2.clear()
        for name, th, d, (P, D) in out:
            lab = f'{name}: θ1 = {th:g}°, d = {d:g} nm'
            a1.plot(LAM, P, label=lab); a2.plot(LAM, D, label=lab)
        a1.set_ylabel('Ψ, deg'); a2.set_ylabel('Δ, deg'); a2.set_xlabel('λ, nm')
        a1.legend(loc='best')
        self._show_no_legend2('a')
        self.say(SAY['A'].format(len(out)))

    def _show_no_legend2(self, key):
        """Part A keeps the legend on the upper Axes only."""
        fig = getattr(self, 'fig_' + key)
        for ax in getattr(self, 'axes_' + key):
            ax.grid(True, linestyle='-', alpha=0.5)
            ax.grid(True, linestyle='--', which='minor', alpha=0.3)
        fig.tight_layout()
        getattr(self, 'canvas_' + key).draw(); getattr(self, 'toolbar_' + key).update()

    # ---------------- Part B.1–B.2 — B1.py, B2.py ----------------
    def setup_tab_b12(self):
        col = self._left(self.tab_b12)
        f = self._frame(col, ' Sample ')
        self.samp = tk.StringVar(value='B1')
        for k in ('B1', 'B2'):
            ttk.Radiobutton(f, text=k + '.txt', value=k, variable=self.samp,
                            command=lambda: self.plot_part_b12(False)).pack(side=tk.LEFT, padx=(0, 18))
        g = self._frame(col, ' Parameters ')
        ttk.Label(g, text='Φ (°):').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.entry_phi = ttk.Entry(g, width=12); self.entry_phi.insert(0, '60.0'); self.entry_phi.grid(row=0, column=1, pady=5, padx=5)
        ttk.Label(g, text='d (nm):').grid(row=1, column=0, sticky=tk.W, pady=5)
        self.entry_d = ttk.Entry(g, width=12); self.entry_d.insert(0, '50.0'); self.entry_d.grid(row=1, column=1, pady=5, padx=5)
        ttk.Button(g, text='Calculate and plot', command=lambda: self.plot_part_b12(True)).grid(
            row=2, column=0, columnspan=2, pady=20, sticky=tk.EW)
        self.lbl_err = ttk.Label(g, text='error = — deg', font=('Arial', 9, 'bold'))
        self.lbl_err.grid(row=3, column=0, columnspan=2, sticky=tk.W)
        for e in (self.entry_phi, self.entry_d):
            e.bind('<Return>', lambda ev: self.plot_part_b12(True))
        self._plot(self.tab_b12, 'b12', 2)

    def plot_part_b12(self, fit_too):
        smp = self.samp.get(); dat = DATA[smp]
        a1, a2 = self.axes_b12
        if fit_too:
            try:
                phi, d = float(self.entry_phi.get()), float(self.entry_d.get())
            except ValueError:
                error('num'); return
            if not 20 <= phi <= 80:
                warn('phi'); return
            if not 0 <= d <= 250:
                warn('d', smp); return
            P, D = psi_delta(phi, d, True)
            err = np.sqrt(np.mean(np.concatenate([(dat[0] - P) ** 2, wrap(dat[1] - D) ** 2])))
            self.res_b12 = (smp, phi, d, P, D)
            self.lbl_err.config(text=f'error = {err:.3f} deg')
            self.say(SAY['B12'].format(smp, f'{err:.3f}'))
        elif not (self.res_b12 and self.res_b12[0] == smp):
            self.lbl_err.config(text='error = — deg')
        a1.clear(); a2.clear()
        a1.plot(LAM, dat[0], 'o', ms=4, label=smp + '.txt'); a2.plot(LAM, dat[1], 'o', ms=4, label=smp + '.txt')
        if self.res_b12 and self.res_b12[0] == smp:
            _, phi, d, P, D = self.res_b12
            a1.plot(LAM, P, label=f'Φ = {phi:g}°, d = {d:g} nm'); a2.plot(LAM, D, label=f'Φ = {phi:g}°, d = {d:g} nm')
        a1.set_ylabel('Ψ, deg'); a2.set_ylabel('Δ, deg'); a2.set_xlabel('λ, nm')
        a1.legend(loc='best')
        self._show_no_legend2('b12')

    # ---------------- Part B.3–B.7 — gen_data, B.py, B7.py ----------------
    def setup_tab_b3(self):
        col = self._left(self.tab_b3)
        f = self._frame(col, ' B_in.txt ')
        ttk.Label(f, text='Name    Φ (°)    T (°C)    t (min)').pack(anchor=tk.W)
        self.ain_b = self._text(f, 'Name\tPhi\tT\tt\ntest\t50\t1000\t40\n', 3)
        row = ttk.Frame(f); row.pack(fill=tk.X, pady=(8, 0))
        self.btn_gen = ttk.Button(row, text='Run gen_data', command=self.gen_data); self.btn_gen.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        self.btn_stop = ttk.Button(row, text='Stop', command=self.stop_gen, state=tk.DISABLED); self.btn_stop.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))
        self.pb = ttk.Progressbar(f, maximum=1.0); self.pb.pack(fill=tk.X, pady=(8, 0))
        g = self._frame(col, ' Processing ')
        row = ttk.Frame(g); row.pack(fill=tk.X)
        self.btn_proc = ttk.Button(row, text='Run B.py', command=self.run_b); self.btn_proc.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        self.btn_b7 = ttk.Button(row, text='Run B7.py', command=self.run_b7); self.btn_b7.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))
        self.lbl_b7 = ttk.Label(g, text='', font=('Arial', 9, 'bold'), justify=tk.LEFT); self.lbl_b7.pack(anchor=tk.W, pady=(10, 0))
        self.btn_to8 = ttk.Button(g, text='Append to B8_in.txt', command=self.to_b8, state=tk.DISABLED); self.btn_to8.pack(fill=tk.X, pady=(6, 0))
        self._plot(self.tab_b3, 'b3', 2)

    def read_b(self):
        r = rows_of(self.ain_b.get('1.0', tk.END))
        if not r or len(r[0]) < 4:
            error('brow'); return None
        try:
            o = dict(name=r[0][0], phi=float(r[0][1]), T=float(r[0][2]), tmax=float(r[0][3]))
        except ValueError:
            error('brow'); return None
        if not 20 <= o['phi'] <= 80:
            warn('phi'); return None
        if not 800 <= o['T'] <= 1200:
            warn('T'); return None
        if not 0 < o['tmax'] <= 200:
            warn('tmax'); return None
        return o

    def _buttons(self, running):
        s = tk.DISABLED if running else tk.NORMAL
        for b in (self.btn_gen, self.btn_proc, self.btn_b7):
            b.config(state=s)

    def gen_data(self):
        if self.gen:
            return
        o = self.read_b()
        if not o:
            return
        o.update(frames=[], res=None, d=TR.dn, t=0)
        self.exps[o['name']] = o; self.cur = o['name']; self.gen = o; self.b7 = None
        self.lbl_b7.config(text=''); self.btn_to8.config(state=tk.DISABLED)
        self._buttons(True); self.btn_stop.config(state=tk.NORMAL)
        self.after(110, self._gen_step)

    def _gen_step(self):
        o = self.gen
        if not o:
            return
        for _ in range(20):
            o['d'] = TR.grow(o['T'], 0.1, o['d'])
        o['t'] += 2
        # the beam wanders by a tenth of a degree between measurements
        o['frames'].append((o['t'], noisy(psi_delta(o['phi'] + np.random.normal(0, 0.12), o['d'], True))))
        n = int(o['tmax'] // 2)
        self.pb.config(value=len(o['frames']) / n)
        self.say(SAY['gen'].format(o['name'], len(o['frames']), n))
        if len(o['frames']) >= n:
            self.stop_gen()
        else:
            self.draw_b3()
            self.after(110, self._gen_step)

    def stop_gen(self):
        if not self.gen:
            return
        o = self.gen; self.gen = None
        self._buttons(False); self.btn_stop.config(state=tk.DISABLED)
        self.say(SAY['genDone'].format(o['name'], len(o['frames']))); self.draw_b3()

    def run_b(self):
        o = self.read_b()
        if not o:
            return
        ex = self.exps.get(o['name'])
        if not ex or not ex['frames']:
            error('noexp', o['name']); return
        self.cur = o['name']; ex['res'] = []
        self._buttons(True)
        for i, (t, s) in enumerate(ex['frames']):
            d, e = fit_d(ex['phi'], s); ex['res'].append((t, d, e))
            self.pb.config(value=(i + 1) / len(ex['frames']))
            self.say(SAY['proc'].format(i + 1, len(ex['frames']))); self.update()
        self._buttons(False)
        self.say(SAY['procDone'].format(ex['name'])); self.draw_b3()

    def run_b7(self):
        o = self.read_b()
        if not o:
            return
        ex = self.exps.get(o['name'])
        if not ex:
            error('noexp', o['name']); return
        if not ex['res']:
            error('noproc', o['name']); return
        p = np.array([r for r in ex['res'] if r[1] >= 25])
        if len(p) < 4:
            self.b7 = None; self.btn_to8.config(state=tk.DISABLED); self.lbl_b7.config(text='')
            warn('thin'); self.draw_b3(); return
        t, d = p[:, 0], p[:, 1]
        M = np.vstack([d * d, d, np.ones_like(d)]).T
        c, *_ = np.linalg.lstsq(M, t, rcond=None)
        s2 = np.sum((t - M @ c) ** 2) / max(1, len(t) - 3)
        cov = s2 * np.linalg.inv(M.T @ M)
        B, BA = 1 / c[0], 1 / c[1]
        sB, sBA = np.sqrt(cov[0, 0]) / c[0] ** 2, np.sqrt(cov[1, 1]) / c[1] ** 2
        self.b7 = dict(name=ex['name'], T=ex['T'], B=B, sB=sB, BA=BA, sBA=sBA, c=c)
        self.btn_to8.config(state=tk.NORMAL)
        self.lbl_b7.config(text=f"T = {ex['T']:g} °C\nB = {B:.1f} ± {sB:.1f} nm²/min\nB/A = {BA:.3f} ± {sBA:.3f} nm/min")
        self.say(SAY['b7'].format(ex['name'], len(p))); self.draw_b3()

    def to_b8(self):
        if self.b7:
            r = self.b7
            body = self.ain_b8.get('1.0', tk.END).rstrip()
            self.ain_b8.delete('1.0', tk.END)
            self.ain_b8.insert('1.0', body + f"\n{r['T']:g}\t{r['B']:.1f}\t{r['sB']:.1f}\t{r['BA']:.3f}\t{r['sBA']:.3f}\n")
            self.say(SAY['added'])

    def draw_b3(self):
        a1, a2 = self.axes_b3
        a1.clear(); a2.clear()
        ex = self.exps.get(self.cur)
        if ex and ex['res']:
            r = np.array(ex['res'])
            a1.errorbar(r[:, 0], r[:, 1], yerr=r[:, 2], fmt='o', ms=4, label=ex['name'] + ' (B.py)')
            if self.b7 and self.b7['name'] == ex['name']:
                ds = np.arange(25, r[:, 1].max() + 1e-9, 0.5); c = self.b7['c']
                a1.plot(c[0] * ds ** 2 + c[1] * ds + c[2], ds, label='t = d²/B + d/(B/A) + c (B7.py)')
        if ex and ex['frames']:
            t, (P, D) = ex['frames'][-1]
            a2.plot(LAM, P, 'o', ms=4, label='Ψ'); a2.plot(LAM, D, 'o', ms=4, label='Δ')
            a2.set_title(f"{ex['name']}:  Φ = {ex['phi']:g}°,  T = {ex['T']:g} °C,  t = {t} min")
        a1.set_xlabel('t, min'); a1.set_ylabel('d, nm'); a2.set_xlabel('λ, nm'); a2.set_ylabel('Ψ, Δ, deg')
        self._show('b3')

    # ---------------- Part B.8 — B8.py ----------------
    def setup_tab_b8(self):
        col = self._left(self.tab_b8)
        f = self._frame(col, ' B8_in.txt ')
        ttk.Label(f, text='T (°C)   B   ΔB   B/A   Δ(B/A)').pack(anchor=tk.W)
        self.ain_b8 = self._text(f, 'T\tB\tdB\tB/A\td(B/A)\n', 9)
        ttk.Button(f, text='Calculate and plot', command=self.plot_part_b8).pack(fill=tk.X, pady=(12, 0))
        self.lbl_b8 = ttk.Label(f, text='', font=('Arial', 9, 'bold'), justify=tk.LEFT); self.lbl_b8.pack(anchor=tk.W, pady=(10, 0))
        self._plot(self.tab_b8, 'b8', 2)
        a1, a2 = self.axes_b8
        a1.set_ylabel('ln(B·min/nm²)'); a2.set_ylabel('ln(B/A·min/nm)'); a2.set_xlabel('1/T, 1/K')
        self.fig_b8.tight_layout()

    def plot_part_b8(self):
        R = []
        for r in rows_of(self.ain_b8.get('1.0', tk.END)):
            try:
                if len(r) < 5:
                    raise ValueError
                v = [float(x) for x in r[:5]]
            except ValueError:
                error('row', ' '.join(r)); return
            if not (v[1] > 0 and v[3] > 0):
                warn('pos', ' '.join(r)); return
            R.append(v)
        if len(R) < 2:
            warn('b8need'); return
        R = np.array(R); x = 1 / (R[:, 0] + 273.15)
        a1, a2 = self.axes_b8
        a1.clear(); a2.clear()
        out = {}
        for ax, key, y, e, lab in ((a1, 'B', np.log(R[:, 1]), R[:, 2] / R[:, 1], 'ln(B·min/nm²)'),
                                   (a2, 'BA', np.log(R[:, 3]), R[:, 4] / R[:, 3], 'ln(B/A·min/nm)')):
            w = 1 / np.maximum(e, 1e-6) ** 2
            S, Sx, Sy, Sxx, Sxy = w.sum(), (w * x).sum(), (w * y).sum(), (w * x * x).sum(), (w * x * y).sum()
            Dt = S * Sxx - Sx ** 2; b = (S * Sxy - Sx * Sy) / Dt; a = (Sy - b * Sx) / S
            chi = (w * (y - a - b * x) ** 2).sum(); s2 = max(1.0, chi / max(1, len(x) - 2))
            sb = np.sqrt(s2 * S / Dt)
            out[key] = (b, sb)
            ax.errorbar(x, y, yerr=e, fmt='o', ms=5, label='B8_in.txt')
            xs = np.array([x.min(), x.max()])
            ax.plot(xs, a + b * xs, label=f'slope = {b:.0f} ± {sb:.0f} K')
            ax.set_ylabel(lab)
        a2.set_xlabel('1/T, 1/K')
        self.res_b8 = (x, R)
        self.lbl_b8.config(text=f"ln B:      slope = {out['B'][0]:.0f} ± {out['B'][1]:.0f} K\n"
                                f"ln(B/A):  slope = {out['BA'][0]:.0f} ± {out['BA'][1]:.0f} K")
        self._show('b8')
        self.say(SAY['B8'].format(len(R)))

    # ---------------- Save data as CSV ----------------
    def save_csv(self):
        i = self.notebook.index(self.notebook.select())
        rows = name = None
        if i == 0 and self.res_a:
            name = 'A_out.csv'
            rows = [['lambda_nm'] + [s for r in self.res_a for s in (r[0] + '_Psi', r[0] + '_Delta')]]
            rows += [[l] + [f'{v:.5f}' for r in self.res_a for v in (r[3][0][k], r[3][1][k])] for k, l in enumerate(LAM)]
        elif i == 1:
            smp = self.samp.get(); dat = DATA[smp]; name = smp + '.csv'
            rows = [['lambda_nm', 'Psi_deg', 'Delta_deg']] + [[l, f'{dat[0][k]:.3f}', f'{dat[1][k]:.3f}'] for k, l in enumerate(LAM)]
        elif i == 2:
            ex = self.exps.get(self.cur)
            if ex and ex['res']:
                name = 'res_' + ex['name'] + '.csv'
                rows = [['t_min', 'd_nm', 'dd_nm']] + [[t, f'{d:.2f}', f'{e:.2f}'] for t, d, e in ex['res']]
            elif ex and ex['frames']:
                t, (P, D) = ex['frames'][-1]; name = f"{ex['name']}_t{t}.csv"
                rows = [['lambda_nm', 'Psi_deg', 'Delta_deg']] + [[l, f'{P[k]:.3f}', f'{D[k]:.3f}'] for k, l in enumerate(LAM)]
        elif i == 3 and self.res_b8:
            x, R = self.res_b8; name = 'B8_out.csv'
            rows = [['invT_K', 'lnB', 'dlnB', 'lnBA', 'dlnBA']] + [
                [f'{x[k]:.6e}', f'{np.log(R[k, 1]):.5f}', f'{R[k, 2] / R[k, 1]:.5f}', f'{np.log(R[k, 3]):.5f}', f'{R[k, 4] / R[k, 3]:.5f}']
                for k in range(len(x))]
        if rows is None:
            warn('nodata'); return
        p = filedialog.asksaveasfilename(defaultextension='.csv', initialfile=name, filetypes=[('CSV', '*.csv')])
        if not p:
            return
        with open(p, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerows(rows)
        self.say(SAY['saved'].format(p))


if __name__ == '__main__':
    app = OxidationApp()
    app.mainloop()
