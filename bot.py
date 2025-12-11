import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен вашего бота (замените на свой)
TOKEN = "YOUR_BOT_TOKEN_HERE"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text('Привет! Я бот. 🤖\nИспользуйте /help для списка команд.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
Доступные команды:
/start - Начать диалог
/help - Показать это сообщение
"""
    await update.message.reply_text(help_text)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Эхо-обработчик для текстовых сообщений"""
    await update.message.reply_text(f'Вы сказали: {update.message.text}')

async def main():
    """Основная функция для запуска бота"""
    try:
        # Создаем приложение бота
        application = ApplicationBuilder().token(TOKEN).build()
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        
        # Добавляем обработчик для текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
        # Запускаем бота в режиме polling
        logger.info("Бот запущен...")
        await application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")

if __name__ == '__main__':
    # Запускаем асинхронную функцию main
    asyncio.run(main())
