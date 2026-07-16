import os

class Config:
    SECRET_KEY = 'clave-super-secreta-para-session'
    
    # ===== BASE DE DATOS =====
    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASSWORD = 'morena12345'
    DB_NAME = 'chinos_cafe'
    DB_PORT = 3307
    
    # ===== CORREO CON GMAIL (ENVÍO REAL) =====
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'chinoscafesa@gmail.com'
    MAIL_PASSWORD = 'yejh tvtq lzta miaz'
    
    # ===== DIRECTORIOS PARA JSON =====
    JSON_ORDERS_DIR = 'json_orders'
    JSON_PAYMENTS_DIR = 'json_payments'
    
    # ===== COSTO DE ENVÍO FIJO =====
    ENVIO_COSTO = 3.00