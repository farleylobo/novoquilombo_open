"""Preparação para publicar: "Sobre os dados" (contato de privacidade) e rede fictícia de exemplo."""
import json
import os
import tempfile
import unittest
from datetime import datetime
from unittest import mock

from apoio import selecao_base, temas_base

import exportar
from exemplo.gerar_exemplo import gerar
from rnq import config as C
from rnq.publico import ErroPrivacidade, montar, validar

AGORA = datetime(2026, 10, 11, 12, 0)


class SobreOsDados(unittest.TestCase):
    def test_sem_contato_avisa(self):
        with mock.patch.object(C, 'CONTATO_PRIVACIDADE', ''):
            pub, avisos, _ = montar(selecao_base(), temas_base(), {}, AGORA)
        self.assertIsNone(pub['sobre']['contato'])
        self.assertTrue(any('Sem e-mail de privacidade' in a for a in avisos))

    def test_com_contato_publica(self):
        with mock.patch.object(C, 'CONTATO_PRIVACIDADE', 'privacidade@exemplo.org'):
            pub, avisos, _ = montar(selecao_base(), temas_base(), {}, AGORA)
        self.assertEqual(pub['sobre']['contato'], 'privacidade@exemplo.org')
        self.assertFalse(any('privacidade' in a for a in avisos))

    def test_lista_fechada_no_sobre(self):
        pub, _, _ = montar(selecao_base(), temas_base(), {}, AGORA)
        pub['sobre']['telefone'] = '11 99999-0000'
        with self.assertRaises(ErroPrivacidade):
            validar(pub)


class RedeDeExemplo(unittest.TestCase):
    def test_exportar_exemplo_gera_site_completo(self):
        with tempfile.TemporaryDirectory() as d:
            gerar(d)
            site = os.path.join(d, 'site-out')
            pub, avisos, _, sug = exportar.executar(pasta=d, agora=AGORA, silencioso=True, site=site)
            self.assertGreaterEqual(len(pub['pessoas']), 30)
            self.assertGreater(len(pub['ligacoes']), 5)
            self.assertTrue(any(p['conhecer'] for p in pub['pessoas']))
            with open(os.path.join(site, 'rnq-publico.json'), encoding='utf-8') as fh:
                self.assertEqual(len(json.load(fh)['pessoas']), len(pub['pessoas']))

    def test_exemplo_e_deterministico(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            pa = exportar.executar(pasta=gerar(a), agora=AGORA, silencioso=True, sem_painel=True)[0]
            pb = exportar.executar(pasta=gerar(b), agora=AGORA, silencioso=True, sem_painel=True)[0]
            self.assertEqual([p['nome'] for p in pa['pessoas']], [p['nome'] for p in pb['pessoas']])


class Publicar(unittest.TestCase):
    def test_recusa_sem_contato_e_com_exemplo(self):
        import publicar
        with tempfile.TemporaryDirectory() as d, mock.patch.object(C, 'CONTATO_PRIVACIDADE', ''), \
                mock.patch.object(publicar, 'MARCA_EXEMPLO', os.path.join(d, '.exemplo')):
            open(os.path.join(d, '.exemplo'), 'w').close()
            erros = publicar.checar(rodar_testes=False)
        self.assertTrue(any('e-mail de privacidade' in e for e in erros))
        self.assertTrue(any('FICTÍCIA' in e for e in erros))
        with mock.patch.object(C, 'CONTATO_PRIVACIDADE', ''):
            self.assertFalse(any('privacidade' in e for e in publicar.checar(rodar_testes=False, sem_contato=True)))

    def test_pasta_so_com_arquivos_da_lista(self):
        import publicar
        with tempfile.TemporaryDirectory() as d:
            site = os.path.join(d, 'site')
            for rel in publicar.PUBLICAR + ['rnq-publico.json', '_versoes-antigas/index.v1.html', 'x.xlsx']:
                os.makedirs(os.path.dirname(os.path.join(site, rel)), exist_ok=True)
                open(os.path.join(site, rel), 'w').close()
            with mock.patch.object(publicar, 'SITE', site):
                destino = publicar.montar_pasta(os.path.join(d, 'out'))
            achados = sorted(os.path.relpath(os.path.join(r, f), destino) for r, _, fs in os.walk(destino) for f in fs)
            self.assertEqual(achados, sorted(publicar.PUBLICAR))

    def test_exemplo_marca_o_site(self):
        with tempfile.TemporaryDirectory() as d:
            site = os.path.join(d, 'site-out')
            exportar.executar(pasta=gerar(d), agora=AGORA, silencioso=True, sem_painel=True, site=site, exemplo=True)
            self.assertTrue(os.path.exists(os.path.join(site, '.exemplo')))
            exportar.executar(pasta=d, agora=AGORA, silencioso=True, sem_painel=True, site=site)
            self.assertFalse(os.path.exists(os.path.join(site, '.exemplo')))


class Convites(unittest.TestCase):
    def test_link_direto_e_mensagem_por_pessoa(self):
        import convites
        pub, _, _ = montar(selecao_base(), temas_base(), {}, AGORA)
        ls = convites.linhas(pub, 'https://exemplo.netlify.app/')
        self.assertEqual(len(ls), len(pub['pessoas']))
        ana = [x for x in ls if x['Nome'] == 'Ana Lima'][0]
        self.assertEqual(ana['Link (PT)'], 'https://exemplo.netlify.app/#p/ana-lima')
        self.assertIn('?lang=en#p/ana-lima', ana['Link (EN)'])
        self.assertTrue(ana['Mensagem (PT)'].startswith('Oi, Ana!'))
        self.assertIn(ana['Link (PT)'], ana['Mensagem (PT)'])


if __name__ == '__main__':
    unittest.main()
