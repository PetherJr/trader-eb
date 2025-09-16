import requests
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from config.settings import BOT_TOKEN
from handlers.menu import menu_handler
from licenciamento.db import SessionLocal, ConfigUsuario, Plano, init_db

# 🔗 URL do backend hospedado no Render
BASE_URL = "https://trader-eb-1.onrender.com"

# Estados para edição
(
    EDIT_VALOR,
    EDIT_STOP_WIN,
    EDIT_STOP_LOSS,
    EDIT_PAYOUT,
) = range(4)


# 🚀 Comando /start
async def start(update, context):
    user = update.effective_user
    identificador = user.username or str(user.id)

    try:
        response = requests.get(f"{BASE_URL}/verificar/{identificador}")
        data = response.json()

        if data["status"] == "sem_licenca":
            await update.message.reply_text(
                "❌ Você ainda não possui uma licença ativa.\nAcesse /plano para comprar."
            )
            return

        if data["status"] == "trial":
            await update.message.reply_text(
                f"🆓 Você ganhou um teste gratuito de 2 dias!\n"
                f"Seu acesso expira em {data['expira_em']}.\n\n"
                "Para continuar após o teste, acesse /plano."
            )
            return

        if data["status"] == "expirada":
            await update.message.reply_text(
                f"⚠️ Sua licença expirou em {data['expira_em']}.\n"
                "Acesse /plano para renovar."
            )
            return

        if data["status"] == "ativa":
            await update.message.reply_text(
                f"✅ Licença ativa! Expira em {data['expira_em']}.\n"
                "Use /menu para começar."
            )
            return

    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao verificar licença: {e}")


# 🚀 Comando /plano
async def plano(update, context):
    user = update.effective_user
    identificador = user.username or str(user.id)

    try:
        # Consulta status da licença
        response = requests.get(f"{BASE_URL}/verificar/{identificador}")
        data = response.json()
        status = data["status"]
        expira_em = data.get("expira_em", "-")

        if status == "trial":
            msg = f"🆓 Você está no período de teste gratuito.\nExpira em: {expira_em}"
        elif status == "ativa":
            msg = f"✅ Sua licença está ativa.\nExpira em: {expira_em}"
        elif status == "expirada":
            msg = f"⚠️ Sua licença expirou em {expira_em}.\nRenove para continuar usando."
        else:
            msg = "❌ Você não possui nenhuma licença ativa."

        # 🔎 Busca os planos no banco
        db = SessionLocal()
        planos = db.query(Plano).all()
        db.close()

        if not planos:
            await update.message.reply_text(msg + "\n\n⚠️ Nenhum plano configurado ainda.")
            return

        # Gera botões dinamicamente
        keyboard = [
            [InlineKeyboardButton(f"📅 {p.nome}", url=p.link_hotmart)]
            for p in planos
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(msg, reply_markup=reply_markup)

    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao verificar plano: {e}")


# 🚀 Comando /config
async def config(update, context):
    user = update.effective_user
    identificador = user.username or str(user.id)

    init_db()
    db = SessionLocal()
    config = db.query(ConfigUsuario).filter(ConfigUsuario.user_id == identificador).first()

    if not config:
        config = ConfigUsuario(user_id=identificador)
        db.add(config)
        db.commit()

    db.refresh(config)
    db.close()

    msg = (
        f"⚙️ Configurações atuais de {identificador}:\n\n"
        f"💰 Valor inicial: {config.valor_inicial}\n"
        f"✅ Stop Win: {config.stop_win}\n"
        f"❌ Stop Loss: {config.stop_loss}\n"
        f"🔄 Martingale: {'Ativado' if config.martingale else 'Desativado'}\n"
        f"🎯 Soros: {'Ativado' if config.soros else 'Desativado'}\n"
        f"📊 Payout mínimo: {config.payout_minimo}%"
    )

    keyboard = [
        [InlineKeyboardButton("💰 Alterar Valor Inicial", callback_data="edit_valor")],
        [InlineKeyboardButton("✅ Alterar Stop Win", callback_data="edit_stop_win")],
        [InlineKeyboardButton("❌ Alterar Stop Loss", callback_data="edit_stop_loss")],
        [InlineKeyboardButton("🔄 Toggle Martingale", callback_data="toggle_martingale")],
        [InlineKeyboardButton("🎯 Toggle Soros", callback_data="toggle_soros")],
        [InlineKeyboardButton("📊 Alterar Payout Mínimo", callback_data="edit_payout")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(msg, reply_markup=reply_markup)


# 🚀 Callback para editar configs
async def callback_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    identificador = query.from_user.username or str(query.from_user.id)

    db = SessionLocal()
    config = db.query(ConfigUsuario).filter(ConfigUsuario.user_id == identificador).first()

    if query.data == "toggle_martingale":
        config.martingale = not config.martingale
        db.commit()
        db.close()
        await query.edit_message_text("🔄 Martingale atualizado! Use /config para ver as alterações.")
        return

    if query.data == "toggle_soros":
        config.soros = not config.soros
        db.commit()
        db.close()
        await query.edit_message_text("🎯 Soros atualizado! Use /config para ver as alterações.")
        return

    # Estados que exigem input do usuário
    db.close()
    if query.data == "edit_valor":
        await query.edit_message_text("💰 Digite o novo valor inicial:")
        return EDIT_VALOR
    elif query.data == "edit_stop_win":
        await query.edit_message_text("✅ Digite o novo Stop Win:")
        return EDIT_STOP_WIN
    elif query.data == "edit_stop_loss":
        await query.edit_message_text("❌ Digite o novo Stop Loss:")
        return EDIT_STOP_LOSS
    elif query.data == "edit_payout":
        await query.edit_message_text("📊 Digite o novo Payout mínimo (%):")
        return EDIT_PAYOUT

    return ConversationHandler.END


# 🚀 Handlers para salvar inputs do usuário
async def salvar_valor(update, context):
    identificador = update.effective_user.username or str(update.effective_user.id)
    novo_valor = int(update.message.text)

    db = SessionLocal()
    config = db.query(ConfigUsuario).filter(ConfigUsuario.user_id == identificador).first()
    config.valor_inicial = novo_valor
    db.commit()
    db.close()

    await update.message.reply_text(f"💰 Valor inicial atualizado para {novo_valor}.")
    return ConversationHandler.END


async def salvar_stop_win(update, context):
    identificador = update.effective_user.username or str(update.effective_user.id)
    novo_valor = int(update.message.text)

    db = SessionLocal()
    config = db.query(ConfigUsuario).filter(ConfigUsuario.user_id == identificador).first()
    config.stop_win = novo_valor
    db.commit()
    db.close()

    await update.message.reply_text(f"✅ Stop Win atualizado para {novo_valor}.")
    return ConversationHandler.END


async def salvar_stop_loss(update, context):
    identificador = update.effective_user.username or str(update.effective_user.id)
    novo_valor = int(update.message.text)

    db = SessionLocal()
    config = db.query(ConfigUsuario).filter(ConfigUsuario.user_id == identificador).first()
    config.stop_loss = novo_valor
    db.commit()
    db.close()

    await update.message.reply_text(f"❌ Stop Loss atualizado para {novo_valor}.")
    return ConversationHandler.END


async def salvar_payout(update, context):
    identificador = update.effective_user.username or str(update.effective_user.id)
    novo_valor = int(update.message.text)

    db = SessionLocal()
    config = db.query(ConfigUsuario).filter(ConfigUsuario.user_id == identificador).first()
    config.payout_minimo = novo_valor
    db.commit()
    db.close()

    await update.message.reply_text(f"📊 Payout mínimo atualizado para {novo_valor}%.")
    return ConversationHandler.END


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_handler))
    app.add_handler(CommandHandler("plano", plano))
    app.add_handler(CommandHandler("config", config))

    # Conversações para editar configs
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
    app.add_handler(conv_handler)

    print("🤖 Bot rodando...")
    app.run_polling()


if __name__ == "__main__":
    main()
