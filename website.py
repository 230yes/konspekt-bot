import os
from flask import Flask, render_template, jsonify
from datetime import datetime

# Создаем Flask приложение
app = Flask(__name__)

# Секретный ключ (Render автоматически установит)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-key-12345')

# Главная страница
@app.route('/')
def index():
    return render_template('index.html', section='home')

# Страница "О боте"
@app.route('/about')
def about():
    return render_template('index.html', section='about')

# Инструкция
@app.route('/instructions')
def instructions():
    return render_template('index.html', section='instructions')

# Форматы
@app.route('/formats')
def formats():
    return render_template('index.html', section='formats')

# Health check для Render
@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'service': 'konspekt-bot-website',
        'timestamp': datetime.now().isoformat()
    })

# API статус
@app.route('/api/status')
def api_status():
    return jsonify({
        'bot_name': 'Konspekt Help Bot',
        'telegram': '@Konspekt_help_bot',
        'version': '1.0.0',
        'status': 'active',
        'website': 'https://konspekt-website.onrender.com'
    })

# Запуск приложения
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
