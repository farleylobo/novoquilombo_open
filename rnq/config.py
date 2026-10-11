"""Decisões de modelo da RNQ. Mudou uma decisão? Mude aqui — o resto do pipeline segue.

Histórico das decisões (Farley, 04/10/2026):
- Comunidade = grupo onde as pessoas se encontram; tema = assunto em que trabalham; atuação = de onde atuam.
- YCL, Fito Network e Terapias Holísticas saíram.
- Diversidade/Equidade/Inclusão, Empreendedorismo, Mentoria e DH e Colaboração Internacional viraram temas.
- Tecnologia e ESG continuam comunidades e absorvem os temas equivalentes.
"""

EXCLUIR_COMUNIDADES = {'YCL', 'Fito Network', 'Terapias Holisticas', 'Terapias Holísticas'}

# Comunidade antiga (como está na planilha de seleção) -> tema
COMUNIDADE_PARA_TEMA = {
    'Diversidade Equidade e Inclusao': 'Diversidade, equidade & inclusão',
    'Empreendedorismo': 'Empreendedorismo & negócios de impacto',
    'Mentoria e DH': 'Mentoria & desenvolvimento humano',
    'Colaboracao Internacional': 'Colaboração internacional',
}

# Tema (já renomeado) -> comunidade que o absorve
TEMA_PARA_COMUNIDADE = {
    'Tecnologia, produto & dados': 'Tecnologia',
    'ESG & sustentabilidade': 'ESG',
}

# Nomes antigos de tema -> nome atual
RENOMEAR_TEMA = {
    'Produto, dados & transformação digital': 'Tecnologia, produto & dados',
    'Negócios de impacto': 'Empreendedorismo & negócios de impacto',
    'Estratégia, finanças & reporte ESG': 'ESG & sustentabilidade',
    'Diversidade & equidade racial': 'Diversidade, equidade & inclusão',
}

# Papéis de rede (Network Weaver Handbook, June Holley)
PAPEIS = [
    {'id': 'conector', 'nome': 'Conector(a)', 'nome_en': 'Connector',
     'desc': 'Apresenta pessoas que ainda não se conhecem e acompanha até a conexão virar relação.',
     'desc_en': 'Introduces people who do not know each other yet and follows up until the connection becomes a relationship.'},
    {'id': 'coordenador', 'nome': 'Coordenador(a) de projetos', 'nome_en': 'Project coordinator',
     'desc': 'Ajuda grupos a transformar conversa em projeto colaborativo.',
     'desc_en': 'Helps groups turn conversation into a collaborative project.'},
    {'id': 'facilitador', 'nome': 'Facilitador(a)', 'nome_en': 'Facilitator',
     'desc': 'Cuida de encontros e processos para que todo mundo participe.',
     'desc_en': 'Takes care of gatherings and processes so that everyone can take part.'},
    {'id': 'guardiao', 'nome': 'Guardiã(o) da rede', 'nome_en': 'Network steward',
     'desc': 'Cuida da infraestrutura da rede: comunicação, acordos, ferramentas.',
     'desc_en': 'Looks after the network’s infrastructure: communication, agreements, tools.'},
]

# Versão em inglês do site (botão PT | EN). Nome da rede em inglês: "Novo Quilombo Network" (Farley, 06/10/2026).
# Chave = nome em português exatamente como sai no site. Criou um tema/comunidade/atuação novo? Acrescente aqui;
# sem tradução, o site mostra o nome em português e o export avisa.
NOMES_EN = {
    # comunidades
    'Comunidade Integral': 'Integral Community',
    'Cultura Regenerativa': 'Regenerative Culture',
    'IDGs': 'IDGs',
    'Tecnologia': 'Technology',
    'ESG': 'ESG',
    'Teoria U': 'Theory U',
    # temas
    'Liderança & cultura organizacional': 'Leadership & organizational culture',
    'Desenvolvimento interior & presença': 'Inner development & presence',
    'Facilitação & processos coletivos': 'Facilitation & collective processes',
    'Clima & descarbonização': 'Climate & decarbonization',
    'Biodiversidade & territórios': 'Biodiversity & territories',
    'Direitos humanos & justiça social': 'Human rights & social justice',
    'Diversidade, equidade & inclusão': 'Diversity, equity & inclusion',
    'Ancestralidade & saberes tradicionais': 'Ancestry & traditional knowledge',
    'Educação & juventude': 'Education & youth',
    'Cuidado & saúde social': 'Care & social health',
    'IA & ética': 'AI & ethics',
    'Comunicação & mídia': 'Communication & media',
    'Redes & ecossistemas': 'Networks & ecosystems',
    'Empreendedorismo & negócios de impacto': 'Entrepreneurship & impact business',
    'Mentoria & desenvolvimento humano': 'Mentoring & human development',
    'Colaboração internacional': 'International collaboration',
    'Tecnologia, produto & dados': 'Technology, product & data',
    'ESG & sustentabilidade': 'ESG & sustainability',
    # atuação
    'Corporativo': 'Corporate',
    'Fundador(a) / Empreendedor(a)': 'Founder / Entrepreneur',
    'Consultoria, facilitação & coaching': 'Consulting, facilitation & coaching',
    'Terceiro setor & coletivos': 'Nonprofits & collectives',
    'Academia & pesquisa': 'Academia & research',
    'Setor público': 'Public sector',
    'Liderança comunitária & tradicional': 'Community & traditional leadership',
}

# Status de apresentação que já significam "essas duas pessoas se conhecem"
STATUS_APRESENTACAO_CONECTADA = {'apresentadas', 'acompanhando', 'colaborando'}
STATUS_APRESENTACAO = ['Sugerida', 'Apresentadas', 'Acompanhando', 'Colaborando', 'Não rolou']

TIPOS_INICIATIVA = ['Projeto', 'Encontro', 'Grupo de prática']

# Quem é o hub atual (para medir dependência e não sugerir sempre a mesma pessoa)
HUB_NOME = 'Farley Lobo'

# Lista fechada de campos públicos (RF3). O export falha se aparecer qualquer outro.
CAMPOS_PESSOA = {'id', 'nome', 'cargo', 'organizacao', 'comunidades', 'temas', 'atuacao', 'linkedin',
                 'papeis', 'compartilha', 'aprende', 'convoca', 'conhecer'}
CAMPOS_MURAL = {'id', 'tipo', 'titulo', 'descricao', 'areas', 'autor', 'autor_id', 'data', 'status'}
CAMPOS_INICIATIVA = {'id', 'tipo', 'titulo', 'descricao', 'areas', 'participantes', 'precisa',
                     'proponente', 'proponente_id', 'data', 'status'}
CAMPOS_LIGACAO = {'a', 'b', 'origem'}
CAMPOS_GRUPO = {'id', 'nome', 'nome_en'}                      # comunidades, temas, atuações
CAMPOS_PAPEL = {'id', 'nome', 'nome_en', 'desc', 'desc_en'}
CAMPOS_TOPO = {'versao', 'gerado_em', 'comunidades', 'temas', 'atuacoes', 'papeis', 'pessoas',
               'ligacoes', 'mural', 'iniciativas', 'estatisticas', 'sobre'}
CAMPOS_SOBRE = {'responsavel', 'contato'}

# "Sobre os dados" (LGPD): quem responde pelo mapa e o e-mail para pedidos de correção ou remoção.
# Sem e-mail, o export avisa e o publicar.py recusa publicar.
RESPONSAVEL_DADOS = 'Farley Lobo · Rede Novo Quilombo'
CONTATO_PRIVACIDADE = 'rnqbrasil@gmail.com'

# Limites de texto público
LIM_TITULO = 90
LIM_TEXTO = 420
LIM_PERFIL = 200
