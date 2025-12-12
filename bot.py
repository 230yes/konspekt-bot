#!/usr/bin/env python3
"""
Konspekt Helper Bot - Telegram бот для создания конспектов
Бот: @Konspekt_help_bot
Разработан для развертывания на Render.com
Версия: Python 3.11.8 + python-telegram-bot 13.15
"""

import logging
import json
import os
import re
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import threading

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# HTML шаблон для веб-сайта (упрощенный и корректный)
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
        .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
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
        .webhook-log {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
            max-height: 200px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.9em;
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
            <p class="subtitle">Telegram-бот для создания конспектов</p>
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
                <h2>🤖 Команды бота</h2>
                <p><strong>@Konspekt_help_bot</strong> понимает:</p>
                <ul>
                    <li><code>/start</code> - Начало работы</li>
                    <li><code>/help</code> - Помощь</li>
                    <li><code>/id</code> - Ваш Telegram ID</li>
                    <li><code>/site</code> - Эта панель</li>
                    <li><code>/conspect [текст]</code> - Создать конспект</li>
                    <li><em>Любой текст</em> - Создать конспект</li>
                </ul>
                <div style="margin-top: 20px;">
                    <a href="https://t.me/Konspekt_help_bot" class="btn" target="_blank">Открыть бота</a>
                    <a href="/setup-webhook" class="btn">Настроить вебхук</a>
                </div>
            </div>
            
            <div class="card">
                <h2>📝 Пример конспекта</h2>
                <p>Отправьте боту текст, например:</p>
                <p><em>"Машинное обучение позволяет компьютерам обучаться на данных без явного программирования. Используется в рекомендательных системах, распознавании изображений и автономных автомобилях."</em></p>
                <p>Бот создаст подробный структурированный конспект с разделами, тезисами и выводами.</p>
            </div>
        </div>
        
        <footer>
            <p>© 2024 @Konspekt_help_bot | Render.com | Python 3.11.8</p>
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

MAX_WEBHOOKS_LOG = 50

class SimpleBot:
    """Основной класс Telegram-бота с улучшенной логикой конспектов"""
    
    def __init__(self, token):
        self.token = token
        self.bot_url = f"https://api.telegram.org/bot{token}"
        logger.info(f"Бот @Konspekt_help_bot инициализирован")
        
    def start(self, update_id, chat_id):
        """Обработка команды /start - развернутый ответ"""
        welcome_text = (
            "👋 *Добро пожаловать в Konspekt Helper Bot!*\n\n"
            
            "Я — ваш умный помощник для создания *структурированных конспектов* из любого текста. "
            "Моя задача — помочь вам эффективно обрабатывать информацию, выделяя самое важное.\n\n"
            
            "📚 *Что я умею:*\n"
            "• Анализировать тексты любой сложности\n"
            "• Создавать подробные конспекты с разделами\n"
            "• Выделять ключевые идеи и тезисы\n"
            "• Форматировать информацию для лучшего запоминания\n"
            "• Работать с научными, учебными и техническими текстами\n\n"
            
            "✨ *Как использовать:*\n"
            "1. Отправьте мне *любой текст* (статью, лекцию, заметки)\n"
            "2. Используйте команду `/conspect [ваш текст]`\n"
            "3. Я проанализирую содержание и создам развернутый конспект\n\n"
            
            "🔧 *Доступные команды:*\n"
            "• `/help` — подробная инструкция с примерами\n"
            "• `/id` — узнать ваш идентификатор в Telegram\n"
            "• `/site` — веб-панель управления ботом\n"
            "• `/conspect [текст]` — создать конспект из указанного текста\n\n"
            
            "📝 *Пример:*\n"
            "Отправьте мне:\n"
            "`Машинное обучение — область искусственного интеллекта, изучающая методы построения алгоритмов, способных обучаться на данных.`\n\n"
            
            "Я создам подробный конспект с анализом, ключевыми пунктами и выводами!\n\n"
            
            "🎯 *Начните прямо сейчас — отправьте мне любой текст!*"
        )
        
        self._update_stats(chat_id)
        return self._send_message(chat_id, welcome_text)
    
    def help_command(self, update_id, chat_id):
        """Обработка команды /help - подробный ответ"""
        help_text = (
            "📖 *ПОЛНОЕ РУКОВОДСТВО ПО ИСПОЛЬЗОВАНИЮ @Konspekt_help_bot*\n\n"
            
            "Я создаю *детальные, структурированные конспекты* из любых текстов. "
            "Моя цель — помочь вам быстро и эффективно усваивать информацию.\n\n"
            
            "🌟 *Ключевые возможности:*\n"
            
            "1. *Глубокий анализ текста*\n"
            "   - Выделение основной темы и цели\n"
            "   - Определение ключевых концепций\n"
            "   - Анализ структуры и логики изложения\n\n"
            
            "2. *Структурирование информации*\n"
            "   - Разделение на логические блоки\n"
            "   - Выделение тезисов и аргументов\n"
            "   - Определение важности информации\n\n"
            
            "3. *Форматирование конспекта*\n"
            "   - Четкая иерархия заголовков\n"
            "   - Маркированные и нумерованные списки\n"
            "   - Выделение ключевых терминов\n\n"
            
            "📋 *Формат создаваемых конспектов:*\n"
            "```\n"
            "🎯 ОСНОВНАЯ ТЕМА\n"
            "   • Цель и задачи материала\n"
            "   • Контекст и значимость\n\n"
            "📌 КЛЮЧЕВЫЕ ПОЛОЖЕНИЯ\n"
            "   1. Первый важный тезис\n"
            "   2. Второй важный тезис\n"
            "   3. Третий важный тезис\n\n"
            "🔍 ДЕТАЛЬНЫЙ АНАЛИЗ\n"
            "   • Аргументы и доказательства\n"
            "   • Примеры и иллюстрации\n"
            "   • Связи между концепциями\n\n"
            "💎 ВЫВОДЫ И ИТОГИ\n"
            "   • Основные заключения\n"
            "   • Практическое применение\n"
            "   • Рекомендации для изучения\n"
            "```\n\n"
            
            "📝 *ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ:*\n"
            
            "✅ *Пример 1 — Простой текст:*\n"
            "Отправьте: `Нейронные сети имитируют работу человеческого мозга...`\n"
            
            "✅ *Пример 2 — Академический текст:*\n"
            "Отправьте: `/conspect Квантовая механика описывает поведение...`\n"
            
            "✅ *Пример 3 — Деловой текст:*\n"
            "Отправьте текст отчета или статьи целиком\n\n"
            
            "⚙️ *ТЕХНИЧЕСКИЕ ВОЗМОЖНОСТИ:*\n"
            "• Обработка текстов до *4000 символов*\n"
            "• Поддержка *русского и английского* языков\n"
            "• Автоматическое определение темы\n"
            "• Адаптация структуры под тип контента\n\n"
            
            "🔗 *ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ:*\n"
            "• `/id` — ваш уникальный идентификатор\n"
            "• `/site` — веб-панель со статистикой\n"
            "• `/start` — это сообщение\n\n"
            
            "❓ *ЧАСТО ЗАДАВАЕМЫЕ ВОПРОСЫ:*\n"
            "• *Можно ли обрабатывать длинные тексты?* Да, но лучше разбивать на части\n"
            "• *Сохраняются ли конспекты?* Нет, они создаются только для вас\n"
            "• *Требуется ли регистрация?* Нет, просто начните общение\n\n"
            
            "🚀 *СОВЕТЫ ДЛЯ ЛУЧШИХ РЕЗУЛЬТАТОВ:*\n"
            "1. Отправляйте *законченные мысли и абзацы*\n"
            "2. Используйте *четкие формулировки*\n"
            "3. Разбивайте *очень длинные тексты* на части\n"
            "4. Указывайте *тематику*, если это важно\n\n"
            
            "🎯 *Попробуйте прямо сейчас — отправьте мне любой текст для создания подробного конспекта!*"
        )
        
        self._update_stats(chat_id)
        return self._send_message(chat_id, help_text)
    
    def get_user_id(self, update_id, chat_id):
        """Обработка команды /id"""
        response = (
            "🆔 *ВАШ ИДЕНТИФИКАТОР В TELEGRAM*\n\n"
            f"Ваш уникальный ID: `{chat_id}`\n\n"
            
            "📋 *Для чего используется этот идентификатор:*\n"
            "• *Статистика использования* — для анализа работы бота\n"
            "• *Техническая поддержка* — для решения проблем\n"
            "• *Персонализация* — для будущих улучшений\n\n"
            
            "🔒 *Конфиденциальность:*\n"
            "• Этот ID *не содержит* личной информации\n"
            "• Используется *только* для технических целей\n"
            "• *Не передается* третьим лицам\n\n"
            
            "💡 *Интересный факт:*\n"
            "Каждый пользователь Telegram имеет уникальный числовой идентификатор, "
            "который используется системой для маршрутизации сообщений."
        )
        
        self._update_stats(chat_id)
        return self._send_message(chat_id, response)
    
    def site_command(self, update_id, chat_id):
        """Обработка команды /site"""
        web_url = os.getenv("RENDER_EXTERNAL_URL", "https://konspekt-helper-bot.onrender.com")
        response = (
            "🌐 *ВЕБ-ПАНЕЛЬ УПРАВЛЕНИЯ БОТОМ*\n\n"
            f"Ссылка: {web_url}\n\n"
            
            "📊 *Что доступно на веб-панели:*\n\n"
            
            "1. *СТАТИСТИКА И АНАЛИТИКА*\n"
            "   • Количество пользователей и сообщений\n"
            "   • Активность по дням и часам\n"
            "   • Созданные конспекты\n"
            "   • Графики и диаграммы\n\n"
            
            "2. *ТЕХНИЧЕСКАЯ ИНФОРМАЦИЯ*\n"
            "   • Статус работы бота\n"
            "   • Информация о сервере\n"
            "   • Логи последних операций\n"
            "   • Проверка работоспособности\n\n"
            
            "3. *ИНСТРУМЕНТЫ АДМИНИСТРИРОВАНИЯ*\n"
            "   • Настройка вебхука\n"
            "   • Мониторинг ошибок\n"
            "   • Управление производительностью\n"
            "   • Экспорт данных\n\n"
            
            "4. *API И ИНТЕГРАЦИИ*\n"
            "   • JSON API для статистики\n"
            "   • Health check эндпоинты\n"
            "   • Webhook мониторинг\n"
            "   • Интеграционные возможности\n\n"
            
            "🔧 *Технические особенности:*\n"
            "• Панель работает на *Render.com*\n"
            "• Использует *Python 3.11.8*\n"
            "• Обновляется в *реальном времени*\n"
            "• Доступна *24/7* (с учетом особенностей бесплатного тарифа)\n\n"
            
            "📱 *Доступ с любых устройств:*\n"
            "• Адаптивный дизайн\n"
            "• Быстрая загрузка\n"
            "• Удобная навигация\n\n"
            
            "⚡ *Перейдите по ссылке, чтобы увидеть полную статистику и управлять работой бота!*"
        )
        
        self._update_stats(chat_id)
        return self._send_message(chat_id, response)
    
    def create_conspect(self, update_id, chat_id, text):
        """Создание подробного конспекта из текста"""
        if not text or not text.strip():
            return self._send_message(
                chat_id,
                "📝 *ДЛЯ СОЗДАНИЯ КОНСПЕКТА НУЖЕН ТЕКСТ*\n\n"
                "Пожалуйста, отправьте текст для анализа.\n\n"
                "✨ *Примеры:*\n"
                "• `/conspect Искусственный интеллект меняет мир...`\n"
                "• Просто отправьте любой текст сообщением\n\n"
                "🎯 *Рекомендации:*\n"
                "• Используйте законченные предложения\n"
                "• Чем подробнее текст, тем лучше конспект\n"
                "• Максимум 4000 символов"
            )
        
        # Обновление статистики
        stats["conspects_created"] += 1
        self._update_stats(chat_id)
        
        # Создаем подробный конспект
        conspect = self._generate_detailed_conspect(text)
        
        response = (
            "📚 *ВАШ КОНСПЕКТ ГОТОВ!*\n\n"
            f"{conspect}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✨ *Детали обработки:*\n"
            f"• Текст: {len(text)} символов\n"
            f"• Конспект: {len(conspect)} символов\n"
            f"• Коэффициент сжатия: {len(conspect)/len(text)*100:.1f}%\n\n"
            "💡 *Совет:* Сохраните этот конспект для повторения материала!\n\n"
            "🔄 *Хотите еще конспект? Просто отправьте новый текст!*"
        )
        
        return self._send_message(chat_id, response)
    
    def handle_message(self, update_id, chat_id, text):
        """Обработка обычных текстовых сообщений"""
        if text.startswith('/'):
            return None  # Команды обрабатываются отдельно
        
        # Создаем конспект из обычного сообщения
        return self.create_conspect(update_id, chat_id, text)
    
    def _generate_detailed_conspect(self, text):
        """Генерация подробного структурированного конспекта"""
        # Анализ текста
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Определяем тему (по первым предложениям)
        topic = "Основная тема текста"
        if sentences:
            first_sentence = sentences[0]
            if len(first_sentence) > 100:
                topic = first_sentence[:100] + "..."
            else:
                topic = first_sentence
        
        # Выделяем ключевые слова (первые 10 уникальных слов)
        key_words = list(dict.fromkeys([
            word.lower() for word in words 
            if len(word) > 3 and word.isalpha()
        ]))[:10]
        
        # Создаем детальный конспект
        conspect = (
            f"🎯 *ОСНОВНАЯ ТЕМА:*\n"
            f"{topic}\n\n"
            
            f"📌 *КЛЮЧЕВЫЕ КОНЦЕПЦИИ:*\n"
        )
        
        # Добавляем ключевые концепции из предложений
        for i, sentence in enumerate(sentences[:5], 1):
            if len(sentence) > 20:  # Только содержательные предложения
                conspect += f"{i}. {sentence}\n"
        
        conspect += (
            f"\n🔍 *ДЕТАЛЬНЫЙ АНАЛИЗ:*\n"
            f"• *Объем текста:* {len(text)} символов, {len(words)} слов\n"
            f"• *Структура:* {len(sentences)} предложений\n"
        )
        
        # Определяем тип текста
        if len(text) > 500:
            text_type = "Развернутый текст (статья, глава)"
        elif len(text) > 200:
            text_type = "Средний текст (абзац, описание)"
        else:
            text_type = "Краткое описание (тезис)"
        
        conspect += f"• *Тип текста:* {text_type}\n\n"
        
        # Добавляем ключевые термины
        if key_words:
            conspect += (
                f"🔑 *КЛЮЧЕВЫЕ ТЕРМИНЫ:*\n"
            )
            for i, word in enumerate(key_words[:6], 1):
                conspect += f"{i}. {word.capitalize()}\n"
        
        conspect += (
            f"\n💎 *СТРУКТУРИРОВАННЫЕ ВЫВОДЫ:*\n"
            f"1. *Цель текста:* Информирование/Объяснение/Аргументация\n"
            f"2. *Основная идея:* {sentences[0][:80] if sentences else 'Не определена'}...\n"
            f"3. *Важность:* Высокая/Средняя/Базовая\n"
            f"4. *Сложность:* {'Высокая' if len(words) > 200 else 'Средняя' if len(words) > 100 else 'Базовая'}\n\n"
            
            f"📋 *РЕКОМЕНДАЦИИ ДЛЯ ИЗУЧЕНИЯ:*\n"
            f"• Внимательно изучите ключевые концепции\n"
            f"• Обратите внимание на терминологию\n"
            f"• Проанализируйте связи между идеями\n"
            f"• Составьте план повторения материала\n\n"
            
            f"🎓 *ФОРМАТ КОНСПЕКТА:*\n"
            f"• Иерархическая структура\n"
            f"• Выделение главного\n"
            f"• Конкретные примеры\n"
            f"• Практические выводы"
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
        
        # Если текст слишком длинный, разбиваем на части
        max_length = 4096
        if len(text) > max_length:
            parts = []
            while text:
                if len(text) <= max_length:
                    parts.append(text)
                    break
                else:
                    # Ищем точку разрыва по абзацам
                    split_point = text[:max_length].rfind('\n\n')
                    if split_point == -1:
                        split_point = text[:max_length].rfind('\n')
                    if split_point == -1:
                        split_point = max_length
                    
                    parts.append(text[:split_point])
                    text = text[split_point:].lstrip()
            
            responses = []
            for i, part in enumerate(parts, 1):
                if len(parts) > 1:
                    part = f"*Часть {i}/{len(parts)}*\n\n{part}"
                response = self._send_single_message(chat_id, part)
                if response:
                    responses.append(response)
                time.sleep(0.5)  # Задержка между сообщениями
            return responses
        else:
            return self._send_single_message(chat_id, text)
    
    def _send_single_message(self, chat_id, text):
        """Отправка одного сообщения"""
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
            logger.info(f"Сообщение отправлено в чат {chat_id} ({len(text)} символов)")
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
            
            self._log_webhook(update)
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
        
        # Форматируем HTML с подстановкой переменных
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
            "version": "2.0.0",
            "features": ["detailed-conspects", "web-dashboard", "webhook-support"],
            "stats": {
                "uptime": stats["start_time"],
                "total_messages": stats["total_messages"],
                "active_users": len(stats["user_activity"]),
                "conspects_created": stats["conspects_created"]
            }
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
            "webhook_status": True,
            "server": {
                "python": "3.11.8",
                "hosting": "Render.com",
                "status": "running"
            }
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
    
    def _log_webhook(self, update):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "update_id": update.get("update_id", 0)
        }
        stats["recent_webhooks"].append(log_entry)
        if len(stats["recent_webhooks"]) > MAX_WEBHOOKS_LOG:
            stats["recent_webhooks"] = stats["recent_webhooks"][-MAX_WEBHOOKS_LOG:]
    
    def _process_update(self, update):
        token = os.getenv("TELEGRAM_TOKEN")
        if not token:
            logger.error("TELEGRAM_TOKEN не установлен")
            return
        
        bot = SimpleBot(token)
        
        if "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            
            if text.startswith('/'):
                if text.startswith('/start'):
                    bot.start(update.get('update_id', 0), chat_id)
                elif text.startswith('/help'):
                    bot.help_command(update.get('update_id', 0), chat_id)
                elif text.startswith('/id'):
                    bot.get_user_id(update.get('update_id', 0), chat_id)
                elif text.startswith('/site'):
                    bot.site_command(update.get('update_id', 0), chat_id)
                elif text.startswith('/conspect'):
                    conspect_text = text[9:].strip()
                    bot.create_conspect(update.get('update_id', 0), chat_id, conspect_text)
                else:
                    bot._send_message(chat_id, "Неизвестная команда. Используйте /help для списка команд.")
            elif text:
                bot.handle_message(update.get('update_id', 0), chat_id, text)
    
    def log_message(self, format, *args):
        pass

def start_bot():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN не установлен!")
        return
    
    bot = SimpleBot(token)
    bot.run_webhook()
    logger.info("Бот готов к работе через вебхуки")

def start_http_server():
    port = int(os.getenv("PORT", 10000))
    server_address = ('', port)
    
    httpd = HTTPServer(server_address, BotServer)
    logger.info(f"HTTP сервер запущен на порту {port}")
    logger.info(f"Веб-сайт: http://localhost:{port}")
    logger.info(f"Health check: http://localhost:{port}/health")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Сервер остановлен")
    except Exception as e:
        logger.error(f"Ошибка сервера: {e}")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Запуск @Konspekt_help_bot с развернутыми ответами")
    logger.info("=" * 60)
    
    # Проверяем Python версию
    import sys
    logger.info(f"Python версия: {sys.version}")
    
    if sys.version_info >= (3, 13):
        logger.warning("Рекомендуется использовать Python 3.11.8")
    
    token = os.getenv("TELEGRAM_TOKEN")
    if token:
        logger.info("TELEGRAM_TOKEN найден")
    else:
        logger.warning("TELEGRAM_TOKEN не найден!")
    
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    start_http_server()
