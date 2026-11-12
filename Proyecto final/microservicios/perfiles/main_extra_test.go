package main

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// failingStore simula la base de datos caida.
type failingStore struct{}

func (failingStore) Ready(context.Context) error            { return errors.New("db caida") }
func (failingStore) List(context.Context) ([]Perfil, error) { return nil, errors.New("db caida") }
func (failingStore) Get(context.Context, string) (*Perfil, error) {
	return nil, errors.New("db caida")
}
func (failingStore) Update(context.Context, string, PerfilUpdate) (*Perfil, error) {
	return nil, errors.New("db caida")
}

func call(h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, path, strings.NewReader(body))
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}

func TestHealthUpWithDependencies(t *testing.T) {
	brokerUp.Store(true)
	w := call(routes(testStore()), "GET", "/health", "")
	if w.Code != 200 || !strings.Contains(w.Body.String(), `"status":"UP"`) {
		t.Fatalf("expected UP, got %d %s", w.Code, w.Body.String())
	}
}

func TestHealthDownWhenDatabaseFails(t *testing.T) {
	brokerUp.Store(true)
	w := call(routes(failingStore{}), "GET", "/health", "")
	if w.Code != 503 || !strings.Contains(w.Body.String(), `"database":"DOWN"`) {
		t.Fatalf("expected database DOWN, got %d %s", w.Code, w.Body.String())
	}
}

func TestHealthDownWhenBrokerFails(t *testing.T) {
	brokerUp.Store(false)
	defer brokerUp.Store(true)
	w := call(routes(testStore()), "GET", "/health", "")
	if w.Code != 503 || !strings.Contains(w.Body.String(), `"messageBroker":"DOWN"`) {
		t.Fatalf("expected messageBroker DOWN, got %d %s", w.Code, w.Body.String())
	}
}

func TestDocumentationEndpoints(t *testing.T) {
	h := routes(testStore())
	spec := call(h, "GET", "/perfiles/openapi.json", "")
	if spec.Code != 200 || !strings.Contains(spec.Body.String(), `"openapi"`) {
		t.Fatalf("unexpected openapi response: %d", spec.Code)
	}
	docs := call(h, "GET", "/perfiles/docs", "")
	if docs.Code != 200 || !strings.Contains(docs.Body.String(), "swagger-ui") {
		t.Fatalf("unexpected docs response: %d", docs.Code)
	}
}

func TestDatabaseFailureReturns503(t *testing.T) {
	h := routes(failingStore{})
	if w := call(h, "GET", "/perfiles", ""); w.Code != 503 {
		t.Fatalf("list: expected 503, got %d", w.Code)
	}
	if w := call(h, "GET", "/perfiles/E1", ""); w.Code != 503 {
		t.Fatalf("get: expected 503, got %d", w.Code)
	}
	if w := call(h, "PUT", "/perfiles/E1", `{"ciudad":"Armenia"}`); w.Code != 503 {
		t.Fatalf("put: expected 503, got %d", w.Code)
	}
}

func TestPutRejectsInvalidBodies(t *testing.T) {
	h := routes(testStore())
	if w := call(h, "PUT", "/perfiles/E1", `{`); w.Code != 400 {
		t.Fatalf("malformed json: expected 400, got %d", w.Code)
	}
	if w := call(h, "PUT", "/perfiles/E1", `{"telefono":5}`); w.Code != 400 {
		t.Fatalf("wrong type: expected 400, got %d", w.Code)
	}
}

func TestPutUnknownProfileReturns404(t *testing.T) {
	w := call(routes(testStore()), "PUT", "/perfiles/no-existe", `{"ciudad":"Armenia"}`)
	if w.Code != 404 {
		t.Fatalf("expected 404, got %d", w.Code)
	}
}

func TestDatabaseURLRequiresEveryVariable(t *testing.T) {
	t.Setenv("DB_HOST", "database-perfiles")
	t.Setenv("DB_PORT", "5432")
	t.Setenv("DB_NAME", "perfiles")
	t.Setenv("DB_USER", "perfiles")
	t.Setenv("DB_PASSWORD", "clave-de-prueba")
	url, err := databaseURL()
	if err != nil || url != "postgres://perfiles:clave-de-prueba@database-perfiles:5432/perfiles" {
		t.Fatalf("unexpected url %q (%v)", url, err)
	}
	t.Setenv("DB_PASSWORD", " ")
	if _, err := databaseURL(); err == nil {
		t.Fatal("expected error when DB_PASSWORD is blank")
	}
}
