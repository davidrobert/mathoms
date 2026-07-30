# report-review — rubrica de julgamento

Critério de julgamento carregado sob demanda pela skill [[report-review]]. O
**procedimento** (passos, ambiente, entregável) vive no `SKILL.md`; aqui está só
**contra o que se julga**.

## As 8 perguntas de produto

O eixo desta skill não é saúde de pipeline — é **mérito para a família que recebe o
relatório**. Toda pergunta tem de sair da rodada com resposta ou com "sem cobertura,
porque X".

| # | Pergunta | O que a torna respondida |
|---|---|---|
| **Q1** | O relatório **atende** a família? | Os pilares que o produto promete estão presentes e populados; o que está vazio está vazio por ausência de dado, não por defeito de entrega |
| **Q2** | Está **claro e preciso**? | Nenhum número exibido está errado; rótulo, janela temporal e base de cada percentual são declarados; nada de jargão de implementação |
| **Q3** | A **usabilidade** está boa? | Ordem de leitura leva à decisão; navegação sem alvo morto; uma resposta única para "o que faço agora" |
| **Q4** | Reflete as **metodologias** de referência? | As regras de domínio codificadas batem com a ADR canônica de cada conceito; divergência é decisão registrada, não drift |
| **Q5** | As **sugestões e acionáveis** estão corretos e completos? | O motor de sugestões produz itens; eles chegam à superfície onde o plano de ação vive; nada urgente fica só em prosa |
| **Q6** | A **principal recomendação** é a certa? | Direção **e** ordenação. Ver §Braço cego |
| **Q7** | **Falta algo**? | Campos do payload sem consumidor; seções sem olhar; dado gerado que não chega à tela |
| **Q8** | Outros | O que não coube acima e o revisor considera material |

**Q5 tem uma armadilha conhecida:** o plano de ação costuma viver em superfície com
endpoint próprio, fora do payload do relatório. Medir só o payload responde a pergunta
errada — abra a superfície real.

## Dimensões (para a coluna do MOC)

`correção` · `consistência` · `completude` · `clareza-ux` · `solidez-financeira` ·
`qualidade-llm` · `saúde-execução`

Mesma taxonomia de [[PIPELINE-REVIEWS-active]], para que um achado migre entre os dois
registros sem re-rotular.

## Severidade

| Severidade | Critério |
|---|---|
| **Crítico** | Número exibido está errado, ou a família decide errado por causa disso |
| **Alto** | Omite pilar, inverte leitura, ou expõe o que não devia; sem número errado |
| **Médio** | Rótulo/base/janela ambíguos; erosão de confiança sem decisão corrompida |
| **Baixo** | Cosmético, ou latente (só morde numa configuração que ainda não ocorre) |

**Regra de calibração:** severidade mede o dano **ao usuário**, não o quão feio é o
código. Defeito estrutural grave cujo efeito é invisível na tela é `inerte` (abaixo),
não `Crítico`.

## Prioridade

`P0` fecha antes do próximo relatório sair · `P1` fecha no sprint corrente ·
`P2` entra na fila · `P3` quando sobrar. Prioridade ≠ severidade: um `Alto` de
esforço S que fecha três achados vence um `Crítico` de risco médio na ordem de ataque.

## Vereditos do cético

| Veredito | Quando |
|---|---|
| `CONFIRMADO` | Tentou refutar por ≥2 caminhos e o núcleo sobreviveu inteiro |
| `PARCIAL` | Núcleo procede, mas ≥1 sub-afirmação caiu **e o cético diz qual** |
| `REFUTADO` | O núcleo caiu — o achado não procede como descrito |

E três campos que não são veredito mas mudam o que se faz com o achado:

- **`triagem`** — `NOVO` · `JÁ-CONHECIDO` (já registrado e aberto num MOC) ·
  `MEDIÇÃO-DE-CONHECIDO` (o defeito já estava registrado; esta rodada mediu a
  magnitude pela primeira vez). Sem isso a rodada infla o placar re-descobrindo.
- **`inerte_para_usuario`** — defeito real que **não alcança o usuário** nesta
  configuração (seção desabilitada, campo sem consumidor, texto que não renderiza).
  Inerte não entra na fila de prioridade, mas **é reavaliado** quando o achado que o
  torna inerte fechar — inerte é estado, não veredito.
- **`severidade_corrigida`** — a do cético, que substitui a da lente.

### Calibração dura

Taxa de `REFUTADO` **igual a zero** numa rodada é tripwire do método, não prova de que
os achados eram bons: significa que o passo cético calibrou para carimbar. Nesse caso:

1. Cético que não conseguiu refutar **declara qual medição faria a refutação**.
2. `PARCIAL` sem rebaixamento medido de severidade é smell — ou ele mediu e rebaixou,
   ou ele não tentou.
3. Refutação **escopada** (derrubou um termo de uma afirmação de dois) é `PARCIAL`, e
   o cético tem de dizer qual termo sobreviveu. Vender escopada como total é o erro
   que faz um defeito vivo parecer resolvido.

## Braço cego (só para Q6)

Um agente lê **apenas** os dados determinísticos — sem o parecer LLM — e responde
sozinho: qual é a recomendação nº 1, com sizing e três argumentos de ordenação.

| Resultado | Leitura |
|---|---|
| Converge com o parecer | **Direção sustentada** — melhor sinal disponível para Q6 |
| Diverge | **É o achado**: ou o parecer errou, ou o determinístico não vê algo |

Convergência **não** valida a ordenação. Para a ordenação valer, tem de existir um
critério de prioridade **encodado e auditável**; se a ordem sai só do julgamento de
dois braços que compartilham a mesma persona, o veredito honesto de Q6 é
**"direção sim, ordenação indeterminada"**, e a rodada tem de listar o que falta para
determiná-la.

## Gates de cobertura da própria rodada

Verificados no Passo 4 e auditados no Passo 6:

| Gate | Falha quando |
|---|---|
| Cobertura de lente | Alguma lente declarada não aparece no campo `lentes` de nenhum cluster |
| Disposição de achado | Existe achado vivo sem cluster e sem descarte com motivo escrito |
| Cobertura de seção | Seção do relatório sem menção em nenhum cluster |
| Fechamento por medição | Nenhum claim pivotal foi fechado por comando determinístico |
| Rótulo de não-observado | Afirmação de clareza/usabilidade sem dizer que é inferência de código |

## O que não é achado desta skill

- Saúde de execução do run (duração, custo, retries) → [[pipeline-review]]
- Documento que virou artefato errado na ingestão → [[parse-certify]]
- Transação perdida ou duplicada no razão → [[ledger-certify]]

Se a rodada tropeçar num desses, **registre no MOC da skill vizinha**, não neste.
