#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISPhO 2026 Experimental Problem 1 — "Fiber Bragg Grating"
FBG Writer — the organisers' program, rebuilt line by line.

This is the code of the official FBG_Writer_win-x64.exe (PyInstaller,
Python 3.9, app.py), recovered from its bytecode: the same window, the same
tabs and fields, the same formulas, constants, random noise and warnings.
Only the dialog texts are translated in the Korean edition; every label on
the window stays in English, as the problem sheet quotes them.

    python ispho2026_E1_fbg_sim.py          (needs numpy and matplotlib)
"""

import tkinter as tk
from tkinter import ttk, messagebox
from numpy import sqrt, exp, pi, cosh, abs, sinh, sin, cos, log10
from numpy import linspace
from numpy import array
from numpy import random
from numpy import interp
from matplotlib import rcParams
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

Y_OPT = 0.45
FREQ = 1
A_temp_exp = 6.67e-06
n_c = 1.444
T_solid = 110
HF_BASE = 20
HF_DELTA = 30
THETA_OPT = -27
LAMBDA_MIN = 1540
LAMBDA_MAX = 1560

LANG = "EN"          # build_editions.py rewrites this line for the KO edition

MSG = {
 "EN": {
  "bounds": ("Incorrect bounds", "Please provide correct wavelength bounds (1540 to 1560 nm). \nNote: bounds have been set to default value."),
  "less": ("Limit error", "Min wavelength must be strictly less than Max wavelength."),
  "positive": ("Limit error", "Wavelengths must be positive values."),
  "limnum": ("Input error", "Please enter valid numerical values for wavelength limits."),
  "num": ("Input error", "Please ensure you have entered a numerical value. Also check decimal delimiter (0.0/0,0)."),
  "v": ("Incorrect value", "Please provide positive stage velocity."),
  "L": ("Incorrect value", "Please provide feasible fiber length."),
  "T": ("Out of bounds", "Please provide a reachable temperature value."),
  "frame": ("Incorrect value", "Frame number out of bounds. Set to {} min"),
  "F": ("Incorrect value", "Please provide feasible force value."),
  "x": ("Incorrect value", "Please provide feasible displacement value."),
 },
 "KO": {
  "bounds": ("범위 오류", "올바른 파장 범위(1540 ~ 1560 nm)를 입력하세요. \n참고: 범위를 기본값으로 되돌렸습니다."),
  "less": ("범위 오류", "최소 파장은 최대 파장보다 작아야 합니다."),
  "positive": ("범위 오류", "파장은 양수여야 합니다."),
  "limnum": ("입력 오류", "파장 범위에 올바른 숫자를 입력하세요."),
  "num": ("입력 오류", "숫자를 입력했는지 확인하세요. 소수점 기호(0.0/0,0)도 확인하세요."),
  "v": ("잘못된 값", "스테이지 속도는 양수여야 합니다."),
  "L": ("잘못된 값", "가능한 광섬유 길이를 입력하세요."),
  "T": ("범위 밖", "도달할 수 있는 온도를 입력하세요."),
  "frame": ("잘못된 값", "시간이 범위를 벗어났습니다. {} 분으로 맞췄습니다."),
  "F": ("잘못된 값", "가능한 힘의 값을 입력하세요."),
  "x": ("잘못된 값", "가능한 변위 값을 입력하세요."),
 }}[LANG]


def warn(key, *a):
    t, m = MSG[key]
    messagebox.showwarning(t, m.format(*a))


def error(key):
    messagebox.showerror(*MSG[key])


def gaussian_filter1d(input_array, sigma):
    import numpy as np
    radius = int(3 * sigma)
    x = np.arange(-radius, radius + 1)
    kernel = np.exp(-0.5 * (x / sigma) ** 2)
    kernel /= kernel.sum()
    return np.convolve(input_array, kernel, mode='same')


def spectrum(wl, Lambda, kappa, L_nm):
    delta = n_c * 2 * pi / wl - pi / Lambda
    gamma = sqrt(kappa ** 2 - delta ** 2)
    t = gamma / (gamma * cosh(gamma * L_nm) - 1j * delta * sinh(gamma * L_nm)) * (random.rand(len(wl)) * 0.2 + 0.9)
    return t


class FBGApp(tk.Tk):
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
                         'ytick.labelsize': base_font_size})
        rcParams.update({'axes.grid': True, 'axes.grid.which': 'both',
                         'xtick.minor.visible': True, 'ytick.minor.visible': True})
        width = int(screen_w * 0.8)
        height = int(screen_h * 0.8)
        width = max(1000, min(width, 1600))
        height = max(650, min(height, 900))
        self.geometry(f'{width}x{height}+{int((screen_w-width)/2)}+{int((screen_h-height)/2)}')
        self.title('FBG Writer')
        self.setup_bottom_panel()
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook.bind('<<NotebookTabChanged>>', self.on_tab_change)
        for key, label in (('a', 'Part A'), ('c', 'Part C'), ('d', 'Part D'),
                           ('e1', 'Part E.I'), ('e2', 'Part E.II'), ('f', 'Part F')):
            fr = ttk.Frame(self.notebook)
            setattr(self, 'tab_' + key, fr)
            self.notebook.add(fr, text=label)
            getattr(self, 'setup_tab_' + key)()

    def on_tab_change(self, event):
        self.reset_limits_panel()
        w = event.widget.nametowidget(event.widget.select())
        {self.tab_a: self.plot_part_a, self.tab_c: self.plot_part_c, self.tab_d: self.plot_part_d,
         self.tab_e1: self.plot_part_e1, self.tab_e2: self.plot_part_e2, self.tab_f: self.plot_part_f}[w]()

    def reset_limits_panel(self):
        self.entry_wl_min.delete(0, 'end'); self.entry_wl_min.insert(0, f'{LAMBDA_MIN:.1f}')
        self.entry_wl_max.delete(0, 'end'); self.entry_wl_max.insert(0, f'{LAMBDA_MAX:.1f}')

    def setup_bottom_panel(self):
        f = ttk.LabelFrame(self, text='Plot Wavelength Limits (1540-1560 nm)', padding=10)
        f.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        ttk.Label(f, text='Min λ (nm):').pack(side=tk.LEFT, padx=(10, 2))
        self.entry_wl_min = ttk.Entry(f, width=10); self.entry_wl_min.insert(0, f'{LAMBDA_MIN:.1f}')
        self.entry_wl_min.pack(side=tk.LEFT, padx=5)
        ttk.Label(f, text='Max λ (nm):').pack(side=tk.LEFT, padx=(15, 2))
        self.entry_wl_max = ttk.Entry(f, width=10); self.entry_wl_max.insert(0, f'{LAMBDA_MAX:.1f}')
        self.entry_wl_max.pack(side=tk.LEFT, padx=5)
        ttk.Button(f, text='Apply limits to active tab', command=self.apply_global_limits).pack(side=tk.LEFT, padx=20)
        self.entry_wl_min.bind('<Return>', lambda _: self.apply_global_limits())
        self.entry_wl_max.bind('<Return>', lambda _: self.apply_global_limits())

    def get_wl_limits(self):
        try:
            a = float(self.entry_wl_min.get()); b = float(self.entry_wl_max.get())
            if a < b and a >= 1540 and b <= 1560:
                return a, b
            raise ValueError
        except ValueError:
            self.reset_limits_panel()
            warn('bounds')
        return 1540.0, 1560.0

    def apply_global_limits(self):
        try:
            a = float(self.entry_wl_min.get()); b = float(self.entry_wl_max.get())
            if a >= b:
                error('less'); return
            if a <= 0 or b <= 0:
                error('positive'); return
        except ValueError:
            error('limnum'); return
        i = self.notebook.index(self.notebook.select())
        [self.plot_part_a, self.plot_part_c, self.plot_part_d, self.plot_part_e1, self.plot_part_e2, self.plot_part_f][i]()

    def _panel(self, tab, title, rows):
        ctrl = ttk.LabelFrame(tab, text=title, padding=15)
        ctrl.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        ents = []
        for r, (lab, val) in enumerate(rows):
            ttk.Label(ctrl, text=lab).grid(row=r, column=0, sticky=tk.W, pady=5)
            e = ttk.Entry(ctrl, width=12); e.insert(0, val); e.grid(row=r, column=1, pady=5, padx=5)
            ents.append(e)
        return ctrl, ents

    def _plot(self, tab, key):
        pf = ttk.Frame(tab)
        pf.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)
        ax.set_xlabel('λ, nm'); ax.set_ylabel('T, dB')
        ax.set_xlim(*self.get_wl_limits())
        ax.grid(True, linestyle='--', alpha=0.5)
        cv = FigureCanvasTkAgg(fig, master=pf); cv.draw()
        tf = ttk.Frame(pf); tf.pack(side=tk.BOTTOM, fill=tk.X)
        tb = NavigationToolbar2Tk(cv, tf); tb.update()
        cv.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        setattr(self, 'fig_' + key, fig); setattr(self, 'ax_' + key, ax)
        setattr(self, 'canvas_' + key, cv); setattr(self, 'toolbar_' + key, tb)

    def _show(self, key, wl, T_db, wl_min, wl_max, title=None, relim=False):
        ax = getattr(self, 'ax_' + key)
        ax.clear()
        if title: ax.set_title(title)
        ax.plot(wl.real, T_db)
        ax.set_xlabel('λ, nm'); ax.set_ylabel('T, dB')
        if relim: ax.relim(); ax.autoscale_view()
        ax.set_xlim(wl_min, wl_max)
        ax.grid(True, linestyle='-', alpha=0.5)
        ax.grid(True, linestyle='--', which='minor', alpha=0.3)
        getattr(self, 'canvas_' + key).draw(); getattr(self, 'toolbar_' + key).update()

    # A
    def setup_tab_a(self):
        ctrl, (self.entry_a_dy, self.entry_a_v, self.entry_a_l) = self._panel(
            self.tab_a, ' Parameters ', [('dY (μm):', '0.0'), ('v (mm/s):', '0.50'), ('L (mm):', '50.0')])
        ttk.Button(ctrl, text='Calculate and plot', command=self.plot_part_a).grid(row=3, column=0, columnspan=2, pady=20, sticky=tk.EW)
        self._plot(self.tab_a, 'a'); self.plot_part_a()

    def plot_part_a(self):
        try:
            dY = float(self.entry_a_dy.get()); v = float(self.entry_a_v.get()); L = float(self.entry_a_l.get())
            if v <= 0:
                warn('v'); return
            if L < 0 or L > 1000:
                warn('L'); return
        except ValueError:
            error('num'); return
        L_nm = L * 1e6; Lambda = v / FREQ * 1000.0
        kappa = 8.699999999999998e-08 * exp(-(dY - Y_OPT) ** 2 / 8)
        wl_min, wl_max = self.get_wl_limits()
        wl = array(linspace(wl_min, wl_max, 50000), dtype=complex)
        kappa = kappa * (1550 / wl)
        T = abs(spectrum(wl, Lambda, kappa, L_nm)) ** 2 + 1e-06
        T_db = log10(gaussian_filter1d(T, 4)) * 10
        self._show('a', wl, T_db, wl_min, wl_max, relim=True)

    # C
    def setup_tab_c(self):
        ctrl, (self.entry_c_t,) = self._panel(self.tab_c, 'Temperature', [('T (°C):', '100.0')])
        ttk.Button(ctrl, text='Calculate and plot', command=self.plot_part_c).grid(row=1, column=0, columnspan=2, pady=20, sticky=tk.EW)
        self._plot(self.tab_c, 'c'); self.plot_part_c()

    def plot_part_c(self):
        try:
            temp = float(self.entry_c_t.get())
            if temp < 25.0 or temp > 100:
                error('T'); return
        except ValueError:
            error('num'); return
        v, L, dY = 0.536, 50.0, 0.0
        L_nm = L * 1e6; Lambda = v / FREQ * 1000.0 * (1 + (temp - 25) * A_temp_exp)
        kappa = 8.699999999999998e-08 * exp(-(dY - Y_OPT) ** 2 / 8)
        wl_min, wl_max = self.get_wl_limits()
        wl = array(linspace(wl_min, wl_max, 50000), dtype=complex)
        kappa = kappa * (1550 / wl)
        T = abs(spectrum(wl, Lambda, kappa, L_nm)) ** 2 + 1e-06
        self._show('c', wl, log10(gaussian_filter1d(T, 4)) * 10, wl_min, wl_max)

    # D
    def run_cooling_simulation(self):
        c_Ts = linspace(50, 150, 100)
        c_HFs = HF_BASE + HF_DELTA * exp(-(c_Ts - T_solid) ** 2 / 50)
        alpha = 0.01; curT = 150.0
        self.Ts_history = []
        while curT > 50:
            curHF = interp(curT, c_Ts, c_HFs)
            curT = curT - alpha * (curT - 25) / curHF
            self.Ts_history.append(curT)
        step = int(len(self.Ts_history) / 40)
        self.T_history_cut = self.Ts_history[::step]
        self.max_t = len(self.T_history_cut)

    def setup_tab_d(self):
        self.run_cooling_simulation(); self.processed_d = False
        ctrl = ttk.LabelFrame(self.tab_d, text='Select point in time', padding=15)
        ctrl.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        ttk.Label(ctrl, text='Time (min):').grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 2))
        sub = ttk.Frame(ctrl); sub.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        self.btn_dec = ttk.Button(sub, text='-1', width=3, command=self.decrement_time); self.btn_dec.pack(side=tk.LEFT, padx=2)
        self.entry_d_time = ttk.Entry(sub, width=8, justify=tk.CENTER); self.entry_d_time.insert(0, '0')
        self.entry_d_time.pack(side=tk.LEFT, padx=2)
        self.btn_inc = ttk.Button(sub, text='+1', width=3, command=self.increment_time); self.btn_inc.pack(side=tk.LEFT, padx=2)
        self.lbl_d_info = ttk.Label(ctrl, text='', justify=tk.LEFT, font=('Arial', 9, 'bold'))
        self.lbl_d_info.grid(row=3, column=0, columnspan=2, pady=10, sticky=tk.W)
        self.entry_d_time.bind('<Return>', lambda _: self.plot_part_d_call())
        self.entry_d_time.bind('<FocusOut>', lambda _: self.plot_part_d_call())
        self._plot(self.tab_d, 'd'); self.update_info(0.0); self.plot_part_d()

    def increment_time(self):
        try:
            val = int(float(self.entry_d_time.get()))
            if val == self.max_t - 1: return
        except ValueError:
            val = 0
        val = min(self.max_t, val + 1)
        self.entry_d_time.delete(0, tk.END); self.entry_d_time.insert(0, str(val)); self.plot_part_d()

    def decrement_time(self):
        try:
            val = int(float(self.entry_d_time.get()))
            if val == 0: return
        except ValueError:
            val = 0
        val = max(0, val - 1)
        self.entry_d_time.delete(0, tk.END); self.entry_d_time.insert(0, str(val)); self.plot_part_d()

    def update_info(self, val):
        try: val = int(float(val))
        except ValueError: val = 0
        self.lbl_d_info.config(text=f'Selected: {val:.1f}/{self.max_t - 1:.1f} min')

    def plot_part_d_call(self):
        if self.processed_d: return
        self.processed_d = True; self.plot_part_d(); self.processed_d = False

    def plot_part_d(self):
        try:
            target_t = int(float(self.entry_d_time.get()))
            if target_t > self.max_t - 1:
                target_t = self.max_t - 1
                warn('frame', self.max_t - 1)
            elif target_t < 0:
                target_t = 0
                warn('frame', 0)
        except ValueError:
            target_t = 0
        self.entry_d_time.delete(0, tk.END); self.entry_d_time.insert(0, str(target_t))
        T_sel = self.T_history_cut[target_t]
        self.update_info(target_t)
        v, L, dY = 0.536, 50.0, 0.0
        L_nm = L * 1e6; Lambda = v / FREQ * 1000.0 * (1 + (T_sel - 25) * A_temp_exp)
        kappa = 8.699999999999998e-08 * exp(-(dY - Y_OPT) ** 2 / 8)
        wl_min, wl_max = self.get_wl_limits()
        wl = array(linspace(wl_min, wl_max, 50000), dtype=complex)
        kappa = kappa * (1550 / wl) * (1 - (T_sel - 25) / 5000)
        delta = n_c * 2 * pi / wl - pi / Lambda
        gamma = sqrt(kappa ** 2 - delta ** 2)
        random.seed(0)
        t = gamma / (gamma * cosh(gamma * L_nm) - 1j * delta * sinh(gamma * L_nm)) * (random.rand(len(wl)) * 0.2 + 0.9)
        T = abs(t) ** 2 + 1e-06
        self._show('d', wl, log10(gaussian_filter1d(T, 4)) * 10, wl_min, wl_max, title=f't = {target_t:.2f} min')

    # E.I
    def setup_tab_e1(self):
        ctrl, (self.entry_e1_f,) = self._panel(self.tab_e1, ' Force ', [('F (mN):', '0')])
        ttk.Button(ctrl, text='Calculate and plot', command=self.plot_part_e1).grid(row=1, column=0, columnspan=2, pady=20, sticky=tk.EW)
        self._plot(self.tab_e1, 'e1'); self.plot_part_e1()

    def plot_part_e1(self):
        try:
            F = float(self.entry_e1_f.get())
            if F > 20 or F < 0:
                warn('F'); return
        except ValueError:
            error('num'); return
        self._force('e1', F)

    def _force(self, key, F):
        v, L, dY = 0.536, 50.0, 0.0
        L_nm = L * 1e6; Lambda = v / FREQ * 1000.0 * (1 + F * 2.7e-05)
        kappa = 8.699999999999998e-08 * exp(-(dY - Y_OPT) ** 2 / 8)
        wl_min, wl_max = self.get_wl_limits()
        wl = array(linspace(wl_min, wl_max, 50000), dtype=complex)
        kappa = kappa * (1550 / wl)
        T = abs(spectrum(wl, Lambda, kappa, L_nm)) ** 2 + 1e-06
        self._show(key, wl, log10(gaussian_filter1d(T, 4)) * 10, wl_min, wl_max)

    # E.II
    def setup_tab_e2(self):
        ctrl, (self.entry_e2_x,) = self._panel(self.tab_e2, ' Displacement ', [('x (mm):', '0')])
        ttk.Button(ctrl, text='Calculate and plot', command=self.plot_part_e2).grid(row=1, column=0, columnspan=2, pady=20, sticky=tk.EW)
        self._plot(self.tab_e2, 'e2'); self.plot_part_e2()

    def plot_part_e2(self):
        try:
            x = float(self.entry_e2_x.get())
            if x > 10 or x < 0:
                warn('x'); return
        except ValueError:
            error('num'); return
        F = 2.5 * x if x < 7 else 0.5 * x ** 2 - 4.5 * x + 24.5
        self._force('e2', F)

    # F
    def setup_tab_f(self):
        ctrl, (self.entry_f_theta,) = self._panel(self.tab_f, 'Polarization', [('θ (°):', '0')])
        ttk.Button(ctrl, text='Calculate and plot', command=self.plot_part_f).grid(row=1, column=0, columnspan=2, pady=20, sticky=tk.EW)
        self._plot(self.tab_f, 'f'); self.plot_part_f()

    def plot_part_f(self):
        try:
            theta = float(self.entry_f_theta.get())
        except ValueError:
            error('num'); return
        v, L = 0.536, 50.0
        L_nm = L * 1e6; dn = 1e-05; Lambda = v / FREQ * 1000.0
        kappa1, kappa2 = 8.699999999999998e-08, 6.089999999999998e-08
        wl_min, wl_max = self.get_wl_limits()
        wl = array(linspace(wl_min, wl_max, 50000), dtype=complex)
        kappa1 = kappa1 * (1550 / wl); kappa2 = kappa2 * (1550 / wl)
        delta1 = n_c * 2 * pi / wl - pi / Lambda
        delta2 = (1 - dn) * n_c * 2 * pi / wl - pi / Lambda
        gamma1 = sqrt(kappa1 ** 2 - delta1 ** 2); gamma2 = sqrt(kappa2 ** 2 - delta2 ** 2)
        th = (theta - THETA_OPT) / 180 * pi
        t1 = gamma1 / (gamma1 * cosh(gamma1 * L_nm) - 1j * delta1 * sinh(gamma1 * L_nm)) * (random.rand(len(wl)) * 0.2 + 0.9)
        t2 = gamma2 / (gamma2 * cosh(gamma2 * L_nm) - 1j * delta2 * sinh(gamma2 * L_nm)) * (random.rand(len(wl)) * 0.2 + 0.9)
        T = abs(t1) ** 2 * cos(th) ** 2 + abs(t2) ** 2 * sin(th) ** 2 + 1e-06
        self._show('f', wl, log10(gaussian_filter1d(T, 4)) * 10, wl_min, wl_max)


if __name__ == '__main__':
    app = FBGApp()
    app.mainloop()
