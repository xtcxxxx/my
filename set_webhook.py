from telegram import Bot

TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
WEBHOOK_URL = 'https://your-app.onrender.com/'  # Render 部署 URL

bot = Bot(token=TOKEN)
bot.set_webhook(url=WEBHOOK_URL + TOKEN)