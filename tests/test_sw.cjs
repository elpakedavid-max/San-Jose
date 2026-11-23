const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const entries = new Map();
const cacheKey = req => typeof req === 'string' ? req : req.url;
const cache = {
  put: async (req, res) => entries.set(cacheKey(req), res),
  match: async req => entries.get(cacheKey(req))?.clone(),
};
entries.set('./index.html', new Response('Página sin conexión'));
let fetchHandler;
let response = new Response('Error del servidor', {status: 503});
vm.runInNewContext(fs.readFileSync('sw.js', 'utf8'), {
  self: {
    location: {origin: 'https://example.test'},
    addEventListener(name, handler) { if (name === 'fetch') fetchHandler = handler; },
  },
  caches: {...cache, open: async () => cache},
  fetch: async () => { if (!response) throw new Error('sin conexión'); return response.clone(); },
  URL, Response,
});

function request(path, mode = 'cors', headers = {}, destination = '') {
  let result;
  fetchHandler({
    request: {method: 'GET', url: 'https://example.test/' + path, mode, headers: new Headers(headers), destination},
    respondWith(value) { result = value; },
  });
  return result;
}

(async () => {
  entries.set('https://example.test/config.js', new Response('config válida'));
  assert.equal((await request('config.js')).status, 503);
  response = null;
  assert.equal(await (await request('config.js')).text(), 'config válida');
  assert.equal(await (await request('partidos', 'navigate')).text(), 'Página sin conexión');
  assert.equal((await request('ausente.js')).type, 'error');
  assert.equal(request('video.mp4', 'cors', {Range: 'bytes=0-'}), undefined);
  assert.equal(request('audio.mp3', 'cors', {}, 'audio'), undefined);
})().catch(err => { console.error(err); process.exitCode = 1; });
