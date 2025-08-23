import streamlit as st
from supabase import create_client, Client
import re

# Configuração da página
st.set_page_config(
    page_title="Cadastrar dados",
    page_icon="📝",
    layout="wide"
)

# Função para conectar ao Supabase
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao conectar com Supabase: {e}")
        return None

# Opções fixas dos campos
ENTRANCIAS = [
    "Juiz(a) Substituto(a)",
    "Inicial", 
    "Intermediária",
    "Final",
    "Única",
    "2º Grau"
]

TRIBUNAIS = [
    "TJAC", "TJAL", "TJAP", "TJAM", "TJBA", "TJCE", "TJDFT", "TJES",
    "TJGO", "TJMA", "TJMT", "TJMS", "TJMG", "TJPA", "TJPB", "TJPR", 
    "TJPE", "TJPI", "TJRJ", "TJRN", "TJRS", "TJRO", "TJRR", "TJSC",
    "TJSE", "TJSP", "TJTO"
]

# Função para validar email
def validar_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Função para inserir dados
def inserir_magistrado(dados):
    supabase = init_supabase()
    if not supabase:
        return False, "Erro na conexão com o banco de dados"
    
    try:
        response = supabase.table("magistrados").insert(dados).execute()
        return True, "Dados cadastrados com sucesso!"
    except Exception as e:
        if "duplicate key value" in str(e).lower():
            return False, "Este email já está cadastrado no sistema"
        return False, f"Erro ao cadastrar: {str(e)}"

# Interface principal
st.title("⚖️ Sistema de Permuta da Magistratura")
st.write("Esta aplicação é gratuita e colaborativa e, tendo em vista que o link para cadastro e acesso foi fornecido individualmente a cada magistrado(a), os dados aqui presentes limitam-se ao fim de facilitar encontros de permutantes. Esta aplicação é privada e a partir do cadastro dos dados, o(a) magistrado(a) assume a responsabilidade.")

st.subheader("Cadastro de Magistrado")

st.info("📝 Preencha seus dados para participar do sistema de permutas entre tribunais.")

# Formulário
with st.form("cadastro_magistrado", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        nome = st.text_input(
            "Nome Completo *",
            placeholder="Digite seu nome completo",
            help="Nome completo como aparece nos documentos oficiais"
        )
        
        entrancia = st.selectbox(
            "Entrância *",
            options=[""] + ENTRANCIAS,
            help="Selecione sua entrância atual"
        )
        
        origem = st.selectbox(
            "Tribunal de Origem *",
            options=[""] + TRIBUNAIS,
            help="Tribunal onde você atualmente trabalha"
        )
        
        telefone = st.text_input(
            "Telefone *",
            placeholder="(11) 99999-9999",
            help="Telefone para contato"
        )
    
    with col2:
        email = st.text_input(
            "E-mail *",
            placeholder="seu.email@exemplo.com",
            help="Email será usado para acessar suas informações no sistema"
        )
        
        destino_1 = st.selectbox(
            "1º Destino Desejado *",
            options=[""] + TRIBUNAIS,
            help="Tribunal de maior interesse para permuta"
        )
        
        destino_2 = st.selectbox(
            "2º Destino Desejado (Opcional)",
            options=[""] + TRIBUNAIS,
            help="Segunda opção de tribunal"
        )
        
        destino_3 = st.selectbox(
            "3º Destino Desejado (Opcional)",
            options=[""] + TRIBUNAIS,
            help="Terceira opção de tribunal"
        )
    
    st.markdown("---")
    st.caption("* Campos obrigatórios")
    
    submitted = st.form_submit_button("📤 Cadastrar Dados", use_container_width=True)
    
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
                "nome": nome.strip(),
                "entrancia": entrancia,
                "origem": origem,
                "destino_1": destino_1,
                "destino_2": destino_2 if destino_2 else None,
                "destino_3": destino_3 if destino_3 else None,
                "email": email.strip().lower(),
                "telefone": telefone.strip(),
                "status": "ativo"
            }
            
            # Inserir no banco
            sucesso, mensagem = inserir_magistrado(dados_magistrado)
            
            if sucesso:
                st.success(f"✅ {mensagem}")
                st.info("🔍 Para consultar as permutas disponíveis, use a página de consulta com seu e-mail cadastrado.")
                st.balloons()
            else:
                st.error(f"❌ {mensagem}")

# Informações do sistema
st.markdown("---")
with st.expander("ℹ️ Como funciona o sistema"):
    st.markdown("""
    ### Sistema de Permuta da Magistratura
    
    1. **Cadastro**: Preencha seus dados com tribunal atual e destinos desejados
    2. **Consulta**: Use seu email para acessar a página de consulta
    3. **Permutas**: Veja magistrados que querem vir para seu tribunal
    4. **Contato**: Entre em contato diretamente com interessados
    
    ### Privacidade
    - Seus dados só são visíveis para magistrados cadastrados
    - Acesso à consulta é feito através do email cadastrado
    - Sistema seguro e protegido
    """)

st.markdown("---")
st.caption("Sistema de Permuta da Magistratura Estadual - Versão com Supabase")