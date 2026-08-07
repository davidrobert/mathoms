"""Tests — ``PontosUrgentesAnalyzer`` (Sessão A5c)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.pontos_urgentes_analyzer import (  # noqa: E402
    PontosUrgentesAnalyzer,
    PontosUrgentesConfig,
    PontoUrgenteItem,
)


def _ratios(endiv: float = 10.0, rent: str = "15%") -> dict:
    return {"taxa_endividamento_pct": endiv, "rentabilidade_pct": rent}


def _reserva(cobertura: float = 12.0) -> dict:
    return {"cobertura_meses": cobertura}


def _pat() -> dict:
    return {"bruto": 1_000_000, "dividas": 0}


class TestReserva:
    def test_dispara_quando_abaixo_do_minimo(self):
        out = PontosUrgentesAnalyzer().analyze(_ratios(), _reserva(cobertura=3), _pat())
        acoes = {i.acao for i in out}
        assert "Reforçar reserva de emergência" in acoes

    def test_nao_dispara_quando_adequada(self):
        out = PontosUrgentesAnalyzer().analyze(_ratios(), _reserva(cobertura=12), _pat())
        acoes = {i.acao for i in out}
        assert "Reforçar reserva de emergência" not in acoes


class TestEndividamento:
    def test_dispara_quando_acima_do_maximo(self):
        out = PontosUrgentesAnalyzer().analyze(_ratios(endiv=25), _reserva(), _pat())
        acoes = {i.acao for i in out}
        assert "Reduzir endividamento" in acoes

    def test_nao_dispara_quando_ok(self):
        out = PontosUrgentesAnalyzer().analyze(_ratios(endiv=10), _reserva(), _pat())
        acoes = {i.acao for i in out}
        assert "Reduzir endividamento" not in acoes


def _protecao(
    vigentes: list[dict] | None = None,
    *,
    gap_flag: bool = False,
    gap_rationale: str = "sem family_members",
) -> dict:
    """Forma do produtor: `compute_protecao` SEMPRE emite `gap_qualitativo`
    (`_protecao_payload`), e é dele que o item de seguro passa a derivar
    (A40.l10 · ADR-365). Fixture sem o bloco não representa nenhum payload real."""
    return {
        "apolices_vigentes": vigentes or [],
        "gap_qualitativo": [
            {"categoria": "vida", "flag": gap_flag, "rationale": gap_rationale},
            {"categoria": "saude", "flag": False, "rationale": "evidencia_pagamento_saude"},
        ],
    }


class TestSeguro:
    def test_sempre_adicionado_sem_payload_protecao(self):
        out = PontosUrgentesAnalyzer().analyze(_ratios(), _reserva(), _pat())
        acoes = {i.acao for i in out}
        assert "Contratar seguro de vida e invalidez" in acoes

    def test_copy_legada_quando_nenhuma_apolice_vigente(self):
        out = PontosUrgentesAnalyzer().analyze(
            _ratios(), _reserva(), _pat(), protecao=_protecao([])
        )
        seguro = [i for i in out if i.acao == "Contratar seguro de vida e invalidez"]
        assert len(seguro) == 1
        assert "nenhuma apólice identificada" in seguro[0].impacto

    def test_copy_diferenciada_quando_so_ha_cobertura_de_bens(self):
        vigentes = [
            {"apolice_numero": "AUTO-1", "tipos_bem": ["veiculo"]},
            {"apolice_numero": "RES-1", "tipos_bem": ["imovel"]},
        ]
        out = PontosUrgentesAnalyzer().analyze(
            _ratios(), _reserva(), _pat(), protecao=_protecao(vigentes)
        )
        seguro = [i for i in out if i.acao == "Contratar seguro de vida e invalidez"]
        assert len(seguro) == 1
        assert "nenhuma apólice identificada" not in seguro[0].impacto
        assert "2 apólices vigentes cobrem" in seguro[0].impacto
        assert "sem cobertura de vida" in seguro[0].impacto

    def test_pluralizacao_singular_uma_apolice(self):
        # A37.l14 (PD-06): "1 apólice(s) vigente(s)" era pluralização de sistema.
        vigentes = [{"apolice_numero": "AUTO-1", "tipos_bem": ["veiculo"]}]
        out = PontosUrgentesAnalyzer().analyze(
            _ratios(), _reserva(), _pat(), protecao=_protecao(vigentes)
        )
        seguro = [i for i in out if i.acao == "Contratar seguro de vida e invalidez"]
        assert len(seguro) == 1
        assert "1 apólice vigente cobre bens" in seguro[0].impacto
        assert "(s)" not in seguro[0].impacto

    def test_omitido_quando_ha_apolice_de_vida_vigente(self):
        vigentes = [{"apolice_numero": "VIDA-1", "tipos_bem": ["pessoa"]}]
        out = PontosUrgentesAnalyzer().analyze(
            _ratios(),
            _reserva(),
            _pat(),
            protecao=_protecao(vigentes, gap_rationale="apolice_vida_ativa"),
        )
        acoes = {i.acao for i in out}
        assert "Contratar seguro de vida e invalidez" not in acoes

    # ── A40.l10 · ADR-365: o item passa a derivar do gap canônico ──────

    def test_omitido_quando_nao_ha_dependencia_economica(self):
        """O achado que motivou o PR: sem gatilho de dependência (titular
        solteiro, sem filho menor, sem passivo alto), recomendar seguro de vida
        é conselho errado — e não é retenção, é conselho que não existe."""
        out = PontosUrgentesAnalyzer().analyze(
            _ratios(), _reserva(), _pat(), protecao=_protecao([], gap_rationale="sem gatilho")
        )
        assert "Contratar seguro de vida e invalidez" not in {i.acao for i in out}

    def test_computavel_quando_ha_dependente_menor(self):
        out = PontosUrgentesAnalyzer().analyze(
            _ratios(),
            _reserva(),
            _pat(),
            protecao=_protecao([], gap_flag=True, gap_rationale="dependentes_menores_18"),
        )
        seguro = [i for i in out if i.code == "seguro_vida"]
        assert len(seguro) == 1
        assert seguro[0].elegibilidade == "computavel"
        assert seguro[0].origem_premissa == "cadastro_familia"

    def test_degenerada_quando_gatilho_e_conjuge_sem_renda(self):
        """Tautológico enquanto `renda_propria_brl` é fixo em 0 (ADR-240 §D3)."""
        out = PontosUrgentesAnalyzer().analyze(
            _ratios(),
            _reserva(),
            _pat(),
            protecao=_protecao([], gap_flag=True, gap_rationale="conjuge_sem_renda_propria"),
        )
        seguro = [i for i in out if i.code == "seguro_vida"]
        assert len(seguro) == 1
        assert seguro[0].elegibilidade == "degenerada"

    def test_computavel_quando_gatilho_e_passivo_alto(self):
        out = PontosUrgentesAnalyzer().analyze(
            _ratios(),
            _reserva(),
            _pat(),
            protecao=_protecao([], gap_flag=True, gap_rationale="passivo_acima_30_pct_patrimonio"),
        )
        seguro = [i for i in out if i.code == "seguro_vida"]
        assert seguro[0].elegibilidade == "computavel"
        assert seguro[0].origem_premissa == "derivado_e5"

    def test_pendente_de_dado_quando_falta_cadastro_da_familia(self):
        out = PontosUrgentesAnalyzer().analyze(
            _ratios(), _reserva(), _pat(), protecao=_protecao([])
        )
        seguro = [i for i in out if i.code == "seguro_vida"]
        assert seguro[0].elegibilidade == "pendente_de_dado"
        assert seguro[0].dado_faltante == "composição da família"

    def test_nao_verificavel_sem_bloco_de_protecao(self):
        """Caller legado: o conselho existe, a premissa é inavaliável."""
        out = PontosUrgentesAnalyzer().analyze(_ratios(), _reserva(), _pat())
        seguro = [i for i in out if i.code == "seguro_vida"]
        assert seguro[0].elegibilidade == "nao_verificavel"

    def test_todo_item_tem_code_estavel(self):
        """`code` é pré-condição de ordenação: `build_default_tarefas_status`
        chaveia por posição, então reordenar sem id remapeia o status do dono."""
        out = PontosUrgentesAnalyzer().analyze(
            _ratios(endiv=25, rent="N/D"), _reserva(cobertura=1), _pat()
        )
        codes = [i.code for i in out]
        assert all(codes), f"item sem code: {codes}"
        assert len(codes) == len(set(codes)), f"code duplicado: {codes}"


class TestRentabilidade:
    def test_dispara_quando_nd(self):
        out = PontosUrgentesAnalyzer().analyze(_ratios(rent="N/D"), _reserva(), _pat())
        acoes = {i.acao for i in out}
        assert "Consolidar dados de rentabilidade dos investimentos" in acoes

    def test_nao_dispara_quando_tem_valor(self):
        out = PontosUrgentesAnalyzer().analyze(_ratios(rent="12.5"), _reserva(), _pat())
        acoes = {i.acao for i in out}
        assert "Consolidar dados de rentabilidade dos investimentos" not in acoes


class TestConfig:
    def test_from_scoring(self):
        cfg = PontosUrgentesConfig.from_scoring(
            {
                "thresholds_alertas": {
                    "reserva_minima_meses": 12,
                    "endividamento_maximo_pct": 10,
                }
            }
        )
        assert cfg.reserva_minima_meses == 12.0
        assert cfg.endividamento_maximo_pct == 10.0


class TestResult:
    def test_to_dict_cobre_todo_campo_do_dataclass(self):
        """Derivado de `fields()`, não enumerado à mão: `to_dict` é construtor
        campo-a-campo, e o padrão "construtor campo-a-campo perde campo novo" já
        mordeu neste repo. Enumerar aqui repetiria a mesma omissão 2×."""
        import dataclasses

        item = PontoUrgenteItem("Alta", "Ação X", "Impacto", "Imediato")
        assert set(item.to_dict()) == {f.name for f in dataclasses.fields(PontoUrgenteItem)}

    def test_item_to_dict(self):
        item = PontoUrgenteItem("Alta", "Ação X", "Impacto", "Imediato")
        d = item.to_dict()
        assert d == {
            "prioridade": "Alta",
            "acao": "Ação X",
            "impacto": "Impacto",
            "prazo": "Imediato",
            "code": "",
            "origem_premissa": "derivado_e5",
            "elegibilidade": "computavel",
            "dado_faltante": None,
        }

    def test_seguro_sempre_presente_mesmo_quando_tudo_ok(self):
        out = PontosUrgentesAnalyzer().analyze(
            _ratios(endiv=5, rent="10%"), _reserva(cobertura=24), _pat()
        )
        # Sem reserva, sem endividamento, sem rentabilidade N/D.
        # Seguro é o único que dispara.
        assert len(out) == 1
        assert out[0].acao == "Contratar seguro de vida e invalidez"
