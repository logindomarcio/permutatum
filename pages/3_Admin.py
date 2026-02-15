import streamlit as st
import hashlib
from datetime import datetime

# ── Configuração da página ──
st.set_page_config(page_title="Permutatum - Admin", page_icon="🔒", layout="wide")

# ── Função init_supabase (mesma lógica dos outros arquivos) ──
from supabase import create_client
import os


def init_supabase():
    try:
        try:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
        except:
            url = os.environ.get("SUPABASE_URL", "")
            key = os.environ.get("SUPABASE_KEY", "")

        if not url or not key:
            st.error("Credenciais do Supabase não encontradas.")
            return None

        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao conectar com Supabase: {e}")
        return None


# ── Função para hashear senha ──
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()


# ── Função para verificar login admin ──
def verificar_admin(email, senha):
    supabase = init_supabase()
    if not supabase:
        return None

    try:
        response = supabase.table("admins").select("*").eq("email", email.strip().lower()).eq("ativo", True).execute()

        if response.data:
            admin = response.data[0]
            # Verificar senha (texto simples por enquanto, depois pode hashear)
            if admin.get('senha_hash') == senha:
                return admin

        return None
    except:
        return None


# ── Função para enviar email via Brevo API ──
def enviar_email_brevo(destinatario_email, destinatario_nome, assunto, conteudo_html):
    """Envia email usando a API do Brevo diretamente."""
    import requests

    BREVO_API_KEY = None
    try:
        BREVO_API_KEY = st.secrets.get("BREVO_API_KEY", None)
    except:
        BREVO_API_KEY = os.environ.get("BREVO_API_KEY", None)

    if not BREVO_API_KEY:
        return False, "Chave API do Brevo não configurada"

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": BREVO_API_KEY
    }
    payload = {
        "sender": {"name": "Permutatum", "email": "noreply@permutatum.com.br"},
        "to": [{"email": destinatario_email, "name": destinatario_nome}],
        "subject": assunto,
        "htmlContent": conteudo_html
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            return True, "Email enviado com sucesso"
        else:
            return False, f"Erro {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Erro ao enviar: {str(e)}"


# ── Session State ──
if "admin_logado" not in st.session_state:
    st.session_state["admin_logado"] = None

# ══════════════════════════════════════
# LOGIN DO ADMIN
# ══════════════════════════════════════
if not st.session_state["admin_logado"]:
    st.title("🔒 Painel Administrativo")
    st.warning("Acesso restrito a administradores.")

    with st.form("login_admin"):
        email_admin = st.text_input("Email do administrador")
        senha_admin = st.text_input("Senha", type="password")
        login_btn = st.form_submit_button("🔑 Entrar", use_container_width=True)

    if login_btn:
        if email_admin and senha_admin:
            admin = verificar_admin(email_admin, senha_admin)
            if admin:
                st.session_state["admin_logado"] = admin
                st.success(f"Bem-vindo, {admin.get('nome', 'Admin')}!")
                st.rerun()
            else:
                st.error("❌ Email ou senha incorretos.")
        else:
            st.error("Preencha email e senha.")

# ══════════════════════════════════════
# PAINEL ADMIN (após login)
# ══════════════════════════════════════
else:
    admin = st.session_state["admin_logado"]
    is_super = admin.get('nivel') == 'super'

    st.title("🔒 Painel Administrativo")
    st.caption(f"Logado como: **{admin.get('nome')}** ({admin.get('nivel', 'delegado')})")

    # ── Abas ──
    if is_super:
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Solicitações Pendentes",
            "📜 Histórico",
            "🔄 Trocar Email de Magistrado",
            "👥 Gerenciar Admins"
        ])
    else:
        tab1, tab2, tab3 = st.tabs([
            "📋 Solicitações Pendentes",
            "📜 Histórico",
            "🔄 Trocar Email de Magistrado"
        ])

    # ══════════════════════════════════
    # ABA 1: SOLICITAÇÕES PENDENTES
    # ══════════════════════════════════
    with tab1:
        st.subheader("📋 Solicitações Pendentes de Cadastro")

        supabase = init_supabase()
        if supabase:
            pendentes = supabase.table("solicitacoes").select("*").eq("status", "pendente").order("created_at", desc=False).execute()

            if pendentes.data and len(pendentes.data) > 0:
                st.info(f"**{len(pendentes.data)}** solicitação(ões) pendente(s)")

                for sol in pendentes.data:
                    with st.expander(f"📌 {sol.get('nome', '')} — {sol.get('tj_origem', '')} ({sol.get('created_at', '')[:10]})"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Nome:** {sol.get('nome', '')}")
                            st.write(f"**TJ Origem:** {sol.get('tj_origem', '')}")
                            st.write(f"**Tipo:** {sol.get('tipo', '')}")
                        with col2:
                            st.write(f"**Email pessoal:** {sol.get('email_pessoal', '')}")
                            st.write(f"**Email institucional:** {sol.get('email_institucional', 'Não informado')}")
                            st.write(f"**Data:** {sol.get('created_at', '')[:19]}")

                        st.markdown("---")
                        st.markdown("**💡 Pesquise na internet para validar se é magistrado(a) real.**")

                        # Link de pesquisa rápida no Google
                        nome_pesquisa = sol.get('nome', '').replace(' ', '+')
                        tj_pesquisa = sol.get('tj_origem', '').replace(' ', '+')
                        link_google = f"https://www.google.com/search?q={nome_pesquisa}+magistrado+{tj_pesquisa}"
                        st.markdown(f"[🔍 Pesquisar no Google]({link_google})")

                        observacao = st.text_input(
                            "Observação (opcional):",
                            key=f"obs_{sol.get('id')}",
                            placeholder="Motivo da rejeição, etc."
                        )

                        col_a, col_r = st.columns(2)

                        with col_a:
                            if st.button("✅ Aprovar", key=f"aprovar_{sol.get('id')}", type="primary", use_container_width=True):
                                # Atualizar status para aprovado
                                supabase.table("solicitacoes").update({
                                    "status": "aprovado",
                                    "admin_responsavel": admin.get('email', ''),
                                    "data_decisao": datetime.now().isoformat(),
                                    "observacao": observacao if observacao else None
                                }).eq("id", sol.get('id')).execute()

                                # Enviar email de confirmação via Brevo
                                html_aprovado = f"""
                                <h2>Permutatum — Cadastro Aprovado!</h2>
                                <p>Olá, <strong>{sol.get('nome', '')}</strong>!</p>
                                <p>Seu cadastro no Permutatum foi <strong>aprovado</strong> pelo administrador.</p>
                                <p>Agora acesse o sistema e complete seus dados:</p>
                                <p>👉 <a href="https://permutatum.streamlit.app/">https://permutatum.streamlit.app/</a></p>
                                <p>Use seu email pessoal (<strong>{sol.get('email_pessoal', '')}</strong>) para fazer login.</p>
                                <br>
                                <p><em>Permutatum — Sistema de Permutas da Magistratura</em></p>
                                """

                                sucesso_email, msg_email = enviar_email_brevo(
                                    sol.get('email_pessoal', ''),
                                    sol.get('nome', ''),
                                    "✅ Seu cadastro no Permutatum foi aprovado!",
                                    html_aprovado
                                )

                                if sucesso_email:
                                    st.success(f"✅ Aprovado! Email de confirmação enviado para {sol.get('email_pessoal', '')}")
                                else:
                                    st.warning(f"✅ Aprovado! Mas houve erro ao enviar email: {msg_email}")

                                st.rerun()

                        with col_r:
                            if st.button("❌ Rejeitar", key=f"rejeitar_{sol.get('id')}", use_container_width=True):
                                supabase.table("solicitacoes").update({
                                    "status": "rejeitado",
                                    "admin_responsavel": admin.get('email', ''),
                                    "data_decisao": datetime.now().isoformat(),
                                    "observacao": observacao if observacao else "Cadastro não aprovado"
                                }).eq("id", sol.get('id')).execute()

                                # Enviar email de rejeição
                                html_rejeitado = f"""
                                <h2>Permutatum — Solicitação de Cadastro</h2>
                                <p>Olá, <strong>{sol.get('nome', '')}</strong>.</p>
                                <p>Infelizmente, sua solicitação de cadastro no Permutatum <strong>não foi aprovada</strong> neste momento.</p>
                                {"<p><strong>Motivo:</strong> " + observacao + "</p>" if observacao else ""}
                                <p>Se acredita que houve um engano, entre em contato conosco.</p>
                                <br>
                                <p><em>Permutatum — Sistema de Permutas da Magistratura</em></p>
                                """

                                enviar_email_brevo(
                                    sol.get('email_pessoal', ''),
                                    sol.get('nome', ''),
                                    "Permutatum — Solicitação de cadastro",
                                    html_rejeitado
                                )

                                st.warning("❌ Solicitação rejeitada.")
                                st.rerun()
            else:
                st.success("🎉 Nenhuma solicitação pendente!")

    # ══════════════════════════════════
    # ABA 2: HISTÓRICO
    # ══════════════════════════════════
    with tab2:
        st.subheader("📜 Histórico de Solicitações")

        supabase = init_supabase()
        if supabase:
            filtro_status = st.selectbox("Filtrar por status:", ["Todos", "aprovado", "rejeitado", "pendente"])

            if filtro_status == "Todos":
                historico = supabase.table("solicitacoes").select("*").order("created_at", desc=True).limit(100).execute()
            else:
                historico = supabase.table("solicitacoes").select("*").eq("status", filtro_status).order("created_at", desc=True).limit(100).execute()

            if historico.data:
                for sol in historico.data:
                    status_emoji = "✅" if sol.get('status') == 'aprovado' else "❌" if sol.get('status') == 'rejeitado' else "⏳"
                    st.markdown(
                        f"{status_emoji} **{sol.get('nome', '')}** — {sol.get('tj_origem', '')} — "
                        f"{sol.get('status', '')} — {sol.get('created_at', '')[:10]} — "
                        f"Admin: {sol.get('admin_responsavel', 'N/A')}"
                    )
            else:
                st.info("Nenhum registro encontrado.")

    # ══════════════════════════════════
    # ABA 3: TROCAR EMAIL DE MAGISTRADO
    # ══════════════════════════════════
    with tab3:
        st.subheader("🔄 Trocar Email de Magistrado")
        st.info("Use esta função para alterar o email de login de um magistrado (ex: de institucional para pessoal).")

        supabase = init_supabase()
        if supabase:
            busca_nome = st.text_input("Buscar magistrado por nome:", placeholder="Digite parte do nome...")

            if busca_nome and len(busca_nome) >= 3:
                resultados = supabase.table("magistrados").select("*").ilike("nome", f"%{busca_nome}%").eq("status", "ativo").execute()

                if resultados.data:
                    for mag in resultados.data:
                        with st.expander(f"👤 {mag.get('nome', '')} — {mag.get('origem', '')} — {mag.get('email', '')}"):
                            st.write(f"**Email atual:** {mag.get('email', '')}")
                            st.write(f"**Origem:** {mag.get('origem', '')}")
                            st.write(f"**Entrância:** {mag.get('entrancia', '')}")

                            novo_email = st.text_input(
                                "Novo email pessoal:",
                                key=f"novo_email_{mag.get('id')}",
                                placeholder="exemplo@gmail.com"
                            )

                            if st.button("💾 Atualizar email", key=f"atualizar_email_{mag.get('id')}"):
                                if novo_email and "@" in novo_email:
                                    # Atualizar email no banco
                                    supabase.table("magistrados").update({
                                        "email": novo_email.strip().lower()
                                    }).eq("id", mag.get('id')).execute()

                                    # Enviar confirmação para o novo email
                                    html_troca = f"""
                                    <h2>Permutatum — Email Atualizado</h2>
                                    <p>Olá, <strong>{mag.get('nome', '')}</strong>!</p>
                                    <p>Seu email de acesso ao Permutatum foi atualizado pelo administrador.</p>
                                    <p>A partir de agora, use <strong>{novo_email}</strong> para fazer login.</p>
                                    <p>👉 <a href="https://permutatum.streamlit.app/">https://permutatum.streamlit.app/</a></p>
                                    <br>
                                    <p><em>Permutatum — Sistema de Permutas da Magistratura</em></p>
                                    """

                                    sucesso_email, msg_email = enviar_email_brevo(
                                        novo_email.strip().lower(),
                                        mag.get('nome', ''),
                                        "Permutatum — Seu email foi atualizado",
                                        html_troca
                                    )

                                    if sucesso_email:
                                        st.success(f"✅ Email atualizado para {novo_email} e confirmação enviada!")
                                    else:
                                        st.success(f"✅ Email atualizado para {novo_email}!")
                                        st.warning(f"Aviso: não foi possível enviar email de confirmação: {msg_email}")

                                    st.rerun()
                                else:
                                    st.error("Email inválido.")
                else:
                    st.warning("Nenhum magistrado encontrado com esse nome.")

    # ══════════════════════════════════
    # ABA 4: GERENCIAR ADMINS (só super)
    # ══════════════════════════════════
    if is_super:
        with tab4:
            st.subheader("👥 Gerenciar Administradores")

            supabase = init_supabase()
            if supabase:
                # Listar admins atuais
                admins_lista = supabase.table("admins").select("*").order("created_at").execute()

                if admins_lista.data:
                    st.write("**Administradores ativos:**")
                    for adm in admins_lista.data:
                        status = "🟢" if adm.get('ativo') else "🔴"
                        nivel_txt = "👑 Super" if adm.get('nivel') == 'super' else "📋 Delegado"
                        st.markdown(f"{status} **{adm.get('nome', '')}** — {adm.get('email', '')} — {nivel_txt}")

                        # Não permitir desativar a si mesmo
                        if adm.get('email') != admin.get('email') and adm.get('nivel') != 'super':
                            if adm.get('ativo'):
                                if st.button(f"🔴 Desativar {adm.get('nome')}", key=f"desativar_{adm.get('id')}"):
                                    supabase.table("admins").update({"ativo": False}).eq("id", adm.get('id')).execute()
                                    st.rerun()
                            else:
                                if st.button(f"🟢 Reativar {adm.get('nome')}", key=f"reativar_{adm.get('id')}"):
                                    supabase.table("admins").update({"ativo": True}).eq("id", adm.get('id')).execute()
                                    st.rerun()

                st.markdown("---")
                st.write("**Adicionar novo administrador delegado:**")

                with st.form("add_admin"):
                    nome_novo_admin = st.text_input("Nome")
                    email_novo_admin = st.text_input("Email")
                    senha_novo_admin = st.text_input("Senha", type="password")
                    add_admin_btn = st.form_submit_button("➕ Adicionar Admin", use_container_width=True)

                if add_admin_btn:
                    if nome_novo_admin and email_novo_admin and senha_novo_admin:
                        # Verificar se já existe
                        existe = supabase.table("admins").select("id").eq("email", email_novo_admin.strip().lower()).execute()
                        if existe.data:
                            st.error("Este email já é de um administrador.")
                        else:
                            supabase.table("admins").insert({
                                "nome": nome_novo_admin.strip(),
                                "email": email_novo_admin.strip().lower(),
                                "senha_hash": senha_novo_admin,
                                "nivel": "delegado"
                            }).execute()
                            st.success(f"✅ Admin {nome_novo_admin} adicionado!")
                            st.rerun()
                    else:
                        st.error("Preencha todos os campos.")

    # ── Botão Sair ──
    st.markdown("---")
    if st.button("🚪 Sair do painel", use_container_width=True):
        st.session_state["admin_logado"] = None
        st.rerun()
