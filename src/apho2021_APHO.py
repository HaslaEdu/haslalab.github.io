#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APhO 2021 (Taiwan, online) - the experiment program APHO.exe
==============================================================

This is the organisers' Unity program (APHO.exe, Unity 2019.4) for both
experiments of APhO 2021, rebuilt in Python with the same scenes, numbers and
behaviour:

  1 A - 1 D   Elasticity of a cantilever: laser, mirror and PSD on the bench,
              point force (1 B), bimorph heater (1 C), adsorbed samples (1 D)
  2 A         Collimation of the laser on a double slit
  2 B - 2 E   Diffraction by the microsphere sample, lasers of eight wavelengths,
              screen distance 10 - 100 cm, photodetector

The executable's scripts (Assembly-CSharp.dll) were decompiled and carried over
line for line: the beam deflection code (nano_beam_core), the reflected ray
construction, the DOTween laser jitter, the heater, the recorder and every drag,
rotation and button.  The layout, colours, fonts and pictures of the four scenes
are read out of the executable's scene data (embedded below) and drawn into the
1024 x 768 window the way Unity's canvas draws them.

The screen pictures of 2 A - 2 E were not in the released package (its
Addressables bundles are missing), so they are computed from the sample the
official solution describes: close-packed 5.627 um microspheres, 58.6 x 51.0 um
rectangles with the long side at 27 deg on a 250 x 200 um grid, and a double
slit best at (3700, -2900) um.  The photodetector reads grey * 5.5 V.

Start: enter COUNTRY and NAME, press NEXT, choose a program; Back (top left)
returns to the menu.

Needs: Python 3.8+, numpy, Pillow (with ImageTk), tkinter.
HaslaLab - https://haslalab.org
"""
import base64
import decimal
import io
import json
import math
import random
import re
import struct
import sys
import time
import zlib
import tkinter as tk

import numpy as np
from PIL import Image as PILImage, ImageDraw, ImageFont, ImageTk

# ---------------------------------------------------------------- the runtime
# A small runtime for the uGUI scenes of APHO.exe: rect transforms, canvas
# scaling, images, legacy and TextMeshPro text, the event system, DOTween and
# the Physics2D triggers the app uses.  World space is screen pixels with y up,
# exactly as in Unity.

SW, SH, FIXED_DT, MAX_DT = 1024, 768, 0.02, 1.0 / 3


def m_mul(m, n):
    return (m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1],
            m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
            m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5])


def m_inv(m):
    det = m[0] * m[3] - m[1] * m[2]
    return (m[3] / det, -m[1] / det, -m[2] / det, m[0] / det,
            (m[2] * m[5] - m[3] * m[4]) / det, (m[1] * m[4] - m[0] * m[5]) / det)


def m_apply(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


def m_trs(x, y, deg, sx, sy):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return (c * sx, s * sx, -s * sy, c * sy, x, y)


def clamp(v, a, b):
    return a if v < a else b if v > b else v


def clamp01(v):
    return clamp(v, 0.0, 1.0)


def lerp(a, b, t):
    return a + (b - a) * t


class V2(tuple):
    __slots__ = ()

    def __new__(cls, x, y):
        return tuple.__new__(cls, (x, y))

    x = property(lambda s: s[0])
    y = property(lambda s: s[1])


def dist2(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def norm360(z):
    z = math.fmod(z, 360.0)
    return z + 360.0 if z < 0 else z


def fround(v):
    return struct.unpack('f', struct.pack('f', v))[0]


def fmt_fixed(v, n):
    """C# ToString("0.00") / "F2": rounds half away from zero, no "-0.00"."""
    d = decimal.Decimal(repr(float(v))).quantize(decimal.Decimal(1).scaleb(-n), rounding=decimal.ROUND_HALF_EVEN)
    s = ('{:.%df}' % n).format(float(v))
    s = format(d, 'f') if abs(float(d) - float(s)) < 1e-12 else s
    if s.startswith('-') and float(s) == 0:
        s = s[1:]
    return s


def fmt_g(v):
    """float.ToString(): shortest form with 7 significant digits"""
    v = float(v)
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    s = '%.7g' % v
    if 'e' in s:
        return s
    return s.rstrip('0').rstrip('.') if '.' in s else s


class Col(tuple):
    __slots__ = ()

    def __new__(cls, r, g, b, a=1.0):
        return tuple.__new__(cls, (r, g, b, a))

    r = property(lambda s: s[0])
    g = property(lambda s: s[1])
    b = property(lambda s: s[2])
    a = property(lambda s: s[3])

    def with_a(self, a):
        return Col(self[0], self[1], self[2], a)


WHITE, BLACK, CLEAR = Col(1, 1, 1, 1), Col(0, 0, 0, 1), Col(0, 0, 0, 0)


def col_eq(a, b):
    return all(abs(a[i] - b[i]) < 1e-4 for i in range(4))


def col4(c):
    return Col(c[0], c[1], c[2], c[3])


class _U:
    pass


U = _U()
U.time = 0.0
U.fixed_time = 0.0
U.dt = 0.0
U.frame = 0
U.in_fixed = False
U.scene = None
U.persist = []
U.prefs = {}
U.sprites = {}
U.data = None
U.scripts = {}
U.objects = {}
U.tweens = []
U.timers = []
U.next_scene = None
U.pending_start = []
U.contacts = set()
U.fixed_acc = 0.0
U.log = lambda m: None


class Input_:
    def __init__(self):
        self.keys = set()
        self.down = set()
        self.up = set()
        self.mouse = V2(0, 0)
        self.btn_held = False
        self.queue = []


U.input = Input_()


def later(t, f):
    U.timers.append([t, f])


TAGS = {5: 'MainCamera', 20000: 'laser', 20001: 'color_picker'}


class GameObject:
    def __init__(self, d):
        self.id = d['id']
        self.name = d['n']
        self.activeSelf = bool(d['a'])
        self.tag = TAGS.get(d.get('tag', 0), 'Untagged')
        self.parent = None
        self.children = []
        self.comps = []
        self.rt = RectTransform(self, d)

    @property
    def activeInHierarchy(self):
        g = self
        while g:
            if not g.activeSelf:
                return False
            g = g.parent
        return True

    def SetActive(self, v):
        v = bool(v)
        if self.activeSelf == v:
            return
        was = self.activeInHierarchy
        self.activeSelf = v
        now = self.activeInHierarchy
        if was != now:
            self._active_changed(now)

    def _active_changed(self, now):
        for c in self.comps:
            if now:
                if hasattr(c, 'OnEnable'):
                    c.OnEnable()
                if not c._started and hasattr(c, 'Start') and c.enabled:
                    U.pending_start.append(c)
            elif hasattr(c, 'OnDisable'):
                c.OnDisable()
        for ch in self.children:
            if ch.activeSelf:
                ch._active_changed(now)

    def get(self, kind):
        for c in self.comps:
            if c.kind == kind:
                return c
        return None

    @property
    def transform(self):
        return self.rt

    @property
    def gameObject(self):
        return self


class RectTransform:
    kind = 'RectTransform'

    def __init__(self, go, d):
        self.go = go
        if 'rt' in d:
            self.isRect = True
            a = [V2(p[0], p[1]) for p in d['rt']]
            self.anchorMin, self.anchorMax, self.anchoredPosition, self.sizeDelta, self.pivot = a
        else:
            self.isRect = False
            tr = d.get('tr') or [0, 0]
            self.anchorMin = self.anchorMax = V2(0.5, 0.5)
            self.anchoredPosition = V2(tr[0], tr[1])
            self.sizeDelta = V2(0, 0)
            self.pivot = V2(0.5, 0.5)
        self.rotZ = d.get('rz', 0.0)
        sc = d.get('sc') or [1, 1]
        self.localScale = V2(sc[0], sc[1])
        self.canvas = None

    gameObject = property(lambda s: s.go)
    transform = property(lambda s: s)

    @property
    def parentRT(self):
        return self.go.parent.rt if self.go.parent else None

    @property
    def size(self):
        if self.canvas:
            s = self.canvas.scaleFactor()
            return V2(SW / s, SH / s)
        p = self.parentRT
        if not p or not self.isRect:
            return self.sizeDelta
        ps = p.size
        return V2(ps.x * (self.anchorMax.x - self.anchorMin.x) + self.sizeDelta.x,
                  ps.y * (self.anchorMax.y - self.anchorMin.y) + self.sizeDelta.y)

    @property
    def rect(self):
        s = self.size
        return (-self.pivot.x * s.x, -self.pivot.y * s.y, s.x, s.y)

    def localPos(self):
        p = self.parentRT
        if not p or not self.isRect:
            return self.anchoredPosition
        ps, pp = p.size, p.pivot
        ax = -pp.x * ps.x + ps.x * (self.anchorMin.x + (self.anchorMax.x - self.anchorMin.x) * self.pivot.x)
        ay = -pp.y * ps.y + ps.y * (self.anchorMin.y + (self.anchorMax.y - self.anchorMin.y) * self.pivot.y)
        return V2(ax + self.anchoredPosition.x, ay + self.anchoredPosition.y)

    def localMatrix(self):
        if self.canvas:
            s = self.canvas.scaleFactor()
            return (s, 0.0, 0.0, s, SW / 2, SH / 2)
        lp = self.localPos()
        return m_trs(lp.x, lp.y, self.rotZ, self.localScale.x, self.localScale.y)

    @property
    def worldMatrix(self):
        l = self.localMatrix()
        if self.canvas:
            return l
        p = self.parentRT
        return m_mul(p.worldMatrix, l) if p else l

    @property
    def position(self):
        m = self.worldMatrix
        return V2(m[4], m[5])

    @position.setter
    def position(self, w):
        p = self.parentRT
        lp = m_apply(m_inv(p.worldMatrix), w.x, w.y) if p else (w.x, w.y)
        cur = self.localPos()
        self.anchoredPosition = V2(self.anchoredPosition.x + lp[0] - cur.x, self.anchoredPosition.y + lp[1] - cur.y)

    def worldRotZ(self):
        z, t = 0.0, self
        while t:
            z += t.rotZ
            t = t.parentRT
        return z

    @property
    def eulerZ(self):
        return norm360(self.worldRotZ())

    @eulerZ.setter
    def eulerZ(self, z):
        self.rotZ = norm360(z - (self.worldRotZ() - self.rotZ))

    def worldCorners(self):
        m = self.worldMatrix
        x, y, w, h = self.rect
        return [m_apply(m, x, y), m_apply(m, x, y + h), m_apply(m, x + w, y + h), m_apply(m, x + w, y)]

    # Z.UI.Extension
    def SetAnchoredPosX(self, x):
        self.anchoredPosition = V2(x, self.anchoredPosition.y)

    def SetAnchoredPosY(self, y):
        self.anchoredPosition = V2(self.anchoredPosition.x, y)

    def SetAnchoredPosOffsetX(self, x):
        self.SetAnchoredPosX(self.anchoredPosition.x + x)

    def SetAnchoredPosOffsetY(self, y):
        self.SetAnchoredPosY(self.anchoredPosition.y + y)

    def SetRotateZ(self, z):
        self.eulerZ = z

    def SetRotateOffsetZ(self, z):
        self.eulerZ = self.eulerZ + z

    def GetEulerAngleZ(self):
        z = fround(self.eulerZ)
        n = 360 - z
        return n if z > n else -z

    def SetWidth(self, w):
        self.sizeDelta = V2(w, self.sizeDelta.y)

    def SetHeight(self, h):
        self.sizeDelta = V2(self.sizeDelta.x, h)


# ----------------------------------------------------------------- components
class Component:
    def __init__(self, go, d):
        self.go = go
        self.kind = d['k']
        self.enabled = bool(d.get('en', True))
        self._started = False
        self._fields = None

    gameObject = property(lambda s: s.go)
    transform = property(lambda s: s.go.rt)
    rectTransform = property(lambda s: s.go.rt)

    def GetComponent(self, k):
        return self.go.get(k)


class Graphic(Component):
    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.color = col4(d.get('col') or [1, 1, 1, 1])
        self.raycastTarget = bool(d.get('ray', True))
        self.crColor = WHITE
        self.crFade = None

    def CrossFadeColor(self, target, dur):
        if dur <= 0:
            self.crColor = target
            self.crFade = None
            return
        self.crFade = [self.crColor, target, 0.0, dur]

    def tick_fade(self, dt):
        f = self.crFade
        if not f:
            return
        f[2] += dt
        k = clamp01(f[2] / f[3])
        a, b = f[0], f[1]
        self.crColor = Col(*[lerp(a[i], b[i], k) for i in range(4)])
        if k >= 1:
            self.crFade = None

    def DOFade(self, a, dur):
        def set_(v):
            self.color = self.color.with_a(v)
        return tween_to(self, lambda: self.color.a, set_, a, dur)


class Image(Graphic):
    def __init__(self, go, d):
        Graphic.__init__(self, go, d)
        self.sprite = U.sprites.get(d.get('spr')) if d.get('spr') else None
        self.type = d.get('type', 0)
        self.preserveAspect = bool(d.get('aspect'))
        self.fillCenter = d.get('fillCenter', 1) != 0
        self.fillMethod = d.get('fm', 0)
        self.fillAmount = d.get('fa', 1.0)
        self.fillOrigin = d.get('fo', 0)
        self.ppum = d.get('ppum') or 1.0

    def DOFillAmount(self, v, dur):
        def set_(x):
            self.fillAmount = clamp01(x)
        return tween_to(self, lambda: self.fillAmount, set_, v, dur)


class Text(Graphic):
    def __init__(self, go, d):
        Graphic.__init__(self, go, d)
        self.text = d['text']
        self.fontSize = d['size']
        self.fontStyle = d['style']
        self.alignment = d['align']
        self.bestFit = bool(d['best'])
        self.minSize = d['min']
        self.maxSize = d['max']
        self.lineSpacing = d['ls']
        self.hOverflow = d['hov']
        self.vOverflow = d['vov']
        self.font = d.get('font') or 'Arial'

    @property
    def preferredWidth(self):
        return measure_legacy(self, self.text)


class TMPText(Graphic):
    def __init__(self, go, d):
        Graphic.__init__(self, go, d)
        self.color = col4(d['fcol'])
        self.text = d['text']
        self.fontSize = d['size']
        self.fontStyle = d['style']
        self.hAlign = d['h']
        self.vAlign = d['v']
        self.wrap = bool(d['wrap'])
        self.margin = d.get('margin') or [0, 0, 0, 0]

    @property
    def preferredWidth(self):
        return measure_tmp(self, self.text)


class UILineRenderer(Graphic):
    def __init__(self, go, d):
        Graphic.__init__(self, go, d)
        self.Points = [V2(p[0], p[1]) for p in d['pts']]
        self.LineThickness = d['th']

    def SetAllDirty(self):
        pass


class CanvasGroup(Component):
    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.alpha = d['alpha']
        self.interactable = bool(d['inter'])
        self.blocksRaycasts = bool(d['block'])
        self.ignoreParentGroups = bool(d['ignore'])

    def DOFade(self, a, dur):
        def set_(v):
            self.alpha = v
        return tween_to(self, lambda: self.alpha, set_, a, dur)

    def SetActive(self, v):           # ZUIExtension.SetActive(CanvasGroup)
        self.interactable = v
        self.blocksRaycasts = v


class Canvas(Component):
    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.sortingOrder = d.get('sort', 0)
        self.scaler = None

    def scaleFactor(self):
        s = self.scaler
        if not s:
            return 1.0
        lw = math.log2(SW / s['ref'][0])
        lh = math.log2(SH / s['ref'][1])
        return 2 ** lerp(lw, lh, s['match'])


class Mask(Component):
    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.showMaskGraphic = bool(d['show'])


class RectMask2D(Component):
    pass


class BoxCollider2D(Component):
    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.size = V2(*d['size'])
        self.offset = V2(*d['off'])


class Rigidbody2D(Component):
    pass


class LayoutGroup(Component):
    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.d = d


class ContentSizeFitter(Component):
    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.h = d['h']
        self.v = d['v']


class Animator(Component):
    """the photodetector spot's "spot-idle" clip (1 s loop): scale 1 -> 1.1 -> 1
    and alpha 1 -> 0 -> 1, from the clip's Hermite curves"""

    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.t = 0.0

    def update(self, dt):
        self.t = (self.t + dt) % 1.0
        t = self.t
        if t < 0.5:
            s = ((-1.6 * t + 1.2) * t) * t + 1
            a = ((16 * t - 12) * t) * t + 1
        else:
            u = t - 0.5
            s = ((1.6 * u - 1.2) * u) * u + 1.1
            a = ((-16 * u + 12) * u) * u
        self.go.rt.localScale = V2(s, s)
        img = self.go.get('Image')
        if img:
            img.color = img.color.with_a(a)

    def OnEnable(self):
        self.t = 0.0


# ---------------------------------------------------------------- selectables
NORMAL, HIGHLIGHTED, PRESSED, SELECTED, DISABLED = range(5)


class Selectable(Component):
    is_selectable = True

    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self._interactable = bool(d['inter'])
        self.transition = d['trans']
        self.colors = [col4(c) for c in d['cols']]
        self.colorMultiplier = d.get('mul', 1)
        self.fadeDuration = d.get('fade', 0.1)
        self._tg_ref = d.get('tg')
        self.targetGraphic = None
        self.isPointerInside = self.isPointerDown = self.hasSelection = False
        self._state = -1

    def resolve(self):
        self.targetGraphic = resolve_ref(self._tg_ref)
        self.apply_state(True)

    @property
    def interactable(self):
        return self._interactable

    @interactable.setter
    def interactable(self, v):
        self._interactable = bool(v)
        self.apply_state(False)

    def IsInteractable(self):
        if not self._interactable:
            return False
        g = self.go
        while g:
            cg = g.get('CanvasGroup')
            if cg and not cg.interactable:
                return False
            if cg and cg.ignoreParentGroups:
                break
            g = g.parent
        return True

    def current_state(self):
        if not self.IsInteractable():
            return DISABLED
        if self.isPointerDown:
            return PRESSED
        if self.hasSelection:
            return SELECTED
        if self.isPointerInside:
            return HIGHLIGHTED
        return NORMAL

    def apply_state(self, instant):
        s = self.current_state()
        if s == self._state and not instant:
            return
        self._state = s
        if self.transition == 1 and self.targetGraphic:
            c, m = self.colors[s], self.colorMultiplier
            self.targetGraphic.CrossFadeColor(Col(c.r * m, c.g * m, c.b * m, c.a * m), 0 if instant else self.fadeDuration)

    def OnPointerEnter(self, e):
        self.isPointerInside = True
        self.apply_state(False)

    def OnPointerExit(self, e):
        self.isPointerInside = False
        self.apply_state(False)

    def OnPointerDown(self, e):
        if self.IsInteractable():
            U.es.SetSelectedGameObject(self.go)
        self.isPointerDown = True
        self.apply_state(False)

    def OnPointerUp(self, e):
        self.isPointerDown = False
        self.apply_state(False)

    def OnSelect(self):
        self.hasSelection = True
        self.apply_state(False)

    def OnDeselect(self):
        self.hasSelection = False
        self.apply_state(False)

    def OnDisable(self):
        self.isPointerInside = self.isPointerDown = self.hasSelection = False
        self._state = -1
        self.apply_state(True)


class _Event:
    def __init__(self, owner):
        self.owner = owner
        self.listeners = []

    def Invoke(self):
        self.owner.press()


class Button(Selectable):
    def __init__(self, go, d):
        Selectable.__init__(self, go, d)
        self.calls = d.get('onclick') or []
        self.onClick = _Event(self)

    def resolve(self):
        Selectable.resolve(self)
        for c in self.calls:
            c['target'] = resolve_ref(c['t'])

    def press(self):
        if not self.go.activeInHierarchy or not self.IsInteractable():
            return
        invoke_calls(self.calls)
        for f in self.onClick.listeners:
            f()

    def OnPointerClick(self, e):
        self.press()


class InputField(Selectable):
    """the legacy InputField of the start screen (single line, caret at the end)"""

    def __init__(self, go, d):
        Selectable.__init__(self, go, d)
        self._text = d.get('text') or ''
        self._text_ref = d.get('textc')
        self._ph_ref = d.get('ph')
        self.limit = d.get('limit') or 0
        self.caretColor = col4(d['caret'])
        self.caretWidth = d.get('cw') or 1
        self.blink = d.get('blink') or 0.85
        self.focused = False
        self.blinkT = 0.0

    def resolve(self):
        Selectable.resolve(self)
        self.textComponent = resolve_ref(self._text_ref)
        self.placeholder = resolve_ref(self._ph_ref)
        self.sync()

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, s):
        self._text = s
        self.sync()

    def sync(self):
        if self.textComponent:
            self.textComponent.text = self._text
        if self.placeholder:
            self.placeholder.enabled = self._text == ''

    def OnSelect(self):
        Selectable.OnSelect(self)
        self.focused = True
        self.blinkT = 0.0

    def OnDeselect(self):
        Selectable.OnDeselect(self)
        self.focused = False

    def OnPointerDown(self, e):
        Selectable.OnPointerDown(self, e)
        self.focused = True
        self.blinkT = 0.0

    def typed(self, ch):
        if not self.focused or not self.IsInteractable():
            return
        if ch == '\b':
            self._text = self._text[:-1]
        elif ch == '\n':
            U.es.SetSelectedGameObject(None)
            return
        elif ch >= ' ':
            if not self.limit or len(self._text) < self.limit:
                self._text += ch
        self.blinkT = 0.0
        self.sync()


# --------------------------------------------------------------------- tweens
def ease_out_quad(t):
    return -t * (t - 2)


class Tween:
    def __init__(self, target, dur):
        self.target = target
        self.duration = dur
        self.elapsed = 0.0
        self.ease = ease_out_quad
        self.on_update = None
        self.on_complete = None
        self.killed = False
        self.started = False

    def OnUpdate(self, f):
        self.on_update = f
        return self

    def OnComplete(self, f):
        self.on_complete = f
        return self

    def Kill(self):
        self.killed = True

    def step(self, dt):
        if self.killed:
            return True
        if not self.started:
            self.started = True
            self.startup()
        self.elapsed = min(self.duration, self.elapsed + dt)
        self.apply(self.elapsed / self.duration if self.duration > 0 else 1.0)
        if self.on_update:
            self.on_update()
        if self.elapsed >= self.duration:
            self.killed = True
            if self.on_complete:
                self.on_complete()
            return True
        return False

    def startup(self):
        pass

    def apply(self, k):
        pass


class FloatTween(Tween):
    def __init__(self, target, get, set_, to, dur):
        Tween.__init__(self, target, dur)
        self.get, self.set, self.to = get, set_, to

    def startup(self):
        self.frm = self.get()

    def apply(self, k):
        self.set(self.frm + (self.to - self.frm) * self.ease(k))


def tween_to(target, get, set_, to, dur):
    t = FloatTween(target, get, set_, to, dur)
    U.tweens.append(t)
    return t


class Sequence(Tween):
    def __init__(self):
        Tween.__init__(self, None, 0.0)
        self.items = []

    def Append(self, t):
        if t in U.tweens:
            U.tweens.remove(t)
        self.items.append(t)
        self.duration += t.duration
        return self

    def step(self, dt):
        if self.killed:
            return True
        left = dt
        while self.items and left >= 0:
            t = self.items[0]
            before = t.elapsed
            done = t.step(left)
            left -= t.elapsed - before
            if done:
                self.items.pop(0)
            else:
                break
            if left <= 0:
                break
        if not self.items:
            self.killed = True
            if self.on_complete:
                self.on_complete()
            return True
        return False


def DOTweenSequence():
    s = Sequence()
    U.tweens.append(s)
    return s


class ShakeTween(Tween):
    """DOTween.Shake as DOShakeAnchorPos builds it: a run of offsets that turn about
    by 180 +- randomness degrees and shrink to zero, each segment eased OutQuad"""

    def __init__(self, rt, dur, strength, vibrato, randomness=90.0, fade_out=True):
        Tween.__init__(self, rt, dur)
        vector_based = not isinstance(strength, (int, float))
        mag = math.hypot(strength[0], strength[1]) if vector_based else float(strength)
        n = int(vibrato * dur)
        if n < 2:
            n = 2
        decay = mag / n
        durs = [dur * (i + 1) / n if fade_out else dur / n for i in range(n)]
        mul = dur / sum(durs)
        durs = [d * mul for d in durs]
        ang = random.random() * 360
        tos = []
        st = [strength[0], strength[1]] if vector_based else None
        for i in range(n):
            if i < n - 1:
                if i > 0:
                    ang = ang - 180 + (random.random() * 2 - 1) * randomness
                if vector_based:
                    yaw = math.radians((random.random() * 2 - 1) * randomness)
                    x = math.cos(math.radians(ang)) * math.cos(yaw) * st[0]
                    y = math.sin(math.radians(ang)) * st[1]
                    l = math.hypot(x, y)
                    tos.append(V2(x / l * mag, y / l * mag) if l > 1e-9 else V2(0, 0))
                    if fade_out:
                        mag -= decay
                    sl = math.hypot(st[0], st[1])
                    if sl > mag:
                        k = max(mag, 0) / sl if sl > 0 else 0
                        st = [st[0] * k, st[1] * k]
                else:
                    tos.append(V2(mag * math.cos(math.radians(ang)), mag * math.sin(math.radians(ang))))
                    if fade_out:
                        mag -= decay
            else:
                tos.append(V2(0, 0))
        self.durs, self.tos = durs, tos

    def startup(self):
        self.start = self.target.anchoredPosition

    def apply(self, k):
        t, i = self.elapsed, 0
        while i < len(self.durs) - 1 and t > self.durs[i]:
            t -= self.durs[i]
            i += 1
        frm = V2(0, 0) if i == 0 else self.tos[i - 1]
        to = self.tos[i]
        e = ease_out_quad(clamp01(t / self.durs[i])) if self.durs[i] > 0 else 1.0
        self.target.anchoredPosition = V2(self.start.x + frm.x + (to.x - frm.x) * e,
                                          self.start.y + frm.y + (to.y - frm.y) * e)


def DOShakeAnchorPos(rt, dur, strength, vibrato):
    t = ShakeTween(rt, dur, strength, vibrato)
    U.tweens.append(t)
    return t


class MoveTween(Tween):
    def __init__(self, rt, w, dur):
        Tween.__init__(self, rt, dur)
        self.w = w

    def startup(self):
        self.frm = self.target.position

    def apply(self, k):
        e = self.ease(k)
        self.target.position = V2(self.frm.x + (self.w.x - self.frm.x) * e, self.frm.y + (self.w.y - self.frm.y) * e)


def DOMove(rt, w, dur):
    t = MoveTween(rt, w, dur)
    U.tweens.append(t)
    return t


# ------------------------------------------------------------- scene loading
KINDS = {'Image': Image, 'Text': Text, 'TMP': TMPText, 'UILineRenderer': UILineRenderer,
         'CanvasGroup': CanvasGroup, 'Canvas': Canvas, 'Mask': Mask, 'RectMask2D': RectMask2D,
         'BoxCollider2D': BoxCollider2D, 'Rigidbody2D': Rigidbody2D, 'Button': Button,
         'InputField': InputField, 'HorizontalLayoutGroup': LayoutGroup, 'VerticalLayoutGroup': LayoutGroup,
         'ContentSizeFitter': ContentSizeFitter, 'Animator': Animator}


def instantiate_nodes(nodes, parent_go, id_map):
    gos = []
    for d in nodes:
        go = GameObject(d)
        gos.append(go)
        id_map[d['id']] = go
        parent = gos[d['p']] if d['p'] >= 0 else parent_go
        if parent:
            go.parent = parent
            parent.children.append(go)
        scaler = None
        for c in d['c']:
            if c['k'] == 'CanvasScaler':
                scaler = c
                continue
            if c['k'] in KINDS:
                comp = KINDS[c['k']](go, c)
            elif c['k'] in U.scripts:
                comp = U.scripts[c['k']](go, c)
                comp._fields = c.get('f')
            else:
                continue
            go.comps.append(comp)
        cv = go.get('Canvas')
        nested = False
        a = parent
        while a:
            if a.get('Canvas'):
                nested = True
            a = a.parent
        if cv and not nested:
            cv.scaler = scaler
            go.rt.canvas = cv
            go.rt.pivot = V2(0.5, 0.5)
    return gos


def resolve_ref(r):
    if not r:
        return None
    if 'prefab' in r:
        return U.data['prefabs'][r['prefab']]
    if 'spr' in r:
        return U.sprites.get(r['spr'])
    if 'go' not in r:
        return {'label': r['asset']} if 'asset' in r else None
    go = U.objects.get(r['go'])
    if not go:
        return None
    c = r.get('c')
    if not c:
        return go
    if c == 'RectTransform':
        return go.rt
    if c == 'TextMeshProUGUI':
        return go.get('TMP')
    for comp in go.comps:
        if comp.kind == c or type(comp).__name__ == c:
            return comp
    return None


def resolve_fields(v):
    if isinstance(v, list):
        if len(v) == 4 and all(isinstance(x, (int, float)) and not isinstance(x, bool) and 0 <= x <= 1 for x in v):
            return col4(v)
        return [resolve_fields(x) for x in v]
    if isinstance(v, dict):
        if 'go' in v or 'prefab' in v or 'spr' in v:
            return resolve_ref(v)
        if 'x' in v and 'y' in v and len(v) <= 3:
            return V2(v['x'], v['y'])
        return {k: resolve_fields(x) for k, x in v.items()}
    return v


class Struct:
    def __init__(self, d):
        self.__dict__.update(d)


def assign_fields(comp, fields):
    for k, v in resolve_fields(fields).items():
        if isinstance(v, dict) and 'label' not in v:
            v = Struct(v)
        setattr(comp, k, v)


def invoke_calls(calls):
    for c in calls:
        t = c['target'] if 'target' in c else resolve_ref(c['t'])
        f = getattr(t, c['m'], None) if t is not None else None
        if not callable(f):
            continue
        mode = c['mode']
        if mode == 3:
            f(c['i'])
        elif mode == 4:
            f(c['f'])
        elif mode == 5:
            f(c['s'])
        elif mode == 6:
            f(c['b'])
        else:
            f()


def load_scene(name):
    U.tweens = [t for t in U.tweens if getattr(t, 'persist', False)]
    U.timers = []
    U.contacts = set()
    U.pending_start = []
    U.objects = {}
    for go in U.persist:
        index_objects(go)
    gos = instantiate_nodes(U.data['scenes'][name], None, U.objects)
    U.scene = _U()
    U.scene.name = name
    U.scene.roots = [g for g in gos if not g.parent]
    for go in gos:
        for c in go.comps:
            if c._fields is not None:
                assign_fields(c, c._fields)
            if hasattr(c, 'resolve'):
                c.resolve()
    for go in gos:
        if go.activeInHierarchy:
            for c in go.comps:
                if hasattr(c, 'Awake') and c.enabled:
                    c.Awake()
    for go in gos:
        if go.activeInHierarchy:
            for c in go.comps:
                if hasattr(c, 'Start') and c.enabled and not c._started:
                    U.pending_start.append(c)
    U.es.reset()


def index_objects(go):
    U.objects[go.id] = go
    for c in go.children:
        index_objects(c)


def all_roots():
    return U.scene.roots + U.persist


_uid = [10 ** 9]


def Instantiate(prefab_nodes, parent_t):
    m = {}
    gos = instantiate_nodes(prefab_nodes, parent_t.go, m)
    saved = U.objects
    merged = dict(saved)
    merged.update(m)
    U.objects = merged
    for go in gos:
        for c in go.comps:
            if c._fields is not None:
                assign_fields(c, c._fields)
            if hasattr(c, 'resolve'):
                c.resolve()
    U.objects = saved
    for g in gos:
        _uid[0] += 1
        g.id = _uid[0]
        U.objects[g.id] = g
    for go in gos:
        if go.activeInHierarchy:
            for c in go.comps:
                if hasattr(c, 'Awake') and c.enabled:
                    c.Awake()
                if hasattr(c, 'Start') and c.enabled:
                    U.pending_start.append(c)
    return gos[0]


# --------------------------------------------------------------------- layout
def run_layout(go):
    if not go.activeInHierarchy:
        return
    for c in go.comps:
        if isinstance(c, LayoutGroup) and c.enabled:
            layout_group(go, c.d)
        if isinstance(c, ContentSizeFitter) and c.enabled:
            t = go.get('TMP') or go.get('Text')
            if t and c.h == 2:
                go.rt.SetWidth(t.preferredWidth)
    for ch in go.children:
        run_layout(ch)


def layout_group(go, g):
    vertical = g['k'] == 'VerticalLayoutGroup'
    kids = [k for k in go.children if k.activeSelf and k.rt.isRect]
    size = go.rt.size
    pad_l, pad_r, pad_t, pad_b = g['pad']

    def pad_axis(a):
        return pad_l + pad_r if a == 0 else pad_t + pad_b

    def align_on(a):
        return (g['align'] % 3) * 0.5 if a == 0 else (g['align'] // 3) * 0.5

    for axis in (0, 1):
        along = (axis == 1) if vertical else (axis == 0)
        sz = size[axis]
        expand = g['fw'] if axis == 0 else g['fh']
        sizes = [(k.rt.sizeDelta[axis], k.rt.sizeDelta[axis], 1 if expand else 0) for k in kids]
        align = align_on(axis)

        def start_offset(req):
            return (pad_l if axis == 0 else pad_t) + (sz - (req + pad_axis(axis))) * align

        def set_(k, pos):
            k.rt.anchorMin = k.rt.anchorMax = V2(0, 1)
            sd = k.rt.sizeDelta[axis]
            ap = k.rt.anchoredPosition
            if axis == 0:
                k.rt.anchoredPosition = V2(pos + sd * k.rt.pivot.x, ap.y)
            else:
                k.rt.anchoredPosition = V2(ap.x, -pos - sd * (1 - k.rt.pivot.y))

        if not along:
            inner = sz - pad_axis(axis)
            for k, (mn, pref, flex) in zip(kids, sizes):
                req = clamp(inner, mn, sz if flex > 0 else pref)
                set_(k, start_offset(req) + (req - k.rt.sizeDelta[axis]) * align)
        else:
            total_pref = pad_axis(axis) + sum(s[1] + g['sp'] for s in sizes)
            total_flex = sum(s[2] for s in sizes)
            if kids:
                total_pref -= g['sp']
            pos = pad_l if axis == 0 else pad_t
            mult = 0
            surplus = sz - total_pref
            if surplus > 0:
                if total_flex == 0:
                    pos = start_offset(total_pref - pad_axis(axis))
                else:
                    mult = surplus / total_flex
            for k, (mn, pref, flex) in zip(kids, sizes):
                cs = pref + flex * mult
                set_(k, pos + (cs - k.rt.sizeDelta[axis]) * align)
                pos += cs + g['sp']


# --------------------------------------------------------------- event system
class PointerEvent:
    def __init__(self, position, press_position, delta):
        self.position = position
        self.pressPosition = press_position
        self.delta = delta
        self.button = 0


class EventSystem:
    def __init__(self):
        self.reset()

    def reset(self):
        self.current = None
        self.press = None
        self.drag = None
        self.dragging = False
        self.eligible = False
        self.pressPos = V2(0, 0)
        self.lastPos = None
        self.pointerEnter = None

    @property
    def currentSelectedGameObject(self):
        return self.current

    def SetSelectedGameObject(self, go):
        if go is self.current:
            return
        old, self.current = self.current, go
        if old:
            for c in old.comps:
                if hasattr(c, 'OnDeselect'):
                    c.OnDeselect()
        if go:
            for c in go.comps:
                if hasattr(c, 'OnSelect'):
                    c.OnSelect()

    def process(self):
        """StandaloneInputModule.ProcessMouseEvent: once a frame, press/release
        first, then enter/exit, then drag, all at the pointer's current position"""
        inp = U.input
        evs, inp.queue = inp.queue, []
        pressed = 'down' in evs
        released = 'up' in evs
        pos = inp.mouse
        delta = V2(pos.x - self.lastPos.x, pos.y - self.lastPos.y) if self.lastPos else V2(0, 0)
        self.lastPos = pos
        hit = raycast(pos)
        ev = PointerEvent(pos, self.pressPos, delta)
        if pressed:
            self.on_press(hit, ev)
        if released:
            self.on_release(hit, ev)
        self.handle_enter_exit(hit, ev)
        if delta.x != 0 or delta.y != 0:
            self.on_drag(ev)

    def handle_enter_exit(self, hit, ev):
        if self.pointerEnter is hit:
            return

        def chain(g):
            a = []
            while g:
                a.append(g)
                g = g.parent
            return a

        old_c, new_c = chain(self.pointerEnter), chain(hit)
        common = next((g for g in old_c if g in new_c), None)
        for g in old_c:
            if g is common:
                break
            for c in g.comps:
                if hasattr(c, 'OnPointerExit') and c.enabled:
                    c.OnPointerExit(ev)
        self.pointerEnter = hit
        for g in new_c:
            if g is common:
                break
            for c in g.comps:
                if hasattr(c, 'OnPointerEnter') and c.enabled:
                    c.OnPointerEnter(ev)

    def on_press(self, hit, ev):
        self.pressPos = ev.position
        ev.pressPosition = ev.position
        self.eligible = True
        self.dragging = False
        if handler_of(hit, 'OnSelect') is not self.current:
            self.SetSelectedGameObject(None)
        ph = handler_of(hit, 'OnPointerDown')
        if ph:
            call_all(ph, 'OnPointerDown', ev)
        else:
            ph = handler_of(hit, 'OnPointerClick')
        self.press = ph
        self.drag = handler_of(hit, 'OnDrag')

    def on_drag(self, ev):
        if not self.drag:
            return
        if not self.dragging:
            if math.hypot(ev.position.x - self.pressPos.x, ev.position.y - self.pressPos.y) >= 10:
                call_all(self.drag, 'OnBeginDrag', ev)
                self.dragging = True
        if self.dragging:
            if self.press and self.press is not self.drag:
                call_all(self.press, 'OnPointerUp', ev)
                self.eligible = False
                self.press = None
            call_all(self.drag, 'OnDrag', ev)

    def on_release(self, hit, ev):
        if self.press:
            call_all(self.press, 'OnPointerUp', ev)
        ch = handler_of(hit, 'OnPointerClick')
        if self.press and self.press is ch and self.eligible:
            call_all(self.press, 'OnPointerClick', ev)
        if self.drag and self.dragging:
            call_all(self.drag, 'OnEndDrag', ev)
        self.press = self.drag = None
        self.dragging = self.eligible = False


def handler_of(go, method):
    g = go
    while g:
        for c in g.comps:
            if c.enabled and callable(getattr(c, method, None)):
                return g
        g = g.parent
    return None


def call_all(go, method, ev):
    for c in go.comps:
        f = getattr(c, method, None)
        if c.enabled and callable(f):
            f(ev)


def canvas_roots():
    out = []

    def visit(g):
        if g.rt.canvas:
            out.append(g)
        else:
            for ch in g.children:
                visit(ch)
    for r in U.scene.roots:
        visit(r)
    for r in U.persist:
        visit(r)
    out.sort(key=lambda g: g.get('Canvas').sortingOrder)
    return out


def collect_draw(go, out, alpha, clip, ray):
    """draw list in hierarchy order with group alpha, raycast blocking and clipping"""
    if not go.activeSelf:
        return
    cg = go.get('CanvasGroup')
    if cg:
        alpha = cg.alpha if cg.ignoreParentGroups else alpha * cg.alpha
        if not cg.blocksRaycasts:
            ray = False
    mask, rm = go.get('Mask'), go.get('RectMask2D')
    img = go.get('Image')
    for c in go.comps:
        if not isinstance(c, Graphic) or not c.enabled:
            continue
        if mask and not mask.showMaskGraphic and c is img:
            out.append((c, 0.0, clip, ray, True))
            continue
        out.append((c, alpha, clip, ray, False))
    if (mask and mask.enabled) or (rm and rm.enabled):
        cs = go.rt.worldCorners()
        xs = [p[0] for p in cs]
        ys = [p[1] for p in cs]
        r = (min(xs), min(ys), max(xs), max(ys))
        if clip:
            r = (max(r[0], clip[0]), max(r[1], clip[1]), min(r[2], clip[2]), min(r[3], clip[3]))
        clip = r
    for ch in go.children:
        collect_draw(ch, out, alpha, clip, ray)


def raycast(pos):
    """GraphicRaycaster: topmost raycast-target graphic under the pointer"""
    best = None
    for root in canvas_roots():
        lst = []
        collect_draw(root, lst, 1.0, None, True)
        for g, alpha, clip, ray, hidden in lst:
            if not g.raycastTarget or not ray:
                continue
            if clip and not (clip[0] <= pos.x <= clip[2] and clip[1] <= pos.y <= clip[3]):
                continue
            x, y, w, h = g.go.rt.rect
            p = m_apply(m_inv(g.go.rt.worldMatrix), pos.x, pos.y)
            if x <= p[0] <= x + w and y <= p[1] <= y + h:
                best = g.go
    return best


# -------------------------------------------------------------------- physics
def box_of(col):
    m = col.go.rt.worldMatrix
    hx, hy, ox, oy = col.size.x / 2, col.size.y / 2, col.offset.x, col.offset.y
    pts = [m_apply(m, ox + a, oy + b) for a, b in ((-hx, -hy), (-hx, hy), (hx, hy), (hx, -hy))]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def physics_step():
    cols = []

    def walk(g):
        if not g.activeInHierarchy:
            return
        c = g.get('BoxCollider2D')
        if c and c.enabled:
            cols.append(c)
        for ch in g.children:
            walk(ch)
    for r in all_roots():
        walk(r)
    now = set()
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            a, b = cols[i], cols[j]
            if not a.go.get('Rigidbody2D') and not b.go.get('Rigidbody2D'):
                continue
            A, B = box_of(a), box_of(b)
            if A[0] < B[2] and B[0] < A[2] and A[1] < B[3] and B[1] < A[3]:
                now.add((a.go, b.go))

    def fire(pair, method):
        A, B = pair
        for c in A.comps:
            f = getattr(c, method, None)
            if f:
                f(B.get('BoxCollider2D'))
        for c in B.comps:
            f = getattr(c, method, None)
            if f:
                f(A.get('BoxCollider2D'))
    for k in list(U.contacts):
        if k not in now:
            fire(k, 'OnTriggerExit2D')
    for k in now:
        if k not in U.contacts:
            fire(k, 'OnTriggerEnter2D')
    U.contacts = now


# ----------------------------------------------------------------- frame loop
def for_each_comp(f):
    def walk(g):
        if not g.activeInHierarchy:
            return
        for c in list(g.comps):
            if c.enabled:
                f(c)
        for ch in list(g.children):
            walk(ch)
    for r in all_roots():
        walk(r)


def tick(dt):
    dt = min(dt, MAX_DT)
    U.dt = dt
    U.time += dt
    while U.pending_start:
        c = U.pending_start.pop(0)
        if not c._started:
            c._started = True
            c.Start()
    U.fixed_acc += dt
    while U.fixed_acc >= FIXED_DT - 1e-9:
        U.fixed_acc -= FIXED_DT
        U.fixed_time += FIXED_DT
        U.in_fixed = True
        for_each_comp(lambda c: c.FixedUpdate() if hasattr(c, 'FixedUpdate') else None)
        physics_step()
        U.in_fixed = False
    U.es.process()

    def upd(c):
        if hasattr(c, 'Update'):
            c.Update()
        if isinstance(c, Animator):
            c.update(dt)
    for_each_comp(upd)
    for t in list(U.tweens):
        if t.step(dt) and t in U.tweens:
            U.tweens.remove(t)

    def after(c):
        if isinstance(c, Selectable):
            c.apply_state(False)
        if isinstance(c, Graphic):
            c.tick_fade(dt)
        if isinstance(c, InputField):
            c.blinkT += dt
    for_each_comp(after)
    for tm in list(U.timers):
        tm[0] -= dt
        if tm[0] <= 0:
            U.timers.remove(tm)
            tm[1]()
    for r in all_roots():
        run_layout(r)
    if U.next_scene:
        n, U.next_scene = U.next_scene, None
        load_scene(n)
    U.input.down.clear()
    U.input.up.clear()
    U.frame += 1


class Input:
    GetKey = staticmethod(lambda k: k in U.input.keys)
    GetKeyDown = staticmethod(lambda k: k in U.input.down)
    GetKeyUp = staticmethod(lambda k: k in U.input.up)
    GetMouseButton = staticmethod(lambda b=0: U.input.btn_held)

    @staticmethod
    def mousePosition():
        return U.input.mouse


class Time:
    @staticmethod
    def time():
        return U.fixed_time if U.in_fixed else U.time

    @staticmethod
    def deltaTime():
        return FIXED_DT if U.in_fixed else U.dt


class PlayerPrefs:
    GetInt = staticmethod(lambda k, d: U.prefs.get(k, d))
    SetInt = staticmethod(lambda k, v: U.prefs.__setitem__(k, v))
    GetFloat = staticmethod(lambda k, d: U.prefs.get(k, d))
    GetString = staticmethod(lambda k, d: U.prefs.get(k, d))
    SetString = staticmethod(lambda k, v: U.prefs.__setitem__(k, v))
    DeleteKey = staticmethod(lambda k: U.prefs.pop(k, None))
    DeleteAll = staticmethod(lambda: U.prefs.clear())
    Save = staticmethod(lambda: None)


def random_range_int(a, b):
    return a + int(random.random() * (b - a))


# ------------------------------------------------------------------ rendering
# The scene drawn with Pillow in the same order and by the same rules as Unity's
# canvas renderer: sprites tinted by the vertex colour, 9-sliced borders at the
# sprite's pixels-per-unit, filled images, masks as clip rectangles, and text laid
# out glyph by glyph from the fonts' own advance tables.

FONTS = {'LibSans': (0.9052734375, 0.2119140625, 0.0327), 'Cursed': (0.84765625, 0.1416015625, 0.0898)}
TMP_ASC, TMP_DESC, TMP_LINE = 77.853515625 / 86, 18.224609375 / 86, 98.8916015625 / 86


def adv_of(table, ch):
    t = ADV.get(table)
    c = ord(ch)
    if t and c in t:
        return t[c]
    if c in ADV['Sym']:
        return ADV['Sym'][c]
    return 0.556


_font_cache = {}


def pil_font(fam, size):
    k = (fam, size)
    f = _font_cache.get(k)
    if f is None:
        f = ImageFont.truetype(io.BytesIO(FONT_BYTES[fam]), size)
        _font_cache[k] = f
    return f


def font_for(fam, ch):
    """the glyph's font: the family, or the symbol font for what it lacks (the ℃)"""
    t = ADV.get(fam)
    if t is not None and ord(ch) not in t and ord(ch) in ADV['Sym']:
        return 'Sym'
    return fam


# ---- legacy Text (Arial metrics, glyph advances rounded to whole pixels)
def legacy_family(t):
    if t.font == 'CursedTimerUlil-Aznm':
        return 'Cursed'
    return 'LibSansB' if t.fontStyle & 1 else 'LibSansI' if t.fontStyle & 2 else 'LibSans'


def legacy_adv(fam, ch, size):
    return int(math.floor(adv_of(fam, ch) * size + 0.5))


def legacy_line_w(fam, s, size):
    return sum(legacy_adv(fam, ch, size) for ch in s)


def wrap_words(text, w, width_of):
    out = []
    for para in text.split('\n'):
        if not (w > 0):
            out.append(para)
            continue
        words = re.split(r'(\s+)', para)
        line = ''
        for wd in words:
            t = line + wd
            if line and wd.strip() and width_of(t.rstrip()) > w + 0.01:
                out.append(line.rstrip())
                line = wd.lstrip()
            else:
                line = t
        out.append(line)
    return out


def legacy_metrics(fam):
    return FONTS['Cursed'] if fam == 'Cursed' else FONTS['LibSans']


def legacy_layout(t, W, size):
    fam = legacy_family(t)
    asc, desc, gap = legacy_metrics(fam)
    lines = wrap_words(t.text, W if t.hOverflow == 0 else 0, lambda s: legacy_line_w(fam, s, size))
    lh = (asc + desc + gap) * size * t.lineSpacing
    return fam, (asc, desc), lines, lh


def legacy_size(t, W, H):
    if not t.bestFit:
        return t.fontSize
    for s in range(t.maxSize, t.minSize - 1, -1):
        fam, met, lines, lh = legacy_layout(t, W, s)
        wide = max(legacy_line_w(fam, l, s) for l in lines)
        if wide <= W + 0.01 and len(lines) * lh <= H + 0.01:
            return s
    return t.minSize


def measure_legacy(t, text):
    fam = legacy_family(t)
    return max(legacy_line_w(fam, l, t.fontSize) for l in text.split('\n'))


def layout_legacy(t, W, H):
    """[(x, baseline, char, family, size)] in the element's own frame (y down)"""
    size = legacy_size(t, W, H)
    fam, (asc, desc), lines, lh = legacy_layout(t, W, size)
    A, D = asc * size, desc * size
    if t.vOverflow == 0:
        fit = max(1, int(math.floor((H - (A + D) + 1e-3) / lh)) + 1)
        lines = lines[:fit]
    block = (len(lines) - 1) * lh + A + D
    va, ha = t.alignment // 3, t.alignment % 3
    top = 0 if va == 0 else (H - block) / 2 if va == 1 else H - block
    out = []
    for i, ln in enumerate(lines):
        lw = legacy_line_w(fam, ln, size)
        x = 0 if ha == 0 else (W - lw) / 2 if ha == 1 else W - lw
        y = top + A + i * lh
        for ch in ln:
            if ch != ' ':
                out.append((x, y, ch, fam, size, False))
            x += legacy_adv(fam, ch, size)
    return out


# ---- TextMeshPro, with the rich text tags the scenes use: <i>, <b>, <size=n>
def tmp_runs(text, base, style):
    runs, i, size = [], 0, base
    ital, bold = bool(style & 2), bool(style & 1)
    stack = []
    while i < len(text):
        if text[i] == '<':
            j = text.find('>', i)
            if j > 0:
                tag = text[i + 1:j]
                ok = True
                if tag == 'i':
                    ital = True
                elif tag == '/i':
                    ital = bool(style & 2)
                elif tag == 'b':
                    bold = True
                elif tag == '/b':
                    bold = bool(style & 1)
                elif tag.startswith('size='):
                    stack.append(size)
                    size = float(tag[5:])
                elif tag == '/size':
                    size = stack.pop() if stack else base
                else:
                    ok = False
                if ok:
                    i = j + 1
                    continue
        if runs and runs[-1][1] == size and runs[-1][2] == ital and runs[-1][3] == bold:
            runs[-1][0] += text[i]
        else:
            runs.append([text[i], size, ital, bold])
        i += 1
    return runs


def tmp_char_adv(r, ch):
    return adv_of('tmp', ch) * r[1] + (0.07 * r[1] if r[3] else 0)


def run_width(r):
    return sum(tmp_char_adv(r, ch) for ch in r[0])


def runs_width(rs):
    return sum(run_width(r) for r in rs)


def trim_runs(rs):
    rs = [list(r) for r in rs]
    while rs and rs[-1][0][-1:].isspace():
        rs[-1][0] = rs[-1][0].rstrip()
        if not rs[-1][0]:
            rs.pop()
    return rs


def measure_tmp(t, text):
    lines = [trim_runs(tmp_runs(l, t.fontSize, t.fontStyle)) for l in text.split('\n')]
    return max([0] + [runs_width(rs) for rs in lines])


def layout_tmp(t, W, H):
    mg = t.margin
    L, T = mg[0], mg[1]
    W, H = W - mg[0] - mg[2], H - mg[1] - mg[3]
    size = t.fontSize
    lines = []
    for raw in t.text.split('\n'):
        runs = tmp_runs(raw, size, t.fontStyle)
        if not t.wrap or runs_width(trim_runs(runs)) <= W + 0.01 or len(runs) != 1:
            lines.append(runs)
            continue
        r0 = runs[0]
        for s in wrap_words(r0[0], W, lambda x: run_width([x, r0[1], r0[2], r0[3]])):
            lines.append([[s, r0[1], r0[2], r0[3]]])
    lh, A, D = TMP_LINE * size, TMP_ASC * size, TMP_DESC * size
    block = (len(lines) - 1) * lh + A + D
    top = T if t.vAlign == 256 else T + H - block if t.vAlign == 1024 else T + (H - block) / 2
    out = []
    for i, runs in enumerate(lines):
        w = runs_width(trim_runs(runs))
        x = L + (W - w) / 2 if t.hAlign == 2 else L + W - w if t.hAlign == 4 else L
        y = top + A + i * lh
        for r in runs:
            fam = 'LibSansI' if r[2] else 'LibSans'
            for ch in r[0]:
                if ch != ' ':
                    out.append((x, y, ch, fam, r[1], r[3]))
                x += tmp_char_adv(r, ch)
    return out


SS = 3          # text is drawn three times larger and scaled down: sub-pixel placement


def text_image(glyphs, W, H, col):
    """the element's text as an RGBA image of W x H (plus room for overflow)"""
    if not glyphs:
        return None, 0, 0
    xs = [g[0] for g in glyphs]
    ys = [g[1] for g in glyphs]
    smax = max(g[4] for g in glyphs)
    x0 = int(math.floor(min(0, min(xs) - smax * 0.2)))
    y0 = int(math.floor(min(0, min(ys) - smax * 1.1)))
    x1 = int(math.ceil(max(W, max(xs) + smax * 1.4)))
    y1 = int(math.ceil(max(H, max(ys) + smax * 0.4)))
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    big = PILImage.new('L', (w * SS, h * SS), 0)
    dr = ImageDraw.Draw(big)
    for x, y, ch, fam, size, bold in glyphs:
        f = pil_font(font_for(fam, ch), int(round(size * SS)))
        dr.text(((x - x0) * SS, (y - y0) * SS), ch, font=f, fill=255, anchor='ls',
                stroke_width=1 if bold else 0, stroke_fill=255)
    a = big.resize((w, h), PILImage.LANCZOS)
    rgba = PILImage.new('RGBA', (w, h), (int(col[0] * 255 + .5), int(col[1] * 255 + .5), int(col[2] * 255 + .5), 0))
    if col[3] < 1:
        a = a.point(lambda v: int(v * col[3] + 0.5))
    rgba.putalpha(a)
    return rgba, x0, y0


# ---- images
_tint_cache = {}


def sprite_tinted(spr, col):
    k = (spr.key, round(col[0], 3), round(col[1], 3), round(col[2], 3))
    im = _tint_cache.get(k)
    if im is None:
        im = spr.img
        if not (col[0] == 1 and col[1] == 1 and col[2] == 1):
            r, g, b, a = im.split()
            r = r.point(lambda v, c=col[0]: int(v * c + 0.5))
            g = g.point(lambda v, c=col[1]: int(v * c + 0.5))
            b = b.point(lambda v, c=col[2]: int(v * c + 0.5))
            im = PILImage.merge('RGBA', (r, g, b, a))
        _tint_cache[k] = im
    return im


def with_alpha(im, a):
    if a >= 0.999:
        return im
    im = im.copy()
    im.putalpha(im.getchannel('A').point(lambda v: int(v * a + 0.5)))
    return im


_elem_cache = {}


def image_element(g, col, W, H):
    """an Image graphic drawn into a W x H RGBA picture, or None for a plain rect"""
    spr = g.sprite
    Wi, Hi = max(1, int(round(W))), max(1, int(round(H)))
    fill = round(g.fillAmount, 4) if g.type == 3 else 1
    k = (id(spr), spr.key if spr else None, Wi, Hi, g.type, fill, g.fillMethod, g.fillOrigin,
         tuple(round(c, 3) for c in col))
    im = _elem_cache.get(k)
    if im is not None:
        return im
    if len(_elem_cache) > 600:
        _elem_cache.clear()
    if spr is None:
        im = PILImage.new('RGBA', (Wi, Hi), (0, 0, 0, 0))
        c = tuple(int(col[i] * 255 + .5) for i in range(3)) + (int(col[3] * 255 + .5),)
        if g.type == 3:
            if g.fillMethod == 0:
                w = int(round(Wi * fill))
                if w > 0:
                    im.paste(c, (Wi - w if g.fillOrigin == 1 else 0, 0, Wi if g.fillOrigin == 1 else w, Hi))
            else:
                h = int(round(Hi * fill))
                if h > 0:
                    im.paste(c, (0, 0 if g.fillOrigin == 1 else Hi - h, Wi, h if g.fillOrigin == 1 else Hi))
        else:
            im.paste(c, (0, 0, Wi, Hi))
        _elem_cache[k] = im
        return im
    src = sprite_tinted(spr, col)
    sw, sh = spr.w, spr.h
    b = spr.b
    if g.type == 1 and any(b):
        ppu = spr.ppu / 100.0 * g.ppum
        bl, bb, br, bt = b[0] / ppu, b[1] / ppu, b[2] / ppu, b[3] / ppu
        if W < bl + br and bl + br > 0:
            s = W / (bl + br)
            bl, br = bl * s, br * s
        if H < bb + bt and bb + bt > 0:
            s = H / (bb + bt)
            bb, bt = bb * s, bt * s
        im = PILImage.new('RGBA', (Wi, Hi), (0, 0, 0, 0))
        sx = [0, b[0], sw - b[2], sw]
        sy = [0, b[3], sh - b[1], sh]
        dx = [0, int(round(bl)), int(round(Wi - br)), Wi]
        dy = [0, int(round(bt)), int(round(Hi - bb)), Hi]
        for i in range(3):
            for j in range(3):
                if i == 1 and j == 1 and not g.fillCenter:
                    continue
                sW, sH = sx[i + 1] - sx[i], sy[j + 1] - sy[j]
                dW, dH = dx[i + 1] - dx[i], dy[j + 1] - dy[j]
                if sW <= 0 or sH <= 0 or dW <= 0 or dH <= 0:
                    continue
                part = src.crop((sx[i], sy[j], sx[i + 1], sy[j + 1])).resize((dW, dH), PILImage.BILINEAR)
                im.alpha_composite(part, (dx[i], dy[j]))
    elif g.type == 3:
        im = PILImage.new('RGBA', (Wi, Hi), (0, 0, 0, 0))
        f = clamp01(fill)
        if f > 0:
            if g.fillMethod == 0:
                w, s = max(1, int(round(Wi * f))), max(1, int(round(sw * f)))
                part = src.crop((sw - s, 0, sw, sh) if g.fillOrigin == 1 else (0, 0, s, sh)).resize((w, Hi), PILImage.BILINEAR)
                im.alpha_composite(part, (Wi - w if g.fillOrigin == 1 else 0, 0))
            else:
                h, s = max(1, int(round(Hi * f))), max(1, int(round(sh * f)))
                part = src.crop((0, 0, sw, s) if g.fillOrigin == 1 else (0, sh - s, sw, sh)).resize((Wi, h), PILImage.BILINEAR)
                im.alpha_composite(part, (0, 0 if g.fillOrigin == 1 else Hi - h))
    elif g.preserveAspect:
        a = sw / sh
        w, h = W, H
        if W / H > a:
            w = H * a
        else:
            h = W / a
        im = PILImage.new('RGBA', (Wi, Hi), (0, 0, 0, 0))
        part = src.resize((max(1, int(round(w))), max(1, int(round(h)))), PILImage.BILINEAR)
        im.alpha_composite(part, (int(round((W - w) * g.go.rt.pivot.x)), int(round((H - h) * (1 - g.go.rt.pivot.y)))))
    else:
        im = src.resize((Wi, Hi), PILImage.BILINEAR) if (Wi, Hi) != (sw, sh) else src
    im = with_alpha(im, col[3])
    _elem_cache[k] = im
    return im


class Renderer:
    def __init__(self):
        self.frame = PILImage.new('RGBA', (SW, SH), (50, 50, 50, 255))
        self.sig = None
        self._text_cache = {}

    def blit(self, im, x, y, clip):
        """composite im with its top-left at screen (x, y), inside the clip box"""
        if im is None:
            return
        w, h = im.size
        x0, y0, x1, y1 = x, y, x + w, y + h
        cx0, cy0, cx1, cy1 = 0, 0, SW, SH
        if clip:
            cx0, cy0 = max(0, int(math.floor(clip[0]))), max(0, int(math.floor(SH - clip[3])))
            cx1, cy1 = min(SW, int(math.ceil(clip[2]))), min(SH, int(math.ceil(SH - clip[1])))
        ax0, ay0, ax1, ay1 = max(x0, cx0), max(y0, cy0), min(x1, cx1), min(y1, cy1)
        if ax1 <= ax0 or ay1 <= ay0:
            return
        part = im if (ax0, ay0, ax1, ay1) == (x0, y0, x1, y1) else im.crop((ax0 - x0, ay0 - y0, ax1 - x0, ay1 - y0))
        self.frame.alpha_composite(part, (ax0, ay0))

    def place(self, im, m, rx, ry, rw, rh, clip):
        """put the element picture (drawn for the local rect, y down) on screen"""
        a, b, c, d = m[0], m[1], m[2], m[3]
        if abs(b) < 1e-9 and abs(c) < 1e-9 and a > 0 and d > 0:
            X = m[4] + a * rx
            Y = SH - (m[5] + d * (ry + rh))
            tw, th = rw * a, rh * d
            if im.size != (max(1, int(round(tw))), max(1, int(round(th)))) and (abs(a - 1) > 1e-6 or abs(d - 1) > 1e-6):
                im = im.resize((max(1, int(round(tw))), max(1, int(round(th)))), PILImage.BILINEAR)
            self.blit(im, int(round(X)), int(round(Y)), clip)
            return
        # general affine: map the picture's pixels onto the screen bounding box
        corners = [m_apply(m, rx, ry), m_apply(m, rx, ry + rh), m_apply(m, rx + rw, ry + rh), m_apply(m, rx + rw, ry)]
        xs = [p[0] for p in corners]
        ys = [SH - p[1] for p in corners]
        bx0, by0 = int(math.floor(min(xs))), int(math.floor(min(ys)))
        bx1, by1 = int(math.ceil(max(xs))), int(math.ceil(max(ys)))
        W, H = im.size
        sxk, syk = W / rw, H / rh
        # screen (u, v) -> local (x, y_up) -> picture (px, py)
        inv = m_inv(m)
        # local x = inv0*X + inv2*Yw + inv4 with Yw = SH - (v + by0), X = u + bx0
        lx_u, lx_v, lx_c = inv[0], -inv[2], inv[0] * bx0 + inv[2] * (SH - by0) + inv[4]
        ly_u, ly_v, ly_c = inv[1], -inv[3], inv[1] * bx0 + inv[3] * (SH - by0) + inv[5]
        # picture px = (x - rx) * sxk, py = (ry + rh - y) * syk
        coeffs = (lx_u * sxk, lx_v * sxk, (lx_c - rx) * sxk,
                  -ly_u * syk, -ly_v * syk, (ry + rh - ly_c) * syk)
        out = im.transform((max(1, bx1 - bx0), max(1, by1 - by0)), PILImage.AFFINE, coeffs, resample=PILImage.BILINEAR)
        self.blit(out, bx0, by0, clip)

    def draw_rect(self, m, rx, ry, rw, rh, col, clip):
        c = tuple(int(col[i] * 255 + .5) for i in range(3)) + (int(col[3] * 255 + .5),)
        a, b, cc, d = m[0], m[1], m[2], m[3]
        if abs(b) < 1e-9 and abs(cc) < 1e-9 and a > 0 and d > 0:
            X0 = m[4] + a * rx
            X1 = m[4] + a * (rx + rw)
            Y0 = SH - (m[5] + d * (ry + rh))
            Y1 = SH - (m[5] + d * ry)
            x0, x1, y0, y1 = int(round(X0)), int(round(X1)), int(round(Y0)), int(round(Y1))
            if x1 == x0 and X1 > X0:      # a hairline still covers one pixel
                x1 = x0 + 1
            if y1 == y0 and Y1 > Y0:
                y1 = y0 + 1
            if clip:
                x0 = max(x0, int(math.floor(clip[0])))
                x1 = min(x1, int(math.ceil(clip[2])))
                y0 = max(y0, int(math.floor(SH - clip[3])))
                y1 = min(y1, int(math.ceil(SH - clip[1])))
            x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, SW), min(y1, SH)
            if x1 <= x0 or y1 <= y0:
                return
            if c[3] >= 255:
                self.frame.paste(c, (x0, y0, x1, y1))
            else:
                self.frame.alpha_composite(PILImage.new('RGBA', (x1 - x0, y1 - y0), c), (x0, y0))
            return
        pts = [m_apply(m, rx, ry), m_apply(m, rx, ry + rh), m_apply(m, rx + rw, ry + rh), m_apply(m, rx + rw, ry)]
        pts = [(p[0], SH - p[1]) for p in pts]
        bx0 = int(math.floor(min(p[0] for p in pts)))
        by0 = int(math.floor(min(p[1] for p in pts)))
        bx1 = int(math.ceil(max(p[0] for p in pts))) + 1
        by1 = int(math.ceil(max(p[1] for p in pts))) + 1
        layer = PILImage.new('RGBA', (max(1, bx1 - bx0), max(1, by1 - by0)), (0, 0, 0, 0))
        ImageDraw.Draw(layer).polygon([(p[0] - bx0 - 0.5, p[1] - by0 - 0.5) for p in pts], fill=c)
        self.blit(layer, bx0, by0, clip)

    def draw_line(self, g, m, col, clip):
        pts = g.Points
        if not pts or len(pts) < 2:
            return
        sp = [m_apply(m, p.x, p.y) for p in pts]
        sp = [(p[0], SH - p[1]) for p in sp]
        c = tuple(int(col[i] * 255 + .5) for i in range(3)) + (int(col[3] * 255 + .5),)
        w = max(1, int(round(g.LineThickness)))
        if not clip and c[3] >= 255:
            ImageDraw.Draw(self.frame).line([(p[0] - 0.5, p[1] - 0.5) for p in sp], fill=c, width=w)
            return
        layer = PILImage.new('RGBA', (SW, SH), (0, 0, 0, 0))
        ImageDraw.Draw(layer).line([(p[0] - 0.5, p[1] - 0.5) for p in sp], fill=c, width=w)
        self.blit(layer, 0, 0, clip)

    def collect(self):
        items = []
        for root in canvas_roots():
            lst = []
            collect_draw(root, lst, 1.0, None, True)
            items.extend(lst)
        return items

    def render(self):
        items = self.collect()
        ops = []
        for g, alpha, clip, ray, hidden in items:
            if hidden:
                continue
            c, cr = g.color, g.crColor
            col = (c[0] * cr[0], c[1] * cr[1], c[2] * cr[2], c[3] * cr[3] * alpha)
            if col[3] <= 0.001:
                continue
            m = g.go.rt.worldMatrix
            r = g.go.rt.rect
            ops.append((g, col, m, r, clip))
        sig = tuple((id(o[0]), tuple(round(v, 3) for v in o[1]), tuple(round(v, 2) for v in o[2]),
                     tuple(round(v, 2) for v in o[3]), o[4] and tuple(round(v, 1) for v in o[4]),
                     self.content_key(o[0])) for o in ops) + tuple(
            (f.focused, f.text, int(f.blinkT * f.blink * 2) % 2) for f in self.inputs(items))
        if sig == self.sig:
            return False
        self.sig = sig
        self.frame.paste((50, 50, 50, 255), (0, 0, SW, SH))     # the camera clears to (50,50,50)
        for g, col, m, r, clip in ops:
            rx, ry, rw, rh = r
            if isinstance(g, Image):
                if g.sprite is None and g.type != 3:
                    self.draw_rect(m, rx, ry, rw, rh, col, clip)
                else:
                    sx = math.hypot(m[0], m[1])
                    sy = math.hypot(m[2], m[3])
                    im = image_element(g, col, rw * sx, rh * sy)
                    self.place(im, m, rx, ry, rw, rh, clip)
            elif isinstance(g, (Text, TMPText)):
                self.draw_text(g, col, m, r, clip)
            elif isinstance(g, UILineRenderer):
                self.draw_line(g, m, col, clip)
        for g, alpha, clip, ray, hidden in items:
            f = g.go.get('InputField')
            if f:
                self.draw_caret(f, alpha)
        return True

    def draw_caret(self, f, alpha):
        """the InputField caret: 1 px, the caret colour, blinking at m_CaretBlinkRate,
        after the last character of the (upper left aligned) text"""
        t = f.textComponent
        if not f.focused or not t or not f.go.activeInHierarchy or not f.IsInteractable():
            return
        period = 1.0 / f.blink
        if (f.blinkT % period) >= period / 2:
            return
        fam = legacy_family(t)
        asc, desc, gap = legacy_metrics(fam)
        rx, ry, rw, rh = t.go.rt.rect
        x = rx + legacy_line_w(fam, f.text, t.fontSize)
        m = t.go.rt.worldMatrix
        h = (asc + desc) * t.fontSize
        self.draw_rect(m, round(x), ry + rh - h, f.caretWidth, h, f.caretColor.with_a(f.caretColor.a * alpha), None)

    def inputs(self, items):
        return [it[0].go.get('InputField') for it in items if it[0].go.get('InputField')]

    def content_key(self, g):
        if isinstance(g, Image):
            return (g.sprite.key if g.sprite else None, round(g.fillAmount, 4))
        if isinstance(g, (Text, TMPText)):
            return g.text
        if isinstance(g, UILineRenderer):
            return tuple((round(p.x, 2), round(p.y, 2)) for p in g.Points)
        return None

    def draw_text(self, g, col, m, r, clip):
        if not g.text:
            return
        rx, ry, rw, rh = r
        k = (type(g).__name__, g.text, rw, rh, getattr(g, 'fontSize', 0), getattr(g, 'fontStyle', 0),
             getattr(g, 'alignment', 0), getattr(g, 'hAlign', 0), getattr(g, 'vAlign', 0), getattr(g, 'font', ''),
             tuple(round(c, 3) for c in col))
        hit = self._text_cache.get(k)
        if hit is None:
            glyphs = layout_tmp(g, rw, rh) if isinstance(g, TMPText) else layout_legacy(g, rw, rh)
            hit = text_image(glyphs, rw, rh, col)
            if len(self._text_cache) > 400:
                self._text_cache.clear()
            self._text_cache[k] = hit
        im, x0, y0 = hit
        if im is None:
            return
        # the text picture covers local x from rx + x0, local y (down) from top + y0
        w, h = im.size
        self.place(im, m, rx + x0, ry + rh - y0 - h, w, h, clip)


# ---------------------------------------------------------- screen pictures
# APHO.exe loads these from Addressables bundles ("dr-351", "dr-488", ... 182
# pictures a wavelength, "dr-488-0" with 1032 for part A) that were not shipped
# with the program, so they are computed here from the sample the official
# solution describes:
#   double slit (part A)  fringes 0.65 cm apart at L = 50 cm with 632.8 nm,
#                         best position (3700, -2900) um
#   microspheres (B)      a = 5.627 um, close packed, rows sqrt(3)/2 a apart
#   rectangles (C)        l = 58.6 um, w = 51.0 um, long side at 27 deg
#   grid (D)              dx = 250 um, dy = 200 um, along the screen axes
# Each picture is 500 x 500 pixels for the +-10 cm screen; the "-tiff" twin is the
# grey intensity the photodetector reads (grey * 5.5 V).

PAT_N, PAT_HALF = 500, 0.10
A_SPHERE, L_RECT, W_RECT, PHI = 5.627e-6, 58.6e-6, 51.0e-6, 27.0
DX_GRID, DY_GRID, BEAM_D = 250e-6, 200e-6, 0.4e-3
SLIT_SEP, SLIT_W, SLIT_LEN, SLIT_BEAM = 48.7e-6, 10e-6, 100e-6, 120e-6
PART_A_RANGE = 1100


def laser_rgb(nm):
    """wavelength to the colour it is drawn in (Bruton); 351 nm and the infrared
    lines are invisible and leave the colour picture black"""
    if nm < 380 or nm > 780:
        return (0.0, 0.0, 0.0)
    r = g = b = 0.0
    if nm < 440:
        r, b = -(nm - 440) / 60.0, 1.0
    elif nm < 490:
        g, b = (nm - 440) / 50.0, 1.0
    elif nm < 510:
        g, b = 1.0, -(nm - 510) / 20.0
    elif nm < 580:
        r, g = (nm - 510) / 70.0, 1.0
    elif nm < 645:
        r, g = 1.0, -(nm - 645) / 65.0
    else:
        r = 1.0
    f = 0.3 + 0.7 * (780 - nm) / 80.0 if nm > 700 else 0.3 + 0.7 * (nm - 380) / 40.0 if nm < 420 else 1.0
    return (r * f, g * f, b * f)


def _sinc2(z):
    out = np.ones_like(z)
    m = np.abs(z) > 1e-9
    out[m] = (np.sin(z[m]) / z[m]) ** 2
    return out


def _grid():
    px = 2 * PAT_HALF / PAT_N
    c = -PAT_HALF + (np.arange(PAT_N) + 0.5) * px
    return c[None, :], (PAT_HALF - (np.arange(PAT_N) + 0.5) * px)[:, None]


def sample_field(nm, Lcm):
    """intensity of the sample's pattern, peak of the straight-through beam = 1"""
    lam, L = nm * 1e-9, Lcm / 100.0
    x, y = _grid()
    sig = 0.42 * lam * L / BEAM_D

    def comb(v, pitch):
        per = lam * L / pitch
        d = v - np.round(v / per) * per
        return np.exp(-d * d / (2 * sig * sig)) + np.exp(-((np.abs(d) - per) ** 2) / (2 * sig * sig))
    fx, fy = comb(x, DX_GRID), comb(y, DY_GRID)
    u, v = x / L, y / L
    p = math.radians(PHI)
    up = u * math.cos(p) + v * math.sin(p)
    vp = -u * math.sin(p) + v * math.cos(p)
    env = _sinc2(math.pi * L_RECT * up / lam) * _sinc2(math.pi * W_RECT * vp / lam)
    I = env * fx * fy * 0.35
    r = np.hypot(x, y)
    d_row = math.sqrt(3) / 2 * A_SPHERE
    for m in (1, 2, 3):
        s = m * lam / d_row
        if s >= 0.95:
            break
        R = L * math.tan(math.asin(s))
        I = I + 1.2e-3 / (m * m) * np.exp(-(((r - R) / (0.02 * R + 0.0004)) ** 2))
    bw = 0.25 * lam * L / BEAM_D
    return I + np.exp(-r * r / (2 * bw * bw))


def slit_field(rx_um, ry_um):
    """part A: the double slit, lit by a narrow beam that misses it when off target"""
    lam, L = 632.8e-9, 0.5
    dx, dy = rx_um * 1e-6, ry_um * 1e-6
    hit = math.exp(-2 * (dx * dx + dy * dy) / (SLIT_BEAM * SLIT_BEAM))
    x, y = _grid()
    if hit < 1e-4:
        return np.zeros((PAT_N, PAT_N))
    u, v = x / L, y / L
    return hit * _sinc2(math.pi * SLIT_LEN * v / lam) * _sinc2(math.pi * SLIT_W * u / lam) * np.cos(math.pi * SLIT_SEP * u / lam) ** 2


def to_grey(I, log_span, top):
    """intensity -> 8 bit grey the way the pictures were exposed (logarithmic)"""
    with np.errstate(divide='ignore'):
        g = np.clip(1 + np.log10(np.maximum(I, 1e-300) / top) / log_span, 0, 1)
    g[I <= 0] = 0
    return np.floor(g * 255 + 0.5).astype(np.uint8)


class GenSprite:
    def __init__(self, key, grey, rgb):
        self.key = key
        self.grey = grey
        self.rgb = rgb
        self.w = self.h = PAT_N
        self.b = [0, 0, 0, 0]
        self.ppu = 100.0
        rgb_img = np.dstack([np.floor(grey * c + 0.5).astype(np.uint8) for c in rgb] + [np.full_like(grey, 255)])
        self.img = PILImage.fromarray(rgb_img, 'RGBA')

    def GetPixel(self, x, y):
        x = clamp(x, 0, PAT_N - 1)
        y = clamp(y, 0, PAT_N - 1)
        v = self.grey[PAT_N - 1 - y, x] / 255.0
        return (v * self.rgb[0], v * self.rgb[1], v * self.rgb[2], 1.0)


LABEL_NM = {'dr-351': 351, 'dr-488': 488, 'dr-514': 514, 'dr-632': 632.8, 'dr-694': 694.3,
            'dr-914': 914, 'dr-1152': 1152, 'dr-1444': 1444}
_RE_SAMPLE = re.compile(r'^([\d.]+)nm-(\d+)cm(-tiff)?$')
_RE_SLIT = re.compile(r'^632\.8nm-50cm-(-?\d+)um-(-?\d+)um(-tiff)?$')


class DiffractionImages:
    label = None
    cache = {}

    @classmethod
    def set_label(cls, l):
        if l != cls.label:
            cls.label = l
            cls.cache = {}

    @classmethod
    def get(cls, name):
        if name in cls.cache:
            return cls.cache[name]
        spr = None
        m = _RE_SAMPLE.match(name)
        if m and cls.label in LABEL_NM:
            nm, d = float(m.group(1)), int(m.group(2))
            if nm == LABEL_NM[cls.label] and 10 <= d <= 100:
                spr = GenSprite(name, to_grey(sample_field(nm, d), 4.2, 0.3), (1, 1, 1) if m.group(3) else laser_rgb(nm))
        else:
            m = _RE_SLIT.match(name)
            if m and cls.label == 'dr-488-0':
                x, y = int(m.group(1)), int(m.group(2))
                if abs(x) <= PART_A_RANGE and abs(y) <= PART_A_RANGE and x % 100 == 0 and y % 100 == 0:
                    spr = GenSprite(name, to_grey(slit_field(x, y), 2.2, 0.6), (1, 1, 1) if m.group(3) else laser_rgb(632.8))
        cls.cache[name] = spr
        return spr


# --------------------------------------------------------------- the scripts
# The app's own C# scripts (Assembly-CSharp.dll), line for line.

SCENE_FILE = {'scene_start': 'start', 'scene_deflection-1b': 'deflection',
              'scene_diffraction-0': 'diffraction0', 'scene_diffraction': 'diffraction'}


class SceneManager:
    @staticmethod
    def LoadScene(name):
        U.next_scene = SCENE_FILE[name]


def DontDestroyOnLoad(go):
    r = go
    while r.parent:
        r = r.parent
    if r in U.scene.roots:
        U.scene.roots.remove(r)
    if r not in U.persist:
        U.persist.append(r)


def reg(cls):
    U.scripts[cls.__name__] = cls
    return cls


def tf(b):
    return 'True' if b else 'False'


class IPHODebug:
    @staticmethod
    def Log(msg, useSceneTag=True):
        U.log(('[' + IPHOConst.GetSceneTag() + ']' if useSceneTag else '') + ' ' + msg)


# ======================================================================= IPHO
class IPHOConst:
    TAG_LASER = 'laser'
    SCENE_TAG = 'scene_tag'
    USER_INFO = 'user_info'

    @staticmethod
    def UpdateNowScene(scene):
        t = {'scene_deflection-1a': '1a', 'scene_deflection-1b': '1b', 'scene_deflection-1c': '1c',
             'scene_diffraction-0': '2a', 'scene_diffraction': '2b'}.get(scene)
        if t:
            PlayerPrefs.SetString(IPHOConst.SCENE_TAG, t)
            PlayerPrefs.Save()

    @staticmethod
    def GetSceneTag():
        return PlayerPrefs.GetString(IPHOConst.SCENE_TAG, '')

    @staticmethod
    def UpdateUser(c, n):
        PlayerPrefs.SetString(IPHOConst.USER_INFO, c + '_' + n)
        PlayerPrefs.Save()


@reg
class IPHOStartSceneViewController(Component):
    Instance = None

    def HandleDiffraction0BtnClick(self):
        self.LoadScene('scene_diffraction-0')
        IPHOStartSceneViewController.Instance.ShareCanvas.SetActive(True)

    def HandleDiffractionBtnClick(self):
        self.LoadScene('scene_diffraction')
        IPHOStartSceneViewController.Instance.ShareCanvas.SetActive(True)

    def _deflection(self, t):
        DeflectionDefaultManager.Instance().UpdateDeflectionType(t)
        self.LoadScene('scene_deflection-1b')
        IPHOStartSceneViewController.Instance.ShareCanvas.SetActive(True)

    def HandleDeflection1aBtnClick(self):
        self._deflection(0)

    def HandleDeflection1bBtnClick(self):
        self._deflection(1)

    def HandleDeflection1cBtnClick(self):
        self._deflection(2)

    def HandleDeflection1dBtnClick(self):
        self._deflection(3)

    def HandleBackBtnClick(self):
        IPHODebug.Log('Leave scene')
        IPHODebug.Log('--------------------------------------------------', False)
        self.LoadScene('scene_start')
        IPHOStartSceneViewController.Instance.ShareCanvas.SetActive(False)

    def HandleClearBtnClick(self):
        PlayerPrefs.DeleteAll()

    def LoadScene(self, sceneName):
        IPHOConst.UpdateNowScene(sceneName)
        IPHODebug.Log('[0] Select secene : ' + sceneName, False)
        SceneManager.LoadScene(sceneName)

    def HandleNextBtnClick(self):
        text, text2 = self.CountryField.text, self.NameField.text
        if text and text2:
            IPHOConst.UpdateUser(text, text2)
            self.CountryTxt.text = text
            self.NameTxt.text = text2
            IPHODebug.Log('[0] user info : ' + text + '_' + text2, False)
            self.InputRoot.SetActive(False)
            self.SceneRoot.SetActive(True)

    def Start(self):
        if not IPHOStartSceneViewController.Instance:
            DeflectionDefaultManager.Instance().ClearAll()
            IPHOStartSceneViewController.Instance = self
            DontDestroyOnLoad(self.go)
        else:
            self.InputRoot.SetActive(False)
            self.SceneRoot.SetActive(True)


@reg
class IPHODebugBehaviour(Component):
    def HandleDebugBtnClick(self):
        self.DebugView.SetActive(not self.DebugView.activeInHierarchy)


# ================================================================ Z.UI drag
class ZUIDraggableBase(Component):
    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.m_LastMousePosition = V2(0, 0)
        self.m_ForceEndDrag = False

    def OnBeginDrag(self, e):
        if self.m_ForceEndDrag:
            self.m_ForceEndDrag = False
        if self.CanDrag:
            self.m_LastMousePosition = e.position
            self.DoBeginDrag(e, e.position)

    def OnDrag(self, e):
        if self.CanDrag and not self.m_ForceEndDrag:
            diff = V2(e.position.x - self.m_LastMousePosition.x, e.position.y - self.m_LastMousePosition.y)
            diff = self.GetNewDiff(diff)
            vec = self.GetNewPosition(self.TargetRect.anchoredPosition, diff)
            if not self.IsRectTransformInsideScreen(self.TargetRect):
                self.ResetPosition()
                vec = self.TargetRect.anchoredPosition
                self.m_ForceEndDrag = True
            else:
                self.TargetRect.anchoredPosition = vec
            self.m_LastMousePosition = V2(self.m_LastMousePosition.x + diff.x, self.m_LastMousePosition.y + diff.y)
            self.DoDrag(e, vec)

    def OnEndDrag(self, e):
        if self.m_ForceEndDrag:
            self.m_ForceEndDrag = False
        if self.CanDrag:
            self.DoEndDrag(e, e.position)

    def DoBeginDrag(self, e, p):
        pass

    def DoDrag(self, e, p):
        pass

    def DoEndDrag(self, e, p):
        pass

    def GetNewDiff(self, d):
        return V2(self.ModifyDiffBySetting(d.x, self.Horizontal), self.ModifyDiffBySetting(d.y, self.Vertical))

    def ModifyDiffBySetting(self, v, d):
        if d.Enable and d.Scale != 0:
            s = 1 if v > 0 else -1
            v = d.Scale * s if abs(v) > d.Scale else 0
        return v

    def GetNewPosition(self, o, diff):
        return V2(self.ModifyPosBySetting(o.x, diff.x, self.Horizontal), self.ModifyPosBySetting(o.y, diff.y, self.Vertical))

    def ModifyPosBySetting(self, value, diff, d):
        if d.Enable:
            value += diff
        if d.EnableLimit:
            value = clamp(value, d.MinValue, d.MaxValue)
        return value

    def IsRectTransformInsideScreen(self, rt):
        n = sum(1 for p in rt.worldCorners() if 0 <= p[0] < SW and 0 <= p[1] < SH)
        return n == 4

    def UpdateInitPosition(self):
        self.m_InitPosition = self.TargetRect.anchoredPosition

    def ResetPosition(self):
        self.TargetRect.anchoredPosition = V2(self.m_InitPosition.x, self.m_InitPosition.y)


# =========================================================== nano_beam_core
class MaterialProperties:
    def __init__(self, E, nu, a):
        self.ElasticModulus, self.PoissonRatio, self.ThermalExpansionCoefficient = E, nu, a


class CantileverBeam:
    def __init__(self, t, L, I, mat):
        self.Thickness, self.Length, self.SecondMomentArea, self.Material = t, L, I or 0.0, mat

    @property
    def BendingStiffness(self):
        return self.Material.ElasticModulus * self.SecondMomentArea


class DeflectionCalculator:
    def __init__(self):
        self.Deflection = 0.0
        self.Curvature = 0.0
        self.theta_ = 0.0

    def calculateCurvatureFromDeflection(self, R):
        if abs(R - 0.0) < 1e-06:
            self.Curvature = 0.0
            return
        num = self.Deflection / R
        num2 = R / num
        self.Curvature = 1.0 / num2
        self.theta_ = num

    def rotatingAngleInDegree(self):
        return self.theta_ * 57.2957795


class PointLoadCalculator(DeflectionCalculator):
    def __init__(self):
        DeflectionCalculator.__init__(self)
        self.beam_ = None
        self.delta_T_ = 0.0
        self.load_ = -0.05

    def calculateWithPosition(self, x):
        length = self.beam_.Length
        num = length * 0.0136
        num2 = length - num
        EI = self.beam_.BendingStiffness
        if not (x < num2):
            num3 = (-self.load_ * num2 * num2) * (3.0 * x - num2) / (6.0 * EI)
        else:
            num3 = (-self.load_ * x * x) * (3.0 * num2 - x) / (6.0 * EI)
        if self.load_ == -1.0:
            num4, num5, num6, num8 = x * 0.00373, math.pi * 2000.0, 0.0277, self.delta_T_
            num3 += num4 * math.exp(-num6 * num8) * math.cos(num5 * num8)
        self.Deflection = num3
        self.calculateCurvatureFromDeflection(x)


class TwoLayersChiHuaEquation(DeflectionCalculator):
    def __init__(self):
        DeflectionCalculator.__init__(self)
        self.delta_T_ = 0.0
        self.beam_width_ = 0.0
        self.Theta = 0.0

    def calculateWithPosition(self, position):
        b1, b2 = self.beam_1_, self.beam_2_
        t1, t2 = b1.Thickness, b2.Thickness
        a1, a2 = b1.Material.ThermalExpansionCoefficient, b2.Material.ThermalExpansionCoefficient
        E1, E2 = b1.Material.ElasticModulus, b2.Material.ElasticModulus
        I1, I2 = b1.SecondMomentArea, b2.SecondMomentArea
        num = t1 + t2
        num2 = (a2 - a1) * self.delta_T_
        num3 = 2.0 / num / self.beam_width_
        num4 = (t1 * E1 + t2 * E2) / (t1 * E1 * t2 * E2)
        num5 = E1 * I1 + E2 * I2
        num6 = 0.5 * num
        num8 = self.Curvature = num2 / (num3 * num4 * num5 + num6)
        num9 = 1.0 / num8 if num8 != 0 else float('inf')
        self.Theta = position / num9
        self.Deflection = position * self.Theta


class TimoshenkoTwoLayers(DeflectionCalculator):
    def __init__(self):
        DeflectionCalculator.__init__(self)
        self.delta_T_ = 0.0
        self.uniform_distributed_load = 0.0
        self.EI_star = 0.0

    def calculateWithPosition(self, L):
        num = self.beam_1_.Thickness * 1e9
        num2 = self.beam_2_.Thickness * 1e9
        num3 = self.beam_1_.Length * 1e9
        num4 = 35000.0
        E1, E2 = self.beam_1_.Material.ElasticModulus, self.beam_2_.Material.ElasticModulus
        num5 = (num / 2.0 * num + (num + num2 / 2.0) * (E1 / E2) * num2) / (num + E1 / E2 * num2)
        num6 = (num4 * num * num * num / 12.0 + num4 * num2 * num2 * num2 / 12.0 +
                (num4 * num * (num / 2.0 - num5) * (num / 2.0 - num5) +
                 num4 * (E1 / E2) * num2 * (num + num2 / 2.0 - num5) * (num + num2 / 2.0 - num5)))
        self.EI_star = num6 * 280.0
        self.Deflection = self.uniform_distributed_load * (L * L) / (24.0 * self.EI_star) * (6.0 * num3 * num3 - 4.0 * num3 * L + L * L)
        self.calculateCurvatureFromDeflection(L)


class Bench:
    def __init__(self):
        self.default_material_ = True
        self.calculator_ = None
        self.material_1_ = self.material_2_ = None

    @property
    def Calculator(self):
        return self.calculator_

    def set_material_1(self, E, nu, a):
        self.default_material_ = False
        self.material_1_ = MaterialProperties(E, nu, a)

    def set_material_2(self, E, nu, a):
        self.default_material_ = False
        self.material_2_ = MaterialProperties(E, nu, a)


class PointLoadBeam(Bench):
    def __init__(self):
        Bench.__init__(self)
        self.load_ = 0.0

    def set_beam_properties(self, b, h, L):
        self.width, self.height, self.length = b, h, L
        self.I = b * h * h * h / 12.0

    def set_load(self, load):
        self.load_ = load
        self.calculator_.load_ = load

    def set_delta_T(self, t):
        self.calculator_.delta_T_ = t

    def initialize(self):
        self.beam_ = CantileverBeam(self.height, self.length, self.I, self.material_1_)
        self.calculator_ = PointLoadCalculator()
        self.calculator_.beam_ = self.beam_
        self.calculator_.load_ = self.load_

    def execute(self, x, dT):
        self.calculator_.calculateWithPosition(x)


class NewTwoLayersBench(Bench):
    def set_beam_1_properties(self, b, h, L):
        self.width_1, self.height_1, self.length_1 = b, h, L
        self.I1 = b * h * h * h / 12.0

    def set_beam_2_properties(self, b, h, L):
        self.width_2, self.height_2, self.length_2 = b, h, L
        self.I2 = b * h * h * h / 12.0

    def initialize(self):
        self.calculator_ = TwoLayersChiHuaEquation()
        self.calculator_.beam_1_ = CantileverBeam(self.height_1, self.length_1, self.I1, self.material_1_)
        self.calculator_.beam_2_ = CantileverBeam(self.height_2, self.length_2, self.I2, self.material_2_)

    def execute(self, x, dT):
        self.calculator_.delta_T_ = dT
        self.calculator_.beam_width_ = self.width_1
        self.calculator_.calculateWithPosition(x)


class HYDRA2R_100NG_TL_Probe(Bench):
    def __init__(self):
        Bench.__init__(self)
        self.initialize()

    def initialize(self):
        sn = MaterialProperties(280.0, 0.3, 8e-07)
        au = MaterialProperties(78.0, 0.4, 1.42e-05)
        m1 = sn if self.default_material_ else self.material_1_
        m2 = au if self.default_material_ else self.material_2_
        self.calculator_ = TimoshenkoTwoLayers()
        self.calculator_.beam_1_ = CantileverBeam(2e-07, 0.0001, 0, m1)
        self.calculator_.beam_2_ = CantileverBeam(4e-08, 0.0001, 0, m2)

    def execute(self, R, dT):
        self.calculator_.delta_T_ = dT
        self.calculator_.calculateWithPosition(R)


class NanoBeamInterface:
    def __init__(self):
        self.bench_HYDRA2R_100NG_TL_ = HYDRA2R_100NG_TL_Probe()
        self.point_load_beam_ = PointLoadBeam()
        self.new_two_layers_bench_ = NewTwoLayersBench()
        self.original_temperature_ = 300.0

    def set_material_1(self, E, nu, a):
        self.bench_HYDRA2R_100NG_TL_.set_material_1(E, nu, a)

    def set_material_2(self, E, nu, a):
        self.bench_HYDRA2R_100NG_TL_.set_material_2(E, nu, a)
        self.bench_HYDRA2R_100NG_TL_.initialize()

    def update_with_position_and_uniformly_distributed_load(self, R, T, W, adh, dens):
        self.bench_HYDRA2R_100NG_TL_.calculator_.uniform_distributed_load = (
            dens * (W * 1000.0) * (adh * 1000.0 * 1e-09) * 3.5000000000000004e-05 * 9.80665 - 0.05 * dens)
        self.bench_HYDRA2R_100NG_TL_.execute(R, T - self.original_temperature_)
        c = self.bench_HYDRA2R_100NG_TL_.Calculator
        return [c.Deflection, c.rotatingAngleInDegree(), 0.0]

    def set_material_point_load(self, E, nu, a, b, h, L):
        self.point_load_beam_.set_beam_properties(b * 1000.0, h * 1000.0, L * 1000.0)
        self.point_load_beam_.set_material_1(E, nu, a)
        self.point_load_beam_.initialize()

    def update_point_load(self, f):
        self.point_load_beam_.set_load(f)

    def update_point_delta_T(self, t):
        self.point_load_beam_.set_delta_T(t)

    def point_load_position(self, x):
        self.point_load_beam_.execute(x, 0.0)
        c = self.point_load_beam_.Calculator
        return [c.Deflection, c.rotatingAngleInDegree()]

    def init_beam_properties(self):
        self.new_two_layers_bench_.set_beam_1_properties(35000.0, 200.0, 100000.0)
        self.new_two_layers_bench_.set_beam_2_properties(35000.0, 30.0, 100000.0)

    def set_material_properties_1(self, E, nu, a):
        self.new_two_layers_bench_.set_material_1(E, nu, a)

    def set_material_properties_2(self, E, nu, a):
        self.new_two_layers_bench_.set_material_2(E, nu, a)
        self.new_two_layers_bench_.initialize()

    def update_new_two_layers(self, R, T):
        self.new_two_layers_bench_.execute(R, T - self.original_temperature_)
        c = self.new_two_layers_bench_.calculator_
        return [c.Deflection, c.Theta * 57.2957795]


# ================================================================ deflection
class DeflectionApplicationConst:
    BeamLength = 100.0
    BeamLengthFront = 60.0
    ExperimentRatio = 100.0
    ResultRatio = 10000.0
    ExperimentRatioToCM = 0.01
    ExperimentRatioToMM = 0.1
    BeamLengthExp = BeamLength / ExperimentRatio
    BeamLengthFrontExp = BeamLengthFront / ExperimentRatio


DA = DeflectionApplicationConst


@reg
class DeflectionApplication(Component):
    def Awake(self):
        DeflectionDefaultManager.Instance()
        self.m_DController = DeflectionController.Create(self.ViewFinder.DeflectionView)


@reg
class DeflectionViewFinder(Component):
    pass


class DeflectionDefaultManager:
    _m = None

    @staticmethod
    def Instance():
        if DeflectionDefaultManager._m is None:
            DeflectionDefaultManager._m = DeflectionDefaultManager()
        return DeflectionDefaultManager._m

    DEFAULT_PARAM = ['280 0.3 0.8 35 0.2 100', '280 0.3 0.8 35 0.2 100', '280 0.3 0.8 78 0.4 14.2',
                     '280 0.3 0.8 78 0.4 14.2 0.0107 0.0077 0.00318 0.02 0.02 0.02 0.8']

    def GetDeflectionType(self):
        return PlayerPrefs.GetInt('deflection_type', 0)

    def UpdateDeflectionType(self, t):
        PlayerPrefs.SetInt('deflection_type', t)
        PlayerPrefs.Save()

    def GetTransformTypt(self):
        return '-1' if self.GetDeflectionType() <= 0 else '0'

    def GetMirrorTransform(self):
        return PlayerPrefs.GetString('deflection_mirror_transform_' + self.GetTransformTypt(), '0,200,22.29364')

    def GetPSDTransform(self):
        return PlayerPrefs.GetString('deflection_psd_transform_' + self.GetTransformTypt(), '400,200,44.19293')

    def UpdateTransform(self, mv, pv):
        self.GetTransformTypt()

    def GetHeatValue(self):
        return PlayerPrefs.GetFloat('deflection_heat_value_0', 0.0)

    def UpdateHeatValue(self, v):
        pass

    def GetHeatDegree(self):
        return PlayerPrefs.GetFloat('deflection_heat_degree_0', 27.0)

    def UpdateHeatDegree(self, d):
        pass

    def GetDeflectionParam(self):
        t = self.GetDeflectionType()
        return PlayerPrefs.GetString('deflection_param_%d' % t, self.DEFAULT_PARAM[t])

    def ClearAll(self):
        PlayerPrefs.DeleteAll()


class DeflectionController:
    @staticmethod
    def Create(view):
        return DeflectionController(view)

    @staticmethod
    def HeatValueToDegree(v):
        return 27.0 + v * 50.0

    def __init__(self, view):
        self.OnExperimentIsOn = []
        self.OnHeatDegreeChange = []
        self.m_IsOn = False
        self.m_Type = DeflectionDefaultManager.Instance().GetDeflectionType()
        num = DeflectionDefaultManager.Instance().GetHeatValue()
        num2 = DeflectionDefaultManager.Instance().GetHeatDegree()
        IPHODebug.Log('Finish init and now degree is %s' % fmt_g(num2))
        self.m_View = view
        self.m_View.Init(self, num2, num, self.m_Type)
        if self.m_Type == 2:
            for f in self.OnHeatDegreeChange:
                f(num2)

    def OnExperimentBtnClick(self):
        self.m_IsOn = not self.m_IsOn
        for f in self.OnExperimentIsOn:
            f(self.m_IsOn)
        IPHODebug.Log('Click On/Off btn, now experiment state is %s' % tf(self.m_IsOn))

    def UpdateHeatDegree(self, d):
        DeflectionDefaultManager.Instance().UpdateHeatDegree(d)
        for f in self.OnHeatDegreeChange:
            f(d)

    def UpdateHeatValue(self, v):
        DeflectionDefaultManager.Instance().UpdateHeatValue(v)


class ZLinearEquation:
    def __init__(self, p0, p1):
        if isinstance(p1, (int, float)):
            angle = p1
            if angle == 90.0:
                self.a, self.b, self.c = 1.0, 0.0, -p0.x
            elif angle == 0.0:
                self.a, self.b, self.c = 0.0, 1.0, -p0.y
            else:
                self.a = math.tan(angle * (math.pi / 180.0))
                self.c = p0.y - self.a * p0.x
                self.b = -1.0
        else:
            self.a = (p0.y - p1.y) / (p0.x - p1.x)
            self.c = p0.y - self.a * p0.x
            self.b = -1.0

    def SymmetryPoint(self, p):
        n = (self.a * p.x + self.b * p.y + self.c) / (self.a * self.a + self.b * self.b)
        return V2(p.x - 2.0 * self.a * n, p.y - 2.0 * self.b * n)

    def IntersectionPoint(self, l):
        d = self.a * l.b - self.b * l.a
        return V2((self.b * l.c - self.c * l.b) / d, (self.c * l.a - self.a * l.c) / d)


@reg
class DeflectionView(Component):
    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.m_BeamAngle = self.m_BeamDisp = self.m_BeamForce = self.m_BeamPoint = 0.0
        self.m_SampleDensity = self.m_SampleAdhesionThickness = 0.0
        self.m_SampleDensityArray = [0.0, 0.0, 0.0]
        self.m_SampleAdhesionThicknessArray = [0.0, 0.0, 0.0]
        self.m_InitLaserPoint = [V2(0, 0)]
        self.m_IsOn = False
        self.MAX_PSD_DISTANCE = 167.58
        self.m_IsInit = False
        self.DeltaT = 0.0
        self.Result = [0.0, 0.0]

    def HandleDeltaReset(self):
        self.DeltaT = 0.0

    def Update(self):
        if self.m_IsInit and self.Type == 0:
            self.DeltaT += Time.deltaTime()
            self.m_NanoBeamInterface.update_point_delta_T(self.DeltaT)

    def Init(self, d, lastDegree, lastValue, type_):
        self.Type = type_
        if type_ == 1:
            self.TypeObjs[0].SetActive(True)
        elif type_ == 2:
            self.TypeObjs[1].SetActive(True)
        elif type_ == 3:
            self.TypeObjs[2].SetActive(True)
        self.SettingView.Init(self)
        self.m_NanoBeamInterface = NanoBeamInterface()
        self.UpdateNano()
        self.m_DController = d
        d.OnExperimentIsOn.append(self.HandleExperimentIsOn)
        d.OnHeatDegreeChange.append(self.HandleHeatDegreeChange)
        self.m_MirrorItem.Init(self, DeflectionDefaultManager.Instance().GetMirrorTransform())
        self.m_PSDItem.Init(self, DeflectionDefaultManager.Instance().GetPSDTransform())
        self.SetForceController.Init(self)
        self.TemperatureController.Init(self, lastValue)
        self.m_Laser.Init(self)
        self.SampleView.Init(self)
        self.HeatBehaviour.Init(self, lastDegree, DeflectionController.HeatValueToDegree(lastValue))
        self.m_IsInit = True

    def OnExperimentBtnClick(self):
        self.m_DController.OnExperimentBtnClick()

    def UpdateResult(self, r):
        self.Result = r
        self.m_BeamDisp = r[0] / (1000.0 * DA.ExperimentRatio)
        self.m_BeamAngle = -r[1]

    # IDeflectionInteractItemDelegate
    def UpdateTransform(self, isUser=False):
        self.UpdateLaser()
        self.SaveTransform()
        if isUser:
            self.HandleDeltaReset()

    def UpdateTargetHeatDegree(self, v):
        num = DeflectionController.HeatValueToDegree(v)
        self.m_DController.UpdateHeatValue(v)
        self.HeatBehaviour.StartHeat(num)
        IPHODebug.Log('Update heat degree, now target degree is %s' % fmt_g(num))

    def UpdateHeatDegree(self, d):
        self.m_DController.UpdateHeatDegree(d)

    def HandleExperimentIsOn(self, isOn):
        self.m_IsOn = isOn
        self.UpdateLaser()
        self.HandleDeltaReset()

    def HandleHeatDegreeChange(self, d):
        if self.Type == 2:
            self.UpdateResult(self.m_NanoBeamInterface.update_new_two_layers(self.m_BeamPoint * 100.0 * 1000.0, d + 273.0))
            self.TemperatureController.UpdateDegreeText(d)
            self.UpdateLaser()

    def SaveTransform(self):
        DeflectionDefaultManager.Instance().UpdateTransform(self.m_MirrorItem.GetTransform(), self.m_PSDItem.GetTransform())

    def UpdateLaser(self):
        if self.m_IsOn:
            self.CalculatePoints()
            self.m_LaserLine.Points = list(self.m_LaserPoints)
        else:
            self.m_LaserLine.Points = self.m_InitLaserPoint
            self.HideSpotRect()

    def CalculatePoints(self):
        L0 = self.m_Laser.LaserRect.anchoredPosition
        M = self.m_MirrorItem.TargetRect.anchoredPosition
        self.m_LaserPoints = [V2(L0.x, L0.y), V2(M.x, M.y)]
        ez = self.m_MirrorItem.RotateRect.GetEulerAngleZ()
        if ez == 0.0:
            self.m_LaserPoints.append(V2(SW / 2, self.m_LaserPoints[0].y))
            return
        if ez == 90.0:
            self.m_LaserPoints.append(V2(-SW / 2, self.m_LaserPoints[0].y))
            return
        frm = self.m_LaserPoints[1]
        x, y = frm.x, frm.y
        to = ZLinearEquation(self.m_LaserPoints[1], 90.0 - ez).SymmetryPoint(self.m_LaserPoints[0])
        num = (y - to.y) / (x - to.x)
        num2 = 0.0
        num3 = (num2 - y) / num + x
        self.m_BeamPoint = abs(num3)
        if DA.BeamLengthFrontExp <= self.m_BeamPoint <= DA.BeamLengthExp and num3 < 0:
            self.UpdateNanoByAB()
            self.UpdateNanoByD()
            vector = V2(num3, num2 - self.m_BeamDisp)
            self.m_LaserPoints.append(vector)
            vector2 = ZLinearEquation(self.m_LaserPoints[2], 90.0 - self.m_BeamAngle).SymmetryPoint(self.m_LaserPoints[1])
            line = ZLinearEquation(vector2, self.m_LaserPoints[2])
            rr, ap = self.m_PSDItem.RotateRect, self.m_PSDItem.TargetRect.anchoredPosition
            l = ZLinearEquation(ap, -rr.GetEulerAngleZ())
            if dist2(line.IntersectionPoint(l), ap) < rr.sizeDelta.x / 2:
                self.m_LaserPoints.append(line.IntersectionPoint(l))
            else:
                self.m_LaserPoints.append(self.GetLengthenPoint(vector, vector2, 500.0))
            num4 = dist2(self.m_LaserPoints[3], ap) * (DA.ResultRatio / DA.ExperimentRatio)
            if dist2(self.m_LaserPoints[3], V2(0, 0)) > self.MAX_PSD_DISTANCE:
                self.HideSpotRect()
            else:
                self.m_SpotRect.SetAnchoredPosY(num4 if self.m_LaserPoints[3].y > ap.y else -num4)
        else:
            self.m_LaserPoints.append(self.GetLengthenPoint(frm, to, 500.0))
            self.HideSpotRect()

    def HideSpotRect(self):
        self.m_SpotRect.SetAnchoredPosY(220.0)

    def GetLengthenPoint(self, frm, to, length):
        d = dist2(to, frm)
        return V2(frm.x + (to.x - frm.x) * length / d, frm.y + (to.y - frm.y) * length / d)

    def UpdateNano(self):
        t = DeflectionDefaultManager.Instance().GetDeflectionType()
        a = [float(s) for s in DeflectionDefaultManager.Instance().GetDeflectionParam().split(' ')]
        nb = self.m_NanoBeamInterface
        if t in (0, 1):
            nb.set_material_point_load(a[0], a[1], 1e-06 * a[2], a[3], a[4], a[5])
            nb.update_point_load(t - 1)
        elif t == 2:
            nb.init_beam_properties()
            nb.set_material_properties_1(a[0], a[1], 1e-06 * a[2])
            nb.set_material_properties_2(a[3], a[4], 1e-06 * a[5])
        elif t == 3:
            nb.set_material_1(a[0], a[1], 1e-06 * a[2])
            nb.set_material_2(a[3], a[4], 1e-06 * a[5])
            self.m_SampleDensityArray = a[6:9]
            self.m_SampleAdhesionThicknessArray = a[9:12]
            self.m_SampleDensityRatio = a[12]
            self.OnUpdateSample(3)

    def OnParamChange(self):
        self.UpdateNano()

    def UpdateForceValue(self, v):
        mx, mn = self.m_MaxSetForce, self.m_MinSetForce
        self.m_BeamForce = mx - (mx - mn) * ((100.0 - v) / (100.0 - -100.0))
        self.m_NanoBeamInterface.update_point_load(self.m_BeamForce * -1.0)
        self.SetForceController.UpdateForceText(self.m_BeamForce * 1.0)

    def UpdateNanoByAB(self):
        if self.Type in (0, 1):
            self.UpdateResult(self.m_NanoBeamInterface.point_load_position(self.m_BeamPoint * 100.0 * 1000.0))

    def UpdateNanoByD(self):
        if self.Type == 3:
            self.UpdateResult(self.m_NanoBeamInterface.update_with_position_and_uniformly_distributed_load(
                self.m_BeamPoint * 100.0 * 1000.0, 300.0, self.m_SampleDensityRatio,
                self.m_SampleAdhesionThickness, self.m_SampleDensity))

    def OnUpdateSample(self, i):
        if i == 3:
            self.m_SampleDensity = self.m_SampleAdhesionThickness = 0.0
        else:
            self.m_SampleDensity = self.m_SampleDensityArray[i]
            self.m_SampleAdhesionThickness = self.m_SampleAdhesionThicknessArray[i]


@reg
class DeflectionHeatBehaviour(Component):
    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.m_NowHeatFrame = 0
        self.m_Delegate = None

    def Init(self, d, start, target):
        self.m_Delegate = d
        self.StartHeat2(start, target)

    def StartHeat2(self, start, target):
        IPHODebug.Log('StartHeat from %s to %s' % (fmt_g(start), fmt_g(target)))
        self.NowHeatDegree = self.StartHeatDegree = start
        self.TargetHeatDegree = target
        self.StartTime = Time.time()
        self.IsNeedHeatUpdate = True
        self.IsHeatUp = self.TargetHeatDegree >= self.StartHeatDegree
        self.Coefficient = 5.0 if self.IsHeatUp else 7.2
        if self.m_Delegate:
            self.m_Delegate.UpdateHeatDegree(self.NowHeatDegree)

    def StartHeat(self, target):
        self.StartHeat2(self.NowHeatDegree, target)

    def FixedUpdate(self):
        if not self.IsNeedHeatUpdate:
            return
        self.m_NowHeatFrame += 1
        if self.m_NowHeatFrame >= 6:
            self.m_NowHeatFrame = 0
            num = (Time.time() - self.StartTime) * self.m_TimeSpeed
            if self.IsHeatUp:
                d = self.TargetHeatDegree - self.StartHeatDegree
                e = math.exp(-num / (self.Coefficient * d)) if d != 0 else 0.0
                self.NowHeatDegree = self.StartHeatDegree + d * (1.0 - e)
            else:
                d = self.StartHeatDegree - self.TargetHeatDegree
                e = math.exp(-num / (self.Coefficient * d)) if d != 0 else 0.0
                self.NowHeatDegree = self.TargetHeatDegree + d * e
            if self.m_Delegate:
                self.m_Delegate.UpdateHeatDegree(self.NowHeatDegree)

    def HandleSpeedClick(self):
        self.m_TimeSpeed = 1 if self.m_TimeSpeed != 1 else 10


@reg
class DeflectionTemperatureController(Component):
    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.m_TargetValue = 0.0
        self.m_Delegate = None

    def Init(self, d, last):
        self.m_Delegate = d
        self.UpdateValueText(last)

    def HandleUpdateValueClick(self, v):
        v *= 2.0
        self.m_TargetValue += v
        self.UpdateValueText(self.m_TargetValue)
        IPHODebug.Log('Click update degree button %s, and now target degree is %s' % (fmt_g(v), fmt_g(self.m_TargetValue)))

    def HandleEnterClick(self):
        if self.m_Delegate:
            self.m_Delegate.UpdateTargetHeatDegree(self.m_TargetValue / 1000.0)

    def UpdateValueText(self, v):
        v = clamp(v, 0.0, 100.0)
        self.m_TargetValue = v
        self.ValueText.text = fmt_g(v)

    def UpdateDegreeText(self, d):
        self.DegreeText.text = fmt_fixed(d, 1)


@reg
class DeflectionSetForceController(Component):
    def Init(self, d):
        self.SetForceItem.Init(d)

    def UpdateForceText(self, f):
        self.ForceText.text = fmt_fixed(f, 2)


@reg
class DeflectionSetForceItem(ZUIDraggableBase):
    def Init(self, d):
        self.m_Delegate = d

    def DoDrag(self, e, pos):
        self.m_Delegate.UpdateForceValue(pos.x)

    def HandleForceUpdate(self, off):
        v = clamp(self.TargetRect.anchoredPosition.x + off, -100.0, 100.0)
        self.TargetRect.SetAnchoredPosX(v)
        self.m_Delegate.UpdateForceValue(v)


@reg
class DeflectionInteractItem(ZUIDraggableBase):
    def __init__(self, go, d):
        ZUIDraggableBase.__init__(self, go, d)
        self.m_ControlTweeners = None
        self.m_Delegate = None

    def Start(self):
        self.m_ControlTweeners = [None] * len(self.ControlCanvasGroups)

    def Init(self, d, trans):
        self.m_Delegate = d
        self.DragRotateItem.Init(self)
        self.SetTransform(trans)

    def OnUpBtnClick(self):
        self.TargetRect.SetAnchoredPosOffsetY(0.1)
        self.LogTransform('[UP]')
        self.UpdateTransform()

    def OnDownBtnClick(self):
        self.TargetRect.SetAnchoredPosOffsetY(-0.1)
        self.LogTransform('[DOWN]')
        self.UpdateTransform()

    def OnRightBtnClick(self):
        self.TargetRect.SetAnchoredPosOffsetX(0.1)
        self.LogTransform('[RIGHT]')
        self.UpdateTransform()

    def OnLeftBtnClick(self):
        self.TargetRect.SetAnchoredPosOffsetX(-0.1)
        self.LogTransform('[LEFT]')
        self.UpdateTransform()

    def OnClockBtnClick(self):
        self.RotateRect.SetRotateOffsetZ(-0.1)
        self.LogTransform('[CLOCK]')
        self.UpdateTransform()

    def OnCounterClockBtnClick(self):
        self.RotateRect.SetRotateOffsetZ(0.1)
        self.LogTransform('[COUNTER CLOCK]')
        self.UpdateTransform()

    def SetTransform(self, data):
        a = [float(s) for s in data.split(',')]
        self.TargetRect.SetAnchoredPosX(a[0])
        self.TargetRect.SetAnchoredPosY(a[1])
        self.RotateRect.SetRotateZ(-a[2])
        self.UpdateTransform(False)

    def GetTransform(self):
        p = self.TargetRect.anchoredPosition
        return '%s,%s,%s' % (fmt_g(p.x), fmt_g(p.y), fmt_g(self.RotateRect.GetEulerAngleZ()))

    def DoBeginDrag(self, e, p):
        self.LogTransform('start drag')

    def DoDrag(self, e, p):
        self.UpdateTransform()

    def DoEndDrag(self, e, p):
        self.LogTransform('end drag')

    def OnPointerEnter(self, e):
        self.CheckControlTweener()
        for i, cg in enumerate(self.ControlCanvasGroups):
            cg.alpha = 0.0
            cg.SetActive(True)
            self.m_ControlTweeners[i] = cg.DOFade(1.0, 0.3)

    def OnPointerExit(self, e):
        self.CheckControlTweener()
        for i, cg in enumerate(self.ControlCanvasGroups):
            cg.alpha = 1.0
            cg.SetActive(False)
            self.m_ControlTweeners[i] = cg.DOFade(0.0, 0.3)

    def CheckControlTweener(self):
        if self.m_ControlTweeners is None:
            self.m_ControlTweeners = [None] * len(self.ControlCanvasGroups)
        for i, t in enumerate(self.m_ControlTweeners):
            if t:
                t.Kill()
                self.m_ControlTweeners[i] = None

    def UpdateTransform(self, notify=True):
        if notify and self.m_Delegate:
            self.m_Delegate.UpdateTransform(True)
        p, ez = self.TargetRect.anchoredPosition, self.RotateRect.GetEulerAngleZ()
        if self.DisplayUnit == 0:
            k = DA.ExperimentRatioToCM
            self.TransformText.text = '(' + fmt_fixed(p.x * k, 1) + '(cm), ' + fmt_fixed(p.y * k, 1) + '(cm)), ' + fmt_fixed(ez, 1)
        elif self.DisplayUnit == 1:
            k = DA.ExperimentRatioToMM
            self.TransformText.text = '(' + fmt_fixed(p.x * k, 0) + ' mm, ' + fmt_fixed(p.y * k, 0) + ' mm), ' + fmt_fixed(ez, 1) + ' '

    def ChangeCanDrag(self, enable):
        self.CanDrag = enable
        self.LogTransform('end rotate' if self.CanDrag else 'start rotate')

    def GetRotatePosition(self):
        return self.RotateRect.position

    def UpdateRotateRect(self, angle):
        if self.RotateLimit:
            angle = clamp(angle, self.RotateMin, self.RotateMax)
        self.RotateRect.SetRotateZ(angle)
        self.UpdateTransform()

    def LogTransform(self, state):
        p = self.TargetRect.anchoredPosition
        IPHODebug.Log('%s %s : (%s, %s), %s' % (self.go.name, state, fmt_fixed(p.x, 3), fmt_fixed(p.y, 3),
                                                fmt_fixed(self.RotateRect.GetEulerAngleZ(), 3)))


@reg
class DeflectionDragRotateItem(Component):
    def Init(self, d):
        self.m_Delegate = d

    def OnBeginDrag(self, e):
        self.m_Delegate.ChangeCanDrag(False)

    def OnDrag(self, e):
        c = self.m_Delegate.GetRotatePosition()
        num = math.atan2(e.position.y - c.y, e.position.x - c.x) * 57.29578
        self.m_Delegate.UpdateRotateRect(num - 90.0)

    def OnEndDrag(self, e):
        self.m_Delegate.ChangeCanDrag(True)


@reg
class DeflectionLaser(Component):
    def Init(self, d):
        self.m_Delegate = d
        self.m_OriPos = self.LaserRect.anchoredPosition
        self.RandomShake()

    def RandomShake(self):
        if not self.UseShake:
            return
        self.ShakeVibrato = random_range_int(1, 5)

        def done():
            self.LaserRect.anchoredPosition = self.m_OriPos
            self.RandomShake()
        DOShakeAnchorPos(self.LaserRect, self.ShakeDuration, self.ShakeStrength, self.ShakeVibrato) \
            .OnUpdate(lambda: self.m_Delegate.UpdateTransform() if self.m_Delegate else None).OnComplete(done)


@reg
class DeflectionSpot(Component):
    def Start(self):
        self.m_OriPos = self.SpotRect.anchoredPosition
        self.RandomShake()

    def RandomShake(self):
        self.ShakeVibrato = random_range_int(1, 5)

        def done():
            self.SpotRect.anchoredPosition = self.m_OriPos
            self.RandomShake()
        DOShakeAnchorPos(self.SpotRect, self.ShakeDuration, (self.ShakeStrength.x, self.ShakeStrength.y), self.ShakeVibrato).OnComplete(done)


@reg
class DeflectionSampleView(Component):
    def Start(self):
        self.ResetBtnColor()
        self.ButtonImages[3].color = self.SelectColor

    def Init(self, d):
        self.m_Delegate = d

    def HandleSampleBtnClick(self, t):
        self.ResetBtnColor()
        self.m_Type = t
        IPHODebug.Log('Update liquid type : %s' % (['Sample0', 'Sample1', 'Sample2', 'Sample3'][t]))
        self.m_Delegate.OnUpdateSample(t)
        self.ButtonImages[t].color = self.SelectColor

    def ResetBtnColor(self):
        for im in self.ButtonImages:
            im.color = self.UnSelectColor


@reg
class DeflectionSettingView(Component):
    def Init(self, d):
        self.m_Delegate = d
        t = DeflectionDefaultManager.Instance().GetDeflectionType()
        a = DeflectionDefaultManager.Instance().GetDeflectionParam().split(' ')

        def set_(f, v):
            if f:
                f.text = v
        set_(self.FieldM11, a[0])
        set_(self.FieldM12, a[1])
        set_(self.FieldM13, a[2])
        if t in (0, 1):
            set_(self.FieldB, a[3])
            set_(self.FieldH, a[4])
            set_(self.FieldL, a[5])
            self.HandleGroup(self.GroupA)
        elif t == 2:
            set_(self.FieldM21, a[3])
            set_(self.FieldM22, a[4])
            set_(self.FieldM23, a[5])
            self.HandleGroup(self.GroupB)
        elif t == 3:
            for f, v in zip((self.FieldM21, self.FieldM22, self.FieldM23, self.FieldSR1, self.FieldSR2, self.FieldSR3,
                             self.FieldST1, self.FieldST2, self.FieldST3, self.FieldSD), a[3:13]):
                set_(f, v)
            self.HandleGroup(self.GroupC)

    def HandleToggleBtnClick(self):
        self.SettingPanel.SetActive(not self.SettingPanel.activeInHierarchy)

    def HandleBtnClick(self):
        self.m_Delegate.OnParamChange()
        self.SettingPanel.SetActive(False)

    def HandleGroup(self, g):
        for o in g['ActiveObjs'] if isinstance(g, dict) else g.ActiveObjs:
            if o:
                o.SetActive(True)
        for o in g['UnActiveObjs'] if isinstance(g, dict) else g.UnActiveObjs:
            if o:
                o.SetActive(False)


@reg
class TMP_InputField(Component):
    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.text = ''


@reg
class DeflectionDebugView(Component):
    pass


@reg
class DeflectionRecordLineView(Component):
    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.m_Points = []
        self.m_IsRecord = False
        self.m_Frame = 0

    def Start(self):
        self.RecordBtn.interactable = True
        self.StopBtn.interactable = False
        self.ResetBtn.interactable = False

    def HandelClearBtnClick(self):
        self.m_Points = [V2(0, 0), V2(0, 0)]
        self.LineRenderer.Points = list(self.m_Points)
        self.PointTextBg.SetWidth(0.0)
        self.PointText.text = ''
        self.PointRect.anchoredPosition = V2(0, 0)
        self.NowIndex = self.TotalIndex = self.m_Frame = 0

    def HandleRecordBtnClick(self):
        self.HandelClearBtnClick()
        self.m_IsRecord = True
        self.RecordBtn.interactable, self.StopBtn.interactable, self.ResetBtn.interactable = False, True, False

    def HandleStopBtnClick(self):
        self.m_IsRecord = False
        self.RecordBtn.interactable, self.StopBtn.interactable, self.ResetBtn.interactable = False, False, True

    def HandleResetBtnClick(self):
        self.HandelClearBtnClick()
        self.m_IsRecord = False
        self.RecordBtn.interactable, self.StopBtn.interactable, self.ResetBtn.interactable = True, False, False

    def FixedUpdate(self):
        if Input.GetKeyDown('Right'):
            self.NowIndex += 1
            self.UpdatePointIndex()
        if Input.GetKeyDown('Left'):
            self.NowIndex -= 1
            self.UpdatePointIndex()
        if not self.m_IsRecord:
            return
        self.m_Frame += 1
        if self.m_Frame < self.FRAME_BATCH:
            return
        self.m_Frame = 0
        y = self.SpotRootRect.anchoredPosition.y
        if not abs(y) > 100.0:
            vec = V2(self.TotalIndex * self.RatioX, y)
            if self.TotalIndex < 2:
                self.m_Points[self.TotalIndex] = vec
            else:
                self.m_Points.append(vec)
            self.TotalIndex += 1
            self.LineRenderer.Points = list(self.m_Points)
            if self.TotalIndex > self.MAX_NUM:
                self.m_IsRecord = False

    def OnDrag(self, e):
        self.NowIndex = int((e.position.x - self.ViewTransform.position.x) / self.RatioX)
        self.UpdatePointIndex()

    def OnEndDrag(self, e):
        pass

    def UpdatePointIndex(self):
        if self.NowIndex >= self.TotalIndex:
            return
        if self.NowIndex < 0:       # List<>[-1] throws in C#; the app logs it and goes on
            IPHODebug.Log('[ ERROR ] System.ArgumentOutOfRangeException')
            return
        p = self.m_Points[self.NowIndex]
        if not abs(p.y) > 100.0:
            self.PointRect.anchoredPosition = p
            text = '%s mm, t = %d s' % (fmt_fixed(p.y / 100.0, 4), self.NowIndex)
            self.PointText.text = text
            px, py = p.x, p.y + 30.0
            num = self.PointText.preferredWidth + 20.0
            self.PointTextBg.SetWidth(num)
            num2 = (1024.0 - 20.0) / 2.0
            if num + px > num2:
                px = num2 - num
            self.PointTextBg.anchoredPosition = V2(px, py)
            IPHODebug.Log('check the record : ' + text)


# =============================================================== diffraction
@reg
class IPHOLongPressBtn(Component):
    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.m_NowFrame = 0
        self.m_IsLongPress = False
        self.m_IsFirstLongPress = True

    def FixedUpdate(self):
        if self.m_IsLongPress:
            self.m_NowFrame += 1
            if self.m_NowFrame >= (self.FirstFrameRate if self.m_IsFirstLongPress else self.FrameRate):
                self.m_IsFirstLongPress = False
                self.m_NowFrame = 0
                self.TargetBtn.onClick.Invoke()

    def OnPointerDown(self, e):
        self.m_IsLongPress = True
        self.TargetImage.color = WHITE

    def OnPointerUp(self, e):
        self.m_IsFirstLongPress = True
        self.m_IsLongPress = False
        self.m_NowFrame = 0
        self.TargetImage.color = CLEAR


class DiffractionModel:
    def __init__(self):
        self.LaserType = 0
        self.Distance = 10.0
        self.IsOn = False

    def IsExperimentAvaliable(self):
        return self.LaserType != 0

    def ToggleIsOn(self):
        self.IsOn = not self.IsOn


class Diffraction0Model:
    def __init__(self):
        self.LaserType = 0
        self.Distance = V2(0, 0)
        self.m_OffsetDistance = V2(37, -29)
        self.IsOn = False

    @property
    def RealDistance(self):
        return V2(self.Distance.x - self.m_OffsetDistance.x, self.Distance.y - self.m_OffsetDistance.y)

    def ForceUpdateDistance(self, p):
        self.Distance = V2(clamp(p.x, -50, 50), clamp(p.y, -50, 50))

    def UpdateDistance(self, o):
        self.Distance = V2(clamp(self.Distance.x + o.x, -50, 50), clamp(self.Distance.y + o.y, -50, 50))

    def IsExperimentAvaliable(self):
        return self.LaserType != 0

    def ToggleIsOn(self):
        self.IsOn = not self.IsOn


LASER_NAMES = ['None', 'A', 'B', 'C', '4', '5', '6', '7', '8']


class DiffractionPrepareController:
    @staticmethod
    def Create(view, controller):
        return DiffractionPrepareController(view, controller)

    def __init__(self, view, controller):
        self.m_View = view
        self.m_IsPrepare = False
        self.m_Job = None
        controller.OnLaserTypeChange.append(lambda t: self.Prepare(t, None))

    @property
    def IsPrepare(self):
        return self.m_IsPrepare

    def UpdateLengthList(self, l):
        self.m_LengthList = l

    def Prepare(self, type_, completion):
        label = self.m_View.GetLabel(type_)
        if label:
            IPHODebug.Log('prepare asset ' + label['m_LabelString'])
            self.m_IsPrepare = True
            self.m_View.Show()
            self.LoadSpriteGroup(label, completion)

    def LoadSpriteGroup(self, label, completion):
        """Addressables.LoadAssetsAsync(label): the pictures are made here instead of
        read from the asset bundles; the progress bar counts them in as they would load"""
        total = self.m_View.TotalNumber
        job = [0]
        self.m_Job = job
        DiffractionImages.set_label(label['m_LabelString'])

        def step():
            if self.m_Job is not job:
                return
            k = min(total, job[0] + int(math.ceil(total / 40.0)))
            while job[0] < k:
                job[0] += 1
                self.m_View.UpdateProgress()
            if job[0] >= total:
                IPHODebug.Log('finish prepare asset, asset count is %d' % total)
                self.m_IsPrepare = False
                self.m_View.OnProgressDone()
                if completion:
                    completion()
            else:
                later(0.05, step)
        later(0.05, step)

    def GetResult(self, model):
        return DiffractionImages.get('%snm-%scm' % (fmt_g(self.m_LengthList[model.LaserType]), fmt_g(model.Distance)))

    def GetGrayResult(self, model):
        return DiffractionImages.get('%snm-%scm-tiff' % (fmt_g(self.m_LengthList[model.LaserType]), fmt_g(model.Distance)))

    def GetResultByName(self, name):
        return DiffractionImages.get(name)


@reg
class DiffractionPrepareView(Component):
    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.m_IsPrepareReady = self.m_IsDelayReady = False

    def Show(self):
        self.ViewCanvasGroup.SetActive(True)
        self.ViewCanvasGroup.DOFade(1.0, 0.5)

        def done():
            self.m_IsDelayReady = True
            self.CheckDelay()
        self.CountdownBarImage.DOFillAmount(1.0, self.PrepareDelay).OnComplete(done)

    def GetLabel(self, t):
        return None if t == 0 else self.LabelList[t]

    def UpdateProgress(self):
        self.NowProgress += 1
        self.BarImage.fillAmount = self.NowProgress / float(self.TotalNumber)

    def OnProgressDone(self):
        self.m_IsPrepareReady = True
        self.CheckDelay()

    def Dismiss(self):
        def done():
            self.m_IsDelayReady = self.m_IsPrepareReady = False
            self.NowProgress = 0
            self.BarImage.fillAmount = 0.0
            self.CountdownBarImage.fillAmount = 0.0
            self.ViewCanvasGroup.SetActive(False)
        self.ViewCanvasGroup.DOFade(0.0, 0.5).OnComplete(done)

    def CheckDelay(self):
        if self.m_IsDelayReady and self.m_IsPrepareReady:
            self.Dismiss()


class DiffractionControllerBase:
    def __init__(self):
        self.OnExperimentImgChange = []
        self.OnExperimentIsOn = []
        self.OnLaserTypeChange = []
        self.OnScreenDistanceChange = []

    def NotifyExperimentIsOn(self):
        for f in self.OnExperimentIsOn:
            f(self.m_Model.IsOn)

    def NotifyLaserTypeChange(self):
        for f in self.OnLaserTypeChange:
            f(self.m_Model.LaserType)

    def UpdateCurrentExperimentIsOn(self, isOn):
        self.m_Model.IsOn = isOn
        self.UpdateExperimentImage()
        self.NotifyExperimentIsOn()


class DiffractionController(DiffractionControllerBase):
    @staticmethod
    def Create(vf):
        return DiffractionController(vf)

    def __init__(self, vf):
        DiffractionControllerBase.__init__(self)
        self.m_View = vf.DiffractionView
        self.m_View.Init(self)
        vf.ColorPicker.Init(self)
        self.m_Model = DiffractionModel()
        self.m_PrepareController = DiffractionPrepareController.Create(vf.PrepareView, self)
        self.m_PrepareController.UpdateLengthList(self.m_View.LengthList)
        IPHODebug.Log('Finish init')

    def UpdateCurrentLaser(self, t):
        self.m_Model.LaserType = t
        self.NotifyLaserTypeChange()
        self.UpdateExperimentImage()
        IPHODebug.Log('Set laser %s' % LASER_NAMES[t])

    def UpdateCurrentDistance(self, d):
        self.m_Model.Distance = d
        for f in self.OnScreenDistanceChange:
            f(d)
        self.UpdateExperimentImage()
        IPHODebug.Log('Modify screen distance, now distance is %s' % fmt_g(d))

    def ToggleCurrentExperimentIsOn(self):
        if not self.m_Model.IsExperimentAvaliable():
            IPHODebug.Log('Click On/Off btn, but not set laser, so experiment state is still %s' % tf(self.m_Model.IsOn))
            return
        self.m_Model.ToggleIsOn()
        self.UpdateExperimentImage()
        self.NotifyExperimentIsOn()
        IPHODebug.Log('Click On/Off btn, now experiment state is %s' % tf(self.m_Model.IsOn))

    def UpdateExperimentImage(self):
        if not self.m_Model.IsOn or self.m_Model.LaserType == 0:
            self.m_View.ResetExperimentImage()
        else:
            if self.m_PrepareController.IsPrepare:
                return
            self.m_View.UpdateExperimentImage(self.m_PrepareController.GetResult(self.m_Model),
                                              self.m_PrepareController.GetGrayResult(self.m_Model))
        for f in self.OnExperimentImgChange:
            f()


@reg
class DiffractionApplication(Component):
    def Awake(self):
        self.m_DController = DiffractionController.Create(self.ViewFinder)
        self.ViewFinder.LaserPosition.Init(self.m_DController)


@reg
class DiffractionViewFinder(Component):
    pass


class Diffraction0Controller(DiffractionControllerBase):
    @staticmethod
    def Create(view, prep, picker):
        return Diffraction0Controller(view, prep, picker)

    def __init__(self, view, prep, picker):
        DiffractionControllerBase.__init__(self)
        self.m_Model = Diffraction0Model()
        self.m_View = view
        self.m_View.Init(self, self)
        picker.Init(self)
        self.m_PrepareController = DiffractionPrepareController.Create(prep, self)
        IPHODebug.Log('Finish init')

    def _pos(self):
        d = self.m_Model.Distance
        return '(%s, %s)' % (fmt_fixed(d.x, 1), fmt_fixed(d.y, 1))

    def OnPosXChange(self, x):
        self.m_Model.UpdateDistance(V2(x, 0))
        self.NotifyPosDidChange()
        IPHODebug.Log('Modify sample pos X, now pos is ' + self._pos())

    def OnPosYChange(self, y):
        self.m_Model.UpdateDistance(V2(0, y))
        self.NotifyPosDidChange()
        IPHODebug.Log('Modify sample pos Y, now pos is ' + self._pos())

    def OnPosChange(self, p):
        self.m_Model.ForceUpdateDistance(p)
        self.NotifyPosDidChange()

    def UpdateCurrentLaser(self, t):
        self.m_Model.LaserType = t
        self.NotifyLaserTypeChange()
        self.UpdateExperimentImage()
        IPHODebug.Log('Set laser %s' % LASER_NAMES[t])

    def UpdateCurrentDistance(self, d):
        pass

    def ToggleCurrentExperimentIsOn(self):
        if self.m_Model.IsExperimentAvaliable():
            self.m_Model.ToggleIsOn()
            self.UpdateExperimentImage()
            self.NotifyExperimentIsOn()
            IPHODebug.Log('Click On/Off btn, now experiment state is %s' % tf(self.m_Model.IsOn))

    def UpdateExperimentImage(self):
        if not self.m_Model.IsOn or self.m_Model.LaserType == 0:
            self.m_View.ResetExperimentImage()
        else:
            if self.m_PrepareController.IsPrepare:
                return
            rd = self.m_Model.RealDistance
            num, num2 = int(rd.x) * 100, int(rd.y) * 100
            pc = self.m_PrepareController
            r = pc.GetResultByName('632.8nm-50cm-%dum-%dum' % (num, num2))
            r2 = pc.GetResultByName('632.8nm-50cm-%dum-%dum-tiff' % (num, num2))
            if not r:
                r = pc.GetResultByName('632.8nm-50cm-900um-900um')
            if not r2:
                r2 = pc.GetResultByName('632.8nm-50cm-900um-900um')
            self.m_View.UpdateExperimentImage(r, r2)
        for f in self.OnExperimentImgChange:
            f()

    def NotifyPosDidChange(self):
        self.UpdateExperimentImage()
        self.m_View.HandlePosDidChange(self.m_Model.Distance)


@reg
class Diffraction0Application(Component):
    def Awake(self):
        self.m_Controller = Diffraction0Controller.Create(self.Diffraction0View, self.PrepareView, self.ColorPicker)
        self.LaserPosition.Init(self.m_Controller)


class ExperimentImageView(Component):
    def ResetExperimentImage(self):
        if self.ExperimentImage.sprite or not col_eq(self.ExperimentImage.color, BLACK):
            self.ExperimentImage.sprite = None
            self.ExperimentImage.color = BLACK
            self.ExperimentGaryImage.sprite = None
            self.ExperimentGaryImage.color = BLACK

    def UpdateExperimentImage(self, sp, sp2):
        if not sp:
            self.ResetExperimentImage()
            return
        if col_eq(self.ExperimentImage.color, BLACK):
            self.ExperimentImage.color = WHITE
            self.ExperimentGaryImage.color = WHITE
        self.ExperimentImage.sprite = sp
        self.ExperimentGaryImage.sprite = sp2

    def HandleExperimentIsOn(self, isOn):
        if isOn:
            DOTweenSequence().Append(self.LightImage1.DOFillAmount(1.0, 0.3)).Append(self.LightImage2.DOFillAmount(1.0, 0.3))
            return
        self.LightImage1.fillAmount = 0.0
        self.LightImage2.fillAmount = 0.0

    def HandleLaserTypeChange(self, t):
        self.IsOnBtn.interactable = t != 0

    def HandelToggleImage(self):
        self.ImageObj.SetActive(not self.ImageObj.activeInHierarchy)


@reg
class DiffractionView(ExperimentImageView):
    def Init(self, c):
        self.m_DController = c
        c.OnScreenDistanceChange.append(self.HandleDistanceChange)
        c.OnExperimentIsOn.append(self.HandleExperimentIsOn)
        c.OnLaserTypeChange.append(self.HandleLaserTypeChange)
        self.ScreenItem.Init(c)
        self.InitLightPosAndWidth()
        self.CreateLasers()

    def InitLightPosAndWidth(self):
        self.LightImage1.rectTransform.SetWidth(self.SampleTrans.position.x - self.LaserPointTrans.position.x - 30.0)
        sp = self.SampleTrans.position
        self.LightImage2.go.rt.position = V2(sp.x + 60.0, sp.y)
        self.LightImage2.rectTransform.SetWidth(self.ScreenTrans.position.x - self.SampleTrans.position.x - 60.0)

    def HandleToggleExperimentIsOn(self):
        self.m_DController.ToggleCurrentExperimentIsOn()

    def HandleDistanceChange(self, d):
        self.LightImage2.rectTransform.SetWidth(self.ScreenTrans.position.x - self.SampleTrans.position.x - 60.0)

    def CreateLasers(self):
        for i in range(1, len(self.LengthList)):
            go = Instantiate(self.LaserPrefab, self.LaserParent)
            go.get('DiffractionLaserItem').Init(self.LengthList[i], i)


@reg
class Diffraction0View(ExperimentImageView):
    def Init(self, d, c):
        self.m_Delegate = d
        self.m_DController = c
        c.OnLaserTypeChange.append(self.HandleLaserTypeChange)
        c.OnExperimentIsOn.append(self.HandleExperimentIsOn)

    def HandleXBtnClick(self, x):
        if self.m_Delegate:
            self.m_Delegate.OnPosXChange(x)

    def HandleYBtnClick(self, y):
        if self.m_Delegate:
            self.m_Delegate.OnPosYChange(y)

    def HandlePosDidChange(self, p):
        self.PosX.text = str(int(p.x) * 100)
        self.PosY.text = str(int(p.y) * 100)

    def HandleToggleExperimentIsOn(self):
        self.m_DController.ToggleCurrentExperimentIsOn()

    def HandleSetBtnClick(self):
        self.m_Delegate.OnPosChange(V2(int(int(self.PosXText.text) / 100), int(int(self.PosYText.text) / 100)))


@reg
class DiffractionScreenItem(ZUIDraggableBase):
    def Init(self, c):
        self.m_DController = c

    def DoDrag(self, e, p):
        self.SetArrowActive(self.RightArrow, self.TargetRect.anchoredPosition.x < self.Horizontal.MaxValue)
        self.SetArrowActive(self.LeftArrow, self.TargetRect.anchoredPosition.x > self.Horizontal.MinValue)
        self.DistanceText.text = self.GetCurrentDistance()

    def SetArrowActive(self, a, out):
        if a.activeInHierarchy != out:
            a.SetActive(out)

    def GetCurrentDistance(self):
        x, h = self.TargetRect.anchoredPosition.x, self.Horizontal
        d = 10.0 + math.floor((100.0 - 10.0) * ((x - h.MinValue) / (h.MaxValue - h.MinValue)))
        self.m_DController.UpdateCurrentDistance(d)
        return fmt_fixed(d, 2) + ' cm'

    def DoEndDrag(self, e, p):
        IPHODebug.Log('Start drag screen from ' + self.GetCurrentDistance())

    def DoBeginDrag(self, e, p):
        IPHODebug.Log('End drag screen to ' + self.GetCurrentDistance())


@reg
class DiffractionLaserItem(ZUIDraggableBase):
    def __init__(self, go, d):
        ZUIDraggableBase.__init__(self, go, d)
        self.LaserRect = None

    def DoEndDrag(self, e, p):
        IPHODebug.Log('End drag laser %s' % LASER_NAMES[self.Type])
        if self.LaserRect:
            lr = self.LaserRect
            DOMove(self.TargetRect, lr.position, 0.5).OnComplete(lambda: lr.go.get('DiffractionLaserPosition').DoChangeType())
        else:
            self.ResetPosition()

    def Init(self, length, typeIndex):
        self.Text.text = '%snm' % fmt_g(length)
        self.Type = typeIndex
        self.TargetRect.anchoredPosition = V2(-400.0, -(40 + (typeIndex - 1) * 30))
        self.UpdateInitPosition()

    def DoBeginDrag(self, e, p):
        IPHODebug.Log('Start drag laser %s' % LASER_NAMES[self.Type])


@reg
class DiffractionLaserPosition(Component):
    def __init__(self, go, d):
        Component.__init__(self, go, d)
        self.m_CurLaser = None

    def Init(self, c):
        self.m_DController = c

    def OnTriggerEnter2D(self, other):
        if not self.m_CurLaser and other.go.tag == 'laser':
            self.m_CurLaser = other.go.get('DiffractionLaserItem')
            if self.m_CurLaser:
                self.m_CurLaser.LaserRect = self.Rect

    def OnTriggerExit2D(self, other):
        if other.go.tag == 'laser':
            comp = other.go.get('DiffractionLaserItem')
            if self.m_CurLaser and comp and self.m_CurLaser.Type == comp.Type:
                self.m_CurLaser.LaserRect = None
                self.m_DController.UpdateCurrentLaser(0)
                self.m_DController.UpdateCurrentExperimentIsOn(False)
                IPHODebug.Log('Uninstall the laser %s, so now experiment state is OFF' % LASER_NAMES[self.m_CurLaser.Type])
                self.m_CurLaser = None

    def DoChangeType(self):
        self.m_DController.UpdateCurrentLaser(self.m_CurLaser.Type)


@reg
class DiffractionTextureColorPicker(Component):
    def Init(self, c):
        c.OnExperimentIsOn.append(self.HandleExperimentIsOn)
        c.OnExperimentImgChange.append(self.HandleExperimentImgChange)

    def HandleExperimentImgChange(self):
        if self.HitUIObject:
            self.GetImageColorAndShow(self.NowPoint)

    def HandleExperimentIsOn(self, isOn):
        self.IsOn = isOn
        if not isOn:
            self.SpotRect.go.SetActive(False)
            self.PosXTxt.text = '--'
            self.PosYTxt.text = '--'
            self.VTxt.text = '--'
        else:
            self.NowFrame = self.MAX_FRAME

    def FixedUpdate(self):
        if not self.IsOn:
            return
        if Input.GetKey('Up'):
            self.UpdateNowPoint(V2(0, 1), 'up')
        if Input.GetKey('Down'):
            self.UpdateNowPoint(V2(0, -1), 'down')
        if Input.GetKey('Right'):
            self.UpdateNowPoint(V2(1, 0), 'right')
        if Input.GetKey('Left'):
            self.UpdateNowPoint(V2(-1, 0), 'left')
        if any(Input.GetKeyUp(k) for k in ('Up', 'Down', 'Right', 'Left')):
            self.NowFrame = self.MAX_FRAME

    def UpdateNowPoint(self, off, log):
        self.NowFrame += 1
        if self.NowFrame > self.MAX_FRAME:
            self.NowPoint = V2(self.NowPoint.x + off.x, self.NowPoint.y + off.y)
            IPHODebug.Log('Click ' + log + ' arrow')
            self.GetImageColorAndShow(self.NowPoint)
            self.NowFrame = 0

    def Update(self):
        if self.TargetImage.sprite and self.IsOn:
            self.GetPixelByMouseClick()

    def GetPixelByMouseClick(self):
        sel = U.es.currentSelectedGameObject
        if not Input.GetMouseButton(0) or not sel:
            return
        if not self.HitUIObject:
            self.HitUIObject = sel.rt
            if sel.tag != 'color_picker':
                self.HitUIObject = None
            else:
                sd, p = self.HitUIObject.sizeDelta, self.HitUIObject.position
                self.PointMax = V2(p.x + sd.x / 2, p.y + sd.y / 2)
                self.PointMin = V2(p.x - sd.x / 2, p.y - sd.y / 2)
                self.PointOffset = V2(self.PointMax.x - self.PointMin.x, self.PointMax.y - self.PointMin.y)
        if self.HitUIObject and sel.rt is self.HitUIObject:
            self.GetImageColorAndShow(Input.mousePosition())

    def GetImageColorAndShow(self, pos):
        IPHODebug.Log('Now result spot pos is (%s, %s)' % (fmt_fixed(pos.x, 1), fmt_fixed(pos.y, 1)))
        if self.TargetImage.sprite:
            self.ShowImageColor(self.GetImageColor(self.GetMousePos(pos)))

    def GetMousePos(self, pos):
        v = self.TransMousePosToImagePos(pos)
        return V2(math.floor(v.x), math.floor(v.y))

    def TransMousePosToImagePos(self, m):
        m = V2(clamp(m.x, self.PointMin.x, self.PointMax.x), clamp(m.y, self.PointMin.y, self.PointMax.y))
        self.NowPoint = m
        rx, ry, rw, rh = self.TargetRect.rect
        hp, tex = self.HitUIObject.position, self.TargetImage.sprite
        return V2((m.x - hp.x + rw * 0.5) * tex.w / rw, (m.y - hp.y + rh * 0.5) * tex.h / rh)

    def GetImageColor(self, p):
        return self.TargetImage.sprite.GetPixel(int(p.x), int(p.y))

    def ShowImageColor(self, c):
        num = (self.NowPoint.x - self.PointMin.x) / self.PointOffset.x * self.ScreenOffset.x + self.ScreenMin.x
        num2 = (self.NowPoint.y - self.PointMin.y) / self.PointOffset.y * self.ScreenOffset.y + self.ScreenMin.y
        self.PosXTxt.text = fmt_fixed(num, 2)
        self.PosYTxt.text = fmt_fixed(num2, 2)
        gray = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
        self.VTxt.text = fmt_fixed(gray * self.GrayRatio, 2)
        self.SpotRect.anchoredPosition = self.NowPoint
        if not self.SpotRect.go.activeInHierarchy:
            self.SpotRect.go.SetActive(True)


# ------------------------------------------------------------------- the app
class Sprite:
    def __init__(self, key, img, d):
        self.key = key
        self.img = img
        self.w, self.h = int(d['w']), int(d['h'])
        self.b = d['b']
        self.ppu = d['ppu']


def load_assets():
    U.data = json.loads(zlib.decompress(base64.b64decode(SCENE_Z)).decode('utf-8'))
    for key, d in U.data['sprites'].items():
        img = PILImage.open(io.BytesIO(base64.b64decode(SPRITES[key]))).convert('RGBA')
        U.sprites[key] = Sprite(key, img, d)
    for name, b64 in FONTS_B64.items():
        FONT_BYTES[name] = base64.b64decode(b64)


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('APHO')
        self.root.resizable(False, False)
        self.root.configure(bg='#323232')
        try:
            self.icon = ImageTk.PhotoImage(PILImage.open(io.BytesIO(base64.b64decode(ICON_PNG))))
            self.root.iconphoto(True, self.icon)
        except Exception:
            pass
        self.renderer = Renderer()
        self.photo = ImageTk.PhotoImage(self.renderer.frame)
        self.label = tk.Label(self.root, image=self.photo, bd=0, highlightthickness=0, cursor='arrow')
        self.label.pack()
        self.splash = PILImage.open(io.BytesIO(base64.b64decode(SPLASH_PNG))).convert('RGBA')
        self.splash_t = 0.0
        self.started = False
        self.last = time.perf_counter()
        lb = self.label
        lb.bind('<Motion>', self.on_move)
        lb.bind('<B1-Motion>', self.on_move)
        lb.bind('<ButtonPress-1>', self.on_down)
        lb.bind('<ButtonRelease-1>', self.on_up)
        self.root.bind('<KeyPress>', self.on_key)
        self.root.bind('<KeyRelease>', self.on_key_up)
        self.root.bind('<FocusOut>', self.on_blur)
        U.es = EventSystem()
        self.root.after(1, self.frame)

    def to_unity(self, e):
        return V2(float(e.x), float(SH - e.y))

    def on_move(self, e):
        U.input.mouse = self.to_unity(e)

    def on_down(self, e):
        U.input.mouse = self.to_unity(e)
        U.input.btn_held = True
        U.input.queue.append('down')
        self.label.focus_set()

    def on_up(self, e):
        U.input.mouse = self.to_unity(e)
        U.input.btn_held = False
        U.input.queue.append('up')

    ARROWS = ('Up', 'Down', 'Left', 'Right')

    def on_key(self, e):
        if e.keysym in self.ARROWS:
            if e.keysym not in U.input.keys:
                U.input.down.add(e.keysym)
            U.input.keys.add(e.keysym)
        sel = U.es.currentSelectedGameObject if U.es else None
        f = sel.get('InputField') if sel else None
        if f:
            if e.keysym == 'BackSpace':
                f.typed('\b')
            elif e.keysym in ('Return', 'KP_Enter'):
                f.typed('\n')
            elif e.char and len(e.char) == 1 and e.char >= ' ' and not (e.state & 0x4):
                f.typed(e.char)

    def on_key_up(self, e):
        if e.keysym in self.ARROWS:
            U.input.keys.discard(e.keysym)
            U.input.up.add(e.keysym)

    def on_blur(self, e):
        for k in list(U.input.keys):
            U.input.up.add(k)
        U.input.keys.clear()

    def draw_splash(self, t):
        """the Unity splash screen (light logo on #231F20, "Dolly"): the logo fades
        in, holds, fades out, the background stays a moment, then the first scene"""
        fr = self.renderer.frame
        fr.paste((35, 31, 32, 255), (0, 0, SW, SH))
        a = 0 if t < 0.3 else (t - 0.3) / 0.5 if t < 0.8 else 1 if t < 1.8 else (2.3 - t) / 0.5 if t < 2.3 else 0
        if a > 0:
            s = 0.1495 + 0.0075 * clamp01((t - 0.3) / 2.0)
            w, h = int(round(2048 * s)), int(round(1024 * s))
            logo = self.splash.resize((w, h), PILImage.LANCZOS)
            fr.alpha_composite(with_alpha(logo, a), ((SW - w) // 2, (SH - h) // 2))

    def frame(self):
        now = time.perf_counter()
        dt = min(now - self.last, MAX_DT)
        self.last = now
        dirty = True
        if not self.started:
            self.splash_t += dt
            self.draw_splash(self.splash_t)
            if self.splash_t >= 2.8:
                self.started = True
                load_scene('start')
        else:
            tick(dt)
            dirty = self.renderer.render()
        if dirty:
            self.photo.paste(self.renderer.frame)
        spent = (time.perf_counter() - now) * 1000
        self.root.after(max(1, int(16 - spent)), self.frame)

    def run(self):
        self.root.mainloop()


def main():
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    load_assets()
    App().run()


# ----------------------------------------------------------- embedded assets
# the scene data of the four scenes and two prefabs, the sprites, the fonts
# (Liberation Sans for Arial and the TMP font, CursedTimer for the meters,
# a DejaVu glyph for the degree Celsius sign), the Unity splash and the icon
FONT_BYTES = {}
ADV = {'tmp': {32: 0.27907, 33: 0.325581, 34: 0.360465, 35: 0.55814, 36: 0.55814, 37: 0.883721, 38: 0.662791, 39: 0.186047, 40: 0.337209, 41: 0.337209, 42: 0.383721, 43: 0.581395, 44: 0.27907, 45: 0.337209, 46: 0.27907, 47: 0.27907, 48: 0.55814, 49: 0.55814, 50: 0.55814, 51: 0.55814, 52: 0.55814, 53: 0.55814, 54: 0.55814, 55: 0.55814, 56: 0.55814, 57: 0.55814, 58: 0.27907, 59: 0.27907, 60: 0.581395, 61: 0.581395, 62: 0.581395, 63: 0.55814, 64: 1.011628, 65: 0.662791, 66: 0.662791, 67: 0.72093, 68: 0.72093, 69: 0.662791, 70: 0.616279, 71: 0.77907, 72: 0.72093, 73: 0.27907, 74: 0.5, 75: 0.662791, 76: 0.55814, 77: 0.825581, 78: 0.72093, 79: 0.77907, 80: 0.662791, 81: 0.77907, 82: 0.72093, 83: 0.662791, 84: 0.604651, 85: 0.72093, 86: 0.662791, 87: 0.988372, 88: 0.674419, 89: 0.651163, 90: 0.616279, 91: 0.27907, 92: 0.27907, 93: 0.27907, 94: 0.44186, 95: 0.55814, 96: 0.337209, 97: 0.55814, 98: 0.55814, 99: 0.5, 100: 0.55814, 101: 0.55814, 102: 0.290698, 103: 0.55814, 104: 0.55814, 105: 0.22093, 106: 0.232558, 107: 0.511628, 108: 0.22093, 109: 0.860465, 110: 0.55814, 111: 0.55814, 112: 0.55814, 113: 0.55814, 114: 0.337209, 115: 0.5, 116: 0.27907, 117: 0.55814, 118: 0.5, 119: 0.709302, 120: 0.5, 121: 0.476744, 122: 0.488372, 123: 0.337209, 124: 0.255814, 125: 0.337209, 126: 0.581395, 160: 0.27907, 161: 0.325581, 162: 0.55814, 163: 0.55814, 164: 0.55814, 165: 0.55814, 166: 0.255814, 167: 0.55814, 168: 0.337209, 169: 0.732558, 170: 0.372093, 171: 0.55814, 172: 0.581395, 173: 0.337209, 174: 0.732558, 175: 0.55814, 176: 0.395349, 177: 0.546512, 178: 0.337209, 179: 0.337209, 180: 0.337209, 181: 0.581395, 182: 0.534884, 183: 0.337209, 184: 0.337209, 185: 0.337209, 186: 0.360465, 187: 0.55814, 188: 0.837209, 189: 0.837209, 190: 0.837209, 191: 0.616279, 192: 0.662791, 193: 0.662791, 194: 0.662791, 195: 0.662791, 196: 0.662791, 197: 0.662791, 198: 1.0, 199: 0.72093, 200: 0.662791, 201: 0.662791, 202: 0.662791, 203: 0.662791, 204: 0.27907, 205: 0.27907, 206: 0.27907, 207: 0.27907, 208: 0.72093, 209: 0.72093, 210: 0.77907, 211: 0.77907, 212: 0.77907, 213: 0.77907, 214: 0.77907, 215: 0.581395, 216: 0.77907, 217: 0.72093, 218: 0.72093, 219: 0.72093, 220: 0.72093, 221: 0.651163, 222: 0.662791, 223: 0.616279, 224: 0.55814, 225: 0.55814, 226: 0.55814, 227: 0.55814, 228: 0.55814, 229: 0.55814, 230: 0.883721, 231: 0.5, 232: 0.55814, 233: 0.55814, 234: 0.55814, 235: 0.55814, 236: 0.27907, 237: 0.27907, 238: 0.27907, 239: 0.27907, 240: 0.55814, 241: 0.55814, 242: 0.55814, 243: 0.55814, 244: 0.55814, 245: 0.55814, 246: 0.55814, 247: 0.546512, 248: 0.616279, 249: 0.55814, 250: 0.55814, 251: 0.55814, 252: 0.55814, 253: 0.476744, 254: 0.55814, 255: 0.476744, 8192: 0.5, 8193: 1.0, 8194: 0.5, 8195: 1.0, 8196: 0.337209, 8197: 0.255814, 8198: 0.162791, 8199: 0.55814, 8200: 0.27907, 8201: 0.197674, 8202: 0.081395, 8203: 0.0, 8204: 0.0, 8205: 0.0, 8206: 0.0, 8207: 0.0, 8210: 0.55814, 8211: 0.55814, 8212: 1.0, 8213: 1.0, 8214: 0.418605, 8215: 0.55814, 8216: 0.22093, 8217: 0.22093, 8218: 0.22093, 8219: 0.22093, 8220: 0.337209, 8221: 0.337209, 8222: 0.337209, 8223: 0.337209, 8224: 0.55814, 8225: 0.55814, 8226: 0.348837, 8230: 1.0, 8234: 0.0, 8235: 0.0, 8236: 0.0, 8237: 0.0, 8238: 0.0, 8239: 0.197674, 8240: 1.0, 8242: 0.186047, 8243: 0.348837, 8244: 0.348837, 8249: 0.337209, 8250: 0.337209, 8252: 0.5, 8254: 0.337209, 8260: 0.162791, 8286: 0.27907, 8298: 0.0, 8299: 0.0, 8300: 0.0, 8301: 0.0, 8302: 0.0, 8303: 0.0, 8364: 0.55814, 8482: 1.0, 9633: 0.604651}, 'LibSans': {32: 0.277832, 33: 0.277832, 34: 0.35498, 35: 0.556152, 36: 0.556152, 37: 0.88916, 38: 0.666992, 39: 0.190918, 40: 0.333008, 41: 0.333008, 42: 0.38916, 43: 0.583984, 44: 0.277832, 45: 0.333008, 46: 0.277832, 47: 0.277832, 48: 0.556152, 49: 0.556152, 50: 0.556152, 51: 0.556152, 52: 0.556152, 53: 0.556152, 54: 0.556152, 55: 0.556152, 56: 0.556152, 57: 0.556152, 58: 0.277832, 59: 0.277832, 60: 0.583984, 61: 0.583984, 62: 0.583984, 63: 0.556152, 64: 1.015137, 65: 0.666992, 66: 0.666992, 67: 0.722168, 68: 0.722168, 69: 0.666992, 70: 0.61084, 71: 0.777832, 72: 0.722168, 73: 0.277832, 74: 0.5, 75: 0.666992, 76: 0.556152, 77: 0.833008, 78: 0.722168, 79: 0.777832, 80: 0.666992, 81: 0.777832, 82: 0.722168, 83: 0.666992, 84: 0.61084, 85: 0.722168, 86: 0.666992, 87: 0.943848, 88: 0.666992, 89: 0.666992, 90: 0.61084, 91: 0.277832, 92: 0.277832, 93: 0.277832, 94: 0.469238, 95: 0.556152, 96: 0.333008, 97: 0.556152, 98: 0.556152, 99: 0.5, 100: 0.556152, 101: 0.556152, 102: 0.277832, 103: 0.556152, 104: 0.556152, 105: 0.222168, 106: 0.222168, 107: 0.5, 108: 0.222168, 109: 0.833008, 110: 0.556152, 111: 0.556152, 112: 0.556152, 113: 0.556152, 114: 0.333008, 115: 0.5, 116: 0.277832, 117: 0.556152, 118: 0.5, 119: 0.722168, 120: 0.5, 121: 0.5, 122: 0.5, 123: 0.333984, 124: 0.259766, 125: 0.333984, 126: 0.583984, 176: 0.399902, 181: 0.576172, 215: 0.583984}, 'LibSansI': {32: 0.277832, 33: 0.277832, 34: 0.35498, 35: 0.556152, 36: 0.556152, 37: 0.88916, 38: 0.666992, 39: 0.190918, 40: 0.333008, 41: 0.333008, 42: 0.38916, 43: 0.583984, 44: 0.277832, 45: 0.333008, 46: 0.277832, 47: 0.277832, 48: 0.556152, 49: 0.556152, 50: 0.556152, 51: 0.556152, 52: 0.556152, 53: 0.556152, 54: 0.556152, 55: 0.556152, 56: 0.556152, 57: 0.556152, 58: 0.277832, 59: 0.277832, 60: 0.583984, 61: 0.583984, 62: 0.583984, 63: 0.556152, 64: 1.015137, 65: 0.666992, 66: 0.666992, 67: 0.722168, 68: 0.722168, 69: 0.666992, 70: 0.61084, 71: 0.777832, 72: 0.722168, 73: 0.277832, 74: 0.5, 75: 0.666992, 76: 0.556152, 77: 0.833008, 78: 0.722168, 79: 0.777832, 80: 0.666992, 81: 0.777832, 82: 0.722168, 83: 0.666992, 84: 0.61084, 85: 0.722168, 86: 0.666992, 87: 0.943848, 88: 0.666992, 89: 0.666992, 90: 0.61084, 91: 0.277832, 92: 0.277832, 93: 0.277832, 94: 0.469238, 95: 0.556152, 96: 0.333008, 97: 0.556152, 98: 0.556152, 99: 0.5, 100: 0.556152, 101: 0.556152, 102: 0.277832, 103: 0.556152, 104: 0.556152, 105: 0.222168, 106: 0.222168, 107: 0.5, 108: 0.222168, 109: 0.833008, 110: 0.556152, 111: 0.556152, 112: 0.556152, 113: 0.556152, 114: 0.333008, 115: 0.5, 116: 0.277832, 117: 0.556152, 118: 0.5, 119: 0.722168, 120: 0.5, 121: 0.5, 122: 0.5, 123: 0.333984, 124: 0.259766, 125: 0.333984, 126: 0.583984, 176: 0.399902, 181: 0.576172, 215: 0.583984}, 'LibSansB': {32: 0.277832, 33: 0.333008, 34: 0.474121, 35: 0.556152, 36: 0.556152, 37: 0.88916, 38: 0.722168, 39: 0.237793, 40: 0.333008, 41: 0.333008, 42: 0.38916, 43: 0.583984, 44: 0.277832, 45: 0.333008, 46: 0.277832, 47: 0.277832, 48: 0.556152, 49: 0.556152, 50: 0.556152, 51: 0.556152, 52: 0.556152, 53: 0.556152, 54: 0.556152, 55: 0.556152, 56: 0.556152, 57: 0.556152, 58: 0.333008, 59: 0.333008, 60: 0.583984, 61: 0.583984, 62: 0.583984, 63: 0.61084, 64: 0.975098, 65: 0.722168, 66: 0.722168, 67: 0.722168, 68: 0.722168, 69: 0.666992, 70: 0.61084, 71: 0.777832, 72: 0.722168, 73: 0.277832, 74: 0.556152, 75: 0.722168, 76: 0.61084, 77: 0.833008, 78: 0.722168, 79: 0.777832, 80: 0.666992, 81: 0.777832, 82: 0.722168, 83: 0.666992, 84: 0.61084, 85: 0.722168, 86: 0.666992, 87: 0.943848, 88: 0.666992, 89: 0.666992, 90: 0.61084, 91: 0.333008, 92: 0.277832, 93: 0.333008, 94: 0.583984, 95: 0.556152, 96: 0.333008, 97: 0.556152, 98: 0.61084, 99: 0.556152, 100: 0.61084, 101: 0.556152, 102: 0.333008, 103: 0.61084, 104: 0.61084, 105: 0.277832, 106: 0.277832, 107: 0.556152, 108: 0.277832, 109: 0.88916, 110: 0.61084, 111: 0.61084, 112: 0.61084, 113: 0.61084, 114: 0.38916, 115: 0.556152, 116: 0.333008, 117: 0.61084, 118: 0.556152, 119: 0.777832, 120: 0.556152, 121: 0.556152, 122: 0.5, 123: 0.38916, 124: 0.279785, 125: 0.38916, 126: 0.583984, 176: 0.399902, 181: 0.576172, 215: 0.583984}, 'Cursed': {32: 0.625, 33: 0.625, 34: 0.625, 35: 0.625, 36: 0.625, 37: 0.625, 38: 0.625, 39: 0.625, 40: 0.625, 41: 0.625, 42: 0.625, 43: 0.625, 44: 0.625, 45: 0.625, 46: 0.625, 47: 0.625, 48: 0.625, 49: 0.625, 50: 0.625, 51: 0.625, 52: 0.625, 53: 0.625, 54: 0.625, 55: 0.625, 56: 0.625, 57: 0.625, 58: 0.625, 59: 0.625, 60: 0.625, 61: 0.625, 62: 0.625, 63: 0.625, 64: 0.625, 65: 0.625, 66: 0.625, 67: 0.625, 68: 0.625, 69: 0.625, 70: 0.625, 71: 0.625, 72: 0.625, 73: 0.625, 74: 0.625, 75: 0.625, 76: 0.625, 77: 0.625, 78: 0.625, 79: 0.625, 80: 0.625, 81: 0.625, 82: 0.625, 83: 0.625, 84: 0.625, 85: 0.625, 86: 0.625, 87: 0.625, 88: 0.625, 89: 0.625, 90: 0.625, 91: 0.625, 92: 0.625, 93: 0.625, 94: 0.625, 95: 0.625, 96: 0.625, 97: 0.625, 98: 0.625, 99: 0.625, 100: 0.625, 101: 0.625, 102: 0.625, 103: 0.625, 104: 0.625, 105: 0.625, 106: 0.625, 107: 0.625, 108: 0.625, 109: 0.625, 110: 0.625, 111: 0.625, 112: 0.625, 113: 0.625, 114: 0.625, 115: 0.625, 116: 0.625, 117: 0.625, 118: 0.625, 119: 0.625, 120: 0.625, 121: 0.625, 122: 0.625, 123: 0.625, 124: 0.625, 125: 0.625, 126: 0.625, 161: 0.625, 169: 0.625, 171: 0.625, 174: 0.625, 176: 0.540039, 180: 0.625, 187: 0.625, 191: 0.625, 199: 0.625, 215: 0.625, 231: 0.625, 247: 0.625, 710: 0.625, 8211: 0.625, 8212: 0.625, 8216: 0.625, 8217: 0.625, 8220: 0.625, 8221: 0.625, 8226: 0.625, 8230: 0.625, 8249: 0.625, 8250: 0.625, 8364: 0.625, 8482: 0.625}, 'Sym': {8451: 1.123047}}
SCENE_Z = (
    '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'
    'TDr5/wcoGnQa')
SPRITES = {
    'sharedassets0.assets:12': (
        'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAACaUlEQVR4nO2XMUgbURjHf++7xJwudXCrDh0kILS0ZjKb'
        'nbLVQRDETegmhVM3R0cNBQOBzoIIDnYThA7ZgtUWhEJwUxf3Yu4ud+91aC6cZyy9kOCSPxy8u/fe9/+9e3cf31MAMzMz'
        'RLJtG2MMlmWhtQbAGINSijSKzxERwjBEKYXrug/GSaqoA5DEV59QHtgFvgMBYFJeQXvubjtWV6kkQHsLHGDbcZzRQqFA'
        'Pp9HJN3L0lrTaDQ4Pz+nXC43gS2lVDm5BUmAEdu2vy4uLpZWVlaYmppKZfqUbm5u2N/f5+jo6MR13Q+A3wEoFApx6s/L'
        'y8ufNjY2+mKc1M7ODgcHB2Wt9Xo3gNda6x/1et3KZrNorQmCAK11529IKxFBRMhkMogInucxNzcXGmPeAL8AJDLQWq9u'
        'bm5a2WyWIAhwXbcD0KuiRUSxcrkcjuNYIrIawcW/rFKxWMTzPHzffzJor/J9H8/zKBaLAKXoeSaWYF5NTEwQhmHfzSOF'
        'Ycj4+DjGmJcdgFj/SNps14ts20Yp9SK6f/5MOAQYAgwBhgBDgFjbb7VaAzdsNpsAv7sBXN/d3Q0coO1x3Q3gpF6vDxzg'
        '7OwMY8ypMebv2SFZktVqNSttBfy/arVazM/PhyLyDrgEkIjEGHOplKpWKpWBmANUq1WAitb6MioFu5blCwsLpaWlJSYn'
        'J/tifHt7y+HhIcfHx4/L8uTBJJfLATjA9tra2ujs7CzT09M9GV9dXXFxccHe3l4T2ALKnuc9GPMIYGxsLGrmtdYfgffA'
        '254I4CfwTUS+AA2A+/v7BwMyj+d01ADW/9HfFz17JvwDX4kcruyE/QQAAAAASUVORK5CYII='),
    'sharedassets0.assets:13': (
        'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAACsUlEQVR4nO2XzUsbQRiHn5ndzX4ECV4NEnoKCC0tIpij'
        'PUg89eLBQ5CA2D8gXj0KhYJ7kEKhV0U8eOlJsVCvooEWhEKOKoIehWI2MTvTSzbNV4WELPbgDxaG5X3n98zMzs47AmBq'
        'aopIjuOgtcYwDJRSAGitEUIwiNpzpJSEYYgQgiAIOuLkQL3GINk++i5lgU2gDDQAPeDTaOZuNvvqK9EN0FyCErCxtLTk'
        'ZrNZMpkMhmEMNLIwDLm4uKBSqbC3t1cF1oUQfvcSdAMkHMf5Ojc3l19YWCCdTmMYBlLKob4BpRRhGHJ9fc3BwQHHx8eH'
        'QRC8A+pRnOm6bitJKfVxfn4+XywWsW2bRCKBaZotiEEUmTcaDRzHYXV1Fcuy8kdHRx+UUmutGZieno7aL5VSP3Z3d42x'
        'sTEcx8G27ZHMQK1WIwgC7u7uKBQKodb6FfALwIy2GrBSLBaNVCqF53k4jtNhPgxABGFZFqZpIqVkeXnZ2N7eXgHWoHMb'
        '5nO5HMlkEtd1O5IGNQcQQiClxDRNLMvCdV2SySS5XA4gH8WZbZ2/yGQy2LbdMh6VIhDbtpmYmEBrnW4BtMUlPM8buXk3'
        'xPj4OEKIVOt9e1Bc5u0Q3f+TDrdh1noYiEcB4oTo1//TH0bPAM8AzwD/E0D94eEhdsNqtQrwux/A5e3tbewANzc3AJf9'
        'AA5PTk5iBzg9PUVr/S0qWHpKsnK5bMR1ItbrdWZnZ0Mp5RvgHEBGJFrrcyHEZ9/3YzEH2NraAviklDpXSqGU6l+WLy4u'
        '5guFApOTkyMxvrq6Ymdnh/39/Z6yvOdiYts2QAnYKJVK7szMDNnsPy82j6pSqXB2dobv+1VgHfBrtVpHTA+A53lRM6uU'
        'eg+8BV4PRQA/ge9Syi9ABeD+/r4jwOzN+TsAmqVznHryP+Ef3cEOoF/irmAAAAAASUVORK5CYII='),
    'sharedassets1.assets:14': (
        'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAACHklEQVR4nO2XP4saQRjGfzOKGptgIRYpJBA4ESKB+wbB'
        'QquUIqjNQarAQYRUKdOepAgEDgLiH6xTeRLJJ0gRPBGv9DoLu2D02J03za6se+bA45ZrfGBgZufP89t3YHhfBZDNZnEV'
        'i8UQEUKhEMYYAEQEpRT7yLtHa41t2yilWK1WW+v0XqcGIO39e5+OgDPgF2ABsmeznL1nzlk7pfwAzhW8Bz5VKpUnmUyG'
        'dDqN1vsFyxjDbDZjOp3S6XT+Ah+VUg3/FfgBIrFY7Hs+ny8Ui0VSqdRepv/TfD6n3+8zHA4vVqvVG+BmA3B8fOyl/lwo'
        'FE6r1eqDGPvVbrcZDAYNY0zd/eaN60vgXblcDsQcoFQqISKnwCbs2hiD005qtVooHA4HBhCJRKhUKiGt9YnWGq31VgQK'
        'uVwuMHNXjkfBHYc9D8zzZDIZOEAikUBEnm0APHORIMPvKh6Po5R66o4f/yU8ABwADgAHgAOAp39jWVbghk5K9mcXwPVi'
        'sQgcwPG43gVwMRqNAgcYj8eIyA8RQUTQSimcdt5sNm23GAlClmXRarVsrfW3TUbkkojIpVLqa7fbDQyg1+sBfDHGXLqp'
        'YNiXp9cHg8EL27YDS8vX6/UH79ytwiQajQJsCpNsNks6nb6X8Ww2YzKZbAoToLFer7fW3AKIx+Nu98gY8xZ4Dby6FwH8'
        'Bn5qrc+BK4Dlcrm14K4k8Aqo3zH/IHr0l/AfylbkNQg/jrMAAAAASUVORK5CYII='),
    'sharedassets1.assets:15': (
        'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAL0lEQVR4nO3OMQEAAAjDsIF/z0MGT2qgmbbNY/s5BwAA'
        'AAAAAAAAAAAAAAAASJIDTYgEPEq9nRUAAAAASUVORK5CYII='),
    'sharedassets1.assets:16': (
        'iVBORw0KGgoAAAANSUhEUgAAAB4AAAAeCAYAAAA7MK6iAAAAgElEQVR4nO3XsQ2DQBAF0YHKzp3QCbgSy5UcJbgT6GAI'
        'zEkOnN5tsl/adF88qNxX1Koe9llVl+Y1dO2E/duqMqkL8GLsHpNagTIY3ifVwSjAGQUzR6AJJ5xwwgknnHDCcfAZBX8C'
        '3H0GngHwuyXMNjBhNn/aCb9BVTthx/27NO8C5GbiFaK7Ye0AAAAASUVORK5CYII='),
    'sharedassets1.assets:17': (
        'iVBORw0KGgoAAAANSUhEUgAAACkAAAAmCAYAAABZNrIjAAABeElEQVR4nM3X623CMBRA4eOIATyCu0m6ARu0naBsABt0'
        'BLpBR+gK3aBscvvDpIoi27p2/OBIlpCA8EFuwBgqJiLZT9E8aMqnRF4tH6iuCrIlECogWwNhJ7IHEHYgewGh4oXTsiJk'
        'z08RCpC9gZCJHAGEDOQoICiRI4GgQGYCZ+Cn0BLtkLozA+iAKx5ZvShSCbTAO3C6325SEKkEvgIfNMQtlXyZz8A3/vTa'
        'mhh1IhJbTkQ+RVfqOOul6rAFBrJ0mLtU/8gI8IifO9eHE26CIHDGz90XZUBRLlVmA7TAGX9qH6b1TC44O0SS6IA/tVcG'
        'z12qiQfGLa1n8oT/qnGjMLG2F44DLsDLCEysLXLJ0XBXk1vst/sGPANv99tDi32S2y74ebUtMbG0SMibV1PoCR+s4P+L'
        'w/9kutRxCz3BSvaTN+CJDvNqjMEYk9w/apYVkcuO/WRwJdtx4O2GuD6uIvgoIr+1caoBL3qXiozRXV/ZV2ENsBa39Afw'
        'AhzyZMUiUwAAAABJRU5ErkJggg=='),
    'sharedassets1.assets:18': (
        'iVBORw0KGgoAAAANSUhEUgAAADoAAAAyCAYAAAAN6MhFAAACrUlEQVR4nN2a3XWjMBCFP7kCSsAd7HbglLAdZEtICe5g'
        'U0FIBbsd2B04Haw6CB1MHgSOjCUhQDI/9xwebGGY6zvMHQYQEZrtICIn2Q4uIvIsDT8lIgDPwBvbxAvwpyX6HyhnDScf'
        'amC/Aw5slyRAAZQ7DOOto1AiUmBSt5g3lmzQNKlbA8dZQ8mLI3CtugAX4Mdc0WSCBvYAO+vLl1lCyYsrJ5voudm2ggr4'
        '136wUxeMzVzYRmHaY1IXuFWUZuH1gcHkwhGLJNwrCkbNNduNBp7oEO0qCuu3mzs1wa1oixOmPVwTNI2ddLFTSvl+tEZV'
        'f/kWXKnb4gy8Jw8lHyrgw7WglOIqpyeFS9ZjNzd2YkMpFVQU1mM3zgIEhiTAzQXqUbXAqFomDCwlNJ4CBN9E+xQFYzdL'
        '7oO9RdMutHcld2V28wH89C2OJXrAkF0SggXIxl3qBnz1zLIKU4WHpAtOVgFVC5bRB2sc/ayNXkVdO1moWYaq7wwgCR5F'
        'IagqzDsH1gTsBNxEvfYSUBXgd2RQORDswX1xx/ioC2fmGbtUzTYYQdkgmMIlJoUfCa+dQDgLxyoKj++DKwbYSRe9isIi'
        '7EYz0E66mKIoPG7s4r07icVURVvknPJreuwEEinadxDy3t30HjsivnjI9ysAvu2U4fH8W8R5o+If9Ff0HLQk/dglaCcQ'
        'r+bUYmRDk9ZuJhcgG4OTu0fVgjR2ozE31HVopyHXZkpFId3Y5UjiVw5GlauIAjBl7KKJsBOYV9EWU5qIp5idhlrKKKIR'
        'JzkzbspfkbAA2RjttBHpWzLMbmpMAdJ9O45pEEanbsTJNMPs5pVMasIERSFK1YK4Kb8mQwGyMakYRZy0Js5ulv+IMqYX'
        '7emDT5HHmJtqFNlSRD4dJD+btc0Qbcn+tQieQiRT4wvheftTbFYnPgAAAABJRU5ErkJggg=='),
    'sharedassets1.assets:19': (
        'iVBORw0KGgoAAAANSUhEUgAAAB0AAAAbCAYAAACAyoQSAAAA5klEQVR4nO2UWxGDMBBFL1WABCRQB5FQCXXQOkACFuoA'
        'CZFQCeAAHNx+ADOQyWtD6BdnJj9kyZndnbkgicTTkSxT/k0VNpxp/yVV3KPOllYke0PaS8cslX5oRzRmifDpEK48cktt'
        'YzUZl7psUh0Qruhc0lekcOUderMgCQ8VgN5XYGECcAcwuApugQe0UAgAJYDOV+CTNpg7TaEG0DpvHXOvhXt0oWJ3WgL4'
        'Huhyy4B5v9P2o228R8ZqUi3v7TFaD6VOKru0kqZOKiM3aRUT5rnQjAwHAAgWWCh8l6FwOIVLekkvqYgfG00Jne7qAQkA'
        'AAAASUVORK5CYII='),
    'sharedassets1.assets:20': (
        'iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAACZUlEQVR4nN2a4XXaMBSFP3kCuoGYoGSCwiZsUDagmQAy'
        'QekEaSeATBAyAd4Ab3DzQ1axHWMwAmPxnaMD2HC410+ypadnaEBS0+kqFhgD3/PXQaF50rxtgQ9gk39uxBjTRsdXJJ1q'
        'A0lzSTtdzk7SQpI99X+3MDGWtA4Qf4zfpwxdy4SV9HoDA60MhZr4KWnfgQnPTtK0Qc9FRhYdGqiyqNHzxYypmqgwANbA'
        '6Lx43owtMAGyY19I/JsemwCnYU35Vl7CwNHnxTv9MFFkCzzVnUjqDgIL+mcCnKZF7ZmaATTtfjy3ZqaKbqNyt7K4vmhv'
        'fGVDyXBdLPUHql1rTv9NgBv0pS5WjIgFdt3qCWaCm3iWIjK/i5Qw/mv2EbHEFw3PNyDzEZndUUgoMzhEZEccg7yOFBga'
        'SZZ4u5XHJrhlaexMEvo5FWnLKMElC2LnR0K8g7zIwEin1oxRkD2KkaPrkehIaFgHx8SjGEkfysjbvVVcgY8El5mIne2j'
        'TBqHCYc9i1hJyccIwJ87CgnlHxwWVgNgf081AQwpRCQjz0ZExop8WBTTQWNcci4mhuRGinOtDfC3ey0Xs6Jwk6pLmb7T'
        'kL7vCSkuOZf6A9XZbwo8dybncp6pPjKqWe28LTvMrLdlqRrN1a5VJJqNHmMMSUNVwYR+zcO2OE0lvP6oN0OLQUiOncjJ'
        'cKF8ub62s3nJNWQX/bpmQE0VVnPSlr1qtth8CzVjJa06MPGq0BKOM8zc0tBarmDnuhVCZxpaKrzM6ZdcyVRTLUyjkVYV'
        'XSeuiMVNPEe4fLKlnI7NCu0Ndyfa0GJR11SA9gmT3Os9LGL2PgAAAABJRU5ErkJggg=='),
    'sharedassets1.assets:21': (
        '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'),
    'sharedassets1.assets:22': (
        'iVBORw0KGgoAAAANSUhEUgAAAFUAAAAaCAYAAADG+xDjAAADNElEQVR4nO3Zv6sdRRQH8M/eu0+jGAvttIjYaGFpbRrB'
        'Ltrb+Qfkn7CwtVHjjwhKwKjEHwRjgmBnQPwVRH1FQgIaCxHEGH8Qfe+Nxcx45y677/7aG+P6vjDMcubMzM7Zme+cc7YK'
        'IRggxtjGoziEp3AhtVVF+1oWP1rHoDcQLuMJbOJ1HBQNuZXqDWuwQTXQnVqJRrsTX+Kuou0jPIMT+DPJ6qS/3cvkAzVq'
        'iU/wIK6Z3pnn8RJewQ9JNhY/yErUUIUQxst2Tujzq/Q51kg0zjE8Lh752sRgddL7Kem8iK+SbCXezROvUnZ6LKHHUqU1'
        'ftNY89jEuH/hDhzGObyFh03zbm1B3q1CCA+l53JhbYvsWvSi8rZiiT6zyljkzEN4Nxmx7VRmLq0L2cd4Dm/i9ySbm3er'
        'EMI13NTR3rbw8nk32Tx1c47SsDsdsmZ7V5132624v9MC0++xLe7KvDMv4ajIu5eTLLdvdQ1UhRCu4Pb0MlWzfY6XGSKa'
        'vHtFdMmex+eFXsnR/6AKIfyC/aZ5aBb+LZdh0Xnzmpb1RfPJKKnhlEgN7xXvUxe6qhDCVdxmMaP+35CpIbtc8AVewHH8'
        'nGQ1wp5RF0Mb734vcu5RXGRvp66CJu/+gQ/w9NBj/3WiuQE3cAs26hblPXQju2xEfh3hR5OIbJPpW20P3SgvqhxAbIqG'
        'PCYaVm7LUUJzgHXjerlkfbpUeQN+iCN4RwxzaURb2b/KA2Se6Lqw+rrIbvQLsbyERmKoekI05tlCLzv/U9FVFULILsIi'
        'mBW+7haedoWqu+l3ha6zQtUt7MO9c65ryyRDRXSXXhVThBeTLLtTnRmsKoTwSBqomS1qe25bXN/JleYHW7bvGL/iMbxt'
        'dkKldOzPiSHpa2KIqug7M6FS48wspf8o8um7L9XNXdXGl++LIejJQi9T5Nx/BWrtX29VXM/cQNdcI9EYDzTkTb68ijdE'
        'Y35W6LXy5TzIHYeG/EuEyU7dNs2X3+LlVL5LsjKtt7AxM4bspwYxq59/+t2c6k/FW/w4fkuy0iXasSKGatR8Ox/A3Ul2'
        'Es/idKG3YckjvhuGatSMe8Tk8pP4upCX/6h6x9/rw8n2p2JykAAAAABJRU5ErkJggg=='),
    'sharedassets2.assets:7': (
        'iVBORw0KGgoAAAANSUhEUgAAAB4AAAAeCAYAAAA7MK6iAAAAnklEQVR4nO3XMRHDMAyF4ZciMJRCCARDMJOEmQuhDAIh'
        'ZfB3qNRz91pZpDstGvxZ9iIJkOUKdOBkTnSguefoBhyGl+Ey/8xqxuZws8IscMziDcqeoAagP1+6AEhaFBdF0nEFLEnc'
        'gsFvJJxwwgknnHDCCV8Dv/QZwMLhp6R7oFklPXzOjR7omxd2K8wa7MvQ4M6wO/kq05kTp529uvcGiSG+gS8gQ3wAAAAA'
        'SUVORK5CYII='),
    'sharedassets2.assets:8': (
        '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'
        'Po88t/f/WAmDPvcWJEMAAAAASUVORK5CYII='),
    'sharedassets2.assets:9': (
        'iVBORw0KGgoAAAANSUhEUgAAACoAAAAqCAYAAADFw8lbAAACU0lEQVR4nNWZ8XHrIAyHP3uSt0HVDdINmg0ySkfpBs0G'
        '7QZVJ3hvg46g/lGwCQECGOfu/e64JLYjfZZsIezJzBgscZ/qN0zTtN2qmY0cYmbfbki4r5Up1jQwogK8sUZSgKP/fSuq'
        'MUd8/DwkLSvkEfhy4+i2SQokzsYt8HkEJVH0nNRtk9h5TxZzoJYYzwU7rxGkl7p9q+FLyEPGVzUowD/gEZjcOBeO7dVH'
        'YP/R+UyqBHpxje0sYb3GF4XRL4Eq94EVVkjNHTRDsXQo+8IKFZCQj+hT8F3ZB1ZIQ2bTv2yomHX+xjNOYry4McLWArpE'
        'tKLwK2MiK1SmO9RF6u8AK3RAQgRaOWMofbBCJ6SZraCN05rSBit0QnrN0Df3Ug8rbIQEmCNIAU4N/1fKsEIf5Cm2F16j'
        '3miLQcjDens9kdQrez117UZtfHNjlD0xMyYzE+Cd307mq/HMYz2wtoPnQfYOwNOoxnl//S+p755/C0b9XD/K3mXBJ7HG'
        'qZSQvru9vZ7pVq7sbUhNLgs+osMuK9i2ChXq6qSyoZHxjVIvqNBWzJUO2LCb6wEV+mYcpQH26klJgyPY3mAoFbCpvrgF'
        'VBjQBVEB62+gUDnQ5+i3MAbSS8nDHqB+UWcbyktcnlrL2+I71K3UC2MjGUupvMFKoMK+kF5KBWwJ9B6QXsoKuyhMfwn0'
        'D/DJ+ijwMBgOfm9ab//T+UwqBzolxkfB4Yn8mulU+N8546satFVKfs2kIxzc7WVDNVDuac3GNi9VF78t8fqm1MJVncDA'
        'iHqJ+9Skw863MD9/KYYgZmKycgAAAABJRU5ErkJggg=='),
}
FONTS_B64 = {
    'LibSans': (
        'AAEAAAARAQAABAAQR0RFRgAQAGMAAF+gAAAAFkdQT1OiNLuJAABfuAAAAh5HU1VCpiGpEQAAYdgAAAAsT1MvMnrJXHsA'
        'AE+kAAAAYGNtYXACsQGzAABQBAAAAExjdnQgStpL+gAAW0gAAAKIZnBnbX5hthEAAFBQAAAHtGdhc3AAGAAJAABfkAAA'
        'ABBnbHlmZ/vrNQAAARwAAEu2aGVhZABohPUAAE28AAAANmhoZWENlAPgAABPgAAAACRobXR4ovok2wAATfQAAAGMbG9j'
        'YUDDVRcAAEz0AAAAyG1heHAD0gPkAABM1AAAACBuYW1lIRI6CgAAXdAAAAGgcG9zdP8qAJYAAF9wAAAAIHByZXD9rkdJ'
        'AABYBAAAA0MAAgC5AAABfwWBAAMABwHkQP8DBwcCBAQJCCABAQ8BAQ4DAQVABAWcWwQCA5IJAYQJAXIJAWIJAVQJAUQJ'
        'ATIJASIJARQJAQQJAfIJAeIJAdQJAcQJAbIJAaQJAZQJAYQJAXIJAWQJAVQJAUQJATQJASQJARQJAQQJAWf0CQG5CQGp'
        'CQGZCQGJCQF5CQFJCQE9CQEtCQEfCQEPCQH/CQHvCQHbCQHLCQG7CQGrCQGdCQGNCQF9CQFvCQFfCQFLCQE7CQErCQEb'
        'CQELCQH9CQHtCQHdCQHNCQG7CQGrCQGbCQGLCQF9CQFrCQFbCQFNCQE9CQEpCQEZCQELCQE3+wkB6wkB3QkBzQkBuwkB'
        'qwkBmQlAWwGJCQF5CQFpCQFbCQFLCQE7CQEtCQEdCQEB6wkB2wkBywkBvwkBrwkBnwkBewkBawkBOwkBKwkBGwkBDwkB'
        'As8JAb8JAZ8JAY8JAX8JAWAJAUAJAR8JAQ8JAQdeXV1dXV1dXV1dX3FxcXFxcXFxcXFxcV9ycnJycnJycnJycnJycnJe'
        'XV1dXV1dXV1dXV1dXV1dXXFxcXFxcXFxcXFxcXFxcXFycnJycnJycnJycl5dXV1dXV1dXV1dXV1dXV1dcXFxcXFxcXFx'
        'cQA/LysAGhgQzl9eXV0REgE5ETMzETMxMAEjAzMDNTMVAWeUGMTGwgGNA/T6f8nJAAACAFcDxgKABYEAAwAHACNAEAMC'
        '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'
        '/qD+GnJ9sAFLAAABAKgAAAUgBYEACwByQBcHAwMECAAACwQLDA0HAl9ZUAcB4AcBB7j/4UAuE0l5B4kHAg8HAQgHBwkF'
        'AwQAEiANAcANAbANAaANAYANAXANAWANAVANASANAV1dXV1dXV1dcQA/Mj8zOS9eXV0rXXErERIBOTkRMxEzETMRMzEw'
        'IREhESMRMxEhETMRBGH9Br+/Avq/Ao39cwWB/awCVPp/AAABAL0AAAF8BYEAAwCMQGEDAAAEBQEDABJABQEwBQEgBQEQ'
        'BQEABQE58AUBsAUBoAUBcAUBYAUBUAUBQAUBAAUB8AUBwAUBsAUBoAUBUAUBQAUBEAUBAAUB8AUBrwUBkAUBcAUBYAUB'
        'UAUBQAUBIAUBXV1dXV1dXV1xcXFxcXFxcXJycnJycnJyXl1dXV1dAD8/ERIBOREzMTAzETMRvb8Fgfp/AAEAIP/sA2gF'
        'gQAQAEZAKgMCCQ4OCwIDERIMC19ZDAMABl9ZQAMBAwMAEyASAWASAVASAUASASASAV1dXV1xAD8yL10rABg/KxESARc5'
        'ETMRMzEwBSADNx4BMzI2NREhNSERFAYByf6aQ7sSfl9oeP7xAc3eFAFyH3SCj4oDRZz8I83rAAEAqAAABT8FgQALADRA'
        'GwALCAkHAwMECwkKBAQMDQoHAQIEBAgFAwAEEgA/Mz8zEhc5ERIBFzkRMxEzETMRMzEwIQEHESMRMxEBMwkBBFL9zbi/'
        'vwKn4f2oAqgCqIz95AWB/T4Cwv2c/OMAAAEAqAAABC8FgQAFAB9ADgMAAAQGBwEDAANfWQASAD8rABg/ERIBOTkRMzEw'
        'MxEzESEVqL8CyAWB+xucAAEAqAAABgIFgQAaAVJA7xgAGhANDhoOHBsDChgKDwMABxQDDhKQHAGEHAFwHAFkHAFEHAE0'
        'HAEgHAEUHAH0HAHQHAHEHAGkHAGEHAF0HAFgHAFUHAE0HAEQHAEEHAFn5BwBxBwBtBwBlBwBdBwBUBwBRBwBJBwBBBwB'
        '9BwB1BwBtBwBhBwBZBwBRBwBNBwBFBwB9BwBxBwBpBwBixwBdBwBVBwBNBwBBBwBN+QcAcscAbQcAZQcAXQcAUQcASQc'
        'AQscAfQcAdQcAbscAYQcAWQcAUscATQcARQcAfscAeQcAcQcAaQcAYAcAQJwHAFQHAFAHAE/HAEgHAEAHAEHXl1dXV1d'
        'XV9dXV1dXXFxcXFxcXFxcnJycnJycnJeXV1dXV1dXV1xcXFxcXFxcXJycnJycnJycl5dXV1dXV1dXV1dXXFxcXFxcXFx'
        'AD8XMz8zMxEzERIBOTkRMzMRMzMxMCERNDcGBwEjAS8BHwERIxEzAR4BFz4BNwEzEQVWCTEn/pSG/o84IQMEqvsBdxQl'
        'BggzCQFw9QOsnJCzZfxAA8Cqbm+9/FQFgfwvO4ceKKMVA9H6fwABAKgAAAUgBYEADQBQQC8ACgoNBwQEBQ0FDw4LAQYD'
        'CAAFEiAPAcAPAbAPAaAPAYAPAXAPAWAPAVAPASAPAV1dXV1dXV1dcQA/MzM/MzMREgE5OREzETMRMxEzMTAhAR8BESMR'
        'MwEmNREzEQQ6/Q4FBareAvoMrASwYaf8WAWB+0jEWAOc+n8AAgBh/+wF1wWWAA4AGgAwQBoVCA8ACAAbHAsSX1kLBAQY'
        'X1kEE4AcASAcAV1dAD8rABg/KxESATk5ETMRMzEwARQCBCMiJAI1EAAhMgQSBxAAIyIAERAAMzIABdep/sTX2f7FpgFy'
        'AUrXATynw/758PL++AEL7fQBBQLH3f60srABTd4BUgF9q/663gEHASz+2P71/vf+yQEtAAIAqAAABOoFgQAKABEAPEAg'
        'DwUFBgsABgASEw8EX1kPDwUHBw5fWQcDBRIgEwEgEwFdcQA/PysREgA5GC8rERIBOTkRMxEzETMxMAEUBCMhESMRITIE'
        'BxApAREhIATq/vvg/mK/AlHtAQTA/rj+hQGDAUAD2cjs/dsFgd7MARH91AACAGH+fQXXBZYAGAAkAD9AJB8SGQAACAMO'
        'EgUlJhUcX1kVBA4iX1kDDhMLBl9ZC4AmASAmAV1dAC8rABg/MysAGD8rERIBFzkRMxEzMTABEAAFHgEzMjcVBiMiJicm'
        'JAI1EAAhMgQSBxAAIyIAERAAMzIABdf+1P71KYVmNzxdVZfDPsb+4ZcBcgFK1wE8p8P++fDy/vgBC+30AQUCx/7W/oAj'
        'fnANhharyAq1AUPVAVIBfav+ut4BBwEs/tj+9f73/skBLQACAKgAAAVoBYEADQAWAFdALwEMDBMJEwMDBA4JAA0NCQQD'
        'FxgMAhMCX1kTEwAFBRJfWQUDBAASgBgBcBgBIBgBXV1dAD8yPysREgA5GC8rEQAzERIBFzkRMxEzETMRMxESOREzMTAh'
        'ASERIxEhMgQVFAYHAQM0JiMhESEyNgSM/pL+Sb8Cl+4BA7ehAZD4p53+OwHNl6UCSf23BYHVvp3WHP2hA+x7gf34jQAA'
        'AQBd/+wE+AWWAC0AjkAfDAAdHCMWBgUFFhwABC8uDBATFkhJDFkMaQwDDwwBI7j/8EA5ExZIRiNWI2YjAw0jAQwEDCMD'
        'GRkgX1lvHQFZHQFLHQEDAB0BCQUdGQQDCV9ZYAYBUgYBRAYBBgMTAD8zXV1dKwAYPzNfXl1fXV1dKxESADk5X15dXStd'
        'XSsREgEXOREzETMRMxEzMTABFAQhIAM3HgEzMjY1NC4CJy4DNTQkITIWFwcuASMiBhUUHgEXHgUE+P7P/uv9/VK5INCz'
        'uck/cp5gp61kNQEVAQLw/jO8H66aqbJFgsJBgXZnTCsBhcPWAWYlf3d/e0VWOCYWJUpbek+1xJOxIXBlcG9BVTsrDx8r'
        'OlRyAAEALgAABLQFgQAHATBA2QECBAIHAwkIAAQFBF9ZBQMBEnsJAUsJATsJASQJAfsJAcsJAbsJAZsJAYsJAX8JAQJf'
        'CQFPCQEwCQEPCQFn3wkBzwkBsAkBjwkBXwkBTwkBDwkB8AkB3wkBzwkBrwkBnwkBcAkBXwkBQAkBHwkB7wkB3wkBnwkB'
        'bwkBXwkBPwkBHwkBAAkBN+8JAdAJAZAJAYAJAW8JAVAJAS8JAQAJAdAJAa8JAZAJAX8JAW8JAVAJAUAJASAJARAJAf8J'
        'AeAJAb8JAaAJAZAJAWAJAUAJAT8JASAJAQ8JAQdeXV1dXV1dXV1dXXFxcXFxcXFxcXJycnJycnJyXl1dXV1dXV1dcXFx'
        'cXFxcXFxcnJycnJycl5dXV1dX11dXV1dXXFxcXEAPz8rEQAzERIBFzkRMzEwAREjESE1IRUC0L7+HASGBOX7GwTlnJwA'
        'AAEAnv/sBSkFgQATAElALA0QBwQQBBUUDgUDAApfWQATIBUBwBUBsBUBoBUBgBUBcBUBYBUBUBUBIBUBXV1dXV1dXV1x'
        'AD8rABg/MxESATk5ETMRMzEwBSIkJjURMxEUFjMyNjURMxEUBgQC263+/o6/xLm+076R/vcUfvCmA4H8j8HIz8cDZPyR'
        'q/iDAAABAAkAAAVNBYEACAA+QCYHCAEABQMCAgUIAwoJIApQCgIwCmAKkArACvAKBS8KAQcCAwUBEgA/Mz8zAV1dcRES'
        'FzkRMxEzMxEzMTAhIwEzARc3ATMDDsb9wckBhlRUAYTJBYH8IPn5A+AAAQAJAAAHhgWBABkB/ED/GBkIAQEBABQHEQEI'
        'EAEREAQIBwcBCwMHDQoJCQ0EFBkFGxqLGwEbwHx/SDkbASobARkbAQobAfkbAeobAdkbAcobAbgbAYkbmRupGwN4GwFp'
        'GwE6G0obWhsDKRsBGhsBDBsBaP0bAewbAd0bAcwbAb0bAasbAZwbAYsbAXwbAWsbAVwbAUsbATwbASsbARwbAQsbAfwb'
        'AesbAdwbAcsbAbwbAasbAZwbAQCNGwF/GwFtGwFfGwFNGwEvGz8bAh0bAQ8bAf0bAe8bAd0bAc8bAb0bAa8bAZ0bAY8b'
        'AW0bfRsCWxsBTRsBOxsBLRsBGxsBDRsBOPsbAe0bAdsbAc0bQG8BuxsBrRsBmxsBjRsBexsBbRsBSxtbGwI5GwErGwEZ'
        'GwELGwH5GwHrGwHdGwHLGwG9GwGrGwGdGwGLGwF9GwFrGwFdGwFLGwE9GwEBKxsBHxsBAl8bfxufG78b3xv/GwYAGwEI'
        'GBAECQMUDQ0BCBIAPzMzETM/MzMzAV5dXV9xcV9xcXFxcXFxcXFxcXFxcnJycnJycnJycnJycnJyXl1dXV1dXV1dXV1d'
        'XV1dXXFxcXFxcXFxX3FxcXFxcXFycnJycnJycnJycnJycnJyXl1dXV1dXV1dXV1dXXFxcXErcRESFzkRMxEzX15dMxEz'
        'M11dETMzXREzMTAhIwMmJw4BAyMBMxMWFzYSEzMTFhc3PgEBMwXn5PQYLhok/+T+Ycf9LSYYP/a39TggCRsiAQjHA39U'
        '2XSc/GQFgfyBqLJuAQQDZ/yT15Ujc5EDsgAAAQAuAAAFKwWBAAsBCEDFCAkGBQIDAAsDBQQKCQsGDQwbDUsNAosNuw3r'
        'DQMEDRQNNA1EDQRqVA1kDYQNlA20DcQN5A30DQg7DQEkDQELDQH0DQHbDQHEDQGrDQGUDQF7DQFkDQEwDQEkDQEADQH0'
        'DQHQDQHEDQGgDQGUDQFwDQFkDQFADQE0DQEQDQEEDQE54A0B1A0BsA0BpA0BgA0BFA1EDXQNAyQNVA2EDbQN5A0FVA1k'
        'DZQN9A0EQA0BAgANMA0CdwcBeAEBAQQKBwQIBQMDABIAPzI/Mxc5XV0BXV9dXXFycnJycnJeXV1dXV1dXV1dXV1xcXFx'
        'cXFxcXFxcnJycl5dXXEREhc5ETMRMxEzETMxMCEJASMJATMJATMJAQRY/ln+UNMCGP4R0wGIAX3T/h4CCwJo/ZgC3AKl'
        '/dcCKf1i/R0AAAEALQAABSkFgQAIAbBA/wYBAQICBAcIBQQIBAoJBgADCAMYA0gDAwwDAQgEAwESdgoBYgoBVAoBRgoB'
        'NgoBJAoBFgoBBAoB8goBAeAKAdAKAcQKAbAKAaAKAZQKAXAKAWQKAUAKATQKASQKARQKAQAKAWn0CgHkCgHQCgHECgG0'
        'CgGkCgGQCgGACgF0CgFgCgFQCgFECgEgCgEUCgEECgH0CgHgCgHUCgHECgGwCgGkCgGUCgF0CgFkCgFUCgFACgEwCgEk'
        'CgEACgH0CgHECgGQCgGECgF0CgFUCgFECgEkCgEUCgEECgE54AoB1AoBpAoBhAoBcAoBZAoBVAoBNAoBJAoBBAoB9AoB'
        '5AoBwEAzCgG0CgGQCgGECgFUCgE0CgEUCgEECgHkCgHUCgG7CgGkCgFwCgECYAoBMAoBLwoBDwoBXV1dXV9dXV1dXXFx'
        'cXFxcXFxcXFycnJycnJycnJyXl1dXV1dXV1dXV1xcXFxcXFxcXFxcXFxcXJycnJycnJycnJycnJycl5dXV1dXV1dXV1d'
        'XV1dX11xcXFxcXFxcQA/PzMSOV5dETMzERIBOTkRMxEzEjkRMxI5MTABESMRATMJATMDCb794tIBrQGr0gJI/bgCSAM5'
        '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'
        'PysAGD8zEjk/ERIBOTkRMxEzETMxMAE+ATMyFhURIxE0LgEjIgYVESMRMxEUBgcBPTqjfbCntSpgVX+ZtLQHAQOBamOv'
        'zv0vAq5ybzSwlf2CBcz+fj2CCgACAIkAAAE9BcwAAwAHAG5ASAMHBwAEBAgJBQ8EFQEAU1kBAP8JAeAJAd8JAcAJAbAJ'
        'AZ8JAYAJAXAJAR8JAQAJAfAJAd8JAcAJAbAJAaAJAZAJAU8JAR8JAV1xcXFxcXFxcnJycnJycnJycgA/KwAYPz8REgE5'
        'ETMzETMxMBM1MxUDETMRibS0tAUgrKz64AQ6+8YAAv/O/lcBPQXMAAMAEAD3QKwKAwQEAA4OERIPDwcLUFkHGwEAU1kB'
        'AM8SAb8SAY8SAQASAW/vEgHQEgGPEgE/EgH/EgGvEgGfEgGPEgFvEgFQEgFAEgEwEgEgEgHfEgGwEgGgEgGQEgFPEgE/'
        'EgEvEgEAEgE9/xIB7xIB3xIBzxIBsBIBkBIBgBIBcBIBHxIBDxIB/xIB3xIBzxIBvxIBrxIBkBIBTxIB/xIB4BIB0BIB'
        'wBIBgBIBcBIBHxIBXV1dXV1dXXFxcXFxcXFycnJycnJycnJyXl1dXV1dXV1dcXFxcXFxcXFxcnJycl5dXV1dAD8rABg/'
        'KwAYPxESATkRMzMRMzIxMBM1MxURFAYjIic1FzI2NREzibR4eE0yPkU4tAUgrKz6WpmKCYsGSGgEpQAAAQCKAAAEAwXM'
        'AAsAjUBnCAkBCgkKBAALCwcDBAQNDB8NPw0CHw0/DV8N/w0EDw0fDT8NXw1/DQU5DUBTVkhgDYANoA3ADdANBd8NAQAN'
        'YA2ADaANBAANEA0wDUANgA2gDcAN4A3wDQkHAgEHCgQIDwUABBUAFQA/Pz8/FzkBXl1xcXIrXl1xchESOREzMzIRMxI5'
        'OREzETMxMCEBBxEjETMRATMJAQMw/pKEtLQB29P+SQHOAe5t/n8FzPxhAg3+L/2XAAEAigAAAT4FzAADAHZAUQMAAAUE'
        'AQAAFfAFAeAFAd8FAcAFAbAFAZ8FAYAFAXAFAR8FAQ8FAfAFAd8FAcAFAbAFAaAFAZAFAU8FAf8FAeAFAdAFAcAFAYAF'
        'AXAFAR8FAV1dXV1dXV1xcXFxcXFxcnJycnJycnJycgA/PxESATkRMzEwMxEzEYq0Bcz6NAABAIgAAAYjBE4AKQF+QP8Y'
        'KQAAIQkhIBIICSAJKyocJVBZHBAYEQAVFQRQWRUQDA8hCQAVZCsBSysBPysBKysBHysBDysB6ysB3ysBuysBqysBiysB'
        'eysBbysBOysBHysBCysBausrAcsrAbsrAa8rAYsrAX8rAVsrAU8rARsrAfsrAe8rAd8rAcsrAbsrAa8rAZQrAWQrAUsr'
        'ASsrARsrAQQrAfQrAdsrAasrAYsrAX8rAWsrATQrARsrAQ8rATn7KwHbKwG7KwGgKwGUKwF0KwFbKwFLKwErKwEfKwEL'
        'KwH7KwHrKwHLKwGkKwF7KwFbKwFLKwEbKwH0KwHQKwECwCsBoCsBkCsBYCsBTytACwEwKwEvKwEAKwEIXl1dXV1dXV1d'
        'X11dcXFxcXFxcXFycnJycnJycnJycl5dXV1dXV1dXV1xcXFxcXFxcXFxcXFycnJycnJycnJeXV1dXV1dXV1dXXFxcXFx'
        'cQA/MjI/PysREgA5ORg/KxESATk5ETMzETMREjkRMzMxMCERNCYjIgYVESMRNCczHgIXMz4BMzIWFzM+ATMyFhURIxE0'
        'JiMiBhURAwBWcHOGswaqAQIDAgM6lmx7jxwDOJ9xpJWyVnB2gwKunXiwoP2NA1O9KgUsOU9zWmJrbWCyy/0vAq6deK+h'
        '/Y0AAQCIAAAD7gROABoAYUA8EgkJCgAaChobHBIWABYFUFkWEA0PCgAV0BwBwBwBsBwB8BwBsBwB/xwB4BwB0BwBwBwB'
        'sBwBoBwBcBwBXV1dXV1dXXFxcnJyAD8yPz8rERIAORESATk5ETMRMxEzMTAhETQuASMiBhURIxE0JzMeAhczPgEzMhYV'
        'EQM5KlxZgpa0BqoBAgMCAz6jebKlAq5rdjSynv2NA1O9KgUsOU9wXbHM/S8AAgBW/+wEHQROAAoAFgBIQCwRBgsABgAX'
        'GAgOUFkIEAMUUFkDFqAYAZAYAYAYAXAYAWAYAVAYATAYAd8YAV1xcXFxcXFxAD8rABg/KxESATk5ETMRMzEwARACIyIC'
        'ERAhMhIDNCYjIgYVFBYzMjYEHfru7fIB5fjqvYWdno2LlaKLAh7+5P7qASEBEQIw/u/+4eDLz9zW19AAAAIAhP5XBB0E'
        'TQAXACQAXUA3GAAfEQgICQAJJiURBBUCFRtQWRUQDA8IGwIiUFkCFrAmAT8mAZAmAXAmAR8mAf8mAeAmAcAmAV1dXXFx'
        'cXJyAD8rABg/Pz8rERIAOTkREgE5OREzETMzETMxMAEQISInIxYVESMRNCczHgIVMz4BMzISAzQmIyIOARUUFjMyNgQd'
        '/nL6VgUEtAauAQQFBDCegcjGvXqFa3k/iJmGewIi/cq8CKL+WQUGpzYEMWYTZF3+9P7d4sJav5nVysUAAgBW/lcD8ARO'
        'ABYAIgCGQFQXCBEREB0DEAMkIxAbDBAIEwUABRpQWQUQACBQWQAWQCQBICQBzyQBsCQBkCQBICQBACQBUN8kAcAkAU8k'
        'AaAkAYAkAS8kAQ8kAfAkAdAkAQ8kAQheXV1dcXFxcXJycl5dXV1dXXFxAD8rABg/KxESADk5GD8/ERIBOTkRMxEzETMz'
        'MTAFIgIRECEyFhczNDY3MwYVESMRNyMOARM0JiMiBhUUFjMyNgHkzsABjnugNgIIBK0HtAQCNp7SipeJeHmGmYoUARYB'
        'FgI2V2UekwU77Ps2Abeka1sCPtPMzN/jxNoAAAEAiAAAAogETgATACNAEAYTEwAADBQVDwYKEAQPABUAPz8/MzMREgE5'
        'OREzETMxMDMRNCczFhUzPgEzMhcVJiMiBhURjgaqCAQrcGYkJSQ8cHYDPnKKuCWLZgqlCsG0/cwAAQA5/+wDtgRLACoA'
        'ZEA8BwYiFRwbDQAAGxUGBCssDSIDGBgfUFkcGBADClBZBwMWECwBACwB8CwB4CwBwCwBYCwBgCwBPywBECwBXV1dcXFx'
        'cXJyAD8zKwAYPzMrERIAOTkREgEXOREzETMRMxEzMTABFAYjIiYnNx4BMzI2NTQmLwEuAjU0NjMyFhcHLgEjIgYVFB4B'
        'Fx4DA7bn0MrbIZ8XkICJf1higZuDStPKs9Mcog+Dbnp0MF6Xj35JKAErmaaFjR9XUVRUQFAaIihNblCUm36LFEhNSksu'
        'PColJD1KYQAAAQAf//ACKgUsABQARUAkDRQUCw8PCQQEFhUOBQgFUFkLDwkBDAMJQAgPAhJQWQIWgBYBXQA/KwAYPxrN'
        'X15dMysRADMREgE5ETMzETMyETMxMCUGIyI1ESM1MzczFTMVIxEUFjMyNwIqWV3YfYQ1eMjIMz8kRAgY9QLSg/Lyg/1V'
        'Tj8OAAABAIX/7APrBDoAGgBfQDsSCAgLARkLGRwbEgUWBVBZFhYNFQkAD9AcAcAcAbAcAfAcAbAcAf8cAeAcAdAcAcAc'
        'AbAcAaAcAXAcAV1dXV1dXV1xcXJycgA/Mj8/KxEAMxESATk5ETMRMxEzMTABERQeATMyNjURMxEUFyMuAicjDgEjIiY1'
        'EQE6KlxZgpa0BqoBAgMCAz6jebKlBDr9Umt2NLKeAnP8rb0qBSw5T3BdscwC0QABAAcAAAP5BDoACgFcQPgBAAYJCgMC'
        'AgYKAwsMCQIPBgEVmwwBhAwBYAwBVAwBRAwBIAwBFAwBBAwB4AwB1AwBxAwBoAwBlAwBhAwBYAwBVAwBRAwBFAwBBAwB'
        'Z9QMAcQMAZQMAYQMAVQMAUQMARQMAQQMAdsMAcQMAZsMAYQMAVsMAUQMARsMAQQMAdsMAcQMAZsMAYsMAVsMAUsMARsM'
        'AQsMATfbDAHLDAGbDAGLDAFbDAFLDAE/DAEgDAEUDAEEDAHgDAHUDAHEDAGgDAGUDAGEDAFgDAFUDAFEDAEgDAEUDAEE'
        'DAHUDAHEDAGgDAGUDAGEDAFgDAECUAwBLwwBEAwBAAwBB15dXV1dX11dXV1dXXFxcXFxcXFxcXFxcXJycnJycnJycnJe'
        'XV1dXV1dXV1xcXFxcXFxcXJycnJycnJyXl1dXV1dXV1dXV1dcXFxcXFxcXEAPzM/MxESARc5ETMRMxEzMzEwISMBMxMW'
        'Fz8BEzMCZdX+d8DuDTgjJ/a/BDr9QCjFdXYCwgAB//0AAAXMBDoAFAGuQP8BABEHBgwPDgMTCQwDEQMUCAcUARQWCAgB'
        'CwgVAw4TAwgPAQwRAwcVdhYBZhYBVBYBRhYBNhYBJBYBFhYBBBYB9BYB5hYBxBYBshYBpBYBlhYBhhYBZhYBVBYBRBYB'
        'NhYBFBYBBhYBafYWAeIWAdQWAcYWAbYWAZYWAYQWAXQWAWYWAUYWATYWASQWARYWAQYWAfQWAeYWAbYWAaQWAZQWAYYW'
        'AWkWAVYWAUQWATYWAQYWAeQWAdYWAcQWAbYWAaYWAYkWAXIWAQFgFgFUFgEkFgEEFgE49BYB1BYBxBYBpBYBgBYBdBYB'
        'SxYBMBYBJBYBFBYB+xYBxBYBoBYBlBZAMAF7FgFkFgFEFgE0FgEbFgHwFgHkFgHLFgG0FgGUFgGEFgFkFgE/FgECEBYB'
        'ABYBCF5dXV9dXV1dXV1dXXFxcXFxcXFxcXJycnJycnJycnJeXV1dXV9dXV1dXV1dcXFxcXFxcXFxcXFycnJycnJycnJy'
        'cnJycl5dXV1dXV1dXV1dXV1dcXFxcXFxcXEAPxczPxczEQEzXl0RM10REhc5MzIRMzMRMzMRMzMxMCEjAycOAQMjATMT'
        'Fhc3EzMTFzcTMwSW0b0kCSa50P7RsrcHJBHiwb0uH82wAv2pLan9MAQ6/SEYrkoDW/0ZvosDGgABABcAAAPqBDoACwFU'
        'QKAACwgJCgQBBwYFAgMDBQcJCwUNDIQNAXYNAUQNVA1kDQM2DQEkDQEWDQEEDQH2DQHkDQHWDQHEDQG2DQGkDQF2DYYN'
        'lg0DZA0BBg0WDSYNRg1WDQVnBg1GDVYNhg2WDcYN1g3mDQiZDdkNAmQNAVYNAUQNATYNASQNARYNAQQNAdYN5g32DQPE'
        'DQEGDSYNNg1GDQQ3Zg2mDbYN5g32DQUNuP/AQDY9Qkg5DQEiDQEBAA0QDQL0DQHADdAN4A0DtA0BgA2QDaANA3QNAWAN'
        'AVQNAUANATQNASANAQ24/8BAIhIYSKANAQIADRANUA1wDYANkA0GBwoEAQQHAwIIBg8AAhUAPzM/MxIXOREzAV5dX10r'
        'cXFxcXFxcXFxcXJfcnIrcl5dXV1xcXFxcXFxcXJeXV1dXV1dXV1dcXFxcXFxcRESFzkRMxEzETMzMxEzETMxMCEJASMJ'
        'ATMJATMJAQMh/t3+28IBgf6RxwEOAQzJ/pEBhgG8/kQCLAIO/lsBpf30/dIAAAEABf5XA/wEOgAWAeRA/xMIDxESCgkJ'
        'Aw8SBBgXCBMPExcRCQ8ABVBZABuSGAGCGAF0GAFkGAFSGAFCGAE0GAEkGAESGAECGAH0GAHkGAHSGAHCGAG0GAGkGAGS'
        'GAGCGAF0GAFkGAFWGAFCGAE0GAEkGAEWGAECGAFn9BgB5BgB1hgBwhgBtBgBpBgBlhgBghgBdBgBZBgBVhgBQhgBNBgB'
        'JBgBFhgBAhgB9BgB5BgB1hgBwhgBAbAYAaAYAZQYAYQYAXAYAWAYAVQYAUQYATAYASAYARQYAQQYAfAYAeAYAdQYAcQY'
        'AbAYAaAYAZQYAYQYAXAYAWAYAVQYAUQYATAYASAYARQYAQQYATfgGEBaAdQYAcQYAaAYAZQYAYQYAWAYAVQYAUQYASAY'
        'ARQYAQQYAeAYAdQYAcQYAaAYAZQYAYQYAWAYAQJQGAEwGAEgGAEAGAHAGAGQGAGAGAFQGAEvGAEQGAEAGAEHXl1dXV1d'
        'XV1xcXFxX3FxcXFxcXFycnJycnJycnJycnJeXV1dXV1dXV1dXV1dXV1dXXFxcXFxcXFxcXFxcV9xcXFxcnJycnJycnJy'
        'cnJycnJycl5dXV1dXV1dXV1dXV1dXV1dcXFxcXFxcXFxcQA/KwAYPzMRMzMRMxESARc5ETMRMxEzMzEwEyInNRYzMj8B'
        'ATMTHgIXNxMzAQ4Cv0oyJi6oYhH+U8DkBQ5MA0btvv5gQ3SN/lcLhwb3KwQ1/aoOJ94NxQKx+8atqVMAAQBTAAADmgQ6'
        'AAkBYkD8AgYHAQEDBggECwoGAwQDUFkEDwEHAAdQWQAV1AsBxAsBtAsBpAsBlAsBhAsBdAsBZAsBVAsBQAsBNAsBIAsB'
        'FAsBAAsB9AsB4AsB1AsBwAsBtAsBpAsBlAsBhAsBdAsBZAsBVAsBRAsBNAsBJAsBBAsB5AsBxAsBtAsBoAsBlAsBgAsB'
        'dAsBZAsBVAsBRAsBNAsBJAsBFAsBBAsBN/QLAeQLAdQLAcQLAaQLAYQLAWQLAUQLAQQLAfQLAeQLAdQLAcQLAbQLAaQL'
        'AZQLAYQLAWQLAUQLASQLAQQLAeALAQLQCwHACwGwCwGgCwGQCwFwCwFQCwEgCwEACwEHXl1dXV1dXV1dXV9dcXFxcXFx'
        'cXFxcXFxcnJycnJycnJyXl1dXV1dXV1dXV1dXV1dcXFxcXFxcXFxcXFxcXFxcnJycnJycnJycnJycnIAPysRADMYPysR'
        'ADMREgEXOREzETMxMDM1ASE1IRUBIRVTAl39xQMQ/aICc4kDJouJ/NqLAAABACL+VwKIBcwAIwBfQDoWHh4LAxEiAwcE'
        'JCUZCAcIB/VZDwhPCAIvCL8IzwgDDwgvCE8I7wgECwMICA8ADxL1WQ8AACH1WQAbAD8rABg/KxESADkYL19eXXFyKxES'
        'ADkREgEXOREzMxEzMTABIiY1ETQmJzU+ATURNDY7ARUjIgYVERQGBxUeARURFBY7ARUCAX+JaW5taoWDhz9bTWpYWWlN'
        'Wz/+V5qLAWl1cwV/BHN1AWqNmIFrbP6cXokVAhWIYf6bam2BAAEAt/5OAV0FzAADAUFA6AAEBQEAAIQFAXQFAWAFAVQF'
        'AUQFATQFASQFAeAFAdQFAcQFAbQFAaQFAYQFAXQFAWQFASAFARQFAQQFAWj0BQHkBQG0BQFwBQFkBQFUBQFEBQE0BQHA'
        'BQGwBQGkBQGUBQGEBQF0BQE7BQErBQEQBQEABQEC8AUB4AUB0AUBwAUBfwUBbwUBUAUBQAUBMAUBIAUBEAUBAAUBOM8F'
        'AbAFAaAFAXAFAWAFAR8FAQAFAfAFAeAFAaAFAVAFAUAFATAFASAFAe8FAd8FAc8FAb8FAa8FAZAFAYAFAXAFAUAFAS8F'
        'AR8FAQ8FAQdeXV1dXV1dXV1dXV1dcXFxcXFxcXJycnJycnJeXV1dXV1dXV1dXV1dX3FxcXFxcXFxcXFycnJycnJycl5d'
        'XV1dXV1dXV1dXXFxcXFxcXEALz8REgE5MTATETMRt6b+Tgd++IIAAAEAIv5XAocFzAAjAF9AOgsWFgQdGh0jEAQkJQcZ'
        'Ghka9VkPGU8ZAi8ZvxnPGQMPGS8ZTxnvGQQLAxkZESIiI/VZIhsREPVZEQAAPysAGD8rERIAORgvX15dcXIrERIAORES'
        'ARc5ETMzETMxMBMyNjURNDY3NS4BNRE0JisBNTMyFhURFBYXFQ4BFREUBisBNV5bT2hZVmtPWzyEg4Vqb3BpiX+E/tht'
        'agFlYogUAhSHYQFkbGuBmI3+lnR0BH8EdHX+l4qbgQAAAQBcAikEUAMnABYAb0AJCBMXGAARrVkIuP/AtCY8SAgAuP/A'
        'sxccSAC4/8CzDhRIALj/wEAsCQxIAEATQCk8SBMLCwWtWR8LTwufCwNvC38LnwuvC88L7wv/CwcLQAkNSAsALytdcSsA'
        'GBDEKxrdKysrxCsrERIBOTkxMAEiJicmIyIGBzU2MzIWFx4BMzI3FQ4BA0xFkUmBWEN0QW+YNH+CH3gtgnI6dQIpLBot'
        'KS+PVBouDCFclSomAAACAHoDXAK4BZYACwAXACtAFQwAEgYABhkYAxWvWQMJQAkPr1kJBAA/KwAaGBDMKxESATk5ETMR'
        'MzEwARQGIyImNTQ2MzIWBzQmIyIGFRQWMzI2Aripdnapp3h4p21nS0tnaUlKaAR5d6aodXWopndMaGpKSmppAAABAIz+'
        'VwRtBDoAHgBXQDIXCgoRCx4CAgELASAfFwYaBlBZGhYUD1BZFBYKAQ8AG+AgAdAgAcAgAbAgAYAgAWAgAV1dXV1dXQA/'
        'PzM/KwAYPysRADMREgE5OREzETMRMzMRMzEwExEzERQWMzI2NREzERQWMzI3FQYjIiYnIwYjIiYnEYy1a3eAkrQkKhkd'
        'QTBbXwUDasFDbR/+VwXj/VKKi66iAnP80ExFCIEUXmTCKSb+HAABAI4A4QQfBHMACwAjQBAECgYIAgAACggDDQwABwEH'
        'ABkvcRESARc5ETMRMxEzMTATCQE3CQEXCQEHCQGOAWL+oGgBXgFeaf6iAWBm/p/+nAFKAWIBYGf+nwFfaf6k/qBpAWH+'
        'nQAAAAEAAABjAVIAVABcAAYAAgAQAC8AXAAAAqQCBAAEAAEAAAAAAAABBgEtAcECgAL7A40DpwPXBAgEUwSNBLIEzgTl'
        'BP0FPwVrBbgGJQZmBsQHJQdVB8cILAhSCIIItAjnCRgJeAouCoEK7AtNC40Lzgv/DGcMuA0KDUwNgg2gDnoOvg8LD0wP'
        'rxAFEJERPBGDEbgS5xOLFHoUthTbFPQVGRXKFeEWBxaWFvwXWxe9GCYYjxkmGX4ZyBphGsMbChwFHF8crB0THY0dvh4w'
        'HnMezR+TIJIhXCJ3Iz4joiRQJLQlEiVOJagl2wABAAAAAgAAGJnULF8PPPUCHwgAAAAAAMyTHUcAAAAAzJMdR/um/ZMK'
        'agfXAAAACAAAAAAAAAAABgAAzQI5AAACOQC5AtcAVwRzAAkEcwAWBx0ASQVWAEgBhwBoAqoAfwKqAAwDHQAhBKwAZAI5'
        'ALgCqgBbAjkAuwI5AAAEcwBQBHMAnARzAGcEcwBOBHMALwRzAFIEcwBoBHMAaQRzAFkEcwBgAjkAuwI5ALgErABlBKwA'
        'ZASsAGUEcwBUCB8AoQVWAAQFVgCoBccAaAXHAKgFVgCoBOMAqAY5AGcFxwCoAjkAvQQAACAFVgCoBHMAqAaqAKgFxwCo'
        'BjkAYQVWAKgGOQBhBccAqAVWAF0E4wAuBccAngVWAAkHjQAJBVYALgVWAC0E4wBBAjkAkgI5AAACOQAQA8EACgRz/+EC'
        'qgBqBHMAVwRzAIQEAABXBHMAVgRzAFcCOQAdBHMAVgRzAI4BxwCJAcf/zgQAAIoBxwCKBqoAiARzAIgEcwBWBHMAhARz'
        'AFYCqgCIBAAAOQI5AB8EcwCFBAAABwXH//0EAAAXBAAABQQAAFMCrAAiAhQAtwKsACIErABcAzMAegScAIwErACOAAEA'
        'AAc+/k4AQwq0+6b6egpqAAEAAAAAAAAAAAAAAAAAAABjAAMEogGQAAUAAAWaBTMAAAEbBZoFMwAAA9EAZgISCAUCCwYE'
        'AgICAgIEAAAAAwAAAAAAAAAAAAAAADFBU0MAQAAgANcF0/5RATMHPgGyAAAAAQAAAAAEOgWBAAAAIAAOAAAAAgAAAAMA'
        'AAAUAAMAAQAAABQABAA4AAAACgAIAAIAAgB+ALAAtQDX//8AAAAgALAAtQDX////4f+w/6z/iwABAAAAAAAAAAAAAEBH'
        'W1pZWFVUU1JRUE9OTUxLSklIR0ZFRENCQUA/Pj08Ozo5ODc2NTEwLy4tLCgnJiUkIyIhHxgUERAPDg0LCgkIBwYFBAMC'
        'AQAsILABYEWwAyUgEUZhI0UjYUgtLCBFGGhELSxFI0ZgsCBhILBGYLAEJiNISC0sRSNGI2GwIGAgsCZhsCBhsAQmI0hI'
        'LSxFI0ZgsEBhILBmYLAEJiNISC0sRSNGI2GwQGAgsCZhsEBhsAQmI0hILSwBECA8ADwtLCBFIyCwzUQjILgBWlFYIyCw'
        'jUQjWSCw7VFYIyCwTUQjWSCwBCZRWCMgsA1EI1khIS0sICBFGGhEILABYCBFsEZ2aIpFYEQtLAGxCwpDI0NlCi0sALEK'
        'C0MjQwstLACwKCNwsQEoPgGwKCNwsQIoRTqxAgAIDS0sIEWwAyVFYWSwUFFYRUQbISFZLSxJsA4jRC0sIEWwAENgRC0s'
        'AbAGQ7AHQ2UKLSwgabBAYbAAiyCxLMCKjLgQAGJgKwxkI2RhXFiwA2FZLSyKA0WKioewESuwKSNEsCl65BgtLEVlsCwj'
        'REWwKyNELSxLUlhFRBshIVktLEtRWEVEGyEhWS0sAbAFJRAjIIr1ALABYCPt7C0sAbAFJRAjIIr1ALABYSPt7C0sAbAG'
        'JRD1AO3sLSywAkOwAVJYISEhISEbRiNGYIqKRiMgRopgimG4/4BiIyAQI4qxDAyKcEVgILAAUFiwAWG4/7qLG7BGjFmw'
        'EGBoATpZLSwgRbADJUZSS7ATUVtYsAIlRiBoYbADJbADJT8jITgbIRFZLSwgRbADJUZQWLACJUYgaGGwAyWwAyU/IyE4'
        'GyERWS0sALAHQ7AGQwstLCEhDGQjZIu4QABiLSwhsIBRWAxkI2SLuCAAYhuyAEAvK1mwAmAtLCGwwFFYDGQjZIu4FVVi'
        'G7IAgC8rWbACYC0sDGQjZIu4QABiYCMhLSxLU1iKsAQlSWQjRWmwQIthsIBisCBharAOI0QjELAO9hshI4oSESA5L1kt'
        'LEtTWCCwAyVJZGkgsAUmsAYlSWQjYbCAYrAgYWqwDiNEsAQmELAO9ooQsA4jRLAO9rAOI0SwDu0birAEJhESIDkjIDkv'
        'L1ktLEUjRWAjRWAjRWAjdmgYsIBiIC0ssEgrLSwgRbAAVFiwQEQgRbBAYUQbISFZLSxFsTAvRSNFYWCwAWBpRC0sS1FY'
        'sC8jcLAUI0IbISFZLSxLUVggsAMlRWlTWEQbISFZGyEhWS0sRbAUQ7AAYGOwAWBpRC0ssC9FRC0sRSMgRYpgRC0sRSNF'
        'YEQtLEsjUVi5ADP/4LE0IBuzMwA0AFlERC0ssBZDWLADJkWKWGRmsB9gG2SwIGBmIFgbIbBAWbABYVkjWGVZsCkjRCMQ'
        'sCngGyEhISEhWS0ssAJDVFhLUyNLUVpYOBshIVkbISEhIVktLLAWQ1iwBCVFZLAgYGYgWBshsEBZsAFhI1gbZVmwKSNE'
        'sAUlsAglCCBYAhsDWbAEJRCwBSUgRrAEJSNCPLAEJbAHJQiwByUQsAYlIEawBCWwAWAjQjwgWAEbAFmwBCUQsAUlsCng'
        'sCkgRWVEsAclELAGJbAp4LAFJbAIJQggWAIbA1mwBSWwAyVDSLAEJbAHJQiwBiWwAyWwAWBDSBshWSEhISEhISEtLAKw'
        'BCUgIEawBCUjQrAFJQiwAyVFSCEhISEtLAKwAyUgsAQlCLACJUNIISEhLSxFIyBFGCCwAFAgWCNlI1kjaCCwQFBYIbBA'
        'WSNYZVmKYEQtLEtTI0tRWlggRYpgRBshIVktLEtUWCBFimBEGyEhWS0sS1MjS1FaWDgbISFZLSywACFLVFg4GyEhWS0s'
        'sAJDVFiwRisbISEhIVktLLACQ1RYsEcrGyEhIVktLLACQ1RYsEgrGyEhISFZLSywAkNUWLBJKxshISFZLSwgiggjS1OK'
        'S1FaWCM4GyEhWS0sALACJUmwAFNYILBAOBEbIVktLAFGI0ZgI0ZhIyAQIEaKYbj/gGKKsUBAinBFYGg6LSwgiiNJZIoj'
        'U1g8GyFZLSxLUlh9G3pZLSywEgBLAUtUQi0ssQIAQrEjAYhRsUABiFNaWLkQAAAgiFRYsgIBAkNgQlmxJAGIUVi5IAAA'
        'QIhUWLICAgJDYEKxJAGIVFiyAiACQ2BCAEsBS1JYsgIIAkNgQlkbuUAAAICIVFiyAgQCQ2BCWblAAACAY7gBAIhUWLIC'
        'CAJDYEJZuUAAAQBjuAIAiFRYsgIQAkNgQlmxJgGIUVi5QAACAGO4BACIVFiyAkACQ2BCWblAAAQAY7gIAIhUWLICgAJD'
        'YEJZWVlZWVmxAAJDVFhACgVACEAJQAwCDQIbsQECQ1RYsgVACLoBAAAJAQCzDAENARuxgAJDUliyBUAIuAGAsQlAG7IF'
        'QAi6AYAACQFAWblAAACAiFW5QAACAGO4BACIVVpYswwADQEbswwADQFZWVlCQkJCQi0sRRhoI0tRWCMgRSBksEBQWHxZ'
        'aIpgWUQtLLAAFrACJbACJQGwASM+ALACIz6xAQIGDLAKI2VCsAsjQgGwASM/ALACIz+xAQIGDLAGI2VCsAcjQrABFgEt'
        'LLCAsAJDULABsAJDVFtYISMQsCAayRuKEO1ZLSywWSstLIoQ5S1BIQAJAT8AAQE5AFUBPgABATkAVQFCAUAAFAAfAUEB'
        'QAAfAB8BOwAzAToAVQE4ADMBOQBVAEABBwABAB8BBwABAJ8BBECqAcD9Aa/9AQD9AQpP+wEg+wH1UCgf8kYoH/FGKh/w'
        'RisfX+9/7wIP70/vX++P76/vBQvl5B4f4+JGHw/iAUDiRhYf4eBGH8/g3+Dv4ANA4DM2RuBGGB/u7f8f7QHoVexI61Xq'
        'MgBV6ejoVedIAFXmAP8f3T3fVd8BA1XePQNV3AP/Hw/VH9UCD9Uf1QJAyhgbRs/CAb3APB/BUCYfvL4oH/+5AVC4cLiA'
        'uAO4/8BA/7gSMkYftz+3T7dvt3+3n7evtwcYtgFwsqCysLIDD7IBkLUBsLUBD7UBCA+zP7PvswOAsJCwArCwwLDQsAMv'
        'rz+vAqCtsK0CwK3QrQIvrD+sAp+rAcCq0KoCT6mPqQIvqW+pv6n/qQScmyQfUJsBb5YBv5YBlkYdH5WUFx8PlB+Uf5SP'
        'lP+UBTCRQJECgJEBcI+AjwKQjwHAj9CPAk+MX4xvjAOGRv8fn4UBhIMxH3RzPx9zUCYfb248H25GNR8aARhVGTMYVQcz'
        'A1UGA/8fYFAmH19QJh9cRjEfW1pIH1pGMR8TMhJVBQEDVQQyA1VsAwEMAzwDTANsA3wDBe9R/0BkUQJAUTU4RkBRJShG'
        'z1ABSUYgH0hGNR9HRjUfr0YB30bvRgKARgEWMhVVEQEPVRAyD1UCAQBVAQABHx8PPw9fD38PBA8PLw9PD28Pjw/fD/8P'
        'Bz8Pfw/vDwNvAAFPAAGAFgEFAbgBkLFUUysrS7gH/1JLsAdQW7ABiLAlU7ABiLBAUVqwBoiwAFVaW1ixAQGOWYWNjQBC'
        'HUuwMlNYsGAdWUuwZFNYsEAdWUuwgFNYsBAdsRYAQllzdHN0dSsrKysrAXN0dSsrKwB0Kytzc3UrKysBKysrACsrKysr'
        'KwErKwArKwErcysAdHN0dXN0cysBK3R1AHMrc3QBc3N0AHN0dHN0cwFec3N0c3MAc3Mrc3MBKwArASsAcyt0dSsrKysr'
        'KysrKysrASsrdCsrXnMrACtec3QBKysrACtzc15zc3MBc3NzACsrKysrKxheAAXMBcwAfQWBABUAeQWBABUAAAAAAAAA'
        'AAAAAAAAAAQ6ABQAdwAA/+wAAAAA/+wAAAAA/+wAAP5XAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAAAAAAALQAvQCvAKAAAAAAAAAAAAAAAAAA'
        'iAB+AAAArAAAAAAAAAAAAAAAAAC/AMMAqwAAAAAAmwCNAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAuQCqAAAAAAAA'
        'AJQAmQCHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGoAgwCNAKQAtAAAAAAAAAAAAAAAYABqAHkAmACsALgApwAAASIB'
        'MwDDAGsAAAAAAAAA2wDJAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHhAckAkgCoAGsAkgC3AGsAmwAAAnsC8gCSAlIAbgLX'
        'A4EAggCJAKAAnwFpAI8AAAFgAKQBWwBeAIIAAAAAAAAAXgBlAG8AAAAAAAAAAAAAAAAAAACKAJAApQB6AIAAAAAAAAAA'
        'AAAABYH/8wAN/LMAgwCJAI8AlgBpAHEFzAAP/B7/8gA0BOYADf7UAL8DHwCnAK4AtQAAAAAAgQAAAAAAAAAAB0gDagK2'
        'AgL9kwAAAJEAZwCRAGEB2QAAAo0DQQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABoEEaAAUBMsAAP/s/9P+fwCDANsAqgC6'
        'AKAAzwAAAAcAWgADAAEECQAAAK4AAAADAAEECQABAB4ArgADAAEECQACAA4AzAADAAEECQADADQA2gADAAEECQAEAB4A'
        'rgADAAEECQAFABwBDgADAAEECQAGABwBKgBEAGkAZwBpAHQAaQB6AGUAZAAgAGQAYQB0AGEAIABjAG8AcAB5AHIAaQBn'
        'AGgAdAAgACgAYwApACAAMgAwADEAMAAgAEcAbwBvAGcAbABlACAAQwBvAHIAcABvAHIAYQB0AGkAbwBuAC4AIAAKAEMA'
        'bwBwAHkAcgBpAGcAaAB0ACAAKABjACkAIAAyADAAMQAyACAAUgBlAGQAIABIAGEAdAAsACAASQBuAGMALgBMAGkAYgBl'
        'AHIAYQB0AGkAbwBuACAAUwBhAG4AcwBSAGUAZwB1AGwAYQByAEEAcwBjAGUAbgBkAGUAcgAgAC0AIABMAGkAYgBlAHIA'
        'YQB0AGkAbwBuACAAUwBhAG4AcwBWAGUAcgBzAGkAbwBuACAAMgAuADAAMAAuADEATABpAGIAZQByAGEAdABpAG8AbgBT'
        'AGEAbgBzAAMAAAAAAAD/JwCWAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADAAgAAgARAAH//wADAAEAAAAMAAAAAAAAAAIA'
        'AQAAAGIAAQAAAAEAAAAKACoAOAADY3lybAAUZ3JlawAUbGF0bgAUAAQAAAAA//8AAQAAAAFrZXJuAAgAAAABAAAAAQAE'
        'AAIACAABAAgAAQAqAAQAAAAQAE4AXABiAIQAkgCsAL4A0AEaAVABggHAAcYB0AHGAdAAAQAQAAEAEgAiACcALQAxADMA'
        'NQA3ADgAOgBHAFMAVwBYAFoAAwAi/48ANf/bADr/2wABABL/aAAIAAH/jwA1/2gAN/9oADj/tAA6/2gAV//bAFj/2wBa'
        '/9sAAwAN/x0AD/8dACL/jwAGAAH/tAA1/2gAN/9oADj/aAA6/2gAWv+0AAQAAf/bAA3++AAP/vgAIv9oAAQANf/bADf/'
        '2wA4/9sAOv/bABIAAf/bAA3/HQAO/48AD/8dABv/HQAc/x0AIv9oADD/2wBC/x0ARP8dAEb/HQBK/7QAUP8dAFP/tABU'
        '/x0AVv+0AFj/jwBa/48ADQAN/0QADv+PAA//RAAb/7QAHP+0ACL/aABC/2gARv+PAEr/2wBQ/48AU/+0AFb/tABa/7QA'
        'DAAN/48ADv/bAA//jwAb/9sAHP/bACL/tABC/7QARv/bAFD/2wBT/9sAVv/bAFr/7gAPAAH/2wAN/vgADv9EAA/++AAb'
        '/48AHP97ACL/aABC/2gARv9EAEr/tABQ/0QAUf9oAFL/RABW/48AV/+PAAEAR//bAAIADf+PAA//jwACAA3/aAAP/2gA'
        'AAABAAAACgAoACoABGN5cmwAGmdyZWsAGmhlYnIAGmxhdG4AGgAAAAAAAAAA'),
    'LibSansB': (
        'AAEAAAARAQAABAAQR0RFRgAQAGMAAFyoAAAAFkdQT1P9Be/kAABcwAAAAiZHU1VCwfXF3wAAXugAAABIT1MvMnv1XbcA'
        'AEs4AAAAYGNtYXACsQGzAABLmAAAAExjdnQgbV9roQAAWCgAAAKIZnBnbX5hthEAAEvkAAAHtGdhc3AAEQALAABcmAAA'
        'ABBnbHlmbvQb1wAAARwAAEdKaGVhZAuN9SgAAElQAAAANmhoZWEOGAPWAABLFAAAACRobXR4tXAg3AAASYgAAAGMbG9j'
        'YXLAh4oAAEiIAAAAyG1heHAEewU0AABIaAAAACBuYW1lJZQ9jQAAWrAAAAHIcG9zdAABANcAAFx4AAAAIHByZXCKoQS5'
        'AABTmAAABJAAAgDBAAAB5wWBAAMABwHgQP8DBwcCBAQJCAEBBQIDBAWdWwSCCQF0CQFkCQFUCQFGCQEyCQEiCQEWCQEE'
        'CQH0CQHkCQHUCQHECQG0CQGkCQGUCQGECQFyCQFkCQFUCQFECQEyCQEkCQEUCQECCQFo9AkB5AkB0gkBxgkBtgkBpgkB'
        'kgkBggkBcgkBZAkBVAkBRAkBNgkBIAkBFAkBBgkB9gkB4gkB1AkBxAkBtAkBpAkBlAkBhAkBdgkBZgkBVgkBNgkBIgkB'
        'ARAJAQAJAfAJAeQJAdQJAcAJAbQJAaQJAZQJAXAJAWAJAVAJAUAJATAJASQJARQJAQQJATj0CQHkCQHQCQHACQGwCQGk'
        'CQGUCQFAWYQJAXQJAWQJAVQJASAJARQJAQAJAfAJAeQJAdQJAcQJAZQJAXAJAWAJAVQJAUQJATQJASQJARQJAQQJAcQJ'
        'AbQJAZQJAYQJAXQJAVQJAUQJARAJAQIACQEHXl1fXV1dXV1dXV1xcXFxcXFxcXFxcXFxcnJycnJycnJycnJycnJeXV1d'
        'XV1dXV1dXV1dXV1dcXFfcXFxcXFxcXFxcXFxcXJycnJycnJycnJycnJycnJeXV1dXV1dXV1dXV1dXV1dXXFxcXFxcXFx'
        'cQAvKwAYPxI5LxESATkRMzMRMzEwASMDIQERIREBx+YgASb+2gEgAaoD1/p/AQ7+8gACAIcDggNEBYEAAwAHAC1AFgMC'
        'BwYABgEJBQIGCQgEAAIAqVsGAgMAPzMrEQAzERIBOTlfXl0RMxEzMTABIwMhASMDIQMn2xsBE/452xsBEQOCAf/+AQH/'
        'AAACACMAAARSBXMAGwAfALtAdgQBABkEGAUHHh8WBBcGCB0cFQQUCQsODxIEEwoXGAYFFBMJCgoTGAUEGgwMHR8aBCEg'
        'BAcICwQMDQyuWQEOHR4EDQAPHB8EEBEQrlkSFRYZBBEPDa8NAs8N/w0CDxFPEa8RA88RAQ0RDREFFBcYAxOxBgkKAwUA'
        'LxczPxczEjk5Ly9dcV1xERczKxEAFzMRFzMrEQAXMxESARc5ERIXOREzETMRMxEzERIXORESFzkREhc5ERIXOTEwAQMz'
        'FSMDIxMhAyMTIzUzEyM1MxMzAyETMwMzFSEDIRMDjUXX9lKcUP7NUJlPm7xGz+5UmVIBM1ScVKT9b0gBNUYDXv60lf6D'
        'AX3+gwF9lQFMlAGB/n8Bgf5/lP60AUwAAwAb/2gEVgXwACgALwA2AI1AUhsjNQQEGS8NBTAACgkrFSAfHxUFCQAFODc1'
        'DQYNdFkAChAKMApACoAKkAoGCQMKCgMGDjQkLyMpGCl1WR0gAQsgASAgGzQvBg8YARhACxBIGAYALy8rXRI5OTMzL11d'
        'KxEAMxEzETMRMzMYL19eXSsRADMREgEXOREzETMRMxEzETMzMzMRMzMzMTABFAYHFSM1LgEnJR4BFxEuASMuAjU0Njc1'
        'MxUeAhcFLgEnERcyBBYBBhUUHgEXATQuAScRNgRW8+5t1/AmAQATcWkDGASipVrl222Dr2sh/vgPV1ALHQEnkv2yuh87'
        'YAFKJEV03QGctccJr6wIu8EvcWkKAYcCBSVlm3CmtgiGhgVJjYMnV18L/qACYLsCgQ6SLDomIP46Mj8oIf6RDwAABQAz'
        '//AG5wWRAAsADwAbACcAMwIJQP8cACIGDg8MDSgTLhkZEw0PBgAGNTQWMbZZEBa3WxArtlkQBw4GCR+2WQMJt1sDJbZZ'
        'AxkNGJQ1AYM1AXQ1AWQ1AVQ1AUU1ATY1ASY1ARc1AfQ1AeM1AQDQNQHCNQG0NQGkNQGSNQGENQF2NQFgNQFSNQFANQEw'
        'NQEiNQEUNQEENQFn9jUB5jUB1jUBwDUBsjUBoDUBkjUBhDUBcjUBZDUBVjUBMjUBIjUBEjUBBDUB8jUB4jUB1DUBxjUB'
        'tjUBkjUBhDUBdjUBZjUBUDUBQjUBNDUBJjUBAjUB8jUB5DUB1jUBxjUBtDUBpDUBljUBhjUBYjUBVDUBRjUBNjUBJjVA'
        'dwEUNQEGNQE30jUBwjUBtDUBpDUBljUBeTUBZjUBSTUBNDUBJDUBFDUBBDUB9jUB2TUBuTUBojUBlDUBhDUBdjUBZjUB'
        'OTUBIDUBEjUBAQA1AfA1AeA1AdQ1Abs1Aas1AZ81AXA1AWA1AVA1AUQ1ARs1AQ81AQcCX15dXV1dXV1dXV1dXV1xX3Fx'
        'cXFxcXFxcXFxcnJycnJycnJycnJyXl1dXV1dXV1dXV1dXV1dXXFxcXFxcXFxcXFxcXFxcnJycnJycnJycnJycnJyXl1d'
        'XV1dXV1dXV1dXV1dX11dcXFxcXFxcXFxAD8/KysrABg/PysrKxESARc5ETMRMxEzETMRMxEzMTABFAYjIiY1NDYzMhYB'
        'IwEzJTIWFRQGIyImNTQ2ATQmIyIGFRQWMzI2ATQmIyIGFRQWMzI2Bue0rrCyrLq0qvtBzgOY0fvVs621sK6yrAUxPUpQ'
        'PUBLSUD8Dz1KUD5BS0o/AbDa5uTc4OHj/XIFgRDi3trn5dzj3fwfn4iKnaCDiAK8nYiHnp6HiAADAFr/7AWHBYkAJAAw'
        'ADoAZUA9ExQlCysFNQAABQsUGy0DDzMRFiAxDTw7Mw8DLQQIGDgiOE9ZIDEWEQQiDxMfEwIOAxMTCB0iFggoUlkIBAA/'
        'KwAYPzMSOS9fXl0SFzkrEQAzEhc5ERIBFzkRMxEzETMRMzEwEzQ2NyY1NDYzMhYVFA4BBxYXNjcXBgcWMzI3FQYjIiYn'
        'BiMiJgE0JiMiBhUUFz4CAyYnBhUUFjMyNlqisErEtajDTo+rY5FoNtFEfVZcQTQ3TFatR6rR5/4DDExBTVE2aVsxUqZq'
        'rIJwQWkBgYfTUpaBnKmgiU18alCvoZ7NRum7SRDLFj47gdUDnTlIVkdXai0+RvzEucBRmWN4MAABAG0DggF9BYEAAwAY'
        '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'
        'CQFozwkBvwkBrwkBkAkBgAkBcAkBPwkBDwkB/wkB4AkBfwkBbwkBXwkBMAkBIAkB7wkB3wkBvwkBoAkBkAkBLwkBHwkB'
        'AAkBOPAJAeAJAa8JAZ8JAY8JAX8JAWAJAVAJAR8JAe8JAd8JAcAJAZAJAV8JAU8JAT8JASAJARAJAQAJAc8JAb8JAZ8J'
        'AYAJAXAJAVAJAUAJAQ8JAQdeXV1dXV1dXV1xcXFxcXFxcXFxcnJycnJycnJyXl1dXV1dXV1dcXFxcXFxcXJycnJycnJy'
        'Xl1dXV1dXV1dXXFxcXFxAC8rABgvK19eXSsREgE5OREzETMxMBMRIREBESERxQEg/uABIALwARr+5v0QARn+5wAAAgDD'
        '/sMB5wQKAAMADgFJQO0DDg4MAAwIAxAPAQCcWw8BLwFPAW8BjwEFDAMBQBYiSAEMDZxbDAioWwyPEAFgEAFQEAEfEAEP'
        'EAH/EAHvEAHQEAHAEAGPEAFfEAFPEAEwEAEAEAFozxABvxABrxABkBABgBABcBABPxABDxAB/xAB4BABfxABbxABXxAB'
        'MBABIBAB7xAB3xABvxABoBABkBABLxABHxABABABOPAQAeAQAa8QAZ8QAY8QAX8QAWAQAVAQAR8QAe8QAd8QAcAQAZAQ'
        'AV8QAU8QAT8QASAQARAQAQAQAc8QAb8QAZ8QAYAQAXAQAVAQAUAQAQ8QAQdeXV1dXV1dXV1xcXFxcXFxcXFxcnJycnJy'
        'cnJyXl1dXV1dXV1dcXFxcXFxcXJycnJycnJyXl1dXV1dXV1dXXFxcXFxAC8rKwAYLytfXl0rERIBFzkRMxEzMTATESEZ'
        'ARQGByM+ATUjESHHASAzObhARYEBIALwARr+5v1SeLhPUaVHARkAAAEAVgB9BFkEzQAGADRAHAMGBAAEBwgBAAQEAgU/'
        'BgEGA18CASACAQ8CAQIAL11dXTMvXTMSOT0vMzMREgEXOTEwExEBFQkBFVYEA/y/A0ECBAFCAYfk/rv+vOMAAgBVASME'
        'WAQpAAMABwBcQD4HAwAEBAgJAAUBCwYEBa1Z3wQBDwQfBI8EAwkDBEAUGUgEDwABCwYBAK1ZMAFwAQIgAUABYAFwAaAB'
        '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'
        'AwAS4AUBsAUBoAUBkAUBgAUBUAUBQAUBAAUB8AUBwAUBsAUBoAUBcAUBYAUBHwUB4AUB0AUBwAUBsAUBgAUBXV1dXV1x'
        'cXFxcXFxcnJycnJycnIAPz8REgE5ETMxMDMRIRGJAScFgfp/AAABAB//7APnBYEAEQA2QB4EAwsODg0DAxMSDQxfWQ0D'
        'AAdfWQQEABNwEwEwEwFxcQA/Mi8rABg/KxESARc5ETMRMzEwBSImJyUeATMyNjURITUhERQGAgzb6ycBJRJiVlhb/ucC'
        'P/oUvtQrbWl2bgLj5/w93PYAAQCJAAAFtAWBAAsAM0AbBwMDBAoBCAkACwsJAQQEDA0FAwASMA0BIA0BXV0APz8REgEX'
        'OREzETMRMxEzETMxMCEBBxEhESERASEJAQRY/gau/tkBJwJ7AVj9pgKLAoeF/f4Fgf2BAn/9rPzTAAABAIkAAASkBYEA'
        'BQAjQBEDAAAEBgcBAwADX1kAElAHAV0APysAGD8REgE5OREzMTAzESERIRWJAScC9AWB+2PkAAABAIkAAAYhBYEAFwFt'
        'QP8VABcQDQ4XDhkYBAoHExcTJxMDCAoYCigKAwkKExUPAw4IABKLGQFrGQFLGQE7GQEbGQH7GQHvGQHEGQGrGQGfGQGL'
        'GQF0GQFbGQFPGQE0GQELGQFn/xkB5BkByxkBuxkBrxkBlBkBexkBbxkBRBkBKxkBHxkBCxkB9BkB2xkBzxkBuxkBixkB'
        'axkBSxkBOxkBGxkB+xkByxkBqxkBixkBexkBWxkBOxkBLxkBBBkBN+sZAcsZAbQZAZsZAXQZAUsZASQZAQsZAfsZAdQZ'
        'AbsZAa8ZAYQZAWsZAV8ZAQJAGQE/GQEfGQHwGQHgGQHPGQGgGQF/GQFPGQE/GQEgGQGzABkBB15dXV1dXV1dXV1xcXFf'
        'cXFxcXFxcXJycnJycnJyXl1dXV1dXV1dXXFxcXFxcXFxcXJycnJycnJycnJycl5dXV1dXV1dXV1dXXFxcXFxAD8yMj8z'
        'OTleXV0RMxESATk5ETMzETMzMTAhETQ2NwIHAyMLARYVESERIRMfATcBIREFGwEJRyL+0v5rDP76AYv8FjA/AQMBiQNW'
        'HTrc/vNq/O4DEgF36Ev8qgWB/OxMveIDO/p/AAABAIkAAAU9BYEADQBQQC8ACgoNBwQEBQ0FDw4BCAsGAwUAEmAPAVAP'
        'AUAPAYAPAXAPAcAPAaAPATAPASAPAV1dXV1xcXJycgA/Mj8zOTkREgE5OREzETMRMxEzMTAhARYVESERIQEmNREhEQPj'
        '/ZoS/voBUQJvEgEGBD2eYPzBBYH7upd8AzP6fwACAFT/7AXjBZYADAAYAEhALBMHDQAHABkaChBfWQoEBBZfWQQToBoB'
        'gBoBcBoBYBoBQBoBMBoB8BoBIBoBXV1xcXFxcXEAPysAGD8rERIBOTkRMxEzMTABFAIEIyAAERAAISAAATQCIyICFRQS'
        'MzISBeOu/rzY/rT+hwF4AU8BTwF5/tPYw8bY3b/G1wLH3P6ysQGHAVQBUwF8/oD+seQBA/7/5uj+9QEEAAIAiQAABRAF'
        'gQALABMASEApDwYGBwwABwAVFAUQX1kFBQYICA9fWQgDBhKAFQFwFQFgFQEwFQEfFQFxcXFxcQA/PysREgA5GC8rERIB'
        'OTkRMxEzETMxMAEUDgEjIREhESEyBAU0KQERITI2BRB855/+ov7ZAnn9ARH+1/76/s8BOXqEA8OI1nX+EAWB6dre/jd5'
        'AAACAFT+bQXjBZYAFgAiAFlANh0RFwAACAMOEQUjJBQaX1kUBAsGX1kLCw4OIF9ZAwMOE4AkAXAkAWAkAUAkATAkAfAk'
        'ASAkAV1dcXFxcXEAPzMvKxEAMxgvKwAYPysREgEXOREzETMxMAEQAAceATMyNwcGIyImJyQAERAAISAAATQCIyICFRQS'
        'MzISBeP+6/cie287PAJ+dKPWQf7j/sUBeAFPAU8Bef7T2MPG2NzAxtcCx/7m/okyY1gKyhy20xsBfQE5AVMBfP6A/rHk'
        'AQP+/+bo/vQBBAACAIkAAAWdBYEADQAVAF1AMwEMDBIJEgMDBA4JAA0NCQQDFxYMEgICEl9ZAgIABQURX1kFAwQAEnAX'
        'AaAXATAXASAXAV1dXXEAPzI/KxESADkYLysREgA5ERIBFzkRMxEzETMRMxESOREzMTAhASERIREhMgQVFAYHCQE0KQER'
        'ITI2BFH+uf6m/tkCwPwBEqiPAX3+kf78/oYBgnyAAhf96QWB2cuU1yL9sAPRy/5gcAAAAQA7/+wFBgWWACoAUkAvDAAd'
        'HCIWBwYGFhwABCwrDCIDGRkgX1kdHRkEAwpfWRAHIAcwBwMwB0AHAgcHAxMAPzMvXXErABg/My8rERIAOTkREgEXOREz'
        'ETMRMxEzMTABFAQhICQnJR4BMyA1NC4BJy4ENTQkISAEFwUuASMgFRQeARceAwUG/s3+1/7x/swsAR0dqJUBNUeBt558'
        'ZEYnAR8BEgEGAQcm/uIWh37+9Dlwq8uvZjYBls/bwMMvcGW8PE40JSUtPVZ0S7/LpL0nW1yoN0YxJStJYYcAAAEAFwAA'
        'BM0FgQAHAURA6AECBAIHAwkIAAQFBF9ZBQMBElAJAUAJATQJASQJAQQJAfQJAeQJAcAJAbQJAaQJAYsJAXAJAWQJAVQJ'
        'ATsJASQJAQQJAWj7CQHkCQHLCQGgCQGQCQGECQFUCQFECQE0CQEECQH0CQHbCQHLCQG0CQGLCQF0CQFbCQE7CQEkCQEL'
        'CQH7CQHrCQHQCQHECQGbCQFECQEbCQELCQE39AkBywkBuwkBmwkBiwkBewkBbwkBSwkBOwkBKwkBBAkB2wkBqwkBiwkB'
        'WwkBSwkBCwkB/wkBAt8JAc8JAY8JAXAJATAJASAJAQAJAQdeXV1dXV1dXV9dcXFxcXFxcnJycnJycnJycnJeXV1dXV1d'
        'XV1xcXFxcXFxcXFxcnJycnJycnJycl5dXV1dXV1dXV1dXV1xcXFxcQA/PysRADMREgEXOREzMTABESERITUhFQMF/tn+'
        'OQS2BJ37YwSd5OQAAQB7/+wFSgWBABEASUAsDQ4FBA4EExINBAMACV9ZABNgEwFQEwFAEwGAEwFwEwHAEwGgEwEwEwEg'
        'EwFdXV1dcXFycnIAPysAGD8zERIBOTkRMxEzMTAFIAAZASERFBYzMjY1ESEREAAC0/7d/ssBJ5+anqoBJ/61FAEcAQgD'
        'cfymp621qQNQ/J7+9P7ZAAEADgAABUgFgQAKADhAHwkKAQAGAwICBgoDDAvADAGfDAFgDAEvDAEJAgMGARIAPzM/MwFd'
        'XV1dERIXOREzETMzETMxMCkBASEBFhc/AQEhA0L+1f33ATQBIhsvFTMBIQExBYH8d1iyVrQDiQAAAQACAAAHiwWBABcB'
        'QEDlFhcBABMQDwQIBwwKCQkMBBMXBRkYaxkBXxkBNBkBGxkB9BkB2xkBzxkBtBkBixkBBBkkGUQZZBkEavsZAdQZAbsZ'
        'AZAZAYQZAWsZAVAZAUQZASsZAQQZAesZAcQZAYsZqxkCFBk0GVQZdBkE+xkB1BkBuxkBrxkBlBkBexkBbxkBUBkBRBkB'
        'KxkBBBkBObQZ1Bn0GQObGQF0GQFLGVsZAjAZASQZAQsZAfAZAQLgGQHPGQGgGQFPGW8ZjxkDEBkB8BkB3xkBsBkBnxkB'
        'cBkBDxlPGV8ZAwgWDwQJAxMMJQwBDAgAEgA/MjJdETM/MzMzAV5dXV1dXV1xcXFxcV9xcnJycnJycl5dXV1dXV1dXV1d'
        'XXFxcXFycnJycnJycnJyXl1dXV1dXXFxcXEREhc5ETMRMzMRMzMRMzMRMzEwKQEDJicOAQMhASETFz4BEyETFhM/ARMh'
        'Bh/+or8jGBgexv6i/pUBK8wuHDWtAUqyFTIZNaoBKwMvkJ2DifywBYH8ctyL/QLi/RJU/th05gMQAAABABIAAAVEBYEA'
        'CwApQBUACwIDCAkGBQMFCQsECgYNDAUDABIAPz8REgEXOREzETMRMxEzMTAhCQEhCQEhCQEhCQEEDv6e/p7+yAHo/kEB'
        'OAE5ATkBNv5UAdUCMf3PAuUCnP4OAfL9ZP0bAAABACMAAAU1BYEACAE4QNkGAQECAgQHCAUECAQKCQYGAAMDAQgEBwES'
        'NAoBJAoBBAoB9AoBxAoBpAoBhAoBdAoBRAoBNAoBFAoBBAoBbOQKAdQKAbQKAaQKAYsKAXAKAQJgCgEwCgEACgHwCgHg'
        'CgGwCgGfCgGACgFwCgFACgEACgHwCgHfCgHACgGQCgGACgEwCgEQCgEACgE6/woB4AoB0AoBoAoBfwoBUAoBIAoBDwoB'
        '8AoB4AoBsAoBjwoBcAoBYAoBTwoBMAoBHwoB8AoBwAoBnwoBgAoBcAoBXwoBQAoBMAoBAAoBXV1dXV1dXV1dcXFxcXFx'
        'cXFxcnJycnJycnJeXV1dXV1dXV1xcXFxcXFxcXJycl9ycnJycnJeXV1dXV1dXV1dcXFxAD8/MxI5LzMzLxESATk5ETMR'
        'MxI5ETMSOTEwAREhEQEhCQEhAz/+2v4KATUBUgFWATUCQv2+AkIDP/2sAlQAAAEAPQAABKgFgQAJAG5ARggCAwcJBwQC'
        'BAoLBwQFBF9ZBQMCCAEIX1kBEo8LAQIACwHwCwHgCwHQCwHACwGwCwGgCwGQCwGACwFwCwFgCwFQCwFACwFdXV1dXV1d'
        'XV1dXV1xX3EAPysRADMYPysRADMREgEXOREzETMxMCkBNQEhNSEVASEEqPuVAvr9UgP2/QYDI9EDyefN/DMAAAEAc/5X'
        'ApEFzAAHACZAFAUAAwYAAwgJAQT1WQEAAAX1WQAbAD8rABg/KxESARc5ETMxMBMRIRUhESEVcwIe/uwBFP5XB3W++gi/'
        'AAABABX/1wImBc0AAwAStgMFAQQBAAAALz8RATMRMzEwBQEzAQEz/uLuASMpBfb6CgABABn+VwI3BcwABwAmQBQCBwQB'
        'BwMJCAUE9VkFAAAB9VkAGwA/KwAYPysREgEXOREzMTATNSERITUhERkBFv7qAh7+V78F+L74iwAAAQAtAgIEfwWBAAYA'
        'JUAQBQQBAQYDBgMIBwMAAAEEAwA/MzMvMhESATk5ERI5ETMzMTAJAiMBIQEDmv66/rzjAYcBQgGJAgIC8P0QA3/8gQAB'
        '/+z/BgSF/1QAAwAZQAwCBQAEAQC7WQABAQEAL3IrEQEzETMxMAc1IRUUBJn6Tk4AAAEAQgSfAj8F3gAFADFAHwAEAwIE'
        'AgcGAAOMWw8AAQ8ALwA/AF8AfwCfAO8ABwAAL11xKxESATk5ETMRMzEwCQE1IRMVAZb+rAEC+wSfARQr/uAfAAIAPP/s'
        'BIAETgAmADMAbUA/JCcnBwcVDg8sAwMPFQM1NAYoUlkGBgBZDmkOAi0OAQMPDh8OAgkEDhISC1FZEhAZLwAvT1kkIQAW'
        'vzUBTzUBXXEAPzIyKxEAMxg/KxEAM19eXV9dXRI5GC8rERIBFzkRMxEzETMRMxEzMTAFIiY1NDY/ATU0JiMiBgclPgEz'
        'MhYVERQWMzI3FQ4DIyImJyMGEwcOAhUUFjMyPgE1AYmdsNvQ6UpUTkkJ/tsb68vN3ikwIB4ZKCgtHmplCgZ2WZBiUitH'
        'O0JtPhSrm6iwAgQ3amdHUg6eo8q6/nZbRQaYBgoGBGhl1QIJAgQjSDxNS0h/RwAAAgCH/+wEjwXMABYAIQA8QCAdBg8P'
        'DRcADQAjIhQaT1kRFBAOAAsVAyBPWQYDFnAjAXEAPzMrABg/Pz8zKxESATk5ETMRMxEzMzEwARACIyImJyMUBgchNjUR'
        'IREHMzYzMhIBNCYjIgYVFBYzMgSP18hzqC0CCQX+7wgBGQQEX/vAzf7bbHFyd3Vy3wIh/vT+12ReI3oRXZoE1f5isND+'
        '3f72uLK/tKzAAAABAFD/7AQ3BE4AGABCQCQUFQoJDwMDCRUDGhkGDU9ZCgoGEAAUYBQCDQMUFAAAEU9ZABYAPysRADMY'
        'L19eXT8zLysREgEXOREzETMRMzEwBSIAERAAMzIWFwUuASMiERAzMjY3BQ4CAlL2/vQBDvi/+iD+5QxgWNndUGwNARoP'
        'gdIUASUBBgEMASvAqQ5TY/6V/oplZA1vrl8AAgBU/+wEXAXMABYAIQA+QCAXAxISEx0JEwkiIxIADBpPWQ8MEAYfT1kD'
        'BhYAFXAjAXEAPz8zKwAYPzMrABg/ERIBOTkRMxEzETMzMTAhLgE1IwYjIgIREBIzMhYXMycRIREUFwE0JiMiBhUQMzI2'
        'A0wECwRb/73O2cdzpy0CAgEZCP7jdXJxbt1veg95KMQBJwEJAQ0BJWBfsgGL+yBkiAIjr723vP6QwwACAFD/7AQtBE4A'
        'EgAZAG9AQxcKEBEWCwsDAxEKAxsaFgtSWRYhEBFIDxYBDgUWFgAGBhNSWQYQAA5RWX8QARAQARAQABafGwFvGwFfGwFP'
        'GwEvGwFdXV1dXQA/Mi9dXSsAGD8rERIAORgvX15dKysREgEXOREzETMRMxEzMTAFIgAREAAzMhIRFSEUFjMyNwUCASIG'
        'ByEuAQJK9P76AQr06fb9SnVslScBCXP+oGNrAwGkCG4UASEBFQEMASD+y/7WCJ6hgRf+2gOxinyDgwAAAQAjAAACrgXM'
        'ABUAQ0AkDRMBBgECAhUEFQQXFgoPUVkKAAAEBQRPWRMFDwEVvxcBgBcBXXEAPz8zKxEAMxg/KxESATkyERI5ETMzETMy'
        'MTABESERIzUzNTQ2MzIXFSYjIgYdATMVAdn+6J6enJ9PYykpSDvVA3z8hAN8vnGTjhC1CTlIVb4AAAIAVP5OBFoETwAh'
        'ACsAYUA6GCIKCh8EAycSEgMfAy0sGw8VJU9ZFxUQDylPWQwPFQAHUVlWBGYEdgQDIgQyBAIFBBUEAgQAG3AtAXEAPzJd'
        'XV0rABg/MysAGD8zKwAYPxESARc5ETMRMxEzETMzMTABIiYnJR4BMzI2PQE3IwYjIgIREBIzMhczNDY3IQYVERQEAzQm'
        'IyIREDMyNgJUxvEcARkPY1B1bAICXf+90NbM7FsFCQUBCgb++g93buHfcHf+TpeMIUFKkI45a8cBHAEIAQkBIMMjeBNs'
        'jvzh5+wD3qe7/pj+n7sAAAEAjwAABGQFzAAVAFBALxIPDxAIBxAHFxYRABAHFRUDAwtQWQMQoBcBkBcB8BcBsBcBoBcB'
        'kBcBcBcB7xcBXXFxcXFxcnIAPysRADMYPzM/ERIBOTkRMxEzETMxMAE+ATMyFhURIREQIyIGFREhESERFAcBpDmsd6y4'
        '/ujBZn3+5wEZCANifHDUzP1SAl4BHa+J/b0FzP5rbWgAAAIAjwAAAagFzAADAAcAVkA2AwcHAAQECAkFDwQVAQBTWQEA'
        'UAkBQAkBsAkBoAkBfwkBYAkBHwkB7wkB0AkBwAkBsAkBgAkBXV1dXV1xcXFxcXJyAD8rABg/PxESATkRMzMRMzEwEzUh'
        'FQERIRGPARn+5wEZBP3Pz/sDBDr7xgAAAv/g/lcBqQXMAAMAEADHQIgHAw0NAAwMERIMDwQIUFkEGwEAU1kBAMASAbAS'
        'Aa8SAYASAVASAUASARASAdASAZASAWASAVASAe8SAcASAbASAZASAYASAXASAVASAUASARASAQASATj/EgHfEgHPEgGg'
        'EgFgEgG/EgGfEgF/EgE/EgEPEgHgEgHQEgGgEgE/EgEfEgEPEgEHXl1dXV1dXXFxcXFxcnJycnJeXV1dXV1dXV1dXXFx'
        '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'
        'sM3NPD8hPWgSh4kCfr7+/r79zk9LDq4iAAEAf//sBFwEOgAWAE9ALw4HBwgAFggWGBcOEhIDUFkSFgwVBwAPoBgBkBgB'
        '8BgBsBgBoBgBkBgBcBgB7xgBXXFxcXFxcnIAPzI/PysRADMREgE5OREzETMRMzEwAREQMzI2NREhERQXISY1Iw4BIyIm'
        'NREBmMBmfQEZCP70DAU4rXesuAQ6/aH+46+JAkT8uIpokEd7cNPMAq8AAAEACAAABGoEOgAKAVNA/wMCAQAGCQoKBgID'
        'CwyUDAGADAFiDHIMAlQMAUIMATQMASYMARIMAQQMAfQMAeYMAdIMAQHADAGkDLQMAoAMkAwCZAx0DAJADFAMAjQMARAM'
        'AQQMAWf0DAHQDOAMArQMxAwCoAwBhAyUDAJgDAFEDFQMAiAMARQMAdQM5AwCywwBkAygDAKEDAFgDHAMAkQMVAwCIAww'
        'DAIUDAHwDAHUDOQMArAMAWQMdAyUDKQMBEAMASQMNAwCAAwBNwJwDIAMsAzADPAMBV8MAQAMEAxADAPQDAGvDAGQDAFv'
        'DAFQDAEvDD8MAn8Mjwy/DO8M/wwFUAwBDwwfDD8MAwcJAg8GAbAVAD8zPzMBXl1dXXFxcXFxcXJycl9eXV1dXV1dXXFx'
        'cXFxcXFxcnJycnJycnJyXl1dXV1dXV1dX11dXXFxcXFxcXFxcRESFzkRMxEzMxEzMTApAQEhExYXPgETIQLb/rD+fQEp'
        'vQ84Cj7HASYEOv2jMsgpzgJgAAH/+gAABj0EOgAUAbpA/wEAEQ4NBAcGCgoEEQMIExQUFgkICBWPFgF5FgFrFgFdFgFP'
        'FgE7FgEtFgEbFgENFgH5FgHrFgHdFgHPFgGpFrkWApsWAY0WAX8WAWsWAV0WAUsWAT0WARsWKxYCDRYBaP8WAdkW6RYC'
        'yxYBvRYBqxYBnRYBiRYBexYBbRYBSxZbFgI9FgErFgEZFgELFgH7FgHtFgHbFgHNFgG5FgGrFgGZFgGLFgFtFn0WAlsW'
        'AUkWASsWOxYCHRYBAQ8WAbsW2xbrFgOvFgFrFosWAk8WXxYCNBYBCxYbFgI46xYB3xYByxYBtBYBmxYBfxaPFgJkFgFL'
        'FgE/FgEbFgH7FgHkFkA/AcsWAb8WAZQWpBYCexYBbxYBKxZLFgL7FgHvFgECwBbQFgKPFq8WAnAWARZACg1IABYBCBMN'
        'BAgPEQoKBwAVAD8yMhEzPzMzMwFeXStdXV1fXV1xcXFxcXFxcXJycnJycnJycnJeXV1dXV1dcV9xcXFxcXFxcXFxcXFx'
        'cnJycnJycnJycnJycnJeXV1dXV1dXV1dXV1dXV1xcXFxcXFxcXERMxEzETMRMxIXOREzMxEzMxEzMzEwKQEDJicHAyEB'
        'IRM/ARMhExYXNxMhBSH+16wMIzSu/tf+6AEIsg4ZqgEtpg4bHJwBBAKULbHg/W4EOvzFSnUCfP2ENIuEArcAAAEADgAA'
        'BGQEOgALAEBAJAALCAkKBAEHBgUCAwMFBwkLBQ0MBQ8AFfANAeANAZ8NAU8NAV1dXXEAPz8REgEXOREzETMRMzMzETMR'
        'MzEwIQsBIQkBIRsBIQkBAzP8/v7VAYz+hwEv5+YBMf6HAY8BiP54Ai8CC/6eAWL9+P3OAAEAEP5XBGgEOgAVAbpA/wsK'
        'EwkOERISDgMKBBYXEQoPEw4JAAVQWQAblhcBhhcBcxcBYxcBAFAXAUIXATIXASQXARQXAQYXAfIXAeAXAdAXAcIXAbQX'
        'AaQXAZYXAYIXAXQXAWAXAVIXAUIXATQXASYXARIXAQQXAWf0FwHiFwHSFwHEFwG0FwGiFwGUFwGEFwF2FwFmFwFUFwFE'
        'FwEyFwEiFwEUFwEGFwH2FwHUFwHGFwGwFwGiFwGSFwGEFwF2FwFmFwFAFwEyFwEiFwEUFwEGFwH2FwHUFwHCFwGyFwEB'
        'oBcBkBcBhBcBYBcBVBcBRBcBMBcBIBcBFBcBBBcBN/QXAcsXAbQXAXQXAQQXAUA79BcB5BcByxcBuxcBqxcBlBcBdBcB'
        'OxcBJBcBABcBAvAXAeAXAb8XAYAXAXAXAVAXATAXARAXAQAXAQdeXV1dXV1dXV1dX3FxcXFxcXFxcXFycnJycl5dXV1d'
        'XV1dXV1dX11dXV1xcXFxcXFxcXFxcXFxcXJycnJycnJycnJycnJycnJeXV1dXV1dXV1dXV1dXV1dXXFxcXFxcV9xcXFx'
        'AD8rABgvMzM/MxESARc5ETMRMzMRMzEwASInNRYzMj4BNwEhExYXPwETIQEOAQEbZUw1LDxPPyf+VAEpqig9GUGgASb+'
        'VFa5/lcNyAgmWGkEL/4FbeFf6wH/+43QoAABAFIAAAO2BDoACQBEQCcCBgcBAQMGCAQLCgYDBANQWQQPAQcAB1BZABVA'
        'CwHQCwHACwF/CwFdcXFyAD8rEQAzGD8rEQAzERIBFzkRMxEzMTAzNQEhNSEVASEVUgH9/iwDCv4GAivHAqjLyf1czQAA'
        'AQAh/lcC8gXMACMAQ0AjFh4eCwMRIgMHBCQlGggHCAf1WQgIDyEPEvVZDwAAIfVZABsAPysAGD8rERIAORgvKxESADkR'
        'EgEXOREzMxEzMTABIiY1ETQmJzU+ATURNDY7ARUjIgYVERQGBxUeARURFBY7ARUCLYahbnd5bJ2KxTpbUXNcX3BRWzr+'
        'V52OAUhycQLDBXFxAUiSmb5oaf7TX4oTBBaJXf7Tame/AAEAnP45AaIFzAADADVAIQAEBQEAAFAFAUAFATAFASAFAaAF'
        'AZAFAYAFAVAFAUAFAV1dXV1dcXFxcQAvPxESATkxMBMRIRGcAQb+OQeT+G0AAQAr/lcC/gXMACMAQ0AjDBYWBB4aHiMR'
        'BCQlCBobGhv1WRoaEgAjAPVZIxsSEfVZEgAAPysAGD8rERIAORgvKxESADkREgEXOREzMxEzMTAXMzI2NRE0Njc1LgE1'
        'ETQmKwE1MzIWFREUFhcVDgEVERQGKwErOV1PcV5bdE9dOcWKnW55eW6gh8XqZ2oBLVyKFgQTiWABLWlovpmS/rhwcgXD'
        'AnRv/riNngABAFECBARfA0gAFQAmQBQIExcWEgsLBa1ZAAuvWwAQrVkIAAAvMisrKxEAMxESATk5MTABIiYnJiMiBgc1'
        'NjMyFx4BMzI3FQ4BA1RLkUuHVkd3QXGeaYmEZC2GckB1AgQqGi8rLdVULy4YXNssJAAAAgBaAxsC2wWRAAwAGAArQBUT'
        'Bg0ABgAZGgMWrlkDAwoKEK5ZCgQAPysRADMYLysREgE5OREzETMxMAEUBiMiJjU0PgEzMhYHNCYjIgYVFBYzMjYC27uG'
        'hLxVk1iHup5dRkdfYkRDYARWgrm2hVaSU7mCRmBhRUVjYgABAIb+VgQhBDoAHAA3QBsRDQ0OAhcXGg4aHR4YDw8OGwYU'
        'UFkJAgYWABUAPz8zMysAGD8/MxESATk5ETMRMxEzETMxMCEmNSMOASMiJicjFhURIREhERQWMzI2NREhERQXAxUNAyFa'
        'TzRRFwQE/ucBGVVaWVkBGQhkLFZOMCorSP6DBeT9o5aGmJ8CQvy4gnAAAAEAVgCoBFYEqgALAEdAKAQKBggCAAAKCAMN'
        'DAcQASABQAFgAXABkAHAAQcAASABoAHAAfABBQG4/8C0DRBIAbIAGT8rXXEzERIBFzkRMxEzETMxMBMJATcJARcJAQcJ'
        'AVYBZP6gngFgAWCe/qABYJ7+oP6cAUYBZgFgnP6iAWCe/p7+oqABYv6aAAAAAQAAAGMBUgBUAFwABgACABAALwBcAAAD'
        'TQNUAAQAAQAAAAAAAAEGATMByAJnA7sERQRfBI8EvwUJBTQFWwVzBYsFowXnBhMGXgbmByoHlAf1CCgIlAj3Ca4KcAqe'
        'CuALDQtpDCQNTQ3IDiAOYA6xDusPQw+TD9MQDhBFEGYRShGPEeQSLhKaEvMTYRQWFF0UlBVkFZoWTxadFsMW2xcBFykX'
        'QhdsF+4YQxiQGOUZTRmRGgYaVBqUGxcbUBuAHAQcVByZHO4dQB2DHfkeOB6GH0kgUSCQIZchzyIlIk0ioiLaIxcjYCOl'
        'AAEAAAACGZkP6Aw5Xw889QAfCAAAAAAAyEloJgAAAADdeykr/CX8/QpvCEQAAQAIAAIAAAAAAAAGAADNAjkAAAKqAMED'
        'ywCHBHMAIwRzABsHHQAzBccAWgHnAG0CqgBmAqoAAgMdAAYErABWAjkAiwKqAFACOQCLAjkAFARzAFEEcwCBBHMARwRz'
        'AC8EcwAfBHMAPwRzAEsEcwBYBHMAQQRzAEcCqgDFAqoAwwSsAFYErABVBKwAVgTjAF4HzQB1BccAMwXHAIkFxwBUBccA'
        'iQVWAIkE4wCJBjkAVAXHAIkCOQCJBHMAHwXHAIkE4wCJBqoAiQXHAIkGOQBUBVYAiQY5AFQFxwCJBVYAOwTjABcFxwB7'
        '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'
        'JSCwBCUIsAIlQ0ghISEtLEUjIEUYILAAUCBYI2UjWSNoILBAUFghsEBZI1hlWYpgRC0sS1MjS1FaWCBFimBEGyEhWS0s'
        'S1RYIEWKYEQbISFZLSxLUyNLUVpYOBshIVktLLAAIUtUWDgbISFZLSywAkNUWLBGKxshISEhWS0ssAJDVFiwRysbISEh'
        'WS0ssAJDVFiwSCsbISEhIVktLLACQ1RYsEkrGyEhIVktLCCKCCNLU4pLUVpYIzgbISFZLSwAsAIlSbAAU1ggsEA4ERsh'
        'WS0sAUYjRmAjRmEjIBAgRophuP+AYoqxQECKcEVgaDotLCCKI0lkiiNTWDwbIVktLEtSWH0belktLLASAEsBS1RCLSyx'
        'AgBCsSMBiFGxQAGIU1pYuRAAACCIVFiyAgECQ2BCWbEkAYhRWLkgAABAiFRYsgICAkNgQrEkAYhUWLICIAJDYEIASwFL'
        'UliyAggCQ2BCWRu5QAAAgIhUWLICBAJDYEJZuUAAAIBjuAEAiFRYsgIIAkNgQlm5QAABAGO4AgCIVFiyAhACQ2BCWbEm'
        'AYhRWLlAAAIAY7gEAIhUWLICQAJDYEJZuUAABABjuAgAiFRYsgKAAkNgQllZWVlZWbEAAkNUWEAKBUAIQAlADAINAhux'
        'AQJDVFiyBUAIugEAAAkBALMMAQ0BG7GAAkNSWLIFQAi4AYCxCUAbsgVACLoBgAAJAUBZuUAAAICIVblAAAIAY7gEAIhV'
        'WlizDAANARuzDAANAVlZWUJCQkJCLSxFGGgjS1FYIyBFIGSwQFBYfFloimBZRC0ssAAWsAIlsAIlAbABIz4AsAIjPrEB'
        'AgYMsAojZUKwCyNCAbABIz8AsAIjP7EBAgYMsAYjZUKwByNCsAEWAS0ssICwAkNQsAGwAkNUW1ghIxCwIBrJG4oQ7Vkt'
        'LLBZKy0sihDlLUFVAT8AAQE5AFUBPgABATkAVQFCAUAAFAAfAUEBQAAfAB8BOwAzAToAVQE4ADMBOQBVAKQBOQD0ATkA'
        'AgEyAD0BMQBVATEAAQEvAFUBMAA9AS8AVQEsASkA/wAfASkAAQEqAFUBKAA9AScAVQEnAAEBKgBVASYAPQElAFUBJQAB'
        'ASoAVQEjASIA/wAfASIAAQEqAFUBKwA9ASoAVQBQAQcAAQAvAQcAAQCvAQRAUAHQ/QG//QEQ/QFv+wFA+wGA9ZD1oPUD'
        '8fA1Hy/wn/ACX+8BL+9f72/vn+/f7wXm5CAf5eQ9H+LgJx/h4D0f3z3dVd49A1UA3TDdAt0BA1UvQQsBHgABABABHgAg'
        'AR4AQAEeAAP/wAEeQCgZHEbcA/8fANsB2gQ8H9TSHB/T0iYfYNGQ0cDRA2DRkNGw0cDR4NEFuP/As9EZHUa4/8C00QoN'
        'Rg+4ARZADwG/viYfQLspQUZAuyInRrgBIUAmtj0fALgBb7gBuLcKHwC3AQC3ILdAt2C3cLcFQLdgt5C30LfwtwW4ASBA'
        'DUg9HwC1YLUCoLXQtQK4/8BADrULDkYPsl+yArEDPB8vQQsBGQA/ARkATwEZAAMAjwEZAAEAQAEZQCgmKUYfry+vP6+f'
        'rwQPrwFArw4WRgCtcK2ArQPgrfCtAquqNR+qUCYfuQEbARqyPB8AuAEatgEPqQEPqAG8ARcBEwA8AB8BFUB+UDwfnpsn'
        'H52bJx+cmycfgJsBmEYoH5+Xr5cClkY1Hw+UH5QCk5AmH5KRJh8Pjx+Pb49/j4+PBY6MJh9PjQEPjAFAjAsPRg+JH4kC'
        'hoUPH1+FATaCRoICdlAmH3VQJh90UCYfc1AmHylwARtwAQNwAfRwAdZw5nACaHABWXABuP/wQH1wCg1Gb25IH25GMh8a'
        'ARhVGTMYVQczA1UGA/8fYVAmH2BfMh9fUCYfXlpIH1xGJx9bWngfWkYxHxMyElUFAQNVBDIDVW8DAQ8DPwNPA28DfwMF'
        'X1MBQFMoLEZAUx4iRkBTExhGa1J7UotSA1FPHB9QTxwfGU8pTwJZT2lPArgBEkAtRiUfSUYZH0hGIR9HRjUf+EYBmEYB'
        'HEgbVRYyFVURAQ9VEDIPVQIBAFUBAP8fuAERshsJH7gBEEAtGwkfHw8/D18Pfw8EDw8vD08Pbw+PD98P/w8HPw9/D+8P'
        'A28AAU8AAYAWAQUBuAGQsVRTKytLuAf/UkuwB1BbsAGIsCVTsAGIsEBRWrAGiLAAVVpbWLEBAY5ZhY2NAEIdS7AyU1iw'
        'YB1ZS7BkU1iwQB1ZS7CAU1iwEB2xFgBCWXN0c3R1KysrKysrKysBc3QrKysrAHN0KytzKysrc3N1KysrASsrKwArKysr'
        'KysrKwErKytzc3NzdHR0ACsrKysBc3MrcwArc3MrcysrcwErcysAcysrKysrc3NzKwErKwBzdCtzdCtzdCtzAStzdCsA'
        'c3R1K3N0KysrASsAcysrc3QBKysAK3MrK3N1K3MrKwErKwArK3N0AXMrAHNzc3NzcwFzc3MAKysrKysrKysrKysrcysr'
        'KysrKxgFzAXMAH0FgQAVAHkFgQAVAAAAAAAAAAAAAAAAAAAEOgAUAHcAAP/sAAAAAP/sAAAAAP/sAAD+V//3AAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAgAAAAAAAEZASUA9QDrAAAAAAAAAAAAAADBANMAugCwAM8AAAAAAAAAAAAAAAABJwEpAQYAAAESAOQA9ADGAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAARkBHwFMAAAAAADfANEAxQC1AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAECAKkB/QDYARkA'
        'gAC3Af0AAAAAAT8A2wFdASUAqgCAAHUAjQH8AXkBIQCgARAAAAAAATEBGQEOAQQAAAAAAAAAAAAAAAAAAAAAAAABPQH/'
        'AOABBgCUAOAAlAFEAOAFcwMZAAAA2ALFAJwDgQLNAMsA9ABOAo0AAAD/ANcAzAEwAUUAcwC0AKYAAAAAAHMAgACNAAAA'
        'AAAAAAAAAAAAAwAAogCYAIMAjQAAAAAAAAAABa7+vAWB/TAAEf/2ALYAvADGAAAAfwCKAGAAAAAAAAAAAADwAe4BkAAA'
        'AhkBCAEVAAAAAAAAAL4AAAAAAAAAAAdIA2oCtgIC/ZMAAACRAGcAkQBhAdkAAAKNA0EAAAAAAAAAAAAAAAAAAACq/m/+'
        'aAEFAJMAmADiAVEAjwC+AK7+uf6kAF4ArwLVAFUA8gCmBBUGAQAAA+EAEAL6AA/+1AHq//MAuAAAAAADYwAL/Q//9QAA'
        'AAAAAAaBBHcAFQTZAAD/7P/F/n8AdQDNAPIBAgDVARkAAAAHAFoAAwABBAkAAACsAAAAAwABBAkAAQAeAKwAAwABBAkA'
        'AgAIAMoAAwABBAkAAwA0ANIAAwABBAkABAAoAQYAAwABBAkABQAaAS4AAwABBAkABgAmAUgARABpAGcAaQB0AGkAegBl'
        'AGQAIABkAGEAdABhACAAYwBvAHAAeQByAGkAZwBoAHQAIAAoAGMAKQAgADIAMAAxADAAIABHAG8AbwBnAGwAZQAgAEMA'
        'bwByAHAAbwByAGEAdABpAG8AbgAuAAoAQwBvAHAAeQByAGkAZwBoAHQAIAAoAGMAKQAgADIAMAAxADIAIABSAGUAZAAg'
        'AEgAYQB0ACwAIABJAG4AYwAuAEwAaQBiAGUAcgBhAHQAaQBvAG4AIABTAGEAbgBzAEIAbwBsAGQAQQBzAGMAZQBuAGQA'
        'ZQByACAALQAgAEwAaQBiAGUAcgBhAHQAaQBvAG4AIABTAGEAbgBzAEwAaQBiAGUAcgBhAHQAaQBvAG4AIABTAGEAbgBz'
        'ACAAQgBvAGwAZABWAGUAcgBzAGkAbwBuACAAMgAuADEALgA1AEwAaQBiAGUAcgBhAHQAaQBvAG4AUwBhAG4AcwAtAEIA'
        'bwBsAGQAAwAAAAAAAP/+ANcAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMACAACAAoAA///AAMAAQAAAAwAAAAAAAAAAgAB'
        'AAAAYgABAAAAAQAAAAoAOgBIAARERkxUABpjeXJsACRncmVrACRsYXRuACQABAAAAAD//wAAAAQAAAAA//8AAQAAAAFr'
        'ZXJuAAgAAAABAAAAAQAEAAIACAABAAgAAQAoAAQAAAAPAEoAVABaAHwAigCkALYAxAEKAUABdgG0AcgBvgHIAAEADwAB'
        'ABIAIgAnAC0AMQAzADUANwA4ADoAUwBXAFgAWgACACL/tAA6/9sAAQAS/48ACAAB/7QANf9oADf/aAA4/48AOv9EAFf/'
        'tABY/9sAWv+0AAMADf8dAA//HQAi/48ABgAB/9sANf9oADf/aAA4/48AOv9EAFr/tAAEAAH/2wAN/vgAD/74ACL/aAAD'
        'ADf/2wA4/9sAOv+0ABEADf8dAA7/jwAP/x0AG/8dABz/HQAi/2gAMP/bAEL/aABE/2gARv9oAEr/2wBQ/2gAU/+PAFT/'
        'aABW/2gAWP9oAFr/aAANAA3/RAAO/48AD/9EABv/jwAc/48AIv9oAEL/jwBG/48ASv/bAFD/aABT/48AVv+0AFr/tAAN'
        'AA3/jwAO/9cAD/+PABv/2wAc/9sAIv+PAEL/tABG/9sASv/uAFD/2wBT/9sAVv/bAFr/2wAPAAH/2wAN/x0ADv+PAA//'
        'HQAb/2gAHP9oACL/RABC/48ARv+PAEr/tABQ/2gAUf+PAFL/aABW/48AV/+PAAIADf+PAA//jwACAA3/tAAP/7QAAgAN'
        '/2gAD/9oAAAAAQAAAAoARABGAAdERkxUACxib3BvADZjb3B0ADZjeXJsADZncmVrADZoZWJyADZsYXRuADYABAAAAAD/'
        '/wAAAAAAAAAAAAA='),
    'LibSansI': (
        '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'
        'BcwADAB6QE04AkgCAjcBRwFXAQM4C0gLWAsDOQJJAgI6AUoBWgEDAgcDBgYFBQMEAQsADAwLBAMNCQoKDj8OTw5fDgMC'
        'AQcLBAkKDwYFAAMEBAwAFQA/MjIvMz8zPzMXOQFdETMRMxIXOREzETMRMzMRMxESOTkxMABdXV0BXV0hAQcDIwEzAzcB'
        'MwkBAtH+9KhIswEgtLPMAWne/e4BUAH2fP6GBcz8a74BRf4v/ZcAAQAhAAAB9QXMAAMANEAiAwAABAVgBQGABdAFAk8F'
        'AR8FLwWfBa8FvwX/BQYBAAMAFQA/Mj8BXXFxchESOREzMTAzATMBIQEgtP7fBcz6NAABACIAAAZLBE0ALQFgQPsSCQ8K'
        'Dw4OCgssGQMDLQAmHx8ACwMuL5IvAQGALwFUL3QvAiAvARQvAVQvdC+EL6QvtC/UL/QvBysvOy8CAC8QLwJn9C8B4C8B'
        '1C8BsC8BRC90L5QvpC8EEC8BBC8B1C/0LwK7LwF0LwFbLwEwLwEkLwEALwH0LwHQLwHELwGrLwF0LwFgLwE0L1QvAgsv'
        'ATf0LwHbLwGULwFrLwFQLwEkL0QvAgsvAVQvhC+0L9Qv5C/0LwYLLysvAvsvAeQvAZsvyy8CdC8BWy8BNC8BEC8gLwIC'
        'AC8BBwMcKVBZHBAZEgksASQhDBIHFgAWBlBZFhAODyIjIwoLCy0AFQA/MjIvMzIvMz8/KxESABc5ETMYPysBX15dX11d'
        'XV1dXV1xcXJycnJycnJeXV1dXV1dXV1xcXFxcXFxcnJycnJycl5dXV1xcXFxX3EREhc5ETMRMzMRMzMRMzMRMxESOTkx'
        'MCETNjU0JiMiBgcDIxM2NzMUBgczPgEzMhYXPgEzMhYVFAcDIxM2NTQmIyIGBwMClHwZTFZ0rRt2s6YUE6oVBwNJk2Z5'
        'jg5ToWiHkRV/snwZTFZ0rBx2Anp9MUtPxqD9pANTX4gLhSlyWndxgmaSikBk/XMCen0xS0/DoP2hAAABACIAAAQWBE0A'
        'GwBHQCUDGBEIDgoODQ0JChgKHRwIARoLEQUVABUFUFkVEA4NDxsKCQAVAD8yMjI/Mz8rERIAFzkREgE5OREzMxEzERI5'
        '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'
        'DBcC5v3KGQMQGP0aAm0ZiQMmi4n82osAAAEAFf5XA0EFzAAtAGRANigDGRAsEB0DCwUuFBQvIScsGRoVHR0MCAMLLQwL'
        '9VkQDwxAEj5IDAwULC0s9VktGxQV9VkUAAA/KwAYPysREgA5GC8rOTkrERIAOTkRORESOTkSOTkRATMREhc5ETMRMzEw'
        'ASImNTQ3EzY1NCYnNz4BNxM+ATsBByMiBgcDDgEHFR4BFRQHAw4BBxUUFjsBBwFub4MKOAldVRlugBdGHJeOhxk/WWEY'
        'RRODXUVRBj0FBwFFTTAZ/leFdT43AR8sIVNJBH8Ec3UBao+WgV55/pxfhxYCEWROGyD+wRhREQY4RYEAAQDV/joBewXM'
        'AAMAFLcDAAAEBQEAAAAvPxESATkRMzEwExEzEdWm/joHkvhuAAH/Yf5XAo0FzAAtAGRANhAZBiMLHSMZBBQvFC4nISwd'
        'LSz1WRoZHRUdCxAPFAwLDPVZAwgtC0ASPkgLCxUtABQV9VkUGwA/KwAYPxI5LysSOTkrERIAOTkSORESOTkrERIAOTkR'
        'ATMREhc5ETMRMzEwATIWFRQHAwYVFBYXBw4BBwMOASsBNzMyNjcTPgE3NS4BNTQ3Ez4BNzU0JisBNwE0b4MKOAldVRlu'
        'gBdGHJeOhxk/WWEYRRODXUVRBj0FBwFFTTAZBcyFdT43/uErIlNJBH8Ec3X+lo+WgV55AWRfhxYCEWROHB8BPxhREQY4'
        'RYEAAQB6AikEbgMnABUAZkAJEggXFgAQrVkIuP/AtCY8SAgAuP/AsxccSAC4/8BALAkUSABAEkApPEgSCwsFrVkfC08L'
        'nwsDbwt/C58LrwvPC+8L/wsHC0AJDUgLAC8rXXErABgQxCsa3SsrxCsrERIBOTkxMAEiJicmIyIGBzU2MzIXHgEzMjcV'
        'DgEDakWRSYFYQ3RBb5hmhZNXJIJyPHMCKSwaLSkvj1QuMxRclSomAAACAMQDXAMCBZYACwAXADFAGQwAEgYABhkYAxWv'
        'WQADARcDAwkJD69ZCQcAPysAGBDEX15dKxESATk5ETMRMzEwARQGIyImNTQ2MzIWBzQmIyIGFRQWMzI2AwKpdnapp3h4'
        'p21nS0tnaUlKaAR5d6aodXWopndMaGpKSmppAAAB///+VwRFBDoAIAGeQBgZCg0NCwwMIgAfBQMDAiAgAAIBAQAAISK4'
        '/wBAEHmASOIiAdAiAcIiAbQiASK4/wBAGXB0SDIiQiJSIgMkIgECIhIiAmrgIvAiAiK4/0CzZGdIIrj/gEAPYGNIQiJS'
        'IgIwIgEiIgEiuP+AQAlYW0jCItIiAiK4/4BAD1JVSHIiAVQiZCICQiIBIrj/gEAySk1I5iL2IgLUIgHGIgGyIgGEIpQi'
        'pCIDViJmInYiA0QiATYiARIiIiICBCIBOvIiASK4/4BAMTU4SJYipiICdCKEIgJiIgEBMCJAIlAiAwQiFCIkIgPwIgHU'
        'IuQiAsAiAbQiAaAiASK4/8BAPR0jSC8iARAiAQQiAeQi9CICwCIBApAioCKwIgN/IgFgIgFPIgEAIgEKAxEHHAdQWRYc'
        'Fh8ZAQsLAQ8gABsAPzI/My8ROTk/MysRADMBX15dXV1dXV9dXXFxcStxcXFxcXJyX3JycityXl1dXV1dXV1dXV0rcXFx'
        'K3ErcnJyKytyXl1dXStdXV1dKxEzETMRMxEzERIXORESOREzMxEzMzEwAwEzAwYVFDMyNjcTMwMGFRQzMjcHBiMiJjUj'
        'BiMiJicDAQEltYYLonClHHa0nQk5DCwWSDNKPgKBtD5aF17+VwXj/VJAJbC+owJi/NkpKUgIgRRhXL0qJf4cAAEArADh'
        'BD0EcwALACVAEgYIBAoCAAABCgcIBQ0MAAcBBwAZL3EREgEXOREzETMRMzEwEwkBNwkBFwkBBwkBrAFi/qBoAV4BXmn+'
        'ogFgZv6f/pwBSgFiAWBn/p8BX2n+pP6gaQFh/p0AAAABAAAAYwFSAFQAZQAGAAIAEAAvAFwAAAN4A6oABAABAAAAAAAA'
        'ACoAUAD0AaICJgK8AtUC/AMiA2QDngPFA+ID+gQRBFcEigThBWIFqwYKBnEGpQcZB4EHqQfgCBMISQh8CN4JtQn3ClQK'
        'qgrmCyQLYQu7DAIMLAxvDLgM2Q2aDdYOHw5hDsAPFQ+GD7AP9BAeEOwRMRFlEZkRxBHdEgYSNRJNEnAS8hNpE7cUGhR7'
        'FMMVSBWXFdIWEhZuFpYXjBfdGCYYhxj1GTYZmRnhGi4aZxsoG3gbxxyaHRMdKh2jHfseOh89H3EAAQAAAAIZmUAjR0Jf'
        'Dzz1AB8IAAAAAADIToG1AAAAAN17LJL6sP2TCuMIHQACAAgAAgAAAAAAAAYAAAACOQAAAjkATQLXALsEcwAnBHP/9Acd'
        'AJIFVgAhAYcAygKqAGACqv85Ax0AeASsAIICOQAlAqoAaQI5AFACOf+MBHMAWQRzADUEc//0BHMAMARzAA0EcwAuBHMA'
        'cwRzANQEcwA2BHMARgI5AFECOQAmBKwAgwSsAIIErACDBHMAnwgfAMIFVv+bBVYAPwXHAHEFxwA/BVYAPwTjAD8GOQBl'
        'BccAPwI5AFEEAP/7BVYAPwRzAD8GqgA/BccAPwY5AG8FVgA/BjkAZQXHAD8FVgA6BOMAuAXHAJkFVgCxB40AsQVW/9kF'
        'VgDVBOP/2AI5/9kCOQCSAjn/VwPBACgEc/9gAqoAggRzAC4EcwAdBAAAQwRzAEUEcwBFAjkARQRzAAQEcwAiAccAIQHH'
        '/xsEAAAiAccAIQaqACIEcwAiBHMAQwRz/80EcwBFAqoAIgQAAAUCOQBdBHMAVgQAAHAFxwBmBAD/rgQA/4wEAP/0AqwA'
        'FQIUANUCrP9hBKwAegMzAMQEnP//BKwArAABAAAHPv5OAEMKqvqw+lYK4wBkABUAAAAAAAAAAAAAAAAAYwADBKEBkAAF'
        'AAAFmgUzAB4BGwWaBTMAWgPRAGYCEggFAgsGBAICAgkCBAAAAAMAAAAAAAAAAAAAAAAxQVNDAAEAIADXBdP+VwEzBz4B'
        'sgAAAAEAAAAABDoFgQAAACAALAAAAAIAAAADAAAAFAADAAEAAAAUAAQAOAAAAAoACAACAAIAfgCwALUA1///AAAAIACw'
        'ALUA1////+H/sP+s/4sAAQAAAAAAAAAAAABAR1taWVhVVFNSUVBPTk1MS0pJSEdGRURDQkFAPz49PDs6OTg3NjUxMC8u'
        'LSwoJyYlJCMiIR8YFBEQDw4NCwoJCAcGBQQDAgEALCCwAWBFsAMlIBFGYSNFI2FILSwgRRhoRC0sRSNGYLAgYSCwRmCw'
        'BCYjSEgtLEUjRiNhsCBgILAmYbAgYbAEJiNISC0sRSNGYLBAYSCwZmCwBCYjSEgtLEUjRiNhsEBgILAmYbBAYbAEJiNI'
        'SC0sARAgPAA8LSwgRSMgsM1EIyC4AVpRWCMgsI1EI1kgsO1RWCMgsE1EI1kgsAQmUVgjILANRCNZISEtLCAgRRhoRCCw'
        'AWAgRbBGdmiKRWBELSwBsQsKQyNDZQotLACxCgtDI0MLLSwAsCgjcLEBKD4BsCgjcLECKEU6sQIACA0tLCBFsAMlRWFk'
        'sFBRWEVEGyEhWS0sSbAOI0QtLCBFsABDYEQtLAGwBkOwB0NlCi0sIGmwQGGwAIsgsSzAioy4EABiYCsMZCNkYVxYsANh'
        'WS0sigNFioqHsBErsCkjRLApeuQYLSxFZbAsI0RFsCsjRC0sS1JYRUQbISFZLSxLUVhFRBshIVktLAGwBSUQIyCK9QCw'
        'AWAj7ewtLAGwBSUQIyCK9QCwAWEj7ewtLAGwBiUQ9QDt7C0ssAJDsAFSWCEhISEhG0YjRmCKikYjIEaKYIphuP+AYiMg'
        'ECOKsQwMinBFYCCwAFBYsAFhuP+6ixuwRoxZsBBgaAE6WS0sIEWwAyVGUkuwE1FbWLACJUYgaGGwAyWwAyU/IyE4GyER'
        'WS0sIEWwAyVGUFiwAiVGIGhhsAMlsAMlPyMhOBshEVktLACwB0OwBkMLLSwhIQxkI2SLuEAAYi0sIbCAUVgMZCNki7gg'
        'AGIbsgBALytZsAJgLSwhsMBRWAxkI2SLuBVVYhuyAIAvK1mwAmAtLAxkI2SLuEAAYmAjIS0sS1NYirAEJUlkI0VpsECL'
        'YbCAYrAgYWqwDiNEIxCwDvYbISOKEhEgOS9ZLSxLU1ggsAMlSWRpILAFJrAGJUlkI2GwgGKwIGFqsA4jRLAEJhCwDvaK'
        'ELAOI0SwDvawDiNEsA7tG4qwBCYREiA5IyA5Ly9ZLSxFI0VgI0VgI0VgI3ZoGLCAYiAtLLBIKy0sIEWwAFRYsEBEIEWw'
        'QGFEGyEhWS0sRbEwL0UjRWFgsAFgaUQtLEtRWLAvI3CwFCNCGyEhWS0sS1FYILADJUVpU1hEGyEhWRshIVktLEWwFEOw'
        'AGBjsAFgaUQtLLAvRUQtLEUjIEWKYEQtLEUjRWBELSxLI1FYuQAz/+CxNCAbszMANABZREQtLLAWQ1iwAyZFilhkZrAf'
        'YBtksCBgZiBYGyGwQFmwAWFZI1hlWbApI0QjELAp4BshISEhIVktLLACQ1RYS1MjS1FaWDgbISFZGyEhISFZLSywFkNY'
        'sAQlRWSwIGBmIFgbIbBAWbABYSNYG2VZsCkjRLAFJbAIJQggWAIbA1mwBCUQsAUlIEawBCUjQjywBCWwByUIsAclELAG'
        'JSBGsAQlsAFgI0I8IFgBGwBZsAQlELAFJbAp4LApIEVlRLAHJRCwBiWwKeCwBSWwCCUIIFgCGwNZsAUlsAMlQ0iwBCWw'
        'ByUIsAYlsAMlsAFgQ0gbIVkhISEhISEhLSwCsAQlICBGsAQlI0KwBSUIsAMlRUghISEhLSwCsAMlILAEJQiwAiVDSCEh'
        'IS0sRSMgRRggsABQIFgjZSNZI2ggsEBQWCGwQFkjWGVZimBELSxLUyNLUVpYIEWKYEQbISFZLSxLVFggRYpgRBshIVkt'
        'LEtTI0tRWlg4GyEhWS0ssAAhS1RYOBshIVktLLACQ1RYsEYrGyEhISFZLSywAkNUWLBHKxshISFZLSywAkNUWLBIKxsh'
        'ISEhWS0ssAJDVFiwSSsbISEhWS0sIIoII0tTiktRWlgjOBshIVktLACwAiVJsABTWCCwQDgRGyFZLSwBRiNGYCNGYSMg'
        'ECBGimG4/4BiirFAQIpwRWBoOi0sIIojSWSKI1NYPBshWS0sS1JYfRt6WS0ssBIASwFLVEItLLECAEKxIwGIUbFAAYhT'
        'Wli5EAAAIIhUWLICAQJDYEJZsSQBiFFYuSAAAECIVFiyAgICQ2BCsSQBiFRYsgIgAkNgQgBLAUtSWLICCAJDYEJZG7lA'
        'AACAiFRYsgIEAkNgQlm5QAAAgGO4AQCIVFiyAggCQ2BCWblAAAEAY7gCAIhUWLICEAJDYEJZsSYBiFFYuUAAAgBjuAQA'
        'iFRYsgJAAkNgQlm5QAAEAGO4CACIVFiyAoACQ2BCWVlZWVlZsQACQ1RYQAoFQAhACUAMAg0CG7EBAkNUWLIFQAi6AQAA'
        'CQEAswwBDQEbsYACQ1JYsgVACLgBgLEJQBuyBUAIugGAAAkBQFm5QAAAgIhVuUAAAgBjuAQAiFVaWLMMAA0BG7MMAA0B'
        'WVlZQkJCQkItLEUYaCNLUVgjIEUgZLBAUFh8WWiKYFlELSywABawAiWwAiUBsAEjPgCwAiM+sQECBgywCiNlQrALI0IB'
        'sAEjPwCwAiM/sQECBgywBiNlQrAHI0KwARYBLSywgLACQ1CwAbACQ1RbWCEjELAgGskbihDtWS0ssFkrLSyKEOUtQTgA'
        'CQE/AAEBOQBVAT4AAQE5AFUBQgFAABQAHwFBAUAAHwAfATsAMwE6AFUBOAAzATkAVQCAAQ8AAQDwAQ8AAQBPAQ8ArwEP'
        'AAIA7wEPAAEAgAEPAAEAPwEPAAEAAAEPAAEAQAEHAAEAHwEHAAEAnwEEQFIBwP0Br/0BAP0BCk/7ASD7AfVQKB/yRigf'
        '8EYrH1/vf+8CD+9P71/vj++v7wUL5eQeH+PiRh8P4gFA4kYWH+HgRh+/4M/g3+ADQOAzNkbgRhgfvgEcAD0BGwBVARoA'
        'PQEZQFhV7u3/H+0C6FXsSOtV6jIAVeno6FXoAQBV50gAVeYA/x/dPd9V3wEDVd49A1XcA/8fD9UBD9X/1QL/1QGf1AHT'
        '0jwfv8IBwVAmH2C+cL6AvgNAuGC4cLgDuP/AQFm4EjJGD7c/twIPsz+z77MDCWCwcLACkLCgsLCwA4CtkK0CoK2wrQJ/'
        'qwGgqrCqAi+pb6kCD6lPqZ+p36kEC6CfKx9AnwkRRgChEKECOkChUKECsKHAodChA7j/wEAgoSAkRp6bJB+dmyQfnJsk'
        'H1CbAZhaSB+XliQf0JbglgK4/8C0lg0RRg+4AQpAVgEPlX+VAl+Ub5TPlN+UBA+UH5R/lI+U/5QFk5I8H0CSFx1GQJIJ'
        'DEYPkQFfkZ+Rr5G/ke+R/5EGQJEcJUagj7CPAsCP0I/gjwOOjUYfMI1AjQKAjQFvvgEMAAEA4AEMAAH/wAEMQJoOEUYg'
        'ijCKAoWERh+Bbf8fgAP/H89133XvdQPvdQF0cz8fc1AmH3JGNR9xRjUfQHAmLEYgcDBwAm9GNR9uRjUfGgEYVRkzGFUH'
        'MwNVBgP/H6dtASltAWwD/x9hXy8fYF9CH19QJh9eWjIfXEYxH1taSB9aRjEfEzISVQUBA1UEMgNVbwMBDwM/A08DbwN/'
        'AwWWWQGwUsBS0FIDuP/As1ItNEa4/8BAm1IgJEbvUf9RAkBRNThGQFElKEbPUAEgTikvRghOHyJGCU0ZTQJITVhN2E3o'
        'TfhNBZhNARhMJC1GGEwdIEaYTKhMAktGNx9JRiAfSEY1H0dGNR+vRgHfRu9GAoBGARYyFVURAQ9VEDIPVQIBAFUBAAEf'
        'Hw8/D18Pfw8EDw8vD08Pbw+PD98P/w8HPw9/D+8PA28AAU8AAYAWAQUBuAGQsVRTKytLuAf/UkuwB1BbsAGIsCVTsAGI'
        'sEBRWrAGiLAAVVpbWLEBAY5ZhY2NAEIdS7AyU1iwYB1ZS7BkU1iwQB1ZS7CAU1iwEB2xFgBCWXN0c3R1KysrKysBc3R1'
        'KysrACtzKytzdHUrK3QrK3MrK3MBcwBzdSsrKwErKysAKysrKytzcysrKysBKyt0KwArKysrc3QrKwErcytzdABzdCtz'
        'dCtzdCsrK3N0c3MBK3MrKwBzKysrK3N1XnMBKysAXnN0AXNzAHN0c3Rec3MrcwFzACtzAStzAHN0dSsrKysrKysrKysr'
        'KysrASsrdCsrXnMrACtec3QBKysAK3NzXnNzcwFzc3MAc3Nzc3R0dSsrKysrKxheAAXMBd4AfQWBABUAeQWBABUAAAAA'
        'AAAAAAAAAAAAAAQ6ABQAdwAA/+wAAAAA/+wAAAAA/+wAAP5XAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAAAAAAALQAvQCvAKAA1gCxAJ0AqACW'
        'AIcAiAB+AKAArAAAAAAAAAAABcwBIAC/AMMAqwAAALwAmwCNAKoAAAAAAAAAAAAAAAAAAAAAAAAAAAWBARIAuQCvAHIA'
        'sgCpAJQAmQCAAAAAAAAAAAAAAAAAAAAAAAAAAAAFgQESAGoAkQCuALQAWwBMAHQAZAHZAYEAagC4AKwAlQCKAWUA9gEI'
        'ASIBMwDtAOkAwwClAIgA2wDPAMkAwwA5ACsAoAAAAAAAAAAAAAAAAAHhAckAkgCoAGsAkgC3AGsAmwAAAAAC8gCKApIA'
        'bgLWA4EATACJAKAAXgAAANcAAAAAAKQBWwBeAIIAdAAAAAAAXgBlAG8AAAAAAAAAAAAAAAAAAACIAI0ApQB6AIAAAAAA'
        'AAAAAP7lBYH/8wAN/LMAgwCIAI0AlgBpAHEFzAAP/B7/8gA0BOYADf7UAL8DHwCpAAAAtQAAAAAAgQAAAAAAAAAAB0gD'
        'agK2AgL9kwAAAJEAZwCRAGEB2QAAAo0DQQAAAVMBRQGXAOMAeQTRA9EHJ/7vAE4AiABXAGQArQC9ALQDXAAOAHj/8gCY'
        'AF8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABoEEaAAUBMsAAP/s/9P+fwCDAN0A'
        'qgC6AKAAzwAAAAcAWgADAAEECQAAAKwAAAADAAEECQABAB4ArAADAAEECQACAAwAygADAAEECQADADQA1gADAAEECQAE'
        'ACwBCgADAAEECQAFABoBNgADAAEECQAGACoBUABEAGkAZwBpAHQAaQB6AGUAZAAgAGQAYQB0AGEAIABjAG8AcAB5AHIA'
        'aQBnAGgAdAAgACgAYwApACAAMgAwADEAMAAgAEcAbwBvAGcAbABlACAAQwBvAHIAcABvAHIAYQB0AGkAbwBuAC4ACgBD'
        'AG8AcAB5AHIAaQBnAGgAdAAgACgAYwApACAAMgAwADEAMgAgAFIAZQBkACAASABhAHQALAAgAEkAbgBjAC4ATABpAGIA'
        'ZQByAGEAdABpAG8AbgAgAFMAYQBuAHMASQB0AGEAbABpAGMAQQBzAGMAZQBuAGQAZQByACAALQAgAEwAaQBiAGUAcgBh'
        'AHQAaQBvAG4AIABTAGEAbgBzAEwAaQBiAGUAcgBhAHQAaQBvAG4AIABTAGEAbgBzACAASQB0AGEAbABpAGMAVgBlAHIA'
        'cwBpAG8AbgAgADIALgAxAC4ANQBMAGkAYgBlAHIAYQB0AGkAbwBuAFMAYQBuAHMALQBJAHQAYQBsAGkAYwADAAD/9AAA'
        '/70AlgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAwAIAAIAEQAB//8AAwABAAAADAAAAAAAAAACAAEAAABiAAEAAAABAAAA'
        'CgA6AEgABERGTFQAGmN5cmwAJGdyZWsAJGxhdG4AJAAEAAAAAP//AAAABAAAAAD//wABAAAAAWtlcm4ACAAAAAEAAAAB'
        'AAQAAgAIAAEACAABACgABAAAAA8ASgBUAFoAfACOAKgAugDMARIBSAFmAaQBvAGyAbwAAQAPAAEAEgAiACcALQAxADMA'
        'NQA3ADgAOgBTAFcAWABaAAIAIv+0ADr/2wABABL/aAAIAAH/tAA1/2gAN/+PADj/2wA6/2gAV//bAFj/2wBa/+4ABAAB'
        '/9sADf74AA/++AAi/2gABgAB/9sANf9oADf/jwA4/7QAOv9EAFr/2wAEAAH/tAAN/vgAD/74ACL/aAAEADX/2wA3/9sA'
        'OP/bADr/tAARAA3/RAAO/0QAD/9EABv/aAAc/2gAIv9oADD/2wBC/0QARP9EAEb/RABK/+4AUP9EAFP/aABU/0QAVv9o'
        'AFj/aABa/2gADQAN/2gADv+0AA//aAAb/9sAHP/bACL/jwBC/7QARv+0AEr/2wBQ/7QAU//bAFb/2wBa/9sABwAN/7QA'
        'Dv/bAA//tAAi/9sAQv/bAEb/2wBK/+4ADwAB/9sADf9EAA7/aAAP/0QAG/+0ABz/tAAi/48AQv9oAEb/jwBK/9sAUP+P'
        'AFH/jwBS/48AVv+0AFf/tAADAA3/jwAO/9sAD/+0AAIADf+PAA//jwACAA3/aAAP/2gAAAABAAAACgBEAEYAB0RGTFQA'
        'LGJvcG8ANmNvcHQANmN5cmwANmdyZWsANmhlYnIANmxhdG4ANgAEAAAAAP//AAAAAAAAAAAAAA=='),
    'Cursed': (
        'AAEAAAANAIAAAwBQRkZUTYHzFmkAADkkAAAAHEdERUYAJwChAAA4/AAAACZPUy8yWZsEhwAAAVgAAABgY21hcIkH4MkA'
        'AAOYAAAB7mdhc3D//wADAAA49AAAAAhnbHlmfGzMcQAABoAAAC4QaGVhZA9pAvgAAADcAAAANmhoZWEGMgJlAAABFAAA'
        'ACRobXR4II0iHAAAAbgAAAHgbG9jYcDgzRQAAAWIAAAA+G1heHAAyQBLAAABOAAAACBuYW1liIv1JAAANJAAAANCcG9z'
        'dIOeh/4AADfUAAABHQABAAAAAQAA5l3Ev18PPPUACwQAAAAAANbsp7cAAAAA1u0Xcv/5/24CdwNkAAAACAACAAAAAAAA'
        'AAEAAANk/28AXAKA//kAAAJ3AAEAAAAAAAAAAAAAAAAAAAB1AAEAAAB7AEgADAAAAAAAAgAAAAEAAQAAAEAAAAAAAAAA'
        'BAJ/AZAABQAAApoCzAAAAI8CmgLMAAAB6gAyAQgAAAIABQMAAAAAAACAAAAjAAAACgAAAAAAAAAAUGZFZACAACAhIgMz'
        '/zMAXANkAJEAAAABAAAAAAL6AvoAAAAgAAECAAAzAAAAAAFVAAACgAAAAoAA8gKAAKMCgP//AoAAKAKAABICgAAwAoAA'
        '+AKAAH4CgAB+AoAAdgKAAAICgACwAoAAHQKAANQCgAAzAoAAKAKAAcQCgAAoAoAAcgKAACkCgAAoAoAAKAKAAHICgAAo'
        'AoAAKAKAANQCgACwAoAArgKAACsCgACuAoAAJwKAACwCgAAoAoAAKgKAACgCgAAqAoAAKAKAACgCgAAoAoAAKQKAADUC'
        'gAAsAoAAJwKAACcCgAAoAoAAKAKAACgCgAAoAoAAKAKAACgCgAAoAoAAGgKAACgCgAAoAoAAKAKAAC8CgAAnAoAAGAKA'
        'AH4CgAAzAoAAfgKAAD4CgAAPAoAAtgKAACgCgAAqAoAAKAKAACoCgAAoAoAAKAKAACgCgAApAoAANQKAACwCgAAnAoAA'
        'JwKAACgCgAAoAoAAKAKAACgCgAAoAoAAKAKAACgCgAAaAoAAKAKAACgCgAAoAoAALwKAACcCgAAYAoD/+QKAAQ0CgAB+'
        'AoAANQKAABECgAArAoAAPgKAAK4CgAD4AoAA+AKAAKMCgACjAoAAbAKAAB0CgAAdAoAAHAKAAK4CgADyAoAAGAKAAD0C'
        'gAAYAikAKAKAALYAPQAnACgAOgAoAB0AAAADAAAAAwAAABwAAQAAAAAA6AADAAEAAAAcAAQAzAAAAC4AIAAEAA4AfgCh'
        'AKkAqwCuALAAtAC7AL8AxwDXAOcA9wLGIBQgGSAdICIgJiA6IKwhIv//AAAAIAChAKkAqwCuALAAtAC7AL8AxwDXAOcA'
        '9wLGIBMgGCAcICIgJiA5IKwhIv///+P/zv/H/8b/xP/D/8D/uv+3/7D/of+S/4P9nuBY4E7gTOBI4D0AAN+230sAAQAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAAAAAAAZQBuAAABBgAAAQAAAAAAAAABAgAAAAIA'
        'AAAAAAAAAAAAAAAAAAABAAADBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyAhIiMkJSYnKCkqKywtLi8wMTIzNDU2'
        'Nzg5Ojs8PT4/QEFCQ0RFRkdISUpLTE1OT1BRUlNUVVZXWFlaW1xdXl9gYQAAAHcAAAAAAAAAAAAAeQAAAAAAAAAAAAAA'
        'AAAAAAAAAABzAAAAagAAcnBtdAAAAAAAAAAAAAAAAAAAAAAAAAAAdm8AAAAAAHF1YwAAAAAAAGtsaGlmZ3oAAAAAYmVu'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAZAAAAAAAAAAAAAAAAAAAFAAUABQAFAA0AE4AygEUAX4B3AHsAhwCTAJkApAC'
        'oAKyAr4C2gMgAzoDdgOwA+AEGARaBIIE0AUUBSYFPAVYBXQFkAXIBg4GVAaeBs4HEAdKB3oHvgf4CBIIQgh+CKQI6Akk'
        'CWoJpAnuCjIKbAqOCsoK/AtAC24LqAvaDAoMJgxWDHAMggyUDNoNJA1UDZYN0A4ADkQOfg6YDsgPBA8qD24Pqg/wECoQ'
        'dBC4EPIRFBFQEYIRxhH0Ei4SYBKaEqgS4hMGE04TZhOAE5wTrBO8E9YT8BQCFBQUJhSEFKAUwBUOFT4VoBXQFeIWFBZM'
        'FoIWtBbqFwgAAgAzAAABzQIiAAMABwAAMxEhESUhESEzAZr+mQE0/swCIv3eMwG8AAMA8v/UAXYDIwADAAkADwAANzMV'
        'Izc1NxcPAQM1NxcPAfKBgQY9QQM7QD1BAztHc8W/SjzSQQHHv0o80kIAAAACAKMB4QH0AzUABQALAAATNTcXDwE3NTcX'
        'DwGjPUEDO5M9QQM7Ai2/STzSQUK/STzSQQAADP//AAACcALtAAUACwARABcAHQAjACkALwA1ADsAQQBHAAABMxcHLwET'
        'MxcHLwEHMxcHLwETMxcHLwEHMxcHLwETMxcHLwETNTcXDwE3NTcXDwEDNTcXDwE3NTcXDwEDNTcXDwE3NTcXDwEB2W0q'
        'IngmJG0qInklp20qIngmJ20qIngmsW0qIngmN20qIngmrCMlAiGZIyUCIeEjJQIimSQlAiLlIyUBIpkjJQEiARspKwMm'
        'AS8oKwIn3CkrAicBMSgrAifgKSsCJwE1KCsCJ/5BfjEoiysofzAnjCsBMX4xKIsrKH8xKIssAUN/MCeLLCl+MSiLKwAD'
        'ACj/xQJOA2QABQALAC0AACUnNx8BBwEnNx8BBxMzFTcXDwEVMxcHIxU3FwcjFSM1Iyc/ATUvATczNSMnPwEBzAE3SQI7'
        '/hkDPUECQpZ1lEk8oRlHOiY7STxIdYtCR4YuPkQoSUFHQ7GaQ0aHSgF+gVNEgkEBojwCPUEBvUNG6AE+QDs7OkEB6wE/'
        'R7w6QQEAAAAACgAS//4CbwJrAAUACwARABcAHQAjACkALwA1ADsAAAE/ARcPAQE/ARcPARMzFwcvAQc1Nx8BBzc1Nx8B'
        'Byc3FwcjJyUzFwcvAQc1Nx8BBzcnNx8BByc3FwcjJwF/il8CmVj+oYlfAplYYnQtJX8oOCcpASnYIy4BJdSTLyagHQE2'
        'dCwkgCc4JykBKdgBIy4CJdWULiafHQHfhQdYkAT+3oUHWJADAmswMwMtq1E8MV0wLG4wMmE1AwIsLjArMDMDLatSOzBe'
        'MCxuMDJhNQMCLC4wAAAJADAAAAJYAmkABQALABEAFwAdACMAKQAvADUAADc1Nx8BBz8BFwcjJxMzFwcvAQc1Nx8BBzc1'
        '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'
        'V5kBYFqJYAKZWAIBYASQWAf+WoUHWJAEjGAEkFgHAaaFB1iQBAAAAAAEACj/bgH1AycACgAQABYAHAAAPwEXByMPAT8B'
        'IycDJzcfAQcTNxcHLwEDJzcfAQfD6Uk8MJdYBjQXPFYDPUECQlPWSjzqQUUBN0kCR3sDPkCOBGAyOgG7gVNEgkEBYwI+'
        'QAE6/c2aQ0agRAADAB0ATgJdAroAAwAHAA0AABMzFSMVMxUjAwUXByUn1s7Ozs51AbZGOf44PwK6z87PAX0DQ0cHPwAA'
        'AAAAAA4ArgABAAAAAAAAAGEAxAABAAAAAAABABEBSgABAAAAAAACAAcBbAABAAAAAAADACwBzgABAAAAAAAEABECHwAB'
        'AAAAAAAFABACUwABAAAAAAAGAA8ChAADAAEECQAAAMIAAAADAAEECQABACIBJgADAAEECQACAA4BXAADAAEECQADAFgB'
        'dAADAAEECQAEACIB+wADAAEECQAFACACMQADAAEECQAGAB4CZABDAG8AcAB5AHIAaQBnAGgAdAAgACgAYwApACAATQBN'
        'AFgAVgBJAEkASQAgAFAAbwByACAAYgBpAGUAbgBlAHMAdABhAHIAIABkAGUAbAAgAGwAbwBzACAAZgBhAG4AcwAgAGQA'
        'ZQAgAFUAcgBiAGEAbgAgAEwAZQBnAGUAbgBkACAAaQBuACAATABpAG0AYgBvAC4AIABFAFMAVABVAEQASQBvAFMAIABI'
        'AEUAQQBWAEUATgAgAEMAQQBTAFQAUgBvAABDb3B5cmlnaHQgKGMpIE1NWFZJSUkgUG9yIGJpZW5lc3RhciBkZWwgbG9z'
        'IGZhbnMgZGUgVXJiYW4gTGVnZW5kIGluIExpbWJvLiBFU1RVRElvUyBIRUFWRU4gQ0FTVFJvAABDAHUAcgBzAGUAZAAg'
        'AFQAaQBtAGUAcgAgAFUATABpAEwAAEN1cnNlZCBUaW1lciBVTGlMAABSAGUAZwB1AGwAYQByAABSZWd1bGFyAABGAG8A'
        'bgB0AEYAbwByAGcAZQAgADIALgAwACAAOgAgAEMAdQByAHMAZQBkACAAVABpAG0AZQByACAAVQBMAGkATAAgADoAIAA2'
        'AC0ANAAtADIAMAAxADgAAEZvbnRGb3JnZSAyLjAgOiBDdXJzZWQgVGltZXIgVUxpTCA6IDYtNC0yMDE4AABDAHUAcgBz'
        'AGUAZAAgAFQAaQBtAGUAcgAgAFUATABpAEwAAEN1cnNlZCBUaW1lciBVTGlMAABWAGUAcgBzAGkAbwBuACAAMAAwADEA'
        'LgAwADAAMAAgAABWZXJzaW9uIDAwMS4wMDAgAABDAHUAcgBzAGUAZABUAGkAbQBlAHIAVQBMAGkATAAAQ3Vyc2VkVGlt'
        'ZXJVTGlMAAAAAAIAAAAAAAD/HAAzAAAAAAAAAAAAAAAAAAAAAAAAAAAAewAAAAEAAgADAAQABQAGAAcACAAJAAoACwAM'
        'AA0ADgAPABAAEQASABMAFAAVABYAFwAYABkAGgAbABwAHQAeAB8AIAAhACIAIwAkACUAJgAnACgAKQAqACsALAAtAC4A'
        'LwAwADEAMgAzADQANQA2ADcAOAA5ADoAOwA8AD0APgA/AEAAQQBCAEMARABFAEYARwBIAEkASgBLAEwATQBOAE8AUABR'
        'AFIAUwBUAFUAVgBXAFgAWQBaAFsAXABdAF4AXwBgAGEBAgCrANgAvgC2ALcAtAC1AIcAsgCzAIwAvwCjAIsAqQCKAIMA'
        'jQCqAKIAZADwAG8AuARFdXJvAAAAAAAAAf//AAIAAQAAAAwAAAAWAB4AAgABAAEAegABAAQAAAACAAAAAQAAAAEAAAAA'
        'AAAAAQAAAADUGVc/AAAAANbsp7cAAAAA1u0Xcg=='),
    'Sym': (
        'AAEAAAASAQAABAAgR0RFRgAPAAQAAA2IAAAAFEdQT1NEdkx1AAANnAAAACBHU1VCJ6Q/wwAADbwAAACWTUFUSAk/M4QA'
        'AA5UAAAA9k9TLzKK45AOAAAC6AAAAFZjbWFwAA4hVgAAA0AAAAA0Y3Z0IABpHTkAAAmIAAAB/mZwZ21xNHZqAAADdAAA'
        'AKtnYXNwAAcABwAADXwAAAAMZ2x5ZgKot3sAAAEsAAABJGhlYWQnWUxPAAACfAAAADZoaGVhDZ8HcQAAAsQAAAAkaG10'
        'eBdfAl8AAAK0AAAAEGxvY2EA3QCGAAACcAAAAAptYXhwBHEGcQAAAlAAAAAgbmFtZSftPb4AAAuIAAAB1HBvc3T/2wBa'
        'AAANXAAAACBwcmVwOwfxAAAABCAAAAVoAAEAc//jBScF8AAZADZAGg2hDq4KlREBoQCuBJUXkRGMGgcZDQAwFBAaEPzs'
        'MuwxABDk9Oz07BDu9u4wtA8bHxsCAV0BFS4BIyAAERAAITI2NxUOASMgABEQACEyFgUnZueC/wD+8AEQAQCC52Zq7YT+'
        'rf56AYYBU4btBWLVX17+x/7Y/tn+x15f00hIAZ8BZwFoAZ9HAAIAwwN1Az0F8AALABoAIEARBsMVxADDDJEbCVoSWwNa'
        'GBsQ3Oz87DEAEPTs/OwwASIGFRQWMzI2NTQmJzIWFx4BFRQGIyImNTQ2AgBQbm5QUG5vT0B2Ky4uuYaHtLgFb29QT21t'
        'T09wgTEuLXJChLe0h4a6AP//AMP/4whtBfAQJgACAAAQBwABA0YAAAABAAAABANUACsAaAAMAAIAEACZAAgAAAQVAhYA'
        'CAAEAAAAAABLAIYAkgAAAAEAAAACXriOcJhiXw889QAfCAAAAAAA4PrROQAAAADg+tE599b8TA5ZCdwAAAAIAAIAAAAA'
        'AAAEzQBmBZYAcwQAAMMI/ADDAAEAAAdt/h0AAA7+99b6UQ5ZAAEAAAAAAAAAAAAAAAAAAAAEAAEEDgGQAAUAAAUzBZkA'
        'AAEeBTMFmQAAA9cAZgISAAACCwYDAwgEAgIEAAAAAAAAAAgAAAAAAAAAAFBmRWQAQCEDIQMGFP4UAZoHbQHjAAAAAQAA'
        'AAAAAAAAAAIAAAADAAAAFAADAAEAAAAUAAQAIAAAAAQABAABAAAhA///AAAhA///3wAAAQAAAAC3BwYFBAMCAQAsIBCw'
        'AiVJZLBAUVggyFkhLSywAiVJZLBAUVggyFkhLSwgEAcgsABQsA15ILj//1BYBBsFWbAFHLADJQiwBCUj4SCwAFCwDXkg'
        'uP//UFgEGwVZsAUcsAMlCOEtLEtQWCCw/UVEWSEtLLACJUVgRC0sS1NYsAIlsAIlRURZISEtLEVELSywAiWwAiVJsAUl'
        'sAUlSWCwIGNoIIoQiiM6ihBlOi0AuAKAQP/7/gP6FAP5JQP4MgP3lgP2DgP1/gP0/gPzJQPyDgPxlgPwJQPvikEF7/4D'
        '7pYD7ZYD7PoD6/oD6v4D6ToD6EID5/4D5jID5eRTBeWWA+SKQQXkUwPj4i8F4/oD4i8D4f4D4P4D3zID3hQD3ZYD3P4D'
        '2xID2n0D2bsD2P4D1opBBdZ9A9XURwXVfQPURwPT0hsF0/4D0hsD0f4D0P4Dz/4Dzv4DzZYDzMseBcz+A8seA8oyA8n+'
        'A8aFEQXGHAPFFgPE/gPD/gPC/gPB/gPA/gO//gO+/gO9/gO8/gO7/gO6EQO5hiUFuf4DuLe7Bbj+A7e2XQW3uwO3gAS2'
        'tSUFtl1A/wO2QAS1JQO0/gOzlgOy/gOx/gOw/gOv/gOuZAOtDgOsqyUFrGQDq6oSBaslA6oSA6mKQQWp+gOo/gOn/gOm'
        '/gOlEgOk/gOjog4FozIDog4DoWQDoIpBBaCWA5/+A56dDAWe/gOdDAOcmxkFnGQDm5oQBZsZA5oQA5kKA5j+A5eWDQWX'
        '/gOWDQOVikEFlZYDlJMOBZQoA5MOA5L6A5GQuwWR/gOQj10FkLsDkIAEj44lBY9dA49ABI4lA43+A4yLLgWM/gOLLgOK'
        'hiUFikEDiYgLBYkUA4gLA4eGJQWHZAOGhREFhiUDhREDhP4Dg4IRBYP+A4IRA4H+A4D+A3/+A0D/fn19BX7+A319A3xk'
        'A3tUFQV7JQN6/gN5/gN4DgN3DAN2CgN1/gN0+gNz+gNy+gNx+gNw/gNv/gNu/gNsIQNr/gNqEUIFalMDaf4DaH0DZxFC'
        'BWb+A2X+A2T+A2P+A2L+A2E6A2D6A14MA13+A1v+A1r+A1lYCgVZ+gNYCgNXFhkFVzIDVv4DVVQVBVVCA1QVA1MBEAVT'
        'GANSFANRShMFUf4DUAsDT/4DTk0QBU7+A00QA0z+A0tKEwVL/gNKSRAFShMDSR0NBUkQA0gNA0f+A0aWA0WWA0T+A0MC'
        'LQVD+gNCuwNBSwNA/gM//gM+PRIFPhQDPTwPBT0SAzw7DQU8QP8PAzsNAzr+Azn+Azg3FAU4+gM3NhAFNxQDNjULBTYQ'
        'AzULAzQeAzMNAzIxCwUy/gMxCwMwLwsFMA0DLwsDLi0JBS4QAy0JAywyAysqJQUrZAMqKRIFKiUDKRIDKCclBShBAycl'
        'AyYlCwUmDwMlCwMk/gMj/gMiDwMhARAFIRIDIGQDH/oDHh0NBR5kAx0NAxwRQgUc/gMb+gMaQgMZEUIFGf4DGGQDFxYZ'
        'BRf+AxYBEAUWGQMV/gMU/gMT/gMSEUIFEv4DEQItBRFCAxB9Aw9kAw7+Aw0MFgUN/gMMARAFDBYDC/4DChADCf4DCAIt'
        'BQj+AwcUAwZkAwQBEAUE/gNAFQMCLQUD/gMCARAFAi0DARADAP4DAbgBZIWNASsrKysrKysrKysrKysrKysrKysrKysr'
        'KysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysr'
        'KysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysr'
        'KysrKwArKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysr'
        'KysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysr'
        'KysrKysrKysrKysrKysrKysrKysrKysrHQE1ALgAywDLAMEAqgCcAaYAuABmAAAAcQDLAKACsgCFAHUAuADDAcsBiQIt'
        'AMsApgDwANMAqgCHAMsDqgQAAUoAMwDLAAAA2QUCAPQBVAC0AJwBOQEUATkHBgQABE4EtARSBLgE5wTNADcEcwTNBGAE'
        'cwEzA6IFVgWmBVYFOQPFAhIAyQAfALgB3wBzALoD6QMzA7wERAQOAN8DzQOqAOUDqgQEAAAAywCPAKQAewC4ABQBbwB/'
        'AnsCUgCPAMcFzQCaAJoAbwDLAM0BngHTAPAAugGDANUAmAMEAkgAngHVAMEAywD2AIMDVAJ/AAADMwJmANMAxwCkAM0A'
        'jwCaAHMEAAXVAQoA/gIrAKQAtACcAAAAYgCcAAAAHQMtBdUF1QXVBfAAfwB7AFQApAa4BhQHIwHTALgAywCmAcMB7AaT'
        'AKAA0wNcA3ED2wGFBCMEqARIAI8BOQEUATkDYACPBdUBmgYUByMGZgF5BGAEYARgBHsAnAAAAncEYAGqAOkEYAdiAHsA'
        'xQB/AnsAAAC0AlIFzQBmALwAZgB3BhAAzQE7AYUDiQCPAHsAAAAdAM0HSgQvAJwAnAAAB30AbwAAAG8DNQBqAG8AewCu'
        'ALIALQOWAI8CewD2AIMDVAY3BfYAjwCcBOECZgCPAY0C9gDNA0QAKQBmBO4AcwAAFAAAlgAAAAAABwBaAAMAAQQJAAAB'
        'MAAAAAMAAQQJAAEAFgEwAAMAAQQJAAIACAFGAAMAAQQJAAMAFgEwAAMAAQQJAAQAFgEwAAMAAQQJAAUAGAFOAAMAAQQJ'
        'AAYAFAFmAEMAbwBwAHkAcgBpAGcAaAB0ACAAKABjACkAIAAyADAAMAAzACAAYgB5ACAAQgBpAHQAcwB0AHIAZQBhAG0A'
        'LAAgAEkAbgBjAC4AIABBAGwAbAAgAFIAaQBnAGgAdABzACAAUgBlAHMAZQByAHYAZQBkAC4ACgBDAG8AcAB5AHIAaQBn'
        'AGgAdAAgACgAYwApACAAMgAwADAANgAgAGIAeQAgAFQAYQB2AG0AagBvAG4AZwAgAEIAYQBoAC4AIABBAGwAbAAgAFIA'
        'aQBnAGgAdABzACAAUgBlAHMAZQByAHYAZQBkAC4ACgBEAGUAagBhAFYAdQAgAGMAaABhAG4AZwBlAHMAIABhAHIAZQAg'
        'AGkAbgAgAHAAdQBiAGwAaQBjACAAZABvAG0AYQBpAG4ACgBEAGUAagBhAFYAdQAgAFMAYQBuAHMAQgBvAG8AawBWAGUA'
        'cgBzAGkAbwBuACAAMgAuADMANwBEAGUAagBhAFYAdQBTAGEAbgBzAAMAAAAAAAD/2ABaAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAACAAgAAv//AAMAAQAAAAwAAAAAAAAAAQADAAEAAQABAAAACgAcAB4AAURGTFQACAAEAAAAAP//AAAAAAAAAAEA'
        'AAAKAJIAlAAUREZMVAB6YXJhYgCEYXJtbgCEYnJhaQCEY2FucwCEY2hlcgCEY3lybACEZ2VvcgCEZ3JlawCEaGFuaQCE'
        'aGVicgCEa2FuYQCEbGFvIACEbGF0bgCEbWF0aACEbmtvIACEb2dhbQCEcnVucgCEdGZuZwCEdGhhaQCEAAQAAAAA//8A'
        'AAAAAAAAAAAAAAAAAQAAAAoA4ADoAFAAPAwAB90AAAAAAoIAAARgAAAF1QAAAAAAAARgAAAAAAAAAAAAAAAAAAAEYAAA'
        'AAAAAAFoAAAEYAAAAFUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQ4AAAJ2AAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAABaAAABDgAAAFoAAABaAAABDgAAAAAAAAAAAAABDgAAAFoAAABaAAABDgAAAFoAAABa'
        'AAAAWgAAAXIAAABaAAAAWgAAAjgAAPuPAAAAPAAAAAAAAAAAACgACgAKAAAAAAABAAAAAA=='),
}
SPLASH_PNG = (
    'iVBORw0KGgoAAAANSUhEUgAAAoAAAAFACAYAAAAszc0KAABQWUlEQVR42u2dd5hsVZW331XV915yRhBRASUoomJAJAtySSOm'
    'MY06ZpxxnHE+8ygz6igGdMQwjmnMDiYMJJGogigmFBRFFERAUHLm3ttdtb4/9trUvudWdVfsrur7e5/nPKe7qk7aZ599fnut'
    'vdYGIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBC'
    'CCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQggh'
    'hBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQ'
    'QgghhBBCCCGEEEIIIYQQQgghhBBCCNE7piIYT9y9Vv3IzHwEx7GoB17UiZEca8TlZUV9nrjzn9TyiXrqk1pvhBBCiLVVFAgh'
    'hBBiLUMCYDyF2VJgi8p9cjO7dgTH2hxYh5YFEOBuM7t1gsqrBtwHyFbTlWZ2k2rSveVTB7YqPrrHzG7p8Nup8l8za8yy32XA'
    '5sVHd5jZHSpxIYQQovcXNe7+eHdf4e73xPru+Psgd7f8uwGOY7Hewt2vKY51Z/z93+X5jHF5lddxbZz7Cnc/pRCGa3N9qsX6'
    'ge5+a1GfPj/I/S3q6UGxvzti/aY2IlIIIcQYooZ6PKkBy8p3LskK+DIzO9vdBx1nVQdmgKcA9yv234xjT1q9MJIVM5fZMlWh'
    'NcpnXWBp/L9kFsF4FLBlfHStmX1qjnq0LOpLXe2JEEJIAIrB8UKYZcF3uLtvY2bXunvNzJp97rsZ1rPnx74b8QJvVI43STSK'
    '826o+qxRl1bFvbUQ/6XwswjeqANvpeUuvhz4VBd1tBEdBwWACCHEhFBTEYwtViy1eMluCPzdIPeuEI67AXvFx/XK8Sa9vDS2'
    'dXXqwAYky98UsNEsgu6GEIgzwM09lrsQQogJQRbAyRI4AM919/fTv5WrRnL1Pj/u/4zqwaIlW+RuBt5Ey1X7q8r31TZhqhCO'
    'QgghJADFArGSNNbKgUcAe5nZD9y9PluU5hpqILl9G+6+PvCs4iWf9y8WU48hcvJFRPe72nzfVCkJIcTaiVzA40220JwO5PQa'
    'Bryoz/3VQxQcDtw/9j8DnNT3CbrX3L3u7lOVpT5oFG7se6rNMrR6m6OqR3Gc2Pe9y6i367Rt/L2kWKqWPaskih7muXSqG3IZ'
    'CyHEAiIL4HiTB9f/mDRu64AQbU9299eb2U3FAP5uyBafFxRi8jLgLOAZxffdvNzrQHMuK1IWUb1Ymyr7bs6yX6NPV3jePiyo'
    's+W6M6DWi6X1XlXV56wYg8ym0W7b+Gx6lm1yGU9XIsz7ndnDCut0o4v7rOARIYSQABRtuA34agjAVaTku08DPkkrpcucgsfM'
    'mu6+PXBgIS5PBf6cf9bFfixEQyP+fxApoOR+wKbxs+uBK4FLzOzP5fG72LcV+34YsAfwIGCTKIffAT80s98XIqJX8VcvjnFf'
    'UjDMQ4DtojxvAX4N/MTMfk1ym9d6EUThZl+XViT3XWZ2T5fbbsjqLvmbujlulF+ZmLlhZrdEGW1Cy8K3MidsjqTjG8d5VlO5'
    'LHH3zVjdU3DnbGIyyqkRdW2jKNvdgG1i3zcAl8Q9vK7buiGEEEIsWooEu3t7YlWsX+fum8f/M/HZ+aUg62LfU7E+urLv3dz9'
    'yPh7Raw/2k5clcdy9+e7+w8jSXUnbnP3E919n0IczCos4+/D3P2c4lqr3O3uXw6BiLvf191vLL4/vdPxiuTIu7j7p9z9plnO'
    'fzrO44h8jnOVd3EPnxgJkm+KcvjKbGVQuGuXuvsvY5u87UGzid3KMW9z9xti/b74fAd3/2skg77N3T9VbHtEfH5zrMsyn3H3'
    'W+LzG2P9gmLbgyt16W1ZwLr7W939ylnK9mZ3/6C7bzpX3RBCCCHWVgH4lvj8rEKYNNz90d28PIsxXEvd/dLiJXxpfP/cuQRg'
    'IVA2c/eTvXfe1EnExLnl8X4fLLZpzLHPO939WXFdt8wlAIvyfUVs2wsfzuMaZxOBRTlt6O7XF9vfGta0tqK9EKaPKbZpxvrd'
    'pYifRdx/sFJuh8TnD446k/lyse3TeiyHf5hFAL7a3bcNATsbK4u/f+3u95cIFEKI+UUu4Mkgi45PAQeRxsVNAc8Dfk4rtUvH'
    '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')
ICON_PNG = (
    'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAETklEQVR4nO2YS28bVRiGnxmPL7Gd+BInTho3du0khZKmN4VS'
    'tQq3Cgk2ZQl/gBV/gP/BAqgQiwoktgikFgpIlQqhtGlLAmpzaRI3sZ00dnwfezwzH4skJaVUQtDWQuKVzmLmaOZ9zpnvnKN3'
    'EBG223EROSciKyJiy+OXJSJLInJWRMZ3fHfMz4jI/BMwfZRmtz1hm2b2KZrvaF5EjqvAO8AwT18p4F1FRJaAeBsAADKKiFiA'
    '2iYAUdtoDqC00xz4l6MXEVqm3T4AyxbKtSa2yJMHsCybhmFiWn+M2GhZXL+Vod5o/WMA7VEd64Uas8sbdPrciAir9yrki3X2'
    '9HQS7w8wHPNRruikcyVGU2H8HhtEQFERnGyWmximhWnZhLs68HqcfwfABquG3SpycTLDt1ez7O3tolRr0OX3EOr0sLBS4Nai'
    'B3O0Qa6oMDldIR4q0ncIbNskXxZ+yUS5eruCAtQaBoN9QV48liA5EEJV1b8AsA1En0WaqygK5IoOrswUEXFgWjZul8Zbrx0k'
    'FQuTXivx6Vc3mFwIEAp0UNM3qDNCxZlgcXWTmfkc12/neC4V5ZlEhEJZ56fpFb68dIu3X+0nGlTAPQCKCwAVMbEyH2JlP0bx'
    'HUAJnubn9AD5CuzbE8TrcZKKhdkfj+ByOhiKhUkMhKg2WugNE4CV9TK3l/I0DIvlbJmTh+O8dGwfg31BomE/LxyMYdpwc9FA'
    'L0xhr326NduAhthIcxWpTiOF82yqx7k2s8hIPMJgX5DpuRwtyyZfqtMT8rFZ1tks62iag3qjhcvpQEUh2Onh14V1qrrB4ZE+'
    'Lvw4R26jgmULpw7HGU1FEauGqa/g0irb9QIaqgst/h526TJ2+Qql7AccCQnJ4Qmy5TppLzRbFp98MUUqFmYpUyS7UeFAshfT'
    'sgj4PczcWWM2vYEtEPC70ZsmpWqDUMBLvWEQ8DtRzQzZ9BW01CCOyAQojl01oAVQu9+g7JzgswvncTksTg+NszyVw+HQGUtG'
    'KVUaZDYqdPrcnDoSZ388wg83l7mzsklVN/C4NUS2luZcOs+JsUH8HS40TcXrVrh4uUR3aByl+3lwan8qwm3dmL3HTBrefHkU'
    'fzCJIQ1qjTojg93sT0So1g08Lo1OnxsA0xKWs0UmjiY4kOzh869nqNYNvm/e4fWTI8R6u9CbLS5MLmLYAU4cHcXjenDh3b9q'
    'GibpXJGx4V5OHdqLokCw08Xevi463M77bbdcTgfhQAfHnt3D6FCUS9eXWS9UGRuKcmlqiWu/ZShWdaJhP6+MJ+nv9j+0Dygi'
    'W/uoCLRMC0UBp7b1ffRmC6Nl4fU479/brXypTqGkEw378Ha4mL+bx7RsEv0h1gpVPC6Ncq1JT8hHJOh96PkHANql//Zx/D/A'
    '4wJoZxHaKpBtI8BdFfiujQDfqMD7wEIbzOeBj3aH07mnnAvPyK50vBNSz8qTi+f29rvPydavAESE3wEDMC7ThY7dWgAAAABJ'
    'RU5ErkJggg==')


if __name__ == '__main__':
    main()
