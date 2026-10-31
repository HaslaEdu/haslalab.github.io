let shared = null;
/** Creates a worker only after a scanner is opened. Images are transferred in
 * memory; the only worker fetches are versioned same-origin public assets. */
export function createDocumentDetector({ workerFactory = url => new Worker(url, { type: 'module' }), timeoutMs = 45000 } = {}) {
  let worker = null, sequence = 0, disposed = false, workerRetryAt = 0;
  const pending = new Map(), subscribers = new Set();
  const rejectAll = error => { for (const item of pending.values()) { clearTimeout(item.timer); item.cleanup(); item.reject(error); } pending.clear(); };
  function start(retry = false) {
    if (disposed) throw new Error('document_detector_disposed');
    if (worker) return worker;
    if (!retry && Date.now() < workerRetryAt) throw new Error('document_worker_unavailable');
    worker = workerFactory(new URL('./document-worker.mjs?v=5c3425ad59a1', import.meta.url));
    worker.onmessage = event => {
      const value = event.data;
      if (value.type === 'progress') { for (const subscriber of subscribers) subscriber(value.stage); return; }
      const item = pending.get(value.id); if (!item) return;
      pending.delete(value.id); clearTimeout(item.timer); item.cleanup();
      if (value.type === 'error') item.reject(new Error(value.code)); else item.resolve(value.result || { ready: true });
    };
    worker.onerror = () => { rejectAll(new Error('document_worker_unavailable')); worker?.terminate(); worker = null; workerRetryAt = Date.now() + 5000; };
    return worker;
  }
  function request(type, payload = {}, { signal, onProgress } = {}) {
    if (signal?.aborted) return Promise.reject(new DOMException('Aborted', 'AbortError'));
    if (pending.size >= 2) return Promise.reject(new Error('document_detector_busy'));
    const active = start(payload.retry === true), id = ++sequence;
    return new Promise((resolve, reject) => {
      const abort = () => { const item = pending.get(id); if (!item) return; pending.delete(id); clearTimeout(item.timer); item.cleanup(); try { active.postMessage({ type: 'cancel', id }); } catch {} reject(new DOMException('Aborted', 'AbortError')); };
      if (onProgress) subscribers.add(onProgress);
      const cleanup = () => { signal?.removeEventListener('abort', abort); if (onProgress) subscribers.delete(onProgress); };
      const timer = setTimeout(() => { pending.delete(id); cleanup(); reject(new Error('document_detector_timeout')); active.terminate(); if (worker === active) worker = null; rejectAll(new Error('document_detector_timeout')); }, timeoutMs);
      pending.set(id, { resolve, reject, timer, cleanup }); signal?.addEventListener('abort', abort, { once: true });
      try { active.postMessage({ type, id, ...payload }, payload.bitmap ? [payload.bitmap] : []); }
      catch (error) { pending.delete(id); clearTimeout(timer); cleanup(); try { payload.bitmap?.close(); } catch {} reject(error); }
    });
  }
  return {
    warm: options => request('warm', { retry: options?.retry === true }, options),
    async detect(canvas, options) { const bitmap = await createImageBitmap(canvas); try { return await request('detect', { bitmap, retry: options?.retry === true }, options); } catch (error) { try { bitmap.close(); } catch {} throw error; } },
    async render(canvas, settings, options) { const bitmap = await createImageBitmap(canvas); try { return await request('render', { bitmap, ...settings }, options); } catch (error) { try { bitmap.close(); } catch {} throw error; } },
    dispose() { disposed = true; rejectAll(new Error('document_detector_disposed')); worker?.terminate(); worker = null; subscribers.clear(); },
  };
}
export const getDocumentDetector = () => shared || (shared = createDocumentDetector());
export function disposeDocumentDetector() { shared?.dispose(); shared = null; }
