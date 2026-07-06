package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/go-chi/chi/v5"

	"mathoms.ai/pipeline-service/internal/contracts"
)

func newTestRouter(t *testing.T) http.Handler {
	t.Helper()
	router := chi.NewRouter()
	contracts.HandlerFromMux(NewServer(nil, nil), router)
	return router
}

func do(t *testing.T, router http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequestWithContext(t.Context(), method, path, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	return rec
}

func decode(t *testing.T, rec *httptest.ResponseRecorder) map[string]any {
	t.Helper()
	var out map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
		t.Fatalf("resposta não é JSON: %v — %s", err, rec.Body.String())
	}
	return out
}

const validStageBody = `{"run_id":"r1","workspace_id":"w1","workspace_root":"/tmp/ws"}`

func TestHealthMirrorsPythonPayload(t *testing.T) {
	rec := do(t, newTestRouter(t), http.MethodGet, "/health", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("esperava 200, veio %d", rec.Code)
	}
	got := decode(t, rec)
	want := map[string]any{"status": "ok", "service": "pipeline-service", "version": "0.1.0"}
	for k, v := range want {
		if got[k] != v {
			t.Errorf("health[%q] = %v, esperava %v", k, got[k], v)
		}
	}
}

func TestExecuteUnknownStageIs404WithValidList(t *testing.T) {
	rec := do(t, newTestRouter(t), http.MethodPost,
		"/api/v1/pipeline/stages/stage_inexistente/execute", validStageBody)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("esperava 404, veio %d: %s", rec.Code, rec.Body.String())
	}
	detail, _ := decode(t, rec)["detail"].(string)
	if !strings.Contains(detail, "unknown stage 'stage_inexistente'") ||
		!strings.Contains(detail, "'reconcile_transactions'") {
		t.Errorf("detail sem paridade com o Python: %s", detail)
	}
}

func TestExecuteLegacyNameResolvesBeforeValidation(t *testing.T) {
	rec := do(t, newTestRouter(t), http.MethodPost,
		"/api/v1/pipeline/stages/E3/execute", validStageBody)
	if rec.Code != http.StatusServiceUnavailable {
		t.Fatalf("legacy E3 deveria resolver (503 do stub F1), veio %d", rec.Code)
	}
}

func TestExecuteMissingRequiredFieldIs422(t *testing.T) {
	rec := do(t, newTestRouter(t), http.MethodPost,
		"/api/v1/pipeline/stages/reconcile_transactions/execute", `{"workspace_id":"w1"}`)
	if rec.Code != http.StatusUnprocessableEntity {
		t.Fatalf("esperava 422, veio %d", rec.Code)
	}
	body := rec.Body.String()
	for _, frag := range []string{`"Field required"`, `"missing"`, `"run_id"`} {
		if !strings.Contains(body, frag) {
			t.Errorf("422 sem shape HTTPValidationError (%s ausente): %s", frag, body)
		}
	}
}

func TestRunsUnknownStagesIs400ListingOriginals(t *testing.T) {
	body := `{"run_id":"r1","workspace_id":"w1","workspace_root":"/tmp/ws","stages":["E3","nope"]}`
	rec := do(t, newTestRouter(t), http.MethodPost, "/api/v1/pipeline/runs", body)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("esperava 400, veio %d: %s", rec.Code, rec.Body.String())
	}
	detail, _ := decode(t, rec)["detail"].(string)
	if !strings.Contains(detail, "unknown stage(s): ['nope']") {
		t.Errorf("detail sem paridade: %s", detail)
	}
}

func TestRunsValidSequenceHitsStub503(t *testing.T) {
	body := `{"run_id":"r1","workspace_id":"w1","workspace_root":"/tmp/ws","stages":["E3","analyze_finances"]}`
	rec := do(t, newTestRouter(t), http.MethodPost, "/api/v1/pipeline/runs", body)
	if rec.Code != http.StatusServiceUnavailable {
		t.Fatalf("sequência válida deveria bater no stub 503 (F1), veio %d", rec.Code)
	}
}

func TestRunsInvalidJSONBodyIs422(t *testing.T) {
	rec := do(t, newTestRouter(t), http.MethodPost, "/api/v1/pipeline/runs", `[1,2]`)
	if rec.Code != http.StatusUnprocessableEntity {
		t.Fatalf("esperava 422, veio %d", rec.Code)
	}
}
