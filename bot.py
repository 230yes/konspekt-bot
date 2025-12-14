#!/usr/bin/env python3
"""
Улучшенный Konspekt Helper Bot - Агрегация информации
Бот связывает информацию из разных источников, убирает дубли и предоставляет больше данных
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
from collections import Counter, defaultdict
import hashlib
from difflib import SequenceMatcher

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
    "aggregated_facts": 0,
    "duplicates_removed": 0,
    "start_time": datetime.now().isoformat(),
    "user_states": {}
}

# ==================== СИСТЕМА АГРЕГАЦИИ И ФИЛЬТРАЦИИ ====================
class InformationAggregator:
    """Агрегирует и связывает информацию из разных источников"""
    
    def __init__(self):
        self.source_checker = SourceChecker()
        
    def aggregate_information(self, items, query):
        """Агрегирует информацию из разных источников"""
        # Собираем все данные
        all_facts = []
        all_definitions = []
        all_statistics = []
        sources_by_domain = defaultdict(list)
        content_hashes = set()  # Для обнаружения дубликатов
        
        for item in items[:15]:  # Проверяем больше источников
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            
            # Проверяем качество источника
            source_check = self.source_checker.check_source_quality(link, title, snippet)
            
            # Пропускаем низкокачественные источники
            if source_check["quality"] == "low":
                continue
            
            # Извлекаем и обрабатываем информацию
            processed_data = self._process_source_item(title, snippet, link, query, source_check)
            
            if processed_data:
                # Проверяем на дубликаты по хешу содержимого
                content_hash = self._generate_content_hash(processed_data["fact"])
                if content_hash in content_hashes:
                    stats["duplicates_removed"] += 1
                    continue
                
                content_hashes.add(content_hash)
                
                # Добавляем факты
                if processed_data["fact"]:
                    all_facts.append({
                        "text": processed_data["fact"],
                        "source": link,
                        "domain": urlparse(link).netloc,
                        "quality": source_check["quality"],
                        "type": self._classify_fact_type(processed_data["fact"])
                    })
                
                # Добавляем определения
                if processed_data["definition"]:
                    all_definitions.append(processed_data["definition"])
                
                # Добавляем статистику
                all_statistics.extend(processed_data["statistics"])
                
                # Группируем источники по доменам
                domain = urlparse(link).netloc
                sources_by_domain[domain].append({
                    "url": link,
                    "quality": source_check["quality"]
                })
        
        # Анализируем и связываем информацию
        analyzed_info = self._analyze_and_link_facts(all_facts, query)
        
        # Объединяем информацию
        result = {
            "linked_facts": analyzed_info["linked_facts"],
            "fact_clusters": analyzed_info["fact_clusters"],
            "definitions": self._merge_definitions(all_definitions)[:6],
            "statistics": self._merge_statistics(all_statistics)[:10],
            "timeline_data": analyzed_info["timeline_data"][:5],
            "comparison_data": analyzed_info["comparison_data"][:5],
            "key_entities": analyzed_info["key_entities"][:12],
            "controversial_points": analyzed_info["controversial_points"][:3],
            "source_coverage": self._calculate_source_coverage(sources_by_domain),
            "total_unique_facts": len(analyzed_info["linked_facts"]),
            "domains_used": list(sources_by_domain.keys())[:8]
        }
        
        stats["aggregated_facts"] += len(result["linked_facts"])
        return result
    
    def _process_source_item(self, title, snippet, link, query, source_check):
        """Обрабатывает информацию из одного источника"""
        full_text = f"{title}. {snippet}"
        
        # Извлекаем факт
        fact = self._extract_comprehensive_fact(full_text, query)
        
        # Извлекаем определение
        definition = self._extract_enhanced_definition(full_text)
        
        # Извлекаем статистику
        statistics = self._extract_detailed_statistics(full_text)
        
        # Извлекаем даты и временные метки
        dates = self._extract_dates(full_text)
        if dates and fact:
            fact = f"{fact} ({dates[0]})"
        
        # Извлекаем имена и организации
        entities = self._extract_entities(full_text)
        
        return {
            "fact": fact,
            "definition": definition,
            "statistics": statistics,
            "dates": dates,
            "entities": entities,
            "quality": source_check["quality"]
        }
    
    def _extract_comprehensive_fact(self, text, query):
        """Извлекает развернутый факт с контекстом"""
        sentences = re.split(r'[.!?]+', text)
        
        relevant_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if 40 < len(sentence) < 250:
                if self._is_comprehensive_sentence(sentence, query):
                    relevant_sentences.append(sentence)
        
        if not relevant_sentences:
            return None
        
        # Объединяем связанные предложения
        if len(relevant_sentences) > 1:
            # Находим наиболее информативное предложение
            best_sentence = max(relevant_sentences, key=lambda s: len(s.split()))
            return best_sentence[:220]
        
        return relevant_sentences[0][:200]
    
    def _is_comprehensive_sentence(self, sentence, query):
        """Проверяет, является ли предложение информативным"""
        sentence_lower = sentence.lower()
        query_words = [w.lower() for w in query.split() if len(w) > 3]
        
        # Проверяем релевантность
        relevance_score = sum(1 for word in query_words if word in sentence_lower)
        
        # Проверяем информативность
        has_specifics = bool(re.search(r'\d{4}|\d+%|\d+\.\d+', sentence))
        has_entities = bool(re.search(r'[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+', sentence))
        has_verbs = len([w for w in sentence.split() if w.endswith(('ся', 'ть', 'л', 'ла'))]) > 1
        
        return (relevance_score > 0 or has_specifics) and (has_verbs or has_entities)
    
    def _extract_enhanced_definition(self, text):
        """Извлекает улучшенное определение с контекстом"""
        patterns = [
            r'это\s+[^.!?]{10,150}(?:[.!?]|\s+—\s+[^.!?]{5,50})',
            r'определ[яю]ется\s+как\s+[^.!?]{10,150}[.!?]',
            r'является\s+[^.!?]{10,150}(?:[.!?]|\s+—\s+[^.!?]{5,50})',
            r'под\s+[^.!?]{3,20}\s+понима[юя]т\s+[^.!?]{10,150}[.!?]'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                definition = match.group(0).strip()
                if 30 < len(definition) < 180:
                    # Добавляем контекст если есть
                    context_match = re.search(r'[^.!?]{10,80}\s+—\s+', definition)
                    if context_match:
                        return definition[:160] + "..."
                    else:
                        return definition[:140] + "..."
        
        return None
    
    def _extract_detailed_statistics(self, text):
        """Извлекает детальную статистику"""
        patterns = [
            # Проценты с контекстом
            r'\d+\.?\d*%\s+(?:[^.!?]{5,40})',
            # Большие числа с пояснением
            r'\d+[,.]?\d*\s*(?:млн|млрд|тыс|миллион|миллиард|тысяч)[^.!?]{5,40}',
            # Деньги с контекстом
            r'\$\d+[,.]?\d*\s+(?:[^.!?]{5,30})',
            # Даты и периоды
            r'\d{4}\s*(?:год[уа]?|г\.?)\s+(?:[^.!?]{5,30})',
            # Диапазоны
            r'от\s+\d+\s+до\s+\d+\s+(?:[^.!?]{5,20})',
            # Сравнения
            r'в\s+\d+[,.]?\d*\s+раза\s+(?:[^.!?]{5,30})'
        ]
        
        statistics = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if 10 < len(match) < 100:
                    statistics.append(match.strip())
        
        return list(set(statistics))[:8]
    
    def _extract_dates(self, text):
        """Извлекает даты"""
        patterns = [
            r'\d{1,2}\s+[а-яё]+\s+\d{4}',
            r'\d{4}\s+год[ау]?',
            r'в\s+\d{4}\s+году',
            r'\d{1,2}\.\d{1,2}\.\d{4}'
        ]
        
        dates = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        return dates[:3]
    
    def _extract_entities(self, text):
        """Извлекает имена и организации"""
        # Имена (Фамилия Имя)
        names = re.findall(r'[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+', text)
        
        # Организации (с заглавных букв, длинные)
        orgs = re.findall(r'[А-ЯЁ][А-ЯЁа-яё]+\s+(?:университет|институт|академия|компания|корпорация)', text)
        
        return names[:3] + orgs[:2]
    
    def _generate_content_hash(self, text):
        """Генерирует хеш для обнаружения дубликатов"""
        if not text:
            return ""
        # Нормализуем текст (убираем пробелы, приводим к нижнему регистру)
        normalized = re.sub(r'\s+', ' ', text.lower()).strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def _classify_fact_type(self, fact):
        """Классифицирует тип факта"""
        fact_lower = fact.lower()
        
        if re.search(r'\d{4}|\d+\.\d+|\d+%', fact):
            return "statistical"
        elif any(word in fact_lower for word in ['обнаружен', 'открыт', 'изобретён']):
            return "discovery"
        elif any(word in fact_lower for word in ['вызвал', 'привел', 'последствием']):
            return "consequence"
        elif any(word in fact_lower for word in ['согласно', 'по данным', 'исследование']):
            return "research"
        elif any(word in fact_lower for word in ['важн', 'значени', 'влияни']):
            return "significance"
        
        return "general"
    
    def _analyze_and_link_facts(self, facts, query):
        """Анализирует и связывает факты из разных источников"""
        if not facts:
            return {
                "linked_facts": [],
                "fact_clusters": [],
                "timeline_data": [],
                "comparison_data": [],
                "key_entities": [],
                "controversial_points": []
            }
        
        # Группируем факты по типам и темам
        fact_clusters = defaultdict(list)
        
        for fact in facts:
            fact_type = fact["type"]
            fact_clusters[fact_type].append(fact)
        
        # Создаем связанные факты
        linked_facts = []
        
        # 1. Статистические факты с разных источников
        if "statistical" in fact_clusters:
            stats_facts = fact_clusters["statistical"]
            if len(stats_facts) >= 2:
                linked = self._link_statistical_facts(stats_facts)
                linked_facts.extend(linked)
        
        # 2. Факты об открытиях и изобретениях
        if "discovery" in fact_clusters:
            disc_facts = fact_clusters["discovery"]
            linked_facts.extend([f["text"] for f in disc_facts[:3]])
        
        # 3. Факты о последствиях
        if "consequence" in fact_clusters:
            cons_facts = fact_clusters["consequence"]
            if cons_facts:
                linked_facts.append(f"🔗 Последствия: {cons_facts[0]['text']}")
        
        # 4. Общие факты
        if "general" in fact_clusters:
            gen_facts = fact_clusters["general"]
            linked_facts.extend([f["text"] for f in gen_facts[:5]])
        
        # 5. Если мало связанных фактов, добавляем лучшие из всех
        if len(linked_facts) < 8:
            all_facts_sorted = sorted(facts, key=lambda x: len(x["text"]), reverse=True)
            additional_facts = [f["text"] for f in all_facts_sorted[:10] 
                              if f["text"] not in linked_facts]
            linked_facts.extend(additional_facts[:8-len(linked_facts)])
        
        # Извлекаем ключевые сущности
        key_entities = self._extract_key_entities_from_facts(facts)
        
        # Находим потенциально спорные моменты
        controversial = self._find_controversial_points(facts)
        
        # Создаем временные данные
        timeline_data = self._create_timeline_data(facts)
        
        # Данные для сравнения
        comparison_data = self._create_comparison_data(facts)
        
        return {
            "linked_facts": linked_facts[:15],  # Больше фактов
            "fact_clusters": [{k: len(v)} for k, v in fact_clusters.items()],
            "timeline_data": timeline_data,
            "comparison_data": comparison_data,
            "key_entities": key_entities,
            "controversial_points": controversial
        }
    
    def _link_statistical_facts(self, stats_facts):
        """Связывает статистические факты"""
        if len(stats_facts) < 2:
            return [f["text"] for f in stats_facts]
        
        # Группируем по схожим числам
        number_groups = defaultdict(list)
        
        for fact in stats_facts:
            numbers = re.findall(r'\d+\.?\d*', fact["text"])
            for num in numbers[:2]:
                if float(num) > 1:  # Игнорируем маленькие числа
                    key = f"{float(num):.1f}"
                    number_groups[key].append(fact)
        
        linked = []
        for num, facts in number_groups.items():
            if len(facts) >= 2:
                # Находим общую тему
                domains = set(f["domain"] for f in facts)
                sources_info = f"({len(facts)} источника: {', '.join(list(domains)[:2])})"
                best_fact = max(facts, key=lambda f: len(f["text"]))
                linked.append(f"📊 {best_fact['text']} {sources_info}")
            else:
                linked.append(f"📊 {facts[0]['text']}")
        
        return linked[:5]
    
    def _extract_key_entities_from_facts(self, facts):
        """Извлекает ключевые сущности из фактов"""
        all_text = " ".join([f["text"] for f in facts])
        
        # Имена и организации
        entities = re.findall(r'[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+|[А-ЯЁ][А-ЯЁа-яё]+\s+(?:университет|институт)', all_text)
        
        # Уникальные и отсортированные по частоте
        entity_counter = Counter(entities)
        return [entity for entity, count in entity_counter.most_common(15)]
    
    def _find_controversial_points(self, facts):
        """Находит потенциально спорные моменты"""
        if len(facts) < 3:
            return []
        
        # Ищем утверждения с модальными глаголами и оценочными словами
        controversial_patterns = [
            r'вероятно', r'возможно', r'предположительно',
            r'спорно', r'дискуссионно', r'противоречиво',
            r'некоторые считают', r'по мнению'
        ]
        
        controversial = []
        for fact in facts:
            fact_lower = fact["text"].lower()
            for pattern in controversial_patterns:
                if re.search(pattern, fact_lower):
                    controversial.append(f"💬 {fact['text'][:120]}...")
                    break
        
        return controversial[:4]
    
    def _create_timeline_data(self, facts):
        """Создает данные для временной линии"""
        timeline = []
        
        for fact in facts:
            # Ищем годы в фактах
            years = re.findall(r'\b\d{4}\b', fact["text"])
            for year in years[:2]:
                if 1000 < int(year) < 2100:
                    # Упрощаем факт для временной линии
                    clean_fact = re.sub(r'\([^)]*\)', '', fact["text"])
                    clean_fact = clean_fact[:80] + ("..." if len(clean_fact) > 80 else "")
                    timeline.append(f"{year}: {clean_fact}")
        
        # Сортируем по году
        timeline.sort(key=lambda x: int(re.search(r'\d{4}', x).group()))
        return timeline[:8]
    
    def _create_comparison_data(self, facts):
        """Создает данные для сравнения"""
        if len(facts) < 2:
            return []
        
        # Ищем факты с числами для сравнения
        comparison = []
        for i in range(min(3, len(facts))):
            for j in range(i+1, min(4, len(facts))):
                fact1, fact2 = facts[i], facts[j]
                
                # Извлекаем числа из фактов
                nums1 = re.findall(r'\d+\.?\d*', fact1["text"])
                nums2 = re.findall(r'\d+\.?\d*', fact2["text"])
                
                if nums1 and nums2:
                    try:
                        num1 = float(nums1[0])
                        num2 = float(nums2[0])
                        if num1 > 0 and num2 > 0 and abs(num1 - num2) > 0.1:
                            ratio = max(num1, num2) / min(num1, num2)
                            if 1.5 < ratio < 10:  # Разумное отношение
                                comparison.append(f"📈 Сравнение: {num1:.1f} vs {num2:.1f} (в {ratio:.1f} раз)")
                    except ValueError:
                        continue
        
        return comparison[:4]
    
    def _merge_definitions(self, definitions):
        """Объединяет определения"""
        if not definitions:
            return []
        
        # Убираем похожие определения
        unique_defs = []
        for def1 in definitions:
            is_duplicate = False
            for def2 in unique_defs:
                similarity = SequenceMatcher(None, def1.lower(), def2.lower()).ratio()
                if similarity > 0.7:  # Более 70% совпадение
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_defs.append(def1)
        
        return unique_defs
    
    def _merge_statistics(self, statistics):
        """Объединяет статистику"""
        if not statistics:
            return []
        
        # Группируем по типам
        percent_stats = [s for s in statistics if '%' in s]
        money_stats = [s for s in statistics if any(w in s.lower() for w in ['$', 'доллар', 'рубл', 'евро'])]
        other_stats = [s for s in statistics if s not in percent_stats and s not in money_stats]
        
        merged = []
        if percent_stats:
            merged.append(f"📊 Проценты: {', '.join(percent_stats[:3])}")
        if money_stats:
            merged.append(f"💰 Финансы: {', '.join(money_stats[:3])}")
        if other_stats:
            merged.extend(other_stats[:5])
        
        return merged
    
    def _calculate_source_coverage(self, sources_by_domain):
        """Рассчитывает охват источников"""
        total_sources = sum(len(sources) for sources in sources_by_domain.values())
        unique_domains = len(sources_by_domain)
        
        coverage = {
            "total_sources": total_sources,
            "unique_domains": unique_domains,
            "domain_distribution": {domain: len(sources) 
                                  for domain, sources in list(sources_by_domain.items())[:5]}
        }
        
        # Рассчитываем разнообразие
        if total_sources > 0:
            diversity_score = unique_domains / total_sources
            coverage["diversity_score"] = f"{diversity_score:.2f}"
            if diversity_score > 0.4:
                coverage["assessment"] = "✅ Высокое разнообразие источников"
            elif diversity_score > 0.2:
                coverage["assessment"] = "⚠️ Среднее разнообразие источников"
            else:
                coverage["assessment"] = "❌ Низкое разнообразие источников"
        
        return coverage

# ==================== ОСНОВНОЙ АНАЛИЗАТОР ====================
class InformationAnalyzer:
    """Основной анализатор с агрегацией"""
    
    def __init__(self):
        self.aggregator = InformationAggregator()
        self.source_checker = SourceChecker()
    
    def analyze_topic(self, query, search_results):
        """Анализирует тему с агрегацией информации"""
        items = search_results.get("items", [])
        
        # Агрегируем информацию
        aggregated_data = self.aggregator.aggregate_information(items, query)
        
        return {
            "topic": query,
            "type": self._determine_topic_type(query),
            "aggregated_data": aggregated_data,
            "timestamp": datetime.now().isoformat(),
            "quality_report": self._generate_quality_report(aggregated_data)
        }
    
    def _determine_topic_type(self, query):
        """Определяет тип темы"""
        query_lower = query.lower()
        
        science_terms = ["физика", "химия", "биология", "математика", "наука", "исследование"]
        tech_terms = ["технология", "программирование", "искусственный интеллект", "компьютер"]
        history_terms = ["история", "война", "революция", "древний", "средневековье"]
        
        if any(term in query_lower for term in science_terms):
            return "научная"
        elif any(term in query_lower for term in tech_terms):
            return "технологическая"
        elif any(term in query_lower for term in history_terms):
            return "историческая"
        
        return "общая"
    
    def _generate_quality_report(self, aggregated_data):
        """Генерирует отчет о качестве"""
        coverage = aggregated_data.get("source_coverage", {})
        total_facts = aggregated_data.get("total_unique_facts", 0)
        
        report = []
        
        if total_facts > 0:
            report.append(f"✅ Найдено фактов: {total_facts}")
        
        if "total_sources" in coverage:
            report.append(f"📚 Источников: {coverage['total_sources']}")
        
        if "unique_domains" in coverage:
            report.append(f"🌐 Уникальных доменов: {coverage['unique_domains']}")
        
        if "assessment" in coverage:
            report.append(coverage["assessment"])
        
        if aggregated_data.get("controversial_points"):
            report.append(f"💬 Спорных моментов: {len(aggregated_data['controversial_points'])}")
        
        return "\n".join(report)

# ==================== ГЕНЕРАТОР КОНСПЕКТОВ ====================
class SmartConspectGenerator:
    def __init__(self):
        self.searcher = SmartGoogleSearch()
        logger.info("✅ Генератор готов с агрегацией информации")
    
    def generate(self, topic, volume="extended"):  # По умолчанию расширенный
        """Генерирует конспект с агрегацией информации"""
        if self._is_easter_egg(topic):
            return self._create_easter_egg_response()
        
        search_results = self.searcher.search_and_analyze(topic)
        structured_info = search_results.get("structured_info", {})
        aggregated_data = structured_info.get("aggregated_data", {})
        quality_report = structured_info.get("quality_report", "")
        
        if volume == "detailed":
            return self._generate_detailed(topic, aggregated_data, quality_report)
        elif volume == "short":
            return self._generate_short(topic, aggregated_data, quality_report)
        else:
            return self._generate_extended(topic, aggregated_data, quality_report)
    
    def _is_easter_egg(self, text):
        text_lower = text.lower()
        return "пасхалка" in text_lower
    
    def _create_easter_egg_response(self):
        return "🥚 *Пасхалка найдена!* Бот использует продвинутую агрегацию данных."
    
    def _generate_short(self, topic, data, quality_report):
        """Кратко - ключевые факты"""
        facts = data.get("linked_facts", [])
        
        if not facts:
            return f"📌 *{topic}*\n\n{quality_report}\n\nИнформация не найдена"
        
        conspect = f"📌 *{topic}*\n\n{quality_report}\n\n"
        
        # Лучшие факты
        for i, fact in enumerate(facts[:6], 1):
            conspect += f"{i}. {fact}\n"
        
        # Ключевые термины
        entities = data.get("key_entities", [])
        if entities:
            conspect += f"\n🔑 *Ключевые понятия:* {', '.join(entities[:4])}\n"
        
        return conspect
    
    def _generate_detailed(self, topic, data, quality_report):
        """Подробно - структурированная информация"""
        conspect = f"📚 *{topic}*\n\n{quality_report}\n\n"
        
        # Основные факты
        facts = data.get("linked_facts", [])
        if facts:
            conspect += "🎯 *Основные факты:*\n\n"
            for i, fact in enumerate(facts[:10], 1):
                conspect += f"{i}. {fact}\n"
        
        # Определения
        definitions = data.get("definitions", [])
        if definitions:
            conspect += f"\n📖 *Определения:*\n\n"
            for definition in definitions[:4]:
                conspect += f"• {definition}\n"
        
        # Статистика
        statistics = data.get("statistics", [])
        if statistics:
            conspect += f"\n📊 *Статистика:*\n\n"
            for stat in statistics[:6]:
                conspect += f"• {stat}\n"
        
        # Временные данные
        timeline = data.get("timeline_data", [])
        if timeline:
            conspect += f"\n🕒 *Хронология:*\n\n"
            for event in timeline[:4]:
                conspect += f"• {event}\n"
        
        # Информация об источниках
        coverage = data.get("source_coverage", {})
        if "total_sources" in coverage:
            conspect += f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
            conspect += f"📚 Источников: {coverage['total_sources']} | "
            conspect += f"🌐 Доменов: {coverage.get('unique_domains', 0)}"
        
        return conspect
    
    def _generate_extended(self, topic, data, quality_report):
        """Полный анализ - вся агрегированная информация"""
        conspect = f"🔬 *ПОЛНЫЙ АНАЛИЗ: {topic}*\n\n{quality_report}\n\n"
        
        # ВВЕДЕНИЕ
        conspect += "="*50 + "\n"
        conspect += "ВВЕДЕНИЕ И МЕТОДОЛОГИЯ\n"
        conspect += "="*50 + "\n\n"
        
        coverage = data.get("source_coverage", {})
        conspect += f"*Методология:* Агрегация информации из {coverage.get('total_sources', 0)} источников\n"
        conspect += f"*Обработано фактов:* {data.get('total_unique_facts', 0)}\n"
        conspect += f"*Удалено дубликатов:* {stats.get('duplicates_removed', 0)}\n"
        conspect += f"*Время анализа:* {datetime.now().strftime('%H:%M')}\n\n"
        
        # ОСНОВНЫЕ ФАКТЫ
        conspect += "="*50 + "\n"
        conspect += "ОСНОВНЫЕ ФАКТЫ И ДАННЫЕ\n"
        conspect += "="*50 + "\n\n"
        
        facts = data.get("linked_facts", [])
        if facts:
            for i, fact in enumerate(facts[:15], 1):
                conspect += f"{i}. {fact}\n\n"
        else:
            conspect += "Информация по теме требует дополнительного изучения\n\n"
        
        # СТАТИСТИКА И ЦИФРЫ
        statistics = data.get("statistics", [])
        if statistics:
            conspect += "="*50 + "\n"
            conspect += "СТАТИСТИКА И ЧИСЛОВЫЕ ДАННЫЕ\n"
            conspect += "="*50 + "\n\n"
            
            for stat in statistics:
                conspect += f"• {stat}\n"
            conspect += "\n"
        
        # ОПРЕДЕЛЕНИЯ И ПОНЯТИЯ
        definitions = data.get("definitions", [])
        if definitions:
            conspect += "="*50 + "\n"
            conspect += "ОПРЕДЕЛЕНИЯ И КЛЮЧЕВЫЕ ПОНЯТИЯ\n"
            conspect += "="*50 + "\n\n"
            
            for i, definition in enumerate(definitions, 1):
                conspect += f"{i}. {definition}\n\n"
        
        # ХРОНОЛОГИЯ
        timeline = data.get("timeline_data", [])
        if timeline:
            conspect += "="*50 + "\n"
            conspect += "ХРОНОЛОГИЧЕСКИЕ ДАННЫЕ\n"
            conspect += "="*50 + "\n\n"
            
            for event in timeline:
                conspect += f"• {event}\n"
            conspect += "\n"
        
        # КЛЮЧЕВЫЕ СУЩНОСТИ
        entities = data.get("key_entities", [])
        if entities:
            conspect += "="*50 + "\n"
            conspect += "КЛЮЧЕВЫЕ СУЩНОСТИ И ОРГАНИЗАЦИИ\n"
            conspect += "="*50 + "\n\n"
            
            for i, entity in enumerate(entities[:12], 1):
                conspect += f"{i}. {entity}\n"
            conspect += "\n"
        
        # СРАВНЕНИЯ И АНАЛИЗ
        comparison = data.get("comparison_data", [])
        if comparison:
            conspect += "="*50 + "\n"
            conspect += "СРАВНИТЕЛЬНЫЙ АНАЛИЗ\n"
            conspect += "="*50 + "\n\n"
            
            for comp in comparison:
                conspect += f"• {comp}\n"
            conspect += "\n"
        
        # СПОРНЫЕ МОМЕНТЫ
        controversial = data.get("controversial_points", [])
        if controversial:
            conspect += "="*50 + "\n"
            conspect += "СПОРНЫЕ И ДИСКУССИОННЫЕ МОМЕНТЫ\n"
            conspect += "="*50 + "\n\n"
            
            for point in controversial:
                conspect += f"• {point}\n"
            conspect += "\n"
        
        # АНАЛИЗ ИСТОЧНИКОВ
        conspect += "="*50 + "\n"
        conspect += "АНАЛИЗ ИСТОЧНИКОВ И ДОСТОВЕРНОСТИ\n"
        conspect += "="*50 + "\n\n"
        
        conspect += f"*Всего обработано источников:* {coverage.get('total_sources', 0)}\n"
        conspect += f"*Уникальных доменов:* {coverage.get('unique_domains', 0)}\n"
        conspect += f"*Связей между фактами:* {len(facts)}\n"
        conspect += f"*Удалено дубликатов:* {stats.get('duplicates_removed', 0)}\n\n"
        
        if "domain_distribution" in coverage:
            conspect += "*Распределение по доменам:*\n"
            for domain, count in coverage["domain_distribution"].items():
                conspect += f"• {domain}: {count} источников\n"
        
        # ЗАКЛЮЧЕНИЕ
        conspect += "\n" + "="*50 + "\n"
        conspect += "ЗАКЛЮЧЕНИЕ И ВЫВОДЫ\n"
        conspect += "="*50 + "\n\n"
        
        total_facts = data.get("total_unique_facts", 0)
        if total_facts >= 10:
            conspect += "✅ Информация хорошо освещена в различных источниках\n"
            conspect += "✅ Найдены статистические данные и конкретные факты\n"
            conspect += "✅ Выявлены ключевые сущности и хронология\n"
        elif total_facts >= 5:
            conspect += "⚠️ Информация представлена ограниченно\n"
            conspect += "⚠️ Рекомендуется обратиться к дополнительным источникам\n"
        else:
            conspect += "❌ Информации недостаточно для комплексного анализа\n"
            conspect += "❌ Требуются дополнительные исследования\n"
        
        conspect += f"\n🤖 *@Konspekt_help_bot* | 🧠 *Агрегация данных* | 🕒 {datetime.now().strftime('%d.%m.%Y')}"
        
        return conspect

# ==================== ОСТАЛЬНОЙ КОД (без изменений) ====================
# [SourceChecker, SmartGoogleSearch, TelegramBot, BotHTTPServer остаются без изменений]
# Просто добавьте этот код после класса InformationAggregator

# ==================== ЗАПУСК ====================
def main():
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК БОТА С АГРЕГАЦИЕЙ ИНФОРМАЦИИ")
    logger.info("=" * 60)
    logger.info(f"✅ Режим: Агрегация из 15+ источников")
    logger.info(f"✅ Фильтрация дубликатов")
    logger.info(f"✅ Связывание информации")
    logger.info(f"✅ Увеличенный объем данных")
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
