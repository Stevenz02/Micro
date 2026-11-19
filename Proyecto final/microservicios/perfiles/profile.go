package main

// Modelo del perfil y reglas de la actualización que hace el propio empleado.
//
// Los datos personales y laborales (nombre, apellido, email, cargo, área, departamento) son
// propiedad de Gestión de Empleados: llegan por los eventos empleado.creado/actualizado y aquí
// son de solo lectura. El empleado gestiona su información complementaria: contacto,
// dirección completa, foto, biografía y redes sociales.

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/url"
	"regexp"
	"sort"
	"strings"
	"time"
	"unicode/utf8"
)

type Perfil struct {
	ID             string            `json:"id"`
	EmpleadoID     string            `json:"empleadoId"`
	Nombre         string            `json:"nombre"`
	Apellido       string            `json:"apellido"`
	Email          string            `json:"email"`
	Cargo          string            `json:"cargo"`
	Area           string            `json:"area"`
	DepartamentoID string            `json:"departamentoId"`
	Telefono       string            `json:"telefono"`
	Direccion      string            `json:"direccion"`
	Ciudad         string            `json:"ciudad"`
	CodigoPostal   string            `json:"codigoPostal"`
	Biografia      string            `json:"biografia"`
	FotoURL        string            `json:"fotoUrl"`
	RedesSociales  map[string]string `json:"redesSociales"`
	FechaCreacion  time.Time         `json:"fechaCreacion"`
	Archivado      bool              `json:"archivado"`
}

// PerfilUpdate es una actualización parcial: un campo ausente (nil) conserva su valor actual.
// Una cadena vacía borra el valor; redesSociales reemplaza el conjunto completo.
type PerfilUpdate struct {
	Telefono      *string           `json:"telefono"`
	Direccion     *string           `json:"direccion"`
	Ciudad        *string           `json:"ciudad"`
	CodigoPostal  *string           `json:"codigoPostal"`
	Biografia     *string           `json:"biografia"`
	FotoURL       *string           `json:"fotoUrl"`
	RedesSociales map[string]string `json:"redesSociales"`
}

var editableFields = map[string]bool{
	"telefono": true, "direccion": true, "ciudad": true, "codigoPostal": true,
	"biografia": true, "fotoUrl": true, "redesSociales": true,
}

// Redes admitidas en redesSociales.
var redesPermitidas = map[string]bool{
	"linkedin": true, "github": true, "x": true, "instagram": true, "facebook": true, "sitioWeb": true,
}

var (
	telefonoPattern     = regexp.MustCompile(`^[0-9+()\- ]{7,20}$`)
	codigoPostalPattern = regexp.MustCompile(`^[A-Za-z0-9 -]{3,10}$`)
)

// decodeUpdate lee el cuerpo del PUT: rechaza campos protegidos o desconocidos, tipos inválidos
// y valores fuera de las reglas. Los errores son mensajes aptos para un 400.
func decodeUpdate(body io.Reader) (PerfilUpdate, error) {
	var u PerfilUpdate
	var raw map[string]json.RawMessage
	if err := json.NewDecoder(body).Decode(&raw); err != nil {
		return u, errors.New("JSON invalido")
	}
	if len(raw) == 0 {
		return u, errors.New("No hay campos para actualizar")
	}
	keys := make([]string, 0, len(raw))
	for key := range raw {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	for _, key := range keys {
		if !editableFields[key] {
			return u, errors.New("Campo protegido o desconocido: " + key)
		}
	}
	data, _ := json.Marshal(raw)
	if err := json.Unmarshal(data, &u); err != nil {
		return u, errors.New("Campos invalidos: los valores deben ser texto y redesSociales un objeto")
	}
	return u, validateUpdate(u)
}

func validateUpdate(u PerfilUpdate) error {
	limits := []struct {
		name  string
		value *string
		max   int
	}{
		{"telefono", u.Telefono, 20}, {"direccion", u.Direccion, 200}, {"ciudad", u.Ciudad, 100},
		{"codigoPostal", u.CodigoPostal, 10}, {"biografia", u.Biografia, 1000}, {"fotoUrl", u.FotoURL, 2048},
	}
	for _, field := range limits {
		if field.value != nil && utf8.RuneCountInString(*field.value) > field.max {
			return fmt.Errorf("%s supera %d caracteres", field.name, field.max)
		}
	}
	if u.Telefono != nil && *u.Telefono != "" && !telefonoPattern.MatchString(*u.Telefono) {
		return errors.New("telefono invalido: use digitos, espacios, +, - o parentesis")
	}
	if u.CodigoPostal != nil && *u.CodigoPostal != "" && !codigoPostalPattern.MatchString(*u.CodigoPostal) {
		return errors.New("codigoPostal invalido: 3 a 10 letras, digitos, espacios o guiones")
	}
	if u.FotoURL != nil && *u.FotoURL != "" && !isWebURL(*u.FotoURL) {
		return errors.New("fotoUrl debe ser una URL http o https")
	}
	if len(u.RedesSociales) > len(redesPermitidas) {
		return errors.New("redesSociales tiene demasiadas entradas")
	}
	for red, enlace := range u.RedesSociales {
		if !redesPermitidas[red] {
			return errors.New("red social no admitida: " + red + " (use linkedin, github, x, instagram, facebook o sitioWeb)")
		}
		if len(enlace) > 2048 || !isWebURL(enlace) {
			return errors.New("el enlace de " + red + " debe ser una URL http o https")
		}
	}
	return nil
}

func isWebURL(value string) bool {
	parsed, err := url.Parse(strings.TrimSpace(value))
	return err == nil && (parsed.Scheme == "http" || parsed.Scheme == "https") && parsed.Host != ""
}
