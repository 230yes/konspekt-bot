import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== ТОЛЬКО для Render =====
# Получаем токен ИЗ ПАНЕЛИ УПРАВЛЕНИЯ Render
TOKEN = os.environ.get('BOT_TOKEN')  # os.environ, а не os.getenv()

if not TOKEN:
    logger.error("""
    ❌ ОШИБКА: Токен не найден!
    
    На Render добавьте переменную:
    1. Откройте Settings вашего сервиса
    2. Найдите 'Environment Variables'
    3. Нажмите 'Add Environment Variable'
    4. Введите:
        Key: BOT_TOKEN
        Value: ваш_токен_бота
    5. Нажмите 'Save Changes'
    6. Перезапустите деплой
    """)
    exit(1)

logger.info(f"✅ Токен получен, запускаю бота...")

# Основной код бота
async def start(update: Update, context):
    await update.message.reply_text('✅ Бот работает на Render!')

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    logger.info("🤖 Бот запущен и ожидает сообщений...")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
