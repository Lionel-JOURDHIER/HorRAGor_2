"""
Script de test pour vérifier le système d'authentification.
"""

import requests
import time

API_URL = "http://localhost:8000"

def test_auth_system():
    """Test complet du système d'authentification."""
    
    print("🧪 === Test du système d'authentification ===\n")
    
    # 1. Test de santé de l'API
    print("1️⃣ Test de santé de l'API...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ API accessible\n")
        else:
            print(f"   ❌ API retourne code {response.status_code}\n")
            return
    except Exception as e:
        print(f"   ❌ Impossible de joindre l'API : {e}")
        print("   💡 Assurez-vous que l'API est démarrée : cd api && uvicorn main:app --reload\n")
        return
    
    # 2. Test d'inscription
    print("2️⃣ Test d'inscription...")
    test_email = f"test_{int(time.time())}@horragor.com"
    test_username = f"testuser_{int(time.time())}"
    test_password = "TestPass123!"
    
    register_data = {
        "email": test_email,
        "username": test_username,
        "password": test_password
    }
    
    try:
        response = requests.post(f"{API_URL}/auth/register", json=register_data, timeout=10)
        
        if response.status_code == 201:
            data = response.json()
            print(f"   ✅ Inscription réussie")
            print(f"   👤 Utilisateur : {data['user']['username']}")
            print(f"   📧 Email : {data['user']['email']}")
            print(f"   🔑 Access token reçu : {data['access_token'][:20]}...")
            print(f"   🔄 Refresh token reçu : {data['refresh_token'][:20]}...\n")
            
            access_token = data['access_token']
            refresh_token = data['refresh_token']
        else:
            print(f"   ❌ Échec de l'inscription : {response.status_code}")
            print(f"   {response.text}\n")
            return
    except Exception as e:
        print(f"   ❌ Erreur lors de l'inscription : {e}\n")
        return
    
    # 3. Test de récupération du profil
    print("3️⃣ Test de récupération du profil...")
    try:
        response = requests.get(
            f"{API_URL}/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Profil récupéré avec succès")
            print(f"   ID : {data['id']}")
            print(f"   Username : {data['username']}")
            print(f"   Email : {data['email']}\n")
        else:
            print(f"   ❌ Échec de la récupération du profil : {response.status_code}\n")
    except Exception as e:
        print(f"   ❌ Erreur lors de la récupération du profil : {e}\n")
    
    # 4. Test de rafraîchissement du token
    print("4️⃣ Test de rafraîchissement du token...")
    try:
        response = requests.post(
            f"{API_URL}/auth/refresh",
            json={"refresh_token": refresh_token},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Token rafraîchi avec succès")
            print(f"   🔑 Nouveau access token : {data['access_token'][:20]}...")
            print(f"   🔄 Nouveau refresh token : {data['refresh_token'][:20]}...\n")
            
            new_access_token = data['access_token']
            new_refresh_token = data['refresh_token']
        else:
            print(f"   ❌ Échec du rafraîchissement : {response.status_code}\n")
            new_access_token = access_token
            new_refresh_token = refresh_token
    except Exception as e:
        print(f"   ❌ Erreur lors du rafraîchissement : {e}\n")
        new_access_token = access_token
        new_refresh_token = refresh_token
    
    # 5. Test de connexion
    print("5️⃣ Test de connexion avec le compte créé...")
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            json={"email": test_email, "password": test_password},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Connexion réussie")
            print(f"   👤 Bienvenue {data['user']['username']} !\n")
        else:
            print(f"   ❌ Échec de la connexion : {response.status_code}\n")
    except Exception as e:
        print(f"   ❌ Erreur lors de la connexion : {e}\n")
    
    # 6. Test de déconnexion
    print("6️⃣ Test de déconnexion...")
    try:
        response = requests.post(
            f"{API_URL}/auth/logout",
            json={"refresh_token": new_refresh_token},
            headers={"Authorization": f"Bearer {new_access_token}"},
            timeout=10
        )
        
        if response.status_code == 204:
            print(f"   ✅ Déconnexion réussie\n")
        else:
            print(f"   ❌ Échec de la déconnexion : {response.status_code}\n")
    except Exception as e:
        print(f"   ❌ Erreur lors de la déconnexion : {e}\n")
    
    print("🎉 === Tests terminés ===")
    print("\n💡 Prochaines étapes :")
    print("   1. Démarrer le frontend : cd frontend && streamlit run app.py")
    print("   2. Ouvrir http://localhost:8501")
    print("   3. Tester la connexion via l'interface graphique\n")


if __name__ == "__main__":
    test_auth_system()
