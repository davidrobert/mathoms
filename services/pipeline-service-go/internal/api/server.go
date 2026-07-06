// Package api implementa o ServerInterface gerado (contrato congelado por
// schemathesis, #747). Semântica de status espelha o serviço Python:
// 404 stage desconhecido (single) · 400 sequence com unknowns · 422 body
// inválido (HTTPValidationError) · 503 executor indisponível · falha de
// stage é 200 com success=false (fluxo, não erro — track f1 decisão 1).
package api

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"

	"mathoms.ai/pipeline-service/internal/contracts"
	"mathoms.ai/pipeline-service/internal/stages"
)

const (
	serviceName = "pipeline-service"
	version     = "0.1.0"
)

// StageRunner executa um stage já resolvido/validado (Fase 2: subprocess
// do CLI A3.cli); nil = stub 503.
type StageRunner interface {
	RunStage(ctx context.Context, stage string, req contracts.StageExecuteRequest) (contracts.StageExecuteResponse, error)
}

// RunCoordinator executa a sequência completa de um run (Fase 3).
type RunCoordinator interface {
	Run(ctx context.Context, req contracts.RunStartRequest) (contracts.RunSummaryResponse, error)
}

// Server implementa contracts.ServerInterface.
type Server struct {
	runner StageRunner
	runs   RunCoordinator
}

// NewServer cria o servidor; dependência nil responde 503.
func NewServer(runner StageRunner, runs RunCoordinator) *Server {
	return &Server{runner: runner, runs: runs}
}

// HealthHealthGet espelha o payload do Python: status/service/version.
func (s *Server) HealthHealthGet(w http.ResponseWriter, _ *http.Request) {
	status, service := "ok", serviceName
	writeJSON(w, http.StatusOK, contracts.ServiceHealthResponse{
		Status:  &status,
		Service: &service,
		Version: version,
	})
}

// ExecuteStageApiV1PipelineStagesStageExecutePost valida e delega ao runner.
func (s *Server) ExecuteStageApiV1PipelineStagesStageExecutePost(w http.ResponseWriter, r *http.Request, stage string) {
	resolved := stages.Resolve(stage)
	if !stages.IsValid(resolved) {
		writeDetail(w, http.StatusNotFound,
			fmt.Sprintf("unknown stage '%s' (valid: %s)", stage, pyList(stages.SortedValidStages())))
		return
	}
	var req contracts.StageExecuteRequest
	if !decodeBody(w, r, &req, requiredStageFields) {
		return
	}
	if s.runner == nil {
		writeDetail(w, http.StatusServiceUnavailable,
			"StageExecutor não implementado (F1 Fase 2) — ADR-303 D4")
		return
	}
	resp, err := s.runner.RunStage(r.Context(), resolved, req)
	if err != nil {
		if errors.Is(err, stages.ErrUnknownStage) {
			writeDetail(w, http.StatusNotFound, err.Error())
			return
		}
		writeDetail(w, http.StatusServiceUnavailable, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, resp)
}

// StartRunApiV1PipelineRunsPost valida a sequência inteira ANTES de executar.
func (s *Server) StartRunApiV1PipelineRunsPost(w http.ResponseWriter, r *http.Request) {
	var req contracts.RunStartRequest
	if !decodeBody(w, r, &req, requiredRunFields) {
		return
	}
	var unknown []string
	for _, st := range req.Stages {
		if !stages.IsValid(st) {
			unknown = append(unknown, st)
		}
	}
	if len(unknown) > 0 {
		writeDetail(w, http.StatusBadRequest, fmt.Sprintf("unknown stage(s): %s", pyList(unknown)))
		return
	}
	if s.runs == nil {
		writeDetail(w, http.StatusServiceUnavailable,
			"RunCoordinator não configurado — ADR-303 D4")
		return
	}
	resp, err := s.runs.Run(r.Context(), req)
	if err != nil {
		writeDetail(w, http.StatusServiceUnavailable, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, resp)
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

// writeDetail espelha o shape de erro do FastAPI HTTPException: {"detail": str}.
func writeDetail(w http.ResponseWriter, status int, detail string) {
	writeJSON(w, status, map[string]string{"detail": detail})
}

// pyList formata como repr de lista Python — paridade com as mensagens do
// serviço Python (f"(valid: {sorted(...)})" / f"unknown stage(s): {[...]}").
func pyList(items []string) string {
	out := "["
	for i, s := range items {
		if i > 0 {
			out += ", "
		}
		out += "'" + s + "'"
	}
	return out + "]"
}
