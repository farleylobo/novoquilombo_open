"""Testes das correções e melhorias da revisão de 06/10/2026."""
import glob
import json
import os
import tempfile
import unittest
from datetime import datetime

from apoio import gravar, selecao_base, temas_base

from rnq import painel, tecelagem
from rnq.publico import montar

AGORA = datetime(2026, 10, 6, 12, 0)


def gerar(tec=None, sel=None):
    return montar(sel or selecao_base(), temas_base(), tec or {}, AGORA)


class Privacidade(unittest.TestCase):
    def test_linkedin_so_http(self):
        sel = selecao_base()
        sel['pessoas'][0]['linkedin'] = 'javascript:alert(1)'
        sel['pessoas'][1]['linkedin'] = 'https://www.linkedin.com/in/bruno'
        pub, avisos, _ = gerar(sel=sel)
        p = {x['nome']: x for x in pub['pessoas']}
        self.assertIsNone(p['Ana Lima']['linkedin'])
        self.assertEqual(p['Bruno Reis']['linkedin'], 'https://www.linkedin.com/in/bruno')
        self.assertTrue(any('LinkedIn inválido' in a for a in avisos))

    def test_contato_em_precisa_de_e_removido(self):
        tec = {'Iniciativas': [{'ID': 'i1', 'Título': 'Roda', 'Precisa de': 'Sala; falar com 11 98765-4321',
                                'Nome de quem propôs': 'Ana Lima', 'Publicar?': 'Sim'}]}
        pub, avisos, _ = gerar(tec)
        self.assertNotIn('98765', json.dumps(pub))
        self.assertTrue(any('Iniciativa "Roda"' in a for a in avisos))


class Saidas(unittest.TestCase):
    def test_saida_com_nome_errado_vira_aviso(self):
        _, avisos, _ = gerar({'Saídas': [{'Nome': 'Ana Lim', 'Remover?': 'Sim'}]})
        self.assertTrue(any('não corresponde a ninguém' in a for a in avisos))


class PlanilhaSegura(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.arq = os.path.join(self.d, 'RNQ-tecelagem.xlsx')
        tecelagem.criar(self.arq)

    def envio(self, i):
        return {'form': 'opt-in', 'id': f'e{i}', 'criado': '2026-10-06', 'dados': {'nome': f'P{i}'}}

    def test_recusa_se_aberta_no_excel(self):
        gravar(os.path.join(self.d, '~$RNQ-tecelagem.xlsx'), 'lock')
        with self.assertRaises(tecelagem.PlanilhaAberta):
            tecelagem.adicionar_envios(self.arq, [self.envio(1)])

    def test_backup_antes_de_gravar_e_rotacao(self):
        for i in range(12):
            tecelagem.adicionar_envios(self.arq, [self.envio(i)])
        backups = glob.glob(os.path.join(self.d, '_trabalho', 'backups', 'RNQ-tecelagem-*.xlsx'))
        self.assertEqual(len(backups), 10)

    def test_sem_envio_novo_nao_grava(self):
        tecelagem.adicionar_envios(self.arq, [self.envio(1)])
        antes = os.path.getmtime(self.arq)
        tecelagem.adicionar_envios(self.arq, [self.envio(1)])
        self.assertEqual(os.path.getmtime(self.arq), antes)


class Painel(unittest.TestCase):
    def test_mensagem_da_semana(self):
        tec = {'Mural': [
            {'ID': 'm1', 'Recebido em': '2026-10-04', 'Tipo': 'Pedido', 'Título': 'Preciso de sala', 'Nome': 'Ana Lima',
             'Publicar?': 'Sim'},
            {'ID': 'm2', 'Recebido em': '2026-08-01', 'Tipo': 'Oferta', 'Título': 'Oferta antiga', 'Nome': 'Bruno Reis',
             'Publicar?': 'Sim'}]}
        pub, _, _ = gerar(tec)
        msg = painel.mensagem_semana(pub, AGORA, 'https://rnq.netlify.app/')
        self.assertIn('Preciso de sala', msg)
        self.assertNotIn('Oferta antiga', msg)              # só os últimos 7 dias
        self.assertIn('https://rnq.netlify.app#mural', msg)
        self.assertIn('Somos 5 pessoas', msg)
        self.assertIn('<link do mapa>', painel.mensagem_semana(pub, AGORA))

    def test_respostas_e_itens_antigos(self):
        tec = {'Mural': [{'ID': 'm2', 'Recebido em': '2026-08-01', 'Tipo': 'Pedido', 'Título': 'Pedido antigo',
                          'Nome': 'Ana Lima', 'Contato (privado)': 'ana@x.org', 'Publicar?': 'Sim'}],
               'Respostas do mural': [{'ID': 'r1', 'ID do item': 'm2', 'Item': 'Pedido antigo', 'Nome': 'Carla Dias',
                                       'Contato (privado)': 'carla@x.org', 'Mensagem': 'Tenho uma sala'}]}
        pub, avisos, interno = gerar(tec)
        html = painel.gerar(pub, interno, tec, [], avisos, [], AGORA)
        self.assertIn('Carla Dias → Ana Lima', html)
        self.assertIn('carla@x.org', html)
        self.assertIn('ana@x.org', html)
        self.assertIn('Abertos há mais de 45 dias', html)
        self.assertIn('Mensagem da semana', html)


if __name__ == '__main__':
    unittest.main()
