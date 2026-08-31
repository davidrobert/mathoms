"""Substrato compartilhado dos goldens E3→E4→E5 (A23.l2): config mínima de tenant + run puro num ``InMemoryArtifactStore`` ([[ADR-212]]), determinístico. Reusado pelos invariantes de conservação, snapshot do view-model e fixture dogfood."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from pipeline.ports.config_store import FiscalParametersAusentes

_REPO = Path(__file__).resolve().parents[1]
_LEGACY_CONFIGS = _REPO / "tests" / "fixtures" / "legacy_configs"

_DEFAULT_FAMILY = {
    "titular": "david",
    "membros": {"david": {"nome_curto": "David", "data_nascimento": "1985-06-15"}},
}
_DEFAULT_GOALS = {"independencia_financeira": {"if_meta": 1_000_000.0, "trs_pct": 4.0}}


def _dump(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _categorization(
    expense_keywords: dict | None,
    income_keywords: dict | None = None,
    internal_transfer_patterns: list[str] | None = None,
) -> dict:
    return {
        "expense_keywords": expense_keywords or {},
        "income_keywords": income_keywords or {"renda": ["PIX"]},
        "internal_transfer_patterns": internal_transfer_patterns or [],
        "pj_source_mapping": {},
        "clt_source_mapping": {},
    }


#: Tabela anual literal de ``fiscal_parameters`` (seed y3z4a5b6c7d8), em reais —
#: a forma que ``PrevidenciaConfig.from_fiscal`` lê.
FAIXAS_IRPF_SEEDADAS = [
    {"limite_anual": 26_963.20, "aliquota_pct": 0.0},
    {"limite_anual": 33_919.80, "aliquota_pct": 7.5},
    {"limite_anual": 45_012.60, "aliquota_pct": 15.0},
    {"limite_anual": 55_976.16, "aliquota_pct": 22.5},
    {"limite_anual": None, "aliquota_pct": 27.5},
]


def _copy_legacy(cfg: Path, irpf_faixas: list[dict] | None) -> None:
    shutil.copy(_REPO / "config" / "scoring.json", cfg / "scoring.json")
    shutil.copy(_LEGACY_CONFIGS / "parametros_fiscais.json", cfg / "parametros_fiscais.json")
    shutil.copy(_LEGACY_CONFIGS / "taxas.json", cfg / "taxas.json")
    if irpf_faixas is not None:
        _injetar_faixas(cfg / "parametros_fiscais.json", irpf_faixas)


# A fixture legada declara a tabela MENSAL pós-Lei 15.270 sob `faixas_mensais`,
# chave que nenhum leitor do repo consome — por isso o analyzer caía no fallback
# de 7,5%. Gravar `faixas` (anual, pré-Lei) no arquivo commitado faria um JSON
# declarar duas leis; a injeção vive só no tmp da suíte que a pede (A40.l34).
def _injetar_faixas(destino: Path, faixas: list[dict]) -> None:
    fiscal = json.loads(destino.read_text(encoding="utf-8"))
    fiscal.setdefault("irpf_tabela_progressiva", {})["faixas"] = faixas
    _dump(destino, fiscal)


def write_e5_config(
    tmp_path: Path,
    *,
    family: dict | None = None,
    goals: dict | None = None,
    expense_keywords: dict | None = None,
    income_keywords: dict | None = None,
    internal_transfer_patterns: list[str] | None = None,
    irpf_faixas: list[dict] | None = None,
) -> None:
    """Escreve config mínima de tenant para rodar E4/E5 isolado."""
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    cat = _categorization(expense_keywords, income_keywords, internal_transfer_patterns)
    _dump(cfg / "categorization.json", cat)
    _dump(cfg / "family_members.json", family or _DEFAULT_FAMILY)
    _dump(cfg / "goals.json", goals or _DEFAULT_GOALS)
    (cfg / "pipeline.json").write_text("{}", encoding="utf-8")
    _copy_legacy(cfg, irpf_faixas)


def _seed_store(
    e3_payloads: dict[str, dict],
    baseline: dict | None,
    irpf_payloads: dict[str, dict] | None = None,
):
    from pipeline.artifact_store import InMemoryArtifactStore

    store = InMemoryArtifactStore()
    for key, payload in e3_payloads.items():
        store.seed("E3", key, payload)
    if baseline is not None:
        store.seed("E1.5c", "baseline_patrimonial", baseline)
    for key, payload in (irpf_payloads or {}).items():
        store.seed("extract_irpf_full", key, payload)
    return store


# `config_store` é OPT-IN por decisão (A40.l56): com ele, `analyze_finances`
# troca `PrevidenciaConfig.from_fiscal` (dict legado) por `from_fiscal_parameters`
# (o construtor de PRODUÇÃO). Injetar no substrato compartilhado trocaria o
# construtor em TODOS os goldens de E5 e forçaria rebaseline geral — o default
# `None` mantém os existentes no caminho legado e deixa UM golden novo exercitar
# o de produção.
def _stages_e4_e5():
    """Import tardio: o substrato é importado por testes que não sobem o pipeline."""
    from pipeline.context import WorkspaceContext
    from scripts.analyze_finances import main_with_store as e5_mws
    from scripts.categorize_transactions import main_with_store as e4_mws

    return WorkspaceContext, e4_mws, e5_mws


def run_e3_e4_e5(root: Path, **kwargs) -> dict[str, Any]:
    """Payload E5; use ``run_e3_e4_e5_ctx`` quando precisar também do artefato E4."""
    return run_e3_e4_e5_ctx(root, **kwargs).artifact_store.read("E5", "analise_financeira")


def run_e3_e4_e5_ctx(
    root: Path,
    *,
    e3_payloads: dict[str, dict],
    baseline: dict | None = None,
    irpf_payloads: dict[str, dict] | None = None,
    config_store: Any | None = None,
):
    """Roda E4→E5 sobre E3 seeded e devolve o ``ctx``; ``irpf_payloads`` semeia
    extract_irpf_full (DE-02)."""
    contexto, e4_mws, e5_mws = _stages_e4_e5()
    store = _seed_store(e3_payloads, baseline, irpf_payloads)
    ctx = contexto(root=root, artifact_store=store, config_store=config_store)
    e4_mws(ctx)
    e5_mws(ctx)
    return ctx


def _tabelas_da_migration_adr389() -> dict:
    import importlib.util

    caminho = (
        Path(__file__).resolve().parents[1]
        / "backend"
        / "alembic"
        / "versions"
        / "adr389tabelas_ir_brackets_anual_e_mensal.py"
    )
    spec = importlib.util.spec_from_file_location("_adr389_golden", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.TABELAS_POR_ANO


# Deriva da constante da MIGRATION, não de literais aqui: golden com execução
# real sobre tabela fantasiada mede a fantasia.
def _ano_inicial_regime_completo() -> int:
    import importlib.util

    caminho = (
        Path(__file__).resolve().parents[1]
        / "backend"
        / "alembic"
        / "versions"
        / "adr414flip_ac2026.py"
    )
    spec = importlib.util.spec_from_file_location("_adr414flip_golden", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ANO_INICIAL_REGIME_COMPLETO


# A ADR-389 semeou AC2026 incompleto; a migration do flip o completou. A fixture
# compõe as DUAS, senão afirma uma retenção que a produção deixou de fazer —
# divergência fixture↔produção medida no ataque à A40.l64.
def _modulo_da_migration(nome: str):
    import importlib.util

    caminho = Path(__file__).resolve().parents[1] / "backend" / "alembic" / "versions" / nome
    spec = importlib.util.spec_from_file_location(f"_golden_{nome}", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _redutor_da_migration() -> dict:
    return _modulo_da_migration("adr414redutor_lei_15270.py").REDUTOR_POR_ANO[2026]["anual"]


def _limiar_irpfm_da_migration() -> int:
    return _modulo_da_migration("adr414irpfm_limiar.py")._LIMIAR_2026_CENTS


def _dados_efetivos(tabelas: dict, year: int) -> dict:
    # SEM clamp `max(a <= year)`. Ele era invenção da fixture: a produção resolve
    # por vigência (`effective_from/to`) e LEVANTA em ano não semeado. Servir a
    # linha de 2026 para 2027 deixava o golden verde num eixo em que a produção
    # falha — a divergência fixture↔produção que a [[A40.l79]] fecha.
    if year not in tabelas:
        raise FiscalParametersAusentes(
            f"seed da migration ADR-389 não cobre {year}; anos: {sorted(tabelas)}"
        )
    dados = dict(tabelas[year])
    if year >= _ano_inicial_regime_completo():
        dados["regime_completo"] = True
        dados["componentes_ausentes"] = []
        # Compor SÓ o `regime_completo` deixava o golden rodando um regime que não
        # existe: completo, mas sem redutor e sem piso do IRPFM. A produção tem os
        # três. É a mesma divergência fixture↔produção que o ataque a esta lane
        # mediu — recriada ao compor uma migration e esquecer as outras duas.
        dados["redutor_anual"] = _redutor_da_migration()
        dados["irpfm_limiar_brl_cents"] = _limiar_irpfm_da_migration()
    return dados


def fiscal_store_do_seed(year: int):
    """``InMemoryConfigStore`` com as tabelas que a migration ADR-389 grava."""
    from pipeline.adapters.fiscal_parsers import fiscal_payload_to_dataclass
    from pipeline.adapters.in_memory_config_store import InMemoryConfigStore

    tabelas = _tabelas_da_migration_adr389()
    dados = _dados_efetivos(tabelas, year)
    fiscal = fiscal_payload_to_dataclass(
        {
            "year": year,
            "ir_brackets_anual": dados["anual"],
            "ir_brackets_mensal": dados["mensal"],
            "regime_completo": dados["regime_completo"],
            "componentes_ausentes": dados["componentes_ausentes"],
            "redutor_anual": dados.get("redutor_anual") or {},
            "irpfm_limiar_brl_cents": dados.get("irpfm_limiar_brl_cents") or 0,
            "lucro_presumido_aliquota": "0.32",
        }
    )
    return InMemoryConfigStore(fiscal_by_year={year: fiscal})


#: Workspace do golden. `property_id` só é cunhado quando resolver E workspace_id
#: estão injetados (`consolidate_baseline` §3), e sem `property_id` o splitter de
#: cat_2 ignora override nenhum — a fixture declararia classificação que o motor
#: não lê.
_WORKSPACE_DO_GOLDEN = "golden-dogfood"

#: As classificações que a fixture do dogfood declara, por `endereco_canonical`
#: ([[ADR-420]] §Critério de aceite 2). O apartamento fica DE PROPÓSITO sem
#: override: é o regime default (imóvel sem classificação nenhuma), classe de
#: defeito distinta que o §Follow-up da [[A40.l95]] mantém viva. Os cinco valores
#: são dois-a-dois distintos e somam os mesmos 600.000 do imóvel único que
#: substituíram — o split move o eixo de classificação sem mover o bruto.
CLASSIFICACOES_DO_DOGFOOD: dict[str, str] = {
    "ficticia 200": "locado",
    "ficticia 300": "especulacao",
    "ficticia 400": "nu_proprietario",
    "ficticia 500": "uso_pessoal",
}


class _OverridesDaFixture:
    """``PropertyOverridesResolver`` de fixture — mapa já resolvido por id."""

    def __init__(self, por_property_id: dict[str, str]) -> None:
        self._por_property_id = dict(por_property_id)

    def list_for_workspace(self, workspace_id: str) -> dict[str, str]:
        return dict(self._por_property_id)


# O mapa só existe DEPOIS do E1.5c: o `property_id` é cunhado lá, e a fixture não
# pode escrevê-lo (é uuid4, e fixá-lo divergiria da regra de mint da produção).
# `endereco_canonical` é a ponte determinística entre os dois momentos.
#
# Casa o que existir e não reclama do resto: `run_dogfood_pipeline` também é o RUNNER
# de baselines próprios (`test_e5_reserva_formula_canonica`), e falhar ali seria falso
# positivo. Quem guarda a discriminação é
# `test_golden_discrimina_classificacao_de_imovel.py::test_a_classificacao_declarada_e_LOAD_BEARING`:
# se o dogfood perder as classificações, `imoveis_geradores` volta a zero e ele reprova.
def _overrides_por_id(consolidado: dict, por_endereco: dict[str, str]) -> dict[str, str]:
    mapa = {}
    for imovel in consolidado.get("imoveis_consolidados") or []:
        classificacao = por_endereco.get(imovel.get("endereco_canonical") or "")
        if classificacao and imovel.get("property_id"):
            mapa[imovel["property_id"]] = classificacao
    return mapa


def _seed_dogfood_store(raw_baseline: dict, e2_extracts: dict[str, dict]):
    from pipeline.artifact_store import InMemoryArtifactStore

    store = InMemoryArtifactStore()
    store.seed("E1.5", "baseline_patrimonial", raw_baseline)
    for key, payload in e2_extracts.items():
        store.seed("E2-extratos", key, payload)
    return store


# Extraído de ``run_dogfood_pipeline`` em A40.l4: a fixture compartilhada das
# narrativas roda E5.N **em cima** deste substrato, e a única coisa que faltava
# era acesso ao ctx (o store é onde o E5.N lê e escreve).
def _ctx_com_identidade(root: Path, raw_baseline: dict, e2_extracts: dict[str, dict]):
    """``ctx`` que cunha ``property_id`` — sem ele o splitter ignora override nenhum."""
    from pipeline.adapters.in_memory_property_identity_resolver import (
        InMemoryPropertyIdentityResolver,
    )
    from pipeline.context import WorkspaceContext

    return WorkspaceContext(
        root=root,
        artifact_store=_seed_dogfood_store(raw_baseline, e2_extracts),
        workspace_id=_WORKSPACE_DO_GOLDEN,
        property_identity_resolver=InMemoryPropertyIdentityResolver(),
    )


def _aplicar_overrides(ctx, property_classifications: dict[str, str] | None) -> None:
    """Só depois do E1.5c: é lá que o ``property_id`` da ponte é cunhado."""
    por_endereco = (
        CLASSIFICACOES_DO_DOGFOOD if property_classifications is None else property_classifications
    )
    consolidado = ctx.artifact_store.read("E1.5c", "baseline_patrimonial")
    ctx.property_overrides_resolver = _OverridesDaFixture(
        _overrides_por_id(consolidado, por_endereco)
    )


# ``property_classifications`` mapeia ``endereco_canonical`` → classificação; ``None``
# usa ``CLASSIFICACOES_DO_DOGFOOD`` e ``{}`` roda o regime default, sem override nenhum.
def run_dogfood_pipeline_ctx(
    root: Path,
    *,
    raw_baseline: dict,
    e2_extracts: dict[str, dict],
    property_classifications: dict[str, str] | None = None,
):
    """Roda E1.5c→E3→E4→E5 e devolve o ``ctx``, para quem precisa continuar o run."""
    from scripts.analyze_finances import main_with_store as e5_mws
    from scripts.categorize_transactions import main_with_store as e4_mws
    from scripts.consolidate_baseline import main_with_store as e15_mws
    from scripts.reconcile_transactions import main_with_store as e3_mws

    ctx = _ctx_com_identidade(root, raw_baseline, e2_extracts)
    e15_mws(ctx)
    _aplicar_overrides(ctx, property_classifications)
    for stage in (e3_mws, e4_mws, e5_mws):
        stage(ctx)
    return ctx


def run_dogfood_pipeline(
    root: Path,
    *,
    raw_baseline: dict,
    e2_extracts: dict[str, dict],
    property_classifications: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Roda E1.5c→E3→E4→E5 sobre baseline bruto + extratos E2 seeded; exercita dedup genuíno (ADR-271 em E1.5c, ADR-255 em E3); retorna ``analise_financeira``."""
    ctx = run_dogfood_pipeline_ctx(
        root,
        raw_baseline=raw_baseline,
        e2_extracts=e2_extracts,
        property_classifications=property_classifications,
    )
    return ctx.artifact_store.read("E5", "analise_financeira")


def load_fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
