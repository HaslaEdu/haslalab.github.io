"""Native CPython oracle: import the entire user source, never construct Tk."""
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
    return {key: getattr(lab, key) for key in (
        "obj", "order", "slider", "laser_fine", "hold_rot", "tape_on", "tape_held",
        "tape_a", "tape_b", "clock", "t", "dark")}


lab = ns["Lab"](201901)
tab = original_tab(lab)
snapshots = []
# Original placement at the web camera's table centre.
for key, point in (("ruler", [136, 170]), ("disk", [136, 96]), ("holder", [136, 96]), ("tape6", [40, 60])):
    tab.center = lambda point=point: point
    tab.toggle(key)
    snapshots.append(state(lab))
    snapshots[-1] = json.loads(json.dumps(snapshots[-1]))

# Original dragging / SAT separation and wheel steps.
tab.side = tab.screen_side("disk")
tab.drag = ("disk", 0.0, 0.0)
tab.m1(types.SimpleNamespace(x=142, y=112))
snapshots.append(json.loads(json.dumps(state(lab))))
lab.sel = "disk"
tab.wheel(types.SimpleNamespace(delta=120, state=0))
snapshots.append(json.loads(json.dumps(state(lab))))
lab.sel = "holder12b"
tab.wheel(types.SimpleNamespace(delta=-120, state=1))
snapshots.append(json.loads(json.dumps(state(lab))))

# Original tape freezes the wobbling pose and subsequent rotation stays anchored.
lab.tape_held = True
x, y, _angle = lab.pose("disk")
tab.stick_tape(x - 5, y)
snapshots.append(json.loads(json.dumps(state(lab))))
x, y, _angle = lab.pose("disk")
tab.stick_tape(x + 5, y)
snapshots.append(json.loads(json.dumps(state(lab))))
lab.sel = "disk"
tab.wheel(types.SimpleNamespace(delta=120, state=0))
snapshots.append(json.loads(json.dumps(state(lab))))
tab.tick(18.1)
snapshots.append(json.loads(json.dumps(state(lab))))
print(json.dumps(snapshots, separators=(",", ":")))
