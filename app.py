import os
import threading
import asyncio
from flask import Flask, request

# Blueprints e auth
from licenciamento.webhook import webhook_bp
from licenciamento.controle import controle_bp
from licenciamento.admin_auth import admin_auth_bp, login_manager
from licenciamento.admin_planos import admin_planos_bp
from licenciamento.admin_estrategias import admin_estrategias_bp
from licenciamento.admin_taxas import admin_taxas_bp

# DB e modelos usados nos botões
from licenciamento.db import SessionLocal, Estrategia, Taxa, Sinal, init_db

# Telegram
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

# Funções do bot (config/planos e states)
from bot import (
    start,
    plano,
    config,
    callback_handler,      # entry-points de /config (edit_/toggle_)
    salvar_valor,
    salvar_stop_win,
    salvar_stop_loss,
    salvar_payout,
    EDIT_VALOR,
    EDIT_STOP_WIN,
    EDIT_STOP_LOSS,
    EDIT_PAYOUT,
)

# -----------------------------
# Estados extras (sinais)
AGENDAR_SINAIS = 100
# -----------------------------

# =========================================================
# Flask
# =========================================================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")

# Blueprints
app.register_blueprint(webhook_bp)
app.register_blueprint(controle_bp)
app.register_blueprint(admin_auth_bp)
app.register_blueprint(admin_estrategias_bp)
app.register_blueprint(admin_planos_bp)
app.register_blueprint(admin_taxas_bp)

# Login
login_manager.init_app(app)

@app.route("/")
def home():
    return "API do Bot TraderEB OB rodando!"

# =========================================================
# Telegram Application (webhook)
# =========================================================
BASE_URL = os.getenv("BASE_URL", "https://trader-eb-1.onrender.com")

application = Application.builder().token(BOT_TOKEN).build()

# Comandos principais
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", menu_handler))
application.add_handler(CommandHandler("plano", plano))
application.add_handler(CommandHandler("config", config))

# =========================================================
# Funções auxiliares para /sinais
# =========================================================
async def iniciar_agendamento(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✍️ Envie a lista de sinais no formato:\n\n"
        "EUR/USD 13:05 CALL 5m\n"
        "GBP/JPY 14:10 PUT",
        parse_mode="Markdown",
    )
    return AGENDAR_SINAIS

async def receber_lista_sinais(update, context):
    identificador = update.effective_user.username or str(update.effective_user.id)
    linhas = (update.message.text or "").strip().splitlines()

    db = SessionLocal()
    for linha in linhas:
        try:
            partes = linha.split()
            if len(partes) < 3:
                continue
            par, horario, direcao = partes[0], partes[1], partes[2]
            expiracao = partes[3] if len(partes) > 3 else None
            db.add(Sinal(
                usuario=identificador,
                par=par,
                horario=horario,
                direcao=direcao.upper(),
                expiracao=expiracao,
            ))
        except Exception:
            continue
    db.commit()
    db.close()

    await update.message.reply_text("✅ Sinais agendados com sucesso!")
    return ConversationHandler.END

async def listar_sinais(update, context):
    identificador = update.effective_user.username or str(update.effective_user.id)
    db = SessionLocal()
    sinais = db.query(Sinal).filter(Sinal.usuario == identificador, Sinal.ativo == True).all()
    db.close()

    if not sinais:
        await update.callback_query.edit_message_text("⚠️ Nenhum sinal agendado no momento.")
        return

    msg = "🗂️ Sinais agendados:\n\n"
    for s in sinais:
        msg += f"- {s.par} {s.horario} {s.direcao} {s.expiracao or ''}\n"
    await update.callback_query.edit_message_text(msg)

# Fallback universal
async def cancelar(update, context):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❎ Operação cancelada.")
    else:
        await update.message.reply_text("❎ Operação cancelada.")
    return ConversationHandler.END

# =========================================================
# Conversa do /config (edit_/toggle_)
# =========================================================
conv_config = ConversationHandler(
    entry_points=[CallbackQueryHandler(callback_handler, pattern=r"^(edit_|toggle_)")],
    states={
        EDIT_VALOR:     [MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_valor)],
        EDIT_STOP_WIN:  [MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_stop_win)],
        EDIT_STOP_LOSS: [MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_stop_loss)],
        EDIT_PAYOUT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_payout)],
    },
    fallbacks=[CommandHandler("cancel", cancelar)],
    per_message=False,
    allow_reentry=True,
)
application.add_handler(conv_config)

# =========================================================
# Conversa “Agendar Sinais”
# =========================================================
conv_sinais = ConversationHandler(
    entry_points=[CallbackQueryHandler(iniciar_agendamento, pattern=r"^agendar_sinais$")],
    states={
        AGENDAR_SINAIS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_lista_sinais)],
    },
    fallbacks=[CommandHandler("cancel", cancelar)],
    per_message=False,
    allow_reentry=True,
)
application.add_handler(conv_sinais)

# =========================================================
# Callback genérico (demais botões do /menu)
# =========================================================
async def generic_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = (query.data or "").strip()

    if data == "sinais_ao_vivo":
        await query.edit_message_text(
            "📡 Modo *Sinais ao Vivo* (placeholder).", parse_mode="Markdown"
        )

    elif data == "sinais_agendados":
        await listar_sinais(update, context)

    elif data == "config":
        await config(update, context)

    elif data == "estrategias":
        init_db()
        db = SessionLocal()
        estrategias = db.query(Estrategia).all()
        db.close()

        if estrategias:
            msg = "🧠 Estratégias disponíveis:\n\n"
            for e in estrategias:
                status = "✅ Ativa" if e.ativa else "❌ Inativa"
                msg += f"- {e.nome} ({status})\n"
                if e.descricao:
                    msg += f"   {e.descricao}\n"
        else:
            msg = "⚠️ Nenhuma estratégia cadastrada ainda."

        await query.edit_message_text(msg)

    elif data == "taxas":
        init_db()
        db = SessionLocal()
        taxas = db.query(Taxa).all()
        db.close()

        if taxas:
            msg = "📊 Taxas cadastradas:\n\n"
            for t in taxas:
                msg += f"- {t.nome}: {t.valor}\n"
        else:
            msg = "⚠️ Nenhuma taxa cadastrada ainda."

        await query.edit_message_text(msg)

    else:
        await query.edit_message_text(f"⚠️ Botão '{data}' não implementado.")

# Handler genérico
application.add_handler(CallbackQueryHandler(
    generic_callback,
    pattern=r"^(?!edit_|toggle_|agendar_sinais).+"
))

# =========================================================
# Loop assíncrono dedicado (thread) + webhook
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

threading.Thread(target=_bot_loop_worker, daemon=True).start()

# =========================================================
# Rota Webhook
# =========================================================
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        asyncio.run_coroutine_threadsafe(
            application.process_update(update), _app_loop
        )
        return "OK", 200
    except Exception as e:
        print("❌ Erro no webhook:", e)
        return "ERR", 200

# =========================================================
# Runner Flask local
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
