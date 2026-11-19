package main

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestPutPartialUpdateKeepsOtherFields(t *testing.T) {
	s := testStore()
	s.perfil.Ciudad = "Armenia"
	s.perfil.Telefono = "3001234567"
	h := routes(s)
	w := call(h, "PUT", "/perfiles/E1", `{"codigoPostal":"630001","fotoUrl":"https://cdn.empresa.com/fotos/e1.jpg",`+
		`"redesSociales":{"linkedin":"https://www.linkedin.com/in/ana","github":"https://github.com/ana"}}`)
	if w.Code != 200 {
		t.Fatalf("expected 200, got %d %s", w.Code, w.Body.String())
	}
	var p Perfil
	if err := json.Unmarshal(w.Body.Bytes(), &p); err != nil {
		t.Fatal(err)
	}
	if p.Ciudad != "Armenia" || p.Telefono != "3001234567" {
		t.Fatalf("partial update must keep untouched fields: %+v", p)
	}
	if p.CodigoPostal != "630001" || p.FotoURL != "https://cdn.empresa.com/fotos/e1.jpg" || p.RedesSociales["github"] != "https://github.com/ana" {
		t.Fatalf("new fields not stored: %+v", p)
	}
}

func TestPutEmptyStringClearsAField(t *testing.T) {
	s := testStore()
	s.perfil.Biografia = "algo"
	w := call(routes(s), "PUT", "/perfiles/E1", `{"biografia":""}`)
	if w.Code != 200 || s.perfil.Biografia != "" {
		t.Fatalf("expected cleared biografia, got %d %+v", w.Code, s.perfil)
	}
}

func TestPutRejectsInvalidValues(t *testing.T) {
	cases := map[string]string{
		"sin campos":          `{}`,
		"foto no web":         `{"fotoUrl":"ftp://servidor/foto.jpg"}`,
		"foto sin host":       `{"fotoUrl":"https://"}`,
		"codigo postal corto": `{"codigoPostal":"12"}`,
		"codigo postal raro":  `{"codigoPostal":"<b>630</b>"}`,
		"telefono con letras": `{"telefono":"llamame"}`,
		"red no admitida":     `{"redesSociales":{"myspace":"https://myspace.com/ana"}}`,
		"red sin url":         `{"redesSociales":{"github":"ana"}}`,
		"redes no objeto":     `{"redesSociales":"https://github.com/ana"}`,
		"biografia larga":     `{"biografia":"` + strings.Repeat("a", 1001) + `"}`,
		"campo protegido":     `{"cargo":"Gerente"}`,
	}
	for name, body := range cases {
		t.Run(name, func(t *testing.T) {
			s := testStore()
			w := call(routes(s), "PUT", "/perfiles/E1", body)
			if w.Code != 400 {
				t.Fatalf("expected 400, got %d %s", w.Code, w.Body.String())
			}
			if s.perfil.CodigoPostal != "" || s.perfil.FotoURL != "" {
				t.Fatalf("invalid update must not be stored: %+v", s.perfil)
			}
		})
	}
}

func TestValidateUpdateAcceptsEmptyValues(t *testing.T) {
	vacio := ""
	u := PerfilUpdate{Telefono: &vacio, CodigoPostal: &vacio, FotoURL: &vacio, RedesSociales: map[string]string{}}
	if err := validateUpdate(u); err != nil {
		t.Fatalf("empty values must be accepted to clear fields: %v", err)
	}
}

func TestIsWebURL(t *testing.T) {
	for value, want := range map[string]bool{
		"https://github.com/ana": true, "http://intranet.local/foto.png": true,
		"javascript:alert(1)": false, "github.com/ana": false, "": false,
	} {
		if got := isWebURL(value); got != want {
			t.Errorf("isWebURL(%q) = %v, want %v", value, got, want)
		}
	}
}
