import asyncio
import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from dotenv import load_dotenv

# ==================== НАСТРОЙКА ====================
# 1. Загружаем переменные из файла .env
load_dotenv()

# 2. Получаем токен из переменной окружения
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    # Сообщение для разработчика, если токен не найден
    raise ValueError(
        "❌ ТОКЕН БОТА НЕ НАЙДЕН!\n"
        "Убедитесь, что:\n"
        "  1. В корне проекта есть файл '.env'\n"
        "  2. В нём есть строка: BOT_TOKEN=ваш_токен\n"
        "  3. Для продакшена (Render): токен задан в настройках Environment Variables"
    )

# 3. Настраиваем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== ОБРАБОТЧИКИ КОМАНД ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start"""
    user = update.effective_user
    welcome_text = (
        f"Привет, {user.first_name}! 👋\n"
        "Я ваш Telegram-бот.\n"
        "Напишите что-нибудь, и я отвечу."
    )
    await update.message.reply_text(welcome_text)
    logger.info(f"Пользователь {user.id} ({user.first_name}) запустил бота.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /help"""
    help_text = (
        "📚 *Доступные команды:*\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/about - О боте\n\n"
        "Просто отправьте мне любое текстовое сообщение."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /about"""
    about_text = (
        "🤖 *О боте*\n"
        "Этот бот создан как безопасный шаблон.\n"
        "Он использует переменные окружения для хранения токена.\n"
        "Вы можете легко расширить его функционал."
    )
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Эхо-ответ на любое текстовое сообщение"""
    user_message = update.message.text
    # Можно добавить логику обработки сообщения здесь
    reply = f"Вы написали:\n`{user_message}`"
    await update.message.reply_text(reply, parse_mode='Markdown')

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает неизвестные команды"""
    await update.message.reply_text(
        "🤔 Не понимаю эту команду.\n"
        "Используйте /help для списка доступных команд."
    )

# ==================== ЗАПУСК БОТА ====================

async def main():
    """Основная функция для настройки и запуска бота"""
    logger.info("Инициализация приложения бота...")
    
    # Создаем приложение с использованием токена
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    
    # Обработчик для текстовых сообщений (все, кроме команд)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message)
    )
    
    # Обработчик для неизвестных команд (должен быть последним!)
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    # Запускаем бота
    logger.info("Бот запущен и ожидает обновлений...")
    await application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True  # Игнорируем сообщения, отправленные, пока бот был офлайн
    )

if __name__ == '__main__':
    # Запускаем асинхронную основную функцию
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Работа бота завершена пользователем.")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
