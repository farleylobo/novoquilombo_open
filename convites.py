"""Lista de convites: uma linha por pessoa do mapa, com o link direto para o card dela e uma mensagem pronta
(PT e EN) para mandar no WhatsApp, LinkedIn ou e-mail, pedindo que confirme, atualize ou retire seu nome.

    python3 convites.py

Gera privado/convites-mapa.csv (abre no Excel). É PRIVADO: tem nomes e fica fora do repositório.
Usa os dados já gerados em site/rnq-publico.json (rode atualizar.py antes) e RNQ_SITE_URL do .env.
"""
import csv
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from rnq import netlify  # noqa: E402

PADRAO_URL = 'https://mapa-novoquilombo.netlify.app'

MSG_PT = ('Oi, {primeiro}! Tudo bem? Montei o mapa da Rede Novo Quilombo: quem faz parte da rede, onde a gente se '
          'encontra e com o que cada pessoa trabalha. Você está nele: {link}\n\n'
          'No seu card você confere seus dados e escolhe:\n'
          '• "Quero ficar no mapa" para confirmar;\n'
          '• "Atualizar meu perfil" para contar o que pode compartilhar e o que quer aprender;\n'
          '• "Quero sair", se preferir não aparecer. Sem problema nenhum, é um clique.\n\n'
          'Aparecem só nome, cargo, organização e LinkedIn, nunca contato. Qualquer dúvida, me chama!')
MSG_EN = ('Hi {primeiro}! I have put together a map of the Novo Quilombo Network: who is in the network, where we meet '
          'and what each person works on. You are on it: {link}\n\n'
          'On your card you can check your details and choose:\n'
          '• "Keep me on the map" to confirm;\n'
          '• "Update my profile" to share what you can offer and what you want to learn;\n'
          '• "Remove me" if you would rather not appear. No problem at all, it is one click.\n\n'
          'Only name, job title, organization and LinkedIn are shown, never contact details. Any questions, let me know!')


def linhas(pub, url):
    url = url.rstrip('/')
    out = []
    for p in sorted(pub['pessoas'], key=lambda x: x['nome'].lower()):
        primeiro = p['nome'].split()[0]
        lpt, len_ = f"{url}/#p/{p['id']}", f"{url}/?lang=en#p/{p['id']}"
        out.append({'Nome': p['nome'], 'Organização': p.get('organizacao') or '', 'Link (PT)': lpt, 'Link (EN)': len_,
                    'Mensagem (PT)': MSG_PT.format(primeiro=primeiro, link=lpt),
                    'Mensagem (EN)': MSG_EN.format(primeiro=primeiro, link=len_),
                    'Enviado?': '', 'Resposta': ''})
    return out


def main():
    with open(os.path.join(AQUI, 'site', 'rnq-publico.json'), encoding='utf-8') as fh:
        pub = json.load(fh)
    if os.path.exists(os.path.join(AQUI, 'site', '.exemplo')):
        sys.exit('O site está com a rede fictícia. Rode python3 atualizar.py antes.')
    url = netlify.ler_env(AQUI).get('RNQ_SITE_URL') or PADRAO_URL
    ls = linhas(pub, url)
    os.makedirs(os.path.join(AQUI, 'privado'), exist_ok=True)
    destino = os.path.join(AQUI, 'privado', 'convites-mapa.csv')
    with open(destino, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(ls[0]), delimiter=';')
        w.writeheader()
        w.writerows(ls)
    print(f'{len(ls)} convites em {destino}')


if __name__ == '__main__':
    main()
