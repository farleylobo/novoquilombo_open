# Tecelagem — o método por trás do painel e do site

Base: June Holley (*Network Weaver Handbook*; Network Weaving Institute) e Valdis Krebs & June Holley
(*Building Smart Communities through Network Weaving*), com um toque de Richard Flyer (*Symbiotic Culture*):
organizar a rede em torno de **necessidades concretas**, não de afinidade.

## 1. Conheça a rede, depois teça a rede

O painel mede a rede a cada atualização (`rnq/rede.py`) e guarda a evolução em `_trabalho/historico-rede.json`.

| Métrica | O que diz | Meta |
|---|---|---|
| Pessoas conectadas | % com pelo menos uma ligação pessoa ↔ pessoa | subir sempre |
| Grupos separados | quantos "fragmentos" a rede tem | cair até 1 |
| Caminho médio | quantos passos, em média, entre duas pessoas | ≤ 3,5 |
| Dependência do hub | % das ligações que passam por você | < 30% |
| "Sem você, a rede viraria…" | o que acontece se você sair | rede continua inteira |
| Pontes (intermediação) | quem está no caminho entre os outros | candidatas a tecer junto |
| Ligações entre comunidades | pontes entre grupos diferentes | subir |

### Fases (Holley & Krebs)

| Fase | Como o painel reconhece | Prioridade |
|---|---|---|
| 1 · Fragmentos dispersos | menos de 40% das pessoas conectadas | apresentar pessoas isoladas a alguém com tema em comum |
| 2 · Hub-and-spoke | ≥ 30% das ligações passam pelo hub | apresentar pessoas entre si sem passar por você; formar tecelões |
| 3 · Multi-hub | conectada e pouco dependente do hub | fortalecer pontes entre comunidades |
| 4 · Núcleo e periferia | ≥ 75% conectadas, dependência < 15%, caminho ≤ 3,5 | trazer gente nova pela periferia; ligar a outras redes |

Em 06/10/2026 a RNQ está na **fase 1** (33% conectadas; 20% das ligações passam pelo Farley).

## 2. Apresentações sugeridas

"Conecte pela semelhança, ganhe com a diferença." Pontuação de cada par ainda não ligado:

| Critério | Pontos |
|---|---|
| Uma das pessoas pediu para conhecer a outra (perfil, "Gostaria de colaborar com") | +10 |
| Cada tema em comum | +3 |
| Comunidade em comum | +1 |
| Comunidades diferentes | +2 |
| Atuação diferente (ex.: corporativo × terceiro setor) | +2 |
| Ligaria dois grupos que hoje não se tocam | +3 |
| Traz alguém que ainda não tem nenhuma ligação | +2 |

Regras: precisa ter tema ou comunidade em comum (ou pedido explícito); **o hub nunca é sugerido**;
cada pessoa aparece no máximo 2 vezes por rodada; pares já registrados em **Apresentações** não voltam.

Cada sugestão vem com uma mensagem pronta para copiar. O impacto acontece nos níveis mais altos da
"pirâmide de apresentações" (Jack Ricchiuto): **apresentar, acompanhar e sugerir algo concreto para fazerem juntos**.

## 3. No site: todo mundo pode tecer

| Funcionalidade | Prática da June |
|---|---|
| **Mural de ofertas e pedidos** | Mercado de ofertas e necessidades; "o que você compartilharia / o que quer aprender" |
| "Na rede, quem trabalha com isso" (em cada pedido) | Fechar triângulos: a própria rede sugere quem pode ajudar |
| **Pode ser bom conhecer** (no card) | Sugestão pública de quem tem tema em comum e ainda não está ligado |
| **Eu conheço essa pessoa** | Mapeamento colaborativo: as pessoas desenham as ligações |
| **Atualizar meu perfil** | As perguntas da June: compartilhar, aprender, com quem colabora, com quem gostaria de colaborar, convocaria um grupo? |
| **Iniciativas** | Projetos colaborativos pequenos e auto-organizados; grupos de prática |
| **Papéis** | Conector, coordenador de projetos, facilitador, guardião |
| **Como participar** | "Todo mundo é um tecelão e pode ser um tecelão melhor" |

## 4. Dois riscos que o desenho evita

1. **Você virar gargalo** — o painel nunca sugere você, mede sua dependência e mostra quem são as pontes
   (candidatas a co-tecelãs). Dê papéis e acesso à planilha a 2 ou 3 pessoas.
2. **A rede virar um silo** — o mural aceita pedidos de quem ainda não está no mapa; as sugestões
   premiam diferença de comunidade e de atuação.

## Fontes

- [Network Weaver Handbook](https://networkweaver.com/product/network-weaver-handbook/)
- [Everyone a network weaver — entrevista com June Holley (Kumu)](https://blog.kumu.io/everyone-a-network-weaver-interview-with-june-holley-f0fd52b7573b)
- [June Holley's Network Weaving Institute](https://networkweaver.com/june-holleys-network-weaving-institute/)
- [Self-organizing case study](https://networkweaver.com/resources/self-organizing-case-study)
