# Publicar no Netlify

O site é estático (pasta `site/`) e os formulários usam **Netlify Forms**. O projeto já existe no Netlify:

- **Endereço:** https://mapa-novoquilombo.netlify.app
- **Painel:** https://app.netlify.com/projects/mapa-novoquilombo
- **Site ID:** `c3545b6d-116b-400d-b0ce-4cb222ea7ceb`
- **Forms:** já ativado.

Abrindo o `index.html` direto do computador, os formulários mostram "Prévia local" e não enviam nada.

## Antes da primeira publicação

1. **Privacidade:** `CONTATO_PRIVACIDADE` em `rnq/config.py` tem o e-mail da rede (rnqbrasil@gmail.com). Sem ele, o `publicar.py` não publica.
2. **Dados:** revise a seleção e rode `python3 atualizar.py` até terminar sem erros.
3. **Token do Netlify** (uma vez):
   1. Em Netlify, vá em **User settings → Applications → Personal access tokens → New access token**.
   2. Copie `env.exemplo` para `.env` e preencha:
      ```
      NETLIFY_TOKEN=<o token>
      NETLIFY_SITE_ID=c3545b6d-116b-400d-b0ce-4cb222ea7ceb
      RNQ_SITE_URL=https://mapa-novoquilombo.netlify.app
      ```
   3. O `.env` é privado e está no `.gitignore`. O mesmo token publica o site e traz os envios dos formulários.
4. **Node.js** instalado no Mac (https://nodejs.org). O `publicar.py` usa a CLI do Netlify via `npx`, sem precisar instalar mais nada.

## Publicar (toda vez)

No **Terminal do seu Mac**:

```bash
cd ~/Desktop/RNQ/visao-publica
python3 atualizar.py      # formulários -> planilha -> site -> testes
python3 publicar.py       # checagens -> pasta limpa -> Netlify
```

Antes de publicar, o `publicar.py` faz três checagens:
- o e-mail de privacidade está preenchido;
- o site foi gerado com os dados reais, e não com a rede fictícia de exemplo;
- os testes passam.

Depois, ele monta uma pasta só com os arquivos que podem ir ao ar, em `_trabalho/publicar/`. Versões antigas, o JSON bruto, as planilhas e o painel nunca saem da sua máquina.

**Sem token?** Rode `python3 publicar.py --so-pasta` e arraste a pasta `_trabalho/publicar` em **Netlify → mapa-novoquilombo → Deploys**, na área "Drag and drop".

## Depois da primeira publicação

- **Netlify → Forms:** confira se os 8 formulários aparecem: `mural`, `mural-resposta`, `perfil`, `sugestao-ligacao`, `opt-out`, `opt-in`, `iniciativa` e `iniciativa-participar`.
- **Forms → Form notifications → Add notification → Email:** cadastre o seu e-mail e o de quem modera junto.
- **Teste:** publique algo no mural pelo site e rode `python3 atualizar.py`. O envio deve aparecer na planilha de tecelagem.

## Por que o GitHub não publica sozinho

O código é aberto no GitHub. Os dados não vão para lá: o `.gitignore` exclui planilhas, `.env`, `painel/`, `_trabalho/`, `privado/`, `site/data.js` e `site/rnq-publico.json`. Por isso o Netlify **não** está ligado ao GitHub para publicar a cada push, já que o repositório não tem os dados. A publicação sai da sua máquina, pelo `publicar.py`.

## Indexação

O site tem `noindex`, na meta tag, no cabeçalho `X-Robots-Tag` e no `robots.txt`. Ele não aparece no Google, mas qualquer pessoa com o link consegue abrir. Para liberar a busca, remova essas três marcações. É uma decisão à parte e não precisa acompanhar a divulgação.

## Domínio próprio (opcional)

**Netlify → Domain management → Add a domain.**
