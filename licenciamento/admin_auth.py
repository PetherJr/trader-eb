from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin
import os

admin_auth_bp = Blueprint("admin_auth", __name__, template_folder="templates")

# Usuário fixo para login admin (⚠️ depois pode migrar para banco)
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "1234")

# Configuração do LoginManager
login_manager = LoginManager()
login_manager.login_view = "admin_auth.login"


# Modelo simples de usuário admin
class AdminUser(UserMixin):
    id = 1
    username = ADMIN_USER


@login_manager.user_loader
def load_user(user_id):
    return AdminUser()


# Página de login
@admin_auth_bp.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USER and password == ADMIN_PASS:
            user = AdminUser()
            login_user(user)
            return redirect(url_for("admin_planos.painel"))

        flash("Usuário ou senha inválidos")
        return redirect(url_for("admin_auth.login"))

    return render_template("login.html")


# Logout
@admin_auth_bp.route("/admin/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("admin_auth.login"))
