import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Any
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==================== НАСТРОЙКА ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальные переменные для обмена данными между модулями
webhook_history: List[Dict[str, Any]] = []
MAX_HISTORY = 100

# Получение токена (будет установлен из web_server.py)
TOKEN = None
bot_instance = None

def init_bot(token: str):
    """Инициализация бота с токеном (вызывается из web_server.py)"""
    global TOKEN, bot_instance
    TOKEN = token
    bot_instance = KonspektBot()
    return bot_instance

class KonspektBot:
    def __init__(self):
        if not TOKEN:
            raise ValueError("Токен бота не установлен!")
        
        self.application = Application.builder().token(TOKEN).build()
        self.bot = self.application.bot
        self.setup_handlers()
        logger.info("✅ Бот KonspektBot инициализирован")
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        # Команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("id", self.id_command))
        self.application.add_handler(CommandHandler("site", self.site_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Текстовые сообщения
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo)
        )
        
        # Обработчик ошибок
        self.application.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        
        # Логируем вебхук
        self._log_webhook({
            'timestamp': datetime.now().timestamp(),
            'type': 'command_start',
            'user_id': user.id,
            'username': user.username,
            'command': '/start'
        })
        
        welcome_text = (
            f"👋 Привет, {user.first_name}!\n\n"
            f"Я *Konspekt Helper Bot* — твой помощник в создании конспектов.\n\n"
            f"📋 *Доступные команды:*\n"
            f"/start - Запустить бота\n"
            f"/help - Помощь и справка\n"
            f"/id - Узнать свой ID\n"
            f"/site - Открыть веб-панель\n"
            f"/status - Статус бота\n\n"
            f"🌐 *Веб-сайт:* https://konspekt-bot.onrender.com\n"
            f"🆔 *Твой ID:* `{user.id}`\n\n"
            f"✨ Бот работает на *Render* с использованием *вебхуков*!"
        )
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        logger.info(f"Пользователь {user.id} отправил /start")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = (
            "📚 *Konspekt Helper Bot - Помощь*\n\n"
            "Я помогаю создавать и структурировать конспекты.\n\n"
            "🔧 *Основные команды:*\n"
            "• /start - Запустить бота\n"
            "• /help - Эта справка\n"
            "• /id - Показать ваш Telegram ID\n"
            "• /site - Открыть веб-панель управления\n"
            "• /status - Проверить статус бота\n\n"
            "🌐 *Веб-интерфейс:*\n"
            "Откройте https://konspekt-bot.onrender.com\n"
            "для просмотра статистики и управления ботом.\n\n"
            "💡 *Как использовать:*\n"
            "1. Отправьте мне текст\n"
            "2. Я проанализирую его\n"
            "3. Создам структурированный конспект"
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def id_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /id"""
        user = update.effective_user
        
        self._log_webhook({
            'timestamp': datetime.now().timestamp(),
            'type': 'command_id',
            'user_id': user.id,
            'command': '/id'
        })
        
        await update.message.reply_text(
            f"🆔 *Ваш Telegram ID:* `{user.id}`\n"
            f"👤 *Имя:* {user.first_name}\n"
            f"📛 *Username:* @{user.username or 'нет'}\n\n"
            f"Этот ID может быть полезен для идентификации в системе.",
            parse_mode='Markdown'
        )
    
    async def site_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /site"""
        await update.message.reply_text(
            "🌐 *Веб-панель управления ботом*\n\n"
            "Откройте в браузере:\n"
            "https://konspekt-bot.onrender.com\n\n"
            "На сайте вы можете:\n"
            "• Проверить статус бота\n"
            "• Просмотреть историю вебхуков\n"
            "• Управлять настройками\n"
            "• Мониторить активность",
            parse_mode='Markdown'
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        status_text = (
            "✅ *Статус бота: АКТИВЕН*\n\n"
            "🤖 *Имя:* @Konspekt_help_bot\n"
            "⚙️ *Режим:* Вебхуки\n"
            "🌐 *Хостинг:* Render\n"
            "🔄 *Последняя проверка:* Сейчас\n\n"
            "Все системы работают нормально!\n"
            "Бот готов к обработке сообщений."
        )
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        text = update.message.text
        
        # Логируем вебхук
        self._log_webhook({
            'timestamp': datetime.now().timestamp(),
            'type': 'message',
            'user_id': update.effective_user.id,
            'text_preview': text[:50] + ('...' if len(text) > 50 else ''),
            'update_id': update.update_id
        })
        
        # Простой эхо-ответ
        response = (
            f"📝 *Вы написали:*\n{text}\n\n"
            f"В будущем здесь будет анализ текста и создание конспекта!\n"
            f"🆔 Ваш ID для этого сообщения: `{update.update_id}`"
        )
        
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"Эхо-ответ для пользователя {update.effective_user.id}")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок бота"""
        logger.error(f"Ошибка в боте: {context.error}")
        
        # Логируем ошибку
        self._log_webhook({
            'timestamp': datetime.now().timestamp(),
            'type': 'error',
            'error': str(context.error),
            'update_id': update.update_id if update else None
        })
        
        # Можно отправить сообщение об ошибке пользователю
        if update and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Произошла ошибка при обработке вашего запроса. Попробуйте позже."
                )
            except:
                pass
    
    def _log_webhook(self, data: Dict[str, Any]):
        """Логирование вебхука в общую историю"""
        webhook_history.append(data)
        if len(webhook_history) > MAX_HISTORY:
            webhook_history.pop(0)
    
    async def process_webhook(self, update_data: Dict[str, Any]):
        """Обработка вебхука от Telegram"""
        try:
            # Создаем объект Update из данных
            update = Update.de_json(update_data, self.bot)
            
            # Обрабатываем обновление
            await self.application.initialize()
            await self.application.process_update(update)
            
            logger.info(f"✅ Вебхук обработан успешно: {update.update_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки вебхука: {e}")
            
            # Логируем ошибку
            self._log_webhook({
                'timestamp': datetime.now().timestamp(),
                'type': 'webhook_error',
                'error': str(e),
                'update_data': update_data
            })
            
            return False
    
    def get_bot_info(self):
        """Получение информации о боте"""
        if not self.bot:
            return None
        
        try:
            import asyncio
            
            # Получаем информацию о боте асинхронно
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def get_info():
                return await self.bot.get_me()
            
            bot_info = loop.run_until_complete(get_info())
            loop.close()
            
            return {
                'id': bot_info.id,
                'username': bot_info.username,
                'first_name': bot_info.first_name,
                'is_bot': bot_info.is_bot
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о боте: {e}")
            return None

# Геттер для истории вебхуков (используется web_server.py)
def get_webhook_history(limit: int = 10) -> List[Dict[str, Any]]:
    """Получение истории вебхуков"""
    return webhook_history[-limit:] if webhook_history else []

# Геттер для последнего вебхука
def get_last_webhook() -> Dict[str, Any]:
    """Получение последнего вебхука"""
    return webhook_history[-1] if webhook_history else {}
    import os
import json
import logging
import asyncio
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import requests

# Импортируем бота и его функции
from bot import init_bot, get_webhook_history, get_last_webhook, webhook_history

# ==================== НАСТРОЙКА ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    logger.error("❌ BOT_TOKEN не найден в переменных окружения!")
    logger.error("Добавьте в настройках Render переменную BOT_TOKEN")

# Глобальная ссылка на экземпляр бота
bot = None

# ==================== HTML ШАБЛОН САЙТА ====================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Konspekt Helper Bot - Панель управления</title>
    <style>
        /* Все стили из предыдущего кода остаются без изменений */
        /* Для краткости оставляю структуру, но удаляю содержимое */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: #333; line-height: 1.6; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); border-radius: 20px; padding: 25px 30px; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; border: 1px solid rgba(255,255,255,0.2); }
        .logo { display: flex; align-items: center; gap: 15px; }
        .logo i { font-size: 2.5rem; color: #667eea; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .logo h1 { font-size: 1.8rem; font-weight: 700; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .status { display: flex; align-items: center; gap: 10px; padding: 10px 20px; background: #f8f9fa; border-radius: 50px; font-weight: 500; }
        .status-dot { width: 12px; height: 12px; border-radius: 50%; background: #28a745; animation: pulse 2s infinite; }
        .status.error .status-dot { background: #dc3545; }
        .status.inactive .status-dot { background: #ffc107; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        .main-content { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 30px; }
        @media (max-width: 768px) { .main-content { grid-template-columns: 1fr; } }
        .card { background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); border-radius: 20px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); border: 1px solid rgba(255,255,255,0.2); }
        .card h2 { font-size: 1.4rem; margin-bottom: 20px; color: #2d3748; display: flex; align-items: center; gap: 10px; }
        .card h2 i { color: #667eea; }
        .bot-info { grid-column: 1 / -1; }
        .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-top: 20px; }
        .info-item { background: #f8f9fa; padding: 15px; border-radius: 12px; border-left: 4px solid #667eea; }
        .info-item label { font-size: 0.9rem; color: #718096; display: block; margin-bottom: 5px; }
        .info-item .value { font-size: 1.1rem; font-weight: 600; color: #2d3748; word-break: break-all; }
        .webhook-item { background: #f8f9fa; padding: 15px; border-radius: 12px; margin-bottom: 15px; border-left: 4px solid #48bb78; animation: slideIn 0.3s ease; }
        .webhook-item.error { border-left-color: #f56565; }
        .webhook-header { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 0.9rem; }
        .webhook-time { color: #718096; }
        .webhook-type { background: #667eea; color: white; padding: 3px 10px; border-radius: 20px; font-size: 0.8rem; }
        .webhook-data { background: white; padding: 10px; border-radius: 8px; font-family: monospace; font-size: 0.9rem; max-height: 150px; overflow-y: auto; }
        @keyframes slideIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .actions { display: flex; gap: 15px; flex-wrap: wrap; margin-top: 20px; }
        .btn { padding: 12px 24px; border-radius: 12px; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; gap: 8px; transition: all 0.3s ease; border: none; cursor: pointer; font-size: 1rem; }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(102,126,234,0.3); }
        .btn-secondary { background: #e2e8f0; color: #4a5568; }
        .btn-secondary:hover { background: #cbd5e0; transform: translateY(-2px); }
        .btn-danger { background: #fc8181; color: white; }
        .btn-danger:hover { background: #f56565; transform: translateY(-2px); }
        .footer { text-align: center; margin-top: 40px; padding: 20px; color: rgba(255,255,255,0.8); font-size: 0.9rem; }
        .empty-state { text-align: center; padding: 40px 20px; color: #a0aec0; }
        .empty-state i { font-size: 3rem; margin-bottom: 20px; opacity: 0.5; }
        .last-updated { font-size: 0.8rem; color: #a0aec0; margin-top: 10px; text-align: right; }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="logo">
                <i class="fas fa-robot"></i>
                <h1>Konspekt Helper Bot</h1>
            </div>
            <div class="status" id="statusIndicator">
                <span class="status-dot"></span>
                <span class="status-text">Загрузка...</span>
            </div>
        </header>

        <main class="main-content">
            <div class="card bot-info">
                <h2><i class="fas fa-info-circle"></i> Информация о боте</h2>
                <div class="info-grid">
                    <div class="info-item">
                        <label>Имя бота</label>
                        <div class="value" id="botName">@Konspekt_help_bot</div>
                    </div>
                    <div class="info-item">
                        <label>Статус</label>
                        <div class="value" id="botStatus">Проверка...</div>
                    </div>
                    <div class="info-item">
                        <label>Вебхук</label>
                        <div class="value" id="webhookStatus">Не настроен</div>
                    </div>
                    <div class="info-item">
                        <label>Последняя активность</label>
                        <div class="value" id="lastActivity">Никогда</div>
                    </div>
                </div>
                
                <div class="actions">
                    <a href="https://t.me/Konspekt_help_bot" class="btn btn-primary" target="_blank">
                        <i class="fab fa-telegram"></i> Открыть в Telegram
                    </a>
                    <button class="btn btn-secondary" onclick="setWebhook()">
                        <i class="fas fa-link"></i> Настроить вебхук
                    </button>
                    <button class="btn btn-secondary" onclick="deleteWebhook()">
                        <i class="fas fa-unlink"></i> Удалить вебхук
                    </button>
                    <button class="btn btn-secondary" onclick="refreshData()">
                        <i class="fas fa-sync-alt"></i> Обновить
                    </button>
                </div>
            </div>

            <div class="card">
                <h2><i class="fas fa-history"></i> История вебхуков</h2>
                <div id="webhookHistory">
                    <div class="empty-state">
                        <i class="fas fa-inbox"></i>
                        <p>Вебхуки еще не поступали</p>
                        <p>Напишите что-нибудь боту в Telegram</p>
                    </div>
                </div>
                <div class="last-updated">
                    <span id="lastUpdate">Обновлено: --:--:--</span>
                </div>
            </div>

            <div class="card">
                <h2><i class="fas fa-terminal"></i> Быстрые команды</h2>
                <div class="info-grid">
                    <div class="info-item">
                        <label>Проверить бота</label>
                        <div class="value">
                            <button class="btn btn-secondary" style="width: 100%; margin-top: 5px;" onclick="testBot()">
                                <i class="fas fa-vial"></i> Тест /start
                            </button>
                        </div>
                    </div>
                    <div class="info-item">
                        <label>Статус вебхука</label>
                        <div class="value">
                            <button class="btn btn-secondary" style="width: 100%; margin-top: 5px;" onclick="getWebhookInfo()">
                                <i class="fas fa-question-circle"></i> Проверить
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2><i class="fas fa-code"></i> Техническая информация</h2>
                <div class="info-item">
                    <label>Токен бота</label>
                    <div class="value" style="font-size: 0.8rem; word-break: break-all;" id="botToken">
                        {{ 'Настроен' if has_token else 'Не настроен' }}
                    </div>
                </div>
                <div class="info-item">
                    <label>URL вебхука</label>
                    <div class="value" style="font-size: 0.8rem; word-break: break-all;">
                        {{ webhook_url }}
                    </div>
                </div>
                <div class="info-item">
                    <label>Статус Render</label>
                    <div class="value" id="renderStatus">Активен</div>
                </div>
            </div>
        </main>

        <footer class="footer">
            <p>🤖 Konspekt Helper Bot • Работает на Render • Версия 1.0.0</p>
            <p>Панель управления обновляется автоматически каждые 5 секунд</p>
        </footer>
    </div>

    <script>
        let lastUpdateTime = null;
        
        async function fetchData() {
            try {
                const statusResponse = await fetch('/api/bot-status');
                const statusData = await statusResponse.json();
                
                const statusElement = document.getElementById('statusIndicator');
                const statusText = document.getElementById('botStatus');
                
                if (statusData.status === 'active') {
                    statusElement.className = 'status';
                    statusText.textContent = '✅ Активен';
                    document.getElementById('statusIndicator').querySelector('.status-text').textContent = 'Активен';
                    document.getElementById('botName').textContent = '@' + (statusData.bot_username || 'Konspekt_help_bot');
                } else {
                    statusElement.className = 'status error';
                    statusText.textContent = '❌ Ошибка';
                    document.getElementById('statusIndicator').querySelector('.status-text').textContent = 'Ошибка';
                }
                
                document.getElementById('webhookStatus').textContent = 
                    statusData.webhook_set ? '✅ Настроен' : '❌ Не настроен';
                
                const historyResponse = await fetch('/api/webhook-history');
                const historyData = await historyResponse.json();
                updateWebhookHistory(historyData);
                
                const now = new Date();
                document.getElementById('lastUpdate').textContent = 
                    `Обновлено: ${now.toLocaleTimeString()}`;
                    
                if (historyData.length > 0) {
                    const lastWebhook = historyData[historyData.length - 1];
                    const time = new Date(lastWebhook.timestamp * 1000);
                    document.getElementById('lastActivity').textContent = 
                        time.toLocaleTimeString();
                }
                
            } catch (error) {
                console.error('Ошибка при получении данных:', error);
                document.getElementById('statusIndicator').className = 'status error';
                document.getElementById('statusIndicator').querySelector('.status-text').textContent = 'Ошибка связи';
            }
        }
        
        function updateWebhookHistory(history) {
            const container = document.getElementById('webhookHistory');
            
            if (history.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-inbox"></i>
                        <p>Вебхуки еще не поступали</p>
                        <p>Напишите что-нибудь боту в Telegram</p>
                    </div>
                `;
                return;
            }
            
            let html = '';
            history.slice(-5).reverse().forEach(item => {
                const time = new Date(item.timestamp * 1000);
                const dataStr = JSON.stringify(item, null, 2);
                
                html += `
                    <div class="webhook-item ${item.error ? 'error' : ''}">
                        <div class="webhook-header">
                            <span class="webhook-time">${time.toLocaleTimeString()}</span>
                            <span class="webhook-type">${item.type || 'webhook'}</span>
                        </div>
                        <pre class="webhook-data">${dataStr}</pre>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }
        
        async function setWebhook() {
            try {
                const response = await fetch('/api/set-webhook', { method: 'POST' });
                const data = await response.json();
                
                if (data.status === 'success') {
                    alert('✅ Вебхук успешно настроен!');
                    refreshData();
                } else {
                    alert('❌ Ошибка: ' + (data.message || 'Неизвестная ошибка'));
                }
            } catch (error) {
                alert('❌ Ошибка сети: ' + error.message);
            }
        }
        
        async function deleteWebhook() {
            if (!confirm('Вы уверены, что хотите удалить вебхук?')) return;
            
            try {
                const response = await fetch('/api/delete-webhook', { method: 'POST' });
                const data = await response.json();
                
                if (data.status === 'success') {
                    alert('✅ Вебхук удален!');
                    refreshData();
                } else {
                    alert('❌ Ошибка: ' + (data.message || 'Неизвестная ошибка'));
                }
            } catch (error) {
                alert('❌ Ошибка сети: ' + error.message);
            }
        }
        
        async function testBot() {
            alert('📱 Откройте Telegram и напишите боту /start');
        }
        
        async function getWebhookInfo() {
            try {
                const response = await fetch('/api/webhook-info');
                const data = await response.json();
                
                if (data.status === 'success') {
                    alert(`ℹ️ Информация о вебхуке:\n\nURL: ${data.webhook_info.url || 'Не установлен'}\nОшибок: ${data.webhook_info.pending_update_count || 0}\nПоследняя ошибка: ${data.webhook_info.last_error_message || 'Нет'}`);
                } else {
                    alert('❌ Ошибка: ' + (data.message || 'Неизвестная ошибка'));
                }
            } catch (error) {
                alert('❌ Ошибка сети: ' + error.message);
            }
        }
        
        function refreshData() {
            fetchData();
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            fetchData();
            setInterval(fetchData, 5000);
        });
    </script>
</body>
</html>
"""

# ==================== HTTP ОБРАБОТЧИК ====================
class BotHTTPHandler(BaseHTTPRequestHandler):
    """HTTP обработчик для вебхуков и сайта"""
    
    def do_GET(self):
        """Обработка GET запросов (веб-сайт)"""
        try:
            if self.path == '/':
                # Главная страница
                webhook_url = f"https://{self.headers.get('Host', 'konspekt-bot.onrender.com')}/webhook"
                
                html = HTML_TEMPLATE.replace(
                    '{{ webhook_url }}', webhook_url
                ).replace(
                    '{{ has_token }}', 'true' if TOKEN else 'false'
                )
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
                
            elif self.path == '/api/bot-status':
                # API: статус бота
                status = {
                    'status': 'active' if TOKEN and bot else 'error',
                    'timestamp': datetime.now().timestamp(),
                    'webhook_set': False
                }
                
                if TOKEN and bot:
                    try:
                        # Получаем информацию о боте
                        bot_info = bot.get_bot_info()
                        if bot_info:
                            status.update({
                                'bot_username': bot_info['username'],
                                'bot_name': bot_info['first_name'],
                                'bot_id': bot_info['id']
                            })
                        
                        # Проверяем, настроен ли вебхук
                        try:
                            response = requests.get(f'https://api.telegram.org/bot{TOKEN}/getWebhookInfo')
                            if response.json().get('result', {}).get('url'):
                                status['webhook_set'] = True
                        except:
                            pass
                            
                    except Exception as e:
                        logger.error(f"Ошибка получения информации о боте: {e}")
                        status['status'] = 'error'
                        status['error'] = str(e)
                
                self.send_json_response(status)
                
            elif self.path == '/api/webhook-history':
                # API: история вебхуков
                history = get_webhook_history(10)
                self.send_json_response(history)
                
            elif self.path == '/api/webhook-info':
                # API: информация о вебхуке
                if not TOKEN:
                    self.send_json_response({'status': 'error', 'message': 'Токен не настроен'})
                    return
                
                try:
                    response = requests.get(f'https://api.telegram.org/bot{TOKEN}/getWebhookInfo')
                    self.send_json_response({
                        'status': 'success',
                        'webhook_info': response.json().get('result', {})
                    })
                except Exception as e:
                    self.send_json_response({
                        'status': 'error',
                        'message': str(e)
                    })
                    
            elif self.path.startswith('/static/'):
                self.send_error(404, "File not found")
                
            else:
                self.send_error(404, "Path not found")
                
        except Exception as e:
            logger.error(f"Ошибка в обработке GET запроса: {e}")
            self.send_error(500, f"Internal server error: {e}")
    
    def do_POST(self):
        """Обработка POST запросов (вебхуки от Telegram)"""
        try:
            if self.path == '/webhook':
                # ВЕБХУК от Telegram
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                # Парсим JSON от Telegram
                update_data = json.loads(post_data.decode('utf-8'))
                
                # Логируем получение вебхука
                webhook_entry = {
                    'timestamp': datetime.now().timestamp(),
                    'data': update_data,
                    'type': 'telegram_webhook',
                    'update_id': update_data.get('update_id'),
                    'headers': dict(self.headers),
                    'received_at': datetime.now().isoformat()
                }
                
                # Добавляем в историю (используем импортированную переменную)
                webhook_history.append(webhook_entry)
                if len(webhook_history) > 100:  # MAX_HISTORY из bot.py
                    webhook_history.pop(0)
                
                logger.info(f"📨 Получен вебхук. Update ID: {update_data.get('update_id')}")
                
                # Обрабатываем вебхук через бота
                if bot:
                    try:
                        # Обрабатываем асинхронно
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        success = loop.run_until_complete(
                            bot.process_webhook(update_data)
                        )
                        loop.close()
                        
                        if success:
                            webhook_entry['processed'] = True
                            webhook_entry['processed_at'] = datetime.now().isoformat()
                            logger.info(f"✅ Вебхук {update_data.get('update_id')} обработан успешно")
                        else:
                            webhook_entry['processed'] = False
                            webhook_entry['error'] = 'Processing failed'
                            logger.error(f"❌ Вебхук {update_data.get('update_id')} не обработан")
                            
                    except Exception as e:
                        logger.error(f"❌ Ошибка обработки вебхука: {e}")
                        webhook_entry['processed'] = False
                        webhook_entry['error'] = str(e)
                else:
                    logger.error("❌ Бот не инициализирован для обработки вебхука")
                    webhook_entry['processed'] = False
                    webhook_entry['error'] = 'Bot not initialized'
                
                # Отправляем успешный ответ Telegram
                self.send_json_response({'status': 'ok'})
                
            elif self.path == '/api/set-webhook':
                # API: настройка вебхука
                if not TOKEN:
                    self.send_json_response({'status': 'error', 'message': 'Токен не настроен'})
                    return
                
                try:
                    webhook_url = f"https://{self.headers.get('Host', 'konspekt-bot.onrender.com')}/webhook"
                    set_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
                    
                    response = requests.post(set_url)
                    result = response.json()
                    
                    if result.get('ok'):
                        logger.info(f"✅ Вебхук настроен: {webhook_url}")
                        self.send_json_response({
                            'status': 'success',
                            'webhook_url': webhook_url,
                            'telegram_response': result
                        })
                    else:
                        logger.error(f"❌ Ошибка настройки вебхука: {result}")
                        self.send_json_response({
                            'status': 'error',
                            'message': result.get('description', 'Unknown error'),
                            'telegram_response': result
                        })
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка при настройке вебхука: {e}")
                    self.send_json_response({
                        'status': 'error',
                        'message': str(e)
                    })
                    
            elif self.path == '/api/delete-webhook':
                # API: удаление вебхука
                if not TOKEN:
                    self.send_json_response({'status': 'error', 'message': 'Токен не настроен'})
                    return
                
                try:
                    delete_url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
                    
                    response = requests.post(delete_url)
                    result = response.json()
                    
                    if result.get('ok'):
                        logger.info("✅ Вебхук удален")
                        self.send_json_response({
                            'status': 'success',
                            'telegram_response': result
                        })
                    else:
                        logger.error(f"❌ Ошибка удаления вебхука: {result}")
                        self.send_json_response({
                            'status': 'error',
                            'message': result.get('description', 'Unknown error')
                        })
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка при удалении вебхука: {e}")
                    self.send_json_response({
                        'status': 'error',
                        'message': str(e)
                    })
                    
            else:
                self.send_error(404, "Path not found")
                
        except Exception as e:
            logger.error(f"Ошибка в обработке POST запроса: {e}")
            self.send_error(500, f"Internal server error: {e}")
    
    def send_json_response(self, data):
        """Отправка JSON ответа"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Отключаем стандартное логирование запросов"""
        # logger.debug(f"HTTP: {format % args}")
        pass

# ==================== ЗАПУСК СЕРВЕРА ====================
def setup_webhook():
    """Настройка вебхука при запуске"""
    if not TOKEN:
        logger.error("❌ Не могу настроить вебхук: токен не найден")
        return
    
    try:
        webhook_url = f"https://konspekt-bot.onrender.com/webhook"
        set_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
        
        response = requests.post(set_url)
        if response.json().get('ok'):
            logger.info(f"✅ Вебхук настроен при запуске: {webhook_url}")
            return True
        else:
            logger.warning(f"⚠️ Не удалось настроить вебхук: {response.json()}")
            return False
            
    except Exception as e:
        logger.warning(f"⚠️ Не удалось настроить вебхук при запуске: {e}")
        return False

def run_server():
    """Запуск HTTP сервера"""
    global bot
    
    # Инициализируем бота
    if TOKEN:
        try:
            bot = init_bot(TOKEN)
            logger.info("✅ Бот инициализирован успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации бота: {e}")
            bot = None
    else:
        logger.error("❌ Токен бота не найден, бот не будет работать")
        bot = None
    
    # Настраиваем вебхук
    if bot:
        setup_webhook()
    
    # Запускаем HTTP сервер
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), BotHTTPHandler)
    
    logger.info(f"🚀 Сервер запущен на порту {port}")
    logger.info(f"🌐 Веб-сайт: http://0.0.0.0:{port}")
    logger.info(f"🤖 Вебхук: https://konspekt-bot.onrender.com/webhook")
    logger.info(f"📊 История вебхуков: http://0.0.0.0:{port}/api/webhook-history")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("⏹️ Сервер остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка сервера: {e}")

# ==================== ТОЧКА ВХОДА ====================
if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🌐 ЗАПУСК WEB СЕРВЕРА ДЛЯ TELEGRAM БОТА")
    logger.info("=" * 60)
    
    if TOKEN:
        logger.info(f"✅ Токен бота: ...{TOKEN[-8:]}")
    else:
        logger.error("❌ ТОКЕН БОТА НЕ НАЙДЕН!")
        logger.error("Добавьте переменную BOT_TOKEN в настройках Render")
    
    # Запускаем сервер
    run_server()
