import sqlite3
import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

# ------------------------------------------------------------------
# Modelos para la base de datos principal
# ------------------------------------------------------------------
class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    
    combos = db.relationship('Combo', backref='company', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address
        }

class Combo(db.Model):
    __tablename__ = 'combos'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    items = db.Column(db.String(500))   # nuevo: lista de comidas separadas por coma
    price = db.Column(db.Float, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'items': self.items,
            'price': self.price,
            'company_id': self.company_id
        }

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='PENDIENTE')  # PENDIENTE o PAGADO
    created_at = db.Column(db.DateTime, default=datetime.now)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    combo_id = db.Column(db.Integer, db.ForeignKey('combos.id'), nullable=False)
    transaction_id = db.Column(db.String(100), nullable=True)
    
    company = db.relationship('Company')
    combo = db.relationship('Combo')
    confirmed = db.Column(db.Boolean, default=False)  # Nuevo campo
    confirmation_token = db.Column(db.String(100), unique=True, nullable=True)  # Para enlaces únicos

    def to_dict(self):
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'quantity': self.quantity,
            'total_price': self.total_price,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'company_id': self.company_id,
            'combo_id': self.combo_id,
            'company_name': self.company.name if self.company else '',
            'combo_name': self.combo.name if self.combo else '',
            'confirmed': self.confirmed,
            'confirmation_token': self.confirmation_token
        }

# ------------------------------------------------------------------
# Gestor de réplica manual (segunda base de datos)
# ------------------------------------------------------------------
class ReplicaManager:
    @staticmethod
    def get_connection():
        """Devuelve conexión a la base de datos réplica (SQLite)."""
        conn = sqlite3.connect(Config.REPLICA_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    @staticmethod
    def init_replica_db():
        """Crea las tablas en la base de datos réplica si no existen."""
        conn = ReplicaManager.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                address TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS combos (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                items TEXT,
                price REAL NOT NULL,
                company_id INTEGER NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                customer_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                total_price REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                company_id INTEGER NOT NULL,
                combo_id INTEGER NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
    
    @staticmethod
    def replicate_company(company_dict, delete=False):
        try:
            conn = ReplicaManager.get_connection()
            cursor = conn.cursor()
            if delete:
                cursor.execute("DELETE FROM companies WHERE id = ?", (company_dict['id'],))
            else:
                cursor.execute('''
                    INSERT OR REPLACE INTO companies (id, name, email, phone, address)
                    VALUES (?, ?, ?, ?, ?)
                ''', (company_dict['id'], company_dict['name'], company_dict['email'],
                    company_dict.get('phone'), company_dict.get('address')))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error replicando empresa: {e}")
    
    @staticmethod
    def replicate_combo(combo_dict, delete=False):
        try:
            conn = ReplicaManager.get_connection()
            cursor = conn.cursor()
            if delete:
                cursor.execute("DELETE FROM combos WHERE id = ?", (combo_dict['id'],))
            else:
                cursor.execute('''
                    INSERT OR REPLACE INTO combos (id, name, description, price, company_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (combo_dict['id'], combo_dict['name'], combo_dict.get('description'),
                    combo_dict['price'], combo_dict['company_id']))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error replicando combo: {e}")
    
    @staticmethod
    def replicate_order(order_dict, delete=False):
        try:
            conn = ReplicaManager.get_connection()
            cursor = conn.cursor()
            if delete:
                cursor.execute("DELETE FROM orders WHERE id = ?", (order_dict['id'],))
            else:
                cursor.execute('''
                    INSERT OR REPLACE INTO orders
                    (id, customer_name, quantity, total_price, status, created_at, company_id, combo_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (order_dict['id'], order_dict['customer_name'], order_dict['quantity'],
                    order_dict['total_price'], order_dict['status'], order_dict['created_at'],
                    order_dict['company_id'], order_dict['combo_id']))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error replicando pedido: {e}")