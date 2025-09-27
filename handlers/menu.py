from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⚡ Conectar Corretora", callback_data="conectar_corretora")],
        [InlineKeyboardButton("📡 Sinais ao Vivo", callback_data="sinais_ao_vivo")],
        [InlineKeyboardButton("🗓️ Agendar Sinais", callback_data="agendar_sinais")],
        [InlineKeyboardButton("📂 Sinais Agendados", callback_data="sinais_agendados")],
        [InlineKeyboardButton("⚙️ Configurações", callback_data="config")],
        [InlineKeyboardButton("🧠 Estratégias", callback_data="estrategias")],
        [InlineKeyboardButton("📊 Taxas", callback_data="taxas")],
        [InlineKeyboardButton("📊 Resultados", callback_data="resultados")],
        [InlineKeyboardButton("🔄 Renovar Assinatura", url="https://seu-link-hotmart-ou-outro.com")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Se o usuário chamou pelo comando (/menu)
    if update.message:
        await update.message.reply_text("📋 MENU PRINCIPAL", reply_markup=reply_markup)

    # Se o usuário chamou pelo clique em botão (callback)
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("📋 MENU PRINCIPAL", reply_markup=reply_markup)
