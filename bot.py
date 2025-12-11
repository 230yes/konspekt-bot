import os
import asyncio
import logging
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import Application, CommandHandler

# ==================== ЧИСТОЕ ЛОГИРОВАНИЕ ====================
class CleanFormatter(logging.Formatter):
    def format(self, record):
        # Убираем все объектные представления из сообщений
        message = record.getMessage()
        # Убираем возможные представления объектов в сообщениях
        if 'object at 0x' in message:
            message = message.split('object at 0x')[0].strip()
        record.msg = message
        return super().format(record)

# Настройка логгера
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(CleanFormatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S'))

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.handlers = [handler]  # Заменяем все обработчики

# Отключаем ненужные логи
logging.getLogger('http.server').disabled = True
logging.getLogger('telegram').setLevel(logging.ERROR)

# ==================== HTTP СЕРВЕР ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, *args):
        pass  # Без логов

def run_http_server(port=8080):
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"HTTP сервер запущен на порту {port}")
    server.serve_forever()

# ==================== ФУНКЦИИ БОТА ====================
async def start(update, context):
    await update.message.reply_text('🚀 Бот запущен')

async def help_cmd(update, context):
    await update.message.reply_text('/start, /help, /id')

async def get_id(update, context):
    await update.message.reply_text(f'ID: {update.effective_user.id}')

# ==================== ОСНОВНОЙ КОД ====================
def main():
    print("=== Запуск бота ===")
    
    TOKEN = os.environ.get('BOT_TOKEN')
    if not TOKEN:
        print("ОШИБКА: Нет токена")
        sys.exit(1)
    
    # HTTP сервер
    port = int(os.environ.get('PORT', 10000))
    http_thread = threading.Thread(
        target=run_http_server, 
        args=(port,), 
        daemon=True
    )
    http_thread.start()
    
    # Основной event loop
    async def bot_main():
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_cmd))
        app.add_handler(CommandHandler("id", get_id))
        
        print("Бот запускается...")
        await app.run_polling(drop_pending_updates=True, close_loop=False)
    
    try:
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        print("Бот остановлен")
    except Exception as e:
        print(f"Ошибка: {str(e)}")

if __name__ == '__main__':
    main()
