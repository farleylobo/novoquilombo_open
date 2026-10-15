"""Painel do tecelão em português e inglês."""
import os
import re
import shutil
import tempfile
import unittest
from datetime import datetime

import apoio

import exportar
from rnq import painel
from rnq.rede import FASES, FASES_EN, sugerir_apresentacoes


class PainelIdiomas(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        apoio.escrever_selecao(os.path.join(self.d, 'RNQ-selecao.xlsx'))
        apoio.escrever_temas(os.path.join(self.d, 'RNQ-temas-atuacao.xlsx'))
        exportar.executar(pasta=self.d, agora=datetime(2026, 10, 6, 9), silencioso=True)
        self.pt = apoio.ler(os.path.join(self.d, 'painel/painel-tecelagem.html'))
        self.en = apoio.ler(os.path.join(self.d, 'painel/painel-tecelagem-en.html'))

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_mesmas_chaves_nos_dois_idiomas(self):
        self.assertEqual(set(painel.TEXTOS['pt']), set(painel.TEXTOS['en']))
        self.assertEqual(set(painel.TEXTOS['pt']['razao']), set(painel.TEXTOS['en']['razao']))
        self.assertEqual(len(painel.TEXTOS['pt']['pend']), len(painel.TEXTOS['en']['pend']))
        self.assertEqual(set(FASES), set(FASES_EN))

    def test_gera_os_dois_paineis_ligados_entre_si(self):
        self.assertIn('<html lang="pt-BR">', self.pt)
        self.assertIn('<html lang="en">', self.en)
        self.assertIn('href="painel-tecelagem-en.html"', self.pt)
        self.assertIn('href="painel-tecelagem.html"', self.en)

    def test_portugues_continua_igual(self):
        for frase in ('Painel do tecelão', 'Saúde da rede', 'Apresentações sugeridas', 'Documento interno',
                      'Esperando você', 'Copiar mensagem'):
            self.assertIn(frase, self.pt)

    def test_ingles_sem_titulos_em_portugues(self):
        for frase in ("Weaver&#x27;s panel", 'Network health', 'Suggested introductions', 'Internal document',
                      'Waiting for you', 'Copy message', 'Bridges'):
            self.assertIn(frase, self.en.replace("Weaver's", 'Weaver&#x27;s'))
        for frase in ('Saúde da rede', 'Apresentações sugeridas', 'Esperando você', 'Pontes', 'Mais conectadas',
                      'Copiar mensagem', 'Quero apresentar', 'Fase 1 ·', 'Fase 2 ·'):
            self.assertNotIn(frase, self.en, frase)

    def test_ingles_continua_privado_e_offline(self):
        self.assertIn('Do not publish or share this file', self.en)
        self.assertIn('noindex,nofollow', self.en)
        self.assertIsNone(re.search(r'<script[^>]+src=', self.en))

    def test_motivos_traduzidos_com_nome_en(self):
        pessoas = [{'id': 'a', 'nome': 'Ana Um', 'temas': ['clima'], 'comunidades': ['c1'], 'atuacao': ['x']},
                   {'id': 'b', 'nome': 'Bia Dois', 'temas': ['clima'], 'comunidades': ['c2'], 'atuacao': ['y']}]
        s = sugerir_apresentacoes(pessoas, [], nomes_temas={'clima': 'Clima'})[0]
        self.assertIn('trabalham com Clima', s['motivos'])
        nomes = {'tema': {'clima': 'Climate'}.get, 'com': str, 'atu': {'x': 'Corporate', 'y': 'Public sector'}.get}
        en = painel._motivos(s, 'en', nomes)
        self.assertIn('both work on Climate', en)
        self.assertIn('act from different places (Corporate × Public sector)', en)
        self.assertIn('brings in someone who has no links yet', en)
        self.assertEqual(painel._motivos(s, 'pt', nomes), s['motivos'])

    def test_idioma_desconhecido(self):
        with self.assertRaises(ValueError):
            painel.mensagem_semana({'mural': [], 'iniciativas': [], 'estatisticas': {}}, datetime.now(), idioma='fr')
