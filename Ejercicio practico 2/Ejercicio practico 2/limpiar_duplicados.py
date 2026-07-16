# arreglar_combos.py
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from models import Combo, ReplicaManager

with app.app_context():
    # Encuentra el ID más pequeño de cada nombre de combo
    from sqlalchemy import func
    subq = db.session.query(Combo.name, func.min(Combo.id).label('min_id')).group_by(Combo.name).subquery()
    ids_a_conservar = [row.min_id for row in db.session.query(subq).all()]
    combos_a_eliminar = Combo.query.filter(~Combo.id.in_(ids_a_conservar)).all()
    
    for combo in combos_a_eliminar:
        ReplicaManager.replicate_combo({'id': combo.id}, delete=True)
        db.session.delete(combo)
    db.session.commit()
    print(f"Eliminados {len(combos_a_eliminar)} combos duplicados. Quedan {len(ids_a_conservar)} combos.")