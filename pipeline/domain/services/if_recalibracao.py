"""Nota one-shot de recalibração do bloco de IF (ADR-360 §Nota one-shot · A40.l25)."""
# O cliente abre o relatório novo e lê "IF em 2049" onde antes lia "2046", sem
# que a vida financeira dele tenha mudado. Sem aviso, ele conclui que piorou.
#
# O gatilho NÃO é uma lista de strings de versão — isso fica stale no próximo
# bump. É um diff sobre este ledger, que cada versão preenche ao nascer; bump
# sem entrada aqui derruba tests/test_if_recalibracao.py.
#
# Regra que gera tudo: par de números só quando os dois respondem à MESMA
# pergunta. O ano do cenário central responde a mesma pergunta em 2.0 e 3.0
# (mudou o estimador), logo tem par. A probabilidade responde a OUTRA pergunta
# em 5.0 (ADR-369 D2 — passou a medir o prazo declarado), logo nunca tem par e
# o número antigo nunca é impresso.

from __future__ import annotations

from typing import Any

FACETA_ANO_CONE = "ano_cone"
FACETA_PROBABILIDADE_ALVO = "probabilidade_alvo"

# major de `mc_version` → facetas que AQUELE bump moveu.
_EFEITOS_POR_MC_VERSION: dict[int, tuple[str, ...]] = {
    1: (),  # linha de base (artefato pré-ADR-360, sem carimbo)
    2: (FACETA_ANO_CONE,),  # seedado, percentil dos sobreviventes
    3: (FACETA_ANO_CONE,),  # percentil censurado na base cheia (ADR-361)
    4: (),  # rename-only (ADR-369 D1) — valores idênticos a 3.0
    5: (FACETA_PROBABILIDADE_ALVO,),  # muda o ALVO, não a calibração (ADR-369 D2)
}

# Ordem em que os números aparecem na S7 — fixa, não por severidade.
_ORDEM_FACETAS = (FACETA_ANO_CONE, FACETA_PROBABILIDADE_ALVO)


def majors_declarados() -> frozenset[int]:
    """Majors com efeito declarado — consumido pelo gate de bump."""
    return frozenset(_EFEITOS_POR_MC_VERSION)


def mc_major(bloco: dict[str, Any] | None) -> int:
    """Major de `mc_version`; ausente em bloco LEGÍVEL = 1 (artefato pré-ADR-360)."""
    bruto = str((bloco or {}).get("mc_version") or "1.0")
    cabeca = bruto.split(".", 1)[0]
    return int(cabeca) if cabeca.isdigit() else 1


def resolve_facetas(anterior: int, atual: int) -> tuple[str, ...]:
    """União dos efeitos no intervalo semiaberto (anterior, atual]."""
    # Semiaberto para que workspace que PULA versões receba todas as facetas de
    # uma vez, numa nota só, em vez de nenhuma.
    movidas = {
        faceta
        for major, facetas in _EFEITOS_POR_MC_VERSION.items()
        if anterior < major <= atual
        for faceta in facetas
    }
    return tuple(f for f in _ORDEM_FACETAS if f in movidas)
