# IPhO 2019 E1 — Optical measurements

Browser entry: `../ipho2019_E1_web.html?lang=ko` (or `lang=en`).

The optical and mechanical model is a direct port of the user-supplied
`IPhO2019_Q1_Sim_KO.py` (SHA-256
`dae656e74496a3f2c224c068ceaa7c820978301aa0d6d1f9d2a78001aa19ba12`).
Lengths are centimetres and orientations are degrees. Air paths are retained
for propagation but never drawn. Measurements use the apparatus graduations;
the interface does not reveal specimen parameters or calculate final answers.
The supplied simulator's accelerated room-light schedule is preserved.

The procedural apparatus models follow photographs on pages 2–3 of the
[official English problem paper](https://ipho.olimpicos.net/pdf/IPhO_2019_Q4.pdf).
No external model, image, font, or script is requested at runtime. Three.js
0.170.0 and its MIT license are vendored in `../../vendor/three`.

The initial browser arrangement places the ruler/laser assembly and disk;
the laser starts off. Moving, rotating, taping, changing beam height, reading
the screen and switching optical elements use the original model. A new
experiment generates a new specimen. Reloads retain this tab's experiment.

Run `node --test tests/test-ipho2019-e1-physics.mjs` from the repository root.
Run `node tools/build-site-catalogue.cjs` after editing a module or stylesheet;
the build updates dependent asset fingerprints.
