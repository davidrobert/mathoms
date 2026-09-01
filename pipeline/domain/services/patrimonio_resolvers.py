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
from dataclasses import dataclass
from datetime import date
from typing import Any

from pipeline.domain.services.member_key_matcher import (
    matches_member_exclusively,
    matches_member_key,
)
from pipeline.domain.services.patrimonio_types import (
    CLASSES_DE_ATIVO,
    CONSOLIDATED_LIST_KEYS,
    AnosBaseDoMembro,
    MemberIdentity,
    MembrosResolvidos,
    _anos_fechados,
    investimento_valor,
    parse_ano_31_12,
    resolve_value_year,
    safe_float,
    ultimo_ano_31_12_fechado,
    years_in_list,
)
from pipeline.domain.services.valor_nao_apurado import anos_nao_apurados

# =============================================================================
# resolve_members — dispatcher de 4 formatos
# =============================================================================


def resolve_members(baseline: dict, identity: MemberIdentity) -> MembrosResolvidos:
    """Resolve titular e cônjuge de qualquer baseline suportado — produtor único."""
    titular, conjuge = _resolve_members_par(baseline, identity)
    return MembrosResolvidos(
        titular=titular,
        conjuge=conjuge,
        titular_key=identity.titular_key,
        conjuge_key=identity.conjuge_key,
    )


# Se o formato não casar com nenhum ramo, cai no consolidated (o mais tolerante).
def _resolve_members_par(baseline: dict, identity: MemberIdentity) -> tuple[dict, dict]:
    """Despacha entre os 4 formatos de baseline e devolve o par cru."""
    members = baseline.get("members", baseline.get("membros", {}))

    if isinstance(members, list):
        has_dicts = any(isinstance(m, dict) for m in members)
        if has_dicts:
            titular_data, conjuge_data = {}, {}
            for m in members:
                if not isinstance(m, dict):
                    continue
                nome = m.get("nome", "").lower()
                if matches_member_key(identity.titular_key, nome):
                    titular_data = m
                elif identity.conjuge_key and matches_member_key(identity.conjuge_key, nome):
                    conjuge_data = m
            return titular_data, conjuge_data

        # Lista de strings → formato E1.5 declarations ou consolidated
        if baseline.get("imoveis_consolidados") is not None or baseline.get("patrimonio_por_ano"):
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

        valor = safe_float(bem.get("situacao_atual", bem.get("valor_31_12_atual", 0)))
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

    if identity.titular_key and matches_member_key(identity.titular_key, membro):
        return identity.titular_key
    if identity.conjuge_key and matches_member_key(identity.conjuge_key, membro):
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


def build_members_from_declarations(baseline: dict, identity: MemberIdentity) -> tuple[dict, dict]:
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
            if key == identity.titular_key and matches_member_key(identity.titular_key, prop):
                total += safe_float(dv.get("saldo_31_12", 0))
            elif (
                key == identity.conjuge_key
                and identity.conjuge_key
                and matches_member_key(identity.conjuge_key, prop)
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
            safe_float(b.get("valor_31_12_ano_base", 0)) for cat in bens.values() for b in cat
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


@dataclass(frozen=True)
class AnoResolution:
    """Desacopla o ano de valor (itens, 31/12) do ano-chave do resumo (ADR-274)."""

    # value_year resolve valores_31_12 por-item; summary_year é a chave de
    # patrimonio_por_ano. Totais vêm de _resolve_summary_year (não aqui).
    value_year: str
    summary_year: str


def _resolve_summary_year(baseline: dict) -> tuple[str, float, float]:
    """Ano-chave do resumo + ``total_bens``/``total_dividas`` (ADR-274)."""
    # Formato original (patrimonio_por_ano) antes do E1.5 v2 (resumo_patrimonial
    # / cálculo_patrimonio_liquido). Default: ano anterior.
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
    calculo = (
        baseline.get(
            "cálculo_patrimonio_liquido",
            baseline.get("calculo_patrimonio_liquido", {}),
        )
        or {}
    )

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


def _resolve_ano_ref(baseline: dict) -> AnoResolution:
    """Resolve ano-base de valor (itens) e ano de resumo, desacoplados (ADR-274)."""
    summary_year, _, _ = _resolve_summary_year(baseline)
    value_year = resolve_value_year(baseline, summary_year)
    return AnoResolution(value_year, summary_year)


def _anos_da_lista(raw: object, identity: MemberIdentity, conjuge: bool) -> set[int]:
    """Anos declarados pelo membro numa lista consolidada (v1 itens ou v2 agregado)."""
    if isinstance(raw, list):
        return years_in_list([i for i in raw if _is_conjuge_exclusive(i, identity) == conjuge])
    if isinstance(raw, dict):
        return _anos_do_membro_agregado(raw, identity, conjuge)
    return set()


def _anos_do_membro(baseline: dict, identity: MemberIdentity, conjuge: bool) -> set[int]:
    """Anos 31/12 declarados nos itens **deste** membro, por lista consolidada."""
    anos: set[int] = set()
    for list_key in CONSOLIDATED_LIST_KEYS:
        anos |= _anos_da_lista(baseline.get(list_key), identity, conjuge)
    return anos


def _anos_do_membro_agregado(raw: dict, identity: MemberIdentity, conjuge: bool) -> set[int]:
    """Anos no formato agregado E1.5 v2, cuja chave é ``<membro>_<ano>``."""

    def _e_do_membro(key: object) -> bool:
        casa = bool(identity.conjuge_key) and matches_member_key(identity.conjuge_key, str(key))
        return casa == conjuge

    anos = (parse_ano_31_12(str(k)) for k in raw if _e_do_membro(k))
    return {ano for ano in anos if ano is not None}


# O eixo de ano era do DOMICÍLIO (`_max_value_year` sobre o baseline inteiro). Com
# os cônjuges declarando em anos disjuntos isso zera todos menos um: quem não tem
# item no ano escolhido cai no fallback de `_resolve_item_valor` e vira 0,00 — a
# mesma conflação `null`↔`0,00` que a [[ADR-394]] proíbe um andar acima.
def anos_base_por_membro(
    baseline: dict, identity: MemberIdentity, ano_domicilio: str
) -> tuple[str, str]:
    """Ano-base de cada membro: o maior ano **fechado** que ele próprio declarou."""
    # O eixo por membro é computado aqui do zero, então filtrar só em
    # `_max_value_year` não alcança este caminho — foi por ele que o `2026` de
    # um item chegou ao titular e zerou imóveis, veículos e dívidas ([[A40.l114]]).
    teto = ultimo_ano_31_12_fechado()
    titular = _anos_fechados(_anos_do_membro(baseline, identity, conjuge=False), teto)
    conjuge = _anos_fechados(_anos_do_membro(baseline, identity, conjuge=True), teto)
    return (
        str(max(titular)) if titular else ano_domicilio,
        str(max(conjuge)) if conjuge else ano_domicilio,
    )


def _anos_do_membro_na_classe(
    baseline: dict, identity: MemberIdentity, conjuge: bool, classe: str
) -> set[int]:
    """Anos 31/12 que o membro declarou **dentro** de uma classe de ativo."""
    anos: set[int] = set()
    for list_key in CLASSES_DE_ATIVO[classe]:
        anos |= _anos_da_lista(baseline.get(list_key), identity, conjuge)
    return anos


def _ano_base_do_membro(
    baseline: dict, identity: MemberIdentity, *, conjuge: bool, fallback: str
) -> AnosBaseDoMembro:
    """Elege o ano de cada classe separadamente ([[ADR-433]])."""
    por_classe: dict[str, str] = {}
    for classe in CLASSES_DE_ATIVO:
        anos = _anos_do_membro_na_classe(baseline, identity, conjuge, classe)
        if anos:
            por_classe[classe] = str(max(anos))
    return AnosBaseDoMembro(por_classe=por_classe, fallback=fallback)


# A eleição sobre a UNIÃO das classes deixava a classe mais atualizada ditar o ano
# das outras; quem não tinha item nesse ano caía no fallback de
# `_resolve_item_valor` e virava 0,00 — publicando "a família não tem casa própria"
# ([[ADR-433]]). O grão certo é (membro × classe); o veto da [[ADR-274]] ao máximo
# **por-item** continua de pé, e esta função não o toca.
def anos_base_por_classe(
    baseline: dict, identity: MemberIdentity, ano_domicilio: str
) -> tuple[AnosBaseDoMembro, AnosBaseDoMembro]:
    """Ano-base de cada membro em cada classe de ativo ([[ADR-433]])."""
    return (
        _ano_base_do_membro(baseline, identity, conjuge=False, fallback=ano_domicilio),
        _ano_base_do_membro(baseline, identity, conjuge=True, fallback=ano_domicilio),
    )


# O ano era descoberto aqui e esquecido. O ramo `valor` cru não tem ano e devolve
# `None` — é o que separa "valor de 2023" de "valor sem data" ([[ADR-383]] §6).
def _resolve_item_valor_e_ano(item: dict, ano_ref: str) -> tuple[float, str | None]:
    """Valor do item consolidated e o ano em que ele foi encontrado."""
    vals_dict = item.get("valores_31_12", {})
    if isinstance(vals_dict, dict):
        v = vals_dict.get(ano_ref, vals_dict.get(f"31_12_{ano_ref}"))
        if v is not None:
            return safe_float(v), ano_ref
    v = item.get(f"valor_{ano_ref}")
    if v is not None:
        return safe_float(v), ano_ref
    return safe_float(item.get("valor", 0)), None


def _resolve_item_valor(item: dict, ano_ref: str) -> float:
    """Só o valor — para quem não precisa da proveniência de ano."""
    return _resolve_item_valor_e_ano(item, ano_ref)[0]


# O produtor declara o estado no item ([[ADR-431]]); ler o `null` cru não bastaria,
# porque `valores_31_12[ano] is None` é indistinguível de ano ausente e
# `_resolve_item_valor_e_ano` cairia nos fallbacks `valor_<ano>`/`valor` —
# ressuscitando um valor de outra data no lugar do que não foi apurado.
def _valor_nao_apurado_no_ano(item: dict, ano_ref: str) -> bool:
    """O produtor declarou que o valor DESTE ano não foi apurado."""
    return ano_ref in anos_nao_apurados(item)


# `None` e não `0,0`: zero publicado é afirmação sobre o patrimônio da pessoa
# ([[ADR-346]] · [[ADR-394]] §Emenda (b) D7). O ano vem de `ano_ref` porque o
# resolvedor perde a proveniência ao cair no fallback.
def _com_valor(entry: dict, item: dict, ano_ref: str) -> tuple[dict, str | None]:
    """Carimba o valor do ano-base, ou o declara não apurado."""
    valor, ano = _resolve_item_valor_e_ano(item, ano_ref)
    if _valor_nao_apurado_no_ano(item, ano_ref):
        entry["valor_31_12_ano_base"] = None
        entry["valor_nao_apurado"] = True
        return entry, ano_ref
    entry["valor_31_12_ano_base"] = valor
    return entry, ano


# Os dois campos já vêm da fonte (`consolidate_baseline.py`); descartá-los era o
# que fazia duas projeções do mesmo item divergirem ([[ADR-410]] D1).
def _com_proveniencia(entry: dict, item: dict, ano: str | None) -> dict:
    """Carimba no entry o ano-base do próprio item e a instituição da fonte."""
    if ano:
        entry["ano_base"] = ano
    if item.get("instituicao"):
        entry["instituicao"] = item["instituicao"]
    return entry


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
        if matches_member_exclusively(identity.conjuge_key, identity.titular_key, p_lower):
            return True

    props = item.get("proprietarios", [])
    if isinstance(props, list):
        names_lower = [p.lower() for p in props if isinstance(p, str)]
        if matches_member_exclusively(identity.conjuge_key, identity.titular_key, names_lower):
            return True

    return False


def _descricao_do_imovel(item: dict) -> str:
    """Descrição rica do imóvel: própria → `dados_completos.imovel` → endereço."""
    descricao = item.get("descricao", "")
    if descricao:
        return descricao
    dc = item.get("dados_completos", {})
    if isinstance(dc, dict) and dc.get("imovel"):
        return dc["imovel"]
    return item.get("endereco", "") or ""


def _imovel_entry_from_consolidated(item: dict, ano_ref: str) -> dict:
    """Monta entry de imóvel consolidated preservando descrição rica + property_id."""
    entry, ano = _com_valor(
        {
            "descricao": _descricao_do_imovel(item),
            "endereco": item.get("endereco", ""),
            "tipo": item.get("tipo", ""),
        },
        item,
        ano_ref,
    )
    pid = item.get("property_id")
    if isinstance(pid, str) and pid:
        entry["property_id"] = pid
    return _com_proveniencia(entry, item, ano)


def _split_imoveis(baseline: dict, identity: MemberIdentity, ano_ref: str) -> tuple[list, list]:
    """Divide imóveis consolidados entre titular e cônjuge."""
    imoveis_list = (
        baseline.get("imoveis_consolidados", baseline.get("bens_imoveis_consolidados", [])) or []
    )
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
            valor, ano = _resolve_item_valor_e_ano(inv, ano_ref)
            # `tipo` NÃO entra: metade do codomínio de `_classify_investimento`
            # é default de grupo RFB (`renda_fixa` do 04, `investimento` do
            # fall-through) indistinguível de evidência, e o classificador o
            # trataria como fato — 11 de 61 posições migraram de classe assim
            # ([[A40.l82]] · RV8-01). Volta quando o degrau 1 da [[ADR-400]]
            # separar presunção de fato no produtor.
            entry = {
                "descricao": inv.get("descricao", ""),
                "valor_31_12_ano_base": valor,
            }
            _com_proveniencia(entry, inv, ano)
            if _is_conjuge_exclusive(inv, identity):
                conjuge_inv.append(entry)
            else:
                titular_inv.append(entry)

    elif isinstance(inv_raw, dict):
        for member_key, categories in inv_raw.items():
            if not isinstance(categories, dict):
                continue
            is_conjuge = identity.conjuge_key and matches_member_key(
                identity.conjuge_key, member_key
            )
            target = conjuge_inv if is_conjuge else titular_inv
            for cat_name, cat_value in categories.items():
                if cat_name == "total":
                    continue
                val = safe_float(cat_value)
                if val == 0:
                    continue
                target.append(
                    {
                        "descricao": cat_name.replace("_", " ").title(),
                        "tipo": cat_name,
                        "valor_31_12_ano_base": val,
                    }
                )

    return titular_inv, conjuge_inv


def _split_veiculos(baseline: dict, identity: MemberIdentity, ano_ref: str) -> tuple[list, list]:
    """Divide veículos consolidated entre titular e cônjuge."""
    titular: list[dict] = []
    conjuge: list[dict] = []
    for v in baseline.get("veiculos_consolidados", []) or []:
        entry, ano = _com_valor({"descricao": v.get("descricao", "")}, v, ano_ref)
        _com_proveniencia(entry, v, ano)
        if _is_conjuge_exclusive(v, identity):
            conjuge.append(entry)
        else:
            titular.append(entry)
    return titular, conjuge


def _split_dividas(baseline: dict, identity: MemberIdentity, ano_ref: str) -> tuple[float, float]:
    """Soma dívidas por membro. Dívidas compartilhadas → titular (para totalizar)."""
    dividas_list = baseline.get("dividas", baseline.get("dividas_consolidadas", [])) or []
    titular_div = 0.0
    conjuge_div = 0.0
    for dv in dividas_list:
        saldo = dv.get("saldo_31_12", {})
        if isinstance(saldo, dict):
            val = safe_float(saldo.get(ano_ref, 0))
        else:
            val = _resolve_item_valor(dv, ano_ref)
        prop = (dv.get("proprietario", "") or "").lower()
        if matches_member_exclusively(identity.conjuge_key, identity.titular_key, prop):
            conjuge_div += val
        else:
            titular_div += val
    return titular_div, conjuge_div


# `frescor` ([[ADR-410]] D6) lê o escalar; com classes em anos distintos qualquer
# escolha é parcial, então usa-se o MENOR — frescor nunca superestimado. O mapa
# completo viaja ao lado, que é a "datas por linha" da [[ADR-383]] §6.
def _ano_base_escalar(anos: AnosBaseDoMembro, fallback: str) -> str:
    """Menor ano eleito entre as classes do membro; o do domicílio se não houver."""
    eleitos = anos.eleitos()
    return min(eleitos) if eleitos else fallback


# O crédito do resíduo ao titular só é lícito quando o sintético é do MESMO ano do
# resumo. Com o eixo por classe o antigo `ano_titular == ano_conjuge` passa a poder
# ser verdadeiro sobre um sintético multi-ano, o que **ligaria** o crédito e
# fabricaria patrimônio — a família do `unattributed → titular` que a [[ADR-394]]
# §D8 cortou. O predicado passa a exigir igualdade com o ano do resumo.
def _todas_as_classes_no_ano(
    anos_por_membro: tuple[AnosBaseDoMembro, ...], summary_year: str
) -> bool:
    """Todo ano **efetivamente usado** para resolver valor é o ano do resumo."""
    # O ano efetivo de uma classe é o eleito, ou o do domicílio quando o membro
    # nada declarou nela — é assim que `_split` resolve. Contar só os eleitos
    # deixaria o formato legado (`valor_YYYY`, que não elege ano nenhum) sem
    # crédito, apesar de ele ser single-year por construção.
    usados = {anos.para(classe) for anos in anos_por_membro for classe in CLASSES_DE_ATIVO}
    return usados == {summary_year}


def build_members_from_consolidated(baseline: dict, identity: MemberIdentity) -> tuple[dict, dict]:
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
    summary_year, total_bens_summary, _ = _resolve_summary_year(baseline)
    ano_ref = resolve_value_year(baseline, summary_year)
    anos_titular, anos_conjuge = anos_base_por_classe(baseline, identity, ano_ref)

    def _split(fn, classe: str):
        """Cada metade no ano que o **próprio** membro declarou **nesta** classe."""
        ano_t, ano_c = anos_titular.para(classe), anos_conjuge.para(classe)
        if ano_t == ano_c:
            return fn(baseline, identity, ano_t)
        return fn(baseline, identity, ano_t)[0], fn(baseline, identity, ano_c)[1]

    titular_imoveis, conjuge_imoveis = _split(_split_imoveis, "imoveis")
    titular_inv, conjuge_inv = _split(_split_investimentos, "investimentos")
    titular_vei, conjuge_vei = _split(_split_veiculos, "veiculos")
    titular_div, conjuge_div = _split(_split_dividas, "dividas")

    def _sum_items(*lists: list[dict]) -> float:
        return sum(safe_float(item.get("valor_31_12_ano_base", 0)) for lst in lists for item in lst)

    titular_total = _sum_items(titular_imoveis, titular_inv, titular_vei)
    conjuge_total = _sum_items(conjuge_imoveis, conjuge_inv, conjuge_vei)

    # `ano_base` por membro para que a soma cross-ano nunca seja silenciosa: o
    # agregado do domicílio pode misturar datas, e quem consome precisa poder
    # ressalvar ([[ADR-383]] §6 — datas mistas nunca levam data única).
    titular_data = {
        "total_bens": titular_total,
        "total_dividas": titular_div,
        "ano_base": _ano_base_escalar(anos_titular, ano_ref),
        "ano_base_por_classe": dict(anos_titular.por_classe),
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
        "ano_base": _ano_base_escalar(anos_conjuge, ano_ref),
        "ano_base_por_classe": dict(anos_conjuge.por_classe),
        "bens": {
            "imoveis": conjuge_imoveis,
            "investimentos": conjuge_inv,
            "veiculos": conjuge_vei,
            "contas_bancarias": [],
        },
    }

    # Diferença vs resumo → atribuída ao titular (comportamento legado). Só vale
    # quando os dois membros estão no MESMO ano: `total_bens_summary` é de um ano
    # só, então com anos distintos o sintético é multi-ano e a divergência dispara
    # por construção — creditar o resíduo ao titular fabricaria patrimônio, a mesma
    # família do `unattributed → titular` que a [[ADR-394]] §D8 cortou.
    synthetic_total = titular_total + conjuge_total
    mesmo_ano = _todas_as_classes_no_ano((anos_titular, anos_conjuge), summary_year)
    if mesmo_ano and total_bens_summary > 0 and abs(synthetic_total - total_bens_summary) > 1.0:
        diff = total_bens_summary - synthetic_total
        titular_data["total_bens"] += diff

    if not identity.conjuge_key:
        conjuge_data = {}

    return titular_data, conjuge_data


def rv_ressalva(sem_por_membro: dict, identity, *, titular_fb: bool, conjuge_fb: bool) -> dict:
    """ADR-346 (A39.l9) invariante 8: agrega posições RV sem valor de mercado por
    membro (atribuição titular / cônjuge / não-atribuído→titular) e sinaliza
    ``pl_ressalva`` quando o membro NÃO foi coberto pelo fallback IRPF — senão a
    marcação faltante é info (o IRPF valora o holding, não deflaciona; fp-S3)."""
    tickers: list[str] = []
    for member_key, nomes in (sem_por_membro or {}).items():
        kl = str(member_key).lower()
        is_conjuge = bool(identity.conjuge_key and matches_member_key(identity.conjuge_key, kl))
        if not (conjuge_fb if is_conjuge else titular_fb):
            tickers.extend(nomes)
    return {
        "pl_ressalva": bool(tickers),
        "posicoes_sem_marcacao": {
            "count": len(tickers),
            "tickers": sorted({t for t in tickers if t}),
        },
    }


def investimentos_from_irpf(bens: dict, *, extras: tuple[str, ...]) -> float:
    """Soma investimentos IRPF (investimentos + contas_bancarias + extras)."""
    total = 0.0
    for inv in bens.get("investimentos", []) or []:
        total += investimento_valor(inv)
    contas = bens.get("contas_bancarias", [])
    if isinstance(contas, list):
        for c in contas:
            total += investimento_valor(c)
    else:
        total += safe_float(contas)
    for extra_key in extras:
        total += safe_float(bens.get(extra_key, 0))
    return total
