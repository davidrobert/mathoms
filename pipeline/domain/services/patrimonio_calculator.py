"""``PatrimonioCalculator`` — composição patrimonial completa (A6d.3.3 — ADR-100).

Substitui ``scripts/analyze_finances.analyze_patrimonio`` por um serviço puro:
- Zero globals; recebe :class:`PatrimonioConfig` com identidade + keyword.
- Zero I/O; o adapter carrega baseline + investimentos_atuais + caixa E3 e
  monta :class:`PatrimonioInputs`.
- Produz o mesmo ``dict`` que ``analyze_patrimonio`` (paridade byte-a-byte
  exceto por prints debug que não fazem parte do contrato).

Segue o **mesmo contrato de saída** do legado — o dict é consumido por:
- ``scripts/analyze_finances.analyze_ratios`` (campos ``bruto``, ``investivel``,
  ``dividas``, ``residencia``, ``veiculos``).
- ``config/report_layout.yaml`` via ``analise_financeira-5_analysis.json``.
- ``scripts/generate_narratives.build_narrativas`` (campos ``composicao``,
  ``caixa_detalhes``, ``fonte_investimentos``).

Composição patrimonial — taxonomia canônica (rules-as-code, ADR-145)
====================================================================

Sprint A7.6 (rules-as-code) consolidou a especificação das categorias da
composição patrimonial neste módulo + ADR-145. As regras universais são
invariantes do produto Mathoms (não dado cliente).

**7 categorias canônicas (ordem ADR-145):**

1. **Residência própria** — moradia principal (exatamente 1 imóvel
   classificado como ``residencia_principal`` via override em
   ``workspace_property_overrides`` por ``property_id``; ADR-215 §1).
2. **Imóveis investimento** — todos os outros imóveis (titular + cônjuge),
   exceto a residência principal. Ver
   :meth:`PatrimonioCalculator._split_imoveis`.
3. **Investimentos {TITULAR}** — ativos financeiros do titular. Inclui
   ``investimentos[]`` clássicos + ``contas_bancarias[]`` cujo ``tipo``
   contenha ``RDB|CDB|CDP|Renda Fixa|Investimento|Aplicacao|Poupança`` (ou
   "saldo em conta" de corretora). **Inclui** fundos regulados (FIC FIM)
   mesmo quando o nome sugere crypto — fundo FIC FIM não é crypto direta.
4. **Investimentos {CONJUGE}** — mesma regra aplicada ao cônjuge. Quando
   ausente (família com 1 titular apenas), retorna 0. Ver
   :meth:`PatrimonioCalculator._compute_investimentos`.
5. **Criptoativos** — crypto direta (BTC/ETH/etc.) em exchanges. **Não
   inclui** fundos regulados de crypto. No fallback IRPF, crypto direta
   chega via campo ``criptos`` em ``bens`` e é somada ao bucket de
   investimentos do titular (paridade legado); composição doughnut tem
   bucket próprio quando o pipeline rodar com extratos Binance via
   :mod:`pipeline.domain.services.investimentos_classes_analyzer`.
6. **Caixa + Moeda Estrangeira** — saldo final reconciliado (E3) das
   contas correntes BRL + contas FX convertidas (USD/EUR via
   ``taxas.json``). Ver :func:`pipeline.domain.services.patrimonio_caixa.compute_caixa` e
   ``scripts/analyze_finances._load_caixa_from_e3_saldos``.
7. **Veículos** — soma de ``veiculos[]`` de todos os membros. Ver
   :meth:`PatrimonioCalculator._sum_veiculos`.

**Premissa de produto:** "casal com até 2 titulares de investimentos"
(titular + cônjuge). Famílias fora dessa configuração ficam limitadas
pela taxonomia — expansão para N membros requer ADR futuro.

**Renaming de label vs key:** os labels exibidos no relatório vêm dos
``nome_curto`` em ``family_members.json``; chaves internas no JSON do
E5 são estáveis (``investimentos_titular``, ``investimentos_conjuge``).

Para o "porquê" de cada decisão (alternativas consideradas, trade-offs):
ver `ADR-145 <docs/DECISIONS.md#adr-145>`_.
"""

from __future__ import annotations

from typing import Any

from pipeline.domain.services.bases_financeiras import PapelMembro, publicar_bases
from pipeline.domain.services.investimentos_cobertura import (
    cobertura_de_membros,
    valor_publicavel,
)
from pipeline.domain.services.member_key_matcher import matches_member_key
from pipeline.domain.services.patrimonio_caixa import caixa_me_from_detalhes, compute_caixa
from pipeline.domain.services.patrimonio_composicao import build_composicao
from pipeline.domain.services.patrimonio_imovel_classifier import (
    CLASSIFICATION_COMERCIAL,
    CLASSIFICATION_DESCONHECIDO,
    CLASSIFICATION_ESPECULACAO,
    CLASSIFICATION_LOCADO,
    CLASSIFICATION_RESIDENCIA_PRINCIPAL,
    CLASSIFICATION_USO_PESSOAL,
    split_imoveis_geradores_vs_nao_geradores,
    split_imoveis_with_overrides,
    sum_imoveis_geradores_liquidos,
)
from pipeline.domain.services.patrimonio_resolvers import (
    investimentos_from_irpf,
    rv_ressalva,
)
from pipeline.domain.services.patrimonio_sign_guard import aplicar_guarda_aos_componentes
from pipeline.domain.services.patrimonio_types import (
    PatrimonioConfig,
    PatrimonioInputs,
    RealEstateValuationContext,
    get_bens,
    safe_float,
    veiculo_valor,
)
from pipeline.domain.services.posicao_31_12_builder import (
    build_caixa_me_detalhe,
    build_posicao_31_12,
)

__all__ = [
    "PatrimonioCalculator",
    "CLASSIFICATION_RESIDENCIA_PRINCIPAL",
    "CLASSIFICATION_USO_PESSOAL",
    "CLASSIFICATION_LOCADO",
    "CLASSIFICATION_COMERCIAL",
    "CLASSIFICATION_ESPECULACAO",
    "CLASSIFICATION_DESCONHECIDO",
    "split_imoveis_with_overrides",
    "split_imoveis_geradores_vs_nao_geradores",
]


class PatrimonioCalculator:
    """Calcula patrimônio consolidado preservando paridade com ``analyze_patrimonio``.

    Uso::

        config = PatrimonioConfig(
            members=MemberIdentity(titular_key="david", ...),
            property_classification_overrides={"prop-uuid": "residencia_principal"},
        )
        calc = PatrimonioCalculator(config)
        report = calc.calculate(
            PatrimonioInputs(
                baseline=...,
                investimentos_atuais=...,
                caixa_total_brl=...,
                caixa_detalhes=[...],
            )
        )
    """

    def __init__(self, config: PatrimonioConfig) -> None:
        self._config = config

    def calculate(self, inputs: PatrimonioInputs) -> dict[str, Any]:
        """Produz dict paridade com ``scripts/analyze_finances.analyze_patrimonio``."""
        identity = self._config.members
        inputs.members.afirma_coerencia_com(identity)
        titular_data, conjuge_data = inputs.members.as_tuple()

        total_bens_irpf = safe_float(titular_data.get("total_bens", 0)) + safe_float(
            conjuge_data.get("total_bens", 0)
        )
        total_dividas = self._sum_dividas(titular_data, conjuge_data)

        titular_bens = get_bens(titular_data)
        conjuge_bens = get_bens(conjuge_data)

        residencia, imoveis_investimento = self._split_imoveis(titular_bens, conjuge_bens)
        veiculos = self._sum_veiculos(titular_bens, conjuge_bens)

        investimentos_titular, investimentos_conjuge, fonte, ressalva = self._compute_investimentos(
            inputs,
            titular_bens,
            conjuge_bens,
            (titular_data.get("ano_base"), conjuge_data.get("ano_base")),
        )

        nao_atribuidos = float(ressalva.get("nao_atribuido") or 0.0)
        caixa_total_brl, caixa_detalhes = compute_caixa(
            inputs,
            total_bens_irpf=total_bens_irpf,
            residencia=residencia,
            imoveis_investimento=imoveis_investimento,
            veiculos=veiculos,
            investimentos_titular=investimentos_titular,
            investimentos_conjuge=investimentos_conjuge,
        )

        # ADR-142 + ADR-215 §6: split cat_2 antes das duas somas — a guarda vê os 8.
        imoveis_geradores, imoveis_nao_geradores = split_imoveis_geradores_vs_nao_geradores(
            titular_bens=titular_bens,
            conjuge_bens=conjuge_bens,
            overrides_by_property_id=self._config.property_classification_overrides or {},
        )
        guarda, investimentos_titular, investimentos_conjuge, caixa_total_brl = (
            aplicar_guarda_aos_componentes(
                residencia=residencia,
                imoveis_investimento=imoveis_investimento,
                veiculos=veiculos,
                investimentos_titular=investimentos_titular,
                investimentos_conjuge=investimentos_conjuge,
                caixa_total_brl=caixa_total_brl,
                imoveis_geradores=imoveis_geradores,
                imoveis_nao_geradores=imoveis_nao_geradores,
            )
        )
        total_dividas += float(guarda.dividas_curto_prazo_brl)

        patrimonio_bruto = self._compute_bruto(
            inputs,
            total_bens_irpf=total_bens_irpf,
            residencia=residencia,
            imoveis_investimento=imoveis_investimento,
            veiculos=veiculos,
            investimentos_titular=investimentos_titular,
            investimentos_conjuge=investimentos_conjuge,
            caixa=caixa_total_brl,
            nao_atribuidos=nao_atribuidos,
        )

        patrimonio_liquido = patrimonio_bruto - total_dividas
        # Regressão do #1550: o termo entrou no bruto e não aqui ([[ADR-412]] §D0).
        investivel_financeiro = max(
            0.0,
            investimentos_titular + investimentos_conjuge + caixa_total_brl + nao_atribuidos,
        )
        cat2_efetivo = self._compute_cat2_efetivo(
            titular_bens=titular_bens,
            conjuge_bens=conjuge_bens,
            imoveis_geradores_bruto=imoveis_geradores,
            valuation_context=inputs.valuation_context,
        )
        investivel_efetivo = max(0.0, investivel_financeiro + cat2_efetivo)

        composicao = build_composicao(
            identity=self._config.members,
            residencia=residencia,
            imoveis_investimento=imoveis_investimento,
            investimentos_titular=investimentos_titular,
            investimentos_conjuge=investimentos_conjuge,
            caixa=caixa_total_brl,
            veiculos=veiculos,
            nao_atribuidos=nao_atribuidos,
        )

        cobertura = ressalva["cobertura"]
        caixa_me_detalhe = build_caixa_me_detalhe(inputs.baseline)
        caixa_me_brl = caixa_me_from_detalhes(caixa_detalhes)
        wise_fiscal_flags = inputs.baseline.get("wise_fiscal_flags") or []
        # A33.l2 (P4, co-design product-designer 2026-07-07) — card S1
        # "posição por instituição/moeda": informe 31/12 + extrato não coberto.
        posicao_31_12 = build_posicao_31_12(inputs.baseline, caixa_detalhes)
        cbe_obrigatorio = any(f.get("code") == "CBE" for f in wise_fiscal_flags)

        return {
            "bruto": round(patrimonio_bruto, 2),
            "dividas": round(total_dividas, 2),
            "liquido": round(patrimonio_liquido, 2),
            "residencia": round(residencia, 2),
            "imoveis_investimento": round(imoveis_investimento, 2),
            "imoveis_geradores": round(imoveis_geradores, 2),
            "imoveis_nao_geradores": round(imoveis_nao_geradores, 2),
            identity.key_inv_titular: valor_publicavel(investimentos_titular, cobertura, "titular"),
            identity.key_inv_conjuge: valor_publicavel(investimentos_conjuge, cobertura, "conjuge"),
            # CTO-02: `caixa_total_brl` guarda o caixa TOTAL (BRL + ME); o ME
            # real fica em `caixa_me_brl`. Alias legado removido em CTO-08
            # (A37.l15); leitores de artefatos antigos mantêm fallback próprio.
            "caixa_total_brl": round(caixa_total_brl, 2),
            "caixa_me_brl": round(caixa_me_brl, 2),
            "caixa_detalhes": caixa_detalhes,
            "caixa_me_detalhe": caixa_me_detalhe,
            "wise_fiscal_flags": wise_fiscal_flags,
            "posicao_31_12": posicao_31_12,
            "cbe_obrigatorio": cbe_obrigatorio,
            "investivel_financeiro": round(investivel_financeiro, 2),
            "investivel_efetivo": round(investivel_efetivo, 2),
            "imoveis_no_if": self._config.include_real_estate_in_if,
            "veiculos": round(veiculos, 2),
            "composicao": composicao,
            "tabela_categorias": composicao,
            "fonte_investimentos": fonte,
            # ADR-346 (A39.l9): ressalva de PL quando há posição RV sem valor de
            # mercado não coberta por IRPF — PL renderizado, mas não "certificado".
            "guarda_de_sinal": guarda.to_dict(),
            "investimentos_nao_atribuidos": round(nao_atribuidos, 2),
            **publicar_bases(
                {
                    "investimentos_titular": investimentos_titular,
                    "investimentos_conjuge": investimentos_conjuge,
                    "investimentos_nao_atribuidos": nao_atribuidos,
                    "caixa_total_brl": caixa_total_brl,
                    "carteira_financeira_familia": investivel_financeiro,
                    "cat2_efetivo": cat2_efetivo,
                    "bruto": patrimonio_bruto,
                    "dividas": total_dividas,
                }
            ),
            "cobertura_investimentos": [c.to_dict() for c in cobertura],
            "pl_ressalva": ressalva["pl_ressalva"],
            "posicoes_sem_marcacao": ressalva["posicoes_sem_marcacao"],
        }

    # -------------------------------------------------------------------------
    # Steps
    # -------------------------------------------------------------------------

    def _compute_cat2_efetivo(
        self,
        *,
        titular_bens: dict,
        conjuge_bens: dict,
        imoveis_geradores_bruto: float,
        valuation_context: RealEstateValuationContext | None,
    ) -> float:
        """Cat_2 efetivo no IF (ADR-227 §D3) — bruto se sem context, líquido econômico se com."""
        if not self._config.include_real_estate_in_if:
            return 0.0
        if valuation_context is None:
            return imoveis_geradores_bruto
        overrides = self._config.property_classification_overrides or {}
        imoveis = (titular_bens.get("imoveis") or []) + (conjuge_bens.get("imoveis") or [])
        return float(sum_imoveis_geradores_liquidos(imoveis, overrides, valuation_context))

    @staticmethod
    def _sum_dividas(titular_data: dict, conjuge_data: dict) -> float:
        return safe_float(
            titular_data.get("total_dividas", titular_data.get("dividas", 0))
        ) + safe_float(conjuge_data.get("total_dividas", conjuge_data.get("dividas", 0)))

    def _split_imoveis(self, titular_bens: dict, conjuge_bens: dict) -> tuple[float, float]:
        """Separa residencia_principal vs demais imóveis (ADR-145 cat_1/cat_2)."""
        return split_imoveis_with_overrides(
            titular_bens=titular_bens,
            conjuge_bens=conjuge_bens,
            overrides_by_property_id=self._config.property_classification_overrides or {},
        )

    @staticmethod
    def _sum_veiculos(titular_bens: dict, conjuge_bens: dict) -> float:
        total = 0.0
        for v in titular_bens.get("veiculos", []) or []:
            total += veiculo_valor(v)
        for v in conjuge_bens.get("veiculos", []) or []:
            total += veiculo_valor(v)
        return total

    def _compute_investimentos(
        self,
        inputs: PatrimonioInputs,
        titular_bens: dict,
        conjuge_bens: dict,
        anos: tuple[str | None, str | None] = (None, None),
    ) -> tuple[float, float, str, dict]:
        """Investimentos por membro + fonte (ADR-145 cat. 3 e 4).

        Prefere ``investimentos_atuais`` (E2-llm) sobre fallback IRPF. Posição
        cujo membro o resolver não canonicalizou sai em ``nao_atribuido``, nunca
        no balde do titular (ADR-394 §D8). ``anos`` é o ano-base de cada membro
        e vira o ``frescor`` da cobertura. FIC FIM com nome de crypto fica aqui.
        """
        identity = self._config.members
        ano_titular, ano_conjuge = anos

        if inputs.has_current_positions:
            assert inputs.investimentos_atuais is not None  # narrow para type-checker
            carteira = inputs.carteira
            titular_val = float(carteira[PapelMembro.titular].total_brl)
            conjuge_val = float(carteira[PapelMembro.conjuge].total_brl)
            titular_atribuido = carteira[PapelMembro.titular].atribuido
            conjuge_atribuido = carteira[PapelMembro.conjuge].atribuido

            titular_fb = False
            conjuge_fb = False
            if titular_val == 0:
                irpf_titular = investimentos_from_irpf(
                    titular_bens, extras=("saldo_corretora", "moeda_estrangeira", "outros")
                )
                if irpf_titular > 0:
                    titular_val = irpf_titular
                    titular_fb = True
            if identity.conjuge_key and conjuge_val == 0:
                irpf_conjuge = investimentos_from_irpf(conjuge_bens, extras=("outros",))
                if irpf_conjuge > 0:
                    conjuge_val = irpf_conjuge
                    conjuge_fb = True

            sem = inputs.investimentos_atuais.get("posicoes_sem_marcacao_por_membro", {})
            ressalva = rv_ressalva(sem, identity, titular_fb=titular_fb, conjuge_fb=conjuge_fb)
            fonte = "posicoes_atuais+irpf" if (titular_fb or conjuge_fb) else "posicoes_atuais"
            ressalva["nao_atribuido"] = float(carteira[PapelMembro.sem_dono].total_brl)
            ressalva["cobertura"] = cobertura_de_membros(
                tem_conjuge=bool(identity.conjuge_key),
                titular=(titular_val, titular_atribuido, titular_fb, ano_titular),
                conjuge=(conjuge_val, conjuge_atribuido, conjuge_fb, ano_conjuge),
            )
            return titular_val, conjuge_val, fonte, ressalva

        # Fallback IRPF
        titular_val = investimentos_from_irpf(
            titular_bens, extras=("saldo_corretora", "moeda_estrangeira", "outros")
        )
        conjuge_val = investimentos_from_irpf(conjuge_bens, extras=("outros",))
        ressalva = rv_ressalva({}, identity, titular_fb=True, conjuge_fb=True)
        ressalva["nao_atribuido"] = 0.0
        ressalva["cobertura"] = cobertura_de_membros(
            tem_conjuge=bool(identity.conjuge_key),
            titular=(titular_val, False, titular_val > 0, ano_titular),
            conjuge=(conjuge_val, False, conjuge_val > 0, ano_conjuge),
        )
        return titular_val, conjuge_val, "irpf", ressalva

    @staticmethod
    def _compute_bruto(
        inputs: PatrimonioInputs,
        *,
        total_bens_irpf: float,
        residencia: float,
        imoveis_investimento: float,
        veiculos: float,
        investimentos_titular: float,
        investimentos_conjuge: float,
        caixa: float,
        nao_atribuidos: float = 0.0,
    ) -> float:
        """Patrimônio bruto: recompõe de fontes mistas (posições atuais)
        ou pega direto do IRPF total (fallback)."""
        if inputs.has_current_positions:
            return (
                residencia
                + imoveis_investimento
                + veiculos
                + investimentos_titular
                + investimentos_conjuge
                + caixa
                + nao_atribuidos
            )
        return total_bens_irpf
