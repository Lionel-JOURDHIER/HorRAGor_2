"""
Composants d'authentification pour l'interface Streamlit de HorRAGor.

Fonctions :
    - render_login_page : Page de connexion/inscription
    - check_authentication : Vérifier si l'utilisateur est connecté
    - logout_button : Bouton de déconnexion
"""

import streamlit as st
from utils.auth_client import login_user, register_user, get_current_user, logout_user as api_logout


def check_authentication() -> bool:
    """
    Vérifie si l'utilisateur est authentifié.
    
    Returns:
        True si l'utilisateur est connecté, False sinon
    """
    if "access_token" not in st.session_state:
        return False
    
    if "user" not in st.session_state:
        return False
    
    return True


def logout_button():
    """
    Affiche un bouton de déconnexion dans la sidebar.
    """
    if check_authentication():
        with st.sidebar:
            st.divider()
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"👤 **{st.session_state['user']['username']}**")
            
            with col2:
                if st.button("🚪", help="Se déconnecter"):
                    # Appeler l'API de déconnexion
                    api_logout(
                        st.session_state.get("refresh_token", ""),
                        st.session_state.get("access_token", "")
                    )
                    
                    # Nettoyer la session
                    for key in ["access_token", "refresh_token", "user"]:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    st.rerun()


def render_login_page():
    """
    Affiche la page de connexion/inscription.
    """
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Creepster&family=Poppins:wght@300;400;600;700&display=swap');
            
            .auth-container {
                background: linear-gradient(135deg, #0a0e27 0%, #1a0b2e 50%, #16003b 100%);
                padding: 3rem;
                border-radius: 25px;
                box-shadow: 0 10px 40px rgba(255, 71, 87, 0.3);
                border: 2px solid rgba(255, 71, 87, 0.5);
                margin: 2rem auto;
                max-width: 500px;
            }
            
            .auth-title {
                font-family: 'Creepster', cursive;
                font-size: 3.5rem;
                color: #ff4757;
                text-align: center;
                text-shadow: 0 0 20px rgba(255, 71, 87, 0.5), 0 0 40px rgba(255, 71, 87, 0.3);
                margin-bottom: 2rem;
                animation: glow 2s ease-in-out infinite alternate;
            }
            
            @keyframes glow {
                from {
                    text-shadow: 0 0 20px rgba(255, 71, 87, 0.5), 0 0 40px rgba(255, 71, 87, 0.3);
                }
                to {
                    text-shadow: 0 0 30px rgba(255, 71, 87, 0.8), 0 0 60px rgba(255, 71, 87, 0.5);
                }
            }
            
            .subtitle {
                font-family: 'Poppins', sans-serif;
                text-align: center;
                color: #c7ecee;
                font-size: 1.2rem;
                margin-bottom: 2rem;
            }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown('<h1 class="auth-title">🎬 HorRAGor 🎬</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Votre chatbot d\'horreur préféré</p>', unsafe_allow_html=True)
    
    # Tabs pour connexion et inscription
    tab1, tab2 = st.tabs(["🔐 Connexion", "📝 Inscription"])
    
    with tab1:
        render_login_form()
    
    with tab2:
        render_register_form()


def render_login_form():
    """
    Affiche le formulaire de connexion.
    """
    with st.form("login_form"):
        st.subheader("Se connecter")
        
        email = st.text_input("📧 Email", placeholder="votre.email@exemple.com")
        password = st.text_input("🔒 Mot de passe", type="password", placeholder="••••••••")
        
        submit = st.form_submit_button("🚀 Connexion", use_container_width=True)
        
        if submit:
            if not email or not password:
                st.error("❌ Veuillez remplir tous les champs")
                return
            
            with st.spinner("🔄 Connexion en cours..."):
                result = login_user(email, password)
            
            if result:
                st.session_state["access_token"] = result["access_token"]
                st.session_state["refresh_token"] = result["refresh_token"]
                st.session_state["user"] = result["user"]
                
                st.success(f"✅ Bienvenue {result['user']['username']} !")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Email ou mot de passe incorrect")


def render_register_form():
    """
    Affiche le formulaire d'inscription.
    """
    with st.form("register_form"):
        st.subheader("Créer un compte")
        
        email = st.text_input("📧 Email", placeholder="votre.email@exemple.com")
        username = st.text_input("👤 Nom d'utilisateur", placeholder="VotreNom")
        password = st.text_input("🔒 Mot de passe", type="password", placeholder="••••••••")
        password_confirm = st.text_input("🔒 Confirmer le mot de passe", type="password", placeholder="••••••••")
        
        submit = st.form_submit_button("📝 S'inscrire", use_container_width=True)
        
        if submit:
            # Validation
            if not email or not username or not password or not password_confirm:
                st.error("❌ Veuillez remplir tous les champs")
                return
            
            if password != password_confirm:
                st.error("❌ Les mots de passe ne correspondent pas")
                return
            
            if len(password) < 8:
                st.error("❌ Le mot de passe doit contenir au moins 8 caractères")
                return
            
            if len(username) < 3:
                st.error("❌ Le nom d'utilisateur doit contenir au moins 3 caractères")
                return
            
            with st.spinner("🔄 Création du compte..."):
                result = register_user(email, username, password)
            
            if result:
                st.session_state["access_token"] = result["access_token"]
                st.session_state["refresh_token"] = result["refresh_token"]
                st.session_state["user"] = result["user"]
                
                st.success(f"✅ Compte créé ! Bienvenue {result['user']['username']} !")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Erreur lors de la création du compte. L'email ou le nom d'utilisateur existe peut-être déjà.")
