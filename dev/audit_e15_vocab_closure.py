#!/usr/bin/env python3
r"""Passo 0 da [[A42.l15]] — fecho do vocabulário do E1.5, read-only e sem token de LLM.

Mede, sobre TODOS os artefatos ``E1.5a`` existentes, quanto do vocabulário que a
chave de identidade consome já é fechado: ``codigo`` contra ``^\d{2}$`` e
``instituicao`` contra o ``institution_catalog`` (ADR-137).

**Fecho não é estabilidade.** Um extrator pode ser 100% fechado e ainda alternar
entre dois codes do catálogo entre runs — o que esta medição responde é se há
vocabulário a fechar, não se fechá-lo estabiliza. A estabilidade run-a-run exige
dois runs completos, é gameável por cache e não roda em CI (A42.l15 §Armadilha D).

Uso:
  python3 dev/audit_e15_vocab_closure.py
  python3 dev/audit_e15_vocab_closure.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CODIGO_CANONICO = re.compile(r"^\d{2}$")
CODIGO_COMPOSTO = re.compile(r"^\d{2}-\d{2}$")

# DUAS populações, e misturá-las falseia o número: `E1.5a` é a extração
# POR DOCUMENTO, e `E1.5`/`extract_baseline` são o agregado consolidado, que
# **re-emite os mesmos itens**. Somar as duas conta cada item duas vezes e ainda
# dilui a taxa da extração com a do agregado (medido em 2026-08-30: 1,86% na
# extração contra 0,84% no agregado; a soma dava 1,5% e não descrevia nenhuma
# das duas). O headline é sempre a EXTRAÇÃO; o agregado sai ao lado, nomeado.
E15_EXTRACAO = "E1.5a"
E15_AGREGADO = ("E1.5", "extract_baseline")
E15_STAGES = (E15_EXTRACAO, *E15_AGREGADO)


@dataclass
class Closure:
    """Contagens do fecho — numerador e denominador, nunca só o percentual."""

    itens: int = 0
    codigo: Counter = field(default_factory=Counter)
    instituicao_ausente: int = 0
    instituicao_no_catalogo: int = 0
    instituicao_fora: int = 0
    fora_por_forma: Counter = field(default_factory=Counter)

    @property
    def instituicao_avaliadas(self) -> int:
        return self.instituicao_no_catalogo + self.instituicao_fora


def classify_codigo(raw: Any) -> str:
    """``canonico`` (``^\\d{2}$``) · ``composto`` (``grupo-codigo``) · ``ausente`` · ``outra``."""
    texto = str(raw or "").strip()
    if not texto:
        return "ausente"
    if CODIGO_CANONICO.match(texto):
        return "canonico"
    if CODIGO_COMPOSTO.match(texto):
        return "composto"
    return "outra"


def normalize_token(raw: Any) -> str:
    """Forma dos codes do catálogo: lowercase sem acento, só ``[a-z0-9]`` (ADR-137)."""
    from pipeline.domain.services.seguradora_resolver import normalize_seguradora_code

    return normalize_seguradora_code(str(raw or ""))


def catalog_tokens(catalog: dict[str, str]) -> set[str]:
    """Codes E nomes de exibição, ambos normalizados — o LLM emite as duas formas."""
    return {normalize_token(code) for code in catalog} | {
        normalize_token(nome) for nome in catalog.values()
    }


def tally(itens: Iterable[dict], tokens: set[str], into: Closure) -> None:
    """Acumula um artefato em ``into``. Mutação explícita: o chamador é dono do agregado."""
    for item in itens:
        into.itens += 1
        into.codigo[classify_codigo(item.get("codigo"))] += 1
        _tally_instituicao(item.get("instituicao"), tokens, into)


def _tally_instituicao(raw: Any, tokens: set[str], into: Closure) -> None:
    bruto = str(raw or "").strip()
    if not bruto:
        into.instituicao_ausente += 1
        return
    if normalize_token(bruto) in tokens:
        into.instituicao_no_catalogo += 1
        return
    into.instituicao_fora += 1
    into.fora_por_forma[bruto[:48]] += 1


def _pct(num: int, den: int) -> float:
    return round(100.0 * num / den, 2) if den else 0.0


def _ratio(num: int, den: int) -> dict[str, float | int]:
    """Numerador E denominador ao lado do percentual — percentual sozinho não é auditável."""
    return {"num": num, "den": den, "pct": _pct(num, den)}


def as_dict(closure: Closure, artefatos: int, ilegiveis: int, catalogo: int) -> dict:
    """Numerador e denominador explícitos — percentual sozinho não é auditável."""
    fora_codigo = closure.itens - closure.codigo["canonico"]
    return {
        "artefatos_e15a": artefatos,
        "artefatos_ilegiveis": ilegiveis,
        "itens": closure.itens,
        "catalogo_codes": catalogo,
        "codigo": dict(closure.codigo),
        "codigo_fora_do_canonico": _ratio(fora_codigo, closure.itens),
        "instituicao_ausente": closure.instituicao_ausente,
        "instituicao_fora_do_catalogo": _ratio(
            closure.instituicao_fora, closure.instituicao_avaliadas
        ),
        "formas_fora_mais_frequentes": closure.fora_por_forma.most_common(15),
    }


def report(por_stage: dict[str, Closure], artefatos: int, ilegiveis: int, catalogo: int) -> dict:
    """Headline = extração; agregado ao lado, NUNCA somado (ver ``E15_EXTRACAO``)."""
    extracao = por_stage.get(E15_EXTRACAO, Closure())
    return {
        "populacao_headline": E15_EXTRACAO,
        "artefatos_total": artefatos,
        "artefatos_ilegiveis": ilegiveis,
        "catalogo_codes": catalogo,
        "extracao": as_dict(extracao, artefatos, ilegiveis, catalogo),
        "agregado_nao_somar": {
            stage: as_dict(c, artefatos, ilegiveis, catalogo)
            for stage, c in sorted(por_stage.items())
            if stage != E15_EXTRACAO
        },
    }


def _e15_rows(session) -> list:
    from sqlalchemy import select

    from backend.app.models.pipeline_artifact import PipelineArtifact

    stmt = select(PipelineArtifact).where(PipelineArtifact.stage.in_(E15_STAGES))
    return list(session.execute(stmt).scalars().all())


def _accumulate(rows: list, tokens: set[str]) -> tuple[dict[str, Closure], int]:
    """``(por_stage, ilegiveis)``. Artefato que não decifra é CONTADO, nunca omitido."""
    from dev.certify_ledger_local import _decrypt

    por_stage: dict[str, Closure] = {}
    ilegiveis = 0
    for row in rows:
        try:
            payload = _decrypt(row.content_json)
        except Exception:  # era antiga / chave rotacionada
            ilegiveis += 1
            continue
        alvo = por_stage.setdefault(str(row.stage), Closure())
        tally(payload.get("itens") or [], tokens, alvo)
    return por_stage, ilegiveis


def _collect() -> tuple[dict[str, Closure], int, int, int]:
    from backend.app.core.database import SyncSessionLocal
    from backend.app.services.institution_catalog_provider import DBInstitutionCatalogProvider
    from pipeline.llm.institution_catalog import institution_code_map

    with SyncSessionLocal() as session:
        catalogo = institution_code_map(DBInstitutionCatalogProvider(session=session))
        rows = _e15_rows(session)
        por_stage, ilegiveis = _accumulate(rows, catalog_tokens(catalogo))
    return por_stage, len(rows), ilegiveis, len(catalogo)


def _render_bloco(rotulo: str, data: dict) -> None:
    fc, fi = data["codigo_fora_do_canonico"], data["instituicao_fora_do_catalogo"]
    formas = " · ".join(f"{k}={v}" for k, v in sorted(data["codigo"].items()))
    print(f"  [{rotulo}] itens={data['itens']}  ({formas})")
    print(f"      codigo fora de ^\\d{{2}}$ : {fc['num']}/{fc['den']} = {fc['pct']}%")
    print(
        f"      instituicao fora do cat.: {fi['num']}/{fi['den']} = {fi['pct']}%"
        f"  (ausente em {data['instituicao_ausente']})"
    )


def _render(data: dict) -> None:
    print(
        f"artefatos: {data['artefatos_total']} · ilegíveis: {data['artefatos_ilegiveis']}"
        f" · catálogo: {data['catalogo_codes']} codes\n"
    )
    print(f"=== EXTRAÇÃO ({data['populacao_headline']}) — é este o número ===")
    _render_bloco(data["populacao_headline"], data["extracao"])
    if data["agregado_nao_somar"]:
        print("\n=== agregado consolidado — RE-EMITE os mesmos itens, não somar ===")
        for stage, bloco in data["agregado_nao_somar"].items():
            _render_bloco(stage, bloco)
    print("\n  formas fora do catálogo mais frequentes (extração):")
    for nome, n in data["extracao"]["formas_fora_mais_frequentes"]:
        print(f"    {n:5}x  {nome}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    por_stage, artefatos, ilegiveis, catalogo = _collect()
    data = report(por_stage, artefatos, ilegiveis, catalogo)
    print(json.dumps(data, ensure_ascii=False, indent=2)) if args.json else _render(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
