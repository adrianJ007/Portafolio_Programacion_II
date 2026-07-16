import json
from datetime import date, time

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class AsignacionAseo(db.Model):
    __tablename__ = "asignacion_aseo"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    cip = db.Column(db.String(20), nullable=False)
    cargo = db.Column(db.String(100), nullable=False)
    dia = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    edificio = db.Column(db.String(20), nullable=False)
    facultad = db.Column(db.String(150), nullable=True)
    fotos_json = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "cip": self.cip,
            "cargo": self.cargo,
            "dia": self.dia.isoformat() if isinstance(self.dia, date) else str(self.dia),
            "hora": self.hora.strftime("%H:%M") if isinstance(self.hora, time) else str(self.hora),
            "descripcion": self.descripcion,
            "edificio": self.edificio,
            "facultad": self.facultad or "",
            "fotos": self._foto_list(),
        }

    def _foto_list(self):
        try:
            return json.loads(self.fotos_json or "[]")
        except json.JSONDecodeError:
            return []


class Gasto(db.Model):
    __tablename__ = "gasto"

    id = db.Column(db.Integer, primary_key=True)
    categoria = db.Column(db.String(50), nullable=False)
    concepto = db.Column(db.String(200), nullable=True)
    monto = db.Column(db.Numeric(12, 2), nullable=False)

    def to_dict(self):
        m = float(self.monto)
        return {
            "id": self.id,
            "categoria": self.categoria,
            "concepto": self.concepto or "",
            "monto": round(m, 2),
        }
