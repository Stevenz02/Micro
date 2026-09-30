package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type Perfil struct {
	ID             string    `json:"id"`
	EmpleadoID     string    `json:"empleadoId"`
	Nombre         string    `json:"nombre"`
	Apellido       string    `json:"apellido"`
	Email          string    `json:"email"`
	Cargo          string    `json:"cargo"`
	Area           string    `json:"area"`
	DepartamentoID string    `json:"departamentoId"`
	Telefono       string    `json:"telefono"`
	Direccion      string    `json:"direccion"`
	Ciudad         string    `json:"ciudad"`
	Biografia      string    `json:"biografia"`
	FechaCreacion  time.Time `json:"fechaCreacion"`
	Archivado      bool      `json:"archivado"`
}

type PerfilUpdate struct {
	Telefono  string `json:"telefono"`
	Direccion string `json:"direccion"`
	Ciudad    string `json:"ciudad"`
	Biografia string `json:"biografia"`
}

type Store interface {
	Ready(context.Context) error
	List(context.Context) ([]Perfil, error)
	Get(context.Context, string) (*Perfil, error)
	Update(context.Context, string, PerfilUpdate) (*Perfil, error)
}

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

func jsonResponse(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func routes(store Store) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		if err := store.Ready(r.Context()); err != nil {
			jsonResponse(w, 503, map[string]string{"detail": "Base de datos no disponible"})
			return
		}
		jsonResponse(w, 200, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("GET /perfiles/openapi.json", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(openapi))
	})
	mux.HandleFunc("GET /perfiles/docs", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		_, _ = w.Write([]byte(swaggerHTML))
	})
	mux.HandleFunc("GET /perfiles", func(w http.ResponseWriter, r *http.Request) {
		items, err := store.List(r.Context())
		if err != nil {
			jsonResponse(w, 503, map[string]string{"detail": "Base de datos no disponible"})
			return
		}
		jsonResponse(w, 200, items)
	})
	mux.HandleFunc("GET /perfiles/{empleadoId}", func(w http.ResponseWriter, r *http.Request) {
		p, err := store.Get(r.Context(), r.PathValue("empleadoId"))
		if errors.Is(err, pgx.ErrNoRows) {
			jsonResponse(w, 404, map[string]string{"detail": "Perfil no encontrado"})
			return
		}
		if err != nil {
			jsonResponse(w, 503, map[string]string{"detail": "Base de datos no disponible"})
			return
		}
		jsonResponse(w, 200, p)
	})
	mux.HandleFunc("PUT /perfiles/{empleadoId}", func(w http.ResponseWriter, r *http.Request) {
		var raw map[string]json.RawMessage
		dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, 64<<10))
		if err := dec.Decode(&raw); err != nil {
			jsonResponse(w, 400, map[string]string{"detail": "JSON invalido"})
			return
		}
		allowed := map[string]bool{"telefono": true, "direccion": true, "ciudad": true, "biografia": true}
		for key := range raw {
			if !allowed[key] {
				jsonResponse(w, 400, map[string]string{"detail": "Campo protegido o desconocido: " + key})
				return
			}
		}
		data, _ := json.Marshal(raw)
		var u PerfilUpdate
		if err := json.Unmarshal(data, &u); err != nil {
			jsonResponse(w, 400, map[string]string{"detail": "Campos invalidos"})
			return
		}
		p, err := store.Update(r.Context(), r.PathValue("empleadoId"), u)
		if errors.Is(err, pgx.ErrNoRows) {
			jsonResponse(w, 404, map[string]string{"detail": "Perfil no encontrado"})
			return
		}
		if err != nil {
			jsonResponse(w, 503, map[string]string{"detail": "Base de datos no disponible"})
			return
		}
		jsonResponse(w, 200, p)
	})
	return mux
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

const swaggerHTML = `<!doctype html><html><head><title>Perfiles Swagger</title><link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css"></head><body><div id="swagger-ui"></div><script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script><script>SwaggerUIBundle({url:'/perfiles/openapi.json',dom_id:'#swagger-ui'})</script></body></html>`
const openapi = `{"openapi":"3.0.3","info":{"title":"Perfiles Service","version":"4.0.0"},"paths":{"/perfiles":{"get":{"responses":{"200":{"description":"Perfiles"}}}},"/perfiles/{empleadoId}":{"get":{"parameters":[{"in":"path","name":"empleadoId","required":true,"schema":{"type":"string"}}],"responses":{"200":{"description":"Perfil"},"404":{"description":"No encontrado"}}},"put":{"parameters":[{"in":"path","name":"empleadoId","required":true,"schema":{"type":"string"}}],"requestBody":{"required":true,"content":{"application/json":{"schema":{"$ref":"#/components/schemas/PerfilUpdate"}}}},"responses":{"200":{"description":"Actualizado"},"400":{"description":"Entrada invalida"},"404":{"description":"No encontrado"}}}}},"components":{"schemas":{"PerfilUpdate":{"type":"object","properties":{"telefono":{"type":"string"},"direccion":{"type":"string"},"ciudad":{"type":"string"},"biografia":{"type":"string"}},"additionalProperties":false}}}}`
