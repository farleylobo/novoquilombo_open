# Como contribuir

Obrigado por querer ajudar! *(English below.)*

1. **Rode com a rede fictícia:** `pip3 install openpyxl && python3 exportar.py --exemplo` e abra `site/index.html`.
2. **Testes:** `python3 -m unittest discover -s tests -q` e `npm install && npm run test:e2e` (Playwright).
3. **Privacidade em primeiro lugar:**
   - nunca inclua dados de pessoas reais em código, testes, issues ou pull requests;
   - todo campo novo no site precisa entrar na lista fechada `CAMPOS_*` de `rnq/config.py`.
4. **Textos da interface:** todo texto novo vai em `site/i18n.js`, em português e inglês. Um teste confere se as chaves batem.
5. Abra uma *issue* antes de mudanças grandes.

## Contributing (English)

1. Run it with the fictional network: `pip3 install openpyxl && python3 exportar.py --exemplo`, then open `site/index.html`.
2. Tests: `python3 -m unittest discover -s tests -q` and `npm install && npm run test:e2e`.
3. Privacy first:
   - never add real people's data to code, tests, issues or pull requests;
   - every new public field must be added to the closed `CAMPOS_*` allow-list in `rnq/config.py`.
4. UI text lives in `site/i18n.js`, in Portuguese and English.
5. Please open an issue before large changes.
