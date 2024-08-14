import os
import re
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
from telegram.ext import CallbackContext

# 环境变量
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# 创建 Flask 应用和 Telegram Bot 实例
app = Flask(__name__)
bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)

# 源频道和目标频道映射
SOURCE_TARGET_CHANNELS = {
    '@source_channel1': '@target_channel1',
    '@source_channel2': '@target_channel2',
    # 可以继续添加更多源频道和目标频道的映射
}

forwarded_message_ids = {}

def clean_text(text: str) -> str:
    """清理文本中的链接和用户名"""
    return re.sub(r'http\S+|www\S+|@\w+', '', text).strip()

def forward_message(update: Update, context: CallbackContext) -> None:
    """转发消息"""
    source_channel_id = str(update.message.chat_id)
    if source_channel_id in SOURCE_TARGET_CHANNELS:
        target_channel_id = SOURCE_TARGET_CHANNELS[source_channel_id]
        text = update.message.text
        cleaned_text = clean_text(text)
        try:
            forwarded_message = bot.send_message(chat_id=target_channel_id, text=cleaned_text)
            forwarded_message_ids.setdefault(source_channel_id, {})[update.message.message_id] = forwarded_message.message_id
        except Exception as e:
            print(f"Failed to forward message: {e}")

def handle_message_deletion(update: Update, context: CallbackContext) -> None:
    """处理消息删除"""
    target_channel_id = str(update.message.chat_id)
    for source_channel_id, target_channel in SOURCE_TARGET_CHANNELS.items():
        if target_channel_id == target_channel:
            if source_channel_id in forwarded_message_ids:
                for source_msg_id, target_msg_id in forwarded_message_ids[source_channel_id].items():
                    if target_msg_id == update.message.message_id:
                        try:
                            bot.delete_message(chat_id=source_channel_id, message_id=source_msg_id)
                            del forwarded_message_ids[source_channel_id][source_msg_id]
                        except Exception as e:
                            print(f"Failed to delete message in source channel: {e}")
                if not forwarded_message_ids[source_channel_id]:
                    del forwarded_message_ids[source_channel_id]
            break

def start(update: Update, context: CallbackContext) -> None:
    """处理 /start 命令"""
    update.message.reply_text('Bot is up and running!')

# 添加处理程序到 Dispatcher
dispatcher.add_handler(MessageHandler(Filters.text & Filters.chat_type.channel, forward_message))
dispatcher.add_handler(MessageHandler(Filters.status_update.deleted_message & Filters.chat_type.channel, handle_message_deletion))
dispatcher.add_handler(CommandHandler('start', start))

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook() -> str:
    """处理来自 Telegram 的 Webhook 更新"""
    json_str = request.get_data(as_text=True)
    update = Update.de_json(json_str, bot)
    dispatcher.process_update(update)
    return 'ok'

@app.route('/')
def index() -> str:
    """根路由"""
    return 'Hello, this is a bot!'

if __name__ == '__main__':
    # 设置 Webhook
    if WEBHOOK_URL:
        try:
            bot.set_webhook(url=WEBHOOK_URL)
        except Exception as e:
            print(f"Failed to set webhook: {e}")

    # 运行 Flask 应用，监听所有网络接口
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)