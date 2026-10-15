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


def _contato(nome):
    """Contato fictício e único por pessoa (domínio reservado para exemplos)."""
    from rnq.util import slug
    return slug(nome).replace('-', '.') + '@exemplo.org'


def envios_tecelagem(nomes):
    """Envios fictícios dos formulários do site (mural, perfis, ligações, iniciativas, cadastros...), para a
    planilha de tecelagem de exemplo. Tudo pendente de moderação, como chega de verdade."""
    n = list(nomes)
    e = []

    def add(form, i, dia, **dados):
        e.append({'form': form, 'id': f'ex-{form}-{i}', 'criado': f'2026-10-{dia:02d}T1{i % 10}:00:00Z',
                  'dados': dados})

    add('mural', 1, 2, tipo='pedido', titulo='Procuro quem facilite uma roda sobre clima na escola',
        descricao='Queremos conversar com estudantes do ensino médio sobre clima e território.',
        areas=['Clima & descarbonização', 'Cultura Regenerativa'], nome=n[1], contato=_contato(n[1]), no_mapa=n[1])
    add('mural', 2, 5, tipo='oferta', titulo='Ofereço mentoria em análise de dados para coletivos',
        descricao='Duas horas por mês, por videochamada.', areas=['Tecnologia', 'IA & ética'],
        nome=n[2], contato=_contato(n[2]), no_mapa=n[2])
    add('mural', 3, 9, tipo='pedido', titulo='Indicação de espaço para encontro presencial',
        descricao='Para 30 pessoas em São Paulo, num sábado.', areas=['Facilitação & processos coletivos'],
        nome=n[3], contato=_contato(n[3]), no_mapa=n[3])
    add('mural', 4, 12, tipo='oferta', titulo='Ofereço revisão de relatórios de sustentabilidade',
        descricao='Para organizações pequenas, sem custo.', areas=['ESG'], nome=n[4], contato=_contato(n[4]),
        no_mapa=n[4])
    add('mural-resposta', 1, 6, item_id='ex-mural-1', item_titulo='Procuro quem facilite uma roda sobre clima na escola',
        nome=n[5], contato=_contato(n[5]), mensagem='Já facilitei rodas assim, posso ajudar!')
    add('perfil', 1, 7, pessoa=n[6], compartilha='Facilitação de círculos de diálogo', aprende='Comunicação não violenta',
        colabora_com=n[7], gostaria_colaborar=n[8], convocaria='Roda de leitura sobre redes', contato=_contato(n[6]))
    add('perfil', 2, 10, pessoa=n[9], compartilha='Design de serviços públicos', aprende='Teoria U',
        contato=_contato(n[9]))
    add('sugestao-ligacao', 1, 8, pessoa=n[10], quem_sugere=n[11], contexto='Trabalhamos juntas num projeto em 2025.')
    add('sugestao-ligacao', 2, 11, pessoa=n[12], quem_sugere=n[13], contexto='Somos da mesma turma de formação.')
    add('iniciativa', 1, 4, tipo='Grupo de prática', titulo='Círculo mensal de tecelagem de redes',
        descricao='Encontro online para praticar apresentações e acompanhamento.',
        areas=['Redes & ecossistemas', 'Comunidade Integral'], participantes=f'{n[14]}; {n[15]}',
        precisa='Uma pessoa para cuidar da agenda', nome=n[14], contato=_contato(n[14]))
    add('iniciativa-participar', 1, 13, iniciativa_id='ex-iniciativa-1',
        iniciativa_titulo='Círculo mensal de tecelagem de redes', nome=n[16], contato=_contato(n[16]),
        mensagem='Quero participar e posso ajudar na agenda.')
    add('participar', 1, 3, nome='Helena Exemplar', quem='eu', cargo='Educadora', organizacao='Escola Fictícia',
        contato='helena.exemplar@exemplo.org', local='Campinas', proposito='Aproximar escolas e coletivos de clima.',
        temas=['Educação & juventude', 'Clima & descarbonização'], atuacao=['Terceiro setor & coletivos'],
        comunidades=['Cultura Regenerativa'], fios=['Cuidado', 'Conexão'], visibilidade='mapa', maior_18='sim',
        idioma='pt', origem='site')
    add('participar', 2, 14, nome='Igor Reservado', quem='eu', cargo='Pesquisador', organizacao='Universidade Imaginária',
        contato='igor.reservado@exemplo.org', proposito='Conhecer a rede antes de aparecer.',
        temas=['IA & ética'], comunidades=['Tecnologia'], visibilidade='rede', maior_18='sim', idioma='pt',
        origem='site')
    return e


def gerar(pasta, com_tecelagem=False):
    os.makedirs(pasta, exist_ok=True)
    sel, tem, nomes = rede()
    escrever_selecao(os.path.join(pasta, 'RNQ-selecao.xlsx'), sel)
    escrever_temas(os.path.join(pasta, 'RNQ-temas-atuacao.xlsx'), tem, nomes)
    if com_tecelagem:
        from rnq import tecelagem
        arq = os.path.join(pasta, 'RNQ-tecelagem.xlsx')
        if os.path.exists(arq):
            os.remove(arq)
        tecelagem.criar(arq)
        tecelagem.adicionar_envios(arq, envios_tecelagem([p['nome'] for p in sel['pessoas'] if p['nome'] != HUB_NOME]))
    return pasta


if __name__ == '__main__':
    print(gerar(sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, '_trabalho', 'exemplo')))
