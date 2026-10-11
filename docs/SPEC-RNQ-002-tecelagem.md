# SPEC-RNQ-002 · Tecelagem: mural, iniciativas, perfil e painel do tecelão

**Status:** Implementado no protótipo local (06/10/2026) — aguardando deploy (ver `docs/DEPLOY.md`)
**Depende de:** SPEC-RNQ-001 (visão pública)
**Base metodológica:** June Holley (*Network Weaver Handbook*), Holley & Krebs (fases de rede), Richard Flyer (organizar por necessidades)

## Problema
A RNQ está na **fase 1 · fragmentos dispersos**: 72 pessoas, só 33% com alguma ligação pessoa ↔ pessoa, e as ligações dependem do Farley.
Um mapa sozinho mostra a rede; não faz a rede **agir** nem **tecer a si mesma**.

## Objetivo
Dar à rede ferramentas para (1) as pessoas oferecerem e pedirem coisas concretas, (2) se apresentarem entre si, (3) fazerem juntas,
e (4) dar a quem tece um painel que diga **quem apresentar a quem** e **o quanto a rede ainda depende de uma pessoa**.

## Decisões (tomadas pelo Claude com autorização do Farley, 06/10)
| Decisão | Escolha | Por quê |
|---|---|---|
| Foco do mural | Aberto a qualquer área (temas + comunidades), com filtro | Rede ainda pequena; um foco único deixaria o mural vazio. Revisar quando houver volume |
| Quem pode publicar | Qualquer pessoa com o link (inclusive quem não está no mapa) | Evita silo; periferia é onde entra gente nova (Holley) |
| Moderação | Tudo passa por revisão, exceto saídas (RF8) | Mantém RF6 e confiança |
| Quem modera | Farley, com planilha pensada para 2–3 co-tecelões | Sair do hub-and-spoke |
| Infraestrutura | Continua estática + Netlify Forms; sincronização por API ou CSV | Sem banco, sem login, custo zero (RF1, RF9) |
| Sugestões de apresentação | Privadas (painel); sugestão pública só "Pode ser bom conhecer" com dados já públicos | Sugerir pares publicamente seria invasivo |
| Exemplos | Modo `?demo=1` com itens fictícios rotulados | Nunca atribuir ofertas inventadas a pessoas reais |
| Correções de dados | Aba Correções (não edita a planilha de seleção) | Preserva as validações do Excel do Farley |

## Escopo entregue
1. **Mural de ofertas e pedidos** — publicar (tipo, título ≤ 90, descrição ≤ 420, até 3 áreas, nome, contato privado, concordância);
   filtros por tipo, área, busca e atendidos; "Na rede, quem trabalha com isso" em pedidos; "Posso ajudar / Tenho interesse".
2. **Iniciativas** — projeto, encontro ou grupo de prática; participantes (só pessoas do mapa), "precisa de", proponente; "Quero participar"; "Propor iniciativa".
3. **Perfil** ("Atualizar meu perfil", no card) — posso compartilhar, quero aprender, toparia convocar (públicos após revisão);
   já colaboro com (vira ligação); gostaria de colaborar com (privado, alimenta sugestões).
4. **Card** — papéis na rede, perfil, itens no mural, iniciativas, "Pode ser bom conhecer" (até 3, tema em comum, não ligadas, sem o hub).
5. **Como participar** — guia em 4 passos ("todo mundo pode tecer").
6. **Planilha de tecelagem** (11 abas) e **sincronização** dos 8 formulários do Netlify.
7. **Painel do tecelão** (local, privado) — fase da rede, dependência do hub, "sem você a rede viraria…", evolução,
   fila de moderação, 15 apresentações sugeridas com mensagem pronta, funil de apresentações, pedidos sem resposta, pontes, isolados, avisos.
8. **Papéis** (Conector, Coordenador de projetos, Facilitador, Guardião) e **Correções** (nome, cargo, organização, LinkedIn).

**Fora do escopo (v3+):** login; edição direta pela pessoa; notificações automáticas por e-mail/WhatsApp; micro-fundo para iniciativas
(Holley: innovation funds); mapa geográfico; tipos de ligação pessoa ↔ pessoa visíveis; integração com Kumu.

## Regras funcionais (somam-se às RF1–RF10 da SPEC-RNQ-001)
| # | Regra |
|---|---|
| RF11 | Nenhum item do mural, iniciativa ou perfil aparece sem `Publicar? = Sim` na planilha de tecelagem. |
| RF12 | Contatos (`Contato (privado)`) e observações internas nunca vão para o JSON público; o export falha se aparecerem. |
| RF13 | E-mails e telefones colados em texto público são removidos no export, com aviso. |
| RF14 | Participantes de iniciativas só aparecem se estiverem no mapa; proponente e autor aparecem pelo nome que informaram. |
| RF15 | Pedido de saída remove também itens do mural e iniciativas propostas pela pessoa. |
| RF16 | Apresentações com status Apresentadas/Acompanhando/Colaborando viram ligação no mapa. |
| RF17 | O painel do tecelão nunca é publicado e nunca sugere o hub configurado (`config.HUB_NOME`). |
| RF18 | O sincronizador só acrescenta envios novos (por ID) e ignora envios com honeypot preenchido. |
| RF19 | "Pode ser bom conhecer" usa só dados já públicos (temas e ligações). |

## Critérios de aceite (todos cobertos por testes automatizados)
- **CA11** Dado um item do mural sem aprovação, ele não aparece; com `Publicar? = Sim`, aparece sem o contato.
- **CA12** Dado um pedido aberto, o card mostra até 4 pessoas do mapa com área em comum (exceto o autor).
- **CA13** Dado "Publicar no mural" sem concordância ou com mais de 3 áreas, o envio é bloqueado.
- **CA14** Dado um perfil publicado, o card mostra "Pode compartilhar / Quer aprender"; "Colaboro com" vira ligação.
- **CA15** Dado um pedido de saída, a pessoa some com suas ligações, itens e iniciativas na próxima atualização.
- **CA16** Dado o mesmo envio sincronizado duas vezes, ele aparece uma vez e edições do Farley são preservadas.
- **CA17** O painel mostra a fase, a dependência do hub e sugestões sem o hub; um par registrado em Apresentações não volta.
- **CA18** No celular (390 px), mapa e mural não têm rolagem horizontal.
- **CA19** Os campos dos 8 formulários declarados no HTML batem com o que o sincronizador espera.

## Métricas de sucesso (painel → "Evolução")
| Métrica | Hoje (06/10) | Meta 90 dias |
|---|---|---|
| Pessoas conectadas | 33% | 60% |
| Dependência do hub | 20% | < 15% |
| Fase | 1 · Fragmentos | 3 · Multi-hub |
| Apresentações registradas | 0 | 30 |
| Itens no mural | 0 | 20 (≥ 50% com resposta) |
| Co-tecelões com papel | 0 | 3 |
