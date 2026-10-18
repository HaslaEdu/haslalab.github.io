#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=======================================================================
  9th Asian Physics Olympiad  (APhO 2008, Ulaanbaatar, Mongolia)
  Experimental Problem :  THE PHYSICS OF SOUND WAVES
  Virtual laboratory simulator
-----------------------------------------------------------------------
  HaslaLab  /  HaslaEdu        https://haslalab.org
-----------------------------------------------------------------------
Design rules
------------
* Part 1: source and microphone are resonant transducers (hidden f0, Q);
  the source beams like a piston, |2 J1(ka sin phi)/(ka sin phi)|.
* Part 2: on the optical bench the microphone signal is the complex sum of
  the direct wave, the mirror's echo and the multiple reflections between
  mirror and source face, so standing-wave maxima repeat every lambda/2
  whether you move the detector or the mirror (positions A and B).
* Part 3: the echo off the saw-toothed disc is Doppler-shifted; the motor's
  speed follows its own hidden law, tabulated on its specification sheet.
* Part 4: real tones.  A short WAV burst at the generator frequency and
  level is written and played with the system player (winsound on Windows,
  afplay on macOS, aplay/paplay on Linux) -- your own ears decide.
* The millivoltmeter is analog: you read the needle and the range.
* Hidden truths are randomised every session.  Standard library only.

    Run:   python3 apho2008_sim_KO.py
"""

import math
import os
import random
import struct
import subprocess
import sys
import tempfile
import tkinter as tk
import wave
from tkinter import ttk

LANG = "ko"          # the EN edition differs only in this line

RANGES = [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100]


def j1(x):
    s, t = 0.0, x / 2
    for k in range(20):
        s += t
        t *= -(x * x / 4) / ((k + 1) * (k + 2))
    return s


# --------------------------------------------------------------------------
#  Physics core  (SI)
# --------------------------------------------------------------------------
class Physics(object):
    def __init__(self, seed=None):
        r = random.Random(seed)
        self.Tair = r.uniform(18, 25)
        self.c = 331.3 * math.sqrt(1 + self.Tair / 273.15)
        self.fS, self.QS = r.uniform(39.4, 40.8) * 1e3, r.uniform(16, 22)
        self.fD, self.QD = r.uniform(39.4, 40.8) * 1e3, r.uniform(16, 22)
        self.gain, self.ka = r.uniform(0.9, 1.1), r.uniform(3.3, 4.0)
        self.Rm, self.Rs, self.leak = r.uniform(0.85, 0.93), r.uniform(0.25, 0.35), r.uniform(0.04, 0.08)
        self.U0, self.kw = r.uniform(1.3, 1.9), r.uniform(2.4, 2.8)
        self.I0, self.kI = r.uniform(0.10, 0.14), r.uniform(0.004, 0.006)
        self.N, self.dl = 36, 4.37e-3
        self.spec = [(U, self.I(U) * (1 + r.uniform(-0.005, 0.005)), self.omega(U) * (1 + r.uniform(-0.004, 0.004))) for U in (4, 6, 8, 10, 12, 14, 16)]
        self.Omega = 0.0

    def omega(self, U):
        return self.kw * (U - self.U0) * (1 - 0.012 * (U - self.U0)) if U > self.U0 else 0.0

    def I(self, U):
        return self.I0 + self.kI * self.omega(U) + 0.01 * U / 16 if U > 0.2 else 0.0

    @staticmethod
    def reso(f, f0, Q):
        return 1 / math.sqrt(1 + Q * Q * (f / f0 - f0 / f) ** 2)

    def beam(self, phi, f):
        x = self.ka * (f / 40e3) * math.sin(phi)
        return 1.0 if abs(x) < 1e-6 else abs(2 * j1(x) / x)

    def det_v(self, b):
        """b: the bench state; returns the microphone voltage, V rms"""
        vin = min(b.ampl, 1.2 + 0.25 * math.tanh((b.ampl - 1.2) / 0.25)) if (b.out and not b.to_phones) else 0.0
        if not vin:
            return 0.0
        f = b.f
        G = 0.012 * self.gain * self.reso(f, self.fS, self.QS) * self.reso(f, self.fD, self.QD) * vin
        ws, wd = b.where_s.get(), b.where_d.get()
        nz = 0.00015 * random.random()
        if ws == "rot" and wd == "rot":
            return G * self.beam(b.phi * math.pi / 180, f) / 0.2 * 0.2 + nz
        if ws == "rail" and wd == "rail":
            k = 2 * math.pi * f / self.c
            xs, xd, xm = b.xs.get(), b.xd.get(), b.xm.get()
            L = max(0.005, (xm - xs) / 1000.0)
            hasM = b.mirror.get() and xm > xs
            rr = self.Rm * self.Rs if hasM else 0.0
            z = 0j
            if xd > xs:
                if hasM and xd >= xm:
                    return nz
                d1 = max(0.004, (xd - xs) / 1000.0)
                for n in range(14):
                    g = rr ** n
                    z += g / (d1 + 2 * n * L) * complex(math.cos(k * (d1 + 2 * n * L)), math.sin(k * (d1 + 2 * n * L)))
                    if hasM:
                        p = 2 * L - d1 + 2 * n * L
                        z += self.Rm * g / p * complex(math.cos(k * p), math.sin(k * p))
            else:
                dB = max(0.01, (xs - xd) / 1000.0)
                z += self.leak / dB * complex(math.cos(k * dB + math.pi), math.sin(k * dB + math.pi))
                if hasM:
                    for n in range(14):
                        g = self.Rm * rr ** n * (1 - self.Rs) * 0.55
                        p = 2 * L + dB + 2 * n * L
                        z += g / p * complex(math.cos(k * p), math.sin(k * p))
            return G * 0.2 * abs(z) * 0.6 + nz
        if ws == "disk" and wd == "disk":
            return G * 0.45 / 0.12 * 0.2 + nz
        return nz

    def counter(self, b):
        if b.det_v() < 0.004:
            return None
        if b.where_s.get() == "disk" and b.where_d.get() == "disk" and self.Omega > 0:
            v = self.Omega * self.dl * self.N / (2 * math.pi)
            return b.f * (self.c + v) / (self.c - v)
        return b.f


def play_tone(freq, level, dur=0.8):
    """write a short sine burst and hand it to the system's player"""
    level = max(0.0, min(0.3, level))
    rate = 44100
    path = os.path.join(tempfile.gettempdir(), "haslalab_tone.wav")
    w = wave.open(path, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    n = int(rate * dur)
    frames = bytearray()
    for i in range(n):
        env = min(1.0, i / 2000.0, (n - i) / 2000.0)
        frames += struct.pack("<h", int(32767 * level * env * math.sin(2 * math.pi * freq * i / rate)))
    w.writeframes(bytes(frames))
    w.close()
    try:
        if sys.platform.startswith("win"):
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        elif sys.platform == "darwin":
            subprocess.Popen(["afplay", path])
        else:
            for player in (["paplay", path], ["aplay", "-q", path]):
                try:
                    subprocess.Popen(player)
                    break
                except OSError:
                    continue
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------
#  Parts and their drawings (assembly tab)
# --------------------------------------------------------------------------
def box_art(col, disp=None):
    def art(cv, x, y, s=1.0):
        cv.create_rectangle(x - 34 * s, y - 22 * s, x + 34 * s, y + 22 * s, fill=col, outline="#777")
        if disp:
            cv.create_rectangle(x - 26 * s, y - 14 * s, x + 4 * s, y - 2 * s, fill=disp, outline="")
    return art


def art_rail(cv, x, y, s=1.0):
    cv.create_rectangle(x - 300 * s, y - 8 * s, x + 300 * s, y + 8 * s, fill="#8a9097", outline="#555")


def art_tr(col):
    def art(cv, x, y, s=1.0):
        cv.create_rectangle(x - 3 * s, y - 10 * s, x + 3 * s, y + 30 * s, fill="#9aa0a6", outline="")
        cv.create_rectangle(x - 12 * s, y - 26 * s, x + 12 * s, y - 10 * s, fill="#c3c8cd", outline="#555")
        cv.create_rectangle(x - 12 * s, y - 20 * s, x + 12 * s, y - 16 * s, fill=col, outline="")
    return art


def art_mirror(cv, x, y, s=1.0):
    cv.create_rectangle(x - 3 * s, y - 30 * s, x + 3 * s, y + 20 * s, fill="#dfe4e8", outline="#888")


def art_rot(cv, x, y, s=1.0):
    cv.create_oval(x - 30 * s, y - 30 * s, x + 30 * s, y + 30 * s, fill="#f2f0e8", outline="#999")
    cv.create_line(x, y, x + 20 * s, y - 20 * s, width=3)


def art_disk(cv, x, y, s=1.0):
    cv.create_oval(x - 30 * s, y - 30 * s, x + 30 * s, y + 30 * s, fill="#2b2e33", outline="#888")


def art_phones(cv, x, y, s=1.0):
    cv.create_arc(x - 24 * s, y - 20 * s, x + 24 * s, y + 24 * s, start=0, extent=180, style="arc", width=3)
    cv.create_rectangle(x - 28 * s, y, x - 16 * s, y + 18 * s, fill="#1f2226")
    cv.create_rectangle(x + 16 * s, y, x + 28 * s, y + 18 * s, fill="#1f2226")


ART = {"fg": box_art("#e3e5e8", "#0d1f12"), "amp": box_art("#2b2e33"), "mv": box_art("#d8d4c4"), "fc": box_art("#2e3237", "#0d1f12"),
       "dc": box_art("#d9dcdf", "#0d1f12"), "rail": art_rail, "src": art_tr("#c0392b"), "det": art_tr("#2b6cb0"), "mirror": art_mirror,
       "rot": art_rot, "disk": art_disk, "phones": art_phones}
PARTS = [
    ("fg", ("[A] 함수 발생기", "[A] Function generator"), []),
    ("amp", ("[B] 초음파 증폭기", "[B] Ultrasonic amplifier"), ["fg"]),
    ("mv", ("[C] 교류 밀리볼트계", "[C] AC millivoltmeter"), []),
    ("fc", ("[D] 주파수 계수기", "[D] Frequency counter"), []),
    ("dc", ("[E] 가변 직류 전원", "[E] Variable DC supply"), []),
    ("rail", ("[R] 광학 레일", "[R] Optical bench"), []),
    ("src", ("[F] 초음파 송신기 (빨강)", "[F] Ultrasonic source (red)"), ["amp"]),
    ("det", ("[G] 초음파 마이크 (파랑)", "[G] Ultrasonic microphone (blue)"), ["mv"]),
    ("mirror", ("[J,K] 거울 + 자석 받침", "[J,K] Mirror + magnetic holder"), ["rail"]),
    ("rot", ("[O] 회전 받침", "[O] Rotating holder"), []),
    ("disk", ("[L,M] 회전 원판 + 모터", "[L,M] Disc + motor"), ["dc"]),
    ("phones", ("[P,T] 헤드폰 + 가변저항", "[P,T] Headphones + rheostat"), ["fg"]),
]
ZONES = {"fg": (150, 120, 70, 46), "amp": (250, 120, 70, 46), "mv": (350, 120, 70, 46), "fc": (450, 120, 70, 46), "dc": (550, 120, 70, 46),
         "rail": (380, 440, 600, 18), "src": (250, 400, 26, 60), "det": (350, 400, 26, 60), "mirror": (480, 400, 10, 54),
         "rot": (650, 260, 62, 62), "disk": (130, 300, 62, 62), "phones": (520, 260, 60, 44)}
SCENE_TITLE = ("그림 1 — 실험 장치와 재료", "Figure 1 — apparatus and materials")
APP_TITLE = ("APhO 2008 실험 — 음파의 물리", "APhO 2008 Experiment — The physics of sound waves")


# --------------------------------------------------------------------------
#  Bench tab
# --------------------------------------------------------------------------
class BenchTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.ph = app.ph
        self.f, self.ampl, self.out, self.to_phones = 40000.0, 1.0, False, False
        self.rng, self.mv_on, self.fc_on, self.needle = 10, False, False, 0.0
        self.U, self.dc_on, self.phi, self.vol = 0.0, False, 0, 0.5
        self.where_s, self.where_d = tk.StringVar(value="rot"), tk.StringVar(value="rot")
        self.xs, self.xd, self.xm = tk.DoubleVar(value=150), tk.DoubleVar(value=300), tk.DoubleVar(value=400)
        self.mirror = tk.BooleanVar(value=False)
        self.build()
        self.refresh()

    def det_v(self):
        if not {"src", "det"} <= self.app.placed:
            return 0.0
        return self.ph.det_v(self)

    def meter_v(self):
        if not self.mv_on:
            return 0.0
        if self.to_phones:
            return self.ampl * self.vol ** 1.6 * 0.5 if self.out else 0.0
        return self.det_v()

    def build(self):
        ctl = ttk.Frame(self)
        ctl.pack(side="left", fill="y", padx=6, pady=6)
        f = ttk.LabelFrame(ctl, text=T("함수 발생기", "Function generator"))
        f.pack(fill="x", pady=2)
        self.dF = tk.Label(f, text="", font=("Courier", 16, "bold"), bg="#0d1f12", fg="#5cff7a", width=14)
        self.dF.pack()
        stepper(f, "f (Hz)", [("−1k", lambda: self.setf(-1000)), ("−100", lambda: self.setf(-100)), ("−10", lambda: self.setf(-10)), ("−1", lambda: self.setf(-1))])
        stepper(f, "", [("+1", lambda: self.setf(1)), ("+10", lambda: self.setf(10)), ("+100", lambda: self.setf(100)), ("+1k", lambda: self.setf(1000))])
        stepper(f, "AMPL (V)", [("−0.1", lambda: self.seta(-0.1)), ("−0.01", lambda: self.seta(-0.01)), ("+0.01", lambda: self.seta(0.01)), ("+0.1", lambda: self.seta(0.1))])
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.out_btn = ttk.Button(row, text="", command=self.toggle_out)
        self.out_btn.pack(side="left", padx=2)
        self.route_btn = ttk.Button(row, text="", command=self.toggle_route)
        self.route_btn.pack(side="left", padx=2)
        f = ttk.LabelFrame(ctl, text=T("밀리볼트계 · 계수기 · 직류 전원", "Millivoltmeter · counter · DC supply"))
        f.pack(fill="x", pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("밀리볼트계 켜기/끄기", "MV on/off"), command=self.toggle_mv).pack(side="left", padx=2)
        ttk.Button(row, text="RANGE ◀", command=lambda: self.setr(-1)).pack(side="left")
        ttk.Button(row, text="RANGE ▶", command=lambda: self.setr(1)).pack(side="left")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text=T("계수기 켜기/끄기", "Counter on/off"), command=self.toggle_fc).pack(side="left", padx=2)
        ttk.Button(row, text=T("모터 전원 켜기/끄기", "Motor on/off"), command=self.toggle_dc).pack(side="left", padx=2)
        stepper(f, "U (V)", [("−1", lambda: self.setu(-1)), ("−0.1", lambda: self.setu(-0.1)), ("+0.1", lambda: self.setu(0.1)), ("+1", lambda: self.setu(1))])
        f = ttk.LabelFrame(ctl, text=T("송신기 · 마이크 위치", "Source · microphone"))
        f.pack(fill="x", pady=2)
        for lab, var in ((T("송신기", "source"), self.where_s), (T("마이크", "microphone"), self.where_d)):
            row = ttk.Frame(f)
            row.pack(fill="x")
            ttk.Label(row, text=lab, width=8).pack(side="left")
            for v, l in (("rot", T("회전 받침", "holder")), ("rail", T("레일", "rail")), ("disk", T("원판", "disc"))):
                ttk.Radiobutton(row, text=l, value=v, variable=var).pack(side="left")
        stepper(f, T("각도", "angle"), [("−5°", lambda: self.setphi(-5)), ("−1°", lambda: self.setphi(-1)), ("+1°", lambda: self.setphi(1)), ("+5°", lambda: self.setphi(5))])
        ttk.Checkbutton(f, text=T("거울을 레일에", "Mirror on the rail"), variable=self.mirror).pack(anchor="w")
        for lab, var in (("S (mm)", self.xs), ("D (mm)", self.xd), ("M (mm)", self.xm)):
            row = ttk.Frame(f)
            row.pack(fill="x")
            ttk.Label(row, text=lab, width=8).pack(side="left")
            ttk.Spinbox(row, from_=0, to=600, increment=0.5, textvariable=var, width=8).pack(side="left")
        f = ttk.LabelFrame(ctl, text=T("헤드폰 (4부 — 실제 소리)", "Headphones (part 4 — real sound)"))
        f.pack(fill="x", pady=2)
        stepper(f, T("볼륨", "volume"), [("−", lambda: self.setvol(-0.02)), ("+", lambda: self.setvol(0.02))])
        ttk.Button(f, text=T("소리 들어 보기 (0.8 s)", "Listen (0.8 s)"), command=self.listen).pack(anchor="w", padx=2)
        self.warn = ttk.Label(ctl, text="", foreground="#8a1b1b", wraplength=380)
        self.warn.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.cv = tk.Canvas(right, width=860, height=700, bg="#2a2d33", highlightthickness=0)
        self.cv.pack()

    def setf(self, d):
        self.f = max(1.0, min(99999.9, round(self.f + d, 1)))

    def seta(self, d):
        self.ampl = max(0.0, min(5.0, round(self.ampl + d, 2)))

    def toggle_out(self):
        if "fg" in self.app.placed:
            self.out = not self.out

    def toggle_route(self):
        if "phones" in self.app.placed:
            self.to_phones = not self.to_phones

    def toggle_mv(self):
        if "mv" in self.app.placed:
            self.mv_on = not self.mv_on
            if self.mv_on:
                self.rng = 10

    def setr(self, d):
        self.rng = max(0, min(len(RANGES) - 1, self.rng + d))

    def toggle_fc(self):
        if "fc" in self.app.placed:
            self.fc_on = not self.fc_on

    def toggle_dc(self):
        if {"dc", "disk"} <= self.app.placed:
            self.dc_on = not self.dc_on

    def setu(self, d):
        self.U = max(0.0, min(16.0, round(self.U + d, 1)))

    def setphi(self, d):
        self.phi = max(-90, min(90, self.phi + d))

    def setvol(self, d):
        self.vol = max(0.0, min(1.0, round(self.vol + d, 2)))

    def listen(self):
        if not (self.to_phones and self.out and "phones" in self.app.placed):
            self.warn.config(text=T("출력을 헤드폰으로 돌리고 켜세요.", "Route the output to the headphones and switch it on."))
            return
        v = self.ampl * self.vol ** 1.6 * 0.5
        if not play_tone(min(20000, self.f), 0.12 * v):
            self.warn.config(text=T("이 컴퓨터에서는 소리를 낼 수 없습니다.", "Cannot play sound on this computer."))

    def tick(self, dt):
        target = self.ph.omega(self.U) if self.dc_on else 0.0
        self.ph.Omega += (target - self.ph.Omega) * min(1, dt / 1.2)
        V = self.meter_v()
        tgt = min(1.08, V / RANGES[self.rng]) if self.mv_on else 0.0
        self.needle += (tgt - self.needle) * min(1, dt / 0.35)
        self.refresh()

    def fg_text(self):
        if not self.out:
            return "OFF"
        return ("%.3f kHz" % (self.f / 1000)) if self.f >= 1000 else ("%.1f Hz" % self.f)

    def refresh(self):
        self.dF.config(text=self.fg_text() if "fg" in self.app.placed else "")
        self.out_btn.config(text=T("출력 끄기", "Output off") if self.out else T("출력 켜기", "Output on"))
        self.route_btn.config(text=T("출력 → 헤드폰", "Output → phones") if self.to_phones else T("출력 → 송신기", "Output → source"))
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        # the analog millivoltmeter
        mx, my, R = 210, 250, 170
        cv.create_rectangle(mx - 200, my - 190, mx + 200, my + 70, fill="#f6f3e6", outline="#999")
        for rr, top in ((R * 0.92, 10), (R * 0.74, 3)):
            n = 50 if top == 10 else 60
            for i in range(n + 1):
                v = i / float(n)
                a = -math.pi * 0.75 + v * math.pi * 0.5
                maj = (i % 5 == 0) if top == 10 else (i % 10 == 0)
                l = 10 if maj else 5
                cv.create_line(mx + rr * math.cos(a), my + rr * math.sin(a), mx + (rr + l) * math.cos(a), my + (rr + l) * math.sin(a), fill="#222")
                if maj:
                    lab = str(i // 5) if top == 10 else ("%g" % (i / 20.0))
                    off = 20 if top == 10 else -12
                    cv.create_text(mx + (rr + off) * math.cos(a), my + (rr + off) * math.sin(a), text=lab, font=("Helvetica", 8))
        a = -math.pi * 0.75 + min(1.08, self.needle) * math.pi * 0.5
        cv.create_line(mx, my, mx + R * math.cos(a), my + R * math.sin(a), width=2)
        rv = RANGES[self.rng]
        cv.create_text(mx, my + 30, text=T("범위: ", "range: ") + (("%g V" % rv) if rv >= 1 else ("%g mV" % (rv * 1000))) + ("" if self.mv_on else T("  (꺼짐)", "  (off)")), font=("Helvetica", 11, "bold"))
        # counter, dc supply
        cf = self.ph.counter(self) if (self.fc_on and "fc" in self.app.placed) else False
        txt = "" if cf is False else ("- - - - -" if cf is None else "%.0f Hz" % cf)
        cv.create_text(450, 80, anchor="w", text=T("주파수 계수기", "Frequency counter"), fill="#c9d1d8", font=("Helvetica", 10, "bold"))
        cv.create_rectangle(450, 92, 840, 140, fill="#0d1f12")
        cv.create_text(830, 116, anchor="e", text=txt, fill="#5cff7a", font=("Courier", 18, "bold"))
        cv.create_text(450, 170, anchor="w", text=T("직류 전원", "DC supply"), fill="#c9d1d8", font=("Helvetica", 10, "bold"))
        cv.create_rectangle(450, 182, 840, 230, fill="#0d1f12")
        if self.dc_on:
            cv.create_text(830, 206, anchor="e", text="%.1f V   %.3f A" % (self.U, self.ph.I(self.U)), fill="#ffb347", font=("Courier", 16, "bold"))
        # the rail from above
        y0, X = 400, lambda mm: 30 + mm / 600.0 * 800
        if "rail" in self.app.placed:
            cv.create_rectangle(X(0), y0 - 20, X(600), y0 + 20, fill="#8a9097")
            cv.create_rectangle(X(0), y0 + 20, X(600), y0 + 40, fill="#f0ead2")
            for mm in range(0, 601, 5):
                cv.create_line(X(mm), y0 + 20, X(mm), y0 + 20 + (12 if mm % 50 == 0 else 7 if mm % 10 == 0 else 4), fill="#222")
                if mm % 50 == 0:
                    cv.create_text(X(mm), y0 + 34, text=str(mm // 10), font=("Helvetica", 7))
            for var, wh, col, lab in ((self.xs, self.where_s, "#ff6b5b", "S"), (self.xd, self.where_d, "#5aa9ff", "D")):
                if wh.get() == "rail":
                    cv.create_rectangle(X(var.get()) - 6, y0 - 16, X(var.get()) + 6, y0 + 16, fill="#2b2e33", outline=col, width=2)
                    cv.create_text(X(var.get()), y0 - 26, text=lab, fill=col, font=("Helvetica", 10, "bold"))
            if self.mirror.get():
                cv.create_rectangle(X(self.xm.get()) - 2, y0 - 22, X(self.xm.get()) + 2, y0 + 22, fill="#dfe4e8")
                cv.create_text(X(self.xm.get()), y0 - 28, text="M", fill="#dfe4e8", font=("Helvetica", 10, "bold"))
        # rotating holder
        if "rot" in self.app.placed:
            cx, cy, Rr = 220, 640, 120
            cv.create_arc(cx - Rr, cy - Rr, cx + Rr, cy + Rr, start=0, extent=180, fill="#f2f0e8", outline="")
            for dg in range(-90, 91, 5):
                a = -math.pi / 2 + math.radians(dg)
                l = 12 if dg % 10 == 0 else 6
                cv.create_line(cx + Rr * math.cos(a), cy + Rr * math.sin(a), cx + (Rr - l) * math.cos(a), cy + (Rr - l) * math.sin(a))
                if dg % 30 == 0:
                    cv.create_text(cx + (Rr - 24) * math.cos(a), cy + (Rr - 24) * math.sin(a), text=str(abs(dg)), font=("Helvetica", 8))
            a = -math.pi / 2 + math.radians(self.phi)
            cv.create_line(cx, cy, cx + Rr * 0.85 * math.cos(a), cy + Rr * 0.85 * math.sin(a), width=4, fill="#2b2e33")
        # specification sheet
        x0, y = 470, 480
        cv.create_rectangle(x0 - 10, y - 20, 850, 690, fill="#fbfaf5")
        cv.create_text(x0, y - 6, anchor="w", text=T("모터 사양서 (CW)  N = %d, Δl = 4.37 ± 0.05 mm", "Motor spec (CW)  N = %d, Δl = 4.37 ± 0.05 mm") % self.ph.N, font=("Helvetica", 9, "bold"))
        cv.create_text(x0, y + 14, anchor="w", text="U (V)     I (A)      Ω (rad/s)", font=("Courier", 9, "bold"))
        for i, (U, I, Om) in enumerate(self.ph.spec):
            cv.create_text(x0, y + 32 + i * 18, anchor="w", text="%5.1f    %6.3f     %6.2f" % (U, I, Om), font=("Courier", 9))
        df = 40000 * 2 * (self.ph.omega(10) * self.ph.dl * self.ph.N / (2 * math.pi)) / self.ph.c
        cv.create_text(x0, y + 172, anchor="w", text=T("보정: U = 10.0 V에서 Δf = %.0f Hz (f0 = 40 kHz)", "Calibration: at U = 10.0 V, Δf = %.0f Hz (f0 = 40 kHz)") % df, fill="#7a1c17", font=("Helvetica", 9, "bold"))


def T(ko, en):
    return ko if LANG == "ko" else en


def rr(cv, x0, y0, x1, y1, r, **kw):
    """rounded rectangle on a Tk canvas"""
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


# --------------------------------------------------------------------------
#  Assembly tab: drag each part from the list onto its place, in order
# --------------------------------------------------------------------------
class AssemblyTab(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master)
        self.app = app
        self.placed = set()
        self.drag = None

        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Label(left, text=T("장치 목록", "Apparatus list"),
                  font=("Helvetica", 11, "bold")).pack(anchor="w")
        self.tray = tk.Canvas(left, width=215, height=640, bg="#f2f3f5",
                              highlightthickness=1,
                              highlightbackground="#c3c7cc")
        self.tray.pack()
        self.msg = ttk.Label(left, text="", wraplength=205,
                             foreground="#8a1b1b")
        self.msg.pack(anchor="w", pady=4)

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("조립 구역 — 준비 절차 순서대로 놓으시오",
                                "Assembly area — follow the preparation order"),
                  font=("Helvetica", 11, "bold")).pack(anchor="w")
        self.scene = tk.Canvas(right, width=760, height=640, bg="#e9ebee",
                               highlightthickness=1,
                               highlightbackground="#c3c7cc")
        self.scene.pack(fill="both", expand=True)

        self.tray.bind("<ButtonPress-1>", self.on_press)
        self.tray.bind("<B1-Motion>", self.on_move)
        self.tray.bind("<ButtonRelease-1>", self.on_release)
        self.redraw()

    def redraw(self):
        self.tray.delete("all")
        pitch = min(60, 620 // len(PARTS))     # every part fits in the list
        y, self.slots, self.half = 10 + pitch // 2, [], pitch // 2 - 2
        for key, lab, _ in PARTS:
            if key in self.placed:
                continue
            self.tray.create_rectangle(8, y - self.half, 205, y + self.half,
                                       fill="#ffffff", outline="#d3d7dc")
            ART[key](self.tray, 50, y, 0.5 * pitch / 60.0)
            self.tray.create_text(98, y, text=T(*lab), width=104,
                                  font=("Helvetica", 8), anchor="w")
            self.slots.append((key, y))
            y += pitch
        self.paint_scene()

    def paint_scene(self):
        cv = self.scene
        cv.delete("all")
        cv.create_text(380, 20, text=T(*SCENE_TITLE),
                       font=("Helvetica", 10, "bold"), fill="#4a5058")
        cv.create_rectangle(20, 470, 740, 500, fill="#d6d3c8", outline="")
        for key, (cx, cy, w, h) in ZONES.items():
            if key in self.placed:
                continue
            cv.create_rectangle(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2,
                                dash=(4, 3), outline="#b0b5bb")
        for key, _, _ in PARTS:
            if key in self.placed:
                cx, cy, w, h = ZONES[key]
                ART[key](cv, cx, cy, 1.0)
        if len(self.placed) == len(PARTS):
            cv.create_text(380, 610, fill="#14532d",
                           font=("Helvetica", 11, "bold"),
                           text=T("조립 완료 — '실험대' 탭으로 이동하시오.",
                                  "Assembly complete — go to the Bench tab."))

    def on_press(self, ev):
        self.drag = None
        for key, y in self.slots:
            if abs(ev.y - y) <= self.half:
                self.drag = key
                return

    def on_move(self, ev):
        if not self.drag:
            return
        x = self.tray.winfo_rootx() + ev.x - self.scene.winfo_rootx()
        y = self.tray.winfo_rooty() + ev.y - self.scene.winfo_rooty()
        self.paint_scene()
        ART[self.drag](self.scene, x, y, 0.9)

    def on_release(self, ev):
        if not self.drag:
            return
        key, self.drag = self.drag, None
        x = self.tray.winfo_rootx() + ev.x - self.scene.winfo_rootx()
        y = self.tray.winfo_rooty() + ev.y - self.scene.winfo_rooty()
        self.drop(key, x, y)

    def drop(self, key, x, y):
        cx, cy, w, h = ZONES[key]
        self.msg.config(text="")
        if not (abs(x - cx) < w / 2 + 28 and abs(y - cy) < h / 2 + 28):
            self.msg.config(text=T("그 위치에는 놓을 수 없습니다.",
                                   "That part does not belong there."))
            self.redraw()
            return False
        needs = dict((k, n) for k, _, n in PARTS)[key]
        miss = [n for n in needs if n not in self.placed]
        if miss:
            names = ", ".join(T(*dict((k, l) for k, l, _ in PARTS)[m])
                              for m in miss)
            self.msg.config(text=T("먼저 설치해야 합니다: ",
                                   "Install first: ") + names)
            self.redraw()
            return False
        self.placed.add(key)
        self.app.on_assembly_change(self.placed)
        self.redraw()
        return True


# --------------------------------------------------------------------------
#  Data sheet: what the student typed down, nothing more
# --------------------------------------------------------------------------
class DataSheet(ttk.Frame):
    def __init__(self, master, cols, height=12):
        ttk.Frame.__init__(self, master)
        self.cols = cols
        self.tv = ttk.Treeview(self, columns=[c[0] for c in cols],
                               show="headings", height=height)
        for key, head, wd in cols:
            self.tv.heading(key, text=head)
            self.tv.column(key, width=wd, anchor="center")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")

    def add(self, row):
        self.tv.insert("", "end", values=row)
        self.tv.yview_moveto(1.0)

    def del_last(self):
        kids = self.tv.get_children()
        if kids:
            self.tv.delete(kids[-1])

    def clear(self):
        for k in self.tv.get_children():
            self.tv.delete(k)

    def as_text(self):
        out = ["\t".join(c[1] for c in self.cols)]
        for k in self.tv.get_children():
            out.append("\t".join(str(v) for v in self.tv.item(k, "values")))
        return "\n".join(out)


def sheet_buttons(parent, sheet, app):
    row = ttk.Frame(parent)
    row.pack(fill="x", pady=2)
    ttk.Button(row, text=T("마지막 줄 삭제", "Delete last"),
               command=sheet.del_last).pack(side="left", padx=2)
    ttk.Button(row, text=T("모두 지우기", "Clear"),
               command=sheet.clear).pack(side="left", padx=2)

    def copy():
        app.clipboard_clear()
        app.clipboard_append(sheet.as_text())
    ttk.Button(row, text=T("표 복사", "Copy table"),
               command=copy).pack(side="left", padx=2)


def stepper(parent, label, cmds):
    """a row of buttons: label  [−1] [−0.1] … ; cmds = [(text, fn), …]"""
    row = ttk.Frame(parent)
    row.pack(fill="x", pady=1)
    ttk.Label(row, text=label, width=16).pack(side="left")
    for txt, fn in cmds:
        ttk.Button(row, text=txt, width=max(6, len(txt) + 1), command=fn).pack(side="left", padx=1)
    return row


class App(tk.Tk):
    def __init__(self, seed=None):
        tk.Tk.__init__(self)
        self.ph = Physics(seed)
        self.title(T(*APP_TITLE))
        self.geometry("1360x800")
        self.placed = set()
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_asm = AssemblyTab(nb, self)
        self.tab_bench = BenchTab(nb, self)
        nb.add(self.tab_asm, text=T(" 조립 ", " Assembly "))
        nb.add(self.tab_bench, text=T(" 실험대 ", " Bench "))
        self.after(40, self.tick)

    def on_assembly_change(self, placed):
        self.placed = set(placed)
        self.tab_bench.refresh()

    def tick(self):
        self.tab_bench.tick(0.04)
        self.after(40, self.tick)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
