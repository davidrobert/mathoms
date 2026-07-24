"""InvestmentsConsolidator — consolida posições de investimento E2 em output E4
(Sessão A4a).

Extrai ``build_investimentos_unified`` (``e4_categorize.py:260``) em domain
service puro. Lê artefatos E2 de posição (``investimentosposicao``,
``carteira``, ``cdbresumo``), deduplica por (instituição, membro) mantendo o
mais recente, agrega posições e consolida totais por membro.

Recebe lista de dicts E2 (não `ArtifactStore` — o adapter faz o load); retorna
:class:`ConsolidatedInvestments` com ``to_legacy_dict()`` para output
``investimentos-4_unified.json``.

Configuração injetável (``InvestmentsConsolidatorConfig``):
- ``banco_membro``: map ``banco_code.lower().replace(" ", "") → member_key`` —
  usado como fallback quando a posição não tem ``membro`` declarado
  (`e4_categorize.py` usa ``_family["banco_membro"]`` para isso).
- ``divergence_tolerance``: R$ — gap acima desse valor entre total declarado
  e soma de posições gera warning (default 1.0).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pipeline.domain.services.member_name_resolver import MemberNameResolver
from pipeline.domain.types.config import BankAccountRecord

# =============================================================================
# Config
# =============================================================================


@dataclass(frozen=True)
class InvestmentsConsolidatorConfig:
    banco_membro: dict[str, str] = field(default_factory=dict)
    # ADR-226 PR3 — quando populada, AccountResolver substitui lookup direto;
    # ambíguo (>1 membro mesmo banco) marca posição needs_review.
    accounts: tuple[BankAccountRecord, ...] = ()
    divergence_tolerance: float = 1.0
    # ADR-243 — resolver de nome canônico de membro. Defensive layer para
    # artifacts E2 carry-forwarded de runs antigas (pré-ADR-243) e para
    # casos onde o LLM ignorou o vocabulário canônico do prompt.
    member_name_resolver: MemberNameResolver | None = None

    @classmethod
    def from_family(cls, family: dict | None = None) -> "InvestmentsConsolidatorConfig":
        fam = family or {}
        raw = fam.get("banco_membro") or {}
        clean = {str(k): str(v) for k, v in raw.items() if not str(k).startswith("_")}
        contas_raw = fam.get("contas") or []
        accounts = tuple(_parse_account_record(c) for c in contas_raw if isinstance(c, dict))
        member_resolver = MemberNameResolver.from_family_config(fam)
        return cls(
            banco_membro=clean,
            accounts=accounts,
            member_name_resolver=member_resolver,
        )


def _parse_account_record(raw: dict) -> BankAccountRecord:
    from pipeline.domain.services.account_normalization import normalize_account_number

    raw_num = raw.get("account_number_raw")
    # fallback da janela A24.l2 (ADR-280): members novos emitem só raw
    norm = raw.get("account_number_norm") or normalize_account_number(
        str(raw_num) if raw_num is not None else None
    )
    return BankAccountRecord(
        member_key=str(raw.get("member_key") or ""),
        institution_code=str(raw.get("institution_code") or ""),
        account_type=str(raw.get("account_type") or ""),
        account_number_norm=norm,
        account_number_raw=raw_num,
        agency=raw.get("agency"),
    )


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class ConsolidatedInvestments:
    """Output ``investimentos-4_unified.json``."""

    dados: list[dict]
    total_por_membro: dict[str, float]
    total_geral: float
    fontes: list[str]
    data_consolidacao: str
    n_posicoes: int
    avisos_validacao: tuple[str, ...] = ()

    def to_legacy_dict(self) -> dict:
        out: dict = {
            "dados": list(self.dados),
            "total_por_membro": {k: v for k, v in sorted(self.total_por_membro.items())},
            "total_geral": self.total_geral,
            "fontes": list(self.fontes),
            "data_consolidacao": self.data_consolidacao,
            "n_posicoes": self.n_posicoes,
        }
        if self.avisos_validacao:
            out["avisos_validacao"] = list(self.avisos_validacao)
        return out


# =============================================================================
# Service
# =============================================================================


class InvestmentsConsolidator:
    """Consolida posições de investimento E2 em uma entidade unificada.

    Stateless. ``now`` injetável para testes determinísticos.
    """

    def __init__(
        self,
        config: InvestmentsConsolidatorConfig | None = None,
        *,
        now=None,
    ) -> None:
        from pipeline.domain.services.account_resolver import AccountResolver

        self._config = config or InvestmentsConsolidatorConfig()
        self._now = now
        self._resolver = AccountResolver(
            self._config.accounts, banco_membro_legacy=self._config.banco_membro
        )
        self._member_name_resolver = self._config.member_name_resolver

    def _iso_today(self) -> str:
        return (self._now or datetime.now()).strftime("%Y-%m-%d")

    # -- API --

    def consolidate(
        self,
        candidates: list[dict],
        *,
        source_names: list[str] | None = None,
    ) -> ConsolidatedInvestments:
        """Processa lista de dicts E2 de posição.

        Args:
            candidates: lista de ``{"_source": filename, **data}`` ou apenas
                dicts com a key ``"_source"``. O adapter injeta ``_source``
                durante o load a partir do `artifact_key`. Se ``source_names``
                não for passado, usa ``_source`` em cada candidate.
            source_names: opcional — nomes de arquivo paralelos a
                ``candidates`` (quando não está injetado como ``_source``).

        Returns:
            :class:`ConsolidatedInvestments` frozen, paridade com
            ``build_investimentos_unified``.
        """
        # Normaliza entrada — produz list[(data_dict, source_name)].
        pairs: list[tuple[dict, str]] = []
        for i, c in enumerate(candidates):
            if not isinstance(c, dict):
                continue
            src = c.get("_source") or (
                source_names[i] if source_names and i < len(source_names) else ""
            )
            pairs.append((c, str(src)))

        # Phase 1: filtra candidates válidos.
        valid: list[dict[str, Any]] = []
        for data, src in pairs:
            posicoes = (
                data.get("posicoes") or data.get("composicao") or data.get("investimentos") or []
            )
            if not posicoes:
                continue
            instituicao = data.get("instituicao") or data.get("banco") or ""
            membro_raw = (data.get("membro") or "").lower()
            # ADR-243 — normaliza nome bruto do LLM para a chave canônica
            # do workspace antes de qualquer outra lógica (dedup, totalização,
            # match contra titular_key/conjuge_key downstream em E5).
            membro = ""
            if membro_raw and self._member_name_resolver is not None:
                resolution = self._member_name_resolver.resolve(membro_raw)
                if resolution.canonical_key:
                    membro = resolution.canonical_key
                else:
                    # Resolver não casou — preserva raw (audit + telemetria
                    # já registra confidence=unknown/ambiguous no log).
                    membro = membro_raw
            else:
                membro = membro_raw
            if not membro and instituicao:
                # ADR-226 PR3 — resolver substitui lookup direto banco_membro.
                inst_key = str(instituicao).lower().replace(" ", "")
                acc_num = data.get("numero_conta") or data.get("account_number")
                resolution = self._resolver.resolve(inst_key, acc_num)
                if resolution.confidence == "ambiguous":
                    membro = "needs_review"
                else:
                    membro = resolution.member_key or ""
            data_ref = (
                data.get("data_referencia") or data.get("data_posicao") or data.get("periodo") or ""
            )
            total_fonte = (
                data.get("total") or data.get("saldo_atual") or data.get("saldo_total") or 0
            )

            valid.append(
                {
                    "_source": src,
                    "_data": data,
                    "_posicoes": posicoes,
                    "instituicao": instituicao,
                    "membro": membro,
                    "data_ref": data_ref,
                    "total_fonte": total_fonte,
                }
            )

        # Phase 2: dedup por (inst, membro) — mantém o mais recente por data_ref.
        # ADR-346 (A39.l9): instituição vazia NÃO pode ser chave que descarta —
        # duas fontes valoradas inst-vazia do mesmo membro colidiriam em
        # ("", membro) e uma sumiria em silêncio (perda de patrimônio). Fallback
        # à identidade de fonte estável (_source/artifact_key). `data_ref` é
        # tie-break, NUNCA componente de chave: adicioná-lo à chave somaria
        # snapshots temporais do mesmo broker (PL 2×). Todo descarte é registrado
        # em `avisos` (invariante 2: nenhum descarte silencioso).
        best_by_key: dict[tuple[str, str], dict[str, Any]] = {}
        dedup_avisos: list[str] = []
        for cand in valid:
            inst_key = (cand["instituicao"] or "").lower().strip()
            if not inst_key:
                dedup_avisos.append(
                    f"[WARN] instituição não resolvida para {cand['_source']!r} — usando "
                    "identidade de fonte no dedup (resolver no parser; ADR-346 passo 4/PR3)"
                )
            key = (inst_key or f"_src:{cand['_source']}", cand["membro"])
            existing = best_by_key.get(key)
            if existing is None:
                best_by_key[key] = cand
                continue
            keep, drop = (
                (cand, existing)
                if str(cand["data_ref"]) > str(existing["data_ref"])
                else (existing, cand)
            )
            best_by_key[key] = keep
            dedup_avisos.append(
                f"[WARN] dedup posição ({cand['membro']}, {inst_key or cand['_source']}): "
                f"mantida data_ref {keep['data_ref']!r} ({keep['_source']!r}), "
                f"descartada {drop['data_ref']!r} ({drop['_source']!r})"
            )

        # Phase 3: construir posições + totais.
        all_positions: list[dict] = []
        sources: list[str] = []
        totals_by_member: dict[str, float] = {}
        avisos: list[str] = list(dedup_avisos)

        for cand in best_by_key.values():
            posicoes = cand["_posicoes"]
            instituicao = cand["instituicao"]
            membro = cand["membro"]
            data_ref = cand["data_ref"]
            total_fonte = cand["total_fonte"]
            source = cand["_source"]

            positions_sum = 0.0
            for pos in posicoes:
                if not isinstance(pos, dict):
                    continue
                valor = (
                    pos.get("valor_total")
                    or pos.get("valor_atual")
                    or pos.get("current_value")
                    or pos.get("valor_brl")
                    or 0
                )
                try:
                    valor = float(valor) if valor else 0.0
                except (ValueError, TypeError):
                    valor = 0.0
                positions_sum += valor

                all_positions.append(
                    {
                        "nome": (pos.get("nome") or pos.get("name") or pos.get("descricao") or ""),
                        "tipo": (
                            pos.get("tipo")
                            or pos.get("tipo_produto")
                            or pos.get("product_type")
                            or ""
                        ),
                        "instituicao": instituicao,
                        "membro": membro,
                        "valor_atual": valor,
                        "data_referencia": data_ref,
                        "taxa": pos.get("taxa") or pos.get("rentabilidade") or "",
                        "vencimento": pos.get("vencimento", ""),
                    }
                )

            try:
                total_f = float(total_fonte) if total_fonte else 0.0
            except (ValueError, TypeError):
                total_f = 0.0
            if total_f == 0 and posicoes:
                total_f = positions_sum

            # Validação: saldo_atual vs soma de posições detalhadas.
            if (
                total_f > 0
                and positions_sum > 0
                and abs(total_f - positions_sum) > self._config.divergence_tolerance
            ):
                gap = total_f - positions_sum
                avisos.append(
                    f"[WARN] {instituicao} ({membro}): saldo_atual R$ {total_f:,.2f} vs "
                    f"itens R$ {positions_sum:,.2f} — gap R$ {gap:,.2f} (posições não detalhadas no E2)"
                )

            totals_by_member[membro] = totals_by_member.get(membro, 0.0) + total_f
            if source:
                sources.append(source)

        total_geral = sum(totals_by_member.values())

        return ConsolidatedInvestments(
            dados=all_positions,
            total_por_membro={k: round(v, 2) for k, v in totals_by_member.items()},
            total_geral=round(total_geral, 2),
            fontes=sources,
            data_consolidacao=self._iso_today(),
            n_posicoes=len(all_positions),
            avisos_validacao=tuple(avisos),
        )
