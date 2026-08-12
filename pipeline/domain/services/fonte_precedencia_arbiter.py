"""Árbitro de precedência temporal entre pools de fontes patrimoniais (ADR-383 · A40.l41).

Fase OBSERVACIONAL (PR-a da lane): o árbitro compara fontes INTEIRAS —
nunca ativo isolado ([[ADR-346]] preservada por construção) — e emite
veredito + warnings tipados, **sem alterar** o número que o PL consome.
O flip (PR-b) só acontece após o relatório veredito×atual sobre o dogfood.

Ordem lexicográfica (ADR-383 §1): data-alvo da visão → proximidade da
data-alvo sem look-ahead (``data_referencia <= alvo``) → qualidade no
empate. ``desconhecida`` nunca vence: fonte sem data só é elegível quando
é a única da célula.
"""

from __future__ import annotations

from dataclasses import dataclass

from pipeline.domain.services.patrimonio_types import (
    normalize_data_referencia,
    parse_ano_31_12,
)

#: Qualidade no empate de data, por tipo de quantidade (ADR-383 §1) — menor
#: rank vence. Para VALOR DE POSIÇÃO: IRPF entregue > informe certificado >
#: report de posição. (Caixa tem hierarquia própria na ADR-376 e não passa
#: por este árbitro nesta fase.)
_QUALIDADE_POSICAO = {"irpf": 0, "informe": 1, "posicoes_atuais": 2}


@dataclass(frozen=True)
class FontePatrimonial:
    """Unidade de arbitragem: uma FONTE inteira de valor por (instituição, membro)."""

    pool: str  # "posicoes_atuais" | "irpf" | "informe"
    instituicao: str  # code/slug normalizado
    membro: str
    # Observacional NÃO carrega valor monetário (LGPD + ADR-090): o delta é
    # recomputado no flip (PR-b), quando o consumo trocar de fonte.
    data_referencia: str | None  # YYYY-MM-DD (fim de período) ou None
    data_precisao: str = "desconhecida"


# Sem valor monetário persistido (LGPD, padrão booleans da ADR-238).
@dataclass(frozen=True)
class ContradicaoFonte:
    """Fonte adotada pelo caminho atual contradita por fonte mais fresca (ADR-097 D1)."""

    instituicao: str
    membro: str
    pool_atual: str
    data_atual: str | None
    pool_mais_fresco: str
    data_mais_fresca: str | None

    def format(self) -> str:
        return (
            f"posição de {self.instituicao} ({self.membro}) vem de "
            f"{self.pool_atual} ({self.data_atual or 'sem data'}), mas existe fonte "
            f"mais fresca: {self.pool_mais_fresco} ({self.data_mais_fresca}); "
            f"revise antes de confiar no valor (ADR-383)."
        )

    def to_dict(self) -> dict:
        return {
            "instituicao": self.instituicao,
            "membro": self.membro,
            "pool_atual": self.pool_atual,
            "data_atual": self.data_atual,
            "pool_mais_fresco": self.pool_mais_fresco,
            "data_mais_fresca": self.data_mais_fresca,
        }


@dataclass(frozen=True)
class VereditoFrescor:
    """Saída observacional: célula → pool vencedor + contradições detectadas."""

    vencedores: dict[tuple[str, str], FontePatrimonial]
    contradicoes: tuple[ContradicaoFonte, ...]

    def to_payload(self) -> dict:
        """Bloco observacional do E5 — sem valores monetários (LGPD)."""
        return {
            "celulas": [
                {
                    "instituicao": inst,
                    "membro": membro,
                    "pool_vencedor": f.pool,
                    "data_referencia": f.data_referencia,
                }
                for (inst, membro), f in sorted(self.vencedores.items())
            ],
            "contradicoes": [c.to_dict() for c in self.contradicoes],
        }


# ``pool_atual_por_celula`` declara qual pool o caminho de produção usa hoje
# para cada célula — quando o veredito diverge, sai ``ContradicaoFonte``.
def arbitrar_frescor(
    fontes: list[FontePatrimonial],
    *,
    data_alvo: str,
    pool_atual_por_celula: dict[tuple[str, str], str] | None = None,
) -> VereditoFrescor:
    """Escolhe a fonte vencedora por célula (instituição, membro) na ``data_alvo``."""
    por_celula: dict[tuple[str, str], list[FontePatrimonial]] = {}
    for f in fontes:
        por_celula.setdefault((f.instituicao, f.membro), []).append(f)
    vencedores = {
        celula: v
        for celula, candidatas in por_celula.items()
        if (v := _vencedor_da_celula(candidatas, data_alvo)) is not None
    }
    contradicoes = tuple(
        _contradicao(celula, por_celula[celula], atual, vencedor)
        for celula, vencedor in vencedores.items()
        if (atual := (pool_atual_por_celula or {}).get(celula)) and atual != vencedor.pool
    )
    return VereditoFrescor(vencedores=vencedores, contradicoes=contradicoes)


def _vencedor_da_celula(
    candidatas: list[FontePatrimonial], data_alvo: str
) -> FontePatrimonial | None:
    datadas = [f for f in candidatas if f.data_referencia and f.data_referencia <= data_alvo]
    if not datadas:
        # ``desconhecida`` nunca vence — só entra quando é a única da célula.
        return candidatas[0] if len(candidatas) == 1 else _melhor_qualidade(candidatas)
    melhor_data = max(f.data_referencia for f in datadas)  # type: ignore[type-var]
    empatadas = [f for f in datadas if f.data_referencia == melhor_data]
    return _melhor_qualidade(empatadas)


def _melhor_qualidade(fontes: list[FontePatrimonial]) -> FontePatrimonial:
    return min(fontes, key=lambda f: (_QUALIDADE_POSICAO.get(f.pool, 99), f.pool))


def _contradicao(
    celula: tuple[str, str],
    candidatas: list[FontePatrimonial],
    pool_atual: str,
    vencedor: FontePatrimonial,
) -> ContradicaoFonte:
    atual = next((f for f in candidatas if f.pool == pool_atual), None)
    return ContradicaoFonte(
        instituicao=celula[0],
        membro=celula[1],
        pool_atual=pool_atual,
        data_atual=atual.data_referencia if atual else None,
        pool_mais_fresco=vencedor.pool,
        data_mais_fresca=vencedor.data_referencia,
    )


# =============================================================================
# Montagem dos pools a partir dos payloads reais (produtor normaliza datas)
# =============================================================================


def fontes_de_posicoes_atuais(investimentos_raw: dict, *, membro_default: str) -> list:
    """Pool E4: agrega ``dados[]`` por (instituição, membro) com a data MÍNIMA
    das posições da fonte (conservador: a fonte é tão fresca quanto a posição
    mais velha que ela contém)."""
    grupos: dict[tuple[str, str], list[dict]] = {}
    for pos in investimentos_raw.get("dados", []) or []:
        inst = _slug(pos.get("instituicao"))
        membro = _slug(pos.get("membro")) or membro_default
        if inst:
            grupos.setdefault((inst, membro), []).append(pos)
    return [_fonte_e4(inst, membro, posicoes) for (inst, membro), posicoes in grupos.items()]


def _fonte_e4(inst: str, membro: str, posicoes: list[dict]) -> FontePatrimonial:
    datas = []
    for pos in posicoes:
        raw = pos.get("data_referencia")
        raw = raw.get("fim") if isinstance(raw, dict) else raw
        datas.append(normalize_data_referencia(raw)[0])
    data_fonte = min(datas) if datas and all(datas) else None
    return FontePatrimonial(
        pool="posicoes_atuais",
        instituicao=inst,
        membro=membro,
        data_referencia=data_fonte,
        data_precisao="dia" if data_fonte else "desconhecida",
    )


# Pool IRPF: cada ano com valor em ``valores_31_12`` é uma fonte própria da
# célula (instituição, membro), datada 31/12/ano.
def fontes_de_irpf(investimentos_consolidados: list[dict]) -> list:
    celulas: set[tuple[str, str, int]] = set()
    for item in investimentos_consolidados or []:
        inst = _slug(item.get("instituicao"))
        membro = _slug(item.get("proprietario"))
        if not inst:
            continue
        anos = (parse_ano_31_12(k) for k in item.get("valores_31_12") or {})
        celulas.update((inst, membro, ano) for ano in anos if ano is not None)
    return [_fonte_irpf(inst, membro, ano) for inst, membro, ano in sorted(celulas)]


def _fonte_irpf(inst: str, membro: str, ano: int) -> FontePatrimonial:
    return FontePatrimonial(
        pool="irpf",
        instituicao=inst,
        membro=membro,
        data_referencia=f"{ano}-12-31",
        data_precisao="dia",
    )


def _slug(v: object) -> str:
    import unicodedata

    s = unicodedata.normalize("NFKD", str(v or "")).encode("ascii", "ignore").decode().lower()
    return "".join(ch for ch in s if ch.isalnum())
