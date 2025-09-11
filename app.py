from flask import Flask
from licenciamento.webhook import webhook_bp
from licenciamento.controle import controle_bp
import os

app = Flask(__name__)
app.register_blueprint(webhook_bp)
app.register_blueprint(controle_bp)

@app.route("/")
def home():
    return "API do Bot TraderEB OB rodando!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)