"""Traz os envios dos formulários do site (Netlify Forms) para a planilha RNQ-tecelagem.xlsx.

Automático (API):  python3 sincronizar.py
    precisa de NETLIFY_TOKEN e NETLIFY_SITE_ID no arquivo .env desta pasta (veja env.exemplo)
Manual (CSV):      python3 sincronizar.py --csv envios.csv --form mural

Só acrescenta linhas novas (pelo ID do envio). Nunca apaga nem altera o que você editou.
"""
import argparse
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from rnq import netlify, tecelagem  # noqa: E402

PLANILHA = os.path.join(AQUI, 'RNQ-tecelagem.xlsx')


def executar(pasta=AQUI, csv=None, form=None, abrir=None):
    planilha = os.path.join(pasta, 'RNQ-tecelagem.xlsx')
    if csv:
        if form not in tecelagem.FORMULARIOS:
            raise SystemExit(f'--form precisa ser um de: {", ".join(tecelagem.FORMULARIOS)}')
        envios = netlify.ler_csv(csv, form)
    else:
        cfg = netlify.ler_env(pasta)
        kw = {'abrir': abrir} if abrir else {}
        envios = netlify.buscar_envios(cfg.get('NETLIFY_TOKEN'), cfg.get('NETLIFY_SITE_ID'), **kw)
    novos = tecelagem.adicionar_envios(planilha, envios)
    return len(envios), novos


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--csv', help='arquivo CSV exportado do Netlify')
    ap.add_argument('--form', help='nome do formulário do CSV (mural, perfil, opt-out, ...)')
    a = ap.parse_args()
    try:
        total, novos = executar(csv=a.csv, form=a.form)
    except (netlify.ErroNetlify, tecelagem.PlanilhaAberta) as err:
        print('Não sincronizou:', err)
        sys.exit(1)
    print(f'{total} envio(s) lidos; novos na planilha: ' +
          (', '.join(f'{aba}: {n}' for aba, n in novos.items()) if novos else 'nenhum'))
