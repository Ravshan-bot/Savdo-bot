import requests
from bs4 import BeautifulSoup
import logging
import sys
import asyncio
import os

try:
    from telegram import Bot, Update, ReplyKeyboardMarkup, KeyboardButton
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
except ModuleNotFoundError:
    print("❌ python-telegram-bot kutubxonasi o‘rnatilmagan.")
    print("Iltimos quyidagini ishga tushiring:\n    pip install python-telegram-bot==20.6")
    raise

from apscheduler.schedulers.background import BackgroundScheduler

# === Sozlamalar ===
BOT_TOKEN = '8151910728:AAFV9mfPa7iqF9X1YYZgQnEfS8EWGnZZJSY'
CHANNEL_ID = '@brok_on'

# Bazani to‘g‘ri yo‘l bilan o‘qish
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTRACT_FILE = os.path.join(BASE_DIR, 'baza Shartnoma raqami QQR va Xorazm.txt')

UZEX_URL = 'https://uzex.uz/Trade/OffersSumNew?Page=1&Offset=0&Length=1000&Search=карбамид'
ASK_CONTRACT = 1

bot = Bot(token=BOT_TOKEN)

def load_contract_numbers():
    with open(CONTRACT_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip().isdigit())

async def fetch_and_send_10am():
    contract_numbers = load_contract_numbers()
    try:
        response = requests.get(UZEX_URL, headers={'User-Agent': 'Mozilla/5.0'}, timeout=60)
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('table tbody tr')

        for row in rows:
            await asyncio.sleep(1)
            cols = [td.text.strip() for td in row.select('td')]
            if len(cols) < 8:
                continue

            kontrakt = cols[0]
            if kontrakt not in contract_numbers:
                continue

            tovar_nomi = cols[1] if len(cols) > 1 else "nomaʼlum"
            ombor = cols[7] if len(cols) > 7 else "nomaʼlum"
            try:
                hajm = int(cols[3].replace(" ", "").replace(",", ""))
                soni = int(cols[6].replace(" ", "").replace(",", ""))

                if hajm > 1000000:
                    hajm = hajm // 1000

                umumiy = hajm * soni
                hajm_text = f"( {umumiy} )  килограмм"
            except:
                hajm_text = "(hajm topilmadi)"

            message = (
                f"🧾 Kontrakt nomeri: {kontrakt}\n"
                f"📦 Tovar nomi: {tovar_nomi}\n"
                f"📍 Ombor joylashuvi: {ombor}\n"
                f"📦 Umumiy hajm: {hajm_text}"
            )
            await bot.send_message(chat_id=CHANNEL_ID, text=message)

    except Exception as e:
        await bot.send_message(chat_id=CHANNEL_ID, text=f"⚠️ Xatolik: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup([[KeyboardButton("Карбамид")]], resize_keyboard=True)
    await update.message.reply_text("✅ Mahsulotni tanlang:", reply_markup=keyboard)

async def ask_contract(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📄 Karbamid uchun kontrakt raqamini kiriting:")
    return ASK_CONTRACT

async def search_by_contract(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contract_number = update.message.text.strip()
    try:
        response = requests.get(UZEX_URL, headers={'User-Agent': 'Mozilla/5.0'}, timeout=60)
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('table tbody tr')

        found = False
        for row in rows:
            cols = [td.text.strip() for td in row.select('td')]

            if contract_number in cols:
                found = True

                kontrakt = cols[0] if len(cols) > 0 else "?"
                tovar_nomi = cols[1] if len(cols) > 1 else "nomaʼlum"
                ombor = cols[7] if len(cols) > 7 else "nomaʼlum"

                try:
                    hajm = int(cols[3].replace(" ", "").replace(",", ""))
                    soni = int(cols[6].replace(" ", "").replace(",", ""))

                    if hajm > 1000000:
                        hajm = hajm // 1000

                    umumiy = hajm * soni
                    hajm_text = f"( {umumiy} )  килограмм"
                except:
                    hajm_text = "(hajm topilmadi)"

                message = (
                    f"🧾 Kontrakt nomeri: {kontrakt}\n"
                    f"📦 Tovar nomi: {tovar_nomi}\n"
                    f"📍 Ombor joylashuvi: {ombor}\n"
                    f"📦 Umumiy hajm: {hajm_text}"
                )

                await update.message.reply_text(message)
                await context.bot.send_message(chat_id=CHANNEL_ID, text=message)
                break

        if not found:
            await update.message.reply_text("❌ Bunday kontrakt raqamli savdo topilmadi.")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Xatolik yuz berdi: {e}")

    await update.message.reply_text(
        "⬇️ Yana kontrakt raqami kiriting:",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Карбамид")]], resize_keyboard=True)
    )
    return ASK_CONTRACT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Jarayon bekor qilindi.")
    return ConversationHandler.END

def schedule_daily_job():
    scheduler = BackgroundScheduler(timezone='Asia/Tashkent')
    scheduler.add_job(lambda: asyncio.run(fetch_and_send_10am()), trigger='cron', hour=10, minute=1)
    scheduler.start()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    schedule_daily_job()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Карбамид$"), ask_contract)],
        states={ASK_CONTRACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_by_contract)]},
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(conv_handler)

    print("🤖 Bot ishga tushdi.")
    app.run_polling()
