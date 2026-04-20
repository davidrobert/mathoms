"""Resolvers de membros/baseline para ``PatrimonioCalculator`` (A6d.3.3 — ADR-100).

Port puro (sem globals, sem I/O, sem prints) dos helpers legados:

- ``_resolve_members`` → :func:`resolve_members`
- ``_build_members_from_declarations`` → :func:`build_members_from_declarations`
- ``_build_members_from_consolidated`` → :func:`build_members_from_consolidated`

Cada função recebe :class:`MemberIdentity` como parâmetro explícito e retorna
uma tupla ``(titular_data, conjuge_data)`` no shape que ``analyze_patrimonio``
consome. Zero dependência de globals ``_TITULAR_KEY``/``_CONJUGE_KEY`` etc.

Quatro formatos de baseline suportados (ordem de precedência em :func:`resolve_members`):

1. **Dict format** — ``{"members": {"david": {...}, "mariana": {...}}}``
2. **List-of-dicts** — ``{"membros": [{"nome": "david", ...}, ...]}``
3. **E1.5 declarations** — ``{"declarations": [...]}`` (IRPF bens_direitos por grupo)
4. **v1.5 consolidated** — top-level ``imoveis_consolidados`` / ``investimentos_consolidados``
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from pipeline.domain.services.patrimonio_types import (
    MemberIdentity,
    safe_float,
)


# =============================================================================
# resolve_members — dispatcher de 4 formatos
# =============================================================================


def resolve_members(
    baseline: dict, identity: MemberIdentity
) -> tuple[dict, dict]:
    """Resolve dicts de titular e cônjuge de qualquer baseline suportado.

    Retorna tupla ``(titular_data, conjuge_data)``. Se o formato não casar
    com nenhum resolver, tenta o path consolidated (mais tolerante).
    """
    members = baseline.get("members", baseline.get("membros", {}))

    if isinstance(members, list):
        has_dicts = any(isinstance(m, dict) for m in members)
        if has_dicts:
            titular_data, conjuge_data = {}, {}
            for m in members:
                if not isinstance(m, dict):
                    continue
                nome = m.get("nome", "").lower()
                if identity.titular_key in nome:
                    titular_data = m
                elif identity.conjuge_key and identity.conjuge_key in nome:
                    conjuge_data = m
            return titular_data, conjuge_data

        # Lista de strings → formato E1.5 declarations ou consolidated
        if (
            baseline.get("imoveis_consolidados") is not None
            or baseline.get("patrimonio_por_ano")
        ):
            return build_members_from_consolidated(baseline, identity)
        if baseline.get("declarations"):
            return build_members_from_declarations(baseline, identity)

    if members and isinstance(members, dict):
        return (
            members.get(identity.titular_key, {}),
            members.get(identity.conjuge_key, {}) if identity.conjuge_key else {},
        )

    # Fallback: v1.5 consolidated sem chave "members"
    return build_members_from_consolidated(baseline, identity)


# =============================================================================
# build_members_from_declarations — IRPF bens_direitos por grupo
# =============================================================================


_GRUPOS_IMOVEIS = "01"
_GRUPOS_VEICULOS = "02"
_GRUPOS_INVESTIMENTOS = frozenset({"03", "04", "07", "99"})
_GRUPO_CONTAS = "06"


def _classify_bens_by_grupo(bens_direitos: list) -> dict:
    """Classifica ``bens_direitos`` por grupo IRPF em 4 categorias.

    Normaliza ``grupo``: ``"G01"`` / ``"1"`` / ``1`` → ``"01"``.

    Mapeamento:
        - G01 → imoveis
        - G02 → veiculos
        - G03/G04/G07/G99 → investimentos (Ações, RF, Fundos, Outros)
        - G06 → contas_bancarias (Depósitos/moeda estrangeira)
        - Outros → investimentos (fallback conservador)
    """
    imoveis: list[dict] = []
    veiculos: list[dict] = []
    investimentos: list[dict] = []
    contas_bancarias: list[dict] = []

    for bem in bens_direitos:
        raw_grupo = str(bem.get("grupo", "")).strip().upper()
        if raw_grupo.startswith("G"):
            raw_grupo = raw_grupo[1:]
        grupo = raw_grupo.zfill(2)

        valor = safe_float(
            bem.get("situacao_atual", bem.get("valor_31_12_atual", 0))
        )
        descricao = bem.get("descricao", "")
        entry = {"descricao": descricao, "valor_31_12_ano_base": valor}

        if grupo == _GRUPOS_IMOVEIS:
            imoveis.append(entry)
        elif grupo == _GRUPOS_VEICULOS:
            veiculos.append(entry)
        elif grupo in _GRUPOS_INVESTIMENTOS:
            investimentos.append(entry)
        elif grupo == _GRUPO_CONTAS:
            contas_bancarias.append(entry)
        else:
            investimentos.append(entry)

    return {
        "imoveis": imoveis,
        "veiculos": veiculos,
        "investimentos": investimentos,
        "contas_bancarias": contas_bancarias,
    }


def _extract_membro_key(decl: dict, identity: MemberIdentity) -> str | None:
    """Extrai chave (titular/conjuge) de uma declaração E1.5.

    Aceita ``declaration["membro"]`` (formato E1.5 direto) ou
    ``declaration["declarante"]["nome"]`` (formato IRPF bruto).
    """
    membro = decl.get("membro", "")
    if not membro:
        declarante = decl.get("declarante", {})
        if isinstance(declarante, dict):
            membro = declarante.get("nome", "")
    membro = membro.lower()

    if identity.titular_key and identity.titular_key in membro:
        return identity.titular_key
    if identity.conjuge_key and identity.conjuge_key in membro:
        return identity.conjuge_key
    return None


def _infer_ano_base(decl: dict) -> int:
    """Infere ``ano_base`` de uma declaração, com fallback ao nome do arquivo."""
    ano = decl.get("ano_base", 0)
    if ano:
        return int(ano)
    src = decl.get("source_file", "")
    if isinstance(src, str):
        tail = src.split("/")[-1] if "/" in src else src
        match = re.search(r"(\d{4})", tail)
        if match:
            return int(match.group(1))
    return 0


def build_members_from_declarations(
    baseline: dict, identity: MemberIdentity
) -> tuple[dict, dict]:
    """Constrói titular/cônjuge a partir de ``declarations`` E1.5 (IRPF).

    Por membro, escolhe a declaração mais recente (maior ``ano_base``),
    classifica os bens por grupo IRPF, soma dívidas atribuídas via
    ``baseline.dividas[].proprietario``.

    Retorna ``({}, {})`` se ``declarations`` estiver ausente ou vazio.
    """
    declarations = baseline.get("declarations", [])
    if not declarations:
        return {}, {}

    # Seleciona 1 declaração por membro (a mais recente)
    member_decls: dict[str, dict] = {}
    for decl in declarations:
        key = _extract_membro_key(decl, identity)
        if key is None:
            continue
        ano = _infer_ano_base(decl)
        # Completa ano_base no decl para referência futura
        if not decl.get("ano_base") and ano:
            decl = {**decl, "ano_base": ano}
        if key not in member_decls or ano > member_decls[key].get("ano_base", 0):
            member_decls[key] = decl

    dividas_list = baseline.get("dividas", []) or []

    def _total_dividas_for(key: str) -> float:
        total = 0.0
        for dv in dividas_list:
            prop = (dv.get("proprietario", "") or "").lower()
            if key == identity.titular_key and identity.titular_key in prop:
                total += safe_float(dv.get("saldo_31_12", 0))
            elif (
                key == identity.conjuge_key
                and identity.conjuge_key
                and identity.conjuge_key in prop
            ):
                total += safe_float(dv.get("saldo_31_12", 0))
        return total

    results: dict[str, dict] = {}
    for key in (identity.titular_key, identity.conjuge_key):
        if not key:
            continue
        decl = member_decls.get(key)
        if not decl:
            results[key] = {}
            continue

        bens = _classify_bens_by_grupo(decl.get("bens_direitos", []))
        total_bens_decl = safe_float(decl.get("total_bens", 0))
        total_dividas = _total_dividas_for(key)

        synthetic_total = sum(
            safe_float(b.get("valor_31_12_ano_base", 0))
            for cat in bens.values()
            for b in cat
        )
        # Usa o total declarado como autoridade se > 0; senão fica com o synthetic.
        authoritative = total_bens_decl if total_bens_decl > 0 else synthetic_total

        results[key] = {
            "total_bens": authoritative,
            "total_dividas": total_dividas,
            "bens": bens,
        }

    return (
        results.get(identity.titular_key, {}),
        results.get(identity.conjuge_key, {}) if identity.conjuge_key else {},
    )


# =============================================================================
# build_members_from_consolidated — formato v1.5 top-level
# =============================================================================


def _resolve_ano_ref(baseline: dict) -> tuple[str, float, float]:
    """Determina ``ano_ref``, ``total_bens`` e ``total_dividas`` do baseline.

    Tenta o formato **original** (``patrimonio_por_ano``) antes do **E1.5 v2**
    (``resumo_patrimonial`` / ``cálculo_patrimonio_liquido``).

    Sempre retorna string de 4 dígitos para ``ano_ref`` (default: ano anterior).
    """
    pat_ano = baseline.get("patrimonio_por_ano", {}) or {}
    if pat_ano:
        anos = sorted(pat_ano.keys())
        ano_ref = anos[-1] if anos else str(date.today().year - 1)
        ano_data = pat_ano.get(ano_ref, {}) or {}
        return (
            ano_ref,
            safe_float(ano_data.get("total_bens", 0)),
            safe_float(ano_data.get("total_dividas", 0)),
        )

    # Formato E1.5 v2
    resumo = baseline.get("resumo_patrimonial", {}) or {}
    calculo = baseline.get(
        "cálculo_patrimonio_liquido",
        baseline.get("calculo_patrimonio_liquido", {}),
    ) or {}

    ano_ref = str(date.today().year - 1)
    for key in sorted(resumo.keys()):
        match = re.search(r"(\d{4})$", key)
        if match and not key.startswith("variacao_"):
            ano_ref = match.group(1)

    resumo_key = f"31_12_{ano_ref}"
    total_bens = safe_float(resumo.get(resumo_key, {}).get("total", 0))
    if not total_bens and calculo:
        total_bens = safe_float(calculo.get(ano_ref, {}).get("ativo_total", 0))
    total_dividas = safe_float(calculo.get(ano_ref, {}).get("passivo_total", 0))
    return ano_ref, total_bens, total_dividas


def _resolve_item_valor(item: dict, ano_ref: str) -> float:
    """Resolve valor de item consolidated tentando 3 conveções.

    Ordem: ``valores_31_12.{ano}`` / ``valores_31_12.31_12_{ano}`` →
    ``valor_{ano}`` → ``valor``.
    """
    vals_dict = item.get("valores_31_12", {})
    if isinstance(vals_dict, dict):
        v = vals_dict.get(ano_ref, vals_dict.get(f"31_12_{ano_ref}"))
        if v is not None:
            return safe_float(v)
    v = item.get(f"valor_{ano_ref}")
    if v is not None:
        return safe_float(v)
    return safe_float(item.get("valor", 0))


def _is_conjuge_exclusive(item: dict, identity: MemberIdentity) -> bool:
    """Confere se item pertence **exclusivamente** ao cônjuge.

    Aceita string ``proprietario`` ou lista ``proprietarios``. "Exclusivo"
    significa que o titular **não** aparece, e o cônjuge **aparece**.
    """
    if not identity.conjuge_key:
        return False

    prop = item.get("proprietario", "")
    if isinstance(prop, str):
        p_lower = prop.lower()
        if identity.conjuge_key in p_lower and identity.titular_key not in p_lower:
            return True

    props = item.get("proprietarios", [])
    if isinstance(props, list):
        names_lower = [p.lower() for p in props if isinstance(p, str)]
        if (
            identity.conjuge_key in names_lower
            and identity.titular_key not in names_lower
        ):
            return True

    return False


def _imovel_entry_from_consolidated(item: dict, ano_ref: str) -> dict:
    """Monta entry de imóvel consolidated preservando descrição rica."""
    descricao = item.get("descricao", "")
    if not descricao:
        dc = item.get("dados_completos", {})
        if isinstance(dc, dict):
            descricao = dc.get("imovel", "")
        if not descricao:
            descricao = item.get("endereco", "")
    return {
        "descricao": descricao or "",
        "endereco": item.get("endereco", ""),
        "tipo": item.get("tipo", ""),
        "valor_31_12_ano_base": _resolve_item_valor(item, ano_ref),
    }


def _split_imoveis(
    baseline: dict, identity: MemberIdentity, ano_ref: str
) -> tuple[list, list]:
    """Divide imóveis consolidados entre titular e cônjuge."""
    imoveis_list = baseline.get(
        "imoveis_consolidados", baseline.get("bens_imoveis_consolidados", [])
    ) or []
    titular_imoveis: list[dict] = []
    conjuge_imoveis: list[dict] = []
    for im in imoveis_list:
        entry = _imovel_entry_from_consolidated(im, ano_ref)
        if _is_conjuge_exclusive(im, identity):
            conjuge_imoveis.append(entry)
        else:
            titular_imoveis.append(entry)
    return titular_imoveis, conjuge_imoveis


def _split_investimentos(
    baseline: dict, identity: MemberIdentity, ano_ref: str
) -> tuple[list, list]:
    """Divide investimentos consolidated entre titular e cônjuge.

    Aceita dois formatos:
        - **list** — itens individuais com ``proprietario``/``proprietarios``.
        - **dict** — ``{"<membro>_<ano>": {"<categoria>": <valor>, ...}}``
          (E1.5 v2 agregado por categoria).
    """
    inv_raw = baseline.get(
        "investimentos_consolidados",
        baseline.get("investimentos_financeiros_consolidados", {}),
    )
    titular_inv: list[dict] = []
    conjuge_inv: list[dict] = []

    if isinstance(inv_raw, list):
        for inv in inv_raw:
            entry = {
                "descricao": inv.get("descricao", ""),
                "tipo": inv.get("tipo", ""),
                "valor_31_12_ano_base": _resolve_item_valor(inv, ano_ref),
            }
            if _is_conjuge_exclusive(inv, identity):
                conjuge_inv.append(entry)
            else:
                titular_inv.append(entry)

    elif isinstance(inv_raw, dict):
        for member_key, categories in inv_raw.items():
            if not isinstance(categories, dict):
                continue
            is_conjuge = (
                identity.conjuge_key
                and identity.conjuge_key in member_key.lower()
            )
            target = conjuge_inv if is_conjuge else titular_inv
            for cat_name, cat_value in categories.items():
                if cat_name == "total":
                    continue
                val = safe_float(cat_value)
                if val == 0:
                    continue
                target.append({
                    "descricao": cat_name.replace("_", " ").title(),
                    "tipo": cat_name,
                    "valor_31_12_ano_base": val,
                })

    return titular_inv, conjuge_inv


def _split_veiculos(
    baseline: dict, identity: MemberIdentity, ano_ref: str
) -> tuple[list, list]:
    """Divide veículos consolidated entre titular e cônjuge."""
    titular: list[dict] = []
    conjuge: list[dict] = []
    for v in baseline.get("veiculos_consolidados", []) or []:
        entry = {
            "descricao": v.get("descricao", ""),
            "valor_31_12_ano_base": _resolve_item_valor(v, ano_ref),
        }
        if _is_conjuge_exclusive(v, identity):
            conjuge.append(entry)
        else:
            titular.append(entry)
    return titular, conjuge


def _split_dividas(
    baseline: dict, identity: MemberIdentity, ano_ref: str
) -> tuple[float, float]:
    """Soma dívidas por membro. Dívidas compartilhadas → titular (para totalizar)."""
    dividas_list = baseline.get(
        "dividas", baseline.get("dividas_consolidadas", [])
    ) or []
    titular_div = 0.0
    conjuge_div = 0.0
    for dv in dividas_list:
        saldo = dv.get("saldo_31_12", {})
        if isinstance(saldo, dict):
            val = safe_float(saldo.get(ano_ref, 0))
        else:
            val = _resolve_item_valor(dv, ano_ref)
        prop = (dv.get("proprietario", "") or "").lower()
        if (
            identity.conjuge_key
            and identity.conjuge_key in prop
            and identity.titular_key not in prop
        ):
            conjuge_div += val
        else:
            titular_div += val
    return titular_div, conjuge_div


def build_members_from_consolidated(
    baseline: dict, identity: MemberIdentity
) -> tuple[dict, dict]:
    """Constrói titular/cônjuge a partir do formato v1.5 consolidated.

    Suporta duas convenções de nomes de chaves:
        - **Original**: ``imoveis_consolidados`` / ``investimentos_consolidados`` /
          ``dividas`` / ``patrimonio_por_ano``.
        - **E1.5 v2**: ``bens_imoveis_consolidados`` /
          ``investimentos_financeiros_consolidados`` / ``dividas_consolidadas`` /
          ``resumo_patrimonial`` + ``cálculo_patrimonio_liquido``.

    Quando ``total_bens`` do resumo diverge do sintético dos itens, a diferença
    é alocada ao titular (comportamento do legado).
    """
    ano_ref, total_bens_summary, _ = _resolve_ano_ref(baseline)

    titular_imoveis, conjuge_imoveis = _split_imoveis(baseline, identity, ano_ref)
    titular_inv, conjuge_inv = _split_investimentos(baseline, identity, ano_ref)
    titular_vei, conjuge_vei = _split_veiculos(baseline, identity, ano_ref)
    titular_div, conjuge_div = _split_dividas(baseline, identity, ano_ref)

    def _sum_items(*lists: list[dict]) -> float:
        return sum(
            safe_float(item.get("valor_31_12_ano_base", 0))
            for lst in lists
            for item in lst
        )

    titular_total = _sum_items(titular_imoveis, titular_inv, titular_vei)
    conjuge_total = _sum_items(conjuge_imoveis, conjuge_inv, conjuge_vei)

    titular_data = {
        "total_bens": titular_total,
        "total_dividas": titular_div,
        "bens": {
            "imoveis": titular_imoveis,
            "investimentos": titular_inv,
            "veiculos": titular_vei,
            "contas_bancarias": [],
        },
    }
    conjuge_data = {
        "total_bens": conjuge_total,
        "total_dividas": conjuge_div,
        "bens": {
            "imoveis": conjuge_imoveis,
            "investimentos": conjuge_inv,
            "veiculos": conjuge_vei,
            "contas_bancarias": [],
        },
    }

    # Diferença vs resumo → atribuída ao titular (comportamento legado)
    synthetic_total = titular_total + conjuge_total
    if total_bens_summary > 0 and abs(synthetic_total - total_bens_summary) > 1.0:
        diff = total_bens_summary - synthetic_total
        titular_data["total_bens"] += diff

    if not identity.conjuge_key:
        conjuge_data = {}

    return titular_data, conjuge_data
