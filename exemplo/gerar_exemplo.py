"""Rede de exemplo, 100% fictícia, para quem clonar o projeto ver o site funcionando sem os dados reais.

Uso: python3 exportar.py --exemplo
Gera planilhas fictícias em _trabalho/exemplo/ (fora do repositório) e o site em site/.
Os nomes são combinações aleatórias (com semente fixa) de nomes e sobrenomes comuns; as organizações são inventadas.
"""
import os
import random
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, 'tests'))

from apoio import escrever_selecao, escrever_temas  # noqa: E402
from rnq.config import HUB_NOME  # noqa: E402

NOMES = ['Ana', 'Bruno', 'Carla', 'Diego', 'Elisa', 'Fábio', 'Gabriela', 'Heitor', 'Iara', 'João', 'Kátia', 'Lucas',
         'Marina', 'Nilo', 'Olívia', 'Paulo', 'Quitéria', 'Rafael', 'Sara', 'Tiago', 'Úrsula', 'Vítor', 'Wanda',
         'Yara', 'Zeca', 'Benedita', 'Caio', 'Dandara', 'Enzo', 'Flora', 'Gilberto', 'Helena', 'Igor', 'Jussara']
SOBRENOMES = ['Almeida', 'Barros', 'Costa', 'Duarte', 'Esteves', 'Freitas', 'Gomes', 'Holanda', 'Ignácio', 'Jardim',
              'Lacerda', 'Macedo', 'Nogueira', 'Oliveira', 'Pacheco', 'Queiroz', 'Rocha', 'Siqueira', 'Teixeira',
              'Vieira']
ORGS = ['Instituto Raiz Viva', 'Coletivo Ponte', 'Empresa Exemplo S.A.', 'Universidade Imaginária', 'Prefeitura de Exemplópolis',
        'Associação Casa Comum', 'Consultoria Trama', 'Startup Semente', 'Fundação Horizonte', 'Cooperativa Mutirão',
        'Rede Fictícia de Escolas', 'Banco Inventado', 'Ateliê Encontro', 'Laboratório Aberto']
CARGOS = ['Coordenadora de projetos', 'Diretor', 'Pesquisadora', 'Facilitador', 'Gerente de sustentabilidade',
          'Fundadora', 'Educador', 'Analista de dados', 'Consultora', 'Articulador comunitário', 'Product Owner',
          'Mentora', 'Designer de serviços']
COMUNIDADES = ['Comunidade Integral', 'Cultura Regenerativa', 'IDGs', 'Tecnologia', 'ESG', 'Teoria U']
TEMAS = ['Liderança & cultura organizacional', 'Desenvolvimento interior & presença', 'Facilitação & processos coletivos',
         'Clima & descarbonização', 'Biodiversidade & territórios', 'Direitos humanos & justiça social',
         'Diversidade, equidade & inclusão', 'Ancestralidade & saberes tradicionais', 'Educação & juventude',
         'Cuidado & saúde social', 'IA & ética', 'Comunicação & mídia', 'Redes & ecossistemas']
ATUACAO = ['Corporativo', 'Fundador(a) / Empreendedor(a)', 'Consultoria, facilitação & coaching',
           'Terceiro setor & coletivos', 'Academia & pesquisa', 'Setor público', 'Liderança comunitária & tradicional']


def rede(n=36, semente=7):
    r = random.Random(semente)
    nomes, usados = [], set()
    while len(nomes) < n:
        nm = f'{r.choice(NOMES)} {r.choice(SOBRENOMES)}'
        if nm not in usados:
            usados.add(nm)
            nomes.append(nm)
    pessoas, por_chave, nomes_ext = [], {}, {}
    for i, nm in enumerate(nomes):
        coms = r.sample(COMUNIDADES, r.choice([0, 1, 1, 1, 2])) if i % 11 else []
        ext = 'ex:' + str(i)
        pessoas.append({'nome': nm, 'cargo': r.choice(CARGOS), 'organizacao': r.choice(ORGS), 'linkedin': '',
                        'ext': ext, 'comunidades': coms})
        por_chave[ext] = (r.sample(TEMAS, r.choice([1, 2, 3])), r.sample(ATUACAO, r.choice([1, 1, 2])))
        nomes_ext[ext] = nm
    pessoas.append({'nome': HUB_NOME, 'cargo': 'Fundador', 'organizacao': 'Rede Novo Quilombo', 'linkedin': '',
                    'ext': 'ex:hub', 'comunidades': ['Comunidade Integral', 'IDGs']})
    por_chave['ex:hub'] = (['Redes & ecossistemas'], ['Terceiro setor & coletivos'])
    nomes_ext['ex:hub'] = HUB_NOME
    ligs = [(HUB_NOME, nomes[i]) for i in range(0, n, 4)]
    ligs += [(nomes[i], nomes[i + 1]) for i in range(1, n - 1, 5)]
    sel = {'comunidades': COMUNIDADES, 'pessoas': pessoas, 'ligacoes': ligs}
    tem = {'existe': True, 'ordem_temas': TEMAS, 'ordem_atuacao': ATUACAO, 'por_chave': por_chave}
    return sel, tem, nomes_ext


def gerar(pasta):
    os.makedirs(pasta, exist_ok=True)
    sel, tem, nomes = rede()
    escrever_selecao(os.path.join(pasta, 'RNQ-selecao.xlsx'), sel)
    escrever_temas(os.path.join(pasta, 'RNQ-temas-atuacao.xlsx'), tem, nomes)
    return pasta


if __name__ == '__main__':
    print(gerar(sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, '_trabalho', 'exemplo')))
