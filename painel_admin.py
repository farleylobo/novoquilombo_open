"""Painel admin com login da Rede Novo Quilombo — preparar, conferir, publicar e gerar a demonstração.

    python3 painel_admin.py configurar           # 1ª vez (e a cada versão nova): prepara o Supabase e o 1º admin
    python3 painel_admin.py publicar             # publica o app do painel no Netlify
    python3 painel_admin.py publicar --so-pasta  # só monta a pasta, para arrastar no Netlify
    python3 painel_admin.py status               # confere a conexão e mostra os números do painel
    python3 painel_admin.py demo                 # regenera admin/demo-dados.js (rede fictícia, modo demonstração)

O dia a dia continua sendo só "python3 atualizar.py": ele traz as decisões do painel e manda os dados novos.
Passo a passo completo: docs/PAINEL-ADMIN.md.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from rnq import admin, netlify  # noqa: E402
from rnq.supabase import Banco, ErroSupabase, Gestao, escolher_chaves  # noqa: E402

ADMIN = os.path.join(AQUI, 'admin')
PASTA_PUBLICAR = os.path.join(AQUI, '_trabalho', 'painel-admin')
PAINEL_URL_PADRAO = 'https://painel-novoquilombo.netlify.app'
NOME_SITE_PADRAO = 'painel-novoquilombo'
# Lista fechada do que vai para o ar (como em publicar.py): nada fora dela sai do Mac.
PUBLICAR = ['index.html', 'app.js', 'app.css', 'i18n.js', 'api.js', 'demo.js', 'demo-dados.js', 'config.js',
            'robots.txt', '_headers', 'netlify.toml', 'img/olho-horus.png', 'img/favicon.png',
            'vendor/supabase.js', 'vendor/LICENSES.txt', 'fonts/marcellus-400.woff2', 'fonts/source-sans-3-400.woff2',
            'fonts/source-sans-3-600.woff2', 'fonts/source-sans-3-700.woff2']
FUNCAO = os.path.join(ADMIN, 'supabase', 'functions', 'convidar')
SEGREDO = re.compile(r'sb_secret_[A-Za-z0-9_-]{16,}|eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]*cm9sZSI6InNlcnZpY2Vfcm9sZS')


def cfg():
    return netlify.ler_env(AQUI)


def ok(msg):
    print('  ✓', msg)


def gravar_env(valores, pasta=None):
    """Atualiza (ou acrescenta) chaves no .env sem mexer nas outras linhas. Nunca imprime os valores."""
    caminho = os.path.join(pasta or AQUI, '.env')
    linhas = []
    if os.path.exists(caminho):
        with open(caminho, encoding='utf-8') as fh:
            linhas = fh.read().splitlines()
    feitas = set()
    for i, linha in enumerate(linhas):
        k = linha.split('=', 1)[0].strip()
        if k in valores and not linha.lstrip().startswith('#'):
            linhas[i] = f'{k}={valores[k]}'
            feitas.add(k)
    for k, v in valores.items():
        if k not in feitas:
            linhas.append(f'{k}={v}')
    with open(caminho, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(linhas) + '\n')
    try:
        os.chmod(caminho, 0o600)
    except OSError:
        pass


def escrever_config(url, chave_publica, pasta=None):
    if SEGREDO.search(chave_publica) or chave_publica.startswith('sb_secret_'):
        raise ErroSupabase('Recusado: isso é uma chave secreta, não pode ir para o app do navegador.')
    texto = ('// Gerado por "python3 painel_admin.py configurar". Só dados públicos: o endereço do projeto e a chave\n'
             '// publicável, que sozinha não abre nada: os dados exigem login e passam pelas regras de acesso do banco.\n'
             'window.RNQ_PAINEL_CONFIG = ' + json.dumps({'supabaseUrl': url.rstrip('/'), 'chavePublica': chave_publica},
                                                        indent=2) + ';\n')
    with open(os.path.join(pasta or ADMIN, 'config.js'), 'w', encoding='utf-8') as fh:
        fh.write(texto)


# ------------------------------------------------------------------------------------------------- e-mails
def _email(titulo_pt, texto_pt, titulo_en, texto_en, codigo=True):
    bloco_codigo = ('<p style="font-size:28px;letter-spacing:6px;font-weight:bold;margin:16px 0">{{ .Token }}</p>'
                    if codigo else '')
    botao = ('<p><a href="{{ .ConfirmationURL }}" style="background:#B4532A;color:#fff;padding:10px 18px;'
             'border-radius:8px;text-decoration:none;display:inline-block">Entrar no painel · Open the panel</a></p>')
    return (f'<div style="font-family:Georgia,serif;color:#2A1C13;max-width:520px">'
            f'<h2>{titulo_pt}</h2><p>{texto_pt}</p>{bloco_codigo}{botao}'
            f'<hr style="border:0;border-top:1px solid #E2D6C3;margin:20px 0">'
            f'<h3>{titulo_en}</h3><p>{texto_en}</p>'
            f'<p style="color:#6E5B4C;font-size:13px">Rede Novo Quilombo · Novo Quilombo Network. Se você não pediu '
            f'este e-mail, ignore. · If you did not ask for this e-mail, ignore it.</p></div>')


def campos_auth(painel_url, c):
    campos = {
        'site_url': painel_url,
        'uri_allow_list': f'{painel_url},{painel_url}/**',
        'disable_signup': True,                       # CA23: só entra quem foi convidado
        'external_email_enabled': True,
        'mfa_totp_enroll_enabled': True,
        'mfa_totp_verify_enabled': True,
        'mailer_otp_length': 6,
        'mailer_otp_exp': 3600,
    }
    # Textos próprios dos e-mails (com o código de 6 dígitos, em PT e EN): o plano gratuito do Supabase só deixa
    # mudar os modelos com e-mail próprio (SMTP). Sem SMTP, valem os e-mails padrão, que trazem o link de acesso.
    modelos = {
        'mailer_subjects_magic_link': 'Seu acesso ao painel da RNQ · Your Novo Quilombo panel sign-in',
        'mailer_templates_magic_link_content': _email(
            'Seu código de acesso', 'Digite este código no painel (vale por 1 hora) ou use o botão.',
            'Your sign-in code', 'Type this code in the panel (valid for 1 hour) or use the button.'),
        'mailer_subjects_invite': 'Convite para o painel da RNQ · Invitation to the Novo Quilombo panel',
        'mailer_templates_invite_content': _email(
            'Você foi convidada(o) para tecer a rede',
            'Você agora faz parte da equipe de tecelagem da Rede Novo Quilombo. Use o botão para entrar.',
            'You were invited to weave the network',
            'You are now part of the Novo Quilombo Network weaving team. Use the button to sign in.', codigo=False),
    }
    if c.get('SMTP_HOST'):
        campos.update(modelos)                            # e-mail próprio (necessário para convidar outras pessoas)
        campos.update({
            'smtp_host': c['SMTP_HOST'], 'smtp_port': str(c.get('SMTP_PORT') or '587'),
            'smtp_user': c.get('SMTP_USER', ''), 'smtp_pass': c.get('SMTP_PASS', ''),
            'smtp_admin_email': c.get('SMTP_ADMIN_EMAIL') or c.get('SMTP_USER', ''),
            'smtp_sender_name': c.get('SMTP_SENDER_NAME') or 'Rede Novo Quilombo',
            'rate_limit_email_sent': 30,
        })
    return campos


def ler_funcao():
    arquivos = {}
    for nome in ('index.ts', 'logica.js'):
        with open(os.path.join(FUNCAO, nome), encoding='utf-8') as fh:  # noqa: PTH123
            arquivos[nome] = fh.read()
    return arquivos


# ------------------------------------------------------------------------------------------------- comandos
def configurar(c=None, gestao=None, banco=None):
    c = c or cfg()
    faltam = [k for k in ('SUPABASE_ACCESS_TOKEN', 'SUPABASE_PROJECT_REF', 'RNQ_ADMIN_EMAIL') if not c.get(k)]
    if faltam:
        print('Faltam no .env:', ', '.join(faltam))
        print('Veja o passo a passo em docs/PAINEL-ADMIN.md (seção "Preparar uma vez").')
        return 1
    painel_url = (c.get('RNQ_PAINEL_URL') or PAINEL_URL_PADRAO).rstrip('/')
    g = gestao or Gestao(c['SUPABASE_ACCESS_TOKEN'], c['SUPABASE_PROJECT_REF'])
    print('Preparando o painel admin no Supabase…')
    proj = g.projeto() or {}
    ok(f'projeto "{proj.get("name", c["SUPABASE_PROJECT_REF"])}" ({proj.get("region", "?")})')
    if proj.get('region') and proj['region'] != 'sa-east-1':
        print('  ! O projeto não está em São Paulo (sa-east-1). Para a LGPD, prefira criar em South America.')

    with open(os.path.join(ADMIN, 'supabase', 'schema.sql'), encoding='utf-8') as fh:
        g.sql(fh.read())
    ok('banco: tabelas, regras de acesso (RLS), auditoria e funções')

    g.configurar_auth(campos_auth(painel_url, c))
    ok(f'login: só por convite, código por e-mail, MFA, endereço {painel_url}')
    if not c.get('SMTP_HOST'):
        print('  ! Sem e-mail próprio (SMTP): vale o e-mail padrão do Supabase (com o link de acesso, em inglês),')
        print('    que só chega para quem é da equipe do projeto e no máximo 2 por hora. Para você, basta.')
        print('    Antes de convidar outras pessoas, configure SMTP (docs/PAINEL-ADMIN.md).')

    publica, secreta = escolher_chaves(g.chaves())
    url = f'https://{c["SUPABASE_PROJECT_REF"]}.supabase.co'
    escrever_config(url, publica)
    gravar_env({'SUPABASE_URL': url, 'SUPABASE_SECRET_KEY': secreta, 'RNQ_PAINEL_URL': painel_url})
    ok('chaves: a publicável em admin/config.js, a secreta só no .env deste Mac')

    g.publicar_funcao('convidar', ler_funcao())
    g.segredos({'RNQ_PAINEL_URL': painel_url, 'RNQ_CHAVE_PUBLICA': publica, 'RNQ_CHAVE_SECRETA': secreta})
    ok('função de convite publicada (Edge Function "convidar")')

    b = banco or Banco(url, secreta)
    email = c['RNQ_ADMIN_EMAIL'].strip().lower()
    nome = c.get('RNQ_ADMIN_NOME') or ''
    uid = b.rpc('rnq_usuario_por_email', {'p_email': email})
    existia = bool(uid)
    if not existia:                                   # rodar de novo não manda outro convite
        uid = b.convidar(email, painel_url, {'nome': nome})
    b.rpc('rnq_convite_registrar', {'p_user': uid, 'p_email': email, 'p_nome': nome, 'p_papel': 'admin',
                                    'p_comunidades': [], 'p_idioma': 'pt', 'p_convidado_por': None})
    ok(f'admin: {email}' + (' (já tinha conta)' if existia else ' — convite enviado por e-mail'))
    print()
    print('Pronto. Agora:')
    print('  1. python3 painel_admin.py publicar     (põe o app no ar)')
    print('  2. python3 atualizar.py                 (manda os dados para o painel)')
    print(f'  3. abra {painel_url}, entre com {email} e cadastre o app autenticador')
    return 0


def status(c=None, banco=None):
    c = c or cfg()
    if not admin.configurado(c):
        print('Painel admin não configurado neste Mac (faltam SUPABASE_URL e SUPABASE_SECRET_KEY no .env).')
        print('Rode: python3 painel_admin.py configurar')
        return 1
    b = banco or admin.banco(c)
    s = b.rpc('rnq_pipeline_status') or {}
    print('Painel admin:', c.get('RNQ_PAINEL_URL') or '(endereço não definido no .env)')
    print(f'  banco versão {s.get("schema")} · {s.get("equipe")} pessoa(s) na equipe ({s.get("admins")} admin)')
    print(f'  {s.get("pendentes")} item(ns) esperando moderação, de {s.get("itens")} · {s.get("comunidades")} comunidades')
    print(f'  última atualização dos dados: {s.get("ultimo_snapshot") or "nunca (rode python3 atualizar.py)"}')
    if not os.path.exists(os.path.join(ADMIN, 'config.js')):
        print('  ! admin/config.js não existe: rode "python3 painel_admin.py configurar" antes de publicar.')
    return 0


def montar_pasta(destino=None, demo=False, segredos=()):
    destino = destino or PASTA_PUBLICAR
    if not demo and not os.path.exists(os.path.join(ADMIN, 'config.js')):
        raise FileNotFoundError('admin/config.js não existe. Rode "python3 painel_admin.py configurar" antes '
                                '(ou publique só a demonstração com --demo).')
    if os.path.exists(destino):
        shutil.rmtree(destino, ignore_errors=True)
    for rel in PUBLICAR:
        origem = os.path.join(ADMIN, rel)
        if rel == 'config.js' and demo:                # demonstração: sem projeto, abre a rede fictícia
            os.makedirs(destino, exist_ok=True)
            with open(os.path.join(destino, rel), 'w', encoding='utf-8') as fh:
                fh.write('// Demonstração: sem projeto Supabase, o painel abre com a rede fictícia.\n'
                         'window.RNQ_PAINEL_CONFIG = null;\n')
            continue
        if not os.path.exists(origem):
            raise FileNotFoundError(f'admin/{rel} não encontrado')
        alvo = os.path.join(destino, rel)
        os.makedirs(os.path.dirname(alvo), exist_ok=True)
        shutil.copy2(origem, alvo)
    for raiz, _, arquivos in os.walk(destino):
        for nome in arquivos:
            caminho = os.path.join(raiz, nome)
            rel = os.path.relpath(caminho, destino)
            if rel not in PUBLICAR:
                raise RuntimeError(f'Arquivo fora da lista na pasta de publicação: {rel}')
            if nome.endswith(('.js', '.html', '.css', '.toml', '_headers')):
                with open(caminho, encoding='utf-8') as fh:
                    texto = fh.read()
                if SEGREDO.search(texto) or any(s and s in texto for s in segredos):
                    raise RuntimeError(f'RECUSADO: {rel} contém uma chave secreta.')
    return destino


def _criar_site(token, nome):
    import urllib.request
    req = urllib.request.Request('https://api.netlify.com/api/v1/sites', method='POST',
                                 data=json.dumps({'name': nome}).encode(),
                                 headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json',
                                          'User-Agent': 'rnq-painel-admin'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def publicar(so_pasta=False, demo=False, c=None):
    c = c or cfg()
    segredos = [c.get('SUPABASE_SECRET_KEY'), c.get('SUPABASE_SERVICE_ROLE_KEY'), c.get('SUPABASE_ACCESS_TOKEN'),
                c.get('NETLIFY_TOKEN')]
    pasta = montar_pasta(demo=demo, segredos=[s for s in segredos if s])
    print('Pasta pronta:', pasta, '(demonstração, sem dados reais)' if demo else '')
    if so_pasta:
        print('Arraste essa pasta em https://app.netlify.com/drop (site novo) ou em Netlify > painel > Deploys.')
        return 0
    if not c.get('NETLIFY_TOKEN'):
        print('Falta NETLIFY_TOKEN no .env (docs/DEPLOY.md). Ou arraste a pasta acima em https://app.netlify.com/drop')
        return 1
    site = c.get('NETLIFY_PAINEL_SITE_ID')
    if not site:
        nome = (c.get('RNQ_PAINEL_URL') or PAINEL_URL_PADRAO).split('//')[-1].split('.')[0] or NOME_SITE_PADRAO
        criado = _criar_site(c['NETLIFY_TOKEN'], nome)
        site = criado['id']
        gravar_env({'NETLIFY_PAINEL_SITE_ID': site, 'RNQ_PAINEL_URL': criado.get('ssl_url') or criado.get('url')})
        ok(f'site criado no Netlify: {criado.get("ssl_url") or criado.get("url")}')
    env = dict(os.environ, NETLIFY_AUTH_TOKEN=c['NETLIFY_TOKEN'])
    cmd = ['npx', '-y', 'netlify-cli@latest', 'deploy', '--prod', '--dir', pasta, '--site', site,
           '--message', 'painel_admin.py publicar']
    print('Publicando o painel…')
    return subprocess.run(cmd, cwd=AQUI, env=env).returncode


# ------------------------------------------------------------------------------------------------- demonstração
DEMO_EQUIPE = [
    {'nome': 'Ana Demonstração', 'email': 'ana@exemplo.org', 'papel': 'admin', 'comunidades': [], 'mfa': True},
    {'nome': 'Iara Exemplo', 'email': 'iara@exemplo.org', 'papel': 'tecelao', 'comunidades': ['tecnologia', 'esg'],
     'mfa': False},
    {'nome': 'Caio Fictício', 'email': 'caio@exemplo.org', 'papel': 'tecelao', 'comunidades': ['cultura-regenerativa'],
     'mfa': True},
]


def montar_demo(agora=None):
    """Dados do modo demonstração: rede fictícia de exemplo, moderação e equipe inventadas."""
    import exportar
    from exemplo.gerar_exemplo import gerar
    agora = agora or datetime(2026, 10, 15, 9, 0)
    pasta = tempfile.mkdtemp(prefix='rnq-demo-')
    try:
        gerar(pasta, com_tecelagem=True)
        ctx = {}
        exportar.executar(pasta=pasta, agora=agora, silencioso=True, site=os.path.join(pasta, 'site'),
                          sem_painel=True, contexto=ctx)
        pk = admin.montar_sincronizacao(ctx['pub'], ctx['interno'], ctx['tec'], ctx['sug'], ctx['avisos'],
                                        ctx['historico'], agora)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
    itens = []
    for i, it in enumerate(pk['itens'], 1):
        it = dict(it, id=i, status='pendente', decidido_por_nome=None, decidido_em=None, motivo=None,
                  origem_decisao=None, atualizado_em=it['recebido_em'])
        it.pop('status_planilha', None)
        itens.append(it)
    # algumas decisões já tomadas, para o histórico não ficar vazio
    for idx, (st, quem, motivo) in {1: ('aprovado', 'Iara Exemplo', None),
                                    7: ('recusado', 'Ana Demonstração', 'As duas pessoas ainda não se conhecem')}.items():
        if idx <= len(itens):
            itens[idx - 1].update(status=st, decidido_por_nome=quem, decidido_em=agora.isoformat() + '-03:00',
                                  motivo=motivo, origem_decisao='painel')
    equipe = [dict(p, user_id=f'demo-{i}', idioma='pt', ativo=True, criado_em='2026-10-01T10:00:00-03:00',
                   ultimo_acesso='2026-10-15T08:30:00-03:00') for i, p in enumerate(DEMO_EQUIPE)]
    auditoria = [
        {'id': 3, 'quem_email': 'iara@exemplo.org', 'acao': 'moderacao.decidir', 'alvo': f'{itens[0]["tipo"]}:{itens[0]["item_id"]}',
         'quando': '2026-10-14T18:20:00-03:00', 'detalhes': {'de': 'pendente', 'para': 'aprovado', 'titulo': itens[0]['titulo']}},
        {'id': 2, 'quem_email': 'ana@exemplo.org', 'acao': 'equipe.convidar', 'alvo': 'caio@exemplo.org',
         'quando': '2026-10-10T11:00:00-03:00', 'detalhes': {'papel': 'tecelao', 'comunidades': ['cultura-regenerativa']}},
        {'id': 1, 'quem_email': None, 'acao': 'pipeline.sincronizar', 'alvo': 'rede',
         'quando': '2026-10-15T09:00:00-03:00', 'detalhes': {'itens_novos': len(itens), 'snapshots': len(pk['snapshots'])}},
    ]
    return {'exemplo': True, 'gerado_em': pk['gerado_em'], 'comunidades': pk['comunidades'],
            'snapshots': [dict(s, gerado_em=pk['gerado_em']) for s in pk['snapshots']],
            'moderacao': itens, 'equipe': equipe, 'auditoria': auditoria}


def demo(destino=None):
    destino = destino or os.path.join(ADMIN, 'demo-dados.js')
    dados = montar_demo()
    with open(destino, 'w', encoding='utf-8') as fh:
        fh.write('// Modo demonstração do painel admin: rede 100% fictícia (exemplo/gerar_exemplo.py).\n'
                 '// Gerado por "python3 painel_admin.py demo". Não contém dados de pessoas reais.\n'
                 'window.RNQ_DEMO = ' + json.dumps(dados, ensure_ascii=False) + ';\n')
    print('Demonstração gerada:', os.path.relpath(destino, AQUI),
          f'({len(dados["snapshots"])} visões, {len(dados["moderacao"])} itens)')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='comando', required=True)
    sub.add_parser('configurar', help='prepara o Supabase (banco, login, função de convite) e o 1º admin')
    p = sub.add_parser('publicar', help='publica o app do painel no Netlify')
    p.add_argument('--so-pasta', action='store_true', help='só monta a pasta, para arrastar no Netlify')
    p.add_argument('--demo', action='store_true', help='publica só o modo demonstração (sem config.js)')
    sub.add_parser('status', help='confere a conexão e mostra os números')
    sub.add_parser('demo', help='regenera admin/demo-dados.js')
    a = ap.parse_args(argv)
    try:
        if a.comando == 'configurar':
            return configurar()
        if a.comando == 'publicar':
            return publicar(so_pasta=a.so_pasta, demo=a.demo)
        if a.comando == 'status':
            return status()
        return demo()
    except (ErroSupabase, FileNotFoundError, RuntimeError) as err:
        print('ERRO:', err)
        return 2


if __name__ == '__main__':
    sys.exit(main())
