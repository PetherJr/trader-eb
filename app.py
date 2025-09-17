import os
import threading
import asyncio
from flask import Flask, request
from licenciamento.webhook import webhook_bp
from licenciamento.controle import controle_bp
from licenciamento.admin_auth import admin_auth_bp, login_manager
from licenciamento.admin_planos import admin_planos_bp

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config.settings import BOT_TOKEN
from handlers.menu import menu_handler
from bot import (
    start,
    plano,
    config,
    callback_handler,
    salvar_valor,
    salvar_stop_win,
    salvar_stop_loss,
    salvar_payout,
    EDIT_VALOR,
    EDIT_STOP_WIN,
    EDIT_STOP_LOSS,
    EDIT_PAYOUT,
)

# =========================================================
# Flask
# =========================================================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")

# Blueprints
app.register_blueprint(webhook_bp)
app.register_blueprint(controle_bp)
app.register_blueprint(admin_auth_bp)
app.register_blueprint(admin_planos_bp)

# Login
login_manager.init_app(app)

@app.route("/")
def home():
    return "API do Bot TraderEB OB rodando!"


# =========================================================
# Telegram Application (PTB v20) - Webhook + event loop próprio
# =========================================================
# URL base do serviço (ajuste se o domínio do Render mudar)
BASE_URL = os.getenv("BASE_URL", "https://trader-eb-1.onrender.com")

# Application do PTB
application = Application.builder().token(BOT_TOKEN).build()

# Handlers principais
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", menu_handler))
application.add_handler(CommandHandler("plano", plano))
application.add_handler(CommandHandler("config", config))

# Conversação para edição de configs
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(callback_handler)],
    states={
        EDIT_VALOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_valor)],
        EDIT_STOP_WIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_stop_win)],
        EDIT_STOP_LOSS: [MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_stop_loss)],
        EDIT_PAYOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_payout)],
    },
    fallbacks=[],
)
application.add_handler(conv_handler)

# Loop assíncrono dedicado ao Telegram
_app_loop = None

def _bot_loop_worker():
    """
    Thread que mantém um event loop dedicado ao PTB,
    inicializa a application e configura o webhook.
    """
    global _app_loop
    _app_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_app_loop)

    async def _startup():
        # Inicializa a aplicação do PTB
        await application.initialize()
        await application.start()

        # Seta o webhook no Telegram apontando para nossa rota Flask
        wh_url = f"{BASE_URL}/webhook/{BOT_TOKEN}"
        await application.bot.set_webhook(url=wh_url)
        print(f"🔗 Webhook configurado: {wh_url}")

    _app_loop.run_until_complete(_startup())
    print("🤖 Bot inicializado e pronto para receber updates (webhook).")
    _app_loop.run_forever()

# Inicia a thread do bot ao subir o app
threading.Thread(target=_bot_loop_worker, daemon=True).start()


# =========================================================
# Rota Webhook do Telegram
# =========================================================
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    # Recebe update do Telegram e despacha para o PTB no loop dedicado
    try:
        data = request.get_json(force=True, silent=False)
        update = Update.de_json(data, application.bot)
        print("📩 Update recebido:", data)

        # Agenda o processamento do update no loop do PTB
        fut = asyncio.run_coroutine_threadsafe(application.process_update(update), _app_loop)
        # Não precisamos esperar o resultado para responder 200 ao Telegram
        return "OK", 200
    except Exception as e:
        print("❌ Erro no webhook:", e)
        return "ERR", 200


# =========================================================
# Runner Flask
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Flask dev server — suficiente no Render para esse caso
    app.run(host="0.0.0.0", port=port)
