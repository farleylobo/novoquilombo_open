"""Formulário "Faça parte" (participar): sincronização para a aba Cadastros e entrada no mapa."""
import json
import os
import tempfile
import unittest
from datetime import datetime

from apoio import selecao_base, temas_base

from rnq import config as C
from rnq import fontes, tecelagem
from rnq.publico import ErroPrivacidade, montar, validar

AGORA = datetime(2026, 10, 11, 12, 0)


def envio(i='c1', **dados):
    base = {'nome': 'Marina Teste', 'quem': 'pessoa', 'contato': 'marina@exemplo.org', 'cargo': 'Facilitadora',
            'organizacao': 'Coletivo Raiz', 'linkedin': 'linkedin.com/in/marina-teste',
            'proposito': 'Criar espaços de escuta.', 'aniversario': '14/03', 'local': 'Salvador, BA',
            'temas': 'Facilitação & processos coletivos; Clima & descarbonização', 'tema_outro': '',
            'atuacao': 'Terceiro setor & coletivos', 'comunidades': 'Cultura Regenerativa; A Gente Muda',
            'quer_orgs': 'Instituto Segredo', 'necessidade': 'Alimento & água',
            'ofertas': 'Mentoria; Conduzir uma meditação', 'oferta': 'Círculo de 2h on-line.',
            'pedido': 'Conhecer quem trabalha com agrofloresta.', 'mural': 'sim', 'objetivo': 'tecer',
            'fios': 'Conexão; Acolhida', 'formatos': 'Mentoria', 'indicacoes': 'Zé Indicado (zé@exemplo.org)',
            'visibilidade': 'mapa', 'maior_18': 'sim', 'idioma': 'pt', 'origem': 'convite'}
    base.update(dados)
    return {'form': 'participar', 'id': i, 'criado': '2026-10-11T10:00:00Z', 'dados': base}


class Sincronizar(unittest.TestCase):
    def test_cadastro_vai_para_aba_e_oferta_pedido_para_o_mural(self):
        with tempfile.TemporaryDirectory() as d:
            arq = os.path.join(d, 'RNQ-tecelagem.xlsx')
            novos = tecelagem.adicionar_envios(arq, [envio()])
            self.assertEqual(novos, {'Cadastros': 1, 'Mural': 2})
            tec = fontes.ler_tecelagem(arq)
            c = tec['Cadastros'][0]
            self.assertEqual(c['Contato (privado)'], 'marina@exemplo.org')
            self.assertEqual(c['Aniversário (privado)'], '14/03')
            self.assertEqual(c['Fios'], 'Conexão; Acolhida')
            self.assertIsNone(c.get('Incluir no mapa?'))
            tipos = {m['Tipo']: m for m in tec['Mural']}
            self.assertEqual(set(tipos), {'Oferta', 'Pedido'})
            self.assertIsNone(tipos['Oferta'].get('Publicar?'), 'mural só publica depois da moderação')
            self.assertEqual(tipos['Pedido']['Está no mapa como'], 'Marina Teste')
            # reenviar não duplica
            self.assertEqual(tecelagem.adicionar_envios(arq, [envio()]), {})

    def test_sem_autorizacao_nao_cria_mural(self):
        with tempfile.TemporaryDirectory() as d:
            arq = os.path.join(d, 'RNQ-tecelagem.xlsx')
            self.assertEqual(tecelagem.adicionar_envios(arq, [envio(mural='nao')]), {'Cadastros': 1})


def cadastro(**k):
    linha = {'ID': 'c1', 'Nome': 'Marina Teste', 'Cargo': 'Facilitadora', 'Organização': 'Coletivo Raiz',
             'LinkedIn': 'linkedin.com/in/marina-teste', 'Contato (privado)': 'marina@exemplo.org',
             'Cidade (privado)': 'Salvador, BA', 'Aniversário (privado)': '14/03',
             'Propósito': 'Criar espaços de escuta.',
             'Temas': 'Redes & ecossistemas; Clima & descarbonização',
             'Atuação': 'Terceiro setor & coletivos', 'Comunidades': 'Cultura Regenerativa; A Gente Muda',
             'Quer se aproximar de (privado)': 'Instituto Segredo', 'Ofertas': 'Mentoria',
             'Oferta (texto)': 'Círculo de 2h on-line.', 'Fios': 'Conexão; Acolhida',
             'Indicações (privado)': 'Zé Indicado', 'Visibilidade': 'mapa', '18 anos ou mais': 'sim',
             'Incluir no mapa?': 'Sim'}
    linha.update(k)
    return {'Cadastros': [linha]}


def gerar(tec):
    return montar(selecao_base(), temas_base(), tec, AGORA)


class EntrarNoMapa(unittest.TestCase):
    def test_cadastro_aprovado_vira_pessoa(self):
        pub, avisos, _ = gerar(cadastro())
        p = {x['nome']: x for x in pub['pessoas']}['Marina Teste']
        self.assertEqual(p['temas'], ['redes-ecossistemas', 'clima-descarbonizacao'])
        self.assertEqual(p['comunidades'], ['cultura-regenerativa', 'a-gente-muda'])
        self.assertEqual(p['fios'], ['conexao', 'acolhida'])
        self.assertEqual(p['proposito'], 'Criar espaços de escuta.')
        self.assertEqual(p['linkedin'], 'https://linkedin.com/in/marina-teste')
        self.assertIn('Círculo de 2h', p['compartilha'])
        com = {c['nome']: c for c in pub['comunidades']}['A Gente Muda']
        self.assertEqual(com['nome_en'], 'A Gente Muda')
        texto = json.dumps(pub, ensure_ascii=False)
        for privado in ('marina@exemplo.org', 'Salvador', '14/03', 'Instituto Segredo', 'Zé Indicado'):
            self.assertNotIn(privado, texto)
        self.assertTrue(validar(pub))

    def test_sem_aprovacao_fora_do_mapa_ou_sem_18_nao_entra(self):
        for k, aviso in (({'Incluir no mapa?': None}, None), ({'Visibilidade': 'fora'}, 'fora do mapa'),
                         ({'18 anos ou mais': None}, '18 anos')):
            pub, avisos, _ = gerar(cadastro(**k))
            self.assertNotIn('Marina Teste', [x['nome'] for x in pub['pessoas']], k)
            if aviso:
                self.assertTrue(any(aviso in a for a in avisos), k)

    def test_pessoa_que_ja_estava_soma_dados(self):
        pub, avisos, _ = gerar(cadastro(Nome='Bruno Reis', Temas='Redes & ecossistemas', Comunidades='Cultura Regenerativa'))
        ps = [x for x in pub['pessoas'] if x['nome'] == 'Bruno Reis']
        self.assertEqual(len(ps), 1)
        self.assertIn('redes-ecossistemas', ps[0]['temas'])
        self.assertIn('clima-descarbonizacao', ps[0]['temas'])      # o que já tinha continua
        self.assertIn('cultura-regenerativa', ps[0]['comunidades'])
        self.assertIn('idgs', ps[0]['comunidades'])
        self.assertEqual(ps[0]['proposito'], 'Criar espaços de escuta.')
        self.assertTrue(any('já estava no mapa' in a for a in avisos))

    def test_nomes_desconhecidos_viram_aviso(self):
        pub, avisos, _ = gerar(cadastro(Temas='Tema Inventado; Clima & descarbonização', Comunidades='Fito'))
        self.assertTrue(any('tema "Tema Inventado"' in a for a in avisos))
        self.assertTrue(any('comunidade "Fito"' in a for a in avisos))

    def test_saida_vence_cadastro(self):
        tec = cadastro()
        tec['Saídas'] = [{'Nome': 'Marina Teste', 'Remover?': 'Sim'}]
        pub, avisos, _ = gerar(tec)
        self.assertNotIn('Marina Teste', [x['nome'] for x in pub['pessoas']])
        self.assertFalse(any('não corresponde a ninguém' in a for a in avisos))


class Listas(unittest.TestCase):
    def test_listas_completas_do_formulario(self):
        pub, _, _ = gerar({})
        ls = pub['listas']
        self.assertEqual(len(ls['fios']), 12)
        self.assertEqual(ls['fios'][6]['nome_en'], 'Connection')
        self.assertIn('A Gente Muda', [c['nome'] for c in ls['comunidades']])
        self.assertNotIn('YCL', [c['nome'] for c in ls['comunidades']])
        self.assertTrue(all(c['nome_en'] for c in ls['comunidades'] + ls['temas'] + ls['atuacoes']))

    def test_lista_fechada_nas_listas(self):
        pub, _, _ = gerar({})
        pub['listas']['fios'][0]['contato'] = 'x'
        with self.assertRaises(ErroPrivacidade):
            validar(pub)
        pub, _, _ = gerar({})
        pub['listas']['pessoas'] = []
        with self.assertRaises(ErroPrivacidade):
            validar(pub)

    def test_toda_comunidade_nova_tem_traducao(self):
        for c in C.COMUNIDADES_NOVAS:
            self.assertTrue(C.NOMES_EN.get(c), c)


if __name__ == '__main__':
    unittest.main()
