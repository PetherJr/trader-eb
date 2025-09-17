from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from licenciamento.db import SessionLocal, Estrategia, init_db

admin_estrategias_bp = Blueprint("admin_estrategias", __name__, template_folder="templates")

@admin_estrategias_bp.route("/admin/estrategias")
@login_required
def listar_estrategias():
    init_db()
    db = SessionLocal()
    estrategias = db.query(Estrategia).all()
    db.close()
    return render_template("estrategias.html", estrategias=estrategias)

@admin_estrategias_bp.route("/admin/estrategias/criar", methods=["POST"])
@login_required
def criar_estrategia():
    nome = request.form["nome"]
    descricao = request.form.get("descricao", "")

    init_db()
    db = SessionLocal()
    estrategia = Estrategia(nome=nome, descricao=descricao, ativa=True)
    db.add(estrategia)
    db.commit()
    db.close()

    return redirect(url_for("admin_estrategias.listar_estrategias"))

@admin_estrategias_bp.route("/admin/estrategias/deletar/<int:estrategia_id>")
@login_required
def deletar_estrategia(estrategia_id):
    init_db()
    db = SessionLocal()
    estrategia = db.query(Estrategia).filter(Estrategia.id == estrategia_id).first()
    if estrategia:
        db.delete(estrategia)
        db.commit()
    db.close()
    return redirect(url_for("admin_estrategias.listar_estrategias"))
