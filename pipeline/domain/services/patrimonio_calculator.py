"""``PatrimonioCalculator`` — composição patrimonial completa (A6d.3.3 — ADR-100).

Substitui ``scripts/e5_analyze.analyze_patrimonio`` por um serviço puro:
- Zero globals; recebe :class:`PatrimonioConfig` com identidade + keyword.
- Zero I/O; o adapter carrega baseline + investimentos_atuais + caixa E3 e
  monta :class:`PatrimonioInputs`.
- Produz o mesmo ``dict`` que ``analyze_patrimonio`` (paridade byte-a-byte
  exceto por prints debug que não fazem parte do contrato).

Segue o **mesmo contrato de saída** do legado — o dict é consumido por:
- ``scripts/e5_analyze.analyze_ratios`` (campos ``bruto``, ``investivel``,
  ``dividas``, ``residencia``, ``veiculos``).
- ``config/report_layout.yaml`` via ``analise_financeira-5_analysis.json``.
- ``scripts/e5n_narrativas.build_narrativas`` (campos ``composicao``,
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
   ``taxas.json``). Ver :meth:`PatrimonioCalculator._compute_caixa` e
   ``scripts/e5_analyze._load_caixa_from_e3_saldos``.
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
from pipeline.domain.services.patrimonio_resolvers import resolve_members
from pipeline.domain.services.patrimonio_types import (
    PatrimonioConfig,
    PatrimonioInputs,
    RealEstateValuationContext,
    get_bens,
    investimento_valor,
    safe_float,
    veiculo_valor,
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
        """Produz dict paridade com ``scripts/e5_analyze.analyze_patrimonio``."""
        identity = self._config.members

        titular_data, conjuge_data = resolve_members(inputs.baseline, identity)

        total_bens_irpf = safe_float(titular_data.get("total_bens", 0)) + safe_float(
            conjuge_data.get("total_bens", 0)
        )
        total_dividas = self._sum_dividas(titular_data, conjuge_data)

        titular_bens = get_bens(titular_data)
        conjuge_bens = get_bens(conjuge_data)

        residencia, imoveis_investimento = self._split_imoveis(titular_bens, conjuge_bens)
        veiculos = self._sum_veiculos(titular_bens, conjuge_bens)

        investimentos_titular, investimentos_conjuge, fonte = self._compute_investimentos(
            inputs, titular_bens, conjuge_bens
        )

        caixa_moeda_estrangeira, caixa_detalhes = self._compute_caixa(
            inputs,
            total_bens_irpf=total_bens_irpf,
            residencia=residencia,
            imoveis_investimento=imoveis_investimento,
            veiculos=veiculos,
            investimentos_titular=investimentos_titular,
            investimentos_conjuge=investimentos_conjuge,
        )

        patrimonio_bruto = self._compute_bruto(
            inputs,
            total_bens_irpf=total_bens_irpf,
            residencia=residencia,
            imoveis_investimento=imoveis_investimento,
            veiculos=veiculos,
            investimentos_titular=investimentos_titular,
            investimentos_conjuge=investimentos_conjuge,
            caixa_moeda_estrangeira=caixa_moeda_estrangeira,
        )

        patrimonio_liquido = patrimonio_bruto - total_dividas
        # ADR-142 + ADR-215 §6: split cat_2 por classification para honrar a
        # invariante anti-dupla-contagem em ``investivel_efetivo``.
        imoveis_geradores, imoveis_nao_geradores = split_imoveis_geradores_vs_nao_geradores(
            titular_bens=titular_bens,
            conjuge_bens=conjuge_bens,
            overrides_by_property_id=self._config.property_classification_overrides or {},
        )
        investivel_financeiro = max(
            0.0,
            investimentos_titular + investimentos_conjuge + caixa_moeda_estrangeira,
        )
        cat2_efetivo = self._compute_cat2_efetivo(
            titular_bens=titular_bens,
            conjuge_bens=conjuge_bens,
            imoveis_geradores_bruto=imoveis_geradores,
            valuation_context=inputs.valuation_context,
        )
        investivel_efetivo = max(0.0, investivel_financeiro + cat2_efetivo)

        composicao = self._build_composicao(
            residencia=residencia,
            imoveis_investimento=imoveis_investimento,
            investimentos_titular=investimentos_titular,
            investimentos_conjuge=investimentos_conjuge,
            caixa_moeda_estrangeira=caixa_moeda_estrangeira,
            veiculos=veiculos,
        )

        return {
            "bruto": round(patrimonio_bruto, 2),
            "dividas": round(total_dividas, 2),
            "liquido": round(patrimonio_liquido, 2),
            "residencia": round(residencia, 2),
            "imoveis_investimento": round(imoveis_investimento, 2),
            "imoveis_geradores": round(imoveis_geradores, 2),
            "imoveis_nao_geradores": round(imoveis_nao_geradores, 2),
            identity.key_inv_titular: round(investimentos_titular, 2),
            identity.key_inv_conjuge: round(investimentos_conjuge, 2),
            "caixa_moeda_estrangeira": round(caixa_moeda_estrangeira, 2),
            "caixa_detalhes": caixa_detalhes,
            "investivel_financeiro": round(investivel_financeiro, 2),
            "investivel_efetivo": round(investivel_efetivo, 2),
            "imoveis_no_if": self._config.include_real_estate_in_if,
            "veiculos": round(veiculos, 2),
            "composicao": composicao,
            "tabela_categorias": composicao,
            "fonte_investimentos": fonte,
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
    ) -> tuple[float, float, str]:
        """Calcula investimentos por membro + fonte.

        Implementa as categorias 3 e 4 de ADR-145 (Investimentos {TITULAR}
        e Investimentos {CONJUGE}). Prefere ``investimentos_atuais``
        (posições atuais E2-llm) sobre fallback IRPF. Posições sem membro
        atribuído (``""``) vão para o titular (convenção legado).

        Fundos regulados (FIC FIM) com nome sugerindo crypto seguem aqui —
        ADR-145: "fundo FIC FIM não é crypto direta".
        """
        identity = self._config.members

        if inputs.has_current_positions:
            assert inputs.investimentos_atuais is not None  # narrow para type-checker
            totais = inputs.investimentos_atuais.get("total_por_membro", {}) or {}

            titular_val = 0.0
            conjuge_val = 0.0
            unattributed = 0.0
            for member_key, value in totais.items():
                v = safe_float(value)
                key_lower = str(member_key).lower()
                if not key_lower:
                    unattributed += v
                elif identity.titular_key and identity.titular_key in key_lower:
                    titular_val += v
                elif identity.conjuge_key and identity.conjuge_key in key_lower:
                    conjuge_val += v
                else:
                    unattributed += v
            if unattributed > 0:
                titular_val += unattributed

            fallback_used = False
            if titular_val == 0:
                irpf_titular = self._investimentos_from_irpf(
                    titular_bens, extras=("saldo_corretora", "moeda_estrangeira", "outros")
                )
                if irpf_titular > 0:
                    titular_val = irpf_titular
                    fallback_used = True
            if identity.conjuge_key and conjuge_val == 0:
                irpf_conjuge = self._investimentos_from_irpf(conjuge_bens, extras=("outros",))
                if irpf_conjuge > 0:
                    conjuge_val = irpf_conjuge
                    fallback_used = True

            fonte = "posicoes_atuais+irpf" if fallback_used else "posicoes_atuais"
            return titular_val, conjuge_val, fonte

        # Fallback IRPF
        titular_val = self._investimentos_from_irpf(
            titular_bens, extras=("saldo_corretora", "moeda_estrangeira", "outros")
        )
        conjuge_val = self._investimentos_from_irpf(conjuge_bens, extras=("outros",))
        return titular_val, conjuge_val, "irpf"

    @staticmethod
    def _investimentos_from_irpf(bens: dict, *, extras: tuple[str, ...]) -> float:
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

    @staticmethod
    def _compute_caixa(
        inputs: PatrimonioInputs,
        *,
        total_bens_irpf: float,
        residencia: float,
        imoveis_investimento: float,
        veiculos: float,
        investimentos_titular: float,
        investimentos_conjuge: float,
    ) -> tuple[float, list]:
        """Caixa + ME.

        Com posições atuais, o adapter carregou o total + detalhes de E3;
        sem, calcula residualmente sobre o IRPF (floor zero).
        """
        if inputs.has_current_positions:
            caixa = max(0.0, inputs.caixa_total_brl)
            detalhes = [d.to_dict() for d in inputs.caixa_detalhes]
            return caixa, detalhes

        residual = (
            total_bens_irpf
            - residencia
            - imoveis_investimento
            - veiculos
            - investimentos_titular
            - investimentos_conjuge
        )
        return max(0.0, residual), []

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
        caixa_moeda_estrangeira: float,
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
                + caixa_moeda_estrangeira
            )
        return total_bens_irpf

    def _build_composicao(
        self,
        *,
        residencia: float,
        imoveis_investimento: float,
        investimentos_titular: float,
        investimentos_conjuge: float,
        caixa_moeda_estrangeira: float,
        veiculos: float,
    ) -> list[dict]:
        """Monta as 6 categorias visíveis + percentuais via largest-remainder
        (soma=100%).

        Categorias retornadas — paridade legado, materializa 6 das 7 buckets
        de ADR-145: Residência (#1), Imóveis Investimento (#2), Investimentos
        Titular (#3), Investimentos Cônjuge (#4), Caixa + ME (#6), Veículos
        (#7). Bucket #5 (Criptoativos) consolida em #3/#6 conforme regra de
        ADR-145 (crypto direta IRPF → bucket investimentos do titular;
        Hashdex/FIC FIM → bucket investimentos titular). Quando o pipeline
        recebe extratos de exchange (Binance), a separação visual aparece
        no doughnut de ``investimentos_classes`` — não nesta composição.
        """
        identity = self._config.members
        # ADR-215 P3: rename visível do bucket cat_2 — "Imóveis Investimento"
        # → "Imóveis de Renda". Comunica o critério econômico real (geração de
        # caixa). `template_key` interno (`imoveis_investimento`) é estável
        # ([[ADR-145]] proíbe rename de key); só o label exibido muda.
        composicao = [
            {"categoria": "Residência", "valor": residencia},
            {"categoria": "Imóveis de Renda", "valor": imoveis_investimento},
            {
                "categoria": f"Investimentos {identity.titular_nome}",
                "valor": investimentos_titular,
            },
            {
                "categoria": f"Investimentos {identity.conjuge_nome}",
                "valor": investimentos_conjuge,
            },
            {"categoria": "Caixa e Moeda Estrangeira", "valor": caixa_moeda_estrangeira},
            {"categoria": "Veículos", "valor": veiculos},
        ]
        self._apply_percentuals_largest_remainder(composicao)
        composicao.sort(key=lambda x: x["valor"], reverse=True)
        return composicao

    @staticmethod
    def _apply_percentuals_largest_remainder(composicao: list[dict]) -> None:
        """Aplica percentuais usando o método do maior resto (soma exata = 100%).

        Mutates ``composicao`` in-place adicionando ``pct`` em cada entry.
        Quando total = 0, atribui pct = 0.0 para todos.
        """
        total_nonzero = sum(c["valor"] for c in composicao)
        if total_nonzero <= 0:
            for comp in composicao:
                comp["pct"] = 0.0
            return

        raw_pcts = [(c["valor"] / total_nonzero) * 100 for c in composicao]
        floored = [int(p * 100) / 100.0 for p in raw_pcts]
        remainders = [(raw_pcts[i] - floored[i], i) for i in range(len(composicao))]
        remainder_sum = round(100.0 - sum(floored), 2)
        steps = int(round(remainder_sum / 0.01))
        remainders.sort(key=lambda x: -x[0])
        for j in range(min(steps, len(remainders))):
            floored[remainders[j][1]] += 0.01
        for i, comp in enumerate(composicao):
            comp["pct"] = round(floored[i], 2)
