"""
Módulo de autenticação via Supabase Auth com OTP (código por email).
Sistema Permutatum - Permutas entre magistrados.
Versão 4 - OTP por código numérico (substitui Magic Link).
"""

import streamlit as st


# Domínios válidos dos 27 Tribunais de Justiça estaduais
DOMINIOS_VALIDOS = {
    "tjac.jus.br", "tjal.jus.br", "tjap.jus.br", "tjam.jus.br",
    "tjba.jus.br", "tjce.jus.br", "tjdft.jus.br", "tjes.jus.br",
    "tjgo.jus.br", "tjma.jus.br", "tjmt.jus.br", "tjms.jus.br",
    "tjmg.jus.br", "tjpa.jus.br", "tjpb.jus.br", "tjpr.jus.br",
    "tjpe.jus.br", "tjpi.jus.br", "tjrj.jus.br", "tjrn.jus.br",
    "tjrs.jus.br", "tjro.jus.br", "tjrr.jus.br", "tjsc.jus.br",
    "tjse.jus.br", "tjsp.jus.br", "tjto.jus.br",
}


def validar_email_magistrado(email: str) -> bool:
    """Valida se o email pertence a um domínio funcional de tribunal estadual."""
    if not email or "@" not in email:
        return False
    dominio = email.strip().lower().split("@")[-1]
    return dominio in DOMINIOS_VALIDOS


def enviar_codigo_otp(supabase, email: str) -> dict:
    """
    Envia código OTP de 6 dígitos para o email do magistrado.
    Usa Supabase Auth sign_in_with_otp SEM redirect (gera código, não link).
    """
    try:
        supabase.auth.sign_in_with_otp({
            "email": email.strip().lower(),
            "options": {
                "should_create_user": True,
            }
        })
        return {
            "sucesso": True,
            "mensagem": f"Código de verificação enviado para {email.strip().lower()}. Verifique sua caixa de entrada (e spam).",
        }
    except Exception as e:
        return {
            "sucesso": False,
            "mensagem": f"Erro ao enviar código: {str(e)}",
        }


def verificar_codigo_otp(supabase, email: str, codigo: str) -> dict:
    """
    Verifica o código OTP digitado pelo magistrado.
    Retorna dados do usuário autenticado se o código for válido.
    """
    try:
        response = supabase.auth.verify_otp({
            "email": email.strip().lower(),
            "token": codigo.strip(),
            "type": "email",
        })

        if response and response.user:
            dados_usuario = {
                "user_id": response.user.id,
                "email": response.user.email,
            }
            # Salvar na sessão do Streamlit
            st.session_state["usuario_auth"] = dados_usuario
            return {
                "sucesso": True,
                "mensagem": "Autenticação realizada com sucesso!",
                "usuario": dados_usuario,
            }
        else:
            return {
                "sucesso": False,
                "mensagem": "Código inválido ou expirado. Tente novamente.",
            }
    except Exception as e:
        erro_str = str(e).lower()
        if "expired" in erro_str or "invalid" in erro_str:
            return {
                "sucesso": False,
                "mensagem": "Código inválido ou expirado. Solicite um novo código.",
            }
        return {
            "sucesso": False,
            "mensagem": f"Erro na verificação: {str(e)}",
        }


def obter_usuario_logado(supabase=None) -> dict | None:
    """
    Obtém os dados do usuário autenticado da sessão Streamlit.
    Com OTP, não precisa mais processar callbacks de URL.
    """
    return st.session_state.get("usuario_auth")


def verificar_autenticacao() -> dict | None:
    """Verifica se existe um usuário autenticado na sessão Streamlit."""
    return st.session_state.get("usuario_auth")


def fazer_logout(supabase=None) -> dict:
    """Desloga o usuário e limpa a sessão Streamlit."""
    try:
        if supabase:
            supabase.auth.sign_out()
    except Exception:
        pass

    # Limpar dados de autenticação da sessão
    chaves_auth = [
        k for k in list(st.session_state.keys())
        if k.startswith("usuario") or k.startswith("supabase") or k.startswith("otp_")
    ]
    for chave in chaves_auth:
        del st.session_state[chave]

    return {
        "sucesso": True,
        "mensagem": "Logout realizado com sucesso.",
    }
