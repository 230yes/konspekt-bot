import os
import asyncio
import logging
import sys
from telegram.ext import Application, CommandHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    logger.error("❌ ОШИБКА: Токен не найден! Проверьте переменную BOT_TOKEN в настройках Render.")
    sys.exit(1)

# Основные функции бота
async def start(update, context):
    await update.message.reply_text('✅ Бот успешно работает на Render!')

async def help(update, context):
    await update.message.reply_text('/start - Запустить бота\n/help - Эта справка')

# Функция запуска бота
async def run_bot():
    """Асинхронная функция для запуска бота"""
    try:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help))
        
        logger.info("🤖 Запускаю polling бота...")
        await app.run_polling(
            drop_pending_updates=True,
            close_loop=False  # Ключевой параметр!
        )
    except Exception as e:
        logger.error(f"Ошибка в run_bot: {e}")
        raise

# Главная функция
def main():
    """Основная точка входа, совместимая с Render"""
    logger.info("🚀 Инициализация бота...")
    
    try:
        # Проверяем, есть ли уже запущенный event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Если loop уже запущен, запускаем задачу внутри него
        if loop.is_running():
            logger.info("🔄 Использую существующий event loop Render")
            task = loop.create_task(run_bot())
            
            # Ждем завершения задачи (блокирующий вызов)
            try:
                loop.run_until_complete(task)
            except KeyboardInterrupt:
                logger.info("⏹️ Получен сигнал прерывания")
            except Exception as e:
                logger.error(f"Ошибка при выполнении задачи: {e}")
        else:
            # Если loop не запущен, запускаем стандартно
            logger.info("🆕 Создаю новый event loop")
            loop.run_until_complete(run_bot())
            
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"💥 Фатальная ошибка: {e}")
        sys.exit(1)

# Точка входа
if __name__ == '__main__':
    main()
