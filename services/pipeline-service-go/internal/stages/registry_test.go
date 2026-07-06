package stages

import "testing"

func TestResolveLegacyMirrorsADR093(t *testing.T) {
	if got := Resolve("E3"); got != "reconcile_transactions" {
		t.Fatalf("Resolve(E3) = %q", got)
	}
	if got := Resolve("reconcile_transactions"); got != "reconcile_transactions" {
		t.Fatalf("descritivo deve passar through, veio %q", got)
	}
	if got := Resolve("bogus"); got != "bogus" {
		t.Fatalf("desconhecido deve passar through, veio %q", got)
	}
}

func TestIsValidAcceptsLegacyAndDescriptive(t *testing.T) {
	for _, name := range []string{"E3", "reconcile_transactions", "E5", "analyze_finances"} {
		if !IsValid(name) {
			t.Errorf("IsValid(%q) = false", name)
		}
	}
	if IsValid("bogus") {
		t.Error("IsValid(bogus) deveria ser false")
	}
}

func TestIsLLMStageCoversAliases(t *testing.T) {
	if IsLLMStage("reconcile_transactions") {
		t.Error("reconcile não é LLM")
	}
	if !IsLLMStage("extract_with_llm") {
		t.Error("extract_with_llm é LLM")
	}
}

func TestSortedValidStagesIsSortedAndComplete(t *testing.T) {
	sorted := SortedValidStages()
	if len(sorted) != len(ValidStages) {
		t.Fatalf("len=%d, esperava %d", len(sorted), len(ValidStages))
	}
	for i := 1; i < len(sorted); i++ {
		if sorted[i-1] >= sorted[i] {
			t.Fatalf("não ordenado em %d: %s >= %s", i, sorted[i-1], sorted[i])
		}
	}
}
