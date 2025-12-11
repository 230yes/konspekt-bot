import os
import asyncio
import logging
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import Application, CommandHandler

# ==================== ЧИСТОЕ ЛОГИРОВАНИЕ ====================
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S'
)

# Отключаем ненужные логи
logging.getLogger('http.server').disabled = True
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('apscheduler').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ==================== HTTP СЕРВЕР ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, *args):
        pass  # Без логов

def run_http_server(port=8080):
    """Запускает HTTP-сервер в отдельном потоке"""
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"HTTP-сервер запущен на порту {port}")
    server.serve_forever()

# ==================== ФУНКЦИИ БОТА ====================
async def start_command(update, context):
    await update.message.reply_text('🚀 Бот запущен и работает на Render!')

async def help_command(update, context):
    help_text = (
        "Доступные команды:\n"
        "/start - Запустить бота\n"
        "/help - Показать справку\n"
        "/id - Показать ваш ID"
    )
    await update.message.reply_text(help_text)

async def id_command(update, context):
    user_id = update.effective_user.id
    await update.message.reply_text(f'Ваш ID: `{user_id}`', parse_mode='Markdown')

# ==================== АСИНХРОННАЯ ИНИЦИАЛИЗАЦИЯ ====================
async def init_bot():
    """Инициализирует и запускает бота"""
    TOKEN = os.environ.get('BOT_TOKEN')
    if not TOKEN:
        logger.error("Токен бота не найден. Установите BOT_TOKEN в настройках Render.")
        sys.exit(1)
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("id", id_command))
    
    return application

# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================
def main():
    """Точка входа для Render"""
    logger.info("Запуск Telegram бота...")
    
    # Проверяем токен
    TOKEN = os.environ.get('BOT_TOKEN')
    if not TOKEN:
        logger.error("Токен бота не найден")
        sys.exit(1)
    
    # Запускаем HTTP-сервер в отдельном потоке
    port = int(os.environ.get('PORT', 10000))
    http_thread = threading.Thread(
        target=run_http_server,
        args=(port,),
        daemon=True
    )
    http_thread.start()
    logger.info(f"HTTP сервер запущен на порту {port}")
    
    try:
        # Получаем текущий event loop
        try:
            loop = asyncio.get_running_loop()
            logger.info("Обнаружен запущенный event loop (Render)")
        except RuntimeError:
            # Если нет запущенного loop, создаем новый
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            logger.info("Создан новый event loop")
        
        # Функция для запуска бота внутри loop
        async def start_bot():
            application = await init_bot()
            logger.info("Бот инициализирован, запускаю polling...")
            await application.run_polling(
                drop_pending_updates=True,
                close_loop=False,  # Ключевой параметр!
                stop_signals=None   # Отключаем обработку сигналов
            )
        
        # Если loop уже запущен (типичный случай на Render)
        if loop.is_running():
            # Запускаем асинхронную задачу в существующем loop
            bot_task = loop.create_task(start_bot())
            
            # Просто возвращаем задачу, не блокируем
            # На Render loop будет работать вечно
            try:
                # Небольшая задержка для видимости в логах
                import time
                time.sleep(2)
                logger.info("Бот успешно запущен в фоновом режиме")
                # Вечный цикл для поддержания работы
                while True:
                    time.sleep(3600)  # Спим час, потом проверяем снова
            except KeyboardInterrupt:
                logger.info("Получен сигнал остановки")
                bot_task.cancel()
        else:
            # Если loop не запущен, запускаем его
            loop.run_until_complete(start_bot())
            
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)[:100]}...")
        sys.exit(1)

# ==================== ТОЧКА ВХОДА ====================
if __name__ == '__main__':
    main()
