// Modo demonstração: a mesma interface da ApiSupabase, em memória, com a rede fictícia de demo-dados.js.
// Reproduz as regras do banco (quem vê o quê, quem decide, último admin) para a demonstração ser fiel.
// Nada é salvo: recarregar a página volta ao começo.
(function () {
  'use strict';
  const copia = (x) => JSON.parse(JSON.stringify(x));
  const agora = () => new Date().toISOString();

  function erro(msg, codigo) { const e = new Error(msg); e.codigo = codigo || ''; throw e; }

  class ApiDemo {
    constructor(dados) {
      this.modo = 'demo';
      this.d = copia(dados);
      this.quem = this.d.equipe[0].user_id;
      this.idAud = 100;
    }
    eu() { return this.d.equipe.find(p => p.user_id === this.quem); }
    ehAdmin() { const e = this.eu(); return !!(e && e.ativo && e.papel === 'admin'); }
    pode(coms) {
      const e = this.eu();
      if (!e || !e.ativo) return false;
      return this.ehAdmin() || (coms || []).some(c => e.comunidades.includes(c));
    }
    auditar(acao, alvo, detalhes) {
      this.d.auditoria.unshift({ id: ++this.idAud, quem_email: this.eu().email, acao, alvo, quando: agora(), detalhes });
    }
    verComo(userId) { this.quem = userId; }
    pessoas() { return this.d.equipe.map(p => ({ user_id: p.user_id, nome: p.nome, papel: p.papel, comunidades: p.comunidades })); }

    async sessao() { return { user: { email: this.eu().email } }; }
    aoMudarSessao() {}
    async enviarCodigo() {}
    async verificarCodigo() {}
    async sair() { location.reload(); }
    async mfa() { return { atual: 'aal2', proximo: 'aal2', verificado: { id: 'demo' }, todos: [] }; }
    async mfaCadastrar() { return { id: 'demo', qr: '', segredo: 'DEMO' }; }
    async mfaVerificar() {}

    async perfil() {
      const e = this.eu();
      return { user_id: e.user_id, email: e.email, nome: e.nome, papel: e.papel, idioma: e.idioma,
               comunidades: e.comunidades.slice(), mfa_exigido: e.papel === 'admin', sessao_ok: true };
    }
    async definirIdioma(idioma) { this.eu().idioma = idioma; }
    async comunidades() { return copia(this.d.comunidades).map(c => Object.assign(c, { ativa: true })); }
    async snapshots() {
      return this.d.snapshots
        .filter(s => this.ehAdmin() || (s.escopo !== 'rede' && this.pode([s.escopo])))
        .map(s => ({ escopo: s.escopo, gerado_em: s.gerado_em, resumo: copia(s.resumo) }));
    }
    async snapshotHtml(escopo, idioma) {
      const s = this.d.snapshots.find(x => x.escopo === escopo);
      if (!s || !(this.ehAdmin() || (escopo !== 'rede' && this.pode([escopo])))) return null;
      return idioma === 'en' ? s.html_en : s.html_pt;
    }
    async moderacao() { return copia(this.d.moderacao.filter(i => this.pode(i.comunidades))); }
    async decidir(id, status, motivo) {
      const i = this.d.moderacao.find(x => x.id === id);
      if (!i || !this.pode(i.comunidades)) erro('Sem permissão para decidir este item', '42501');
      if (status === 'aprovado' && i.conteudo.bloqueio) erro('Este item não pode ser aprovado', '22023');
      const de = i.status;
      Object.assign(i, status === 'pendente'
        ? { status, motivo: null, decidido_por_nome: null, decidido_em: null, origem_decisao: null }
        : { status, motivo: (motivo || '').trim() || null, decidido_por_nome: this.eu().nome, decidido_em: agora(),
            origem_decisao: 'painel' });
      this.auditar('moderacao.decidir', `${i.tipo}:${i.item_id}`, { de, para: status, titulo: i.titulo, motivo: i.motivo });
      return copia(i);
    }
    async equipe() {
      if (!this.ehAdmin()) erro('Só admin vê a equipe', '42501');
      return copia(this.d.equipe);
    }
    async atualizarMembro(userId, m) {
      if (!this.ehAdmin()) erro('Só admin muda a equipe', '42501');
      const p = this.d.equipe.find(x => x.user_id === userId);
      const papel = m.papel ?? p.papel, ativo = m.ativo ?? p.ativo;
      const outrosAdmins = this.d.equipe.filter(x => x.user_id !== userId && x.papel === 'admin' && x.ativo).length;
      if (p.papel === 'admin' && p.ativo && !(papel === 'admin' && ativo) && !outrosAdmins) {
        erro('A rede precisa de pelo menos um admin ativo', 'P0001');
      }
      const antes = copia(p);
      Object.assign(p, { papel, ativo, comunidades: m.comunidades ?? p.comunidades, nome: m.nome || p.nome });
      this.auditar('equipe.atualizar', p.email, { papel: [antes.papel, p.papel], ativo: [antes.ativo, p.ativo],
                                                  comunidades: [antes.comunidades, p.comunidades] });
      return { user_id: p.user_id, papel: p.papel, ativo: p.ativo, comunidades: p.comunidades };
    }
    async convidar(dados) {
      if (!this.ehAdmin()) erro('Só admin convida', '42501');
      const email = String(dados.email || '').trim().toLowerCase();
      const existente = this.d.equipe.find(x => x.email === email);
      const membro = existente || { user_id: 'demo-' + (this.d.equipe.length + 1), email, criado_em: agora(),
                                    ultimo_acesso: null, mfa: false };
      Object.assign(membro, { nome: dados.nome || membro.nome || '', papel: dados.papel, ativo: true,
                              comunidades: dados.comunidades || [], idioma: dados.idioma || 'pt' });
      if (!existente) this.d.equipe.push(membro);
      this.auditar(existente ? 'equipe.reconvidar' : 'equipe.convidar', email,
                   { papel: dados.papel, comunidades: dados.comunidades || [] });
      return { ok: true, novo: !existente, convite_enviado: !existente };
    }
    async auditoria() {
      if (!this.ehAdmin()) erro('Só admin vê o histórico', '42501');
      return copia(this.d.auditoria);
    }
  }

  window.RNQ_API = Object.assign(window.RNQ_API || {}, { ApiDemo });
})();
