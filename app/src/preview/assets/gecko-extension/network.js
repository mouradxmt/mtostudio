// Keep editor HTTP requests on this app's loopback asset server. The native updater is separate.
const ids = new Set(['photocraft','vectorcraft','filmcraft','lightcraft','pdfcraft','effectcraft','designcraft','figcraft','texturecraft','wordcraft','soundcraft','deckcraft','cadcraft','gridcraft','craft-anything']);
browser.webRequest.onBeforeRequest.addListener(details => {
  const url = new URL(details.url);
  const local = url.protocol === 'http:' && url.port === '43873' && ids.has(url.hostname.replace(/\.localhost$/, '')) && url.hostname.endsWith('.localhost');
  return {cancel: !local};
}, {urls: ['http://*/*', 'https://*/*', 'ws://*/*', 'wss://*/*']}, ['blocking']);
