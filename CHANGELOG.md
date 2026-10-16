# Changelog

## 2.7.0 — 16/10/2026 · Envios na hora e mapa atualizado todo dia

- **Envios chegam ao painel sozinhos.** Inscrição, oferta, pedido, resposta e participação enviados no mapa entram na Moderação na hora, com a marca "chegou pelo site". Sem terminal.
  - Nova Edge Function `receber`: o Netlify a chama a cada envio (aviso `submission_created` por formulário).
  - Protegida por chave longa na URL (`RNQ_RECEBER_SEGREDO`, comparação em tempo constante), confere o nome do site, recusa corpo acima de 64 KB e ignora o honeypot.
  - Monta o item exatamente como o pipeline (`contrato.json` gerado de `rnq/admin.py`; paridade testada).
  - O pipeline não apaga nem sobrescreve itens que chegaram pelo site (`moderacao.fonte`).
- **Mapa público atualizado uma vez por dia**, por rotina no Mac (`python3 painel_admin.py automatizar [--hora N] [--desligar]`, launchd). Se o Mac estiver dormindo, roda quando ele acordar. Log em `~/Library/Logs/rnq-rotina.log`.
- **Faixa do mapa no painel:** horário da rotina, última publicação e, se falhou, em que etapa. Fica vermelha também quando a rotina está ligada e não roda há mais de 26 h (Mac desligado ou sem permissão do macOS). `publicar.py` manual também registra.
- **Moderação:** botão "Atualizar lista" e recarga automática ao voltar para a aba.
- `configurar` agora publica a função `receber`, cria a chave e liga os formulários do Netlify. Novo comando `ligar-formularios`.
- Datas dos envios do Netlify (UTC) passam a ser gravadas no horário de Brasília.
- Banco: esquema versão 2 (`rnq_receber_envio`, `rnq_pipeline_registrar`, `rnq_painel_status`).
- Testes: 168 unitários, 40 do banco e funções, 22 de ponta a ponta do painel, 30 do site.

## 2.6.2 — 16/10/2026 · Painel ligado ao mapa

- Botão **"Ver o mapa"** no topo do painel: abre o mapa público em outra aba (no idioma do painel).
- **"Ver no mapa"** em cada item da moderação: abre direto o card da pessoa (`#p/…`), o item do mural (`#m/…`) ou a iniciativa (`#i/…`), quando o alvo está nos dados da última atualização. O mapa no ar mostra a última versão publicada.
- Sem SMTP próprio, o painel usa os e-mails padrão do Supabase (o plano gratuito não aceita modelos próprios) e o login funciona pelo link do e-mail.

## 2.6.0 — 15/10/2026 · Painel admin com login

- Novo **painel admin com login**, em https://painel-novoquilombo.netlify.app (pasta `admin/`). Ele substitui o envio do HTML local e está em português e inglês.
  - **Visão da rede:** o painel do tecelão para a rede toda e para cada comunidade.
  - **Moderação:** aprovar, recusar com motivo e desfazer. Os contatos ficam escondidos até você pedir para ver.
  - **Equipe:** convites, papéis (admin ou tecelã/tecelão) e comunidades.
  - **Histórico:** registro de tudo o que foi feito, que não pode ser apagado.
- **Login:** só por convite, com código de 6 dígitos por e-mail. Quem é admin também precisa de MFA (app autenticador), e o próprio banco exige isso.
- **Banco no Supabase, região São Paulo** (`admin/supabase/schema.sql`):
  - regras de acesso (RLS) em todas as tabelas;
  - funções `rnq_*` para tudo o que muda dados;
  - travas para que a rede nunca fique sem admin e para que o histórico não possa ser alterado.
- **O painel passa a ser a fonte da moderação.** O `atualizar.py` traz as decisões do painel antes de gerar o site e, no fim, envia os itens novos e as visões.
  - Sem conexão com o painel, nada é gerado.
  - Em emergência, `--sem-painel-admin` volta a usar só a planilha.
- **Cada comunidade tem a sua visão**, montada só com as pessoas e as linhas da planilha daquela comunidade. Um tecelão nunca recebe contatos de outra comunidade (RF21, testado).
- **Quem pede para sair do mapa** também some do painel, inclusive os contatos (RF25).
- **Segurança no navegador:**
  - a visão roda num iframe isolado (sandbox);
  - CSP rígida, com hash do único script inline;
  - a chave secreta nunca entra no app (`publicar` e os testes recusam).
- **Novos comandos em `painel_admin.py`:**
  - `configurar` prepara o Supabase pela Management API: banco, login, e-mails PT/EN, função de convite e o primeiro admin;
  - `publicar`, `status` e `demo`.
- **Modo demonstração** com a rede fictícia, incluindo a opção "ver como" uma tecelã. A planilha de exemplo agora pode trazer envios fictícios (`gerar(..., com_tecelagem=True)`).
- **Edge Function `convidar`:** confere se quem chama é admin com MFA, usando o login da própria pessoa, e só então convida.
- **Fluxo opcional** `.github/workflows/painel-manter-ativo.yml`, para o plano gratuito do Supabase não pausar o projeto.
- **Painel do tecelão:** ganhou o modo `painel`, usado pelo painel admin. O arquivo local continua igual.
- **Testes:**
  - 151 unitários;
  - 32 do banco e da função de convite (PGlite: Postgres de verdade em memória), mais 1 opcional no Deno;
  - 18 de ponta a ponta do painel (Chromium com a CSP do Netlify e um Supabase falso para login e MFA);
  - os 30 de ponta a ponta do site continuam passando.

## 2.5.0 — 15/10/2026 · Painel em inglês

- O painel do tecelão agora sai também em inglês: **`painel/painel-tecelagem-en.html`**, gerado junto com o painel em português a cada `exportar.py` / `atualizar.py`. Um link no topo leva de um para o outro.
- Textos do painel em `TEXTOS` (`rnq/painel.py`), com blocos `pt` e `en`; as fases da rede em inglês em `FASES_EN` (`rnq/rede.py`).
- Em inglês, temas, comunidades e atuação usam o `nome_en`. Os motivos de cada apresentação sugerida e a mensagem pronta saem traduzidos.
- Ficam em português, como estão na planilha: nomes de abas e colunas, valores como "Apresentadas", o que as pessoas escreveram (mural, cargos) e os avisos da atualização. O painel em inglês avisa isso no topo.
- O painel em português não muda, exceto "1 ligação" no singular.
- Testes: 97 unitários (7 novos para os dois idiomas).

## 2.4.0 — 11/10/2026 · "Faça parte"

- Nova página **`participar.html`**: cadastro em 5 passos com prévia do card, em PT e EN. Portada do protótipo de 11/10 e ligada pelo botão "Faça parte" no mapa e em "Como participar".
- O envio vai para o formulário `participar` do Netlify, declarado escondido no `index.html`. As escolhas seguem sempre em português, nos dois idiomas.
- Nova aba **Cadastros** na planilha de tecelagem:
  - `Incluir no mapa? = Sim` põe a pessoa no mapa, se ela escolheu aparecer e tem 18 anos ou mais;
  - se a pessoa já estava no mapa, o cadastro soma ao que ela já tinha;
  - oferta e pedido autorizados entram também na aba Mural, esperando moderação.
- O card no mapa mostra **propósito** (até 432 caracteres) e **fios que tece** (até 4 dos 12).
- Comunidades novas: A Gente Muda, Guerreiros Sem Armas, Antroposofia/Teosofia e afins, Espiritualidade & Religião, com nome em inglês.
- Ficam fora do site: contato, cidade, aniversário, organizações de interesse, necessidade, objetivo, formatos e indicações.
- Painel: conta os cadastros esperando revisão.
- Testes: 90 unitários e 30 de ponta a ponta.

## 2.3.0 — 11/10/2026 · Pronto para publicar e abrir o código

- **Sobre os dados** (PT/EN), no rodapé e no link `#sobre`: o que aparece, o que nunca aparece, base legal, direitos e contato. O e-mail fica em `rnq/config.py` (`CONTATO_PRIVACIDADE`), e o export avisa enquanto estiver vazio.
- `publicar.py`: só publica se houver e-mail de privacidade, se o site tiver sido gerado com os dados reais e se os testes passarem. Envia ao Netlify apenas os arquivos de uma lista fechada.
- Rede fictícia para quem clonar o projeto: `python3 exportar.py --exemplo` (pasta `exemplo/`).
- Código aberto sem dados pessoais:
  - scripts de importação e notas com nomes reais saíram para `privado/`, que fica fora do repositório;
  - correções iniciais com nomes reais saíram do `exportar.py`.
- Projeto no Netlify: `mapa-novoquilombo` (Forms ativado). `CONTRIBUTING.md` e README com resumo em inglês.
- Contato de privacidade: rnqbrasil@gmail.com. No ar em https://mapa-novoquilombo.netlify.app desde 11/10/2026.
- Testes: 79 unitários e 26 de ponta a ponta.

## 2.2.0 — 06/10/2026 · Versão em inglês

- Botão **PT | EN** no cabeçalho. A troca acontece na hora, sem recarregar: o card aberto continua aberto e o endereço (`#p/...`) se mantém.
- Nome da rede em inglês: **Novo Quilombo Network**.
- Idioma de abertura: `?lang=en|pt` primeiro, depois a última escolha no botão (guardada no navegador), depois o idioma do navegador.
- Interface em `site/i18n.js`. Datas relativas ("há 3 dias" / "3 days ago") vêm do próprio navegador.
- Comunidades, temas, atuação e papéis ganharam nome em inglês nos dados públicos (`nome_en` e `desc_en`). As traduções ficam em `rnq/config.py` (`NOMES_EN`). Nome sem tradução gera aviso e aparece em português.
- A lista fechada de campos passou a valer também para grupos e papéis (`CAMPOS_GRUPO`, `CAMPOS_PAPEL`).
- Não são traduzidos: o que as pessoas escrevem e os nomes de pessoas e organizações. Os campos dos formulários do Netlify são os mesmos nos dois idiomas.
- Testes: 70 unitários e 25 de ponta a ponta (7 novos, só de idioma).

## 2.1.0 — 06/10/2026 · Revisão

**Correções**
- Contato colado em "Precisa de" (iniciativas) agora também é removido do site.
- LinkedIn só é publicado se for um link http(s) (bloqueia `javascript:` e lixo vindo da planilha).
- Pedido de saída com nome que não bate com ninguém vira aviso (antes era ignorado em silêncio).
- Sincronizar com a planilha de tecelagem aberta no Excel é recusado (o Excel apagaria as linhas novas ao salvar); cópia de segurança automática antes de cada gravação (10 últimas em `_trabalho/backups`).
- "Pode ser bom conhecer" estava vazio para 12 pessoas sem tema (grupo de Tecnologia/ESG): agora completa com quem é da mesma comunidade e de outra organização.
- Contraste: texto escuro nas etiquetas de cor clara.
- Ao abrir uma organização, o endereço mantém a aba.

**Melhorias**
- Bibliotecas servidas pelo próprio site (`site/vendor`): nenhuma chamada a CDN, mais privacidade, funciona se o CDN cair.
- Busca aceita trecho do nome (Enter); Esc fecha o card; abas com `aria-selected`.
- "Copiar link" em itens do mural e iniciativas; links diretos `#m/<id>` e `#i/<id>` (para compartilhar no WhatsApp).
- Itens abertos há mais de 60 dias aparecem como "pode estar desatualizado".
- Painel: "Posso ajudar" esperando apresentação (com os dois contatos e mensagem pronta), itens antigos e **mensagem da semana** pronta para os grupos de WhatsApp (`RNQ_SITE_URL` no `.env`).
- Testes: 63 unitários + 18 de ponta a ponta.

## 2.0.0 — 06/10/2026 · Tecelagem (SPEC-RNQ-002)

**Site**
- Mural de ofertas e pedidos: filtros (tipo, área, busca, atendidos), "Na rede, quem trabalha com isso", "Posso ajudar / Tenho interesse", publicação com concordância e até 3 áreas.
- Iniciativas: projetos, encontros e grupos de prática; "Quero participar"; "Propor iniciativa".
- Card da pessoa: papéis na rede, perfil (compartilha / aprende / convocaria), itens no mural, iniciativas, "Pode ser bom conhecer", "Atualizar meu perfil".
- "Como participar" (todo mundo pode tecer), links diretos (`#mural`, `#iniciativas`, `#p/<id>`), modo demonstração (`?demo=1`), aviso de prévia local nos formulários.
- Código separado em `index.html`, `app.js`, `app.css`, `demo.js`.

**Pipeline**
- Novo pacote `rnq/` (testável); `atualizar.py`, `exportar.py`, `sincronizar.py`.
- Planilha de tecelagem com 11 abas (moderação, diário de apresentações, papéis, correções).
- Sincronização dos Netlify Forms (API ou CSV), deduplicada e sem sobrescrever edições.
- Saídas aplicadas automaticamente (RF8); apresentações feitas viram ligações; correções sem mexer na seleção.
- Privacidade: lista fechada de campos, remoção de e-mail/telefone em texto público, checagem de vazamento de contato.
- Painel do tecelão: fase da rede, dependência do hub, apresentações sugeridas com mensagem pronta, fila de moderação, pedidos sem resposta, histórico.

**Testes e docs**
- 54 testes unitários (unittest) + 14 testes de ponta a ponta (Playwright).
- README, MODERACAO, TECELAGEM, DEPLOY, SPEC-RNQ-002.

## 1.x — 04/10/2026 · Visão pública (SPEC-RNQ-001)
- Mapa de pessoas, organizações e 3D; agrupar por comunidade, tema e atuação; opt-in/opt-out; "Eu conheço essa pessoa".
