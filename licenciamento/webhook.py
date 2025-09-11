from flask import Blueprint, request
from datetime import datetime, timedelta
import json
import os

webhook_bp = Blueprint("webhook", __name__)
DB_PATH = "database/licencas.json"
SEGREDO_HOTMART = "UByHSJJcYrDLXkaMJT3IQq17cYkcgW8dfa138a-b9d4-4991-97b5-7a3c13354508"

def salvar_licencas(dados):
    with open(DB_PATH, "w") as f:
        json.dump(dados, f, indent=4)

def carregar_licencas():
    if not os.path.exists(DB_PATH):
        return {}
    with open(DB_PATH, "r") as f:
        return json.load(f)

@webhook_bp.route("/webhook/hotmart", methods=["POST"])
def receber_webhook():
    data = request.form.to_dict()

    if data.get("hottok") != SEGREDO_HOTMART:
        return "Acesso negado", 403

    email = data.get("buyer_email", "").lower()
    status = data.get("purchase_status")

    if status != "approved":
        return "Compra não aprovada", 200

    dias = 30  # plano mensal por padrão
    validade = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")

    licencas = carregar_licencas()
    licencas[email] = validade
    salvar_licencas(licencas)

    print(f"[HOTMART] Licença ativa para {email} até {validade}")
    return "OK", 200