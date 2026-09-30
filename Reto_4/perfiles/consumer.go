package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/url"
	"os"
	"regexp"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	amqp "github.com/rabbitmq/amqp091-go"
)

const profilesQueue = "perfiles.events"

var uuidPattern = regexp.MustCompile(`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`)

type eventEnvelope struct {
	ID         string          `json:"id"`
	Type       string          `json:"type"`
	Version    int             `json:"version"`
	OccurredAt string          `json:"occurredAt"`
	Producer   string          `json:"producer"`
	Data       json.RawMessage `json:"data"`
}

type employeeData struct {
	EmpleadoID     string `json:"empleadoId"`
	Nombre         string `json:"nombre"`
	Apellido       string `json:"apellido"`
	Email          string `json:"email"`
	Cargo          string `json:"cargo"`
	Area           string `json:"area"`
	DepartamentoID string `json:"departamentoId"`
	Estado         string `json:"estado"`
	FechaRetiro    string `json:"fechaRetiro"`
	Motivo         string `json:"motivo"`
}

type invalidEvent struct{ reason string }

func (e invalidEvent) Error() string { return e.reason }

func parseProfileEvent(body []byte) (eventEnvelope, employeeData, error) {
	var event eventEnvelope
	if err := json.Unmarshal(body, &event); err != nil {
		return event, employeeData{}, invalidEvent{"JSON invalido"}
	}
	if !uuidPattern.MatchString(event.ID) || event.Version != 1 || event.Producer != "empleados-service" {
		return event, employeeData{}, invalidEvent{"sobre de evento invalido"}
	}
	if _, err := time.Parse(time.RFC3339Nano, event.OccurredAt); err != nil {
		return event, employeeData{}, invalidEvent{"occurredAt invalido"}
	}
	if event.Type != "empleado.creado" && event.Type != "empleado.actualizado" && event.Type != "empleado.retirado" {
		return event, employeeData{}, invalidEvent{"tipo de evento no soportado"}
	}
	var data employeeData
	if err := json.Unmarshal(event.Data, &data); err != nil || data.EmpleadoID == "" {
		return event, data, invalidEvent{"data invalida"}
	}
	if event.Type == "empleado.retirado" {
		if data.Email == "" || data.FechaRetiro == "" || data.Motivo == "" {
			return event, data, invalidEvent{"retiro incompleto"}
		}
	} else if data.Nombre == "" || data.Apellido == "" || data.Email == "" || data.Cargo == "" || data.Area == "" || data.DepartamentoID == "" {
		return event, data, invalidEvent{"empleado incompleto"}
	}
	if event.Type == "empleado.creado" && data.Estado != "ACTIVO" {
		return event, data, invalidEvent{"estado inicial invalido"}
	}
	return event, data, nil
}

func applyProfileEvent(ctx context.Context, pool *pgxpool.Pool, event eventEnvelope, data employeeData) error {
	tx, err := pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)
	var inserted int
	err = tx.QueryRow(ctx, `INSERT INTO eventos_procesados(id) VALUES($1::uuid) ON CONFLICT DO NOTHING RETURNING 1`, event.ID).Scan(&inserted)
	if errors.Is(err, pgx.ErrNoRows) {
		return tx.Commit(ctx)
	}
	if err != nil {
		return err
	}
	var command string
	var args []any
	switch event.Type {
	case "empleado.creado":
		command = `INSERT INTO perfiles(id,empleado_id,nombre,apellido,email,cargo,area,departamento_id)
			VALUES(gen_random_uuid(),$1,$2,$3,$4,$5,$6,$7)
			ON CONFLICT(empleado_id) DO UPDATE SET nombre=EXCLUDED.nombre,apellido=EXCLUDED.apellido,
			email=EXCLUDED.email,cargo=EXCLUDED.cargo,area=EXCLUDED.area,departamento_id=EXCLUDED.departamento_id`
		args = []any{data.EmpleadoID, data.Nombre, data.Apellido, data.Email, data.Cargo, data.Area, data.DepartamentoID}
	case "empleado.actualizado":
		command = `UPDATE perfiles SET nombre=$2,apellido=$3,email=$4,cargo=$5,area=$6,departamento_id=$7 WHERE empleado_id=$1`
		args = []any{data.EmpleadoID, data.Nombre, data.Apellido, data.Email, data.Cargo, data.Area, data.DepartamentoID}
	case "empleado.retirado":
		command = `UPDATE perfiles SET archivado=TRUE WHERE empleado_id=$1`
		args = []any{data.EmpleadoID}
	}
	result, err := tx.Exec(ctx, command, args...)
	if err != nil {
		return err
	}
	if result.RowsAffected() == 0 {
		return fmt.Errorf("perfil %s aun no existe", data.EmpleadoID)
	}
	if err := tx.Commit(ctx); err != nil {
		return err
	}
	log.Printf("evento_procesado id=%s tipo=%s empleadoId=%s", event.ID, event.Type, data.EmpleadoID)
	return nil
}

func rabbitAddress() string {
	for _, key := range []string{"RABBITMQ_HOST", "RABBITMQ_USER", "RABBITMQ_PASSWORD"} {
		if strings.TrimSpace(os.Getenv(key)) == "" {
			log.Fatalf("falta %s", key)
		}
	}
	return (&url.URL{Scheme: "amqp", Host: os.Getenv("RABBITMQ_HOST") + ":5672", User: url.UserPassword(os.Getenv("RABBITMQ_USER"), os.Getenv("RABBITMQ_PASSWORD"))}).String()
}

func consumeEvents(pool *pgxpool.Pool) {
	address := rabbitAddress()
	for {
		if err := consumeOnce(pool, address); err != nil {
			log.Printf("consumidor perfiles desconectado: %v", err)
		}
		time.Sleep(2 * time.Second)
	}
}

func consumeOnce(pool *pgxpool.Pool, address string) error {
	connection, err := amqp.Dial(address)
	if err != nil {
		return err
	}
	defer connection.Close()
	channel, err := connection.Channel()
	if err != nil {
		return err
	}
	defer channel.Close()
	if err := channel.Qos(1, 0, false); err != nil {
		return err
	}
	deliveries, err := channel.Consume(profilesQueue, "", false, false, false, false, nil)
	if err != nil {
		return err
	}
	for delivery := range deliveries {
		event, data, err := parseProfileEvent(delivery.Body)
		if err == nil {
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			err = applyProfileEvent(ctx, pool, event, data)
			cancel()
		}
		if err != nil {
			var invalid invalidEvent
			permanent := errors.As(err, &invalid)
			log.Printf("evento_perfiles_error id=%s error=%v requeue=%t", event.ID, err, !permanent)
			if !permanent {
				time.Sleep(time.Second)
			}
			if nackErr := delivery.Nack(false, !permanent); nackErr != nil {
				return nackErr
			}
			continue
		}
		if err := delivery.Ack(false); err != nil {
			return err
		}
	}
	return errors.New("canal de entregas cerrado")
}
