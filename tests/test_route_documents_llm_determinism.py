"""Determinismo + guarda de roteamento da classificação LLM (A39.l11 · ADR-348).

Offline (spy nomeado sobre o client Anthropic — sem API, sem MagicMock):
- `temperature=0` é enviado no payload (invariante de determinismo);
- `dest_group` fora do conjunto fechado (alucinado / path-traversal) → None,
  nunca cria `data/<lixo>/` (perda silenciosa de documento);
- `dest_group` válido segue roteando; caminho de baixa confiança intacto.
"""

import json

from scripts import route_documents as rd

_VALID = {
    "institution": "itau",
    "doc_type": "extratocontabrl",
    "dest_group": "financial_statements",
    "period": "202602",
    "final_name": "itau_extratocontabrl_202602-0_original.txt",
    "confidence": 0.95,
}


class _FakeMessage:
    def __init__(self, text: str):
        self.content = [type("_Block", (), {"text": text})()]


class _FakeMessages:
    def __init__(self, recorder: dict, payload: str):
        self._recorder = recorder
        self._payload = payload

    def create(self, **kwargs):
        self._recorder.update(kwargs)
        return _FakeMessage(self._payload)


def _run(monkeypatch, tmp_path, payload: dict):
    import anthropic

    recorder: dict = {}

    class _FakeAnthropic:
        def __init__(self, **kwargs):
            recorder["_init"] = kwargs
            self.messages = _FakeMessages(recorder, json.dumps(payload))

    monkeypatch.setattr(anthropic, "Anthropic", _FakeAnthropic)
    f = tmp_path / "doc.txt"
    f.write_text("conteudo de teste suficiente para gerar preview nao vazio", encoding="utf-8")
    result = rd.classify_by_llm(f, api_key="test-key")
    return result, recorder


def test_temperature_zero_no_payload(monkeypatch, tmp_path):
    _, rec = _run(monkeypatch, tmp_path, _VALID)
    assert rec.get("temperature") == 0.0


def test_dest_group_alucinado_retorna_none(monkeypatch, tmp_path):
    # dest_group fora do conjunto fechado → doc iria para data/crypto/ (perda
    # silenciosa) → trata como baixa confiança (nao_identificados/).
    result, _ = _run(monkeypatch, tmp_path, {**_VALID, "dest_group": "crypto"})
    assert result is None


def test_dest_group_path_traversal_retorna_none(monkeypatch, tmp_path):
    result, _ = _run(monkeypatch, tmp_path, {**_VALID, "dest_group": "../secrets"})
    assert result is None


def test_dest_group_valido_roteia(monkeypatch, tmp_path):
    result, _ = _run(monkeypatch, tmp_path, _VALID)
    assert result is not None
    assert result["dest_group"] == "financial_statements"
    assert result["source"] == "llm"


def test_dest_group_comprovantes_valido(monkeypatch, tmp_path):
    # comprovantes é regex-only no prompt mas é dir consumido (ADR-239) —
    # não pode ser rejeitado se o LLM o retornar.
    result, _ = _run(monkeypatch, tmp_path, {**_VALID, "dest_group": "comprovantes"})
    assert result is not None
    assert result["dest_group"] == "comprovantes"


def test_baixa_confianca_retorna_none(monkeypatch, tmp_path):
    result, _ = _run(monkeypatch, tmp_path, {**_VALID, "confidence": 0.5})
    assert result is None
