import os
import asyncio
import logging
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import Application, CommandHandler

# ==================== НАСТРОЙКА ЛОГОВ ====================
# Полностью отключаем асинхронные предупреждения
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Простое логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Отключаем все лишние логи
for name in ['http.server', 'telegram', 'apscheduler', 'hpack', 'asyncio']:
    logging.getLogger(name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ==================== HTTP СЕРВЕР ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')
    
    def log_message(self, *args):
        pass

def run_http_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"HTTP сервер запущен на порту {port}")
    server.serve_forever()

# ==================== КОМАНДЫ БОТА ====================
async def start(update, context):
    await update.message.reply_text('✅ Бот работает!')

async def help_cmd(update, context):
    await update.message.reply_text('/start - запуск\n/id - ваш ID')

async def id_cmd(update, context):
    await update.message.reply_text(f'Ваш ID: {update.effective_user.id}')

# ==================== ОСНОВНОЙ КОД ====================
def run_telegram_bot():
    """Запуск Telegram бота в отдельном потоке"""
    token = os.environ.get('BOT_TOKEN')
    if not token:
        logger.error("Ошибка: токен не найден")
        return
    
    # Создаем НОВЫЙ event loop для бота
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def bot_main():
        try:
            # Создаем приложение
            app = Application.builder().token(token).build()
            
            # Добавляем команды
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("help", help_cmd))
            app.add_handler(CommandHandler("id", id_cmd))
            
            logger.info("Бот инициализирован, запускаю polling...")
            
            # Запускаем бота с правильными параметрами
            await app.run_polling(
                drop_pending_updates=True,
                close_loop=False,
                stop_signals=[]  # Не обрабатываем сигналы
            )
        except Exception as e:
            logger.error(f"Ошибка в боте: {e}")
        finally:
            logger.info("Бот завершил работу")
    
    try:
        loop.run_until_complete(bot_main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    finally:
        loop.close()

def main():
    """Главная функция"""
    logger.info("=== Запуск сервиса ===")
    
    # Проверяем токен
    if not os.environ.get('BOT_TOKEN'):
        logger.error("Установите BOT_TOKEN в настройках Render")
        sys.exit(1)
    
    # Запускаем HTTP сервер в отдельном потоке
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    logger.info("HTTP сервер запущен")
    
    # Запускаем Telegram бота в отдельном потоке
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    logger.info("Telegram бот запущен")
    
    # Держим основной поток активным
    try:
        # Просто ждем вечно
        while True:
            threading.Event().wait(3600)  # Ждем час
    except KeyboardInterrupt:
        logger.info("Завершение работы...")
    except Exception as e:
        logger.error(f"Ошибка: {e}")

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    main()
