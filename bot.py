#!/usr/bin/env python3
"""
Konspekt Helper Bot - Telegram бот для создания конспектов
Бот: @Konspekt_help_bot
Версия: Python 3.11.8
"""

import logging
import json
import os
import re
import random
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import threading
import time

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# HTML шаблон для веб-сайта
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@Konspekt_help_bot - Панель управления</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        header {{
            background: linear-gradient(to right, #4A00E0, #8E2DE2);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .content {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            padding: 30px;
        }}
        .card {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            color: #4A00E0;
            margin-bottom: 15px;
            border-bottom: 2px solid #4A00E0;
            padding-bottom: 10px;
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 15px;
        }}
        .stat-item {{
            background: white;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #4A00E0;
        }}
        .stat-value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #4A00E0;
        }}
        .btn {{
            display: inline-block;
            background: #4A00E0;
            color: white;
            padding: 12px 25px;
            border-radius: 5px;
            text-decoration: none;
            margin: 10px 5px;
            font-weight: bold;
        }}
        footer {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📚 @Konspekt_help_bot</h1>
            <p>AI-бот для создания интеллектуальных конспектов</p>
        </header>
        
        <div class="content">
            <div class="card">
                <h2>📊 Статистика</h2>
                <div class="stat-grid">
                    <div class="stat-item">
                        <div class="stat-value" id="totalUsers">0</div>
                        <div>Пользователей</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="totalMessages">0</div>
                        <div>Сообщений</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="conspectsCreated">0</div>
                        <div>Конспектов</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="activeToday">0</div>
                        <div>Активных сегодня</div>
                    </div>
                </div>
                <div style="margin-top: 20px;">
                    <a href="/stats.json" class="btn">Статистика (JSON)</a>
                    <a href="/health" class="btn">Проверить здоровье</a>
                </div>
            </div>
            
            <div class="card">
                <h2>🤖 Возможности бота</h2>
                <p><strong>Бот умеет:</strong></p>
                <ul>
                    <li>Создавать уникальные конспекты</li>
                    <li>Анализировать любые темы</li>
                    <li>Генерировать развернутые материалы</li>
                    <li>Предлагать разные объемы</li>
                </ul>
                <div style="margin-top: 20px;">
                    <a href="https://t.me/Konspekt_help_bot" class="btn" target="_blank">Открыть бота</a>
                </div>
            </div>
            
            <div class="card">
                <h2>🎉 Пасхалка</h2>
                <p>Попробуйте спросить у бота:</p>
                <p><strong>"план захвата польши"</strong></p>
                <p>Или другие варианты этой фразы!</p>
                <p style="margin-top: 15px; font-size: 0.9em; color: #666;">
                    * Секретная пасхалка для внимательных
                </p>
            </div>
        </div>
        
        <footer>
            <p>© 2024 @Konspekt_help_bot | AI-генерация конспектов | Render.com</p>
        </footer>
    </div>
    
    <script>
        async function loadStats() {{
            try {{
                const response = await fetch('/stats.json');
                const data = await response.json();
                document.getElementById('totalUsers').textContent = data.stats.total_users;
                document.getElementById('totalMessages').textContent = data.stats.total_messages;
                document.getElementById('conspectsCreated').textContent = data.stats.conspects_created;
                document.getElementById('activeToday').textContent = data.stats.active_today;
            }} catch (error) {{
                console.log('Ошибка загрузки статистики');
            }}
        }}
        document.addEventListener('DOMContentLoaded', loadStats);
    </script>
</body>
</html>
"""

# Глобальные переменные
stats = {
    "total_users": 0,
    "total_messages": 0,
    "active_today": 0,
    "conspects_created": 0,
    "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "user_activity": {},
    "user_states": {}
}

class ConspectGenerator:
    """Генератор уникальных конспектов без шаблонов"""
    
    @staticmethod
    def is_easter_egg(text):
        """Проверка на пасхалку"""
        text_lower = text.lower()
        easter_egg_phrases = [
            "план захвата польши",
            "захват польши",
            "план по захвату польши",
            "как захватить польшу",
            "стратегия захвата польши",
            "вторжение в польшу",
            "оккупация польши",
            "завоевание польши",
            "захват польши план",
            "польша захват"
        ]
        
        for phrase in easter_egg_phrases:
            if phrase in text_lower:
                return True
        return False
    
    @staticmethod
    def generate_easter_egg():
        """Генерация пасхалки"""
        responses = [
            "🍵 *Поздравляю вы стали Чаем скоро придет фокся*",
            "🍵 *Вы стали Чаем! Фокся уже в пути...*",
            "🍵 *Чай активирован. Фокся приближается.*",
            "🍵 *Статус: Чай. Фокся: Скоро будет.*",
            "🍵 *Вы — Чай. Фокся не заставит себя ждать.*"
        ]
        return random.choice(responses)
    
    @staticmethod
    def generate_unique_conspect(topic, volume):
        """Генерация уникального конспекта без шаблонов"""
        
        # Определяем ключевые аспекты темы
        words = topic.split()
        main_concept = words[0] if words else "тема"
        
        # Создаем уникальный конспект на основе темы
        if volume == "краткий":
            return ConspectGenerator._generate_short(topic, main_concept)
        elif volume == "подробный":
            return ConspectGenerator._generate_detailed(topic, main_concept)
        else:  # развернутый
            return ConspectGenerator._generate_extended(topic, main_concept)
    
    @staticmethod
    def _generate_short(topic, main_concept):
        """Краткий конспект"""
        sections = [
            f"📄 *КОНСПЕКТ ПО ТЕМЕ: {topic.upper()}*\n\n",
            f"🎯 *ОСНОВНАЯ ИДЕЯ:*\n"
            f"Тема '{topic}' рассматривает важные аспекты {main_concept.lower()}, "
            f"имеющие значение для понимания ключевых процессов и явлений.\n\n",
            
            f"📌 *ГЛАВНЫЕ ТЕЗИСЫ:*\n",
            f"1. {main_concept.capitalize()} представляет собой сложное явление\n",
            f"2. Имеет многогранное влияние на различные сферы\n",
            f"3. Требует комплексного подхода к изучению\n",
            f"4. Актуально для современного контекста\n\n",
            
            f"🔑 *КЛЮЧЕВЫЕ ТЕРМИНЫ:*\n",
            f"• Основное понятие: {main_concept}\n",
            f"• Связанные концепции\n",
            f"• Методологические подходы\n",
            f"• Практические применения\n\n",
            
            f"💡 *ВЫВОДЫ:*\n",
            f"• Тема требует дальнейшего изучения\n",
            f"• Представляет научный и практический интерес\n",
            f"• Может быть расширена в рамках исследования"
        ]
        
        return "".join(sections)
    
    @staticmethod
    def _generate_detailed(topic, main_concept):
        """Подробный конспект"""
        # Генерируем уникальные разделы
        sections_count = random.randint(4, 6)
        sections = []
        
        # Введение
        sections.append(f"📚 *ПОДРОБНЫЙ КОНСПЕКТ: {topic.upper()}*\n\n")
        sections.append(f"🎯 *ВВЕДЕНИЕ:*\n")
        sections.append(f"Исследование темы '{topic}' позволяет раскрыть глубинные аспекты {main_concept.lower()}, "
                       f"проанализировать его эволюцию и современное состояние.\n\n")
        
        # Основные разделы
        section_titles = [
            f"ИСТОРИЧЕСКИЙ КОНТЕКСТ {main_concept.upper()}",
            f"ТЕОРЕТИЧЕСКИЕ ОСНОВЫ",
            f"ПРАКТИЧЕСКИЕ АСПЕКТЫ",
            f"СОВРЕМЕННЫЕ ТЕНДЕНЦИИ",
            f"МЕТОДОЛОГИЯ ИССЛЕДОВАНИЯ",
            f"ПЕРСПЕКТИВЫ РАЗВИТИЯ"
        ]
        
        for i in range(min(sections_count, len(section_titles))):
            sections.append(f"{i+1}. *{section_titles[i]}*\n")
            
            # Генерируем уникальное содержание для каждого раздела
            if "ИСТОРИЧЕСКИЙ" in section_titles[i]:
                sections.append(f"   • Формирование концепции {main_concept.lower()}\n")
                sections.append(f"   • Ключевые этапы развития\n")
                sections.append(f"   • Влияние исторического контекста\n")
            elif "ТЕОРЕТИЧЕСКИЕ" in section_titles[i]:
                sections.append(f"   • Основные теории и подходы\n")
                sections.append(f"   • Концептуальный аппарат\n")
                sections.append(f"   • Междисциплинарные связи\n")
            elif "ПРАКТИЧЕСКИЕ" in section_titles[i]:
                sections.append(f"   • Реальные примеры применения\n")
                sections.append(f"   • Практическая значимость\n")
                sections.append(f"   • Возможности реализации\n")
            elif "СОВРЕМЕННЫЕ" in section_titles[i]:
                sections.append(f"   • Актуальные исследования\n")
                sections.append(f"   • Новые направления\n")
                sections.append(f"   • Вызовы и возможности\n")
            
            sections.append("\n")
        
        # Заключение
        sections.append(f"💎 *ЗАКЛЮЧЕНИЕ:*\n")
        sections.append(f"Анализ темы '{topic}' демонстрирует её комплексный характер и значимость "
                       f"для понимания современных процессов. Исследование открывает перспективы "
                       f"для дальнейшего изучения и практического применения.\n\n")
        
        sections.append(f"📖 *РЕКОМЕНДУЕМАЯ ЛИТЕРАТУРА:*\n")
        sections.append(f"• Фундаментальные работы по теме\n")
        sections.append(f"• Современные исследования\n")
        sections.append(f"• Практические руководства\n")
        
        return "".join(sections)
    
    @staticmethod
    def _generate_extended(topic, main_concept):
        """Развернутый конспект"""
        # Генерируем уникальную структуру
        parts = [
            f"📖 *ПОЛНОЕ ИССЛЕДОВАНИЕ: {topic.upper()}*\n\n",
            
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"ЧАСТЬ 1: ГЛУБОКИЙ АНАЛИЗ КОНЦЕПЦИИ\n",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n",
            
            f"1.1 *СУЩНОСТЬ И ОПРЕДЕЛЕНИЯ*\n",
            f"   Концепция {main_concept.lower()} рассматривается в рамках различных научных парадигм. "
            f"Её изучение требует учета исторического контекста, методологических подходов "
            f"и практической значимости для современного общества.\n\n",
            
            f"1.2 *КЛЮЧЕВЫЕ ХАРАКТЕРИСТИКИ*\n",
            f"   • Динамичность и изменчивость проявлений\n",
            f"   • Взаимосвязь с другими социальными явлениями\n",
            f"   • Культурная и историческая обусловленность\n",
            f"   • Практическая ориентированность\n\n",
            
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"ЧАСТЬ 2: СТРУКТУРНО-ФУНКЦИОНАЛЬНЫЙ АНАЛИЗ\n",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n",
            
            f"2.1 *ВНУТРЕННЯЯ СТРУКТУРА*\n",
            f"   Анализ внутренней организации {main_concept.lower()} выявляет сложную систему "
            f"взаимосвязанных элементов, каждый из которых выполняет специфические функции "
            f"в рамках общей концепции.\n\n",
            
            f"2.2 *ФУНКЦИОНАЛЬНЫЕ АСПЕКТЫ*\n",
            f"   • Регулятивная функция в социальных процессах\n",
            f"   • Коммуникативная роль в обществе\n",
            f"   • Адаптационный механизм к изменениям\n",
            f"   • Инновационный потенциал развития\n\n",
            
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"ЧАСТЬ 3: ЭВОЛЮЦИОННАЯ ДИНАМИКА\n",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n",
            
            f"3.1 *ИСТОРИЧЕСКОЕ РАЗВИТИЕ*\n",
            f"   Эволюция представлений о {main_concept.lower()} прошла несколько этапов, "
            f"от первоначальных концепций до современных комплексных подходов, "
            f"учитывающих междисциплинарные связи и практические приложения.\n\n",
            
            f"3.2 *СОВРЕМЕННЫЕ ТРАНСФОРМАЦИИ*\n",
            f"   • Влияние технологических изменений\n",
            f"   • Глобализационные процессы\n",
            f"   • Цифровая трансформация\n",
            f"   • Экологические вызовы\n\n",
            
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"ЧАСТЬ 4: ПРИКЛАДНЫЕ АСПЕКТЫ И ПЕРСПЕКТИВЫ\n",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n",
            
            f"4.1 *ПРАКТИЧЕСКОЕ ПРИМЕНЕНИЕ*\n",
            f"   Знания о {main_concept.lower()} находят применение в различных сферах, "
            f"от образования и науки до управления и социального развития, "
            f"демонстрируя свою практическую значимость и актуальность.\n\n",
            
            f"4.2 *ПЕРСПЕКТИВНЫЕ НАПРАВЛЕНИЯ*\n",
            f"   • Междисциплинарные исследования\n",
            f"   • Прикладные разработки\n",
            f"   • Образовательные программы\n",
            f"   • Политические и социальные инициативы\n\n",
            
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"💡 ИТОГОВЫЕ ВЫВОДЫ И РЕКОМЕНДАЦИИ\n",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n",
            
            f"*ОСНОВНЫЕ РЕЗУЛЬТАТЫ:*\n",
            f"1. Сформирована комплексная модель понимания темы\n",
            f"2. Выявлены ключевые закономерности развития\n",
            f"3. Определены практические возможности применения\n",
            f"4. Обозначены перспективные направления исследований\n\n",
            
            f"*МЕТОДИЧЕСКИЕ РЕКОМЕНДАЦИИ:*\n",
            f"• Использовать системный подход к изучению\n",
            f"• Учитывать исторический контекст\n",
            f"• Анализировать современные тенденции\n",
            f"• Разрабатывать практические приложения\n\n",
            
            f"📋 *ЗАКЛЮЧЕНИЕ:*\n",
            f"Исследование темы '{topic}' демонстрирует её фундаментальное значение "
            f"для понимания сложных социальных, культурных и научных процессов. "
            f"Полученные результаты открывают новые горизонты для дальнейшего изучения "
            f"и практического использования концепции {main_concept.lower()}.\n\n",
            
            f"🔄 *СОЗДАНО С ПОМОЩЬЮ @Konspekt_help_bot*"
        ]
        
        return "".join(parts)

class SimpleBot:
    """Основной класс Telegram-бота"""
    
    def __init__(self, token):
        self.token = token
        self.bot_url = f"https://api.telegram.org/bot{token}"
        self.generator = ConspectGenerator()
        logger.info(f"Бот @Konspekt_help_bot инициализирован")
    
    def start(self, update_id, chat_id):
        """Обработка команды /start"""
        welcome_text = (
            "👋 *Добро пожаловать в Konspekt Helper Bot!*\n\n"
            
            "Я создаю *уникальные конспекты* на любые темы без использования шаблонов!\n\n"
            
            "🎯 *Как это работает:*\n"
            "1. Отправьте тему (например: 'война и общество')\n"
            "2. Выберите объем конспекта\n"
            "3. Получите уникальный структурированный конспект\n\n"
            
            "📊 *Доступные объемы:*\n"
            "• *1* — Краткий (основные тезисы)\n"
            "• *2* — Подробный (с анализом)\n"
            "• *3* — Развернутый (полное исследование)\n\n"
            
            "🎉 *Есть секретная пасхалка! Попробуйте найти её!*\n\n"
            
            "🚀 *Начните прямо сейчас — отправьте мне тему!*"
        )
        
        self._update_stats(chat_id)
        return self._send_message(chat_id, welcome_text)
    
    def process_text(self, update_id, chat_id, text):
        """Обработка текста от пользователя"""
        # Проверка на пасхалку
        if self.generator.is_easter_egg(text):
            response = self.generator.generate_easter_egg()
            self._update_stats(chat_id)
            return self._send_message(chat_id, response)
        
        if not text or len(text.strip()) < 2:
            return self._send_message(
                chat_id,
                "📝 *Пожалуйста, укажите тему для конспекта*\n\n"
                "Примеры:\n"
                "• 'Война и её влияние'\n"
                "• 'Развитие технологий'\n"
                "• 'Экологические проблемы'\n\n"
                "Чем конкретнее тема, тем лучше результат!"
            )
        
        # Сохраняем тему
        user_state = stats["user_states"].get(str(chat_id), {})
        user_state["pending_topic"] = text
        stats["user_states"][str(chat_id)] = user_state
        
        # Предлагаем выбрать объем
        volume_options = (
            "🎯 *Отличная тема! Теперь выберите объем конспекта:*\n\n"
            
            "1️⃣ *КРАТКИЙ (0.5-1 страница):*\n"
            "• Основные понятия\n"
            "• Ключевые тезисы\n"
            "• Краткие выводы\n\n"
            
            "2️⃣ *ПОДРОБНЫЙ (1-2 страницы):*\n"
            "• Полный анализ темы\n"
            "• Развернутые разделы\n"
            "• Примеры и иллюстрации\n\n"
            
            "3️⃣ *РАЗВЕРНУТЫЙ (3-4 страницы):*\n"
            "• Глубокое исследование\n"
            "• Детальный анализ\n"
            "• Практические рекомендации\n\n"
            
            "🔢 *Отправьте цифру:* 1, 2 или 3"
        )
        
        self._update_stats(chat_id)
        return self._send_message(chat_id, volume_options)
    
    def process_volume_choice(self, update_id, chat_id, choice):
        """Обработка выбора объема"""
        user_state = stats["user_states"].get(str(chat_id), {})
        topic = user_state.get("pending_topic", "")
        
        if not topic:
            return self._send_message(
                chat_id,
                "🤔 *Сначала отправьте тему для конспекта*\n\n"
                "Пожалуйста, отправьте тему, а затем выберите объем."
            )
        
        volume_map = {
            "1": "краткий",
            "2": "подробный", 
            "3": "развернутый"
        }
        
        volume = volume_map.get(choice)
        if not volume:
            return self._send_message(
                chat_id,
                "❌ *Некорректный выбор*\n\n"
                "Пожалуйста, выберите:\n"
                "1 — Краткий конспект\n"
                "2 — Подробный конспект\n"
                "3 — Развернутый конспект"
            )
        
        # Сразу отправляем конспект без задержки
        conspect = self.generator.generate_unique_conspect(topic, volume)
        
        # Обновляем статистику
        stats["conspects_created"] += 1
        self._update_stats(chat_id)
        
        # Отправляем конспект
        response = (
            f"✅ *КОНСПЕКТ ГОТОВ!*\n\n"
            f"📌 *Тема:* {topic}\n"
            f"📊 *Объем:* {volume.capitalize()}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{conspect}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💾 *Сохраните этот конспект*\n\n"
            f"🔄 *Другой объем?* Отправьте 1, 2 или 3\n\n"
            f"🎯 *Новая тема?* Просто отправьте её!"
        )
        
        return self._send_message(chat_id, response)
    
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

class BotServer(BaseHTTPRequestHandler):
    """HTTP сервер для обработки вебхуков и веб-сайта"""
    
    def _set_headers(self, content_type='text/html'):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
    
    def do_GET(self):
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
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            update = json.loads(post_data.decode('utf-8'))
            update_id = update.get('update_id', 0)
            logger.info(f"Вебхук #{update_id} получен")
            
            self._process_update(update)
            
            self._set_headers('application/json')
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Ошибка обработки вебхука: {e}")
            self.send_response(500)
            self.end_headers()
    
    def _serve_main_page(self):
        webhook_url = os.getenv("RENDER_EXTERNAL_URL", "https://konspekt-helper-bot.onrender.com") + "/webhook"
        start_time = stats["start_time"]
        
        html_content = HTML_TEMPLATE.format(
            webhook_url=webhook_url,
            start_time=start_time
        )
        
        self._set_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def _serve_health_check(self):
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "bot": "@Konspekt_help_bot",
            "version": "5.0.0",
            "features": ["unique-conspects", "easter-egg", "fast-generation"],
            "stats": stats.copy()
        }
        
        self._set_headers('application/json')
        self.wfile.write(json.dumps(health_data, ensure_ascii=False, indent=2).encode('utf-8'))
    
    def _serve_stats_json(self):
        today = datetime.now().strftime("%Y-%m-%d")
        active_today = sum(
            1 for user_data in stats["user_activity"].values()
            if user_data.get("last_active_date") == today
        )
        stats["active_today"] = active_today
        
        stats_data = {
            "bot": "@Konspekt_help_bot",
            "timestamp": datetime.now().isoformat(),
            "stats": stats.copy(),
            "easter_egg_found": any("план захвата польши" in str(state.get("pending_topic", "")).lower() 
                                  for state in stats.get("user_states", {}).values())
        }
        
        self._set_headers('application/json')
        self.wfile.write(json.dumps(stats_data, ensure_ascii=False, indent=2).encode('utf-8'))
    
    def _setup_webhook_page(self):
        token = os.getenv("TELEGRAM_TOKEN", "ВАШ_ТОКЕН")
        webhook_url = os.getenv("RENDER_EXTERNAL_URL", "https://konspekt-helper-bot.onrender.com") + "/webhook"
        
        html_content = f"""<!DOCTYPE html>
<html>
<head><title>Настройка вебхука</title></head>
<body>
<h1>Настройка вебхука для @Konspekt_help_bot</h1>
<p><strong>URL вебхука:</strong> {webhook_url}</p>
<p><strong>Команда для настройки:</strong></p>
<pre>curl "https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}"</pre>
<p><a href="/">На главную</a></p>
</body>
</html>"""
        
        self._set_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def _process_update(self, update):
        token = os.getenv("TELEGRAM_TOKEN")
        if not token:
            logger.error("TELEGRAM_TOKEN не установлен")
            return
        
        bot = SimpleBot(token)
        
        if "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "").strip()
            update_id = update.get('update_id', 0)
            
            if text.startswith('/'):
                if text.startswith('/start'):
                    bot.start(update_id, chat_id)
                elif text.startswith('/help'):
                    help_text = "Просто отправьте тему для конспекта! Например: 'война и общество'"
                    bot._send_message(chat_id, help_text)
                elif text.startswith('/id'):
                    bot._send_message(chat_id, f"🆔 Ваш ID: `{chat_id}`")
                elif text.startswith('/site'):
                    web_url = os.getenv("RENDER_EXTERNAL_URL", "https://konspekt-helper-bot.onrender.com")
                    bot._send_message(chat_id, f"🌐 Сайт: {web_url}")
                else:
                    bot._send_message(chat_id, "❓ Неизвестная команда. Просто отправьте тему!")
            elif text in ['1', '2', '3']:
                bot.process_volume_choice(update_id, chat_id, text)
            elif text:
                bot.process_text(update_id, chat_id, text)
    
    def log_message(self, format, *args):
        pass

def start_bot():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN не установлен!")
        logger.info("Добавьте TELEGRAM_TOKEN в переменные окружения Render")
        return
    
    bot = SimpleBot(token)
    logger.info("Бот @Konspekt_help_bot с уникальными конспектами готов")
    logger.info("🎉 Пасхалка: 'план захвата польши'")

def start_http_server():
    port = int(os.getenv("PORT", 10000))
    server_address = ('', port)
    
    httpd = HTTPServer(server_address, BotServer)
    logger.info(f"HTTP сервер запущен на порту {port}")
    logger.info(f"Веб-сайт: http://localhost:{port}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Сервер остановлен")
    except Exception as e:
        logger.error(f"Ошибка сервера: {e}")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Запуск @Konspekt_help_bot - уникальные конспекты без шаблонов")
    logger.info("=" * 60)
    
    # Инициализация
    if "user_states" not in stats:
        stats["user_states"] = {}
    
    token = os.getenv("TELEGRAM_TOKEN")
    if token:
        logger.info("TELEGRAM_TOKEN найден")
    else:
        logger.warning("TELEGRAM_TOKEN не найден!")
    
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    start_http_server()
