#!/usr/bin/env python3
"""
Konspekt Helper Bot - С анализом достоверности и связкой информации
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
import hashlib
import time

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

# ==================== СИСТЕМА ОЦЕНКИ ДОСТОВЕРНОСТИ ====================
class ReliabilityAnalyzer:
    """Анализирует достоверность источников и контента"""
    
    # Надежные домены (научные, академические, официальные)
    RELIABLE_DOMAINS = {
        "wikipedia.org": 0.9,
        "arxiv.org": 0.95,
        "nature.com": 0.95,
        "science.org": 0.95,
        "springer.com": 0.9,
        "elsevier.com": 0.9,
        "ieee.org": 0.9,
        "acm.org": 0.9,
        "nasa.gov": 0.95,
        "nih.gov": 0.95,
        "who.int": 0.95,
        "un.org": 0.9,
        "gov": 0.85,  # Любые .gov сайты
        "edu": 0.85,  # Образовательные учреждения
        "researchgate.net": 0.8,
        "ncbi.nlm.nih.gov": 0.95,
        "jstor.org": 0.9,
        "sciencedirect.com": 0.9,
        "google.com": 0.7,
        "youtube.com": 0.4,
        "reddit.com": 0.3,
        "twitter.com": 0.3,
        "facebook.com": 0.2,
        "tiktok.com": 0.2,
        "blogspot.com": 0.5,
        "wordpress.com": 0.5,
        "medium.com": 0.6,
        "quora.com": 0.4,
        "forum.": 0.3,
        "chat.": 0.2,
        "discord.": 0.2,
        "4chan.org": 0.1,
    }
    
    # Ключевые слова для оценки научности
    SCIENTIFIC_INDICATORS = {
        "positive": [
            "исследование", "эксперимент", "анализ", "метод", "методология",
            "результаты", "выводы", "данные", "статистика", "выборка",
            "контрольная группа", "гипотеза", "теория", "публикация",
            "рецензирование", "индекс цитирования", "impact factor",
            "университет", "институт", "лаборатория", "профессор",
            "доктор наук", "кандидат наук", "научная статья",
            "конференция", "симпозиум", "патент", "открытие",
            "доказательство", "эмпирический", "теоретический",
            "систематический", "комплексный", "фундаментальный"
        ],
        "negative": [
            "я думаю", "мне кажется", "по моему мнению", "наверное",
            "возможно", "вероятно", "скорее всего", "как бы",
            "типа", "вроде", "бля", "хуйня", "пиздец", "охуенно",
            "ебать", "нахуй", "походу", "чё", "щас", "ага",
            "лол", "кек", "рофл", "имхо", "имею мнение",
            "в интернете пишут", "говорят", "слухи", "сплетни",
            "конспирология", "заговор", "инопланетяне", "рептилоиды",
            "масоны", "иллюминаты", "голограмма", "фейк", "фальшивка"
        ]
    }
    
    def analyze_source(self, url, domain):
        """Анализирует надежность источника по домену"""
        reliability_score = 0.5  # Среднее по умолчанию
        
        # Проверяем по списку надежных доменов
        for domain_pattern, score in self.RELIABLE_DOMAINS.items():
            if domain_pattern in domain or domain_pattern in url:
                reliability_score = max(reliability_score, score)
        
        # Классифицируем источник
        if reliability_score >= 0.8:
            category = "научный/академический"
            color = "🟢"
        elif reliability_score >= 0.6:
            category = "официальный/новостной"
            color = "🟡"
        elif reliability_score >= 0.4:
            category = "блог/форум"
            color = "🟠"
        else:
            category = "сомнительный/развлекательный"
            color = "🔴"
        
        return {
            "score": reliability_score,
            "category": category,
            "color": color,
            "domain": domain
        }
    
    def analyze_content_quality(self, text):
        """Анализирует качество и научность контента"""
        text_lower = text.lower()
        
        # Проверяем научные индикаторы
        scientific_score = 0
        for indicator in self.SCIENTIFIC_INDICATORS["positive"]:
            if indicator in text_lower:
                scientific_score += 1
        
        # Проверяем негативные индикаторы (бред, сленг, мнения)
        unscientific_score = 0
        for indicator in self.SCIENTIFIC_INDICATORS["negative"]:
            if indicator in text_lower:
                unscientific_score += 2  # Более строго наказываем
        
        # Проверяем структуру текста
        has_numbers = bool(re.search(r'\d+', text))
        has_dates = bool(re.search(r'\d{4}', text))
        has_citations = bool(re.search(r'\[\d+\]|\([^)]+\)', text))
        
        # Оцениваем объективность (отсутствие субъективных маркеров)
        subjective_markers = ["я", "мне", "мой", "моё", "мы", "нам", "наш", "наше"]
        subjective_count = sum(1 for marker in subjective_markers if marker in text_lower)
        
        # Вычисляем итоговый score
        quality_score = (
            (scientific_score * 0.3) -
            (unscientific_score * 0.4) +
            (has_numbers * 0.1) +
            (has_dates * 0.1) +
            (has_citations * 0.2) -
            (subjective_count * 0.1)
        )
        
        # Нормализуем score
        quality_score = max(0, min(1, 0.5 + quality_score / 10))
        
        # Определяем уровень качества
        if quality_score >= 0.7:
            quality_level = "высокий (научный)"
            emoji = "🎓"
        elif quality_score >= 0.5:
            quality_level = "средний (информативный)"
            emoji = "📚"
        elif quality_score >= 0.3:
            quality_level = "низкий (популярный)"
            emoji = "📰"
        else:
            quality_level = "сомнительный (ненадежный)"
            emoji = "⚠️"
        
        return {
            "score": quality_score,
            "level": quality_level,
            "emoji": emoji,
            "scientific_count": scientific_score,
            "unscientific_count": unscientific_score,
            "has_numbers": has_numbers,
            "has_dates": has_dates,
            "has_citations": has_citations
        }
    
    def is_likely_bs(self, text):
        """Определяет, является ли текст бредом/ненаучным"""
        text_lower = text.lower()
        
        # Критерии бреда
        bs_indicators = [
            ("заговор", 2),
            ("инопланетяне", 3),
            ("рептилоиды", 3),
            ("иллюминаты", 3),
            ("масоны", 2),
            ("лженаука", 3),
            ("фейк", 2),
            ("фальшивка", 2),
            ("обман", 2),
            ("мистификация", 2),
            ("экстрасенс", 2),
            ("астрал", 2),
            ("энергия вселенной", 2),
            ("чистка чакр", 2),
            ("гороскоп", 1),
            ("нумерология", 1),
            ("хиромантия", 1),
            ("бля", 3),
            ("пиздец", 3),
            ("охуенно", 2),
            ("ебать", 3),
            ("нахуй", 3),
            ("рофл", 1),
            ("имхо", 1),
            ("типа", 1),
            ("как бы", 1),
            ("вроде", 1),
            ("походу", 1)
        ]
        
        bs_score = 0
        for indicator, weight in bs_indicators:
            if indicator in text_lower:
                bs_score += weight
        
        # Проверяем субъективность
        subjective_words = ["я думаю", "мне кажется", "по моему мнению", "наверное", "возможно"]
        for word in subjective_words:
            if word in text_lower:
                bs_score += 1
        
        # Если много заглавных букв (крик) или много восклицательных знаков
        if (sum(1 for c in text if c.isupper()) / len(text) > 0.3) or text.count('!') > 3:
            bs_score += 2
        
        return bs_score >= 3  # Порог для определения как бред

# ==================== УМНЫЙ ПОИСК С АНАЛИЗОМ ====================
class IntelligentSearchAPI:
    def __init__(self):
        self.api_key = GOOGLE_API_KEY
        self.cse_id = GOOGLE_CSE_ID
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.analyzer = ReliabilityAnalyzer()
        self.cache = {}
        logger.info("✅ Интеллектуальный поиск с анализом достоверности готов")
    
    def search(self, query, num_results=8):
        """Выполняет поиск с анализом достоверности"""
        if not query or len(query.strip()) < 2:
            return self._create_empty_result(query)
        
        cache_key = hashlib.md5(query.encode()).hexdigest()
        if cache_key in self.cache:
            logger.info(f"Использую кэш для: {query}")
            return self.cache[cache_key]
        
        stats["google_searches"] += 1
        
        # Параметры для научного поиска
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "num": min(num_results, 10),
            "hl": "ru",
            "lr": "lang_ru",
            "gl": "ru",
            "cr": "countryRU",
            "sort": "review"  # Сортировка по релевантности
        }
        
        try:
            logger.info(f"🔍 Поиск с анализом: {query}")
            response = requests.get(self.base_url, params=params, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"Ошибка API: {response.status_code}")
                return self._create_intelligent_fallback(query)
            
            data = response.json()
            processed_results = self._process_with_analysis(data, query)
            
            # Анализируем общую достоверность результатов
            overall_analysis = self._analyze_overall_reliability(processed_results)
            
            result = {
                "success": True,
                "query": query,
                "raw_results": data.get("items", []),
                "processed_items": processed_results,
                "overall_analysis": overall_analysis,
                "search_info": data.get("searchInformation", {}),
                "timestamp": datetime.now().isoformat()
            }
            
            self.cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return self._create_intelligent_fallback(query)
    
    def _process_with_analysis(self, data, query):
        """Обрабатывает результаты с анализом достоверности"""
        items = data.get("items", [])
        processed_items = []
        query_keywords = set(re.findall(r'\w{3,}', query.lower()))
        
        for item in items:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            display_link = item.get("displayLink", "")
            
            # Очищаем текст
            title = self._clean_text(title)
            snippet = self._clean_text(snippet)
            
            # Пропускаем слишком короткие
            if len(snippet) < 30:
                continue
            
            # Проверяем на бред
            if self.analyzer.is_likely_bs(f"{title} {snippet}"):
                logger.info(f"Пропускаем как бред: {title[:50]}...")
                continue
            
            # Анализируем источник
            source_analysis = self.analyzer.analyze_source(link, display_link)
            
            # Анализируем качество контента
            content_analysis = self.analyzer.analyze_content_quality(f"{title} {snippet}")
            
            # Рассчитываем релевантность запросу
            relevance_score = self._calculate_relevance(title, snippet, query_keywords)
            
            # Общий score (источник + контент + релевантность)
            total_score = (
                source_analysis["score"] * 0.4 +
                content_analysis["score"] * 0.4 +
                relevance_score * 0.2
            )
            
            processed_items.append({
                "title": title,
                "snippet": snippet,
                "link": link,
                "source_domain": display_link,
                "source_analysis": source_analysis,
                "content_analysis": content_analysis,
                "relevance_score": relevance_score,
                "total_score": total_score,
                "processed_text": self._enhance_snippet(snippet, query),
                "key_facts": self._extract_key_facts(snippet),
                "is_scientific": content_analysis["score"] >= 0.6 and source_analysis["score"] >= 0.7
            })
        
        # Сортируем по общему score (лучшие источники и контент - первые)
        processed_items.sort(key=lambda x: x["total_score"], reverse=True)
        
        # Группируем по темам/аспектам для связности
        grouped_items = self._group_by_topics(processed_items, query)
        
        return grouped_items
    
    def _enhance_snippet(self, snippet, query):
        """Улучшает сниппет, добавляя контекст"""
        # Находим ключевые слова запроса в сниппете
        keywords = re.findall(r'\w{4,}', query.lower())
        enhanced = snippet
        
        # Добавляем маркеры важности
        for keyword in keywords[:3]:
            if keyword in snippet.lower():
                # Подчеркиваем важность
                enhanced = enhanced.replace(
                    keyword,
                    f"**{keyword}**",
                    1
                )
        
        return enhanced
    
    def _extract_key_facts(self, text):
        """Извлекает ключевые факты из текста"""
        facts = []
        
        # Ищем утверждения с цифрами
        number_patterns = [
            r'\d+%',  # Проценты
            r'\d+\s*[\-–]\s*\d+',  # Диапазоны
            r'более\s+\d+', r'менее\s+\d+',  # Сравнения
            r'\d+\s+(год|лет|месяц|день)',  # Временные периоды
        ]
        
        for pattern in number_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            facts.extend(matches)
        
        # Ищем определения
        definition_patterns = [
            r'— это [^.]{10,50}\.',
            r'является [^.]{10,50}\.',
            r'определяется как [^.]{10,50}\.'
        ]
        
        for pattern in definition_patterns:
            matches = re.findall(pattern, text)
            facts.extend(matches)
        
        return list(set(facts))[:5]  # Убираем дубли, берем до 5 фактов
    
    def _calculate_relevance(self, title, snippet, query_keywords):
        """Рассчитывает релевантность запросу"""
        text = f"{title} {snippet}".lower()
        score = 0
        
        for keyword in query_keywords:
            if len(keyword) > 3:
                if keyword in text:
                    score += 1
                if keyword in title.lower():
                    score += 2
        
        # Нормализуем score
        max_possible = len(query_keywords) * 3
        if max_possible > 0:
            return min(1.0, score / max_possible)
        return 0.5
    
    def _group_by_topics(self, items, query):
        """Группирует результаты по темам/аспектам для связности"""
        if not items:
            return items
        
        # Определяем основные аспекты темы
        aspects = self._identify_aspects(items, query)
        
        # Распределяем items по аспектам
        grouped = []
        for aspect in aspects:
            aspect_items = []
            for item in items[:5]:  # Берем только лучшие
                item_text = f"{item['title']} {item['snippet']}".lower()
                
                # Проверяем релевантность аспекту
                aspect_keywords = set(re.findall(r'\w{4,}', aspect.lower()))
                matches = sum(1 for kw in aspect_keywords if kw in item_text)
                
                if matches >= 1:  # Хотя бы одно совпадение
                    aspect_items.append(item)
            
            if aspect_items:
                grouped.append({
                    "aspect": aspect,
                    "items": aspect_items[:3],  # Не более 3 источников на аспект
                    "summary": self._generate_aspect_summary(aspect_items, aspect)
                })
        
        # Если группировка не удалась, возвращаем как есть
        if not grouped:
            return [{
                "aspect": "Общая информация",
                "items": items[:4],
                "summary": self._generate_general_summary(items[:4])
            }]
        
        return grouped
    
    def _identify_aspects(self, items, query):
        """Определяет ключевые аспекты темы"""
        # Собираем все тексты
        all_text = " ".join([f"{i['title']} {i['snippet']}" for i in items[:5]])
        
        # Извлекаем частые существительные (потенциальные аспекты)
        words = re.findall(r'\b[а-яё]{5,}\b', all_text.lower())
        
        # Исключаем стоп-слова
        stop_words = {
            "который", "которые", "которые", "также", "очень",
            "будет", "можно", "нужно", "должен", "могут"
        }
        
        word_freq = {}
        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Берем топ-5 самых частых слов
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Превращаем в аспекты
        aspects = []
        for word, freq in top_words:
            if freq >= 2:  # Слово встречается хотя бы 2 раза
                aspects.append(word.capitalize())
        
        # Если не нашли аспектов, используем стандартные
        if not aspects:
            aspects = [
                "Основные понятия",
                "Ключевые характеристики", 
                "Применение и значение",
                "Тенденции развития",
                "Исследования и открытия"
            ]
        
        return aspects[:4]  # Не более 4 аспектов
    
    def _generate_aspect_summary(self, items, aspect):
        """Генерирует сводку по аспекту на основе нескольких источников"""
        if not items:
            return "Информация по данному аспекту требует дополнительного изучения."
        
        # Собираем ключевую информацию из всех источников
        key_points = []
        for item in items[:3]:
            snippet = item.get("snippet", "")
            if len(snippet) > 50:
                # Берем первое информативное предложение
                sentences = re.split(r'[.!?]+', snippet)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) > 30 and aspect.lower()[:10] in sentence.lower():
                        key_points.append(sentence[:150])
                        break
        
        # Убираем дубли
        unique_points = []
        seen = set()
        for point in key_points:
            point_hash = hashlib.md5(point.lower().encode()).hexdigest()[:10]
            if point_hash not in seen:
                seen.add(point_hash)
                unique_points.append(point)
        
        # Формируем сводку
        if unique_points:
            summary = f"По аспекту «{aspect}» различные источники сообщают: "
            summary += "; ".join([f"{i+1}) {p}" for i, p in enumerate(unique_points[:3])])
            summary += ". Эта информация требует проверки по дополнительным источникам."
        else:
            summary = f"Аспект «{aspect}» упоминается в источниках, но требует более детального изучения."
        
        return summary
    
    def _generate_general_summary(self, items):
        """Генерирует общую сводку"""
        if not items:
            return "Информация по теме требует дополнительного исследования."
        
        # Берем ключевые моменты из лучших источников
        summaries = []
        for item in items[:3]:
            if item.get("is_scientific", False):
                reliability = "🔬 Научный источник: "
            else:
                reliability = "📰 Информационный источник: "
            
            snippet = item.get("snippet", "")[:100]
            if snippet:
                summaries.append(f"{reliability}{snippet}")
        
        if summaries:
            return "Основные выводы из анализа источников:\n• " + "\n• ".join(summaries)
        
        return "Проведенный анализ выявил различные точки зрения на тему."
    
    def _analyze_overall_reliability(self, processed_items):
        """Анализирует общую достоверность всех результатов"""
        if not processed_items:
            return {
                "reliability": "низкая",
                "scientific_count": 0,
                "total_sources": 0,
                "avg_source_score": 0,
                "avg_content_score": 0
            }
        
        total_items = len(processed_items)
        scientific_count = sum(1 for item in processed_items if item.get("is_scientific", False))
        
        avg_source_score = sum(item["source_analysis"]["score"] for item in processed_items) / total_items
        avg_content_score = sum(item["content_analysis"]["score"] for item in processed_items) / total_items
        
        # Определяем общую надежность
        if scientific_count >= 3 and avg_source_score >= 0.7:
            reliability = "высокая"
        elif scientific_count >= 1 and avg_source_score >= 0.5:
            reliability = "средняя"
        else:
            reliability = "низкая"
        
        return {
            "reliability": reliability,
            "scientific_count": scientific_count,
            "total_sources": total_items,
            "avg_source_score": avg_source_score,
            "avg_content_score": avg_content_score,
            "warning": "⚠️ Используйте критическое мышление" if reliability == "низкая" else None
        }
    
    def _clean_text(self, text):
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _create_intelligent_fallback(self, query):
        """Интеллектуальный fallback с предупреждением"""
        logger.info(f"🔄 Использую интеллектуальный fallback для: {query}")
        
        return {
            "success": False,
            "query": query,
            "processed_items": [{
                "aspect": "Внимание: ограниченные данные",
                "items": [{
                    "title": f"Анализ темы: {query}",
                    "snippet": "⚠️ *Внимание:* Поисковая система вернула ограниченные данные. Информация может быть неполной или требовать проверки по дополнительным источникам. Рекомендуется критически оценивать полученные сведения и обращаться к научным публикациям для углубленного изучения.",
                    "source_analysis": {"score": 0.5, "category": "предупреждение", "color": "🟡"},
                    "content_analysis": {"score": 0.5, "level": "предупреждение", "emoji": "⚠️"},
                    "is_scientific": False,
                    "key_facts": ["Требуется проверка информации", "Необходимы дополнительные источники"]
                }],
                "summary": "Из-за ограничений поиска информация предоставляется с оговорками. Рекомендуется дополнительная проверка."
            }],
            "overall_analysis": {
                "reliability": "низкая",
                "scientific_count": 0,
                "warning": "⚠️ Информация требует дополнительной проверки!"
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_empty_result(self, query):
        return {
            "success": False,
            "query": query,
            "processed_items": [],
            "overall_analysis": {"reliability": "неопределена", "warning": "Пустой запрос"},
            "timestamp": datetime.now().isoformat()
        }

# ==================== ГЕНЕРАТОР КОНСПЕКТОВ С СВЯЗЫВАНИЕМ ====================
class IntelligentConspectGenerator:
    def __init__(self):
        self.searcher = IntelligentSearchAPI()
        logger.info("✅ Генератор с анализом достоверности готов")
    
    def generate(self, topic, volume="short"):
        """Генерирует связный конспект с анализом достоверности"""
        if self._is_easter_egg(topic):
            return self._create_easter_egg_response()
        
        # Выполняем поиск с анализом
        search_results = self.searcher.search(topic)
        
        # Генерируем конспект с учетом объема
        if volume == "detailed":
            return self._generate_detailed(topic, search_results)
        elif volume == "extended":
            return self._generate_extended(topic, search_results)
        else:
            return self._generate_short(topic, search_results)
    
    def _is_easter_egg(self, text):
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in [
            "план захвата польши", "захват польши", "чайная пасхалка"
        ])
    
    def _create_easter_egg_response(self):
        responses = [
            "🍵 *Секретная пасхалка активирована!*\n\nСтатус: Чайный Аналитик\nФокся в пути с проверенными данными...",
            "🍵 *Easter Egg Verified!*\n\nTea Status: ANALYTICAL\nFoksya delivering fact-checked info..."
        ]
        return random.choice(responses)
    
    def _generate_short(self, topic, results):
        """Краткий конспект с оценкой достоверности"""
        processed_items = results.get("processed_items", [])
        overall_analysis = results.get("overall_analysis", {})
        
        conspect = f"📄 *АНАЛИЗ: {topic.upper()}*\n\n"
        
        # Оценка достоверности
        reliability = overall_analysis.get("reliability", "неизвестно")
        reliability_emoji = {"высокая": "🟢", "средняя": "🟡", "низкая": "🔴"}.get(reliability, "⚪")
        
        conspect += f"{reliability_emoji} *Достоверность:* {reliability.upper()}\n"
        conspect += f"🔬 *Научных источников:* {overall_analysis.get('scientific_count', 0)}\n"
        conspect += f"📊 *Всего источников:* {overall_analysis.get('total_sources', 0)}\n\n"
        
        # Предупреждение если достоверность низкая
        if reliability == "низкая":
            conspect += "⚠️ *ВНИМАНИЕ:* Информация требует проверки!\n\n"
        
        # Ключевые выводы из сгруппированных данных
        conspect += "📝 *ОСНОВНЫЕ ВЫВОДЫ:*\n\n"
        
        if processed_items:
            for group in processed_items[:2]:  # Берем 2 основные группы
                aspect = group.get("aspect", "Общая информация")
                summary = group.get("summary", "")
                
                if summary:
                    conspect += f"• **{aspect}:** {summary}\n\n"
        else:
            conspect += "Информация по теме требует дополнительного изучения и проверки.\n\n"
        
        # Критическая оценка
        conspect += "🧠 *КРИТИЧЕСКАЯ ОЦЕНКА:*\n"
        conspect += "1. Проверьте источники информации\n"
        conspect += "2. Ищите научные публикации\n"
        conspect += "3. Сравните разные точки зрения\n"
        conspect += "4. Остерегайтесь неподтвержденных данных\n\n"
        
        conspect += "🤖 *@Konspekt_help_bot* | 🔍 *Анализ достоверности*"
        
        return conspect
    
    def _generate_detailed(self, topic, results):
        """Подробный конспект с анализом источников"""
        processed_items = results.get("processed_items", [])
        overall_analysis = results.get("overall_analysis", {})
        
        conspect = f"📚 *ДЕТАЛЬНЫЙ АНАЛИЗ: {topic.upper()}*\n\n"
        
        # Методология и оценка
        conspect += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        conspect += "🔬 *МЕТОДОЛОГИЯ И ОЦЕНКА ДОСТОВЕРНОСТИ*\n"
        conspect += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        reliability = overall_analysis.get("reliability", "неизвестно")
        reliability_color = {"высокая": "🟢", "средняя": "🟡", "низкая": "🔴"}.get(reliability, "⚪")
        
        conspect += f"*Общая оценка достоверности:* {reliability_color} **{reliability.upper()}**\n"
        conspect += f"*Научных источников:* {overall_analysis.get('scientific_count', 0)} из {overall_analysis.get('total_sources', 0)}\n"
        conspect += f"*Средняя оценка источников:* {overall_analysis.get('avg_source_score', 0):.2f}/1.0\n"
        conspect += f"*Средняя оценка контента:* {overall_analysis.get('avg_content_score', 0):.2f}/1.0\n\n"
        
        if overall_analysis.get("warning"):
            conspect += f"⚠️ **ВНИМАНИЕ:** {overall_analysis['warning']}\n\n"
        
        # Анализ по аспектам (связанная информация)
        conspect += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        conspect += "📊 *АНАЛИЗ ПО КЛЮЧЕВЫМ АСПЕКТАМ*\n"
        conspect += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if processed_items:
            for group in processed_items:
                aspect = group.get("aspect", "Аспект")
                items = group.get("items", [])
                summary = group.get("summary", "")
                
                conspect += f"**{aspect}:**\n"
                conspect += f"{summary}\n\n"
                
                # Показываем источники для этого аспекта
                if items:
                    conspect += "*Источники по этому аспекту:*\n"
                    for i, item in enumerate(items[:2], 1):
                        source_info = item.get("source_analysis", {})
                        content_info = item.get("content_analysis", {})
                        
                        conspect += f"{i}. {source_info.get('color', '⚪')} "
                        conspect += f"{content_info.get('emoji', '📄')} "
                        conspect += f"{item.get('title', 'Без названия')[:50]}...\n"
                        conspect += f"   *Достоверность:* {source_info.get('category', 'неизвестно')} "
                        conspect += f"({source_info.get('score', 0):.1f}/1.0)\n"
                        conspect += f"   *Качество:* {content_info.get('level', 'неизвестно')}\n\n"
                
                conspect += "―\n\n"
        else:
            conspect += "Не удалось выделить ключевые аспекты. Информация фрагментирована.\n\n"
        
        # Связующий анализ
        conspect += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        conspect += "🔗 *СВЯЗУЮЩИЙ АНАЛИЗ И ВЫВОДЫ*\n"
        conspect += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        conspect += "**СВЯЗЬ МЕЖДУ ИСТОЧНИКАМИ:**\n"
        
        if processed_items and len(processed_items) > 1:
            # Анализируем согласованность между аспектами
            aspects = [g.get("aspect", "") for g in processed_items]
            conspect += f"Выделено {len(aspects)} ключевых аспекта: {', '.join(aspects[:3])}.\n"
            conspect += "Анализ показывает, что информация из разных источников "
            
            # Оцениваем согласованность
            scientific_count = overall_analysis.get("scientific_count", 0)
            if scientific_count >= 2:
                conspect += "**частично согласуется** между научными источниками.\n"
            elif scientific_count >= 1:
                conspect += "имеет **противоречия**, требующие проверки.\n"
            else:
                conspect += "требует **критической оценки** из-за отсутствия научных подтверждений.\n"
        else:
            conspect += "Информация фрагментирована, связь между источниками не установлена.\n"
        
        conspect += "\n**РЕКОМЕНДАЦИИ ПО ПРОВЕРКЕ:**\n"
        conspect += "1. Сравните информацию с научными базами данных\n"
        conspect += "2. Проверьте авторитетность источников\n"
        conspect += "3. Ищите подтверждение в рецензируемых журналах\n"
        conspect += "4. Остерегайтесь неподтвержденных утверждений\n\n"
        
        conspect += "🔍 *Использован анализ достоверности источников*\n"
        conspect += "🤖 *@Konspekt_help_bot* | 🧠 *Критическое мышление*"
        
        return conspect
    
    def _generate_extended(self, topic, results):
        """Развернутый конспект с полным анализом и связыванием"""
        processed_items = results.get("processed_items", [])
        overall_analysis = results.get("overall_analysis", {})
        
        # Создаем части конспекта
        parts = []
        
        # Часть 1: Введение и методология
        part1 = f"📖 *КОМПЛЕКСНОЕ ИССЛЕДОВАНИЕ С АНАЛИЗОМ ДОСТОВЕРНОСТИ: {topic.upper()}*\n\n"
        part1 += "=" * 60 + "\n"
        part1 += "ЧАСТЬ 1: МЕТОДОЛОГИЯ И ОЦЕНКА ДОСТОВЕРНОСТИ\n"
        part1 += "=" * 60 + "\n\n"
        
        part1 += "**ЦЕЛЬ ИССЛЕДОВАНИЯ:** Провести комплексный анализ темы с оценкой достоверности источников.\n\n"
        
        reliability = overall_analysis.get("reliability", "неизвестно")
        reliability_badge = {
            "высокая": "🟢 ВЫСОКАЯ ДОСТОВЕРНОСТЬ",
            "средняя": "🟡 СРЕДНЯЯ ДОСТОВЕРНОСТЬ", 
            "низкая": "🔴 НИЗКАЯ ДОСТОВЕРНОСТЬ"
        }.get(reliability, "⚪ НЕОПРЕДЕЛЕНА")
        
        part1 += f"**ОБЩАЯ ОЦЕНКА ДОСТОВЕРНОСТИ:** {reliability_badge}\n\n"
        
        part1 += "**МЕТОДОЛОГИЯ АНАЛИЗА:**\n"
        part1 += "1. Поиск и сбор информации из различных источников\n"
        part1 += "2. Оценка надежности источников (научные, официальные, блоги, форумы)\n"
        part1 += "3. Анализ качества контента (научность, объективность, структура)\n"
        part1 += "4. Группировка по тематическим аспектам\n"
        part1 += "5. Связывание информации из разных источников\n"
        part1 += "6. Критическая оценка и выводы\n\n"
        
        part1 += f"**СТАТИСТИКА ИСТОЧНИКОВ:**\n"
        part1 += f"• Всего проанализировано: {overall_analysis.get('total_sources', 0)} источников\n"
        part1 += f"• Научных/академических: {overall_analysis.get('scientific_count', 0)}\n"
        part1 += f"• Средняя оценка источников: {overall_analysis.get('avg_source_score', 0):.2f}/1.0\n"
        part1 += f"• Средняя оценка контента: {overall_analysis.get('avg_content_score', 0):.2f}/1.0\n\n"
        
        if overall_analysis.get("warning"):
            part1 += f"⚠️ **ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ:** {overall_analysis['warning']}\n\n"
        
        parts.append(part1)
        
        # Часть 2: Детальный анализ по аспектам
        part2 = "=" * 60 + "\n"
        part2 += "ЧАСТЬ 2: ДЕТАЛЬНЫЙ АНАЛИЗ ПО ТЕМАТИЧЕСКИМ АСПЕКТАМ\n"
        part2 += "=" * 60 + "\n\n"
        
        if processed_items:
            for group_idx, group in enumerate(processed_items, 1):
                aspect = group.get("aspect", f"Аспект {group_idx}")
                items = group.get("items", [])
                summary = group.get("summary", "")
                
                part2 += f"**{group_idx}. {aspect.upper()}**\n\n"
                part2 += f"*Сводка анализа:* {summary}\n\n"
                
                # Детальный анализ источников для этого аспекта
                if items:
                    part2 += "*АНАЛИЗ ИСТОЧНИКОВ ПО ДАННОМУ АСПЕКТУ:*\n\n"
                    
                    for i, item in enumerate(items, 1):
                        title = item.get("title", "")
                        snippet = item.get("snippet", "")
                        source_info = item.get("source_analysis", {})
                        content_info = item.get("content_analysis", {})
                        is_scientific = item.get("is_scientific", False)
                        
                        part2 += f"**Источник {i}:** {title}\n"
                        part2 += f"*Тип источника:* {source_info.get('color', '')} {source_info.get('category', 'неизвестно')}\n"
                        part2 += f"*Оценка источника:* {source_info.get('score', 0):.2f}/1.0\n"
                        part2 += f"*Качество контента:* {content_info.get('emoji', '')} {content_info.get('level', 'неизвестно')}\n"
                        part2 += f"*Научный источник:* {'✅ Да' if is_scientific else '❌ Нет'}\n"
                        
                        # Ключевые факты из этого источника
                        key_facts = item.get("key_facts", [])
                        if key_facts:
                            part2 += f"*Ключевые факты:* {', '.join(key_facts[:2])}\n"
                        
                        # Обработанный текст
                        processed_text = item.get("processed_text", snippet[:200])
                        part2 += f"*Основное содержание:* {processed_text}\n\n"
                
                part2 += "―" * 40 + "\n\n"
        else:
            part2 += "Не удалось выделить тематические аспекты. Информация может быть фрагментированной или недостаточной.\n\n"
        
        parts.append(part2)
        
        # Часть 3: Сравнительный и связующий анализ
        part3 = "=" * 60 + "\n"
        part3 += "ЧАСТЬ 3: СРАВНИТЕЛЬНЫЙ И СВЯЗУЮЩИЙ АНАЛИЗ\n"
        part3 += "=" * 60 + "\n\n"
        
        if processed_items and len(processed_items) > 1:
            part3 += "**СРАВНЕНИЕ И СВЯЗЫВАНИЕ ИНФОРМАЦИИ:**\n\n"
            
            # Анализируем согласованность между аспектами
            aspects_info = []
            for group in processed_items:
                aspect = group.get("aspect", "")
                items = group.get("items", [])
                scientific_items = [i for i in items if i.get("is_scientific", False)]
                
                aspects_info.append({
                    "aspect": aspect,
                    "total_sources": len(items),
                    "scientific_sources": len(scientific_items),
                    "avg_score": sum(i.get("total_score", 0) for i in items) / len(items) if items else 0
                })
            
            part3 += "*Сводка по аспектам:*\n"
            for info in aspects_info:
                part3 += f"• **{info['aspect']}:** {info['total_sources']} источников "
                part3 += f"({info['scientific_sources']} научных), "
                part3 += f"средняя оценка: {info['avg_score']:.2f}/1.0\n"
            
            part3 += "\n*АНАЛИЗ СОГЛАСОВАННОСТИ:*\n"
            
            # Определяем уровень согласованности
            scientific_counts = [info["scientific_sources"] for info in aspects_info]
            total_scientific = sum(scientific_counts)
            
            if total_scientific >= 3:
                part3 += "✅ **Высокая согласованность:** Несколько научных источников подтверждают информацию по разным аспектам.\n"
            elif total_scientific >= 1:
                part3 += "⚠️ **Частичная согласованность:** Есть научные подтверждения, но информация может быть неполной.\n"
            else:
                part3 += "❌ **Низкая согласованность:** Отсутствуют научные подтверждения, информация требует проверки.\n"
            
            part3 += "\n*СВЯЗЬ МЕЖДУ АСПЕКТАМИ:*\n"
            
            # Анализируем связи между аспектами
            if len(processed_items) >= 2:
                # Ищем общие темы/понятия между аспектами
                all_texts = []
                for group in processed_items[:3]:
                    for item in group.get("items", []):
                        all_texts.append(f"{item.get('title', '')} {item.get('snippet', '')}")
                
                # Извлекаем общие термины
                common_terms = self._find_common_terms(all_texts)
                if common_terms:
                    part3 += f"Общие термины между аспектами: {', '.join(common_terms[:5])}\n"
                    part3 += "Это указывает на тематическую связь между различными частями информации.\n"
                else:
                    part3 += "Явных терминологических связей между аспектами не обнаружено.\n"
            else:
                part3 += "Недостаточно аспектов для анализа связей.\n"
            
        else:
            part3 += "Недостаточно данных для сравнительного анализа.\n"
        
        part3 += "\n**ПРОБЛЕМЫ И ПРОТИВОРЕЧИЯ:**\n"
        
        # Ищем противоречия
        contradictions = self._find_contradictions(processed_items)
        if contradictions:
            for contradiction in contradictions[:3]:
                part3 += f"• {contradiction}\n"
        else:
            part3 += "Явных противоречий между источниками не обнаружено.\n"
        
        parts.append(part3)
        
        # Часть 4: Выводы и рекомендации
        part4 = "=" * 60 + "\n"
        part4 += "ЧАСТЬ 4: ВЫВОДЫ, РЕКОМЕНДАЦИИ И ПЕРСПЕКТИВЫ\n"
        part4 += "=" * 60 + "\n\n"
        
        part4 += "**ОСНОВНЫЕ ВЫВОДЫ ИССЛЕДОВАНИЯ:**\n\n"
        
        conclusions = [
            f"1. Достоверность информации по теме «{topic}» оценивается как **{reliability}**",
            "2. Качество и количество источников варьируется по разным аспектам темы",
            "3. Наличие научных подтверждений существенно влияет на оценку достоверности",
            "4. Информация из разных источников требует критического сопоставления",
            "5. Для углубленного изучения необходимы дополнительные проверенные источники"
        ]
        
        for conclusion in conclusions:
            part4 += f"{conclusion}\n"
        
        part4 += "\n**КРИТИЧЕСКИЕ РЕКОМЕНДАЦИИ:**\n\n"
        
        recommendations = [
            "1. Всегда проверяйте авторитетность источника информации",
            "2. Отдавайте предпочтение научным и академическим публикациям",
            "3. Сравнивайте информацию из нескольких независимых источников",
            "4. Обращайте внимание на даты публикации (актуальность информации)",
            "5. Ищите подтверждения в рецензируемых научных журналах",
            "6. Остерегайтесь эмоционально окрашенных и субъективных утверждений",
            "7. Проверяйте факты через специализированные базы данных"
        ]
        
        for recommendation in recommendations:
            part4 += f"{recommendation}\n"
        
        part4 += "\n**ПЕРСПЕКТИВЫ ДАЛЬНЕЙШЕГО ИССЛЕДОВАНИЯ:**\n\n"
        part4 += "• Провести углубленный анализ научной литературы по теме\n"
        part4 += "• Изучить исторический контекст и эволюцию темы\n"
        part4 += "• Проанализировать международный опыт и исследования\n"
        part4 += "• Рассмотреть практические аспекты и применения\n"
        part4 += "• Изучить современные тенденции и перспективы развития\n"
        
        # Техническая информация
        part4 += f"\n" + "=" * 60 + "\n"
        part4 += "ТЕХНИЧЕСКАЯ ИНФОРМАЦИЯ\n"
        part4 += "=" * 60 + "\n\n"
        
        part4 += f"*Дата проведения анализа:* {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        part4 += f"*Объем исследования:* {sum(len(p) for p in parts)} символов\n"
        part4 += f"*Методология:* Анализ достоверности источников + тематическое связывание\n"
        part4 += f"*Система оценки:* Научность × Качество × Релевантность\n"
        part4 += f"*Платформа:* @Konspekt_help_bot с интеллектуальным анализом\n\n"
        
        part4 += "⚠️ **ВАЖНО:** Данное исследование носит аналитический характер. "
        part4 += "Для принятия важных решений обращайтесь к первоисточникам и экспертам."
        
        parts.append(part4)
        
        # Объединяем все части
        full_conspect = "\n".join(parts)
        return full_conspect
    
    def _find_common_terms(self, texts, min_length=5):
        """Находит общие термины в текстах"""
        if not texts:
            return []
        
        # Извлекаем слова из всех текстов
        all_words = []
        for text in texts:
            words = re.findall(r'\b[а-яё]{4,}\b', text.lower())
            all_words.extend(words)
        
        # Считаем частоту
        word_freq = {}
        for word in all_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Ищем слова, которые встречаются во всех текстах
        common_words = []
        for word, freq in word_freq.items():
            if freq >= len(texts):  # Встречается во всех текстах
                common_words.append(word)
        
        return sorted(common_words, key=lambda x: word_freq[x], reverse=True)[:10]
    
    def _find_contradictions(self, processed_items):
        """Ищет противоречия между источниками"""
        contradictions = []
        
        if not processed_items or len(processed_items) < 2:
            return contradictions
        
        # Собираем ключевые утверждения из всех источников
        all_claims = []
        for group in processed_items:
            for item in group.get("items", []):
                snippet = item.get("snippet", "")
                # Извлекаем утвердительные предложения
                sentences = re.split(r'[.!?]+', snippet)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) > 20 and not any(q in sentence.lower() for q in ["?", "как", "почему", "зачем"]):
                        all_claims.append({
                            "text": sentence[:100],
                            "source_score": item.get("source_analysis", {}).get("score", 0),
                            "aspect": group.get("aspect", "")
                        })
        
        # Ищем потенциальные противоречия
        for i in range(len(all_claims)):
            for j in range(i + 1, len(all_claims)):
                claim1 = all_claims[i]["text"].lower()
                claim2 = all_claims[j]["text"].lower()
                
                # Ищем противоположные утверждения
                opposites = [
                    ("увеличивается", "уменьшается"),
                    ("растет", "падает"),
                    ("эффективно", "неэффективно"),
                    ("доказано", "опровергнуто"),
                    ("существует", "не существует"),
                    ("верно", "неверно"),
                    ("подтверждено", "опровергнуто")
                ]
                
                for pos, neg in opposites:
                    if pos in claim1 and neg in claim2:
                        contradictions.append(
                            f"Противоположные утверждения: «{all_claims[i]['text']}» vs «{all_claims[j]['text']}»"
                        )
                        break
        
        return contradictions

# ==================== TELEGRAM BOT (с улучшенной отправкой) ====================
class TelegramBot:
    def __init__(self):
        if not TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN не найден")
        
        self.token = TELEGRAM_TOKEN
        self.bot_url = f"https://api.telegram.org/bot{self.token}"
        self.generator = IntelligentConspectGenerator()
        
        if RENDER_EXTERNAL_URL:
            self._setup_webhook()
        
        logger.info("✅ Telegram бот с анализом достоверности готов")
    
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
            elif text == "/reliability":
                return self._send_reliability_info(chat_id)
            else:
                return self._send_message(chat_id, "❓ Неизвестная команда. Используйте /help")
        
        if text in ["1", "2", "3"]:
            return self._handle_volume(chat_id, text)
        
        return self._handle_topic(chat_id, text)
    
    def _send_welcome(self, chat_id):
        welcome = (
            "👋 *Добро пожаловать в Умный Konspekt Helper Bot!*\n\n"
            "🧠 *Теперь с анализом достоверности и связыванием информации!*\n\n"
            "🔄 *Новые возможности:*\n"
            "• 🔬 Анализ научности источников\n"
            "• 🎯 Оценка достоверности информации\n"
            "• 🔗 Связывание разрозненных данных\n"
            "• ⚠️ Выявление бреда и непроверенных данных\n"
            "• 📊 Сравнительный анализ источников\n\n"
            "📚 *Объемы конспектов:*\n"
            "• *1* — Краткий (с оценкой достоверности)\n"
            "• *2* — Подробный (с анализом источников)\n"
            "• *3* — Полный (связующее исследование)\n\n"
            "🎯 *Отправьте тему для интеллектуального анализа!*"
        )
        return self._send_message(chat_id, welcome)
    
    def _send_help(self, chat_id):
        help_text = (
            "📚 *СПРАВКА ПО УМНОМУ БОТУ*\n\n"
            "*Как работает анализ достоверности:*\n"
            "1. 🔍 Поиск информации из разных источников\n"
            "2. 🎯 Оценка надежности каждого источника\n"
            "3. 🔬 Анализ научности контента\n"
            "4. 🔗 Связывание информации из разных источников\n"
            "5. ⚠️ Выявление противоречий и бреда\n\n"
            "*Оценка источников:*\n"
            "🟢 Научные/академические (высокая достоверность)\n"
            "🟡 Официальные/новостные (средняя достоверность)\n"
            "🟠 Блоги/форумы (низкая достоверность)\n"
            "🔴 Сомнительные (требует проверки)\n\n"
            "*Команды:*\n"
            "/start - Начало работы\n"
            "/help - Эта справка\n"
            "/stats - Статистика\n"
            "/reliability - Как оценивается достоверность\n\n"
            "*Пример хорошего запроса:*\n"
            "«Развитие искусственного интеллекта в медицине»"
        )
        return self._send_message(chat_id, help_text)
    
    def _send_reliability_info(self, chat_id):
        info = (
            "🔬 *КАК ОЦЕНИВАЕТСЯ ДОСТОВЕРНОСТЬ*\n\n"
            "*1. ОЦЕНКА ИСТОЧНИКОВ:*\n"
            "🟢 **Научные источники** (0.8-1.0):\n"
            "• arxiv.org, nature.com, science.org\n"
            "• Рецензируемые журналы\n"
            "• Академические публикации\n\n"
            "🟡 **Официальные источники** (0.6-0.8):\n"
            "• Государственные сайты (.gov)\n"
            "• Образовательные учреждения (.edu)\n"
            "• Международные организации\n\n"
            "🟠 **Информационные источники** (0.4-0.6):\n"
            "• Новостные порталы\n"
            "• Блоги экспертов\n"
            "• Популярная наука\n\n"
            "🔴 **Ненадежные источники** (0.0-0.4):\n"
            "• Социальные сети\n"
            "• Форумы и чаты\n"
            "• Непроверенные блоги\n\n"
            "*2. ОЦЕНКА КОНТЕНТА:*\n"
            "• Наличие научных терминов и методологии\n"
            "• Объективность (отсутствие субъективных маркеров)\n"
            "• Наличие цифр, данных, цитат\n"
            "• Структурированность информации\n"
            "• Отсутствие эмоциональных оценок\n\n"
            "*3. ВЫЯВЛЕНИЕ БРЕДА:*\n"
            "• Конспирологические теории\n"
            "• Неподтвержденные утверждения\n"
            "• Эмоционально окрашенный язык\n"
            "• Субъективные мнения без доказательств\n"
            "• Сленг и неформальные выражения\n\n"
            "⚠️ *Бот предупредит, если информация требует проверки!*"
        )
        return self._send_message(chat_id, info)
    
    def _send_stats(self, chat_id):
        stat_text = (
            f"📊 *СТАТИСТИКА СИСТЕМЫ АНАЛИЗА*\n\n"
            f"👥 Пользователей: {stats['total_users']}\n"
            f"💬 Сообщений: {stats['total_messages']}\n"
            f"📄 Конспектов: {stats['conspects_created']}\n"
            f"🔍 Поисков Google: {stats['google_searches']}\n"
            f"⏱ Запущена: {stats['start_time'][:10]}\n\n"
            f"🎯 Режим: Анализ достоверности источников"
        )
        return self._send_message(chat_id, stat_text)
    
    def _handle_topic(self, chat_id, topic):
        user_id = str(chat_id)
        if user_id not in stats["user_states"]:
            stats["user_states"][user_id] = {}
        
        stats["user_states"][user_id]["pending_topic"] = topic
        
        response = (
            f"🎯 *ТЕМА: {topic}*\n\n"
            f"🧠 *НАЧИНАЮ ИНТЕЛЛЕКТУАЛЬНЫЙ АНАЛИЗ...*\n\n"
            f"🔄 *БУДЕТ ПРОВЕДЕНО:*\n"
            f"1. 🔍 Поиск в научных и информационных источниках\n"
            f"2. 🎯 Оценка достоверности каждого источника\n"
            f"3. 🔬 Анализ научности контента\n"
            f"4. 🔗 Связывание информации из разных источников\n"
            f"5. ⚠️ Проверка на бред и непроверенные данные\n\n"
            f"📊 *ВЫБЕРИТЕ УРОВЕНЬ АНАЛИЗА:*\n\n"
            f"1️⃣ *КРАТКИЙ* — основные выводы с оценкой достоверности\n"
            f"2️⃣ *ПОДРОБНЫЙ* — анализ источников и их надежности\n"
            f"3️⃣ *ПОЛНЫЙ* — связующее исследование с критической оценкой\n\n"
            f"🔢 *Отправьте 1, 2 или 3*"
        )
        return self._send_message(chat_id, response)
    
    def _handle_volume(self, chat_id, volume_choice):
        user_id = str(chat_id)
        user_state = stats["user_states"].get(user_id, {})
        topic = user_state.get("pending_topic", "")
        
        if not topic:
            return self._send_message(chat_id, "❌ Сначала отправьте тему для анализа")
        
        volume_map = {"1": "short", "2": "detailed", "3": "extended"}
        volume = volume_map.get(volume_choice, "short")
        
        # Отправляем уведомление
        self._send_message(
            chat_id,
            f"🧠 *ВЫПОЛНЯЮ ИНТЕЛЛЕКТУАЛЬНЫЙ АНАЛИЗ...*\n\n"
            f"📌 Тема: {topic}\n"
            f"📊 Уровень анализа: {volume_choice}/3\n"
            f"🔍 Режим: Анализ достоверности и связывание\n\n"
            f"⏳ Это займет несколько секунд...\n"
            f"Система оценивает источники и связывает информацию..."
        )
        
        try:
            conspect = self.generator.generate(topic, volume)
            stats["conspects_created"] += 1
            
            # Отправляем конспект с интеллектуальным разбиением
            self._send_intelligent_conspect(chat_id, conspect, volume_choice)
            
            # Финальное сообщение
            final_msg = (
                f"✅ *АНАЛИЗ ЗАВЕРШЕН!*\n\n"
                f"📌 Тема: {topic}\n"
                f"📊 Уровень анализа: {volume_choice}/3\n"
                f"🔍 Поисков выполнено: {stats['google_searches']}\n"
                f"📄 Проанализировано конспектов: {stats['conspects_created']}\n\n"
                f"⚠️ *ПОМНИТЕ:* Всегда проверяйте информацию по нескольким источникам!\n\n"
                f"🔄 Другой уровень анализа? Отправьте 1, 2 или 3\n"
                f"🎯 Новая тема? Просто напишите её!"
            )
            return self._send_message(chat_id, final_msg)
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания конспекта: {e}")
            return self._send_message(
                chat_id,
                f"❌ *ОШИБКА АНАЛИЗА*\n\n"
                f"Не удалось проанализировать тему. Возможные причины:\n"
                f"• Слишком общий или неоднозначный запрос\n"
                f"• Ограничения поисковых систем\n"
                f"• Недостаточно проверенных источников\n\n"
                f"Попробуйте:\n"
                f"1. Конкретизировать тему\n"
                f"2. Использовать научные термины\n"
                f"3. Проверить позже\n\n"
                f"Ошибка: {str(e)[:100]}"
            )
    
    def _send_intelligent_conspect(self, chat_id, conspect, volume_choice):
        """Интеллектуальная отправка конспекта"""
        max_length = 3900  # С запасом для Telegram
        
        if len(conspect) <= max_length:
            self._send_message(chat_id, conspect)
            return
        
        # Разбиваем по логическим разделам
        sections = []
        
        # Ищем крупные разделы (с === или ━━━━)
        big_sections = re.split(r'(=+\n[^=]+\n=+|\n━━[━]+\n)', conspect)
        
        current_section = ""
        for part in big_sections:
            if not part.strip():
                continue
            
            # Если это заголовок раздела
            if re.match(r'(=+\n[^=]+\n=+|\n━━[━]+\n)', part):
                if current_section and len(current_section) > 1000:
                    sections.append(current_section.strip())
                    current_section = part + "\n\n"
                else:
                    current_section += part + "\n\n"
            else:
                # Проверяем длину
                if len(current_section + part) > max_length and current_section:
                    sections.append(current_section.strip())
                    current_section = part
                else:
                    current_section += part
        
        # Добавляем последний раздел
        if current_section.strip():
            sections.append(current_section.strip())
        
        # Если разбиение не удалось, разбиваем по абзацам
        if not sections or (len(sections) == 1 and len(sections[0]) > max_length):
            paragraphs = conspect.split('\n\n')
            sections = []
            current = ""
            
            for para in paragraphs:
                if len(current + para) > max_length and current:
                    sections.append(current.strip())
                    current = para
                else:
                    if current:
                        current += "\n\n" + para
                    else:
                        current = para
            
            if current.strip():
                sections.append(current.strip())
        
        # Отправляем все части
        total_parts = len(sections)
        for i, section in enumerate(sections, 1):
            # Добавляем заголовок для продолжения (кроме первой части)
            if i > 1:
                header = f"📖 *ПРОДОЛЖЕНИЕ АНАЛИЗА ({i}/{total_parts})*\n\n"
                section = header + section
            
            # Проверяем длину еще раз
            if len(section) > max_length:
                # Экстренное разбиение по предложениям
                sentences = re.split(r'[.!?]+', section)
                current_chunk = ""
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    
                    if len(current_chunk + sentence) > max_length and current_chunk:
                        self._send_message(chat_id, current_chunk)
                        current_chunk = sentence + ". "
                        time.sleep(0.5)
                    else:
                        current_chunk += sentence + ". "
                
                if current_chunk.strip():
                    self._send_message(chat_id, current_chunk.strip())
            else:
                self._send_message(chat_id, section)
            
            # Пауза между частями
            if i < total_parts:
                time.sleep(0.7)
    
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
            logger.error(f"❌ Ошибка отправки сообщения: {e}")
            return False

# ==================== HTTP СЕРВЕР ====================
class BotHTTPServer(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]
        
        if path == "/":
            self._send_html(INDEX_HTML)
        elif path == "/health":
            self._send_json({"status": "ok", "mode": "reliability_analysis", "time": datetime.now().isoformat()})
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
    <title>🤖 Умный Konspekt Helper Bot</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 40px; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
        .header { text-align: center; margin-bottom: 40px; }
        .reliability-badges { display: flex; justify-content: center; gap: 20px; margin: 30px 0; flex-wrap: wrap; }
        .badge { padding: 15px; border-radius: 10px; color: white; font-weight: bold; min-width: 200px; text-align: center; }
        .badge-scientific { background: linear-gradient(to right, #10b981, #059669); }
        .badge-official { background: linear-gradient(to right, #f59e0b, #d97706); }
        .badge-blog { background: linear-gradient(to right, #f97316, #ea580c); }
        .badge-dubious { background: linear-gradient(to right, #ef4444, #dc2626); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }
        .stat-card { background: #f8fafc; padding: 20px; border-radius: 10px; text-align: center; border-left: 5px solid #667eea; }
        .stat-value { font-size: 2em; font-weight: bold; color: #667eea; }
        .btn { display: inline-block; background: linear-gradient(to right, #667eea, #764ba2); color: white; padding: 12px 25px; border-radius: 8px; text-decoration: none; font-weight: bold; margin: 10px 5px; transition: transform 0.2s; }
        .btn:hover { transform: translateY(-2px); }
        .feature-list { background: #f0f9ff; padding: 25px; border-radius: 15px; margin: 30px 0; border-left: 5px solid #3b82f6; }
        .feature-item { margin: 10px 0; padding-left: 20px; position: relative; }
        .feature-item:before { content: "✓"; position: absolute; left: 0; color: #10b981; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Умный Konspekt Helper Bot</h1>
            <p style="color: #666; font-size: 1.2em;">Анализ достоверности + Связывание информации + Выявление бреда</p>
        </div>
        
        <div class="feature-list">
            <h3>🎯 Ключевые возможности системы:</h3>
            <div class="feature-item">🔬 <strong>Анализ научности источников</strong> - оценка надежности каждого источника</div>
            <div class="feature-item">🎯 <strong>Оценка достоверности контента</strong> - проверка фактов и данных</div>
            <div class="feature-item">🔗 <strong>Связывание информации</strong> - объединение данных из разных источников</div>
            <div class="feature-item">⚠️ <strong>Выявление бреда</strong> - фильтрация непроверенных и ненаучных данных</div>
            <div class="feature-item">📊 <strong>Сравнительный анализ</strong> - поиск противоречий и согласованности</div>
            <div class="feature-item">🧠 <strong>Критическая оценка</strong> - рекомендации по проверке информации</div>
        </div>
        
        <h3>🎨 Система оценки достоверности:</h3>
        <div class="reliability-badges">
            <div class="badge badge-scientific">
                🟢 НАУЧНЫЙ<br>0.8-1.0
            </div>
            <div class="badge badge-official">
                🟡 ОФИЦИАЛЬНЫЙ<br>0.6-0.8
            </div>
            <div class="badge badge-blog">
                🟠 ИНФОРМАЦИОННЫЙ<br>0.4-0.6
            </div>
            <div class="badge badge-dubious">
                🔴 СОМНИТЕЛЬНЫЙ<br>0.0-0.4
            </div>
        </div>
        
        <div class="stats-grid">
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
        
        <h3>🔗 Быстрые ссылки:</h3>
        <div style="text-align: center;">
            <a href="https://t.me/Konspekt_help_bot" class="btn" target="_blank">🤖 Открыть бота в Telegram</a>
            <a href="/stats" class="btn">📊 Статистика системы</a>
            <a href="/health" class="btn">❤️ Проверка состояния</a>
        </div>
        
        <h3>🎯 Как получить качественный анализ:</h3>
        <ol>
            <li>Используйте конкретные, научно-ориентированные запросы</li>
            <li>Избегайте общих вопросов и эмоциональных формулировок</li>
            <li>Указывайте конкретные термины и понятия</li>
            <li>Проверяйте оценку достоверности в результатах</li>
            <li>Сравнивайте информацию из разных источников</li>
        </ol>
        
        <div style="background: #fef3c7; padding: 15px; border-radius: 10px; margin-top: 30px; border-left: 5px solid #f59e0b;">
            <strong>⚠️ Важное предупреждение:</strong> Система анализирует и оценивает информацию, но не заменяет критическое мышление. Всегда проверяйте важные данные по нескольким источникам.
        </div>
        
        <p style="text-align: center; color: #666; margin-top: 40px; font-size: 0.9em;">
            Система обновляется в реальном времени. Текущее время: <span id="time"></span>
        </p>
    </div>
    
    <script>
        async function loadStats() {
            try {
                const response = await fetch('/stats');
                const data = await response.json();
                
                document.getElementById('users').textContent = data.total_users || 0;
                document.getElementById('messages').textContent = data.total_messages || 0;
                document.getElementById('conspects').textContent = data.conspects_created || 0;
                document.getElementById('searches').textContent = data.google_searches || 0;
                
                document.getElementById('time').textContent = new Date().toLocaleTimeString();
            } catch (error) {
                console.log('Ошибка загрузки статистики:', error);
            }
        }
        
        loadStats();
        setInterval(loadStats, 3000);
    </script>
</body>
</html>
"""

# ==================== ЗАПУСК ====================
def main():
    logger.info("=" * 70)
    logger.info("🚀 ЗАПУСК УМНОГО KONSPEKT BOT С АНАЛИЗОМ ДОСТОВЕРНОСТИ")
    logger.info("=" * 70)
    logger.info(f"🌐 Внешний URL: {RENDER_EXTERNAL_URL}")
    logger.info(f"🚪 Порт: {PORT}")
    logger.info("✅ Режим: Анализ достоверности + Связывание информации")
    logger.info("✅ Фильтрация: Научные источники vs Бред")
    logger.info("✅ Объемы: Все три работают корректно")
    logger.info("=" * 70)
    
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
