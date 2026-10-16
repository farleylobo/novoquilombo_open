"""painel_admin.py (configurar, publicar, status, demo) e a integração com atualizar.py — sem rede."""
import io
import json
import os
import re
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

import apoio  # noqa: F401

import atualizar
import painel_admin
from rnq import admin
from rnq.supabase import ErroSupabase


class GestaoFalsa:
    def __init__(self, regiao='sa-east-1'):
        self.chamadas = []
        self.regiao = regiao

    def projeto(self):
        return {'name': 'rnq-painel', 'region': self.regiao}

    def sql(self, q):
        self.chamadas.append(('sql', len(q)))

    def configurar_auth(self, campos):
        self.chamadas.append(('auth', campos))

    def chaves(self):
        return [{'type': 'publishable', 'api_key': 'sb_publishable_ABC'},
                {'type': 'secret', 'api_key': 'sb_secret_' + 'X' * 30}]

    def publicar_funcao(self, slug, arquivos, verificar_jwt=True):
        self.chamadas.append(('funcao', slug, sorted(arquivos), verificar_jwt))

    def exigir_login_na_funcao(self, slug, exigir):
        self.chamadas.append(('login_funcao', slug, exigir))

    def segredos(self, pares):
        self.chamadas.append(('segredos', pares))


class BancoFalso:
    def __init__(self, existente=None):
        self.chamadas = []
        self.existente = existente

    def rpc(self, nome, args=None):
        self.chamadas.append((nome, args))
        if nome == 'rnq_usuario_por_email':
            return self.existente
        if nome == 'rnq_pipeline_status':
            return {'schema': '1', 'equipe': 1, 'admins': 1, 'pendentes': 3, 'itens': 9, 'comunidades': 6,
                    'ultimo_snapshot': '2026-10-15T09:00:00-03:00'}
        return {'user_id': 'u-1', 'novo': True}

    def convidar(self, email, redirecionar, dados=None):
        self.chamadas.append(('convidar', email, redirecionar))
        return 'u-novo'


class Configurar(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.admin = os.path.join(self.pasta, 'admin')
        shutil.copytree(painel_admin.ADMIN, self.admin, ignore=shutil.ignore_patterns('config.js'))
        self.cfg = {'SUPABASE_ACCESS_TOKEN': 'sbp_teste', 'SUPABASE_PROJECT_REF': 'abcdefghijklmnopqrst',
                    'RNQ_ADMIN_EMAIL': 'Farley@Exemplo.org', 'RNQ_ADMIN_NOME': 'Farley'}

    def tearDown(self):
        shutil.rmtree(self.pasta)

    def rodar(self, gestao, banco, cfg=None):
        saida = io.StringIO()
        with mock.patch.object(painel_admin, 'ADMIN', self.admin), \
             mock.patch.object(painel_admin, 'AQUI', self.pasta), \
             mock.patch.object(painel_admin, 'FUNCAO', os.path.join(self.admin, 'supabase', 'functions', 'convidar')), \
             redirect_stdout(saida):
            r = painel_admin.configurar(cfg or self.cfg, gestao=gestao, banco=banco)
        return r, saida.getvalue()

    def test_faltando_dados_explica_e_nao_chama_nada(self):
        g = GestaoFalsa()
        r, saida = self.rodar(g, BancoFalso(), {'SUPABASE_PROJECT_REF': 'x'})
        self.assertEqual(r, 1)
        self.assertIn('SUPABASE_ACCESS_TOKEN', saida)
        self.assertEqual(g.chamadas, [])

    def test_configura_tudo_na_ordem_e_nao_imprime_a_chave_secreta(self):
        g, b = GestaoFalsa(), BancoFalso()
        r, saida = self.rodar(g, b)
        self.assertEqual(r, 0)
        self.assertEqual([c[0] for c in g.chamadas], ['sql', 'auth', 'funcao', 'funcao', 'login_funcao', 'segredos'])
        self.assertEqual(g.chamadas[3][1:], ('receber', ['contrato.json', 'index.ts', 'logica.js'], False))
        self.assertEqual(g.chamadas[4], ('login_funcao', 'receber', False))
        auth = g.chamadas[1][1]
        self.assertTrue(auth['disable_signup'])
        self.assertTrue(auth['mfa_totp_enroll_enabled'] and auth['mfa_totp_verify_enabled'])
        self.assertEqual(auth['site_url'], 'https://painel-novoquilombo.netlify.app')
        self.assertNotIn('mailer_templates_magic_link_content', auth, 'plano gratuito sem SMTP não aceita modelos')
        self.assertEqual(g.chamadas[2][1:3], ('convidar', ['index.ts', 'logica.js']))
        seg = g.chamadas[5][1]
        self.assertEqual(seg['RNQ_PAINEL_URL'], 'https://painel-novoquilombo.netlify.app')
        self.assertEqual(seg['RNQ_CHAVE_PUBLICA'], 'sb_publishable_ABC')
        self.assertGreaterEqual(len(seg['RNQ_RECEBER_SEGREDO']), 32)
        self.assertEqual(seg['RNQ_SITE_NOME'], 'mapa-novoquilombo')
        self.assertNotIn(seg['RNQ_RECEBER_SEGREDO'], saida, 'a chave da função não aparece no Terminal')
        self.assertNotIn('sb_secret_', saida)
        with open(os.path.join(self.admin, 'config.js'), encoding='utf-8') as fh:
            cfgjs = fh.read()
        self.assertIn('sb_publishable_ABC', cfgjs)
        self.assertIn('https://abcdefghijklmnopqrst.supabase.co', cfgjs)
        self.assertNotIn('sb_secret_', cfgjs)
        with open(os.path.join(self.pasta, '.env'), encoding='utf-8') as fh:
            env = fh.read()
        self.assertIn('SUPABASE_SECRET_KEY=sb_secret_', env)
        self.assertIn('RNQ_RECEBER_SEGREDO=' + seg['RNQ_RECEBER_SEGREDO'], env)
        self.assertIn('Sem NETLIFY_TOKEN', saida)
        self.assertIn('SUPABASE_URL=https://abcdefghijklmnopqrst.supabase.co', env)
        reg = [c for c in b.chamadas if c[0] == 'rnq_convite_registrar'][0][1]
        self.assertEqual((reg['p_email'], reg['p_papel'], reg['p_user']), ('farley@exemplo.org', 'admin', 'u-novo'))
        self.assertIn(('convidar', 'farley@exemplo.org', 'https://painel-novoquilombo.netlify.app'), b.chamadas)

    def test_rodar_de_novo_nao_manda_outro_convite(self):
        b = BancoFalso(existente='u-velho')
        r, saida = self.rodar(GestaoFalsa(), b)
        self.assertEqual(r, 0)
        self.assertFalse(any(c[0] == 'convidar' for c in b.chamadas))
        self.assertIn('já tinha conta', saida)

    def test_avisa_fora_de_sao_paulo_e_sem_smtp(self):
        _, saida = self.rodar(GestaoFalsa(regiao='us-east-1'), BancoFalso())
        self.assertIn('São Paulo', saida)
        self.assertIn('SMTP', saida)

    def test_smtp_proprio_entra_na_configuracao(self):
        cfg = dict(self.cfg, SMTP_HOST='smtp.gmail.com', SMTP_USER='rnqbrasil@gmail.com', SMTP_PASS='senha-app')
        campos = painel_admin.campos_auth('https://p', cfg)
        self.assertEqual((campos['smtp_host'], campos['smtp_port'], campos['smtp_admin_email']),
                         ('smtp.gmail.com', '587', 'rnqbrasil@gmail.com'))
        self.assertIn('{{ .Token }}', campos['mailer_templates_magic_link_content'])

    def test_nunca_grava_chave_secreta_no_app(self):
        with self.assertRaises(ErroSupabase):
            painel_admin.escrever_config('https://x.supabase.co', 'sb_secret_' + 'Y' * 30, self.admin)




class HooksFalsos:
    def __init__(self, existentes=()):
        self.avisos_ = list(existentes)
        self.criados, self.apagados = [], []

    def ligar(self, url, nomes):
        from rnq.supabase import NetlifyHooks
        h = NetlifyHooks.__new__(NetlifyHooks)
        forms = [{'name': n, 'id': 'f-' + n} for n in nomes] + [{'name': 'opt-out', 'id': 'f-opt-out'}]
        h.formularios = lambda: forms
        h.avisos = lambda: self.avisos_
        h.criar = lambda fid, u: self.criados.append((fid, u))
        h.apagar = lambda hid: self.apagados.append(hid)
        return NetlifyHooks.ligar(h, url, nomes)


class LigarFormularios(unittest.TestCase):
    C = {'NETLIFY_TOKEN': 'nfp_x', 'NETLIFY_SITE_ID': 'site', 'SUPABASE_URL': 'https://abc.supabase.co',
         'RNQ_RECEBER_SEGREDO': 's' * 40}

    def test_um_aviso_por_formulario_moderado(self):
        h = HooksFalsos()
        with redirect_stdout(io.StringIO()):
            r = painel_admin.ligar_formularios(self.C, hooks=h)
        self.assertEqual(r['criados'], 7)
        self.assertNotIn('f-opt-out', [f for f, _ in h.criados], 'saídas seguem pelo Mac')
        self.assertTrue(all(u == 'https://abc.supabase.co/functions/v1/receber?chave=' + 's' * 40 for _, u in h.criados))

    def test_rodar_de_novo_nao_duplica_e_troca_chave_antiga(self):
        url = painel_admin.url_receber(self.C)
        existentes = [{'id': 'h1', 'event': 'submission_created', 'form_id': 'f-mural', 'data': {'url': url}},
                      {'id': 'h2', 'event': 'submission_created', 'form_id': 'f-perfil',
                       'data': {'url': 'https://abc.supabase.co/functions/v1/receber?chave=velha'}},
                      {'id': 'h3', 'event': 'submission_created', 'form_id': 'f-mural', 'data': {'url': 'https://outro.app/x'}}]
        h = HooksFalsos(existentes)
        with redirect_stdout(io.StringIO()):
            r = painel_admin.ligar_formularios(self.C, hooks=h)
        self.assertEqual((r['mantidos'], r['apagados'], r['criados']), (1, 1, 6))
        self.assertEqual(h.apagados, ['h2'], 'não mexe em avisos de outros serviços')

    def test_sem_token_do_netlify_explica(self):
        with redirect_stdout(io.StringIO()) as s:
            self.assertIsNone(painel_admin.ligar_formularios({}))
        self.assertIn('NETLIFY_TOKEN', s.getvalue())


class Rotina(unittest.TestCase):
    CFG = {'SUPABASE_URL': 'https://x.supabase.co', 'SUPABASE_SECRET_KEY': 'sb_secret_x'}

    def rodar(self, codigos):
        feitos = []

        def rodar(cmd):
            feitos.append(os.path.basename(cmd[1]))
            return mock.Mock(returncode=codigos.get(os.path.basename(cmd[1]), 0), stdout='saída\núltima linha', stderr='')
        b = BancoFalso()
        with redirect_stdout(io.StringIO()):
            r = painel_admin.rotina(self.CFG, rodar=rodar, banco=b)
        regs = {a['p_chave']: a['p_valor'] for n, a in b.chamadas if n == 'rnq_pipeline_registrar'}
        return r, feitos, regs

    def test_atualiza_publica_e_avisa_o_painel(self):
        r, feitos, regs = self.rodar({})
        self.assertEqual(r, 0)
        self.assertEqual(feitos, ['atualizar.py', 'publicar.py'])
        self.assertTrue(regs['ultima_publicacao']['ok'])
        self.assertTrue(regs['ultima_publicacao']['automatica'])
        self.assertTrue(regs['rotina_diaria']['ok'])

    def test_se_atualizar_falha_nao_publica_e_mostra_o_erro_no_painel(self):
        r, feitos, regs = self.rodar({'atualizar.py': 3})
        self.assertEqual(r, 1)
        self.assertEqual(feitos, ['atualizar.py'])
        self.assertEqual(regs['ultima_publicacao']['etapa'], 'atualizar')
        self.assertEqual(regs['ultima_publicacao']['erro'], 'última linha')

    def test_plist_do_macos(self):
        import plistlib
        p = plistlib.loads(painel_admin.montar_plist(7, python='/usr/bin/python3', path_env='/usr/local/bin:/usr/bin'))
        self.assertEqual(p['Label'], 'org.novoquilombo.rotina')
        self.assertEqual(p['StartCalendarInterval'], {'Hour': 7, 'Minute': 0})
        self.assertEqual(p['ProgramArguments'][1:], [os.path.join(painel_admin.AQUI, 'painel_admin.py'), 'rotina'])
        self.assertEqual(p['EnvironmentVariables']['PATH'], '/usr/local/bin:/usr/bin', 'precisa achar o npx')
        self.assertFalse(p['RunAtLoad'])

    def test_automatizar_liga_e_desliga(self):
        home = tempfile.mkdtemp()
        cmds = []
        sistema = lambda cmd: cmds.append(cmd) or mock.Mock(returncode=0, stderr='')
        b = BancoFalso()
        with mock.patch.dict(os.environ, {'HOME': home}), redirect_stdout(io.StringIO()) as s:
            self.assertEqual(painel_admin.automatizar(7, c=self.CFG, sistema=sistema, banco=b), 0)
            self.assertTrue(os.path.exists(painel_admin.caminho_plist()))
            self.assertEqual(painel_admin.estado_rotina(), {'ligada': True, 'hora': '07:00'})
            self.assertEqual(painel_admin.automatizar(25, c=self.CFG, sistema=sistema, banco=b), 1)
            self.assertEqual(painel_admin.automatizar(desligar=True, c=self.CFG, sistema=sistema, banco=b), 0)
            self.assertFalse(os.path.exists(painel_admin.caminho_plist()))
        self.assertIn(['launchctl', 'bootstrap', f'gui/{os.getuid()}', os.path.join(home, 'Library/LaunchAgents/org.novoquilombo.rotina.plist')], cmds)
        self.assertIn('todo dia às 07:00', s.getvalue())
        estados = [a['p_valor'] for n, a in b.chamadas if n == 'rnq_pipeline_registrar']
        self.assertEqual([e['ligada'] for e in estados], [True, False])
        shutil.rmtree(home)


class Env(unittest.TestCase):
    def test_gravar_env_preserva_as_outras_linhas(self):
        d = tempfile.mkdtemp()
        try:
            with open(os.path.join(d, '.env'), 'w') as fh:
                fh.write('# comentário\nNETLIFY_TOKEN=abc\nSUPABASE_URL=velho\n')
            painel_admin.gravar_env({'SUPABASE_URL': 'novo', 'SUPABASE_SECRET_KEY': 's'}, d)
            with open(os.path.join(d, '.env')) as fh:
                linhas = fh.read().splitlines()
            self.assertEqual(linhas, ['# comentário', 'NETLIFY_TOKEN=abc', 'SUPABASE_URL=novo', 'SUPABASE_SECRET_KEY=s'])
            self.assertEqual(os.stat(os.path.join(d, '.env')).st_mode & 0o777, 0o600)
        finally:
            shutil.rmtree(d)


class Publicar(unittest.TestCase):
    def setUp(self):
        self.destino = os.path.join(tempfile.mkdtemp(), 'pub')

    def test_demo_monta_a_lista_fechada_sem_projeto(self):
        painel_admin.montar_pasta(self.destino, demo=True)
        arquivos = sorted(os.path.relpath(os.path.join(r, f), self.destino)
                          for r, _, fs in os.walk(self.destino) for f in fs)
        self.assertEqual(arquivos, sorted(painel_admin.PUBLICAR))
        with open(os.path.join(self.destino, 'config.js')) as fh:
            self.assertIn('RNQ_PAINEL_CONFIG = null', fh.read())

    def test_sem_config_nao_publica_o_painel_de_verdade(self):
        with mock.patch.object(painel_admin.os.path, 'exists', lambda p: False if p.endswith('config.js') else os.path.lexists(p)):
            with self.assertRaises(FileNotFoundError):
                painel_admin.montar_pasta(self.destino)

    def test_recusa_se_algum_arquivo_tiver_a_chave_secreta(self):
        segredo = 'segredo-do-env-1234567890'
        with mock.patch.object(painel_admin, 'SEGREDO', re.compile('nunca-casa')):
            with self.assertRaises(RuntimeError):
                painel_admin.montar_pasta(self.destino, demo=True, segredos=['window.RNQ_I18N'])
        painel_admin.montar_pasta(self.destino, demo=True, segredos=[segredo])


class Status(unittest.TestCase):
    def test_sem_configuracao(self):
        with redirect_stdout(io.StringIO()) as s:
            self.assertEqual(painel_admin.status({}), 1)
        self.assertIn('configurar', s.getvalue())

    def test_mostra_os_numeros(self):
        with redirect_stdout(io.StringIO()) as s:
            painel_admin.status({'SUPABASE_URL': 'u', 'SUPABASE_SECRET_KEY': 'k', 'RNQ_PAINEL_URL': 'https://p'},
                                banco=BancoFalso())
        self.assertIn('3 item(ns) esperando moderação', s.getvalue())


class Demo(unittest.TestCase):
    def test_demo_e_ficticia_e_completa(self):
        d = painel_admin.montar_demo()
        self.assertTrue(d['exemplo'])
        texto = json.dumps(d, ensure_ascii=False)
        contatos = set(re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', texto))
        self.assertTrue(contatos)
        self.assertTrue(all(c.endswith('@exemplo.org') for c in contatos), contatos)
        self.assertEqual({s['escopo'] for s in d['snapshots']} >= {'rede', 'tecnologia'}, True)
        self.assertEqual(len({i['id'] for i in d['moderacao']}), len(d['moderacao']))
        self.assertEqual(sum(1 for p in d['equipe'] if p['papel'] == 'admin'), 1)

    def test_arquivo_da_demo_esta_atualizado(self):
        with open(os.path.join(painel_admin.ADMIN, 'demo-dados.js'), encoding='utf-8') as fh:
            js = fh.read()
        gravado = json.loads(js[js.index('{'):js.rindex('}') + 1])
        self.assertEqual(gravado, json.loads(json.dumps(painel_admin.montar_demo())),
                         'rode "python3 painel_admin.py demo" depois de mudar o painel ou o exemplo')


class Atualizar(unittest.TestCase):
    CFG = {'SUPABASE_URL': 'https://x.supabase.co', 'SUPABASE_SECRET_KEY': 'sb_secret_x'}

    def test_sem_conexao_com_o_painel_nada_e_gerado(self):
        with mock.patch.object(atualizar.netlify, 'ler_env', return_value=self.CFG), \
             mock.patch.object(atualizar.admin, 'buscar_decisoes', side_effect=ErroSupabase('offline')), \
             mock.patch.object(atualizar.exportar, 'executar') as exp, redirect_stdout(io.StringIO()) as s:
            with self.assertRaises(SystemExit) as fim:
                atualizar.main([])
        self.assertEqual(fim.exception.code, 3)
        exp.assert_not_called()
        self.assertIn('NADA foi gerado', s.getvalue())

    def test_com_o_painel_aplica_decisoes_e_sincroniza(self):
        dec = [{'tipo': 'mural', 'item_id': 'a', 'status': 'aprovado'}]

        def exportar_falso(decisoes=None, contexto=None):
            self.assertEqual(decisoes, dec)
            contexto.update(pasta_hist='/tmp/x')
        ok = mock.Mock(returncode=0, stdout='', stderr='Ran 1 test\n\nOK')
        with mock.patch.object(atualizar.netlify, 'ler_env', return_value=dict(self.CFG, RNQ_PAINEL_URL='https://p')), \
             mock.patch.object(atualizar.admin, 'buscar_decisoes', return_value=dec), \
             mock.patch.object(atualizar.exportar, 'executar', side_effect=exportar_falso), \
             mock.patch.object(atualizar.admin, 'sincronizar', return_value={'snapshots': 7, 'itens_novos': 2}) as sinc, \
             mock.patch.object(atualizar.subprocess, 'run', return_value=ok), redirect_stdout(io.StringIO()) as s:
            atualizar.main([])
        sinc.assert_called_once()
        self.assertIn('7 visão(ões), 2 item(ns) novo(s)', s.getvalue())
        self.assertIn('Abra: https://p', s.getvalue())

    def test_emergencia_sem_painel(self):
        ok = mock.Mock(returncode=0, stdout='', stderr='OK')
        with mock.patch.object(atualizar.netlify, 'ler_env', return_value=self.CFG), \
             mock.patch.object(atualizar.admin, 'buscar_decisoes') as busca, \
             mock.patch.object(atualizar.exportar, 'executar') as exp, \
             mock.patch.object(atualizar.subprocess, 'run', return_value=ok), redirect_stdout(io.StringIO()):
            atualizar.main(['--sem-painel-admin'])
        busca.assert_not_called()
        self.assertIsNone(exp.call_args.kwargs['decisoes'])

    def test_sem_supabase_continua_como_antes(self):
        ok = mock.Mock(returncode=0, stdout='', stderr='OK')
        with mock.patch.object(atualizar.netlify, 'ler_env', return_value={}), \
             mock.patch.object(atualizar.exportar, 'executar') as exp, \
             mock.patch.object(atualizar.subprocess, 'run', return_value=ok), redirect_stdout(io.StringIO()) as s:
            atualizar.main([])
        self.assertIsNone(exp.call_args.kwargs['decisoes'])
        self.assertIn('não configurado', s.getvalue())


if __name__ == '__main__':
    unittest.main()
