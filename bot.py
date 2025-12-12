#!/usr/bin/env python3
"""
Konspekt Helper Bot - Оптимизирован для Render
Без хардкода токенов в коде
"""

import os
import logging
import json
import requests
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import threading
import time

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (ТОЛЬКО ИЗ RENDER) ====================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "13aac457275834df9")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")
PORT = int(os.getenv("PORT", 10000))

# ==================== ПРОВЕРКА КОНФИГУРАЦИИ ====================
logger.info("=" * 60)
logger.info("🚀 ЗАПУСК KONSPEKT HELPER BOT")
logger.info("=" * 60)

# Проверяем обязательные переменные
missing_vars = []
if not TELEGRAM_TOKEN:
    missing_vars.append("TELEGRAM_TOKEN")
if not GOOGLE_API_KEY:
    missing_vars.append("GOOGLE_API_KEY")

if missing_vars:
    logger.error(f"❌ Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
    logger.error("Добавьте их в Render Dashboard -> Environment")
    exit(1)

logger.info("✅ Все переменные окружения загружены")

# ==================== СТАТИСТИКА ====================
stats = {
    "total_users": 0,
    "total_messages": 0,
    "conspects_created": 0,
    "google_searches": 0,
    "start_time": datetime.now().isoformat(),
    "user_states": {}
}

# ==================== GOOGLE SEARCH API ====================
class GoogleSearchAPI:
    def __init__(self):
        self.api_key = GOOGLE_API_KEY
        self.cse_id = GOOGLE_CSE_ID
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.cache = {}
        logger.info("✅ Google Search API готов")
    
    def search(self, query, num_results=3):
        """Выполняет поиск через Google Custom Search API"""
        if not query or len(query.strip()) < 2:
            return self._create_fallback_result(query, "Пустой запрос")
        
        # Проверяем кэш
        cache_key = f"{query}_{num_results}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Обновляем статистику
        stats["google_searches"] += 1
        
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "num": min(num_results, 5),
            "hl": "ru",
            "lr": "lang_ru"
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code == 403:
                logger.error("❌ Доступ запрещен. Проверьте API ключ в Google Cloud Console")
                return self._create_fallback_result(query, "API доступ запрещен")
            
            if response.status_code == 429:
                logger.warning("⚠️ Превышен лимит запросов (100/день)")
                return self._create_fallback_result(query, "Достигнут дневной лимит")
            
            response.raise_for_status()
            data = response.json()
            
            result = self._parse_results(data, query)
            self.cache[cache_key] = result
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Ошибка сети: {e}")
            return self._create_fallback_result(query, f"Ошибка сети: {str(e)[:50]}")
    
    def _parse_results(self, data, query):
        """Парсит результаты поиска"""
        items = []
        if "items" in data:
            for item in data["items"][:3]:
                items.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "source": item.get("displayLink", "")
                })
        
        return {
            "success": True,
            "query": query,
            "items": items,
            "total": len(items),
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_fallback_result(self, query, reason=""):
        """Создает fallback-результат при ошибке"""
        return {
            "success": False,
            "query": query,
            "items": [{
                "title": f"Информация по запросу: {query}",
                "snippet": f"Данные будут обновлены позже. {reason}",
                "source": "локальная база"
            }],
            "total": 1,
            "fallback": True,
            "timestamp": datetime.now().isoformat()
        }

# ==================== ГЕНЕРАТОР КОНСПЕКТОВ ====================
class ConspectGenerator:
    def __init__(self):
        self.searcher = GoogleSearchAPI()
        logger.info("✅ Генератор конспектов готов")
    
    def generate(self, topic, volume="short"):
        """Генерирует конспект на основе поиска"""
        # Проверка пасхалки
        if self._is_easter_egg(topic):
            return self._create_easter_egg_response()
        
        # Выполняем поиск
        search_results = self.searcher.search(topic)
        
        # Генерируем конспект в зависимости от объема
        if volume == "detailed":
            return self._create_detailed_conspect(topic, search_results)
        elif volume == "extended":
            return self._create_extended_conspect(topic, search_results)
        else:
            return self._create_short_conspect(topic, search_results)
    
    def _is_easter_egg(self, text):
        """Проверяет, является ли запрос пасхалкой"""
        text_lower = text.lower()
        easter_phrases = [
            "план захвата польши",
            "захват польши",
            "чай и польша"
        ]
        return any(phrase in text_lower for phrase in easter_phrases)
    
    def _create_easter_egg_response(self):
        """Создает ответ для пасхалки"""
        responses = [
            "🍵 *Секретная пасхалка активирована!*\n\nСтатус: Чайный мастер. Фокся уже в пути!",
            "🍵 *Поздравляем!* Вы нашли секрет!\n\nЧай заварен, фокся скоро будет здесь!",
            "🍵 *Wow! Easter egg found!*\n\nTea status: ACTIVE. Foksya incoming!"
        ]
        import random
        return random.choice(responses)
    
    def _create_short_conspect(self, topic, results):
        """Создает краткий конспект"""
        conspect = f"📄 *КОНСПЕКТ: {topic.upper()}*\n\n"
        
        conspect += f"🔍 *Результаты поиска:* {results['total']} источников\n\n"
        
        if results["items"]:
            conspect += "*ОСНОВНЫЕ ТЕЗИСЫ:*\n"
            for i, item in enumerate(results["items"][:2], 1):
                snippet = item["snippet"]
                if len(snippet) > 120:
                    snippet = snippet[:120] + "..."
                conspect += f"{i}. {snippet}\n"
        else:
            conspect += "*ИНФОРМАЦИЯ:*\nТема требует дополнительного изучения.\n"
        
        conspect += f"\n💡 *ВЫВОД:* Тема актуальна для исследования.\n\n"
        conspect += f"🤖 *@Konspekt_help_bot* | 🌐 *Google Search API*"
        
        return conspect
    
    def _create_detailed_conspect(self, topic, results):
        """Создает подробный конспект"""
        conspect = f"📚 *ПОДРОБНЫЙ АНАЛИЗ: {topic.upper()}*\n\n"
        
        conspect += "*ИСТОЧНИКИ ИНФОРМАЦИИ:*\n"
        if results["items"]:
            for i, item in enumerate(results["items"], 1):
                conspect += f"{i}. *{item['title']}*\n"
                snippet = item["snippet"]
                if len(snippet) > 150:
                    snippet = snippet[:150] + "..."
                conspect += f"   {snippet}\n"
                if item["source"]:
                    conspect += f"   📍 {item['source']}\n"
                conspect += "\n"
        
        conspect += "*СТРУКТУРА ИССЛЕДОВАНИЯ:*\n"
        sections = [
            "Теоретические основы",
            "Практическое применение",
            "Актуальные тенденции",
            "Перспективы развития"
        ]
        for section in sections:
            conspect += f"• {section}\n"
        
        conspect += f"\n📊 *Всего проанализировано:* {results['total']} источников\n"
        conspect += f"🤖 *Автоматически сгенерировано @Konspekt_help_bot*"
        
        return conspect
    
    def _create_extended_conspect(self, topic, results):
        """Создает развернутый конспект"""
        conspect = f"📖 *ПОЛНОЕ ИССЛЕДОВАНИЕ: {topic.upper()}*\n\n"
        
        conspect += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        conspect += "ЧАСТЬ 1: МЕТОДОЛОГИЯ ИССЛЕДОВАНИЯ\n"
        conspect += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        conspect += f"*ИССЛЕДОВАТЕЛЬСКИЙ ЗАПРОС:*\n{topic}\n\n"
        conspect += f"*ОБЪЕМ ДАННЫХ:* {results['total']} источников\n"
        conspect += f"*ВРЕМЯ АНАЛИЗА:* {datetime.now().strftime('%H:%M')}\n\n"
        
        conspect += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        conspect += "ЧАСТЬ 2: АНАЛИТИЧЕСКИЕ ВЫВОДЫ\n"
        conspect += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        conspect += "*КЛЮЧЕВЫЕ НАПРАВЛЕНИЯ ДЛЯ ИЗУЧЕНИЯ:*\n"
        directions = [
            "Изучение базовых понятий и определений",
            "Анализ различных методологических подходов",
            "Исследование исторического контекста",
            "Рассмотрение практических кейсов применения",
            "Оценка современных тенденций и перспектив"
        ]
        for i, direction in enumerate(directions, 1):
            conspect += f"{i}. {direction}\n"
        
        conspect += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        conspect += f"*ИССЛЕДОВАНИЕ ВЫПОЛНЕНО С ИСПОЛЬЗОВАНИЕМ:*\n"
        conspect += f"• Google Custom Search API\n"
        conspect += f"• Платформа Render.com\n"
        conspect += f"• 🤖 @Konspekt_help_bot\n"
        conspect += f"• ⏱ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        return conspect

# ==================== TELEGRAM BOT ====================
class TelegramBot:
    def __init__(self):
        if not TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN не найден в переменных окружения")
        
        self.token = TELEGRAM_TOKEN
        self.bot_url = f"https://api.telegram.org/bot{self.token}"
        self.generator = ConspectGenerator()
        
        # Настраиваем вебхук
        if RENDER_EXTERNAL_URL:
            self._setup_webhook()
        
        logger.info("✅ Telegram бот инициализирован")
    
    def _setup_webhook(self):
        """Настраивает вебхук Telegram на Render URL"""
        webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
        try:
            response = requests.post(
                f"{self.bot_url}/setWebhook",
                json={"url": webhook_url},
                timeout=10
            )
            if response.json().get("ok"):
                logger.info(f"✅ Вебхук установлен: {webhook_url}")
            else:
                logger.warning(f"⚠️ Не удалось установить вебхук")
        except Exception as e:
            logger.error(f"❌ Ошибка настройки вебхука: {e}")
    
    def process_message(self, chat_id, text):
        """Обрабатывает входящее сообщение"""
        text = text.strip()
        
        # Обновляем статистику
        self._update_stats(chat_id)
        
        # Обработка команд
        if text.startswith("/"):
            if text == "/start":
                return self._send_welcome(chat_id)
            elif text == "/help":
                return self._send_help(chat_id)
            elif text == "/stats":
                return self._send_stats(chat_id)
            else:
                return self._send_message(chat_id, "❓ Неизвестная команда. Используйте /help")
        
        # Обработка выбора объема (1, 2, 3)
        if text in ["1", "2", "3"]:
            return self._handle_volume_selection(chat_id, text)
        
        # Обработка новой темы
        return self._handle_new_topic(chat_id, text)
    
    def _send_welcome(self, chat_id):
        """Отправляет приветственное сообщение"""
        welcome = (
            "👋 *Добро пожаловать в Konspekt Helper Bot!*\n\n"
            "🤖 *Я — интеллектуальный помощник для создания конспектов!*\n\n"
            "🚀 *Как это работает:*\n"
            "1. Отправьте тему для изучения\n"
            "2. Выберите объем (1-3)\n"
            "3. Получите готовый конспект\n\n"
            "📊 *Доступные форматы:*\n"
            "• *1* — Краткий (основные идеи)\n"
            "• *2* — Подробный (с анализом)\n"
            "• *3* — Развернутый (полное исследование)\n\n"
            "🔍 *Использую Google Search API*\n"
            "🌐 *Работаю на Render.com*\n\n"
            "🎯 *Отправьте тему для начала!*"
        )
        return self._send_message(chat_id, welcome)
    
    def _send_help(self, chat_id):
        """Отправляет справку"""
        help_text = (
            "📚 *СПРАВКА ПО ИСПОЛЬЗОВАНИЮ БОТА*\n\n"
            "*Основные команды:*\n"
            "/start - Начало работы\n"
            "/help - Эта справка\n"
            "/stats - Статистика бота\n\n"
            "*Процесс создания конспекта:*\n"
            "1. Отправьте тему (например: 'Искусственный интеллект')\n"
            "2. Выберите цифру 1, 2 или 3\n"
            "3. Получите готовый конспект\n\n"
            "*Технологии:*\n"
            "• Google Custom Search API\n"
            "• Python + Render.com\n"
            "• Telegram Bot API"
        )
        return self._send_message(chat_id, help_text)
    
    def _send_stats(self, chat_id):
        """Отправляет статистику"""
        stat_text = (
            f"📊 *СТАТИСТИКА БОТА*\n\n"
            f"👥 Пользователей: {stats['total_users']}\n"
            f"💬 Сообщений: {stats['total_messages']}\n"
            f"📄 Конспектов: {stats['conspects_created']}\n"
            f"🔍 Поисков Google: {stats['google_searches']}\n"
            f"⏱ Запущен: {stats['start_time'][:10]}\n\n"
            f"🌐 Хостинг: Render.com\n"
            f"🔗 URL: {RENDER_EXTERNAL_URL or 'не настроен'}"
        )
        return self._send_message(chat_id, stat_text)
    
    def _handle_new_topic(self, chat_id, topic):
        """Обрабатывает новую тему"""
        # Сохраняем тему в состоянии пользователя
        user_id = str(chat_id)
        if user_id not in stats["user_states"]:
            stats["user_states"][user_id] = {}
        
        stats["user_states"][user_id]["pending_topic"] = topic
        
        # Предлагаем выбрать объем
        response = (
            f"🎯 *ТЕМА ПРИНЯТА: {topic}*\n\n"
            f"✅ Готовлю поиск в Google...\n\n"
            f"📊 *ВЫБЕРИТЕ ОБЪЕМ КОНСПЕКТА:*\n\n"
            f"1️⃣ *КРАТКИЙ*\nОсновные тезисы и выводы\n\n"
            f"2️⃣ *ПОДРОБНЫЙ*\nС анализом источников\n\n"
            f"3️⃣ *РАЗВЕРНУТЫЙ*\nПолное исследование\n\n"
            f"🔢 *Отправьте цифру 1, 2 или 3*"
        )
        return self._send_message(chat_id, response)
    
    def _handle_volume_selection(self, chat_id, volume_choice):
        """Обрабатывает выбор объема"""
        user_id = str(chat_id)
        user_state = stats["user_states"].get(user_id, {})
        topic = user_state.get("pending_topic", "")
        
        if not topic:
            return self._send_message(chat_id, "❌ Сначала отправьте тему для поиска")
        
        volume_map = {"1": "short", "2": "detailed", "3": "extended"}
        volume = volume_map.get(volume_choice, "short")
        
        # Уведомляем о начале обработки
        self._send_message(
            chat_id, 
            f"🔍 *ИЩУ ИНФОРМАЦИЮ В GOOGLE...*\n\nТема: {topic}\nОбъем: {volume_choice}"
        )
        
        try:
            # Генерируем конспект
            conspect = self.generator.generate(topic, volume)
            stats["conspects_created"] += 1
            
            # Отправляем результат
            result = (
                f"✅ *КОНСПЕКТ ГОТОВ!*\n\n"
                f"📌 Тема: {topic}\n"
                f"📊 Объем: {volume_choice}/3\n"
                f"🔍 Использовано поисков: {stats['google_searches']}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{conspect}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🔄 *Другой объем?* Отправьте 1, 2 или 3\n"
                f"🎯 *Новая тема?* Просто напишите её!"
            )
            
            return self._send_message(chat_id, result)
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации конспекта: {e}")
            return self._send_message(
                chat_id,
                f"❌ *Ошибка при создании конспекта*\n\n"
                f"Попробуйте другую тему или повторите позже.\n\n"
                f"Ошибка: {str(e)[:100]}"
            )
    
    def _update_stats(self, chat_id):
        """Обновляет статистику"""
        user_id = str(chat_id)
        
        if user_id not in stats["user_states"]:
            stats["total_users"] += 1
            stats["user_states"][user_id] = {
                "first_seen": datetime.now().isoformat(),
                "message_count": 0
            }
        
        stats["user_states"][user_id]["last_seen"] = datetime.now().isoformat()
        stats["user_states"][user_id]["message_count"] += 1
        stats["total_messages"] += 1
    
    def _send_message(self, chat_id, text):
        """Отправляет сообщение в Telegram"""
        try:
            response = requests.post(
                f"{self.bot_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True
                },
                timeout=10
            )
            return response.json().get("ok", False)
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения: {e}")
            return False

# ==================== HTTP СЕРВЕР ДЛЯ RENDER ====================
class BotHTTPServer(BaseHTTPRequestHandler):
    """HTTP сервер для обработки вебхуков и отдачи статики"""
    
    def do_GET(self):
        """Обрабатывает GET запросы"""
        path = self.path.split('?')[0]
        
        if path == "/":
            self._send_html(INDEX_HTML)
        elif path == "/health":
            self._send_json({"status": "ok", "time": datetime.now().isoformat()})
        elif path == "/stats":
            self._send_json(stats)
        elif path == "/webhook":
            # Для проверки вебхука
            self._send_json({"webhook": "active", "url": f"{RENDER_EXTERNAL_URL}/webhook"})
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Обрабатывает POST запросы (Telegram вебхук)"""
        if self.path == "/webhook":
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length:
                try:
                    data = self.rfile.read(content_length)
                    update = json.loads(data.decode('utf-8'))
                    
                    # Обрабатываем в отдельном потоке
                    threading.Thread(
                        target=self._handle_telegram_update,
                        args=(update,),
                        daemon=True
                    ).start()
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки вебхука: {e}")
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def _handle_telegram_update(self, update):
        """Обрабатывает обновление от Telegram"""
        try:
            if "message" in update and "text" in update["message"]:
                chat_id = update["message"]["chat"]["id"]
                text = update["message"]["text"]
                
                bot = TelegramBot()
                bot.process_message(chat_id, text)
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
    
    def _send_html(self, content):
        """Отправляет HTML ответ"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))
    
    def _send_json(self, data):
        """Отправляет JSON ответ"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Отключает логирование запросов"""
        pass

# HTML для статусной страницы
INDEX_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 Konspekt Helper Bot</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .status {
            display: flex;
            align-items: center;
            margin-bottom: 30px;
        }
        .status-dot {
            width: 12px;
            height: 12px;
            background: #10b981;
            border-radius: 50%;
            margin-right: 10px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 30px 0;
        }
        .stat-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }
        .btn {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: bold;
            margin: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="status">
            <div class="status-dot"></div>
            <h1>🤖 Konspekt Helper Bot</h1>
        </div>
        
        <p>Telegram бот для создания интеллектуальных конспектов с использованием Google Search API</p>
        
        <div class="stats-grid" id="stats">
            <div class="stat-card">
                <div class="stat-value" id="users">0</div>
                <div>Пользователей</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="messages">0</div>
                <div>Сообщений</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="conspects">0</div>
                <div>Конспектов</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="searches">0</div>
                <div>Поисков</div>
            </div>
        </div>
        
        <h2>🔗 Ссылки</h2>
        <div>
            <a href="https://t.me/Konspekt_help_bot" class="btn" target="_blank">🤖 Открыть бота</a>
            <a href="/stats" class="btn">📊 Статистика</a>
            <a href="/health" class="btn">❤️ Health Check</a>
        </div>
        
        <h2>🚀 Технологии</h2>
        <ul>
            <li><strong>Google Custom Search API</strong> - настоящий поиск в интернете</li>
            <li><strong>Telegram Bot API</strong> - общение с пользователями</li>
            <li><strong>Python 3.11</strong> - бэкенд логика</li>
            <li><strong>Render.com</strong> - облачный хостинг</li>
        </ul>
        
        <h2>📚 Как использовать</h2>
        <ol>
            <li>Откройте <a href="https://t.me/Konspekt_help_bot" target="_blank">@Konspekt_help_bot</a></li>
            <li>Отправьте любую тему для изучения</li>
            <li>Выберите объем конспекта (1, 2 или 3)</li>
            <li>Получите готовый конспект на основе поиска Google</li>
        </ol>
        
        <p style="margin-top: 30px; color: #666; font-size: 14px;">
            Система автоматически обновляется. Текущее время: <span id="time"></span>
        </p>
    </div>
    
    <script>
        async function updateStats() {
            try {
                const res = await fetch('/stats');
                const data = await res.json();
                
                document.getElementById('users').textContent = data.total_users || 0;
                document.getElementById('messages').textContent = data.total_messages || 0;
                document.getElementById('conspects').textContent = data.conspects_created || 0;
                document.getElementById('searches').textContent = data.google_searches || 0;
                
                const timeElement = document.getElementById('time');
                if (timeElement) {
                    timeElement.textContent = new Date().toLocaleTimeString();
                }
            } catch (error) {
                console.log('Ошибка загрузки статистики:', error);
            }
        }
        
        // Первоначальная загрузка
        updateStats();
        
        // Обновление каждые 5 секунд
        setInterval(updateStats, 5000);
    </script>
</body>
</html>
"""

# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================
def main():
    """Главная функция запуска"""
    logger.info(f"🌐 Внешний URL: {RENDER_EXTERNAL_URL or 'Не настроен'}")
    logger.info(f"🚪 Порт: {PORT}")
    logger.info(f"🔑 Telegram Token: {'Установлен' if TELEGRAM_TOKEN else 'НЕТ!'}")
    logger.info(f"🔑 Google API Key: {'Установлен' if GOOGLE_API_KEY else 'НЕТ!'}")
    logger.info(f"🆔 Google CSE ID: {GOOGLE_CSE_ID}")
    logger.info("=" * 60)
    
    # Запускаем HTTP сервер
    server = HTTPServer(('', PORT), BotHTTPServer)
    
    logger.info(f"✅ HTTP сервер запущен на порту {PORT}")
    logger.info(f"✅ Статусная страница: http://localhost:{PORT}")
    
    if RENDER_EXTERNAL_URL:
        logger.info(f"✅ Вебхук Telegram: {RENDER_EXTERNAL_URL}/webhook")
    
    logger.info("✅ Бот готов к работе!")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("⏹️ Сервер остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка сервера: {e}")

if __name__ == "__main__":
    main()
