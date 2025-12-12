#!/usr/bin/env python3
"""
Konspekt Helper Bot - Telegram бот для создания конспектов
Бот: @Konspekt_help_bot
Разработан для развертывания на Render.com
"""

import logging
import json
import os
import html
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# HTML шаблон для веб-сайта
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@Konspekt_help_bot - Панель управления</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        header {
            background: linear-gradient(to right, #4A00E0, #8E2DE2);
            color: white;
            padding: 30px;
            text-align: center;
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
        }
        .content {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            padding: 30px;
        }
        .card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        .card h2 {
            color: #4A00E0;
            margin-bottom: 15px;
            border-bottom: 2px solid #4A00E0;
            padding-bottom: 10px;
        }
        .stat-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 15px;
        }
        .stat-item {
            background: white;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #4A00E0;
        }
        .stat-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #4A00E0;
        }
        .stat-label {
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }
        .btn {
            display: inline-block;
            background: linear-gradient(to right, #4A00E0, #8E2DE2);
            color: white;
            padding: 12px 25px;
            border-radius: 50px;
            text-decoration: none;
            font-weight: bold;
            margin: 10px 5px;
            transition: all 0.3s ease;
            border: none;
            cursor: pointer;
        }
        .btn:hover {
            transform: scale(1.05);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        .btn-success {
            background: linear-gradient(to right, #00b09b, #96c93d);
        }
        .btn-danger {
            background: linear-gradient(to right, #ff416c, #ff4b2b);
        }
        .webhook-log {
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
            max-height: 300px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.9em;
        }
        .log-entry {
            padding: 8px;
            margin: 5px 0;
            border-left: 3px solid #4A00E0;
            background: #f8f9fa;
        }
        .log-time {
            color: #666;
            font-size: 0.8em;
        }
        .command-list {
            list-style: none;
        }
        .command-list li {
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        .command {
            font-weight: bold;
            color: #4A00E0;
        }
        footer {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #666;
            border-top: 1px solid #eee;
        }
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            margin-left: 10px;
        }
        .status-active {
            background: #d4edda;
            color: #155724;
        }
        .status-inactive {
            background: #f8d7da;
            color: #721c24;
        }
        @media (max-width: 768px) {
            .content {
                grid-template-columns: 1fr;
                padding: 20px;
            }
            h1 {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📚 @Konspekt_help_bot</h1>
            <p class="subtitle">Telegram-бот для создания конспектов | Панель управления</p>
            <p>Статус: <span class="status-badge status-active">● Активен</span></p>
        </header>
        
        <div class="content">
            <div class="card">
                <h2>📊 Статистика бота</h2>
                <div class="stat-grid">
                    <div class="stat-item">
                        <div class="stat-value" id="totalUsers">0</div>
                        <div class="stat-label">Пользователей</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="totalMessages">0</div>
                        <div class="stat-label">Сообщений</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="activeToday">0</div>
                        <div class="stat-label">Активных сегодня</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="conspectsCreated">0</div>
                        <div class="stat-label">Конспектов создано</div>
                    </div>
                </div>
                <div style="margin-top: 20px;">
                    <a href="/stats.json" class="btn" target="_blank">Полная статистика (JSON)</a>
                    <button onclick="refreshStats()" class="btn btn-success">Обновить</button>
                </div>
            </div>
            
            <div class="card">
                <h2>🤖 Управление ботом</h2>
                <p>Используйте эти команды в Telegram:</p>
                <ul class="command-list">
                    <li><span class="command">/start</span> - Начать работу с ботом</li>
                    <li><span class="command">/help</span> - Помощь и инструкции</li>
                    <li><span class="command">/id</span> - Узнать свой Telegram ID</li>
                    <li><span class="command">/site</span> - Ссылка на эту панель</li>
                    <li><span class="command">/conspect [текст]</span> - Создать конспект</li>
                    <li><span class="command">Любой текст</span> - Автоматически создаст конспект</li>
                </ul>
                <div style="margin-top: 20px;">
                    <a href="https://t.me/Konspekt_help_bot" class="btn" target="_blank">Открыть бота в Telegram</a>
                    <a href="/setup-webhook" class="btn btn-success">Настроить вебхук</a>
                </div>
            </div>
            
            <div class="card">
                <h2>🔗 Вебхук (Webhook)</h2>
                <p><strong>URL вебхука:</strong> <code>{webhook_url}</code></p>
                <p><strong>Статус:</strong> <span id="webhookStatus">Проверка...</span></p>
                
                <h3 style="margin-top: 20px;">📨 Последние вебхуки</h3>
                <div class="webhook-log" id="webhookLog">
                    <!-- Заполняется JavaScript -->
                </div>
            </div>
            
            <div class="card">
                <h2>⚙️ Системная информация</h2>
                <p><strong>Сервер:</strong> Render.com</p>
                <p><strong>Python:</strong> 3.11.8</p>
                <p><strong>Библиотека бота:</strong> python-telegram-bot 13.15</p>
                <p><strong>Режим:</strong> Вебхуки (Webhook)</p>
                <p><strong>Время запуска:</strong> {start_time}</p>
                
                <div style="margin-top: 20px;">
                    <a href="/health" class="btn" target="_blank">Проверить здоровье</a>
                    <button onclick="location.reload()" class="btn">Обновить страницу</button>
                </div>
            </div>
        </div>
        
        <footer>
            <p>© 2024 @Konspekt_help_bot | Развернуто на Render.com | <a href="https://render.com" style="color: #4A00E0;">Render.com</a></p>
            <p style="margin-top: 10px; font-size: 0.9em;">Бот автоматически засыпает после 15 минут бездействия (бесплатный тариф Render)</p>
        </footer>
    </div>
    
    <script>
        // Функция для загрузки статистики
        async function loadStats() {
            try {
                const response = await fetch('/stats.json');
                const data = await response.json();
                
                document.getElementById('totalUsers').textContent = data.stats.total_users;
                document.getElementById('totalMessages').textContent = data.stats.total_messages;
                document.getElementById('activeToday').textContent = data.stats.active_today;
                document.getElementById('conspectsCreated').textContent = data.stats.conspects_created;
                
                document.getElementById('webhookStatus').textContent = 
                    data.webhook_status ? '✅ Активен' : '❌ Не настроен';
                    
                // Обновляем логи вебхуков
                const logContainer = document.getElementById('webhookLog');
                logContainer.innerHTML = '';
                data.recent_webhooks.slice(0, 10).forEach(log => {
                    const logEntry = document.createElement('div');
                    logEntry.className = 'log-entry';
                    logEntry.innerHTML = `
                        <div class="log-time">${new Date(log.timestamp).toLocaleString()}</div>
                        <div>${log.message}</div>
                    `;
                    logContainer.appendChild(logEntry);
                });
            } catch (error) {
                console.error('Ошибка загрузки статистики:', error);
            }
        }
        
        function refreshStats() {
            loadStats();
            // Визуальная обратная связь
            const btn = event.target;
            btn.textContent = 'Обновление...';
            setTimeout(() => {
                btn.textContent = 'Обновить';
            }, 1000);
        }
        
        // Загружаем статистику при загрузке страницы
        document.addEventListener('DOMContentLoaded', loadStats);
        
        // Автообновление каждые 30 секунд
        setInterval(loadStats, 30000);
    </script>
</body>
</html>
"""

# Глобальные переменные для статистики
stats = {
    "total_users": 0,
    "total_messages": 0,
    "active_today": 0,
    "conspects_created": 0,
    "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "user_activity": {},
    "recent_webhooks": []
}

# Максимальное количество хранимых вебхуков
MAX_WEBHOOKS_LOG = 50

class SimpleBot:
    """Основной класс Telegram-бота"""
    
    def __init__(self, token):
        self.token = token
        self.bot_url = f"https://api.telegram.org/bot{token}"
        logger.info(f"Бот @Konspekt_help_bot инициализирован")
        
    def start(self, update_id, chat_id):
        """Обработка команды /start"""
        welcome_text = (
            "👋 Привет! Я @Konspekt_help_bot!\n\n"
            "Я помогу тебе создавать конспекты из любого текста.\n\n"
            "📝 *Как использовать:*\n"
            "1. Отправь мне любой текст\n"
            "2. Используй команду /conspect [текст]\n"
            "3. Я создам структурированный конспект\n\n"
            "🔧 *Доступные команды:*\n"
            "/help - справка и примеры\n"
            "/id - узнать свой Telegram ID\n"
            "/site - веб-панель управления ботом\n\n"
            "✨ *Пример:*\n"
            "Отправь мне: \n"
            "`Машинное обучение - это область искусственного интеллекта, которая позволяет компьютерам обучаться на данных без явного программирования.`\n\n"
            "Просто отправь мне текст и я начну работу!"
        )
        
        # Обновление статистики
        self._update_stats(chat_id)
        
        return self._send_message(chat_id, welcome_text)
    
    def help_command(self, update_id, chat_id):
        """Обработка команды /help"""
        help_text = (
            "📚 *@Konspekt_help_bot - Помощь*\n\n"
            "Я создаю структурированные конспекты из любого текста.\n\n"
            "✨ *Примеры использования:*\n\n"
            "1. *Прямой текст:*\n"
            "   Просто отправь мне текст\n"
            "   `ИИ меняет мир. Машинное обучение позволяет...`\n\n"
            "2. *Команда /conspect:*\n"
            "   `/conspect Квантовые компьютеры используют кубиты...`\n\n"
            "3. *Длинные тексты:*\n"
            "   Я обрабатываю сообщения до 4000 символов\n\n"
            "📋 *Формат конспекта:*\n"
            "• 🎯 Основная идея\n"
            "• 📌 Ключевые тезисы\n"
            "• 🔑 Термины и определения\n"
            "• 💎 Выводы\n\n"
            "🔧 *Другие команды:*\n"
            "• /id - ваш Telegram ID\n"
            "• /site - веб-панель управления\n"
            "• /start - начальное сообщение\n\n"
            "Попробуй отправить мне текст прямо сейчас! ✨"
        )
        
        self._update_stats(chat_id)
        return self._send_message(chat_id, help_text)
    
    def get_user_id(self, update_id, chat_id):
        """Обработка команды /id"""
        response = f"🆔 Ваш Telegram ID: `{chat_id}`\n\nЭтот идентификатор используется для:\n• Статистики использования\n• Отладки работы бота\n• Персонализированных функций"
        
        self._update_stats(chat_id)
        return self._send_message(chat_id, response)
    
    def site_command(self, update_id, chat_id):
        """Обработка команды /site"""
        web_url = os.getenv("RENDER_EXTERNAL_URL", "https://konspekt-helper-bot.onrender.com")
        response = f"🌐 *Веб-панель управления ботом*\n\n{web_url}\n\nНа сайте вы найдете:\n• 📊 Статистику использования\n• 🔗 Информацию о вебхуке\n• ⚙️ Системную информацию\n• 📨 Логи последних запросов"
        
        self._update_stats(chat_id)
        return self._send_message(chat_id, response)
    
    def create_conspect(self, update_id, chat_id, text):
        """Создание конспекта из текста"""
        if not text.strip():
            return self._send_message(chat_id, "📝 Пожалуйста, укажите текст для создания конспекта.\n\nПример: /conspect Машинное обучение - это...")
        
        # Обновление статистики
        stats["conspects_created"] += 1
        self._update_stats(chat_id)
        
        # Создаем конспект
        conspect = self._generate_conspect(text)
        
        response = f"📝 *Ваш конспект готов!*\n\n{conspect}\n\n✨ Создано с помощью @Konspekt_help_bot"
        return self._send_message(chat_id, response)
    
    def handle_message(self, update_id, chat_id, text):
        """Обработка обычных текстовых сообщений"""
        if text.startswith('/'):
            return None  # Команды обрабатываются отдельно
        
        # Создаем конспект из обычного сообщения
        return self.create_conspect(update_id, chat_id, text)
    
    def _generate_conspect(self, text):
        """Генерация структурированного конспекта"""
        # Упрощенная логика для примера
        # В реальном приложении можно использовать NLP или шаблоны
        
        # Ограничиваем длину текста для конспекта
        if len(text) > 1000:
            text_preview = text[:300] + "..."
        else:
            text_preview = text
        
        # Разбиваем текст на предложения для ключевых тезисов
        sentences = text_preview.split('. ')
        key_points = sentences[:3]  # Берем первые 3 предложения
        
        conspect = (
            "📋 *Структурированный конспект*\n\n"
            "🎯 *Основная идея:*\n"
            f"Текст посвящен важной теме, содержащей ключевую информацию.\n\n"
            "📌 *Ключевые тезисы:*\n"
        )
        
        for i, point in enumerate(key_points, 1):
            if point.strip():
                conspect += f"{i}. {point.strip()}\n"
        
        conspect += (
            "\n🔑 *Термины и определения:*\n"
            "• *Конспект* - краткое изложение основных мыслей текста\n"
            "• *Структура* - организация информации для лучшего понимания\n"
            "• *Анализ* - разбор материала на составляющие элементы\n\n"
            "💎 *Выводы:*\n"
            "Представленный материал содержит ценные сведения, которые "
            "структурированы для эффективного запоминания и использования. "
            "Конспект помогает выделить самое важное из текста."
        )
        
        return conspect
    
    def _update_stats(self, chat_id):
        """Обновление статистики"""
        user_key = str(chat_id)
        today = datetime.now().strftime("%Y-%m-%d")
        
        if user_key not in stats["user_activity"]:
            stats["total_users"] += 1
            stats["user_activity"][user_key] = {
                "first_seen": datetime.now(), 
                "last_seen": datetime.now(), 
                "message_count": 0
            }
        
        stats["user_activity"][user_key]["last_seen"] = datetime.now()
        stats["user_activity"][user_key]["message_count"] += 1
        
        if stats["user_activity"][user_key].get("last_active_date") != today:
            stats["active_today"] += 1
            stats["user_activity"][user_key]["last_active_date"] = today
        
        stats["total_messages"] += 1
    
    def _send_message(self, chat_id, text):
        """Отправка сообщения через Telegram Bot API"""
        import requests
        
        url = f"{self.bot_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Сообщение отправлено в чат {chat_id}")
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return None
    
    def run_webhook(self):
        """Запуск бота в режиме вебхука"""
        logger.info("Бот @Konspekt_help_bot готов к работе через вебхуки")

class BotServer(BaseHTTPRequestHandler):
    """HTTP сервер для обработки вебхуков и веб-сайта"""
    
    def _set_headers(self, content_type='text/html'):
        """Установка заголовков ответа"""
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
    
    def do_GET(self):
        """Обработка GET запросов"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        logger.info(f"GET запрос: {path}")
        
        if path == '/':
            self._serve_main_page()
        elif path == '/health':
            self._serve_health_check()
        elif path == '/stats.json':
            self._serve_stats_json()
        elif path == '/setup-webhook':
            self._setup_webhook_page()
        else:
            self.send_error(404, "Страница не найдена")
    
    def do_POST(self):
        """Обработка POST запросов (вебхуки от Telegram)"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            update = json.loads(post_data.decode('utf-8'))
            update_id = update.get('update_id', 0)
            logger.info(f"Получен вебхук #{update_id} для @Konspekt_help_bot")
            
            # Логируем вебхук
            self._log_webhook(update)
            
            # Обрабатываем обновление
            self._process_update(update)
            
            # Отправляем успешный ответ
            self._set_headers('application/json')
            self.wfile.write(json.dumps({"status": "ok", "bot": "@Konspekt_help_bot"}).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Ошибка обработки вебхука: {e}")
            self.send_response(500)
            self.end_headers()
    
    def _serve_main_page(self):
        """Главная страница веб-сайта"""
        webhook_url = os.getenv("RENDER_EXTERNAL_URL", "https://konspekt-helper-bot.onrender.com") + "/webhook"
        start_time = stats["start_time"]
        
        html_content = HTML_TEMPLATE.format(
            webhook_url=webhook_url,
            start_time=start_time
        )
        
        self._set_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def _serve_health_check(self):
        """Health check эндпоинт"""
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "bot": "@Konspekt_help_bot",
            "version": "1.0.0",
            "stats": {
                "uptime": str(datetime.now() - datetime.strptime(stats["start_time"], "%Y-%m-%d %H:%M:%S")),
                "total_messages": stats["total_messages"],
                "active_users": len(stats["user_activity"]),
                "conspects_created": stats["conspects_created"]
            }
        }
        
        self._set_headers('application/json')
        self.wfile.write(json.dumps(health_data, ensure_ascii=False, indent=2).encode('utf-8'))
    
    def _serve_stats_json(self):
        """JSON API для статистики"""
        # Рассчитываем активных сегодня
        today = datetime.now().strftime("%Y-%m-%d")
        active_today = sum(
            1 for user_data in stats["user_activity"].values()
            if user_data.get("last_active_date") == today
        )
        
        stats["active_today"] = active_today
        
        stats_data = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "bot": "@Konspekt_help_bot",
            "stats": {
                "total_users": stats["total_users"],
                "total_messages": stats["total_messages"],
                "active_today": stats["active_today"],
                "conspects_created": stats["conspects_created"],
                "uptime": stats["start_time"]
            },
            "webhook_status": True,
            "recent_webhooks": stats["recent_webhooks"][-10:],
            "server_info": {
                "python_version": "3.11.8",
                "bot_library": "python-telegram-bot 13.15",
                "hosting": "Render.com",
                "bot_username": "Konspekt_help_bot"
            }
        }
        
        self._set_headers('application/json')
        self.wfile.write(json.dumps(stats_data, ensure_ascii=False, indent=2).encode('utf-8'))
    
    def _setup_webhook_page(self):
        """Страница настройки вебхука"""
        token = os.getenv("TELEGRAM_TOKEN", "")
        webhook_url = os.getenv("RENDER_EXTERNAL_URL", "https://konspekt-helper-bot.onrender.com") + "/webhook"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Настройка вебхука для @Konspekt_help_bot</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 5px 20px rgba(0,0,0,0.1); }}
                h1 {{ color: #4A00E0; border-bottom: 2px solid #4A00E0; padding-bottom: 10px; }}
                .code {{ background: #f8f9fa; padding: 15px; border-radius: 5px; font-family: monospace; margin: 15px 0; border-left: 4px solid #4A00E0; }}
                .btn {{ background: #4A00E0; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 5px; font-weight: bold; }}
                .step {{ margin: 25px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; }}
                .step-number {{ display: inline-block; background: #4A00E0; color: white; width: 30px; height: 30px; border-radius: 50%; text-align: center; line-height: 30px; margin-right: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⚙️ Настройка вебхука для @Konspekt_help_bot</h1>
                
                <div class="step">
                    <div class="step-number">1</div>
                    <strong>Текущий URL вебхука:</strong>
                    <div class="code">{webhook_url}</div>
                </div>
                
                <div class="step">
                    <div class="step-number">2</div>
                    <strong>Настроить вебхук (выполнить в терминале):</strong>
                    <div class="code">
                    curl "https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}"
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-number">3</div>
                    <strong>Проверить статус вебхука:</strong>
                    <div class="code">
                    curl "https://api.telegram.org/bot{token}/getWebhookInfo"
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-number">4</div>
                    <strong>Удалить вебхук (если нужно):</strong>
                    <div class="code">
                    curl "https://api.telegram.org/bot{token}/deleteWebhook"
                    </div>
                </div>
                
                <div style="margin-top: 30px; text-align: center;">
                    <a href="/" class="btn">← Вернуться на главную</a>
                    <a href="https://t.me/Konspekt_help_bot" class="btn" target="_blank">Открыть бота</a>
                </div>
            </div>
        </body>
        </html>
        """
        
        self._set_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def _log_webhook(self, update):
        """Логирование вебхука"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "update_id": update.get("update_id", 0),
            "message": self._extract_message_info(update)
        }
        
        stats["recent_webhooks"].append(log_entry)
        
        # Ограничиваем размер лога
        if len(stats["recent_webhooks"]) > MAX_WEBHOOKS_LOG:
            stats["recent_webhooks"] = stats["recent_webhooks"][-MAX_WEBHOOKS_LOG:]
    
    def _extract_message_info(self, update):
        """Извлечение информации из сообщения"""
        if "message" in update:
            msg = update["message"]
            chat = msg.get("chat", {})
            text = msg.get("text", "Без текста")
            
            # Обрезаем длинный текст
            if len(text) > 50:
                text = text[:50] + "..."
            
            return f"Сообщение от пользователя {chat.get('id')}: {text}"
        elif "edited_message" in update:
            return "Измененное сообщение"
        elif "callback_query" in update:
            return "Callback запрос"
        else:
            return f"Тип обновления: {list(update.keys())}"
    
    def _process_update(self, update):
        """Обработка обновления от Telegram"""
        token = os.getenv("TELEGRAM_TOKEN")
        if not token:
            logger.error("TELEGRAM_TOKEN не установлен для @Konspekt_help_bot")
            return
        
        bot = SimpleBot(token)
        
        # Извлекаем информацию из обновления
        update_id = update.get("update_id", 0)
        
        if "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            
            # Обработка команд
            if text.startswith('/'):
                if text.startswith('/start'):
                    bot.start(update_id, chat_id)
                elif text.startswith('/help'):
                    bot.help_command(update_id, chat_id)
                elif text.startswith('/id'):
                    bot.get_user_id(update_id, chat_id)
                elif text.startswith('/site'):
                    bot.site_command(update_id, chat_id)
                elif text.startswith('/conspect'):
                    # Убираем команду из текста
                    conspect_text = text[9:].strip()
                    bot.create_conspect(update_id, chat_id, conspect_text)
                else:
                    bot._send_message(chat_id, f"Неизвестная команда: {text}\n\nИспользуйте /help для списка команд")
            elif text:
                # Обработка обычного сообщения
                bot.handle_message(update_id, chat_id, text)
            else:
                bot._send_message(chat_id, "📝 Пожалуйста, отправьте текстовое сообщение для создания конспекта.")
    
    def log_message(self, format, *args):
        """Переопределение логирования для уменьшения шума"""
        pass

def start_bot():
    """Запуск Telegram бота"""
    token = os.getenv("TELEGRAM_TOKEN")
    
    if not token:
        logger.error("Переменная окружения TELEGRAM_TOKEN не установлена!")
        logger.info("Пожалуйста, установите TELEGRAM_TOKEN на Render.com")
        logger.info("Затем настройте вебхук командой:")
        logger.info('curl "https://api.telegram.org/bot<ВАШ_ТОКЕН>/setWebhook?url=https://ваш-сервис.onrender.com/webhook"')
        return
    
    bot = SimpleBot(token)
    bot.run_webhook()
    logger.info("Бот @Konspekt_help_bot инициализирован и готов к работе через вебхуки")

def start_http_server():
    """Запуск HTTP сервера"""
    port = int(os.getenv("PORT", 10000))
    server_address = ('', port)
    
    httpd = HTTPServer(server_address, BotServer)
    logger.info(f"HTTP сервер запущен на порту {port}")
    logger.info(f"Веб-сайт: http://localhost:{port}")
    logger.info(f"Health check: http://localhost:{port}/health")
    logger.info(f"Статистика: http://localhost:{port}/stats.json")
    logger.info(f"Вебхук: http://localhost:{port}/webhook")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Сервер остановлен")
    except
