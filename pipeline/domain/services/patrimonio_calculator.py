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
"""

from __future__ import annotations

from typing import Any

from pipeline.domain.services.patrimonio_resolvers import resolve_members
from pipeline.domain.services.patrimonio_types import (
    PatrimonioConfig,
    PatrimonioInputs,
    get_bens,
    imovel_desc,
    imovel_valor,
    investimento_valor,
    safe_float,
    veiculo_valor,
)


class PatrimonioCalculator:
    """Calcula patrimônio consolidado preservando paridade com ``analyze_patrimonio``.

    Uso::

        config = PatrimonioConfig(
            members=MemberIdentity(titular_key="david", ...),
            residencia_keyword="rua araújo alvim",
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
        investivel = max(0.0, patrimonio_bruto - residencia - veiculos)

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
            identity.key_inv_titular: round(investimentos_titular, 2),
            identity.key_inv_conjuge: round(investimentos_conjuge, 2),
            "caixa_moeda_estrangeira": round(caixa_moeda_estrangeira, 2),
            "caixa_detalhes": caixa_detalhes,
            "investivel": round(investivel, 2),
            "veiculos": round(veiculos, 2),
            "composicao": composicao,
            "tabela_categorias": composicao,
            "fonte_investimentos": fonte,
        }

    # -------------------------------------------------------------------------
    # Steps
    # -------------------------------------------------------------------------

    @staticmethod
    def _sum_dividas(titular_data: dict, conjuge_data: dict) -> float:
        return safe_float(
            titular_data.get("total_dividas", titular_data.get("dividas", 0))
        ) + safe_float(conjuge_data.get("total_dividas", conjuge_data.get("dividas", 0)))

    def _split_imoveis(self, titular_bens: dict, conjuge_bens: dict) -> tuple[float, float]:
        """Separa imóveis em residência principal (via keyword) vs investimento."""
        residencia = 0.0
        imoveis_investimento = 0.0
        keyword = (self._config.residencia_keyword or "").lower()

        for im in titular_bens.get("imoveis", []) or []:
            if keyword and keyword in imovel_desc(im):
                residencia = imovel_valor(im)
            else:
                imoveis_investimento += imovel_valor(im)

        # Cônjuge: todos os imóveis são investimento por convenção legado.
        for im in conjuge_bens.get("imoveis", []) or []:
            imoveis_investimento += imovel_valor(im)

        return residencia, imoveis_investimento

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

        Prefere ``investimentos_atuais`` (posições atuais E2-llm) sobre
        fallback IRPF. Posições sem membro atribuído (``""``) vão para o
        titular (convenção legado).
        """
        identity = self._config.members

        if inputs.has_current_positions:
            assert inputs.investimentos_atuais is not None  # narrow para type-checker
            totais = inputs.investimentos_atuais.get("total_por_membro", {}) or {}
            titular_val = safe_float(totais.get(identity.titular_key, 0))
            conjuge_val = (
                safe_float(totais.get(identity.conjuge_key, 0)) if identity.conjuge_key else 0.0
            )
            unattributed = safe_float(totais.get("", 0))
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
        """Monta as 6 categorias + percentuais via largest-remainder (soma=100%)."""
        identity = self._config.members
        composicao = [
            {"categoria": "Residência", "valor": residencia},
            {"categoria": "Imóveis Investimento", "valor": imoveis_investimento},
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
