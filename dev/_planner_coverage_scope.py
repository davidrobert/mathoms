"""Universo declarado de folhas do E5 que NÃO são projetadas ao parecer.

Extraído de ``dev/_planner_coverage_internals.py`` em 2026-09-01: o módulo estava
em 499 linhas — uma abaixo do teto P2 de 500 —, então QUALQUER entrada nova aqui
reprovava o gate de code style. Duas mudanças independentes colidiram nesse teto
no mesmo dia. Declarar exceção é o uso normal deste dict, e o uso normal não pode
custar um refactor a cada vez.
"""

from __future__ import annotations

E5_FIELDS_FORA_DO_PARECER: dict[str, str] = {
    "$._lineage": "rastro de proveniência do pipeline — insumo de debug, não de conselho",
    # [[ADR-420]] §D1/§D6: TERMOS de razão, não conclusões. O parecer já recebe as duas
    # conclusões que eles produzem — a concentração e `imobilizacao_patrimonial_pct` (§D3,
    # criado para o ativo fora-de-alocação não sumir da superfície de risco).
    "$.patrimonio.imoveis_alocacao": "termo do numerador; o parecer recebe a razão",
    "$.patrimonio.imoveis_fora_alocacao": "termo fora do numerador; chega por §D3",
    # [[A40.l114]]: extremo, como as bases acima; já redundante via `classificacao`.
    "$.score.piso": "extremo conservador do score; a `classificacao` projetada já deriva dele",
    "$.narrativas": "texto já destilado em outra superfície; projetá-lo duplicaria prosa",
    "$.protection_computation_inputs_v1": "insumos crus do cálculo de proteção; o parecer lê o resultado",
    # A40.l80 ([[ADR-412]] §D0): base que AMPUTA a fatia sem titular. Ambas têm
    # `publicavel_sozinha() is False` — só valem como extremo inferior de um
    # intervalo declarado. Projetá-las cruas convidaria o modelo a citar o número
    # amputado como se fosse o patrimônio da família, que é o defeito da lane.
    # O parecer recebe o INTERVALO e o motivo, não a ponta.
    "$.patrimonio.bases.carteira_com_titular_identificado": (
        "extremo conservador de intervalo; o parecer recebe o intervalo, nunca a ponta amputada"
    ),
    "$.patrimonio.bases.carteira_produtiva_com_titular_identificado": (
        "extremo conservador de intervalo; o parecer recebe o intervalo, nunca a ponta amputada"
    ),
    # A40.l80 §Completude: esta base existe para AUDITAR o denominador da
    # concentração ([[ADR-340]]) — o parecer já recebe `ratios.concentracao_imobiliaria`
    # e o hint que nomeia a base. O valor cru é rastro de auditoria do gate
    # `tests/test_cobertura_de_base.py`, não insumo de conselho; projetá-lo daria ao
    # modelo um segundo número de "carteira produtiva" para confundir com o primeiro,
    # que é exatamente o defeito que declarar a base foi feito para matar.
    # A40.l80 §Completude: rótulo de auditoria da base do pct — o manifest já entrega o
    # pct com a base nomeada na própria label (#1780). Projetar o campo daria ao modelo um
    # segundo lugar de onde tirar o mesmo nome.
    # A40.l80: termo de base publicado para tornar o bloco `bases` auditável só do
    # payload. É rastro de auditoria, não insumo de conselho — o parecer recebe o
    # patrimônio, não os termos que somam cada denominador.
    "$.patrimonio.cat2_efetivo": (
        "termo de base; rastro de auditoria do bloco `bases`, não insumo de conselho"
    ),
    "$.exposicao_cambial.base_pct_investivel_financeiro": (
        "rótulo de auditoria; a label do pct já nomeia a base ao modelo"
    ),
    "$.patrimonio.bases.carteira_produtiva_fixa": (
        "rastro de auditoria do denominador da concentração; o parecer recebe a razão"
    ),
    # 2026-09-01 ([[ADR-236]] §D5): declarar a raiz no schema a trouxe para este gate.
    "$.tributario": "bloco fiscal nunca projetado ao parecer; declaração registra o status quo",
    # [[ADR-439]]: os três baldes já existiam no payload e o parecer nunca os recebeu;
    # declará-los no schema (para aceitarem `null`) os trouxe para este gate. Desde a
    # [[A40.l123]] o parecer recebe o VEREDITO de cada balde, não o número: `residencia` e
    # `imoveis_geradores` não são chave monetária pelo nome, então em `brl` virariam folha
    # R$ visível sem rota de citação — e o modelo passaria a fazer conta com eles.
    "$.patrimonio.residencia": "o parecer recebe o veredito do balde, não o número",
    "$.patrimonio.imoveis_geradores": "idem — o veredito do par chega pelo bloco de cobertura",
    "$.patrimonio.imoveis_nao_geradores": "idem — par de `imoveis_geradores`",
    # [[A40.l123]]: do bloco, o parecer recebe a fatia (%) e os vereditos; o resto fica aqui.
    "$.patrimonio.cobertura_classificacao_imovel.valor_total": (
        "termo R$ da partição; a ressalva usa a fatia em %, não o valor"
    ),
    "$.patrimonio.cobertura_classificacao_imovel.valor_desconhecido": "idem",
    "$.patrimonio.cobertura_classificacao_imovel.residencia_identificada": (
        "idem; o parecer recebe o veredito da residência"
    ),
    "$.patrimonio.cobertura_classificacao_imovel.geradores_identificados": (
        "idem; um segundo número de renda de imóvel ao lado da IF convidaria a recalculá-la"
    ),
    "$.patrimonio.cobertura_classificacao_imovel.nao_geradores_identificados": "idem",
    "$.patrimonio.cobertura_classificacao_imovel.n_total": (
        "contagem; a fatia que decide é de VALOR ([[ADR-433]] §D3)"
    ),
    "$.patrimonio.cobertura_classificacao_imovel.n_desconhecido": "idem",
    "$.patrimonio.cobertura_classificacao_imovel.n_desconhecido_em_aberto": (
        "idem; imóvel sem valor apurado já chega ao parecer pela tabela `itens_sem_valor`"
    ),
    "$.patrimonio.cobertura_classificacao_imovel.overrides_sem_imovel": (
        "escolhe o motivo, nunca o veredito; o parecer recebe o motivo"
    ),
    "$.patrimonio.cobertura_classificacao_imovel.residencia_status": (
        "eco do cadastro ([[ADR-215]]); o veredito da residência já carrega o que o conselho usa"
    ),
    # [[ADR-444]] D8 (expand→contract): o escalar entra no contrato ANTES do produtor, que só
    # o emite no flip — e é no flip, com o bump do manifest, que ele passa a ser projetado.
    "$.investimentos.total_imoveis_uso_nao_apurado": (
        "declarado antes do produtor (expand); o flip da ADR-444 o projeta e o tira daqui"
    ),
}
