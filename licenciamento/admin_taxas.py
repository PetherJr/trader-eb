from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from licenciamento.db import SessionLocal, Taxa, init_db

admin_taxas_bp = Blueprint("admin_taxas", __name__, template_folder="templates")

@admin_taxas_bp.route("/admin/taxas")
@login_required
def listar_taxas():
    init_db()
    db = SessionLocal()
    taxas = db.query(Taxa).all()
    db.close()
    return render_template("taxas.html", taxas=taxas)

@admin_taxas_bp.route("/admin/taxas/criar", methods=["POST"])
@login_required
def criar_taxa():
    nome = request.form["nome"]
    valor = request.form["valor"]

    init_db()
    db = SessionLocal()
    taxa = Taxa(nome=nome, valor=valor)
    db.add(taxa)
    db.commit()
    db.close()

    return redirect(url_for("admin_taxas.listar_taxas"))

@admin_taxas_bp.route("/admin/taxas/deletar/<int:taxa_id>")
@login_required
def deletar_taxa(taxa_id):
    init_db()
    db = SessionLocal()
    taxa = db.query(Taxa).filter(Taxa.id == taxa_id).first()
    if taxa:
        db.delete(taxa)
        db.commit()
    db.close()
    return redirect(url_for("admin_taxas.listar_taxas"))
