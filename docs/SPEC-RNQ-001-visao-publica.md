# SPEC-RNQ-001 · Visão pública da Rede Novo Quilombo

**Status:** Implementado no protótipo local (06/10/2026) — aguardando deploy. Continuação: SPEC-RNQ-002 (tecelagem).
**Tipo:** Produto novo (projeto separado do Atria)

## Contexto (para quem chega sem histórico)
- A Rede Novo Quilombo (RNQ) é a rede/movimento fundada pelo Farley (ancestralidade, equidade racial, regeneração). Decisão anterior: a plataforma da RNQ é **gratuita e open source**, separada do **Atria** (produto comercial de inteligência de rede).
- O Atria já tem: banco com a rede do Farley (Netlify DB), card de detalhe da pessoa, aba **Mapa** (`NetworkView2D`, 2D com clusters) e tela **3D** (`/graph`, `react-force-graph-3d`). Código: `~/Desktop/Merlin/6.nqb-network-platform` (repo `farleylobo/RNQ-NETWORK`).
- Material anterior da RNQ: `~/Desktop/Merlin/3.rede-novo-quilombo-app` (`explorador-3d.html`, `rede-dados.json`, modelo de dados em `REDE-CATEGORIAS-CLUSTERS-FORMULARIO.md`).

## Objetivo
Publicar a **primeira visão da RNQ, focada em pessoas**: quem está na rede, **onde se encontra** (comunidades), **com o que trabalha** (temas), **de onde atua** (atuação) e quem se conecta com quem — para ser divulgada pelo Farley em grupos de WhatsApp de que participa. Pergunta principal do mapa (Farley, 04/10): *quem pode colaborar e onde as pessoas se encontram*.

## Público e distribuição
- Membros dos grupos de que o Farley participa e qualquer pessoa com o link.
- Acesso: **qualquer pessoa com o link**, sem login. Página com `noindex` (não aparece no Google).

## Modelo de agrupamento (decisão 04/10)
| Dimensão | Definição | Quantidade | Exibição |
|---|---|---|---|
| **Comunidade** | Grupo onde as pessoas se encontram | 6: ESG (24), Cultura Regenerativa (23), Tecnologia (17), IDGs (14), Teoria U (12), Comunidade Integral (11) | Hubs com círculo preenchido; chips coloridos no card |
| **Tema** | Assunto em que a pessoa trabalha; vários por pessoa | 16 | Hubs com contorno tracejado; chips com contorno no card |
| **Atuação** | De onde a pessoa atua; até 2 por pessoa | 7 | Hubs só com rótulo; texto simples no card |

- Viraram temas (antes comunidades): Diversidade/Equidade/Inclusão → "Diversidade, equidade & inclusão"; Empreendedorismo → "Empreendedorismo & negócios de impacto"; Mentoria e DH → "Mentoria & desenvolvimento humano"; Colaboração Internacional → "Colaboração internacional".
- **Tecnologia e ESG são comunidades** (Farley, 04/10) e absorvem os temas equivalentes.
- Tema "Diversidade & equidade racial" renomeado para "Diversidade, equidade & inclusão" (Farley, 04/10).
- Temas e atuação propostos pelo Claude e revisados pelo Farley em `RNQ-temas-atuacao.xlsx`.
- Pessoas sem comunidade aparecem num hub neutro "Ainda sem comunidade" na visão por Comunidades.
- Todas essas regras vivem em `rnq/config.py`.

## Escopo
1. **Seleção curada:** o Farley define a lista de pessoas; os dados vêm da base do Atria.
2. **Exportação com lista fechada de campos:** gera `rnq-publico.json` só com os campos públicos (RF3).
3. **Abas:** **Pessoas** (2D), **Organizações** (2D), **3D** com chave **Pessoas | Organizações** (visual e navegação do Atria). Lateral **"Agrupar por: Comunidades · Temas · Atuação"**. Busca por pessoa ou organização. (Mural e Iniciativas: SPEC-RNQ-002.)
4. **Card público:** blocos Comunidades / Temas / Atuação, sem nenhum dado de avaliação.
5. **Ligações pessoa ↔ pessoa:** curadas pelo Farley; "Eu conheço essa pessoa" → moderação → próximo export.
6. **Opt-in / opt-out no card e no rodapé**, com confirmação Sim/Não; sem persistência no navegador.
7. **Identidade visual da RNQ.** Projeto Netlify próprio.

**Fora do escopo:** cadastro próprio, login, edição do perfil pela pessoa, ligações sem moderação, mapa geográfico/território, indexação no Google, verificação de identidade em opt-in/opt-out, 3D único pessoas + organizações.

## Regras funcionais
| # | Regra |
|---|---|
| RF1 | Nenhuma conexão em tempo real com o banco do Atria. O site público só lê o JSON gerado no export. |
| RF2 | Só entra no JSON quem está marcado "Sim" na planilha de seleção do Farley. |
| RF3 | Campos públicos (lista fechada, `rnq/config.py`): nome, cargo, organização, comunidades, temas, atuação, LinkedIn; desde 06/10 também papéis, compartilha/aprende/convoca (perfil revisado) e "pode ser bom conhecer" (SPEC-RNQ-002). Qualquer campo novo exige aprovação do Farley. |
| RF4 | Nunca publicados: score, eixos/score breakdown, triagem e nota de triagem, ação recomendada, ruído, recomendações de sinergia, status de rede, `attributes`, email, telefone, data de conexão, localização, confiança e base da sugestão de temas. |
| RF5 | `summary` e `tags` do Atria não são publicados; temas públicos vêm só da planilha validada. |
| RF6 | Ligação pessoa ↔ pessoa só aparece depois de aprovada pelo Farley. |
| RF7 | Frase visível de origem e finalidade dos dados e link de opt-out. |
| RF8 | Pedido de opt-out tem prioridade: a pessoa sai no próximo export, sem pergunta. |
| RF9 | Formulários via Netlify Forms (8 formulários; ver SPEC-RNQ-002). Opt-in/opt-out não pedem contato; Farley confere na aba Saídas. |
| RF10 | Linha da planilha de temas com "Aprovado? = Não" é ignorada; vazio ou "Sim" é aceito. |

## Fluxo de atualização
Farley edita as planilhas → `python3 atualizar.py` (formulários → planilha → site + painel → testes) → `netlify deploy --dir site --prod`. Ou pede ao Claude "atualiza o mapa". Meta: < 10 min por atualização.

## Arquivos (em `~/Desktop/RNQ/visao-publica/`)
- `RNQ-selecao.xlsx` — seleção (Pessoas, Comunidades, Ligações).
- `RNQ-temas-atuacao.xlsx` — temas e atuação por pessoa.
- `RNQ-tecelagem.xlsx` — moderação, apresentações, papéis, correções (`docs/MODERACAO.md`).
- `atualizar.py`, `exportar.py`, `sincronizar.py` + pacote `rnq/` — pipeline.
- `site/` — site estático. `painel/` — painel privado do tecelão. `tests/` — testes. `docs/` — specs e guias.

## Decisões registradas
- Site estático separado, não workspace público no Atria.
- Notificação depois do lançamento, com opt-out (Farley). Ponto em aberto: checagem de LGPD.
- 04/10 — Seleção via planilha; Farley aparece como nó ("Farley Lobo").
- 04/10 — Removidas: YCL, Fito Network, Terapias Holísticas.
- 04/10 — Visão de Organizações (círculos) e 3D de Organizações via chave dentro do 3D.
- 04/10 — Opt-in/opt-out com Sim/Não, sem persistência. 3D alinhado ao Atria.
- 04/10 — Grupo de product owners entra na RNQ.
- 04/10 — Comunidade vs. tema separados; Tecnologia e ESG mantidas como comunidades.
- 04/10 — LinkedIn não é lido automaticamente (exige login; automação contraria os termos do LinkedIn).
- 06/10 — Código aberto sem dados: o `.gitignore` exclui planilhas e dados gerados; deploy via `netlify deploy` da máquina do Farley.

## Em aberto
- [ ] Pessoas ainda sem comunidade (lista nos avisos do `atualizar.py`).
- [ ] ID-X como comunidade?
- [ ] Link do LinkedIn do Farley.
- [x] Certificações removidas dos nomes vindos do LinkedIn (aba Correções, 06/10).
- [ ] Confirmar cargos aplicados via aba Correções.
- [ ] Revisar cargos dos membros do núcleo e nomes de organização.
- [ ] Domínio/URL da RNQ; projeto Netlify (passo a passo em `docs/DEPLOY.md`).
- [ ] Ativos de identidade visual da RNQ.
- [ ] Checagem de LGPD.
- [ ] Atualizar a base (snapshot de 11/09).

## Critérios de aceite (cobertos por testes automatizados)
- **CA1:** O JSON exportado não contém nenhum campo de RF4.
- **CA2:** Sem login, vejo Pessoas, Organizações e 3D e consigo agrupar por Comunidades, Temas e Atuação.
- **CA3:** Uma pessoa em 2 grupos da dimensão escolhida aparece ligada aos 2.
- **CA4:** O card mostra só os campos de RF3, em blocos Comunidades / Temas / Atuação.
- **CA5:** "Eu conheço essa pessoa" não cria ligação até o Farley aprovar.
- **CA6:** Após um pedido de opt-out, no próximo export a pessoa e as ligações dela somem.
- **CA7:** A página não é indexada (`noindex`) e funciona no celular.
- **CA8:** Clicando numa organização (2D ou 3D), vejo as pessoas da rede que estão nela e os grupos delas.
- **CA9:** "Quero sair" → "Sim" esconde a pessoa na sessão; ao recarregar, ela volta até o próximo export.
- **CA10:** Trocar "Agrupar por" muda título, frase explicativa e estilo dos hubs.
