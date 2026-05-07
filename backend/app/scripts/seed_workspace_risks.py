"""Seed dos 5 riscos universais Cerbasi para um workspace (ADR-178).

Não-cliente-específico: morte, invalidez, doença grave, desemprego,
longevidade. Todos com ``status="Ativo"`` e ``probability=None`` (cliente
preenche). ``impact_level`` calibrado pelo arquétipo do provedor.

Função `seed_default_risks(workspace_id, session)` é exposta para o
``WorkspaceCreate`` use case chamar opcionalmente. Não executa
automaticamente — integração com onboarding fica em A10.7.

Riscos cliente-específicos (concentração PJ, cambial, sucessório,
iliquidez) NÃO entram aqui: são adicionados pelo consultor/cliente via
UI (ADR-178 §"Decisão").
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.risk import Risk


@dataclass(frozen=True)
class _RiskTemplate:
    code: str
    name: str
    rationale: str
    impact_level: str


# Cerbasi 5 riscos universais do provedor financeiro. Rationales ≥ 10 chars.
# Ordem visível na UI segue ranking (impact_level → probability), não esta
# lista — a lista é apenas template estável.
DEFAULT_RISK_TEMPLATES: tuple[_RiskTemplate, ...] = (
    _RiskTemplate(
        code="morte",
        name="Morte do provedor",
        rationale=(
            "Falecimento do principal gerador de renda compromete a renda "
            "familiar e o plano de IF. Cerbasi: protege com seguro de vida "
            "+ inventário + sucessão estruturada."
        ),
        impact_level="crítico",
    ),
    _RiskTemplate(
        code="invalidez",
        name="Invalidez do provedor",
        rationale=(
            "Perda de capacidade laboral sem morte: piora o orçamento "
            "(despesas médicas + queda de renda) sem ativar seguro de "
            "vida. Cobertura por seguro de invalidez específico."
        ),
        impact_level="alto",
    ),
    _RiskTemplate(
        code="doenca_grave",
        name="Doença grave",
        rationale=(
            "Tratamento de longa duração (oncológico, cardíaco, etc.) "
            "drena reserva de emergência e pode interromper aportes. "
            "Plano de saúde robusto + seguro doença grave mitigam."
        ),
        impact_level="alto",
    ),
    _RiskTemplate(
        code="desemprego",
        name="Desemprego ou queda de renda",
        rationale=(
            "Demissão CLT ou perda de cliente PJ relevante reduz aporte e "
            "consome reserva. Cerbasi: 6-12 meses de reserva de emergência "
            "calibrados pela estabilidade da fonte de renda."
        ),
        impact_level="médio",
    ),
    _RiskTemplate(
        code="longevidade",
        name="Longevidade (sobreviver à reserva)",
        rationale=(
            "Esgotar patrimônio antes do fim da vida — risco simétrico ao "
            "de morte precoce. Mitigado por TRS conservadora (3-4%) + "
            "previdência privada + ajuste dinâmico de retiradas."
        ),
        impact_level="alto",
    ),
)


async def seed_default_risks(workspace_id: str, session: AsyncSession) -> list[Risk]:
    """Cria os 5 riscos universais Cerbasi para o workspace.

    Idempotente por construção do caller: se o workspace já tem risks
    com esses ``code``s, viola UNIQUE — chamar apenas em workspace novo.
    Retorna lista de Risks recém-criados (já flushed; caller commita).
    """
    created: list[Risk] = []
    for template in DEFAULT_RISK_TEMPLATES:
        risk = Risk(
            workspace_id=workspace_id,
            code=template.code,
            name=template.name,
            rationale=template.rationale,
            probability=None,
            impact_level=template.impact_level,
            impact_brl_cents=None,
            status="Ativo",
            mitigations_decision_ids=[],
        )
        session.add(risk)
        created.append(risk)
    await session.flush()
    return created
