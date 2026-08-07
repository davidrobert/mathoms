"""A40.l18 — `frontend-ops` não está em NENHUM workflow de CI; este teste é o gate."""

# Medido: `frontend-ops/**` não aparece em nenhum grupo do `files_yaml` do
# `ci.yml` exceto `any_code`. Um PR que toque só esse app dispara `changes` +
# `lint-all` (Python) e o `all-green` passa — zero verificação de TS. Logo um
# `types.ts` dessincronizado do DTO passa por todos os gates e quebra no navegador
# do dono, que é o único que existe (não há deploy: GHCR/Coolify estão
# OWNER-GATED).
#
# Idioma copiado do `test_pipeline_status_enum_parity.py` que o PR1 desta mesma
# lane criou. Roda dentro de `backend-tests`, que É required via `all-green` —
# zero job novo, zero minuto novo de CI. A CI própria do `frontend-ops` é lane
# separada (A42).
#
# Para o gate não virar no-op, `frontend-ops/src/lib/types.ts` entra no grupo
# `backend` do `files_yaml`: sem isso, um PR que mova só o lado TS pula
# `backend-tests` e o gate não roda. Mesma classe de falha-aberta do comentário
# que já existe no `ci.yml` sobre `pipeline_lib`.

from __future__ import annotations

import re
from pathlib import Path

from backend.app.schemas.admin import MetricsResponse

_TYPES_TS = Path(__file__).resolve().parents[2] / "frontend-ops" / "src" / "lib" / "types.ts"


def _ts_interface_fields(name: str) -> set[str]:
    src = _TYPES_TS.read_text(encoding="utf-8")
    match = re.search(rf"export interface {name} \{{(.*?)\n\}}", src, re.DOTALL)
    assert match, f"interface {name} não encontrada em {_TYPES_TS.name}"
    return set(re.findall(r"^\s{2}(\w+)[?]?:", match.group(1), re.MULTILINE))


def test_metrics_response_em_paridade_com_o_dto():
    """Campo novo no DTO que não chegue ao `types.ts` sai da tela em silêncio."""
    assert _ts_interface_fields("MetricsResponse") == set(MetricsResponse.model_fields)


def test_breakdowns_de_degradacao_estao_no_ts():
    """Âncora explícita nos 3 campos da §Decisões do dono, item 2."""
    # Sem isto, um refactor que renomeie os campos passaria pelo teste acima
    # (os dois lados mudariam juntos) sem que ninguém revisasse a decisão.
    fields = _ts_interface_fields("MetricsResponse")
    assert {
        "pipeline_runs_by_status",
        "stages_degraded_by_reason",
        "stages_degraded_by_stage",
    } <= fields


def test_types_ts_esta_no_grupo_backend_do_ci():
    """O gate acima é no-op se `backend-tests` não rodar quando o TS move."""
    ci = (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml").read_text()
    assert "frontend-ops/src/lib/types.ts" in ci, (
        "adicione frontend-ops/src/lib/types.ts ao grupo `backend` do files_yaml — "
        "senão um PR que toque só o TS pula backend-tests e este gate não roda"
    )
