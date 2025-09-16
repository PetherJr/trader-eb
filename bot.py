import requests
from telegram.ext import Application, CommandHandler
from config.settings import BOT_TOKEN
from handlers.menu import menu_handler

# 🔗 URL do backend hospedado no Render
BASE_URL = "https://trader-eb.onrender.com"

async def start(update, context):
    user = update.effective_user
    identificador = user.username or str(user.id)

    try:
        response = requests.get(f"{BASE_URL}/verificar/{identificador}")
        data = response.json()

        if data["status"] == "sem_licenca":
            await update.message.reply_text(
                "❌ Você ainda não possui uma licença ativa.\nAcesse /menu para comprar."
            )
            return

        if data["status"] == "trial":
            await update.message.reply_text(
                f"🆓 Você ganhou um teste gratuito de 2 dias!\n"
                f"Seu acesso expira em {data['expira_em']}."
            )
            return

        if data["status"] == "expirada":
            await update.message.reply_text(
                f"⚠️ Sua licença expirou em {data['expira_em']}.\n"
                "Acesse /menu para renovar."
            )
            return

        if data["status"] == "ativa":
            await update.message.reply_text(
                "✅ Licença ativa! Use /menu para continuar."
            )
            return

    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao verificar licença: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_handler))

    print("🤖 Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
