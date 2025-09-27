import os
import threading
import asyncio
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from pytz import timezone
from iqoptionapi.stable_api import IQ_Option
from licenciamento.db import CredencialCorretora
from licenciamento.db import SessionLocal, Estrategia, Taxa, Sinal, Resultado, CredencialCorretora, init_db

# Blueprints e auth
from licenciamento.webhook import webhook_bp
from licenciamento.controle import controle_bp
from licenciamento.admin_auth import admin_auth_bp, login_manager
from licenciamento.admin_planos import admin_planos_bp
from licenciamento.admin_estrategias import admin_estrategias_bp
from licenciamento.admin_taxas import admin_taxas_bp

# Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
SALVAR_CREDENCIAIS = 200

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

async def iniciar_conexao_corretora(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚡ Envie suas credenciais no formato:\n\nemail;senha;demo/real\n\nExemplo:\nmeuemail@gmail.com;minhasenha;demo"
    )
    return SALVAR_CREDENCIAIS

async def salvar_credenciais(update, context):
    identificador = str(update.effective_user.id)
    partes = update.message.text.split(";")
    if len(partes) < 3:
        await update.message.reply_text("⚠️ Formato inválido. Use: email;senha;demo/real")
        return ConversationHandler.END

    email, senha, tipo = partes
    conta_demo = True if tipo.strip().lower() == "demo" else False

    db = SessionLocal()
    cred = db.query(CredencialCorretora).filter(CredencialCorretora.usuario == identificador).first()
    if cred:
        cred.email = email.strip()
        cred.senha = senha.strip()
        cred.conta_demo = conta_demo
    else:
        cred = CredencialCorretora(
            usuario=identificador,
            corretora="iqoption",
            email=email.strip(),
            senha=senha.strip(),
            conta_demo=conta_demo
        )
        db.add(cred)
    db.commit()
    db.close()

    await update.message.reply_text("✅ Credenciais salvas com sucesso!")
    return ConversationHandler.END


async def receber_lista_sinais(update, context):
    identificador = str(update.effective_user.id)
    linhas = (update.message.text or "").strip().splitlines()

    db = SessionLocal()
    adicionados = 0
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
            adicionados += 1
        except Exception:
            continue
    db.commit()
    db.close()

    if adicionados > 0:
        await update.message.reply_text(f"✅ {adicionados} sinais agendados com sucesso!")
    else:
        await update.message.reply_text("⚠️ Nenhum sinal válido foi encontrado. Tente novamente.")

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
    keyboard = []

    for s in sinais:
        msg += f"- {s.par} {s.horario} {s.direcao} {s.expiracao or ''}\n"
        keyboard.append([InlineKeyboardButton(f"❌ {s.par} {s.horario}", callback_data=f"del_sinal_{s.id}")])

    # botão apagar todos
    keyboard.append([InlineKeyboardButton("🗑️ Apagar todos", callback_data="del_all_sinais")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(msg, reply_markup=reply_markup)

# Excluir todos os sinais
async def excluir_todos_sinais(update, context):
    query = update.callback_query
    await query.answer()
    identificador = query.from_user.username or str(query.from_user.id)

    db = SessionLocal()
    db.query(Sinal).filter(Sinal.usuario == identificador).delete()
    db.commit()
    db.close()

    await query.edit_message_text("🗑️ Todos os sinais foram apagados com sucesso!")

# Excluir sinal específico
async def excluir_sinal(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data  # ex.: "del_sinal_5"

    try:
        sinal_id = int(data.split("_")[-1])
    except Exception:
        await query.edit_message_text("⚠️ Erro ao identificar o sinal.")
        return

    db = SessionLocal()
    sinal = db.query(Sinal).filter(Sinal.id == sinal_id).first()
    if sinal:
        db.delete(sinal)
        db.commit()
        resposta = f"🗑️ Sinal {sinal.par} {sinal.horario} {sinal.direcao} apagado."
    else:
        resposta = "⚠️ Sinal não encontrado."
    db.close()

    await query.edit_message_text(resposta)

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
conv_credenciais = ConversationHandler(
    entry_points=[CallbackQueryHandler(iniciar_conexao_corretora, pattern=r"^conectar_corretora$")],
    states={SALVAR_CREDENCIAIS: [MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_credenciais)]},
    fallbacks=[CommandHandler("cancel", cancelar)],
    per_message=False,
    allow_reentry=True,
)
application.add_handler(conv_credenciais)


# =========================================================
# Conversa “Agendar Sinais”
# =========================================================
conv_sinais = ConversationHandler(
    entry_points=[CallbackQueryHandler(iniciar_agendamento, pattern=r"^agendar_sinais$")],
    states={
        AGENDAR_SINAIS: [MessageHandler(filters.ALL & ~filters.COMMAND, receber_lista_sinais)],
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

    elif data == "resultados":
        init_db()
        db = SessionLocal()
        user_id = str(query.from_user.id)
        resultados = (
            db.query(Resultado)
            .filter(Resultado.usuario == user_id)
            .order_by(Resultado.id.desc())
            .limit(5)
            .all()
        )
        total = db.query(Resultado).filter(Resultado.usuario == user_id).count()
        db.close()

        if not resultados:
            await query.edit_message_text("📊 Nenhum resultado registrado ainda.")
            return

        msg = f"📊 Resultados:\n\nTotal executados: {total}\n\nÚltimos sinais:\n"
        for r in resultados:
            msg += f"- {r.par} {r.horario} {r.direcao} ({r.status})\n"

        await query.edit_message_text(msg)

    else:
        await query.edit_message_text(f"⚠️ Botão '{data}' não implementado.")


# Handlers extras para exclusão
application.add_handler(CallbackQueryHandler(excluir_todos_sinais, pattern=r"^del_all_sinais$"))
application.add_handler(CallbackQueryHandler(excluir_sinal, pattern=r"^del_sinal_\d+$"))

# Handler genérico
application.add_handler(CallbackQueryHandler(
    generic_callback,
    pattern=r"^(?!edit_|toggle_|agendar_sinais|del_sinal_|del_all_sinais).+"
))

# =========================================================
# Executor automático de sinais (APScheduler)
# =========================================================
async def processar_sinais():
    tz = timezone("America/Sao_Paulo")
    agora = datetime.now(tz).strftime("%H:%M")

    db = SessionLocal()
    sinais = db.query(Sinal).filter(Sinal.ativo == True, Sinal.horario == agora).all()

    for sinal in sinais:
        sinal.ativo = False
        db.commit()

        cred = db.query(CredencialCorretora).filter(CredencialCorretora.usuario == sinal.usuario).first()

        if not cred:
            await application.bot.send_message(chat_id=int(sinal.usuario), text="⚠️ Nenhuma credencial salva.")
            continue

        try:
            Iq = IQ_Option(cred.email, cred.senha)
            Iq.connect()
            tipo_conta = "PRACTICE" if cred.conta_demo else "REAL"
            Iq.change_balance(tipo_conta)

            status, order_id = Iq.buy_digital_spot(sinal.par.replace("/", ""), 1, sinal.direcao.lower(), 1)

            if status:
                msg = f"🚀 Ordem enviada: {sinal.par} {sinal.horario} {sinal.direcao} ({'demo' if cred.conta_demo else 'real'})"
            else:
                msg = f"❌ Falha ao enviar ordem para {sinal.par}"

            await application.bot.send_message(chat_id=int(sinal.usuario), text=msg)

            # salva no histórico de resultados
            resultado = Resultado(
                usuario=sinal.usuario,
                par=sinal.par,
                horario=sinal.horario,
                direcao=sinal.direcao,
                expiracao=sinal.expiracao,
                status="executado"
            )
            db.add(resultado)
            db.commit()

        except Exception as e:
            await application.bot.send_message(chat_id=int(sinal.usuario), text=f"❌ Erro ao conectar: {e}")

    db.close()


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

    # Inicia o scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: asyncio.run_coroutine_threadsafe(processar_sinais(), _app_loop), 'interval', minutes=1)
    scheduler.start()

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
