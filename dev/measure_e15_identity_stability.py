#!/usr/bin/env python3
r"""Critério 6 da [[A42.l15]] — harness OFFLINE de estabilidade do `investment_id`."""

# Mede ``|A∩B|/|A∪B|`` sobre o conjunto de `investment_id` entre K extrações do MESMO
# documento na MESMA era de prompt, replayando artefatos `E1.5a` já gravados. Zero token
# de LLM: a variação já está no corpus.
#
# Por que replay e não runs novos (§Armadilha D): estabilidade run-a-run é gameável numa
# linha (`use_cache=True` em `litellm_client.py`) e não pode ser o critério de aceite.
# Artefato histórico foi gravado com o cache desligado, então a variação que ele carrega é
# real. Para o regime futuro o harness ainda checa pares byte-idênticos e os reporta
# separado — ao 23,5% medido, par idêntico é anomalia, não sorte.
#
# Uso:
#   python3 dev/measure_e15_identity_stability.py
#   python3 dev/measure_e15_identity_stability.py --json
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# O critério pede K>=5 amostras e >=2 documentos. Medido em 2026-08-31: o corpus sustenta
# os dois (47 pares (doc, era) com >=5 amostras), então nada aqui precisa de run novo.
K_MINIMO = 5
DOCS_MINIMO = 2

# `secao` e `categoria_hint` são CONTROLE NEGATIVO declarado: o prompt os enumera e a
# medição de abertura da lane os viu imóveis (0 e 1 divergências em 72 pares). Se eles se
# moverem numa amostra, o que mudou não foi só a descrição — e o número inteiro é inválido.
CONTROLES_NEGATIVOS = ("secao", "categoria_hint")


@dataclass
class GrupoResult:
    """Um (documento, era). TRÊS estados, porque dois colapsam causas distintas."""

    # A 1ª execução real colapsava `sem investimento` em `controle moveu`, e o operador lia
    # falha de controle onde não havia nada a medir — a mesma patologia que a lane registra
    # nas duas pernas HARD do `compare_reviews` (§O dano de gate).

    documento: str
    era: str
    k: int
    intersecao: int = 0
    uniao: int = 0
    pares: int = 0
    ids_por_amostra: tuple[int, ...] = ()
    controles_que_moveram: tuple[str, ...] = ()
    pares_byte_identicos: int = 0

    @property
    def aplicavel(self) -> bool:
        """Documento sem investimento nenhum não é falha — é nada a medir."""
        return self.uniao > 0

    @property
    def valido(self) -> bool:
        return self.aplicavel and not self.controles_que_moveram

    @property
    def cardinalidade_media(self) -> float:
        """100% sobre 1 id não é 100% sobre 60 — sem isto o número engana."""
        if not self.ids_por_amostra:
            return 0.0
        return round(sum(self.ids_por_amostra) / len(self.ids_por_amostra), 1)

    @property
    def estabilidade_pct(self) -> float | None:
        """`None` quando inválido — quem chama não consegue imprimir número sem checar."""
        if not self.valido:
            return None
        return round(100.0 * self.intersecao / self.uniao, 2)


@dataclass
class Corrida:
    grupos: list[GrupoResult] = field(default_factory=list)
    excluidos_por_k: int = 0
    ilegiveis: int = 0

    @property
    def documentos_medidos(self) -> int:
        return len({g.documento for g in self.grupos})


def era_do_payload(payload: dict) -> str:
    """A era vem do PAYLOAD, nunca da coluna `prompt_version`."""
    # Medido 2026-08-31: a coluna diverge do payload em 394/836 artefatos E1.5a (47,1%),
    # sempre no mesmo sentido — coluna `NULL` onde o payload sabe a era (1.0.0=154,
    # 1.1.0=190, 1.2.0=50). Agrupar pela coluna misturaria três eras numa só.
    return str(payload.get("prompt_version") or "NULL")


def identity_set(payload: dict) -> set[str]:
    """Conjunto de `investment_id` pelo caminho REAL — consolidador + dedup, nesta ordem."""
    from pipeline.domain.services.investimentos_dedup import dedup_investimentos_consolidados
    from scripts.consolidate_baseline import consolidate_from_itens

    with contextlib.redirect_stdout(io.StringIO()):
        consolidado = consolidate_from_itens(payload)
        dedup = dedup_investimentos_consolidados(
            consolidado.get("investimentos_consolidados") or []
        )
    return {e["investment_id"] for e in dedup.investimentos if e.get("investment_id")}


def assinatura_de_controle(payload: dict) -> dict[str, Counter]:
    """Multiset por campo de controle — ordem dos itens não é sinal, contagem é."""
    itens = payload.get("itens") or []
    return {campo: Counter(str(i.get(campo) or "") for i in itens) for campo in CONTROLES_NEGATIVOS}


def controles_que_moveram(payloads: Sequence[dict]) -> tuple[str, ...]:
    assinaturas = [assinatura_de_controle(p) for p in payloads]
    primeira = assinaturas[0]
    moveram = {c for a in assinaturas[1:] for c in CONTROLES_NEGATIVOS if a[c] != primeira[c]}
    return tuple(sorted(moveram))


def _jaccard(a: set[str], b: set[str]) -> tuple[int, int]:
    """(numerador, denominador) — percentual sozinho não é auditável."""
    return len(a & b), len(a | b)


def avaliar_grupo(documento: str, era: str, payloads: Sequence[dict]) -> GrupoResult:
    """Jaccard agregado sobre TODOS os pares, não só o primeiro contra o resto."""
    conjuntos = [identity_set(p) for p in payloads]
    resultado = GrupoResult(documento=documento, era=era, k=len(payloads))
    resultado.controles_que_moveram = controles_que_moveram(payloads)
    resultado.ids_por_amostra = tuple(len(c) for c in conjuntos)
    for esq, dir_ in combinations(range(len(conjuntos)), 2):
        inter, uni = _jaccard(conjuntos[esq], conjuntos[dir_])
        resultado.intersecao += inter
        resultado.uniao += uni
        resultado.pares += 1
        resultado.pares_byte_identicos += int(payloads[esq] == payloads[dir_])
    return resultado


def agrupar(artefatos: Iterable[tuple[str, dict]]) -> dict[tuple[str, str], list[dict]]:
    grupos: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for documento, payload in artefatos:
        grupos[(documento, era_do_payload(payload))].append(payload)
    return grupos


def medir(artefatos: Iterable[tuple[str, dict]], ilegiveis: int = 0) -> Corrida:
    """Grupo com K<K_MINIMO é EXCLUÍDO e CONTADO — truncagem silenciosa lê como cobertura."""
    corrida = Corrida(ilegiveis=ilegiveis)
    for (documento, era), payloads in sorted(agrupar(artefatos).items()):
        if len(payloads) < K_MINIMO:
            corrida.excluidos_por_k += 1
            continue
        corrida.grupos.append(avaliar_grupo(documento, era, payloads))
    return corrida


def _grupo_as_dict(g: GrupoResult) -> dict[str, Any]:
    return {
        "documento": g.documento,
        "era": g.era,
        "k": g.k,
        "pares": g.pares,
        "intersecao": g.intersecao,
        "uniao": g.uniao,
        "estabilidade_pct": g.estabilidade_pct,
        "valido": g.valido,
        "aplicavel": g.aplicavel,
        "cardinalidade_media": g.cardinalidade_media,
        "controles_que_moveram": list(g.controles_que_moveram),
        "pares_byte_identicos": g.pares_byte_identicos,
    }


def as_dict(corrida: Corrida) -> dict[str, Any]:
    return {
        "k_minimo": K_MINIMO,
        "documentos_minimo": DOCS_MINIMO,
        "documentos_medidos": corrida.documentos_medidos,
        "criterio_atendido": corrida.documentos_medidos >= DOCS_MINIMO,
        "grupos_excluidos_por_k": corrida.excluidos_por_k,
        "artefatos_ilegiveis": corrida.ilegiveis,
        "grupos": [_grupo_as_dict(g) for g in corrida.grupos],
    }


def _estado_do_grupo(g: GrupoResult) -> str:
    if g.controles_que_moveram:
        return f"CONTROLE MOVEU ({','.join(g.controles_que_moveram)}) — resultado inválido"
    if not g.aplicavel:
        return "SEM INVESTIMENTO — nada a medir (não é falha)"
    cache = f"  ⚠ {g.pares_byte_identicos} par(es) byte-idênticos" if g.pares_byte_identicos else ""
    return (
        f"{g.intersecao}/{g.uniao} = {g.estabilidade_pct}%  (~{g.cardinalidade_media} ids){cache}"
    )


def _rotulo(documento: str) -> str:
    """Só a `artifact_key` — o UUID do workspace comia a coluna e não distingue nada aqui."""
    return documento.rsplit("/", 1)[-1][:30]


def _linha_do_grupo(g: GrupoResult) -> str:
    return f"  {_rotulo(g.documento):30s} [{g.era:5s}] K={g.k:2d}  {_estado_do_grupo(g)}"


def _render(corrida: Corrida) -> None:
    print(f"estabilidade do `investment_id` — K>={K_MINIMO}, replay offline, zero token LLM\n")
    for g in corrida.grupos:
        print(_linha_do_grupo(g))
    validos = [g for g in corrida.grupos if g.valido]
    moveu = [g for g in corrida.grupos if g.controles_que_moveram]
    na = [g for g in corrida.grupos if not g.aplicavel and not g.controles_que_moveram]
    print(
        f"\ngrupos: {len(corrida.grupos)} — {len(validos)} medidos · "
        f"{len(moveu)} com controle movido · {len(na)} sem investimento · "
        f"documentos: {corrida.documentos_medidos} (mínimo {DOCS_MINIMO}) · "
        f"excluídos por K<{K_MINIMO}: {corrida.excluidos_por_k} · "
        f"ilegíveis: {corrida.ilegiveis}"
    )
    if corrida.documentos_medidos < DOCS_MINIMO:
        print("NÃO ATENDE o critério 6 — menos de 2 documentos com K suficiente.")


def _coletar() -> tuple[list[tuple[str, dict]], int]:
    from sqlalchemy import select

    from backend.app.core.database import SyncSessionLocal
    from backend.app.models.pipeline_artifact import PipelineArtifact
    from dev.certify_ledger_local import _decrypt

    artefatos: list[tuple[str, dict]] = []
    ilegiveis = 0
    with SyncSessionLocal() as sessao:
        stmt = select(PipelineArtifact).where(PipelineArtifact.stage == "E1.5a")
        for row in sessao.execute(stmt).scalars().all():
            try:
                artefatos.append(
                    (f"{row.workspace_id}/{row.artifact_key}", _decrypt(row.content_json))
                )
            except Exception:  # era antiga / chave rotacionada
                ilegiveis += 1
    return artefatos, ilegiveis


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    artefatos, ilegiveis = _coletar()
    corrida = medir(artefatos, ilegiveis=ilegiveis)
    if args.json:
        print(json.dumps(as_dict(corrida), indent=2, ensure_ascii=False))
    else:
        _render(corrida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
