// Acesso aos dados do painel. Duas implementações com a mesma interface:
//  - ApiSupabase: o painel de verdade (login, MFA, banco com regras de acesso).
//  - ApiDemo (demo.js): rede fictícia em memória, para mostrar o painel sem dados reais.
// Toda permissão de verdade é conferida no banco (RLS e funções rnq_*); aqui só se chama.
(function () {
  'use strict';

  function falhar(error, extra) {
    const e = new Error((error && (error.message || error.msg)) || 'erro');
    e.codigo = (error && (error.code || error.status)) || (extra && extra.codigo) || '';
    e.original = error;
    throw e;
  }

  class ApiSupabase {
    constructor(cfg) {
      this.modo = 'real';
      this.sb = window.supabase.createClient(cfg.supabaseUrl, cfg.chavePublica, {
        auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, flowType: 'implicit',
                storageKey: 'rnq-painel-sessao' },
      });
    }

    // ---- login
    async sessao() {
      const { data, error } = await this.sb.auth.getSession();
      if (error) falhar(error);
      return data.session;
    }
    aoMudarSessao(cb) { this.sb.auth.onAuthStateChange((evento, sessao) => cb(evento, sessao)); }
    async enviarCodigo(email) {
      const { error } = await this.sb.auth.signInWithOtp({
        email, options: { shouldCreateUser: false, emailRedirectTo: location.origin + location.pathname } });
      if (error) falhar(error);
    }
    async verificarCodigo(email, token) {
      const { error } = await this.sb.auth.verifyOtp({ email, token, type: 'email' });
      if (error) falhar(error);
    }
    async sair() { await this.sb.auth.signOut(); }

    // ---- MFA (app autenticador)
    async mfa() {
      const nivel = await this.sb.auth.mfa.getAuthenticatorAssuranceLevel();
      if (nivel.error) falhar(nivel.error);
      const fatores = await this.sb.auth.mfa.listFactors();
      if (fatores.error) falhar(fatores.error);
      const todos = fatores.data.all || [];
      return { atual: nivel.data.currentLevel, proximo: nivel.data.nextLevel,
               verificado: todos.find(f => f.factor_type === 'totp' && f.status === 'verified') || null, todos };
    }
    async mfaCadastrar() {
      const st = await this.mfa();
      for (const f of st.todos) {                       // cadastro que ficou pela metade
        if (f.status !== 'verified') await this.sb.auth.mfa.unenroll({ factorId: f.id });
      }
      const { data, error } = await this.sb.auth.mfa.enroll({
        factorType: 'totp', friendlyName: 'Painel RNQ ' + new Date().toISOString().slice(0, 16) });
      if (error) falhar(error);
      return { id: data.id, qr: data.totp.qr_code, segredo: data.totp.secret };
    }
    async mfaVerificar(factorId, code) {
      const { error } = await this.sb.auth.mfa.challengeAndVerify({ factorId, code });
      if (error) falhar(error);
    }

    // ---- dados
    async rpc(nome, args) {
      const { data, error } = await this.sb.rpc(nome, args || {});
      if (error) falhar(error);
      return data;
    }
    async tabela(consulta) {
      const { data, error } = await consulta;
      if (error) falhar(error);
      return data;
    }
    perfil() { return this.rpc('rnq_meu_perfil'); }
    definirIdioma(idioma) { return this.rpc('rnq_definir_idioma', { p_idioma: idioma }); }
    comunidades() {
      return this.tabela(this.sb.from('comunidades').select('id,nome,nome_en,ativa').order('nome'));
    }
    snapshots() {
      return this.tabela(this.sb.from('snapshots').select('escopo,gerado_em,resumo').order('escopo'));
    }
    async snapshotHtml(escopo, idioma) {
      const col = idioma === 'en' ? 'html_en' : 'html_pt';
      const linha = await this.tabela(this.sb.from('snapshots').select(col).eq('escopo', escopo).maybeSingle());
      return linha ? linha[col] : null;
    }
    moderacao() {
      return this.tabela(this.sb.from('moderacao').select('*')
        .order('recebido_em', { ascending: false, nullsFirst: false }).limit(2000));
    }
    decidir(id, status, motivo) {
      return this.rpc('rnq_decidir', { p_id: id, p_status: status, p_motivo: motivo || null });
    }
    equipe() { return this.rpc('rnq_equipe_listar'); }
    atualizarMembro(userId, m) {
      return this.rpc('rnq_equipe_atualizar', {
        p_user: userId, p_papel: m.papel ?? null, p_ativo: m.ativo ?? null,
        p_comunidades: m.comunidades ?? null, p_nome: m.nome ?? null });
    }
    async convidar(dados) {
      const { data, error } = await this.sb.functions.invoke('convidar', { body: dados });
      if (error) {
        let corpo = null;
        try { corpo = await error.context.json(); } catch (_) { /* resposta sem JSON */ }
        falhar({ message: (corpo && corpo.erro) || error.message, code: corpo && corpo.codigo });
      }
      return data;
    }
    painelStatus() { return this.rpc('rnq_painel_status'); }
    auditoria() {
      return this.tabela(this.sb.from('auditoria').select('*').order('quando', { ascending: false }).limit(300));
    }
  }

  window.RNQ_API = Object.assign(window.RNQ_API || {}, { ApiSupabase });
})();
