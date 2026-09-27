import { test } from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { createApp } from '../src/app.js';

async function withApi(t, repository = {}) {
  const server = createApp(repository).listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => new Promise((resolve) => server.close(resolve)));
  const url = `http://127.0.0.1:${server.address().port}`;
  return (path, options) => fetch(url + path, options);
}
const department = { id: 'IT', nombre: 'Tecnología', descripcion: 'Departamento de TI' };
const post = (body) => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

test('alta, consulta y listado preservan el modelo completo', async (t) => {
  let stored;
  const request = await withApi(t, {
    crear: async (body) => (stored = body), obtener: async () => stored, listar: async () => [stored],
  });
  const created = await request('/departamentos', post(department));
  assert.equal(created.status, 201);
  assert.equal(created.headers.get('location'), '/departamentos/IT');
  assert.deepEqual(await created.json(), department);
  assert.deepEqual(await (await request('/departamentos/IT')).json(), department);
  assert.deepEqual(await (await request('/departamentos')).json(), [department]);
});

test('inexistente devuelve 404 descriptivo', async (t) => {
  const request = await withApi(t, { obtener: async () => undefined });
  const response = await request('/departamentos/MISSING');
  assert.equal(response.status, 404);
  assert.match((await response.json()).detail, /MISSING.*no existe/);
});

for (const body of [{}, [], { ...department, id: ' ' }, { ...department, nombre: 1 }, { ...department, extra: true }]) {
  test(`rechaza entrada inválida: ${JSON.stringify(body)}`, async (t) => {
    const request = await withApi(t, { crear: () => assert.fail('No debe persistir') });
    assert.equal((await request('/departamentos', post(body))).status, 400);
  });
}

test('JSON malformado devuelve 400', async (t) => {
  const request = await withApi(t);
  assert.equal((await request('/departamentos', { ...post({}), body: '{' })).status, 400);
});

for (const [code, status] of [['23505', 400], ['ECONNREFUSED', 503], ['XX000', 500]]) {
  test(`error ${code} devuelve ${status} sin filtrar detalles`, async (t) => {
    const request = await withApi(t, { crear: async () => { throw Object.assign(new Error('secret'), { code }); } });
    const response = await request('/departamentos', post(department));
    assert.equal(response.status, status);
    assert.doesNotMatch(await response.text(), /secret/);
  });
}

test('Swagger, assets locales y OpenAPI documentan el contrato', async (t) => {
  const request = await withApi(t);
  assert.match(await (await request('/docs/')).text(), /Swagger UI/);
  const asset = await request('/docs/swagger-ui-bundle.js');
  assert.equal(asset.status, 200);
  assert.ok((await asset.arrayBuffer()).byteLength > 0);
  const spec = await (await request('/openapi.json')).json();
  assert.deepEqual(spec.components.schemas.Departamento.required, ['id', 'nombre', 'descripcion']);
  for (const status of ['201', '400', '500', '503']) assert.ok(spec.paths['/departamentos'].post.responses[status]);
});
