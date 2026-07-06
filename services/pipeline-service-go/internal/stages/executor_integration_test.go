package stages

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"

	"mathoms.ai/pipeline-service/internal/contracts"
)

// Integração com o CLI REAL (gate F1.2 do track): seed E2 em SQLite →
// RunStage via subprocess → E3 persistido em pipeline_artifacts. Espelho de
// test_artifact_store_integration.py. Exige venv Python com backend —
// guarded: roda local e no harness da Fase 4 (o job go-test não tem venv).
const integrationEnvGate = "MATHOMS_GO_CLI_INTEGRATION"

const testFernetKey = "NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA="

func repoRoot(t *testing.T) string {
	t.Helper()
	abs, err := filepath.Abs("../../../..")
	if err != nil {
		t.Fatal(err)
	}
	return abs
}

func pySnippet(root, dbURL, code string) *exec.Cmd {
	cmd := exec.CommandContext(context.Background(), "python3", "-c", code)
	cmd.Dir = root
	cmd.Env = append(os.Environ(),
		"MATHOMS_DATABASE_URL="+dbURL,
		"MATHOMS_ENCRYPT_PIPELINE_ARTIFACTS=false",
		"MATHOMS_FERNET_KEY="+testFernetKey,
		"MATHOMS_REDIS_URL=redis://127.0.0.1:6390/0",
		"PYTHONPATH="+root,
	)
	return cmd
}

func TestRealCLIPersistsArtifactEndToEnd(t *testing.T) {
	if os.Getenv(integrationEnvGate) == "" {
		t.Skipf("defina %s=1 (exige venv Python com backend)", integrationEnvGate)
	}
	root := repoRoot(t)
	tmp := t.TempDir()
	dbURL := fmt.Sprintf("sqlite+aiosqlite:///%s/it.db", tmp)
	writeWorkspaceConfig(t, tmp)

	seed := `
import json, sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import backend.app.models
from backend.app.core.database import Base
from backend.app.services.db_artifact_store import DBArtifactStore
url = "` + fmt.Sprintf("sqlite:///%s/it.db", tmp) + `"
engine = create_engine(url); Base.metadata.create_all(engine)
payload = json.loads(Path("tests/fixtures/pipeline_golden/e2/minimal-extrato-2_extract.json").read_text())
payload.update(saldo_inicial=0.0, saldo_final=100.0)
s = sessionmaker(bind=engine, expire_on_commit=False)()
DBArtifactStore(s, workspace_id="ws-go", pipeline_run_id="run-go").write("E2-extratos", "golden-minimal", payload)
s.commit(); s.close()
print("seed-ok")`
	if out, err := pySnippet(root, dbURL, seed).CombinedOutput(); err != nil {
		t.Fatalf("seed falhou: %v — %s", err, out)
	}

	t.Setenv("MATHOMS_DATABASE_URL", dbURL)
	t.Setenv("MATHOMS_ENCRYPT_PIPELINE_ARTIFACTS", "false")
	t.Setenv("MATHOMS_FERNET_KEY", testFernetKey)
	t.Setenv("MATHOMS_REDIS_URL", "redis://127.0.0.1:6390/0")
	t.Setenv("PYTHONPATH", root)

	e := &Executor{Python: "python3", RepoRoot: root, Timeout: 3 * time.Minute}
	reqBody := contracts.StageExecuteRequest{RunId: "run-go", WorkspaceId: "ws-go", WorkspaceRoot: tmp}
	resp, err := e.RunStage(context.Background(), "reconcile_transactions", reqBody)
	if err != nil {
		t.Fatalf("RunStage real falhou: %v", err)
	}
	if !resp.Success {
		t.Fatalf("stage real success=false: %+v", resp)
	}

	readback := `
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import backend.app.models
from backend.app.services.db_artifact_store import DBArtifactStore
url = "` + fmt.Sprintf("sqlite:///%s/it.db", tmp) + `"
s = sessionmaker(bind=create_engine(url), expire_on_commit=False)()
store = DBArtifactStore(s, workspace_id="ws-go", pipeline_run_id="run-go")
keys = store.list_keys("E3")
assert len(keys) == 1, keys
assert store.read("E3", keys[0])["banco"] == "itau"
print("readback-ok", keys[0])`
	out, err := pySnippet(root, dbURL, readback).CombinedOutput()
	if err != nil {
		t.Fatalf("readback falhou: %v — %s", err, out)
	}
	t.Logf("E3 persistido pelo subprocess do Go: %s", out)
}

func TestRealCLIEnvironmentErrorIs503Sentinel(t *testing.T) {
	if os.Getenv(integrationEnvGate) == "" {
		t.Skipf("defina %s=1", integrationEnvGate)
	}
	root := repoRoot(t)
	// Limpa o env de DB para forçar o fail-fast D4 do CLI real.
	t.Setenv("MATHOMS_DATABASE_URL", "")
	if err := os.Unsetenv("MATHOMS_DATABASE_URL"); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PYTHONPATH", root)

	e := &Executor{Python: "python3", RepoRoot: root, Timeout: time.Minute}
	_, err := e.RunStage(context.Background(), "reconcile_transactions",
		contracts.StageExecuteRequest{RunId: "r", WorkspaceId: "w", WorkspaceRoot: t.TempDir()})
	if !errors.Is(err, ErrExecutorUnavailable) {
		t.Fatalf("exit 2 environment deve virar ErrExecutorUnavailable: %v", err)
	}
}

func writeWorkspaceConfig(t *testing.T, ws string) {
	t.Helper()
	cfg := filepath.Join(ws, "config")
	if err := os.MkdirAll(cfg, 0o755); err != nil {
		t.Fatal(err)
	}
	files := map[string]string{
		"pipeline.json":       `{"reconciliation": {"skip_types": [], "skip_files": []}}`,
		"family_members.json": `{}`,
		"institutions.json":   `{"banco_canonical": {}}`,
	}
	for name, content := range files {
		if err := os.WriteFile(filepath.Join(cfg, name), []byte(content), 0o644); err != nil {
			t.Fatal(err)
		}
	}
}
