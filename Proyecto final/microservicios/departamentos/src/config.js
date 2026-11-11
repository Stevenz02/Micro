export function databaseConfig(env = process.env) {
  for (const name of ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']) {
    if (!env[name]) throw new Error(`Falta variable ${name}`);
  }
  return {
    host: env.DB_HOST, port: Number(env.DB_PORT || 5432), database: env.DB_NAME,
    user: env.DB_USER, password: env.DB_PASSWORD,
    connectionTimeoutMillis: 5000, statement_timeout: 5000, max: 10,
  };
}
