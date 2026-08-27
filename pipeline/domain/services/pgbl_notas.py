"""Copy do card PGBL — uma nota por motivo dominante ([[ADR-402]] D4).

Separado de ``previdencia_analyzer`` porque é PRESENTAÇÃO, não regra: cada motivo
novo traz uma nota, e o analyzer não deveria crescer por causa de texto.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from pipeline.domain.services.brl_prose import fmt_brl_prosa
from pipeline.domain.services.irpf_pgbl_capacidade import PgblStatus
from pipeline.domain.services.pgbl_motivos import MotivoAusenciaPgbl

if TYPE_CHECKING:  # ciclo em runtime: o analyzer importa este módulo
    from pipeline.domain.services.previdencia_analyzer import (
        CapacidadePgblIRPF,
        PrevidenciaConfig,
    )

_NOTA_SEM_CAPACIDADE = (
    "Não há IRPF processado para medir o seu espaço dedutível de PGBL. O limite de "
    "12% incide sobre a renda tributável declarada na pessoa física — pró-labore e "
    "demais rendimentos tributáveis —, e lucros distribuídos não entram nessa base. "
    "Processe a declaração mais recente para que este número apareça."
)


# ADR-305 D3 (co-design financial-planner): a capacidade lida do IRPF é
# retrospectiva — o número recomenda o ano-calendário CORRENTE via proxy.
_NOTA_PROXY_ANO_CORRENTE = (
    "O espaço dedutível de 12% aplica-se ao ano-calendário corrente — aportes até "
    "31/12 deduzem na próxima declaração; se a renda tributável atual diferir do "
    "ano-base, o espaço real muda proporcionalmente."
)


# RV2-03 (co-design financial-planner): a nota ramifica por PgblStatus, não por
# restante>0. modelo_simplificado (dedução desabilitada pelo modelo) e no_teto
# (teto de 12% consumido) colapsavam ambos em "teto atingido" — factualmente falso
# no simplificado e invertia o conselho. Sem fabricar 12% hipotético (limite/aporte
# ficam 0 — só a prosa cita a hipótese). Conformidade a ADR-305 D3.
_NOTA_DIFERIMENTO = (
    "Lembre que o PGBL difere o IR — o resgate é tributado; o benefício depende da alíquota futura."
)
_NOTA_SIMPLIFICADO = (
    "Declaração no modelo simplificado no ano-base {ano}: o desconto padrão "
    "substitui as deduções legais, então o PGBL não gera economia de IR neste "
    "modelo — o teto de 12% não foi consumido. Migrar para o modelo completo só "
    "compensa se a soma das deduções legais (incluindo até 12% da renda tributável "
    "em PGBL) superar o desconto simplificado, e a dedução de 12% pressupõe "
    "contribuição a regime oficial de previdência. Avalie com seu contador — a "
    "opção de modelo é feita a cada declaração e vale para o ano-calendário corrente."
)
_NOTA_SEM_RENDA = (
    "Sem renda tributável no ano-base {ano}: sem base de cálculo, o PGBL não gera "
    "dedução de IR no momento. O benefício reaparece se houver renda tributável "
    "(ex.: pró-labore ou PJ tributada); reavalie se a situação mudar."
)
_NOTA_NO_TETO = (
    "Teto de 12% da renda tributável já atingido no ano-base {ano} — aportes "
    "adicionais em PGBL não trazem dedução extra neste ano."
)


# A40.l64 — a row de AC2026 nasce `regime_completo=False` porque a tabela
# progressiva deixou de descrever sozinha o imposto devido. Os dois componentes
# que faltam são independentes do aporte, então a diferencial por faixa
# superestima: quem tem tributável anual até R$ 60k já paga zero depois do
# redutor, e acima de R$ 600k o mínimo reabsorve o que a dedução economiza.
_COMPONENTE_LABEL = {
    "redutor_lei_15270": "o redutor da Lei 15.270/2025",
    "irpfm": "o imposto mínimo sobre altas rendas (IRPFM)",
}


def _lista_componentes(componentes: tuple[str, ...]) -> str:
    """Rótulos legíveis em português; termo desconhecido sai verbatim, não sumido."""
    rotulos = [_COMPONENTE_LABEL.get(c, c) for c in componentes]
    if not rotulos:
        return "componentes do regime vigente"
    if len(rotulos) == 1:
        return rotulos[0]
    return f"{', '.join(rotulos[:-1])} e {rotulos[-1]}"


_NOTA_REGIME_INCOMPLETO = (
    "A estimativa de economia de IR não se aplica ao ano-calendário {ano}: a tabela "
    "progressiva deixou de descrever sozinha o imposto devido, e ainda falta modelar "
    "{componentes}. Nenhum deles se move com o aporte, então calcular a economia pela "
    "diferença de faixa superestimaria o benefício — e para renda tributável de até "
    "R$ 60 mil no ano, em que o imposto já fica zerado, publicaria uma economia "
    "inexistente. O seu espaço dedutível de 12% continua válido e está declarado acima; "
    "a estimativa volta quando o regime estiver completo."
)


def _nota_regime_incompleto(config: "PrevidenciaConfig") -> str:
    ano = config.ano_fiscal or "corrente"
    return _NOTA_REGIME_INCOMPLETO.format(
        ano=ano, componentes=_lista_componentes(config.componentes_ausentes)
    )


def _nota_capacidade_irpf(cap: "CapacidadePgblIRPF", restante: Decimal | None) -> str:
    """Fato medido (sem motivo dominante de ausência total): teto vivo ou consumido."""
    ano = cap.ano_base
    if cap.pgbl_status == PgblStatus.no_teto or not restante or restante <= 0:
        return f"{_NOTA_NO_TETO.format(ano=ano)} {_NOTA_PROXY_ANO_CORRENTE}"
    capacidade = (
        f"Capacidade PGBL restante do IRPF {ano}: {fmt_brl_prosa(restante)} "
        "(já descontado o aportado)."
    )
    return f"{capacidade} {_NOTA_DIFERIMENTO} {_NOTA_PROXY_ANO_CORRENTE}"


# Nomeia o mecanismo, não a nossa incapacidade: o cliente precisa entender que o
# PGBL não deixou de valer — o benefício é reabsorvido pelo mínimo enquanto ele
# vincular, e isso muda com o perfil de renda dele.
# Declara que a limitação é NOSSA. O cliente não tem o que corrigir — e dizer
# "não se aplica" aqui seria empurrar para ele um problema de modelagem.
_NOTA_BASE_FAMILIAR = (
    "Sua família tem mais de uma declaração de IRPF neste ano-base. O imposto é "
    "apurado por declaração, e ainda não separamos a base de cada uma — somar as "
    "duas superestimaria a economia, porque a tabela é progressiva. Preferimos não "
    "publicar um número que sabemos estar alto."
)

# Nomeia o que falta no NOSSO lado. O cliente não tem o que corrigir, e dizer
# "não se aplica ao ano" seria afirmar sobre um regime que não conhecemos.
_NOTA_SEM_TABELA = (
    "Ainda não temos a tabela do imposto de renda de {ano} carregada. Sem ela, "
    "qualquer economia de PGBL que publicássemos seria chute — preferimos não "
    "publicar. O espaço de 12% do seu IRPF continua válido e aparece acima."
)

_NOTA_IRPFM = (
    "Sua renda total do ano fica na faixa do imposto mínimo (IRPFM, Lei 15.270/2025): "
    "acima de R$ 600 mil, o IR devido pela tabela é abatido do mínimo, então reduzir "
    "o imposto com PGBL não gera economia líquida enquanto o mínimo vincular. "
    "Prescrever aporte aqui seria conselho com o sinal invertido."
)


#: Motivos cuja nota SUBSTITUI o fato da capacidade.
_NOTA_SUBSTITUI = {
    MotivoAusenciaPgbl.modelo_simplificado: _NOTA_SIMPLIFICADO,
    MotivoAusenciaPgbl.sem_renda_tributavel: _NOTA_SEM_RENDA,
    MotivoAusenciaPgbl.sem_tabela_fiscal_do_ano: _NOTA_SEM_TABELA,
}

#: Motivos cuja nota PREFIXA o fato. `regime_fiscal_incompleto` fica de fora
#: porque depende da config (lista os componentes ausentes).
_NOTA_PREFIXA = {
    MotivoAusenciaPgbl.base_familiar_nao_particionada: _NOTA_BASE_FAMILIAR,
    MotivoAusenciaPgbl.irpfm_pode_vincular: _NOTA_IRPFM,
}


def _nota_do_motivo(
    dominante: MotivoAusenciaPgbl | None,
    cap: "CapacidadePgblIRPF",
    config: "PrevidenciaConfig",
) -> str:
    """Uma nota, um motivo. A precedência já calou os demais."""
    if dominante in _NOTA_SUBSTITUI:
        return _NOTA_SUBSTITUI[dominante].format(ano=cap.ano_base)
    fato = _nota_capacidade_irpf(cap, cap.capacidade.restante)
    prefixo = _NOTA_PREFIXA.get(dominante)
    if dominante == MotivoAusenciaPgbl.regime_fiscal_incompleto:
        prefixo = _nota_regime_incompleto(config)
    return f"{prefixo} {fato}" if prefixo else fato
