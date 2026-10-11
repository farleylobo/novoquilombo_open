"""Pipeline da visão pública da Rede Novo Quilombo (RNQ).

Módulos:
- config      — decisões de modelo (comunidades, temas, papéis) e lista fechada de campos públicos
- util        — normalização de texto e identificadores
- fontes      — leitura das planilhas (seleção, temas/atuação, tecelagem)
- tecelagem   — criação e atualização da planilha de tecelagem (moderação)
- netlify     — leitura dos envios de formulários do Netlify (API ou CSV)
- rede        — métricas de saúde da rede e sugestões de apresentação (June Holley)
- publico     — monta o JSON público (somente campos permitidos)
- painel      — gera o painel local do tecelão (HTML, nunca publicado)
"""
__version__ = "2.0.0"
