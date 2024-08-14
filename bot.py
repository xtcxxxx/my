import os
import re
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

# 替换为你的 Telegram Bot Token
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

app = Flask(__name__)
bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)

# 替换为源频道 ID 和目标频道 ID 的映射
SOURCE_TARGET_CHANNELS = {
    '@source_channel1': '@target_channel1',
    '@source_channel2': '@target_channel2',
    # 可以继续添加更多源频道和目标频道的映射
}

forwarded_message_ids = {}

def clean_text(text: str) -> str:
    text = re.sub(r'http\S+|www\S+|@\w+', '', text)
    return text.strip()

def forward_message(update: Update, context) -> None:
    source_channel_id = str(update.message.chat_id)
    if source_channel_id in SOURCE_TARGET_CHANNELS:
        target_channel_id = SOURCE_TARGET_CHANNELS[source_channel_id]
        text = update.message.text
        cleaned_text = clean_text(text)
        forwarded_message = bot.send_message(chat_id=target_channel_id, text=cleaned_text)
        if source_channel_id not in forwarded_message_ids:
            forwarded_message_ids[source_channel_id] = {}
        forwarded_message_ids[source_channel_id][update.message.message_id] = forwarded_message.message_id

def handle_message_deletion(update: Update, context) -> None:
    target_channel_id = str(update.message.chat_id)
    for source_channel_id, target_channel in SOURCE_TARGET_CHANNELS.items():
        if target_channel_id == target_channel:
            if source_channel_id in forwarded_message_ids:
                for source_msg_id, target_msg_id in forwarded_message_ids[source_channel_id].items():
                    if target_msg_id == update.message.message_id:
                        try:
                            bot.delete_message(chat_id=source_channel_id, message_id=source_msg_id)
                        except Exception as e:
                            print(f"Failed to delete message in source channel: {e}")
                        del forwarded_message_ids[source_channel_id][source_msg_id]
                if not forwarded_message_ids[source_channel_id]:
                    del forwarded_message_ids[source_channel_id]
            break

def start(update, context):
    update.message.reply_text('Bot is up and running!')

dispatcher.add_handler(MessageHandler(Filters.text & Filters.chat_type.channel, forward_message))
dispatcher.add_handler(MessageHandler(Filters.status_update.deleted_message & Filters.chat_type.channel, handle_message_deletion))
dispatcher.add_handler(CommandHandler('start', start))

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data(as_text=True)
    update = Update.de_json(json_str, bot)
    dispatcher.process_update(update)
    return 'ok'

@app.route('/')
def index():
    return 'Hello, this is a bot!'

if __name__ == '__main__':
    app.run(port=int(os.environ.get('PORT', 5000)))