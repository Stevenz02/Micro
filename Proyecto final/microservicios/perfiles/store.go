package main

// Adaptador SQL de perfiles (PostgreSQL). Requiere una base real: lo validan la suite BDD y
// el health check, no las pruebas unitarias (que usan un Store en memoria).

import (
	"context"
	"encoding/json"

	"github.com/jackc/pgx/v5/pgxpool"
)

type PostgresStore struct{ pool *pgxpool.Pool }

// redes_sociales se lee como texto y se decodifica en Go: evita depender del codec JSONB.
const columns = `id, empleado_id, nombre, apellido, email, cargo, area, departamento_id, telefono, direccion, ciudad, codigo_postal, biografia, foto_url, redes_sociales::text, fecha_creacion, archivado`

// scanner lo cumplen pgx.Row y pgx.Rows.
type scanner interface{ Scan(dest ...any) error }

func scanPerfil(row scanner) (*Perfil, error) {
	var p Perfil
	var redes string
	if err := row.Scan(&p.ID, &p.EmpleadoID, &p.Nombre, &p.Apellido, &p.Email, &p.Cargo, &p.Area, &p.DepartamentoID,
		&p.Telefono, &p.Direccion, &p.Ciudad, &p.CodigoPostal, &p.Biografia, &p.FotoURL, &redes, &p.FechaCreacion, &p.Archivado); err != nil {
		return nil, err
	}
	p.RedesSociales = map[string]string{}
	if err := json.Unmarshal([]byte(redes), &p.RedesSociales); err != nil {
		return nil, err
	}
	return &p, nil
}

func (s *PostgresStore) EnsureSchema(ctx context.Context) error {
	for _, statement := range []string{
		`ALTER TABLE perfiles ADD COLUMN IF NOT EXISTS apellido TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE perfiles ADD COLUMN IF NOT EXISTS cargo TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE perfiles ADD COLUMN IF NOT EXISTS area TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE perfiles ADD COLUMN IF NOT EXISTS departamento_id TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE perfiles ADD COLUMN IF NOT EXISTS codigo_postal TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE perfiles ADD COLUMN IF NOT EXISTS foto_url TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE perfiles ADD COLUMN IF NOT EXISTS redes_sociales JSONB NOT NULL DEFAULT '{}'::jsonb`,
	} {
		if _, err := s.pool.Exec(ctx, statement); err != nil {
			return err
		}
	}
	return nil
}

func (s *PostgresStore) Ready(ctx context.Context) error { return s.pool.Ping(ctx) }

func (s *PostgresStore) List(ctx context.Context) ([]Perfil, error) {
	rows, err := s.pool.Query(ctx, `SELECT `+columns+` FROM perfiles ORDER BY empleado_id`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []Perfil{}
	for rows.Next() {
		p, err := scanPerfil(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, *p)
	}
	return items, rows.Err()
}

func (s *PostgresStore) Get(ctx context.Context, id string) (*Perfil, error) {
	return scanPerfil(s.pool.QueryRow(ctx, `SELECT `+columns+` FROM perfiles WHERE empleado_id=$1`, id))
}

// Update aplica solo los campos presentes (COALESCE conserva los demás).
func (s *PostgresStore) Update(ctx context.Context, id string, u PerfilUpdate) (*Perfil, error) {
	var redes *string
	if u.RedesSociales != nil {
		encoded, err := json.Marshal(u.RedesSociales)
		if err != nil {
			return nil, err
		}
		text := string(encoded)
		redes = &text
	}
	return scanPerfil(s.pool.QueryRow(ctx, `UPDATE perfiles SET
			telefono=COALESCE($1,telefono), direccion=COALESCE($2,direccion), ciudad=COALESCE($3,ciudad),
			codigo_postal=COALESCE($4,codigo_postal), biografia=COALESCE($5,biografia), foto_url=COALESCE($6,foto_url),
			redes_sociales=COALESCE($7::text::jsonb,redes_sociales)
		WHERE empleado_id=$8 RETURNING `+columns,
		u.Telefono, u.Direccion, u.Ciudad, u.CodigoPostal, u.Biografia, u.FotoURL, redes, id))
}
