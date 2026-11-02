import module from './vendor/pdfium/pdfium.wasm';
import { init } from './vendor/pdfium/engine.js';
export async function loadReferencePdfium() {
  const library=await init({instantiateWasm(imports,receive){const instance=new WebAssembly.Instance(module,imports);receive(instance,module);return instance.exports;},
    print(){},printErr(){}});
  library.PDFiumExt_Init();return library;
}
