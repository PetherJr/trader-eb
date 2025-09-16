from flask import Blueprint, jsonify
from datetime import datetime
from licenciamento.db import SessionLocal, Licenca, init_db

controle_bp = Blueprint("controle", __name__)

@controle_bp.route("/verificar/<email>")
def verificar_licenca(email):
    init_db()
    db = SessionLocal()
    licenca = db.query(Licenca).filter(Licenca.email == email.lower()).first()
    db.close()

    if not licenca:
        return jsonify({"status": "sem_licenca"})

    hoje = datetime.now().date()

    if hoje > licenca.validade:
        return jsonify({"status": "expirada", "expira_em": str(licenca.validade)})

    return jsonify({"status": "ativa", "expira_em": str(licenca.validade)})
