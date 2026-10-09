"""O parecer recebe o veredito do balde de imóvel ([[A40.l123]] · [[ADR-439]]).

O gate de cobertura confere só a CABEÇA do path (`$.patrimonio`): um subpath errado passa
verde e a linha some calada (`on_null: skip`). Por isso cada regime é montado pelo
PRODUTOR, com a fiação do `PatrimonioCalculator`, e o valor esperado sai do objeto do
produtor — nunca de `walk_path` sobre o path do manifest, que resolveria `None` nos dois
lados de um path errado. Mede-se o CORPO orçado: os hints citam os códigos por definição,
e medir o texto inteiro daria verde pela guidance, não pelo dado. Fixtures PII-zero.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from backend.app.services.parecer_distiller import distill_exec_context
from backend.app.services.parecer_manifest import load_manifest
from dev import _planner_coverage_internals as internals
from pipeline.domain.services.patrimonio_imovel_classifier import (
    split_imoveis_geradores_vs_nao_geradores,
    split_imoveis_with_overrides,
)
from pipeline.domain.services.veredito_balde_imovel import (
    RESIDENCIA_ALUGADA,
    RESIDENCIA_NAO_DECLARADA,
    RESIDENCIA_PROPRIA,
    MotivoBaldeImovel,
    classificar_imoveis_do_run,
)
from pipeline.llm.value_formatter import format_value
from tests.test_parecer_distiller_exec_context import make_dogfood_like_e5

_HINTS_HEADER = "### Diretrizes de leitura por seção (hints)"
_MARKER = "[exec context truncado em max_exec_context_bytes"
_BLOCO = "$.patrimonio.cobertura_classificacao_imovel"
_SEM_VALOR = {"valor_nao_apurado": {"anos": ["2025"]}}
_CASA = {"property_id": "pid-casa", "valor": 500_000.0}
_SALA = {"property_id": "pid-sala", "valor": 150_000.0}
_SEM_ID = {"valor": 190_000.0}

# (imóveis, overrides, residencia_status) — o regime U5 é o do run `40d1af2a`: casa
# identificada como piso e os overrides `locado` sem imóvel no run.
_REGIMES = {
    "golden_dogfood": ([_SEM_ID, _SALA], {"pid-sala": "locado"}, RESIDENCIA_NAO_DECLARADA),
    "u5": (
        [_CASA, _SEM_ID],
        {"pid-casa": "residencia_principal", "pid-x": "locado"},
        RESIDENCIA_PROPRIA,
    ),
    "tudo_apurado": (
        [_CASA, _SALA],
        {"pid-casa": "residencia_principal", "pid-sala": "locado"},
        RESIDENCIA_PROPRIA,
    ),
    "aluga": ([_SALA], {"pid-sala": "locado"}, RESIDENCIA_ALUGADA),
    "casa_sem_valor": (
        [{"property_id": "pid-casa", **_SEM_VALOR}],
        {"pid-casa": "residencia_principal"},
        RESIDENCIA_PROPRIA,
    ),
    "casa_nao_localizada": ([_SEM_ID], {"pid-casa": "residencia_principal"}, RESIDENCIA_PROPRIA),
    "casa_nao_classificada": ([_SEM_ID], {}, RESIDENCIA_PROPRIA),
    "gerador_sem_valor": (
        [{"property_id": "pid-sala", **_SEM_VALOR}],
        {"pid-sala": "locado"},
        RESIDENCIA_ALUGADA,
    ),
    "sem_imovel": ([], {}, RESIDENCIA_NAO_DECLARADA),
}


def _bloco_do_produtor(regime: str) -> dict:
    """O bloco que o calculator publicaria: mesmos splitters, mesmo produtor."""
    imoveis, overrides, status = _REGIMES[regime]
    bens = {"imoveis": [dict(i) for i in imoveis]}
    kwargs = {"titular_bens": bens, "conjuge_bens": {}, "overrides_by_property_id": overrides}
    residencia, _outros = split_imoveis_with_overrides(**kwargs)
    geradores, _nao_geradores = split_imoveis_geradores_vs_nao_geradores(**kwargs)
    return classificar_imoveis_do_run(
        titular_bens=bens,
        conjuge_bens={},
        overrides=overrides,
        residencia_status=status,
        residencia=residencia,
        geradores=geradores,
    ).bloco()


def _e5(bloco: dict | None) -> dict:
    patrimonio = {"bruto": 1_000_000.0, "liquido": 900_000.0}
    if bloco is not None:
        patrimonio["cobertura_classificacao_imovel"] = bloco
    return {"patrimonio": patrimonio}


def _corpo(manifest, e5: dict) -> str:
    return distill_exec_context(manifest, e5).split(_HINTS_HEADER, 1)[0]


def _esperado(bloco: dict) -> dict[str, object]:
    """path do manifest → valor do produtor. A CHAVE é o contrato: o teste a compara ao
    conjunto declarado, então campo novo no manifest exige decisão aqui."""
    return {
        f"{_BLOCO}.pct_desconhecido": bloco["pct_desconhecido"],
        f"{_BLOCO}.residencia.status": bloco["residencia"]["status"],
        f"{_BLOCO}.residencia.motivo": bloco["residencia"]["motivo"],
        f"{_BLOCO}.imoveis_geradores.status": bloco["imoveis_geradores"]["status"],
    }


def _campos_do_bloco(manifest) -> dict[str, dict]:
    return {
        f["path"]: f
        for section in manifest.sections
        for block in section.get("blocks", []) or []
        for f in block.get("fields", []) or []
        if str(f.get("path", "")).startswith(_BLOCO)
    }


def _linhas_faltantes(manifest, bloco: dict) -> list[str]:
    """Linha esperada que não está no corpo (ou que está quando o valor é null)."""
    campos, corpo, faltas = _campos_do_bloco(manifest), _corpo(manifest, _e5(bloco)), []
    for path, valor in _esperado(bloco).items():
        campo = campos.get(path)
        if campo is None:
            faltas.append(f"não declarado: {path}")
            continue
        linha = f"{campo['label']}: {format_value(valor, campo['format'])}"
        if (valor is not None) != (linha in corpo):
            faltas.append(f"{path} → {linha!r}")
    return faltas


@pytest.mark.parametrize("regime", sorted(_REGIMES))
def test_o_corpo_carrega_o_veredito_do_produtor(regime: str) -> None:
    assert _linhas_faltantes(load_manifest(), _bloco_do_produtor(regime)) == []


def test_o_manifest_declara_exatamente_os_campos_decididos() -> None:
    """Igualdade de conjunto: projetar campo a mais (R$, contagem) exige revisitar a decisão."""
    declarados = set(_campos_do_bloco(load_manifest()))
    assert declarados == set(_esperado(_bloco_do_produtor("u5")))


def test_mutacao_de_subpath_reprova() -> None:
    """O gate de cobertura passaria verde com este typo — este teste não."""
    manifest = load_manifest()
    secoes = json.loads(
        json.dumps(manifest.sections).replace(".residencia.motivo", ".residencia.motive")
    )
    mutado = dataclasses.replace(manifest, sections=secoes)
    assert _linhas_faltantes(mutado, _bloco_do_produtor("casa_nao_classificada"))


def test_os_regimes_exercitam_todo_motivo_do_produtor() -> None:
    """Motivo novo no enum sem regime aqui reprova — senão escaparia do teste de hints."""
    vistos = {
        b[balde]["motivo"]
        for b in map(_bloco_do_produtor, _REGIMES)
        for balde in ("residencia", "imoveis_geradores")
    }
    assert vistos - {None} == {m.value for m in MotivoBaldeImovel}


def _hints(manifest, secao: str) -> str:
    return " ".join(next(s for s in manifest.sections if s["id"] == secao)["narrative_hints"])


def test_todo_codigo_da_residencia_tem_leitura_nos_hints() -> None:
    """Por balde: `sem_valor` é dos dois, e um hint só não pode cobrir o outro."""
    hints = _hints(load_manifest(), "patrimonio")
    codigos = {
        valor
        for b in map(_bloco_do_produtor, _REGIMES)
        for valor in (b["residencia"]["status"], b["residencia"]["motivo"])
        if valor not in (None, "apurado")
    }
    assert codigos and {c for c in codigos if c not in hints} == set()


def test_o_veredito_dos_imoveis_de_renda_tem_leitura_no_hint_de_if() -> None:
    assert "nao_apurado" in _hints(load_manifest(), "independencia_financeira")


def test_a_label_da_fatia_declara_a_base() -> None:
    """A fatia é do VALOR de imóveis, não da carteira — a base vai na label (A37.l9)."""
    campo = _campos_do_bloco(load_manifest())[f"{_BLOCO}.pct_desconhecido"]
    assert "% do valor total de imóveis" in campo["label"]


# ---------------------------------------------------------------------------
# Snapshot anterior ao bloco e orçamento do corpo
# ---------------------------------------------------------------------------


def _sem_os_campos(manifest):
    secoes = json.loads(json.dumps(manifest.sections))
    for block in (b for secao in secoes for b in secao.get("blocks", []) or []):
        if "fields" in block:
            block["fields"] = [f for f in block["fields"] if not f["path"].startswith(_BLOCO)]
    return dataclasses.replace(manifest, sections=secoes)


def test_snapshot_sem_o_bloco_renderiza_o_mesmo_corpo() -> None:
    """E5 anterior ao #2049: só hints e catálogo mudam, nenhuma linha órfã no corpo."""
    manifest = load_manifest()
    assert _corpo(manifest, _e5(None)) == _corpo(_sem_os_campos(manifest), _e5(None))


# O E5 real do dogfood já evicta `plano_acao_atual`; a seção seguinte da fila é
# `investimentos`. O teto abaixo é o crescimento que esta decisão comprou no pior regime
# (motivo mais longo, fatia de três dígitos) — subir exige re-medir a eviction no E5 real.
_TETO_DO_BLOCO_BYTES = 240


def test_o_bloco_cabe_no_orcamento_declarado() -> None:
    manifest = load_manifest()
    e5 = make_dogfood_like_e5()
    # Todo E5 desde a A40.l83 publica o diagnóstico, então o título do bloco de incerteza
    # já está no corpo: sem isto o teste cobraria o título como custo desta decisão.
    e5["diagnostico_confianca"] = {"nivel": "alta"}
    e5["patrimonio"]["cobertura_classificacao_imovel"] = _bloco_do_produtor("casa_nao_classificada")
    e5["patrimonio"]["cobertura_classificacao_imovel"]["pct_desconhecido"] = 100.0
    com, sem = (len(_corpo(m, e5).encode()) for m in (manifest, _sem_os_campos(manifest)))
    assert 0 < com - sem <= _TETO_DO_BLOCO_BYTES
    assert _MARKER not in _corpo(manifest, e5)


# ---------------------------------------------------------------------------
# Gate de drift: a subárvore deixa de estar escapada em bloco
# ---------------------------------------------------------------------------


def test_folha_nova_do_bloco_nao_nasce_escapada() -> None:
    """O escape amplo engolia a subárvore: folha nova do bloco passava sem decisão."""
    assert not internals._escapado(f"{_BLOCO}.campo_futuro")


def test_toda_folha_do_bloco_tem_decisao_propria() -> None:
    """Projetada ou escapada com razão — nenhuma vai calada para o débito herdado."""
    schema = internals.load_json(internals.REPO_ROOT / "config/schemas/e5_analysis.schema.json")
    projetados = internals._paths_projetados(
        internals.REPO_ROOT / "config/prompts/parecer_planejador.yaml"
    )
    folhas = {p for p in internals._e5_leaf_paths(schema) if p.startswith(f"{_BLOCO}.")}
    sem_decisao = {
        p
        for p in folhas
        if not internals._coberto_pelo_manifest(p, projetados) and not internals._escapado(p)
    }
    assert folhas and sem_decisao == set()
