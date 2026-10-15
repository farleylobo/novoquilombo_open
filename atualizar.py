"""Atualiza tudo de uma vez: formulários do site -> planilha de tecelagem -> site + painel.

    python3 atualizar.py

1. Se houver NETLIFY_TOKEN/NETLIFY_SITE_ID (.env), traz os envios novos dos formulários.
2. Gera site/rnq-publico.json, site/data.js e o painel (painel/painel-tecelagem.html, em inglês: painel-tecelagem-en.html).
3. Roda os testes automáticos; se algum falhar, avisa (o site gerado continua no lugar para você conferir).
"""
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import exportar  # noqa: E402
import sincronizar  # noqa: E402
from rnq import netlify  # noqa: E402


def main():
    cfg = netlify.ler_env(AQUI)
    if cfg.get('NETLIFY_TOKEN') and cfg.get('NETLIFY_SITE_ID'):
        try:
            total, novos = sincronizar.executar()
            print(f'Formulários: {total} envio(s) lidos; novos: ' +
                  (', '.join(f'{a}: {n}' for a, n in novos.items()) if novos else 'nenhum'))
        except (netlify.ErroNetlify, sincronizar.tecelagem.PlanilhaAberta) as err:
            print('Formulários não sincronizados:', err)
    else:
        print('Formulários: sem .env do Netlify — pulando (veja docs/DEPLOY.md).')
    try:
        exportar.executar()
    except exportar.publico.ErroPrivacidade as err:
        print('ERRO DE PRIVACIDADE — nada foi publicado:', err)
        sys.exit(2)
    r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'],
                       cwd=AQUI, capture_output=True, text=True)
    linhas = (r.stderr or r.stdout).strip().splitlines()
    print('Testes:', linhas[-1] if linhas else '?')
    if r.returncode != 0:
        print(r.stderr)
        sys.exit(1)
    print('Painel do tecelão: painel/painel-tecelagem.html (English: painel/painel-tecelagem-en.html)')


if __name__ == '__main__':
    main()
