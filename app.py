import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import re

from utils.auth_supabase import obter_usuario_logado, fazer_logout

# Configuração da página
st.set_page_config(
    page_title="Home",
    page_icon="🏠",
    layout="wide",
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


# Função para conectar ao Supabase
def init_supabase():
    try:
        import os
        # Tentar st.secrets primeiro (Streamlit Cloud)
        try:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
        except:
            # Fallback para variáveis de ambiente (Render, etc.)
            url = os.environ.get("SUPABASE_URL", "")
            key = os.environ.get("SUPABASE_KEY", "")

        if not url or not key:
            st.error("Credenciais do Supabase não encontradas.")
            return None

        supabase = create_client(url, key)
        return supabase
    except Exception as e:
        st.error(f"Erro ao conectar com Supabase: {e}")
        return None


# ─────────────────────────────────────────────
# Verificar autenticação
# ─────────────────────────────────────────────
supabase = init_supabase()
usuario = obter_usuario_logado()

if not usuario:
    # Logo centralizada
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(
            "logo.png",
            width=350,
        )
    st.markdown("---")

    st.warning("⚠️ Acesso Restrito — Apenas Novos Cadastros")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📋 Já possui cadastro?")
        st.info(
            "Use a página **🔍 Buscar Permutas** para "
            "acessar seus dados e encontrar permutas disponíveis."
        )
        if st.button("🔍 Ir para Buscar Permutas", use_container_width=True):
            st.switch_page("pages/2_Login_Acessar.py")

    with col2:
        st.markdown("### 🔐 Primeiro acesso?")
        st.info(
            "Faça login com seu email funcional (@tjxx.jus.br) "
            "para realizar seu primeiro cadastro no sistema."
        )
        if st.button(
            "📋 Iniciar cadastro", use_container_width=True, type="primary"
        ):
            st.switch_page("pages/1_Cadastre-se.py")

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

    st.stop()

# ─────────────────────────────────────────────
# Usuário autenticado — exibir página completa
# ─────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(
        "logo.png",
        width=350,
    )
st.markdown("---")

st.success(f"✅ Autenticado como: **{usuario['email']}**")
st.markdown("---")

# Opções fixas dos campos
ENTRANCIAS = [
    "Juiz(a) Substituto(a)",
    "Inicial",
    "Intermediária",
    "Final",
    "Única",
    "2º Grau",
]

TRIBUNAIS = [
    "TJAC", "TJAL", "TJAP", "TJAM", "TJBA", "TJCE", "TJDFT", "TJES",
    "TJGO", "TJMA", "TJMT", "TJMS", "TJMG", "TJPA", "TJPB", "TJPR",
    "TJPE", "TJPI", "TJRJ", "TJRN", "TJRS", "TJRO", "TJRR", "TJSC",
    "TJSE", "TJSP", "TJTO",
]


# Função para validar email
def validar_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


# Função para inserir dados
def inserir_magistrado(dados):
    supabase = init_supabase()
    if not supabase:
        return False, "Erro na conexão com o banco de dados"

    try:
        # Verificar se email já está cadastrado
        email_check = supabase.table("magistrados").select("id").eq("email", dados.get('email', '')).eq("status", "ativo").execute()
        if email_check.data and len(email_check.data) > 0:
            return False, "⚠️ Este e-mail já está cadastrado no sistema. Use a página de Login para acessar seus dados, ou edite seu cadastro em 'Gerenciar meus dados'."

        response = supabase.table("magistrados").insert(dados).execute()
        return True, "Dados cadastrados com sucesso!"
    except Exception as e:
        if "duplicate key value" in str(e).lower():
            return False, "Este email já está cadastrado no sistema"
        return False, f"Erro ao cadastrar: {str(e)}"


# Interface principal
st.title("⚖️ Sistema de Permuta da Magistratura")
st.write(
    "Esta aplicação é gratuita e colaborativa e, tendo em vista que o link "
    "para cadastro e acesso foi fornecido individualmente a cada magistrado(a), "
    "os dados aqui presentes limitam-se ao fim de facilitar encontros de "
    "permutantes. Esta aplicação é privada e a partir do cadastro dos dados, "
    "o(a) magistrado(a) assume a responsabilidade."
)

st.subheader("Cadastro de Magistrado")

st.info("📝 Preencha seus dados para participar do sistema de permutas entre tribunais.")

# Formulário
with st.form("cadastro_magistrado", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        nome = st.text_input(
            "Nome Completo *",
            placeholder="Digite seu nome completo",
            help="Nome completo como aparece nos documentos oficiais",
        )

        entrancia = st.selectbox(
            "Entrância *",
            options=[""] + ENTRANCIAS,
            help="Selecione sua entrância atual",
        )

        origem = st.selectbox(
            "Tribunal de Origem *",
            options=[""] + TRIBUNAIS,
            help="Tribunal onde você atualmente trabalha",
        )

        telefone = st.text_input(
            "Telefone *",
            placeholder="(11) 99999-9999",
            help="Telefone para contato",
        )

        telefone_visivel = st.checkbox(
            "Tornar meu telefone visível para outros magistrados",
            value=True,
            help="Se desmarcado, apenas seu email será exibido como forma de contato",
        )

    with col2:
        email = st.text_input(
            "E-mail *",
            placeholder="seu.email@exemplo.com",
            help="Email será usado para acessar suas informações no sistema",
        )

        destino_1 = st.selectbox(
            "1º Destino Desejado *",
            options=[""] + TRIBUNAIS,
            help="Tribunal de maior interesse para permuta",
        )

        destino_2 = st.selectbox(
            "2º Destino Desejado (Opcional)",
            options=[""] + TRIBUNAIS,
            help="Segunda opção de tribunal",
        )

        destino_3 = st.selectbox(
            "3º Destino Desejado (Opcional)",
            options=[""] + TRIBUNAIS,
            help="Terceira opção de tribunal",
        )

    st.markdown("---")
    st.caption("* Campos obrigatórios")

    submitted = st.form_submit_button(
        "📤 Cadastrar Dados", use_container_width=True
    )

    if submitted:
        # Validações
        erros = []

        if not nome.strip():
            erros.append("Nome é obrigatório")

        if not entrancia:
            erros.append("Entrância é obrigatória")

        if not origem:
            erros.append("Tribunal de origem é obrigatório")

        if not destino_1:
            erros.append("Primeiro destino é obrigatório")

        if not email.strip():
            erros.append("E-mail é obrigatório")
        elif not validar_email(email):
            erros.append("E-mail inválido")

        if not telefone.strip():
            erros.append("Telefone é obrigatório")

        if origem == destino_1:
            erros.append("Destino não pode ser igual ao tribunal de origem")

        if destino_2 and destino_2 == origem:
            erros.append("2º destino não pode ser igual ao tribunal de origem")

        if destino_3 and destino_3 == origem:
            erros.append("3º destino não pode ser igual ao tribunal de origem")

        if destino_2 and destino_1 == destino_2:
            erros.append("2º destino deve ser diferente do 1º destino")

        if destino_3 and (destino_1 == destino_3 or destino_2 == destino_3):
            erros.append("3º destino deve ser diferente dos anteriores")

        if erros:
            for erro in erros:
                st.error(f"❌ {erro}")
        else:
            # Preparar dados para inserção
            dados_magistrado = {
                "user_id": usuario["user_id"],
                "nome": nome.strip(),
                "entrancia": entrancia,
                "origem": origem,
                "destino_1": destino_1,
                "destino_2": destino_2 if destino_2 else None,
                "destino_3": destino_3 if destino_3 else None,
                "email": email.strip().lower(),
                "telefone": telefone.strip(),
                "telefone_visivel": telefone_visivel,
                "status": "ativo",
            }

            # Inserir no banco
            sucesso, mensagem = inserir_magistrado(dados_magistrado)

            if sucesso:
                st.success(f"✅ {mensagem}")
                st.info(
                    "🔍 Para consultar as permutas disponíveis, "
                    "use a página de consulta com seu e-mail cadastrado."
                )
                st.balloons()

                # ── Gerar notificações de match ──
                try:
                    # Buscar todos os magistrados ativos
                    todos = supabase.table("magistrados").select("*").eq("status", "ativo").execute()
                    if todos.data:
                        novo_origem = dados_magistrado.get('origem', '')
                        novo_destino_1 = dados_magistrado.get('destino_1', '')
                        novo_email = dados_magistrado.get('email', '')
                        novo_nome = dados_magistrado.get('nome', '')

                        for mag in todos.data:
                            if mag.get('email', '').lower() == novo_email.lower():
                                continue  # Pular o próprio usuário

                            mag_origem = mag.get('origem', '')
                            mag_destino_1 = mag.get('destino_1', '')

                            # Verificar permuta direta via destino_1
                            if mag_origem == novo_destino_1 and mag_destino_1 == novo_origem:
                                # Match! Notificar o magistrado existente
                                supabase.table("notificacoes").insert({
                                    "email_destino": mag.get('email', ''),
                                    "tipo": "permuta_direta",
                                    "mensagem": f"Novo match de permuta direta! {novo_nome} ({novo_origem}) quer ir para {novo_destino_1}.",
                                    "detalhes": f"Confira na aba 'Busca de Permuta' selecionando {mag_origem} → {novo_origem}."
                                }).execute()

                                # Notificar também o novo cadastrado
                                supabase.table("notificacoes").insert({
                                    "email_destino": novo_email,
                                    "tipo": "permuta_direta",
                                    "mensagem": f"Boa notícia! {mag.get('nome', '')} ({mag_origem}) quer ir para {mag_destino_1} — permuta direta possível!",
                                    "detalhes": f"Confira na aba 'Busca de Permuta' selecionando {novo_origem} → {novo_destino_1}."
                                }).execute()
                except Exception as e:
                    pass  # Não bloquear o cadastro por erro de notificação
            else:
                st.error(f"❌ {mensagem}")

# Informações do sistema
st.markdown("---")
with st.expander("ℹ️ Como funciona o sistema"):
    st.markdown(
        """
    ### Sistema de Permuta da Magistratura

    1. **Cadastro**: Preencha seus dados com tribunal atual e destinos desejados
    2. **Consulta**: Use seu email para acessar a página de consulta
    3. **Permutas**: Veja magistrados que querem vir para seu tribunal
    4. **Contato**: Entre em contato diretamente com interessados

    ### Privacidade
    - Seus dados só são visíveis para magistrados cadastrados
    - Acesso à consulta é feito através do email cadastrado
    - Sistema seguro e protegido
    """
    )

st.markdown("---")

# Rodapé
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
