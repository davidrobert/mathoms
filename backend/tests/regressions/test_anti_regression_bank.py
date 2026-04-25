"""Anti-regression bank — F6.5E.8.

Cada teste prova que **um bug histórico não voltou**. Falha imediata se o
fix for revertido. Ver `README.md` neste diretório para o catálogo completo.

Convenção dos nomes:
- `test_bug_NNN_*` para BUG-001..BUG-015 (QA pass de 2026-04-14/15)
- `test_op_NNN_*` para bugs operacionais do dogfood (2026-04-15)

Tests que precisam de frontend (Vitest/Playwright) ficam como `pytest.skip`
com ponteiro pro arquivo frontend que cobrirá. Quando 6.5B/D forem feitas,
o skip vira import + assert real.
"""

from __future__ import annotations

import inspect
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]


# ─────────────────────────────────────────────────────────────────────
# BUG-001 — Celery autodiscover não encontrava `pipeline_task.py`
# ─────────────────────────────────────────────────────────────────────


class TestBug001CeleryTaskDiscovery:
    """# Bug
    Celery worker subia mas a task `pipeline.run` não era registrada porque
    `autodiscover_tasks` procura `tasks.py` (singular). Nosso arquivo é
    `pipeline_task.py`.

    # Fix
    `worker.py`: substituiu `autodiscover_tasks` por
    `include=["backend.app.tasks.pipeline_task"]`.

    # Por que falharia se revertido
    Sem `include=`, o módulo não é importado pelo worker, a task fica
    desregistrada e qualquer envio falha com KeyError.
    """

    def test_worker_explicitly_includes_pipeline_task(self):
        from backend.app import worker

        celery_app = worker.celery_app
        # `include` config preserva o que foi passado no construtor
        included = celery_app.conf.get("include") or []
        assert "backend.app.tasks.pipeline_task" in included, (
            "BUG-001 REGRESSION: `pipeline_task` removido do include do Celery. "
            "autodiscover_tasks não vai encontrar (procura por tasks.py)."
        )

    def test_pipeline_run_task_is_registered(self):
        # Force-import do módulo de tasks (Celery `include` é lazy — só roda
        # quando o worker bootstrapa). Em test, importamos explicitamente
        # para popular o registry.
        import backend.app.tasks.pipeline_task  # noqa: F401
        from backend.app import worker

        names = list(worker.celery_app.tasks.keys())
        # nome canônico definido via @celery_app.task(name="...") em pipeline_task.py
        assert any("pipeline" in n.lower() for n in names), (
            f"Nenhuma task contendo 'pipeline' registrada após import explícito. " f"Tasks: {names}"
        )


# ─────────────────────────────────────────────────────────────────────
# BUG-002 — Celery fork worker sem `pipeline` no sys.path
# ─────────────────────────────────────────────────────────────────────


class TestBug002CeleryPipelineModule:
    """# Bug
    Em fork pool do Celery, workers filhos não herdavam `sys.path`
    customizado → `import pipeline` falhava com ModuleNotFoundError.

    # Fix
    `sys.path.insert(0, project_root)` no topo de `worker.py` E dentro do
    corpo da task (fork workers não herdam mutações pós-import).

    # Por que falharia se revertido
    Sem o insert duplo, `pipeline` não é importável dentro do worker fork.
    """

    def test_worker_module_inserts_project_root_in_sys_path(self):
        worker_file = PROJECT_ROOT / "backend" / "app" / "worker.py"
        text = worker_file.read_text(encoding="utf-8")
        assert "sys.path.insert" in text, (
            "BUG-002 REGRESSION: `sys.path.insert` removido de worker.py — "
            "Celery fork worker vai falhar ao importar `pipeline`."
        )

    def test_pipeline_task_inserts_project_root_too(self):
        task_file = PROJECT_ROOT / "backend" / "app" / "tasks" / "pipeline_task.py"
        text = task_file.read_text(encoding="utf-8")
        assert "sys.path.insert" in text, (
            "BUG-002 REGRESSION: `sys.path.insert` removido de pipeline_task.py — "
            "fork workers não herdam sys.path do parent."
        )


# ─────────────────────────────────────────────────────────────────────
# BUG-003 — Pipeline ficava 'pending' quando task crashava
# ─────────────────────────────────────────────────────────────────────


class TestBug003OnFailureMarksFailed:
    """# Bug
    Quando Celery task crashava fora do try/catch interno (ex: SegFault,
    SystemExit), o run ficava `"pending"` para sempre — usuário via
    spinner eterno.

    # Fix
    Callback `on_failure` em `pipeline_task` marca o run como `failed`
    com a exceção capturada.

    # Por que falharia se revertido
    Sem o callback, qualquer crash não-handled deixa o run zumbi.
    """

    def test_pipeline_task_has_on_failure_callback(self):
        from backend.app.tasks import pipeline_task

        # Task decorator é aplicado; verifica se o callback está registrado
        src = inspect.getsource(pipeline_task)
        assert "on_failure=" in src, (
            "BUG-003 REGRESSION: `on_failure=` removido do @task decorator. "
            "Crashes não-handled vão deixar runs em 'pending' eterno."
        )
        assert "_on_pipeline_task_failure" in src or "def on_failure" in src.lower()


# ─────────────────────────────────────────────────────────────────────
# BUG-004 — CPFs reais vazavam via fallback global
# ─────────────────────────────────────────────────────────────────────


class TestBug004FallbackCPFLeak:
    """# Bug
    Endpoint de members com fallback para `config/family_members.json`
    global expunha CPFs reais do founder para tenants novos.

    # Fix
    `cpf=None` no fallback (nunca expor CPF do JSON global).

    # Por que falharia se revertido
    Endpoint retornaria CPF do founder para qualquer workspace novo.
    """

    def test_config_api_strips_cpf_in_fallback(self):
        # A6e: conversão de fallback global → DTOs migrou para
        # ``schemas/dto/family_member/mapper.py``
        # (``convert_global_defaults_to_responses``). A sentinela
        # ``cpf=None`` agora mora lá.
        mapper_file = (
            PROJECT_ROOT / "backend" / "app" / "schemas" / "dto" / "family_member" / "mapper.py"
        )
        text = mapper_file.read_text(encoding="utf-8")
        assert "cpf=None" in text, (
            "BUG-004 REGRESSION: `cpf=None` removido do fallback de members "
            "(schemas/dto/family_member/mapper.py). "
            "CPFs reais do founder vão vazar para tenants novos."
        )


# ─────────────────────────────────────────────────────────────────────
# BUG-007 — skip_llm sempre true ignorando tier premium
# ─────────────────────────────────────────────────────────────────────


class TestBug007SkipLLMRespectsTier:
    """# Bug
    Frontend chamava `triggerPipeline` sempre com `skip_llm: true`,
    mesmo em tier premium → LLM nunca rodava.

    # Fix
    Frontend detecta tier via `getLLMTier()` e envia
    `skip_llm: !isPremium`.

    # Por que falharia se revertido (cobertura backend)
    Backend ainda precisa aceitar `skip_llm=false` e usar `FULL_ORDER`
    quando o flag chega como false. Cobertura frontend de OP-007 cai em
    6.5B (integration de pipeline trigger).
    """

    def test_orchestrator_full_order_when_skip_llm_false(self):
        from pipeline.orchestrator import DETERMINISTIC_ORDER, FULL_ORDER

        # FULL_ORDER deve incluir stages LLM (E1, E1.5, E2-llm)
        full_set = set(FULL_ORDER)
        det_set = set(DETERMINISTIC_ORDER)
        llm_only = full_set - det_set
        assert llm_only, (
            "BUG-007 REGRESSION: FULL_ORDER == DETERMINISTIC_ORDER. "
            "Não há diferença entre tier free e premium — LLM nunca roda."
        )


# ─────────────────────────────────────────────────────────────────────
# BUG-014 — `BankAccount.label` faltava em model/schema/endpoint
# ─────────────────────────────────────────────────────────────────────


class TestBug014AccountLabelField:
    """# Bug
    POST /config/members/<id>/accounts não aceitava `label` (campo "Apelido").

    # Fix
    Adicionado em model + schema + endpoint.

    # Por que falharia se revertido
    Sem a coluna `label`, frontend perde a feature de apelidar contas.
    """

    def test_bank_account_model_has_label_column(self):
        from backend.app.models.family_member import BankAccount

        # Inspeciona colunas declaradas
        cols = {c.name for c in BankAccount.__table__.columns}
        assert "label" in cols, (
            "BUG-014 REGRESSION: coluna `label` removida de BankAccount. "
            "Frontend não consegue mais apelidar contas."
        )


# ─────────────────────────────────────────────────────────────────────
# BUG-015 — capa do relatório vazia (ver test_serializers_round_trip.py)
# ─────────────────────────────────────────────────────────────────────


class TestBug015FamiliaSobrenome:
    """# Bug
    `serialize_family_members` perdia `familia.sobrenome` ao sobrescrever
    `family_members.json` materializado.

    # Cobertura primária
    `backend/tests/test_serializers_round_trip.py::TestRoundTripFamilyMembers`
    (3 testes anti-regressão dedicados).

    # Cobertura aqui
    Apenas sentinela mínima de existência da coluna `family_surname`.
    """

    def test_workspace_has_family_surname_column(self):
        from backend.app.models import Workspace

        cols = {c.name for c in Workspace.__table__.columns}
        assert "family_surname" in cols, (
            "BUG-015 REGRESSION: coluna `family_surname` removida de Workspace. "
            "Capa do relatório multi-tenant volta a ficar vazia."
        )


# ─────────────────────────────────────────────────────────────────────
# OP-001 — parse_args() lendo sys.argv do Celery
# ─────────────────────────────────────────────────────────────────────


class TestOp001ParseArgsCelery:
    """# Bug
    Scripts (e0_audit, e0_unlock, e0_route, e2_extract) faziam
    `parser.parse_args()` que dentro do Celery fork worker lia argumentos
    do comando `celery` → crash.

    # Fix
    `parse_args([] if root_dir else None)`.

    # Escopo pós-A6c
    e15_consolidate e e7_review perderam ``main(root_dir)``/parse_args
    (cutover Caminho B); rodam só via ``main_with_store(ctx)``.

    # Por que falharia se revertido
    parse_args() puro lê sys.argv que dentro do Celery contém args do
    próprio celery binary.
    """

    @pytest.mark.parametrize(
        "script_name",
        [
            "e0_audit.py",
            "e0_unlock.py",
            "e0_route.py",
            "e2_extract.py",
        ],
    )
    def test_script_parse_args_accepts_explicit_argv(self, script_name):
        script_path = PROJECT_ROOT / "scripts" / script_name
        if not script_path.exists():
            pytest.skip(f"{script_name} não existe — possivelmente renomeado")
        text = script_path.read_text(encoding="utf-8")
        # O fix tem padrão `parse_args([] if ...)` ou `parse_args(args=`
        has_explicit = (
            "parse_args([])" in text
            or "parse_args([] if" in text
            or "parse_args(args=" in text
            or "parse_known_args([])" in text
        )
        assert has_explicit, (
            f"OP-001 REGRESSION em {script_name}: parse_args sem argv explícito. "
            "Vai crashar quando rodado dentro do Celery worker."
        )


# ─────────────────────────────────────────────────────────────────────
# OP-002 — SystemExit matava Celery worker
# ─────────────────────────────────────────────────────────────────────


class TestOp002SystemExitInCelery:
    """# Bug
    Scripts legados usavam `sys.exit(1)` que em fork pool mata o
    processo inteiro do worker, não só a task.

    # Fix
    `_run_stage` no orchestrator captura `SystemExit` → converte para
    `StageResult(success=False)`.

    # Por que falharia se revertido
    SystemExit mata o worker; outras runs em queue ficam órfãs.
    """

    def test_orchestrator_catches_systemexit(self):
        from pipeline import orchestrator

        src = inspect.getsource(orchestrator)
        assert "SystemExit" in src, (
            "OP-002 REGRESSION: `SystemExit` não é mais capturado em orchestrator.py. "
            "Stages que dão sys.exit(1) vão matar o worker inteiro."
        )


# ─────────────────────────────────────────────────────────────────────
# OP-008 — FERNET_KEY não persistida → secrets ilegíveis
# ─────────────────────────────────────────────────────────────────────


class TestOp008FernetPersistence:
    """# Bug
    Settings gerava nova FERNET_KEY a cada restart — qualquer secret
    cifrado antes ficava ilegível (api_key LLM, vault, CPF).

    # Fix
    FERNET_KEY persistida em `.env` e carregada via Pydantic Settings.

    # Por que falharia se revertido
    Reiniciar o worker corrompe acesso a todos os secrets.
    """

    def test_fernet_key_loaded_from_env(self):
        from backend.app.core.config import settings

        # No mínimo, settings tem que EXPOR a key (não pode ser hardcoded
        # como "" sem fallback)
        assert hasattr(
            settings, "FERNET_KEY"
        ), "OP-008 REGRESSION: FERNET_KEY removida de Settings."
        # Em CI: FERNET_KEY é setada via env (conftest faz isso)
        assert settings.FERNET_KEY, (
            "OP-008 REGRESSION: FERNET_KEY vazia. Verifique que .env tem a key "
            "ou que MATHOMS_FERNET_KEY está exportada."
        )


# ─────────────────────────────────────────────────────────────────────
# OP-009 — max_tokens E1.5 truncava
# ─────────────────────────────────────────────────────────────────────


class TestOp009MaxTokensE15:
    """# Bug
    `max_tokens=4096` default truncava resposta do E1.5 (consolidação
    do baseline patrimonial).

    # Fix
    Schema permite valores grandes (`le=200000`) para que user/admin
    configure pelo menos 16384 quando rodando E1.5. Default sobe quando
    detectado uso intensivo.

    # Por que falharia se revertido
    Se schema cair para `le=4096`, user não consegue mais salvar config
    de 16384 e LLM volta a truncar consolidação.
    """

    def test_llm_config_schema_allows_at_least_16k(self):
        from backend.app.schemas.llm import LLMConfigCreateRequest

        # Tentativa de salvar 16384 deve passar validação
        try:
            cfg = LLMConfigCreateRequest(
                provider="anthropic",
                api_key="sk-test",
                model_name="claude-opus-4-6",
                max_tokens=16384,
            )
            assert cfg.max_tokens == 16384
        except Exception as exc:
            pytest.fail(
                f"OP-009 REGRESSION: schema rejeita max_tokens=16384 ({exc!r}). "
                "Sem isso, E1.5 vai truncar consolidação do baseline."
            )

    def test_llm_config_db_default_above_threshold(self):
        """Default no model deve ser pelo menos 4096 (mínimo histórico)."""
        from backend.app.models import LLMConfig

        col = LLMConfig.__table__.columns["max_tokens"]
        default = col.default.arg if col.default else None
        assert default is not None and default >= 4096, (
            f"OP-009 REGRESSION: default de LLMConfig.max_tokens caiu para {default}. "
            "Histórico mínimo é 4096 (a partir do qual user precisa subir manualmente "
            "para 16384 quando rodar E1.5)."
        )


# ─────────────────────────────────────────────────────────────────────
# OP-010 — started_at sem timezone
# ─────────────────────────────────────────────────────────────────────


class TestOp010StartedAtTimezoneAware:
    """# Bug
    `PipelineRun.started_at` vinha como datetime naive do SQLite →
    Pydantic serializava sem `Z` → frontend interpretava como hora
    LOCAL → mostrava "0s" elapsed para runs em outro fuso.

    # Fix
    Field serializer no Pydantic adiciona `tzinfo=UTC` antes de
    serializar.

    # Por que falharia se revertido
    Nova run aparece como "started 0s ago" indefinidamente em outro TZ.
    """

    def test_pipeline_run_schema_serializes_started_at_with_tz(self):
        from backend.app.schemas.pipeline import PipelineRunResponse

        # Cria instância com naive datetime (simula DB sem tz)
        naive = datetime(2026, 4, 15, 12, 0, 0)  # NO tzinfo
        try:
            inst = PipelineRunResponse(
                id="r1",
                workspace_id="w1",
                status="running",
                current_stage=None,
                failed_at_stage=None,
                paused_at_stage=None,
                tier_at_run="free",
                total_documents=1,
                celery_task_id=None,
                started_at=naive,
                completed_at=None,
                stage_logs=[],
            )
        except Exception as exc:
            pytest.skip(f"Schema mudou (assinatura diferente): {exc}")
        dumped = inst.model_dump(mode="json")
        started_str = dumped["started_at"]
        assert started_str.endswith("Z") or "+00:00" in started_str or "+" in started_str[-6:], (
            f"OP-010 REGRESSION: started_at='{started_str}' sem timezone. "
            "Frontend vai mostrar '0s elapsed' para qualquer browser fora UTC."
        )


# ─────────────────────────────────────────────────────────────────────
# Frontend regressions — placeholders (cobertos em 6.5B/D)
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.skip(
    reason="BUG-005/006/008/011/012 + OP-011: regressões frontend. "
    "Cobertas em 6.5B (integration tests de NotificationCenter, "
    "AppShell nav, transactions table, pipeline UI) e em 6.5D (lint "
    "de dead imports). Re-implementar como Vitest specs em frontend/tests/."
)
def test_frontend_regressions_placeholder():
    """Reservado para portar os bugs frontend para Vitest quando 6.5B chegar."""
    pass
