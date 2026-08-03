package runs

import (
	"context"
	"encoding/json"
	"errors"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"

	"mathoms.ai/pipeline-service/internal/contracts"
	"mathoms.ai/pipeline-service/internal/events"
)

type fakeRunner struct{ failOn string }

func (f *fakeRunner) RunStage(_ context.Context, stage string, _ contracts.StageExecuteRequest) (contracts.StageExecuteResponse, error) {
	if stage == "explode" {
		return contracts.StageExecuteResponse{}, errors.New("boom exec")
	}
	if stage == f.failOn {
		msg := "stage quebrou"
		return contracts.StageExecuteResponse{Stage: stage, Success: false, Error: &msg}, nil
	}
	return contracts.StageExecuteResponse{Stage: stage, Success: true}, nil
}

func captureRun(t *testing.T, req contracts.RunStartRequest, failOn string) (contracts.RunSummaryResponse, []map[string]json.RawMessage) {
	t.Helper()
	mr := miniredis.RunT(t)
	t.Setenv("REDIS_URL", "redis://"+mr.Addr())
	sub := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	pubsub := sub.Subscribe(context.Background(), "pipeline:"+req.RunId)
	t.Cleanup(func() { _ = pubsub.Close(); _ = sub.Close() })
	if _, err := pubsub.Receive(context.Background()); err != nil {
		t.Fatal(err)
	}

	c := &Coordinator{Runner: &fakeRunner{failOn: failOn}, Publisher: events.NewPublisher()}
	resp, err := c.Run(context.Background(), req)
	if err != nil {
		t.Fatalf("Run falhou: %v", err)
	}
	var envelopes []map[string]json.RawMessage
	deadline := time.After(2 * time.Second)
	for {
		select {
		case msg := <-pubsub.Channel():
			var env map[string]json.RawMessage
			if err := json.Unmarshal([]byte(msg.Payload), &env); err != nil {
				t.Fatalf("envelope inválido: %v", err)
			}
			envelopes = append(envelopes, env)
		case <-deadline:
			t.Fatal("timeout aguardando eventos")
		default:
			if len(envelopes) > 0 && string(envelopes[len(envelopes)-1]["event"]) == `"run_completed"` {
				return resp, envelopes
			}
			if len(envelopes) > 0 && string(envelopes[len(envelopes)-1]["event"]) == `"run_failed"` {
				return resp, envelopes
			}
			time.Sleep(10 * time.Millisecond)
		}
	}
}

func baseReq(stagesList ...string) contracts.RunStartRequest {
	return contracts.RunStartRequest{
		RunId: "r-run", WorkspaceId: "w1", WorkspaceRoot: "/tmp/ws", Stages: stagesList,
	}
}

func eventNames(envs []map[string]json.RawMessage) []string {
	out := make([]string, 0, len(envs))
	for _, e := range envs {
		var name string
		_ = json.Unmarshal(e["event"], &name)
		out = append(out, name)
	}
	return out
}

func TestRunHappyPathEventsAndSummary(t *testing.T) {
	resp, envs := captureRun(t, baseReq("reconcile_transactions", "analyze_finances"), "")
	want := []string{"stage_started", "stage_completed", "stage_started", "stage_completed", "run_completed"}
	got := eventNames(envs)
	if len(got) != len(want) {
		t.Fatalf("eventos: %v", got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("evento %d: %s != %s (%v)", i, got[i], want[i], got)
		}
	}
	if !resp.Success || len(resp.Stages) != 2 || resp.FailedStage != nil {
		t.Fatalf("summary errado: %+v", resp)
	}
	var pct int
	_ = json.Unmarshal(envs[len(envs)-1]["progress_pct"], &pct)
	if pct != 100 {
		t.Fatalf("run_completed deve ter progress 100: %v", envs[len(envs)-1])
	}
}

func TestSkipLLMEmitsEventAndSyntheticEntry(t *testing.T) {
	resp, envs := captureRun(t, baseReq("extract_with_llm", "reconcile_transactions"), "")
	got := eventNames(envs)
	if got[0] != "stage_skipped" {
		t.Fatalf("primeiro evento deveria ser stage_skipped: %v", got)
	}
	if len(resp.Stages) != 2 || !resp.Stages[0].Success || resp.Stages[0].Detail == nil {
		t.Fatalf("entry sintético do skip ausente: %+v", resp.Stages)
	}
	if (*resp.Stages[0].Detail)["skipped"] != true {
		t.Fatalf("detail do skip errado: %+v", *resp.Stages[0].Detail)
	}
}

func TestStageFailureStopsAndRunFailedOmitsProgress(t *testing.T) {
	resp, envs := captureRun(t, baseReq("reconcile_transactions", "analyze_finances", "validate_cross"), "analyze_finances")
	if resp.Success || resp.FailedStage == nil || *resp.FailedStage != "analyze_finances" {
		t.Fatalf("summary errado: %+v", resp)
	}
	if len(resp.Stages) != 2 {
		t.Fatalf("stop_on_error deveria parar após a falha: %d stages", len(resp.Stages))
	}
	last := envs[len(envs)-1]
	if string(last["event"]) != `"run_failed"` {
		t.Fatalf("último evento: %v", eventNames(envs))
	}
	if _, present := last["progress_pct"]; present {
		t.Fatalf("run_failed NÃO leva progress_pct (decisão 6): %v", last)
	}
}

func TestEnvelopeShapeHasNoNulls(t *testing.T) {
	_, envs := captureRun(t, baseReq("reconcile_transactions"), "")
	for _, env := range envs {
		for k, v := range env {
			if string(v) == "null" {
				t.Fatalf("campo %q serializado como null — deve ser omitido: %v", k, env)
			}
		}
		for _, required := range []string{"event", "run_id", "timestamp"} {
			if _, ok := env[required]; !ok {
				t.Fatalf("campo obrigatório %q ausente: %v", required, env)
			}
		}
	}
}

func TestStageRequestCarregaSkipLLMResolvido(t *testing.T) {
	// ADR-355: o default do run é `true` e o do request per-stage é `false`.
	// Copiar o ponteiro cru entregaria LLM liberado sempre que o chamador
	// omitisse SkipLlm — o bug ao contrário do que esta ADR fecha.
	req := contracts.RunStartRequest{RunId: "r1", WorkspaceId: "w1", WorkspaceRoot: "/ws"}
	if req.SkipLlm != nil {
		t.Fatal("premissa do teste: request do run sem o campo")
	}
	for _, resolvido := range []bool{true, false} {
		got := stageRequest(req, resolvido)
		if got.SkipLlm == nil || *got.SkipLlm != resolvido {
			t.Errorf("skipLLM=%v não chegou ao request per-stage: %v", resolvido, got.SkipLlm)
		}
	}
}

func TestRunnerErrorPropagates(t *testing.T) {
	mr := miniredis.RunT(t)
	t.Setenv("REDIS_URL", "redis://"+mr.Addr())
	c := &Coordinator{Runner: &fakeRunner{}, Publisher: events.NewPublisher()}
	_, err := c.Run(context.Background(), baseReq("explode"))
	if err == nil {
		t.Fatal("erro do runner deveria propagar (vira 503 no handler)")
	}
}
