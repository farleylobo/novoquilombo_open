"""Versão em inglês (botão PT | EN): nomes traduzidos nos dados públicos, sem abrir a lista fechada de campos."""
import re
import unittest
from datetime import datetime
from pathlib import Path

from apoio import selecao_base, temas_base

from rnq import config as C
from rnq.publico import ErroPrivacidade, montar, validar

AGORA = datetime(2026, 10, 6, 12, 0)
SITE = Path(__file__).resolve().parent.parent / 'site'


def gerar(tem=None):
    return montar(selecao_base(), tem or temas_base(), {}, AGORA)


class NomesEmIngles(unittest.TestCase):
    def test_grupos_saem_com_nome_en(self):
        pub, avisos, _ = gerar()
        for k in ('comunidades', 'temas', 'atuacoes'):
            for g in pub[k]:
                self.assertTrue(g['nome_en'], f'{k}: {g["nome"]} sem nome_en')
        coms = {c['nome']: c['nome_en'] for c in pub['comunidades']}
        self.assertEqual(coms['Tecnologia'], 'Technology')
        self.assertFalse(any('Sem tradução' in a for a in avisos))

    def test_papeis_saem_com_nome_e_descricao_en(self):
        pub, _, _ = gerar()
        for p in pub['papeis']:
            self.assertTrue(p['nome_en'] and p['desc_en'])

    def test_tema_sem_traducao_avisa_e_cai_para_pt(self):
        tem = temas_base()
        tem['ordem_temas'].append('Tema Novo')
        tem['por_chave']['li:ana-lima'] = (['Tema Novo'], ['Corporativo'])
        pub, avisos, _ = gerar(tem)
        novo = [t for t in pub['temas'] if t['nome'] == 'Tema Novo'][0]
        self.assertIsNone(novo['nome_en'])
        self.assertTrue(any('Sem tradução em inglês: "Tema Novo"' in a for a in avisos))

    def test_lista_fechada_vale_para_grupos_e_papeis(self):
        pub, _, _ = gerar()
        pub['temas'][0]['observacao'] = 'interno'
        with self.assertRaises(ErroPrivacidade):
            validar(pub)
        pub, _, _ = gerar()
        pub['papeis'][0]['contato'] = 'x'
        with self.assertRaises(ErroPrivacidade):
            validar(pub)

    def test_toda_traducao_e_texto_nao_vazio(self):
        for pt, en in C.NOMES_EN.items():
            self.assertTrue(isinstance(en, str) and en.strip(), pt)


class TextosDoSite(unittest.TestCase):
    """i18n.js: toda chave em PT existe em EN (e vice-versa), para nenhum texto ficar pela metade."""

    def chaves(self, bloco):
        texto = (SITE / 'i18n.js').read_text(encoding='utf-8')
        ini = texto.index(f'    {bloco}: {{')
        fim = texto.index('\n    }', ini)
        corpo = texto[ini + len(bloco) + 7:fim]
        return {a or b for a, b in re.findall(r"(?:^\s*|,\s+)(?:'([^']+)'|([a-z_0-9]+)):\s", corpo, re.M)}

    def test_mesmas_chaves_em_pt_e_en(self):
        pt, en = self.chaves('pt'), self.chaves('en')
        self.assertGreater(len(pt), 100)
        self.assertEqual(sorted(pt - en), [])
        self.assertEqual(sorted(en - pt), [])

    def test_chaves_usadas_existem(self):
        pt = self.chaves('pt')
        usadas = set()
        for arq in ('app.js', 'index.html', 'participar.js', 'participar.html'):
            s = (SITE / arq).read_text(encoding='utf-8')
            usadas |= set(re.findall(r"\bt\('([^']+)'\s*[,)]", s))
            usadas |= set(re.findall(r'data-i18n(?:-ph|-aria)?="([^"]+)"', s))
            usadas |= {c for c in re.findall(r"dica\('([^']+)'\)", s)}
        usadas = {u for u in usadas if not u.endswith('_') and u not in ('tipo:',)}
        self.assertEqual(sorted(usadas - pt), [])


if __name__ == '__main__':
    unittest.main()
