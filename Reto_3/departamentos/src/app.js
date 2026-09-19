import express from 'express';
import swaggerUi from 'swagger-ui-express';
import { openapi } from './openapi.js';

export function createApp(repository) {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: '64kb' }));
  app.get('/openapi.json', (req, res) => res.json(openapi));
  app.use('/docs', swaggerUi.serve, swaggerUi.setup(openapi));
  app.get('/health', async (req, res) => {
    await repository.ready();
    res.json({ status: 'ok' });
  });
  app.post('/departamentos', async (req, res) => {
    const fields = ['id', 'nombre', 'descripcion'];
    if (!req.body || Array.isArray(req.body) ||
        fields.some((key) => typeof req.body[key] !== 'string' || !req.body[key].trim()) ||
        Object.keys(req.body).some((key) => !fields.includes(key))) {
      return res.status(400).json({ detail: 'Se requieren únicamente id, nombre y descripcion como textos no vacíos' });
    }
    const body = Object.fromEntries(fields.map((key) => [key, req.body[key].trim()]));
    const department = await repository.crear(body);
    res.location(`/departamentos/${encodeURIComponent(department.id)}`).status(201).json(department);
  });
  app.get('/departamentos', async (req, res) => res.json(await repository.listar()));
  app.get('/departamentos/:id', async (req, res) => {
    const department = await repository.obtener(req.params.id);
    if (!department) return res.status(404).json({ detail: `El departamento con id ${req.params.id} no existe` });
    res.json(department);
  });
  app.use((req, res) => res.status(404).json({ detail: 'Recurso no encontrado' }));
  app.use((err, req, res, next) => {
    if (res.headersSent) return next(err);
    if (err.code === '23505') return res.status(400).json({ detail: 'El id del departamento ya está registrado' });
    if (err.type === 'entity.parse.failed') return res.status(400).json({ detail: 'El cuerpo debe contener JSON válido' });
    if (err.type === 'entity.too.large') return res.status(413).json({ detail: 'Cuerpo demasiado grande' });
    const unavailable = ['ECONNREFUSED', 'ENOTFOUND', 'ETIMEDOUT', '57P01', '57P03', '53300'].includes(err.code)
      || err.code?.startsWith('08') || /connection.*(timeout|terminated)|timeout.*connect/i.test(err.message);
    console.error('Error de persistencia:', err.code || err.name);
    res.status(unavailable ? 503 : 500).json({ detail: 'No se pudo completar la operación en la base de datos' });
  });
  return app;
}
