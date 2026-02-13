import streamlit as st
from supabase import create_client
from datetime import datetime

from utils.auth_supabase import (
    validar_email_magistrado,
    enviar_codigo_otp,
    verificar_codigo_otp,
    obter_usuario_logado,
)

# Configuração da página
st.set_page_config(
    page_title="Login - Permutatum",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="auto"
)

# Esconder navegação automática e usar links customizados
st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.page_link("app.py", label="🏠 Home")
st.sidebar.page_link("pages/1_Cadastre-se.py", label="📋 Cadastre-se")
st.sidebar.page_link("pages/2_Login_Acessar.py", label="🔑 Login / Acessar")


@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao conectar com Supabase: {e}")
        return None


# ─────────────────────────────────────
# Se já está autenticado, redirecionar
# ─────────────────────────────────────
usuario = obter_usuario_logado()
if usuario:
    st.success(f"✅ Você já está autenticado como **{usuario['email']}**")
    st.info("Redirecionando para o cadastro...")
    import time
    time.sleep(1)
    st.switch_page("app.py")

# ─────────────────────────────────────
# Interface de Login
# ─────────────────────────────────────
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(
        "logo.png",
        width=300,
    )

st.markdown("---")
st.title("🔐 Autenticação de Magistrado")
st.write(
    "Para realizar seu cadastro no sistema de permutas, "
    "é necessário verificar seu email funcional."
)
st.markdown("---")

supabase = init_supabase()

if not supabase:
    st.error("Erro na conexão com o banco de dados. Tente novamente mais tarde.")
    st.stop()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ETAPA 1: Enviar código OTP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if "otp_email_enviado" not in st.session_state:
    st.session_state["otp_email_enviado"] = False

if not st.session_state["otp_email_enviado"]:
    st.subheader("📧 Etapa 1: Informe seu email funcional")

    email = st.text_input(
        "Email funcional (@tjxx.jus.br)",
        placeholder="seu.nome@tjpr.jus.br",
        help="Use seu email funcional do tribunal (domínio @tjxx.jus.br)",
    )

    if st.button("📨 Enviar código de verificação", use_container_width=True, type="primary"):
        if not email.strip():
            st.error("❌ Por favor, digite seu email.")
        elif not validar_email_magistrado(email):
            st.error(
                "❌ Email inválido. Use seu email funcional do tribunal "
                "(exemplo: nome@tjpr.jus.br)."
            )
        else:
            with st.spinner("Enviando código de verificação..."):
                resultado = enviar_codigo_otp(supabase, email)

            if resultado["sucesso"]:
                st.session_state["otp_email_enviado"] = True
                st.session_state["otp_email"] = email.strip().lower()
                st.success(f"✅ {resultado['mensagem']}")
                st.rerun()
            else:
                st.error(f"❌ {resultado['mensagem']}")

    # Informações
    st.markdown("---")
    with st.expander("ℹ️ Dúvidas sobre o login"):
        st.markdown(
            """
            **Por que preciso verificar meu email?**
            A verificação garante que apenas magistrados(as) com email
            funcional dos tribunais estaduais possam se cadastrar.

            **Quais emails são aceitos?**
            Emails dos 27 Tribunais de Justiça estaduais
            (ex: @tjpr.jus.br, @tjsp.jus.br, @tjrj.jus.br, etc.)

            **Não recebi o código. O que fazer?**
            - Verifique a pasta de spam/lixo eletrônico
            - Aguarde até 5 minutos
            - Tente solicitar novamente
            """
        )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ETAPA 2: Verificar código OTP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
else:
    email_enviado = st.session_state.get("otp_email", "")

    st.subheader("🔢 Etapa 2: Digite o código de verificação")
    st.info(f"📧 Código enviado para: **{email_enviado}**")

    codigo = st.text_input(
        "Código de 6 dígitos",
        max_chars=6,
        placeholder="123456",
        help="Digite o código numérico que você recebeu por email",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Verificar código", use_container_width=True, type="primary"):
            if not codigo.strip():
                st.error("❌ Por favor, digite o código.")
            elif len(codigo.strip()) != 6 or not codigo.strip().isdigit():
                st.error("❌ O código deve ter exatamente 6 dígitos numéricos.")
            else:
                with st.spinner("Verificando código..."):
                    resultado = verificar_codigo_otp(supabase, email_enviado, codigo)

                if resultado["sucesso"]:
                    st.success(f"✅ {resultado['mensagem']}")
                    st.info("Redirecionando para o cadastro...")
                    import time
                    time.sleep(1.5)
                    st.switch_page("app.py")
                else:
                    st.error(f"❌ {resultado['mensagem']}")

    with col2:
        if st.button("🔄 Reenviar código", use_container_width=True):
            with st.spinner("Reenviando código..."):
                resultado = enviar_codigo_otp(supabase, email_enviado)
            if resultado["sucesso"]:
                st.success("✅ Novo código enviado! Verifique seu email.")
            else:
                st.error(f"❌ {resultado['mensagem']}")

    st.markdown("---")

    if st.button("◀️ Voltar e usar outro email"):
        st.session_state["otp_email_enviado"] = False
        st.session_state.pop("otp_email", None)
        st.rerun()

# Rodapé
st.markdown("---")
st.markdown(
    f"""
    <div style="text-align: center; padding: 20px 0;">
        <p style="margin: 5px 0; font-style: italic; font-family: 'Times New Roman', serif; font-size: 16px;">
            <em>Permutatum</em>
        </p>
        <p style="margin: 5px 0; font-size: 13px; color: #888;">
            Castro/PR — {datetime.now().year}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
