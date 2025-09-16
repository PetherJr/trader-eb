from flask import Blueprint, jsonify
from datetime import datetime, timedelta
from licenciamento.db import SessionLocal, Licenca, init_db

controle_bp = Blueprint("controle", __name__)

@controle_bp.route("/verificar/<email>")
def verificar_licenca(email):
    init_db()
    db = SessionLocal()
    licenca = db.query(Licenca).filter(Licenca.email == email.lower()).first()

    # 🆓 Primeiro acesso → cria trial de 2 dias
    if not licenca:
        validade = datetime.now() + timedelta(days=2)
        licenca = Licenca(email=email.lower(), validade=validade.date(), is_trial=True)
        db.add(licenca)
        db.commit()
        db.close()
        return jsonify({
            "status": "trial",
            "expira_em": str(validade.date())
        })

    hoje = datetime.now().date()

    # Licença expirada
    if hoje > licenca.validade:
        status = "expirada"
    # Trial ativo
    elif licenca.is_trial:
        status = "trial"
    # Licença paga ativa
    else:
        status = "ativa"

    db.close()
    return jsonify({
        "status": status,
        "expira_em": str(licenca.validade)
    })
