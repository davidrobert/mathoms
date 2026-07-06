// Package observability faz o bootstrap OTel do shell Go (paridade ADR-110:
// propagator W3C sempre; exporter OTLP opt-in via OTEL_EXPORTER_OTLP_ENDPOINT).
package observability

import (
	"context"
	"log/slog"
	"net/http"
	"os"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	sdkresource "go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
)

// Setup instala o propagator W3C e, com endpoint OTLP configurado, o SDK
// exportador. Retorna shutdown (flush) — no-op quando sem exporter.
func Setup(ctx context.Context) func(context.Context) error {
	otel.SetTextMapPropagator(propagation.TraceContext{})
	if os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT") == "" {
		return func(context.Context) error { return nil }
	}
	exporter, err := otlptracehttp.New(ctx)
	if err != nil {
		slog.Warn("OTLP exporter init falhou; traces desabilitados", "error", err)
		return func(context.Context) error { return nil }
	}
	provider := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(sdkresource.NewWithAttributes(
			semconv.SchemaURL, semconv.ServiceName("pipeline-service"),
		)),
	)
	otel.SetTracerProvider(provider)
	return provider.Shutdown
}

// ExtractTraceContext é middleware: restaura o contexto de trace dos headers
// do request (o backend chamador propaga traceparent).
func ExtractTraceContext(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ctx := otel.GetTextMapPropagator().Extract(r.Context(), propagation.HeaderCarrier(r.Header))
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}
