#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISPhO 2023 Theoretical Problem 1 — "Polycrystal diffusion"
A.exe, B.exe and C.exe with B.nb, C.nb and InteractiveBuffer as the tabs of
one Tk window, laid out like the organisers' FBG Writer of ISPhO 2026.

The organisers' programs were never published; these are rebuilt from the
inputs and outputs on the problem sheet and the results of the solution.
Every label on the window stays in English, as the sheet quotes them; the
dialogs and the output line follow LANG.

A.exe  impurity atoms hop between the inter-nodes of a cubic lattice
       (a = 1); along each axis a jump happens at the rate 2D/a², with
       D = D0 sqrt(T) exp(-Eg/T) in arbitrary units.  The program returns
       the rms displacement and its error over the N particles.
B.exe  type-A kinetics: the front moves with the effective coefficient of
       the polycrystal, D_eff/D = 1 + alpha delta (D_gb/D - 1); it writes
       ln c against z².
C.exe  type-B kinetics: the boundaries carry the impurity ahead of the
       lattice front, ln c falls linearly in z^(6/5); it writes the
       average profile and the map around one boundary.
Eg, alpha, xi, eta, zeta and C are left for the user to find; Eg, D0,
alpha and C are drawn afresh each time the window opens.

    python ispho2023_T1_diffusion_sim_KO.py          (needs numpy and matplotlib)
"""

import csv
import random
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import numpy as np
from matplotlib import rcParams
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

LANG = "EN"          # the EN edition differs only in this line

MSG = {
 "EN": {
  "num": ("Input error", "Please ensure you have entered a numerical value. Also check decimal delimiter (0.0/0,0)."),
  "range": ("Out of bounds", "Please provide {}."),
  "buf2": ("Buffer", "Add at least two points."),
  "nofit": ("Fit", "No fit yet: run the program and choose a range with at least 3 points."),
  "nodata": ("Nothing to save", "Run the program first."),
 },
 "KO": {
  "num": ("입력 오류", "숫자를 입력했는지 확인하세요. 소수점 기호(0.0/0,0)도 확인하세요."),
  "range": ("범위 밖", "{} 인 값을 넣으세요."),
  "buf2": ("Buffer", "점을 두 개 이상 넣으세요."),
  "nofit": ("직선 맞춤", "아직 맞춘 직선이 없습니다. 프로그램을 실행하고 점이 3 개 이상인 구간을 고르세요."),
  "nodata": ("저장할 데이터 없음", "먼저 실행하세요."),
 }}[LANG]

SAY = {
 "EN": dict(idle="Set the input and run.", Arun="A.exe: particle {} / {}", A="A.exe: t = {}, T = {}, N = {} ({} s)",
            B="B.exe: t = {}, Dgb/D = {}, δ = {} → Bavg.csv ({} points)", C="C.exe: t = {}, Dgb/D = {}, δ = {} → Cavg.csv ({} points), Cmap.csv",
            add="Buffer: {} points", toBuf="ln|k| = {} copied to y (t = {}, Dgb/D = {}, δ = {}). Enter x.", saved="Saved as {}."),
 "KO": dict(idle="입력을 정하고 실행하세요.", Arun="A.exe: 입자 {} / {}", A="A.exe: t = {}, T = {}, N = {} ({} s)",
            B="B.exe: t = {}, Dgb/D = {}, δ = {} → Bavg.csv ({} 점)", C="C.exe: t = {}, Dgb/D = {}, δ = {} → Cavg.csv ({} 점), Cmap.csv",
            add="Buffer: 점 {} 개", toBuf="ln|k| = {} 를 y 에 넣었습니다 (t = {}, Dgb/D = {}, δ = {}). x 를 넣으세요.", saved="{} 로 저장했습니다."),
}[LANG]


def warn(key, *a):
    t, m = MSG[key]
    messagebox.showwarning(t, m.format(*a))


def error(key, *a):
    t, m = MSG[key]
    messagebox.showerror(t, m.format(*a))


RANGE = {"A": ((1, 10), (1, 10), (100, 10000)), "B": ((2, 5), (2, 5), (0.005, 0.05)), "C": ((0.005, 0.2), (5, 50), (0.02, 0.2))}
NAMES = {"A": ("t", "T", "N"), "B": ("t", "Dgb/D", "δ"), "C": ("t", "Dgb/D", "δ")}


def U(a, b):
    return random.uniform(a, b)


class Truth:
    def __init__(self):
        self.Eg, self.D0, self.alpha = U(3.40, 3.80), 113 * U(0.95, 1.05), U(0.68, 0.82)
        self.C, self.xi, self.eta, self.zeta = 1.42 * U(0.96, 1.04), -0.39, -0.68, -0.44


TR = Truth()


def eta_A(t, T, N):
    return N * 6 * TR.D0 * np.sqrt(T) * np.exp(-TR.Eg / T) * t * 4e-9 + 0.05


def run_A(t, T, N, progress):
    """Random walk between inter-nodes; exact hops for short walks, the normal limit for long ones."""
    D = TR.D0 * np.sqrt(T) * np.exp(-TR.Eg / T)
    n = np.random.poisson(6 * D * t, size=N)
    pos = np.zeros((N, 3))
    for i in range(N):
        if n[i] < 3000:
            ax = np.random.randint(0, 3, n[i]); sg = np.random.choice((-1, 1), n[i])
            for k in range(3):
                pos[i, k] = np.sum(sg[ax == k])
        else:
            pos[i] = np.round(np.random.normal(0, np.sqrt(n[i] / 3), 3))
        if i % 400 == 399:
            progress(i + 1)
    r2 = np.sum(pos ** 2, axis=1); R = np.sqrt(r2.mean())
    return pos, R, r2.std(ddof=1) / np.sqrt(N) / (2 * R)


def run_B(t, g, dl):
    Deff = 1 + TR.alpha * dl * (g - 1)
    z = np.abs(np.random.normal(0, np.sqrt(2 * Deff * t), 40000)); dz = 0.1
    h, e = np.histogram(z, bins=np.arange(0, z.max() + dz, dz))
    zc = (e[:-1] + e[1:]) / 2; ok = h >= 3
    return zc[ok] ** 2, np.log(h[ok] / (z.size * dz)), z[:1500]


def run_C(t, g, dl):
    k = TR.C * dl ** TR.xi * g ** TR.eta * t ** TR.zeta
    A0 = 1 / np.sqrt(np.pi * t); Agb = A0 * dl * np.sqrt(g) * 0.6; ell = 0.7 * np.sqrt(t)
    zmax = (np.log(Agb / 1e-6 * A0) / k) ** (5 / 6) * 0.9
    z = (np.arange(160) + 0.5) / 160 * zmax; y = np.linspace(-0.5, 0.5, 81)
    Z, Y = np.meshgrid(z, y, indexing="ij")
    c = A0 * np.exp(-Z ** 2 / (4 * t)) + Agb * np.exp(-k * Z ** 1.2) * np.exp(-np.abs(Y) / ell) / (2 * ell * (1 - np.exp(-0.5 / ell)))
    cnt = 6e6; m = c.mean(axis=1); n = m * cnt * zmax / 160 / A0; ok = n >= 4
    lc = np.log(m[ok] * (1 + np.random.normal(0, 1, ok.sum()) / np.sqrt(n[ok])))
    nn = c * 40 * cnt * zmax / 160 / 81 / A0
    cmap = np.where(nn >= 1, np.log(np.abs(c * (1 + np.random.normal(0, 1, c.shape) / np.sqrt(np.maximum(nn, 1))))), np.nan)
    return z[ok] ** 1.2, lc, cmap, zmax


def linfit(x, y):
    """Least squares y = a + b x with the standard errors of a and b."""
    x, y = np.asarray(x, float), np.asarray(y, float); n = len(x)
    S, Sx, Sy, Sxx, Sxy = n, x.sum(), y.sum(), (x * x).sum(), (x * y).sum()
    D = S * Sxx - Sx ** 2; b = (S * Sxy - Sx * Sy) / D; a = (Sy - b * Sx) / S
    s2 = ((y - a - b * x) ** 2).sum() / max(1, n - 2)
    return a, b, np.sqrt(s2 * Sxx / D), np.sqrt(s2 * S / D)


class DiffusionApp(tk.Tk):
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
        self.title('Polycrystal Diffusion')
        self.res = {'A': None, 'B': None, 'C': None}; self.kfit = {'B': None, 'C': None}
        self.fr = {'B': [0.0, 1.0], 'C': [0.0, 1.0]}; self.buf = []; self.bfit = None; self.busy = False
        self.grains = None
        self.setup_bottom_panel()
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        for key, label in (('a', 'Part A'), ('b', 'Part B'), ('c', 'Part C'), ('buf', 'Buffer')):
            fr = ttk.Frame(self.notebook)
            setattr(self, 'tab_' + key, fr)
            self.notebook.add(fr, text=label)
            getattr(self, 'setup_tab_' + key)()
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

    def _left(self, tab):
        col = ttk.Frame(tab, width=300)
        col.pack(side=tk.LEFT, fill=tk.Y)
        return col

    def _frame(self, col, title):
        f = ttk.LabelFrame(col, text=title, padding=15)
        f.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        return f

    def _params(self, col, k, rows, cmd):
        f = self._frame(col, ' Parameters ')
        ents = []
        for r, (lab, val) in enumerate(rows):
            ttk.Label(f, text=lab).grid(row=r, column=0, sticky=tk.W, pady=5)
            e = ttk.Entry(f, width=14); e.insert(0, val); e.grid(row=r, column=1, pady=5, padx=5)
            e.bind('<Return>', lambda ev: cmd())
            ents.append(e)
        setattr(self, 'ent_' + k, ents)
        return f

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

    def _show(self, key, legend=(0,)):
        fig = getattr(self, 'fig_' + key); axes = getattr(self, 'axes_' + key)
        for i, ax in enumerate(axes):
            ax.grid(True, linestyle='-', alpha=0.5)
            ax.grid(True, linestyle='--', which='minor', alpha=0.3)
            if i in legend and ax.get_legend_handles_labels()[0]:
                ax.legend(loc='best')
        fig.tight_layout()
        getattr(self, 'canvas_' + key).draw(); getattr(self, 'toolbar_' + key).update()

    def read_par(self, k):
        try:
            v = [float(e.get()) for e in getattr(self, 'ent_' + k)]
        except ValueError:
            error('num'); return None
        for x, (lo, hi), nm in zip(v, RANGE[k], NAMES[k]):
            if not lo <= x <= hi:
                warn('range', f'{nm} ∈ [{lo:g}; {hi:g}]'); return None
        return v

    # ---------------- Part A — A.exe ----------------
    def setup_tab_a(self):
        col = self._left(self.tab_a)
        f = self._params(col, 'A', [('t  [1; 10]:', '10'), ('T  [1; 10]:', '1'), ('N  [100; 10000]:', '1000')], self.plot_part_a)
        self.lbl_eta = ttk.Label(f, text=''); self.lbl_eta.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        self.btn_a = ttk.Button(f, text='Run A.exe', command=self.plot_part_a)
        self.btn_a.grid(row=4, column=0, columnspan=2, pady=20, sticky=tk.EW)
        self.pb_a = ttk.Progressbar(f, maximum=1.0); self.pb_a.grid(row=5, column=0, columnspan=2, sticky=tk.EW)
        self.lbl_a = ttk.Label(f, text='', font=('Arial', 9, 'bold')); self.lbl_a.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        for e in self.ent_A:
            e.bind('<KeyRelease>', lambda ev: self.upd_eta())
        self.upd_eta()
        self._plot(self.tab_a, 'a', 2); self.draw_a()

    def upd_eta(self):
        try:
            t, T, N = (float(e.get()) for e in self.ent_A)
            self.lbl_eta.config(text=f'Expected simulation time: {eta_A(t, T, N):.1f} s')
        except ValueError:
            self.lbl_eta.config(text='Expected simulation time: — s')

    def plot_part_a(self):
        if self.busy:
            return
        v = self.read_par('A')
        if not v:
            return
        N = int(round(v[2])); self.busy = True; self.btn_a.config(state=tk.DISABLED); t0 = time.time()

        def progress(i):
            self.pb_a.config(value=i / N); self.say(SAY['Arun'].format(i, N)); self.update()
        pos, R, sR = run_A(v[0], v[1], N, progress)
        self.pb_a.config(value=1.0); self.busy = False; self.btn_a.config(state=tk.NORMAL)
        self.res['A'] = (pos, R, sR, v[0], v[1], N)
        self.lbl_a.config(text=f'Δr_sq = {R:.3f} ± {sR:.3f}')
        self.say(SAY['A'].format(f'{v[0]:g}', f'{v[1]:g}', N, f'{time.time() - t0:.1f}'))
        self.draw_a()

    def draw_a(self):
        a1, a2 = self.axes_a; a1.clear(); a2.clear()
        if self.res['A']:
            pos, R, sR, t, T, N = self.res['A']
            a1.plot(pos[:3000, 0], pos[:3000, 1], '.', ms=4, alpha=0.6)
            a1.set_title(f'{t = :g},  {T = :g},  {N = }')
            r = np.sqrt(np.sum(pos ** 2, axis=1))
            a2.hist(r, bins=40, range=(0, max(r.max(), 1)))
        a1.set_xlabel('x, a'); a1.set_ylabel('y, a'); a2.set_xlabel('r, a'); a2.set_ylabel('N')
        self._show('a', legend=())

    # ---------------- Part B / Part C — B.exe + B.nb, C.exe + C.nb ----------------
    def _setup_bc(self, k, tab, rows):
        col = self._left(tab)
        f = self._params(col, k, rows, lambda: self.run_bc(k))
        ttk.Button(f, text=f'Run {k}.exe', command=lambda: self.run_bc(k)).grid(row=3, column=0, columnspan=2, pady=20, sticky=tk.EW)
        g = self._frame(col, f' Fit range ({k}.nb) ')
        sc, lb = [], []
        for i, lab in enumerate(('from', 'to')):
            ttk.Label(g, text=lab).grid(row=i, column=0, sticky=tk.W, pady=4)
            var = tk.DoubleVar(value=float(i))
            s = ttk.Scale(g, from_=0, to=1, variable=var, length=150, command=lambda val, i=i: self.on_scale(k, i, float(val)))
            s.grid(row=i, column=1, padx=5)
            l = ttk.Label(g, text='—', width=8, anchor=tk.E); l.grid(row=i, column=2, sticky=tk.E)
            sc.append(var); lb.append(l)
        setattr(self, 'sc_' + k, sc); setattr(self, 'scl_' + k, lb)
        lf = ttk.Label(g, text='', font=('Arial', 9, 'bold'), justify=tk.LEFT); lf.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
        setattr(self, 'lbl_fit_' + k, lf)
        ttk.Button(g, text='Copy ln|slope| to Buffer', command=lambda: self.to_buf(k)).grid(row=3, column=0, columnspan=3, pady=(6, 0), sticky=tk.EW)
        self._plot(tab, k.lower(), 2); self.draw_bc(k)

    def setup_tab_b(self):
        self._setup_bc('B', self.tab_b, [('t  [2; 5]:', '5'), ('Dgb/D  [2; 5]:', '5'), ('δ  [0.005; 0.05]:', '0.02')])

    def setup_tab_c(self):
        self._setup_bc('C', self.tab_c, [('t  [0.005; 0.2]:', '0.1'), ('Dgb/D  [5; 50]:', '25'), ('δ  [0.02; 0.2]:', '0.1')])

    def run_bc(self, k):
        v = self.read_par(k)
        if not v:
            return
        out = run_B(*v) if k == 'B' else run_C(*v)
        self.res[k] = out + (v,); self.grains = None
        xm = out[0].max(); self.fr[k] = [0, 0.6 * xm] if k == 'B' else [0.15 * xm, 0.85 * xm]
        self.sync_scales(k)
        self.say(SAY[k].format(f'{v[0]:g}', f'{v[1]:g}', f'{v[2]:g}', len(out[0])))
        self.refit(k)

    def sync_scales(self, k):
        xm = self.res[k][0].max()
        for i in range(2):
            getattr(self, 'sc_' + k)[i].set(self.fr[k][i] / xm)
            getattr(self, 'scl_' + k)[i].config(text=f'{self.fr[k][i]:.4g}')

    def on_scale(self, k, i, val):
        if not self.res[k]:
            return
        xm = self.res[k][0].max(); fr = self.fr[k]
        if i == 0:
            fr[0] = min(val * xm, fr[1] - 0.02 * xm)
        else:
            fr[1] = max(val * xm, fr[0] + 0.02 * xm)
        getattr(self, 'scl_' + k)[i].config(text=f'{fr[i]:.4g}')
        self.refit(k)

    def refit(self, k):
        x, y = self.res[k][0], self.res[k][1]; x0, x1 = self.fr[k]
        ok = (x >= x0) & (x <= x1)
        if ok.sum() >= 3:
            a, b, sa, sb = linfit(x[ok], y[ok])
            self.kfit[k] = (a, b, sa, sb, x0, x1)
            getattr(self, 'lbl_fit_' + k).config(text=f'slope = {b:.6g} ± {sb:.2g}\nintercept = {a:.6g} ± {sa:.2g}\n{ok.sum()} points')
        else:
            self.kfit[k] = None
            getattr(self, 'lbl_fit_' + k).config(text='fewer than 3 points in the range')
        self.draw_bc(k)

    def draw_bc(self, k):
        fig = getattr(self, 'fig_' + k.lower()); a1, a2 = getattr(self, 'axes_' + k.lower())
        fig.clf(); a1, a2 = fig.add_subplot(211), fig.add_subplot(212)
        setattr(self, 'axes_' + k.lower(), [a1, a2])
        xl = 'z²' if k == 'B' else '$z^{6/5}$'
        R = self.res[k]
        if R:
            x, y = R[0], R[1]; p = R[-1]
            a1.plot(x, y, 'o', ms=4, label='Bavg.csv' if k == 'B' else 'Cavg.csv')
            if self.kfit[k]:
                a, b, sa, sb, x0, x1 = self.kfit[k]
                a1.plot([x0, x1], [a + b * x0, a + b * x1], label=f'fit: slope = {b:.4g}')
            a1.set_title(f't = {p[0]:g},  Dgb/D = {p[1]:g},  δ = {p[2]:g}')
            if k == 'B':
                # a cut through the polycrystal: grains, their boundaries (width ∝ δ), the impurity
                if self.grains is None:
                    self.grains = np.column_stack([np.random.uniform(-0.5, 5.5, 36), np.random.uniform(-0.5, 2.5, 36)])
                W, H, nx, ny = 6, 3, 300, 150
                X, Z = np.meshgrid((np.arange(nx) + 0.5) / nx * W - 0.5, (np.arange(ny) + 0.5) / ny * H - 0.5)
                d2 = (X[..., None] - self.grains[:, 0]) ** 2 + (Z[..., None] - self.grains[:, 1]) ** 2
                srt = np.sort(d2, axis=-1); k1 = np.argmin(d2, axis=-1)
                gb = (np.sqrt(srt[..., 1]) - np.sqrt(srt[..., 0])) / 2 < max(p[2] / 6, 0.7 * W / nx)
                sh = 200 + (k1 * 37) % 40
                img = np.where(gb[..., None], np.array([60, 90, 150]), np.stack([sh, sh + 5, sh + 12], axis=-1)).astype(np.uint8)
                a2.imshow(img, extent=(0, W, H, 0), aspect='auto', interpolation='nearest')
                z = R[2][R[2] < H]
                a2.plot(np.random.uniform(0, W, z.size), z, '.', ms=3, color='#d62728', label='impurity')
                a2.set_xlim(0, W); a2.set_ylim(H, 0); a2.set_xlabel('x'); a2.set_ylabel('z')
            else:
                cmap, zmax = R[2], R[3]
                im = a2.imshow(cmap.T, aspect='auto', origin='lower', extent=(0, zmax ** 1.2, -0.5, 0.5), interpolation='nearest')
                fig.colorbar(im, ax=a2, label='ln c')
                a2.set_xlabel(xl); a2.set_ylabel('y')
        else:
            a2.set_xlabel('x' if k == 'B' else xl); a2.set_ylabel('z' if k == 'B' else 'y')
        a1.set_xlabel(xl); a1.set_ylabel('ln c̄')
        self._show(k.lower())

    # ---------------- Buffer — InteractiveBuffer.nb ----------------
    def setup_tab_buf(self):
        col = self._left(self.tab_buf)
        f = self._frame(col, ' InteractiveBuffer ')
        ttk.Label(f, text='x:').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.e_bx = ttk.Entry(f, width=14); self.e_bx.grid(row=0, column=1, pady=5, padx=5)
        ttk.Label(f, text='y:').grid(row=1, column=0, sticky=tk.W, pady=5)
        self.e_by = ttk.Entry(f, width=14); self.e_by.grid(row=1, column=1, pady=5, padx=5)
        for e in (self.e_bx, self.e_by):
            e.bind('<Return>', lambda ev: self.buf_add())
        for i, (lab, cmd) in enumerate((('Add point', self.buf_add), ('Remove last point', self.buf_del),
                                        ('Clear data', self.buf_clr), ('Plot fit', self.buf_fit))):
            ttk.Button(f, text=lab, command=cmd).grid(row=2 + i // 2, column=i % 2, sticky=tk.EW, padx=2, pady=(8 if i < 2 else 2, 0))
        g = self._frame(col, ' Points ')
        ttk.Label(g, text='#     x     y').pack(anchor=tk.W)
        self.lst = tk.Text(g, height=8, width=34, font=('Consolas', 10), state=tk.DISABLED); self.lst.pack(fill=tk.X)
        self.lbl_buf = ttk.Label(g, text='', font=('Arial', 9, 'bold'), justify=tk.LEFT); self.lbl_buf.pack(anchor=tk.W, pady=(10, 0))
        self._plot(self.tab_buf, 'buf', 1); self.draw_buf()

    def buf_add(self):
        try:
            p = (float(self.e_bx.get()), float(self.e_by.get()))
        except ValueError:
            error('num'); return
        self.buf.append(p); self.e_bx.delete(0, tk.END); self.e_by.delete(0, tk.END)
        self.buf_list(); self.draw_buf(); self.say(SAY['add'].format(len(self.buf)))

    def buf_del(self):
        if self.buf:
            self.buf.pop()
        self.bfit = None; self.buf_list(); self.draw_buf()

    def buf_clr(self):
        self.buf = []; self.bfit = None; self.buf_list(); self.draw_buf()

    def buf_fit(self):
        if len(self.buf) < 2:
            warn('buf2'); return
        p = np.array(self.buf); self.bfit = linfit(p[:, 0], p[:, 1]); a, b, sa, sb = self.bfit
        self.lbl_buf.config(text=f'y = a + b x\nb = {b:.6g} ± {sb:.3g}\na = {a:.6g} ± {sa:.3g}')
        self.draw_buf()

    def buf_list(self):
        self.lst.config(state=tk.NORMAL); self.lst.delete('1.0', tk.END)
        self.lst.insert('1.0', '\n'.join(f'{i + 1}\t{x:g}\t{y:g}' for i, (x, y) in enumerate(self.buf)))
        self.lst.config(state=tk.DISABLED)
        if not self.bfit:
            self.lbl_buf.config(text='')

    def draw_buf(self):
        ax = self.axes_buf[0]; ax.clear()
        if self.buf:
            p = np.array(self.buf); ax.plot(p[:, 0], p[:, 1], 'o', label='data')
            if self.bfit and len(p) >= 2:
                a, b, sa, sb = self.bfit; xs = np.array([p[:, 0].min(), p[:, 0].max()])
                ax.plot(xs, a + b * xs, label=f'y = {a:.4g} + {b:.4g} x')
        ax.set_xlabel('x'); ax.set_ylabel('y')
        self._show('buf')

    def to_buf(self, k):
        if not self.kfit[k]:
            warn('nofit'); return
        b = self.kfit[k][1]; p = self.res[k][-1]
        self.e_by.delete(0, tk.END); self.e_by.insert(0, f'{np.log(abs(b)):.5f}'); self.e_bx.delete(0, tk.END)
        self.say(SAY['toBuf'].format(f'{np.log(abs(b)):.5f}', f'{p[0]:g}', f'{p[1]:g}', f'{p[2]:g}'))
        self.notebook.select(3)

    # ---------------- Save data as CSV ----------------
    def save_csv(self):
        i = self.notebook.index(self.notebook.select())
        rows = name = None
        if i == 0 and self.res['A']:
            name = 'A_positions.csv'; rows = [['x', 'y', 'z']] + self.res['A'][0].astype(int).tolist()
        elif i in (1, 2) and self.res['BC'[i - 1]]:
            k = 'BC'[i - 1]; R = self.res[k]; name = k + 'avg.csv'
            rows = [['z2' if k == 'B' else 'z6_5', 'ln_c']] + [[f'{a:.6f}', f'{b:.6f}'] for a, b in zip(R[0], R[1])]
        elif i == 3 and self.buf:
            name = 'buffer.csv'; rows = [['x', 'y']] + [list(p) for p in self.buf]
        if rows is None:
            warn('nodata'); return
        p = filedialog.asksaveasfilename(defaultextension='.csv', initialfile=name, filetypes=[('CSV', '*.csv')])
        if not p:
            return
        with open(p, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerows(rows)
        self.say(SAY['saved'].format(p))


if __name__ == '__main__':
    app = DiffusionApp()
    app.mainloop()
