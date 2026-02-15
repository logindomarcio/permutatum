import streamlit as st
from supabase import create_client
import os
import re

# ── Configuração da página ──
st.set_page_config(page_title="Permutatum - Solicitar Cadastro", page_icon="📝", layout="centered")


# ── Função init_supabase ──
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


# ── Lista de tribunais (mesma do arquivo principal) ──
TRIBUNAIS = [
    "TJAC", "TJAL", "TJAP", "TJAM", "TJBA", "TJCE", "TJDFT", "TJES",
    "TJGO", "TJMA", "TJMT", "TJMS", "TJMG", "TJPA", "TJPB", "TJPR",
    "TJPE", "TJPI", "TJRJ", "TJRN", "TJRS", "TJRO", "TJRR", "TJSC",
    "TJSE", "TJSP", "TJTO"
]


def validar_email(email):
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None


# ── Página ──
st.title("📝 Solicitar Cadastro")

st.markdown("""
<div style="background-color: #e8f4f8; border-radius: 10px; padding: 16px 20px; margin-bottom: 20px; border-left: 5px solid #17a2b8;">
    <p style="margin: 0; font-size: 14px; color: #0c5460;">
        <strong>Como funciona:</strong><br>
        1️⃣ Preencha seus dados abaixo<br>
        2️⃣ Um administrador analisará sua solicitação<br>
        3️⃣ Após aprovação, você receberá um email de confirmação<br>
        4️⃣ Com o email confirmado, acesse o sistema pela página de Login e complete seu cadastro
    </p>
</div>
""", unsafe_allow_html=True)

# ── Verificar se já tem solicitação pendente ──
if "solicitacao_enviada" not in st.session_state:
    st.session_state["solicitacao_enviada"] = False

if st.session_state["solicitacao_enviada"]:
    st.success("✅ Sua solicitação foi enviada com sucesso!")
    st.info("📧 Você receberá um email no seu email pessoal quando o administrador aprovar seu cadastro. Isso pode levar algumas horas.")
    st.markdown("👉 Após receber a aprovação, acesse a página de **Login** para completar seu cadastro.")

    if st.button("📝 Fazer nova solicitação"):
        st.session_state["solicitacao_enviada"] = False
        st.rerun()
else:
    with st.form("form_solicitacao"):
        st.subheader("Dados para solicitação")

        nome = st.text_input("Nome completo *", placeholder="Seu nome completo")

        tj_origem = st.selectbox("Tribunal de Origem *", options=["Selecione..."] + TRIBUNAIS)

        email_pessoal = st.text_input(
            "Email pessoal *",
            placeholder="seu.email@gmail.com",
            help="Email pessoal (Gmail, Yahoo, Hotmail, etc.) — será usado para login e comunicações do sistema"
        )

        email_institucional = st.text_input(
            "Email institucional (opcional)",
            placeholder="seu.email@tjxx.jus.br",
            help="Email funcional do tribunal — usado apenas para validação pelo administrador"
        )

        st.markdown("---")
        st.markdown(
            """
            <div style="background-color: #fff3cd; border-radius: 8px; padding: 12px; border-left: 4px solid #ffc107; font-size: 13px; color: #856404;">
                <strong>⚠️ Importante:</strong> O email pessoal será seu email de acesso ao sistema.
                Certifique-se de informar um email que você acessa regularmente.
            </div>
            """,
            unsafe_allow_html=True,
        )

        submitted = st.form_submit_button("📨 Enviar Solicitação", use_container_width=True, type="primary")

    if submitted:
        # Validações
        erros = []
        if not nome or not nome.strip():
            erros.append("Nome é obrigatório")
        if tj_origem == "Selecione...":
            erros.append("Selecione o Tribunal de Origem")
        if not email_pessoal or not email_pessoal.strip():
            erros.append("Email pessoal é obrigatório")
        elif not validar_email(email_pessoal):
            erros.append("Email pessoal inválido")
        if email_institucional and not validar_email(email_institucional):
            erros.append("Email institucional inválido")

        if erros:
            for erro in erros:
                st.error(f"❌ {erro}")
        else:
            supabase = init_supabase()
            if supabase:
                email_limpo = email_pessoal.strip().lower()

                # Verificar se já tem cadastro ativo
                cadastro_existente = supabase.table("magistrados").select("id").eq("email", email_limpo).eq("status", "ativo").execute()
                if cadastro_existente.data and len(cadastro_existente.data) > 0:
                    st.error("⚠️ Este email já está cadastrado no sistema. Use a página de Login para acessar.")
                    st.stop()

                # Verificar se já tem solicitação pendente
                solicitacao_existente = supabase.table("solicitacoes").select("id").eq("email_pessoal", email_limpo).eq("status", "pendente").execute()
                if solicitacao_existente.data and len(solicitacao_existente.data) > 0:
                    st.warning("⏳ Você já tem uma solicitação pendente de análise. Aguarde a resposta do administrador.")
                    st.stop()

                # Inserir solicitação
                try:
                    response = supabase.table("solicitacoes").insert({
                        "nome": nome.strip(),
                        "tj_origem": tj_origem,
                        "email_pessoal": email_limpo,
                        "email_institucional": email_institucional.strip().lower() if email_institucional else None,
                        "tipo": "novo_cadastro",
                        "status": "pendente"
                    }).execute()

                    if response.data:
                        st.session_state["solicitacao_enviada"] = True
                        st.rerun()
                    else:
                        st.error("❌ Erro ao enviar solicitação. Tente novamente.")
                except Exception as e:
                    st.error(f"❌ Erro: {str(e)}")

# ── Rodapé ──
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #999; font-size: 12px;'><em>Permutatum — Sistema de Permutas da Magistratura</em></p>",
    unsafe_allow_html=True,
)
