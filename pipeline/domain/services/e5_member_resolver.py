"""E5MemberResolver — resolve membros do baseline em 4 formatos (dict, lista, declarations[] IRPF, consolidado v1.5) num domain service puro (A5c)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pipeline.domain.services.patrimonio_types import resolve_value_year


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


# =============================================================================
# Config
# =============================================================================


@dataclass(frozen=True)
class MemberResolverConfig:
    """Chaves do titular/cônjuge (R9/ISP).

    Source no legado:
    - ``titular_key`` ← ``family_members.json::titular`` (default ``"david"``)
    - ``conjuge_key`` ← membro com ``papel == "conjuge"`` em
      ``family_members.json`` (vazio se não houver).
    """

    titular_key: str = "david"
    conjuge_key: str = ""

    @classmethod
    def from_family(cls, family: dict | None = None) -> "MemberResolverConfig":
        fam = family or {}
        titular = str(fam.get("titular", "david"))
        membros = fam.get("membros", {}) or {}
        conjuge = ""
        if isinstance(membros, dict):
            conjuge = next(
                (
                    k
                    for k, v in membros.items()
                    if isinstance(v, dict) and v.get("papel") == "conjuge"
                ),
                "",
            )
        return cls(titular_key=titular, conjuge_key=conjuge)


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class ResolvedMembers:
    """Titular + cônjuge já resolvidos do baseline."""

    titular_data: dict[str, Any] = field(default_factory=dict)
    conjuge_data: dict[str, Any] = field(default_factory=dict)
    titular_key: str = "david"
    conjuge_key: str = ""
    reference_year: str | None = None
    source_format: str = "unknown"  # "dict" | "list_dicts" | "declarations" | "consolidated"

    def as_tuple(self) -> tuple[dict, dict]:
        """Formato compatível com ``_resolve_members`` (tuple)."""
        return (dict(self.titular_data), dict(self.conjuge_data))


# =============================================================================
# Service
# =============================================================================


class E5MemberResolver:
    """Resolve membros do baseline em qualquer um dos 4 formatos."""

    def __init__(self, config: MemberResolverConfig | None = None) -> None:
        self._config = config or MemberResolverConfig()

    def resolve(self, baseline: dict[str, Any] | None) -> ResolvedMembers:
        if not isinstance(baseline, dict):
            return self._empty("unknown")

        cfg = self._config
        members = baseline.get("members", baseline.get("membros", {}))

        # Formato 2/3: lista.
        if isinstance(members, list):
            has_dicts = any(isinstance(m, dict) for m in members)
            if has_dicts:
                return self._from_list_of_dicts(members)
            # Lista de strings → tenta consolidado ou declarations.
            if baseline.get("imoveis_consolidados") is not None or baseline.get(
                "patrimonio_por_ano"
            ):
                return self._from_consolidated(baseline)
            if baseline.get("declarations"):
                return self._from_declarations(baseline)

        # Formato 1: dict com titular/conjuge como keys.
        if members and isinstance(members, dict):
            return ResolvedMembers(
                titular_data=dict(members.get(cfg.titular_key, {}) or {}),
                conjuge_data=dict(members.get(cfg.conjuge_key, {}) or {})
                if cfg.conjuge_key
                else {},
                titular_key=cfg.titular_key,
                conjuge_key=cfg.conjuge_key,
                source_format="dict",
            )

        # Formato 4: consolidado (sem members).
        return self._from_consolidated(baseline)

    # -- Helpers por formato --

    def _empty(self, source: str) -> ResolvedMembers:
        cfg = self._config
        return ResolvedMembers(
            titular_key=cfg.titular_key, conjuge_key=cfg.conjuge_key, source_format=source
        )

    def _from_list_of_dicts(self, members: list) -> ResolvedMembers:
        cfg = self._config
        titular_data: dict = {}
        conjuge_data: dict = {}
        for m in members:
            if not isinstance(m, dict):
                continue
            nome = str(m.get("nome", "")).lower()
            if cfg.titular_key and cfg.titular_key in nome:
                titular_data = m
            elif cfg.conjuge_key and cfg.conjuge_key in nome:
                conjuge_data = m
        return ResolvedMembers(
            titular_data=titular_data,
            conjuge_data=conjuge_data,
            titular_key=cfg.titular_key,
            conjuge_key=cfg.conjuge_key,
            source_format="list_dicts",
        )

    def _from_declarations(self, baseline: dict) -> ResolvedMembers:
        cfg = self._config
        declarations = baseline.get("declarations", []) or []

        # Agrupa por membro, mantém a declaração mais recente.
        member_decls: dict[str, dict] = {}
        for decl in declarations:
            if not isinstance(decl, dict):
                continue
            membro = str(decl.get("membro", "")).lower()
            if not membro:
                declarante = decl.get("declarante", {})
                if isinstance(declarante, dict):
                    membro = str(declarante.get("nome", "")).lower()
            ano = _safe_float(decl.get("ano_base", 0))
            if not ano:
                src = decl.get("source_file", "")
                if isinstance(src, str):
                    m = re.search(r"(\d{4})", src.split("/")[-1] if "/" in src else src)
                    if m:
                        ano = float(m.group(1))
            key = (
                cfg.titular_key
                if cfg.titular_key and cfg.titular_key in membro
                else cfg.conjuge_key
                if cfg.conjuge_key and cfg.conjuge_key in membro
                else None
            )
            if key is None:
                continue
            existing = member_decls.get(key)
            if existing is None or ano > _safe_float(existing.get("ano_base", 0)):
                member_decls[key] = decl

        def _classify_bens(bens_direitos: list) -> dict:
            imoveis: list = []
            veiculos: list = []
            investimentos: list = []
            contas: list = []
            for bem in bens_direitos or []:
                if not isinstance(bem, dict):
                    continue
                raw = str(bem.get("grupo", "")).strip().upper()
                if raw.startswith("G"):
                    raw = raw[1:]
                grupo = raw.zfill(2)
                valor = _safe_float(bem.get("situacao_atual", bem.get("valor_31_12_atual", 0)))
                entry = {
                    "descricao": bem.get("descricao", ""),
                    "valor_31_12_ano_base": valor,
                }
                if bem.get("instituicao"):  # DE-01: preserva instituição estruturada
                    entry["instituicao"] = bem["instituicao"]
                if grupo == "01":
                    imoveis.append(entry)
                elif grupo == "02":
                    veiculos.append(entry)
                elif grupo == "06":
                    contas.append(entry)
                else:  # 03, 04, 07, 99 e desconhecidos.
                    investimentos.append(entry)
            return {
                "imoveis": imoveis,
                "veiculos": veiculos,
                "investimentos": investimentos,
                "contas_bancarias": contas,
            }

        results: dict[str, dict] = {}
        for key in (cfg.titular_key, cfg.conjuge_key):
            if not key:
                continue
            decl = member_decls.get(key)
            if not decl:
                results[key] = {}
                continue
            bens = _classify_bens(decl.get("bens_direitos", []))
            total_bens_decl = _safe_float(decl.get("total_bens", 0))
            total_dividas = 0.0
            for dv in baseline.get("dividas", []) or []:
                if not isinstance(dv, dict):
                    continue
                prop_lower = str(dv.get("proprietario", "")).lower()
                if key in prop_lower:
                    total_dividas += _safe_float(dv.get("saldo_31_12", 0))
            synthetic = sum(
                _safe_float(b.get("valor_31_12_ano_base", 0)) for cat in bens.values() for b in cat
            )
            results[key] = {
                "total_bens": total_bens_decl if total_bens_decl > 0 else synthetic,
                "total_dividas": total_dividas,
                "bens": bens,
            }

        return ResolvedMembers(
            titular_data=results.get(cfg.titular_key, {}),
            conjuge_data=results.get(cfg.conjuge_key, {}) if cfg.conjuge_key else {},
            titular_key=cfg.titular_key,
            conjuge_key=cfg.conjuge_key,
            source_format="declarations",
        )

    def _from_consolidated(self, baseline: dict) -> ResolvedMembers:
        """Formato v1.5 consolidado — titular recebe tudo menos o que for
        exclusivo do cônjuge.
        """
        cfg = self._config
        ano_ref, total_bens, total_dividas_summary = self._resolve_ano_ref_and_totals(baseline)

        # Imóveis.
        imoveis_list = baseline.get(
            "imoveis_consolidados", baseline.get("bens_imoveis_consolidados", [])
        )
        titular_imoveis, conjuge_imoveis = self._split_by_conjuge(
            imoveis_list,
            ano_ref,
            enrich_descricao=True,
        )

        # Investimentos — pode ser lista ou dict v2.
        inv_raw = baseline.get(
            "investimentos_consolidados",
            baseline.get("investimentos_financeiros_consolidados", {}),
        )
        titular_inv, conjuge_inv = self._split_investimentos(inv_raw, ano_ref)

        # Veículos.
        titular_veiculos, conjuge_veiculos = self._split_by_conjuge(
            baseline.get("veiculos_consolidados", []), ano_ref
        )

        # Dívidas.
        titular_dividas, conjuge_dividas = self._split_dividas(
            baseline.get("dividas", baseline.get("dividas_consolidadas", [])),
            ano_ref,
        )

        titular_bens_total = self._sum_bens_val(titular_imoveis, titular_inv, titular_veiculos)
        conjuge_bens_total = self._sum_bens_val(conjuge_imoveis, conjuge_inv, conjuge_veiculos)

        titular_data = {
            "total_bens": titular_bens_total,
            "total_dividas": titular_dividas,
            "bens": {
                "imoveis": titular_imoveis,
                "investimentos": titular_inv,
                "veiculos": titular_veiculos,
                "contas_bancarias": [],
            },
        }
        conjuge_data = {
            "total_bens": conjuge_bens_total,
            "total_dividas": conjuge_dividas,
            "bens": {
                "imoveis": conjuge_imoveis,
                "investimentos": conjuge_inv,
                "veiculos": conjuge_veiculos,
                "contas_bancarias": [],
            },
        }

        # Ajuste: se synthetic total diverge do summary, distribui diff no titular
        # (paridade com linha 634-639).
        synthetic_total = titular_bens_total + conjuge_bens_total
        if total_bens > 0 and abs(synthetic_total - total_bens) > 1.0:
            diff = total_bens - synthetic_total
            titular_data["total_bens"] = titular_data["total_bens"] + diff

        return ResolvedMembers(
            titular_data=titular_data,
            conjuge_data=conjuge_data,
            titular_key=cfg.titular_key,
            conjuge_key=cfg.conjuge_key,
            reference_year=ano_ref,
            source_format="consolidated",
        )

    def _resolve_ano_ref_and_totals(self, baseline: dict) -> tuple[str, float, float]:
        """``(value_year ano-base, total_bens, total_dividas do resumo)`` (ADR-274)."""
        summary_year, total_bens, total_dividas = self._resolve_summary_year(baseline)
        value_year = resolve_value_year(baseline, summary_year)
        return value_year, total_bens, total_dividas

    @staticmethod
    def _resolve_summary_year(baseline: dict) -> tuple[str, float, float]:
        pat_ano = baseline.get("patrimonio_por_ano", {}) or {}
        if pat_ano:
            anos = sorted(pat_ano.keys())
            ano_ref = anos[-1] if anos else str(date.today().year - 1)
            ano_data = pat_ano.get(ano_ref, {}) or {}
            total_bens = _safe_float(ano_data.get("total_bens", 0))
            total_dividas = _safe_float(ano_data.get("total_dividas", 0))
            return ano_ref, total_bens, total_dividas

        resumo = baseline.get("resumo_patrimonial", {}) or {}
        calculo = (
            baseline.get("cálculo_patrimonio_liquido")
            or baseline.get("calculo_patrimonio_liquido")
            or {}
        )
        ano_ref = str(date.today().year - 1)
        for key in sorted(resumo.keys()):
            m = re.search(r"(\d{4})$", key)
            if m and not str(key).startswith("variacao_"):
                ano_ref = m.group(1)

        resumo_key = f"31_12_{ano_ref}"
        total_bens = _safe_float(resumo.get(resumo_key, {}).get("total", 0))
        if not total_bens and calculo:
            total_bens = _safe_float((calculo.get(ano_ref, {}) or {}).get("ativo_total", 0))
        total_dividas = _safe_float((calculo.get(ano_ref, {}) or {}).get("passivo_total", 0))
        return ano_ref, total_bens, total_dividas

    @staticmethod
    def _resolve_valor(item: dict, ano: str) -> float:
        vals_dict = item.get("valores_31_12") if isinstance(item, dict) else None
        if isinstance(vals_dict, dict):
            v = vals_dict.get(ano, vals_dict.get(f"31_12_{ano}"))
            if v is not None:
                return _safe_float(v)
        v = item.get(f"valor_{ano}") if isinstance(item, dict) else None
        if v is not None:
            return _safe_float(v)
        return _safe_float(item.get("valor", 0))

    def _is_conjuge_exclusive(self, item: dict) -> bool:
        cfg = self._config
        prop = item.get("proprietario", "")
        if (
            isinstance(prop, str)
            and cfg.conjuge_key
            and cfg.conjuge_key in prop.lower()
            and cfg.titular_key not in prop.lower()
        ):
            return True
        props = item.get("proprietarios", [])
        if isinstance(props, list):
            names_lower = [str(p).lower() for p in props]
            if (
                cfg.conjuge_key
                and cfg.conjuge_key in names_lower
                and cfg.titular_key not in names_lower
            ):
                return True
        return False

    def _split_by_conjuge(
        self,
        items: list,
        ano_ref: str,
        *,
        enrich_descricao: bool = False,
    ) -> tuple[list, list]:
        titular, conjuge = [], []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            val = self._resolve_valor(item, ano_ref)
            descricao = item.get("descricao", "")
            if enrich_descricao and not descricao:
                dc = item.get("dados_completos", {})
                descricao = (
                    (dc.get("imovel", "") if isinstance(dc, dict) else "")
                    or item.get("endereco", "")
                    or ""
                )
            entry: dict = {"descricao": descricao, "valor_31_12_ano_base": val}
            # DE-01: preserva a instituição estruturada da fonte (IRPF/baseline);
            # sem isso o top_ativos/instituicoes_por_membro chega vazio ao narrador.
            if item.get("instituicao"):
                entry["instituicao"] = item["instituicao"]
            if enrich_descricao:
                entry["endereco"] = item.get("endereco", "")
                entry["tipo"] = item.get("tipo", "")
                # ADR-215 P3: propaga property_id do baseline E1.5c para
                # `_split_imoveis` poder casar override.
                if item.get("property_id"):
                    entry["property_id"] = item["property_id"]
            if self._is_conjuge_exclusive(item):
                conjuge.append(entry)
            else:
                titular.append(entry)
        return titular, conjuge

    def _split_investimentos(self, inv_raw, ano_ref: str) -> tuple[list, list]:
        cfg = self._config
        titular, conjuge = [], []
        if isinstance(inv_raw, list):
            return self._split_by_conjuge(inv_raw, ano_ref)
        if isinstance(inv_raw, dict):
            for member_key, categories in inv_raw.items():
                if not isinstance(categories, dict):
                    continue
                member_lower = str(member_key).lower()
                is_conjuge = bool(cfg.conjuge_key and cfg.conjuge_key in member_lower)
                for cat_name, cat_value in categories.items():
                    if cat_name == "total":
                        continue
                    val = _safe_float(cat_value)
                    if val == 0:
                        continue
                    entry = {
                        "descricao": str(cat_name).replace("_", " ").title(),
                        "tipo": cat_name,
                        "valor_31_12_ano_base": val,
                    }
                    if is_conjuge:
                        conjuge.append(entry)
                    else:
                        titular.append(entry)
        return titular, conjuge

    def _split_dividas(self, dividas_list: list, ano_ref: str) -> tuple[float, float]:
        cfg = self._config
        titular_dividas = 0.0
        conjuge_dividas = 0.0
        for dv in dividas_list or []:
            if not isinstance(dv, dict):
                continue
            saldo = dv.get("saldo_31_12", {})
            if isinstance(saldo, dict):
                val = _safe_float(saldo.get(ano_ref, 0))
            else:
                val = self._resolve_valor(dv, ano_ref)
            prop = str(dv.get("proprietario", "")).lower()
            if cfg.conjuge_key and cfg.conjuge_key in prop and cfg.titular_key not in prop:
                conjuge_dividas += val
            else:
                titular_dividas += val
        return titular_dividas, conjuge_dividas

    @staticmethod
    def _sum_bens_val(*lists) -> float:
        total = 0.0
        for items in lists:
            for item in items or []:
                total += _safe_float(item.get("valor_31_12_ano_base", 0))
        return total
