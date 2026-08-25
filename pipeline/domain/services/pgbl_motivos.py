"""Motivos de ausência do card PGBL — enum fechado, precedência e derivação.

Separado de ``previdencia_analyzer`` porque é a superfície que cresce: cada lane
que descobre um insumo faltante novo acrescenta um valor aqui, e o analyzer não
deveria inchar por isso ([[ADR-402]]).
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from pipeline.domain.services.irpf_pgbl_capacidade import PgblStatus

if TYPE_CHECKING:  # ciclo em runtime: o analyzer importa este módulo
    from pipeline.domain.services.previdencia_analyzer import CapacidadePgblIRPF


# `nota_degradacao` NÃO serve a este papel: tem dono semântico (ADR-305 D3 —
# "existe ano-base mais recente não usado") e coocorre com estes motivos.
class MotivoAusenciaPgbl(str, Enum):
    """Por que um campo do card PGBL nasce ausente (ADR-402). Enum fechado."""

    sem_irpf_processado = "sem_irpf_processado"
    modelo_simplificado = "modelo_simplificado"
    sem_renda_tributavel = "sem_renda_tributavel"
    regime_fiscal_incompleto = "regime_fiscal_incompleto"
    # Único motivo que nomeia CONCLUSÃO de cálculo, não insumo faltante — e o
    # único que coexiste com campos publicados (a economia zero fica). Por isso
    # é o último da precedência: qualquer insumo faltante o cala.
    sem_imposto_a_reduzir = "sem_imposto_a_reduzir"
    # Acima do piso do IRPFM a dedução do PGBL reduz o IR-tabela, que é ABATIDO
    # do mínimo — a economia líquida some enquanto o mínimo vincula. Prescrever
    # ali é conselho com o SINAL invertido, no público principal do produto.
    irpfm_pode_vincular = "irpfm_pode_vincular"
    # Limitação NOSSA, não do dado: a base soma as declarações do ano e a
    # progressividade não é aditiva. Só ocorre com 2+ declarantes.
    base_familiar_nao_particionada = "base_familiar_nao_particionada"


# Precedência declarada: o primeiro que se aplica é o dominante e CALA os demais.
# Sem ela, o r7 publicou uma nota que casava `_NOTA_REGIME_INCOMPLETO` E
# `_NOTA_SIMPLIFICADO` — duas explicações mutuamente exclusivas no mesmo texto.
PRECEDENCIA_MOTIVO_PGBL: tuple[MotivoAusenciaPgbl, ...] = (
    MotivoAusenciaPgbl.sem_irpf_processado,
    MotivoAusenciaPgbl.modelo_simplificado,
    MotivoAusenciaPgbl.sem_renda_tributavel,
    MotivoAusenciaPgbl.regime_fiscal_incompleto,
    MotivoAusenciaPgbl.irpfm_pode_vincular,
    MotivoAusenciaPgbl.base_familiar_nao_particionada,
    MotivoAusenciaPgbl.sem_imposto_a_reduzir,
)

# Os quatro campos que podem nascer ausentes, na ordem em que o card os lê.
CAMPOS_MOTIVO_PGBL: tuple[str, ...] = ("teto", "restante", "aporte", "economia")

# Fonte única do par (motivo, texto): a nota e os campos derivam AMBOS do VO, e
# este mapa é o que permite ao gate assertar coocorrência em vez de inspecionar.
FRAGMENTO_CANONICO_MOTIVO: dict[MotivoAusenciaPgbl, str] = {
    MotivoAusenciaPgbl.sem_irpf_processado: "Não há IRPF processado",
    MotivoAusenciaPgbl.modelo_simplificado: "modelo simplificado",
    MotivoAusenciaPgbl.sem_renda_tributavel: "Sem renda tributável",
    MotivoAusenciaPgbl.regime_fiscal_incompleto: "não se aplica ao ano-calendário",
}


def motivo_dominante(
    motivos: dict[str, MotivoAusenciaPgbl | None],
) -> MotivoAusenciaPgbl | None:
    """O motivo de maior precedência presente — quem decide a nota."""
    presentes = {m for m in motivos.values() if m is not None}
    for motivo in PRECEDENCIA_MOTIVO_PGBL:
        if motivo in presentes:
            return motivo
    return None


# Carrega o VO inteiro, não o escalar: `teto` e `restante` são grandezas
# distintas, e o campo publicado com nome de teto precisa do teto.
# Direção da derivação (ADR-402): nota e campos derivam AMBOS do VO. A nota
# nunca é escrita ao lado do campo, e o campo nunca é lido a partir da nota —
# `null` não carrega a razão de ser `null`, então "nota derivada do campo" é
# inexequível. O motivo dominante é o pivô comum.
# Anula a PRESCRIÇÃO e preserva o FATO: teto e restante vêm do IRPF e não dependem
# do regime, do mínimo nem de quantas declarações compõem a base.
def _so_prescricao(motivo: MotivoAusenciaPgbl) -> dict[str, MotivoAusenciaPgbl | None]:
    return {"teto": None, "restante": None, "aporte": motivo, "economia": motivo}


def _motivos_por_campo(
    cap: "CapacidadePgblIRPF", regime_completo: bool, irpfm_vincula: bool = False
) -> dict[str, MotivoAusenciaPgbl | None]:
    """Aplica a precedência aos 4 campos. Fonte única do que é ausência e por quê."""
    if cap.pgbl_status == PgblStatus.modelo_simplificado:
        return dict.fromkeys(CAMPOS_MOTIVO_PGBL, MotivoAusenciaPgbl.modelo_simplificado)
    # `teto is None` sem status simplificado significa que nenhuma declaração
    # COMPLETA tem base tributável — a dedução de 12% não tem sobre o que incidir.
    if cap.pgbl_status == PgblStatus.sem_renda_tributavel or cap.capacidade.teto is None:
        return dict.fromkeys(CAMPOS_MOTIVO_PGBL, MotivoAusenciaPgbl.sem_renda_tributavel)
    if irpfm_vincula:
        return _so_prescricao(MotivoAusenciaPgbl.irpfm_pode_vincular)
    if cap.declaracoes_no_ano > 1:
        return _so_prescricao(MotivoAusenciaPgbl.base_familiar_nao_particionada)
    if not regime_completo:
        return _so_prescricao(MotivoAusenciaPgbl.regime_fiscal_incompleto)
    return dict.fromkeys(CAMPOS_MOTIVO_PGBL, None)


def _prescreve(economia: Decimal | None) -> bool:
    """ADR-375 D4 cond. 2: prescrever exige `IR(base) − IR(base − aporte) > 0`."""
    return economia is not None and economia > 0


# Economia zero é FATO publicável (o cliente já não paga IR), mas não autoriza
# prescrever aporte. O gate antigo era o motivo, e o motivo não conhecia o
# resultado do cálculo — então o caso isento que o diferencial destravou saía
# com "aporte sugerido" ao lado de "economia R$ 0,00".
def _com_motivo_de_economia_nula(
    motivos: dict[str, MotivoAusenciaPgbl | None],
    economia: Decimal | None,
    restante: Decimal | None,
) -> dict[str, MotivoAusenciaPgbl | None]:
    # `restante == 0` já é `no_teto`: ali o aporte zero é a RESPOSTA ("não aporte
    # mais, o espaço acabou"), publicada como fato sem motivo (ADR-402). A causa
    # da economia nula é o teto consumido, não a ausência de imposto — atribuir
    # `sem_imposto_a_reduzir` ali nomearia a causa errada.
    if economia is None or _prescreve(economia) or motivos["aporte"] is not None:
        return motivos
    if restante is None or restante <= 0:
        return motivos
    return {**motivos, "aporte": MotivoAusenciaPgbl.sem_imposto_a_reduzir}
