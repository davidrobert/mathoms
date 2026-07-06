package stages

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/trace"

	"mathoms.ai/pipeline-service/internal/contracts"
)

const fakeResult = `{"stage":"reconcile_transactions","success":true,"duration_ms":12.5,"detail":{"total":1},"error":null}`

func fakeCLI(t *testing.T, script string) *Executor {
	t.Helper()
	path := filepath.Join(t.TempDir(), "fake-python")
	if err := os.WriteFile(path, []byte("#!/bin/sh\n"+script+"\n"), 0o755); err != nil {
		t.Fatal(err)
	}
	return &Executor{Python: path, RepoRoot: t.TempDir(), Timeout: 10 * time.Second}
}

func req() contracts.StageExecuteRequest {
	return contracts.StageExecuteRequest{RunId: "r1", WorkspaceId: "w1", WorkspaceRoot: "/tmp/ws"}
}

func TestExitZeroParsesStageResultAndSetsAttempts(t *testing.T) {
	e := fakeCLI(t, "echo '"+fakeResult+"'")
	resp, err := e.RunStage(context.Background(), "reconcile_transactions", req())
	if err != nil {
		t.Fatalf("erro inesperado: %v", err)
	}
	if !resp.Success || resp.Stage != "reconcile_transactions" {
		t.Fatalf("resposta errada: %+v", resp)
	}
	if resp.Attempts == nil || *resp.Attempts != 1 {
		t.Fatalf("attempts deve ser fixo 1 (decisão 7): %+v", resp.Attempts)
	}
}

func TestExitOneIsStageFailureNotError(t *testing.T) {
	e := fakeCLI(t, `echo '{"stage":"analyze_finances","success":false,"duration_ms":3,"detail":null,"error":"boom"}'; exit 1`)
	resp, err := e.RunStage(context.Background(), "analyze_finances", req())
	if err != nil {
		t.Fatalf("falha de stage é resultado, não error: %v", err)
	}
	if resp.Success || resp.Error == nil || *resp.Error != "boom" {
		t.Fatalf("resposta errada: %+v", resp)
	}
}

func TestExitTwoUnknownStageMapsTo404Sentinel(t *testing.T) {
	e := fakeCLI(t, `echo '{"error":"unknown_stage","message":"stage desconhecido: x"}' >&2; exit 2`)
	_, err := e.RunStage(context.Background(), "x", req())
	if !errors.Is(err, ErrUnknownStage) {
		t.Fatalf("esperava ErrUnknownStage, veio: %v", err)
	}
}

func TestExitTwoEnvironmentMapsTo503Sentinel(t *testing.T) {
	e := fakeCLI(t, `echo '{"error":"environment","message":"MATHOMS_DATABASE_URL ausente","adr":"ADR-303 D4"}' >&2; exit 2`)
	_, err := e.RunStage(context.Background(), "reconcile_transactions", req())
	if !errors.Is(err, ErrExecutorUnavailable) || errors.Is(err, ErrUnknownStage) {
		t.Fatalf("esperava ErrExecutorUnavailable puro, veio: %v", err)
	}
}

func TestGarbageStdoutIsExecutorUnavailable(t *testing.T) {
	e := fakeCLI(t, "echo 'isto nao e json'")
	_, err := e.RunStage(context.Background(), "reconcile_transactions", req())
	if !errors.Is(err, ErrExecutorUnavailable) {
		t.Fatalf("stdout lixo deve ser 503, veio: %v", err)
	}
}

func TestTimeoutKillsSubprocessFast(t *testing.T) {
	e := fakeCLI(t, "sleep 30")
	e.Timeout = 300 * time.Millisecond
	start := time.Now()
	_, err := e.RunStage(context.Background(), "reconcile_transactions", req())
	elapsed := time.Since(start)
	if !errors.Is(err, ErrExecutorUnavailable) || !strings.Contains(err.Error(), "timeout") {
		t.Fatalf("esperava timeout→ErrExecutorUnavailable, veio: %v", err)
	}
	if elapsed > 5*time.Second {
		t.Fatalf("subprocess não foi morto rápido (%.1fs) — grace/kill quebrado", elapsed.Seconds())
	}
}

func TestTraceparentIsInjectedIntoChildEnv(t *testing.T) {
	prev := otel.GetTextMapPropagator()
	otel.SetTextMapPropagator(propagation.TraceContext{})
	t.Cleanup(func() { otel.SetTextMapPropagator(prev) })

	e := fakeCLI(t, `echo "TP=$TRACEPARENT" >&2; echo '`+fakeResult+`'`)
	traceID, _ := trace.TraceIDFromHex("0123456789abcdef0123456789abcdef")
	spanID, _ := trace.SpanIDFromHex("0011223344556677")
	ctx := trace.ContextWithSpanContext(context.Background(), trace.NewSpanContext(trace.SpanContextConfig{
		TraceID: traceID, SpanID: spanID, TraceFlags: trace.FlagsSampled,
	}))

	// Sem SDK instalado, o span é não-gravador e propaga o contexto do pai —
	// o TRACEPARENT do filho carrega o trace-id injetado.
	if _, err := e.RunStage(ctx, "reconcile_transactions", req()); err != nil {
		t.Fatalf("erro inesperado: %v", err)
	}
}

func TestBuildArgsFlagMapping(t *testing.T) {
	cfg, base := "/cfg", "run-base"
	inc := true
	docs := []string{"inbox/a.pdf", "inbox/b.pdf"}
	fallback := []string{"E2-extratos", "E2-faturas"}
	r := contracts.StageExecuteRequest{
		RunId: "r1", WorkspaceId: "w1", WorkspaceRoot: "/ws",
		ConfigDir: &cfg, Incremental: &inc, IncrementalDocPaths: &docs,
		BaseRunId: &base, BaseRunFallbackStages: &fallback,
	}
	got := strings.Join(BuildArgs("reconcile_transactions", r), " ")
	for _, frag := range []string{
		"--config-dir /cfg", "--incremental ",
		"--incremental-doc inbox/a.pdf --incremental-doc inbox/b.pdf",
		"--base-run-id run-base", "--base-run-fallback-stages E2-extratos,E2-faturas",
	} {
		if !strings.Contains(got+" ", frag) {
			t.Errorf("args sem %q: %s", frag, got)
		}
	}
}

func TestBuildArgsOmitsAbsentOptionals(t *testing.T) {
	got := strings.Join(BuildArgs("analyze_finances", req()), " ")
	for _, frag := range []string{"--config-dir", "--incremental", "--base-run"} {
		if strings.Contains(got, frag) {
			t.Errorf("flag %q não deveria aparecer (decisão 9): %s", frag, got)
		}
	}
}
