import os
import asyncio
from flask import Flask
from licenciamento.webhook import webhook_bp
from licenciamento.controle import controle_bp
from licenciamento.admin_auth import admin_auth_bp, login_manager
from licenciamento.admin_planos import admin_planos_bp
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

app = Flask(__name__)
app.secret_key = "chave_super_secreta"

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


async def run_flask():
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    config = Config()
    config.bind = [f"0.0.0.0:{os.environ.get('PORT', 5000)}"]

    await serve(app, config)


async def run_bot():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_handler))
    application.add_handler(CommandHandler("plano", plano))
    application.add_handler(CommandHandler("config", config))

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

    print("🤖 Bot rodando dentro do Render...")
    await application.run_polling()


async def main():
    await asyncio.gather(
        run_flask(),
        run_bot()
    )


if __name__ == "__main__":
    asyncio.run(main())
