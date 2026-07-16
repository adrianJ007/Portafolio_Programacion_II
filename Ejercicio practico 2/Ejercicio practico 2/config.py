import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-segura-para-desarrollo'
    
    # Base de datos principal (SQLite local)
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:morena12345@localhost:3307/chiriqui_main'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Base de datos réplica (otro archivo SQLite, pero puede cambiarse a MySQL/VM luego)
    REPLICA_DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'chiriqui_replica.db')
    
    # Configuración de correo (cambiar por datos reales o usar MailHog)
    MAIL_SERVER = 'smtp.gmail.com'          # O 'localhost' si pruebas con MailHog
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'chiriquieatss.a.507@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'ztwc wzqe bewi eoid')  # ¡Cuidado! No dejes esto en producción
    MAIL_DEFAULT_SENDER = MAIL_USERNAME