#!/usr/bin/env python3
"""
Улучшенный Konspekt Helper Bot с исправлением API поиска
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

# Проверяем наличие API ключа
if not GOOGLE_API_KEY:
    logger.warning("⚠️ GOOGLE_API_KEY не установлен! Будет использоваться ограниченный режим")

# ==================== СТАТИСТИКА ====================
stats = {
    "total_users": 0,
    "total_messages": 0,
    "conspects_created": 0,
    "google_searches": 0,
    "api_errors": 0,
    "fallback_mode": 0,
    "start_time": datetime.now().isoformat(),
    "user_states": {}
}

# ==================== БАЗА ЗНАНИЙ ДЛЯ FALLBACK ====================
KNOWLEDGE_BASE = {
    # Научные темы
    "искусственный интеллект": [
        "Искусственный интеллект (ИИ) — область компьютерных наук, занимающаяся созданием машин, способных выполнять задачи, требующие человеческого интеллекта",
        "Основные направления ИИ: машинное обучение, обработка естественного языка, компьютерное зрение",
        "ИИ применяется в медицине, финансах, транспорте, образовании и многих других сферах",
        "Этические вопросы ИИ включают приватность данных, предвзятость алгоритмов и влияние на рабочие места"
    ],
    "квантовая физика": [
        "Квантовая физика — раздел физики, изучающий поведение микрочастиц на квантовом уровне",
        "Основные принципы: квантовая суперпозиция, квантовая запутанность, принцип неопределенности Гейзенберга",
        "Квантовые компьютеры используют кубиты вместо битов и могут решать сложные задачи быстрее классических",
        "Квантовая механика лежит в основе современных технологий: лазеры, транзисторы, МРТ"
    ],
    "генетика": [
        "Генетика — наука о наследственности и изменчивости организмов",
        "ДНК содержит генетическую информацию в виде последовательности нуклеотидов",
        "Генная инженерия позволяет изменять геном организмов для медицинских и сельскохозяйственных целей",
        "CRISPR-Cas9 — революционная технология редактирования генома"
    ],
    
    # Исторические темы
    "древний рим": [
        "Древний Рим существовал с 753 года до н.э. по 476 год н.э.",
        "Римское право стало основой многих современных правовых систем",
        "Римская империя достигла максимальных размеров при императоре Траяне",
        "Колизей — самый большой амфитеатр Древнего Рима, вмещавший до 50000 зрителей"
    ],
    "вторая мировая война": [
        "Вторая мировая война длилась с 1939 по 1945 год",
        "В войне участвовали 62 страны, погибло около 70 миллионов человек",
        "Важнейшие сражения: Сталинградская битва, высадка в Нормандии, битва за Москву",
        "Война завершилась капитуляцией Германии и Японии"
    ],
    
    # Технологические темы
    "блокчейн": [
        "Блокчейн — распределенная база данных, хранящая информацию в виде цепочки блоков",
        "Каждый блок содержит хеш предыдущего блока, что обеспечивает неизменность данных",
        "Блокчейн используется в криптовалютах, смарт-контрактах, системах голосования",
        "Биткойн — первая и самая известная криптовалюта на основе блокчейна"
    ],
    "большие данные": [
        "Большие данные (Big Data) — огромные объемы структурированных и неструктурированных данных",
        "Характеристики больших данных: объем, скорость, разнообразие, достоверность",
        "Технологии обработки: Hadoop, Spark, NoSQL базы данных",
        "Применяются в аналитике, машинном обучении, интернете вещей"
    ],
    
    # Медицинские темы
    "вирус иммунодефицита человека": [
        "ВИЧ — вирус, поражающий иммунную систему человека",
        "Передается через кровь, половым путем и от матери к ребенку",
        "СПИД — терминальная стадия ВИЧ-инфекции",
        "Антиретровирусная терапия позволяет контролировать вирус и продлевать жизнь"
    ],
    "вакцинация": [
        "Вакцинация — введение вакцины для создания иммунитета к заболеванию",
        "Первая вакцина была создана Эдвардом Дженнером против оспы в 1796 году",
        "Вакцины спасают 2-3 миллиона жизней ежегодно",
        "Гердальный иммунитет возникает при вакцинации 70-90% населения"
    ]
}

# ==================== УЛУЧШЕННЫЙ ПОИСК ====================
class SmartGoogleSearch:
    def __init__(self):
        self.api_key = GOOGLE_API_KEY
        self.cse_id = GOOGLE_CSE_ID
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.session = requests.Session()
        self.session.timeout = 20
        
    def search_and_analyze(self, query):
        """Выполняет поиск с улучшенной обработкой ошибок"""
        if not query or len(query.strip()) < 2:
            return {"error": "Слишком короткий запрос"}
        
        stats["google_searches"] += 1
        
        # Проверяем наличие API ключа
        if not self.api_key:
            logger.warning("⚠️ API ключ отсутствует, использую fallback")
            return self._create_fallback_response(query)
        
        try:
            # Пробуем разные параметры поиска
            search_variants = [
                {
                    "key": self.api_key,
                    "cx": self.cse_id,
                    "q": query,
                    "num": 8,
                    "hl": "ru",
                    "lr": "lang_ru",
                    "gl": "ru"
                },
                {
                    "key": self.api_key,
                    "cx": self.cse_id,
                    "q": query + " научные статьи",
                    "num": 6,
                    "hl": "ru"
                },
                {
                    "key": self.api_key,
                    "cx": self.cse_id,
                    "q": query + " исследование",
                    "num": 6,
                    "hl": "ru"
                }
            ]
            
            search_results = []
            
            for params in search_variants:
                try:
                    logger.info(f"🔍 Поиск: {params['q']}")
                    response = self.session.get(self.base_url, params=params, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "items" in data:
                            search_results.extend(data["items"])
                            logger.info(f"✅ Найдено {len(data.get('items', []))} результатов")
                        else:
                            logger.warning("⚠️ В ответе нет items")
                    else:
                        logger.error(f"❌ Ошибка API: {response.status_code}")
                        
                except requests.exceptions.Timeout:
                    logger.error("⏰ Таймаут запроса")
                    continue
                except requests.exceptions.ConnectionError:
                    logger.error("🔌 Ошибка соединения")
                    continue
                except Exception as e:
                    logger.error(f"❌ Ошибка поиска: {e}")
                    continue
            
            if not search_results:
                logger.warning("⚠️ Не найдено результатов, использую fallback")
                return self._create_fallback_response(query)
            
            # Анализируем результаты
            analyzed_data = self._analyze_search_results(search_results, query)
            
            return {
                "success": True,
                "query": query,
                "results": analyzed_data,
                "total_results": len(search_results),
                "timestamp": datetime.now().isoformat(),
                "source": "google_search"
            }
            
        except Exception as e:
            stats["api_errors"] += 1
            logger.error(f"❌ Критическая ошибка поиска: {e}")
            return self._create_fallback_response(query)
    
    def _analyze_search_results(self, items, query):
        """Анализирует результаты поиска"""
        facts = []
        definitions = []
        statistics = []
        
        for item in items[:10]:  # Анализируем первые 10 результатов
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            
            # Извлекаем полезную информацию
            text = f"{title}. {snippet}"
            
            # Ищем факты
            fact = self._extract_fact(text, query)
            if fact:
                facts.append({
                    "text": fact,
                    "source": link,
                    "domain": self._extract_domain(link)
                })
            
            # Ищем определения
            definition = self._extract_definition(text)
            if definition:
                definitions.append(definition)
            
            # Ищем статистику
            stats_data = self._extract_statistics(text)
            statistics.extend(stats_data)
        
        # Убираем дубликаты
        facts = self._remove_duplicates(facts)
        definitions = list(set(definitions))
        statistics = list(set(statistics))
        
        # Извлекаем ключевые термины
        key_terms = self._extract_key_terms(facts, definitions)
        
        return {
            "facts": facts[:8],
            "definitions": definitions[:4],
            "statistics": statistics[:6],
            "key_terms": key_terms[:10],
            "total_facts": len(facts),
            "total_definitions": len(definitions)
        }
    
    def _extract_fact(self, text, query):
        """Извлекает факт из текста"""
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if 30 < len(sentence) < 200:
                # Проверяем релевантность
                query_words = [w.lower() for w in query.split() if len(w) > 3]
                sentence_lower = sentence.lower()
                
                # Считаем совпадения с запросом
                matches = sum(1 for word in query_words if word in sentence_lower)
                
                # Проверяем информативность
                has_numbers = bool(re.search(r'\d+[%‰°]|\d+\.\d+|\d{4}', sentence))
                has_meaning = len(sentence.split()) > 5
                
                if matches > 0 and has_meaning:
                    return sentence[:180]
        
        return None
    
    def _extract_definition(self, text):
        """Извлекает определение"""
        patterns = [
            r'это\s+[^.!?]{10,100}[.!?]',
            r'является\s+[^.!?]{10,100}[.!?]',
            r'определяется\s+как\s+[^.!?]{10,100}[.!?]',
            r'под\s+[^.!?]{5,20}\s+понимают\s+[^.!?]{10,100}[.!?]'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                definition = matches[0].strip()
                if 20 < len(definition) < 150:
                    return definition[:120] + "..."
        
        return None
    
    def _extract_statistics(self, text):
        """Извлекает статистику"""
        patterns = [
            r'\d+\.?\d*%',
            r'\d+\.?\d*\s*(?:млн|млрд|тыс|миллион|миллиард)',
            r'\$\d+\.?\d*',
            r'\d+\.?\d*\s*(?:долларов|рублей|евро)',
            r'\d{4}\s*году?'
        ]
        
        statistics = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            statistics.extend(matches)
        
        return statistics[:5]
    
    def _extract_key_terms(self, facts, definitions):
        """Извлекает ключевые термины"""
        all_text = " ".join([f["text"] for f in facts] + definitions)
        
        # Находим существительные (слова от 4 букв)
        words = re.findall(r'\b[а-яё]{4,}\b', all_text.lower())
        
        # Считаем частоту
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Сортируем по частоте
        sorted_terms = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [term.capitalize() for term, freq in sorted_terms[:15]]
    
    def _extract_domain(self, url):
        """Извлекает домен из URL"""
        if not url:
            return "unknown"
        
        # Упрощенное извлечение домена
        domain = url.split('//')[-1].split('/')[0]
        return domain
    
    def _remove_duplicates(self, facts):
        """Удаляет дублирующиеся факты"""
        seen_texts = set()
        unique_facts = []
        
        for fact in facts:
            text = fact["text"].lower()
            # Упрощаем для сравнения
            simple_text = re.sub(r'[^\w\s]', '', text)
            words = simple_text.split()
            key = " ".join(sorted(set(words))[:10])  # Используем ключевые слова
            
            if key not in seen_texts:
                seen_texts.add(key)
                unique_facts.append(fact)
        
        return unique_facts
    
    def _create_fallback_response(self, query):
        """Создает fallback-ответ при проблемах с API"""
        stats["fallback_mode"] += 1
        
        query_lower = query.lower()
        
        # Ищем в базе знаний
        for topic, facts in KNOWLEDGE_BASE.items():
            if topic in query_lower or any(word in query_lower for word in topic.split()):
                analyzed_data = {
                    "facts": [{"text": fact, "source": "knowledge_base", "domain": "knowledge_base"} 
                             for fact in facts[:6]],
                    "definitions": [facts[0]] if facts else [],
                    "statistics": [],
                    "key_terms": [topic.capitalize()] + [f.split()[0].capitalize() for f in facts[:3]],
                    "total_facts": len(facts[:6]),
                    "total_definitions": 1 if facts else 0
                }
                
                return {
                    "success": True,
                    "query": query,
                    "results": analyzed_data,
                    "total_results": len(facts[:6]),
                    "timestamp": datetime.now().isoformat(),
                    "source": "knowledge_base",
                    "fallback": True
                }
        
        # Если не нашли в базе, создаем общий ответ
        general_facts = [
            f"{query} — важная тема, требующая изучения",
            f"По теме '{query}' существует множество исследований и публикаций",
            f"Рекомендуется обратиться к научным источникам для получения полной информации",
            f"{query} имеет практическое применение в различных областях"
        ]
        
        analyzed_data = {
            "facts": [{"text": fact, "source": "general_knowledge", "domain": "general"} 
                     for fact in general_facts],
            "definitions": [f"{query} — тема, представляющая научный и практический интерес"],
            "statistics": [],
            "key_terms": [query.capitalize(), "Исследование", "Анализ", "Изучение"],
            "total_facts": len(general_facts),
            "total_definitions": 1
        }
        
        return {
            "success": True,
            "query": query,
            "results": analyzed_data,
            "total_results": len(general_facts),
            "timestamp": datetime.now().isoformat(),
            "source": "general_knowledge",
            "fallback": True
        }

# ==================== ГЕНЕРАТОР КОНСПЕКТОВ ====================
class SmartConspectGenerator:
    def __init__(self):
        self.searcher = SmartGoogleSearch()
        logger.info("✅ Генератор конспектов готов")
    
    def generate(self, topic, volume="detailed"):
        """Генерирует конспект"""
        # Пасхалка
        if self._is_easter_egg(topic):
            return self._create_easter_egg_response()
        
        # Выполняем поиск
        logger.info(f"🔍 Начинаю поиск по теме: {topic}")
        search_results = self.searcher.search_and_analyze(topic)
        
        if "error" in search_results:
            return f"❌ *Ошибка:* {search_results['error']}"
        
        results = search_results.get("results", {})
        source = search_results.get("source", "unknown")
        
        # Генерируем в зависимости от объема
        if volume == "short":
            return self._generate_short(topic, results, source)
        elif volume == "extended":
            return self._generate_extended(topic, results, source)
        else:
            return self._generate_detailed(topic, results, source)
    
    def _is_easter_egg(self, text):
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in [
            "план захвата польши", "захват польши", "чайная пасхалка", "пасхалка"
        ])
    
    def _create_easter_egg_response(self):
        return "🥚 *Пасхалка найдена!* Бот работает в штатном режиме."
    
    def _generate_short(self, topic, results, source):
        """Краткий конспект"""
        facts = results.get("facts", [])
        
        conspect = f"📌 *{topic}*\n\n"
        
        if source == "knowledge_base" or source == "general_knowledge":
            conspect += "📚 *Источник:* База знаний\n\n"
        else:
            conspect += f"🔍 *Источник:* {source}\n\n"
        
        if facts:
            for i, fact in enumerate(facts[:4], 1):
                conspect += f"{i}. {fact['text']}\n"
        else:
            conspect += "Информация по теме требует дополнительного изучения\n"
        
        # Ключевые термины
        terms = results.get("key_terms", [])
        if terms:
            conspect += f"\n🔑 *Ключевые термины:* {', '.join(terms[:5])}\n"
        
        conspect += f"\n📊 *Фактов найдено:* {len(facts)}"
        return conspect
    
    def _generate_detailed(self, topic, results, source):
        """Подробный конспект"""
        facts = results.get("facts", [])
        definitions = results.get("definitions", [])
        statistics = results.get("statistics", [])
        
        conspect = f"📚 *{topic}*\n\n"
        
        if source == "knowledge_base":
            conspect += "📚 *Режим:* База знаний (API недоступен)\n\n"
        elif source == "general_knowledge":
            conspect += "📚 *Режим:* Общие знания (API недоступен)\n\n"
        else:
            conspect += f"🔍 *Источник:* {source}\n\n"
        
        # Определения
        if definitions:
            conspect += "📖 *Определения:*\n\n"
            for definition in definitions[:3]:
                conspect += f"• {definition}\n"
            conspect += "\n"
        
        # Факты
        if facts:
            conspect += "🎯 *Основные факты:*\n\n"
            for i, fact in enumerate(facts[:8], 1):
                conspect += f"{i}. {fact['text']}\n"
            conspect += "\n"
        else:
            conspect += "⚠️ *Информация не найдена*\n\n"
        
        # Статистика
        if statistics:
            conspect += "📊 *Статистика:*\n\n"
            for stat in statistics[:5]:
                conspect += f"• {stat}\n"
            conspect += "\n"
        
        # Ключевые термины
        terms = results.get("key_terms", [])
        if terms:
            conspect += "🔑 *Ключевые термины:*\n"
            conspect += f"{', '.join(terms[:8])}\n"
        
        # Информация о поиске
        conspect += f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
        conspect += f"📈 Фактов: {len(facts)} | "
        conspect += f"Определений: {len(definitions)} | "
        conspect += f"Статистик: {len(statistics)}"
        
        if "fallback" in results:
            conspect += "\n⚠️ *Внимание:* Используется локальная база знаний"
        
        return conspect
    
    def _generate_extended(self, topic, results, source):
        """Расширенный конспект"""
        conspect = f"🔬 *ПОЛНЫЙ АНАЛИЗ: {topic}*\n\n"
        
        if source == "knowledge_base":
            conspect += "📚 *Режим:* Локальная база знаний\n\n"
        elif source == "general_knowledge":
            conspect += "📚 *Режим:* Общие знания\n\n"
        else:
            conspect += f"🔍 *Источник данных:* {source}\n\n"
        
        conspect += "="*50 + "\n"
        conspect += "ВВЕДЕНИЕ\n"
        conspect += "="*50 + "\n\n"
        
        conspect += f"*Тема исследования:* {topic}\n"
        conspect += f"*Время анализа:* {datetime.now().strftime('%H:%M')}\n"
        conspect += f"*Режим работы:* {'Локальная база' if 'fallback' in results else 'Поиск в интернете'}\n\n"
        
        # ОПРЕДЕЛЕНИЯ
        definitions = results.get("definitions", [])
        if definitions:
            conspect += "="*50 + "\n"
            conspect += "ОПРЕДЕЛЕНИЯ И ПОНЯТИЯ\n"
            conspect += "="*50 + "\n\n"
            
            for i, definition in enumerate(definitions, 1):
                conspect += f"{i}. {definition}\n\n"
        
        # ФАКТЫ
        facts = results.get("facts", [])
        if facts:
            conspect += "="*50 + "\n"
            conspect += "ФАКТЫ И ИНФОРМАЦИЯ\n"
            conspect += "="*50 + "\n\n"
            
            for i, fact in enumerate(facts[:12], 1):
                source_info = f" ({fact.get('domain', '')})" if fact.get('domain') else ""
                conspect += f"{i}. {fact['text']}{source_info}\n\n"
        
        # СТАТИСТИКА
        statistics = results.get("statistics", [])
        if statistics:
            conspect += "="*50 + "\n"
            conspect += "ЦИФРЫ И СТАТИСТИКА\n"
            conspect += "="*50 + "\n\n"
            
            for stat in statistics:
                conspect += f"• {stat}\n"
            conspect += "\n"
        
        # ТЕРМИНОЛОГИЯ
        terms = results.get("key_terms", [])
        if terms:
            conspect += "="*50 + "\n"
            conspect += "ТЕРМИНОЛОГИЧЕСКИЙ СЛОВАРЬ\n"
            conspect += "="*50 + "\n\n"
            
            for i, term in enumerate(terms[:15], 1):
                conspect += f"{i}. {term}\n"
            conspect += "\n"
        
        # ИТОГИ
        conspect += "="*50 + "\n"
        conspect += "ИТОГИ И РЕКОМЕНДАЦИИ\n"
        conspect += "="*50 + "\n\n"
        
        total_facts = len(facts)
        
        if total_facts >= 8:
            conspect += "✅ Информация достаточно полная для начального изучения\n"
            conspect += "✅ Имеются конкретные данные и определения\n"
            conspect += "✅ Тема освещена с разных сторон\n"
        elif total_facts >= 4:
            conspect += "⚠️ Информация ограниченная, требует дополнения\n"
            conspect += "⚠️ Рекомендуется обратиться к специализированным источникам\n"
        else:
            conspect += "❌ Информации недостаточно для анализа\n"
            conspect += "❌ Попробуйте уточнить запрос или использовать другие источники\n"
        
        conspect += f"\n📊 *Статистика анализа:*\n"
        conspect += f"• Фактов: {len(facts)}\n"
        conspect += f"• Определений: {len(definitions)}\n"
        conspect += f"• Статистических данных: {len(statistics)}\n"
        conspect += f"• Ключевых терминов: {len(terms)}\n"
        
        if "fallback" in results:
            conspect += f"\n⚠️ *Примечание:* API поиска временно недоступен. Используется локальная база знаний.\n"
            conspect += f"Для полного функционала проверьте настройки GOOGLE_API_KEY\n"
        
        conspect += f"\n🤖 *@Konspekt_help_bot* | 🕒 {datetime.now().strftime('%d.%m.%Y')}"
        
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
        
        logger.info("✅ Telegram бот готов к работе")
    
    def _setup_webhook(self):
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
                logger.warning(f"⚠️ Ошибка вебхука: {response.json()}")
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
            elif text == "/api_status":
                return self._send_api_status(chat_id)
            else:
                return self._send_message(chat_id, "❓ Неизвестная команда. Используйте /help")
        
        if text in ["1", "2", "3"]:
            return self._handle_volume(chat_id, text)
        
        return self._handle_topic(chat_id, text)
    
    def _send_welcome(self, chat_id):
        welcome = (
            "🤖 *Добро пожаловать в Konspekt Helper Bot!*\n\n"
            "🔍 *Как использовать:*\n"
            "1. Напишите тему для изучения\n"
            "2. Выберите уровень детализации (1, 2 или 3)\n"
            "3. Получите структурированную информацию\n\n"
            "📊 *Уровни анализа:*\n"
            "• 1 — Краткие тезисы\n"
            "• 2 — Подробный конспект\n"
            "• 3 — Полный анализ\n\n"
            "🚀 *Примеры тем:*\n"
            "• Искусственный интеллект\n"
            "• Квантовая физика\n"
            "• Древний Рим\n"
            "• Блокчейн технологии\n\n"
            "📌 *Примечание:* Если API недоступен, используется локальная база знаний"
        )
        return self._send_message(chat_id, welcome)
    
    def _send_help(self, chat_id):
        help_text = (
            "📚 *Konspekt Helper Bot*\n\n"
            "*Возможные проблемы и решения:*\n\n"
            "❌ *Проблема:* 'Нет данных от поисковиков'\n"
            "✅ *Решение:*\n"
            "1. Проверьте GOOGLE_API_KEY в настройках\n"
            "2. Убедитесь, что API ключ действителен\n"
            "3. При отсутствии API используется локальная база\n\n"
            "*Команды:*\n"
            "/start - Информация о боте\n"
            "/help - Эта справка\n"
            "/stats - Статистика работы\n"
            "/api_status - Статус API\n\n"
            "*Работа с ботом:*\n"
            "1. Просто напишите тему\n"
            "2. Выберите 1, 2 или 3\n"
            "3. Получите конспект"
        )
        return self._send_message(chat_id, help_text)
    
    def _send_stats(self, chat_id):
        stat_text = (
            f"📊 *Статистика бота:*\n\n"
            f"👥 Пользователей: {stats['total_users']}\n"
            f"💬 Сообщений: {stats['total_messages']}\n"
            f"📄 Конспектов: {stats['conspects_created']}\n"
            f"🔍 Поисковых запросов: {stats['google_searches']}\n"
            f"❌ Ошибок API: {stats['api_errors']}\n"
            f"📚 Fallback режим: {stats['fallback_mode']}\n"
            f"⏱ Работает с: {stats['start_time'][:10]}\n\n"
            f"📌 *API статус:* {'✅ Активен' if GOOGLE_API_KEY else '❌ Отключен'}"
        )
        return self._send_message(chat_id, stat_text)
    
    def _send_api_status(self, chat_id):
        if GOOGLE_API_KEY:
            status = "✅ *API ключ установлен*\n\n"
            status += "Проверяю соединение с Google API..."
            
            self._send_message(chat_id, status)
            
            # Проверяем соединение
            try:
                test_url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx=test&q=test"
                response = requests.get(test_url, timeout=5)
                
                if response.status_code == 200:
                    result = "✅ *Соединение успешно*\nAPI работает корректно"
                elif response.status_code == 403:
                    result = "❌ *Ошибка доступа*\nПроверьте правильность API ключа"
                else:
                    result = f"⚠️ *Статус: {response.status_code}*\nAPI отвечает, но могут быть ограничения"
                    
            except Exception as e:
                result = f"❌ *Ошибка соединения:* {str(e)[:100]}"
        else:
            result = (
                "❌ *API ключ не установлен*\n\n"
                "Бот работает в ограниченном режиме с локальной базой знаний.\n\n"
                "*Как исправить:*\n"
                "1. Получите API ключ Google Custom Search\n"
                "2. Установите переменную GOOGLE_API_KEY\n"
                "3. Перезапустите бота"
            )
        
        return self._send_message(chat_id, result)
    
    def _handle_topic(self, chat_id, topic):
        user_id = str(chat_id)
        if user_id not in stats["user_states"]:
            stats["user_states"][user_id] = {}
        
        stats["user_states"][user_id]["pending_topic"] = topic
        
        response = (
            f"🎯 *Тема принята: {topic}*\n\n"
            f"📊 *Выберите уровень анализа:*\n\n"
            f"1️⃣ *Краткие тезисы*\nОсновные факты и термины\n\n"
            f"2️⃣ *Подробный конспект*\nФакты + определения + статистика\n\n"
            f"3️⃣ *Полный анализ*\nВсе данные с структурой\n\n"
            f"🔢 *Отправьте цифру 1, 2 или 3*"
        )
        return self._send_message(chat_id, response)
    
    def _handle_volume(self, chat_id, volume_choice):
        user_id = str(chat_id)
        user_state = stats["user_states"].get(user_id, {})
        topic = user_state.get("pending_topic", "")
        
        if not topic:
            return self._send_message(chat_id, "❌ Сначала отправьте тему для анализа")
        
        volume_map = {"1": "short", "2": "detailed", "3": "extended"}
        volume = volume_map.get(volume_choice, "detailed")
        
        # Уведомление
        self._send_message(chat_id, f"🔍 *Анализирую тему:* {topic}\n📊 Уровень: {volume_choice}/3\n⏳ Подождите...")
        
        try:
            conspect = self.generator.generate(topic, volume)
            stats["conspects_created"] += 1
            
            # Отправляем конспект
            self._send_conspect_safely(chat_id, conspect)
            
            # Финальное сообщение
            final_msg = f"✅ *Анализ завершен!*\n\nНовая тема? Просто напишите её"
            return self._send_message(chat_id, final_msg)
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации: {e}")
            return self._send_message(
                chat_id,
                f"❌ *Ошибка анализа*\n\nПопробуйте другую тему или уточните запрос\n\nОшибка: {str(e)[:100]}"
            )
    
    def _send_conspect_safely(self, chat_id, conspect):
        """Безопасно отправляет конспект"""
        max_length = 4000
        
        if len(conspect) <= max_length:
            self._send_message(chat_id, conspect)
            return
        
        # Разбиваем по разделам
        parts = conspect.split('\n\n')
        
        current = ""
        for part in parts:
            if len(current + part) > max_length and current:
                self._send_message(chat_id, current.strip())
                current = part + "\n\n"
            else:
                current += part + "\n\n"
        
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
            
            if not response.json().get("ok"):
                logger.error(f"❌ Ошибка Telegram API: {response.json()}")
            
            return response.json().get("ok", False)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения: {e}")
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
        elif path == "/api_check":
            status = {
                "google_api_key_set": bool(GOOGLE_API_KEY),
                "telegram_token_set": bool(TELEGRAM_TOKEN),
                "total_searches": stats["google_searches"],
                "api_errors": stats["api_errors"],
                "fallback_mode": stats["fallback_mode"]
            }
            self._send_json(status)
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
    <title>🤖 Konspekt Helper Bot</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
        .status-ok { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .status-warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        .status-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .btn { display: inline-block; background: #0088cc; color: white; padding: 10px 20px; border-radius: 5px; text-decoration: none; margin: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Konspekt Helper Bot</h1>
        
        <div class="status status-ok">
            ✅ Сервер работает
        </div>
        
        <div id="api_status" class="status status-warning">
            ⏳ Проверка API...
        </div>
        
        <h3>📊 Статистика системы:</h3>
        <div id="stats">Загрузка...</div>
        
        <h3>🔗 Быстрые ссылки:</h3>
        <div>
            <a href="https://t.me/Konspekt_help_bot" class="btn" target="_blank">🤖 Открыть бота</a>
            <a href="/stats" class="btn">📈 Статистика (JSON)</a>
            <a href="/api_check" class="btn">🔧 Проверка API</a>
            <a href="/health" class="btn">❤️ Health Check</a>
        </div>
        
        <h3>⚠️ Решение проблем:</h3>
        <p><strong>Если бот пишет "Нет данных от поисковиков":</strong></p>
        <ol>
            <li>Проверьте наличие GOOGLE_API_KEY в настройках</li>
            <li>Убедитесь, что API ключ действителен</li>
            <li>При отсутствии API бот использует локальную базу знаний</li>
            <li>Используйте команду /api_status в боте для проверки</li>
        </ol>
        
        <p style="color: #666; margin-top: 30px;">
            Обновлено: <span id="time"></span>
        </p>
    </div>
    
    <script>
        async function loadStats() {
            try {
                const response = await fetch('/stats');
                const data = await response.json();
                
                document.getElementById('stats').innerHTML = `
                    <p>👥 Пользователей: ${data.total_users || 0}</p>
                    <p>💬 Сообщений: ${data.total_messages || 0}</p>
                    <p>📄 Конспектов: ${data.conspects_created || 0}</p>
                    <p>🔍 Поисков: ${data.google_searches || 0}</p>
                    <p>❌ Ошибок API: ${data.api_errors || 0}</p>
                    <p>📚 Fallback режим: ${data.fallback_mode || 0}</p>
                `;
                
                document.getElementById('time').textContent = new Date().toLocaleTimeString();
            } catch (error) {
                document.getElementById('stats').innerHTML = 'Ошибка загрузки статистики';
            }
        }
        
        async function checkAPIStatus() {
            try {
                const response = await fetch('/api_check');
                const data = await response.json();
                
                let statusHtml = '';
                
                if (data.google_api_key_set) {
                    statusHtml = '<div class="status status-ok">✅ GOOGLE_API_KEY установлен</div>';
                } else {
                    statusHtml = '<div class="status status-error">❌ GOOGLE_API_KEY не установлен</div>';
                }
                
                if (data.telegram_token_set) {
                    statusHtml += '<div class="status status-ok">✅ TELEGRAM_TOKEN установлен</div>';
                }
                
                statusHtml += `<p>🔍 Поисков: ${data.total_searches || 0}</p>`;
                statusHtml += `<p>❌ Ошибок API: ${data.api_errors || 0}</p>`;
                statusHtml += `<p>📚 Fallback режим: ${data.fallback_mode || 0}</p>`;
                
                document.getElementById('api_status').innerHTML = statusHtml;
            } catch (error) {
                document.getElementById('api_status').innerHTML = 
                    '<div class="status status-error">❌ Ошибка проверки API</div>';
            }
        }
        
        loadStats();
        checkAPIStatus();
        setInterval(loadStats, 5000);
        setInterval(checkAPIStatus, 30000);
    </script>
</body>
</html>
"""

# ==================== ЗАПУСК ====================
def main():
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК KONSPEKT HELPER BOT")
    logger.info("=" * 60)
    logger.info(f"🌐 URL: {RENDER_EXTERNAL_URL}")
    logger.info(f"🚪 Порт: {PORT}")
    logger.info(f"🔑 GOOGLE_API_KEY: {'✅ Установлен' if GOOGLE_API_KEY else '❌ Отсутствует'}")
    logger.info(f"🤖 TELEGRAM_TOKEN: {'✅ Установлен' if TELEGRAM_TOKEN else '❌ Отсутствует'}")
    
    if not GOOGLE_API_KEY:
        logger.warning("⚠️ ВНИМАНИЕ: API ключ не установлен")
        logger.warning("⚠️ Бот будет работать в ограниченном режиме")
        logger.warning("⚠️ Для полного функционала установите GOOGLE_API_KEY")
    
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
