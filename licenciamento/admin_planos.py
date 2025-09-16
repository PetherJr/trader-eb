from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from licenciamento.db import SessionLocal, Plano, init_db

admin_planos_bp = Blueprint("admin_planos", __name__, template_folder="templates")


@admin_planos_bp.route("/admin/painel")
@login_required
def painel():
    init_db()
    db = SessionLocal()
    planos = db.query(Plano).all()
    db.close()
    return render_template("painel.html", planos=planos)


@admin_planos_bp.route("/admin/planos/criar", methods=["POST"])
@login_required
def criar_plano():
    nome = request.form["nome"]
    dias = int(request.form["dias"])
    link_hotmart = request.form["link_hotmart"]

    init_db()
    db = SessionLocal()
    plano = Plano(nome=nome, dias=dias, link_hotmart=link_hotmart)
    db.add(plano)
    db.commit()
    db.close()

    return redirect(url_for("admin_planos.painel"))


@admin_planos_bp.route("/admin/planos/deletar/<int:plano_id>")
@login_required
def deletar_plano(plano_id):
    init_db()
    db = SessionLocal()
    plano = db.query(Plano).filter(Plano.id == plano_id).first()
    if plano:
        db.delete(plano)
        db.commit()
    db.close()
    return redirect(url_for("admin_planos.painel"))
