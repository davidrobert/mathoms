// Package events publica andamento de run no Redis — envelope e channel
// BIT-EXACT com event_publisher.py (ADR-150 §6, decisão 5 do track):
// campos None são OMITIDOS (ponteiros+omitempty), channel pipeline:{run_id},
// timestamp no formato isoformat Python (offset +00:00, 6 dígitos).
package events

import (
	"context"
	"encoding/json"
	"log/slog"
	"os"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"
)

// pythonISOLayout espelha datetime.now(timezone.utc).isoformat().
const pythonISOLayout = "2006-01-02T15:04:05.000000-07:00"

// Envelope é o shape exato consumido pelo WebSocket do backend.
//
//nolint:govet // fieldalignment: legibilidade do DTO > 8 bytes
type Envelope struct {
	Stage       *string         `json:"stage,omitempty"`
	Status      *string         `json:"status,omitempty"`
	ProgressPct *int            `json:"progress_pct,omitempty"`
	Error       *string         `json:"error,omitempty"`
	Detail      json.RawMessage `json:"detail,omitempty"`
	Event       string          `json:"event"`
	RunID       string          `json:"run_id"`
	Timestamp   string          `json:"timestamp"`
}

// Publisher envia envelopes para pipeline:{run_id}. Client lazy idempotente
// (ADR-111 exceção (b) — registrado em STATELESS_AUDIT §2); falha de Redis é
// não-fatal (espelho do Python: eventos são best-effort).
//
//nolint:govet // fieldalignment: 2 campos, irrelevante
type Publisher struct {
	once   sync.Once
	client *redis.Client
}

// NewPublisher cria o publisher (client conecta lazy no primeiro Publish).
func NewPublisher() *Publisher { return &Publisher{} }

func (p *Publisher) redisClient() *redis.Client {
	p.once.Do(func() {
		url := os.Getenv("REDIS_URL")
		if url == "" {
			url = "redis://localhost:6379/0"
		}
		opts, err := redis.ParseURL(url)
		if err != nil {
			slog.Warn("REDIS_URL inválida; eventos desabilitados", "error", err)
			return
		}
		p.client = redis.NewClient(opts)
	})
	return p.client
}

// Publish monta o envelope (timestamp agora, UTC) e publica; nunca falha o run.
func (p *Publisher) Publish(ctx context.Context, runID string, env Envelope) {
	client := p.redisClient()
	if client == nil {
		return
	}
	env.RunID = runID
	env.Timestamp = time.Now().UTC().Format(pythonISOLayout)
	payload, err := json.Marshal(env)
	if err != nil {
		slog.Warn("envelope não serializável", "error", err)
		return
	}
	if err := client.Publish(ctx, "pipeline:"+runID, payload).Err(); err != nil {
		slog.Warn("publish falhou; evento descartado", "run_id", runID, "error", err)
	}
}

// Str e Pct ajudam a montar campos opcionais sem zero-values serializados.
func Str(s string) *string { return &s }

// Pct converte para ponteiro — progress omitido quando nil (ex.: run_failed).
func Pct(v int) *int { return &v }
