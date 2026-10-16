"""Painel admin com login (SPEC-RNQ-003): decisões do painel valendo no site, itens de moderação, recorte por
comunidade sem vazar contatos, snapshots do painel e conversa com o Supabase (sem rede: urlopen falso)."""
import base64
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import unittest
import urllib.error
from datetime import datetime

from apoio import RAIZ, selecao_base, temas_base

import exportar
from exemplo.gerar_exemplo import gerar as gerar_exemplo
from rnq import admin, fontes, painel, publico
from rnq.supabase import Banco, ErroSupabase, Gestao, escolher_chaves

AGORA = datetime(2026, 10, 15, 9, 30)
ADMIN = os.path.join(RAIZ, 'admin')


def ler(*p):
    with open(os.path.join(*p), encoding='utf-8') as fh:
        return fh.read()


class _Exemplo:
    """Rede fictícia de exemplo com a planilha de tecelagem cheia de envios pendentes."""
    _cache = None

    @classmethod
    def contexto(cls, decisoes=None):
        if decisoes is None and cls._cache:
            return cls._cache
        d = tempfile.mkdtemp()
        gerar_exemplo(d, com_tecelagem=True)
        ctx = {}
        exportar.executar(pasta=d, agora=AGORA, silencioso=True, site=os.path.join(d, 'site'), sem_painel=True,
                          decisoes=decisoes, contexto=ctx)
        ctx['pasta'] = d
        if decisoes is None:
            cls._cache = ctx
        return ctx


def pacote(ctx):
    return admin.montar_sincronizacao(ctx['pub'], ctx['interno'], ctx['tec'], ctx['sug'], ctx['avisos'],
                                      ctx['historico'], ctx['agora'])


class Decisoes(unittest.TestCase):
    def tec(self):
        return {'Mural': [
            {'ID': 'a', 'Tipo': 'Oferta', 'Título': 'Mentoria', 'Nome': 'Ana Lima', 'Publicar?': None, 'Status': 'Aberto',
             'Contato (privado)': 'ana@x.org'},
            {'ID': 'b', 'Tipo': 'Pedido', 'Título': 'Espaço', 'Nome': 'Bruno Reis', 'Publicar?': 'Sim', 'Status': 'Aberto'},
            {'ID': 'c', 'Tipo': 'Pedido', 'Título': 'Novo', 'Nome': 'Carla Dias', 'Publicar?': 'Sim', 'Status': 'Aberto'},
        ]}

    def test_painel_vale_no_lugar_da_planilha(self):
        tec = self.tec()
        dec = [{'tipo': 'mural', 'item_id': 'a', 'status': 'aprovado'},
               {'tipo': 'mural', 'item_id': 'b', 'status': 'recusado'}]
        novo, avisos = admin.aplicar_decisoes(tec, dec)
        col = [r['Publicar?'] for r in novo['Mural']]
        self.assertEqual(col, ['Sim', 'Não', 'Sim'])          # c ainda não chegou ao painel: vale a planilha
        self.assertIsNone(tec['Mural'][0]['Publicar?'], 'não pode alterar o original')
        self.assertEqual(len(avisos), 1)
        self.assertIn('vale o painel', avisos[0])

    def test_pendente_no_painel_esvazia_a_coluna(self):
        novo, _ = admin.aplicar_decisoes(self.tec(), [{'tipo': 'mural', 'item_id': 'b', 'status': 'pendente'}])
        self.assertIsNone(novo['Mural'][1]['Publicar?'])

    def test_sem_painel_nada_muda(self):
        tec = self.tec()
        self.assertIs(admin.aplicar_decisoes(tec, None)[0], tec)

    def test_site_obedece_ao_painel(self):
        dec = [{'tipo': 'mural', 'item_id': 'a', 'status': 'aprovado'},
               {'tipo': 'mural', 'item_id': 'b', 'status': 'recusado'}]
        tec, _ = admin.aplicar_decisoes(self.tec(), dec)
        pub, _, _ = publico.montar(selecao_base(), temas_base(), tec, AGORA)
        self.assertEqual(sorted(m['titulo'] for m in pub['mural']), ['Mentoria', 'Novo'])
        self.assertNotIn('ana@x.org', json.dumps(pub))

    def test_exportar_aplica_as_decisoes(self):
        ctx = _Exemplo.contexto()
        mural = [i for i in pacote(ctx)['itens'] if i['tipo'] == 'mural']
        dec = [{'tipo': 'mural', 'item_id': mural[0]['item_id'], 'status': 'aprovado'}]
        ctx2 = _Exemplo.contexto(decisoes=dec)
        self.assertEqual(len(ctx2['pub']['mural']), 1)
        self.assertEqual(len(ctx['pub']['mural']), 0)


class Itens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = _Exemplo.contexto()
        cls.pk = pacote(cls.ctx)
        cls.itens = cls.pk['itens']

    def test_todos_os_tipos_e_ids_unicos(self):
        self.assertEqual({i['tipo'] for i in self.itens}, set(admin.TIPOS))
        chaves = [(i['tipo'], i['item_id']) for i in self.itens]
        self.assertEqual(len(chaves), len(set(chaves)))

    def test_tipos_batem_com_o_banco(self):
        sql = ler(ADMIN, 'supabase', 'schema.sql')
        m = re.search(r"tipo\s+text not null check \(tipo in \(([^)]*)\)", sql)
        self.assertEqual(set(re.findall(r"'(\w+)'", m.group(1))), set(admin.TIPOS))

    def test_contato_fica_no_privado(self):
        for i in self.itens:
            publicos = json.dumps(i['conteudo'], ensure_ascii=False)
            self.assertNotIn('@exemplo.org', publicos, i['titulo'])
            self.assertNotIn('(privado)', publicos)
        m = next(i for i in self.itens if i['tipo'] == 'mural')
        self.assertTrue(any(c == 'Contato (privado)' and v.endswith('@exemplo.org') for c, v in m['privado']['campos']))

    def test_cadastro_fora_do_mapa_fica_bloqueado(self):
        cad = {i['titulo']: i for i in self.itens if i['tipo'] == 'cadastro'}
        self.assertEqual(cad['Igor Reservado']['conteudo']['bloqueio'], 'fora_do_mapa')
        self.assertIsNone(cad['Helena Exemplar']['conteudo']['bloqueio'])

    def test_comunidades_do_item(self):
        cad = next(i for i in self.itens if i['titulo'] == 'Helena Exemplar')
        self.assertEqual(cad['comunidades'], ['cultura-regenerativa'])
        tec = next(i for i in self.itens if 'mentoria em análise de dados' in i['titulo'].lower())
        self.assertIn('tecnologia', tec['comunidades'])
        resp = next(i for i in self.itens if i['tipo'] == 'resposta')
        mural1 = next(i for i in self.itens if i['item_id'] == 'ex-mural-1')
        self.assertTrue(set(mural1['comunidades']) <= set(resp['comunidades']))

    def test_status_da_planilha_vira_semente(self):
        self.assertEqual(admin.status_da_planilha('mural', 'Sim'), 'aprovado')
        self.assertEqual(admin.status_da_planilha('mural', 'Não'), 'recusado')
        self.assertEqual(admin.status_da_planilha('mural', None), 'pendente')

    def test_id_estavel_sem_id_do_netlify(self):
        r = {'Tipo': 'Oferta', 'Título': 'X', 'Nome': 'Ana'}
        self.assertEqual(admin.item_id('mural', r), admin.item_id('mural', dict(r)))
        self.assertNotEqual(admin.item_id('mural', r), admin.item_id('mural', dict(r, Título='Y')))

    def test_quando_tem_fuso_de_brasilia(self):
        self.assertEqual(admin._quando('2026-10-06 10:00'), '2026-10-06T10:00:00-03:00')
        self.assertIsNone(admin._quando('ontem'))

    def test_pacote_e_json_com_data_e_fuso(self):
        json.dumps(self.pk)
        self.assertTrue(self.pk['gerado_em'].endswith('-03:00'))
        self.assertTrue(all(c['nome'] for c in self.pk['comunidades']))


class LinkNoMapa(unittest.TestCase):
    def test_itens_apontam_para_o_card_certo_no_mapa(self):
        ctx = _Exemplo.contexto()
        itens = {(i['tipo'], i['item_id']): i for i in pacote(ctx)['itens']}
        ids = {p['id'] for p in ctx['pub']['pessoas']}
        cad = next(i for i in itens.values() if i['titulo'] == 'Helena Exemplar')
        self.assertIsNone(cad['conteudo']['mapa'], 'cadastro pendente ainda não está no mapa')
        perfil = next(i for i in itens.values() if i['tipo'] == 'perfil')
        self.assertTrue(perfil['conteudo']['mapa'].startswith('p/'))
        self.assertIn(perfil['conteudo']['mapa'][2:], ids)
        mural = next(i for i in itens.values() if i['tipo'] == 'mural')
        self.assertTrue(mural['conteudo']['mapa'].startswith('p/'), 'pendente: aponta para quem publicou')

    def test_mural_aprovado_aponta_para_o_item(self):
        base = _Exemplo.contexto()
        m = next(i for i in pacote(base)['itens'] if i['tipo'] == 'mural')
        ctx = _Exemplo.contexto(decisoes=[{'tipo': 'mural', 'item_id': m['item_id'], 'status': 'aprovado'}])
        novo = next(i for i in pacote(ctx)['itens'] if i['item_id'] == m['item_id'])
        self.assertEqual(novo['conteudo']['mapa'], 'm/' + m['item_id'])


class QuemSaiu(unittest.TestCase):
    def test_rf25_quem_saiu_some_dos_itens_e_dos_snapshots(self):
        ctx = _Exemplo.contexto()
        resp = ctx['tec']['Respostas do mural'][0]
        tec = dict(ctx['tec'], **{'Saídas': [{'Nome': resp['Nome'], 'Remover?': 'Sim'}]})
        pk = admin.montar_sincronizacao(ctx['pub'], ctx['interno'], tec, ctx['sug'], ctx['avisos'], ctx['historico'], AGORA)
        self.assertFalse(any(i['tipo'] == 'resposta' for i in pk['itens']))
        for s in pk['snapshots']:
            self.assertNotIn(resp['Contato (privado)'], s['html_pt'] + s['html_en'])
        # se o Farley marcou "Não" (abuso), nada sai
        tec['Saídas'][0]['Remover?'] = 'Não'
        self.assertIs(admin.sem_saidas(tec), tec)


class RecortePorComunidade(unittest.TestCase):
    """RF21/CA20: o snapshot de uma comunidade só tem contatos de linhas daquela comunidade."""

    @classmethod
    def setUpClass(cls):
        cls.ctx = _Exemplo.contexto()
        cls.snaps = {s['escopo']: s for s in pacote(cls.ctx)['snapshots']}
        cls.com = admin.Comunidades(cls.ctx['pub'], cls.ctx['interno'])
        cls.coms = admin.comunidades_das_linhas(cls.ctx['tec'], cls.com)

    def privados(self, aba, r):
        return [str(v) for k, v in r.items() if v and ('privado' in k.lower() or k.lower().startswith('observa')
                                                       or k == 'Contexto')]

    def test_nenhum_contato_de_fora_da_comunidade(self):
        tipo_da_aba = {a: t for t, a in admin.ABA_DO_TIPO.items()}
        verificados = 0
        for escopo, s in self.snaps.items():
            if escopo == 'rede':
                continue
            html = s['html_pt'] + s['html_en']
            for aba, linhas in self.ctx['tec'].items():
                for r in linhas:
                    t = tipo_da_aba.get(aba)
                    dentro = t and escopo in self.coms.get((t, admin.item_id(t, r)), [])
                    for v in self.privados(aba, r):
                        if not dentro:
                            self.assertNotIn(v, html, f'{escopo}: vazou {aba}/{v}')
                            verificados += 1
        self.assertGreater(verificados, 20)

    def test_contato_da_propria_comunidade_aparece(self):
        # "Posso ajudar" mostra os contatos de quem respondeu: aparece no painel da comunidade do item
        resp = self.ctx['tec']['Respostas do mural'][0]
        coms = self.coms[('resposta', admin.item_id('resposta', resp))]
        self.assertTrue(coms)
        for c in coms:
            self.assertIn(resp['Contato (privado)'], self.snaps[c]['html_pt'])

    def test_rede_toda_tem_tudo_e_os_avisos(self):
        html = self.snaps['rede']['html_pt']
        self.assertIn(self.ctx['tec']['Respostas do mural'][0]['Contato (privado)'], html)
        self.assertIn('Avisos da última atualização', html)
        self.assertNotIn('Avisos da última atualização', self.snaps['tecnologia']['html_pt'])

    def test_pessoas_e_metricas_da_comunidade(self):
        pub = self.ctx['pub']
        n = sum(1 for p in pub['pessoas'] if 'tecnologia' in p['comunidades'])
        r = self.snaps['tecnologia']['resumo']
        self.assertEqual(r['pessoas'], n)
        self.assertEqual(r['nome'], {'pt': 'Tecnologia', 'en': 'Technology'})
        self.assertIn(r['fase'], ('fragmentos', 'hub', 'multi-hub', 'nucleo'))
        self.assertEqual(self.snaps['rede']['resumo']['pessoas'], len(pub['pessoas']))

    def test_sugestoes_so_entre_pessoas_da_comunidade(self):
        pub_c, _, _, sug = admin.recortar(self.ctx['pub'], self.ctx['interno'], self.ctx['tec'], 'esg')
        ids = {p['id'] for p in pub_c['pessoas']}
        self.assertTrue(all(s['a'] in ids and s['b'] in ids for s in sug))

    def test_comunidade_sem_hub_explica(self):
        html = self.snaps['tecnologia']['html_pt']
        self.assertIn('não está nesta comunidade', html)
        self.assertIn('not in this community', self.snaps['tecnologia']['html_en'])

    def test_comunidade_vazia_nao_gera_snapshot(self):
        self.assertTrue(set(self.snaps) - {'rede'} <= {c['id'] for c in self.ctx['pub']['comunidades']})


class ModoPainel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = _Exemplo.contexto()
        cls.snaps = pacote(cls.ctx)['snapshots']

    def test_sem_onclick_nem_links_locais(self):
        for s in self.snaps:
            for html in (s['html_pt'], s['html_en']):
                self.assertNotIn('onclick=', html)
                self.assertNotIn('painel-tecelagem', html)
                self.assertIn('data-copiar', html)
                self.assertIn(f'<script>{painel.SCRIPT_PAINEL}</script>', html)
                self.assertEqual(html.count('<script'), 1)

    def test_textos_apontam_para_a_aba_moderacao(self):
        rede = next(s for s in self.snaps if s['escopo'] == 'rede')
        self.assertIn('aba Moderação', rede['html_pt'])
        self.assertIn('Moderation tab', rede['html_en'])
        self.assertIn('Rede toda', rede['html_pt'])

    def test_csp_do_painel_tem_o_hash_do_script(self):
        h = base64.b64encode(hashlib.sha256(painel.SCRIPT_PAINEL.encode()).digest()).decode()
        for arq in ('_headers', 'netlify.toml'):
            self.assertIn(f"'sha256-{h}'", ler(ADMIN, arq), f'atualize o hash em admin/{arq}')

    def test_modo_arquivo_continua_igual(self):
        html = painel.gerar(self.ctx['pub'], self.ctx['interno'], self.ctx['tec'], self.ctx['sug'],
                            self.ctx['avisos'], self.ctx['historico'], AGORA)
        self.assertIn('onclick="copiar(this)"', html)
        self.assertIn('painel-tecelagem-en.html', html)
        with self.assertRaises(ValueError):
            painel.gerar(self.ctx['pub'], self.ctx['interno'], self.ctx['tec'], [], [], [], AGORA, modo='x')


class _Resposta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Falso:
    """urlopen falso: guarda os pedidos e devolve respostas prontas por trecho da URL."""

    def __init__(self, respostas=None, erro=None):
        self.pedidos, self.respostas, self.erro = [], respostas or {}, erro

    def __call__(self, req, timeout=None):
        self.pedidos.append(req)
        if self.erro:
            raise self.erro
        for trecho, valor in self.respostas.items():
            if trecho in req.full_url:
                return _Resposta(json.dumps(valor).encode())
        return _Resposta(b'null')


class Supabase(unittest.TestCase):
    CFG = {'SUPABASE_URL': 'https://abc.supabase.co/', 'SUPABASE_SECRET_KEY': 'sb_secret_TESTE'}

    def test_configurado(self):
        self.assertFalse(admin.configurado({}))
        self.assertFalse(admin.configurado({'SUPABASE_URL': 'x'}))
        self.assertTrue(admin.configurado(self.CFG))
        self.assertTrue(admin.configurado({'SUPABASE_URL': 'x', 'SUPABASE_SERVICE_ROLE_KEY': 'eyJ'}))
        self.assertIsNone(admin.buscar_decisoes({}))

    def test_decisoes_pela_rpc_com_chave_nova_so_no_apikey(self):
        f = Falso({'rnq_pipeline_decisoes': [{'tipo': 'mural', 'item_id': 'a', 'status': 'aprovado'}]})
        d = admin.buscar_decisoes(self.CFG, abrir=f)
        self.assertEqual(d[0]['status'], 'aprovado')
        req = f.pedidos[0]
        self.assertEqual(req.full_url, 'https://abc.supabase.co/rest/v1/rpc/rnq_pipeline_decisoes')
        self.assertEqual(req.get_method(), 'POST')
        self.assertEqual(req.headers['Apikey'], 'sb_secret_TESTE')
        self.assertNotIn('Authorization', req.headers)

    def test_chave_antiga_jwt_vai_tambem_no_authorization(self):
        f = Falso({'rpc': []})
        Banco('https://x.supabase.co', 'eyJabc', abrir=f).rpc('rnq_pipeline_decisoes')
        self.assertEqual(f.pedidos[0].headers['Authorization'], 'Bearer eyJabc')

    def test_erros_viram_mensagem_clara(self):
        e401 = urllib.error.HTTPError('u', 401, 'x', {}, io.BytesIO(b'{"message":"invalid"}'))
        with self.assertRaisesRegex(ErroSupabase, 'recusou a chave'):
            admin.buscar_decisoes(self.CFG, abrir=Falso(erro=e401))
        with self.assertRaisesRegex(ErroSupabase, 'Sem conexão'):
            admin.buscar_decisoes(self.CFG, abrir=Falso(erro=urllib.error.URLError('offline')))
        e404 = urllib.error.HTTPError('u', 404, 'x', {}, io.BytesIO(b''))
        with self.assertRaisesRegex(ErroSupabase, 'configurar'):
            admin.buscar_decisoes(self.CFG, abrir=Falso(erro=e404))
        with self.assertRaisesRegex(ErroSupabase, 'inesperada'):
            admin.buscar_decisoes(self.CFG, abrir=Falso({'rpc': {'x': 1}}))

    def test_sincronizar_manda_o_pacote_inteiro(self):
        ctx = _Exemplo.contexto()
        f = Falso({'rnq_pipeline_sincronizar': {'snapshots': 7, 'itens_novos': 13}})
        r = admin.sincronizar(self.CFG, ctx, abrir=f)
        self.assertEqual(r['itens_novos'], 13)
        corpo = json.loads(f.pedidos[0].data.decode())
        self.assertEqual(set(corpo), {'p'})
        self.assertEqual(set(corpo['p']), {'gerado_em', 'comunidades', 'itens', 'snapshots'})
        self.assertEqual(corpo['p']['snapshots'][0]['escopo'], 'rede')

    def test_historico_por_comunidade_fica_no_mac(self):
        ctx = _Exemplo.contexto()
        pasta = tempfile.mkdtemp()
        try:
            admin.montar_sincronizacao(ctx['pub'], ctx['interno'], ctx['tec'], ctx['sug'], ctx['avisos'],
                                       ctx['historico'], AGORA, pasta_hist=pasta)
            arquivos = sorted(os.listdir(pasta))
            self.assertIn('rede.json', arquivos)
            self.assertIn('tecnologia.json', arquivos)
        finally:
            shutil.rmtree(pasta)

    def test_convite_de_quem_ja_existe_busca_o_id(self):
        e422 = urllib.error.HTTPError('u', 422, 'x', {}, io.BytesIO(b'{"msg":"User already registered"}'))

        class Misto(Falso):
            def __call__(s, req, timeout=None):
                s.pedidos.append(req)
                if '/auth/v1/invite' in req.full_url:
                    raise e422
                return _Resposta(json.dumps('uuid-1').encode())
        f = Misto()
        uid = Banco('https://x.supabase.co', 'sb_secret_x', abrir=f).convidar('a@b.c', 'https://painel')
        self.assertEqual(uid, 'uuid-1')
        self.assertIn('redirect_to=https%3A%2F%2Fpainel', f.pedidos[0].full_url)

    def test_publicar_funcao_em_multipart(self):
        f = Falso({'functions/deploy': {'slug': 'convidar'}})
        Gestao('sbp_x', 'abcdefghijklmnopqrst', abrir=f).publicar_funcao('convidar', {'index.ts': 'x', 'logica.js': 'y'})
        req = f.pedidos[0]
        self.assertIn('/projects/abcdefghijklmnopqrst/functions/deploy?slug=convidar', req.full_url)
        self.assertTrue(req.headers['Content-type'].startswith('multipart/form-data; boundary='))
        corpo = req.data.decode()
        self.assertIn('"entrypoint_path": "index.ts"', corpo)
        self.assertEqual(corpo.count('name="file"'), 2)
        self.assertEqual(req.headers['Authorization'], 'Bearer sbp_x')

    def test_escolher_chaves_prefere_as_novas(self):
        lista = [{'name': 'anon', 'type': 'legacy', 'api_key': 'eyJanon'},
                 {'name': 'service_role', 'type': 'legacy', 'api_key': 'eyJsr'},
                 {'name': 'default', 'type': 'publishable', 'api_key': 'sb_publishable_1'},
                 {'name': 'default', 'type': 'secret', 'api_key': 'sb_secret_1'}]
        self.assertEqual(escolher_chaves(lista), ('sb_publishable_1', 'sb_secret_1'))
        self.assertEqual(escolher_chaves(lista[:2]), ('eyJanon', 'eyJsr'))
        with self.assertRaises(ErroSupabase):
            escolher_chaves([])


class NadaSecretoNoApp(unittest.TestCase):
    """RF24: a chave secreta nunca vai para o app do navegador."""

    def test_admin_sem_chaves_secretas(self):
        chave = re.compile(r'sb_secret_[A-Za-z0-9_-]{16,}|service_role["\']?\s*[:=]\s*["\']eyJ')
        jwt_servico = re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]*cm9sZSI6InNlcnZpY2Vfcm9sZS')
        for raiz, _, arquivos in os.walk(ADMIN):
            for nome in arquivos:
                if nome.endswith(('.js', '.html', '.css', '.toml', '.json', '_headers', '.ts')):
                    texto = ler(raiz, nome)
                    self.assertIsNone(chave.search(texto), f'{nome} tem cara de chave secreta')
                    self.assertIsNone(jwt_servico.search(texto), f'{nome} tem um JWT de service_role')


if __name__ == '__main__':
    unittest.main()
