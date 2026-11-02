# scanic-ml 0.2.0 (MIT)

Files from the npm package `scanic-ml@0.2.0` (https://github.com/marquaye/scanic, directory `scanic-ml`), MIT licence (see `LICENSE`, the scanic repository's licence; the package declares `"license": "MIT"`):

- `doccornernet_lean.f16.bin`: the package's `doccornernet_lean.ort` (DocCornerNet LEAN document-corner model, architecture from DocCornerNet-CoordClass, https://github.com/mapo80/DocCornerNet-CoordClass, MIT; see `MODEL_CARD.md`), **modified by HaslaLab** for a smaller download: its 48 large weight tensors are stored as fp16 (`tools/pack_corner_model.py`, source sha256 `732eb8d02d83cc63efb3f9467f01e0c458205a89b2547de3870bc6db1a80c8b3`). The browser rebuilds the fp32 `.ort` from it (`decodeCornerModel` in `sim/labscan/scanner.js`) and runs it unchanged.
- `ort-wasm-simd-threaded.mjs`, `ort-wasm-simd-threaded.wasm` (unmodified): scanic's custom minimal ONNX Runtime Web build (ONNX Runtime is MIT, Microsoft).

The JavaScript loader is `../scanic-1.7.1/scanic-mlDetector.js` with `scanic-ort.wasm.min.js` (scanic 1.7.1, MIT). HaslaLab serves these files itself; nothing is fetched from a CDN and no photo leaves the device.
