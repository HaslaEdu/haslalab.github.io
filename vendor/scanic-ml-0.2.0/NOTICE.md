# scanic-ml 0.2.0 (MIT)

Unmodified files from the npm package `scanic-ml@0.2.0` (https://github.com/marquaye/scanic, directory `scanic-ml`), MIT licence (see `LICENSE`, the scanic repository's licence; the package declares `"license": "MIT"`):

- `doccornernet_lean.ort`: DocCornerNet LEAN document-corner model (architecture from DocCornerNet-CoordClass, https://github.com/mapo80/DocCornerNet-CoordClass, MIT); see `MODEL_CARD.md`.
- `ort-wasm-simd-threaded.mjs`, `ort-wasm-simd-threaded.wasm`: scanic's custom minimal ONNX Runtime Web build (ONNX Runtime is MIT, Microsoft).

The JavaScript loader is `../scanic-1.7.1/scanic-mlDetector.js` with `scanic-ort.wasm.min.js` (scanic 1.7.1, MIT). HaslaLab serves these files itself; nothing is fetched from a CDN and no photo leaves the device.
