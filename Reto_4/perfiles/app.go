package main

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"time"

	"github.com/jackc/pgx/v5"
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

const swaggerHTML = `<!doctype html><html><head><title>Perfiles Swagger</title><link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css"></head><body><div id="swagger-ui"></div><script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script><script>SwaggerUIBundle({url:'/perfiles/openapi.json',dom_id:'#swagger-ui'})</script></body></html>`
const openapi = `{"openapi":"3.0.3","info":{"title":"Perfiles Service","version":"4.0.0"},"paths":{"/perfiles":{"get":{"responses":{"200":{"description":"Perfiles"}}}},"/perfiles/{empleadoId}":{"get":{"parameters":[{"in":"path","name":"empleadoId","required":true,"schema":{"type":"string"}}],"responses":{"200":{"description":"Perfil"},"404":{"description":"No encontrado"}}},"put":{"parameters":[{"in":"path","name":"empleadoId","required":true,"schema":{"type":"string"}}],"requestBody":{"required":true,"content":{"application/json":{"schema":{"$ref":"#/components/schemas/PerfilUpdate"}}}},"responses":{"200":{"description":"Actualizado"},"400":{"description":"Entrada invalida"},"404":{"description":"No encontrado"}}}}},"components":{"schemas":{"PerfilUpdate":{"type":"object","properties":{"telefono":{"type":"string"},"direccion":{"type":"string"},"ciudad":{"type":"string"},"biografia":{"type":"string"}},"additionalProperties":false}}}}`
