import pg from 'pg';
import { createApp } from './app.js';
import { databaseConfig } from './config.js';
import { Repository } from './repository.js';

const pool = new pg.Pool(databaseConfig());
pool.on('error', (err) => console.error('Conexión inactiva de PostgreSQL:', err.code || err.name));
const port = Number(process.env.PORT || 8081);
const server = createApp(new Repository(pool)).listen(port, '0.0.0.0', () => {
  console.log(`Departamentos escucha en puerto ${port}`);
});
for (const signal of ['SIGTERM', 'SIGINT']) {
  process.once(signal, () => server.close(async () => { await pool.end(); }));
}
