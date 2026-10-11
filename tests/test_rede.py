import unittest

import apoio  # noqa: F401  (ajusta o caminho)

from rnq import rede


def p(i, temas=(), coms=(), atu=()):
    return {'id': i, 'nome': i.title(), 'temas': list(temas), 'comunidades': list(coms), 'atuacao': list(atu)}


class Metricas(unittest.TestCase):
    def test_componentes_e_caminho(self):
        adj = rede.grafo(['a', 'b', 'c', 'd'], [('a', 'b'), ('b', 'c')])
        self.assertEqual([len(c) for c in rede.componentes(adj)], [3, 1])
        med, diam = rede.caminho_medio(adj)
        self.assertAlmostEqual(med, 4 / 3)
        self.assertEqual(diam, 2)

    def test_intermediacao_do_centro_de_um_caminho(self):
        adj = rede.grafo(['a', 'b', 'c'], [('a', 'b'), ('b', 'c')])
        bc = rede.intermediacao(adj)
        self.assertAlmostEqual(bc['b'], 1.0)
        self.assertEqual(bc['a'], 0.0)

    def test_estrela_e_hub_and_spoke(self):
        ps = [p(x) for x in 'habcde']
        m = rede.metricas(ps, [('h', x) for x in 'abcde'], hub_id='h')
        self.assertEqual(m['fase'], 'hub')
        self.assertEqual(m['dependencia_hub'], 1.0)
        self.assertEqual(m['isolados_sem_hub'], 5)
        self.assertEqual(m['intermediacao'][0][0], 'h')

    def test_fragmentos(self):
        ps = [p(x) for x in 'abcdefghij']
        m = rede.metricas(ps, [('a', 'b')], hub_id=None)
        self.assertEqual(m['fase'], 'fragmentos')
        self.assertEqual(len(m['isolados']), 8)

    def test_fases_por_limiar(self):
        self.assertEqual(rede.fase(0.3, 0.0, 2), 'fragmentos')
        self.assertEqual(rede.fase(0.6, 0.5, 2), 'hub')
        self.assertEqual(rede.fase(0.6, 0.1, 2), 'multi-hub')
        self.assertEqual(rede.fase(0.9, 0.1, 2.5), 'nucleo')

    def test_ligacoes_entre_comunidades(self):
        ps = [p('a', coms=['x']), p('b', coms=['y']), p('c', coms=['x'])]
        m = rede.metricas(ps, [('a', 'b'), ('a', 'c')])
        self.assertEqual(m['ligacoes_entre_comunidades'], 1)


class Apresentacoes(unittest.TestCase):
    def setUp(self):
        self.ps = [
            p('hub', temas=['clima'], coms=['x']),
            p('ana', temas=['clima', 'redes'], coms=['x'], atu=['corp']),
            p('bia', temas=['clima', 'redes'], coms=['y'], atu=['ong']),
            p('caio', temas=['clima'], coms=['x'], atu=['corp']),
            p('duda', temas=['arte'], coms=['z']),
        ]

    def test_nunca_sugere_hub_nem_ligados_nem_ja_feitos(self):
        s = rede.sugerir_apresentacoes(self.ps, [('ana', 'caio')], ja_feitas=[('bia', 'caio')], hub_id='hub')
        pares = {frozenset((x['a'], x['b'])) for x in s}
        self.assertFalse(any('hub' in par for par in pares))
        self.assertNotIn(frozenset(('ana', 'caio')), pares)
        self.assertNotIn(frozenset(('bia', 'caio')), pares)

    def test_semelhanca_mais_diferenca_ganha(self):
        s = rede.sugerir_apresentacoes(self.ps, [], hub_id='hub')
        self.assertEqual({s[0]['a'], s[0]['b']}, {'ana', 'bia'})
        motivos = ' '.join(s[0]['motivos'])
        self.assertIn('comunidades diferentes', motivos)
        self.assertIn('lugares diferentes', motivos)

    def test_sem_nada_em_comum_nao_sugere(self):
        s = rede.sugerir_apresentacoes(self.ps, [], hub_id='hub')
        self.assertFalse(any('duda' in (x['a'], x['b']) for x in s))

    def test_pedido_explicito_vence(self):
        s = rede.sugerir_apresentacoes(self.ps, [], desejos=[('caio', 'duda')], hub_id='hub')
        self.assertEqual({s[0]['a'], s[0]['b']}, {'caio', 'duda'})

    def test_limite_por_pessoa(self):
        ps = [p(f'p{i}', temas=['t']) for i in range(8)]
        s = rede.sugerir_apresentacoes(ps, [], n=50, max_por_pessoa=2)
        uso = {}
        for x in s:
            for k in (x['a'], x['b']):
                uso[k] = uso.get(k, 0) + 1
        self.assertLessEqual(max(uso.values()), 2)

    def test_conhecer(self):
        c = rede.conhecer(self.ps, [('ana', 'caio')], hub_id='hub')
        ids = [x['id'] for x in c['ana']]
        self.assertEqual(ids[0], 'bia')
        self.assertNotIn('caio', ids)
        self.assertNotIn('hub', ids)
        self.assertEqual(c['duda'], [])

    def test_conhecer_completa_pela_comunidade(self):
        ps = [dict(p('ana', coms=['tec']), organizacao='X'), dict(p('bia', coms=['tec']), organizacao='Y'),
              dict(p('caio', coms=['tec']), organizacao='X')]
        c = rede.conhecer(ps, [])
        self.assertEqual([x['id'] for x in c['ana']], ['bia'])          # caio é da mesma organização
        self.assertEqual(c['ana'][0]['comunidades'], ['tec'])


if __name__ == '__main__':
    unittest.main()
