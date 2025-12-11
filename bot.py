import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==================== НАСТРОЙКА ====================
# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен ИЗ НАСТРОЕК RENDER (не из .env файла!)
TOKEN = os.environ.get('BOT_TOKEN')

if not TOKEN:
    logger.error("""
    ⚠️  ТОКЕН БОТА НЕ НАЙДЕН!
    
    На Render необходимо:
    1. Откройте Settings вашего сервиса
    2. Найдите 'Environment Variables'
    3. Нажмите 'Add Environment Variable'
    4. Введите:
        Key: BOT_TOKEN
        Value: ваш_токен_бота
    5. Нажмите 'Save Changes'
    6. Перезапустите деплой
    
    Пример токена: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
    """)
    exit(1)

logger.info("✅ Токен получен успешно!")

# ==================== ВСЕ ФУНКЦИИ БОТА ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    user = update.effective_user
    welcome_text = (
        f"🎉 Привет, {user.first_name}!\n\n"
        f"Твой ID: `{user.id}`\n"
        f"Я работаю на облачном хостинге Render!\n\n"
        "Доступные команды:\n"
        "• /help - все команды\n"
        "• /info - информация о боте\n"
        "• /id - твои данные\n"
        "• /calc <число> - умножить на 2\n"
        "• /echo <текст> - повторить текст"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')
    logger.info(f"Пользователь {user.id} использовал /start")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help"""
    help_text = (
        "🛠️ *ПОЛНЫЙ СПИСОК КОМАНД*\n\n"
        "📋 *Основные:*\n"
        "/start - начать работу\n"
        "/help - эта справка\n"
        "/info - о боте\n"
        "/id - ваши данные\n\n"
        "🔧 *Утилиты:*\n"
        "/calc <число> - умножить число на 2\n"
        "/echo <текст> - повторить текст\n"
        "/time - текущее время\n\n"
        "💬 *Просто отправьте любой текст,*\n"
        "*и бот его обработает!*"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /info"""
    info_text = (
        "🤖 *ИНФОРМАЦИЯ О БОТЕ*\n\n"
        "• *Хостинг:* Render (Web Service)\n"
        "• *Python:* 3.11.8\n"
        "• *Библиотека:* python-telegram-bot 20.7\n"
        "• *Статус:* Активен ✅\n"
        "• *Безопасность:* Токен в переменных окружения\n\n"
        "📊 *Статистика бота:*\n"
        "─ Авторские права отсутствуют\n"
        "─ Можно модифицировать как угодно\n"
        "─ Поддержка 24/7 на Render"
    )
    await update.message.reply_text(info_text, parse_mode='Markdown')

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /id"""
    user = update.effective_user
    chat = update.effective_chat
    
    id_text = (
        f"👤 *ВАШИ ДАННЫЕ*\n\n"
        f"*Пользователь:*\n"
        f"├ ID: `{user.id}`\n"
        f"├ Имя: {user.first_name or '—'}\n"
        f"├ Фамилия: {user.last_name or '—'}\n"
        f"└ Юзернейм: @{user.username or 'нет'}\n\n"
        f"*Чат:*\n"
        f"└ ID чата: `{chat.id}`\n\n"
        f"💡 *ID нужны для технической поддержки*"
    )
    await update.message.reply_text(id_text, parse_mode='Markdown')

async def calc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /calc <число>"""
    try:
        # Получаем число из аргумента команды
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите число!\n"
                "Пример: `/calc 5`", 
                parse_mode='Markdown'
            )
            return
        
        number = float(context.args[0])
        result = number * 2
        
        await update.message.reply_text(
            f"🧮 *Результат:*\n"
            f"{number} × 2 = *{result}*",
            parse_mode='Markdown'
        )
        logger.info(f"Вычисление: {number} * 2 = {result}")
        
    except ValueError:
        await update.message.reply_text(
            "❌ Это не число!\n"
            "Используйте: `/calc 5`", 
            parse_mode='Markdown'
        )

async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /echo <текст>"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите текст!\n"
            "Пример: `/echo Привет мир`", 
            parse_mode='Markdown'
        )
        return
    
    text = ' '.join(context.args)
    await update.message.reply_text(
        f"📢 *Эхо:*\n`{text}`",
        parse_mode='Markdown'
    )

async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /time"""
    from datetime import datetime
    import pytz
    
    moscow_tz = pytz.timezone('Europe/Moscow')
    moscow_time = datetime.now(moscow_tz)
    
    time_text = (
        f"🕐 *ТЕКУЩЕЕ ВРЕМЯ*\n\n"
        f"*Москва:* {moscow_time.strftime('%H:%M:%S')}\n"
        f"*Дата:* {moscow_time.strftime('%d.%m.%Y')}\n\n"
        f"⏰ Время сервера Render"
    )
    await update.message.reply_text(time_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ЛЮБЫХ текстовых сообщений (не команд)"""
    user_message = update.message.text
    
    # Разные ответы в зависимости от содержания
    if any(word in user_message.lower() for word in ['привет', 'hello', 'hi', 'здравствуй']):
        response = f"👋 И тебе привет, {update.effective_user.first_name}!"
    elif any(word in user_message.lower() for word in ['как дела', 'как ты', 'how are']):
        response = "🤖 У ботов дел не бывает, но спасибо, что спросил!"
    elif '?' in user_message:
        response = "❓ Хороший вопрос! Но я пока только учусь на него отвечать."
    else:
        # Считаем слова и символы
        word_count = len(user_message.split())
        char_count = len(user_message)
        
        response = (
            f"📝 *Получено сообщение*\n\n"
            f"*Текст:* `{user_message[:100]}{'...' if len(user_message) > 100 else ''}`\n\n"
            f"📊 *Статистика:*\n"
            f"• Символов: {char_count}\n"
            f"• Слов: {word_count}\n\n"
            f"💡 Используйте /help для списка команд"
        )
    
    await update.message.reply_text(response, parse_mode='Markdown')
    logger.info(f"Получено сообщение от {update.effective_user.id}: {user_message[:50]}...")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка НЕИЗВЕСТНЫХ команд"""
    await update.message.reply_text(
        "🤔 *Неизвестная команда!*\n\n"
        "Используйте /help для списка доступных команд.\n"
        "Или просто напишите мне сообщение!",
        parse_mode='Markdown'
    )

# ==================== ЗАПУСК БОТА ====================

async def main():
    """Главная функция запуска бота"""
    try:
        logger.info("🚀 Начинаю запуск бота...")
        
        # 1. Создаем приложение бота
        application = Application.builder().token(TOKEN).build()
        logger.info("✅ Приложение создано")
        
        # 2. Добавляем ВСЕ обработчики команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("info", info_command))
        application.add_handler(CommandHandler("id", id_command))
        application.add_handler(CommandHandler("calc", calc_command))
        application.add_handler(CommandHandler("echo", echo_command))
        application.add_handler(CommandHandler("time", time_command))
        logger.info("✅ Обработчики команд добавлены")
        
        # 3. Добавляем обработчик обычных сообщений
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )
        logger.info("✅ Обработчик сообщений добавлен")
        
        # 4. Добавляем обработчик неизвестных команд (ВСЕГДА ПОСЛЕДНИЙ!)
        application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
        logger.info("✅ Обработчик неизвестных команд добавлен")
        
        # 5. Запускаем бота
        logger.info("=" * 50)
        logger.info("🤖 БОТ УСПЕШНО ЗАПУЩЕН!")
        logger.info("📡 Ожидаю сообщений от пользователей...")
        logger.info("=" * 50)
        
        await application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            timeout=30
        )
        
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        raise

if __name__ == '__main__':
    try:
        # Запускаем асинхронный цикл
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️  Бот остановлен (Ctrl+C)")
    except Exception as e:
        logger.error(f"💥 Фатальная ошибка при запуске: {e}")
