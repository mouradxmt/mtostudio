(() => {
  if (location.port !== '43873') return;
  window.addEventListener('__artcraft_request', event => {
    if (typeof event.detail !== 'string') return;
    let message;
    try { message = JSON.parse(event.detail); } catch { return; }
    browser.runtime.sendNativeMessage('AndroidDocuments', message).then(reply => {
      window.dispatchEvent(new CustomEvent('__artcraft_reply', {detail: reply}));
    });
  });
  // Startup diagnostics are also used by the isolated Android integration tests.
  let last = '';
  const timer = setInterval(() => {
    if (!document.body) return;
    const text = document.body.innerText.slice(0, 1800);
    const loading = [...document.querySelectorAll('[id$="_loading"],#loading')]
      .some(el => getComputedStyle(el).display !== 'none' && el.getClientRects().length > 0);
    const nativeBridge = window.wrappedJSObject.artcraftNativeBridgeReady === true;
    const ready = nativeBridge && !!document.querySelector('input:not([type=file]),textarea') && !!document.querySelector('canvas') && !loading;
    const error = /failed to (start|load)/i.test(text) && !text.includes('files may have failed');
    const state = JSON.stringify({ready, nativeBridge, error, text, origin: location.origin});
    if (state !== last) {
      last = state;
      browser.runtime.sendNativeMessage('AndroidDocuments', {id: 0, action: 'health', state: JSON.parse(state)}).catch(() => {});
    }
    if (ready || error) clearInterval(timer);
  }, 500);
})();
