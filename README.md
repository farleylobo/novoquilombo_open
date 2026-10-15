# Rede Novo Quilombo — visão pública

> **In English:** a living, bilingual (PT/EN) map of the Novo Quilombo Network (who is in the network, where they meet,
> what they work on, what they offer and need) plus network-weaving tools inspired by June Holley's
> *Network Weaver Handbook*: an offers & requests board, initiatives, introduction suggestions and a weaver's dashboard.
> Static site (HTML/CSS/vanilla JS, d3) + a small Python pipeline that turns curated spreadsheets into public data.
> The code is open; **the network's data is not in this repository**. Try it with a fictional network:
> `pip3 install openpyxl && python3 exportar.py --exemplo`, then open `site/index.html`.

Mapa vivo da Rede Novo Quilombo (RNQ): quem está na rede, onde se encontra, com o que trabalha,
o que oferece e o que precisa — e um conjunto de ferramentas para **tecer** a rede, inspiradas no
*Network Weaver Handbook*, de June Holley.

> Especificações: `docs/SPEC-RNQ-001-visao-publica.md` (mapa), `docs/SPEC-RNQ-002-tecelagem.md` (mural, iniciativas, painel)
> e `docs/SPEC-RNQ-003-painel-admin.md` (painel admin com login).
>
> **Publicar:** `docs/DEPLOY.md` · **Painel admin:** `docs/PAINEL-ADMIN.md` · **Contribuir:** `CONTRIBUTING.md`
> No ar: https://mapa-novoquilombo.netlify.app · Painel: https://painel-novoquilombo.netlify.app

## O que tem aqui

| Para quem | O quê | Onde |
|---|---|---|
| Quem abre o link | Mapa de **pessoas**, **organizações** e **3D**, agrupado por comunidade, tema ou atuação | `site/` |
| Quem abre o link | **Mural de ofertas e pedidos**, **Iniciativas** (projetos, encontros, grupos de prática), **Como participar** | `site/` |
| Quem quer entrar | **Faça parte**: cadastro em 5 passos (PT/EN) com prévia do card; cai na aba Cadastros para moderação | `site/participar.html` |
| Quem abre o link | No card: perfil ("posso compartilhar / quero aprender"), papéis na rede, "Pode ser bom conhecer", "Eu conheço essa pessoa", ficar/sair do mapa | `site/` |
| Farley e quem tece junto | **Planilha de tecelagem**: moderação de tudo que chega pelo site, diário de apresentações, papéis, correções | `RNQ-tecelagem.xlsx` |
| Farley e quem tece junto | **Painel do tecelão**: fase da rede, dependência do hub, apresentações sugeridas com mensagem pronta, fila de moderação, pedidos sem resposta. Em português e inglês | `painel/painel-tecelagem.html` e `painel/painel-tecelagem-en.html` |
| A equipe de tecelagem | **Painel admin com login**: o painel do tecelão por comunidade, **moderação** (aprovar/recusar), **equipe** (convites, papéis, comunidades) e **histórico**. Login por código + MFA, regras de acesso no banco (Supabase), PT/EN | `admin/` · https://painel-novoquilombo.netlify.app · `docs/PAINEL-ADMIN.md` |

## Como atualizar (o dia a dia)

O jeito mais simples: peça ao Claude **"atualiza o mapa"**.

No Terminal do Mac (uma vez: `pip3 install openpyxl`):

```bash
cd ~/Desktop/RNQ/visao-publica
python3 atualizar.py      # formulários -> planilha -> site + painel -> testes
```

`atualizar.py` faz, em ordem:
1. traz os envios novos dos formulários do site (se houver `.env` com o token do Netlify — ver `docs/DEPLOY.md`);
2. com o painel admin configurado, traz as decisões de moderação de lá (elas valem no lugar das colunas da planilha) e, no fim, manda os dados novos para o painel (`docs/PAINEL-ADMIN.md`);
3. gera `site/rnq-publico.json`, `site/data.js`, o painel (`painel/painel-tecelagem.html` e a versão em inglês `painel-tecelagem-en.html`) e o histórico de saúde da rede;
4. roda os testes. Se algo falhar, nada é escondido: você vê o erro.

Depois, abra `painel/painel-tecelagem.html` para ver o que fazer, e `site/index.html` para conferir o site.
Para ver o mural e as iniciativas com exemplos fictícios: `site/index.html?demo=1`.

## Idiomas (PT | EN)

O site tem um botão **PT | EN** no cabeçalho. Em inglês, o nome da rede é **Novo Quilombo Network**.

- **Textos da interface:** `site/i18n.js`. Para mudar uma frase, edite os dois blocos, `pt` e `en`. Um teste confere se os dois têm as mesmas chaves.
- **Textos do painel do tecelão:** `TEXTOS` em `rnq/painel.py`, também com os blocos `pt` e `en` e o mesmo teste. As fases da rede em inglês ficam em `FASES_EN` (`rnq/rede.py`).
- **Nomes de comunidades, temas e atuação:** `NOMES_EN` em `rnq/config.py`. Os nomes dos papéis ficam em `PAPEIS`, no mesmo arquivo. Se você criar um nome novo sem tradução, o site mostra o nome em português e o `atualizar.py` avisa.
- **Não são traduzidos:** o que as pessoas escrevem (mural, iniciativas, perfil, cargos) e os nomes de pessoas e organizações.
- **Idioma de abertura:** o link com `?lang=en` (ou `?lang=pt`) vem primeiro. Depois vale a última escolha feita no botão. Sem nenhuma das duas, o site segue o idioma do navegador: português para quem usa português e inglês para os demais.
- **Formulários:** os campos enviados ao Netlify são os mesmos nos dois idiomas, então a planilha de tecelagem não muda.

## As três planilhas

| Planilha | Quem edita | Para quê |
|---|---|---|
| `RNQ-selecao.xlsx` | Farley | Quem entra no mapa (`Incluir? = Sim`), comunidades (até 3) e ligações curadas |
| `RNQ-temas-atuacao.xlsx` | Farley | Temas (até 3) e atuação (até 2) de cada pessoa |
| `RNQ-tecelagem.xlsx` | Farley e co-tecelões | Tudo que chega pelo site + diário de apresentações, papéis e correções (ver `docs/MODERACAO.md`) |

## Privacidade (resumo)

- **Lista fechada de campos**: o export falha se aparecer qualquer campo fora de `rnq/config.py` (`CAMPOS_*`).
- **Contatos nunca vão para o site.** Colunas "(privado)" e "Observação interna" ficam só na planilha e no painel.
  Se alguém colar e-mail ou telefone num texto público, o export remove e avisa.
- **Nada aparece sem moderação**, exceto pedidos de saída: esses valem na próxima atualização (RF8).
- `painel/`, `_trabalho/`, `.env` e as planilhas são **privados** — nunca publique (o `.gitignore` já os exclui).
- O site tem `noindex` (meta + cabeçalho `X-Robots-Tag` no `netlify.toml`) e `robots.txt` bloqueando tudo.

## Estrutura

```
visao-publica/
├── atualizar.py          # tudo de uma vez
├── publicar.py           # checagens + publicação no Netlify (docs/DEPLOY.md)
├── exportar.py           # planilhas -> site + painel
├── sincronizar.py        # Netlify Forms -> RNQ-tecelagem.xlsx (API ou CSV)
├── painel_admin.py       # painel admin: configurar (Supabase) · publicar · status · demo
├── admin/                # o app do painel admin (estático) + supabase/ (banco e função de convite)
├── rnq/                  # pipeline (Python puro + openpyxl)
│   ├── config.py         #   decisões de modelo e lista fechada de campos públicos
│   ├── fontes.py         #   leitura das planilhas
│   ├── publico.py        #   monta o JSON público (moderação, saídas, correções, privacidade)
│   ├── rede.py           #   saúde da rede e sugestões de apresentação
│   ├── tecelagem.py      #   planilha de tecelagem (criação, migração, envios)
│   ├── netlify.py        #   leitura dos formulários
│   ├── painel.py         #   painel do tecelão (arquivo local e visão do painel admin)
│   ├── admin.py          #   painel admin: moderação, recorte por comunidade, sincronização
│   └── supabase.py       #   conversa com o Supabase (só urllib)
├── site/                 # o que vai para o Netlify
│   ├── index.html  app.js  app.css  i18n.js (PT/EN)  demo.js  vendor/ (d3, 3d-force-graph)
│   ├── data.js  rnq-publico.json   (gerados — não editar)
│   └── netlify.toml  robots.txt
├── exemplo/              # rede fictícia (python3 exportar.py --exemplo)
├── tests/                # unittest (Python) + e2e (Playwright)
└── docs/                 # specs, moderação, tecelagem, deploy
```

## Rodar com uma rede fictícia (para quem clonou o projeto)

As planilhas e os dados reais não estão no repositório. Para ver tudo funcionando:

```bash
pip3 install openpyxl
python3 exportar.py --exemplo    # gera o site com ~37 pessoas inventadas
open site/index.html             # ou site/index.html?demo=1 para ver mural e iniciativas de exemplo
```

Para adaptar a outra rede, comece por `rnq/config.py` (comunidades, temas, papéis, nomes em inglês, hub e contato de
privacidade) e pelo formato das planilhas descrito em `docs/MODERACAO.md`.

## Testes

```bash
python3 -m unittest discover -s tests -q      # testes do pipeline (sem instalar nada além de openpyxl)
npm install && npm run test:e2e               # testes do site num navegador de verdade (Playwright)
npm run test:sql                              # banco do painel admin (Postgres em memória) e função de convite
npm run test:painel                           # painel admin no navegador (demo, login, MFA, moderação, equipe)
```

O site usa as bibliotecas de `site/vendor` (sem CDN), então os testes de ponta a ponta funcionam offline
e salvam capturas de tela em `tests/e2e/screenshots/`.

## Código aberto

O **código** é aberto; os **dados** não ficam no repositório. O `.gitignore` exclui planilhas, painel, histórico,
`.env` e os dados gerados do site (`site/data.js`, `site/rnq-publico.json`). O deploy é feito da sua máquina
(`netlify deploy`), que leva os dados junto sem publicá-los no GitHub. Ver `docs/DEPLOY.md`.
