#!/usr/bin/env python3
"""
Улучшенный Konspekt Helper Bot с фильтрацией информации
Бот проверяет достоверность источников и фильтрует ненаучную информацию
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
from urllib.parse import urlparse
from collections import Counter

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
    "reliable_sources": 0,
    "filtered_sources": 0,
    "start_time": datetime.now().isoformat(),
    "user_states": {}
}

# ==================== СИСТЕМА ПРОВЕРКИ ИСТОЧНИКОВ ====================
class SourceChecker:
    """Проверяет качество и достоверность источников"""
    
    # Надежные домены (образование, наука, официальные источники)
    RELIABLE_DOMAINS = [
        '.edu', '.ac.', '.gov', '.org', 
        'wikipedia.org', 'arxiv.org', 'sciencedirect.com',
        'nature.com', 'sciencemag.org', 'researchgate.net',
        'springer.com', 'ieee.org', 'ncbi.nlm.nih.gov',
        'who.int', 'unesco.org', 'bbc.com', 'reuters.com',
        'theguardian.com', 'nytimes.com', 'meduza.io'
    ]
    
    # Ненадежные домены (пользовательский контент, развлечения)
    UNRELIABLE_DOMAINS = [
        'reddit.com', '4chan.org', 'tiktok.com', 
        'twitter.com', 'x.com', 'instagram.com',
        'facebook.com', 'pikabu.ru', 'vk.com',
        'livejournal.com', '9gag.com', 'buzzfeed.com'
    ]
    
    # Слова-маркеры ненаучного контента
    PSEUDOSCIENCE_KEYWORDS = [
        'лженаука', 'псевдонаука', 'конспирология', 'теория заговора',
        'чудесное исцеление', 'магическая сила', 'экстрасенс', 'ясновидящий',
        'альтернативная медицина', 'биоэнергетика', 'торсионные поля',
        'холодный ядерный синтез', 'вечный двигатель', 'память воды'
    ]
    
    # Признаки ненадежного контента
    UNRELIABLE_PATTERNS = [
        r'шок[!.]?', r'сенсац[ия][!.]?', r'вы не поверите', r'всем немедленно',
        r'уч[ёе]ные скрывают', r'правительство молчит', r'100% доказано',
        r'официально опровергнуто', r'это скрывают', r'тайное знание',
        r'секретные материалы', r'запрещ[её]нная правда'
    ]
    
    # Признаки научного контента
    SCIENTIFIC_PATTERNS = [
        r'исследовани[ея] показал[ио]', r'эксперимент[ы]? подтвердил[и]',
        r'по данным', r'статистически значим', r'мета-анализ',
        r'рецензируемое издание', r'клиническое испытание',
        r'контролируемое исследование', r'двойной слепой метод'
    ]
    
    def check_source_quality(self, url, title, snippet):
        """Проверяет качество источника по нескольким критериям"""
        score = 0
        reasons = []
        
        # 1. Проверка домена
        domain_quality = self._check_domain(url)
        if domain_quality == "reliable":
            score += 3
            reasons.append("✅ Надежный домен")
        elif domain_quality == "unreliable":
            score -= 2
            reasons.append("⚠️ Ненадежный домен")
        
        # 2. Проверка заголовка на сенсационность
        title_score = self._check_sensationalism(title)
        score += title_score
        if title_score < 0:
            reasons.append("⚠️ Сенсационный заголовок")
        
        # 3. Проверка содержания на научность
        content_score = self._check_content_quality(snippet)
        score += content_score
        if content_score > 0:
            reasons.append("✅ Научный стиль")
        
        # 4. Проверка на псевдонауку
        if self._check_pseudoscience(title + " " + snippet):
            score -= 3
            reasons.append("❌ Признаки псевдонауки")
        
        # Определяем уровень достоверности
        if score >= 3:
            quality = "high"
        elif score >= 0:
            quality = "medium"
        else:
            quality = "low"
        
        return {
            "quality": quality,
            "score": score,
            "reasons": reasons,
            "domain": urlparse(url).netloc if url else "unknown"
        }
    
    def _check_domain(self, url):
        """Проверяет домен источника"""
        if not url:
            return "neutral"
        
        url_lower = url.lower()
        
        # Проверяем надежные домены
        for domain in self.RELIABLE_DOMAINS:
            if domain in url_lower:
                return "reliable"
        
        # Проверяем ненадежные домены
        for domain in self.UNRELIABLE_DOMAINS:
            if domain in url_lower:
                return "unreliable"
        
        return "neutral"
    
    def _check_sensationalism(self, text):
        """Проверяет текст на сенсационность"""
        if not text:
            return 0
        
        text_lower = text.lower()
        
        # Счетчик сенсационных маркеров
        sensational_count = 0
        for pattern in self.UNRELIABLE_PATTERNS:
            if re.search(pattern, text_lower):
                sensational_count += 1
        
        if sensational_count >= 2:
            return -2  # Очень сенсационный
        elif sensational_count == 1:
            return -1  # Немного сенсационный
        
        return 0  # Нормальный заголовок
    
    def _check_content_quality(self, text):
        """Проверяет качество содержания"""
        if not text:
            return 0
        
        text_lower = text.lower()
        
        # Счетчик научных маркеров
        scientific_count = 0
        for pattern in self.SCIENTIFIC_PATTERNS:
            if re.search(pattern, text_lower):
                scientific_count += 1
        
        # Проверяем наличие цифр и данных
        has_numbers = bool(re.search(r'\d+[%‰°]|\d+\.\d+', text))
        has_references = bool(re.search(r'исследовани[ея]|эксперимент|данные', text_lower))
        
        score = 0
        if scientific_count >= 2:
            score += 2
        elif scientific_count == 1:
            score += 1
        
        if has_numbers:
            score += 1
        if has_references:
            score += 1
        
        return score
    
    def _check_pseudoscience(self, text):
        """Проверяет на признаки псевдонауки"""
        text_lower = text.lower()
        
        for keyword in self.PSEUDOSCIENCE_KEYWORDS:
            if keyword in text_lower:
                return True
        
        # Проверяем паттерны заговоров
        conspiracy_patterns = [
            r'тайное правительство', r'мировая закулиса',
            r'скрыва[ю]?т правду', r'на самом деле',
            r'официальная наука ошибается'
        ]
        
        for pattern in conspiracy_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def filter_content(self, text):
        """Фильтрует текст, удаляя ненадежные утверждения"""
        if not text:
            return text
        
        sentences = re.split(r'[.!?]+', text)
        filtered_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Проверяем предложение на достоверность
            if self._is_reliable_sentence(sentence):
                filtered_sentences.append(sentence)
            else:
                logger.debug(f"Отфильтровано: {sentence[:50]}...")
                stats["filtered_sources"] += 1
        
        return ". ".join(filtered_sentences) + ("." if filtered_sentences else "")
    
    def _is_reliable_sentence(self, sentence):
        """Проверяет, является ли предложение достоверным"""
        if len(sentence) < 10:
            return False
        
        sentence_lower = sentence.lower()
        
        # 1. Проверяем на сенсационность
        for pattern in self.UNRELIABLE_PATTERNS:
            if re.search(pattern, sentence_lower):
                return False
        
        # 2. Проверяем на псевдонауку
        if self._check_pseudoscience(sentence):
            return False
        
        # 3. Проверяем на излишнюю категоричность без доказательств
        categorical_without_proof = [
            r'точно известно', r'несомненно', r'абсолютно точно',
            r'доказано раз и навсегда', r'это факт'
        ]
        
        for pattern in categorical_without_proof:
            if re.search(pattern, sentence_lower):
                # Разрешаем только если есть ссылки на исследования
                if not re.search(r'исследовани[ея]|эксперимент|данные', sentence_lower):
                    return False
        
        # 4. Проверяем на наличие конкретики
        has_specifics = bool(re.search(r'\d{4}|\d+[%]|\d+\.\d+', sentence))
        has_clear_subject = len(sentence.split()) > 5
        
        return has_clear_subject and (has_specifics or len(sentence) > 30)

# ==================== УЛУЧШЕННЫЙ АНАЛИЗАТОР ====================
class InformationAnalyzer:
    """Анализирует информацию с проверкой достоверности"""
    
    def __init__(self):
        self.source_checker = SourceChecker()
        self.cache = {}
    
    def analyze_topic(self, query, search_results):
        """Анализирует тему с фильтрацией источников"""
        # Определяем тип темы
        topic_type = self._determine_topic_type(query)
        
        # Анализируем результаты с проверкой качества
        analysis = self._analyze_with_quality_check(search_results, query)
        
        return {
            "topic": query,
            "type": topic_type,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat(),
            "source_quality_report": self._generate_quality_report(analysis)
        }
    
    def _determine_topic_type(self, query):
        """Определяет тип темы"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["история", "война", "революция"]):
            return "историческая"
        elif any(word in query_lower for word in ["технология", "программирование", "искусственный интеллект"]):
            return "технологическая"
        elif any(word in query_lower for word in ["медицина", "здоровье", "болезнь"]):
            return "медицинская"
        elif any(word in query_lower for word in ["экономика", "финансы", "рынок"]):
            return "экономическая"
        elif any(word in query_lower for word in ["физика", "химия", "биология", "наука"]):
            return "научная"
        return "общая"
    
    def _analyze_with_quality_check(self, results, query):
        """Анализирует результаты с проверкой качества"""
        items = results.get("items", [])
        
        reliable_points = []
        questionable_points = []
        statistics = []
        definitions = []
        sources_checked = []
        
        for item in items[:10]:  # Проверяем больше результатов
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            
            # Проверяем качество источника
            source_check = self.source_checker.check_source_quality(link, title, snippet)
            
            # Фильтруем контент
            filtered_text = self.source_checker.filter_content(f"{title}. {snippet}")
            if not filtered_text:
                continue  # Пропускаем полностью отфильтрованный контент
            
            # Извлекаем факты только из надежных частей
            fact = self._extract_reliable_fact(filtered_text, query, source_check["quality"])
            if fact:
                if source_check["quality"] == "high":
                    reliable_points.append({
                        "text": fact,
                        "source": link,
                        "quality": "high",
                        "reasons": source_check["reasons"]
                    })
                    stats["reliable_sources"] += 1
                elif source_check["quality"] == "medium":
                    reliable_points.append({
                        "text": fact,
                        "source": link,
                        "quality": "medium",
                        "reasons": source_check["reasons"]
                    })
                else:
                    questionable_points.append({
                        "text": f"⚠️ {fact}",
                        "source": link,
                        "quality": "low",
                        "reasons": source_check["reasons"]
                    })
            
            # Извлекаем данные только из надежного контента
            if source_check["quality"] in ["high", "medium"]:
                numbers = self._extract_numbers(filtered_text)
                statistics.extend(numbers)
                
                definition = self._extract_definition(filtered_text)
                if definition:
                    definitions.append(definition)
            
            sources_checked.append({
                "url": link,
                "quality": source_check["quality"],
                "score": source_check["score"],
                "domain": source_check["domain"]
            })
        
        # Сортируем точки по качеству
        reliable_points.sort(key=lambda x: 0 if x["quality"] == "high" else 1)
        all_points = [p["text"] for p in reliable_points] + [p["text"] for p in questionable_points]
        
        # Извлекаем термины только из надежных точек
        key_terms = self._extract_terms_from_reliable_points([p["text"] for p in reliable_points])
        
        # Находим консенсусные факты
        consensus_terms = self._find_consensus_facts([p["text"] for p in reliable_points])
        
        return {
            "reliable_points": [p["text"] for p in reliable_points[:8]],
            "questionable_points": [p["text"] for p in questionable_points[:3]],
            "statistics": statistics[:6],
            "definitions": definitions[:4],
            "key_terms": key_terms[:8],
            "consensus_terms": consensus_terms[:5],
            "total_sources": len(items),
            "reliable_sources_count": len([s for s in sources_checked if s["quality"] in ["high", "medium"]]),
            "sources_quality": sources_checked[:5],
            "all_points": all_points[:10]
        }
    
    def _extract_reliable_fact(self, text, query, quality):
        """Извлекает факт с учетом качества источника"""
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if 30 < len(sentence) < 200:
                if self._is_relevant_fact(sentence, query):
                    # Для низкокачественных источников требуем больше доказательств
                    if quality == "low":
                        if re.search(r'\d{4}|\d+%|исследовани[ея]', sentence.lower()):
                            return sentence[:180]
                    else:
                        return sentence[:180]
        
        return None
    
    def _is_relevant_fact(self, sentence, query):
        """Проверяет релевантность факта"""
        query_words = [word.lower() for word in query.split() if len(word) > 3]
        sentence_lower = sentence.lower()
        
        matches = sum(1 for word in query_words if word in sentence_lower)
        return matches > 0 and len(sentence.split()) > 5
    
    def _extract_numbers(self, text):
        """Извлекает числа и статистику"""
        patterns = [
            r'\d+\.?\d*%',  # Проценты
            r'\d+\.?\d*\s*(?:млн|млрд|тыс|миллион|миллиард|тысяч)',  # Большие числа
            r'\$\d+\.?\d*',  # Доллары
            r'\d+\.?\d*\s*(?:долларов|рублей|евро|долл\.|руб\.)',
            r'\d{4}\s*году?',  # Года
            r'\d+\.?\d*\s*(?:лет|год|месяц|день)'  # Периоды
        ]
        
        numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            numbers.extend(matches)
        
        return list(set(numbers))[:8]
    
    def _extract_definition(self, text):
        """Извлекает определения"""
        patterns = [
            r'это\s+[^.!?]{10,120}[.!?]',
            r'является\s+[^.!?]{10,120}[.!?]',
            r'определ[яю]ется\s+как\s+[^.!?]{10,120}[.!?]',
            r'под\s+[^.!?]{5,20}\s+понима[юя]т\s+[^.!?]{10,120}[.!?]'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                definition = match.group(0).strip()
                if 30 < len(definition) < 150:
                    return definition[:120] + "..."
        
        return None
    
    def _extract_terms_from_reliable_points(self, points):
        """Извлекает термины из надежных точек"""
        all_text = " ".join(points)
        words = re.findall(r'\b[а-яёa-z]{4,}\b', all_text.lower())
        
        stop_words = {"этот", "такой", "какой", "который", "очень", "может", "будет"}
        freq = {}
        
        for word in words:
            if word not in stop_words and len(word) > 3:
                freq[word] = freq.get(word, 0) + 1
        
        sorted_terms = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [term.capitalize() for term, count in sorted_terms[:15]]
    
    def _find_consensus_facts(self, points):
        """Находит факты, упоминаемые в нескольких источниках"""
        if not points:
            return []
        
        # Упрощаем точки для сравнения
        simplified = []
        for point in points:
            clean = re.sub(r'[^\w\s]', '', point.lower())
            words = clean.split()
            keywords = [w for w in words if len(w) > 4][:6]
            simplified.append(" ".join(keywords))
        
        # Считаем частоту слов
        word_counter = Counter()
        for point in simplified:
            word_counter.update(point.split())
        
        # Берем слова, встречающиеся в нескольких источниках
        common_terms = [word for word, count in word_counter.items() if count > 1]
        return common_terms[:8]
    
    def _generate_quality_report(self, analysis):
        """Генерирует отчет о качестве источников"""
        total = analysis["total_sources"]
        reliable = analysis["reliable_sources_count"]
        
        if total == 0:
            return "Нет данных для анализа"
        
        reliability_percent = (reliable / total) * 100
        
        if reliability_percent >= 70:
            rating = "✅ Высокое"
        elif reliability_percent >= 40:
            rating = "⚠️ Среднее"
        else:
            rating = "❌ Низкое"
        
        return f"{rating} качество источников ({reliable}/{total} надежных)"
    
    def _is_junk(self, text):
        """Проверяет, не является ли текст мусором"""
        junk_phrases = [
            "кликните", "нажмите", "подробнее", "читать далее",
            "узнать больше", "реклама", "sponsored", "advertisement",
            "купить", "заказать", "цена", "акция", "скидка"
        ]
        
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in junk_phrases)

# ==================== УМНЫЙ ПОИСК ====================
class SmartGoogleSearch:
    def __init__(self):
        self.api_key = GOOGLE_API_KEY
        self.cse_id = GOOGLE_CSE_ID
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.analyzer = InformationAnalyzer()
        
    def search_and_analyze(self, query):
        """Выполняет поиск с проверкой качества"""
        if not query or len(query.strip()) < 2:
            return {"error": "Короткий запрос"}
        
        stats["google_searches"] += 1
        
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "num": 10,
            "hl": "ru",
            "lr": "lang_ru",
            "gl": "ru"
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=15)
            
            if response.status_code != 200:
                return self._create_fallback(query)
            
            data = response.json()
            
            # Анализируем с проверкой качества
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
                    "reliable_points": ["Информация требует проверки по надежным источникам"],
                    "questionable_points": [],
                    "statistics": [],
                    "definitions": [],
                    "key_terms": [query.capitalize()],
                    "consensus_terms": [],
                    "total_sources": 0,
                    "reliable_sources_count": 0,
                    "sources_quality": []
                },
                "source_quality_report": "❌ Нет данных от поисковика"
            },
            "fallback": True
        }

# ==================== ГЕНЕРАТОР КОНСПЕКТОВ ====================
class SmartConspectGenerator:
    def __init__(self):
        self.searcher = SmartGoogleSearch()
        logger.info("✅ Генератор готов с системой проверки качества")
    
    def generate(self, topic, volume="short"):
        """Генерирует конспект с учетом качества информации"""
        # Пасхалка
        if self._is_easter_egg(topic):
            return self._create_easter_egg_response()
        
        # Поиск и анализ с проверкой качества
        search_results = self.searcher.search_and_analyze(topic)
        structured_info = search_results.get("structured_info", {})
        analysis = structured_info.get("analysis", {})
        quality_report = structured_info.get("source_quality_report", "")
        
        # В зависимости от объема
        if volume == "detailed":
            return self._generate_detailed(topic, analysis, quality_report)
        elif volume == "extended":
            return self._generate_extended(topic, analysis, quality_report)
        else:
            return self._generate_short(topic, analysis, quality_report)
    
    def _is_easter_egg(self, text):
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in [
            "план захвата польши", "захват польши", "чайная пасхалка"
        ])
    
    def _create_easter_egg_response(self):
        return "🍵 *Пасхалка активирована!* Чайные церемонии — важный культурный феномен."
    
    def _generate_short(self, topic, analysis, quality_report):
        """Кратко - только проверенная информация"""
        reliable_points = analysis.get("reliable_points", [])
        
        if not reliable_points:
            return f"📌 *{topic}*\n\n🔍 *{quality_report}*\n\nИнформация не найдена в надежных источниках"
        
        conspect = f"📌 *{topic}*\n\n🔍 *{quality_report}*\n\n"
        
        # Только надежные точки
        for i, point in enumerate(reliable_points[:4], 1):
            conspect += f"• {point}\n"
        
        # Консенсусные термины
        consensus = analysis.get("consensus_terms", [])
        if consensus:
            conspect += f"\n🔑 Ключевые понятия: {', '.join(consensus[:3])}\n"
        
        return conspect
    
    def _generate_detailed(self, topic, analysis, quality_report):
        """Подробно - проверенная информация + данные"""
        reliable_points = analysis.get("reliable_points", [])
        
        if not reliable_points:
            return f"📚 *{topic}*\n\n🔍 *{quality_report}*\n\nНедостаточно проверенной информации"
        
        conspect = f"📚 *{topic}*\n\n🔍 *{quality_report}*\n\n"
        
        # Все надежные точки
        for i, point in enumerate(reliable_points[:8], 1):
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
        
        # Сомнительные точки (если есть)
        questionable = analysis.get("questionable_points", [])
        if questionable:
            conspect += f"\n⚠️ *Спорная информация:*\n"
            for point in questionable[:2]:
                conspect += f"• {point}\n"
        
        # Информация о поиске
        conspect += f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
        conspect += f"📈 Надежных источников: {analysis.get('reliable_sources_count', 0)}/{analysis.get('total_sources', 0)}"
        
        return conspect
    
    def _generate_extended(self, topic, analysis, quality_report):
        """Полно - вся информация с маркировкой качества"""
        all_points = analysis.get("all_points", [])
        
        if not all_points:
            return f"🔬 *{topic}*\n\n🔍 *{quality_report}*\n\nИнформация не найдена"
        
        conspect = f"🔬 *{topic}*\n\n🔍 *{quality_report}*\n\n"
        
        # Все точки с указанием качества
        reliable_count = 0
        for i, point in enumerate(all_points, 1):
            if point.startswith("⚠️"):
                conspect += f"{i}. {point}\n"
            else:
                conspect += f"{i}. ✅ {point}\n"
                reliable_count += 1
        
        # Вся статистика
        statistics = analysis.get("statistics", [])
        if statistics:
            conspect += f"\n📊 *Статистика и цифры:*\n\n"
            for stat in statistics:
                conspect += f"• {stat}\n"
        
        # Все определения
        definitions = analysis.get("definitions", [])
        if definitions:
            conspect += f"\n📖 *Определения:*\n\n"
            for definition in definitions:
                conspect += f"• {definition}\n"
        
        # Вся терминология
        terms = analysis.get("key_terms", [])
        consensus = analysis.get("consensus_terms", [])
        
        if terms:
            conspect += f"\n🔤 *Терминология:*\n\n"
            for i, term in enumerate(terms[:12], 1):
                conspect += f"{i}. {term}\n"
        
        if consensus:
            conspect += f"\n🎯 *Консенсусные понятия:*\n"
            conspect += f"{', '.join(consensus)}\n"
        
        # Детальный отчет о качестве
        conspect += f"\n{'='*50}\n"
        conspect += f"📋 *ОТЧЕТ О КАЧЕСТВЕ ИНФОРМАЦИИ*\n"
        conspect += f"{'='*50}\n\n"
        
        conspect += f"• Всего источников: {analysis.get('total_sources', 0)}\n"
        conspect += f"• Надежных источников: {analysis.get('reliable_sources_count', 0)}\n"
        conspect += f"• Проверенных фактов: {reliable_count}\n"
        conspect += f"• Отфильтровано: {stats.get('filtered_sources', 0)}\n\n"
        
        # Информация о доменах
        sources_quality = analysis.get("sources_quality", [])
        if sources_quality:
            conspect += f"*Проверенные источники:*\n"
            for source in sources_quality[:5]:
                quality_icon = "✅" if source["quality"] == "high" else "⚠️" if source["quality"] == "medium" else "❌"
                conspect += f"{quality_icon} {source['domain']} (оценка: {source['score']})\n"
        
        conspect += f"\n🕒 Анализ выполнен: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        conspect += f"\n🤖 @Konspekt_help_bot с проверкой качества"
        
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
        
        logger.info("✅ Telegram бот готов с системой проверки качества")
    
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
            elif text == "/quality":
                return self._send_quality_info(chat_id)
            else:
                return self._send_message(chat_id, "❓ Неизвестная команда")
        
        if text in ["1", "2", "3"]:
            return self._handle_volume(chat_id, text)
        
        return self._handle_topic(chat_id, text)
    
    def _send_welcome(self, chat_id):
        welcome = (
            "🔍 *Бот с проверкой качества информации*\n\n"
            "🤖 *Что нового:*\n"
            "• ✅ Фильтрация ненадежных источников (Reddit и др.)\n"
            "• ✅ Проверка на псевдонауку и сенсационность\n"
            "• ✅ Приоритет научным и официальным источникам\n"
            "• ✅ Маркировка спорной информации\n\n"
            "📊 *Уровни:*\n"
            "• 1 — Проверенные тезисы\n"
            "• 2 — Факты + данные + определения\n"
            "• 3 — Полный отчет с оценкой качества\n\n"
            "📌 Просто напишите тему"
        )
        return self._send_message(chat_id, welcome)
    
    def _send_help(self, chat_id):
        help_text = (
            "🔍 *Как работает проверка качества:*\n\n"
            "1. *Фильтрация доменов:*\n"
            "   ✅ Приоритет: .edu, .gov, научные журналы\n"
            "   ❌ Фильтрация: Reddit, соцсети, развлекательные сайты\n\n"
            "2. *Проверка контента:*\n"
            "   • Обнаружение сенсационных заголовков\n"
            "   • Фильтрация псевдонаучных утверждений\n"
            "   • Проверка на конкретику и ссылки на исследования\n\n"
            "3. *Оценка источников:*\n"
            "   • Каждому источнику присваивается оценка\n"
            "   • Информация маркируется ✅/⚠️/❌\n"
            "   • В отчете показывается процент надежных данных\n\n"
            "📌 *Пример:*\n"
            "Отправьте 'Квантовая физика' или 'История Рима'"
        )
        return self._send_message(chat_id, help_text)
    
    def _send_stats(self, chat_id):
        stat_text = (
            f"📊 *Статистика с проверкой качества:*\n\n"
            f"👥 Пользователей: {stats['total_users']}\n"
            f"💬 Сообщений: {stats['total_messages']}\n"
            f"📄 Конспектов: {stats['conspects_created']}\n"
            f"🔍 Поисков: {stats['google_searches']}\n"
            f"✅ Надежных источников: {stats['reliable_sources']}\n"
            f"🚫 Отфильтровано: {stats['filtered_sources']}\n"
            f"📈 Эффективность фильтрации: {stats['filtered_sources']/(stats['google_searches']*10+1)*100:.1f}%"
        )
        return self._send_message(chat_id, stat_text)
    
    def _send_quality_info(self, chat_id):
        info = (
            "🔬 *Система проверки качества:*\n\n"
            "*Проверяемые домены:*\n"
            "✅ Надежные: .edu, .gov, .org, научные журналы\n"
            "⚠️ Нейтральные: новостные сайты, блоги\n"
            "❌ Ненадежные: Reddit, соцсети, форумы\n\n"
            "*Маркеры ненадежности:*\n"
            "• Сенсационные заголовки ('Шок!', 'Сенсация!')\n"
            "• Псевдонаучные термины\n"
            "• Отсутствие конкретных данных\n"
            "• Утверждения без ссылок на исследования\n\n"
            "📌 Бот помечает ⚠️ спорную информацию"
        )
        return self._send_message(chat_id, info)
    
    def _handle_topic(self, chat_id, topic):
        user_id = str(chat_id)
        if user_id not in stats["user_states"]:
            stats["user_states"][user_id] = {}
        
        stats["user_states"][user_id]["pending_topic"] = topic
        
        response = (
            f"🎯 *Тема: {topic}*\n\n"
            f"🔍 *Будет проверено качество источников*\n\n"
            f"📊 *Уровень информации:*\n\n"
            f"1️⃣ Только проверенные тезисы\n"
            f"2️⃣ Факты + данные + определения\n"
            f"3️⃣ Полный отчет с оценкой качества\n\n"
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
        
        # Уведомление
        self._send_message(chat_id, f"🔍 *Проверяю информацию по теме:* {topic}\n📊 Уровень: {volume_choice}/3")
        
        try:
            conspect = self.generator.generate(topic, volume)
            stats["conspects_created"] += 1
            
            # Отправляем
            self._send_conspect_safely(chat_id, conspect)
            
            # Короткое завершение
            return self._send_message(chat_id, "✅ *Готово!*\n\nНовая тема? Просто напишите её")
            
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return self._send_message(
                chat_id,
                f"❌ *Ошибка проверки информации*\n\nПопробуйте другую формулировку"
            )
    
    def _send_conspect_safely(self, chat_id, conspect):
        """Безопасно отправляет конспект"""
        max_length = 4000
        
        if len(conspect) <= max_length:
            self._send_message(chat_id, conspect)
            return
        
        # Разбиваем по разделам
        sections = re.split(r'(={10,}|\n━━[━]+\n)', conspect)
        
        current = ""
        for section in sections:
            if re.match(r'(={10,}|\n━━[━]+\n)', section):
                if current and len(current) > 1000:
                    self._send_message(chat_id, current.strip())
                    current = section + "\n\n"
                else:
                    current += section + "\n\n"
            else:
                if len(current + section) > max_length and current:
                    self._send_message(chat_id, current.strip())
                    current = section
                else:
                    current += section
        
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
        elif path == "/quality_info":
            info = {
                "reliable_domains": SourceChecker.RELIABLE_DOMAINS[:10],
                "unreliable_domains": SourceChecker.UNRELIABLE_DOMAINS,
                "filtered_sources": stats.get("filtered_sources", 0),
                "reliable_sources": stats.get("reliable_sources", 0)
            }
            self._send_json(info)
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
    <title>🤖 Бот с проверкой качества информации</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f0f2f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .status { color: green; font-weight: bold; padding: 10px; background: #e8f5e8; border-radius: 5px; }
        .quality-badges { display: flex; gap: 10px; margin: 15px 0; }
        .badge { padding: 5px 10px; border-radius: 4px; font-size: 14px; }
        .badge-reliable { background: #d4edda; color: #155724; }
        .badge-unreliable { background: #f8d7da; color: #721c24; }
        .badge-filtered { background: #fff3cd; color: #856404; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🤖 Бот с проверкой качества информации</h2>
        <p class="status">✅ Работает с системой фильтрации ненадежных источников</p>
        
        <div class="quality-badges">
            <div class="badge badge-reliable">✅ Надежные источники</div>
            <div class="badge badge-unreliable">❌ Ненадежные источники</div>
            <div class="badge badge-filtered">⚠️ Отфильтровано</div>
        </div>
        
        <h3>🔍 Что фильтрует бот:</h3>
        <ul>
            <li>❌ Reddit, социальные сети, пользовательские форумы</li>
            <li>❌ Сенсационные заголовки и псевдонаучный контент</li>
            <li>❌ Информация без ссылок на исследования и данные</li>
            <li>✅ Приоритет: .edu, .gov, научные журналы, официальные источники</li>
        </ul>
        
        <h3>📊 Статистика системы:</h3>
        <div id="stats">Загрузка...</div>
        
        <h3>🔗 Быстрые ссылки:</h3>
        <p><a href="https://t.me/Konspekt_help_bot" target="_blank">🤖 Открыть бота</a></p>
        <p><a href="/stats" target="_blank">📈 Полная статистика (JSON)</a></p>
        <p><a href="/quality_info" target="_blank">🔬 Информация о системе проверки</a></p>
        
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
                    <p>👥 Пользователей: ${data.total_users || 0}</p>
                    <p>📄 Конспектов: ${data.conspects_created || 0}</p>
                    <p>🔍 Поисков: ${data.google_searches || 0}</p>
                    <p>✅ Надежных источников: ${data.reliable_sources || 0}</p>
                    <p>🚫 Отфильтровано: ${data.filtered_sources || 0}</p>
                `;
                
                document.getElementById('time').textContent = new Date().toLocaleTimeString();
            } catch (error) {
                document.getElementById('stats').innerHTML = 'Ошибка загрузки статистики';
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
    logger.info("🚀 ЗАПУСК БОТА С ПРОВЕРКОЙ КАЧЕСТВА")
    logger.info("=" * 60)
    logger.info(f"🌐 URL: {RENDER_EXTERNAL_URL}")
    logger.info(f"🚪 Порт: {PORT}")
    logger.info("✅ Режим: Фильтрация ненадежных источников")
    logger.info(f"✅ Надежные домены: {len(SourceChecker.RELIABLE_DOMAINS)}")
    logger.info(f"✅ Ненадежные домены: {len(SourceChecker.UNRELIABLE_DOMAINS)}")
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
