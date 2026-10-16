"""Chegada na hora (Edge Function "receber"): o item que a função monta a partir do envio do Netlify tem de ser
igual ao que o pipeline monta depois a partir da planilha — senão o painel mostraria uma coisa e depois outra.
Roda a lógica JS de verdade no Node (admin/supabase/functions/receber/logica.js)."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from apoio import RAIZ

import exportar
from exemplo.gerar_exemplo import envios_tecelagem, gerar as gerar_exemplo, rede
from rnq import admin, fontes, tecelagem

FUNCAO = os.path.join(RAIZ, 'admin', 'supabase', 'functions', 'receber')
NODE = shutil.which('node')


def rodar_js(envios, comunidades):
    script = (
        "import { itens } from %s;\n"
        "import fs from 'node:fs';\n"
        "const e = JSON.parse(fs.readFileSync(0, 'utf8'));\n"
        "const c = JSON.parse(fs.readFileSync(%s, 'utf8'));\n"
        "process.stdout.write(JSON.stringify(e.envios.flatMap(x => itens(x, c, e.comunidades))));\n"
    ) % (json.dumps('file://' + os.path.join(FUNCAO, 'logica.js')), json.dumps(os.path.join(FUNCAO, 'contrato.json')))
    r = subprocess.run([NODE, '--input-type=module', '-e', script], input=json.dumps(
        {'envios': envios, 'comunidades': comunidades}), capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


@unittest.skipUnless(NODE, 'precisa do Node para rodar a lógica da Edge Function')
class IgualAoPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sel, _, _ = rede()
        nomes = [p['nome'] for p in sel['pessoas']]
        cls.envios = envios_tecelagem(nomes[:-1])
        # um envio com o formato exato do Netlify (UTC com Z) e listas
        cls.envios.append({'form': 'mural', 'id': 'z-utc', 'criado': '2026-10-16T19:14:14.365Z',
                           'dados': {'tipo': 'oferta', 'titulo': 'Mentoria; com ponto e vírgula', 'descricao': 'Teste',
                                     'areas': ['Tecnologia', 'Clima & descarbonização'], 'nome': 'Fulana',
                                     'contato': 'fulana@exemplo.org'}})
        cls.envios.append({'form': 'participar', 'id': 'z-cad', 'criado': '2026-10-16T19:13:11Z',
                           'dados': {'nome': 'Nova Pessoa', 'contato': 'nova@exemplo.org', 'temas': ['ESG & sustentabilidade', 'IA & ética'],
                                     'comunidades': ['Cultura Regenerativa'], 'ofertas': ['Mentoria', 'Facilitação'],
                                     'oferta': 'Ofereço mentoria. Duas horas por mês', 'pedido': 'Preciso de um espaço; urgente',
                                     'mural': 'sim', 'visibilidade': 'mapa', 'maior_18': 'sim'}})
        cls.envios.append({'form': 'opt-out', 'id': 'z-out', 'criado': '2026-10-16T19:00:00Z', 'dados': {'nome': 'X'}})
        cls.envios.append({'form': 'mural', 'id': 'z-bot', 'criado': '2026-10-16T19:00:00Z',
                           'dados': {'tipo': 'pedido', 'titulo': 'spam', 'bot': 'eu sou robô'}})
        d = tempfile.mkdtemp()
        cls.pasta = d
        gerar_exemplo(d)
        arq = os.path.join(d, 'RNQ-tecelagem.xlsx')
        tecelagem.criar(arq)
        tecelagem.adicionar_envios(arq, cls.envios)
        ctx = {}
        exportar.executar(pasta=d, silencioso=True, site=os.path.join(d, 'site'), sem_painel=True, contexto=ctx)
        cls.py = {(i['tipo'], i['item_id']): i for i in admin.itens_moderacao(ctx['tec'], ctx['pub'], ctx['interno'])}
        coms = ctx['pub']['listas']['comunidades']
        cls.js = {(i['tipo'], i['item_id']): i for i in rodar_js(cls.envios, coms)}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.pasta)

    def test_mesmos_itens(self):
        self.assertEqual(set(self.js), set(self.py))
        self.assertIn(('mural', 'z-cad-oferta'), self.js)
        self.assertIn(('mural', 'z-cad-pedido'), self.js)
        self.assertNotIn(('mural', 'z-bot'), self.js, 'honeypot')

    def test_titulo_campos_privado_e_data_iguais(self):
        for k, py in self.py.items():
            js = self.js[k]
            with self.subTest(item=k):
                self.assertEqual(js['titulo'], py['titulo'])
                self.assertEqual(js['conteudo']['campos'], py['conteudo']['campos'])
                self.assertEqual(js['conteudo']['alertas'], py['conteudo']['alertas'])
                self.assertEqual(js['conteudo']['bloqueio'], py['conteudo']['bloqueio'])
                self.assertEqual(js['privado'], py['privado'])
                self.assertEqual(js['recebido_em'], py['recebido_em'])

    def test_comunidades_da_funcao_estao_contidas_nas_do_pipeline(self):
        # a função só vê as áreas citadas; o Mac acrescenta as comunidades das pessoas citadas
        algum = False
        for k, py in self.py.items():
            with self.subTest(item=k):
                self.assertTrue(set(self.js[k]['comunidades']) <= set(py['comunidades']))
                algum = algum or bool(self.js[k]['comunidades'])
        self.assertTrue(algum)
        self.assertEqual(self.js[('cadastro', 'z-cad')]['comunidades'], ['cultura-regenerativa', 'esg'])

    def test_horario_de_brasilia(self):
        self.assertEqual(self.js[('mural', 'z-utc')]['recebido_em'], '2026-10-16T16:14:00-03:00')

    def test_resposta_aponta_para_o_item(self):
        r = next(i for i in self.js.values() if i['tipo'] == 'resposta')
        self.assertEqual(r['ref'], 'ex-mural-1')


@unittest.skipUnless(NODE, 'precisa do Node')
class Contrato(unittest.TestCase):
    def test_contrato_gravado_esta_atualizado(self):
        with open(os.path.join(FUNCAO, 'contrato.json'), encoding='utf-8') as fh:
            gravado = json.load(fh)
        self.assertEqual(gravado, json.loads(json.dumps(admin.contrato())),
                         'rode painel_admin.py configurar (ou admin.gravar_contrato) depois de mudar as planilhas')

    def test_todos_os_tipos_de_moderacao_tem_formulario(self):
        tipos = {f['tipo'] for f in admin.contrato()['formularios'].values() if f['tipo']}
        self.assertEqual(tipos, set(admin.TIPOS))


if __name__ == '__main__':
    unittest.main()
