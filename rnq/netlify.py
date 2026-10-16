"""Leitura dos envios de formulários do Netlify Forms.

Duas formas:
1. API (automático): precisa de NETLIFY_TOKEN (token pessoal) e NETLIFY_SITE_ID — no arquivo .env
   da pasta visao-publica ou em variáveis de ambiente. Só leitura.
2. CSV (manual): no painel do Netlify, Forms > (formulário) > Download CSV; depois
   python3 sincronizar.py --csv arquivo.csv --form mural
"""
import csv
import json
import os
import urllib.error
import urllib.request

from .util import id_estavel, txt

API = 'https://api.netlify.com/api/v1'


class ErroNetlify(Exception):
    pass


def ler_env(pasta):
    """Lê pasta/.env (formato CHAVE=valor) sem dependências. Variáveis de ambiente têm prioridade."""
    cfg = {}
    caminho = os.path.join(pasta, '.env')
    if os.path.exists(caminho):
        with open(caminho, encoding='utf-8') as fh:
            for linha in fh:
                linha = linha.strip()
                if linha and not linha.startswith('#') and '=' in linha:
                    k, v = linha.split('=', 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
    for k in ('NETLIFY_TOKEN', 'NETLIFY_SITE_ID', 'RNQ_SITE_URL', 'SUPABASE_URL', 'SUPABASE_SECRET_KEY',
              'SUPABASE_SERVICE_ROLE_KEY', 'SUPABASE_ACCESS_TOKEN', 'SUPABASE_PROJECT_REF', 'RNQ_PAINEL_URL',
              'NETLIFY_PAINEL_SITE_ID', 'RNQ_ADMIN_EMAIL', 'RNQ_ADMIN_NOME'):
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    return cfg


def _get(caminho, token, abrir=urllib.request.urlopen):
    req = urllib.request.Request(API + caminho, headers={'Authorization': f'Bearer {token}',
                                                        'User-Agent': 'rnq-visao-publica'})
    try:
        with abrir(req, timeout=30) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ErroNetlify('Token do Netlify recusado (401/403). Gere um novo em User settings > Applications.')
        if e.code == 404:
            raise ErroNetlify('Site não encontrado (404). Confira NETLIFY_SITE_ID.')
        raise ErroNetlify(f'Netlify respondeu {e.code}')
    except urllib.error.URLError as e:
        raise ErroNetlify(f'Sem conexão com o Netlify: {e.reason}')


def buscar_envios(token, site_id, abrir=urllib.request.urlopen):
    """Devolve [{'form', 'id', 'criado', 'dados'}] de todos os formulários do site."""
    if not token or not site_id:
        raise ErroNetlify('Faltam NETLIFY_TOKEN e/ou NETLIFY_SITE_ID (veja docs/DEPLOY.md).')
    envios = []
    for f in _get(f'/sites/{site_id}/forms', token, abrir):
        pagina = 1
        while True:
            lote = _get(f'/forms/{f["id"]}/submissions?per_page=100&page={pagina}', token, abrir)
            for s in lote:
                envios.append({'form': f.get('name') or s.get('form_name'), 'id': txt(s.get('id')),
                               'criado': s.get('created_at'), 'dados': s.get('data') or {}})
            if len(lote) < 100:
                break
            pagina += 1
    return envios


def ler_csv(caminho, form):
    """CSV exportado do Netlify -> mesmo formato de buscar_envios."""
    envios = []
    with open(caminho, encoding='utf-8-sig', newline='') as fh:
        for row in csv.DictReader(fh):
            dados = {txt(k).lower().replace(' ', '_'): v for k, v in row.items() if k}
            eid = dados.pop('id', '') or id_estavel('csv', form, *sorted(dados.items()))
            criado = dados.pop('created_at', '') or dados.pop('date', '') or dados.pop('data', '')
            envios.append({'form': form, 'id': txt(eid), 'criado': criado, 'dados': dados})
    return envios
