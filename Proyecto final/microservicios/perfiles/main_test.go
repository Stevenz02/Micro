package main

import (
	"context"
	"github.com/jackc/pgx/v5"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

type memoryStore struct{ perfil Perfil }

func (m *memoryStore) Ready(context.Context) error            { return nil }
func (m *memoryStore) List(context.Context) ([]Perfil, error) { return []Perfil{m.perfil}, nil }
func (m *memoryStore) Get(_ context.Context, id string) (*Perfil, error) {
	if id != m.perfil.EmpleadoID {
		return nil, pgx.ErrNoRows
	}
	p := m.perfil
	return &p, nil
}
func (m *memoryStore) Update(_ context.Context, id string, u PerfilUpdate) (*Perfil, error) {
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
	for _, path := range []string{"/perfiles", "/perfiles/E1"} {
		r := httptest.NewRequest("GET", path, nil)
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		if w.Code != 200 {
			t.Fatalf("%s returned %d", path, w.Code)
		}
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

func TestMissingProfileReturns404(t *testing.T) {
	h := routes(testStore())
	r := httptest.NewRequest("GET", "/perfiles/no-existe", nil)
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	if w.Code != 404 {
		t.Fatalf("expected 404, got %d", w.Code)
	}
}
