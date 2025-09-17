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

# Registrar rotas Flask
app.register_blueprint(webhook_bp)
app.register_blueprint(controle_bp)
app.register_blueprint(admin_auth_bp)
app.register_blueprint(admin_planos_bp)

# Config login Flask
login_manager.init_app(app)

@app.route("/")
def home():
    return "API do Bot TraderEB OB rodando!"


# =========================================================
# Telegram Application (em webhook)
# =========================================================
BASE_URL = os.getenv("BASE_URL", "https://trader-eb-1.onrender.com")

application = Application.builder().token(BOT_TOKEN).build()

# Handlers principais
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", menu_handler))
application.add_handler(CommandHandler("plano", plano))
application.add_handler(CommandHandler("config", config))


# =========================================================
# Conversações do /config (apenas botões edit/toggle)
# =========================================================
conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(callback_handler, pattern="^(edit_|toggle_)")
    ],
    states={
        EDIT_VALOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_valor)],
        EDIT_STOP_WIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_stop_win)],
        EDIT_STOP_LOSS: [MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_stop_loss)],
        EDIT_PAYOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_payout)],
    },
    fallbacks=[],
)
application.add_handler(conv_handler)  # ✅ vem antes do handler genérico


# =========================================================
# Callback genérico para botões do menu
# =========================================================
async def generic_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "sinais_ao_vivo":
        await query.edit_message_text("📡 Você clicou em *Sinais ao Vivo* (em breve).", parse_mode="Markdown")
    elif data == "agendar_sinais":
        await query.edit_message_text("🗓️ Função *Agendar Sinais* ainda em desenvolvimento.", parse_mode="Markdown")
    elif data == "sinais_agendados":
        await query.edit_message_text("🗂️ Nenhum sinal agendado no momento.", parse_mode="Markdown")
    elif data == "config":
        await config(update, context)  # reaproveita função existente
    elif data == "estrategias":
        await query.edit_message_text("🧠 Estratégias disponíveis em breve.", parse_mode="Markdown")
    elif data == "taxas":
        await query.edit_message_text("📊 Taxas ainda em configuração.", parse_mode="Markdown")
    else:
        await query.edit_message_text(f"⚠️ Botão '{data}' não implementado.")

# ✅ genérico só pega o que não é edit_ ou toggle_
application.add_handler(CallbackQueryHandler(generic_callback, pattern="^(?!edit_|toggle_).+"))


# =========================================================
# Loop assíncrono dedicado
# =========================================================
_app_loop = None

def _bot_loop_worker():
    global _app_loop
    _app_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_app_loop)

    async def _startup():
        await application.initialize()
        await application.start()

        wh_url = f"{BASE_URL}/webhook/{BOT_TOKEN}"
        await application.bot.set_webhook(url=wh_url)
        print(f"🔗 Webhook configurado no Telegram: {wh_url}")

    _app_loop.run_until_complete(_startup())
    print("🤖 Bot inicializado (modo webhook).")
    _app_loop.run_forever()

# Inicia thread dedicada ao bot
threading.Thread(target=_bot_loop_worker, daemon=True).start()


# =========================================================
# Rota Webhook para receber updates
# =========================================================
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        print("📩 Update recebido:", data)

        asyncio.run_coroutine_threadsafe(
            application.process_update(update), _app_loop
        )
        return "OK", 200
    except Exception as e:
        print("❌ Erro no webhook:", e)
        return "ERR", 200


# =========================================================
# Runner Flask
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
