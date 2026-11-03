(() => {
  window.AndroidDocuments = {
    onmessage: null,
    postMessage(message) {
      window.dispatchEvent(new CustomEvent('__artcraft_request', {detail: message}));
    }
  };
  window.addEventListener('__artcraft_reply', event => {
    window.AndroidDocuments.onmessage?.({data: event.detail});
  });
})();
