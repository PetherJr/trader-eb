from flask import Flask
from licenciamento.webhook import webhook_bp
from licenciamento.controle import controle_bp

app = Flask(__name__)
app.register_blueprint(webhook_bp)
app.register_blueprint(controle_bp)

@app.route("/")
def home():
    return "API do Bot TraderEB OB rodando!"

if __name__ == "__main__":
    app.run(debug=True)