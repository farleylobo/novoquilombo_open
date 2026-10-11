"""Publica o mapa no Netlify, com checagens antes.

    python3 publicar.py              # checa, monta a pasta de publicação e publica (precisa de .env)
    python3 publicar.py --so-pasta   # só checa e monta a pasta (para arrastar no painel do Netlify)
    --sem-contato                    # publica mesmo sem o e-mail de privacidade (saída continua pelo formulário)

Checagens (qualquer falha impede a publicação):
1. e-mail de privacidade preenchido (rnq/config.py, CONTATO_PRIVACIDADE);
2. o site foi gerado com os dados reais, não com a rede fictícia de exemplo;
3. testes automáticos passando.

Só os arquivos da lista PUBLICAR vão para o ar: versões antigas, planilhas, painel e o JSON bruto nunca saem
da sua máquina. A publicação usa NETLIFY_TOKEN e NETLIFY_SITE_ID do .env (veja docs/DEPLOY.md).
Rode no Terminal do seu Mac (precisa de Node.js: https://nodejs.org).
"""
import argparse
import os
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from rnq import config as C  # noqa: E402
from rnq import netlify  # noqa: E402

SITE = os.path.join(AQUI, 'site')
PASTA = os.path.join(AQUI, '_trabalho', 'publicar')
PUBLICAR = ['index.html', 'app.js', 'app.css', 'i18n.js', 'demo.js', 'data.js', 'robots.txt', 'netlify.toml', '_headers',
            'vendor/d3.min.js', 'vendor/3d-force-graph.min.js', 'vendor/LICENSES.txt',
            'participar.html', 'participar.js', 'participar.css', 'img/olho-horus.png']
MARCA_EXEMPLO = os.path.join(SITE, '.exemplo')


def checar(rodar_testes=True, sem_contato=False):
    erros = []
    if not C.CONTATO_PRIVACIDADE and not sem_contato:
        erros.append('Falta o e-mail de privacidade: preencha CONTATO_PRIVACIDADE em rnq/config.py e rode atualizar.py.')
    if os.path.exists(MARCA_EXEMPLO):
        erros.append('O site está com a rede FICTÍCIA de exemplo. Rode python3 atualizar.py para gerar com os dados reais.')
    if not os.path.exists(os.path.join(SITE, 'data.js')):
        erros.append('site/data.js não existe. Rode python3 atualizar.py.')
    if rodar_testes and not erros:
        r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'],
                           cwd=AQUI, capture_output=True, text=True)
        if r.returncode != 0:
            erros.append('Testes falhando:\n' + (r.stderr or r.stdout)[-1500:])
    return erros


def montar_pasta(destino=PASTA):
    if os.path.exists(destino):
        try:
            shutil.rmtree(destino)
        except OSError:       # pasta sem permissão de apagar: sobrescreve e confere se sobrou algo fora da lista
            pass
    for rel in PUBLICAR:
        origem = os.path.join(SITE, rel)
        if not os.path.exists(origem):
            raise FileNotFoundError(f'site/{rel} não encontrado')
        alvo = os.path.join(destino, rel)
        os.makedirs(os.path.dirname(alvo), exist_ok=True)
        shutil.copy2(origem, alvo)
    extras = [os.path.relpath(os.path.join(r, f), destino) for r, _, fs in os.walk(destino) for f in fs]
    extras = [x for x in extras if x not in PUBLICAR]
    if extras:
        raise RuntimeError(f'A pasta {destino} tem arquivos fora da lista: {extras}. Apague a pasta e rode de novo.')
    return destino


def publicar(pasta, cfg):
    env = dict(os.environ, NETLIFY_AUTH_TOKEN=cfg['NETLIFY_TOKEN'])
    cmd = ['npx', '-y', 'netlify-cli@latest', 'deploy', '--prod', '--dir', pasta, '--site', cfg['NETLIFY_SITE_ID'],
           '--message', 'publicar.py']
    print('Publicando…')
    return subprocess.run(cmd, cwd=AQUI, env=env).returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--so-pasta', action='store_true', help='só checa e monta a pasta, sem publicar')
    ap.add_argument('--sem-contato', action='store_true',
                    help='publica sem o e-mail de privacidade (o pedido de saída continua pelo formulário do site)')
    a = ap.parse_args()
    erros = checar(sem_contato=a.sem_contato)
    if a.sem_contato and not C.CONTATO_PRIVACIDADE:
        print('ATENÇÃO: publicando sem e-mail de privacidade. Preencha CONTATO_PRIVACIDADE assim que puder.')
    if erros:
        print('NÃO PUBLICADO:')
        for e in erros:
            print(' -', e)
        sys.exit(1)
    pasta = montar_pasta()
    print('Pasta pronta:', pasta, f'({len(PUBLICAR)} arquivos)')
    if a.so_pasta:
        print('Arraste essa pasta em Netlify > seu projeto > Deploys ("drag and drop").')
        return
    cfg = netlify.ler_env(AQUI)
    if not (cfg.get('NETLIFY_TOKEN') and cfg.get('NETLIFY_SITE_ID')):
        print('Falta NETLIFY_TOKEN/NETLIFY_SITE_ID no .env (veja docs/DEPLOY.md). '
              'Ou arraste a pasta acima em Netlify > seu projeto > Deploys.')
        sys.exit(1)
    sys.exit(publicar(pasta, cfg))


if __name__ == '__main__':
    main()
