# config/firebase_config.py
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials

# Solo carga .env en desarrollo (Render no lo necesita)
if os.getenv("RENDER") is None:
    load_dotenv()

def get_firebase_credentials():
    # 🌐 Opción 1: Producción (Render) - JSON desde variable de entorno
    cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if cred_json:
        try:
            cred_dict = json.loads(cred_json)
            return credentials.Certificate(cred_dict)
        except json.JSONDecodeError as e:
            raise ValueError(f"🔥 FIREBASE_CREDENTIALS_JSON malformado: {e}")

    # 💻 Opción 2: Local - Archivo físico
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "./firebase-service-account.json")
    abs_path = Path(cred_path).resolve()
    if abs_path.exists():
        return credentials.Certificate(str(abs_path))

    raise RuntimeError("❌ Credenciales de Firebase no encontradas. Configura FIREBASE_CREDENTIALS_JSON (prod) o FIREBASE_CREDENTIALS_PATH (local).")

# Inicialización segura (maneja --reload en local)
try:
    cred = get_firebase_credentials()
    firebase_admin.initialize_app(cred)
    print("✅ Firebase Admin SDK inicializado correctamente")
except ValueError:
    pass  # Ya inicializado (ocurre con uvicorn --reload)