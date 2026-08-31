"""A40.l74 — contrato do stage `extract_comprovantes_bens`, que tem DOIS produtores.

`SCHEMA_BY_STAGE` é 1:1 stage→schema e apontava direto para `crlv.schema.json`,
então payload de apólice validava contra o schema de veículo (25 paths em drift,
medidos pelo caminho real). O schema é resolvido **pelo mapa** e sua existência é
afirmada: `validate_dict` faz short-circuit para True quando o arquivo não existe,
então teste com nome literal de schema passa verde antes do fix.
"""

from __future__ import annotations

import functools
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.services.storage.db_artifact_store import (  # noqa: E402
    SCHEMA_BY_STAGE,
    _schema_version_token,
)
from pipeline.llm.schemas.apolice import ApolicePayload  # noqa: E402
from pipeline.llm.schemas.crlv import CRLVPayload  # noqa: E402
from pipeline.stages.comprovantes_bens_llm import (  # noqa: E402
    _build_apolice_payload,
    _build_payload,
)
from scripts.pipeline_common import CONFIG_DIR, validate_dict  # noqa: E402

STAGE = "extract_comprovantes_bens"
GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "llm_golden"
APOLICE_GOLDENS = sorted(GOLDEN_DIR.glob("apolice_*.json"))

_CRLV_MINIMO = {
    "placa": "ABC1D23",
    "renavam": "12345678901",
    "marca": "Fiat",
    "modelo": "Toro",
    "ano_modelo": 2022,
    "ano_fabricacao": 2021,
    "exercicio": 2024,
    "categoria": "particular",
    "confidence": 0.95,
    "prompt_version": "1.0.0",
}


@pytest.fixture
def schema_strict(monkeypatch) -> str:
    """Nome do schema que o `DBArtifactStore` aplicaria, em modo strict."""
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
    return SCHEMA_BY_STAGE[STAGE]


def _apolice(golden: Path) -> dict:
    payload = ApolicePayload(**json.loads(golden.read_text(encoding="utf-8")))
    return _build_apolice_payload(payload, "1.3.0", "texto sem cpf", "k", cascade_triggered=False)


def _crlv(**overrides) -> dict:
    base = {**_CRLV_MINIMO, **overrides}
    return _build_payload(CRLVPayload(**base), "1.0.0", "texto sem cpf", "crlv_abc1d23_2024")


def _drift_paths(payload: dict, schema_name: str) -> list[str]:
    """Paths que a telemetria da ADR-284 emitiria — é o eixo que gateia o flip strict."""
    from scripts.pipeline_common import _build_schema_validator, _schema_to_validate
    from scripts.schema_drift_telemetry import _count_drift_paths

    schema, _ = _schema_to_validate(schema_name)
    errors = list(_build_schema_validator(schema).iter_errors(payload))
    return sorted(path for path, _ in _count_drift_paths(errors))


def test_schema_do_stage_existe_em_disco(schema_strict):
    """Anti-vazio: schema ausente faz `validate_dict` retornar True sem validar nada."""
    assert (
        CONFIG_DIR / "schemas" / schema_strict
    ).exists(), f"{schema_strict} não existe — todo teste de contrato deste stage passaria vazio"


def test_goldens_de_apolice_existem():
    """Guarda o próprio corpus: sem goldens, os testes abaixo passam sem exercitar nada."""
    assert len(APOLICE_GOLDENS) == 6, [g.name for g in APOLICE_GOLDENS]


@pytest.mark.parametrize("golden", APOLICE_GOLDENS, ids=lambda g: g.stem)
def test_payload_apolice_produzido_valida_em_strict(golden, schema_strict):
    """Output do produtor real, não payload copiado à mão (cobre os 3 tipos de bem)."""
    assert validate_dict(_apolice(golden), schema_strict, source=f"test/{golden.stem}")


def test_payload_crlv_produzido_valida_em_strict(schema_strict):
    assert validate_dict(_crlv(), schema_strict, source="test/crlv")


def test_drift_de_apolice_nomeia_o_campo_e_nao_a_raiz(schema_strict):
    """Anti-regressão para `oneOf`-por-shape: ele colapsa todo drift em `$`, e a
    telemetria per-path da ADR-284 é o gate do flip warn→strict — schema cujo drift
    é sempre `$` fica indiagnosticável, logo permanentemente inelegível."""
    payload = _apolice(GOLDEN_DIR / "apolice_combinada.json")
    del payload["corretor"]
    assert _drift_paths(payload, schema_strict) == ["$.corretor"]


def test_campo_extra_em_sub_objeto_de_apolice_reprova(schema_strict):
    """Sub-models são `extra="forbid"` (trava em test_schema_leniency_lock)."""
    payload = _apolice(GOLDEN_DIR / "apolice_combinada.json")
    payload["bens_segurados"][0]["campo_novo"] = "drift"
    assert _drift_paths(payload, schema_strict) == ["$.bens_segurados[].campo_novo"]


def test_campo_extra_no_topo_de_apolice_passa(schema_strict):
    """Leniência top-level é design (ADR-238 D2) — payload sobrevive a shape novo de PDF."""
    payload = _apolice(GOLDEN_DIR / "apolice_combinada.json")
    payload["campo_novo_do_pdf"] = "shape novo"
    assert validate_dict(payload, schema_strict, source="test/lenient")


def test_campo_extra_no_crlv_reprova(schema_strict):
    """A assimetria sobrevive ao despacho: o ramo CRLV segue `additionalProperties: false`."""
    payload = _crlv()
    payload["campo_novo"] = "drift"
    assert _drift_paths(payload, schema_strict) == ["$.campo_novo"]


def test_dinheiro_como_number_reprova(schema_strict):
    """ADR-090 — no wire do artefato, dinheiro é string decimal."""
    payload = _apolice(GOLDEN_DIR / "apolice_combinada.json")
    payload["premio_total_brl"] = 3250.00
    assert _drift_paths(payload, schema_strict) == ["$.premio_total_brl"]


def test_payload_sem_discriminador_reprova(schema_strict):
    """Identidade é declarada, não inferida do shape — sem `tipo_comprovante` não há ramo."""
    payload = _apolice(GOLDEN_DIR / "apolice_combinada.json")
    del payload["tipo_comprovante"]
    assert _drift_paths(payload, schema_strict) == ["$.tipo_comprovante"]


@pytest.mark.parametrize("ramo", ["crlv.schema.json", "apolice.schema.json"])
def test_token_de_auditoria_muda_quando_o_ramo_muda(ramo, tmp_path, monkeypatch):
    """`pipeline_artifacts.schema_version` audita a row. Hashear só o arquivo-base
    deixaria o token estável enquanto o contrato real muda atrás do `$ref`."""
    origem = CONFIG_DIR / "schemas"
    destino = tmp_path / "schemas"
    destino.mkdir()
    for arquivo in origem.glob("*.schema.json"):
        (destino / arquivo.name).write_text(arquivo.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr("scripts.pipeline_common.CONFIG_DIR", tmp_path)

    antes = _schema_version_token(STAGE, "crlv_abc1d23_2024")
    alvo = destino / ramo
    doc = json.loads(alvo.read_text(encoding="utf-8"))
    doc["$comment"] = "mutação de controle"
    alvo.write_text(json.dumps(doc), encoding="utf-8")

    assert (
        _schema_version_token(STAGE, "crlv_abc1d23_2024") != antes
    ), f"token cego a mudança em {ramo}"


# Mapa explícito Pydantic → `$defs`. O teste do produtor só exercita o que os goldens
# emitem; campo novo opcional em sub-model passaria por ele sem o schema declará-lo.
_SUB_MODEL_DEFS = {
    "EnderecoStruct": "endereco",
    "CongenereRef": "congenere_ref",
    "CorretorRef": "corretor_ref",
    "BeneficiarioRef": "beneficiario_ref",
    "CoberturaMaterial": "cobertura_material",
    "CoberturaRcfv": "cobertura_rcfv",
    "CoberturaVida": "cobertura_vida",
    "CoberturaSaude": "cobertura_saude",
    "CoberturaAcidentes": "cobertura_acidentes",
    "BemSeguradoVeiculo": "bem_veiculo",
    "BemSeguradoImovel": "bem_imovel",
    "BemSeguradoPessoa": "bem_pessoa",
}


@functools.lru_cache(maxsize=1)
def _apolice_schema() -> dict:
    # lru_cache: 12 casos parametrizados reparseariam o mesmo JSON (ADR-210).
    return json.loads((CONFIG_DIR / "schemas" / "apolice.schema.json").read_text(encoding="utf-8"))


def test_mapa_de_sub_models_cobre_todos_os_forbid():
    """Sub-model novo em `apolice.py` entra no mapa — senão os testes abaixo o ignoram."""
    import inspect

    from pydantic import BaseModel

    from pipeline.llm.schemas import apolice as mod

    forbid = {
        nome
        for nome, obj in inspect.getmembers(mod, inspect.isclass)
        if issubclass(obj, BaseModel)
        and obj is not BaseModel
        and obj.model_config.get("extra") == "forbid"
    }
    assert forbid == set(_SUB_MODEL_DEFS)


@pytest.mark.parametrize("modelo,nome_def", sorted(_SUB_MODEL_DEFS.items()))
def test_sub_model_tem_def_strict_com_os_mesmos_required(modelo, nome_def):
    """Espelha a trava de `test_schema_leniency_lock`: sub-model é `extra="forbid"`."""
    from pipeline.llm.schemas import apolice as mod

    definicao = _apolice_schema()["$defs"][nome_def]
    assert definicao["additionalProperties"] is False
    campos = getattr(mod, modelo).model_fields
    assert set(definicao["properties"]) == set(campos), "schema derivou do Pydantic"
    obrigatorios = {n for n, f in campos.items() if f.is_required()}
    assert obrigatorios <= set(definicao["required"])


def test_top_level_de_apolice_espelha_a_leniencia_do_pydantic():
    """Topo lenient é design ([[ADR-238]] D2), não descuido — e o schema tem de segui-lo."""
    from pipeline.llm.schemas.apolice import ApolicePayload

    schema = _apolice_schema()
    assert ApolicePayload.model_config.get("extra") == "allow"
    assert schema["additionalProperties"] is True
    campos = ApolicePayload.model_fields
    assert set(campos) <= set(schema["properties"])
    assert {n for n, f in campos.items() if f.is_required()} <= set(schema["required"])
