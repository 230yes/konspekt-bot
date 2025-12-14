#!/usr/bin/env python3
"""
Konspekt Helper Bot - Упрощенная рабочая версия
Бот ищет информацию и создает конспекты
"""

import os
import logging
import json
import requests
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import re

# ==================== НАСТРОЙКА ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "13aac457275834df9")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")
PORT = int(os.getenv("PORT", 10000))

if not TELEGRAM_TOKEN:
    logger.error("❌ TELEGRAM_TOKEN не установлен!")
    exit(1)

# ==================== СТАТИСТИКА ====================
stats = {
    "total_users": 0,
    "total_messages": 0,
    "conspects_created": 0,
    "google_searches": 0,
    "start_time": datetime.now().isoformat(),
    "user_states": {}
}

# ==================== БАЗА ЗНАНИЙ ====================
KNOWLEDGE_BASE = {
    "искусственный интеллект": [
        "Искусственный интеллект (ИИ) — область компьютерных наук, создающая интеллектуальные машины",
        "Основные направления: машинное обучение, обработка естественного языка, компьютерное зрение",
        "ИИ применяется в медицине, финансах, транспорте, образовании",
        "Этические вопросы ИИ: приватность данных, предвзятость алгоритмов, влияние на рабочие места"
    ],
    "квантовая физика": [
        "Квантовая физика изучает поведение частиц на атомном и субатомном уровнях",
        "Основные принципы: суперпозиция, запутанность, принцип неопределенности",
        "Квантовые компьютеры используют кубиты и решают задачи быстрее классических",
        "Применения: лазеры, транзисторы, медицинская визуализация"
    ],
    "древний рим": [
        "Древний Рим существовал с 753 г. до н.э. по 476 г. н.э.",
        "Римское право стало основой многих современных правовых систем",
        "Колизей вмещал до 50 000 зрителей для гладиаторских боев",
        "Римские акведуки и дороги — инженерные достижения античности"
    ],
    "блокчейн": [
        "Блокчейн — распределенная база данных в виде цепочки блоков",
        "Каждый блок содержит хеш предыдущего блока, обеспечивая неизменность",
        "Биткойн — первая криптовалюта на основе блокчейна",
        "Смарт-контракты автоматически исполняют условия соглашений"
    ],
    "генная инженерия": [
        "Генная инженерия изменяет геном организмов для практических целей",
        "CRISPR-Cas9 — технология точного редактирования генов",
        "Применения: создание ГМО, генотерапия, производство инсулина",
        "Этические вопросы: безопасность, последствия для экосистем"
    ]
}

# ==================== ПОИСК ====================
class GoogleSearch:
    def __init__(self):
        self.api_key = GOOGLE_API_KEY
        self.cse_id = GOOGLE_CSE_ID
        self.base_url = "https://www.googleapis.com/customsearch/v1"
    
    def search(self, query):
        """Выполняет поиск в Google"""
        if not self.api_key:
            logger.warning("API ключ не установлен, использую базу знаний")
            return None
        
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "num": 5,
            "hl": "ru",
            "lr": "lang_ru"
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                stats["google_searches"] += 1
                return data.get("items", [])
            else:
                logger.error(f"Ошибка API: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return None
    
    def get_information(self, query):
        """Получает информацию по запросу"""
        # Сначала пытаемся получить из базы знаний
        query_lower = query.lower()
        for topic, facts in KNOWLEDGE_BASE.items():
            if topic in query_lower:
                return {
                    "source": "knowledge_base",
                    "facts": facts,
                    "topic": topic
                }
        
        # Пытаемся поискать в Google
        items = self.search(query)
        
        if items:
            facts = []
            for item in items[:3]:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                
                # Очищаем текст
                text = f"{title}. {snippet}"
                text = re.sub(r'\.\.\.', '', text)
                text = re.sub(r'\s+', ' ', text).strip()
                
                if len(text) > 30:
                    facts.append(text[:200])
            
            if facts:
                return {
                    "source": "google_search",
                    "facts": facts,
                    "topic": query
                }
        
        # Если ничего не нашли, возвращаем общую информацию
        return {
            "source": "general",
            "facts": [
                f"Тема '{query}' представляет интерес для изучения",
                "Рекомендуется обратиться к специализированным источникам",
                "Для получения информации проверьте формулировку запроса"
            ],
            "topic": query
        }

# ==================== ГЕНЕРАТОР КОНСПЕКТОВ ====================
class ConspectGenerator:
    def __init__(self):
        self.searcher = GoogleSearch()
    
    def generate(self, topic, volume="medium"):
        """Генерирует конспект"""
        info = self.searcher.get_information(topic)
        
        if volume == "short":
            return self._generate_short(info)
        elif volume == "detailed":
            return self._generate_detailed(info)
        else:
            return self._generate_medium(info)
    
    def _generate_short(self, info):
        """Краткий конспект"""
        conspect = f"📌 *{info['topic'].upper()}*\n\n"
        
        if info["source"] == "knowledge_base":
            conspect += "📚 *Источник:* База знаний\n\n"
        elif info["source"] == "google_search":
            conspect += "🔍 *Источник:* Поиск Google\n\n"
        
        for i, fact in enumerate(info["facts"][:3], 1):
            conspect += f"{i}. {fact}\n"
        
        conspect += f"\n🤖 @Konspekt_help_bot"
        return conspect
    
    def _generate_medium(self, info):
        """Средний конспект"""
        conspect = f"📚 *{info['topic'].upper()}*\n\n"
        
        if info["source"] == "knowledge_base":
            conspect += "📚 *Источник:* Локальная база знаний\n\n"
        elif info["source"] == "google_search":
            conspect += "🔍 *Источник:* Поиск в интернете\n\n"
        else:
            conspect += "💡 *Источник:* Общие знания\n\n"
        
        conspect += "🎯 *Основная информация:*\n\n"
        for i, fact in enumerate(info["facts"], 1):
            conspect += f"{i}. {fact}\n"
        
        # Добавляем рекомендации
        conspect += "\n💡 *Рекомендации:*\n"
        conspect += "• Изучите дополнительные источники\n"
        conspect += "• Проверьте актуальность информации\n"
        conspect += "• Обратите внимание на ключевые термины\n"
        
        conspect += f"\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        conspect += f"\n🤖 @Konspekt_help_bot"
        
        return conspect
    
    def _generate_detailed(self, info):
        """Подробный конспект"""
        conspect = f"🔬 *ДЕТАЛЬНЫЙ АНАЛИЗ: {info['topic'].upper()}*\n\n"
        
        # Методология
        conspect += "=" * 40 + "\n"
        conspect += "МЕТОДОЛОГИЯ ИССЛЕДОВАНИЯ\n"
        conspect += "=" * 40 + "\n\n"
        
        if info["source"] == "knowledge_base":
            conspect += "*Источник данных:* Локальная база знаний\n"
        elif info["source"] == "google_search":
            conspect += "*Источник данных:* Поиск Google Custom Search\n"
        else:
            conspect += "*Источник данных:* Обобщенная информация\n"
        
        conspect += f"*Время анализа:* {datetime.now().strftime('%H:%M')}\n"
        conspect += f"*Объем данных:* {len(info['facts'])} пунктов\n\n"
        
        # Основная информация
        conspect += "=" * 40 + "\n"
        conspect += "АНАЛИЗ ИНФОРМАЦИИ\n"
        conspect += "=" * 40 + "\n\n"
        
        for i, fact in enumerate(info["facts"], 1):
            conspect += f"**{i}. {fact}**\n\n"
        
        # Выводы
        conspect += "=" * 40 + "\n"
        conspect += "ВЫВОДЫ И РЕКОМЕНДАЦИИ\n"
        conspect += "=" * 40 + "\n\n"
        
        conspect += "На основе анализа можно сделать следующие выводы:\n\n"
        conspect += "1. Тема требует систематического подхода к изучению\n"
        conspect += "2. Рекомендуется использовать различные источники\n"
        conspect += "3. Важно проверять актуальность и достоверность данных\n"
        conspect += "4. Для углубленного изучения нужны специализированные материалы\n\n"
        
        # План изучения
        conspect += "*ПЛАН ИЗУЧЕНИЯ ТЕМЫ:*\n\n"
        conspect += "1. Ознакомьтесь с основными понятиями и определениями\n"
        conspect += "2. Изучите историю развития и ключевые события\n"
        conspect += "3. Проанализируйте современное состояние и тенденции\n"
        conspect += "4. Рассмотрите практическое применение и примеры\n"
        conspect += "5. Изучите дискуссионные вопросы и перспективы\n\n"
        
        # Техническая информация
        conspect += "=" * 40 + "\n"
        conspect += "ТЕХНИЧЕСКАЯ ИНФОРМАЦИЯ\n"
        conspect += "=" * 40 + "\n\n"
        
        conspect += f"*Дата анализа:* {datetime.now().strftime('%d.%m.%Y')}\n"
        conspect += "*Система:* Konspekt Helper Bot\n"
        conspect += "*Версия:* Упрощенная рабочая\n"
        conspect += "*Статус:* Оперативный\n\n"
        
        conspect += "⚠️ *Примечание:* Информация носит ознакомительный характер"
        
        return conspect

# ==================== TELEGRAM BOT ====================
class TelegramBot:
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.bot_url = f"https://api.telegram.org/bot{self.token}"
        self.generator = ConspectGenerator()
        
        if RENDER_EXTERNAL_URL:
            self._setup_webhook()
        
        logger.info("✅ Telegram бот инициализирован")
    
    def _setup_webhook(self):
        """Настраивает вебхук"""
        webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
        try:
            response = requests.post(
                f"{self.bot_url}/setWebhook",
                json={"url": webhook_url},
                timeout=5
            )
            if response.json().get("ok"):
                logger.info(f"✅ Вебхук установлен: {webhook_url}")
        except Exception as e:
            logger.error(f"❌ Ошибка вебхука: {e}")
    
    def send_message(self, chat_id, text):
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
            return response.json()
        except Exception as e:
            logger.error(f"❌ Ошибка отправки: {e}")
            return None
    
    def process_message(self, chat_id, text):
        """Обрабатывает входящее сообщение"""
        text = text.strip()
        self._update_stats(chat_id)
        
        # Команды
        if text == "/start":
            return self._handle_start(chat_id)
        elif text == "/help":
            return self._handle_help(chat_id)
        elif text == "/stats":
            return self._handle_stats(chat_id)
        
        # Выбор уровня
        if text in ["1", "2", "3"]:
            return self._handle_volume(chat_id, text)
        
        # Тема для анализа
        return self._handle_topic(chat_id, text)
    
    def _handle_start(self, chat_id):
        """Обрабатывает команду /start"""
        welcome = (
            "🤖 *Добро пожаловать в Konspekt Helper Bot!*\n\n"
            "Я помогу вам создать структурированные конспекты по любым темам.\n\n"
            "📌 *Как использовать:*\n"
            "1. Напишите тему для изучения\n"
            "2. Выберите уровень детализации (1, 2 или 3)\n"
            "3. Получите готовый конспект\n\n"
            "📊 *Уровни анализа:*\n"
            "• 1 — Краткий обзор (основные тезисы)\n"
            "• 2 — Стандартный конспект (структурированная информация)\n"
            "• 3 — Детальный анализ (полное исследование)\n\n"
            "🚀 *Начните с любой темы, например:*\n"
            "• Искусственный интеллект\n"
            "• Квантовая физика\n"
            "• Древний Рим\n"
            "• Блокчейн технологии"
        )
        return self.send_message(chat_id, welcome)
    
    def _handle_help(self, chat_id):
        """Обрабатывает команду /help"""
        help_text = (
            "📚 *Konspekt Helper Bot - Помощь*\n\n"
            "*Основные команды:*\n"
            "/start - Начало работы с ботом\n"
            "/help - Эта справка\n"
            "/stats - Статистика работы бота\n\n"
            "*Как работать:*\n"
            "1. Отправьте тему для анализа\n"
            "2. Выберите уровень 1, 2 или 3\n"
            "3. Получите конспект\n\n"
            "*Примеры запросов:*\n"
            "• 'История Древнего Рима'\n"
            "• 'Искусственный интеллект в медицине'\n"
            "• 'Квантовая механика основы'\n"
            "• 'Экономика Китая'\n\n"
            "🤖 Бот использует поиск Google и локальную базу знаний"
        )
        return self.send_message(chat_id, help_text)
    
    def _handle_stats(self, chat_id):
        """Обрабатывает команду /stats"""
        stat_text = (
            f"📊 *Статистика бота:*\n\n"
            f"👥 Пользователей: {stats['total_users']}\n"
            f"💬 Сообщений: {stats['total_messages']}\n"
            f"📄 Конспектов создано: {stats['conspects_created']}\n"
            f"🔍 Поисковых запросов: {stats['google_searches']}\n"
            f"⏱ Работает с: {stats['start_time'][:10]}\n\n"
            f"📌 *Текущий статус:* Оперативный"
        )
        return self.send_message(chat_id, stat_text)
    
    def _handle_topic(self, chat_id, topic):
        """Обрабатывает ввод темы"""
        user_id = str(chat_id)
        if user_id not in stats["user_states"]:
            stats["user_states"][user_id] = {}
        
        stats["user_states"][user_id]["pending_topic"] = topic
        
        response = (
            f"🎯 *Тема принята: {topic}*\n\n"
            f"Теперь выберите уровень детализации:\n\n"
            f"1️⃣ *КРАТКИЙ ОБЗОР*\nОсновные тезисы и ключевые моменты\n\n"
            f"2️⃣ *СТАНДАРТНЫЙ КОНСПЕКТ*\nСтруктурированная информация с разделами\n\n"
            f"3️⃣ *ДЕТАЛЬНЫЙ АНАЛИЗ*\nПолное исследование с методологией и выводами\n\n"
            f"📌 *Отправьте цифру 1, 2 или 3*"
        )
        return self.send_message(chat_id, response)
    
    def _handle_volume(self, chat_id, volume_choice):
        """Обрабатывает выбор уровня"""
        user_id = str(chat_id)
        user_state = stats["user_states"].get(user_id, {})
        topic = user_state.get("pending_topic", "")
        
        if not topic:
            return self.send_message(chat_id, "❌ Сначала отправьте тему для анализа")
        
        # Определяем уровень
        volume_map = {
            "1": "short",
            "2": "medium", 
            "3": "detailed"
        }
        volume = volume_map.get(volume_choice, "medium")
        
        # Отправляем уведомление о начале работы
        self.send_message(chat_id, f"🔍 *Анализирую тему:* {topic}\n📊 *Уровень:* {volume_choice}/3\n⏳ *Подождите...*")
        
        try:
            # Генерируем конспект
            conspect = self.generator.generate(topic, volume)
            stats["conspects_created"] += 1
            
            # Отправляем конспект
            self._send_conspect(chat_id, conspect)
            
            # Отправляем завершающее сообщение
            finish_msg = (
                f"✅ *Анализ завершен!*\n\n"
                f"📌 Тема: {topic}\n"
                f"📊 Уровень анализа: {volume_choice}/3\n\n"
                f"🔄 Хотите другой уровень? Отправьте 1, 2 или 3\n"
                f"🎯 Новая тема? Просто напишите её!"
            )
            return self.send_message(chat_id, finish_msg)
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации: {e}")
            return self.send_message(
                chat_id,
                f"❌ *Ошибка при создании конспекта*\n\n"
                f"Попробуйте:\n"
                f"1. Другую формулировку темы\n"
                f"2. Более простой запрос\n"
                f"3. Повторить попытку позже"
            )
    
    def _send_conspect(self, chat_id, conspect):
        """Отправляет конспект"""
        # Telegram имеет ограничение 4096 символов на сообщение
        if len(conspect) <= 4096:
            self.send_message(chat_id, conspect)
            return
        
        # Если конспект слишком длинный, разбиваем на части
        parts = []
        current_part = ""
        
        # Разбиваем по разделам
        sections = re.split(r'(=+\n)', conspect)
        
        for section in sections:
            if len(current_part + section) > 4000 and current_part:
                parts.append(current_part)
                current_part = section
            else:
                current_part += section
        
        if current_part:
            parts.append(current_part)
        
        # Отправляем все части
        for i, part in enumerate(parts, 1):
            if i > 1:
                part = f"📖 *Продолжение ({i}/{len(parts)})*\n\n{part}"
            self.send_message(chat_id, part)
    
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

# ==================== HTTP СЕРВЕР ====================
class BotHTTPServer(BaseHTTPRequestHandler):
    def do_GET(self):
        """Обрабатывает GET запросы"""
        if self.path == "/":
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            # ИСПРАВЛЕНО: используем encode() для русских символов
            self.wfile.write('<h1>Бот-помощник Konspekt работает!</h1>'.encode('utf-8'))
        elif self.path == "/health":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = json.dumps({"status": "ok", "time": datetime.now().isoformat()})
            self.wfile.write(response.encode('utf-8'))
        elif self.path == "/stats":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = json.dumps(stats, ensure_ascii=False, indent=2)
            self.wfile.write(response.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Обрабатывает POST запросы (вебхук от Telegram)"""
        if self.path == "/webhook":
            content_length = int(self.headers.get('Content-Length', 0))
            
            if content_length:
                try:
                    data = self.rfile.read(content_length)
                    update = json.loads(data.decode('utf-8'))
                    
                    # Обрабатываем в отдельном потоке
                    threading.Thread(
                        target=self._process_update,
                        args=(update,),
                        daemon=True
                    ).start()
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка вебхука: {e}")
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def _process_update(self, update):
        """Обрабатывает обновление от Telegram"""
        try:
            if "message" in update and "text" in update["message"]:
                message = update["message"]
                chat_id = message["chat"]["id"]
                text = message["text"]
                
                bot = TelegramBot()
                bot.process_message(chat_id, text)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
    
    def log_message(self, format, *args):
        """Отключаем логирование запросов"""
        pass

# ==================== ЗАПУСК ====================
def main():
    """Запускает сервер"""
    logger.info("=" * 50)
    logger.info("🚀 ЗАПУСК KONSPEKT HELPER BOT")
    logger.info("=" * 50)
    logger.info(f"🌐 Внешний URL: {RENDER_EXTERNAL_URL}")
    logger.info(f"🚪 Порт: {PORT}")
    logger.info(f"🔑 Google API: {'✅' if GOOGLE_API_KEY else '❌'}")
    logger.info(f"🤖 Telegram токен: {'✅' if TELEGRAM_TOKEN else '❌'}")
    logger.info("=" * 50)
    
    if not GOOGLE_API_KEY:
        logger.info("⚠️  GOOGLE_API_KEY не установлен")
        logger.info("⚠️  Бот будет использовать только локальную базу знаний")
    
    # Создаем и запускаем сервер
    server = HTTPServer(('', PORT), BotHTTPServer)
    logger.info(f"✅ HTTP сервер запущен на порту {PORT}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("⏹️  Сервер остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка сервера: {e}")

if __name__ == "__main__":
    main()
