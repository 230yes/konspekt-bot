import os
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Проверка токена
if not TOKEN:
    logger.error("Токен Telegram не найден! Проверьте переменную TELEGRAM_TOKEN")
    exit(1)

# Импорт модулей
try:
    from search_engine import SearchEngine
    from formatter import DocumentFormatter
    SEARCH_AVAILABLE = True
except ImportError as e:
    logger.error(f"Ошибка импорта модулей: {e}")
    SEARCH_AVAILABLE = False

# Состояния пользователей
user_states = {}

# Инициализация движков
if SEARCH_AVAILABLE:
    search_engine = SearchEngine()
    formatter = DocumentFormatter()

# ================== МЕНЮ ==================
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 Конспект", callback_data='type_конспект')],
        [InlineKeyboardButton("📄 Реферат", callback_data='type_реферат')],
        [InlineKeyboardButton("📋 Краткий обзор", callback_data='type_обзор')],
        [InlineKeyboardButton("🔍 Анализ текста", callback_data='type_анализ')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_volume_menu():
    keyboard = [
        [InlineKeyboardButton("1 страница", callback_data='volume_1')],
        [InlineKeyboardButton("2 страницы", callback_data='volume_2')],
        [InlineKeyboardButton("3 страницы", callback_data='volume_3')],
        [InlineKeyboardButton("5 страниц", callback_data='volume_5')],
        [InlineKeyboardButton("↩️ Назад", callback_data='back_to_main')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_format_menu():
    keyboard = [
        [InlineKeyboardButton("📄 Word (.docx)", callback_data='format_docx')],
        [InlineKeyboardButton("📋 PDF", callback_data='format_pdf')],
        [InlineKeyboardButton("📝 TXT", callback_data='format_txt')],
        [InlineKeyboardButton("💬 В чате", callback_data='format_text')],
        [InlineKeyboardButton("↩️ Назад", callback_data='back_to_volume')]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================== КОМАНДЫ ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome = f"""👋 Привет, {user.first_name}!

Я бот для создания конспектов и рефератов.

📚 **Что я умею:**
• Искать информацию в Google и Wikipedia
• Создавать конспекты, рефераты, обзоры
• Форматировать текст под нужный объем
• Сохранять в DOCX, PDF, TXT

Выберите тип работы:"""
    
    await update.message.reply_text(welcome, reply_markup=get_main_menu())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📖 **Инструкция:**

1. Выберите тип работы
2. Введите тему
3. Выберите объем (страницы А4)
4. Выберите формат выдачи

📊 **Форматы:**
• DOCX - для Microsoft Word
• PDF - для печати
• TXT - простой текст
• В чате - быстрый просмотр

❌ Отмена: /cancel"""
    await update.message.reply_text(help_text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_states:
        del user_states[user_id]
    await update.message.reply_text("Отменено. /start для начала.", reply_markup=get_main_menu())

# ================== ОБРАБОТЧИКИ ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Инициализация состояния
    if user_id not in user_states:
        user_states[user_id] = {'type': None, 'volume': None, 'format': None, 'topic': None}
    
    # Обработка типа
    if data.startswith('type_'):
        work_type = data.split('_')[1]
        user_states[user_id]['type'] = work_type
        
        type_names = {
            'конспект': 'краткое изложение',
            'реферат': 'развернутый анализ',
            'обзор': 'общий обзор',
            'анализ': 'детальный разбор'
        }
        
        await query.edit_message_text(
            f"✅ **{work_type.capitalize()}**\n"
            f"{type_names.get(work_type, '')}\n\n"
            f"📝 Введите тему:",
            parse_mode='Markdown'
        )
    
    # Объем
    elif data.startswith('volume_'):
        pages = int(data.split('_')[1])
        user_states[user_id]['volume'] = pages
        
        await query.edit_message_text(
            f"📊 **{pages} стр. А4**\n\nВыберите формат:",
            parse_mode='Markdown',
            reply_markup=get_format_menu()
        )
    
    # Формат
    elif data.startswith('format_'):
        format_type = data.split('_')[1]
        user_states[user_id]['format'] = format_type
        
        # Начинаем обработку
        await process_request(update, context, user_id)
    
    # Навигация
    elif data == 'back_to_main':
        await query.edit_message_text("Выберите тип работы:", reply_markup=get_main_menu())
    elif data == 'back_to_volume':
        await query.edit_message_text("Выберите объем:", reply_markup=get_volume_menu())
    elif data == 'help':
        await help_command(update, context)

async def handle_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_states:
        await update.message.reply_text("Сначала выберите тип через /start")
        return
    
    topic = update.message.text.strip()
    if len(topic) < 3:
        await update.message.reply_text("Тема слишком короткая. Введите подробнее.")
        return
    
    user_states[user_id]['topic'] = topic
    
    await update.message.reply_text(
        f"📌 Тема: **{topic}**\n\nВыберите объем:",
        parse_mode='Markdown',
        reply_markup=get_volume_menu()
    )

# ================== ОСНОВНАЯ ЛОГИКА ==================
async def process_request(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Основная функция обработки запроса"""
    try:
        state = user_states[user_id]
        
        # Проверка доступности поиска
        if not SEARCH_AVAILABLE:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Сервис поиска временно недоступен"
            )
            return
        
        # Уведомление о начале
        status_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🔍 Ищу информацию по теме: **{state['topic']}**...",
            parse_mode='Markdown'
        )
        
        # Поиск информации
        search_results = search_engine.search_all_sources(state['topic'], max_results=3)
        
        if not search_results:
            await status_msg.edit_text("❌ Не удалось найти информацию. Попробуйте другую тему.")
            return
        
        # Формирование текста
        await status_msg.edit_text("📚 Обрабатываю найденную информацию...")
        
        combined_text = ""
        for result in search_results:
            content = result.get('content', result.get('summary', ''))
            if content:
                combined_text += f"\n\n[{result.get('source', 'Источник')}]: {content}"
        
        # Форматирование
        formatted_text = formatter.format_for_a4(combined_text, state['volume'])
        
        # Создание файла
        await status_msg.edit_text("📄 Создаю документ...")
        
        filename = None
        if state['format'] == 'docx':
            filename = formatter.create_word_document(formatted_text, state['topic'], state['type'])
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(filename, 'rb'),
                filename=f"{state['type']}_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                caption=f"📄 {state['type'].capitalize()}: {state['topic']}"
            )
        
        elif state['format'] == 'pdf':
            filename = formatter.create_pdf_document(formatted_text, state['topic'], state['type'])
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(filename, 'rb'),
                filename=f"{state['type']}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                caption=f"📄 {state['type'].capitalize()}: {state['topic']}"
            )
        
        elif state['format'] == 'txt':
            filename = formatter.create_txt_file(formatted_text, state['topic'], state['type'])
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(filename, 'rb'),
                filename=f"{state['type']}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                caption=f"📄 {state['type'].capitalize()}: {state['topic']}"
            )
        
        else:  # text в чате
            chunks = [formatted_text[i:i+4000] for i in range(0, len(formatted_text), 4000)]
            await status_msg.delete()
            
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"📝 **{state['type'].capitalize()}: {state['topic']}**\n\n{chunk}",
                        parse_mode='Markdown'
                    )
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=chunk
                    )
        
        # Очистка
        if filename and os.path.exists(filename):
            os.remove(filename)
        
        if user_id in user_states:
            del user_states[user_id]
        
        # Предложение нового запроса
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="✅ Готово! Создать еще?",
            reply_markup=get_main_menu()
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка при обработке запроса. Попробуйте позже."
        )
        
        if user_id in user_states:
            del user_states[user_id]

# ================== ЗАПУСК ==================
def main():
    """Основная функция запуска"""
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_topic))
    
    # Запуск
    logger.info("🚀 Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
