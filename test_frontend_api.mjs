import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import vm from 'node:vm';

async function loadApi({ apiBaseUrl, location = 'http://localhost:5500/upload.html' } = {}) {
  const source = await readFile(new URL('./frontend/js/api.js', import.meta.url), 'utf8');
  const context = {
    window: {
      ...(apiBaseUrl ? { PYQ_API_BASE_URL: apiBaseUrl } : {}),
      location: new URL(location)
    },
    fetch: async () => ({ ok: true, status: 200, json: async () => ({}) }),
    URLSearchParams,
    console
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  return context;
}

test('local development defaults to the Flask API on localhost', async () => {
  const context = await loadApi();

  assert.equal(context.window.API_CONFIG.baseUrl, 'http://localhost:5000/api');
});

test('production uses the configured Vercel API base URL', async () => {
  const context = await loadApi({
    apiBaseUrl: 'https://smart-pyq-api.onrender.com/api',
    location: 'https://smart-pyq.vercel.app/index.html'
  });

  assert.equal(context.window.API_CONFIG.baseUrl, 'https://smart-pyq-api.onrender.com/api');
});

test('production without an override uses the same-origin API path', async () => {
  const context = await loadApi({ location: 'https://smart-pyq.vercel.app/index.html' });

  assert.equal(context.window.API_CONFIG.baseUrl, '/api');
});

test('uploadPaper sends the admin session credentials and CSRF token', async () => {
  const source = await readFile(new URL('./frontend/js/api.js', import.meta.url), 'utf8');
  let request;
  const context = {
    window: { PYQ_API_BASE_URL: 'http://localhost:5000/api', location: new URL('http://localhost:5500/upload.html') },
    fetch: async (...args) => {
      request = args;
      return { ok: true, status: 201, json: async () => ({ data: { question_count: 1 } }) };
    },
    URLSearchParams,
    console
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  context.window.PYQAuth.csrfToken = 'csrf-token-from-admin-session';

  await context.window.PYQApi.uploadPaper({ pdf: 'paper.pdf' });

  assert.equal(request[0], 'http://localhost:5000/api/papers');
  assert.equal(request[1].method, 'POST');
  assert.deepEqual({ ...request[1].body }, { pdf: 'paper.pdf' });
  assert.equal(request[1].headers['X-CSRF-Token'], 'csrf-token-from-admin-session');
  assert.equal(request[1].credentials, 'include');
});
