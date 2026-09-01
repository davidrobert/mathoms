"""Gate A40.l110 — o balde `patrimonio` é função pura do input, sem relógio.

`BaselineNormalizer` gravava `date.today()` em `data_processamento` quando o
produtor não emitia a chave — e `consolidate_baseline` nunca emitiu. Mesmo
input em dois dias civis produzia payload diferente, num artefato persistido:
qualquer métrica de massa por conteúdo contava 1 evidência nova por dia.

Três medidas, porque cada uma pega o que a outra não pega:

- **efeito** — dois builds do mesmo input têm o mesmo `sha256`. Pega
  não-determinismo de qualquer origem (uuid, ordenação, cache), mas passa
  trivialmente se as duas execuções caem no mesmo dia civil.
- **mecanismo** — nenhuma chamada de relógio de parede acontece enquanto o
  payload é construído. Pega a regressão específica **sem** depender do
  calendário: reinstalar `self._resolve_today()` reprova aqui hoje, não em
  algum dia futuro. Sem orçamento de relógio em `assert` (CLAUDE.md §Testes).
- **ausência de hoje no payload** — rede de segurança para carimbo vindo de
  módulo fora do caminho medido acima. A fixture é sintética e datada em
  2024/2025, então nenhum valor legítimo pode ser a data de hoje.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.artifact_store import InMemoryArtifactStore  # noqa: E402
from pipeline.domain.services.baseline_normalizer import BaselineNormalizer  # noqa: E402
from pipeline.domain.services.e4_serialization import (  # noqa: E402
    build_patrimonio_artifact,
)

_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "tests/fixtures/pipeline_golden/e2/dois-membros-anos-disjuntos-1.5_consolidated.json"
)

_RELOGIOS = ("date.today", "datetime.now", "datetime.today", "datetime.utcnow", "time.time")


def _baseline_bruto() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def _build_patrimonio(raw: dict) -> dict | None:
    return build_patrimonio_artifact(BaselineNormalizer().normalize(raw))


def _sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _relogios_chamados(fn, *args):
    """Nomes de relógio de parede invocados durante ``fn`` — via ``sys.setprofile``."""
    vistos: list[str] = []

    def profiler(frame, event, arg):
        if event != "c_call":
            return
        nome = getattr(arg, "__qualname__", "") or getattr(arg, "__name__", "")
        modulo = getattr(arg, "__module__", None) or ""
        for alvo in _RELOGIOS:
            if nome == alvo or f"{modulo}.{nome}" == alvo:
                vistos.append(f"{modulo}.{nome}" if modulo else nome)

    anterior = sys.getprofile()
    sys.setprofile(profiler)
    try:
        resultado = fn(*args)
    finally:
        sys.setprofile(anterior)
    return resultado, vistos


def test_patrimonio_tem_o_mesmo_hash_em_dois_builds():
    """Efeito: o payload é função do input, não do momento."""
    primeiro = _build_patrimonio(_baseline_bruto())
    segundo = _build_patrimonio(_baseline_bruto())
    assert primeiro is not None
    assert _sha256(primeiro) == _sha256(segundo)


def test_construir_patrimonio_nao_consulta_relogio_de_parede():
    """Mecanismo: reinstalar `date.today()` no normalizer reprova ESTE teste hoje."""
    payload, relogios = _relogios_chamados(_build_patrimonio, _baseline_bruto())
    assert payload is not None
    assert relogios == [], (
        f"relógio de parede consultado ao construir o balde `patrimonio`: {relogios}. "
        "Valor de relógio em artefato persistido quebra idempotência (A40.l110)."
    )


def test_payload_nao_carrega_a_data_de_hoje():
    """Rede: carimbo de hoje vindo de qualquer módulo apareceria como string ISO."""
    hoje = date.today().isoformat()
    bruto = json.dumps(_build_patrimonio(_baseline_bruto()), ensure_ascii=False)
    assert hoje not in bruto, (
        f"a data de hoje ({hoje}) aparece no balde `patrimonio` — algum produtor "
        "voltou a carimbar relógio no artefato (A40.l110)."
    )


def test_normalizer_nao_sintetiza_chave_que_produtor_nenhum_emite():
    """Os 2 fósseis não voltam nem por síntese, nem por passagem da fixture."""
    payload = _build_patrimonio(_baseline_bruto())
    assert payload is not None
    assert "pipeline_stage" not in payload
    assert "data_processamento" not in payload


def test_store_e_normalizer_concordam_no_conjunto_de_chaves():
    """O que a fixture entrega é o que o balde publica — sem enxerto no meio."""
    store = InMemoryArtifactStore()
    store.seed("E1.5c", "baseline_patrimonial", _baseline_bruto())
    lido = store.read("E1.5c", "baseline_patrimonial")
    payload = _build_patrimonio(lido)
    assert payload is not None
    assert set(payload) == set(_baseline_bruto())
