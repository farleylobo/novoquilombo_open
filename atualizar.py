"""Atualiza tudo de uma vez: formulários do site -> planilha de tecelagem -> site + painel.

    python3 atualizar.py
    python3 atualizar.py --sem-painel-admin   # gera só com a planilha, sem falar com o painel admin (emergência)

1. Se houver NETLIFY_TOKEN/NETLIFY_SITE_ID (.env), traz os envios novos dos formulários.
2. Se o painel admin estiver configurado (SUPABASE_URL e SUPABASE_SECRET_KEY no .env), traz as decisões de
   moderação de lá: elas valem no lugar de "Publicar?", "Incluir no mapa?" etc. Sem conexão, para (nada é gerado).
3. Gera site/rnq-publico.json, site/data.js e o painel local (painel/painel-tecelagem.html e -en.html).
4. Manda para o painel admin os itens de moderação, as comunidades e o painel (rede toda + uma por comunidade).
5. Roda os testes automáticos; se algum falhar, avisa (o site gerado continua no lugar para você conferir).
"""
import argparse
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import exportar  # noqa: E402
import sincronizar  # noqa: E402
from rnq import admin, netlify  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--sem-painel-admin', action='store_true',
                    help='não fala com o painel admin: usa as colunas de moderação da planilha (só em emergência)')
    a = ap.parse_args(argv)
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

    usar_painel = admin.configurado(cfg) and not a.sem_painel_admin
    decisoes = None
    if usar_painel:
        try:
            decisoes = admin.buscar_decisoes(cfg)
            print(f'Painel admin: {len(decisoes)} decisão(ões) de moderação lidas.')
        except admin.ErroSupabase as err:
            print('Painel admin sem conexão — NADA foi gerado, porque as decisões de moderação estão lá.')
            print('  ', err)
            print('   Tente de novo em alguns minutos. Em emergência: python3 atualizar.py --sem-painel-admin')
            sys.exit(3)
    elif a.sem_painel_admin:
        print('Painel admin: ignorado (--sem-painel-admin). Valem as colunas de moderação da planilha.')
    else:
        print('Painel admin: não configurado — pulando (veja docs/PAINEL-ADMIN.md).')

    contexto = {}
    try:
        exportar.executar(decisoes=decisoes, contexto=contexto)
    except exportar.publico.ErroPrivacidade as err:
        print('ERRO DE PRIVACIDADE — nada foi publicado:', err)
        sys.exit(2)

    if usar_painel:
        try:
            r = admin.sincronizar(cfg, contexto, pasta_hist=contexto.get('pasta_hist'))
            print(f'Painel admin: atualizado — {r.get("snapshots", 0)} visão(ões), {r.get("itens_novos", 0)} item(ns) '
                  f'novo(s) para moderar, {r.get("itens_apagados", 0)} removido(s).')
            url = cfg.get('RNQ_PAINEL_URL')
            if url:
                print('   Abra:', url)
        except admin.ErroSupabase as err:
            print('Painel admin: NÃO atualizado (o site foi gerado normalmente):', err)

    r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'],
                       cwd=AQUI, capture_output=True, text=True)
    linhas = (r.stderr or r.stdout).strip().splitlines()
    print('Testes:', linhas[-1] if linhas else '?')
    if r.returncode != 0:
        print(r.stderr)
        sys.exit(1)
    print('Painel do tecelão (local): painel/painel-tecelagem.html (English: painel/painel-tecelagem-en.html)')


if __name__ == '__main__':
    main()
