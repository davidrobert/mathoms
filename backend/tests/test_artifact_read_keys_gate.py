"""O gate de chave lida↔emitida precisa reprovar o bug que o originou."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = REPO_ROOT / "dev" / "check_artifact_read_keys.py"


def _gate_module():
    spec = importlib.util.spec_from_file_location("check_artifact_read_keys", GATE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _erros(codigo: str, tmp_path: Path) -> list[str]:
    gate = _gate_module()
    alvo = tmp_path / "modulo_sob_teste.py"
    alvo.write_text(codigo, encoding="utf-8")
    # Resolve o mapa com o REPO_ROOT real (ele lê o fonte do store por AST) antes de
    # apontar a raiz para o tmp — senão o gate procura o arquivo dentro do tmp.
    mapa = gate._schema_por_stage()
    real = gate.REPO_ROOT
    try:
        gate.REPO_ROOT = tmp_path
        return gate._analisa(alvo, mapa)
    finally:
        gate.REPO_ROOT = real


_LEITOR_CORRETO = """
from backend.app.services.security.crypto import read_artifact_content

ARTIFACT_CONTRACT = ("analyze_finances",)


def f(artifact):
    payload = read_artifact_content(artifact.content_json) or {}
    return payload.get("patrimonio"), payload["investimentos"]
"""

_LEITOR_DO_BUG = _LEITOR_CORRETO.replace('"patrimonio"', '"patrimonio_full"')

_SEM_CONTRATO = _LEITOR_CORRETO.replace('ARTIFACT_CONTRACT = ("analyze_finances",)', "")

_ENXERTO = """
from backend.app.services.security.crypto import read_artifact_content

ARTIFACT_CONTRACT = ("analyze_finances",)


def f(artifact):
    payload = dict(read_artifact_content(artifact.content_json))
    payload["_report_lineage"] = {}
    return payload
"""


# O payload também chega por atributo de um carrier já decriptado. Era o furo que
# deixava `recalibracao_note.py` fora do falha-fechado (A40.l25).
_LEITOR_POR_CONTENT_JSON = """
ARTIFACT_CONTRACT = ("analyze_finances",)


def f(snapshot):
    return (snapshot.content_json or {}).get("if_monte_carlo")
"""

_CONTENT_JSON_SEM_CONTRATO = _LEITOR_POR_CONTENT_JSON.replace(
    'ARTIFACT_CONTRACT = ("analyze_finances",)', ""
)

# Modo estrito: chave de BLOCO lida de PARÂMETRO, que o rastreio por variável não vê.
_LEITOR_ESTRITO = """
ARTIFACT_CONTRACT = ("analyze_finances",)
ARTIFACT_CONTRACT_BLOCO = "if_monte_carlo"


def bloco(snapshot):
    return (snapshot.content_json or {}).get("if_monte_carlo")


def ano(bloco):
    return (bloco or {}).get("ano_if_cenario_central")
"""

_ESTRITO_COM_CHAVE_MORTA = _LEITOR_ESTRITO.replace('"ano_if_cenario_central"', '"p50_ano_if"')


def test_reprova_a_chave_ficticia_que_originou_o_gate(tmp_path):
    erros = _erros(_LEITOR_DO_BUG, tmp_path)
    assert any("patrimonio_full" in e for e in erros), erros


def test_aprova_as_chaves_que_o_produtor_emite(tmp_path):
    assert _erros(_LEITOR_CORRETO, tmp_path) == []


def test_falha_fechado_sem_contrato_declarado(tmp_path):
    erros = _erros(_SEM_CONTRATO, tmp_path)
    assert any("ARTIFACT_CONTRACT" in e for e in erros), erros


def test_enxerto_do_backend_nao_e_violacao(tmp_path):
    # Escrever chave nova no payload é legítimo; só a LEITURA precisa existir no schema.
    assert _erros(_ENXERTO, tmp_path) == []


def test_falha_fechado_para_payload_lido_por_content_json(tmp_path):
    """O furo da A40.l25: sem detectar `.content_json`, o módulo nunca declarava nada."""
    erros = _erros(_CONTENT_JSON_SEM_CONTRATO, tmp_path)
    assert any("ARTIFACT_CONTRACT" in e for e in erros), erros


def test_aprova_leitor_por_content_json_com_contrato(tmp_path):
    assert _erros(_LEITOR_POR_CONTENT_JSON, tmp_path) == []


def test_modo_estrito_aprova_chave_viva_do_bloco(tmp_path):
    assert _erros(_LEITOR_ESTRITO, tmp_path) == []


def test_modo_estrito_reprova_chave_morta_do_bloco(tmp_path):
    """`p50_ano_if` morreu no rename de `mc_version` 4.0 e deixou a nota inerte."""
    erros = _erros(_ESTRITO_COM_CHAVE_MORTA, tmp_path)
    assert any("p50_ano_if" in e for e in erros), erros


def test_sem_modo_estrito_a_chave_de_parametro_nao_e_checada(tmp_path):
    """Limite declarado: fora do opt-in, leitura de parâmetro segue invisível."""
    # Registrado como teste para que o limite seja fato medido, não suposição de
    # quem lê o gate — e para que ampliar a cobertura seja mudança consciente.
    sem_bloco = _ESTRITO_COM_CHAVE_MORTA.replace('ARTIFACT_CONTRACT_BLOCO = "if_monte_carlo"', "")
    assert _erros(sem_bloco, tmp_path) == []


def test_todo_leitor_de_application_declara_contrato():
    """O repo inteiro passa — se um módulo novo ler artefato, este teste acusa."""
    gate = _gate_module()
    erros: list[str] = []
    mapa = gate._schema_por_stage()
    for path in sorted(gate.SCAN_DIR.rglob("*.py")):
        erros.extend(gate._analisa(path, mapa))
    assert erros == [], "\n".join(erros)


def test_contratos_declarados_citam_stage_conhecido():
    gate = _gate_module()
    mapa = gate._schema_por_stage()
    declarados = 0
    for path in sorted(gate.SCAN_DIR.rglob("*.py")):
        stages = gate._contrato_declarado(ast.parse(path.read_text(encoding="utf-8")))
        if not stages:
            continue
        declarados += 1
        assert all(s in mapa for s in stages), f"{path}: stage fora de SCHEMA_BY_STAGE"
    assert declarados >= 5, "esperado ao menos os 5 leitores conhecidos de application/"


def test_backstop_por_stage_recupera_as_properties_dos_ramos():
    """A42.l19 — `e4_unified` virou `anyOf` de `$ref` e não tem `properties` no topo."""
    # Sem descer por `anyOf`, o conjunto sairia VAZIO e todo `payload["x"]` de um leitor
    # de E4 seria reprovado como chave que o produtor não emite: falso positivo plantado
    # pelo próprio refactor. Descer só por `allOf[].then.$ref` (comprovante_base) não
    # basta — `e4_seguros` declara `properties` INLINE no `then`.
    props = _gate_module()._propriedades("e4_unified.schema.json")

    assert props, "backstop sem properties alcançáveis — leitor de E4 reprovaria inteiro"
    # chaves de ramos DIFERENTES: a união precisa cobrir todos, não só o primeiro
    assert {"meses_ordenados", "patrimonio_por_ano", "n_posicoes", "apolices"} <= props
