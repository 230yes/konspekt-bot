import os
import json
import logging
import asyncio
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import requests

# Telegram библиотеки
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==================== НАСТРОЙКА ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Отключаем лишние логи
logging.getLogger('http.server').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)

# ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get('PORT', 10000))
webhook_history = []
bot_instance = None

if not TOKEN:
    logger.error("❌ BOT_TOKEN не найден! Добавьте в Render.")

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
            
            # Логируем команду
            webhook_history.append({
                'time': datetime.now().isoformat(),
                'type': 'command_start',
                'user_id': user.id,
                'username': user.username,
                'command': '/start'
            })
            
            await update.message.reply_text(
                f"👋 Привет, {user.first_name}!\n"
                f"Я Konspekt Bot. Ваш ID: `{user.id}`\n"
                f"Бот работает на Render!",
                parse_mode='Markdown'
            )
            logger.info(f"✅ Ответил на /start от {user.id}")
        
        async def help_cmd(update: Update, context):
            await update.message.reply_text(
                "📋 Помощь:\n"
                "/start - начать\n"
                "/id - ваш ID\n"
                "/site - сайт бота\n"
                "Просто напишите текст"
            )
        
        async def id_cmd(update: Update, context):
            user = update.effective_user
            await update.message.reply_text(f"🆔 Ваш ID: `{user.id}`", parse_mode='Markdown')
        
        async def site_cmd(update: Update, context):
            await update.message.reply_text(
                "🌐 Сайт бота:\n"
                "https://konspekt-bot.onrender.com\n\n"
                "Там можно:\n"
                "• Проверить статус бота\n"
                "• Настроить вебхук\n"
                "• Увидеть историю сообщений"
            )
        
        async def echo(update: Update, context):
            text = update.message.text
            
            # Логируем сообщение
            webhook_history.append({
                'time': datetime.now().isoformat(),
                'type': 'message',
                'user_id': update.effective_user.id,
                'text': text[:100] + ('...' if len(text) > 100 else '')
            })
            
            await update.message.reply_text(f"📝 Вы написали: {text}")
            logger.info(f"📨 Ответил на сообщение от {update.effective_user.id}")
        
        # Регистрация обработчиков
        self.app.add_handler(CommandHandler("start", start))
        self.app.add_handler(CommandHandler("help", help_cmd))
        self.app.add_handler(CommandHandler("id", id_cmd))
        self.app.add_handler(CommandHandler("site", site_cmd))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    async def process_update(self, update_data: dict):
        """Обработка вебхука от Telegram"""
        try:
            # Создаем объект Update из данных
            update = Update.de_json(update_data, self.app.bot)
            
            # Инициализируем и обрабатываем
            await self.app.initialize()
            await self.app.process_update(update)
            
            logger.info(f"✅ Обработан вебхук: {update.update_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки вебхука: {e}")
            return False
    
    def get_bot_info(self):
        """Получение информации о боте"""
        try:
            # Получаем информацию о боте асинхронно
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def get_info():
                return await self.app.bot.get_me()
            
            bot_info = loop.run_until_complete(get_info())
            loop.close()
            
            return {
                'id': bot_info.id,
                'username': bot_info.username,
                'first_name': bot_info.first_name
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о боте: {e}")
            return None

# ==================== HTTP СЕРВЕР ====================
class BotServer(BaseHTTPRequestHandler):
    
    def do_GET(self):
        """Обработка GET запросов"""
        try:
            if self.path == '/' or self.path == '':
                # Главная страница
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
            
            elif self.path == '/api/status':
                # API статуса
                status = {
                    'status': 'active' if TOKEN and bot_instance else 'error',
                    'message_count': len(webhook_history),
                    'webhook_url': f'https://{self.headers.get("Host", "konspekt-bot.onrender.com")}/webhook'
                }
                
                if TOKEN and bot_instance:
                    try:
                        bot_info = bot_instance.get_bot_info()
                        if bot_info:
                            status['bot_name'] = f"@{bot_info['username']}"
                        
                        # Проверяем вебхук
                        resp = requests.get(f'https://api.telegram.org/bot{TOKEN}/getWebhookInfo', timeout=5)
                        if resp.json().get('result', {}).get('url'):
                            status['webhook_set'] = True
                        else:
                            status['webhook_set'] = False
                            
                    except Exception as e:
                        status['status'] = 'error'
                        status['error'] = str(e)
                
                self.send_json(status)
            
            elif self.path == '/api/webhook-history':
                # История вебхуков
                self.send_json(webhook_history[-10:] if webhook_history else [])
            
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
                # ВЕБХУК от Telegram
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
                            # requests уже импортирован в начале файла
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
                
                # Логируем вебхук
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
        """Отключаем стандартное логирование запросов"""
        pass
            # ==================== HTML ШАБЛОН САЙТА ====================
HTML_TEMPLATE = '''<!DOCTYPE html>
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
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
        }
        .status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            background: #28a745;
            color: white;
            font-weight: bold;
            margin-top: 10px;
        }
        .status.error { background: #dc3545; }
        .status.warning { background: #ffc107; color: #333; }
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
        .btn-success { background: #28a745; }
        .btn-success:hover { background: #218838; }
        .webhook-item {
            background: white;
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            border-left: 4px solid #28a745;
            font-family: monospace;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Konspekt Bot</h1>
            <div class="status" id="status">Загрузка...</div>
        </div>
        
        <div class="card">
            <h3>📊 Статус бота</h3>
            <div id="botInfo">Загружаем информацию...</div>
            <button class="btn" onclick="refreshStatus()">Обновить</button>
            <button class="btn btn-success" onclick="setupWebhook()">Настроить вебхук</button>
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
    </div>

    <script>
        async function refreshStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                const statusEl = document.getElementById('status');
                if (data.status === 'active') {
                    statusEl.textContent = '✅ Активен';
                    statusEl.className = 'status';
                } else {
                    statusEl.textContent = '❌ Ошибка';
                    statusEl.className = 'status error';
                }
                
                document.getElementById('botInfo').innerHTML = `
                    Имя: ${data.bot_name || 'Неизвестно'}<br>
                    Вебхук: ${data.webhook_set ? '✅ Настроен' : '❌ Не настроен'}<br>
                    Сообщений: ${data.message_count || 0}<br>
                    URL: ${data.webhook_url || 'Не настроен'}
                `;
                
                // Загружаем историю
                const historyRes = await fetch('/api/webhook-history');
                const history = await historyRes.json();
                updateHistory(history);
                
            } catch (error) {
                document.getElementById('status').textContent = '⚠️ Нет связи';
                document.getElementById('status').className = 'status warning';
            }
        }
        
        function updateHistory(history) {
            const container = document.getElementById('webhookHistory');
            if (!history || history.length === 0) {
                container.innerHTML = 'Нет вебхуков';
                return;
            }
            
            let html = '';
            history.slice(-5).reverse().forEach(item => {
                html += `<div class="webhook-item">${item.time}: ${item.type} от ${item.user_id || 'unknown'}</div>`;
            });
            container.innerHTML = html;
        }
        
        async function setupWebhook() {
            const res = await fetch('/api/setup-webhook', { method: 'POST' });
            const data = await res.json();
            alert(data.message || (data.success ? 'Вебхук настроен!' : 'Ошибка'));
            refreshStatus();
        }
        
        function testBot() {
            alert('📱 Откройте Telegram и напишите боту /start');
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
# ==================== HTTP СЕРВЕР ====================
class BotServer(BaseHTTPRequestHandler):
    
    def do_GET(self):
        """Обработка GET запросов"""
        try:
            if self.path == '/' or self.path == '':
                # Главная страница
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
            
            elif self.path == '/api/status':
                # API статуса
                status = {
                    'status': 'active' if TOKEN and bot_instance else 'error',
                    'message_count': len(webhook_history),
                    'webhook_url': f'https://{self.headers.get("Host", "konspekt-bot.onrender.com")}/webhook'
                }
                
                if TOKEN and bot_instance:
                    try:
                        bot_info = bot_instance.get_bot_info()
                        if bot_info:
                            status['bot_name'] = f"@{bot_info['username']}"
                        
                        # Проверяем вебхук
                        resp = requests.get(f'https://api.telegram.org/bot{TOKEN}/getWebhookInfo', timeout=5)
                        if resp.json().get('result', {}).get('url'):
                            status['webhook_set'] = True
                        else:
                            status['webhook_set'] = False
                            
                    except Exception as e:
                        status['status'] = 'error'
                        status['error'] = str(e)
                
                self.send_json(status)
            
            elif self.path == '/api/webhook-history':
                # История вебхуков
                self.send_json(webhook_history[-10:] if webhook_history else [])
            
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
                # ВЕБХУК от Telegram
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
                
                # Логируем вебхук
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
        """Отключаем стандартное логирование запросов"""
        pass
        # ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================
def setup_webhook():
    """Настройка вебхука при запуске"""
    if not TOKEN:
        logger.error("❌ Не могу настроить вебхук: нет токена")
        return
    
    try:
        webhook_url = f"https://konspekt-bot.onrender.com/webhook"
        resp = requests.post(f'https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}', timeout=10)
        
        if resp.json().get('ok'):
            logger.info(f"✅ Вебхук настроен: {webhook_url}")
            return True
        else:
            logger.warning(f"⚠️ Не удалось настроить вебхук: {resp.json()}")
            return False
            
    except Exception as e:
        logger.warning(f"⚠️ Ошибка настройки вебхука: {e}")
        return False

def main():
    """Главная функция"""
    global bot_instance
    
    logger.info("=" * 50)
    logger.info("🚀 Запуск Konspekt Bot...")
    logger.info(f"🌐 Порт: {PORT}")
    logger.info(f"🤖 Токен: {'✅ Настроен' if TOKEN else '❌ Не настроен'}")
    logger.info("=" * 50)
    
    # Инициализируем бота
    if TOKEN:
        try:
            bot_instance = SimpleBot(TOKEN)
            logger.info("✅ Бот создан успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка создания бота: {e}")
            bot_instance = None
    
    # Настраиваем вебхук
    if bot_instance:
        setup_webhook()
    
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
