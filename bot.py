# ==================== ИМПОРТЫ И НАСТРОЙКИ ====================
import os
import json
import logging
import asyncio
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get('PORT', 10000))
webhook_history = []
bot_instance = None

if not TOKEN:
    logger.error("❌ BOT_TOKEN не найден! Добавьте в Render.")
    # ==================== HTML САЙТА ====================
HTML_HEAD = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Konspekt Bot</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f0f2f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            background: #28a745;
            color: white;
            font-weight: bold;
        }
        .card {
            background: #f8f9fa;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }
        .btn {
            display: inline-block;
            padding: 10px 20px;
            margin: 5px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            border: none;
            cursor: pointer;
        }
        .btn:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Konspekt Bot</h1>
            <div class="status" id="status">Загрузка...</div>
        </div>
'''

HTML_BODY = '''
        <div class="card">
            <h3>📊 Статус бота</h3>
            <div id="botInfo">Загружаем информацию...</div>
            <button class="btn" onclick="refreshStatus()">Обновить</button>
            <button class="btn" onclick="setupWebhook()">Настроить вебхук</button>
        </div>

        <div class="card">
            <h3>📨 История вебхуков</h3>
            <div id="webhookHistory">Нет данных</div>
        </div>

        <div class="card">
            <h3>🔧 Быстрые действия</h3>
            <button class="btn" onclick="testBot()">Тест бота</button>
            <a href="https://t.me/Konspekt_help_bot" class="btn" target="_blank">Открыть в Telegram</a>
            <button class="btn" onclick="clearHistory()">Очистить историю</button>
        </div>
'''

HTML_FOOT = '''
    </div>

    <script>
        async function refreshStatus() {
            const res = await fetch('/api/status');
            const data = await res.json();
            
            document.getElementById('status').textContent = 
                data.status === 'active' ? '✅ Активен' : '❌ Ошибка';
            
            document.getElementById('botInfo').innerHTML = `
                Имя: ${data.bot_name || 'Неизвестно'}<br>
                Вебхук: ${data.webhook_set ? '✅ Настроен' : '❌ Не настроен'}<br>
                Сообщений: ${data.message_count || 0}
            `;
        }

        async function setupWebhook() {
            const res = await fetch('/api/setup-webhook', { method: 'POST' });
            const data = await res.json();
            alert(data.message);
            refreshStatus();
        }

        async function testBot() {
            alert('Откройте Telegram и напишите боту /start');
        }

        async function clearHistory() {
            await fetch('/api/clear-history', { method: 'POST' });
            alert('История очищена');
            refreshStatus();
        }

        // Автообновление
        setInterval(refreshStatus, 5000);
        document.addEventListener('DOMContentLoaded', refreshStatus);
    </script>
</body>
</html>'''
# ==================== КЛАСС TELEGRAM БОТА ====================
class SimpleBot:
    def __init__(self, token: str):
        self.token = token
        self.app = Application.builder().token(token).build()
        self.setup_handlers()
        logger.info("✅ Бот инициализирован")
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        
        async def start(update: Update, context):
            user = update.effective_user
            await update.message.reply_text(
                f"👋 Привет, {user.first_name}!\n"
                f"Я Konspekt Bot. Ваш ID: {user.id}\n"
                f"Бот работает на Render!"
            )
            # Логируем
            webhook_history.append({
                'time': datetime.now().isoformat(),
                'type': 'command_start',
                'user_id': user.id
            })
        
        async def help_cmd(update: Update, context):
            await update.message.reply_text(
                "Помощь:\n"
                "/start - начать\n"
                "/id - ваш ID\n"
                "/site - сайт бота\n"
                "Просто напишите текст"
            )
        
        async def id_cmd(update: Update, context):
            await update.message.reply_text(f"Ваш ID: {update.effective_user.id}")
        
        async def echo(update: Update, context):
            text = update.message.text
            await update.message.reply_text(f"Вы написали: {text}")
            # Логируем
            webhook_history.append({
                'time': datetime.now().isoformat(),
                'type': 'message',
                'user_id': update.effective_user.id,
                'text': text[:50]
            })
        
        # Регистрация обработчиков
        self.app.add_handler(CommandHandler("start", start))
        self.app.add_handler(CommandHandler("help", help_cmd))
        self.app.add_handler(CommandHandler("id", id_cmd))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    async def process_update(self, update_data: dict):
        """Обработка вебхука"""
        try:
            update = Update.de_json(update_data, self.app.bot)
            await self.app.initialize()
            await self.app.process_update(update)
            return True
        except Exception as e:
            logger.error(f"Ошибка обработки: {e}")
            return False
            # ==================== HTTP СЕРВЕР ====================
class BotServer(BaseHTTPRequestHandler):
    
    def do_GET(self):
        """Обработка GET запросов"""
        try:
            if self.path == '/':
                # Главная страница
                html = HTML_HEAD + HTML_BODY + HTML_FOOT
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
            
            elif self.path == '/api/status':
                # API статуса
                status = {'status': 'active' if TOKEN else 'error'}
                if TOKEN and bot_instance:
                    try:
                        # Проверка вебхука
                        resp = requests.get(f'https://api.telegram.org/bot{TOKEN}/getWebhookInfo', timeout=5)
                        if resp.json().get('result', {}).get('url'):
                            status['webhook_set'] = True
                        else:
                            status['webhook_set'] = False
                    except:
                        status['webhook_set'] = False
                
                status['message_count'] = len(webhook_history)
                self.send_json(status)
            
            elif self.path == '/health':
                # Health check для Render
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'OK')
            
            else:
                self.send_error(404, "Not Found")
                
        except Exception as e:
            logger.error(f"GET ошибка: {e}")
            self.send_error(500, str(e))
    
    def do_POST(self):
        """Обработка POST запросов"""
        try: 
    if self.path == '/webhook':
    # ========== НОВЫЙ КОД (замените старый) ==========
    content_len = int(self.headers.get('Content-Length', 0))
    post_data = self.rfile.read(content_len)
    update_data = json.loads(post_data.decode('utf-8'))
    
    # ⭐⭐ ОТЛАДОЧНЫЙ ВЫВОД ⭐⭐
    print("=" * 60)
    print("🔥 ВЕБХУК ПОЛУЧЕН ОТ TELEGRAM!")
    print(f"📊 Тип обновления: {list(update_data.keys())}")
    print(f"🆔 Update ID: {update_data.get('update_id')}")
    
    # Проверяем, что это сообщение
    if 'message' in update_data:
        message = update_data['message']
        print(f"💬 Сообщение от: {message.get('from', {}).get('id')}")
        print(f"📝 Текст: {message.get('text', 'Нет текста')}")
        
        # Если это /start, пробуем ответить напрямую
        if message.get('text') == '/start':
            print("✅ Обнаружена команда /start, пытаюсь ответить...")
            
            try:
                chat_id = message['chat']['id']
                token = os.environ.get('BOT_TOKEN')
                
                # Отправляем тестовый ответ через API
                import requests
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {
                    'chat_id': chat_id,
                    'text': '✅ Тест: бот получил ваш /start!',
                    'parse_mode': 'Markdown'
                }
                response = requests.post(url, json=data, timeout=5)
                print(f"📤 Тестовый ответ отправлен, статус: {response.status_code}")
                print(f"📋 Ответ Telegram: {response.json()}")
                
            except Exception as e:
                print(f"❌ Ошибка отправки тестового ответа: {e}")
                import traceback
                traceback.print_exc()
    else:
        print(f"⚠️ Это не сообщение, а: {list(update_data.keys())}")
    
    print("=" * 60)
    # ========== КОНЕЦ НОВОГО КОДА ==========
    
    # Продолжаем обычную обработку через бота
    logger.info(f"📨 Вебхук получен: {update_data.get('update_id')}")
    
    # Обрабатываем через бота
    if bot_instance:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(bot_instance.process_update(update_data))
        loop.close()
        print(f"🤖 Обработка ботом: {'✅ Успех' if success else '❌ Ошибка'}")
    
    self.send_response(200)
    self.send_header('Content-type', 'application/json')
    self.end_headers()
    self.wfile.write(json.dumps({'ok': True}).encode())
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True}).encode())
            
            elif self.path == '/api/setup-webhook':
                # Настройка вебхука
                if not TOKEN:
                    self.send_json({'success': False, 'message': 'Нет токена'})
                    return
                
                webhook_url = f"https://{self.headers.get('Host', 'konspekt-bot.onrender.com')}/webhook"
                resp = requests.post(f'https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}')
                
                if resp.json().get('ok'):
                    self.send_json({'success': True, 'message': 'Вебхук настроен!'})
                else:
                    self.send_json({'success': False, 'message': 'Ошибка настройки'})
            
            elif self.path == '/api/clear-history':
                webhook_history.clear()
                self.send_json({'success': True, 'message': 'История очищена'})
            
            else:
                self.send_error(404, "Not Found")
                
        except Exception as e:
            logger.error(f"POST ошибка: {e}")
            self.send_error(500, str(e))
    
    def send_json(self, data):
        """Отправка JSON ответа"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Отключаем стандартное логирование"""
        pass
        # ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================
def setup_webhook():
    """Настройка вебхука при запуске"""
    if not TOKEN:
        logger.error("Не могу настроить вебхук: нет токена")
        return
    
    try:
        webhook_url = f"https://konspekt-bot.onrender.com/webhook"
        resp = requests.post(f'https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}', timeout=10)
        
        if resp.json().get('ok'):
            logger.info(f"✅ Вебхук настроен: {webhook_url}")
        else:
            logger.warning(f"⚠️ Не удалось настроить вебхук: {resp.json()}")
    except Exception as e:
        logger.warning(f"⚠️ Ошибка настройки вебхука: {e}")

def main():
    """Главная функция"""
    global bot_instance
    
    logger.info("=" * 50)
    logger.info("🚀 Запуск Konspekt Bot...")
    logger.info(f"🌐 Порт: {PORT}")
    logger.info(f"🤖 Токен: {'Настроен' if TOKEN else 'Не настроен'}")
    logger.info("=" * 50)
    
    # Инициализируем бота
    if TOKEN:
        try:
            bot_instance = SimpleBot(TOKEN)
            setup_webhook()
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации бота: {e}")
    
    # Запускаем сервер
    server = HTTPServer(('0.0.0.0', PORT), BotServer)
    
    logger.info(f"✅ Сервер запущен: http://0.0.0.0:{PORT}")
    logger.info(f"✅ Вебхук: https://konspekt-bot.onrender.com/webhook")
    logger.info("⏳ Ожидание запросов...")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("⏹️ Сервер остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка сервера: {e}")

# ==================== ТОЧКА ВХОДА ====================
if __name__ == '__main__':
    main()
