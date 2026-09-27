export class Repository {
  constructor(pool) { this.pool = pool; }
  async ready() { await this.pool.query('SELECT id FROM departamentos LIMIT 1'); }
  async crear({ id, nombre, descripcion }) {
    const result = await this.pool.query(
      'INSERT INTO departamentos (id, nombre, descripcion) VALUES ($1, $2, $3) RETURNING id, nombre, descripcion',
      [id, nombre, descripcion],
    );
    return result.rows[0];
  }
  async obtener(id) {
    return (await this.pool.query('SELECT id, nombre, descripcion FROM departamentos WHERE id = $1', [id])).rows[0];
  }
  async listar() {
    return (await this.pool.query('SELECT id, nombre, descripcion FROM departamentos ORDER BY id')).rows;
  }
}
