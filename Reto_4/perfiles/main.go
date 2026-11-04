package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

type PostgresStore struct{ pool *pgxpool.Pool }

const columns = `id, empleado_id, nombre, apellido, email, cargo, area, departamento_id, telefono, direccion, ciudad, biografia, fecha_creacion, archivado`

func (s *PostgresStore) EnsureSchema(ctx context.Context) error {
	for _, statement := range []string{
		`ALTER TABLE perfiles ADD COLUMN IF NOT EXISTS apellido TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE perfiles ADD COLUMN IF NOT EXISTS cargo TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE perfiles ADD COLUMN IF NOT EXISTS area TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE perfiles ADD COLUMN IF NOT EXISTS departamento_id TEXT NOT NULL DEFAULT ''`,
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
		var p Perfil
		if err := rows.Scan(&p.ID, &p.EmpleadoID, &p.Nombre, &p.Apellido, &p.Email, &p.Cargo, &p.Area, &p.DepartamentoID, &p.Telefono, &p.Direccion, &p.Ciudad, &p.Biografia, &p.FechaCreacion, &p.Archivado); err != nil {
			return nil, err
		}
		items = append(items, p)
	}
	return items, rows.Err()
}
func (s *PostgresStore) Get(ctx context.Context, id string) (*Perfil, error) {
	var p Perfil
	err := s.pool.QueryRow(ctx, `SELECT `+columns+` FROM perfiles WHERE empleado_id=$1`, id).Scan(&p.ID, &p.EmpleadoID, &p.Nombre, &p.Apellido, &p.Email, &p.Cargo, &p.Area, &p.DepartamentoID, &p.Telefono, &p.Direccion, &p.Ciudad, &p.Biografia, &p.FechaCreacion, &p.Archivado)
	if err != nil {
		return nil, err
	}
	return &p, nil
}
func (s *PostgresStore) Update(ctx context.Context, id string, u PerfilUpdate) (*Perfil, error) {
	var p Perfil
	err := s.pool.QueryRow(ctx, `UPDATE perfiles SET telefono=$1,direccion=$2,ciudad=$3,biografia=$4 WHERE empleado_id=$5 RETURNING `+columns,
		u.Telefono, u.Direccion, u.Ciudad, u.Biografia, id).Scan(&p.ID, &p.EmpleadoID, &p.Nombre, &p.Apellido, &p.Email, &p.Cargo, &p.Area, &p.DepartamentoID, &p.Telefono, &p.Direccion, &p.Ciudad, &p.Biografia, &p.FechaCreacion, &p.Archivado)
	if err != nil {
		return nil, err
	}
	return &p, nil
}

func databaseURL() (string, error) {
	keys := []string{"DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"}
	for _, k := range keys {
		if strings.TrimSpace(os.Getenv(k)) == "" {
			return "", errors.New("falta " + k)
		}
	}
	return fmt.Sprintf("postgres://%s:%s@%s:%s/%s", os.Getenv("DB_USER"), os.Getenv("DB_PASSWORD"), os.Getenv("DB_HOST"), os.Getenv("DB_PORT"), os.Getenv("DB_NAME")), nil
}

func main() {
	url, err := databaseURL()
	if err != nil {
		log.Fatal(err)
	}
	pool, err := pgxpool.New(context.Background(), url)
	if err != nil {
		log.Fatal(err)
	}
	defer pool.Close()
	store := &PostgresStore{pool}
	if err := store.EnsureSchema(context.Background()); err != nil {
		log.Fatal(err)
	}
	go consumeEvents(pool)
	server := &http.Server{Addr: ":8083", Handler: routes(store), ReadHeaderTimeout: 5 * time.Second}
	log.Fatal(server.ListenAndServe())
}
