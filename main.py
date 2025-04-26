import os
import requests
import pandas as pd
import datetime
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, ContextTypes, JobQueue
import nest_asyncio
import asyncio

nest_asyncio.apply()

# Environment Variables
BOT_TOKEN = os.getenv('8089417044:AAHpOMAVXazxziQlWyrlusJgkRGDSgFny2s')
CHAT_ID = os.getenv('987387288')

# List of 20 MOEX tickers
TICKERS = [
    'SBER', 'GAZP', 'LKOH', 'GMKN', 'ROSN',
    'TATN', 'MGNT', 'MTSS', 'NVTK', 'ALRS',
    'POLY', 'YNDX', 'AFKS', 'FIVE', 'CHMF',
    'PHOR', 'PIKK', 'RTKM', 'IRAO', 'MOEX'
]

THRESHOLD_SINGLE = 1.0  # % change for individual stock
THRESHOLD_TOTAL = 1.0   # % average change for entire market

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch prices from MOEX API
def fetch_stock_data():
    today = datetime.date.today().strftime('%Y-%m-%d')
    results = []

    for ticker in TICKERS:
        try:
            url = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{ticker}/candles.json?interval=60&from={today}&till={today}"
            response = requests.get(url)
            data = response.json()
            candles = data['candles']['data']
            columns = data['candles']['columns']

            if not candles:
                continue

            df = pd.DataFrame(candles, columns=columns)
            open_price = df.iloc[0]['open']
            current_price = df.iloc[-1]['close']
            percent_change = ((current_price - open_price) / open_price) * 100

            results.append({
                'ticker': ticker,
                'change': round(percent_change, 2),
                'status': current_price > open_price,
                'open': open_price,
                'current': current_price
            })
        except Exception as e:
            logger.warning(f"Failed for {ticker}: {e}")
            continue

    return results

# Generate message
def generate_alert(results):
    if not results:
        return "⚠️ No data available for any company right now.", 0

    total_change = sum(r['change'] for r in results) / len(results)

    message_lines = []
    for r in results:
        direction = "📈 UP" if r["change"] > 0 else "📉 DOWN"
        message_lines.append(
            f"{r['ticker']}: {direction} {r['change']:.2f}% (from {r['open']:.2f} to {r['current']:.2f})"
        )

    message_lines.append(f"\n📊 TOTAL AVERAGE CHANGE: {total_change:.2f}%")

    # Check if total average crosses threshold
    if abs(total_change) >= THRESHOLD_TOTAL:
        message_lines.append(
            "🚨 Market-wide movement detected!" +
            (" 📈 Average UP" if total_change > 0 else " 📉 Average DOWN")
        )

    return "\n".join(message_lines), total_change

# Manual command handler
async def start(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("📊 Run Market Check", callback_data='check_market')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome! Click below to check market trends now:", reply_markup=reply_markup)

# Button callback
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    results = fetch_stock_data()
    message, _ = generate_alert(results)

    if message:
        await query.message.reply_text("📡 Market Update:\n" + message)
    else:
        await query.message.reply_text("✅ No major changes detected.")

# Scheduled job every 15 mins
async def scheduled_check(context: ContextTypes.DEFAULT_TYPE):
    results = fetch_stock_data()
    message, total_change = generate_alert(results)

    if message:
        await context.bot.send_message(chat_id=CHAT_ID, text="⏰ Auto Market Check:\n" + message)

# Main entry
async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Schedule auto check every 15 minutes
    job_queue: JobQueue = app.job_queue
    job_queue.run_repeating(scheduled_check, interval=900, first=5)

    await app.run_polling()

# Entry point
if __name__ == '__main__':
    asyncio.run(main())


        else:
            print(f"[DEBUG] No data for {ticker}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch data for {ticker}: {e}")
