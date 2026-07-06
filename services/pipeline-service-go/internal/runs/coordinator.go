// Package runs sequencia stages de um run completo — porta fiel de
// run_coordinator.py (decisão 6 do track): progress cortado por posição,
// run_failed SEM progress_pct, skip_llm emite evento + entry sintético.
package runs

import (
	"context"
	"encoding/json"
	"time"

	"mathoms.ai/pipeline-service/internal/contracts"
	"mathoms.ai/pipeline-service/internal/events"
	"mathoms.ai/pipeline-service/internal/stages"
)

// StageRunner é a interface mínima consumida (implementada pelo Executor).
type StageRunner interface {
	RunStage(ctx context.Context, stage string, req contracts.StageExecuteRequest) (contracts.StageExecuteResponse, error)
}

// Coordinator executa a sequência e publica eventos por boundary de stage.
type Coordinator struct {
	Runner    StageRunner
	Publisher *events.Publisher
}

func boolOr(v *bool, fallback bool) bool {
	if v == nil {
		return fallback
	}
	return *v
}

func stageRequest(req contracts.RunStartRequest) contracts.StageExecuteRequest {
	return contracts.StageExecuteRequest{
		RunId: req.RunId, WorkspaceId: req.WorkspaceId, WorkspaceRoot: req.WorkspaceRoot,
		ConfigDir: req.ConfigDir, Incremental: req.Incremental,
		IncrementalDocPaths: req.IncrementalDocPaths,
		BaseRunId:           req.BaseRunId, BaseRunFallbackStages: req.BaseRunFallbackStages,
	}
}

func skippedEntry(stage string) contracts.StageExecuteResponse {
	detail := map[string]interface{}{"skipped": true, "reason": "LLM stage skipped"}
	return contracts.StageExecuteResponse{Stage: stage, Success: true, Detail: &detail}
}

// Run executa a sequência (defaults do contrato Python: skip_llm=true,
// stop_on_error=true) e devolve o RunSummaryResponse agregado.
func (c *Coordinator) Run(ctx context.Context, req contracts.RunStartRequest) (contracts.RunSummaryResponse, error) {
	started := time.Now().UTC().Format("2006-01-02T15:04:05.000000-07:00")
	results, failedStage, err := c.loop(ctx, req)
	if err != nil {
		return contracts.RunSummaryResponse{}, err
	}
	success := failedStage == nil
	status, event := "completed", "run_completed"
	var pct *int
	if success {
		pct = events.Pct(100)
	} else {
		status, event = "failed", "run_failed"
	}
	c.Publisher.Publish(ctx, req.RunId, events.Envelope{Event: event, Status: &status, ProgressPct: pct})
	return contracts.RunSummaryResponse{
		RunId: req.RunId, WorkspaceId: req.WorkspaceId, Success: success,
		StartedAt: started, FinishedAt: time.Now().UTC().Format("2006-01-02T15:04:05.000000-07:00"),
		Stages: results, FailedStage: failedStage,
	}, nil
}

func (c *Coordinator) loop(ctx context.Context, req contracts.RunStartRequest) ([]contracts.StageExecuteResponse, *string, error) {
	skipLLM, stopOnError := boolOr(req.SkipLlm, true), boolOr(req.StopOnError, true)
	total := len(req.Stages)
	results := make([]contracts.StageExecuteResponse, 0, total)
	var failedStage *string
	for idx, stage := range req.Stages {
		progress := idx * 100 / total
		if skipLLM && stages.IsLLMStage(stage) {
			c.publishSkip(ctx, req.RunId, stage, progress)
			results = append(results, skippedEntry(stage))
			continue
		}
		c.publishStage(ctx, req.RunId, "stage_started", stage, "running", events.Pct(progress), nil)
		resp, err := c.Runner.RunStage(ctx, stage, stageRequest(req))
		if err != nil {
			return nil, nil, err
		}
		results = append(results, resp)
		completed := (idx + 1) * 100 / total
		if resp.Success {
			c.publishStage(ctx, req.RunId, "stage_completed", stage, "completed", events.Pct(completed), nil)
			continue
		}
		errMsg := "unknown"
		if resp.Error != nil {
			errMsg = *resp.Error
		}
		c.publishStage(ctx, req.RunId, "stage_failed", stage, "failed", events.Pct(completed), &errMsg)
		failedStage = &req.Stages[idx]
		if stopOnError {
			break
		}
	}
	return results, failedStage, nil
}

func (c *Coordinator) publishSkip(ctx context.Context, runID, stage string, progress int) {
	detail, _ := json.Marshal(map[string]string{"reason": "LLM stage skipped"})
	c.Publisher.Publish(ctx, runID, events.Envelope{
		Event: "stage_skipped", Stage: &stage, Status: events.Str("skipped"),
		ProgressPct: events.Pct(progress), Detail: detail,
	})
}

func (c *Coordinator) publishStage(ctx context.Context, runID, event, stage, status string, pct *int, errMsg *string) {
	c.Publisher.Publish(ctx, runID, events.Envelope{
		Event: event, Stage: &stage, Status: &status, ProgressPct: pct, Error: errMsg,
	})
}
