import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-this-key")
    DATA_DIR = BASE_DIR / "data"
    UPLOAD_DIR = BASE_DIR / "uploads"
    JSON_EXPORT_DIR = BASE_DIR / "json_exports"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024

    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "")
    MAIL_DEFAULT_SENDER_NAME = os.getenv("MAIL_DEFAULT_SENDER_NAME", "Turismo Chiriquí")
    MAIL_ADMIN_RECEIVER = os.getenv("MAIL_ADMIN_RECEIVER", "")

    # --- Backend de persistencia -------------------------------------------------
    # json (por defecto) | mariadb | mongodb | firebase
    # Cambiar SOLO esta variable en .env cambia el motor de datos de toda la
    # aplicación; storage_service.py es el único archivo que la lee.
    DATABASE_BACKEND = os.getenv("DATABASE_BACKEND", "json").lower()

    # MariaDB (usado si DATABASE_BACKEND=mariadb; ver schema.sql)
    MARIADB_HOST = os.getenv("MARIADB_HOST", "localhost")
    MARIADB_PORT = int(os.getenv("MARIADB_PORT", "3306"))
    MARIADB_USER = os.getenv("MARIADB_USER", "root")
    MARIADB_PASSWORD = os.getenv("MARIADB_PASSWORD", "")
    MARIADB_DATABASE = os.getenv("MARIADB_DATABASE", "turismo_chiriqui")

    # MongoDB (usado si DATABASE_BACKEND=mongodb)
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "turismo_chiriqui")

    # Espejo en tiempo real MariaDB -> MongoDB (independiente de DATABASE_BACKEND).
    # En "false" por defecto: si no lo activas explícitamente en el .env, la app
    # se comporta exactamente igual que antes, sin tocar Mongo para nada.
    MONGO_MIRROR_ENABLED = os.getenv("MONGO_MIRROR_ENABLED", "false").lower() == "true"

    # Firebase Firestore (usado si DATABASE_BACKEND=firebase)
    _firebase_creds_raw = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    # Si la ruta viene relativa (ej. "secrets/firebase-service-account.json"),
    # se resuelve contra la carpeta del proyecto (BASE_DIR), sin importar desde
    # qué carpeta se ejecute `python run.py`. Si ya viene absoluta, se respeta tal cual.
    FIREBASE_CREDENTIALS_PATH = (
        str(BASE_DIR / _firebase_creds_raw) if _firebase_creds_raw and not os.path.isabs(_firebase_creds_raw) else _firebase_creds_raw
    )
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")

    # Espejo en tiempo real MariaDB -> Firebase (independiente de DATABASE_BACKEND
    # y de MONGO_MIRROR_ENABLED; puedes prender uno sin el otro). En "false" por
    # defecto: si no lo activas, la app no toca Firebase para nada.
    FIREBASE_MIRROR_ENABLED = os.getenv("FIREBASE_MIRROR_ENABLED", "false").lower() == "true"