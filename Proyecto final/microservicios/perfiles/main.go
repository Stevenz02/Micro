package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"log/slog"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

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
	// Reto 8: formato común {status, service, checks}; 200 si UP, 503 si DOWN
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		checks := map[string]string{"database": "UP", "messageBroker": "UP"}
		if err := store.Ready(r.Context()); err != nil {
			checks["database"] = "DOWN"
		}
		if !brokerUp.Load() {
			checks["messageBroker"] = "DOWN"
		}
		status, code := "UP", 200
		if checks["database"] == "DOWN" || checks["messageBroker"] == "DOWN" {
			status, code = "DOWN", 503
		}
		jsonResponse(w, code, map[string]any{"status": status, "service": serviceName, "checks": checks})
	})
	mux.Handle("GET /metrics", metricsHandler())
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
		u, err := decodeUpdate(http.MaxBytesReader(w, r.Body, 64<<10))
		if err != nil {
			jsonResponse(w, 400, map[string]string{"detail": err.Error()})
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
	setupLogging()
	shutdown := setupTracing(context.Background())
	defer shutdown(context.Background())
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
	server := &http.Server{Addr: ":8083", Handler: instrument(routes(store)), ReadHeaderTimeout: 5 * time.Second}
	slog.Info("perfiles-service escucha en :8083")
	log.Fatal(server.ListenAndServe())
}

const swaggerHTML = `<!doctype html><html><head><title>Perfiles Swagger</title><link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css"></head><body><div id="swagger-ui"></div><script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script><script>SwaggerUIBundle({url:'/perfiles/openapi.json',dom_id:'#swagger-ui'})</script></body></html>`
const openapi = `{"openapi":"3.0.3","info":{"title":"Proyecto final - Perfiles","version":"1.0.0","description":"Perfil personal del empleado. Se crea y sincroniza por eventos (empleado.creado, empleado.actualizado) y se archiva con empleado.retirado. Cada empleado solo puede modificar su propio perfil: el API Gateway responde 403 si el token pertenece a otro empleado."},"servers":[{"url":"/"}],"paths":{"/perfiles":{"get":{"tags":["Perfiles"],"summary":"Listar perfiles","responses":{"200":{"description":"Perfiles registrados","content":{"application/json":{"schema":{"type":"array","items":{"$ref":"#/components/schemas/Perfil"}}}}},"401":{"description":"Token ausente o inválido","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Error"}}}},"503":{"description":"Base de datos no disponible","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Error"}}}}}}},"/perfiles/{empleadoId}":{"get":{"tags":["Perfiles"],"summary":"Obtener el perfil de un empleado","parameters":[{"in":"path","name":"empleadoId","required":true,"schema":{"type":"string"},"description":"Identificador del empleado dueño del perfil"}],"responses":{"200":{"description":"Perfil encontrado","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Perfil"}}}},"401":{"description":"Token ausente o inválido","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Error"}}}},"404":{"description":"Perfil no encontrado","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Error"}}}},"503":{"description":"Base de datos no disponible","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Error"}}}}}},"put":{"tags":["Perfiles"],"summary":"Actualizar el perfil propio","parameters":[{"in":"path","name":"empleadoId","required":true,"schema":{"type":"string"},"description":"Identificador del empleado dueño del perfil"}],"description":"Actualización parcial del perfil propio (contacto, dirección completa, foto, biografía y redes sociales).","requestBody":{"required":true,"content":{"application/json":{"schema":{"$ref":"#/components/schemas/PerfilUpdate"}}}},"responses":{"200":{"description":"Perfil actualizado","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Perfil"}}}},"400":{"description":"JSON inválido, campo protegido o desconocido, o valor fuera de las reglas","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Error"}}}},"401":{"description":"Token ausente o inválido","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Error"}}}},"403":{"description":"El perfil pertenece a otro empleado","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Error"}}}},"404":{"description":"Perfil no encontrado","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Error"}}}},"503":{"description":"Base de datos no disponible","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Error"}}}}}}},"/health":{"get":{"tags":["Salud"],"summary":"Estado del servicio y de sus dependencias","responses":{"200":{"description":"Servicio operativo","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Salud"}}}},"503":{"description":"Alguna dependencia está caída","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Salud"}}}}}}}},"components":{"schemas":{"Perfil":{"type":"object","properties":{"id":{"type":"string"},"empleadoId":{"type":"string","example":"E001"},"nombre":{"type":"string"},"apellido":{"type":"string"},"email":{"type":"string","format":"email"},"cargo":{"type":"string"},"area":{"type":"string"},"departamentoId":{"type":"string"},"telefono":{"type":"string"},"direccion":{"type":"string"},"ciudad":{"type":"string"},"codigoPostal":{"type":"string","example":"630001"},"biografia":{"type":"string"},"fotoUrl":{"type":"string","format":"uri","example":"https://cdn.empresa.com/fotos/E001.jpg"},"redesSociales":{"type":"object","additionalProperties":{"type":"string","format":"uri"},"example":{"linkedin":"https://www.linkedin.com/in/ana","github":"https://github.com/ana"}},"fechaCreacion":{"type":"string","format":"date-time"},"archivado":{"type":"boolean","description":"true cuando el empleado fue retirado"}}},"PerfilUpdate":{"type":"object","additionalProperties":false,"minProperties":1,"description":"Actualización parcial: solo cambian los campos enviados; una cadena vacía borra el valor. Nombre, apellido, email, cargo, área y departamento los gestiona RR. HH. en Empleados y aquí son de solo lectura.","properties":{"telefono":{"type":"string","maxLength":20,"pattern":"^[0-9+()\\- ]{7,20}$","example":"3001234567"},"direccion":{"type":"string","maxLength":200,"example":"Calle 10 # 5-20"},"ciudad":{"type":"string","maxLength":100,"example":"Armenia"},"codigoPostal":{"type":"string","maxLength":10,"pattern":"^[A-Za-z0-9 -]{3,10}$","example":"630001"},"biografia":{"type":"string","maxLength":1000,"example":"Ingeniera de plataforma"},"fotoUrl":{"type":"string","format":"uri","maxLength":2048,"description":"URL http(s) de la foto de perfil","example":"https://cdn.empresa.com/fotos/E001.jpg"},"redesSociales":{"type":"object","description":"Reemplaza el conjunto completo. Claves admitidas: linkedin, github, x, instagram, facebook, sitioWeb.","additionalProperties":{"type":"string","format":"uri"},"example":{"linkedin":"https://www.linkedin.com/in/ana","github":"https://github.com/ana"}}}},"Error":{"type":"object","required":["detail"],"properties":{"detail":{"type":"string"}}},"Salud":{"type":"object","required":["status","service","checks"],"properties":{"status":{"type":"string","enum":["UP","DOWN"]},"service":{"type":"string"},"checks":{"type":"object","additionalProperties":{"type":"string","enum":["UP","DOWN"]}}}}}}}`
