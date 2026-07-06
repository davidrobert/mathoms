// Command pipeline-service é o shell HTTP do Caminho 1 (ADR-150 §5).
package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"

	"github.com/go-chi/chi/v5"

	"mathoms.ai/pipeline-service/internal/api"
	"mathoms.ai/pipeline-service/internal/contracts"
	"mathoms.ai/pipeline-service/internal/observability"
	"mathoms.ai/pipeline-service/internal/stages"
)

func main() {
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, nil)))
	shutdown := observability.Setup(context.Background())

	router := chi.NewRouter()
	router.Use(observability.ExtractTraceContext)
	contracts.HandlerFromMux(api.NewServer(stages.NewExecutorFromEnv()), router)

	addr := envOr("PIPELINE_SERVICE_HOST", "0.0.0.0") + ":" + envOr("PIPELINE_SERVICE_PORT", "8001")
	slog.Info("pipeline-service-go up", "addr", addr)
	err := http.ListenAndServe(addr, router)
	slog.Error("server exited", "error", err)
	_ = shutdown(context.Background())
	os.Exit(1)
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
