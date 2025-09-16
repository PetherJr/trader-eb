from flask import Blueprint, request
from datetime import datetime, timedelta
from licenciamento.db import SessionLocal, Licenca, init_db

webhook_bp = Blueprint("webhook", __name__)

SEGREDO_HOTMART = "UByHSJJcYrDLXkaMJT3IQq17cYkcgW8dfa138a-b9d4-4991-97b5-7a3c13354508" 
@webhook_bp.route("/webhook/hotmart", methods=["POST"])
def receber_webhook():
    data = request.form.to_dict()

    if data.get("hottok") != SEGREDO_HOTMART:
        return "Acesso negado", 403

    email = data.get("buyer_email", "").lower()
    status = data.get("purchase_status")

    if status != "approved":
        return "Compra não aprovada", 200

    validade = datetime.now() + timedelta(days=30)  # por padrão, 30 dias

    init_db()  # garante que a tabela existe
    db = SessionLocal()

    licenca = db.query(Licenca).filter(Licenca.email == email).first()
    if licenca:
        licenca.validade = validade.date()
    else:
        licenca = Licenca(email=email, validade=validade.date())
        db.add(licenca)

    db.commit()
    db.close()

    return "OK", 200
