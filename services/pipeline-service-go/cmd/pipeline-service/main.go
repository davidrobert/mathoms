// Command pipeline-service é o shell HTTP do Caminho 1 (ADR-150 §5).
package main

import (
	"log/slog"
	"net/http"
	"os"

	"github.com/go-chi/chi/v5"

	"mathoms.ai/pipeline-service/internal/api"
	"mathoms.ai/pipeline-service/internal/contracts"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	slog.SetDefault(logger)

	host := envOr("PIPELINE_SERVICE_HOST", "0.0.0.0")
	port := envOr("PIPELINE_SERVICE_PORT", "8001")
	router := chi.NewRouter()
	contracts.HandlerFromMux(api.NewServer(nil), router)

	addr := host + ":" + port
	slog.Info("pipeline-service-go up", "addr", addr)
	if err := http.ListenAndServe(addr, router); err != nil {
		slog.Error("server exited", "error", err)
		os.Exit(1)
	}
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
