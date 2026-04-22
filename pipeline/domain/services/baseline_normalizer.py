"""BaselineNormalizer — canoniza o baseline patrimonial (Sessão A4a).

Extrai ``normalize_baseline`` (``e4_categorize.py:418``) em domain service
puro. Mapeia as chaves do formato v2 do E1.5 (``membros_familia``,
``data_consolidacao``, ``resumo_patrimonial``, ``bens_imoveis_consolidados``,
``investimentos_financeiros_consolidados``, ``dividas_consolidados``) para o
schema canônico (v1) esperado pelo E5 e pelo schema JSON.

Responsabilidades:
- Adicionar ``pipeline_stage`` quando ausente.
- Resolver ``data_processamento`` (de ``data_consolidacao`` ou today).
- Alias ``membros`` ← ``membros_familia`` (só nomes, para compat de schema —
  **não** para ``_resolve_members`` do E5, que continua usando o formato
  consolidado).
- Derivar ``patrimonio_por_ano`` a partir de ``resumo_patrimonial``
  (chaves ``31_12_{ano}`` → ``{ano: {total_bens, total_dividas}}``).
- Enriquecer ``imoveis_consolidados`` com ``descricao`` (de ``endereco`` ou
  ``dados_completos.imovel``) + ``proprietario`` (a partir de
  ``proprietarios``).
- Converter ``investimentos_consolidados`` de dict
  (``{member_ano: {categoria: valor}}``) para lista.
- Alias ``dividas`` ← ``dividas_consolidados``.

Função **pura** — não muta o dict de entrada (retorna cópia).
Retorna tupla ``(data_normalizado, fixes_aplicados)`` para que o shell
decida como logar.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True)
class NormalizedBaseline:
    """Resultado de ``BaselineNormalizer.normalize``."""

    data: dict[str, Any]
    fixes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def was_normalized(self) -> bool:
        return len(self.fixes) > 0


class BaselineNormalizer:
    """Canoniza dict de baseline patrimonial.

    Stateless. Usa ``date_today`` injetável para testes determinísticos.
    """

    def __init__(self, *, date_today: date | None = None) -> None:
        self._today = date_today

    def _resolve_today(self) -> str:
        return (self._today or date.today()).isoformat()

    # -- API --

    def normalize(self, raw: dict | None) -> NormalizedBaseline:
        if not isinstance(raw, dict):
            return NormalizedBaseline(data={}, fixes=())

        data = copy.deepcopy(raw)
        fixes: list[str] = []

        # 1. pipeline_stage
        if "pipeline_stage" not in data:
            data["pipeline_stage"] = "E1.5_Baseline_Patrimonial"
            fixes.append("pipeline_stage added")

        # 2. data_processamento
        if "data_processamento" not in data:
            if "data_consolidacao" in data:
                data["data_processamento"] = str(data["data_consolidacao"])[:10]
                fixes.append("data_processamento ← data_consolidacao")
            else:
                data["data_processamento"] = self._resolve_today()
                fixes.append("data_processamento set to today")

        # 3. membros (nomes apenas) ← membros_familia
        if "membros" not in data and "membros_familia" in data:
            raw_list = data["membros_familia"]
            data["membros"] = [
                m.get("nome", m) if isinstance(m, dict) else m for m in (raw_list or [])
            ]
            fixes.append("membros ← membros_familia (names only, not for _resolve_members)")

        # 4. patrimonio_por_ano ← resumo_patrimonial
        if "patrimonio_por_ano" not in data and "resumo_patrimonial" in data:
            resumo = data["resumo_patrimonial"] or {}
            pat_ano: dict[str, dict[str, Any]] = {}
            for key, val in resumo.items():
                m = re.search(r"(\d{4})$", str(key))
                if m and isinstance(val, dict):
                    ano = m.group(1)
                    pat_ano[ano] = {
                        "total_bens": val.get("total", val.get("bens_imoveis", 0)),
                        "total_dividas": val.get("dividas", 0),
                    }
            if pat_ano:
                data["patrimonio_por_ano"] = pat_ano
                fixes.append(f"patrimonio_por_ano ← resumo_patrimonial ({len(pat_ano)} anos)")

        # 5. imoveis_consolidados ← bens_imoveis_consolidados (+ enriquecimento)
        if "imoveis_consolidados" not in data and "bens_imoveis_consolidados" in data:
            imoveis = list(data["bens_imoveis_consolidados"] or [])
            for im in imoveis:
                if not isinstance(im, dict):
                    continue
                if not im.get("descricao"):
                    dc = im.get("dados_completos")
                    desc = ""
                    if isinstance(dc, dict):
                        desc = dc.get("imovel", "") or ""
                    if not desc:
                        desc = im.get("endereco", "") or ""
                    im["descricao"] = desc
                if "proprietario" not in im and "proprietarios" in im:
                    props = im["proprietarios"]
                    im["proprietario"] = ", ".join(props) if isinstance(props, list) else str(props)
            data["imoveis_consolidados"] = imoveis
            fixes.append(
                f"imoveis_consolidados ← bens_imoveis_consolidados ({len(imoveis)} imóveis, descricao enriched)"
            )

        # 6. investimentos_consolidados ← investimentos_financeiros_consolidados
        if (
            "investimentos_consolidados" not in data
            and "investimentos_financeiros_consolidados" in data
        ):
            inv_raw = data["investimentos_financeiros_consolidados"]
            if isinstance(inv_raw, dict):
                inv_list: list[dict] = []
                for member_key, categories in inv_raw.items():
                    if not isinstance(categories, dict):
                        continue
                    prop = str(member_key).split("_")[0].title()
                    year = str(member_key).split("_")[-1]
                    for cat_name, cat_value in categories.items():
                        if cat_name in ("total",):
                            continue
                        inv_list.append(
                            {
                                "descricao": str(cat_name).replace("_", " ").title(),
                                "tipo": cat_name,
                                "proprietario": prop,
                                "valores_31_12": {year: cat_value},
                            }
                        )
                data["investimentos_consolidados"] = inv_list
                fixes.append(
                    f"investimentos_consolidados ← investimentos_financeiros_consolidados (dict→list, {len(inv_list)} entries)"
                )
            else:
                data["investimentos_consolidados"] = inv_raw
                fixes.append(
                    "investimentos_consolidados ← investimentos_financeiros_consolidados (list)"
                )

        # 7. dividas ← dividas_consolidados
        if "dividas" not in data and "dividas_consolidados" in data:
            data["dividas"] = data["dividas_consolidados"]
            fixes.append("dividas ← dividas_consolidados")

        return NormalizedBaseline(data=data, fixes=tuple(fixes))
