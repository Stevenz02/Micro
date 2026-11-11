import pg from 'pg';
import { createApp } from './app.js';
import { databaseConfig } from './config.js';
import { Repository } from './repository.js';
import { logger } from './observability.js';

const pool = new pg.Pool(databaseConfig());
pool.on('error', (err) => logger.error('Conexión inactiva de PostgreSQL', { code: err.code || err.name }));
const port = Number(process.env.PORT || 8082);
const server = createApp(new Repository(pool)).listen(port, '0.0.0.0', () => {
  logger.info(`Departamentos escucha en puerto ${port}`);
});
for (const signal of ['SIGTERM', 'SIGINT']) {
  process.once(signal, () => server.close(async () => { await pool.end(); }));
}
