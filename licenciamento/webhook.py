from flask import Blueprint, request
from datetime import datetime, timedelta
from licenciamento.db import SessionLocal, Licenca, init_db

webhook_bp = Blueprint("webhook", __name__)

SEGREDO_HOTMART = "UByHSJJcYrDLXkaMJT3IQq17cYkcgW8dfa138a-b9d4-4991-97b5-7a3c13354508"  # ⚠️ depois use variável de ambiente

# Definição dos dias de validade para cada plano
PLANOS = {
    "mensal": 30,
    "trimestral": 90,
    "anual": 365
}

@webhook_bp.route("/webhook/hotmart", methods=["POST"])
def receber_webhook():
    data = request.form.to_dict()

    # 🔒 segurança: só processa se o hottok for válido
    if data.get("hottok") != SEGREDO_HOTMART:
        return "Acesso negado", 403

    email = data.get("buyer_email", "").lower()
    status = data.get("purchase_status")
    produto = data.get("product_name", "").lower()

    if status != "approved":
        return "Compra não aprovada", 200

    # 📌 Descobre o plano pelo nome do produto
    dias = 30  # padrão mensal
    for chave, validade in PLANOS.items():
        if chave in produto:
            dias = validade
            break

    validade = datetime.now() + timedelta(days=dias)

    init_db()
    db = SessionLocal()

    licenca = db.query(Licenca).filter(Licenca.email == email).first()

    if licenca:
        # Atualiza a licença existente (seja trial ou expirada)
        licenca.validade = validade.date()
        licenca.is_trial = False
    else:
        # Cria uma nova licença como paga
        licenca = Licenca(email=email, validade=validade.date(), is_trial=False)
        db.add(licenca)

    db.commit()
    db.close()

    return "OK", 200
