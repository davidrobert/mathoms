// Package stages executa stages via exec do CLI A3.cli (Caminho 1,
// ADR-150 §3). Decisões 1/8/9 do track f1-go-service: exit 2 desambiguado
// pelo stderr JSON; process group + SIGTERM→30s→SIGKILL; stdout = 1 linha JSON.
package stages

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"syscall"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/propagation"

	"mathoms.ai/pipeline-service/internal/contracts"
)

// ErrUnknownStage indica que o subprocess rejeitou o stage (rede de
// segurança do registry local) — mapeia para HTTP 404.
var ErrUnknownStage = errors.New("unknown stage")

// ErrExecutorUnavailable indica ambiente/CLI indisponível (ADR-303 D4) — HTTP 503.
var ErrExecutorUnavailable = errors.New("stage executor unavailable")

const sigkillGrace = 30 * time.Second

// Executor roda stages via subprocess do CLI `python -m pipeline.orchestrator`.
type Executor struct {
	Python   string
	RepoRoot string
	Timeout  time.Duration
}

// NewExecutorFromEnv monta o executor a partir do ambiente do serviço.
func NewExecutorFromEnv() *Executor {
	timeout := 3600 * time.Second
	if raw := os.Getenv("MATHOMS_STAGE_EXEC_TIMEOUT_SECONDS"); raw != "" {
		if secs, err := strconv.Atoi(raw); err == nil && secs > 0 {
			timeout = time.Duration(secs) * time.Second
		}
	}
	return &Executor{
		Python:   envOr("MATHOMS_PYTHON", "python3"),
		RepoRoot: envOr("MATHOMS_REPO_ROOT", "."),
		Timeout:  timeout,
	}
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

// BuildArgs mapeia o request HTTP para as flags do CLI (decisão 9: config_dir
// ausente = flag omitida; --incremental-doc repetível; fallback stages CSV).
func BuildArgs(stage string, req contracts.StageExecuteRequest) []string {
	args := []string{
		"-m", "pipeline.orchestrator", "run-stage", stage,
		"--workspace", req.WorkspaceRoot,
		"--run-id", req.RunId,
		"--workspace-id", req.WorkspaceId,
	}
	if req.ConfigDir != nil && *req.ConfigDir != "" {
		args = append(args, "--config-dir", *req.ConfigDir)
	}
	if req.Incremental != nil && *req.Incremental {
		args = append(args, "--incremental")
	}
	if req.IncrementalDocPaths != nil {
		for _, doc := range *req.IncrementalDocPaths {
			args = append(args, "--incremental-doc", doc)
		}
	}
	if req.SkipLlm != nil && *req.SkipLlm {
		args = append(args, "--skip-llm")
	}
	if req.BaseRunId != nil && *req.BaseRunId != "" {
		args = append(args, "--base-run-id", *req.BaseRunId)
	}
	if req.BaseRunFallbackStages != nil && len(*req.BaseRunFallbackStages) > 0 {
		args = append(args, "--base-run-fallback-stages", strings.Join(*req.BaseRunFallbackStages, ","))
	}
	return args
}

// RunStage executa o stage e devolve o StageResult do CLI. Falha de stage é
// resultado (200 success=false), não error.
func (e *Executor) RunStage(ctx context.Context, stage string, req contracts.StageExecuteRequest) (contracts.StageExecuteResponse, error) {
	tracer := otel.Tracer("mathoms.pipeline")
	ctx, span := tracer.Start(ctx, "pipeline."+stage)
	defer span.End()
	span.SetAttributes(
		attribute.String("pipeline.stage", stage),
		attribute.String("pipeline.workspace_root", req.WorkspaceRoot),
		attribute.String("pipeline.run_id", req.RunId),
	)

	execCtx, cancel := context.WithTimeout(ctx, e.Timeout)
	defer cancel()
	stdout, stderr, exitCode, runErr := e.runSubprocess(execCtx, ctx, stage, req)
	if execCtx.Err() != nil {
		return contracts.StageExecuteResponse{}, fmt.Errorf(
			"%w: timeout de %s excedido no stage %s (subprocess morto via SIGTERM→SIGKILL)",
			ErrExecutorUnavailable, e.Timeout, stage)
	}
	return e.interpret(stage, stdout, stderr, exitCode, runErr)
}

// runSubprocess isola o lifecycle do exec: process group próprio, SIGTERM no
// cancel, SIGKILL após grace (WaitDelay), reaping garantido pelo Run().
func (e *Executor) runSubprocess(execCtx, spanCtx context.Context, stage string, req contracts.StageExecuteRequest) (string, string, int, error) {
	cmd := exec.CommandContext(execCtx, e.Python, BuildArgs(stage, req)...)
	cmd.Dir = e.RepoRoot
	cmd.Env = append(os.Environ(), traceparentEnv(spanCtx)...)
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	cmd.Cancel = func() error {
		return syscall.Kill(-cmd.Process.Pid, syscall.SIGTERM)
	}
	cmd.WaitDelay = sigkillGrace
	var stdout, stderr bytes.Buffer
	cmd.Stdout, cmd.Stderr = &stdout, &stderr
	err := cmd.Run()
	return stdout.String(), stderr.String(), cmd.ProcessState.ExitCode(), err
}

// traceparentEnv injeta o contexto W3C do span Go — o CLI (A3.cli.otel)
// restaura e cria o span filho, mantendo o trace contínuo.
func traceparentEnv(ctx context.Context) []string {
	carrier := propagation.MapCarrier{}
	otel.GetTextMapPropagator().Inject(ctx, carrier)
	env := make([]string, 0, len(carrier))
	for k, v := range carrier {
		env = append(env, strings.ToUpper(k)+"="+v)
	}
	return env
}

func (e *Executor) interpret(stage, stdout, stderr string, exitCode int, runErr error) (contracts.StageExecuteResponse, error) {
	switch exitCode {
	case 0, 1:
		return parseStageResult(stage, stdout, stderr)
	case 2:
		logChildStderr(stage, stderr)
		return contracts.StageExecuteResponse{}, classifyUsageError(stderr)
	default:
		logChildStderr(stage, stderr)
		return contracts.StageExecuteResponse{}, fmt.Errorf(
			"%w: CLI saiu com exit %d (erro: %s)", ErrExecutorUnavailable, exitCode, errString(runErr))
	}
}

// parseStageResult lê a linha única de JSON do stdout (decisão 9). Qualquer
// coisa fora disso = executor não-confiável → 503.
func parseStageResult(stage, stdout, stderr string) (contracts.StageExecuteResponse, error) {
	line := lastNonEmptyLine(stdout)
	if line == "" {
		logChildStderr(stage, stderr)
		return contracts.StageExecuteResponse{}, fmt.Errorf(
			"%w: stdout vazio — StageResult ausente", ErrExecutorUnavailable)
	}
	var resp contracts.StageExecuteResponse
	if err := json.Unmarshal([]byte(line), &resp); err != nil {
		logChildStderr(stage, stderr)
		return contracts.StageExecuteResponse{}, fmt.Errorf(
			"%w: stdout não é StageResult JSON: %s", ErrExecutorUnavailable, err.Error())
	}
	attempts := 1
	resp.Attempts = &attempts
	logChildStderr(stage, stderr)
	return resp, nil
}

// classifyUsageError desambigua o exit 2 do CLI pelo campo `error` do JSON
// de stderr (decisão 1): unknown_stage → 404; environment → 503.
func classifyUsageError(stderr string) error {
	var payload struct {
		Error   string `json:"error"`
		Message string `json:"message"`
	}
	line := lastNonEmptyLine(stderr)
	if err := json.Unmarshal([]byte(line), &payload); err != nil {
		return fmt.Errorf("%w: exit 2 sem stderr JSON parseável: %s", ErrExecutorUnavailable, truncate(line, 300))
	}
	if payload.Error == "unknown_stage" {
		return fmt.Errorf("%w: %s", ErrUnknownStage, payload.Message)
	}
	return fmt.Errorf("%w: %s", ErrExecutorUnavailable, payload.Message)
}

// logChildStderr repassa os logs do filho (stderr) ao log do serviço —
// stdout do container fica com os dois JSONs (slog do Go + mathoms.* do CLI).
func logChildStderr(stage, stderr string) {
	for _, line := range strings.Split(strings.TrimSpace(stderr), "\n") {
		if line != "" {
			slog.Info("subprocess", "stage", stage, "line", line)
		}
	}
}

func lastNonEmptyLine(s string) string {
	lines := strings.Split(strings.TrimSpace(s), "\n")
	for i := len(lines) - 1; i >= 0; i-- {
		if trimmed := strings.TrimSpace(lines[i]); trimmed != "" {
			return trimmed
		}
	}
	return ""
}

func errString(err error) string {
	if err == nil {
		return "<nil>"
	}
	return err.Error()
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "…"
}
