/* Adapt WordCraft's existing asynchronous save API to Android's document picker.
 * A save completes only after Android has closed the destination stream. */
(() => {
  'use strict';
  if (!window.AndroidDocuments) return;
  // These eframe web builds handle both PointerEvent and TouchEvent. Android sends
  // both for a finger: craft-menu consequently toggles twice and closes immediately.
  // Keep the original touch path (including multi-touch/drag/cancel), and leave
  // mouse and pen pointer events alone. Limit the filter to the editor canvas.
  if (typeof document !== 'undefined' && typeof HTMLCanvasElement !== 'undefined') {
    for (const type of ['pointerdown', 'pointerup']) {
      document.addEventListener(type, event => {
        if (event.pointerType === 'touch' && event.target instanceof HTMLCanvasElement) {
          event.stopImmediatePropagation();
        }
      }, true);
    }
  }
  let sequence = 0;
  const pending = new Map();
  AndroidDocuments.onmessage = event => {
    const result = JSON.parse(event.data);
    const operation = pending.get(result.id);
    if (!operation) return;
    pending.delete(result.id);
    if (result.error) operation.reject(new DOMException(result.error, result.cancelled ? 'AbortError' : 'OperationError'));
    else operation.resolve(result.value);
  };
  function request(action, data = {}) {
    const id = ++sequence;
    return new Promise((resolve, reject) => {
      pending.set(id, {resolve, reject});
      try { AndroidDocuments.postMessage(JSON.stringify({id, action, ...data})); }
      catch (error) { pending.delete(id); reject(error); }
    });
  }
  window.artcraftNativeBridgeReady = false;
  request('ping').then(() => { window.artcraftNativeBridgeReady = true; }).catch(() => {});
  window.showSaveFilePicker = async options => {
    const token = await request('pick', {
      name: options?.suggestedName || 'Document.docx',
      mime: Object.keys(options?.types?.[0]?.accept || {})[0] || 'application/octet-stream'
    });
    return {
      kind: 'file',
      async createWritable() {
        let closed = false;
        return {
          async write(data) {
            if (closed) throw new DOMException('File is closed', 'InvalidStateError');
            const bytes = data instanceof Blob ? new Uint8Array(await data.arrayBuffer())
              : data instanceof ArrayBuffer ? new Uint8Array(data)
              : ArrayBuffer.isView(data) ? new Uint8Array(data.buffer, data.byteOffset, data.byteLength)
              : new TextEncoder().encode(String(data));
            try {
              for (let offset = 0; offset < bytes.length; offset += 49152) {
                const part = bytes.subarray(offset, offset + 49152);
                let binary = '';
                for (let i = 0; i < part.length; i++) binary += String.fromCharCode(part[i]);
                await request('append', {token, bytes: btoa(binary)});
              }
            } catch (error) {
              closed = true;
              await request('abort', {token}).catch(() => {});
              throw error;
            }
          },
          async close() {
            if (closed) throw new DOMException('File is closed', 'InvalidStateError');
            closed = true;
            await request('finish', {token});
          },
          async abort() {
            closed = true;
            await request('abort', {token});
          }
        };
      }
    };
  };
  // Older suite apps export by clicking a blob download instead of using a save picker.
  // Queue those downloads so only one Android destination picker is open at a time.
  let downloads = Promise.resolve();
  function saveDownload(anchor) {
    const url = anchor.href;
    if (!anchor.hasAttribute('download') || !url.startsWith('blob:')) return false;
    const name = anchor.download || 'Export';
    // Read immediately, before the app revokes the object URL after its click.
    const contents = fetch(url).then(response => response.blob());
    contents.catch(() => {});
    downloads = downloads.then(async () => {
      const blob = await contents;
      const handle = await window.showSaveFilePicker({suggestedName: name,
        types: [{accept: {[blob.type || 'application/octet-stream']: []}}]});
      const writer = await handle.createWritable();
      await writer.write(blob);
      await writer.close();
    }).catch(async error => {
      if (error.name !== 'AbortError') {
        await request('notice', {message: 'Could not save export: ' + error.message}).catch(() => {});
      }
    });
    return true;
  }
  if (typeof HTMLAnchorElement !== 'undefined') {
    const click = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function (...args) {
      if (!saveDownload(this)) return click.apply(this, args);
    };
    document.addEventListener('click', event => {
      const anchor = event.target.closest?.('a[download]');
      if (anchor && saveDownload(anchor)) event.preventDefault();
    }, true);
  }
  // Older Android WebViews cap WebGL textures below several upstream engines' minimum.
  // Explain that concrete startup failure without changing or overstating GPU capabilities.
  if (typeof MutationObserver !== 'undefined') {
    const observe = () => {
      const observer = new MutationObserver(() => {
        if (!/max_texture_dimension_2d[\s\S]*8192[\s\S]*4096/.test(document.body.innerText)) return;
        observer.disconnect();
        const help = document.createElement('p');
        help.textContent = 'This editor needs newer Android graphics support. Update Android System WebView. An Android upgrade or newer device may also be needed.';
        help.style.cssText = 'position:fixed;bottom:0;left:0;right:0;margin:0;padding:16px;background:#fff3cd;color:#332701;font:15px/1.4 system-ui;z-index:2147483647';
        help.setAttribute('role', 'alert');
        document.body.appendChild(help);
      });
      observer.observe(document.body, {childList: true, subtree: true});
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', observe, {once: true});
    else observe();
  }
})();
