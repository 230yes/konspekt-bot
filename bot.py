#!/usr/bin/env python3
"""
Умный Konspekt Helper Bot - ТОЛЬКО ФАКТЫ
Бот анализирует информацию и присылает только суть по запросу
"""

import os
import logging
import json
import requests
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import random
import re
import html

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

# ==================== УМНЫЙ АНАЛИЗАТОР ИНФОРМАЦИИ ====================
class InformationAnalyzer:
    """Анализирует и структурирует информацию - ТОЛЬКО ФАКТЫ"""
    
    def analyze_topic(self, query, search_results):
        """Анализирует тему - берем только реальные данные"""
        # Определяем тип темы
        topic_type = self._determine_topic_type(query)
        
        # Анализируем результаты
        analysis = self._analyze_search_results(search_results, query)
        
        return {
            "topic": query,
            "type": topic_type,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
    
    def _determine_topic_type(self, query):
        """Определяет тип темы"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["история", "война", "революция", "древний"]):
            return "историческая"
        elif any(word in query_lower for word in ["технология", "программирование", "компьютер", "искусственный интеллект"]):
            return "технологическая"
        elif any(word in query_lower for word in ["медицина", "здоровье", "болезнь", "лечение"]):
            return "медицинская"
        elif any(word in query_lower for word in ["экономика", "финансы", "рынок", "бизнес"]):
            return "экономическая"
        elif any(word in query_lower for word in ["наука", "исследование", "теория", "эксперимент"]):
            return "научная"
        return "общая"
    
    def _analyze_search_results(self, results, query):
        """Анализирует результаты поиска - только факты"""
        items = results.get("items", [])
        
        key_points = []
        statistics = []
        definitions = []
        sources = []
        
        for item in items[:8]:  # Берем больше результатов
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            
            # Извлекаем реальные факты
            fact = self._extract_fact(title, snippet, query)
            if fact:
                key_points.append(fact)
                sources.append(link)
            
            # Цифры и статистика
            numbers = self._extract_numbers(title + " " + snippet)
            statistics.extend(numbers)
            
            # Определения
            definition = self._extract_definition(title + " " + snippet)
            if definition:
                definitions.append(definition)
        
        # Термины из найденного
        key_terms = self._extract_terms_from_points(key_points)
        
        return {
            "key_points": key_points[:10],
            "statistics": statistics[:6],
            "definitions": definitions[:4],
            "key_terms": key_terms[:8],
            "total_sources": len(items),
            "sources": sources[:3]
        }
    
    def _extract_fact(self, title, snippet, query):
        """Извлекает факт из текста"""
        text = f"{title}. {snippet}"
        
        # Убираем рекламу и мусор
        if self._is_junk(text):
            return None
        
        # Находим наиболее информативное предложение
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if 30 < len(sentence) < 200:
                # Проверяем релевантность
                if self._is_relevant_fact(sentence, query):
                    # Очищаем от лишнего
                    clean_sentence = re.sub(r'\s+', ' ', sentence)
                    clean_sentence = clean_sentence[:180]
                    return clean_sentence
        
        return None
    
    def _is_junk(self, text):
        """Проверяет, не является ли текст мусором"""
        junk_phrases = [
            "кликните", "нажмите", "подробнее", "читать далее",
            "узнать больше", "реклама", "sponsored", "advertisement",
            "купить", "заказать", "цена", "акция", "скидка"
        ]
        
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in junk_phrases)
    
    def _is_relevant_fact(self, sentence, query):
        """Проверяет релевантность факта"""
        query_words = [word.lower() for word in query.split() if len(word) > 3]
        sentence_lower = sentence.lower()
        
        # Считаем совпадения
        matches = sum(1 for word in query_words if word in sentence_lower)
        
        # Должно быть достаточно длинным и релевантным
        return matches > 0 and len(sentence.split()) > 5
    
    def _extract_numbers(self, text):
        """Извлекает числа и статистику"""
        patterns = [
            r'\d+\.?\d*%',  # Проценты
            r'\d+\.?\d*\s*(?:млн|млрд|тыс)',  # С числами
            r'\$\d+\.?\d*',  # Доллары
            r'\d+\.?\d*\s*(?:долларов|рублей|евро)'
        ]
        
        numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            numbers.extend(matches)
        
        return list(set(numbers))[:5]
    
    def _extract_definition(self, text):
        """Извлекает определения"""
        patterns = [
            r'это\s+[^.!?]{10,100}[.!?]',
            r'является\s+[^.!?]{10,100}[.!?]',
            r'определяется\s+как\s+[^.!?]{10,100}[.!?]',
            r'под\s+[^.!?]{5,20}\s+понимают\s+[^.!?]{10,100}[.!?]'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                definition = match.group(0).strip()
                if 30 < len(definition) < 150:
                    return definition[:120] + "..."
        
        return None
    
    def _extract_terms_from_points(self, key_points):
        """Извлекает термины из ключевых точек"""
        all_text = " ".join(key_points)
        words = re.findall(r'\b[а-яё]{4,}\b', all_text.lower())
        
        # Убираем стоп-слова
        stop_words = {"этот", "такой", "какой", "который", "очень", "может", "будет"}
        freq = {}
        
        for word in words:
            if word not in stop_words:
                freq[word] = freq.get(word, 0) + 1
        
        # Берем наиболее частые
        sorted_terms = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [term.capitalize() for term, count in sorted_terms[:12]]

# ==================== УМНЫЙ ПОИСК ====================
class SmartGoogleSearch:
    def __init__(self):
        self.api_key = GOOGLE_API_KEY
        self.cse_id = GOOGLE_CSE_ID
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.analyzer = InformationAnalyzer()
        
    def search_and_analyze(self, query):
        """Выполняет поиск и возвращает только факты"""
        if not query or len(query.strip()) < 2:
            return {"error": "Короткий запрос"}
        
        stats["google_searches"] += 1
        
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "num": 8,
            "hl": "ru",
            "lr": "lang_ru",
            "gl": "ru"
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=15)
            
            if response.status_code != 200:
                return self._create_fallback(query)
            
            data = response.json()
            
            # Анализируем только факты
            structured_info = self.analyzer.analyze_topic(query, data)
            
            return {
                "success": True,
                "query": query,
                "structured_info": structured_info,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return self._create_fallback(query)
    
    def _create_fallback(self, query):
        """Минимальный fallback"""
        return {
            "success": False,
            "query": query,
            "structured_info": {
                "topic": query,
                "type": "общая",
                "analysis": {
                    "key_points": [f"Информация по теме '{query}' требует дополнительного изучения"],
                    "statistics": [],
                    "definitions": [],
                    "key_terms": [query.capitalize()],
                    "total_sources": 0,
                    "sources": []
                }
            },
            "fallback": True
        }

# ==================== ГЕНЕРАТОР КОНСПЕКТОВ - ТОЛЬКО ФАКТЫ ====================
class SmartConspectGenerator:
    def __init__(self):
        self.searcher = SmartGoogleSearch()
        logger.info("✅ Генератор готов - только факты")
    
    def generate(self, topic, volume="short"):
        """Генерирует конспект - только факты"""
        # Пасхалка
        if self._is_easter_egg(topic):
            return self._create_easter_egg_response()
        
        # Поиск и анализ
        search_results = self.searcher.search_and_analyze(topic)
        structured_info = search_results.get("structured_info", {})
        analysis = structured_info.get("analysis", {})
        
        # В зависимости от объема
        if volume == "detailed":
            return self._generate_detailed(topic, analysis)
        elif volume == "extended":
            return self._generate_extended(topic, analysis)
        else:
            return self._generate_short(topic, analysis)
    
    def _is_easter_egg(self, text):
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in [
            "план захвата польши", "захват польши", "чайная пасхалка"
        ])
    
    def _create_easter_egg_response(self):
        return "🍵 *Пасхалка!* Чайные церемонии изучаются в культурологии."
    
    def _generate_short(self, topic, analysis):
        """Кратко - только самое важное"""
        key_points = analysis.get("key_points", [])
        
        if not key_points:
            return f"📌 *{topic}*\n\nИнформация не найдена"
        
        conspect = f"📌 *{topic}*\n\n"
        
        # Только ключевые точки
        for i, point in enumerate(key_points[:4], 1):
            conspect += f"• {point}\n"
        
        # Одна статистика если есть
        statistics = analysis.get("statistics", [])
        if statistics:
            conspect += f"\n📊 {statistics[0]}\n"
        
        # Ключевые термины если есть
        terms = analysis.get("key_terms", [])
        if terms:
            conspect += f"🔑 {', '.join(terms[:3])}\n"
        
        return conspect
    
    def _generate_detailed(self, topic, analysis):
        """Подробно - факты + данные"""
        key_points = analysis.get("key_points", [])
        
        if not key_points:
            return f"📚 *{topic}*\n\nИнформация не найдена"
        
        conspect = f"📚 *{topic}*\n\n"
        
        # Все ключевые точки
        for i, point in enumerate(key_points[:8], 1):
            conspect += f"{i}. {point}\n"
        
        # Статистика
        statistics = analysis.get("statistics", [])
        if statistics:
            conspect += f"\n📊 *Данные:*\n"
            for stat in statistics[:4]:
                conspect += f"• {stat}\n"
        
        # Определения
        definitions = analysis.get("definitions", [])
        if definitions:
            conspect += f"\n📖 *Определения:*\n"
            for definition in definitions[:3]:
                conspect += f"• {definition}\n"
        
        # Термины
        terms = analysis.get("key_terms", [])
        if terms:
            conspect += f"\n🔑 *Термины:* {', '.join(terms[:6])}\n"
        
        # Источники
        sources = analysis.get("sources", [])
        if sources:
            conspect += f"\n🔍 Источников: {analysis.get('total_sources', 0)}"
        
        return conspect
    
    def _generate_extended(self, topic, analysis):
        """Полно - все факты"""
        key_points = analysis.get("key_points", [])
        
        if not key_points:
            return f"🔬 *{topic}*\n\nИнформация не найдена"
        
        conspect = f"🔬 *{topic}*\n\n"
        
        # Все ключевые точки
        for i, point in enumerate(key_points, 1):
            conspect += f"{i}. {point}\n"
        
        # Все статистики
        statistics = analysis.get("statistics", [])
        if statistics:
            conspect += f"\n📊 *Статистика и цифры:*\n\n"
            for stat in statistics:
                conspect += f"• {stat}\n"
        
        # Все определения
        definitions = analysis.get("definitions", [])
        if definitions:
            conspect += f"\n📖 *Определения и понятия:*\n\n"
            for definition in definitions:
                conspect += f"• {definition}\n"
        
        # Все термины
        terms = analysis.get("key_terms", [])
        if terms:
            conspect += f"\n🔤 *Ключевая терминология:*\n\n"
            for i, term in enumerate(terms[:10], 1):
                conspect += f"{i}. {term}\n"
        
        # Информация о поиске
        conspect += f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
        conspect += f"📈 Найдено фактов: {len(key_points)}\n"
        conspect += f"🔍 Источников: {analysis.get('total_sources', 0)}\n"
        conspect += f"🕒 {datetime.now().strftime('%H:%M')}"
        
        return conspect

# ==================== TELEGRAM BOT ====================
class TelegramBot:
    def __init__(self):
        if not TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN не найден")
        
        self.token = TELEGRAM_TOKEN
        self.bot_url = f"https://api.telegram.org/bot{self.token}"
        self.generator = SmartConspectGenerator()
        
        if RENDER_EXTERNAL_URL:
            self._setup_webhook()
        
        logger.info("✅ Telegram бот готов - только факты")
    
    def _setup_webhook(self):
        webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
        try:
            response = requests.post(
                f"{self.bot_url}/setWebhook",
                json={"url": webhook_url},
                timeout=10
            )
            if response.json().get("ok"):
                logger.info(f"✅ Вебхук: {webhook_url}")
        except Exception as e:
            logger.error(f"❌ Ошибка вебхука: {e}")
    
    def process_message(self, chat_id, text):
        text = text.strip()
        self._update_stats(chat_id)
        
        if text.startswith("/"):
            if text == "/start":
                return self._send_welcome(chat_id)
            elif text == "/help":
                return self._send_help(chat_id)
            elif text == "/stats":
                return self._send_stats(chat_id)
            else:
                return self._send_message(chat_id, "❓ Неизвестная команда")
        
        if text in ["1", "2", "3"]:
            return self._handle_volume(chat_id, text)
        
        return self._handle_topic(chat_id, text)
    
    def _send_welcome(self, chat_id):
        welcome = (
            "🤖 *Бот для анализа информации*\n\n"
            "📌 Отправьте тему → Получите факты\n\n"
            "📊 *Уровни:*\n"
            "• 1 — Основные тезисы\n"
            "• 2 — Факты + данные\n"
            "• 3 — Вся информация\n\n"
            "🚀 Просто напишите тему"
        )
        return self._send_message(chat_id, welcome)
    
    def _send_help(self, chat_id):
        help_text = (
            "📌 *Как работает:*\n"
            "1. Пишете тему\n"
            "2. Выбираете 1, 2 или 3\n"
            "3. Получаете информацию\n\n"
            "🎯 *Примеры:*\n"
            "• Искусственный интеллект\n"
            "• История Рима\n"
            "• Квантовая физика\n"
            "• Экономика Китая\n\n"
            "🤖 Бот ищет факты и присылает их"
        )
        return self._send_message(chat_id, help_text)
    
    def _send_stats(self, chat_id):
        stat_text = (
            f"📊 *Статистика:*\n\n"
            f"👥 Пользователей: {stats['total_users']}\n"
            f"💬 Сообщений: {stats['total_messages']}\n"
            f"📄 Конспектов: {stats['conspects_created']}\n"
            f"🔍 Поисков: {stats['google_searches']}"
        )
        return self._send_message(chat_id, stat_text)
    
    def _handle_topic(self, chat_id, topic):
        user_id = str(chat_id)
        if user_id not in stats["user_states"]:
            stats["user_states"][user_id] = {}
        
        stats["user_states"][user_id]["pending_topic"] = topic
        
        response = (
            f"🎯 *Тема: {topic}*\n\n"
            f"📊 Уровень информации:\n\n"
            f"1️⃣ Краткие тезисы\n"
            f"2️⃣ Факты + данные\n"
            f"3️⃣ Полная информация\n\n"
            f"Отправьте 1, 2 или 3"
        )
        return self._send_message(chat_id, response)
    
    def _handle_volume(self, chat_id, volume_choice):
        user_id = str(chat_id)
        user_state = stats["user_states"].get(user_id, {})
        topic = user_state.get("pending_topic", "")
        
        if not topic:
            return self._send_message(chat_id, "❌ Сначала отправьте тему")
        
        volume_map = {"1": "short", "2": "detailed", "3": "extended"}
        volume = volume_map.get(volume_choice, "short")
        
        # Минимальное уведомление
        self._send_message(chat_id, f"🔍 Ищу информацию...")
        
        try:
            conspect = self.generator.generate(topic, volume)
            stats["conspects_created"] += 1
            
            # Отправляем
            self._send_conspect_safely(chat_id, conspect)
            
            # Короткое завершение
            return self._send_message(chat_id, "✅ Готово! Новая тема?")
            
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return self._send_message(
                chat_id,
                f"❌ Ошибка поиска\nПопробуйте другую формулировку"
            )
    
    def _send_conspect_safely(self, chat_id, conspect):
        """Безопасно отправляет конспект"""
        max_length = 4000
        
        if len(conspect) <= max_length:
            self._send_message(chat_id, conspect)
            return
        
        # Разбиваем по абзацам
        paragraphs = conspect.split('\n\n')
        
        current = ""
        for para in paragraphs:
            if len(current + para) > max_length and current:
                self._send_message(chat_id, current.strip())
                current = para
            else:
                if current:
                    current += "\n\n" + para
                else:
                    current = para
        
        if current.strip():
            self._send_message(chat_id, current.strip())
    
    def _update_stats(self, chat_id):
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
        try:
            response = requests.post(
                f"{self.bot_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True
                },
                timeout=15
            )
            return response.json().get("ok", False)
        except Exception as e:
            logger.error(f"❌ Ошибка отправки: {e}")
            return False

# ==================== HTTP СЕРВЕР ====================
class BotHTTPServer(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]
        
        if path == "/":
            self._send_html(INDEX_HTML)
        elif path == "/health":
            self._send_json({"status": "ok", "time": datetime.now().isoformat()})
        elif path == "/stats":
            self._send_json(stats)
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == "/webhook":
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length:
                try:
                    data = self.rfile.read(content_length)
                    update = json.loads(data.decode('utf-8'))
                    
                    threading.Thread(
                        target=self._handle_update,
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
    
    def _handle_update(self, update):
        try:
            if "message" in update and "text" in update["message"]:
                chat_id = update["message"]["chat"]["id"]
                text = update["message"]["text"]
                
                bot = TelegramBot()
                bot.process_message(chat_id, text)
        except Exception as e:
            logger.error(f"❌ Ошибка обработки: {e}")
    
    def _send_html(self, content):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))
    
    def _send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))
    
    def log_message(self, format, *args):
        pass

INDEX_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>🤖 Бот для анализа информации</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f0f2f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        .status { color: green; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🤖 Бот для анализа информации</h2>
        <p class="status">✅ Работает</p>
        <p>Отправляет только факты по запросу</p>
        
        <h3>📊 Статистика:</h3>
        <div id="stats">Загрузка...</div>
        
        <h3>🔗 Ссылки:</h3>
        <p><a href="https://t.me/Konspekt_help_bot" target="_blank">🤖 Открыть бота</a></p>
        <p><a href="/stats" target="_blank">📈 JSON статистика</a></p>
        
        <p style="color: #666; margin-top: 20px;">
            Обновлено: <span id="time"></span>
        </p>
    </div>
    
    <script>
        async function loadStats() {
            try {
                const response = await fetch('/stats');
                const data = await response.json();
                
                document.getElementById('stats').innerHTML = `
                    <p>Пользователей: ${data.total_users || 0}</p>
                    <p>Сообщений: ${data.total_messages || 0}</p>
                    <p>Конспектов: ${data.conspects_created || 0}</p>
                    <p>Поисков: ${data.google_searches || 0}</p>
                `;
                
                document.getElementById('time').textContent = new Date().toLocaleTimeString();
            } catch (error) {
                document.getElementById('stats').innerHTML = 'Ошибка загрузки';
            }
        }
        
        loadStats();
        setInterval(loadStats, 10000);
    </script>
</body>
</html>
"""

# ==================== ЗАПУСК ====================
def main():
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК БОТА - ТОЛЬКО ФАКТЫ")
    logger.info("=" * 60)
    logger.info(f"🌐 URL: {RENDER_EXTERNAL_URL}")
    logger.info(f"🚪 Порт: {PORT}")
    logger.info("✅ Режим: Факты без шаблонов")
    logger.info("=" * 60)
    
    server = HTTPServer(('', PORT), BotHTTPServer)
    logger.info(f"✅ HTTP сервер запущен на порту {PORT}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("⏹️ Сервер остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
