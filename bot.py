import os
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# ==================== НАСТРОЙКА ====================

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения Render
TOKEN = os.environ.get('BOT_TOKEN')

if not TOKEN:
    logger.error("""
    ⚠️  ТОКЕН БОТА НЕ НАЙДЕН!
    
    На Render необходимо:
    1. Перейти в настройки сервиса (Settings)
    2. Найти раздел 'Environment Variables'
    3. Добавить переменную:
        Key: BOT_TOKEN
        Value: ваш_настоящий_токен_бота
    
    Токен должен начинаться с цифр, например: 1234567890:ABCdefGHIjkl...
    """)
    exit(1)

logger.info("✅ Токен получен, запускаю бота...")

# ==================== ОБРАБОТЧИКИ КОМАНД ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start"""
    user = update.effective_user
    welcome_text = (
        f"Привет, {user.first_name}! 👋\n"
        f"Твой ID: {user.id}\n\n"
        "Я работаю на Render! 🚀\n"
        "Используй /help для списка команд."
    )
    await update.message.reply_text(welcome_text)
    logger.info(f"Пользователь {user.id} запустил бота")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /help"""
    help_text = (
        "📋 *Доступные команды:*\n"
        "/start - Начать работу\n"
        "/help - Эта справка\n"
        "/id - Показать твой ID\n"
        "/info - Информация о боте\n\n"
        "Просто напиши мне что-нибудь, и я отвечу!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /id"""
    user = update.effective_user
    chat = update.effective_chat
    
    id_text = (
        f"👤 *Твои данные:*\n"
        f"• ID пользователя: `{user.id}`\n"
        f"• ID чата: `{chat.id}`\n"
        f"• Имя: {user.first_name or '—'}\n"
        f"• Фамилия: {user.last_name or '—'}\n"
        f"• Юзернейм: @{user.username or '—'}"
    )
    await update.message.reply_text(id_text, parse_mode='Markdown')

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /info"""
    info_text = (
        "🤖 *Информация о боте*\n\n"
        "• *Платформа:* Render\n"
        "• *Хостинг:* Web Service\n"
        "• *Библиотека:* python-telegram-bot 20.7\n"
        "• *Статус:* Активен ✅\n\n"
        "Бот использует переменные окружения\n"
        "для безопасного хранения токена."
    )
    await update.message.reply_text(info_text, parse_mode='Markdown')

async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Эхо-ответ на текстовые сообщения"""
    user_message = update.message.text
    response = f"📝 Ты написал:\n```\n{user_message}\n```\n\nКоличество символов: {len(user_message)}"
    await update.message.reply_text(response, parse_mode='Markdown')

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает неизвестные команды"""
    await update.message.reply_text(
        "🤔 Не знаю такой команды.\n"
        "Попробуй /help для списка команд."
    )

# ==================== ЗАПУСК БОТА ====================

async def main():
    """Основная функция запуска бота"""
    try:
        # Создаем приложение бота
        application = Application.builder().token(TOKEN).build()
        
        # Регистрируем обработчики команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("id", id_command))
        application.add_handler(CommandHandler("info", info_command))
        
        # Обработчик текстовых сообщений
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message)
        )
        
        # Обработчик неизвестных команд (последний!)
        application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
        
        # Запускаем бота
        logger.info("🚀 Бот успешно запущен и готов к работе!")
        logger.info("📡 Ожидаю сообщений...")
        
        await application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️  Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"💥 Фатальная ошибка: {e}")
