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

const put = (body) => ({ method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

test('actualiza nombre y descripcion conservando el id', async (t) => {
  let received;
  const request = await withApi(t, { actualizar: async (id, body) => (received = { id, ...body }) });
  const response = await request('/departamentos/IT', put({ id: 'IT', nombre: ' Tecnología ', descripcion: 'TI y plataformas' }));
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { id: 'IT', nombre: 'Tecnología', descripcion: 'TI y plataformas' });
  assert.deepEqual(received, { id: 'IT', nombre: 'Tecnología', descripcion: 'TI y plataformas' });
});

test('actualizar un departamento inexistente devuelve 404', async (t) => {
  const request = await withApi(t, { actualizar: async () => undefined });
  assert.equal((await request('/departamentos/NOPE', put({ nombre: 'x', descripcion: 'y' }))).status, 404);
});

for (const body of [{}, [], { nombre: 'x' }, { nombre: ' ', descripcion: 'y' }, { nombre: 'x', descripcion: 'y', extra: 1 },
  { id: 'OTRO', nombre: 'x', descripcion: 'y' }]) {
  test(`rechaza actualización inválida: ${JSON.stringify(body)}`, async (t) => {
    const request = await withApi(t, { actualizar: () => assert.fail('No debe persistir') });
    assert.equal((await request('/departamentos/IT', put(body))).status, 400);
  });
}

test('elimina un departamento y responde 404 si no existe', async (t) => {
  const existentes = new Set(['IT']);
  const request = await withApi(t, { eliminar: async (id) => existentes.delete(id) });
  const eliminado = await request('/departamentos/IT', { method: 'DELETE' });
  assert.equal(eliminado.status, 204);
  assert.equal(await eliminado.text(), '');
  assert.equal((await request('/departamentos/IT', { method: 'DELETE' })).status, 404);
});

test('cada respuesta identifica la instancia que la atendió', async (t) => {
  const request = await withApi(t, { listar: async () => [] });
  assert.ok((await request('/departamentos')).headers.get('x-instance-id'));
});
