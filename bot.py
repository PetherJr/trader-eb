import requests
from telegram.ext import Application, CommandHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config.settings import BOT_TOKEN
from handlers.menu import menu_handler
from licenciamento.db import SessionLocal, Plano

# 🔗 URL do backend hospedado no Render
BASE_URL = "https://trader-eb.onrender.com"


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


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_handler))
    app.add_handler(CommandHandler("plano", plano))

    print("🤖 Bot rodando...")
    app.run_polling()


if __name__ == "__main__":
    main()
