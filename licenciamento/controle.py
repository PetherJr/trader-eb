from flask import Blueprint, jsonify
from datetime import datetime
import json
import os

controle_bp = Blueprint("controle", __name__)
DB_PATH = "database/licencas.json"

def carregar_licencas():
    if not os.path.exists(DB_PATH):
        return {}
    with open(DB_PATH, "r") as f:
        return json.load(f)

@controle_bp.route("/verificar/<email>")
def verificar_licenca(email):
    licencas = carregar_licencas()
    email = email.lower()

    validade_str = licencas.get(email)
    if not validade_str:
        return jsonify({"status": "sem_licenca"})

    validade = datetime.strptime(validade_str, "%Y-%m-%d")
    hoje = datetime.now()

    if hoje > validade:
        return jsonify({"status": "expirada", "expira_em": validade_str})

    return jsonify({"status": "ativa", "expira_em": validade_str})