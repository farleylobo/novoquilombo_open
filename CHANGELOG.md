# Changelog

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
