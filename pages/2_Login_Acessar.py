import streamlit as st
from supabase import create_client, Client
from utils.auth_supabase import enviar_codigo_otp, verificar_codigo_otp
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import re
import urllib.parse

# Configuração da página
st.set_page_config(
    page_title="Buscar permuta",
    page_icon="🔍",
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

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("logo.png", width=350)
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

    # ── Dashboard estilizado ──
    st.markdown(
        """
        <style>
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
        }
        .metric-card-green {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }
        .metric-card-blue {
            background: linear-gradient(135deg, #2193b0 0%, #6dd5ed 100%);
        }
        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: #ffffff;
            margin: 0;
            line-height: 1.2;
        }
        .metric-label {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.85);
            margin-top: 8px;
            font-weight: 500;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }
        .metric-detail {
            font-size: 0.8rem;
            color: rgba(255, 255, 255, 0.7);
            margin-top: 4px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Preparar dados dos cards
    tribunal_mais_procurado = "-"
    total_mais_procurado = 0
    if destinos_contador:
        mais_procurado = destinos_contador.most_common(1)[0]
        tribunal_mais_procurado = mais_procurado[0]
        total_mais_procurado = mais_procurado[1]

    maior_exportador = "-"
    total_exportador = 0
    if origens_contador:
        top_exportador = origens_contador.most_common(1)[0]
        maior_exportador = top_exportador[0]
        total_exportador = top_exportador[1]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <p class="metric-value">{total_juizes}</p>
                <p class="metric-label">Magistrados Cadastrados</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card metric-card-green">
                <p class="metric-value">{tribunal_mais_procurado}</p>
                <p class="metric-label">Tribunal Mais Procurado</p>
                <p class="metric-detail">{total_mais_procurado} interessados</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card metric-card-blue">
                <p class="metric-value">{maior_exportador}</p>
                <p class="metric-label">Maior Exportador</p>
                <p class="metric-detail">{total_exportador} magistrados</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

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

# Funções para triangulação por etapas
def triangular_prioritarias(origem, destino, dados):
    """Etapa 1: Triangulações onde TODOS os envolvidos usam destino_1."""
    triangulacoes = []

    for mag_origem in dados:
        if mag_origem.get('origem') != origem:
            continue
        if mag_origem.get('destino_1') != destino:
            destino_1_mag = mag_origem.get('destino_1')
            if not destino_1_mag:
                continue

            for mag_inter in dados:
                if mag_inter.get('origem') != destino_1_mag:
                    continue
                if mag_inter.get('destino_1') != destino:
                    continue

                for mag_final in dados:
                    if mag_final.get('origem') != destino:
                        continue
                    if mag_final.get('destino_1') != origem:
                        continue

                    seq = f"{origem} → {destino_1_mag} → {destino} → {origem}"
                    triangulacoes.append({
                        'tipo': 'triangular',
                        'magistrados': [mag_origem, mag_inter, mag_final],
                        'sequencia': seq,
                        'nivel': 'prioritaria'
                    })
        else:
            for mag_destino in dados:
                if mag_destino.get('origem') != destino:
                    continue
                if mag_destino.get('destino_1') != origem:
                    continue

                seq = f"{origem} ↔ {destino}"
                triangulacoes.append({
                    'tipo': 'direta',
                    'magistrados': [mag_origem, mag_destino],
                    'sequencia': seq,
                    'nivel': 'prioritaria'
                })

    # Remover duplicatas por combinação de nomes
    vistos = set()
    unicos = []
    for t in triangulacoes:
        nomes = tuple(sorted(m.get('nome', '') for m in t['magistrados']))
        chave = (t['sequencia'], nomes)
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(t)

    return unicos


def triangular_expandidas(origem, destino, dados, limite=50, ja_encontradas=None):
    """Etapa 2+: Triangulações usando destinos 1, 2 e 3, com limite."""
    triangulacoes = []

    sequencias_existentes = set()
    if ja_encontradas:
        for t in ja_encontradas:
            nomes = tuple(sorted(m.get('nome', '') for m in t['magistrados']))
            sequencias_existentes.add((t['sequencia'], nomes))

    for mag_origem in dados:
        if mag_origem.get('origem') != origem:
            continue

        destinos_mag_origem = [mag_origem.get(f'destino_{i}') for i in range(1, 4) if mag_origem.get(f'destino_{i}')]

        for dest_mag in destinos_mag_origem:
            if dest_mag == destino:
                for mag_destino in dados:
                    if mag_destino.get('origem') != destino:
                        continue
                    destinos_dest = [mag_destino.get(f'destino_{i}') for i in range(1, 4) if mag_destino.get(f'destino_{i}')]
                    if origem in destinos_dest:
                        seq = f"{origem} ↔ {destino}"
                        nomes = tuple(sorted(m.get('nome', '') for m in [mag_origem, mag_destino]))
                        chave = (seq, nomes)
                        if chave not in sequencias_existentes:
                            triangulacoes.append({
                                'tipo': 'direta',
                                'magistrados': [mag_origem, mag_destino],
                                'sequencia': seq,
                                'nivel': 'expandida'
                            })
                            sequencias_existentes.add(chave)
                            if len(triangulacoes) >= limite:
                                return triangulacoes, True
            else:
                for mag_inter in dados:
                    if mag_inter.get('origem') != dest_mag:
                        continue
                    destinos_inter = [mag_inter.get(f'destino_{i}') for i in range(1, 4) if mag_inter.get(f'destino_{i}')]
                    if destino not in destinos_inter:
                        continue

                    for mag_final in dados:
                        if mag_final.get('origem') != destino:
                            continue
                        destinos_final = [mag_final.get(f'destino_{i}') for i in range(1, 4) if mag_final.get(f'destino_{i}')]
                        if origem in destinos_final:
                            seq = f"{origem} → {dest_mag} → {destino} → {origem}"
                            nomes = tuple(sorted(m.get('nome', '') for m in [mag_origem, mag_inter, mag_final]))
                            chave = (seq, nomes)
                            if chave not in sequencias_existentes:
                                triangulacoes.append({
                                    'tipo': 'triangular',
                                    'magistrados': [mag_origem, mag_inter, mag_final],
                                    'sequencia': seq,
                                    'nivel': 'expandida'
                                })
                                sequencias_existentes.add(chave)
                                if len(triangulacoes) >= limite:
                                    return triangulacoes, True

    return triangulacoes, False


def gerar_link_whatsapp(texto):
    """Gera link do WhatsApp com texto pré-formatado."""
    texto_encoded = urllib.parse.quote(texto)
    return f"https://wa.me/?text={texto_encoded}"


def buscar_pares_aguardando(dados):
    """
    Encontra magistrados que querem ir para um tribunal,
    mas ninguém desse tribunal quer ir para o tribunal deles.
    Retorna lista de magistrados 'sem par'.
    """
    sem_par = []

    for mag in dados:
        origem = mag.get('origem')
        destino_1 = mag.get('destino_1')

        if not origem or not destino_1:
            continue

        # Verificar se existe alguém do destino_1 que queira vir para a origem
        tem_par = False
        for outro in dados:
            if outro.get('origem') != destino_1:
                continue
            destinos_outro = [outro.get(f'destino_{i}') for i in range(1, 4) if outro.get(f'destino_{i}')]
            if origem in destinos_outro:
                tem_par = True
                break

        if not tem_par:
            sem_par.append({
                'magistrado': mag,
                'origem': origem,
                'destino_desejado': destino_1,
                'falta': f"Magistrado do {destino_1} com destino {origem}"
            })

    return sem_par


def pecas_faltantes_prioritarias(origem_filtro, destino_filtro, dados):
    """Etapa 1: Peças faltantes considerando APENAS destino_1 de todos."""
    pecas = []
    vistos = set()

    # Cenário A: mag_1 (origem, destino_1=destino), mag_2 (destino, destino_1=X), falta X→origem
    for mag_1 in dados:
        if mag_1.get('origem') != origem_filtro:
            continue
        if mag_1.get('destino_1') != destino_filtro:
            continue

        for mag_2 in dados:
            if mag_2.get('origem') != destino_filtro:
                continue
            dest_2 = mag_2.get('destino_1')
            if not dest_2 or dest_2 == origem_filtro:
                continue

            tem_terceiro = False
            for mag_3 in dados:
                if mag_3.get('origem') != dest_2:
                    continue
                if mag_3.get('destino_1') == origem_filtro:
                    tem_terceiro = True
                    break

            if not tem_terceiro:
                chave = (mag_1.get('nome'), mag_2.get('nome'), dest_2)
                if chave not in vistos:
                    vistos.add(chave)
                    pecas.append({
                        'mag_1': mag_1,
                        'mag_2': mag_2,
                        'sequencia': f"{origem_filtro} → {destino_filtro} → {dest_2} → {origem_filtro}",
                        'falta': f"Magistrado do {dest_2} com destino {origem_filtro}",
                        'nivel': 'prioritaria'
                    })

    # Cenário B: mag_1 (origem, destino_1=intermediario), mag_inter (intermediario, destino_1=destino), falta destino→origem
    for mag_1 in dados:
        if mag_1.get('origem') != origem_filtro:
            continue
        intermediario = mag_1.get('destino_1')
        if not intermediario or intermediario == destino_filtro:
            continue

        for mag_inter in dados:
            if mag_inter.get('origem') != intermediario:
                continue
            if mag_inter.get('destino_1') != destino_filtro:
                continue

            tem_terceiro = False
            for mag_3 in dados:
                if mag_3.get('origem') != destino_filtro:
                    continue
                if mag_3.get('destino_1') == origem_filtro:
                    tem_terceiro = True
                    break

            if not tem_terceiro:
                chave = (mag_1.get('nome'), mag_inter.get('nome'), destino_filtro)
                if chave not in vistos:
                    vistos.add(chave)
                    pecas.append({
                        'mag_1': mag_1,
                        'mag_2': mag_inter,
                        'sequencia': f"{origem_filtro} → {intermediario} → {destino_filtro} → {origem_filtro}",
                        'falta': f"Magistrado do {destino_filtro} com destino {origem_filtro}",
                        'nivel': 'prioritaria'
                    })

    return pecas


def pecas_faltantes_expandidas(origem_filtro, destino_filtro, dados, limite=50, ja_encontradas=None):
    """Etapa 2: Peças faltantes usando destinos 1, 2 e 3, com limite."""
    pecas = []
    vistos = set()

    if ja_encontradas:
        for p in ja_encontradas:
            chave = (p['mag_1'].get('nome'), p['mag_2'].get('nome'), p['sequencia'])
            vistos.add(chave)

    # Cenário A: mag_1 da origem quer destino (via qualquer destino), mag_2 do destino quer X, falta X→origem
    for mag_1 in dados:
        if mag_1.get('origem') != origem_filtro:
            continue
        destinos_1 = [mag_1.get(f'destino_{i}') for i in range(1, 4) if mag_1.get(f'destino_{i}')]
        if destino_filtro not in destinos_1:
            continue

        for mag_2 in dados:
            if mag_2.get('origem') != destino_filtro:
                continue
            destinos_2 = [mag_2.get(f'destino_{i}') for i in range(1, 4) if mag_2.get(f'destino_{i}')]

            for dest_2 in destinos_2:
                if dest_2 == origem_filtro:
                    continue

                tem_terceiro = False
                for mag_3 in dados:
                    if mag_3.get('origem') != dest_2:
                        continue
                    destinos_3 = [mag_3.get(f'destino_{i}') for i in range(1, 4) if mag_3.get(f'destino_{i}')]
                    if origem_filtro in destinos_3:
                        tem_terceiro = True
                        break

                if not tem_terceiro:
                    seq = f"{origem_filtro} → {destino_filtro} → {dest_2} → {origem_filtro}"
                    chave = (mag_1.get('nome'), mag_2.get('nome'), seq)
                    if chave not in vistos:
                        vistos.add(chave)
                        pecas.append({
                            'mag_1': mag_1,
                            'mag_2': mag_2,
                            'sequencia': seq,
                            'falta': f"Magistrado do {dest_2} com destino {origem_filtro}",
                            'nivel': 'expandida'
                        })
                        if len(pecas) >= limite:
                            return pecas

    # Cenário B: mag_1 da origem quer intermediário, mag_inter quer destino, falta destino→origem
    for mag_1 in dados:
        if mag_1.get('origem') != origem_filtro:
            continue
        destinos_1 = [mag_1.get(f'destino_{i}') for i in range(1, 4) if mag_1.get(f'destino_{i}')]

        for intermediario in destinos_1:
            if intermediario == destino_filtro:
                continue

            for mag_inter in dados:
                if mag_inter.get('origem') != intermediario:
                    continue
                destinos_inter = [mag_inter.get(f'destino_{i}') for i in range(1, 4) if mag_inter.get(f'destino_{i}')]
                if destino_filtro not in destinos_inter:
                    continue

                tem_terceiro = False
                for mag_3 in dados:
                    if mag_3.get('origem') != destino_filtro:
                        continue
                    destinos_3 = [mag_3.get(f'destino_{i}') for i in range(1, 4) if mag_3.get(f'destino_{i}')]
                    if origem_filtro in destinos_3:
                        tem_terceiro = True
                        break

                if not tem_terceiro:
                    seq = f"{origem_filtro} → {intermediario} → {destino_filtro} → {origem_filtro}"
                    chave = (mag_1.get('nome'), mag_inter.get('nome'), seq)
                    if chave not in vistos:
                        vistos.add(chave)
                        pecas.append({
                            'mag_1': mag_1,
                            'mag_2': mag_inter,
                            'sequencia': seq,
                            'falta': f"Magistrado do {destino_filtro} com destino {origem_filtro}",
                            'nivel': 'expandida'
                        })
                        if len(pecas) >= limite:
                            return pecas

    return pecas


def buscar_quadrangulacao_func(origem_filtro, destino_filtro, dados, limite=30):
    """
    Busca quadrangulações (ciclo de 4 magistrados) usando APENAS destino_1.
    Ciclo: origem → A → B → destino → origem
    Onde:
    - mag_1 está na origem, destino_1 = A
    - mag_2 está em A, destino_1 = B
    - mag_3 está em B, destino_1 = destino
    - mag_4 está no destino, destino_1 = origem
    """
    quadrangulacoes = []
    vistos = set()

    for mag_1 in dados:
        if mag_1.get('origem') != origem_filtro:
            continue
        tribunal_a = mag_1.get('destino_1')
        if not tribunal_a or tribunal_a == destino_filtro or tribunal_a == origem_filtro:
            continue

        for mag_2 in dados:
            if mag_2.get('origem') != tribunal_a:
                continue
            tribunal_b = mag_2.get('destino_1')
            if not tribunal_b or tribunal_b == origem_filtro or tribunal_b == tribunal_a or tribunal_b == destino_filtro:
                continue

            for mag_3 in dados:
                if mag_3.get('origem') != tribunal_b:
                    continue
                if mag_3.get('destino_1') != destino_filtro:
                    continue

                for mag_4 in dados:
                    if mag_4.get('origem') != destino_filtro:
                        continue
                    if mag_4.get('destino_1') != origem_filtro:
                        continue

                    nomes = tuple(sorted(m.get('nome', '') for m in [mag_1, mag_2, mag_3, mag_4]))
                    seq = f"{origem_filtro} → {tribunal_a} → {tribunal_b} → {destino_filtro} → {origem_filtro}"
                    chave = (nomes, seq)

                    if chave not in vistos:
                        vistos.add(chave)
                        quadrangulacoes.append({
                            'magistrados': [mag_1, mag_2, mag_3, mag_4],
                            'sequencia': seq,
                            'tribunais': [origem_filtro, tribunal_a, tribunal_b, destino_filtro]
                        })

                        if len(quadrangulacoes) >= limite:
                            return quadrangulacoes

    return quadrangulacoes


def pecas_faltantes_quadrangulacao(origem_filtro, destino_filtro, dados, limite=30):
    """
    Encontra quadrangulações quase completas: 3 magistrados encaixam,
    falta 1 para fechar o ciclo de 4. Apenas destino_1.
    """
    pecas = []
    vistos = set()

    # Cenário 1: mag_1(origem→A), mag_2(A→B), mag_3(B→destino), falta mag_4(destino→origem)
    for mag_1 in dados:
        if mag_1.get('origem') != origem_filtro:
            continue
        tribunal_a = mag_1.get('destino_1')
        if not tribunal_a or tribunal_a == destino_filtro or tribunal_a == origem_filtro:
            continue

        for mag_2 in dados:
            if mag_2.get('origem') != tribunal_a:
                continue
            tribunal_b = mag_2.get('destino_1')
            if not tribunal_b or tribunal_b == origem_filtro or tribunal_b == tribunal_a or tribunal_b == destino_filtro:
                continue

            for mag_3 in dados:
                if mag_3.get('origem') != tribunal_b:
                    continue
                if mag_3.get('destino_1') != destino_filtro:
                    continue

                # Verificar se existe mag_4(destino→origem)
                tem_quarto = False
                for mag_4 in dados:
                    if mag_4.get('origem') != destino_filtro:
                        continue
                    if mag_4.get('destino_1') == origem_filtro:
                        tem_quarto = True
                        break

                if not tem_quarto:
                    seq = f"{origem_filtro} → {tribunal_a} → {tribunal_b} → {destino_filtro} → {origem_filtro}"
                    chave = (mag_1.get('nome'), mag_2.get('nome'), mag_3.get('nome'), seq)
                    if chave not in vistos:
                        vistos.add(chave)
                        pecas.append({
                            'magistrados': [mag_1, mag_2, mag_3],
                            'sequencia': seq,
                            'falta': f"Magistrado do {destino_filtro} com destino {origem_filtro}",
                            'posicao_faltante': 4
                        })
                        if len(pecas) >= limite:
                            return pecas

    # Cenário 2: mag_1(origem→A), mag_2(A→B), falta mag_3(B→destino), mag_4(destino→origem) existe
    for mag_1 in dados:
        if mag_1.get('origem') != origem_filtro:
            continue
        tribunal_a = mag_1.get('destino_1')
        if not tribunal_a or tribunal_a == destino_filtro or tribunal_a == origem_filtro:
            continue

        for mag_2 in dados:
            if mag_2.get('origem') != tribunal_a:
                continue
            tribunal_b = mag_2.get('destino_1')
            if not tribunal_b or tribunal_b == origem_filtro or tribunal_b == tribunal_a or tribunal_b == destino_filtro:
                continue

            # Verificar se existe mag_3(B→destino)
            tem_terceiro = False
            for mag_3 in dados:
                if mag_3.get('origem') != tribunal_b:
                    continue
                if mag_3.get('destino_1') == destino_filtro:
                    tem_terceiro = True
                    break

            if not tem_terceiro:
                # Verificar se existe mag_4(destino→origem) para confirmar que é quase completa
                for mag_4 in dados:
                    if mag_4.get('origem') != destino_filtro:
                        continue
                    if mag_4.get('destino_1') != origem_filtro:
                        continue

                    seq = f"{origem_filtro} → {tribunal_a} → {tribunal_b} → {destino_filtro} → {origem_filtro}"
                    chave = (mag_1.get('nome'), mag_2.get('nome'), mag_4.get('nome'), seq)
                    if chave not in vistos:
                        vistos.add(chave)
                        pecas.append({
                            'magistrados': [mag_1, mag_2, mag_4],
                            'sequencia': seq,
                            'falta': f"Magistrado do {tribunal_b} com destino {destino_filtro}",
                            'posicao_faltante': 3
                        })
                        if len(pecas) >= limite:
                            return pecas

    # Cenário 3: mag_1(origem→A), falta mag_2(A→B), mag_3(B→destino) e mag_4(destino→origem) existem
    for mag_1 in dados:
        if mag_1.get('origem') != origem_filtro:
            continue
        tribunal_a = mag_1.get('destino_1')
        if not tribunal_a or tribunal_a == destino_filtro or tribunal_a == origem_filtro:
            continue

        # Para cada possível tribunal_b (origens no banco que não sejam origem, A ou destino)
        tribunais_b_possiveis = set()
        for m in dados:
            o = m.get('origem')
            if o and o != origem_filtro and o != tribunal_a and o != destino_filtro:
                tribunais_b_possiveis.add(o)

        for tribunal_b in tribunais_b_possiveis:
            # Verificar se existe mag_2(A→B)
            tem_segundo = False
            for mag_2 in dados:
                if mag_2.get('origem') != tribunal_a:
                    continue
                if mag_2.get('destino_1') == tribunal_b:
                    tem_segundo = True
                    break

            if tem_segundo:
                continue  # Se existe, não é peça faltante nesta posição

            # Verificar se mag_3(B→destino) e mag_4(destino→origem) existem
            tem_terceiro = False
            mag_3_ref = None
            for mag_3 in dados:
                if mag_3.get('origem') != tribunal_b:
                    continue
                if mag_3.get('destino_1') == destino_filtro:
                    tem_terceiro = True
                    mag_3_ref = mag_3
                    break

            if not tem_terceiro:
                continue

            for mag_4 in dados:
                if mag_4.get('origem') != destino_filtro:
                    continue
                if mag_4.get('destino_1') != origem_filtro:
                    continue

                seq = f"{origem_filtro} → {tribunal_a} → {tribunal_b} → {destino_filtro} → {origem_filtro}"
                chave = (mag_1.get('nome'), mag_3_ref.get('nome'), mag_4.get('nome'), seq)
                if chave not in vistos:
                    vistos.add(chave)
                    pecas.append({
                        'magistrados': [mag_1, mag_3_ref, mag_4],
                        'sequencia': seq,
                        'falta': f"Magistrado do {tribunal_a} com destino {tribunal_b}",
                        'posicao_faltante': 2
                    })
                    if len(pecas) >= limite:
                        return pecas

    return pecas


# Função para buscar novos cadastros
def buscar_novos_cadastros(dias=60):
    """Busca magistrados cadastrados nos últimos X dias."""
    supabase = init_supabase()
    if not supabase:
        return []

    try:
        from datetime import datetime, timedelta
        data_limite = (datetime.now() - timedelta(days=dias)).isoformat()

        response = (
            supabase.table("magistrados")
            .select("nome, entrancia, origem, destino_1, destino_2, destino_3, email, telefone_visivel, created_at")
            .gte("created_at", data_limite)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Erro ao buscar novos cadastros: {e}")
        return []

def buscar_notificacoes(email):
    """Busca notificações não lidas para o usuário."""
    supabase = init_supabase()
    if not supabase:
        return []
    try:
        response = (
            supabase.table("notificacoes")
            .select("*")
            .eq("email_destino", email)
            .eq("lida", False)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data if response.data else []
    except:
        return []


def marcar_notificacoes_lidas(email):
    """Marca todas as notificações do usuário como lidas."""
    supabase = init_supabase()
    if not supabase:
        return
    try:
        supabase.table("notificacoes").update(
            {"lida": True}
        ).eq("email_destino", email).eq("lida", False).execute()
    except:
        pass


# Função para exibir magistrado
def exibir_magistrado(magistrado, prioridade=None):
    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        st.write(f"**{magistrado.get('nome', 'N/A')}**")
        st.write(f"📍 {magistrado.get('origem', 'N/A')} - {magistrado.get('entrancia', 'N/A')}")

    with col2:
        # Email sempre visível
        email_contato = magistrado.get('email', '-')
        st.write(f"📧 {email_contato}")
        # Telefone só se visível
        if magistrado.get('telefone_visivel', True) and magistrado.get('telefone'):
            st.write(f"📞 {magistrado['telefone']}")

    with col3:
        if prioridade:
            cores = {1: "🟢", 2: "🟡", 3: "🔵"}
            st.write(f"{cores.get(prioridade, '⚪')} Prioridade {prioridade}")

# Interface principal
st.title("🔍 Busca de Permutas")
st.write("Esta aplicação é gratuita e colaborativa e, tendo em vista que o link para cadastro e acesso foi fornecido individualmente a cada magistrado(a), os dados aqui presentes limitam-se ao fim de facilitar encontros de permutantes. Esta aplicação é privada e a partir do cadastro dos dados, o(a) magistrado(a) assume a responsabilidade.")

# Botões de ação
col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    if st.button("🔄 Atualizar base de dados agora", use_container_width=True):
        atualizar_dados()

with col_btn2:
    if st.button("☕ Contribua com um café para a manutenção", use_container_width=True, type="primary"):
        st.session_state["mostrar_pix"] = not st.session_state.get("mostrar_pix", False)
        st.rerun()

if st.session_state.get("mostrar_pix", False):
    with st.container():
        st.markdown("---")
        st.markdown(
            """
            <div style="background-color: #f8f9fa; border-radius: 10px; padding: 20px; border: 1px solid #e0e0e0;">
                <p style="font-size: 14px; color: #555; text-align: center; margin-bottom: 15px;">
                    <em>O Permutatum é uma aplicação gratuita e mantida de forma independente.
                    Não se trata de prestação de serviços ou compra de produtos.
                    Sua contribuição ajuda a manter o sistema no ar, com ampliação da escalabilidade da ferramenta.</em>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("")

        col_qr1, col_qr2, col_qr3 = st.columns([1, 2, 1])
        with col_qr2:
            st.image("qrcode.jpeg", caption="Escaneie o QR Code com seu app bancário", width=250)

            st.markdown("**Chave PIX (aleatória):**")

            chave_pix = "b2a904e7-7d32-445c-92e1-a30f41efaac9"
            st.code(chave_pix, language=None)

            st.markdown(
                """
                <p style="font-size: 12px; color: #888; text-align: center;">
                    Clique no campo acima para copiar a chave
                </p>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("---")

# Autenticação
if 'usuario_autenticado' not in st.session_state:
    st.session_state.usuario_autenticado = None

if "pecas_etapa" not in st.session_state:
    st.session_state["pecas_etapa"] = 0

if "quad_resultados" not in st.session_state:
    st.session_state["quad_resultados"] = None
if "pecas_quad" not in st.session_state:
    st.session_state["pecas_quad"] = None

if not st.session_state.usuario_autenticado:
    st.write("Digite seu e-mail para acessar a aplicação:")
    
    email_input = st.text_input("E-mail:", placeholder="seu.email@exemplo.com")
    
    if email_input:
        usuario = verificar_email(email_input)
        if usuario:
            st.session_state.usuario_autenticado = usuario
            st.success(f"Bem-vindo(a), {usuario.get('nome', 'Usuário')}!")
            st.session_state["gerenciar_otp_verificado"] = False
            st.session_state["gerenciar_otp_enviado"] = False
            st.session_state["gerenciar_otp_email"] = ""
            st.rerun()
        else:
            st.warning("⚠️ Acesso restrito. Seu e-mail não está cadastrado na base de dados.")
            if st.button("📝 Ir para página de cadastro"):
                st.switch_page("app.py")

else:
    # Usuário autenticado - mostrar sistema completo
    usuario = st.session_state.usuario_autenticado
    dados = carregar_dados()

    # ── Verificar notificações ──
    notificacoes = buscar_notificacoes(usuario.get('email', ''))
    if notificacoes:
        st.markdown(
            f"""
            <div style="background-color: #d4edda; border-radius: 10px; padding: 16px 20px; margin-bottom: 20px; border: 1px solid #c3e6cb; border-left: 5px solid #28a745;">
                <p style="margin: 0 0 8px 0; font-size: 16px; color: #155724; font-weight: bold;">
                    🔔 Você tem {len(notificacoes)} notificação(ões) nova(s)!
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for notif in notificacoes:
            tipo_emoji = "🔄" if notif.get('tipo') == 'permuta_direta' else "🔺"
            st.markdown(
                f"""
                <div style="background-color: #fff3cd; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px; border-left: 4px solid #ffc107;">
                    <p style="margin: 0; font-size: 14px; color: #856404;">
                        {tipo_emoji} {notif.get('mensagem', '')}
                    </p>
                    <p style="margin: 4px 0 0 0; font-size: 12px; color: #999;">
                        {notif.get('detalhes', '')}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if st.button("✅ Marcar notificações como lidas", key="btn_marcar_lidas"):
            marcar_notificacoes_lidas(usuario.get('email', ''))
            st.rerun()

        st.markdown("---")

    # Gráficos e estatísticas
    gerar_graficos(dados)
    
    st.markdown("---")
    
    # Sistema de tabs para diferentes consultas
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🔍 𝗕𝘂𝘀𝗰𝗮 𝗱𝗲 𝗣𝗲𝗿𝗺𝘂𝘁𝗮",
        "🔎 𝗣𝗮𝗿𝗲𝘀 𝗮𝗴𝘂𝗮𝗿𝗱𝗮𝗻𝗱𝗼 𝗺𝗮𝘁𝗰𝗵",
        "📊 Novos cadastros",
        "🎯 Interessados no meu tribunal",
        "📍 Tribunais que me interessam",
        "⚙️ Gerenciar meus dados"
    ])

    with tab1:
        st.subheader("🔍 Busca de Permuta")
        st.markdown(
            """
            <div style="background-color: #fdf6ec; border-radius: 10px; padding: 18px 22px; margin-bottom: 20px; border: 1px solid #f0e0c0;">
                <p style="margin: 0 0 12px 0; font-size: 15px; color: #333;">
                    Selecione os tribunais de <strong>Origem</strong> e <strong>Destino</strong> e escolha uma das opções:
                </p>
                <table style="width: 100%; border-collapse: collapse; font-size: 14px; color: #555;">
                    <tr>
                        <td style="padding: 8px 12px; vertical-align: top; width: 33%;">
                            <strong>🔄 Buscar Permuta</strong><br>
                            Encontra pares diretos: magistrados que querem trocar de tribunal entre si.
                            Ex: você do TJGO quer ir ao TJBA e alguém do TJBA quer vir ao TJGO.
                        </td>
                        <td style="padding: 8px 12px; vertical-align: top; width: 33%;">
                            <strong>🔺 Buscar Triangulação</strong><br>
                            Permutas indiretas entre 3 magistrados.
                            Ex: TJGO → TJBA → TJSP → TJGO.
                        </td>
                        <td style="padding: 8px 12px; vertical-align: top; width: 33%;">
                            <strong>🧩 Peças Faltantes</strong><br>
                            Triangulações quase completas: 2 magistrados encaixados, falta 1 para fechar.
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 12px; vertical-align: top; width: 50%;" colspan="1">
                            <strong>🔷 Buscar Quadrangulação</strong><br>
                            Permutas indiretas entre 4 magistrados em ciclo.
                            Ex: TJGO → TJBA → TJSP → TJRJ → TJGO.
                            Apenas destinos prioritários.
                        </td>
                        <td style="padding: 8px 12px; vertical-align: top; width: 50%;" colspan="2">
                            <strong>🧩 Peças Faltantes (quadrangulação)</strong><br>
                            Quadrangulações quase completas: 3 magistrados encaixados, falta 1 para fechar o ciclo de 4.
                        </td>
                    </tr>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)

        with col1:
            origem_filtro = st.selectbox(
                "Tribunal de Origem:",
                options=[""] + TRIBUNAIS,
                help="Selecione o tribunal de origem",
                key="sel_origem_busca"
            )

        with col2:
            destino_filtro = st.selectbox(
                "Tribunal de Destino:",
                options=[""] + TRIBUNAIS,
                help="Selecione o tribunal de destino",
                key="sel_destino_busca"
            )

        # Três botões lado a lado
        col_b1, col_b2, col_b3 = st.columns(3)

        with col_b1:
            buscar_permuta = st.button("🔄 Buscar Permuta", use_container_width=True, type="primary", key="btn_buscar_permuta")

        with col_b2:
            buscar_triangulacao = st.button("🔺 Buscar Triangulação", use_container_width=True, type="primary", key="btn_buscar_triangulacao")

        with col_b3:
            buscar_pecas = st.button("🧩 Peças faltantes", use_container_width=True, key="btn_buscar_pecas")

        col_b4, col_b5 = st.columns(2)

        with col_b4:
            btn_buscar_quad = st.button("🔷 Buscar Quadrangulação", use_container_width=True, type="primary", key="btn_buscar_quad")

        with col_b5:
            btn_buscar_pecas_quad = st.button("🧩 Peças faltantes (quadrangulação)", use_container_width=True, key="btn_buscar_pecas_quad")

        # Validação comum
        def validar_selecao():
            if not origem_filtro or not destino_filtro:
                st.warning("Selecione ambos os tribunais para realizar a busca.")
                return False
            if origem_filtro == destino_filtro:
                st.error("Tribunal de origem e destino devem ser diferentes.")
                return False
            return True

        st.markdown("---")

        # ═══════════════════════════════════
        # BUSCAR PERMUTA (permutas diretas)
        # ═══════════════════════════════════
        if buscar_permuta:
            if validar_selecao():
                # Limpar resultados de triangulação anteriores
                st.session_state["tri_etapa_busca"] = 0
                st.session_state["tri_prio_busca"] = []
                st.session_state["tri_exp_busca"] = []
                st.session_state["quad_resultados"] = None
                st.session_state["pecas_quad"] = None

                permutas_diretas, _ = busca_livre_inteligente(origem_filtro, destino_filtro, dados)

                st.subheader("🔄 Permutas Diretas Encontradas")
                if permutas_diretas:
                    st.success(f"Encontradas **{len(permutas_diretas)}** permutas diretas possíveis!")

                    for i, permuta in enumerate(permutas_diretas, 1):
                        with st.expander(f"Permuta {i}: {permuta['sequencia']}"):
                            st.success("✅ **PERMUTA DIRETA POSSÍVEL**")
                            st.write("Estes dois magistrados podem trocar de tribunal diretamente:")

                            st.write("**Magistrado 1:**")
                            exibir_magistrado(permuta['magistrado_1'], permuta['prioridade_1'])

                            st.write("**Magistrado 2:**")
                            exibir_magistrado(permuta['magistrado_2'], permuta['prioridade_2'])

                            score = 0
                            if permuta['prioridade_1'] == 1: score += 3
                            elif permuta['prioridade_1'] == 2: score += 2
                            elif permuta['prioridade_1'] == 3: score += 1
                            if permuta['prioridade_2'] == 1: score += 3
                            elif permuta['prioridade_2'] == 2: score += 2
                            elif permuta['prioridade_2'] == 3: score += 1

                            if score >= 5:
                                st.success("🌟 **ALTA COMPATIBILIDADE** - Ambos têm forte interesse")
                            elif score >= 3:
                                st.info("⭐ **MÉDIA COMPATIBILIDADE** - Interesse moderado")
                            else:
                                st.warning("💫 **BAIXA COMPATIBILIDADE** - Interesse limitado")
                else:
                    st.info(f"Nenhuma permuta direta encontrada entre {origem_filtro} e {destino_filtro}.")

        # ═══════════════════════════════════
        # BUSCAR TRIANGULAÇÃO (3 etapas)
        # ═══════════════════════════════════
        if buscar_triangulacao:
            if validar_selecao():
                st.session_state["quad_resultados"] = None
                st.session_state["pecas_quad"] = None
                with st.spinner("Buscando triangulações prioritárias (destino 1)..."):
                    resultado = triangular_prioritarias(origem_filtro, destino_filtro, dados)
                    st.session_state["tri_prio_busca"] = resultado
                    st.session_state["tri_exp_busca"] = []
                    st.session_state["tri_tem_mais_busca"] = False
                    st.session_state["tri_lote_busca"] = 1
                    st.session_state["tri_etapa_busca"] = 1
                    st.session_state["tri_origem_busca"] = origem_filtro
                    st.session_state["tri_destino_busca"] = destino_filtro
                    st.rerun()

        # ── Exibir resultados de triangulação (persistentes via session_state) ──
        if st.session_state.get("tri_etapa_busca", 0) >= 1:
            origem_tri = st.session_state.get("tri_origem_busca", "")
            destino_tri = st.session_state.get("tri_destino_busca", "")

            st.subheader(f"🔺 Triangulações: {origem_tri} ↔ {destino_tri}")

            # Etapa 1: Prioritárias
            prioritarias = st.session_state.get("tri_prio_busca", [])

            if prioritarias:
                st.success(f"🎯 **{len(prioritarias)}** triangulações prioritárias (apenas destino 1)")

                for i, tri in enumerate(prioritarias, 1):
                    emoji = "🔄" if tri['tipo'] == 'direta' else "🔺"
                    with st.expander(f"{emoji} Prioritária {i}: {tri['sequencia']}"):
                        if tri['tipo'] == 'direta':
                            st.success("🔄 **Permuta Direta Possível**")
                        else:
                            st.info("🔺 **Triangulação de 3 Magistrados**")
                            st.write("Operação coordenada entre três magistrados:")

                        st.write(f"**Sequência:** {tri['sequencia']}")
                        st.write("**Magistrados envolvidos:**")
                        for mag in tri['magistrados']:
                            exibir_magistrado(mag)
            else:
                st.warning("Nenhuma triangulação prioritária encontrada (destino 1).")

            st.markdown("---")

            # Etapa 2: Expandidas
            if st.session_state.get("tri_etapa_busca", 0) == 1:
                st.write("Expandir a busca para incluir destinos 1, 2 e 3?")
                if st.button("🔍 Buscar mais triangulações", use_container_width=True, key="btn_tri_exp_busca"):
                    with st.spinner("Expandindo busca (limitado a 50)..."):
                        resultado, tem_mais = triangular_expandidas(
                            origem_tri, destino_tri, dados,
                            limite=50,
                            ja_encontradas=prioritarias
                        )
                        st.session_state["tri_exp_busca"] = resultado
                        st.session_state["tri_tem_mais_busca"] = tem_mais
                        st.session_state["tri_etapa_busca"] = 2
                        st.rerun()

            if st.session_state.get("tri_etapa_busca", 0) >= 2:
                expandidas = st.session_state.get("tri_exp_busca", [])

                if expandidas:
                    st.success(f"🔍 **{len(expandidas)}** triangulações adicionais (destinos 1, 2 e 3)")

                    for i, tri in enumerate(expandidas, 1):
                        emoji = "🔄" if tri['tipo'] == 'direta' else "🔺"
                        with st.expander(f"{emoji} Adicional {i}: {tri['sequencia']}"):
                            if tri['tipo'] == 'direta':
                                st.success("🔄 **Permuta Direta Possível**")
                            else:
                                st.info("🔺 **Triangulação de 3 Magistrados**")
                                st.write("Operação coordenada entre três magistrados:")

                            st.write(f"**Sequência:** {tri['sequencia']}")
                            st.write("**Magistrados envolvidos:**")
                            for mag in tri['magistrados']:
                                exibir_magistrado(mag)
                else:
                    st.info("Nenhuma triangulação adicional encontrada.")

                # Etapa 3: Carregar mais
                if st.session_state.get("tri_tem_mais_busca", False):
                    st.markdown("---")
                    lote = st.session_state.get("tri_lote_busca", 1)
                    if st.button("📥 Carregar mais 50 triangulações", use_container_width=True, key=f"btn_tri_mais_busca_{lote}"):
                        with st.spinner("Carregando mais..."):
                            todas_anteriores = prioritarias + expandidas
                            novas, tem_mais = triangular_expandidas(
                                origem_tri, destino_tri, dados,
                                limite=50 * (lote + 1),
                                ja_encontradas=todas_anteriores
                            )
                            st.session_state["tri_exp_busca"].extend(novas)
                            st.session_state["tri_tem_mais_busca"] = tem_mais
                            st.session_state["tri_lote_busca"] = lote + 1
                            st.rerun()

            # Resumo total
            total = len(st.session_state.get("tri_prio_busca", [])) + len(st.session_state.get("tri_exp_busca", []))
            if total > 0:
                st.markdown("---")
                st.success(f"📊 **Total:** {total} triangulações encontradas")

            # Botão nova busca
            if st.button("🔄 Nova busca de triangulação", key="btn_tri_reset_busca"):
                st.session_state["tri_etapa_busca"] = 0
                st.session_state["tri_prio_busca"] = []
                st.session_state["tri_exp_busca"] = []
                st.session_state["tri_tem_mais_busca"] = False
                st.session_state["tri_lote_busca"] = 1
                st.rerun()

        # ═══════════════════════════════════
        # PEÇAS FALTANTES PARA TRIANGULAÇÃO
        # ═══════════════════════════════════
        if buscar_pecas:
            if validar_selecao():
                st.session_state["quad_resultados"] = None
                st.session_state["pecas_quad"] = None
                with st.spinner("Buscando peças faltantes prioritárias (destino 1)..."):
                    resultado = pecas_faltantes_prioritarias(origem_filtro, destino_filtro, dados)
                    st.session_state["pecas_prio"] = resultado
                    st.session_state["pecas_exp"] = []
                    st.session_state["pecas_etapa"] = 1
                    st.session_state["pecas_origem"] = origem_filtro
                    st.session_state["pecas_destino"] = destino_filtro
                    st.rerun()

        # ── Exibir resultados de peças faltantes ──
        if st.session_state.get("pecas_etapa", 0) >= 1:
            origem_p = st.session_state.get("pecas_origem", "")
            destino_p = st.session_state.get("pecas_destino", "")

            st.subheader(f"🧩 Peças Faltantes: {origem_p} ↔ {destino_p}")

            # Etapa 1: Prioritárias
            prio = st.session_state.get("pecas_prio", [])

            if prio:
                st.success(f"🎯 **{len(prio)}** triangulações quase completas (apenas destino 1)")

                for i, peca in enumerate(prio, 1):
                    with st.expander(f"🧩 Prioritária {i}: {peca['sequencia']}"):
                        st.write(f"**Sequência:** {peca['sequencia']}")
                        st.markdown(
                            f"""
                            <div style="background-color: #fff3cd; border-radius: 8px; padding: 12px; border-left: 4px solid #ffc107; margin: 10px 0;">
                                <strong>⚠️ Falta:</strong> {peca['falta']}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        st.write("**Magistrados já encaixados:**")
                        exibir_magistrado(peca['mag_1'])
                        st.write("⬇️")
                        exibir_magistrado(peca['mag_2'])

                        # Botão compartilhar WhatsApp
                        msg_whats = (
                            f"🧩 *Permutatum — Triangulação quase completa*\n\n"
                            f"Sequência: *{peca['sequencia']}*\n"
                            f"⚠️ *{peca['falta']}*\n\n"
                            f"Já estão encaixados 2 magistrados. "
                            f"Falta apenas 1 para fechar o ciclo!\n\n"
                            f"Cadastre-se: 👉 https://permutatum.streamlit.app/"
                        )
                        link_wpp = gerar_link_whatsapp(msg_whats)
                        st.markdown(
                            f"""
                            <a href="{link_wpp}" target="_blank" style="
                                display: inline-block;
                                background-color: #25D366;
                                color: white;
                                padding: 8px 16px;
                                border-radius: 8px;
                                text-decoration: none;
                                font-size: 14px;
                                font-weight: 500;
                            ">📲 Compartilhar no WhatsApp</a>
                            """,
                            unsafe_allow_html=True,
                        )
            else:
                st.warning("Nenhuma peça faltante prioritária encontrada (destino 1).")

            st.markdown("---")

            # Botão para expandir busca
            if st.session_state.get("pecas_etapa", 0) == 1:
                st.write("Expandir busca para incluir destinos 1, 2 e 3?")
                if st.button("🔍 Buscar mais peças faltantes", use_container_width=True, key="btn_pecas_exp"):
                    with st.spinner("Expandindo busca (limitado a 50)..."):
                        resultado = pecas_faltantes_expandidas(
                            origem_p, destino_p, dados,
                            limite=50,
                            ja_encontradas=prio
                        )
                        st.session_state["pecas_exp"] = resultado
                        st.session_state["pecas_etapa"] = 2
                        st.rerun()

            # Etapa 2: Expandidas
            if st.session_state.get("pecas_etapa", 0) >= 2:
                exp = st.session_state.get("pecas_exp", [])

                if exp:
                    st.success(f"🔍 **{len(exp)}** peças faltantes adicionais (destinos 1, 2 e 3)")

                    for i, peca in enumerate(exp, 1):
                        with st.expander(f"🧩 Adicional {i}: {peca['sequencia']}"):
                            st.write(f"**Sequência:** {peca['sequencia']}")
                            st.markdown(
                                f"""
                                <div style="background-color: #fff3cd; border-radius: 8px; padding: 12px; border-left: 4px solid #ffc107; margin: 10px 0;">
                                    <strong>⚠️ Falta:</strong> {peca['falta']}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            st.write("**Magistrados já encaixados:**")
                            exibir_magistrado(peca['mag_1'])
                            st.write("⬇️")
                            exibir_magistrado(peca['mag_2'])

                            # Botão compartilhar WhatsApp
                            msg_whats = (
                                f"🧩 *Permutatum — Triangulação quase completa*\n\n"
                                f"Sequência: *{peca['sequencia']}*\n"
                                f"⚠️ *{peca['falta']}*\n\n"
                                f"Já estão encaixados 2 magistrados. "
                                f"Falta apenas 1 para fechar o ciclo!\n\n"
                                f"Cadastre-se: 👉 https://permutatum.streamlit.app/"
                            )
                            link_wpp = gerar_link_whatsapp(msg_whats)
                            st.markdown(
                                f"""
                                <a href="{link_wpp}" target="_blank" style="
                                    display: inline-block;
                                    background-color: #25D366;
                                    color: white;
                                    padding: 8px 16px;
                                    border-radius: 8px;
                                    text-decoration: none;
                                    font-size: 14px;
                                    font-weight: 500;
                                ">📲 Compartilhar no WhatsApp</a>
                                """,
                                unsafe_allow_html=True,
                            )
                else:
                    st.info("Nenhuma peça faltante adicional encontrada.")

            # Resumo total
            total_pecas = len(st.session_state.get("pecas_prio", [])) + len(st.session_state.get("pecas_exp", []))
            if total_pecas > 0:
                st.markdown("---")
                st.success(f"📊 **Total:** {total_pecas} triangulações quase completas")

            # Botão nova busca
            if st.button("🔄 Nova busca de peças faltantes", key="btn_pecas_reset"):
                st.session_state["pecas_etapa"] = 0
                st.session_state["pecas_prio"] = []
                st.session_state["pecas_exp"] = []
                st.rerun()

        # ═══════════════════════════════════
        # BUSCAR QUADRANGULAÇÃO
        # ═══════════════════════════════════
        if btn_buscar_quad:
            if validar_selecao():
                st.session_state["tri_etapa_busca"] = 0
                st.session_state["tri_prio_busca"] = []
                st.session_state["tri_exp_busca"] = []
                st.session_state["pecas_etapa"] = 0
                st.session_state["pecas_prio"] = []
                st.session_state["pecas_exp"] = []
                with st.spinner("Buscando quadrangulações (destino 1 apenas)..."):
                    resultado = buscar_quadrangulacao_func(origem_filtro, destino_filtro, dados, limite=30)
                    st.session_state["quad_resultados"] = resultado
                    st.session_state["quad_origem"] = origem_filtro
                    st.session_state["quad_destino"] = destino_filtro
                    st.rerun()

        if st.session_state.get("quad_resultados") is not None:
            quad = st.session_state["quad_resultados"]
            origem_q = st.session_state.get("quad_origem", "")
            destino_q = st.session_state.get("quad_destino", "")

            st.subheader(f"🔷 Quadrangulações: {origem_q} ↔ {destino_q}")

            if quad:
                st.success(f"**{len(quad)}** quadrangulações encontradas (destino 1 apenas, máx. 30)")

                for i, q in enumerate(quad, 1):
                    with st.expander(f"🔷 Quadrangulação {i}: {q['sequencia']}"):
                        st.info("🔷 **Quadrangulação de 4 Magistrados**")
                        st.write("Operação coordenada entre quatro magistrados:")
                        st.write(f"**Sequência:** {q['sequencia']}")
                        st.write("**Magistrados envolvidos:**")
                        for j, mag in enumerate(q['magistrados']):
                            exibir_magistrado(mag)
                            if j < len(q['magistrados']) - 1:
                                st.write("⬇️")
                        st.success("💡 **Coordenação necessária:** Todos os 4 magistrados precisam concordar simultaneamente")
            else:
                st.info(f"Nenhuma quadrangulação encontrada entre {origem_q} e {destino_q} com destinos prioritários.")

            if st.button("🔄 Nova busca de quadrangulação", key="btn_quad_reset"):
                st.session_state["quad_resultados"] = None
                st.rerun()

        # ═══════════════════════════════════
        # PEÇAS FALTANTES QUADRANGULAÇÃO
        # ═══════════════════════════════════
        if btn_buscar_pecas_quad:
            if validar_selecao():
                st.session_state["tri_etapa_busca"] = 0
                st.session_state["tri_prio_busca"] = []
                st.session_state["tri_exp_busca"] = []
                st.session_state["pecas_etapa"] = 0
                st.session_state["pecas_prio"] = []
                st.session_state["pecas_exp"] = []
                with st.spinner("Buscando peças faltantes para quadrangulação (destino 1)..."):
                    resultado = pecas_faltantes_quadrangulacao(origem_filtro, destino_filtro, dados, limite=30)
                    st.session_state["pecas_quad"] = resultado
                    st.session_state["pecas_quad_origem"] = origem_filtro
                    st.session_state["pecas_quad_destino"] = destino_filtro
                    st.rerun()

        if st.session_state.get("pecas_quad") is not None:
            pecas_q = st.session_state["pecas_quad"]
            origem_pq = st.session_state.get("pecas_quad_origem", "")
            destino_pq = st.session_state.get("pecas_quad_destino", "")

            st.subheader(f"🧩 Peças Faltantes (Quadrangulação): {origem_pq} ↔ {destino_pq}")

            if pecas_q:
                st.warning(f"**{len(pecas_q)}** quadrangulações quase completas — falta 1 magistrado para fechar o ciclo de 4!")

                for i, peca in enumerate(pecas_q, 1):
                    with st.expander(f"🧩 Quase completa {i}: {peca['sequencia']}"):
                        st.write(f"**Sequência:** {peca['sequencia']}")
                        st.markdown(
                            f"""
                            <div style="background-color: #fff3cd; border-radius: 8px; padding: 12px; border-left: 4px solid #ffc107; margin: 10px 0;">
                                <strong>⚠️ Falta:</strong> {peca['falta']}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        st.write("**Magistrados já encaixados:**")
                        for j, mag in enumerate(peca['magistrados']):
                            exibir_magistrado(mag)
                            if j < len(peca['magistrados']) - 1:
                                st.write("⬇️")

                        # Botão compartilhar WhatsApp
                        msg_whats = (
                            f"🧩 *Permutatum — Quadrangulação quase completa*\n\n"
                            f"Sequência: *{peca['sequencia']}*\n"
                            f"⚠️ *{peca['falta']}*\n\n"
                            f"Já estão encaixados 3 magistrados. "
                            f"Falta apenas 1 para fechar o ciclo de 4!\n\n"
                            f"Cadastre-se: 👉 https://permutatum.streamlit.app/"
                        )
                        link_wpp = gerar_link_whatsapp(msg_whats)
                        st.markdown(
                            f"""
                            <a href="{link_wpp}" target="_blank" style="
                                display: inline-block;
                                background-color: #25D366;
                                color: white;
                                padding: 8px 16px;
                                border-radius: 8px;
                                text-decoration: none;
                                font-size: 14px;
                                font-weight: 500;
                            ">📲 Compartilhar no WhatsApp</a>
                            """,
                            unsafe_allow_html=True,
                        )
            else:
                st.info(f"Nenhuma quadrangulação incompleta encontrada entre {origem_pq} e {destino_pq}.")

            if st.button("🔄 Nova busca de peças (quadrangulação)", key="btn_pecas_quad_reset"):
                st.session_state["pecas_quad"] = None
                st.rerun()

    with tab2:
        st.subheader("🔎 Pares Aguardando Match")
        st.markdown(
            """
            <div style="background-color: #fdf6ec; border-radius: 10px; padding: 18px 22px; margin-bottom: 20px; border: 1px solid #f0e0c0;">
                <p style="margin: 0 0 12px 0; font-size: 15px; color: #333;">
                    <strong>O que são pares aguardando match?</strong>
                </p>
                <p style="margin: 0 0 10px 0; font-size: 14px; color: #555;">
                    São magistrados que cadastraram interesse em permutar, mas <strong>ainda não existe ninguém</strong>
                    no tribunal de destino desejado que queira vir para o tribunal deles.
                </p>
                <p style="margin: 0 0 8px 0; font-size: 14px; color: #555;">
                    <strong>Exemplo:</strong> Um magistrado do <strong>TJGO</strong> deseja ir para o <strong>TJBA</strong>,
                    mas nenhum magistrado do TJBA cadastrou o TJGO como destino.
                    O par está incompleto — falta o outro lado.
                </p>
                <p style="margin: 0; font-size: 13px; color: #888;">
                    💡 <em>Se você conhece alguém no tribunal indicado, compartilhe o Permutatum!
                    Um novo cadastro pode completar o par.</em>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        sem_par = buscar_pares_aguardando(dados)

        if sem_par:
            # Filtros
            col_f1, col_f2 = st.columns(2)
            origens_unicas = sorted(set(str(s['origem']).strip() for s in sem_par if s.get('origem')))
            destinos_unicos = sorted(set(str(s['destino_desejado']).strip() for s in sem_par if s.get('destino_desejado')))
            with col_f1:
                filtro_origem_par = st.selectbox(
                    "Filtrar por tribunal de origem:",
                    options=["Todos"] + origens_unicas,
                    key="filtro_origem_par"
                )
            with col_f2:
                filtro_destino_par = st.selectbox(
                    "Filtrar por destino desejado:",
                    options=["Todos"] + destinos_unicos,
                    key="filtro_destino_par"
                )

            # Aplicar filtros
            filtrados = sem_par
            if filtro_origem_par != "Todos":
                filtrados = [s for s in filtrados if str(s['origem']).strip() == filtro_origem_par]
            if filtro_destino_par != "Todos":
                filtrados = [s for s in filtrados if str(s['destino_desejado']).strip() == filtro_destino_par]

            st.success(f"**{len(filtrados)}** magistrados aguardando par (de {len(sem_par)} no total)")

            st.markdown("---")

            # Agrupar por rota (origem → destino)
            rotas = {}
            for item in filtrados:
                rota = f"{item['origem']} → {item['destino_desejado']}"
                if rota not in rotas:
                    rotas[rota] = []
                rotas[rota].append(item)

            # Ordenar por quantidade (mais magistrados primeiro)
            rotas_ordenadas = sorted(rotas.items(), key=lambda x: len(x[1]), reverse=True)

            for idx_rota, (rota, magistrados_rota) in enumerate(rotas_ordenadas):
                with st.expander(f"🔸 {rota} — {len(magistrados_rota)} magistrado(s) aguardando"):
                    st.warning(f"**Falta:** {magistrados_rota[0]['falta']}")
                    for item in magistrados_rota:
                        exibir_magistrado(item['magistrado'])
                        st.markdown("---")

                    # Botão compartilhar WhatsApp
                    msg_whats = (
                        f"🔍 *Permutatum — Par aguardando match*\n\n"
                        f"Rota: *{rota}*\n"
                        f"Há *{len(magistrados_rota)}* magistrado(s) do {magistrados_rota[0]['origem']} "
                        f"querendo ir para o {magistrados_rota[0]['destino_desejado']}, "
                        f"mas ninguém do {magistrados_rota[0]['destino_desejado']} cadastrou interesse "
                        f"no {magistrados_rota[0]['origem']}.\n\n"
                        f"Conhece alguém do {magistrados_rota[0]['destino_desejado']}? "
                        f"Compartilhe o Permutatum!\n\n"
                        f"👉 https://permutatum.streamlit.app/"
                    )
                    link_wpp = gerar_link_whatsapp(msg_whats)
                    st.markdown(
                        f"""
                        <a href="{link_wpp}" target="_blank" style="
                            display: inline-block;
                            background-color: #25D366;
                            color: white;
                            padding: 8px 16px;
                            border-radius: 8px;
                            text-decoration: none;
                            font-size: 14px;
                            font-weight: 500;
                        ">📲 Compartilhar no WhatsApp</a>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            st.success("🎉 Todos os magistrados possuem ao menos um par potencial!")

    with tab3:
        st.subheader("📊 Novos Cadastros")
        st.write("Magistrados cadastrados recentemente no sistema.")

        # Seletor de período
        periodo = st.selectbox(
            "Período:",
            options=[30, 60, 90],
            index=1,
            format_func=lambda x: f"Últimos {x} dias",
            key="periodo_novos"
        )

        novos = buscar_novos_cadastros(dias=periodo)

        if not novos:
            st.info(f"Nenhum novo cadastro nos últimos {periodo} dias.")
        else:
            st.success(f"**{len(novos)}** novos cadastros nos últimos {periodo} dias")

            # ── Estatísticas resumidas ──
            st.markdown("---")

            df = pd.DataFrame(novos)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total de novos", len(novos))

            with col2:
                origem_top = df["origem"].value_counts()
                if not origem_top.empty:
                    st.metric("Origem mais frequente", origem_top.index[0], f"{origem_top.iloc[0]} magistrados")

            with col3:
                destino_top = df["destino_1"].value_counts()
                if not destino_top.empty:
                    st.metric("Destino mais procurado", destino_top.index[0], f"{destino_top.iloc[0]} magistrados")

            st.markdown("---")

            # ── Gráficos lado a lado ──
            col_g1, col_g2 = st.columns(2)

            with col_g1:
                st.markdown("**Por Tribunal de Origem**")
                origem_counts = df["origem"].value_counts().reset_index()
                origem_counts.columns = ["Tribunal", "Quantidade"]
                st.bar_chart(origem_counts.set_index("Tribunal"))

            with col_g2:
                st.markdown("**Por 1º Destino Desejado**")
                destino_counts = df["destino_1"].value_counts().reset_index()
                destino_counts.columns = ["Tribunal", "Quantidade"]
                st.bar_chart(destino_counts.set_index("Tribunal"))

            st.markdown("---")

            # ── Tabela de cadastros recentes ──
            st.markdown("**Lista de novos cadastros**")

            dados_exibir = []
            for item in novos:
                data_raw = item.get("created_at", "")
                try:
                    dt = datetime.fromisoformat(data_raw.replace("Z", "+00:00"))
                    data_formatada = dt.strftime("%d/%m/%Y")
                except Exception:
                    data_formatada = data_raw[:10] if data_raw else "-"

                destinos = item.get("destino_1", "-")
                if item.get("destino_2"):
                    destinos += f", {item['destino_2']}"
                if item.get("destino_3"):
                    destinos += f", {item['destino_3']}"

                dados_exibir.append({
                    "Nome": item.get("nome", "-"),
                    "Entrância": item.get("entrancia", "-"),
                    "Origem": item.get("origem", "-"),
                    "Destinos": destinos,
                    "Cadastro": data_formatada,
                })

            df_exibir = pd.DataFrame(dados_exibir)

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_origem = st.multiselect(
                    "Filtrar por origem:",
                    options=sorted(df["origem"].unique()),
                    key="filtro_origem_novos"
                )
            with col_f2:
                filtro_destino = st.multiselect(
                    "Filtrar por destino:",
                    options=sorted(df["destino_1"].unique()),
                    key="filtro_destino_novos"
                )

            df_filtrado = df_exibir.copy()
            if filtro_origem:
                df_filtrado = df_filtrado[df_filtrado["Origem"].isin(filtro_origem)]
            if filtro_destino:
                df_filtrado = df_filtrado[df_filtrado["Destinos"].apply(
                    lambda x: any(d in x for d in filtro_destino)
                )]

            st.dataframe(
                df_filtrado,
                use_container_width=True,
                hide_index=True,
            )

            st.caption(f"Exibindo {len(df_filtrado)} de {len(novos)} cadastros")

    with tab4:
        st.subheader(f"Magistrados interessados em vir para o {usuario.get('origem')}")

        interessados = buscar_interessados(usuario.get('origem'), dados)

        if interessados:
            for item in interessados:
                with st.container():
                    exibir_magistrado(item['magistrado'], item['prioridade'])
                    st.markdown("---")
        else:
            st.info("Nenhum magistrado demonstrou interesse em seu tribunal ainda.")

    with tab5:
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

    with tab6:
        st.subheader("⚙️ Gerenciar Meus Dados")

        def anonimizar_email(email):
            """Mascara parcialmente o email: mar****@gmail.com"""
            if not email or "@" not in email:
                return email
            local, dominio = email.split("@", 1)
            if len(local) <= 3:
                mascarado = local[0] + "****"
            else:
                mascarado = local[:3] + "****"
            return f"{mascarado}@{dominio}"

        # ── Verificação de identidade via OTP ──
        if "gerenciar_otp_verificado" not in st.session_state:
            st.session_state["gerenciar_otp_verificado"] = False
        if "gerenciar_otp_enviado" not in st.session_state:
            st.session_state["gerenciar_otp_enviado"] = False

        if not st.session_state["gerenciar_otp_verificado"]:
            st.warning("🔐 Para sua segurança, confirme sua identidade antes de editar seus dados.")

            email_usuario = usuario.get('email', '')

            if not st.session_state["gerenciar_otp_enviado"]:
                st.info(f"Enviaremos um código de verificação para: **{anonimizar_email(email_usuario)}**")

                if st.button("📨 Enviar código de verificação", key="btn_enviar_otp_gerenciar", use_container_width=True, type="primary"):
                    supabase_conn = init_supabase()
                    if supabase_conn:
                        resultado = enviar_codigo_otp(supabase_conn, email_usuario)
                        if resultado["sucesso"]:
                            st.session_state["gerenciar_otp_enviado"] = True
                            st.session_state["gerenciar_otp_email"] = email_usuario
                            st.success(f"✅ {resultado['mensagem']}")
                            st.rerun()
                        else:
                            st.error(f"❌ {resultado['mensagem']}")
            else:
                email_otp = st.session_state.get("gerenciar_otp_email", email_usuario)
                st.info(f"📧 Código enviado para: **{anonimizar_email(email_otp)}**")

                codigo = st.text_input(
                    "Digite o código de 6 dígitos",
                    max_chars=6,
                    placeholder="123456",
                    key="input_otp_gerenciar",
                )

                col_v1, col_v2 = st.columns(2)

                with col_v1:
                    if st.button("✅ Verificar código", key="btn_verificar_otp_gerenciar", use_container_width=True, type="primary"):
                        if not codigo.strip():
                            st.error("❌ Digite o código.")
                        elif len(codigo.strip()) != 6 or not codigo.strip().isdigit():
                            st.error("❌ O código deve ter exatamente 6 dígitos numéricos.")
                        else:
                            supabase_conn = init_supabase()
                            if supabase_conn:
                                resultado = verificar_codigo_otp(supabase_conn, email_otp, codigo)
                                if resultado["sucesso"]:
                                    st.session_state["gerenciar_otp_verificado"] = True
                                    st.success("✅ Identidade confirmada!")
                                    import time
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ {resultado['mensagem']}")

                with col_v2:
                    if st.button("🔄 Reenviar código", key="btn_reenviar_otp_gerenciar", use_container_width=True):
                        supabase_conn = init_supabase()
                        if supabase_conn:
                            resultado = enviar_codigo_otp(supabase_conn, email_otp)
                            if resultado["sucesso"]:
                                st.success("✅ Novo código enviado!")
                            else:
                                st.error(f"❌ {resultado['mensagem']}")

                st.markdown("---")
                if st.button("◀️ Cancelar", key="btn_cancelar_otp_gerenciar"):
                    st.session_state["gerenciar_otp_enviado"] = False
                    st.rerun()

        else:
            # ── OTP verificado — mostrar formulário de edição/exclusão ──
            st.success("✅ Identidade confirmada")

            opcao = st.radio(
                "Escolha uma opção:",
                ["✏️ Editar meus dados", "🗑️ Excluir meu cadastro"],
                horizontal=True,
                key="radio_gerenciar"
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
                        telefone_visivel_novo = st.checkbox(
                            "Tornar meu telefone visível para outros magistrados",
                            value=usuario.get('telefone_visivel', True),
                            help="Se desmarcado, apenas seu email será exibido como forma de contato",
                        )

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
                        usuario_id = usuario_atual.get('id')

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
                                "telefone": telefone_novo.strip(),
                                "telefone_visivel": telefone_visivel_novo,
                            }

                            sucesso, mensagem = atualizar_magistrado(usuario_id, dados_atualizados)

                            if sucesso:
                                st.success("✅ " + mensagem)
                                st.cache_data.clear()
                                # ── Gerar notificações de match após edição ──
                                try:
                                    supabase_notif = init_supabase()
                                    if supabase_notif:
                                        todos = supabase_notif.table("magistrados").select("*").eq("status", "ativo").execute()
                                        if todos.data:
                                            novo_origem = dados_atualizados.get('origem', '')
                                            novo_destino_1 = dados_atualizados.get('destino_1', '')
                                            novo_email = dados_atualizados.get('email', '')
                                            novo_nome = dados_atualizados.get('nome', '')

                                            for mag in todos.data:
                                                if mag.get('email', '').lower() == novo_email.lower():
                                                    continue

                                                mag_origem = mag.get('origem', '')
                                                mag_destino_1 = mag.get('destino_1', '')

                                                if mag_origem == novo_destino_1 and mag_destino_1 == novo_origem:
                                                    # Verificar se já existe notificação igual não lida para evitar duplicatas
                                                    existente = supabase_notif.table("notificacoes").select("id").eq(
                                                        "email_destino", mag.get('email', '')
                                                    ).eq("lida", False).ilike(
                                                        "mensagem", f"%{novo_nome}%"
                                                    ).execute()

                                                    if not existente.data:
                                                        supabase_notif.table("notificacoes").insert({
                                                            "email_destino": mag.get('email', ''),
                                                            "tipo": "permuta_direta",
                                                            "mensagem": f"Novo match! {novo_nome} ({novo_origem}) atualizou dados — destino {novo_destino_1}, permuta direta possível!",
                                                            "detalhes": f"Confira na aba 'Busca de Permuta' selecionando {mag_origem} → {novo_origem}."
                                                        }).execute()

                                                    # Notificar também quem editou
                                                    existente2 = supabase_notif.table("notificacoes").select("id").eq(
                                                        "email_destino", novo_email
                                                    ).eq("lida", False).ilike(
                                                        "mensagem", f"%{mag.get('nome', '')}%"
                                                    ).execute()

                                                    if not existente2.data:
                                                        supabase_notif.table("notificacoes").insert({
                                                            "email_destino": novo_email,
                                                            "tipo": "permuta_direta",
                                                            "mensagem": f"Boa notícia! {mag.get('nome', '')} ({mag_origem}) quer ir para {mag_destino_1} — permuta direta possível!",
                                                            "detalhes": f"Confira na aba 'Busca de Permuta' selecionando {novo_origem} → {novo_destino_1}."
                                                        }).execute()
                                except:
                                    pass  # Não bloquear a edição por erro de notificação
                                usuario_atualizado = verificar_email(email_novo.strip().lower())
                                if usuario_atualizado:
                                    st.session_state.usuario_autenticado = usuario_atualizado
                                st.info("Dados atualizados. A página será recarregada.")
                                import time
                                time.sleep(1)
                                st.rerun()
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
                    placeholder="Digite EXCLUIR para confirmar",
                    key="input_confirmar_exclusao"
                )

                if st.button("🗑️ Confirmar Exclusão", type="secondary", key="btn_confirmar_exclusao"):
                    if confirmar_exclusao == "EXCLUIR":
                        sucesso, mensagem = excluir_magistrado(usuario.get('id'))

                        if sucesso:
                            st.success(mensagem)
                            st.info("Você será deslogado em 3 segundos...")
                            import time
                            time.sleep(3)
                            st.session_state.usuario_autenticado = None
                            st.session_state["gerenciar_otp_verificado"] = False
                            st.session_state["gerenciar_otp_enviado"] = False
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(mensagem)
                    else:
                        st.error("Confirmação incorreta. Digite exatamente 'EXCLUIR' para prosseguir.")

            # Botão para sair da área protegida
            st.markdown("---")
            if st.button("🔒 Bloquear edição", key="btn_bloquear_edicao"):
                st.session_state["gerenciar_otp_verificado"] = False
                st.session_state["gerenciar_otp_enviado"] = False
                st.rerun()
    
    # Botão para sair
    st.markdown("---")
    if st.button("🚪 Sair do sistema"):
        st.session_state.usuario_autenticado = None
        st.session_state["gerenciar_otp_verificado"] = False
        st.session_state["gerenciar_otp_enviado"] = False
        st.session_state["gerenciar_otp_email"] = ""
        st.rerun()
# Rodapé
st.markdown(f"""
<div style="text-align: center; padding: 20px 0;">
    <p style="margin: 5px 0; font-style: italic; font-family: 'Times New Roman', serif; font-size: 16px;">
        <em>Permutatum</em>
    </p>
    <p style="margin: 5px 0; font-size: 13px; color: #888;">
        Castro/PR — {datetime.now().year}
    </p>
</div>
""", unsafe_allow_html=True)
