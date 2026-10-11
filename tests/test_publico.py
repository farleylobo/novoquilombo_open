import json
import unittest
from datetime import datetime

from apoio import selecao_base, temas_base

from rnq import publico
from rnq.publico import ErroPrivacidade, montar, validar

AGORA = datetime(2026, 10, 6, 12, 0)


def gerar(tec=None, sel=None, tem=None):
    return montar(sel or selecao_base(), tem or temas_base(), tec or {}, AGORA)


def por_nome(pub):
    return {p['nome']: p for p in pub['pessoas']}


class Modelo(unittest.TestCase):
    def test_comunidade_generica_vira_tema_e_tema_vira_comunidade(self):
        pub, _, _ = gerar()
        p = por_nome(pub)
        # Diversidade (comunidade antiga) -> tema renomeado
        self.assertIn('diversidade-equidade-inclusao', p['Ana Lima']['temas'])
        self.assertNotIn('diversidade-equidade-e-inclusao', p['Ana Lima']['comunidades'])
        # "Produto, dados..." -> renomeado para Tecnologia, produto & dados -> absorvido pela comunidade Tecnologia
        self.assertIn('tecnologia', p['Bruno Reis']['comunidades'])
        self.assertNotIn('tecnologia-produto-dados', p['Bruno Reis']['temas'])
        # tema renomeado
        self.assertIn('diversidade-equidade-inclusao', p['Davi Nunes']['temas'])

    def test_comunidade_excluida_some(self):
        pub, avisos, _ = gerar()
        self.assertEqual(por_nome(pub)['Davi Nunes']['comunidades'], [])
        self.assertNotIn('ycl', [c['id'] for c in pub['comunidades']])
        self.assertTrue(any('Davi Nunes: sem comunidade' in a for a in avisos))

    def test_listas_so_com_o_que_e_usado(self):
        pub, _, _ = gerar()
        usados = {t for p in pub['pessoas'] for t in p['temas']}
        self.assertEqual({t['id'] for t in pub['temas']}, usados)

    def test_lista_fechada_de_campos(self):
        pub, _, _ = gerar()
        self.assertTrue(validar(pub))
        pub['pessoas'][0]['email'] = 'x@y.com'
        with self.assertRaises(ErroPrivacidade):
            validar(pub)


class Saidas(unittest.TestCase):
    def test_saida_remove_pessoa_ligacoes_e_itens(self):
        tec = {'Saídas': [{'Nome': 'ana lima', 'Remover?': 'Sim'}],
               'Mural': [{'ID': 'm1', 'Tipo': 'Oferta', 'Título': 'Mentoria', 'Nome': 'Ana Lima', 'Publicar?': 'Sim'}]}
        pub, avisos, _ = gerar(tec)
        self.assertNotIn('Ana Lima', por_nome(pub))
        self.assertFalse(any('ana-lima' in (l['a'], l['b']) for l in pub['ligacoes']))
        self.assertEqual(pub['mural'], [])
        self.assertTrue(any('removida' in a for a in avisos))

    def test_saida_vazia_conta_como_sim_rf8(self):
        pub, _, _ = gerar({'Saídas': [{'Nome': 'Bruno Reis', 'Remover?': None}]})
        self.assertNotIn('Bruno Reis', por_nome(pub))

    def test_saida_marcada_nao_mantem(self):
        pub, _, _ = gerar({'Saídas': [{'Nome': 'Bruno Reis', 'Remover?': 'Não'}]})
        self.assertIn('Bruno Reis', por_nome(pub))


class Correcoes(unittest.TestCase):
    def test_correcao_de_nome_e_cargo(self):
        tec = {'Correções': [
            {'Pessoa (nome na seleção)': 'Carla Dias', 'Campo': 'Nome', 'Novo valor': 'Carla Dias Souza', 'Aplicar?': 'Sim'},
            {'Pessoa (nome na seleção)': 'Carla Dias', 'Campo': 'Cargo', 'Novo valor': 'Gerente', 'Aplicar?': 'Sim'},
            {'Pessoa (nome na seleção)': 'Bruno Reis', 'Campo': 'Cargo', 'Novo valor': 'Não aplicar', 'Aplicar?': 'Não'}]}
        pub, _, _ = gerar(tec)
        p = por_nome(pub)
        self.assertEqual(p['Carla Dias Souza']['cargo'], 'Gerente')
        self.assertEqual(p['Carla Dias Souza']['temas'], ['clima-descarbonizacao'])   # temas seguem pelo ID externo
        self.assertEqual(p['Bruno Reis']['cargo'], 'Cargo')


class Ligacoes(unittest.TestCase):
    def test_so_aprovadas_viram_ligacao(self):
        tec = {'Ligações sugeridas': [
            {'Pessoa': 'Carla Dias', 'Quem sugere': 'Bruno Reis', 'Aprovar?': 'Sim'},
            {'Pessoa': 'Carla Dias', 'Quem sugere': 'Ana Lima', 'Aprovar?': None}]}
        pub, _, _ = gerar(tec)
        pares = {frozenset((l['a'], l['b'])) for l in pub['ligacoes']}
        self.assertIn(frozenset(('carla-dias', 'bruno-reis')), pares)
        self.assertNotIn(frozenset(('carla-dias', 'ana-lima')), pares)

    def test_apresentacao_feita_vira_ligacao(self):
        tec = {'Apresentações': [
            {'Pessoa A': 'Ana Lima', 'Pessoa B': 'Carla Dias', 'Status': 'Apresentadas'},
            {'Pessoa A': 'Davi Nunes', 'Pessoa B': 'Carla Dias', 'Status': 'Sugerida'}]}
        pub, _, interno = gerar(tec)
        pares = {frozenset((l['a'], l['b'])): l['origem'] for l in pub['ligacoes']}
        self.assertEqual(pares[frozenset(('ana-lima', 'carla-dias'))], 'apresentacao')
        self.assertNotIn(frozenset(('davi-nunes', 'carla-dias')), pares)
        self.assertEqual(len(interno['ja_apresentadas']), 2)

    def test_nome_desconhecido_vira_aviso(self):
        _, avisos, _ = gerar({'Ligações sugeridas': [{'Pessoa': 'Zé Ninguém', 'Quem sugere': 'Ana Lima', 'Aprovar?': 'Sim'}]})
        self.assertTrue(any('Zé Ninguém' in a for a in avisos))


class Perfis(unittest.TestCase):
    def test_perfil_publicado_e_colaboracao(self):
        tec = {'Perfis': [{'Pessoa no mapa': 'Davi Nunes', 'Posso compartilhar': 'Rodas de conversa',
                           'Quero aprender': 'Captação', 'Colaboro com': 'Carla Dias',
                           'Gostaria de colaborar com': 'Bruno Reis', 'Contato (privado)': 'davi@exemplo.org',
                           'Publicar?': 'Sim'}]}
        pub, _, interno = gerar(tec)
        d = por_nome(pub)['Davi Nunes']
        self.assertEqual(d['compartilha'], 'Rodas de conversa')
        self.assertEqual(d['aprende'], 'Captação')
        self.assertIn(frozenset(('davi-nunes', 'carla-dias')), {frozenset((l['a'], l['b'])) for l in pub['ligacoes']})
        self.assertIn(('davi-nunes', 'bruno-reis'), interno['desejos'])
        self.assertNotIn('davi@exemplo.org', json.dumps(pub))
        self.assertNotIn('Bruno Reis', d['compartilha'] or '')

    def test_perfil_nao_publicado_nao_aparece_mas_alimenta_desejos(self):
        tec = {'Perfis': [{'Pessoa no mapa': 'Davi Nunes', 'Posso compartilhar': 'X', 'Gostaria de colaborar com': 'Ana Lima'}]}
        pub, _, interno = gerar(tec)
        self.assertIsNone(por_nome(pub)['Davi Nunes']['compartilha'])
        self.assertIn(('davi-nunes', 'ana-lima'), interno['desejos'])

    def test_contato_colado_no_texto_e_removido(self):
        tec = {'Perfis': [{'Pessoa no mapa': 'Davi Nunes', 'Posso compartilhar': 'Mentoria, fale comigo: davi@x.org ou 11 98888-7777',
                           'Publicar?': 'Sim'}]}
        pub, avisos, _ = gerar(tec)
        texto = por_nome(pub)['Davi Nunes']['compartilha']
        self.assertNotIn('davi@x.org', texto)
        self.assertNotIn('98888', texto)
        self.assertTrue(any('removido' in a for a in avisos))


class Mural(unittest.TestCase):
    def base(self, **extra):
        item = {'ID': 'm1', 'Recebido em': '2026-10-01 10:00', 'Tipo': 'Pedido', 'Título': 'Preciso de facilitação',
                'Descrição': 'Encontro em novembro', 'Áreas': 'Clima & descarbonização; Tema Inventado; ESG',
                'Nome': 'Ana', 'Contato (privado)': 'ana-privado@exemplo.org', 'Está no mapa como': 'Ana Lima',
                'Publicar?': 'Sim', 'Status': 'Aberto'}
        item.update(extra)
        return {'Mural': [item]}

    def test_publica_so_aprovado_sem_contato(self):
        pub, avisos, _ = gerar(self.base())
        m = pub['mural'][0]
        self.assertEqual(m['tipo'], 'pedido')
        self.assertEqual(m['autor_id'], 'ana-lima')
        self.assertEqual(m['autor'], 'Ana Lima')
        self.assertEqual(m['areas'], ['Clima & descarbonização', 'ESG'])
        self.assertEqual(m['data'], '2026-10-01')
        self.assertTrue(any('Tema Inventado' in a for a in avisos))
        self.assertNotIn('ana-privado', json.dumps(pub))

    def test_nao_publicado_nao_aparece(self):
        pub, _, _ = gerar(self.base(**{'Publicar?': None}))
        self.assertEqual(pub['mural'], [])

    def test_sem_tipo_vira_aviso(self):
        pub, avisos, _ = gerar(self.base(Tipo='Talvez'))
        self.assertEqual(pub['mural'], [])
        self.assertTrue(any('sem tipo' in a for a in avisos))

    def test_area_com_nome_antigo_e_aceita(self):
        pub, _, _ = gerar(self.base(**{'Áreas': 'Diversidade & equidade racial'}))
        self.assertEqual(pub['mural'][0]['areas'], ['Diversidade, equidade & inclusão'])

    def test_contato_privado_no_texto_publico_bloqueia(self):
        tec = self.base(**{'Descrição': 'me chame em ana-privado@exemplo.org'})
        # o e-mail é removido do texto público, então o export passa sem vazar
        pub, _, _ = gerar(tec)
        self.assertNotIn('ana-privado@exemplo.org', json.dumps(pub))

    def test_atendidos_vao_para_o_fim(self):
        tec = self.base()
        tec['Mural'].append({'ID': 'm2', 'Recebido em': '2026-10-05', 'Tipo': 'Oferta', 'Título': 'Sala',
                             'Nome': 'Bruno', 'Publicar?': 'Sim', 'Status': 'Atendido'})
        tec['Mural'].append({'ID': 'm3', 'Recebido em': '2026-09-01', 'Tipo': 'Oferta', 'Título': 'Antigo',
                             'Nome': 'Bruno', 'Publicar?': 'Sim', 'Status': 'Aberto'})
        pub, _, _ = gerar(tec)
        self.assertEqual([m['id'] for m in pub['mural']], ['m1', 'm3', 'm2'])
        self.assertEqual(pub['estatisticas']['mural_abertos'], 2)


class Iniciativas(unittest.TestCase):
    def test_participantes_so_do_mapa(self):
        tec = {'Iniciativas': [{'ID': 'i1', 'Tipo': 'Encontro', 'Título': 'Roda de clima',
                                'Participantes': 'Ana Lima, Carla Dias, Pessoa Externa', 'Precisa de': 'Local',
                                'Nome de quem propôs': 'Carla Dias', 'Contato (privado)': 'carla@exemplo.org',
                                'Publicar?': 'Sim', 'Áreas': 'Clima & descarbonização'}]}
        pub, avisos, _ = gerar(tec)
        i = pub['iniciativas'][0]
        self.assertEqual(i['participantes'], ['ana-lima', 'carla-dias'])
        self.assertEqual(i['proponente_id'], 'carla-dias')
        self.assertEqual(i['tipo'], 'Encontro')
        self.assertTrue(any('Pessoa Externa' in a for a in avisos))
        self.assertNotIn('carla@exemplo.org', json.dumps(pub))


class Papeis(unittest.TestCase):
    def test_papeis(self):
        pub, _, _ = gerar({'Papéis': [{'Pessoa': 'Carla Dias', 'Papel 1': 'Facilitador(a)', 'Papel 2': 'Inexistente'}]})
        self.assertEqual(por_nome(pub)['Carla Dias']['papeis'], ['facilitador'])


class Sugestoes(unittest.TestCase):
    def test_conhecer_nao_sugere_hub_nem_quem_ja_esta_ligado(self):
        pub, _, _ = gerar()
        for p in pub['pessoas']:
            ids = [c['id'] for c in p['conhecer']]
            self.assertNotIn('farley-lobo', ids)
            self.assertNotIn(p['id'], ids)
        self.assertIn('bruno-reis', [c['id'] for c in por_nome(pub)['Carla Dias']['conhecer']])

    def test_estatisticas(self):
        pub, _, interno = gerar()
        e = pub['estatisticas']
        self.assertEqual(e['pessoas'], 5)
        self.assertEqual(e['ligacoes'], 2)
        self.assertEqual(e['organizacoes'], 4)
        self.assertEqual(e['pct_conectadas'], 60)
        self.assertEqual(interno['hub'], 'farley-lobo')


if __name__ == '__main__':
    unittest.main()
