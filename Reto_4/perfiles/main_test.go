package main

import (
	"context"
	"errors"
	"github.com/jackc/pgx/v5"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

type memoryStore struct {
	perfil    Perfil
	readyErr  error
	listErr   error
	getErr    error
	updateErr error
}

func (m *memoryStore) Ready(context.Context) error { return m.readyErr }
func (m *memoryStore) List(context.Context) ([]Perfil, error) {
	return []Perfil{m.perfil}, m.listErr
}
func (m *memoryStore) Get(_ context.Context, id string) (*Perfil, error) {
	if m.getErr != nil {
		return nil, m.getErr
	}
	if id != m.perfil.EmpleadoID {
		return nil, pgx.ErrNoRows
	}
	p := m.perfil
	return &p, nil
}
func (m *memoryStore) Update(_ context.Context, id string, u PerfilUpdate) (*Perfil, error) {
	if m.updateErr != nil {
		return nil, m.updateErr
	}
	if id != m.perfil.EmpleadoID {
		return nil, pgx.ErrNoRows
	}
	m.perfil.Telefono = u.Telefono
	m.perfil.Direccion = u.Direccion
	m.perfil.Ciudad = u.Ciudad
	m.perfil.Biografia = u.Biografia
	p := m.perfil
	return &p, nil
}

func testStore() *memoryStore {
	return &memoryStore{perfil: Perfil{ID: "P1", EmpleadoID: "E1", Nombre: "Ana", Email: "ana@example.com", FechaCreacion: time.Now()}}
}

func TestGetAndList(t *testing.T) {
	h := routes(testStore())
	for _, path := range []string{"/health", "/perfiles", "/perfiles/E1", "/perfiles/openapi.json", "/perfiles/docs"} {
		r := httptest.NewRequest("GET", path, nil)
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		if w.Code != 200 {
			t.Fatalf("%s returned %d", path, w.Code)
		}
	}
}

func TestDependencyFailuresReturnServiceUnavailable(t *testing.T) {
	boom := errors.New("database unavailable")
	tests := []struct {
		name   string
		method string
		path   string
		body   string
		setup  func(*memoryStore)
	}{
		{"health", http.MethodGet, "/health", "", func(s *memoryStore) { s.readyErr = boom }},
		{"list", http.MethodGet, "/perfiles", "", func(s *memoryStore) { s.listErr = boom }},
		{"get", http.MethodGet, "/perfiles/E1", "", func(s *memoryStore) { s.getErr = boom }},
		{"update", http.MethodPut, "/perfiles/E1", `{}`, func(s *memoryStore) { s.updateErr = boom }},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := testStore()
			tt.setup(s)
			r := httptest.NewRequest(tt.method, tt.path, strings.NewReader(tt.body))
			w := httptest.NewRecorder()
			routes(s).ServeHTTP(w, r)
			if w.Code != http.StatusServiceUnavailable {
				t.Fatalf("expected 503, got %d", w.Code)
			}
		})
	}
}

func TestPutUpdatesOwnedFields(t *testing.T) {
	s := testStore()
	h := routes(s)
	r := httptest.NewRequest("PUT", "/perfiles/E1", strings.NewReader(`{"telefono":"123","direccion":"Calle 1","ciudad":"Armenia","biografia":"Bio"}`))
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	if w.Code != 200 || s.perfil.Telefono != "123" || s.perfil.Nombre != "Ana" {
		t.Fatalf("unexpected update: %d %+v", w.Code, s.perfil)
	}
}

func TestPutRejectsProtectedFields(t *testing.T) {
	h := routes(testStore())
	r := httptest.NewRequest("PUT", "/perfiles/E1", strings.NewReader(`{"archivado":true}`))
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	if w.Code != 400 {
		t.Fatalf("expected 400, got %d", w.Code)
	}
}

func TestPutRejectsMalformedOrInvalidJSON(t *testing.T) {
	for _, body := range []string{`{`, `{"telefono":123}`} {
		r := httptest.NewRequest("PUT", "/perfiles/E1", strings.NewReader(body))
		w := httptest.NewRecorder()
		routes(testStore()).ServeHTTP(w, r)
		if w.Code != 400 {
			t.Fatalf("body %q: expected 400, got %d", body, w.Code)
		}
	}
}

func TestMissingProfileReturns404(t *testing.T) {
	h := routes(testStore())
	for _, method := range []string{"GET", "PUT"} {
		body := strings.NewReader(`{}`)
		r := httptest.NewRequest(method, "/perfiles/no-existe", body)
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		if w.Code != 404 {
			t.Fatalf("%s: expected 404, got %d", method, w.Code)
		}
	}
}
