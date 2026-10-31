# Pyodide 0.29.3

Unmodified runtime files from the official `pyodide@0.29.3` npm distribution:
https://registry.npmjs.org/pyodide/-/pyodide-0.29.3.tgz

Project and source: https://github.com/pyodide/pyodide/tree/0.29.3
Documentation: https://pyodide.org/en/0.29.3/usage/quickstart.html

`pyodide.mjs`, `pyodide.asm.js`, `pyodide.asm.wasm`, `python_stdlib.zip`, and
`pyodide-lock.json` are hosted locally so the optical experiment does not require
a third-party CDN. No optional package installation is performed.

Pyodide is licensed under MPL 2.0; see LICENSE. Its CPython 3.13.2 runtime and
standard library use the Python license in PYTHON-LICENSE, copied from:
https://github.com/python/cpython/blob/v3.13.2/LICENSE

The experiment executes `src/ipho2019_E1_sim_KO.py` unchanged. The small
`sim/ipho2019/e1-bridge.py` adapter replaces Tk drawing callbacks with the web
renderer and forwards input to the original Lab/LabTab classes.
