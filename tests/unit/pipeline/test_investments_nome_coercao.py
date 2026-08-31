"""A42.l19 — o `nome` da posição vai para o balde `investimentos` sem coerção.

O contrato declara `items: {type: string}` e o corpus nunca exercitou a chave
(`posicoes_sem_marcacao_por_membro`, 0/70 em 98 dias). Sob `strict`, um `nome`
numérico de parser abortaria o write do E4 — que é `criticality: required`.
"""

from __future__ import annotations

from pathlib import Path


class TestNomeNaoStringNoBadge:
    """A42.l19 / [[ADR-409]] §D — o `nome` vem de parser/LLM sem coerção, e o balde
    declara `items: {type: string}`. O corpus nunca exercitou a chave (0/70 em 98 dias),
    então sob `strict` um `nome` numérico abortaria o write do E4 (`required`).
    """

    def test_nome_numerico_vira_string(self):
        from pipeline.domain.services.investments_consolidator import _nome_str

        assert _nome_str(12345) == "12345"
        assert _nome_str(3.5) == "3.5"

    def test_ausente_e_vazio_viram_interrogacao(self):
        from pipeline.domain.services.investments_consolidator import _nome_str

        assert _nome_str(None) == "?"
        assert _nome_str("") == "?"

    def test_badge_do_produtor_e_sempre_lista_de_string(self):
        """Contrafactual do fix: sem coerção, este payload emitiria `int` na lista."""
        import json

        import jsonschema

        from pipeline.domain.services.investments_consolidator import _nome_str

        badge = {"david": [_nome_str(999), _nome_str(None), _nome_str("CDB")]}
        schema = json.loads(
            (
                Path(__file__).resolve().parents[3]
                / "config"
                / "schemas"
                / "e4_investimentos.schema.json"
            ).read_text(encoding="utf-8")
        )
        sub = schema["properties"]["posicoes_sem_marcacao_por_membro"]

        jsonschema.validate(badge, sub)
        assert all(isinstance(v, str) for vs in badge.values() for v in vs)
