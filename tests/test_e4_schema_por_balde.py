"""A42.l19 — contrato dos 7 baldes do stage `categorize_transactions`.

`SCHEMA_BY_STAGE` é 1:1 stage→schema: os 7 baldes batiam contra um único
`e4_unified.schema.json`, um `oneOf` de 5 ramos. Medido no produtor real:
2 ramos eram mortos (o de receitas/despesas declarava `periodo` como object,
o produtor emite string; o placeholder `{status}` nenhum produtor emitia),
5 dos 7 baldes passavam pelo ramo mais frouxo (`required: ["dados"]` com
`dados: {}`, que não restringe nada) e o `patrimonio` não casava com ramo
nenhum — reprovando em `$` e sendo gravado assim mesmo em modo `warn`.

O discriminador já existia: a `artifact_key`, coluna da própria row.

Dois cuidados que estes testes carregam:

- **A existência do schema é afirmada.** `validate_dict` faz short-circuit
  para True quando o arquivo não existe, então teste com nome literal de
  schema passa verde antes do fix (mesma armadilha da A40.l74).
- **O controle é positivo.** Não basta os baldes reais validarem: o payload
  que o guard ACEITAVA antes precisa reprovar agora, balde a balde.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.services.storage.db_artifact_store import (  # noqa: E402
    SCHEMA_BY_STAGE,
    SCHEMA_BY_STAGE_KEY,
    _schema_version_token,
    resolve_schema_name,
)
from pipeline.domain.services.e4_serialization import ARTIFACT_KEYS  # noqa: E402
from scripts.pipeline_common import CONFIG_DIR, validate_dict  # noqa: E402

_STAGES_E4 = ("E4", "categorize_transactions")

# Shape que o ramo placeholder aceitava. Nenhum produtor E4 o emite — ele existia
# só como buraco de aceitação.
_SHAPE_PLACEHOLDER = {"status": "vazio"}

# Balde de fluxo escrito no shape de cashflow: troca de balde, não placeholder.
# Passava pelo ramo `dados` do umbrella porque `dados: {}` não restringe nada.
_SHAPE_CASHFLOW = {
    "consolidation_date": "2026-01-01",
    "periodo": "2026-01",
    "categorias": [],
    "total_categorias": 0,
    "total_transacoes": 0,
    "totais_por_categoria": {},
    "total_geral": 0.0,
    "dados": {},
}


@pytest.fixture
def strict(monkeypatch) -> None:
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")


@pytest.fixture(scope="module")
def baldes_reais() -> dict[str, dict]:
    """Os 7 baldes como o produtor real os emite (E3 + baseline E1.5c do golden)."""
    from scripts.categorize_transactions import main_with_store
    from tests.test_e4_golden_execution import (
        _BASELINE_MIN,
        _E3_FIXTURE,
        _new_e4_ctx,
        _write_e4_config,
    )

    root = Path(tempfile.mkdtemp())
    _write_e4_config(root)
    ctx = _new_e4_ctx(root, e3_fixture=_E3_FIXTURE, baseline=_BASELINE_MIN)
    main_with_store(ctx)
    store = ctx.artifact_store
    return {key: store.read("E4", key) for key in store.list_keys("E4")}


# ───────────────────────── completude do mapa ─────────────────────────


@pytest.mark.parametrize("stage", _STAGES_E4)
def test_todo_balde_tem_schema_por_chave(stage: str) -> None:
    """Igualdade de conjunto, não continência: balde novo sem entrada cairia no
    backstop do stage e reabriria o buraco em silêncio; entrada órfã aponta para
    balde que ninguém escreve."""
    mapeados = {key for (s, key) in SCHEMA_BY_STAGE_KEY if s == stage}
    assert mapeados == set(ARTIFACT_KEYS), (
        f"{stage}: mapa por chave dessincronizado de ARTIFACT_KEYS — "
        f"sem schema: {sorted(set(ARTIFACT_KEYS) - mapeados)}; "
        f"órfãos: {sorted(mapeados - set(ARTIFACT_KEYS))}"
    )


def test_legado_e_descritivo_resolvem_o_mesmo_schema() -> None:
    """Paridade legacy↔descritivo (janela F9.2→F9.6): `E4` e `categorize_transactions`
    não podem validar o mesmo balde contra contratos diferentes."""
    for key in ARTIFACT_KEYS:
        assert resolve_schema_name("E4", key) == resolve_schema_name("categorize_transactions", key)


def test_schema_resolvido_existe_em_disco() -> None:
    """`validate_dict` faz short-circuit para True no arquivo ausente — schema que
    não existe é indistinguível de contrato cumprido."""
    for key in ARTIFACT_KEYS:
        nome = resolve_schema_name("E4", key)
        assert (CONFIG_DIR / "schemas" / nome).exists(), f"{key}: schema {nome} não existe"


def test_stage_sem_entrada_por_chave_segue_resolvendo_por_stage() -> None:
    """O mapa por chave acrescenta precisão; não troca o mecanismo."""
    assert resolve_schema_name("E3", "qualquer_grupo") == SCHEMA_BY_STAGE["E3"]
    assert resolve_schema_name("E1", "members") is None


def test_token_de_schema_discrimina_baldes() -> None:
    """Token por stage daria o mesmo hash aos 7 baldes e a coluna `schema_version`
    deixaria de dizer qual contrato validou a row."""
    tokens = {key: _schema_version_token("E4", key) for key in ARTIFACT_KEYS}
    assert all(t is not None for t in tokens.values())
    assert tokens["patrimonio"] != tokens["receitas"]
    assert tokens["receitas"] == tokens["despesas"], "mesmo contrato ⇒ mesmo token"


# ───────────────────────── baldes reais em strict ─────────────────────────


def test_baldes_reais_validam_em_strict(baldes_reais, strict) -> None:
    """Ordem da lane: o schema descreve o que o produtor emite HOJE, senão o flip
    para strict derruba o stage. `patrimonio` reprovava em `$` antes desta lane."""
    reprovados = [
        key
        for key, payload in baldes_reais.items()
        if not validate_dict(payload, resolve_schema_name("E4", key), source=f"E4/{key}")
    ]
    assert reprovados == [], f"baldes que o produtor emite e o schema rejeita: {reprovados}"


def test_patrimonio_usa_o_contrato_da_propria_fonte(baldes_reais) -> None:
    """O balde é cópia normalizada do artefato E1.5c, que já é gateado por este
    mesmo schema — a cópia não pode ser julgada por contrato mais frouxo que a fonte."""
    assert resolve_schema_name("E4", "patrimonio") == SCHEMA_BY_STAGE["consolidate_baseline"]
    assert "patrimonio" in baldes_reais


# ───────────────────────── controle positivo ─────────────────────────


@pytest.mark.parametrize("key", ["receitas", "despesas", "patrimonio", "investimentos"])
def test_shape_de_placeholder_reprova_em_balde_transacional(key: str, strict) -> None:
    assert not validate_dict(
        _SHAPE_PLACEHOLDER, resolve_schema_name("E4", key), source=key
    ), f"{key}: guard aceita o shape de placeholder — o buraco da A42.l19 voltou"


def test_troca_de_balde_reprova(strict) -> None:
    """Discriminação real: não basta rejeitar `{status}`; o contrato de um balde
    precisa rejeitar o payload bem-formado de OUTRO balde."""
    nome = resolve_schema_name("E4", "fluxo_mensal_detalhado")
    assert not validate_dict(_SHAPE_CASHFLOW, nome, source="fluxo")


def test_umbrella_nao_aceita_mais_o_shape_de_placeholder(strict) -> None:
    """O backstop por stage cobre `artifact_key` que ninguém mapeou — e não pode
    ser ele próprio o buraco."""
    assert not validate_dict(_SHAPE_PLACEHOLDER, SCHEMA_BY_STAGE["E4"], source="backstop")


def test_umbrella_aceita_os_baldes_reais(baldes_reais, strict) -> None:
    """`anyOf`, não `oneOf`: `seguros` v1 e `pontos_milhas` são ambos `{"dados": []}`
    e sob `oneOf` duas correspondências reprovariam um payload correto."""
    for key, payload in baldes_reais.items():
        assert validate_dict(payload, SCHEMA_BY_STAGE["E4"], source=f"backstop/{key}"), key


def test_ramo_morto_nao_volta() -> None:
    """O umbrella referencia os contratos por balde; ramo literal `{status}` de volta
    aqui significa que alguém reintroduziu o buraco."""
    doc = json.loads((CONFIG_DIR / "schemas" / "e4_unified.schema.json").read_text("utf-8"))
    assert "oneOf" not in doc
    assert all("$ref" in ramo for ramo in doc["anyOf"])
