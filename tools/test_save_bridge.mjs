import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { test } from 'node:test';

const script = fs.readFileSync(new URL('../app/src/shared/assets/native-save.js', import.meta.url), 'utf8');
function bridge(handler, additions = {}) {
  const channel = { postMessage(raw) {
    const message = JSON.parse(raw);
    if (message.action === 'ping') respond(message, {value: true});
    else handler(message, respond);
  } };
  function respond(message, result = {}) {
    queueMicrotask(() => channel.onmessage({data: JSON.stringify({id: message.id, ...result})}));
  }
  const context = { window: {}, AndroidDocuments: channel, DOMException, Blob, Uint8Array,
    ArrayBuffer, TextEncoder, btoa, Map, ...additions };
  context.window.AndroidDocuments = channel;
  vm.runInNewContext(script, context);
  return context.window;
}

test('the page confirms that its native request/reply channel is working', async () => {
  const window = bridge(() => {});
  assert.equal(window.artcraftNativeBridgeReady, false);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(window.artcraftNativeBridgeReady, true);
});

test('binary exports preserve every byte across chunk boundaries and await disk completion', async () => {
  const chunks = [];
  let finish;
  const window = bridge((message, respond) => {
    if (message.action === 'pick') respond(message, {value: 'save-token'});
    if (message.action === 'append') {
      assert.equal(message.token, 'save-token');
      chunks.push(Buffer.from(message.bytes, 'base64'));
      respond(message, {value: true});
    }
    if (message.action === 'finish') finish = () => respond(message, {value: true});
  });
  const bytes = Uint8Array.from({length: 150001}, (_, index) => index % 256);
  const handle = await window.showSaveFilePicker({suggestedName: 'test.docx'});
  const writer = await handle.createWritable();
  await writer.write(bytes.subarray(3, 150000));
  assert.deepEqual(Buffer.concat(chunks), Buffer.from(bytes.subarray(3, 150000)));
  assert.equal(chunks.length, 4);
  let closed = false;
  const closing = writer.close().then(() => { closed = true; });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(closed, false);
  finish();
  await closing;
  assert.equal(closed, true);
});

test('picker cancellation is AbortError, so WordCraft does not start fallback download', async () => {
  const window = bridge((message, respond) => respond(message, {error: 'Save cancelled', cancelled: true}));
  await assert.rejects(window.showSaveFilePicker(), {name: 'AbortError'});
});

test('disk errors reject close instead of reporting a successful save', async () => {
  const window = bridge((message, respond) => respond(message, message.action === 'pick'
    ? {value: 'save-token'} : {error: 'Storage is full'}));
  const writer = await (await window.showSaveFilePicker()).createWritable();
  await assert.rejects(writer.close(), /Storage is full/);
});

test('a failed chunk aborts the native transaction', async () => {
  const actions = [];
  const window = bridge((message, respond) => {
    actions.push(message.action);
    respond(message, message.action === 'pick' ? {value: 'save-token'}
      : message.action === 'append' ? {error: 'Storage is full'} : {value: true});
  });
  const writer = await (await window.showSaveFilePicker()).createWritable();
  await assert.rejects(writer.write(new Uint8Array([0, 255, 10])), /Storage is full/);
  assert.deepEqual(actions, ['pick', 'append', 'abort']);
});

test('legacy blob downloads reach Android save with the original filename and binary bytes', async () => {
  class Anchor {
    href = 'blob:local-export'; download = 'drawing.png';
    hasAttribute(name) { return name === 'download'; }
    click() { throw new Error('Unexpected browser download'); }
  }
  const bytes = Uint8Array.from([137, 80, 78, 71, 0, 255, 42]);
  const chunks = [];
  let finished;
  const saved = new Promise(resolve => { finished = resolve; });
  bridge((message, respond) => {
    if (message.action === 'pick') {
      assert.equal(message.name, 'drawing.png');
      respond(message, {value: 'token'});
    } else if (message.action === 'append') {
      chunks.push(Buffer.from(message.bytes, 'base64')); respond(message, {value: true});
    } else if (message.action === 'finish') {
      respond(message, {value: true}); finished();
    }
  }, {HTMLAnchorElement: Anchor, document: {addEventListener() {}},
    fetch: async url => { assert.equal(url, 'blob:local-export'); return {blob: async () => new Blob([bytes], {type: 'image/png'})}; }});
  new Anchor().click();
  await saved;
  assert.deepEqual(Buffer.concat(chunks), Buffer.from(bytes));
});

test('ordinary links are left to the browser navigation handler', () => {
  let clicks = 0;
  class Anchor {
    href = 'https://example.com';
    hasAttribute() { return false; }
    click() { clicks++; }
  }
  bridge(() => { throw new Error('Unexpected native save'); },
    {HTMLAnchorElement: Anchor, document: {addEventListener() {}}});
  new Anchor().click();
  assert.equal(clicks, 1);
});
