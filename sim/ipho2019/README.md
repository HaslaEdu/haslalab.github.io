# IPhO 2019 E1 — Optical measurements

Browser entry: `../ipho2019_E1_web.html?lang=ko` (or `lang=en`).

The browser executes the complete, unmodified user-supplied Python file at
`../../src/ipho2019_E1_sim_KO.py` (SHA-256
`dae656e74496a3f2c224c068ceaa7c820978301aa0d6d1f9d2a78001aa19ba12`).
`e1-python.mjs` loads locally hosted Pyodide 0.29.3 / CPython 3.13.2.
`e1-bridge.py` provides browser input/output around the original `Lab` and
`LabTab` methods. Inert Tk base classes let the full source import without
constructing desktop windows. The original optical calculations, random
specimens, collision rules, tape constraints, slider, rotation and room-light
schedule execute in Python. The former JavaScript optical port is removed.

The web shell follows the site's other experimental simulators: a compact
header, equipment tray, central bench and control panel with grey panels and
yellow accents. As in the Python version, equipment starts in the tray and
is placed at the center of the current view. Reloading starts a new experiment.
Drag to move; wheel over apparatus rotates 2 degrees (Shift: .25). The slider,
laser switch, cylinder, tape roll and screen retain their original controls.
The web renderer adds the 3D camera and touch controls. Measurements use printed
apparatus graduations; hidden specimen values and calculated answers are never
shown.

Procedural 3D apparatus follows the photographs on pages 2–3 of the
[official English problem paper](https://ipho.olimpicos.net/pdf/IPhO_2019_Q4.pdf).
No external runtime requests are needed. Three.js 0.170.0 is in
`../../vendor/three`; Pyodide and CPython licenses are in `../../vendor/pyodide`.

Run `node --test tests/test-ipho2019-e1-*.mjs tests/test-learn-coming-soon.cjs`
from the repository root. Tests run the actual WebAssembly Python runtime,
compare eight frozen source raytraces, and compare apparatus controls with the
original methods in native CPython. Run `node tools/build-site-catalogue.cjs`
after source edits to update dependent fingerprints.
