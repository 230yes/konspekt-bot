#!/usr/bin/env python3
"""
Telegram бот Konspekt Helper Bot + веб-сайт управления
Разработано для развертывания на Render.com
"""

import os
import logging
import json
import html
from datetime import datetime
from typing import Dict, List, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time
import hashlib

# ==================== КОНФИГУРАЦИЯ ЛОГГИРОВАНИЯ ====================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== ИМПОРТЫ ДЛЯ TELEGRAM ====================

try:
    from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        filters,
        CallbackContext
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("Предупреждение: python-telegram-bot не установлен")

# ==================== КОНСТАНТЫ И ПЕРЕМЕННЫЕ ====================

# Получение переменных окружения Render
TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
PORT = int(os.environ.get('PORT', 10000))
WEBHOOK_URL = os.environ.get('RENDER_EXTERNAL_URL', '')
BOT_USERNAME = os.environ.get('BOT_USERNAME', 'KonspektHelperBot')

# Проверка обязательных переменных
if not TOKEN or TOKEN == 'ВАШ_ТОКЕН_БОТА':
    logger.error("TELEGRAM_TOKEN не установлен!")
    TOKEN = 'DEMO_TOKEN_FOR_TESTING'

if not WEBHOOK_URL:
    WEBHOOK_URL = f"http://localhost:{PORT}"

# Глобальные переменные для хранения данных
webhook_history: List[Dict] = []
user_stats = {
    "total_users": 0,
    "active_today": 0,
    "conspects_created": 0,
    "messages_processed": 0
}

# ==================== HTML ШАБЛОН (ДОЛЖЕН БЫТЬ В НАЧАЛЕ!) ====================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Konspekt Helper Bot - Панель управления</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
            padding: 40px 20px;
        }
        .header h1 { 
            font-size: 3em; 
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .header p { 
            font-size: 1.2em; 
            opacity: 0.9;
        }
        .card {
            background: white;
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        .card h2 {
            color: #333;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .card h2 i { color: #667eea; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #f8f9fa;
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            transition: transform 0.3s ease;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-card .value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }
        .stat-card .label {
            color: #666;
            font-size: 0.9em;
        }
        .btn {
            display: inline-block;
            background: linear-gradient(to right, #667eea, #764ba2);
            color: white;
            padding: 15px 30px;
            border-radius: 50px;
            text-decoration: none;
            font-weight: bold;
            border: none;
            cursor: pointer;
            font-size: 1.1em;
            transition: all 0.3s ease;
            margin: 5px;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        .btn-telegram {
            background: linear-gradient(to right, #0088cc, #00aced);
        }
        .btn-success {
            background: linear-gradient(to right, #00b09b, #96c93d);
        }
        .btn-danger {
            background: linear-gradient(to right, #dc3545, #c82333);
        }
        .webhook-history {
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #eee;
            border-radius: 10px;
            padding: 15px;
        }
        .webhook-item {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
        }
        .webhook-item.error { border-left-color: #dc3545; }
        .webhook-item.success { border-left-color: #28a745; }
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .status-active { background: #d4edda; color: #155724; }
        .status-inactive { background: #f8d7da; color: #721c24; }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .feature {
            background: #f8f9fa;
            border-radius: 15px;
            padding: 25px;
            text-align: center;
        }
        .feature-icon {
            font-size: 2.5em;
            margin-bottom: 15px;
            color: #667eea;
        }
        .feature h3 {
            margin-bottom: 10px;
            color: #333;
        }
        .instructions {
            background: #fff8e1;
            border-left: 4px solid #ffc107;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
        }
        code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
            display: block;
            margin: 10px 0;
            overflow-x: auto;
        }
        pre {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            overflow-x: auto;
        }
        footer {
            text-align: center;
            color: rgba(255,255,255,0.8);
            margin-top: 50px;
            padding: 20px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        .form-group input, .form-group textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 1em;
        }
        .form-group textarea {
            min-height: 120px;
            resize: vertical;
        }
        @media (max-width: 768px) {
            .header h1 { font-size: 2em; }
            .card { padding: 20px; }
            .stats-grid { grid-template-columns: 1fr; }
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-robot"></i> Konspekt Helper Bot</h1>
            <p>Интеллектуальный помощник для создания конспектов</p>
        </div>
"""
# ==================== КЛАСС TELEGRAM БОТА ====================

class SimpleBot:
    """Основной класс Telegram бота"""
    
    def __init__(self, token: str):
        self.token = token
        self.application = None
        self.user_data = {}
        
    async def start(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        user_id = user.id
        
        # Обновляем статистику
        if user_id not in self.user_data:
            user_stats["total_users"] += 1
            user_stats["active_today"] += 1
            self.user_data[user_id] = {
                "first_seen": datetime.now().isoformat(),
                "conspects_created": 0,
                "messages_count": 0
            }
        
        # Приветственное сообщение
        welcome_text = (
            f"👋 Привет, {user.first_name}!\n\n"
            f"Я — <b>Konspekt Helper Bot</b>, твой помощник в создании конспектов.\n\n"
            f"<b>Что я умею:</b>\n"
            f"• Создавать структурированные конспекты из текста\n"
            f"• Выделять ключевые идеи и тезисы\n"
            f"• Форматировать информацию для лучшего запоминания\n\n"
            f"<b>Доступные команды:</b>\n"
            f"/conspect - Создать конспект из текста\n"
            f"/help - Получить справку\n"
            f"/id - Узнать свой ID\n"
            f"/site - Открыть сайт управления\n\n"
            f"Просто отправь мне текст, и я создам из него конспект!"
        )
        
        # Создаем клавиатуру
        keyboard = [
            [KeyboardButton("/conspect")],
            [KeyboardButton("/help"), KeyboardButton("/site")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
        logger.info(f"New user: {user_id} - {user.first_name}")
        
    async def help_command(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /help"""
        help_text = (
            "📚 <b>Konspekt Helper Bot - Справка</b>\n\n"
            "<b>Основные команды:</b>\n"
            "/start - Начать работу с ботом\n"
            "/conspect [текст] - Создать конспект из текста\n"
            "/id - Узнать свой Telegram ID\n"
            "/site - Открыть веб-сайт управления\n\n"
            "<b>Как использовать:</b>\n"
            "1. Отправь команду /conspect и текст\n"
            "2. Или просто отправь текст, и бот создаст конспект\n"
            "3. Получи структурированный конспект с ключевыми идеями\n\n"
            "<b>Примеры текста для конспекта:</b>\n"
            "• Лекции и учебные материалы\n"
            "• Статьи и научные работы\n"
            "• Доклады и презентации\n"
            "• Книги и главы\n\n"
            "Для связи с разработчиком: /site"
        )
        
        await update.message.reply_text(help_text, parse_mode='HTML')
        
    async def get_user_id(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /id"""
        user = update.effective_user
        user_id = user.id
        
        await update.message.reply_text(
            f"🆔 Ваш Telegram ID: <code>{user_id}</code>\n"
            f"👤 Имя: {user.first_name}\n"
            f"📅 Зарегистрирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode='HTML'
        )
        
    async def site_command(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /site"""
        site_url = WEBHOOK_URL.replace('/webhook', '')
        
        await update.message.reply_text(
            f"🌐 <b>Веб-сайт управления ботом</b>\n\n"
            f"Перейдите по ссылке для управления ботом:\n"
            f"<a href='{site_url}'>{site_url}</a>\n\n"
            f"На сайте вы найдете:\n"
            f"• Статистику использования\n"
            f"• Историю запросов\n"
            f"• Настройки вебхука\n"
            f"• Документацию",
            parse_mode='HTML',
            disable_web_page_preview=False
        )
        
    async def create_conspect(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /conspect и текстовых сообщений"""
        user = update.effective_user
        user_id = user.id
        
        # Получаем текст
        if update.message.text.startswith('/conspect'):
            text = ' '.join(context.args) if context.args else ''
            if not text:
                await update.message.reply_text(
                    "📝 <b>Создание конспекта</b>\n\n"
                    "Отправьте текст для создания конспекта после команды:\n"
                    "<code>/conspect Ваш текст здесь...</code>\n\n"
                    "Или просто отправьте текст без команды.",
                    parse_mode='HTML'
                )
                return
        else:
            text = update.message.text
            
        if not text or len(text) < 10:
            await update.message.reply_text(
                "⚠️ Текст слишком короткий для создания конспекта. "
                "Отправьте текст объемом от 50 символов."
            )
            return
            
        # Обновляем статистику
        user_stats["messages_processed"] += 1
        user_stats["conspects_created"] += 1
        
        if user_id in self.user_data:
            self.user_data[user_id]["conspects_created"] += 1
            self.user_data[user_id]["messages_count"] += 1
        
        # Отправляем сообщение о начале обработки
        processing_msg = await update.message.reply_text(
            "⏳ Обрабатываю текст...",
            parse_mode='HTML'
        )
        
        try:
            # Имитация обработки текста
            await self._process_text_for_conspect(update, context, text, processing_msg)
            
        except Exception as e:
            logger.error(f"Error creating conspect: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при создании конспекта. "
                "Попробуйте еще раз или обратитесь к разработчику."
            )
            
    async def _process_text_for_conspect(self, update: Update, context: CallbackContext, 
                                        text: str, processing_msg) -> None:
        """Обработка текста и создание конспекта"""
        # Имитация обработки
        time.sleep(1)  # Имитация задержки обработки
        
        # Простая логика создания конспекта
        words = text.split()
        sentences = text.split('. ')
        
        # Создаем простой конспект
        conspect = (
            "📋 <b>СОЗДАННЫЙ КОНСПЕКТ</b>\n\n"
            f"<b>Объем исходного текста:</b> {len(words)} слов, {len(text)} символов\n"
            f"<b>Ключевые моменты:</b>\n"
        )
        
        # Добавляем ключевые предложения (первые 3-5 предложений)
        for i, sentence in enumerate(sentences[:5]):
            if sentence.strip():
                conspect += f"• {sentence.strip()}.\n"
        
        # Добавляем статистику
        conspect += f"\n<b>Основные темы:</b>\n"
        
        # Простой анализ слов
        word_freq = {}
        for word in words:
            word_lower = word.lower().strip('.,!?;:()[]{}"\'')
            if len(word_lower) > 4:  # Только слова длиной более 4 символов
                word_freq[word_lower] = word_freq.get(word_lower, 0) + 1
        
        # Топ-5 слов
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        for word, count in top_words:
            conspect += f"#{word} ({count})\n"
        
        # Добавляем рекомендации
        conspect += (
            f"\n<b>Рекомендации по изучению:</b>\n"
            f"1. Сфокусируйтесь на ключевых темах\n"
            f"2. Составьте план изучения\n"
            f"3. Повторите основные идеи\n\n"
            f"<i>Конспект создан: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"
        )
        
        # Удаляем сообщение об обработке
        try:
            await processing_msg.delete()
        except:
            pass
            
        # Отправляем конспект
        await update.message.reply_text(conspect, parse_mode='HTML')
        
        # Отправляем дополнительные действия
        keyboard = [
            [KeyboardButton("Еще конспект"), KeyboardButton("/help")],
            [KeyboardButton("/site")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "✅ Конспект успешно создан!\n\n"
            "Хотите создать еще один конспект или перейти на сайт управления?",
            reply_markup=reply_markup
        )
        
    async def handle_message(self, update: Update, context: CallbackContext) -> None:
        """Обработчик всех текстовых сообщений"""
        if update.message and update.message.text:
            # Если не команда, создаем конспект
            if not update.message.text.startswith('/'):
                await self.create_conspect(update, context)
                
    def setup_handlers(self) -> None:
        """Настройка обработчиков команд"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("id", self.get_user_id))
        self.application.add_handler(CommandHandler("site", self.site_command))
        self.application.add_handler(CommandHandler("conspect", self.create_conspect))
        
        # Обработчик текстовых сообщений
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
    async def run_webhook(self) -> None:
        """Запуск бота в режиме вебхука"""
        if not TELEGRAM_AVAILABLE:
            logger.error("python-telegram-bot не установлен!")
            return
            
        # Создаем Application
        self.application = Application.builder().token(self.token).build()
        
        # Настраиваем обработчики
        self.setup_handlers()
        
        # Устанавливаем вебхук
        webhook_url = f"{WEBHOOK_URL}/webhook"
        await self.application.bot.set_webhook(webhook_url)
        
        logger.info(f"Webhook установлен: {webhook_url}")
        logger.info("Бот запущен в режиме вебхука")
        # ==================== КЛАСС HTTP СЕРВЕРА ====================

class BotServer(BaseHTTPRequestHandler):
    """HTTP сервер для обработки вебхуков и отдачи сайта"""
    
    def log_message(self, format, *args):
        """Кастомное логирование HTTP запросов"""
        logger.info(f"{self.address_string()} - {format % args}")
        
    def do_GET(self):
        """Обработка GET запросов (веб-сайт)"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Обновляем статистику для логов
        webhook_history.append({
            "timestamp": datetime.now().isoformat(),
            "method": "GET",
            "path": path,
            "status": "success"
        })
        
        # Ограничиваем историю
        if len(webhook_history) > 50:
            webhook_history.pop(0)
            
        # Маршрутизация
        if path == '/':
            self._serve_main_page()
        elif path == '/health':
            self._serve_health_check()
        elif path == '/stats':
            self._serve_stats_json()
        elif path == '/webhook-info':
            self._serve_webhook_info()
        elif path == '/setup-webhook':
            self._setup_webhook_page()
        elif path == '/test':
            self._serve_test_page()
        elif path == '/logs':
            self._serve_logs_page()
        else:
            self._serve_404()
            
    def do_POST(self):
        """Обработка POST запросов (вебхуки от Telegram)"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            # Парсим JSON
            data = json.loads(post_data.decode('utf-8'))
            
            # Логируем вебхук
            webhook_entry = {
                "timestamp": datetime.now().isoformat(),
                "method": "POST",
                "path": self.path,
                "update_id": data.get('update_id', 'unknown'),
                "status": "received"
            }
            webhook_history.append(webhook_entry)
            
            # Ограничиваем историю
            if len(webhook_history) > 50:
                webhook_history.pop(0)
            
            # Если это вебхук от Telegram
            if self.path == '/webhook' and TELEGRAM_AVAILABLE and bot_instance:
                # Обрабатываем через бота
                update = Update.de_json(data, bot_instance.application.bot)
                bot_instance.application.update_queue.put_nowait(update)
                
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'OK')
                
                logger.info(f"Webhook processed: update_id={data.get('update_id')}")
                
            else:
                self.send_response(404)
                self.end_headers()
                
        except Exception as e:
            logger.error(f"Error processing POST: {e}")
            
            # Логируем ошибку
            webhook_history.append({
                "timestamp": datetime.now().isoformat(),
                "method": "POST",
                "path": self.path,
                "status": f"error: {str(e)}"
            })
            
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Internal Server Error')
    
    def _serve_main_page(self):
        """Главная страница управления"""
        # Статистика
        webhook_status = "✅ Активен" if TELEGRAM_AVAILABLE else "❌ Не настроен"
        
        # Генерируем историю вебхуков
        history_html = ""
        for entry in reversed(webhook_history[-10:]):  # Последние 10 записей
            status_class = "success" if entry.get("status") in ["success", "received"] else "error"
            time_str = datetime.fromisoformat(entry["timestamp"]).strftime("%H:%M:%S")
            
            history_html += f"""
            <div class="webhook-item {status_class}">
                <div style="display: flex; justify-content: space-between;">
                    <span><strong>{entry['method']} {entry['path']}</strong></span>
                    <span>{time_str}</span>
                </div>
                <div style="font-size: 0.9em; color: #666; margin-top: 5px;">
                    Статус: {entry.get('status', 'unknown')}
                    {f" | Update ID: {entry.get('update_id', '')}" if entry.get('update_id') else ""}
                </div>
            </div>
            """
        
        if not history_html:
            history_html = "<p style='text-align: center; color: #666;'>История вебхуков пуста</p>"
        
        # Формируем HTML
        html_content = HTML_TEMPLATE + f"""
        <!-- Статистика -->
        <div class="card">
            <h2><i class="fas fa-chart-bar"></i> Статистика</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="label">Всего пользователей</div>
                    <div class="value">{user_stats['total_users']}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Конспектов создано</div>
                    <div class="value">{user_stats['conspects_created']}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Сообщений обработано</div>
                    <div class="value">{user_stats['messages_processed']}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Статус бота</div>
                    <div class="value">
                        <span class="status-badge status-active">Активен</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Управление -->
        <div class="card">
            <h2><i class="fas fa-cogs"></i> Управление</h2>
            <p style="margin-bottom: 20px;">Настройте и управляйте вашим ботом</p>
            <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px;">
                <a href="https://t.me/{BOT_USERNAME}" target="_blank" class="btn btn-telegram">
                    <i class="fab fa-telegram"></i> Открыть в Telegram
                </a>
                <a href="/setup-webhook" class="btn btn-success">
                    <i class="fas fa-link"></i> Настроить вебхук
                </a>
                <a href="/test" class="btn">
                    <i class="fas fa-vial"></i> Тест API
                </a>
                <a href="/logs" class="btn">
                    <i class="fas fa-file-alt"></i> Посмотреть логи
                </a>
                <a href="/stats" class="btn">
                    <i class="fas fa-database"></i> JSON статистика
                </a>
            </div>
            <div id="webhook-status" class="instructions">
                <p><strong>Вебхук:</strong> {webhook_status}</p>
                <p><strong>URL:</strong> <code>{WEBHOOK_URL}/webhook</code></p>
                <p><strong>Токен:</strong> <code>{TOKEN[:10]}...{TOKEN[-10:] if len(TOKEN) > 20 else ''}</code></p>
                <p><small>Для настройки вебхука нажмите кнопку "Настроить вебхук"</small></p>
            </div>
        </div>

        <!-- Функции -->
        <div class="card">
            <h2><i class="fas fa-star"></i> Возможности бота</h2>
            <div class="features">
                <div class="feature">
                    <div class="feature-icon">📝</div>
                    <h3>Создание конспектов</h3>
                    <p>Автоматическое выделение главных идей из текста</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">📊</div>
                    <h3>Структурирование</h3>
                    <p>Разбивка на разделы, подзаголовки и списки</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">⚡</div>
                    <h3>Быстрая обработка</h3>
                    <p>Мгновенная генерация конспектов</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">📚</div>
                    <h3>Экспорт</h3>
                    <p>Сохранение в разных форматах</p>
                </div>
            </div>
        </div>

        <!-- Форма создания конспекта -->
        <div class="card">
            <h2><i class="fas fa-edit"></i> Создать конспект (тест)</h2>
            <form action="/test-conspect" method="POST" style="margin-top: 20px;">
                <div class="form-group">
                    <label for="text">Текст для конспекта:</label>
                    <textarea id="text" name="text" placeholder="Введите текст для создания конспекта..."></textarea>
                </div>
                <button type="submit" class="btn btn-success">
                    <i class="fas fa-magic"></i> Создать конспект
                </button>
            </form>
        </div>

        <!-- История вебхуков -->
        <div class="card">
            <h2><i class="fas fa-history"></i> Последние вебхуки</h2>
            <div class="webhook-history">
                {history_html}
            </div>
            <p style="text-align: center; margin-top: 10px; color: #666;">
                Показано {min(10, len(webhook_history))} из {len(webhook_history)} записей
            </p>
        </div>

        <!-- Инструкции -->
        <div class="card">
            <h2><i class="fas fa-info-circle"></i> Инструкция по настройке</h2>
            <div class="instructions">
                <p><strong>1. Установите вебхук:</strong></p>
                <code>curl "https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}/webhook"</code>
                
                <p style="margin-top: 15px;"><strong>2. Проверьте статус:</strong></p>
                <code>curl "https://api.telegram.org/bot{TOKEN}/getWebhookInfo"</code>
                
                <p style="margin-top: 15px;"><strong>3. Удалите вебхук (если нужно):</strong></p>
                <code>curl "https://api.telegram.org/bot{TOKEN}/deleteWebhook"</code>
                
                <p style="margin-top: 15px;"><strong>4. Основные команды бота:</strong></p>
                <ul style="margin-left: 20px; margin-top: 10px;">
                    <li><code>/start</code> - Начало работы</li>
                    <li><code>/help</code> - Справка</li>
                    <li><code>/conspect [текст]</code> - Создать конспект</li>
                    <li><code>/id</code> - Узнать свой ID</li>
                    <li><code>/site</code> - Открыть этот сайт</li>
                </ul>
            </div>
        </div>

        <footer>
            <p>Konspekt Helper Bot © 2024 | Работает на Render.com</p>
            <p>Версия 1.0 | Последнее обновление: {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
        </footer>
    </div>

    <script>
        function setupWebhook() {{
            fetch('/setup-webhook')
                .then(response => response.text())
                .then(data => {{
                    alert('Вебхук настроен!');
                }});
        }}
        
        // Автообновление статистики каждые 30 секунд
        setInterval(() => {{
            fetch('/stats')
                .then(response => response.json())
                .then(data => {{
                    document.getElementById('total-users').textContent = data.total_users;
                    document.getElementById('total-conspects').textContent = data.conspects_created;
                    document.getElementById('webhooks-today').textContent = data.webhooks_today;
                }});
        }}, 30000);
    </script>
</body>
</html>
"""
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def _serve_health_check(self):
        """Проверка здоровья сервиса"""
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "Konspekt Helper Bot",
            "version": "1.0",
            "telegram_available": TELEGRAM_AVAILABLE,
            "webhook_url": WEBHOOK_URL,
            "users_count": user_stats["total_users"]
        }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(health_data, ensure_ascii=False).encode('utf-8'))
    
    def _serve_stats_json(self):
        """JSON статистика"""
        # Считаем вебхуки за сегодня
        today = datetime.now().date().isoformat()
        webhooks_today = sum(
            1 for entry in webhook_history 
            if datetime.fromisoformat(entry["timestamp"]).date().isoformat() == today
        )
        
        stats_data = {
            "bot": {
                "username": BOT_USERNAME,
                "webhook_url": f"{WEBHOOK_URL}/webhook",
                "telegram_available": TELEGRAM_AVAILABLE
            },
            "statistics": user_stats,
            "webhooks": {
                "total": len(webhook_history),
                "today": webhooks_today,
                "last_10": webhook_history[-10:] if webhook_history else []
            },
            "system": {
                "timestamp": datetime.now().isoformat(),
                "python_version": "3.11.8",
                "service": "Render.com"
            }
        }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(stats_data, ensure_ascii=False, indent=2).encode('utf-8'))
    
    def _serve_webhook_info(self):
        """Информация о вебхуке"""
        info_html = f"""
        <html>
        <head><title>Webhook Info</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h1>Webhook Information</h1>
            <p><strong>URL:</strong> {WEBHOOK_URL}/webhook</p>
            <p><strong>Token:</strong> {TOKEN[:15]}...{TOKEN[-10:] if len(TOKEN) > 25 else ''}</p>
            <p><strong>Status:</strong> {'Active' if TELEGRAM_AVAILABLE else 'Not configured'}</p>
            <p><a href="/">Back to main page</a></p>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(info_html.encode('utf-8'))
    
    def _setup_webhook_page(self):
        """Страница настройки вебхука"""
        # Пытаемся настроить вебхук
        success = False
        message = ""
        
        if TELEGRAM_AVAILABLE and bot_instance and bot_instance.application:
            try:
                import asyncio
                
                # Создаем новое event loop для этого потока
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Устанавливаем вебхук
                loop.run_until_complete(
                    bot_instance.application.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
                )
                
                success = True
                message = "✅ Вебхук успешно настроен!"
                
                # Логируем действие
                webhook_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "method": "SETUP",
                    "path": "/setup-webhook",
                    "status": "webhook configured"
                })
                
            except Exception as e:
                success = False
                message = f"❌ Ошибка: {str(e)}"
        else:
            message = "❌ Telegram бот не инициализирован"
        
        # Формируем ответ
        result_html = f"""
        <html>
        <head>
            <title>Setup Webhook</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 40px; text-align: center; }}
                .success {{ color: green; font-size: 1.2em; }}
                .error {{ color: red; font-size: 1.2em; }}
                .code {{ background: #f4f4f4; padding: 10px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>Настройка вебхука</h1>
            <div class="{ 'success' if success else 'error' }">
                {message}
            </div>
            
            <div class="code">
                <p><strong>URL вебхука:</strong></p>
                <code>{WEBHOOK_URL}/webhook</code>
                
                <p style="margin-top: 20px;"><strong>Команда для ручной настройки:</strong></p>
                <code>curl "https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}/webhook"</code>
            </div>
            
            <div style="margin-top: 30px;">
                <a href="/" style="padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px;">
                    Вернуться на главную
                </a>
            </div>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(result_html.encode('utf-8'))
    
    def _serve_test_page(self):
        """Тестовая страница API"""
        test_html = """
        <html>
        <head><title>API Test</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h1>API Test Endpoints</h1>
            <ul>
                <li><a href="/health">/health</a> - Health check</li>
                <li><a href="/stats">/stats</a> - Statistics (JSON)</li>
                <li><a href="/webhook-info">/webhook-info</a> - Webhook information</li>
            </ul>
            <p><a href="/">Back to main page</a></p>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(test_html.encode('utf-8'))
    
    def _serve_logs_page(self):
        """Страница с логами"""
        # Получаем последние 20 логов
        logs = []
        for handler in logger.handlers:
            if hasattr(handler, 'baseFilename'):
                try:
                    with open(handler.baseFilename, 'r', encoding='utf-8') as f:
                        logs = f.readlines()[-20:]  # Последние 20 строк
                except:
                    logs = ["Log file not available"]
        
        logs_html = "<br>".join(html.escape(log.strip()) for log in logs if log.strip())
        
        page_html = f"""
        <html>
        <head>
            <title>Logs</title>
            <style>
                body {{ font-family: monospace; padding: 20px; background: #f5f5f5; }}
                .log-container {{ background: white; padding: 20px; border-radius: 5px; }}
                .log-line {{ margin: 5px 0; padding: 5px; border-bottom: 1px solid #eee; }}
            </style>
        </head>
        <body>
            <h1>System Logs</h1>
            <p>Showing last 20 log entries:</p>
            <div class="log-container">
                {logs_html}
            </div>
            <p><a href="/">Back to main page</a></p>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(page_html.encode('utf-8'))
    
    def _serve_404(self):
        """Страница 404"""
        self.send_response(404)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        
        html_404 = """
        <html>
        <head><title>404 Not Found</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1>404 - Страница не найдена</h1>
            <p>Запрошенная страница не существует.</p>
            <p><a href="/">Вернуться на главную</a></p>
        </body>
        </html>
        """
        self.wfile.write(html_404.encode('utf-8'))
        # ==================== ГЛОБАЛЬНЫЕ ЭКЗЕМПЛЯРЫ ====================

bot_instance = None
server_instance = None

# ==================== ФУНКЦИИ ЗАПУСКА ====================

async def start_bot():
    """Запуск Telegram бота в отдельном потоке"""
    global bot_instance
    
    if not TELEGRAM_AVAILABLE:
        logger.warning("Telegram бот не может быть запущен (библиотека не установлена)")
        return
    
    if not TOKEN or TOKEN == 'DEMO_TOKEN_FOR_TESTING':
        logger.warning("Токен бота не настроен. Запускаю в демо-режиме.")
        return
    
    try:
        bot_instance = SimpleBot(TOKEN)
        await bot_instance.run_webhook()
        logger.info("Telegram бот успешно запущен")
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")

def start_http_server():
    """Запуск HTTP сервера"""
    global server_instance
    
    server_address = ('', PORT)
    server_instance = HTTPServer(server_address, BotServer)
    
    logger.info(f"HTTP сервер запущен на порту {PORT}")
    logger.info(f"Веб-сайт доступен по адресу: http://localhost:{PORT}")
    logger.info(f"Вебхук Telegram: {WEBHOOK_URL}/webhook")
    
    try:
        server_instance.serve_forever()
    except KeyboardInterrupt:
        logger.info("Сервер остановлен")
    except Exception as e:
        logger.error(f"Ошибка сервера: {e}")

def run_server():
    """Основная функция запуска сервера"""
    import asyncio
    import threading
    
    # Запускаем бот в отдельном потоке
    if TELEGRAM_AVAILABLE and TOKEN and TOKEN != 'DEMO_TOKEN_FOR_TESTING':
        bot_thread = threading.Thread(
            target=lambda: asyncio.run(start_bot()),
            daemon=True
        )
        bot_thread.start()
        logger.info("Поток Telegram бота запущен")
    else:
        logger.warning("Telegram бот запущен в демо-режиме. Установите TELEGRAM_TOKEN для полноценной работы.")
    
    # Запускаем HTTP сервер в основном потоке
    start_http_server()

# ==================== ТОЧКА ВХОДА ====================

if __name__ == '__main__':
    print("=" * 60)
    print("KONSPEKT HELPER BOT - Запуск системы")
    print("=" * 60)
    print(f"Версия: 1.0")
    print(f"Python: 3.11.8 (рекомендуемая для Render)")
    print(f"Telegram Bot API: {'Доступен' if TELEGRAM_AVAILABLE else 'Не доступен'}")
    print(f"Порт: {PORT}")
    print(f"Вебхук URL: {WEBHOOK_URL}")
    print(f"Токен бота: {'Установлен' if TOKEN and TOKEN != 'DEMO_TOKEN_FOR_TESTING' else 'Не установлен'}")
    print("=" * 60)
    
    # Проверяем переменные окружения
    if not TOKEN or TOKEN == 'DEMO_TOKEN_FOR_TESTING':
        print("\n⚠️  ВНИМАНИЕ: Токен бота не установлен!")
        print("Установите переменную окружения TELEGRAM_TOKEN")
        print("На Render: Settings -> Environment Variables")
        print("Или в локальном запуске: export TELEGRAM_TOKEN='ваш_токен'")
        print("\nБот запустится в демо-режиме без Telegram функционала.")
    
    if not WEBHOOK_URL or 'localhost' in WEBHOOK_URL:
        print("\nℹ️  WEBHOOK_URL не настроен, используется localhost")
        print("На Render это настроится автоматически")
    
    print("\nЗапуск системы...")
    print("Доступные эндпоинты:")
    print(f"  • Веб-сайт: http://localhost:{PORT}")
    print(f"  • Проверка здоровья: http://localhost:{PORT}/health")
    print(f"  • Статистика (JSON): http://localhost:{PORT}/stats")
    print(f"  • Вебхук Telegram: http://localhost:{PORT}/webhook")
    print("\nДля остановки нажмите Ctrl+C")
    print("=" * 60 + "\n")
    
    # Запускаем сервер
    run_server()
