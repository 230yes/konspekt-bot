import os
import asyncio
import logging
import signal
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен ИЗ НАСТРОЕК RENDER
TOKEN = os.environ.get('BOT_TOKEN')

if not TOKEN:
    logger.error("""
    ⚠️  ТОКЕН БОТА НЕ НАЙДЕН!
    
    На Render необходимо добавить переменную окружения:
    Key: BOT_TOKEN
    Value: ваш_токен_бота
    
    Пример токена: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
    """)
    exit(1)

logger.info("✅ Токен получен успешно!")

# Глобальная переменная для приложения
application = None

# Функция для корректной остановки
async def shutdown(signal=None):
    """Корректная остановка бота"""
    if signal:
        logger.info(f"📴 Получен сигнал {signal.name}, останавливаю бота...")
    
    if application and application.running:
        logger.info("🛑 Останавливаю polling...")
        await application.stop()
        
        logger.info("⏳ Жду завершения обновлений...")
        await application.updater.stop()
        
        logger.info("🔌 Закрываю приложение...")
        await application.shutdown()
    
    logger.info("✅ Бот успешно остановлен")

# Обработка сигналов остановки
def signal_handler():
    """Обработчик сигналов ОС"""
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda s, f: asyncio.create_task(shutdown(s)))

async def main():
    """Главная функция запуска бота"""
    global application
    
    try:
        logger.info("🚀 Начинаю запуск бота...")
        
        # 1. Создаем приложение бота
        application = Application.builder().token(TOKEN).build()
        logger.info("✅ Приложение создано")
        
        # 2. Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("id", id_command))
        logger.info("✅ Обработчики команд добавлены")
        
        # 3. Настраиваем обработку сигналов
        signal_handler()
        
        # 4. Запускаем бота
        logger.info("=" * 50)
        logger.info("🤖 БОТ УСПЕШНО ЗАПУЩЕН!")
        logger.info("📡 Ожидаю сообщений от пользователей...")
        logger.info("=" * 50)
        
        # Запускаем polling с правильной обработкой остановки
        await application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False  # ВАЖНО: не закрываем цикл событий
        )
        
    except asyncio.CancelledError:
        logger.info("⏹️  Работа бота отменена")
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        raise

# ==================== ПРОСТЫЕ ФУНКЦИИ БОТА ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    await update.message.reply_text('✅ Бот работает на Render!')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help"""
    await update.message.reply_text('/start - запустить бота\n/help - помощь\n/id - ваш ID')

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /id"""
    await update.message.reply_text(f'Ваш ID: {update.effective_user.id}')

# ==================== ТОЧКА ВХОДА ====================

if __name__ == '__main__':
    try:
        # Запускаем главную функцию
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("⏹️  Бот остановлен вручную")
    except Exception as e:
        logger.error(f"💥 Фатальная ошибка: {e}")
