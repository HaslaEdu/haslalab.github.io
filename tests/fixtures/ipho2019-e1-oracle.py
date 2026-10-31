"""Native CPython oracle for the IPhO 2019 E1 web lab.

Imports the whole original source (src/ipho2019_E1_sim_KO.py) without
constructing Tk and prints, as JSON, the specimen of Lab(201901), ray traces
of many arrangements and the state after a sequence of the original LabTab
handlers.  tests/fixtures/ipho2019-e1-python.json is this output, frozen:

    python3 tests/fixtures/ipho2019-e1-oracle.py > tests/fixtures/ipho2019-e1-python.json
"""
import hashlib
import json
from pathlib import Path
import sys
import types

tk, ttk = types.ModuleType("tkinter"), types.ModuleType("tkinter.ttk")
tk.Toplevel, ttk.Frame = type("Toplevel", (), {}), type("Frame", (), {})
tk.ttk = ttk
sys.modules.update({"tkinter": tk, "tkinter.ttk": ttk})
source = Path(__file__).parents[2] / "src/ipho2019_E1_sim_KO.py"
ns = {"__name__": "ipho2019_native_oracle", "__file__": str(source)}
exec(compile(source.read_bytes(), str(source), "exec"), ns)
Lab = ns["Lab"]


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class Label:
    def configure(self, **_kwargs):
        pass


def original_tab(lab):
    tab = object.__new__(ns["LabTab"])
    tab.lab = lab
    tab.redraw = tab.wobble_redraw = lambda: None
    tab.cm = lambda event: (event.x, event.y)
    tab.side = 0
    tab.ts, tab.lbl_dark = Value(10), Label()
    return tab


def state(lab):
    return json.loads(json.dumps({key: getattr(lab, key) for key in (
        "obj", "order", "slider", "laser_fine", "hold_rot", "tape_on", "tape_held",
        "tape_a", "tape_b", "clock", "t", "dark")}))


def fixed(x, y, ang=0.0):
    return dict(on=True, pos=[x, y], ang=ang, tapes=[(-12.0, -2.0), (12.0, 2.0)])


SPECIMEN = ("n_disk", "n_prism", "lam_over_d", "grating_id", "prism_eps", "prot_zero", "_ph")
CASES = []


def case(name, objects, **attrs):
    CASES.append(dict(name=name, objects=objects, **attrs))


for s in (-8.0, -4.0, 0.0, 3.0, 7.5):
    case("disk slider %g" % s, {"ruler": fixed(136, 170), "disk": fixed(136, 96, 270)}, slider=s)
for f in (1.25, -3.0, 9.5):
    case("disk fine %g" % f, {"ruler": fixed(136, 170), "disk": fixed(136, 96, 270)}, slider=-6.0, laser_fine=f)
case("disk turned", {"ruler": fixed(136, 170), "disk": fixed(140, 92, 31)}, slider=-5.0)
case("ruler turned", {"ruler": fixed(130, 168, 15), "disk": fixed(140, 100, 0)}, slider=2.0)
case("ruler backwards", {"ruler": fixed(136, 40, 180), "disk": fixed(136, 110, 270)}, slider=-3.0)
case("bare wall", {"ruler": fixed(136, 170)})
for r in (0.0, 12.0, -25.0, 40.0):
    case("grating %g" % r, {"ruler": fixed(136, 170), "holder": fixed(140, 110),
                            "screen": fixed(136, 30)}, level="high", hold_rot=r, slider=4.0)
for r in (0.0, 20.0, 47.0, 75.0, 130.0):
    case("prism %g" % r, {"ruler": fixed(136, 170), "holder": fixed(136, 110),
                          "screen": fixed(150, 40, 20)}, level="high", hold_item="prism", hold_rot=r, slider=-1.5)
case("low beam blocked by 12B", {"ruler": fixed(136, 170), "holder": fixed(136, 110)}, slider=0.0)
case("screen behind disk", {"ruler": fixed(136, 170), "disk": fixed(136, 110, 270),
                            "screen": fixed(136, 40)}, slider=-7.0)
case("wobbling disk", {"ruler": fixed(136, 170), "disk": dict(on=True, pos=[136, 96], ang=270.0, tapes=[])},
     slider=-6.0, t=37.3)
case("pinned disk", {"ruler": fixed(136, 170), "disk": dict(on=True, pos=[136, 96], ang=270.0, tapes=[(-12.0, 4.0)])},
     slider=-6.0, t=81.9)
case("wobbling ruler", {"ruler": dict(on=True, pos=[136, 170], ang=0.0, tapes=[]), "disk": fixed(136, 96, 270)},
     slider=-6.0, t=12.4)


def run_case(c):
    lab = Lab(201901)
    lab.laser_on = True
    for key, value in c["objects"].items():
        lab.obj[key].update(json.loads(json.dumps(value)))
    for key, value in c.items():
        if key not in ("name", "objects"):
            setattr(lab, key, value)
    lab._pc.clear()
    segs, spots, hits, shots = lab.trace()
    return json.loads(json.dumps(dict(segs=segs, spots=spots, hits=hits, shots=shots)))


def handlers():
    """the original LabTab methods, driven as the web lab drives them"""
    lab = Lab(201901)
    tab = original_tab(lab)
    out = []
    for key, point in (("ruler", [136, 170]), ("disk", [136, 150]), ("holder", [136, 96]),
                       ("screen", [136, 100]), ("tape6", [40, 60])):
        tab.center = lambda point=point: point
        tab.toggle(key)
        out.append(state(lab))
    tab.side = tab.screen_side("disk")
    tab.drag = ("disk", 0.0, 0.0)
    tab.m1(types.SimpleNamespace(x=142, y=112))
    out.append(state(lab))
    lab.sel = "disk"
    tab.wheel(types.SimpleNamespace(delta=120, state=0))
    out.append(state(lab))
    lab.sel = "holder12b"
    tab.wheel(types.SimpleNamespace(delta=-120, state=1))
    out.append(state(lab))
    lab.sel = "laser"
    tab.wheel(types.SimpleNamespace(delta=120, state=1))
    out.append(state(lab))
    lab.tape_held = True
    x, y, _a = lab.pose("disk")
    tab.stick_tape(x - 5, y)
    out.append(state(lab))
    x, y, _a = lab.pose("disk")
    tab.stick_tape(x + 5, y)
    out.append(state(lab))
    lab.sel = "disk"
    tab.wheel(types.SimpleNamespace(delta=120, state=0))
    out.append(state(lab))
    x, y, _a = lab.pose("ruler")
    tab.stick_tape(x - 20, y)
    tab.stick_tape(x + 20, y)
    tab.stick_tape(x + lab.slider + 2, y)
    out.append(state(lab))
    tab.drag = ("slider", 0.0, 0.0)
    tab.m1(types.SimpleNamespace(x=x + 25, y=y))
    out.append(state(lab))
    tab.m1(types.SimpleNamespace(x=x - 25, y=y))
    out.append(state(lab))
    tab.tick(18.1)
    out.append(state(lab))
    tab.tick(3.0)
    out.append(state(lab))
    return out


print(json.dumps(dict(
    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    specimen={k: getattr(Lab(201901), k) for k in SPECIMEN},
    cases=[dict(input=c, trace=run_case(c)) for c in CASES],
    handlers=handlers()), separators=(",", ":")))
