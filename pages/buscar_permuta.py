import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import re

# Configuração da página
st.set_page_config(
    page_title="Buscar permuta",
    page_icon="🔍",
    layout="wide"
)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("https://raw.githubusercontent.com/logindomarcio/permutatum/main/logo.png", width=350)
st.markdown("---")
# Listas fixas
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

# Função para carregar todos os dados
@st.cache_data(ttl=300)
def carregar_dados():
    supabase = init_supabase()
    if not supabase:
        return []
    
    try:
        response = supabase.table("magistrados").select("*").eq("status", "ativo").execute()
        return response.data
    except:
        return []

# Função para verificar email
def verificar_email(email):
    dados = carregar_dados()
    for magistrado in dados:
        if magistrado.get('email', '').lower() == email.lower():
            return magistrado
    return None

# Função para validar email
def validar_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Função para atualizar magistrado
def atualizar_magistrado(id_magistrado, dados_novos):
    supabase = init_supabase()
    if not supabase:
        return False, "Erro na conexão"
    
    try:
        # Primeiro, verificar se o registro ainda existe
        verificacao = supabase.table("magistrados").select("*").eq("id", id_magistrado).execute()
        
        if not verificacao.data:
            return False, "Registro não encontrado. Faça logout e login novamente."
        
        # Se existe, fazer a atualização
        response = supabase.table("magistrados").update(dados_novos).eq("id", id_magistrado).execute()
        
        if response.data:
            return True, "Dados atualizados com sucesso!"
        else:
            return False, "Falha na atualização. Tente novamente."
            
    except Exception as e:
        return False, f"Erro ao atualizar: {str(e)}"
# Função para excluir magistrado
def excluir_magistrado(id_magistrado):
    supabase = init_supabase()
    if not supabase:
        return False, "Erro na conexão"
    
    try:
        response = supabase.table("magistrados").delete().eq("id", id_magistrado).execute()
        return True, "Cadastro excluído com sucesso!"
    except Exception as e:
        return False, f"Erro ao excluir: {str(e)}"

# Função para busca livre inteligente (detecta permutas e triangulações)
def busca_livre_inteligente(origem_filtro, destino_filtro, dados):
    permutas_diretas = []
    triangulacoes = []
    
    # Filtrar magistrados pelos critérios
    magistrados_origem = []
    magistrados_destino = []
    
    if origem_filtro:
        magistrados_origem = [m for m in dados if m.get('origem') == origem_filtro]
    
    if destino_filtro:
        for magistrado in dados:
            destinos = [magistrado.get(f'destino_{i}') for i in range(1, 4) if magistrado.get(f'destino_{i}')]
            if destino_filtro in destinos:
                magistrados_destino.append(magistrado)
    
    # Se ambos filtros foram aplicados, buscar permutas diretas
    if origem_filtro and destino_filtro:
        for mag_origem in magistrados_origem:
            destinos_mag = [mag_origem.get(f'destino_{i}') for i in range(1, 4) if mag_origem.get(f'destino_{i}')]
            
            if destino_filtro in destinos_mag:
                # Buscar magistrados no destino que querem vir para origem
                for mag_destino in dados:
                    if mag_destino.get('origem') == destino_filtro:
                        destinos_mag_destino = [mag_destino.get(f'destino_{i}') for i in range(1, 4) if mag_destino.get(f'destino_{i}')]
                        
                        if origem_filtro in destinos_mag_destino:
                            # Permuta direta encontrada
                            prioridade_1 = None
                            prioridade_2 = None
                            
                            if mag_origem.get('destino_1') == destino_filtro:
                                prioridade_1 = 1
                            elif mag_origem.get('destino_2') == destino_filtro:
                                prioridade_1 = 2
                            elif mag_origem.get('destino_3') == destino_filtro:
                                prioridade_1 = 3
                            
                            if mag_destino.get('destino_1') == origem_filtro:
                                prioridade_2 = 1
                            elif mag_destino.get('destino_2') == origem_filtro:
                                prioridade_2 = 2
                            elif mag_destino.get('destino_3') == origem_filtro:
                                prioridade_2 = 3
                            
                            permutas_diretas.append({
                                'magistrado_1': mag_origem,
                                'magistrado_2': mag_destino,
                                'prioridade_1': prioridade_1,
                                'prioridade_2': prioridade_2,
                                'sequencia': f"{origem_filtro} ↔ {destino_filtro}"
                            })
        
        # Buscar triangulações envolvendo os tribunais filtrados
        for mag_origem in magistrados_origem:
            destinos_mag_origem = [mag_origem.get(f'destino_{i}') for i in range(1, 4) if mag_origem.get(f'destino_{i}')]
            
            for destino_intermediario in destinos_mag_origem:
                if destino_intermediario == destino_filtro:
                    continue  # Pular permutas diretas já detectadas
                
                # Buscar magistrado no tribunal intermediário
                for mag_intermediario in dados:
                    if mag_intermediario.get('origem') == destino_intermediario:
                        destinos_mag_inter = [mag_intermediario.get(f'destino_{i}') for i in range(1, 4) if mag_intermediario.get(f'destino_{i}')]
                        
                        if destino_filtro in destinos_mag_inter:
                            # Buscar magistrado no destino final que quer voltar à origem
                            for mag_destino_final in dados:
                                if mag_destino_final.get('origem') == destino_filtro:
                                    destinos_final = [mag_destino_final.get(f'destino_{i}') for i in range(1, 4) if mag_destino_final.get(f'destino_{i}')]
                                    
                                    if origem_filtro in destinos_final:
                                        triangulacoes.append({
                                            'magistrados': [mag_origem, mag_intermediario, mag_destino_final],
                                            'sequencia': f"{origem_filtro} → {destino_intermediario} → {destino_filtro} → {origem_filtro}",
                                            'tribunais': [origem_filtro, destino_intermediario, destino_filtro]
                                        })
    
    return permutas_diretas, triangulacoes

# Função para atualizar dados
def atualizar_dados():
    st.cache_data.clear()
    st.success("Base de dados atualizada!")
    st.rerun()

# Função para calcular estatísticas
def calcular_estatisticas(dados):
    if not dados:
        return {}, {}, 0, 0
    
    destinos = []
    origens = []
    tribunais_unicos = set()
    
    for magistrado in dados:
        origem = magistrado.get('origem')
        if origem:
            origens.append(origem)
            tribunais_unicos.add(origem)
        
        for destino_col in ['destino_1', 'destino_2', 'destino_3']:
            destino = magistrado.get(destino_col)
            if destino:
                destinos.append(destino)
                tribunais_unicos.add(destino)
    
    destinos_contador = Counter(destinos)
    origens_contador = Counter(origens)
    
    return destinos_contador, origens_contador, len(dados), len(tribunais_unicos)

# Função para gerar gráficos
def gerar_graficos(dados):
    destinos_contador, origens_contador, total_juizes, total_tribunais = calcular_estatisticas(dados)
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Métricas principais
    with col1:
        st.metric("Juízes(as) Cadastrados(as)", total_juizes)
    
    with col2:
        st.metric("Tribunais Envolvidos", total_tribunais)
    
    with col3:
        if destinos_contador:
            mais_procurado = destinos_contador.most_common(1)[0]
            st.metric("Tribunal Mais Procurado", mais_procurado[0], f"{mais_procurado[1]} interessados")
    
    with col4:
        if origens_contador:
            mais_exportador = origens_contador.most_common(1)[0]
            st.metric("Maior Exportador", mais_exportador[0], f"{mais_exportador[1]} magistrados")
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        if destinos_contador:
            st.subheader("🎯 Tribunais Mais Procurados")
            top_destinos = dict(destinos_contador.most_common(10))
            fig = px.bar(x=list(top_destinos.keys()), y=list(top_destinos.values()),
                        color=list(top_destinos.values()), 
                        color_continuous_scale='Viridis')
            fig.update_layout(showlegend=False, xaxis_title="Tribunais", yaxis_title="Interessados")
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if origens_contador:
            st.subheader("📤 Tribunais Mais Exportadores")
            top_origens = dict(origens_contador.most_common(10))
            fig = px.bar(x=list(top_origens.keys()), y=list(top_origens.values()),
                        color=list(top_origens.values()),
                        color_continuous_scale='Plasma')
            fig.update_layout(showlegend=False, xaxis_title="Tribunais", yaxis_title="Magistrados")
            st.plotly_chart(fig, use_container_width=True)

# Função para buscar interessados no tribunal do usuário
def buscar_interessados(tribunal_usuario, dados):
    interessados = []
    
    for magistrado in dados:
        if magistrado.get('origem') == tribunal_usuario:
            continue  # Não mostrar o próprio usuário
        
        prioridade = None
        if magistrado.get('destino_1') == tribunal_usuario:
            prioridade = 1
        elif magistrado.get('destino_2') == tribunal_usuario:
            prioridade = 2
        elif magistrado.get('destino_3') == tribunal_usuario:
            prioridade = 3
        
        if prioridade:
            interessados.append({
                'magistrado': magistrado,
                'prioridade': prioridade
            })
    
    return sorted(interessados, key=lambda x: x['prioridade'])

# Função para buscar destinos disponíveis
def buscar_destinos_disponiveis(destinos_usuario, dados):
    disponveis = []
    
    for magistrado in dados:
        origem = magistrado.get('origem')
        if origem in destinos_usuario:
            disponveis.append(magistrado)
    
    return disponveis

# Função para detectar triangulações
def detectar_triangulacoes(usuario, dados):
    triangulacoes = []
    origem_usuario = usuario.get('origem')
    destinos_usuario = [usuario.get(f'destino_{i}') for i in range(1, 4) if usuario.get(f'destino_{i}')]
    
    for destino_usuario in destinos_usuario:
        # Busca magistrados no destino desejado pelo usuário
        for mag_destino in dados:
            if mag_destino.get('origem') != destino_usuario:
                continue
            
            destinos_mag = [mag_destino.get(f'destino_{i}') for i in range(1, 4) if mag_destino.get(f'destino_{i}')]
            
            for destino_mag in destinos_mag:
                if destino_mag == origem_usuario:
                    # Triangulação de 2 (permuta direta)
                    triangulacoes.append({
                        'tipo': 'direta',
                        'magistrados': [usuario, mag_destino],
                        'sequencia': f"{origem_usuario} ↔ {destino_usuario}"
                    })
                else:
                    # Busca terceiro magistrado para triangulação de 3
                    for mag_terceiro in dados:
                        if mag_terceiro.get('origem') != destino_mag:
                            continue
                        
                        destinos_terceiro = [mag_terceiro.get(f'destino_{i}') for i in range(1, 4) if mag_terceiro.get(f'destino_{i}')]
                        
                        if origem_usuario in destinos_terceiro:
                            triangulacoes.append({
                                'tipo': 'triangular',
                                'magistrados': [usuario, mag_destino, mag_terceiro],
                                'sequencia': f"{origem_usuario} → {destino_usuario} → {destino_mag} → {origem_usuario}"
                            })
    
    return triangulacoes

# Função para exibir magistrado (SEM EMAIL por segurança)
def exibir_magistrado(magistrado, prioridade=None):
    col1, col2, col3 = st.columns([3, 2, 1])
    
    with col1:
        st.write(f"**{magistrado.get('nome', 'N/A')}**")
        st.write(f"📍 {magistrado.get('origem', 'N/A')} - {magistrado.get('entrancia', 'N/A')}")
    
    with col2:
        st.write(f"📞 {magistrado.get('telefone', 'N/A')}")
        # Email removido por segurança
    
    with col3:
        if prioridade:
            cores = {1: "🟢", 2: "🟡", 3: "🔵"}
            st.write(f"{cores.get(prioridade, '⚪')} Prioridade {prioridade}")

# Interface principal
st.title("🔍 Busca de Permutas")
st.write("Esta aplicação é gratuita e colaborativa e, tendo em vista que o link para cadastro e acesso foi fornecido individualmente a cada magistrado(a), os dados aqui presentes limitam-se ao fim de facilitar encontros de permutantes. Esta aplicação é privada e a partir do cadastro dos dados, o(a) magistrado(a) assume a responsabilidade.")

# Botão de atualizar dados
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    if st.button("🔄 Atualizar base de dados agora"):
        atualizar_dados()

# Autenticação
if 'usuario_autenticado' not in st.session_state:
    st.session_state.usuario_autenticado = None

if not st.session_state.usuario_autenticado:
    st.write("Digite seu e-mail para acessar a aplicação:")
    
    email_input = st.text_input("E-mail:", placeholder="seu.email@exemplo.com")
    
    if email_input:
        usuario = verificar_email(email_input)
        if usuario:
            st.session_state.usuario_autenticado = usuario
            st.success(f"Bem-vindo(a), {usuario.get('nome', 'Usuário')}!")
            st.rerun()
        else:
            st.warning("⚠️ Acesso restrito. Seu e-mail não está cadastrado na base de dados.")
            if st.button("📝 Ir para página de cadastro"):
                st.switch_page("app.py")

else:
    # Usuário autenticado - mostrar sistema completo
    usuario = st.session_state.usuario_autenticado
    dados = carregar_dados()
    
    # Gráficos e estatísticas
    gerar_graficos(dados)
    
    st.markdown("---")
    
    # Sistema de tabs para diferentes consultas
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 Interessados no meu tribunal", 
        "📍 Tribunais que me interessam", 
        "🔄 Triangulações disponíveis",
        "🔍 Busca livre",
        "⚙️ Gerenciar meus dados"
    ])
    
    with tab1:
        st.subheader(f"Magistrados interessados em vir para o {usuario.get('origem')}")
        
        interessados = buscar_interessados(usuario.get('origem'), dados)
        
        if interessados:
            for item in interessados:
                with st.container():
                    exibir_magistrado(item['magistrado'], item['prioridade'])
                    st.markdown("---")
        else:
            st.info("Nenhum magistrado demonstrou interesse em seu tribunal ainda.")
    
    with tab2:
        st.subheader("Magistrados nos tribunais de seu interesse")
        
        destinos_usuario = [usuario.get(f'destino_{i}') for i in range(1, 4) if usuario.get(f'destino_{i}')]
        
        if destinos_usuario:
            disponveis = buscar_destinos_disponiveis(destinos_usuario, dados)
            
            if disponveis:
                for tribunal in destinos_usuario:
                    magistrados_tribunal = [m for m in disponveis if m.get('origem') == tribunal]
                    if magistrados_tribunal:
                        st.write(f"**{tribunal}** ({len(magistrados_tribunal)} magistrados)")
                        
                        for magistrado in magistrados_tribunal:
                            with st.container():
                                exibir_magistrado(magistrado)
                                st.markdown("---")
            else:
                st.info("Nenhum magistrado encontrado nos tribunais de seu interesse.")
        else:
            st.info("Você não cadastrou tribunais de destino.")
    
    with tab3:
        st.subheader("Oportunidades de Triangulação")
        st.info("💡 Triangulações permitem permutas indiretas entre 2 ou mais magistrados")
        
        triangulacoes = detectar_triangulacoes(usuario, dados)
        
        if triangulacoes:
            for i, triangulacao in enumerate(triangulacoes, 1):
                with st.expander(f"Triangulação {i}: {triangulacao['sequencia']}"):
                    
                    if triangulacao['tipo'] == 'direta':
                        st.success("🔄 **Permuta Direta Possível**")
                        st.write("Vocês dois podem trocar de tribunal diretamente!")
                    else:
                        st.info("🔺 **Triangulação de 3 Magistrados**")
                        st.write("Operação coordenada entre três magistrados:")
                    
                    st.write(f"**Sequência:** {triangulacao['sequencia']}")
                    
                    st.write("**Magistrados envolvidos:**")
                    for mag in triangulacao['magistrados']:
                        if mag != usuario:  # Não mostrar o próprio usuário
                            exibir_magistrado(mag)
        else:
            st.info("Nenhuma triangulação detectada no momento. Tente novamente após mais cadastros.")
    
    with tab4:
        st.subheader("🔍 Busca Livre Inteligente")
        st.info("Encontre automaticamente permutas diretas e triangulações entre tribunais específicos")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            origem_filtro = st.selectbox(
                "Tribunal de Origem:",
                options=[""] + TRIBUNAIS,
                help="Selecione um tribunal de origem"
            )
        
        with col2:
            destino_filtro = st.selectbox(
                "Tribunal de Destino:",
                options=[""] + TRIBUNAIS,
                help="Selecione um tribunal de destino"
            )
        
        with col3:
            buscar_clicked = st.button("🔍 Buscar Oportunidades", use_container_width=True)
        
        if buscar_clicked:
            if not origem_filtro or not destino_filtro:
                st.warning("Selecione ambos os tribunais para realizar a busca inteligente")
            elif origem_filtro == destino_filtro:
                st.error("Tribunal de origem e destino devem ser diferentes")
            else:
                permutas_diretas, triangulacoes = busca_livre_inteligente(origem_filtro, destino_filtro, dados)
                
                # Mostrar resultados
                col_resultado1, col_resultado2 = st.columns(2)
                
                with col_resultado1:
                    st.subheader("🔄 Permutas Diretas Encontradas")
                    if permutas_diretas:
                        st.success(f"Encontradas {len(permutas_diretas)} permutas diretas possíveis!")
                        
                        for i, permuta in enumerate(permutas_diretas, 1):
                            with st.expander(f"Permuta {i}: {permuta['sequencia']}"):
                                st.success("✅ **PERMUTA DIRETA POSSÍVEL**")
                                st.write("Estes dois magistrados podem trocar de tribunal diretamente:")
                                
                                st.write("**Magistrado 1:**")
                                exibir_magistrado(permuta['magistrado_1'], permuta['prioridade_1'])
                                
                                st.write("**Magistrado 2:**")
                                exibir_magistrado(permuta['magistrado_2'], permuta['prioridade_2'])
                                
                                # Análise de compatibilidade
                                score = 0
                                if permuta['prioridade_1'] == 1:
                                    score += 3
                                elif permuta['prioridade_1'] == 2:
                                    score += 2
                                elif permuta['prioridade_1'] == 3:
                                    score += 1
                                
                                if permuta['prioridade_2'] == 1:
                                    score += 3
                                elif permuta['prioridade_2'] == 2:
                                    score += 2
                                elif permuta['prioridade_2'] == 3:
                                    score += 1
                                
                                if score >= 5:
                                    st.success("🌟 **ALTA COMPATIBILIDADE** - Ambos têm forte interesse")
                                elif score >= 3:
                                    st.info("⭐ **MÉDIA COMPATIBILIDADE** - Interesse moderado")
                                else:
                                    st.warning("💫 **BAIXA COMPATIBILIDADE** - Interesse limitado")
                    else:
                        st.info("Nenhuma permuta direta encontrada entre estes tribunais")
                
                with col_resultado2:
                    st.subheader("🔺 Triangulações Encontradas")
                    if triangulacoes:
                        st.success(f"Encontradas {len(triangulacoes)} triangulações possíveis!")
                        
                        for i, triangulacao in enumerate(triangulacoes, 1):
                            with st.expander(f"Triangulação {i}: {triangulacao['sequencia']}"):
                                st.info("🔺 **TRIANGULAÇÃO DE 3 MAGISTRADOS**")
                                st.write("Operação coordenada entre três magistrados:")
                                
                                st.write(f"**Sequência:** {triangulacao['sequencia']}")
                                
                                for j, magistrado in enumerate(triangulacao['magistrados'], 1):
                                    st.write(f"**Magistrado {j}:**")
                                    exibir_magistrado(magistrado)
                                    if j < len(triangulacao['magistrados']):
                                        st.write("⬇️")
                                
                                st.success("💡 **Coordenação necessária:** Todos os três magistrados precisam concordar simultaneamente")
                    else:
                        st.info("Nenhuma triangulação encontrada entre estes tribunais")
                
                # Resumo geral
                total_oportunidades = len(permutas_diretas) + len(triangulacoes)
                if total_oportunidades > 0:
                    st.markdown("---")
                    st.success(f"🎯 **RESUMO:** {total_oportunidades} oportunidades encontradas entre {origem_filtro} e {destino_filtro}")
                else:
                    st.markdown("---")
                    st.warning(f"😔 Nenhuma oportunidade de permuta encontrada entre {origem_filtro} e {destino_filtro} no momento")
    
    with tab5:
        st.subheader("⚙️ Gerenciar Meus Dados")
        
        opcao = st.radio(
            "Escolha uma opção:",
            ["✏️ Editar meus dados", "🗑️ Excluir meu cadastro"],
            horizontal=True
        )
        
        if opcao == "✏️ Editar meus dados":
            st.info("Edite seus dados abaixo e clique em Salvar Alterações")
            
            with st.form("editar_dados"):
                col1, col2 = st.columns(2)
                
                with col1:
                    nome_novo = st.text_input("Nome Completo *", value=usuario.get('nome', ''))
                    entrancia_nova = st.selectbox(
                        "Entrância *", 
                        options=ENTRANCIAS,
                        index=ENTRANCIAS.index(usuario.get('entrancia', ENTRANCIAS[0])) if usuario.get('entrancia') in ENTRANCIAS else 0
                    )
                    origem_nova = st.selectbox(
                        "Tribunal de Origem *",
                        options=TRIBUNAIS,
                        index=TRIBUNAIS.index(usuario.get('origem', TRIBUNAIS[0])) if usuario.get('origem') in TRIBUNAIS else 0
                    )
                    telefone_novo = st.text_input("Telefone *", value=usuario.get('telefone', ''))
                
                with col2:
                    email_novo = st.text_input("E-mail *", value=usuario.get('email', ''))
                    
                    destino_1_idx = TRIBUNAIS.index(usuario.get('destino_1')) if usuario.get('destino_1') in TRIBUNAIS else 0
                    destino_1_novo = st.selectbox("1º Destino *", options=TRIBUNAIS, index=destino_1_idx)
                    
                    destino_2_opcoes = [""] + TRIBUNAIS
                    destino_2_idx = destino_2_opcoes.index(usuario.get('destino_2', '')) if usuario.get('destino_2') in destino_2_opcoes else 0
                    destino_2_novo = st.selectbox("2º Destino (Opcional)", options=destino_2_opcoes, index=destino_2_idx)
                    
                    destino_3_opcoes = [""] + TRIBUNAIS
                    destino_3_idx = destino_3_opcoes.index(usuario.get('destino_3', '')) if usuario.get('destino_3') in destino_3_opcoes else 0
                    destino_3_novo = st.selectbox("3º Destino (Opcional)", options=destino_3_opcoes, index=destino_3_idx)
                
                submitted = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
                
                if submitted:
                    # Recarregar dados atuais do usuário antes de tentar atualizar
                    usuario_atual = verificar_email(usuario.get('email'))
                    if not usuario_atual:
                        st.error("Usuário não encontrado. Faça login novamente.")
                        st.stop() 
                    # Usar o ID atualizado
                    usuario_id = usuario_atual.get('id')
                    
                    # Validações básicas
                    erros = []
                    
                    if not nome_novo.strip():
                        erros.append("Nome é obrigatório")
                    
                    if not email_novo.strip():
                        erros.append("E-mail é obrigatório")
                    elif not validar_email(email_novo):
                        erros.append("E-mail inválido")
                    
                    if not telefone_novo.strip():
                        erros.append("Telefone é obrigatório")
                    
                    if origem_nova == destino_1_novo:
                        erros.append("Destino não pode ser igual ao tribunal de origem")
                    
                    if erros:
                        for erro in erros:
                            st.error(f"❌ {erro}")
                    else:
                        dados_atualizados = {
                            "nome": nome_novo.strip(),
                            "entrancia": entrancia_nova,
                            "origem": origem_nova,
                            "destino_1": destino_1_novo,
                            "destino_2": destino_2_novo if destino_2_novo else None,
                            "destino_3": destino_3_novo if destino_3_novo else None,
                            "email": email_novo.strip().lower(),
                            "telefone": telefone_novo.strip()
                        }
                        
                        sucesso, mensagem = atualizar_magistrado(usuario_id, dados_atualizados)
                        
                        if sucesso:
                            st.success(mensagem)
                            st.cache_data.clear()  # Limpar cache para refletir mudanças
                            st.info("Por favor, faça logout e login novamente para ver as alterações.")
                        else:
                            st.error(mensagem)
        
        elif opcao == "🗑️ Excluir meu cadastro":
            st.error("⚠️ **ATENÇÃO: Esta ação não pode ser desfeita!**")
            st.write("Ao excluir seu cadastro:")
            st.write("- Todos seus dados serão removidos permanentemente")
            st.write("- Você não aparecerá mais nas buscas de outros magistrados")
            st.write("- Será necessário cadastrar-se novamente para usar o sistema")
            
            confirmar_exclusao = st.text_input(
                "Para confirmar, digite 'EXCLUIR' (em maiúsculas):",
                placeholder="Digite EXCLUIR para confirmar"
            )
            
            if st.button("🗑️ Confirmar Exclusão", type="secondary"):
                if confirmar_exclusao == "EXCLUIR":
                    sucesso, mensagem = excluir_magistrado(usuario.get('id'))
                    
                    if sucesso:
                        st.success(mensagem)
                        st.info("Você será deslogado em 3 segundos...")
                        # Logout automático
                        st.session_state.usuario_autenticado = None
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(mensagem)
                else:
                    st.error("Confirmação incorreta. Digite exatamente 'EXCLUIR' para prosseguir.")
    
    # Botão para sair
    st.markdown("---")
    if st.button("🚪 Sair do sistema"):
        st.session_state.usuario_autenticado = None
        st.rerun()
