/* This page is loaded in an opaque-origin iframe. Code runs in a disposable worker. */
(() => {
  if (self === parent || self.origin !== 'null') return;

  function runtime() {
    let started = false;
    const send = self.postMessage.bind(self);
    self.onmessage = async ({data}) => {
      if (started) return;
      started = true;
      const {language, code} = data;
      let stdout = '', stderr = '', plots = [];
      try {
        if (language === 'python') {
          const url = 'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/';
          importScripts(url + 'pyodide.js');
          const py = await loadPyodide({indexURL: url});
          py.setStdout({batched: s => { if (stdout.length < 32000) stdout += s.slice(0, 32000) + '\n'; }});
          py.setStderr({batched: s => { if (stderr.length < 8000) stderr += s.slice(0, 8000) + '\n'; }});
          await py.loadPackagesFromImports(code);
          py.globals.set('_hl_plot', (x, y, label) => {
            if (plots.length < 6) plots.push({x: x.toJs(), y: y.toJs(), label: String(label).slice(0, 80)});
          });
          await py.runPythonAsync(`
from itertools import islice as _hl_slice
def plot(x, y, label=""):
    _hl_plot(list(map(float, _hl_slice(iter(x), 2000))), list(map(float, _hl_slice(iter(y), 2000))), label)
`);
          send({phase: 'running'});
          const result = await py.runPythonAsync(code);
          if (typeof result?.destroy === 'function') result.destroy();
        } else if (language === 'c') {
          const [{runClang}, {WASI, File, OpenFile, ConsoleStdout}] = await Promise.all([
            import('https://cdn.jsdelivr.net/npm/@yowasp/clang@22.0.0-git20695-13/gen/bundle.js'),
            import('https://cdn.jsdelivr.net/npm/@bjorn3/browser_wasi_shim@0.4.2/dist/index.js')
          ]);
          const decoder = new TextDecoder();
          const files = await runClang(['clang', '-std=c17', '-O1', 'main.c', '-o', 'main.wasm'], {'main.c': code}, {
            decodeASCII: false,
            stdout: null,
            stderr: b => { if (b && stderr.length < 8000) stderr += decoder.decode(b, {stream: true}).slice(0, 8000); },
            fetchProgress: () => {}
          });
          send({phase: 'running'});
          const outDecoder = new TextDecoder(), errDecoder = new TextDecoder();
          const wasi = new WASI(['simulation'], [], [
            new OpenFile(new File(new Uint8Array())),
            new ConsoleStdout(bytes => { if (stdout.length < 32000) stdout += outDecoder.decode(bytes, {stream:true}).slice(0, 32000); }),
            new ConsoleStdout(bytes => { if (stderr.length < 8000) stderr += errDecoder.decode(bytes, {stream:true}).slice(0, 8000); })
          ]);
          const {instance} = await WebAssembly.instantiate(files['main.wasm'], {wasi_snapshot_preview1: wasi.wasiImport});
          const status = wasi.start(instance);
          stdout += outDecoder.decode(); stderr += errDecoder.decode();
          if (status) throw new Error('C exit code ' + status);
          const rows = stdout.split('\n').slice(0, 2001).map(line => line.trim())
            .filter(line => /^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?,\s*[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(line))
            .map(line => line.split(',').map(Number));
          if (rows.length > 1) plots = [{x: rows.map(r => r[0]), y: rows.map(r => r[1]), label: ''}];
        } else throw new Error('Unsupported runtime');
        send({phase: 'done', stdout: stdout.slice(0, 32000), stderr: stderr.slice(0, 8000), plots});
      } catch (error) {
        send({phase: 'done', stdout: stdout.slice(0, 32000), error: (stderr + '\n' + String(error?.message || error)).trim().slice(0, 8000)});
      }
    };
  }

  const workerUrl = URL.createObjectURL(new Blob(['(' + runtime.toString() + ')();'], {type: 'text/javascript'}));
  let worker, parentOrigin;
  const forward = data => parent.postMessage(data, parentOrigin);
  addEventListener('message', e => {
    if (e.source !== parent || e.origin === 'null' || e.data?.type !== 'workshop-run' || worker) return;
    if (typeof e.data.code !== 'string' || e.data.code.length > 60000 || !['python','c'].includes(e.data.language)) return;
    parentOrigin = e.origin;
    try {
      worker = new Worker(workerUrl);
      worker.onmessage = ev => forward(ev.data);
      worker.onerror = event => forward({phase: 'done', error: event.message || 'Browser runtime failed to start'});
      worker.postMessage({language: e.data.language, code: e.data.code});
    } catch (error) {
      forward({phase: 'done', error: String(error?.message || error)});
    }
  });
  addEventListener('pagehide', () => { worker?.terminate(); URL.revokeObjectURL(workerUrl); });
  parent.postMessage({phase: 'ready'}, '*');
})();
