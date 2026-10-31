"""Browser input/output adapter for the unmodified IPhO 2019 simulator.

The original Lab owns every optical computation. The original LabTab owns
placement, collision, tape, slider, rotation and clock behavior. Its Tk drawing
callbacks are replaced by the web renderer; no desktop window is constructed.
"""
import json
import math
import sys
import types


def _hl_original(source):
    # Only base classes are needed when the complete source is imported. Tk
    # constructors must never run in the browser; the frontend supplies drawing.
    tk = types.ModuleType("tkinter")
    ttk = types.ModuleType("tkinter.ttk")
    tk.Toplevel = type("Toplevel", (), {})
    ttk.Frame = type("Frame", (), {})
    tk.ttk = ttk
    previous = {name: sys.modules.get(name) for name in ("tkinter", "tkinter.ttk")}
    sys.modules.update({"tkinter": tk, "tkinter.ttk": ttk})
    namespace = {"__name__": "ipho2019_original", "__file__": "ipho2019_E1_sim_KO.py"}
    try:
        exec(compile(source, namespace["__file__"], "exec"), namespace)
    finally:
        for name, value in previous.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value
    return namespace


_HL_ORIGINAL = _hl_original(_hl_source)
_HL_LABS = {}
_HL_FIELDS = (
    "obj", "order", "tape_on", "tape_held", "tape_a", "tape_b", "ftape_a", "ftape_b",
    "slider", "laser_fine", "hold_item", "hold_rot", "sel", "level", "laser_on",
    "parchment", "dark", "clock", "t", "lamp",
)
_HL_PARAMETERS = ("n_disk", "n_prism", "lam_over_d", "grating_id", "prism_eps", "prot_zero", "_ph")


class _Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class _Label:
    def configure(self, **_kwargs):
        pass


def _hl_tab(lab):
    tab = object.__new__(_HL_ORIGINAL["LabTab"])
    tab.lab = lab
    tab.side = 0
    tab.drag = None
    tab.press_xy = None
    tab.redraw = lambda: None
    tab.wobble_redraw = lambda: None
    tab.cm = lambda event: (event.x, event.y)
    tab.center = lambda: (136.0, 104.0)
    tab.ts = _Value(1)
    tab.lbl_dark = _Label()
    return tab


def _hl_frame(lab, trace=None):
    poses = {key: lab.pose(key) for key in lab.obj}
    frame = {"poses": poses, "pivot": lab.pivot(), "laser": lab.laser(),
             "beam_dir": lab.beam_dir(), "disk_center": lab.disk_center(),
             "prism_poly": lab.prism_poly(), "grating_seg": lab.grating_seg(),
             "screen_seg": lab.screen_seg(), "light_phase": lab.light_phase(),
             "slider_limits": lab.slider_limits(), "active": lab.active(),
             "wobbly": lab.wobbly(), "ruler8_samples": []}
    # Evaluate the original coverage predicate at renderer sample positions in
    # one Python call. This avoids a Python/JS boundary crossing for every ray.
    if trace is not None and lab.obj["ruler8"]["on"]:
        samples = frame["ruler8_samples"]
        for x0, y0, x1, y1, _intensity, kind in trace["segments"]:
            if kind != "glass":
                continue
            dx, dy = (x1 - x0) / 12, (y1 - y0) / 12
            for index in range(12):
                x, y = x0 + (index + .5) * dx, y0 + (index + .5) * dy
                samples.append((x, y, lab.in_ruler8(x, y)))
        for x, y, _intensity in trace["spots"]:
            samples.append((x, y, lab.in_ruler8(x, y)))
    return frame


def _hl_snapshot(lab, result=None, trace=None):
    state = {key: getattr(lab, key) for key in _HL_FIELDS if hasattr(lab, key)}
    state.update({key: getattr(lab, key) for key in _HL_PARAMETERS})
    return json.dumps({"state": state, "frame": _hl_frame(lab, trace), "result": result},
                      separators=(",", ":"), allow_nan=False)


def _hl_new(identifier, seed):
    lab = _HL_ORIGINAL["Lab"](seed)
    lab.lamp = False
    _HL_LABS[identifier] = (lab, _hl_tab(lab))
    return _hl_snapshot(lab)


def _hl_dispatch(identifier, state_json, method, args_json):
    lab, tab = _HL_LABS[identifier]
    state, args = json.loads(state_json), json.loads(args_json)
    for key in _HL_FIELDS + _HL_PARAMETERS:
        if key in state:
            setattr(lab, key, state[key])
    lab._pc.clear()
    result, trace = None, None
    if method == "refresh":
        pass
    elif method == "trace":
        segments, spots, hits, shots = lab.trace()
        trace = {"segments": segments, "segs": segments, "spots": spots, "hits": hits, "shots": shots}
        result = trace
    elif method == "raise_":
        result = lab.raise_(*args)
    elif method == "setMounted":
        key, mounted, position = args
        current = lab.tape_on if key == "tape" else lab.obj[key]["on"]
        if current != mounted:
            default = (136.0, 104.0) if key == "tape" else lab.obj[key]["pos"]
            tab.center = lambda: position if position is not None else default
            tab.toggle(key)
        if not mounted and key == "tape6":
            lab.tape_held = False
        result = lab.tape_on if key == "tape" else lab.obj[key]["on"]
    elif method == "move":
        key, position, remove_outside = args
        obj = lab.obj.get(key)
        result = bool(obj and obj["on"] and not obj["tapes"])
        if result:
            tab.side = tab.screen_side(key)
            tab.drag = (key, 0.0, 0.0)
            tab.m1(types.SimpleNamespace(x=position[0], y=position[1]))
            if remove_outside:
                tab.press_xy = (-1000, -1000)
                tab.r1(types.SimpleNamespace(x=position[0], y=position[1]))
            tab.side = 0
    elif method == "rotate":
        key, delta = args
        obj = lab.obj.get(key)
        result = key in ("laser", "holder12b") or bool(
            obj and key in lab.LOCAL and obj["on"] and len(obj["tapes"]) < 2)
        if result:
            # The source has two wheel steps: 2 degrees and Shift+wheel .25.
            # Quantize 3D pointer motion to those same physical adjustments.
            quarter_steps = int(abs(delta) * 4 + .5)
            lab.sel = key
            direction = 1 if delta >= 0 else -1
            large, small = divmod(quarter_steps, 8)
            for shift, count in ((0, large), (1, small)):
                for _ in range(count):
                    tab.wheel(types.SimpleNamespace(delta=direction, state=shift))
    elif method == "setSlider":
        value, = args
        x, y, angle = lab.pose("ruler")
        ux, uy = _HL_ORIGINAL["dirv"](angle)
        tab.drag = ("slider", 0.0, 0.0)
        tab.m1(types.SimpleNamespace(x=x + ux * value, y=y + uy * value))
        result = lab.slider
    elif method == "stickTape":
        result = bool(lab.tape_held and lab.obj["tape6"]["on"] and tab.stick_tape(*args))
    elif method == "peelTape":
        key, index = args
        obj = lab.obj.get(key)
        result = bool(obj and 0 <= index < len(obj["tapes"]))
        if result:
            obj["tapes"].pop(index)
    elif method == "moveTapeEndpoint":
        key, position, remove_outside = args
        setattr(lab, key, position)
        if key.startswith("tape_") and remove_outside:
            tab.drag = (key, 0.0, 0.0)
            tab.press_xy = (-1000, -1000)
            tab.r1(types.SimpleNamespace(x=position[0], y=position[1]))
        result = True
    elif method == "advance":
        dt, scale = args
        tab.ts.value = scale
        tab.tick(dt)
        result = lab.light_phase()
    elif method in ("local", "inside", "in_ruler8", "protractor"):
        result = getattr(lab, method)(*args)
    else:
        raise ValueError("Unknown browser operation: " + method)
    lab._pc.clear()
    return _hl_snapshot(lab, result, trace)


def _hl_vis(intensity, dark):
    return _HL_ORIGINAL["vis"](intensity, dark)


def _hl_dispose(identifier):
    _HL_LABS.pop(identifier, None)
